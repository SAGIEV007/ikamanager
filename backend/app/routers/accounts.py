"""API routes for Ikariam account management."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models.account import IkariamAccount
from app.models.proxy import Proxy
from app.utils.crypto import encrypt_password, decrypt_password
from app.services.ikariam.login import IkariamLoginService, GameforgeLoginError
from app.services.ikariam.game_actions import GameActionService

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


class AccountCreate(BaseModel):
    email: str
    password: str
    nickname: str = ""
    group_name: str = "Default"


class AccountUpdate(BaseModel):
    nickname: Optional[str] = None
    group_name: Optional[str] = None
    proxy_id: Optional[int] = None
    is_active: Optional[bool] = None


class AccountResponse(BaseModel):
    id: int
    nickname: str
    email: str
    server_country: str
    server_world: str
    server_number: Optional[int]
    server_language: Optional[str]
    group_name: str
    is_online: bool
    is_active: bool
    status: str
    status_message: Optional[str]
    last_login: Optional[datetime]
    last_action: Optional[datetime]
    gold: float
    population: int
    proxy_id: Optional[int]
    delay_min: float
    delay_max: float
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=list[AccountResponse])
async def list_accounts(
    group: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all Ikariam accounts."""
    query = select(IkariamAccount)
    if group:
        query = query.where(IkariamAccount.group_name == group)
    query = query.order_by(IkariamAccount.created_at.desc())

    result = await db.execute(query)
    accounts = result.scalars().all()
    return accounts


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(account_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific account."""
    result = await db.execute(
        select(IkariamAccount).where(IkariamAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.post("/", response_model=AccountResponse)
async def create_account(data: AccountCreate, db: AsyncSession = Depends(get_db)):
    """Add a new Ikariam account. Only email and password required."""
    encrypted_pw = encrypt_password(data.password)

    nickname = data.nickname or data.email.split("@")[0]

    account = IkariamAccount(
        nickname=nickname,
        email=data.email,
        password_encrypted=encrypted_pw,
        server_country="",
        server_world="",
        group_name=data.group_name,
    )

    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.put("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: int,
    data: AccountUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an account."""
    result = await db.execute(
        select(IkariamAccount).where(IkariamAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(account, key, value)

    await db.commit()
    await db.refresh(account)
    return account


@router.delete("/{account_id}")
async def delete_account(account_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an account."""
    result = await db.execute(
        select(IkariamAccount).where(IkariamAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    await db.delete(account)
    await db.commit()
    return {"detail": "Account deleted"}


class LoginRequest(BaseModel):
    blackbox: str = ""


@router.post("/{account_id}/login")
async def login_account(
    account_id: int,
    login_data: Optional[LoginRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    """Login to Gameforge, auto-detect servers, and enter game world."""
    result = await db.execute(
        select(IkariamAccount).where(IkariamAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Get proxy URL if assigned
    proxy_url = None
    if account.proxy_id:
        proxy_result = await db.execute(
            select(Proxy).where(Proxy.id == account.proxy_id)
        )
        proxy = proxy_result.scalar_one_or_none()
        if proxy:
            proxy_url = proxy.url

    password = decrypt_password(account.password_encrypted)
    blackbox = login_data.blackbox if login_data else ""

    login_service = IkariamLoginService(proxy_url=proxy_url)
    try:
        result_data = await login_service.login(
            email=account.email,
            password=password,
            blackbox=blackbox,
        )

        # Auto-detect server info from game accounts
        game_accounts = result_data.get("accounts", [])
        servers = result_data.get("servers", [])

        # Update account with detected info
        account.is_online = True
        account.status = "online"
        account.last_login = datetime.utcnow()

        if game_accounts:
            first_account = game_accounts[0] if isinstance(game_accounts, list) else list(game_accounts.values())[0] if isinstance(game_accounts, dict) else None
            if first_account:
                # Extract server info from the game account
                server_info = first_account.get("server", {})
                account.server_language = server_info.get("language", "")
                account.server_number = server_info.get("number", 0)
                account.server_country = server_info.get("language", "").upper()
                account.server_world = first_account.get("name", "")
                if first_account.get("name"):
                    account.nickname = first_account.get("name", account.nickname)

        account.status_message = f"Online. {len(game_accounts)} mundo(s) detectado(s)."

        # Store token for game actions
        token = result_data.get("token", "")
        account.session_cookie = token

        await db.commit()
        await db.refresh(account)

        return {
            "status": "success",
            "message": f"Login OK! {len(game_accounts)} mundo(s) encontrado(s).",
            "game_accounts": game_accounts,
            "servers": servers,
        }
    except GameforgeLoginError as e:
        account.status = "error"
        account.status_message = str(e)
        account.is_online = False
        await db.commit()
        raise HTTPException(
            status_code=401,
            detail={
                "message": str(e),
                "error_type": e.error_type,
                "challenge_id": e.challenge_id,
            },
        )
    except Exception as e:
        account.status = "error"
        account.status_message = f"Erro: {str(e)}"
        account.is_online = False
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Erro de conexao: {str(e)}")
    finally:
        await login_service.close()


@router.post("/{account_id}/logout")
async def logout_account(account_id: int, db: AsyncSession = Depends(get_db)):
    """Logout from an Ikariam account."""
    result = await db.execute(
        select(IkariamAccount).where(IkariamAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account.is_online = False
    account.status = "offline"
    account.session_cookie = None
    account.status_message = None

    await db.commit()
    return {"detail": "Logged out"}


@router.post("/{account_id}/enter-world")
async def enter_world(
    account_id: int,
    login_data: Optional[LoginRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    """Enter the game world and get city/building data."""
    result = await db.execute(
        select(IkariamAccount).where(IkariamAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if not account.session_cookie:
        raise HTTPException(status_code=400, detail="Account not logged in. Login first.")

    blackbox = login_data.blackbox if login_data else ""

    # Get proxy URL
    proxy_url = None
    if account.proxy_id:
        proxy_result = await db.execute(
            select(Proxy).where(Proxy.id == account.proxy_id)
        )
        proxy = proxy_result.scalar_one_or_none()
        if proxy:
            proxy_url = proxy.url

    game_service = GameActionService(proxy_url=proxy_url)
    try:
        # Use stored token to get loginLink and enter world
        login_service = IkariamLoginService(proxy_url=proxy_url)
        await login_service.create_session()
        login_service.auth_token = account.session_cookie

        # Get accounts to find the right one
        game_accounts = await login_service._get_accounts()

        if not game_accounts:
            raise HTTPException(status_code=400, detail="No game accounts found")

        first_account = game_accounts[0] if isinstance(game_accounts, list) else list(game_accounts.values())[0]
        account_gf_id = first_account.get("id", "")
        server = first_account.get("server", {})

        # Get login link
        login_url = await login_service.get_login_link(
            account_id=account_gf_id,
            server_language=server.get("language", ""),
            server_number=server.get("number", 1),
            blackbox=blackbox,
        )

        # Enter the world
        world_data = await login_service.login_to_world(login_url)

        account.status_message = "In-game. World loaded."
        account.last_action = datetime.utcnow()
        await db.commit()

        return {
            "status": "success",
            "login_url": login_url,
            "cookies": world_data.get("cookies", {}),
        }
    except GameforgeLoginError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error entering world: {str(e)}")
    finally:
        await login_service.close()


class DonateRequest(BaseModel):
    city_id: int
    resource_type: str = "wood"  # "wood" or luxury resource name
    amount: int = 0  # 0 = donate all available


class BuildRequest(BaseModel):
    city_id: int
    position: int  # building position (0-based)


@router.post("/{account_id}/donate")
async def donate_resources(
    account_id: int,
    data: DonateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Donate resources to the island."""
    result = await db.execute(
        select(IkariamAccount).where(IkariamAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if not account.is_online:
        raise HTTPException(status_code=400, detail="Account is not online. Login first.")

    game_service = GameActionService(account=account, db=db)
    try:
        result_data = await game_service.donate(
            city_id=data.city_id,
            resource_type=data.resource_type,
            amount=data.amount,
        )
        return result_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{account_id}/build")
async def upgrade_building(
    account_id: int,
    data: BuildRequest,
    db: AsyncSession = Depends(get_db),
):
    """Upgrade a building at given position."""
    result = await db.execute(
        select(IkariamAccount).where(IkariamAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if not account.is_online:
        raise HTTPException(status_code=400, detail="Account is not online. Login first.")

    game_service = GameActionService(account=account, db=db)
    try:
        result_data = await game_service.upgrade_building(
            city_id=data.city_id,
            position=data.position,
        )
        return result_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{account_id}/game-data")
async def get_game_data(
    account_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get current game data (cities, resources, buildings)."""
    result = await db.execute(
        select(IkariamAccount).where(IkariamAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if not account.is_online:
        raise HTTPException(status_code=400, detail="Account is not online. Login first.")

    game_service = GameActionService(account=account, db=db)
    try:
        data = await game_service.get_full_game_data()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
