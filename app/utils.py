import contextlib
import json
from typing import Any

from fastapi.encoders import jsonable_encoder
from rich.pretty import pretty_repr


def pretty_data(data: Any) -> str:
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return data

    with contextlib.suppress(TypeError, ValueError):
        data = jsonable_encoder(data)

    return pretty_repr(data, max_width=80, indent_size=2)
