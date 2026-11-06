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
