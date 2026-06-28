"""Ikariam Gameforge login service."""

import aiohttp
from aiohttp_socks import ProxyConnector
from typing import Optional
import json
import re

from app.services.ikariam.endpoints import (
    PIXELZIRKUS_URL,
    LOBBY_LOGIN,
    LOBBY_ACCOUNTS,
    LOBBY_SERVERS,
    LOBBY_LOGIN_LINK,
    LOBBY_HEADERS,
    DEFAULT_HEADERS,
)
from app.utils.humanizer import random_delay


class GameforgeLoginError(Exception):
    pass


class IkariamLoginService:
    """Handles the Gameforge lobby login flow."""

    def __init__(self, proxy_url: Optional[str] = None):
        self.proxy_url = proxy_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.cookies: dict = {}
        self.accounts: list = []
        self.servers: list = []

    def _get_connector(self):
        if self.proxy_url:
            return ProxyConnector.from_url(self.proxy_url)
        return aiohttp.TCPConnector(ssl=False)

    async def create_session(self) -> aiohttp.ClientSession:
        connector = self._get_connector()
        self.session = aiohttp.ClientSession(
            connector=connector,
            headers=DEFAULT_HEADERS,
        )
        return self.session

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def login(self, email: str, password: str) -> dict:
        """
        Full Gameforge login flow:
        1. Get initial cookie from pixelzirkus
        2. Login with email/password
        3. Get accounts list
        4. Return accounts and session data
        """
        if not self.session:
            await self.create_session()

        # Step 1: Get initial tracking cookie
        await self._get_initial_cookie()
        await random_delay(1.0, 2.0)

        # Step 2: Login with credentials
        await self._login_credentials(email, password)
        await random_delay(1.0, 2.0)

        # Step 3: Get available accounts
        accounts = await self._get_accounts()
        await random_delay(0.5, 1.0)

        # Step 4: Get servers info
        servers = await self._get_servers()

        return {
            "accounts": accounts,
            "servers": servers,
            "cookies": dict(self.session.cookie_jar.filter_cookies("https://lobby.ikariam.gameforge.com")),
        }

    async def _get_initial_cookie(self):
        """Step 1: POST to pixelzirkus to get tracking cookie."""
        try:
            async with self.session.post(
                PIXELZIRKUS_URL,
                data={"product": "ikariam"},
            ) as resp:
                if resp.status not in (200, 204, 302):
                    pass  # Some servers return different codes, continue anyway
        except Exception:
            pass  # Non-critical, continue

    async def _login_credentials(self, email: str, password: str):
        """Step 2: Login with email and password to Gameforge lobby."""
        payload = {
            "mail": email,
            "password": password,
            "locale": "en_GB",
        }

        async with self.session.post(
            LOBBY_LOGIN,
            json=payload,
            headers=LOBBY_HEADERS,
        ) as resp:
            if resp.status == 400:
                raise GameforgeLoginError("Invalid email or password")
            if resp.status == 403:
                raise GameforgeLoginError("Account blocked or captcha required")
            if resp.status not in (200, 201):
                text = await resp.text()
                raise GameforgeLoginError(f"Login failed with status {resp.status}: {text}")

    async def _get_accounts(self) -> list:
        """Step 3: Get all game accounts for this email."""
        async with self.session.get(
            LOBBY_ACCOUNTS,
            headers=LOBBY_HEADERS,
        ) as resp:
            if resp.status != 200:
                raise GameforgeLoginError(f"Failed to get accounts: {resp.status}")
            data = await resp.json()
            self.accounts = data if isinstance(data, list) else list(data.values())
            return self.accounts

    async def _get_servers(self) -> list:
        """Step 4: Get available servers."""
        async with self.session.get(
            LOBBY_SERVERS,
            headers=LOBBY_HEADERS,
        ) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            self.servers = data if isinstance(data, list) else list(data.values())
            return self.servers

    async def get_login_link(self, account_id: str, server_language: str, server_number: int) -> str:
        """Step 5: Get the login link for a specific game world."""
        if not self.session:
            raise GameforgeLoginError("Not logged in")

        params = {
            "id": account_id,
            "server[language]": server_language,
            "server[number]": str(server_number),
        }

        async with self.session.get(
            LOBBY_LOGIN_LINK,
            params=params,
            headers=LOBBY_HEADERS,
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise GameforgeLoginError(f"Failed to get login link: {resp.status} - {text}")
            data = await resp.json()
            return data.get("url", "")

    async def login_to_world(self, login_url: str) -> dict:
        """Step 6: Use the login link to enter the game world. Returns session cookies."""
        async with self.session.get(
            login_url,
            headers=DEFAULT_HEADERS,
            allow_redirects=True,
        ) as resp:
            if resp.status != 200:
                raise GameforgeLoginError(f"Failed to login to world: {resp.status}")

            # Extract cookies from the response
            cookies = {}
            for cookie in self.session.cookie_jar:
                cookies[cookie.key] = cookie.value

            # Try to extract the ikariam session cookie
            text = await resp.text()

            return {
                "cookies": cookies,
                "html": text[:5000],  # First part of response for parsing
            }
