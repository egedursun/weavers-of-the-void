# W52 expansions coverage matrix

Traceability matrix for `docs/spec/17-w52-expansions.md` (spec 0.2). Generated and checked by `scripts/spec_coverage.py`.
Every numbered item of the spec has one row.
A row is `done` only when every work column is filled (or `n/a` where it does not apply) and its test passes.
`deferred-approved` requires the user's explicit approval and a reason in the Test column.
Gap rows (kind `gap`) are done when every section they point to is done.
Run `python scripts/spec_coverage.py write` after editing the spec, and `python scripts/spec_coverage.py check` to verify.

| ID | Kind | Title | Spec | Module | Trigger | Lever | UI | LLM | Templates | Backfill | Test | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S0.1 | section | Baseline | §0.1 | — | — | — | — | — | — | — | — | planned |
| S0.2 | section | Numbering | §0.2 | — | — | — | — | — | — | — | — | planned |
| S0.3 | section | Decided scope (user decisions, 2026-11-16) | §0.3 | — | — | — | — | — | — | — | — | planned |
| S0.4 | section | Ground rules | §0.4 | — | — | — | — | — | — | — | — | planned |
| S0.5 | section | Defects found while writing batch 1 | §0.5 | — | — | — | — | — | — | — | — | planned |
| F59 | foundation | Season positions are one registry | §F59 | catalog/season_positions.py; engine/environment/season_remap.py; services/integrity/season_positions.py | seasons:add, seasons:remove, seasons:reorder remap every registered column; startup repair | seasons:add, seasons:remove, seasons:reorder | WorldSeasonsSection | n/a | n/a | repair season_positions mends positions past the season count | tests/engine/environment/test_season_positions.py::test_removing_a_season_moves_a_gathering_and_a_birth_sign_with_it; tests/engine/environment/test_season_positions.py::test_a_position_beyond_the_seasons_is_mended | done |
| F60 | foundation | Weather draws and weather traits are typed in the catalogue | §F60 | catalog/weather.py; engine/environment/weather.py | weather draws each sampled year | weather:force | n/a | n/a | n/a | n/a | tests/unit/test_weather_traits.py; tests/engine/warfare/test_battle_depth.py | done |
| F61 | foundation | Calendar slots are one catalogue and one function | §F61 | catalog/calendar_slots.py; engine/lore/calendar_slots.py; services/integrity/rite_needs.py | rites and traditions ask slot_open | rite:requirements | RiteControls war switch | n/a | n/a | fixup rites.w52_war_need | tests/engine/lore/test_calendar_slots.py::test_a_holy_day_on_another_world_does_not_open_a_rite_slot; tests/engine/lore/test_calendar_slots.py::test_every_slot_opens_by_its_own_season | done |
| S52.1 | section | Up to eight seasons | §52.1 | — | — | — | — | — | — | — | — | planned |
| S52.2 | section | Frost and ice storm | §52.2 | — | — | — | — | — | — | — | — | planned |
| S52.3 | section | Six causes of long winters and summers | §52.3 | — | — | — | — | — | — | — | — | planned |
| S52.4 | section | Named years read the new sources | §52.4 | — | — | — | — | — | — | — | — | planned |
| S52.5 | section | Ten calendar slots | §52.5 | — | — | — | — | — | — | — | — | planned |
| S52.6 | section | Integration of batch 1 | §52.6 | — | — | — | — | — | — | — | — | planned |
| S52.7 | section | Guards and proving tests | §52.7 | — | — | — | — | — | — | — | — | planned |
| S52.8 | section | Compliance catalogue (batch 1) | §52.8 | — | — | — | — | — | — | — | — | planned |
| S52.9 | section | Cross-cutting layers | §52.9 | — | — | — | — | — | — | — | — | planned |
| S52.10 | section | Couplings, loops, stories and decisions | §52.10 | — | — | — | — | — | — | — | — | planned |
| K.54 | decision | Why eight seasons at most? | Part K | — | — | — | — | — | — | — | — | planned |
| K.55 | decision | Are seasons equal in length? | Part K | — | — | — | — | — | — | — | — | planned |
| K.56 | decision | How do frost, ice storm, snow and hail differ? | Part K | — | — | — | — | — | — | — | — | planned |
| K.57 | decision | One long season per world? | Part K | — | — | — | — | — | — | — | — | planned |
| K.58 | decision | Does batch 1 add kinds of named year? | Part K | — | — | — | — | — | — | — | — | planned |
| K.59 | decision | What does the `campaign` slot mean? | Part K | — | — | — | — | — | — | — | — | planned |
| S52.11 | section | Execution order (batch 1) | §52.11 | — | — | — | — | — | — | — | — | planned |
| F62 | foundation | Terrain traits are typed in the catalogue | §F62 | catalog/terrain.py; engine/military/tables.py; engine/environment/profile.py | every terrain reader tests a trait | region_env:edit | n/a | n/a | n/a | n/a | tests/unit/test_terrain_traits.py; tests/unit/test_literal_enum_sets.py | done |
| F63 | foundation | Movement modes are typed by medium | §F63 | catalog/movement.py; engine/environment/profile.py; rules/renames.py | passability_of loops over MOVEMENT | region_env:edit | EntityEnvironment passability grid | n/a | n/a | split renames of the old terrain bases | tests/unit/test_movement_catalogue.py::test_every_terrain_has_a_passage_for_every_mode; tests/unit/test_movement_catalogue.py::test_an_old_terrain_base_override_reaches_every_ground_passage | done |
| F64 | foundation | Danger and hazard happenings are told from typed fields | §F64 | catalog/dangers.py; catalog/incident_kinds/nature_kinds.py; services/integrity/told_dangers.py | dangers and hazards record danger.harm and hazard.struck | n/a | n/a | n/a | danger.harm, hazard.struck | fixup incidents.w52_dangers | tests/unit/test_canned_lines.py::test_a_per_kind_sentence_table_in_a_catalogue_is_caught; tests/unit/test_prompt_bias_rules.py::test_a_chronicle_template_in_a_catalogue_is_scanned | done |
| S52.12 | section | Thirty terrain kinds | §52.12 | — | — | — | — | — | — | — | — | planned |
| S52.13 | section | Seventeen soil kinds | §52.13 | — | — | — | — | — | — | — | — | planned |
| S52.14 | section | Eight movement modes | §52.14 | — | — | — | — | — | — | — | — | planned |
| S52.15 | section | Sixteen scars | §52.15 | — | — | — | — | — | — | — | — | planned |
| S52.16 | section | Thirteen memories of the land | §52.16 | — | — | — | — | — | — | — | — | planned |
| S52.17 | section | Twelve danger sources | §52.17 | — | — | — | — | — | — | — | — | planned |
| S52.18 | section | Nine danger targets | §52.18 | — | — | — | — | — | — | — | — | planned |
| S52.19 | section | Seven seasonal terrain hazards | §52.19 | — | — | — | — | — | — | — | — | planned |
| S52.20 | section | Forty-two place kinds | §52.20 | — | — | — | — | — | — | — | — | planned |
| S52.21 | section | Twelve place secrets | §52.21 | — | — | — | — | — | — | — | — | planned |
| S52.22 | section | Ten succession stages | §52.22 | — | — | — | — | — | — | — | — | planned |
| S52.23 | section | Integration of batch 2 | §52.23 | — | — | — | — | — | — | — | — | planned |
| S52.24 | section | Guards and proving tests | §52.24 | — | — | — | — | — | — | — | — | planned |
| S52.25 | section | Compliance catalogue (batch 2) | §52.25 | — | — | — | — | — | — | — | — | planned |
| S52.26 | section | Cross-cutting layers | §52.26 | — | — | — | — | — | — | — | — | planned |
| S52.27 | section | Couplings, loops, stories and decisions | §52.27 | — | — | — | — | — | — | — | — | planned |
| K.60 | decision | Is `ambush` a target? | Part K | — | — | — | — | — | — | — | — | planned |
| K.61 | decision | Where do passage values live? | Part K | — | — | — | — | — | — | — | — | planned |
| K.62 | decision | Who may move `incorporeal`? | Part K | — | — | — | — | — | — | — | — | planned |
| S52.28 | section | Order of work (batch 2) | §52.28 | — | — | — | — | — | — | — | — | planned |
| F65 | foundation | Rocks, strata and sediments are typed catalogues | §F65 | — | — | — | — | — | — | — | — | in-progress |
| S52.29 | section | Twenty-five rock kinds | §52.29 | — | — | — | — | — | — | — | — | planned |
| S52.30 | section | Nine strata beneath the ground | §52.30 | — | — | — | — | — | — | — | — | planned |
| S52.31 | section | Six kinds of seal | §52.31 | — | — | — | — | — | — | — | — | planned |
| S52.32 | section | Eight causes of a river's change of course | §52.32 | — | — | — | — | — | — | — | — | planned |
| S52.33 | section | Eight sediment kinds | §52.33 | — | — | — | — | — | — | — | — | planned |
| S52.34 | section | Eleven coast forms | §52.34 | — | — | — | — | — | — | — | — | planned |
| S52.35 | section | Six fossil sources | §52.35 | — | — | — | — | — | — | — | — | planned |
| S52.36 | section | Six readings of fossils | §52.36 | — | — | — | — | — | — | — | — | planned |
| S52.37 | section | Integration, guards, catalogue and order | §52.37 | — | — | — | — | — | — | — | — | planned |
| K.63 | decision | Are spec 13's world-type layers kept? | Part K | — | — | — | — | — | — | — | — | planned |
| K.64 | decision | May a living world be mined? | Part K | — | — | — | — | — | — | — | — | planned |
| K.65 | decision | Does revival reach dead gods? | Part K | — | — | — | — | — | — | — | — | planned |
| F66 | foundation | Planetary cycles are typed rows | §F66 | catalog/planetary_cycles.py; engine/cosmos/cycles.py; db/tables/evolution.py | world_cycles step turns one row per cycle | world_cycle:edit, world_cycle:reset | EvolutionSection CycleCard | n/a | n/a | migration 9c9860da5822 moves columns to rows | tests/engine/core/test_evolution_w17.py::test_a_cycle_held_by_a_god_keeps_its_stock_and_the_rest_turn; tests/engine/core/test_evolution_w17.py::test_a_fixed_cycle_column_is_caught | done |
| S52.38 | section | Ten wind belts | §52.38 | — | — | — | — | — | — | — | — | planned |
| S52.39 | section | Four kinds of ocean current | §52.39 | — | — | — | — | — | — | — | — | planned |
| S52.40 | section | Five planetary cycles | §52.40 | — | — | — | — | — | — | — | — | planned |
| S52.41 | section | Integration, guards, catalogue and order (batch 4) | §52.41 | — | — | — | — | — | — | — | — | planned |
| K.66 | decision | Are oscillation phases widened? | Part K | — | — | — | — | — | — | — | — | planned |
| K.67 | decision | Are climate eras widened? | Part K | — | — | — | — | — | — | — | — | planned |
| K.68 | decision | What does the water cycle count on a world of another liquid? | Part K | — | — | — | — | — | — | — | — | planned |
| F67 | foundation | Catch grounds, gear and market ranks are typed catalogues | §F67 | catalog/catch.py; catalog/market_ranks.py; engine/agrarian/rings.py; engine/couplings/closures.py | rings rank places; grounds seed gear | law:enact (gear_ban gear) | n/a | n/a | n/a | n/a | tests/unit/test_catch_catalogue.py::test_a_gear_ban_cuts_only_the_gear_it_names; tests/unit/test_catch_catalogue.py::test_market_ranks_keep_their_order_and_reach | done |
| S52.42 | section | Five ranks of market place | §52.42 | — | — | — | — | — | — | — | — | planned |
| S52.43 | section | Six ways to govern a commons | §52.43 | — | — | — | — | — | — | — | — | planned |
| S52.44 | section | Eight catch grounds | §52.44 | — | — | — | — | — | — | — | — | planned |
| S52.45 | section | Ten kinds of gear | §52.45 | — | — | — | — | — | — | — | — | planned |
| S52.46 | section | Integration, guards, catalogue and order (batch 5) | §52.46 | — | — | — | — | — | — | — | — | planned |
| K.69 | decision | Are rings, soil stocks, perennials and commons kinds widened? | Part K | — | — | — | — | — | — | — | — | planned |
| K.70 | decision | Are fish ponds a catch ground or a farm? | Part K | — | — | — | — | — | — | — | — | planned |
| K.71 | decision | How are trained hunting animals used? | Part K | — | — | — | — | — | — | — | — | planned |
| F68 | foundation | Species families come from typed catalogues | §F68 | catalog/diets.py; catalog/domestication.py; catalog/senses.py | ecology steps read the catalogues | n/a | n/a | n/a | n/a | n/a | tests/unit/test_species_catalogues.py::test_diet_traits_keep_their_memberships | done |
| S52.47 | section | Fifteen diets | §52.47 | — | — | — | — | — | — | — | — | planned |
| S52.48 | section | Six social forms | §52.48 | — | — | — | — | — | — | — | — | planned |
| S52.49 | section | Eight biochemistries | §52.49 | — | — | — | — | — | — | — | — | planned |
| S52.50 | section | Seven stages of domestication | §52.50 | — | — | — | — | — | — | — | — | planned |
| S52.51 | section | Thirteen species roles | §52.51 | — | — | — | — | — | — | — | — | planned |
| S52.52 | section | Thirteen plant growth forms | §52.52 | — | — | — | — | — | — | — | — | planned |
| S52.53 | section | Thirteen plant parts | §52.53 | — | — | — | — | — | — | — | — | planned |
| S52.54 | section | Sixteen plant product categories | §52.54 | — | — | — | — | — | — | — | — | planned |
| S52.55 | section | Integration, guards, catalogue and order (batch 6) | §52.55 | — | — | — | — | — | — | — | — | planned |
| K.72 | decision | Are species and size classes widened? | Part K | — | — | — | — | — | — | — | — | planned |
| K.73 | decision | Are creature traits counted? | Part K | — | — | — | — | — | — | — | — | planned |
| K.74 | decision | Do parasite peoples imply a tone? | Part K | — | — | — | — | — | — | — | — | planned |
| S52.56 | section | Fifteen heritable traits | §52.56 | — | — | — | — | — | — | — | — | planned |
| S52.57 | section | Five trophic levels | §52.57 | — | — | — | — | — | — | — | — | planned |
| S52.58 | section | Seven keystone roles | §52.58 | — | — | — | — | — | — | — | — | planned |
| S52.59 | section | Eleven senses | §52.59 | — | — | — | — | — | — | — | — | planned |
| S52.60 | section | Five dormancy states | §52.60 | — | — | — | — | — | — | — | — | planned |
| S52.61 | section | Four kinds of temperature regulation | §52.61 | — | — | — | — | — | — | — | — | planned |
| S52.62 | section | Seven plant defences | §52.62 | — | — | — | — | — | — | — | — | planned |
| S52.63 | section | Eight resting states of carrion | §52.63 | — | — | — | — | — | — | — | — | planned |
| S52.64 | section | Integration, guards, catalogue and order (batch 7) | §52.64 | — | — | — | — | — | — | — | — | planned |
| K.75 | decision | Are kinds of symbiosis widened? | Part K | — | — | — | — | — | — | — | — | planned |
| K.76 | decision | Are ferment cultures widened? | Part K | — | — | — | — | — | — | — | — | planned |
| K.77 | decision | Does `athermic` mean immortal to the elements? | Part K | — | — | — | — | — | — | — | — | planned |
| S52.65 | section | Ten beast tempers | §52.65 | — | — | — | — | — | — | — | — | planned |
| S52.66 | section | Nine beast temperaments | §52.66 | — | — | — | — | — | — | — | — | planned |
| S52.67 | section | Seven habitats | §52.67 | — | — | — | — | — | — | — | — | planned |
| S52.68 | section | Seven aversions | §52.68 | — | — | — | — | — | — | — | — | planned |
| S52.69 | section | Six awakening triggers | §52.69 | — | — | — | — | — | — | — | — | planned |
| S52.70 | section | Nineteen beast product categories | §52.70 | — | — | — | — | — | — | — | — | planned |
| S52.71 | section | One taxonomy of fifteen kinds of knowledge | §52.71 | — | — | — | — | — | — | — | — | planned |
| S52.72 | section | Integration, guards, catalogue and order (batch 8) | §52.72 | — | — | — | — | — | — | — | — | planned |
| K.78 | decision | Are body materials and attacks widened? | Part K | — | — | — | — | — | — | — | — | planned |
| K.79 | decision | What does "held" mean for a beast? | Part K | — | — | — | — | — | — | — | — | planned |
| K.80 | decision | Which name survives the merge of `LoreKind` and `TeachingKind`? | Part K | — | — | — | — | — | — | — | — | planned |
| S52.73 | section | One taxonomy of fifteen ways of passing | §52.73 | — | — | — | — | — | — | — | — | planned |
| S52.74 | section | Twelve cure classes | §52.74 | — | — | — | — | — | — | — | — | planned |
| S52.75 | section | Eleven spread paths | §52.75 | — | — | — | — | — | — | — | — | planned |
| S52.76 | section | Twelve plague responses | §52.76 | — | — | — | — | — | — | — | — | planned |
| S52.77 | section | Climate affinity on two axes | §52.77 | — | — | — | — | — | — | — | — | planned |
| S52.78 | section | Integration, guards, catalogue and order (batch 9) | §52.78 | — | — | — | — | — | — | — | — | planned |
| K.81 | decision | Which name survives the merge? | Part K | — | — | — | — | — | — | — | — | planned |
| K.82 | decision | Are targets and agents widened? | Part K | — | — | — | — | — | — | — | — | planned |
| K.83 | decision | Are cure means (`CureKind`) and cure classes one concept? | Part K | — | — | — | — | — | — | — | — | planned |
| F69 | foundation | Body families come from typed catalogues | §F69 | catalog/harm_kinds.py; catalog/conditions.py | hits, healing, treatment and capacities read the catalogues | n/a | n/a | n/a | n/a | n/a | tests/unit/test_body_catalogues.py::test_injury_traits_keep_their_memberships | done |
| S52.79 | section | Sixteen body plans and fifty-four body parts | §52.79 | — | — | — | — | — | — | — | — | planned |
| S52.80 | section | Eighteen damage types | §52.80 | — | — | — | — | — | — | — | — | planned |
| S52.81 | section | Twenty-seven injury kinds | §52.81 | — | — | — | — | — | — | — | — | planned |
| S52.82 | section | Eight injury states | §52.82 | — | — | — | — | — | — | — | — | planned |
| S52.83 | section | Twenty-eight causes of harm | §52.83 | — | — | — | — | — | — | — | — | planned |
| S52.84 | section | Twenty-one conditions | §52.84 | — | — | — | — | — | — | — | — | planned |
| S52.85 | section | Eleven lasting maims | §52.85 | — | — | — | — | — | — | — | — | planned |
| S52.86 | section | Thirteen treatment steps | §52.86 | — | — | — | — | — | — | — | — | planned |
| S52.87 | section | Ten capacities | §52.87 | — | — | — | — | — | — | — | — | planned |
| S52.88 | section | Integration, guards and catalogue (batch 10) | §52.88 | — | — | — | — | — | — | — | — | planned |
| S52.89 | section | Couplings, stories, decisions and order (batch 10) | §52.89 | — | — | — | — | — | — | — | — | planned |
| K.84 | decision | Are tissues, functions, medicine tiers, systems and sensitivities widened? | Part K | — | — | — | — | — | — | — | — | planned |
| K.85 | decision | Is bleeding always harmful? | Part K | — | — | — | — | — | — | — | — | planned |
| K.86 | decision | Is `asphyxia` both a damage type and an injury kind? | Part K | — | — | — | — | — | — | — | — | planned |
| F70 | foundation | Package, mind and life-course families come from typed catalogues | §F70 | catalog/life_traits.py; catalog/life/polity.py; core/dispatch.py | engine steps read the trait catalogues and registered handlers | n/a | n/a | n/a | n/a | n/a | tests/unit/test_literal_enum_sets.py::test_the_source_keeps_every_family_in_its_catalogues | done |
| S52.90 | section | Seventeen effect package categories | §52.90 | — | — | — | — | — | — | — | — | planned |
| S52.91 | section | Audit of ways of passing, visibility and cures (52.91–52.93) | §52.91 | — | — | — | — | — | — | — | — | planned |
| S52.94 | section | Integration, guards, catalogue, stories and order (batch 11) | §52.94 | — | — | — | — | — | — | — | — | planned |
| S52.95 | section | Twenty-eight emotions | §52.95 | — | — | — | — | — | — | — | — | planned |
| S52.96 | section | Six grief stages | §52.96 | — | — | — | — | — | — | — | — | planned |
| S52.97 | section | Seven breaking points | §52.97 | — | — | — | — | — | — | — | — | planned |
| S52.98 | section | Audit of the rest of the inner life | §52.98 | — | — | — | — | — | — | — | — | planned |
| S52.99 | section | Integration, guards, catalogue, stories and order (batch 12) | §52.99 | — | — | — | — | — | — | — | — | planned |
| S52.100 | section | Thirteen life paths | §52.100 | — | — | — | — | — | — | — | — | planned |
| S52.101 | section | Nineteen life arcs | §52.101 | — | — | — | — | — | — | — | — | planned |
| S52.102 | section | Twenty-nine causes of death | §52.102 | — | — | — | — | — | — | — | — | planned |
| S52.103 | section | Twelve funeral customs | §52.103 | — | — | — | — | — | — | — | — | planned |
| S52.104 | section | Honour and shame of a death read from culture | §52.104 | — | — | — | — | — | — | — | — | planned |
| S52.105 | section | Integration, guards, catalogue, stories and order (batch 13) | §52.105 | — | — | — | — | — | — | — | — | planned |
| S52.106 | section | Twenty-one relation types | §52.106 | — | — | — | — | — | — | — | — | planned |
| S52.107 | section | Twenty-four interactions | §52.107 | — | — | — | — | — | — | — | — | planned |
| S52.108 | section | Ten circles | §52.108 | — | — | — | — | — | — | — | — | planned |
| S52.109 | section | Seven appeals | §52.109 | — | — | — | — | — | — | — | — | planned |
| S52.110 | section | Seven persuasion aims | §52.110 | — | — | — | — | — | — | — | — | planned |
| S52.111 | section | Nine contests | §52.111 | — | — | — | — | — | — | — | — | planned |
| S52.112 | section | Nine contest stakes | §52.112 | — | — | — | — | — | — | — | — | planned |
| S52.113 | section | Audit of the rest of hearts and hands | §52.113 | — | — | — | — | — | — | — | — | planned |
| S52.114 | section | Integration, guards, catalogue, stories and order (batch 14) | §52.114 | — | — | — | — | — | — | — | — | planned |
| S52.115 | section | Eleven house duties | §52.115 | — | — | — | — | — | — | — | — | planned |
| S52.116 | section | Nine intoxicants | §52.116 | — | — | — | — | — | — | — | — | planned |
| S52.117 | section | Seven uses of intoxicants | §52.117 | — | — | — | — | — | — | — | — | planned |
| S52.118 | section | Twelve shares of time | §52.118 | — | — | — | — | — | — | — | — | planned |
| S52.119 | section | Sixteen leisure pursuits | §52.119 | — | — | — | — | — | — | — | — | planned |
| S52.120 | section | Audit of the rest of hearth and home | §52.120 | — | — | — | — | — | — | — | — | planned |
| S52.121 | section | Integration, guards, catalogue, stories and order (batch 15) | §52.121 | — | — | — | — | — | — | — | — | planned |
| S52.122 | section | Sixteen biology variants | §52.122 | — | — | — | — | — | — | — | — | planned |
| S52.123 | section | Integration, guards, catalogue, stories and order (batch 16) | §52.123 | — | — | — | — | — | — | — | — | planned |
| S52.124 | section | Fifty-eight judged acts | §52.124 | — | — | — | — | — | — | — | — | planned |
| S52.125 | section | Eleven reputation axes | §52.125 | — | — | — | — | — | — | — | — | planned |
| S52.126 | section | Audit of the rest of codes of honour | §52.126 | — | — | — | — | — | — | — | — | planned |
| S52.127 | section | Integration, guards, catalogue and stories (batch 17) | §52.127 | — | — | — | — | — | — | — | — | planned |
| S52.128 | section | Decisions and order (batch 17) | §52.128 | — | — | — | — | — | — | — | — | planned |
| S52.129 | section | Sixty gene loci | §52.129 | — | — | — | — | — | — | — | — | planned |
| S52.130 | section | Succession rules named by side, as spec 16 names descent | §52.130 | — | — | — | — | — | — | — | — | planned |
| S52.131 | section | Eight inheritance customs | §52.131 | — | — | — | — | — | — | — | — | planned |
| S52.132 | section | Eighteen kin roles | §52.132 | — | — | — | — | — | — | — | — | planned |
| S52.133 | section | Fifteen dwelling kinds | §52.133 | — | — | — | — | — | — | — | — | planned |
| S52.134 | section | Integration, guards, catalogue, stories, decisions and order (batch 18) | §52.134 | — | — | — | — | — | — | — | — | planned |
| S52.135 | section | Cohorts by the biology's own sexes | §52.135 | — | — | — | — | — | — | — | — | planned |
| S52.136 | section | Five age bands | §52.136 | — | — | — | — | — | — | — | — | planned |
| S52.137 | section | Eight cohort conditions | §52.137 | — | — | — | — | — | — | — | — | planned |
| S52.138 | section | Seventeen kinds of work | §52.138 | — | — | — | — | — | — | — | — | planned |
| S52.139 | section | Seven mobility events | §52.139 | — | — | — | — | — | — | — | — | planned |
| S52.140 | section | Seventeen formative events | §52.140 | — | — | — | — | — | — | — | — | planned |
| S52.141 | section | Integration, guards, catalogue, stories, decisions and order (batch 19) | §52.141 | — | — | — | — | — | — | — | — | planned |
| S52.142 | section | Twelve identity layers | §52.142 | — | — | — | — | — | — | — | — | planned |
| S52.143 | section | Thirteen salience drivers | §52.143 | — | — | — | — | — | — | — | — | planned |
| S52.144 | section | Five ways of revival | §52.144 | — | — | — | — | — | — | — | — | planned |
| S52.145 | section | Five revival goals | §52.145 | — | — | — | — | — | — | — | — | planned |
| S52.146 | section | Twelve movement causes | §52.146 | — | — | — | — | — | — | — | — | planned |
| S52.147 | section | Audit of the rest of many banners | §52.147 | — | — | — | — | — | — | — | — | planned |
| S52.148 | section | Integration, guards, catalogue, stories, decisions and order (batch 20) | §52.148 | — | — | — | — | — | — | — | — | planned |
| S52.149 | section | Twelve crowd acts | §52.149 | — | — | — | — | — | — | — | — | planned |
| S52.150 | section | Five crowd feelings as typed rows | §52.150 | — | — | — | — | — | — | — | — | planned |
| S52.151 | section | Sixteen crowd triggers | §52.151 | — | — | — | — | — | — | — | — | planned |
| S52.152 | section | Integration, guards, catalogue, stories, decisions and order (batch 21) | §52.152 | — | — | — | — | — | — | — | — | planned |
| S52.153 | section | Twenty tradition functions | §52.153 | — | — | — | — | — | — | — | — | planned |
| S52.154 | section | Thirty-six gathering kinds | §52.154 | — | — | — | — | — | — | — | — | planned |
| S52.155 | section | Ten body marks | §52.155 | — | — | — | — | — | — | — | — | planned |
| S52.156 | section | Eleven meanings of marks | §52.156 | — | — | — | — | — | — | — | — | planned |
| S52.157 | section | Six naming patterns | §52.157 | — | — | — | — | — | — | — | — | planned |
| S52.158 | section | Eight name forms | §52.158 | — | — | — | — | — | — | — | — | planned |
| S52.159 | section | Age grades named by age | §52.159 | — | — | — | — | — | — | — | — | planned |
| S52.160 | section | Integration, guards, catalogue, stories, decisions and order (batch 22) | §52.160 | — | — | — | — | — | — | — | — | planned |
| S52.161 | section | Thirteen gift occasions | §52.161 | — | — | — | — | — | — | — | — | planned |
| S52.162 | section | Eight gift states | §52.162 | — | — | — | — | — | — | — | — | planned |
| S52.163 | section | Integration, guards, catalogue, stories, decisions and order (batch 23) | §52.163 | — | — | — | — | — | — | — | — | planned |
| S52.164 | section | Seven art market roles | §52.164 | — | — | — | — | — | — | — | — | planned |
| S52.165 | section | Seven kinds of forgery | §52.165 | — | — | — | — | — | — | — | — | planned |
| S52.166 | section | Eleven kinds of cultural right | §52.166 | — | — | — | — | — | — | — | — | planned |
| S52.167 | section | Eight ways of gaining a right | §52.167 | — | — | — | — | — | — | — | — | planned |
| S52.168 | section | Audit of the rest of muse and market | §52.168 | — | — | — | — | — | — | — | — | planned |
| S52.169 | section | Integration, guards, catalogue, stories, decisions and order (batch 24) | §52.169 | — | — | — | — | — | — | — | — | planned |
| S52.170 | section | Six kinds of club | §52.170 | — | — | — | — | — | — | — | — | planned |
| S52.171 | section | Fixing contests | §52.171 | — | — | — | — | — | — | — | — | planned |
| S52.172 | section | Integration, guards, catalogue, stories, decisions and order (batch 25) | §52.172 | — | — | — | — | — | — | — | — | planned |
| S52.173 | section | Six numeral bases | §52.173 | — | — | — | — | — | — | — | — | planned |
| S52.174 | section | Ten language modalities | §52.174 | — | — | — | — | — | — | — | — | planned |
| S52.175 | section | Six language stages | §52.175 | — | — | — | — | — | — | — | — | planned |
| S52.176 | section | Eight sense shifts | §52.176 | — | — | — | — | — | — | — | — | planned |
| S52.177 | section | Seven word registers | §52.177 | — | — | — | — | — | — | — | — | planned |
| S52.178 | section | Six causes of script change | §52.178 | — | — | — | — | — | — | — | — | planned |
| S52.179 | section | Fourteen writing media | §52.179 | — | — | — | — | — | — | — | — | planned |
| S52.180 | section | Six language policies | §52.180 | — | — | — | — | — | — | — | — | planned |
| S52.181 | section | Eight sociolects | §52.181 | — | — | — | — | — | — | — | — | planned |
| S52.182 | section | Five causes of sign languages | §52.182 | — | — | — | — | — | — | — | — | planned |
| S52.183 | section | Audit of the rest of tongues of ages (52.183–52.185) | §52.183 | — | — | — | — | — | — | — | — | planned |
| S52.186 | section | Integration, guards, catalogue, stories, decisions and order (batch 26) | §52.186 | — | — | — | — | — | — | — | — | planned |
| S52.187 | section | Twelve kinds of account | §52.187 | — | — | — | — | — | — | — | — | planned |
| S52.188 | section | Seven account stances | §52.188 | — | — | — | — | — | — | — | — | planned |
| S52.189 | section | Integration, guards, catalogue, stories, decisions and order (batch 27) | §52.189 | — | — | — | — | — | — | — | — | planned |
| F71 | foundation | Goods and materials families come from typed catalogues | §F71 | catalog/goods_traits.py; catalog/goods_tables.py | economy steps read the goods traits | n/a | n/a | n/a | n/a | n/a | tests/unit/test_literal_enum_sets.py::test_only_static_tables_outside_a_catalogue_are_caught | done |
| S52.190 | section | Forty-five materials | §52.190 | — | — | — | — | — | — | — | — | planned |
| S52.191 | section | Ten material origins | §52.191 | — | — | — | — | — | — | — | — | planned |
| S52.192 | section | Forty-three built-in goods | §52.192 | — | — | — | — | — | — | — | — | planned |
| S52.193 | section | Twenty-four workshops | §52.193 | — | — | — | — | — | — | — | — | planned |
| S52.194 | section | Twenty-six processes | §52.194 | — | — | — | — | — | — | — | — | planned |
| S52.195 | section | Six pollutants | §52.195 | — | — | — | — | — | — | — | — | planned |
| S52.196 | section | Twelve chemical products | §52.196 | — | — | — | — | — | — | — | — | planned |
| S52.197 | section | Audit of the rest of forge and furnace (52.197–52.198) | §52.197 | — | — | — | — | — | — | — | — | planned |
| S52.199 | section | Integration, guards, catalogue, stories, decisions and order (batch 28) | §52.199 | — | — | — | — | — | — | — | — | planned |
| S52.200 | section | Six credit states | §52.200 | — | — | — | — | — | — | — | — | planned |
| S52.201 | section | Seven loan states | §52.201 | — | — | — | — | — | — | — | — | planned |
| S52.202 | section | Five forms of saving | §52.202 | — | — | — | — | — | — | — | — | planned |
| S52.203 | section | Six insurance covers | §52.203 | — | — | — | — | — | — | — | — | planned |
| S52.204 | section | Four speculation states | §52.204 | — | — | — | — | — | — | — | — | planned |
| S52.205 | section | Three market plays | §52.205 | — | — | — | — | — | — | — | — | planned |
| S52.206 | section | The rest, integration, catalogue and order (batch 29) (52.206–52.207) | §52.206 | — | — | — | — | — | — | — | — | planned |
| S52.208 | section | Seven trade route media in one taxonomy | §52.208 | — | — | — | — | — | — | — | — | planned |
| S52.209 | section | Seven route states | §52.209 | — | — | — | — | — | — | — | — | planned |
| S52.210 | section | Seven trade losses | §52.210 | — | — | — | — | — | — | — | — | planned |
| S52.211 | section | Eight convoy states | §52.211 | — | — | — | — | — | — | — | — | planned |
| S52.212 | section | Ten containers | §52.212 | — | — | — | — | — | — | — | — | planned |
| S52.213 | section | Eight navigation aids | §52.213 | — | — | — | — | — | — | — | — | planned |
| S52.214 | section | The rest, integration, catalogue and order (batch 30) | §52.214 | — | — | — | — | — | — | — | — | planned |
| S52.215 | section | Nine reasons for labour allocation | §52.215 | — | — | — | — | — | — | — | — | planned |
| S52.216 | section | Eleven shortfalls | §52.216 | — | — | — | — | — | — | — | — | planned |
| S52.217 | section | The rest, integration, catalogue and order (batch 31) (52.217–52.218) | §52.217 | — | — | — | — | — | — | — | — | planned |
| S52.219 | section | Twenty-four district kinds | §52.219 | — | — | — | — | — | — | — | — | planned |
| S52.220 | section | Eight causes of rebuilding | §52.220 | — | — | — | — | — | — | — | — | planned |
| S52.221 | section | Four ways of rebuilding | §52.221 | — | — | — | — | — | — | — | — | planned |
| S52.222 | section | Seven kinds of relief | §52.222 | — | — | — | — | — | — | — | — | planned |
| S52.223 | section | The rest, integration, catalogue and order (batch 32) (52.223–52.224) | §52.223 | — | — | — | — | — | — | — | — | planned |
| S52.225 | section | Seven construction states | §52.225 | — | — | — | — | — | — | — | — | planned |
| S52.226 | section | Five kinds of collection | §52.226 | — | — | — | — | — | — | — | — | planned |
| S52.227 | section | Eight kinds of collected piece | §52.227 | — | — | — | — | — | — | — | — | planned |
| S52.228 | section | Nine gardens | §52.228 | — | — | — | — | — | — | — | — | planned |
| S52.229 | section | Seven ways of lifting water | §52.229 | — | — | — | — | — | — | — | — | planned |
| S52.230 | section | The rest, integration, catalogue and order (batch 33) (52.230–52.231) | §52.230 | — | — | — | — | — | — | — | — | planned |
| S52.232 | section | Five stances toward relics | §52.232 | — | — | — | — | — | — | — | — | planned |
| S52.233 | section | Six aids to sight and hearing | §52.233 | — | — | — | — | — | — | — | — | planned |
| S52.234 | section | Eight clocks | §52.234 | — | — | — | — | — | — | — | — | planned |
| S52.235 | section | Seven locks | §52.235 | — | — | — | — | — | — | — | — | planned |
| S52.236 | section | The rest, integration, catalogue and order (batch 34) (52.236–52.237) | §52.236 | — | — | — | — | — | — | — | — | planned |
| S52.238 | section | Six kinds of criminal organisation | §52.238 | — | — | — | — | — | — | — | — | planned |
| S52.239 | section | Four state stances toward crime | §52.239 | — | — | — | — | — | — | — | — | planned |
| S52.240 | section | Six kinds of fugitive | §52.240 | — | — | — | — | — | — | — | — | planned |
| S52.241 | section | Six kinds of sanctuary | §52.241 | — | — | — | — | — | — | — | — | planned |
| S52.242 | section | The rest, integration, catalogue and order (batch 35) (52.242–52.243) | §52.242 | — | — | — | — | — | — | — | — | planned |
| S52.244 | section | Nine council tasks | §52.244 | — | — | — | — | — | — | — | — | planned |
| S52.245 | section | Ten mandates | §52.245 | — | — | — | — | — | — | — | — | planned |
| S52.246 | section | Seven crisis demands | §52.246 | — | — | — | — | — | — | — | — | planned |
| S52.247 | section | Eight court positions | §52.247 | — | — | — | — | — | — | — | — | planned |
| S52.248 | section | The rest, integration, catalogue and order (batch 36) (52.248–52.249) | §52.248 | — | — | — | — | — | — | — | — | planned |
| S52.250 | section | Six client roles | §52.250 | — | — | — | — | — | — | — | — | planned |
| S52.251 | section | Eight member rights | §52.251 | — | — | — | — | — | — | — | — | planned |
| S52.252 | section | Eight ways of naturalisation | §52.252 | — | — | — | — | — | — | — | — | planned |
| S52.253 | section | The rest, integration, catalogue and order (batch 37) | §52.253 | — | — | — | — | — | — | — | — | planned |
| S52.254 | section | Title ranks: withdrawn | §52.254 | — | — | — | — | — | — | — | — | planned |
| S52.255 | section | Eight claim bases | §52.255 | — | — | — | — | — | — | — | — | planned |
| S52.256 | section | Nine succession rules | §52.256 | — | — | — | — | — | — | — | — | planned |
| S52.257 | section | The rest, integration, catalogue and order (batch 38) (52.257–52.258) | §52.257 | — | — | — | — | — | — | — | — | planned |
| S52.259 | section | Twelve areas of law | §52.259 | — | — | — | — | — | — | — | — | planned |
| S52.260 | section | Seven court levels | §52.260 | — | — | — | — | — | — | — | — | planned |
| S52.261 | section | Eight kinds of evidence | §52.261 | — | — | — | — | — | — | — | — | planned |
| S52.262 | section | Registry kinds named by function | §52.262 | — | — | — | — | — | — | — | — | planned |
| S52.263 | section | Thirteen oaths | §52.263 | — | — | — | — | — | — | — | — | planned |
| S52.264 | section | The rest, integration, catalogue and order (batch 39) (52.264–52.265) | §52.264 | — | — | — | — | — | — | — | — | planned |
| S52.266 | section | Fourteen faction goals | §52.266 | — | — | — | — | — | — | — | — | planned |
| S52.267 | section | Seventeen faction actions | §52.267 | — | — | — | — | — | — | — | — | planned |
| S52.268 | section | Seven estate privileges | §52.268 | — | — | — | — | — | — | — | — | planned |
| S52.269 | section | Eight cooperative purposes | §52.269 | — | — | — | — | — | — | — | — | planned |
| S52.270 | section | The rest, integration, catalogue and order (batch 40) | §52.270 | — | — | — | — | — | — | — | — | planned |
| S52.271 | section | Five party roles | §52.271 | — | — | — | — | — | — | — | — | planned |
| S52.272 | section | Seven treaty states | §52.272 | — | — | — | — | — | — | — | — | planned |
| S52.273 | section | Five crisis states | §52.273 | — | — | — | — | — | — | — | — | planned |
| S52.274 | section | Five regional standings | §52.274 | — | — | — | — | — | — | — | — | planned |
| S52.275 | section | Seven council resolutions | §52.275 | — | — | — | — | — | — | — | — | planned |
| S52.276 | section | The rest, integration, catalogue and order (batch 41) | §52.276 | — | — | — | — | — | — | — | — | planned |
| S52.277 | section | Audit: complete as built | §52.277 | — | — | — | — | — | — | — | — | planned |
| S52.278 | section | Eleven kinds of message | §52.278 | — | — | — | — | — | — | — | — | planned |
| S52.279 | section | Seven message states | §52.279 | — | — | — | — | — | — | — | — | planned |
| S52.280 | section | Six fates of envoys | §52.280 | — | — | — | — | — | — | — | — | planned |
| S52.281 | section | Five signal states | §52.281 | — | — | — | — | — | — | — | — | planned |
| S52.282 | section | Seven subjects of opinion | §52.282 | — | — | — | — | — | — | — | — | planned |
| S52.283 | section | The rest, integration, catalogue and order (batch 43) | §52.283 | — | — | — | — | — | — | — | — | planned |
| S52.284 | section | Five prices of knowledge | §52.284 | — | — | — | — | — | — | — | — | planned |
| S52.285 | section | Four kinds of claim | §52.285 | — | — | — | — | — | — | — | — | planned |
| S52.286 | section | Four claim states | §52.286 | — | — | — | — | — | — | — | — | planned |
| S52.287 | section | The rest, integration, catalogue and order (batch 44) (52.287–52.288) | §52.287 | — | — | — | — | — | — | — | — | planned |
| S52.289 | section | Eighteen kinds of secret | §52.289 | — | — | — | — | — | — | — | — | planned |
| S52.290 | section | Eight hook demands | §52.290 | — | — | — | — | — | — | — | — | planned |
| S52.291 | section | Nine origins of favour | §52.291 | — | — | — | — | — | — | — | — | planned |
| S52.292 | section | Eight reasons for a false identity | §52.292 | — | — | — | — | — | — | — | — | planned |
| S52.293 | section | The rest, integration, catalogue and order (batch 45) (52.293–52.295) | §52.293 | — | — | — | — | — | — | — | — | planned |
| S52.296 | section | Ten spy operations | §52.296 | — | — | — | — | — | — | — | — | planned |
| S52.297 | section | Six spy motives | §52.297 | — | — | — | — | — | — | — | — | planned |
| S52.298 | section | Seven agent states | §52.298 | — | — | — | — | — | — | — | — | planned |
| S52.299 | section | The rest, integration, catalogue and order (batch 46) (52.299–52.300) | §52.299 | — | — | — | — | — | — | — | — | planned |
| S52.301 | section | Audit: complete as built | §52.301 | — | — | — | — | — | — | — | — | planned |
| S52.302 | section | Ten army stances | §52.302 | — | — | — | — | — | — | — | — | planned |
| S52.303 | section | Eight army roles | §52.303 | — | — | — | — | — | — | — | — | planned |
| S52.304 | section | Seven unit honours | §52.304 | — | — | — | — | — | — | — | — | planned |
| S52.305 | section | Five veteran grants | §52.305 | — | — | — | — | — | — | — | — | planned |
| S52.306 | section | The rest, integration, catalogue and order (batch 48) (52.306–52.308) | §52.306 | — | — | — | — | — | — | — | — | planned |
| S52.309 | section | Six casualty fates | §52.309 | — | — | — | — | — | — | — | — | planned |
| S52.310 | section | Nine captive fates | §52.310 | — | — | — | — | — | — | — | — | planned |
| S52.311 | section | The rest, integration, catalogue and order (batch 49) (52.311–52.312) | §52.311 | — | — | — | — | — | — | — | — | planned |
| S52.313 | section | Six siege actions | §52.313 | — | — | — | — | — | — | — | — | planned |
| S52.314 | section | Thirteen siege works | §52.314 | — | — | — | — | — | — | — | — | planned |
| S52.315 | section | Seven defender actions | §52.315 | — | — | — | — | — | — | — | — | planned |
| S52.316 | section | Five choices after a fall | §52.316 | — | — | — | — | — | — | — | — | planned |
| S52.317 | section | Five siege states | §52.317 | — | — | — | — | — | — | — | — | planned |
| S52.318 | section | The rest, integration, catalogue and order (batch 50) (52.318–52.319) | §52.318 | — | — | — | — | — | — | — | — | planned |
| S52.320 | section | Audit: complete as built | §52.320 | — | — | — | — | — | — | — | — | planned |
| S52.321 | section | Thirteen crew stations | §52.321 | — | — | — | — | — | — | — | — | planned |
| S52.322 | section | The rest, integration, catalogue and order (batch 52) | §52.322 | — | — | — | — | — | — | — | — | planned |
| S52.323 | section | Six duel contexts | §52.323 | — | — | — | — | — | — | — | — | planned |
| S52.324 | section | Eight duel endings | §52.324 | — | — | — | — | — | — | — | — | planned |
| S52.325 | section | The rest, integration, catalogue and order (batch 53) | §52.325 | — | — | — | — | — | — | — | — | planned |
| S52.326 | section | Ten states of named captives | §52.326 | — | — | — | — | — | — | — | — | planned |
| S52.327 | section | The rest, integration, catalogue and order (batch 54) | §52.327 | — | — | — | — | — | — | — | — | planned |
| S52.328 | section | Audit: complete as built | §52.328 | — | — | — | — | — | — | — | — | planned |
| S52.329 | section | Six kinds of vision | §52.329 | — | — | — | — | — | — | — | — | planned |
| S52.330 | section | Six causes of a god's silence | §52.330 | — | — | — | — | — | — | — | — | planned |
| S52.331 | section | Six sacraments | §52.331 | — | — | — | — | — | — | — | — | planned |
| S52.332 | section | Four protections of sacraments | §52.332 | — | — | — | — | — | — | — | — | planned |
| S52.333 | section | The rest, integration, catalogue and order (batch 56) | §52.333 | — | — | — | — | — | — | — | — | planned |
| S52.334 | section | Four paths of rebirth | §52.334 | — | — | — | — | — | — | — | — | planned |
| S52.335 | section | The rest, integration, catalogue and order (batch 57) | §52.335 | — | — | — | — | — | — | — | — | planned |
| S52.336 | section | Seventeen kinds of place spirit | §52.336 | — | — | — | — | — | — | — | — | planned |
| S52.337 | section | Six offences to spirits | §52.337 | — | — | — | — | — | — | — | — | planned |
| S52.338 | section | Nine kinds of petition | §52.338 | — | — | — | — | — | — | — | — | planned |
| S52.339 | section | The rest, integration, catalogue and order (batch 58) (52.339–52.340) | §52.339 | — | — | — | — | — | — | — | — | planned |
| S52.341 | section | Nine luck signs | §52.341 | — | — | — | — | — | — | — | — | planned |
| S52.342 | section | Eight reaches of luck | §52.342 | — | — | — | — | — | — | — | — | planned |
| S52.343 | section | Six charm powers | §52.343 | — | — | — | — | — | — | — | — | planned |
| S52.344 | section | Seven outcomes of an accusation | §52.344 | — | — | — | — | — | — | — | — | planned |
| S52.345 | section | The rest, integration, catalogue and order (batch 59) | §52.345 | — | — | — | — | — | — | — | — | planned |
| S52.346 | section | Nine kinds of divination | §52.346 | — | — | — | — | — | — | — | — | planned |
| S52.347 | section | Eight divination questions | §52.347 | — | — | — | — | — | — | — | — | planned |
| S52.348 | section | The rest, integration, catalogue and order (batch 60) | §52.348 | — | — | — | — | — | — | — | — | planned |
| S52.349 | section | Six spell ranges | §52.349 | — | — | — | — | — | — | — | — | planned |
| S52.350 | section | Six spell durations | §52.350 | — | — | — | — | — | — | — | — | planned |
| S52.351 | section | Seven spell targets | §52.351 | — | — | — | — | — | — | — | — | planned |
| S52.352 | section | Six ways of recharging | §52.352 | — | — | — | — | — | — | — | — | planned |
| S52.353 | section | The rest, integration, catalogue and order (batch 61) | §52.353 | — | — | — | — | — | — | — | — | planned |
| S52.354 | section | Seven link tokens | §52.354 | — | — | — | — | — | — | — | — | planned |
| S52.355 | section | The rest, integration, catalogue and order (batch 62) | §52.355 | — | — | — | — | — | — | — | — | planned |
| S52.356 | section | Six quest trials | §52.356 | — | — | — | — | — | — | — | — | planned |
| S52.357 | section | Five layers that lay a geas | §52.357 | — | — | — | — | — | — | — | — | planned |
| S52.358 | section | The rest, integration, catalogue and order (batch 63) | §52.358 | — | — | — | — | — | — | — | — | planned |
| S52.359 | section | Fifteen kinds of order | §52.359 | — | — | — | — | — | — | — | — | planned |
| S52.360 | section | Seven order conditions | §52.360 | — | — | — | — | — | — | — | — | planned |
| S52.361 | section | Seven command tokens | §52.361 | — | — | — | — | — | — | — | — | planned |
| S52.362 | section | The rest, integration, catalogue and order (batch 64) | §52.362 | — | — | — | — | — | — | — | — | planned |
| S52.363 | section | Three modes of worship | §52.363 | — | — | — | — | — | — | — | — | planned |
| S52.364 | section | Four tones of prayer | §52.364 | — | — | — | — | — | — | — | — | planned |
| S52.365 | section | The rest, integration, catalogue and order (batch 65) | §52.365 | — | — | — | — | — | — | — | — | planned |
| S52.366 | section | Five manifestations | §52.366 | — | — | — | — | — | — | — | — | planned |
| S52.367 | section | The rest, integration, catalogue and order (batch 66) | §52.367 | — | — | — | — | — | — | — | — | planned |
| S52.368 | section | Audit: complete as built | §52.368 | — | — | — | — | — | — | — | — | planned |
| S52.369 | section | Eight causes of divine wounds | §52.369 | — | — | — | — | — | — | — | — | planned |
| S52.370 | section | The rest, integration, catalogue and order (batch 68) | §52.370 | — | — | — | — | — | — | — | — | planned |
| S52.371 | section | Six council penalties | §52.371 | — | — | — | — | — | — | — | — | planned |
| S52.372 | section | Five origins of servitors | §52.372 | — | — | — | — | — | — | — | — | planned |
| S52.373 | section | The rest, integration, catalogue and order (batch 69) | §52.373 | — | — | — | — | — | — | — | — | planned |
| S52.374 | section | Audit: complete as built | §52.374 | — | — | — | — | — | — | — | — | planned |
| S52.375 | section | Six exemptions from natural laws | §52.375 | — | — | — | — | — | — | — | — | planned |
| S52.376 | section | The rest, integration, catalogue and order (batch 71) | §52.376 | — | — | — | — | — | — | — | — | planned |
| S52.377 | section | Five gains of an outer bargain | §52.377 | — | — | — | — | — | — | — | — | planned |
| S52.378 | section | Five prices of an outer bargain | §52.378 | — | — | — | — | — | — | — | — | planned |
| S52.379 | section | The rest, integration, catalogue and order (batch 72) | §52.379 | — | — | — | — | — | — | — | — | planned |
| S52.380 | section | Six life environments | §52.380 | — | — | — | — | — | — | — | — | planned |
| S52.381 | section | Six air needs | §52.381 | — | — | — | — | — | — | — | — | planned |
| S52.382 | section | Five gravity bands | §52.382 | — | — | — | — | — | — | — | — | planned |
| S52.383 | section | The rest, integration, catalogue and order (batch 73) | §52.383 | — | — | — | — | — | — | — | — | planned |
| S52.384 | section | Six impacting bodies | §52.384 | — | — | — | — | — | — | — | — | planned |
| S52.385 | section | Five impact outcomes | §52.385 | — | — | — | — | — | — | — | — | planned |
| S52.386 | section | The rest, integration, catalogue and order (batch 74) | §52.386 | — | — | — | — | — | — | — | — | planned |
| S52.387 | section | Nine ends of worlds | §52.387 | — | — | — | — | — | — | — | — | planned |
| S52.388 | section | Ten causes of an end | §52.388 | — | — | — | — | — | — | — | — | planned |
| S52.389 | section | The rest, integration, catalogue and order (batch 75) | §52.389 | — | — | — | — | — | — | — | — | planned |
| S52.390 | section | Eleven ways of settling | §52.390 | — | — | — | — | — | — | — | — | planned |
| S52.391 | section | Eight grounds of war | §52.391 | — | — | — | — | — | — | — | — | planned |
| S52.392 | section | The rest, integration, catalogue and order (batch 76) | §52.392 | — | — | — | — | — | — | — | — | planned |
| S52.393 | section | Audit: complete as built | §52.393 | — | — | — | — | — | — | — | — | planned |
| S52.394 | section | Eight journey intents | §52.394 | — | — | — | — | — | — | — | — | planned |
| S52.395 | section | The rest, integration, catalogue and order (batch 78) | §52.395 | — | — | — | — | — | — | — | — | planned |
| S52.396 | section | Audit: complete as built | §52.396 | — | — | — | — | — | — | — | — | planned |
| S52.397 | section | Audit: complete as built | §52.397 | — | — | — | — | — | — | — | — | planned |
| S52.398 | section | Nine fields of great persons | §52.398 | — | — | — | — | — | — | — | — | planned |
| S52.399 | section | The rest, integration, catalogue and order (batch 81) | §52.399 | — | — | — | — | — | — | — | — | planned |
| S52.400 | section | Three numeral notations | §52.400 | — | — | — | — | — | — | — | — | planned |
| S52.401 | section | The rest, integration, catalogue and order (batch 82) | §52.401 | — | — | — | — | — | — | — | — | planned |
| S52.402 | section | Audit: complete as built | §52.402 | — | — | — | — | — | — | — | — | planned |
| S52.403 | section | Every spec 17 mechanic in the storyteller's palette | §52.403 | — | — | — | — | — | — | — | — | planned |
| S52.404 | section | Eight expedition roles | §52.404 | — | — | — | — | — | — | — | — | planned |
| S52.405 | section | Six expedition grounds | §52.405 | — | — | — | — | — | — | — | — | planned |
| S52.406 | section | Eleven states of resolve | §52.406 | — | — | — | — | — | — | — | — | planned |
| S52.407 | section | Site challenges, digging risks and battlefield features | §52.407 | — | — | — | — | — | — | — | — | planned |
| S52.408 | section | The rest, integration, catalogue and order (batch 85) | §52.408 | — | — | — | — | — | — | — | — | planned |
| S52.409 | section | Audit of the boundless | §52.409 | — | — | — | — | — | — | — | — | planned |
| S52.410 | section | Audit of minds unmade | §52.410 | — | — | — | — | — | — | — | — | planned |
| S52.411 | section | Audit of the remade | §52.411 | — | — | — | — | — | — | — | — | planned |
| S52.412 | section | Audit of every voice at once | §52.412 | — | — | — | — | — | — | — | — | planned |
| S52.413 | section | Audit of plenty and ruin | §52.413 | — | — | — | — | — | — | — | — | planned |
| S52.414 | section | Audit of the born gifted | §52.414 | — | — | — | — | — | — | — | — | planned |
| S52.415 | section | Audit of the hidden folk | §52.415 | — | — | — | — | — | — | — | — | planned |
| S52.416 | section | Audit of grown, not built | §52.416 | — | — | — | — | — | — | — | — | planned |
| S52.417 | section | Dimension elements: withdrawn | §52.417 | — | — | — | — | — | — | — | — | planned |
| S52.418 | section | Ten being agendas and six being scales | §52.418 | — | — | — | — | — | — | — | — | planned |
| S52.419 | section | Ten rift causes | §52.419 | — | — | — | — | — | — | — | — | planned |
| S52.420 | section | Eleven purposes of made minds and six ways into made realms | §52.420 | — | — | — | — | — | — | — | — | planned |
| S52.421 | section | Ten augment kinds | §52.421 | — | — | — | — | — | — | — | — | planned |
| S52.422 | section | Nine surveillance foci | §52.422 | — | — | — | — | — | — | — | — | planned |
| S52.423 | section | Four legal levels of powers and six attitudes toward the gifted | §52.423 | — | — | — | — | — | — | — | — | planned |
| S52.424 | section | Five stances toward living craft | §52.424 | — | — | — | — | — | — | — | — | planned |
| S52.425 | section | Integration, catalogue and order (second pass) | §52.425 | — | — | — | — | — | — | — | — | planned |
| S52.426 | section | Five water readings of a season and the onset of every season | §52.426 | — | — | — | — | — | — | — | — | planned |
| S52.427 | section | Twenty-five weather kinds and eleven weather effects | §52.427 | — | — | — | — | — | — | — | — | planned |
| S52.428 | section | Eight causes of long seasons and five reaches | §52.428 | — | — | — | — | — | — | — | — | planned |
| S52.429 | section | Ten kinds of named year | §52.429 | — | — | — | — | — | — | — | — | planned |
| S52.430 | section | Fourteen calendar slots | §52.430 | — | — | — | — | — | — | — | — | planned |
| S52.431 | section | Thirty-four terrain kinds | §52.431 | — | — | — | — | — | — | — | — | planned |
| S52.432 | section | Nineteen soil kinds | §52.432 | — | — | — | — | — | — | — | — | planned |
| S52.433 | section | Ten movement modes | §52.433 | — | — | — | — | — | — | — | — | planned |
| S52.434 | section | Nineteen scars | §52.434 | — | — | — | — | — | — | — | — | planned |
| S52.435 | section | Sixteen memories of the land | §52.435 | — | — | — | — | — | — | — | — | planned |
| S52.436 | section | Fifteen danger sources and eleven danger targets | §52.436 | — | — | — | — | — | — | — | — | planned |
| S52.437 | section | Ten seasonal terrain hazards | §52.437 | — | — | — | — | — | — | — | — | planned |
| S52.438 | section | Forty-eight place kinds | §52.438 | — | — | — | — | — | — | — | — | planned |
| S52.439 | section | Fifteen place secrets | §52.439 | — | — | — | — | — | — | — | — | planned |
| S52.440 | section | Twelve succession stages | §52.440 | — | — | — | — | — | — | — | — | planned |
| S52.441 | section | Twenty-nine rock kinds | §52.441 | — | — | — | — | — | — | — | — | planned |
| S52.442 | section | Eleven strata beneath the ground | §52.442 | — | — | — | — | — | — | — | — | planned |
| S52.443 | section | Seven kinds of seal | §52.443 | — | — | — | — | — | — | — | — | planned |
| S52.444 | section | Ten causes of a river's change of course | §52.444 | — | — | — | — | — | — | — | — | planned |
| S52.445 | section | Ten sediment kinds and six carriers | §52.445 | — | — | — | — | — | — | — | — | planned |
| S52.446 | section | Thirteen coast forms | §52.446 | — | — | — | — | — | — | — | — | planned |
| S52.447 | section | Eight fossil sources, eight readings and eight preservations | §52.447 | — | — | — | — | — | — | — | — | planned |
| S52.448 | section | Twelve wind belts | §52.448 | — | — | — | — | — | — | — | — | planned |
| S52.449 | section | Six kinds of ocean current | §52.449 | — | — | — | — | — | — | — | — | planned |
| S52.450 | section | Five oscillation phases and eleven climate eras | §52.450 | — | — | — | — | — | — | — | — | planned |
| S52.451 | section | Seven planetary cycles | §52.451 | — | — | — | — | — | — | — | — | planned |
| S52.452 | section | Seven land-use rings and six market ranks | §52.452 | — | — | — | — | — | — | — | — | planned |
| S52.453 | section | Six hidden soil stocks | §52.453 | — | — | — | — | — | — | — | — | planned |
| S52.454 | section | Nine perennial kinds | §52.454 | — | — | — | — | — | — | — | — | planned |
| S52.455 | section | Twelve commons kinds and seven rules | §52.455 | — | — | — | — | — | — | — | — | planned |
| S52.456 | section | Ten catch grounds and twelve kinds of gear | §52.456 | — | — | — | — | — | — | — | — | planned |
| S52.457 | section | Twelve species classes and seven size classes | §52.457 | — | — | — | — | — | — | — | — | planned |
| S52.458 | section | Sixteen diets | §52.458 | — | — | — | — | — | — | — | — | planned |
| S52.459 | section | Eight social forms | §52.459 | — | — | — | — | — | — | — | — | planned |
| S52.460 | section | Nine biochemistries | §52.460 | — | — | — | — | — | — | — | — | planned |
| S52.461 | section | Eight domestication stages | §52.461 | — | — | — | — | — | — | — | — | planned |
| S52.462 | section | Fifteen species roles | §52.462 | — | — | — | — | — | — | — | — | planned |
| S52.463 | section | Fifteen plant forms, fifteen parts and nineteen products | §52.463 | — | — | — | — | — | — | — | — | planned |
| S52.464 | section | Eighteen heritable traits | §52.464 | — | — | — | — | — | — | — | — | planned |
| S52.465 | section | Six trophic levels and nine keystone roles | §52.465 | — | — | — | — | — | — | — | — | planned |
| S52.466 | section | Six kinds of symbiosis | §52.466 | — | — | — | — | — | — | — | — | planned |
| S52.467 | section | Thirteen senses | §52.467 | — | — | — | — | — | — | — | — | planned |
| S52.468 | section | Six dormancy states and five kinds of temperature regulation | §52.468 | — | — | — | — | — | — | — | — | planned |
| S52.469 | section | Nine plant defences | §52.469 | — | — | — | — | — | — | — | — | planned |
| S52.470 | section | Seven ferment cultures | §52.470 | — | — | — | — | — | — | — | — | planned |
| S52.471 | section | Nine resting states of carrion | §52.471 | — | — | — | — | — | — | — | — | planned |
| S52.472 | section | Twelve beast tempers and eleven temperaments | §52.472 | — | — | — | — | — | — | — | — | planned |
| S52.473 | section | Seventeen body materials | §52.473 | — | — | — | — | — | — | — | — | planned |
| S52.474 | section | Twelve deliveries and five ranges | §52.474 | — | — | — | — | — | — | — | — | planned |
| S52.475 | section | Nine habitats and nine aversions | §52.475 | — | — | — | — | — | — | — | — | planned |
| S52.476 | section | Eight awakening triggers | §52.476 | — | — | — | — | — | — | — | — | planned |
| S52.477 | section | Twenty-one beast product categories | §52.477 | — | — | — | — | — | — | — | — | planned |
| S52.478 | section | Seventeen kinds of knowledge | §52.478 | — | — | — | — | — | — | — | — | planned |
| S52.479 | section | Seventeen ways of passing | §52.479 | — | — | — | — | — | — | — | — | planned |
| S52.480 | section | Thirteen disease agents | §52.480 | — | — | — | — | — | — | — | — | planned |
| S52.481 | section | Fourteen cure classes | §52.481 | — | — | — | — | — | — | — | — | planned |
| S52.482 | section | Thirteen spread paths and fifteen plague responses | §52.482 | — | — | — | — | — | — | — | — | planned |
| S52.483 | section | Climate affinity on three axes | §52.483 | — | — | — | — | — | — | — | — | planned |
| S52.484 | section | Eighteen body plans, fifty-eight body parts and seventeen functions | §52.484 | — | — | — | — | — | — | — | — | planned |
| S52.485 | section | Twenty damage types and thirty injury kinds | §52.485 | — | — | — | — | — | — | — | — | planned |
| S52.486 | section | Nine injury states and thirty-one causes of harm | §52.486 | — | — | — | — | — | — | — | — | planned |
| S52.487 | section | Twenty-four conditions and thirteen maims | §52.487 | — | — | — | — | — | — | — | — | planned |
| S52.488 | section | Fifteen medicine tiers, fifteen treatment steps and twelve capacities | §52.488 | — | — | — | — | — | — | — | — | planned |
| S52.489 | section | Nine body systems and nine sensitivities | §52.489 | — | — | — | — | — | — | — | — | planned |
| S52.490 | section | Integration, catalogue and order (deepening pass, batches 1–10) | §52.490 | — | — | — | — | — | — | — | — | planned |
| S52.491 | section | Twenty effect package categories | §52.491 | — | — | — | — | — | — | — | — | planned |
| S52.492 | section | Four kinds of package visibility | §52.492 | — | — | — | — | — | — | — | — | planned |
| S52.493 | section | Twelve cure means | §52.493 | — | — | — | — | — | — | — | — | planned |
| S52.494 | section | Thirty-two emotions | §52.494 | — | — | — | — | — | — | — | — | planned |
| S52.495 | section | Seven grief stages and nine breaking points | §52.495 | — | — | — | — | — | — | — | — | planned |
| S52.496 | section | Twenty-seven value axes and thirty-six facets | §52.496 | — | — | — | — | — | — | — | — | planned |
| S52.497 | section | One hundred thirty-five personality traits and twenty-one moods | §52.497 | — | — | — | — | — | — | — | — | planned |
| S52.498 | section | Thirty needs in five groups | §52.498 | — | — | — | — | — | — | — | — | planned |
| S52.499 | section | Fifteen pressures | §52.499 | — | — | — | — | — | — | — | — | planned |
| S52.500 | section | Forty-three memories and one hundred sixty thoughts | §52.500 | — | — | — | — | — | — | — | — | planned |
| S52.501 | section | Eight inspirations and eight dream kinds | §52.501 | — | — | — | — | — | — | — | — | planned |
| S52.502 | section | Seven life stages and six readings of a death | §52.502 | — | — | — | — | — | — | — | — | planned |
| S52.503 | section | Sixty-nine skills and forty-six masteries | §52.503 | — | — | — | — | — | — | — | — | planned |
| S52.504 | section | Fifteen life paths and twenty-two life arcs | §52.504 | — | — | — | — | — | — | — | — | planned |
| S52.505 | section | Thirty-three causes of death | §52.505 | — | — | — | — | — | — | — | — | planned |
| S52.506 | section | Fourteen funeral customs | §52.506 | — | — | — | — | — | — | — | — | planned |
| S52.507 | section | Fourteen socialization techniques, nine pedagogies and ten youth purposes | §52.507 | — | — | — | — | — | — | — | — | planned |
| S52.508 | section | Twenty-four relation types and twenty-eight interactions | §52.508 | — | — | — | — | — | — | — | — | planned |
| S52.509 | section | Twelve circles and ten group kinds | §52.509 | — | — | — | — | — | — | — | — | planned |
| S52.510 | section | Sixteen passions, eight appeals and nine persuasion aims | §52.510 | — | — | — | — | — | — | — | — | planned |
| S52.511 | section | Eleven contests and eleven stakes | §52.511 | — | — | — | — | — | — | — | — | planned |
| S52.512 | section | Eight intimacy contexts, six stances, nine birth complications and seven postnatal customs | §52.512 | — | — | — | — | — | — | — | — | planned |
| S52.513 | section | Thirteen house duties and fourteen shares of time | §52.513 | — | — | — | — | — | — | — | — | planned |
| S52.514 | section | Thirty-five cooking methods and nine meal slots | §52.514 | — | — | — | — | — | — | — | — | planned |
| S52.515 | section | Eleven intoxicants and nine uses | §52.515 | — | — | — | — | — | — | — | — | planned |
| S52.516 | section | Nineteen leisure pursuits | §52.516 | — | — | — | — | — | — | — | — | planned |
| S52.517 | section | Nineteen biology variants | §52.517 | — | — | — | — | — | — | — | — | planned |
| S52.518 | section | Five honour models | §52.518 | — | — | — | — | — | — | — | — | planned |
| S52.519 | section | Sixty-five judged acts | §52.519 | — | — | — | — | — | — | — | — | planned |
| S52.520 | section | Thirteen reputation axes, six renown currencies and thirty-four punishments | §52.520 | — | — | — | — | — | — | — | — | planned |
| S52.521 | section | Senses, breath and pain by descent | §52.521 | — | — | — | — | — | — | — | — | planned |
| S52.522 | section | Nine inheritance customs, twenty-one kin roles and eleven household forms | §52.522 | — | — | — | — | — | — | — | — | planned |
| S52.523 | section | Eighteen dwelling kinds | §52.523 | — | — | — | — | — | — | — | — | planned |
| S52.524 | section | Six age bands, ten cohort conditions and nineteen kinds of work | §52.524 | — | — | — | — | — | — | — | — | planned |
| S52.525 | section | Nine mobility events, nineteen formative events and seventeen population instruments | §52.525 | — | — | — | — | — | — | — | — | planned |
| S52.526 | section | Fourteen identity layers and fifteen salience drivers | §52.526 | — | — | — | — | — | — | — | — | planned |
| S52.527 | section | Six ways of revival, six goals and fourteen movement causes | §52.527 | — | — | — | — | — | — | — | — | planned |
| S52.528 | section | Audit of values kept (batches 11–20) | §52.528 | — | — | — | — | — | — | — | — | planned |
| S52.529 | section | Integration, catalogue and order (deepening pass, batches 11–20) | §52.529 | — | — | — | — | — | — | — | — | planned |
| S52.530 | section | Corrections to earlier batches (D30–D35) | §52.530 | domain/enums/material.py; db/alembic/versions/3ca6d1cc6955_w52_material_names.py | n/a | n/a | material labels renamed | n/a | n/a | migration 3ca6d1cc6955 renames stored values | tests/unit/test_material_names.py::test_no_material_or_yield_is_named_with_an_imagery_word; tests/unit/test_spec_duplicates.py::test_the_specs_add_no_value_twice | done |
| S52.531 | section | Fifteen crowd acts, seven crowd feelings and nineteen triggers | §52.531 | — | — | — | — | — | — | — | — | planned |
| S52.532 | section | Twenty-three tradition functions, eight rite-of-passage stages and sixteen tradition effects | §52.532 | — | — | — | — | — | — | — | — | planned |
| S52.533 | section | Thirty-eight gathering kinds and eight death roles | §52.533 | — | — | — | — | — | — | — | — | planned |
| S52.534 | section | Twelve body marks, thirteen meanings, eight naming patterns, ten name forms and six age grades | §52.534 | — | — | — | — | — | — | — | — | planned |
| S52.535 | section | Sixteen gift occasions and nine gift states | §52.535 | — | — | — | — | — | — | — | — | planned |
| S52.536 | section | Nineteen art modes, nine market roles, eight forgeries, thirteen rights and nine ways of gaining one | §52.536 | — | — | — | — | — | — | — | — | planned |
| S52.537 | section | Eight kinds of club and enhancing contestants | §52.537 | — | — | — | — | — | — | — | — | planned |
| S52.538 | section | Eight numeral bases, twelve modalities and seven language stages | §52.538 | — | — | — | — | — | — | — | — | planned |
| S52.539 | section | Nine sense shifts, nine registers, seven script causes, sixteen media, seven policies, ten sociolects and six sign causes | §52.539 | — | — | — | — | — | — | — | — | planned |
| S52.540 | section | Fourteen kinds of account, eight stances, eight media | §52.540 | — | — | — | — | — | — | — | — | planned |
| S52.541 | section | Forty-eight materials and eleven origins | §52.541 | — | — | — | — | — | — | — | — | planned |
| S52.542 | section | Forty-seven goods, twenty-seven workshops and twenty-nine processes | §52.542 | — | — | — | — | — | — | — | — | planned |
| S52.543 | section | Seven pollutants, fourteen chemical products, nineteen extraction kinds and seventeen work hazards | §52.543 | — | — | — | — | — | — | — | — | planned |
| S52.544 | section | Seven credit states, eight loan states, six forms of saving, eight covers, five speculation states, four plays and eleven trade policies | §52.544 | — | — | — | — | — | — | — | — | planned |
| S52.545 | section | Eight route media, eight route states, nine losses, nine convoy states, twelve containers, ten aids, sixteen carriers and twelve cargo classes | §52.545 | — | — | — | — | — | — | — | — | planned |
| S52.546 | section | Audit of values kept (batches 21–30) | §52.546 | — | — | — | — | — | — | — | — | planned |
| S52.547 | section | Integration, catalogue and order (deepening pass, batches 21–30) | §52.547 | — | — | — | — | — | — | — | — | planned |
| S52.548 | section | Audit corrections to batches 31–40 (D36–D38) | §52.548 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | tests/unit/test_spec_duplicates.py::test_a_value_named_with_a_bias_word_is_caught | done |
| S52.549 | section | Eleven reasons for labour allocation and thirteen shortfalls | §52.549 | — | — | — | — | — | — | — | — | planned |
| S52.550 | section | Twenty-seven district kinds, eleven zones, thirteen housing levels and twenty-three services | §52.550 | — | — | — | — | — | — | — | — | planned |
| S52.551 | section | Ten causes of rebuilding, five ways, nine kinds of relief, eleven aid kinds and fourteen preparedness measures | §52.551 | — | — | — | — | — | — | — | — | planned |
| S52.552 | section | Eight construction states, six collections, ten pieces, eleven gardens and eight water lifts | §52.552 | — | — | — | — | — | — | — | — | planned |
| S52.553 | section | Twenty-nine building forms, nine builders and forty-five sections | §52.553 | — | — | — | — | — | — | — | — | planned |
| S52.554 | section | Six relic stances, eight aids, nine clocks, eight locks and twenty curse kinds | §52.554 | — | — | — | — | — | — | — | — | planned |
| S52.555 | section | Eight criminal organisations, five state stances, eight fugitives, eight sanctuaries and fifteen rackets | §52.555 | — | — | — | — | — | — | — | — | planned |
| S52.556 | section | Eleven council tasks, twelve mandates, nine crisis demands and ten court positions | §52.556 | — | — | — | — | — | — | — | — | planned |
| S52.557 | section | Twenty-three offices, fourteen office powers and eighteen taxes | §52.557 | — | — | — | — | — | — | — | — | planned |
| S52.558 | section | Eight client roles, ten member rights, nine ways of naturalisation, seven legitimacy types and six memberships | §52.558 | — | — | — | — | — | — | — | — | planned |
| S52.559 | section | Eleven title tiers, nine claim bases, ten succession rules and thirteen long plans | §52.559 | — | — | — | — | — | — | — | — | planned |
| S52.560 | section | Fourteen areas of law, eight court levels, ten kinds of evidence, fourteen oaths and fifteen registry kinds | §52.560 | — | — | — | — | — | — | — | — | planned |
| S52.561 | section | Sixteen faction goals, nineteen actions, nine privileges and ten cooperative purposes | §52.561 | — | — | — | — | — | — | — | — | planned |
| S52.562 | section | Audit of values kept (batches 31–40) | §52.562 | — | — | — | — | — | — | — | — | planned |
| S52.563 | section | Integration, catalogue and order (deepening pass, batches 31–40) | §52.563 | — | — | — | — | — | — | — | — | planned |
| S52.564 | section | Six party roles, eight treaty states, six crisis states, six standings and nine council resolutions | §52.564 | — | — | — | — | — | — | — | — | planned |
| S52.565 | section | Seventeen treaty kinds and twenty-nine clauses | §52.565 | — | — | — | — | — | — | — | — | planned |
| S52.566 | section | Fourteen challenges and four responses | §52.566 | — | — | — | — | — | — | — | — | planned |
| S52.567 | section | Thirteen kinds of message, eight states, seven envoy fates, six signal states and nine subjects of opinion | §52.567 | — | — | — | — | — | — | — | — | planned |
| S52.568 | section | Twelve media and nine signal kinds | §52.568 | — | — | — | — | — | — | — | — | planned |
| S52.569 | section | Six prices of knowledge, five kinds of claim, five claim states and fifteen belief sources | §52.569 | — | — | — | — | — | — | — | — | planned |
| S52.570 | section | Twenty secrets, ten hook demands, eleven favour origins, nine identity reasons, seven hook sources and twenty-two plot kinds | §52.570 | — | — | — | — | — | — | — | — | planned |
| S52.571 | section | Twelve spy operations, seven motives, eight agent states and fourteen sabotage kinds | §52.571 | — | — | — | — | — | — | — | — | planned |
| S52.572 | section | Eleven army stances, ten roles, nine honours, six grants, thirteen formations and six command areas | §52.572 | — | — | — | — | — | — | — | — | planned |
| S52.573 | section | Twenty-nine commander traits, five contract states and six mutiny outcomes | §52.573 | — | — | — | — | — | — | — | — | planned |
| S52.574 | section | Seven casualty fates, ten captive fates, twelve battle phases and twenty-five tactics | §52.574 | — | — | — | — | — | — | — | — | planned |
| S52.575 | section | Eight siege actions, fourteen siege works, nine defender actions, six choices after a fall, six siege states and five starvation stages | §52.575 | — | — | — | — | — | — | — | — | planned |
| S52.576 | section | Audit of values kept (batches 41–50) | §52.576 | — | — | — | — | — | — | — | — | planned |
| S52.577 | section | Integration, catalogue and order (deepening pass, batches 41–50) | §52.577 | — | — | — | — | — | — | — | — | planned |
| S52.578 | section | Six echelons, six echelon orders, seventeen war aims, twelve grounds for war and thirty war causes | §52.578 | — | — | — | — | — | — | — | — | planned |
| S52.579 | section | Nineteen peace terms, eleven war endings and seven field agreements | §52.579 | — | — | — | — | — | — | — | — | planned |
| S52.580 | section | Twenty-six vehicle families, nineteen propulsion kinds, fifty-seven sections and twelve shot kinds | §52.580 | — | — | — | — | — | — | — | — | planned |
| S52.581 | section | Seven duel contexts and nine duel endings | §52.581 | — | — | — | — | — | — | — | — | planned |
| S52.582 | section | Eleven captive states, twelve feud actions and eight feud states | §52.582 | — | — | — | — | — | — | — | — | planned |
| S52.583 | section | Ten holdings and twelve kinds of zeal | §52.583 | — | — | — | — | — | — | — | — | planned |
| S52.584 | section | Seven kinds of vision, eight causes of a god's silence, eight sacraments, five protections and seven mystic states | §52.584 | — | — | — | — | — | — | — | — | planned |
| S52.585 | section | Five rebirth paths, nine afterlife models, six judgement doctrines and ten bindings | §52.585 | — | — | — | — | — | — | — | — | planned |
| S52.586 | section | Twenty place spirits, eight offences and eleven petitions | §52.586 | — | — | — | — | — | — | — | — | planned |
| S52.587 | section | Ten luck signs, ten reaches, eight charm powers and eight accusation outcomes | §52.587 | — | — | — | — | — | — | — | — | planned |
| S52.588 | section | Thirty-three mishaps, fifteen attributions and nine responses | §52.588 | — | — | — | — | — | — | — | — | planned |
| S52.589 | section | Eleven kinds of divination, ten questions and five foresight sources | §52.589 | — | — | — | — | — | — | — | — | planned |
| S52.590 | section | Audit of values kept (batches 51–60) | §52.590 | — | — | — | — | — | — | — | — | planned |
| S52.591 | section | Integration, catalogue and order (deepening pass, batches 51–60) | §52.591 | — | — | — | — | — | — | — | — | planned |
| S52.592 | section | Thirteen spell techniques, twenty-three forms and nine rite components | §52.592 | — | — | — | — | — | — | — | — | planned |
| S52.593 | section | Twelve restrictions and eleven resistances | §52.593 | — | — | — | — | — | — | — | — | planned |
| S52.594 | section | Seven ranges, seven durations, nine targets and eight ways of recharging | §52.594 | — | — | — | — | — | — | — | — | planned |
| S52.595 | section | Ten link tokens and eleven power hazards | §52.595 | — | — | — | — | — | — | — | — | planned |
| S52.596 | section | Eight quest trials, six geas layers, three geas modes, ten boons and three creature lessons | §52.596 | — | — | — | — | — | — | — | — | planned |
| S52.597 | section | Eighteen kinds of order, nine conditions, eight command tokens and nine bindings | §52.597 | — | — | — | — | — | — | — | — | planned |
| S52.598 | section | Five modes of worship, six prayer tones and eleven divine wounds | §52.598 | — | — | — | — | — | — | — | — | planned |
| S52.599 | section | Seven manifestations, eight divine scales, eight magic sites, eleven creature deeds and four belief stances | §52.599 | — | — | — | — | — | — | — | — | planned |
| S52.600 | section | Ten causes of divine wounds, eight council penalties, seven servitor origins and thirteen servitor roles | §52.600 | — | — | — | — | — | — | — | — | planned |
| S52.601 | section | Twenty-eight council motions, twelve office duties and five ways of gaining office | §52.601 | — | — | — | — | — | — | — | — | planned |
| S52.602 | section | Thirteen transformation triggers and six mantling states | §52.602 | — | — | — | — | — | — | — | — | planned |
| S52.603 | section | Audit of values kept (batches 61–70) | §52.603 | — | — | — | — | — | — | — | — | planned |
| S52.604 | section | Integration, catalogue and order (deepening pass, batches 61–70) | §52.604 | — | — | — | — | — | — | — | — | planned |
| S52.605 | section | Eight exemptions from natural laws and five law scopes | §52.605 | — | — | — | — | — | — | — | — | planned |
| S52.606 | section | Ten creator passions, five mood axes and sixteen creator signs | §52.606 | — | — | — | — | — | — | — | — | planned |
| S52.607 | section | Seven gains, seven prices and seven hungers of the outer dark | §52.607 | — | — | — | — | — | — | — | — | planned |
| S52.608 | section | Eight life environments and seven air needs | §52.608 | — | — | — | — | — | — | — | — | planned |
| S52.609 | section | Thirty-seven world types, nine cosmic features and seven atmospheres | §52.609 | — | — | — | — | — | — | — | — | planned |
| S52.610 | section | Seven impacting bodies and seven impact outcomes | §52.610 | — | — | — | — | — | — | — | — | planned |
| S52.611 | section | Eleven ends of worlds, twelve causes, fourteen land acts and eleven terraforming aims | §52.611 | — | — | — | — | — | — | — | — | planned |
| S52.612 | section | Thirteen ways of settling, nine grounds of war, ten light sources and eight needs to live | §52.612 | — | — | — | — | — | — | — | — | planned |
| S52.613 | section | A rhythm for phenomena | §52.613 | — | — | — | — | — | — | — | — | planned |
| S52.614 | section | Ten journey intents, twelve vehicle kinds, twelve route states and seven survey levels | §52.614 | — | — | — | — | — | — | — | — | planned |
| S52.615 | section | Ten kinds of prehistory and three forms of the cosmos | §52.615 | — | — | — | — | — | — | — | — | planned |
| S52.616 | section | Audit of values kept (batches 71–80) | §52.616 | — | — | — | — | — | — | — | — | planned |
| S52.617 | section | Integration, catalogue and order (deepening pass, batches 71–80) | §52.617 | — | — | — | — | — | — | — | — | planned |
| S52.618 | section | Twenty-three knowledge branches, one hundred seven techniques and fourteen tech families | §52.618 | — | — | — | — | — | — | — | — | planned |
| S52.619 | section | Ten kinds of age, fifteen era deeds, ten research incidents, eleven blueprint kinds and six sources | §52.619 | — | — | — | — | — | — | — | — | planned |
| S52.620 | section | Eleven fields of great persons | §52.620 | — | — | — | — | — | — | — | — | planned |
| S52.621 | section | Four numeral notations, ten theory domains and six kinds of anomaly | §52.621 | — | — | — | — | — | — | — | — | planned |
| S52.622 | section | Thirteen technology eras, nineteen era channels and six programme stages | §52.622 | — | — | — | — | — | — | — | — | planned |
| S52.623 | section | Eight storyteller profiles, nine arc roles and seven setups | §52.623 | — | — | — | — | — | — | — | — | planned |
| S52.624 | section | Ten expedition roles, seven grounds, twelve states of resolve, sixteen quirks and fourteen events | §52.624 | — | — | — | — | — | — | — | — | planned |
| S52.625 | section | Seventeen room kinds, seven challenges, eight contents, seven digging risks, nine finds and five battlefield features | §52.625 | — | — | — | — | — | — | — | — | planned |
| S52.626 | section | Seventeen cosmic beings | §52.626 | — | — | — | — | — | — | — | — | planned |
| S52.627 | section | Ten kinds of upkeep, twelve will causes, five making outcomes, twelve realm purposes and six stances toward made minds | §52.627 | — | — | — | — | — | — | — | — | planned |
| S52.628 | section | Four augment makes, six effect targets and six host placements | §52.628 | — | — | — | — | — | — | — | — | planned |
| S52.629 | section | Eight carriers, six network roles, twelve outage causes, ten intrusion targets, seven aims, four outcomes and eight data contents | §52.629 | — | — | — | — | — | — | — | — | planned |
| S52.630 | section | Five company charters and nine holdings | §52.630 | — | — | — | — | — | — | — | — | planned |
| S52.631 | section | Eight replicator outputs, eight ways of allocation, five relic states and seven relic uses | §52.631 | — | — | — | — | — | — | — | — | planned |
| S52.632 | section | Audit of values kept (batches 81–90) | §52.632 | — | — | — | — | — | — | — | — | planned |
| S52.633 | section | Integration, catalogue and order (deepening pass, batches 81–90) | §52.633 | — | — | — | — | — | — | — | — | planned |
| S52.634 | section | Twelve power origins, seventeen sources, eight states and nine triggers | §52.634 | — | — | — | — | — | — | — | — | planned |
| S52.635 | section | Twenty-three costs, thirteen restrictions, nine device effects, eight ways of access and eleven ways of renewal | §52.635 | — | — | — | — | — | — | — | — | planned |
| S52.636 | section | Six stances, seven attitudes, five legal levels and five bloodline rules for the gifted | §52.636 | — | — | — | — | — | — | — | — | planned |
| S52.637 | section | Eleven kinds of hidden truth, eight scopes and six keeper roles | §52.637 | — | — | — | — | — | — | — | — | planned |
| S52.638 | section | Eight keeper responses, six seeker aims, twelve breach causes and nine attitudes to a truth | §52.638 | — | — | — | — | — | — | — | — | planned |
| S52.639 | section | Eleven methods of living craft, twenty-three line traits, eight metabolisms, five kinds of fertility and seven line outcomes | §52.639 | — | — | — | — | — | — | — | — | planned |
| S52.640 | section | Audit of values kept (batches 91–93) | §52.640 | — | — | — | — | — | — | — | — | planned |
| S52.641 | section | Integration, catalogue and order (deepening pass, batches 91–93) | §52.641 | — | — | — | — | — | — | — | — | planned |
| S52.642 | section | Sixty-one good categories | §52.642 | — | — | — | — | — | — | — | — | planned |
| S52.643 | section | Fourteen money forms and seven backings | §52.643 | — | — | — | — | — | — | — | — | planned |
| S52.644 | section | Twelve ingredient roles, twelve flavour axes and fourteen drink categories | §52.644 | — | — | — | — | — | — | — | — | planned |
| S52.645 | section | Twenty garment categories and ten colour meanings | §52.645 | — | — | — | — | — | — | — | — | planned |
| S52.646 | section | Fourteen furnishing categories, nine instrument categories and fifteen game categories | §52.646 | — | — | — | — | — | — | — | — | planned |
| S52.647 | section | Sixteen kinds of instrument in a step, seventeen loci and thirty-five step states | §52.647 | — | — | — | — | — | — | — | — | planned |
| S52.648 | section | Five witness modes and twelve rumour distortions | §52.648 | — | — | — | — | — | — | — | — | planned |
| S52.649 | section | Twelve record forms, eleven kinds of media item and six satire sources | §52.649 | — | — | — | — | — | — | — | — | planned |
| S52.650 | section | Ten humour forms, nine speech venues and nine speech aims | §52.650 | — | — | — | — | — | — | — | — | planned |
| S52.651 | section | Twenty kinds of public works, eight forms of state enterprise and eleven endowment purposes | §52.651 | — | — | — | — | — | — | — | — | planned |
| S52.652 | section | Five supply tiers | §52.652 | — | — | — | — | — | — | — | — | planned |
| S52.653 | section | Eight kinds of space weather | §52.653 | — | — | — | — | — | — | — | — | planned |
| S52.654 | section | Nine tolerances of each body system and five ways past the body's limits | §52.654 | — | — | — | — | — | — | — | — | planned |
| S52.655 | section | Eight methods of working the weather and seven aims | §52.655 | — | — | — | — | — | — | — | — | planned |
| S52.656 | section | Eleven methods of observation | §52.656 | — | — | — | — | — | — | — | — | planned |
| S52.657 | section | Seven causes of a local climate | §52.657 | — | — | — | — | — | — | — | — | planned |
| S52.658 | section | Audit of values kept (batches 94–99) | §52.658 | — | — | — | — | — | — | — | — | planned |
| S52.659 | section | Integration, catalogue and order (batches 94–99) | §52.659 | — | — | — | — | — | — | — | — | planned |
| S52.660 | section | Order of work | §52.660 | — | — | — | — | — | — | — | — | planned |
| S52.661 | section | Guards of W52 | §52.661 | — | — | — | — | — | — | — | — | planned |
| S52.662 | section | Acceptance of W52 | §52.662 | — | — | — | — | — | — | — | — | planned |
| F72 | foundation | Cells of the deep and one layered graph | §F72 | — | — | — | — | — | — | — | — | planned |
| S52.663 | section | Six strata named, and every stratum a cell | §52.663 | — | — | — | — | — | — | — | — | planned |
| S52.664 | section | Passages of the deep | §52.664 | — | — | — | — | — | — | — | — | planned |
| S52.665 | section | Dwelling below | §52.665 | — | — | — | — | — | — | — | — | planned |
| S52.666 | section | Moving, trading and fighting through the deep | §52.666 | — | — | — | — | — | — | — | — | planned |
| S52.667 | section | The map of the deep | §52.667 | — | — | — | — | — | — | — | — | planned |
| S52.668 | section | Integration, guards, catalogue and order (batch 100) | §52.668 | — | — | — | — | — | — | — | — | planned |
| K.121 | decision | Is a cell a node of its own? | Part K | — | — | — | — | — | — | — | — | planned |
| K.122 | decision | May a passage join two different regions at two different depths? | Part K | — | — | — | — | — | — | — | — | planned |
| K.123 | decision | Is settling below limited by biology? | Part K | — | — | — | — | — | — | — | — | planned |
| K.124 | decision | Does the map replace the "Beneath" panel? | Part K | — | — | — | — | — | — | — | — | planned |
