from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel, field_validator, field_serializer, computed_field

tz = ZoneInfo("Asia/Shanghai")


class AccountSchema(BaseModel):

    id: int
    username: str
    password: str
    updated_at: datetime
    created_at: datetime
    balance: int

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
