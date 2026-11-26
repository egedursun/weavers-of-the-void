FROM ghcr.io/astral-sh/uv:0.13.6-python3.13-trixie-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

COPY backend/src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable


FROM python:3.13-slim-trixie AS runtime

ARG AERONA_UID=10001
ARG AERONA_GID=10001

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fontconfig \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid "${AERONA_GID}" aerona \
    && useradd --system --uid "${AERONA_UID}" --gid aerona --home-dir /home/aerona --create-home --shell /usr/sbin/nologin aerona \
    && mkdir -p /data \
    && chown aerona:aerona /data

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/home/aerona \
    AERONA_DATA_DIR=/data \
    AERONA_HOST=0.0.0.0 \
    AERONA_PORT=8000

COPY --from=builder --chown=aerona:aerona /app/.venv /app/.venv
COPY --chown=aerona:aerona scripts/backup_library.py /app/scripts/backup_library.py

WORKDIR /home/aerona
USER aerona
VOLUME ["/data"]
EXPOSE 8000

LABEL org.opencontainers.image.title="Weavers of the Void backend" \
      org.opencontainers.image.licenses="AGPL-3.0-only" \
      org.opencontainers.image.source="https://github.com/egedursun/weavers-of-the-void"
COPY LICENSE NOTICE LICENSING.md TRADEMARKS.md THIRD_PARTY_NOTICES.md LICENSES /usr/share/licenses/weavers-of-the-void/

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import os, sys, urllib.request; sys.exit(0 if urllib.request.urlopen(f\"http://127.0.0.1:{os.environ['AERONA_PORT']}/api/health\", timeout=4).status == 200 else 1)"]

CMD ["sh", "-c", "exec uvicorn aerona.main:create_app --factory --host \"$AERONA_HOST\" --port \"$AERONA_PORT\" --proxy-headers --forwarded-allow-ips '*'"]
