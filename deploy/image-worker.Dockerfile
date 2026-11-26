FROM ghcr.io/astral-sh/uv:0.13.6 AS uv


FROM nvidia/cuda:13.0.3-base-ubuntu24.04 AS builder

COPY --from=uv /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_INSTALL_DIR=/opt/python \
    UV_PYTHON_PREFERENCE=only-managed \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

RUN uv python install 3.13

COPY image-worker/pyproject.toml image-worker/uv.lock image-worker/.python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --extra diffusers --no-install-project

COPY image-worker/src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --extra diffusers --no-editable


FROM nvidia/cuda:13.0.3-base-ubuntu24.04 AS runtime

ARG WORKER_UID=10001
ARG WORKER_GID=10001

RUN groupadd --system --gid "${WORKER_GID}" worker \
    && useradd --system --uid "${WORKER_UID}" --gid worker --home-dir /home/worker --create-home --shell /usr/sbin/nologin worker \
    && mkdir -p /models \
    && chown worker:worker /models

COPY --from=builder /opt/python /opt/python
COPY --from=builder --chown=worker:worker /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/home/worker \
    HF_HOME=/models \
    HF_HUB_DISABLE_TELEMETRY=1 \
    AERONA_IMAGE_WORKER_BACKEND=diffusers \
    AERONA_IMAGE_WORKER_HOST=0.0.0.0 \
    AERONA_IMAGE_WORKER_PORT=8100

WORKDIR /home/worker
USER worker
VOLUME ["/models"]
EXPOSE 8100

LABEL org.opencontainers.image.title="Weavers of the Void image worker" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.source="https://github.com/egedursun/weavers-of-the-void"
COPY image-worker/LICENSE THIRD_PARTY_NOTICES.md /usr/share/licenses/weavers-of-the-void-image-worker/

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD ["python", "-c", "import os, sys, urllib.request; sys.exit(0 if urllib.request.urlopen(f\"http://127.0.0.1:{os.environ['AERONA_IMAGE_WORKER_PORT']}/health\", timeout=4).status == 200 else 1)"]

CMD ["aerona-image-worker"]
