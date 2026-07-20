from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import app_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    captcha_mode: Optional[str] = None
    twocaptcha_api_key: Optional[str] = None


@router.get("/")
async def get_app_settings():
    return app_settings.public_view()


@router.put("/")
async def update_app_settings(data: SettingsUpdate):
    try:
        return app_settings.update(
            captcha_mode=data.captcha_mode,
            twocaptcha_api_key=data.twocaptcha_api_key,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
