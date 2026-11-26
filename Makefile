BACKEND := backend
FRONTEND := frontend

.PHONY: install agents gateway dev backend frontend test lint typecheck rules version bump prerelease release migration typegen check migrate-legacy legacy-rule-map anatomy

install: agents
	cd $(BACKEND) && uv sync
	cd $(FRONTEND) && npm install

agents:
	cd deploy/agents && npm ci --no-audit --no-fund

gateway:
	mkdir -p data/bifrost && cp deploy/bifrost/config.json data/bifrost/config.json
	npx -y @maximhq/bifrost@1.6.3 --transport-version v2.6.0 -app-dir data/bifrost -host 127.0.0.1 -port 8180

backend:
	cd $(BACKEND) && uv run uvicorn aerona.main:create_app --factory --reload --host 127.0.0.1 --port 8000

frontend:
	cd $(FRONTEND) && npm run dev

dev:
	$(MAKE) -j3 gateway backend frontend

rules:
	cd $(BACKEND) && uv run python ../scripts/check_source_rules.py
	cd $(BACKEND) && uv run python ../scripts/version.py check

version:
	cd $(BACKEND) && uv run --no-sync python ../scripts/version.py $(if $(v),set $(v),show)

bump:
	cd $(BACKEND) && uv run --no-sync python ../scripts/version.py bump $(part) $(pre)

prerelease:
	cd $(BACKEND) && uv run --no-sync python ../scripts/version.py pre $(pre)

release:
	cd $(BACKEND) && uv run --no-sync python ../scripts/version.py release

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

anatomy:
	cd scripts/anatomy && python3 build.py

check: rules lint typecheck test

.PHONY: docker-up docker-up-gpu docker-up-console docker-down image-worker image-worker-test minio env worker-start worker-stop worker-status up down

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
