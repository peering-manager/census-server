ARG PYTHON_VER=3.14
FROM docker.io/python:${PYTHON_VER}-slim AS base

ENV PYTHONUNBUFFERED=1

WORKDIR /app/

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install --no-install-recommends -y curl && \
    apt-get autoremove -y && \
    apt-get clean all && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /var/lib/apt/lists/* 

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PATH="/app/.venv/bin:$PATH"
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

ENV PYTHONPATH=/app

COPY ./pyproject.toml ./uv.lock ./alembic.ini /app/
COPY ./census_api /app/census_api

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync

COPY ./gunicorn_conf.py /gunicorn_conf.py

COPY ./start.sh /start.sh
RUN chmod +x /start.sh

COPY ./start-reload.sh /start-reload.sh
RUN chmod +x /start-reload.sh

COPY ./alembic.ini /app/
COPY ./prestart.sh /app/

CMD ["/start.sh"]
