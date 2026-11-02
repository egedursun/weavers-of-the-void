# Aerona

Aerona is a self-generating lore engine. You play the Creator. Your sons are god cards that act as LLM agents once per epoch, while a deterministic engine simulates the world between their turns. Images for records are generated locally by a separate image worker.

- Architecture: [docs/architecture.md](docs/architecture.md)
- Decisions: [docs/decisions.md](docs/decisions.md)
- Business logic: [docs/spec/](docs/spec/)

## Requirements

- [uv](https://docs.astral.sh/uv/) (Python 3.13 is installed by uv)
- Node.js 24 and npm
- A Claude subscription and the [Claude Code CLI](https://docs.claude.com/en/docs/claude-code) for the token
- Docker with Compose v2.24 or newer, for the containerized setup
- Optional: an Apple Silicon Mac (native `mlx` image worker) or an NVIDIA GPU with the NVIDIA Container Toolkit (`diffusers` image worker)

## Quick start

```sh
make env           # creates .env with a generated media secret and the worker URL
make claude-token  # signs in with your Claude subscription and stores the token in .env
make up            # the whole stack: backend, web, media store and the image worker
make down          # stops it again; volumes are kept
```

`make up` picks the image worker for the machine. On Apple Silicon it starts the native MLX worker in the background (`make worker-start`, `make worker-stop`, `make worker-status`; log in `data/run/image-worker.log`) and points the backend container at `http://host.docker.internal:8100`. Anywhere else it starts the `image-worker` container on the NVIDIA GPU (profile `gpu`). The web app is at http://127.0.0.1:8080.

`make claude-token` runs `claude setup-token`, asks you to paste the printed token with hidden input, checks it with a one-word Claude Haiku reply and only then writes it to `.env` (mode 600). The token never appears on screen twice and never goes into git.

## Configuration

Every setting is an environment variable. `.env` is ignored by git. The main ones:

| Variable | Meaning |
|---|---|
| `CLAUDE_CODE_OAUTH_TOKEN` | Subscription token for the Claude Agent SDK (see below). Never use an API key. |
| `AERONA_DATA_DIR` | Database, backups and (with the file media store) images. Docker always uses the `aerona-data` volume. |
| `AERONA_LLM_ENABLED` | `false` runs the world engine without any LLM calls. |
| `AERONA_IMAGE_WORKER_URL` | Base URL of the image worker for a backend running on the host. Empty disables image generation. |
| `AERONA_DOCKER_IMAGE_WORKER_URL` | Worker URL inside the backend container. `make up` sets it; the default is the `image-worker` container. |
| `AERONA_BIND_ADDRESS` | Host address Docker publishes ports on (default `127.0.0.1`). |
| `AERONA_IMAGE_WORKER_*` | Image worker settings: backend, model, timeouts, idle unload. |
| `AERONA_MEDIA_*` | Media store: backend (`file` or `s3`), endpoint, bucket, credentials, region, TLS. See [Media store](#media-store). |

### Claude token

Aerona uses your Claude subscription through the Agent SDK, never an API key. Create a long-lived token once:

```sh
claude setup-token
```

Put the printed token into `CLAUDE_CODE_OAUTH_TOKEN` in `.env`, or let `make claude-token` do it. The backend hands the token to every Agent SDK call, on the host and in Docker alike. Without a token, a backend on the host falls back to this machine's `claude` login; Settings, Maintenance, Health shows which one is in use.

## Local development

```sh
make install
make dev
```

- Backend: http://127.0.0.1:8000 (API under `/api`, with reload)
- Frontend: http://127.0.0.1:5173 (Vite proxies `/api` to the backend)
- Checks: `make check` (source rules, lint, types, tests) and `make image-worker-test`

## Docker

```sh
make docker-up
```

This builds and starts:

- `backend`: FastAPI on Python 3.13, running as a non-root user. SQLite and backups live in the `aerona-data` volume.
- `minio`: the S3-compatible media store. Images live in the `aerona-media` volume. It has no host port; the backend reaches it on the internal network.
- `minio-init`: a one-shot job that creates the bucket with `mc` and keeps it private. The backend starts after it finished.
- `web`: the built frontend served by nginx at http://127.0.0.1:8080. nginx proxies `/api` to the backend with SSE buffering off.

On an NVIDIA host, `make docker-up-gpu` also starts the `image-worker` container (profile `gpu`); the backend reaches it at `http://image-worker:8100` by default. Model weights are downloaded on the first image into the `aerona-models` volume, never into the image.

`make docker-down` stops everything. Volumes are kept.

## Media store

Images never touch a plain directory directly: every read and write goes through one `MediaStore` interface with two implementations.

| Backend | `AERONA_MEDIA_BACKEND` | Where objects live |
|---|---|---|
| File | `file` (default for local development and tests) | `$AERONA_DATA_DIR/media` |
| S3 | `s3` (Docker uses it) | A MinIO bucket, or any S3-compatible service |

Object keys:

- `originals/<image-id>.<ext>` for every uploaded or generated image. The image row stores the key, the content type, the size and the SHA-256 checksum. Identical content is stored once: an upload whose checksum is already known reuses the object.
- `thumbnails/<width>/<image-id>.webp`, rendered with Pillow on the first request for that width and then served from the store.

The browser only reaches images through the backend at `/api/media/<file>?w=<width>`, which streams the object with its content type, an `ETag` and immutable caching headers. MinIO is never exposed.

An object is deleted only when neither the live world, nor any backup, nor an open discovery world references it, so restoring a backup always finds its images. World packages (`.aerona`) are gzip-compressed tar archives holding a manifest, the database and the referenced objects, streamed to and from the store one object at a time.

### Settings

| Variable | Meaning |
|---|---|
| `AERONA_MEDIA_BACKEND` | `file` or `s3`. |
| `AERONA_MEDIA_ENDPOINT` | S3 endpoint as `host:port` or a full URL. Empty means AWS S3. |
| `AERONA_MEDIA_BUCKET` | Bucket name (default `aerona-media`). The backend creates it if it is missing. |
| `AERONA_MEDIA_ACCESS_KEY`, `AERONA_MEDIA_SECRET_KEY` | Credentials. Docker also uses them as the MinIO root user, so both are required for `docker compose`. |
| `AERONA_MEDIA_REGION` | Region (default `us-east-1`). |
| `AERONA_MEDIA_SECURE` | `true` uses HTTPS for a `host:port` endpoint. |

### MinIO console

`make docker-up-console` also starts a small proxy that publishes the MinIO console on http://127.0.0.1:9001 only (profile `media-console`, port `AERONA_MINIO_CONSOLE_PORT`).

### MinIO for local development

`make minio` runs MinIO for a backend started with `make dev`. It uses a native `minio` binary when one is on the `PATH` (data in `data/minio`), otherwise it runs only the MinIO container with ports bound to `127.0.0.1`. Then set in `.env`:

```sh
AERONA_MEDIA_BACKEND=s3
AERONA_MEDIA_ENDPOINT=127.0.0.1:9000
AERONA_MEDIA_ACCESS_KEY=aerona
AERONA_MEDIA_SECRET_KEY=<at least 8 characters>
```

The upstream MinIO project no longer publishes community images, so the default image is the community build `pgsty/minio`. Set `AERONA_MINIO_IMAGE` to use another one.

## Migrating the legacy world

The world of the legacy Node app (`~/aerona/data`) can be carried into the rewrite once. The plan and its limits are in [docs/migration-plan.md](docs/migration-plan.md).

```sh
make migrate-legacy LEGACY=~/aerona/data TARGET=data/aerona.db MIGRATE_FLAGS=--dry-run
make migrate-legacy LEGACY=~/aerona/data TARGET=data/aerona.db
```

Or directly: `cd backend && uv run python -m aerona.migration.legacy --legacy ~/aerona/data --target <path> [--dry-run] [--media file|s3] [--replace] [--media-dir <dir>] [--report-dir <dir>]`.

- The legacy database is read only through a consistent snapshot (SQLite backup API), so the legacy app may keep running. Nothing in the legacy folder is written.
- The legacy epoch must be finished: a paused epoch or a paused turn stops the migration.
- The target is always a fresh database built by the Alembic migration, with `lore_language = turkish`. An existing target is refused unless `--replace` is given. The work happens in `<target>.partial` inside one transaction; any failure removes the partial file and every image object the run uploaded.
- Images are copied from the legacy image folder into the media store (`--media file` writes to `--media-dir`, by default `media/` next to the target; `--media s3` uses the `AERONA_MEDIA_*` settings). Identical files are stored once (SHA-256). Thumbnails are not copied; they are rebuilt on demand.
- `--dry-run` converts into a throwaway database, uploads nothing and only writes the report.
- Every run writes `migration-report.json` and `migration-report.md` (to `--report-dir`, or next to the target): counts per table, renamed records, everything that could not be placed, tags that were not understood and how every rule override was mapped. A real run also keeps the legacy undo ledger as a read-only `legacy-ledger.json`.

The legacy vocabulary (Turkish table, column, enum and tag names) lives only in `backend/src/aerona/migration/legacy/schema_map.json`. Its rule section is regenerated from `docs/spec/rules-registry.json` and the current registry with `make legacy-rule-map`.

## Image worker on macOS

Docker on macOS cannot use the Apple GPU (containers get no Metal access), so the `mlx` worker runs natively on the host. `make up` starts it for you; to run it alone:

```sh
make worker-start   # background, or `make image-worker` in the foreground
```

It listens on http://127.0.0.1:8100 and loads `mflux-community/z-image-turbo-mflux-q4` (about 6 GB, downloaded on the first image into the Hugging Face cache). Point the backend at it:

- Docker backend: `AERONA_IMAGE_WORKER_URL=http://host.docker.internal:8100`
- Local backend: `AERONA_IMAGE_WORKER_URL=http://127.0.0.1:8100`

The model loads on the first job and is released after `AERONA_IMAGE_WORKER_IDLE_UNLOAD_SECONDS` without work.

### Worker backends

| Backend | Where | Model |
|---|---|---|
| `mlx` | Apple Silicon host (`make image-worker`) | `mflux-community/z-image-turbo-mflux-q4` |
| `diffusers` | NVIDIA container (profile `gpu`) | `unsloth/Z-Image-Turbo-unsloth-bnb-4bit` |
| `fake` | Tests and CI | Deterministic gradient PNG |

### Worker HTTP contract

| Method | Path | Result |
|---|---|---|
| `GET` | `/health` | Backend, model, loaded state, queue length |
| `POST` | `/jobs` | `{prompt, width, height, steps, seed, priority}` → `{job_id}`; `manual` jobs run before `bulk` ones |
| `GET` | `/jobs/{id}` | Job status and last progress event |
| `GET` | `/jobs/{id}/events` | SSE: `queued`, `loading`, `encoding`, `step`, `decoding`, `done`, `error`, `cancelled` |
| `GET` | `/jobs/{id}/image` | The PNG of a finished job |
| `DELETE` | `/jobs/{id}` | Cancels a queued job |

One job runs at a time. A job that exceeds its time limit fails, and the worker restarts its model process.
