from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, computed_field, field_serializer, field_validator

tz = ZoneInfo("Asia/Shanghai")


class AccountSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    updated_at: datetime
    created_at: datetime
    energy: int

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
