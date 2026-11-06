# Weavers of the Void — Architecture

Weavers of the Void is a self-generating lore engine. The player is the Creator. The Creator's sons are god cards of a given rarity. Each son acts as an LLM agent with tools once per epoch. A deterministic, LLM-free world engine simulates mortals, peoples, settlements, wars, economy, faith, languages and the cosmos between those turns. Fate judges each epoch's creations and writes the chronicle.

This document describes the clean rewrite. The business logic is specified in `docs/spec/`, which was extracted from the legacy codebase and translated to English.

## Non-negotiable code rules

1. No comments of any kind in source code: no `#`, `//`, `/* */`, JSX comments or docstrings. Names and structure carry the meaning. `scripts/check_source_rules.py` enforces this in CI and in the test suite.
2. English only in code, identifiers, UI copy, prompts and file names. The same check rejects Turkish characters.
3. Every LLM prompt lives in one place: `backend/src/aerona/prompts/`. No module builds prompt prose inline. Modules pass typed context objects to the prompt catalog.
4. No magic numbers. Every balance number is a tunable in the rules registry (`backend/src/aerona/rules/registry/`). The registry can be edited at runtime from Settings → World Rules. Non-gameplay constants (paths, limits, timeouts and enums) live in `constants/` modules.
5. Every LLM call uses Claude Haiku. Every model resolution path and fallback ends at Haiku, and a test asserts this.
6. Every mechanism runs automatically and can also be triggered or overridden by the player. It also has a UI surface. A test checks that every API route has a frontend caller.
7. The UI is built on the proven shadcn-admin template and shadcn/ui components. Feature code composes those components and never restyles them. See the Design system section.

## Stack

| Layer | Choice | Why |
|---|---|---|
| Backend runtime | Python 3.13, `uv` | Modern async and typing; reproducible environments |
| HTTP | FastAPI + Uvicorn | Async, OpenAPI schema that drives the typed frontend client |
| Realtime | Server-Sent Events | One-way progress and world events; reconnect via `Last-Event-ID` |
| Database | SQLite (WAL) through SQLAlchemy 2 async + `aiosqlite` | Durable local DB with a typed ORM |
| Migrations | Alembic | Versioned schema; no ad-hoc `ALTER` at startup |
| Validation | Pydantic v2 | API schemas, tool input schemas, LLM structured outputs |
| LLM | `claude-agent-sdk` (Python) on the user's Claude Max login | Same auth model as today, no API key |
| Jobs | In-process asyncio job manager with persisted job rows | Epochs and long tasks are resumable and cancellable, with progress events |
| Frontend | React 19 + TypeScript + Vite | |
| Routing / data | TanStack Router + TanStack Query | Type-safe routes, cache, SSE-driven invalidation |
| API client | `openapi-typescript` + `openapi-fetch`, generated from the backend schema | Frontend and backend types cannot drift |
| UI foundation | [shadcn-admin](https://github.com/satnaing/shadcn-admin) template (MIT, 16k stars) with shadcn/ui on Radix + Tailwind v4 | A production-proven shell (sidebar, header, command palette, theming, data tables) with consistent control sizing out of the box |
| Icons | `lucide-react`, sized only by the components that host them | |
| Charts | recharts through the shadcn chart component | Same tokens as the rest of the UI |
| Graph | `react-force-graph` (2D/3D) | Knowledge graph |
| Map | Canvas renderer over `d3-delaunay` Voronoi | Same algorithm as the legacy map, rendered cleanly |
| Cosmos 3D | `@react-three/fiber` + `drei` | Declarative three.js |
| Tests | pytest + pytest-asyncio; Vitest + Testing Library; Playwright smoke tests | |
| Quality | ruff, mypy (strict), eslint, stylelint, prettier | |

## Repository layout

```
aerona/
  README.md
  Makefile                        dev, test, lint, typegen, migrate, seed
  docs/
    architecture.md
    design-system.md
    spec/                         business logic spec (English)
  scripts/
    check_source_rules.py         no comments, no Turkish, prompts only in prompts/
  backend/
    pyproject.toml
    alembic.ini
    migrations/
    src/aerona/
      main.py                     app factory and lifespan
      settings.py                 environment settings (pydantic-settings)
      constants/                  non-gameplay constants
        paths.py  limits.py  timeouts.py  http.py  events.py
      domain/                     pure types: enums and value objects, no I/O
        enums/                    rarity.py  entity_kind.py  bond_kind.py  chronicle_kind.py ...
        models/                   pydantic domain models
      catalog/                    static game data: rarities, stats, powers, domains,
                                  entity types, disasters, miracles, climates, classes
      rules/                      tunable balance registry
        registry/                 one module per namespace (limits.py, gods.py, war.py ...)
        service.py                load, validate, override, persist
      db/
        session.py                engine, WAL, single-writer lock
        tables/                   SQLAlchemy models, one module per aggregate
        repositories/             query objects per aggregate
      engine/                     deterministic LLM-free world simulation
        pipeline.py               ordered phase list for one tick
        context.py                tick context: rng, rules snapshot, unit of work
        phases/                   mortals, population, settlements, diplomacy, warfare,
                                  economy, faith, heroes, climate, cosmos, travel,
                                  exploration, horror, creatures, civilization,
                                  pantheon, sky, afterlife, death, reputation, goals ...
      language/                   procedural languages and naming
      cartography/                map generation
      llm/
        client.py                 SDK wrapper: Haiku-only, retries, timeouts, metrics
        structured.py             structured-output calls
      prompts/                    THE single source of every prompt
        templates/                one .md.j2 file per prompt
        catalog.py                prompt ids → template + typed context model
      agents/                     roles: son, fate, chronicler, genesis, summoner, deepener ...
      tools/                      son tools: schema, gating, cost, effect (one module per tool family)
      epoch/                      epoch orchestration: phases, concurrency, resume
      jobs/                       job manager, persistence, cancellation, progress
      events/                     event bus and SSE broadcaster
      services/                   application services used by the API
      api/
        routers/                  one router per domain
        schemas/                  request and response models
        errors.py
    tests/
      unit/  engine/  api/  agents/  fixtures/
  frontend/
    package.json
    vite.config.ts
    src/                          based on the shadcn-admin template
      main.tsx
      routes/                     TanStack file routes (thin: they mount feature screens)
      components/
        ui/                       shadcn/ui components: the only place sizes are defined
        layout/                   app shell: sidebar, header, main
        typography/               PageTitle, SectionTitle, Text, Muted, Stat
        domain/                   RarityBadge, EntityLink, StatBar, Portrait ...
      styles/                     theme.css (all tokens), index.css
      context/                    theme, font, layout, search providers
      api/                        generated schema + client + query keys
      realtime/                   SSE subscription → query invalidation
      features/                   one folder per domain, each with routes/components/hooks
        pantheon/ son/ entity/ chronicle/ epoch/ atlas/ map/ graph/ cosmos/
        languages/ prayers/ goals/ council/ notifications/ ledger/ settings/
        onboarding/ search/ backups/ metrics/
      constants/
      lib/
```

## Backend design

- **Layers.** The layers are `api` → `services` → (`engine`, `agents`, `epoch`) → `repositories` → `db`. `domain`, `catalog` and `rules` are pure and import nothing above them. An import-linter contract enforces this.
- **Async model.**
  - Uvicorn serves the API on the event loop.
  - Long work (epochs, genesis, deepening, imports) runs as jobs on the job manager. Jobs are asyncio tasks. Their state is persisted, so a crash leaves a resumable record.
  - Son agents within an epoch run concurrently, bounded by a semaphore tunable.
  - CPU-heavy engine ticks run in a worker thread (`asyncio.to_thread`), so the API stays responsive. This replaces the legacy "breathing" hacks.
- **SQLite writes.**
  - One async engine in WAL mode with `busy_timeout`.
  - Writes go through a unit-of-work that holds a process-wide async write lock, so writers never collide.
  - Reads run concurrently.
- **Determinism.**
  - The engine takes a seeded RNG per tick (world seed + epoch).
  - Given the same DB and seed, a tick is reproducible, which makes engine tests exact.
- **Rules.**
  - Tunables are declared as typed `Rule(key, default, min, max, group, label)` objects in the registry modules.
  - The rules service merges persisted overrides at startup and on change.
  - The engine reads an immutable snapshot per tick.
- **Prompts.**
  - Prompts are Jinja templates (with `StrictUndefined`) in `prompts/templates/`.
  - `catalog.py` maps a `PromptId` enum to a template and a Pydantic context model.
  - Agents call `prompts.render(PromptId.FATE_JUDGMENT, FateJudgmentContext(...))`, so nothing else holds prompt text.
- **Tools.**
  - Each son tool is declared once: name, Pydantic input model, rarity gate, cost function and effect handler.
  - The same declaration produces the SDK MCP tool, the UI tool catalog and the docs.
- **Events.** Engine phases, agents and jobs publish typed events to the bus. SSE streams them, and the frontend maps event types to query invalidations.
- **Errors.**
  - Domain errors map to 4xx.
  - Unexpected errors are logged with a correlation id and return a 500 carrying only that id.
- **Backups.**
  - SQLite backup API before every epoch.
  - The retention policy lives in the rules registry.
  - Export and import use a versioned archive format.

## Frontend design

- **App shell.** A fixed left navigation and a top bar (world, epoch status, search and notifications) frame the content area. Entity details open in a right drawer stack.
- **Server state.** All server state goes through TanStack Query. Local UI state stays in components, and URL state (filters, tabs, selection) lives in route search params, so every view is linkable.
- **Real-time updates.** One SSE connection publishes into a typed event emitter. Feature hooks subscribe to the events they care about.
- **Lazy loading.** Heavy views (map, graph, cosmos 3D) are lazy routes.

## Design system

The user wants no visual drift: every select is exactly as tall as every input and button, every body text has the same size, and nothing overlaps. Instead of hand-rolling a design system, Weavers of the Void adopts the **shadcn-admin** template (MIT) as its foundation and enforces these rules on top of it:

- **One theme file.** `frontend/src/styles/theme.css` holds every color, radius and font as CSS variables, with light and dark themes. Dark is the default. The Weavers of the Void brand palette is a deep celestial indigo with gold primary, plus six rarity colors (`--rarity-*`). Fonts: Cinzel for display headings, Inter for UI, tabular numbers for stats.
- **Only `components/ui` sets sizes.** Control height, padding, font size and radius are defined once in the shadcn components (`Button`, `Input`, `SelectTrigger`, `Textarea`, `Badge`, `Tabs` and so on) through their `size` variants, which share the same height scale. Feature code picks a `size` variant and never passes height, padding or font-size classes.
- **Typography components.** `PageTitle`, `SectionTitle`, `Text`, `Muted` and `Stat` are the only way to render text with a size, so each kind of text has exactly one size in the whole app.
- **Layout through gap.** Feature layouts use flex or grid with `gap-*` from the spacing scale. No margins on components, no arbitrary values (`[13px]`), no inline `style` except computed geometry for canvas, map and graph.
- **Lint enforcement.** ESLint `no-restricted-syntax` rules reject arbitrary Tailwind values, text-size classes and height or padding classes on controls in `src/features/**` and `src/routes/**`.
- **Visual consistency test.** A Playwright test visits every route on desktop and mobile widths and asserts:
  - every visible control of the same size variant has the same computed height and font size;
  - no two text boxes overlap;
  - no element overflows its container horizontally.
  It runs in CI alongside the screenshot smoke tests.
- **Living reference.** `/design` renders every component and typography role in both themes.

## What is not ported

- `gorsel-lab`.
- Turkish-grammar machinery (suffix harmony, possessive fixing). Code and prompts are English. The lore output language is chosen once while creating the Creator in the genesis wizard (default English, Turkish available), then stored on the world and passed to every prompt as an output-language directive. It cannot be changed afterwards.
- Startup "repair passes". They existed because the legacy schema allowed invalid states. The new schema prevents those states with constraints and migrations.
- Importing the legacy Turkish database. The new world starts fresh.

## Image generation

The app generates images for records (the Creator, sons, foreign gods, worlds and entities) from image prompts written by the LLM. Generation runs in a separate `image-worker` service behind a small HTTP contract: enqueue a job, stream progress (`loading`, `encoding`, `step k/n`, `decoding`, `done`, `error`) and fetch the PNG. The backend owns the queue (one GPU means one job at a time, and manual requests go ahead of bulk ones). Images are only ever added, never replaced. Auto-generation at the end of an epoch is a tunable rule. There are two worker backends behind the same contract:

- `diffusers`: containerized, for NVIDIA hosts (compose `gpu` profile, CUDA base image).
- `mlx`: Apple Silicon. Docker on macOS cannot reach Metal, so this backend runs natively on the host (`make image-worker`). The containers reach it at `host.docker.internal`.

Model weights come from a pre-quantized repo and live in a named volume, never in the image. The worker releases the model after an idle timeout (a tunable rule). `IMAGE_WORKER_URL` empty means image generation is disabled and the UI says so.

## Deployment

Single-user, local-first. `docker compose up` brings up:

- `backend`: Python image (multi-stage, `uv` lockfile, non-root user, healthcheck on `/api/health`).
  - SQLite and backups live in the `aerona-data` volume.
  - The Claude Agent SDK authenticates with the user's Claude subscription through `CLAUDE_CODE_OAUTH_TOKEN` (created once with `claude setup-token`), passed from an `.env` file that git ignores. No API key.
- `web`: the frontend built with Vite, served by nginx. nginx also reverse-proxies `/api` to the backend, with SSE buffering disabled.
- `minio`: the S3-compatible media store behind the `MediaStore` interface (decision 77), with the `aerona-media` volume, a healthcheck and no host port. `minio-init` creates the private bucket with `mc` before the backend starts. The profile `media-console` publishes the MinIO console on `127.0.0.1` only.
- `image-worker` (profile `gpu`): the diffusers worker with an NVIDIA device reservation and an `aerona-models` volume.

Every setting comes from environment variables declared in `settings.py`, with a checked-in `.env.example`. Ports bind to `127.0.0.1` by default. Local development without Docker is `make dev`: backend with reload, Vite dev server, and optionally the native image worker.

## Mechanic coverage

`docs/spec/coverage.md` is a traceability matrix. Each row is one legacy mechanic, with:

- the spec section;
- the new module;
- the automatic trigger;
- the manual player control;
- the UI surface;
- the test.

A mechanic counts as ported only when every column is filled. Independent review agents audit the matrix against the legacy source at the end of each phase, so nothing is skipped or forgotten.

## Delivery phases

1. Specs (in progress) → `docs/spec/`.
2. Skeleton:
   - repo, tooling and the source-rules check;
   - DB schema and migrations, the rules registry and catalog;
   - the design system and app shell.
3. Engine: phases ported module by module, each with deterministic tests and an LLM-free multi-epoch simulation test asserting that the world grows.
4. LLM layer: client, the prompt catalog, tools, agents and the epoch orchestrator with jobs and SSE.
5. API, plus the typed client.
6. Features in the UI, view by view; the route ↔ caller coverage test.
7. Hardening: Playwright smoke tests on desktop and mobile, independent review agents, fixes.
