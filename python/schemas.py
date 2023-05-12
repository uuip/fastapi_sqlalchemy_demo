from datetime import datetime, timezone, timedelta
from pydantic import BaseModel as _BaseModel, validator
from pydantic.utils import GetterDict
from typing import Any

from models import Users, Trees
from utils import sqlalchemy2pydantic

sh = timezone(timedelta(hours=+8))


def transform_time(dt):
    return dt.astimezone(sh).strftime("%Y-%m-%d %H:%M:%S +08:00")


def transform_naive_time(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


class BaseModel(_BaseModel):
    class Config:
        orm_mode = True


def key_source(key_map: dict):
    def get(self, key: Any, default: Any = None) -> Any:
        if key in key_map:
            foreign_keys = key_map[key].split(".")
            obj = self._obj
            for x in foreign_keys:
                obj = getattr(obj, x)
            return obj
        return getattr(self._obj, key, default)

    return type("AGetterDict", (GetterDict,), {"get": get})


class TreeSchema(sqlalchemy2pydantic(Trees, BaseModel)):
    @validator("create_at", "update_at")
    def transform_time(cls, v):
        if isinstance(v, int):
            v = datetime.fromtimestamp(v)
            return transform_naive_time(v)
        if isinstance(v, datetime):
            return transform_naive_time(v)
        return v

    # class Config:
    #     getter_dict = key_source({"user": "user.id"})


class UserSchema(sqlalchemy2pydantic(Users, BaseModel)):
    ...


class Item(BaseModel):
    id: int
    energy: int
