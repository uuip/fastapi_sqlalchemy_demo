from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field, model_validator
from pydantic_settings import SettingsConfigDict, BaseSettings

_env_file = Path(__file__).parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_env_file, extra="ignore")

    db: str = Field(alias="db")
    db_dict: dict

    @model_validator(mode="before")
    def set_variant(cls, values: dict):
        c = urlparse(values["db"])
        values["db_dict"] = {
            "host": c.hostname,
            "port": c.port or 5432,
            "database": c.path.lstrip("/"),
            "user": c.username,
            "password": c.password,
        }
        return values


settings = Settings()
