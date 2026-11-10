# 13 — Depth Expansion: Entities, Behaviours, Interconnection

Status: **proposal, not implemented.** This document is the design that precedes integration (TODO item 1). It inventories the current depth of every entity, then specifies, entity by entity, new attributes, new behaviours and the explicit couplings between them. Integration happens in later waves (Part J). Nothing here overrides a decision in `docs/decisions.md` unless Part K says so.

**Second pass (2026-11-02).** A second research pass (TODO item 2) reviewed this spec against seven reference sets (Part 1R) and folded every gap into the document: new foundations F13–F30, three more entity types (2T.6), "Reference pass" blocks at the end of each entity section, the derived cosmic physics in 10.9, and addenda I.5–I.7 and J.10.

**Third pass (2026-11-02).** The lanes were widened from 7 to 25 with the aim of being deeper than the deepest work in *every* lane (1R.11–1R.13). This added 122 more gaps, about 50 beyond-the-leader mechanics, foundations F31–F35, "Reference pass 3" blocks, a third taxonomy review (2T.7, no new types needed) and addenda I.8–I.10 and J.12.

**Fourth pass (2026-11-02).** The bar moved beyond games to the formal models of history, anthropology, political science, economic geography, operations research, comparative religion and systemic literary worlds (1R.14–1R.16). It added 17 lanes (42 in total), 103 more gaps, foundations F36–F38, "Reference pass 4" blocks, a fourth taxonomy review (2T.8) and addenda I.11–I.13 and J.13.

**Fifth pass (2026-11-02).** The method changed from hand-picked lanes to exhaustive sweeps (1R.17–1R.21): the HRAF Outline of Cultural Materials (all 76 major categories of culture), the Earth-system spheres, a scale matrix and the remaining leading works. It added 40 gaps (none was a fully missing OCM category), foundations F39–F42, "Reference pass 5" blocks and addenda I.14 and J.14. The convergence analysis in 1R.21 explains why further design passes would mostly find granularity rather than new kinds of mechanics.

**Sixth pass (2026-11-02).** Six more standard classifications were swept (1R.22–1R.24): biology, the International Patent Classification, the JEL economics classification, Thompson's motif index with Propp's functions, Brown's human universals and the warfighting functions. It added 27 gaps, most importantly the technology ceiling (F44: worlds can now reach gunpowder, industrial, electrical, information and spaceflight eras), plus identity salience (F43), "Reference pass 6" blocks and addenda I.15 and J.15.

**Seventh pass (2026-11-02).** The spec was audited on axes that domain classifications cannot cover (1R.25–1R.31):

- entity completeness (every type's lifecycle and roles);
- stock and flow balance;
- applicability to every world type (34 since 14-cosmos-types.md) and to twelve non-human biologies (F45, F46);
- architecture compliance: levers, UI, LLM exposure, templates, Fate checks and backfill for every mechanic, enforced by a CI compliance test (J.16);
- a final Dewey Decimal sweep.

Lifecycle ends and decays were completed (F47), and the waves were extended (J.17).

**Eighth pass (2026-11-02).** The relations between parts of the spec were audited (1R.32–1R.38): coupling coverage over 380 subsystem pairs, agency of every actor in every action category, the stability of all 74 feedback loops, the full transformation graph between types (F49), and timescale coverage. The last of these added a simulated prehistory before play (F48). The pass found 29 gaps, all resolved, with addenda I.16 and J.18.

**Ninth pass (2026-11-02).** A regression audit re-ran every earlier audit against the newest content (1R.39). It found 12 detail-level gaps inside F45–F49 and the latest blocks, plus missing compliance rows, all resolved (F45–F49 reference pass 9 blocks, J.16b).

**Tenth pass (2026-11-02).** A confirmation audit of the ninth-pass fixes, including checks against the existing engine code (1R.40). It found 9 issues: two conflicts with running mechanics (the fading rule and the god-death path), four consistency details, and three compliance items. The systemic one was closed by a generic, registry-driven lever and surface layer (J.16c) that guarantees rule 6 for every mechanic by construction. No new kind of mechanic was missing.

Target: a **5–10× increase** in each of three axes for every entity:

1. **Attributes:** typed, engine-read state (not prose).
2. **Behaviours:** engine mechanics that read and write that state.
3. **Interconnection:** typed edges through which one subsystem's state changes another's behaviour, including feedback loops.

The baseline in Part 1 was taken from the code on 2026-11-02 (`backend/src/aerona`, about 122k lines, 60+ engine phases). Each claim about current state has a file reference in the audit notes of Part 1.

---

## Part 0. Ground rules carried into every proposal

These follow from `docs/architecture.md` and `docs/decisions.md`. Every section below obeys them, so they are not repeated per entity.

| # | Rule | Consequence for this design |
|---|---|---|
| G1 | No magic numbers (architecture rule 4) | Every number below is a **default** for a tunable in a named rules namespace. Defaults are written `[default]`. Namespaces are listed per entity and collected in J.4. |
| G2 | Explicit fields, never prose detection (decision 40) | No mechanic may parse descriptions, subtypes or names. Existing regex paths are replaced: function role from subtype (`living_stats.py:38`), resource mechanic hints, natural-law hints, creature traits from description (`fauna.py:28`), "written work" regex. LLM creation tools emit typed enums instead. |
| G3 | Determinism (decision 37) | Every new random draw uses a named `ctx.rng(stream)`. Streams are keyed by entity id plus sub-step, so adding one mechanic never shifts the draws of another. |
| G4 | Every mechanic is automatic, player-overridable and has a UI surface (architecture rule 6) | Each entity section ends with **Player levers** and **UI**. |
| G5 | Engine phases are `async def phase(ctx)` units with no transaction across an await (decisions 23, 72, 75) | Phases stay small. Heavy per-entity loops batch-load through preloaded indexes, as `MilitaryStrength.load` already does. |
| G6 | LLM reads structured state | Agent contexts (`prompts/contexts/*`) gain typed blocks: injuries, needs, opinions, doctrine, treaty terms. The LLM never becomes the source of truth for a number. |
| G7 | Typed rows over JSON for anything the engine queries (spec 01 §14) | High-cardinality state (injuries, memories, modifiers, unit stacks) lives in tables. Small fixed blocks stay as typed Pydantic stats. |
| G8 | Prose fields stay | `description`, `depth`, `fate_note` remain lore. Where this spec turns a prose concept into a mechanic (a mortal's temperament, a species' diet), the typed field becomes canonical and the deepener writes prose *from* it. |
| G9 | Plain narration of harm, behind closed doors (decisions K.3, K.9) | Injuries, punishments, sacrifice, torture and atrocities are typed state. Prompts and engine lines state them plainly at the level of fact ("he lost an eye", "her hand was cut off"), or imply them ("the village was put to the sword", "what was done in that cellar was never spoken of"). They are never described step by step: no anatomical or sadistic detail, nothing done to bodies shown on the page, nothing gratuitous. One shared prompt directive enforces this, and engine line templates follow the same rule. |
| G10 | As if it had always been so (decision K.2) | Existing worlds are upgraded in place with no opt-in profile and without re-running epochs. Everything that can be derived from existing state is backfilled as if the deep rules had always applied. Lore that cannot be backfilled stays exactly as written, and the deep rules govern it from the next epoch on. |
| G11 | Mechanical harshness is one dial (decision K.19) | The rules profile `harshness.profile` (heroic, realistic, brutal; default **realistic**) scales, as one group, the lethality of wounds and infections, the rates of permanent injury, deaths from disease, famine and childbirth, siege starvation, battle and pursuit losses, and the survival bonus of notable figures. Realistic means rates near historical ones: a famous king can die of one arrow. The profile is a set of multipliers over the individual tunables, editable in World Rules; individual tunables can still be overridden. Narration stays under G9 at every setting. |

### 0.1 Notation

- `entity.stat` means a key in the typed stats model (`domain/models/entity_stats.py`). A `table.column` written in backticks is a new or existing table.
- **→** marks an interconnection edge: "A → B: effect". Every edge listed here must exist in the interconnection matrix (Part I).
- **Loop R** is a reinforcing feedback loop and **Loop B** a balancing one. Both are catalogued in I.3.
- `[n]` is a default tunable value; `[a..b]` is a range.

### 0.2 Depth metric

Depth is measured mechanically, so the 5–10× target can be checked (J.7).

- **A (attributes):** the number of typed state fields the engine reads, per entity type. Counted fields are stats keys, typed columns, rows in typed side tables keyed by the entity, and enum-valued flags with an effect.
- **B (behaviours):** the number of distinct engine rules that write state of that entity type.
- **C (couplings):** the number of distinct (source subsystem → target subsystem) edges in which that entity type is the carrier.

A CI script (`scripts/depth_metric.py`, J.7) computes A and B from code annotations (`@reads`, `@writes` on phase functions) and C from the interconnection registry (I.1). The baseline is recorded in Part 1.

---

## Part 1. Baseline: what exists today

The baseline counts below are approximate. A counts engine-read fields only; prose is excluded.

| Entity | A now | B now | C now | Biggest gaps (all detailed in the audits) |
|---|---|---|---|---|
| mortal | 8 (hp, str, agi, int, cha, age, lifespan, role) + ~20 flags | ~25 | ~10 | No body, injuries are only hp, no hp regeneration, no personality/skills/needs in the engine, no sex/fertility, kinship is one bond kind, no wealth, no memory |
| species | 7 + 10 traits | ~15 | ~8 | Aggregate only, no diet/habitat/climate tolerance/size/lifecycle; domestication is one bond |
| spirit | 2 (strength, unrest) | ~6 | ~4 | No soul attributes, no judgement, no reincarnation, no agency |
| people | 7 + society row (18) | ~20 | ~12 | No age structure, health, culture values, government, legitimacy |
| settlement | 4 + society row | ~20 | ~12 | No wealth, infrastructure, districts, tax, crime; city tiers display-only |
| faction | 3 | ~4 | ~4 | No agenda, membership, actions or power contest; kinds are labels |
| cult | 4 | ~8 | ~6 | No doctrine, clergy, finances; zeal never decays |
| law | 2 | ~4 | ~3 | Content prose-only; engine never enacts laws |
| resource | 3 + mechanic | ~10 | ~6 | No quantity, units, extraction labour or refining chain; food/goods tags unread |
| item | 4 | ~8 | ~5 | No material, condition, category, value or provenance |
| structure | 3 | ~8 | ~6 | 3 engine kinds; function role from regex; no upkeep, staff or capacity |
| vessel | 5 | ~5 | ~3 | strangeness unread; no cargo, condition or combat role |
| language | 3 + profile + lexicon | ~10 | ~5 | No intelligibility mechanic, prestige, barrier effects; script type inert |
| legend | 1 + category | ~5 | ~3 | No credence, distortion degree or behavioural effect |
| tradition | 2 | ~2 | ~1 | No effect on its celebrants at all |
| artwork | 2 | ~3 | ~2 | influence never read outside itself |
| knowledge | 2 + branch | ~10 | ~10 | Shared level per record, 8/18 prerequisites, spread cosmetic |
| prophecy | 1 + reading | ~3 | ~3 | Fulfilment LLM-only; no machine-checkable condition |
| event | 1 (severity) | ~4 | ~4 | No duration, footprint, phases |
| army | 4 + row | ~8 | ~6 | Four numbers, no unit types, no movement, supply, terrain or weather |
| war (row) | 15 | ~10 | ~10 | Two parties only, no aims, terms or occupation; several enum values never written |
| celestial | 2 | ~2 | ~2 | influence never read |
| outer_being | 3 | ~4 | ~3 | size never read |
| natural_law | 0 + kind | ~10 | ~8 | No strength, scope, decay; kind from regex |
| region / place | 4 / 3 + map record | ~8 | ~6 | Biome unread; no seasons, weather, rivers, soils; danger rarely harms anyone |
| son | 9 stats + 4 passions + ~25 | ~30 | ~15 | mercy unread, ambition read once; domains thin; no goals; personality prose |
| creator | 5 mood + passions | ~10 | ~8 | Passions display-only |
| foreign god | ~20 | ~10 | ~6 | No goals, no inter-god relations |
| world | ~25 | ~12 | ~10 | danger unread; gravity/atmosphere one scalar each; no seasons; leak not regional |
| star | 4 | ~4 | ~3 | Type matters only through dark/collapsible sets |
| route / journey | ~15 / ~10 | ~8 | ~6 | Reasonably deep already; no cargo, convoy, piracy encounters per journey |

Systemic findings that cut across entities:

1. **Single-roll resolution.** Battles, sieges, quests, duels and taming each resolve as one sum plus one die. There are no phases, no states and no carried-over consequences except hp, morale and score.
2. **Couplings are additive constants.** Most interconnections are "+k to a stat". Few loops exist where a state *changes how another rule behaves* (a law changes what injuries mean, a season changes which units are useful).
3. **The environment is world-level.** Climate era, gravity, atmosphere and leak are per world. Region variation is limited to elevation class and coastal flag. Biomes exist on the map only.
4. **No individual memory.** Nothing remembers who wronged whom except bonds, the 12-event community relation log and blood-feud flags.
5. **Coarse time.** An epoch is 50 years (`time.years_per_epoch`). Everything happens once per epoch, so seasons, campaign years, harvests and diseases have no inner rhythm.
6. **Dead enum values and unread fields.** WarCause, WarEnding.BETRAYAL, `incited_by_son_id`, `golden_age_since_epoch`, celestial influence, outer-being size, son mercy, world danger, creator passions, structure `dedicated_son_id`.

The foundations in Part 2 solve 1–5 once, as shared substrates. The per-entity sections then plug every entity into them. Item 6 is fixed by wiring each value into a mechanic in the relevant section.

---

## Part 1R. Reference comparison and self-review (second pass)

This part records the second research pass (TODO item 2). It does two things:

1. A critical review of this spec's first pass against the "real depth" bar.
2. A gap count against reference games that are known for depth in one area.

Every gap found is resolved inside this document: in a new foundation (F13–F30), in an entity section ("Reference pass" blocks), or in a new entity type (2T.6). No gap is left without a resolution row.

### 1R.1 Self-review of the first pass: weaknesses found

| # | Weakness in the first pass | Why it falls short of real depth | Fixed in |
|---|---|---|---|
| S1 | Personality merged three different things: values, temperament and abilities | Dwarf Fortress-grade minds separate *what one believes* (values), *how one reacts* (facets) and *what one can do* (attributes). Mixing them makes characters one-dimensional. | F13 |
| S2 | Only 11 abilities, no mental attribute set | Analytical ability, memory, patience, focus, intuition, empathy, social awareness, linguistic and spatial sense, musicality and recuperation are missing, so skills have nothing distinct to learn from. | F13 |
| S3 | Stress was the only emotion | There were no typed emotions, thoughts or moods, so "why is she unhappy" had no answer beyond a number. | F14 |
| S4 | No likes or dislikes | Taste is a main source of individual and cultural difference: food, materials, colours, art forms, creatures. | F15 |
| S5 | value_reading(ActKind) was a function without data | Cultures need a stored ethics table (acceptable / frowned upon / unthinkable per act), or the readings are arbitrary. | F16 |
| S6 | Mortals had needs but no life goals | Sons had goals and mortals did not; lives had no arc. | F17 |
| S7 | Relationships were opinions plus kin bonds only | There was no friendship or romance axis, no relationship types and no social interactions that change them. | F18 |
| S8 | Renown and infamy were global | Reputation is local: a hero in one city is a butcher in another. | F19 |
| S9 | Intrigue was a list of faction actions | There were no schemes as objects with agents and phases, no secrets, no hooks and no favours. | F20 |
| S10 | Diplomacy had no communication layer | There were no letters, envoys, delays, interception, forgery, misunderstanding or public opinion. | F21 |
| S11 | The engine decides with perfect information | Rumours (F11) existed, but decisions ignored them. Real depth needs actors to act on what they *believe*. | F22 |
| S12 | Materials had no physics | No melting, ignition or hardness against impact or shear, so fire, forging and armour penetration are guesses. | F23 |
| S13 | Bodies had no tissue layers, bleeding or consciousness | A deep cut and a crushed skull differ by tissue, artery and nerve, not just by "severity". | F23 |
| S14 | Production chains had one recipe each | There were no alternative production methods, no energy and no pollution, so there was no technological transition in industry. | F24 |
| S15 | No social occasions | Feasts, tournaments, hunts, weddings, funerals and councils are where relationships, marriages and plots happen. | F25 |
| S16 | No appearance or genetics | Inheritance was ability averages only; looks, heritable conditions and recognisability were missing. | F26 |
| S17 | No pacing layer | An emergent world needs a deterministic storyteller that modulates pressure, or it oscillates between dull and chaotic. | F27 |
| S18 | No conservation invariants | Population, goods, money and souls could appear or vanish (the audit's army-soldier bug is one example). | F28 |
| S19 | No household level | People live in households with shared wealth, dwellings and dependents. A cohort is too coarse and a house too dynastic. | F29 |
| S20 | Conditions were a flat list | Curses, venoms, diseases, rites and material contacts need one generic effect-package system with transmission, onset and duration, as Dwarf Fortress syndromes have. | F30 |
| S21 | Titles were rejected as entities | Landed and sovereign titles outlive the realms that hold them (de jure kingdoms that can be recreated). That passes the identity test. | 2T.6 (title type) |
| S22 | Art had media but no forms | Cultures own musical, poetic, dance and visual *forms*: named styles with structure. Artworks are instances of forms. | 2T.6 (art_form type) |
| S23 | Knowledge was always true | Wrong theories (four humours, geocentrism, miasma) shape what people do and can be overturned. | 2T.6 (theory type) |
| S24 | Cosmic physics was not derived | Year length, temperature and habitable band were stored values, not consequences of orbit, star mass and atmosphere. | 10.9 |
| S25 | Battle model lacked frontage, organisation, morale states, reserves and command delay | Deep war games treat these as central. | 5.3 reference pass |
| S26 | Economy lacked wages, ownership, investment, corruption, substitution and need tiers | Deep economy games treat these as central. | 4.1, 4.2, 6.3, 6.4 reference passes |
| S27 | Tech lacked a civic tree, boosts by doing, eras, great people and institutions spreading geographically | Deep tech-tree games treat these as central. | 8.4 reference pass |
| S28 | Politics lacked coalitions, casus belli justification, enactment processes, elections, estates' privileges and title hierarchy | Deep political games treat these as central. | 4.6, 4.11, 5.8 reference passes |

### 1R.2 Counting rules

- **Counted:** mechanics that the reference has and Weavers of the Void's current code lacks. Mechanics Weavers of the Void has and the reference lacks (cosmology, gods, Fate, inter-world travel) are not counted.
- **Status columns:**
  - **Code**: — missing, ◐ partial.
  - **13 (first pass)**: — missing, ◐ partial, ● covered.
  - **Resolution**: the section of this document that now resolves the gap.
- **Reference sets:**
  - **R1** Dwarf Fortress: fortress, adventure and legends modes.
  - **R2** cosmic simulators: Universe Sandbox, SpaceEngine, plus Stellaris and Elite Dangerous for cosmic civilisation.
  - **R3** battle-depth war games: Combat Mission, Hearts of Iron IV, Europa Universalis IV, Total War, Mount & Blade.
  - **R4** economy and resource games: Victoria 3, Anno, Factorio, EVE Online, Frostpunk.
  - **R5** tech and knowledge games: Civilization, Stellaris, Europa Universalis IV, Alpha Centauri, Crusader Kings III cultures.
  - **R6** politics, diplomacy and communication games: Crusader Kings III, Victoria 3, Europa Universalis IV, the board game Diplomacy, Democracy.
  - **R7** life simulators: The Sims, RimWorld.
- The comparison is drawn from the design of those games as publicly documented. Weavers of the Void reproduces none of their content: only mechanic *classes* are compared.

### 1R.3 R1 — Dwarf Fortress

| # | Mechanic | Code | 13 | Resolution |
|---|---|---|---|---|
| 1 | Layered geology per region (soil, sedimentary, igneous, metamorphic layers), specific stone types | — | ◐ mineral layers | 6.1 RP (geology column) |
| 2 | Aquifers, cavern layers, an underground sea of magma, a deep underworld | — | — | 6.1 RP (subterranean strata) |
| 3 | Hydrology: rivers with flow, brooks, lakes, salinity, flooding of low ground | — | ◐ river class | 6.1 RP |
| 4 | Temperature physics: melting, boiling, ignition points; fire spread by material | — | — | F23 |
| 5 | Plants as species with seasons, soil needs and products (fibre, dye, brew, herb, alchemy) | — | ◐ crop mix | 3.2 RP (flora) |
| 6 | Good/evil and savagery alignment of regions (haunted, reanimating, blessed lands) | — | ◐ scars, phenomena | 6.1 RP (region alignment axes) |
| 7 | Syndromes: a generic effect system carried by materials, creatures, gases, bites and interactions | — | ◐ conditions | F30 |
| 8 | Procedurally generated monsters (random anatomy, materials, breath, temperament) | — | ◐ beast | 3.3a RP |
| 9 | Night creatures, werebeast and vampire curses spread by bite or desecration | — | — | F30, 3.3a RP |
| 10 | Tissue layers (skin, fat, muscle, bone, nerve, artery), bleeding, motor and sensory nerve loss, internal organs, teeth and digits | — | ◐ parts | F23 |
| 11 | Pain, nausea, dizziness, unconsciousness, exhaustion, bleeding out | — | ◐ pain | F23 |
| 12 | Per-attack physics: momentum, contact area, edge, material yield, layered armour | — | ◐ hits | F23, 5.6 RP |
| 13 | Wrestling: grabs, throws, chokes, joint locks; dodging, parrying, blocking | — | — | 5.6 RP |
| 14 | 19 physical and mental attributes | — | ◐ 11 | F13 |
| 15 | About 50 personality facets independent of beliefs | — | — | F13 |
| 16 | Beliefs/values (about 30) | — | ◐ 14 axes | F13 (extended to 24 axes) |
| 17 | Thoughts and emotions with intensity; short- and long-term memories that change personality over time | — | ◐ memories | F14 |
| 18 | About 30 individual needs (pray, fight, learn, craft, be with family, drink) | — | ◐ 6 | F14 needs extension |
| 19 | Life dreams (create a masterwork, rule, raise a family) | — | — | F17 |
| 20 | Preferences: liked materials, foods, creatures, colours, shapes, art forms | — | — | F15 |
| 21 | Friendships, grudges, lovers, acquaintances with strength and history | — | ◐ | F18 |
| 22 | Skill rust from disuse, learning by demonstration and sparring, teaching | — | ◐ | F6 RP |
| 23 | Quality grades, decorations (encrusted, studded), engravings that depict historical events, maker's marks | — | ◐ quality | 7.1 RP |
| 24 | Strange moods: compulsions to make an artifact; failure leads to madness | — | — | F17 (inspiration) and 7.1 RP |
| 25 | Musical, poetic and dance forms generated per culture | — | — | 2T.6 art_form |
| 26 | Performance troupes, scholars writing books on specific topics | — | ◐ | 7.4 RP, 8.4 RP |
| 27 | Ethics per civilisation (killing, theft, slavery, torture, eating sapients…) with levels | — | ◐ | F16 |
| 28 | Food preparation, brewing, spoilage, vermin in stores, alcohol need | — | — | 6.3 RP, F24 |
| 29 | Hospital work: diagnosis, setting bones, suturing, dressing, crutches, traction | — | ◐ | F23, 7.2 RP |
| 30 | Justice: crimes with witnesses, investigations, interrogation, sentences | — | ◐ punishment | 4.5 RP |
| 31 | Nobles' demands (room quality) and mandates (production orders, export bans) | — | — | 4.6 RP (office demands and mandates) |
| 32 | Room and dwelling quality affecting thoughts | — | ◐ districts | F29 |
| 33 | Ammunition, training injuries, uniforms, patrol routes | — | — | 5.1 RP |
| 34 | Pets bonded to owners, grazing, milking, shearing, eggs, butchery | — | ◐ | 3.2 RP |
| 35 | Every person in history is a historical figure with a full event log | ◐ | ◐ incidents | F10 RP (event collections) |
| 36 | Event collections: abductions, beast attacks, persecutions, purges, insurrections, competitions, performances, processions, ceremonies | — | — | F10 RP, F25 |
| 37 | Abductions of children raised as soldiers, necromancer towers raising undead, vampires infiltrating with false identities | — | ◐ | F20 (identities), 8.6 RP, 5.7 RP |
| 38 | Deity spheres (about 130) with compatible and precluded pairs | ◐ 40 | — | 9.1 RP (domain aspects and compatibility) |
| 39 | Desecration curses from gods | — | — | 9.1 RP, F30 |
| 40 | Ghosts of the unburied with types, put to rest by memorials | ◐ | ◐ | 3.3 RP |
| 41 | Per-site reputation of a character (hero, monster slayer, troublemaker) | — | — | F19 |
| 42 | Sites with structure: towers, vaults, lairs, hamlets, monasteries, camps, with ownership history | ◐ | ◐ | 6.2 RP |
| 43 | Cave-ins and structural support in mines | — | ◐ collapse | 6.3 RP |
| 44 | Sleep, fatigue, thirst, cleanliness (as aggregates at epoch scale) | — | — | F14 needs extension (lifestyle) |
| 45 | Language translation of names: every name has a meaning in its language | ◐ | ◐ | 8.1 RP |

**Count (R1):** 45 gaps. Of these, 17 were missing from the first pass and 28 were partial. All 45 are now resolved.

### 1R.4 R2 — Cosmic simulators and space civilisation

| # | Mechanic | Code | 13 | Resolution |
|---|---|---|---|---|
| 1 | Orbital elements: semi-major axis, eccentricity, inclination, period, resonance | — | — | 10.9 |
| 2 | Year length, seasons and insolation derived from orbit, star mass and luminosity | — | ◐ stored | 10.9 |
| 3 | Planet mass, radius, density, composition (iron, rock, ice, gas fractions) | — | — | 10.9 |
| 4 | Surface temperature from luminosity, albedo and greenhouse effect | — | — | 10.9 |
| 5 | Atmosphere composition and pressure (oxygen, nitrogen, carbon dioxide, methane, exotic) | ◐ 5 levels | ◐ | 10.9 |
| 6 | Magnetosphere and radiation shielding | — | ◐ magnetism | 10.9 |
| 7 | Tectonics, volcanism and their cycles | — | — | 10.9, 6.1 RP |
| 8 | Hydrosphere and cryosphere fractions; sea level change | ◐ sea | — | 10.9 |
| 9 | Stellar evolution by mass, with lifetimes (main sequence, giant, dwarf, neutron star, black hole) | — | ◐ age stage | 10.1 RP |
| 10 | Binary and multiple stars, circumbinary orbits, double sunsets and seasons | — | — | 10.9 (star systems) |
| 11 | Habitable zone computed per system | — | ◐ | 10.9 |
| 12 | Impacts (asteroids, comets) with craters, impact winters, extinctions | — | — | 10.9 (impact events) |
| 13 | Rings, Roche limit, tidal locking computed, tidal heating of moons | ◐ ringed type | ◐ tides | 10.9 |
| 14 | Galactic structure: arms, clusters, nebulae, stellar nurseries, voids | — | — | 10.9 (cosmic features) |
| 15 | Periodic comets with orbits and return epochs | ◐ comet event | ◐ cycle | 10.3 RP, 10.9 |
| 16 | Biochemistry class of life per world (carbon/water, silicon, ammonia, exotic) | — | — | 10.9, 3.2 RP |
| 17 | Habitability per species per climate class | — | ◐ acclimatisation | 4.1 RP, 10.9 |
| 18 | Terraforming over epochs | ◐ climate imposition | — | 10.9 |
| 19 | Megastructures (star-scale works) | ◐ gates, bridges | — | 7.2 RP (cosmic structures) |
| 20 | Space fauna (void leviathans) with migrations | ◐ cosmic mounts | ◐ beast | 3.3a RP (void habitat) |
| 21 | Anomalies and multi-stage archaeological sites of precursors | ◐ previous creation | — | 6.2 RP (excavations) |
| 22 | Fuel, supply and jump range per vessel | ◐ travel resource | — | 7.3 RP |
| 23 | Survey levels per world per observer (detected, surveyed, mapped) | ◐ discovery | — | 10.2 RP |
| 24 | Galactic assembly with resolutions | ◐ federation | — | 4.6 RP (interworld assembly) |
| 25 | Light-delay of news between worlds | — | ◐ rumours | F21 |
| 26 | Rogue planets and wandering bodies | — | — | 10.9 |
| 27 | Aurorae, eclipses, transits computed from geometry | ◐ events | — | 10.9 |

**Count (R2):** 27 gaps (17 missing from the first pass, 10 partial), all resolved.

### 1R.5 R3 — Battle-depth war games

| # | Mechanic | Code | 13 | Resolution |
|---|---|---|---|---|
| 1 | Organisation versus strength: units lose cohesion before they lose men | — | — | 5.1 RP |
| 2 | Morale state ladder (steady, shaken, wavering, routing, broken, rallied) and suppression | — | ◐ | 5.3 RP |
| 3 | Frontage and combat width set by terrain; formations and facing | — | — | 5.3 RP |
| 4 | Reserves, second lines, reinforcement during battle | — | — | 5.3 RP |
| 5 | Command and control: span of control, order delay, misunderstood orders, initiative | — | — | 5.3 RP |
| 6 | Spotting, line of sight, elevation, concealment | — | ◐ scouting | 5.3 RP |
| 7 | Ammunition per stack and resupply | — | — | 5.1 RP |
| 8 | Fatigue and stamina within battle; forced marches | — | ◐ field | 5.1 RP |
| 9 | Supply limit per region (how many soldiers the land can feed) | — | ◐ | 5.1 RP |
| 10 | Zones of control, forts controlling movement, encirclement | — | — | 5.4 RP |
| 11 | Entrenchment and field fortifications built over seasons | — | — | 5.1 RP |
| 12 | Planning bonus for prepared attacks | — | — | 5.3 RP |
| 13 | Armour penetration versus armour value; hard and soft targets | — | ◐ | F23, 5.3 RP |
| 14 | Leader skills by area (fire, shock, manoeuvre, siege) and battle-earned traits | ◐ | ◐ | 5.1 RP |
| 15 | Death of a general shocks morale; standards captured | — | ◐ | 5.3 RP |
| 16 | Casualty classes: killed, wounded, captured, missing, deserted | — | ◐ | 5.3 RP |
| 17 | Field surgeons and evacuation change wounded survival | — | ◐ | 5.3 RP |
| 18 | Combat engineering: pontoons, roads, demolitions | — | — | 5.1 RP |
| 19 | Discipline as a separate stat from experience | — | — | 5.1 RP |
| 20 | Weapon range, rate of fire, accuracy | — | ◐ | 5.3 RP |
| 21 | Deception: feints, false camps, misinformation | — | ◐ ambush | 5.3 RP, F22 |
| 22 | Siege phases with garrison, artillery breach, blockade by sea | ◐ | ◐ | 5.4 RP |
| 23 | Naval: ship classes, weather gauge, boarding, naval supremacy for crossings, amphibious landing penalty | — | ◐ | 5.5 RP |
| 24 | Air superiority over regions (here: flying mounts and skyships) | — | ◐ | 5.5 RP |
| 25 | Equipment capture and battlefield salvage | — | — | 5.3 RP |
| 26 | Production lines for war materiel with efficiency growth | — | ◐ stocks | 5.8 RP |
| 27 | War support and home-front stability | — | ◐ weariness | 5.8 RP |
| 28 | Peace conference where each demand costs war score | — | ◐ | 5.8 RP |
| 29 | Casus belli types and justification time | — | — | 5.8 RP |
| 30 | Coalitions against aggressive expansion | — | — | 4.6 RP |
| 31 | Division templates (standard compositions) | — | ◐ martial style | 5.1 RP |
| 32 | Directional blocking and couched charges in single combat; mounted momentum | — | ◐ | 5.6 RP |
| 33 | Terrain micro-features (ditches, walls, woods edges) | — | ◐ place | 5.3 RP |
| 34 | Time of day and night fighting | — | ◐ | 5.3 RP |
| 35 | Psychological warfare: terror, propaganda, atrocity backlash | — | ◐ | 5.8 RP |

**Count (R3):** 35 gaps (13 missing from the first pass, 22 partial), all resolved.

### 1R.6 R4 — Economy and resource management

| # | Mechanic | Code | 13 | Resolution |
|---|---|---|---|---|
| 1 | Alternative production methods for the same good | — | — | F24 |
| 2 | Wages per job and standard of living per class | — | ◐ | 4.1 RP |
| 3 | Ownership of workplaces (nobles, guilds, state, cult, households) and profit distribution | — | — | 6.3 RP |
| 4 | Investment pools and construction capacity | — | ◐ | 4.2 RP |
| 5 | Market access: share of output that reaches a market | — | ◐ capacity | 6.4 RP |
| 6 | Tariffs, subsidies, embargoes | — | ◐ tolls | 6.4 RP |
| 7 | Substitution between goods (fuel: wood or coal; food types) | — | — | F24 |
| 8 | Tiered population needs that unlock upgrades (Anno-style) | — | — | 4.1 RP |
| 9 | Class promotion when needs are met | — | ◐ mobility | 4.1 RP |
| 10 | Quality tiers of goods | — | ◐ | F24 |
| 11 | Storage, spoilage, perishables, preservation | — | — | 6.3 RP |
| 12 | Energy sources (muscle, water, wind, magic, divine) | — | — | F24 |
| 13 | Pollution and its health effects | — | ◐ slag scar | F24 |
| 14 | Interest rates, credit ratings, bankruptcy states, reserves | — | ◐ | 6.4 RP |
| 15 | Boom and bust cycles; speculation; hoarding during famine | — | — | 6.4 RP |
| 16 | Economic indicators (output, price index, trade balance) | — | — | 6.4 RP, J.9 |
| 17 | Black markets for illegal goods | — | ◐ smuggling | 6.4 RP |
| 18 | Unemployment and underemployment | — | — | 4.1 RP |
| 19 | Corruption and tax farming | — | — | 4.6 RP |
| 20 | Tax types (land, poll, trade, consumption) with collection efficiency | — | ◐ | 4.6 RP |
| 21 | Price elasticity and demand by income | — | — | 6.4 RP |
| 22 | State granaries and famine relief policy | — | — | 4.6 RP (mandates) |
| 23 | Item destruction as a sink | — | ◐ | F28 |
| 24 | Blueprints and designs as tradable knowledge | — | — | 8.4 RP |
| 25 | Survival economy under extreme cold or scarcity (heat as a resource) | — | — | F24 (heat), 4.2 RP |
| 26 | Logistics throughput limits inside a settlement (hauling capacity) | — | — | 4.2 RP |
| 27 | Chartered companies with shares and monopolies abroad | — | ◐ guild | 4.3 RP |
| 28 | Regional price differences driving arbitrage by merchant agents | ◐ | ◐ | 6.4 RP |
| 29 | Tool wear in production | — | ◐ item wear | F24 |
| 30 | Supply shocks propagating through chains with visible bottlenecks | — | ◐ | 6.3 RP, J.9 |

**Count (R4):** 30 gaps (15 missing from the first pass, 15 partial), all resolved.

### 1R.7 R5 — Technology and knowledge trees

| # | Mechanic | Code | 13 | Resolution |
|---|---|---|---|---|
| 1 | Separate civic/social tree (governance, law, philosophy, religion innovations) | — | — | 8.4 RP |
| 2 | Boosts by doing (eureka and inspiration triggers) | — | ◐ need | 8.4 RP |
| 3 | Eras and era scores (golden and dark ages per realm by deeds) | ◐ | ◐ | 8.4 RP |
| 4 | Great people generated from accumulated points by field | — | ◐ | 8.4 RP |
| 5 | Catch-up discount when neighbours know a technique | — | ◐ | 8.4 RP |
| 6 | Card-draw research options | — | — | 8.4 RP |
| 7 | Dangerous techniques with world consequences | ◐ forbidden | ◐ | 8.4 RP |
| 8 | Obsolescence and upgrading of units and buildings | — | — | 8.4 RP, 5.1 RP |
| 9 | Specialised researchers with expertise | — | ◐ | 8.4 RP |
| 10 | Unique projects and wonders gated by techniques | ◐ | ◐ | 7.2 RP |
| 11 | Institutions that spread geographically from an origin and change the cost of everything | — | — | 8.4 RP |
| 12 | Cultural innovations per culture | — | ◐ | 4.1 RP |
| 13 | Wrong theories and paradigm shifts | — | — | 2T.6 theory, 8.4b |
| 14 | Reverse engineering of found artifacts | — | ◐ | 8.4 RP |
| 15 | Experiment accidents | — | — | 8.4 RP |
| 16 | Patronage of scholars by rulers | — | ◐ | 8.4 RP |
| 17 | Printing and copying economics of knowledge | — | ◐ books | 8.4 RP |
| 18 | Censorship and forbidden books | — | — | 8.4 RP |
| 19 | Research agreements and shared research between realms | — | — | 8.4 RP, 5.13 RP |
| 20 | Tech-driven social change (social engineering choices) | — | — | 8.4 RP |
| 21 | Knowledge of geography as a tree branch (cartography quality) | ◐ | ◐ | 8.4 RP |
| 22 | Era-locked capabilities that require several branches together | — | ◐ | 8.4 RP |

**Count (R5):** 22 gaps (9 missing from the first pass, 13 partial), all resolved.

### 1R.8 R6 — Politics, diplomacy and communication

| # | Mechanic | Code | 13 | Resolution |
|---|---|---|---|---|
| 1 | Title hierarchy (barony → county → duchy → kingdom → empire) with de jure territory | — | — | 2T.6 title, 4.11 |
| 2 | Schemes with agents, phases, success odds and discovery | — | ◐ | F20 |
| 3 | Secrets and hooks (strong and weak leverage) | — | ◐ blackmail | F20 |
| 4 | Favours and obligations ledgers | — | — | F20 |
| 5 | Trust as its own diplomatic quantity | — | ◐ component | F18, 4.6 RP |
| 6 | Aggressive expansion and coalitions | — | — | 4.6 RP |
| 7 | Diplomatic capacity (number of relations a realm can maintain) | — | — | 4.6 RP |
| 8 | Crises with escalation, backers and swing parties | — | — | 4.6 RP (diplomatic crises) |
| 9 | Casus belli and claim fabrication | — | — | 5.8 RP, F20 |
| 10 | Estates and interest groups with privileges and loyalty | — | ◐ factions | 4.3 RP |
| 11 | Elections, assemblies, political parties and movements | — | ◐ decision rule | 4.6 RP |
| 12 | Law enactment as a process with progress, obstruction and chance | — | — | 4.5 RP |
| 13 | Council offices with tasks | — | ◐ offices | 4.6 RP |
| 14 | Lifestyle focuses and perks | — | ◐ careers | F17 |
| 15 | Prestige, piety, dread and tyranny as currencies | — | ◐ | F19 |
| 16 | Negotiable vassal contracts | — | ◐ | 4.6 RP |
| 17 | Personal unions and inheritance of foreign titles | — | — | 4.11 |
| 18 | Rivals and nemeses designated | ◐ RIVAL bond | ◐ | F18 |
| 19 | Public opinion and media (criers, broadsheets, propaganda, censorship) | — | ◐ | F21 |
| 20 | Correspondence with delay, interception, forgery, misreading | — | — | F21 |
| 21 | Lying and bad-faith treaties; a reputation for honesty | — | ◐ honour | F21, 5.13 RP |
| 22 | Summits and multi-party congresses | — | — | F25 |
| 23 | Great power status and spheres of influence | — | ◐ | 4.6 RP |
| 24 | Nationalism and separatist movements | — | ◐ revolts | 4.6 RP |
| 25 | Diplomatic etiquette: gifts, insults, precedence | — | — | F21 |
| 26 | Activities that build relationships (feasts, hunts, tournaments) | — | — | F25 |
| 27 | Subject types (vassal, march, tributary, personal union, client) | ◐ tribute | ◐ | 4.6 RP |
| 28 | Policy networks: each policy affects voter groups and other policies | — | — | 4.6 RP |
| 29 | Simultaneous negotiation and betrayal among several parties | — | ◐ | 5.13 RP |
| 30 | Constitutional structures and charters | — | ◐ | 4.6 RP |
| 31 | Hostage and ward diplomacy | — | ● | 5.7 |
| 32 | Information asymmetry in decisions | — | ◐ | F22 |
| 33 | Court with courtiers, positions and grandeur | — | ◐ | 4.6 RP |
| 34 | Inheritance partition splitting realms | — | ◐ law | 4.11 |
| 35 | Religious authority over rulers (investiture, excommunication) | — | ● | 4.4 |

**Count (R6):** 35 gaps (13 missing from the first pass, 20 partial, 2 already covered), all resolved.

### 1R.9 R7 — Life simulation

| # | Mechanic | Code | 13 | Resolution |
|---|---|---|---|---|
| 1 | Typed emotions and moods with sources and durations | — | ◐ stress | F14 |
| 2 | Aspirations and life goals with milestones | — | — | F17 |
| 3 | Short-term wants and fears | — | — | F17 |
| 4 | Two-axis relationships (friendship, romance) with types (best friend, crush, ex, enemy) | — | ◐ | F18 |
| 5 | Social interactions with outcomes (befriend, flirt, insult, comfort, argue, gossip) | — | — | F18 |
| 6 | Appearance and genetics (inherited looks, heritable conditions) | — | ◐ | F26 |
| 7 | Likes and dislikes | — | — | F15 |
| 8 | Households with shared funds, dwellings and dependents | — | — | F29 |
| 9 | Home quality and environment affecting mood | — | ◐ | F29 |
| 10 | Leisure, hobbies, a fun need | — | — | F14, F17 |
| 11 | Clubs and social circles | — | ◐ faction band | F18 |
| 12 | Reputation (good or bad) in a community | — | — | F19 |
| 13 | Career ladders with performance and income | — | ◐ | 3.1 RP |
| 14 | Pregnancy with duration and complications | — | ◐ | 3.1 RP |
| 15 | Affairs, jealousy, divorce | — | ◐ divorce field | F18, F20 |
| 16 | Varied causes of death and ghosts by cause | ◐ | ◐ | 3.3 RP |
| 17 | Storyteller pacing of events | — | — | F27 |
| 18 | Ideology precepts that shape daily life | — | ● tenets | 4.4 |
| 19 | Mental breaks of many kinds | — | ● stress breaks | 3.1 |
| 20 | Inspirations (positive breaks producing great work) | — | — | F14, F17 |
| 21 | Childhood development stages with milestones and upbringing quality | — | ◐ education | 3.1 RP |
| 22 | Old age wisdom and mentoring roles | — | ◐ | 3.1 RP |
| 23 | Social roles in family (head, dependent, carer) | — | — | F29 |
| 24 | Grief and mourning processes | — | ◐ traditions | F14 |
| 25 | Addiction and recovery at the individual level | — | ◐ | F30 |
| 26 | Daily-life lifestyle quality (sleep, hygiene, comfort) as an aggregate | — | — | F14 needs extension |
| 27 | Personal events (birthdays, anniversaries, coming of age) feeding memories | — | ◐ | F25 |
| 28 | Pets and companionship | — | — | 3.2 RP, 3.3a RP |

**Count (R7):** 28 gaps (12 missing from the first pass, 14 partial, 2 already covered), all resolved.

### 1R.10 Total

| Reference set | Gaps (reference has, Weavers of the Void lacks) | Missing from the first pass | Partial in the first pass | Covered by the first pass |
|---|---|---|---|---|
| R1 Dwarf Fortress | 45 | 17 | 28 | 0 |
| R2 Cosmic | 27 | 17 | 10 | 0 |
| R3 Battle | 35 | 13 | 22 | 0 |
| R4 Economy | 30 | 15 | 15 | 0 |
| R5 Tech | 22 | 9 | 13 | 0 |
| R6 Politics and communication | 35 | 13 | 20 | 2 |
| R7 Life | 28 | 12 | 14 | 2 |
| **Total** | **222** | **96** | **122** | **4** |

Partial gaps count fully: a first-pass mechanic that only touched the concept is deepened to the reference's level. Each partial and missing gap now has a specific section. The "RP" marker in the resolution column means a "Reference pass" block at the end of that section.

### 1R.11 Third pass: lane expansion ("deeper than the deepest in every lane")

**Principle.** The target is not to beat one reference. It is to be deeper than the deepest known work **in every lane** at the same time. The third pass therefore:

1. widens the set of lanes from 7 to 25;
2. names the leading works per lane, games and canonical lore alike;
3. counts what the leaders have that this spec (after the first two passes) still lacks;
4. adds **beyond-the-leader** mechanics: depth the leaders do not have. These usually come from coupling the lane with Weavers of the Void's unique layers (gods, Fate, cosmos, afterlife, belief) or with another lane.

Gaps already resolved by the first two passes are not counted again. The resolution column points to third-pass sections ("RP3" marks a "Reference pass 3" block at the end of a section, and F31–F35 are new foundations).

**The 25 lanes and their leaders:**

| # | Lane | Leaders taken as the bar |
|---|---|---|
| R1–R7 | (passes 1–2) world simulation, cosmos, battle, economy, tech, politics, life | Dwarf Fortress, Universe Sandbox, SpaceEngine, Stellaris, Combat Mission, Hearts of Iron IV, Europa Universalis IV, Total War, Mount & Blade, Victoria 3, Anno, Factorio, EVE Online, Civilization, Alpha Centauri, Crusader Kings III, Diplomacy, Democracy, The Sims, RimWorld |
| R8 | God games | Dominions, Black & White, Populous, From Dust, Reus |
| R9 | Mythic cosmology and heroquesting | King of Dragon Pass and Six Ages (Glorantha), Planescape, The Elder Scrolls lore, Malazan Book of the Fallen, Discworld's *Small Gods*, Tolkien's *Silmarillion*, Earthsea |
| R10 | Magic systems | Ars Magica, Dominions magic, Noita, Mage: The Ascension |
| R11 | Language and linguistics | diachronic conlang tools (sound-change appliers), Heaven's Vault, Chants of Sennaar |
| R12 | Evolution and ecology | Species: Artificial Life, Real Evolution; Thrive; SimEarth; Eco; Equilinox |
| R13 | City-building and urbanism | Cities: Skylines, Manor Lords, Caesar III and Pharaoh, Banished |
| R14 | Trade and logistics | Patrician and Port Royale, OpenTTD and Transport Fever, Offworld Trading Company |
| R15 | Epidemics | Plague Inc., Project Hospital |
| R16 | Social simulation and narrative AI | Comme il Faut and Prom Week, Versu, Façade, crowd and threshold models of collective behaviour |
| R17 | Espionage | Sid Meier's Covert Action, Phantom Doctrine, Invisible, Inc. |
| R18 | Law and justice | no game is deep here; the bar is comparative legal history (customary, civil, religious and precedent-based systems) |
| R19 | Procedural history and lore generation | Caves of Qud, Azgaar's map generator, World Anvil and Kanka template sets, Wildermyth |
| R20 | Storylet and event systems | Crusader Kings III events, Stellaris event chains, Fallen London and Sunless Sea (quality-based narrative), Wildermyth |
| R21 | Vehicle and engineering design | Aurora 4X, Kerbal Space Program, From the Depths |
| R22 | Tabletop RPG systems | Pendragon, Burning Wheel, Traveller, GURPS, Ars Magica covenants |
| R23 | Crime and underworld | Empire of Sin, Gangsters: Organized Crime |
| R24 | Demography and migration | demographic-transition and migration-network models |
| R25 | Historiography and collective memory | Dwarf Fortress legends, Caves of Qud's procedural sultans, the historiography of real chronicles (official and folk histories, damnatio memoriae) |

### 1R.12 Third-pass gap tables

Status columns as in 1R.2. "Code" is current code and "1–2" is this spec after the first two passes.

**R8 God games**

| # | Mechanic | Code | 1–2 | Resolution |
|---|---|---|---|---|
| 1 | Spatial dominion: each god's presence as a field per region, spreading from temples, prophets and holy sites, contested between gods | — | ◐ standing (not spatial) | F31 |
| 2 | Dominion scales that change the land (order–turmoil, productivity–sloth, heat–cold, growth–death, fortune–misfortune, magic–drain) | — | ◐ region alignment | F31 |
| 3 | God design trade-offs at creation (dominion strength against magic against body against scales) | ◐ rarity budget | — | 9.1 RP3 |
| 4 | Global enchantments: world-wide persistent spells with upkeep, contested and dispellable | — | ◐ natural laws | 8.6 RP3, 9.5 RP3 |
| 5 | Magic sites found by searching regions with the right path knowledge | — | ◐ place secrets | 6.2 RP3 |
| 6 | Magical resource economy (gems per path) | — | ◐ reagents | 8.6 RP3 |
| 7 | Thrones of power: holy sites that confer cosmic advantage and count toward ascension | — | — | 6.2 RP3, 9.1 RP3 |
| 8 | Perceived alignment of a god from its acts, changing worship mode (love against fear) and the look of its holy sites and its manifestation | — | ◐ standing components | 9.1 RP3 |
| 9 | A divine creature that learns behaviours from its god's reward and punishment | — | ◐ avatars | 9.1 RP3 |
| 10 | Miracle impressiveness: belief gain scales with witnesses, spectacle and need | — | — | 9.1 RP3 |
| 11 | Land manipulation with physics consequences (raise land, redirect rivers, lava) | ◐ terraform lever | ◐ | 6.1 RP3 |
| 12 | Mana cost by proximity to one's dominion | — | — | F31 |

Beyond the leaders:

- Dominion interacts with *belief state* (F22): peoples misattribute miracles to the wrong god when dominions overlap, and gods compete for credit.
- Dominion scales feed the economy, health, war supply and the storyteller at once.
- A god's dominion also shapes the afterlife strata of its realm (3.3).

**R9 Mythic cosmology and heroquesting**

| # | Mechanic | Code | 1–2 | Resolution |
|---|---|---|---|---|
| 1 | Heroquests: mortals enter a mythic realm to re-enact a myth for a boon; deviations alter the myth; failure traps the soul | — | — | 8.2 RP3 |
| 2 | Myths as mechanics: rites gain power by re-enacting a known myth | — | ◐ | 8.6 RP3 |
| 3 | Belief shapes worlds and planes: regions and worlds drift toward their inhabitants' dominant beliefs | — | ◐ alignment moved by acts | 10.2 RP3 |
| 4 | Belief shapes gods: folk beliefs change a god's aspects, appearance and temperament over time | — | ◐ folk beliefs prose | 9.1 RP3 |
| 5 | Mantling and ascension by imitation: a mortal who walks a god's path can join or replace it | ◐ deification by the Creator | — | 9.1 RP3, 3.1 RP3 |
| 6 | Divine servitors (angels, heralds, lesser spirits) in a hierarchy under gods | — | — | 3.3 RP3 |
| 7 | Cosmic offices among gods (Lord of the Dead, Keeper of the Gate) with duties, powers and contests | — | ◐ council | 9.4 RP3 |
| 8 | Discord in creation: a god's dissonant act taints the lineages it touched | — | ◐ curses | 3.2 RP3, F30 |
| 9 | Contested histories (dragon-break-like): two versions of events are canon until resolved | — | ◐ time echoes | 10.6 RP3 |
| 10 | True names with power: knowing a name grants command, hooks or protection | ◐ son true name (prose) | — | F20 RP3 |
| 11 | Geasa: personal taboos laid by gods or seers; breaking one brings doom | — | ◐ oaths | 4.8 RP3 |

Beyond the leaders:

- Heroquests use the actual distorted legends of the simulated world (8.2). A people with a corrupted myth quests on the corrupted version, and the boon reflects the corruption.
- Mantling can be blocked by Fate's verdict and by the Creator, so mortal ambition becomes a three-way conflict.

**R10 Magic systems**

| # | Mechanic | Code | 1–2 | Resolution |
|---|---|---|---|---|
| 1 | Spell grammar: technique × form matrix for designing rites | — | ◐ schools | 8.6 RP3 |
| 2 | Magic resources tied to places and creatures (vis, gems) and their trade | — | ◐ | 8.6 RP3 |
| 3 | Magic research and spell invention in laboratories | — | ◐ | 8.6 RP3 |
| 4 | Magic resistance, penetration, counterspells, dispels and wards in interaction | — | ◐ warding | 8.6 RP3 |
| 5 | Familiars bound to mages | — | — | 3.3a RP3 |
| 6 | Paradigms: magic works according to the caster's belief model | — | ◐ theories | 8.6 RP3 |
| 7 | Warping from long magical exposure | — | ◐ | 8.6 RP3, F30 |
| 8 | Magical orders with a code (law among mages) | — | ◐ faction | 4.3 RP3 |
| 9 | Element and state combinations (wet + lightning, oil + fire) with the environment | — | ◐ weather | 8.6 RP3 |
| 10 | Enchanted items with charges and recharging | — | ◐ | 8.6 RP3 |
| 11 | Longevity magic and its costs | — | ◐ | 8.6 RP3 |

Beyond the leaders:

- Magic paradigms are theories (8.4b) whose correctness is known to the engine. A culture whose magic paradigm is closer to the true natural law of its world gets more reliable rites.
- A son can change that law (9.5), invalidating whole magical traditions at once.

**R11 Language and linguistics**

| # | Mechanic | Code | 1–2 | Resolution |
|---|---|---|---|---|
| 1 | Regular sound change over time, producing cognates and divergence | ◐ dialect sampling | — | 8.1 RP3 |
| 2 | Grammar typology as data (word order, morphology, cases, noun classes, evidentiality, honorifics) | — | — | 8.1 RP3 |
| 3 | Semantic drift and taboo replacement | — | — | 8.1 RP3 |
| 4 | Script evolution chain and script borrowing | ◐ writing systems | — | 8.1 RP3 |
| 5 | Decipherment of dead scripts as a process (bilingual texts, scholars) | ◐ decipherable flag | — | 8.1 RP3 |
| 6 | Phonological adaptation of loanwords | ◐ | — | 8.1 RP3 |
| 7 | Pidgin stage before creoles | — | — | 8.1 RP3 |
| 8 | Language policy (official languages, suppression, revival movements) | ◐ revival | — | 8.1 RP3 |
| 9 | Non-vocal languages (sign, scent, telepathy) for non-human peoples | — | — | 8.1 RP3 |

Beyond the leaders:

- Divine languages: each son has a sacred tongue whose words are rites (true names, F20 RP3).
- Sound change is driven by the simulated contact, migration and prestige history, not by a random walk, so a world's linguistic map is a fossil record of its history.

**R12 Evolution and ecology**

| # | Mechanic | Code | 1–2 | Resolution |
|---|---|---|---|---|
| 1 | Trait evolution under selection pressure | ◐ mutation | ◐ speciation | 3.2 RP3 |
| 2 | Niches and competitive exclusion | — | — | 3.2 RP3 |
| 3 | Adaptive radiation after mass extinctions | — | — | 3.2 RP3 |
| 4 | Trophic energy flow (biomass pyramid) | — | ◐ food web | 3.2 RP3 |
| 5 | Coevolution (predator against prey, host against pathogen) | — | — | 3.2 RP3, 3.4 RP3 |
| 6 | Keystone species and ecosystem services (pollination, soil building) | — | — | 3.2 RP3 |
| 7 | Biogeochemical cycles at world scale (carbon, water, nutrients) | — | ◐ climate dynamics | 10.9 RP3 |
| 8 | Biome succession and fire ecology | — | — | 6.1 RP3 |
| 9 | Feral reversion of domesticated species | — | — | 3.2 RP3 |

Beyond the leaders: selection pressure includes *belief and divinity*. Sacred species are protected and thrive; hunted-for-magic species are selected for concealment; leak drives mutation (existing). So the biosphere evolves under divine and cultural pressure.

**R13 City-building and urbanism**

| # | Mechanic | Code | 1–2 | Resolution |
|---|---|---|---|---|
| 1 | Desirability and land value per district | — | — | 4.2 RP3 |
| 2 | Service coverage by radius (wells, temples, watch, healers, markets) | — | ◐ | 4.2 RP3 |
| 3 | Plots and housing evolution by satisfied services | — | ◐ dwellings | 4.2 RP3 |
| 4 | Homelessness, slum clearance, gentrification | — | ◐ slums | 4.2 RP3 |
| 5 | Fire and crime prevention by coverage | — | ◐ | 4.2 RP3 |
| 6 | Urban morphology (organic, planned grid, wall rings and growth beyond walls) | — | — | 4.2 RP3 |

Beyond the leaders: districts carry *memory* (F33). The quarter where the massacre happened stays cheap and haunted for generations; the temple quarter of a dead god becomes a ruin quarter with cultic squatters.

**R14 Trade and logistics**

| # | Mechanic | Code | 1–2 | Resolution |
|---|---|---|---|---|
| 1 | Caravans and convoys as moving agents with cargo, guards and schedules | — | ◐ route flows | 6.4 RP3 |
| 2 | Transport fleets with aging, maintenance and replacement | — | ◐ | 6.4 RP3 |
| 3 | Cargo-specific transport (perishables, livestock on the hoof, bulk by water) | — | ◐ spoilage | 6.4 RP3 |
| 4 | Port throughput and warehouses for speculation | — | ◐ harbour capacity | 6.4 RP3 |
| 5 | Merchant houses with trading posts in foreign towns | — | ◐ chartered companies | 4.3 RP3 |
| 6 | Market manipulation: cornering and dumping | — | ◐ speculation | 6.4 RP3 |

Beyond the leaders: caravans carry rumours, diseases, art forms and missionaries as cargo of their own (F11, 3.4, 7.5, 4.4), so a trade road is also a road of ideas and plagues, with typed consequences.

**R15 Epidemics**

| # | Mechanic | Code | 1–2 | Resolution |
|---|---|---|---|---|
| 1 | Pathogen trait evolution (transmission, severity, resistance to cold, heat and treatment) | — | ◐ strains | 3.4 RP3 |
| 2 | Vectors (birds, livestock, insects by season, water) | — | ◐ hosts | 3.4 RP3 |
| 3 | Societal response decisions (close ports, quarantine, burn the dead) with costs | — | ◐ quarantine law | 3.4 RP3 |
| 4 | Variolation, vaccination and herd immunity | — | — | 3.4 RP3 |
| 5 | A cure research race | — | ◐ | 3.4 RP3 |
| 6 | Asymptomatic carriers | — | — | 3.4 RP3 |
| 7 | Zoonotic spillover from land clearing and contact with wild species | — | — | 3.4 RP3 |

Beyond the leaders: plagues have gods (Plague-domain sons) who may steer them, cults that worship them, and theories (8.4b) that misread them, which Plague Inc. cannot model.

**R16 Social simulation and narrative AI**

| # | Mechanic | Code | 1–2 | Resolution |
|---|---|---|---|---|
| 1 | Social norms per situation (what is proper at a funeral against a feast) | — | ◐ etiquette | F35 |
| 2 | Volition computed from social rules (each interaction scored by rules) | — | ◐ weighted draws | F35 |
| 3 | Gossip networks: who tells whom | — | ◐ rumours by route | F11 RP3 |
| 4 | Persuasion and argument models (appeals to beliefs, evidence, authority) | — | — | F18 RP3 |
| 5 | Crowd and mob dynamics (threshold models of riots, panic contagion) | — | ◐ uprisings | F32 |
| 6 | Social learning (prestige bias, conformity bias) | — | ◐ value drift | F5 RP3 |
| 7 | Status hierarchies in small groups | — | — | F18 RP3 |

Beyond the leaders: social norms are typed per culture *and* per god (doctrine), and they change with history (F33 memory), so etiquette has a history.

**R17 Espionage**

| # | Mechanic | Code | 1–2 | Resolution |
|---|---|---|---|---|
| 1 | Recruitment by motive (money, ideology, compromise, ego) | — | ◐ | 5.10 RP3 |
| 2 | Network topology: handlers, cells, dead drops, safe houses | — | — | 5.10 RP3 |
| 3 | Codes and ciphers, codebreaking | — | — | F21 RP3 |
| 4 | Moles and mole hunts with false positives | — | — | 5.10 RP3 |
| 5 | Defectors | — | — | 5.10 RP3 |
| 6 | Assassination methods with forensic detection | — | ◐ | 5.10 RP3 |

Beyond the leaders:

- Divine espionage: seers scry (rites), dreams leak secrets (dream_whisper power), and gods spy on each other through mortal agents.
- Prophecies can expose plots before they happen (8.7 conditions).

**R18 Law and justice**

| # | Mechanic | Code | 1–2 | Resolution |
|---|---|---|---|---|
| 1 | Legal system typology (customary, codified, religious, precedent, oracle) | — | — | 4.5 RP3 |
| 2 | Precedent accumulating into case law | — | — | 4.5 RP3 |
| 3 | Courts hierarchy, appeals, advocates as a profession | — | ◐ | 4.5 RP3 |
| 4 | Property registries and contract enforcement | — | — | 4.5 RP3 |
| 5 | Jurisdiction conflicts (church against crown, foreigners) | — | ◐ | 4.5 RP3 |
| 6 | Pardons, amnesties | — | — | 4.5 RP3 |
| 7 | Outlawry and bounties | — | — | 4.5 RP3 |

Beyond the leaders: oaths sworn before gods are enforced by the gods themselves (4.8, F30 desecration and oath curses). Oracle law (divine judgement) is a real mechanic with a son's answer, so justice can be divine, mistaken or bought.

**R19 Procedural history and lore generation**

| # | Mechanic | Code | 1–2 | Resolution |
|---|---|---|---|---|
| 1 | In-world texts with authored bias (the same event told differently per faction) | ◐ historian views (prose) | — | F33 |
| 2 | Lore and secrets as a currency that factions trade for | — | ◐ secrets | F19 RP3 |
| 3 | Procedural heraldry | — | ◐ emblems | 4.7 RP3 |
| 4 | Per-world materials (procedural materials as articles) | — | ◐ catalog | F3 RP3 |
| 5 | Culture-specific dating systems ("year 34 of King X") | — | — | F1 RP3 |
| 6 | Engine-generated plots with stakes | ◐ threads | ◐ | F34 |

Beyond the leaders: every generated text artifact (histories, gospels, epics, laws) is backed by typed state with a measurable distance from the truth, which the player can inspect.

**R20 Storylet and event systems**

| # | Mechanic | Code | 1–2 | Resolution |
|---|---|---|---|---|
| 1 | Typed storylets: preconditions over state, weights, choices, typed outcomes | ◐ opportunities for LLM | — | F34 |
| 2 | Event chains spanning epochs | — | ◐ excavations | F34 |
| 3 | Choices resolved by an LLM agent when selected, otherwise by personality | ◐ | — | F34 |

Beyond the leaders: storylet outcomes are not scripted text. They are typed effects on a simulation with feedback loops, so the same storylet leads to different histories.

**R21 Vehicle and engineering design**

| # | Mechanic | Code | 1–2 | Resolution |
|---|---|---|---|---|
| 1 | Component-based design (hull, propulsion, holds, armour, weapons, wards, quarters) with a mass budget | — | ◐ hull class | 7.3 RP3 |
| 2 | Design lineage, prototypes and refits | — | — | 7.3 RP3 |
| 3 | Component wear and failure rates | — | ◐ condition | 7.3 RP3 |
| 4 | Siege-engine and war-machine designs | — | ◐ unit kinds | 5.1 RP3 |

**R22 Tabletop RPG systems**

| # | Mechanic | Code | 1–2 | Resolution |
|---|---|---|---|---|
| 1 | Passions: intense directed loves, loyalties and hatreds that inspire or break (Pendragon) | ◐ son passions | ◐ facets | F18 RP3 |
| 2 | Acting on beliefs is rewarded and reinforces them (Burning Wheel) | — | — | F17 RP3 |
| 3 | Annual household phase with family events | — | ● sampled years, households | — |
| 4 | Magical covenants as bases with resources | — | ◐ | 4.3 RP3 |

**R23 Crime and underworld**

| # | Mechanic | Code | 1–2 | Resolution |
|---|---|---|---|---|
| 1 | Criminal organisations with hierarchy and rackets (protection, smuggling, gambling, fencing) | — | ◐ bandits | 4.3 RP3 |
| 2 | Turf per district and turf wars | — | — | 4.3 RP3, 4.2 RP3 |
| 3 | Thief-takers and bounty hunters | — | — | 4.5 RP3 |
| 4 | Prisons with conditions, prison gangs and release | — | ◐ prisons | 4.5 RP3 |

**R24 Demography and migration**

| # | Mechanic | Code | 1–2 | Resolution |
|---|---|---|---|---|
| 1 | Migration networks: diasporas, chain migration, remittances | — | ◐ push factors | 4.1 RP3 |
| 2 | Generations with shared formative memories | — | ◐ cohorts | F12 RP3 |
| 3 | Demographic transition (urbanisation and literacy lower fertility) | — | ◐ | 4.1 RP3 |
| 4 | Sex-ratio effects after wars (marriage markets) | — | — | 4.1 RP3 |
| 5 | Role norms per culture (which sex, age and class may hold which roles; fully culture-defined, including matriarchal and egalitarian worlds) | — | ◐ succession gender rule | 4.1 RP3 |

**R25 Historiography and collective memory**

| # | Mechanic | Code | 1–2 | Resolution |
|---|---|---|---|---|
| 1 | Official, folk and foreign histories with typed bias | ◐ historian views | — | F33 |
| 2 | Damnatio memoriae and revisionism | — | — | F33 |
| 3 | Commemoration calendars and collective reliving of anniversaries | — | ◐ traditions | F33 |
| 4 | Founding myths of peoples and realms | ◐ ascension myths | — | F33 |
| 5 | Historical grievances driving politics centuries later (irredentism) | — | ◐ de jure titles | F33 |

### 1R.13 Third-pass totals

| Lanes | Gaps counted | Missing after passes 1–2 | Partial after passes 1–2 | Covered |
|---|---|---|---|---|
| R8–R25 (18 lanes) | 122 | 52 | 69 | 1 |

Grand total over the three passes: **344 gaps** across 25 lanes, every one with a resolution in this document, plus about 50 beyond-the-leader mechanics.

### 1R.14 Fourth pass: beyond games, into the sciences and systemic lore

**Why another widening.** Games are not the deepest models available in many lanes. History, anthropology, political science, economic geography, military operations research and literary worldbuilding contain formal models that no game implements fully. The fourth pass treats those models as the bar. The same rules apply: only gaps left after passes 1–3 are counted, every gap is resolved in this document ("RP4" marks a "Reference pass 4" block), and every lane gets beyond-the-leader mechanics.

| # | Lane | Leaders taken as the bar |
|---|---|---|
| R26 | Historical dynamics (cliodynamics) | Turchin's structural-demographic theory, Goldstone's state breakdown model, Ibn Khaldun's asabiyya cycle, Toynbee's challenge and response, the Seshat databank's variables |
| R27 | Anthropology of kinship, exchange and honour | Mauss (the gift), Lévi-Strauss (alliance theory), Sahlins (big-man and chief, segmentary lineages), potlatch and kula exchange, honour–shame cultures |
| R28 | Political science of regimes | Bueno de Mesquita's selectorate theory, Weber's types of legitimacy, Olson's stationary bandit, elite theory, clientelism, the sale of offices, civil service examinations; the games Imperator: Rome (character power bases), Tropico, Shadow Empire (councils) |
| R29 | Economic geography and agrarian systems | von Thünen rings, central place theory, Boserup's intensification, agrarian cycles, nutrient balance and rotations, transhumance and nomadism, commons and enclosure |
| R30 | Age-of-sail naval simulation | Naval Action, Ultimate Admiral: Age of Sail, Rule the Waves |
| R31 | Expeditions and survival | Darkest Dungeon, Kenshi, The Long Dark, The Oregon Trail |
| R32 | Operational command | Shadow Empire, Command Ops 2, Gary Grigsby's War in the East, Lanchester's laws |
| R33 | Comparative religion | mysticism, millenarian movements, theodicy crises, sacraments, secularisation, genius loci and celestial bureaucracies (Chinese folk religion, Exalted), Warhammer's emotion-fed gods |
| R34 | Systemic literary worlds | Dune, Foundation, A Song of Ice and Fire, The Wheel of Time, Le Guin's Hainish cycle, Bas-Lag, The Witcher |
| R35 | Divination, astrology and dreams | cultural divination systems (augury, astrology, oracle bones), dream cultures and dream interpretation |
| R36 | Arts institutions, markets and sports | art markets and patronage, forgery, canon formation, art movements; circus factions (Blues and Greens), leagues, betting |
| R37 | Education, bureaucracy and meritocracy | imperial examinations, academies, academic freedom, credentials, scholar migration |
| R38 | Constructs and artificial minds | golems and automata in folklore, RimWorld mechanoids, Dwarf Fortress golems |
| R39 | Planet and system formation | accretion physics (snow line, migration of giant planets, heavy bombardment), as modelled in planetary science |
| R40 | Narrative structure and character arcs | Wildermyth arcs, drama managers (Façade), the monomyth and dramatic arc theory |
| R41 | Labour regimes and bondage | corvée, indenture, debt peonage, slave markets and manumission in comparative history |
| R42 | Disaster resilience and relief | disaster preparedness, relief diplomacy, reconstruction cycles |

### 1R.15 Fourth-pass gap tables

**R26 Historical dynamics**

| # | Mechanic | Code | 1–3 | Resolution |
|---|---|---|---|---|
| 1 | Elite overproduction: aspirants to elite positions outgrow positions, which drives intra-elite conflict | — | — | F37 |
| 2 | Popular immiseration: falling real wages as population exceeds land | — | ◐ SoL | F37 |
| 3 | State fiscal distress: expenses outgrow revenue | — | ◐ treasury | F37 |
| 4 | Political stress index combining the three, which predicts instability waves | — | — | F37 |
| 5 | Secular cycles of growth, stagflation, crisis and depression over centuries | — | — | F37 |
| 6 | Asabiyya: frontier peoples gain cohesion, conquerors lose it over generations of luxury | — | ◐ cohesion | F37 |
| 7 | Meta-ethnic frontiers that forge new solidarities | — | — | F37 |
| 8 | Challenge and response: severe but survivable challenges spur innovation | — | ◐ need-driven research | F37 |

Beyond the leaders: the cycles here are not fitted curves but emergent from cohorts, households, offices and wages (F12, F29, 4.6). Gods and cosmic events act as exogenous shocks that real history lacks, so the theory can be *tested* in the world.

**R27 Anthropology of kinship, exchange and honour**

| # | Mechanic | Code | 1–3 | Resolution |
|---|---|---|---|---|
| 1 | Gift economies: obligations to give, receive and return; unreturned gifts create debt and status | — | ◐ gifts in diplomacy | F38 |
| 2 | Competitive feasting and potlatch: destroying or giving wealth for rank | — | ◐ feasts | F38 |
| 3 | Ceremonial exchange circuits (kula) that bind distant communities | — | — | F38 |
| 4 | Kinship systems (patrilineal, matrilineal, bilateral, double descent) with descent groups and terms | — | ◐ inheritance custom | 4.1 RP4 |
| 5 | Marriage alliance rules (cross-cousin preference, clan exogamy, bride price, dowry, bride service) | — | ◐ marriage custom | 4.1 RP4 |
| 6 | Big-man (achieved) against chief (ascribed) leadership | — | ◐ government | 4.6 RP4 |
| 7 | Segmentary lineages: fusion against outsiders, fission inside | — | — | 4.7 RP4 |
| 8 | Honour–shame dynamics (face, avenging shame, public shaming) | — | ◐ honour | F16 RP4 |
| 9 | Sacrifice as exchange with gods (do ut des) | ◐ offerings | ◐ | F38 |

**R28 Political science of regimes**

| # | Mechanic | Code | 1–3 | Resolution |
|---|---|---|---|---|
| 1 | Selectorate and winning-coalition size, which decide public goods against private rewards | — | — | 4.6 RP4 |
| 2 | Types of legitimacy (traditional, charismatic, legal-rational) and the routinisation of charisma after a founder's death | — | ◐ legitimacy | 4.6 RP4 |
| 3 | Roving against stationary bandits: the time horizon of rulers shapes extraction | — | — | 4.6 RP4 |
| 4 | Patron–client networks (clientelism) | — | ◐ favours | 4.6 RP4 |
| 5 | Sale of offices (venality) and sinecures | — | — | 4.6 RP4 |
| 6 | Personal power bases: characters with holdings and troops loyal to them, not to the state | — | ◐ | 4.6 RP4 |
| 7 | Coup-proofing (rotating commanders, parallel guards) | — | — | 4.6 RP4 |
| 8 | Civil service examinations and meritocratic recruitment | — | — | 8.4 RP4 |

**R29 Economic geography and agrarian systems**

| # | Mechanic | Code | 1–3 | Resolution |
|---|---|---|---|---|
| 1 | von Thünen rings: land use by distance to the market town | — | ◐ market access | 4.2 RP4 |
| 2 | Central place hierarchy: market towns emerge at spacings by range of goods | — | — | 4.2 RP4 |
| 3 | Boserupian intensification: population pressure drives agricultural innovation | — | ◐ need-driven research | 6.1 RP4 |
| 4 | Soil nutrient balance (nitrogen-like and phosphorus-like stocks), rotations, fallow, manure | — | ◐ soil fertility | 6.1 RP4 |
| 5 | Perennial crops with maturity times (orchards, vineyards) | — | ◐ plant growth cycle | 6.1 RP4 |
| 6 | Transhumance and nomadic pastoralism with seasonal pastures | — | ◐ nomad camp subtype | 4.1 RP4 |
| 7 | Commons, overgrazing, enclosure | — | ◐ land use | 6.1 RP4 |
| 8 | Hunting reserves and game laws, poaching | — | — | 6.1 RP4 |
| 9 | Famine foods and food storage culture | — | ◐ | 6.1 RP4 |

**R30 Age-of-sail naval simulation**

| # | Mechanic | Code | 1–3 | Resolution |
|---|---|---|---|---|
| 1 | Per-ship damage locations: hull, sails, rigging, rudder, guns, crew | — | ◐ components | 5.5 RP4 |
| 2 | Sailing by wind angle (points of sail), tacking, being in irons | — | ◐ weather gauge | 5.5 RP4 |
| 3 | Crew stations and skills (gunners, topmen, marines); a gunnery rate of fire | — | ◐ | 5.5 RP4 |
| 4 | Leaks, fires and magazine explosions | — | — | 5.5 RP4 |
| 5 | Prizes taken and prize crews; prize money | — | — | 5.5 RP4 |
| 6 | Naval budgets, admiralty politics and naval treaties limiting fleets | — | ◐ | 5.5 RP4 |

**R31 Expeditions and survival**

| # | Mechanic | Code | 1–3 | Resolution |
|---|---|---|---|---|
| 1 | Expedition planning with provisions, light, tools and camping | — | ◐ site rooms | 6.2 RP4 |
| 2 | Stress afflictions and virtues during expeditions | — | ◐ breaks and inspirations | 6.2 RP4 |
| 3 | Quirks acquired from places and events (positive and negative) | — | ◐ traits | 6.2 RP4 |
| 4 | Exposure: cold, wet, hunger and fatigue during travel and survival | — | ◐ attrition | 6.2 RP4 |
| 5 | Party composition roles (scout, healer, guide, fighter) | — | — | 6.2 RP4 |

**R32 Operational command**

| # | Mechanic | Code | 1–3 | Resolution |
|---|---|---|---|---|
| 1 | Order of battle hierarchy (army → corps → division → brigade) with headquarters | — | ◐ sub-commanders | 5.1 RP4 |
| 2 | Headquarters command range and command points | — | ◐ span | 5.1 RP4 |
| 3 | Logistics network: depots, throughput, transport assets, supply points | — | ◐ supply line | 5.1 RP4 |
| 4 | Lanchester attrition (linear for melee, square for massed missiles) | — | — | 5.3 RP4 |
| 5 | Operational pauses and culmination points | — | — | 5.1 RP4 |
| 6 | Strategic reserves and theatre-level allocation | — | ◐ | 5.1 RP4 |

**R33 Comparative religion**

| # | Mechanic | Code | 1–3 | Resolution |
|---|---|---|---|---|
| 1 | Mysticism: personal religious experience that bypasses clergy | — | ◐ visions | 4.4 RP4 |
| 2 | Millenarian movements: end-time prophecies mobilise masses | — | ◐ prophecy, movements | 4.4 RP4 |
| 3 | Theodicy crises: disasters test faith in a just god | — | ◐ plague faith | 4.4 RP4 |
| 4 | Sacraments as life-stage rites with typed protections | — | ◐ traditions | 4.4 RP4 |
| 5 | Believed afterlife against the actual afterlife | — | — | 4.4 RP4 |
| 6 | Secularisation: faith declining with literacy, prosperity and cosmic silence | — | ◐ godlessness | 4.4 RP4 |
| 7 | Genius loci: minor spirits of places (rivers, hearths, crossroads) with offerings | ◐ local gods | — | 3.3 RP4 |
| 8 | Celestial bureaucracy: minor gods in offices, petitions, promotions, demotions | — | ◐ cosmic offices | 3.3 RP4, 9.1 RP4 |
| 9 | Gods fed by specific mortal emotions | — | ◐ domain activity | 9.1 RP4 |

**R34 Systemic literary worlds**

| # | Mechanic | Code | 1–3 | Resolution |
|---|---|---|---|---|
| 1 | One resource that ties ecology, economy, religion and politics (the spice) | — | ◐ cosmic monopoly | 6.4 RP4 |
| 2 | Long-term ecological transformation plans spanning centuries | — | ◐ terraforming | F37, 10.2 RP4 |
| 3 | Multi-generational breeding and lineage plans by secret orders | — | ◐ marriage strategy | 4.7 RP4 |
| 4 | Prescience and its limits (blind spots, competing seers) | — | ◐ prophecy | 8.7 RP4 |
| 5 | Psychohistory: an in-world faction predicts and steers history statistically | — | — | 8.7 RP4 |
| 6 | Irregular, multi-year seasons | — | — | 10.2 RP4 |
| 7 | Cyclic ages that turn and repeat with variations | ◐ previous creation | — | 10.8 RP4 |
| 8 | Biologically different sex and reproduction systems shaping society (ambisexual, sequential, caste-based) | — | ◐ "other" sex | 4.1 RP4 |
| 9 | Punitive bodily remaking as a judicial institution | — | ◐ mutilation punishments | 4.5 RP4 |
| 10 | Monster contracts and professional monster hunters | — | ◐ hunts | 3.3a RP4 |

**R35 Divination, astrology and dreams**

| # | Mechanic | Code | 1–3 | Resolution |
|---|---|---|---|---|
| 1 | Cultural divination systems that guide decisions (auspicious days, augury) | — | ◐ omens | 8.7 RP4 |
| 2 | Astrology: birth under celestial bodies, real or believed influence | — | ◐ celestial influence | 3.1 RP4, 8.7 RP4 |
| 3 | Individual dreams: prophetic dreams, nightmares from trauma, dream visits, dream interpretation | ◐ divine dreams | — | F14 RP4 |
| 4 | Court diviners whose advice shapes rulers' timing | — | — | 8.7 RP4 |

**R36 Arts institutions, markets and sports**

| # | Mechanic | Code | 1–3 | Resolution |
|---|---|---|---|---|
| 1 | Art markets with prices, collectors and patronage competition | — | ◐ patronage | 7.4 RP4 |
| 2 | Forgery of artworks and relics | — | ◐ relic theft | 7.4 RP4 |
| 3 | Canon formation (which works become classics) | — | ◐ renown | 7.4 RP4 |
| 4 | Art movements as rival schools with manifestos | — | ◐ art forms | 4.3 RP4 |
| 5 | Sporting leagues, champions, fandoms and betting | — | ◐ tournaments, arenas | 4.3 RP4 |
| 6 | Circus factions turning into political factions (the Nika-riot pattern) | — | — | 4.3 RP4 |

**R37 Education, bureaucracy and meritocracy**

| # | Mechanic | Code | 1–3 | Resolution |
|---|---|---|---|---|
| 1 | Examinations that recruit officials by merit | — | — | 8.4 RP4 |
| 2 | Credentials and degrees with prestige | — | ◐ ranks | 8.4 RP4 |
| 3 | Academic freedom against orthodoxy | — | ◐ censorship | 8.4 RP4 |
| 4 | Scholar migration toward patrons (brain drain) | — | ◐ migration | 8.4 RP4 |
| 5 | Schools of thought with lineages of masters and disciples | — | ◐ ideologies | 8.4 RP4 |

**R38 Constructs and artificial minds**

| # | Mechanic | Code | 1–3 | Resolution |
|---|---|---|---|---|
| 1 | Constructs with instruction sets (commands, literal interpretation, loopholes) | ◐ golems | — | 3.3a RP4 |
| 2 | Construct decay, maintenance and the master's death | — | — | 3.3a RP4 |
| 3 | Emergent will and rogue constructs | ◐ creature rebellion | — | 3.3a RP4 |
| 4 | Mass-produced constructs as labour and soldiers | — | ◐ golem units | 3.3a RP4 |

**R39 Planet and system formation**

| # | Mechanic | Code | 1–3 | Resolution |
|---|---|---|---|---|
| 1 | Formation from a disc: composition by distance (snow line) | — | ◐ derived composition | 10.2 RP4 |
| 2 | Giant planet migration and bombardment eras | — | ◐ impacts | 10.2 RP4 |
| 3 | Planetary differentiation (core, mantle, crust), which sets magnetism and volcanism | — | ◐ | 10.2 RP4 |

**R40 Narrative structure and character arcs**

| # | Mechanic | Code | 1–3 | Resolution |
|---|---|---|---|---|
| 1 | Character arcs tracked as stages (call, refusal, mentor, threshold, ordeal, return) | — | ◐ dreams | F36 |
| 2 | A drama manager steering toward arc beats within the simulation's freedom | — | ◐ storyteller | F36 |
| 3 | Ensemble arcs (rivals, lovers, mentors in counterpoint) | — | — | F36 |
| 4 | Foreshadowing and payoff bookkeeping | — | ◐ prophecies, threads | F36 |

**R41 Labour regimes and bondage**

| # | Mechanic | Code | 1–3 | Resolution |
|---|---|---|---|---|
| 1 | Corvée: state labour obligations for great works | — | — | 4.9 RP4 |
| 2 | Indenture and debt peonage | — | ◐ debt law | 4.9 RP4 |
| 3 | Slave markets with prices by skill and origin | — | ◐ enslavement | 4.9 RP4 |
| 4 | Manumission paths and freedmen's status | — | — | 4.9 RP4 |

**R42 Disaster resilience and relief**

| # | Mechanic | Code | 1–3 | Resolution |
|---|---|---|---|---|
| 1 | Preparedness (stockpiles, levees, firebreaks, drills) | — | ◐ granaries | 4.2 RP4 |
| 2 | Relief diplomacy (aid as influence) | — | ◐ famine aid memory | 4.2 RP4 |
| 3 | Reconstruction cycles with opportunism (rebuild better or worse) | — | ◐ investment | 4.2 RP4 |

### 1R.16 Fourth-pass totals

| Lanes | Gaps counted | Missing after passes 1–3 | Partial after passes 1–3 |
|---|---|---|---|
| R26–R42 (17 lanes) | 103 | 33 | 70 |

Grand total over four passes: **447 gaps across 42 lanes**, each with a resolution in this document.

### 1R.17 Fifth pass: systematic sweeps instead of hand-picked lanes

**Why the method changes.** Passes 1–4 found 222, 122 and 103 gaps by choosing lanes and their leaders. Hand-picked lanes cannot prove completeness: a lane nobody thought of stays invisible. The fifth pass therefore checks the spec against **exhaustive classifications** that were built to cover a whole domain, and then against the remaining leading works.

| Sweep | Classification used | Why it is exhaustive |
|---|---|---|
| S-A Culture | The Human Relations Area Files' *Outline of Cultural Materials* (OCM), major categories 13–88 | It is anthropology's standard index of everything a society does, built to classify every ethnography ever written |
| S-B Nature | Earth-system science spheres (atmosphere, hydrosphere, cryosphere, lithosphere, biosphere, magnetosphere and space weather) | The spheres partition the physical world |
| S-C Scale | Every mechanic family at every scale (individual, household, settlement, region, polity, world, star system, cosmos) | It detects families missing at some scale |
| S-D Leaders | Deep works not used in passes 1–4: Shadows of Doubt, Disco Elysium, Terra Invicta, Songs of Syx, Workers & Resources: Soviet Republic, Mistborn, the Stormlight Archive, the Kingkiller Chronicle | They complete the leader sets of existing lanes |

### 1R.18 S-A: Outline of Cultural Materials sweep

● means covered after passes 1–4 (with the sections), ◐ partial, and — missing. Every ◐ and — row gets a fifth-pass resolution ("RP5" marks a "Reference pass 5" block, and F39–F42 are new foundations).

| OCM | Category | Status | Covered by | Fifth-pass resolution |
|---|---|---|---|---|
| 13 | Geography | ● | F2, 6.1, 10.9 | — |
| 14 | Human biology | ◐ | F4, F23, F26, 4.1 | **nutrition and diet quality** (F39) |
| 15 | Behaviour processes and personality | ◐ | F13–F14, F17 | **decision biases** (F40); idea internalisation (F13 RP5) |
| 16 | Demography | ● | F12, 4.1, 4.1 RP3 | — |
| 17 | History and culture change | ◐ | F5, F33, F37 | **revitalisation and nativist movements** (4.1 RP5) |
| 18 | Total culture | ● | F5, F16, F35 | — |
| 19 | Language | ● | 8.1 and its reference passes | — |
| 20 | Communication | ● | F11, F21 | — |
| 21 | Records | ● | 7.1, 8.4, F33 | — |
| 22 | Food quest (hunting, fishing, gathering) | ◐ | 3.2, F24 | **fisheries model** and trapping (6.1 RP5) |
| 23 | Animal husbandry | ● | 3.2 RP | — |
| 24 | Agriculture | ● | F2.4, 6.1 RP4 | — |
| 25 | Food processing | ● | F24, 6.3 RP | — |
| 26 | Food consumption | ◐ | F15, F24 | **cuisines, meals, taverns and inns** (4.2 RP5) |
| 27 | Drink, drugs and indulgence | ◐ | F30 | **intoxication cultures and drinking houses** (4.1 RP5, 4.2 RP5) |
| 28 | Leather, textiles and fabrics | ● | F24 | — |
| 29 | Clothing | ● | 7.1 RP | — |
| 30 | Adornment | ◐ | scar rites (8.3) | **body modification, tattoos, cosmetics, jewellery codes** (4.1 RP5) |
| 31 | Exploitative activities | ● | 6.3 | — |
| 32 | Processing of basic materials | ● | F3, F24 | — |
| 33 | Building and construction | ● | 7.2 | — |
| 34 | Structures | ● | 7.2 | — |
| 35 | Equipment and maintenance of buildings | ● | F29, 7.2 | — |
| 36 | Settlements | ● | 4.2 and its reference passes | — |
| 37 | Energy and power | ● | F24 | — |
| 38 | Chemical industries | ◐ | F24 | **dyes, soap, explosives, pharmaceuticals, fertilisers** (6.3 RP5) |
| 39 | Capital goods industries | ◐ | F24 | **optics** (lenses, spectacles, telescopes) (7.1 RP5) |
| 40 | Machines | ◐ | 5.1, 7.3 | **timekeeping devices** (sundials, water clocks, mechanical clocks) (7.1 RP5) |
| 41 | Tools and appliances | ● | 7.1, F24 | — |
| 42 | Property | ◐ | 4.5 RP3, 6.3 RP | **incorporeal property** (rights to songs, rites, designs, names) (6.4 RP5) |
| 43 | Exchange and transfers | ● | F38, 6.4 | — |
| 44 | Marketing | ● | 6.4, brands (6.4 RP4) | — |
| 45 | Finance | ◐ | 6.4 RP | **insurance and risk pooling** (6.4 RP5) |
| 46 | Labour | ● | 4.1 RP, 4.9 RP4 | — |
| 47 | Business and industrial organisation | ◐ | 6.3 RP, 4.4 RP | **cooperatives and mutual societies** (4.3 RP5) |
| 48 | Travel and transportation | ◐ | 6.4, 7.3 | **travel regulation** (passes, border control, guides) (4.6 RP5) |
| 49 | Land transport | ● | 6.4 RP3 | — |
| 50 | Water and air transport | ● | 5.5, 7.3 | — |
| 51 | Living standards and routines | ◐ | F14, F29 | **time budgets** (work, rest, worship, leisure per class) (4.1 RP5) |
| 52 | Recreation | ◐ | F25, 4.3 RP4 | **games of skill and chance as cultural artifacts** (7.4 RP5) |
| 53 | Fine arts | ● | 7.4, 7.5 | — |
| 54 | Entertainment | ● | 7.4 RP, 4.3 RP4 | — |
| 55 | Individuation and mobility | ◐ | 3.1, F19 | **naming customs** (name-giving, taboo names, renaming at life stages) (4.1 RP5) |
| 56 | Social stratification | ◐ | 4.1, 4.9 | **age-sets and age-grades; caste systems with purity rules** (4.1 RP5, F41) |
| 57 | Interpersonal relations | ● | F18, F35 | — |
| 58 | Marriage | ● | 4.1 RP4 | — |
| 59 | Family | ● | F29 | — |
| 60 | Kinship | ● | 4.1 RP4 | — |
| 61 | Kin groups | ● | 4.7 RP4 | — |
| 62 | Community | ● | 4.2, F35 | — |
| 63 | Territorial organisation | ● | 4.6, 4.11 | — |
| 64 | State | ◐ | 4.6 | **citizenship and naturalisation** (4.6 RP5) |
| 65 | Government activities | ◐ | 4.6 RP | **public welfare and poor relief** (almshouses, orphanages, foundling homes) (4.2 RP5, 4.6 RP5); **standard weights and measures** (4.6 RP5) |
| 66 | Political behaviour | ● | 4.6 RP, F32 | — |
| 67 | Law | ● | 4.5 | — |
| 68 | Offences and sanctions | ● | 4.5 | — |
| 69 | Justice | ◐ | 4.6 RP, 4.5 RP3 | **evidence model** (traces, documents, witness reliability) (4.5 RP5) |
| 70 | Armed forces | ● | 5.1 | — |
| 71 | Military technology | ● | 5.1, 5.1 RP3 | — |
| 72 | War | ● | Part 5 | — |
| 73 | Social problems | ● | 4.2, 4.9 | — |
| 74 | Health and welfare | ◐ | 7.2 RP | welfare institutions (with 65) |
| 75 | Sickness | ◐ | 3.4, F23 | **sorcery and witchcraft as believed causes of illness; witch accusations and hunts** (F42) |
| 76 | Death | ● | 3.1, 3.3 | — |
| 77 | Religious beliefs | ◐ | 4.4, 9.1 | **luck beliefs, charms and amulets** (F42) |
| 78 | Religious practices | ◐ | 4.4, 8.6 | **ritual purity and pollution states, purification** (F41) |
| 79 | Ecclesiastical organisation | ● | 4.4 | — |
| 80 | Numbers and measures | ◐ | F1 | **number systems and numeracy** (8.4 RP5); measures (with 65) |
| 81 | Exact knowledge | ● | 8.4, 8.4b | — |
| 82 | Ideas about nature and man | ● | 8.4b | — |
| 83 | Sex | ● | F35 norms, 4.1 RP4 | — |
| 84 | Reproduction | ● | 3.1 RP | — |
| 85 | Infancy and childhood | ● | 3.1 RP | — |
| 86 | Socialisation | ● | 3.1 RP, F5 RP3 | — |
| 87 | Education | ● | 8.4 RP4 | — |
| 88 | Adolescence, adulthood and old age | ◐ | 3.1 RP | age-sets (with 56) |

**Result of S-A:** 76 categories. 49 were already covered, 27 were partial, and none was missing outright. The 27 partial ones yield **28 concrete gaps** (three categories have two; idea internalisation in row 15 and the evidence model in row 69 also appear in S-D and are counted once), all resolved below.

### 1R.19 S-B and S-C: nature and scale sweeps

**S-B Earth-system spheres**

| Sphere | Gaps after passes 1–4 | Resolution |
|---|---|---|
| Atmosphere | prevailing winds and atmospheric circulation; rain shadows; monsoons; climate oscillations (El Niño-like cycles) | 10.7 RP5 |
| Hydrosphere | ocean currents (navigation and coastal climate) | 10.7 RP5 |
| Cryosphere | — (glaciers, ice–albedo, sea level are covered) | — |
| Lithosphere | — (geology, tectonics, formation are covered) | — |
| Biosphere | — | — |
| Magnetosphere and space weather | — (radiation, auroras, flares are covered) | — |
| Orbital dynamics for travel | launch windows from planetary alignment for physical travel methods | 10.4 RP5 |

**S-C Scale matrix.** Mechanic families checked at each scale: economy, politics, culture, ecology, memory, conflict, information.

- The matrix is full at individual, household, settlement, region, polity and world level.
- At **star-system level**, interworld assemblies (4.6 RP) and the cosmic market cover politics and economy, but **culture** and **memory** had no system-level carrier. The new resolution is **cosmopolitan cultures** (10.4 RP5): shared culture spread along routes, with its own art forms, lingua francas and system-level accounts.
- At **cosmos** level, the families are carried by the Creator, the pantheon and the doom clock.

### 1R.20 S-D: remaining leading works

| Work | What it has that the spec lacked | Resolution |
|---|---|---|
| Shadows of Doubt | a forensic evidence model (traces, documents, timelines, alibis) for investigations | 4.5 RP5 |
| Disco Elysium | ideas internalised over time (a thought cabinet: incubation, then permanent effects with side effects) | F13 RP5 |
| Terra Invicta | launch windows and travel cost by orbital alignment; public opinion per nation | 10.4 RP5 (opinion covered by F21) |
| Songs of Syx | species-specific needs and preferences per city race | covered (F15, 4.1 RP3) |
| Workers & Resources: Soviet Republic | commuting: workers travel to workplaces, which limits labour by distance | 4.2 RP5 |
| Mistborn | magic bound to materials (powers from consuming or wearing specific metals) | 8.6 RP5 |
| Stormlight Archive | emotion spirits that manifest around strong emotions | 3.3 RP5 |
| Kingkiller Chronicle | sympathy: magic through links between similar or once-joined things | 8.6 RP5 |

### 1R.21 Fifth-pass totals and convergence

| Pass | Method | Gaps found |
|---|---|---|
| 1 | first design | (baseline) |
| 2 | 7 lanes, 20 leaders | 222 |
| 3 | 18 more lanes | 122 |
| 4 | 17 lanes of formal models and systemic lore | 103 |
| 5 | exhaustive sweeps (OCM, Earth system, scale matrix) and 8 remaining works | **40** (28 from S-A, 6 from S-B, 1 from S-C, 5 from S-D not counted elsewhere) |

**Total: 487 gaps over five passes, all resolved in this document.**

**Convergence.** The exhaustive culture sweep found *no OCM category missing outright*. Every one of the 76 categories of human culture now has a typed carrier in the spec, and the remaining gaps were refinements inside partially covered categories. The nature sweep found only atmospheric and oceanic circulation, and the scale sweep found one empty cell. This is the signature of category-level completeness: further passes would mostly find **granularity inside existing mechanics** (more act kinds, more thought kinds, finer coefficients). Those are best found during integration by tests, balance runs and the depth metric (J.7), rather than by more design passes. New *kinds* of mechanics remain possible, and the acceptance stories and the interconnection explorer (J.9) are the tools to surface them during integration.

### 1R.22 Sixth pass: further exhaustive classifications

The fifth pass swept culture, nature and scale. The sixth pass applies the standard exhaustive classifications of six more domains:

| Sweep | Classification | Domain it partitions |
|---|---|---|
| S-E Biology | the tree of life (domains and kingdoms), life-history theory, symbiosis types, ethology, physiology and the senses, biogeography | living nature |
| S-F Technology | the International Patent Classification, sections A–H | all technical activity |
| S-G Economics | the Journal of Economic Literature classification, A–Z | all economic phenomena |
| S-H Narrative | Thompson's Motif-Index of Folk-Literature (classes A–Z) and Propp's 31 narrative functions | the building blocks of stories |
| S-I Human behaviour | Donald Brown's list of human universals | behaviours found in every society |
| S-J Warfare | the warfighting functions (command and control, intelligence, fires, movement and manoeuvre, protection, sustainment), plus engineering, medical, civil affairs and military culture | all military activity |

For each sweep, every class is checked against the spec after passes 1–5. Only the classes with gaps are listed. Every class not listed is covered by existing sections. A full class-by-class covered-by listing is generated in W0 by the depth-metric tooling (J.7) from the interconnection registry, so it stays current as integration proceeds.

### 1R.23 Sixth-pass gap tables

**S-E Biology**

| # | Class | Gap | Resolution |
|---|---|---|---|
| 1 | Microorganisms (bacteria, fungi, yeasts) beyond pathogens | decomposers and soil microbiota, which set the nutrient cycling rate; domesticated fermentation cultures (yeasts, starters) as heritable assets | 3.2 RP6 |
| 2 | Symbiosis | typed species relations: mutualism, commensalism, parasitism (non-disease parasites such as ticks and lampreys), mimicry | 3.2 RP6 |
| 3 | Ethology: dormancy | hibernation, aestivation and seasonal dormancy, which change raid and hunting patterns by season | 3.2 RP6 |
| 4 | Physiology: thermoregulation | ectothermy against endothermy: cold-blooded species and peoples slow in cold seasons and regions | 3.2 RP6, 4.1 RP6 |
| 5 | Senses | sensory modalities per species and people (sight range, night vision, smell, hearing, echolocation, magnetic sense, spirit sight), which drive detection, spotting and ambushes | 3.2 RP6 |
| 6 | Plant defences | thorns, toxins, allelopathy (plants suppressing neighbours), carnivorous plants | 3.2 RP6 |
| 7 | Biogeography | the island rule (dwarfism and gigantism on islands), endemism, relict populations | 3.2 RP6 |

**S-F Technology (IPC sections)**

| # | Section | Gap | Resolution |
|---|---|---|---|
| 1 | H (electricity), and modern parts of B, F, G | **a technology ceiling**: the tech graph stops at pre-modern, magic and cosmic branches. The genesis wizard already has a technology setting (`genesis_settings.technology`), so the world must support gunpowder, steam, industrial chemistry, electricity, telecommunication, flight, computation and non-magical spaceflight | F44 |
| 2 | B (printing and writing) and D (paper) | writing media: clay, wax, bark, papyrus, parchment, paper, metal plates; durability, cost and copy speed | 7.1 RP6 |
| 3 | B (packaging) | containers (amphorae, barrels, sacks, crates, jars), which affect spoilage, breakage and transport capacity | 6.4 RP6 |
| 4 | E (locks and safes) | locks, keys, vaults, seals and security against theft schemes | 7.1 RP6 |
| 5 | F (pumps and water-lifting devices) | shadufs, waterwheels, screws and pumps, which gate irrigation on terraces and the drainage of deep mines | 7.2 RP6 |
| 6 | G (navigation instruments) | compass (needs the world's magnetosphere, 10.9), astrolabe, log-line and charts, which set navigation accuracy | 7.3 RP6 |
| 7 | C04 (cements and concrete) | lime mortar, hydraulic concrete and fired brick as building materials with different durability, cost and underwater use | F3 RP6 |

**S-G Economics (JEL classes)**

| # | Class | Gap | Resolution |
|---|---|---|---|
| 1 | D9 (intertemporal choice) | household saving against consumption by time preference (the patience facet, the culture, security), which drives capital accumulation | 6.4 RP6 |
| 2 | F3 (international finance) | exchange rates between currencies, money changers, bills of exchange | 6.4 RP6 |
| 3 | P (economic systems) | allocation systems other than markets: **redistributive palace and temple economies**, command economies, manorial economies, gift economies (F38) as the polity's dominant system | 4.6 RP6 |
| 4 | L2 (firm organisation) | vertical integration (merchant houses owning whole chains), putting-out systems | 6.4 RP6 |
| 5 | Z3 (tourism) | travel for leisure and curiosity to wonders, baths and sights (beyond pilgrimage) | 6.4 RP6 |

**S-H Narrative (Thompson classes and Propp functions)**

| # | Class or function | Gap | Resolution |
|---|---|---|---|
| 1 | H (tests: riddles, contests of wit) | non-violent contests with stakes: riddle games, poetry duels (flyting), debates, games of skill, trials of wisdom | F18 RP6 |
| 2 | R (captives and fugitives: asylum) | the right of sanctuary in temples and the asylum of fugitives with hosts, under hospitality norms | 4.4 RP6 |
| 3 | X (humour: the licensed fool) | jesters and satirists with a licence to mock rulers; satire as a typed act with reduced punishment and political effect | 4.6 RP6 |
| 4 | Propp 24 (unfounded claims of a false hero) | taking credit for another's deed; verification of claims; impostor heroes | F19 RP6 |

The other 19 Thompson classes and 30 Propp functions are generated by existing typed mechanics. For example, absentation is a journey, interdiction is a geas or taboo, the donor's test is a storylet with a spirit or beast donor, branding is an injury or divine mark, unrecognised arrival is a false identity, and transfiguration is an appearance change.

**S-I Human universals**

| # | Universal | Gap | Resolution |
|---|---|---|---|
| 1 | Self-image and in-group identity | **identity layers and salience**: every mortal and cohort holds several identities (people, faith, class, settlement, house, guild, age-set) whose salience shifts with events and decides which lines conflicts follow | F43 |
| 2 | Play (children's play and peer groups) | peer groups and play in childhood shape facets, friendships and later loyalties | 3.1 RP6 |

All other universals in the list (about 300 items, such as gossip, rites of passage, incest avoidance, mourning, proverbs, reciprocity, territoriality, tool-making and weaving) are covered.

**S-J Warfare**

| # | Function | Gap | Resolution |
|---|---|---|---|
| 1 | Military culture | unit identity and battle honours (named regiments with histories, honours on standards, esprit de corps) | 5.1 RP6 |
| 2 | Civil–military aftermath | veteran settlements and land grants; veterans' associations as a political bloc | 5.1 RP6 |

### 1R.24 Sixth-pass totals and convergence

| Pass | Gaps found |
|---|---|
| 2 | 222 |
| 3 | 122 |
| 4 | 103 |
| 5 | 40 |
| 6 | **27** (7 biology, 7 technology, 5 economics, 4 narrative, 2 human universals, 2 warfare) |

**Total over six passes: 514 gaps, all resolved.**

Twelve exhaustive or standard classifications have now been swept: OCM culture, Earth-system spheres, scale, biology, IPC technology, JEL economics, Thompson motifs, Propp functions, human universals, warfighting functions, plus the 42 lanes. The one structural gap of this pass was the **technology ceiling** (F44). The rest were refinements inside covered classes.

### 1R.25 Seventh pass: auditing the spec itself on orthogonal axes

The domain sweeps of passes 5–6 converged: no standard classification produced a missing category. The seventh pass checks the spec along axes that no domain classification covers. These axes find gaps of *structure*, not of topic:

| Audit | Question | Why it is orthogonal to the domain sweeps |
|---|---|---|
| A1 Entity completeness | does every entity type have creation, change, end, agency, memory, economic, conflict, faith and environmental roles, plus player levers and a UI? | a topic can be covered while one entity in it lacks a lifecycle stage |
| A2 Stock and flow | does every accumulating quantity have both a source and a sink? | missing sinks cause runaway growth, and missing sources cause dead stocks |
| A3 Applicability | does every mechanic say what it does on each world type (34 since 14-cosmos-types.md) and for non-human biologies? | mechanics written for an ordinary world silently break on a gas giant or for an incorporeal people |
| A4 Architecture compliance | does every mechanic satisfy architecture rule 6 (automatic, player override, UI) and decisions 21, 26, 41, 68 and 71 (typed tools, prompts in `prompts/`, Fate review, rule snapshots, English templates with localisation)? | the first passes specified mechanics but not always their levers, surfaces and narrative templates |
| A5 Universal knowledge | does the Dewey Decimal Classification (100 divisions, the most-used universal classification of knowledge) expose any topic not yet covered? | the last domain check, from a library rather than a science |

### 1R.26 A1: entity completeness matrix

Columns:

- **Cr**: creation
- **Ch**: change over time
- **End**: death, dissolution, loss
- **Ag**: agency (it decides or acts)
- **Me**: memory and history
- **Ec**: economic role
- **Co**: conflict role
- **Fa**: faith or divine role
- **En**: environment coupling
- **Lv**: player levers
- **UI**: UI surface

● covered; n/a where the aspect does not apply; any other mark points to its resolution.

| Entity | Cr | Ch | End | Ag | Me | Ec | Co | Fa | En | Lv | UI |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mortal | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| species | ● | ● | ● | ● (instinct) | n/a | ● | ● | ● | ● | ● | ● |
| beast | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| spirit | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| disease | ● | ● | F47 (eradication) | n/a | ● | ● | ● | ● | ● | ● | ● |
| people | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| settlement | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| polity | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| house | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| title | ● | ● | ● | n/a | ● | ● | ● | ● | ● | ● | ● |
| faction | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| cult | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| law | ● | ● | ● | n/a | ● | ● | ● | ● | ● | ● | ● |
| army | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| treaty | ● | ● | ● | n/a | ● | ● | ● | ● | ● | J.16 | J.16 |
| trade_route | ● | ● | ● | n/a | ● | ● | ● | ● | ● | ● | ● |
| region | ● | ● | ● | n/a | ● | ● | ● | ● | ● | ● | ● |
| place | ● | ● | ● | n/a | ● | ● | ● | ● | ● | ● | ● |
| resource | ● | ● | ● | n/a | ● | ● | ● | ● | ● | ● | ● |
| item | ● | ● | ● | n/a | ● | ● | ● | ● | ● | ● | ● |
| structure | ● | ● | ● | n/a | ● | ● | ● | ● | ● | ● | ● |
| vessel | ● | ● | ● | n/a | ● | ● | ● | ● | ● | J.16 | J.16 |
| artwork | ● | ● | ● | n/a | ● | ● | ● | ● | ● | J.16 | J.16 |
| art_form | ● | ● | ● | n/a | ● | ● | ● | ● | ● | ● | ● |
| language | ● | ● | ● | n/a | ● | ● | ● | ● | ● | ● | ● |
| legend | ● | ● | ● | n/a | ● | ● | ● | ● | ● | J.16 | J.16 |
| tradition | ● | ● | ● | n/a | ● | ● | ● | ● | ● | J.16 | J.16 |
| knowledge | ● | ● | ● | n/a | ● | ● | ● | ● | ● | ● | ● |
| theory | ● | ● | F47 (oblivion) | n/a | ● | ● | ● | ● | ● | J.16 | ● |
| ideology | ● | ● | F47 (decline) | n/a | ● | ● | ● | ● | ● | J.16 | J.16 |
| rite | ● | ● | F47 (loss) | n/a | ● | ● | ● | ● | ● | J.16 | J.16 |
| prophecy | ● | ● | ● | n/a | ● | ● | ● | ● | ● | J.16 | J.16 |
| event | ● | ● | ● | n/a | ● | ● | ● | ● | ● | J.16 | J.16 |
| phenomenon | ● | ● | ● | n/a | ● | ● | ● | ● | ● | J.16 | J.16 |
| natural_law | ● | ● | ● | n/a | ● | ● | ● | ● | ● | J.16 | J.16 |
| outer_being | ● | ● | F47 (banishment) | ● | ● | ● | ● | ● | ● | J.16 | J.16 |
| celestial | ● | ● | ● | n/a | ● | ● | ● | ● | ● | J.16 | J.16 |
| son *(record)* | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| creator *(record)* | n/a | ● | n/a | ● | ● | ● | ● | ● | ● | ● | J.16 |
| foreign god *(record)* | ● | ● | ● | ● | ● | ● | ● | ● | ● | J.16 | J.16 |
| star *(record)* | ● | ● | ● | n/a | ● | ● | ● | ● | ● | J.16 | J.16 |
| world *(record)* | ● | ● | F47 (end states) | ● (living worlds) | ● | ● | ● | ● | ● | J.16 | J.16 |
| route *(record)* | ● | ● | ● | n/a | ● | ● | ● | ● | ● | J.16 | J.16 |
| journey *(record)* | ● | ● | ● | n/a | ● | ● | ● | ● | ● | J.16 | J.16 |

**A1 result:** 6 lifecycle gaps (all *End* stages) and 38 lever and UI cells across 20 entities. The foundations F1–F43 also lacked levers and UI surfaces in their own sections; these are added in J.16.

### 1R.27 A2: stock and flow audit

All countable or accumulating quantities were listed with their sources and sinks. Most balance already (population, goods, money, essence, faith, dominion, leak, doom, pollution, soil nutrients, knowledge, materials, species, languages, souls). The unbalanced ones:

| Stock | Source | Missing | Resolution |
|---|---|---|---|
| ideology adherents | spread | decline and extinction | F47 |
| rite knowledge | design, revelation | loss when practitioners and texts vanish | F47 |
| disease presence | spillover, mutation | eradication | F47 |
| favours owed | gifts, help | expiry and forgetting | F47 |
| local reputation | deeds, rumours | decay without new deeds | F47 |
| secrets' value | creation | obsolescence (subject dead, truth public) | F47 |
| prestige, dread, tyranny | acts | decay | F47 |
| war weariness | war | recovery in peace | F47 |
| warping | magical exposure | slow fading away from magic | F47 |
| magic site output | site yield | site exhaustion and renewal | F47 |
| thrones of power | fixed at world birth | creation and destruction | F47 |
| outer beings | leak peaks | banishment and destruction | F47 |
| worlds | birth | end states | F47 |

**A2 result:** 13 unbalanced stocks, of which 8 are new (5 overlap with A1).

### 1R.28 A3: applicability audit

**World types.** Of the 18 world types in `domain/enums/world.py`, only the ordinary world was implicitly assumed by passes 1–6. The ringed and tidally locked types were partially handled (ring shadows, the terminator). The other 17 need explicit rules for every foundation family (regions, light, seasons and weather, food, materials, fire and water, disease and body, war, travel, settlement). → **F45**. Spec 14 (14-cosmos-types.md) later added 16 world types, including the moon archetypes; their F45 rows are in the table below.

**Biologies.** Peoples and species are not all humanoid, terrestrial and mortal. Twelve biological variants need explicit rules for bodies and harm, sustenance, reproduction, technology and culture, war, disease and death:

- incorporeal, aquatic, aerial, subterranean, hive, plant-like, construct, ageless, shapeshifting, gaseous, crystalline, undead.

→ **F46**.

**A3 result:** 17 world-type rule sets and 12 biology rule sets were missing.

### 1R.29 A4: architecture compliance audit

- **Rule 6 (automatic, override, UI):** 43 foundations and 20 entity sections, plus cross-cutting sections (4.8–4.10, 10.7–10.9), lacked an explicit player lever, a UI surface or both. → **J.16** compliance catalogue.
- **Decision 21 (tool metadata) and J.8:** new agent tools were named in general terms only. → J.16 lists the LLM exposure (context block, tools) per section.
- **Decision 71 (English templates and localisation):** new incident kinds need template keys. → J.16 lists the template families.
- **Decision 41 (Fate review of creations):** the new creatable types need Fate checks. → J.16 lists them.
- **Decision 68 and G10 (snapshots and backfill):** each new table needs a backfill rule. → J.16 lists them.
- **Guard:** an automated **compliance test** extends the existing route ↔ caller coverage test. It makes the catalogue enforceable (J.16 last part).

### 1R.30 A5: Dewey Decimal sweep

All 100 divisions (000–990) were checked. Three topics surfaced that no earlier pass covered:

| Division | Topic | Resolution |
|---|---|---|
| 060–069 (museums and collections) | museums, cabinets of curiosities, collections as institutions | 7.2 RP7 |
| 560–569 (palaeontology) | fossils and deep time: bones of extinct species and of previous creations as finds that feed theories and legends | 6.2 RP7 |
| 710–719 (landscape architecture) | designed gardens, parks, sacred groves and hunting parks as built landscapes | 7.2 RP7 |

Every other division maps to existing sections. For example, 310 statistics is the census technique, 390 customs is F35, and 590 animals is 3.2.

### 1R.31 Seventh-pass totals and the guarantee

| Audit | Gaps |
|---|---|
| A1 entity completeness | 6 lifecycle gaps + 38 lever/UI cells |
| A2 stock and flow | 8 new (13 total with A1 overlaps) |
| A3 applicability | 29 rule sets (17 world types, 12 biologies) |
| A4 compliance | the compliance catalogue (J.16) for every section without levers, UI, templates, Fate checks or backfill |
| A5 Dewey | 3 |

**Guarantee.** Completeness is now argued on five independent bases:

1. **Domain completeness:** 42 lanes and 12 standard classifications (OCM, Earth-system spheres, scale, biology, IPC, JEL, Thompson, Propp, human universals, warfighting functions, Dewey).
2. **Entity completeness:** the A1 matrix has no empty cell.
3. **Balance:** every stock has a source and a sink (A2, F47).
4. **Applicability:** every foundation has rules for every world type and biology (F45, F46).
5. **Compliance:** every mechanic has a lever, UI, LLM exposure, template, Fate check and backfill (J.16).

The guarantee is made **ongoing** by CI: the compliance test, the conservation tests (F28), the depth metric and the loop finder (I.1) run on every change during integration. Any new mechanic that lacks one of these fails the build.

### 1R.32 Eighth pass: auditing interconnection, agency, stability, transformation and time

The seventh pass audited each entity and stock on its own. The eighth pass audits **relations between parts of the spec**:

| Audit | Question |
|---|---|
| B1 Coupling coverage | for every ordered pair of the 20 subsystems, is there a typed coupling where one is meaningful? |
| B2 Agency coverage | can every actor type act in every action category where it makes sense? |
| B3 Loop stability | does every reinforcing loop have a brake that is itself a specified mechanic? |
| B4 Transformation coverage | can every meaningful change of an entity from one type into another happen? |
| B5 Timescale coverage | is every mechanic family represented at every timescale, from a battle phase to a cosmic age? |

### 1R.33 B1: coupling coverage over 20 subsystems

The subsystems are:

- body, mind, social life, household, demography, economy, polity, law and justice, intrigue, communication, war;
- faith, magic, knowledge, culture, language, ecology, environment, gods, cosmos.

That gives 380 ordered pairs. Each pair was checked against the couplings of I.2, I.5, I.8, I.11, I.14 and I.15 and the entity sections. About 300 pairs carry typed couplings. About 70 pairs have no meaningful coupling (for example language → cosmos, or law → material physics), and they are listed as intentionally empty in the registry, so the loop finder does not flag them. Seven pairs had a meaningful coupling that was missing:

| From → to | Missing coupling | Resolution |
|---|---|---|
| body → language | deaf, mute and tongueless communities form **sign languages** | 8.1 RP8 |
| body → magic | rite components need **bodily functions** (speech for spoken components, hands for gestures, sight for inscriptions) | 8.6 RP8 |
| body → ecology | mass deaths feed **scavenger and vermin booms** and disease | 3.2 RP8 |
| social life → language | social networks make **sociolects** (class, caste, guild and court speech) | 8.1 RP8 |
| demography → magic | the **magical gift** as a heritable trait, so the share of the gifted is a demographic quantity | F26 RP8 |
| intrigue → ecology | **ecological sabotage** (releasing pests, burning forests, poisoning fisheries, salting fields covertly) | F20 RP8 |
| environment → intrigue | conditions that **shape scheme success** (night, fog, storms, festivals, crowds, plague panic) | F20 RP8 |

### 1R.34 B2: agency coverage

The actors are mortal, household, house, faction, cult, polity, people, settlement, army, beast, spirit, son, foreign god, outer being and the Creator. The action categories are economic, diplomatic, military, religious, cultural, intrigue, personal and environmental.

Every actor had verbs in every meaningful category except three cells:

| Actor × category | Missing | Resolution |
|---|---|---|
| army × diplomatic | **field diplomacy** by commanders: parleys, local truces, surrender terms, exchanges of the dead, safe conducts, without the polity's direct order | 5.8 RP8 |
| spirit × cultural | spirits and ancestors as **teachers**: songs, rites and lore revealed by the dead, place spirits and servitors to the living | 3.3 RP8 |
| beast × cultural | sapient beasts as **lore keepers**: dragon-like beings with long memories that hold accounts (F33) and teach or bargain with knowledge | 3.3a RP8 |

### 1R.35 B3: loop stability

All 74 loops in I.3, I.6, I.9, I.12, I.14 and I.15 were checked. Every reinforcing loop names a brake, and every brake was checked for being a specified mechanic. Four brakes were named but not yet specified:

| Loop | Brake named | Resolution |
|---|---|---|
| L33 art form prestige | form exhaustion | 7.5 RP8 (fashion and novelty cycles) |
| L37 deep mining | sealing the deep | 6.1 RP8 (sealing caverns and breaches) |
| L63 credential inflation | office creation | 4.6 RP8 (creating and abolishing offices) |
| L69 overfishing | rights and closures | 6.1 RP8 (closed seasons and protected waters) |

Balancing loops were checked for **failure modes** (overshoot, oscillation, collapse). Each balancing loop's delay is now a rule (`loops.delay.*`), so balance tests can detect oscillation (J.18).

### 1R.36 B4: transformation coverage

Every meaningful transformation of one type into another was enumerated. The full table is in F49. Fourteen transformations were missing:

- a god falling to mortality;
- a people losing sapience;
- a cult becoming a people;
- a polity forging a people;
- a phenomenon growing into a world;
- a living world ascending as a god;
- a star or celestial body raised to godhood;
- an ideology sacralised into a cult;
- a cult secularised into an ideology;
- a beast founding a species;
- an outer being entering the pantheon as a foreign god;
- a son corrupted into an outer being;
- a house growing into a people;
- a colossal corpse becoming a place.

### 1R.37 B5: timescale coverage

Mechanic families were checked at these scales:

- battle phase
- day and night
- season
- year
- generation
- epoch
- era
- age of the world
- cosmic cycle

One gap: **deep time before play**. Dwarf Fortress generates centuries of history before the player arrives. Weavers of the Void's genesis writes a cosmology by LLM but does not *simulate* prehistory, so new worlds start without organically grown language families, ruins, extinct species, dynasties and grudges. → **F48**.

### 1R.38 Eighth-pass totals

| Audit | Gaps |
|---|---|
| B1 coupling coverage | 7 |
| B2 agency coverage | 3 |
| B3 loop stability | 4 |
| B4 transformation coverage | 14 |
| B5 timescale coverage | 1 |
| **Total** | **29** |

These are new mechanics, so they are comparable to the mechanic counts of passes 2–7. The number rises from 17 to 29 because three of the five audits (B2, B4, B5) open axes never examined before: the transformation graph alone contributes 14. On the axes already swept (domains, entities, stocks), the count is zero.

### 1R.39 Ninth pass: regression audit of the newest content

Passes 7 and 8 opened new axes and added new content: F45–F49, the "Reference pass 7" and "8" blocks, and the J.16 catalogue itself. A new section can have the same kinds of holes that the earlier audits closed elsewhere. The ninth pass therefore **re-runs every earlier audit** against that content, together with the pass-5 and pass-6 blocks for compliance:

- A1 entity completeness
- A2 stock and flow
- A3 applicability to world types and biologies
- A4 compliance
- B1 coupling
- B2 agency
- B3 loop stability
- B4 transformation
- B5 timescale

**Findings:**

| # | Audit | Content | Gap | Resolution |
|---|---|---|---|---|
| 1 | A1 | F49 god → mortal | the fallen son's record status, its worshippers, its agent mode and the fate of its soul at mortal death were unspecified | F49 RP9 |
| 2 | A1 | F49 son → outer being | the son record's end state and its loss of agent turns were unspecified | F49 RP9 |
| 3 | A1 | F49 people → species | the mapping of the people's records (settlements, languages, titles, memories) was incomplete | F49 RP9 |
| 4 | B4 | F49 star → god | the consequence of the star-god's death for its star was missing (its birth was specified, its end was not) | F49 RP9 |
| 5 | A3 | F48 prehistory | prehistory was written for ordinary worlds only; realms of the dead, dream worlds, palaces, generation ships and void pockets need their own kind of prehistory | F48 RP9 |
| 6 | A4 (G10) | F48 prehistory | the rule for existing worlds was missing: simulating a prehistory for a world with written lore could contradict that lore | F48 RP9 |
| 7 | A3 | 8.6 RP8 rite components | components were tied to the humanoid body; incorporeal, construct, aquatic, hive and gaseous casters need mappings | F46 RP9 |
| 8 | A3 | F40 decision biases | biases were written for humanlike minds; constructs, hive minds and ageless peoples need their own profiles | F46 RP9 |
| 9 | A3 | 3.2 RP8 carrion pulse | worlds without scavenger fauna (asteroids, void pockets, ice and dead realms) need a rule for what happens to the dead | F45 RP9 |
| 10 | A2 | 3.3a RP8 beast lore | a lore-keeping beast's accounts had a source but no sink: what happens to them at its death | 3.3a RP9 |
| 11 | A2 | 8.1 RP8 sociolects | sociolects formed but never faded | 8.1 RP9 |
| 12 | A2 | 5.8 RP8 field diplomacy | field agreements had no end conditions | 5.8 RP9 |
| 13 | A4 | F48, F49 | no J.16 rows (levers, UI, LLM exposure, templates, backfill) | J.16b |
| 14 | A4 | all pass-5 to pass-8 blocks inside entity sections | the features were specified, but their levers, LLM tools and template families were not listed. Affected: taverns, welfare, commuting, cuisines, evidence, citizenship, fisheries and closures, chemistry, insurance, incorporeal property, optics, clocks, games, numeracy, material magic, sympathy, emotion spirits, sign languages, sociolects, rite components, carrion, the gift, ecosabotage, field diplomacy, spirit teachers, beast lore, novelty, offices, sealing, museums, gardens, fossils | J.16b |

**The other audits found nothing new.** B1 found no new coupling missing, B3 found that the new loops L75–L78 have specified brakes, and B5 found no gap.

**Totals:** 12 mechanic-level gaps (rows 1–12) and 2 compliance gaps (rows 13–14, which together add 30 catalogue rows in J.16b), all resolved below. The mechanic-level gaps are details inside new content, not missing kinds of mechanics. This is the expected shape of a regression audit: new content carries its own small holes, and they are closed by the same audits. A tenth, confirmatory regression of these fixes is planned as part of W0's compliance test, which runs automatically on every change.

### 1R.40 Tenth pass: confirmation audit of the ninth-pass fixes

Every fix of 1R.39 was re-checked against all audits (A1–A5, B1–B5). In addition, each fix was checked against the **existing engine code** for rule conflicts, since a fix that is consistent inside the spec can still contradict a mechanic that already runs.

| # | Check | Finding | Resolution |
|---|---|---|---|
| C1 | code conflict | the fallen son's existence "held at the floor" contradicts the existing fading rule (`death.fading_threshold` [10], `death.fading_death_epochs` [3] in `rules/registry/death.py`), which would kill every fallen son within three epochs | F49 RP10 |
| C2 | A4 (decision 26) | the fallen son's turn with the mortal tool set needs its own prompt variant in `prompts/` | F49 RP10 |
| C3 | code conflict | the corrupted son was to skip corpse and shade, but the existing `god_death()` (`engine/gods/god_death.py`) always creates a corpse place, a god shade and a resurrection order | F49 RP10 |
| C4 | A2 (F28 conservation) | people → species moves population out of the people stock into species abundance, but the conservation ledger had no flow for it | F49 RP10 |
| C5 | consistency with 10.9 | the star-god's death "dims the star by 30%", but star luminosity is *derived* from mass and age (10.9), so a stored change would be overwritten | F49 RP10 |
| C6 | A3 | the star-god's corpse is "a phenomenon in the sky", but phenomena had only region footprints | 10.6 RP10 |
| C7 | A3 | prehistory fallbacks: a generation ship created without a source world, and a mirror world whose twin does not exist yet | F48 RP10 |
| C8 | A4 (catalogue hygiene) | J.16b repeated the F43 row already in J.16, and 1R.39 stated a row count that did not match the table | J.16b (row removed), 1R.39 (count corrected) |
| C9 | A4 (systemic) | J.16 and J.16b list the bespoke levers of foundations and of sections that lacked them. Sections that already had generic levers (people, settlement, cult, polity, army…) received many reference-pass sub-mechanics without a lever of their own. For example: kinship systems, legitimacy types, the selectorate, millenarian movements, theodicy, expeditions, the OOB and HQs, age-sets, body modification, time budgets. Enumerating levers one by one cannot be proven complete | J.16c (a generic, registry-driven lever and surface layer that covers every mechanic by construction) |

**Totals:** 9 findings. Two are conflicts with existing code (C1, C3), four are consistency or applicability details (C4–C7), and three are compliance (C2, C8, C9). C9 is systemic. Its resolution replaces case-by-case compliance with a generic guarantee, so later additions are covered automatically.

**Trend of the regression audits:** 12 (ninth pass) → 9 (tenth pass), and the tenth pass's systemic fix (J.16c) removes the class of compliance findings that produced most of the remaining ones.

---

## Part 2. Shared foundations

Each entity in Parts 3–10 depends on these substrates. They are what turns isolated "+k" effects into an interconnected simulation. One shared model of the body, one model of values, one environment and one modifier bus mean that a change in any subsystem reaches every other one through the same channels.

### F1. Time: seasons, sampled years and campaign turns

**Problem.** One epoch is 50 years, so anything that happens on a scale of years or seasons collapses into one roll.

**Design.** The tick stays one epoch. Inside it, the engine adds three nested sub-clocks that are evaluated only where a mechanic needs them. This keeps cost bounded.

| Clock | Granularity | Count per epoch | Used by |
|---|---|---|---|
| `sample_year` | one year | `time.sampled_years` [5] drawn deterministically from the epoch's years | harvest, disease seasons, births, market volatility, weather extremes |
| `campaign_season` | one season of one year | `campaigns.seasons_per_war_epoch` [6] per active war | army movement, battles, sieges, supply, attrition |
| `season` (of the year) | one of the world's seasons | 2–6 per world (F2.2) | weather, harvest, migration, festivals, sky visibility |

- **Sampled years.** Each epoch, `ctx.rng("years")` picks N distinct years in the epoch. Systems that need yearly variance evaluate those N years and scale the result to the epoch by `years_per_epoch / N`. The worst sampled year is kept as a named **notable year** (`notable_years` table: world, year, kind, magnitude), for example "the Year of Ash Rain". It becomes a chronicle line, can become a legend through the existing legendification path, and is read by traditions (F5: a fast day that commemorates the hungry year).
- **Campaign seasons.** Wars no longer fight "one battle per epoch". Each active war runs K campaign seasons, and each season has a real season of the year (F2.2) and a weather draw (F2.3). Battles happen when armies meet (Part 5).
- **Engine cost.** A cost budget (`engine_budget.max_sub_steps_per_epoch` [400]) caps the total of campaign seasons and sampled-year evaluations. When the cap is exceeded, fewer sampled years are used and the rest are extrapolated. A counter `ctx.count("sub_steps_extrapolated")` records this.
- **Chronicle years.** The existing chronicle-year spreading (`time.year_pace_divisor`) is replaced by real years whenever an event comes from a sampled year or campaign season, so lines read "In the third winter of the war…".

#### F1 reference pass 3: dating systems and calendars per culture

- Each people, polity and cult may use its own **era system** (`dating_systems`: holder, kind, anchor incident, unit): regnal years ("year 34 of King X"), a founding era ("year 412 since the city's foundation"), a religious era ("since the god's descent"), or cycles of a celestial body (comet returns).
- Chronicle lines, in-world texts (F33) and agent contexts render dates in the speaker's system. The UI shows the absolute world year alongside.
- A calendar reform (a civic technique or a cult decision) is an incident: it can shift festivals and cause disputes between cults.

### F2. Environment substrate

#### F2.1 Region environment (new typed table `region_environment`)

Every region gets a mechanical environment profile, computed once from the map at world birth and then changed by climate, disasters, magic and work. The map cells already carry elevation, moisture, water, coastal flag and biome. Region aggregates are computed from them, so the map and the engine finally share one geography.

| Field | Range | Source / meaning |
|---|---|---|
| `biome_mix` | shares of `Biome` (10) | already computed for prompts; now mechanical |
| `dominant_terrain` | `TerrainKind` enum (below) | derived from biome mix plus features |
| `elevation_mean`, `roughness` | 0–100 | from cells; roughness = elevation variance |
| `forest_cover` | 0–100 | biome mix (wet lowland/hills) × humidity, reduced by clearing (F2.5) |
| `wetland` | 0–100 | wet lowland plus river delta |
| `river_class` | none/stream/river/great_river | from the flood/routing layers that already exist in `cartography/flood.py` and `roads.py` |
| `coast_kind` | none/cliff/beach/harbour_site/reef | coastal cells and elevation |
| `soil` | `SoilKind`: thin, loam, clay, sand, volcanic, peat, salt, ash, crystal, bone (world-type soils) | world type + biome + volcanic events |
| `soil_fertility` | 0–100 | replaces the region `fertility` stat as the base; `fertility` becomes derived (F2.4) |
| `temperature_band` | frozen/cold/temperate/warm/hot/searing | latitude (cell y) + elevation + world type + climate era |
| `rainfall` | 0–100 | moisture + coast + climate era |
| `seasonality` | 0–100 | world axial tilt (F2.2) × latitude |
| `disease_load` | 0–100 | warmth × wetland × population density × sanitation (settlement) |
| `mineral_layers` | set of `MaterialKind` with richness 0–100 | seeded from terrain (mountains → ores, volcanic → obsidian/sulfur, crystal worlds → crystal) |
| `magic_density` | 0–100 | the existing region `magic` stat, now also raised by ley convergence (F2.6) |
| `passability` | per `MovementMode` 0–100 | derived (F2.4) |
| `defensibility` | 0–100 | roughness + river + forest + chokepoints |
| `scar` | set of `ScarKind` with depth: battlefield, plague_ground, salted_earth, burned, crater, haunted, blighted, leak_wound | written by wars, plagues, disasters, horror |

`TerrainKind`: plain, steppe, forest, jungle, marsh, hills, mountains, high_pass, desert, tundra, ice_sheet, volcanic, coast, island, river_valley, canyon, underground, crystal_field, flesh (living worlds), void_shore (void pockets), ruin_field, urban.

Places keep their own stats but inherit their region's profile, with local overrides (`place_environment`: terrain, `cover`, `water_source`, `height_advantage`, `chokepoint` bool). A pass is a chokepoint, a ford is a river crossing and a ruin is cover.

#### F2.2 World seasons and calendar

New world columns:

| Column | Range | Effect |
|---|---|---|
| `axial_tilt` | 0–90 | seasonality amplitude; 0 = no seasons; tidally locked worlds have none and use the terminator band instead |
| `year_length_days` | rule-bounded | flavour plus festival count; feeds the calendar |
| `season_count` | 2–6 | derived from tilt and world type (ice worlds: long winter / short thaw) |
| `day_length_hours` | | feeds night-battle frequency, sleep traditions |
| `moon_count`, `tidal_strength` | | from moon child worlds; tides change coast passability and flood chance; eclipses gain a moon-driven frequency |

The `world_seasons` table holds per-season `temperature_shift`, `rain_shift`, `growth` (0–100), `travel` (0–100) and `campaign` (0–100: how suitable the season is for war). Seasons are generated from tilt and world type, are editable by the player, and can be changed by a son with the new `reorder_seasons` power (Part 9).

Calendar entities: each people may adopt a **calendar** (a knowledge record of branch `astronomy` with a typed `calendar` block: epoch anchor, named months, holy days). A calendar improves harvest planning (F2.4 `planning_bonus`) and fixes tradition dates (Part 8).

#### F2.3 Weather on demand

Weather is never stored per cell. It is drawn deterministically whenever a mechanic needs it:

```
weather(region, epoch, slot) = pick(WeatherKind, weights(region.temperature_band, region.rainfall,
                                    season, climate_era, sky_events_active, magic_density, leak))
rng stream: "weather.{region_id}.{epoch}.{slot}"
```

`WeatherKind`: clear, overcast, rain, downpour, storm, fog, snow, blizzard, heat_wave, drought_wind, sandstorm, hail, magic_storm (high magic), ash_fall (volcanic or after a supernova), void_rain (high leak), eclipse_dark (an active eclipse sky event), aurora.

Every weather kind has a typed effect row (`weather_effects`, rules namespace `weather`):

| Effect key | Meaning |
|---|---|
| `visibility` | missile accuracy, ambush chance, scouting |
| `footing` | cavalry and charge penalty, march speed |
| `cold`, `heat` | attrition per season by armour weight and acclimatisation |
| `wet` | bowstring and firearm penalty, fire spells weaker, disease up |
| `wind` | sea travel speed and danger, missile drift, fire spread |
| `morale` | omen weight scaled by the culture's superstition value (F5) |
| `growth` | harvest modifier for the sampled year |

So the same storm is a sailing disaster, a pinned-down archer line, a lucky omen for a storm-god people and a bad harvest year. Each of those readings is a separate coupling.

#### F2.4 Derived environment values

- `fertility` (region and place stat) = soil_fertility × rainfall_fit(crop mix) × temperature_fit × (1 − scar penalties) × (1 + irrigation from structures) × natural-law multipliers. The existing climate-era fertility drift (`climate.py:52`) becomes a shift on `rainfall` and `temperature_band`, not a direct fertility write. Existing readers of fertility keep working.
- **Harvest** for a sampled year = fertility × season growth × weather growth × farmer labour (4.1 labour allocation) × tool quality (materials) × agriculture level × calendar planning bonus × pest pressure (species, Part 3) × blight. The epoch food result is the scaled mean, and the minimum is remembered as a notable year when it falls below `harvest.notable_threshold` [55%].
- `passability[mode]` for modes on_foot, mounted, wheeled, boat, flying and burrowing = terrain base table × weather footing × roads (structures) × river crossing (bridges) × forest cover.

#### F2.5 Land use and ecological pressure

New per-region counters, each 0–100: `cleared`, `farmed`, `grazed`, `mined`, `built`. Communities raise them by working the land. They:

- reduce forest cover and wild species carrying capacity (→ ecology, Part 3.2);
- raise erosion risk in hills (→ soil fertility decline, flood chance up);
- raise `disease_load` (built + density);
- fall back slowly when the region is abandoned (rewilding), feeding ruin ecology.

Loop B: overfarming → soil decline → famine → migration → abandonment → rewilding → soil recovery. Loop R: clearing → more farms → population → more clearing, until soil and disease brake it.

#### F2.6 Ley lines and magic geography

Regions with `magic_density` ≥ `magic.ley_threshold` [70] that are adjacent form **ley lines** (`ley_lines` table: region pair, strength). Ley lines:

- carry magic-storm spread and wizard power (Part 8, magic);
- make structures built on them (temples, observatories, gates) more powerful (+function);
- are cut by salted earth, leak wounds or a son's `sever_ley` act;
- converge at **nexus** places, which become contested goals for war aims (Part 5) and cult holy sites.

### F3. Materials and commodities

#### F3.1 Material catalog (`catalog/materials.py`, rules namespace `materials`)

Every item, structure, vessel and army equipment slot references a `MaterialKind`. Each material has typed properties:

| Property | Meaning |
|---|---|
| `hardness` | edge retention, armour value |
| `toughness` | resistance to breaking |
| `weight` | encumbrance, march speed, heat attrition |
| `edge` | cutting quality |
| `conductivity` | magic channelling (enchantment cap) |
| `sanctity` | holy affinity: temple splendour, spirit binding, undead harm |
| `corruption` | leak affinity: outer-being attraction, curse chance |
| `rarity`, `base_value` | economy |
| `workability` | the craft level needed; tied to knowledge branches (metallurgy level gates bronze → iron → steel; star-metal needs forbidden or gate science) |
| `decay` | wood rots, bone cracks, ice melts in warm regions |

Starting catalog (expandable per world type): wood, bone, hide, cloth, stone, flint, obsidian, copper, bronze, iron, steel, silver, gold, glass, crystal, ivory, chitin (from species), dragonbone (from megafauna), star_metal (fallen comets and celestial events), void_glass (leak wounds), godflesh (from god corpses), living_wood (living worlds), salt, amber, lead, mithral-like `skysteel` (high-magic plus metallurgy level 6).

Materials come from resources (Part 6), from species (`species.yields`: hide, bone, chitin, venom, silk; Part 3.2), from events (comet → star_metal) and from god corpses. **Material availability becomes a war-economy coupling.** A people with iron but no forests cannot field siege engines. A people that hunted a megafauna species to extinction loses its dragonbone armourers.

#### F3.2 Commodity expansion

The three commodities (food, ore, goods) become 16 commodity kinds grouped in four families. The society row keeps the aggregate columns for compatibility and adds a `community_stocks` table (community, commodity, quantity, quality).

| Family | Commodities |
|---|---|
| Subsistence | grain, livestock, fish, fodder, timber, fuel |
| Industrial | ore (by material), stone, cloth, tools |
| Strategic | weapons, armour, horses/mounts, siege_materiel, medicine |
| Luxury and sacred | luxuries (by material: gold, silver, ivory, amber, glass), incense, sacred_goods, magical_reagents |

Consumption becomes per capita (`economy.consumption_per_1000[commodity]`), replacing the flat stockpile cap of 200. The cap becomes storage capacity from granaries and warehouses (structures, Part 7).

#### F3 reference pass 3: world-specific materials

The material catalog is the **starting set**. Each world also holds a `world_materials` table of procedural materials, with the same property columns (F3.1, F23) and an origin:

- a god's blood and bones;
- a dead star's core;
- a beast's scales;
- a leak crystal;
- an alloy discovered by research.

Every world therefore has its own adamant-like, orichalcum-like or unnamed exotic substances with consistent physics. The LLM names and describes them from their properties (G8).

#### F3 reference pass 6: building materials

Building materials join the material catalog with structural properties:

| Property | Meaning |
|---|---|
| compressive strength | load-bearing |
| durability | weathering per climate |
| fire resistance | burning |
| water resistance | underwater and wet use |
| cost | |
| workability | the masons' skill and technique needed |

The materials are mud brick, fired brick, dressed stone, rubble, timber, lime mortar, hydraulic concrete (which sets underwater; harbours, aqueducts, domes), thatch, tile and glass. Structures (7.2) record their materials, so durability under earthquakes (F2), sieges (5.4) and fire (4.2) follows them. A civilisation that loses its concrete technique cannot repair its old harbours.

### F4. Bodies, injuries and conditions

This substrate answers the core request directly: permanent injuries with lasting effects on people and on the balance of power.

#### F4.1 Body plans (`catalog/anatomy.py`)

Every mortal, species and son has a body plan (`BodyPlan` enum: humanoid, quadruped, avian, serpentine, insectoid, aquatic, amorphous, arboreal, incorporeal, colossal, construct, divine_manifest). A body plan is a tree of **parts** with typed function tags:

| Function tag | Lost function means |
|---|---|
| `grasp` (per hand) | weapon handling, craft, writing |
| `fine_manipulation` (fingers) | craft quality, writing speed, bowmanship, surgery |
| `locomotion` (per leg) | march, charge, flight from battle |
| `sight` (per eye) | missile skill, command at range, reading, perception |
| `hearing` (per ear) | perception, music, ambush detection |
| `speech` (tongue, jaw) | charisma use, command orders, preaching, singing, oaths |
| `breath` (lungs) | endurance, singing |
| `vital` (heart, gut) | wound death chance, disease resistance |
| `cognition` (brain) | intellect use, sanity floor |
| `reproduction` | fertility, succession |
| `flight` (wings), `venom` (gland), `horn`, `tail` | species functions |
| `presence` (face) | charisma reading, recognised identity |

The humanoid plan has 22 parts: head, face, left and right eye, left and right ear, nose, jaw, tongue, neck, torso, heart, lungs, gut, groin, left and right arm, left and right hand, fingers (as a counted part: 0–10), left and right leg, left and right foot. Species plans are generated from `BodyPlan` plus species traits (flying → wings, venomous → gland).

#### F4.2 Injury records (`injuries` table)

| Column | Meaning |
|---|---|
| `bearer_node_id` | mortal, beast (new type, Part 2T), son or foreign god |
| `part` | body part key |
| `kind` | `InjuryKind`: bruise, cut, deep_cut, puncture, fracture, crush, burn, frostbite, bite, venom, severed, gouged, destroyed, curse_wither, void_touch, divine_brand |
| `severity` | 1–5 |
| `state` | fresh → infected? → healing → healed_scar \| permanent \| lethal |
| `function_loss` | 0–100 % of the part's function |
| `cause_kind`, `cause_node_id`, `event_entity_id` | battle, duel, punishment, torture, accident, monster, disaster, curse, magic backlash, god; who did it and in which event |
| `epoch`, `year` | when |
| `treated_by_node_id`, `prosthesis_item_id` | healer and prosthesis (F4.5) |
| `visible` | scars and missing parts are visible; organ damage is not |

Mortal `hp` remains as an **acute condition pool**. Injuries are what persists. Damage now arrives as typed **hits** (F4.3) instead of a bare `hp −= damage`. The existing `wound()` primitive (`engine/lifecycle/wounds.py`) becomes `apply_hits(bearer, hits, cause)`. All current callers (battle wounds, duels, curses, quests, armour saves, poison, escape) migrate to it, so every source of harm gains anatomical consequences without new call sites.

#### F4.3 From weapons to injuries

A hit has a `damage_type` (cut, pierce, blunt, fire, cold, venom, magic, void, holy), a magnitude and a target-part distribution. The damage type comes from the weapon class (Part 7.1); the part distribution comes from the attacker's style, the defender's armour coverage, and the attacker's size versus the defender's (a colossal species tramples legs and torso; a flyer strikes head and eyes). The injury kind is chosen by a table (`injury.kind_table[damage_type][severity]`):

- **cut** at high severity → severed (arm, hand, fingers, ear, nose) or deep_cut
- **pierce** → puncture, gouged (eye), vital organ damage
- **blunt** → fracture, crush (skull → cognition), shattered jaw (speech)
- **fire** → burn (presence, grasp), blinding
- **venom** → chronic weakness (`vital`), sometimes paralysis (locomotion)
- **void** → void_touch (sanity floor down, cognition), never heals
- **holy/divine** → divine_brand: a visible mark that changes how cults read the bearer (blessed or damned, by doctrine)

Armour reduces hits per covered part, by material hardness and type (F3, Part 7.1). Helmets protect eyes and skull, so a people without helmets produces many one-eyed veterans. This is an emergent cultural signature that traditions and artworks can pick up (Part 8).

#### F4.4 Healing, infection and death from wounds

Each epoch (and per campaign season for soldiers on campaign):

```
p_infection = base[kind] × disease_load(region) × (1 − medicine_level_effect) × (1 − healer_skill/100)
p_heal      = base_heal[kind, severity] × (1 + endurance/100) × rest_factor × healer_bonus
p_permanent = permanent_table[kind, severity]   (severed and gouged parts are always permanent)
p_lethal    = infected vital wounds × (1 − medicine) ...
```

- `hp` regenerates for mortals (closing the audit gap): +`healing.hp_regen_base` [20] per epoch, +endurance/`healing.endurance_div` [5], ×0 while any wound is infected.
- **Medicine level** (knowledge) sets the treatments available: none → herbs (infection down) → surgery (amputation instead of death: an infected arm becomes a severed arm, a survivable permanent injury) → prosthetics → reattachment (high magic or biomancy).
- **Healers** are mortals with the `healer` role or the healing skill (F6). A wounded notable seeks the best healer within reach. This creates `TREATED_BY` bonds and healer renown, and gives healers a reason to exist in the simulation.

#### F4.5 Permanent conditions and how they change the world

Permanent injuries and conditions (`conditions` table: bearer, kind, since, source) change **derived capacities**, which every behaviour reads in place of raw stats:

| Capacity | Formula shape |
|---|---|
| `melee` | strength × grasp(weapon hand) × locomotion × (1 − pain) + skill |
| `missile` | agility × sight × fine_manipulation + skill |
| `command` | intellect × sight (range) × speech + charisma + skill |
| `craft` | intellect × grasp × fine_manipulation + skill |
| `scholarship` | intellect × sight (reading) + skill; blind scholars need a reader (a bond to an apprentice) |
| `presence` | charisma × culture_reading(face scars, missing parts) |
| `mobility` | locomotion × endurance |
| `fertility` | reproduction × age curve |

Non-injury conditions use the same table:

- chronic illness (from disease, F4.6)
- madness forms (from sanity: paranoia, visions, rage, melancholy)
- addiction (individual, extending the community addiction rows)
- blindness or deafness from age
- curses (withered limb, endless hunger)
- possession (by a spirit, Part 3.3)
- void taint
- divine marks: CHOSEN becomes a condition with typed effects

**Prosthetics** are items with `prosthesis_for: part` and a material (wood leg, silver hand, glass eye, star-metal jaw). They restore part of the lost function: `material.workability × craft quality`. A legendary prosthesis such as "the Silver Hand" becomes a heritable relic that can carry legitimacy (Part 4.1).

**Culture reads injuries.** A people's values (F5) decide how a condition is read:

- A martial-honour culture reads battle scars as presence +; mutilation by punishment as presence −; a one-eyed seer as presence + (via a `seer_eye` tradition).
- A purity culture reads any visible missing part as presence −, and **disqualifies a maimed ruler** if its succession law requires bodily wholeness.
- A cult whose doctrine sanctifies suffering (Part 4.4) recruits the maimed.

This is the power-balance coupling. Example chain:

> A duel severs the king's sword hand → his `melee` capacity collapses and `presence` drops in a culture with `wholeness_required` → his legitimacy (Part 4.1) falls → a faction with a rival claimant (Part 4.3) crosses its challenge threshold → succession crisis → civil war (Part 5) → the winning claimant's people grow suspicious of the healer who failed (opinion memory, F7) → the healers' guild loses standing → medicine diffusion slows in that kingdom (knowledge, Part 8).

Every arrow in that chain is a typed rule in this spec.

**The maimed as a population.** Communities track a **veteran and maimed cohort** (`community_cohorts`, Part 4.1): the counts of permanently injured soldiers returned from war, by condition. This cohort:

- lowers labour productivity (Part 4 labour);
- raises demand for alms, healers and prosthetics;
- produces beggar and veteran sub-classes when no pension law exists;
- feeds martial traditions (scar festivals) or anti-war sentiment (war-weariness, Part 5);
- shrinks by death and age.

Generations after a great war, a people remains a "people of one-armed grandfathers" in its traditions and artworks.

#### F4.6 Disease

Diseases become typed records (`diseases` table: name, vector [air, water, touch, bite, spirit, void], virulence, lethality, chronic_rate, target body function, host species, origin event, immunity duration). The current plague events become outbreaks of a named disease. Outbreaks spread along trade routes, army movements and journeys. Survivors gain an `immunity` row per disease, so a disease that returns finds an immune generation. They may also gain a chronic condition (lung-rot → breath −).

Species can host diseases (rats, a swamp fly species). Ecology therefore links to epidemiology, and exterminating the host species is a real counter, with ecological costs (Part 3.2).

### F5. Personality, values and culture (shared value space)

One value space is used for **mortals, peoples, cults, factions and gods**. Alignment and conflict can then be computed everywhere with the same function.

**Value axes** (`ValueAxis` enum, each −100..+100):

| Axis | − pole | + pole |
|---|---|---|
| `honour` | pragmatism | honour |
| `tradition` | innovation | tradition |
| `hierarchy` | equality | hierarchy |
| `martial` | peace | martial glory |
| `piety` | worldliness | piety |
| `purity` | tolerance of the unclean | purity (bodily, ritual) |
| `kinship` | individualism | clan loyalty |
| `mercy` | cruelty | mercy |
| `knowledge` | anti-intellectualism | learning |
| `wealth` | austerity | commerce and display |
| `nature` | mastery over nature | harmony with nature |
| `superstition` | rationalism | omen-reading |
| `xenophilia` | xenophobia | openness to strangers |
| `death` | fear of death | acceptance and veneration of the dead |

- Peoples hold a **culture vector** (`culture_values` table: entity, axis, value). It is seeded from the people's stats and their god's domains at creation (War domain → martial +, Death → death +), and it drifts (Part 4.1).
- Mortals hold a **personal vector** (`personality_values`). It is seeded from the culture with deviation, plus **traits** (F5.1).
- Cults hold a **doctrine vector**. Factions hold an **agenda vector**.
- Sons and foreign gods hold a vector derived from domains and passions. Son `mercy` finally has mechanical weight here (closing the audit gap).

Three functions use the value space:

- `value_distance(a, b)` → 0–100. It feeds opinion (F7), migration preference, assimilation, conversion chance, marriage alliances, mortal loyalty and syncretism.
- `value_reading(culture, act)` → how a culture judges an act (`ActKind`: execution, mutilation, betrayal, mercy to an enemy, human sacrifice, trade with outsiders, building temples, burning books…). This drives legitimacy, reputation and outrage.
- `value_pressure(entity)` → drift toward neighbours, rulers, gods and experiences. A war makes a culture martial or pacifist depending on the outcome; plague raises piety or death acceptance; trade raises xenophilia and wealth; conquest by a foreign culture pulls toward it, or pushes away if resistance is high.

#### F5.1 Traits (`TraitKind`, mortals and gods)

There are about 40 traits, each with typed effects on capacities, decisions and opinion: brave, craven, wrathful, patient, cruel, kind, ambitious, content, greedy, generous, honest, deceitful, zealous, cynical, paranoid, trusting, lustful, chaste, gluttonous, ascetic, scholarly, illiterate-proud, gregarious, reclusive, vengeful, forgiving, stubborn, fickle, just, arbitrary, humble, proud, curious, incurious, melancholic, sanguine, iron-willed, impressionable, cunning-tactician, reckless.

Traits come from:

- birth (personality seed);
- **experience**: a battle survivor may gain brave or craven, a torture survivor gains paranoid, a maimed warrior gains melancholic or iron-willed by roll weighted by personality;
- **conditions**: madness forms map to traits;
- **education**: a master passes traits to an apprentice (Part 3.1).

The LLM deepener reads traits to write prose. It no longer invents temperament (G8).

#### F5 reference pass 3: social learning

Beliefs and preferences spread between people by three biases:

- **prestige bias:** people copy those with high reputation in their community, F19;
- **conformity bias:** people copy the local majority, scaled by the facet of the same name and the culture's tradition value;
- **content bias:** some beliefs are stickier, for example fear-based beliefs in anxious cultures.

Value drift (F5) is the aggregate of these individual copy events, so a single charismatic reformer can move a town.

### F6. Skills and proficiency

`skills` table (holder node, skill, level 0–100, xp). Skills apply to mortals, and to communities and armies as aggregates (Part 4, Part 5).

| Family | Skills |
|---|---|
| Combat | blade, spear, axe, blunt, bow, sling, throwing, shield, unarmed, riding, mounted_combat, siegecraft, naval_combat, beast_handling |
| Command | tactics, strategy, logistics, leadership, intimidation |
| Social | oratory, negotiation, intrigue, etiquette, deception, teaching |
| Craft | smithing, carpentry, masonry, weaving, pottery, jewelling, shipwright, engineering, alchemy |
| Knowledge | lore, medicine (healing), surgery, astronomy, law, theology, languages (per language), writing, accounting |
| Survival | hunting, tracking, foraging, sailing, navigation, mountaineering, swimming |
| Faith and magic | ritual, prophecy, spellcraft (per magic school, Part 8), spirit_speaking |

- XP comes from doing: a battle gives combat and command XP, crafting gives craft XP, a teaching bond gives XP to the student.
- Skills decline with age past `aging.skill_decline_start_pct` [70%] of lifespan, and with conditions that remove the needed function.
- **Roles become derived.** `mortal_role` is recomputed from the top skills and offices (Part 4.1). An injury that ends a warrior's career moves a mortal from warrior to, for example, teacher (tactics), beggar or priest, by skills, personality and community values. This is a behaviour change caused by injury.

#### F6 reference pass: learning, rust and teaching

- **Learning rate** per skill = base × the governing attributes (F13; for example blade uses agility and kinaesthetic sense, oratory uses linguistic ability and social awareness) × the teacher's skill gap × the practice volume.
- **Rust:** skills unused for `skills.rust_epochs` [2] lose `skills.rust_rate` [8%] per epoch down to a floor of the highest level ever reached × `skills.rust_floor_pct` [60]. Retained skill memory makes re-learning fast.
- **Ways to learn:**
  - doing (job, battle, duel);
  - demonstration (watching a master in the same workplace);
  - sparring (combat skills; training injuries are rolled at low severity, F4);
  - lectures (schools);
  - books (scholarship × the book's fidelity, 7.1).
- **Professions** are typed bundles of skills with an expected minimum. They are what careers, guild ranks (4.3) and offices (4.6) check.

### F7. Opinions and memory

**Memories** (`memories` table: holder node, subject node, kind `MemoryKind`, magnitude, epoch, decay, source event). Holders are mortals, communities, cults, factions and gods. Memory kinds include: harmed_me, killed_kin, saved_me, betrayed_me, kept_oath, broke_oath, maimed_me, humiliated_me, gifted_me, converted_me, conquered_us, freed_us, famine_aid, desecrated_holy, married_into.

**Opinion** of A toward B is not stored as one number. It is computed from components:

```
opinion(A→B) = Σ memories(A,B) × decay × value_reading(A.values, memory.kind)
             + value_alignment(A, B) × w_align
             + shared(language, god, kin, enemies) × w_shared
             + traits(A) modifiers (paranoid: −trust, forgiving: faster decay)
components: trust, fear, respect, affection, grievance
```

- The community relation scalar (`community_relations.value`) becomes a cached aggregate of community-level opinion. Existing readers keep working; the scalar now has a *reason*.
- The 12-event history (`community_relation_events`) migrates into memories.
- Blood feuds become `killed_kin` memories with very slow decay and active vendetta behaviour (Part 5.9).
- **Memory inheritance.** On death, a mortal's strongest memories pass to their heirs at `memory.inherit_pct` [50%] (grudges are passed down), and to their people if the mortal was a ruler.
- **Memory distortion.** Memories carried by legends (Part 8) distort over time, so a people may remember a betrayal that never happened as they tell it.

### F8. Needs and pressures

**Mortal needs** (0–100 each): sustenance, safety, belonging, status, purpose, faith, plus a pleasure need only for some traits.

**Community pressures** (0–100 each): hunger, insecurity, overcrowding, poverty, impiety, humiliation, stagnation.

Needs and pressures drive three things:

1. **Engine decisions.** Migration, uprising, war declarations, conversion, emigration through journeys and founding of factions all use pressure, not a single prosperity threshold.
2. **Mortal agent selection.** A mortal under strong pressure is more likely to be picked as an LLM agent (`agents/mortal.py` scoring gains a `pressure` term).
3. **LLM prompts.** Agent contexts include the top two pressures. The LLM acts on real state, not flavour.

### F9. Modifier bus (the backbone of interconnection)

Today couplings are scattered "+k" writes. This substrate makes them first-class.

`modifiers` table:

| Column | Meaning |
|---|---|
| `target_node_id` | the entity the modifier applies to |
| `target_key` | the stat or capacity it changes |
| `op` | add or multiply |
| `magnitude` | the size of the change |
| `source_kind`, `source_node_id` | where it came from: injury, law, tradition, artwork, weather, terrain, season, structure, god_power, natural_law, condition, treaty, doctrine, wonder, curse, blessing |
| `stacking_group` | modifiers in the same group do not stack beyond the group cap |
| `start_epoch`, `end_epoch` or `decay` | duration |
| `visible_reason` | an English template key that the UI and LLM contexts render |

Rules:

- Every stat read in the engine goes through `effective(entity, key)` = base + Σ add × Π mul, clamped. It is cached per tick in the unit of work.
- Temporary effects (blessings, curses, war-weariness, festival mood, weather) are modifiers. Permanent ones (injuries, traits, doctrines) are also modifiers, derived from their source rows each tick.
- **Explainability.** The UI shows a "why" breakdown for every stat (the same mechanism as the existing creator-mood inputs).
- **Interconnection registry.** Each modifier source declares its (source subsystem → target key) edge. That registry is matrix I.1, and the depth metric C counts it.

### F10. Causality log (`incidents`)

Every engine action that changes state for a reason records an **incident** (kind, epoch, year, actors, targets, place, cause_incident_id). For example, battle → injury → death → succession → crisis → war.

The causality log:

- turns emergent chains into traceable stories for the chronicler, which gets cause chains instead of disconnected lines;
- lets Fate and the LLM bard write consequences ("because the king lost his hand at Varn…");
- drives memories (F7): the memory of a maiming points at the incident;
- supports UI "story threads", an automatic causality graph view per entity;
- feeds threads: the engine can open a thread from a chain of length ≥ `incidents.thread_chain_min` [4].

#### F10 reference pass: event collections

Incidents group into **event collections** (`incident_collections`: kind, name, start, end, participants, places, parent collection). They are the legends-level view of history.

- **Kinds:** war, battle, siege, duel, abduction, beast_attack, raid, persecution, purge, insurrection, coup, succession_crisis, occupation, journey, pilgrimage, competition, performance, procession, ceremony, wedding, funeral, coronation, feast, tournament, hunt, council, summit, plague, famine, migration, founding, theft, investigation, trial, conversion_wave, schism, excavation.
- Collections nest: a war contains battles, a battle contains duels.
- Every historical figure has a **life log**: the collections it took part in, with its role.
- The chronicler, the wiki and the books (decision 33) read collections. The legends view lists them with filters by figure, place and kind.

### F11. Information and rumour

Facts about the world spread before they are known. `rumours` table: subject incident, carrier community, fidelity 0–100, epoch. Rumours travel along trade routes, pilgrimages, journeys and spy networks, losing fidelity with distance, language barriers (Part 8.1) and the legend-distortion rate.

Rumours drive:

- the mortal knowledge rule (decision 42), which is extended: a mortal knows its region plus rumours that reached its community;
- opinion (F7): a community can hate a ruler for an atrocity it heard about, even distorted;
- war readiness: a community that hears of an approaching army prepares, raising walls and calling allies;
- the legend pipeline (Part 8): low-fidelity rumours that persist become legends.

#### F11 reference pass 3: gossip networks

Within a settlement, rumours move along the **social graph** (F18 relationships, circles and gatherings), not only along trade routes. Each telling passes through a teller with a gossip propensity (the facets friendliness and discretion), loses fidelity and can be **spun**: the teller's opinion of the subject biases the content. So the same scandal reaches the palace in one form and the docks in another, and reputations (F19) differ by social circle.

### F12. Scale bridging: individuals and cohorts

Named mortals are few (about 1,100 in the reference world). Populations are aggregates. The bridge between them:

- **Cohorts** (`community_cohorts`): per community, counts by class, age band (child, adult, elder), and condition (maimed, veteran, sick, enslaved, captive). Population changes always go through cohorts, so a famine kills children and elders first and a war kills young adult men first.
- **Promotion.** When a cohort event is notable (a mass maiming at a battle, a plague's first victim, a famine orphan), the engine may **promote** an individual from the cohort into a named mortal with matching state (injury, condition, memory). The current `notables` birth path is generalised into this.
- **No ceiling on named mortals (decision K.4).** Named mortals are never removed or merged back into cohorts. For performance only, a mortal of low importance who has been uninvolved for `cohorts.dormant_after_epochs` [6] becomes **dormant**. A dormant mortal still exists, ages, heals, can marry, have children and die, and can be picked by any mechanic. The engine only skips its expensive per-epoch choices (careers, needs and opinion recomputation), and any incident that touches the mortal wakes it at once. A loose safety threshold `cohorts.named_mortal_soft_limit_per_world` [10000] only lowers the promotion rate from cohorts when it is exceeded. It never deletes, merges or blocks births.


#### F12 reference pass 3: generations

- Cohorts carry a **generation tag**: the epoch band of their youth. Each generation records the formative incidents of its youth: a great war, a plague, a golden age, a conquest.
- A generation's beliefs are shifted by those incidents (the "war generation" is more pacifist or more martial depending on the outcome). That shift persists while the generation lives and is passed on partly through upbringing.
- Political change often happens at a **generational turnover**, when the last of a generation dies, as an incident that lets suppressed movements rise.

### F13. Attributes, facets and beliefs (the mind split)

The first pass mixed three layers. They are now separate, and each has its own role.

**Attributes** (what one *can* do; 0–100 for every mortal, beast and avatar):

| Physical | Mental |
|---|---|
| strength, agility, toughness, endurance, recuperation, disease_resistance | analytical_ability, focus, willpower, creativity, intuition, patience, memory, linguistic_ability, spatial_sense, musicality, kinaesthetic_sense, empathy, social_awareness |

- The first-pass abilities map onto these: intellect → analytical_ability and memory; charisma → social_awareness, empathy and linguistic_ability with beauty (F26) feeding presence; perception → intuition and focus; wisdom → patience, intuition and empathy. Existing stats remain as derived summaries for compatibility (G10).
- Attributes rise slowly with use (a smith's strength) and fall with age and conditions.
- Every skill names its governing attributes (F6 reference pass).

**Facets** (how one *reacts*; −50..+50 around a cultural mean). There are 36 facets, grouped:

| Group | Facets |
|---|---|
| Emotional | anxiety, anger, depression, self-consciousness, vulnerability, cheerfulness, excitement-seeking, emotional_stability |
| Social | friendliness, gregariousness, assertiveness, trust, altruism, modesty, politeness, cooperation, vanity, envy, gratitude |
| Drive | ambition, perseverance, orderliness, discipline, thoroughness, activity_level, caution |
| Mind | imagination, curiosity, abstraction, artistic_inclination, tolerance_of_strangeness, humour, sense_of_duty, greed |

- Facets drive **reactions**: emotion intensity from events (F14), interaction choices (F18), stress gain, break-event kinds (3.1), and tactical choices for commanders (cautious versus aggressive).
- The F5.1 traits remain as **notable extremes** and acquired marks: a facet at ±40 grants the matching trait, and experiences can add traits that shift facets.

**Beliefs** (what one *values*): the F5 value axes, extended from 14 to 24. The new axes are:

- law (law versus independence)
- loyalty (loyalty versus opportunism)
- family (family versus self)
- friendship
- truth (honesty versus expedience)
- craftsmanship
- artwork
- competition
- perseverance_value
- leisure

These are used everywhere `value_distance` and `value_reading` are used. Mortals inherit beliefs from upbringing (parents, culture, teachers, cult). Long-term memories (F14) shift them.

#### F13 reference pass 5: internalising ideas

When a mortal encounters an idea (a belief argument, an ideology, a theory, a doctrine tenet, a heretical book), it may enter an **incubation** (`incubating_ideas`: holder, idea, progress, side effects during incubation). Incubation takes seasons, scaled by curiosity and the idea's fit, and brings temporary effects (distraction, focus loss or obsession). At completion the idea is **internalised**: permanent belief shifts and a typed benefit and cost (a mortal who internalised a rationalist theory gains analysis and loses comfort in rites). Mortals can reject an idea mid-incubation. Disco Elysium's thought cabinet thereby becomes a general mechanism for how ideas change people.

### F14. Thoughts, emotions and moods

**Thoughts** (`thoughts`: holder, kind, subject, emotion, intensity, epoch, decay). There are about 80 typed thought kinds. Examples: admired_great_work, saw_kin_die, was_maimed, won_duel, lost_home, married, child_born, prayed_answered, prayer_ignored, ate_fine_food, lived_in_squalor, was_insulted, betrayed, rose_in_rank, defeated, witnessed_atrocity, attended_feast, heard_great_music, lost_faith, lost_limb_but_lived.

- Each thought produces one **emotion** from a typed set of 24 emotions. The set is: joy, contentment, pride, love, gratitude, relief, hope, awe, amusement, fear, anxiety, anger, rage, grief, sadness, shame, guilt, envy, jealousy, disgust, loneliness, boredom, despair, longing.
- The intensity is scaled by the facets: anxiety amplifies fear, gratitude amplifies thankfulness, and so on.

**Mood** is the decaying sum of recent emotions, giving a typed mood state: elated, content, fine, uneasy, unhappy, miserable, broken. Mood feeds:

- labour productivity;
- stress (3.1: stress accumulates from negative mood);
- social interaction choices;
- break events (negative) and **inspirations** (positive: a creative mortal in an elated mood may begin a masterwork, F17);
- agent selection;
- the LLM character block.

**Long-term memories:** thoughts with intensity ≥ `mind.long_term_threshold` [70] become long-term memories (F7 rows of kind `formative`). Formative memories:

- shift beliefs and facets (a war survivor's caution rises; a woman saved by a priest gains piety);
- can be **relived** (an anniversary in the same season, or seeing the killer) and produce the emotion again;
- can produce a **trauma condition** (F30 effect package) when the memory is extreme and willpower is low.

**Grief** is a typed process with stages: shock, mourning, acceptance or complicated grief. Its length is set by the relationship strength and mourning traditions (8.3). Complicated grief leads to the melancholic trait or vengeance.

**Needs extension** (F8). Mortal needs grow from 6 to 22, each with a facet- and belief-weighted importance:

| Group | Needs |
|---|---|
| Body | eat, drink, rest, comfort, health |
| Social | family, friends, romance, solitude, status, belonging |
| Spirit | faith/pray, purpose, learning, creating, beauty, nature |
| Action | adventure, fighting, trade/wealth, leisure/fun, order |

- Lifestyle quality (sleep, hygiene, comfort) is an aggregate from the dwelling (F29), wealth and the settlement's sanitation.
- Unmet needs give thoughts with negative emotions; met needs give positive ones.

#### F14 reference pass 4: dreams

Every named mortal **dreams** in aggregate per sampled year (`dreams`: dreamer, kind, content refs, intensity, interpreted_as, by).

- **Kinds:** ordinary (the processing of recent strong thoughts), nightmare (from trauma memories and fear), longing (unmet needs and passions), prophetic (a dream that contains a true future incident: only under a seer gift, a divine sender, or a dream world's proximity), visitation (a god, spirit or the dead: the existing dream messages generalised), shared (two dreamers in the same dream: lovers, twins, members of a cult with a dream rite).
- **Effects:** nightmares raise stress and may become recurring (a condition); longing dreams strengthen passions; visitations carry messages (F21 medium `dream`) and shift standing.
- **Interpretation:** cultures with dream cultures (a tradition or art) interpret dreams through dream readers (a profession). Interpretations may be wrong, and they lead to actions (a king's dream read as a war omen).
- **Dream worlds** (the existing world type) are reachable by dreamers with dream rites and are where shared dreams take place.

### F15. Preferences (likes and dislikes)

`preferences` table: holder (a mortal or a people), kind, target, strength (−100..+100).

- **Kinds:** material, food, drink, creature, plant, colour, shape, art_form (2T.6), artwork_subject, season, weather, terrain, activity, craft, deity_aspect.
- **Mortal preferences** are seeded from the culture with deviation, then grow from experiences: a hunter comes to love the forest.
- **Cultural preferences** are the aggregate. They drive:
  - luxury demand (a people that loves amber raises the amber price);
  - gift value in diplomacy (F21);
  - mood from food and surroundings;
  - aesthetic choices for structures and artworks;
  - which artworks gain renown in that culture (preference fit);
  - totem animals;
  - trade preferences (merchants carry what the destination likes).
- **Disgust preferences** create taboos (8.3) when they are culture-wide.

### F16. Ethics tables

`culture_ethics` table: culture or cult, act kind, stance.

- **ActKinds** (about 40): killing_kin, killing_outsider, killing_in_war, killing_captive, theft, oath_breaking, lying, slavery, torture, mutilation_punishment, human_sacrifice, animal_sacrifice, cannibalism, eating_sapients, adultery, incest_degree, polygamy, usury, desecration, necromancy, blood_magic, void_magic, magic_use, suicide, infanticide, abandoning_elders, ancestor_neglect, trade_with_infidels, conversion_by_force, iconoclasm, duel_to_death, revenge_killing, mercy_to_enemy, cowardice, hoarding_in_famine, abduction, bribery, treason, regicide, kin_strife.
- **Stance ladder:** required → admirable → acceptable → frowned_upon → shameful → unthinkable. Each step maps to typed effects:
  - opinion deltas toward the actor;
  - renown or infamy, local (F19);
  - legitimacy for rulers;
  - law creation pressure (an unthinkable act with no law against it raises legislation pressure);
  - stress for the actor when it acts against its own ethics (guilt).
- Ethics drift slowly with beliefs (F13) and doctrine (4.4), and can split a culture (an ethics schism, then a faction or ethnogenesis).
- `value_reading(culture, act)` from the first pass is now a lookup in this table, modulated by the circumstance (war, famine, the victim's kinship).

#### F16 reference pass 4: honour and shame dynamics

- Cultures have an **honour model** (`honour_model`: individual honour, family honour, face; dignity-based, honour-based or face-based) that sets how insults, defeats and shames propagate.
  - In honour cultures, a shame to one member is a shame to the household and the house, and it demands restoration (an apology, compensation, a duel, vengeance).
  - In face cultures, public shame matters more than private guilt, and saving face (indirect refusals, intermediaries) shapes diplomacy (F21).
  - In dignity cultures, insults matter less and law matters more.
- **Public shaming** (pillory, stripping of titles, forced confession) is a punishment kind with reputation effects scaled by the honour model.
- **Restoration** follows typed paths per model, and unrestored shame accumulates as a household grievance (F7).

### F17. Aspirations, dreams, wants and fears

- **Life dream** (one per adult mortal, from beliefs, facets and needs): rule a realm, found a house, master a craft, create a masterwork, become a legend, raise a large family, see the world, achieve holiness, gain wealth, avenge kin, know a truth (research), defeat a beast, serve a god, live in peace, find love. A dream has typed **milestones**. Progress gives thoughts (pride, hope) and fulfilment gives a strong formative memory and contentment. Failure or impossibility (a maimed would-be champion) gives despair, unless the mortal adapts and re-dreams (cheerfulness and perseverance facets).
- **Wants** (short-term, per epoch: 1–3) and **fears** (1–2): marry X, gain an office, buy a fine weapon, visit a shrine; fear of death, of the dark, of a beast, of losing a child.
  - Wants steer the engine's choices for the mortal: careers, social interactions, travel.
  - Wants also become the LLM agent's suggested objectives.
  - Fears raise anxiety when the feared thing is near (a beast's terror aura, a plague rumour).
- **Lifestyle focus** (mortals with an office or high skill): diplomacy, martial, stewardship, intrigue, learning, piety, craft, or leisure. A focus gives faster skill gain in its family and unlocks **perks** (typed modifiers, about 5 per focus) at skill milestones.
- **Inspiration** (positive break, F14) takes three forms:
  - a masterwork fever (a craft or art compulsion that needs specific materials, as in a strange mood; success creates a named artifact or artwork with very high quality, failure brings a madness condition);
  - a research insight (a technique breakthrough, 8.4 reference pass);
  - a heroic resolve (fear immunity for one campaign).

#### F17 reference pass 3: acting in character

- Mortals that act in line with their beliefs and dream (choices tagged with the beliefs they serve) gain **conviction** (0–100). Conviction raises willpower in crises and makes the belief harder to change. It is spendable in a crisis: a heroic effort at a key roll, as Burning Wheel spends earned points.
- Acting against one's beliefs costs conviction and adds guilt thoughts. Repeated violations may **flip** the belief: a disillusionment incident.

### F18. Relationships and social interactions

**Relationship rows** (`relationships`: a, b, friendship −100..+100, romance 0..100, familiarity 0..100, rivalry 0..100, types).

- **Types** (derived, with hysteresis): acquaintance, friend, close_friend, best_friend, confidant, crush, lover, ex_lover, spouse (kin bond), rival, nemesis, enemy, mentor, protégé, comrade_in_arms (fought together), drinking_companion, patron, client.
- Opinions (F7) stay the evaluative layer; relationships are the social layer. They feed each other.

**Social interactions.** At epoch scale, interactions are simulated in aggregate. Each pair of co-located, socially linked mortals gets `social.interactions_per_epoch` [6] samples drawn from the interaction catalog:

- converse, befriend, gossip, joke, comfort, flatter, boast, insult, argue, flirt, court, propose, seduce, quarrel, reconcile, teach, gift, ask_favour, confide_secret, threaten, brawl
- The draw is weighted by facets, mood, relationship, beliefs fit, language intelligibility and local events.
- Each interaction has typed outcomes: relationship deltas, thoughts, sometimes secrets learned (F20), brawl injuries (F4, low severity) or proposals.
- **Clubs and circles:** mortals with shared preferences and beliefs form **circles** (`social_circles`: a faction of scale band, kind social: drinking hall, poets' circle, hunting lodge, secret society seed). Circles raise friendship among members, are recruitment pools for factions and conspiracies, and spread ideologies.
- **Jealousy and affairs:** romance outside marriage gives an affair secret (F20). Discovery leads to jealousy (an anger emotion), divorce (by the marriage law), a duel (in honour cultures) or a house feud.

#### F18 reference pass 3: passions, persuasion and status

- **Passions** (Pendragon-style) are intense directed attachments: love(person), loyalty(lord, house, realm, god), hatred(person, people), devotion(place, cause), with a strength of 0–100. Passions above [80] can be invoked for an **inspiration roll** in battle, duel, oath or crisis: success gives a large bonus, failure gives a break (madness or despair). The death or betrayal of a passion's object causes grief at full force and may begin a vengeance dream. Passions come from relationships, oaths, formative memories and upbringing. Sons already have passions; mortals now do too.
- **Persuasion.** Attempts to change someone's mind (a lord's decision, a faith, a vote) are typed arguments: appeal to belief X, to self-interest, to authority (the speaker's office and reputation), to evidence (facts in the target's belief store, F22) or to fear. Success = the speaker's oratory and the appeal's fit with the target's beliefs and facets − the target's stubbornness and contrary passions. Successful arguments shift beliefs, decisions and votes. They are the mechanical core of council debates, sermons and envoy talks.
- **Status hierarchies.** Small groups (households, courts, circles, warbands, crews) hold a **pecking order** by dominance (strength, office, reputation, assertiveness). Challenges to the order are interactions (boast, brawl, duel, scheme). Rank in a group sets access to resources and influence over group decisions.

#### F18 reference pass 6: contests of wit

**Non-violent contests** are duel analogues (5.6) with stakes: honour, a bride, a wager, an office, the release of a captive, a god's favour.

- **Kinds:** riddle game, poetry duel (insult verse, flyting), formal debate (disputation), game of skill (7.4 reference pass 5 games), trial of wisdom (judgement of a hard case), song contest, storytelling contest.
- **Resolution:** exchanges as in duels. Each round compares the relevant skills and attributes (lore and memory for riddles; poetry, linguistic ability and wit for flyting; oratory and the beliefs fit with the judges for debates) plus conviction and passions.
- **Judges** (gods, kings, crowds) apply their own preferences (F15).
- **Outcomes:** reputation (F19), relationships and stakes, plus legends and art. A famous flyting becomes an epic in its art form.

### F19. Local reputation and social currencies

`reputations` table: subject (mortal, house, polity, god), community, axis, value. Every community holds its own reputation of each known subject on several axes:

| Axis | Meaning |
|---|---|
| heroism | monster-slaying, defending |
| honour | oaths kept |
| cruelty | atrocities |
| piety | |
| generosity | |
| wisdom | |
| trickery | |
| skill_renown | per craft |
| troublemaker | crimes, brawls |

- Reputation is set by acts witnessed or heard (rumours, F11, with fidelity), read through that community's ethics (F16). A massacre gives cruelty + where the victims' kin live and maybe heroism + among the perpetrators' people.
- Global renown and infamy (3.1) become aggregates for UI and legacy readers.
- **Ruler currencies** (CK3-style) are derived from reputation:
  - **Prestige**: renown among one's own realm's communities.
  - **Piety**: standing with the state cult.
  - **Dread**: fear from executions, maimings and victories; it suppresses faction challenges but lowers love.
  - **Tyranny**: accumulated unjust acts against the realm's own ethics; it lowers vassal opinion and raises faction pressure.
- These are spendable. Prestige buys vassal acceptance of laws; piety buys clergy support; dread silences dissent for a while.

#### F19 reference pass 3: lore as currency

Factions, cults, scholars and beasts **value specific knowledge**: secrets, lost techniques, true names, locations of sites, prophecies. Knowledge can be **traded** for favours, reputation and goods. "Telling a secret" is an interaction with a value set by how much the recipient wants it and how few already know it, and selling it lowers its future value. Caves of Qud's secret-trading becomes a general currency of information.

#### F19 reference pass 6: claims of deeds

Reputation gains require that a deed be **credited**. Deeds have witnesses and evidence (4.5 reference pass 5), and claims of a deed can be **true, shared or false**.

- **False claims** (Propp's false hero) take credit for another's deed: a scheme kind `claim_credit`, more likely for vain and deceitful characters.
- **Verification** comes from witnesses, tokens (the beast's tongue cut by the true slayer, the ring given by the rescued) and contests.
- **Exposure** of a false claim is a scandal: a reputation reversal, a duel, a punishment.
- Accounts (F33) may preserve the false version, so history can honour the impostor.

### F20. Secrets, hooks, favours, identities and schemes

**Secrets** (`secrets`: holder, kind, about, severity, known_by list). Kinds: affair, illegitimate_child, murder, heresy, secret_cult_membership, debt, crime, cowardice_in_battle, hidden_condition (a hidden illness or madness), false_identity, deal_with_outer_being, true_parentage, broken_oath.

- Secrets are created by incidents: an affair interaction, a secret murder in a scheme, or a hidden condition.
- They are discovered by interactions (confide, gossip), spy operations (5.10), investigations (4.5 reference pass) or scheme fallout.

**Hooks** (`hooks`: holder, target, strength weak or strong, source: a secret, a debt, a favour, a hostage). Using a hook forces compliance with a request: a vote, a marriage, a law, or stepping down. A weak hook is spent on use; a strong one persists. Exposing a secret publicly converts it into reputation damage (F19) and may break the hook.

**Favours** (`favours`: owed by, owed to, magnitude, origin). Favours come from gifts, rescues, support in a war or a succession, or votes. Honouring a favour gains trust; refusing a called favour loses trust and honour. Diplomacy (4.6 reference pass) uses favours as the currency of support.

**Identities** (`identities`: true mortal, false name, cover role, community, exposure). Spies, vampires (F30), exiles and impostors live under false identities. Exposure follows investigations, slips (facets: low discretion) or a recognisable appearance (F26).

**Schemes** (`schemes`: owner, kind, target, agents, power, secrecy, progress, phase, discovered_by).

- **Kinds:** murder, abduct, seduce, sway, fabricate_claim, fabricate_hook, steal_relic, coup, poison_well, frame, elope, convert_secretly, sabotage_wedding, free_prisoner.
- **Phases:** recruit agents (offering money, hooks, favours or a shared cause), prepare (power accumulates from agents' skills: intrigue and stealth), and execute (a success roll against the target's defence: the spymaster office, bodyguards and the target's intuition).
- **Discovery** per epoch: secrecy against the counter-intelligence of the target's court. Discovery exposes agents and creates memories.
- **Outcomes** are incidents: deaths, injuries, captures, claims, hooks, scandals.
- Faction actions (4.3) and spy operations (5.10) become scheme kinds under one system.

#### F20 reference pass 3: true names

Every son, foreign god, outer being and spirit, and some beasts, mortals, places and artifacts, has a **true name** (the existing son `true_name`, now typed: a lexeme in the being's sacred or original language, plus a `known_by` list).

- **Knowing a true name** gives a strong hook on the bearer: command (for spirits and lesser beings), protection against its power, or a **binding** (a rite input).
- **Learning a true name** happens through research (old languages, 8.1 decipherment), schemes, divine revelation or the bearer's confession to an intimate.
- **Changing a true name** is a transformation incident: for gods, a costly rebirth of the manifestation; for mortals, an initiation.

#### F20 reference pass 8: ecology and environment in intrigue

- **Ecological sabotage:** a scheme kind `ecosabotage`: release a pest or invasive species, burn forests or fields, poison a fishery or well, divert a river covertly, salt fields at night. It is detected by evidence (4.5 reference pass 5) and readable by the ethics of the victims (often unthinkable). Its effects run through the ecology and environment models.
- **Conditions shape schemes:** scheme success and discovery read the environment and the social situation at execution: night and fog raise success and lower witnesses; storms cut pursuit; festivals and crowds give cover but more witnesses; a plague panic distracts the watch; a siege disorders a city. Schemers choose timing (their skills and belief state), so plots cluster on festival nights and foggy mornings.

### F21. Communication: correspondence, envoys, public opinion and etiquette

**Messages between mortals and polities** (extends the existing `messages` table, which today carries son and creator messages):

- Fields: sender, recipient, medium (envoy, letter, herald, signal_fire, dream (divine), bird, magic_sending), language, content kind (proposal, demand, threat, insult, gift_notice, declaration, report, plea, intelligence), payload (typed, e.g. treaty clauses), sent year, arrival year, intercepted_by, forged (bool), misread (bool).
- **Delay** = path distance × medium speed × season (mountain passes closed in winter). Between worlds it follows the route duration (light-delay analogue). Decisions use the latest *received* information (F22). A peace treaty can arrive after the battle.
- **Interception:** messages pass through regions where spy networks, bandits or enemy armies sit, and each has an interception chance. Intercepted messages give intel, hooks or forged replacements.
- **Forgery:** a scheme kind; success = the forger's writing skill against the recipient's familiarity with the sender. Forged declarations start wars between the innocent.
- **Misreading** = the language barrier (8.1) × payload complexity (multi-clause treaties) × the interpreter's skill. A misread clause causes a breach dispute later (5.13).
- **Envoys** are mortals sent with messages. Their skills (negotiation, etiquette) modify reception. They can be insulted, imprisoned or killed (an ethics reading: killing an envoy is unthinkable in most cultures and leads to war).

**Diplomatic etiquette.** Gifts are valued through the recipient culture's preferences (F15). Precedence and forms of address follow the hierarchy value. Insults follow culture readings. A breach of etiquette costs opinion; a well-chosen gift gives opinion and a favour (F20).

**Public opinion** (`public_opinion`: community, subject (ruler, law, war, god, ideology), approval −100..+100).

- It is fed by experiences, reputations (F19), rumours, propaganda artworks, sermons (cult stance), heralds and criers (a polity office), broadsheets (printing technique), and censorship (a law that lowers the spread of contrary rumours but raises distrust when discovered).
- **Effects:** approval of a war sets war support (5.8 reference pass); approval of the ruler feeds legitimacy and revolt pressure; approval of a law sets its enforcement.

#### F21 reference pass 3: codes and ciphers

- Messages can be **enciphered** (a cipher from the writing and cryptography techniques, with a cipher strength). Interception without breaking the cipher yields only the fact of the message. **Codebreakers** (scholars with the cryptography skill, analytical ability and patience) attack intercepted ciphers over seasons, and success rises with the volume of intercepted traffic.
- A broken cipher is a secret. While the sender doesn't know it is broken, all its messages are readable, and discovering the break is a counter-intelligence incident.
- **Signal networks** (fire beacons, mirror towers, post stations as structures; magical sending stones as items) cut delays on their routes and can be captured or burned.

### F22. Belief state and fog of war for decisions

Every deciding actor (polity, faction, cult, house head, army commander, beast, mortal agent) decides on a **belief state**, not on ground truth.

- **The belief store** (`beliefs`: holder, subject, attribute, believed value, confidence, as-of year, source) holds facts the actor has received: an enemy army's size, a rival's treasury, a claimant's health, a god's favour.
- **Sources:** direct observation (same region), messages (F21), rumours (F11), spy intel (5.10), scouts (5.3), and the actor's own records (literacy-dependent).
- **Decay:** confidence decays with age. Stale beliefs lead to wrong decisions, for example marching on a city that was already relieved.
- **Deception** writes false beliefs into a target's store: feints, false campfires, planted rumours, forged letters.
- **Engine rule:** every decision function receives the actor's belief view through `BeliefView(actor)`, which returns the believed value or a prior estimate. The resolution of the outcome uses ground truth. The gap between belief and truth is where surprise, folly and genius come from.
- **LLM agents** see the same belief view. This extends decision 42 (mortal knowledge) to all actors.

### F23. Material physics and tissue layers

**Material properties added to F3:**

| Property | Use |
|---|---|
| `melting_point`, `ignition_point`, `boiling_point` | fire spread, forging feasibility, heat of magma and dragon fire; a lava world's ambient heat ignites timber |
| `density` | weight |
| `impact_yield`, `impact_fracture` | blunt weapons and armour |
| `shear_yield`, `shear_fracture` | edged weapons and armour |
| `elasticity` | bows (yew-like woods, horn), springs |
| `thermal_conductivity` | burns through armour |
| `solid_density` | |
| `max_edge` | sharpness cap |

- **Attack resolution** (shared by battles in aggregate and by duels in detail): momentum = mass × velocity (a skill and attribute term). The contact area (edge or point against flat) decides cut versus blunt. The layered armour stack is checked layer by layer: each layer either deflects (the attacker's material yield is below the armour's) or is penetrated with residual momentum. Then the tissue stack is applied.
- **Armour layering:** under (padded), over (mail, scale, plate), cover (cloak), plus a shield. The layering rule allows one rigid layer per covering class.

**Tissue layers** (for body plans): skin/scale/chitin, fat, muscle, bone, plus organs with typed functions. Arteries (bleeding), motor and sensory nerves (function loss without severance), tendons and ligaments (grasp and locomotion), teeth, digits individually (fingers and toes), eyes, ears, nose, tongue.

**Injury mechanics (extends F4.2–F4.4):**

- **Bleeding:** artery hits bleed at a rate by vessel size, until bound (a healer or the first-aid skill) or death. Mass bleeding in battle is a main cause of death among the wounded, which field surgeons reduce (5.3 reference pass).
- **Nerve damage:** a motor nerve hit gives a limp limb without severance; a sensory hit gives numbness (craft penalty).
- **Pain → shock → unconsciousness:** pain is the sum over injuries scaled by willpower. Over thresholds come nausea, dizziness and unconsciousness (out of the fight, capture likely).
- **Exhaustion:** within battles and duels, exertion accumulates against endurance. Exhausted fighters attack weaker and fall more often.
- **Treatment steps** (healers, F4.4): diagnosis (a skill check: misdiagnosis wastes treatment), clean, suture, set bone, splint, dress, amputate, cauterise. Each needs supplies (cloth, thread, splints, medicine commodity) and a technique level.
- **Crutches** and **traction** restore part of a locomotion function during recovery.

### F24. Production methods, quality, energy and pollution

**Production methods** (`production_methods` catalog): every good has 1–6 alternative methods, each with:

- inputs (commodities and materials), labour (job and skill), energy, output multiplier, quality bonus, pollution, and required techniques and structures.

Examples:

| Good | Methods |
|---|---|
| Grain | hand-sickle, ox-plough, irrigated terraces, crop rotation, divine harvest (rite) |
| Iron | bloomery (charcoal), blast furnace (coal), divine forge (essence) |
| Cloth | hand-loom, water-frame mill |
| Bread | hand-quern, watermill, windmill |
| Light | tallow, oil, glow-moss, magic |

- Each production site picks the method that maximises profit under the owner's beliefs: a nature-harmony culture avoids high-pollution methods.
- **Transitions** happen when techniques arrive. An early adopter gains output and displaces artisans, which creates unemployment (4.1 reference pass) and guild resistance (4.3).

**Substitution:** consumers substitute within families by price and preference. Fuel can be timber, coal, peat, dung or magic. Food can be grain, fish, meat or tubers.

**Quality tiers** for goods: poor, common, fine, superior, exceptional, masterwork, artifact. The tier comes from skill, method and material quality. Higher tiers carry luxury value and mood bonuses (fine meals, fine clothes) and are what nobles demand (4.6 reference pass).

**Spoilage and preservation:** perishables (meat, fish, fruit, milk) decay per sampled year unless preserved (salt, smoke, cold: ice worlds and cellars, magic). Preservation methods are production methods. Vermin species raise the spoilage of stored grain (granary quality and cats-like pest hunters reduce it).

**Energy** (`energy` per settlement: muscle (from labour and draught beasts), water (rivers with mills), wind (mills; terrain and weather), heat (fuel), magic (ley density and mages), divine (temple rites, essence)). Production methods consume energy. The energy mix limits output and is a geographic advantage (river towns industrialise first). On frozen worlds, **heat** is also a survival need: a fuel shortage brings cold deaths in cohorts and frostbite conditions.

**Pollution** (`region_pollution`: air, water, soil). It comes from smelting, tanning, dyeing, mining, crowding and void rites. Effects: disease load +, fertility −, fish yield −, the nature-value culture's opinion of polluters −, and a phenomenon at extreme levels (a blight). Cleanup comes from rewilding, purification rites and sanitation structures.

**Tool wear:** production consumes tools (a commodity) at a rate per method. Tool quality sets productivity. A blockade on iron reaches farming through broken ploughs.

### F25. Activities and gatherings

`gatherings` table: host, kind, place, year and season, invitees, attendees, cost, outcome. Gatherings are event collections (F10 reference pass).

- **Kinds:** feast, wedding, funeral, coronation, tournament, hunt, pilgrimage, council, summit (multi-polity congress), festival (a tradition), fair, games, performance (troupes, art forms), trial (public), execution (public), religious procession, birthday or coming-of-age (households), wake.
- **Mechanics:** attendance is decided by relationships, opinion, obligation and distance.
  - Interactions among attendees are concentrated, so relationships, romances, schemes (agents meet), secrets learned and marriages proposed all happen here.
  - Outcome rolls follow the kind: a tournament gives renown and injuries; a hunt may promote a beast encounter; a feast spends commodities for prestige and opinion; a summit negotiates treaties among several parties at once (simultaneous bargaining, 5.13 reference pass).
  - Gatherings can be targets: murder at the wedding, a massacre at a feast (with ethics readings: the hospitality-law tradition makes it unthinkable).
- **Personal milestones** (births, comings of age, anniversaries) are household gatherings that produce thoughts and memories.

### F26. Appearance and genetics

**Genome** (`genomes`: holder, genes). It holds a small set of typed loci with alleles:

- height, build, skin, hair colour and texture, eye colour, facial features, voice;
- heritable predispositions: longevity, fertility, disease resistance, madness predisposition, colour blindness, giant blood, divine blood (son marker), a curse marker.

**Inheritance** is Mendelian with dominance per locus. The F4/3.1 ability inheritance (mean ± deviation) becomes polygenic potential plus upbringing.

**Appearance** is derived from genes, age, injuries (scars and missing parts, F4) and conditions. It feeds:

- the beauty attribute (culture-read: preferences, F15);
- recognisability (identity exposure, F20; resemblance to a parent exposes a true parentage secret);
- portraits (image prompts read appearance, keeping the same face across portraits);
- house resemblance (a house trait such as "the copper hair of the Varns").

**Inbreeding** (consanguinity from kin bonds) raises the chance of heritable conditions. Laws and ethics (F16 incest degree) govern it, and royal houses face the trade-off between claims and health.

Peoples' biology (4.1) defines the allele pools and how they mix; cross-people children inherit from both pools.

#### F26 reference pass 8: the magical gift

The genome (F26) carries **magical aptitude loci** per form (8.6 reference pass 3), so aptitude is heritable, with recessive and rare alleles.

- The **gifted share** is a demographic quantity per people and cohort. Bloodline plans (4.7 reference pass 4) can aim at it, and mage orders recruit from it (testing children).
- Cultures read the gift by their ethics: honoured, feared, persecuted or taxed.
- Magical aptitude interacts with selection (persecution lowers the share) and with natural laws that raise or suppress it.

### F27. Storyteller (deterministic drama pacing)

A world-level **tension meter** tracks recent drama: incidents weighted by magnitude per epoch, against a target curve per world (`storyteller.profile`: steady, rising, cyclic, chaotic). It is set in genesis and editable. Decision K.17: the default is **cyclic** (golden ages and crises in waves), and existing worlds receive cyclic in the upgrade.

- **Modulation:** when tension is far below the target, the storyteller raises the base rates of spontaneous disruptions (beast awakenings, raids, comets, plagues, ambitious claimants) by `storyteller.boost_max_pct` [50]. When tension is far above the target, it lowers them and raises recovery events (good harvests, peace envoys, healer births). It never overrides causal mechanics: it only scales *spontaneous* base rates.
- **Variety:** a recency memory of incident kinds lowers the chance of repeating the same kind (the existing tired-motif detector, decision 59, extended to engine incidents).
- **Spotlight:** the storyteller assigns attention to under-narrated regions and characters, which raises their agent-selection weight and the chronicler's sampling of them.
- The existing `world_balance` revival of quiet worlds becomes one storyteller rule.

### F28. Conservation and stock-flow invariants

Every countable quantity is conserved by construction and checked by tests:

- **Population:** births − deaths ± migration ± journeys ± captives ± levies (out of cohorts, back on disband) = Δ cohorts. This fixes the audit bug where engine-raised armies returned soldiers that were never subtracted.
- **Goods:** production − consumption − spoilage − destruction (war, fire) ± trade ± tribute ± loot = Δ stocks.
- **Money:** minting − destruction (melting) ± flows = Δ holdings. Inflation follows from the money supply against goods.
- **Souls:** deaths = new souls. Souls are accounted for (in a realm, reborn, consumed, wandering, bound) and never lost.
- **Essence:** the existing essence ledger, extended with the domain-activity income (9.1).

A `ConservationLedger` per tick records the flows. The invariant tests in J.6 assert a zero residual within rounding.

### F29. Households and dwellings

**Households** (`households`: head, members, dwelling, wealth, income, expenses, servants, dependents, settlement, class). Every named mortal belongs to one household. Cohorts are made of anonymous households in aggregate.

- **Behaviour:**
  - pooled income from members' work and holdings;
  - expenses for food, rent or upkeep, dowries, tithes and taxes;
  - care roles (who looks after children, elders, the maimed: a maimed veteran in a poor household is a burden, in a rich one a respected elder);
  - household decisions (whom to marry, whom to apprentice, where to migrate).
- **Household roles:** head, spouse, heir, dependent, carer, servant, ward, lodger.

**Dwellings** (`dwellings`: household, kind (hut, longhouse, townhouse, manor, palace, tent, cave, ship, tower), quality 0–100, rooms, furnishings (items), location district).

- Quality affects lifestyle needs (F14: comfort, beauty, status), mood, disease (squalor) and the prestige of houses.
- Nobles' room demands (4.6 reference pass) are dwelling requirements.

### F30. Effect packages (syndromes)

**Effect packages** (`effect_packages` catalog; applied as `afflictions`: bearer, package, stage, since, source) generalise conditions, curses, venoms, diseases' symptoms, drugs, blessings, transformations and rite effects into one system.

- **Package fields:**
  - transmission (contact, bite, ingestion, inhalation, blood, curse (desecration of a holy place), birth, rite, gaze);
  - onset delay; stages with typed effects per stage (attribute modifiers, facet shifts, needs added or removed, body changes, new abilities, appearance changes);
  - duration or permanent; cure conditions (rite, technique, medicine, time, a quest);
  - **contagion of the package itself** (a werebeast bite passes the curse).
- **Examples:**
  - snake venom: necrosis stage, then a chronic weakness;
  - dwarven-style alcohol dependence: a need added, and withdrawal;
  - **lycanthropy-like curse:** transformation every full moon of the world's first moon, with a sapient beast form; it is transmitted by bite and earned by desecrating a Hunt-god shrine;
  - **vampirism-like curse:** no ageing, blood need, a false identity (F20), sunlight harm; it can come from a blood rite backlash or a Blood-domain son's curse;
  - divine blessing: strength +, a fear of the god;
  - void taint: a stage progression to madness, then outer-cult recruitment;
  - possession (3.3);
  - drugs (luxury commodities with dependence);
  - trauma (F14).
- **Visibility:** each package has a visibility level (obvious, noticeable, hidden). Hidden afflictions are secrets (F20).

### F31. Dominion and scales (the spatial presence of gods)

**Dominion** (`dominions`: god node, region, strength 0–100) is each god's presence in the land. It is separate from worship (decision 27 unchanged) and from standing (9.1).

- **Sources:** temples (by splendour and staffing), holy sites and thrones (6.2 reference pass 3), prophets and saints (mortals with the prophet flag radiate dominion), miracles performed there (impressiveness, 9.1 reference pass 3), worshipper density, and the god's own `dominion_strength` attribute (9.1 reference pass 3).
- **Spread** per epoch to adjacent regions, scaled by strength against the existing dominion of other gods.
- **Contest:** dominions of different gods in a region compete (Dominions-like candles). The strongest converts dominion share each epoch. Contests are visible as a map layer, and every god knows where it is losing ground.
- **Effects of dominion:**
  - Miracles and rites of the god cost less and work better under its dominion (the proximity mana of Populous, R8 #12).
  - Missionaries of the god convert more easily (4.4).
  - Rival gods' miracles there cost more.
  - Worshippers there gain morale and fear less.
  - Priests of other gods suffer a stress thought.
  - The god's **scales** apply (below).
- **Scales** (each −3..+3, set by the god at creation and shifted by its aspects and deeds). Each one is a typed modifier package on every region where the god's dominion dominates:

| Scale | Positive pole effects | Negative pole effects |
|---|---|---|
| order ↔ turmoil | order +, crime −, income + | unrest +, random incidents +, storyteller tension + |
| productivity ↔ sloth | output + | output −, leisure + |
| heat ↔ cold | temperature band shift (F2.1): harvest, attrition, disease | (opposite shift) |
| growth ↔ death | fertility +, healing +, population growth + | decay +, unrest of spirits +, the necromancy rite cost − |
| fortune ↔ misfortune | rare-event rolls skew favourable (notable good years) | rare-event rolls skew unfavourable (disasters, accidents) |
| magic ↔ drain | magic density +, rite power + | magic density −, rite power −, warding + |

Scales are the most direct way a god changes the land in which mortals live, and dominion contests between gods are therefore felt by every farmer.

- **Coupling:** dominion feeds region alignment (6.1 reference pass: a death-scaled god darkens a land), belief-shaped worlds (10.2 reference pass 3), afterlife strata (3.3: a realm's strata reflect the dominant god's scales) and son existence (dominion area is an existence anchor term).
- **Misattribution:** where dominions overlap, F22 belief states decide which god a people credits for a miracle or blames for a disaster. Gods can gain or lose standing for each other's acts, a beyond-the-leader effect.

### F32. Collective behaviour: crowds, mobs, panics and movements

**Threshold model** (Granovetter-style): each mortal and cohort segment has a **participation threshold** for collective acts (riot, panic flight, lynching, mass conversion, joining a revolt, a strike, a procession). The threshold depends on facets (anger, anxiety, conformity), needs, pressures and relationships.

- **Dynamics:** within a settlement district, a collective act spreads when the participating share exceeds the thresholds of the next segment. The engine computes the cascade per sampled year when a trigger occurs (a price spike, an execution, a sermon, an omen, a rumour).
- **Results:**
  - small sparks die out, or a cascade becomes a riot, panic or movement;
  - the size and violence of the outcome are emergent, not rolled;
  - the watch and garrison raise thresholds by deterrence, and charismatic agitators lower them.
- **Mobs** are short-lived actors (`mobs`: size, target, anger, leaders). They burn districts, lynch a scapegoat (a wrongful-justice incident), storm a granary or open a gate during a siege. They disperse by fatigue, force or concession.
- **Panics** (fire, plague rumour, beast attack, eclipse) cause flight (migration spikes), trampling deaths in crowded districts, and hoarding (F24, 6.4).
- **Mass phenomena of faith:** revivals, flagellant-like processions and mass conversions are cascades with religious triggers (miracles, sermons, plagues).

### F33. Historiography and collective memory

**Accounts** (`accounts`: author (mortal, cult, polity, people), kind (official chronicle, folk memory, foreign account, gospel, epic, inscription), subject (an event collection or figure), stance per participant (glorify, vilify, omit), fidelity, medium (artwork, book, oral legend, inscription on a structure), epoch).

- Every event collection can have many accounts. The **truth** is the incident record, and accounts are measured against it. Ruling polities produce official chronicles; peoples hold folk memories (legends, 8.2); enemies hold foreign accounts.
- **Damnatio memoriae:** a polity or cult can erase a figure. Inscriptions are defaced (a structure decoration change), names are struck from official accounts, and artworks are destroyed. The figure's reputation fades in the next generations unless folk memory or foreign accounts keep it alive.
- **Revisionism:** new rulers rewrite official accounts to support legitimacy (founding myths, a dynasty's divine descent). Revisions conflict with surviving older texts, and scholars who find the old texts create scandals (F20 secrets: the true history as a secret).
- **Founding myths:** each people and polity has a founding account. Its credence supports cohesion and legitimacy, and debunking it (a discovered inscription, F33 contradiction) costs both.
- **Commemoration calendar:** anniversaries of great collections (a victory, a massacre, a founding) are relived collectively (F14 reliving at cohort scale) through traditions and gatherings. They keep grievances and pride alive, and their neglect lets memory fade.
- **Irredentism:** memories of lost lands (de jure titles, F33 accounts of the old borders) generate claims and movements centuries later. They are the historical root of many wars.
- **The chronicle itself:** the in-app chronicle (spec 08/09) remains the player's ground truth. Accounts are the in-world view, readable side by side (J.9).

### F34. Storylets (typed event chains)

**Storylets** (`catalog/storylets`, data-driven, with English templates only):

- a **precondition** over typed state (a DSL shared with prophecy conditions, 8.7);
- a **weight** (the storyteller, F27, scales weights);
- a **cast** (roles bound to entities that satisfy role predicates);
- **choices** (2–4), each with typed **effects** and the next storylet ids;
- a **cooldown** and repetition rules (the tired-motif detector, decision 59).

Examples: a stranger at the gate claiming to be the lost heir; a famine and a granary key; a beast's tribute demand; a heretic book found in the abbey; a desecrated grove; a duel challenge at the wedding; a dying king and two sons; an envoy insulted.

- **Resolution.** When a cast member is a selected LLM agent, the choice is offered to the agent as a typed tool call (the agent sees the situation in its context). Otherwise the engine chooses by the cast member's personality, beliefs, passions and belief state, so the same storylet branches differently for different characters.
- **Chains.** Choices can schedule follow-ups for later epochs (archaeology chains, prophecies' fulfilment chains, the long return of the exiled heir). Chains are event collections (F10 reference pass).
- **Emergence first.** Storylets are a narrative layer *on top of* the simulation. They never replace a mechanic: their effects are ordinary typed effects, and their preconditions read emergent state. They concentrate drama at the moments the simulation creates.

### F35. Social norms and volition

**Norm tables** (`social_norms`: culture or cult, situation, behaviour, stance):

- **Situations:** funeral, feast, wedding, court, temple, market, battle, duel, hospitality, mourning period, sacred day, encounter with a stranger, encounter with a superior.
- **Behaviours:** interaction kinds (F18), dress (7.1), speech register (8.1), gifts, laughter, weapons carried, eating particular foods (F15).
- **Stances:** follow the ethics ladder (F16).

**Volition.** A mortal's choice of interaction or action in a situation is scored by a sum of **social rules**: its desires (needs, wants, passions), the relationship with the target, the norms of the situation (breaking a norm has a cost scaled by the conformity facet and a reputation risk), and the norm-breaking appeal for rebels (low tradition belief). This replaces the weighted random draws of F18 with a Comme il Faut-style rule system. It also makes etiquette breaches (F21) emergent.

Norms drift with culture (F5 reference pass 3) and are set by doctrine (4.4) and law (sumptuary, 4.5). Their history is recorded (F33), so customs have origins.

### F36. Narrative arcs and the drama manager

**Arcs** (`arcs`: subject (mortal, house, polity, god), template, stage, started, beats achieved, linked figures).

- **Templates** (about 20): rise_and_fall, rags_to_riches, revenge, redemption, quest (monomyth stages), tragedy (a flaw leading to ruin), forbidden_love, rivalry, mentor_and_heir, exile_and_return, corruption, coming_of_age, fall_of_a_house, founding, apotheosis (mantling).
- **Detection:** the engine assigns arcs by pattern-matching typed state and incidents. A dream with a matching structure (avenge kin) plus an inciting incident (kin killed) starts a revenge arc. A mortal can have several arcs, and figures in each other's arcs are **counterparts** (the rival, the mentor, the beloved).

**Drama manager** (extends the storyteller, F27):

- It reads the open arcs and raises the weights of storylets (F34) and spontaneous rates that would advance a stalled arc's next beat: the mentor's death in a coming-of-age arc, the confrontation in a revenge arc.
- It never forces outcomes. It only changes opportunities, so arcs can still fail, twist or end in irony, and those outcomes are recorded as their own beats.
- **Ensemble counterpoint:** arcs of counterparts are kept in rhythm, so a rival's rise is timed against the hero's fall within the bounds of the simulation.
- **Foreshadowing bookkeeping:** prophecies, omens, dreams and threads are logged as **setups**. The drama manager tracks open setups and favours their **payoffs** (fulfilment or subversion). The chronicler and the bard are told which incidents are payoffs of which setups, so the narrative reads as authored even though it emerged.

### F37. Structural-demographic and civilisational cycles

The engine tracks the variables of structural-demographic theory per polity, derived from simulated state, not fitted:

| Variable | Derivation |
|---|---|
| **Population pressure** | population against carrying capacity (F2.4) |
| **Popular immiseration** (MMP: mass mobilisation potential) | real wages and SoL of the lower classes (4.1 reference pass) × the youth share of cohorts (F12) × urbanisation |
| **Elite numbers and elite overproduction** (EMP: elite mobilisation potential) | nobles, the wealthy and the credentialed (8.4 reference pass 4) against elite positions (offices, titles, land, benefices). Overproduction yields **counter-elites**: aspirants with no position who lead factions, movements and revolts |
| **State fiscal distress** (SFD) | debt, revenue against expenses, corruption |
| **Political stress index** (PSI) | MMP × EMP × SFD |

- **PSI raises:** faction formation, revolt and coup probabilities, the threshold drops of the collective behaviour model (F32), and the drama manager's crisis weights.
- **Secular cycles emerge:** growth (land abundant, wages high), stagflation (land scarce, elites grow), crisis (PSI peaks: civil war, plague, collapse) and depression or recovery (population falls, elites thin). There is no scripted cycle: the variables are the readings of an emergent process, kept for the UI and for decision weights.

**Asabiyya** (group solidarity) per people and polity:

- It **rises** at meta-ethnic frontiers: regions bordering peoples with a large value distance (F5), with continuous conflict and a shared enemy. Frontier peoples unify and expand.
- It **decays** with generations of luxury (SoL above the comfort tier for [3] generations, F12), elite intrigue (PSI) and distance from frontiers.
- Asabiyya multiplies cohesion, mobilisation, army morale and resistance to assimilation. Ibn Khaldun's cycle of desert conquerors becoming soft dynasties overthrown by new frontier peoples therefore emerges.

**Challenge and response:** a challenge index (disasters, climate shocks, invasions, plagues, measured as losses against capacity) feeds research boosts (8.4 reference pass), innovation in institutions (civic techniques), and asabiyya. Too little challenge brings stagnation, and too much brings collapse. A middle band of severe-but-survivable challenge produces the strongest responses (`cycles.response_band`).

**Long plans:** polities, cults, orders and gods can hold **long plans** (`long_plans`: holder, goal (an ecological transformation, a bloodline, a conversion of a world, a wonder), steps per epoch, progress, secrecy). Plans outlive their authors and are carried by offices and orders, so centuries-long projects (Dune-style terraforming of a desert world, a breeding plan of a secret order) are typed, trackable and disruptable.

### F38. Reciprocity and gift exchange

**Gift ledger** (`gifts`: giver, receiver, value (by the receiver's preferences, F15), occasion, returned (bool), epoch). Gifts create **obligations** under the culture's reciprocity norm (F35):

- to accept (refusal is an insult);
- to return in kind and in time (an unreturned gift is a status debt);
- to give more to rise in rank.

Gifts operate between households, houses, polities, cults and gods.

- **Competitive giving** (potlatch-like): rank is claimed by giving or destroying wealth at gatherings (F25). Rivals must match or lose prestige, which drains treasuries and redistributes goods (Loop R of status competition, braked by ruin).
- **Ceremonial circuits** (kula-like): valued items circulate along fixed circuits of communities, never stopping. Holding a famous item briefly gives prestige, and the circuit binds distant communities in peace (relation +) with obligations of hospitality.
- **Sacrifice as exchange** (do ut des): offerings to gods are gifts that create a *divine* obligation in the doctrine. Gods who fail to return favour (unanswered prayers after sacrifices) lose standing faster (9.1), and gods who return generously gain it. Sons see their "gift debts" to peoples as a typed list in their context.
- **Dowry, bride price and bride service** are marriage gifts (4.1 reference pass 4) with the same obligation logic.

### F39. Nutrition and diet quality

Food is no longer only quantity. Each household and cohort has a **diet** (the shares of staples, protein, fats, fresh produce, salt, and special foods), derived from consumption (F3.2, F24) and cuisine.

- **Nutrition score** per mortal and cohort: the energy sufficiency plus a micronutrient balance (deficiency kinds: protein, fresh foods, salt, iodine-like, and world-specific ones for non-human biochemistries).
- **Effects:**
  - stature and strength at maturity (childhood nutrition sets adult attributes, so famine generations are shorter);
  - immunity (disease resistance);
  - fertility and childbirth risk;
  - cognition in children;
  - deficiency diseases as F30 packages (scurvy-like on long voyages without fresh food, goitre-like inland without salt).
- **Couplings:** voyages need provisions with fresh food or the preservation techniques that keep it (7.3). Nobles eat better and grow taller (stratification visible in bodies). Sieges and famines leave generational marks.

### F40. Decision biases

Engine decision functions (F22) apply **cognitive biases** weighted by the decider's facets and traits:

| Bias | Effect | Raised by |
|---|---|---|
| overconfidence | overestimates own strength | vanity, ambition |
| sunk cost | persists in failing wars, sieges and projects | stubbornness |
| loss aversion | over-weights potential losses | anxiety |
| confirmation bias | discounts belief-contradicting reports | low curiosity |
| recency | over-weights the last incidents | low patience |
| groupthink | councils converge on the ruler's view | a small coalition, dread |
| hostile attribution | reads ambiguous acts as attacks | paranoia |
| optimism | expects good outcomes from plans | cheerfulness |

Biases make decisions fallible in characterful ways. Rulers lose wars they should have ended, and councils follow a paranoid king into catastrophe. The biases are visible in decision explanations ("why", F9).

### F41. Purity and pollution

**Ritual purity states** (`purity`: holder, state, source, until) under the doctrine (4.4) and culture (F16):

- **Sources of impurity:** contact with the dead, birth, blood, certain foods, certain species, certain professions (tanners, executioners, gravediggers), outsiders, or violation of a taboo.
- **Effects:** exclusion from temples, rites and gatherings, from certain professions and from marriage with the pure, until **purification** (bathing, fasting, sacrifice, waiting, a rite).
- **Caste systems:** hereditary purity ranks (jati-like castes with occupations, endogamy and commensality rules) are culture data that combine purity, role norms (4.1 reference pass 3) and stratification. Purity rules shape the division of labour (impure occupations held by low castes), settlement layout (districts by caste, 4.2) and disease (corpse handlers' exposure).
- **Couplings:**
  - epidemics: purity rules can help (quarantine-like avoidance) or harm (exclusion of carers);
  - the injured: wounds as impurity in some cultures;
  - outsiders: hostility to traders, and trade restricted to designated markets.

### F42. Luck, charms and witchcraft

**Luck beliefs:** cultures hold beliefs about luck, such as lucky and unlucky days (F1 calendars), signs, numbers (8.4 reference pass 5) and gestures. **Charms and amulets** are items with a believed effect (protection, fertility, luck). Their real effect depends on the world: real where enchanted or blessed (8.6, a god's answer, a natural law), placebo otherwise (stress −, confidence +, which is a real psychological effect through F14). The difference is player-visible.

**Witchcraft as a believed cause of misfortune** (Evans-Pritchard-style):

- In cultures with a witchcraft belief, unexplained misfortunes (illness, crop failure, the death of a child, livestock deaths) are attributed to **witches**. The accused is chosen through belief state (F22), grievances and social distance: envied neighbours, widows, outsiders, the eccentric.
- **Accusations** follow divination (8.7 reference pass 4) or rumour (F11 reference pass 3), and lead to trials (4.5), ordeals, exile or killing.
- **Witch hunts** are collective behaviour cascades (F32) under stress (plague, famine, war, PSI) and with zealous authorities (cults, inquisitions). They are major incidents with memories, accounts and ghosts (wrongful deaths: vengeful ghosts, 3.3 reference pass).
- **Real witches:** where rites (8.6) and curses (F30) exist, some accused may really be casters. The engine knows who is, and the player can see accurate and false accusations. This is a uniquely sharp beyond-the-leader effect: a world where magic is real makes the witch-hunt ambiguous rather than simply false.

### F43. Identity layers and salience

Every mortal and cohort holds several **identities** (`identities_held`: holder, layer, value, strength):

| Layer | Example value |
|---|---|
| people | ethnicity |
| faith | |
| class or estate | |
| settlement or region | locality |
| house or clan | |
| guild or profession | |
| age-set or generation | |
| polity | subjecthood or citizenship |
| circle or party | |

**Salience** (0–100 per layer) decides which identity dominates behaviour and loyalty at a given time. It shifts with:

- **events:** a holy war raises faith salience; a famine raises class salience; an invasion raises people and polity salience; a guild strike raises profession salience;
- **rhetoric:** sermons, propaganda and movements (F21, 4.4 reference pass);
- **segregation:** districts by caste or people (4.2);
- **cross-cutting ties:** marriages across lines and mixed guilds lower the salience of the lines they cross.

**Effects:**

- **Conflict lines:** factions, revolts, riots (F32) and civil-war sides form along the most salient layer. The same city splits by faith one decade and by class the next.
- **Cohesion:** high salience of a shared polity identity raises mobilisation and stability. High salience of a sub-identity raises separatism (4.6 reference pass).
- **Opinion and trust** (F7, F18) gain an in-group term per shared salient identity.
- **Collective memory** (F33) is curated by identity groups, each telling its own history.

Salience replaces ad-hoc "same god" and "same language" bonuses with one general mechanism, keeping them as special cases.

### F44. The technology ceiling: advanced eras

The tech graph (8.4) is extended so that worlds can reach any technology level the genesis setting or history allows, not only pre-modern, magical and cosmic branches.

**Eras and branch families:**

| Era | Families and representative techniques |
|---|---|
| Ancient–classical | (existing) agriculture, bronze and iron, writing, architecture, seafaring, astronomy, medicine, law, coinage |
| Medieval–early modern | (existing plus RP) mills, clocks, optics, printing, double-entry bookkeeping, universities, blast furnace, compass navigation |
| Gunpowder | gunpowder (forbidden or chemistry branch), firearms, cannon, star forts (fortification), muskets and drill (discipline) |
| Industrial | steam power (energy, F24), coke smelting, machine tools, railways (land transport), steamships, factory production methods, industrial chemistry, canned food (preservation), vaccines (medicine) |
| Electrical | electricity generation, the telegraph and telephone (communication delays collapse, F21), electric light, refrigeration, the internal combustion analogue, aviation (air transport, air superiority, 5.5) |
| Information | computation, radio broadcasting (mass public opinion, F21), mass media, antibiotics (disease mortality), the green revolution (yields) |
| Advanced | nuclear-analogue power and weapons (dangerous; doom +), non-magical spaceflight (an interworld route method `rocketry` obeying launch windows, 10.4 reference pass 5), genetic engineering (biomancy analogue), artificial minds (constructs, 3.3a reference pass 4) |

**Rules:**

1. **Every technique uses the same machinery:** prerequisites, boosts, theories (8.4b: electricity needs a correct theory of it), materials (F3: copper, rubber-like, rare earths of the world), energy sources and production methods (F24). Industrial methods transform the economy through the method transitions (F24): unemployment, urbanisation (demographic transition, 4.1 reference pass 3), pollution, new classes (industrial workers, engineers, financiers as faction kinds).
2. **War changes form by era:** unit kinds gain era variants (musketeers, line infantry, artillery, rifles, armoured vehicles, aircraft) through the same stack, penetration, frontage and logistics models. Lanchester's square law grows in weight with ranged firepower, and logistics needs fuel and ammunition at industrial scale.
3. **Magic and technology coexist:** worlds can have both, with interactions. Iron and electricity disrupt certain rites (8.6), and some theories (8.4b) unify them. Cultures choose paths (a magic-heavy or technology-heavy development) through preferences, doctrines and natural laws (a son can forbid gunpowder in a world as a natural law, 9.5).
4. **No ceiling (decision K.13):** there is no era cap, for existing or new worlds. A world advances as far as its history carries it. The genesis technology setting only sets the starting era and the research speed. Worlds may also stay pre-modern for ever, if the rules and history keep them there.
5. **Plausibility guards (decision K.13):** high technology must never turn into absurdity, such as one character destroying the universe. The guards are structural:
   - **Scale gating:** the magnitude of any effect is bounded by the acting entity's scale. A mortal's acts reach a region; a polity's reach a world; an interworld power's reach a system. Only the Creator and cosmic office holders act at cosmic scale. Every mechanic declares its maximum scale per actor kind.
   - **Collective prerequisites:** world-scale and system-scale techniques (nuclear-analogue weapons, star-lifting, planet engines) require polity-scale programmes over generations: institutions, industry, materials and many specialists. They cannot be achieved by one character, however gifted.
   - **Visible escalation:** dangerous programmes pass through observable stages (incidents, rumours, leak, doom contributions), so other actors (polities, cults, sons, the council, the Creator) can respond, oppose or sabotage before the final step.
   - **Physical bounds:** effects obey the derived physics (10.9) and conservation (F28). No technique creates energy, matter or souls from nothing outside divine acts.
   - **Fate's plausibility check:** creations and transformations involving dangerous techniques are judged by Fate against these guards, and implausible results are corrected or rejected.
   - **Cosmic ends remain the doom clock's:** the destruction of a world or the cosmos happens only through the doom mechanics, divine wars or the Creator's acts, never as a side effect of one mortal invention.
6. **Gods and high technology:** secularisation (4.4 reference pass 4) accelerates with information-era media and correct theories. Sons respond (miracles, revelations, natural laws), and outer beings take interest in dangerous techniques (leak +).

### F45. World-type applicability rules

Every foundation reads the world type through one **world-type profile** (`world_type_profiles`, rules namespace `world_types`). The profile states how each foundation family behaves. Ordinary worlds use the defaults. The other types override them as follows:

| World type | Ground and regions | Sky, light, seasons, weather | Life, food, materials | War, travel, settlement, special |
|---|---|---|---|---|
| ocean | few islands and reefs; most regions are water regions with depth zones (shallows, open sea, abyss) as habitats | strong storms, monsoon-like circulation, tides from moons | fisheries and kelp farming are the staple; coral, pearls, shell; wood is scarce, so ships are built from reef timber, bone or magic | naval war dominates; underwater peoples (F46 aquatic) fight in three dimensions; floating and stilt settlements; sea level change (10.9) remakes coasts |
| sand | dunes, oases, rock plateaus; wind moves dunes over epochs (settlements can be buried) | heat waves, sandstorms, a large day–night temperature swing, rare rains | water is the binding stock (wells, cisterns, qanat-like channels as structures); dates and herds; glass from sand; salt | caravans dominate travel; water rights are the main casus belli; heat attrition (F2.3); cities cluster at oases (central places) |
| ice | ice sheets over rock or ocean, crevasse fields, geothermal oases | long night and long day by latitude, blizzards, auroras | sea hunting, fishing through ice, lichen-herding and geothermal greenhouses; heat (F24) is a survival need; bone and ivory replace wood | sledges and ice ships; winter campaigns are deadly; settlements around thermal vents; frozen corpses preserve the dead (spirits of the unburied are common) |
| lava | volcanic fields, lava rivers, ash plains, cooled basalt islands | ash weather, acid rain, a glow of lava at night (light without a sun) | fire-resistant species; volcanic soils are rich where cooled; obsidian, sulphur, metals; fire is ambient (timber ignites, F23) | heat-proof materials needed for structures; lava flows change regions (tectonics, 6.1 reference pass); fire peoples (F46) |
| crystal | crystal bedrock, refractive plains, resonant caverns | refraction storms (light weather), harmonics (sound carries) | crystal growth as a resource that regrows; few soils, so food from crystal-feeding species or imports | resonance magic ×; crystal weapons with high edge but brittle (F23); acoustic signalling networks |
| living | flesh terrain, vein rivers, bone ridges; regions are organs with functions | "weather" is the world's breath, fever and sleep, tied to its mood | the world feeds those who honour it; mining and clearing wound it (world mood, 10.2) | the world itself is an actor: wounds bring quakes and immune-like fauna; worship of the planet changes everything |
| dead (realm of the dead) | strata regions (3.3), rivers of forgetting, gates | grey light, no seasons unless a god wills them | no births; the dead do not eat but need offerings from the living (F38); materials are memory and bone | souls are the population; war between strata or against invaders from the living; travel by the river of the dead (existing method) |
| dream | regions shift with dreamers' beliefs (10.2 reference pass 3) | weather of moods; time loose (time_factor drifts) | sustenance is belief; materials can be dreamed into being by strong dreamers at a sanity cost | injuries are psychological (F30 trauma) but real for dreamers; dying in a dream traps the dreamer (heroquest rules, 8.2 reference pass 3) |
| mirror | regions mirror the twin world's | weather mirrors with inversion | what dies in one is born in the other (existing twin rule); mirror materials | events echo between twins; travel through mirrors; identity confusion between twins (F20) |
| gas (gas giant) | no surface: regions are cloud bands and altitude layers | perpetual storms, bands of wind, lightning, a vast sky | aerial plankton and floating flora; gas harvesting as mining; buoyant materials | floating settlements and sky-cities (buoyancy upkeep); only sky warfare (5.5); falling is death; peoples are aerial or gaseous (F46) |
| ringed | as ordinary, plus ring shadows | shadow seasons (existing capacity effect); meteor showers from the rings | ring ice and stone mined by sky-ships | the rings as a visible calendar and omen; ring fragments as impacts (10.9) |
| asteroid belt | regions are rocks of various sizes; micro-gravity | no weather; space weather only; light from the distant star | no soil: food from domes, magic or imports; mining is the economy | travel between rocks needs vessels; boarding warfare; air is a stock (sealed habitats, magic, or air-free peoples) |
| tidally locked | bands: the day side (scorched), the terminator (habitable), the night side (frozen) | no days and no seasons; constant winds from the day to the night side; weather fixed by band | farming in the terminator; night-side ice and day-side metals | the habitable band is a ring-shaped world; war along it; expeditions into the day or night side are survival trips (6.2 reference pass 4) |
| void pocket | a small bounded region set in nothing | no star: light from magic, divine fire or phenomena; no seasons unless made | everything imported or conjured; leak is high | mortals are few; sanity is the binding constraint; outer beings press on the boundary |
| god's palace | divine terraces, halls and gardens (existing geometry) | seasons and weather follow the resident god's mood and scales (F31) | servants are fed by the god; divine materials | the god's dominion is absolute; mortals are servitors or guests; disease and ageing as the god permits |
| generation ship | regions are decks and sections (existing geometry); no geology | ship cycles in place of days and seasons; "weather" is system failures (air, heat, light) | closed ecology: conservation is strict (F28), recycling is the economy, mining is salvage | ship ageing (components, 7.3 reference pass 3), mutiny as revolution, lost purpose and myth of the destination (F33), disease in a closed population |
| corpse-world | regions are the god's body parts (existing ribs geometry); decay soils | sky of the god's fading light; seasons of decay | rich, eerie soils; bone and godflesh materials (F3); spirits are many | necromancy cheap; the dead god's will as a phenomenon; pilgrims and grave-robbers |
| super-earth | broad plains, low worn mountains and deep seas; large regions | thick air: strong storms, mild climates | heavy bodies need more food; deep weathered soils | high gravity (forced): flight costly, armies slower, missiles short, buildings squat; tectonic quakes ×1.5 |
| ice giant | no surface: cloud bands and pressure layers, as on a gas giant | cold perpetual storms; extreme-tilt seasons | floating ice plankton; ice and gas harvesting | as a gas giant: sky war only, floating settlements; the pressure deep as a hazard; storms ×2 |
| hot giant | no surface: a scorched day band, a dark night band and a living twilight belt | endless day toward its star (no night battles), supersonic winds, iron rain | glowing aerial life in the twilight belt | floating settlements only in the twilight belt; fire peoples (F46); storms ×2.5 |
| iron world | metal plains, rust fields and iron cliffs; thin soils | thin air (forced), magnetic storms (navigation errors), auroras | ore yield ×2, iron and lead layers; food is scarce | metallurgy cheap and weapons abundant; high gravity (forced) |
| diamond world | graphite plains, tar seas, diamond mountains | soot haze; dry ages | gems abundant (wealth, trade); ash soils | the diamond trade drives the economy; tar pits as hazards |
| greenhouse world | baked basalt plains and volcanoes; almost no water | toxic crushing air (forced), acid rain, no seasons | water and food are the binding stocks; sulfur; fertility decays each epoch | life only in high cloud cities or sealed habitats; colonies without void living fail; droughts ×2.5 |
| dwarf world | a small cratered body of frost plains and nitrogen glaciers | almost no air (thin, forced), a long winter and a short thaw (two seasons) | ice mining; food from vents or imports; ore yield ×0.7 | low gravity (forced); air as a stock; travel by cosmic mount; no storms or floods |
| chthonian world | molten scars and iron plains: a giant's bared core | no air (forced), endless day toward a close star, no seasons | metal and gold abundant (ore yield ×1.8); no soil | survival habitats only; fire and construct peoples (F46); quakes ×2.5 |
| steam-ocean world | nearly all ocean with rare rock isles and steam vents | hot, humid, dense air (forced), endless rains | fisheries and kelp under steam; salt | naval war; floating towns; heat attrition; storms ×2, floods ×1.5 |
| jungle world | rainforest and swamp from pole to pole (jungle terrain, peat soils) | heavy rains, flood seasons | plant and animal abundance; amber; a high disease load (plague ×1.5) | ambush war, slow armies, floods ×1.5 |
| forge-world | worked land: foundries, slag rivers, open-pit terraces | a dense soot sky (forced), scorched ages | ore yield ×1.6, iron and copper; soils poisoned by soot (fertility decay) | craft economies; pollution (F24); mining quakes ×1.5 |
| fungal world | mycelium ground and giant fungus forests | spore fog, damp rain ages | fungal food; spores that carry disease (plague ×2) and dreams | sanity erosion; dream routes as hidden routes |
| shattered world | floating continents around the burning wound of its heart (fragment map) | low gravity (forced), debris in its sky | star metal from the heart; thin soils; ore yield ×1.3 | travel between fragments by flight or mounts; falls are lethal; route danger +8; leak +1; quakes ×2 |
| hollow world | the inside of a shell lit by an inner sun; polar openings | endless day, no seasons, no night battles | steady growing seasons; gems | the polar openings as gates to the outside; low gravity (forced); its shell repairs leak |
| ice-shell world | an ice crust over a hidden ocean; geysers and vent gardens | thin air (forced), cold ages | life at the vents of the ocean below; salt | under-ice (aquatic, F46) peoples; cryoquakes ×1.5 |
| methane world | methane lakes, haze dunes, cryovolcanoes | dense cold haze (forced), methane rain | hydrocarbon life (an exotic biochemistry, 10.9) | cold-adapted or exotic peoples; methane floods ×1.5 |
| ordinary | defaults | defaults | defaults | defaults |

Each row is data: the profile's fields override foundation parameters (rules), toggle mechanics (no fire without oxygen, no soil on asteroids), and replace spatial units (cloud bands, decks, strata) while keeping the same graph-based machinery.

#### F45 reference pass 9: the dead without scavengers

On worlds or regions without scavenger fauna, the carrion pulse (3.2 reference pass 8) does not run. The dead **accumulate** and are preserved by the environment:

- mummified in deserts and on dry worlds;
- frozen on ice worlds (preserved bodies, later finds, re-released diseases, F47 eradication);
- drifting on gas giants (falling to the crushing depths);
- floating in asteroid and void habitats (a hazard and a source of hauntings).

Unremoved dead raise the restless-spirit chance (3.3) and make funeral logistics (cremation fuel, burial in limited space) a real cost.

### F46. Biology applicability rules

`people_biology` and species profiles select a **biology variant** (one or several). Each variant changes how the foundations apply:

| Variant | Body and harm | Sustenance and reproduction | Culture and technology | War, disease and death |
|---|---|---|---|---|
| incorporeal | no tissue; harm is to **coherence** (a spirit pool). Iron, salt, sanctity and rites harm; blades pass through | sustained by belief, emotion or place-binding; reproduce by division or by gathering souls | cannot hold tools without possession or binding; writing by impression on minds or dreams | cannot be blinded or bled; disease does not apply but warping and dispersal do; death is dissipation, with possible re-formation |
| aquatic | gills or skin breathing; dehydration on land | aquatic diets; spawning seasons and many offspring | no fire: metallurgy through volcanic vents, magic or trade; writing by carving, knots, shell inlay or pigment in mucus; sound-based languages carry far | three-dimensional war; land invasion is costly; waterborne disease dominant; burial in the depths |
| aerial | wings (flight function); hollow bones (fracture risk) | high metabolism (food need +); nests on heights | light materials; sky settlements; navigation by winds | air superiority native; vulnerable to storms; falls are lethal injuries |
| subterranean | dark-adapted senses; light sensitivity | fungal and root diets; low metabolism | tunnelling engineering, cavern cities, little astronomy (no sky) unless surface contact | ambush and tunnel war; surface light is a weapon; cave diseases; ossuaries |
| hive | individuals are cohort members; the queen or mind as the vital organ of the colony | castes (4.1 reference pass 4); the breeding caste; rapid replacement | collective decisions (no individual politics; the hive mind trait); architecture by secretion | expendable soldiers; hive death on queen death; colony-level disease |
| plant-like | photosynthetic tissue; slow movement; regrowth of limbs | sunlight and water as food; seed or cutting reproduction; long lives | rooted settlements (mobility low); horticultural technology; fire is a mortal fear | slow armies, strong defence; fire weapons devastating; blight diseases; decomposition as afterlife rites |
| construct | material body (F23 by material); no pain; repair instead of healing | power source upkeep (3.3a reference pass 4); manufacture instead of birth | instruction-bound minds that may grow will; craft precision | no morale; dispels and command loss; no disease but rust, wear and corruption; death is breakdown, possible reactivation |
| ageless | no senescence (the existing immortal flag generalised to peoples) | very low fertility to keep demography stable | very long memory: legends distort slowly (8.2), grudges last for ever (F7) | deaths only by violence, disease or magic; generations overlap for centuries (F12) |
| shapeshifting | multiple body plans per individual with transition costs | reproduction in the base form | identity is fluid: impersonation is easy (F20 identities), trust is low (F18) | form choice in battle; recognisability low; forms carry different weaknesses |
| gaseous | diffuse bodies; harm by dispersal (wind, heat) | sustained by atmosphere composition (10.9); fission and fusion | no solid tools; technologies of pressure and chemistry; languages of colour and scent | live only in fitting atmospheres; vulnerable to storms; disease as contamination |
| crystalline | crystal tissue (high hardness, brittle, F23); heal by growth | mineral diets; growth reproduction (budding) | resonance languages; lapidary arts native | resistant to blades, shattered by blunt force and sound; slow healing; death leaves gemstones (a grave-robbery motive) |
| undead | dead tissue: no pain, no healing without necromancy, decay over time | sustained by the necromantic bond, essence or souls; no reproduction (only creation) | culture of the bound (constructs-like) or of free undead (with memories) | no fear (morale immune) but holy harm; plague-carriers; destruction is release to the afterlife (3.3) |

The variants combine. An aquatic hive is possible, for example. Their rows are data in `biology_variants`, and every foundation reads them through the biology view of the people or species.

#### F46 reference pass 9: components and biases by biology

- **Rite components by biology:**

| Variant | Casting |
|---|---|
| incorporeal | mental and spoken-by-presence components only |
| construct | inscribed and material components, with mental components only if ensouled |
| aquatic | sung and gestured components underwater, but not inscribed with ink |
| hive | mental components through the hive mind, cast collectively |
| gaseous | colour and scent components replace the spoken ones |
| plant-like | slow material and growth components; their rites have long casting times |

  The F4 function check is applied to the variant's own body plan.
- **Decision biases by biology:**

| Variant | Biases |
|---|---|
| construct | no emotional biases (no loss aversion, no hostile attribution); literalism instead (orders followed beyond their purpose) |
| hive mind | groupthink at its maximum and no individual vanity; a different bias, **colony risk aversion** (over-protection of the breeding caste) |
| ageless | sunk-cost and grudge biases strengthened by long memory; recency weakened |
| undead | biases of their bound instructions, or of their living imprint for free undead |

### F47. Lifecycle ends and decay rules

The stocks and lifecycles that A1 and A2 found unbalanced get their missing ends:

| Item | Rule |
|---|---|
| **Ideology decline** | adherents fall when the ideology's appeal falls (pressures it addressed are relieved, its predictions fail, its adherents are persecuted without martyrdom effects, rival ideologies win debates). Below a floor of adherents and texts, it becomes **dormant** (recoverable from books). With no texts left, it is **extinct** (only accounts mention it) |
| **Rite loss** | a rite is lost when no living practitioner knows it and no text (lab text, scripture) survives. Partial texts allow **reconstruction** (research with an error risk: a corrupted rite) |
| **Theory oblivion** | a theory with no adherents and no surviving texts is forgotten. It can be rediscovered independently (research) or found in excavations |
| **Disease eradication** | a disease with no infected hosts (people and reservoir species) for `epidemiology.eradication_epochs` [3] is eradicated. A frozen or sealed reservoir (a tomb, an ice body, a sealed vault) can re-release it |
| **Outer being banishment** | an outer being is **banished** when its breach points are sealed (rites, wards, god acts), its cults destroyed and its interest falls below a floor. It is **destroyed** only by acts of the Creator or a cosmic office holder at great cost. Banished beings keep a memory of the world (a return risk tied to leak) |
| **World end states** | shattered (impacts, divine wrath: it becomes an asteroid belt), swallowed (by its star's giant phase, 10.1 reference pass), frozen dead (a star's death: life ends, ruins remain), sunk into the void (the existing visit of the void at world scale), forgotten (existing), transfigured (belief drift to a new world type, 10.2 reference pass 3). Each has typed consequences for souls, routes, peoples abroad (diasporas lose their homeland) and gods (anchors lost) |
| **Favour expiry** | favours decay by `favours.decay_pct` [10] per epoch, faster in cultures with weak reciprocity norms. They vanish at the debtor's death unless the culture inherits obligations (F38) |
| **Local reputation decay** | each reputation axis decays toward neutral without new deeds or retellings. Legends and accounts (F33) slow the decay, and monuments freeze it |
| **Secret obsolescence** | a secret loses value when its subject dies, when the truth becomes public, or when the matter stops mattering (the illegitimate heir's line ends). Hooks based on it weaken accordingly |
| **Ruler currencies** | prestige decays slowly without new achievements. Dread decays faster without new displays of force. Tyranny decays very slowly, faster with amends (restitutions, pardons, public penance) |
| **War weariness recovery** | weariness falls in peace by `war_weariness.recovery_pct` [15] per epoch, slower while the maimed cohort is large (F4.5) and while memories of the war are relived (F33 commemorations) |
| **Warping fade** | warping fades slowly away from magical exposure, except for permanent stages (F30 packages marked permanent) |
| **Magic site exhaustion** | sites yield from a reservoir that regenerates by the site's nature (a ley flux, a beast's lair, a god's favour). Over-harvesting exhausts them for epochs. A god's death or a ley severance can kill a site, and new sites arise at new nexuses and god corpses |
| **Thrones of power** | thrones can be **destroyed** (desecration with a rite, divine war) and **arise** (on god corpses, at the sites of world-changing incidents with the highest magnitude, or by a son's sacrifice of essence). The count per world is a soft cap |

### F48. Prehistory and deep-time runs

**Prehistory run.** When a world is created (genesis, a son's world birth, a horizon intuition becoming a world), the engine runs an **accelerated, LLM-free prehistory** of `prehistory.epochs` epochs before the world joins the live cosmos (decision K.14). The default is **0**: a world starts from the Creator's and the sons' creations alone. The player can choose any length in the genesis wizard or when a son births a world, and can later **seed a prehistory** for a world that is still empty of lore. All the rules below apply whenever the length is above zero.

- **Which mechanics run:** the full engine pipeline with a reduced mechanic set (`prehistory.phases`): physics, climate, ecology and evolution, demography, migration, ethnogenesis, language sound change and divergence, settlement growth and ruin, polity rise and fall, war at aggregate resolution (battles without named-mortal detail unless promoted), religion spread, knowledge, legends and accounts.
- **Speed:** cohorts only (named mortals are promoted only for rulers, founders, great people and heroes), fewer sampled years and campaign seasons, and coarse rules (`prehistory.resolution`).
- **Output:** a world that begins *with history*: language families with cognates, ruins and lost cities, extinct species and fossil beds, dynasties and dormant titles, old grudges (memories, irredentist accounts), myths distorted from real prehistoric incidents, sacred sites, old roads and diasporas.
- **Fate and the chronicler** receive a **prehistory digest** (top event collections by magnitude) to write the world's legendary age in prose. Names are assigned in batches (the existing naming flow), and the cosmology from genesis is checked against the simulated prehistory, with Fate reconciling conflicts.

**Deep-time fast-forward.** The player can run a world forward N epochs in LLM-free mode (the existing `AERONA_LLM_ENABLED=false` path made a first-class lever), with a digest at the end. Sons' turns are skipped or simulated by their goals, values and standing (a policy model of the son built from F13 layers and goals) for the duration.

**Determinism and cost:** prehistory uses its own RNG domain (`prehistory.{world}`) and the parallel engine (J.11). Its cost is budgeted separately (`engine_budget.prehistory_seconds_per_epoch`).

#### F48 reference pass 9: prehistory by world type and for existing worlds

**Prehistory by world type** (F45 profile field `prehistory_kind`):

| World type | Prehistory kind |
|---|---|
| ordinary, ocean, sand, ice, lava, crystal, ringed, tidally locked, asteroid belt, gas giant, super-earth, ice giant, hot giant, iron, diamond, greenhouse, dwarf, chthonian, steam-ocean, jungle, forge, fungal, shattered, hollow, ice-shell, methane | the full accelerated run |
| living world | the full run, plus the world's own mood history (its old wounds and favours) |
| realm of the dead | the arrival history of souls: strata formed by the dead of its source world's prehistory, old judgements, ancient ghosts and lost kings of the dead |
| dream world | no causal prehistory. A **dreamt past** is generated from the dreams and myths of the dreamers who reach it, and it changes as they change (10.2 reference pass 3) |
| mirror world | its twin's prehistory, mirrored |
| god's palace | the god's own deeds (its epic, the existing `Epic`), rendered as the history of the palace |
| generation ship | the **voyage history**: departure (from a source world's accounts), generations aboard, failures, mutinies, lost decks, myths about the destination |
| void pocket | none, or the history of the phenomenon it grew from (F49) |
| corpse-world | the god's life and death as the world's founding era, then the settlement of its body |

**Existing worlds (G10).** Worlds that already have written lore do **not** get a simulated prehistory, because it could contradict their canon. Their deep past is **backfilled from lore only**:

- previous-creation records, ruins, ancient legends and old languages are mapped to prehistoric collections and accounts;
- language families come from the existing parent-language links;
- dormant titles come from fallen polities in the chronicle.

Prehistory runs only for worlds born after the upgrade, or on the player's explicit request for a world that is still empty of lore.

#### F48 reference pass 10: prehistory fallbacks

- **A generation ship without a source world:** the prehistory generates a **lost origin**. A source world is created as a record with discovery `forgotten` (the existing value), with a short prehistory of its own as the ship's founding myth. It is reachable only by legend, or by a later discovery (a horizon intuition, a quest).
- **A mirror world whose twin does not exist yet:** mirror worlds are created **as a pair**. One shared prehistory is run and mirrored, so neither world has a history without the other. When a son makes an existing world into a mirror's twin, the mirror receives the twin's existing history, mirrored, with the inversion rules.

### F49. Transformation graph (type changes)

Entities and records can **change type** through typed transformations. A transformation keeps the node identity where possible (name, history, bonds, memories and accounts carry over to the new type; the old type's state maps by rules) so that history is continuous.

| From → to | Status | Conditions and process |
|---|---|---|
| mortal → son | existing (deification), extended (mantling, 3.1 reference pass 3) | Fate approval; worship; aspect deeds |
| son → mortal (**fall**) | new | a son stripped of divinity by the Creator, by the council (9.4) or by fading below a floor while anchored in a mortal body. A fall by the council or by fading is announced to the player one epoch ahead, with the J.16c levers to block it (decision K.11). It becomes a mortal with high attributes, memories of godhood, a hidden true name and no essence. It can try to regain godhood (a heroquest, mantling) |
| mortal → spirit | existing | death, unrest |
| spirit → mortal | existing (reincarnation, possession) | — |
| spirit → god | existing (local gods, genius loci promotion) | worship growth |
| mortal → beast and back | existing (F30 curses) | — |
| species → people | existing (uplift) | intelligence threshold |
| people → species (**loss of sapience**) | new | a catastrophic curse, a void taint at full stage, isolation and regression in a dark age under a natural law, or a god's punishment. Culture, language and records end; the remnant becomes a species with feral traits and possibly legends of a fallen people. It is rare and tunable |
| cult → people (**ethnoreligious ethnogenesis**) | new | a cult with high cohesion, endogamy rules and a diaspora (4.1 reference pass 3) across generations becomes a people with its own culture vector, keeping its faith as an identity layer (F43) |
| polity → people (**nation-building**) | new | a polity with high polity-identity salience (F43), a standard language policy (8.1 reference pass 3) and schooling across generations forges a new people from its subjects: ethnogenesis led by the state |
| house → people | new | a clan that grows across many generations into a tribe (segmentary lineages, 4.7 reference pass 4) becomes a people named after its founder |
| settlement → polity | existing (city-state) | — |
| faction → polity | existing (secession, rebels) | — |
| cult → polity | existing (theocracy) | — |
| polity ↔ title | existing (4.11) | — |
| legend → species, spirit, item, resource | existing (manifestation) | credence |
| artwork ↔ legend | existing (a legend fixed into an artwork; a lost artwork remembered as a legend) | — |
| event → phenomenon | existing | — |
| phenomenon → world (**pocket world**) | new | a phenomenon of high intensity with a void, dream or time nature that grows past `phenomena.world_threshold` [95] detaches as a void pocket or dream world with its own routes |
| world → god (**world-soul ascension**) | new | a living world (10.2 reference pass) with worship from its peoples (the existing worships-planet flag) and high consciousness can ascend as a foreign god whose body is the world. The world becomes the god's anchor, and harming the world harms the god |
| god → world or place | existing (god corpse places, corpse-worlds) | — |
| star or celestial → god | new | a star worshipped long and widely, under a natural law or a son's act, gains a star spirit that becomes a foreign god anchored to the star (sun gods made literal). Its dominion follows its light |
| ideology → cult (**sacralisation**) | new | an ideology whose founder is venerated, with rites and a promise of salvation, under a crisis, becomes a cult with a patron (the deified founder through mantling, or a god who claims it) |
| cult → ideology (**secularisation**) | new | a cult under secularisation pressure (4.4 reference pass 4) whose adherents keep its ethics but drop its worship becomes an ideology. Its patron god loses standing but its tenets survive as beliefs |
| item or structure → beast | existing (constructs, golems) | — |
| species → beast | existing (promotion) | — |
| beast → species (**progenitor**) | new | a beast that breeds (a unique monster with offspring, or a god-touched creature) founds a species line that inherits its traits and its legend ("children of the Wyrm") |
| outer being → foreign god | new | an outer being worshipped long enough by in-cosmos cults, under low leak resistance, enters the cosmos as a foreign god. It is bound by cosmic law and keeps its hunger (9.6) |
| son → outer being (**corruption**) | new | a son at sanity zero after void bargains (existing outer bargains) passes out of the cosmos and becomes an outer being, keeping its memories and grudges, and its worshippers become an outer cult. Decision K.11: the player is warned when a son enters the corruption danger band (`transform.corruption_warning_sanity`). From that point on there are intervention levers (cleanse, forbid bargains, chain, a council intervention, a redemption heroquest by worshippers), and the transformation runs only if they fail or are not used |
| beast or colossus → place | new | the corpse of a colossal beast becomes a place (bone hills, a skull cave, a petrified serpent ridge) with materials and a haunting, as god corpses already do |
| language → dead → revived | existing | — |
| knowledge ↔ theory | existing (8.4b) | — |
| tradition → law | existing (customary law codified, 4.5 reference pass 3) | — |

**Rules:** each transformation is an incident, has a rules namespace (`transform.*`), a Fate check (J.16), a player lever (force or block it) and a template family (`transform.*`). The compliance test (J.16) includes the transformation registry.

#### F49 reference pass 9: completing the transformations

- **The fallen son (god → mortal):**
  - The son record gets status `fallen` (the son status enum is extended), with a link to the mortal entity that now embodies it. Its powers are suspended, its essence is set to zero and its existence is held at the floor.
  - **Worshippers** keep their worship bond (decision 27 unchanged): prayers go unanswered, so the neglect component of standing grows (9.1) and conversion away accelerates. A loyal remnant may recognise the fallen god in the mortal (an identity claim against evidence, F19 reference pass 6).
  - **Agent mode:** the fallen son keeps its LLM turn as a son agent with the *mortal* tool set and its memories and personality, so it can act to regain godhood (heroquests, mantling) or accept mortality.
  - **Death of the fallen mortal:** if it has not regained godhood, its soul goes to its own realm's afterlife with a divine imprint. It may become a powerful spirit, a restless god-shade (the existing god shade), or the object of a resurrection order (the existing devotion mechanics). The son record then becomes `dead` through the existing god-death path.
- **The corrupted son (son → outer being):** the son record gets status `dead` with the death cause `cosmic_horror` (the existing cause), and an outer-being record is created with a link to it. The son's LLM turns end (outer beings act through the engine only). Its worshippers become an outer cult (stated), its anchor and corpse are skipped (it did not die in the cosmos), and its relations with other sons persist as memories of the outer being (grudges against the pantheon).
- **People → species, record mapping:**
  - the people entity ends with status `destroyed` (merged into the species);
  - its settlements become ruins (the existing rule) with feral inhabitants as species ranges;
  - its languages lose their speakers (the existing language death) and become decipherable dead scripts if written;
  - its titles go dormant;
  - its memories and accounts stay with the neighbours who remember the fallen people (legends of the cursed people);
  - the species keeps a `former_people_id` link.
- **The star-god's death:** a star-god's death dims its star by the god's share of its luminosity (`transform.star_god_dim_pct` [30]), shifts its life cycle forward (10.1 reference pass), cools its worlds and leaves a god corpse as a phenomenon in the sky (a dark spot or a wound in the light). Its worshippers face a theodicy crisis (4.4 reference pass 4) under a visibly dimmer sun.

#### F49 reference pass 10: consistency with the existing engine

- **The fallen son and the fading rule (C1):** while a son's status is `fallen`, the fading rule does not apply: its existence is anchored in its living mortal body. The rule `death.fading_applies_to_fallen` [0] makes this explicit and tunable. Existence instead follows the mortal's renown and the remnant of worship (a weak drift), so a fallen god who regains followers can climb back toward the threshold of godhood (mantling, 3.1 reference pass 3). The fading rule applies again only if the son regains divinity.
- **The fallen son's prompt (C2):** a `PromptId.FALLEN_SON_TURN` template in `prompts/templates/` with a typed context: the son's memories, the mortal body's state (F4), the remnant worshippers and the paths back to godhood. The tool list is the mortal tool set plus `seek_true_name` and `undertake_heroquest`. The existing son-turn prompt is not reused, so the agent is never offered divine tools it cannot use.
- **The corrupted son and the god-death path (C3):** `god_death()` gains a typed **mode**: `in_cosmos` (the existing behaviour: corpse, shade, resurrection order) and `left_cosmos`, which:
  - creates no corpse place and no shade;
  - creates no resurrection order (resurrection is impossible while the outer being exists);
  - transfers the worshippers to an outer cult;
  - records a death-cause row that points to the new outer-being record.
  
  If the outer being is later **banished** (F47), a redemption heroquest can attempt to bring the son back through the existing resurrection mechanics with a special path. The choice of mode is part of the death-cause mapping (`cosmic_horror` with the flag set).
- **People → species conservation (C4):** the transformation writes a typed flow in the conservation ledger (F28): `population → species_abundance`. The population is converted to range abundance by the species' density rule (`transform.people_to_species_density`), so the population test balances. Cohorts of the people are closed with the same flow.
- **The star-god's dimming (C5):** the dimming is a **modifier** on the star's derived luminosity (F9): source `god_death`, permanent or decaying by `transform.star_god_dim_decay`. Stored star physics stay intact, and the derived values (insolation, temperatures, habitable band, F2 temperature bands) follow the effective luminosity. The life-cycle shift is likewise a modifier on the star's effective age.

---

## Part 2T. Entity taxonomy review: are 25 types enough?

### 2T.1 Method

A concept deserves its own entity type only if it passes all four tests:

1. **Identity.** It is named and persists across epochs. It is not a single moment (that is an event) and not a property (that is a stat or row).
2. **Own state.** It carries attributes that no existing type can hold without overloading.
3. **Own behaviour.** At least two engine rules act on it as a subject.
4. **Graph role.** Other entities bond to it in ways that are not already one existing bond kind.

If a concept fails test 1, it becomes a typed table. If it passes 1 but fails 2 or 3, it becomes a typed `engine_kind` of an existing type (with a typed stats block when needed).

### 2T.2 Concepts the world already talks about but cannot model

The audits surfaced concepts that exist only in prose or as overloaded types:

| Concept | Today | Problem |
|---|---|---|
| State / realm / kingdom | a settlement, people or faction holding RULES bonds | No government, treasury, territory, laws-of-the-realm or succession rule. Three types pretend to be states, none is one. |
| Noble house / dynasty / clan | `dynasty_root` name parsing | Inheritance, claims, marriage alliances and feuds between lineages have no carrier. |
| A named individual beast | a `species` row with the megafauna flag | A kind cannot have one dragon's age, wounds, lair, hoard or grudge. |
| A named disease | an `event` (plague outbreak) | The pathogen outlives the outbreak, returns, mutates and has hosts. An event cannot. |
| A treaty, pact or oath | ALLY or TRUCE bonds plus prose | Terms, guarantors, breach and reputation have no carrier. |
| A trade road, sea lane or caravan route within a world | TRADES_WITH bonds with no fields | Distance, capacity, goods, tolls, bandits and control have no carrier. |
| A ritual, spell or working | knowledge branch `magic` plus the WIZARD flag | Magic has no repeatable acts with costs and effects. |
| A school of thought or ideology | nothing (tradition or legend at best) | Value change (F5) has no idea that spreads it. |
| A persistent anomaly (eternal storm, time-slip zone, leak wound) | a place with flags, or an event that never ends | Localised persistent effects have no footprint or intensity. |

### 2T.3 New entity types (9)

| Key | English | Why not an existing type | Creation |
|---|---|---|---|
| `polity` | Realm / state | A people is ethnic, a settlement is a place, a faction is an interest group. A polity is the *government*: it owns territory, offices, treasury, laws and a succession rule, and it can contain many peoples and settlements. | Engine (tier promotion, conquest, union, secession); son tool `found_realm` (uncommon); mortal tool `proclaim_realm` |
| `house` | Noble house / dynasty / clan | A people is too large and a faction is not hereditary. A house is a hereditary line with members, claims, prestige, heirlooms and feuds. | Engine (every ruler founds or continues one); mortal tool `found_house` |
| `beast` | Named individual creature | A species is a population. A beast is one creature, with a body (F4), age, lair, hoard, memories and a name. It is the individual counterpart of species, as mortal is to people. | Engine (promotion from megafauna or monster species, F12); son tool `create_beast` (rare); legend manifestation |
| `disease` | Named disease | An event is a time-bounded outbreak. A disease persists with a vector, virulence, hosts and immunity across outbreaks. | Engine (outbreak with no known disease, mutation); son tool `loose_plague` (epic, Plague domain cheap) |
| `treaty` | Treaty / pact / oath | A bond has no terms. A treaty is a named document with parties, typed clauses, duration, guarantors and breach state. | Engine (every peace, alliance, tribute, marriage); mortal and son diplomacy tools |
| `trade_route` | Road / sea lane / caravan route | Inter-world routes already have a table. Intra-world trade is a bond with no fields. A trade route has a path over regions, capacity, goods, tolls, controller and dangers. | Engine (sustained trade along a region path); mortal tool `open_route` |
| `rite` | Rite / spell / working | Knowledge is a capability and tradition is a custom. A rite is a repeatable act with requirements, a cost, typed effects and a backlash. | Engine (magic and theology discovery); son tool `teach_rite`; cult doctrine |
| `ideology` | School of thought / philosophy / movement | A cult is an organisation and a tradition is a practice. An ideology is a portable idea that shifts value vectors (F5) and spreads. | Engine (from scholars, crises, prophets); mortal tool `found_school` |
| `phenomenon` | Persistent anomaly | An event ends and a natural law is world-wide. A phenomenon is local and persistent, with a footprint of regions, an intensity and typed effects. | Engine (magic storms that do not end, leak wounds, time echoes, god corpses' aura); son tool `shape_phenomenon` (legendary) |

Rarity gates are tunables in `rarity_gates.tur_<key>` (default rarities as listed). Creation base costs are tunables in `creation_base_cost.<key>`.

### 2T.4 Concepts considered and rejected (and where they go instead)

| Concept | Decision | Home |
|---|---|---|
| Office (chancellor, marshal, treasurer, high judge) | table, not entity: it has no life apart from its polity, cult or army | `offices` table under polity / cult / faction (Part 4.6). *Landed and sovereign titles (Duchy of X, Kingdom of Y) were reconsidered in the second pass and are now an entity type: 2T.6, 4.11.* |
| Claim to a title | table | `claims` (Part 4.7) |
| Breed / cultivar | `species` with `domesticated_from` lineage and the `domesticated` engine kind | Part 3.2 |
| Band / company / crew / gang | `faction` with a typed `scale` (band) and typed `kind` | Part 4.3 |
| Guild / bank / court / school institution | `faction` kinds plus `structure` kinds | Parts 4.3 and 7.2 |
| Campaign / front | table under war | `campaigns_fronts` (Part 5) |
| Currency | `item` engine kind plus a `currencies` table for monetary state | Part 6.4 |
| Calendar | `knowledge` with a typed calendar block | F2.2 |
| Shrine / monument / lair | `structure` and `place` kinds | Parts 7.2, 6.2 |
| Fleet | `army` with naval composition | Part 5.1 |
| Afterlife realm | world of type realm-of-the-dead, or region `is_underworld` | Part 3.3 |
| Cohort | table (F12) | — |

### 2T.5 Existing types: kept, sharpened or split

- **event:** kept. Its role is narrowed to *time-bounded happenings*: battles, sieges, disasters, outbreaks, uprisings, festivals of note, coronations. Persistent happenings move to `phenomenon`. Wars stay event entities with the war row.
- **faction:** kept. It gains typed `kind` and `scale` and stops standing in for states (moved to `polity`).
- **settlement / people:** kept. RULES-based statehood moves to `polity`. A settlement or people *belongs to* a polity (new bond `MEMBER_OF_REALM`). A city-state is a polity with one settlement.
- **species:** kept as the population and kind. Individuals move to `beast`.
- **legend vs artwork:** kept separate. A legend is an oral and mutable story (credence, distortion); an artwork is a fixed made work (medium, author, physical or performed). A legend can be *fixed* into an artwork (an epic poem), which freezes its distortion.
- **tradition vs law vs ideology:** a tradition is practised, a law is enforced, an ideology is believed. Each has a distinct engine role (Part 8).
- **outer_being vs foreign god:** kept separate. Foreign gods are cosmic persons inside the cosmos; outer beings are outside it and cannot be worshipped normally.

The new bond kinds the new types need are listed per type and collected in J.3.


### 2T.6 Second-pass taxonomy review: three more entity types

The reference comparison (Part 1R) was run through the four tests again (2T.1). Three concepts pass them and become entity types, which brings the total to **37 entity types** (25 existing + 9 from the first pass + 3 here).

| Key | English | Why it passes and why it is not redundant | Creation |
|---|---|---|---|
| `title` | Landed or sovereign title (Duchy of X, Kingdom of Y, High Seat of a cult) | **Identity:** a title outlives the realm that holds it. A fallen kingdom's title can be claimed and recreated centuries later. **Own state:** de jure territory, rank, holder history, succession law override, emblem, prestige. **Behaviour:** creation, usurpation, de jure drift, inheritance and partition. **Graph role:** mortals and polities hold titles, claims target titles, and titles nest. A polity is the *de facto* government; a title is the *de jure* right. The first pass rejected this as a table (2T.4); that decision is reversed, while offices (chancellor, marshal) stay a table. | Engine (polity creation creates its primary title; conquests create claims); son tool `ordain_title`; mortal tool `create_title` (needs the territory and the prestige) |
| `art_form` | Musical, poetic, dance, visual or dramatic form (a named style) | **Identity:** "the seven-beat lament of the Orvaeli" persists across generations. **Own state:** structure (typed), origin culture, rules, instruments, difficulty, prestige. **Behaviour:** invention, spread, mastery, fusion and decline. **Graph role:** artworks are made *in* a form, performers *know* forms, and cultures *prefer* forms (F15). An artwork is an instance, a tradition a practice, and an art form the *grammar* of a kind of work. | Engine (artists with high creativity invent forms; fusion at cultural contact); mortal tool `invent_form` |
| `theory` | Natural-philosophical or scientific theory (it may be true or false) | **Identity:** "the doctrine of the four humours" spreads, is taught and is overturned. **Own state:** domain (medicine, cosmology, matter, life, mind, magic), correctness 0–100 (hidden truth), explanatory power, adherents, founding texts. **Behaviour:** spread among scholars, contests between rival theories, paradigm shifts. **Graph role:** techniques *depend on* theories, scholars *hold* them, cults *endorse or condemn* them. Knowledge is a capability, an ideology a value programme, and a theory a model of nature whose truth changes outcomes. | Engine (scholars, contact, crises); mortal tool `propose_theory`; son tool `reveal_truth` (raises the correctness of a held theory or plants a true one) |

**Two new cosmic record kinds.** Cosmic records are tables, like stars and worlds, not graph entities:

| Record | Why | Contents |
|---|---|---|
| `star_systems` | Binary and multiple stars and circumbinary worlds need a system level above the star | id, name, star members with roles (primary, companion), barycentre, habitable band, galactic position (replacing star x/y as the canonical position) |
| `cosmic_features` | Nebulae, clusters, black holes, asteroid fields, periodic comets, rogue worlds, wormholes, dust lanes and stellar nurseries shape travel, omens and star birth | kind, position and extent, properties (density, radiation, travel modifier, omen weight), linked routes; a stellar nursery spawns stars over epochs |

**Second-pass rejections** (each one's home is given):

| Concept | Home |
|---|---|
| Household | table (F29) |
| Scheme, secret, hook, favour, identity | tables (F20) |
| Diplomatic crisis | table `crises` (4.6 reference pass) |
| Company or corporation | faction kind `chartered_company` (4.3 reference pass) |
| Holy order | faction kind bound to a cult (4.3 reference pass) |
| Political party or movement | faction kind `party` / `movement` (4.6 reference pass) |
| Megastructure | structure kinds at cosmic scale (7.2 reference pass) |
| Constellation | celestial entity |
| Institution (Renaissance-like movement that spreads geographically) | knowledge of branch `civics` with an `institution` flag (8.4 reference pass) |
| Pet | beast with the companion temper (3.3a reference pass) |
| Dish or recipe | commodity quality and production method (F24) |
| Election, coronation, tournament | event kinds and gatherings (F25) |
| Thought, emotion | tables (F14) |
| Body part | catalog (F4.1) |

### 2T.7 Third-pass taxonomy review

The 18 new lanes were run through the four tests (2T.1). **No new entity type passes all four.** Each new concept fits an existing type or a table:

| Concept from the third pass | Home | Why not a type |
|---|---|---|
| Heroquest | event collection kind `heroquest` (F10 reference pass) | time-bounded |
| Divine servitor (angel, herald) | spirit with `servant_of` and a rank (3.3 reference pass 3) | a spirit with a role |
| Cosmic office (Lord of the Dead) | title of divine rank (2T.6, 9.4 reference pass 3) | a title |
| Global enchantment | natural law with source `enchantment` and upkeep (9.5 reference pass 3) | a scoped rule |
| Magic site, throne of power | place kinds (6.2 reference pass 3) | a place |
| Caravan or convoy | table `caravans` (6.4 reference pass 3) | a moving bundle of goods and people with no identity beyond its journey |
| Criminal organisation, magical order, merchant house | faction kinds (4.3 reference pass 3) | factions |
| Account (an in-world history text) | table `accounts`, carried by artworks, books and legends (F33) | a text about a collection |
| Storylet | catalog (F34) | data, not a world thing |
| Dominion | table (F31) | a field |
| Generation | cohort tag (F12 reference pass 3) | a property |
| Mob | table `mobs` (F32) | short-lived |
| World material | table `world_materials` (F3 reference pass 3) | a catalog row with physics |
| Cipher | knowledge item (F21 reference pass 3) | a technique instance |
| Diaspora | bonds and relations between communities (4.1 reference pass 3) | a relation |

The type count stays at **37**. The third pass adds depth inside them.

### 2T.8 Fourth-pass taxonomy review

The fourth-pass concepts were run through the four tests:

| Concept | Home | Why not a type |
|---|---|---|
| genius loci (place spirit) | spirit with `bound_place` and an office in a celestial bureaucracy (3.3 reference pass 4) | a spirit |
| construct (golem, automaton) | beast (individual) or species with the construct body plan (3.3a reference pass 4) | a body plan |
| long plan | table (F37) | a goal record |
| arc | table (F36) | a narrative reading of figures |
| dream | table (F14 reference pass 4) | a mental event |
| gift | table (F38) | an exchange record |
| art movement, sports club, circus faction | faction kinds (4.3 reference pass 4) | factions |
| kinship system | culture data (4.1 reference pass 4) | a property of a people |
| age of the world (cyclic age) | world and cosmos state (10.8 reference pass 4) | a state |

The type count stays at **37**.

---

## Part 3. Living beings

Each entity section follows the same layout: **Current → Attributes → Behaviours → Interconnections → Emergence examples → Tables and rules → Player levers and UI.**

### 3.1 Mortal

**Current.** hp, strength, agility, intellect, charisma, age, lifespan, mortal_role, about 20 flags. Personality is prose. hp never regenerates. A child can be born to any two linked mortals at any age.

#### Attributes

**Core abilities** (0–100; the current four are kept):

- strength, agility, intellect, charisma (existing)
- endurance: hp max, healing, march
- willpower: fear resistance, torture, sanity, temptation
- perception: ambush, discovery, spying
- wisdom: judgement, prophecy, counsel
- creativity: works, rites, innovation
- beauty: presence base; culture-read

**Body** (F4):

- `body_plan` (humanoid or another plan for non-human peoples)
- `height_class`, `build` (slight/average/heavy/giant)
- injuries and conditions rows
- `pain` 0–100, derived from active injuries
- derived capacities (melee, missile, command, craft, scholarship, presence, mobility, fertility)

**Life course:**

- `sex` (female/male/other; typed so fertility and succession laws can read it; worlds may define more through people biology)
- `life_stage`: infant, child, youth, adult, elder, ancient. Derived from age over the people's lifespan curve, so elven peoples have long adulthoods.
- `fertility_window` (from people biology)
- `health` 0–100: chronic illness, age and conditions
- `cause_of_death` (enum, extends the death flags)
- `death_place_id`

**Mind:**

- personality value vector (F5)
- 2–5 traits (F5.1)
- needs (F8)
- `stress` 0–100: accumulates from trauma, needs and conflicting duties; past thresholds it triggers break events (F below)
- `sanity` (existing column, now with typed madness forms)

**Skills** (F6): 0–100 per skill, with xp.

**Social standing:**

- `social_class` (the column exists; now set for every mortal)
- `wealth` 0–100 personal
- `renown` 0–100: mortal fame, distinct from charisma, with decay
- `honour` 0–100: kept and broken oaths, culture-read
- `infamy` 0–100: atrocities, culture-read
- `legitimacy` (only while holding an office, Part 4.6)
- `house_id` (new type `house`)
- `polity_id` loyalty target
- `loyalty` 0–100 toward their liege, community and god, as three numbers

**Kinship:** typed kin bonds replace the overloaded DESCENDS_FROM and LOVES:

- PARENT_OF (directed)
- SPOUSE_OF (with `marriage` row: kind monogamous/plural/political, treaty_id, start, end, cause_end)
- SIBLING_OF (derived, not stored)
- BETROTHED_TO
- CONCUBINE_OF (culture-gated)
- FOSTERED_BY
- SWORN_KIN (blood brotherhood, an oath; Part 4.8)

The existing DESCENDS_FROM to communities remains for ancestry of peoples.

**Possessions:** OWNS items (existing). Equipment slots: `wielded_main`, `wielded_off`, `armour_body`, `armour_head`, `mount` (a beast or tamed species), `focus` (magic), `prosthesis[part]`. Slots are typed columns on a `mortal_equipment` row.

**Memory** (F7) and **incidents** (F10) give every mortal a biography made of state.

#### Behaviours

1. **Ageing with stages.** Each stage transition applies typed changes:
   - youth → adult: stat growth ends; skills unlock their caps.
   - adult → elder: strength, agility and endurance decline per epoch [−4]; wisdom rises [+3]; age conditions are rolled (failing sight, deafness, frailty).
   - The existing `effective_lifespan` remains as the cap. Death past the cap becomes a hazard curve: `p_death(age) = base × exp(k × (age/lifespan − 1))`, × health, × medicine. So exceptional old age happens and is notable.
2. **Health.** Chronic illness and infections (F4.4–F4.6) are checked per epoch. Hp regenerates. A mortal at hp < `health.bedridden_hp` [25] cannot act as an agent, hold command or fight.
3. **Fertility and birth.** `couples_bear_children` is replaced:
   - **Conditions:** both partners alive and fertile, life stage adult (or youth where the culture allows), a SPOUSE_OF or CONCUBINE_OF bond (or LOVES at a lower rate `births.unwed_rate_pct` [25]).
   - **Chance per epoch:** `fertility × (1 − stress/200) × sustenance_need × culture.kinship_bonus`.
   - Childbirth risk for the bearer: `birth.mortality_base` [6%] × (1 − medicine) × age risk. Death in childbirth creates an orphan memory and a widowed spouse.
   - Twins at [3%]. Stillbirth at [8%] × hunger.
   - **Inheritance:** each ability = parents' mean ± deviation, plus **heritable traits** (`inheritance.trait_pass_pct` [35] per parental trait, with a traits table flag `heritable`) and **bloodline marks** (house traits, divine blood, curses).
4. **Education.** Children and youths gain skills from parents, masters (APPRENTICE_OF), schools (structures, Part 7.2) and temples. Education quality = teacher skill × institution function × literacy of the community. A child raised as a hostage (Part 5.7) gets the captor's culture drift.
5. **Careers and offices.** Each epoch, an adult mortal without an office evaluates options by skills, class, traits, needs and openings. Options: join an army, seek office, apprentice, take vows (a cult), trade, wander (explorer), turn bandit (when poverty and low honour). This replaces the static `mortal_role`, which becomes a derived label (F6).
6. **Combat participation.** Mortals in an army's war band (Part 5.1) roll per battle: engagement chance by role and position, then **hits** (F4.3) from the opposing weapon mix. Commanders roll lower exposure but suffer **targeting** when the enemy has the `decapitation` doctrine. Results are injuries, death, capture or glory (renown +, trait gain).
7. **Duels and challenges.** Duels become multi-exchange contests (Part 5.6) that produce injuries rather than "badly wounded". Challenges are culturally framed: honour duels, trials by combat (law), champion combat in lieu of battle (treaty clause).
8. **Stress and break events.** When stress ≥ `stress.break_threshold` [80], one break event is rolled by traits:
   - rage (attacks the source)
   - flight (deserts, emigrates)
   - despair (melancholic trait, possible suicide under the despair rule, default off)
   - zeal (converts or joins a cult)
   - vice (an addiction condition)
   - revelation (seer chance; a vision condition)
9. **Opinion-driven acts.** Mortals act on memories (F7):
   - vengeance (hero quest kind vengeance, now automatic from strong `killed_kin` and `maimed_me` memories)
   - gratitude (protects, gives gifts)
   - betrayal (ambitious and deceitful trait with a grievance toward a liege → plot, Part 4.6)
10. **Punishment.** Laws (Part 4.5) can sentence mortals to fines, exile, branding, mutilation (hand for theft, tongue for blasphemy, eyes for treason) or death. Mutilation creates injuries and conditions by law, so a cruel legal code fills a people with one-handed thieves and tongueless heretics, which feeds infamy, legitimacy and value drift.
11. **Death.** The single death path (`die()`) is extended:
    - cause and place recorded
    - memories inherited
    - the house's prestige changes by manner of death (a glorious death raises it; execution for treason lowers it)
    - burial according to the people's funeral tradition (Part 8.3: cremation, barrow, sky burial, eaten by the kin), which determines spirit chance (an unburied body raises the restless chance) and relic availability (bones can become a holy relic of a saint)
12. **Afterlife routing.** At death the soul is sorted (Part 3.3) by the god's judgement doctrine, the deeds ledger (renown, infamy, honour, faith) and the funeral rite.

#### Interconnections

- → **War:** derived capacities replace raw stats in duel power, commander power and battle exposure. Injuries change who leads. Veterans' skills raise army experience (Part 5.1).
- → **Polity and house:** legitimacy reads conditions (wholeness), honour and infamy via culture values. Succession reads sex, age, kinship, house and claims.
- → **Economy:** a mortal's craft skill and grasp produce item quality. Personal wealth funds patronage (structures, artworks) and bribes (intrigue).
- → **Faith:** piety need and personality drive conversion. Saints come from renown + piety + miracles. Relics come from saints' bones. Divine marks are conditions.
- → **Knowledge:** scholars with high scholarship deepen knowledge. Blind or one-handed scholars need assistants (a teaching bond becomes mandatory).
- → **Culture:** artists' creativity and skill set artwork renown. Traditions decide how bodies, deaths and marriages are read.
- ← **Environment:** weather and terrain injure travellers and soldiers (frostbite, heat). Disease load raises infection.
- ← **Gods:** blessings and curses are conditions and modifiers. CHOSEN becomes a condition with typed boons (and costs: the god's demands, Part 9.1).

#### Emergence examples

- **The one-eyed house.** A house's founder lost an eye at a famous battle. The house adopts the eye-patch as heraldry (house emblem, Part 4.2). Its people read one-eyedness as noble (a value_reading override from a tradition). Generations later, veterans who lose an eye gain presence there.
- **The tongueless prophet.** A law cuts out a heretic's tongue. He cannot preach (speech 0), but his written rites (writing skill) spread through an ideology. The martyr memory raises the cult's zeal. A conversion wave follows, and the law is repealed by the new majority.
- **Childbirth and succession.** A queen dies in childbirth. Her heir is a female infant, and the law requires a male adult heir. Claimants of a rival house press claims (Part 4.7) and a regency council forms (an office). A civil war becomes likely, raised by the stress of the regent.

#### Tables and rules

- **Tables:** `mortal_profiles` (abilities beyond the four, body, life course, standing), `mortal_equipment`, `injuries`, `conditions`, `skills`, `personality_values`, `entity_traits` (extended to `TraitKind`), `marriages`, `memories`, `needs`.
- **Rules namespaces:** `anatomy`, `injury`, `healing`, `aging`, `fertility`, `education`, `careers`, `stress`, `punishment`, `afterlife_routing`.

#### Player levers and UI

- **Levers:** heal or maim; grant or remove a trait; set a betrothal; force a marriage; adopt; promote from cohort; apply a prosthesis; set personal values; and the existing levers (kill, resurrect, deify, chosen).
- **UI:** the entity drawer gains a **Body** tab (a body diagram of the plan with injury markers and history), **Mind** (values radar, traits, needs, stress), **Skills**, **Kin** (family tree from typed kin bonds), and **Biography** (an incident timeline, F10).

---

#### Reference pass (R1, R7)

**Mind:** the mortal mind is now the full F13–F19 stack:

- 19 attributes, 36 facets, 24 beliefs, about 40 traits;
- thoughts, emotions and mood;
- 22 needs, a life dream, wants and fears, a lifestyle focus with perks;
- preferences;
- relationships with types;
- local reputations;
- secrets, hooks and favours;
- a belief state (F22).

The first-pass "personality value vector" is the beliefs layer of F13.

**Life course in stages, with milestones** (R7):

- **Infancy:** survival depends on the household's food, the carer and disease. Milestones are walking and speech; their timing feeds attributes.
- **Childhood:** upbringing quality is a household and education score made of parental warmth (relationship), wealth, teachers and trauma. It sets the starting facets, beliefs and skills, and an adverse childhood raises the anxiety and anger facets.
- **Youth:** coming of age is a gathering and a tradition (scar rites, F25 and 8.3). The first life dream is chosen. A first love is possible.
- **Adulthood:** careers, marriage, children, offices.
- **Elder:** a mentor role (teaching efficiency +), a council voice (age-respecting cultures), memory loss risk (memory attribute decline) and "wise elder" reputation growth.
- **Ancient** (long-lived peoples): eccentricity (facet drift), and a living-history role, reducing legend distortion for nearby tellers.

**Pregnancy and birth** (R7): pregnancy is a state with a duration from people biology (`fertility.gestation_years`, often 0.75). It carries complications: hunger and disease raise the risk, and medicine and healers lower it. Miscarriage is a grief thought. The birth outcome includes twins, the bearer's health and a newborn condition. Divine or cursed conception is an effect package (F30).

**Careers as ladders** (R7, R6): each profession has ranks (apprentice, journeyman, master, grandmaster for crafts; soldier, sergeant, captain, marshal for arms; acolyte, priest, high priest for clergy). Promotion depends on skill, performance (the outputs and victories credited, an incident count), relationships with superiors and openings. The rank sets income (household, F29), status needs and reputation. Being demoted or dismissed gives a shame thought.

**Death causes catalogue:** death causes are typed and recorded:

- violence (weapon class), bleeding, infection, disease (by id), childbirth, old age, starvation, cold, heat, drowning, fire, beast, execution (method), murder (scheme), suicide (rule-gated), curse, divine act, void, accident (work kind), heartbreak (grief with low health).

The cause sets the ghost type (3.3 reference pass), memories and legends.

**Personal events:** birthdays are not simulated, but comings of age, weddings, anniversaries of a death (reliving, F14) and jubilees of a ruler are gatherings with thoughts.

#### Reference pass 3 (R9, R22)

- **Heroquests as life events:** mortals with high renown, faith and a fitting legend may undertake a heroquest (8.2 reference pass 3). Success brings boons (conditions, items, a title, a domain blessing). Failure brings injury, a soul trapped in the mythic realm (the body comatose) or death. A completed heroquest becomes part of the legend (re-enactment changes the myth for future questers).
- **Mantling** (Elder Scrolls and Malazan-like): a mortal who imitates a god's defining deeds (aspect deeds, 9.1), gathers worship (a cult whose patron is the mortal, allowed under decision 27 because the mortal becomes a candidate god) and survives the god's opposition can **ascend** when Fate approves. The result is a new son (the deification path generalised), or the **replacement** of a god whose aspects the mortal took (decision K.10). Replacement is rare by construction and has three conditions, all required:
  1. **The god is weak:** its existence, faith and standing are all below the mantling thresholds (`mantling.weak_existence_max`, `mantling.weak_faith_share_max`, `mantling.weak_standing_max`).
  2. **The mortal is overwhelming:** its renown, its own worship, its power level and its aspect deeds are all above the thresholds (`mantling.mortal_*_min`). The mortal's power is measured against the god's on the god-duel scale (9.1), and it must exceed it by `mantling.power_margin_pct`.
  3. **The mortal kills the god:** through the existing god-challenge path (the mortal tool `challenge_god`, its slay outcome) or a divine-war victory.
  
  Only then can Fate approve the replacement. The old son dies through the god-death path (`in_cosmos` mode, F49 reference pass 10), and the mortal becomes a new son that inherits the slain god's aspects, dominion share and part of its worshippers. This applies equally to the player's sons. No extra approval is needed beyond the three conditions and Fate, but the player is notified as soon as a mortal starts meeting them, and every lever of J.16c applies (block, pin, intervene). This gives mortal ambition a cosmic ceiling.
- **Passions** (F18 reference pass 3) and **conviction** (F17 reference pass 3) are part of every mortal.

#### Reference pass 4 (R34, R35)

- **Astrology:** each mortal records the celestial configuration of its birth (its birth sign: the visible celestial entities and the season at birth, from the computed sky, 10.9).
  - Where a natural law or a celestial's influence (10.3) makes the stars truly influential, the configuration applies real modifiers (facet shifts, a fortune bias).
  - Where it does not, the influence is **believed only**: cultures with astrology read the sign (beliefs and reputation, a role eligibility in some cultures, a prophecy target). Children born under a dreaded sign may be exposed or fostered away (an ethics-gated act).
  - The difference between believed and real influence is player-visible.
- **Reproductive systems:** see 4.1 reference pass 4. A mortal's sex follows its people's system and can change in sequential systems.

#### Reference pass 6 (S-I)

**Childhood play and peer groups:** children of a settlement district and class form **peer groups** (cohort-level, with named members for named mortals). Play (games, mock fights, imitation of adult roles) shapes facets (assertiveness, cooperation), skills (riding, archery and songs, by the culture's play customs) and **childhood friendships and rivalries** (F18) that persist into adulthood: a king's companions in childhood become his inner council. Lack of play (child labour, famine, war) lowers cheerfulness and raises later stress.

### 3.2 Species (kind and population)

**Current.** hp, strength, agility, intelligence, danger, abundance, might, plus 10 traits. There is no diet, habitat or climate tolerance, and domestication is one bond.

#### Attributes

**Biology:**

- `body_plan`, `size_class` (tiny/small/medium/large/huge/colossal)
- `lifespan_years`, `maturity_years`, `litter_size`, `breeding_seasons` (reading F2.2 seasons)
- `diet`: herbivore, carnivore, omnivore, scavenger, filter, photosynthetic, mineral, soul, void (soul and void are typed now, not prose)
- `metabolism`: food need per individual, which shapes starvation sensitivity

**Habitat:**

- `habitat` (preferred TerrainKinds with weights)
- `temperature_tolerance` (min/max band)
- `water_need`
- `altitude_range`
- `nocturnal`
- `migratory` (seasonal path between regions)

**Behaviour:**

- `aggression`, `territoriality`, `sociality` (solitary/pack/herd/hive)
- `cunning`, `fear_of_people`

**Population:**

- `population_index` per region in a `species_ranges` table (region, abundance, trend) instead of one global abundance. The global abundance becomes the weighted total.

**Yields:** materials and commodities per harvested unit (`species_yields`: material or commodity, rate): hide, bone, chitin, ivory, venom, silk, meat, milk, wool, feathers, magic reagents (from high-might species).

**Domestication:**

- `tameability` 0–100
- `domestication_stage` (wild → tamed → herded → domesticated → breed)
- `domesticated_from` (parent species for a breed)
- `uses` (set: food, labour, mount, war, guard, companion, sacrifice, magic)

**Disease:** host-of (disease ids), immune-to.

**Traits:** the existing 10 enum traits are extended to about 30: armoured, burrowing, aquatic, amphibious, pack_hunter, ambush_predator, regenerating, poisonous_flesh (cannot be eaten), fire_breathing, cold_breathing, echolocation, camouflage, swarm_breeder, long_lived, mimic, spirit_sight, iron_eating (eats ore: an economy pest), crop_pest, plague_bearer, sacred_animal (by doctrine).

#### Behaviours

1. **Range dynamics per region.** Growth = r(litter, maturity) × habitat fit (terrain, temperature from F2.1, season) × food (prey abundance in the region, or forage from forest cover and fertility) − predation − hunting − disease − land use (F2.5). Seasonal migration moves range shares between regions along a path.
2. **Food web.** HUNTS bonds become derived from diet, size and region overlap each epoch. Prey shortage raises predator aggression → livestock raids on settlements (economy: the livestock commodity drops) → monster-raid behaviour emerges from ecology instead of a separate danger roll.
3. **Pests and blights.** Crop-pest species reduce harvest in sampled years (F2.4). Iron-eaters reduce ore stocks. Plague-bearers raise disease load.
4. **Domestication path.** Tamed (a mortal tool, existing) → herded (a community keeps the TAMED bond for [2] epochs with fodder) → domesticated (a new species row of engine kind `domesticated`, with stats drifting toward tameness: aggression −, size ±, yields +) → named breeds (from selective breeding by herders with the husbandry skill). Domesticated species become livestock commodities and mounts, and war-beasts for armies (Part 5.1 unit kinds: war_elephant-like, war_hound, sky_mount).
5. **Speciation and adaptation.** The existing speciation is extended: isolated populations in a different habitat drift tolerances and size. This produces "highland" and "desert" subspecies with typed differences.
6. **Extinction cascade.** Extinction of a prey species starves its predators. Extinction of a yield species removes a material (F3), and the craft that needed it declines (a knowledge level drop for specialised branches). Extinction of a sacred animal is a doctrinal crisis (Part 4.4).
7. **Champion promotion.** When a species has the megafauna flag or `size_class` ≥ huge with danger ≥ [70], the engine may promote an individual **beast** (3.3a) that becomes the region's named terror or guardian.

#### Interconnections

- → **Economy:** yields become materials and commodities; livestock; mounts; pests.
- → **War:** mounts and war-beasts become unit kinds; cavalry needs horse-like species with the mount use.
- → **Disease:** hosts.
- → **Faith:** sacred animals; animal-headed gods (a son with the Hunt domain and a totem species); sacrifice.
- → **Culture:** totems (a people's emblem species, a tradition), legends (a monster legend manifests a species).
- ← **Environment:** habitat fit; climate eras shift ranges (an ice age pushes species to the lowlands, where they meet people).
- ← **Communities:** land use and hunting pressure.

#### Tables and rules

- **Tables:** `species_profiles`, `species_ranges`, `species_yields`, `species_uses`, `species_hosts`, `species_traits` (extended enum).
- **Rules namespaces:** `ecology` (extended), `domestication`, `pests`, `habitat`.

#### Player levers and UI

- **Levers:** move a range; domesticate now; make a species sacred to a son; cull; seed into a region.
- **UI:** a species range map layer; a food-web graph per region; a domestication timeline.

---

#### Reference pass (R1, R2)

**Flora** is part of the species type with kind `plant`. Plants get:

- growing seasons (F2.2), soil and temperature needs, a growth cycle (annual, perennial, tree);
- yields: grain, fibre, dye, timber, fruit, herb, brew base, alchemical reagent, poison;
- a wild or cultivated status, and cultivars (a domestication path);
- pests and diseases (host links).

Crops in the region crop mix are plant species, so harvest (F2.4) reads the planted crops' needs against the region and the sampled year.

**Animal husbandry** (R1):

- grazing pressure on region land (grazed land use, F2.5);
- milking, shearing, egg laying and butchery as production methods (F24);
- breeding seasons;
- herd sizes as commodity counts per community;
- draught power (energy, F24);
- war, hunting and guard training (skill: beast_handling);
- pets: individual companion animals are beasts (3.3a reference pass).

**Biochemistry class** (R2): each species has `biochemistry` (carbon-water, carbon-ammonia, silicon, crystal, void, spirit). Habitability on worlds is checked against the world's biochemistry tolerances (10.9). Cross-world introductions (stowaways, colonisation) succeed only where the class fits, and void or spirit species ignore atmosphere.

**Vermin and small pests** form a species class `vermin` that spoils stores (F24), spreads disease (3.4) and gives a pest-hunter niche (cats-like species, a domestication use `pest_control`).

**Procedural generation:** son-created and engine-generated species receive a generated anatomy (body plan plus typed modifications: extra limbs, materials of skin and bone (F23: a stone-skinned species has a stone tissue layer), breath attacks, venom packages (F30)), a temperament and preferences. The LLM names and describes them *from* this data (G8).

#### Reference pass 3 (R9, R12)

- **Trait evolution under selection:** each species carries heritable trait values (size, speed, armour, venom potency, camouflage, cold tolerance, intelligence, fecundity) as population means and variances. Per epoch, each range's selection pressure moves the means:
  - predators select prey for speed and camouflage;
  - climate selects tolerance;
  - human hunting selects wariness and smaller size (trophy hunting);
  - divine protection relaxes selection;
  - leak adds variance (mutation).
  
  Large divergence between ranges becomes speciation (the existing rule, now driven by trait distance).
- **Niches and competitive exclusion:** a niche is a diet × habitat × size × activity-time combination. Two species in the same niche and region compete: the less fit declines and is excluded, or shifts niche (character displacement). Empty niches attract invaders and drive **adaptive radiation** after mass extinctions: surviving lineages speciate into the vacated niches over epochs.
- **Trophic flow:** biomass per trophic level per region is bounded by the level below (an energy-transfer efficiency of `ecology.trophic_efficiency_pct` [10]). Overhunting the herbivores collapses the predators, and overfishing collapses the fisheries.
- **Coevolution:** predator and prey trait means drive each other (arms races). Hosts and pathogens do too (3.4 reference pass 3).
- **Keystone species and services:** species flagged `keystone` (pollinators, soil-makers, dam-builders, scavengers) provide ecosystem services as region modifiers: crop yield, soil fertility, wetland creation, disease load −. Their extinction cascades through the region's agriculture and health.
- **Feral reversion:** domesticated species released or abandoned (after a ruin or a plague) revert over generations toward wild traits, becoming invasive pests or new wild breeds.
- **Divine taint and blessing of lineages** (R9 #8): a god's dissonant or corrupting act (a curse on a species, a void bargain, a desecration) marks the touched lineages with an F30 package inherited down the species line. Blessed lineages (a sacred species) carry a benign package.

#### Reference pass 6 (S-E)

- **Microbial layer:** per region, a **soil microbiota** index (from soil, moisture, pollution and land use) sets decomposition and nutrient recycling speed (6.1 reference pass 4 nutrients). Sterile or poisoned soils recover slowly. **Fermentation cultures** (yeasts, starters, moulds, ferments) are domesticated microbe strains held by households, guilds and monasteries: heritable assets that set brewing, bread and cheese quality (F24), which can be lost (plague, fire) or traded.
- **Symbiosis relations** (`species_relations`: a, b, kind, strength):
  - **mutualism** (pollinators and plants, cleaner species, mycorrhiza: yield +);
  - **commensalism**;
  - **parasitism** (ticks on livestock: health −, a disease vector; lampreys on fish stocks; mistletoe on trees);
  - **mimicry** (harmless species resemble dangerous ones and are avoided by hunters; a misidentification risk for scouts).
  
  Relations enter population dynamics and selection (coevolution, 3.2 reference pass 3).
- **Dormancy:** species with hibernation or aestivation are inactive in their dormant season (no raids, no hunting yield, vulnerable lairs). Peoples' hunting calendars and beast-hunting quests follow dormancy, and a disturbed dormancy wakes a hungry beast.
- **Thermoregulation:** ectothermic species (and peoples of that biology, 4.1 reference pass 6) have activity scaled by the temperature band and season. They are slow in cold, strong in heat, and they fight and work by season and region. Endotherms pay a food cost in the cold.
- **Senses:** species and peoples hold typed **sensory profiles** (sight range, night vision, smell, hearing, echolocation, vibration, magnetic sense, spirit sight, heat sense). Senses feed detection (spotting and concealment, 5.3 reference pass), tracking, ambush, navigation (magnetic sense without a compass) and espionage (scent trails reveal agents). Night-sighted peoples prefer night raids.
- **Plant defences:** thorns (passability −, grazing −), toxins (poisoning risk for foragers, a material source for poisons and medicines), allelopathy (invasive plants suppress crops: a pest) and carnivorous or dangerous plants (a region danger source).
- **Biogeography:** isolated island populations drift by the **island rule** (large species shrink, small ones grow) under the selection model, and endemics and relict populations (survivors in refugia after climate shifts) get the endemic flag (conservation value for nature-valuing cultures and sacredness).

#### Reference pass 8 (B1)

**Mass death and scavengers:** large death events (battles, plagues, famines, massacres) create a **carrion pulse** in the region. Scavenger species (vultures, rats, carrion beasts) boom, vermin rise (stores spoil, disease load rises) and predators are drawn in (beast attacks rise). Unburied dead raise the restless-spirit chance (3.3). The pulse decays as the carrion is consumed, so battlefields have an ecological afterlife.

### 3.3a Beast (new type: a named individual creature)

#### Attributes

- `species_id`
- body plan and injuries (F4)
- abilities: strength, agility, endurance, cunning, perception, willpower
- `age`, `lifespan`
- `size_class`
- `lair_place_id`
- `hoard` (OWNS items and a commodity stock: gold, bones, relics)
- `temper`: hungry, territorial, sleeping, enraged, bound, tamed
- `bound_to` (a master mortal, cult or god)
- `memories` (F7: who wounded it, who stole from the hoard)
- `renown`, `terror` (a regional fear aura: settlers' safety need ↓, prosperity ↓)
- `intelligence` (a sapient beast can speak, bargain and be an LLM agent; the current species agent rule INT ≥ 55 moves here)

#### Behaviours

- **Lair cycle:** sleep → wake (seasonal or disturbed by mining, war or a theft) → hunt (raids on livestock and settlements in range) → return.
- **Hoard growth:** raids and tribute (communities may pay a beast tribute through a treaty, 5.13).
- **Wounding memory:** a beast wounded by a hero hunts that hero's house (vengeance behaviour).
- **Taming and binding:** riding a tamed beast gives a mount slot with large combat and travel effects; bound beasts can guard temples or gates.
- **Death:** the corpse yields materials (dragonbone, star-scale), the hoard becomes a treasure place, and a slayer legend and renown follow. Ecology may recover in the region.

#### Interconnections

- → **Heroes:** quests target beasts by name. Slaying gives a title and an item yield.
- → **Economy:** the hoard is a large wealth injection when looted (price shock in luxuries).
- → **War:** a bound beast joins an army as a unit (terror: enemy morale −).
- → **Faith:** worshipped beasts become local gods through the native-faith path.
- **Mounts:** a beast mount gives its rider a mounted-combat bonus and access to sky or sea routes (the existing cosmic mount logic generalises).

#### Tables and rules

- **Tables:** `beast_profiles`. Uses the shared `injuries`, `memories` and `entity_traits`.
- **Rules namespace:** `beasts`.

#### Player levers and UI

- **Levers:** wake or lull; bind to an entity; spawn; shift the lair.
- **UI:** a beast card with body and hoard; map lair icons with a terror radius.

---

#### Reference pass (R1, R2, R7)

**Procedural monsters** (R1): forgotten-beast and titan-like generation for beasts whose species is unique:

- a random body plan from a generator;
- tissue materials (F23): crystal, fire, steam, metal;
- an attack package: breath (fire, frost, venom gas, a web), a bite effect package (F30), a gaze;
- size; preferences (what it hoards, what it hates);
- an awakening trigger (deep mining near its cavern, or a desecration).

They emerge from the subterranean strata (6.1 reference pass) when communities dig deep, which couples mining depth with monster risk.

**Night creatures and curses:**

- werebeasts and vampire-like beings are mortals or beasts carrying the F30 packages;
- night trolls and bogeymen are beasts with the abductor temperament, which kidnap mortals (abduction incidents);
- necromancers are mortals with the necromancy rite who build towers (structure kind `tower`) and raise undead (bound spirits in corpses) as armies, and can besiege settlements.

**Pets and companions** (R7): beasts with the `companion` temper, bonded to a mortal (a `PET_OF` bond). A pet's death is a grief thought for the owner; a pet's presence gives comfort and loneliness relief; war hounds and falcons have a role (hunting skill bonus).

**Void fauna** (R2): beasts with the `void` habitat migrate along inter-world routes, threaten journeys, can be tamed as cosmic mounts (the existing route logic) and are hunted for void materials (F23).

#### Reference pass 3 (R10)

- **Familiars:** a mage may bind a beast or spirit as a familiar (a rite). The familiar shares senses (intel, F22), lends a skill or magic resistance, and suffers the backlash first. The death of a familiar is a grief thought and an injury-like condition for the mage.
- **Beasts in dominions:** beasts sacred to a god thrive and are calmer under its dominion (F31). Beasts of a rival god's domain are restless there.

#### Reference pass 4 (R34, R38)

**Constructs** (golems, automata, homunculi, war machines with minds):

- **Instruction sets:** a construct has a body plan `construct`, a material (F23), a power source (a soul bound, a rune, essence, a ley line) and an **instruction set** (`construct_orders`: typed commands with literal semantics, such as "guard the gate", "obey whoever holds the seal", "kill intruders").
- **Literalism:** constructs follow orders literally, so loopholes exist. The seal-holder rule passes control to whoever steals the seal, and a guard order outlives the city it guarded.
- **Decay and maintenance:** power sources fade, materials wear (F23 decay) and runes need renewal by a maker with the skill. A construct whose maker dies keeps its last orders (a hazard in ruins, a guardian in tombs).
- **Emergent will:** constructs powered by bound souls (3.3) inherit fragments of the soul's imprint, and over epochs may develop wants (F17). This leads to the existing creature rebellion, now with a cause.
- **Mass production:** construct species (many identical units, from a production method with rare materials) serve as labour (an energy and labour source, F24) and as soldiers (stacks of kind `construct`: no morale, but vulnerable to dispels and to the loss of their command seal).

**Monster contracts** (Witcher-style): communities troubled by beasts post **contracts** (a bounty, F20 favours or treasury). Professional monster hunters (a profession with the tracking, lore and combat skills, and possibly an F30 mutation package from their order's training) take contracts. Study of the beast (lore: weaknesses from its generated anatomy and packages, 3.3) improves the odds. Contracts are a career and a reputation path, and a source of monster legends.

#### Reference pass 8 (B2)

**Beasts as lore keepers:** sapient beasts with long lifespans and memory attributes hold **accounts** (F33) of past ages: a dragon remembers the war of three centuries ago as it truly happened, or as it chose to remember it. Such beasts are sought for knowledge (lore as currency, F19 reference pass 3), bargains (F38) and heroquest guidance. They may teach rites, languages and true names, or sell secrets, and they can be propagandists for their own version of history.

#### Reference pass 9 (A2)

**The end of beast lore:** at a lore-keeping beast's death, the accounts it held are lost, except what it taught, told or had recorded: accounts held by its pupils, a lair library, inscriptions in its hoard. The loss is an incident ("the memory of the age died with the Wyrm"). Its corpse may still yield secrets to necromancy and spirit-speaking (3.3).

### 3.3 Spirit, soul and afterlife

**Current.** strength and unrest only. Souls record where a soul went; there is no judgement and no reincarnation.

#### Attributes (spirit)

- `origin_mortal_id` (existing via souls)
- `imprint`: personality values and traits copied from the mortal at death
- `deeds_ledger` (renown, infamy, honour, faith, violence), copied
- `unrest` (existing)
- `strength` (existing)
- `binding` (none, place, item, structure, beast, person: possession)
- `memory_strength` 0–100: how much of the mortal it remembers; decays, preserved by remembrance
- `veneration` 0–100: offerings received
- `alignment_to_living`: guardian, neutral, vengeful
- `afterlife_state`: wandering, judged, in_realm, reborn, consumed, released

#### Afterlife model

- Each realm (a world of type realm-of-the-dead, or an underworld region) has **strata** (`afterlife_strata`): paradise, plain, torment, oblivion, or doctrine-specific ones (a warrior hall). Each stratum has entry criteria, written as typed predicates over the deeds ledger and faith.
- **Judgement:** at death the soul is judged by the patron god's **judgement doctrine** (Part 9.1: which deeds count), the funeral rite performed (Part 8.3) and the god's favour. A soul with no rite or a broken burial wanders as a restless spirit, so the existing unrest mechanics gain a cause.
- **Reincarnation (decision K.7): rare and earned, never the default fate.** A soul can be reborn only if at least one gate opens: a doctrine with the reincarnation tenet, the `souls_reincarnate` natural law, a reincarnation rite performed for that soul, or a god's direct act.
  - Even with a gate open, only an exceptional soul qualifies. It needs high renown or deep faith, or a strong unfinished memory such as an unpaid vendetta or a broken oath, measured as a deeds-ledger score ≥ `afterlife.reincarnation_min_score` [75].
  - Each qualifying soul then rolls `afterlife.reincarnation_chance_pct` [10]. Even under a reincarnation law, ordinary mortals are not reborn.
  - **Blocking rites** (8.6, death and warding schools) can seal a soul against rebirth: a binding seal, a nameless burial, or soul-eating by an outer being. So can the `souls_rest` tenet. Unsealing needs a stronger counter-rite.
  - A reborn soul becomes a newborn mortal in a community (by doctrine: the same people, the same house, or by merit), with a fraction of the old traits and a `past_life` link. Faint memories can let the reborn recognise old enemies (a memory carryover of `afterlife.reincarnation_memory_pct` [15]).
- **Ancestor veneration:** a people with high `death` value keeps ancestor spirits as guardians. They give modifiers (the household's luck, a battle morale boost at ancestral sites). Neglect (no offerings) turns guardians restless.
- **Necromancy and binding** (rites, Part 8.6): bound spirits power items and structures (existing) and can now **possess** mortals (a condition): stats are replaced by the spirit's imprint, with stress for the host and an exorcism rite as the counter.
- **Consumption:** soul-eaters (species trait, outer beings, some gods) consume souls. The god of that soul loses a would-be follower in its realm, which counts toward realm population, a new son resource for Death-domain sons (Part 9.1).

#### Interconnections

- ← **Mortal:** deeds become judgement; funerals become spirit chance.
- → **Gods:** realm population; Death-domain essence; a son's doctrine of judgement affects how pious mortals behave (fear of torment raises honour and lawfulness in that culture, via value pressure).
- → **Settlements:** hauntings now target the killers' descendants (memory) instead of a random same-region settlement.
- → **Culture:** ghost legends with high credence; mourning traditions.

#### Tables and rules

- **Tables:** `spirit_profiles`, `afterlife_strata`, `soul_judgements`, `possessions`, `reincarnations`.
- **Rules namespaces:** `afterlife`, `spirits` (extended), `necromancy`.

#### Player levers and UI

- **Levers:** judge a soul; release; bind; reincarnate; set a realm's strata.
- **UI:** a realm view with strata populations; a soul card with its ledger and judgement reason.

---

#### Reference pass (R1, R7)

**Ghost typology by cause and rite** (R1):

| Ghost type | Cause |
|---|---|
| lingering | unfinished dream (F17) |
| vengeful | murdered, with a killed_by memory |
| sorrowful | grief |
| haunting a place | died there, unburied |
| poltergeist | violent death in a home |
| bound guardian | a rite |
| possessing | 3.3 |

- **Resting a ghost** needs the matching remedy: a memorial (a structure kind `memorial_slab` with the dead's name, made by a mason), a proper funeral rite, completion of the dream by kin, vengeance done, or an exorcism rite.
- Ghost unrest drives typed haunting effects: mood thoughts for the living, prosperity −, livestock deaths, the haunted terror of a place (3.3a terror analogue).

**Death and the afterlife are tied to life choices:** the deeds ledger now uses local reputations (F19), ethics compliance (F16: unthinkable acts weigh heavily), life-dream fulfilment, and faith standing (9.1 standing with the patron).

**Mourning:** the grief process (F14) runs for the bereaved. Mourning traditions shorten complicated grief, and the funeral gathering (F25) settles relationships among the heirs (inheritance disputes can begin at the funeral).

#### Reference pass 3 (R9)

**Divine servitors:** spirits with `servant_of` (a son, foreign god or the Creator) and a rank: herald, guardian, angel, fury, psychopomp, choir.

- **Origin:** made by a son (an essence cost), raised from saints' souls (the afterlife strata of a doctrine that rewards service) or summoned (rites).
- **Role:** they carry messages (a divine medium, F21), guard holy sites and thrones, judge souls in the realm (judgement doctrine) and fight in divine wars (stacks of kind `host`).
- **Loyalty:** servitors have their own minds (F13 at a spirit scale) and can fall, becoming demons of a rival or an outer being. Their loyalty follows the god's standing and treatment.

#### Reference pass 4 (R33)

**Genius loci** (minor spirits of places: rivers, springs, groves, hearths, crossroads, mountains, cities):

- Every notable place may host one. It is a spirit with `bound_place`, a temperament, preferences (F15) and a **reciprocity ledger** with the local community (F38: offerings for favours).
- **Content place spirits** give modifiers: fertility, safe crossings, good catches, hearth luck. **Neglected or offended ones** (pollution, deforestation, an unpaid offering, a broken taboo) give misfortune, floods and illness.
- This links land use and pollution to the folk religion directly.

**Celestial bureaucracy:** minor gods and spirits are organised in offices under the sons and foreign gods (cosmic offices, 9.4 reference pass 3, extended downward): city gods, river gods and hearth gods have ranks.

- Mortals **petition** them in writing (prayers as F21 messages with a bureaucratic channel).
- Petitions are processed (delays, bribes in offerings, appeals to higher offices).
- Spirits are **promoted** for good service (worship growth, petitions resolved) and **demoted or dismissed** for neglect, by their superior god or by the council.
- A village can sue its river god before the city god. This gives the folk faith of the simulated world a Chinese-folk-religion and Exalted-like depth, while every rule stays typed.

#### Reference pass 5 (S-D Stormlight)

**Emotion spirits:** in regions with magic density above `spirits.emotion_spawn_density` [60], strong collective emotions (F14 aggregated: battlefield fear, festival joy, mourning grief, mob rage) **manifest** minor spirits (`emotion_spirits`: emotion, region, strength, lifetime).

- Their presence amplifies the emotion (Loop R, braked by their lifetime).
- They are read as omens (superstition), feed the matching gods (emotion-fed gods, 9.1 reference pass 4) and can be bound by rites (8.6) as reagents or allies.
- They make the emotional life of mortals visible in the world itself.

#### Reference pass 8 (B2)

**Spirits as teachers:** ancestors, ghosts, place spirits and divine servitors can **teach** the living through dreams (F14 reference pass 4), visions, possession or direct manifestation. What they teach: songs and art forms, rites, lost techniques, true names, prophecies, the locations of treasures. Taught knowledge carries the spirit's biases and errors. Cultures with strong ancestor veneration gain cultural continuity through this channel, and a culture's dead can be a library or a liability.

### 3.4 Disease (new type)

#### Attributes

- `vector` (air, water, touch, bite: host species, spirit, void, curse)
- `virulence` (spread), `lethality`, `chronic_rate`
- `incubation` (in sampled years)
- `target_functions` (breath, vital, cognition, sight, skin/presence)
- `climate_affinity` (warm/wet/cold)
- `host_species`
- `immunity_epochs`
- `mutation_rate`
- `origin_incident_id`
- `stigma` (how cultures read the sick: purity value interaction)
- `cure_knowledge_level` (the medicine level that makes it treatable)

#### Behaviours

- **Outbreak** = event entity linked to the disease. Spread per sampled year:
  - along trade routes (per volume), armies (per size), journeys and pilgrimages;
  - × disease load of the region × crowding × sanitation (structures: aqueducts, sewers);
  - deaths by cohort (elders and children first).
- **Immunity:** survivors' cohorts gain immunity. Repeat outbreaks hit the young.
- **Mutation:** a new strain (a child disease) bypasses immunity.
- **Endemicity:** a disease can become endemic in a region (a permanent disease load +), which slows growth and repels settlers but protects locals against invaders who lack immunity. This is the "virgin soil" effect on conquest and colonisation journeys (Part 10).
- **Stigma:** high-purity cultures expel the sick (refugee flows of the sick, leper colonies as settlements). Merciful cultures build hospitals (structures), which raises healer skill gain.
- **Divine:** plague-domain sons gain essence per outbreak. The existing plague faith (`remembrance.py:498`) now targets the specific disease's god.

#### Interconnections

- War (army disease during sieges: the besieger's attrition, Part 5.4).
- Ecology (hosts).
- Economy (labour loss, price spikes).
- Faith (conversions).
- Culture (plague traditions, quarantine laws).
- Knowledge (medicine research pressure: a medicine deepen bonus when a disease is endemic).

#### Tables and rules

- **Tables:** `disease_profiles`, `outbreaks` (event-linked), `immunities` (cohort level), `endemic_diseases`.
- **Rules namespace:** `epidemiology`.

#### Player levers and UI

- **Levers:** loose, cure, quarantine a region, grant immunity.
- **UI:** an outbreak map layer with spread arrows; a disease card with strains and history.


#### Reference pass (R1, R7)

- **Effect packages:** a disease's symptom stages are F30 packages. Staged progression (incubation → fever → crisis → recovery or death → after-effects) gives the healer's diagnosis something to read (F23 treatment steps).
- **Minor illnesses** (colds, fevers) are aggregated per cohort as a seasonal productivity loss. They are not individual records, except for named mortals in a bad year.
- **Addiction diseases** (alcohol, drugs, void dust) are F30 packages with dependence needs, withdrawal and recovery chances raised by healers, faith and family support (relationships).
- **Medical theories** (2T.6 theory) change outcomes. A healer holding a false theory (bleeding cures fever) applies harmful treatments that raise mortality; a true theory (contagion) enables quarantine laws to work. Paradigm shifts in medicine are therefore visible in mortality curves.

#### Reference pass 3 (R12, R15)

**Pathogen evolution:** a disease's traits (transmission per vector, virulence, lethality, incubation, cold and heat tolerance, resistance to each treatment, symptom set) evolve per epoch under selection:

- high lethality in sparse populations is selected against;
- crowded cities select for transmission;
- treatment use selects for resistance;
- an immune population selects for immune escape (new strains).

Coevolution with host immunity is explicit (3.2 reference pass 3).

**Vectors:** air, water, touch, bite by vector species (insects by season and temperature band, rats, birds that migrate along seasonal paths, livestock). Vector ecology ties outbreaks to seasons and to land use.

**Asymptomatic carriers:** a share of infected mortals are carriers without symptoms. Named carriers who travel (merchants, envoys, pilgrims) seed distant outbreaks. Identifying a carrier needs the contagion theory (8.4b) and a skilled physician.

**Zoonotic spillover:** clearing land, hunting bushmeat and keeping livestock in contact with wild hosts raise the chance that a host species' pathogen jumps to people (a new disease record).

**Societal responses** are polity and settlement decisions with typed costs:

- close ports and borders (trade flows −, unrest +);
- quarantine districts (spread −, an ethics reading, a riot chance through F32);
- burn the dead (spread −, an ethics and funeral conflict);
- expel the sick (the stigma value);
- ring the bells for prayer (morale +, spread + at the gathering);
- seek a cure.

**Variolation and vaccination:** techniques (medicine sub-techniques) that convert a share of cohorts to immune at a small risk. **Herd immunity** emerges when the immune share passes the disease's threshold, from its transmission rate.

**Cure research race:** institutions (hospitals, universities, monasteries) accumulate research points against a specific disease, scaled by scholars, correct theories and specimen access (outbreak proximity). A cure becomes a technique with diffusion, and its holders gain prestige and leverage (selling the cure).

---

## Part 4. Communities, power and society

### 4.1 People (ethnic and cultural community)

**Current.** population, martiality, magic, craft, piety, prosperity, wealth, plus a society row (6 class shares, satisfactions, 3 stocks, prices).

#### Attributes

**Biology** (`people_biology`):

- lifespan curve (maturity, adult span, elder span)
- body plan, size
- fertility rate
- climate acclimatisation (temperature band)
- natural traits (dark-sight, cold-blooded, winged)
- diet
- immunity profile (endemic diseases of the homeland)

**Culture:**

- culture value vector (F5)
- `cohesion` 0–100: shared identity; resists assimilation, enables mobilisation
- `literacy` 0–100
- `urbanisation` 0–100
- `language_ids` (primary, liturgical, trade)
- `cuisine_staples` (commodities: dietary demand)
- `aesthetic` (`AestheticKind`: austere, ornate, geometric, natural, macabre, celestial; read by artworks and structures)
- `martial_tradition` (`MartialStyle`: shieldwall, horse_archer, skirmisher, chariot, phalanx, berserker, naval_raider, siege_engineer, war_magic, beast_war; Part 5)
- `funeral_rite` (a tradition id)
- `marriage_custom` (monogamy/polygyny/polyandry/group; endogamy/exogamy)
- `inheritance_custom` (gavelkind, primogeniture, ultimogeniture, matrilineal, elective, by merit)

**Demography:** cohorts (F12): age bands × class × condition. This replaces the single population count, which becomes their sum.

**Society:** the existing class shares, extended by 4 classes:

- `noble`: landholders; legitimacy and command
- `serf_or_slave`: unfree labour; culture-gated, created by conquest and debt
- `outcast`: the maimed, sick and criminal without support
- `clergy` is split from priest into `priest` (ritual) and `monastic` (scholarship)

**Stocks:** the expanded commodity table (F3.2) replaces three stocks.

**Pressures** (F8): hunger, insecurity, overcrowding, poverty, impiety, humiliation, stagnation.

**Memory and opinion** (F7) at the people level.

#### Behaviours

1. **Demographic step per sampled year.** Births by fertile cohorts × sustenance × health; deaths by age hazard × disease × famine × war. Births are sensitive to food and stress, which closes the audit gap that food did not affect growth. Population growth is no longer a logistic toward capacity alone; capacity is where hunger begins.
2. **Labour allocation.** Adults are allocated to jobs: farming, herding, fishing, mining, crafting, trade, soldiering, clergy, scholarship, building. The allocation follows class shares, available resources, structures (a mine needs miners) and demand (prices). Output per job = workers × skill aggregate × tools (materials) × environment. This makes class shares mean headcount and productivity (closing the audit gap).
3. **Consumption and standard of living.** Per-capita consumption of staples, luxuries and sacred goods. Shortfall raises the poverty and hunger pressures and lowers class satisfaction by need. Luxury abundance raises status satisfaction for nobles and merchants.
4. **Culture drift.** Value pressure (F5) per epoch from:
   - its god (doctrine)
   - its rulers (polity ideology)
   - ideologies held by its scholars
   - experiences, as typed incidents: won wars → martial +, lost wars → martial ± by cohesion, plague → piety or death acceptance, famine → kinship +, trade → xenophilia + and wealth +, conquest → toward or away from the conqueror
   - neighbours (contact)
5. **Ethnogenesis and assimilation.** Existing rules gain criteria:
   - assimilation when value distance < [20], cohesion < [40] and the language is shared;
   - ethnogenesis when a settlement's culture diverges by > [35] from its parent people.
6. **Mobilisation.** The share of adults that can be levied = martial value × cohesion × polity's levy law × season (harvest season halves it).
7. **Martial tradition** evolves from victories with a style (a style that wins is reinforced), terrain (steppe → horse archery) and knowledge (metallurgy → heavy infantry).
8. **Memory of the great events:** traditions and legends are created from incidents with a magnitude ≥ threshold (generalised remembrance).

#### Interconnections

- War: levy size; martial style becomes army composition.
- Economy: labour and consumption.
- Faith: piety and doctrine fit, so conversion chance uses value distance to the cult doctrine.
- Polity: loyalty to a polity = value distance to rulers − grievances + benefits.
- Language: cohesion and literacy.
- Disease: immunity.
- Environment: acclimatisation (cold peoples suffer heat attrition in southern campaigns).

#### Tables and rules

- **Tables:** `people_biology`, `culture_values`, `people_culture` (cohesion, literacy, aesthetic, martial style, customs), `community_cohorts`, `community_stocks`, `labour_allocations`, `pressures`.
- **Rules namespaces:** `demography`, `labour`, `consumption`, `culture_drift`, `mobilisation`.

#### Player levers and UI

- **Levers:** edit values and customs; impose a martial style; set fertility; move cohorts.
- **UI:**
  - culture radar compared with neighbours;
  - a population pyramid (age × class);
  - a labour Sankey (workers → outputs);
  - pressures gauges;
  - "why" breakdowns (F9).

---

#### Reference pass (R4, R5, R7)

**Jobs and wages:**

- Each labour allocation (4.1 behaviour 2) is a set of **jobs** at workplaces (production sites, structures, armies, offices).
- **Wage** per job = the workplace's revenue share for labour × productivity, bounded by the wage custom (serf and slave labour gets subsistence only, by law).
- Households (F29) receive wages. **Standard of living** (SoL, 0–100 per class and per household) = income against the cost of the class's needs basket at local prices.
- SoL drives migration (people move toward higher SoL), satisfaction, fertility (lower SoL raises fertility in subsistence cultures and lowers it in urban ones), radicalism (faction recruitment) and loyalty.

**Need tiers** (Anno-style, R4). Each class has tiered needs baskets:

| Tier | Contents |
|---|---|
| Subsistence | staple food, fuel, shelter |
| Basic | clothes, tools, salt, simple drink |
| Comfort | varied food, furniture, festivals, temple access |
| Luxury | fine goods by preference, art, services |

- Meeting a tier for [2] epochs allows **class promotion** of a share of the cohort (farmers → artisans → merchants; any class → clergy or scholar by education), within the polity's class mobility law and the culture's hierarchy value.
- Failing a lower tier causes **class demotion** (to outcast, or serf by debt law).

**Unemployment:** labour supply above the jobs, or method transitions that displace workers (F24), produce unemployed adults. They raise the poverty pressure, crime, emigration, levy willingness (soldiering as employment) and radical faction recruitment. Underemployment (seasonal: winter for farmers) feeds side work: crafts, banditry, festivals.

**Cultural innovations** (R5, CK3-style): each people accumulates **innovations** (techniques of the `culture` branch: martial (shieldwall drill, horse-archery mastery), civic (oral law, council of elders), economic (terrace farming, salt trade), artistic (an art form school), religious (ancestor rites)). They are researched by the culture's scholars, elders and practitioners, diffused by contact, and give typed modifiers. They are the culture-specific half of the tech graph (8.4).

**Habitability by species and climate** (R2): `people_biology` gains a climate preference set (temperature band, rainfall, atmosphere composition, gravity range, biochemistry). The habitability of each region and world for the people modifies growth, health and willingness to settle. A cold-adapted people colonising a hot world suffers until it adapts (an acclimatisation innovation, or speciation of the people over epochs).

#### Reference pass 3 (R24)

- **Migration networks:** migrants prefer destinations where their **diaspora** already lives (a pull from co-ethnic population share). Chain migration follows: each wave raises the pull for the next. Diasporas keep ties home (remittances: wealth flows; news: rumour channels; marriage alliances). They may form foreign quarters (4.2) and, over time, ethnogenesis or assimilation (4.1 behaviour 5).
- **Demographic transition:** fertility falls with urbanisation, literacy, women's education where role norms allow it (below), child survival (medicine) and standard of living, with lags. Ageing populations follow, with fewer levies, more elders and a different politics (an elder-respecting culture gains stability).
- **Sex ratios after wars:** war deaths skew the adult sex ratio. The marriage market shifts: more polygamy where allowed, later marriages, widows' households and role-norm changes (women entering crafts and offices in cultures where norms are flexible). These changes are recorded as norm drift (F35).
- **Role norms** (`role_norms`: culture, role (office, profession, combat, priesthood, inheritance, property), eligibility by sex, age and class, stance). They are fully culture-defined, so matriarchal, patriarchal, egalitarian and caste-based worlds all arise from data. They drift with beliefs, law and experience, and they constrain careers (3.1), succession (4.6) and mobilisation.

#### Reference pass 4 (R27, R29, R34)

**Kinship systems** (`kinship_system` per people):

- descent: patrilineal, matrilineal, bilateral, double, ambilineal;
- residence after marriage: patrilocal, matrilocal, neolocal, avunculocal;
- descent groups: lineage, clan, moiety, house;
- terminology class: whether cousins are called siblings, which matters for incest rules and alliances;
- inheritance follows descent.

Matrilineal peoples pass titles and property through the mother's line (to the sister's son, for example), which changes claims (4.7), the house structure and the marriage strategy.

**Marriage alliance rules:**

- preferred spouse categories (cross-cousin marriage, clan exogamy, moiety exogamy);
- payments (bride price paid to the bride's kin, a dowry given with the bride, bride service in labour) as F38 gifts;
- polygamy forms, levirate (a widow marries the husband's brother) and sororate.

Alliance theory emerges: exchange of spouses between lineages builds durable alliances (relation +, treaties of kind marriage_pact), and asymmetric exchange creates rank between wife-givers and wife-takers.

**Reproductive systems and sex** (people biology): typed systems are two-sex, sequential (sex changes with age or condition), ambisexual (sex chosen or assumed in a fertile phase), caste-based (hive peoples with castes: worker, soldier, breeder) or asexual (budding, fission). Role norms (4.1 reference pass 3), succession, marriage, fertility, demography and law all read the system. Le Guin-like peoples without fixed sex have different marriage, succession and war patterns, all from data.

**Nomadism and transhumance:** pastoral peoples and their mobile settlements (settlement subtype `camp`, a mechanical mobility flag) move between seasonal pastures along a migration circuit (regions by season). Herd sizes, grazing pressure (F2.5) and water decide the circuit. Nomads trade with, raid or tax sedentary neighbours (a tributary relation from nomads to farmers is common), and they have high asabiyya at the steppe frontier (F37). Steppe confederations form under a charismatic leader (charismatic legitimacy, 4.6 reference pass 4) and fragment after his death.

**Legacy traits** (Humankind-style): when a people undergoes ethnogenesis, adopts a new culture identity (conversion, a conquest assimilation, a new era of the polity) or a successor people emerges, it keeps **legacy traits**: selected innovations, art forms, beliefs and martial styles from the predecessor, and a reference to it in its founding myth (F33). Cultural history therefore stacks.

#### Reference pass 5 (S-A OCM 17, 27, 30, 51, 55, 56)

- **Revitalisation and nativist movements:** under heavy acculturation pressure (conquest by a distant culture, value distance, the suppression of language and forms), movements arise to **restore** the old ways (nativism), to **synthesise** new hope from old and new (revitalisation with a prophet, F37 crises), or to **adopt** the dominant culture wholesale. They follow Wallace's stages: steady state, stress, distortion, revitalisation, new steady state, as movement factions with typed goals (revive the language, restore the old god, expel foreigners).
- **Intoxication cultures:** each people has drinking and drug customs (which substances, who may use them, on which occasions, through norms F35). They link to the economy (brewing, F24), health (dependence, F30), religion (sacred intoxicants in rites, visions for mystics) and violence (brawls at feasts, F18).
- **Body modification and adornment:** tattoos, scarification, piercings, cranial shaping, tooth filing, cosmetics and jewellery codes are culture data with **meanings** (status, clan, deeds, age-set, marriage, mourning, protection charms). Marks are visible state on the body (F4, F26 appearance) and are read by others (identification, reputation, presence by culture). A warrior's tattoos tell his kills; an exile's brand tells his crime.
- **Time budgets:** each class has a time budget per sampled year (work, rest, worship, leisure, travel, military service), set by norms, laws (rest days), seasons and labour regimes (corvée). Output, satisfaction, fertility and participation in gatherings read the budget. Holy days and long festivals cost output and gain cohesion.
- **Naming customs:** name-giving rites (when and by whom), naming patterns (patronymics, matronymics, clan names, teknonyms, deed names, a secret name alongside a public one), taboo names (the names of the dead not spoken for a time) and renaming at life stages (initiation, marriage, a monastic vow, an ascension). Names are typed and connect to true names (F20 reference pass 3) and to the Namer's semantics (8.1 reference pass).
- **Age-sets and age-grades:** in cultures with age-set systems, all those initiated in a span of years form a named **age-set** that moves together through grades (boys, warriors, junior elders, senior elders). Age-sets hold collective duties (warrior age-sets form the military), rights (marriage only after the warrior grade) and loyalties (age-mates as comrades across lineages). Promotion ceremonies are gatherings that can be delayed (generational tension, F12 reference pass 3).

#### Reference pass 6 (S-E)

Peoples gain the biological fields of 3.2 reference pass 6: thermoregulation and sensory profiles. These change their campaign seasons, labour seasons, preferred terrain and the warfare they excel at (cold-blooded peoples avoid winter war; dark-sighted peoples fight at night and underground).

### 4.2 Settlement

**Current.** population, prosperity, defense, piety, plus a society row. Settlements have no wealth, and city tiers are display-only.

#### Attributes

- `size_tier`: hamlet, village, town, city, metropolis. **Mechanical:** it gates districts, offices and structure slots.
- `districts`: a typed `districts` table with kind (farmland, market, craft quarter, temple quarter, harbour, citadel, slums, palace, foreign quarter, necropolis), level and condition.
- `infrastructure`: walls (level, material, condition), gates, roads, water (well/cistern/aqueduct), sanitation, granary capacity, warehouse capacity, harbour capacity, defensive towers.
- `treasury` (polity-held or city-held for free cities), `tax_rate` (by polity law), `tolls`.
- `order` 0–100 (crime and policing), `crime` 0–100, `unrest` 0–100 (replaces implicit uprising chances), `sanitation` 0–100, `fire_risk` 0–100 (timber density × crowding).
- `garrison` (army reference, Part 5.1), `militia` (from the population and the warrior class).
- `wealth` 0–100: added. Payments stop falling back to prosperity.
- `foreigners` share by people (multi-ethnic cities), with foreign-quarter districts.
- `prestige` 0–100: wonders, artworks, renowned residents.
- `siege_state` (supplies days, wall breaches, disease in the city).

#### Behaviours

1. **Growth and districts.** A settlement grows through tiers by population and infrastructure. Each tier requires infrastructure (a city needs water and a granary). Districts are built by the polity, guilds or patrons with treasury and labour (structures, Part 7.2). Slums grow when immigration exceeds housing.
2. **Taxation and treasury.** Tax income per epoch = taxable output × tax rate × order × administrative capacity (literacy, scribes, writing). High taxes raise unrest. The treasury funds garrisons, walls, buildings, festivals and alms.
3. **Order and crime.**
   - crime = poverty + outcast share + inequality + low order + bandit factions nearby − policing (garrison, watch office) − law justice.
   - Crime lowers prosperity and trade. It also feeds bandit factions (Part 4.3) and creates punishment incidents (Part 4.5) that produce injuries.
4. **Fire, flood and collapse.** The fire chance per sampled year = fire_risk × dry weather. Fires destroy districts and kill cohorts. Stone rebuilding lowers future risk.
5. **Sanitation and disease.** Sanitation sets disease_load in the region (F2.1). Aqueducts and sewers need engineering knowledge.
6. **Sieges:** see Part 5.4. Supplies are days of food from granaries over population. Water depends on wells or cisterns. Disease builds up inside. Morale and treason (a gate opened by a disgruntled faction) are modelled.
7. **Migration attraction.** Settlements pull migrants by prosperity, order, foreign-quarter tolerance (xenophilia) and opportunity (jobs).
8. **Urban culture.** Cities have their own culture-value drift, more xenophilic and less traditional, which creates city-versus-countryside tensions inside a people (feeding factions).

#### Interconnections

- Economy: markets, tolls, granaries.
- War: walls and garrison.
- Disease: sanitation.
- Polity: taxes, offices.
- Faith: the temple quarter; pilgrims.
- Culture: prestige and artworks.
- Crime: factions and laws.
- Environment: fire and flood.

#### Tables and rules

- **Tables:** `settlement_profiles`, `districts`, `settlement_infrastructure`, `settlement_treasury`.
- **Rules namespaces:** `urban`, `taxation`, `crime`, `fire`, `sanitation`.

#### Player levers and UI

- **Levers:** build or raze a district; set tax; declare a free city; grant a charter (a law).
- **UI:** a settlement plan view (districts as tiles), a treasury ledger, and an order/crime/unrest timeline.

---

#### Reference pass (R1, R4, R7)

- **Investment pool:** a share of profits from owners (nobles, merchants, guilds, cults, the polity) goes into an investment pool per settlement. A **construction capacity** (builders, masons, carpenters, engineering skill, materials) turns the pool into structures in priority order: the owners' interest, mandates (4.6 reference pass), and the needs of the population. Capacity limits how fast a city can grow and rebuild after a fire or a sack.
- **Internal logistics:** a settlement's hauling capacity (porters, carts, draught beasts, roads, canals) limits how much of the production reaches storage and the market (market access, 6.4 reference pass). A large city without roads or canals suffers waste and higher prices in its outer districts.
- **Survival economy:** on frozen worlds, in sieges or during a long winter (F2.2), heat and food rationing policies are settlement decisions (mandates) with ethics readings. Abandoning the old and sick is a real option where the culture's ethics allow it: survival against morale and memory (Frostpunk-like hard choices made by the engine or the agent).
- **Housing:** dwellings (F29) per district. Slums are low-quality, crowded dwellings that raise disease and crime; housing construction comes from the investment pool.
- **Local reputation** of every notable figure is held per settlement (F19), so heroes are welcomed and villains turned away at the gate (entry refusal and arrest on sight by the watch).

#### Reference pass 3 (R13, R23)

- **Desirability and land value** per district = amenities (temples, markets, fountains, parks, artworks) − nuisances (tanneries, slaughterhouses, prisons, pollution, crime, haunted memory) + prestige. Land value sets rents (household expenses, F29), who can live where (class sorting), and what builders want to build there.
- **Service coverage:** each service structure (well, temple, watch post, healer, market, school, bathhouse) covers districts within a radius by its capacity and staffing. Uncovered districts suffer: thirst, impiety, crime, disease, prices, illiteracy.
- **Housing evolution** (Caesar III-style): dwellings in a district rise in quality level when their coverage and goods needs are met (hut → cottage → house → townhouse → manor) and fall when they are not. Housing quality sets the class composition the district can hold.
- **Homelessness** (housing below demand: migrants, refugees, the ruined) raises crime, disease and unrest, and feeds slums and mobs (F32). **Slum clearance** is a mandate (displacement, unrest, a later rebuild). **Gentrification** (rising land value pushes the poor outward) is an emergent effect.
- **Fire and crime prevention:** watch posts and fire brigades (a structure kind `firehouse`) lower fire and crime by coverage. Wooden districts without brigades burn in great fires (F2.3 dry wind).
- **Urban morphology:** a settlement's growth pattern is organic (old quarters, irregular), planned (a grid from a founding plan or a rebuild after a great fire) or concentric (wall rings expanded over time). It affects fire spread, siege defence (inner walls), traffic (internal logistics) and district adjacency.
- **Turf:** criminal organisations (4.3 reference pass 3) hold turf by district, collect protection, run gambling, smuggling and fencing, and fight turf wars (incidents, injuries, deaths, order −).

#### Reference pass 4 (R29, R42)

**von Thünen land-use rings:** around each market town, land use by distance follows transport cost and perishability:

- market gardens and dairy near the town;
- forestry for fuel next;
- grain further out;
- ranching furthest.

Region land-use shares (F2.5) are derived from the distance to the nearest market by mode (rivers stretch the rings). Roads and canals reshape the rings, so a new road turns pasture into farms.

**Central place hierarchy:** market towns emerge at spacings set by the range of goods (how far people travel for each good) and the threshold population (how many buyers a good needs). Hamlets serve daily needs, towns weekly ones and cities rare ones. The engine evaluates the central place gaps when choosing where new settlements are founded and which settlements grow into towns (settlement tier growth gains a centrality term).

**Preparedness:** settlements invest (mandates, the investment pool) in levees, firebreaks, stockpiles, drills, watchtowers and seawalls. Preparedness lowers disaster losses (F2, 3.4). It is visible to the drama manager as a reason a disaster did not become a catastrophe.

**Relief diplomacy:** after disasters, other polities and cults may send **aid** (commodities, healers, labour). Aid creates gratitude memories and favours (F20), a gift obligation (F38) and standing for the aid-giver's god. Refusing aid from a rival is a face issue (F16 reference pass 4).

**Reconstruction:** rebuilding after fire, flood, quake or sack is an opportunity. Planned rebuilds (a grid plan, stone instead of wood, wider streets) need treasury and a planner, while opportunistic rebuilds reproduce the old risks. Elites may seize burned land (a dispossession incident).

#### Reference pass 5 (S-A OCM 26, 27, 65, 74; S-D Workers & Resources)

- **Cuisines and meals:** each culture's cuisine is a set of dishes made by production methods from local ingredients (F24) under its preferences (F15) and taboos. A cuisine spreads by contact and diaspora, and fine cuisine is a status marker (nobles' demands). Shared meals (commensality) are interactions with norm rules (F35: who eats with whom), and food is part of gifts and feasts (F38).
- **Taverns, inns and drinking houses:** structures of kind `tavern` and `inn` in settlements and along routes. They are **social hubs**: interaction density, gossip nodes (F11 reference pass 3), recruitment places for schemes, mercenaries and crews, brawl sites, and lodging for travellers and caravans (route capacity). Innkeepers are information brokers (lore as currency, F19 reference pass 3).
- **Welfare institutions:** almshouses, orphanages, foundling homes, hospitals for the poor, leper houses and widows' houses. They are run by cults, guilds, polities or patrons, take in outcasts, orphans and the maimed (F4.5 cohorts), and lower mortality and crime among the poor. Patrons gain piety and reputation (F19). Their absence fills the streets with beggars and the gangs with children.
- **Commuting:** workers live in districts and work at workplaces. The labour available to a workplace is limited by the travel time from housing districts (internal logistics, roads, bridges, ferries). Distant mines need worker camps (a settlement subtype) or slaves (4.9 reference pass 4).

### 4.3 Faction (interest group, guild, order, band)

**Current.** strength, wealth and sway. Factions have no behaviour of their own.

#### Attributes

- `kind` (typed): merchant_guild, craft_guild, priesthood, warrior_order, noble_council, peasant_league, rebels, bandits, pirates, assassins, scholars_academy, secret_society, mercenary_company, interworld_federation, wandering_market, void_pirates (the existing engine kinds map onto these)
- `scale`: band (≤ 50 named), company, organisation, network
- `agenda`: a value vector (F5) plus typed **goals** (`faction_goals`). Goal kinds: lower_taxes, monopoly_on(commodity), install_claimant(id), abolish_law(id), enact_law(kind), war_on(id), peace_with(id), protect_craft, convert_realm(god), independence, loot(settlement).
- `members` (named mortals via MEMBER_OF bonds with a rank) and a **membership share** of cohorts (e.g. 30% of merchants)
- `leader` (office)
- `treasury`
- `cohesion`
- `secrecy` 0–100 (for secret societies and assassins)
- `influence_over` (per polity and settlement: sway)
- `armed` (has a band army)
- `reputation` (by culture reading of its acts)

#### Behaviours

1. **Agenda pursuit** (the core missing behaviour). Each epoch a faction picks an **action** by goal priority, means and opportunity:
   - **lobby:** sway + treasury, aimed at an office holder's opinion
   - **bribe:** treasury → an opinion modifier
   - **petition or enact:** law changes through the polity's decision rule (Part 4.6)
   - **strike or boycott:** withdraws guild labour; output falls; settlement unrest rises
   - **riot:** order falls
   - **coup:** needs an armed faction plus a claimant
   - **assassinate:** needs assassins or intrigue; targets mortals and creates hits (F4)
   - **smuggle** (bandits and pirates)
   - **raid** (bandits)
   - **fund war:** the treasury goes to a polity war chest, for war aims that match the agenda
   - **recruit:** members grow
   - **schism:** the faction splits on agenda divergence
2. **Power contest.** Inside each polity the factions' sway shares form a **power balance**. The current regional dominance weights (`politics.py`, display-only) become this mechanical balance, which feeds the polity's decision rule.
3. **Guild monopolies.** A guild with a monopoly sets commodity prices (Part 6.3) and blocks rival production; this raises crime through smuggling.
4. **Bandits and pirates.** They live on trade routes and coasts: tolls and robbery reduce route throughput, and they hit traveller cohorts. They can be suppressed by garrisons (a military campaign of kind `suppression`, Part 5). They can be legitimised by a polity charter (privateers).
5. **Mercenary companies.** A company has a captain (a mortal), contract terms (treaty kind `condotta`) and loyalty that follows pay. Unpaid mercenaries turn bandit or change sides mid-war.

#### Interconnections

- Polity (decision rule, coups).
- Economy (monopolies, strikes).
- War (funding, mercenaries).
- Crime.
- Faith (priesthood factions and cult politics).
- Knowledge (academies deepen knowledge and keep secret branches).

#### Tables and rules

- **Tables:** `faction_profiles`, `faction_goals`, `faction_memberships`, `faction_actions` (log).
- **Rules namespaces:** `factions` (extended), `intrigue`, `mercenaries`, `banditry`.

#### Player levers and UI

- **Levers:** set goals, fund, outlaw, charter.
- **UI:** a power-balance donut per polity; a faction agenda card; an action log.

---

#### Reference pass (R4, R6)

- **Estates and interest groups** (R6): factions of kind `estate` represent classes: nobility, clergy, burghers, peasants, and warriors where martial. Each has **privileges** (typed grants from the polity: tax exemptions, a monopoly, a council seat, the right to bear arms, judicial immunity) and **loyalty** to the polity. Granting privileges raises loyalty and lowers state revenue or power. Revoking them raises disloyalty and faction pressure. Estate influence is a share of the polity's power balance (4.3 behaviour 2).
- **Political parties and movements** (R6): factions of kind `party` (organised for elections) and `movement` (a cause-driven mass group with a support share per cohort: abolition, independence, a religious revival, a land reform). Movements grow from pressures and ideologies. They lobby, protest (unrest), turn into parties where assemblies exist, or into revolts where they don't.
- **Chartered companies** (R4): faction kind `chartered_company` with shares owned by houses and merchants, a charter (a treaty or law from a polity) granting a monopoly over a trade route, region or commodity abroad, armed forces (mercenary stacks) and dividends to shareholders. A company can conquer (an occupation, 5.8), become a polity, or collapse (bank and shareholders hit).
- **Holy orders:** faction kind `holy_order`, bound to a cult with a military arm, fed by cult tithes and with members from the warrior and noble classes. They serve holy wars and crusades, holding fortresses on borders.
- **Guild ranks and craft secrets:** guild membership follows profession ranks (3.1 reference pass). Guilds hold secret techniques (8.4 secrecy), control apprenticeships and set quality standards, raising the quality tier (F24).

#### Reference pass 3 (R10, R14, R22, R23)

- **Criminal organisations** (faction kind `crime_family`, `thieves_guild`, `smuggling_ring`, `pirate_brotherhood`):
  - a hierarchy of ranks;
  - rackets (protection, smuggling, gambling, fencing, kidnapping, counterfeiting) with income;
  - turf;
  - officials on the payroll (hooks and bribes, F20);
  - an omertà-like code (an oath, 4.8) with traitors punished.
  
  Wars between them are turf wars. Polities can suppress them (thief-takers, the watch, purges) or co-opt them (privateering, informants).
- **Merchant houses with trading posts:** merchant households and chartered companies open **trading posts** (a structure kind `kontor`) in foreign settlements by treaty or charter. A trading post gives local market access, warehouse speculation (6.4 reference pass 3), intelligence (merchants as informants) and a diaspora seed.
- **Magical orders and covenants:** faction kind `magical_order` with:
  - a code (typed laws among mages: no killing of members, no dealing with outer beings, a duty to share discoveries);
  - tribunals that enforce the code;
  - covenants (structures with laboratories, libraries and a magic resource income from the sites they hold, 6.2 reference pass 3).
  
  Orders compete with cults over magic legality (4.5) and may be at war with each other or with the polity.

#### Reference pass 4 (R36)

- **Art movements** (faction kind `art_movement`): artists sharing a manifesto (a value vector plus preferred art forms, 7.5). Movements compete for patrons and canon (7.4 reference pass 4), provoke scandals (norm breaches, F35) and become the next orthodoxy.
- **Sports clubs and leagues** (faction kinds `club`, `league`): teams of athletes (mortals with athletics skills) compete in games and races at arenas and festivals. Clubs have **fandoms** (cohort support shares) and **betting** (a market in which wins and losses move household wealth).
- **Circus factions** (the Nika-riot pattern): when a polity's fandoms coincide with class, district or religious lines, clubs become political factions. They hold public opinion leverage, can be bought by rulers, and their crowds are a riot cascade risk (F32). A lost championship plus a tax rise can burn a capital.

#### Reference pass 5 (S-A OCM 47)

**Cooperatives and mutual societies** (faction kinds `cooperative`, `mutual_society`, `burial_society`): members pool resources for shared production (a mill, fishing boats, irrigation), insurance (6.4 reference pass 5), burial costs (funerals, 3.1) or credit (rotating savings). They are democratic inside (member votes), raise members' SoL and resilience, and can grow into political movements.

### 4.4 Cult (religious organisation and its doctrine)

**Current.** followers, zeal, influence and devotion. Devotion is used only for god resurrection; zeal never decays.

#### Attributes

- **Doctrine** (`cult_doctrines`):
  - doctrine value vector;
  - **tenets** (typed `TenetKind`, 3–6 per cult): pacifism, holy_war, asceticism, sacred_suffering (honours the maimed), purity_of_body (the maimed are unclean), ancestor_veneration, human_sacrifice, animal_sacrifice, celibate_clergy, proselytism, exclusivity (no syncretism), syncretic_openness, monastic_learning, anti_magic, sanctified_magic, judgement_by_deeds, judgement_by_faith, reincarnation, martyrdom_glory, divine_kingship (rulers are the god's sons), dietary_law(commodity), sacred_species(id), pilgrimage_duty(place);
  - `judgement_doctrine` (Part 3.3).
- **Clergy:** an offices hierarchy (high priest, priests, monks, inquisitors), `clergy_count` (from the priest class share), `clergy_quality` (the theology skill aggregate).
- **Holdings:** temples (structures bonded), lands (tithe base), relics (items with relic status), holy places.
- **Treasury** with `tithe_rate`.
- `orthodoxy` 0–100: tolerance for heresy (inverse of syncretism openness).
- `zeal` (existing, now with decay and drivers), `influence` (existing), `devotion` (existing, extended to all cults as a resource).
- `heresies` (child cults with a doctrinal distance).
- `liturgical_language`.

#### Behaviours

1. **Tenets act.** Every tenet is a set of typed modifiers and rule hooks. For example:
   - holy_war: an offensive war on infidels gains a morale +, and peace with them costs zeal.
   - pacifism: the warrior class share target −, and refusing war costs the polity legitimacy when its ruler is devout.
   - sacred_suffering vs purity_of_body: inverts the presence reading of injured mortals for members (F4.5).
   - human_sacrifice: cohort deaths and captives consumed; Death or Blood god essence +; infamy with other cultures.
   - celibate_clergy: clergy lines don't found houses.
2. **Zeal dynamics.**
   - Zeal rises from: persecution (a memory), martyrdom, miracles of the god, holy war victories, preaching, crises (plague, doom omens).
   - Zeal falls from: prosperity, comfort, scandal (a clergy vice condition revealed), and failed prophecies (a mocked prophecy linked to the cult).
   - Zeal > [80] triggers **fanaticism** events: inquisition, iconoclasm, crusade.
3. **Tithes and wealth.** Tithe income from followers' output. It funds temples, alms (poverty pressure ↓, loyalty ↑), monasteries (scholarship) and war chests.
4. **Heresy.** Doctrinal drift under ideology pressure and a theologian's creativity creates heresies, which schism (existing rule, now doctrine-driven). Orthodoxy decides suppression (inquisition: punishment incidents, injuries, executions) versus tolerance.
5. **Missions.** Proselytising cults send missionaries along trade routes and journeys (rumour carriers, F11). Conversion chance = doctrine fit to the target culture × missionary skill × miracles − rival clergy quality − language barrier.
6. **Clergy and rulers.** Divine-kingship doctrine fuses offices. Otherwise a church–state balance exists: clergy sway in the polity power balance (Part 4.3), investiture conflicts as typed incidents, excommunication of rulers (legitimacy −).
7. **Relics.** Saints' bones and items get relic status. Pilgrimage to them produces piety, income and disease spread.

#### Interconnections

- Gods: a son's domains and passions seed the doctrine. A son can **reveal a tenet** (a tool), and its acceptance is weighted by fit.
- War (holy wars, crusade aims).
- Body (sacred suffering).
- Economy (tithes).
- Knowledge (monastic learning protects knowledge in dark ages, which generalises `dark_ages.py` protection).
- Afterlife (judgement).
- Law (religious law).

#### Tables and rules

- **Tables:** `cult_doctrines`, `cult_tenets`, `cult_holdings`, `cult_offices`, `heresies`.
- **Rules namespaces:** `doctrine`, `zeal`, `tithes`, `missions`, `inquisition`.

#### Player levers and UI

- **Levers:** add or remove a tenet; declare heresy; canonise a saint; set orthodoxy.
- **UI:** a doctrine sheet (tenets as cards with their effects); a heresy tree; a map of holdings.

---

#### Reference pass (R6)

- **Religious authority** is covered (investiture, excommunication). Additions:
  - **sacred offices** become titles (2T.6: the High Seat of a cult is a title with de jure jurisdiction over temples);
  - **councils of doctrine** are gatherings (F25) that vote on tenets, decide heresy and ratify saints;
  - **religious hierarchy vacancies** create succession crises inside cults (an anti-pope-like schism).
- **Pilgrimage economy:** pilgrimage gatherings spend at holy places. Their income goes to the cult and the host settlement.

#### Reference pass 4 (R33)

- **Mysticism:** some mortals (high intuition, the piety belief, a contemplative tradition) have **direct religious experiences** (visions and union states, as F30 packages). Mystics gain followers outside the clergy, can found orders or heresies, and are revered or persecuted by the orthodoxy. Their experiences are real contact if a god chooses to answer, or self-generated otherwise (a hidden truth visible to the player).
- **Millenarian movements:** prophecies of an end time (8.7), cosmic omens (sky events, rising doom, F27 tension) and immiseration (F37) mobilise **millenarian movements** (movement factions). They sell property, stop working, march, attack the "unclean" or await the end on a mountain. When the date passes, the movement disperses, reinterprets the prophecy (a new date) or turns into a sect.
- **Theodicy crises:** when great suffering hits the faithful (plagues, famines, defeats) and the patron god does not respond in a way the people can see, a **theodicy crisis** tests the doctrine. It is resolved by theologians' arguments (persuasion), a new doctrine (suffering as a trial, a hidden god), conversion away (standing neglect), or secular drift.
- **Sacraments:** life-stage rites (birth blessing, initiation, marriage, last rites) give typed protections in the doctrine's terms:
  - in the actual afterlife (3.3: rites performed change the routing);
  - against the possession of children;
  - against unrest at death.
  
  Missing a sacrament (no priest available because of plague, war or remoteness) is an anxiety thought and a real routing risk.
- **Believed afterlife against the actual afterlife:** every doctrine teaches an afterlife model. The actual strata (3.3) may differ. Souls who arrive and find their belief false suffer a **revelation shock** (the restless chance +, an emotion of the dead). The dead who return as ghosts or in dreams may tell the living, which is evidence for doctrinal debates (F33 accounts, theories of the afterlife, 8.4b). Gods can align the actual afterlife with their doctrine at an essence cost.
- **Secularisation:** faith (the piety belief) declines with literacy, scientific theories that displace divine explanations (8.4b), prosperity, urban life and **cosmic silence** (gods inactive in a world for long periods). It rises with disasters, wars, miracles and dominion (F31). Godless communities (existing) are one endpoint, and modernising sceptic cultures another.

#### Reference pass 6 (S-H)

**Sanctuary and asylum:** temples (by doctrine) and hosts (by hospitality norms, F35) may grant **sanctuary** to fugitives (criminals, runaway slaves, defeated rivals, refugees).

- Violating sanctuary is a desecration (8.6 reference pass) and a grave ethics breach.
- Sanctuary limits the pursuer: a siege of the temple, negotiation, or waiting.
- Cults gain leverage and income from sanctuary, and polities may restrict it by law (a jurisdiction conflict, 4.5 reference pass 3).
- Asylum between polities (exiles and defectors) is a diplomatic act with relation effects.

### 4.5 Law

**Current.** rigidity and justice. The content is prose only; the engine never enacts laws.

#### Attributes

- `law_kind` (typed `LawKind`, with typed parameters per kind):

| Area | Kinds |
|---|---|
| Succession | succession_rule (primogeniture/seniority/elective/tanistry/matrilineal/by_combat/divine_choice), `wholeness_required`, `gender_rule` |
| Property and inheritance | inheritance_split, land_tenure (feudal/communal/freehold), slavery (allowed/banned/debt_only), serfdom |
| Fiscal | tax_rate, tithe_enforcement, tolls, debt_law (bondage, prison, jubilee) |
| Penal | punishments by crime (theft → fine/hand; murder → wergild/death/exile; treason → blinding/death; blasphemy → tongue/death; desertion) with `cruelty` derived |
| Military | levy_law (share, duration), conscription, standing_army, veteran_pension, ransom_custom |
| Social | marriage_law, sumptuary_law (class luxuries), guild_charter, foreigner_rights, religious_tolerance, worship_ban (existing kind), blood_feud_custom (wergild allowed?) |
| Public health | quarantine, burial_law, sanitation |
| Magic | magic_ban, licensed_magic, rite_restrictions |

- `jurisdiction` (polity, settlement, cult: religious law)
- `enforcement` 0–100 (from order and officials)
- `legitimacy_basis` (custom, decree, divine, council)
- `rigidity`, `justice` (existing; justice is now derived from the parameters and the culture reading)
- `enacted_epoch`, `enacted_by` (office holder or faction)

#### Behaviours

1. **Enactment and repeal** happen through the polity's decision rule (4.6), driven by factions, rulers, cults and crises. This closes the gap that the engine never enacts laws. A plague raises the quarantine law chance; a lost war raises conscription.
2. **Effects are typed rule parameters,** never prose. Succession law decides heirs. Penal law decides punishments for crimes and their injuries. Levy law sets mobilisation. Veteran pension supports the maimed cohort (reducing outcasts and raising the military's opinion). Slavery law enables captive enslavement (Part 5.7). Sumptuary law sets luxury demand by class.
3. **Legitimacy of laws:** a law at odds with culture values loses enforcement and causes unrest (civil disobedience). Customary laws resist repeal by rigidity.
4. **Legal conflict:** in conquered territories, conqueror law versus local law creates unrest. The existing 35% conquest repeal becomes this conflict, resolved over epochs.

#### Interconnections

Mortal (punishments → injuries; succession), polity, factions, economy (taxes), war (levy), faith (religious law), disease (quarantine), magic.

#### Tables and rules

- **Tables:** `law_profiles` (kind and typed params JSON validated per kind), `law_jurisdictions`.
- **Rules namespace:** `legislation`.

#### Player levers and UI

- **Levers:** enact or repeal, edit parameters.
- **UI:** a law code view per polity, grouped by area, with effects rendered from rules (decision 70).

---

#### Reference pass (R1, R6)

**Enactment as a process** (Victoria 3-style, R6):

- A proposed law (by an office holder, a faction, an estate or the ruler) enters `law_proposals` with progress 0–100.
- Each epoch, progress moves by the support (power balance of supporters against opponents) under the decision rule. Obstruction (estates using privileges, hooks against council members) can stall it.
- Advancement checks may produce events: debates in an assembly (a gathering), riots, or compromises (an amended parameter).
- The law passes at 100. It fails, with a reputation cost for its champion, if it stalls for [3] epochs.

**Justice process** (R1). Crimes are incidents with **witnesses** (co-located mortals, with each witness's relationship to the perpetrator affecting testimony).

- An **investigation** is run by the sheriff or high-judge office: their skills, the witnesses and evidence (secrets), and **interrogation** (with an ethics-dependent use of torture, an injury source).
- A **trial** is a gathering: a judge with traits (just or arbitrary), a jury if the law says so, and trial by combat or by ordeal where the law and culture allow.
- **Sentences** follow the penal law (4.5). **Wrongful convictions** happen (low investigation quality, forged evidence by schemes) and create grievances and martyrs.

#### Reference pass 3 (R18, R23)

**Legal system typology** (`legal_systems`, per polity and cult jurisdiction):

| System | How law is made | How disputes are decided |
|---|---|---|
| customary/oral | elders, memory-dependent (the memory attribute of the lawspeakers) | assemblies, oaths, compurgation |
| codified | written codes (the writing techniques) | judges applying the code |
| religious | sacred texts and clergy | ecclesiastical courts |
| precedent | rulings by judges become binding | courts citing case law |
| oracle | a god's answer through a seer (the son can answer, lie or ignore) | divination, ordeal |
| mixed | | |

- **Precedent:** under a precedent system, each trial ruling (F33 accounts of the trial) can become a **precedent** (`precedents`: question, ruling, court, epoch, authority). Later trials on similar questions follow it unless overturned by a higher court. Case law accumulates and drifts with judges' beliefs, so a realm's law evolves without legislation.
- **Courts and appeals:** a court hierarchy (local, provincial, royal or high, and religious) is set by offices. Appeals go up the chain with fees, delays and chances of reversal. **Advocates** are a profession (skills: law, oratory) whose quality changes trial outcomes, so the rich get better justice (an inequality coupling).
- **Property registries and contracts:** where the codified technique exists, land titles and contracts (debts, sales, dowries, guild indentures) are registered. Registered rights are enforced by courts, and unregistered ones depend on strength and witnesses. Land disputes are trials or feuds.
- **Jurisdiction conflicts:** clergy claim jurisdiction over clergy and faith matters, guilds over guild matters, and foreigners may have treaty rights (extraterritoriality). Conflicts between jurisdictions are crises between the institutions (an investiture-like struggle).
- **Pardons and amnesties:** rulers can pardon (prestige or tyranny by the ethics reading) and declare amnesties (after a civil war, a coronation). Pardoning one's friends is a corruption reading.
- **Outlawry and bounties:** an outlaw loses legal protection: anyone may kill or rob them without crime. Bounties (treasury or private) attract **bounty hunters and thief-takers** (a profession). Outlaws form bands (4.3) and may become folk heroes (reputation, F19, in the communities they spare).
- **Prisons:** conditions (food, crowding, cruelty), length of sentences, prison gangs (status hierarchies, F18 reference pass 3), disease, escapes and releases. Released prisoners carry a stigma (reputation) and skills learned inside (intrigue).

#### Reference pass 4 (R34)

**Punitive remaking** (Bas-Lag-style, ethics-gated): in cultures with magic or biomancy and a cruel penal ethic, sentences may **remake** the convict's body as punishment (an F30 package: a transformation with a function loss or a forced function: a labourer's extra arms). The remade form a visible underclass, with their own memories, movements and eventual revolts. Narration follows G9.

#### Reference pass 5 (S-A OCM 69; S-D Shadows of Doubt)

**Evidence model for investigations:** crimes and schemes leave **evidence** (`evidence`: kind, incident, points to, reliability, decay):

- witnesses: with reliability from perception, memory, relationship with the accused and bribes or hooks;
- physical traces: wounds by weapon class (F4.3), blood, footprints in weather and terrain, poison signs, stolen goods;
- documents: letters, ledgers, forged items (F21);
- timelines and alibis: whereabouts from incidents and gatherings;
- magical traces: residue of rites (8.6), detectable by mages.

Investigators (the high judge's office, sheriffs, thief-takers, inquisitors) gather evidence by skills (perception, intuition, law, interrogation) within time limits as the evidence decays. Verdicts follow from evidence weight against the legal system's standard (4.5 reference pass 3), so wrongful verdicts arise from bad evidence or bias (F40), not from dice.

### 4.6 Polity (new type: realm / state)

#### Attributes

- `government` (`GovernmentKind`): chiefdom, monarchy, theocracy, oligarchy (merchant republic), republic, tribal_confederation, empire, hive_council, god_kingdom (a son rules directly), occupation (military rule).
- **Decision rule** (from the government): autocratic (the ruler decides, weighted by advisers' opinions), council vote (offices vote by sway), assembly (cohort-weighted), divine (a son's will via the patron).
- **Territory:** member settlements, peoples and regions (`polity_territories` with control 0–100 per region). Provinces are an optional grouping.
- **Offices** (`offices` table: polity, kind, holder mortal, appointed_by, since, powers). Kinds: ruler, heir_designate, regent, chancellor, marshal, treasurer, high_judge, spymaster, governor (per province), ambassador.
- **Legitimacy** 0–100 of the ruler, computed from:
  - succession correctness against the law
  - conditions vs `wholeness_required` and culture readings (F4.5)
  - honour, infamy and renown
  - religious sanction (cult opinion; excommunication)
  - victories and defeats
  - prosperity
  - age (child or senile)
- **Stability** 0–100: legitimacy × faction balance × unrest × war weariness.
- **Treasury**, debt (loans to banks, guilds or other polities), war chest.
- `administration` capacity: literacy × scribes × writing system × roads, which limits effective territory size and creates **overextension**.
- `ideology` (an optional link to an ideology entity), `state_religion` (a cult), `capital` (a settlement), `emblem` (heraldry: typed motifs, used by artworks and armies).
- `claims` (Part 4.7), `treaties` (Part 5.8), `vassals` (overlord–vassal relations with obligations: a treaty kind).
- `war_weariness` 0–100.

#### Behaviours

1. **Decisions.** Each epoch the polity takes decisions on its agenda: laws, war or peace, taxes, building, appointments and succession. Each uses its decision rule; office holders' opinions and personalities (F5, F7) weigh the options. A paranoid ruler purges, a greedy one taxes, a pious one funds temples. The LLM mortal agent can drive a ruler when selected; otherwise the engine decides.
2. **Succession** (on ruler death or deposition):
   - **Heirs** are chosen by law: candidates filtered by sex, age, wholeness and house, then ordered by rule.
   - **Disputes:** rival claimants with claims (4.7) evaluate pressing the claim (their opinion, faction support, strength).
   - **Outcomes:** a peaceful succession, a regency (child heir; regent office; regent ambition can lead to usurpation), or a **succession war** (a civil war, Part 5, with sides from factions and houses).
   - The existing `succession.py` heir spawning remains as a fallback when no candidate exists.
3. **Overextension.** When territory exceeds administration, provinces drift: governors gain autonomy, secession pressure rises and taxes leak. This is a balancing loop on empire size, and replaces the flat empire tier.
4. **Vassalage.** Vassals owe tribute, levies and loyalty by treaty. Low opinion plus overlord weakness leads to revolt or switching to another overlord. The existing tribute is migrated into vassal treaties.
5. **Revolts and coups.** Unrest in regions plus factions with goals lead to typed revolts: peasant, noble, religious, secession, slave. Each spawns a rebel army with a war aim.
6. **Tier at every level (decision K.5).** Civilization tiers are deepened, not just moved: they exist at every level and each level is mechanical.
   - **Polity tier** is computed from territory, administration, knowledge and worlds. It gates realm capabilities: the existing unlocks (`catalog/civilization.py`), plus standing armies, provinces, embassies, coinage and an interworld presence.
   - **Community tier** remains for every people and settlement, with its own mechanics: the settlement size tier (4.2) gates districts and offices, and a people's development tier gates crafts and institutions.
   - **Regional standing** ranks a polity within its world (hegemon, great power, minor power, client) and feeds diplomacy weights.
   - Every tier has typed requirements, unlocks, hysteresis (the existing margins) and decline causes (overextension, plague, lost knowledge, sacked capitals).
7. **Diplomacy:** foreign policy is computed per polity, not per community. Communities in a polity share its wars and treaties, which solves the "every war has two parties" gap at the source.

#### Interconnections

This is the hub. Law, factions, houses, cults, war, economy (taxes), administration (knowledge and writing), body (legitimacy), culture (values), gods (divine kingship, a son as patron of the realm).

#### Tables and rules

- **Tables:** `polity_profiles`, `polity_territories`, `offices`, `office_history`, `polity_treasury`, `vassalages`.
- **Rules namespaces:** `government`, `succession` (extended), `legitimacy`, `administration`, `overextension`, `revolts`.

#### Player levers and UI

- **Levers:** change the government; appoint; depose; split or merge polities; grant independence.
- **UI:** a realm view (map territory with control shading, an offices org chart, legitimacy and stability gauges with a "why" breakdown, a succession line preview: "if the king died now…").

---

#### Reference pass (R1, R4, R6)

**Coalitions and aggressive expansion:** conquests, unjustified wars and broken treaties raise **threat** (a per-polity memory in every polity that heard of it, F11 and F22, scaled by proximity and value distance). When threat across neighbours exceeds `diplomacy.coalition_threshold` [50], they form a **coalition** (a treaty of kind `coalition` with a call-to-arms against the threatening polity). Threat decays slowly; good relations and marriages reduce it.

**Diplomatic capacity:** a polity maintains active relations (alliances, guarantees, vassal contracts, embassies) up to a capacity = administration + the diplomatic skill of its chancellor and ambassadors + the number of embassies (structures). Excess relations decay in quality.

**Diplomatic crises** (Victoria 3 plays, R6, `crises` table):

- A demand by one polity on another (cede a region, release a vassal, convert, pay) opens a crisis with an escalation clock.
- Other polities **back** a side for promised clause shares (favours, F20, and treaty clauses). **Swing parties** are courted.
- At each escalation step, either side may back down (prestige loss), concede, or let it reach war (the war starts with all backers as coalition sides).
- Crises are where the LLM agents of rulers make the most difference.

**Spheres and great powers:** polities above a power threshold in their world gain **great power** status (a regional standing level, K.5). Great powers maintain **spheres of influence** over weaker polities (client relations: votes aligned, trade preference, protection), contest each other's spheres, and convene **summits** (F25).

**Subject types:** vassal (levies + taxes), tributary (tribute only, otherwise autonomous), march (border military vassal: no taxes but obliged defence), personal union (same ruler, separate realms: from inheritance of titles, 4.11), client (sphere relation), colony (a dependent settlement on another world), protectorate. Each has typed obligations, a liberty desire (from opinion, relative strength and value distance) and revolt behaviour.

**Negotiable vassal contracts:** contract terms (levy share, tax share, the right to wage private war, coinage rights, succession confirmation) are clauses (5.13). The overlord can renegotiate (opinion cost), and vassals can demand a renegotiation through factions.

**Council with tasks:** each office (chancellor, marshal, steward, spymaster, court chaplain, high judge) chooses a **task** each epoch (improve relations with X, train troops, collect taxes, disrupt schemes, convert a province, purge corruption). The result scales with the holder's skills. Office holders' opinions of the ruler affect diligence, and a disloyal spymaster leaks.

**Elections and assemblies:** where the government has an assembly or elective monarchy, elections are gatherings. Votes come from cohorts or electors by class weight (the franchise law) and party or candidate appeal (beliefs fit, public opinion, bribery, hooks). Results are offices and seats in a council with voting power on laws.

**Corruption** (R4): corruption 0–100 per polity = administration overreach + low justice + office holders' greed facet + tax farming + absence of an audit office. It skims taxes, lowers enforcement and the effectiveness of mandates, and raises public disapproval. It is reduced by just high judges, audit tasks and an anti-corruption ideology.

**Tax types:** land tax (farmers and nobles), poll tax (per head), trade tax (tolls, markets), consumption tax (luxuries), tithes (cult), and tribute. Each has a collection efficiency (administration, corruption, order) and an incidence on classes' standard of living. **Tax farming** raises the short-term take but also corruption and unrest.

**Mandates and demands** (R1):

- Rulers and nobles issue **mandates** (production orders, export bans, construction orders, famine relief from state granaries, curfews). Unmet mandates anger the issuer; harsh ones anger the people.
- Nobles hold **demands** (dwelling quality, fine goods, an office, an honour). Unmet demands lower their loyalty.

**Policy networks** (Democracy-style, R6): laws and mandates are nodes with typed effects on classes' satisfaction, public opinion and economic outputs. Each class or estate's approval of the government is the weighted sum over current policies, so changing one policy shifts several groups at once.

**Constitutions and charters:** a polity's fundamental law (a law kind `constitution` of high rigidity) defines the government, the decision rule, the franchise and the estates' rights. Changing it is a high-threshold enactment, or a revolution.

**Interworld assembly:** an assembly of polities across worlds (the existing federation extended into a polity kind `assembly` with resolutions: shared route security, an embargo of a polity, a ban on void rites, a sanction on a son's world). Resolutions are voted by member weight and enforced by member obligations.

**Nationalism and separatism:** peoples inside a polity with a distinct culture and high cohesion develop a separatist movement when they are not the ruling culture, rising with grievances and falling with privileges and autonomy. An independence revolt (cause `independence`) follows past the threshold.

**Court:** the ruler's court is the set of courtiers (mortals resident at the capital with relationships to the ruler) plus **grandeur** (from the dwelling, artworks, feasts and fine goods). It raises prestige and diplomatic reception and attracts talent.

#### Reference pass 4 (R27, R28)

**Selectorate and winning coalition:** each polity has a **selectorate** (those with a say in choosing the ruler: all adult men of the tribe, the nobles, the council, the army, the priests) and a **winning coalition** (the subset whose support keeps the ruler in power), both computed from the government, the constitution and the power balance (4.3).

- **Small coalitions** (autocracies) make rulers spend on **private goods** for the coalition (gifts, offices, land, tax exemptions), with low public goods.
- **Large coalitions** make rulers spend on **public goods** (roads, granaries, schools, courts, defence).
- Coalition size therefore drives the polity's spending mix, corruption and SoL. Purging coalition members is how rulers survive, and the coalition's loyalty (opinion and the expected rewards under an alternative ruler) decides coups.

**Legitimacy types** (Weber):

- **traditional** (inherited by custom and succession law);
- **charismatic** (from the person's renown, miracles, victories, prophecy fit);
- **legal-rational** (from offices, laws and procedures, under bureaucracy techniques).

Each ruler's legitimacy (4.6) is a mix by type, and each type has different vulnerabilities: traditional to succession breaks, charismatic to defeat and death, rational to corruption.

- **Routinisation of charisma:** at a charismatic founder's death, the movement or realm must convert charisma into tradition (a dynasty) or rules (an institution). This is a crisis point: schism, a succession war, or a stable new order.

**Stationary against roving bandits:** a ruler's **time horizon** (expected tenure from age, health, legitimacy, the succession law and threat) sets extraction. Short horizons plunder (high taxes, sell offices, neglect investment), while long horizons invest. Insecure rulers therefore ruin their realms, and stable ones build them (Olson).

**Clientelism:** patron–client networks link powerful mortals and houses to clients (households, lesser nobles, officials) through favours (F20), protection and offices. Networks are the real structure of politics under formal institutions. Elections, votes and promotions follow patronage where institutions are weak (an institutional strength variable from bureaucracy techniques, justice and literacy).

**Venality of office:** offices can be sold (a revenue source), and buyers recoup the price from the office (corruption +, F19 tyranny for the seller in ethics that condemn it). **Sinecures** are offices with income but no duty, used as private goods for the winning coalition.

**Personal power bases** (Imperator-style): characters accumulate a **power base** (holdings, armies whose commanders are their clients, offices, wealth, popularity). A large power base makes a character dangerous: a governor or general with a large base can defy, extort or overthrow the ruler. Rulers counter with rotation, splitting commands, marriages and purges.

**Coup-proofing:** rulers can rotate commanders (army effectiveness −), create parallel guards (an upkeep cost), promote by loyalty over merit, and keep hostages. Coup-proofing lowers coup risk and military quality at once.

**Big-man and chief leadership:** in tribal polities, leadership is either **achieved** (a big-man who builds a following by gifts and feasts, F38; it does not pass to heirs) or **ascribed** (a chief by descent). Big-man polities fragment at the leader's death. Chiefdoms keep office. The transition from one to the other is a civic innovation.

#### Reference pass 5 (S-A OCM 48, 64, 65, 80)

- **Citizenship and naturalisation:** polities define **membership** categories (citizen, subject, resident foreigner, slave, protected minority), with typed rights (property, office, marriage, arms, courts, voting) and duties (taxes, levies, corvée). Membership is acquired by birth (by descent or by place), by naturalisation (residence time, conversion, service, purchase) or by grant. Foreigners' rights differ by treaty. Citizenship politics (expanding the franchise, expelling minorities) are movement goals and law kinds.
- **Travel regulation:** passes, safe-conducts and border controls at gates, passes and ports. They have costs (time, fees, bribes) and enforcement (guards, corruption). They are used against refugees, spies, plague carriers and smugglers, and they create a black market for forged passes (F20 identities).
- **Poor relief policy:** polity-level welfare (granary distribution, alms laws, workhouses, a parish system through the cult), with costs and effects on poverty pressure, mobility and crime. Welfare can be a public good (large coalitions) or a reward to specific groups (small coalitions, 4.6 reference pass 4).
- **Standard weights and measures:** a civic technique and a law. A standard lowers transaction costs (trade flows +, market convergence), enables taxation by quantity and helps engineering precision. Fraud with false measures is a crime and a guild offence.

#### Reference pass 6 (S-G, S-H)

**Economic systems** (`economic_system` per polity, possibly mixed by sector):

| System | How goods are allocated |
|---|---|
| **market** | the existing model (6.4) |
| **redistributive palace or temple economy** | producers deliver goods to central stores (the palace, the temple); scribes record them (writing and numeracy are required); the centre redistributes rations to workers, artisans and soldiers by office and need. Prices matter little; record keeping, storage and the centre's legitimacy matter much. Collapse of the centre (a sack, a fiscal crisis) collapses the whole economy (a Bronze Age collapse pattern) |
| **command economy** | an office allocates labour and output by mandates and plans (4.6 reference pass), with efficiency set by administration and information quality (F22) |
| **manorial economy** | lords hold estates; serfs owe labour and dues in kind; local self-sufficiency; markets only for surpluses |
| **gift and tribal economy** | F38 dominates; prestige drives production |

The system sets which mechanisms run (market flows against redistribution flows), what institutions matter and how crises propagate. Transitions between systems are civic techniques plus political struggles.

**The licensed fool and satire:** courts may keep **jesters** (an office) and cultures may tolerate **satirists** (artwork message kind `satire`). Satire mocks rulers and policies with a licence that lowers punishment by norm. It shifts public opinion (F21) and the ruler's prestige (F19), and acts as a pressure valve: tolerated satire lowers riot thresholds' sensitivity (F32), while suppressed satire raises grievances. Fools may speak truths no councillor dares (a counter to groupthink, F40).

#### Reference pass 8 (B3)

**Creating and abolishing offices:** polities (by the decision rule) can **create offices** (new governorships, ministries, sinecures, colleges of officials) and **abolish** them. Created offices absorb counter-elites (F37) at a fiscal cost; abolishing them saves money and creates aggrieved former office holders. This is the specified brake of L63, and a tool of coalition management (4.6 reference pass 4).

### 4.7 House (new type: dynasty, clan, noble line)

#### Attributes

- `founder_id`, `head_id` (an office inside the house)
- `members` (via kin bonds plus a `house_id` on the mortal)
- `prestige` 0–100
- `wealth`
- `heirlooms` (items with heirloom status)
- `emblem` and motto (typed motifs plus text)
- `house_traits` (heritable bloodline traits: long-lived, giant-blooded, god-blooded with son_id, cursed)
- `cadet_branches` (child houses)
- `seats` (settlements or structures)
- `feuds` (with houses, via memories)
- `alliances` (by marriages)
- `claims` (`claims` table: claimant mortal or house, title office, strength 0–100, basis: inheritance, marriage, conquest, divine, fabricated; pressed?)

#### Behaviours

1. **Marriage strategy.** House heads arrange marriages to maximise prestige, alliances and claims, subject to the people's marriage custom and value fit. The engine pairs eligible mortals across houses; the outcome creates a treaty kind `marriage_pact` between the houses' polities.
2. **Claims propagation.** Claims pass by inheritance law (a daughter's sons inherit her claim under some laws). Claims weaken over generations unless pressed.
3. **Prestige:** + offices held, victories, wonders funded, renowned members; − defeats, executions, maimings in a purity culture, infamy.
4. **Cadet branches** split when a house grows large ([12] living members) or on a succession dispute. A branch carries a claim against the senior line.
5. **Extinction:** with no members, heirlooms pass by law or are lost (to a hero quest kind relic), and claims die.
6. **Bloodline traits** inherit through members. Divine blood (a son's mortal child) carries a link to the son: an existence anchor (Part 9.1) and a fate.

#### Interconnections

Succession, war (houses as sides in civil wars), marriages (treaties), items (heirlooms), gods (divine bloodlines), culture (emblems in artworks), memory (feuds).

#### Tables and rules

- **Tables:** `house_profiles`, `house_members` (derived index), `claims`, `heirlooms`.
- **Rule namespace:** `houses`.

#### Player levers and UI

- **Levers:** found, merge or extinguish a house; grant a claim.
- **UI:** a house page (family tree with injuries and causes of death marked, claims list, emblem).

---

#### Reference pass (R6)

- **Houses hold titles** (4.11), not just claims. A house's power is its titles' rank and de jure territory.
- **Inheritance partition** (gavelkind law): titles split among sons or daughters by law, which fragments realms over generations (Loop R of division, braked by primogeniture laws and civil wars).
- **House feuds** are memories plus gatherings: duels at tournaments, insults at feasts.
- **Marriages for alliance and claim** are weighed through genetics (F26: inbreeding risk against claim consolidation).

#### Reference pass 3 (R19)

**Procedural heraldry:** every house, polity, title, army and guild has a typed **arms** (`heraldry`: field tinctures, divisions, charges (beasts, items, celestial bodies, body parts from house history: an eye, a hand), mottos in its language). It is generated from house history (deeds, injuries of the founder, totems, the patron god's symbols) and the culture's aesthetic, then inherited, differenced for cadet branches and combined on marriages (quartering). Arms appear on items, standards and structures (decorations, 7.1 reference pass) and render in the UI.

#### Reference pass 4 (R27, R34)

- **Segmentary lineages:** clans and lineages nest (a lineage within a clan within a tribe). Conflicts trigger **fusion and fission** rules: brothers fight cousins, but brothers and cousins unite against outsiders, and the whole tribe unites against foreigners. Feuds and alliances are computed from the segmentary distance between the parties at the moment of conflict, which gives stateless peoples order without rulers.
- **Multi-generational breeding and lineage plans:** secret orders (4.3) or houses can hold long plans (F37) that steer marriages across generations toward a target genome (F26: a predisposition, divine blood, a seer gift) or a target claim union. These plans work through schemes (F20: arranged marriages, concealed parentage) and are disrupted by love matches, exposure and infertility. Narration stays within G9.

### 4.8 Oaths and honour (typed table)

An `oaths` table: swearer, recipient (mortal, god, polity), kind (fealty, vengeance, celibacy, pilgrimage, protection, silence, blood_brotherhood), witnessed_by (a god: oath-domain sons gain essence per kept oath), status (kept, broken, fulfilled), and deadline.

- Breaking an oath produces an honour loss, a memory (`broke_oath`) for the recipient, and the god's wrath if the god was the witness.
- Oaths give the existing OATHBREAKER flag a mechanical source.
- Oath-domain sons gain a real role.

#### Reference pass 3 (R9)

**Geasa:** a geas is a personal taboo or obligation (never refuse hospitality, never eat a dog's flesh, never pass a burning house without helping) laid on a mortal at birth by a seer, by a god or by a rite, as an oath with a divine witness and no consent needed. Keeping it gives favour (dominion and standing with that god), and breaking it brings an F30 doom package (misfortune, wasting, death in battle). Enemies can engineer situations that force a geas conflict, a scheme kind `geas_trap`.

### 4.9 Society and labour (cross-cutting)

The audit noted that satisfaction feeds only revolts. With 4.1–4.6:

- **Class satisfaction** feeds labour productivity ([±20%]), faction recruitment, loyalty to the polity, migration choice and desertion in armies (a warrior class with low satisfaction deserts).
- **Inequality** (Gini-like over class wealth) raises crime and revolt pressure, scaled by the culture's hierarchy value: hierarchical cultures tolerate more.
- **Social mobility events:** a war hero is ennobled (class change → a house founded); a ruined merchant falls to the poor; a freed slave becomes free. Each is an incident and a memory.
- **Slavery and serfdom** (law-gated): captives (Part 5.7), debtors (debt law) and conquered cohorts can be enslaved. They raise output in mines and fields, lower cohesion, raise revolt pressure, and lower opinion across xenophile cultures.

#### Reference pass 4 (R41)

- **Corvée:** polities can levy labour obligations (days per season per household) for great works (walls, roads, wonders, canals). This lowers farm output in those seasons and raises unrest, with an ethics reading. Wonders built by corvée carry a memory of suffering in folk accounts (F33).
- **Indenture and debt peonage:** debtors (debt law) and migrants (contracts) serve fixed terms or until debts are paid. In practice, debts can be manipulated to be unpayable (an exploitation score per employer). Indentured cohorts have low SoL and mobility and are a movement recruitment base.
- **Slave markets:** where slavery is lawful, enslaved people (captives, debtors, the condemned, the bred) are traded with prices by skill, age, origin and appearance (F26). Markets sit in settlements with the slave-trade institution. Supply comes from wars and raids (5.7), so slave-holding economies have a war-for-captives incentive (Loop R).
- **Manumission:** freedom through purchase, a master's will, service, law (an abolition, partial reforms) or revolt. Freedmen hold an intermediate status (role norms, reputation) and their own households and networks (often a diaspora). Abolition movements form from ideologies, slave revolts and the beliefs of the free.

### 4.10 Community relations (extended)

The relation scalar becomes the aggregate of the opinion components (F7) between the two communities' populations and rulers. Diplomacy acts between **polities** (4.6). Peoples keep inter-people opinions, which feed migration, assimilation and ethnic conflict inside multi-ethnic polities. Blood feuds become memory-driven vendettas with escalation (Part 5.9).


### 4.11 Title (new type)

#### Attributes

- `rank`: lordship, county, duchy, kingdom, empire, plus religious ranks (see, archsee, high seat) and special ranks (a mercenary captaincy, a guildmastership)
- `de_jure_territory` (regions or lower titles)
- `de_jure_liege` (the higher title)
- `holder` (a mortal; or a polity for republics)
- `holder_history`
- `succession_override` (a law, 4.5)
- `emblem` (heraldry)
- `prestige`
- `created_epoch`, `destroyed_epoch` (titles can be dormant: held by nobody, still claimable)
- `capital`
- `regalia` (items, 7.1)

#### Behaviours

1. **Creation** requires holding a share of the de jure territory (`titles.creation_share_pct` [51]), prestige and the right techniques (civic tree, 8.4). **Usurpation** requires holding the de jure capital and a majority of the territory.
2. **De jure drift:** territory held for a long time under another title drifts into its de jure ([8] epochs). Maps of de jure realms diverge from de facto ones, and that gap is the source of claims and wars.
3. **Claims** (4.7) target titles, not offices.
4. **Personal unions:** a mortal holding two top titles rules both polities. A later partition, or a union treaty (merging), may follow.
5. **Dormant titles** can be recreated by a claimant ("restore the old kingdom"), which is a legend resonance case (8.2).
6. **Titles and offices:** the ruler office of a polity is held by the holder of its primary title. Offices of state remain a table.

#### Interconnections

Succession, war (casus belli from claims to titles), houses, regalia, legends, cults (religious titles), territory and de jure maps.

#### Tables and rules

- **Tables:** `title_profiles`, `title_holders`, `de_jure_links`.
- **Rules namespace:** `titles`.

#### Player levers and UI

- **Levers:** create, destroy, grant or usurp a title; redraw de jure territory.
- **UI:** a title tree (an empire down to its counties), a de jure versus de facto map layer, and holder timelines.

---

## Part 5. Conflict

**Current.** A war is two parties. An army is four numbers. A battle is one sum plus a d20. A siege is one roll. A duel is strength + agility + weapon + die. Terrain, weather, season, climate, supply, movement, unit types, commander traits and injuries have no effect. Several WarCause values and the BETRAYAL ending are never written, and `incited_by_son_id` is never set. The audit also found two bugs: `_besieged` can pick the attacker, and idle armies return soldiers that were never subtracted. Both are fixed by 5.1 (levies come out of cohorts).

### 5.1 Army

#### Attributes

**Composition:** an army is a set of **unit stacks** (`army_units` table: army, unit_kind, count, quality, equipment profile, experience, morale, fatigue, wounded count).

`UnitKind` catalogue (`catalog/units.py`, rules namespace `military_units`). Each unit kind has: role, base melee, missile, defence, speed, mass (charge), cost, upkeep, requirements (knowledge level, material, species use, class) and terrain affinities.

| Family | Units |
|---|---|
| Infantry | levy, spearmen, heavy_infantry, shield_wall, pikemen, skirmishers, berserkers, temple_guard |
| Missile | slingers, archers, crossbowmen, horse_archers, javelineers |
| Mounted | light_cavalry, heavy_cavalry, camel_or_beast_riders, chariots |
| Beasts | war_beasts (from domesticated species with the `war` use), bound_beasts (named beasts), sky_mounts (flying species) |
| Engineers | sappers, siege_engines (ram, tower, catapult, trebuchet; material-gated) |
| Magic | war_mages (rite users, Part 8.6), priests (morale, healing), necromancers (raise dead units after battles, doctrine-gated) |
| Naval | galleys, longships, warships, fire_ships, skyships (vessel-gated) |
| Exotic | golems (bound constructs), void_spawn (outer cults), ghost_host (bound spirits) |

**Equipment profile per stack:**

- weapon class mix (blade, spear, axe, blunt, bow, crossbow, sling, polearm, firearm-like if a forbidden branch allows)
- armour type (none, hide, padded, mail, scale, plate, enchanted)
- shield (none, small, large, tower)
- helmet (bool)
- materials (from F3)
- condition 0–100

Equipment is drawn from the community's **weapons and armour stocks** (F3.2). The equipment number at raise time becomes the stock-derived profile.

**Army-level:**

- `commander` and `sub_commanders` (offices)
- `doctrine` (martial style of its people, F5 / 4.1, plus commander traits)
- `supply` (days of food), `supply_line` (path to a friendly settlement)
- `baggage` (camp followers: cohort-linked)
- `location_region_id` (armies move now), `stance` (march, forage, entrench, besiege, garrison, raid, retreat)
- `cohesion` (mixed peoples and mercenaries lower it)
- `war_chest` (pay)
- `disease` (camp sickness)
- `loot` (carried)

**Size** is derived from the sum of stacks. **Levies are subtracted from cohorts** (young adults of the levy class) and returned on disband minus casualties, with the maimed returning into the maimed cohort.

#### Behaviours

1. **Raising.**
   - The polity raises armies by levy law (4.5): the share of adult cohorts by class (warriors and nobles first), the season (harvest halves the levy) and cohesion.
   - Mercenaries are raised by contract (4.3). Holy armies come from cult zeal (crusade).
   - Composition = martial style × available stocks × species mounts × knowledge.
2. **Upkeep.** Per campaign season: food (by size and species metabolism for mounts), pay (from the treasury or war chest), equipment wear. Shortfall → morale −, desertion (by class satisfaction and loyalty), foraging (which damages the local region's farmed land and creates `scar: plundered`), or mutiny.
3. **Movement.** Per campaign season the army moves along the region graph by speed = slowest stack × passability (F2.4) × weather footing × roads × season travel. Mountains and marshes slow it and rivers need fords or bridges. Movement grows the supply line; a long line is vulnerable to raids (light cavalry and bandits).
4. **Attrition.** Per season: cold or heat attrition by armour weight × acclimatisation (F2.3), disease (camp sickness × disease load × sanitation doctrine), starvation and desertion. A winter campaign in mountains with heavy armour bleeds an army without any battle.
5. **Training and experience.** Stacks gain experience from battles and drills (the standing army law). Experience is per stack, so veteran units are distinct. Veteran named mortals add to their stack's quality (their skills, F6).
6. **Morale.** Per stack, from:
   - commander leadership (command capacity, F4.5)
   - pay and supply
   - recent outcomes
   - faith (holy war tenet, priests present, omens: weather and sky events × superstition value)
   - terror (bound beasts and void spawn opposing, minus the army's willpower aggregate)
   - home news (rumours, F11: their city sacked raises both rage and desertion, weighted by kinship value)
7. **Garrisons and standing armies** are persistent armies with the garrison stance. They raise the settlement's order and siege defence and cost upkeep in peacetime.

#### Tables and rules

- **Tables:** `army_units`, `army_profiles` (location, stance, supply, cohesion, war chest, disease, loot), `army_movements` (log per campaign season).
- **Rules namespaces:** `military_units`, `logistics`, `attrition`, `morale`, `levies`.

#### Reference pass (R1, R3)

**Organisation versus strength** (R3). Each stack has three separate pools:

- **strength** (men);
- **organisation** 0–100: formation cohesion, which is lost first in combat and on bad marches, and recovers with rest, leadership and supply;
- **discipline** 0–100: training and drill quality, separate from experience. It sets the organisation loss rate and the recovery speed.

A stack at zero organisation cannot fight and routs even at full strength. Disciplined professional troops hold formation where levies break.

**Ammunition** (R1, R3): missile stacks carry ammunition (arrows, bolts, stones, javelins: commodities made by fletchers and smiths) for [3] volleys per battle phase by default. Resupply comes from baggage. Running dry forces melee or a withdrawal. Sieges consume siege ammunition (stones, fire pots).

**Fatigue and forced march:** each campaign season, the march speed choice (normal, forced) trades distance against fatigue and organisation loss. Fatigue carries into battle (melee ×, morale ×).

**Supply limit per region** (R3): a region feeds at most `logistics.supply_limit` = farmed land × the season's harvest × the local stocks share × roads. Armies above it suffer attrition per season and devastate the land (land-use scar, the local population's opinion −). Large armies must split or depend on supply trains, which shapes strategy.

**Entrenchment and field fortifications:** an army in the entrench stance builds earthworks (palisade, ditch, stakes) over seasons, with the sappers' and engineering skills. This gives a defence multiplier and a charge penalty to attackers. Fortifications persist as place features (6.2 reference pass) after the war.

**Combat engineering:** sappers build pontoons (river crossing without a ford), roads (passability + on the supply line), demolitions (destroy bridges to block pursuit) and mines in sieges.

**Commander skills by area** (R3): fire (missile coordination), shock (melee and charge), manoeuvre (movement, flanking, retreat), siege (assault and engineering), logistics. These are drawn from the F6 tactics, strategy and logistics skills plus traits. Commanders gain **battle traits** (`commander_traits`: aggressive assaulter, defensive genius, cavalry master, winter campaigner, hill fighter, siege expert, reckless, cautious, inspiring, brutal) from their record. The traits shape the tactic weights (5.3 step 2) and terrain bonuses.

**Templates:** a polity stores **army templates** (named compositions: "border legion", "steppe horde"). Raising an army fills a template from stocks and cohorts. The marshal office maintains them. Obsolete templates are upgraded when techniques arrive (8.4 reference pass: obsolescence).

**Training injuries and drills:** standing armies drill per epoch (discipline +, combat skills +), with a small sparring-injury rate (F4 low severity). Patrols reduce bandits on routes in their region (a danger source −).

**Uniforms and identity:** an army's colours and standards (items, 7.1) carry renown. Standard capture is a morale shock and a war-score event (5.3 reference pass).

#### Reference pass 3 (R21)

**War-machine designs:** siege engines, chariots, war wagons, fire-throwers (alchemy) and skyships are **designs** (`designs`: kind, components, materials, mass, crew, performance, designer, lineage). They are built to a design and refitted to new designs. A great engineer's design is a blueprint (8.4 reference pass) that can be stolen. Performance comes from the F23 material physics (a trebuchet's range from its counterweight and frame material).

#### Reference pass 4 (R32)

**Order of battle hierarchy:** armies are organised as a tree:

- army group → army → corps → division → brigade or regiment → stacks.
- Each level has a **headquarters** (`headquarters`: commander, staff skills, location).

**Command range and command points:** a headquarters directs subordinate formations within its **command range** (regions by distance, extended by signal networks and couriers, F21). Each HQ has **command points** per campaign season, from the staff's skills, which are spent on orders (attack, manoeuvre, resupply priority). Formations outside range or beyond the points act on standing orders with penalties.

**Logistics network:**

- **depots** (structures or field depots) hold supplies;
- **transport assets** (wagons, pack animals, river barges, ships, sky-barges) carry them with **throughput** limited by assets, roads and danger;
- **supply points** are consumed per formation per season by size and activity.

The network is a flow problem from production (F24) through depots to formations. Cutting a depot or a river line starves the armies it feeds.

**Operational pauses and culmination:** advancing forces outrun their supply as lines lengthen and losses accumulate. When the supply delivered falls below need and organisation is low, the offensive reaches its **culmination point** and must pause or risk collapse. Commanders with a logistics skill predict culmination better (F22 belief state).

**Theatre allocation:** the marshal (4.6) allocates reserves, transport and new levies between theatres (fronts) by strategy. Allocation errors (from bad beliefs) are a major cause of defeats.

#### Reference pass 6 (S-J)

- **Unit identity and honours:** stacks formed from the same recruitment area or order become **named units** (regiments, companies, warbands) with a history: battle honours on standards (items, 7.1), traditions, a nickname, esprit de corps (a morale modifier that grows with honours and shared survival), and memory (the regiment remembers its massacres and triumphs, F7). Disbanding a famous unit is a reputation event, and reconstituting it from veterans restores part of its esprit.
- **Veterans after war:** polities may grant **land to veterans** (veteran colonies: new settlements in conquered or frontier regions, a strong loyalty to the granting ruler) or pensions (4.5). Veterans' associations (faction kind `veterans`) are a political bloc: they press for pensions, honour the war dead, back martial candidates and may support coups by their old commanders (a personal power base, 4.6 reference pass 4).

### 5.2 Terrain, weather and season in battle

Each battle has a **battlefield**: the region and place where the two armies meet, with its terrain (F2.1 and the place overrides), the weather draw (F2.3) for that campaign season, the time of day (night battles are possible with the ambush doctrine) and an attacker/defender assignment (the defender picks a defensive position when it has scouting advantage).

**Terrain matrix** (`terrain_effects[TerrainKind][UnitFamily]`, tunable):

| Terrain | Effect highlights |
|---|---|
| plain / steppe | cavalry charge ×1.3, horse archers ×1.3, infantry defence ×1.0 |
| forest / jungle | cavalry ×0.5, missile ×0.6, ambush chance +, skirmishers ×1.2 |
| hills | defender ×1.2 (height), missile range +, chariots ×0.6 |
| mountains / high_pass | cavalry ×0.3, defender at a chokepoint ×1.5 (the few hold the many), siege engines cannot move |
| marsh | heavy units ×0.6, disease +, mounted ×0.4 |
| desert | heat attrition, camel-or-beast riders ×1.2, armour weight penalty |
| tundra / ice_sheet | cold attrition, footing −, sky mounts unaffected |
| river_valley | crossing penalty: attacker ×0.7 while crossing, bridges and fords matter |
| coast | naval support possible (fleet in the same sea region adds missile) |
| urban | street fighting: cavalry ×0.4, defenders ×1.3, civilian cohort casualties |
| underground | missile ×0.3, burrowing species ×1.5 |
| crystal_field / flesh / void_shore | world-type exotic modifiers (magic ×, sanity loss, leak) |

**Weather matrix** (`weather_battle_effects`):

| Weather | Effect |
|---|---|
| rain | bows ×0.7, crossbows ×0.85, footing −, fire rites ×0.5 |
| downpour / storm | missile ×0.5, cavalry ×0.7, morale × by superstition, lightning omen (storm-god armies +) |
| fog | missile ×0.4, ambush and surprise ×2, command range ×0.5 |
| snow / blizzard | cold attrition, speed −, missile ×0.7, defender holds |
| heat_wave | armour-heavy units fatigue ×1.5, water need |
| wind | missile drift, fire spread (burning fields), naval |
| eclipse_dark | morale collapse unless the culture reads eclipses as favour (sky event link) |
| magic_storm | rites ×1.5 with backlash ×2, items with high might flare |

**Season:** the campaign suitability of the world's season (F2.2) affects supply (forage availability), levies (harvest), river levels (spring floods block fords) and disease (summer camp fever).

**Sky events:** an active alignment, comet or eclipse is an omen for both sides, read through culture superstition and doctrine.

### 5.3 Battle resolution (phased)

A battle runs in **phases**. Each phase computes stack-versus-stack effects, adjusted by terrain, weather, doctrine and commander.

1. **Scouting and position.** Each side's scouting = light cavalry, skirmishers and the perception and tracking skills of its scouts, + spy network intel (5.10). A winner by margin chooses a stance: defend the best local terrain, ambush (forest, fog, night), or refuse battle (retreat with a pursuit risk).
2. **Commander plan.** Each commander picks a **tactic** from the doctrine's repertoire, weighted by tactics skill, traits (reckless → charge; patient → hold; cunning-tactician → flank or feint) and the terrain read. Tactics: hold_line, frontal_assault, double_envelopment, feigned_retreat, flank_cavalry, missile_attrition, shield_wall, wedge, night_raid, ambush, skirmish_harass, river_defence, siege_assault. Tactics have rock-paper-scissors counters (`tactic_matchups` table) and terrain requirements. A tactic that matches the terrain and counters the enemy gives a phase multiplier; a mismatch gives a penalty.
3. **Missile phase.** Missile stacks fire: hits = count × missile skill × weapon × weather × range (terrain), against armour and shields. Casualties and morale shock follow.
4. **Charge phase.** Mounted and beast stacks charge where the terrain allows: mass × speed × footing against spears and pikes (pikes counter charges). Terror from beasts and golems is applied.
5. **Melee phase** (1–3 rounds, until a rout): each stack's melee × quality × experience × equipment × fatigue × morale × terrain × flanking. Losses are distributed. Morale checks run per stack after each round, with routing contagion between adjacent stacks.
6. **Rites and miracles.** War mages and priests act in any phase (Part 8.6 rites: fireball-like rites, fog-calling, healing, terror, raising the dead). A patron son may intervene through a power (Part 9.1); this replaces the flat patron bonus with a typed intervention that can backfire (the god's attention draws a rival god's opposition).
7. **Pursuit and rout.** A routed side suffers pursuit losses = the pursuer's light cavalry × terrain (forest and mountains shield the fleeing). Captives are taken (5.7). Baggage may be lost (supply and loot).
8. **Aftermath.**
   - Wounded survivors roll their injuries (F4): each stack's wounded count becomes maimed and recovering counts in cohorts, and named mortals get individual injuries.
   - Morale and experience update. War score changes.
   - The battlefield gets `scar: battlefield` (haunted chance from mass death, a later relic site).
   - Remembrance: monuments and laments, as existing.

**Outcome classes:** decisive victory, victory, pyrrhic victory (the winner loses more than [40%]), stalemate, rout, massacre (pursuit ≥ [50%] of the loser).

**Determinism:** every phase draws from `rng("battle.{war}.{season}.{phase}.{stack}")`.

**Battle power for the LLM and the UI:** a summary sheet per battle lists stacks, terrain, weather, tactics, phase results and named casualties. The existing BattleRow gains `terrain`, `weather`, `season`, `tactics_attacker`, `tactics_defender`, `phases` (JSON summary), `casualties_by_kind`, `outcome_class`.

#### Reference pass (R3)

**Frontage and combat width:** each battlefield has a **width** from terrain (open plain wide, pass narrow, forest broken) and weather (fog narrows the effective width). Only stacks within the width fight each phase; the rest are **reserves**. Reserves enter when front stacks rout or are exhausted, or when the commander commits them (a tactics-skill timing roll). Width makes numbers matter differently: at a pass, 300 can hold 30,000 for a time.

**Formation and facing:** stacks have a formation (line, column, wedge, square, loose, shieldwall) and a facing. Flanking requires manoeuvre superiority or terrain (an open flank). Flank and rear attacks multiply damage and organisation loss. Squares counter cavalry and are weak to missiles.

**Morale state ladder** (R3): steady → shaken (penalties) → wavering (no offensive actions) → routing (fleeing, taking pursuit losses) → broken (dispersed, units lost for the campaign). Recovery happens by rallying (commander leadership, standards, priests, fresh reserves). **Suppression:** heavy missile fire pins stacks (no advance) without casualties.

**Command and control:** each commander has a **span of control** (`command.span` = command capacity / [10] stacks). Beyond it, stacks act on their default doctrine with delays.

- Orders travel by messengers within the battle (a delay of one phase over [3] stacks of distance), and can be misunderstood (the sub-commander's intellect and the language barrier, 8.1).
- Sub-commanders show **initiative** by facet: aggressive ones charge unordered.
- The death or wounding of the commander (F4 targeting) causes a command collapse: stacks fall back to default, and a morale shock ripples.

**Spotting and concealment:** stacks have a concealment value (terrain cover, forest, night, fog, camouflage traits). Detection uses the scouts' intuition and focus attributes plus elevation. Undetected stacks can ambush (the first phase has a surprise multiplier) or hold in hiding as a trap reserve.

**Planning bonus:** an attacker that stayed in contact for a season without fighting and holds good intel (F22 confidence) gains a planning bonus for its first phases. Hasty attacks lack it.

**Penetration and hard targets:** missile and melee damage against armour follows F23 material physics. Units are classed **soft** (unarmoured) or **hard** (plate, chitin, stone-skinned, golems) by the share of their coverage. Weapons have a **piercing** value (crossbows, picks, maces, magic). Hard units barely suffer from non-piercing attacks.

**Weapon profiles:** range, rate (volleys per phase), accuracy (skill × weapon), and the volley-against-melee threshold (missiles at close range lose effect when engaged).

**Casualty classes** (R3): killed, wounded (walking, stretcher), captured, missing (stragglers, who rejoin later), deserted. The wounded's fate depends on **field surgeons** (healers attached to the army, the medicine technique and supplies). Without them, mass bleeding and infection turn the wounded into the dead within the season (F23).

**Equipment capture and salvage:** the victor salvages weapons and armour from the field (by quality and condition, F24), becoming better armed. The loser's lost standards, siege engines and baggage are taken.

**Night battles** are allowed with the night-raid tactic: concealment ×, command span ×0.5, and friendly-fire risk (organisation loss). Cultures read night fighting through their ethics (dishonourable in some).

**Terrain micro-features:** place features (walls, ditches, hedgerows, woods edges, ruins, fords) are local features on the battlefield, used by the defending tactic for cover and to anchor flanks.

**Deception:** feints (a tactic: an attacker holds the defender's reserves with a false attack), false campfires (a scouting deception that inflates the believed size, F22) and planted deserters (false intel).

#### Reference pass 4 (R32)

**Lanchester attrition:** within each battle phase, losses between engaged stacks follow Lanchester-type laws chosen by the combat mode:

- **linear law** for melee, where only the front engages: losses proportional to the enemy's engaged strength × effectiveness, bounded by frontage;
- **square law** for massed missiles and magic, where all can engage all: losses proportional to the enemy's *total* strength × effectiveness, so concentration pays quadratically.

The effectiveness coefficients come from all the second-pass factors: quality, discipline, equipment penetration, morale state, terrain, weather and tactics. This gives battle results consistent physics while frontage (5.3 reference pass) decides which law dominates where.

### 5.4 Sieges (multi-season)

- **Siege state** (`sieges` extended): walls (level, material, condition, breaches), garrison, supplies (food days, water source), disease inside and outside, besieger works (circumvallation, mines, towers, ramps), sallies, relief armies expected, treason risk, starvation stage (none → rationing → famine → cannibalism-taboo break, where purity and kinship values are read).
- **Per campaign season:**
  - **Besieger:** chooses blockade, bombard (engines vs walls by material), mine (sappers vs rock type and the soil of the region), assault (ladders and towers vs the breach count), or negotiate (terms).
  - **Defender:** sally, repair walls (masons, stone stock), ration, or seek relief.
  - **Disease** in camp and city (sanitation, water, season).
  - **Starvation** reduces garrison morale and raises the chance of civilian revolt or betrayal (a faction with a grievance opens a gate).
- **Assault:** a battle with an urban/walls terrain profile. Defenders get the wall multiplier, which breaches reduce.
- **Sack:** after a successful assault the victor's doctrine and commander traits decide mercy versus sack. A sack brings loot (treasury, items, relics), atrocities (cohort deaths, maimings, enslavement, burning: districts destroyed), infamy, and memory `conquered_us` with high magnitude.
- **Fix:** the besieged side is always the defender-side settlement. The attacker cannot be besieged in its own war turn unless it is defending in that season.

#### Reference pass (R3)

- **Siege phases** gain:
  - a fort **level** (from structures, with the garrison's skill) that sets the breach difficulty;
  - **artillery** (siege engines and their crews) that accumulate breach points;
  - a **blockade by sea** that cuts the supplies of coastal cities (only a fleet can blockade, 5.5);
  - **sorties to destroy siege works**;
  - **mining and counter-mining** (sapper duels underground, with cave-ins).
- **Leader siege skill** matters.
- **Zone of control:** forts (citadels, forts, walled cities) exert control over adjacent regions. Enemy armies cannot pass a fort's region without besieging it or accepting supply attrition (their supply line is cut), so fortress lines shape invasions.

### 5.5 Naval and sky warfare

- **Fleets** are armies of naval stacks moving through sea regions (water regions on the map). They have weather exposure (storms sink ships by seamanship) and coast support.
- **Naval battles:** boarding (the marines' melee), ramming (the galley mass), missile, fire ships (wind), sky support. Losses become the vessels' condition (Part 7.3).
- **Blockades** cut trade routes over water (Part 6.4), which hurts the target's prices and treasury.
- **Sky warfare** (skyships and sky mounts) ignores terrain, is vulnerable to storms, and is the only counter to flying beasts.

#### Reference pass (R3)

- **Ship classes** have hull (strength), sails or oars (speed, and wind dependence), crew (seamanship), marines (boarding), artillery (missiles, fire), and size class.
- **Weather gauge:** the fleet upwind (from the wind of the weather draw) chooses engagement.
- **Boarding** is resolved as a melee between marines.
- **Naval supremacy** in a sea region (the strongest fleet present) is required to move armies across it safely; without it, transports risk interception.
- **Amphibious landings** bring a heavy penalty to the first battle phases (landing against defenders) unless the beach is uncontested.
- **Air superiority** (flying mounts, sky beasts, skyships) over a region gives scouting dominance (concealment ×), strafing of supply trains and bombardment of sieges. Only flying units or missile stacks with an anti-air capacity (crossbows, mages) contest it.

#### Reference pass 4 (R30)

**Age-of-sail and galley detail** (for sea and sky fleets):

- **Damage locations per ship:** hull (leaks: pumps and crew work against water intake), sails and rigging (speed, manoeuvre), rudder (steering), guns or engines (fire rate), crew by station (gunners, topmen, marines, officers). Each hit is assigned by the shot type (round shot to hull, chain shot to rigging, grapeshot to crew, fire pots to sails) and the angle (a raking fire along the length).
- **Points of sail:** speed by the angle to the wind (the weather draw's wind direction): close-hauled, reaching, running; tacking manoeuvres; being caught in irons. Galleys ignore the wind with oars at a fatigue cost to rowers. Sky-ships use wind and lift.
- **Crew stations and gunnery:** the rate of fire per gun deck from gunners' skill, training (discipline) and casualties. Officers' command (F4.5) affects reloading under fire.
- **Fires and magazine explosions:** fire spreads by deck material (F23), and a magazine explosion destroys the ship. Fire ships exploit this.
- **Prizes:** ships that strike their colours (morale broken) are taken as prizes with prize crews (taken from the victor's crew, lowering its efficiency). Prize money goes to the crew and officers' households (wealth +, recruitment +), which is a motive for aggressive captains.
- **Naval budgets and treaties:** admiralty offices request budgets, compete with army offices in councils and build to designs (7.3). **Naval treaties** (a clause kind `fleet_limit`) cap tonnage per class, with cheating as a scheme.

### 5.6 Duels and single combat

- A duel is a **multi-exchange contest** (3–7 exchanges): each exchange is skill (weapon) × melee capacity × weapon reach (spear outreaches sword in the first exchange) × armour × footing (weather and terrain of the place) × stamina (endurance, fading per exchange) × pain.
- Each exchange may produce **hits with injuries** (F4.3). A duel can end by yield (honour reading), disarm, crippling injury or death. A duel loser is no longer "badly wounded"; they lose an eye, a hand or a leg.
- **Contexts:**
  - war duels (existing chance)
  - honour duels (memory-driven, grievance ≥ threshold, honour culture)
  - trials by combat (law)
  - champion combat (a treaty clause or the doctrine "the gods decide": the war ends by champion)
  - god duels (existing son duels gain divine injuries, Part 9.1)

#### Reference pass (R1, R3)

A duel is resolved by the F23 attack physics, exchange by exchange. Each exchange runs four steps:

1. **Initiative and distance:** reach and speed decide who strikes first. A spear outreaches a sword; once the swordsman closes, the spear loses its advantage.
2. **Choice of action**, by skill, facets, injuries and fatigue: strike (a target part chosen by skill: called shots at a high skill), feint, block (shield skill), parry (weapon skill), dodge (agility and dodge skill), grapple, or a charge with a couched lance when mounted (mass × speed, mount strength).
3. **Wrestling:** grab a limb or the weapon, throw (prone opponent), choke (unconsciousness), joint lock (break: fracture or dislocation), or bite (when desperate, by culture).
4. **Directional defence** (Mount & Blade-style): the defender's read of the attack (intuition and the defender's skill against the attacker's feint skill) decides whether the block or parry meets it.

A downed fighter fights at a penalty and can be finished, with an ethics reading: the mercy value decides whether an enemy is spared. Yielding is accepted according to honour and ethics. Mounted duels add the horse as a target (the mount's injuries) and falls (a crush injury).

Duels produce a **detailed exchange log** for the battle report and the bard, written plainly (G9).

### 5.7 Captives, hostages and slaves

- **Mass captives:** pursuit and sacks take captives as cohorts (`captive_cohorts`: captor, origin community, count, class, condition).
- **Their fates:** ransom by origin, enslavement (law-gated), sacrifice (doctrine-gated), labour, exchange (treaty clause), or release (mercy reading + opinion).
- **Named captives** (existing CaptiveRow) gain these fates:
  - torture for intelligence: an injury, and the captor's spy network learns the origin's war plans → a scouting bonus
  - **hostage-ward:** child heirs raised at the captor's court, with culture drift and memories; a future pro-captor ruler or a vengeful one by traits
  - ransom amount from status and house prestige, paid from the house's or polity's treasury
  - marriage into the captor house (a treaty)
- Executions produce `killed_kin` memories in the captive's house: vendetta (5.9).

#### Reference pass (R1)

- **Abductions:** raiders whose ethics accept abduction take children and spouses in raids (abduction incidents).
  - Abducted children are raised in the captor culture: beliefs and facets are drawn toward it, and memories of their origin fade unless the memory attribute is high.
  - They may become captor soldiers (a stack of abductee warriors with low loyalty to their birth people) or famous turncoats.
  - Their kin hold `abducted_kin` memories and may mount rescue schemes and quests.
- **Slave soldiers** (law and ethics gated): enslaved cohorts form stacks with low morale and high desertion, and may revolt mid-battle when their own people fight on the other side.
- **Prisoner labour and exchanges** are covered. Additionally, a **parole** (an oath not to fight again, 4.8) can release officers. Breaking parole is an oath break.

### 5.8 War, war aims and peace (with the treaty type)

#### War attributes (extended)

- `cause` (now always written: hostility, uprising, tribute_revolt, incited, declared, betrayal, conquest_journey, foreign_god, plus new causes: claim, holy_war, succession, independence, vendetta, resource, raid, liberation, punitive)
- `incited_by_son_id` (now written by the son incite tool)
- `war_aims` per side (`war_aims` table): conquer_region(id), seize_settlement(id), press_claim(claim_id), convert(god), tribute(amount, epochs), vassalise, liberate(id), destroy_cult(id), seize_resource(id), seize_nexus(place), humiliate, revenge(memory_id), loot
- `war_score` per aim (achieved %)
- `war_weariness` per side
- `occupation` (`occupations`: region, occupier, since, control, resistance)
- `coalitions` (multiple sides through allies who are **called to arms** by treaty clauses)
- `fronts` (`campaign_fronts`: region pairs where armies are engaged)

#### War behaviours

1. **Call to arms.** A defensive alliance clause obliges allies to join (honour and opinion decide whether they honour the call; refusal is a broken treaty with memory). Allies now fight with their own armies (solving the passive 40% gap).
2. **Strategy per side per campaign season** (AI by the marshal office plus the ruler's traits): march to an aim target, besiege, defend, raid supply lines or devastate (scorched earth: the land-use scar, enemy food −, own infamy +).
3. **Occupation.** Controlling a region over seasons yields its taxes and levies. Resistance = cohesion × value distance × atrocity memories, which leads to partisan raids and revolts.
4. **War score and weariness.** Weariness grows with casualties (cohort-weighted), taxes, lost trade, occupation of home regions and maimed veterans returning (each maimed veteran adds visible weariness: a people that sees one-armed sons comes home tires of war faster, scaled by the martial value). When weariness > [70], peace pressure rises. A martial-honour culture resists peace while its humiliation pressure is high.
5. **Peace negotiation.** Peace is a **treaty** whose clauses are chosen from achieved war aims and score: cession, tribute (amount, duration), vassalage, conversion rights, hostages, marriage, reparations, demilitarised zone, trade concessions, release of captives, a champion clause for future disputes. The existing endings (victory, conquest, tribute, exhaustion, peace, white peace, betrayal, miracle) map onto treaty templates. **Betrayal is now produced** when an ally breaks a call to arms or a truce mid-war.
6. **Aftermath.**
   - Veterans return to cohorts (with the maimed cohort).
   - War memories and legends; battlefields scarred.
   - War debt (treasury loans) and inflation (Part 6.4).
   - Value drift (F5).
   - Promotions: heroes ennobled, new houses.
   - Refugees (existing).
   - Dark-age knowledge loss (existing), now tied to sacked libraries specifically.

#### Reference pass (R3, R6)

**Casus belli and justification** (R6). A war needs a **casus belli** (`casus_belli`: kind, holder, target, source, expiry):

- claim (on a title, 4.11)
- holy war (doctrine tenet)
- vendetta (killed_kin)
- broken treaty
- insult (an etiquette breach, F21)
- liberation (of co-cultural subjects)
- trade dispute (tolls, embargo)
- debt default
- resource need
- conquest (no casus belli: unjustified)

Fabricating a claim is a scheme (F20) run by the chancellor. An unjustified war gives tyranny (F19), threat (4.6 reference pass) and lower war support.

**War score cost per demand:** each peace clause has a cost in war score, by kind and size (ceding a region costs by its value; vassalisation costs heavily; tribute costs by amount and duration). The winner chooses clauses up to the war score achieved. The loser can accept, or fight on with a weariness cost. Partial peaces with individual coalition members are allowed.

**War support and home front:** war support 0–100 per side = public opinion of the war (F21) + casus belli justification + propaganda − casualties (weighted by the kinship value) − taxes − the visible maimed (F4.5) − occupation of home regions. Low war support lowers levy compliance, raises desertion, triggers anti-war movements (factions, 4.4 reference pass) and pushes the decision rule toward peace.

**Psychological warfare:** terror tactics (sacks, massacres, displayed executions: dread +) lower enemy morale where the enemy's culture fears, and raise resistance and coalition threat where it hardens. Atrocity backlash is computed through ethics (F16) and reputations (F19). Propaganda artworks and criers raise support at home.

**Production for war:** war materiel (weapons, armour, ammunition, siege materiel, ships) is produced by production methods (F24) at workplaces with **efficiency growth**. Sustained production raises efficiency ([+10%] per epoch to a cap), and switching products resets it. Converting civilian production to war production lowers civilian goods and the standard of living (4.1 reference pass).

#### Reference pass 8 (B2)

**Field diplomacy:** commanders act diplomatically in the field within their authority (an office power: a marshal's or general's warrant):

- **Parleys** before battle: demands, insults and bluffs (persuasion and contests, F18). These can avert battle, change belief states (F22: a successful bluff about numbers) or provoke.
- **Local truces** (for the harvest, holy days, the burial of the dead).
- **Surrender terms** for garrisons and cities (honours of war, safe conduct, no sack).
- **Exchanges of prisoners and the dead.**
- **Fraternisation** in long sieges.

Field agreements bind the commander's honour. The polity may repudiate them (an honour and trust cost), and breaking a surrender term is an atrocity reading.

#### Reference pass 9 (A2)

**End of field agreements:** a field agreement ends at its stated term (a truce until the harvest is in), at the end of the war, when the commander is replaced, killed or repudiated by the polity, or when it is broken (an honour and atrocity reading, with memories for both sides). Surrender terms persist as obligations of the victor's polity after the war (treaty clauses, 5.13) and are remembered by the surrendered city.

### 5.9 Vendettas and blood feuds

A blood feud is a set of `killed_kin` memories between houses or communities.

- **Per epoch, the aggrieved side acts by honour × grievance:** raid (a small band fights, producing injuries and deaths), assassinate (intrigue), demand wergild (a treaty: payment ends the feud if the culture allows), or escalate (a war of cause vendetta).
- Every killing adds a new memory to the other side: Loop R.
- **Brakes (Loop B):** wergild law, intermarriage, a common enemy, a priest's mediation (the cult's peace tenet) and decay of memories over generations.
- This replaces the never-decaying feud flag.

### 5.10 Espionage (extended)

- **Spy network** (a typed table, not a bond): owner (polity, faction, cult), target, agents (named mortals + count), depth 0–100, exposure 0–100, cover (merchants, priests, envoys) and a spymaster office.
- **Operations:**
  - steal_knowledge (existing)
  - sabotage (existing, now typed: granary fire, wall weakening, poison wells → disease, arson of districts)
  - assassinate (a target mortal; produces hits)
  - incite (raise unrest; plant a claimant)
  - intel (scouting bonus in battles; reveals war aims; forewarns attacks)
  - blackmail (opinion lever over an office holder, using their hidden conditions or vices)
  - counterfeit (currency debasement)
- **Counter-intelligence:** the target's spymaster skill and order raise exposure; a caught agent becomes a captive with torture options, and their faction's memory drives the relation.

#### Reference pass (R6)

Espionage operations are scheme kinds (F20). Networks gain:

- **identities** (agents under covers, F20);
- **message interception** (F21);
- **deception operations** (planting false beliefs, F22);
- **counter-espionage tasks** by the spymaster (4.6 reference pass).

Captured agents can be **turned** (double agents feeding false intel) or exchanged.

#### Reference pass 3 (R17)

- **Recruitment by motive:** an agent is recruited by money (greed facet, debts), ideology (belief fit with the recruiter's cause), compromise (a hook, F20) or ego (vanity, grievance against the agent's own lord). The motive sets loyalty and the risk of a double cross. Ideological agents are the most reliable and the hardest to turn back.
- **Network topology:** networks are graphs of agents, handlers and cells (`spy_cells`), with dead drops and safe houses (structures or households). Compartmentalisation limits what a captured agent can reveal (only their cell), and flat networks are fast but fragile.
- **Mole hunts:** counter-intelligence investigations (F20 schemes against one's own court) with **false positives**. Paranoid spymasters (facets) accuse the innocent, which yields purges, defections and the loss of loyal officers: Loop R of paranoia.
- **Defectors** cross with secrets (belief-store dumps, F22) and need protection. The defection itself is a reputation event (a traitor at home, a hero abroad).
- **Assassination methods:** blade, poison (by an F30 package), staged accident, disease (a deliberate infection), curse (a rite). **Forensic detection** (a physician's skill, the medicine level and correct theories) decides whether a death is recognised as murder, which sets whether a vendetta, an investigation or a war follows.
- **Divine espionage:** scrying rites, dream intrusions and servitor spies work across distances. Wards and the counter-dominion (F31) block them.

### 5.11 Interconnections of conflict

- War ← economy (stocks of weapons and armour, treasury, food, horses), environment (terrain, weather, season, disease), faith (doctrine, priests, gods), knowledge (unit gates, siege engines, medicine for wounded), species (mounts, war beasts), beasts, magic (rites), law (levy, slavery, pensions), polity (decision, stability), houses (claims), culture (martial style, readings).
- War → bodies (injuries), cohorts (maimed, dead, captive, enslaved), economy (scars on land, looting, war debt), culture (value drift, traditions), faith (holy-war zeal), legitimacy (victory or defeat), houses (prestige, claims), environment (battlefield scars, plundered land), disease (spread by armies), language (captive and hostage culture transfer), knowledge (military knowledge: tactics discovered from victories; a new tactic becomes a `warfare` sub-knowledge).

### 5.12 Tables, rules, levers, UI

- **Tables:** `army_units`, `army_profiles`, `army_movements`, `battlefields` (on BattleRow), `battle_phases`, `campaign_fronts`, `war_aims`, `occupations`, `captive_cohorts`, `spy_networks`, `treaties` (5.13), `treaty_clauses`, `vendettas` (view on memories).
- **Rules namespaces:** `military_units`, `logistics`, `attrition`, `morale`, `terrain_effects`, `weather_battle_effects`, `tactics`, `sieges` (extended), `naval`, `duels`, `captivity`, `war_aims`, `occupation`, `war_weariness`, `peace`, `vendetta`, `espionage` (extended).
- **Levers:**
  - command an army (move, stance, tactic); force a battle at a place
  - set or change the weather for one campaign season (a son power or the Creator's hand)
  - grant victory (existing)
  - impose peace terms; release captives
  - call allies; break a treaty
- **UI:**
  - war room per war: a map with fronts and army positions per campaign season, a timeline scrubber;
  - battle report: phases, terrain and weather badges, tactics and counters, a stack table with losses, named casualties with injuries and links;
  - army card: composition, supply, morale breakdown;
  - siege tracker (walls, supplies, disease);
  - war-weariness gauges;
  - peace-treaty builder.

### 5.13 Treaty (new type)

#### Attributes

- `kind` (peace, truce, alliance_defensive, alliance_offensive, non_aggression, vassalage, tribute, marriage_pact, trade_pact, condotta, guarantee, interworld_treaty: replacing the son tool's ad hoc pacts)
- `parties` (polities, houses, cults, beasts, foreign gods)
- `clauses` (typed: call_to_arms, tribute(amount/commodity/epochs), cession(region), hostage(mortal), marriage(pair), trade_rights(route), tolls_waived, religious_freedom, demilitarised(region), champion_clause, extradition, wergild(amount), non_aggression(epochs))
- `guarantors` (third parties who join if broken)
- `witnessed_by_god` (an oath link, 4.8)
- `duration`, `status` (in force, fulfilled, broken, expired), `breaches` (incidents)

#### Behaviours

- Clauses are executed by the engine each epoch: tribute flows, call-to-arms checks, hostage residence, toll waivers.
- Breach detection: an action against a clause creates a breach incident, triggers guarantors, gives the breaker honour and infamy losses, and causes the witness god's wrath.
- Renewal or expiry.
- Treaties are the source of the TRUCE, ALLY and PAYS_TRIBUTE bonds, which become derived views (decision 73's "typed row is the source of truth" is extended).

#### Interconnections

Diplomacy, war, economy, houses, gods (oath witness), memory (kept and broken).


#### Reference pass (R5, R6)

- **Bad-faith treaties:** a party may sign intending to break the treaty (low truth belief, a deceitful trait, a secret plan). The belief state of the counterparty decides whether it trusts (F22, and trust in F18). A treaty broken in bad faith gives a large honour loss and a lasting trust collapse.
- **Simultaneous multi-party negotiation:** at summits (F25) several parties negotiate at once. Offers and counter-offers are exchanged in rounds. Parties can make **secret side deals** (secrets, F20), and the order of commitments matters. This is resolved by an engine negotiation protocol with typed offers, or driven by LLM agents of the rulers when selected.
- **Research agreements** (R5): a treaty clause shares the research progress of a branch between the parties (8.4 reference pass).
- **Guarantees, non-aggression and defensive pacts** each have typed triggers. A guarantee activates when the guaranteed party is attacked without a casus belli it accepted.

---

## Part 6. Land and economy

### 6.1 Region

**Current.** breadth, danger, fertility and magic, plus a map record (size, coastal, elevation class, top biomes). Biomes are read only by prompts.

#### Attributes

The full environment profile (F2.1), plus:

- land use (F2.5)
- ley lines (F2.6)
- scars
- `control` per polity (4.6)
- `danger` with typed **danger sources** (`region_dangers`: beasts, bandits, monsters, phenomena, disease, terrain hazards: avalanche, quicksand, volcanic). Danger is no longer one number: each source produces typed harm to travellers, settlers and armies.
- `wildness` (inverse of land use)
- `sacredness` (holy sites, burials of saints, god corpses)
- `memory` (what happened here: incidents with a magnitude, used by hauntings and pilgrimages)

#### Behaviours

1. **Environmental update per epoch.**
   - Climate-era shifts change temperature and rainfall, which feed fertility.
   - Erosion and soil change from land use.
   - Rewilding.
   - River course change after major floods (a typed incident; can move settlement water access).
   - Desertification under drought + overgrazing.
   - Volcanic soil enrichment after eruptions (the earthquake disaster gains a volcanic variant in volcanic terrain).
2. **Hazards.** Per sampled year, terrain hazards strike travellers and settlements: avalanches in high passes in winter, floods in river valleys in spring, wildfire in dry forest in summer. They produce injuries (crush, burn, frostbite) and cohort deaths.
3. **Danger actually harms.** Each danger source applies per epoch to settlers (cohort deaths, livestock loss), travellers (journey events), armies (attrition, ambush) and merchants (route throughput). This closes the audit gap that region danger never harms anyone.
4. **Discovery and mapping.** Exploration (existing) now reveals terrain features, mineral layers and sacred sites. Unknown regions have **unknown properties**, so an army marching into an unmapped region suffers navigation risk (the map knowledge of the polity).

#### Interconnections

Everything spatial: war (terrain), economy (yields, land use), disease (load), ecology (habitat), settlement placement, magic (ley), faith (sacred sites), climate.

#### Tables and rules

- **Tables:** `region_environment`, `region_land_use`, `region_dangers`, `region_scars`, `ley_lines`, `region_control`.
- **Rules namespaces:** `terrain`, `land_use`, `hazards`, `regional_danger`.

#### Player levers and UI

- **Levers:** terraform (change terrain or soil), redirect a river, sanctify, salt the earth.
- **UI:** map layers for terrain, soil, temperature, rainfall, land use, danger sources, control, ley lines and scars, each with a legend and time scrubbing (snapshots already exist).

---

#### Reference pass (R1, R2)

**Geology column** (`region_geology`): an ordered stack of layers, each with a rock kind (soil, clay, sand, limestone, sandstone, shale, granite, basalt, marble, obsidian, slate, crystal bedrock, world-type exotic layers: frozen methane, bone, glass), a thickness and its veins (MaterialKind with richness). It is generated from the world's tectonics and volcanism (10.9) and the region's terrain.

- Mining depth (6.3) digs through layers: deeper layers hold rarer veins, and harder rock needs better picks (material hardness, F23).
- Layers set aquifer presence (sandstone and limestone), cave formation (limestone karst) and stone availability for construction (marble enables splendid works; F3 sanctity for some stones).

**Subterranean strata** (`region_underground`):

- aquifers (water access for wells; flooding risk for mines);
- cavern layers 1–3 (each a hidden underworld biome with its own species: fungi forests, blind fauna, cave peoples);
- a magma sea on volcanically active worlds (forge energy, deadly breaches);
- a deep underworld (on worlds with an underworld region; where the existing `is_underworld` and the realm of the dead meet).

Deep mining reaches caverns, which reveals species and peoples and lets beasts out (3.3 reference pass). The existing underworld regions become reachable through the strata.

**Hydrology:**

- Rivers get a flow (from the catchment rainfall of upstream regions and the season), a navigability (from the flow and rapids), salinity (estuaries) and a flood plain share.
- Lakes and seas get salinity and depth.
- Spring floods come from the snowmelt of upstream mountains (F2.2 seasons). Dams and canals (structures) change flows downstream: upstream polities can starve downstream ones (a water dispute is a casus belli).
- River course changes after great floods (6.1 behaviour 1) move the flood plains.

**Region alignment axes** (R1): `goodness` (−100 evil … +100 blessed) and `savagery` (0 tame … 100 savage), as typed region stats.

- **Evil regions** have hostile weather (blood rain, a void-rain analogue as a weather kind), reanimation (the dead rise as bound spirits in corpses: undead beasts), corrupting effect packages (F30) and a raised leak.
- **Blessed regions** have healing springs, gentle weather and the benevolent fauna of the region (unicorn-like species).
- **Savage regions** have larger, more dangerous fauna and faster plant growth, and resist taming.
- The axes are moved by god acts (consecration, curse), atrocities and massacres (evil +), temples and saints (good +), land use (savagery −) and rewilding (savagery +). Where the first pass had scars and phenomena, these axes now give the persistent background on which they act.

**Tectonics:** earthquakes and volcanic eruptions follow the world's tectonic activity (10.9) and the region's position on plate boundaries (generated with the map). Eruptions create volcanic soil and ash weather and can form new land.

#### Reference pass 3 (R8, R12)

- **Divine land manipulation with physics:** sons can raise and lower land, carve or fill valleys, redirect rivers, open springs, call lava or sink coasts. These acts change the region's elevation, hydrology and geology (6.1 reference pass) and are propagated through derived values (passability, fertility, flood plains, defensibility). Downstream regions lose or gain water, and settlements on raised land lose their harbours. Every act has physical consequences, as in From Dust, plus political and religious ones (whose valley did the god drown?).
- **Biome succession:** regions move through successional stages (bare → grassland → shrubland → young forest → old forest; or wetland stages) at rates set by the climate and soil. Fire resets the succession (fire ecology: wildfires in dry seasons, slash-and-burn farming), grazing holds grasslands, and abandonment lets forest return (F2.5 rewilding made explicit).

#### Reference pass 4 (R29)

- **Boserupian intensification:** population pressure (F37 population against capacity) raises the research boosts and the adoption of intensive production methods (irrigation, terraces, rotations, manuring) and labour inputs per land unit. Hunger drives agricultural innovation, and land abundance delays it.
- **Soil nutrients:** soil fertility (F2.1) becomes the readout of nutrient stocks: a fixed-element stock (nitrogen-like), a mineral stock (phosphorus-like), organic matter and salinity.
  - Crops draw stocks by kind.
  - Legumes fix the fixed element.
  - Fallow and manure (livestock, F2.5 grazing) restore it.
  - Irrigation without drainage salinises.
  - Volcanic ash and river floods deposit minerals.
  
  Rotations are production methods (F24). Ancient irrigation civilisations can salt their soils over centuries.
- **Perennials:** orchards, vineyards, olive-like groves and timber plantations have **maturity times** (years to epochs) and long lives. They are long investments that wars can destroy (cutting the groves as a strategy), with recovery taking generations.
- **Commons and enclosure:** common lands (pasture, woods, fisheries) are used by households under customary rules. Overuse brings degradation (the tragedy of the commons) unless the community has commons governance (rules, a council). Enclosure by elites (a law or a mandate) privatises commons: productivity rises for owners and dispossession falls on cottagers (household SoL −, migration to cities, movements).
- **Game reserves:** hunting rights reserved for elites (forest law) protect species (ecology) and create **poaching** (crime, punishment) and resentment.
- **Famine foods and storage culture:** cultures with frequent famine memories develop famine foods (wild plants, bark breads: a production method with health costs) and storage traditions (granaries, preserved foods, communal stores), driven by memory (F33) and generational experience (F12 reference pass 3).

#### Reference pass 5 (S-A OCM 22)

**Fisheries:** water regions and rivers hold **fish stocks** per species (the species model, 3.2), with growth by water temperature (F2.1), nutrients (river discharge and upwelling at currents, 10.7 reference pass 5) and seasons.

- **Effort and gear:** catch = effort (boats, fishers) × gear (lines, nets, weirs, traps) × skill × season.
- Overfishing collapses stocks (logistic dynamics with a collapse threshold). Fishing rights are property (commons or owned waters), and disputes over them are casus belli.
- **Trapping and fowling** are production methods on land species ranges.
- **Marine hunting** (whale-like megafauna) gives large yields with large risks (beasts, storms).

#### Reference pass 8 (B3)

- **Sealing the deep:** breached caverns and strata (6.1 reference pass) can be **sealed** by structures (seal gates, collapsed tunnels, plug walls), rites (warding seals with upkeep) or divine acts. Seals have strength and decay, and beasts and miners test them. Unsealing is a scheme or a mining decision, which makes the deep a managed frontier (the brake of L37).
- **Closed seasons and protected waters:** fishery and hunting **closures** (law kinds: closed seasons, protected breeding grounds, catch quotas, gear bans) protect stocks. They are enforced by wardens (an office and a coverage) and evaded by poachers. Closures are customary (commons governance) or legal (the brake of L69).

### 6.2 Place

**Current.** danger, fertility and mystery.

#### Attributes

- `place_kind` (typed): mountain, peak, pass, forest, grove, river, ford, lake, spring, cave, cavern_system, ruin, island, swamp, well, valley, cliff, volcano, crater, battlefield, burial_ground, lair, nexus, shrine_site, god_corpse (existing engine kind), mine_site, harbour_site, crossroads
- local environment overrides (F2.1)
- `mystery` (existing; now it drives discovery chances of hidden resources, rites, relics or knowledge)
- `sacredness`
- `chokepoint`, `height_advantage`, `water_source`
- `hidden_features` (`place_secrets`: a typed hidden resource, buried relic, sealed spirit, lost knowledge or entrance to the underworld, revealed by exploration, a seer's prophecy or a dig)

#### Behaviours

- **Discovery of secrets** by explorers (perception skill), seers (wisdom) and miners (deep mining can release a sealed thing, a typed incident that releases a spirit or a beast, or opens a phenomenon).
- **Pilgrimage destination** (sacredness).
- **Battle site preference:** chokepoints and passes attract battles in campaign strategy.
- **Lair** for beasts.

#### Tables and rules

- **Tables:** `place_profiles`, `place_secrets`.
- **Rules namespace:** `places`.

#### Player levers and UI

- **Levers:** place a secret; reveal it.
- **UI:** a place card with features and secrets (player-visible).

---

#### Reference pass (R1, R2)

- **Sites with structure:** places of kind tower, vault, lair, hamlet, monastery, camp, shrine, fortress, cave_complex and dungeon have **rooms** (`site_rooms`: kind, contents: items, spirits, beasts, traps) and an **ownership history** (holders over time). Heroes' quests and raids walk room by room in a summary resolution: each room is a challenge roll (trap, guardian, puzzle, hazard) with its injuries and loot. Necromancer towers, beast lairs and vaults of the gods become explorable sites.
- **Excavations** (R2 anomalies): ruins, previous-creation sites, crashed vessels and god-corpse places carry **excavation chains** (`excavations`: stages 1–5, each with a skill and technique requirement (lore, engineering, spellcraft), risks (curse packages, released spirits, collapse) and finds (artifacts, books, lost techniques for reverse engineering (8.4), titles' regalia, precursor maps of routes)).
- **Battlefield and fortification features** persist (5.1 reference pass) as place features: old earthworks, mass graves (haunted), and fields of salvage.

#### Reference pass 3 (R8, R10)

- **Magic sites:** places with typed magical properties (a source of a magic resource per path or school, a bonus to rites of a school, a ward, a gateway). They are hidden until found by **searching** (explorers or mages with the matching school skill, 6.2 secrets). Sites yield magic resources each epoch to their holder, and are war aims and cult holy sites.
- **Thrones of power:** a small number per world (`thrones.per_world` [3]) of mythic sites that, when held by a god's dominion or claimed by its worshippers, give the god typed advantages: dominion spread, essence, standing across the world. Holding a majority of a world's thrones counts toward **ascension** (a son's goal, 9.1). This adds a territorial contest between gods that mortals fight on their behalf.

#### Reference pass 4 (R31)

**Expeditions into sites and wilds** (Darkest Dungeon, Kenshi and The Long Dark-style):

- An expedition is a party (mortals with roles: scout, guide, healer, fighter, scholar, porter) going into a site, a wilderness, an underworld stratum or a mythic realm. It carries **provisions, light sources (torches, lamps, magic light), tools (picks, ropes, keys) and medicine** as an inventory.
- **Progress:** each room or leg consumes provisions and light. **Darkness** raises danger, surprise and stress. **Exposure** (cold, wet, hunger, fatigue) applies F23 conditions (frostbite, hypothermia, fatigue). **Camping** restores fatigue and stress at a provision cost and with a night-ambush risk.
- **Stress afflictions and virtues:** party members gain stress from horrors, injuries and darkness. Past a threshold they roll an **affliction** (paranoid, hopeless, selfish, abusive: it hurts others' stress) or a **virtue** (courageous, focused, stalwart: it helps), by facets and conviction (F17 reference pass 3).
- **Quirks:** places and events leave quirks (typed minor traits): "afraid of the deep", "knows the old tunnels", "loves the sea", "eats anything". They persist after return and change later behaviour.
- **Party roles** set the expedition's capacities (scouting, healing, carrying, fighting, reading inscriptions). Missing roles show as risks.

#### Reference pass 7 (A5 Dewey 560)

**Fossils and deep time:** the geology column (6.1 reference pass) holds **fossil beds**: remains of extinct species (the extinction records of 3.2), of megafauna and beasts, of previous creations (existing) and, on old worlds, of extinct peoples.

- Fossils are found by mining, erosion after floods and quakes, and excavations.
- Interpretations follow cultures' theories (8.4b): dragon bones in legends (8.2 manifestation weight +), relics of giants for cults, evidence of deep time for scholars (a theory of the world's age; conflicts with creation doctrines).
- Fossil materials (ivory, amber with inclusions) are luxuries.

### 6.3 Resource

**Current.** abundance, value, might and mechanics. There is no quantity, extraction or refining. The commodity tags for food and goods are never read.

#### Attributes

- `material` (MaterialKind, F3) or `commodity` (for non-material resources: grain fields, fisheries, pasture)
- `reserve` (an absolute quantity in units, replacing abundance as the source of truth; abundance becomes reserve / initial reserve × 100)
- `richness` (yield per worker)
- `regeneration` (renewable vs finite: a forest regrows, an ore vein does not)
- `extraction_difficulty` (depth, hardness, hazard: mines have collapse risk, which produces crush injuries and cohort deaths)
- `required_knowledge` (level per branch)
- `quality` 0–100 (high-quality iron gives better weapons)
- `byproducts` (silver from lead; slag pollution; the land-use scar)
- `mechanics` (existing: decaying, addictive, sentient, depletion_price, fixed, sacred; each mechanic now has typed parameters)
- `owner` (polity, house, faction, cult, community)
- `workers` (from labour allocation)

#### Behaviours

1. **Extraction.** Output = workers × richness × skill (mining, logging, fishing) × tools quality × knowledge level × season (logging in winter, fishing in summer). Reserve depletes. Hazards roll per sampled year (mine collapse; logging accidents produce injuries).
2. **Refining chains** (`production_chains` catalog): ore → metal (needs fuel: timber or coal, plus smiths) → tools, weapons, armour; hide → leather → armour; grain → bread (feeds cohorts); grapes → wine (luxury); reagents → potions (medicine); stone → building stock; timber → ships and siege engines.
   Each chain step is a structure (forge, tannery, mill, shipyard, alchemist) plus workers plus inputs. A bottleneck anywhere propagates. For example, deforestation removes fuel → iron output falls → weapons stock falls → army equipment falls → war outcomes change. That is a five-subsystem chain made of typed steps.
3. **Resource conflict.** Scarce strategic resources (iron, horses, reagents, star metal) become war aims (seize_resource) and trade-route chokepoints. This replaces the "identical resource sets → rivalry war" rule with a demand-driven one.
4. **Sacred and sentient resources** keep their existing mechanics with typed parameters. A sentient resource's demands become negotiations through treaties.

#### Tables and rules

- **Tables:** `resource_profiles`, `resource_workers`, `production_chains` (catalog), `production_runs` (per-epoch log).
- **Rules namespaces:** `extraction`, `refining`, `mining_hazards`.

#### Player levers and UI

- **Levers:** set a reserve, change the owner, reveal a deposit.
- **UI:** a production chain graph per polity, with bottlenecks highlighted.

---

#### Reference pass (R1, R4)

**Ownership and profit** (R4): every production site and resource has an **owner** (a household, house, faction, cult, polity, or a chartered company's shareholders).

- Revenue minus wages, inputs, upkeep and taxes gives the **profit**, which goes to the owner's treasury. A share of it goes into the investment pool (4.3 reference pass).
- This creates class wealth dynamics: landlords grow rich from farms, and guilds from workshops.
- It also gives a motive for politics: owners lobby for tariffs, wars to seize resources, low taxes on their sector, and against laws that threaten their methods.

**Mines and cave-ins:** mining depth versus the rock's support (the geology layer, 6.1 reference pass) and engineering gives a cave-in risk per sampled year. Cave-ins cause crush injuries, deaths, sealed mines and sometimes broken-open caverns (beasts).

**Food chain and spoilage:** grain → flour (mill) → bread (bakery); meat → preserved meat (salt, smoke); fruit → wine or brew; milk → cheese. Each step is a production method with spoilage at the raw stage (F24). **Drink** is a need for some peoples (the dwarven-style drink need) and a luxury for others.

#### Reference pass 5 (S-A OCM 38)

**Chemical industries:** production methods (F24) for dyes (by plant, shellfish and mineral sources; colour preferences, F15, make some dyes luxury monopolies), soap (hygiene: disease load −), mordants, tanning agents, fertilisers (nutrients, 6.1 reference pass 4), pharmaceuticals (medicine commodity by technique and theory, 8.4b), incendiaries, and explosives (forbidden or late techniques; siege mining, mining productivity, accidents). Each has inputs, pollution and hazards (F24, F23).

### 6.4 Markets, money and trade routes

#### Markets

- Each settlement with a market district is a **market node** holding prices for all 16 commodity kinds (F3.2).
- Prices respond to supply and demand (stocks against consumption), transport cost (route distance × danger) and tariffs.
- The two overlapping trade-flow systems the audit found (`society_economy.py:507` and `market.py:127`) are merged into one **route-based flow**: per trade route, a capacity-limited flow from low-price to high-price nodes. Price convergence follows the flow.

#### Money

- `currencies` table: issuer polity, metal (F3), purity 0–100, supply, trust 0–100.
- Polities with trade knowledge mint coins. Debasement (purity ↓) raises the treasury short-term but causes inflation and lowers trust: merchants' opinion falls and trade with that currency drops.
- **Inflation:** a large hoard looted from a beast or temple floods the luxury price index, and silver-backed prices fall.
- Debts (`OWES` bonds, existing) are denominated in a currency and an amount, and are tied to the debt law (4.5).
- **Banks:** merchant-guild factions with treasury lend to polities (war loans). Defaults bring bank opinion −, future credit ×, and possibly bank collapse (an incident that hits merchant satisfaction).

#### Trade route (new type)

**Attributes:**

- `path` (an ordered region list along roads, rivers or sea)
- `mode` (road, river, sea, caravan, sky)
- `length`, `capacity` (volume per epoch, raised by roads, bridges, harbours and caravanserais)
- `goods` (the flow by commodity, computed)
- `tolls` (per controller region)
- `danger` (from the regions' danger sources: bandits, beasts, weather; seasonal for sea routes)
- `controller` (the polity or faction holding chokepoints)
- `waystations` (structures)
- `age`, `renown` (a famous road becomes a legend), `carried_culture` (rumour and diffusion weight)

**Behaviours:**

- **Formation:** sustained flow between two markets over [2] epochs along a passable path forms a named route. It decays without traffic.
- **Throughput:** flow = min(capacity, price-gap-driven demand) × (1 − danger loss) × season. Losses go to bandits (faction treasury) or the sea (shipwreck incidents with cohort deaths).
- **Diffusion:** knowledge, culture, language loans, religion (missionaries) and disease travel by flow volume, replacing the bond-based diffusion in `culture_exchange.py` with route-weighted diffusion.
- **War:** routes become war aims. Blockades (fleets, armies at chokepoints) cut throughput. Merchant factions push for peace when their routes suffer.
- **Toll revenue** funds polities; high tolls divert traffic to alternative paths (Loop B).

#### Interconnections

Settlements, factions, polities, war, disease, culture, language, faith, knowledge, regions (danger), structures (roads, bridges).

#### Tables and rules

- **Tables:** `market_prices`, `trade_route_profiles`, `trade_flows`, `currencies`, `loans`.
- **Rules namespaces:** `markets`, `money`, `trade_routes`, `banking`, `tolls`.

#### Player levers and UI

- **Levers:** open or close a route; set tolls; debase; forgive debt; inject a hoard.
- **UI:**
  - a trade-flow map (animated route volumes);
  - a price board per market with history sparklines;
  - currency cards (purity, trust);
  - a debts ledger.


#### Reference pass (R4)

- **Market access:** for each production site, the share of output that reaches its market = internal logistics (4.3 reference pass) × route capacity × danger. The rest is consumed locally or wasted. Remote mines with no road sell only a fraction of their output, which makes infrastructure valuable.
- **Tariffs, subsidies and embargoes:** polity policies per commodity and per partner. Tariffs raise revenue and the prices for consumers and protect local producers (whose owners lobby for them). Subsidies cost the treasury and support a sector. Embargoes cut flows by treaty or decree, and smuggling rises with the price gap (black markets).
- **Black markets:** illegal commodities (drugs, void materials, slaves where banned, forbidden books) trade through bandit and smuggler factions at a premium. Crime rises with their volume.
- **Credit:**
  - Lenders set **interest rates** by the borrower's credit rating (repayment history, treasury, stability) and the money supply.
  - **Bankruptcy states** run normal → strained → default → restructuring: a default triggers debt laws and clauses, bank losses and possibly a war of cause `debt_default`.
  - Polities can hold **reserves** (gold and silver stocks) that back currency trust.
- **Boom and bust:** merchants with the greed facet **speculate**: they buy commodities expected to rise (their belief state, F22) and hoard them in famines. The resulting price spikes raise unrest, and the subsequent busts ruin merchants (bankruptcy incidents). Cycles emerge from these behaviours rather than from a scripted cycle.
- **Price elasticity:** demand per commodity responds to price by elasticity (low for staples, high for luxuries) and to income (SoL, 4.1 reference pass).
- **Arbitrage agents:** merchant households and guild caravans choose routes by the believed price gaps (F22), so markets converge where merchants are informed, and stay apart where information is slow.
- **Economic indicators** per polity and world: output (a GDP analogue), price index, trade balance, treasury balance, debt ratio, unemployment and SoL by class. They are stored per epoch for charts (J.9).

#### Reference pass 3 (R14)

- **Caravans and convoys** (`caravans`: owner, route, cargo (commodities and quality), animals and vehicles, guards (a small stack), passengers (pilgrims, migrants, missionaries, carriers of disease), schedule (a season), status). Trade route flows (6.4) are carried by caravans: route capacity is the sum of caravans. Caravans are raided (bandits, beasts, enemy armies), escorted (by guards or a treaty clause), delayed by weather and lost in storms at sea. Their arrival brings goods, news, art forms and diseases as typed cargo.
- **Transport fleets:** pack animals, wagons and ships age and need maintenance and replacement (capital costs to their owners). A merchant house's fleet age is a strategic asset.
- **Cargo-specific transport:** perishables need speed or preservation (salted, iced, magically kept). Livestock walks (slow, grazing along the way). Bulk goods (grain, stone, timber) go by water where possible (cost per distance much lower). This sets the economic geography: river and sea networks dominate bulk trade.
- **Ports and warehouses:** harbour capacity (berths, cranes, depth) limits throughput. Warehouses hold stocks for speculation (6.4 reference pass) and for siege reserves.
- **Market manipulation:** merchant houses with large stocks can **corner** a commodity (buy out the local supply, raise prices) or **dump** (flood a rival's market). Guild monopolies, mandates and laws against forestalling and engrossing counter them.

#### Reference pass 4 (R34, R4)

- **A world-defining resource** (Dune-style): the engine can designate (at genesis, or by a son's act) a **keystone resource** of a world. It is a resource whose production is tied to a unique ecology (a species life cycle, a phenomenon), whose consumption is needed by an institution (navigation, longevity, prescience, a rite) and whose control is sacred to a cult. Its flows then couple ecology (harvesting harms the producers), economy (a monopoly), religion (a holy substance) and politics (control of it is the main war aim). Coupling rules are typed so that disturbing one domain shakes the others.
- **Brands and producer reputation:** workshops, shipyards, vineyards and smiths' houses earn **brand** reputation from quality history (F24) and renowned products (7.1). Brands raise prices and demand, can be counterfeited (forgery, 7.4 reference pass 4) and pass with the workshop by inheritance or sale.

#### Reference pass 5 (S-A OCM 42, 45)

- **Insurance and risk pooling:** merchant guilds, banks and mutual societies insure cargoes (6.4 reference pass 3 caravans and ships), houses (fire) and lives (burial societies). Premiums are set by the insurers' beliefs about risk (F22). Large losses can ruin insurers (a cascade to banks). Insurance changes behaviour: insured merchants take riskier routes (moral hazard), so piracy and storm losses shift between private and pooled.
- **Incorporeal property:** rights to songs, dances and stories (some cultures own them by clan), rites (8.6) and their performance, designs (8.4 reference pass blueprints), names and titles (heraldry, 4.8 reference pass 3), trademarks (brands, 6.4 reference pass 4) and market privileges. They are inherited, sold, licensed, stolen or infringed, with disputes in courts or feuds. Performing another clan's song is an insult.

#### Reference pass 6 (S-F, S-G)

- **Saving and time preference:** households split income between consumption and saving by the patience facet, beliefs (wealth), security (war, banditry, a predatory ruler's short horizon, 4.6 reference pass 4) and institutions (banks, a safe property registry). Savings become hoards (buried treasure: lost when owners die, found by later diggers), bank deposits (lent on) or investment (the investment pool). Insecure societies hoard, and secure ones invest, which is a growth coupling.
- **Exchange rates and money changers:** each currency's rate to others follows its purity, trust, money supply and trade balance. Money changers (merchants with the accounting skill) profit on spreads at markets and fairs. **Bills of exchange** (a banking technique) let merchants pay across distance without moving coin, which lowers transport risk and creates credit networks.
- **Vertical integration and putting-out:** merchant houses can own several steps of a production chain (6.3) to secure supply and margins. In the **putting-out system**, merchants supply raw materials to rural households who produce at home (spinning, weaving), which gives a proto-industrial phase before workshops and factories (F44).
- **Tourism:** leisure travel to wonders, baths, sacred sights, famous battlefields and exotic cities, by the wealthy (SoL above the luxury tier). Visitors bring income (inns, guides), rumours and diseases, and spread fame (renown of structures, prestige of cities).
- **Containers:** goods move and are stored in typed containers (amphorae, barrels, sacks, crates, jars, chests), each with capacity, breakage, spoilage protection (sealed jars against vermin), cost and reuse. Container production (coopers, potters) is part of chains. Container shortages bottleneck trade, and container marks (potters' stamps) become archaeological evidence for excavations (6.2 reference pass).

---

## Part 7. Made things

### 7.1 Item

**Current.** damage, protection, might and curse. The category is not stored; crowns, mirrors and seals have no role; quality is prose.

#### Attributes

- `item_class` (typed; drives which mechanics apply):

| Group | Classes |
|---|---|
| Weapons | blade, longblade, axe, spear, polearm, mace, bow, crossbow, sling, throwing, staff |
| Protection | armour (type), shield, helmet |
| Regalia and status | crown, sceptre, seal, ring, standard (banner) |
| Religious | holy_relic, idol, prayer_book |
| Knowledge | book, scroll, map, astrolabe |
| Craft and use | tool, instrument (music), mirror, vessel_object (cup, urn), prosthesis, key |
| Other | jewel, currency (existing engine kind) |

- `material` (F3) and secondary materials
- `quality` 0–100: crafter skill × material workability × tools × knowledge level. The words crude, sturdy and masterwork become derived bands.
- `condition` 0–100 (wear, rust by material decay and climate, repairs)
- `damage_type` and `reach` (weapons)
- `coverage` and `weight` (armour)
- `enchantments` (`item_enchantments`: a typed rite effect with strength, bounded by material conductivity)
- `curse` (existing; now typed curse kinds: bloodthirst, misfortune, wasting, madness, betrayal)
- `value` (from material, quality, renown and enchantments)
- `renown` 0–100 (fame of the object)
- `provenance` (`item_history`: maker, owners in order, deeds: kills, battles, coronations, losses, theft, burial)
- `status` flags: heirloom (house), relic (cult), regalia (polity office), legendary (existing)
- `bound_spirit` (existing binding, now typed)
- `prosthesis_for` (F4.5)

#### Behaviours

1. **Crafting** (mortal tools and engine forges): quality from the crafter. Materials from stocks. Enchanting needs a rite. Masterworks create renown for the crafter and a chance of a named item (the record is promoted to an entity; ordinary items remain stock counts).
2. **Wear and repair.** Condition falls with use (battles and duels per exchange), material decay and climate (humidity rusts iron). Repair needs a smith and materials. A broken item loses its function, and a broken legendary sword is a quest hook (a thread).
3. **Renown accrual from deeds.** Kills by a weapon, coronations with a crown, victories under a standard. Renown above [60] turns the item into a **symbol**: its possession gives legitimacy (regalia) or morale (standard) to its holder. Its loss is a typed humiliation incident for the polity, and its capture is a war aim.
4. **Regalia and legitimacy.** A ruler holding the polity's regalia gets legitimacy +. Usurpers seek the crown. A lost crown lowers legitimacy until a new crown gains renown.
5. **Relics.** Saint bones (from mortal death, 3.1) and god corpse fragments are relics. They give pilgrimage, healing miracles (a chance-based condition cure, raising faith) and cult zeal. Relic theft raids happen.
6. **Books and maps.** Books carry knowledge records (`book_contents`: knowledge id, fidelity) and are a vector for knowledge transfer without a teacher, which strengthens the dark-age survival role. Maps carry region knowledge, which shortens army navigation risk and journey times.
7. **Curses.** Typed curses act through modifiers and conditions on bearers (bloodthirst: the wrathful trait plus duel seeking; betrayal: an opinion − toward lieges).
8. **Inheritance** follows house heirloom rules, not just "OWNS passes to a DESCENDS_FROM child".

#### Interconnections

War (equipment profile; materials), legitimacy (regalia), faith (relics), knowledge (books), houses (heirlooms), economy (value, materials), body (prostheses), magic (enchantment), spirits (binding).

#### Tables and rules

- **Tables:** `item_profiles`, `item_history`, `item_enchantments`, `book_contents`.
- **Rules namespaces:** `crafting`, `item_wear`, `item_renown`, `regalia`, `relics`.

#### Player levers and UI

- **Levers:** forge, enchant, break, transfer.
- **UI:** an item card with provenance timeline, condition bar, enchantments and a "symbol of" badge.

---

#### Reference pass (R1)

- **Quality grades** follow the F24 tiers (poor → artifact), with a **maker's mark** (the maker mortal and their house emblem) on every crafted item.
- **Decorations** (`item_decorations`: kind (studded, encrusted, inlaid, engraved, painted, banded, menacing spikes, runed), material, quality, and **an image**):
  - Engraved and painted images **depict** a subject: an event collection (F10 reference pass), a figure, a god, a beast, an art form motif.
  - They raise the item's value and renown, and the subject's memory (remembrance).
  - A shield showing the victory at Varn keeps that battle alive in the culture.
- **Artifacts:** items from inspirations (F17 masterwork fever) are artifacts. They have a unique name, the highest quality, often several decorations, and possibly an enchantment. Artifacts are coveted: there is a theft and quest motive, and nobles with greed demand them. Their **history** (7.1 provenance) tends to be long.
- **Prostheses, crutches and splints** are item classes with materials (F4.5, F23).
- **Clothing:** item class clothes (with material, quality and colour) meets comfort and status needs (F14) and carries culture-specific dress codes (sumptuary law, 4.5). Fine clothing is a luxury good (F3.2).
- **Furniture and household goods** (beds, tables, chests, statues) furnish dwellings (F29), raising room quality.

#### Reference pass 5 (S-A OCM 39, 40)

- **Optics:** lenses (glass, crystal materials, F3) through the techniques of glassworking and optics give:
  - **spectacles** (an assistive item that restores the sight function lost to age, F4.5, which extends scholars' and craftsmen's careers);
  - magnifiers (fine craft quality, engraving);
  - telescopes (astronomy research, naval scouting, eclipse and impact prediction, 10.9);
  - burning glasses.
  
  Other assistive items join prostheses and crutches (hearing horns, canes, reading frames).
- **Timekeeping devices:** sundials, water clocks, sand glasses, candle clocks, mechanical clocks (gears and metallurgy), astronomical clocks (wonders). Public clocks (structures) raise **coordination**: labour discipline (output +, satisfaction − for some classes), synchronised military operations (command delay −), navigation (longitude-like position at sea needs a precise clock, 7.3) and calendar precision (F1).

#### Reference pass 6 (S-F)

- **Writing media:** books, letters, records and inscriptions have a **medium** (clay tablet, wax tablet, bark, palm leaf, papyrus, parchment, paper, metal plate, stone, knotted cord). The medium sets durability (by climate: papyrus rots in wet regions, clay survives fire and is even baked by it), cost (parchment needs livestock skins), copy speed (paper and printing) and portability. Archives' survival through disasters follows their media, so what history remembers depends on what it was written on (F33).
- **Locks and security:** locks, keys, seals, vaults, guards and traps defend property (stores, treasuries, archives, relics). Theft schemes (F20) contend against lock quality (craft and the lockwork technique), seals (tampering evidence) and guards. Master locksmiths and thieves form a skill rivalry, and a vault's security is a structure property.

### 7.2 Structure

**Current.** splendor, durability and function. The engine builds three kinds; the function role comes from a regex; there is no upkeep or staff.

#### Attributes

- `structure_kind` (typed, replacing the regex):

| Group | Kinds |
|---|---|
| Faith | temple, shrine, monastery, necropolis |
| Knowledge | library, school, observatory, academy, hospital |
| Defence | wall, gate, tower, citadel, watchtower, fort |
| Civic | palace, court, prison |
| Commerce | market, harbour, warehouse, granary, caravanserai, bank |
| Production | forge, mill, tannery, mine, quarry, shipyard, workshop, alchemist_lab |
| Infrastructure | road, bridge, aqueduct, sewer, canal, irrigation, dam |
| Memory and wonders | monument, tomb, arena, theatre, wonder |
| Cosmic | gate (cosmic, existing), cosmic_archive (existing) |

- `level`
- `capacity` (granary tons, library volumes, garrison size, hospital beds)
- `staff_required` and `staff` (workers allocated from cohorts; priests, scribes, guards)
- `upkeep` (commodities and treasury per epoch)
- `material` (stone, wood, …: durability and fire resistance)
- `condition` (replaces durability as the source of truth; durability becomes the max)
- `construction_state` (planned, building with progress %, complete, damaged, ruined)
- `builder` (polity, faction, cult, patron mortal), `architect` (mortal)
- `dedicated_son_id` (the audit found it unused; now it gives patron fame, faith and an existence anchor option)
- `on_ley_line` (F2.6)
- `aesthetic` (from the builder people's culture)
- `splendor` (from aesthetic fit, materials and the architect's skill)

#### Behaviours

1. **Construction takes time.** Progress per epoch = workers × engineering skill × materials delivered / cost. Wonders take generations: a multi-epoch project that survives rulers or is abandoned (a half-built wonder becomes a ruin with legends).
2. **Function by kind** (typed effects replacing the regex):
   - **Granaries** raise storage and siege supply.
   - **Aqueducts and sewers** raise sanitation.
   - **Hospitals** cut infection and death from wounds (F4.4) and give healer XP.
   - **Schools** give literacy and education quality.
   - **Libraries** hold books (knowledge preserved; they finally get a build effect).
   - **Observatories** give astronomy, calendars and an omen-interpretation bonus (eclipse morale shock reduced).
   - **Roads and bridges** raise passability and route capacity.
   - **Walls** give a siege multiplier by level and material.
   - **Prisons** raise order and give punishment capacity.
   - **Arenas** give public mood; gladiatorial duels give renown and injuries to fighters.
   - **Mills** give a grain refining multiplier.
   - **Forges** let refining chains run.
3. **Upkeep and decay.** Unpaid upkeep lowers condition. Condition < [40] gives function ×condition. Disasters (an earthquake by material), sieges and fires damage structures. Neglect after abandonment turns them into ruins (existing).
4. **Staffing.** No staff means no function. Plagues that kill scribes close libraries in effect, even when the building stands.
5. **Prestige.** Splendor feeds settlement prestige, polity legitimacy (palaces) and wonder status (existing threshold).

#### Interconnections

Every subsystem through function: economy (production, storage), war (walls, forts), health (hospitals, sanitation), knowledge (libraries, schools), faith (temples), polity (palace, court), culture (theatres, arenas).

#### Tables and rules

- **Tables:** `structure_profiles`, `structure_staff`, `constructions`.
- **Rules namespaces:** `construction`, `structure_functions`, `upkeep`.

#### Player levers and UI

- **Levers:** commission, fund, finish now, damage, staff.
- **UI:** a settlement plan (4.2) with structures; construction progress bars; a function breakdown.

---

#### Reference pass (R1, R2, R5)

- **Hospitals in detail:** beds, healers by skill, supplies (cloth, thread, splints, medicine, soap), and treatment capacity per season. Traction benches and crutch stocks support locomotion recovery. Without supplies, treatments fail (F23 treatment steps).
- **Dwelling structures** (F29): manors, townhouses and palaces have rooms whose quality comes from the furnishings and the structure's splendour. Nobles' demands (4.6 reference pass) refer to them.
- **Cosmic-scale structures (megastructures, R2):** star-cage (an essence collector around a star, which dims the star and angers sun cults), orbital ring, world-bridge (the existing divine bridge generalised), void lighthouse (route safety), and a planetary engine (moves a world's orbit: a 10.9 orbit change). Each is gated by techniques of the cosmic branches plus essence and generations of labour. Wonders at a world scale.
- **Unique projects** (R5): structures of kind `wonder` and `cosmic` have **uniqueness** (only one per world or cosmos), a **technique gate** (8.4) and a **race**: several polities may build at once, the first to finish wins, and the others lose their investment except a salvage share. This is a classic wonder competition with diplomatic consequences (envy, 7.2 behaviour 5).
- **Memorial slabs and tombs** put ghosts to rest (3.3 reference pass).
- **Towers of necromancers and mages** (3.3a reference pass) are structure kinds with rooms (6.2 reference pass).

#### Reference pass 6 (S-F)

**Water-lifting devices:** shadufs, waterwheels (norias), Archimedes-like screws, chain pumps and later steam pumps (F44) are production methods and structures. They gate **irrigation** of land above the river (terrace farming, 6.1 reference pass 4), **drainage of deep mines** (mining depth against aquifers, 6.1 reference pass) and urban water supply. A mine without pumps floods at the aquifer layer, and a terrace system without lifting devices depends on rain.

#### Reference pass 7 (A5 Dewey 060, 710)

- **Museums and collections:** cabinets of curiosities, treasuries of temples, royal collections and museums (a structure kind `museum`) gather artifacts, relics, fossils, art and specimens.
  - Collections give prestige (court grandeur, 4.6 reference pass), research boosts (specimens for natural philosophy, artifacts for reverse engineering, 8.4 reference pass) and tourism (6.4 reference pass 6).
  - They are targets for looting in sacks, and their acquisition is a motive for expeditions and schemes.
  - Restitution of looted collections is a treaty clause and a reconciliation act.
- **Designed landscapes:** gardens (pleasure gardens, physic gardens with medicinal plants, monastery gardens), parks, hunting parks (game reserves, 6.1 reference pass 4), sacred groves (genius loci, 3.3 reference pass 4) and cemeteries as gardens. They are structures with a planted species mix, an aesthetic (the art form of landscape style, 7.5) and upkeep. Effects:
  - beauty and nature needs (F14);
  - healers' supply (physic gardens);
  - prestige;
  - a refuge for species (biodiversity);
  - dominion and standing for nature gods.

### 7.3 Vessel

**Current.** speed, range, crew, armour and strangeness. Strangeness is never read.

#### Attributes

- `hull_class` (raft, boat, galley, longship, cog, carrack, warship, light_sailer, bone_hull, generation_ship, skyship, living_ship)
- `material`, `condition`, `cargo_capacity`, `crew` (existing; now a cohort reference: sailors' seamanship skill aggregate)
- `armament` (rams, missiles, siege engines, rites)
- `seaworthiness` (storm survival)
- `captain` (a mortal)
- `owner`
- `home_port`
- `renown`
- `strangeness` (existing; now it drives route possibilities, see below)

#### Behaviours

- **Voyages** (journeys, existing) and trade-route sea legs. Each leg rolls weather: a storm × seaworthiness × seamanship gives damage, crew loss or a wreck.
- **Naval combat** (5.5).
- **Repair** at shipyards.
- **Strangeness** unlocks exotic routes (dream, river of the dead) and raises the chance of ghost-ship transformation (existing engine kind) and outer attention.
- Ship **renown** creates legends ("the ship that sailed the river of the dead").

#### Tables and rules

- **Tables:** `vessel_profiles`.
- **Rules namespace:** `seafaring`.

---

#### Reference pass (R2)

- **Fuel and supply:** vessels carry provisions (food and water days per crew) and, for cosmic methods, the cosmos's travel resource (the existing `travel_resource` becomes a commodity with a quantity: mined, refined and traded). The **jump range** per voyage leg is limited by the stock. Running short means strandings, rationing, cannibalism-taboo breaks (ethics), mutiny and ghost-ship origins.
- **Crew morale and discipline** use the army models (5.1 reference pass) at a smaller scale, with mutiny as a revolt kind.
- **Navigation:** the navigator's skill and maps (7.1 books and maps) against the route's danger and the weather; a lost vessel drifts to unknown regions or worlds (discovery).

#### Reference pass 3 (R21)

- **Component design:** vessels are built to **designs** (5.1 reference pass 3) from components, under a mass and volume budget:
  - hull (material, size), propulsion (oars, sails, a mount harness, a sky-sail, a void-sail, a divine engine), holds (cargo and provisions), quarters (crew and passenger capacity), armour (by section), weapons (rams, engines, mage stations), wards (rites bound to the hull), and navigation equipment (astrolabe and maps).
  - Performance (speed, range, seaworthiness, cargo, armament) is derived from the components.
- **Lineage and refits:** designs evolve as new techniques arrive. Ships are refitted (time and cost) or kept obsolete. A famous shipwright's design lineage is a blueprint line.
- **Component wear and failure:** each component has wear and a failure chance per voyage leg (a broken mast in a storm, a failed ward in the void). Maintenance at shipyards resets wear, and neglect leads to wrecks.

#### Reference pass 6 (S-F)

**Navigation instruments:** the compass (functional only where the world has a magnetosphere, 10.9; useless or misleading near magnetic anomalies and some phenomena), the astrolabe and quadrant (latitude from stars: needs astronomy), the log-line (speed), charts (maps, 8.4 reference pass) and a sea clock (longitude, 7.1 reference pass 5). Navigation accuracy = instruments × the navigator's skill × the weather visibility. It sets the risk of getting lost, the safe distance from shore and the possibility of open-ocean routes.

### 7.4 Artwork

**Current.** renown and influence. Influence is never read outside its own phase; "written" is a regex.

#### Attributes

- `medium` (typed: song, epic_poem, play, statue, fresco, tapestry, mosaic, book, dance, music, carving, architecture_ornament)
- `performed` vs `physical`
- `author` (a mortal), `patron`
- `subject` (bond to the incident, mortal, god or legend it portrays)
- `message` (a value vector delta: what the artwork argues for, e.g. martial glory or mourning of war)
- `quality`, `renown` (existing), `influence` (existing; now read)
- `location`, `copies` (for books and songs: spread count)
- `language` (for verbal works)

#### Behaviours

1. **Influence matters.** Artworks apply value pressure (F5) to the communities that hold or perform them, by influence × renown. A war-mourning epic pushes martial values down, which raises war weariness in later wars (Loop B on militarism). A glorifying statue of a conqueror pushes the conqueror's people toward martial values, while the conquered read it as humiliation, keeping resistance alive.
2. **Commemoration of subjects.** A portrayed mortal's renown is preserved after death (memory strength for spirits, 3.3). A portrayed god gains fame and existence (existing).
3. **Propaganda.** Polities commission artworks to raise legitimacy, at a cost of treasury and artists.
4. **Censorship and destruction.** Iconoclasm (cult zeal) and conquest destroy physical works. Performed works survive as long as performers survive (cohort-linked).
5. **Translation.** Works cross language barriers when translated (needs a scribe with both languages), which spreads their message.

#### Tables and rules

- **Tables:** `artwork_profiles`.
- **Rules namespaces:** `art` (extended), `propaganda`.


#### Reference pass (R1, R7)

- **Performance troupes:** faction kind `troupe` (scale band) with performers (mortals with musicality, kinaesthetic sense and performance skills). Troupes tour along trade routes and perform artworks in art forms at gatherings (F25). They earn income and spread art forms, legends and rumours (F11 carriers), and are sometimes spies (F20 identities).
- **Written works:** books (7.1) have an author, a topic (a knowledge branch, theory, ideology, legend, law code, chronicle) and a style (an art form for literature). Scholars write books when the inspiration or research insight triggers, or when commissioned by patrons. Copies are made by scribes (the printing technique multiplies them).
- **Depictions:** artworks and decorations (7.1 reference pass) have a **subject** typed by an event collection, figure or god. Depictions extend remembrance and reputation, so a culture's art is part of its memory.

#### Reference pass 4 (R36)

- **Art markets:** artworks and artifacts have prices set by renown, the artist's reputation, the canon status, provenance and collectors' preferences (F15). **Collectors** (nobles, merchants, temples) compete in auctions at gatherings. **Patronage competition** among courts draws artists (scholar and artist migration), raising a court's grandeur (4.6 reference pass).
- **Forgery:** artworks, relics, documents and branded goods can be forged (a scheme kind; skill against the experts' connoisseurship). Discovered forgeries damage reputations and provenance chains. Undiscovered ones enter the canon, and forged relics still get pilgrims. The truth is player-visible.
- **Canon formation:** each culture's **canon** is the set of works treated as classics: selected by renown over time, institutions (academies, temples), copying (books), teaching (schools) and art movements. Canonical works shape art forms and values (F5) across generations, and canon wars (movements fighting over the canon) are culture conflicts.

#### Reference pass 5 (S-A OCM 52)

**Games of skill and chance as cultural artifacts:** board games, dice games, card-like games, ball games and wrestling styles are typed records with origin cultures, rules (strategy, chance, physical) and spread (contact, routes). Strategy games train the tactics and strategy skills of those who play them (a small XP source for nobles and officers). Chance games carry gambling (household wealth flows, debts, crime). Ball games are sports (4.3 reference pass 4). Games travel with diasporas and are adopted by preference.

### 7.5 Art form (new type)

#### Attributes

- `discipline`: music, poetry, dance, theatre, painting, sculpture, architecture_style, textile, calligraphy
- `structure` (typed and discipline-specific):
  - music: scale, rhythm, voices, instruments (item classes and materials);
  - poetry: metre, rhyme, stanza, line length, subject conventions;
  - dance: tempo, group size, movement focus;
  - visual styles: palette, motif set, materials.
- `origin_culture`, `founder` (a mortal)
- `difficulty` (the skill needed to master it)
- `prestige` (cultural esteem)
- `sacred_use` (liturgical or not)
- `occasion_kinds` (which gatherings use it)
- `parent_forms` (fusions)
- `practitioners`

#### Behaviours

- **Invention:** a creative mortal with high skill and an inspiration (F17) may invent a form, especially at cultural contact (a fusion of two forms) or after formative events (a lament form after a plague).
- **Spread** through performances, troupes, books (notation), trade routes and conquest. Adoption follows the receiving culture's preferences (F15) and value fit.
- **Mastery:** performers learn forms as sub-skills. Artworks made in a form gain quality from mastery and renown from the form's prestige in the audience culture.
- **Decline** when practitioners die out and no notation survives (scripts and books).
- **Ritual role:** sacred forms are part of cult rites (8.6) and traditions (8.3). A heretical form can be banned (law, censorship), and suppressing a people's forms is a humiliation (resistance +).

#### Interconnections

Artwork quality and renown, traditions and gatherings, preferences, language (poetry depends on its language's phonology: metre from syllable structure, a link to `language_profiles`), cults (liturgy), trade routes, identity and cohesion.

#### Tables and rules

- **Tables:** `art_form_profiles`, `art_form_practitioners`.
- **Rules namespace:** `art_forms`.

#### Player levers and UI

- **Levers:** invent a form, ban it, spread it.
- **UI:** an art-form card (structure and lineage tree of fusions) and the cultures that practise it.

#### Reference pass 8 (B3)

**Fashion and novelty cycles:** art forms, styles, dress, cuisine and names follow **novelty dynamics**. Adoption rises with prestige (the trendsetters: courts, great artists), saturates, then the form becomes common and its prestige falls (distinction-seeking elites move on). Old forms can return as revivals. Each form has a `novelty` stock that drains with ubiquity and recovers with rarity. This is the specified brake of L33, and it gives cultures visible style periods.

---

## Part 8. Culture, knowledge and the supernatural

### 8.1 Language

**Current.** spread, complexity and sacredness, plus phonology, a lexicon, dialects and contact. There are no barrier effects, and the writing system is inert beyond having a script.

#### Attributes

- `family_tree` (existing parent link)
- `intelligibility` (a computed matrix between languages from lexicon overlap and phonology similarity; already used for naming, now mechanical)
- `prestige` 0–100 (speakers' polity power, literature: artworks, sacred status)
- `registers` (court, common, liturgical, trade)
- `writing_system` (existing; now typed effects)
- `literacy_cost` (alphabet low, syllabary medium, logographic high, knot or notch special)
- `standardisation` 0–100 (grammar books, schools)
- `speaker_cohorts` (per community: L1, L2, liturgical-only)

#### Behaviours

1. **Barriers.** Every cross-community interaction reads intelligibility:
   - diplomacy (opinion gain ×; treaty misunderstanding chance: a clause misread is a breach incident)
   - trade (transaction cost; fewer flows)
   - conversion (preaching ×)
   - rumour fidelity (F11)
   - army cohesion (mixed-language armies: command penalty)
   - assimilation speed
2. **Interpreters and lingua francas.** Mortals with language skills are interpreters (dragomans) and remove barrier penalties. A high-prestige language becomes a lingua franca along trade routes (an L2 spread).
3. **Writing effects by system.** Literacy cost limits literacy growth, which limits administration capacity (polity size), knowledge diffusion and record keeping (rumour fidelity of written records). A logographic script empowers a scribe caste (scribe class satisfaction and power). Alphabet adoption raises literacy and weakens the scribe caste's monopoly, which creates faction tension.
4. **Prestige dynamics.** Conquerors' languages gain prestige, but a conquered people with a prestigious literature can culturally conquer its conquerors (prestige-weighted shift).
5. **Liturgical languages** survive as dead L1 but living liturgy (the existing dead-language flag gains a liturgical exception).

#### Tables and rules

- **Tables:** `language_intelligibility` (cache), `language_registers`, `speaker_cohorts`.
- **Rules namespace:** `language` (extended), `interpreters`.

#### Player levers and UI

- **UI:** intelligibility matrix heatmap, prestige ranking and a speakers map.

---

#### Reference pass (R1, R6)

- **Names have meanings:** every generated name (persons, places, titles, art forms, artifacts) is composed from lexicon morphemes with a recorded **meaning** (`name_meanings`: name, language, gloss, morphemes). Translating a name into another language gives its foreign form (exonyms). Epithets come from deeds and are composed in the namer's language ("the Silver-Handed"). The existing Namer gains a semantic layer: names are chosen to fit the bearer's deeds, house or place features.
- **Diplomatic language:** the court register (8.1) is used in treaties, and translation quality sets the misreading chance (F21).
- **Poetry and phonology:** art forms (7.5) of poetry read the phonology (syllable structure, stress) of their language, so forms do not transfer cleanly between languages (a translation quality penalty).

#### Reference pass 3 (R11)

- **Sound-change engine:** each language holds an ordered list of **sound changes** (`sound_changes`: rule, environment, epoch, cause: contact, prestige, migration, random drift). Each epoch, a language may acquire a change, at a rate set by its isolation and contact. Lexicon forms are re-derived from proto-forms by applying the changes in order. Dialects and daughter languages share early changes and diverge later, so **cognates** emerge and comparative reconstruction is possible (scholars can reconstruct proto-words: a research topic). Place names fossilise older forms (names change more slowly).
- **Grammar typology** (`language_grammar`: word order, morphology type (isolating, agglutinative, fusional, polysynthetic), cases, noun classes or genders, evidentiality, honorific levels, number systems). It sets translation difficulty between languages (the misreading chance, F21), naming patterns (compounds in agglutinative tongues), poetry (art forms) and how easily the language takes loans. Grammar also changes under contact (simplification in creoles, convergence in language areas).
- **Semantic drift and taboo replacement:** words shift meaning over time (lexeme meaning history). Words for feared or sacred things (a beast, death, a god's name) are replaced by euphemisms, driven by fear and taboo traditions. The old word survives in poetry and the sacred register.
- **Script evolution:** scripts are records with lineage (`scripts`: type, parent, epoch, signs). The chain runs pictographic → logographic → mixed → syllabary → abjad → alphabet, plus knot and notch systems. Changes happen by reform, by simplification through heavy use (merchants) and by **borrowing** with adaptation (a borrowed script gains signs for new sounds).
- **Decipherment as a process:** dead scripts (DECIPHERABLE) are studied by scholars over seasons. Progress depends on corpus size (surviving inscriptions and books), the existence of **bilingual texts** (a find in excavations), related living languages (cognates) and the analytical ability and linguistics skill of the scholars. Partial decipherment yields partial knowledge, and errors propagate (a mistranslation becomes a theory or a legend).
- **Loan adaptation:** loanwords are adapted to the borrowing language's phonology (the sound inventory and syllable rules), so loans look native and their origin is traceable.
- **Pidgins:** sustained contact without a shared language (trade posts, plantations, mixed armies) first produces a **pidgin** (a reduced contact language with no native speakers). It becomes a creole (the existing rule) when children acquire it.
- **Language policy:** polities and cults can set official and liturgical languages, suppress languages (schools, laws: cohesion − and resistance + among speakers) and sponsor revivals (the existing revival flag, now with a mechanism).
- **Non-vocal languages:** peoples whose biology lacks speech organs use sign, scent, colour-pattern or telepathic languages (the language profile gains a `modality`). Modality changes barriers (telepathic languages cross all barriers between telepaths and none with others), writing (some modalities cannot be written) and espionage (scent languages leave traces).
- **Divine tongues:** each son has a sacred language (the language of its true name), learnable through revelation. Its words are rite components (8.6 reference pass 3: spoken components).

#### Reference pass 8 (B1)

- **Sign languages:** communities with many deaf members (a heritable deafness allele in a closed population, F26), monastic silence vows, hunting cultures that need silence, or many tongueless or mute members (punishment, injury, F4) develop **sign languages** (a language modality, 8.1 reference pass 3) with their own lexicon, grammar and spread, independent of the spoken language.
- **Sociolects:** within a language, social groups (classes, castes, guilds, courts, criminals with their cant, sailors) develop **sociolects**: lexical and phonological variants that mark identity (F43 salience), carry prestige or stigma, serve as secret codes (thieves' cant) and can become dialects or new languages when groups separate.

#### Reference pass 9 (A2)

**Sociolect fading:** a sociolect fades when its group dissolves, assimilates or loses its distinctness (identity salience falls, F43), when standardisation (schools, printing) levels it, or when its speakers die out. Fragments survive as loanwords and slang in the standard language. A sociolect becomes a dialect or language only when its group separates geographically or socially for generations (8.1 dialect rules).

### 8.2 Legend

**Current.** spread and category; manifestation exists. There is no credence and no behavioural effect.

#### Attributes

- `credence` 0–100 (how much it is believed)
- `distortion` 0–100 (distance from the source incident)
- `source_incident_id` (the true event, if any)
- `moral` (a value vector delta: the lesson)
- `archetype` (`LegendArchetype`: hero_quest, monster, trickster, creation, flood, betrayal, lost_paradise, chosen_one, cursed_line, return_of_the_king, haunted_place)
- `tellers` (communities, bards)
- `fixed_in` (artwork: freezes distortion)

#### Behaviours

1. **Telling and distortion.** Each retelling epoch, distortion rises by [3] × (1 − literacy), and the distortion direction follows the teller culture's values: a legend of a defeat becomes a story of betrayal in an honour culture. Credence rises with tellers and with confirming events.
2. **Behavioural effect.** Credence × moral applies value pressure to tellers.
   - A "return of the king" legend raises the claim strength of a pretender who matches it, and lowers resistance to a usurper who claims the role.
   - A "cursed line" legend lowers a house's prestige.
   - A "haunted place" legend raises a region's danger in settlers' minds (migration avoidance) even with no spirit there.
3. **Manifestation** (existing) is gated by credence instead of spread.
4. **Prophetic resonance.** Prophecies that match a legend archetype gain certainty (8.7).

#### Tables and rules

- **Tables:** `legend_profiles`.
- **Rules namespace:** `belief` (extended).

---

#### Reference pass (R1)

- **Legends depict event collections:** a legend's source is an event collection (F10 reference pass), and its distortion is measured against the collection's true participants and outcomes. Legends can swap heroes and villains, merge two figures or move the place. Player-visible "truth versus telling" comparisons come for free.
- **Legend cycles:** related legends form a cycle (`legend_cycles`: shared hero, place or archetype). Cycles reinforce credence among themselves and are fixed into epics (art forms).

#### Reference pass 3 (R9)

**Heroquests** (King of Dragon Pass-style, with the simulated world's own myths):

- A **heroquest** is an event collection in which a mortal (or a party) enters a mythic realm: the god's palace world, the realm of the dead, a dream world, or a place where the myth happened (a sacred site in heroquest state).
- The quest **re-enacts a legend** (8.2) of a god's deed, step by step. Each step is a challenge (a skill, passion, conviction or faith check) defined by the legend's archetype and content.
- **Fidelity to the legend's version** matters. Following the version the people believes gives a bonus. **Deviation** can win a different boon and **changes the legend** (the people's version updates when the quester returns: a myth rewritten by a hero).
- **Boons:** blessings (F30), a magical item, a rite (8.6), a lifted curse, a renewed land (dominion strength, F31), the god's favour (standing) or knowledge of a true name.
- **Failure:** the quester's soul is trapped (the body comatose until rescued by another quest), they return injured or mad, or the myth breaks: the legend's credence collapses and the people's cohesion falls.
- **Interference:** rival gods' servitors and outer beings can interfere in heroquests, since the mythic realm is contested ground.
- **Group heroquests:** a community's rite (8.6) can send many participants, each a role in the myth, with a shared outcome.

### 8.3 Tradition

**Current.** spread and rigidity, with no effect on its celebrants.

#### Attributes

- `tradition_kind` (typed): festival, fast, funeral_rite, initiation, marriage_rite, coming_of_age, taboo, offering, pilgrimage, hospitality_law, duel_custom, mourning, harvest_rite, war_dance, scar_rite, ancestor_feast
- `calendar_slot` (a season or holy day, F2.2)
- `cost` (commodities consumed: feasts eat grain, offerings burn incense)
- `effects` (typed modifiers on celebrants: cohesion +, piety +, class satisfaction, value pressure, fertility (marriage rites), martial (war dances), spirit placation (ancestor feasts))
- `taboo_target` (an ActKind or commodity it forbids)
- `participation` 0–100
- `origin_incident_id` (for commemorations)

#### Behaviours

1. **Celebration effects** per epoch on the participating communities: these finally give traditions an effect.
   - A **festival** costs food and raises cohesion and satisfaction; in a famine year, skipping it lowers cohesion.
   - A **taboo** blocks an act and gives an infamy reading to violators. A pork taboo removes livestock from consumption; a taboo against fighting in winter shapes campaign seasons.
   - A **funeral rite** decides spirit routing (3.3).
   - An **initiation or scar rite** adds a ritual injury (a facial scar, a removed finger) with a culture-positive presence reading, which interacts with F4.5.
   - A **hospitality law** raises safety for travellers (route danger −) and makes guest-killing a grave infamy.
2. **Emergence from incidents.** Notable years, great victories, plagues and miracles create commemorative traditions (generalising the existing remembrance phase).
3. **Spread and adoption** via contact (existing) now uses value fit.
4. **Conflict.** Rigid traditions resist laws and ideologies that contradict them (unrest), and force syncretism in conversion: a new religion absorbs the festival.

#### Tables and rules

- **Tables:** `tradition_profiles`, `tradition_effects`, `tradition_participation`.
- **Rules namespace:** `traditions`.

---

#### Reference pass (R7)

- **Personal events and family rites** (comings of age, weddings, funerals, name-givings) are traditions with household gatherings (F25) whose costs are paid by households (F29). Poor households skipping rites suffer shame thoughts and status loss.
- **Calendar festivals** synchronise gatherings across a people's settlements (a season slot), which raises cohesion and also the spread of disease at crowded festivals.

### 8.4 Knowledge

**Current.** One shared level per record (so every knower shares it), 18 branches, prerequisites for 8 of them, and spread that has no effect.

#### Attributes

- The shared record level remains as the **frontier** (the best known). Each holder now has `holder_levels` (holder, knowledge, level, practitioners). A people can know metallurgy at level 2 while another is at 5.
- A **tech graph**: every branch has a typed prerequisite set (AND/OR) of branch levels, covering all 18 branches plus **sub-techniques** (`techniques` catalog: e.g. under warfare: phalanx_drill, horse_archery, siegecraft, fortification, logistics, tactics_of_X; under medicine: herbalism, surgery, amputation, prosthetics, quarantine, inoculation; under agriculture: irrigation, crop_rotation, terracing, plough, selective_breeding; under metallurgy: bronze, iron, steel, skysteel; under architecture: arch, dome, aqueduct, fortress; under writing: alphabet, paper, printing; under astronomy: calendar, navigation_stars, eclipse_prediction). Techniques are what unit kinds, structures, refining chains and treatments require.
- `secrecy` (guild or cult held: does not diffuse through trade unless stolen)
- `practitioners` (a skill cohort size)
- `carriers` (books, archives, masters)

#### Behaviours

1. **Research pressure.** Deepening chance per holder = scholars' scholarship × institutions (schools, academies, libraries) × literacy × **need** (war raises warfare research; endemic disease raises medicine; famine raises agriculture) × contact with higher-level holders.
2. **Diffusion** per route volume (6.4), per teacher bonds and books; blocked by secrecy unless spies steal it (5.10).
3. **Loss.** Practitioners die (plague, war) → holder level falls if no books and no masters remain. The dark ages become the result of losing practitioners, books and institutions, which generalises the existing rule with an actual mechanism.
4. **Spread finally matters:** spread is the share of the world's communities with holder level ≥ 1, read by the doom clock (enlightenment relief), the creator's interest (a knowledge passion), and son goals.
5. **Unlocks** are typed requirements: units, structures, chains, rites, treatments and tiers read techniques, not the raw branch level.

#### Tables and rules

- **Tables:** `holder_levels`, `techniques` (catalog), `holder_techniques`, `research_progress`.
- **Rules namespaces:** `knowledge` (extended), `research`, `tech_graph`.

#### Player levers and UI

- **UI:** a tech graph per holder (known, frontier, available, locked), with a diffusion map.

---

#### Reference pass (R1, R4, R5)

**Two trees.** The tech graph gains a **civic tree** (branch family `civics`). Its sub-techniques:

| Area | Techniques |
|---|---|
| Governance | oral_law, written_law, codified_law, bureaucracy, census, postal_service, diplomatic_corps, standing_army_admin |
| Economy | coinage, banking, double_entry, joint_stock, insurance |
| Society | guilds, universities, hospitals_institution, printing_press_institution |
| Religion | organised_clergy, monasticism, theology_schools |
| Philosophy | logic, natural_philosophy, empiricism, humanism-like_ideals |

Civic techniques gate governments (4.6), offices, tax types, laws, estates' privileges and ideologies.

**Institutions that spread geographically** (EU4-style, R5): civic techniques flagged `institution` (universities, printing, banking, bureaucracy) appear at an origin (where conditions are met: wealth, scholars, trade volume) and then **spread regionally**: adjacency, trade route volume and shared culture or religion raise the spread chance. Embracing an institution costs treasury, and refusing it raises the cost of all research (a catch-up penalty that grows over time).

**Boosts by doing** (Civ-style eurekas and inspirations): each technique has **triggers** that add progress (a typed incident kind or state):

| Technique | Trigger |
|---|---|
| sailing | coastal fishing at scale |
| fortification | survived a siege |
| medicine | survived an epidemic |
| astronomy | an eclipse observed from an observatory |
| law | a great trial |
| banking | a great debt |
| horse archery | a steppe culture with tamed horses at war |

Triggers make history drive tech.

**Catch-up:** research cost falls by `research.catch_up_pct` [10] per known neighbour holder (route or border), down to a floor. Knowledge also leaks through captives, refugees (scholars among them) and conquered libraries.

**Card-draw options:** each epoch, every researching holder draws N options (`research.options` [3]) from the available techniques, weighted by need and boosts. The holder's patron scholars choose one; or the LLM ruler agent chooses when selected (a typed tool `choose_research`). This makes research paths diverge between peoples.

**Great people:** points accumulate per field from scholars, artists, generals, prophets, engineers, merchants and explorers (the outputs of the relevant skills and institutions). Past a threshold a **great person** is promoted (F12) with high skill and a field-specific action (a great work, a breakthrough, a doctrine, a campaign, a wonder rush, a trade monopoly, a discovery). Great people are the engine's channel for "the one who changed everything".

**Eras and era score:** a world's era advances with the share of techniques of the next era known by leading holders. Each polity accumulates an **era score** from historic deeds (firsts: first circumnavigation, first university; great victories; wonders). A high score gives a golden age with typed bonuses; a low one a dark age with stability penalties and a chance of a **heroic recovery** (a resurgence bonus when the score is recovered). This extends the existing golden and dark ages from per-community flags to realm-scale eras.

**Specialised scholars:** scholars have expertise fields (skills), so research in their field is faster. Patronage: a ruler or noble who funds scholars (stipends) gains research and prestige, and a court scholar office exists.

**Dangerous techniques:** techniques flagged `dangerous` (forbidden, void living, biomancy at high levels, star-caging) have **incident risks** on discovery and use (leak, a released beast, plague, a backlash phenomenon) and **ethics stances** (F16) that can turn the world against the researcher.

**Experiment accidents:** research in alchemy, engineering and magic rolls accident risks: fires, explosions (injuries), poisoning (an F30 package), summoning gone wrong.

**Obsolescence:** when a better technique for a role exists (unit kinds, methods, structures), the older ones lose relative value, and upgrades (refitting stacks, rebuilding workshops) cost resources. Obsolete things remain in the world until upgraded.

**Reverse engineering:** found artifacts and excavation finds (6.2 reference pass) can be studied (the scholars' analytical ability and the matching branch) to gain progress toward their techniques, sometimes from far eras (with a dangerous-technique risk).

**Printing and copying economics:** copying a book costs scribe labour. Printing (a technique) makes copies cheap, so literacy rises, rumour fidelity rises (written records) and ideologies spread quickly. Printing also produces **censorship** demand: censored books are a law target, a black-market good (6.4 reference pass) and a heresy vector.

**Research agreements** between polities (a treaty clause, 5.13 reference pass) share the progress of a branch.

**Tech-driven social change:** some techniques shift beliefs on adoption (printing → knowledge +; banking → wealth +; gunpowder-like forbidden arms → martial honour − as the knight loses meaning) and the class structure (the scribe class grows with bureaucracy; artisans fall with mills). This is technology as a social force.

**Geography and cartography:** a polity's map knowledge (`map_knowledge`: the regions known at each fidelity) improves through exploration, trade and the cartography technique. It affects army navigation (5.1), journey safety (7.3) and claims (de jure maps are drawn by cartographers).

**Era-locked capabilities** require several branches together. Examples: blue-water navigation needs astronomy, shipbuilding and cartography; a university needs writing, scholarship and organised clergy or wealth.

**Blueprints:** designs (for vessels, siege engines, structures, artifacts' patterns) are knowledge items, stored in books and on masters. They can be stolen (schemes, spies), traded and licensed (guild charters).

#### Reference pass 4 (R37)

- **Examinations:** polities with the civic technique `examinations` recruit officials by **examination** (gatherings at set intervals). Candidates (mortals with education) are scored on skills (law, writing, lore, the canon). Passing grants **credentials** and office eligibility. This shifts elite recruitment from birth to merit, and feeds elite overproduction when credentials outgrow offices (F37 counter-elites).
- **Credentials and degrees** from universities and academies (master, doctor, a temple ordination) are typed status markers read by careers, role norms and reputation.
- **Academic freedom:** institutions have a freedom level (laws, the cult's orthodoxy, a ruler's mandate). Freedom raises research and theory competition. Its suppression lowers both and drives **scholar migration** toward freer patrons, carrying knowledge (brain drain and gain).
- **Schools of thought:** masters and disciples form intellectual lineages (`school_lineages`: a theory or ideology, a founder, a chain of masters). Lineages give a teaching bonus, have rivalries and preserve heterodox knowledge through persecutions.

#### Reference pass 5 (S-A OCM 80)

**Number systems and numeracy:** each culture has a **number system** (base: 10, 12, 20, 60 or a world-specific base; positional or additive; with or without a zero concept, a civic and mathematical technique) and a **numeracy** level per cohort. Numeracy sets the quality of accounting (corruption detection, tax efficiency), engineering (structure quality), astronomy (prediction accuracy) and commerce (merchant arbitrage). A zero and positional notation are research milestones that boost mathematics-dependent techniques. Numerology (luck beliefs, F42) reads numbers through the culture's system.

### 8.4b Theory (new type)

#### Attributes

- `domain`: medicine, cosmology, matter, life, mind, magic, history, society
- `claims`: typed propositions such as "disease spreads by bad air", "the world is a disk", "souls are reborn", "the stars are gods"
- `correctness` 0–100 (hidden truth, set at creation from the world's real mechanics: the engine knows what is actually true in this cosmos)
- `explanatory_power` (how many observations it accounts for)
- `adherents` (scholars, institutions, cults)
- `founding_texts` (books)
- `rival_theories`

#### Behaviours

1. **Effects through techniques:** techniques depend on theories. A treatment derived from a false medical theory has a harmful or no effect. A navigation technique based on a correct cosmology works better. Rites that rely on a correct magic theory are more reliable.
2. **Anomalies:** observations that contradict a theory accumulate. For example, an eclipse predicted wrongly, or a quarantine that works against the humours theory.
3. **Paradigm shift:** when anomalies exceed the theory's explanatory power and a rival exists with adherents, a **paradigm contest** runs among scholars. The outcome depends on evidence (correctness), institutional support (universities, cults), and the facets of the leading scholars (stubbornness, curiosity). The winner becomes the orthodoxy of that scholarly community.
4. **Religious entanglement:** cults endorse or condemn theories. A condemned true theory's scholars are persecuted (a heresy trial). An endorsed false theory is propped up by the cult.
5. **The gods know:** sons can reveal the truth (a tool that plants or confirms a correct theory), which costs essence and gives standing with scholars, or anger with cults that held the opposing theory.

#### Interconnections

Knowledge effectiveness, medicine outcomes (3.4 reference pass), navigation, magic reliability, cult doctrine, ideologies, education.

#### Tables and rules

- **Tables:** `theory_profiles`, `theory_adherents`, `theory_anomalies`.
- **Rules namespace:** `theories`.

#### UI

A theory card with "what people believe versus what is true" (the player sees both) and a paradigm timeline.

### 8.5 Ideology (new type)

#### Attributes

- `value_delta` (the vector it pushes)
- `tenets` (typed, shared with cult tenets where secular: legalism, stoicism-like_restraint, egalitarianism, divine_right, mercantilism, militarism, asceticism, rationalism, nature_harmony, xenophobia, cosmopolitanism, anti_god (a rebel creed against the pantheon: interacts with son existence), creatorism (exclusive Creator worship))
- `founder`, `texts` (books)
- `adherents` (scholars, rulers, factions, cohorts)
- `appeal` per class (egalitarianism appeals to the poor and serfs; divine right to nobles and clergy)

#### Behaviours

- **Spread** through scholars, books, schools and routes, and by appeal to discontented classes (needs and pressures).
- **Adoption** by a polity (state ideology) changes its decision weights (e.g. mercantilism raises trade-route investment) and law enactment preferences.
- **Conflict** with cults whose tenets oppose it: heresy accusations, persecution.
- **Revolutions:** an egalitarian ideology plus an unhappy class plus a weak polity leads to a revolt of cause `ideology` with a war aim to change the government (4.6).
- **Anti-god creeds** reduce faith in sons, which lowers their existence: a mortal movement that threatens gods. Sons may respond with miracles or persecution. This is a new god↔mortal conflict channel.

#### Tables and rules

- **Tables:** `ideology_profiles`, `ideology_adherents`.
- **Rule namespace:** `ideologies`.

---

#### Reference pass (R6, R5)

- Ideologies drive **political movements** (4.4 reference pass) and shape **policy networks** (4.6 reference pass). Revolutions can write constitutions (4.6 reference pass).
- Tech-driven ideology emergence: printing and universities raise the base rate of new ideologies.

### 8.6 Rite and magic (new type `rite`)

**Current.** Magic is the branch level plus the WIZARD flag. There are no spells, costs or schools.

#### Magic model

- **Schools** (`MagicSchool` enum: elemental_fire, elemental_water, earth, storm, life, death, mind, illusion, divination, warding, binding, summoning, blood, void). Schools map to domains, so a son's domains favour schools for its worshippers.
- **Sources** (`MagicSource`): ley (region magic density), divine (granted by a god: essence), blood (the caster's own hp: an injury), soul (spirits bound), reagent (commodity), void (leak: sanity cost).

#### Rite attributes

- `school`, `source`, `requirements` (technique level, skill, place kind or ley line, season or sky event: "only under an eclipse", participants count)
- `cost` (essence, hp, reagents, captives for blood rites, sanity)
- `effect` (typed effect list: damage hits of type fire, cold or void; heal injury (regrow a limb at high power); weather_change (call fog or storm for a campaign season, linking F2.3); curse or bless (modifiers); ward (siege defence); scry (intel); bind; summon (beast, spirit); raise_dead (undead units from battle dead); fertility; harvest_blessing)
- `power` 1–10
- `backlash` (probability and kind: injury, madness, leak +, a summoned thing escapes)
- `legality` (per law), `sanctity` (per doctrine: holy or heresy)

#### Behaviours

1. **Casting** by mortals with the spellcraft skill (wizards), cults (collective rites), armies (war mages) and sons (powers are formalised as rites with essence cost).
2. **Weather rites** override the weather draw for one slot. War outcomes and harvests can thus be changed by magic, with counter-rites (warding).
3. **Healing rites** restore lost function, which is why mages are valued in war and courts: an incentive structure.
4. **Blood and void rites** produce injuries, infamy and leak, and are tempting when desperate (needs and pressure weight). The engine picks them for desperate agents with low mercy.
5. **Backlash** creates phenomena (10.6: a failed storm rite becomes an eternal storm) and injuries.
6. **Magic price** (the existing natural law) becomes a rite cost multiplier.

#### Tables and rules

- **Tables:** `rite_profiles`, `rite_effects`, `castings` (log).
- **Rules namespaces:** `magic` (extended), `rites`, `backlash`.

---

#### Reference pass (R1)

- **Necromancy towers and undead:** the raise_dead rite plus a tower (structure) lets necromancers keep an undead host (army stacks of kind `undead`: no morale, slow, not fed, they decay without essence or soul fuel). The undead besiege the living (beasts and armies). Their creation is unthinkable in most ethics (F16) and raises the region's evil axis (6.1 reference pass).
- **Interaction rites:** the rite effect list includes applying an F30 effect package (curses, blessings, transformations).
- **Reincarnation blocks** (decision K.7) are rites of the warding and death schools.
- **Desecration:** violating a holy place (theft from a temple, killing in a sanctuary, defiling a tomb) triggers the god's **desecration curse**, an effect package chosen by the god's domains (a Hunt god gives a werebeast curse; a Blood god, vampirism; a Death god, a haunting). This makes sacred space mechanically protected.

#### Reference pass 3 (R8, R9, R10)

**Spell grammar** (Ars Magica-style): every rite is composed of a **technique** and a **form**.

- **Techniques:** create, perceive, transform, destroy, control, bind, summon, ward.
- **Forms:** fire, water, air, earth, plant, animal, body, mind, image, spirit, time, void, death, light.
- **Modifiers:** range (touch, sight, region, world), duration (instant, season, epoch, permanent), target (one, group, structure, region) and power.

Cost and difficulty are computed from the combination. Mages **design** rites in laboratories (research seasons) and record them as **lab texts** (books) that others can learn. The fixed schools of the first pass become typical technique-and-form clusters.

**Magic resources:** typed per form (fire vis, death vis, …), found at magic sites (6.2 reference pass 3), harvested from creatures (organs of beasts with matching affinities) and from phenomena. They are stored, traded (the black market where magic is banned) and consumed by rites, enchantments and longevity potions.

**Resistance and penetration:** every target has **magic resistance** from willpower, wards, materials (iron and sanctity, F23), dominion of a hostile god (F31) and faith. A rite's **penetration** comes from power and the caster's skill. Counterspells (a ward rite cast in reaction, by a prepared mage), dispels (end an ongoing effect) and wards (place and item protections) interact by power contests.

**Paradigms:** each magical tradition is grounded in a **theory** (8.4b) of how magic works. The theory's correctness against the world's true natural laws (9.5) sets the reliability of rites designed under it, and a paradigm shift changes how well a whole tradition works. Mage: The Ascension's paradigm idea thereby gains a real truth value.

**Myth-coupling:** rites that **re-enact a known myth** (a legend with high credence among the participants) gain power, and group rites at the myth's site gain more. A myth's distortion (8.2) changes the rite's effect, so a corrupted myth gives a corrupted rite.

**Environmental combination:** rites interact with environmental states (F2.3 weather and F23 materials):

- wet targets conduct storm rites;
- rain weakens fire rites and strengthens water rites;
- dry forests turn fire rites into wildfires;
- iron disrupts spirit rites;
- void rites in high-leak regions over-perform and backlash more.

Noita-like composite effects come from typed state, not scripted combos.

**Warping:** long exposure to magic (mages, people living on ley lines, users of enchanted items) accumulates **warping**, which triggers F30 packages over time (strange appearance, attunement, madness, longevity).

**Enchanted items:** enchantments have charges and recharge rules (at a magic site, from a resource, by the moon cycle, 10.9). Over-use cracks the item (condition −).

**Longevity magic:** potions and rites that slow ageing, at resource costs, with warping and growing dependence. An ancient mage's longevity is a recurring cost and a lever (cut off their vis supply).

**Global enchantments:** world-scale rites with upkeep (essence, resources, a sustaining order of mages), modelled as natural laws with source `enchantment` (9.5 reference pass 3). Rival casters can dispel them by a power contest.

#### Reference pass 5 (S-D Mistborn, Kingkiller)

- **Material-bound magic:** materials (F3, `world_materials`) can carry **innate magical affinities** (a metal that grants strength when consumed by those with the gift; a crystal that stores a technique; salt that wards spirits). They are recorded as affinity rows (material, technique × form, mode: consumed, worn, inscribed, ground). This makes materials a magic economy (mining for magic, F23) and lets a world's magic depend on its geology (6.1 reference pass).
- **Sympathy:** rites can target through a **sympathetic link**: something once part of the target or strongly similar to it (hair, blood, a name, a portrait, a piece of a ship). Link strength sets the penetration (8.6 reference pass 3) and the range.
  - Links are evidence (4.5 reference pass 5) and objects of schemes (stealing a lock of hair).
  - Defences include burning one's hair and keeping one's true name secret.
  - The spell grammar gains a `via link` modifier.

#### Reference pass 8 (B1)

**Rite components and the body:** each rite lists its **components**: spoken (needs speech: tongue, jaw), gestured (needs grasp and fine manipulation), inscribed (needs sight and hands), sung (needs breath), danced (needs locomotion), material (needs the reagents), mental (needs focus and cognition). Injuries and conditions (F4) block or weaken matching components, so a tongueless mage can still inscribe, and a blinded one can still chant. Silencing (gags), binding hands and blindfolds become the standard way to hold captive mages.

### 8.7 Prophecy

**Current.** certainty and reading. Fulfilment is decided by the LLM only.

#### Attributes

- `condition` (a typed, machine-checkable predicate built from a small DSL: `dies(entity)`, `falls(settlement)`, `born_in(house)`, `sky_event(kind)`, `war_between(a,b)`, `ruler_of(polity, matches(archetype))`, `within_epochs(n)`)
- `consequence` (typed: who will rule, what will fall)
- `seer` (a mortal), `audience` (communities that heard it)
- `certainty` (existing)
- `reading` (existing)
- `self_fulfilling_pressure` 0–100

#### Behaviours

1. **Engine fulfilment check** each epoch against the condition. The LLM writes prose and may judge ambiguous cases, but a met condition is fulfilled deterministically (closing the LLM-only gap).
2. **Self-fulfilment.** Believers act toward or against the prophecy. A prophecy that "the child born under the comet will rule" raises the claim strength of such children and makes the current ruler paranoid, so infanticide attempts follow (incidents and memories). The Oedipal loop is emergent.
3. **Resonance** with legends (8.2) raises certainty.
4. **Failure** (the deadline passes) mocks the seer, lowers the cult's zeal and the son's fame (existing), and raises cynicism (a value push toward rationalism).

#### Tables and rules

- **Tables:** `prophecy_conditions`.
- **Rules namespace:** `prophecy` (extended).

---

#### Reference pass

- Prophecy conditions can reference event collections (F10 reference pass) and titles (2T.6). Prophecies also distort as legends do when they are retold (8.2).

#### Reference pass 4 (R34, R35)

- **Divination systems** (`divination_systems` per culture): augury (birds and weather signs), haruspicy-like readings (sacrifices), astrology (10.9 sky), oracle readings (a god's answer through a seer), lots and dice, dream reading (F14 reference pass 4).
  - Each system has a **validity** in the world: truly informative only where a god answers, a seer gift exists or a natural law makes signs real; otherwise noise.
  - **Court diviners** advise rulers on timing: auspicious days for battles, weddings and coronations. Decision functions (F22) read divination results through the ruler's superstition belief.
  - Wrong but trusted diviners are a real source of folly, and a god can corrupt or guide them.
- **Prescience and its limits:** seers with high prescience see **probable futures**. The engine runs a cheap forecast of typed outcomes from the current state with rolls held out, which can be wrong because other actors also act on prophecy. Rival seers' visions interfere and create **blind spots** around them. Gods with the seer power have the strongest sight, and outer beings are invisible to prescience.
- **Psychohistory:** a scholarly order with the `statistics` civic technique and a large archive can build a **forecast model** of a polity or world: the engine exposes aggregated PSI, wages and dynamics (F37) as a noisy forecast. The order may then run a **long plan** (F37) to steer outcomes through small interventions (schemes, propaganda, preserved knowledge). Its effectiveness falls when individuals of great influence (great people, gods, mantling mortals) intervene, which is the mule problem, emerging from the same rules.

### 8.8 Event (time-bounded happening)

**Current.** severity only.

#### Attributes

- `event_kind` (existing engine kind; extended: festival_of_note, coronation, wedding, massacre, sack, famine, flood, fire, eruption, riot, schism_council, eclipse_watch)
- `start`, `end` (year and season)
- `footprint` (regions)
- `phase` (onset, peak, aftermath)
- `casualties_by_cohort`
- `incident_id`

#### Behaviours

- Events are the visible face of incidents (F10). Multi-season events (famines, plagues, sieges) progress through phases with per-phase effects.
- The chronicler reads phases, so lines mark the turn of a famine.


#### Reference pass

Events are now the visible face of **event collections** (F10 reference pass), with the full kind list there. Gatherings (F25) are events of the occasion family.

---

## Part 9. The divine

### 9.1 Son (god card)

**Current.** 9 stats, 4 passions (mercy is never read and ambition is read once), 13 power effects, existence, sanity and reputation toward the Creator. Personality is prose. Domains are mechanically thin. Sons have no goals, no inheritance math and no divine injuries.

#### Attributes

**Value vector** (F5), derived from domains and passions and editable. Mercy and ambition become value and trait weights that every engine choice of the son reads: spontaneous acts, rivalry, intervention style.

**Traits** (F5.1, a divine subset) replace the prose temperament as the canonical source. The personality prose is written from them (G8).

**Domain mechanics** (`domain_effects` catalog): each of the 40 domains gets typed hooks across subsystems. Examples:

| Domain | Hooks |
|---|---|
| Sea | naval stacks of worshippers ×; storms at sea obey the son; fisheries + |
| Fire | fire rites; volcano phenomena; fire risk in enemy cities on a curse |
| War | levy morale; duel injuries inflicted ×; the war_father power; essence per battle in which worshippers fight |
| Death | soul realm control; essence per death (existing); necromancy rites |
| Plague | disease creation; outbreaks give essence; immunity grants |
| Harvest | sampled-year harvest floor for worshippers |
| Oath | essence per kept oath; wrath at breaches |
| Memory | slows legend distortion for worshippers; remembers lost knowledge |
| Border | territory control and defence ×; fortification techniques |
| Salt | soil salting curse; preservation (food decay −) |
| Glass | lenses → astronomy; mirror worlds |
| Hunger | famine as a weapon; fasting traditions |
| Lie | rumour distortion ×; spy network depth |
| Road | route capacity and safety; travellers' oaths |
| Blood | blood rites; bloodline marks |
| Bone | relics; ossuaries |
| Madness | (existing hooks extended) |
| Time | aging speed; prophecy certainty |

All 40 domains get rows. **Domain synergy** of a son's pair creates compound hooks (Sea + Death: drowned souls go to an undersea realm).

**Divine body:** a manifest-form body plan (F4) with **divine injuries** (`injuries` with bearer = son). Sons hurt in duels, foreign-god wars or by the Creator suffer typed wounds: a severed domain (a lost power slot until healed), a shattered manifestation (manifestation mode change), a stolen true name (vulnerability), a wound of the void (sanity floor down). Divine wounds heal with faith over epochs, and can be healed faster by worshippers' rites (devotion).

**Goals** (`son_goals` table): typed, generated from values and domains and chosen by the son agent or the engine:

- be_worshipped_by(n)
- found_realm(holy world)
- destroy_rival(son)
- spread_domain(e.g. bring Plague to world X)
- win_war(people)
- acquire_relic, raise_hero(house), awaken(god), defeat(foreign_god)
- reconcile_with_creator, rebel

Goals give the LLM a typed objective and the engine a progress check, with xp and fame on completion. The `plan` text is then written about a goal.

**Worshipper standing** (per community): `son_standing` (community, son, awe, love, fear, neglect). Folk beliefs (prose) gain a mechanical twin. Gods are seen differently by each people.

**Avatars and incarnations:** a son can manifest as a mortal-form avatar entity (a mortal with the `avatar_of` link) that acts in the world. It can be wounded and killed, and killing it gives the son a divine wound.

**Divine offspring:** mortal children of a son are typed (`divine_blood` house trait). Son children (children born to sons) inherit stats as the mean of the parents ± deviation, plus a domain from each parent, closing the inheritance-math gap.

#### Behaviours

1. **Domain economy.** Essence income adds a domain activity term (each domain hook reports activity: battles for War, deaths for Death, voyages for Sea). Sons are therefore pushed to cultivate their domain in the world. This creates intrinsic motivation and inter-son domain conflict (Sea vs Storm over sailors).
2. **Intervention typed by power.** Powers become rites with essence costs and typed effects (8.6), including battle interventions (5.3 step 6) with counter-intervention by rival gods (a god contest roll on the same battle).
3. **Standing dynamics.** Answered prayers, miracles and protection raise love. Wrath signs raise fear. Neglect (unanswered prayers, no presence) grows the neglect component, which drives conversions away from the son and existence loss. Mercy-trait sons and wrath-trait sons produce different standing profiles in the same people.
4. **Divine politics.** Son relations (existing) gain memories (F7): who stole my worshippers, who helped my hero. Councils (9.4) decide on typed motions.
5. **Wounds and healing** (above). A son with a severed domain loses the corresponding hooks, and the world feels it: a Harvest god wounded means a hungry decade.
6. **Goal pursuit** for the engine-driven parts between LLM turns: drift of attention (which world the son watches) toward its goal targets.

#### Interconnections

Every subsystem via domain hooks; war (interventions, avatars); faith (standing, doctrine seeding); afterlife (judgement doctrine, realm control); houses (divine blood); prophecy (seer powers); ideology (anti-god creeds threaten existence).

#### Tables and rules

- **Tables:** `domain_effects` (catalog), `son_goals`, `son_standing`, `son_traits`, `divine_injuries` (the shared `injuries` table), `avatars`.
- **Rules namespaces:** `domains`, `son_goals`, `standing`, `divine_wounds`, `avatars`.

#### Player levers and UI

- **Levers:** set goals; wound or heal a son; edit domain hooks per world.
- **UI:** a son page with a domain activity chart (where its essence comes from), standing per people (a heat map), goals with progress, and a divine body with wounds.

---

#### Reference pass (R1, R6, R7)

**Domain aspects and compatibility** (R1 spheres):

- Each of the 40 domains has **3–4 aspects** (`domain_aspects` catalog, about 140 in total). Examples:
  - War: conquest, valour, slaughter, strategy.
  - Sea: storms at sea, depths, voyages, fish.
  - Death: rest, judgement, decay, the hunt for souls.
  - Love: desire, devotion, marriage, longing.
- A son's domains are realised through aspects chosen at birth (by passions and personality) and broadened by deeds. Aspects carry the domain hooks of 9.1 at a finer grain, so two War sons differ (valour against slaughter).
- **Compatibility matrix:** aspects are **friendly** (synergy), **neutral** or **precluded** (they cannot coexist in one god: mercy and slaughter). Precluded combinations are blocked at creation and summoning. Deeds that pull a son toward a precluded aspect create inner conflict: stress for gods (sanity −) and a possible **domain fracture** (an existing aspect is lost).
- Folk beliefs (prose) are generated *from* aspects and the people's standing (9.1).

**Gods have mind layers too:** facets, beliefs and thoughts (F13, F14) for sons, foreign gods and avatars, at a divine scale (the emotions are those of gods: wrath, jealousy, pride, longing for worship). Son mood shapes spontaneous acts between LLM turns.

**God relationships use F18:** friendship, rivalry and romance between gods (divine marriages and children: the existing `co_parent_son_id`).

**Divine schemes** (F20): sons can run schemes against each other (steal worshippers, frame for desecration, seduce a rival's chosen) with mortal agents. Their discovery creates council motions (9.4).

**Desecration curses:** each son defines (by aspects) the curse package applied to desecrators of its holy places (8.6 reference pass).

#### Reference pass 3 (R8, R9)

- **God design trade-offs** (Dominions-style, R8 #3): a son's creation budget (rarity × stars) is spent across:
  - stats;
  - `dominion_strength` (F31);
  - scales (F31: extreme scales cost or refund budget by their desirability);
  - magic aptitude per form (8.6 reference pass 3);
  - manifestation (an avatar body, F4);
  - powers.
  
  Summoning (the LLM) proposes a design within the budget, and Fate checks it. This makes sons differ in *kind*, not only in degree.
- **Perceived alignment and worship mode** (Black & White-style, R8 #8): from its acts, each people perceives a god as benevolent or malevolent (the standing components love and fear). The **worship mode** follows (devotion or appeasement), and so do the god's holy-site appearance (a temple's aesthetic shifts: decorations and artworks, 7.1), its manifestation (avatar appearance) and the prayers it receives (petitions of thanks or of mercy). A feared god gets offerings to stay away; a loved one gets requests to come.
- **Learning divine creature** (R8 #9): a son may raise a **divine creature** (a beast avatar) that acts on its own between turns. Its behaviour policy is learned by reinforcement from its god: the son's typed rewards and punishments on specific behaviours (eating villagers, helping farmers, throwing rocks at enemies) adjust the creature's action weights. A neglected creature drifts on its own needs. Its deeds count as the god's for standing and dominion.
- **Miracle impressiveness** (R8 #10): the belief gained from a miracle = magnitude × witnesses (cohorts present, gatherings) × need (a miracle in famine counts more) × novelty (repeats count less: the tired-motif analogue) × legibility (the people's theory of the god, 8.4b: a miracle that matches expectations is credited, a strange one may be misattributed, F31).
- **Belief shapes gods** (R9 #4, Small Gods-style): the aggregate folk beliefs, standing and accounts (F33) of a god among its worshippers pull its **aspects**, **manifestation** and **facets** each epoch toward the believed image (decision K.12). The pull is an equation, not a constant:

  ```
  pull = base × belief_intensity × worship_share × crisis_severity × malleability(god) × (1 − pin)
  ```

  - **belief_intensity:** the credence and uniformity of the image across the god's peoples. A contested image pulls weakly in several directions.
  - **worship_share:** the share of the god's faith held by the believing peoples.
  - **crisis_severity:** pressure from disasters, wars, plagues and theodicy crises. In desperate times peoples cling to their image of the god and reshape it fastest.
  - **malleability(god):** from the god's facets and state. Stubbornness, willpower, pride and a strong sense of self resist; impressionability, vanity, a hunger for worship and low existence yield. A fading god is most malleable, and a radiant one barely moves.
  - **pin:** the player's pin lever (J.16c) on a son's personality or appearance stops the pull on the pinned fields entirely.
  
  The son can also resist at an essence cost, or embrace the image for standing. A god believed cruel slowly becomes crueller, and a god believed to have a lion's head is seen with one. Gods therefore are partly what their peoples make of them.
- **Mantling and ascension** (R9 #5): see 3.1 reference pass 3. A son's goals now include *preventing* a mortal mantling of its aspects, or *sponsoring* one (a chosen successor).
- **Ascension by thrones:** holding thrones of power (6.2 reference pass 3) across worlds is a son goal that leads toward a higher divine rank: a cosmic office (9.4 reference pass 3), more power slots, or a challenge to the Creator. The last is the rebellion path, made territorial.

#### Reference pass 4 (R33)

- **Emotion-fed gods** (Warhammer-like, generalised): each domain aspect (9.1 reference pass) declares the **mortal emotions that feed it** (F14): a War aspect of slaughter feeds on rage, a Love aspect on longing, a Death aspect on grief, Madness on despair, Trickery on amusement, the Hunt on fear. Essence income gains an **emotion term**: the sum of matching emotions among mortals in the god's dominion (F31). Gods therefore have an interest in their peoples' emotional lives, and some gods have dark incentives. A god of grief prospers in plague years, which is a beyond-the-leader coupling of divine economy and mortal psychology.
- **Celestial bureaucracy at the top:** sons supervise lesser spirits' offices (3.3 reference pass 4). Their divine work (processing petitions, appointing city gods) is a source of standing and dominion, and neglect lets the bureaucracy rot (corrupt spirits, unanswered prayers, popular cults of rogue spirits).

### 9.2 Creator (the player's god)

**Current.** 4 mood axes, temperament, passions (display-only) and essence.

#### Attributes and behaviours

- **Passions become mechanical:** each `CreatorPassion` (order, chaos, beauty, knowledge, war, mercy, creation, silence) maps to world metrics, for example beauty → wonders and artwork renown, knowledge → tech spread, war → battles. Contentment rises when the world matches the passions. Passions also bias spontaneous creator signs (a creator with the knowledge passion sends revelation dreams to scholars).
- **Taboos** (`GodDepth.taboos`, today prose) become typed `creator_taboos` (an ActKind list). Breaking one (by sons or mortals) raises anger and targets wrath signs.
- **Creator standing** among peoples (as `son_standing`, 9.1). The Creator's cult, godless communities and estrangement are already partly modelled; they become standing components.
- **Attention budget:** the Creator's interest is spent on watched worlds. Unwatched worlds drift: sons there act more freely, and rebellion is likelier.

#### Tables and rules

- **Tables:** `creator_taboos`, `creator_standing`.
- **Rules namespace:** `creator` (extended).

---

#### Reference pass

- The Creator's standing per people is in F19 currencies too (prestige and dread toward the Creator).
- **The Creator's attention** (9.2) is a budget visible in the UI. Unattended worlds show a "far from the eye" status, raising son autonomy and rebellion risk.

### 9.3 Foreign god

**Current.** Stats, power, stance and 8 power effects. Foreign gods have no goals and no relations among themselves.

#### Additions

- The same value vector, traits, domain hooks, goals and standing as sons (9.1). Their domains get the same `domain_effects` rows, so a native Harvest god competes with a son of Harvest for the same farmers.
- **Inter-god relations:** foreign gods hold opinions (F7) of each other and of sons. They can ally against the pantheon, sign **treaties** (5.13, kind `divine_pact`) with sons, and be worshipped jointly (syncretism, existing).
- **Old-god doctrine:** each foreign god seeds the native cult doctrine (4.4), so native faith has tenets.
- **Divine injuries** apply in god wars (existing conflict resolver, extended).

---

#### Reference pass

Foreign gods gain aspects, mind layers, relationships and schemes as sons do. Native pantheons have internal structures (a family tree of gods with titles in their mythology: a divine title, 2T.6) that peoples tell of in legends.

### 9.4 Pantheon council

**Current.** An LLM debate with 5–6 scalar outcomes.

**Additions.** Typed motions with typed effects:

- war on a foreign god (a joint conflict with pooled strength)
- divide worlds (patronage assignment)
- outlaw a rite (cosmic law: a natural-law-like rule)
- punish a son (chain, exile, strip a power)
- bless a hero (a condition)
- declare a holy world
- set a cosmic truce (block god duels for N epochs)
- petition the Creator (raises the Creator's interest; may lower anger)

Votes weigh relations, goals and values. Results are binding rules for N epochs and are enforced by the engine.

---

#### Reference pass (R6)

Council motions are crises (4.6 reference pass) between gods: backers, favours (F20) and escalation, up to a divine war when they fail.

#### Reference pass 3 (R9)

**Cosmic offices:** titles of divine rank (2T.6) such as Lord of the Dead, Keeper of the Gates, Warden of the Stars, Judge of Oaths, Herald of the Creator, Master of the Hunt.

- Each office has duties (e.g. the Lord of the Dead runs the realms' judgement), powers (typed rite access and essence income from the office's domain activity) and a holder chosen by the council (9.4), the Creator, conquest of the previous holder, or mantling.
- **Neglected duties** have world effects: an absent Lord of the Dead lets ghosts multiply, and an absent Keeper lets routes decay.
- Offices are contested in council crises and divine wars, which gives the pantheon a real political structure (Malazan-like houses).

### 9.5 Natural law

**Current.** No stats; one of 10 kinds, assigned by regex.

#### Attributes

- `law_effect` (typed; the 10 existing plus new: no_iron, eternal_night_in(region), souls_reincarnate, magic_requires_blood, gravity_shift, seasons_reversed, dreams_are_real (dream routes always open), oaths_bind (oath-breakers are cursed automatically), the_dead_speak (spirits are agents), metal_rusts_fast)
- `scope` (cosmos, world, region)
- `strength` 0–100
- `stability` (decays without its maintaining god's essence)
- `author` (son or creator)
- `exceptions` (e.g. immortality except for the creator's chosen)

#### Behaviours

- Laws are modifiers on whole scopes, plus typed rule switches (G2: no regex).
- **Contest:** two sons' laws that contradict (immortality vs short_life) contest by strength. The weaker erodes, or the region becomes a phenomenon of conflicting physics (10.6).
- **Upkeep:** an author's existence below a threshold weakens its laws, so the death of a god can unmake laws.

---

#### Reference pass

Natural laws can reference physical constants in 10.9 (gravity shift, seasons reversed, tidal lock). Laws change those derived values through the same modifier bus.

#### Reference pass 3 (R8, R10)

**Global enchantments** are natural laws with `source: enchantment`, a caster (son, mage order, foreign god), an **upkeep** (essence or magic resources per epoch) and a **dispel resistance**. Examples: eternal summer over a world, a ward against outer beings, a curse of barren wombs on an enemy world, a sea-calm across all oceans. They stop when their upkeep fails or a dispel succeeds. Natural laws authored by sons gain the same upkeep model, so laws need a living, paying author (9.5 stability made explicit).

### 9.6 Outer being

**Current.** size, interest and influence (size is never read).

#### Additions

- `size` becomes mechanical: reach (regions affected) and the essence or sanity cost to oppose.
- `hunger` (what it feeds on: souls, knowledge, light, names, memories). Typed consumption follows: it eats words from languages (the existing wave of silence), memories (legend credence drop), souls (realm population), and light (a star's brightness drop).
- `cults` (existing outer cults) with a doctrine of typed void tenets.
- `bargains` (existing outer bargains) get typed terms: what the son gains (essence, a power) and pays (a world's sanity, a domain, a true name).
- `breach_points` (phenomena where it touches the cosmos).


#### Reference pass

Outer beings use F30 packages for their touch (void taint), F22 deception (whispers plant false beliefs) and schemes through their cults.

---

## Part 10. Cosmos

### 10.1 Star

**Current.** 32 types (the spectral classes, giants and supergiants, remnants and fantastic stars of 14-cosmos-types.md), brightness and position. Each type has a mechanics row (brightness band, heat, capacity, collapse and flare weights, remnant, eclipse weight, leak, sanity, sail danger, instability) that the engine reads today.

#### Attributes

- `spectral_class` (typed effects table)
- `age_stage` (young, main, old, dying, dead, reborn)
- `luminosity` (brightness, existing)
- `stability` (flare risk)
- `habitable_band` (the orbit range where worlds have temperate bands)
- `radiation` (mutation pressure)
- `sacredness` (worship by peoples: sun cults)
- `patron_son`
- `lifecycle_clock` (epochs to the next stage)

#### Behaviours

- **Life cycle:** stars age and dim. Worlds cool, so temperature bands shift and ice ages become likelier. Dying stars produce supernova risk (existing event, now a lifecycle outcome).
- **Flares:** per sampled year a flare can cause auroras (an omen), radiation mutation, crop failure, or route disruption for light sails (existing failure).
- **Star worship:** sun cults' piety tracks brightness. A dimming star causes a crisis of faith and invites eclipse prophecies.
- **Rekindling** (existing quest) gains typed costs.

#### Reference pass (R2)

- **Mass-based evolution:** each star has `mass` (solar-mass analogue) and `metallicity`. Lifetime, luminosity and stage transitions follow tables keyed by mass:
  - low-mass stars burn long and dim;
  - high-mass stars burn briefly and end as neutron-star or black-hole analogues (the existing black-sun type) with a supernova on the way;
  - mid-mass stars swell into giants (engulfing inner worlds: a doom-class event for those worlds) and leave white-dwarf analogues.
- **Flares** scale with the star type (red dwarf flares are frequent).
- **Divine stars:** stars made by sons can break the tables (a sacredness and essence upkeep instead of mass), with their stability tied to the maker's existence.

### 10.2 World

**Current.** Type, gravity, atmosphere, time factor, terrain, discovery, danger, leakage and climate era.

#### Attributes

- **Seasons:** axial tilt, seasons, day length, moons and tides (F2.2).
- **Physics:** `gravity` (existing; now effects across movement speed, flying-species viability, building height limits, missile range), `atmosphere` (existing; breathability per people biology: a thin atmosphere gives endurance −, a toxic one disease load +), `magnetism` (navigation), `radiation`.
- **Climate system:** a world-level era (existing) plus regional variation (F2.1) and an ocean current flag per coast (warm current: coastal temperature +).
- `danger` (now aggregated from regional danger sources; read by settlers and travellers instead of being unread)
- **Leak** gets regional distribution (`region_leak`). Leak concentrates near gates, outer cults and phenomena, so horror becomes a geography.
- `biosphere_health` 0–100 (the aggregate ecology: extinctions, land use, invasive species)
- `age_stage` (young, mature, old, dying)
- `consciousness` (living worlds: the existing `consciousness_closed`, extended into a mood toward its inhabitants that responds to land use and mining)

#### Behaviours

1. **Physics effects** are wired through modifiers: gravity affects army speed and siege-engine range, flight availability and settlement build height. Atmosphere affects people endurance and disease. Low-gravity worlds favour flying species and sky mounts.
2. **Living-world mood:** a living planet reacts to mining and clearing with quakes and hostile fauna, and to reverence with fertility. Peoples that worship the planet (the existing `WORSHIPS_PLANET` flag) get its favour.
3. **World aging:** old worlds cool and their soils deplete, raising migration pressure toward new worlds (journeys).
4. **Biosphere collapse** (a threshold on biosphere health) brings famines, disease emergence and doom +.

#### Reference pass (R2)

- **Survey levels per observer:** each polity holds a survey level per world (unknown, rumoured, detected, observed (by astronomy), surveyed (visited), mapped). Survey level gates journeys, colonisation planning and claims across worlds, and sky-sailing techniques raise it. The existing `discovery` field stays as the cosmos-wide (player) view.
- **Habitability per people** (4.1 reference pass) uses the derived physics of 10.9.

#### Reference pass 3 (R9)

**Belief-shaped worlds** (Planescape-style): worlds, especially dream, mirror, palace and realm-of-the-dead types, and to a lesser degree all worlds, drift toward the dominant beliefs and dominions of their inhabitants:

- regions' alignment axes (6.1 reference pass) move with the inhabitants' ethics and the dominant god's scales (F31);
- on mutable world types, terrain and weather follow the inhabitants' dominant preferences and fears (a dream world of a fearful people grows nightmares);
- a world dominated by one god's dominion may slowly **change world type** toward that god's domains (a Death god's world becomes corpse-like, a Sea god's world floods). This is a long-term, contestable process that the player sees as a gauge.

Gates and routes to a world shift with its belief-drift (a route's danger and method follow the new nature).

#### Reference pass 4 (R34, R39)

- **Formation history:** world birth (the existing genesis and son world-birth) runs a short **formation model**:
  - a protoplanetary disc around the star with a **snow line**: rocky and metal-rich inside, icy and gas-rich outside;
  - accretion into embryos;
  - **giant migration** (inward migration scatters inner worlds and brings water; outward leaves them dry);
  - a **bombardment era** (heavy impacts in the young system, recorded as ancient craters and as the source of the world's water and exotic materials);
  - **differentiation** (core size sets magnetism; mantle heat sets volcanism and tectonics).
  
  The world's 10.9 inputs come from this history, so a system's worlds are physically consistent with each other. Divine worlds (palaces, dream worlds) bypass it by design.
- **Irregular seasons** (A Song of Ice and Fire-like): a natural law, a chaotic orbit (a binary system with resonance, 10.9) or a divine act can make seasons **irregular**: multi-year winters of uncertain length. Cultures adapt (storage, F24; famine foods; maesters-like calendar scholars who predict winters), and unpreparedness is catastrophic. The derived-season model supports this without special cases.
- **Long ecological transformation:** long plans (F37) can target a world's climate and biome distribution over centuries (terraforming a desert world by planting, water capture and a slowly growing biosphere, 10.9 reference pass 3 cycles). The plan's progress is tracked against the natural feedbacks, and it can be sabotaged by the people who depend on the old ecology.

### 10.3 Celestial body (entity)

**Current.** brightness and influence; influence is never read.

**Additions:**

- `influence` is wired into domain hooks: a celestial whose domain matches gives the epoch-star essence bonus (existing), and now also cult piety, prophecy certainty and rite power for its school (moon → divination, comet → fire).
- `cycle` (period in years: a visible return; comets return and create recurring omens and festivals)
- `visibility` (season-dependent)
- `omen_reading` per culture (good, evil or neutral, from superstition and doctrine)

#### Reference pass (R2)

**Periodic bodies:** celestial entities for comets and wandering stars get orbital elements (10.9), so their return year is computed. Omens and festivals are tied to returns, and prophecies can reference them.

### 10.4 Route (inter-world)

Already deep. Additions:

- `capacity` and `traffic` (trade volume between worlds, shared with the trade-route model in 6.4)
- `toll_controller`
- `piracy_level` (void pirates, existing faction; now an actual per-journey encounter roll)
- `seasonal_window` (slingshot alignment, existing; generalised to all methods: some gates open only at a solstice)
- `wear` (gates degrade with traffic and need maintenance rites)

#### Reference pass 5 (S-B, S-C, S-D Terra Invicta)

- **Launch windows:** for physical travel methods (sails, slingshots, sky-ships between worlds, void mounts), travel duration and danger depend on the **relative positions** of the worlds in their computed orbits (10.9). Windows open periodically (the synodic period), and travel outside them costs more provisions and time. Divine and magical methods (gates, folding, dreams, bridges) ignore windows. Windows synchronise migration waves, invasions and trade fleets across worlds.
- **Cosmopolitan cultures (system scale):** along busy interworld routes, a **cosmopolitan culture** forms: a shared value drift among merchant, crew and diaspora communities of several worlds, a lingua franca (8.1), art forms of the routes, and system-scale accounts (F33) of shared history. It gives the star-system level its own culture and memory, and it is a counterweight to world-bound nativism (4.1 reference pass 5).

### 10.5 Journey

Already deep. Additions:

- `cargo` (commodities, items, relics)
- `passengers` as cohorts with class and condition (a colony ship of sick refugees spreads disease)
- `convoy` (multiple vessels; escorts)
- `encounters` (typed: piracy, storm, beast, outer touch, derelict found)
- `memory_loss` (existing) is applied to passengers' memories and knowledge (F7, 8.4): colonists of the river of the dead arrive without their history, which seeds new legends.

### 10.6 Phenomenon (new type)

#### Attributes

- `phenomenon_kind`: eternal_storm, time_slip, leak_wound, ley_nexus_flare, god_corpse_aura, living_fog, crystal_bloom, dead_zone (nothing grows), mirror_lake, gravity_well, singing_stones, aurora_permanent, ghost_road, blight
- `footprint` (regions with intensity per region)
- `intensity` 0–100, `growth` (spread rate), `cause_incident_id`
- `effects` (typed modifiers: weather override, magic density, sanity drain, aging rate, fertility, danger source, travel block)
- `containment` (wards, temples, rites holding it)

#### Behaviours

- **Spread or decay** by intensity and containment.
- **Effects** on everything in the footprint through modifiers.
- **Formation** from incidents: rite backlash (8.6), god deaths (corpse aura), conflicting natural laws (9.5), sky events (a supernova shard), leak peaks, mass-death battlefields (ghost road).
- **Exploitation:** reagents harvested at crystal blooms, pilgrimage to auroras, gates opened at leak wounds. This creates risk-reward incentives.
- **Sealing** by rites, the Creator's hand or son tools.

#### Tables and rules

- **Tables:** `phenomenon_profiles`, `phenomenon_footprints`.
- **Rules namespace:** `phenomena`.

#### Reference pass 3 (R9)

**Contested histories** (dragon-break-like): time-slip phenomena and time-domain sons can create **divergent chronologies**. A span of years in a footprint has two incompatible incident records, each canon for the people who lived it. Both branches are stored (incident branch ids). Accounts, legends and memories follow the branch of their holders. Fate (an LLM step) or a son's act **reconciles** the branches later: one becomes canon and the other becomes legend, prophecy or madness, with typed effects on those who remember the lost branch.

#### Reference pass 10 (C6)

**Footprint kinds.** A phenomenon's footprint is typed (`footprint_kind`):

| Kind | Where it acts | Typical effects |
|---|---|---|
| `regions` (existing) | regions with an intensity per region | all region effects |
| `world_sky` | over a whole world | light, omens, celestial influence, weather |
| `system` | over all worlds of a star system | insolation modifiers, sky omens on every world, route danger inside the system |
| `route` | along an inter-world route | travel danger, duration, encounters |
| `stratum` | an underground or afterlife stratum | hauntings, beasts, judgement anomalies |

The star-god's corpse is a `system` phenomenon. A void storm along a route is a `route` phenomenon, which gives the existing void-storm sky event a persistent form when it does not dissipate.

### 10.7 Climate (cross-cutting)

- The world-level era (existing) becomes a set of **targets** for regional temperature and rainfall shifts, applied with regional modulation (coast, elevation, ocean currents, latitude).
- **Feedbacks:** deforestation lowers rainfall in neighbouring regions (Loop R toward desertification). Volcanic phenomena cause short cold periods (ash), and a supernova causes a long one.
- **Sons** (Storm, Sun, Ice domains) can push targets (existing imposition, now regional).
- **Notable climate years** (F1) feed traditions and legends.

#### Reference pass 5 (S-B)

- **Atmospheric circulation:** each world's derived physics (10.9: rotation, insolation and tilt) gives **circulation bands** (trade-wind-like, westerly and polar bands analogues; one-cell or exotic circulation on slow-rotating or tidally locked worlds). Bands set the **prevailing winds** per region and season. These feed sailing routes (points of sail, 5.5 reference pass 4), fire spread, pollution transport (F24) and the rain side and dry side of mountain ranges.
- **Rain shadows:** moist winds rising over mountains rain on the windward side and leave deserts in the lee. Rainfall per region (F2.1) is computed from the prevailing winds and the terrain, so deserts and forests sit in physically plausible places.
- **Monsoons:** seasonal reversal of winds over large land–sea contrasts gives wet and dry seasons with variable strength. A failed monsoon is a famine year (F1 notable year), and monsoon timing shapes sailing seasons on trade routes.
- **Ocean currents:** warm and cold currents (from the circulation and the coastline) set coastal temperatures, fisheries (upwelling of nutrients, 6.1 reference pass 5) and sailing speeds. They also carry drifting things (wrecks, castaways, stowaway species, messages in bottles: rumours, F11).
- **Climate oscillations:** quasi-periodic oscillations (El Niño-like) shift rainfall and temperature across regions for sampled years, producing correlated droughts and floods across distant regions. Diviners and astronomers who track them gain prediction power (8.7 reference pass 4).

### 10.8 Doom and leak (cross-cutting)

- The doom clock (existing) gains **typed contributors with provenance** through the modifier bus (F9). The doom UI explains its sources.
- Regional leak (10.2) makes horror events target hot spots and creates phenomena at peaks.
- **Apocalypse variants** become typed and depend on the dominant contributors: a war-dominated doom ends in a world war called by the Calling; a leak-dominated doom brings an outer-being descent; a godlessness-dominated one is a twilight of the gods (sons fade ×2).


#### Reference pass 4 (R34)

**Cyclic ages** (Wheel of Time-like): a cosmos may run on a **cycle of ages** (genesis setting: linear or cyclic). Decision K.18: existing cosmoses stay **linear** (their current behaviour, G10), and the genesis default for new cosmoses is also linear.

- In a cyclic cosmos, the doom clock's apocalypse is a **turning of the age**, not an end. The world is remade (existing previous-creation mechanics: ruins and relics of the prior age, lost knowledge) with **echoes**: archetypal roles recur (a dragon-reborn-like figure, the betrayer, the founding couple) as arc templates (F36) seeded at higher weights. Souls of the prior age may be reborn into their echoes (a reincarnation gate, K.7).
- Prophecies and legends of the prior age carry over as fragmentary texts (F33 accounts with low fidelity), so each age half-remembers the last.
- The cycle's period and how much carries over are rules (`ages.*`).

### 10.10 Galaxy (new node kind)

**Current.** Stars sit on one flat map (`x`, `y`) with no larger structure. The cosmos has no galaxy, no place for a star inside a galaxy, and nothing beyond.

The cosmos is one whole, with a fixed scale ladder: **dimension → cluster (with nested groups) → galaxy → galactic structure and zone → star → world → moon.** Each step is a node, or a record owned by a node, that the engine reads and the god controls. The stored star position becomes its position inside its galaxy.

#### Attributes

- `galaxy_type` (typed effects table), with real and fantasy types:
  - **Real:** spiral, barred spiral, grand-design spiral, flocculent spiral, lenticular, elliptical, giant elliptical, dwarf elliptical, dwarf spheroidal, irregular, dwarf irregular, ring, peculiar (interacting), starburst, active (bright nucleus), quasar host, low surface brightness, ultra-diffuse.
  - **Fantasy:** living galaxy, dead galaxy, shattered galaxy, forged galaxy (made by a god), dreaming galaxy, mirror galaxy, crowned galaxy (one ruling power), hollow galaxy, ember galaxy (dying fire), veiled galaxy (hidden from outside).
  - Each type row gives star density, the star formation base, metallicity base, the arm count range, nucleus weights, leak, sanity, travel danger, life capacity and the zone layout.
- `cluster_id` or `dimension_id` (where it lies; one of the two, and a galaxy without either lies in the prime dimension), `x`, `y` (its place in the cluster), `radius`.
- `arm_count`, `nucleus` (none, dormant, active, quasar, devoured), `star_formation` 0–100, `metallicity` 0–100, `age_stage` (forming, young, mature, old, dying, dead), `leak` 0–100, `discovery`, `patron_son_id`.
- `merging_with_galaxy_id`, `merge_progress` 0–100.

**Galactic zones** (`galactic_zone` per star, derived from its position and the type's layout, and overridable): core, bulge, bar, inner disc, arm, interarm, outer disc, halo, rim and intergalactic (a star cast out of every galaxy). The zone row sets:

| Effect | Reader |
|---|---|
| radiation | the star's radiation (10.1), and through it mutation pressure and the disease load of its worlds |
| metallicity | ore yield and the signature minerals of its worlds (rare metals in metal-rich zones) |
| star density | sky event weight (more neighbours, more omens and nearby supernovae), eclipse weight |
| life capacity | the galactic habitable zone: a multiplier on the life capacity of its worlds |
| leak | per-epoch leak of its worlds (the core and the rim of some fantasy types) |
| travel | route danger and duration inside the galaxy |

#### Galactic structures (owned records)

`galactic_structures` rows (owned by the galaxy, shown in its entry and on its map):

- **Real kinds:** spiral arm, bar, bulge, core (the central black hole), halo, emission nebula, reflection nebula, dark nebula, planetary nebula, supernova remnant, stellar nursery, open cluster, globular cluster, stellar stream, dust lane, superbubble.
- **Fantasy kinds:** star graveyard, ley spiral (a lane of magic), sealed vault, god's forge, drift of dead light, singing nebula, rift scar.

Each kind row gives effects on the stars inside it and on their worlds: star birth (nurseries, emission nebulae), hiding (dark nebulae and dust lanes lower discovery and astronomy), old metal-poor stars (globular clusters), radiation and star metal (remnants), magic density (ley spirals), leak (rift scars), route speed and danger through it. A star belongs to at most one structure (`structure_id`). Structures have `x`, `y`, `radius`, `intensity` 0–100 and an end epoch.

#### Behaviours

1. **Star formation:** each epoch, nurseries and emission nebulae bear new stars by the galaxy's star formation and the structure's intensity. The new stars are unclaimed and appear for sons to take (hang a world, become patron).
2. **Galactic aging:** star formation falls with age, metallicity rises with every supernova, and old galaxies redden (more old stars, fewer nurseries). A dying galaxy's stars enter their late stages faster (10.1).
3. **Mergers:** two galaxies of one cluster can drift into each other. The merge progresses each epoch; during it star formation bursts, arms are disrupted (structures end or move), routes between their worlds shorten, and at 100 the smaller galaxy is absorbed (its stars and structures move into the larger, which may change type to peculiar, then elliptical).
4. **Nucleus:** an active nucleus or quasar raises the radiation of the core and bulge zones. An outburst is a galactic event.
5. **Galactic events** (`galactic_events`, each with a start, an end and an intensity): core outburst, gamma-ray burst (worlds within its reach lose fertility and biosphere health, species face extinction checks), starburst, tidal stripping (stars thrown into a stream or out of the galaxy), merger begun or completed, hypervelocity star (a star is flung into the intergalactic zone), nebula collapse (a new nursery), galactic dimming, and the fantasy events awakening (a living galaxy stirs), shrouding (a veiled galaxy hides) and severing (a shattered galaxy splits). Events act through modifiers on everything inside their reach.
6. **Patrons:** a son may become a galaxy's patron. It gains `galaxies.patron_essence` per epoch for each world in the galaxy that worships it, and a Star, Sun, Light or Sky patron raises the galaxy's star formation, while a Death, Ash or Shadow patron lowers it.

#### Tables and rules

- **Tables:** `galaxies` (node), `galactic_structures`, `galactic_events`; stars gain `galaxy_id`, `structure_id`, `galactic_zone`.
- **Rules namespaces:** `galaxy_types`, `galactic_structures`, `galactic_zones`, `galaxies` (formation, mergers, events).

### 10.11 Cluster (new node kind)

Galaxies gather into groups and clusters, and those into superclusters, filaments and walls around voids: the cosmic web.

#### Attributes

- `cluster_kind`, with real and fantasy kinds:
  - **Real:** galaxy group, local group, poor cluster, rich cluster, supercluster, filament, wall, void.
  - **Fantasy:** crown cluster (one power rules it), drowned cluster (lost to a dimension), forge cluster (built by gods), dream cluster, mirror cluster.
- `parent_cluster_id` (a group inside a supercluster, a cluster on a filament) or `dimension_id` (a top cluster; one of the two).
- `x`, `y` (its place in the dimension's web), `radius`, `medium_heat` 0–100 (the hot gas between its galaxies: travel danger and the stripping of passing galaxies), `expansion` (drift per epoch between top clusters: inter-cluster routes lengthen), `discovery`.

#### Behaviours

1. **Dominance:** the largest galaxy of a cluster is its central galaxy. It pulls the others into mergers over epochs (merger chance by distance and mass).
2. **Medium:** a hot medium strips gas from galaxies that fall through it (their star formation falls).
3. **Expansion:** top clusters drift apart. Routes between them lengthen by `expansion`, unless a god's bridge or a gate holds them.
4. **Voids** hold few galaxies and are the most dangerous and lonely crossings; some fantasy natures (leak, sanity) gather there.

#### Tables and rules

- **Tables:** `galaxy_clusters` (node).
- **Rules namespace:** `cluster_kinds`, `clusters`.

### 10.12 Intergalactic and intercluster travel and trade

**Current.** Routes join two worlds with a method, a duration and a danger. Nothing knows how far apart the worlds lie.

- **Route scope** is derived from the endpoints' placement: system (same star), stellar (same galaxy), galactic (a galaxy and its satellites in one group), intergalactic (two galaxies of one cluster), intercluster (two clusters), interdimensional (two dimensions). Scope multiplies duration, danger and provision cost (`cosmography.scope_*`), and sets the news delay of rumours carried along it.
- **Methods by reach:** each travel method has a maximum scope (a light sail or a slingshot stays inside a galaxy; a cosmic mount reaches the cluster; ancient gates, space folds and divine bridges reach any scope inside one dimension; dream journeys and the river of the dead cross dimensions). New methods: **void ark** (a generation ship for intergalactic and intercluster crossings: very long, carries whole cohorts, needs the highest sky-sailing knowledge), **galactic gate** (a gate pair between galaxies, built by gods or ancient makers), **filament lane** (a natural road along a cluster filament, open to cosmic mounts and arks), **dimensional rift** (a passage through a rift, 10.14) and **planar door** (a stable door between dimensions, made by a rite or a god).
- **Trade between worlds:** routes carry goods. Each epoch, the markets (6.4) of two worlds joined by an open route exchange surplus for deficit, up to the route's capacity, at a cost that grows with scope. Traffic is recorded on the route, the toll goes to the toll controller, and piracy takes a share. Goods found only in some galaxies, structures or dimensions (star metal from remnants, nebula salts and essences of planes, through the signature minerals of their worlds) make long routes worth their danger.
- **Cosmic distances in the chronicle:** journeys report the scope crossed, and the arrival of a void ark from another galaxy is a founding event for its colony.

#### Rules

- **Rules namespace:** `cosmography` (scope multipliers, method reach, trade costs, news delay).

### 10.13 Dimension (new node kind)

The cosmos holds several dimensions. Each is a whole layer of existence with its own clusters, galaxies, stars and worlds, or a smaller plane that holds worlds or nothing but its own nature. The **prime dimension** is where every existing cosmos already lies.

#### Attributes

- `dimension_kind` (typed effects table), with real and fantasy kinds:
  - **Real (from physics):** prime, parallel (a sibling with its own history), mirror (inverted), pocket (small, inside another), bubble universe, brane, higher-dimensional, antimatter, quantum branch, time-reversed, compactified (folded small).
  - **Fantasy:** astral, ethereal, dream, shadow, spirit, fey, elemental (with an `element` of fire, water, earth, air, void or another typed element), celestial (a heaven), infernal, abyssal, limbo, far realm, clockwork (order), chaos, underworld, divine domain (one god's plane), void between.
- `parent_dimension_id` (a pocket, branch or bubble inside or beside another).
- `veil` 0–100 (how thick the boundary to the others is; 0 is open), `stability` 0–100, `time_factor` (how fast time runs against the prime), `magic` 0–100 (magic density of everything inside it), `hostility` 0–100 (danger to visitors), `sanity_drain`, `leak` 0–100, `causality` (strict, loose, broken), `discovery`.
- `ruler_node_id` (a son, a foreign god, an outer being, a cosmic being or none), `natural_laws` (laws that hold across the whole dimension, 9.5, read by the law book as a dimension scope).

The dimension kind row gives the defaults and the effects:

| Effect | Reader |
|---|---|
| time factor | multiplies the time factor of every world inside it (years per epoch, aging) |
| magic | added to the magic density of every region inside it; rite power (8.6) |
| hostility | danger of its worlds and of journeys into it |
| sanity drain | per-epoch sanity loss of mortals inside it and of visitors |
| leak | per-epoch leak of its worlds |
| veil | the default veil |
| life capacity | multiplier on the life capacity of its worlds |
| laws | the natural laws it holds by its nature (the dead speak in the underworld, dreams are real in the dream dimension) |

#### Behaviours

1. **Nested placement:** a dimension's clusters, galaxies and worlds read its effects through the placement chain. A world's effective time factor, magic, danger, leak and sanity drain include the dimension's.
2. **Veils:** veils thin with open rifts, incursions, leak and rites, and thicken with sealing rites, wards and time. A thin veil raises the chance of rifts and crossings. A veil at 0 opens a convergence.
3. **Dimensional events** (`dimensional_events`): incursion (beings cross into a world), convergence (two dimensions overlap: their veils open, beings and laws cross, time runs at the mean of both), veil thinning, planar alignment (every veil thins for a span), bleed (a dimension's nature seeps into a world: magic, time factor, danger and leak move toward the dimension's), schism (a branch dimension splits off), collapse (a pocket or bubble dimension collapses: its worlds are thrown into the parent or lost), echo (a mirror counterpart of a mortal or a people appears). Events act through modifiers and end at their end epoch.
4. **Rulers:** a dimension's ruler gains essence or power from it and can close or open its veil. Sons may rule a divine domain dimension of their own.
5. **Faith and afterlife:** an underworld, a celestial or an infernal dimension can host afterlife strata (3.3), so the souls of a world go to a real place.

#### Tables and rules

- **Tables:** `dimensions` (node); worlds without a star gain `galaxy_id` or `dimension_id`; galaxies and clusters gain `dimension_id`.
- **Rules namespaces:** `dimension_kinds`, `dimensions` (veils, events, convergence).

### 10.14 Rifts

A rift is a tear between a region of a world and another dimension.

- Attributes: `world_id`, `region_entity_id`, `dimension_id`, `target_world_id` (a world on the far side, if any), `size` 0–100, `stability` 0–100, `state` (opening, open, closing, sealed, collapsed), `cause` (rite backlash, leak peak, convergence, god, being, phenomenon, Creator), `opened_by_node_id`, `opened_epoch`, `sealed_epoch`, `route_id`.
- **Effects:** the region gains leak and magic by size; it becomes a danger source; the dimension's veil thins; beings of the far side may cross (incursions); phenomena (10.6) form at large rifts (leak wounds).
- **Passage:** an open rift with a target world opens a dimensional rift route between the two worlds. The route closes when the rift seals or collapses.
- **Life cycle:** rifts grow when unstable and shrink when stable; sealing rites, wards, gods and the Creator seal them; a rift whose stability falls to 0 collapses (a disaster in the region).

**Tables:** `rifts`. **Rules namespace:** `rifts`.

### 10.15 Cosmic being (new entity type)

Beings that live at the scale of galaxies or between dimensions. They are distinct from outer beings (9.6), which feed from beyond: a cosmic being is a native of a dimension or of the great dark, with a home, a reach and an aim.

#### Attributes

- `being_kind`, with real-flavoured and fantasy kinds: planar native, dimension walker, rift spawn, higher-dimensional entity, star eater, nebula mind, galactic leviathan, void shepherd, echo (a mirror double), time wanderer, cosmic titan, veil warden, plane sovereign, swarm intelligence, living constellation.
- `home_dimension_id`, `galaxy_id` (where it roams), `scale` (world, system, galaxy, cluster, dimension), `might` 0–100, `phase` (dormant, roaming, manifest, incursion, bound, banished), `agenda` (feed, explore, conquer, guard, trade, flee, seek worship, unmake, mend), `bound_by_node_id`, `rift_id`, `target_world_id`, `manifest_epochs`.

#### Behaviours

1. **Roaming and crossing:** roaming beings move between the galaxies of their scale and cross into other dimensions where veils are thin or rifts are open.
2. **Agenda acts:** feeders dim stars (star eaters) or drain magic (nebula minds); conquerors make incursions (a beast attack at the scale of a region, with armies answering); guards strengthen veils; traders carry goods along routes; worship-seekers draw cults (they can be a community's patron through the cult machinery, like outer beings); menders repair stars and veils; unmakers raise doom.
3. **Binding and banishment:** rites, sons, foreign gods and the Creator bind beings (they serve their binder) or banish them to their home dimension.
4. **Rulers:** a plane sovereign can rule a dimension (10.13).
5. **Echoes:** an echo is bound to a mortal it mirrors; it can take that mortal's place (an impostor, 5.10) or befriend them.

#### Tables and rules

- **Tables:** `cosmic_being_profiles`.
- **Rules namespace:** `cosmic_beings`.

### 10.16 Interconnections of the cosmic scales

- **Placement reaches every system:** world physics, temperature (through the star), life capacity, radiation, leak, magic, time factor, sanity and danger all read the placement chain (dimension → cluster → galaxy → zone and structure → star → world).
- **Gods:** a dimension's ruler shapes it by domain: Dream, Shadow, Madness and Border rulers thin its veil or thicken it (Border thickens), Time rulers steady its stability, Death and Sleep rulers draw souls to its strata. Galaxy patrons act on star formation (10.10). Sons have tools to open and seal rifts, call and banish cosmic beings, and contain phenomena. The Creator's attention (9.2) and every lever reach every scale.
- **Faith:** stars, galaxies and dimensions can be worshipped (sun cults, sky cults, cults of a plane), with piety tracking the object's state.
- **Doom:** open rifts, incursions, convergences, gamma-ray bursts and unmaking beings are typed doom contributors (10.8). Dimensional collapse is an apocalypse variant.
- **Book and Codex:** the atlas of the heavens is ordered by the scale ladder, with every dimension, cluster, galaxy, structure, event, rift and being in its place.

### 10.9 Cosmic physics (derived, second pass)

All cosmic values that the first pass stored are now **derived** from a small set of physical inputs. Stored values become caches, and divine or player overrides become modifiers (F9).

**Inputs per star:** mass, metallicity, age, and system membership (star systems, 2T.6).

**Inputs per world:**

- orbital elements: semi-major axis, eccentricity, inclination, argument, and the parent (star or world for moons);
- physical inputs: mass, radius, a composition mix (iron, rock, ice, gas, exotic), rotation period, axial tilt;
- atmosphere composition (fractions of nitrogen, oxygen, carbon dioxide, methane, water vapour, exotic gases) and surface pressure;
- albedo, magnetosphere strength, tectonic activity, volcanism, the hydrosphere and cryosphere fractions;
- a biochemistry class.

**Derived values:**

| Value | Derivation |
|---|---|
| Year length | from the semi-major axis and the system mass (a Kepler analogue). Feeds F2.2 and the chronicle year arithmetic per world (the existing `time_factor` remains as the divine time-flow modifier, separate from the orbital year) |
| Day length | from the rotation; tidal locking when the tidal lock timescale passes the world age |
| Seasons | from the axial tilt and the eccentricity (eccentric orbits give a global season) |
| Insolation | luminosity / distance², through the year (eccentricity) |
| Surface temperature | insolation × (1 − albedo) + greenhouse (from the atmosphere composition and pressure) + tidal heating (moons) + internal heat (volcanism). Feeds the regional temperature bands (F2.1) |
| Habitable band | per system, for liquid water at a standard pressure, shifting with star evolution |
| Gravity | from mass and radius (replacing the three-level enum as the source; the enum remains as a derived band) |
| Escape velocity | atmosphere retention over epochs (small hot worlds lose their air: atmosphere decay) |
| Radiation | the star type and flares against the magnetosphere; feeds mutation (3.2) and disease_resistance |
| Tides | moon masses and distances; feed coast passability and flood chance (F2.2) |
| Rings | bodies inside the Roche limit break up into rings (a moon destroyed by a son's act becomes a ring) |
| Eclipses and transits | from geometry (moon size, distance, orbital inclination), replacing the random eclipse sky event with a computed calendar plus a divine override |
| Auroras | from the magnetosphere and the solar activity |

**Impacts:**

- Bodies in crossing orbits (asteroid fields, periodic comets, rogue worlds) have an impact probability per sampled year.
- Impacts create craters (place kind `crater`), regional devastation, an **impact winter** (global temperature − for sampled years: harvest failures, a notable year, extinction chances by species tolerance), new materials (star metal) and legends.
- Sons can deflect or call impacts (a cosmic power), and astronomers can predict them (the eclipse-prediction technique extends to orbits), which raises warning time and lets polities prepare: migration, granaries, prayer.

**Climate dynamics (planetary):**

- Ice–albedo feedback: more ice raises albedo, which cools further (Loop R) until stopped by volcanism or the star's brightening.
- Greenhouse changes from volcanism (carbon dioxide up), large-scale burning (land use), and divine acts.
- Sea level rises and falls with the cryosphere. Coastal regions flood or emerge, and settlements on coasts move.
- The world-level climate eras of the first pass become **emergent states** of these dynamics, with a divine imposition still possible as a modifier.

**Terraforming:** sons (essence) and advanced polities (techniques of the cosmic branches) can shift the atmosphere composition, the hydrosphere (comet water) and albedo over epochs. Native life with incompatible biochemistry suffers, which is an ethics question.

**Star systems and cosmic features:**

- **Binary systems:** worlds orbit one star (S-type) or both (P-type). Insolation varies with the companions' phases, giving double seasons and double-sun eclipses. The habitable band is computed from both stars.
- **Nebulae** and the other galactic structures are records of their galaxy (10.10); this pass derives their effects from the physical inputs.
- **Black holes:** route slingshots with time dilation (the existing `time_factor` analogue for travellers: they arrive younger than their kin), and devouring of nearby bodies.
- **Asteroid fields:** mining for materials (vessels with miners), impacts, hiding places for void pirates.
- **Wormholes:** natural routes with instability windows.
- **Rogue worlds:** dark wanderers with no star (frozen, but possibly inhabited by underground or void life). Their pass through systems perturbs orbits and causes impacts.

**Life classes per world:** biochemistry, complexity (none, microbial, simple, complex, sapient) and environment (marine, terrestrial, aerial, subterranean). They gate which species and peoples can arise natively (the existing life seeding reads them) and which can survive transplanting.

**Galactic structure** is placed by 10.10 (galaxies, zones, structures) and 10.11 (clusters and voids). This pass derives star positions inside the arms from the orbital model. Light-delay of news (F21) between distant systems follows route durations and the route scope (10.12).

**Tables:** `star_physics`, `world_physics`, `star_systems`, `cosmic_features`, `impact_events`, `world_life`.

**Rules namespaces:** `orbits`, `stellar_evolution`, `planetary_climate`, `impacts`, `terraforming`, `cosmic_features`.

#### Reference pass 3 (R12)

**Biogeochemical cycles** (SimEarth-style) at world scale: the carbon (or world-type analogue), water and nutrient cycles are tracked as stocks and flows.

- **Carbon:** volcanoes, burning (land use), respiration and decay add to it; forests, oceans and rock weathering take it up. It feeds the greenhouse term (10.9).
- **Water:** evaporation, precipitation, ice and river discharge feed rainfall and sea level.
- **Nutrients:** soils, erosion, river deposition and volcanic ash feed soil fertility (F2.1).

Biosphere activity (3.2 trophic flows, land use) closes the cycles. Large disturbances (a world-wide war burning forests, a son's eternal summer) therefore have planetary consequences over epochs, and gods and peoples share one planetary system.

---

## Part I. Interconnection

### I.1 Interconnection registry

Every coupling in this spec is registered once in `engine/interconnect/registry.py` as `Edge(source_subsystem, target_subsystem, carrier, rule_key, kind)`, where kind is modifier, rule_switch, flow or trigger. The modifier bus (F9) and the incident log (F10) reference these edges. The registry:

- drives the depth metric C (J.7);
- generates the matrix below for the docs;
- lets a test assert that every edge has a reader and a writer;
- feeds the UI "what affects this" panel.

### I.2 Subsystem matrix (rows affect columns)

Legend: ● strong typed coupling, ○ weak or conditional, and "·" none. **Bold** marks cells that are empty today and filled by this spec.

| from ↓ / to → | Body | Mind | Demog. | Economy | Polity | War | Faith | Knowl. | Culture | Lang. | Ecology | Env. | Gods | Cosmos |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Body (injury, disease)** | — | **●** stress, traits | **●** cohorts | **●** labour | **●** legitimacy | **●** capacities | **○** saints, marks | **●** scholars lost | **●** readings, scar rites | · | **○** hosts | · | **○** divine wounds | · |
| **Mind (values, traits, memory)** | **○** break events | — | **●** fertility | **○** consumption | **●** decisions | **●** tactics, morale | **●** conversion | **○** research | **●** drift | **○** prestige | · | · | **●** standing | · |
| **Demography (cohorts)** | ○ | ○ | — | **●** labour | **●** levy, tax | **●** levy | ○ | **●** practitioners | ○ | **●** speakers | **●** land use | **●** disease load | ● faith | · |
| **Economy** | **●** prosthetics, food | **●** needs | **●** births | — | **●** treasury | **●** equipment, supply | **●** tithes | **○** funding | **○** patronage | ○ | **●** hunting, yields | **●** land use | ○ | ○ cosmic market |
| **Polity / law** | **●** punishments | **●** loyalty | **●** levy | **●** taxes, tolls | — | **●** war aims | **●** state religion | **○** schools | **●** law vs custom | **○** official tongue | ○ | ○ | ○ divine kingship | ○ |
| **War** | **●** injuries | **●** memories, traits | **●** deaths, maimed | **●** scars, loot, debt | **●** legitimacy, succession | — | **●** zeal | **●** tactics, libraries | **●** drift, legends | **●** captives, hostages | **○** war beasts | **●** scars | **●** domain activity | ○ |
| **Faith (cults, doctrine)** | **●** sacred suffering, purity | **●** values | **○** celibacy | **●** tithes | **●** legitimacy | **●** holy war | — | **●** monastic learning | **●** traditions | **●** liturgy | **○** sacred species | · | **●** standing | · |
| **Knowledge (techniques)** | **●** medicine | ○ | **●** health | **●** chains | **●** administration | **●** units, engines | ○ | — | ○ | **●** writing | **●** domestication | **●** irrigation | ○ | **●** travel |
| **Culture (legend, tradition, art, ideology)** | **●** scar rites | **●** value pressure | **●** marriage customs | **●** feasts | **●** legitimacy, revolts | **●** weariness, morale | **●** syncretism | **●** books | — | **●** prestige | ○ totems | · | **●** fame | · |
| **Language** | · | ○ | ○ | **●** trade cost | **●** administration | **●** cohesion | **●** preaching | **●** diffusion | **●** distortion | — | · | · | ○ | · |
| **Ecology (species, beasts)** | **●** bites, disease | **●** terror | **●** food | **●** yields, pests | ○ | **●** mounts, beasts | **●** sacred animals | ○ | **●** totems, legends | · | — | **●** land | ○ Hunt domain | ○ stowaways |
| **Environment (terrain, weather, season)** | **●** frostbite, heat | **●** omens | **●** harvest | **●** harvest, routes | ○ | **●** terrain, weather | **○** omens | ○ need | **●** notable years | · | **●** habitat | — | ○ | · |
| **Gods (sons, foreign, creator)** | **●** marks, wounds, healing | **●** standing | **●** fertility | **●** blessings | **●** divine right | **●** interventions | **●** doctrine seeding | ○ revelation | ○ | ○ | ○ | **●** weather rites | — | ● |
| **Cosmos (stars, worlds, phenomena, leak)** | **●** radiation, void | **●** sanity | **●** aging | **○** cosmic trade | ○ | **●** gravity, eclipses | **●** star cults | ○ | **●** omens | · | **●** mutation | **●** seasons, climate | ● | — |

Today about 45 cells carry a coupling and most of them are "+k" constants. With this spec, about 160 cells are typed couplings, and most bold cells carry several rules each.

### I.3 Feedback loops catalogue

Each loop is a cycle of edges in the registry. The CI loop finder lists all cycles of length ≤ 6. These are the designed ones:

| Id | Type | Loop | Brake or accelerator |
|---|---|---|---|
| L1 | B | War casualties → maimed cohort → visible weariness → peace pressure → fewer wars | the martial value weakens it |
| L2 | R | Victory → martial values → bigger levies → more victories | overextension (L3) |
| L3 | B | Conquest → territory > administration → provincial autonomy → secession → smaller realm | literacy and roads raise the limit |
| L4 | R | Deforestation → less rainfall → desertification → famine → clearing more land | rewilding when abandoned |
| L5 | B | Overfarming → soil decline → famine → migration → rewilding | — |
| L6 | R | Trade → wealth → luxury demand → more trade | bandits and tolls (L7) |
| L7 | B | High tolls → traffic diverts → toll revenue falls | — |
| L8 | R | Killing → killed_kin memory → vendetta → killing | wergild, intermarriage, mediation, memory decay |
| L9 | R | Persecution → martyr memory → zeal → conversion → bigger cult | prosperity lowers zeal |
| L10 | B | Prosperity → comfort → zeal falls → cult shrinks | crises re-raise zeal |
| L11 | R | Prophecy → believers act → condition met → certainty of the next prophecy rises | failures mock the seer |
| L12 | B | Disease endemic → locals immune → invaders die → conquest fails | mutation bypasses immunity |
| L13 | R | Leak → horror → godlessness → leak | temples, priests |
| L14 | B | God neglect → conversion away → existence falls → the son acts more (desperate goals) → standing recovers | — |
| L15 | R | Injured ruler → legitimacy falls → faction challenge → civil war → more injured rulers | strong succession law, regency |
| L16 | B | Extinction of prey → predators starve → predation falls → prey recovers | — |
| L17 | R | A legend of a cursed line → house prestige falls → fewer marriages → house weakens → confirms the legend | a heroic deed rewrites it |
| L18 | B | Debasement → inflation → merchant opinion falls → trade falls → tax falls → the treasury must recoin honestly | — |
| L19 | R | Literacy → administration → bigger realm → schools → literacy | the scribe-caste monopoly (logographic) brakes it |
| L20 | B | Wonder envy → neighbours' relation falls → war → wonder sacked | — |
| L21 | R | Weather rite in war → victory → the mages' faction grows → more weather rites → leak and backlash | backlash phenomena |
| L22 | B | Child heir → regency → regent ambition → usurpation risk → laws for regency councils | — |

### I.4 End-to-end emergence scenarios (acceptance stories)

These stories are acceptance tests: a seeded multi-epoch engine run (LLM off) must be able to produce each chain. J.6 describes the test.

1. **The Winter Campaign.** A steppe polity with horse archers invades a mountain kingdom in a late-autumn campaign season. A blizzard draw (F2.3), mountain terrain (cavalry ×0.3) and long supply lines (attrition) bleed the invaders. A chokepoint battle (defender ×1.5) is won by pikemen. The invading khan loses a hand to a pike (injury). His legitimacy falls (wholeness reading), so his brother presses a claim and a succession war follows. The mountain kingdom's martial value rises and a pass-guard tradition forms.
2. **The Iron Famine.** A trading city's forests are cleared for farms (land use). Fuel shortage cuts iron refining (chain), so army equipment declines. A rival with skysteel conquers the city, and its scribes die in the sack, so the library is unstaffed and the city's medicine level falls (practitioners lost). The next plague kills more, and the city becomes a ruin. Its legend, "the city that ate its forests", spreads as a moral (nature value +) among the neighbours, who pass a forest law.
3. **The Silver Hand.** A hero loses an arm to a beast (bite → infection → amputation by a surgeon). The house smith forges a silver prosthesis (masterwork; renown from deeds). The hero slays the beast with it. The prosthesis becomes an heirloom and regalia when the hero's house takes the throne. A usurper later steals it to legitimise himself, and a war of cause `claim` is fought over a hand.
4. **The Plague Saint.** An endemic disease in a marsh region gives locals immunity. A missionary cult of the Plague son preaches there; its sacred-suffering tenet honours the scarred survivors. Invaders without immunity die besieging the marsh city (L12). The cult's zeal rises and its saint's relic (bones) heals by chance, so the faith spreads along trade routes. Its Death-domain rival son loses standing, and a divine grudge war between their peoples follows.
5. **The Tongueless Law.** A cruel penal law cuts out blasphemers' tongues. An ideology of tolerance spreads among scribes through books (writing still works for the mutilated). Martyr memories accumulate. The scribe faction lobbies, the council votes, and the law is repealed. A tradition of silent prayer forms among the faithful, commemorating the tongueless.


### I.5 Second-pass couplings

New edges added by F13–F30 and the reference passes, beyond matrix I.2. Each edge below is a registered edge (I.1).

| From | To | Carrier |
|---|---|---|
| Mind (facets, emotions) | War | commander initiative, morale reactions, break events in battle, tactic weights |
| Mind (preferences) | Economy | luxury demand, gift value, trade goods choice |
| Mind (ethics) | Polity | legitimacy, tyranny, law pressure, coalition threat |
| Mind (dreams, wants) | Demography | marriage choices, migration, career choice |
| Relationships | Polity | court factions, council diligence, succession support, schemes' recruitment |
| Secrets and hooks | Polity, War | forced votes, abdications, betrayals, double agents |
| Communication | War, Diplomacy | delayed orders and treaties, forged declarations, misread clauses |
| Belief state | Every decision | wrong-information choices; deception |
| Material physics | War, Economy | penetration, fire spread, forging feasibility |
| Tissue layers | Body, War | bleeding deaths, unconsciousness captures, nerve damage careers |
| Production methods | Economy, Society | method transitions, unemployment, pollution, guild politics |
| Energy | Economy | the industrial geography of rivers and winds; heat survival |
| Pollution | Health, Ecology | disease load, fertility, fisheries |
| Gatherings | Relationships, Diplomacy | marriages, schemes, summit treaties, tournament injuries |
| Genetics | Houses, Health | inbreeding conditions, recognisable heirs, exposed parentage |
| Storyteller | Spontaneous rates | pacing of disruptions and recoveries |
| Conservation ledger | Tests | invariant checks |
| Households and dwellings | Mind, Economy | lifestyle needs, care of the maimed, inheritance |
| Effect packages | Body, Mind, Faith | curses, venoms, transformations, desecration |
| Titles | Polity, War | de jure claims, personal unions, partition |
| Art forms | Culture | artwork renown, cohesion, liturgy |
| Theories | Knowledge, Health | treatment success, navigation, rite reliability, paradigm conflicts with cults |
| Geology and strata | Economy, Ecology | mining depth, cave species and monsters, aquifers |
| Region alignment | Ecology, Faith | evil and blessed lands, undead, healing springs |
| Cosmic physics | Environment | derived seasons, temperatures, tides, eclipses, impacts |

With these, the registered couplings rise from about 160 cells (first pass) to about **230 edge kinds** spread across the 14 subsystems of I.2 plus 6 new subsystems:

- Mind-social (relationships, reputation)
- Intrigue (schemes, secrets)
- Communication (messages, public opinion)
- Material physics
- Household
- Physics of the cosmos

### I.6 Second-pass feedback loops

| Id | Type | Loop | Brake or accelerator |
|---|---|---|---|
| L23 | R | Inbreeding to hold claims → heritable conditions → weak heirs → claims contested → more inbreeding to secure them | exogamy laws, ethics |
| L24 | B | Mechanised production (mills) → unemployment → unrest → guild riots against mills → slower adoption | new jobs from growth |
| L25 | R | False theory endorsed by a cult → bad treatments → more deaths → more prayer → stronger cult | anomalies → paradigm shift |
| L26 | R | Speculation → hoarding → famine prices → riots → state granaries opened → merchants ruined → less speculation | B-closure through ruin |
| L27 | R | Threat from conquests → coalition → war → more conquests or a collapse | coalition victory |
| L28 | B | Tyranny → factions → concessions → less tyranny | dread suppression delays it |
| L29 | R | Pollution → disease → fewer workers → more coal-hungry methods per worker → more pollution | rewilding, laws |
| L30 | B | Ice–albedo cooling → glaciers → volcanism exposure unchanged → greenhouse rises slowly → thaw | — |
| L31 | R | Secrets learned at gatherings → hooks → forced marriages → more gatherings of the hooked houses | exposure scandals |
| L32 | B | Delayed messages → wars that peace would have prevented → war weariness → faster courier networks (postal technique) | — |
| L33 | R | Art form prestige → more artists → more renowned works → higher prestige | form exhaustion via the tired-motif analogue |
| L34 | B | Storyteller: low tension → raised disruptions → crisis → recovery boost | profile |
| L35 | R | Desecration → curse (werebeast) → bitten victims → more cursed → hunts and purges → persecution memories | cure rites |
| L36 | B | Dwelling squalor → disease → deaths → fewer people per dwelling → lower squalor | — |
| L37 | R | Deep mining → caverns opened → beasts emerge → walls and armies → more ore for arms → deeper mining | sealing the deep |
| L38 | B | Great person concentration in one realm → era score lead → envy → wars that kill scholars | — |
| L39 | R | Censorship → black-market books → secret circles → movements → harsher censorship | revolution or repeal |
| L40 | B | Impact predicted → granaries and migration → fewer deaths → astronomers' prestige → more observatories → better prediction | — |

### I.7 Second-pass acceptance stories

6. **The Forged Letter.** A spymaster's agent intercepts a peace offer (F21), forges a declaration of war in the sender's hand (a writing-skill check against familiarity), and the recipient's belief state (F22) holds the forgery as true. A war starts between parties who both wanted peace. A captured courier later exposes the forgery (an investigation), which leads to the spymaster's trial, a scandal, a coalition against the forger's realm, and a legend of "the war of the false letter".
7. **The Humours and the Plague.** The dominant medical theory (bleeding cures fever) raises plague mortality. An anomaly accumulates: quarantined monasteries survive. A heterodox physician with the contagion theory gains adherents among scholars. The cult condemns it, and a heresy trial blinds him (G9 plain). His books spread through a black market, and a paradigm shift occurs a generation later, so mortality curves visibly fall.
8. **The Mill Riots.** A river town adopts water-frame mills (a production method transition). Weavers lose their jobs (unemployment) and their guild strikes, then riots and burns the mills (a fire, injuries). The lord's tyranny rises when he hangs the leaders. A weavers' movement becomes a party in a later assembly, and the mill law (a charter) is enacted after an enactment process with an obstruction phase.
9. **The Werewolf of the Grove.** A poacher desecrates a Hunt-son's grove (a desecration curse, F30) and turns at the full moon of the first moon (10.9 lunar calendar). Bites spread the curse. The village's fear (thoughts, F14) feeds a purge (event collection). An innocent hermit is burned (a wrongful conviction, F20/4.6 justice), which gives a ghost (a vengeful type). A cure rite is discovered by a healer through a research insight.
10. **The Comet Winter.** Astronomers of one polity predict a comet impact on a neighbour's world region (orbital elements, 10.9). The warning travels by envoys (delay, F21), but the neighbour's court distrusts the sender (trust, F18). The impact brings an impact winter: harvest failures in sampled years, a notable year, species extinctions by tolerance, and migrations into the predictor's lands. The predicting realm gains prestige and an observatory institution spreads.
11. **The Wedding Feast.** A summit-cum-wedding (F25) gathers three houses. Interactions produce an affair (a secret), a rival's scheme agent meets a disgruntled steward (scheme recruitment), and a tournament leaves the bride's brother with a crushed knee (F23 nerve damage: the end of his career as a knight → a new life dream as a scholar). A year later the affair's exposure breaks the marriage pact (a treaty breach) and starts a war.
12. **The Iron Seam Beneath.** A mountain people mines deeper for iron to arm against a coalition (L27 threat). It breaks into the second cavern layer (6.1 reference pass) and releases a procedurally generated crystal-scaled beast (3.3 reference pass). The beast's attacks devastate the mines. The people's art forms gain a lament form (7.5) and its legends a cycle (8.2 reference pass). Eventually a hero in skysteel (F23 materials) slays the beast, and its crystal scales enable a new production method (F24).

### I.8 Third-pass couplings

| From | To | Carrier |
|---|---|---|
| Dominion and scales (F31) | Economy, Health, War, Magic, Afterlife | scale modifier packages per region; rite cost; strata |
| Dominion | Faith, Belief state | missionary success; miracle misattribution |
| Collective behaviour (F32) | Polity, Settlement, Faith | riots, panics, revivals, lynchings, gate-openings in sieges |
| Historiography (F33) | Polity, Culture, War | legitimacy from founding myths; revisionism scandals; irredentist claims |
| Storylets (F34) | All | typed effects at dramatic junctures, chosen by agents or personalities |
| Social norms and volition (F35) | Mind-social | interaction choice, etiquette breaches, norm drift |
| Heroquests | Legends, Gods, Mortals | myth rewriting; boons; trapped souls |
| Mantling | Gods, Fate | new sons; replacement of gods |
| Belief shapes gods | Gods | aspect, manifestation and facet drift |
| Belief shapes worlds | Cosmos, Environment | alignment, terrain and world-type drift |
| Spell grammar and paradigms | Magic, Knowledge | rite design and reliability by theory correctness |
| Sound change and typology | Language, Diplomacy, Art | cognates, translation difficulty, poetry forms |
| Selection and niches | Ecology, Economy | trait evolution, extinctions, radiations, keystone services |
| Pathogen evolution and responses | Health, Economy, Polity | resistance, strains, border closures, cure races |
| Desirability and coverage | Settlement | housing evolution, class sorting, crime and fire |
| Caravans and fleets | Economy, Communication, Disease | cargo of goods, news, diseases and art |
| Legal typology and precedent | Law, Polity | case-law drift, appeals, inequality of justice |
| Ciphers and signal networks | Communication, War | interception value, delays |
| True names | Magic, Gods, Intrigue | binding, protection, hooks |
| Passions and conviction | Mind, War | inspirations and breaks; belief stability |
| Generations | Demography, Politics | formative beliefs; generational turnover |
| Diaspora networks | Migration, Economy, Diplomacy | chain migration, remittances, ties |
| Role norms | Careers, Succession, Mobilisation | eligibility by sex, age and class (culture-defined) |
| Biogeochemical cycles | Climate, Ecology, Economy | planetary feedback |

The registered edge kinds rise to about **300**.

### I.9 Third-pass feedback loops

| Id | Type | Loop | Brake or accelerator |
|---|---|---|---|
| L41 | R | Dominion → cheaper miracles → more belief → stronger dominion | rival dominion contests |
| L42 | R | Belief shapes god → god acts as believed → belief confirmed | the son's essence spent to resist |
| L43 | B | Heroquest deviations → myth changes → future questers on the new myth → divergent boons → schisms | orthodoxy |
| L44 | R | Treatment use → pathogen resistance → more deaths → more treatment | variolation, correct theories |
| L45 | R | Riot cascade → harsher policing → grievances → lower thresholds next time | concessions, amnesties |
| L46 | B | Gentrification → poor pushed out → service workers scarce → wages rise → partial return | — |
| L47 | R | Revisionist history → legitimacy → stability → the revision becomes the only surviving account | old texts found in excavations |
| L48 | B | Precedent drift → harsh case law → unrest → appeals overturn | — |
| L49 | R | Paranoid mole hunts → loyal officers purged → real moles thrive → more paranoia | a competent new spymaster |
| L50 | B | Overhunting the keystone species → service loss → famine → hunting pressure falls | extinction is the failure mode |
| L51 | R | Chain migration → diaspora → stronger pull → more migration | host backlash (xenophobia) |
| L52 | R | Belief-shaped world drifts toward a Death god's nature → death scale stronger → more death belief | rival dominion |

### I.10 Third-pass acceptance stories

13. **The Lion-Headed God.** A people's legend describes the War son as lion-headed. Belief pull (9.1 reference pass 3) shapes its manifestation over epochs. A heroquest re-enacting "the lion's descent" succeeds with a deviation, and the people's myth changes. The son's facets drift toward wrath. A rival people that believes the same son is a peacemaker sees an "apostasy" of their god and schisms.
14. **The Plague That Learned.** A city's physicians bleed patients (a false theory). Treatment use selects a hardier strain. Ports close (trade collapse, a riot cascade). A merchant carrier slips out, and the strain reaches a diaspora quarter abroad. A rival university with the contagion theory wins the cure race, sells the cure for a treaty clause, and gains a great person.
15. **The Pass of the Drowned Valley.** Two sons contest a valley's dominion. One floods the valley (divine hydrology) to drown the rival's temple, which cuts a trade route and shifts the river downstream. A downstream people loses its fields and migrates along its diaspora network. The flooded temple becomes a heroquest site.
16. **The Revised King.** A usurper's dynasty rewrites the chronicles (revisionism) and strikes the old king's name (damnatio memoriae). A century later, an excavation finds an old inscription (a bilingual stele that also advances a decipherment). The scandal lowers legitimacy, a movement of the "true line" rises, and a generational turnover lets it win an assembly vote to restore the old title.
17. **The Cipher of the Salt Road.** A spymaster's codebreakers break a rival's cipher. For three epochs every message on the salt road's signal towers is read. A double agent feeds forged replies. When the break is discovered (a mole hunt with false positives purges loyal officers), the rival's court collapses into paranoia (L49) just as a coalition (L27) forms.
18. **The Death-Shaped World.** A Death son's dominion spreads over a small world through temples and a throne of power. Its scales (growth–death) darken the land. Belief-shaping pulls the world type toward corpse-world, the fauna under selection grows carrion-adapted, and the afterlife strata of its realm swell. The Life son's worshippers mount a group heroquest to renew the land, while the council debates the office of Lord of the Dead.

### I.11 Fourth-pass couplings

| From | To | Carrier |
|---|---|---|
| Structural-demographic variables (F37) | Polity, Factions, Collective behaviour, Storyteller | PSI-weighted revolt, coup and riot rates; counter-elite leaders |
| Asabiyya | War, Assimilation, Polity | cohesion, morale, frontier unification, dynastic softening |
| Challenge index | Knowledge, Institutions | boosts in the response band |
| Long plans | Every subsystem a plan targets | multi-generation steering |
| Reciprocity (F38) | Diplomacy, Households, Gods | gift debts, competitive giving, ceremonial circuits, sacrifice obligations |
| Kinship systems | Succession, Claims, Marriage, Houses | descent lines, alliance exchange, inheritance |
| Reproductive systems | Demography, Role norms, Law | sex systems shaping society |
| Selectorate and coalition | Economy (public against private goods), Corruption, Coups | spending mix, purges |
| Legitimacy types | Succession crises | routinisation of charisma |
| Time horizon | Taxation, Investment | roving against stationary bandit extraction |
| Clientelism and power bases | Polity, War | patronage politics, overmighty subjects |
| von Thünen rings, central places | Land use, Settlement growth | spatial economy |
| Boserup and nutrients | Agriculture, Knowledge | intensification, salinisation |
| Commons and enclosure | Households, Migration, Movements | dispossession |
| Operational HQs and logistics networks | War | command range, culmination |
| Lanchester laws | Battle | concentration effects |
| Age-of-sail damage | Naval war | ship-level outcomes, prizes |
| Expeditions | Mind, Body | afflictions, virtues, quirks |
| Mysticism, millenarianism, theodicy | Faith, Movements, Gods | heterodoxy, mass action, crises |
| Believed against actual afterlife | Spirits, Doctrine | revelation shock, evidence |
| Genius loci and bureaucracy | Land use, Faith | place spirits and petitions |
| Emotion-fed gods | Divine economy, Mind | emotions as essence |
| Divination and prescience | Decisions | timing, forecast-driven acts, blind spots |
| Psychohistory | Long plans | statistical steering |
| Art markets, canon, forgery | Culture, Economy | prices, classics, scandals |
| Sports and circus factions | Politics, Collective behaviour | fandom-to-faction, riots |
| Examinations and credentials | Elites (F37), Careers | meritocracy, counter-elites |
| Constructs | Labour, War, Ruins | literal orders, rogue minds |
| Formation history | Cosmos physics | consistent systems |
| Cyclic ages | Doom, Legends, Arcs | echoes |
| Narrative arcs and drama manager (F36) | Storylets, Chronicle | arc beats, setups and payoffs |
| Labour regimes | Economy, War, Movements | corvée, peonage, slave markets, manumission |
| Disaster resilience | Disasters, Diplomacy | preparedness, aid, reconstruction |

The registered edge kinds rise to about **370**.

### I.12 Fourth-pass feedback loops

| Id | Type | Loop | Brake or accelerator |
|---|---|---|---|
| L53 | R | Elite overproduction → counter-elites → civil war → elite deaths → (B) fewer elites → stability | secular cycle |
| L54 | B | Population growth → falling wages → immiseration → famine and war → population falls → wages rise | Malthusian brake |
| L55 | R | Frontier conflict → asabiyya → conquest → luxury → asabiyya decays → a new frontier people conquers | Ibn Khaldun cycle |
| L56 | R | Small coalition → private goods → poverty → unrest → purges → smaller coalition | revolution |
| L57 | R | Insecure ruler → short horizon → plunder → weaker realm → more insecurity | stable succession |
| L58 | R | Competitive giving → prestige race → treasuries drained → ruin of one side | ruin |
| L59 | B | Irrigation → salinisation → yields fall → abandonment → recovery over centuries | drainage technique |
| L60 | R | Enclosure → dispossessed migrate to cities → cheap labour → more enclosure profit | movements, laws |
| L61 | R | Millenarian fervour → mass abandonment of work → famine → more fervour | the failed date |
| L62 | B | Theodicy crisis → conversion away → the god acts (desperate) → visible miracle → faith restored | — |
| L63 | R | Credential inflation → more aspirants → more counter-elites → more examinations demanded | office creation, purges |
| L64 | R | Slave raids → captives → slave labour profits → more raids | abolition, revolts |

### I.13 Fourth-pass acceptance stories

19. **The Soft Dynasty.** Steppe nomads (high asabiyya at a meta-ethnic frontier) conquer a river kingdom under a charismatic khan. His death forces the routinisation of charisma: the dynasty adopts the kingdom's examinations. Three generations of luxury decay asabiyya, elite overproduction and fiscal distress raise PSI, and a new frontier people takes the capital. The new dynasty's founding myth (F33) mirrors the old one, and the cycle is visible in the PSI chart.
20. **The Salt of Ages.** An irrigation civilisation intensifies under population pressure (Boserup). Centuries of irrigation without drainage salinise the soils. Yields fall, elites keep extracting (a short time horizon after a disputed succession), the commons are enclosed and the dispossessed fill the cities. A millenarian movement arises when a comet returns on its computed orbit, and the river god's theodicy crisis splits the cult.
21. **The River God's Lawsuit.** A village whose river spirit flooded its fields petitions the city god (the celestial bureaucracy). The petition is delayed by a corrupt clerk spirit until the village's gift to the city god's temple pays the bribe. The river spirit is demoted, and its replacement demands different offerings. Polluting tanneries upstream anger the new spirit, and the flood returns, which leads the guild to an enclosure fight with the village.
22. **The Greens and the Blues.** Two chariot-racing clubs in the capital map onto two cults and two districts. A disputed race result plus a new consumption tax tips the collective behaviour threshold (F32). The riot burns the hippodrome quarter. The emperor's small winning coalition favours the Blues, so purges follow, and the Greens' patron senator, holding a large personal power base, marches.
23. **The Clockwork Guard.** A dead artificer's construct guards a vault with the order "admit only the seal-bearer". The seal is stolen in a scheme, so the thief's patron gains the vault and its relic. The relic legitimises a claim. The construct's bound soul, an ancestor of the robbed house, develops a want for vengeance and turns on its new master during the coronation.
24. **The Grief God's Harvest.** A Death son's aspect feeds on grief (emotion-fed gods). Plague years enrich it, and its dominion spreads with mourning traditions. Its rival, a Life son, sends healers through relief diplomacy and earns gift obligations. A theologian's theodicy argument (persuasion) converts the grieving to the Life son. The Death son's essence falls, and its long plan to make the world a realm of mourning is exposed by a seer's prescience.

### I.14 Fifth-pass couplings, loops and stories

**Couplings** (the registered edge kinds rise to about **410**):

| From | To | Carrier |
|---|---|---|
| Nutrition (F39) | Body, Demography, Health | stature, immunity, fertility, deficiencies |
| Decision biases (F40) | All decisions | sunk cost, overconfidence, groupthink |
| Purity (F41) | Faith, Labour, Health, Trade | exclusion, castes, designated markets |
| Luck and witchcraft (F42) | Justice, Collective behaviour, Magic | accusations, hunts, real and false witches |
| Idea internalisation | Mind | belief change with costs |
| Emotion spirits | Faith, Omens, Magic | amplified emotions, reagents |
| Revitalisation movements | Culture, Politics | nativism against assimilation |
| Body modification | Reputation, Identity | readable bodies |
| Time budgets | Economy, Culture | output against rest |
| Age-sets | Military, Marriage | generational corporations |
| Taverns and welfare | Information, Poverty | social hubs, poor relief |
| Commuting | Labour | spatial labour limits |
| Citizenship, travel regulation, measures | Polity, Trade | rights, borders, transaction costs |
| Evidence | Justice | verdict quality |
| Fisheries, chemical industries, insurance, incorporeal property | Economy | stocks, dyes, risk pooling, rights |
| Optics and clocks | Knowledge, Labour, War | careers extended, coordination |
| Numeracy | Administration, Engineering, Trade | precision |
| Material magic and sympathy | Magic, Economy, Intrigue | magic mining, link theft |
| Circulation, rain shadows, monsoons, currents, oscillations | Climate, Sailing, Fisheries | physically placed climates |
| Launch windows, cosmopolitan cultures | Cosmos travel, Culture | synchronised travel, system-scale culture |

**Loops:**

| Id | Type | Loop | Brake or accelerator |
|---|---|---|---|
| L65 | R | Famine → poor nutrition in childhood → a weaker adult generation → lower output → famine risk | recovery generations |
| L66 | R | Witch hunt → vengeful ghosts and misfortune → more accusations | exhaustion of the hunt, a sceptical theory (8.4b) |
| L67 | R | Sunk cost in a failing war → more losses → more sunk cost | a new ruler (a bias reset) |
| L68 | B | Monsoon failure → famine → migration → less pressure | — |
| L69 | R | Overfishing → stock collapse → fishers turn to raiding or emigration → coastal decline | rights and closures |
| L70 | R | Nativist revival → suppression → martyrs → stronger revival | accommodation |

**Acceptance stories:**

25. **The Witches of the Marsh.** A plague year (3.4) in a culture with a witchcraft belief leads to accusations. The diviner (wrongly) names a widow, and an evidence-weak trial follows (4.5 reference pass 5). The hunt cascades. Among the accused is one real caster, whose curse on the inquisitor is real. Vengeful ghosts follow, and a sceptical physician's theory of contagion slowly ends the hunts.
26. **The Monsoon That Failed.** Climate oscillation weakens the monsoon. Rice fails and a notable year follows. Fishing collapses at the same time (upwelling weak). The poor's children grow up short and sickly (nutrition). Thirty years later the levy of that generation loses a war (lower attributes), and the war's sunk-cost ruler refuses peace (F40) until he dies.

### I.15 Sixth-pass couplings, loops and stories

**Couplings** (the registered edge kinds rise to about **440**):

- identity salience → conflict lines, cohesion, opinion and memory curation;
- the technology ceiling → economy (methods), war (era variants), communication (delays collapse), demography (transition), faith (secularisation), doom (dangerous techniques);
- microbes → nutrient cycling and fermentation quality;
- symbiosis, dormancy, thermoregulation, senses → ecology, war and detection;
- the island rule → speciation;
- writing media → archive survival and accounts;
- locks → theft schemes;
- water-lifting → irrigation and mines;
- navigation instruments → open-ocean routes;
- building materials → structure durability;
- saving → investment and hoards;
- exchange rates → trade;
- economic systems → allocation and collapse modes;
- tourism → renown and income;
- containers → spoilage and trade capacity;
- contests of wit → reputation;
- sanctuary → justice and cult power;
- satire → opinion and stability;
- claims of deeds → reputation truth;
- peer groups → adult loyalties;
- named units → morale;
- veteran colonies and associations → frontier settlement and coups.

**Loops:**

| Id | Type | Loop | Brake or accelerator |
|---|---|---|---|
| L71 | R | Faith salience → holy war → more faith salience | cross-cutting marriages and guilds |
| L72 | R | Industrialisation → pollution and urbanisation → secularisation → less religious opposition to industry | nature-value movements |
| L73 | B | Redistributive centre grows → bureaucracy cost → fiscal stress → collapse → local self-sufficiency | — |
| L74 | R | Insecurity → hoarding → less investment → poverty → banditry → insecurity | a stable ruler |

**Stories:**

27. **The Salience of Bread.** A city long divided by faith suffers a grain price spike. Class salience overtakes faith salience. Bakers' guild members of both faiths riot together against the merchant oligarchs (F32). The ruling council, a small coalition, breaks the movement by raising faith salience again: a sermon campaign blames an infidel quarter. The riot turns into a sectarian massacre, which memory (F33) records differently in each community.
28. **The Iron Horse.** A world reaches steam power (F44). Railways (land transport) shrink the von Thünen rings outward and collapse the canal guild's monopoly (method transition, F24). Rural putting-out spinners lose work to mills, enclosure accelerates, cities swell (the demographic transition) and secularisation rises. The world's Harvest son, losing standing, imposes a natural law that coal will not burn on holy ground. The tech-against-faith conflict becomes a war over coalfields.

### I.16 Eighth-pass loops and stories

**Loops:**

| Id | Type | Loop | Brake or accelerator |
|---|---|---|---|
| L75 | R | Persecution of the gifted → fewer gifted → rarer mages → mages more feared → more persecution | natural laws favouring the gift; mage orders' protection |
| L76 | B | Novelty drain → elites abandon a form → it becomes rare → novelty recovers → revival | — |
| L77 | R | Carrion pulse → vermin and disease → more deaths → more carrion | burial rites, plague burning, scavenger saturation |
| L78 | R | Nation-building → polity identity salience → assimilation → stronger polity identity | minority cohesion, separatism (4.6 reference pass) |

**Stories:**

29. **The Fallen God.** The council strips a rebellious son of divinity (F49 fall). He wakes as a mortal among the people who once worshipped him, remembering everything. His former cult splits between those who recognise him and those who think him an impostor (a claim of identity against evidence). He seeks his true name in an ancient beast's memory (beasts as lore keepers), undertakes a heroquest on his own myth, and either regains godhood through mantling or dies as a mortal martyr whose cult becomes an ideology (secularisation).
30. **The Kingdom Before Us.** A new world is born with a 40-epoch prehistory (F48). When play begins, the peoples speak languages descended from a dead proto-language, three ruined capitals lie in the hills, a dormant imperial title waits for a claimant, a fossil bed of an extinct megafauna feeds dragon legends, and two peoples hold a grudge from a prehistoric war that their accounts tell in opposite ways. The first claimant to the dormant title appears in the tenth live epoch.

---

## Part J. Integration plan

### J.1 Waves

J.10, J.12–J.15, J.17 and J.18 insert the second- to eighth-pass waves (W2+ … W41) into this plan, and J.16 adds the compliance catalogue every wave must satisfy.


Each wave is independently shippable, keeps the engine green (multi-epoch simulation test) and adds its UI surface (architecture rule 6).

| Wave | Content | Depends on |
|---|---|---|
| W0 | Modifier bus (F9), incidents (F10), interconnection registry (I.1), depth metric script (J.7), `@reads`/`@writes` annotations; fix the audit bugs (`_besieged`, idle-army soldiers); wire the dead fields (WarCause, BETRAYAL, `incited_by_son_id`, `golden_age_since_epoch`, celestial influence, outer-being size, son mercy, world danger, creator passions, `dedicated_son_id`) | — |
| W1 | Time sub-clocks (F1), region environment (F2.1–F2.5), weather on demand (F2.3), seasons (F2.2) | W0 |
| W2 | Anatomy and injuries (F4.1–F4.5), healing, conditions, derived capacities; migrate `wound()` → `apply_hits` | W0 |
| W3 | Values, traits, skills, memories, needs (F5–F8); opinion-derived community relations | W0 |
| W4 | Materials and commodities (F3), extraction and refining chains (6.3), markets and money and trade routes (6.4) | W1 |
| W5 | Cohorts and labour (F12, 4.1, 4.9), disease type (3.4), settlements (4.2) | W2, W4 |
| W6 | Polity, house, law, offices, claims, succession, legitimacy (4.5–4.8); treaties (5.13) | W3, W5 |
| W7 | Military: unit stacks, movement, logistics, phased battles with terrain and weather, sieges, duels, captives, war aims, occupation, weariness, vendettas, espionage (Part 5) | W1, W2, W4, W6 |
| W8 | Faith: doctrine and tenets, zeal dynamics, clergy, relics, afterlife strata, judgement, reincarnation (4.4, 3.3) | W3, W6 |
| W9 | Culture and knowledge: language barriers, legends with credence, tradition effects, tech graph with holder levels, ideology, rites and magic, prophecy conditions (Part 8); artworks and items with provenance (Part 7) | W3, W4 |
| W10 | Ecology: species ranges and food web, domestication, beasts (3.2, 3.3a) | W1, W2 |
| W11 | Divine: domain hooks for all 40 domains, son goals, standing, divine wounds, avatars, creator passions and taboos, foreign-god relations, typed council motions (Part 9) | W3, W8 |
| W12 | Cosmos: star life cycle, world physics wiring, regional leak, phenomena, journey cargo and convoys, typed apocalypse variants (10.1–10.8); galaxies with zones, structures and events, clusters, intergalactic and intercluster travel and trade, dimensions with veils and events, rifts, cosmic beings, and the scale ladder in every system (10.10–10.16) | W1, W11 |

#### Execution order after W10

Waves run in dependency order, not in number order. A "+" wave deepens its base wave and is never folded into it. Many later waves depend on "+" waves, so all of W0–W41 cannot finish before the "+" waves start. The order below is a topological sort of the "Depends on" columns of J.1, J.10, J.12–J.15, J.17 and J.18. When several waves are ready, the lowest number goes first, and a "+" wave follows its base.

1. Close W0–W10 completely, including the sections no wave row names, each in its natural wave:
   - F2.6, 6.1 and 6.2 in W1;
   - 3.1 in W2 and W3;
   - 4.10 in W3;
   - F4.6 and 7.2 in W5;
   - 4.3 in W6;
   - 7.3 in W7;
   - F11 in W9;
   - 8.8 in W0.

   Closing W10 also means the gap audit and the control audit are clean, and every W0–W10 row in `13-coverage.md` is `done` or `deferred-approved`.
2. Deepen the fresh systems: W2+, W3+, W4+, W5+, W6+, W7+, W9+, W10+. (Done)
3. Divine and cosmos: W11, W12, W12+. (=2+1) (Done)
4. Gatherings, dominion, magic and language: W13, W14, W15, W16. (=4)
5. Evolution, cities and law: W17, W18, W19. (=3)
6. Collective life and politics: W20, W21, W22, W23. (=4)
7. War, faith and culture depth: W24, W25, W26, W27. (=4)
8. Society and economy depth: W28, W29, W30, W31. (=4)
9. Identity, technology, biology and materials: W32, W33, W34, W35. (=4)
10. World and biology variants, lifecycle ends: W36, W37, W38. (=3)
11. Deep time: W39, which also needs the parallel engine (J.11). (=1)
12. Transformations and the last couplings: W40, W41. (=2)

Every wave closes the same way before the next one starts:
- engine behaviour that actually reads the data;
- typed data with no prose detection (G2);
- rules for every tunable (G1);
- full player control: create, edit every value, hold and release, delete, a son tool where a god would act, and a polished UI (G4);
- LLM context and chronicle templates;
- backfill as if it had always been so (G10);
- tests;
- an adversarial audit with no open rows;
- the wave's rows in `13-coverage.md` filled in.

### J.2 Data migration

- Alembic migrations add every table. A fix-up (`applied_fixups`, spec 01 §11) backfills the new state:
  - region environments from the stored map geometry;
  - cohorts from population counts (age bands from a default pyramid per people biology);
  - mortal profiles with abilities rolled deterministically from existing stats (`rng("backfill.{id}")`);
  - personalities from the existing `depth.specifics` (the LLM-free mapping uses a fixed table of keywords from the enum list; this one-time backfill is the only place prose is read, in the same spirit as the legacy migrator (decision 78); engine code never parses prose (G2));
  - polities from existing RULES hierarchies and tiers;
  - houses from `dynasty_root` clusters;
  - treaties from ALLY, TRUCE and PAYS_TRIBUTE bonds;
  - holder levels = the existing record level.
- **No profiles, no replay (G10).** Existing worlds get the deep rules directly, as if they had always been in force. Epochs are never re-run.
  - **Rule snapshots (decision 68):** new tunables are added to each world's stored snapshot with their deep defaults. Existing tunables keep their stored values.
  - **Backfill as much as possible.** Everything derivable from stored state is backfilled: chronicle, incidents, bonds, battles, captives, deaths and their causes, flags, stats and descriptions. For example, a mortal whose death cause is "fell in battle" gets the battle injury that killed them. A war's recorded battles get terrain and season from their place and year. Houses come from dynasties. Values come from a people's god, stats and history.
  - **Where backfill is impossible**, the existing lore stays exactly as written: no retroactive text edits, no invented history. The new state is initialised neutrally (no injuries, a culture-seeded personality, neutral memories) and evolves under the new rules from the next epoch.
  - Backfill is deterministic (`rng("backfill.{id}")`) and runs once as a recorded fix-up. Its report lists what was derived and what was initialised neutrally.

### J.3 New enums and bond kinds (summary)

- **Enums:** TerrainKind, SoilKind, WeatherKind, Biome (now mechanical), MovementMode, MaterialKind, Commodity (16), BodyPlan, BodyPart, InjuryKind, ConditionKind, ValueAxis, TraitKind, SkillKind, MemoryKind, NeedKind, PressureKind, GovernmentKind, OfficeKind, LawKind, TenetKind, UnitKind, TacticKind, WarAimKind, TreatyKind, ClauseKind, StructureKind, ItemClass, MagicSchool, MagicSource, LegendArchetype, TraditionKind, PhenomenonKind, PlaceKind, FactionKind, FactionGoalKind, ActKind, ScarKind, DangerSourceKind.
- **Bond kinds** (typed rows are the source of truth; bonds are display): PARENT_OF, SPOUSE_OF, BETROTHED_TO, CONCUBINE_OF, FOSTERED_BY, SWORN_KIN, MEMBER_OF (with rank), MEMBER_OF_REALM, HOLDS_OFFICE, CLAIMS, TREATY_PARTY, GUARANTOR_OF, TREATED_BY, AVATAR_OF, ADHERENT_OF (ideology), PRACTISES (rite), HOSTS (disease), LAIR_OF, TELLS (credence), FIXED_IN (legend → artwork).

### J.4 Rules namespaces (new and extended)

`time` (sub-clocks), `engine_budget`, `terrain`, `land_use`, `hazards`, `regional_danger`, `seasons`, `weather`, `weather_battle_effects`, `materials`, `economy` (consumption), `anatomy`, `injury`, `healing`, `aging`, `fertility`, `education`, `careers`, `stress`, `punishment`, `afterlife`, `afterlife_routing`, `necromancy`, `epidemiology`, `ecology`, `domestication`, `pests`, `habitat`, `beasts`, `demography`, `labour`, `consumption`, `culture_drift`, `mobilisation`, `urban`, `taxation`, `crime`, `fire`, `sanitation`, `factions`, `intrigue`, `mercenaries`, `banditry`, `doctrine`, `zeal`, `tithes`, `missions`, `inquisition`, `legislation`, `government`, `succession`, `legitimacy`, `administration`, `overextension`, `revolts`, `houses`, `oaths`, `military_units`, `logistics`, `attrition`, `morale`, `levies`, `terrain_effects`, `tactics`, `sieges`, `naval`, `duels`, `captivity`, `war_aims`, `occupation`, `war_weariness`, `peace`, `vendetta`, `espionage`, `places`, `extraction`, `refining`, `mining_hazards`, `markets`, `money`, `trade_routes`, `banking`, `tolls`, `crafting`, `item_wear`, `item_renown`, `regalia`, `relics`, `construction`, `structure_functions`, `upkeep`, `seafaring`, `art`, `propaganda`, `language`, `interpreters`, `belief`, `traditions`, `knowledge`, `research`, `tech_graph`, `ideologies`, `magic`, `rites`, `backlash`, `prophecy`, `domains`, `son_goals`, `standing`, `divine_wounds`, `avatars`, `creator`, `council`, `natural_law`, `outer_beings`, `stars`, `world_physics`, `phenomena`, `climate`, `doom`, `memory`, `opinion`, `needs`, `cohorts`, `incidents`, `rumours`.

Rule groups (decision 55) are split by subsystem as listed. Pair constraints (decision 69) are declared for every threshold pair, for example `injury.permanent_threshold` < `injury.lethal_threshold`.

### J.5 Pipeline placement and performance

- **New stages, in order:**
  1. **environment** (season set-up, sampled years, weather caches): before the sub-engine stage.
  2. **campaign** (K campaign seasons of all wars): replaces the single campaigns phase.
  3. **demography** (cohort births, deaths, labour): before society_economy.
  4. **production** (extraction, refining, markets, routes): replaces the economy stage.
  5. **polity** (decisions, succession, laws, offices): after society.
  6. **mind** (needs, stress, memories decay, opinion caches): before agents are chosen.
  7. **body** (healing, infection, conditions): in the aging stage.
- **Budget:** per-tick work is bounded by:
  - cohorts instead of individuals;
  - promotion and demotion of named mortals (F12);
  - caching `effective()` per unit of work;
  - sub-step budgets (F1);
  - preloaded indexes per phase (pattern: `MilitaryStrength.load`).
  - Target: a tick for the reference world (3.6k entities, 6 worlds) stays under `engine_budget.tick_target_seconds` [20] on a laptop. A benchmark test enforces it.
- **Determinism:** stream naming conventions are in G3. A test runs a seeded 20-epoch simulation twice and asserts identical database hashes.

### J.6 Testing

- **Unit tests** per formula (deterministic RNG).
- **Scenario tests** per acceptance story (I.4). They build a small world fixture, run N epochs with forced seeds, and assert that the incident chain appears (incident kinds in order).
- **Invariant tests:**
  - cohorts sum to population;
  - every injury bearer exists;
  - every war has aims;
  - every treaty clause executes or is marked;
  - no modifier without a registered edge;
  - no prose parsing in engine code: the source-rules check is extended to forbid `re.` in `engine/` outside allow-listed modules, which removes the regex paths listed in G2.
- **Balance sims:** a 100-epoch LLM-free run per world template, reporting distributions (wars per epoch, mean lifespan, maimed share, polity count, tech spread, doom trajectory). These are compared against target bands stored in `docs/spec/13-balance-bands.json` (created in W0).

### J.7 Depth metric: target

`scripts/depth_metric.py` reports A (typed attributes read), B (behaviour rules that write the entity) and C (registered coupling edges carried), per entity type, from annotations and the registry. The targets below come from the per-entity sections of this spec. They meet or exceed the 5× floor everywhere, and reach about 10× for the most central entities.

| Entity | A now → target | B now → target | C now → target |
|---|---|---|---|
| mortal | 8 → ~75 | ~25 → ~140 | ~10 → ~80 |
| species | 17 → ~70 | ~15 → ~80 | ~8 → ~45 |
| beast (new) | — → ~45 | — → ~30 | — → ~25 |
| spirit | 2 → ~25 | ~6 → ~35 | ~4 → ~25 |
| disease (new) | — → ~20 | — → ~25 | — → ~20 |
| people | 25 → ~150 (incl. cohorts and values) | ~20 → ~110 | ~12 → ~70 |
| settlement | 22 → ~120 | ~20 → ~100 | ~12 → ~65 |
| polity (new) | — → ~60 | — → ~60 | — → ~55 |
| house (new) | — → ~25 | — → ~25 | — → ~20 |
| faction | 3 → ~35 | ~4 → ~45 | ~4 → ~35 |
| cult | 4 → ~45 | ~8 → ~55 | ~6 → ~45 |
| law | 2 → ~30 (per-kind parameters) | ~4 → ~35 | ~3 → ~30 |
| army | 10 → ~90 (stacks × fields) | ~8 → ~80 | ~6 → ~45 |
| war | 15 → ~60 | ~10 → ~70 | ~10 → ~50 |
| treaty (new) | — → ~25 | — → ~20 | — → ~20 |
| region | 12 → ~70 | ~8 → ~60 | ~6 → ~45 |
| place | 3 → ~25 | ~3 → ~20 | ~2 → ~15 |
| resource | 6 → ~35 | ~10 → ~50 | ~6 → ~30 |
| trade_route (new) | — → ~25 | — → ~25 | — → ~25 |
| item | 4 → ~40 | ~8 → ~45 | ~5 → ~30 |
| structure | 3 → ~35 | ~8 → ~50 | ~6 → ~40 |
| vessel | 5 → ~25 | ~5 → ~25 | ~3 → ~15 |
| artwork | 2 → ~20 | ~3 → ~20 | ~2 → ~15 |
| language | ~20 → ~45 | ~10 → ~45 | ~5 → ~30 |
| legend | 2 → ~15 | ~5 → ~25 | ~3 → ~20 |
| tradition | 2 → ~20 | ~2 → ~25 | ~1 → ~25 |
| knowledge | 3 → ~30 (holder levels, techniques) | ~10 → ~50 | ~10 → ~50 |
| ideology (new) | — → ~20 | — → ~20 | — → ~20 |
| rite (new) | — → ~20 | — → ~25 | — → ~25 |
| prophecy | 2 → ~15 | ~3 → ~15 | ~3 → ~15 |
| event | 1 → ~15 | ~4 → ~20 | ~4 → ~15 |
| phenomenon (new) | — → ~20 | — → ~20 | — → ~25 |
| son | ~40 → ~150 (domain hooks, goals, standing, body) | ~30 → ~150 | ~15 → ~90 |
| creator | ~10 → ~35 | ~10 → ~40 | ~8 → ~35 |
| foreign god | ~20 → ~100 | ~10 → ~70 | ~6 → ~50 |
| natural law | 1 → ~10 | ~10 → ~30 | ~8 → ~30 |
| outer being | 3 → ~15 | ~4 → ~20 | ~3 → ~20 |
| celestial | 2 → ~10 | ~2 → ~12 | ~2 → ~15 |
| star | 4 → ~15 | ~4 → ~15 | ~3 → ~15 |
| world | ~25 → ~60 | ~12 → ~50 | ~10 → ~50 |
| route / journey | ~25 → ~45 | ~8 → ~30 | ~6 → ~25 |

CI publishes the metric after each wave, and the wave's goal is met when its entities reach their targets.

### J.8 LLM layer

- **Agent contexts** gain typed blocks (decision K.15). There is no restrictive cap. The only ceiling is `context.max_tokens_per_turn`, whose default is the model's full input window minus the reserved output, so in practice nothing relevant is cut. Blocks are ordered by relevance, so the most important facts come first, but they are not trimmed to a small budget. The blocks are:
  - body (visible injuries and conditions)
  - mind (traits, top values, needs, stress)
  - memories (top 5 by magnitude)
  - offices and claims
  - doctrine tenets
  - treaty obligations
  - war aims
  - local weather and season
  - environment of the region
- **Tools** gain typed parameters instead of free text: unit composition when raising an army, tactic choice, treaty clauses, law kind and parameters, rite selection, item class and material, structure kind. The tool declarations (decision 21) list the gates (techniques, materials).
- **Fate** judges creations against the new typed fields (a son-created species must declare body plan, diet and habitat). This keeps prose and mechanics consistent (G8).
- **Harm directive (G9):** one shared prompt block, included by every narrative prompt, requires harm to be stated plainly without graphic detail. English engine line templates are reviewed against the same rule.
- **The chronicler and the bard** read incident chains (F10) and phase summaries (5.3), so they can narrate causes. All prompts stay in `prompts/` (architecture rule 3).

### J.9 UI surfaces (summary)

**New drawer tabs:**

- Body
- Mind
- Skills
- Kin
- Biography
- Doctrine
- Law code
- Offices
- Claims
- Treaty
- Provenance

**New views:**

- War room, battle report, siege tracker
- Realm view, house tree
- Production chains, trade-flow map, price boards
- Tech graph
- Species ranges and food web
- Disease map
- Phenomenon layer
- Climate layers, seasons calendar
- Interconnection explorer (the registry graph)
- The "why" breakdown of every stat (F9)

The route ↔ caller coverage test (architecture rule 6) extends to every new route.


### J.10 Second-pass integration addendum

**Waves** (inserted into J.1; dependencies as listed):

| Wave | Content | Depends on |
|---|---|---|
| W3+ | F13 mind split, F14 thoughts and emotions, F15 preferences, F16 ethics, F17 dreams and wants, F18 relationships and interactions, F19 local reputation and currencies (W3 grows into these) | W0 |
| W2+ | F23 material physics and tissue layers, F30 effect packages | W2 |
| W4+ | F24 production methods, energy, pollution, quality tiers, spoilage; ownership and profits; market access, tariffs, credit, speculation | W4 |
| W5+ | F29 households and dwellings; F26 genetics; F28 conservation ledger (land in W0 as a test harness, completed here) | W5 |
| W6+ | 4.11 titles; F20 schemes, secrets, hooks, favours, identities; F21 communication and public opinion; F22 belief state; estates, parties, movements, elections, enactment processes, crises, coalitions, corruption, tax types, mandates | W6 |
| W7+ | Organisation, discipline, ammunition, frontage and reserves, the morale ladder, command and control, spotting, penetration, casualty classes, surgeons, salvage, casus belli, war-score peace, war support, production efficiency | W7 |
| W9+ | Civic tree, institutions, boosts, catch-up, card draws, great people, era scores, dangerous techniques and accidents, reverse engineering, printing and censorship, theories (8.4b), art forms (7.5), name meanings | W9 |
| W10+ | Flora, husbandry, vermin, procedural beasts, night creatures, pets | W10 |
| W12+ | 10.9 cosmic physics (derived), star systems, cosmic features, impacts, terraforming, survey levels, life classes | W12 |
| W13 | F25 gatherings, F27 storyteller, event collections, excavations and sites with rooms | W3+, W6+ |

**Enums added:** Attribute (19), Facet (36), BeliefAxis (24), ThoughtKind (~80), Emotion (24), MoodState, NeedKind (22), PreferenceKind, ActKind (~40), EthicStance, DreamKind, WantKind, FearKind, LifestyleFocus, RelationshipType, InteractionKind, ReputationAxis, SecretKind, HookStrength, SchemeKind, SchemePhase, MessageMedium, MessageContentKind, BeliefSource, TissueKind, ArmourLayer, TreatmentStep, ProductionMethodId, EnergySource, PollutionKind, QualityTier, GatheringKind, Locus/Allele, StorytellerProfile, AfflictionTransmission, TitleRank, ArtDiscipline, TheoryDomain, RockKind, CavernLayer, AlignmentAxis, StarStage, Biochemistry, LifeComplexity, CosmicFeatureKind, CommanderTrait, Formation, MoraleState, CasualtyClass, CasusBelliKind, SubjectKind, EstateKind, TaxKind, CrisisStage, SurveyLevel, GhostType, SiteRoomKind, ExcavationStage.

**Bond kinds added:** PET_OF, HOLDS_TITLE, DE_JURE_OF, PRACTISES_FORM, HOLDS_THEORY, ENDORSES (cult → theory), CONDEMNS, MEMBER_OF_CIRCLE, HOOK_ON, FAVOUR_OWED, SCHEME_AGENT, ENVOY_TO, BACKS (crisis), IN_SPHERE_OF, SUBJECT_OF (typed by SubjectKind).

**Rules namespaces added:** attributes, facets, beliefs, thoughts, emotions, mood, preferences, ethics, dreams, wants, lifestyle, relationships, interactions, circles, reputation, currencies, secrets, hooks, favours, identities, schemes, messages, envoys, etiquette, public_opinion, beliefs_state, deception, material_physics, tissues, bleeding, consciousness, treatments, production_methods, energy, pollution, quality, spoilage, ownership, investment, market_access, tariffs, credit, speculation, gatherings, genetics, storyteller, conservation, households, dwellings, afflictions, titles, art_forms, theories, civics, institutions, boosts, catch_up, great_people, eras, accidents, printing, censorship, geology, hydrology, strata, alignment, tectonics, sites, excavations, flora, husbandry, vermin, monster_generation, night_creatures, organisation, discipline, ammunition, frontage, command_control, spotting, penetration, casualty_classes, field_medicine, salvage, casus_belli, war_score, war_support, war_production, estates, parties, movements, elections, enactment, crises, coalitions, diplomatic_capacity, spheres, subjects, corruption, taxes, mandates, demands, policy_network, constitution, court, separatism, orbits, stellar_evolution, planetary_climate, impacts, terraforming, survey, life_classes.

**Engine budget:** the second pass adds per-mortal mind updates and social sampling. The budget rules hold, with dormancy (K.4), cohort aggregation for anonymous people, social sampling caps, belief-store pruning (keep the top N per holder by relevance, `beliefs_state.max_per_holder` [200]) and per-phase preloading. The reference-world tick target stays [20] seconds (K.8), met by the parallel engine of J.11.

**Testing additions:**

- **Conservation tests** (F28) for population, goods, money, souls and essence.
- **Belief-gap tests:** a forged message changes a decision, and the truth resolves the outcome.
- **Physics tests:** penetration tables and bleeding curves.
- **Paradigm tests:** a false theory raises mortality and a shift lowers it.
- **Storyteller pacing bands:** tension stays within the profile's band over 100 epochs.
- **Acceptance stories 6–12** (I.7) as seeded scenario tests.

**Depth metric targets** (additions and revisions to J.7):

| Entity | A target (first → second pass) | B target | C target |
|---|---|---|---|
| mortal | ~75 → ~260 (19 attributes, 36 facets, 24 beliefs, 22 needs, preferences, relationships, reputation axes, genome, tissue-level body) | ~140 → ~260 | ~80 → ~140 |
| beast | ~45 → ~120 | ~30 → ~70 | ~25 → ~55 |
| species | ~70 → ~110 (flora, husbandry, biochemistry) | ~80 → ~110 | ~45 → ~70 |
| people | ~150 → ~230 (ethics ~40, preferences, innovations, habitability, SoL per class) | ~110 → ~170 | ~70 → ~110 |
| settlement | ~120 → ~170 (investment, logistics, housing, local reputations) | ~100 → ~150 | ~65 → ~95 |
| polity | ~60 → ~140 (estates, taxes, corruption, mandates, subjects, spheres, court, constitution, policies) | ~60 → ~150 | ~55 → ~110 |
| house | ~25 → ~60 (titles, genetics, feuds, partition) | ~25 → ~55 | ~20 → ~45 |
| faction | ~35 → ~70 (estates, parties, movements, companies, holy orders, troupes) | ~45 → ~85 | ~35 → ~60 |
| army | ~90 → ~180 (organisation, discipline, ammunition, formations, commander traits, templates) | ~80 → ~150 | ~45 → ~75 |
| war | ~60 → ~95 (casus belli, war support, score costs) | ~70 → ~110 | ~50 → ~75 |
| knowledge | ~30 → ~70 (civics, institutions, boosts, eras, blueprints) | ~50 → ~110 | ~50 → ~85 |
| son | ~150 → ~260 (aspects, mind layers, relationships, schemes) | ~150 → ~230 | ~90 → ~130 |
| world | ~60 → ~120 (derived physics, life classes, survey) | ~50 → ~90 | ~50 → ~80 |
| star | ~15 → ~35 (mass evolution, systems) | ~15 → ~30 | ~15 → ~25 |
| region | ~70 → ~130 (geology, strata, hydrology, alignment, tectonics) | ~60 → ~100 | ~45 → ~75 |
| item | ~40 → ~65 (decorations, depictions, clothing and furniture classes) | ~45 → ~60 | ~30 → ~45 |
| structure | ~35 → ~55 | ~50 → ~70 | ~40 → ~55 |
| title (new) | — → ~25 | — → ~25 | — → ~25 |
| art_form (new) | — → ~20 | — → ~20 | — → ~20 |
| theory (new) | — → ~15 | — → ~20 | — → ~25 |

All other entities keep their J.7 targets plus the shared mind, effect and reputation layers where they apply.

**UI additions:**

- **Mind:** an emotions and thoughts feed, a facets and beliefs chart, preferences, a dream tracker.
- **Social and reputation:** a relationships web, a reputation map per figure.
- **Intrigue and communication:** a scheme board (the player sees all), a secrets ledger (player-only), and message traffic (a map of envoys and letters in transit, with interceptions).
- **Belief-versus-truth toggles:** what the polity believes against what is true.
- **Body and physics:** a tissue-level body diagram, a penetration explainer in battle reports.
- **Economy:** production-method choices per site, an energy and pollution map layer, economic indicator charts.
- **Politics:** gatherings calendar, title tree and de jure layer, crises tracker with escalation and backers, coalition threat gauges, estates' privileges panel, policy-network graph per polity.
- **Knowledge and culture:** civic tree, institutions spread map, era score panel, theory cards, art-form lineage.
- **Cosmos:** orbit view with computed seasons and eclipses, impact warnings.
- **Storyteller:** tension chart.

### J.11 Parallel and efficient engine (decision K.8)

The second pass multiplies per-tick computation, while decision K.8 keeps the CPU budget. The engine therefore changes from "phase reads and writes rows" to **compute in parallel, commit serially**.

1. **Snapshot load.** At the start of each stage, the phase loads the rows it needs into compact in-memory structures: columnar arrays (numpy) for cohorts, region environments, species ranges, market prices and stack tables, and dictionaries for graph slices. This extends the existing preload pattern (`MilitaryStrength.load`) to every phase.
2. **Shard.** Work is partitioned into **shards** that do not interact within the step:
   - worlds are the first-level shard (they interact only through routes and journeys);
   - inside a world, the second level is region clusters (connected components of the interaction radius for the step: wars, trade, diffusion);
   - entity batches are used for per-entity mind, body and household updates.
3. **Compute in parallel.** Each shard runs as a pure function of its snapshot in a `ProcessPoolExecutor` sized by `engine_budget.workers` [cores − 1]. Python's GIL is bypassed by processes; numpy kernels release the GIL. A free-threaded CPython build (3.13t or later) can later switch shards to threads without code changes, because shard functions are pure. Each shard returns **effect lists**: typed deltas (stat changes, new rows, incidents, modifiers, conservation-ledger flows).
4. **Deterministic merge.** Effect lists are merged in a canonical order (shard key, then entity id, then effect sequence). RNG streams are keyed by entity and sub-step (G3), never by worker or order, so a tick produces byte-identical results with 1 worker or N. A test asserts equal database hashes across worker counts.
5. **Serial commit.** The merged effects are applied in one write unit per phase, under the single-writer lock (decisions 23 and 75). SQLite stays single-writer; only computation is parallel.
6. **Cross-shard reconcile.** Interactions that span shards (inter-world journeys and trade, rumours crossing worlds, coalitions across regions) run in a small serial reconcile step after the parallel compute. Their inputs are the shard outputs.
7. **Vectorised kernels** run the hot paths (demography per cohort, ecology per range, markets per commodity, weather and harvest per sampled year, the battle phases per stack pair) as array operations, not Python loops over rows.
8. **Incremental work.** Dormant mortals (K.4) and unchanged regions are skipped through dirty flags set by incidents and modifiers, so a tick only recomputes what can have changed.
9. **Profiling and budget tests.** Each phase reports its CPU time in tick stats (the existing `TickStats`). A benchmark test on the reference world asserts the [20]-second target with the default worker count, and fails CI on regression beyond `engine_budget.regression_pct` [15].
10. **LLM concurrency is independent.** Son and mortal agent turns already run concurrently under a semaphore. Their timeouts are set generously (K.8), and engine ticks never wait on the LLM.

### J.12 Third-pass integration addendum

**Waves:**

| Wave | Content | Depends on |
|---|---|---|
| W14 | F31 dominion and scales, thrones and magic sites, perceived alignment and worship mode, miracle impressiveness, belief shapes gods, divine creature learning, god design trade-offs | W11, W12 |
| W15 | Spell grammar, magic resources, resistance and dispels, paradigms, myth-coupling, environmental combinations, warping, global enchantments; heroquests; mantling; servitors; cosmic offices; true names; geasa | W9+, W14 |
| W16 | Sound-change engine, typology, semantic drift, script evolution, decipherment, pidgins, language policy, non-vocal modalities, divine tongues | W9 |
| W17 | Trait evolution, niches, radiation, trophic flow, coevolution, keystones, feral reversion, biome succession, biogeochemical cycles; pathogen evolution, vectors, carriers, spillover, responses, vaccination, cure race | W10+, W12+ |
| W18 | Desirability, coverage, housing evolution, homelessness, prevention, morphology, turf; caravans, fleets, cargo transport, ports, manipulation; crime organisations, trading posts, magical orders | W5+, W4+ |
| W19 | Legal typology, precedent, courts and appeals, registries, jurisdiction conflicts, pardons, outlawry, prisons; recruitment motives, network topology, mole hunts, defectors, assassination forensics, ciphers, signal networks | W6+ |
| W20 | F32 collective behaviour, F33 historiography, F34 storylets, F35 social norms and volition; passions, conviction, persuasion, status hierarchies; social learning; generations; diaspora; demographic transition; sex ratios; role norms; dating systems; world materials; heraldry; component designs | W13, W3+ |

**Enums added:** ScaleAxis, Technique, Form (magic), RangeKind, DurationKind, MagicResourceKind, ParadigmKind, ServitorRank, CosmicOfficeKind, GeasKind, SoundChangeKind, WordOrder, MorphologyType, ScriptType, LanguageModality, NicheKey, TrophicLevel, ServiceKind, HousingLevel, Morphology, CaravanStatus, CargoClass, LegalSystem, CourtLevel, RecruitmentMotive, AssassinationMethod, CipherStrength, CollectiveActKind, AccountKind, AccountStance, StoryletId, NormSituation, PassionKind, DatingSystemKind, HeraldicCharge, DesignComponentKind.

**Rules namespaces added:** dominion, scales, thrones, magic_sites, worship_mode, miracle_impressiveness, belief_pull, divine_creature, god_design, spell_grammar, magic_resources, magic_resistance, paradigms, myth_coupling, warping, global_enchantments, heroquests, mantling, servitors, cosmic_offices, true_names, geasa, sound_change, typology, semantic_drift, scripts, decipherment, pidgins, language_policy, selection, niches, trophic, keystones, feral, succession_biomes, biogeochemistry, pathogen_evolution, vectors, carriers, spillover, outbreak_response, vaccination, cure_research, desirability, coverage, housing_evolution, homelessness, prevention, morphology, turf, caravans, fleets, cargo, ports, manipulation, crime_orgs, trading_posts, magical_orders, legal_systems, precedent, courts, registries, jurisdiction, pardons, outlawry, prisons, recruitment, network_topology, mole_hunts, defectors, forensics, ciphers, signals, collective_behaviour, historiography, storylets, norms, volition, passions, conviction, persuasion, status, social_learning, generations, diaspora, demographic_transition, sex_ratio, role_norms, dating, world_materials, heraldry, designs.

**Testing additions:**

- **Scenario tests** for stories 13–18.
- **Linguistic tests:** a sound-change application is deterministic, and cognates are recoverable.
- **Evolution tests:** selection moves trait means in the expected direction, and niches exclude.
- **Collective behaviour tests:** threshold cascades are reproducible and deterrence raises thresholds.
- **Dominion conservation:** dominion shares per region sum correctly.
- **Historiography tests:** the distance of accounts from the truth is measurable, and revisions are detectable by old texts.

**Depth metric targets (third-pass revisions):**

| Entity | A (second → third) | B (second → third) | C (second → third) |
|---|---|---|---|
| mortal | ~260 → ~300 (passions, conviction, generation, role eligibility, true name) | ~260 → ~300 | ~140 → ~170 |
| son | ~260 → ~320 (dominion, scales, design budget, believed image, offices, creature) | ~230 → ~290 | ~130 → ~170 |
| foreign god | ~100 → ~200 | ~70 → ~140 | ~50 → ~100 |
| species | ~110 → ~150 (heritable traits, niches, trophic level, keystone) | ~110 → ~150 | ~70 → ~95 |
| disease | ~20 → ~45 (evolving traits, vectors, resistance) | ~25 → ~50 | ~20 → ~40 |
| language | ~45 → ~110 (sound changes, typology, scripts, modality) | ~45 → ~90 | ~30 → ~55 |
| settlement | ~170 → ~230 (desirability, coverage, housing levels, morphology, turf) | ~150 → ~200 | ~95 → ~125 |
| region | ~130 → ~170 (dominions, succession, cycles) | ~100 → ~130 | ~75 → ~100 |
| world | ~120 → ~150 (belief drift, cycles) | ~90 → ~115 | ~80 → ~100 |
| law | ~30 → ~55 (system, precedents, courts) | ~35 → ~60 | ~30 → ~45 |
| faction | ~70 → ~95 (crime, trading posts, magical orders) | ~85 → ~110 | ~60 → ~80 |
| rite | ~20 → ~50 (grammar, resources, paradigm, myth-coupling) | ~25 → ~55 | ~25 → ~45 |
| legend | ~15 → ~30 (heroquest fidelity, cycles) | ~25 → ~40 | ~20 → ~35 |
| vessel | ~25 → ~50 (components, lineage, wear) | ~25 → ~40 | ~15 → ~25 |

**UI additions:**

- **Gods:** a dominion map with contests and scales legend; a god design sheet; a believed-image versus actual comparison; a cosmic offices board.
- **Myth and magic:** a heroquest log; a spell designer view; magic resources and sites.
- **Language:** a sound-change timeline and a cognate explorer; a decipherment progress view.
- **Ecology:** trait evolution charts per species; a niche map.
- **Epidemics:** a pathogen evolution panel; outbreak responses.
- **Cities:** desirability and coverage layers; housing levels.
- **Trade:** caravans on the map.
- **Law:** a case-law browser.
- **Espionage:** a spy network graph and a cipher status board.
- **Society:** riot cascade replays.
- **Memory and narrative:** an accounts versus truth viewer; the storylet queue; a generations panel.

### J.13 Fourth-pass integration addendum

**Waves:**

| Wave | Content | Depends on |
|---|---|---|
| W21 | F37 structural-demographic variables, asabiyya, challenge–response, long plans; F38 reciprocity and gift ledgers; kinship systems, marriage alliance, reproductive systems, nomadism, legacy traits; labour regimes | W5+, W6+, W20 |
| W22 | Selectorate and coalitions, legitimacy types and routinisation, time horizon, clientelism, venality, power bases, coup-proofing, big-man and chief; segmentary lineages; breeding plans; examinations, credentials, academic freedom, schools of thought | W6+, W9+ |
| W23 | von Thünen rings, central places, Boserup, nutrients, perennials, commons and enclosure, game reserves, famine foods; resilience, aid and reconstruction; world-defining resource; brands | W4+, W18 |
| W24 | OOB hierarchy, HQ command range and points, logistics network flow, culmination, theatre allocation; Lanchester attrition; age-of-sail damage, points of sail, gunnery, fires, prizes, naval treaties; expeditions with light, provisions, afflictions, virtues and quirks | W7+ |
| W25 | Mysticism, millenarianism, theodicy, sacraments, believed against actual afterlife, secularisation; genius loci and celestial bureaucracy; emotion-fed gods; divination systems and prescience; psychohistory; dreams; honour models | W8, W14 |
| W26 | Art markets, forgery, canon; art movements, clubs, leagues, betting, circus factions; constructs; monster contracts; astrology; punitive remaking | W9+, W10+, W18 |
| W27 | Formation history, irregular seasons, long ecological transformations; cyclic ages; F36 narrative arcs and the drama manager | W12+, W20 |

**Enums added:** PSIComponent, LongPlanKind, GiftOccasion, KinshipDescent, ResidenceRule, MarriagePreference, MarriagePayment, ReproductiveSystem, MobilityMode, CoalitionBase, LegitimacyType, PatronageTie, OfficeSaleKind, PowerBaseAsset, CoupProofingMeasure, LeadershipMode, LineageLevel, LandUseRing, CentralityRank, NutrientKind, PerennialKind, CommonsRule, ExpeditionRole, AfflictionKind, VirtueKind, QuirkKind, HQLevel, LogisticsAsset, LanchesterMode, ShipLocation, ShotKind, PointOfSail, MysticState, MillenarianStage, SacramentKind, AfterlifeModel, GeniusLocusKind, BureauRank, PetitionStatus, DivinationKind, ArtMarketRole, ClubKind, ConstructOrder, PowerSource, ArcTemplate, ArcStage, SetupKind, LabourRegime, PreparednessKind, AgeCycleMode, HonourModel, DreamKind.

**Rules namespaces added:** structural_demography, asabiyya, challenge_response, long_plans, reciprocity, potlatch, ceremonial_circuits, sacrifice_exchange, kinship, marriage_alliance, reproduction_systems, nomadism, legacy_traits, labour_regimes, corvee, indenture, slave_markets, manumission, selectorate, legitimacy_types, charisma_routinisation, time_horizon, clientelism, venality, power_bases, coup_proofing, leadership_modes, segmentary_lineages, breeding_plans, examinations, credentials, academic_freedom, school_lineages, thunen, central_places, boserup, nutrients, perennials, commons, game_laws, famine_foods, resilience, relief, reconstruction, keystone_resource, brands, command_hierarchy, headquarters, logistics_network, culmination, theatre_allocation, lanchester, ship_damage, sailing, gunnery, prizes, naval_treaties, expeditions, afflictions_virtues, quirks, mysticism, millenarianism, theodicy, sacraments, afterlife_belief, secularisation, genius_loci, celestial_bureaucracy, emotion_feeding, divination, prescience, psychohistory, dreams, honour_models, art_markets, forgery, canon, art_movements, sports, circus_factions, constructs, monster_contracts, astrology, punitive_remaking, formation, irregular_seasons, ecological_plans, ages, arcs, drama_manager.

**Testing additions:**

- **Cliodynamic tests:** in a closed world with no shocks, PSI waves emerge from population growth and elite growth over long runs.
- **Logistics flow tests:** supply delivered equals supply produced minus losses (F28).
- **Lanchester tests:** concentration effects under the square law.
- **Gift ledger tests:** reciprocity balances.
- **Afterlife-belief tests:** revelation shocks happen when the doctrine and the strata differ.
- **Arc tests:** setups and payoffs are paired in the chronicle feed.
- **Acceptance stories 19–24** (I.13).

**Depth metric targets (fourth-pass revisions):**

| Entity | A (third → fourth) | B (third → fourth) | C (third → fourth) |
|---|---|---|---|
| mortal | ~300 → ~330 (dreams, astrology, quirks, credentials, power base, patronage ties, arc stages) | ~300 → ~340 | ~170 → ~200 |
| people | ~230 → ~290 (kinship, reproduction, mobility, asabiyya, legacy traits, honour model, divination system) | ~170 → ~220 | ~110 → ~140 |
| polity | ~140 → ~210 (PSI variables, coalition, legitimacy mix, time horizon, clientelism, venality, coup-proofing, exams, HQ tree) | ~150 → ~220 | ~110 → ~150 |
| settlement | ~230 → ~260 (rings, centrality, preparedness, reconstruction) | ~200 → ~230 | ~125 → ~145 |
| region | ~170 → ~200 (nutrients, perennials, commons, reserves) | ~130 → ~160 | ~100 → ~120 |
| cult | ~45 → ~90 (mysticism, millenarianism, sacraments, afterlife model, theodicy state, secularisation, petitions) | ~55 → ~100 | ~45 → ~75 |
| son | ~320 → ~350 (emotion diet, bureaucracy, gift debts) | ~290 → ~320 | ~170 → ~190 |
| army | ~180 → ~240 (OOB, HQ, logistics assets, culmination) | ~150 → ~200 | ~75 → ~95 |
| vessel | ~50 → ~80 (damage locations, sailing, gunnery) | ~40 → ~65 | ~25 → ~35 |
| spirit | ~25 → ~60 (genius loci, bureaucracy rank, petitions, reciprocity) | ~35 → ~60 | ~25 → ~40 |
| beast | ~120 → ~150 (constructs, contracts) | ~70 → ~90 | ~55 → ~65 |
| world | ~150 → ~180 (formation history, irregular seasons, age cycle) | ~115 → ~135 | ~100 → ~115 |

**UI additions:**

- **History and politics:** a PSI dashboard (secular-cycle chart) per polity; an asabiyya frontier map; coalition and power-base panels; a patronage network graph.
- **Kinship and exchange:** a kinship-system view (descent and alliance); a gift ledger.
- **Economy:** von Thünen and central-place overlays; a soil nutrient layer.
- **War:** an OOB tree with HQ ranges; a logistics flow map.
- **Naval:** ship damage cards.
- **Expeditions:** an expedition log.
- **Faith:** a celestial bureaucracy chart with petitions; an afterlife "believed against actual" comparison.
- **Culture:** a canon list per culture; an art market board.
- **Prediction and narrative:** a diviners' and prescience forecast panel (with the player-visible truth); a narrative arcs board with setups and payoffs.

### J.14 Fifth-pass integration addendum

**Waves:**

| Wave | Content | Depends on |
|---|---|---|
| W28 | F39 nutrition, F40 decision biases, F41 purity and castes, F42 luck, charms and witchcraft; idea internalisation | W3+, W5+ |
| W29 | Revitalisation, intoxication cultures, body modification, time budgets, naming customs, age-sets; cuisines, taverns, welfare, commuting; cooperatives; citizenship, travel regulation, poor relief, measures; evidence | W6+, W18, W20 |
| W30 | Fisheries, chemical industries, insurance, incorporeal property, optics, clocks, games, numeracy; material magic and sympathy; emotion spirits | W4+, W15 |
| W31 | Atmospheric circulation, rain shadows, monsoons, ocean currents, oscillations; launch windows; cosmopolitan cultures | W12+ |

**Rules namespaces added:** nutrition, deficiencies, biases, purity, castes, luck, charms, witchcraft, internalisation, emotion_spirits, revitalisation, intoxication, body_modification, time_budgets, naming_customs, age_sets, cuisine, taverns, welfare, commuting, cooperatives, citizenship, travel_regulation, poor_relief, measures, evidence, fisheries, chemistry, insurance, incorporeal_property, optics, timekeeping, games, numeracy, material_magic, sympathy, circulation, rain_shadow, monsoon, currents, oscillations, launch_windows, cosmopolitan_culture.

**Testing additions:**

- **Nutrition tests:** famine cohorts show lower adult attributes.
- **Bias tests:** a sunk-cost ruler continues wars beyond the unbiased decision point.
- **Witchcraft tests:** accusation accuracy is measurable against the real casters.
- **Climate placement tests:** rain shadows place deserts in the lee of ranges.
- **Launch-window tests:** physical travel durations vary with the synodic period.
- **Stories 25–26.**

**Depth metric targets (fifth-pass increments):**

| Entity | Increment |
|---|---|
| mortal | +~25 (nutrition, purity, biases, marks, name forms, age-set) |
| people | +~30 (cuisine, intoxication, adornment, time budgets, naming, age-sets, castes, number system, luck beliefs, witchcraft belief) |
| settlement | +~20 (taverns, welfare, commuting, measures) |
| polity | +~15 (citizenship, travel regulation, poor relief) |
| region and world | +~15 each (circulation, rain shadow, monsoon, currents, fisheries) |

### J.15 Sixth-pass integration addendum

**Waves:**

| Wave | Content | Depends on |
|---|---|---|
| W32 | F43 identity layers and salience; peer groups; contests of wit; claims of deeds; sanctuary; satire and fools | W3+, W20 |
| W33 | F44 technology ceiling and advanced eras (era variants of units, industrial methods, communication media, rocketry routes) | W9+, W24, W31 |
| W34 | Microbes, symbiosis, dormancy, thermoregulation, senses, plant defences, island rule | W17 |
| W35 | Writing media, locks, water-lifting, navigation instruments, building materials; saving, exchange rates, economic systems, vertical integration, tourism, containers; named units and veterans | W4+, W18, W24 |

**Rules namespaces added:** identities_salience, tech_eras, era_units, industrialisation, mass_media, rocketry, microbes, fermentation, symbiosis, dormancy, thermoregulation, senses, plant_defences, island_rule, writing_media, security, water_lifting, navigation_instruments, building_materials, saving, exchange_rates, economic_systems, putting_out, tourism, containers, contests, sanctuary, satire, deed_claims, peer_groups, unit_honours, veterans.

**Tests:**

- **Salience tests:** conflict sides follow the most salient layer.
- **Tech-era tests:** a seeded world with a high technology setting reaches the industrial-era techniques along valid prerequisite paths.
- **Economic-system tests:** the collapse of a redistributive centre propagates.
- **Archive-survival tests:** survival follows the media.
- **Stories 27–28.**

### J.16 Compliance catalogue (architecture rule 6 and decisions 21, 26, 41, 68, 71)

**Stage names** are the pipeline stages of J.5 (environment, campaign, demography, production, polity, mind, body) and the existing ones (sub-engine, raid, economy, society, society-engine, aging, transition, post-transition).

**Lever verbs** are player actions with ledger undo (decision 61):

- set, force, grant, remove, trigger, block;
- edit (of typed fields);
- pin (freeze from automatic change).

**LLM exposure** names the agent context block (J.8) and the typed tools (decision 21), whose descriptions live in `prompts/` (decision 26).

**Templates** are English chronicle template families (decision 71), localised at epoch end.

**Backfill** is the G10 rule.

| Section | Tables | Trigger stage | Player levers | UI | LLM exposure | Templates | Backfill |
|---|---|---|---|---|---|---|---|
| F1 time sub-clocks | `notable_years`, `dating_systems` | environment | set the sampled-year count; force a notable year; edit dating systems | year strip on the chronicle; notable-years list | context: season, year in the speaker's dating system | `year.*` | notable years from the existing disaster and famine chronicle rows |
| F2 environment | `region_environment`, `world_seasons`, `weather_effects`, `region_land_use`, `ley_lines` | environment | edit region fields; set a season table; force weather for a slot; sever or forge ley lines | map layers (terrain, soil, climate, land use, ley); seasons calendar | context: local terrain, season, weather; son tool `shape_weather` | `weather.*`, `season.*`, `land.*` | derived from the map geometry and the climate era |
| F3 materials | `materials` (catalog), `world_materials`, `community_stocks` | production | edit materials; grant stock | materials browser; stock tables | context: notable materials held; mortal tool parameter `material` | `material.*` | stocks from the existing food, ore and goods via fixed splits |
| F4 bodies and injuries | `injuries`, `conditions` | body | heal, maim (typed part and kind), apply a prosthesis | Body tab (diagram, history) | context: visible injuries and conditions | `injury.*`, `healing.*` | death causes give fatal injuries; others neutral |
| F5 values and culture | `culture_values`, `personality_values` | mind | edit values; pin a culture | culture radar | context: top values | `culture.*` | from the people's god domains, stats and history |
| F6 skills | `skills` | mind | grant or remove skill levels | Skills tab | context: top skills; tool gates by skill | `skill.*` | from role, stats and age |
| F7 opinions and memory | `memories` | mind | add or remove a memory; edit decay | memory list per entity; relation "why" | context: top memories | `memory.*` | from bonds (enemy, killed, captive) and community relation events |
| F8 needs and pressures | `needs`, `pressures` | mind | set a need or pressure; pin | gauges | context: top two pressures | `need.*` | computed |
| F9 modifier bus | `modifiers` | every stage | add or remove a modifier | the "why" breakdown on every stat | context: active modifiers (summarised) | n/a | derived from existing flags and effects |
| F10 incidents and collections | `incidents`, `incident_collections` | every stage | annotate; merge collections | timeline, legends view, biography | context: the recent incident chain of the actor | n/a (incidents carry template keys) | from the chronicle rows (kind to incident kind map) |
| F11 rumour | `rumours` | mind | plant or quash a rumour | rumour map | context: rumours known to the actor | `rumour.*` | none (start empty) |
| F12 cohorts and generations | `community_cohorts` | demography | move, promote or demote cohort members | population pyramid; generations panel | context: cohort summary of the community | `cohort.*` | a default pyramid per biology |
| F13 mind split | `mortal_profiles` (attributes, facets, beliefs), `incubating_ideas` | mind | edit attributes, facets and beliefs; implant an idea | Mind tab | context: character block (facets, beliefs) | `mind.*` | from stats, depth specifics (one-time map, J.2), culture |
| F14 thoughts, emotions, dreams | `thoughts`, `dreams` | mind | send a thought or dream | emotions feed; dream log | context: mood and recent strong thoughts; son tool `send_dream` (existing, typed) | `thought.*`, `dream.*` | none |
| F15 preferences | `preferences` | mind | edit | preferences panel | context: likes and dislikes; gift choice | `taste.*` | culture-seeded |
| F16 ethics | `culture_ethics`, `honour_model` | mind | edit stances | ethics table per culture | context: the stance on acts under consideration | `ethics.*` | from culture values and doctrine |
| F17 dreams, wants, focus | `life_dreams`, `wants`, `fears` | mind | set a dream, want or fear | dream tracker | context: dream, wants and fears as objectives; tool `pursue_dream` | `aspiration.*` | from role, values and age |
| F18 relationships and contests | `relationships`, `social_circles`, `contests` | mind | set relationship values; start a contest | relationship web; circles | context: key relationships; tools `befriend`, `court`, `insult`, `challenge_contest` | `social.*`, `contest.*` | from bonds (loves, rival, companion) |
| F19 reputation and currencies | `reputations` | mind | edit reputation per community; grant prestige, dread, tyranny | reputation map; currency gauges | context: reputation where the actor stands | `reputation.*` | from fame, charisma and deeds |
| F20 secrets, hooks, favours, identities, schemes | `secrets`, `hooks`, `favours`, `identities`, `schemes` | polity, mind | reveal, plant or cancel; expose an identity; abort a scheme | scheme board (player sees all); secrets ledger | context: own secrets and hooks; tools `start_scheme`, `use_hook`, `call_favour` | `scheme.*`, `secret.*` | none |
| F21 communication | `messages` (extended), `public_opinion` | polity, mind | intercept, forge or deliver a message; set opinion | message traffic map; opinion charts | context: inbox with delays; tools `send_envoy`, `write_letter`, `encipher` | `message.*`, `opinion.*` | existing messages kept |
| F22 belief state | `beliefs` | every decision | reveal truth to an actor; plant a false belief | belief-against-truth toggle | the agent context *is* the belief view | n/a | initialised from the truth for co-located facts |
| F23 material physics and tissues | material columns; tissue catalog | campaign, body | edit material properties | penetration explainer | n/a | `wound.*` | catalog |
| F24 production methods, energy, pollution | `production_methods`, `energy`, `region_pollution` | production | set a site's method; clean pollution | production chain view; energy and pollution layers | context: methods at the actor's sites; tool `set_method` | `industry.*`, `pollution.*` | method from existing knowledge |
| F25 gatherings | `gatherings` | society | convene or cancel a gathering | gatherings calendar | tools `host_gathering`, `attend` | `gathering.*` | none |
| F26 genetics | `genomes` | demography | edit genes | appearance view; family resemblance | context: appearance summary | `lineage.*` | random genomes consistent with parents' records |
| F27 storyteller | `storyteller_state` | post-transition | set the profile; boost or calm | tension chart | n/a | n/a | computed |
| F28 conservation | `conservation_ledger` | every stage | none (a test harness) | ledger inspector (maintenance) | n/a | n/a | n/a |
| F29 households and dwellings | `households`, `dwellings` | demography | move a mortal; edit a dwelling | household view | context: household standing | `household.*` | from kin bonds and locations |
| F30 effect packages | `effect_packages`, `afflictions` | body | afflict or cure | afflictions list | context: visible afflictions | `affliction.*` | from flags (cursed, immortal) |
| F31 dominion and scales | `dominions` | transition | set dominion; edit scales | dominion map | son context: dominion map summary; tools `consecrate`, `contest_dominion` | `dominion.*` | from temples, worship and patron worlds |
| F32 collective behaviour | `mobs` | society | spark or calm a crowd | riot replay | n/a | `crowd.*` | none |
| F33 historiography | `accounts` | society-engine | write, revise or erase an account | accounts against truth viewer | context: the actor's own people's account; tool `commission_history` | `history.*` | historian views become folk accounts |
| F34 storylets | `storylet_state` | post-transition | trigger or suppress a storylet | storylet queue | the choice offered as a tool call | storylet templates | none |
| F35 norms and volition | `social_norms` | mind | edit norms | norms table | context: norms of the current situation | `norm.*` | culture-seeded |
| F36 arcs | `arcs` | post-transition | assign or close an arc | arcs board | context: own arc stage (sons and selected mortals) | `arc.*` | none |
| F37 cycles and long plans | `psi_state`, `asabiyya`, `long_plans` | transition | edit; start or abort a long plan | PSI dashboard; plans list | context: the realm's stress summary; tool `adopt_long_plan` | `cycle.*`, `plan.*` | computed |
| F38 reciprocity | `gifts` | society | give, return or cancel | gift ledger | tool `give_gift` | `gift.*` | none |
| F39 nutrition | `diets` | demography | set a diet | nutrition chart | context: diet quality | `diet.*` | computed |
| F40 biases | trait and facet driven | every decision | toggle a bias per actor | decision explanations | n/a | n/a | computed |
| F41 purity and castes | `purity`, caste data | mind | purify or defile; edit castes | purity status | context: purity state | `purity.*` | culture-seeded |
| F42 luck and witchcraft | charm items, `accusations` | society | accuse, acquit, reveal a real witch | accusations log (truth visible) | tools `accuse`, `consult_diviner` | `witch.*` | none |
| F43 identity salience | `identities_held` | mind | set salience | salience chart per community | context: dominant identity | `identity.*` | from people, faith and class |
| F44 technology eras | techniques catalog extension | society-engine | grant a technique; set the era cap | tech graph (era bands) | tool `choose_research` | `era.*` | from existing knowledge levels |
| F45 world-type rules | `world_type_profiles` | every stage | edit a profile per world | world profile card | context: world peculiarities | `world.*` | from the world type |
| F46 biology rules | `biology_variants` | every stage | edit variants per people or species | biology card | context: own biology constraints | `biology.*` | from existing body plans and flags |
| F47 lifecycle ends | rules only | per owner section | force an end; revive | ends shown on entity status | n/a | `end.*` | n/a |
| 4.8 oaths | `oaths` | society | swear, release or break | oaths list per figure | tool `swear_oath` | `oath.*` | from oathbreaker flags |
| 4.9 society and labour | allocations, regimes | demography, production | set an allocation; impose corvée | labour Sankey | context: labour situation | `labour.*` | computed |
| 4.10 community relations | aggregates | mind | edit opinion components | relation "why" | context: relations | `relation.*` | from existing values |
| 5.13 treaty | `treaty_profiles`, `treaty_clauses` | polity | draft, sign, break or void a treaty; add a guarantor | treaty builder; treaty card (clauses, breaches) | tools `propose_treaty`, `accept_treaty`, `break_treaty` | `treaty.*` | from ally, truce and tribute bonds (J.2) |
| 7.3 vessel | `vessel_profiles`, `designs` | production, campaign | build to a design, refit, repair, scuttle | vessel card (components, wear) | tool `commission_vessel` | `vessel.*` | from existing stats |
| 7.4 artwork | `artwork_profiles` | society-engine | commission, destroy, canonise | artwork card (subject, message, market) | tool `commission_artwork` | `art.*` | medium from subtype, one-time map |
| 8.2 legend | `legend_profiles`, `legend_cycles` | society-engine | set credence and distortion; fix into an artwork | legend card (truth against telling) | context: legends known | `legend.*` | from spread and category |
| 8.3 tradition | `tradition_profiles`, `tradition_effects` | society | start or abolish a tradition; set its calendar slot | tradition card with effects | tool `found_tradition` | `tradition.*` | kind from subtype, one-time map |
| 8.4b theory | `theory_profiles` | society-engine | plant, refute or reveal a theory | theory card (existing) | son tool `reveal_truth`; mortal tool `propose_theory` | `theory.*` | none |
| 8.5 ideology | `ideology_profiles`, `ideology_adherents` | society-engine | found or suppress an ideology | ideology card; adherents map | tool `found_school` | `ideology.*` | none |
| 8.6 rite | `rite_profiles`, `rite_effects`, `castings` | every stage where cast | teach, forbid, cast or dispel | spell designer; casting log | tools `design_rite`, `cast_rite` | `rite.*` | from wizard and magic flags |
| 8.7 prophecy | `prophecy_conditions` | transition | set a condition; fulfil or void | prophecy card (condition, status) | tool `prophesy` (typed condition) | `prophecy.*` | conditions empty for old prophecies (the LLM-judged path remains for them) |
| 8.8 event | collections | every stage | end or extend an event | event card with phases | context: ongoing events | event templates | existing events |
| 9.2 creator | `creator_taboos`, `creator_standing` | post-transition | edit taboos and passions | creator page: standing map, attention budget | n/a (the player is the creator) | `creator.*` | taboos from GodDepth (one-time map) |
| 9.3 foreign god | as son tables | transition | same levers as sons | foreign god page (aspects, dominion, relations) | foreign god context (when a god acts through the engine) | `foreign_god.*` | from existing rows |
| 9.4 council | motions, offices | transition | call a council; veto a motion | council minutes with typed motions | council prompt with typed motions | `council.*` | existing councils |
| 9.5 natural law | law profiles | transition | enact, weaken or repeal; set scope | laws of nature panel per world | son tool `decree_law` | `natural_law.*` | kind from the existing enum |
| 9.6 outer being | profiles, bargains | transition | summon, banish, seal a breach | outer being card (hunger, breach points) | son tool `bargain` (typed terms) | `outer.*` | from existing rows |
| 10.1 star | `star_physics` | transition | set mass, age, stage; rekindle | star card with evolution track | son tools on stars (existing) | `star.*` | mass and age inferred from the type and brightness |
| 10.2 world | `world_physics`, `world_life` | transition | edit physics inputs; change type | world physics card | context: world summary | `world.*` | inputs inferred from the stored gravity, atmosphere and terrain |
| 10.3 celestial | orbital elements | transition | set orbit and return | sky calendar | context: visible omens | `sky.*` | from existing rows |
| 10.4 route | extended columns | travel | open, close, toll, escort | route card (windows, traffic) | tools on travel (existing) | `route.*` | existing |
| 10.5 journey | extended columns | travel | redirect, rescue, wreck | journey card (cargo, convoys, encounters) | traveller context | `journey.*` | existing |
| 10.6 phenomenon | `phenomenon_profiles`, `phenomenon_footprints` | environment | create, grow, contain or seal | phenomenon layer | son tool `shape_phenomenon` | `phenomenon.*` | from flags (eternal storms, leak wounds) |
| 10.7 climate | circulation and oscillation state | environment | impose a regional target; trigger an oscillation | climate layers | context: climate news | `climate.*` | from the existing climate era |
| 10.8 doom and leak | contributors, `region_leak` | transition | adjust a contributor; set regional leak | doom panel with sources | context: omens | `doom.*` | existing values spread by sources |
| 10.9 cosmic physics | physics tables, `impact_events`, `cosmic_features`, `star_systems` | transition | edit inputs; trigger or deflect an impact | orbit view; impact warnings | son tools `call_impact`, `deflect_impact` | `cosmos.*` | inferred inputs (10.2 row) |

**Fate checks for creatable types** (decision 41). Fate's structured judgement validates the typed fields of every created record:

| Type | What Fate checks |
|---|---|
| species and beast | body plan, diet, habitat, biochemistry against the world (F46, 10.9), traits consistent with anatomy |
| people | biology variant against the world type (F45), kinship and marriage system completeness |
| polity | government, decision rule and succession law consistency |
| house | founder and seat exist |
| title | de jure territory coherent with rank |
| law | parameters valid for the kind |
| cult | tenets not mutually precluded; doctrine against the patron's aspects |
| item and structure | material workable at the maker's technique; kind-specific fields |
| art form | structure fields valid for the discipline and the language |
| theory | domain and claims typed; correctness set by the engine, not by the creator |
| ideology | tenets and the value delta coherent |
| rite | technique and form within the creator's aptitude; cost proportional to power |
| prophecy | the condition is machine-checkable |
| natural law | effect, scope and upkeep valid; contest with existing laws |
| phenomenon | footprint and effects typed |
| treaty | clauses executable |
| disease | vectors and hosts exist |

Records that fail are corrected by Fate (existing behaviour: `fate_note`) or rejected.

**The compliance test** (`backend/tests/test_mechanic_compliance.py`, added in W0). The interconnection registry (I.1) lists every mechanic (a rule namespace with at least one phase writer). For each mechanic, the test asserts:

1. a phase writer exists (automatic);
2. at least one player lever route exists and has a frontend caller (extending the existing route ↔ caller test);
3. a UI surface is registered (`frontend` route or drawer tab key);
4. for agent-facing mechanics, a context block or typed tool exists in `prompts/`;
5. every incident kind it emits has an English template key;
6. every table it owns has a backfill rule in the fix-up registry;
7. every countable stock it owns appears in the conservation ledger (F28).

A mechanic missing any of these fails CI, so this catalogue cannot silently fall behind the code.

### J.17 Seventh-pass integration addendum

| Wave | Content | Depends on |
|---|---|---|
| W0 (extended) | the compliance test and the compliance catalogue registry (J.16); the conservation ledger harness (F28); the class-by-class sweep listings (1R.22) generated from the registry | — |
| W36 | F45 world-type profiles: every foundation reads its world-type view; the exotic rules of the 17 non-ordinary types | W1, W12 |
| W37 | F46 biology variants: every foundation reads its biology view; the twelve variants | W2, W3+, W10 |
| W38 | F47 lifecycle ends and decays; fossils, museums and collections, designed landscapes | W9+, W13 |

Every earlier wave also delivers its J.16 rows (levers, UI, LLM exposure, templates, backfill) within the same wave, because the compliance test fails otherwise.

**Tests:**

- **World-type tests:** a seeded run on each world type (all 34) completes 20 epochs with no foundation raising an applicability error, and each exotic rule shows up in incidents. Examples: no fires on an asteroid without air, cloud-band settlements on a gas giant, mutiny on a generation ship.
- **Biology tests:** each variant's people completes 20 epochs. Examples: aquatic peoples smelt only with vents or trade; constructs need power upkeep; ageless peoples' grudges never decay.
- **Lifecycle-end tests:** every stock in A2 reaches zero or equilibrium under no input; there is no runaway growth over 200 epochs in LLM-free runs.

### J.18 Eighth-pass integration addendum

| Wave | Content | Depends on |
|---|---|---|
| W39 | F48 prehistory and deep-time runs (genesis integration, the prehistory digest for Fate and the chronicler, the fast-forward lever, the son policy model) | W12+, W27, J.11 |
| W40 | F49 transformation graph (all new transformations) with the transformation registry in the compliance test | W11, W15, W21 |
| W41 | B1 couplings: sign languages, sociolects, rite components, carrion pulses, the heritable gift, ecosabotage, conditions on schemes; B2 verbs: field diplomacy, spirit teachers, beast lore keepers; B3 brakes: novelty cycles, sealing the deep, office creation, closures; loop delay rules | W15, W16, W17, W19, W24 |

**Tests:**

- **Prehistory tests:** a 40-epoch prehistory produces language families with recoverable cognates, at least one ruin and one dormant title, and the same output for the same seed.
- **Transformation tests:** each transformation preserves the identity, history and bonds of the node.
- **Loop delay tests:** balancing loops do not oscillate beyond the bands set in `docs/spec/13-balance-bands.json`.
- **Coupling registry test:** every ordered subsystem pair is either coupled or listed as intentionally empty.
- **Stories 29–30.**

### J.16b Compliance catalogue, ninth-pass rows

The rows below complete J.16 for F48 and F49 and for the features added by reference passes 5–8 inside entity sections. The compliance test (J.16) enforces every row.

| Feature (section) | Trigger stage | Player levers | UI | LLM exposure | Templates | Backfill |
|---|---|---|---|---|---|---|
| F48 prehistory and fast-forward | world creation; on request | set the prehistory epochs and resolution; run, abort or discard a prehistory; fast-forward N epochs | prehistory digest view; a timeline of the legendary age | Fate and chronicler prompts receive the digest | `prehistory.*` | existing worlds: lore-only backfill (F48 reference pass 9) |
| F49 transformations | per transformation | force or block a transformation; revert one within the epoch (ledger undo) | the entity's "former type" history; a transformation timeline | context: a transformation's prospects for agents (a mortal near mantling, a son near a fall) | `transform.*` | from existing records (deification, uplift, local gods) |
| Taverns and inns (4.2 reference pass 5) | society | build or close | a settlement tile; a hub activity panel | context: tavern rumours for local agents | `tavern.*` | none |
| Welfare institutions (4.2 reference pass 5) | society | found, fund or close | a welfare panel per settlement | tool `found_charity` | `welfare.*` | none |
| Commuting (4.2 reference pass 5) | production | set a worker camp | labour reach overlay | n/a | n/a | computed |
| Cuisines (4.2 reference pass 5) | society | edit a cuisine | cuisine card per culture | context: dishes for feasts | `cuisine.*` | culture-seeded |
| Evidence (4.5 reference pass 5) | polity | plant, destroy or reveal evidence | investigation board | tools `investigate`, `destroy_evidence` | `evidence.*` | none |
| Citizenship, travel regulation, poor relief, measures (4.6 reference pass 5) | polity | edit categories; set border rules; fund relief; standardise | realm law panels | tools `grant_citizenship`, `issue_pass` | `citizen.*`, `border.*`, `relief.*` | from existing foreigner-rights laws |
| Fisheries and closures (6.1 reference passes 5 and 8) | production | set stocks; declare a closure | fishery layer | tool `declare_closure` | `fishery.*` | stocks from water regions' fertility |
| Sealing the deep (6.1 reference pass 8) | environment | seal or unseal | seals on the strata view | tool `seal_breach` | `seal.*` | none |
| Chemical industries (6.3 reference pass 5) | production | set methods (via F24) | in the production chain view | via `set_method` | `industry.*` | none |
| Insurance, incorporeal property (6.4 reference pass 5) | economy | underwrite or void; grant or revoke rights | insurers' board; a rights registry | tools `insure`, `license_right` | `insurance.*`, `rights.*` | none |
| Saving, exchange rates, economic systems, tourism, containers (6.4 and 4.6 reference pass 6) | economy, polity | set the economic system; set rates; edit containers | an economy panel per polity | tool `set_economic_policy` | `economy.*` | system from existing structures (temples, palaces) |
| Optics, clocks (7.1 reference pass 5) | society-engine | grant devices | items and structures cards | n/a | `device.*` | none |
| Writing media, locks (7.1 reference pass 6) | society-engine | set the medium; set vault security | archive survival panel | n/a | `archive.*` | media from writing systems |
| Museums, gardens (7.2 reference pass 7) | society-engine | found, curate, loot or restitute | museum and garden cards | tool `found_museum` | `collection.*`, `garden.*` | none |
| Fossils (6.2 reference pass 7) | environment | place or reveal fossil beds | fossil layer | context: finds | `fossil.*` | from extinct species and previous-creation records |
| Games (7.4 reference pass 5) | society | invent, ban, spread | games card per culture | n/a | `game.*` | none |
| Numeracy (8.4 reference pass 5) | society-engine | set the number system and numeracy | culture card field | n/a | `number.*` | culture-seeded |
| Material magic, sympathy, rite components (8.6 reference passes 5 and 8) | per casting | edit affinities; grant or destroy links | spell designer fields | tool parameters on `cast_rite` | `rite.*` | none |
| Emotion spirits (3.3 reference pass 5) | mind | spawn or dispel | spirit layer | n/a | `spirit.*` | none |
| Spirits as teachers (3.3 reference pass 8) | mind | grant or block a teaching | teaching log | son tool `send_teacher` | `teaching.*` | none |
| Beast lore keepers (3.3a reference passes 8 and 9) | mind | grant lore; reveal accounts | beast card accounts tab | sapient beasts' agent context | `lore.*` | none |
| Carrion pulse, the dead without scavengers (3.2 reference pass 8, F45 reference pass 9) | environment | clear or keep the dead | carrion layer | n/a | `carrion.*` | none |
| The magical gift (F26 reference pass 8) | demography | edit aptitude | gifted-share chart | context: own aptitude | `gift.*` | random, consistent with existing wizards |
| Ecosabotage, scheme conditions (F20 reference pass 8) | polity | via schemes | scheme board | tool `start_scheme` kinds | `scheme.*` | none |
| Sign languages, sociolects (8.1 reference passes 8 and 9) | society-engine | create or merge | language card variants | context: the actor's registers | `language.*` | none |
| Field diplomacy (5.8 reference passes 8 and 9) | campaign | force a parley; void an agreement | war room parley log | tools `parley`, `offer_terms` | `parley.*` | none |
| Novelty cycles (7.5 reference pass 8) | society-engine | set novelty | art-form fashion chart | n/a | `fashion.*` | computed |
| Office creation (4.6 reference pass 8) | polity | create or abolish an office | offices chart | tool `create_office` | `office.*` | existing offices |

### J.16c Generic lever and surface layer (the compliance guarantee by construction)

Bespoke levers (J.16, J.16b) make the common actions convenient. Completeness is guaranteed by a **generic layer** that every mechanic gets automatically from its registration, so rule 6 holds even for sub-mechanics that no catalogue row names.

**Mechanic registry.** Every rules namespace with an engine writer registers a `Mechanic` descriptor (in `engine/interconnect/registry.py`, I.1):

- **key, owner subsystem and target types** (the entity types it acts on);
- **trigger handler** `trigger(ctx, target, params)`: runs the mechanic now on a target (for example run a theodicy crisis check on a cult now, or run an expedition into this site now);
- **block handler** `block(ctx, target, epochs)`: suppresses the mechanic on a target for a number of epochs (stored as a modifier, F9, so it is visible and undoable);
- **typed fields** it owns (Pydantic models), which the **generic record editor** can edit with validation and pair constraints (decision 69);
- **incident kinds** it emits, each with an English template key (decision 71);
- **agent exposure**: none, context, or a tool, with the tool's typed input model (decision 21) and its description id in `prompts/` (decision 26);
- **UI descriptor**: the entity drawer section and map layer it appears in, and the chart kind for its stocks;
- **backfill rule id** (G10) and **conservation flows** (F28).

**Generic player levers** (available for every registered mechanic, through one API family and one UI pattern):

1. **Run now** on a target (the trigger handler).
2. **Suppress** on a target for N epochs, or **unsuppress** (the block handler).
3. **Edit the fields** the mechanic owns on a target (the generic editor, validated).
4. **Tune** its rules (the existing World Rules editor, already per namespace).
5. **Pin** a field so that the mechanic cannot change it (a pin modifier).

All five are ledger-recorded and undoable (decision 61).

**Generic surfaces:**

- every entity drawer has a **Mechanics** tab listing the registered mechanics acting on that entity, their last effects (incidents), their current modifiers ("why", F9) and the five generic levers;
- every map has a layer per mechanic with a spatial stock;
- every stock has a time-series chart from the epoch statistics.

**Generic agent exposure:** every mechanic marked `context` contributes a typed block to the agent context of affected agents, ordered by relevance and bounded only by the generous ceiling of decision K.15. Every mechanic marked `tool` is offered to agents whose gates allow it.

**The compliance test (J.16, extended)** now iterates the mechanic registry and asserts, for **every** mechanic:

- trigger and block handlers exist;
- the owned fields are editable through the generic editor;
- the incident templates exist;
- the UI descriptor resolves to a real frontend surface (a Playwright check that the Mechanics tab renders the mechanic on a fixture entity);
- the backfill rule and the conservation flows are declared.

A mechanic that registers without them fails the build, and a writer phase that writes a namespace without a registered mechanic also fails. This turns rule 6 into a structural property of the code: no mechanic can exist without a lever, a surface, templates and backfill, whether or not this document names it.

### J.19 Completion contract (decision K.16)

Integration happens in waves, but **the whole of this document is the deliverable**. Partial completion is a stage, never an end state:

1. **Traceability matrix:** `docs/spec/13-coverage.md` (created in W0, in the format of the existing `docs/spec/coverage.md`) lists every numbered item of this document. That means every foundation, every entity section and reference-pass block, every gap row of Part 1R, every loop, story, wave, table and rules namespace. For each item it records the module, the automatic trigger, the player lever, the UI surface, the LLM exposure, the template family, the backfill rule and the test.
2. **Done means every column is filled.** An item counts as integrated only when every column is filled and its tests pass. The compliance test (J.16, J.16c) checks the code side, and a coverage test checks that every item of this document has a row and that no row is empty.
3. **No silent deferral:** no item may be dropped, simplified or postponed without the user's explicit approval, recorded in the matrix with the reason. "Later" without approval is not a status.
4. **Wave reports:** at the end of every wave, the report lists the items completed, the items remaining, and any divergence from this document, with the reason. Nothing is reported as done unless its row is complete and its tests pass.
5. **Final check:** integration of TODO item 1 is complete only when the coverage matrix has no open row, the compliance and conservation tests pass, the depth metric meets the J.7, J.10, J.12–J.15 and J.17–J.18 targets, and the acceptance stories 1–30 run as scenario tests.

---

## Part K. Decisions

### K.1 Resolved (2026-11-02, by the user)

| # | Topic | Decision | Where it applies |
|---|---|---|---|
| K.1 | Sub-epoch time | Epochs stay 50 years. Two inner clocks are added (F1): `time.sampled_years` [5] per epoch for harvest, disease and weather variance, and campaign seasons per war for marching, attrition, sieges and battles with a real season and weather. Epochs are not shortened. | F1, Part 5 |
| K.2 | Existing worlds | No classic/deep profile and no epoch replay. Worlds upgrade in place "as if it had always been so". Everything derivable is backfilled; lore that cannot be backfilled stays as written and follows the new rules from the next epoch. | G10, J.2 |
| K.3 | Depiction of harm | Plain, non-graphic statements ("he lost an eye", "her hand was cut off"). No anatomical or sadistic detail, no gratuitous cruelty. | G9, J.8 |
| K.4 | Named mortals | No ceiling. Mortals are never deleted or merged back into cohorts. Low-importance ones may become dormant for performance only. A loose soft limit of 10,000 per world only slows promotions from cohorts. | F12 |
| K.5 | Civilization tiers | As broad and deep as possible: mechanical tiers at the polity, community and regional-standing levels, each with requirements, unlocks, hysteresis and decline causes. | 4.6 behaviour 6 |
| K.6 | Per-people view of gods | Approved. Every people holds `son_standing` (awe, love, fear, neglect) toward every god it knows, alongside its single patron. Decision 27 is unchanged: worship stays single-patron, and standing only shapes prayers, fears, conversions and grudges. | 9.1, 9.2, 9.3 |
| K.7 | Reincarnation | Rare and earned, never the default. It needs an open gate (doctrine, law, rite or god) and an exceptional soul, and even then it is a low chance. Rites and tenets can block it. | 3.3 |
| K.8 | Engine tick time | The tick budget is **CPU computation** of the deterministic engine (no LLM inside it). It is met by making the engine efficient and multicore (J.11), not by raising the target: `engine_budget.tick_target_seconds` stays [20] for the reference world. Separately, LLM-bearing steps (son, mortal and Fate turns), whose prompts grow with the typed context blocks of J.8, get comfortable per-call and per-turn timeouts (`model.*` and `agents.*` timeout rules raised so that no turn is cut off by growth in context). | J.11, J.8 |
| K.9 | Sensitive acts as data | Kept. Cannibalism, infanticide, incest degrees, human sacrifice and similar acts stay in the ethics catalog (F16) as typed acts that cultures allow or condemn. Narration follows G9: stated or implied, never described in detail. | F16, G9 |
| K.10 | Mortals replacing gods | Possible but rare: the god must be weak, the mortal overwhelming, and the mortal must kill the god. This applies to the player's sons too, with notification and J.16c levers; Fate approves | 3.1 reference pass 3, 9.1 reference pass 3 |
| K.11 | Falls and corruption of sons | Both stay, with an advance warning to the player and intervention levers before they happen; integrated through the existing son status, god-death and outer-being mechanics, not as special cases | F49, F49 reference passes 9 and 10 |
| K.12 | Belief shaping gods | Stays. Its strength is an equation of belief intensity, worship share, crisis severity and the god's malleability (facets and existence). A pin lever stops it on pinned fields | 9.1 reference pass 3, J.16c |
| K.13 | Technology ceiling | None: worlds advance as far as their history carries them, under structural plausibility guards (scale gating, collective prerequisites, visible escalation, physical bounds, Fate's check; cosmic ends only through doom, divine war or the Creator) | F44 |
| K.14 | Prehistory length | Default 0: worlds start from the player's and the sons' creations. Any length is selectable at world creation, and a prehistory can be seeded later for a world still empty of lore | F48 |
| K.15 | LLM context size | Haiku stays the only model. No restrictive cap: the only ceiling defaults to the model's full input window minus output, and blocks are ordered by relevance, not trimmed | J.8, J.16c |
| K.16 | Integration completeness | Waves are fine, but the whole document must be integrated. A traceability matrix, coverage and compliance tests, wave reports, and no deferral without explicit approval | J.19 |
| K.17 | Storyteller pacing | Default profile cyclic; selectable in genesis and editable; existing worlds get cyclic | F27 |
| K.18 | Linear or cyclic cosmos | Existing cosmoses stay linear; the genesis default is linear, with cyclic selectable | 10.8 reference pass 4 |
| K.19 | Mechanical harshness | One harshness dial (heroic, realistic, brutal), default realistic, scaling all lethality and loss rates as a group; editable in World Rules | G11 |
| K.20 | Scales beyond the star (2026-11-09) | The cosmos is one whole with dimensions, clusters and galaxies as node kinds (10.10–10.16), real and fantasy kinds for each, all controllable. Existing cosmoses lie in a prime dimension, a home group and a home galaxy holding every existing star, as if it had always been so (G10). The stored star position is its position inside its galaxy | 10.10–10.16, G10 |

All first-pass decisions are resolved.

All second-pass decisions are resolved as well. Decisions K.10–K.19 were taken after the tenth pass, and K.20 with the scale ladder of W12. No design question remains open.
