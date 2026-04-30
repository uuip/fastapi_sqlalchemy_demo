import re
from functools import cached_property
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic import Field, computed_field, field_validator
from pydantic_settings import SettingsConfigDict, BaseSettings
from sqlalchemy import make_url

_env_file = Path(__file__).parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_env_file, extra="ignore")

    db_url: str = Field(description="Database connection string")
    secret_key: str = Field(description="Secret key for JWT tokens (generate with: openssl rand -hex 32)")
    jwt_expire_days: int = Field(30, description="JWT token expiration in days")

    @computed_field
    @cached_property
    def db_dict(self) -> dict[str, Any]:
        u = urlparse(self.db_url)
        return {
            "host": u.hostname,
            "port": int(u.port or 5432),
            "database": u.path.lstrip("/"),
            "user": u.username,
            "password": u.password,
        }

    @field_validator("db_url")
    @classmethod
    def inject_db_timezone(cls, v):
        if re.search(r"time_?zone", v, re.I):
            return v
        url = make_url(v)
        if "mysql" in url.drivername:
            url = url.update_query_dict({"init_command": "SET time_zone = '+08:00'"})
        elif "postgres" in url.drivername or "kingbase" in url.drivername:
            existing = url.query.get("options", "")
            url = url.update_query_dict({"options": f"{existing} -c timezone=Asia/Shanghai".strip()})
        return url.render_as_string(hide_password=False)


settings = Settings()
