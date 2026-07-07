"""Background auto-piracy runner.

Mirrors Ikabot's ``autoPirate``: repeat a piracy mission a number of times,
waiting the mission's duration plus a random extra delay between runs.

Because the app is a single uvicorn process, each account's loop runs as an
asyncio task tracked in-memory. Status is exposed so the UI can poll it.
"""

import asyncio
import logging
import random
import time
from typing import Optional

from sqlalchemy import select

from app.database import async_session
from app.models.account import IkariamAccount
from app.models.proxy import Proxy
from app.services.ikariam.game_actions import GameActionService
from app.services.ikariam.session import (
    GameSessionError,
    PIRACY_MISSION_WAITING_TIME,
)

logger = logging.getLogger(__name__)

# account_id -> status dict
_STATUS: dict[int, dict] = {}
# account_id -> asyncio.Task
_TASKS: dict[int, asyncio.Task] = {}


def get_status(account_id: int) -> Optional[dict]:
    return _STATUS.get(account_id)


def is_running(account_id: int) -> bool:
    task = _TASKS.get(account_id)
    return task is not None and not task.done()


async def _resolve_proxy_url(db, account: IkariamAccount) -> Optional[str]:
    if not account.proxy_id:
        return None
    result = await db.execute(select(Proxy).where(Proxy.id == account.proxy_id))
    proxy = result.scalar_one_or_none()
    return proxy.url if proxy else None


async def _run_loop(
    account_id: int,
    city_id: str,
    mission_level: int,
    runs: int,
    extra_wait_max: int,
) -> None:
    status = _STATUS[account_id]
    base_wait = PIRACY_MISSION_WAITING_TIME.get(int(mission_level), 150)
    try:
        for _ in range(runs):
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
                proxy_url = await _resolve_proxy_url(db, account)
                service = GameActionService(account=account, db=db, proxy_url=proxy_url)
                try:
                    result = await service.start_piracy(city_id, mission_level)
                except GameSessionError as e:
                    status["state"] = "stopped"
                    status["message"] = str(e)
                    return
                except Exception as e:  # noqa: BLE001 - surface unexpected errors
                    status["state"] = "error"
                    status["message"] = f"Erro: {e}"
                    return

            status["runs_done"] += 1
            status["runs_left"] = runs - status["runs_done"]
            status["message"] = result.get("message", "Missao iniciada.")

            if status["runs_done"] >= runs:
                break

            wait_s = base_wait + random.randint(0, max(0, extra_wait_max))
            status["next_run_at"] = time.time() + wait_s
            status["message"] = (
                f"Missao {status['runs_done']}/{runs} iniciada. "
                f"Proxima em ~{wait_s // 60}min {wait_s % 60}s."
            )
            await asyncio.sleep(wait_s)

        status["state"] = "done"
        status["next_run_at"] = None
        status["message"] = f"Concluido: {status['runs_done']} missoes."
    except asyncio.CancelledError:
        status["state"] = "stopped"
        status["next_run_at"] = None
        status["message"] = f"Parado pelo usuario apos {status['runs_done']} missoes."
        raise
    finally:
        _TASKS.pop(account_id, None)


def start(
    account_id: int,
    city_id: str,
    mission_level: int,
    runs: int,
    extra_wait_max: int,
) -> dict:
    if is_running(account_id):
        raise ValueError("Ja existe uma pirataria automatica rodando para esta conta.")

    _STATUS[account_id] = {
        "state": "running",
        "city_id": city_id,
        "mission_level": mission_level,
        "runs": runs,
        "runs_done": 0,
        "runs_left": runs,
        "extra_wait_max": extra_wait_max,
        "next_run_at": None,
        "message": "Iniciando...",
    }
    task = asyncio.create_task(
        _run_loop(account_id, city_id, mission_level, runs, extra_wait_max)
    )
    _TASKS[account_id] = task
    return _STATUS[account_id]


async def stop(account_id: int) -> None:
    task = _TASKS.get(account_id)
    if task is None or task.done():
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
