# 18 — The Divine Will

The Divine Will is the Creator's own agent: a chat panel in the bottom-right corner of the app through which the player, and only the player, commands the world, plans multi-step creation, asks about the lore, produces creative work, learns the mechanics and foresees outcomes. It is the Creator's divine self, so everything it says and does is part of the world's record and appears in full in the lore book and the Codex.

This spec is the contract every part of the build follows. Every name below is the name used in code.

## 1. Principles

- **D1. One model seam.** The Divine Will uses the model chain of the conversation role (spec 22) through `LlmClient`; a model that sees pictures reads the attached ones.
- **D2. Everything, through one door.** Every god action reachable from the frontend is reachable by the Divine Will, because it acts through the same action catalog (`services/player/catalog.py`, `ACTIONS`) and the same runner (`run_action` / `perform`), with the same validation, essence, ledger, `acting(ActorKind.CREATOR, …)` scope and undo. A new action is automatically a Divine Will action.
- **D3. Nothing is cut.** No tool result, lore text, document or artifact is ever truncated. Large results are paged under a token budget and the model asks for the next page through a handle. The model decides when it has read enough.
- **D4. Agentic retrieval.** Retrieval is a set of tools the model drives in a loop (search, read, expand along the graph, enumerate exhaustively, read more), not a fixed top-k injection. "All X" questions are answered by exhaustive enumeration, never by similarity.
- **D5. The record is complete.** Every session, cycle, message, tool call, tool result, confirmation, plan, forecast, attachment and artifact (with every version) appears in the book and the Codex, well formatted, never truncated (rule 7).
- **D6. Prompts never constrain the lore** (rule 2). Divine Will prompts carry no imagery, no example sentences that carry images, no persona, no gendered default. Style in Creative Work comes from the player and the world's canon.
- **D7. Language.** The Divine Will answers in the language the player writes in. Everything it writes into the world (names, descriptions, chronicle text, any free-text action field) is written in the world's lore language (`cosmos.lore_language`). Artifacts are written in the language the player chooses for them (asked in Creative Work, default: the player's language).

## 2. Modes

A mode is an intent plus a fixed toolset; all modes are one agent. The player switches modes with Tab / Shift+Tab inside the composer, or with the mode bar. `DivineWillMode` values:

| Mode | Value | May change the world | Output | Toolsets |
|---|---|---|---|---|
| Command | `command` | Yes, now; destructive or costly acts ask first (§6) | Performed acts with undo | read, act, rules-read, artifacts-read, attachments |
| Plan | `plan` | Never while planning; only by executing an approved plan | A plan (versioned) → stepwise execution | read, rules-read, plan, foresight, attachments |
| Ask Lore | `ask_lore` | No | Answer with sources | read, artifacts-read, attachments |
| Creative Work | `creative_work` | No | Artifacts (stories, chapters, screenplays…) and brainstorming | read, artifacts, attachments |
| Mechanics Guide | `mechanics_guide` | No | Explanation of rules and mechanics | mechanics, catalog-read |
| Foresight | `foresight` | No (works on a copy) | A forecast report comparing outcomes | read, rules-read, foresight, attachments |

**Command vs Plan contract.**
- Command performs in the same cycle. It never writes a plan. When a request is large, open-ended or multi-staged, the agent does not plan silently: it answers with a `suggest_mode` notice ("this is better as a plan") and the player decides.
- Plan never writes to the world while planning. It produces a `Plan` (§8). Nothing runs until the player approves it and presses Execute (or says so). New wishes during execution become plan steps; no act happens outside the plan.

## 3. Sessions and cycles

- One active session (`divine_will_sessions` with `closed_at IS NULL`). Resetting closes it and opens a new one. Closed sessions are kept forever (they are part of the record, D5) and shown in the book, the Codex and a "Past sessions" view; only the active session is the chat.
- A **cycle** is one player query and everything until its final answer: thoughts, tool calls, tool results, confirmations and intermediate text all belong to that cycle.
- **Memory window:** the context of a new cycle holds the last `divine_will.remembered_cycles` completed cycles of the active session (rule, default 10, 1–100, group `CONTEXT_BUDGETS`). Older cycles stay visible in the chat above a "beyond memory" boundary but never enter the context.
- Within the window, old cycles enter as: player text, mode, final answer in full, and a compact trace of tool calls (tool, arguments, a one-line outcome and the result handle). Full results stay retrievable through their handles while the cycle is in the window.
- Attachments and their document chunks belong to their cycle and leave retrieval when it leaves the window (the files and their record stay).

## 4. Data model

All tables in `db/tables/divine_will.py`, one migration. Foreign keys cascade from the session.

- `divine_will_sessions`: `id`, `opened_epoch`, `opened_at`, `closed_at`, `closed_epoch`, `title`.
- `divine_will_cycles`: `id`, `session_id`, `ordinal`, `mode` (DivineWillMode), `epoch`, `status` (`CycleStatus`: running, awaiting_confirmation, done, failed, cancelled), `player_text`, `final_text`, `model`, `input_tokens`, `output_tokens`, `steps`, `error`, `started_at`, `finished_at`.
- `divine_will_events`: `id`, `cycle_id`, `ordinal`, `kind` (`CycleEventKind`: player, thought, text, tool_call, tool_result, confirmation_request, confirmation_reply, notice, retry, error), `tool`, `payload` (JSON, plain text values only), `handle`, `created_at`. The full trace of a cycle, in order.
- `divine_will_handles`: `key` (opaque), `cycle_id`, `tool`, `query` (JSON), `total`, `created_at`. A handle stores the query, not the result; reading it re-runs the query at the next offset under a deterministic ordering.
- `divine_will_confirmations`: `id`, `cycle_id`, `action_id`, `input` (JSON), `reason` (`ConfirmationReason`: destructive, costly, both), `preview` (JSON: the changes the dry run produced, §6), `status` (pending, approved, declined, expired), `decided_at`, `ledger_entry_id`.
- `divine_will_attachments`: `id`, `cycle_id`, `kind` (`AttachmentKind`: image, document), `filename`, `mime`, `size`, `media_key`, `markdown_key`, `status` (`AttachmentStatus`: stored, converted, indexed, unreadable), `seen_by_model` (bool), `note`.
- `divine_will_chunks`: `id`, `source` (`ChunkSource`: entity, typed_section, chronicle, incident, son, foreign_god, world, star, creator, word, epoch, note, message, council, artifact, attachment), `source_id`, `node_id`, `cycle_id` (attachments only), `ordinal`, `text`, `tokens`, `vector` (float16 blob, 384 dims), `digest`, `updated_epoch`.
- `divine_will_artifacts`: `id`, `title`, `kind` (`ArtifactKind`: story, chapter, novel, screenplay, poem, chronicle, encyclopedia, outline, notes, report, plan, forecast, html_page), `format` (`ArtifactFormat`: markdown, fountain, html), `status` (`ArtifactStatus`: draft, final), `language`, `mode`, `tags` (JSON list of text), `created_cycle_id`, `current_version`, `created_at`, `updated_at`.
- `divine_will_artifact_versions`: `artifact_id`, `version`, `body`, `summary`, `cycle_id`, `created_at`.
- `divine_will_artifact_nodes`: `artifact_id`, `node_id` (the subjects an artifact is about).
- `divine_will_plans`: `id`, `cycle_id`, `artifact_id`, `title`, `status` (`PlanStatus`: draft, approved, running, paused, done, failed, abandoned), `approved_at`, `finished_at`.
- `divine_will_plan_steps`: `plan_id`, `ordinal`, `title`, `action_id`, `input` (JSON), `depends_on` (JSON list of ordinals), `declared_impact` (`StepImpact`: safe, costly, destructive), `estimated_essence`, `status` (`StepStatus`: pending, running, done, skipped, failed, undone), `ledger_entry_id`, `job_id`, `result_text`, `error`.
- `divine_will_forecasts`: `id`, `cycle_id`, `epochs`, `status` (`ForecastStatus`: queued, running, done, failed, cancelled), `eta_seconds`, `interventions` (JSON list of `{action_id, input}`), `report` (JSON), `job_id`, `started_at`, `finished_at`.

These are the player-god's own records, created by the player and the Divine Will, not by the engine; they are not engine-changed tables for `check_control`, and they are not bookkeeping: they are rendered in the book and the Codex (§12).

## 5. Rules and settings

Rules (`rules/registry/divine_will.py`, `DivineWillRules`, field `divine_will` on `Rules`):

| Rule | Default | Range | Meaning |
|---|---|---|---|
| `remembered_cycles` | 10 | 1–100 | Completed cycles of the session the Divine Will keeps in mind |
| `max_steps` | 40 | 5–200 | Model replies one cycle may take |
| `page_tokens` | 6000 | 500–50000 | Token budget of one page of a tool result |
| `search_page` | 12 | 3–100 | Hits per page of a search |
| `costly_essence` | 25 | 0–100000 | Essence at or above which an act asks first |
| `forecast_max_epochs` | 3 | 1–10 | Most epochs a forecast may live |
| `index_batch` | 16 | 1–256 | Passages embedded per batch |

Settings (environment, `settings.py`, `.env.example`):

| Variable | Default |
|---|---|
| `AERONA_DIVINE_WILL_UPLOAD_MAX_MB` | 50 |
| `AERONA_DIVINE_WILL_UPLOAD_MAX_FILES` | 10 (per cycle) |
| `AERONA_EMBED_THREADS` | 2 |
| `AERONA_EMBED_MODEL_DIR` | `<data dir>/models/multilingual-e5-small` |

## 6. Acting, previews and confirmation

- `perform_action(action_id, input)` validates with the action's input model, then **previews** the act: it runs the action in a savepoint through the real runner, collects the `state_changes` it produced and the essence it spent, and rolls back. The preview is the act's true effect, not a guess.
- The act needs confirmation when the preview deletes a node or a record, ends a node (status to dead, destroyed, dissolved, ended), ends a world or a war, or spends at least `costly_essence` essence. Job actions (`ActionSpec.job`) cannot be previewed; they need confirmation when their declared cost is at least `costly_essence`.
- Otherwise the act runs at once through `run_action` and returns its ledger entry, a summary of changes and the undo handle.
- When confirmation is needed, a `divine_will_confirmations` row is written, the cycle status becomes `awaiting_confirmation`, a `divine_will.confirmation_requested` event carries the preview, and the turn ends with the agent saying what it waits for. Approving runs the act and resumes the same cycle with the result; declining resumes it with the refusal.
- `undo_action(ledger_entry_id)` uses the existing `/ledger/{id}/undo` service.
- While an epoch runs (`busy_group`), acting tools return a clear "the world is busy with an epoch" result; the agent may wait or tell the player.

## 7. Tools

All Divine Will tools are `ToolSpec`s with `agent=DivineWill` in `tools/divine_will/`, run through the tool runtime under `acting(ActorKind.CREATOR, …)` for writes. Every tool has a case in `tests/tools/every_divine_will_tool.py`, proven by `tests/tools/test_every_tool.py`.

Paging envelope (every list-like or long result): `{"items" | "text", "total", "shown", "handle", "next": bool}` within `page_tokens`, counted with tiktoken. `read_more(handle)` returns the next page.

- **read** — `search_lore(query, sources?, handle?)` hybrid search (§9); `read_node(node_id, part?)` the node's entry: identity, stats, typed sections, bonds, depth, lore and every change made to its records (paged); `read_records(node_id, table?)`; `enumerate(kind, filters?, sort?)` every matching record, exhaustive and paged; `graph_neighbours(node_id, bond_kinds?, depth?)`; `graph_path(a, b, depth?)`; `chronicle(filters)`; `explain(node_id? incident_id?)` causes, effects, steps and terms; `state_at(epoch, node_id)`; `ledger(filters)`; `world_overview()`; `read_more(handle)`.
- **act** — `search_actions(query, group?)`; `describe_action(action_id)` full input schema, cost and description; `perform_action(action_id, input)`; `job_status(job_id)`; `undo_action(ledger_entry_id)`.
- **catalog-read** — `search_actions`, `describe_action`.
- **rules-read** — `search_rules`, `read_rule` (also in mechanics).
- **act** also holds `set_rule(namespace, name, value)` and `reset_rule(namespace, name)`; plan steps and forecast interventions change rules with the reserved acts `rule:set` and `rule:reset`.
- **mechanics** — `search_rules(query)`, `read_rule(namespace, name)`, `search_mechanics(query)`, `read_mechanic(key)` (the interconnection registry), `read_game_rules(section?)` (docs/game-rules.md, paged).
- **plan** — `plan_create(title, steps)`, `plan_read(plan_id)`, `plan_revise(plan_id, steps)`; steps name catalog actions with inputs validated against their models.
- **foresight** — `forecast_estimate(epochs)`, `forecast_run(interventions, epochs)`, `forecast_read(forecast_id)`.
- **artifacts** — `artifact_create(title, kind, format, body, language, tags, node_ids)`, `artifact_read(artifact_id, version?)` (paged), `artifact_edit(artifact_id, edits)` where an edit is `{replace: {old, new}} | {insert_after: {anchor, text}} | {append: text} | {rewrite: body}`, each producing a new version, `artifact_list(filters)`.
- **artifacts-read** — `artifact_read`, `artifact_list`.
- **attachments** — `attachment_list()`, `attachment_read(attachment_id)` (paged markdown), `attachment_search(query)`.
- **notices** — `suggest_mode(mode, reason)` in every mode.

## 8. Plans

- A plan is a `divine_will_plans` row with steps and a mirrored `plan` artifact (readable, versioned, in the library).
- The player edits steps (reorder, change inputs, delete, add), approves, executes, pauses, resumes, skips a step or abandons the plan from the plan card.
- Execution is a job in the world's exclusive group. Steps run in order honouring `depends_on`. Each step is previewed (§6). Approval of the plan approves every step's declared impact; a step whose preview shows a destructive change it did not declare stops the plan and asks.
- A failed step stops the plan and the agent explains it in the plan's cycle. Each done step keeps its ledger entry and can be undone.

## 9. Retrieval

- **Embedder:** `multilingual-e5-small`, int8 ONNX (`onnx/model_quantized.onnx` from `Xenova/multilingual-e5-small`, pinned revision `761b726dd34fb83930e26aab4e9ac3899aa1fa78`), tokenized with `sentencepiece.bpe.model` (from `intfloat/multilingual-e5-small`, revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`, ids identical to the reference tokenizer). Files are fetched once into `AERONA_EMBED_MODEL_DIR` and checked by SHA-256. onnxruntime CPU, `intra_op_num_threads = AERONA_EMBED_THREADS`, memory arena off. Measured here: ~390 MB resident, ~670 MB peak while indexing, 1.2 ms a query, ~400 passages/s on 2 threads.
- Queries are embedded as `query: …`, passages as `passage: …`, mean-pooled and normalised.
- **Chunks** follow the record's structure: one record or section per chunk, split at paragraph and sentence boundaries to at most 256 model tokens with a 32-token overlap; every chunk carries its source and node.
- **What is read by meaning:** every record, section and text of the world once. The History and Changes sections of the entries are views of the incidents and the change ledger and are not embedded again: each incident is one passage carrying its line, name, every participant by role, facts, terms, steps, rumours and cause, and a node's changes are read in full through `read_node(part=changes)`, `explain` and `state_at`. The index grows with the world, never with the square of an incident's participants.
- **Index:** vectors in `divine_will_chunks`, held in memory as one normalised matrix; exact cosine search (no approximation at this scale). Built in the background when missing, kept fresh by an indexer that follows the change feed after `EPOCH_FINISHED` and `WORLD_CHANGED`, re-embedding only chunks whose digest changed. It waits while an epoch runs. Its job reports progress by the tokens read, so the share shown is the share of the work done. A player who cancels the job stops the reading until the world next changes (the mark of the last change, incident, fact, chronicle line and writing version moves); the job's own writes never restart it.
- **Hybrid search:** the existing FTS5 `SearchIndex` (BM25) and the vector search are fused by reciprocal rank fusion (k = 60). Results are paged with a handle; nothing is capped.
- **The loop is the model's:** it decomposes questions, issues several searches (including terms in the lore language when the player writes in another), reads sources in full, follows bonds with `graph_neighbours`/`graph_path`, enumerates exhaustively when asked for "all", and cites every claim by node or incident.

## 10. Attachments

- `POST /api/divine-will/attachments` (multipart), at most `AERONA_DIVINE_WILL_UPLOAD_MAX_FILES` files per cycle and `AERONA_DIVINE_WILL_UPLOAD_MAX_MB` each.
- Documents (pdf, docx, pptx, xlsx, html, csv, json, md, txt and other markitdown formats) are converted to markdown with markitdown, chunked and embedded as `attachment` chunks bound to their cycle.
- Images go to the model as image content when the model accepts images (probed once per process with a tiny image; result shown at `/api/divine-will/capabilities`). When it does not, the image is stored and the model is told in text that the player attached an image it cannot see, and the panel says so to the player. Never an error.

## 11. Foresight

- A forecast copies the world database (SQLite online backup) into a temporary folder twice, applies the interventions (catalog actions; job actions that need the model are refused) to one copy through the real runner, then lives both copies through `epochs` engine-only epochs in two processes in parallel with the same seed, and compares them.
- ETA = last epoch's engine seconds (`epoch_engine_phases`) × epochs × 1.15, shown before it starts. Measured here: 28–31 s an epoch for a young world, 65 s for a ten-epoch world.
- Progress events per epoch; cancellable. The report holds, per scenario, population, prosperity, deaths by flow, wars, communities and the nodes the interventions touched, and the chronicle lines of each copy; the agent reads it and explains the difference.

## 12. The record in the book and the Codex

- The Creator's entry gets "The Divine Will": every session (open and closed) with every cycle in full — mode, the player's words, the answer, each tool call with its arguments and outcome, each confirmation with its preview and decision, each act linked to its ledger entry and the nodes it touched — then plans with every step and outcome, and forecasts with their reports.
- Appendix "Writings of the Divine Will": every artifact, current version in full, with its kind, status, language, tags, subjects and the list of versions; attachments listed with their names and conversion status.
- Both the HTML/PDF book and the Codex render these with designed layouts; nothing is truncated.

## 13. API (`api/routers/divine_will.py`, prefix `/api/divine-will`)

- `GET /session` active session, cycles paged (newest last), memory boundary ordinal, capabilities.
- `GET /sessions` closed sessions; `GET /sessions/{id}`.
- `POST /cycles` `{text, mode, attachment_ids}` → 202 `{cycle_id}`; `POST /cycles/{id}/cancel`; `GET /cycles/{id}` full trace.
- `POST /confirmations/{id}` `{decision: approve|decline}`.
- `POST /session/reset`.
- `GET /modes`; `GET /capabilities`; `GET /index` (indexing status and counts).
- `POST /attachments` (multipart); `GET /attachments/{id}`; `GET /attachments/{id}/file`.
- Library: `GET /artifacts` (q, kind, status, format, language, mode, tag, node_id, sort, paging), `GET /artifacts/{id}`, `GET /artifacts/{id}/versions/{v}`, `GET /artifacts/{id}/diff?a=&b=`, `PATCH /artifacts/{id}` (title, status, tags, kind, nodes), `DELETE /artifacts/{id}`, `GET /artifacts/{id}/export?format=md|html|pdf|epub|docx|fountain`.
- Plans: `GET /plans/{id}`, `PUT /plans/{id}/steps`, `POST /plans/{id}/approve|execute|pause|resume|abandon`, `POST /plans/{id}/steps/{ordinal}/skip|undo`.
- Forecasts: `GET /forecasts/{id}`, `POST /forecasts/{id}/cancel`.
- Events on `/api/events`: the existing `agent.*` stream kinds with actor `{kind: "divine_will", cycle_id}`, plus `divine_will.cycle_started`, `divine_will.cycle_finished`, `divine_will.confirmation_requested`, `divine_will.artifact_changed`, `divine_will.plan_changed`, `divine_will.forecast_progress`, `divine_will.index_progress`.

## 14. Frontend

- `components/layout/divine-will/DivineWillDock.tsx`: the floating medallion (bottom-right, keyboard shortcut, unread and running indicators) and the panel shell (resizable side panel on wide screens, full screen sheet on phones, `role="complementary"` so global shortcuts keep working, never colliding with the live feed dock).
- `features/divine-will/`: mode bar and composer (Tab / Shift+Tab switch modes inside the composer, Enter sends, Shift+Enter breaks, multi-file drag-and-drop tray with per-file status, stop button), transcript (streaming text, collapsible thoughts, tool call cards with action, cost, result and undo, confirmation cards with the preview of changes, notices, retries), the "beyond memory" boundary, a markdown renderer (react-markdown, remark-gfm, rehype-sanitize) that turns node and incident references into links to the entry window, the reset button with `ConfirmDialog`, plan card, forecast card (ETA, progress, cancel, comparison), capability notices, and every loading, empty, error and disabled state with its reason.
- Artifacts drawer inside the panel and a full **Library** screen (`/library`): search, sort, filters by kind, status, format, language, mode, tag and subject; preview (markdown, fountain, html in a sandboxed iframe); versions with diff; export; ask the Divine Will to revise.
- Built from the design system (OrnateFrame, Section, Medallion, MiniStat, tones, icons), light and dark, responsive, accessible (`aria-live` for streaming), rewarding motion on acts and essence.

## 15. Proof

- Every tool proven through the real runtime (`every_divine_will_tool.py`).
- Scripted-model tests: a cycle with tool calls and streaming events; the memory window at N and at N+1; reset keeps closed sessions in the record; confirmation approve and decline resume the same cycle; preview rolls back; plan approve, execute, pause, fail, undo; forecast with ETA, two scenarios, cancel; vision fallback; attachment conversion and expiry from retrieval; paging reaches every item (no truncation); hybrid search fusion; index freshness after a change.
- Book and Codex render every Divine Will record in full.
- Frontend tests for the dock, mode switching, composer, confirmation, reset dialog, library filters and plan card.
