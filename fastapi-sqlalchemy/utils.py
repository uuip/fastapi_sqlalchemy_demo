from typing import Type, TypeVar, Dict

from fastapi.openapi.utils import get_openapi
from loguru import logger
from pydantic import create_model, BaseModel
from sqlalchemy.orm import Relationship, DeclarativeBase

Model = TypeVar("Model", bound=BaseModel)


def sqlalchemy2pydantic(model: Type[DeclarativeBase], base: Type[BaseModel]) -> Type[BaseModel]:
    attrs = {}
    db_orm_column_map = {v.name: k for k, v in model.__mapper__.c.items()}

    # Track foreign key columns already mapped through relationships
    fk_mapped_columns: Dict[str, str] = {}

    # Process relationships
    for attr_name, relationship in model.__mapper__.attrs.items():
        if isinstance(relationship, Relationship):
            if relationship.direction.name == "MANYTOONE":
                # For many-to-one relationships, get the foreign key column name
                fk_column_name = list(relationship.local_columns)[0].name
                fk_mapped_columns[attr_name] = db_orm_column_map[fk_column_name]
            elif relationship.direction.name == "ONETOMANY":
                # One-to-many relationships don't need special handling here
                continue
            else:  # MANYTOMANY
                logger.warning(
                    "Many-to-many relationship found {}: {}, please handle manually", model.__name__, attr_name
                )
                continue
    schema_keys = set(db_orm_column_map.values()) - set(fk_mapped_columns.values())

    for attr_name, column in model.__mapper__.c.items():
        if attr_name in schema_keys:
            attrs[attr_name] = (column.type.python_type, None)

    if fk_mapped_columns:
        logger.debug("Adding foreign keys for {}: {}", model.__name__, set(fk_mapped_columns.keys()))

    kwargs = {"__base__": base}
    pydantic_model = create_model(f"{model.__name__}Schema", **kwargs, **attrs)
    return pydantic_model


def custom_openapi(app):
    def remove_422():
        if not app.openapi_schema:
            app.openapi_schema = get_openapi(
                title=app.title,
                version=app.version,
                openapi_version=app.openapi_version,
                description=app.description,
                terms_of_service=app.terms_of_service,
                contact=app.contact,
                license_info=app.license_info,
                routes=app.routes,
                tags=app.openapi_tags,
                servers=app.servers,
            )

            for path_item in app.openapi_schema.get("paths", {}).values():
                for operation in path_item.values():
                    responses = operation.get("responses", {})
                    if "422" in responses:
                        del responses["422"]
        return app.openapi_schema

    app.openapi = remove_422
