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
  - `scripts/check_wiring.py`: enum types never used, tables never read, player actions missing from the catalog, catalog actions with no frontend caller (rule 3).
  - ruff, mypy and import layers for backend changes.
  - tsc, eslint and prettier for frontend changes (rule 5).
- **Never bypass a check.** No `--no-verify`, no allowlists, and no downgrading an error to a warning. A failing check means the work is not done: fix what it found, in the same task.
