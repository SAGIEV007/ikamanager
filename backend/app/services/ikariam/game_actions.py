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

# Growth-focused upgrade priority (Level-1 autopilot). Buildings earlier in the
# list are preferred when several are eligible at the same level, so the city
# grows in a healthy order (storage -> population -> satisfaction -> production
# -> research) instead of blindly bumping whatever is lowest. Keys are the
# internal Ikariam building identifiers reported by the city parser.
UPGRADE_PRIORITY: list[str] = [
    "warehouse",     # protect stored resources first
    "townHall",      # population / workers
    "tavern",        # satisfaction (keeps population growing)
    "museum",        # culture / satisfaction (needed to expand)
    "carpentering",  # cheaper wood buildings
    "architect",     # cheaper marble buildings
    "vineyard",      # cheaper wine buildings
    "optician",      # cheaper crystal buildings
    "fireworker",    # cheaper sulfur buildings
    "academy",       # research output
    "forester",      # wood production
    "stonemason",    # marble production
    "winegrower",    # wine production
    "glassblowing",  # crystal production
    "alchemist",     # sulfur production
    "port",          # trading port
    "branchOffice",  # trading post
]
_PRIORITY_RANK = {name: i for i, name in enumerate(UPGRADE_PRIORITY)}
# Military / non-resource buildings: only touched when nothing else is eligible.
_DEPRIORITIZED = {
    "barracks",
    "wall",
    "shipyard",
    "embassy",
    "safehouse",
    "temple",
    "dump",
    "pirateFortress",
    "marineChamber",
}
_DEFAULT_RANK = len(UPGRADE_PRIORITY) + 1
_DEPRIORITIZED_RANK = _DEFAULT_RANK + 100


def _upgrade_rank(building: str) -> int:
    if building in _DEPRIORITIZED:
        return _DEPRIORITIZED_RANK
    return _PRIORITY_RANK.get(building, _DEFAULT_RANK)


# Economy-oriented research keywords (pt-br / en). Used to prefer research that
# boosts resources/storage/economy first when several are available.
_RESEARCH_PRIORITY: tuple[str, ...] = (
    "economia",
    "economy",
    "comercio",
    "comercial",
    "trade",
    "armazen",
    "deposito",
    "storage",
    "carga",
    "expedicao",
    "well",
    "construcao",
    "constru",
    "carpint",
    "recurso",
    "resource",
    "producao",
    "geometr",
    "conserv",
)


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

    async def verify_session(self) -> dict:
        """Check whether the stored game session is really usable *right now*
        and update the account's status to reflect reality.

        This is what makes the UI honest: an account can show ``online`` only
        because it logged in once, even though the session has since expired
        (e.g. the player logged in from their phone). A light request to the
        game confirms the truth and flips the status to ``session_expired``
        when the cookie no longer works.
        """
        async with account_locks.get_lock(self.account.id):
            try:
                session = await self._open_session()
            except GameSessionError as e:
                return await self._set_session_status(False, "session_expired", str(e))
            try:
                await session.get_cities()
            except GameSessionError as e:
                return await self._set_session_status(False, "session_expired", str(e))
            finally:
                await session.close()
            return await self._set_session_status(True, "online", "Sessao ativa.")

    async def _set_session_status(
        self, online: bool, status: str, message: str
    ) -> dict:
        self.account.is_online = online
        self.account.status = status
        self.account.status_message = message
        if not online:
            # A dead session cookie is useless; drop it so the UI clearly
            # requires a fresh login.
            self.account.session_cookie = None
        await self.db.commit()
        return {"online": online, "status": status, "message": message}

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

    async def donate(
        self,
        city_id,
        resource_type: str,
        amount: int = 0,
        percent: int = 0,
    ) -> dict:
        """Donate resources to the city's island.

        ``resource_type`` is ``"wood"`` (forest) or ``"tradegood"`` (luxury).
        When ``percent`` > 0 the amount is computed as that percentage of the
        currently stored resource, so a recurring donation never fails for
        lack of resources (it just donates what is available).
        """
        async with account_locks.get_lock(self.account.id):
            session = await self._open_session()
            try:
                # Resolve island id for the city
                detail = await self.get_city_detail(session, city_id)
                island_id = detail.get("islandId", "")
                if not island_id:
                    return {"status": "failed", "message": "Ilha da cidade nao encontrada."}

                donate_amount = int(amount)
                if percent > 0:
                    available = await self._available_resource(
                        session, city_id, resource_type, detail
                    )
                    donate_amount = int(available * min(percent, 100) / 100)

                if donate_amount <= 0:
                    return {
                        "status": "skipped",
                        "message": "Nada a doar (recurso insuficiente).",
                    }

                resp = await session.donate(
                    city_id, island_id, resource_type, donate_amount
                )
                success = session.action_succeeded(resp)
                self.account.last_action = datetime.utcnow()
                await self.db.commit()
                return {
                    "status": "success" if success else "failed",
                    "amount": donate_amount,
                    "message": (
                        f"Doacao de {donate_amount} de {resource_type} "
                        + ("realizada." if success else "falhou.")
                    ),
                }
            finally:
                await session.close()

    # tradegood index (from the city list) -> stored-resource name
    _TRADEGOOD_TO_RESOURCE = {"1": "wine", "2": "marble", "3": "crystal", "4": "sulfur"}

    async def _available_resource(
        self, session: IkariamSession, city_id, resource_type: str, detail: dict
    ) -> int:
        """How much of the donatable resource the city currently stores."""
        resources = detail.get("resources", {}) or {}
        if resource_type == "wood":
            return int(resources.get("wood", 0))
        # Luxury: figure out which good this city produces from the city list.
        try:
            cities = await session.get_cities()
        except GameSessionError:
            cities = []
        tradegood = ""
        for c in cities:
            if str(c.get("id")) == str(city_id):
                tradegood = str(c.get("tradegood", ""))
                break
        res_name = self._TRADEGOOD_TO_RESOURCE.get(tradegood)
        if not res_name:
            return 0
        return int(resources.get(res_name, 0))

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

    async def upgrade_next(
        self, city_id, position: Optional[int] = None, prioritized: bool = True
    ) -> dict:
        """Upgrade one building in a city.

        If ``position`` is given, upgrade that building. Otherwise pick a
        building that reports ``canUpgrade`` and isn't already under
        construction. When ``prioritized`` (Level-1 autopilot) the choice
        keeps the city balanced but nudges growth toward the important
        buildings (see ``UPGRADE_PRIORITY``): among all eligible buildings it
        upgrades the lowest level, breaking ties by priority. When
        ``prioritized`` is False it falls back to the plain lowest-level pick.
        Returns ``status="skipped"`` when nothing can be upgraded right now
        (e.g. not enough resources / already building).
        """
        async with account_locks.get_lock(self.account.id):
            session = await self._open_session()
            try:
                await session.get_action_token()
                detail = await session.get_city(city_id)
                positions = detail.get("positions", [])

                target = None
                if position is not None:
                    if 0 <= position < len(positions):
                        b = positions[position]
                        if b["building"] != "empty":
                            target = b
                else:
                    candidates = [
                        b
                        for b in positions
                        if b["building"] != "empty"
                        and not b.get("isBusy")
                        and not b.get("isMaxLevel")
                        and b.get("canUpgrade")
                    ]
                    if prioritized:
                        # Growth-focused: never spend resources on military /
                        # non-resource buildings while any resource-oriented
                        # building can still be upgraded. Among the preferred
                        # set, keep the city balanced (lowest level first) but
                        # break ties toward the more important buildings.
                        preferred = [
                            b
                            for b in candidates
                            if b.get("building", "") not in _DEPRIORITIZED
                        ]
                        pool = preferred or candidates
                        pool.sort(
                            key=lambda b: (
                                b.get("level") or 0,
                                _upgrade_rank(b.get("building", "")),
                            )
                        )
                        if pool:
                            target = pool[0]
                    else:
                        candidates.sort(key=lambda b: (b.get("level") or 0))
                        if candidates:
                            target = candidates[0]

                if target is None:
                    return {
                        "status": "skipped",
                        "message": "Nenhum edificio disponivel para melhorar agora.",
                    }

                resp = await session.upgrade_building(
                    city_id=city_id,
                    position=target["position"],
                    level=target["level"],
                    building_type=target["building"],
                )
                success = session.action_succeeded(resp)
                self.account.last_action = datetime.utcnow()
                await self.db.commit()
                return {
                    "status": "success" if success else "failed",
                    "position": target["position"],
                    "message": (
                        f"Melhoria de {target['name']} (pos {target['position']}) "
                        + ("iniciada." if success else "falhou.")
                    ),
                }
            finally:
                await session.close()

    async def research_next(self) -> dict:
        """Start the next research (Level-2 autopilot), best effort.

        Reads the research advisor, skips when a research is already running or
        nothing is available, otherwise picks an economy-oriented research when
        possible (falling back to the cheapest available) and starts it. If the
        research screen cannot be parsed it returns ``skipped`` with the path of
        the auto-saved page dump so the parser can be refined later.
        """
        async with account_locks.get_lock(self.account.id):
            session = await self._open_session()
            try:
                await session.get_action_token()
                data = await session.get_research()

                if not data.get("parsed"):
                    dump = data.get("dump", "")
                    hint = f" (pagina salva em {dump})" if dump else ""
                    return {
                        "status": "skipped",
                        "message": "Nao consegui ler a tela de pesquisa ainda."
                        + hint,
                    }

                if data.get("in_progress"):
                    return {
                        "status": "skipped",
                        "message": "Pesquisa ja em andamento.",
                    }

                options = data.get("options", [])
                if not options:
                    return {
                        "status": "skipped",
                        "message": "Nenhuma pesquisa disponivel agora.",
                    }

                target = self._pick_research(options)
                resp = await session.start_research(target["type"])
                success = session.action_succeeded(resp)
                self.account.last_action = datetime.utcnow()
                await self.db.commit()
                return {
                    "status": "success" if success else "failed",
                    "message": (
                        f"Pesquisa '{target['name']}' "
                        + ("iniciada." if success else "falhou.")
                    ),
                }
            finally:
                await session.close()

    @staticmethod
    def _pick_research(options: list) -> dict:
        """Prefer economy-oriented research, then the cheapest available."""
        def score(opt: dict) -> tuple:
            name = str(opt.get("name", "")).lower()
            is_economy = any(k in name for k in _RESEARCH_PRIORITY)
            return (0 if is_economy else 1, opt.get("cost") or 0)

        return sorted(options, key=score)[0]

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
