IMPLEMENTATION BRIEF (read fully before writing code)

Project: /Users/egedogan_dursun/Repositories/Personal/aerona — the clean, production-grade rewrite of the legacy Turkish game at /Users/egedogan_dursun/aerona (READ ONLY; never modify it, read it only to resolve ambiguities in the spec).
Read first: docs/architecture.md, docs/decisions.md (decisions override the legacy behaviour and the spec where they conflict), and the spec files named in your task under docs/spec/. docs/spec/coverage.md may exist (mechanic traceability matrix); if it does, every row in your scope must be implemented.

ABSOLUTE CODE RULES (the user is very strict; violations are failures):
1. ZERO comments of any kind in any file you write: no #, //, /* */, JSX {/* */}, HTML <!-- -->, Jinja {# #}, no docstrings, no bare string statements. Names and structure carry meaning.
2. ZERO Turkish anywhere in code: identifiers, strings, file names, test data. English only.
3. Every LLM prompt text lives only in backend/src/aerona/prompts/ (templates + catalog). No prompt prose anywhere else.
4. No magic gameplay numbers: every balance number is read from the typed rules snapshot (backend/src/aerona/rules/registry/*, accessed as rules.<namespace>.<key>). Merge semantically duplicate keys and move keys between namespaces if your subsystem owns them; add new rules with rule(default, min, max, RuleGroup.X, "English label") when the spec or a decision requires a tunable. Non-gameplay constants go into backend/src/aerona/constants/*.py.
5. Clean architecture, proper folders/subfolders, small focused modules, typed code (mypy --strict clean, ruff clean), async where I/O is involved. Respect the import-linter layers in backend/pyproject.toml.
6. Every LLM call uses only the single Haiku model constant; never Sonnet/Opus.
7. Frontend: build only on the shadcn-admin/shadcn-ui foundation in frontend/src/components/ui; never restyle controls with height/padding/font-size/arbitrary-value classes in feature code; use the typography components; spacing via gap.
8. Do not edit files outside your assigned scope except where your task explicitly allows. If you need a shared change (a new dependency, a shared enum, a layer change), make the smallest change and list it in your final report.

VERIFY before reporting (all must pass for your scope):
- cd backend && uv run python ../scripts/check_source_rules.py → 0 violations (system python3 is 3.9 and cannot parse the code)
- cd backend && uv run ruff check src tests ../scripts && uv run ruff format src tests ../scripts && uv run mypy src && uv run lint-imports && uv run pytest -q
- frontend scope: cd frontend && npm run build && npx eslint .
Write tests for everything you build (deterministic, no network, no real LLM).

FINAL REPORT: files/modules created, what is fully implemented, anything not implemented with the reason, shared changes made, open questions. Keep it concise.
