from fastapi.openapi.utils import get_openapi
from loguru import logger
from pydantic import create_model, ConfigDict, BaseModel
from sqlalchemy.orm import DeclarativeBase


def sqlalchemy2pydantic(model: type[DeclarativeBase]) -> type[BaseModel]:
    fk_columns = set()
    for rel in model.__mapper__.relationships:
        if rel.direction.name == "MANYTOONE":
            fk_columns.update(c.name for c in rel.local_columns)
        elif rel.direction.name == "MANYTOMANY":
            logger.warning("Many-to-many relationship found {}: {}, please handle manually", model.__name__, rel.key)

    fields = {
        attr: (col.type.python_type | None, None)
        for attr, col in model.__mapper__.c.items()
        if col.name not in fk_columns
    }
    return create_model(
        f"{model.__name__}Schema",
        __config__=ConfigDict(from_attributes=True),
        **fields,
    )


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
