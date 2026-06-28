"""Ikariam game session manager - handles all game interactions."""

import aiohttp
from aiohttp_socks import ProxyConnector
from typing import Optional
import re
import json
from datetime import datetime, timezone

from app.services.ikariam.endpoints import DEFAULT_HEADERS, GAME_INDEX
from app.utils.humanizer import random_delay


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
        self.cookies = cookies
        self.proxy_url = proxy_url
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.session: Optional[aiohttp.ClientSession] = None
        self.action_token: Optional[str] = None
        self.city_ids: list = []
        self.current_city_id: Optional[int] = None

    def _get_connector(self):
        if self.proxy_url:
            return ProxyConnector.from_url(self.proxy_url)
        return aiohttp.TCPConnector(ssl=False)

    async def start(self) -> "IkariamSession":
        connector = self._get_connector()
        cookie_jar = aiohttp.CookieJar()
        self.session = aiohttp.ClientSession(
            connector=connector,
            headers=DEFAULT_HEADERS,
            cookie_jar=cookie_jar,
        )
        # Set cookies
        for name, value in self.cookies.items():
            self.session.cookie_jar.update_cookies({name: value})
        return self

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def _request(self, method: str, path: str, **kwargs) -> str:
        """Make a request to the game server with human-like delay."""
        await random_delay(self.delay_min, self.delay_max)

        url = f"{self.server_url}{path}"
        async with self.session.request(method, url, **kwargs) as resp:
            return await resp.text()

    async def _get(self, params: dict = None) -> str:
        return await self._request("GET", GAME_INDEX, params=params)

    async def _post(self, data: dict = None, params: dict = None) -> str:
        return await self._request("POST", GAME_INDEX, data=data, params=params)

    def _extract_action_token(self, html: str) -> Optional[str]:
        """Extract the actionRequest token from page HTML."""
        match = re.search(r"actionRequest=([a-f0-9]+)", html)
        if match:
            self.action_token = match.group(1)
            return self.action_token

        match = re.search(r"'actionRequest'\s*:\s*'([a-f0-9]+)'", html)
        if match:
            self.action_token = match.group(1)
            return self.action_token

        return None

    def _extract_city_ids(self, html: str) -> list:
        """Extract city IDs from the page HTML."""
        matches = re.findall(r"cityId['\"]?\s*[:=]\s*['\"]?(\d+)", html)
        if matches:
            self.city_ids = list(set(int(m) for m in matches))
        return self.city_ids

    def _extract_json_data(self, html: str) -> dict:
        """Try to extract JSON data from game response."""
        # Ikariam sometimes returns JSON in script tags
        match = re.search(r"var\s+dataSetForView\s*=\s*(\{.*?\});", html, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to parse as JSON directly
        try:
            return json.loads(html)
        except (json.JSONDecodeError, ValueError):
            pass

        return {}

    async def get_city_view(self, city_id: Optional[int] = None) -> dict:
        """Get the city view data."""
        params = {"view": "city"}
        if city_id:
            params["cityId"] = str(city_id)
            self.current_city_id = city_id

        html = await self._get(params)
        self._extract_action_token(html)
        self._extract_city_ids(html)

        return self._parse_city_data(html)

    def _parse_city_data(self, html: str) -> dict:
        """Parse city data from HTML response."""
        data = {
            "resources": self._extract_resources(html),
            "buildings": self._extract_buildings(html),
            "population": self._extract_population(html),
        }
        return data

    def _extract_resources(self, html: str) -> dict:
        """Extract resource amounts from HTML."""
        resources = {}
        patterns = {
            "wood": r"id=['\"]js_GlobalMenu_wood['\"][^>]*>[\s]*([0-9.,]+)",
            "wine": r"id=['\"]js_GlobalMenu_wine['\"][^>]*>[\s]*([0-9.,]+)",
            "marble": r"id=['\"]js_GlobalMenu_marble['\"][^>]*>[\s]*([0-9.,]+)",
            "crystal": r"id=['\"]js_GlobalMenu_crystal['\"][^>]*>[\s]*([0-9.,]+)",
            "sulfur": r"id=['\"]js_GlobalMenu_sulfur['\"][^>]*>[\s]*([0-9.,]+)",
            "gold": r"id=['\"]js_GlobalMenu_gold['\"][^>]*>[\s]*([0-9.,]+)",
        }
        for resource, pattern in patterns.items():
            match = re.search(pattern, html)
            if match:
                value_str = match.group(1).replace(",", "").replace(".", "")
                try:
                    resources[resource] = int(value_str)
                except ValueError:
                    resources[resource] = 0
            else:
                resources[resource] = 0
        return resources

    def _extract_buildings(self, html: str) -> dict:
        """Extract building information from HTML."""
        buildings = {}
        # Pattern for building positions and levels
        matches = re.findall(
            r"position(\d+).*?level['\"]?\s*[:=]\s*['\"]?(\d+).*?building['\"]?\s*[:=]\s*['\"]?(\w+)",
            html,
            re.DOTALL,
        )
        for pos, level, building_type in matches:
            buildings[f"position_{pos}"] = {
                "type": building_type,
                "level": int(level),
            }
        return buildings

    def _extract_population(self, html: str) -> dict:
        """Extract population data from HTML."""
        pop = {}
        pop_match = re.search(r"population['\"]?\s*[:=]\s*['\"]?(\d+)", html)
        if pop_match:
            pop["current"] = int(pop_match.group(1))

        max_match = re.search(r"maxPopulation['\"]?\s*[:=]\s*['\"]?(\d+)", html)
        if max_match:
            pop["max"] = int(max_match.group(1))

        return pop

    async def get_island_view(self, island_id: int) -> dict:
        """Get island view data."""
        params = {"view": "island", "islandId": str(island_id)}
        html = await self._get(params)
        return self._extract_json_data(html)

    async def get_research_view(self) -> dict:
        """Get research/academy data."""
        params = {"view": "research"}
        html = await self._get(params)
        return self._extract_json_data(html)

    async def get_military_view(self) -> dict:
        """Get military/barracks data."""
        params = {"view": "military"}
        html = await self._get(params)
        return self._extract_json_data(html)

    async def donate(self, city_id: int, resource_type: str, amount: int) -> bool:
        """Donate resources to the island (forest or luxury)."""
        if not self.action_token:
            await self.get_city_view(city_id)

        donate_type = "resource" if resource_type == "wood" else "tradegood"
        data = {
            "action": "IslandScreen",
            "function": "donate",
            "donation": str(amount),
            "type": donate_type,
            "cityId": str(city_id),
            "actionRequest": self.action_token,
        }

        result = await self._post(data=data)
        self._extract_action_token(result)
        return "error" not in result.lower()

    async def send_resources(
        self,
        from_city_id: int,
        to_city_id: int,
        wood: int = 0,
        wine: int = 0,
        marble: int = 0,
        crystal: int = 0,
        sulfur: int = 0,
    ) -> bool:
        """Send resources from one city to another."""
        if not self.action_token:
            await self.get_city_view(from_city_id)

        data = {
            "action": "transportOperations",
            "function": "loadTransporters",
            "cityId": str(from_city_id),
            "destinationCityId": str(to_city_id),
            "cargo_resource": str(wood),
            "cargo_tradegood1": str(wine),
            "cargo_tradegood2": str(marble),
            "cargo_tradegood3": str(crystal),
            "cargo_tradegood4": str(sulfur),
            "transpiortSelection": "0",
            "backgroundView": "city",
            "currentCityId": str(from_city_id),
            "actionRequest": self.action_token,
        }

        result = await self._post(data=data)
        self._extract_action_token(result)
        return "error" not in result.lower()

    async def start_building(self, city_id: int, building_position: int) -> bool:
        """Upgrade a building at given position."""
        if not self.action_token:
            await self.get_city_view(city_id)

        data = {
            "action": "CityScreen",
            "function": "upgradeBuilding",
            "cityId": str(city_id),
            "position": str(building_position),
            "backgroundView": "city",
            "currentCityId": str(city_id),
            "actionRequest": self.action_token,
        }

        result = await self._post(data=data)
        self._extract_action_token(result)
        return "error" not in result.lower()

    async def start_piracy(self, city_id: int) -> bool:
        """Start a piracy capture mission."""
        if not self.action_token:
            await self.get_city_view(city_id)

        data = {
            "action": "PirateFortress",
            "function": "startCapture",
            "cityId": str(city_id),
            "backgroundView": "city",
            "currentCityId": str(city_id),
            "actionRequest": self.action_token,
        }

        result = await self._post(data=data)
        self._extract_action_token(result)
        return "error" not in result.lower()

    async def activate_miracle(self, island_id: int, city_id: int) -> bool:
        """Activate a wonder/miracle on an island."""
        if not self.action_token:
            await self.get_city_view(city_id)

        data = {
            "action": "IslandScreen",
            "function": "activateWonder",
            "islandId": str(island_id),
            "cityId": str(city_id),
            "backgroundView": "island",
            "currentCityId": str(city_id),
            "actionRequest": self.action_token,
        }

        result = await self._post(data=data)
        self._extract_action_token(result)
        return "error" not in result.lower()

    async def get_movements(self) -> dict:
        """Get current military/transport movements."""
        params = {"view": "militaryAdvisor"}
        html = await self._get(params)
        return self._extract_json_data(html)

    async def get_marketplace_offers(self, city_id: int) -> dict:
        """Get marketplace offers."""
        params = {"view": "branchOffice", "cityId": str(city_id)}
        html = await self._get(params)
        return self._extract_json_data(html)
