"""API routes for Ikariam account management."""

import logging
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
from app.services.ikariam.game_actions import GameActionService, serialize_session
from app.services.ikariam.session import GameSessionError
from app.services.ikariam.captcha import CaptchaError
from app.services.ikariam import auto_piracy

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


def _find_server_name(servers: list, number: int, language: str) -> str:
    """Look up the human-readable world name from the lobby servers list."""
    for srv in servers or []:
        if not isinstance(srv, dict):
            continue
        if srv.get("number") == number and srv.get("language") == language:
            return srv.get("name") or srv.get("serverName") or ""
    return ""


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
    gf_token: str = ""  # manual gf-token-production cookie (fallback)


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
    gf_token = login_data.gf_token if login_data else ""

    login_service = IkariamLoginService(proxy_url=proxy_url)
    try:
        result_data = await login_service.login(
            email=account.email,
            password=password,
            blackbox=blackbox,
            gf_token=gf_token,
        )

        # Auto-detect server info from game accounts
        game_accounts = result_data.get("accounts", [])
        servers = result_data.get("servers", [])
        token = result_data.get("token", "")

        account.is_online = True
        account.status = "online"
        account.last_login = datetime.utcnow()

        first_account = None
        if game_accounts:
            first_account = (
                game_accounts[0]
                if isinstance(game_accounts, list)
                else list(game_accounts.values())[0]
            )

        if not first_account:
            account.session_cookie = serialize_session(token, {}, "")
            account.status_message = "Login OK, mas nenhum mundo encontrado nesta conta."
            await db.commit()
            await db.refresh(account)
            return {
                "status": "success",
                "message": "Login OK, mas nenhum mundo foi encontrado.",
                "game_accounts": game_accounts,
            }

        server_info = first_account.get("server", {})
        server_language = server_info.get("language", "")
        server_number = server_info.get("number", 0)
        account_gf_id = first_account.get("id", "")

        # Player nickname is the lobby account name; the world name comes from
        # the servers list (fall back to the language code if not found).
        world_name = _find_server_name(servers, server_number, server_language)
        player_name = first_account.get("name", "") or account.nickname

        account.server_language = server_language
        account.server_number = server_number
        account.server_country = server_language.upper()
        account.server_world = world_name or f"s{server_number}-{server_language}"
        account.nickname = player_name

        # Enter the game world to obtain the in-game session cookie.
        world_error = None
        try:
            login_url = await login_service.get_login_link(
                account_id=account_gf_id,
                server_language=server_language,
                server_number=server_number,
                blackbox=blackbox,
            )
            world_data = await login_service.login_to_world(login_url)
            account.session_cookie = serialize_session(
                token,
                world_data.get("cookies", {}),
                world_data.get("server_url", ""),
            )
        except Exception as e:  # noqa: BLE001 - degrade gracefully
            world_error = str(e)
            account.session_cookie = serialize_session(token, {}, "")

        if world_error:
            account.status_message = (
                f"Logado, mas nao entrou no mundo: {world_error}"
            )
        else:
            account.status_message = f"Online no mundo {account.server_world}."

        await db.commit()
        await db.refresh(account)

        return {
            "status": "success",
            "message": (
                f"Login OK! Mundo: {account.server_world} "
                f"(jogador: {account.nickname})."
            ),
            "server_world": account.server_world,
            "world_error": world_error,
            "game_accounts": game_accounts,
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


async def _get_proxy_url(account: IkariamAccount, db: AsyncSession) -> Optional[str]:
    if not account.proxy_id:
        return None
    proxy_result = await db.execute(select(Proxy).where(Proxy.id == account.proxy_id))
    proxy = proxy_result.scalar_one_or_none()
    return proxy.url if proxy else None


class DonateRequest(BaseModel):
    city_id: str
    resource_type: str = "wood"  # "wood" (forest) or "tradegood" (luxury)
    amount: int = 0


class BuildRequest(BaseModel):
    city_id: str
    position: int  # building position (0-based)


class PiracyRequest(BaseModel):
    city_id: str
    mission_level: int = 1


class AutoPiracyRequest(BaseModel):
    city_id: str
    mission_level: int = 1
    runs: int = 10
    extra_wait_max: int = 30  # extra random seconds added after each mission


@router.get("/{account_id}/cities")
async def list_cities(account_id: int, db: AsyncSession = Depends(get_db)):
    """List the player's cities (name + coordinates) for the logged-in world."""
    result = await db.execute(
        select(IkariamAccount).where(IkariamAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if not account.is_online:
        raise HTTPException(status_code=400, detail="Conta offline. Faca login primeiro.")

    proxy_url = await _get_proxy_url(account, db)
    game_service = GameActionService(account=account, db=db, proxy_url=proxy_url)
    try:
        cities = await game_service.get_cities()
        return {"cities": cities}
    except GameSessionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@router.get("/{account_id}/game-data")
async def get_game_data(account_id: int, db: AsyncSession = Depends(get_db)):
    """Get cities with detailed resources and buildings."""
    result = await db.execute(
        select(IkariamAccount).where(IkariamAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if not account.is_online:
        raise HTTPException(status_code=400, detail="Conta offline. Faca login primeiro.")

    proxy_url = await _get_proxy_url(account, db)
    game_service = GameActionService(account=account, db=db, proxy_url=proxy_url)
    try:
        return await game_service.get_full_game_data()
    except GameSessionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@router.get("/{account_id}/city/{city_id}")
async def get_city_detail(
    account_id: int, city_id: str, db: AsyncSession = Depends(get_db)
):
    """Get one city's detailed data (buildings/resources)."""
    result = await db.execute(
        select(IkariamAccount).where(IkariamAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if not account.is_online:
        raise HTTPException(status_code=400, detail="Conta offline. Faca login primeiro.")

    proxy_url = await _get_proxy_url(account, db)
    game_service = GameActionService(account=account, db=db, proxy_url=proxy_url)
    try:
        return await game_service.get_city(city_id)
    except GameSessionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@router.post("/{account_id}/donate")
async def donate_resources(
    account_id: int, data: DonateRequest, db: AsyncSession = Depends(get_db)
):
    """Donate resources to the island."""
    result = await db.execute(
        select(IkariamAccount).where(IkariamAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if not account.is_online:
        raise HTTPException(status_code=400, detail="Conta offline. Faca login primeiro.")

    proxy_url = await _get_proxy_url(account, db)
    game_service = GameActionService(account=account, db=db, proxy_url=proxy_url)
    try:
        return await game_service.donate(
            city_id=data.city_id,
            resource_type=data.resource_type,
            amount=data.amount,
        )
    except GameSessionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@router.post("/{account_id}/build")
async def upgrade_building(
    account_id: int, data: BuildRequest, db: AsyncSession = Depends(get_db)
):
    """Upgrade a building at given position."""
    result = await db.execute(
        select(IkariamAccount).where(IkariamAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if not account.is_online:
        raise HTTPException(status_code=400, detail="Conta offline. Faca login primeiro.")

    proxy_url = await _get_proxy_url(account, db)
    game_service = GameActionService(account=account, db=db, proxy_url=proxy_url)
    try:
        return await game_service.upgrade_building(
            city_id=data.city_id,
            position=data.position,
        )
    except GameSessionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@router.post("/{account_id}/piracy")
async def start_piracy(
    account_id: int, data: PiracyRequest, db: AsyncSession = Depends(get_db)
):
    """Start a piracy capture mission."""
    result = await db.execute(
        select(IkariamAccount).where(IkariamAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if not account.is_online:
        raise HTTPException(status_code=400, detail="Conta offline. Faca login primeiro.")

    proxy_url = await _get_proxy_url(account, db)
    game_service = GameActionService(account=account, db=db, proxy_url=proxy_url)
    try:
        return await game_service.start_piracy(
            city_id=data.city_id, mission_level=data.mission_level
        )
    except GameSessionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except CaptchaError as e:
        raise HTTPException(status_code=400, detail=f"Captcha: {str(e)}")
    except Exception as e:
        logger.exception("Piracy failed for account %s", account_id)
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@router.post("/{account_id}/piracy/auto/start")
async def start_auto_piracy(
    account_id: int, data: AutoPiracyRequest, db: AsyncSession = Depends(get_db)
):
    """Start repeating piracy missions automatically (Ikabot-style loop)."""
    result = await db.execute(
        select(IkariamAccount).where(IkariamAccount.id == account_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if not account.is_online:
        raise HTTPException(status_code=400, detail="Conta offline. Faca login primeiro.")
    if data.runs < 1:
        raise HTTPException(status_code=400, detail="Numero de missoes deve ser >= 1.")

    try:
        status = auto_piracy.start(
            account_id=account_id,
            city_id=data.city_id,
            mission_level=data.mission_level,
            runs=data.runs,
            extra_wait_max=data.extra_wait_max,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"status": "started", "detail": status}


@router.post("/{account_id}/piracy/auto/stop")
async def stop_auto_piracy(account_id: int):
    """Stop the automatic piracy loop for this account."""
    await auto_piracy.stop(account_id)
    return {"status": "stopped", "detail": auto_piracy.get_status(account_id)}


@router.get("/{account_id}/piracy/auto/status")
async def auto_piracy_status(account_id: int):
    """Get the current status of the automatic piracy loop."""
    return {
        "running": auto_piracy.is_running(account_id),
        "detail": auto_piracy.get_status(account_id),
    }
