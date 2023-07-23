from typing import Type, TypeVar

from pydantic import create_model, BaseModel
from sqlalchemy.orm import Relationship, DeclarativeBase

Model = TypeVar("Model", bound=BaseModel)


def sqlalchemy2pydantic(model: Type[DeclarativeBase], base: Type[BaseModel]) -> Type[BaseModel]:
    attrs = {}
    db_orm_column_map = {v.name: k for k, v in model.__mapper__.c.items()}
    fk_mapped_columns = {}  # orm中已经被外键映射过的列{"xx_id":"xx"}
    for k, v in model.__mapper__.attrs.items():
        if isinstance(v, Relationship):
            if v.direction.name == "MANYTOONE":
                fk_mapped_columns[k] = db_orm_column_map[list(v.local_columns)[0].name]
            elif v.direction.name == "ONETOMANY":
                # no need
                continue
            else:  # MANYTOMANY
                print("handle MANYTOMANY  by yourself")
                continue
    schema_keys = set(db_orm_column_map.values()) - set(fk_mapped_columns.values())
    for k, v in model.__mapper__.c.items():
        if k in schema_keys:
            attrs[k] = (v.type.python_type, None)
    print("添加外键", set(fk_mapped_columns.keys()))
    kwargs = {"__base__": base}
    pydantic_model = create_model(f"{model.__name__}Schema", **kwargs, **attrs)
    return pydantic_model
