# Depth expansion coverage matrix

Traceability matrix for `docs/spec/13-depth-expansion.md` (spec J.19). Generated and checked by `scripts/spec_coverage.py`.
Every numbered item of the spec has one row.
A row is `done` only when every work column is filled (or `n/a` where it does not apply) and its test passes.
`deferred-approved` requires the user's explicit approval and a reason in the Test column.
Gap rows (kind `gap`) are done when every section they point to is done.
Run `python scripts/spec_coverage.py write` after editing the spec, and `python scripts/spec_coverage.py check` to verify.

| ID | Kind | Title | Spec | Module | Trigger | Lever | UI | LLM | Templates | Backfill | Test | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G1 | ground-rule | No magic numbers (architecture rule 4) | Part 0 | rules/registry/* (every tunable a rule) | test-time | World Rules editor | WorldRules | n/a | n/a | n/a | tests/unit/test_rule_registry.py (every key read) | done |
| G2 | ground-rule | Explicit fields, never prose detection (decision 40) | Part 0 | typed enums and tools replace prose readers in every engine path: star placement from the typed star and star_id, resource yields from a required typed commodity (son and mortal tools, awakening, revelation, world birth, cosmic deposits, trails), structure kinds from the typed kind or engine_kind, resource and law workings from the typed choice or a seeded die, durable artworks from the typed medium, vessel image direction from VehicleKind; prose is read only inside recorded one-time fixups (law kinds, depth traits, plague history, species plans, economy and structure backfills, resource profiles) | every creation path and every engine phase; fixups once on the first epoch after upgrade | n/a | n/a | typed tool inputs | n/a | one-time fixups | tests/engine/port_structure/test_mechanics_assignment.py, tests/engine/port_structure/test_economy_depth.py (resource words read once), tests/engine/core/test_structures.py (typed after the fixup), tests/engine/cosmos/test_worlds.py (prose never picks a star), tests/unit/test_mechanic_compliance.py | done |
| G3 | ground-rule | Determinism (decision 37) | Part 0 | engine/primitives/random seeded streams; per-battle and per-phase streams | every phase | n/a | n/a | n/a | n/a | n/a | tests/engine/integration/test_determinism.py (20-epoch DB hash) | done |
| G4 | ground-rule | Every mechanic is automatic, player-overridable and has a UI surface (architecture rule 6) | Part 0 | db/profile_guard.py, services/player/* create/edit/hold/release/delete levers | every guarded phase honours holds | profile:set/release, lever:pin/suppress, per-domain levers | summary-first sections with Adjust panels in every domain | son tools per domain | n/a | n/a | tests/engine/interconnect/test_profile_guard.py, tests/services/player/*, test_mechanic_compliance.py | done |
| G5 | ground-rule | Engine phases are `async def phase(ctx)` units with no transaction across an await (decisions 23, 72, 75) | Part 0 | engine/pipeline.py Phase units | every tick | n/a | n/a | n/a | n/a | n/a | tests/engine/core/test_wiring.py | done |
| G6 | ground-rule | LLM reads structured state | Part 0 | agents/context/* typed blocks (society, realm, military, lore, wilds, economy, son_faith) | every agent turn | n/a | n/a | typed context blocks | n/a | n/a | tests/agents/*, tests/prompts/* | done |
| G7 | ground-rule | Typed rows over JSON for anything the engine queries (spec 01 §14) | Part 0 | typed tables for every engine-queried value (profiles, ranges, feuds, rumours, structures...) | every phase reads typed rows | n/a | n/a | n/a | n/a | alembic migrations | tests/db/test_schema.py | done |
| G8 | ground-rule | Prose fields stay | Part 0 | prose fields kept beside typed fields; deepener writes prose from typed fields | deepening | n/a | entity drawer prose | prompts/data/deepening.py | n/a | n/a | tests/prompts/* | done |
| G9 | ground-rule | Plain narration of harm, behind closed doors (decisions K.3, K.9) | Part 0 | prompts/templates/shared/_harm_narration.md.j2 included by every narrative prompt | every narrative call | n/a | n/a | shared harm block | n/a | n/a | tests/prompts/test_catalog.py | done |
| G10 | ground-rule | As if it had always been so (decision K.2) | Part 0 | fixups per domain (AppliedFixupRow) and table_backfills.py | first epoch after upgrade | n/a | n/a | n/a | n/a | per-domain fixups | tests/unit/test_mechanic_compliance.py (per-table backfill) | done |
| G11 | ground-rule | Mechanical harshness is one dial (decision K.19) | Part 0 | engine/primitives/harshness.py, rules/registry/harshness.py | wounds, infection, disease, famine, battle, childbirth | harshness.profile rule | world-rules/HarshnessDial.tsx | n/a | n/a | n/a | tests/engine/body/test_mortal_life.py | done |
| S0.1 | section | Notation | §0.1 | — | — | — | — | — | — | — | — | planned |
| S0.2 | section | Depth metric | §0.2 | — | — | — | — | — | — | — | — | planned |
| G1R.3.1 | gap | Layered geology per region (soil, sedimentary, igneous, metamorphic layers), specific stone types | §1R.3 | → S6.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.2 | gap | Aquifers, cavern layers, an underground sea of magma, a deep underworld | §1R.3 | → S6.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.3 | gap | Hydrology: rivers with flow, brooks, lakes, salinity, flooding of low ground | §1R.3 | → S6.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.4 | gap | Temperature physics: melting, boiling, ignition points; fire spread by material | §1R.3 | → F23 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.5 | gap | Plants as species with seasons, soil needs and products (fibre, dye, brew, herb, alchemy) | §1R.3 | → S3.2/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.6 | gap | Good/evil and savagery alignment of regions (haunted, reanimating, blessed lands) | §1R.3 | → S6.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.7 | gap | Syndromes: a generic effect system carried by materials, creatures, gases, bites and interactions | §1R.3 | → F30 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.8 | gap | Procedurally generated monsters (random anatomy, materials, breath, temperament) | §1R.3 | → S3.3a/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.9 | gap | Night creatures, werebeast and vampire curses spread by bite or desecration | §1R.3 | → F30, S3.3a/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.10 | gap | Tissue layers (skin, fat, muscle, bone, nerve, artery), bleeding, motor and sensory nerve loss, internal organs, teeth and digits | §1R.3 | → F23 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.11 | gap | Pain, nausea, dizziness, unconsciousness, exhaustion, bleeding out | §1R.3 | → F23 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.12 | gap | Per-attack physics: momentum, contact area, edge, material yield, layered armour | §1R.3 | → F23, S5.6/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.13 | gap | Wrestling: grabs, throws, chokes, joint locks; dodging, parrying, blocking | §1R.3 | → S5.6/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.14 | gap | 19 physical and mental attributes | §1R.3 | → F13 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.15 | gap | About 50 personality facets independent of beliefs | §1R.3 | → F13 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.16 | gap | Beliefs/values (about 30) | §1R.3 | → F13 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.17 | gap | Thoughts and emotions with intensity; short- and long-term memories that change personality over time | §1R.3 | → F14 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.18 | gap | About 30 individual needs (pray, fight, learn, craft, be with family, drink) | §1R.3 | → F14 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.19 | gap | Life dreams (create a masterwork, rule, raise a family) | §1R.3 | → F17 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.20 | gap | Preferences: liked materials, foods, creatures, colours, shapes, art forms | §1R.3 | → F15 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.21 | gap | Friendships, grudges, lovers, acquaintances with strength and history | §1R.3 | → F18 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.22 | gap | Skill rust from disuse, learning by demonstration and sparring, teaching | §1R.3 | → F6/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | done |
| G1R.3.23 | gap | Quality grades, decorations (encrusted, studded), engravings that depict historical events, maker's marks | §1R.3 | → S7.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.24 | gap | Strange moods: compulsions to make an artifact; failure leads to madness | §1R.3 | → F17, S7.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.25 | gap | Musical, poetic and dance forms generated per culture | §1R.3 | → S7.5 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.26 | gap | Performance troupes, scholars writing books on specific topics | §1R.3 | → S7.4/RP2, S8.4/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.27 | gap | Ethics per civilisation (killing, theft, slavery, torture, eating sapients…) with levels | §1R.3 | → F16 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.28 | gap | Food preparation, brewing, spoilage, vermin in stores, alcohol need | §1R.3 | → S6.3/RP2, F24 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.29 | gap | Hospital work: diagnosis, setting bones, suturing, dressing, crutches, traction | §1R.3 | → F23, S7.2/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.30 | gap | Justice: crimes with witnesses, investigations, interrogation, sentences | §1R.3 | → S4.5/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.31 | gap | Nobles' demands (room quality) and mandates (production orders, export bans) | §1R.3 | → S4.6/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.32 | gap | Room and dwelling quality affecting thoughts | §1R.3 | → F29 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.33 | gap | Ammunition, training injuries, uniforms, patrol routes | §1R.3 | → S5.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.34 | gap | Pets bonded to owners, grazing, milking, shearing, eggs, butchery | §1R.3 | → S3.2/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.35 | gap | Every person in history is a historical figure with a full event log | §1R.3 | → F10/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.36 | gap | Event collections: abductions, beast attacks, persecutions, purges, insurrections, competitions, performances, processions, ceremonies | §1R.3 | → F10/RP2, F25 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.37 | gap | Abductions of children raised as soldiers, necromancer towers raising undead, vampires infiltrating with false identities | §1R.3 | → F20, S8.6/RP2, S5.7/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.38 | gap | Deity spheres (about 130) with compatible and precluded pairs | §1R.3 | → S9.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.39 | gap | Desecration curses from gods | §1R.3 | → S9.1/RP2, F30 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.40 | gap | Ghosts of the unburied with types, put to rest by memorials | §1R.3 | → S3.3/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.41 | gap | Per-site reputation of a character (hero, monster slayer, troublemaker) | §1R.3 | → F19 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.42 | gap | Sites with structure: towers, vaults, lairs, hamlets, monasteries, camps, with ownership history | §1R.3 | → S6.2/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.43 | gap | Cave-ins and structural support in mines | §1R.3 | → S6.3/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.44 | gap | Sleep, fatigue, thirst, cleanliness (as aggregates at epoch scale) | §1R.3 | → F14 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.3.45 | gap | Language translation of names: every name has a meaning in its language | §1R.3 | → S8.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.4.1 | gap | Orbital elements: semi-major axis, eccentricity, inclination, period, resonance | §1R.4 | → S10.9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.4.2 | gap | Year length, seasons and insolation derived from orbit, star mass and luminosity | §1R.4 | → S10.9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.4.3 | gap | Planet mass, radius, density, composition (iron, rock, ice, gas fractions) | §1R.4 | → S10.9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.4.4 | gap | Surface temperature from luminosity, albedo and greenhouse effect | §1R.4 | → S10.9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.4.5 | gap | Atmosphere composition and pressure (oxygen, nitrogen, carbon dioxide, methane, exotic) | §1R.4 | → S10.9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.4.6 | gap | Magnetosphere and radiation shielding | §1R.4 | → S10.9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.4.7 | gap | Tectonics, volcanism and their cycles | §1R.4 | → S10.9, S6.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.4.8 | gap | Hydrosphere and cryosphere fractions; sea level change | §1R.4 | → S10.9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.4.9 | gap | Stellar evolution by mass, with lifetimes (main sequence, giant, dwarf, neutron star, black hole) | §1R.4 | → S10.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.4.10 | gap | Binary and multiple stars, circumbinary orbits, double sunsets and seasons | §1R.4 | → S10.9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.4.11 | gap | Habitable zone computed per system | §1R.4 | → S10.9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.4.12 | gap | Impacts (asteroids, comets) with craters, impact winters, extinctions | §1R.4 | → S10.9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.4.13 | gap | Rings, Roche limit, tidal locking computed, tidal heating of moons | §1R.4 | → S10.9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.4.14 | gap | Galactic structure: arms, clusters, nebulae, stellar nurseries, voids | §1R.4 | → S10.9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.4.15 | gap | Periodic comets with orbits and return epochs | §1R.4 | → S10.3/RP2, S10.9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.4.16 | gap | Biochemistry class of life per world (carbon/water, silicon, ammonia, exotic) | §1R.4 | → S10.9, S3.2/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.4.17 | gap | Habitability per species per climate class | §1R.4 | → S4.1/RP2, S10.9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.4.18 | gap | Terraforming over epochs | §1R.4 | → S10.9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.4.19 | gap | Megastructures (star-scale works) | §1R.4 | → S7.2/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.4.20 | gap | Space fauna (void leviathans) with migrations | §1R.4 | → S3.3a/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.4.21 | gap | Anomalies and multi-stage archaeological sites of precursors | §1R.4 | → S6.2/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.4.22 | gap | Fuel, supply and jump range per vessel | §1R.4 | → S7.3/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.4.23 | gap | Survey levels per world per observer (detected, surveyed, mapped) | §1R.4 | → S10.2/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.4.24 | gap | Galactic assembly with resolutions | §1R.4 | → S4.6/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.4.25 | gap | Light-delay of news between worlds | §1R.4 | → F21 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.4.26 | gap | Rogue planets and wandering bodies | §1R.4 | → S10.9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.4.27 | gap | Aurorae, eclipses, transits computed from geometry | §1R.4 | → S10.9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.1 | gap | Organisation versus strength: units lose cohesion before they lose men | §1R.5 | → S5.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.2 | gap | Morale state ladder (steady, shaken, wavering, routing, broken, rallied) and suppression | §1R.5 | → S5.3/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.3 | gap | Frontage and combat width set by terrain; formations and facing | §1R.5 | → S5.3/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.4 | gap | Reserves, second lines, reinforcement during battle | §1R.5 | → S5.3/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.5 | gap | Command and control: span of control, order delay, misunderstood orders, initiative | §1R.5 | → S5.3/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.6 | gap | Spotting, line of sight, elevation, concealment | §1R.5 | → S5.3/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.7 | gap | Ammunition per stack and resupply | §1R.5 | → S5.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.8 | gap | Fatigue and stamina within battle; forced marches | §1R.5 | → S5.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.9 | gap | Supply limit per region (how many soldiers the land can feed) | §1R.5 | → S5.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.10 | gap | Zones of control, forts controlling movement, encirclement | §1R.5 | → S5.4/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.11 | gap | Entrenchment and field fortifications built over seasons | §1R.5 | → S5.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.12 | gap | Planning bonus for prepared attacks | §1R.5 | → S5.3/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.13 | gap | Armour penetration versus armour value; hard and soft targets | §1R.5 | → F23, S5.3/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.14 | gap | Leader skills by area (fire, shock, manoeuvre, siege) and battle-earned traits | §1R.5 | → S5.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.15 | gap | Death of a general shocks morale; standards captured | §1R.5 | → S5.3/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.16 | gap | Casualty classes: killed, wounded, captured, missing, deserted | §1R.5 | → S5.3/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.17 | gap | Field surgeons and evacuation change wounded survival | §1R.5 | → S5.3/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.18 | gap | Combat engineering: pontoons, roads, demolitions | §1R.5 | → S5.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.19 | gap | Discipline as a separate stat from experience | §1R.5 | → S5.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.20 | gap | Weapon range, rate of fire, accuracy | §1R.5 | → S5.3/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.21 | gap | Deception: feints, false camps, misinformation | §1R.5 | → S5.3/RP2, F22 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.22 | gap | Siege phases with garrison, artillery breach, blockade by sea | §1R.5 | → S5.4/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.23 | gap | Naval: ship classes, weather gauge, boarding, naval supremacy for crossings, amphibious landing penalty | §1R.5 | → S5.5/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.24 | gap | Air superiority over regions (here: flying mounts and skyships) | §1R.5 | → S5.5/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.25 | gap | Equipment capture and battlefield salvage | §1R.5 | → S5.3/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.26 | gap | Production lines for war materiel with efficiency growth | §1R.5 | → S5.8/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.27 | gap | War support and home-front stability | §1R.5 | → S5.8/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.28 | gap | Peace conference where each demand costs war score | §1R.5 | → S5.8/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.29 | gap | Casus belli types and justification time | §1R.5 | → S5.8/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.30 | gap | Coalitions against aggressive expansion | §1R.5 | → S4.6/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.31 | gap | Division templates (standard compositions) | §1R.5 | → S5.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.32 | gap | Directional blocking and couched charges in single combat; mounted momentum | §1R.5 | → S5.6/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.33 | gap | Terrain micro-features (ditches, walls, woods edges) | §1R.5 | → S5.3/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.34 | gap | Time of day and night fighting | §1R.5 | → S5.3/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.5.35 | gap | Psychological warfare: terror, propaganda, atrocity backlash | §1R.5 | → S5.8/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.6.1 | gap | Alternative production methods for the same good | §1R.6 | → F24 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.6.2 | gap | Wages per job and standard of living per class | §1R.6 | → S4.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.6.3 | gap | Ownership of workplaces (nobles, guilds, state, cult, households) and profit distribution | §1R.6 | → S6.3/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.6.4 | gap | Investment pools and construction capacity | §1R.6 | → S4.2/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | done |
| G1R.6.5 | gap | Market access: share of output that reaches a market | §1R.6 | → S6.4/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.6.6 | gap | Tariffs, subsidies, embargoes | §1R.6 | → S6.4/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.6.7 | gap | Substitution between goods (fuel: wood or coal; food types) | §1R.6 | → F24 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.6.8 | gap | Tiered population needs that unlock upgrades (Anno-style) | §1R.6 | → S4.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.6.9 | gap | Class promotion when needs are met | §1R.6 | → S4.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.6.10 | gap | Quality tiers of goods | §1R.6 | → F24 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.6.11 | gap | Storage, spoilage, perishables, preservation | §1R.6 | → S6.3/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.6.12 | gap | Energy sources (muscle, water, wind, magic, divine) | §1R.6 | → F24 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.6.13 | gap | Pollution and its health effects | §1R.6 | → F24 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.6.14 | gap | Interest rates, credit ratings, bankruptcy states, reserves | §1R.6 | → S6.4/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.6.15 | gap | Boom and bust cycles; speculation; hoarding during famine | §1R.6 | → S6.4/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.6.16 | gap | Economic indicators (output, price index, trade balance) | §1R.6 | → S6.4/RP2, J.9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.6.17 | gap | Black markets for illegal goods | §1R.6 | → S6.4/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.6.18 | gap | Unemployment and underemployment | §1R.6 | → S4.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.6.19 | gap | Corruption and tax farming | §1R.6 | → S4.6/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.6.20 | gap | Tax types (land, poll, trade, consumption) with collection efficiency | §1R.6 | → S4.6/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.6.21 | gap | Price elasticity and demand by income | §1R.6 | → S6.4/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.6.22 | gap | State granaries and famine relief policy | §1R.6 | → S4.6/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.6.23 | gap | Item destruction as a sink | §1R.6 | → F28 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | done |
| G1R.6.24 | gap | Blueprints and designs as tradable knowledge | §1R.6 | → S8.4/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.6.25 | gap | Survival economy under extreme cold or scarcity (heat as a resource) | §1R.6 | → F24, S4.2/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.6.26 | gap | Logistics throughput limits inside a settlement (hauling capacity) | §1R.6 | → S4.2/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | done |
| G1R.6.27 | gap | Chartered companies with shares and monopolies abroad | §1R.6 | → S4.3/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.6.28 | gap | Regional price differences driving arbitrage by merchant agents | §1R.6 | → S6.4/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.6.29 | gap | Tool wear in production | §1R.6 | → F24 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.6.30 | gap | Supply shocks propagating through chains with visible bottlenecks | §1R.6 | → S6.3/RP2, J.9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.7.1 | gap | Separate civic/social tree (governance, law, philosophy, religion innovations) | §1R.7 | → S8.4/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.7.2 | gap | Boosts by doing (eureka and inspiration triggers) | §1R.7 | → S8.4/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.7.3 | gap | Eras and era scores (golden and dark ages per realm by deeds) | §1R.7 | → S8.4/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.7.4 | gap | Great people generated from accumulated points by field | §1R.7 | → S8.4/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.7.5 | gap | Catch-up discount when neighbours know a technique | §1R.7 | → S8.4/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.7.6 | gap | Card-draw research options | §1R.7 | → S8.4/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.7.7 | gap | Dangerous techniques with world consequences | §1R.7 | → S8.4/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.7.8 | gap | Obsolescence and upgrading of units and buildings | §1R.7 | → S8.4/RP2, S5.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.7.9 | gap | Specialised researchers with expertise | §1R.7 | → S8.4/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.7.10 | gap | Unique projects and wonders gated by techniques | §1R.7 | → S7.2/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.7.11 | gap | Institutions that spread geographically from an origin and change the cost of everything | §1R.7 | → S8.4/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.7.12 | gap | Cultural innovations per culture | §1R.7 | → S4.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.7.13 | gap | Wrong theories and paradigm shifts | §1R.7 | → S8.4b | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.7.14 | gap | Reverse engineering of found artifacts | §1R.7 | → S8.4/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.7.15 | gap | Experiment accidents | §1R.7 | → S8.4/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.7.16 | gap | Patronage of scholars by rulers | §1R.7 | → S8.4/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.7.17 | gap | Printing and copying economics of knowledge | §1R.7 | → S8.4/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.7.18 | gap | Censorship and forbidden books | §1R.7 | → S8.4/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.7.19 | gap | Research agreements and shared research between realms | §1R.7 | → S8.4/RP2, S5.13/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.7.20 | gap | Tech-driven social change (social engineering choices) | §1R.7 | → S8.4/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.7.21 | gap | Knowledge of geography as a tree branch (cartography quality) | §1R.7 | → S8.4/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.7.22 | gap | Era-locked capabilities that require several branches together | §1R.7 | → S8.4/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.1 | gap | Title hierarchy (barony → county → duchy → kingdom → empire) with de jure territory | §1R.8 | → S4.11 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.2 | gap | Schemes with agents, phases, success odds and discovery | §1R.8 | → F20 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.3 | gap | Secrets and hooks (strong and weak leverage) | §1R.8 | → F20 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.4 | gap | Favours and obligations ledgers | §1R.8 | → F20 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.5 | gap | Trust as its own diplomatic quantity | §1R.8 | → F18, S4.6/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.6 | gap | Aggressive expansion and coalitions | §1R.8 | → S4.6/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.7 | gap | Diplomatic capacity (number of relations a realm can maintain) | §1R.8 | → S4.6/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.8 | gap | Crises with escalation, backers and swing parties | §1R.8 | → S4.6/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.9 | gap | Casus belli and claim fabrication | §1R.8 | → S5.8/RP2, F20 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.10 | gap | Estates and interest groups with privileges and loyalty | §1R.8 | → S4.3/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.11 | gap | Elections, assemblies, political parties and movements | §1R.8 | → S4.6/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.12 | gap | Law enactment as a process with progress, obstruction and chance | §1R.8 | → S4.5/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.13 | gap | Council offices with tasks | §1R.8 | → S4.6/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.14 | gap | Lifestyle focuses and perks | §1R.8 | → F17 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.15 | gap | Prestige, piety, dread and tyranny as currencies | §1R.8 | → F19 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.16 | gap | Negotiable vassal contracts | §1R.8 | → S4.6/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.17 | gap | Personal unions and inheritance of foreign titles | §1R.8 | → S4.11 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.18 | gap | Rivals and nemeses designated | §1R.8 | → F18 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.19 | gap | Public opinion and media (criers, broadsheets, propaganda, censorship) | §1R.8 | → F21 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.20 | gap | Correspondence with delay, interception, forgery, misreading | §1R.8 | → F21 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.21 | gap | Lying and bad-faith treaties; a reputation for honesty | §1R.8 | → F21, S5.13/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.22 | gap | Summits and multi-party congresses | §1R.8 | → F25 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.23 | gap | Great power status and spheres of influence | §1R.8 | → S4.6/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.24 | gap | Nationalism and separatist movements | §1R.8 | → S4.6/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.25 | gap | Diplomatic etiquette: gifts, insults, precedence | §1R.8 | → F21 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.26 | gap | Activities that build relationships (feasts, hunts, tournaments) | §1R.8 | → F25 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.27 | gap | Subject types (vassal, march, tributary, personal union, client) | §1R.8 | → S4.6/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.28 | gap | Policy networks: each policy affects voter groups and other policies | §1R.8 | → S4.6/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.29 | gap | Simultaneous negotiation and betrayal among several parties | §1R.8 | → S5.13/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.30 | gap | Constitutional structures and charters | §1R.8 | → S4.6/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.31 | gap | Hostage and ward diplomacy | §1R.8 | → S5.7 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | done |
| G1R.8.32 | gap | Information asymmetry in decisions | §1R.8 | → F22 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.33 | gap | Court with courtiers, positions and grandeur | §1R.8 | → S4.6/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.34 | gap | Inheritance partition splitting realms | §1R.8 | → S4.11 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.8.35 | gap | Religious authority over rulers (investiture, excommunication) | §1R.8 | → S4.4 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | done |
| G1R.9.1 | gap | Typed emotions and moods with sources and durations | §1R.9 | → F14 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.9.2 | gap | Aspirations and life goals with milestones | §1R.9 | → F17 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.9.3 | gap | Short-term wants and fears | §1R.9 | → F17 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.9.4 | gap | Two-axis relationships (friendship, romance) with types (best friend, crush, ex, enemy) | §1R.9 | → F18 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.9.5 | gap | Social interactions with outcomes (befriend, flirt, insult, comfort, argue, gossip) | §1R.9 | → F18 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.9.6 | gap | Appearance and genetics (inherited looks, heritable conditions) | §1R.9 | → F26 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.9.7 | gap | Likes and dislikes | §1R.9 | → F15 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.9.8 | gap | Households with shared funds, dwellings and dependents | §1R.9 | → F29 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.9.9 | gap | Home quality and environment affecting mood | §1R.9 | → F29 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.9.10 | gap | Leisure, hobbies, a fun need | §1R.9 | → F14, F17 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.9.11 | gap | Clubs and social circles | §1R.9 | → F18 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.9.12 | gap | Reputation (good or bad) in a community | §1R.9 | → F19 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.9.13 | gap | Career ladders with performance and income | §1R.9 | → S3.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.9.14 | gap | Pregnancy with duration and complications | §1R.9 | → S3.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.9.15 | gap | Affairs, jealousy, divorce | §1R.9 | → F18, F20 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.9.16 | gap | Varied causes of death and ghosts by cause | §1R.9 | → S3.3/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.9.17 | gap | Storyteller pacing of events | §1R.9 | → F27 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.9.18 | gap | Ideology precepts that shape daily life | §1R.9 | → S4.4 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | done |
| G1R.9.19 | gap | Mental breaks of many kinds | §1R.9 | → S3.1 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | done |
| G1R.9.20 | gap | Inspirations (positive breaks producing great work) | §1R.9 | → F14, F17 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.9.21 | gap | Childhood development stages with milestones and upbringing quality | §1R.9 | → S3.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.9.22 | gap | Old age wisdom and mentoring roles | §1R.9 | → S3.1/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.9.23 | gap | Social roles in family (head, dependent, carer) | §1R.9 | → F29 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.9.24 | gap | Grief and mourning processes | §1R.9 | → F14 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.9.25 | gap | Addiction and recovery at the individual level | §1R.9 | → F30 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.9.26 | gap | Daily-life lifestyle quality (sleep, hygiene, comfort) as an aggregate | §1R.9 | → F14 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.9.27 | gap | Personal events (birthdays, anniversaries, coming of age) feeding memories | §1R.9 | → F25 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.9.28 | gap | Pets and companionship | §1R.9 | → S3.2/RP2, S3.3a/RP2 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.12.1 | gap | Spatial dominion: each god's presence as a field per region, spreading from temples, prophets and holy sites, contested  | §1R.12 | → F31 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.12.2 | gap | Dominion scales that change the land (order–turmoil, productivity–sloth, heat–cold, growth–death, fortune–misfortune, ma | §1R.12 | → F31 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.12.3 | gap | God design trade-offs at creation (dominion strength against magic against body against scales) | §1R.12 | → S9.1/RP3 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.12.4 | gap | Global enchantments: world-wide persistent spells with upkeep, contested and dispellable | §1R.12 | → S8.6/RP3, S9.5/RP3 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.12.5 | gap | Magic sites found by searching regions with the right path knowledge | §1R.12 | → S6.2/RP3 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.12.6 | gap | Magical resource economy (gems per path) | §1R.12 | → S8.6/RP3 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.12.7 | gap | Thrones of power: holy sites that confer cosmic advantage and count toward ascension | §1R.12 | → S6.2/RP3, S9.1/RP3 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.12.8 | gap | Perceived alignment of a god from its acts, changing worship mode (love against fear) and the look of its holy sites and | §1R.12 | → S9.1/RP3 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.12.9 | gap | A divine creature that learns behaviours from its god's reward and punishment | §1R.12 | → S9.1/RP3 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.12.10 | gap | Miracle impressiveness: belief gain scales with witnesses, spectacle and need | §1R.12 | → S9.1/RP3 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.12.11 | gap | Land manipulation with physics consequences (raise land, redirect rivers, lava) | §1R.12 | → S6.1/RP3 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.12.12 | gap | Mana cost by proximity to one's dominion | §1R.12 | → F31 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.15.1 | gap | Elite overproduction: aspirants to elite positions outgrow positions, which drives intra-elite conflict | §1R.15 | → F37 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.15.2 | gap | Popular immiseration: falling real wages as population exceeds land | §1R.15 | → F37 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.15.3 | gap | State fiscal distress: expenses outgrow revenue | §1R.15 | → F37 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.15.4 | gap | Political stress index combining the three, which predicts instability waves | §1R.15 | → F37 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.15.5 | gap | Secular cycles of growth, stagflation, crisis and depression over centuries | §1R.15 | → F37 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.15.6 | gap | Asabiyya: frontier peoples gain cohesion, conquerors lose it over generations of luxury | §1R.15 | → F37 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.15.7 | gap | Meta-ethnic frontiers that forge new solidarities | §1R.15 | → F37 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.15.8 | gap | Challenge and response: severe but survivable challenges spur innovation | §1R.15 | → F37 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.15.9 | gap | Sacrifice as exchange with gods (do ut des) | §1R.15 | → F38 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.15.10 | gap | Monster contracts and professional monster hunters | §1R.15 | → S3.3a/RP4 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.18.14 | gap | Human biology | §1R.18 | → F39 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.18.15 | gap | Behaviour processes and personality | §1R.18 | → F40, F13/RP5 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.18.17 | gap | History and culture change | §1R.18 | → S4.1/RP5 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.18.22 | gap | Food quest (hunting, fishing, gathering) | §1R.18 | → S6.1/RP5 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.18.26 | gap | Food consumption | §1R.18 | → S4.2/RP5 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.18.27 | gap | Drink, drugs and indulgence | §1R.18 | → S4.1/RP5, S4.2/RP5 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.18.30 | gap | Adornment | §1R.18 | → S4.1/RP5 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.18.38 | gap | Chemical industries | §1R.18 | → S6.3/RP5 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.18.39 | gap | Capital goods industries | §1R.18 | → S7.1/RP5 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.18.40 | gap | Machines | §1R.18 | → S7.1/RP5 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.18.42 | gap | Property | §1R.18 | → S6.4/RP5 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.18.45 | gap | Finance | §1R.18 | → S6.4/RP5 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.18.47 | gap | Business and industrial organisation | §1R.18 | → S4.3/RP5 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.18.48 | gap | Travel and transportation | §1R.18 | → S4.6/RP5 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.18.51 | gap | Living standards and routines | §1R.18 | → S4.1/RP5 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.18.52 | gap | Recreation | §1R.18 | → S7.4/RP5 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.18.55 | gap | Individuation and mobility | §1R.18 | → S4.1/RP5 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.18.56 | gap | Social stratification | §1R.18 | → S4.1/RP5, F41 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.18.64 | gap | State | §1R.18 | → S4.6/RP5 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.18.65 | gap | Government activities | §1R.18 | → S4.2/RP5, S4.6/RP5 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.18.69 | gap | Justice | §1R.18 | → S4.5/RP5 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.18.74 | gap | Health and welfare | §1R.18 | → S4.2/RP5, S4.6/RP5 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.18.75 | gap | Sickness | §1R.18 | → F42 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.18.77 | gap | Religious beliefs | §1R.18 | → F42 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.18.78 | gap | Religious practices | §1R.18 | → F41 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.18.80 | gap | Numbers and measures | §1R.18 | → S4.2/RP5, S4.6/RP5 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.18.88 | gap | Adolescence, adulthood and old age | §1R.18 | → S4.1/RP5, F41 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.23.1 | gap | Microorganisms (bacteria, fungi, yeasts) beyond pathogens | §1R.23 | → S3.2/RP6 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.23.2 | gap | Symbiosis | §1R.23 | → S3.2/RP6 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.23.3 | gap | Ethology: dormancy | §1R.23 | → S3.2/RP6 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.23.4 | gap | Physiology: thermoregulation | §1R.23 | → S3.2/RP6, S4.1/RP6 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.23.5 | gap | Senses | §1R.23 | → S3.2/RP6 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.23.6 | gap | Plant defences | §1R.23 | → S3.2/RP6 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.23.7 | gap | Biogeography | §1R.23 | → S3.2/RP6 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.39.1 | gap | A1 | §1R.39 | → F49/RP9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.39.2 | gap | A1 | §1R.39 | → F49/RP9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.39.3 | gap | A1 | §1R.39 | → F49/RP9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.39.4 | gap | B4 | §1R.39 | → F49/RP9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.39.5 | gap | A3 | §1R.39 | → F48/RP9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.39.6 | gap | A4 (G10) | §1R.39 | → F48/RP9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.39.7 | gap | A3 | §1R.39 | → F46/RP9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.39.8 | gap | A3 | §1R.39 | → F46/RP9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.39.9 | gap | A3 | §1R.39 | → F45/RP9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.39.10 | gap | A2 | §1R.39 | → S3.3a/RP9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.39.11 | gap | A2 | §1R.39 | → S8.1/RP9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.39.12 | gap | A2 | §1R.39 | → S5.8/RP9 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.39.13 | gap | A4 | §1R.39 | → J.16b | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.39.14 | gap | A4 | §1R.39 | → J.16b | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.40.C1 | gap | code conflict | §1R.40 | → F49/RP10 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.40.C2 | gap | A4 (decision 26) | §1R.40 | → F49/RP10 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.40.C3 | gap | code conflict | §1R.40 | → F49/RP10 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.40.C4 | gap | A2 (F28 conservation) | §1R.40 | → F49/RP10 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.40.C5 | gap | consistency with 10.9 | §1R.40 | → F49/RP10 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.40.C6 | gap | A3 | §1R.40 | → S10.6/RP10 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.40.C7 | gap | A3 | §1R.40 | → F48/RP10 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.40.C8 | gap | A4 (catalogue hygiene) | §1R.40 | → J.16b | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| G1R.40.C9 | gap | A4 (systemic) | §1R.40 | → J.16c | n/a | n/a | n/a | n/a | n/a | n/a | n/a | planned |
| F1 | foundation | Time: seasons, sampled years and campaign turns | §F1 | engine/environment/years.py, disease/seasons.py, markets.swing_of, campaign seasons | growth, settlement_life, economy, epidemics, markets, campaigns | year:*, seasons:* | SeasonCalendarPanel, market swing chart | geography_lines | season.*, settlement.fire_wind | environment.battle_ground | tests/engine/environment/test_couplings.py, test_calendar.py | done |
| F1/RP3 | reference-pass | dating systems and calendars per culture | §F1 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| F2 | foundation | Environment substrate | §F2 | engine/environment/* | environment_survey, environment phases | environment:*, place:*, region:* | EntityEnvironment, RegionTerrain, map layers | geography_lines | environment.* | environment_survey | tests/engine/environment/* | done |
| F2.1 | foundation | Region environment (new typed table `region_environment`) | §F2.1 | db/tables/environment.py RegionEnvironmentRow, PlaceEnvironmentRow; cartography/environment.py (rivers by flow accumulation, roughness, latitude, coast kind); engine/environment/profile.py (terrain, soil, temperature band, rainfall, seasonality, disease load, minerals, passability, defensibility); catalog/place_terrain.py; scars written by battles, sieges, conquest, plague, quakes, curses, the leak and haunted battlefields | cleanup: environment_survey; growth: environment_derive | environment:set, environment:unlock, environment:scar, environment:mineral, environment:place | section-environment | geography lines: terrain, climate, soil, river, scars, harvest | n/a | environment_survey: profiled from the stored map; soil solved so fertility is unchanged; land use starts at what the people need | tests/engine/environment/test_environment.py; tests/engine/warfare/test_campaign_seasons.py | done |
| F2.2 | foundation | World seasons and calendar | §F2.2 | engine/lore/calendar_rites.py, environment/time_control.py | tradition_cycles, calendars | seasons:*, calendar:* | SeasonCalendarPanel | geography_lines | season.* | lore.holy_day_traditions | tests/engine/environment/test_calendar.py, seasonCalendar.test.tsx | done |
| F2.3 | foundation | Weather on demand | §F2.3 | environment/weather, settlement fires, lore/rites dampening | weather draw each phase; settlement_life; wizards | weather:force/edit/release | RegionWorksPanel | geography_lines | settlement.fire_wind | n/a | tests/engine/environment/test_couplings.py | done |
| F2.4 | foundation | Derived environment values | §F2.4 | environment/profile.py (rainfall_of, fertility), environment/works.py irrigation, natural-law multiplier | environment_survey | environment:set, settlement:edit | RegionWorksPanel | geography_lines | n/a | environment.typed_works | tests/engine/environment/test_couplings.py | done |
| F2.5 | foundation | Land use and ecological pressure | §F2.5 | land_use phase (cleared, farmed, grazed, mined, built; erosion, overfarming, rewilding); mined by worked resources and seams deplete; wild land carries species (ecology); disease load reads building and crowding Land use writes land.erosion, land.overfarmed, land.soil_exhausted, land.rewilded. Rewilding lowers cleared land, which raises forest cover and wildness, which raises wild species carrying capacity in engine/ecology/ranges.py (3.2) | society engine: land_use; economy: resource_economy | environment:set for any land-use counter | section-environment (land use) | geography lines: land use | n/a | environment_survey: inhabited regions start at the land use their people need | tests/engine/environment/test_environment.py | done |
| F2.6 | foundation | Ley lines and magic geography | §F2.6 | environment/ley.py, ley_works.py, faith/doctrine.target_for, cosmos/pilgrimage.holy_sites | ley_lines, faith_cycles, travel | ley:*, nexus via environment:place | RegionWorksPanel, place section, ley map layer | geography | tools.son.raise_nexus | environment.ley_attunement | tests/engine/environment/test_couplings.py | done |
| F3 | foundation | Materials and commodities | §F3 | catalog/materials.py, engine/economy/{materials,provenance,sanctity,loot}.py | economy_survey, travel, markets | material:*, node_material:*, stock:grant | MaterialsBrowser, MaterialForge, NodeMaterials | entity_detail EconomyBlock | tools.son.forge_material | economy.depth_backfill | tests/engine/society/test_economy_depth.py | done |
| F3.1 | foundation | Material catalog (`catalog/materials.py`, rules namespace `materials`) | §F3.1 | catalog/materials.py, world_materials (player-creatable), node material slots | economy_survey, item and structure creation | material:create/edit/delete/revert, node_material:* | MaterialForge, NodeMaterials | entity_detail | tools.son.forge_material | economy.depth_backfill | tests/engine/society/test_economy_depth.py | done |
| F3.2 | foundation | Commodity expansion | §F3.2 | catalog/commodities.py, demography/basket.py, settlement/storage.py | society_economy, markets | stock:*, needs:* | EntityEconomy stores, NeedsBasket | EconomyBlock | n/a | economy.depth_backfill | tests/engine/society/test_society_depth.py | done |
| F3/RP3 | reference-pass | world-specific materials | §F3 reference pass 3 | engine/economy/deposits.py new_substance (a god's remains, a dead star's core, a slain great beast, a leak crystal, a researched alloy; properties strayed from the base material; the deposit is a pending-name record so the LLM names and describes it, G8); WorldMaterialRow | economy: world_materials | material:edit (rename, set properties) | /economy MaterialsBrowser | named by the naming pipeline | material.substance_* | none: substances appear from events | tests/engine/port_structure/test_economy_depth.py (world-specific substances from god remains, dead stars, beasts, leak crystals and research become pending-named deposits; forged, held and unmade) | done |
| F3/RP6 | reference-pass | building materials | §F3 reference pass 6 | — | — | — | — | — | — | — | — | planned |
| F4 | foundation | Bodies, injuries and conditions | §F4 | engine/body/* | body_* phases | body:* levers | BodySection | body block in contexts | injury.*, healing.* | body_survey | tests/engine/body/* | done |
| F4.1 | foundation | Body plans (`catalog/anatomy.py`) | §F4.1 | catalog/anatomy.py (12 plans, part trees with function tags, counted fingers, species trait parts: wings, venom gland, horn, tail); db/tables/body.py BodyRow; engine/body/book.py plan_for (species of the people, divine bodies for sons and foreign gods) | cleanup: body_survey | body:plan | section-body (body diagram: a drawn figure per plan from scripts/anatomy, every wound state textured, marked and labelled, the killing wound shown on the fallen) | entity detail Body and wounds | n/a | body_survey: species plans from their traits; mortals take their people's species or a humanoid body | tests/engine/body/test_body.py, tests/api/test_bodies.py, AnatomyFigure.test.tsx | done |
| F4.2 | foundation | Injury records (`injuries` table) | §F4.2 | db/tables/body.py InjuryRow (bearer, part, kind, severity, state, function_loss, cause, event, healer, visible); engine/lifecycle/wounds.py apply_hits replaces wound() for battle wounds, falls, duels, monster hunts, quests, curses, cursed items, poison, escapes, theft, gate sacrifice, disasters, son duels, foreign-god wars and the creator's punishments; fatal_injury for violent deaths | every harm source; aging: mortal_wounds | body:maim, body:injury, body:heal | section-body (injury history) | entity detail: missing parts, scars, open wounds | injury.<kind> | body_survey: the fallen (battle, siege, captivity, disaster flags) get one fatal wound; others start unhurt | tests/engine/body/test_body.py; tests/engine/core/test_lifecycle.py | done |
| F4.3 | foundation | From weapons to injuries | §F4.3 | body/hits.py, lifecycle/wounds.py, military duels (per-exchange injury) | combat, hunts, disasters | body:injury, body:injury_hold | BodySection | body block | injury.* | body_survey | tests/engine/body/test_body.py | done |
| F4.4 | foundation | Healing, infection and death from wounds | §F4.4 | engine/body/healing.py (festering by kind, disease load and medicine; campaign checks; lethal festering; surgery amputation; healing chance by severity, endurance, rest, healer and divine bodies; scars and lasting damage; reattachment; prosthetics; hp regeneration; TREATED_BY bonds and healer renown); miracles mend wounds and restore senses; the healer is whoever holds the medicine and surgery skills of F6, gains experience per patient and is remembered as saved_me or failed_to_heal (W3) | aging: body_healing | body:heal, body:prosthesis, body:prosthesis_remove, healing.* rules | section-body (healer, medicine tier, prostheses) | entity detail Body and wounds | healing.amputated, healing.reattached, healing.prosthesis | none: open wounds begin healing on the next epoch | tests/engine/body/test_body.py; tests/engine/mind/test_mind.py | done |
| F4.5 | foundation | Permanent conditions and how they change the world | §F4.5 | body/conditions.py, customs.py, capacities.py | body phases | body:condition_edit, prosthesis_edit | BodySection, BodySociety | body block | condition.* | body_survey | tests/engine/body/* | done |
| F4.6 | foundation | Disease | §F4.6 | engine/disease/* (vectors, hosts, target functions, chronic illness) | epidemics | disease:*, outbreak:*, endemic:* | DiseaseCard, ForgeDisease | mortal sickness lines | disease.emerged/loosed | disease.plague_history | tests/engine/society/test_disease_depth.py, test_disease_controls.py | done |
| F5 | foundation | Personality, values and culture (shared value space) | §F5 | engine/mind/values.py, mortal/acts.py (loyalty, value pressure) | mind_values, mortal_minds | mind:*, mortal:set | MindSection | mind block | mind.* | mind backfill | tests/engine/mind/* | done |
| F5.1 | foundation | Traits (`TraitKind`, mortals and gods) | §F5.1 | domain/enums/mind.py TraitKind (40), TraitEffect; catalog/mind.py TRAITS (opposites, value shifts, capacity and decision effects, heritable, divine subset), CONDITION_TRAITS; engine/mind/traits.py (birth by values, inheritance, experience: battle survivors, freed captives, maimed fighters; madness and marks; education by masters); readers: capacities in use, war appetite, betrayal, cruelty to captives, justice against uprisings, trust, memory decay, learning, value drift, exploration, agent selection; LLM reads traits (deepener, bard, son turn) | cleanup: mind_survey; war: campaigns; aging: body_conditions; mind: mind_skills | mind:trait, mind:trait_remove, mind:lock | section-mind (temperament chips with effects) | Mind block: temperament; deepener writes character from it | n/a | mind_survey: two to three birth traits weighted by values, heritable ones from parents; gods take a divine subset | tests/engine/mind/test_mind.py; mindSections.test.tsx | done |
| F5/RP3 | reference-pass | social learning | §F5 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| F6 | foundation | Skills and proficiency | §F6 | engine/mind/skills.py, mortal/learning.py (per-language, per-school, professions) | mortal_minds, rite_cycles | mind:skill, mind:skill_edit, variant:* | SkillsSection, Life profession | mind block | career.* | mortal_survey | tests/engine/body/test_mortal_learning.py | done |
| F6/RP2 | reference-pass | learning, rust and teaching | §F6 reference pass 2 | engine/mind/skills.py: learning rate by traits, rust after skills.rust_epochs down to the best level x skills.rust_floor_pct, learning by doing and from masters (teach_apprentices with the master's teaching skill); engine/mortal/learning.py: demonstration by watching a master of the profession in the same community, lectures at lecture halls by a teaching master, books by fidelity; phases/mind.py spar: combat practice with light training wounds; governing attributes read the core abilities, and the F13 attribute set replaces them in W3+ | mind: mind_skills | skills.* rules | section-skills | Mind block | skill.career_* (a calling changed or lost) | none: rust starts from the backfilled last use | tests/engine/mind/test_mind.py, tests/engine/body/test_mortal_learning.py | done |
| F7 | foundation | Opinions and memory | §F7 | engine/mind/opinion.py, memories, lore/legends.remember_legend | mind_opinion, legend_cycles | mind:memory | MemoriesSection, CommunityRelations | mind block | memory.*, lore.legend_memory | mind.relation_history | tests/engine/mind/* | done |
| F8 | foundation | Needs and pressures | §F8 | domain/enums/mind.py NeedKind, PressureKind; db/tables/mind.py NeedRow, PressureRow; engine/mind/needs.py (mortal needs: sustenance, safety, belonging, status, purpose, faith, pleasure; community pressures: hunger, insecurity, overcrowding, poverty, impiety, humiliation, stagnation); engine/mind/drives.py; readers: famine migration, uprisings with the ruler's justice, war declarations, faction founding, conversion, expeditions, agent selection; need.despair notes | mind: mind_needs | mind:need, mind:pressure, mind:lock | section-mind (need bars, pressure tiles) | Mind block: most pressing needs or the two heaviest pressures | need.despair | computed every epoch | tests/engine/mind/test_mind.py; mindSections.test.tsx | done |
| F9 | foundation | Modifier bus (the backbone of interconnection) | §F9 | db/tables/interconnect.py ModifierRow; engine/primitives/modifiers.py (ModifierIndex, combine with stacking groups, base_for, live per-step index LIVE_MODIFIERS); engine/primitives/stats.py (stat reads effective values clamped to the field, set_stats writes the base, conserved counts take no modifier); engine/interconnect/guards.py run_guarded loads the index per step; engine/phases/interconnect.py derive_modifiers (wonders, conditions); engine/interconnect/sources.py (source subsystems, reason texts, condition effects) | every engine step reads through the bus; cleanup stage: modifier_upkeep (expiry, decay, derived modifiers) | modifier:add, modifier:remove, lever:pin, lever:set | section-mechanics WhyBreakdown on every stat (base, each modifier with its reason, ignored stacking) | entity detail: What bears on it now (modifier lines with reasons) | reason keys modifier.wonder, modifier.condition.*, player.* | derive_modifiers: wonder flags and lasting conditions become modifiers on the first epoch | tests/engine/interconnect/test_guards.py; tests/unit/test_interconnection_registry.py | done |
| F10 | foundation | Causality log (`incidents`) | §F10 | db/tables/interconnect.py IncidentRow (cause, magnitude, thread, note), IncidentParticipantRow (subject, actor, target, witness, place); db/repositories/chronicle.py (cause found through shared participants in the same epoch, magnitude by kind and participants, place role, LAST_INCIDENT for memories and injuries); engine/interconnect/incidents.py (chains, recent chain, causality graph); engine/phases/interconnect.py incident_threads | every chronicle write; mind stage: incident_threads opens a story thread from a chain of incidents.thread_chain_min | incident:annotate | section-biography BiographySection (life log by epoch with CausalChain and notes); section-mechanics incidents | entity detail: How its latest deed came about; chronicler, Fate and bards: chains of cause this age | incidents carry their chronicle template keys | migration 26caa21842b3: incidents from chronicle rows | tests/engine/interconnect/test_incidents.py; e2e/entity.spec.ts | done |
| F10/RP2 | reference-pass | event collections | §F10 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| F11 | foundation | Information and rumour | §F11 | engine/lore/rumours.py, phases/rumours.py | rumour_cycles | rumour:plant/edit/suppress | RumoursSection | mortal_context heard rumours | rumour.alarm, rumour.legend | lore.rumours_backfill | tests/engine/lore/test_rumours.py | done |
| F11/RP3 | reference-pass | gossip networks | §F11 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| F12 | foundation | Scale bridging: individuals and cohorts | §F12 | engine/demography/* cohorts, promotion, dormancy | cohort_upkeep, labour_allocation | cohort:set/move, mortal:dormancy | Demography | folk lines | peoples.* | peoples.depth_backfill | tests/engine/society/test_peoples_depth.py | done |
| F12/RP3 | reference-pass | generations | §F12 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| F13 | foundation | Attributes, facets and beliefs (the mind split) | §F13 | catalog/mind_split.py (19 attributes with stat summaries, the 34 facets the spec lists with culture leanings and trait extremes, skill governing attributes, condition wear, 10 new belief axes), engine/mind/split.py, db/tables/mind.py (mind_attributes, mind_facets); beliefs inherited from parents, cult and master; cross-wave: beauty feeding presence lands with F26 (W5+), facets setting emotion intensity with F14 and interaction choices with F18 (W3+) | mind_survey seeds and backfills; mind_split grows attributes with practice, wears them with age and conditions, syncs stat summaries both ways, pulls facets toward held traits and grants traits at the extremes; toughness, recuperation and disease resistance in wounds and healing; facets in stress, breaks and commander boldness | mind:attributes, mind:facets, mind:lock, mind:unlock | MindSplitSection in ThingSections (attribute tiles, facet bars with culture lean, controls with holds) | mind_lines strongest and weakest attributes and most marked facets | mind.facet_trait | mind_survey: attributes from stats, facets around culture beliefs and traits; mind.belief_axes fills the new axes from the old ones | tests/engine/mind/test_mind_split.py; tests/services/player/test_mind_split_levers.py | done |
| F13/RP5 | reference-pass | internalising ideas | §F13 reference pass 5 | engine/mind/ideas.py, db/tables/mind.py (incubating_ideas), catalog/mind_split.py IDEAS with belief shifts, typed gains and costs, facet shifts and focus cost | mind_ideas: ideas met in ideologies, cult tenets, known theories, owned books and masters; incubation scaled by curiosity and fit; poorly fitting ideas let go | mind:idea, mind:idea_edit, mind:idea_remove; son tool plant_idea | MindSplitSection Ideas card (progress, fit, source, settle, let go, plant with preview) | mind_lines ideas turning over and taken to heart; plant_idea tool | idea.internalised, idea.rejected | none: ideas are met from the next epoch | tests/engine/mind/test_mind_split.py; tests/services/player/test_mind_split_levers.py | done |
| F14 | foundation | Thoughts, emotions and moods | §F14 | catalog/thoughts.py (96 thought kinds, 24 emotions with facet amplifiers, needs with group, facet and belief importance), engine/mind/thoughts.py, feelings.py, grief.py, needs.py (23 needs: the 7 kept with safety, and 16 more), db/tables/mind.py (thoughts, griefs), mortal_profiles mood; cross-wave: dwelling quality in comfort lands with F29, mood steering interaction choices with F18 and inspirations with F17 (W3+) | mind_thoughts: thoughts from remembered deeds, weddings, births, needs, feasts, great works, music, prayers answered or ignored; battles, duels, deaths, wounds, healing, illness, punishment, conversion, miracles, teaching, callings and masterworks think directly; formative memories shift beliefs and facets, are relived and can leave a trauma; mood feeds stress, breaking points, craft quality and agent choice; mind_grief runs shock, mourning and acceptance or complicated grief | thought:send, thought:edit, thought:remove, thought:mood, grief:start, grief:edit, grief:remove, mind:need, mind:lock, mind:unlock | FeelingsSection in ThingSections (mood, feelings, thoughts, formative memories, grief, controls); Mind needs card grouped with importance | mind_lines mood, strongest feelings, grief, last dream | none | migration d5f7b9c1e3a4: thoughts arise from the next epoch, every mood starts fine | tests/engine/mind/test_feelings.py; tests/services/player/test_feeling_levers.py | done |
| F14/RP4 | reference-pass | dreams | §F14 reference pass 4 | engine/mind/dreams.py, db/tables/mind.py (dreams), catalog/thoughts.py readings; nightmares condition; cross-wave: dream as a message medium lands with F21 (W6+) | mind_dreams: ordinary, nightmare, longing, prophetic, shared and visitation dreams; god dream messages and the son tool send_dream become visitations; recurring nightmares become a condition; dream readers read omens that shift beliefs, true or false; dream worlds host shared and prophetic dreams | dream:send, dream:edit, dream:remove; son tool send_dream | FeelingsSection Dreams card (kind, people, world, reading picker, recurring) | mind_lines last dream and reading | dream.recurring, dream.reading | none: dreams begin from the next epoch | tests/engine/mind/test_feelings.py; tests/services/player/test_feeling_levers.py | done |
| F15 | foundation | Preferences (likes and dislikes) | §F15 | catalog/preferences.py (15 kinds and their targets), engine/mind/preferences.py, db/tables/mind.py (preferences), artwork colour and shape; cross-wave: gift value in diplomacy lands with F21 (W6+) | mind_preferences seeds peoples from land, patron, aesthetic and beliefs and mortals from their people, grows tastes with life, pulls cultures toward their mortals, makes taboos of shared disgust and totems of loved creatures; markets weigh food, drink and material demand by taste; art renown follows the holders' taste and rulers commission their loved art form; glory hunts spare the totem; loved creatures and plants feed the need for nature; land, weather, food and the season of feasts colour mood | preference:set, preference:remove, mind:lock, mind:unlock | TastesSection in ThingSections (tastes by kind, totem, controls) | mind_lines loves and dislikes | none | mind_preferences | tests/engine/mind/test_culture_mind.py; tests/services/player/test_culture_mind_levers.py | done |
| F16 | foundation | Ethics tables | §F16 | catalog/ethics.py (stance ladder, act labels, crimes), engine/mind/ethics.py, db/tables/mind.py (culture_ethics); 26 new acts each with an engine source (killings named at death, crimes, bribery, torture, slavery, feeding, iconoclasm and forced conversion, marriages of kin or many, magic by school, hoarding in famine; conquest, raids, broken oaths and mercy now sourced too); cross-wave: adultery with F18 (W3+); usury, infanticide and abandoning elders with F29 households (W5+) | witnesses judge acts by their culture's stance, softened by war and hardened by famine or kin; the actor gains renown or infamy, guilt and stress, rulers lose legitimacy; unthinkable acts with light punishments harden the code; mind_ethics drifts stances with beliefs and the people's cults, splits a people when its notables hold the opposite pole | ethics:set, mind:lock, mind:unlock | EthicsSection in ThingSections (stance ladder, inherited ethics for mortals and settlements) | mind_lines held right and wrong | ethics.schism | mind_ethics | tests/engine/mind/test_culture_mind.py; tests/services/player/test_culture_mind_levers.py | done |
| F16/RP4 | reference-pass | honour and shame dynamics | §F16 reference pass 4 | engine/mind/ethics.py honour models, db/tables/mind.py (culture_honour), public shaming punishment (pillory in the code of punishments); cross-wave: face-saving in diplomacy lands with F21 (W6+) | honour cultures spread shame to kin as a household grievance and seek restoration by compensation; face cultures weigh public shame more and guilt less; dignity cultures put law over insult and harden codes for shameful acts too | ethics:honour | EthicsSection honour panel | mind_lines honour model | none | mind_ethics | tests/engine/mind/test_culture_mind.py; tests/services/player/test_culture_mind_levers.py | done |
| F17 | foundation | Aspirations, dreams, wants and fears | §F17 | — | — | — | — | — | — | — | — | planned |
| F17/RP3 | reference-pass | acting in character | §F17 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| F18 | foundation | Relationships and social interactions | §F18 | owed in W3+: adultery as an F16 act; mood steering interaction choices (F14) | — | — | — | — | — | — | — | planned |
| F18/RP3 | reference-pass | passions, persuasion and status | §F18 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| F18/RP6 | reference-pass | contests of wit | §F18 reference pass 6 | — | — | — | — | — | — | — | — | planned |
| F19 | foundation | Local reputation and social currencies | §F19 | — | — | — | — | — | — | — | — | planned |
| F19/RP3 | reference-pass | lore as currency | §F19 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| F19/RP6 | reference-pass | claims of deeds | §F19 reference pass 6 | — | — | — | — | — | — | — | — | planned |
| F20 | foundation | Secrets, hooks, favours, identities and schemes | §F20 | cross-wave owed: hidden F30 afflictions become hidden_condition secrets; the F30 blood curse gives a false identity | — | — | — | — | — | — | — | planned |
| F20/RP3 | reference-pass | true names | §F20 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| F20/RP8 | reference-pass | ecology and environment in intrigue | §F20 reference pass 8 | — | — | — | — | — | — | — | — | planned |
| F21 | foundation | Communication: correspondence, envoys, public opinion and etiquette | §F21 | cross-wave owed: F14 dreams as a message medium (visitations already record their message); F15 gift value; F16 face-saving in diplomacy | — | — | — | — | — | — | — | planned |
| F21/RP3 | reference-pass | codes and ciphers | §F21 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| F22 | foundation | Belief state and fog of war for decisions | §F22 | — | — | — | — | — | — | — | — | planned |
| F23 | foundation | Material physics and tissue layers | §F23 | catalog/materials.py PHYSICS, engine/economy/materials.py, engine/body/strike.py, catalog/tissues.py, engine/body/tissues.py, engine/body/digits.py (named fingers and toes by hand and foot, weighted thumb and index, the leading hand in grip), engine/body/treatment.py, healing.bled_out, duels.armour_burden, warfare.out_cold | economy_survey, body_survey, body_healing, war_casualties, duels, settlement fires | body:set, body:unlock, body:consciousness, body:digit, body:handedness, body:treat, body:injury, material:edit, material:hold, mortal:equip | BodySection (blood, exertion, consciousness, teeth and toes, tissue, bleeding, nerve and treatment steps on wounds), MaterialsTab physics, section-gear armour layers | body_lines (bleeding, limp or numb wounds, consciousness, blood and exertion) in mortal and son context | healing.amputated, injury.* | economy_survey (PHYSICS_FIXUP), body_survey | tests/engine/body/test_strike.py; tests/engine/body/test_tissues.py; tests/engine/body/test_digits.py | done |
| F24 | foundation | Production methods, quality, energy and pollution | §F24 | — | — | — | — | — | — | — | — | planned |
| F25 | foundation | Activities and gatherings | §F25 | — | — | — | — | — | — | — | — | planned |
| F26 | foundation | Appearance and genetics | §F26 | cross-wave owed: F30 stages change appearance (beast curse, blood curse, void taint); F13 beauty feeds presence alongside social awareness | — | — | — | — | — | — | — | planned |
| F26/RP8 | reference-pass | the magical gift | §F26 reference pass 8 | — | — | — | — | — | — | — | — | planned |
| F27 | foundation | Storyteller (deterministic drama pacing) | §F27 | — | — | — | — | — | — | — | — | planned |
| F28 | foundation | Conservation and stock-flow invariants | §F28 | engine/interconnect/flows.py (FlowCategory, transfers, sources, sinks, per-step defaults, flowing); engine/interconnect/conservation.py (snapshot with journeys, residuals over new records, transfer imbalance, wrong signs, unexplained flows, journey imbalance); engine/primitives/levies.py (levy, discharge); engine/primitives/records.py founded; engine/snapshot.py soldiers, travelling and flow totals per epoch | every engine step records categorised conserved flows | lever:run (flows recorded the same way) | overview StatsCharts chart-population, chart-followers, chart-soldiers, chart-travelling | n/a | n/a | none: the ledger starts with the first epoch after W0 | tests/engine/interconnect/test_conservation.py | done |
| F29 | foundation | Households and dwellings | §F29 | cross-wave owed: dwelling quality feeds the F14 comfort and rest needs; usury, infanticide and abandoning elders as F16 acts | — | — | — | — | — | — | — | planned |
| F30 | foundation | Effect packages (syndromes) | §F30 | catalog/effect_packages.py (stages hold conditions, stats, values, needs added and quenched, body traits granted), engine/body/afflictions.py, db/tables/afflictions.py; cross-wave: stage appearance changes land with F26 (W5+), hidden afflictions as secrets and the blood curse's false identity land with F20 (W6+) | body_afflictions; bites, births, possession, vice, blood-school backlash, desecration, son curse | affliction:give, affliction:edit, affliction:hold, affliction:cure, affliction:delete | AfflictionsSection (stages, visibility, transmission, source, cures, give form with package preview) | body_lines Bears line; son curse tool affliction field | affliction.*, affliction.cured | none: afflictions arise from play from the next epoch | tests/engine/body/test_afflictions.py | done |
| F31 | foundation | Dominion and scales (the spatial presence of gods) | §F31 | — | — | — | — | — | — | — | — | planned |
| F32 | foundation | Collective behaviour: crowds, mobs, panics and movements | §F32 | — | — | — | — | — | — | — | — | planned |
| F33 | foundation | Historiography and collective memory | §F33 | — | — | — | — | — | — | — | — | planned |
| F34 | foundation | Storylets (typed event chains) | §F34 | — | — | — | — | — | — | — | — | planned |
| F35 | foundation | Social norms and volition | §F35 | — | — | — | — | — | — | — | — | planned |
| F36 | foundation | Narrative arcs and the drama manager | §F36 | — | — | — | — | — | — | — | — | planned |
| F37 | foundation | Structural-demographic and civilisational cycles | §F37 | — | — | — | — | — | — | — | — | planned |
| F38 | foundation | Reciprocity and gift exchange | §F38 | — | — | — | — | — | — | — | — | planned |
| F39 | foundation | Nutrition and diet quality | §F39 | — | — | — | — | — | — | — | — | planned |
| F40 | foundation | Decision biases | §F40 | — | — | — | — | — | — | — | — | planned |
| F41 | foundation | Purity and pollution | §F41 | — | — | — | — | — | — | — | — | planned |
| F42 | foundation | Luck, charms and witchcraft | §F42 | — | — | — | — | — | — | — | — | planned |
| F43 | foundation | Identity layers and salience | §F43 | — | — | — | — | — | — | — | — | planned |
| F44 | foundation | The technology ceiling: advanced eras | §F44 | — | — | — | — | — | — | — | — | planned |
| F45 | foundation | World-type applicability rules | §F45 | — | — | — | — | — | — | — | — | planned |
| F45/RP9 | reference-pass | the dead without scavengers | §F45 reference pass 9 | — | — | — | — | — | — | — | — | planned |
| F46 | foundation | Biology applicability rules | §F46 | — | — | — | — | — | — | — | — | planned |
| F46/RP9 | reference-pass | components and biases by biology | §F46 reference pass 9 | — | — | — | — | — | — | — | — | planned |
| F47 | foundation | Lifecycle ends and decay rules | §F47 | — | — | — | — | — | — | — | — | planned |
| F48 | foundation | Prehistory and deep-time runs | §F48 | — | — | — | — | — | — | — | — | planned |
| F48/RP9 | reference-pass | prehistory by world type and for existing worlds | §F48 reference pass 9 | — | — | — | — | — | — | — | — | planned |
| F48/RP10 | reference-pass | prehistory fallbacks | §F48 reference pass 10 | — | — | — | — | — | — | — | — | planned |
| F49 | foundation | Transformation graph (type changes) | §F49 | — | — | — | — | — | — | — | — | planned |
| F49/RP9 | reference-pass | completing the transformations | §F49 reference pass 9 | — | — | — | — | — | — | — | — | planned |
| F49/RP10 | reference-pass | consistency with the existing engine | §F49 reference pass 10 | — | — | — | — | — | — | — | — | planned |
| S3.1 | section | Mortal | §3.1 | engine/mortal/*, phases/mortal_life.py, births, mortals | mortal_survey, mortal_life_course, mortal_kin, mortal_standing, mortal_minds | mortal:*, kin:*, variant:* | Life, Kin, Gear sections, Stress card | life_lines | life., kin., births., justice., standing. | mortal.typed_kin, mortal.death_causes, mortal_survey | tests/engine/body/test_mortal_life.py, tests/services/player/test_mortals.py | done |
| S3.1/RP2 | reference-pass | R1, R7 | §3.1 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S3.1/RP3 | reference-pass | R9, R22 | §3.1 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| S3.1/RP4 | reference-pass | R34, R35 | §3.1 reference pass 4 | — | — | — | — | — | — | — | — | planned |
| S3.1/RP6 | reference-pass | S-I | §3.1 reference pass 6 | — | — | — | — | — | — | — | — | planned |
| S3.2 | section | Species (kind and population) | §3.2 | engine/ecology/*, phases/creatures.py, phases/wilds.py, phases/ecology.py | creatures, speciation, husbandry, ecology | species:*, herd:*, use_kind:*, people:totem | SpeciesSection, food-web graph, range layer, Create a kind | nature lines, create_species | creatures.predation, ecology.animal_god | wilds.typed_nature | tests/engine/cosmos/test_wilds_typed.py, tests/services/player/test_wilds_controls.py | done |
| S3.2/RP2 | reference-pass | R1, R2 | §3.2 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S3.2/RP3 | reference-pass | R9, R12 | §3.2 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| S3.2/RP6 | reference-pass | S-E | §3.2 reference pass 6 | — | — | — | — | — | — | — | — | planned |
| S3.2/RP8 | reference-pass | B1 | §3.2 reference pass 8 | — | — | — | — | — | — | — | — | planned |
| S3.3a | section | Beast (new type: a named individual creature) | §3.3a | engine/ecology/beasts.py, military/clash.py, travel.py | beast_cycles, campaigns, travel | beast:create/slay/treasure | BeastSection, Call forth a beast | beast nature lines, raise_beast | beasts.* | n/a (no prior state) | tests/engine/cosmos/test_wilds_typed.py | done |
| S3.3a/RP2 | reference-pass | R1, R2, R7 | §3.3a reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S3.3a/RP3 | reference-pass | R10 | §3.3a reference pass 3 | — | — | — | — | — | — | — | — | planned |
| S3.3a/RP4 | reference-pass | R34, R38 | §3.3a reference pass 4 | — | — | — | — | — | — | — | — | planned |
| S3.3a/RP8 | reference-pass | B2 | §3.3a reference pass 8 | — | — | — | — | — | — | — | — | planned |
| S3.3a/RP9 | reference-pass | A2 | §3.3a reference pass 9 | — | — | — | — | — | — | — | — | planned |
| S3.3 | section | Spirit, soul and afterlife | §3.3 | engine/faith/{judgement,souls,exorcism,control,backfill}.py, phases/spirits.py | soul_cycles, beyond, hauntings | soul:*, afterlife:stratum | SoulCard, AfterlifeRealm, StratumEditor, PossessionCard | son_turn_user souls; open_rebirth_gate | afterlife.*, spirits.ghost_legend | faith.spirit_profiles, strata fixups | tests/engine/faith/test_afterlife.py, tests/api/test_faith.py | done |
| S3.3/RP2 | reference-pass | R1, R7 | §3.3 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S3.3/RP3 | reference-pass | R9 | §3.3 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| S3.3/RP4 | reference-pass | R33 | §3.3 reference pass 4 | — | — | — | — | — | — | — | — | planned |
| S3.3/RP5 | reference-pass | S-D Stormlight | §3.3 reference pass 5 | — | — | — | — | — | — | — | — | planned |
| S3.3/RP8 | reference-pass | B2 | §3.3 reference pass 8 | — | — | — | — | — | — | — | — | planned |
| S3.4 | section | Disease (new type) | §3.4 | engine/disease/* | epidemics, natural_disasters | disease:*, outbreak:*, cohort sickness | DiseaseCard, ForgeDisease | mortal sickness lines | disease.* | disease.plague_history | tests/engine/society/test_disease_depth.py | done |
| S3.4/RP2 | reference-pass | R1, R7 | §3.4 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S3.4/RP3 | reference-pass | R12, R15 | §3.4 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| S4.1 | section | People (ethnic and cultural community) | §4.1 | engine/demography/{biology,kinship,rites,martial,urban,tongues,basket}.py | people_cycles, society_economy | people:* | Folk and customs, Demography | folk lines | peoples.* | peoples.depth_backfill | tests/engine/society/test_peoples_depth.py | done |
| S4.1/RP2 | reference-pass | R4, R5, R7 | §4.1 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S4.1/RP3 | reference-pass | R24 | §4.1 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| S4.1/RP4 | reference-pass | R27, R29, R34 | §4.1 reference pass 4 | — | — | — | — | — | — | — | — | planned |
| S4.1/RP5 | reference-pass | S-A OCM 17, 27, 30, 51, 55, 56 | §4.1 reference pass 5 | — | — | — | — | — | — | — | — | planned |
| S4.1/RP6 | reference-pass | S-E | §4.1 reference pass 6 | — | — | — | — | — | — | — | — | planned |
| S4.2 | section | Settlement | §4.2 | engine/settlement/{districts,storage,readout,life,control}.py | settlement_life, natural_disasters, campaigns, polity_cycles | settlement:*, district:* | SettlementPlan, CityWorkings, DistrictDesigns | mortal context | settlement.district_* | settlement_life | tests/engine/society/test_settlement_depth.py, test_urban_controls.py | done |
| S4.2/RP2 | reference-pass | R1, R4, R7 | §4.2 reference pass 2 | engine/settlement/life.py (investment pool from owners' sales; construction capacity from builders and architecture; hauling capacity and waste in the outer districts; rationing and abandoning the old where mercy allows); housing per district (F29 dwellings follow in W5+); local reputation per settlement follows F19 | society-engine: settlement_life | settlement:edit | section-settlement-plan | mortal_context: home line | settlement.abandoned | none: acts from the next epoch | tests/engine/society/test_settlement_depth.py (investment pool from owners' sales and its hold, roads raise hauling and short hauling wastes production, a starving merciless town abandons its elders and a merciful one does not) | done |
| S4.2/RP3 | reference-pass | R13, R23 | §4.2 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| S4.2/RP4 | reference-pass | R29, R42 | §4.2 reference pass 4 | — | — | — | — | — | — | — | — | planned |
| S4.2/RP5 | reference-pass | S-A OCM 26, 27, 65, 74; S-D Workers & Resources | §4.2 reference pass 5 | — | — | — | — | — | — | — | — | planned |
| S4.3 | section | Faction (interest group, guild, order, band) | §4.3 | engine/factions/{agenda,balance,outlaws,control}.py | faction phases | faction:* | Faction.tsx (power balance, agenda, deeds) | found_faction | faction.* | faction_profiles_from_kinds | tests/engine/warfare/test_factions_espionage_conflict.py, faction.test.tsx | done |
| S4.3/RP2 | reference-pass | R4, R6 | §4.3 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S4.3/RP3 | reference-pass | R10, R14, R22, R23 | §4.3 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| S4.3/RP4 | reference-pass | R36 | §4.3 reference pass 4 | — | — | — | — | — | — | — | — | planned |
| S4.3/RP5 | reference-pass | S-A OCM 47 | §4.3 reference pass 5 | — | — | — | — | — | — | — | — | planned |
| S4.4 | section | Cult (religious organisation and its doctrine) | §4.4 | engine/faith/{doctrine,works,zeal,zealotry,church,backfill}.py | faith_cycles, religion_spread, schisms | cult:*, relic:* | DoctrineSheet, TenetCard, ClergyOffices, RelicShrine | mortal_context, son_turn_user; reveal_tenet | faith.* | faith fixups | tests/engine/faith/test_church.py, test_faith_levers.py | done |
| S4.4/RP2 | reference-pass | R6 | §4.4 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S4.4/RP4 | reference-pass | R33 | §4.4 reference pass 4 | — | — | — | — | — | — | — | — | planned |
| S4.4/RP6 | reference-pass | S-H | §4.4 reference pass 6 | — | — | — | — | — | — | — | — | planned |
| S4.5 | section | Law | §4.5 | engine/polity/{laws,law_effects,justice}.py | polity_cycles, settlement_life | law:*, change_law, protect_law | Realm law code, Statecraft | realm context; enact_law | polity.* | law_kinds_from_text | tests/engine/polity/test_polity_depth.py | done |
| S4.5/RP2 | reference-pass | R1, R6 | §4.5 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S4.5/RP3 | reference-pass | R18, R23 | §4.5 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| S4.5/RP4 | reference-pass | R34 | §4.5 reference pass 4 | — | — | — | — | — | — | — | — | planned |
| S4.5/RP5 | reference-pass | S-A OCM 69; S-D Shadows of Doubt | §4.5 reference pass 5 | — | — | — | — | — | — | — | — | planned |
| S4.6 | section | Polity (new type: realm / state) | §4.6 | engine/polity/{standing,formation,offices,governance,control}.py | polity_cycles | polity:*, office:*, claim:* | Realm, Statecraft | agents/context/realm.py | polity.* | dynasty and realm fixups | tests/engine/polity/test_polity_depth.py, test_polity_epochs.py | done |
| S4.6/RP2 | reference-pass | R1, R4, R6 | §4.6 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S4.6/RP4 | reference-pass | R27, R28 | §4.6 reference pass 4 | — | — | — | — | — | — | — | — | planned |
| S4.6/RP5 | reference-pass | S-A OCM 48, 64, 65, 80 | §4.6 reference pass 5 | — | — | — | — | — | — | — | — | planned |
| S4.6/RP6 | reference-pass | S-G, S-H | §4.6 reference pass 6 | — | — | — | — | — | — | — | — | planned |
| S4.6/RP8 | reference-pass | B3 | §4.6 reference pass 8 | — | — | — | — | — | — | — | — | planned |
| S4.7 | section | House (new type: dynasty, clan, noble line) | §4.7 | engine/polity/houses.py | house_cycles | house:* | Covenants house editor, FamilyTree | realm context; bless_bloodline | houses.* | houses_dynasty_ancestors | tests/engine/polity/test_polity_depth.py | done |
| S4.7/RP2 | reference-pass | R6 | §4.7 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S4.7/RP3 | reference-pass | R19 | §4.7 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| S4.7/RP4 | reference-pass | R27, R34 | §4.7 reference pass 4 | — | — | — | — | — | — | — | — | planned |
| S4.8 | section | Oaths and honour (typed table) | §4.8 | engine/polity/oaths.py, accords.py | oath and treaty cycles | oath edit/release; swear_oath | Oaths cards | swear_oath | oath.* | existing rows | tests/engine/polity/test_polity_depth.py | done |
| S4.8/RP3 | reference-pass | R9 | §4.8 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| S4.9 | section | Society and labour (cross-cutting) | §4.9 | engine/demography/{labour,wealth,events}.py, polity/loyalty.py | labour_allocation, society_economy | labour:*, mobility:*, loyalty:* | Work, LabourReasons, Loyalty | society lines | society.*, loyalty.wavering | society.depth_backfill | tests/engine/society/test_society_depth.py | done |
| S4.9/RP4 | reference-pass | R41 | §4.9 reference pass 4 | — | — | — | — | — | — | — | — | planned |
| S4.10 | section | Community relations (extended) | §4.10 | services/community_relations.py, phases/mortal_life ethnic_relations, migration, institutions | mind_opinion, ethnic_relations | mind:memory | CommunityRelations | entity_detail | relations.ethnic_strife | mind.relation_history | tests/engine/body/test_mortal_life.py | done |
| S4.11 | section | Title (new type) | §4.11 | — | — | — | — | — | — | — | — | planned |
| S5.1 | section | Army | §5.1 | engine/military/{units,campaign,logistics,finance}.py | campaigns, war_upkeep | army:*, military:* | ArmyPanel, ArmyOrders | agents/context/military.py | war.mutiny.* | military.army_size_matches_stacks | tests/engine/warfare/test_military_depth.py | done |
| S5.1/RP2 | reference-pass | R1, R3 | §5.1 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S5.1/RP3 | reference-pass | R21 | §5.1 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| S5.1/RP4 | reference-pass | R32 | §5.1 reference pass 4 | — | — | — | — | — | — | — | — | planned |
| S5.1/RP6 | reference-pass | S-J | §5.1 reference pass 6 | — | — | — | — | — | — | — | — | planned |
| S5.2 | section | Terrain, weather and season in battle | §5.2 | engine/military/{tables,rule_tables}.py, environment/battleground.py | campaigns | war:battle_at, tactic | BattleDepth | military context | war.battle.* | defaults equal old values | tests/engine/warfare/test_battle_depth.py | done |
| S5.3 | section | Battle resolution (phased) | §5.3 | engine/military/{battle,clash,aftermath}.py | campaigns | war:battle_at, army tactic | BattleDepth, battle timeline | military context | war.battle.* | n/a | tests/engine/warfare/test_battle_depth.py | done |
| S5.3/RP2 | reference-pass | R3 | §5.3 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S5.3/RP4 | reference-pass | R32 | §5.3 reference pass 4 | — | — | — | — | — | — | — | — | planned |
| S5.4 | section | Sieges (multi-season) | §5.4 | engine/military/{siege,siege_depth}.py | campaigns | siege:start, siege edits | WarOrders, siege works cards | military context; lay_siege | war.sack.*, war.siege.relieved | wall material on open | tests/engine/warfare/* | done |
| S5.4/RP2 | reference-pass | R3 | §5.4 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S5.5 | section | Naval and sky warfare | §5.5 | engine/military/{naval,vessels,shipyard}.py | seafaring, campaigns | vessel:* | VesselCard | commission_vessel | seafaring.* | vessel fixup | tests/engine/warfare/* | done |
| S5.5/RP2 | reference-pass | R3 | §5.5 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S5.5/RP4 | reference-pass | R30 | §5.5 reference pass 4 | — | — | — | — | — | — | — | — | planned |
| S5.6 | section | Duels and single combat | §5.6 | engine/military/{duels,trials}.py | campaigns | war:ordeal | duel lines in war room | military context (duel results) | war.trial_by_combat, war.god_duel | n/a | tests/engine/warfare/test_war_gaps.py | done |
| S5.6/RP2 | reference-pass | R1, R3 | §5.6 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S5.7 | section | Captives, hostages and slaves | §5.7 | engine/military/{ransom,captivity}.py | prisoners | captive:take, captive records | NamedPrisoners | military context | prisoner.* | n/a | tests/engine/warfare/test_tribute_and_prisoners.py | done |
| S5.7/RP2 | reference-pass | R1 | §5.7 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S5.8 | section | War, war aims and peace (with the treaty type) | §5.8 | engine/military/{causes,aims,peace,finance,upkeep}.py | campaigns, war_upkeep | war:declare, war:peace | WarRoom, WarLedger, PeaceTreaty, WarMap | military context; wage_war, offer_peace | war.* | n/a | tests/engine/warfare/test_military_depth.py | done |
| S5.8/RP2 | reference-pass | R3, R6 | §5.8 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S5.8/RP8 | reference-pass | B2 | §5.8 reference pass 8 | — | — | — | — | — | — | — | — | planned |
| S5.8/RP9 | reference-pass | A2 | §5.8 reference pass 9 | — | — | — | — | — | — | — | — | planned |
| S5.9 | section | Vendettas and blood feuds | §5.9 | engine/military/feuds.py | vendetta_cycles | feud records | Vendettas | military context | vendetta.faded | flag mirrors feud row | tests/engine/society/test_heroes.py | done |
| S5.10 | section | Espionage (extended) | §5.10 | engine/military/spycraft.py, phases/espionage.py | espionage | spy network/agent records, faction:spy | SpyNetworks | military context; plant_spies | espionage.* | bond migration fixup | tests/engine/warfare/test_factions_espionage_conflict.py | done |
| S5.10/RP2 | reference-pass | R6 | §5.10 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S5.10/RP3 | reference-pass | R17 | §5.10 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| S5.11 | section | Interconnections of conflict | §5.11 | engine/military/aftermath.py (medicine, captives carry language, learned tactics) | campaigns | military:* | MilitaryDepth | military context | war.* | n/a | tests/engine/warfare/test_military_depth.py | done |
| S5.12 | section | Tables, rules, levers, UI | §5.12 | tables, rules namespaces campaigns/battle_*/levies/seafaring/siege_depth/tactic_matchups | campaigns, war_upkeep, seafaring, espionage | military:create/edit/release/delete | WarRoom, ArmyPanel, MilitarySection | military context | war.* | 5b1d3f7a9c21, 5b1d3f7a9c23 | tests/engine/warfare/* | done |
| S5.13 | section | Treaty (new type) | §5.13 | engine/polity/{accords,treaties}.py | treaty_cycles | treaty:*, clause:*, vassalage:* | treaty builder, TreatyView | seal_treaty, void_treaty; propose/accept/break | treaty.* | treaties_from_bonds | tests/engine/polity/test_polity_depth.py | done |
| S5.13/RP2 | reference-pass | R5, R6 | §5.13 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S6.1 | section | Region | §6.1 | engine/environment/{dangers,memory,knowledge,perils,hazards,region_control,geomorph}.py, phases/regions.py | region_survey, danger_harm, terrain_hazards, sacred_pilgrims, geomorphology | region:*, environment:*, land:* | RegionTerrain, RegionSeams, LandShapeSection, danger/rainfall/scar/sacred map layers | geography_lines | danger.*, hazard.*, land.* | region.terrain_backfill, geomorphology | tests/engine/environment/test_region_terrain.py, regionTerrain.test.tsx | done |
| S6.1/RP2 | reference-pass | R1, R2 | §6.1 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S6.1/RP3 | reference-pass | R8, R12 | §6.1 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| S6.1/RP4 | reference-pass | R29 | §6.1 reference pass 4 | — | — | — | — | — | — | — | — | planned |
| S6.1/RP5 | reference-pass | S-A OCM 22 | §6.1 reference pass 5 | — | — | — | — | — | — | — | — | planned |
| S6.1/RP8 | reference-pass | B3 | §6.1 reference pass 8 | — | — | — | — | — | — | — | — | planned |
| S6.2 | section | Place | §6.2 | db/tables/place.py, environment/{places,secrets,place_backfill,battleground}.py, phases/places.py | survey, place_profiles, place_secrets, campaigns | place:* | PlaceSection, PlaceSecrets, CreatePlace | geography lines; create_place | place.* | places.kind_backfill | tests/engine/environment/test_places.py, place.test.tsx | done |
| S6.2/RP2 | reference-pass | R1, R2 | §6.2 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S6.2/RP3 | reference-pass | R8, R10 | §6.2 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| S6.2/RP4 | reference-pass | R31 | §6.2 reference pass 4 | — | — | — | — | — | — | — | — | planned |
| S6.2/RP7 | reference-pass | A5 Dewey 560 | §6.2 reference pass 7 | — | — | — | — | — | — | — | — | planned |
| S6.3 | section | Resource | §6.3 | engine/economy/{resources,extraction}.py | resource_economy, resource_regeneration | resource:* | ResourceProfile | EconomyBlock | extraction.* | economy.depth_backfill | tests/engine/core/test_tick_phases.py, test_economy_depth.py | done |
| S6.3/RP2 | reference-pass | R1, R4 | §6.3 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S6.3/RP5 | reference-pass | S-A OCM 38 | §6.3 reference pass 5 | — | — | — | — | — | — | — | — | planned |
| S6.4 | section | Markets, money and trade routes | §6.4 | engine/economy/{routes,chokepoints,markets,money,realm_credit,toll_polities}.py | trade_flow, banking, markets | route, toll, pact, loan, currency, hoard, price levers | RouteAndMarket, EconomyScreen, HoardControl, LoanForge | EconomyBlock | trade_route.*, banking.*, market.* | economy.route_depth_backfill | tests/engine/port_structure/test_route_depth.py, test_market.py | done |
| S6.4/RP2 | reference-pass | R4 | §6.4 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S6.4/RP3 | reference-pass | R14 | §6.4 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| S6.4/RP4 | reference-pass | R34, R4 | §6.4 reference pass 4 | — | — | — | — | — | — | — | — | planned |
| S6.4/RP5 | reference-pass | S-A OCM 42, 45 | §6.4 reference pass 5 | — | — | — | — | — | — | — | — | planned |
| S6.4/RP6 | reference-pass | S-F, S-G | §6.4 reference pass 6 | — | — | — | — | — | — | — | — | planned |
| S7.1 | section | Item | §7.1 | engine/lore/{items,arms,history}.py, phases/made_things.py | item_cycles, travel, vendetta_cycles | item:*, lore:create, kind:* | ItemPanel, ItemControls | forge_item (typed) | item.* | lore.typed_items | tests/engine/lore/test_made_things.py | done |
| S7.1/RP2 | reference-pass | R1 | §7.1 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S7.1/RP5 | reference-pass | S-A OCM 39, 40 | §7.1 reference pass 5 | — | — | — | — | — | — | — | — | planned |
| S7.1/RP6 | reference-pass | S-F | §7.1 reference pass 6 | — | — | — | — | — | — | — | — | planned |
| S7.2 | section | Structure | §7.2 | engine/structures/* | structure_survey, structure_upkeep, engine_works, structure_functions | structure:* (11 levers) | Structures sections, works panel | entity_detail; commission_structure, build_structure | structures.* | structures.typed_backfill | tests/engine/society/test_structures.py, structures.test.tsx | done |
| S7.2/RP2 | reference-pass | R1, R2, R5 | §7.2 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S7.2/RP6 | reference-pass | S-F | §7.2 reference pass 6 | — | — | — | — | — | — | — | — | planned |
| S7.2/RP7 | reference-pass | A5 Dewey 060, 710 | §7.2 reference pass 7 | — | — | — | — | — | — | — | — | planned |
| S7.3 | section | Vessel | §7.3 | engine/military/{vessels,shipyard,naval}.py | seafaring | vessel:create/refit/repair | VesselCard, LayDownVessel | create_vessel, commission_vessel | seafaring.* | vessel fixup | tests/engine/warfare/* | done |
| S7.3/RP2 | reference-pass | R2 | §7.3 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S7.3/RP3 | reference-pass | R21 | §7.3 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| S7.3/RP6 | reference-pass | S-F | §7.3 reference pass 6 | — | — | — | — | — | — | — | — | planned |
| S7.4 | section | Artwork | §7.4 | engine/lore/art.py | artwork_cycles | art:commission/canonise, lore:create | ArtworkPanel, ArtControls | commission_artwork, create_artwork | art.* | lore.typed_artworks | tests/engine/lore/test_made_things.py | done |
| S7.4/RP2 | reference-pass | R1, R7 | §7.4 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S7.4/RP4 | reference-pass | R36 | §7.4 reference pass 4 | — | — | — | — | — | — | — | — | planned |
| S7.4/RP5 | reference-pass | S-A OCM 52 | §7.4 reference pass 5 | — | — | — | — | — | — | — | — | planned |
| S7.5 | section | Art form (new type) | §7.5 | deferred to W9+ per J.10 (art forms) | — | — | — | — | — | — | — | planned |
| S7.5/RP8 | reference-pass | B3 | §7.5 reference pass 8 | — | — | — | — | — | — | — | — | planned |
| S8.1 | section | Language | §8.1 | engine/lore/language.py | language_cycles, treaty_cycles, trade_flow, religion_spread | language:register, release_* | LanguagePanel, TongueAtlas registers | mortal_context | treaty.misread_breach | language_cycles | tests/engine/lore/test_language.py | done |
| S8.1/RP2 | reference-pass | R1, R6 | §8.1 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S8.1/RP3 | reference-pass | R11 | §8.1 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| S8.1/RP8 | reference-pass | B1 | §8.1 reference pass 8 | — | — | — | — | — | — | — | — | planned |
| S8.1/RP9 | reference-pass | A2 | §8.1 reference pass 9 | — | — | — | — | — | — | — | — | planned |
| S8.2 | section | Legend | §8.2 | engine/lore/{legends,backfill}.py | legend_cycles | lore:edit/create, legend:forget | LegendPanel | tell_legend (typed) | lore.legend_* | lore.typed_kinds_backfill | tests/engine/lore/test_legends.py | done |
| S8.2/RP2 | reference-pass | R1 | §8.2 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S8.2/RP3 | reference-pass | R9 | §8.2 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| S8.3 | section | Tradition | §8.3 | engine/lore/{traditions,taboos}.py | tradition_cycles, campaigns, vendetta_cycles | tradition:effect/reseed/participation | TraditionPanel | found_tradition (typed) | lore.taboo_broken, lore.guest_killing, lore.commemoration* | lore.typed_kinds_backfill | tests/engine/lore/test_traditions.py | done |
| S8.3/RP2 | reference-pass | R7 | §8.3 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S8.4 | section | Knowledge | §8.4 | engine/lore/research.py, phases/knowledge_levels.py, culture_exchange, doom, mood | research_cycles, knowledge_levels, knowledge_diffusion | research:*, item:content, kind:* | LearningSection, KindForge, map marks | mortal_context, son knowledge_pairs | knowledge.deepened | research_cycles | tests/engine/lore/test_made_things.py | done |
| S8.4/RP2 | reference-pass | R1, R4, R5 | §8.4 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S8.4/RP4 | reference-pass | R37 | §8.4 reference pass 4 | — | — | — | — | — | — | — | — | planned |
| S8.4/RP5 | reference-pass | S-A OCM 80 | §8.4 reference pass 5 | — | — | — | — | — | — | — | — | planned |
| S8.4b | section | Theory (new type) | §8.4b | deferred to W9+ per J.10 (theories) | — | — | — | — | — | — | — | planned |
| S8.5 | section | Ideology (new type) | §8.5 | engine/lore/ideology.py, learning_control.py | ideology_cycles | creed:* | IdeologyPanel | son GodlessCreeds line; found_school | lore.creed, lore.revolution, lore.godless_* | ideology_cycles | tests/engine/lore/test_made_things.py | done |
| S8.5/RP2 | reference-pass | R6, R5 | §8.5 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S8.6 | section | Rite and magic (new type `rite`) | §8.6 | engine/lore/rites.py, phases/magic.py | rite_cycles, wizards | rite:*, item:enchant | RitePanel, RiteDesigner | design_rite, cast_rite | magic.* | lore.rite_profiles | tests/engine/lore/test_made_things.py | done |
| S8.6/RP2 | reference-pass | R1 | §8.6 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S8.6/RP3 | reference-pass | R8, R9, R10 | §8.6 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| S8.6/RP5 | reference-pass | S-D Mistborn, Kingkiller | §8.6 reference pass 5 | — | — | — | — | — | — | — | — | planned |
| S8.6/RP8 | reference-pass | B1 | §8.6 reference pass 8 | — | — | — | — | — | — | — | — | planned |
| S8.7 | section | Prophecy | §8.7 | engine/lore/prophecy.py | prophecy_cycles, belief_and_memory | lore:edit, prophecy:resolve, lore:create | ProphecyPanel | prophesy, utter_prophecy (typed) | lore.prophecy*, lore.infanticide | prophecy_cycles | tests/engine/lore/test_made_things.py | done |
| S8.7/RP2 | reference-pass | reference pass | §8.7 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S8.7/RP4 | reference-pass | R34, R35 | §8.7 reference pass 4 | — | — | — | — | — | — | — | — | planned |
| S8.8 | section | Event (time-bounded happening) | §8.8 | engine/happenings/* | event_phases, natural_disasters, settlement_life, campaigns | event:* | EventCard, EventsHere | chronicler event_phases block | event.<kind>, event.phase.* | event_phases, events.casualties_backfill | tests/engine/environment/test_happenings.py, happenings.test.tsx | done |
| S8.8/RP2 | reference-pass | reference pass | §8.8 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S9.1 | section | Son (god card) | §9.1 | — | — | — | — | — | — | — | — | planned |
| S9.1/RP2 | reference-pass | R1, R6, R7 | §9.1 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S9.1/RP3 | reference-pass | R8, R9 | §9.1 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| S9.1/RP4 | reference-pass | R33 | §9.1 reference pass 4 | — | — | — | — | — | — | — | — | planned |
| S9.2 | section | Creator (the player's god) | §9.2 | — | — | — | — | — | — | — | — | planned |
| S9.2/RP2 | reference-pass | reference pass | §9.2 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S9.3 | section | Foreign god | §9.3 | — | — | — | — | — | — | — | — | planned |
| S9.3/RP2 | reference-pass | reference pass | §9.3 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S9.4 | section | Pantheon council | §9.4 | — | — | — | — | — | — | — | — | planned |
| S9.4/RP2 | reference-pass | R6 | §9.4 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S9.4/RP3 | reference-pass | R9 | §9.4 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| S9.5 | section | Natural law | §9.5 | — | — | — | — | — | — | — | — | planned |
| S9.5/RP2 | reference-pass | reference pass | §9.5 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S9.5/RP3 | reference-pass | R8, R10 | §9.5 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| S9.6 | section | Outer being | §9.6 | — | — | — | — | — | — | — | — | planned |
| S9.6/RP2 | reference-pass | reference pass | §9.6 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S10.1 | section | Star | §10.1 | — | — | — | — | — | — | — | — | planned |
| S10.1/RP2 | reference-pass | R2 | §10.1 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S10.2 | section | World | §10.2 | — | — | — | — | — | — | — | — | planned |
| S10.2/RP2 | reference-pass | R2 | §10.2 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S10.2/RP3 | reference-pass | R9 | §10.2 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| S10.2/RP4 | reference-pass | R34, R39 | §10.2 reference pass 4 | — | — | — | — | — | — | — | — | planned |
| S10.3 | section | Celestial body (entity) | §10.3 | — | — | — | — | — | — | — | — | planned |
| S10.3/RP2 | reference-pass | R2 | §10.3 reference pass 2 | — | — | — | — | — | — | — | — | planned |
| S10.4 | section | Route (inter-world) | §10.4 | — | — | — | — | — | — | — | — | planned |
| S10.4/RP5 | reference-pass | S-B, S-C, S-D Terra Invicta | §10.4 reference pass 5 | — | — | — | — | — | — | — | — | planned |
| S10.5 | section | Journey | §10.5 | — | — | — | — | — | — | — | — | planned |
| S10.6 | section | Phenomenon (new type) | §10.6 | — | — | — | — | — | — | — | — | planned |
| S10.6/RP3 | reference-pass | R9 | §10.6 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| S10.6/RP10 | reference-pass | C6 | §10.6 reference pass 10 | — | — | — | — | — | — | — | — | planned |
| S10.7 | section | Climate (cross-cutting) | §10.7 | — | — | — | — | — | — | — | — | planned |
| S10.7/RP5 | reference-pass | S-B | §10.7 reference pass 5 | — | — | — | — | — | — | — | — | planned |
| S10.8 | section | Doom and leak (cross-cutting) | §10.8 | — | — | — | — | — | — | — | — | planned |
| S10.8/RP4 | reference-pass | R34 | §10.8 reference pass 4 | — | — | — | — | — | — | — | — | planned |
| S10.9 | section | Cosmic physics (derived, second pass) | §10.9 | — | — | — | — | — | — | — | — | planned |
| S10.9/RP3 | reference-pass | R12 | §10.9 reference pass 3 | — | — | — | — | — | — | — | — | planned |
| I.1 | deliverable | Interconnection registry | §I.1 | engine/interconnect/registry.py (Mechanic, Coupling with kind and rule_key, Edge, EdgeKind); engine/interconnect/edges.py (declared, flow edges from @reads/@writes, modifier edges, rule switches, matrix); engine/interconnect/sweeps.py; scripts/interconnection_docs.py writes docs/spec/13-interconnection.md (matrix I.2, cycles I.3, 1R.22 sweep listings) | n/a | n/a | section-mechanics: mechanics acting on the record with what they reach | n/a | n/a | n/a | tests/unit/test_interconnection_registry.py; tests/unit/test_mechanic_compliance.py | done |
| I.2 | deliverable | Subsystem matrix (rows affect columns) | §I.2 | — | — | — | — | — | — | — | — | planned |
| I.3 | deliverable | Feedback loops catalogue | §I.3 | — | — | — | — | — | — | — | — | planned |
| L1 | loop | War casualties → maimed cohort → visible weariness → peace pressure → fewer wars | Part I | — | — | — | — | — | — | — | — | planned |
| L2 | loop | Victory → martial values → bigger levies → more victories | Part I | — | — | — | — | — | — | — | — | planned |
| L3 | loop | Conquest → territory > administration → provincial autonomy → secession → smaller realm | Part I | — | — | — | — | — | — | — | — | planned |
| L4 | loop | Deforestation → less rainfall → desertification → famine → clearing more land | Part I | — | — | — | — | — | — | — | — | planned |
| L5 | loop | Overfarming → soil decline → famine → migration → rewilding | Part I | — | — | — | — | — | — | — | — | planned |
| L6 | loop | Trade → wealth → luxury demand → more trade | Part I | — | — | — | — | — | — | — | — | planned |
| L7 | loop | High tolls → traffic diverts → toll revenue falls | Part I | — | — | — | — | — | — | — | — | planned |
| L8 | loop | Killing → killed_kin memory → vendetta → killing | Part I | — | — | — | — | — | — | — | — | planned |
| L9 | loop | Persecution → martyr memory → zeal → conversion → bigger cult | Part I | — | — | — | — | — | — | — | — | planned |
| L10 | loop | Prosperity → comfort → zeal falls → cult shrinks | Part I | — | — | — | — | — | — | — | — | planned |
| L11 | loop | Prophecy → believers act → condition met → certainty of the next prophecy rises | Part I | — | — | — | — | — | — | — | — | planned |
| L12 | loop | Disease endemic → locals immune → invaders die → conquest fails | Part I | — | — | — | — | — | — | — | — | planned |
| L13 | loop | Leak → horror → godlessness → leak | Part I | — | — | — | — | — | — | — | — | planned |
| L14 | loop | God neglect → conversion away → existence falls → the son acts more (desperate goals) → standing recovers | Part I | — | — | — | — | — | — | — | — | planned |
| L15 | loop | Injured ruler → legitimacy falls → faction challenge → civil war → more injured rulers | Part I | — | — | — | — | — | — | — | — | planned |
| L16 | loop | Extinction of prey → predators starve → predation falls → prey recovers | Part I | — | — | — | — | — | — | — | — | planned |
| L17 | loop | A legend of a cursed line → house prestige falls → fewer marriages → house weakens → confirms the legend | Part I | — | — | — | — | — | — | — | — | planned |
| L18 | loop | Debasement → inflation → merchant opinion falls → trade falls → tax falls → the treasury must recoin honestly | Part I | — | — | — | — | — | — | — | — | planned |
| L19 | loop | Literacy → administration → bigger realm → schools → literacy | Part I | — | — | — | — | — | — | — | — | planned |
| L20 | loop | Wonder envy → neighbours' relation falls → war → wonder sacked | Part I | — | — | — | — | — | — | — | — | planned |
| L21 | loop | Weather rite in war → victory → the mages' faction grows → more weather rites → leak and backlash | Part I | — | — | — | — | — | — | — | — | planned |
| L22 | loop | Child heir → regency → regent ambition → usurpation risk → laws for regency councils | Part I | — | — | — | — | — | — | — | — | planned |
| I.4 | deliverable | End-to-end emergence scenarios (acceptance stories) | §I.4 | — | — | — | — | — | — | — | — | planned |
| AS1 | story | The Winter Campaign. | Part I | — | — | — | — | — | — | — | — | planned |
| AS2 | story | The Iron Famine. | Part I | — | — | — | — | — | — | — | — | planned |
| AS3 | story | The Silver Hand. | Part I | — | — | — | — | — | — | — | — | planned |
| AS4 | story | The Plague Saint. | Part I | — | — | — | — | — | — | — | — | planned |
| AS5 | story | The Tongueless Law. | Part I | — | — | — | — | — | — | — | — | planned |
| I.5 | deliverable | Second-pass couplings | §I.5 | — | — | — | — | — | — | — | — | planned |
| I.6 | deliverable | Second-pass feedback loops | §I.6 | — | — | — | — | — | — | — | — | planned |
| L23 | loop | Inbreeding to hold claims → heritable conditions → weak heirs → claims contested → more inbreeding to secure them | Part I | — | — | — | — | — | — | — | — | planned |
| L24 | loop | Mechanised production (mills) → unemployment → unrest → guild riots against mills → slower adoption | Part I | — | — | — | — | — | — | — | — | planned |
| L25 | loop | False theory endorsed by a cult → bad treatments → more deaths → more prayer → stronger cult | Part I | — | — | — | — | — | — | — | — | planned |
| L26 | loop | Speculation → hoarding → famine prices → riots → state granaries opened → merchants ruined → less speculation | Part I | — | — | — | — | — | — | — | — | planned |
| L27 | loop | Threat from conquests → coalition → war → more conquests or a collapse | Part I | — | — | — | — | — | — | — | — | planned |
| L28 | loop | Tyranny → factions → concessions → less tyranny | Part I | — | — | — | — | — | — | — | — | planned |
| L29 | loop | Pollution → disease → fewer workers → more coal-hungry methods per worker → more pollution | Part I | — | — | — | — | — | — | — | — | planned |
| L30 | loop | Ice–albedo cooling → glaciers → volcanism exposure unchanged → greenhouse rises slowly → thaw | Part I | — | — | — | — | — | — | — | — | planned |
| L31 | loop | Secrets learned at gatherings → hooks → forced marriages → more gatherings of the hooked houses | Part I | — | — | — | — | — | — | — | — | planned |
| L32 | loop | Delayed messages → wars that peace would have prevented → war weariness → faster courier networks (postal technique) | Part I | — | — | — | — | — | — | — | — | planned |
| L33 | loop | Art form prestige → more artists → more renowned works → higher prestige | Part I | — | — | — | — | — | — | — | — | planned |
| L34 | loop | Storyteller: low tension → raised disruptions → crisis → recovery boost | Part I | — | — | — | — | — | — | — | — | planned |
| L35 | loop | Desecration → curse (werebeast) → bitten victims → more cursed → hunts and purges → persecution memories | Part I | — | — | — | — | — | — | — | — | planned |
| L36 | loop | Dwelling squalor → disease → deaths → fewer people per dwelling → lower squalor | Part I | — | — | — | — | — | — | — | — | planned |
| L37 | loop | Deep mining → caverns opened → beasts emerge → walls and armies → more ore for arms → deeper mining | Part I | — | — | — | — | — | — | — | — | planned |
| L38 | loop | Great person concentration in one realm → era score lead → envy → wars that kill scholars | Part I | — | — | — | — | — | — | — | — | planned |
| L39 | loop | Censorship → black-market books → secret circles → movements → harsher censorship | Part I | — | — | — | — | — | — | — | — | planned |
| L40 | loop | Impact predicted → granaries and migration → fewer deaths → astronomers' prestige → more observatories → better prediction | Part I | — | — | — | — | — | — | — | — | planned |
| I.7 | deliverable | Second-pass acceptance stories | §I.7 | — | — | — | — | — | — | — | — | planned |
| AS6 | story | The Forged Letter. | Part I | — | — | — | — | — | — | — | — | planned |
| AS7 | story | The Humours and the Plague. | Part I | — | — | — | — | — | — | — | — | planned |
| AS8 | story | The Mill Riots. | Part I | — | — | — | — | — | — | — | — | planned |
| AS9 | story | The Werewolf of the Grove. | Part I | — | — | — | — | — | — | — | — | planned |
| AS10 | story | The Comet Winter. | Part I | — | — | — | — | — | — | — | — | planned |
| AS11 | story | The Wedding Feast. | Part I | — | — | — | — | — | — | — | — | planned |
| AS12 | story | The Iron Seam Beneath. | Part I | — | — | — | — | — | — | — | — | planned |
| I.8 | deliverable | Third-pass couplings | §I.8 | — | — | — | — | — | — | — | — | planned |
| I.9 | deliverable | Third-pass feedback loops | §I.9 | — | — | — | — | — | — | — | — | planned |
| L41 | loop | Dominion → cheaper miracles → more belief → stronger dominion | Part I | — | — | — | — | — | — | — | — | planned |
| L42 | loop | Belief shapes god → god acts as believed → belief confirmed | Part I | — | — | — | — | — | — | — | — | planned |
| L43 | loop | Heroquest deviations → myth changes → future questers on the new myth → divergent boons → schisms | Part I | — | — | — | — | — | — | — | — | planned |
| L44 | loop | Treatment use → pathogen resistance → more deaths → more treatment | Part I | — | — | — | — | — | — | — | — | planned |
| L45 | loop | Riot cascade → harsher policing → grievances → lower thresholds next time | Part I | — | — | — | — | — | — | — | — | planned |
| L46 | loop | Gentrification → poor pushed out → service workers scarce → wages rise → partial return | Part I | — | — | — | — | — | — | — | — | planned |
| L47 | loop | Revisionist history → legitimacy → stability → the revision becomes the only surviving account | Part I | — | — | — | — | — | — | — | — | planned |
| L48 | loop | Precedent drift → harsh case law → unrest → appeals overturn | Part I | — | — | — | — | — | — | — | — | planned |
| L49 | loop | Paranoid mole hunts → loyal officers purged → real moles thrive → more paranoia | Part I | — | — | — | — | — | — | — | — | planned |
| L50 | loop | Overhunting the keystone species → service loss → famine → hunting pressure falls | Part I | — | — | — | — | — | — | — | — | planned |
| L51 | loop | Chain migration → diaspora → stronger pull → more migration | Part I | — | — | — | — | — | — | — | — | planned |
| L52 | loop | Belief-shaped world drifts toward a Death god's nature → death scale stronger → more death belief | Part I | — | — | — | — | — | — | — | — | planned |
| I.10 | deliverable | Third-pass acceptance stories | §I.10 | — | — | — | — | — | — | — | — | planned |
| AS13 | story | The Lion-Headed God. | Part I | — | — | — | — | — | — | — | — | planned |
| AS14 | story | The Plague That Learned. | Part I | — | — | — | — | — | — | — | — | planned |
| AS15 | story | The Pass of the Drowned Valley. | Part I | — | — | — | — | — | — | — | — | planned |
| AS16 | story | The Revised King. | Part I | — | — | — | — | — | — | — | — | planned |
| AS17 | story | The Cipher of the Salt Road. | Part I | — | — | — | — | — | — | — | — | planned |
| AS18 | story | The Death-Shaped World. | Part I | — | — | — | — | — | — | — | — | planned |
| I.11 | deliverable | Fourth-pass couplings | §I.11 | — | — | — | — | — | — | — | — | planned |
| I.12 | deliverable | Fourth-pass feedback loops | §I.12 | — | — | — | — | — | — | — | — | planned |
| L53 | loop | Elite overproduction → counter-elites → civil war → elite deaths → (B) fewer elites → stability | Part I | — | — | — | — | — | — | — | — | planned |
| L54 | loop | Population growth → falling wages → immiseration → famine and war → population falls → wages rise | Part I | — | — | — | — | — | — | — | — | planned |
| L55 | loop | Frontier conflict → asabiyya → conquest → luxury → asabiyya decays → a new frontier people conquers | Part I | — | — | — | — | — | — | — | — | planned |
| L56 | loop | Small coalition → private goods → poverty → unrest → purges → smaller coalition | Part I | — | — | — | — | — | — | — | — | planned |
| L57 | loop | Insecure ruler → short horizon → plunder → weaker realm → more insecurity | Part I | — | — | — | — | — | — | — | — | planned |
| L58 | loop | Competitive giving → prestige race → treasuries drained → ruin of one side | Part I | — | — | — | — | — | — | — | — | planned |
| L59 | loop | Irrigation → salinisation → yields fall → abandonment → recovery over centuries | Part I | — | — | — | — | — | — | — | — | planned |
| L60 | loop | Enclosure → dispossessed migrate to cities → cheap labour → more enclosure profit | Part I | — | — | — | — | — | — | — | — | planned |
| L61 | loop | Millenarian fervour → mass abandonment of work → famine → more fervour | Part I | — | — | — | — | — | — | — | — | planned |
| L62 | loop | Theodicy crisis → conversion away → the god acts (desperate) → visible miracle → faith restored | Part I | — | — | — | — | — | — | — | — | planned |
| L63 | loop | Credential inflation → more aspirants → more counter-elites → more examinations demanded | Part I | — | — | — | — | — | — | — | — | planned |
| L64 | loop | Slave raids → captives → slave labour profits → more raids | Part I | — | — | — | — | — | — | — | — | planned |
| I.13 | deliverable | Fourth-pass acceptance stories | §I.13 | — | — | — | — | — | — | — | — | planned |
| AS19 | story | The Soft Dynasty. | Part I | — | — | — | — | — | — | — | — | planned |
| AS20 | story | The Salt of Ages. | Part I | — | — | — | — | — | — | — | — | planned |
| AS21 | story | The River God's Lawsuit. | Part I | — | — | — | — | — | — | — | — | planned |
| AS22 | story | The Greens and the Blues. | Part I | — | — | — | — | — | — | — | — | planned |
| AS23 | story | The Clockwork Guard. | Part I | — | — | — | — | — | — | — | — | planned |
| AS24 | story | The Grief God's Harvest. | Part I | — | — | — | — | — | — | — | — | planned |
| I.14 | deliverable | Fifth-pass couplings, loops and stories | §I.14 | — | — | — | — | — | — | — | — | planned |
| L65 | loop | Famine → poor nutrition in childhood → a weaker adult generation → lower output → famine risk | Part I | — | — | — | — | — | — | — | — | planned |
| L66 | loop | Witch hunt → vengeful ghosts and misfortune → more accusations | Part I | — | — | — | — | — | — | — | — | planned |
| L67 | loop | Sunk cost in a failing war → more losses → more sunk cost | Part I | — | — | — | — | — | — | — | — | planned |
| L68 | loop | Monsoon failure → famine → migration → less pressure | Part I | — | — | — | — | — | — | — | — | planned |
| L69 | loop | Overfishing → stock collapse → fishers turn to raiding or emigration → coastal decline | Part I | — | — | — | — | — | — | — | — | planned |
| L70 | loop | Nativist revival → suppression → martyrs → stronger revival | Part I | — | — | — | — | — | — | — | — | planned |
| AS25 | story | The Witches of the Marsh. | Part I | — | — | — | — | — | — | — | — | planned |
| AS26 | story | The Monsoon That Failed. | Part I | — | — | — | — | — | — | — | — | planned |
| I.15 | deliverable | Sixth-pass couplings, loops and stories | §I.15 | — | — | — | — | — | — | — | — | planned |
| L71 | loop | Faith salience → holy war → more faith salience | Part I | — | — | — | — | — | — | — | — | planned |
| L72 | loop | Industrialisation → pollution and urbanisation → secularisation → less religious opposition to industry | Part I | — | — | — | — | — | — | — | — | planned |
| L73 | loop | Redistributive centre grows → bureaucracy cost → fiscal stress → collapse → local self-sufficiency | Part I | — | — | — | — | — | — | — | — | planned |
| L74 | loop | Insecurity → hoarding → less investment → poverty → banditry → insecurity | Part I | — | — | — | — | — | — | — | — | planned |
| AS27 | story | The Salience of Bread. | Part I | — | — | — | — | — | — | — | — | planned |
| AS28 | story | The Iron Horse. | Part I | — | — | — | — | — | — | — | — | planned |
| I.16 | deliverable | Eighth-pass loops and stories | §I.16 | — | — | — | — | — | — | — | — | planned |
| L75 | loop | Persecution of the gifted → fewer gifted → rarer mages → mages more feared → more persecution | Part I | — | — | — | — | — | — | — | — | planned |
| L76 | loop | Novelty drain → elites abandon a form → it becomes rare → novelty recovers → revival | Part I | — | — | — | — | — | — | — | — | planned |
| L77 | loop | Carrion pulse → vermin and disease → more deaths → more carrion | Part I | — | — | — | — | — | — | — | — | planned |
| L78 | loop | Nation-building → polity identity salience → assimilation → stronger polity identity | Part I | — | — | — | — | — | — | — | — | planned |
| AS29 | story | The Fallen God. | Part I | — | — | — | — | — | — | — | — | planned |
| AS30 | story | The Kingdom Before Us. | Part I | — | — | — | — | — | — | — | — | planned |
| J.1 | deliverable | Waves | §J.1 | — | — | — | — | — | — | — | — | planned |
| W0 | wave | Modifier bus (F9), incidents (F10), interconnection registry (I.1), depth metric script (J.7), `@reads`/`@writes` annota | Part J | F9 modifier bus on every stat read; F10 causality chains; I.1 edge registry; J.7 depth metric; @reads/@writes on every step (scripts/phase_io.py records them); F28 conservation ledger; J.16 catalogue and J.16c generic layer; docs/spec/13-balance-bands.json with scripts/balance_sim.py; dead fields wired: typed war causes on every hostility (sabotage, raid as grudge, tribute, theft, defiance, rivalry, schism, foreign god), WarEnding.BETRAYAL when an ally betrays mid-war, incited_by_son_id, golden_age_since_epoch, celestial influence, outer-being size, world danger, son mercy, creator passions, dedicated structures; levies conserve soldiers | see F9, F10, F28 | see F9, F10, J.16c | section-mechanics, section-biography, map layers, stock charts | see F9, F10 | see F10 | see F9, F10 | tests/unit/test_mechanic_compliance.py; tests/unit/test_interconnection_registry.py; tests/unit/test_depth_metric.py; tests/engine/interconnect/; tests/engine/integration/test_balance_bands.py | done |
| W1 | wave | Time sub-clocks (F1), region environment (F2.1–F2.5), weather on demand (F2.3), seasons (F2.2) | Part J | F1 sub-clocks, F2.1 region and place environment, F2.2 seasons and calendars, F2.3 weather, F2.4 derived fertility and harvest, F2.5 land use, F2.6 ley lines (unassigned in J.1, integrated with its foundation). Cross-wave terms are listed on each F row | see F1–F2.6 | environment:set, seasons:edit, seasons:reorder, weather:force, weather:release, ley:sever, ley:restore, ley:forge, ley:unforge, year:force_notable | section-environment (forge ley lines, held weather, years remembered), section-seasons, chronicle YearStrip, map layers terrain, soil, climate, land use and ley | geography lines with season and weather, mortal land with ground and weather, world header; son tools reorder_seasons, sever_ley, shape_weather | year.*, season.*, land.*, tools.son.shape_weather, tools.son.reorder_seasons | environment_survey (notable years from famine and plague records), ley_lines | tests/engine/environment/test_environment.py; tests/engine/warfare/test_campaign_seasons.py | done |
| W2 | wave | Anatomy and injuries (F4.1–F4.5), healing, conditions, derived capacities; migrate `wound()` → `apply_hits` | Part J | F4.1 body plans, F4.2 injuries with every harm source on apply_hits, F4.3 hits and armour, F4.4 healing, F4.5 conditions, capacities, customs and maimed cohorts. Cross-wave terms are listed on each F row | see F4–F4.5 | see F4–F4.5 | section-body (height and build, plan), section-body-customs, section-maimed | entity detail Body and wounds; son turn divine body | see F4–F4.5 | body_survey (fatal wounds for every violent death, with killer and event; species plans re-read) | tests/engine/body/test_body.py | done |
| W3 | wave | Values, traits, skills, memories, needs (F5–F8); opinion-derived community relations | Part J | F5 values, F5.1 traits, F6 skills, F6/RP2 rust and teaching, F7 memories and opinion, F8 needs and pressures; community_relations.value is now the mean of both sides' opinion (engine/services/community_relations.py, mind_opinion); the twelve-event history became memories (migration c42218f12748). Cross-wave terms are listed on each F row | see F5–F8 | see F5–F8 | section-mind, section-skills, section-memories, section-community-relations | Mind block in entity detail, son turn, bard and deepener | see F5–F8 | mind_survey (personalities from written character), migration c42218f12748 (relation history to memories) | tests/engine/mind/test_mind.py; tests/api/test_bodies.py; mindSections.test.tsx | done |
| W4 | wave | Materials and commodities (F3), extraction and refining chains (6.3), markets and money and trade routes (6.4) | Part J | F3 materials and world materials, 6.3 extraction/refining, 6.4 markets/money/routes (see F3, S6.3, S6.4) | economy_survey, resource_economy, refining, markets, trade_flow, banking | material:*, stock:*, resource:*, route/toll/loan/currency/price levers | EconomyScreen, EntityEconomy, ResourceProfile, RouteAndMarket, MaterialForge | EconomyBlock | economy and trade templates | economy fixups | tests/engine/society/test_economy_depth.py, tests/engine/port_structure/test_route_depth.py | done |
| W5 | wave | Cohorts and labour (F12, 4.1, 4.9), disease type (3.4), settlements (4.2) | Part J | F12 cohorts and labour, 4.1 peoples, 4.9 society, 3.4/F4.6 disease, 4.2 settlements, 7.2 structures | people_cycles, labour_allocation, epidemics, settlement_life, structure phases | people:*, labour:*, disease:*, settlement:*, district:*, structure:* | Demography, Folk, Work, DiseaseCard, SettlementPlan, Structures | folk, needs, sickness, home works lines | peoples.*, society.*, disease.*, settlement.*, structures.* | peoples/society/disease/structure fixups | tests/engine/society/test_*_depth.py, test_structures.py | done |
| W6 | wave | Polity, house, law, offices, claims, succession, legitimacy (4.5–4.8); treaties (5.13) | Part J | 4.5 law, 4.6 polity, 4.7 house, 4.8 oaths, 5.13 treaty, 4.3 faction, 4.10 relations | polity_cycles, house_cycles, treaty_cycles, faction phases, ethnic_relations | law:*, polity:*, office:*, claim:*, house:*, treaty:*, faction:* | Realm, Statecraft, Covenants, treaty builder, Faction | realm context; enact_law, seal_treaty, found_faction | polity.*, houses.*, treaty.*, faction.* | law, dynasty, treaty, faction fixups | tests/engine/polity/test_polity_depth.py, faction.test.tsx | done |
| W7 | wave | Military: unit stacks, movement, logistics, phased battles with terrain and weather, sieges, duels, captives, war aims, | Part J | Part 5 military (5.1-5.12) and 7.3 vessels | campaigns, war_upkeep, prisoners, espionage, vendetta_cycles, seafaring | army:*, war:*, siege:*, military:*, vessel:* | WarRoom, WarMap, ArmyPanel, MilitarySection, VesselCard | military context; 8 son military tools | war.*, seafaring.*, espionage.* | army size, spy network, vessel fixups | tests/engine/warfare/* | done |
| W8 | wave | Faith: doctrine and tenets, zeal dynamics, clergy, relics, afterlife strata, judgement, reincarnation (4.4, 3.3) | Part J | 4.4 cult doctrine and 3.3 afterlife | faith_cycles, religion_spread, schisms, soul_cycles | cult:*, relic:*, soul:*, afterlife:* | Doctrine, Afterlife, StratumEditor | son doctrine and souls; reveal_tenet, open_rebirth_gate | faith.*, afterlife.* | faith fixups | tests/engine/faith/* | done |
| W9 | wave | Culture and knowledge: language barriers, legends with credence, tradition effects, tech graph with holder levels, ideol | Part J | Part 8 culture and knowledge, 7.1 items, 7.4 artworks, F11 rumours | language, legend, tradition, research, ideology, rite, prophecy, item, artwork, rumour cycles | lore:*, research:*, creed:*, rite:*, item:*, art:*, rumour:*, kind:* | Lore panels, LearningSection, TongueAtlas, RumoursSection, LoreForge | mortal context; typed lore tools | lore.*, magic.*, item.*, art.*, rumour.* | lore fixups | tests/engine/lore/* | done |
| W10 | wave | Ecology: species ranges and food web, domestication, beasts (3.2, 3.3a) | Part J | 3.2 species and food web, domestication, 3.3a beasts | creatures, speciation, husbandry, ecology, beast_cycles | species:*, herd:*, beast:*, use_kind:*, people:totem | SpeciesSection, BeastSection, food-web graph, range layer | nature lines; create_species, raise_beast | creatures.*, beasts.*, ecology.* | wilds.typed_nature | tests/engine/cosmos/test_wilds_typed.py | done |
| W11 | wave | Divine: domain hooks for all 40 domains, son goals, standing, divine wounds, avatars, creator passions and taboos, forei | Part J | — | — | — | — | — | — | — | — | planned |
| W12 | wave | Cosmos: star life cycle, world physics wiring, regional leak, phenomena, journey cargo and convoys, typed apocalypse var | Part J | — | — | — | — | — | — | — | — | planned |
| J.2 | deliverable | Data migration | §J.2 | — | — | — | — | — | — | — | — | planned |
| J.3 | deliverable | New enums and bond kinds (summary) | §J.3 | — | — | — | — | — | — | — | — | planned |
| J.4 | deliverable | Rules namespaces (new and extended) | §J.4 | — | — | — | — | — | — | — | — | planned |
| J.5 | deliverable | Pipeline placement and performance | §J.5 | divergence so far: the environment steps sit in the cleanup (environment_survey), growth (environment_derive, ley_lines), sub-engine (harvest) and society (land_use) stages instead of one environment stage, because they must run where their inputs settle; mind steps form the mind stage after aging | — | — | — | — | — | — | — | planned |
| J.6 | deliverable | Testing | §J.6 | — | — | — | — | — | — | — | — | planned |
| J.7 | deliverable | Depth metric: target | §J.7 | scripts/depth_metric.py (A typed attributes read from @reads, B mechanics acting or writing, C coupling edges carried; entity, son, creator, foreign god, war, world, star, route; compared with the J.7 targets) writes docs/spec/13-depth-metric.md | n/a | n/a | n/a | n/a | n/a | n/a | tests/unit/test_depth_metric.py (the published metric must be current) | done |
| J.8 | deliverable | LLM layer | §J.8 | — | — | — | — | — | — | — | — | planned |
| J.9 | deliverable | UI surfaces (summary) | §J.9 | — | — | — | — | — | — | — | — | planned |
| J.10 | deliverable | Second-pass integration addendum | §J.10 | — | — | — | — | — | — | — | — | planned |
| W3+ | wave | F13 mind split, F14 thoughts and emotions, F15 preferences, F16 ethics, F17 dreams and wants, F18 relationships and inte | Part J | — | — | — | — | — | — | — | — | planned |
| W2+ | wave | F23 material physics and tissue layers, F30 effect packages | Part J | F23 material physics, attack resolution, layered armour, tissue layers and injury mechanics; F30 effect packages; god control surface rule (CLAUDE.md rule 6) with the compliance check covering every engine-written table | see F23, F30 | see F23, F30; addiction:set, addiction:immunity, son:power, faith:unsyncretize, resource:mechanic | see F23, F30; AddictionList, ImmunityList, SonPowers, ResourceProfile workings | see F23, F30 | see F23, F30 | see F23, F30 | tests/engine/body/test_strike.py; tests/engine/body/test_tissues.py; tests/engine/body/test_afflictions.py; tests/unit/test_mechanic_compliance.py | done |
| W4+ | wave | F24 production methods, energy, pollution, quality tiers, spoilage; ownership and profits; market access, tariffs, credi | Part J | — | — | — | — | — | — | — | — | planned |
| W5+ | wave | F29 households and dwellings; F26 genetics; F28 conservation ledger (land in W0 as a test harness, completed here) | Part J | — | — | — | — | — | — | — | — | planned |
| W6+ | wave | 4.11 titles; F20 schemes, secrets, hooks, favours, identities; F21 communication and public opinion; F22 belief state; e | Part J | — | — | — | — | — | — | — | — | planned |
| W7+ | wave | Organisation, discipline, ammunition, frontage and reserves, the morale ladder, command and control, spotting, penetrati | Part J | — | — | — | — | — | — | — | — | planned |
| W9+ | wave | Civic tree, institutions, boosts, catch-up, card draws, great people, era scores, dangerous techniques and accidents, re | Part J | — | — | — | — | — | — | — | — | planned |
| W10+ | wave | Flora, husbandry, vermin, procedural beasts, night creatures, pets | Part J | — | — | — | — | — | — | — | — | planned |
| W12+ | wave | 10.9 cosmic physics (derived), star systems, cosmic features, impacts, terraforming, survey levels, life classes | Part J | — | — | — | — | — | — | — | — | planned |
| W13 | wave | F25 gatherings, F27 storyteller, event collections, excavations and sites with rooms | Part J | — | — | — | — | — | — | — | — | planned |
| J.11 | deliverable | Parallel and efficient engine (decision K.8) | §J.11 | — | — | — | — | — | — | — | — | planned |
| J.12 | deliverable | Third-pass integration addendum | §J.12 | — | — | — | — | — | — | — | — | planned |
| W14 | wave | F31 dominion and scales, thrones and magic sites, perceived alignment and worship mode, miracle impressiveness, belief s | Part J | — | — | — | — | — | — | — | — | planned |
| W15 | wave | Spell grammar, magic resources, resistance and dispels, paradigms, myth-coupling, environmental combinations, warping, g | Part J | — | — | — | — | — | — | — | — | planned |
| W16 | wave | Sound-change engine, typology, semantic drift, script evolution, decipherment, pidgins, language policy, non-vocal modal | Part J | — | — | — | — | — | — | — | — | planned |
| W17 | wave | Trait evolution, niches, radiation, trophic flow, coevolution, keystones, feral reversion, biome succession, biogeochemi | Part J | — | — | — | — | — | — | — | — | planned |
| W18 | wave | Desirability, coverage, housing evolution, homelessness, prevention, morphology, turf; caravans, fleets, cargo transport | Part J | — | — | — | — | — | — | — | — | planned |
| W19 | wave | Legal typology, precedent, courts and appeals, registries, jurisdiction conflicts, pardons, outlawry, prisons; recruitme | Part J | — | — | — | — | — | — | — | — | planned |
| W20 | wave | F32 collective behaviour, F33 historiography, F34 storylets, F35 social norms and volition; passions, conviction, persua | Part J | — | — | — | — | — | — | — | — | planned |
| J.13 | deliverable | Fourth-pass integration addendum | §J.13 | — | — | — | — | — | — | — | — | planned |
| W21 | wave | F37 structural-demographic variables, asabiyya, challenge–response, long plans; F38 reciprocity and gift ledgers; kinshi | Part J | — | — | — | — | — | — | — | — | planned |
| W22 | wave | Selectorate and coalitions, legitimacy types and routinisation, time horizon, clientelism, venality, power bases, coup-p | Part J | — | — | — | — | — | — | — | — | planned |
| W23 | wave | von Thünen rings, central places, Boserup, nutrients, perennials, commons and enclosure, game reserves, famine foods; re | Part J | — | — | — | — | — | — | — | — | planned |
| W24 | wave | OOB hierarchy, HQ command range and points, logistics network flow, culmination, theatre allocation; Lanchester attritio | Part J | — | — | — | — | — | — | — | — | planned |
| W25 | wave | Mysticism, millenarianism, theodicy, sacraments, believed against actual afterlife, secularisation; genius loci and cele | Part J | — | — | — | — | — | — | — | — | planned |
| W26 | wave | Art markets, forgery, canon; art movements, clubs, leagues, betting, circus factions; constructs; monster contracts; ast | Part J | — | — | — | — | — | — | — | — | planned |
| W27 | wave | Formation history, irregular seasons, long ecological transformations; cyclic ages; F36 narrative arcs and the drama man | Part J | — | — | — | — | — | — | — | — | planned |
| J.14 | deliverable | Fifth-pass integration addendum | §J.14 | — | — | — | — | — | — | — | — | planned |
| W28 | wave | F39 nutrition, F40 decision biases, F41 purity and castes, F42 luck, charms and witchcraft; idea internalisation | Part J | — | — | — | — | — | — | — | — | planned |
| W29 | wave | Revitalisation, intoxication cultures, body modification, time budgets, naming customs, age-sets; cuisines, taverns, wel | Part J | — | — | — | — | — | — | — | — | planned |
| W30 | wave | Fisheries, chemical industries, insurance, incorporeal property, optics, clocks, games, numeracy; material magic and sym | Part J | — | — | — | — | — | — | — | — | planned |
| W31 | wave | Atmospheric circulation, rain shadows, monsoons, ocean currents, oscillations; launch windows; cosmopolitan cultures | Part J | — | — | — | — | — | — | — | — | planned |
| J.15 | deliverable | Sixth-pass integration addendum | §J.15 | — | — | — | — | — | — | — | — | planned |
| W32 | wave | F43 identity layers and salience; peer groups; contests of wit; claims of deeds; sanctuary; satire and fools | Part J | — | — | — | — | — | — | — | — | planned |
| W33 | wave | F44 technology ceiling and advanced eras (era variants of units, industrial methods, communication media, rocketry route | Part J | — | — | — | — | — | — | — | — | planned |
| W34 | wave | Microbes, symbiosis, dormancy, thermoregulation, senses, plant defences, island rule | Part J | — | — | — | — | — | — | — | — | planned |
| W35 | wave | Writing media, locks, water-lifting, navigation instruments, building materials; saving, exchange rates, economic system | Part J | — | — | — | — | — | — | — | — | planned |
| J.16 | deliverable | Compliance catalogue (architecture rule 6 and decisions 21, 26, 41, 68, 71) | §J.16 | engine/interconnect/compliance.py CATALOGUE (F1, F2, F4–F10 rows: tables, steps, levers, surfaces, contexts, tools, templates, backfill) | n/a | n/a | n/a | n/a | n/a | n/a | tests/unit/test_mechanic_compliance.py (catalogue resolves to real code; every mechanic has steps, written templates, tools, a known backfill and flow categories for conserved writes) | in-progress |
| J.17 | deliverable | Seventh-pass integration addendum | §J.17 | — | — | — | — | — | — | — | — | planned |
| W36 | wave | F45 world-type profiles: every foundation reads its world-type view; the exotic rules of the 17 non-ordinary types | Part J | — | — | — | — | — | — | — | — | planned |
| W37 | wave | F46 biology variants: every foundation reads its biology view; the twelve variants | Part J | — | — | — | — | — | — | — | — | planned |
| W38 | wave | F47 lifecycle ends and decays; fossils, museums and collections, designed landscapes | Part J | — | — | — | — | — | — | — | — | planned |
| J.18 | deliverable | Eighth-pass integration addendum | §J.18 | — | — | — | — | — | — | — | — | planned |
| W39 | wave | F48 prehistory and deep-time runs (genesis integration, the prehistory digest for Fate and the chronicler, the fast-forw | Part J | — | — | — | — | — | — | — | — | planned |
| W40 | wave | F49 transformation graph (all new transformations) with the transformation registry in the compliance test | Part J | — | — | — | — | — | — | — | — | planned |
| W41 | wave | B1 couplings: sign languages, sociolects, rite components, carrion pulses, the heritable gift, ecosabotage, conditions o | Part J | — | — | — | — | — | — | — | — | planned |
| J.16b | deliverable | Compliance catalogue, ninth-pass rows | §J.16b | — | — | — | — | — | — | — | — | planned |
| J.16c | deliverable | Generic lever and surface layer (the compliance guarantee by construction) | §J.16c | engine/interconnect/registry.py, catalog.py (map layer and chart descriptors), guards.py (pins, suppressions and targeted runs block stats, bonds, injuries, healing, conditions, cohorts, values, traits, skills, memories, needs and pressures); db/write_guard.py; services/player/levers.py (lever:run with target, lever:set); api/routers/mechanics.py (acting mechanics, why breakdown, incidents) | every engine step runs guarded | lever:pin, lever:unpin, lever:suppress, lever:unsuppress, lever:run, lever:set, modifier:add, modifier:remove | section-mechanics (ActingMechanics with the five levers, WhyBreakdown); map layers map-layer-*; overview stock charts | entity detail: recent work of context mechanics | n/a | n/a | tests/unit/test_mechanic_compliance.py; tests/engine/interconnect/test_guards.py; e2e/entity.spec.ts | done |
| J.19 | deliverable | Completion contract (decision K.16) | §J.19 | — | — | — | — | — | — | — | — | planned |
| K.1 | decision | Sub-epoch time | Part K | — | — | — | — | — | — | — | — | planned |
| K.2 | decision | Existing worlds | Part K | — | — | — | — | — | — | — | — | planned |
| K.3 | decision | Depiction of harm | Part K | — | — | — | — | — | — | — | — | planned |
| K.4 | decision | Named mortals | Part K | — | — | — | — | — | — | — | — | planned |
| K.5 | decision | Civilization tiers | Part K | — | — | — | — | — | — | — | — | planned |
| K.6 | decision | Per-people view of gods | Part K | — | — | — | — | — | — | — | — | planned |
| K.7 | decision | Reincarnation | Part K | — | — | — | — | — | — | — | — | planned |
| K.8 | decision | Engine tick time | Part K | — | — | — | — | — | — | — | — | planned |
| K.9 | decision | Sensitive acts as data | Part K | — | — | — | — | — | — | — | — | planned |
| K.10 | decision | Mortals replacing gods | Part K | — | — | — | — | — | — | — | — | planned |
| K.11 | decision | Falls and corruption of sons | Part K | — | — | — | — | — | — | — | — | planned |
| K.12 | decision | Belief shaping gods | Part K | — | — | — | — | — | — | — | — | planned |
| K.13 | decision | Technology ceiling | Part K | — | — | — | — | — | — | — | — | planned |
| K.14 | decision | Prehistory length | Part K | — | — | — | — | — | — | — | — | planned |
| K.15 | decision | LLM context size | Part K | — | — | — | — | — | — | — | — | planned |
| K.16 | decision | Integration completeness | Part K | — | — | — | — | — | — | — | — | planned |
| K.17 | decision | Storyteller pacing | Part K | — | — | — | — | — | — | — | — | planned |
| K.18 | decision | Linear or cyclic cosmos | Part K | — | — | — | — | — | — | — | — | planned |
| K.19 | decision | Mechanical harshness | Part K | — | — | — | — | — | — | — | — | planned |
