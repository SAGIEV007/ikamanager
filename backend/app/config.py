from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "IkaManager"
    debug: bool = True
    # Echo every SQL statement to the console. Off by default: it floods the
    # terminal and makes real messages hard to spot. Enable only for debugging.
    sql_echo: bool = False
    database_url: str = "sqlite+aiosqlite:///./ikamanager.db"
    secret_key: str = "change-this-in-production-use-a-real-secret-key"
    encryption_key: str = "change-this-32-byte-key-for-prod!"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    redis_url: str = "redis://localhost:6379"
    default_request_delay_min: float = 2.0
    default_request_delay_max: float = 6.0
    max_requests_per_minute: int = 20
    # Piracy captcha solving: "auto" (local then 2captcha), "local",
    # "2captcha", or "off".
    captcha_mode: str = "auto"
    twocaptcha_api_key: str = ""

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
