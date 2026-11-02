INDEPENDENT AUDIT BRIEF (READ-ONLY on code)

Repo: /Users/egedogan_dursun/Repositories/Personal/aerona (rewrite). Legacy game: /Users/egedogan_dursun/aerona (Turkish Node code, READ ONLY). The traceability matrix docs/spec/coverage.md lists every legacy mechanic as a row with an ID, mechanic, legacy source, spec section, planned new module, auto trigger, manual control, UI surface. Its Status/Test columns are NOT reliable (agents did not update them). Your job: independently verify, for your assigned ID prefixes, whether each row is really implemented in the new code, and how faithfully.

For EVERY row of your prefixes (parse the matrix rows with the given prefixes; tool rows use IDs like TOOL-S-017 / TOOL-M-005):
1. Find the implementing code (grep the new repo; the planned module path may have moved — engine consolidation merged many modules). Record file:function.
2. Verdict: IMPLEMENTED (behaviour present, wired into the live path, with a test that exercises it), PARTIAL (exists but a piece is missing: not wired into the epoch/engine order, no manual control where the row demands one, no UI surface where the row demands one, no test, or simplified logic), MISSING (not found), or NOT-PORTED-OK (row explicitly not ported per decisions 14/44 in docs/decisions.md).
3. For rows with formulas/probabilities/order-of-operations, compare the new logic with the legacy function (and spec section) and flag deviations that are not covered by docs/decisions.md.
4. Wiring check: a phase/service/tool/route that exists but is never called from the live path (pipeline TICK_ORDER/TRANSITION_ORDER, epoch orchestrator, tool registry, router, frontend) counts as PARTIAL.
5. "Manual control" and "UI surface" columns: verify a player action/endpoint exists and a frontend caller exists (grep frontend/src for the route path or action id).

Output (write ONLY these files, never edit code, tests, or coverage.md):
- docs/audit/<name>.md : summary counts per prefix and verdict; then a table of every non-IMPLEMENTED row: ID | mechanic | verdict | what exactly is missing/wrong | evidence (file:line) | suggested fix scope (S/M/L).
- docs/audit/<name>.json : array of {id, verdict, evidence, test, note} for ALL rows.
Be rigorous and evidence-based: do not mark IMPLEMENTED without having opened the code. Do not spawn subagents. Absolute rules for anything you write: no code comments anywhere, English only. Final reply: counts per verdict and the 10 most serious gaps.
