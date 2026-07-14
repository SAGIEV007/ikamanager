"""Background recurring runners for resources: donations and building upgrades.

Two kinds of loop are supported per account:

- ``donate``: repeatedly donate resources to the city's island (to grow the
  island level). Amount can be fixed or a percentage of what's stored.
- ``upgrade``: repeatedly upgrade a building (a fixed position, or the lowest
  building that can currently be upgraded).

Each loop runs as an in-memory asyncio task (the app is a single process),
respects the account's operation-hours window and uses human-like timing.
Multiple accounts run their loops in parallel; per-account request
serialization is still enforced by ``account_locks`` inside the service.
"""

import asyncio
import logging
import time
from typing import Optional

from sqlalchemy import select

from app.database import async_session
from app.models.account import IkariamAccount
from app.services.ikariam.game_actions import GameActionService
from app.services.ikariam.runner_common import (
    human_wait,
    resolve_proxy_url,
    seconds_until_window,
)
from app.services.ikariam.session import GameSessionError

logger = logging.getLogger(__name__)

# (kind, account_id) -> status dict / asyncio.Task
_STATUS: dict[tuple[str, int], dict] = {}
_TASKS: dict[tuple[str, int], asyncio.Task] = {}


def _key(kind: str, account_id: int) -> tuple[str, int]:
    return (kind, account_id)


def get_status(kind: str, account_id: int) -> Optional[dict]:
    return _STATUS.get(_key(kind, account_id))


def is_running(kind: str, account_id: int) -> bool:
    task = _TASKS.get(_key(kind, account_id))
    return task is not None and not task.done()


def status_all(kind: Optional[str] = None) -> list[dict]:
    out = []
    for (k, account_id), status in _STATUS.items():
        if kind and k != kind:
            continue
        entry = dict(status)
        entry["kind"] = k
        entry["account_id"] = account_id
        entry["running"] = is_running(k, account_id)
        out.append(entry)
    return out


async def _perform(kind: str, account_id: int, config: dict) -> dict:
    """Run one action of the given kind and return its result dict."""
    async with async_session() as db:
        account = (
            await db.execute(
                select(IkariamAccount).where(IkariamAccount.id == account_id)
            )
        ).scalar_one_or_none()
        if account is None:
            raise GameSessionError("Conta nao encontrada.")
        proxy_url = await resolve_proxy_url(db, account)
        service = GameActionService(account=account, db=db, proxy_url=proxy_url)
        if kind == "donate":
            return await service.donate(
                config["city_id"],
                config["resource_type"],
                amount=config.get("amount", 0),
                percent=config.get("percent", 0),
            )
        if kind == "upgrade":
            return await service.upgrade_next(
                config["city_id"], position=config.get("position")
            )
        raise ValueError(f"Tipo de tarefa desconhecido: {kind}")


async def _run_loop(kind: str, account_id: int, config: dict) -> None:
    key = _key(kind, account_id)
    status = _STATUS[key]
    interval = int(config.get("interval_s", 1800))
    extra_wait_max = int(config.get("extra_wait_max", 60))
    runs = int(config.get("runs", 0))  # 0 = infinite
    try:
        while runs == 0 or status["runs_done"] < runs:
            # Operation-hours window (a normal player doesn't grind 24/7).
            async with async_session() as db:
                account = (
                    await db.execute(
                        select(IkariamAccount).where(IkariamAccount.id == account_id)
                    )
                ).scalar_one_or_none()
                if account is None:
                    status["state"] = "error"
                    status["message"] = "Conta nao encontrada."
                    return
                wait_window = seconds_until_window(
                    account.operation_start_hour, account.operation_end_hour
                )
                start_h = account.operation_start_hour
                end_h = account.operation_end_hour

            if wait_window > 0:
                status["state"] = "waiting_hours"
                status["next_run_at"] = time.time() + wait_window
                status["message"] = (
                    f"Fora do horario de operacao ({start_h}h-{end_h}h). "
                    f"Retomando em ~{wait_window // 3600}h{(wait_window % 3600) // 60}min."
                )
                await asyncio.sleep(wait_window)
                status["state"] = "running"
                continue

            try:
                result = await _perform(kind, account_id, config)
            except GameSessionError as e:
                status["state"] = "stopped"
                status["message"] = str(e)
                return
            except Exception as e:  # noqa: BLE001 - surface unexpected errors
                status["state"] = "error"
                status["message"] = f"Erro: {e}"
                logger.exception("Auto-%s falhou para conta %s", kind, account_id)
                return

            status["runs_done"] += 1
            status["last_result"] = result.get("status")
            status["last_message"] = result.get("message", "")

            if runs and status["runs_done"] >= runs:
                break

            wait_s = human_wait(interval, extra_wait_max)
            status["next_run_at"] = time.time() + wait_s
            status["state"] = "running"
            status["message"] = (
                f"Ciclo {status['runs_done']}"
                + (f"/{runs}" if runs else "")
                + f": {result.get('message', '')} "
                f"Proximo em ~{wait_s // 60}min {wait_s % 60}s."
            )
            await asyncio.sleep(wait_s)

        status["state"] = "done"
        status["next_run_at"] = None
        status["message"] = f"Concluido: {status['runs_done']} ciclos."
    except asyncio.CancelledError:
        status["state"] = "stopped"
        status["next_run_at"] = None
        status["message"] = f"Parado pelo usuario apos {status['runs_done']} ciclos."
        raise
    finally:
        _TASKS.pop(key, None)


def _start(kind: str, account_id: int, config: dict) -> dict:
    if is_running(kind, account_id):
        raise ValueError(
            f"Ja existe uma tarefa '{kind}' rodando para esta conta."
        )
    status = {
        "state": "running",
        "runs_done": 0,
        "runs": int(config.get("runs", 0)),
        "config": {k: v for k, v in config.items()},
        "next_run_at": None,
        "message": "Iniciando...",
    }
    _STATUS[_key(kind, account_id)] = status
    task = asyncio.create_task(_run_loop(kind, account_id, config))
    _TASKS[_key(kind, account_id)] = task
    return status


def start_donate(
    account_id: int,
    city_id: str,
    resource_type: str,
    amount: int = 0,
    percent: int = 0,
    interval_minutes: int = 30,
    extra_wait_max: int = 60,
    runs: int = 0,
) -> dict:
    return _start(
        "donate",
        account_id,
        {
            "city_id": city_id,
            "resource_type": resource_type,
            "amount": amount,
            "percent": percent,
            "interval_s": int(interval_minutes) * 60,
            "extra_wait_max": extra_wait_max,
            "runs": runs,
        },
    )


def start_upgrade(
    account_id: int,
    city_id: str,
    position: Optional[int] = None,
    interval_minutes: int = 20,
    extra_wait_max: int = 60,
    runs: int = 0,
) -> dict:
    return _start(
        "upgrade",
        account_id,
        {
            "city_id": city_id,
            "position": position,
            "interval_s": int(interval_minutes) * 60,
            "extra_wait_max": extra_wait_max,
            "runs": runs,
        },
    )


async def stop(kind: str, account_id: int) -> None:
    task = _TASKS.get(_key(kind, account_id))
    if task is None or task.done():
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
