from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import (
    BaseModel,
    field_validator,
    ConfigDict,
    field_serializer,
    computed_field,
    )

from model import Trees
from utils import sqlalchemy2pydantic

tz = ZoneInfo("Asia/Shanghai")


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TreeSchema(sqlalchemy2pydantic(Trees, BaseModel)):

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def transform_time(cls, v) -> datetime:
        if isinstance(v, int):
            v = datetime.fromtimestamp(v)
        return v

    @field_serializer("created_at", "updated_at")
    def serializes_time(self, v: datetime):
        return v.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S%z")

    @computed_field
    @property
    def someattr(self) -> int:
        return self.created_at.astimezone(tz).year


class Item(BaseModel):
    id: int
    energy: int


class UserSchema(BaseModel):
    username: str
