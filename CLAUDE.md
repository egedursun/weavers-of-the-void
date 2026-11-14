# Standing rules from the user (always apply, every session)

1. **No unneeded tests.** Never run the full backend suite, broad `-k` sweeps, Playwright or e2e on your own initiative. Per change: ruff, mypy, lint-imports, `scripts/check_source_rules.py`, `npx tsc -b`, eslint, plus at most the few test files that directly cover the touched code. If those pass, commit, push and deploy. Run broad suites only when the user explicitly asks.

2. **Prompts never constrain the lore.** Whatever seed, god or world the player creates (sea myth, vampires, cosmic myth, anything), the lore must be able to go there. A world that drifts to the same images whatever the seed is a defect. Images from the player's seed, typed values and the world's own canon are fine, and the model inventing images is fine; our text pushing imagery is not. Any text the LLM sees (prompt templates, schema descriptions, tool texts and results, `prompts/data`, `catalog` lines, chronicle strings, genesis template seeds, frontend placeholders and suggestion lists) must let the world become any kind of lore:
   - No imagery through exemplification: no example lists, sample sentences, canned narrative lines or template seeds that carry images (lamps, threads, salt, bone…).
   - No figurative metaphors in our own wording (weave, woven, thread, stitch, web, tapestry, "threads of fate"): use plain verbs and nouns.
   - Never fix drift by constraining the model (bans on its own images, anti-monoculture rules): fix our text.
   - No quotas or mandates: forced conflict, rivalry, tension, rebellion, grudges, or mandatory hidden truths or prices.
   - No fixed creator persona or hostile default.
   - No gendered defaults: no he, his, father or brother.
   - No genre-steering examples (salt, death, ash…).
   - No "strange" forcing.
   - No hardcoded visual medium: image style is applied at render time.

   When you touch such text, read all of it, not by keyword, and rewrite anything that pushes a theme, tone, conflict, gender or look the seed did not ask for. A new feature must reduce constraints, not add them.

3. **Every dynamic is fully wired.** Anything created (a table, enum value, type, mechanic, rule, tool, phase, profile field, bond kind, event, setting) must connect end to end:
   - engine effects and the epoch phases that read it
   - agent tools and their schemas
   - prompts and context
   - API, frontend views and god (son) tools to create, edit, hold and delete it
   - the Codex and the lore book with labelled values
   - integrity checks, legacy mapping and the spec

   Nothing may be label-only, orphaned or silently deferred. Trace each new thing through every consumer before calling it done.

4. **No comments or docstrings, ever.** Never write comments, docstrings, commented-out code or explanatory headers of any kind in any language. That covers Python, TS/TSX, CSS, Jinja and SQL/migrations, including `#`, `//`, `/* */`, `"""…"""`, JSDoc and TODOs. Code must explain itself through names and structure. `scripts/check_source_rules.py` must report 0 violations.

5. **Frontend is production grade and gamified.**
   - Build every screen from the design system: `components/ui`, `components/domain`, typography, tones, icons and tokens. Follow the eslint class policy: no arbitrary values, no margins on controls, no raw `<button>`.
   - Every view must be polished and consistent. Cover loading, empty, error and disabled states, with a reason for each disabled state.
   - No overflow: long lists are paged with show-more. Layouts must be responsive down to phone width. Light and dark themes must both work, and accessibility roles and labels must be present.
   - Every value must be readable and editable.
   - Make it feel like a game: rewarding feedback, clear progress, tasteful motion, visual hierarchy, icons and medallions, and a strong sense of the player's power as a god.
   - Never ship a rough or placeholder UI.

6. **The god controls everything the engine does, from the frontend.** No god-simulator or lore-engine function may exist in the backend without a control in the frontend:
   - Every table, typed thing and mechanic the engine creates or changes needs god actions to create, edit, hold (lock against the engine) and delete it, with every value editable.
   - Those actions must be registered in the action catalog and reachable from a polished control panel in the app: the entity drawer, the atlas or the mechanic panels, in the same style as the existing control panels.
   - A backend mechanic without its frontend control surface is unfinished work, never a later task. This applies to everything already built and to everything integrated from now on, in the same change that adds it.
   - **Every kind of thing, always.** A feature for things reaches every kind of node at once: the Creator, sons, foreign gods, worlds (planets and moons), stars and every entity type. Never pick some of them. Sections that apply to every thing go only into `frontend/src/features/entity/sections/ThingSections.tsx`, which every node drawer page renders. `scripts/check_wiring.py` fails when a node drawer page does not render it. A section for some kinds only must say why the others cannot have it.
   - The only tables exempt are the bookkeeping ones listed in `BOOKKEEPING_TABLES` in `backend/src/aerona/constants/control.py` (fixups, cursors, counters, notifications, the player's action ledger, score and achievements, and the per-epoch goods-flow log). Only the user may add to that list.

7. **Every change reaches the Codex and the lore book.** Every update and addition (a new table, column, enum value, node kind, mechanic or record) must appear in the lore book (HTML/PDF) and the Codex (Markdown/zip), well formatted, with labelled values and a designed layout:
   - Records owned by a node (an entity, son, foreign god, world, star or the Creator) appear in that node's entry through `services/books/typed.py`. Every kind of node renders its typed sections in both the book and the Codex.
   - Records that belong to no single node appear as designed tables in the "Records of the Cosmos" appendix of both.
   - A table may stay out of the generic records only when dedicated book and Codex code renders it. Nothing is ever truncated.
   - A new kind of thing or a new layout needs its own readable rendering in both, not a raw dump.

8. **Every defect closes its class, and every tool is proven to work.** Fixing a defect is not enough. In the same change:
   - Add a test that fails on the old code and passes on the fix.
   - Add a mechanical guard (a check script, a pre-commit gate, a warning turned into an error, a type rule) so the same defect cannot come back. Then look for its siblings, defects that share the cause, and close them too.
   - Every agent tool (each son and mortal tool) has a case in `backend/tests/tools/every_son_tool.py` or `every_mortal_tool.py`. That case reaches the tool's success path through the real tool runtime. `tests/tools/test_every_tool.py` fails when a tool has no case or when its case is rejected. A new tool is unfinished until its case passes.
   - A tool call that crashes inside the runtime fails every test where it happens. Only a test that crashes a tool on purpose may say so with `@pytest.mark.tool_failure_expected`.
   - Deprecated library APIs are never used. SQLAlchemy and our own deprecation warnings are errors in tests, mypy reports deprecated calls, and `scripts/check_deprecated_apis.py` scans the code.

## Enforcement

These rules are enforced mechanically, and they bind Claude as much as anyone.

- **Claude Code hook** (`.claude/settings.json` → `.claude/hooks/guard_tests.py`). It blocks:
  - pytest runs that don't name individual test files, and pytest with `-n`
  - vitest runs on a directory
  - any run of more than 6 test files at once
  - every npm test script, Playwright, and the Makefile test and check targets

  Only the user may lift it, by creating `.claude/allow-broad-tests`; Claude never creates that file.
- **Git pre-commit** (`.githooks/pre-commit`, enabled with `git config core.hooksPath .githooks`). It runs on every commit:
  - `scripts/check_source_rules.py`: no comments or docstrings (rule 4). It also fails when a module that imports the hold guard (`held` or `unheld`) binds a local of the same name, since that local hides the guard and the step can no longer skip held nodes (rule 6).
  - `scripts/check_prompt_bias.py`: gendered defaults, conflict quotas, forced strangeness, steering examples (including bare example lists), reactions our text imposes, borrowed imagery and hardcoded image media in LLM-facing and UI text (rule 2). A newly found imagery family is added to it in the same change, with a case in `backend/tests/unit/test_prompt_bias_rules.py`.
  - `scripts/check_wiring.py`: enum types never used, tables never read, player actions missing from the catalog, catalog actions with no frontend caller (rule 3). It also flags any table an engine phase writes that has no compliance-catalogue row with registered god levers (rule 6). It also fails when a table is kept out of the generic book records with no dedicated renderer, when a kind of node is missing from the book's owners, or when the book or the Codex stops rendering typed sections for entities, sons, foreign gods, worlds, stars, the Creator or the records appendix (rule 7).
  - `scripts/check_control.py` (rule 6). It finds automatically, by reading the code, every table whose rows the engine changes over time. Each must be creatable, editable and deletable by a god lever that the frontend reaches, and whose code (followed through its calls) really touches that table. Several cases are covered without per-table levers:
    - Profile tables (one row per thing) through `profile:set`.
    - Every node-linked table through the generic `record_row:create`, `record_row:edit` and `record_row:delete` levers and the "Every record" section in each drawer.
    - Append-only histories and tables the engine wipes and rebuilds wholesale are outputs, not authored state.
  - `backend/tests/engine/core/test_god_control.py` whenever engine or db code changes (rule 6). It runs every engine step, found automatically, twice, on a rich cosmos stirred with creeds, old gods, plots, captives, spies, shades, sickness, curses, companies, every kind of lore, a beast and a war, and with every chance rule certain. First with every node held: nothing tied to a node may be created, changed or deleted. Then forced on one node: it must run cleanly. `tests/engine/core/test_eager_epochs.py` then lives that cosmos through five whole epochs with every chance certain, so rare branches meeting each other cannot crash an epoch. A new step that acts on a held node fails the commit. Skip held nodes with `held()` or `unheld()` from `aerona.db.write_guard` where the step chooses whom to act on. Field updates on held rows are already reverted for every node-linked table.
  - `scripts/check_deprecated_apis.py` on every commit (rule 8). It finds every retired SQLAlchemy, pydantic, FastAPI, Starlette, httpx and Alembic API, such as `Result.tuples()`, and fails on any use of one in source, tests or scripts.
  - `scripts/check_import_cycles.py` on every commit (rule 8). It fails on any circle of module-level imports, so every module imports on its own.
  - `scripts/check_hidden_controls.py` on every commit (rules 5 and 6). It fails when a screen swaps a god control for a note because a list is empty. The control stays on screen and is disabled with its reason.
  - `scripts/check_shared_labels.py` on every commit (rule 5). It fails when a section that every node drawer renders (anything reached from `ThingSections`) labels a field only 'Name', 'Kind' or 'Type'. Such a label clashes with the drawer's own fields, so name what the field holds.
  - `scripts/check_raw_ids.py` on every commit (rule 5). It fails when a screen shows a record by its raw number (`#${row.thing_id}`). Name the record or say what it is; only search keywords may carry a number.
  - `scripts/check_label_maps.py` on every commit (rule 5). It fails when a frontend label map names nearly every value of an enum but leaves some out, so every value shows its own label and icon.
  - `scripts/check_orphans.py` on every commit (rule 3). It fails on any backend function or constant that nothing uses. Wire it in or delete it.
  - `scripts/check_frontend_orphans.py` on every commit (rules 3 and 5). It fails on any frontend export, hook, component, constant or type that nothing in the app uses. Only an export of a module that keeps state of its own may be read by tests alone. Wire it in or delete it.
  - `tests/api/test_frontend_reads_every_field.py` on every backend or frontend change (rules 3 and 5). Every field of every value a read endpoint serves must be read by a screen. A field also counts as read through its `_label` or `_caption`, an id through the record or name it names, a `_key` through the text it keys, an entity stat through the stat grid the catalogue drives, and an enum list through its generated `…Values` constant. Show each value or stop serving it.
  - `scripts/check_folk_queries.py` on every commit (rule 8). It fails when a query finds mortals by a raw `location_id` of a place. A people or a polity holds no mortal directly, so such a query finds nobody there. Use `present_among` or `folk_among` from `engine/primitives/folk.py`, which reach the settlements of a people and the members of a polity.
  - `scripts/check_coin_units.py` on every commit (rule 8). It fails when an amount whose rule is in treasury meets the 0 to 100 wealth points of a thing without conversion. Spend and pay such amounts through `engine/economy/purse.py` (`take_coin`, `give_coin`, `coin_of`, `wealth_points`).
  - `scripts/check_zero_fallbacks.py` on every commit (rule 8). It fails on `stat(...) or <default>` and `hops(...) or <default>` with any default but 0, since a true zero (a dead hero's hp, a broken hull, a town in the same region) would read as missing. Use `stat_or` or an explicit None check.
  - `scripts/check_scene_colors.py` on every commit (rule 8). It fails when frontend code hands a CSS colour to three.js unresolved (`setStyle`, or a raw computed style in `new Color`). Theme tokens are oklch, which three.js cannot read; pass every colour through `colorHex` or `tokenHex` from `features/cosmography/visual/palette.ts`.
  - `scripts/check_counts.py` on every commit (rule 5). It fails when text writes a count straight before a plural word (`{len(rows)} records`, `{count} were`, a `{count} people` template), since a count of one then reads wrong. Count through `several()` from `aerona.core.grammar`, or `{count:person|people}` in a template filled by `fill`.
  - `scripts/check_theme_tokens.py` on every commit (rule 5). It fails when the theme declares a spacing or text token that the class merging in `frontend/src/lib/utils.ts` does not list, or lists one the theme lacks, since class merging then drops the class.
  - `scripts/check_zero_ids.py` on every commit (rule 5). It fails when a screen calls a data hook with an id that falls back to 0 (`useThing(row?.id ?? 0)`), since the hook then asks the server for record 0 while the id is missing. Pass null and let the hook wait until there is an id.
  - `scripts/check_record_cuts.py` on every commit (rules 7 and 8). It fails when a reader of the chronicle in the book, the Codex, search, the player services or the API filters lines by visibility or drops engine-folded lines. Use `shown_lines()` or `kept_lines()` from `db/repositories/chronicle.py`, or `feed_lines()` for the feed that shows a fold in their place.
  - `scripts/check_canned_lines.py` on every commit (rule 2). It fails on a pool of canned sentences (a module constant or a random pick over two or more prose lines or `Line`s). Tell a happening once, plainly, from its typed fields.
  - `scripts/check_moon_orbits.py` on every commit (rule 8). It fails when engine, agent, service or API code reads a world's `orbit` without telling a moon from a planet, since a moon's orbit is around its planet. Read the planet's through `root_of` or `planet_of`, or check `parent_world_id`.
  - `scripts/check_goods_ledger.py` on every commit (rule 8). It fails when code outside the goods ledger changes a stock's quantity by hand, since the flow then goes unlogged and a held lot can be touched. Move goods through `goods_of(...).add`, `take`, `move` or `shift_lot`.
  - `scripts/spec_coverage.py check` on every commit. Every done row must name test files, tests, frontend tests and modules that exist.
  - The proving gate on every backend change (rule 8):
    - `tests/tools/test_every_tool.py`: every son and mortal tool runs to success.
    - `tests/services/player/test_every_lever.py`: every god lever in the action catalog runs to success through the real action runner. A new lever whose payload the harness cannot fill gets a case in `tests/services/player/every_lever.py`. A lever whose `action`, `mode`, `op` or `operation` field picks between branches runs once for every value of it; a branch that needs its own setup gets a case in `BRANCH_LEVERS`. Every editor lever that takes `values` runs with real values from `EDITS`, never an empty dict, so its edit path is proven.
    - `tests/services/player/test_every_job.py`: every god job (summoning, births, worlds, fate controls) runs to success with stand-in ports.
    - `tests/api/test_every_endpoint.py`: every read endpoint answers a seeded, simulated world without a server error.
    - `tests/api/test_frontend_types.py`: the generated frontend types hold every schema, field and enum value the API serves, so `npm run typegen` is never forgotten.
    - `tests/unit/test_derived_world_fields.py`: only the heavens and levers that hold the value write a world value the heavens derive, and every value of the heavens' enums is produced or read by the engine.
    - `tests/tools/test_catalogue.py`: every tool field the model sees is described.
    - The whole-source guards: every near-total enum table read by subscript is total or declares what it leaves out (`tests/unit/test_total_tables.py`), names are found by whole words (`tests/unit/test_word_matching.py`), a tool text that lists an enum lists every value of it (`tests/unit/test_tool_enum_lists.py`), every god lever id is registered once (`tests/unit/test_unique_levers.py`), every API schema has a name of its own so the generated frontend types never merge two (`tests/api/test_unique_schema_names.py`), a JSON column never claims to hold enums, since what it reads back is plain text (`tests/unit/test_json_enum_columns.py`), every value an editor lever accepts is offered by the screen that calls it (`tests/unit/test_editable_fields.py`), every property a material slot shows is served (`tests/api/test_material_slot_fields.py`), and the mechanic, schema, produced-kind and rule registry checks.
    - A full epoch with a scripted model, and an engine-only epoch.
    - Every test file that imports a changed function, class or constant, or a changed test helper. `scripts/covering_tests.py` lists them from the staged diff.
  - ruff, mypy (with deprecated calls as errors) and import layers for backend changes.
  - tsc, eslint and prettier for frontend changes (rule 5), and the vitest files that cover the change: every test in the folder of a changed file and every test that imports it. `scripts/covering_frontend_tests.py` lists them from the staged diff.
- **Never bypass a check.** No `--no-verify`, no allowlists, and no downgrading an error to a warning. A failing check means the work is not done: fix what it found, in the same task.
