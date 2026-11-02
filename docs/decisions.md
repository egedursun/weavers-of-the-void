# Decisions

| # | Topic | Decision |
|---|---|---|
| 1 | Lore language | Asked once in the genesis wizard when the Creator is created. Default English, Turkish available. Stored on the world and immutable afterwards. Code and prompts are English. |
| 2 | Legacy data | Superseded: the legacy world and its media are migrated into the rewrite by a one-time migrator (see docs/migration-plan.md). |
| 3 | gorsel-lab | Not ported. Image generation is part of the app through the `image-worker` service. |
| 4 | Deployment | Docker compose with backend, nginx web and an optional GPU image worker. Single user. Claude auth through the subscription OAuth token, never an API key. |
| 5 | UI foundation | shadcn-admin template (MIT) with shadcn/ui. Sizes are defined only in `components/ui`. Lint rules and a Playwright consistency test enforce it. |
| 6 | Themes | Dark (default) and light, both from `theme.css`. The legacy high-contrast mode is folded into the light theme's contrast targets. |
| 7 | World colors | One palette per world, defined once and shared by the 2D cosmos, the 3D cosmos and the map. |
| 8 | Map geometry | Computed on the server only, persisted, and served to the client as data. The client only renders. |
| 9 | Destructive confirmations | Typed English words: RESET, RESTORE, REPLACE, MERGE. |
| 10 | Realtime events | Only events the server actually emits exist. Each event kind is a typed enum shared through the OpenAPI schema. Dead legacy kinds are dropped unless a spec section defines an emitter. |
| 11 | Path finder | Works across every node type in the graph: entities, sons, the Creator, worlds and foreign gods. |
| 12 | World rules editor | A virtualised, searchable table grouped by rule group, not one giant form. |
| 13 | Long work | Every long operation is a job resource (`/api/jobs`) with progress over SSE. Changes are pushed as typed events, not discovered by polling. Large collections (state, graph, entity detail relations) are paginated or windowed. |
| 14 | Lore language mechanics | Procedural conlang naming stays. Turkish grammar helpers are not ported. |
| 15 | Model | One constant, `claude-haiku-5-5` (Claude Haiku 5.5), for every LLM role. No per-role model settings and no fallback; a test asserts every role resolves to it. |
| 16 | Language heuristics | Turkish stemming, stop words, dialect checks and `LIKE` matching on chronicle text are replaced by structured data: per-epoch counters, reward streaks and refunds live in tables. |
| 17 | Chronicle timing | The chronicler runs after Fate's verdicts are committed, so the chronicle never contradicts a verdict. |
| 18 | Fate disabled | Creations are stored with an explicit `unjudged` verdict instead of being silently converted to accepted. |
| 19 | Births at the lowest rarity | A son of the lowest rarity gives birth at the same rarity (the floor), never crashes. |
| 20 | Cross-world reach | One rule everywhere: a target is reachable when it is in the same world or an active route connects the two worlds. |
| 21 | Tool metadata | Action cost, essence cost, rarity gate and read-only flag are explicit per-tool fields, never inferred from descriptions. |
| 22 | Atomic verdicts | A verdict, its rewards, its rejection rollback and its done-marker are written in one transaction. |
| 23 | Engine transactions | No transaction spans an await. Engine phases run as separate units of work under the single writer lock. |
| 24 | No fixed gameplay numbers | Creation costs, rarity turn limits, prompt caps, mortal-agent settings and stream timings move into the rules registry. |
| 25 | Nested world birth | `discover_route` records a pending discovery. The world-birth LLM call runs as a deferred step at the end of the epoch. |
| 26 | Tool descriptions | Model-facing tool descriptions are prompts and live in `prompts/`, keyed by tool id. |
| 27 | Worship | An entity has exactly one patron: the Creator or one son. Cult paths and manual assignment follow the same rule. |
| 28 | Passions, reputation, achievements | Driven by structured action kinds recorded with every action, through a kind-to-passion mapping table. No text matching. |
| 29 | Return from death | The achievement fires only on an actual resurrection. |
| 30 | Scenarios | Completing the same scenario again does not add points again. |
| 31 | Unanswered prayers | Counted over a decaying window (tunable length and decay). |
| 32 | Declared but unused rules | Wired into the mechanic they describe (for example the rite's devotion and prosperity effects), never left dead. |
| 33 | Book exports | One export model renders both the printable HTML book and the Markdown codex. |
| 34 | Auto council | Every N epochs (tunable, default 4) as a deferred end-of-epoch step. |
| 35 | War definition | A war is an active row in the wars table. Mood, goals, achievements and the engine all read that row. Every war declaration, from any source, goes through one war service, which enforces caps and breaks alliances. |
| 36 | Ordinals | English ordinals. |
| 37 | Determinism | Every engine tick uses a seeded RNG derived from the world seed and epoch number. |
| 38 | Maps | The backend is the only map generator. Legacy map equality is not required. |
| 39 | Spatial model | Voronoi region adjacency is the single distance model (hop distance). The location tree is used only for containment. Region-less entities are never treated as co-located. |
| 40 | Explicit fields | Water, underworld, temple, miracle kind, debt terms and similar facts are typed fields or enums, never detected from names or text. |
| 41 | Mortal creations | Reviewed by Fate like son creations, in batch (tunable switch, default on). |
| 42 | Mortal knowledge | Mortals' read tools only return what the mortal can know: their world, region and connected regions. |
| 43 | Peace miracle | Also ends ongoing wars between the affected parties. |
| 44 | Turkish-only tunables | Dropped together with the grammar code. |
| 45 | World types | All designed world types are implemented: the 11 built ones plus ringed, asteroid belt, tidally locked, void pocket, god's palace, generation ship and corpse-world. |
| 46 | Travel method costs | Real mechanics, not flavour text: gate sacrifice, sails failing when their star dies, dream travellers who may not return, memory loss on the river of the dead. All are tunable. |
| 47 | Son sanity | Implemented as a son stat affected by cosmic horror, with tunable thresholds and effects. |
| 48 | Civilization tiers | Tiers unlock defined capabilities (mortal tools and engine actions) through a tier-unlock table, in addition to their military and goal effects. |
| 49 | Foreign-god conflict | One conflict resolver shared by the engine and the son war tool. |
| 50 | Souls | Souls go to the realm of the dead of their own world. Burning an archive destroys only knowledge held in that archive. |
| 51 | Cosmic travel resource | Defined when the cosmos is created at genesis; the player can edit it later. |
| 52 | Siege morale | Follows the rule's meaning: when the attacker wins the field but the walls hold, the attacker's army loses morale. |
| 53 | Prosperity gains | Every prosperity gain, tribute included, goes through the shared diminishing-returns function. |
| 54 | Syncretism | A real secondary reverence relation with a weaker effect than worship. The single-patron rule still holds. |
| 55 | Rule groups | Split by subsystem (diplomacy, campaigns, society, life, knowledge, ...). Every key lives with the subsystem that reads it. Unused keys are wired up or removed. |
| 56 | War endings | Every way a war ends (victory, conquest, tribute, exhaustion, peace, betrayal) goes through one war-resolution service with one relation-effect table. |
| 57 | Name uniqueness | Names are unique across every node kind (entities, sons, the Creator, stars, worlds, foreign gods) through one name registry. |
| 58 | Naming rules | Each world's and language's naming rule is stored as structured phonology data, never as prose. |
| 59 | Tired motifs | Fate's structured output tags each creation with motif keys. The tired-motif detector counts tags, so it works in any lore language. |
| 60 | Discovery mode | A guest world opens read-only, side by side, through a separate connection. The live database is never swapped. |
| 61 | Undo ledger | Included in v1. Every player action is recorded with its inverse and can be undone. |
| 62 | Startup completion job | The job that fills in missing prompts and portraits runs as a visible job after startup. It is controlled by a tunable switch (default on). |
| 63 | Telemetry | LLM metrics and logs live in a separate SQLite file (`telemetry.db`), outside backups and exports. |
| 64 | Rarity names | common, uncommon, rare, epic, legendary, mythic. |
| 65 | Duplicate tunables | Rules that mean the same thing are merged into one key when their subsystem is ported. The registry generated from `rules-registry.json` is the starting point, not the final layout. |
| 66 | Operational settings | Server, UI, metrics, backup, model-retry and image-generation settings stay editable in the same registry, under system groups, so the player keeps full control. |
| 67 | Rarity and cost tables | Their numbers are flattened tunables in the registry. `catalog/` builds typed objects (for example `Rarity`) from the current rules snapshot. |
| 68 | Rule stability | When a world is created, the full rule snapshot is stored with it, so a later change to a code default never silently rebalances an existing world. The UI shows where a value differs from the current default. |
| 69 | Rule consistency | Related rules declare pair constraints (min below max, thresholds in order). Updates that break a constraint are rejected. |
| 70 | Descriptions | Power and tool descriptions that quote numbers render them from the live rules, never as fixed text. |
| 71 | Engine-written lore lines | The engine records chronicle lines as English text plus a `template_key`. For worlds whose lore language is not English, an end-of-epoch localisation step (Haiku, batched) translates that epoch's engine lines into the lore language. Code holds English templates only. |
| 72 | Engine phase contract | Every engine phase is `async def phase(ctx: TickContext) -> None`, registered as `Phase(name, run)`. The pipeline opens one write unit per phase (decision 23). Randomness comes only from `ctx.rng(stream)`, chronicle lines only from `ctx.chronicle(...)`, counters from `ctx.count(...)`. |
| 73 | Tributes and captives | The typed row is the source of truth. The bond exists only for graph display and is kept in sync by the war service. |
| 74 | Live agent stream | Supersedes decision 10 for the streaming kinds, because spec 12 part 5 and spec 10 define their emitters: `agent.stream` (batched text), `agent.thought`, `agent.tool_preparing`, `agent.tool_writing`, `agent.tool_called`, `agent.tool_result`, `agent.writing` (long structured writes) and the `stream.hello` connect message. The LLM client emits them from the SDK partial-message stream; they carry typed payloads, tool results carry a server-set `quiet` flag instead of prefix sniffing, the transient ones are never kept in the replay buffer, and the emit intervals are tunables (`server.stream_emit_interval_ms`, `server.tool_write_step_chars`, `server.writing_emit_interval_ms`). |
| 75 | Single write unit, no joining | The legacy `tx()` joined an already open transaction. The rewrite takes one non-reentrant lock per write unit (decision 23), so nested calls never join: a unit that needs another unit's work calls the service function inside its own session, and an error rolls back the whole unit. Savepoints (`begin_nested`) isolate the steps that must not abort their siblings (data repairs, player actions). |
| 76 | Canon cache removed | The incremental `CanonCache` was never consulted by the engine: every tick loads its own scope inside its single write unit (decisions 23 and 75), so a cache outliving a unit could only serve stale rows. It was deleted rather than wired in; no memo cache depends on a canon or location version counter (CORE-005, CORE-006, CORE-007). |
| 77 | Media storage | Images live in an S3-compatible object store (MinIO in Docker, a filesystem store for local development and tests) behind one MediaStore interface. Thumbnails are generated on demand and cached in the store. The browser only reaches media through the backend. |
| 78 | Legacy vocabulary | The migrator's legacy schema vocabulary (Turkish table, column, enum and tag names) lives only in a data file (migration/legacy/schema_map.json). Migrator code uses English names only. |
| 79 | English-only text repairs | The narrative sweep and the ending backfill write and match English sentences, so they run only when the lore language is English. Worlds in another lore language keep their text untouched; endings for new deaths there come from the localised engine lines (decision 71). |
