from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import (
    BaseModel,
    field_validator,
    ConfigDict,
    field_serializer,
    computed_field,
)

from models import Trees
from utils import sqlalchemy2pydantic

sh = ZoneInfo('Asia/Shanghai')


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TreeSchema(sqlalchemy2pydantic(Trees, BaseModel)):
    @field_validator("created_at", "updated_at", mode="before", check_fields=False)
    def transform_time(cls, v):
        if isinstance(v, int):
            v = datetime.fromtimestamp(v)
        return v

    @field_serializer("created_at", "updated_at", check_fields=False)
    def serializes_time(self, v):
        return v.strftime("%Y-%m-%d %H:%M:%S")

    @computed_field(return_type=int)
    @property
    def someattr(self):
        return self.created_at.year


class Item(BaseModel):
    id: int
    energy: int
