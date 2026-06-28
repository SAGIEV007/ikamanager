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

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


class AccountCreate(BaseModel):
    nickname: str
    email: str
    password: str
    server_country: str
    server_world: str
    server_number: Optional[int] = None
    server_language: Optional[str] = None
    group_name: str = "Default"
    proxy_id: Optional[int] = None
    delay_min: float = 2.0
    delay_max: float = 6.0
    max_requests_per_minute: int = 20
    operation_start_hour: int = 6
    operation_end_hour: int = 23


class AccountUpdate(BaseModel):
    nickname: Optional[str] = None
    group_name: Optional[str] = None
    proxy_id: Optional[int] = None
    delay_min: Optional[float] = None
    delay_max: Optional[float] = None
    max_requests_per_minute: Optional[int] = None
    operation_start_hour: Optional[int] = None
    operation_end_hour: Optional[int] = None
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
    """Add a new Ikariam account."""
    # Encrypt the password before storing
    encrypted_pw = encrypt_password(data.password)

    account = IkariamAccount(
        nickname=data.nickname,
        email=data.email,
        password_encrypted=encrypted_pw,
        server_country=data.server_country,
        server_world=data.server_world,
        server_number=data.server_number,
        server_language=data.server_language,
        group_name=data.group_name,
        proxy_id=data.proxy_id,
        delay_min=data.delay_min,
        delay_max=data.delay_max,
        max_requests_per_minute=data.max_requests_per_minute,
        operation_start_hour=data.operation_start_hour,
        operation_end_hour=data.operation_end_hour,
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


@router.post("/{account_id}/login")
async def login_account(account_id: int, db: AsyncSession = Depends(get_db)):
    """Login to a specific Ikariam account."""
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

    # Decrypt password
    password = decrypt_password(account.password_encrypted)

    # Login
    login_service = IkariamLoginService(proxy_url=proxy_url)
    try:
        result_data = await login_service.login(account.email, password)

        # Update account status
        account.is_online = True
        account.status = "online"
        account.last_login = datetime.utcnow()
        account.status_message = f"Logged in. Found {len(result_data['accounts'])} game accounts."

        await db.commit()
        await db.refresh(account)

        return {
            "status": "success",
            "message": f"Logged in successfully. Found {len(result_data['accounts'])} game accounts.",
            "game_accounts": result_data["accounts"],
        }
    except GameforgeLoginError as e:
        account.status = "error"
        account.status_message = str(e)
        account.is_online = False
        await db.commit()
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        account.status = "error"
        account.status_message = f"Connection error: {str(e)}"
        account.is_online = False
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Connection error: {str(e)}")
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


@router.get("/{account_id}/cities")
async def get_account_cities(account_id: int, db: AsyncSession = Depends(get_db)):
    """Get cities for an account."""
    from app.models.city import City

    result = await db.execute(
        select(City).where(City.account_id == account_id)
    )
    cities = result.scalars().all()
    return cities
