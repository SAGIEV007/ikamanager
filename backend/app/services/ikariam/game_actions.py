"""Game action service - executes real game actions using a stored session.

After a successful login (see accounts.py), the account's ``session_cookie``
holds a JSON blob with the Gameforge token, the in-game ``ikariam`` cookie and
the game server URL. This service reuses those cookies directly (the same way
Ikabot reuses the ``ikariam`` cookie), so game actions do NOT need the blackbox
token again.
"""

import json
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.services.ikariam.session import IkariamSession, GameSessionError
from app.services.ikariam import captcha
from app.services.ikariam import account_locks
from app.models.account import IkariamAccount
from app.services import app_settings

logger = logging.getLogger(__name__)


def serialize_session(gf_token: str, cookies: dict, server_url: str) -> str:
    return json.dumps(
        {"gf_token": gf_token, "cookies": cookies, "server_url": server_url}
    )


class GameActionService:
    """Executes game actions for a logged-in account using stored cookies."""

    def __init__(
        self,
        account: IkariamAccount,
        db: AsyncSession,
        proxy_url: Optional[str] = None,
    ):
        self.account = account
        self.db = db
        self.proxy_url = proxy_url

    def _load_session_data(self) -> dict:
        raw = self.account.session_cookie
        if not raw:
            raise GameSessionError("Conta nao esta logada. Faca login primeiro.")
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            raise GameSessionError(
                "Sessao invalida. Faca login novamente para entrar no mundo."
            )
        if not data.get("cookies") or not data.get("server_url"):
            raise GameSessionError(
                "Sessao do jogo ausente. Faca login novamente para entrar no mundo."
            )
        return data

    def _build_captcha_solver(self):
        """Return an async captcha solver ``(bytes) -> str`` based on settings.

        Returns ``None`` when captcha solving is disabled ("off").
        """
        mode = (app_settings.get_captcha_mode() or "auto").lower()
        if mode == "off":
            return None
        key = app_settings.get_twocaptcha_key()

        async def _solver(image_bytes: bytes) -> str:
            return await captcha.solve(image_bytes, mode=mode, twocaptcha_key=key)

        return _solver

    async def _open_session(self) -> IkariamSession:
        data = self._load_session_data()
        session = IkariamSession(
            server_url=data["server_url"],
            cookies=data["cookies"],
            proxy_url=self.proxy_url,
            delay_min=self.account.delay_min,
            delay_max=self.account.delay_max,
        )
        await session.start()
        return session

    async def get_cities(self) -> list:
        async with account_locks.get_lock(self.account.id):
            session = await self._open_session()
            try:
                return await session.get_cities()
            finally:
                await session.close()

    async def get_city(self, city_id) -> dict:
        async with account_locks.get_lock(self.account.id):
            session = await self._open_session()
            try:
                await session.get_action_token()
                return await session.get_city(city_id)
            finally:
                await session.close()

    async def get_full_game_data(self) -> dict:
        """List cities and load detail for each own city."""
        async with account_locks.get_lock(self.account.id):
            session = await self._open_session()
            try:
                cities = await session.get_cities()
                await session.get_action_token()
                detailed = []
                for c in cities:
                    if c["relationship"] != "ownCity":
                        continue
                    try:
                        detail = await session.get_city(c["id"])
                        detail["coords"] = c["coords"]
                        detail["tradegood"] = c["tradegood"]
                        detailed.append(detail)
                    except GameSessionError as e:
                        detailed.append(
                            {"id": c["id"], "name": c["name"], "coords": c["coords"], "error": str(e)}
                        )
                return {"cities": detailed}
            finally:
                await session.close()

    async def donate(self, city_id, resource_type: str, amount: int) -> dict:
        async with account_locks.get_lock(self.account.id):
            session = await self._open_session()
            try:
                # Resolve island id for the city
                detail = await self.get_city_detail(session, city_id)
                island_id = detail.get("islandId", "")
                if not island_id:
                    return {"status": "failed", "message": "Ilha da cidade nao encontrada."}
                resp = await session.donate(city_id, island_id, resource_type, amount)
                success = session.action_succeeded(resp)
                self.account.last_action = datetime.utcnow()
                await self.db.commit()
                return {
                    "status": "success" if success else "failed",
                    "message": (
                        f"Doacao de {amount} de {resource_type} "
                        + ("realizada." if success else "falhou.")
                    ),
                }
            finally:
                await session.close()

    async def upgrade_building(self, city_id, position: int) -> dict:
        async with account_locks.get_lock(self.account.id):
            session = await self._open_session()
            try:
                await session.get_action_token()
                detail = await session.get_city(city_id)
                positions = detail.get("positions", [])
                if position < 0 or position >= len(positions):
                    return {"status": "failed", "message": "Posicao de edificio invalida."}
                building = positions[position]
                if building["building"] == "empty":
                    return {
                        "status": "failed",
                        "message": "Nao ha edificio nesta posicao para melhorar.",
                    }
                resp = await session.upgrade_building(
                    city_id=city_id,
                    position=position,
                    level=building["level"],
                    building_type=building["building"],
                )
                success = session.action_succeeded(resp)
                self.account.last_action = datetime.utcnow()
                await self.db.commit()
                return {
                    "status": "success" if success else "failed",
                    "message": (
                        f"Melhoria de {building['name']} (pos {position}) "
                        + ("iniciada." if success else "falhou.")
                    ),
                }
            finally:
                await session.close()

    async def start_piracy(self, city_id, mission_level: int = 1) -> dict:
        async with account_locks.get_lock(self.account.id):
            session = await self._open_session()
            try:
                solver = self._build_captcha_solver()
                resp = await session.start_piracy(
                    city_id, mission_level, captcha_solver=solver
                )
                success = session.action_succeeded(resp)
                self.account.last_action = datetime.utcnow()
                await self.db.commit()
                return {
                    "status": "success" if success else "failed",
                    "message": "Pirataria " + ("iniciada." if success else "falhou."),
                }
            finally:
                await session.close()

    @staticmethod
    async def get_city_detail(session: IkariamSession, city_id) -> dict:
        await session.get_action_token()
        return await session.get_city(city_id)
