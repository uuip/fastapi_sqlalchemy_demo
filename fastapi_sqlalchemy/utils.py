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

    try:
        data = jsonable_encoder(data)
    except (TypeError, ValueError):
        pass

    return pretty_repr(data, max_width=120, indent_size=2)
