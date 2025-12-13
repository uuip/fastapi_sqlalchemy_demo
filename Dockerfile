FROM python:3.14-slim
ENV PYTHONPATH=/app
ENV UV_PROJECT_ENVIRONMENT=/usr/local/
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --no-install-project

WORKDIR $PYTHONPATH
COPY ./fastapi_sqlalchemy fastapi_sqlalchemy