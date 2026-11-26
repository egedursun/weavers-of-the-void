# 20 — The Library of Universes

**Naming.** In the code a "world" is already a planet of a cosmos (`world_id`, the planet switcher, `/api/worlds/{id}`). The unit of the library is a whole cosmos with every planet in it, so it is called a **universe** in code and on screen (`universe_id`, `X-Aerona-Universe`, `/api/library/universes`). The player-facing page is "The Library of Universes"; each universe is a book on its shelf.

**Reuse, not reinvention.** The app already has a world package format (`.aerona`, gzip tar: `services/exchange.py`), backups and restore (`services/backups.py`), discovery (a read-only guest database) and reset. They keep working inside each universe; the library builds on them: export is the existing package, import loads a package into a new universe, backups live in the universe's folder.

The app holds many worlds. The first screen is the **World Library**: every world the player has made or brought in, each a book on a shelf, with search, filters, sort and paging. From it the player creates a world, opens one, renames it, sets its cover and notes, duplicates it, exports it as a single file, imports a world someone shared, archives it or deletes it. Opening a world enters its own management area: the whole app as it is today, bound to that world alone. Worlds never share a database, never lock each other and never mix records, files, jobs or live events.

## 1. Layout on disk

```
<data_dir>/
  library.db                 the library catalogue (§2)
  universes/<universe_id>/
    aerona.db                the world's own database (today's schema)
    images/ …                every file the world owns (images, book PDF, Codex, attachments, artifacts, exports)
    universe.json            a small manifest kept in step with the catalogue (§2), so a folder alone can be adopted
  models/                    shared, read-only model files (embedding model)
  imports/                   uploads being checked; removed when done
  trash/<world_id>-<ts>/     deleted worlds kept until `library.trash_days` pass, then removed
```

- `world_id` is a short opaque id (lowercase letters and digits, 12 characters) generated on creation; it never changes. The display name is free text and may be renamed.
- Every path a world writes is resolved through its **WorldPaths** (§3); nothing outside the world folder is written for a world except the shared model cache.
- **Adopting the old layout:** on start, if `<data_dir>/aerona.db` exists and no catalogue does, it becomes the first world: the database and every world file move into `worlds/<id>/`, the catalogue is created, and a note in the log says so. The move is atomic per file (rename on the same volume) and resumable.

## 2. The catalogue

`library.db` (its own small SQLAlchemy model and Alembic history, separate from the world schema):

- `worlds`: `id`, `name`, `summary` (from the cosmos seed or the player), `notes`, `cover_path`, `status` (`WorldStatus`: active, archived), `pinned`, `created_at`, `opened_at`, `updated_at`, `epoch` and `year` (cached from the world), `population`, `sons`, `size_bytes`, `schema_revision`, `app_version`, `origin` (`WorldOrigin`: created, imported, duplicated, adopted), `origin_note`, `tags` (JSON list).
- `library_events`: an append-only log of library acts (created, opened, renamed, exported, imported, duplicated, archived, restored, deleted, purged) with time and world id, shown on the library screen.
- The cached facts (epoch, year, population, sons, size) are refreshed when a world closes, after every epoch and on demand; the world's own database stays the source of truth.

## 3. One process, many worlds

- **WorldHub** (`services/worlds/hub.py`) holds the open worlds: `world_id → WorldRuntime` (its `Database`, `Services`, jobs manager, event bus, workers). A world is opened on first use and closed after `library.idle_minutes` without requests, jobs or listeners, or when the player closes it. At most `library.open_worlds` stay open; the least recently used idle one closes first; a world with a running job never closes.
- **Request binding:** every universe-scoped request names its universe in the header `X-Aerona-Universe` (or the `universe` query parameter for event streams, images and downloads, which a browser cannot give headers). A dependency resolves it to the open `WorldRuntime`; every existing router keeps its `ServicesDep` and receives that world's services. A world-scoped request without a world, or with an unknown, archived or deleted world, answers 409 with a code the frontend turns into "Choose a world" (it never falls back to another world).
- **Isolation:** no module-level state may hold world data. Caches keyed by nothing (names, rules, catalogues built from a world) are keyed by world or moved into `Services`. A test opens two worlds in one process and proves their records, events, jobs, files and caches stay apart.
- **Locking:** each world database has its own engine, WAL and busy timeout; jobs of different worlds run in parallel within `library.parallel_epochs`; one world's epoch never waits for another's lock. Catalogue writes are short and serialized.
- **Library routes** (`/api/library/*`) never need a world.

## 4. Lifecycle acts

> The package manifest described under **Export** is a format specification licensed under [CC BY 4.0](../../LICENSES/CC-BY-4.0.txt). See [LICENSING.md](../../LICENSING.md#the-open-format-specifications).

- **Create:** name (required), optional notes and tags → a new folder and database at the schema head; the world opens on its genesis screen (today's world-birth flow), and the catalogue records it.
- **Open:** marks `opened_at`, opens the runtime, and the frontend enters the world (§7).
- **Rename / notes / tags / cover / pin:** catalogue edits; the name is also written to the world manifest.
- **Duplicate:** an online SQLite backup of the source and a copy of its files into a new world; the new world records `origin=duplicated` and the source.
- **Archive / restore:** an archived world is closed and read-only to the library (cannot be opened until restored); archives are filtered out by default.
- **Delete:** after a ConfirmDialog naming the world, the world is closed, its folder moves to `trash/`, and the catalogue row is removed; it can be brought back from the trash until purged. Purge removes it for good.
- **Export:** a `.aerona` file: the existing `.aerona` package (`services/exchange.py`, with images), extended with a library manifest (format version, app version, schema revision, universe id, name, summary, notes, tags, created, exported, epoch, year, counts, file list with sizes and SHA-256). Large worlds stream to the download; the export runs as a library job with progress.
- **Import:** upload a `.aerona` package → it is checked (manifest, format version, hashes, zip paths confined to the archive, size limits `library.import_max_mb`, SQLite integrity check, schema revision not newer than this app) in `imports/`, migrated to the schema head, and becomes a new world (a new id always; the name gets " (2)" when taken unless the player renames it in the import dialog). A failed import leaves nothing behind and says why.

## 5. Library API

- `GET /api/library/universes?q=&status=&include_archived=&origin=&tag=&sort=&offset=&limit=` — paged universes `{items, total, offset, limit, facets: {tags, origins, statuses}}`, each facet a list of `{value, count}` (sort: last opened, created, name, epoch, size; archived ones only when `status=archived` or `include_archived=true`). Each row holds the catalogue fields of §2 with `is_open` and `running_jobs` (the kinds of the jobs running in it; `epoch` among them disables delete and archive with its reason).
- `GET /api/library/universes/{id}` — one universe with its catalogue facts, open/closed, running jobs and its recent library events.
- `POST /api/library/universes` `{name, notes, tags, summary}` → 201 with the new row.
- `PATCH /api/library/universes/{id}` `{name?, notes?, summary?, tags?, pinned?, status?}`; an archived universe takes only `status`.
- `POST /api/library/universes/{id}/open`, `/close`, `/duplicate` `{name}` (201 with the new row), `/archive`, `/restore`.
- `DELETE /api/library/universes/{id}` → to trash, answering the trash entry; `GET /api/library/trash` (paged `{items, total, offset, limit}`, each `{id, universe_id, name, deleted_at, purge_at, size_bytes}`), `POST /api/library/trash/{id}/restore`, `DELETE /api/library/trash/{id}` (purge).
- `POST /api/library/universes/{id}/export` → a library job; `GET /api/library/exports/{job}` progress; `GET /api/library/exports/{job}/file` download; `DELETE /api/library/exports/{job}` stops it or discards the file.
- `POST /api/library/imports` (multipart field `file`, the app's own page only, at most `library.import_max_mb`) → a library job that checks the file; `GET /api/library/imports/{job}` until its status is `waiting` with a `preview` of the package manifest; then `POST /api/library/imports/{job}/confirm` `{name?}` makes the universe, or `DELETE /api/library/imports/{job}` cancels it and leaves nothing behind.
- `GET /api/library/jobs` — every library job still held (exports and imports), so a reloaded screen finds its progress.
- A library job is `{id, kind, stage, status, done, total, progress, error, notes, file_name, size_bytes, preview, universe_id, universe_name}`; status is running, waiting (an import checked and waiting for its name), done, failed or cancelled.
- `PUT /api/library/universes/{id}/cover` (multipart field `file`, a PNG, JPEG or WEBP image), `PUT /api/library/universes/{id}/cover/from-media` `{file_name}` (one of the universe's own images), `DELETE /api/library/universes/{id}/cover` and `GET /api/library/universes/{id}/cover`.
- `GET /api/library/events?offset=&limit=&universe_id=` — the library's own log, paged `{items, total, offset, limit}`.
- `GET /api/library/events/stream` — library live events (`hello`, `universe`, `removed`, `trash`, `job`), each a `LibraryStreamEvent` carrying the changed universe row or job.

## 6. Rules and settings

Settings (env): `AERONA_DATA_DIR` (unchanged), `AERONA_LIBRARY_OPEN_UNIVERSES` (4), `AERONA_LIBRARY_IDLE_MINUTES` (20), `AERONA_LIBRARY_PARALLEL_EPOCHS` (2), `AERONA_LIBRARY_IMPORT_MAX_MB` (2048), `AERONA_LIBRARY_TRASH_DAYS` (30). World game rules stay per world as today.

## 7. Frontend

- `/` is the **Library of Universes**, outside the universe shell; the current overview moves to `/overview` and every link to `/` that meant the overview follows it. The Divine Will's writings keep `/library`.
- The library page: a gamified hall of shelves. Each world is a book card (cover from its world images or a generated crest from its name, name, summary, epoch and year, population, sons, last opened, size, origin badge, pinned star, archived seal). Search, filters (status, origin, tags), sort, pin, paging with show-more; a hero row of pinned and recent worlds; an empty state that offers creating or importing a world.
- Actions on each card: Open, Rename (inline), Notes and tags, Cover, Duplicate, Export (progress and download), Archive/Restore, Delete (ConfirmDialog naming the world); bulk-free, every act one click with a clear disabled reason when not possible (a running epoch blocks delete and archive).
- **Create** dialog; **Import** dialog (drop a file, see its manifest before confirming, name it, progress); **Trash** drawer with restore and purge; the library activity log.
- Inside a world, every API call carries the world id (the API client adds the header; event streams and file URLs add the query parameter). The world id lives in the URL as `?world=` on entering and in `sessionStorage` per tab, so two tabs can hold two worlds; the top bar shows the world name with a **Library** button that returns to `/` and a quick switcher of recent worlds. React-query keys start with the world id, so switching worlds never shows the other world's cache.
- Loading, empty, error and disabled states with reasons; light and dark; phone width.

## 8. Deploy and Docker

- The Docker image runs one process per container with `/data` as the library root (a volume); the entrypoint adopts an old single-world `/data/aerona.db` once. `docker-compose.yml` and the docs describe the volume, backups (copy `/data` while the app runs: worlds are backed up with SQLite online backup by `scripts/backup_library.py`), and the env settings of §6.
- The live deploy procedure (aerona-live) keeps working: the first start after this change adopts `data/aerona.db` as the first world.

## 8a. Per-universe state that must move

- **Paths:** every path derived from `data_dir` that belongs to a universe moves under `universes/<id>/` through `UniversePaths`: `aerona.db`, `media/` (file backend), `backups/`, `exports/` (book PDF, Codex), `work/` (exchange temp), `forecasts/`, `discovery/` and `discovery.json`, `secondary-backup-target.json`. `telemetry.db` is per universe too (its live events are keyed by the universe's own event ids and its model usage has no universe tag), so the usage page shows the open universe's usage. Process-wide stay: `library.db`, `logs/`, `models/`, `aerona.lock`.
- **Media:** in the S3 backend keys gain a per-universe prefix (`universes/<id>/originals/…`, `…/thumbnails/…`); the file backend is already one folder per universe; the adopted universe keeps its existing unprefixed keys through a `media_prefix` stored in the catalogue, so no object moves in a shared bucket.
- **Global listeners and handlers:** `install_change_tracking` and `install_error_ring` install once per process and route by bind/universe, so opening and closing universes never piles up listeners or handlers; a test opens and closes a universe many times and counts them.
- **Module caches:** caches keyed by a planet `world_id` (`TERRAIN_CACHE` in `api/routers/books.py`) gain the universe id in their key.
- **Frontend storage:** every `localStorage` key that holds universe data (bookmarks, onboarding, feed, divine will composer, atlas, records tab, compare, map, this-epoch, cards seals, world filter) is scoped by universe id; app-wide preferences (theme, sidebar, sounds) stay global.
- **Query cache:** each universe gets its own react-query client, so switching never shows another universe's data.
- **URLs built by hand:** every raw `/api/...` URL in the frontend (media, book, PDF, backups, exports, attachments, event stream) is built by one helper that adds `universe=`; a check script fails on a raw `/api/` URL string that bypasses it.

## 9. Book, Codex, records

The book and the Codex stay per world. The library's own log is not part of any world's book. Each world's book title page shows the world's library name.

## 10. The test instance

The test instance's library is filled by importing worlds made earlier with the real model (their exports), so several living worlds stand on the shelf; no world is generated from our own text.

## 11. Proof

- Two worlds open at once in one process: writes, reads, events, jobs, files and caches stay apart; an epoch in one does not block requests in the other.
- Adoption of the old layout is idempotent and resumable.
- Export → import round trip yields an identical database content (row counts and hashes per table) and files; tampered hashes, zip path escapes, too-new schema and corrupt databases are refused and leave nothing.
- Duplicate, archive, restore, delete to trash, restore from trash, purge; idle close never closes a world with a running job; LRU closing.
- Every world-scoped endpoint refuses a missing or unknown world; library endpoints work without one.
- Frontend: library screen states, create, import with manifest preview, export progress, delete dialog, world switcher, per-world query keys.
