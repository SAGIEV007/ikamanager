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
import random
import time
from typing import Optional

from sqlalchemy import select

from app.database import async_session
from app.models.account import IkariamAccount
from app.models.resource_job import ResourceJob
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


async def _persist_job(kind: str, account_id: int, config: dict) -> None:
    """Upsert the job as active so it can be resumed after a restart."""
    try:
        async with async_session() as db:
            existing = (
                await db.execute(
                    select(ResourceJob).where(
                        ResourceJob.account_id == account_id,
                        ResourceJob.kind == kind,
                    )
                )
            ).scalar_one_or_none()
            if existing is None:
                db.add(
                    ResourceJob(
                        account_id=account_id,
                        kind=kind,
                        config=dict(config),
                        is_active=True,
                    )
                )
            else:
                existing.config = dict(config)
                existing.is_active = True
            await db.commit()
    except Exception:  # noqa: BLE001 - persistence must never break the loop
        logger.exception("Falha ao salvar job %s da conta %s", kind, account_id)


async def _deactivate_job(kind: str, account_id: int) -> None:
    """Mark the job inactive so it is NOT resumed on the next restart."""
    try:
        async with async_session() as db:
            existing = (
                await db.execute(
                    select(ResourceJob).where(
                        ResourceJob.account_id == account_id,
                        ResourceJob.kind == kind,
                    )
                )
            ).scalar_one_or_none()
            if existing is not None:
                existing.is_active = False
                await db.commit()
    except Exception:  # noqa: BLE001 - persistence must never break the loop
        logger.exception("Falha ao desativar job %s da conta %s", kind, account_id)


# How long to wait before re-checking the session after it expired. The loop
# stays alive during this time so it resumes automatically once the user logs
# in again (no app restart needed).
SESSION_RETRY_S = 120


async def _set_account_session_state(
    account_id: int, online: bool, status: str, message: str
) -> None:
    """Update the account's session status from inside a runner loop."""
    try:
        async with async_session() as db:
            account = (
                await db.execute(
                    select(IkariamAccount).where(IkariamAccount.id == account_id)
                )
            ).scalar_one_or_none()
            if account is None:
                return
            # Only write when something actually changed (avoids churn).
            if (
                account.is_online == online
                and account.status == status
                and account.status_message == message
            ):
                return
            account.is_online = online
            account.status = status
            account.status_message = message
            if not online:
                account.session_cookie = None
            await db.commit()
    except Exception:  # noqa: BLE001 - status sync must never break the loop
        logger.exception("Falha ao atualizar status da conta %s", account_id)


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
        if config.get("all_cities") and kind in ("donate", "upgrade"):
            return await _perform_all_cities(service, kind, config)
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
        if kind == "research":
            # Research is account-wide (single Academy per account), so it never
            # iterates cities.
            return await service.research_next()
        raise ValueError(f"Tipo de tarefa desconhecido: {kind}")


async def _perform_all_cities(
    service: GameActionService, kind: str, config: dict
) -> dict:
    """Run the action on *every* own city of the account, one after another.

    Used when the account has several cities on the island: a single task
    keeps them all growing/donating instead of only the main city.
    """
    cities = await service.get_cities()
    own = [c["id"] for c in cities if c.get("relationship") == "ownCity"]
    if not own:
        return {"status": "skipped", "message": "Nenhuma cidade propria encontrada."}

    ok = 0
    parts = []
    for city_id in own:
        if kind == "donate":
            res = await service.donate(
                city_id,
                config["resource_type"],
                amount=config.get("amount", 0),
                percent=config.get("percent", 0),
            )
        elif kind == "upgrade":
            # position is per-city, so always auto-pick when covering all cities
            res = await service.upgrade_next(city_id, position=None)
        else:
            raise ValueError(f"Tipo de tarefa desconhecido: {kind}")
        if res.get("status") == "success":
            ok += 1
        parts.append(res.get("message", ""))

    return {
        "status": "success" if ok else "skipped",
        "message": f"{ok}/{len(own)} cidades: " + " | ".join(p for p in parts if p),
    }


async def _run_loop(kind: str, account_id: int, config: dict) -> None:
    key = _key(kind, account_id)
    status = _STATUS[key]
    interval = int(config.get("interval_s", 1800))
    extra_wait_max = int(config.get("extra_wait_max", 60))
    runs = int(config.get("runs", 0))  # 0 = infinite
    # Persist the job so it can be resumed automatically after a restart.
    await _persist_job(kind, account_id, config)
    try:
        # Stagger the start so several accounts don't all act in the same
        # minute (a dead giveaway for a bot). Each account waits a random
        # slice of the interval before its first cycle.
        if config.get("stagger"):
            offset = random.randint(0, min(interval, 600))
            if offset > 0:
                status["state"] = "waiting_hours"
                status["next_run_at"] = time.time() + offset
                status["message"] = (
                    f"Escalonando inicio (~{offset // 60}min {offset % 60}s) "
                    "para nao agir junto com as outras contas."
                )
                await asyncio.sleep(offset)
                status["state"] = "running"
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
                # Session expired (e.g. the player logged in elsewhere). Keep
                # the task alive and retry: it will resume by itself once the
                # user logs in again, without restarting the app.
                await _set_account_session_state(
                    account_id, False, "session_expired", str(e)
                )
                status["state"] = "waiting_login"
                status["next_run_at"] = time.time() + SESSION_RETRY_S
                status["message"] = (
                    f"Sessao expirada: {e} "
                    f"Retomo sozinho apos voce relogar (checo a cada "
                    f"~{SESSION_RETRY_S // 60}min)."
                )
                await asyncio.sleep(SESSION_RETRY_S)
                status["state"] = "running"
                continue
            except Exception as e:  # noqa: BLE001 - surface unexpected errors
                status["state"] = "error"
                status["message"] = f"Erro: {e}"
                logger.exception("Auto-%s falhou para conta %s", kind, account_id)
                return

            # A successful action proves the session works again.
            await _set_account_session_state(
                account_id, True, "online", "Sessao ativa."
            )
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
        # Finished on its own: don't resume it after a restart.
        await _deactivate_job(kind, account_id)
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
    all_cities: bool = False,
    stagger: bool = False,
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
            "all_cities": all_cities,
            "stagger": stagger,
        },
    )


def start_upgrade(
    account_id: int,
    city_id: str,
    position: Optional[int] = None,
    interval_minutes: int = 20,
    extra_wait_max: int = 60,
    runs: int = 0,
    all_cities: bool = False,
    stagger: bool = False,
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
            "all_cities": all_cities,
            "stagger": stagger,
        },
    )


def start_research(
    account_id: int,
    interval_minutes: int = 60,
    extra_wait_max: int = 120,
    runs: int = 0,
    stagger: bool = False,
) -> dict:
    return _start(
        "research",
        account_id,
        {
            "interval_s": int(interval_minutes) * 60,
            "extra_wait_max": extra_wait_max,
            "runs": runs,
            "stagger": stagger,
        },
    )


async def stop(kind: str, account_id: int) -> None:
    # Stopped by the user: mark inactive so it is not resumed on restart.
    await _deactivate_job(kind, account_id)
    task = _TASKS.get(_key(kind, account_id))
    if task is None or task.done():
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def resume_active_jobs() -> int:
    """Restart every job left active in the DB (called on app startup).

    Returns the number of jobs resumed. Idempotent: jobs already running are
    skipped.
    """
    resumed = 0
    try:
        async with async_session() as db:
            jobs = (
                await db.execute(
                    select(ResourceJob).where(ResourceJob.is_active.is_(True))
                )
            ).scalars().all()
    except Exception:  # noqa: BLE001 - never block startup on this
        logger.exception("Falha ao ler jobs persistidos no startup")
        return 0

    for job in jobs:
        if is_running(job.kind, job.account_id):
            continue
        try:
            _start(job.kind, job.account_id, dict(job.config or {}))
            resumed += 1
        except ValueError:
            # Already running or invalid; skip.
            continue
        except Exception:  # noqa: BLE001 - one bad job must not stop the rest
            logger.exception(
                "Falha ao retomar job %s da conta %s", job.kind, job.account_id
            )
    if resumed:
        logger.info("Retomadas %s tarefa(s) de recursos do banco.", resumed)
    return resumed
