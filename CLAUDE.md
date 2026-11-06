# Standing rules from the user (always apply, every session)

1. **No unneeded tests.** Never run the full backend suite, broad `-k` sweeps, Playwright or e2e on your own initiative. Per change: ruff, mypy, lint-imports, `scripts/check_source_rules.py`, `npx tsc -b`, eslint, plus at most the few test files that directly cover the touched code. If those pass, commit, push and deploy. Run broad suites only when the user explicitly asks.

2. **Prompts never constrain the lore.** Any text the LLM sees (prompt templates, schema descriptions, tool texts, `prompts/data`, `catalog` lines, chronicle strings, frontend placeholders and suggestion lists) must let the world become any kind of lore:
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
   - The only tables exempt are the bookkeeping ones listed in `BOOKKEEPING_TABLES` in `scripts/check_wiring.py` (fixups, cursors, counters, notifications, the player's action ledger, score and achievements, and the per-epoch goods-flow log). Only the user may add to that list.

## Enforcement

These rules are enforced mechanically, and they bind Claude as much as anyone.

- **Claude Code hook** (`.claude/settings.json` → `.claude/hooks/guard_tests.py`). It blocks:
  - pytest runs that don't name individual test files, and pytest with `-n`
  - vitest runs on a directory
  - any run of more than 6 test files at once
  - every npm test script, Playwright, and the Makefile test and check targets

  Only the user may lift it, by creating `.claude/allow-broad-tests`; Claude never creates that file.
- **Git pre-commit** (`.githooks/pre-commit`, enabled with `git config core.hooksPath .githooks`). It runs on every commit:
  - `scripts/check_source_rules.py`: no comments or docstrings (rule 4).
  - `scripts/check_prompt_bias.py`: gendered defaults, conflict quotas, forced strangeness, steering examples and hardcoded image media in LLM-facing and UI text (rule 2).
  - `scripts/check_wiring.py`: enum types never used, tables never read, player actions missing from the catalog, catalog actions with no frontend caller (rule 3). It also flags any table an engine phase writes that has no compliance-catalogue row with registered god levers (rule 6).
  - `scripts/check_control.py` (rule 6). It finds automatically, by reading the code, every table whose rows the engine changes over time. Each must be creatable, editable and deletable by a god lever that the frontend reaches, and whose code (followed through its calls) really touches that table. Several cases are covered without per-table levers:
    - Profile tables (one row per thing) through `profile:set`.
    - Every node-linked table through the generic `record_row:create`, `record_row:edit` and `record_row:delete` levers and the "Every record" section in each drawer.
    - Append-only histories and tables the engine wipes and rebuilds wholesale are outputs, not authored state.
  - `backend/tests/engine/core/test_god_control.py` whenever engine or db code changes (rule 6). It runs every engine step, found automatically, twice. First with every node held: nothing tied to a node may be created, changed or deleted. Then forced on one node: it must run cleanly. A new step that acts on a held node fails the commit. Skip held nodes with `held()` or `unheld()` from `aerona.db.write_guard` where the step chooses whom to act on. Field updates on held rows are already reverted for every node-linked table.
  - ruff, mypy and import layers for backend changes.
  - tsc, eslint and prettier for frontend changes (rule 5).
- **Never bypass a check.** No `--no-verify`, no allowlists, and no downgrading an error to a warning. A failing check means the work is not done: fix what it found, in the same task.
