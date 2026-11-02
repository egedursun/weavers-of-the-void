BACKEND := backend
FRONTEND := frontend

.PHONY: install dev backend frontend test lint typecheck rules version migration typegen check migrate-legacy legacy-rule-map

install:
	cd $(BACKEND) && uv sync
	cd $(FRONTEND) && npm install

backend:
	cd $(BACKEND) && uv run uvicorn aerona.main:create_app --factory --reload --host 127.0.0.1 --port 8000

frontend:
	cd $(FRONTEND) && npm run dev

dev:
	$(MAKE) -j2 backend frontend

rules:
	cd $(BACKEND) && uv run python ../scripts/check_source_rules.py
	cd $(BACKEND) && uv run python ../scripts/version.py check

version:
	cd $(BACKEND) && uv run --no-sync python ../scripts/version.py set $(v)

test:
	cd $(BACKEND) && uv run pytest -q -n auto
	cd $(FRONTEND) && npm run build

lint:
	cd $(BACKEND) && uv run ruff check src tests ../scripts && uv run ruff format --check src tests ../scripts && uv run lint-imports
	cd $(FRONTEND) && npx eslint .

typecheck:
	cd $(BACKEND) && uv run mypy src
	cd $(FRONTEND) && npm run typecheck

migration:
	cd $(BACKEND) && uv run python ../scripts/make_migration.py $(name)

typegen:
	cd $(FRONTEND) && npm run typegen

LEGACY ?= $(HOME)/aerona/data
TARGET ?= data/aerona.db
MEDIA ?= file
MIGRATE_FLAGS ?=

migrate-legacy:
	cd $(BACKEND) && uv run python -m aerona.migration.legacy --legacy "$(abspath $(patsubst ~/%,$(HOME)/%,$(LEGACY)))" --target "$(abspath $(patsubst ~/%,$(HOME)/%,$(TARGET)))" --media $(MEDIA) $(MIGRATE_FLAGS)

legacy-rule-map:
	cd $(BACKEND) && uv run python ../scripts/build_legacy_rule_map.py

check: rules lint typecheck test

.PHONY: docker-up docker-up-gpu docker-up-console docker-down image-worker image-worker-test minio env claude-token worker-start worker-stop worker-status up down

MINIO_IMAGE ?= pgsty/minio:RELEASE.2026-08-04T00-00-00Z
MINIO_DEV_DIR ?= data/minio

docker-up:
	docker compose up -d --build

docker-up-gpu:
	docker compose --profile gpu up -d --build

docker-up-console:
	docker compose --profile media-console up -d --build

docker-down:
	docker compose --profile gpu --profile media-console down

minio:
	@set -a; if [ -f .env ]; then . ./.env; fi; set +a; \
	if [ -z "$$AERONA_MEDIA_ACCESS_KEY" ] || [ -z "$$AERONA_MEDIA_SECRET_KEY" ]; then echo "Set AERONA_MEDIA_ACCESS_KEY and AERONA_MEDIA_SECRET_KEY in .env"; exit 1; fi; \
	export MINIO_ROOT_USER="$$AERONA_MEDIA_ACCESS_KEY" MINIO_ROOT_PASSWORD="$$AERONA_MEDIA_SECRET_KEY"; \
	if command -v minio >/dev/null 2>&1; then \
		mkdir -p $(MINIO_DEV_DIR) && minio server $(MINIO_DEV_DIR) --address 127.0.0.1:$${AERONA_MINIO_DEV_PORT:-9000} --console-address 127.0.0.1:$${AERONA_MINIO_CONSOLE_PORT:-9001}; \
	else \
		docker run --rm --name aerona-minio-dev -e MINIO_ROOT_USER -e MINIO_ROOT_PASSWORD \
			-p 127.0.0.1:$${AERONA_MINIO_DEV_PORT:-9000}:9000 -p 127.0.0.1:$${AERONA_MINIO_CONSOLE_PORT:-9001}:9001 \
			-v aerona-minio-dev:/data $${AERONA_MINIO_IMAGE:-$(MINIO_IMAGE)} server /data --console-address :9001; \
	fi

image-worker:
	cd image-worker && AERONA_IMAGE_WORKER_BACKEND=mlx uv run --extra mlx aerona-image-worker

image-worker-test:
	cd image-worker && uv run ruff check src tests && uv run ruff format --check src tests && uv run mypy src tests && uv run pytest -q

env:
	cd $(BACKEND) && uv run python ../scripts/stack.py env

claude-token:
	cd $(BACKEND) && uv run python ../scripts/stack.py claude-token

worker-start:
	cd $(BACKEND) && uv run python ../scripts/stack.py worker-start

worker-stop:
	cd $(BACKEND) && uv run python ../scripts/stack.py worker-stop

worker-status:
	cd $(BACKEND) && uv run python ../scripts/stack.py worker-status

up:
	cd $(BACKEND) && uv run python ../scripts/stack.py up

down:
	cd $(BACKEND) && uv run python ../scripts/stack.py down
