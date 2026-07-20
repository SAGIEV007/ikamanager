"""Ikariam game session manager - handles all in-game interactions.

Parsing is ported from the proven Ikabot project
(https://github.com/Ikabot-Collective/ikabot):

- The list of cities is embedded in the main page HTML as
  ``relatedCityData: JSON.parse('...')``.
- A city's detailed data (buildings, resources) comes from an AJAX request to
  ``index.php?view=city&cityId=...&ajax=1`` and is embedded as
  ``["updateBackgroundData", {...}],["updateTemplateData"``.
- Every POST action needs a fresh ``actionRequest`` token, which is scraped
  from any page via ``actionRequest":"..."``.

These endpoints do NOT require the blackbox token - they only need the
``ikariam`` session cookie obtained after entering the world.
"""

import aiohttp
from aiohttp_socks import ProxyConnector
from typing import Optional
import re
import json
import logging

from app.services.ikariam.endpoints import DEFAULT_HEADERS
from app.utils.humanizer import random_delay

logger = logging.getLogger(__name__)

# Resource order used across the game: wood, wine, marble, crystal, sulfur
RESOURCE_NAMES = ["wood", "wine", "marble", "crystal", "sulfur"]

# Piracy mission (1-9) -> required pirate-fortress building level (from Ikabot).
PIRACY_MISSION_TO_BUILDING_LEVEL = {
    1: 1, 2: 3, 3: 5, 4: 7, 5: 9, 6: 11, 7: 13, 8: 15, 9: 17,
}

# Piracy mission (1-9) -> mission duration in seconds (from Ikabot). The bot must
# wait at least this long after starting before the mission can be repeated.
PIRACY_MISSION_WAITING_TIME = {
    1: 150, 2: 450, 3: 900, 4: 1800, 5: 3600,
    6: 7200, 7: 14400, 8: 28800, 9: 57600,
}


class GameSessionError(Exception):
    """Raised when the game session is invalid/expired or parsing fails."""


class IkariamSession:
    """Manages an active session with an Ikariam game world."""

    def __init__(
        self,
        server_url: str,
        cookies: dict,
        proxy_url: Optional[str] = None,
        delay_min: float = 2.0,
        delay_max: float = 6.0,
    ):
        self.server_url = server_url.rstrip("/")
        self.base_url = f"{self.server_url}/index.php"
        self.cookies = cookies
        self.proxy_url = proxy_url
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.session: Optional[aiohttp.ClientSession] = None
        self.action_token: Optional[str] = None

    def _get_connector(self):
        if self.proxy_url:
            return ProxyConnector.from_url(self.proxy_url)
        return aiohttp.TCPConnector(ssl=False)

    async def start(self) -> "IkariamSession":
        connector = self._get_connector()
        self.session = aiohttp.ClientSession(
            connector=connector,
            headers=DEFAULT_HEADERS,
        )
        for name, value in self.cookies.items():
            self.session.cookie_jar.update_cookies({name: value})
        return self

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

    # ------------------------------------------------------------------ #
    # Low level HTTP
    # ------------------------------------------------------------------ #
    def _update_token(self, html: str) -> None:
        """Scrape the latest ``actionRequest`` token from a response and store it.

        The game rotates this token on every request, so (like Ikabot) we keep it
        current from each response and re-inject it into the next request.
        """
        match = re.search(r'actionRequest"?:\s*"(.*?)"', html)
        if match:
            self.action_token = match.group(1)

    async def _get(self, query: str = "", humanize: bool = True) -> str:
        if humanize:
            await random_delay(self.delay_min, self.delay_max)
        url = self.base_url
        if query:
            url = f"{self.base_url}?{query}"
        async with self.session.get(url, allow_redirects=True) as resp:
            html = await resp.text()
        self._update_token(html)
        return html

    async def _post(self, query: str) -> str:
        await random_delay(self.delay_min, self.delay_max)
        url = f"{self.base_url}?{query}"
        async with self.session.post(url) as resp:
            html = await resp.text()
        self._update_token(html)
        return html

    async def _post_params(self, params: dict) -> str:
        await random_delay(self.delay_min, self.delay_max)
        async with self.session.post(self.base_url, data=params) as resp:
            html = await resp.text()
        self._update_token(html)
        return html

    async def _post_query(self, params: dict) -> str:
        """POST with params in the URL query string and no ``index.php`` in the
        path (Ikabot's ``session.post(params=params, noIndex=True)``). The
        piracy captcha resubmit requires exactly this form."""
        await random_delay(self.delay_min, self.delay_max)
        url = f"{self.server_url}/"
        async with self.session.post(url, params=params) as resp:
            html = await resp.text()
        self._update_token(html)
        return html

    async def _get_bytes(self, query: str) -> bytes:
        await random_delay(self.delay_min, self.delay_max)
        url = f"{self.base_url}?{query}"
        async with self.session.get(url, allow_redirects=True) as resp:
            return await resp.read()

    def _is_expired(self, html: str) -> bool:
        return "index.php?logout" in html or "lobby.ikariam.gameforge.com" in html[:2000]

    async def get_action_token(self) -> str:
        """Scrape a fresh actionRequest token from the main page."""
        html = await self._get(humanize=False)
        if self._is_expired(html):
            raise GameSessionError("Sessao do jogo expirada. Faca login novamente.")
        match = re.search(r'actionRequest"?:\s*"(.*?)"', html)
        if not match:
            raise GameSessionError(
                "Nao foi possivel obter o token de acao (actionRequest)."
            )
        self.action_token = match.group(1)
        return self.action_token

    # ------------------------------------------------------------------ #
    # City list
    # ------------------------------------------------------------------ #
    async def get_cities(self) -> list:
        """Return the list of the player's own cities.

        Each entry: {id, name, coords, tradegood, relationship}
        """
        html = await self._get()
        if self._is_expired(html):
            raise GameSessionError("Sessao do jogo expirada. Faca login novamente.")

        match = re.search(
            r'relatedCityData:\s*JSON\.parse\(\'(.+?),\\"additionalInfo', html
        )
        if not match:
            raise GameSessionError(
                "Nao foi possivel ler a lista de cidades. "
                "O jogo pode ter mudado o formato da pagina."
            )

        raw = match.group(1) + "}"
        raw = raw.replace("\\", "").replace("city_", "")
        try:
            data = json.loads(raw, strict=False)
        except json.JSONDecodeError as e:
            raise GameSessionError(f"Erro ao interpretar as cidades: {e}")

        cities = []
        for city_id, info in data.items():
            if not isinstance(info, dict):
                continue
            cities.append(
                {
                    "id": str(city_id),
                    "name": info.get("name", ""),
                    "coords": info.get("coords", "").strip(),
                    "tradegood": info.get("tradegood", ""),
                    "relationship": info.get("relationship", ""),
                }
            )
        # Own cities first
        cities.sort(key=lambda c: (c["relationship"] != "ownCity", c["id"]))
        return cities

    def own_city_ids(self, cities: list) -> list:
        return [c["id"] for c in cities if c["relationship"] == "ownCity"]

    # ------------------------------------------------------------------ #
    # City detail
    # ------------------------------------------------------------------ #
    async def get_city(self, city_id) -> dict:
        """Fetch and parse a single city's detailed data (buildings/resources).

        Ikabot fetches the plain city page (``?view=city&cityId=X``); the same
        ``updateBackgroundData`` blob is embedded there. As a fallback we retry
        with an explicit AJAX request (``X-Requested-With`` header) which returns
        the JSON array directly.
        """
        # The AJAX request (with X-Requested-With) returns the clean JSON array
        # that the regex expects. Fall back to the plain page if needed.
        ajax_html = await self._get_ajax(
            f"view=city&cityId={city_id}&backgroundView=city"
            f"&currentCityId={city_id}"
            f"&actionRequest={self.action_token or 'REQUESTID'}&ajax=1"
        )
        if re.search(r'"updateBackgroundData"', ajax_html):
            return self._parse_city(ajax_html)

        plain_html = await self._get(f"view=city&cityId={city_id}")
        if re.search(r'"updateBackgroundData"', plain_html):
            return self._parse_city(plain_html)

        # Neither worked - dump whichever we got for diagnosis
        return self._parse_city(ajax_html or plain_html)

    async def _get_ajax(self, query: str) -> str:
        await random_delay(self.delay_min, self.delay_max)
        url = f"{self.base_url}?{query}"
        headers = {"X-Requested-With": "XMLHttpRequest"}
        async with self.session.get(url, headers=headers, allow_redirects=True) as resp:
            return await resp.text()

    def _dump_debug(self, html: str, name: str = "debug_city_response.html") -> str:
        """Persist a raw response so parsing issues can be diagnosed."""
        try:
            import os

            path = os.path.join(os.getcwd(), name)
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            return path
        except OSError:
            return ""

    def _parse_city(self, html: str) -> dict:
        match = re.search(
            r'"updateBackgroundData",\s?([\s\S]*?)\],\["updateTemplateData"', html
        )
        if not match:
            # Try a couple of tolerant fallbacks before giving up
            match = re.search(
                r'updateBackgroundData"?\s*,\s*(\{[\s\S]*?\})\s*\]\s*,\s*\[\s*"?updateTemplateData',
                html,
            )
        if not match:
            path = self._dump_debug(html)
            hint = f" (resposta salva em {path})" if path else ""
            raise GameSessionError(
                "Nao foi possivel ler os dados da cidade (edificios/recursos)." + hint
            )
        try:
            city = json.loads(match.group(1), strict=False)
        except json.JSONDecodeError as e:
            raise GameSessionError(f"Erro ao interpretar a cidade: {e}")

        positions = []
        for i, position in enumerate(city.get("position", [])):
            building = position.get("building", "")
            name = position.get("name", "")
            is_empty = "buildingGround " in building
            positions.append(
                {
                    "position": i,
                    "name": "empty" if is_empty else name,
                    "building": "empty" if is_empty else building,
                    "level": int(position["level"]) if str(position.get("level", "")).isdigit() else None,
                    "canUpgrade": position.get("canUpgrade"),
                    "isMaxLevel": position.get("isMaxLevel"),
                    "isBusy": "constructionSite" in building,
                }
            )

        resources = self._extract_resources(html)

        return {
            "id": str(city.get("id", "")),
            "name": city.get("name", ""),
            "islandId": str(city.get("islandId", "")),
            "islandX": city.get("islandXCoord", ""),
            "islandY": city.get("islandYCoord", ""),
            "resources": resources,
            "positions": positions,
        }

    def _extract_resources(self, html: str) -> dict:
        """Extract current stored resources [wood, wine, marble, crystal, sulfur]."""
        match = re.search(
            r'\\"resource\\":(\d+),\\"2\\":(\d+),\\"1\\":(\d+),\\"4\\":(\d+),\\"3\\":(\d+)}',
            html,
        )
        if not match:
            return {name: 0 for name in RESOURCE_NAMES}
        wood = int(match.group(1))
        marble = int(match.group(2))
        wine = int(match.group(3))
        sulfur = int(match.group(4))
        crystal = int(match.group(5))
        return {
            "wood": wood,
            "wine": wine,
            "marble": marble,
            "crystal": crystal,
            "sulfur": sulfur,
        }

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #
    async def donate(self, city_id, island_id, resource_type: str, amount: int) -> str:
        """Donate resources to the island (forest 'resource' or luxury 'tradegood')."""
        await self.get_action_token()
        donate_type = "resource" if resource_type == "wood" else "tradegood"
        query = (
            f"islandId={island_id}&type={donate_type}&action=IslandScreen"
            f"&function=donate&donation={int(amount)}&backgroundView=island"
            f"&templateView=resource&actionRequest={self.action_token}&ajax=1"
        )
        return await self._post(query)

    async def upgrade_building(self, city_id, position: int, level, building_type: str) -> str:
        """Upgrade an existing building at a position."""
        await self.get_action_token()
        query = (
            f"action=UpgradeExistingBuilding&actionRequest={self.action_token}"
            f"&cityId={city_id}&position={int(position)}&level={level}"
            f"&activeTab=tabSendTransporter&backgroundView=city"
            f"&currentCityId={city_id}&templateView={building_type}&ajax=1"
        )
        return await self._post(query)

    # ------------------------------------------------------------------ #
    # Research (Academy) - best effort
    # ------------------------------------------------------------------ #
    async def get_research(self) -> dict:
        """Best-effort read of the research advisor screen.

        Ikariam embeds the research tree either as a ``js_ResearchGraphViewData``
        JSON blob or inside the ``updateBackgroundData`` AJAX array. We try
        several tolerant patterns and, if none match, dump the page for later
        diagnosis instead of guessing.

        Returns a dict:
            {"parsed": bool, "in_progress": bool,
             "options": [{"type": str, "name": str, "cost": int}],
             "dump": str}
        """
        # Try, in order, the request forms that actually carry the research
        # tree. The plain AJAX header refresh does NOT contain it (it only has
        # the top bar / advisor menu links), so we must load the advisor view
        # itself and, failing that, the full page whose inline script embeds
        # the tree.
        attempts: list[str] = []
        for html in (
            await self._get_ajax("view=researchAdvisor&ajax=1"),
            await self._get("view=researchAdvisor"),
        ):
            if self._is_expired(html):
                raise GameSessionError(
                    "Sessao do jogo expirada. Faca login novamente."
                )
            attempts.append(html)
            if self._has_research_tree(html):
                return self._parse_research(html)

        # None carried the tree: parse the richest response (may still work via
        # tolerant patterns) and, if it doesn't, dump it for later refinement.
        best = max(attempts, key=len) if attempts else ""
        return self._parse_research(best)

    def _has_research_tree(self, html: str) -> bool:
        """Only trust a response that carries the actual research advisor data,
        not the advisor menu link that appears in every page header."""
        return bool(self._research_template(html))

    def _research_template(self, html: str) -> dict:
        """Return the ``updateTemplateData`` dict from a research-advisor AJAX
        response (a JSON array), or ``{}`` when it isn't present."""
        stripped = html.lstrip()
        if not stripped.startswith("["):
            return {}
        try:
            arr = json.loads(html, strict=False)
        except json.JSONDecodeError:
            return {}
        for entry in arr:
            if (
                isinstance(entry, list)
                and len(entry) >= 2
                and entry[0] == "updateTemplateData"
                and isinstance(entry[1], dict)
            ):
                td = entry[1]
                if any(k.startswith("js_researchAdvisor") for k in td):
                    return td
        return {}

    def _parse_research(self, html: str) -> dict:
        """Parse the research advisor screen.

        Ikariam's research advisor groups researches into five categories
        (``economy``, ``seafaring``, ``knowledge``, ``military``, ``mythology``).
        Each category exposes its *next* research (name + cost) and whether it is
        affordable now (``addClass == "red"`` means not enough research points).
        Researching happens per category via ``doResearch&type=<category>``,
        which unlocks that category's next item.
        """
        td = self._research_template(html)
        if not td:
            path = self._dump_debug(html, "debug_research.html")
            return {
                "parsed": False,
                "in_progress": False,
                "options": [],
                "dump": path,
            }

        options = self._extract_research_nodes(td)
        return {
            "parsed": True,
            # Research unlocks are instantaneous in Ikariam (points accrue over
            # time via scientists), so there is no "ongoing research" state.
            "in_progress": False,
            "options": options,
            "dump": "",
        }

    def _extract_research_nodes(self, td: dict) -> list:
        """Collect the next researchable item of each category from the parsed
        ``updateTemplateData`` dict.

        Returns a list of dicts::

            {"type": "economy", "name": "Recolha ...", "category": "Economia",
             "cost": 990, "affordable": True}
        """
        options: list = []
        for n in range(0, 12):
            change = td.get(f"js_researchAdvisorChangeResearchType{n}")
            if not isinstance(change, dict):
                continue
            match = re.search(
                r"researchType=(\w+)", str(change.get("ajaxrequest", ""))
            )
            if not match:
                continue
            category = match.group(1)
            cat_name = str(
                td.get(f"js_researchAdvisorChangeResearchTypeTxt{n}", category)
            )
            next_name = str(
                td.get(f"js_researchAdvisorNextResearchName{n}", "")
            ).strip()
            if not next_name:
                # Category fully researched / no next item available.
                continue
            cost_info = td.get(f"js_researchAdvisorNextResearchCost{n}")
            cost_text = ""
            affordable = True
            if isinstance(cost_info, dict):
                cost_text = str(cost_info.get("text", ""))
                affordable = cost_info.get("addClass") != "red"
            options.append(
                {
                    "type": category,
                    "name": next_name,
                    "category": cat_name,
                    "cost": self._digits_to_int(cost_text),
                    "affordable": affordable,
                }
            )
        return options

    @staticmethod
    def _digits_to_int(text: str) -> int:
        """Parse a localized number like ``"2.048"`` / ``"2,236"`` into an int
        by keeping only the digits (thousands separators are dropped)."""
        digits = re.sub(r"[^0-9]", "", text or "")
        return int(digits) if digits else 0

    async def start_research(self, research_type: str) -> str:
        """Unlock the next research of a category (``economy``/``seafaring``/
        ``knowledge``/``military``/``mythology``), mirroring the in-game
        ``doResearch`` link."""
        await self.get_action_token()
        query = (
            f"action=Advisor&function=doResearch&actionRequest={self.action_token}"
            f"&type={research_type}&backgroundView=researchAdvisor"
            f"&templateView=researchAdvisor&ajax=1"
        )
        return await self._post(query)

    async def get_captcha_image(self) -> bytes:
        """Fetch the current piracy captcha image (PNG bytes)."""
        return await self._get_bytes("action=Options&function=createCaptcha")

    async def start_piracy(
        self, city_id, mission_level: int = 1, captcha_solver=None
    ) -> str:
        """Start a piracy capture mission.

        ``mission_level`` (1-9) maps to a pirate-fortress building level, exactly
        like Ikabot's ``piracyMissionToBuildingLevel``:
        1=2m30s, 2=7m30s, 3=15m, 4=30m, 5=1h, 6=2h, 7=4h, 8=8h, 9=16h.

        ``captcha_solver`` is an optional async callable ``(image_bytes) -> str``.
        When the game asks for a captcha and a solver is provided, it is solved
        and the mission is resubmitted (up to a few attempts).
        """
        building_level = PIRACY_MISSION_TO_BUILDING_LEVEL.get(int(mission_level), 1)
        await self.get_action_token()
        # The game requires "looking at" the origin town before dispatching.
        await self._get(f"view=city&cityId={city_id}")
        query = (
            f"action=PiracyScreen&function=capture&buildingLevel={building_level}"
            f"&view=pirateFortress&cityId={city_id}&position=17"
            f"&activeTab=tabBootyQuest&backgroundView=city&currentCityId={city_id}"
            f"&templateView=pirateFortress&actionRequest={self.action_token}&ajax=1"
        )
        html = await self._post(query)
        if "function=createCaptcha" not in html:
            return html

        if captcha_solver is None:
            raise GameSessionError(
                "A pirataria pediu captcha e nenhum resolvedor esta configurado. "
                "Ative o resolvedor local (onnxruntime) ou a chave 2Captcha."
            )

        # Solve the captcha and resubmit. The local model is imperfect per image,
        # but each retry pulls a fresh captcha, so many attempts (like Ikabot's 20)
        # eventually land a correct read.
        attempts = []
        for attempt in range(20):
            image = await self.get_captcha_image()
            solution = await captcha_solver(image)
            logger.info("Piracy captcha attempt %s: solver returned %r", attempt + 1, solution)
            attempts.append(solution)
            # Look at the origin town again before resubmitting (Ikabot POSTs here).
            await self._post(f"view=city&cityId={city_id}")
            # Ikabot fetches a fresh actionRequest token right before each submit
            # (its post() calls __token() -> a new GET). The token rotates per
            # request, so a stale one is rejected.
            await self.get_action_token()
            params = {
                "action": "PiracyScreen",
                "function": "capture",
                "cityId": str(city_id),
                "position": "17",
                "captchaNeeded": "1",
                "buildingLevel": str(building_level),
                "captcha": solution,
                "activeTab": "tabBootyQuest",
                "backgroundView": "city",
                "currentCityId": str(city_id),
                "templateView": "pirateFortress",
                "actionRequest": self.action_token,
                "ajax": "1",
            }
            html = await self._post_query(params)
            # Crew still in town => request rejected (wrong captcha); retry.
            if '"showPirateFortressShip":1' not in html:
                return html
        raise GameSessionError(
            "Nao foi possivel resolver o captcha apos varias tentativas "
            f"({len(attempts)}). O modelo local errou a leitura; considere usar "
            "o 2Captcha (pago) nas configuracoes para maior precisao."
        )

    @staticmethod
    def action_succeeded(resp: str) -> bool:
        """Best-effort check that a POST action was accepted by the game."""
        low = resp.lower()
        if "providefeedback" in low:
            # Feedback type 10 = success, 11 = rejected (ikabot convention)
            try:
                data = json.loads(resp, strict=False)
                for r in data:
                    if isinstance(r, list) and r and r[0] == "provideFeedback":
                        for fb in r[1]:
                            if fb.get("type") == 11:
                                return False
                        return True
            except (json.JSONDecodeError, TypeError, KeyError):
                pass
        return "error" not in low
