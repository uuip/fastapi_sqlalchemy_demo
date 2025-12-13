from functools import cached_property
from pathlib import Path
from typing import Dict, Any
from urllib.parse import urlparse

from pydantic import Field, computed_field
from pydantic_settings import SettingsConfigDict, BaseSettings

_env_file = Path(__file__).parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_env_file, extra="ignore")

    db: str = Field(alias="db_url", description="Database connection string")
    debug: bool = Field(True, description="Enable debug mode")
    secret_key: str = Field(
        description="Secret key for JWT tokens (generate with: openssl rand -hex 32)",
    )
    jwt_expire_days: int = Field(30, description="JWT token expiration in days")

    @computed_field
    @cached_property
    def db_dict(self) -> Dict[str, Any]:
        u = urlparse(self.db)
        return {
            "host": u.hostname,
            "port": int(u.port or 5432),
            "database": u.path.lstrip("/"),
            "user": u.username,
            "password": u.password,
        }


settings = Settings()
