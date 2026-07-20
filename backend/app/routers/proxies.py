"""API routes for proxy management."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import aiohttp
from aiohttp_socks import ProxyConnector

from app.database import get_db
from app.models.proxy import Proxy
from app.utils.crypto import encrypt_password

router = APIRouter(prefix="/api/proxies", tags=["proxies"])


class ProxyCreate(BaseModel):
    host: str
    port: int
    protocol: str = "https"  # https, socks5, socks4
    username: Optional[str] = None
    password: Optional[str] = None
    label: Optional[str] = None
    country: Optional[str] = None


class ProxyUpdate(BaseModel):
    host: Optional[str] = None
    port: Optional[int] = None
    protocol: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    label: Optional[str] = None
    country: Optional[str] = None
    is_active: Optional[bool] = None


class ProxyResponse(BaseModel):
    id: int
    host: str
    port: int
    protocol: str
    username: Optional[str]
    label: Optional[str]
    country: Optional[str]
    is_active: bool
    is_valid: bool
    last_check: Optional[datetime]
    response_time_ms: Optional[float]
    fail_count: int
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=list[ProxyResponse])
async def list_proxies(db: AsyncSession = Depends(get_db)):
    """List all proxies."""
    result = await db.execute(select(Proxy).order_by(Proxy.created_at.desc()))
    proxies = result.scalars().all()
    return proxies


@router.post("/", response_model=ProxyResponse)
async def create_proxy(data: ProxyCreate, db: AsyncSession = Depends(get_db)):
    """Add a new proxy."""
    encrypted_pw = None
    if data.password:
        encrypted_pw = encrypt_password(data.password)

    proxy = Proxy(
        host=data.host,
        port=data.port,
        protocol=data.protocol,
        username=data.username,
        password_encrypted=encrypted_pw,
        label=data.label,
        country=data.country,
    )

    db.add(proxy)
    await db.commit()
    await db.refresh(proxy)
    return proxy


@router.put("/{proxy_id}", response_model=ProxyResponse)
async def update_proxy(
    proxy_id: int,
    data: ProxyUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a proxy."""
    result = await db.execute(select(Proxy).where(Proxy.id == proxy_id))
    proxy = result.scalar_one_or_none()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")

    update_data = data.model_dump(exclude_unset=True)
    if "password" in update_data and update_data["password"]:
        update_data["password_encrypted"] = encrypt_password(update_data.pop("password"))
    elif "password" in update_data:
        update_data.pop("password")

    for key, value in update_data.items():
        setattr(proxy, key, value)

    await db.commit()
    await db.refresh(proxy)
    return proxy


@router.delete("/{proxy_id}")
async def delete_proxy(proxy_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a proxy."""
    result = await db.execute(select(Proxy).where(Proxy.id == proxy_id))
    proxy = result.scalar_one_or_none()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")

    await db.delete(proxy)
    await db.commit()
    return {"detail": "Proxy deleted"}


@router.post("/{proxy_id}/test")
async def test_proxy(proxy_id: int, db: AsyncSession = Depends(get_db)):
    """Test if a proxy is working."""
    result = await db.execute(select(Proxy).where(Proxy.id == proxy_id))
    proxy = result.scalar_one_or_none()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")

    proxy_url = proxy.url

    try:
        import time

        start = time.time()

        if proxy.protocol in ("socks5", "socks4"):
            connector = ProxyConnector.from_url(proxy_url)
        else:
            connector = aiohttp.TCPConnector()

        async with aiohttp.ClientSession(connector=connector) as session:
            if proxy.protocol in ("socks5", "socks4"):
                async with session.get("https://httpbin.org/ip", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    data = await resp.json()
            else:
                async with session.get(
                    "https://httpbin.org/ip",
                    proxy=proxy_url,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    data = await resp.json()

        elapsed = (time.time() - start) * 1000

        # Update proxy status
        proxy.is_valid = True
        proxy.last_check = datetime.utcnow()
        proxy.response_time_ms = elapsed
        proxy.fail_count = 0
        await db.commit()

        return {
            "status": "success",
            "ip": data.get("origin", "unknown"),
            "response_time_ms": round(elapsed, 2),
        }
    except Exception as e:
        proxy.is_valid = False
        proxy.last_check = datetime.utcnow()
        proxy.fail_count += 1
        await db.commit()

        return {
            "status": "failed",
            "error": str(e),
        }
