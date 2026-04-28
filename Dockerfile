FROM docker.m.daocloud.io/python:3.14-slim AS base
RUN sed -i 's|deb.debian.org|mirrors.ustc.edu.cn|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends vim \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.m.daocloud.io/astral-sh/uv:latest /uv /bin/

FROM base AS builder
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/usr/local/
COPY uv.lock pyproject.toml ./
RUN --mount=type=cache,id=uv-cache,target=/root/.cache/uv uv sync --no-install-project

FROM builder
ENV PYTHONPATH=/app
WORKDIR $PYTHONPATH
COPY ./fastapi_sqlalchemy fastapi_sqlalchemy

ENTRYPOINT ["gunicorn","fastapi_sqlalchemy.main:app","--pid","pid", "--access-logfile", "-"]
CMD [ "--bind","0.0.0.0:8000", "--worker-class","uvicorn.workers.UvicornWorker","--workers","2", "--timeout","1800"]
