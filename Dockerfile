# syntax=docker/dockerfile:1

FROM docker.m.daocloud.io/python:3.14-slim AS builder

ARG TARGETARCH

ENV UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /build

RUN --mount=from=ghcr.m.daocloud.io/astral-sh/uv:0.12.5,source=/uv,target=/bin/uv \
    --mount=type=cache,id=uv-cache-py314-${TARGETARCH},target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=/build/uv.lock \
    --mount=type=bind,source=pyproject.toml,target=/build/pyproject.toml \
    uv sync --locked --no-install-project --no-default-groups

FROM docker.m.daocloud.io/python:3.14-slim AS runtime

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    PYTHONPATH=/project

WORKDIR /project

COPY --link --from=builder /opt/venv /opt/venv
COPY ./app app
COPY ./migrations migrations
COPY ./alembic.ini alembic.ini
COPY ./static static

ENTRYPOINT [ "gunicorn", "app.main:app", "--pid", "pid", "--access-logfile", "-" ]
CMD [ "--bind", "0.0.0.0:8000", "--worker-class", "uvicorn_worker.UvicornWorker", "--workers", "2", "--timeout", "1800" ]
