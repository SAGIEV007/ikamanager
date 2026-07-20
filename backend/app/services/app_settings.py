"""Runtime-configurable app settings persisted to a small JSON file.

Used for options the (non-technical) user should be able to change from the UI
without editing ``.env`` - currently the piracy captcha configuration. Values
default to the environment-based :class:`Settings` when not set here.
"""

import json
import os
from typing import Optional

from app.config import get_settings

_SETTINGS_PATH = os.path.join(os.getcwd(), "ikamanager_settings.json")

_ALLOWED_CAPTCHA_MODES = {"auto", "local", "2captcha", "off"}


def _read() -> dict:
    try:
        with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {}


def _write(data: dict) -> None:
    with open(_SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_captcha_mode() -> str:
    return _read().get("captcha_mode") or get_settings().captcha_mode


def get_twocaptcha_key() -> str:
    return _read().get("twocaptcha_api_key") or get_settings().twocaptcha_api_key


def update(captcha_mode: Optional[str], twocaptcha_api_key: Optional[str]) -> dict:
    data = _read()
    if captcha_mode is not None:
        if captcha_mode not in _ALLOWED_CAPTCHA_MODES:
            raise ValueError(
                f"Modo invalido. Use um de: {', '.join(sorted(_ALLOWED_CAPTCHA_MODES))}."
            )
        data["captcha_mode"] = captcha_mode
    if twocaptcha_api_key is not None:
        data["twocaptcha_api_key"] = twocaptcha_api_key
    _write(data)
    return public_view()


def public_view() -> dict:
    """Return settings safe to expose to the UI (key is masked)."""
    key = get_twocaptcha_key()
    from app.services.ikariam import captcha

    return {
        "captcha_mode": get_captcha_mode(),
        "twocaptcha_key_set": bool(key),
        "local_captcha_available": captcha.local_available(),
    }
