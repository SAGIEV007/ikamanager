"""Game action service - executes real game actions using active session."""

import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.services.ikariam.login import IkariamLoginService, GameforgeLoginError
from app.services.ikariam.session import IkariamSession
from app.models.account import IkariamAccount
from app.utils.crypto import decrypt_password

logger = logging.getLogger(__name__)


class GameActionService:
    """Executes game actions for a logged-in account."""

    def __init__(self, account: IkariamAccount, db: AsyncSession, proxy_url: Optional[str] = None):
        self.account = account
        self.db = db
        self.proxy_url = proxy_url
        self.login_service: Optional[IkariamLoginService] = None
        self.game_session: Optional[IkariamSession] = None

    async def _ensure_login(self) -> IkariamLoginService:
        """Ensure we have a valid login service with token."""
        if not self.account.session_cookie:
            raise GameforgeLoginError("Account not logged in")

        self.login_service = IkariamLoginService(proxy_url=self.proxy_url)
        await self.login_service.create_session()
        self.login_service.auth_token = self.account.session_cookie
        return self.login_service

    async def _enter_world(self, blackbox: str = "") -> IkariamSession:
        """Enter the game world and get an active session."""
        login_svc = await self._ensure_login()

        # Get game accounts
        accounts = await login_svc._get_accounts()
        if not accounts:
            raise GameforgeLoginError("No game accounts found")

        first_account = accounts[0] if isinstance(accounts, list) else list(accounts.values())[0]
        account_id = first_account.get("id", "")
        server = first_account.get("server", {})

        # Get login link
        login_url = await login_svc.get_login_link(
            account_id=account_id,
            server_language=server.get("language", ""),
            server_number=server.get("number", 1),
            blackbox=blackbox,
        )

        # Enter world
        world_data = await login_svc.login_to_world(login_url)

        # Create game session
        server_url = f"https://s{server.get('number', 1)}-{server.get('language', 'en')}.ikariam.gameforge.com"
        self.game_session = IkariamSession(
            server_url=server_url,
            cookies=world_data.get("cookies", {}),
            proxy_url=self.proxy_url,
        )
        await self.game_session.start()
        return self.game_session

    async def get_full_game_data(self) -> dict:
        """Get cities, resources, and buildings for the account."""
        session = await self._enter_world()
        try:
            city_data = await session.get_city_view()
            return {
                "cities": session.city_ids,
                "current_city": session.current_city_id,
                "resources": city_data.get("resources", {}),
                "buildings": city_data.get("buildings", {}),
                "population": city_data.get("population", {}),
            }
        finally:
            await session.close()
            if self.login_service:
                await self.login_service.close()

    async def donate(self, city_id: int, resource_type: str, amount: int) -> dict:
        """Donate resources to the island."""
        session = await self._enter_world()
        try:
            success = await session.donate(city_id, resource_type, amount)
            self.account.last_action = datetime.utcnow()
            await self.db.commit()
            return {
                "status": "success" if success else "failed",
                "message": f"Donation of {amount} {resource_type} {'completed' if success else 'failed'}",
            }
        finally:
            await session.close()
            if self.login_service:
                await self.login_service.close()

    async def upgrade_building(self, city_id: int, position: int) -> dict:
        """Upgrade a building."""
        session = await self._enter_world()
        try:
            success = await session.start_building(city_id, position)
            self.account.last_action = datetime.utcnow()
            await self.db.commit()
            return {
                "status": "success" if success else "failed",
                "message": f"Building upgrade at position {position} {'started' if success else 'failed'}",
            }
        finally:
            await session.close()
            if self.login_service:
                await self.login_service.close()

    async def start_piracy(self, city_id: int) -> dict:
        """Start piracy capture."""
        session = await self._enter_world()
        try:
            success = await session.start_piracy(city_id)
            self.account.last_action = datetime.utcnow()
            await self.db.commit()
            return {
                "status": "success" if success else "failed",
                "message": f"Piracy {'started' if success else 'failed'}",
            }
        finally:
            await session.close()
            if self.login_service:
                await self.login_service.close()
