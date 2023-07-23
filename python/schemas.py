from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from pydantic import (
    BaseModel as _BaseModel,
    field_validator,
    ConfigDict,
    field_serializer,
    computed_field,
)

from models import Users, Trees
from utils import sqlalchemy2pydantic

sh = ZoneInfo('Asia/Shanghai')


def transform_time(dt):
    return dt.astimezone(sh).strftime("%Y-%m-%d %H:%M:%S +08:00")


def transform_naive_time(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


class BaseModel(_BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TreeSchema(sqlalchemy2pydantic(Trees, BaseModel)):
    @field_validator("created_at", "updated_at", mode="before", check_fields=False)
    def transform_time(cls, v):
        if isinstance(v, int):
            v = datetime.fromtimestamp(v)
        return v

    @field_serializer("created_at", "updated_at", check_fields=False)
    def serializes_time(self, v):
        return transform_naive_time(v)

    @computed_field(return_type=int)
    @property
    def someattr(self):
        return self.created_at.year


class UserSchema(sqlalchemy2pydantic(Users, BaseModel)):
    ...


class Item(BaseModel):
    id: int
    energy: int
