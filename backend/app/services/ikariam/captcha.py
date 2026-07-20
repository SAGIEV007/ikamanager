"""Piracy captcha solving.

Two backends are supported:

* **local** - an ONNX model (ported from Ikabot's ``piratesDecaptcha``) that runs
  on the user's machine for free. Requires the optional ``onnxruntime`` package.
* **2captcha** - a paid remote service. Requires an API key.

``solve`` picks a backend according to the configured mode and available
resources, returning the recognised captcha text (uppercase) or raising
``CaptchaError``.
"""

import asyncio
import base64
import logging

import httpx

from app.services.ikariam import pirates_decaptcha

logger = logging.getLogger(__name__)


class CaptchaError(Exception):
    """Raised when a captcha could not be solved."""


def local_available() -> bool:
    return pirates_decaptcha.is_available()


def solve_local(image_bytes: bytes) -> str:
    """Solve the captcha locally with the ONNX model (blocking, CPU-bound)."""
    if not pirates_decaptcha.is_available():
        raise CaptchaError(
            "Resolvedor local indisponivel (instale 'onnxruntime')."
        )
    try:
        text = pirates_decaptcha.get_captcha_string(image_bytes)
    except Exception as e:  # noqa: BLE001
        raise CaptchaError(f"Falha no resolvedor local: {e}")
    if not text:
        raise CaptchaError("Resolvedor local retornou vazio.")
    return text


async def solve_2captcha(image_bytes: bytes, api_key: str) -> str:
    """Solve the captcha via the 2captcha.com service."""
    if not api_key:
        raise CaptchaError("Chave da API 2Captcha nao configurada.")
    b64 = base64.b64encode(image_bytes).decode("ascii")
    async with httpx.AsyncClient(timeout=30) as client:
        submit = await client.post(
            "https://2captcha.com/in.php",
            data={"key": api_key, "method": "base64", "body": b64, "json": 1},
        )
        data = submit.json()
        if data.get("status") != 1:
            raise CaptchaError(f"2Captcha recusou o envio: {data.get('request')}")
        captcha_id = data["request"]

        # Poll for the result (2captcha usually needs ~10-20s).
        for _ in range(24):
            await asyncio.sleep(5)
            res = await client.get(
                "https://2captcha.com/res.php",
                params={"key": api_key, "action": "get", "id": captcha_id, "json": 1},
            )
            rdata = res.json()
            if rdata.get("status") == 1:
                return str(rdata["request"]).upper()
            if rdata.get("request") != "CAPCHA_NOT_READY":
                raise CaptchaError(f"2Captcha erro: {rdata.get('request')}")
    raise CaptchaError("2Captcha demorou demais para responder.")


async def solve(image_bytes: bytes, mode: str, twocaptcha_key: str) -> str:
    """Solve a captcha according to ``mode`` (auto|local|2captcha).

    ``auto`` tries the local solver first (free) and falls back to 2captcha.
    """
    mode = (mode or "auto").lower()

    if mode == "off":
        raise CaptchaError("Resolucao de captcha desativada nas configuracoes.")

    if mode in ("local", "auto") and local_available():
        try:
            return await asyncio.to_thread(solve_local, image_bytes)
        except CaptchaError:
            if mode == "local":
                raise
            logger.info("Local captcha failed, falling back to 2captcha")

    if mode in ("2captcha", "auto") and twocaptcha_key:
        return await solve_2captcha(image_bytes, twocaptcha_key)

    raise CaptchaError(
        "Nenhum resolvedor de captcha disponivel. Instale 'onnxruntime' "
        "(local) ou configure a chave 2Captcha."
    )
