INTEGRATION NOTES (collected from workstream reports)

E2 war/diplomacy:
- Remove engine/phases/society_support/ports.py fallback_declare_war; route everything through engine/services/war.py (decision 35).
- Cosmic court hook in phases/diplomacy.py duplicates BEY-027 in phases/afterlife.py -> merge into afterlife.
- Single foreign-god resolver lives in engine/cosmos/foreign_gods.py::resolve_god_war; conflict.py delegates. Consider moving resolver into engine/services/conflict.py.
- Engine war/army/battle names use community name; should use language-derived names (language/ naming).
- Tribute bonds without typed rows are adopted each epoch.
- E2 phase order: expire_truces(0.2), divine grudges(1), diplomacy(2.1), war_upkeep, tribute, campaigns, prisoners (2.2), death engine (2.10), factions (12 after births), espionage (12 after belief/memory), gods_fate (T7).

Prompts:
- Tool-specific success/rejection texts must move into prompts/ (tools layer agent).
- Network repair node keys s12/e12; parser must tolerate bare numbers.
- FatherStance enum lives in prompts/contexts/son_turn.py; consider domain/.
- Budget helpers in prompts/budget.py; agents import them.

Frontend:
- Generate enums via OpenAPI (event kinds, job statuses, rarities) once API phase is done; run npm run typegen.
- Duplicate component owners in coverage: GodPanel (creator/pantheon), PathFinder (entity/graph), HandOfGodPanel (entity/son).

Image worker:
- Image queue service maps rules.image_gen width/height/steps/startup/image/idle timeouts onto ImageJobRequest.

General:
- Regenerate single migration after all engine workstreams.
- Several agents ran ruff --fix/format across others' files; re-run full checks at merge.

E5 gods:
- Core logic in engine/gods/*; services/gods/* thin wrappers. Manual service fns record ActionRecordRow themselves (player layer must NOT double-record).
- Phase order: tick 2c resource_mechanics -> cosmic_economy; tick 2f' (after foreign gods, before civilization) death_engine; transition after rebels theft/doom items/essence income/epoch increment: creator_mood, god_power, reputation, goals, gods_fate. Transition phases treat ctx.epoch as NEW epoch.
- Epoch transition must consume engine.gods.worship.cult_effect() for essence income + doomsday line (MOOD-005).
- Consolidate helpers: mortality.mortal_dies -> engine/lifecycle/mortal_death; interventions.py (INT owner); essence.py (POW-001/002, services/world.py); stats.add_prosperity (shared prosperity fn, decision 53); world_view.near -> spatial model; worship_creator -> services/faith.py; notifications written directly to NotificationRow -> use notifications service.
- NOT implemented: Deify mortal (ACT row) needs shared son stat/power roller (summoner). Assign to player-actions workstream.
- hungry_food default skipped for communities without society row (fine).

E3 society:
- Phase order: P0 language_and_faith (0.3); P4 trade_income (4.1), barter_and_rivalry (4.5 after prosperity reversion); P5 schisms 5.1, hero_births 5.3, knowledge_diffusion 5.4, cultural_exchange 5.5, natural_disasters 5.6, uprisings 5.9, currency 5.13, godlessness 5.16, love_and_rivalry 5.19; P6 society_economy, heroes, ..., religion_spread, ..., wonders, dark_ages (before ruins); transition law_fertility (T1), climate_transition (T3) before population growth.
- Consolidate: society_support/records.create_record vs E2 war_records.create_engine_record; faith.change_religion vs war_records.convert; uprising_target vs DEEP-054. services/faith.py and services/player/interventions.py must call down to engine-level versions.
- Resource creation tools must call set_resource_commodity (else no ore).
- CORE-044 faith computation must count reverences at religion.reverence_weight_pct.
- CosmosRow has no climate column (climate_of falls back to primary world) — fine.

E1 core:
- engine/pipeline.py has TICK_ORDER/TRANSITION_ORDER with SUB_ENGINE_STAGE empty + bracket slots for other workstreams (full order in E1 report; mirrors spec 04 §1). Integrator wires E2/E3/E4/E5 PHASES into these slots; post-transition steps (creator mood, god power, reputation, goals, certain facts) into TOLERANT_TRANSITION_STEPS.
- Duplicates: engine/services/war_strength.py vs primitives/strength.py; engine/gods/worship vs services/faith worship_creator/worshipper_faith; primitives/first_bonds vs language/lexicon; primitives/naming vs language/naming; primitives/physics vs COS-020..022 (E4); primitives/knowledge (law resolver) vs INT owner; primitives/society class shares vs E3 society_economy; death_options vs DTH-001/002 (E5 engine/gods/mortality).
- Not done: protect settlement from ruin (needs typed field) -> add flag/column and manual fn.
- Manifestation kind chosen by English keywords: replace with typed legend category (decision 40).
- Phase toggles storage: add rules namespace "engine_phases" with 0/1 per phase? -> decide: a phase_toggles table or rules switches. Use rules (bool ints) so the player controls them in World Rules.
- Leak breakdown in epoch stats belongs to horror (E4).

E4 cosmos:
- Phase order: travel 2.3, exploration 2.4, [resource_mechanics, cosmic_economy 2.5-2.6], horror 2.7, creatures 2.8, pantheon 2.9, death 2.10, civilization 2.11, sky 2.12, beyond 2.13; creature_migration 5.2, creature_rebellion 5.15, speciation 5.17; transition T5 choose_epoch_stars; before transition birth_local_gods; startup pair_mirrors, connect_all_worlds, recover_intuitions, align_moons.
- Ship-building tools must call vessels.set_vessel_kind.
- Merge duplicates: kit/manual vs primitives/manual; worlds.world_physics vs primitives/physics (latter lacks new world types); kit/disasters vs INT disaster code (engine/gods/interventions, society disasters.apply_disaster); duels.son_duel vs tools challenge tool.
- Not done: CRE-004 manual "order a species to feed". Creature migration needs persisted map geometry (store generated map per world; region adjacency from stored map) -> map persistence service needed.

P1 player:
- Epoch runner must call services/player/assignments.auto_distribute(scope, ctx) each epoch (only when distribution automatic).
- Mortal-agent picker must read EntityFlag.AGENT_SELECTED (ACT-142).
- Wire CreativePorts (SonSummoner, RevelationAuthor, WorldMaker, PeopleAwakener, ContentWriter) in services/player/ports.py to L2 agents.
- Not implemented: ACT-173 (wake rewrite of foreign god "asleep" text) -> on wake, enqueue an LLM refresh of the foreign god's description via content job; ACT-174 edit foreign god depth text fields -> add an edit action.
- S1 ledger_undo.UndoRun._refresh_touched: guard primary_key_from_instance against expired instances (MissingGreenlet).
- coverage.md: ACT-155..162 now in services/player/world_edits.py, ACT-172..174 in foreign_gods.py.
- services/player/catalog.py ACTIONS + describe/run_ledgered/run_job -> API generates routes from it.

L2 agents/epoch (done):
- App lifespan wiring still TODO (API/app workstream): LlmClient with TelemetrySink; attach_toolkits(runtime); EpochHooks closures (backup, complete_missing, network_rule_repair, prune, after_epoch, image_autogen, spawn, distribute -> services/player/assignments.auto_distribute); CreativePorts(summoner=p.summoner, revelations=p.revelations, worlds=p.worlds, awakener=p.awakener, writer=p.writer) from agents/creative.agent_creative_ports(runtime).
- Rejection rollback is partial (hides chronicle rows, refunds, marks ledger undone) -> should use generic ledger undo (S1 UndoRun) for the creation's ledger entry.
- Rule-based loose-end network repair only fixes missing location bonds -> complete per spec 02 network repair rules (S1 services/integrity owns).
- Genesis does not generate the world map -> call map persistence (I1) at genesis.
- World-creation request new_star_type ignored -> honour it.
- TickEnvironment lacks phase year windows -> add window to TickEnvironment/TickContext so engine chronicle years fall into the phase window.
- Minimal internal versions of motifs/threads/canon_facts in agents/fate -> consolidate with S1's services (move core to a lower layer if agents need them).

S1 services (done):
- services/application.py builds everything; container.application; exposes epoch_end_maintenance() -> wire into EpochHooks.after_epoch.
- Engine ctx.chronicle bypasses notifications: call ChronicleWriter.notify_unclassified(since_id) after each tick (EpochHooks / engine tick wrapper).
- API must apply DiscoveryService.ensure_writable() as 423 guard on all writes.
- Telemetry: wrap agents' TelemetrySink with MetricsService.sink() for pruning.
- ImageQueue.start_bulk(auto=True) for epoch-end image autogen (EpochHooks.image_autogen).
- Remove text-only motif rules in rules/registry/language.py (root letters, suffix steps).
- Open: temple destruction should write typed "destroyed" bonds in pantheon engine; typed death cause (INV-037); Fate output flag shared_theme_only for companion bonds.
- RowJournal capture could be consolidated into services/ledger.py.

L1 tools (done):
- Agents must implement tools/framework/ports.py ReadViews (world_summary, son_memory, mortal_view) from agents/context; ChildBirth, WorldBirth; verify agents/tool_ports.py covers all three (L2 says it implements ToolPorts). Agents must await settle_long_jobs() before resolve_pending_job. Toolkits returns tools' ToolCatalogue/DoneAction types: ensure agents adapt.
- Consolidate: level-up tools/son/support.grant vs services/sons.py (move to engine level); miracle effect tools/son/intervention.apply_miracle vs services/player/interventions._miracle -> engine; subtype normalisation tools/framework/subtypes.py vs services/narrative; duplicate tunables civilization.loan_repay_relation vs mortal_tools.debt_repay_relation; engine son_duel should cap essence + level-up itself (tool currently corrects); resolve_god_war deducts its own cost (check double charging).
- Partial: entity detail lacks society lines + canon facts; transform rename doesn't rewrite old name in texts (rename-everywhere service exists in S1 names?); mortal explore_land new region lacks map position (expose engine positioning helper); engine helpers with direct SQL updates/deletes (remove_flag) not captured by ledger -> ledger capture must hook bulk statements (P1 RowJournal handles bulk: unify).

I1 engine integration (done) — remaining cross-layer items:
- epoch/phases/transition.py + engine_tick.py: run POST_TRANSITION_ORDER via after_transition(environment) tolerantly (creator mood, god power, reputation, goals never run otherwise!); apply enabled_phases(..., rules) switches; optionally use local_gods phase (already births local gods itself).
- agents/mortal.py picker reads string tag AGENT_SELECTED_TAG but player writes EntityFlag.AGENT_SELECTED -> switch picker to the flag.
- Player layer needs service + API wrappers for: protect_from_ruin, order_feeding, spare_soul, regenerate_world_map, set_doom_clock (and any other engine manual fns without a player action — audit all engine manual functions vs services/player/catalog.py).
- LLM-created legends must set legend_category; ship-building tools call vessels.set_vessel_kind; resource-creation tools call set_resource_commodity.
- agents/genesis.py should store map at genesis (startup + world_maps phase cover it; fine).

FINAL PASS (after X1):
- ACT-173: player action waking a foreign god must also queue the LLM description refresh (refresh_awakened_god via job), like the engine path.
- FatherStance -> domain/enums.
- coverage.md status update for X1 rows; audit_api_usage --strict must be 0 gaps after UI.

UI FOLLOW-UPS (from F1/F5):
Backend:
- World package import MERGE mode missing (legacy had replace/merge) -> implement merge import (decision 9 lists MERGE).
- Council with blank agenda: legacy let Fate pick topic -> accept empty topic, Fate/agent picks (update test).
- Genesis first sons: let the player choose the first sons' rarities/count (within rules) instead of fixed Common/Rare/Legendary.
- Expose missing data: star of the epoch; great expedition countdown + declarer; dead-son devotion, earliest return, loyal communities; son "half turn" (existence band action loss); per-entity notes API.
Frontend:
- Atlas route search params (type filter) so links can deep-link; Cosmos route accepts ?world= selection; header world filter (global) or consistent world pickers.
- Bookmarks: single store/format (localStorage aerona.bookmarks "son:<id>" vs server favourites) -> unify on server favourites if API exists.
- Command palette: actions with fixed-field routes (creator content, route sever/restore/reveal) must work from the generic form.
- e2e: shared mock rules must include cost keys; mock all endpoints (/api/entities, /api/discovery-summary, /api/image-gen); delete debug specs zz-*.spec; stale tsbuildinfo.
- Optional: text-size accessibility setting.

F4 map/graph partials:
- 3D link colours not faded toward background (UI-074); descend-from-cosmos transition (UI-450); entity markers type icon (UI-454); keyboard nav of canvas nodes (UI-067); default focus from Atlas selection (UI-059); global world selector (UI-435); graph time slider max = current epoch (UI-062).
- Link groups classified client-side: move bond-group classification to server bond catalog metadata (catalog/bonds) and expose it.
- NetworkHealthPanel embed under Settings > Network repair (F5 area).
- GET /api/map-notes list should appear in ledger "My notes" (UI-125).

ROUND 2 LEFTOVERS (frontend functional agent):
- UI-142 unify son/climate/chronicle jump links on entity hero.
- UI-137 collapse-on-scroll top bar.
- UI-054 custom SVG chart primitive; UI-160 shared theme-colour hook; UI-175 #id token links in text; UI-191 drag-and-drop package picker; UI-192 shared multi-select; UI-195 global world filter.
- Verify backend sends feed stream fields: order, order_total, model, rarity, done, wait_s (agent stream/turn/retry events).
- foreign-god/ForeignGodPowerPanel.tsx unused PERCENT/rule; e2e/capture.ts lint.
- Full e2e + full vitest re-run after all agents finish; screenshots review of all screens dark+light.
- New components (EpochStarChip, ExpeditionCard, HalfTurnChip, MergeSummaryView, RuleInfo, CopyButton, Sigil, DomainGlyph) must appear on /design.
- e2e mocks needed: /api/sons/{id}/opportunities, /api/sons/{id}/tools, /api/opportunities/creator, /api/entities/{id}/dreams, wars routes.
- tsc: epoch/ShellStatus.tsx ChangeFeed casing clash; realtime/invalidation.ts lacks agent.stream kinds; son/SonRebellion.tsx, son/SonTools.tsx action paths.
- UI tests still missing (gods/run-world agent): UI-041; creator UI-096, 241, 247..260; council UI-113; pantheon UI-094, 098, 101, 102, 104..107, 109; foreign god UI-261, 262, 268, 269, 271..273, 390, 393; son UI-276..278, 281, 283, 285..288, 291..297, 299..301.
- tsc: components/domain/domain.test.tsx:85 Element|null vs Locator.
- e2e failing: cosmos consistency dark/light, cosmos.spec forget world + travel resource chip, entity.spec wars and relations (desktop+mobile).
- UI tests still missing (lore/cosmos/map agent): cosmos canvas/3D UI-404, 407..411, 413, 415..423, 425, 426, 428..430 (use Playwright with SwiftShader WebGL + screenshot/structural assertions); map canvas UI-431, 433..436, 438, 441, 442, 444, 446..451, 454, 456..458, 460, 461 (time slider, playback, marker drag); graph UI-061, 063, 065..068, 070..072, 074..078; entity UI-305, 314, 330, 345, 346, 352, 353; cosmos forms UI-133, 134, 354, 357, 358, 361..363, 365..371, 375..377, 384, 394, 397, 399..402; images UI-205, 206, 212; UI-056 per-son cards; UI-204 second part; UI-373 seal/re-raise.
- vitest: serverLines.test.tsx imports @testing-library/react (not installed) -> rewrite with vitest-browser-react; 13 failing files incl ledger.test.tsx (check after all agents).
- eslint: EntityView.tsx no-duplicate-imports.
- sonner Toaster pointerEvents auto fixed (shared).
- Gods previews agent left: ACT-130 distribution candidate score read endpoint + UI (gods backend agent may also do it — check); ForeignGodPowerPanel "deathless" caption computed client-side -> server field; backend test failures test_exchange, test_flow, test_genesis, test_prompt_context (fate_geography_chars rule missing) -> diagnose at integration; migration must be regenerated after all schema changes.

COSMOS ROUND-2 LEFTOVERS:
- Tests needed: COS-011, BEY-003, BEY-009, FGD-008, LANG-024, INT-005, MAP-031 (fixed, untested); INT-008, 016, 017, 018, BEY-005, 010, 011, TRV-018, PAN-009, 010, 013, 017, 018, 019.
- TRV-018, EXP-020, PAN-003, BEY-029: confirm engine:run_phase covers travel/exploration/pantheon/beyond phases by name + test.
- BEY-004 soul descent: decide per decision 50 and document.
- UI needed for new actions/endpoints: language:edit (writing_system, sample_names, alphabet, signature), language:signature, language:epoch_words, cosmic:extinguish_star, son:outer_bargain (force/forbid/allow), intuition:discard(_all), world:edit terrain_seed/sea_pct/mountains_pct/moisture_pct, record:edit is_water, region creation water, POST /languages/{id}/sample-names, GET /worlds/{id}/geography, GET /worlds/{id}/laws, language tree signature/alphabet; MAP-020 fog toggle.
- Pytest blocked: constants.maintenance PACKAGE_CHUNK_BYTES missing (services/exchange.py), rules.registry.deep_relations missing; ScriptedToolkit.read_only_tools in test_son_turn.
- Migration regen: LanguageProfileRow signature/alphabet, WorldMapRow signature, SonRow outer_bargain_forbidden (+ others).
- Engine controls agent: verify DEEP-014, DEEP-171, DATA-027 against /api/maintenance*; mark MORT-021/023 done if previews cover them; confirm mobile engine row layout screenshot; `fate_geography_chars` missing in ContextRules breaks tests/agents/test_context.py.

PLATFORM B LEFTOVERS:
- Not done: CTX-032 (chronicle world filter), CTX-034 (lexicon sampling test); CAT-023/035/056, SVC-006/024/026/084/136, CORE-013/043/050, INV-016, NEW-004/008, LLM-036, LLM-129 (plus whatever slice A leaves of INV-005/006/010, NEW-010/011, LLM-100, EPOCH-002/037/041..046, SVC-116/117, Fate controls).
- Test failures to check: test_son_turn::test_partial_turn_with_world_changes_still_finishes; prompt sample renders son_turn_continuation / mortal_turn_continuation (long_jobs undefined — gods backend agent added long_jobs to continuation context; samples need the field).
- PLR0917 services/player/fate_controls.py:60.
- UI needed: prompt-context viewer (blocks, son prompt preview, catalogue + template + schema), tired motifs list + overrides, maintenance page (tasks list/run/progress, missing completion, backup verify, son powers / cosmos prompts / chronicles LLM jobs).
- LIVE STREAM field mismatch: frontend reads order, order_total, model, rarity, done, wait_s; backend emits son.turn_queued {no,total,son_id,name}, son.turn_started {son_id,son_name,resumed}, son.turn_finished {...,status}, agent.retry {actor,kind,attempt,total,reason}. Legacy UI showed model + rarity + wait seconds on turn/retry lines -> ADD to backend: turn events carry model + rarity; retry carries wait_s and kept steps; then align frontend field names to the real payload (no/total). Run tests/api/test_entity_jobs.py.

PLATFORM A LEFTOVERS:
- SVC-200 on-demand prune: maintenance task "prune" exists (platform B) — verify and mark.
- LLM-020 `partial` call status missing in LLM metrics.
- EPOCH-016, EPOCH-041..046 tests; image autogen full bulk run test; snapshot-now action.
- tests/engine/core/test_lifecycle.py::test_laws_freeze_or_haunt_the_old fails (age 70 vs 65).
- UI needed: Fate controls panel (GET /api/fate/controls; fate:retry, fate:rejudge_debt, fate:rejudge_limbo, voices:retry, births:retry jobs; fate:override_verdict, voices:edit_view, voices:delete_view).

W35 cross-cutting layers (spec 16 6.6), filled at the W35 audit of 2026-11-15:

| Layer | What W35 gives | Left to |
|---|---|---|
| Record of what happened | notes with typed keys (economy.order_set, economy.transition_begun, honours.nicknamed, honours.disbanded, veterans.granted, honours.reconstituted); unit honours, item history rows for honours borne on standards, order transitions with stages | typed incident records, W49 F58.1–F58.4 |
| What changed | actor tool calls and god levers through the ledger; tool writes to held values are refused and rolled back | engine-side change capture, W49 F58.5 |
| When | since, hidden, issued, formed, disbanded, started and ended epochs on every table | in-world calendar moment, W49 F58.6 |
| Where | hoard place, market, from and to markets of bills, village of putting-out, origin and sight of tourists, unit raised from | origin and destination per happening, W49 F58.6 |
| Why | couplings with rule keys for every number; resistance and transferred on transitions | stored causes, W49 F58.7–F58.8 |
| Who knows | hoards stay hidden until found by diggers | witnesses and rumours, W49 F58.9 |
| How it is told | English notes and chronicle lines from fields | re-renderable tiers, W49 F58.10 |
| What it was | none | W49 F58.11 |
| What is kept | no table is folded or cut; transitions, honours and grants are kept after they end | |
| Names | unit names and earned nicknames from the tongue of the land a unit was raised from | |
| Look | none added | |
| Model-facing wording | the four tool texts, results and context lines read in full against rule 2 | |
| Control | 62 levers registered and proven; tools honour locks and holds through the runtime | record reverts, W49 49.5 |
| Reach | MeansSection, OrdersSection and HonoursSection in ThingSections | |
| Books | generic typed sections and records appendix render every W35 table with named references | |
| Search | text search only | W49 49.5 |
| Integrity and legacy | orders_links repair closes open transitions of vanished realms, idle putting-out, orphaned named units, dead changers, lost hoards and dead chain holders; migration c3567396253d backfills | every table, 47.13 |
| Speed | engine tick measured at 144–171 s on the real-data copy, against a 20 s target | W49 49.8 |
