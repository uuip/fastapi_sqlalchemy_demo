from functools import cached_property
from pathlib import Path
from urllib.parse import urlparse

from pydantic import *
from pydantic_settings import SettingsConfigDict, BaseSettings

_env_file = Path(__file__).parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_env_file, extra="ignore")

    db: str = Field(alias="db_url")
    debug: bool = Field(True)

    @computed_field(return_type=dict)
    @cached_property
    def db_dict(self):
        c = urlparse(self.db)
        return {
            "host": c.hostname,
            "port": c.port or 5432,
            "database": c.path.lstrip("/"),
            "user": c.username,
            "password": c.password,
        }


settings = Settings()
