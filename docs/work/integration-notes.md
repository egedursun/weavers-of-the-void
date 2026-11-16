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

W36 cross-cutting layers (spec 16 6.6), filled at the W36 audit of 2026-11-15:

| Layer | What W36 gives | Left to |
|---|---|---|
| Record of what happened | world_views.short notes when a town runs short of what its world binds it to; tallies of seeded, met, short, upkept and unpaid in every epoch's counts | typed incident records, W49 F58.1–F58.4 |
| What changed | god levers and the son tool through the ledger; the son tool is refused on a held world and on a held value | engine-side change capture, W49 F58.5 |
| When | updated_epoch on every world nature | in-world calendar moment, W49 F58.6 |
| Where | one nature per world; towns, regions, armies and resources read the nature of their world | |
| Why | couplings with rule keys for every number; the kind of world is the stated source of every default | stored causes, W49 F58.7–F58.8 |
| Who knows | the nature of the world is in mortal and son context | witnesses and rumours, W49 F58.9 |
| How it is told | plain lines from fields | re-renderable tiers, W49 F58.10 |
| What it was | none | W49 F58.11 |
| What is kept | one row per world, never folded | |
| Names | none added | |
| Look | none added; image style stays at render time | |
| Model-facing wording | the son tool text, its results and the context lines read in full against rule 2: they name the fields, not images | |
| Control | world_view:edit (with hold and release), world_view:reset, world_views:run, proven in the lever harness; the son tool proven in the tool harness | record reverts, W49 49.5 |
| Reach | WorldViewSection in ThingSections for every kind of thing; the Creator and stars stand on no world and the section says so with its controls disabled | |
| Books | world entries render the world nature as a typed section in the book and the Codex | |
| Search | text search only | W49 49.5 |
| Integrity and legacy | startup seeding of every missing world nature; migration 39ded63f7c3f; the god's held values survive a seeding | every table, 47.13 |
| Speed | world natures are read through one memo per session | W49 49.8 |

W36 audit, lived world (2026-11-15): the population of the real-data world fell from 2.8 million at epoch 49 to 0.3 million at epoch 57 and kept shrinking at the 25% cap on every non-dream world. The cause was the order of energy draws: resource_economy ran before society_economy and spent a town's whole pool of muscle on mines, quarries and logging, so harvest_goods found no energy and the fields of whole towns yielded nothing. Farmers now work their own fields first (worked_by_hand) and the shared pool holds only the muscle of the other workers; check_food_energy keeps food from being drawn from the shared pool alone. Two deeper causes were found by the same audit: a people's food need was the sum of the consumption of every nourishing commodity in the catalogue, so every wave that added a food (meat, milk, cheese, fruit, tubers, eggs) raised the need of every person, and grain and the bread made from it were both required; the need is now one rule per thousand people (consumption.nourishment_per_1000), and the food aggregate follows it, guarded by test_food_need. And every church holding a land took its tithe from the whole harvest, up to eleven churches on one land; a land's tithe is now shared among the churches that hold it. Likewise a town gave each place spirit it kept the whole of its offerings (one town kept seventeen); its offerings are now shared among them.

W37 cross-cutting layers (spec 16 6.6), filled at the W37 audit of 2026-11-15:

| Layer | What W37 gives | Left to |
|---|---|---|
| Record of what happened | the son tool writes a chronicle line with its reason; tallies of seeded and followed biologies in every epoch's counts | typed incident records, W49 F58.1–F58.4 |
| What changed | god levers and the son tool through the ledger; the son tool is refused on a held people or species and on a body whose variants the god holds | engine-side change capture, W49 F58.5 |
| When | updated_epoch on every biology | in-world calendar moment, W49 F58.6 |
| Where | one biology per people or species; towns, mortals, armies (through the people that raised them) and beasts (through their species) read the biology of their kind | |
| Why | couplings with rule keys for the bias share and the son's cost; the variants are the stated source of every effect a god has not held | stored causes, W49 F58.7–F58.8 |
| Who knows | the nature of the body is in mortal context; the bodies of the kinds of life of the son's world are in son context | witnesses and rumours, W49 F58.9 |
| How it is told | plain lines from fields | re-renderable tiers, W49 F58.10 |
| What it was | none: a change of variants is told by the son's chronicle line or the god's ledger | W49 F58.11 |
| What is kept | one row per people or species, never folded | |
| Names | none added | |
| Look | none added; image style stays at render time | |
| Model-facing wording | the son tool text, its results and the context lines read in full against rule 2: they name the effects, not images, and the tool text does not list the variants | |
| Control | biology:edit (every effect, with hold and release, and the release of the variants to the sons), biology_variant:add, biology_variant:remove, biology:reset, biology_variants:run, proven in the lever harness; the son tool proven in the tool harness | record reverts, W49 49.5 |
| Reach | BiologySection in ThingSections for every kind of thing; gods, worlds, stars and things of no living kind carry no biology and the section says so with its controls disabled and their reason | |
| Books | the biology of a people or species renders as a typed section of its entry, variants and effects labelled, in the book and the Codex | |
| Search | text search only | W49 49.5 |
| Integrity and legacy | startup seeding of every missing biology, dropping of unknown variants and of rows whose holder is no longer a people or species, and the free values follow the variants; migration 4490378d89b2 also widens the bias enum | every table, 47.13 |
| Speed | biologies are read through one memo per session; a town's people through the people_of memo | W49 49.8 |

W37 audit, engine: every effect of the view has a reader. Food need is read by eating and by the hunger of wild hunters; births by population growth and wild growth; deaths by population growth and wild starvation; sickness by population disease, wild disease and plagues; fear by the battle and, after the audit, by every other loss of morale (supply, wages, ambushes, standards taken, dread of a cruel foe, night dishonour, mutiny, news from home, a culminated offensive and sieges), which check_morale_losses now enforces; fire and storm harm by great fires and storms; breathing and drinking by a world's binding need; ageing by mortal ageing. The audit also found that an army read no biology at all, since the people of an army could not be found; an army now reads the people of its owner. The audit found as well that the harm of single bodies read only the body plan of each mortal, so a people made incorporeal, construct, undead, gaseous, crystalline or plant-like kept bleeding, healing and taking blades as before; the anatomy a wound and a tending read now follows the variants of the bearer's people (a body without matter lets blades and blows pass, constructs and the undead do not heal or take infection, the crystalline and plant-like bear wounds through crystal and wood), and the section shows these as values of the body. What the view does not carry and other waves build: rite components by biology (W41 with 8.6 reference pass 8) and the remains of the dead by biology (W41 with the carrion pulse).

W37 audit, lived world (2026-11-15): five epochs of the real-data world after W37 and its audit. The population rose from 302,125 at epoch 57 to 391,321 at epoch 62 (the best run after W36 had plateaued at 357,000). Every people of that world is humanoid, so none took a variant; 103 of its 249 species did (44 hive, 23 aerial, 11 incorporeal and mixes of hive, aerial, incorporeal and aquatic), and 548 minds now carry the two new biases. The engine tick stayed at 175 to 179 seconds; the 223 seconds of the first epoch came from a commit gate and a deploy running beside it, which slowed unrelated phases alike.

W38 cross-cutting layers (spec 16 6.6), filled at W38 of 2026-11-15:

| Layer | What W38 gives | Left to |
|---|---|---|
| Record of what happened | lifecycle.*, world_end.*, fossil.* and museum.looted notes from fields; son tools write chronicle lines with their reasons; tallies in every epoch's counts | typed incident records, W49 F58.1–F58.4 |
| What changed | god levers and the son tools through the ledger; every tool is refused on a held thing | engine-side change capture, W49 F58.5 |
| When | since_epoch and idle epochs of every life, the epoch of every world end, laid and found epochs of every bed, founded and acquired epochs of collections, pieces and gardens, the epoch a piece was given back | in-world calendar moment, W49 F58.6 |
| Where | beds by land and world, collections by keeper, gardens by town, the ended world | |
| Why | causes typed on lives (no holders, no texts, no hosts, sealed, revived, rediscovered, rebuilt, released again, returned, an act of a god) and world ends (impact, wrath, a swollen or dead star, the void, oblivion, drifting belief); couplings with rule keys for every number | stored causes, W49 F58.7–F58.8 |
| Who knows | son context names ended and dormant lore, ended worlds and lands with hidden remains; mortal context names the collections, gardens and finds of the mortal's town | witnesses and rumours, W49 F58.9 |
| How it is told | plain lines from fields; fossil readings are typed by what a people values (legend, relic, deep time), not by any image | re-renderable tiers, W49 F58.10 |
| What it was | world ends keep the former and the new kind of world and what they ended; looted pieces keep whom they were taken from and who gave them back | W49 F58.11 |
| What is kept | one row per life, world end, bed, collection, piece and garden, never folded | |
| Names | none added | |
| Look | none added; image style stays at render time | |
| Model-facing wording | the four son tool texts, their results and the context lines read in full against rule 2: no images are named; the fossil readings were first written as images of particular beasts and beings and rewritten as legend, relic and deep time so that every world reads its own | |
| Control | lifecycle:edit (state, cause, idle epochs, with hold and release), lifecycle:reset, lifecycle:destroy, lifecycles:run, world_end:declare, world_end:edit, world_end:remove, fossil_bed:create/edit/delete/reveal, fossils:run, museum:found/edit/delete, museum_piece:add/edit/remove/restitute, museums:run, garden:found/edit/delete/plant/uproot, gardens:run, all proven in the lever harness; wake_lore, lay_bare_fossils, found_museum and lay_out_garden proven in the tool harness | record reverts, W49 49.5 |
| Reach | LifecycleSection, WorldEndSection, FossilSection and GroundsSection in ThingSections for every kind of thing; each says why a kind that cannot hold it has nothing, with its controls disabled and their reason | |
| Books | every new table renders as a typed section of its owner in the book and the Codex; the kinds planted in a garden are named | |
| Search | text search only | W49 49.5 |
| Integrity and legacy | startup seeding of every missing life and removal of lives whose holder changed kind; migration 8ad812bbd71a, which also widens the sights of travellers for collections and gardens | every table, 47.13 |
| Speed | lives are read through one memo per session; each phase walks its own rows once | W49 49.8 |

W38 audit (2026-11-15). Engine: a lost rite could still be cast by a mortal, since casting read no life; casting now refuses a lost rite (a dormant one can be taken up from its text). A breach could still be opened for an outer being the Creator had destroyed, and tools counted it as present; opening a breach now refuses a destroyed being at its single door in engine/divine/control.py, son tool availability no longer counts it, and warding it is refused. The fossil query joined two kinds of node on the shared nodes table, which made the database layer build an alias on its own; check_node_joins now fails on any query that joins two kinds of node without an alias, and it found one sibling in the division of worlds among the sons (engine/divine/rulings.py), now aliased. Lived world, five epochs of the real-data world: the population rose from 302,125 to 385,596; 11 diseases were eradicated, 23 theories forgotten and 2 rites lost; 36 fossil beds were laid and 8 found; 15 collections held 47 pieces and 38 gardens were laid out; favours faded to an average weight of 18; the tick stayed at 174 to 177 seconds. Two findings came from that data: every temple treasury stood empty, because a treasury gathered only what its town itself owned, and towns own almost nothing; treasuries now take in the relics kept in their town or owned by those who live there, and museums and cabinets its prized things too. And nearly every find stayed unread, because a find was read only from a value of 30, which few peoples hold in superstition, piety or knowledge; it is now read from 10.

J.11, first step (2026-11-15). A cProfile of one tick of the real-data world (175 seconds, about 554,000 statements) showed the time spent in the database layer, not in game logic: entity placements re-read 1,518 times, realm books re-read 389 times, faithful cults re-derived on every law lookup, opinions and relations recomputed after every unrelated write, and every flush reading attribute history for all rows. Each fix keeps results identical: a live placement map follows every flush, the realm book, faithful cults, opinions and relations are kept until a table they read changes, world maps are computed in one lasting pool of workers and their positions committed as typed effects in a canonical order, and the flush guards read history only for held or locked columns. A first attempt cached opinion inputs for a whole stage; it could let a change within a stage reach opinions only in the next stage, so it was dropped for caches tied to the exact tables read. A validation run of one epoch of the real-data world gave statistics identical to the earlier run in every field, with the tick at 135.5 seconds. A statement budget for a tick of the reference world (docs/work/engine-budget.json, 42,415 statements) now guards against regressions.

J.11, second step (2026-11-15). A profile after the first step showed opinions recomputed about 115,000 times a tick. A cache that forgot a node's opinions on any write it touched barely helped: every change of a relation wiped both communities. Opinions are now kept per pair, with the facts of each node kept beside them. A flushed memory, personal bond, reputation or community relation forgets only its pair; a bond, value, trait, identity, purse or structural node change forgets its nodes; culture values, peoples, languages, deleted nodes, bulk writes and rollbacks forget everything. A test changes every followed table in turn and checks each kept opinion against a fresh reading, and a guard fails if a fresh reading starts to read a table the cache does not follow. In the database layer, a two-part key is found through a keyed map of its siblings instead of a scan, a fresh row's columns are checked as one set comparison, bonds are indexed by node and kind, and the tables a statement reads are kept per statement shape for the lazy autoflush. Church ethics are read once per culture when its ethics drift, and a narrow canon read is cut from a wider kept one. One epoch of the real-data world gave statistics identical to the reference run in every field, with the tick at 128.7 seconds. A count of loaded rows then showed 2.3 million loads a tick for 578,000 distinct rows: each step let go of the rows the last one had kept, so every phase loaded its entities, cohorts and culture values again. Rows now stay kept for the whole run of steps and are let go only after a write from outside; the tick fell to 104.4 seconds with identical statistics, at a peak of about 2.1 GB instead of 1.4 GB.

J.11, third step (2026-11-15). A count of fetched rows showed 7.8 million rows a tick, 2.4 million of them the registered names that every namer loaded to build its own pool. The registered pool is now built once while the name registry stands still and copied to each namer, so names one namer invents stay its own; world alphabets and language parents are kept likewise. Coalition targets and faction profiles are kept until their tables change. Every flush used to walk every memo to find the ones it touched; memos are now indexed by the tables they read. The flush guards skip a row with no standing locks at once when the phase guards nothing. A general cache of repeated statements was tried and dropped: its keys and frozen results cost more than they saved, and the tick grew from 101 to 115 seconds. One epoch of the real-data world gave identical statistics with the tick at 97.5 seconds.

J.11, fourth step (2026-11-15). Writes in a loop kept clearing the sibling maps that answer two-part keys, so lookups such as standings, regards and relations went back to the database for rows that did not exist. Since rows now stay kept for a whole run of steps, a table of at most 40,000 rows is read whole on its first miss; while nothing writes past the session and the table has no pending change, a key missing from the kept rows is missing from the database. A bulk write, a rollback, clearing the session or a write from outside forgets that. The tick fell to 94.8 seconds with identical statistics.

J.11, fifth step (2026-11-15). The realm book was read again on every structural change of any entity, so each birth or move rebuilt it. It now follows only realm entities: a new realm, a deleted entity or a change of a realm's kind or status reads it again, and a new region atlas is swapped into the kept book. Reading only keys for rows already held was tried and dropped: it made the tick slower (160 seconds) and changed the statistics. The tick fell to 92.8 seconds with identical statistics.

W39 (2026-11-15). Prehistory and deep time. The decision for a world born into a live cosmos was to hold every other world: the cosmos epoch does not advance and every record of the past carries the birth epoch. Genesis starts at epoch one and every epoch column has a floor, so earlier virtual epochs were not possible; every round runs at the birth epoch with its own chance domain (prehistory.{world}.{round}). Running the same steps twice at one epoch broke the tables that keep one point per epoch (settlement history, prices, trait history, map snapshots and others), so the points of the world for the birth epoch are cleared before each next round; these tables are found from their keys, so a new one is covered by itself. A run holds every node outside its world through the phase guard, which now takes a set of nodes outside. The kind of past comes from the world's nature (prehistory_kind), so the god can change it. Fallbacks make a forgotten origin for a ship and a twin for a mirror. Deep time runs the cosmos forward with no language model; the sons act by their aims and standing, which the engine already moves each epoch, and a digest of the strongest happenings is kept. Fate and the chronicler receive the digest of a past that just ran, told as the world's past with no images of our own.

W39 audit (2026-11-15). A run on the real-data world found two defects. A round took 77 seconds against a budget of 10, because each set of steps opened a new run and loaded every index again; a whole prehistory now runs in one run of steps, and a round takes about 7 seconds. The hold leaked: a set of outside nodes fixed at the start let nodes made during the run act freely, and about twenty steps chose whom to act on without asking whether they were held, so held worlds gained births, deaths, heirs, ruins, dialects, creoles, loans, armies, ended alliances, doctrines, calendars and lines of their own. The hold is now a set of nodes inside, grown as the world makes new ones, so every other node, old or new, is held; and death, ruin, language death, creoles, trade loans of words, dialects, desolation, debts, mercenaries, battles, alliance ends, urban drift, promotion, doctrines, calendars, language standing, conversion, knowledge diffusion and coined names now skip held nodes, which also closes these gaps for a god's own holds. A test lives a prehistory on a stirred cosmos with every chance certain and fails on any row a held world gains; the real-data run then showed none.

Gate speed (2026-11-15). Two gates ran at once and each took over 20 minutes. The pre-commit hook now takes a lock in the shared git directory, so a second gate waits for the first. The job manager tests, the migrated-epoch test and every API test built their database by running the whole migration chain; they now copy the migrated template, and those tests fell from minutes to seconds. The determinism test now compares two five-epoch runs and the full simulation lives six epochs, which keeps what they prove while shortening the longest tests of a gate that touches the engine.

W40 (2026-11-16). The transformation graph. Every type change of F49 is in one registry (catalog/transformations.py) with its source and target kind. Twenty kinds are watched each epoch by the engine step transformations: each gains progress by its pressure over its rule's epochs, loses it when its conditions lapse, and is performed under an undo ledger once it is full, unless the Creator blocked it or a hold covers its subject. A fall and a corruption are announced first and wait transform.warn_epochs. The Creator can force any watched kind, block or release any kind for a thing, and undo a change within its epoch. The older transformations are recorded where they already happen and honour the block. Six transformations that spec 13 lists as existing were not in the engine: a spirit raised to a local god, a mortal cursed into a beast and back, a theory settled into knowledge, a lost work remembered as a legend, a custom written down as law, and a title made a realm. All six are built in this wave. A cursed mortal keeps its node, history and bonds; only its kind and stats change, and the lifting restores its former stats from the ledger. A fallen son lives in a mortal body: it keeps its memories and worship and has a hidden true name. Its turn uses the mortal tool set, seek_true_name and undertake_heroquest under its own prompt, and it dies as a god if its body dies. Fading cannot kill it, and its existence follows its renown and remaining worship back toward godhood. A corrupted son leaves no corpse, and its worshippers and grudges pass to the outer being it becomes. A star god's death dims its star through a modifier on the derived light, so its worlds cool while the stored physics stay intact. The registry is guarded by a test: every kind has a line, every watched kind an engine, and every other kind a recording site or hook outside the transform package.

W40 audit (2026-11-16). Four epochs of the real-data world ran with the transformation step without an error. Two defects were found. A transformed thing lost its bonds: a node that changed kind kept only the bonds the transformation wrote itself, so a settlement that became a city state forgot its kin, allies and trade. Every active bond whose ends the new kind can hold now carries to the result. The spec says a loyal remnant of a fallen son's worshippers may recognise it in its mortal body, and nothing did; each worshipper now does so by its piety (transform.remnant_pct), and the rest keep worshipping the god they think is gone. Story 29, the fallen god, runs as a test through both of its endings.

W41 (2026-11-16). Couplings, new verbs, brakes and loop delays. A rite has parts (spoken, gestured, inscribed, sung, danced, material, of the mind), drawn from its school when first read and editable by the Creator. A caster whose body or captor denies a part cannot work the rite, and a caster's biology decides which parts it can give at all. A mortal with no body record is never read as maimed: a body is read through function_unhindered, and a test fails on any other reading outside the venom of a wound. Communities that cannot hear, keep silence or hunt in silence come to share signed languages; classes, castes, guilds, courts, crews and cants speak in their own ways, which printing levels. Mass deaths leave carrion: scavengers eat, vermin spread disease, predators gather and the living bury at a cost. Where nothing eats the dead they rot, dry out, freeze, fall to the depths or float, by their world and their land. The dead, place spirits and servitors teach what their origin knew; long-lived beasts keep the memory of their age, teach or sell it and take it with them when they die. Commanders parley, make truces, offer and keep surrender terms, exchange captives and the dead, and fraternise across siege lines; broken terms are an atrocity. Walls, warding rites and a god's hand seal the deep; seals wear and are tested and dug through. Closed seasons, protected waters, catch quotas and gear bans cut catches by their enforcement, wardens curb poaching, and grounds near collapse are closed by custom. A form wears out as everyone takes it up and grows fresh as it grows rare. A realm under elite overproduction makes offices for its aspirants and abolishes them when its treasury cannot pay. Each of the 29 balancing loops of the spec reads its driver through loops.delay_* (engine/loops/delay.py), as it stood that many epochs ago; three brakes the loops named were missing and are now built (war weariness pushing a realm toward a postal service, the upkeep of a redistributing centre, and neighbours' envy of a realm that gathers great people). With every delay at two epochs a run stays inside the balance bands. Every ordered pair of subsystems is coupled, which a test now keeps.
