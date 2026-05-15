from fastapi import APIRouter

from app.apps.examples.api.background import bg_api
from app.apps.examples.api.files import file_api
from app.apps.examples.api.param_examples import example_api
from app.apps.examples.api.streaming import stream_api

examples_router = APIRouter()
examples_router.include_router(example_api)
examples_router.include_router(bg_api)
examples_router.include_router(file_api)
examples_router.include_router(stream_api)

__all__ = ["examples_router"]
