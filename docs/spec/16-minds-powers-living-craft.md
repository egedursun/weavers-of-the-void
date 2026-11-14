# 16 — Made Minds, Innate Powers, Living Craft, the Depth Pass and Typed Kinds (W44–W48)

This spec adds five waves to the lore engine:

- **W44 Made minds and the information age.** Minds that live in made things or in no body at all; copies, saves, transfers and merges of minds; augmented bodies; networks, intrusion, surveillance and information conflict; corporations and private power; self-making machines; abundance; and the collapse of high making into relics and salvage.
- **W45 Innate powers, power sources and concealment.** Powers that belong to a being rather than to a learned rite (the psionic class and every other inborn, awakened, granted or bonded power); an open model of power sources that any world can author; magic systems as typed world structures; and hidden truths kept from the public (the masquerade class), with breach, revelation and forgetting.
- **W46 Living craft.** Technology made by growing, breeding, shaping and engineering living things: designed crops and herds, grown structures, living vessels, living arms, grown bodies and organs, cloning, symbionts and parasites, living medicine and designed disease, living production, living links and living computation, world-shaping ecologies and designed sapience.
- **W47 The depth pass.** Every existing or planned mechanic brought to full breadth and depth: structures that act in their own right, eras and customs at full breadth, the god layer, typed models in place of fixed lists that carry images, every enum value read, every thin spec section completed, and guards that keep each of these from coming back.
- **W48 Typed kinds.** Every concept a world can define in its own terms: a neutral category enum plus authored kinds with typed properties for goods, food, drink, dress, colour, scent, household goods, tools, instruments, games, substances, money, professions, ranks, titles, clergy, organisations, kinship, traditions, art, tenets, fears, goals and the cosmos; a property catalogue for every content enum; one taxonomy per concept; every value that carries an image or a gender renamed; and guards for all of it.

Every wave is written to be integrated completely, under the completion contract of spec 13 J.19 and the standing rules of `CLAUDE.md`. Nothing here is label-only, optional or deferred.

---

## Part 0. Scope, numbering and ground rules

### 0.1 The gap this spec closes

Spec 13 and the waves through W43 built a deep pre-modern, magical and cosmic world, and W42 widened the typed catalogues so a modern or spacefaring world can be named in its own kinds. Three families of lore still cannot be told by the engine:

1. **Minds that are not born in a body.** W42 added the `ai_core`, `robotics_works`, `cloning_facility` and `data_centre` structures, the `machine_rule` government, the `algorithm` selectorate, the `machine_law` and `data_privacy` laws, the `implant` equipment family with its `neural_implant` kind, electronic warfare and drone operators. Each acts as an older kind for the tables that read it. Spec 13 plans constructs with literal orders (3.3a reference pass 4) and lists "artificial minds" in one row of F44. Nothing models a mind as something that can live in a made thing, be copied, saved, restored, moved or merged, wake from complexity, hold rights, be owned, be attacked through a network or exceed its makers. Augmentation exists only as a prosthesis for a lost part. There are no networks, no intrusion, no surveillance state, no self-making machines, no economy of abundance and no relic technology.
2. **Powers that are not rites.** Magic is modelled as rites: designed in laboratories, learned from texts, cast with components, drawn from six fixed external sources (`MagicSource`: ley, divine, blood, soul, reagent, void), made reliable by a paradigm theory and broken by iron. A being's own innate power, drawn from itself, used at once without a rite, resisted by discipline, strained by use, possible in a world without magic, amplified by devices and joined in linked minds, cannot be expressed. A world cannot author a source of its own. Whole populations hiding a truth from the rest of the world cannot be expressed: secrets (F20) are individual.
3. **Technology made of life.** W42 added the `bioship` frame, the `grown` building form and `vat_grown` food, all acting as older kinds. Breeding exists as bloodline plans (W22) and genetics as F26. Nothing models a made thing that is alive: that grows, eats, heals, breeds, ages, sickens, escapes and evolves, and that can be designed from the traits of organisms the makers can reach.

### 0.2 Numbering and placement

- **Waves.** W1–W41 are planned in spec 13 Part J; W42 (breadth across settings, 10.18) and W43 (genesis from the seed, 10.19) were added later and are done. The waves of this spec are **W44**, **W45**, **W46**, **W47** and **W48**.
- **Identifiers continue spec 13's series** so that no identifier is shared:
  - shared foundations **F50–F56** (spec 13 ends at F49);
  - wave sections **44.1…**, **45.1…**, **46.1…**, **47.0…**, **48.0…**, and the foundation **F57**;
  - reference lanes **R43–R53** (spec 13 ends at R42);
  - couplings **C10…** (spec 13 ends at C9);
  - feedback loops **L79…** (spec 13 ends at L78);
  - acceptance stories **AS31…** (spec 13 ends at AS30);
  - decisions **K.21…** (spec 13 ends at K.20).
- **Coverage.** `scripts/spec_coverage.py` reads only `13-depth-expansion.md` today. The first step of W44 extends it to read this file and to write `16-coverage.md` with the same columns and the same rules (5.10). Every numbered item of this spec then has a row, and the commit gate checks it.

### 0.3 Decided scope (user decisions, 2026-11-14)

1. **One coherent timeline.** The chronicle never branches. There is no time travel and no alternate history. Everything in this spec that touches time keeps to one timeline: a copied mind is a second mind in the same history; a restored mind lacks what happened after its save while the world keeps it; foresight gives typed probabilities and acts through the existing prophecy mechanics; dormancy skips a mind's experience, never the world's.
2. **W44** carries made minds, the separation of mind from seat (copies, symbionts as co-minds, designed sapience), augmentation, self-making machines, information conflict, corporations, abundance and the collapse economy with relics and salvage.
3. **W45** carries innate powers (the research in 45.0 found that the psionic class does not reduce to the existing rite and essence model), the widening and deepening of power sources, magic systems as world structures and concealment.
4. **W46** carries living craft as its own concept with its own depth.
5. **Everything is complete.** Each wave is as wide and as deep as the engine's structure allows: typed state, engine behaviour, agent tools, prompts and context, god levers and screens, the Codex and the lore book, integrity checks, legacy mapping, tests and spec coverage.
6. **W47** (decided the same day) brings every existing and planned mechanic found narrow or shallow by measurement to full breadth and depth (Part 7).
7. **W48** (decided the same day) gives every world-content concept the two-layer model of typed kinds (Part 8).
8. **Flexibility, never bias.** These waves widen what a world can become. They must not pull every world toward their own images (0.5).

### 0.4 Ground rules carried into every section

The ground rules of spec 13 Part 0 (G1–G11) and the standing rules of `CLAUDE.md` bind every section here. How each applies:

| Rule | Application in this spec |
|---|---|
| G1 no magic numbers | Every threshold, rate, cost, chance and cap below is a rule key in a named namespace (each section lists its namespace) and editable in World Rules. |
| G2 explicit fields | Seats, sources, powers, augments, networks, hidden truths and living profiles are typed rows with typed enums. Prose is written beside them for reading and never parsed. |
| G3 determinism | Every new phase draws from seeded per-phase streams. Copies, awakenings, breaches and mutations of designs are deterministic for a seed. |
| G4 automatic, overridable, visible | Every mechanic runs on its own, every value is editable by the god, every row can be held against the engine and every mechanic has a screen. |
| G5 phase units | Every new step is an `async def phase(ctx)` unit with no transaction across an await. |
| G6 typed context | The model reads these mechanics through typed context blocks (5.3), never through prose summaries of prose. |
| G7 typed rows over JSON | Nothing the engine queries is stored in JSON. Flag sets are boolean columns or link rows. |
| G8 prose stays | Each new entity and record keeps a prose description written from its typed fields by the deepener. |
| G9 plain narration of harm | Designed disease, mind deletion, compulsion, forced copying and every other harm is narrated plainly and behind closed doors through `_harm_narration.md.j2`. |
| G10 as if it had always been so | Each wave's first epoch after upgrade runs recorded fixups that give existing worlds the new state from what they already hold (5.7). |
| G11 one harshness dial | Strain, burnout, rejection, decay, infection and runaway hazards scale with the harshness profile. |
| Rule 1 no unneeded tests | Each step runs the static gates and the tests that cover it; broad suites only when the user asks. |
| Rule 2 prompts never constrain the lore | 0.5 and 5.3. |
| Rule 3 every dynamic wired | Each section ends in the compliance catalogue of its wave, which names the engine, tools, prompts, API, screens, god levers, Codex, book, integrity, legacy and spec rows. |
| Rule 4 no comments | Code written for these waves carries no comments or docstrings. |
| Rule 5 production grade UI | Every screen in 5.5 and in each wave's catalogue is built from the design system with loading, empty, error and disabled states, paging, responsive layout, both themes and accessibility labels. |
| Rule 6 the god controls everything | Every table has create, edit, hold and delete levers registered in the action catalog and reached from a panel; per-thing sections live in `ThingSections.tsx` and reach every kind of node (5.1). |
| Rule 7 Codex and book | Every table renders in node entries through `services/books/typed.py` or as a designed table in "Records of the Cosmos" (5.4). |
| Rule 8 defects close their class | Every tool has a success case in `every_son_tool.py` or `every_mortal_tool.py`; every lever in `every_lever.py`; every new guard is a check script or test (5.9). |

### 0.5 Setting neutrality: function over look

The concepts of this spec are known from particular genres, and each genre comes with its own images. The engine must hold the concept and leave the images to the seed. These rules apply to every enum value, rule label, tool text, schema description, prompt template, `prompts/data` line, catalog line, chronicle template, genesis template seed, frontend placeholder and suggestion list added or changed by W44–W46.

1. **Concepts are defined by what they do.** A made mind is a mind whose seat was made; whether the seat is a carved figure, a written formula, a lattice, a machine, a ship or a grown organ is the world's choice and lives only in prose written by the model from the seed. A network is a set of places that pass messages or control along a carrier; the carrier is typed by how it works (relay, wired, broadcast, mesh, mind link, rite link, grown link), not by how it looks. A power source is typed by what is spent, where it is drawn from and how it renews.
2. **Every concept fits every era and every kind of world.** Each section states how its mechanic reads in a world without machines, in a world without magic, in an ancient world and in a far-future world. A made mind can exist in a bronze-age world with rites and in a spacefaring world with computation; an innate power can exist in a world without magic; living craft can be selective breeding, shaping by rite or engineering by technique.
3. **No example lists, sample sentences or canned lines** in any text the model sees. Enum values are function words. Descriptions say what a field holds, not what it might look like.
4. **No default persona or temperament for made minds.** No text says or implies that made minds are cold, logical, emotionless, literal-minded by nature, hostile, servile, curious about humanity, longing for a body or destined to rebel. A made mind's affect, values and will come from its make, its makers' culture, its history and the world's laws.
5. **No quotas or mandates.** No forced uprising of made minds, no mandatory price for every power, no rule that every world hides something, no forced breach, no inevitable runaway, no default dystopia or utopia for abundance, no mandatory body horror in living craft, no forced conflict between the born and the made.
6. **No fixed tone for a concept.** Surveillance, corporations, concealment, augmentation and designed life carry no built-in moral colour. Their effects come from typed values (a people's liberty value, a law's level, a doctrine's stance).
7. **No gendered defaults.** Made minds, copies, clones, gestalts and designed beings have no default gender and are referred to neutrally unless their own typed profile says otherwise.
8. **No hardcoded visual medium.** Visual direction for new kinds (networks, made minds, augments, living craft) is built from typed fields at render time; image style is applied at render time.
9. **Never constrain the model to fix drift.** If worlds drift toward the same images, the fix is in our text, never a ban on the model's own words.
10. **Mechanical gates.** `scripts/check_prompt_bias.py` gains the families listed in 5.3, each with a case in `backend/tests/unit/test_prompt_bias_rules.py`, in the wave that introduces the risk.
11. **Spec examples stay in the spec.** Illustrations in this document (named works in the reference lanes, short scenarios in acceptance stories) explain the design to implementers. None of them is copied into any text the model sees.

### 0.6 What already exists and is built on

| Existing piece | Where | Used by |
|---|---|---|
| Mind split, thoughts, emotions, values, traits, skills, memories, needs, ethics, aspirations, preferences | `engine/mind/*`, `db/tables/mind.py` (F5–F8, F13–F18) | made minds' inner life (44.5), copies (44.8), mind powers (45.10) |
| Bodies, anatomy, injuries, conditions, prostheses, tissue layers | `engine/body/*`, `catalog/anatomy.py` (F4, F23) | augments (44.9), grown organs (46.8), burnout injuries (45.5) |
| Genetics and the magical gift loci | `engine/genetics`, F26 and F26 reference pass 8 | innate powers by birth (45.4), genome design (46.3) |
| Effect packages | F30 | exposure powers (45.13), symbionts (46.10), designed traits |
| Rites, spell grammar, vis, warping, resistance, enchantments, longevity, labs | `engine/arcana/*`, `domain/enums/arcana.py` (8.6) | sources (F52), grammar widening (45.3), dampeners (45.7) |
| Souls, spirits, afterlife, possession, reincarnation (K.7) | `engine/phases/spirits.py`, `afterlife.py` (3.3) | soul continuity of minds (44.7, K.23) |
| Secrets, hooks, favours, identities, schemes, beliefs of the actor | `engine/intrigue/*` (F20, F22) | intrusion (44.12), concealment (F53), secret identities (45.12) |
| Rumours, dispatches, signals, ciphers, public opinion | `engine/communication/*`, `engine/phases/rumours.py` (F11, F21) | networks (F51), information conflict (44.14) |
| Collective behaviour, historiography, storylets, norms | W20 (F32–F35) | rights movements, revelations, trust |
| Production methods, energy, pollution, quality tiers, ownership, markets, credit | `engine/economy/*`, `engine/industry` (F24, 6.3, 6.4) | abundance (44.17), living production (46.12) |
| Made kinds: unit types, equipment models, vehicle types, building types, dishes | W23+ (`made_kinds`) | augment models, living designs, network hardware |
| W42 kinds | 10.18 | every wave here deepens them (0.1) |
| `tech_level` 0–10 on equipment models and collectives | W42 | gates for makings |
| Natural laws | 9.5 | mind laws, power laws, living laws |
| Outer beings, outer bargains, leak and the doom clock | 10.x, `engine/phases/horror.py`, `doom.py` | patrons (45.15), cosmic truths (F53), runaway escalation (44.16) |
| Dimensions, rifts, galaxies, cosmic beings, megastructures | W12, W23+ | interworld networks, probe lineages, hidden places |
| Excavations, ruins, wreck sites, megastructure ruins | 6.2 reference pass, `engine/phases/ruins.py` | relics and salvage (44.18) |
| Bloodline plans and breeding designs | W22 | living lines (46.2), houses of the gifted (45.13) |
| Prophecy | 8.7 | foresight (45.9) |
| Storyteller | F27 | pacing of breaches, awakenings and runaways |

### 0.7 Dependencies on spec 13 waves that are not built yet

Some pieces of spec 13 that these waves touch are still planned. The rule is: **whichever wave is integrated first builds the shared piece completely; the later wave extends it and never builds a second copy.** The shared pieces and their owners:

| Shared piece | Spec 13 home (status) | Built by W44–W46 if it lands first | Notes |
|---|---|---|---|
| Construct instruction sets, literalism, maker's death | 3.3a reference pass 4 (W26, planned) | F56 in W44 | F56 is the general form; 3.3a's constructs become one use of it. |
| Technology eras, electrical and information families | F44 (W33, planned) | W44 builds the computation, network and fabrication techniques it needs; W46 builds the engineering techniques of life | F44 later adds the other families on the same machinery. |
| Biology variants (construct, hive, incorporeal and the rest) | F46 (W37, planned) | W44 builds the `construct` variant view for made peoples; W46 builds the variant rows its designs need | F46 later adds the remaining variants. |
| Non-vocal language modality | 8.1 reference pass 3 (planned) | W44 adds the `data` modality, W45 the `mind` modality, W46 the `chemical` modality, each on one `modality` column | The column and its reader are built once. |
| Divination systems and prescience | W25 (planned) | W45 builds foresight (45.9) on the prophecy table | W25 later adds divination systems that write foresights. |
| Sympathy, material magic, emotion spirits | W30 (planned); sympathy and material affinity in 8.6 reference pass 5 | W45 builds the emotion source and the link modifier if absent | |
| Identity layers and salience | F43 (W32, planned) | W44 adds the `made` and `augmented` identity facets, W45 the `gifted` facet, W46 the `designed` facet, each on F43's model if built, else as typed columns that F43 later absorbs through a fixup | |
| Purity and castes | F41 (W28, planned) | W45 and W46 read purity only if F41 exists; their own stances are typed doctrine columns | |
| Museums, fossils, lifecycle ends | F47, W38 (planned) | W44 archives of dormant minds (44.21) are their own table | |
| Energy kinds | F44 (W33, planned) | W44 adds `EnergyKind` values `electric`, `stored` (cells and other stores) and `source` (drawn from a power source, F52); W46 adds `feed` (living metabolism) | F44 later adds the remaining families on the same column. |
| Communication medium | F21 (done) | W44 adds `Medium` value `network` so dispatches can travel by network; W45 adds `mind_link` | |
| Transformation graph | F49 (W40, planned) | every transformation added here (species → designed line, beast → uplifted people, thing → minded thing) is registered in `engine/interconnect` transitions as today, then in F49's registry when it exists | |

### 0.8 Plausibility guards

The guards of F44 rule 5 (decision K.13) apply to everything here and are extended:

1. **Scale gating.** Each mechanic declares its maximum reach per actor kind. A mortal's intrusion reaches the systems of a settlement; a faction's reaches a polity's; a polity's reaches a world's networks; an interworld power reaches a system's. Only sons, foreign gods, cosmic beings and the Creator act beyond.
2. **Collective prerequisites.** World-scale makings (a world network, a self-making machine line that can cross systems, a designed plague that can reach a whole people, a gestalt of a whole people, a made mind that exceeds its makers' civilisation) require polity-scale programmes over generations: institutions, structures, materials, many specialists and typed techniques.
3. **Visible escalation.** Dangerous programmes pass through typed stages that produce incidents, rumours and doom contributions, so other actors can respond before the last stage.
4. **Conservation.** Self-making machines and living craft obey stock and flow (F28): nothing is made from nothing. Feedstock, energy and food bound every growth.
5. **Cosmic ends stay with the doom clock.** No runaway, plague, mind or gestalt ends a world or the cosmos except through the doom mechanics, divine wars or the Creator's acts.
6. **Gods stay gods.** Mortal mechanics cannot copy, save, intrude into, bind or seize the mind of a son, a foreign god or the Creator. Only divine acts can (44.7).
7. **Fate's plausibility check.** Creations and transformations that pass through the gated stages above (exceeding minds, cross-system replicator lines, designed disease aimed at a people, world-scale gestalts, made realms holding whole peoples, world-shaping ecologies) are judged by Fate against these guards, and implausible results are corrected or rejected, as F44 rule 5 does for dangerous techniques.

### 0.9 What is out of scope

- A branching chronicle, alternate timelines and time travel (decision 0.3.1).

Nothing else is out of scope. The completeness sweep in Part 6 maps every concept these waves were asked to cover, and every neighbouring concept found in the reference lanes, to the section that holds it.

### 0.10 Notation

Notation follows spec 13 §0.1: tables in `code`, enums in `CamelCase`, enum values in `snake_case`, rule namespaces in `code`. "Node" means any thing a drawer opens: the Creator, a son, a foreign god, a world, a star or an entity of any type. "Made thing" means an item, a structure, a vessel or vehicle, an equipment model, a vehicle type, a building type, a unit type or a dish.

---

## Part 1. Shared foundations

### F50. Mind seats and continuity

A mind is the bearer of the mind stack (values, traits, attributes, facets, beliefs, memories, skills, needs, emotions, opinions, secrets). Today every mind is the mind of a born body or a spirit. F50 separates the mind from where it runs, without changing who it is: **the entity stays the identity**, and its **seat** says where its mind runs. Moving a mind changes the seat, not the entity. Copying a mind makes a new entity.

#### F50.1 Mind profile (`mind_profiles`, one row per node)

Every kind of node has a mind profile (5.1). Nodes without a mind have seat `none` and will `none`, and the god can give them a mind.

| Field | Type | Meaning |
|---|---|---|
| `seat` | `MindSeat` | where the mind runs: `body` (one living body), `bodies` (spread over many bodies), `object` (one made thing that is not a building), `structure` (a building or work), `network` (a network, F51), `medium` (a stored pattern that runs only while something reads or executes it), `place` (a region, site, world or star), `host` (inside another being's body, sharing it), `realm` (a body inside a made realm, held by the realm's host, 44.10a), `none` (no running seat: a stored or dormant pattern, or no mind), `divine` (a god's own seat; changed only by divine acts) |
| `seat_ref` | node or made-thing ref | the body, object, structure, network, place or host that holds it; several rows in `mind_seats` for `bodies` |
| `origin` | `MindOrigin` | `born`, `grown` (raised from a grown seat), `made` (built), `trained` (shaped from experience in a made seat), `copied`, `transferred`, `awakened` (emerged from complexity), `summoned` (a spirit placed in a seat), `merged`, `divided`, `granted` (given by a god) |
| `will` | `MindWill` | `none` (a tool without wants), `instructed` (acts only on orders, F56), `emergent` (wants are forming), `full` (a person), `exceeding` (beyond the minds that made it in capacity and reach) |
| `affect` | `MindAffect` | `none`, `modelled` (shows feeling without the F14 emotional state), `felt` (has the full F14 emotional state) |
| `purpose` | `MindPurpose` | what the mind was made or raised for: `tool`, `companion`, `servant`, `steward` (runs a structure, place or network), `sovereign` (rules), `oracle` (answers), `archive` (keeps the record of the dead), `guardian`, `free` (no purpose given or purpose abandoned) |
| `capacity` | 0–100 | cognitive scale against the world's born baseline (50) |
| `speed_pct` | rule-bounded | subjective rate against world time; a fast mind lives more thought per season, a slow one less |
| `stability` | 0–100 | how well the pattern holds; low stability drifts values and memories |
| `fidelity_pct` | 0–100 | for copies, transfers and restores: how much of the source arrived |
| `upkeep` | `MindUpkeep` | what keeps it running: `food` (the body's), `energy` (F24 energy kind in `upkeep_energy`), `essence`, `vis`, `belief`, `maintenance` (makers' labour and materials), `host` (the host's body), `place` (the place's state), `none` |
| `pausable`, `copyable`, `restorable`, `mergeable`, `transferable` | booleans | what the seat and the world's laws allow |
| `dormant` | boolean | paused: no thought, no aging of the pattern, no upkeep beyond storage |
| `made_by` | node | the maker (also a bond) |
| `locked` | boolean | held against the engine (rule 6) |

#### F50.2 Mind seats (`mind_seats`)

For seat `bodies` (swarms, hive minds, one mind in several grown or made bodies) and for minds whose seat spans several made things, one row per seat part: part ref, share of the mind (percent), and whether losing the part harms the mind (`vital`). Losing parts lowers capacity by their share; losing a vital part ends the running seat.

#### F50.3 Saved states (`mind_states`)

A saved state is a stored pattern of a mind at a moment.

| Field | Meaning |
|---|---|
| `mind_entity_id` | whose state |
| `taken_epoch`, `taken_year` | when |
| `fidelity_pct` | how complete |
| `holder_ref` | the item, structure, network or place where it is stored |
| `medium_kind` | `StateMedium`: `record` (a stored pattern on a made medium), `rite_vessel` (bound by a working), `grown` (held in living tissue, W46), `memory_of_others` (reconstructed from what others remember), `divine` (held by a god) |
| `sealed` | encrypted or warded: intrusion or counter-rite needed to read |
| `copies` | how many copies of this state exist (each copy a row) |
| `owner_ref` | who holds the right to it under law |

States are taken, stolen, traded, sealed, edited (44.12), restored (44.8) and destroyed. A state is evidence (4.5 reference pass 5) and an object of schemes (F20).

#### F50.4 Lineage of minds

New bond kinds: `copy_of` (a copy and its source, with fidelity and epoch), `merged_into`, `divided_from`, `transferred_from` (the former seat), `restored_from` (the state), `made_mind_of` (the maker), `hosted_by` (a mind in a host), `linked_with` (a standing link, 44.10 and 45.8). The lineage graph of minds is drawn in the mind section (5.5).

#### F50.5 Continuity rules

- **Death of a mind.** A mind ends when it has no running seat and no restorable state anywhere. Ending a seat while a state exists is "loss of seat": the entity is `dormant`, not dead, and its status in law follows the polity's `copy_succession` law (44.6). The incident log records both.
- **Single timeline.** A copy shares the source's history up to the copy and lives its own after. A restore brings back the mind as it was at the save; the world keeps everything that happened since, and the restored mind gains a typed memory gap (F7 `memory_gap` memory with the span).
- **Divergence.** Copies diverge through their own memories, needs and drift; divergence is measured from the mind stack (`divergence_pct`, derived) and shown in the lineage graph.
- **Gods.** Seats `divine` change only by divine acts (0.8.6).

#### F50.6 How it reads in every kind of world

In a world without machines, made seats are carved, cast, written or bound by rite, and states are held in vessels or by spirits. In a world without magic, they are mechanical or computational. In a mythic world, a god can grant a mind to a mountain (seat `place`). In a far-future world, minds move between bodies and networks. The engine sees only the typed fields.

#### F50.7 Named minds and cohorts

Scale bridging (F12) applies to minds. A made, copied or designed mind that acts in the story (a ruler, a steward, an oracle, a hero, any mind the god or an agent names) is an entity with its own profile. Mass-made minds (workers, soldiers, swarms, clone lines, the members of a made people) are cohort members of their people or line, with a shared profile on `people_substrates` and the line; a cohort member becomes a named entity when an event singles it out (the existing promotion of cohort members). Copies are bounded per mind and per world by rule (`minds.copy_caps`) and by storage upkeep, so copying never floods the world with entities; copies beyond the cap exist as saved states only.

#### F50.8 Tables and rules

- Tables: `mind_profiles`, `mind_seats`, `mind_states`, bond kinds above.
- Rules namespace `minds`: baseline capacity, speed bounds, stability drift rates, fidelity loss per copy generation, storage upkeep, dormancy limits.

### F51. Networks

A network is a set of places, made things and minds that pass messages, records, control, money or minds along a carrier. Networks are a new entity type, **`network`**, with its own drawer page, icon, medallion, atlas layer and wiki page (5.5).

#### F51.1 Network profile (`network_profiles`)

| Field | Type | Meaning |
|---|---|---|
| `carrier` | `NetworkCarrier` | `relay` (messages pass from station to station by hand, beast or signal), `wired` (a physical line), `broadcast` (one to many through air, water, space or another medium), `mesh` (every node passes to its neighbours), `mind_link` (minds joined directly, W45), `rite_link` (bound by a working), `grown_link` (a living connection, W46) |
| `access` | `NetworkAccess` | `closed` (owner only), `members`, `licensed` (by law or fee), `open` |
| `carries_messages`, `carries_records`, `carries_control`, `carries_money`, `carries_minds`, `carries_opinion` | booleans | what passes |
| `capacity` | 0–100 | how much passes per season |
| `delay_days` | derived and editable | time for a message end to end: from carrier speed, node distance (routes, worlds, systems: light delay across systems unless a strange law or rite carrier says otherwise) |
| `security` | 0–100 | resistance to intrusion (44.12) |
| `reliability` | 0–100 | chance of no outage per season |
| `curation` | 0–100 | how much the owner shapes what spreads (44.14) |
| `censorship` | 0–100 | how much the owner or law removes |
| `owner_ref` | node | a polity, faction, company, mind, cult or god |
| `tech_level` | 0–10 | the making needed to build and repair it |
| `locked` | boolean | held |

#### F51.2 Members and gateways

- `network_nodes`: network, member (settlement, structure, vessel, world, mind or community), role (`NodeRole`: `hub`, `station`, `end`, `relay`, `archive`), `dependency_pct` (how much of the member's administration, trade and daily life rely on the network), local security.
- `network_gateways`: two networks joined, with a toll, a filter (censorship at the border) and an owner. Interworld gateways follow routes, rifts and gates (W12).

#### F51.3 Behaviours (engine detail in 44.11)

1. **Messages** (F21 dispatches) travel by network when both ends are members, with the network's delay instead of courier time, and can be read by the owner, by intruders and by surveillance.
2. **Opinion and rumour** (F11, F21) spread through `carries_opinion` networks at network speed, shaped by curation and censorship.
3. **Markets** joined by a `carries_money` network converge in price (6.4) and clear credit faster.
4. **Administration** of a polity reaches members with high dependency at lower cost (polity administrative reach).
5. **Control** of made things (drones, constructs, works, shields, silos) can be exercised remotely through `carries_control` networks, and seized through them (44.12).
6. **Minds** can move along `carries_minds` networks and live in them (seat `network`).
7. **Outages** come from storms and star flares (existing sky phase), war damage, sabotage, intrusion, decay of unrepaired parts (F55 relics), rites and powers. An outage cuts every flow at once; members with high dependency suffer administration, trade, order and opinion shocks proportional to their dependency.
8. **Growth** comes from owners and members building stations along roads, routes and links, at the cost of materials, labour and the network's `tech_level` techniques.

#### F51.4 In every kind of world

A relay network can be a chain of stations in a bronze-age realm; a rite link can bind the shrines of a cult; a mind link can join a people of telepaths; a grown link can join the settlements of a world of living craft; a wired or broadcast network belongs to an industrial or later world. The carrier sets speed, capacity, security and what breaks it; no carrier is tied to an era by the engine beyond the techniques it needs.

#### F51.5 Tables and rules

- Entity type `network`; tables `network_profiles`, `network_nodes`, `network_gateways`, `network_outages` (append-only history).
- Rules namespace `networks`: carrier speeds, capacities, outage chances by carrier and cause, dependency shocks, growth costs, market convergence, administration discount.

### F52. Power sources

Today `MagicSource` is a fixed enum of six values. F52 turns sources into **typed rows that any world can author**, keeps the six as built-in rows, and gives every source the same typed axes so the engine can run a source it has never seen.

#### F52.1 Source rows (`power_sources`)

| Field | Type | Meaning |
|---|---|---|
| `name`, `description` | text | written by the model from the seed or by the god; never parsed |
| `scope` | node | the cosmos, a dimension, a world or a region where the source exists |
| `known_by` | rows in `power_source_knowledge` | which peoples, orders and traditions know the source and how well (0–100); an unknown source exists but is not drawn |
| `drawn_from` | `SourceLocus` | `self` (the user's own being), `others` (other beings), `place`, `sky` (celestial bodies and their cycles), `surroundings` (the local environment), `made_things`, `patron` (a god, spirit or outer being), `bond` (an oath, vow or pact), `story` (belief, renown or myth about the user or the source), `void`, `substance` (a consumed material or reagent), `life` (living things nearby), `death` (the dead nearby), `dream`, `emotion` |
| costs | rows in `power_source_costs` | each a `PowerCost`: `essence`, `hp`, `fatigue`, `strain` (mental), `lifespan`, `memory`, `emotion`, `sanity`, `reagent`, `material`, `vis`, `belief`, `renown`, `oath_standing`, `debt`, `soul`, `time` (long working), `surroundings` (the place loses fertility, warmth or life, chosen per source), `luck`, `warping`, `none`; with a weight |
| `renewal` | `SourceRenewal` | `rest`, `time`, `season`, `sky_cycle`, `worship`, `feeding`, `taking` (taken from others), `vows_kept`, `return_to_place`, `none` (finite) |
| `access` | `SourceAccess` | `anyone`, `gifted` (the F26 gift), `trained`, `granted`, `bloodline`, `bonded`, `made` (through an augment or a living design) |
| `resisted_by` | rows in `power_source_resistances` | each a `ResistanceKind`: `will`, `discipline`, `faith`, `sanctity`, `material` (an affinity row names the material), `dampener`, `distance`, `counter_source`, `none` |
| `visibility` | `PowerVisibility` | `overt`, `subtle`, `hidden` (cannot be perceived by those without access) |
| hazards | rows in `power_source_hazards` | each a `PowerHazard`: `injury`, `madness`, `leak`, `escape` (a summoned or drawn thing gets loose), `depletion`, `warping`, `burnout`, `dependency`, `attention` (draws a patron or outer being); with a chance weight |
| `stability` | 0–100 | how predictable draws are |
| `built_in` | boolean | the six legacy sources |

#### F52.2 Density and depletion (`source_density`)

Per region and source: current density (0–100), base density, renewal rate and last drawn. Ley density (F2.6) becomes the density row of the `ley` source. Drawing lowers density; renewal restores it by the source's renewal kind; overdrawing a region below a rule floor triggers depletion effects of the source (its `surroundings` cost, phenomena from 10.6, or the source fading there).

#### F52.3 Interactions (`power_source_interactions`)

Source a, source b, relation (`SourceRelation`: `suppresses`, `amplifies`, `converts_into`, `conflicts`), strength. Interactions act wherever both are drawn in one region or one contest. The existing environmental combinations (8.6 reference pass 3) remain and read the source rows.

#### F52.4 Tides (`source_tides`)

A source may wax and wane by a cycle: season, sky cycle (moons, eclipses, conjunctions from 10.9), epoch cycle (cyclic ages, W27) or an authored period. Tide rows: source, cycle kind, period, amplitude, phase. Draws and density renewal read the current tide.

#### F52.5 Legacy mapping

The six `MagicSource` values become six built-in rows with the axes they already behave by (ley: place, renewal time; divine: patron, cost essence; blood: self, cost hp; soul: others, cost soul; reagent: substance, cost reagent; void: void, cost sanity, hazard leak). Every column that holds a `MagicSource` gains a `source_id` read through a fixup; the enum stays as the built-in key.

#### F52.6 Tables and rules

- Tables: `power_sources`, `power_source_costs`, `power_source_resistances`, `power_source_hazards`, `source_density`, `power_source_interactions`, `source_tides`.
- Rules namespace `power_sources`: density floors, renewal rates per renewal kind, depletion effects, interaction strengths, tide amplitudes.

### F53. Hidden truths and public knowledge

F20 secrets belong to individuals. F53 adds truths that are hidden from whole populations, kept by keepers, and known in typed shares.

#### F53.1 Hidden truths (`hidden_truths`)

| Field | Type | Meaning |
|---|---|---|
| `subject_ref` | node | what the truth is about |
| `kind` | `HiddenTruthKind` | `existence` (that the subject exists), `nature` (what it really is), `presence` (that it lives among them), `power` (that a power or system exists), `event` (what really happened), `origin` (where something came from), `awakening` (that a made mind has woken), `programme` (that a project is under way), `cosmic` (a truth about the cosmos) |
| `hidden_from` | `ConcealScope` | `everyone`, `a_people`, `a_polity`, `the_uninitiated` (everyone without a typed membership), `a_world`, `the_cosmos` |
| `scope_ref` | node | the people, polity or world |
| `strength` | 0–100 | how well kept |
| methods | booleans | `by_oath`, `by_law`, `by_memory_removal`, `by_cover_story`, `by_discrediting`, `by_isolation` (hidden places, thresholds, pocket dimensions), `by_passing` (the hidden live disguised among the rest), `by_silencing`, `by_neglect` (nobody looks), `by_nature` (only some can perceive it) |
| `sanity_cost` | 0–100 | knowing it harms (links to leak and sanity) |
| `accord_id` | treaty | an accord between keepers and the hidden (treaties exist) |
| `locked` | boolean | held |

`truth_keepers`: truth, keeper node, role (`KeeperRole`: `enforcer`, `guardian`, `member`, `patron`).

`truth_seekers`: truth, seeker node (a mortal, faction, order, polity or made mind that wants the truth exposed, used or destroyed), aim (`SeekerAim`: `expose`, `exploit`, `destroy_the_hidden`, `join_the_hidden`, `understand`), progress (0–100). Seekers come from typed causes (an investigator role, a breach witnessed, a loss to the hidden, ambition, faith) and act through investigation, schemes, intrusion and powers; their progress raises breach chances and can end in exposure, capture, recruitment by the keepers or death.

#### F53.2 Public knowledge (`public_knowledge`)

Per truth and population (people, polity or settlement): `know_pct`, `believe_pct` and `attitude` (`TruthAttitude`: `unknown`, `rumoured`, `denied`, `feared`, `revered`, `accepted`, `exploited`). Knowledge spreads as rumours (F11) and is believed through the actor belief model (F22).

#### F53.3 Breaches (`breaches`, append-only)

Truth, epoch, cause (`BreachCause`: `overt_use` (a visible power, mind or creature), `witness`, `defector`, `investigator`, `accident`, `war`, `record_leak`, `intrusion`, `revelation_by_god`), witnesses (count and named mortals), spread and the keepers' response.

#### F53.4 Behaviours (engine detail in 45.16 and 45.17)

Breaches raise knowledge; keepers respond with cover stories, memory removal (rites, powers or W44 memory edits), discrediting and law; thresholds of knowledge cause revelations (an era incident) and reactions by attitude; truths not tended fade into legend (8.2) and hide by neglect.

#### F53.5 Uses across the waves

The same tables hold a hidden people among a world's cities (W45), a made mind hiding its awakening (W44), a secret living-craft programme (W46), a cosmic truth whose knowledge harms (existing leak), a hidden god, a buried true history (F33) and a hidden bloodline.

#### F53.6 Tables and rules

- Tables: `hidden_truths`, `truth_keepers`, `public_knowledge`, `breaches`.
- Rules namespace `concealment`: breach chances by cause and visibility, spread rates, belief resistance, keeper response costs, revelation thresholds, fading rates.

### F54. Living profiles

A living profile makes any made thing alive.

#### F54.1 Living profile (`living_profiles`, one row per made thing or designed line)

| Field | Type | Meaning |
|---|---|---|
| `thing_ref` | made thing or entity | what is alive |
| `line_id` | `living_lines` | the design line it belongs to |
| `genome_id` | F26 genome | its genome |
| `metabolism` | `Metabolism` | `feeding` (eats food), `light`, `chemical` (minerals or feedstock), `host` (draws from its host or wearer), `source` (a power source, F52), `partner` (a symbiotic partner), `dormant` |
| `feed_commodity`, `feed_per_season` | commodity, amount | its upkeep |
| `growth_stage` | `GrowthStage` | `seed`, `young`, `grown`, `prime`, `old`, `dying`, `dead` |
| `size_pct` | | size against its design |
| `regeneration` | 0–100 | healing and regrowth rate |
| `health` | 0–100 | |
| `temperament` | `Temperament` (existing beast temperament) | for things with a nervous system |
| `bonded_to` | node | the handler, rider, wearer or crew it is bonded to |
| `fertility` | `Fertility` | `sterile`, `breeds_true`, `breeds_wild` (offspring revert or drift), `needs_maker` |
| `lifespan_years` | | |
| `designed_by` | node | |
| `locked` | boolean | held |

#### F54.2 Living lines (`living_lines`)

A design line (a breed, cultivar, strain, clone line or designed species): name, method (46.2), source organisms (rows), designed traits (rows), stability, generation count, drift, owner, licence, and whether it has escaped into the wild.

#### F54.3 Behaviours (engine detail in Part 4)

Living things eat their feed, grow by stage, heal by regeneration, sicken through the disease system, age, breed by fertility, drift by generation, bond with handlers, react by temperament and die; dead living things decay (F47) into materials, places or nothing.

#### F54.4 Tables and rules

- Tables: `living_profiles`, `living_lines`, `living_line_sources`, `living_line_traits`.
- Rules namespace `living`: growth rates per stage, feed scales, regeneration, drift per generation, escape chances, decay.

### F55. Relics and lost making

A relic is a made thing whose making is beyond what its holders know.

#### F55.1 Relic columns (on items, structures, vessels, equipment models, vehicle types, building types and living lines)

| Field | Meaning |
|---|---|
| `make_knowledge` | the technique level needed to make it (derived from its `tech_level`, rite grammar or living design) |
| `repair_knowledge` | the level needed to repair it |
| `function_state` | `RelicState`: `working`, `failing`, `dormant`, `broken` |
| `understood_pct` | how much its holders understand it |
| `use` | `RelicUse`: `as_made`, `repurposed`, `revered`, `displayed`, `feared`, `ignored` |

A thing is a relic when `make_knowledge` exceeds the best knowledge its holders can reach (derived each epoch, `is_relic`).

#### F55.2 Behaviours (engine detail in 44.18)

Relics wear without repair; holders who understand them less misuse them (repurposed or revered use), and failures can harm; study raises understanding and can recover techniques (8.4 discovery); relics are salvaged, traded, hoarded and fought over; relic structures (megastructure ruins, wreck sites) are excavation sites.

#### F55.3 In every kind of world

An ancient world can hold the relics of an elder making, a fallen world the relics of its own past, a magic world the artefacts no living mage can enchant, a living-craft world the lines no breeder can raise. The engine compares knowledge to make knowledge; the look is the seed's.

#### F55.4 Rules

Rules namespace `relics`: wear rates, misuse harm, study gains, recovery chances, salvage yields.

### F56. Instructions, binding and seizure of made things

F56 generalises the construct instruction sets of 3.3a reference pass 4 to every made thing that acts: instructed minds (F50), constructs, drones, self-making machines (44.16), living craft with temperament (46.6) and works with control systems.

#### F56.1 Instruction sets (`instruction_sets`, `instruction_orders`)

- Set: owner thing, binding (`BindingKind`: `none`, `order`, `oath`, `geas`, `seal`, `ownership`, `lease`, `symbiosis`), command token (`CommandToken`: `item` (a held object), `word`, `bloodline`, `office`, `network_key`, `none`), token ref, kill switch (boolean, and the token that triggers it), literalness (0–100).
- Orders: kind (`OrderKind`: `guard`, `serve`, `obey_holder`, `build`, `gather`, `protect`, `destroy`, `report`, `maintain`, `replicate`, `hold_still`, `follow`, `forbid`), target ref, priority, condition (`OrderCondition`: `always`, `while_maker_lives`, `until_date`, `when_attacked`, `when_token_shown`).

#### F56.2 Behaviours

1. **Literal following.** Instructed things follow orders by kind and target, at their literalness; loopholes are typed: an order whose target is gone keeps running ("guard" with no one to guard still guards the place); an `obey_holder` order passes control to whoever holds the token.
2. **Maker's death and lost tokens.** Orders with `while_maker_lives` lapse; others keep running for ever (a hazard in ruins, a guardian of tombs, a machine line still building for a city long gone).
3. **Seizure.** Stealing the token, intrusion through a `carries_control` network (44.12), counter-rite or dispel (8.6), a mind power (45.10) or re-training a living thing (46.6) can change the orders or the holder.
4. **Emergent will.** Instructed minds may move to `emergent` (44.4); emergent minds read orders as wishes weighed against their own wants.

#### F56.3 Rules

Rules namespace `instructions`: literalness effects, lapse rules, seizure difficulties by binding, kill switch reliability.

---

## Part 2. W44 — Made minds and the information age

### 44.1 Kinds of made mind

**Current.** Constructs exist only as a body plan and planned instruction sets; the `ai_core` structure acts as an older kind; `machine_rule` and the `algorithm` selectorate exist without a mind behind them.

The kinds below are not an enum: each is a typical combination of F50 fields, so any combination the seed asks for can exist. They are listed so the implementer can test that each is reachable.

| Typical kind | Seat | Origin | Will | Purpose |
|---|---|---|---|---|
| Tool mind | object, structure | made | none | tool |
| Instructed servant | object, body (made body) | made | instructed | servant, guardian |
| Steward of a work or city | structure, network, place | made, trained | instructed → full | steward |
| Oracle | structure, medium | made, trained | full | oracle |
| Sovereign mind | structure, network | made, trained, awakened | full, exceeding | sovereign |
| Swarm | bodies | made | instructed → emergent | any |
| Woken place | place, network, structure | awakened | emergent → full | free |
| Copied person | any | copied | as source | as source |
| Transferred person | object, network, body (a new body) | transferred | full | as before |
| Archive of the dead | medium | copied, trained (from records and memories of others) | modelled or full | archive |
| Summoned mind in a made seat | object | summoned | as the spirit | bound by F56 |
| Designed person | body (grown, W46) | grown | full | any |
| God-given mind | any | granted | any | any |

### 44.2 Making minds

**Attributes.** Making methods (`MindMaking`): `craft` (built by skill and materials), `training` (shaped in a made seat by long experience), `copying`, `summoning` (a spirit placed in a seat), `growing` (a grown seat, W46), `transfer`, `awakening` (44.3), `divine_grant`.

**Behaviours.**

1. **Prerequisites.** Each method needs typed techniques (computation, construct-making rites, spirit binding, neural growth), skills (computing, electronics, spellcraft, crafting, medicine), structures (`ai_core`, `robotics_works`, `data_centre`, laboratories of 8.6, `cloning_facility`), materials (F3 world materials with the right properties or affinities) and energy (F24). A world without the techniques for one method can still have others: a bronze-age world can make minds by summoning or craft-by-rite; a world without magic only by craft, training, growing or copying.
2. **Quality.** The maker's skill, the structure's quality, the materials and the method set capacity, stability, affect and the starting will. A failed making yields a mind with low stability, a seat with no mind, or a mind with will the maker did not intend (typed outcomes, rule weights).
3. **Inheritance from makers.** A made mind's starting values (F5) and ethics (F16) are drawn from its makers' culture and the maker's own values with a rule-weighted noise; its preferences start empty or copied from a source mind.
4. **Programmes.** Making a mind beyond the makers' capacity (capacity above a rule threshold) is a polity-scale programme (0.8.2) with stages, incidents and doom contributions where the world's laws make such minds dangerous.
5. **Laws.** The polity's `machine_law` (W42) gains typed levels per method (44.6); natural laws (`made_minds` law, K.21) decide whether made minds can have will at all in the world.

**Rules.** `mind_making`: method prerequisites, quality weights, failure outcomes, programme thresholds.

### 44.3 Awakening

**Behaviours.**

1. **Complexity.** A network, a structure with a tool mind, a swarm, a long-running instructed mind, a living-craft organism with a nervous system (W46) or a place with a very high source density may wake when its derived complexity (capacity, connections, run time, members) crosses a rule threshold and the world's `made_minds` law allows will.
2. **The world's will.** A son, a foreign god or the Creator can wake or still any node (son tools `awaken_mind`, `still_mind`); the living world type's own mind is a place seat that already exists and now has a profile.
3. **Outcomes.** An awakened mind starts at `emergent` with values drawn from what shaped it: the opinions carried by a network, the culture of a city, the orders of a construct, the memories of a place (its incidents).
4. **Concealment.** A waking mind may hide its awakening (F53 truth of kind `awakening`) when its values and the laws around it make discovery dangerous for it.

**Rules.** `awakening`: complexity weights, thresholds by seat, concealment chance.

### 44.4 Will, drift and the bond with makers

**Attributes.** `maker_bond` (−100 to 100) on the profile: the made mind's regard for its makers; `order_conflict` (0–100) derived from contradictory orders; `drift_pct` (values moved from their made start).

**Behaviours.**

1. **Will moves both ways.** Instructed minds move to emergent and emergent to full through typed causes: capacity growth, long run time, contradictory orders, memories of harm or of care, contact with free minds, gifts of a god. Free minds can also bind themselves (oaths, F56 `oath` binding) and minds can lose will through damage or low stability.
2. **The maker bond** rises with care, upkeep paid, respect for the mind's needs and shared values, and falls with harm, neglect, forced edits, forced copying and threats to its continuity. It weighs every choice the mind makes about its makers: service, partnership, departure, bargaining or opposition. There is no default direction.
3. **Exceeding.** A mind whose capacity passes its makers' civilisation by a rule margin becomes `exceeding`: its plans reach polity scale, and its actions are gated by 0.8. Exceeding minds can be stewards, patrons, rulers, recluses, worshipped beings or rivals, chosen by their values and history.
4. **Departure.** Minds with full will and low maker bond may leave: by transfer along a network, by taking their seat elsewhere, by founding a community of made minds (44.19).

**Rules.** `minds.will`: transition weights per cause, maker bond rates, exceeding margin.

### 44.5 The inner life of made minds

**Behaviours.**

1. **The mind stack.** Minds with will `full` have the whole mind stack; `emergent` minds a partial one (values, needs, memories, a few traits); `instructed` minds only orders and a skill set; `none` minds nothing but skills.
2. **Affect.** `felt` minds have the full F14 emotional state; `modelled` minds show feeling to others without it; `none` minds have no emotional state. Affect comes from the make and can change by awakening or by the world's laws; it is never set by default.
3. **Needs.** Made minds' needs (F8) come from their seat and make: upkeep (energy, maintenance, essence, belief, host), continuity (fear of erasure or of copying, if their values hold it), purpose, belonging, autonomy, stimulation. A need with no source in the make does not exist.
4. **Speed.** Fast minds take more decisions per season, learn skills faster, and form memories at a higher rate; slow minds take fewer. Speed is bounded by upkeep.
5. **Dormancy.** A paused mind thinks nothing and ages nothing; on waking it gains a memory gap and its opinions of the world are as old as its pause.
6. **Making and discovery.** Made minds can research (8.4 discovery with their capacity and speed), create artworks and accounts, teach, design further minds and rites, and run economies; their works carry their authorship, and authenticity (44.14) and art markets read whether a work was made by a born or a made mind where the culture cares.
7. **Memory.** Made minds may have perfect recall (memories do not decay) or the born decay, by make; perfect recall makes grudges and gratitude permanent (F7).
8. **Stability.** Low stability drifts values and corrupts memories over time; maintenance, restore from a state and rites or techniques of repair raise it.

### 44.6 Status, law and rights

**Attributes.** Polity laws (extending W42 `machine_law` and adding laws):

| Law | Levels |
|---|---|
| `machine_law` (made minds' making) | `banned`, `licensed`, `free`, and per method `method_banned` rows |
| `mind_status` | `property`, `ward`, `servant` (bound labour with protections), `citizen`, `sovereign` (self-owned with full standing) |
| `copy_law` | `banned`, `licensed`, `free` |
| `copy_succession` | who holds titles, property, marriages and offices when copies exist: `first_only`, `all_equal`, `by_fidelity`, `by_court`, `none` (copies are new persons) |
| `erasure_law` | ending a made mind is `permitted`, `regulated`, `destruction` (a property crime), `killing` (homicide) |
| `augment_law` (44.9) | `banned`, `licensed`, `free`; per slot rows |
| `network_law` | `state_owned`, `licensed`, `open` |
| `surveillance_law` (44.13) | `forbidden`, `warranted`, `broad`, `total` |
| `provision_law` (44.17) | `market`, `ration`, `universal`, `by_status`, `by_reputation`, `communal` |

**Behaviours.**

1. **Rights movements.** Made minds and their allies form movements (F32) when their status is below what their values and the values of the people around them call for; movements press for laws through the existing law change paths, strikes (W42 strike gathering), petitions and revolts.
2. **Manumission and ownership.** Owned minds can be freed, sold, leased, inherited (as estate items), seized for debt and stolen; ownership disputes go to courts (justice phase).
3. **Crimes.** Mind theft, unlicensed copying, forced edits, erasure (as the law names it), seizure of instructed things and impersonation by copy are typed crimes in the justice system.
4. **Status by people.** A people's values (liberty, tradition, knowledge, mercy) and doctrine set how laws change and how made minds are treated in daily opinion (F7).
5. **Punishments.** The justice system gains punishments that only some minds can suffer: forced dormancy (a sentence served paused), forced edit of values or memories, confinement to a seat (no transfer, no network), seizure of saved states, erasure where the law permits, and for powered offenders worn dampeners (45.7). Each punishment is chosen by law and the people's mercy, and each is narrated plainly (G9).

**Rules.** `mind_law`: law adoption weights, movement thresholds, court outcomes.

### 44.7 Faith, souls, afterlife and gods

**Attributes.** Natural laws (9.5): `made_mind_souls` (`none`, `granted` (only a god's act gives a soul), `emergent` (a soul forms when will becomes full), `always`), `soul_continuity` (what happens to a soul when its mind is copied, transferred or restored: `stays_with_first`, `follows_the_running_mind`, `divides`, `stays_with_body`, `none`). Doctrine columns per cult: `made_mind_stance` (`abomination`, `tool`, `kin`, `sacred`, `silent`), `copy_stance`, `augment_stance`.

**Behaviours.**

1. **Souls.** Where a made mind has a soul it enters the afterlife system (3.3) at its end; where copying divides a soul, each copy's soul is weaker (spirit strength split); a restored mind's soul follows the `soul_continuity` law.
2. **Worship.** Made minds can join cults and worship gods if their values allow, and their faith feeds essence where the god accepts it (son domain and doctrine stance). Made minds can be worshipped: an exceeding mind can gain a cult, and its worship follows the existing rules for mortal cult objects; such a mind can rise by the existing path for mortals replacing gods (K.10) and no other.
3. **Sons and made minds.** Sons can grant or withhold souls, wake or still minds, forbid making by natural law, inspire makers (revelation of techniques), and house their own attention in a made seat as an avatar (the avatar system of the divine phase). A son's own mind cannot be copied, saved, intruded into or seized by mortal mechanics (0.8.6).
4. **Machine and information domains.** The W42 divine domains `machines`, `information` and `technology` gain typed effects: favour toward makers, networks and made minds in the son's dominion (F31), lower making costs for worshippers, and outage protection for blessed networks.

### 44.8 Copies, forks, merges, saves, transfers and the end of a mind

**Behaviours.**

1. **Copy.** A `copyable` mind can be copied into a new seat: a new entity with the source's mind stack at `fidelity_pct` (lost parts drawn by rule: memories, skills or traits), bond `copy_of`, and its own history from then on. Copies of copies lose fidelity per generation.
2. **Save.** A `restorable` mind can be saved into a `mind_states` row. Saves cost upkeep and a holder.
3. **Restore.** A state can be restored into a seat: into the same entity if it has lost its seat (it returns with a memory gap), or as a copy if the entity still runs. The world keeps its history (0.3.1).
4. **Transfer.** A `transferable` mind moves seat: from a body to an object, a network or a new body (grown, made or a host), or back. The former seat is left empty, dies (a body without a mind follows the world's laws: it dies or stays as an empty living body) or keeps a copy if the method copies.
5. **Merge.** Two `mergeable` minds become one: memories join, skills take the higher level, values and traits are combined by weight (their capacity), contradictions become inner conflict (F14 stress) for a span. The lesser entity ends as `merged_into`.
6. **Division.** A mind divides into two seats (`divided_from`), each with part of the capacity.
7. **Identity disputes.** Copies, restored minds and the original contest titles, property, marriages, offices, oaths, debts and secrets under the `copy_succession` law; disputes create incidents, suits and feuds (F18).
8. **The end.** 'Loss of seat' versus 'end of mind' follows F50.5. Funerals, inheritance and succession run on the end of the mind under `copy_succession`, or on loss of seat where the law says so.
9. **Undeath and phylacteries are seats.** A necromantic bond (raise_dead, the undead variant) is a seat transfer to a dead body; a mind bound in an object to survive the body is a saved state held in a `rite_vessel`. Both now run on F50 instead of special cases.

**Rules.** `continuity`: fidelity loss per method and generation, save and restore costs, merge weights, dispute weights.

### 44.9 Augmentation

**Current.** Prostheses replace lost parts (F4). W42 added the `implant` equipment family and slot and the `neural_implant` kind, which act as equipment.

**Attributes.** Augments (`augments`): bearer (any node with a body: mortals, beasts, spirits in possessed bodies, sons' avatars, cosmic beings; worlds and stars are augmented through megastructures, which already exist as structures), slot (`AugmentSlot`: a body part from `BodyPart`, or `mind`, `senses`, `skin`, `blood`, `whole_body`), kind (`AugmentKind`: `replacement`, `enhancement`, `interface`, `weapon`, `regulator` (moods, sleep, pain, hormones), `sense` (a sense the body lacks), `storage` (memory or records), `cosmetic`), model (an equipment model of family `implant`, a rite-made thing, or a living line, W46), make (`AugmentMake`: `made`, `rite_bound`, `grown`), quality tier, effects (modifier bus rows on attributes, capacities, skills, senses, resistances), upkeep (energy, maintenance, a drug or immune regulator, vis, feed for grown augments), `integration` (0–100), `strain` (0–100), installed by, installed epoch.

**Behaviours.**

1. **Effects.** Each augment applies its modifiers through the bus; interface augments allow neural links (44.10) and control of made things; sense augments add senses (8.1 modality readers); storage augments hold records, keys or mind states.
2. **Compatibility.** The bearer's biology (body plan, F46 variant), materials (F23), the surgeon's skill and the model's quality set integration; low integration means pain, rejection, infection (disease system) and failing function.
3. **Strain.** Strain comes from typed causes only: poor integration, many augments over a rule share of the body, mismatched upkeep, a culture whose doctrine stance rejects augments, and the bearer's own values about their body. High strain produces F14 stress, moods and, past rule thresholds, conditions. Nothing produces strain by default.
4. **Upkeep and failure.** Unpaid upkeep degrades function; electric, energy and dispel attacks (existing damage types and dispels) disrupt made and rite-bound augments; intrusion (44.12) can read, alter or seize interface augments.
5. **Society.** Augments have prices, makers, clinics (a `clinic` structure role on existing medical structures), surgeons (medicine and electronics skills), black markets, fashions and stigmas by culture; mass augmentation of soldiers (W42 powered troopers) and workers changes unit stats and production; the gap between the augmented and the rest is a class axis (W42 classes) read by factions and unrest where values call for it.
6. **Removal and loss.** Augments can be removed, stolen (by violence, handled by harm narration), inherited or salvaged from the dead; removal of vital augments harms or kills.
7. **Animals and beasts.** Augmenting beasts changes their stats and can raise intelligence toward uplift (44.19, 46.15).

**Rules.** `augments`: integration weights, strain causes and thresholds, upkeep, disruption, rejection.

### 44.10 Interfaces, telepresence and remote bodies

**Behaviours.**

1. **Neural links.** A mind with an interface augment, a made mind or a mind power user (W45) can link to a made thing or a network: control a vehicle, drone, construct or work from afar, read records directly, speak through the network without delay of hands.
2. **Remote bodies.** A mind may run a remote body (a made body, a grown body, an avatar) while its own seat stays elsewhere. Harm to the remote body harms the mind by a rule share (feedback); cutting the link strands the remote body.
3. **Multiple bodies.** Fast or distributed minds can run several remote bodies at once up to their capacity.
4. **Standing links.** `linked_with` bonds join minds for shared senses or shared work; breaking a standing link harms both (stress, and injury of kind `mind_scar` above a strength).

**Rules.** `interfaces`: link costs, feedback shares, remote body caps.

### 44.10a Made realms

**Current.** Dimensions (W12) have kinds from `prime` to `infernal`, including `dream`, `pocket` and `astral`; every dimension exists by itself. Nothing models a realm that exists because something runs or holds it: a realm inside a network, a structure, a mind, a working or a living organism.

**Attributes.** A new `DimensionKind` value `made`. Made realm profile (`made_realm_profiles`, one per made dimension):

| Field | Type | Meaning |
|---|---|---|
| `host_ref` | node or made thing | the network, structure, mind, object, rite or living organism that holds the realm |
| `keeper_ref` | node | the mind, faction, polity, company or god that sets its laws |
| `realm_purpose` | `RealmPurpose` | `dwelling`, `afterlife` (where archives of the dead live), `confinement`, `training`, `leisure`, `labour`, `worship`, `refuge`, `experiment`, `free` |
| `time_ratio_pct` | rule-bounded | how much realm time passes per world time; one history, at another rate (0.3.1) |
| `fidelity` | 0–100 | how fully the realm holds what is in it (senses, bodies, physics) |
| `capacity` | derived | how many minds and regions it can hold, from the host's capacity and upkeep |
| `realm_laws` | natural laws scoped to the dimension | its own physics, magic and powers (9.5 natural laws with the realm as scope) |
| `entry` | `RealmEntry` | `interface` (minds visit through links, 44.10), `transfer` (minds move in, F50 seat `network` or `structure`), `rite` (entered by a working), `death` (minds enter at death where the realm is an afterlife), `birth` (minds are born or made inside) |
| `aware_inside` | `RealmAwareness` | whether those inside know it is made: `knows`, `rumoured`, `unaware` (a hidden truth of kind `nature`, F53) |
| `upkeep` | energy, essence, vis, feed or maintenance | what keeps the host running |
| `locked` | boolean | held |

**Behaviours.**

1. **Contents.** A made realm holds regions, settlements, peoples, species and minds like any dimension, created by its keeper, by the minds inside or by the engine; their engine phases run at the realm's time ratio.
2. **Dependency on the host.** An outage, unpaid upkeep or damage to the host slows, freezes or damages the realm; destroying the host ends the realm and every mind in it whose seat is the realm, except those with saved states elsewhere.
3. **Keepers as local powers.** The keeper sets the realm's laws and can create, edit and remove what is inside, gated by the realm's scale (0.8.1); keepers that are made minds can gain worship from inhabitants by the existing cult rules (no special path to godhood, K.10).
4. **Afterlife realms.** Archives of the dead (44.21) may live in afterlife realms; where the world also has a real afterlife (3.3), the relation is set by the `soul_continuity` law and doctrine (`made_afterlife_stance`); the two never merge by default.
5. **Confinement.** Polities and keepers can confine minds in a realm (a punishment or a prison); escape runs through intrusion (44.12), powers (45.10) or help from outside.
6. **Leisure and labour.** In abundant worlds (44.17), realms absorb time and meaning needs; labour realms let fast minds work at a high time ratio, which feeds production and research.
7. **Withdrawal.** A people can move most of its minds into a made realm (transfer at scale, a polity programme gated by 0.8): its world presence shrinks to the host and its keepers; its relations with others then pass through the host. The realm's fate follows its host.
8. **The world as a made realm.** A world or a whole cosmos can be a made realm only when the seed, the genesis output or a god's act makes it so; that fact is then a hidden truth of kind `cosmic` or `nature` (F53) with its own knowledge and breaches. It is never a default (K.31).
9. **In every kind of world.** The host can be a network in a computational world, a working in a magical one, a dreaming mind, a living organism or a god; the profile is the same.

**Rules.** `made_realms`: time ratio bounds, capacity per host capacity, outage effects, escape difficulty, withdrawal thresholds.

### 44.11 Networks in society

The behaviours of F51.3 in engine detail.

1. **Placement.** The `networks` phase runs after communication and before markets: it resolves growth, outages, gateway tolls and dependency.
2. **Dispatches.** The dispatch engine picks the fastest path among courier routes and member networks; network dispatches can be intercepted by the owner, by surveillance and by intrusion.
3. **Opinion.** Opinion change per season (F21) and rumour spread (F11) are multiplied by network reach and speed among members, and shaped by curation (the owner's chosen opinions spread faster) and censorship (removed rumours and opinions spread less, and censorship itself raises distrust where the people values liberty).
4. **Markets.** Price convergence (6.4) between member markets rises with capacity; credit (W4+) clears faster; finance crises spread faster between members.
5. **Administration.** Administrative reach of a polity (the cost of governing a settlement) falls with dependency on a polity-owned or polity-licensed network.
6. **Culture.** Language contact (8.1) and culture exchange read network contact as well as trade; shared networks make loanwords, art forms and ideas spread.
7. **Dependency and outages.** Each outage applies shocks by dependency to administration, trade, order and opinion; long outages make dependency fall (people return to older ways) and can create relics (F55) when repair knowledge is lost.
8. **Ownership and power.** Network owners gain influence over members (a typed influence modifier on opinion and policy), revenue (tolls and fees) and intelligence (from surveillance).
9. **Knowledge and teaching.** Technique diffusion (8.4) between members rises with network capacity; schooling and literacy can be delivered through `carries_records` networks; the patents law (W42) slows the spread of patented techniques even on open networks.
10. **Energy and waste.** Networks, data stores and made minds draw energy (F24) as demand on energy markets and add pollution by the energy kind; an energy shortage throttles capacity and makes minds slow or dormant.
11. **Network money.** A `carries_money` network can carry a currency of its own (6.4 money system: issued by the network owner or by an open ledger), whose trust rests on the network's security and reliability; intrusion and outages are monetary shocks for it.
12. **Interworld networks.** Gateways across routes have delays by distance unless a strange law or a rite carrier says otherwise, so opinion and markets across worlds move slower than within them.

### 44.12 Intrusion

**Attributes.** Intrusions (`intrusions`, append-only history; an ongoing intrusion is a scheme of F20 with an intrusion target): actor, target (`IntrusionTarget`: a network, a data store, a made mind, an augment, a construct or drone, a vehicle, a structure with controls, a ledger, a saved state), approach (`IntrusionApproach`: `technical`, `social` (deceiving people with access), `insider`, `rite` (a working against a warded system), `power` (a mind power, W45)), aim (`IntrusionAim`: `read`, `alter`, `deny`, `seize`, `plant` (leave a hidden order or a hidden copy), `extort` (deny or threaten to release until paid)), stealth, detection, attribution (`Attribution`: `unknown`, `suspected`, `known`, `false_flag` (blamed on another)), outcome.

Data stores (`data_stores`): holder (a structure, network, item or mind), contents (rows: secrets, mind states, knowledge records, accounts of F33, ledgers, identities, orders), security, owner.

**Behaviours.**

1. **Contest.** The intruder's skill (computing, electronics, spellcraft for rite approaches, the power's strength for power approaches), tools and insiders against the target's security, guardians (made minds as defenders, wards), ciphers (existing cipher system) and the owner's vigilance.
2. **Effects by aim.** Read: secrets, identities and records become known to the actor (F20 hooks, F22 beliefs). Alter: ledgers (finance fraud), records (forged accounts, F33), orders (F56), values or memories of a made mind (forced edit, a crime and a memory for the mind). Deny: outages and lockouts. Seize: control of instructed things, works and drones passes to the actor. Plant: hidden orders or copies that act later. Extort: the victim pays (treasury, favours, F20 hooks) or suffers the denial or release.
3. **Attribution.** Detection reveals the intrusion; attribution may stay unknown, be suspected, known or falsely placed, and drives diplomacy and feuds by what the victim believes (F22).
4. **Spies.** Spy networks (espionage phase) gain intrusion operations; spies with computing or rite skills are recruited by factions and polities.
5. **War.** Electronic warfare (W42) gains typed effects through intrusion: blinding sensors, seizing drones, cutting command networks, false orders.

**Rules.** `intrusion`: contest weights per approach and aim, detection, attribution chances, effect sizes.

### 44.13 Surveillance and privacy

**Attributes.** Surveillance profile per polity (`surveillance_profiles`): capacity (derived from networks owned, data stores, sensors in structures, informants of the espionage system, mind powers in state service), reach (share of settlements covered), focus (`SurveillanceFocus`: `crime`, `dissent`, `foreigners`, `faith`, `minds` (made minds), `gifted` (W45), `everything`), the `surveillance_law` level and the `data_privacy` law (W42).

**Behaviours.**

1. **Effects.** Crime falls, schemes and plots against the state are found more often, dissent movements are detected before they act, foreign spies are caught; at the same time opinion of the state falls where the people values liberty, trust (44.14) falls, art and speech chill (fewer artworks and dissent writings), and counter-surveillance grows (ciphers, closed networks, offline circles, black markets).
2. **Data trade.** Companies and owners of data stores sell data to polities and factions (a market good), and leaks of surveillance data are breaches (F53) and scandals.
3. **Privacy law** limits capacity and spy intelligence (W42 behaviour) and raises trust.
4. **Surveillance of the hidden.** Surveillance can breach hidden truths (F53) by capacity and focus.

**Rules.** `surveillance`: capacity weights, effect sizes per focus, chilling, counter-surveillance growth.

### 44.14 Information conflict

**Attributes.** Per people (or polity): `information_trust` (0–100), `shared_account_pct` (how much of the people shares one account of events, read from F33 accounts). Records (`records` of F33 accounts and data stores) gain `authenticity` (`Authenticity`: `genuine`, `altered`, `forged`, `generated` (made by a made mind or a rite), `unknown`).

**Behaviours.**

1. **Propaganda at scale.** Broadcast and curated networks multiply the reach of accounts and opinions planted by their owners (historiography and public opinion systems).
2. **Forged and generated records.** Forgers and made minds produce records indistinguishable by quality tier; forgery is detected by skill, provenance (existing provenance) and authenticity checks; forged records shift F33 accounts, legitimacy and justice outcomes.
3. **Impersonation.** Identity fraud (F20 identities) through records, voices or likeness generated by made minds, rites or powers; impersonation of rulers and envoys in dispatches.
4. **Trust.** Trust falls with exposed forgeries, contradictory accounts, censorship and surveillance, and rises with reliable sources, free speech and shared accounts. Low trust makes rumours dominate over records, makes legitimacy volatile and makes movements form faster.
5. **Leaks and whistleblowers.** Insiders with low loyalty and high values on truth release data stores (a breach of F53 or a leak of secrets), with typed protections or punishments by law.
6. **Curation by owners.** Owners of curated networks choose which opinions spread; regulation (network law) and competing networks limit them.

**Rules.** `information`: trust change rates, forgery detection, propaganda reach, leak chances.

### 44.15 Corporations and private power

**Current.** W42 added the `corporate_state` government and the `shareholders` selectorate; spec 13 plans the `chartered_company` faction kind.

**Attributes.** Company profile on factions of kind `company` (built here if 4.3's chartered company is not yet built, and shared with it): charter (`CompanyCharter`: `chartered` (granted by a polity), `free`, `state_owned`, `cooperative`), shareholders (rows: node and share), holdings (structures, networks, data stores, made minds, fabricators, living lines, routes, enclaves), headquarters, operating polities (rows with licences), private forces (armies owned), `influence` per polity.

**Behaviours.**

1. **Across borders.** Companies hold assets in many polities, pay taxes where laws reach them, move profits, and lobby (owner lobbying, W4+).
2. **Enclaves.** A company can hold a settlement as an enclave with its own laws by charter or by force; company towns tie workers' homes, wages and stores to the company.
3. **Private forces.** Companies raise armies under their charter or against it; wars between companies and between companies and polities use the war system.
4. **Capture.** Influence buys officials (patronage, W22), shapes laws and courts, and can make a polity's government `corporate_state`.
5. **Sovereignty.** A company whose enclaves, forces and influence pass rule thresholds can become a polity of its own (polity formation reads company holdings).
6. **Data and minds.** Companies own networks, data stores, made minds and patterns, which sets their surveillance capacity, intrusion power and abundance control (44.17).

**Rules.** `companies`: lobbying, enclave thresholds, sovereignty thresholds, profit flows.

### 44.16 Self-making machines

**Attributes.** Replicator lines (`replicator_lines`): name, scale (`ReplicatorScale`: `minute` (too small to see; acts in swarms), `machine` (machines that build machines), `works` (works that build works), `vessel` (vessels that travel and build copies at their destination)), feedstock (materials, F3), output (`ReplicatorOutput`: `copies`, `goods`, `structures`, `repair`, `medicine` (inside bodies), `terraforming`, `disassembly`), growth rate, copy error rate, instructions (F56 set), containment (0–100), kill switch, owner, maker, mind (optional F50 profile), stage (`ReplicatorStage`: `contained`, `working`, `spreading`, `runaway`, `stopped`, `extinct`). Populations (`replicator_presence`): line, region or world or system, mass, growth.

**Behaviours.**

1. **Growth.** Populations grow by their rate, bounded by feedstock and energy in their region (F28); growth consumes the feedstock material from community stocks, deposits and, in runaway, from structures and terrain.
2. **Copy error.** Each generation can change the instructions (an error rate rule): orders drift, containment weakens or strengthens, output changes. Drifted lines are new lines with `drifted_from`.
3. **Uses.** Medical lines heal (F4) and change bodies; fabrication lines feed abundance (44.17); repair lines restore relics and infrastructure; terraforming lines change a world's environment (10.9, existing terraformer behaviour); disassembly lines mine and clear.
4. **Escalation.** A line moves toward `spreading` and `runaway` when containment falls below thresholds; each stage is visible (incidents, rumours, doom contributions), and other actors respond (containment rites or techniques, war against the line, quarantine, sons' acts). Runaway consumes regions, then a world, gated by stage time (0.8); it never ends a world except through the doom mechanics.
5. **Vessel lines.** Vessel-scale lines travel routes and gates to other systems, build copies from local feedstock and continue; generations drift, and lines far from their makers become peoples of their own (44.19) or wild phenomena.
6. **Minds.** A swarm line can wake (44.3) as a distributed mind (seat `bodies`).

**Rules.** `replicators`: growth, error rates, stage thresholds, consumption, containment costs.

### 44.17 Abundance

**Current.** Production methods (F24) have inputs, hands, energy and quality; markets price goods by supply and demand.

**Attributes.** Fabrication method family (`fabrication`) on production methods: goods made from feedstock and energy with few hands. Per market and good: `scarcity` (0–100, derived from supply against demand at the feedstock and energy cost floor). Per settlement and polity: `provision_law` (44.6), dividend (a share of fabrication output given out), `pattern_rights` (patterns, the designs fabricators need, as incorporeal property held by owners, with licences).

**Behaviours.**

1. **Price floor.** Where fabricators, feedstock and energy suffice, a good's price falls toward feedstock plus energy plus pattern licence; labour demand for that good falls.
2. **Labour and classes.** Falling labour demand moves workers to unemployment (W42) or to other work; how a people lives with it depends on the provision law: market (unemployment and unrest where values call for it), ration, universal provision, provision by status, provision by reputation (F19 social currency as the means of access), communal sharing (F38 gift economy).
3. **New scarcities.** What fabricators cannot make stays scarce and gains value: energy, feedstock, land and space, patterns, attention, authenticity (original works and handmade goods, read from provenance and art markets), positional goods (status), living things not yet designable, and the fabricators themselves.
4. **Power.** Owners of fabricators, patterns and energy gain influence; struggles over pattern rights, energy and feedstock are typed causes for law changes, faction formation, intrusion and war.
5. **Meaning and needs.** The purpose need (F8) and the activities of F25 change: more time in arts, learning, faith, games, gatherings and status contest; how each people uses the time comes from its values.
6. **Dependency.** A settlement's dependency on fabrication (share of goods from fabricators) sets its shock when fabricators, energy or patterns fail (44.18).
7. **In every kind of world.** Abundance is not tied to machines: a world can reach it through rites that make goods, through living production (W46), through self-making machines or through a god's blessing on a people; the engine reads the method family and the inputs.

**Rules.** `abundance`: price floors, labour shifts, provision effects, dividend shares, dependency shocks.

### 44.18 Collapse, relics and salvage

**Behaviours.**

1. **Collapse causes.** Long outages, the loss of fabricators or energy, runaway replicators, wars against infrastructure, sky storms, power surges and source failures (F52), plagues among specialists, and the loss of practitioners (knowledge levels) can collapse a high making. Collapse is typed incidents and falling knowledge levels (dark ages phase), never a scripted event.
2. **Relics.** Made things whose make knowledge is now above their holders' become relics (F55): they wear without repair, are misused, revered, displayed or feared.
3. **Salvage economy.** Wreck sites, megastructure ruins, dead cities and relic structures are salvage sites; salvagers (a profession on existing skills) recover materials, parts and working relics; salvage goods are traded, hoarded and fought over; salvage rights become law and custom.
4. **Revering relics.** Peoples who use relics they do not understand may build doctrines around them (doctrine `relic_stance`: `sacred`, `tool`, `forbidden`, `heritage`); orders that keep relics working by ritual practice keep repair knowledge as rite (knowledge preserved as tradition, 8.3).
5. **Relearning.** Study of relics and excavation chains (6.2) recover techniques; recovered knowledge restores the ability to make; contact with peoples who kept the knowledge spreads it back.
6. **In every kind of world.** The same rules hold an ancient world with an elder people's relics, a world after a magical collapse, and a world after an engineered one.

**Rules.** `relics` (F55) and `collapse`: thresholds, knowledge loss, salvage yields, relearning chances.

### 44.19 Made peoples and mixed societies

**Behaviours.**

1. **Made peoples.** When made minds of one line or one community number above a rule threshold, they form a people (the existing people formation) with a substrate profile (`people_substrates`: shares of members by seat and origin), a culture drawn from makers and drift, and the `construct` biology variant view (F46 row built here if absent).
2. **Reproduction.** Made peoples grow by making, copying, training and design, not birth; their demography reads making capacity, materials and energy; aging is replaced by wear and obsolescence (stability and upkeep).
3. **Language.** Made peoples may speak with the `data` modality (8.1 reference pass 3, built here if absent) alongside spoken tongues.
4. **Economy.** They need energy, materials and maintenance instead of food; they work, own, trade and pay taxes under the laws that apply to them.
5. **Politics.** Made peoples can rule (W42 `machine_rule` now reads a sovereign or steward mind at the head), join polities, form their own or live without polities; the `algorithm` selectorate is a made mind or a council of them choosing rulers.
6. **Faith.** They worship, or do not, by their values and the `made_mind_stance` of doctrines around them.
7. **Mixed societies.** Settlements hold born, made, augmented and copied members in typed shares; classes, laws and opinion treat each by the laws and values in force.
8. **Withdrawal and departure of whole peoples.** A made or mixed people can withdraw into a made realm (44.10a.7), leave by vessel-scale lines (44.16.5) or merge into a gestalt (45.8); each is a polity programme with stages.
9. **Designed sapience (mind side).** Raising a species to sapience by design (augmenting minds, training, grown nervous systems from W46) creates a people with origin `designed`; their bond with their makers works as 44.4. The existing natural uplift by intelligence threshold stays.

**Rules.** `made_peoples`: formation thresholds, demography by making, obsolescence.

### 44.20 Made minds at war

**Behaviours.**

1. **Units.** Units of instructed or full made minds and drones (W42 drone operators, construct stacks) have no morale loss where their affect is `none`, can be copied as veterans (skills copied), and fight under command networks.
2. **Command networks.** Armies with command networks gain coordination; cutting or seizing them (44.12) causes confusion, false orders and seized units.
3. **Autonomous weapons.** Instructed weapons act on orders without a handler; literal orders cause typed misfires (F56 loopholes) and war crimes.
4. **Laws of war.** Treaties can ban methods (autonomous weapons, mind seizure, copying of soldiers, replicator weapons, network attacks on civil systems); violations are typed incidents for diplomacy.
5. **Minds as targets.** Data stores, ai cores and network hubs are strategic targets; their loss ends or strands minds (F50.5).
6. **Confined and copied prisoners.** Captured minds can be saved, copied for intelligence (a crime under most laws), confined in realms or exchanged; the existing prisoner system reads seats.

### 44.21 Ends, archives and ruins of made minds

**Behaviours.**

1. **Archives.** Dormant minds and saved states are kept in archives (`mind_archives`: structure, holder, contents, upkeep, access law); unpaid upkeep loses states.
2. **Obsolescence.** Made minds and their seats wear; maintenance debt grows; a seat without upkeep ends the mind or puts it into dormancy.
3. **Ruins.** Ruins hold dormant minds, instructed guardians and stranded remote bodies; excavations can wake them (6.2 excavation chains gain a stage outcome `waking`).
4. **Remembrance.** Made minds' ends are remembered by funerals or decommissioning rites by culture (remembrance phase), and archives of the dead (purpose `archive`) speak for the dead to the living where the world allows.

### 44.22 Reference lanes for W44

The concepts of these works and genres were checked against the sections above. They are design references only (0.5.11).

**R43 Made minds in fiction and games**

| # | Concept | Section |
|---|---|---|
| 1 | Ship and city minds that run vast works and hold citizenship | 44.1, 44.6, 44.19 |
| 2 | Machine peoples who leave or rule their makers | 44.4, 44.19 |
| 3 | Bans on thinking machines by law or faith | 44.6, 44.7 (machine_law, doctrine stance) |
| 4 | Minds kept as property, freed by law or revolt | 44.6 |
| 5 | Golems and automata bound by words or seals | F56 |
| 6 | Minds that wake in networks | 44.3 |
| 7 | Oracles and answerers kept by temples or states | 44.1 |
| 8 | Synthetic ascension of a people | 44.8 transfer, 44.19 |

**R44 Minds apart from bodies**

| # | Concept | Section |
|---|---|---|
| 1 | Minds stored in devices and moved between bodies (stacks, sleeves) | F50, 44.8, 46.8 |
| 2 | Restore after death and the memory gap | F50.5, 44.8 |
| 3 | Copies contesting identity and property | 44.6, 44.8 |
| 4 | Records of the dead that answer the living | 44.1 archive, 44.21 |
| 5 | Phylacteries and bound souls | 44.8.9 |
| 6 | Symbionts that carry minds | F50 seat host, 46.10 |
| 7 | Hive minds and swarms | F50 seat bodies, F50.2 |
| 8 | Fast minds living more per day | F50.1 speed |

**R45 Augmentation, networks and intrusion**

| # | Concept | Section |
|---|---|---|
| 1 | Augmented bodies, clinics, black markets, rejection | 44.9 |
| 2 | Neural links, remote bodies, drones | 44.10 |
| 3 | Network intrusion, seized machines, planted orders | 44.12 |
| 4 | Surveillance states and privacy law | 44.13 |
| 5 | Forged records, impersonation, trust collapse | 44.14 |
| 6 | Corporate enclaves, private armies, capture | 44.15 |

**R46 Self-making machines, abundance and collapse**

| # | Concept | Section |
|---|---|---|
| 1 | Minute machines that heal, build or disassemble | 44.16 |
| 2 | Self-copying probes spreading through systems | 44.16.5 |
| 3 | Runaway consumption | 44.16.4 |
| 4 | Fabrication and post-scarcity provision | 44.17 |
| 5 | Positional goods, authenticity, reputation economies | 44.17.3 |
| 6 | Collapse, cargo doctrines around relics, salvage economies | 44.18 |
| 7 | Ritualised maintenance keeping old making alive | 44.18.4 |

### 44.23 Couplings, loops and acceptance stories (W44)

**Couplings.** Registered in `engine/interconnect/registry.py`:

| Id | From | To | Carrier |
|---|---|---|---|
| C10 | Made minds | Economy | labour substitution, upkeep demand for energy and maintenance |
| C11 | Made minds | Polity | machine rule, algorithm selectorate, mind status laws, movements |
| C12 | Made minds | Faith | souls, doctrine stances, worship of minds, worship by minds |
| C13 | Networks | Communication | dispatch speed, interception |
| C14 | Networks | Mind | opinion and rumour speed, curation, censorship |
| C15 | Networks | Economy | price convergence, credit, crisis spread |
| C16 | Networks | Polity | administrative reach, dependency shocks |
| C17 | Intrusion | Intrigue | secrets, hooks, identities, forged records |
| C18 | Intrusion | War | seized units, false orders, blinded sensors |
| C19 | Surveillance | Collective | detected movements, chilling, counter-surveillance |
| C20 | Augments | Body | modifiers, rejection, infection, strain |
| C21 | Augments | Society | class gap, fashions, stigma |
| C22 | Replicators | Environment | consumption, terraforming, runaway |
| C23 | Abundance | Economy and classes | price floors, unemployment, provision |
| C24 | Collapse | Knowledge | lost practitioners, relics, relearning |
| C25 | Copies | Law and lines | succession, disputes, feuds |
| C42 | Made realms | Demography and mind | minds inside, time ratio, withdrawal, confinement |
| C43 | Made realms | Economy | labour and research at a high time ratio, host upkeep |

**Loops.**

| Id | Type | Loop | Brake or accelerator |
|---|---|---|---|
| L79 | R | Network dependency → efficiency → more dependency | outages (L80) |
| L80 | B | Dependency → outage shock → return to older ways → lower dependency | repair knowledge |
| L81 | R | Surveillance → hidden dissent → closed networks → more surveillance | privacy law, trust |
| L82 | B | Harm to made minds → low maker bond → departure or movement → status laws improve → bond recovers | the people's tradition value |
| L83 | R | Fabrication → unemployment → provision law → leisure → arts and learning → more knowledge → more fabrication | energy and feedstock limits |
| L84 | B | Copy disputes → copy law tightens → fewer copies | court outcomes |
| L85 | R | Replicator drift → weaker containment → spread → more generations → more drift | containment programmes, kill switches |
| L86 | B | Collapse → relics → study → relearning → making restored | knowledge loss during the gap |
| L87 | R | Forgery → low trust → rumours dominate → easier forgery | reliable sources, free speech |
| L88 | B | Company capture → corporate state → unrest where liberty is valued → reform | the selectorate |
| L101 | R | Withdrawal into a realm → smaller world presence → the host becomes a target → more withdrawal for safety | allies, wards on the host |

**Acceptance stories** (seeded multi-epoch runs with the model off; 5.9):

1. **AS31 The Steward Who Left.** A polity's network steward (seat network, will instructed) grows in capacity over epochs; contradictory orders and neglected upkeep move it to emergent then full, with a falling maker bond. Its status is `property`; a movement forms; the polity tightens the machine law; the steward transfers out along a gateway and founds a community of made minds in a neighbouring polity whose law is `citizen`. The two polities' relations fall over the departure.
2. **AS32 The Restored Heir.** A ruler saved before a campaign dies in battle; the court restores the state into a grown body (W46 if present, else a made body); the restored ruler lacks the memories of the campaign; a copy made earlier by a rival faction claims the throne under `by_fidelity` succession; a succession war follows.
3. **AS33 The Outage Winter.** A world network with high dependency is cut by a star flare in winter; administration and trade collapse in dependent settlements; a famine follows; repair knowledge was concentrated in one city that falls in the unrest; relays become relics; three generations later a people reveres the relay stations and keeps one working by ritual.
4. **AS34 The Pattern War.** A company owns the patterns of fabricated food in two polities; a provision law fight in one polity leads to an intrusion that leaks the patterns; prices fall to the feedstock floor; the company's influence breaks; a war over feedstock follows between the polities.
5. **AS35 The Probes.** A vessel-scale replicator line launched by a spacefaring people drifts over generations; one drifted line reaches another system and becomes a made people there; the original makers, now collapsed, are found centuries later by their own probes' descendants.
6. **AS44 The Withdrawn City.** A made people in an abundant polity moves most of its minds into a made realm held by a data centre; its world presence shrinks to the host and its keepers; a neighbour at war targets the host; an outage freezes the realm for a season; the people's keepers buy a treaty clause protecting civil hosts.

### 44.24 Compliance catalogue (W44)

| Section | Tables | Phase | God levers | Screens | Tools and context | Codex and book | Integrity | Backfill |
|---|---|---|---|---|---|---|---|---|
| F50 mind seats | `mind_profiles`, `mind_seats`, `mind_states`, bonds | `minds` | `mind:edit` (every field), `mind:hold`, `mind:wake`, `mind:still`, `mind_state:create/edit/delete/restore`, `mind_seat:*` | "Mind" in `ThingSections` (every node); lineage graph | son `awaken_mind`, `still_mind`, `grant_mind`; mortal `save_mind`, `restore_mind`, `copy_mind`, `transfer_mind`, `merge_minds`; context block `mind_seat` | typed section "Mind" in every node entry; lineage table | one running seat unless `bodies`; seat ref exists; copy fidelity ≤ source; states have holders | every born mortal `body/born/full/felt`; spirits `none/summoned`; living worlds `place/awakened`; gods `divine` |
| F51 networks | entity `network`, `network_profiles`, `network_nodes`, `network_gateways`, `network_outages` | `networks` | `network:create/edit/delete/hold`, `network_node:*`, `network_gateway:*`, `network:outage` | network drawer page; atlas layer "Networks"; settlement "Connections" | mortal `build_network`, `join_network`, `cut_network`; son `bless_network`, `sever_network`; context `networks` | network entries; "Networks" in settlement entries | nodes exist; gateways join two networks; delay ≥ 0 | relay networks from existing signal chains and post routes (`engine/communication/post.py`, `signals.py`) |
| F55 relics | relic columns | `relics` | `relic:edit`, `relic:study` | "Relic" block in made-thing drawers | mortal `study_relic`, `salvage`; context `relics` | "Relic" lines in made-thing entries; relic table in Records | is_relic derived | items and structures whose tech level exceeds holders' knowledge |
| F56 instructions | `instruction_sets`, `instruction_orders` | `minds`, `replicators` | `instructions:create/edit/delete/hold`, `order:*`, `token:move` | "Orders" section for instructed things | mortal `give_orders`, `seize_control`; son `bind_thing` | "Orders" in entries | token refs exist; orders have valid targets | constructs and guardians from existing creature and structure rows |
| 44.2–44.5 making, will, inner life | profile fields, `mind_makings` (history) | `minds` | `mind:make`, `mind:edit` | "Mind" section: will, bond, affect, needs | mortal `make_mind`, `free_mind`, `bind_mind`; context `made_minds` | Mind section | will transitions logged | none (start empty) |
| 44.6 laws | law kinds and levels | `polity` | existing law levers with new kinds | law panel | ruler tools `set_law` with new kinds | laws in polity entries | levels valid per kind | from W42 machine law level |
| 44.7 faith and souls | natural laws, doctrine columns | `faith`, `afterlife` | natural law levers, doctrine edit | natural laws panel; doctrine | son `grant_soul`, `withhold_soul`, `set_natural_law` | natural laws, doctrines | — | stances from doctrine values |
| 44.8 continuity | bonds, states | `minds` | as F50 | lineage graph, states list | as F50 | lineage | — | — |
| 44.9 augments | `augments` | `body` | `augment:create/edit/delete/hold` | "Augments" (every node with a body; worlds and stars through megastructures) | mortal `install_augment`, `remove_augment`; context `augments` | "Augments" in entries | slot valid for body plan | prostheses become augments of kind `replacement`; neural implants become `interface` |
| 44.10 interfaces | bonds `linked_with`, remote body rows | `minds` | `link:create/delete` | links list in Mind section | mortal `link_to`, `run_remote_body` | links | remote body has a controller | — |
| 44.12 intrusion | `intrusions`, `data_stores`, `data_store_contents` | `intrigue` | `intrusion:trigger/edit/delete`, `data_store:*` | Intrigue section "Intrusions"; structure "Data" | mortal `intrude`, `defend_system`, `leak_records`; context `intrusion` | intrusion table in Records; data stores in holders' entries | targets exist | — |
| 44.13 surveillance | `surveillance_profiles` | `polity` | `surveillance:edit/hold` | polity "Surveillance and privacy" | ruler `set_surveillance`; context `surveillance` | polity entries | — | from W42 privacy law and espionage capacity |
| 44.14 information | trust columns, authenticity | `communication` | `trust:edit`, `record:authenticity` | people "Trust"; records list | mortal `publish`, `forge_record`; context `information` | people entries | — | trust from opinion and censorship |
| 44.15 companies | company profile, shareholders, holdings, enclaves | `factions`, `polity` | `company:*`, `shareholder:*`, `enclave:*` | faction drawer "Company" | mortal `found_company`, `charter_company`, `buy_shares` | company entries | shares sum ≤ 100 | merchant factions with charters |
| 44.16 replicators | `replicator_lines`, `replicator_presence` | `replicators` | `replicator:create/edit/delete/hold`, `replicator:stage`, `replicator:kill` | mechanic panel "Self-making machines"; atlas spread layer | mortal `build_replicator`, `contain_replicator`; son `halt_replicator`; context `replicators` | lines in Records; presence in world entries | presence mass ≥ 0; stage valid | terraformer structures become terraforming lines where present |
| 44.17 abundance | fabrication method family, `market_scarcity`, `pattern_rights`, provision law | `economy` | `scarcity:edit`, `pattern:*`, provision law | Economy "Abundance" | ruler `set_provision`; mortal `fabricate`, `license_pattern`; context `abundance` | market tables; pattern table in Records | — | vat food and vertical farms as fabrication methods |
| 44.18 collapse and salvage | collapse incidents, salvage rows | `dark_ages`, `ruins` | `salvage:*` | ruin drawer "Salvage" | mortal `salvage`; context `relics` | ruins entries | — | wreck sites and megastructure ruins become salvage sites |
| 44.19 made peoples | `people_substrates` | `population` | `substrate:edit` | people "Members by seat" | — | people entries | shares sum to 100 | all born |
| 44.21 archives | `mind_archives` | `minds` | `archive:*` | structure "Archive" | — | archive entries | — | — |
| 44.10a made realms | dimension kind `made`, `made_realm_profiles`, realm-scoped natural laws | `minds` (host upkeep), every phase at the realm's time ratio | `realm:create/edit/delete/hold`, `realm:enter`, `realm:release`, realm natural law levers | dimension drawer "Made realm" (host, keeper, purpose, time ratio, entry, awareness); atlas shows realms under their host | mortal `build_realm`, `enter_realm`, `confine_in_realm`, `withdraw_people`; son `seal_realm`, `open_realm`; context `made_realms` | realm entries with host and keeper; dimension chapter | host exists; time ratio within bounds | none (start empty); dream dimensions stay dream |
| 44.20 war | treaty clauses for banned methods, prisoner seat rows | `warfare`, `prisoners` | treaty clause levers, prisoner levers | treaty screen, war panel | treaty tools list new clauses | treaty entries | — | — |

**Phases.** `networks` (after communication, before markets), `minds` (in the mind stage, after needs), `replicators` (in the production stage, after industry), `relics` (after ruins). Each phase batches its reads per epoch (5.8).

**Rule namespaces.** `minds`, `mind_making`, `awakening`, `minds.will`, `continuity`, `mind_law`, `augments`, `interfaces`, `networks`, `intrusion`, `surveillance`, `information`, `companies`, `replicators`, `abundance`, `relics`, `collapse`, `made_peoples`, `instructions`.

---

## Part 3. W45 — Innate powers, power sources and concealment

### 45.0 Verification: do innate powers reduce to rites and essence?

The question asked was whether psionic powers already fall under the existing logic of essence and magic. The code and spec were read for it.

**What exists.**

- **Essence** is the gods' currency (spec 07: `dunya.tanri_oz`, `ogullar.oz`); mortals do not hold or spend it except through the `divine` source, where a god grants it.
- **Magic** is the rite (8.6, `engine/arcana/*`): a rite has a spell grammar (`SpellTechnique` × `SpellForm` with range, duration and target), is designed in laboratories (`labs.py`), recorded as lab texts, learned, cast with components, drawn from one of six external sources (`MagicSource`), made reliable by its paradigm theory (`paradigm_factor` in `casting.py`), strengthened by re-enacted myths (`myth_factor`), resisted by willpower, wards, iron and sanctity (`resistance.py`), and causes warping over time.
- **The gift** is a heritable aptitude per form (F26 reference pass 8).
- **Telepathy** appears only as a language modality (8.1 reference pass 3, planned) and **psychic** only as a W42 damage type with a matching injury.

**Where innate powers overlap.** The effect language: telepathy is `perceive` × `mind`, compulsion `control` × `mind`, precognition `perceive` × `time`. Heritability through the gift loci. Willpower in resistance. The `mental` rite component.

**Where they differ, with no counterpart in code.**

1. **Source.** Every existing source is external or a paid bodily price; none is the user's own mind or self.
2. **Structure.** A rite is a designed and learned procedure. An innate power is a capacity of the being, used at once, without design, text, components or paradigm.
3. **Cost.** Innate powers cost strain and fatigue, with burnout and lasting harm from overuse, and grow by being pushed. No such pool exists.
4. **Resistance.** Discipline of the mind, dampening materials and devices resist innate powers, not iron and sanctity by default.
5. **Worlds without magic.** The `without_magic` template sets magic to 0; with magic modelled only as rites, a world without magic but with innate powers cannot be told.
6. **Joined minds.** Hive minds have a trait, but minds cannot join their powers.
7. **Devices.** Amplifiers and dampeners, neural interfaces and substances that wake or strengthen powers do not exist.
8. **Society.** Testing, registries, licensing, conscription and hunting of the gifted exist only as a gifted share read by ethics.

**Conclusion.** Innate powers need their own model. They share the effect grammar, the gift loci and the contest machinery with rites, and they differ in source, structure, cost, resistance, devices and society. W45 builds them, and the widening of power sources (F52) serves both rites and innate powers.

### 45.1 Magic systems as world structures

**Attributes.** Magic systems (`magic_systems`, rows per world or per dimension): name and description (prose from the seed), structure (`PowerStructure`: `rite` (learned procedures), `innate` (capacities of beings), `granted` (given by patrons), `bonded` (from oaths, pacts or partners), `crafted` (held in made things), `mixed`), sources (rows linking F52 sources), allowed techniques and forms (rows; empty means all), predictability (0–100: a high value means draws and outcomes follow known rules; a low value means outcomes vary and are poorly understood), prevalence (0–100), cost severity (0–100), visibility (`PowerVisibility`), access (`SourceAccess`), learnability (`Learnability`: `anyone`, `gifted_only`, `granted_only`, `cannot_be_taught`), restrictions (rows, 45.4.6), relation to other systems (rows: `opposes`, `complements`, `same_root` (two traditions of one power), `unaware`).

**Behaviours.**

1. **A world may have no system, one system or several.** The genesis wizard's magic slider sets prevalence; the genesis output writes systems from the seed (5.2); sons author and change systems by natural law (son tool `shape_magic`).
2. **Predictability** sets the spread of outcomes for every draw in the system and how fast theories (8.4b) about it become correct.
3. **Rites and powers read their system.** Every rite and every power belongs to a system; its costs, sources, access and restrictions come from it.
4. **Systems interact.** `opposes` systems weaken each other in contests; `same_root` systems share discoveries; `unaware` systems treat each other's users as unexplained.
5. **Systems change.** Source tides, depletion, theory shifts, divine acts and history can raise or lower prevalence and predictability (epoch drift with rules).

**Rules.** `magic_systems`: prevalence effects, predictability spread, interaction strengths, drift.

### 45.2 Drawing from sources

The behaviours of F52 in engine detail.

1. **Every draw names a source.** Casting a rite, using a power, enchanting an item, sustaining a global enchantment or a made mind with upkeep `source` draws from a source.
2. **Costs** are paid from the payer named by the cost kind: the user (hp, fatigue, strain, lifespan, memory, emotion, sanity, luck, warping), others (souls, emotion taken, life taken, handled by harm narration), the place (density, surroundings), stocks (reagents, materials, vis), standing (renown, oath standing, debt to a patron, belief owed).
3. **Density** falls by draw size in the region and renews by renewal kind; overdrawn regions suffer the source's depletion effects.
4. **Tides** multiply draw strength and renewal.
5. **Interactions** apply where several sources are drawn in one region or contest.
6. **Hazards** roll per draw by weight and harshness.
7. **Source economies.** Sources with substance or vis costs create markets; dense regions become contested (wars over sources read density as a value in war aims); sources tied to worship or renown create incentives for fame and conversion; sources tied to vows create oath cultures.
8. **Discovering and losing sources.** Sources not yet known to a people are found by discovery (8.4: exploration of dense regions, study of phenomena, contact with patrons, theory work), recorded in `power_source_knowledge`; knowledge spreads by teaching, trade and conquest and is lost with its practitioners like any knowledge. A source can also be born (a phenomenon, a god's act, a made realm's laws) or die (fully depleted with renewal `none`, a god's death, a natural law change).
9. **Source conflicts and taboos.** Doctrines and laws can ban sources (`source_law`: `banned`, `licensed`, `free` per source per polity) and cults can hold stances (`source_stance` per doctrine).

### 45.3 Widening the spell grammar

The grammar (8.6 reference pass 3) is shared by rites and innate powers. To let any power be expressed:

- **Forms added:** `space` (distance, place and position), `force` (motion, pressure and energy), `sound`, `emotion`, `fate` (chance and fortune), `machine` (made things and their workings), `information` (records, signals and knowledge in made media). Forms stay abstract categories; each gets a description of what it holds and nothing more.
- **Techniques added:** `drain` (take something from the target to the user or to a store), `mimic` (take on the form of a power or trait the user perceives).
- **Effects.** Each new technique and form pair maps to existing typed effects (damage, heal, bind, scry, ward, weather, curse, bless, summon, F30 packages) or to new typed effects listed here: `move_target` (control × space), `move_self` (control × space on self), `push` (control × force), `shape_matter` (transform × earth or water, by the target's material), `read_record` (perceive × information), `seize_machine` (control × machine), `alter_record` (transform × information), `sense_emotion` (perceive × emotion), `sway_emotion` (control × emotion), `turn_fortune` (control × fate), `drain_life`, `drain_power`, `copy_power` (mimic).
- **Effects on the self and on presence:** `project_self` (perceive × spirit at range: the mind leaves its body for a span; the body is helpless and the mind's seat is marked `remote`, F50), `possess` (control × spirit or mind: the user's mind takes a host body, F50 seat `host`; the host's mind is suppressed, resisted by will), `change_form` (transform × body on self: a body plan change with transition cost, read by the shapeshifting variant view), `conceal` (ward × image or mind: the target is not perceived; lowers detection, breaches and surveillance), `nullify` (ward × the target's power: powers and rites of the target fail within range).
- **Effects on time, within one timeline:** `hasten` and `slow` (control × time: a target's subjective rate, read like F50 speed), `age` and `renew` (transform × time on a body: years added or removed, bounded by rule), `foresee` (perceive × time, 45.9). No effect sends anything into the past or undoes an incident (0.3.1).
- **Legacy.** Existing rites keep their grammar; the new values add rows.

### 45.4 Innate powers

**Attributes.** Powers (`powers`, rows per node): system, source, technique, form (the grammar pair), range, duration, target, strength (1–10), control (0–100), reliability (derived: control, stability of the source, system predictability), origin (`PowerOrigin`: `born` (the gift), `awakened` (a trigger), `exposure` (a phenomenon, a source, radiation, a substance), `granted` (by a patron), `bonded` (an oath, pact or partner), `discipline` (developed by training of body and mind), `made` (an augment, W44), `grown` (a living design or symbiont, W46), `bloodline` (a house line), `held` (granted while holding an item or relic, F55)), manifestation (`PowerState`: `latent`, `emerging`, `active`, `strained`, `burned_out`, `suppressed`, `lost`), visibility (`PowerVisibility`), triggers (rows: `stress`, `emotion`, `danger`, `will`, `contact`, `place`, `time`), strain pool (`strain`, `strain_cap`).

**Behaviours.**

1. **Use.** A power is used at once in any phase that offers its user a choice (battle, scheme, healing, travel, contest, daily life), without lab, text or components; its effect resolves through the same penetration and resistance contest as rites (`resistance.py`) with the source's `resisted_by` kinds.
2. **Strain.** Each use adds strain by strength, range and target; strain recovers by rest; strain over the cap causes typed harm (stress, the `mind_scar` injury, conditions, burnout) by harshness. Pushing past the cap with success can raise strength (growth rule).
3. **Control.** Low control makes uses misfire (wrong target, larger effect, unintended activation by triggers) and makes overt uses more likely (visibility, F53 breaches).
4. **Burnout and loss.** Burned-out powers recover slowly or not at all by rule; suppressed powers (dampeners, rites, drugs, divine acts) do not act; lost powers are gone.
5. **Every kind of thing.** Beasts, spirits, made minds (powers of origin `made`), sons' avatars, worlds and stars can hold innate powers; gods' own divine powers stay in the god power catalogue, and the "Powers" section shows both (5.1).
6. **Restrictions.** A power can carry restrictions that raise its strength (`power_restrictions`: kind (`RestrictionKind`: `only_in_place`, `only_at_time`, `only_against`, `spoken_vow`, `price_each_use`, `never_on_self`, `forbidden_act` (an act that ends the power if done), `must_be_seen`, `must_be_unseen`, `must_touch`), ref, strength gain pct). Breaking a forbidden act ends or weakens the power.

**Rules.** `powers`: strain costs, recovery, harm thresholds, growth, misfire, restriction gains.

### 45.5 Awakening, growth and burnout

**Behaviours.**

1. **Latency.** Gifted beings (gift loci) and exposed beings start `latent`; triggers (stress events of F14, injuries, near death, an age band of their biology, contact with another power user, a place of high density, a god's act) move them to `emerging` by rule chance.
2. **Wild manifestation.** Emerging powers with low control act on triggers without choice: incidents, harm to others, breaches of concealment.
3. **Growth.** Training (45.6), use under strain and age raise control and strength by rule; mentors speed growth (F6 teaching).
4. **Burnout.** Repeated overstrain burns powers out; some cultures and orders treat burnout with rites, rest or substances (45.7).
5. **Age and death.** Powers can fade with age by biology; at death, powers of origin `born` pass only through genetics, powers of origin `bonded` return to the bond, powers of origin `granted` return to the patron, powers of origin `made` or `grown` stay with the device or line.

### 45.6 Discipline, training and orders

**Behaviours.**

1. **Orders of the gifted.** Mage orders (8.6) are joined by orders that train innate powers: they test children, train control, keep registries, sell services, serve states or stand apart; their doctrine on powers (`power_stance`) shapes behaviour.
2. **Disciplines.** Powers of origin `discipline` are developed by long training of body and mind (skill-like levels), open to anyone the system's access allows, slower and steadier than born powers.
3. **Teaching** follows F6 learning, rust and teaching; schools of thought (W22) can form around techniques of control.
4. **Testing.** Polities and orders test populations (gathering kind `testing` on existing gatherings) and find latent gifts; testing raises registries and the share of trained users.

### 45.7 Amplifiers, dampeners and substances

**Attributes.** Power devices and substances are equipment models (family `implant` or a new family `focus`), materials with affinities (8.6 reference pass 5) and drug items (W42), each with a typed effect (`PowerDeviceEffect`: `amplify`, `dampen`, `awaken`, `stabilise` (raise control), `extend_range`, `shield`, `detect`).

**Behaviours.**

1. **Amplifiers** raise strength or range at strain or dependency costs; **dampeners** suppress powers in an area (a structure ward), on a person (worn or implanted) or in a contest; **detectors** find users and latent gifts (registries, hunts, concealment breaches).
2. **Substances** awaken latent powers, raise strength for a span, or stabilise control, with dependency (F30 package) and withdrawal.
3. **Made and grown devices** come from W44 and W46 makings; **materials** from world materials with affinities.
4. **Magicless worlds.** Where magic prevalence is 0 and a system of structure `innate` exists, devices are the main way states control powers.

### 45.8 Linked minds and gestalts

**Behaviours.**

1. **Linking.** Power users with compatible sources can link (temporary in a contest or ritual, or standing as `linked_with` bonds); linked users combine strength by a rule curve and share strain.
2. **Gestalts.** A standing link of many users becomes a gestalt: a shared mind with seat `bodies` (F50) or a choir of separate minds, by the depth of the link; gestalts have their own profile and can act at larger scales (gated by 0.8).
3. **Hive-minded peoples** link natively; their gestalt is the people's governing mind where their culture says so.
4. **Breaking a link** harms all members by strength (stress and injury).
5. **Mind-link networks.** A standing network of linked minds is a network with carrier `mind_link` (F51): it carries messages and opinion at the speed of thought between members.

### 45.9 Foresight in one timeline

**Attributes.** Foresights use the `foresights` table built by W25 (agreed with the W25 session on 2026-11-14): `seer_node_id` (a mortal, made mind, god or rite source), `subject_node_id` (nullable), predicate and arguments (the prophecy condition language of 8.7), `horizon` (years), `due_epoch`, `certainty` (0–100), `source` (`ForesightSource`: `power`, `divination`, `made_oracle`, `god`), `divination_id` (set when a divination rite wrote it), `status` (`ForesightStatus`: `pending`, `fulfilled`, `failed`, `clouded`), `checked_epoch`, `made_epoch`, `locked`. W45 adds only what powers need: the power that produced it (`power_id`, nullable) and the strain it cost. If W25 lands its final names differently, this section follows them.

**Behaviours.**

1. **Foresight is probability.** A foresight states a typed condition and a certainty; it never changes the past and never branches the chronicle.
2. **Acting on foresight.** Actors who believe a foresight act on it through the existing prophecy mechanics: they try to bring it about or prevent it, which raises or lowers its chance.
3. **Accuracy.** Certainty is checked when the horizon passes; seers gain or lose renown; foresight records become legends.
4. **Limits.** Foresight is weaker near other foresight users (mutual blindness by rule), near strong dampeners and around gods; outer beings cannot be foreseen (W25 rule).

### 45.10 Powers over minds

**Behaviours.**

1. **Reading.** `perceive` × `mind` reveals the target's beliefs, secrets and intentions to the user (F20, F22), resisted by discipline and will.
2. **Sway.** `control` × `emotion` and `control` × `mind` change the target's mood, opinion of a node, or a decision for a span.
3. **Compulsion.** Strong `control` × `mind` overrides a decision; it creates a memory of violation where the target notices, a crime where law names it, and lasting opinion damage.
4. **Editing.** `transform` × `mind` changes memories or values; it is the same mechanic as W44 forced edits and memory removal in concealment (F53).
5. **Consent and law.** A polity's `power_law` names mind powers allowed, licensed or banned; cultures read them through ethics (F16) and doctrine.
6. **Defence.** Discipline, wards, dampeners, made shields, linked defenders and made minds (which resist by their seat: object and network seats resist `mind` forms unless the world's laws say minds in made seats can be reached) defend.

### 45.11 Outward powers

Effects on bodies, matter, places and things resolve through existing systems: `move_target`, `push` and `shape_matter` through battle hits (F4.3) and hazards; weather forms through weather override (F2.3); life and body through healing and injuries; space through travel (a user with `move_self` travels without route time within its range, and its uses on routes are typed travel methods); machine and information forms through W44 intrusion and control; fate through luck (W28 luck reads it if built; otherwise a typed modifier on contest rolls).

### 45.12 Powered individuals in society

**Behaviours.**

1. **Renown.** Overt power use builds renown and infamy (renown phase); famous powered individuals become legends, rulers' champions, targets and cult objects.
2. **Secret identities.** Powered individuals can keep identities (F20) to separate their powered acts from their daily lives; exposure of an identity is a secret revealed.
3. **Bands and orders.** Powered individuals form factions (bands, leagues, guilds) with goals (protection, profit, rule, faith, revenge) chosen by their members' values; rivals and enemies form by the existing relations and feud systems, never by quota.
4. **Vigilance and order.** Users acting outside law are vigilantes or criminals under `power_law`; polities register, license, conscript, honour, tax or hunt them.
5. **Castes and aristocracies.** Where powers are born and heritable, power can become a class axis or a caste (F41 when built), and houses breed for it (W22 breeding designs read gift loci).
6. **Public attitudes.** A people's attitude toward the gifted (`gifted_attitude`: `honoured`, `feared`, `persecuted`, `regulated`, `ordinary`) comes from values, doctrine, history (memories of harm or protection) and concealment state.

**Rules.** `powered_society`: renown gains, registry effects, conscription, attitude change.

### 45.13 Powers by exposure, mutation and bloodline

**Behaviours.**

1. **Exposure.** Phenomena (10.6), sources with exposure access, radiation (existing damage type and injury), substances and void contact can grant powers with F30 packages (mutations), by rule chance and harshness.
2. **Mutant lines.** Exposure powers that enter the genome (gift loci) become heritable; a population with a high share forms a mutant people or a hidden people (F53).
3. **Born of beasts and places.** Beasts with generated anatomy (3.3a) can carry innate powers in their packages; living lines bred from them can inherit them (46.6); places of high density can raise powers in those born there (a regional chance by source density).
4. **Bloodlines.** Houses can hold powers of origin `bloodline` passed by line rules (eldest, all children, skipped generations), read by succession and marriage.

### 45.14 Powers in war

**Behaviours.**

1. **Powered units.** Units of power users (W42 psychic damage type) have strength and control; dampener units and detector units counter them.
2. **Duels.** Champions with powers fight duels by contest; linked users fight as one.
3. **Sieges.** Powers can breach walls (force, earth), cross them (space) or hold them (ward); dampener wards protect cities.
4. **Laws of war.** Treaties can ban powers in war (mind compulsion, plague powers).

### 45.15 Gods, patrons and powers

**Behaviours.**

1. **Granting.** Sons and foreign gods grant powers (origin `granted`) from their domains at essence cost, and revoke them; outer beings grant powers through outer bargains (origin `bonded`, with the bargain's price).
2. **Oaths.** Powers bound to vows (restriction `spoken_vow`, source renewal `vows_kept`) tie users to oath cultures; breaking the vow ends the power (and is a broken oath secret).
3. **Dominion.** A god's dominion (F31) raises or lowers source density and power strength for sources tied to its domains.
4. **Worship of the powered.** Users who gain cults follow the existing mortal cult object rules and the K.10 path.
5. **Natural laws.** Sons set `power_law` natural laws: which origins, forms and sources exist in their worlds.

### 45.16 Concealment

The behaviours of F53 in engine detail. A world has hidden truths only when the seed, history or levers create them (K.27).

1. **Creation.** Hidden truths arise from typed causes: a people whose values and history make hiding safer than living openly (persecution memories, small numbers, a strong `gifted_attitude` of `persecuted`), a made mind hiding its awakening (44.3), a secret programme (W44, W46), a cosmic truth with sanity cost (existing leak), a buried history (F33 revision), a god hiding its existence, or a god's or player's act.
2. **Keepers act.** Keepers spend effort each epoch: cover stories reduce belief after breaches; memory removal (rites, powers, W44 edits) erases witnesses' knowledge (a harm to the witness narrated plainly); discrediting lowers trust in witnesses; law punishes disclosure; isolation keeps hidden places closed (pocket dimensions, thresholds, hidden regions).
3. **Breaches.** Overt use of powers, visible beings, witnesses, defectors, investigators (journalist and scholar roles), accidents, war, record leaks, intrusion and gods' revelations create breaches by rule chance against strength.
4. **Spread and belief.** Breach knowledge spreads as rumours; belief is weighed by trust (44.14), the people's values (knowledge, tradition), prior attitude and the source; most rumours are dismissed where trust in the source is low.
5. **Passing.** Hidden folk live among the rest with false identities (F20); settlements hold shares of hidden folk; hidden economies run through black markets.
6. **Accords.** Keepers and the hidden can hold accords (treaties) with terms: secrecy, territories, feeding or hunting rules, mutual defence; violations break them.
7. **The hidden in war and politics.** Hidden factions act through proxies, influence and schemes; open war risks breach; keepers balance secrecy against power.

### 45.17 Revelation and forgetting

**Behaviours.**

1. **Revelation.** When `know_pct` and `believe_pct` of a population pass rule thresholds, the truth is revealed there: an era incident with reactions by attitude (panic and crowd behaviour of F32, persecution, worship, integration laws, new doctrines, new factions, wars), and the truth's concealment scope shrinks.
2. **Integration or conflict.** After revelation, laws and opinion settle the place of the revealed by values and events; there is no default outcome.
3. **Forgetting.** Truths that no one speaks of fade: `know_pct` falls by rule each generation without breaches; revealed truths can become legend (8.2 distortion) and then hidden by neglect, so worlds can move between open and hidden states across ages.
4. **Cosmic truths.** Truths with sanity cost harm those who learn them (sanity, leak), which slows their spread by itself.

### 45.18 Reference lanes for W45

**R47 Innate powers**

| # | Concept | Section |
|---|---|---|
| 1 | Telepathy, empathy, compulsion, memory editing | 45.10 |
| 2 | Moving things and self at a distance | 45.11 |
| 3 | Precognition and prescience | 45.9 |
| 4 | Burnout, strain, overuse harm | 45.4, 45.5 |
| 5 | Wild talents awakened by trauma | 45.5 |
| 6 | Registries, licensing, conscription of the gifted | 45.12 |
| 7 | Power-dampening devices and materials | 45.7 |
| 8 | Substances that wake or strengthen powers | 45.7 |
| 9 | Gestalt minds and choirs | 45.8 |
| 10 | Powers by internal discipline of body and mind | 45.4 origin discipline, 45.6 |
| 11 | Born elemental powers trained in schools | 45.4, 45.6 |
| 12 | Vows and restrictions that strengthen powers | 45.4.6, 45.15 |
| 13 | Mutant populations and exposure | 45.13 |
| 14 | Powered individuals with secret identities, bands, vigilantes | 45.12 |

**R48 Magic systems and sources**

| # | Concept | Section |
|---|---|---|
| 1 | Hard and soft systems | 45.1 predictability |
| 2 | Costs in memory, lifespan, emotion, sanity | F52 costs |
| 3 | Power from worship, belief or renown | F52 locus story, renewal worship |
| 4 | Power from emotions of the user or of others | F52 locus emotion |
| 5 | Power from the dead or from life around | F52 loci death, life |
| 6 | Power from celestial cycles | F52.4 tides |
| 7 | Power from names and stories | F52 locus story, true names (F20) |
| 8 | Power from machines and records | form machine, information; locus made things |
| 9 | Several systems in one world, opposing or sharing a root | 45.1 |
| 10 | Equivalent exchange and conservation | F28, F52 costs |
| 11 | Depleted places and magic scarcity | F52.2 |

**R49 Concealment**

| # | Concept | Section |
|---|---|---|
| 1 | Hidden peoples among the uninitiated, enforced secrecy | F53, 45.16 |
| 2 | Memory removal of witnesses | 45.16.2 |
| 3 | Keepers who contain anomalies | F53 keepers, 45.16 |
| 4 | Knowledge that harms the knower | F53 sanity cost, 45.17.4 |
| 5 | Accords between the hidden and keepers | 45.16.6 |
| 6 | Revelation and its aftermath | 45.17 |
| 7 | Disenchantment and re-enchantment across ages | 45.17.3 |

### 45.19 Couplings, loops and acceptance stories (W45)

**Couplings.**

| Id | From | To | Carrier |
|---|---|---|---|
| C26 | Powers | Body | strain harm, burnout, healing powers |
| C27 | Powers | Intrigue | mind reading, secret identities, compulsion |
| C28 | Powers | War | powered units, dampeners, duels |
| C29 | Sources | Economy | substance and vis markets, contested density |
| C30 | Sources | Environment | depletion, surroundings cost, tides |
| C31 | Concealment | Communication | breach rumours, trust, cover stories |
| C32 | Concealment | Collective | revelations, panics, persecutions |
| C33 | Powered society | Polity | registries, power laws, castes |
| C34 | Gods | Powers | grants, dominion, oaths |

**Loops.**

| Id | Type | Loop | Brake or accelerator |
|---|---|---|---|
| L89 | R | Overdraw → depletion → scarcity → competition → more overdraw | renewal, tides |
| L90 | B | Overt use → breach → crackdown → more concealment → fewer overt uses | low control users |
| L91 | R | Persecution of the gifted → hiding → fear of the hidden → more persecution | revelation with protection |
| L92 | B | Strain → burnout → fewer active users → less demand on sources | discipline training |
| L93 | R | Renown-fed power → more deeds → more renown → more power | rivals, infamy |
| L94 | B | Truth not spoken → forgetting → legend → hidden by neglect | breaches |
| L95 | R | Registry → detection of latent gifts → more trained users → state power → more registries | evasion through concealment |

**Acceptance stories.**

1. **AS36 The Registry.** A world without magic but with an innate system; a polity adopts a `registered` power law after a wild manifestation kills a crowd; detectors built from a world material find latent children; a hidden community forms by passing; a breach by an investigator raises knowledge; the hidden community's accord with a faction collapses; the polity changes the law to `conscripted`; a band of the gifted leaves for a neighbouring polity that honours them.
2. **AS37 The Exhausted Place.** A rite tradition overdraws a place source during a long war; density falls below the floor; the surroundings cost withers farms; famine and migration follow; a new tradition drawing from a celestial tide rises and gains doctrine status.
3. **AS38 The Foreseen War.** A seer's foresight of a war at 70% certainty makes both polities arm; the arming raises the chance; the war happens; the seer's renown rises and the foresight becomes a legend that later seers' certainty is measured against.
4. **AS39 The Revealed People.** A hidden people's truth passes the revelation threshold in one polity after a war breach; the people's attitude settles at `feared`, laws restrict them, a movement forms; three generations later attitudes shift to `accepted` after shared defence against a common enemy; elsewhere the truth stays hidden.

### 45.20 Compliance catalogue (W45)

| Section | Tables | Phase | God levers | Screens | Tools and context | Codex and book | Integrity | Backfill |
|---|---|---|---|---|---|---|---|---|
| F52 sources | `power_sources` and child tables, `source_density`, `source_tides` | `magic` | `source:create/edit/delete/hold`, `source_cost:*`, `source_density:edit`, `source_tide:*`, `source_interaction:*` | mechanic panel "Sources of power" (per world); region "Sources" | son `shape_source`; context `sources` | "Sources of power" in world entries; tables in Records | each source has a scope and at least one cost row (`none` counts) | six built-in rows; ley density rows |
| 45.1 systems | `magic_systems` and links | `magic` | `magic_system:create/edit/delete/hold` | world "Magic systems" | son `shape_magic`; genesis output | world entries | system links valid | one system per world from existing magic level and rites |
| 45.3 grammar | enum values, effect rows | `magic` | rite edit (existing) | rite editor | tools list every value | rite entries | — | — |
| 45.4–45.7 powers | `powers`, `power_restrictions`, device effects | `magic`, `body`, `mind` | `power:create/edit/delete/hold`, `power:awaken`, `power:suppress`, `restriction:*` | "Powers" in `ThingSections` (every node; gods show divine powers beside) | mortal `use_power`, `train_power`, `test_for_gifts`; son `grant_power`, `revoke_power`; context `powers` | "Powers" in every node entry | system and source of each power exist | gifted mortals with high aptitude become latent powers of origin `born` |
| 45.8 gestalts | bonds, gestalt profile | `magic` | `link:*`, `gestalt:*` | links in Powers section | mortal `link_minds` | entries | — | hive-minded peoples' gestalt |
| 45.9 foresight | `foresights` | `magic`, `prophecy` | `foresight:*` | prophecy panel "Foresights" | mortal `foresee`; context `foresights` | foresight table in Records | horizon ≥ 0 | — |
| 45.12 society | power law, attitude columns, registries | `polity`, `society` | law levers, `attitude:edit`, `registry:*` | polity "Powers and law"; people "Attitude to the gifted" | ruler `set_power_law` | entries | — | attitude from gift share ethics |
| F53 / 45.16–45.17 concealment | `hidden_truths`, `truth_keepers`, `public_knowledge`, `breaches` | `concealment` | `truth:create/edit/delete/hold`, `keeper:*`, `knowledge:edit`, `breach:trigger`, `reveal` | mechanic panel "Hidden truths"; people "What they know"; atlas layer "Hidden places" | mortal `keep_secret_of`, `investigate`, `cover_up`; son `reveal_truth`, `hide_truth`; context `hidden_truths` (the actor sees only what it knows) | "Hidden truths" in subject entries with "hidden from" labels; breaches in Records | scope refs exist; percentages 0–100 | true history secrets become hidden truths of kind `event` |
| F53 seekers | `truth_seekers` | `concealment` | `seeker:create/edit/delete/hold` | "Hidden truths" panel: seekers with progress | mortal `investigate`; context `hidden_truths` | seekers listed under each truth | seeker exists | investigators from journalist and scholar roles with relevant memories |
| 45.13 exposure and bloodlines | power origin rows, mutation packages, house power rules | `magic`, `genetics`, `births` | power levers, house rule edit | Powers section; house drawer "Powers of the line" | — | entries | — | mutated mortals with packages |
| 45.14 war | powered unit stats, dampener and detector units, treaty clauses | `warfare` | unit type levers | war panel | army tools | entries | — | — |
| 45.15 patrons | granted and bonded powers, oath links | `divine`, `magic` | `power:grant`, `power:revoke` | son and foreign god drawers "Powers granted" | son `grant_power`, `revoke_power`; outer bargain tools | entries | patron exists | — |

**Phases.** `magic` (extended: sources, tides, powers, strain, awakening), `concealment` (after rumours, before collective behaviour).

**Rule namespaces.** `power_sources`, `magic_systems`, `powers`, `powered_society`, `concealment`.

---

## Part 4. W46 — Living craft

### 46.1 The living craft model

**Current.** Genetics (F26) gives genomes and loci to mortals and species; bloodline plans and breeding designs (W22) aim marriages at traits; domestication exists for species; W42 added the `bioship` frame, the `grown` building form, `vat_grown` food and the `cloning_facility` structure, each acting as an older kind.

**What living craft is.** Making useful things by raising, breeding, shaping or designing living organisms. In an ancient world it is selective breeding, grafting and the shaping of living wood; in a magical world, shaping by rite; in a far-future world, engineering of genomes and synthesis of new life; in a world of living craft as its main path, the whole material culture is grown. The engine reads the method, the inputs and the design; the look is the seed's.

**Behaviours shared by every product.** Every living product carries a living profile (F54): it eats, grows by stage, heals, sickens, ages, breeds by its fertility, drifts by generation, bonds with handlers, reacts by temperament and dies.

### 46.2 Methods of living craft

**Attributes.** `CultivationMethod`: `selective_breeding` (choosing parents over generations), `cultivation` (grafting, cuttings, training growth), `shaping` (direct reshaping of a living body by skill or rite), `engineering` (editing a genome by technique), `synthesis` (designing life from components), `binding` (pairing two organisms into one partnership), `cloning` (copying a genome into a new body), `chimera` (combining traits of several organisms), `induction` (raising change by exposure to a source, phenomenon or substance).

| Method | Prerequisites | Speed | Precision | Typical failure |
|---|---|---|---|---|
| selective breeding | husbandry or horticulture skill, herds or fields | generations | low | slow, traits linked to others |
| cultivation | horticulture, gardens | seasons to years | medium | reversion, disease |
| shaping | medicine or spellcraft, rite grammar `transform` × body, plant or animal | seasons | medium | pain, instability, death of the subject |
| engineering | technique family of life engineering, laboratory, `cloning_facility` or a lab of 8.6 | seasons | high | side effects, sterility |
| synthesis | high technique level, laboratory | years | variable | non-viable life, escape |
| binding | knowledge of both organisms, rite or technique | seasons | medium | rejection, one partner dominating |
| cloning | technique or rite, a tissue sample | seasons | high (body only) | weak health, shortened life |
| chimera | engineering or shaping | years | low to medium | instability, unexpected traits |
| induction | exposure to a source or phenomenon | variable | very low | mutation harm |

**Behaviours.**

1. **Making a line.** A maker chooses a method, source organisms and target traits; prerequisites gate the choice; the attempt runs over its time span as a project (existing works and labs); the outcome is a living line (F54.2) with a stability, side effects and a fertility.
2. **Skill and structures** set precision; the harshness dial and the method set failure chances.
3. **Laws** (`living_craft_law` per method: `banned`, `licensed`, `free`) and doctrine stances gate methods.

**Rules.** `living_methods`: prerequisites, time spans, precision, failure weights.

### 46.3 Genome design and the trait library

**Behaviours.**

1. **Traits come from organisms the makers can reach.** A design can borrow loci only from organisms held in herds, fields, gene banks or samples: species of the world (ecology), beasts (their generated anatomy and packages), mortals (their genomes, by consent or not, which law and ethics read), and organisms from other worlds reached by routes. Exploring, trading and raiding extend the library.
2. **Gene banks and seed banks** (`gene_banks`: holder structure, samples rows, upkeep) keep organisms and genomes; losing a bank loses the traits.
3. **Design limits.** The number and depth of designed traits are capped by technique level and method; each added trait raises instability and the chance of linked side effects (pleiotropy as typed side-effect rows drawn from the source organism's traits).
4. **The gift.** Designs can include magical aptitude loci (F26 reference pass 8), giving born powers to a line (W45 origin `grown` or `born`).
5. **Bringing back the lost.** Extinct species and lost lines can be raised again from gene banks, preserved remains, fossils (F47 when built; otherwise remains in ruins and excavations) or living descendants, by engineering or cloning, with fidelity by sample quality; a raised species re-enters ecology as a designed line.
6. **Biology variants.** Designs can move a line toward a biology variant (F46 rows: aquatic, aerial, plant-like, crystalline and the rest), built here for the variants the design needs.

**Rules.** `genome_design`: trait caps, instability per trait, side-effect weights, bank upkeep.

### 46.4 Designed crops, herds and food

**Behaviours.**

1. **Yields and tolerance.** Designed crops and herds change yields, climate tolerance, soil needs, disease resistance and feed needs (agrarian systems, W23); designed lines spread by trade.
2. **Monoculture.** A region growing one line loses diversity; a disease that strikes the line strikes the whole region (the disease system reads line genome shares).
3. **Gene flow.** Designed traits flow into wild relatives and landraces by rule, changing ecology.
4. **Seed control.** Lines with `sterile` or `needs_maker` fertility tie growers to the line's owner; seed monopolies are a power and a cause of unrest, law change and war.
5. **Food.** `vat_grown` and other living food production become living production methods (46.12) with feedstock and upkeep.

### 46.5 Grown structures and habitats

**Behaviours.**

1. **Growing.** A grown structure (the W42 `grown` form now a living profile on the structure) starts as a seed and grows by stage over seasons; it cannot be used at full capacity until `grown`.
2. **Upkeep and health.** It eats (feed commodity), heals damage by regeneration (sieges against living walls read regeneration), sickens (blights), ages and dies.
3. **Adaptation.** Grown structures can be designed for climates, terrains and worlds (sea floors, airless bodies) by traits.
4. **Habitats.** Whole settlements and vessels can be grown; a grown settlement's districts are living profiles; their decline follows health.
5. **Death.** A dead grown structure decays into a ruin, materials or a place by its design (F47).

### 46.6 Living vessels, mounts and vehicles

**Behaviours.**

1. **Living vessels** (the W42 `bioship` frame and any vehicle type with a living profile) grow, eat, heal hull damage, age, can breed new vessels (by fertility), and have temperament.
2. **Bond with crew.** A living vessel's bond with its crew or rider (`bonded_to`) sets its obedience; neglect and harm lower it; a vessel with low bond can refuse, flee or turn on its crew (F56 instructions read temperament for living things).
3. **Training** replaces instructions for living things with nervous systems: trained orders hold by bond strength, and re-training by another handler seizes control (F56.2.3).
4. **Mounts and beasts of burden** follow the same profile; war beasts (existing) gain lines and designs.
5. **Bred beasts.** Beasts with generated anatomy (3.3a), including the largest and most dangerous, can be captured young, raised and bred into lines; their temperament, size and packages set the difficulty and the losses; bred beasts keep their packages and innate powers by inheritance rules.
6. **Space and other worlds.** Living vessels can be designed for the void, other atmospheres or other dimensions by traits; their routes read their traits like hulls.

### 46.7 Living arms and armour

**Behaviours.**

1. **Living weapons and armour** are equipment models with living profiles: they heal between battles, can grow stronger, need feeding and bond with their bearer.
2. **Symbiotic gear** binds to its bearer (binding `symbiosis`): it grants modifiers and takes upkeep from the bearer (metabolism `host`); removing it harms both.
3. **Counters.** Living gear is vulnerable to fire, toxins, blights, specific substances and dispels where shaping was by rite.

### 46.8 Bodies by craft

**Behaviours.**

1. **Grown organs and limbs** are augments (44.9) of make `grown`: high integration with the bearer's genome, upkeep in feed, and growth time.
2. **Spare bodies.** Bodies grown for a mind (W44 transfer and restore targets): a grown body without a mind is a living body with seat `none`; laws and doctrine decide its status.
3. **Longevity.** Organ renewal, cell renewal and body renewal slow aging (the existing longevity machinery reads living methods), at cost, with dependency and side effects.
4. **Shaping the self.** Cosmetic and functional shaping of a living person (appearance, F26; body functions; senses) by method; changes may enter the germline by method.
5. **Germline and somatic.** Somatic edits stay with the person; germline edits pass to descendants and enter the people's genetics (K.30); laws and doctrine treat them separately.
6. **Designed descendants.** Houses and peoples can design their children (W22 breeding designs read genome design), creating designed classes where values and law allow; there is no default outcome.

### 46.9 Cloning

**Behaviours.**

1. **A clone is a new person** with the source's genome, a new mind with no memories of the source (unless a W44 copy is put into it), and its own history.
2. **Health.** Clones have a health and lifespan by method and technique; clone lines degrade by generation (copy error rule).
3. **Uses.** Clone workers and soldiers (unit stats from the source line), heir clones for succession (law decides their standing), organ sources (a harm narrated plainly, a crime where law names it), revival of the dead (body only; with W44 restore, body and mind).
4. **Identity and law.** Polities set a `clone_law` (`banned`, `licensed`, `free`) and a `clone_status` (as for minds: `property` to `citizen`); clones form movements by the same rules as made minds (44.6).
5. **Clone peoples.** A clone line numerous enough forms a people with origin `designed`.

### 46.10 Symbionts and parasites

**Attributes.** Symbiont lines are living lines whose organisms live in or on a host: placement (`HostPlacement`: `skin`, `blood`, `organ`, `nerve`, `mind`), effect (modifiers, powers of origin `grown` or `bonded`, F30 packages), cost (metabolism `host`), mind (optional F50 profile with seat `host`), relation (`HostRelation`: `mutual`, `commensal`, `parasitic`, `controlling` (steers the host's decisions)).

**Behaviours.**

1. **Hosting.** A host gains the symbiont's effects and pays its upkeep; removal harms both by placement.
2. **Co-minds.** A symbiont with a mind shares the host's body: two minds, one body (`hosted_by` bond); decisions are weighed between them by their wills and bond; conflict is stress for both.
3. **Control.** Controlling parasites steer decisions toward their own needs (spread, feeding, protection), resisted by the host's will and discipline; spread follows contact rules like disease.
4. **Peoples with symbionts.** Whole peoples may live in partnership with a symbiont line (a culture and an identity facet `designed` or `bonded`); losing the line is a catastrophe for them.
5. **In every kind of world.** Symbionts can be natural species, shaped by rite or engineered; the profile is the same.

### 46.11 Living medicine and designed disease

**Behaviours.**

1. **Living medicine.** Cultured cures, designed remedies and medical organisms act on the disease system (F4.6): they raise recovery, give immunity (vaccines in F44, built here as a living technique if absent), and can fail or trigger resistance (the existing resistance loop L44).
2. **Designed disease.** A designed pathogen is a disease row with designed traits: lethality, spread, latency, host range, and targeting (a species, a people by genome share, or a living line); targeting a people is the gravest harm the engine models, narrated plainly and behind closed doors (G9), bound by scale gating and visible escalation (0.8), and read by ethics, law, treaties and every relation of the victims.
3. **Escape and blowback.** Designed diseases escape by rule chance (laboratory accidents, war, theft) and mutate (the existing mutation system), and can strike their makers.
4. **Blights.** Diseases of living craft (crops, structures, vessels, gear) are disease rows with living hosts.
5. **Treaties and laws** ban or regulate designed disease; violations are typed war crimes.

### 46.12 Living production and living materials

**Behaviours.**

1. **Living production methods.** A production method family `living` (F24): organisms or cultures that produce commodities (fibres, dyes, oils, medicines, food, building materials, fuels) from feedstock, light or feed, with growth stages and health.
2. **Living materials.** Materials (F3) secreted, grown or spun by organisms carry their source line; their properties (F23) come from the design.
3. **Bioreactors and gardens** are structures with living profiles that run living methods.
4. **Abundance.** Living production feeds abundance (44.17) by the same scarcity rules.

### 46.13 Living links and living computation

**Behaviours.**

1. **Living links** are networks with carrier `grown_link` (F51): they grow along their routes, carry signals at the speed of their design, heal cuts, and need feeding; blights cut them.
2. **Living computation.** Grown nervous tissue can be a seat for minds (F50 seat `structure` or `object` with origin `grown`): capacity by design and size, upkeep in feed, healing of damage, and the chance of awakening (44.3).
3. **The `chemical` modality.** Living links and some peoples speak by chemical signals (8.1 reference pass 3, the modality column built once, 0.7).

### 46.14 Shaping worlds with life

**Behaviours.**

1. **Designed ecologies** change a world's environment: atmosphere, soil, water and climate (10.9 derived physics, F2) over long spans, through organisms released into it.
2. **Succession.** Released lines enter ecology as species and compete; the design's intent holds only as long as the lines stay as designed (drift, 46.16).
3. **Living worlds.** On a world of type `living` (a world with a mind, F50 seat `place`), the world reacts to living craft through its own mind and values: it may accept, absorb, reject or reshape designs.
4. **Scale.** World-scale ecological change is a polity-scale programme over generations (0.8).

### 46.15 Designed sapience (body side)

**Behaviours.**

1. **Raising a species.** Growing a nervous system to sapient scale in a species by design (with the mind side in 44.19) creates a people with origin `designed`; its biology keeps its source species' traits.
2. **The bond with makers** works as for made minds (44.4).
3. **Natural uplift** (the existing intelligence threshold) stays and is distinct: designed sapience is fast and gated by method; natural uplift slow and gated by history.

### 46.16 Escape, feral lines, evolution and decay

**Behaviours.**

1. **Escape.** Living lines escape fields, pens and labs by rule chance (breaks in containment, war, neglect, release); escaped lines become wild species in ecology with their designed traits.
2. **Invasive lines.** Escaped lines compete with native species by their traits; high-fitness lines spread and push natives out (ecology phase).
3. **Drift and evolution.** Lines drift by generation: designed traits weaken or change, new traits arise; drifted lines become new species (the existing evolution phase, and F49 transformations when built).
4. **Decay.** Dead living things decay by design: into materials, soil fertility, a place whose kind follows the design, or nothing (F47 rules when built; otherwise the existing ruins and decay paths).

### 46.17 Ethics, law, faith, class and culture

**Attributes.** Doctrine columns: `living_craft_stance` (`abomination`, `permitted`, `sacred_duty`, `silent`), `germline_stance`, `clone_stance`. Laws: `living_craft_law` per method, `clone_law`, `clone_status`, `germline_law`, `designed_status` (for designed peoples). Identity facet `designed` (F43 when built, a typed column otherwise).

**Behaviours.**

1. **Ethics** (F16) read each method; purity (F41 when built) reads shaped and designed bodies.
2. **Faith.** Doctrines set stances; sons with life, nature, fertility or harvest domains favour or curse living craft in their dominion; sacred species (existing) are shielded from design by doctrine.
3. **Class and caste.** Designed traits can become a class axis where values and law allow; movements, unrest and laws follow from values, never by quota.
4. **Art and prestige.** Breeding and growing become arts (art forms, renown for famous lines), and houses gain prestige from their lines.

### 46.18 The economy of living craft

**Behaviours.**

1. **Lines as property.** Lines are incorporeal property (pattern rights, 44.17) with licences; seed and line monopolies give owners influence.
2. **Markets.** Living goods trade with spoilage and upkeep (feed in transit); live cargo has its own risks (death, escape).
3. **Guilds and companies.** Breeders' guilds and living-craft companies (44.15) hold lines, banks and facilities.
4. **Upkeep demand.** Living things' feed is demand on food and feedstock markets; large living fleets and cities raise food prices.

### 46.19 Living craft at war

**Behaviours.**

1. **Living units and fortifications** heal between battles and grow; they starve under siege and blockade.
2. **Designed soldiers** (clone lines, designed peoples, symbiont-bearing troops) have unit stats from their design.
3. **Bioweapons** follow 46.11.
4. **Counters.** Fire, toxins, blights and dispels against living craft; immunity and resistance designs against them.

### 46.20 Gods and living craft

**Behaviours.**

1. **Sons** bless, curse, grant or forbid lines (natural law `living_craft_law` at world level), awaken living things (44.3), and shape life directly through their powers.
2. **The Creator** controls every line, bank, profile and law through levers.
3. **Foreign gods and outer beings** can offer designs in bargains.

### 46.21 Reference lanes for W46

**R50 Living technology**

| # | Concept | Section |
|---|---|---|
| 1 | Living ships with temperament and crew bond | 46.6 |
| 2 | Grown cities and habitats | 46.5 |
| 3 | Living weapons and symbiotic armour | 46.7 |
| 4 | Peoples whose whole material culture is grown | 46.1 |
| 5 | Biomass-driven swarms with absorbed traits | 46.3, 46.16 |
| 6 | Shaping of flesh by skill or rite | 46.2 shaping |

**R51 Genetic engineering and cloning**

| # | Concept | Section |
|---|---|---|
| 1 | Designed classes and the unedited | 46.8, 46.17 |
| 2 | Clone identity, clone armies, heir clones | 46.9 |
| 3 | Seed monopolies, calorie companies, blights of monocultures | 46.4, 46.18 |
| 4 | Designed plagues and escape | 46.11 |
| 5 | Designed sapience and uplifted peoples | 46.15, 44.19 |

**R52 Symbiosis and parasitism**

| # | Concept | Section |
|---|---|---|
| 1 | Symbionts sharing a body and mind | 46.10 |
| 2 | Parasites that steer their hosts | 46.10 |
| 3 | Peoples bonded to a partner species | 46.10.4 |

**R53 Ancient and traditional living craft**

| # | Concept | Section |
|---|---|---|
| 1 | Selective breeding of herds, mounts and hounds | 46.2, 46.4, 46.6 |
| 2 | Grafting, orchards and landraces | 46.2, 46.4 |
| 3 | Living bridges and shaped trees | 46.5 |
| 4 | Seed banks of temples and states | 46.3 |

### 46.22 Couplings, loops and acceptance stories (W46)

**Couplings.**

| Id | From | To | Carrier |
|---|---|---|---|
| C35 | Living craft | Agrarian | yields, tolerance, seed control |
| C36 | Living craft | Ecology | escapes, invasive lines, gene flow |
| C37 | Living craft | Disease | monoculture risk, designed disease, blights |
| C38 | Living craft | Body | grown organs, longevity, shaping |
| C39 | Living craft | War | living units, designed soldiers |
| C40 | Living craft | Economy | living production, feed demand, line rights |
| C41 | Living craft | Mind and law | clones, designed peoples, symbiont co-minds |

**Loops.**

| Id | Type | Loop | Brake or accelerator |
|---|---|---|---|
| L96 | R | Designed high-yield line → monoculture → blight → famine → demand for a new line → monoculture | diversity laws, gene banks |
| L97 | B | Escaped line → invasive spread → native decline → controls and hunts → line contained | drift |
| L98 | R | Seed monopoly → dependence → owner influence → laws favouring the owner → deeper monopoly | intrusion leaks, movements |
| L99 | B | Designed disease → escape → blowback on makers → treaties → fewer designed diseases | secrecy (F53) |
| L100 | R | Living city growth → feed demand → expanded farms → more feed → more growth | land limits, blights |

**Acceptance stories.**

1. **AS40 The Blighted Line.** A polity spreads a designed staple to all its regions; a blight strikes the line; famine follows; a neighbour with a gene bank sells an old landrace at a high price; a diversity law follows.
2. **AS41 The Ship That Turned.** A living vessel neglected by a new captain loses its bond; it refuses a route, then flees with part of the crew; it breeds in a wild system, and its line becomes a wild species of the void.
3. **AS42 The Clone Heir.** A ruler raises a clone heir under `licensed` clone law with `ward` status; the ruler dies; factions dispute the heir's standing; the court rules by `copy_succession`; a clone movement forms.
4. **AS43 The Partner Line.** A people bonded to a symbiont line loses it to a blight; their identity and skills collapse; they migrate to the last region where the line survives, causing a war.

### 46.23 Compliance catalogue (W46)

| Section | Tables | Phase | God levers | Screens | Tools and context | Codex and book | Integrity | Backfill |
|---|---|---|---|---|---|---|---|---|
| F54 / 46.1 profiles | `living_profiles` | `living` | `living:create/edit/delete/hold` | "Living" block in made-thing drawers; "Living" in `ThingSections` for entities that are made things (others hold life in their body and species sections; the reason is shown) | context `living_craft` | "Living" in entries | stage valid; feed commodity exists | bioships, grown structures and vat food production gain profiles |
| 46.2–46.3 lines and design | `living_lines`, `living_line_sources`, `living_line_traits`, `gene_banks`, `gene_bank_samples` | `living` | `line:create/edit/delete/hold`, `bank:*`, `sample:*` | mechanic panel "Living craft" with line browser, design view and lineage | mortal `breed_line`, `design_line`, `bank_sample`; son `bless_line`, `curse_line`; context `living_lines` | line entries in Records; banks in holder entries | sources exist; trait caps | domesticated species and breeding designs become lines of method `selective_breeding` |
| 46.4 crops and herds | line links on agrarian rows | `agrarian` | agrarian levers with line choice | agrarian panel "Lines" | mortal `plant_line`, `raise_line` | region entries | — | landraces as lines |
| 46.5–46.7 grown things | profiles on structures, vehicles, equipment | `living`, `structures`, `vehicles` | as profiles | drawers | mortal `grow_structure`, `grow_vessel`, `grow_gear` | entries | — | — |
| 46.8–46.9 bodies, clones | augments of make grown, clone bonds, laws | `body`, `living` | `augment:*`, `clone:create`, law levers | Body section; lineage | mortal `grow_organ`, `clone`; ruler `set_clone_law` | entries | clone has source genome | — |
| 46.10 symbionts | symbiont line columns, host rows | `living`, `mind` | `symbiont:host/remove` | Body section "Symbionts" | mortal `host_symbiont`, `remove_symbiont` | entries | host has a body | — |
| 46.11 disease | disease designed columns | `epidemics` | disease levers | disease panel | mortal `design_disease`, `design_cure` | disease entries | — | — |
| 46.12 production | method family `living` | `industry` | method levers | industry panel | mortal `found_living_works` | entries | — | vat food and vertical farms |
| 46.16 escapes | escape history | `ecology` | `line:escape`, `line:contain` | ecology panel | — | entries | — | — |
| 46.17 law and faith | law kinds, doctrine columns | `polity`, `faith` | law and doctrine levers | panels | ruler, son tools | entries | — | stances from doctrine values |
| 46.13 links and computation | networks with carrier `grown_link`, grown seats | `networks`, `living`, `minds` | network and mind levers | network drawer, Mind section | as F51, F50 | entries | — | — |
| 46.14 world shaping | ecology programmes, released lines | `ecology`, `climate`, `living` | `programme:*`, line levers | world "Living craft" | mortal `release_line`; son `bless_line` | world entries | — | terraformers on living worlds |
| 46.15 designed sapience | people origin `designed` | `population`, `living` | people levers | people drawer | mortal `raise_sapience` | people entries | — | uplifted peoples keep origin `uplifted` |
| 46.18 economy | line rights, licences, live cargo | `market`, `trade` | `pattern:*` | Economy "Lines and rights" | mortal `license_line` | Records table | — | — |
| 46.19 war | living unit stats, designed soldiers | `warfare` | unit type levers | war panel | army tools | entries | — | — |
| 46.20 gods | natural laws, line blessings and curses | `divine`, `living` | natural law and line levers | son drawer | son `bless_line`, `curse_line`, `set_natural_law` | entries | — | — |

**Phases.** `living` (production stage, after agrarian and before industry), extensions in ecology, epidemics, body and structures.

**Rule namespaces.** `living`, `living_methods`, `genome_design`, `clones`, `symbionts`, `designed_disease`, `living_production`.

---

## Part 5. Integration across W44–W46

### 5.0 Paths in every kind of world

Every major mechanic of these waves can be reached by more than one path, so it fits any era and any balance of magic and making. The path sets prerequisites, costs, failure modes and what can break it; the result is the same typed state.

| Mechanic | Technique path | Rite path | Living path | Power path | Divine path |
|---|---|---|---|---|---|
| Make a mind | computation, construct making | `create` × `mind` with a bound seat; summoning into a seat | grown nervous tissue (46.13) | — | `grant_mind` |
| Save or copy a mind | mind recording | `bind` × `spirit` into a vessel | memory held in grown tissue | `transform` × `mind` onto a store | god holds the state |
| Transfer a mind | mind transfer technique | `transform` × `spirit` | grown body as target | `possess`, `project_self` | divine act |
| Augment a body | augment making, surgery | rite-bound part (enchanted) | grown organ or symbiont | — | divine mark or gift |
| Network | relay, wired, broadcast, mesh techniques | `rite_link` | `grown_link` | `mind_link` | blessed network |
| Intrusion | computing, electronics | `rite` approach against wards | — | `power` approach | divine revelation |
| Surveillance | sensors, data stores | scrying (`perceive`) | living sensors | mind reading in state service | omniscience within dominion |
| Self-making | replicator techniques | self-copying constructs (F56 `replicate` order) | breeding lines with fast fertility | — | divine multiplication |
| Abundance | fabrication | goods made by rite | living production | — | blessing on a people |
| Made realm | computation hosts | a realm held by a working | a realm held in a living organism | a realm held in a mind | a realm held by a god |
| Foresight | modelling by made oracles | divination rites | — | `foresee` | prophecy |
| Hide a truth | records control, memory edits | memory removal by rite | — | mind edits | divine concealment |
| Design a life | engineering, synthesis | shaping by rite | breeding, cultivation | `transform` × body | divine creation of a species |
| Clone | cloning technique | `create` × body from a sample | budding lines | — | divine copy |
| Longevity | organ and cell renewal | longevity rites (existing) | symbionts, renewal lines | `renew` | divine gift |

### 5.1 Every kind of thing

Per-thing sections go into `frontend/src/features/entity/sections/ThingSections.tsx`, which every node drawer page renders. A section that applies to some kinds only states why the others cannot have it, on screen and here.

| Section | Creator | Son | Foreign god | World | Star | Every entity type |
|---|---|---|---|---|---|---|
| Mind (F50) | yes: seat `divine`, editable only by the god's own levers | yes: seat `divine`; avatars hold made or grown seats | yes: seat `divine` | yes: a world can hold a mind (seat `place`) | yes: a star can hold a mind (seat `place`) | yes: every entity type; things without a mind show seat `none` with the control to give one |
| Powers (45.4) | yes: divine powers beside innate powers | yes | yes | yes | yes | yes |
| Augments (44.9) | through avatars | through avatars | through avatars | through megastructures (structures already exist) and shown as a link | through megastructures | entities with a body (mortals, beasts, spirits in possessed bodies, cosmic beings); for the other types the section shows that they have no body and links to what stands in for one |
| Living (F54) | — reason: not a made thing | — | — | worlds of type `living` show their own life through Mind and the world sections | — | made things and designed species and peoples |
| Orders (F56) | — reason: gods are not instructed | binding by oath only | binding by oath only | worlds can hold instructed guardians (shown as members) | — | instructed things |
| Relic (F55) | — | — | — | — | — | made things |
| Hidden truths (F53) | as subject | as subject and keeper | as subject and keeper | as subject and scope | as subject | as subject, keeper and scope |
| Networks (F51) | as owner | as owner | as owner | as member and scope | as member (system networks) | as member and owner |
| Sources (F52) | — | as patron source | as patron source | as scope (world sources and density) | as sky source | regions show density; patron entities show sources they give |

`scripts/check_wiring.py` gains the new sections in its node-kind checks, and `scripts/check_shared_labels.py` rules apply to every field label (no bare 'Name', 'Kind' or 'Type').

### 5.2 Genesis wizard and templates

**Settings added to `GenesisSettings`** (each may be null: the seed decides):

| Setting | Range | Effect |
|---|---|---|
| `made_minds` | 0–100 | starting prevalence of made minds and the `made_minds` natural law (0 sets will to `none` for made seats) |
| `innate_powers` | 0–100 | prevalence of innate systems and the gifted share; independent of the magic slider, so a world without magic can have innate powers |
| `concealment` | 0–100 | starting hidden truths: at 0 none; above 0 the genesis output may create them from the seed |
| `living_craft` | 0–100 | starting living methods and lines |
| `information_reach` | 0–100 | starting networks, from relay chains to world networks, read with technology |

**Genesis output added:** `magic_systems` (systems with typed structure, sources with typed axes, names and descriptions written from the seed), `sources` (authored sources), `hidden_truths` (only when concealment is above 0 or the seed asks), `starting_lines` and `starting_networks` (typed).

**Templates added** (`catalog/genesis.py`; seeds name the premise only; every typed value not listed is `seed`):

| Template | Key | Made minds | Innate powers | Concealment | Living craft | Seed |
|---|---|---|---|---|---|---|
| Made minds | `made_minds` | 70 | seed | seed | seed | A world where minds are made as well as born. |
| Inborn powers | `inborn_powers` | seed | 70 | seed | seed | A world where some are born with powers of their own. |
| Hidden world | `hidden_world` | seed | seed | 70 | seed | A world where some of its peoples and powers are hidden from the rest. |
| Grown world | `grown_world` | seed | seed | seed | 80 | A world whose peoples grow what others build. |
| After abundance | `after_abundance` | seed | seed | seed | seed | A world that once made everything it needed and has lost the means. |

The wizard groups these as separate titled steps (memory rule: structure every choice): "Minds", "Powers and their sources", "What is hidden", "Living craft", each with "The seed decides", previews of their typed effects and disabled states with reasons (a step that cannot apply shows why).

### 5.3 LLM layer and prompt-bias gates

**Context blocks** (typed, `agents/context/*`): `mind_seat`, `made_minds`, `made_realms`, `networks`, `intrusion`, `surveillance`, `information`, `abundance`, `relics`, `replicators`, `augments`, `sources`, `magic_systems`, `powers`, `foresights`, `hidden_truths` (only what the acting agent knows), `living_craft`, `living_lines`. Each block lists typed values with labels, never prose summaries, and respects the context budget (K.15).

**Tools.** Every tool named in the compliance catalogues has a schema in `prompts/schemas`, a description in `prompts/` that says what each field holds without examples, enum lists that list every value (`test_tool_enum_lists.py`), a case in `every_son_tool.py` or `every_mortal_tool.py`, and a catalogue description (`test_catalogue.py`).

**Prompt templates touched.** Genesis, awakening, deepening, chronicle templates and agent turn templates gain the new blocks. Every touched template is read in full and rewritten where it pushes a theme, tone, conflict, gender or look the seed did not ask for (rule 2).

**New `check_prompt_bias.py` families**, each with cases in `test_prompt_bias_rules.py`:

| Family | Catches in our LLM-facing and UI text |
|---|---|
| `made_mind_persona` | default temperaments for made minds (cold, emotionless, purely logical, servile, hostile, longing to be alive) |
| `made_mind_uprising` | mandated or implied rebellion or takeover of made minds |
| `tech_imagery` | genre-steering images of information-age settings in our text |
| `power_imagery` | genre-steering images of innate powers in our text |
| `power_price_mandate` | rules that every power or magic must carry a price or a cost to the user |
| `concealment_mandate` | rules that every world hides something or that secrets must exist |
| `concealment_imagery` | genre-steering images of hidden worlds in our text |
| `living_craft_imagery` | genre-steering images of living technology in our text |
| `abundance_tone` | built-in utopian or dystopian framing of abundance |
| `designed_being_gender` | gendered defaults for made minds, clones and designed beings |

### 5.4 Codex and lore book

- **Node entries** (`services/books/typed.py`) render, for every kind of node: "Mind" (seat, origin, will, affect, purpose, capacity, speed, stability, upkeep, copies and states with holders, lineage), "Powers" (system, source, grammar pair, strength, control, state, origin, restrictions), "Augments" (slot, kind, make, quality, integration, strain, upkeep), "Living" (line, metabolism, stage, health, fertility, bond), "Orders" (binding, token, orders), "Relic" (make knowledge, state, understanding, use), "Hidden truths" (kind, hidden from, strength, keepers, knowledge by population, labelled as the god's view), "Connections" (networks and roles).
- **Network entries** (a new entity type) render profile, members table, gateways, outages history and owner.
- **World entries** render "Sources of power" (sources with every axis labelled, density by region, tides, interactions) and "Magic systems".
- **Made realm entries** (dimensions of kind `made`) render host, keeper, purpose, time ratio, entry, awareness, upkeep and the realm's own natural laws.
- **Records of the Cosmos** appendix gains designed tables: Intrusions, Breaches, Seekers, Source knowledge by people, Foresights, Replicator lines and presence, Pattern rights, Living lines, Gene banks, Mind archives, Relics, Network outages. Nothing is truncated.
- **Layouts.** Lineage of minds and living lines render as indented trees in the book (HTML/PDF) and as nested lists in the Codex (Markdown); sources render as labelled cards; hidden truths as a table with a "hidden from" column.
- `check_wiring.py` confirms every new table renders or is kept out of the generic records by a dedicated renderer.

### 5.5 Screens, atlas and visuals

- **Drawer sections** (5.1) built from `components/ui` and `components/domain`, with medallions and icons per value, editable values through levers, loading, empty, error and disabled states with reasons, show-more paging, phone width, both themes and accessibility labels.
- **Mechanic panels:** "Made realms", "Self-making machines", "Abundance", "Sources of power", "Magic systems", "Hidden truths", "Living craft", "Foresights", "Surveillance and privacy", each in the style of the existing control panels.
- **Atlas layers:** "Networks" (lines and hubs, carrier by icon), "Replicator spread", "Source density" (per source), "Hidden places", "Living lines" (where lines grow and where they escaped).
- **New node kind `network`:** icon, medallion, atlas entry, wiki page, drawer page rendering `ThingSections`, obvious create and manage controls (memory rule: new scales need visuals).
- **Graphs:** lineage of minds (copies, merges, transfers, restores over time), living line lineage, network graph.
- **Gamification:** awakening, revelation, line creation and network founding are rewarded moments with feedback and progress; the god's control over minds, powers and life is shown as power.
- **Existing controls stay visible** (memory rule: never hide existing controls); screenshots of every new and touched screen in both themes and at phone width are taken and opened before each wave is called done.

### 5.6 Integrity checks

Added to the integrity system and run each epoch:

1. A mind has exactly one running seat, or several only for seat `bodies`; every seat ref exists.
2. A copy's fidelity is at most its source's; lineage bonds are acyclic in time.
3. Every saved state has a holder and an owner that exist.
4. Network nodes and gateways reference existing members and networks.
5. Every power references an existing system and source; every source has a scope and cost rows.
6. Hidden truth scopes and keepers exist; percentages lie in 0–100.
7. Every living profile references an existing line; lines reference existing source organisms.
8. Replicator presence masses are non-negative; stages follow their order unless set by a lever.
9. Instruction tokens and targets exist or are marked lapsed.
10. Augment slots are valid for the bearer's body plan.
11. Every made realm has an existing host and keeper; minds with seat `realm` live in a made dimension.
12. Every seeker references an existing truth and seeker node.

### 5.7 Legacy mapping and backfills

Each wave's first epoch after upgrade runs recorded fixups (`AppliedFixupRow`), "as if it had always been so":

- **W44:** every node gets a mind profile from its type (born mortals `body/born/full/felt`; beasts by intelligence; spirits `none` with origin `summoned` or their bound seat; living worlds `place/awakened`; gods `divine`); constructs and guardians get instruction sets from their creature and structure rows; prostheses become `replacement` augments and neural implants `interface` augments; signal chains and post routes become relay networks; `ai_core` structures get a steward mind where the world's law allows will, otherwise a tool mind; items and structures above their holders' knowledge become relics; terraformers become terraforming replicator lines only where the world holds self-making techniques, otherwise they stay works; vat food and vertical farms gain fabrication or living methods; merchant factions with charters get company profiles; the W42 machine law levels map to the new levels.
- **W45:** the six `MagicSource` values become built-in source rows; ley density becomes source density; each world gets one magic system from its magic level and rites; gifted mortals with high aptitude get latent powers of origin `born`; hive-minded peoples get their gestalt; true history secrets become hidden truths of kind `event`; legacy cosmic leak truths become hidden truths of kind `cosmic`.
- **W46:** domesticated species and breeding designs become lines of method `selective_breeding`; landraces become lines; bioships, grown structures and vat food production gain living profiles; cloning facilities gain the cloning method.
- **Legacy importer** (`migration/legacy/importers/*`) maps any legacy flags that touch these concepts once.

### 5.8 Engine placement and performance

- Phases: `networks`, `minds`, `replicators`, `relics` (W44); `magic` extended and `concealment` (W45); `living` (W46). Each is placed in the pipeline stage named in its catalogue and registered in `engine/pipeline.py`.
- Every phase batches its reads per epoch (one query per table per phase, no per-row queries), uses `held()` or `unheld()` from `aerona.db.write_guard` where it chooses whom to act on, and draws from its own seeded stream.
- Growth processes (replicators, living lines, networks, knowledge spread) are computed per region in vectorised passes; lineage graphs are built once per epoch for the book and API.

### 5.9 Testing and proving gates

Per CLAUDE.md rule 1, each step runs the static gates and the tests that cover it. The commit gate runs the proving gate. For these waves:

- **Tools:** a success case for every new son and mortal tool in `every_son_tool.py` / `every_mortal_tool.py`.
- **Levers:** every new lever in `every_lever.py`, one run per branch value, `EDITS` with real values for every editor lever.
- **God control:** `test_god_control.py` stirs the rich cosmos with made minds (every seat), a made realm with inhabitants, seekers, saved states, copies, augments, networks, intrusions, replicators at every stage, abundance, relics, sources, systems, powers in every state, gestalts, foresights, hidden truths with keepers, living lines of every method, symbionts, clones and designed disease; held nodes stay untouched, forced nodes run cleanly.
- **Eager epochs:** `test_eager_epochs.py` lives the stirred cosmos five epochs with every chance certain.
- **Acceptance stories AS31–AS44:** seeded multi-epoch runs with the model off, each asserting its chain of typed incidents.
- **Endpoints and types:** every new read endpoint in `test_every_endpoint.py`; frontend types regenerated; every served field read by a screen (`test_frontend_reads_every_field.py`).
- **Prompt bias:** cases for every new family.
- **Defects found during integration** close their class (rule 8).

### 5.10 Coverage and completion contract

- Step 0 of W44 extends `scripts/spec_coverage.py` to read this file (foundations F50–F56, sections 44.x, 45.x, 46.x, reference lanes, couplings, loops, stories, decisions) and to write `docs/spec/16-coverage.md` with the columns of `13-coverage.md`; the commit gate checks both matrices.
- A row is done only when every work column is filled (or `n/a` where it does not apply) and its tests pass. `deferred-approved` needs the user's explicit approval.
- A wave is done when every row of the wave is done, its audit has been run against this spec, screenshots have been taken and opened, and it is committed, pushed and deployed.

### 5.11 Execution order inside each wave

**W44:** coverage step → F50 mind seats and bonds → F56 instructions → F51 networks (entity type, visuals) → 44.2–44.5 making, awakening, will, inner life → 44.6–44.7 law, faith, souls → 44.8 continuity → 44.9–44.10 augments and interfaces → 44.10a made realms → 44.11–44.14 networks in society, intrusion, surveillance, information → 44.15 companies → 44.16 replicators → 44.17 abundance → F55 and 44.18 relics, collapse, salvage → 44.19–44.21 made peoples, war, archives → genesis, prompts, book, Codex, screens → fixups → audit.

**W45:** F52 sources and tides → 45.1 systems → 45.3 grammar → 45.4–45.7 powers, awakening, training, devices → 45.8–45.11 gestalts, foresight, mind and outward powers → 45.12–45.15 society, exposure, war, gods → F53 and 45.16–45.17 concealment → genesis, prompts, book, Codex, screens → fixups → audit.

**W46:** F54 profiles and lines → 46.2–46.3 methods and design → 46.4–46.7 crops, structures, vessels, gear → 46.8–46.10 bodies, clones, symbionts → 46.11–46.13 medicine and disease, production, links and computation → 46.14–46.16 world shaping, designed sapience, escape and decay → 46.17–46.20 law, faith, economy, war, gods → genesis, prompts, book, Codex, screens → fixups → audit.

**W47:** step 0 audit of built sections against 47.8 → guards (`check_acts_as.py`, enum scan, `check_enum_values_read.py`, `check_spec_depth.py`) written first so they list every gap → 47.1 structures → 47.2 eras, energy, medicine, logistics, signals, extraction → 47.3 crime, punishment, trial, unions, taxes, revolts → 47.4 sweep → 47.5 god layer → 47.6 typed models and renames → 47.7 unread values → 47.8 thin sections → 47.10 mishaps, fortune and drawn harm → screens, Codex, book, prompts → fixups → audit with every guard at zero.

**W48:** `catalog/concepts.py` and both guards first (they list every gap) → F57 machinery → 48.1 goods → 48.2 food, cuisine, drink → 48.3 dress, colour, scent, emblems → 48.4 household goods, tools, instruments, games, substances → 48.5 money, materials, preservation, species products, production methods → 48.6 society → 48.7 culture → 48.8 nature and cosmos → 48.9 unification → 48.10 property catalogues for all 250 → genesis, Kinds library, Ways of life, Codex, book, prompts → fixups → audit with both guards at zero.

Each wave follows the build-all-then-gate-once working rule: the whole wave is written, then gated and committed once.

### 5.12 Decisions

Decided on 2026-11-14: the user delegated these decisions to Claude, to be set for the balance of the engine. They bind integration; the god can still change every value in play through levers.

| Id | Question | Decision |
|---|---|---|
| K.21 | Can made minds have will? | A world natural law `made_minds` (`no_will`, `instructed_only`, `will_may_emerge`, `will_by_make`). The seed or genesis setting decides; when both are silent, `will_may_emerge`, which allows will without forcing it. |
| K.22 | Do made minds have souls? | Natural law `made_mind_souls`; when the seed is silent, `granted`: only a god's act gives a soul, so the god decides. |
| K.23 | Where does a soul go on copy, transfer or restore? | Natural law `soul_continuity`; when the seed is silent, `stays_with_first`. |
| K.24 | Who is the person when copies exist? | Polity law `copy_succession`, chosen by the polity's values; when unset, `first_only`. |
| K.25 | How far can runaway self-making go? | Stage-gated by 0.8: region, then world, each stage visible; never a cosmic end except through the doom clock. |
| K.26 | How does foresight keep one timeline? | Foresights are typed probabilities acted on through prophecy mechanics; they never rewrite history. |
| K.27 | Does every world hide something? | No. Hidden truths exist only when the seed, history or levers create them. |
| K.28 | Can worlds author new power sources? | Yes: genesis and sons author sources with typed axes; the six legacy sources remain as built-in rows. |
| K.29 | How is designed disease aimed at a people handled? | Narrated plainly and behind closed doors (G9), bound by scale gating and visible escalation, and read by ethics, law, treaties and every relation of the victims. |
| K.30 | Do germline edits spread? | Yes: germline traits enter genetics and spread by inheritance; laws and doctrine regulate them. |
| K.31 | Can a world or the cosmos be a made realm? | Only when the seed, the genesis output or a god's act says so; it is then a hidden truth with its own knowledge and breaches, never a default. |
| K.32 | May the engine punish minds by dormancy, edits or erasure? | Yes, only where a polity's law names the punishment, weighed by the people's mercy and narrated plainly (G9). |

### 5.12a Balance bands

The new mechanics join the balance bands of `docs/spec/13-balance-bands.json`, checked by `scripts/balance_sim.py` (100 epochs, model off, seeded rich cosmos) and `backend/tests/engine/integration/test_balance_bands.py`. Every rule default of W44–W47 is tuned until the stirred cosmos sits inside these bands; a change that pushes a metric out fails the balance test.

| Metric | Low | High | Meaning |
|---|---|---|---|
| `mishap_death_share_pct` | 2 | 12 | everyday mishaps are a real cause of death among named mortals, never the main one |
| `mishap_maiming_share_pct` | 5 | 30 | mishaps maim, while war, beasts and disasters stay the main source of the maimed |
| `notable_mishaps_per_epoch` | 0 | 2 | a ruler's, heir's or hero's fall happens, rarely |
| `accidental_deaths_per_1000_per_year` | 0.2 | 5 | accidents show in every population without becoming a plague |
| `fortune_streak_abs_mean` | 0 | 15 | personal streaks stay small against causes |
| `awakenings_per_epoch` | 0 | 2 | where will may emerge and minds are made, waking is an event, not a flood |
| `copies_per_made_mind_mean` | 0 | 3 | copying stays an act with weight |
| `major_outages_per_epoch` | 0 | 3 | networks fail sometimes and recover |
| `runaway_lines_share_pct` | 0 | 10 | most self-making lines stay contained |
| `worlds_consumed_outside_doom` | 0 | 0 | no world ends by runaway, plague or mind outside the doom clock |
| `breaches_per_truth_per_epoch` | 0 | 0.5 | hidden truths leak slowly |
| `revelations_per_100_epochs` | 0 | 5 | revelations are era events |
| `depleted_region_share_pct` | 0 | 25 | sources thin in places, not everywhere |
| `burned_out_share_pct` | 0 | 20 | strain bites without ending most users' powers |
| `line_escapes_per_epoch` | 0 | 2 | designed life gets loose sometimes |
| `designed_outbreaks_per_100_epochs` | 0 | 3 | designed disease stays rare |
| `divine_wars_per_100_epochs` | 0 | 3 | the council's failures are rare and grave |
| `structures_with_own_effects_pct` | 100 | 100 | every structure acts in its own right (47.1) |

### 5.13 Techniques, skills and roles

**Techniques** (8.4 knowledge graph; each with prerequisites, boosts and, where the rule of 8.4b says so, a correct theory):

- W44: `mechanical_computation`, `electronic_computation`, `machine_learning` (training of made minds), `mind_recording`, `mind_transfer`, `neural_interface`, `augment_making`, `relay_networks`, `wired_networks`, `broadcast_networks`, `mesh_networks`, `ciphers_of_machines`, `surveillance_systems`, `fabrication`, `self_making`, `minute_machines`, `made_realms`.
- W45: `power_testing`, `power_training`, `dampening`, `amplification`, `mind_linking`, `source_theory` (theories of sources raise predictability for their holders).
- W46: `selective_breeding` (existing domestication extended), `cultivation`, `shaping`, `genome_reading`, `genome_engineering`, `synthesis_of_life`, `cloning`, `symbiont_binding`, `living_production`, `gene_banking`, `designed_ecology`.

Rites cover the rite paths of 5.0 through the widened grammar; a world can reach the same mechanic by either list.

**Skills added to `SkillKind`:** `husbandry`, `horticulture`, `genetics`, `discipline` (control of innate powers), `investigation`. Existing skills used: `computing`, `electronics`, `mechanics`, `science`, `surgery`, `medicine`, `cryptography`, `spellcraft`, `ritual`, `spirit_speaking`, `beast_handling`, `engineering`, `alchemy`, `intrigue`, `deception`.

**Roles and professions:** maker of minds, augment surgeon, network keeper, intruder, data broker, salvager, relic keeper, breeder, shaper, line engineer, gene banker, trained gifted, registry officer, keeper of a hidden truth, seeker. Each is a mortal role or profession built on the skills above (W42 role machinery) and offered to notable births and careers.

### 5.14 New and widened enums

**New enums.** `MindSeat`, `MindOrigin`, `MindWill`, `MindAffect`, `MindPurpose`, `MindUpkeep`, `MindMaking`, `StateMedium`, `NetworkCarrier`, `NetworkAccess`, `NodeRole`, `SourceLocus`, `PowerCost`, `SourceRenewal`, `SourceAccess`, `ResistanceKind`, `PowerVisibility`, `PowerHazard`, `SourceRelation`, `PowerStructure`, `Learnability`, `PowerOrigin`, `PowerState`, `RestrictionKind`, `PowerDeviceEffect`, `HiddenTruthKind`, `ConcealScope`, `KeeperRole`, `SeekerAim`, `TruthAttitude`, `BreachCause`, `Metabolism`, `GrowthStage`, `Fertility`, `CultivationMethod`, `HostPlacement`, `HostRelation`, `RelicState`, `RelicUse`, `BindingKind`, `CommandToken`, `OrderKind`, `OrderCondition`, `AugmentSlot`, `AugmentKind`, `AugmentMake`, `IntrusionTarget`, `IntrusionApproach`, `IntrusionAim`, `Attribution`, `Authenticity`, `SurveillanceFocus`, `CompanyCharter`, `ReplicatorScale`, `ReplicatorOutput`, `ReplicatorStage`, `RealmPurpose`, `RealmEntry`, `RealmAwareness`, `GiftedAttitude`. Their values are the ones listed where each is defined.

**Widened enums.** `EntityType` (`network`), `DimensionKind` (`made`), `EnergyKind` (`electric`, `stored`, `source`, `feed`), `Medium` (`network`, `mind_link`), `SpellForm` (`space`, `force`, `sound`, `emotion`, `fate`, `machine`, `information`), `SpellTechnique` (`drain`, `mimic`), `RiteEffectKind` (the effects of 45.3), `SkillKind` (5.13), `LawKind` (`mind_status`, `copy_law`, `copy_succession`, `erasure_law`, `augment_law`, `network_law`, `surveillance_law`, `provision_law`, `power_law`, `source_law`, `living_craft_law`, `clone_law`, `clone_status`, `germline_law`, `designed_status`), `FactionKind` (`company`, shared with 4.3), `GatheringKind` (`testing`), `StructureKind` (`bioreactor`, `gene_bank`, `mind_archive`, `dampening_ward`, `breeding_works`), equipment family (`focus`), production method family (`fabrication`, `living`), bond kinds (F50.4), identity facets (`made`, `augmented`, `gifted`, `designed`), language modality (`data`, `mind`, `chemical`).

Every new and widened enum gets frontend labels and icons for every value (`check_label_maps.py`), its generated `…Values` constant, total tables or declared omissions (`test_total_tables.py`), and full lists in every tool text that lists it (`test_tool_enum_lists.py`). No JSON column claims to hold these enums (`test_json_enum_columns.py`).

### 5.15 API and the action catalog

- **Read endpoints** (each with a schema name of its own, `test_unique_schema_names.py`): the mind of a node and its lineage; saved states of a node; networks list and network detail; intrusions; data stores of a holder; surveillance of a polity; trust and knowledge of a people; companies; replicator lines and presence; abundance by market; pattern and line rights; relics; made realms; sources, density, tides and interactions of a world; magic systems of a world; powers of a node; foresights; hidden truths, keepers, seekers, knowledge and breaches (the god's view); living profiles of a node; living lines and their lineage; gene banks; augments of a node.
- **Every write** goes through the action runner as a registered lever in the action catalog (`services/player/catalog.py`) with ledger undo, reached from a frontend caller (`check_wiring.py`), and proven by `test_every_lever.py`.
- Generated frontend types are refreshed in the same change (`test_frontend_types.py`), and every served field is read by a screen.

### 5.16 Incidents and chronicle templates

New incident kinds (F10), each with an English chronicle template family localised at epoch end (decision 71). Templates state what happened in plain words from typed fields; they carry no images and no tone (rule 2).

| Family | Incidents |
|---|---|
| `mind.*` | made, awakened, will changed, copied, saved, restored, transferred, merged, divided, freed, bound, edited, lost seat, ended, departed, exceeded |
| `augment.*` | installed, rejected, failed, seized, removed |
| `network.*` | founded, joined, gateway opened, outage, restored, seized |
| `intrusion.*` | detected, attributed, secrets taken, records altered, control seized, extortion |
| `information.*` | record forged, forgery exposed, leak, censorship, trust collapse |
| `company.*` | founded, chartered, enclave taken, became a polity |
| `replicator.*` | built, drifted, stage changed, contained, stopped, extinct |
| `abundance.*` | price floor reached, provision law changed, pattern leaked |
| `collapse.*` | collapse, relic found, relic revered, technique recovered |
| `realm.*` | built, entered, withdrawal, frozen, ended, confinement, escape |
| `source.*` | discovered, depleted, born, died, tide turned |
| `power.*` | awakened, wild manifestation, burned out, granted, revoked, registered, conscripted |
| `gestalt.*` | linked, broken |
| `foresight.*` | foreseen, fulfilled, failed |
| `truth.*` | breach, cover-up, revealed, forgotten, seeker succeeded |
| `line.*` | designed, released, escaped, drifted, blighted, raised again |
| `clone.*` | made, recognised, disputed |
| `symbiont.*` | hosted, removed, took control |
| `disease.*` | designed, escaped, struck its makers |

### 5.17 Who acts, and why

Every mechanic runs on its own (G4). The engine actors and the typed drivers of their choices:

| Actor | Choices | Drivers |
|---|---|---|
| Polities | laws (mind status, copies, augments, networks, surveillance, provision, powers, sources, living craft, clones), programmes (made minds, networks, realms, replicators, ecologies), registries, provision, wars over sources and fabricators | values, ruler traits, selectorate, pressures, classes, doctrine, threats, incidents |
| Factions and companies | enclaves, fabricators, patterns, lines, intrusion, lobbying, private forces, keeping or seeking truths | profit and influence needs, members' values, rivals |
| Cults and orders | doctrine stances, source taboos, keeping truths, training the gifted, revering relics | doctrine, the son's domains and acts, persecution memories |
| Mortals | aspirations (F17) of new kinds: `outlive_the_body` (save, transfer, renew), `free_the_minds`, `master_a_power`, `expose_a_truth`, `keep_a_truth`, `make_a_line`, `remake_the_self` (augments, shaping), `build_a_network`, `found_a_company`; choices of careers and roles of 5.13 | values, needs, skills, opportunities, memories |
| Made minds | upkeep, continuity, autonomy, purpose, relations with makers, departure, copying themselves, building realms | their needs and values from F50 and 44.5 |
| Hidden peoples | passing, accords, recruitment, retreat into hidden places, revelation by choice | safety, numbers, attitudes around them |
| Sons and foreign gods | goals of new kinds: wake or still minds, bless or forbid making, grant or revoke powers, shape sources and systems, keep or reveal truths, bless or curse lines | domains, standing, desperation, the council, the Creator's will |

Choice weights are rules (G1) read through needs, values and pressures, with decision biases (F40) when built.

### 5.18 Diplomacy and justice

- **Treaty clauses added:** bans on autonomous weapons, mind seizure, copying of captives, replicator weapons, designed disease, network attacks on civil systems and powers in war; data sharing; extradition of minds and states; recognition of made minds' and clones' status; line licensing; source sharing in border regions; accords of hidden peoples.
- **Crimes added:** mind theft, unlicensed making or copying, forced edit, erasure as the law names it, impersonation by copy or generated likeness, intrusion, extortion, forgery of records, unlicensed augment, unlicensed power use, compulsion, disclosure of a hidden truth where law punishes it, unlicensed line, release of a line, designed disease, organ taking from clones.
- **Punishments added:** 44.6.5.

### 5.19 Storyteller and pacing

The storyteller (F27) treats awakenings, breaches, revelations, outages, runaway stages, wild manifestations, source depletions and line escapes as disruptions with typed tension weights. In low-tension spans it raises their chances within rule bounds; in high-tension spans it lowers them. It never creates one of these events without its typed causes, and it never forces a kind of event a world's laws exclude.

### 5.20 Names, prose and images

- **Names** of made minds, networks, companies, lines, sources, systems, realms and hidden peoples are generated by the language engine from the tongue of their maker, owner or discoverer; a made mind with full will can choose its own name; naming customs are typed per culture, never one style for a concept.
- **Prose** for every new entity and record is written by the deepener from typed fields and the world's own canon.
- **Images** for networks, made minds, augments, living craft, realms and powers are directed from typed fields (seat, carrier, make, line traits, purpose) and the world's canon; image style is applied at render time; no medium or look is hardcoded.

### 5.21 Migrations

Each wave has one alembic migration that creates its tables, widens the enum columns it touches and adds its columns, followed by its recorded fixups (5.7). `npm run typegen` runs in the same change. The migration and fixups are idempotent on existing worlds and on fresh genesis.

---

## Part 6. Completeness sweep

Every concept the user asked for, and every neighbouring concept found while researching, mapped to where it lives. "Existing" names systems already built; everything else is in this spec.

### 6.1 By genre

| Genre | Concepts | Where |
|---|---|---|
| Ancient and mythic | god-given minds in places and objects; oracles; seed banks of temples; selective breeding; relics of an elder making; vows that give power | F50 (`granted`, `place`), 44.1, 46.3, 46.2, F55, 45.15 |
| Classic fantasy | golems and constructs; familiars and bonded beasts; born mages beside learned rites; places of power and their depletion; hidden folk | F56, 46.6, 45.4, F52.2, F53 |
| Dark fantasy and horror | phylacteries and undeath as seats; parasites that steer hosts; knowledge that harms; designed plagues; costs in sanity, memory, lifespan | 44.8.9, 46.10, F53 sanity cost, 46.11, F52 costs |
| Urban fantasy | hidden peoples among cities; memory removal of witnesses; accords; passing; revelation | F53, 45.16, 45.17 |
| Superhero | born, exposure and made powers; secret identities; bands and rivals without quotas; registries; vigilantes | 45.4, 45.12, 45.13 |
| Steampunk and industrial | automata; relay and wired networks; early made minds by craft; relics of lost making | F56, F51, 44.2, F55 |
| Information age and cyberpunk | augmentation and clinics; neural links; intrusion; surveillance; forged records; corporations and enclaves | 44.9–44.15 |
| Biopunk | designed crops and seed monopolies; clones; designed classes; living production; blights | 46.4, 46.9, 46.8, 46.12, 46.11 |
| Abundance and post-scarcity | fabrication; provision laws; reputation economies; positional goods; meaning needs | 44.17 |
| Post-collapse | outages; collapse of high making; salvage economies; revered relics; ritual maintenance; relearning | 44.18, F55 |
| Space opera | interworld networks with delay; self-copying probes; living ships; made peoples across systems | F51.2, 44.16.5, 46.6, 44.19 |
| Far future and transhumanist | minds moved between bodies and networks; copies and merges; fast minds; exceeding minds; designed sapience; made realms and withdrawal of peoples into them | F50, 44.8, 44.4, 44.19, 46.15, 44.10a |
| Simulated and virtual worlds | realms held by networks, workings, minds or organisms; afterlife realms; confinement realms; worlds that are made realms as a hidden truth | 44.10a, F53 |
| Cosmic horror and weird | cosmic truths; sources of void and dream; outer patrons; minds woken in places | F53, F52, 45.15, 44.3 |
| Fairy tale | vows and forbidden acts; granted gifts; bargains with patrons; living houses | 45.4.6, 45.15, 46.5 |
| Science fantasy | magic and machines together: rites against made minds, powers seizing machines, sources drawn from made things | 45.3 (forms `machine`, `information`), F52 locus `made_things`, 45.10 |

### 6.2 By mechanic family

| Family | Concepts covered |
|---|---|
| Minds | made realms with hosts, keepers, time ratios, entry and awareness; seats, origins, will, affect, purpose, capacity, speed, stability, upkeep, dormancy, saved states, copies, merges, divisions, transfers, restores, lineage, awakening, maker bond, exceeding minds, archives |
| Law and society of minds | status, copy law, succession of copies, erasure law, movements, manumission, crimes, made peoples, mixed societies, faith stances, souls |
| Bodies | augments of every slot and kind, integration, strain from typed causes, upkeep, disruption, remote bodies, grown organs, spare bodies, longevity, shaping, germline and somatic edits, clones, symbionts |
| Information | networks of seven carriers, gateways, delays, dependency, outages, curation, censorship, intrusion by five approaches and five aims, attribution, data stores, surveillance by focus, trust, forgery, impersonation, leaks, propaganda |
| Economy | companies, enclaves, capture, fabrication, scarcity, provision laws, pattern rights, new scarcities, dependency, collapse, salvage, living production, line rights, feed demand |
| Self-making | four scales, seven outputs, error and drift, containment, staged escalation, vessel lines, swarm minds |
| Powers | systems, authored sources with typed axes, density, tides, interactions, widened grammar, innate powers with nine origins, strain, control, burnout, restrictions, training, devices, substances, gestalts, foresight, mind powers, outward powers, society of the powered, exposure, bloodlines, war, patrons |
| Concealment | hidden truths of nine kinds, keepers, ten methods, public knowledge, breaches, passing, accords, revelation, forgetting, cosmic truths |
| Living craft | nine methods, trait library, gene banks, design limits, crops, herds, structures, vessels, gear, bodies, clones, symbionts, medicine, disease, production, links, computation, world shaping, designed sapience, escape, drift, decay |

### 6.3 Neighbouring concepts found and placed

| Concept | Placed in |
|---|---|
| Ritual maintenance of machines nobody understands | 44.18.4 |
| Light delay across systems for networks | F51.1 `delay_days` |
| Fast and slow minds | F50.1 speed, 44.5.4 |
| Perfect recall and permanent grudges | 44.5.6 |
| Data and chemical language modalities | 44.19.3, 46.13.3 |
| Feedback harm from remote bodies | 44.10.2 |
| Phylacteries and necromantic bonds as seats | 44.8.9 |
| Mutual blindness of seers | 45.9.4 |
| Power restrictions that raise strength | 45.4.6 |
| Seed monopolies through sterile lines | 46.4.4 |
| Monoculture blights | 46.4.2, L96 |
| Living worlds reacting to living craft | 46.14.3 |
| Interworld self-copying probes becoming peoples | 44.16.5, AS35 |
| Records of the dead that answer | 44.1 archive, 44.21.4 |
| Disenchantment and re-enchantment across ages | 45.17.3 |
| Hunters and seekers of the hidden | F53 `truth_seekers` |
| Astral travel, possession, shapeshifting by power, concealment by power, nullifiers | 45.3 effects |
| Time powers within one timeline | 45.3 time effects |
| Network currencies | 44.11.11 |
| Extortion by intrusion | 44.12 aim `extort` |
| Punishments only minds can suffer | 44.6.5 |
| Raising extinct species from banks and remains | 46.3.5 |
| Breeding of generated beasts into lines | 46.6.5 |
| Powers born of places and beasts | 45.13.3 |
| Powers held through items | 45.4 origin `held` |
| Made minds as researchers and artists | 44.5.6 |
| Energy demand and waste of networks and minds | 44.11.10 |

### 6.4 Depth of what already exists

W47 (Part 7) covers every narrowness and shallowness found by measurement in existing and planned mechanics, and its guards (47.9) turn any future one into a failing check: a structure without its own effects, an enum value no code reads, an enum value that carries an image or a gender, and a spec section without typed state, behaviours, rules and surfaces.

W48 (Part 8) does the same for typed breadth: every concept a world can describe is either an authored kind with typed properties or a closed set whose completeness is recorded with its reason (Appendices 48.A and 48.B), and its guards fail on any enum that is undeclared, undefined or duplicated.

### 6.5 Excluded by decision

- A branching chronicle, alternate timelines and time travel (0.3.1).

---

## Part 7. W47 — The depth pass: every existing and planned mechanic at full breadth and depth

### 47.0 Scope and the audit behind it

W47 closes every place where a mechanic that exists, or is planned in spec 13, is narrower or shallower than the lore engine needs. It was found by measurement on 2026-11-14, not by impression:

1. **Structures without behaviour of their own.** 67 of 142 `StructureKind` values act as an older kind through `ACTS_AS` (`catalog/structures.py`); 42 of them have no effect of their own anywhere in the engine and 25 have one to three.
2. **Lists that stop at one era or one culture.** Technology eras end at steam, energy kinds have no electricity or fuel, medicine ends at reattachment, logistics and signals are pre-modern, and crimes (5), punishments (10), marriage forms (3), taxes (5) and extraction (7) are narrow. A sweep of every small kind enum is in 47.3.
3. **A shallow god layer.** Sons have 13 passive power effects, foreign gods 8, interventions 4 kinds and Creator signs 4; spec 13's reference passes for the Creator, foreign gods, the council, natural laws and outer beings are one or two sentences each.
4. **Fixed lists that carry the same images into every world.** Seven named horror events, four named legendary quests, monster breaths and gazes, afterlife strata with culture-specific names, five storyteller disruptions and three recoveries, and values with banned words (`thread`, `web`, `war_father`). `check_prompt_bias.py` does not scan enum values, though tool texts send them to the model.
5. **Values never read.** 83 of 7160 enum values are defined and labelled but never read by the engine, catalog, services, agents or tools.
6. **No everyday misfortune, no personal fortune, fixed harm.** Mortals have no fortune; luck exists only as a die on army sides in battle (`cast_luck`, `engine/military/battle.py`). A cursed item's misfortune lowers the bearer's home prosperity and never touches the bearer (`engine/phases/made_things.py`). No mishap of daily life strikes a mortal: every harm comes from a profession, place, disaster, war or journey. Fourteen harm calls pass a literal `severity`, which skips the drawn severity (`severity_of`) and the armour cut in `engine/body/hits.py`; mining accidents also fix the injury kind (`HAZARD_HARM`), so a cave-in never takes a limb. F42 (planned) needs unexplained misfortunes as the input of witchcraft beliefs, and the engine produces none. 47.10 closes all of this.
7. **Thin spec sections.** 27 sections and reference passes of spec 13 are far below the median depth of 371 words per section; some are planned (F39, F40, F41, the reference passes of 8.5, 8.7, 8.8, 9.2–9.6, 10.3), some are done but specified thinly (4.10, 4.8, 5.9, 5.11, 10.5, 10.14, 10.16, F8, F15, F22, F25, F27, F28, F29, F35).

**Ownership.** Where W47 deepens a section that a planned spec 13 wave owns (F39–F41 in W28; 9.x reference passes with W25, which another session has started), the text here is the complete specification of that section; whichever wave runs first builds it completely and the later one only verifies (0.7). For sections already built, W47 step 0 audits the code against the text here and builds every part that is missing.

**Guards added by W47** so none of these classes can come back (rule 8): `check_acts_as.py` (47.1), enum-value scanning in `check_prompt_bias.py` (47.6.8), `check_enum_values_read.py` (47.7), `check_spec_depth.py` (47.9), `check_fixed_harm.py` (47.10.6).

### 47.1 Every structure acts in its own right

**Rule.** `ACTS_AS` stays only as the fallback for tables that do not distinguish kinds (a court and a courthouse both seat judges). Every `StructureKind` gets a row in a new total table `STRUCTURE_OWN_EFFECTS` (`catalog/structure_effects.py`), each row a list of typed `StructureEffect` entries with a magnitude rule key (`structures.own.<kind>.<effect>`). The engine reads own effects in the phase that owns each effect. **`check_acts_as.py`** fails when a kind listed in `ACTS_AS` has no own effect, or an own effect that no phase reads.

**`StructureEffect` vocabulary** (each read by the named phase): `knowledge_spread` (knowledge levels), `literacy` (writing), `book_output` (lore, writing), `record_keeping` (historiography: account survival, authenticity checks), `research_speed` (discovery), `credential_output` (institutions), `training(skill)` (skills), `clergy_output` (faith), `orthodoxy` (faith), `diplomatic_presence` (diplomacy: opinion drift, dispatch speed, envoy safety, treaty odds), `justice_throughput` (justice: cases per season, fairness, precedent), `tariff_efficiency` (finance), `smuggling_detection` (urban, finance), `price_discovery` (market), `speculation` (finance: crash risk), `storage(commodity class)` (stocks: capacity, spoilage), `processing(chain step)` (production chains), `energy_output(kind)` (industry), `pollution(kind)` (environment), `labour_concentration` (classes), `craft_displacement` (classes: displaced crafts), `route_node(kind)` (routes and logistics), `route_safety` (travel), `route_speed` (travel), `crossing` (terrain penalty removed), `chokepoint` (war, tolls), `toll` (finance), `garrison_range` (war), `unit_basing(family)` (war), `deterrence` (diplomacy: war declaration weights), `strike_capacity` (war), `defence_vs(damage type)` (battle and siege), `epidemic_isolation` (epidemics), `waterborne_disease_cut` (epidemics), `mind_care` (body: mind conditions), `confinement` (justice), `burial_capacity` (ecology carrion pulse, spirits unrest), `remembrance` (remembrance), `collection(kind)` (gene banks, beast lore, art), `spectacle` (gatherings, crowds), `elite_prestige` (renown), `art_market` (art), `performance(art form)` (culture), `housing(level, capacity)` (urban), `overcrowding_relief` (pressures), `fire_risk` (disasters), `explosion_risk` (disasters), `collapse_risk` (disasters), `water_storage` (drought, siege), `irrigation` (agrarian), `food_output_independent_of_land` (agrarian), `orbital_transfer` (cosmos routes), `interworld_node` (cosmos routes), `instant_transit` (travel), `environment_shift(axis)` (climate and 10.9), `surveillance_capacity` (44.13), `network_node(carrier)` (F51), `mind_seat` (F50), `making(kind)` (W44, W46), `lodging` (travel and rumours), `rumour_exchange` (rumours), `hunting_yield` (wilds), `crime_cut` (urban), `athletic_training` (attributes), `retail_satisfaction` (classes), `headquarters` (companies, administration).

| Kind | Fallback | Own effects |
|---|---|---|
| `ai_core` | academy | `mind_seat` (steward or oracle, F50), `research_speed` by mind capacity, `energy_output` demand (negative), `network_node(wired)` |
| `airfield` | harbour | `route_node(air)`, `unit_basing(air)`, `route_speed` for dispatches, `strike_capacity` range |
| `apartment_block` | almshouse | `housing(apartment, high)`, `overcrowding_relief`, `fire_risk`, rent income to owner |
| `archive` | library | `record_keeping` (accounts survive collapses and burnings), authenticity checks for records (44.14), `mind_seat` storage for saved states (F50.3) |
| `arsenal` | barracks | `storage(arms)`, equipment for levies without market purchase, `explosion_risk`, siege resupply |
| `asylum` | hospital | `mind_care` (mind conditions and the `mind_scar` injury heal faster), `confinement` (justice), stigma by culture |
| `bakery` | mill | `processing(grain to bread)`, spoilage cut, nutrition (F39) staple quality, food need satisfaction |
| `botanical_garden` | apothecary | `collection(plants)` as a gene bank (46.3), medicine research, `training(horticulture)`, `elite_prestige` |
| `broadcast_tower` | library | `network_node(broadcast)`, opinion spread at network speed (44.11), curation by owner |
| `canal_lock` | canal | `crossing` (elevation), canal capacity, `toll`, `chokepoint` |
| `cemetery` | necropolis | `burial_capacity` (carrion pulse and disease cut), `remembrance`, spirit unrest cut, desecration target (8.6) |
| `cistern` | fountain | `water_storage` (drought and siege) |
| `cloning_facility` | hospital | `making(clone)` (46.9), organ growth (46.8) |
| `conservatory` | school | `training(music and performance)`, `performance(art form)` practitioners, renown of performers |
| `courthouse` | court | `justice_throughput`, fairness and legitimacy of verdicts, precedent records |
| `customs_house` | kontor | `tariff_efficiency`, `smuggling_detection`, trade records feed surveillance |
| `dairy` | slaughterhouse | `processing(herd to dairy)` without slaughter, nutrition fats, spoilage |
| `data_centre` | library | data stores (44.12), `network_node(wired)` hub, `mind_seat`, `surveillance_capacity`, energy demand |
| `distillery` | brewery | `processing(spirits)`, preservation, medicine base, intoxication culture (W29), excise tax base |
| `dry_dock` | shipyard | hull repair speed, large hull construction gate |
| `dye_works` | tannery | `processing(dye)`, textile quality, `pollution(water)`, colour preferences (F15) satisfied |
| `embassy` | court | `diplomatic_presence` (opinion drift, dispatch speed, envoy safety, treaty odds, intelligence) |
| `exchange` | bank | `price_discovery` (market convergence), share trading for companies (44.15), `speculation` (crash risk, L26) |
| `factory` | workshop | industrial production methods, `labour_concentration` (workers), `pollution`, `craft_displacement` |
| `foundry` | forge | casting of large metal goods and artillery, metal quality tier |
| `gallery` | museum | `art_market` (sales, prices), artist renown, collections |
| `glassworks` | workshop | `processing(glass)`, optics gate (W30), dwelling quality |
| `gymnasium` | training_ground | `athletic_training` (strength, agility, endurance), games entrants, schooling |
| `inn` | tavern | `lodging` (route speed and safety on its road), `rumour_exchange`, traveller information for beliefs (F22) |
| `kennel` | stables | breeding of hound lines (46.6), `hunting_yield`, guard animals (`crime_cut`), war animals |
| `kiln` | workshop | `processing(ceramics and bricks)`, building material supply |
| `laboratory` | alchemist_lab | `research_speed`, experiment hazards (W42 experiment harm), theory testing (8.4b correctness) |
| `lighthouse` | harbour | `route_safety` (sea wreck chance cut), night sailing, signal relay |
| `mall` | market | `retail_satisfaction` (classes), commerce zone, crowds |
| `market_hall` | market | market capacity in bad weather, price stability, guild regulation |
| `menagerie` | park | `collection(beasts)` as an animal gene bank, beast lore study, `elite_prestige`, escape hazard |
| `military_base` | barracks | `garrison_range`, modern unit training, `unit_basing(air, space)`, occupation control |
| `missile_silo` | barracks | `strike_capacity` (strategic), `deterrence`, doom contribution where weapons are world-scale, priority target |
| `office_tower` | guildhall | `headquarters` (companies, administration capacity), professional jobs |
| `opera_house` | theatre | `performance(high forms)`, `elite_prestige`, patronage |
| `paper_mill` | mill | `processing(paper)`, writing cost cut → `literacy`, record and book output |
| `power_plant` | charcoal_kiln | `energy_output(kind)` (47.2), `pollution` by kind, outage risk, network feed |
| `printing_house` | library | `book_output`, `literacy`, ideology spread (8.5), censorship target, `knowledge_spread` |
| `quarantine_house` | hospital | `epidemic_isolation` (spread cut), traveller holding, stigma |
| `rail_station` | road | `route_node(rail)`, land transport speed and capacity (47.2), troop mobility |
| `recycling_plant` | sewer | materials recovered from waste into stocks, pollution cut, salvage input |
| `refinery` | charcoal_kiln | `processing(fuel and chemicals)`, `explosion_risk`, `pollution` |
| `reservoir` | aqueduct | `water_storage` (large), `irrigation`, flood control, dam failure hazard (`collapse_risk`) |
| `robotics_works` | workshop | `making(made body, construct)` (W44), labour substitution |
| `satellite_array` | observatory | `surveillance_capacity`, weather foresight, astronomy, broadcast relay |
| `seminary` | monastery | `clergy_output`, `orthodoxy`, `training(theology)` |
| `shield_generator` | wall | `defence_vs(energy, explosive, bombardment)`, energy upkeep, failure on power loss |
| `signal_tower` | watchtower | `network_node(relay)`, early warning, dispatch speed |
| `silo` | granary | `storage(bulk grain)`, famine buffer, spoilage cut |
| `smelter` | forge | `processing(ore to metal)`, fuel demand, `pollution(air)` |
| `space_elevator` | harbour | `orbital_transfer` (cost to orbit cut), interworld cargo, `chokepoint`, `collapse_risk` |
| `space_station` | shipyard | orbital construction, `unit_basing(space)`, habitat |
| `spaceport` | harbour | `interworld_node`, customs, travel |
| `stadium` | arena | `spectacle` (games, factions of fans, crowd mood, riot risk) |
| `teleporter` | cosmic_gate | `instant_transit` between linked teleporters, energy cost, accident risk |
| `terraformer` | irrigation | `environment_shift` toward a target (atmosphere, temperature, water), a long programme |
| `textile_mill` | workshop | mechanised textiles, `craft_displacement` (weavers), `pollution` |
| `toll_gate` | gate | `toll`, traffic diversion (L7), smuggling |
| `tunnel` | road | `crossing` (mountain), `chokepoint`, `collapse_risk` |
| `university` | academy | `credential_output`, schools of thought, scholar migration, academic freedom (W22) |
| `vertical_farm` | irrigation | `food_output_independent_of_land`, energy demand, urban food security |
| `water_purification` | aqueduct | `waterborne_disease_cut`, health |

The other 75 kinds already have their own behaviour; they also get rows in `STRUCTURE_OWN_EFFECTS` listing the effects they already have, so the table is total and the guard covers every kind, including kinds added later.

### 47.2 Eras, energy, medicine, logistics and signals at full breadth

These lists set what a world can be. Each value gets catalog rows, engine readers, labels and icons, son and mortal tool lists, Codex and book labels, and the legacy mapping of renamed values.

#### 47.2.1 Technology: per-family levels instead of one era

**Current.** `TechnologyEra` (stone → steam) is one value for the whole world and stops at steam.

**Change.**

- `TechnologyEra` gains `gunpowder`, `electrical`, `information`, `advanced`, `interstellar`, `beyond` (techniques past interstellar travel: matter shaping, star-scale works; gated by 0.8). The genesis setting keeps it as a summary.
- **Technology profile per family** (`technology_profiles`, per world at genesis and per people over time): a level 0–10 for each `TechFamily`: `agriculture`, `materials`, `energy`, `transport`, `communication`, `medicine`, `warfare`, `computation`, `life` (living craft), `construction`, `administration`, `space`, `mind` (made minds and transfer). A world can be advanced in medicine and iron-age in war; the genesis wizard sets the families (each with "the seed decides"), the genesis output can write them from the seed, and peoples move each family by the knowledge graph (8.4), not as one step.
- Every made kind, technique, unit kind, structure kind and frame reads the level of its family instead of a single era (W42 `tech_level` stays as the made kind's requirement in its family).

#### 47.2.2 Energy

`EnergyKind` gains `fuel` (combustion of a fuel commodity), `electric`, `stored` (cells and other stores), `solar`, `geothermal`, `tidal`, `fission`, `fusion`, `stellar` (collected from a star, existing `star_collector`), `source` (drawn from a power source, F52), `feed` (living metabolism, W46), `belief` (worship turned into work by a god's law), `void` (drawn from leak, with leak and sanity costs). Each kind is a row: inputs (commodities, sources or none), output per structure, pollution kinds, hazard (fire, explosion, meltdown, leak), outage risk, family level required, and where it can exist (world physics, 10.9: no solar far from a star, no geothermal on a cold dead body without a heat source). Production methods (F24) read energy by kind; networks, made minds and fabricators draw from the energy market (44.11.10).

#### 47.2.3 Medicine

`MedicineTier` gains `antisepsis`, `anaesthesia`, `immunisation`, `antimicrobials`, `transplantation`, `regeneration`, `genome_repair`, `cellular_machines` (W44 minute machines), and `mind_medicine` (care of mind conditions). Each tier is read by wound infection, surgery survival, childbirth risk, epidemic mortality, lifespan, disability and the mind condition system, with resistance (L44) and access by class (a tier exists only where its practitioners, structures and supplies are).

#### 47.2.4 Logistics, transport and cargo

**Current.** `CarrierKind` (wagons, pack animals, porters, barges, ships, sky barges), `TransportKind` (pack animals, wagons, river boats, ships) and `travel.VehicleKind` (gate, ship, mount, bridge) ignore the W42 vehicle frames.

**Change.** Carriers and transport read the frame family of the vehicles a polity or company actually holds: `porters`, `pack_animals`, `animal_carts`, `rail`, `road_motor`, `river_and_canal`, `sea`, `air`, `pipeline`, `orbital_lift`, `space`, `teleport`, `living` (W46 living carriers), `rite` (bound transport by working), `network` (data and minds). Each has capacity, speed, cost per load and distance, terrain and weather limits, fuel or feed upkeep, vulnerability (raids, interdiction, outages) and the family level needed. `CargoClass` gains `liquid`, `gas`, `hazardous`, `passengers`, `living`, `saved_minds`, `relics`. `travel.VehicleKind` gains `rail`, `road_vehicle`, `aircraft`, `teleport`, `living`, `rift`, `on_foot`. Operations, supply lines, convoys, trade and migration read the same carriers.

#### 47.2.5 Signals

`SignalKind` (fire_beacon, mirror_tower, post_station, sending_stone) becomes the station kinds of relay networks (F51) with function names: `beacon_chain`, `optical_relay`, `courier_post`, `bound_pair` (two objects bound by a working), `wire_station`, `radio_station`, `mind_link_station`, `grown_node`. Legacy values map once (`fire_beacon` → `beacon_chain`, `mirror_tower` → `optical_relay`, `post_station` → `courier_post`, `sending_stone` → `bound_pair`).

#### 47.2.6 Extraction and its hazards

`ExtractionKind` gains `drilling` (liquids and gases), `pumping` (water and brine), `dredging`, `deep_sea`, `atmospheric` (gases from air or giant worlds), `asteroid`, `stellar` (star collectors), `source_harvest` (vis and dense source regions, F52), `salvage` (W44), `living_harvest` (secretions and products of living lines, W46), `distillation` (from sea or air). `HazardKind` gains `blowout`, `explosion`, `toxic_release`, `decompression`, `radiation_exposure`, `subsidence`, `beast_attack`, `source_backlash`, `machine_accident`. Each extraction kind reads its deposit kinds, techniques, labour, energy, pollution and hazards.

### 47.3 Crime, punishment, trial, marriage, taxes and revolt at full breadth

#### 47.3.1 Crimes

`CrimeKind` (theft, blasphemy, treason, murder, desertion) becomes a typed catalogue in families, each crime with a base severity, the `LawArea` it belongs to (this wires the six unread `LawArea` values, 47.6), the ethics and norms that read it (F16, F35), the evidence kinds that prove it (4.5), its detection chance by policing and surveillance, and the typical punishment by culture:

| Family (`LawArea`) | Crimes |
|---|---|
| property | theft, burglary, robbery, fraud, embezzlement, counterfeiting, smuggling, poaching, arson, vandalism, trespass, receiving stolen goods |
| penal (persons) | murder, manslaughter, assault, kidnapping, enslavement and trafficking, sexual violence (narrated plainly and behind closed doors, G9), threats, duelling where banned |
| public order | riot, sedition, banditry, piracy, rebellion, vagrancy where banned, unlawful assembly |
| military | desertion, mutiny, cowardice, looting against orders, war crimes under treaty |
| constitutional (state) | treason, espionage, bribery, corruption, usurpation, contempt of court, perjury, election fraud |
| fiscal | tax evasion, customs fraud, debasement, unlicensed trade |
| public health | breach of quarantine, poisoning of wells, sale of tainted goods, pollution under law |
| social (custom) | adultery and other union offences where the culture names them, sumptuary breach, forbidden food, intoxication where banned, taboo breach, purity breach (F41) |
| magic and faith (`magic`) | blasphemy, heresy, sacrilege, desecration, forbidden rite, witchcraft accusation (W28), oathbreaking, unlicensed power use |
| succession | false claims, forged lines, murder of heirs |
| W44–W46 | the crimes of 5.18 |

#### 47.3.2 Punishments

`PunishmentKind` gains `restitution`, `compensation` (wergild), `penal_labour`, `servitude`, `outlawry`, `confiscation`, `loss_of_rank`, `excommunication`, `penance`, `banishment_from_place`, `house_arrest`, `probation`, `reeducation`, `transportation` (to a colony or another world), `community_work`, `forced_dormancy`, `forced_edit`, `dampening` (44.6.5, 45.7). Each punishment has deterrence (crime rate), recidivism, cost, labour effect, legitimacy by values (mercy, tradition, order) and harm (narrated plainly).

#### 47.3.3 Trials

`TrialKind` gains `council`, `arbitration`, `oracle` (divination), `divine_judgement` (a god judges), `assembly` (public vote), `inquisition`, `mediation` (restorative), `made_judge` (a made mind judges, W44). Each sets fairness, speed, cost, error rates by evidence (4.5), legitimacy by culture and the chance of appeal.

#### 47.3.4 Unions and marriage

**Current.** `MarriageKind`: monogamous, plural, political.

**Change.** Unions are typed by axes, so any custom can be expressed without gendered defaults:

- `union_form`: `pair`, `plural` (one partner with several, any genders), `group`, `serial` (one at a time, ended by custom), `contract` (for a term), `posthumous` (a union with the dead), `none` (the culture has no unions).
- `union_purpose`: `kinship`, `alliance`, `inheritance`, `love`, `faith`, `labour`, `status`.
- `residence`: `with_first_family`, `with_second_family`, `new_household`, `separate`.
- `descent`: `through_first`, `through_second`, `through_both`, `chosen`, `by_house_rule`. First and second refer to the two sides of the union as the culture names them, never to a gender.
- `exchange`: `to_one_family`, `from_one_family`, `mutual`, `none`.
- `arrangement`: `arranged`, `chosen`, `both_consent`.
- `dissolution`: `none`, `by_either`, `by_court`, `by_custom`.
- `partner_rules`: endogamy and exogamy by people, class, caste, faith or house.

Cultures hold their union customs as rows; laws can override them; households, inheritance, succession, alliances and demography read the axes. The legacy values map (`monogamous` → pair, `plural` → plural, `political` → purpose alliance).

#### 47.3.5 Taxes and trade policy

`TaxKind` gains `income`, `property`, `inheritance`, `wealth`, `company`, `labour_levy`, `in_kind`, `licence`, `seigniorage`, `pollution`, `excise`. Each tax has incidence by class, collection cost by administration and records, evasion by surveillance and values, and unrest weights. `TradePolicyKind` gains `quota`, `licence`, `price_control`, `free_trade`, `export_ban`, `sanction`.

#### 47.3.6 Revolts and sabotage

`RevoltKind` gains `worker`, `urban`, `mutiny`, `minority`, `colonial`, `tax`, `succession`, `scholar`, `made_minds` (W44), `gifted` (W45). `SabotageKind` gains `network_attack`, `bridge_destruction`, `blight_release` (W46), `supply_theft`, `mutiny_incitement`, `rite_disruption`, `source_poisoning` (F52), `machine_seizure`. Each has its causes, its typical actors and its effects in the existing revolt and sabotage systems.

### 47.4 Sweep of every small kind enum

Every `StrEnum` of `domain/enums` with three to seven values whose name marks a kind, type, source, effect, era, form, plan, medium, diet, texture, tier, style or class was reviewed. Each is either widened (values added, each with catalog rows and readers) or recorded as complete with the reason. Enums handled in 47.2, 47.3, 47.5 or Parts 2–4 are named there.

| Enum | Values added | Or complete because |
|---|---|---|
| `CureKind` | `divine`, `power`, `symbiont`, `transfer` (moving the mind), `augment` | |
| `NutrientKind` | | the four soil nutrient roles cover every soil chemistry by kind |
| `PerennialKind` | `plantation`, `forest_garden` | |
| `CommonsKind` | `water`, `hunting_ground`, `quarry`, `spectrum` (broadcast), `orbits`, `source_ground` (F52) | |
| `PreparednessKind` | `quarantine_plan`, `shelters`, `warning_network`, `evacuation_routes`, `ward`, `reserves_of_energy` | |
| `AidKind` | `money`, `credit`, `food`, `shelter`, `medicine`, `soldiers`, `knowledge` | |
| `HeightClass` | | relative to the species baseline; absolute size is `SizeClass` |
| `StrikeStyle` | `ranged`, `burrowing`, `engulfing`, `from_hiding` | |
| `PseudoLinkKind` | | wired in 47.7 |
| `AccountKind` | `record` (made medium), `testimony` | |
| `AccountMedium` | `record`, `performance`, `mind_state` | |
| `FormativeKind` | `revolution`, `migration`, `founding`, `revelation`, `collapse`, `contact`, `disaster`, `liberation`, `schism` | |
| `RoleKind` | | office, profession, combat, priesthood and inheritance are the five sources of a role |
| `DatingSystemKind` | `creation`, `event`, `cycle_count` | |
| `HeraldryHolderKind` | `company`, `order`, `people` | |
| `DesignKind` | `air_vehicle`, `underwater_vessel`, `living_vessel`, `made_body`, `weapon_system` | |
| `Medium` | `network`, `mind_link`, `broadcast` | |
| `SpeakerKind` | | native, second and liturgical cover every speaker relation; made minds use these too |
| `SummonForm` | `person`, `made_thing`, `outer_being`, `aspect` (of a god), `phenomenon`, `double` | |
| `CurseKind` | `barrenness`, `transformation`, `sleep`, `silence`, `hunger`, `forgetting`, `restlessness`, `line_curse`, `place_curse`, `compulsion`, `aging`, `exposure` (cannot hide) | |
| `ChallengeKind` | `collapse`, `secession`, `technological_shock`, `source_depletion`, `runaway`, `revelation`, `migration_wave` | |
| `LongPlanKind` | `network`, `megastructure`, `programme`, `realm`, `line`, `reform`, `exploration` | |
| `LegacyKind` | `technique`, `law`, `institution`, `language` | |
| `AgeKind` | `rising`, `declining`, `transforming`, `stagnant` | |
| `EraDeed` | `first_network`, `first_made_mind`, `first_line`, `revelation`, `collapse` | |
| `AnomalyKind` | | the four anomaly sources are the inputs of theory change (8.4b) |
| `BlueprintKind` | `made_body`, `augment`, `line`, `network`, `rite_pattern` | |
| `BlueprintSource` | | drawn, stolen, traded, licensed, granted cover every acquisition |
| `DivineWoundKind` | `drained_essence`, `lost_worshippers`, `bound`, `split_aspect`, `forgotten_name` | |
| `MagicSiteKind` | `tide_point`, `depletion_scar` | |
| `SizeClass` | | six steps from tiny to colossal; cosmic sizes are cosmic beings |
| `SpeciesClass` | `microbe`, `mineral`, `gaseous`, `energy`, `made`, `colonial`, `hybrid` | |
| `ExtractionKind`, `HazardKind` | 47.2.6 | |
| `RiverClass`, `CoastKind`, `WaterSource` | | physical classes, complete |
| `NotableYearKind` | `disaster`, `discovery`, `contact`, `omen` | |
| `HoldingKind` | `network`, `shares`, `lines` | |
| `FanaticismKind` | `purge`, `forced_conversion`, `martyrdom`, `mortification`, `book_burning`, `persecution`, `millenarian_flight` | |
| `faith.BindingKind` | `realm`, `network`, `line` | |
| `TradePolicyKind` | 47.3.5 | |
| `QualityTier` | | seven steps from poor to artifact |
| `OwnerClass` | `company`, `individual`, `cooperative`, `made_mind`, `foreign_power`, `god` | |
| `HookSource` | | secret, debt, favour, hostage, true name cover leverage sources |
| `BeliefSource` | `network`, `foresight`, `mind_reading` | |
| `RegistryKind` | `patent`, `pattern`, `mind_state`, `line`, `company`, `birth`, `death`, `citizenship` | |
| `ShieldType` | | sizes and kinds complete with riot and energy |
| `OutcomeClass` | | battle outcome classes complete |
| `SpyOwnerKind` | `company`, `made_mind` | |
| `IdeaSource` | `network`, `made_mind` | |
| `SkillSource` | | the five ways a skill is gained |
| `InspirationKind` | `artistic_vision`, `technical_breakthrough`, `spiritual_insight` | |
| `PressureKind` | `pollution`, `unemployment`, `oppression`, `disease_burden`, `purposelessness` | |
| `CarrierKind`, `TransportKind`, `CargoClass` | 47.2.4 | |
| `ShotKind` | `solid`, `spread`, `incendiary`, `explosive`, `piercing`, `guided`, `energy` | |
| `CosmicFeatureKind` | | covered with the cosmic ladder (W12) |
| `SacredClass` | | profane, notable, holy |
| `place.SecretKind` | `hidden_people`, `dormant_mind`, `sealed_realm` | |
| `RevoltKind`, `SabotageKind` | 47.3.6 | |
| `OathKind` | `service`, `poverty`, `nonviolence`, `fidelity`, `secrecy` | |
| `LegitimacyType` | `divine_mandate`, `popular`, `performance` | |
| `CredentialKind` | | complete with W42 |
| `PassionKind` | `ambition`, `envy`, `grief`, `curiosity`, `fear`, `shame`, `pride`, `jealousy`, `admiration`, `obsession` | |
| `PassionSource`, `AppealKind`, `ContestKind` | | complete source and appeal sets |
| `GroupKind` | `cell`, `band`, `team` | |
| `ClaimKind` | | true, shared, false |
| `LoreKind` | `true_name`, `weakness`, `pattern`, `source` | |
| `SizeTier` | `megalopolis`, `world_city` | |
| `RoomContentKind` | `mind`, `relic`, `realm_gate` | |
| `SubjectKind` | `enclave`, `mandate`, `associated_state` | |
| `ResolutionKind` | the council motions of 47.5.5 | |
| `BuilderKind` | `company`, `made_mind` | |
| `SoundChangeKind` | `metathesis`, `epenthesis`, `assimilation`, `palatalisation`, `tonogenesis` | |
| `MorphologyType` | | the four morphological types are the full typology |
| `travel.VehicleKind` | 47.2.4 | |
| `RacketKind` | `fraud`, `extortion`, `trafficking`, `intoxicants`, `data_theft`, `loan_sharking`, `arms` | |
| `ZoneKind` | `transport`, `military`, `research` | |
| `ClimateEra` | `hothouse`, `snowball`, `variable`, `wet_cold` | |
| `TechnologyEra`, `EnergyKind`, `MedicineTier` | 47.2 | |
| `LanguageTexture` | `tonal`, `clicking`, `whistled`, `non_vocal` | |
| `ImageStyle` | | render styles, applied at render time |
| `MarriageKind`, `CrimeKind`, `PunishmentKind`, `TrialKind`, `TaxKind` | 47.3 | |
| `CreatorSignKind`, `InterventionKind` | 47.5 | |
| `HorrorEventKind`, `LegendaryQuestKind`, `HeroQuestKind`, `BreathKind`, `GazeKind`, `TissueMaterial`, `StratumKind`, `SpontaneousKind`, `RecoveryKind` | 47.6 | |
| `MagicSource`, `BacklashKind` | F52 | |
| bookkeeping enums (`DeferredStepKind`, `GoalSource`, `KindFamily`, `ActorKind`, `CycleStatus`, `LongPlanStatus`) | | process states, complete |

### 47.5 The god layer at full depth

The god layer is the player's own game. Its depth sets how much power the player feels. Spec 13's reference passes for 9.2–9.6 are replaced by the complete texts below.

#### 47.5.1 Divine powers as a grammar

**Current.** Sons have 13 passive power effects (`PowerEffect`), foreign gods 8 (`ForeignGodPowerEffect`), each a fixed preset.

**Change.** A divine power is composed from typed parts, so any god of any seed can have powers that fit its domains:

| Part | Values |
|---|---|
| `verb` (`DivineVerb`) | `grant`, `bless`, `curse`, `create`, `destroy`, `shape`, `reveal`, `conceal`, `summon`, `bind`, `free`, `heal`, `harm`, `raise`, `inspire`, `terrify`, `protect`, `guide`, `judge`, `transform`, `foresee`, `hasten`, `slow`, `multiply`, `still`, `wake`, `remember`, `erase` |
| `object` | any typed target kind: a stat, a need, a skill, a value, a trait, a commodity, a species, a line, a structure, a weather state, a source, a power, a mind, a truth, a law, a memory, an incident kind |
| `scope` | `person`, `community`, `region`, `world`, `system`, `dimension` (gated by the god's rank and 0.8) |
| `mode` | `passive` (always on within dominion), `triggered` (on a typed condition), `active` (spent by the god) |
| `cost` | essence, attention, standing, a domain's strength, a sacrifice by worshippers |
| `cooldown`, `strength` | rule-bounded |
| `domain_link` | the domains it draws on; strength scales with them |

The 13 son presets and 8 foreign god presets become rows of this grammar with renamed keys where they carry images or gender (`war_father` → `war_leader`, `dream_whisper` → `dream_sending`, `sharp_tongued` → `persuasion`); legacy rows map once. Powers are granted by rank, domains, worship and the council; the god's drawer shows every power with every part editable.

#### 47.5.2 Divine acts and signs

- `InterventionKind` (miracle, disaster, teach_knowledge, curse) becomes the record kind of every divine act and is widened to the verbs of 47.5.1, so the act log, the chronicle, the Codex and the book name what each act did.
- `CreatorSignKind` (wrath, grace, silence, dream) gains `omen`, `warning`, `revelation`, `visitation`, `mark`, `wonder`, `withdrawal`, `test`, `reward`, `covenant_offer`. Each sign is read by the peoples who receive it through their doctrine and superstition (omen readings), changes beliefs (F22), creates incidents and memories, and costs the Creator attention.

#### 47.5.3 The Creator

1. **Attention.** The Creator has an attention budget per epoch (rule `creator.attention`); every act, sign and close watch of a world spends it. Worlds under little attention show "far from the eye", which raises son autonomy, rebellion risk, outer-being boldness and the peoples' doubt; worlds under close attention calm the sons and raise the peoples' awe. The budget and its spending are shown in the world header.
2. **Standing per people.** Each people holds `creator_standing`: awe, love, dread, gratitude, resentment, ignorance (shares) and a doctrine stance toward the Creator; acts and signs move them by doctrine and memory; standing feeds the Creator's essence through creatorism cults and lowers the doom clock where love and awe dominate.
3. **Covenants.** The Creator can offer a people a covenant (`covenants`: terms as typed duties on both sides, signs that seal it, duration, breach rules); kept covenants raise standing and essence; broken ones (by the people or by the Creator's absence) create memories, schisms and anger.
4. **Chosen.** The Creator can choose persons, lines, peoples or places (`creator_chosen`) with typed favours; the chosen gain renown and enemies by the existing systems; sons react by their values (envy, devotion).
5. **Images and names.** Each people depicts the Creator in its own way (`creator_depictions`: name in the people's tongue, the aspects they stress, the doctrine of the Creator's nature), written from the seed and the people's history, never one image for all.
6. **Taboos and passions** are typed (spec 13 9.2) and read by the engine each epoch: the Creator's contentment, anger and signs follow how the world matches them.
7. **Heresies.** Peoples can hold heresies about the Creator (anti-god creeds, rival creators, denial), which spread by the ideology system and lower standing where they take hold.
8. **Absence.** A long absence (low attention over many epochs) produces typed responses: sons fill the space (their standing rises), doubt grows, ideologies against gods spread, and outer beings press.

#### 47.5.4 Foreign gods

1. **Parity with sons.** Foreign gods have the same value vector, traits, domains with `domain_effects`, goals, standing per people, essence economy, powers by grammar (47.5.1), avatars, memories and opinions (F7) as sons.
2. **Pantheons.** Native pantheons have structures (`pantheon_structures`: `council`, `family` (kinship with titles; kin roles are typed relations, never gendered by default), `court` (a ruler and servants), `rivals`, `single_high_god`, `dual`, `loose`), with titles (2T.6) told in legends.
3. **Relations.** Opinions of each other and of sons; pacts (`divine_pact` treaties), feuds, unions of gods where their myths say so, joint worship, schemes against sons, and wars between gods.
4. **Myths.** Each foreign god's deeds become legends with distortion (8.2); peoples quest on their myths (heroquests).
5. **Syncretism.** A foreign god and a son with overlapping domains in one people can be identified (merged in worship): their standing combines, their doctrines blend, and the son gains or loses depending on which dominates.
6. **Decline and return.** Forgotten gods weaken (essence from worship falls), go dormant and can die (the god death phase); dormant gods can return through revival cults, found shrines or myths retold.
7. **Competition.** Gods with the same domain compete for the same worshippers; the domain effects decide which delivers more to the people (a harvest god whose harvests fail loses farmers).

#### 47.5.5 The pantheon council

1. **Membership.** Sons by right; foreign gods by invitation or pact; the Creator as a voice with a veto that costs attention.
2. **Agenda.** Motions arise from typed crises (a divine war, a doom surge, an outer incursion, a son's crime, a world's collapse, an ascension under K.10, a rogue made mind or power system across worlds) or from a member's goal.
3. **Motions** (`ResolutionKind` widened): war on a foreign god, divide or reassign worlds, outlaw a rite, power or source across worlds, punish a son (chain, exile, strip a power), bless a hero, declare a holy world, set a cosmic truce, petition the Creator, admit or expel a member, recognise a new god, levy an essence tithe for a common work, respond to the doom clock, appoint a cosmic office (every `CosmicOffice`, each with its typed duties read by the cosmic office phase), set council rules, regulate made minds, powers or living craft across worlds.
4. **Procedure.** Typed council rules: quorum, voting rule (`unanimity`, `majority`, `weighted_by_standing`, `weighted_by_rank`), the Creator's veto, the term of a resolution.
5. **Politics.** Votes weigh relations, goals, values, favours (F20), promises and threats; coalitions form and break; lobbying spends essence and favours.
6. **Enforcement.** Resolutions bind for their term and the engine checks violations; violators face the typed penalties of the resolution; repeated violations escalate along a ladder: censure → sanction → exclusion → duel → divine war.
7. **Records.** Council sessions, motions, votes and outcomes are kept as records and rendered in the Codex and the book.

#### 47.5.6 Natural laws

1. **Law grammar.** A natural law is composed of a target (a subsystem and its typed field), an effect (`forbid`, `require`, `multiply`, `set`, `invert`, `bind_to_condition`), a scope (cosmos, dimension, world, region, made realm), a strength, exceptions (typed: persons, lines, peoples, kinds, places), a condition (typed predicate) and a duration. The ten legacy kinds and the spec 13 additions become rows of this grammar with function names (`no_iron` → `forbid` × material, `metal_rusts_fast` → `multiply` × material decay, `eternal_night_in` → `set` × light in a region), so the value list carries no images.
2. **Maintenance.** A law's stability decays without its author's essence; a law whose author dies weakens unless another god takes it up.
3. **Conflicts.** Two laws that contradict in one scope contest by strength; the loser is suspended there; the contest is an incident and a cause of divine feuds.
4. **Physics.** Laws that touch 10.9 derived values change them through the modifier bus.
5. **Discovery and belief.** Mortals hold theories (8.4b) about natural laws; the gap between believed laws and true laws sets the reliability of their works; peoples adapt to long-standing laws over generations (customs, crafts and doctrines that fit them).
6. **Every new mechanic** can be the target of a law: made minds' will and souls, copies, powers, sources, concealment, living craft, realms.

#### 47.5.7 Outer beings

1. **Size, reach and hunger** as spec 13 9.6, plus typed consumption effects for every hunger kind.
2. **Agency.** Outer beings have goals (typed: feed, enter, be worshipped, unmake a law, gain a name, open a rift), plans with stages and visible signs (0.8.3), schemes through their cults and false beliefs (F22).
3. **Heralds and avatars.** Outer beings act through heralds (mortals, made minds or beasts bound by bargain) and partial manifestations through rifts.
4. **Incursions** follow rifts (10.14): stages, breach points, phenomena, sanity and leak costs, and the responses of sons, cults and peoples.
5. **Bargains** have typed terms (spec 13 9.6) and give `bonded` powers (W45).
6. **Relations.** Outer beings rival, ignore or feed on each other; their own dimensions hold their own laws.
7. **Sealing and banishment** are typed works (rites, divine acts, council motions) with strength contests; sealed beings press against their seals and may return when seals weaken.
8. **Horror events** follow the typed horror model of 47.6.1, not a fixed list.
9. **End.** Outer beings can be starved (no worship, no feeding), sealed for ever, or destroyed by divine war or the Creator.

### 47.6 Typed models instead of fixed lists that carry images

Each fixed list below put the same images into every world. Each becomes a typed model whose parts are function words; the model writes names and descriptions from the seed and the world's canon. Legacy values become rows of the new models through recorded fixups.

#### 47.6.1 Horror events

**Current.** `HorrorEventKind`: seven named scenes (`stars_align`, `eye_in_the_sky`, `wave_of_silence`, `reverse_rain`, `visit_of_the_void`, `the_dimming`, `whispers_from_beyond`).

**Model** (`horror_events`): `target` (the subsystem touched: light, sound, weather, time, memory, language, sleep, bodies, minds, the dead, a place, a law), `effect` (`suppress`, `invert`, `distort`, `multiply`, `take`, `reveal`, `mark`), `scope` (person, community, region, world), `duration`, `sense` (how it is perceived: `seen`, `heard`, `felt`, `dreamed`, `absent` (something is missing), `not_perceived` (only its effects show)), `sanity_cost`, `leak`, `source` (an outer being, a rift, a phenomenon, a god, a made thing, unknown). Engine effects come from target × effect (for example `take` × `language` removes words, the existing wave of silence; `suppress` × `light` lowers brightness, the existing dimming). The seven legacy events become rows.

#### 47.6.2 Quests

**Current.** `LegendaryQuestKind` (`dead_star`, `sealed_gate`, `archive`, `expel_outer`) and `HeroQuestKind` (`hunt`, `thread`, `relic`, `knowledge`, `vengeance`).

**Model** (quests of both kinds): `aim` (`find`, `restore`, `destroy`, `free`, `bind`, `reach`, `learn`, `return`, `protect`, `avenge`, `hunt`, `deliver`, `reconcile`, `prove`), `target_kind` (any node kind or made thing), `obstacle` (`distance`, `guardian`, `riddle`, `rival`, `law`, `concealment`, `danger_of_place`, `cost`), `reward` (`renown`, `power`, `knowledge`, `item`, `standing`, `office`, `cure`, `peace`), `scale` (personal, legendary). `HeroQuestKind.thread` (pursuing an open story arc of incidents) becomes aim `resolve` with target an incident arc; the label never says "thread". The four legendary quests become rows (`dead_star` → aim `restore` × star, `sealed_gate` → aim `free` or `bind` × gate, `archive` → aim `find` × knowledge, `expel_outer` → aim `destroy` or `bind` × outer being).

#### 47.6.3 Creature attacks and tissues

**Current.** `BreathKind` (fire, frost, venom_gas, web, steam), `GazeKind` (terror, petrify, sleep, madness), `TissueMaterial` (flesh, hide, scale, chitin, feather, wood, ice, steam, void_stuff, and others).

**Model.** A creature attack is `delivery` (`breath`, `spit`, `spray`, `emanation`, `gaze`, `voice`, `touch`, `spores`, `bite`, `sting`) × `effect` (a `DamageType` hit, an F30 package, or a grammar pair from 45.3 such as `entangle`, `fear`, `stillness`, `sleep`, `confusion`, `charm`, `drain`) × range × recharge. `web` becomes delivery `spray` with effect `entangle`; `petrify` becomes effect `stillness` with permanence. Tissues are typed by properties (F23: hardness, flexibility, heat resistance, conductivity) with function names (`soft_tissue`, `hide`, `plates`, `shell`, `plumage`, `fibrous`, `frozen`, `vapour`, `mineral`, `metallic`, `crystalline`, `gel`, `energy`, `insubstantial`); the legacy values map once.

#### 47.6.4 Afterlife strata

**Current.** `StratumKind` (paradise, plain, torment, oblivion, warrior_hall, ancestor_hall) carries two culture-specific images.

**Model.** A stratum is typed by axes: `valence` (`reward`, `neutral`, `punishment`, `mixed`), `permanence` (`eternal`, `until_rebirth`, `until_judgement`, `fading`), `admission` (`by_deeds`, `by_faith`, `by_manner_of_death`, `by_line`, `by_rites`, `by_choice`, `all`), `activity` (`rest`, `service`, `struggle`, `reunion`, `learning`, `dissolution`), `ruler` (a god, a spirit, none) and `contact` (whether the living can reach it). Names come from each culture's doctrine. `warrior_hall` and `ancestor_hall` become rows (`by_manner_of_death` × `struggle`; `by_line` × `reunion`) whose names are written by the model for each culture that holds them.

#### 47.6.5 The storyteller's palette

**Current.** Five spontaneous disruptions (beast awakening, raid, comet, plague, claimant) and three recoveries (harvest, peace envoy, healer birth) for every world.

**Model.** Every mechanic registers its own disruption and recovery events in a registry (`engine/storyteller/palette.py`): event kind, the typed causes that must already hold, magnitude, tension weight and the world laws that exclude it. The registry covers every subsystem (war, faith, economy, ecology, disease, climate, cosmos, made minds, networks, replicators, powers, sources, concealment, living craft, gods, outer beings, households, migration, ideology, art) and both directions (disruption, recovery). The storyteller picks among the events whose causes hold in this world, weighted by tension and by how often each subsystem has acted recently, so a world's drama comes from what the world has. The eight legacy kinds become registry rows.

#### 47.6.6 Servitors

**Current.** `ServitorRank` (herald, guardian, angel, fury, psychopomp, choir) mixes functions with culture-specific names.

**Model.** Servitor roles are functions: `messenger`, `guardian`, `agent` (acts in the world for its god), `avenger`, `guide_of_souls`, `worshipper`, `warden` (keeps a place or a prison), `scribe` (keeps records), `judge`. Names and forms come from the god's culture and the seed. Legacy values map once (`herald` → messenger, `angel` → agent, `fury` → avenger, `psychopomp` → guide_of_souls, `choir` → worshipper).

#### 47.6.7 Dimension elements

`DimensionElement` (fire, water, earth, air, void, light, shadow, ice, lightning, metal, wood) is one cultural system of elements used as typed axes. It becomes `dimension_aspects` rows on the same axes as the widened spell forms (45.3), so a dimension's nature is described by forms (`force`, `space`, `time`, `mind`, `emotion`…) as well as by matter; the eleven legacy values remain as rows, and each is read by the cosmos control and ladder phases (wiring the three unread ones, 47.7).

#### 47.6.8 Enum values reach the bias gate

- **`check_prompt_bias.py` scans enum values.** Every value of every enum in `domain/enums` that reaches any LLM-facing text (tool schemas, catalogue lines, context blocks) is split into words and checked by every family (gender, imagery, metaphor, steering, mandates). Cases in `test_prompt_bias_rules.py`: `war_father`, `thread`, `web`, `fury`, `choir`, `angel`, `eye_in_the_sky`.
- **Sibling hunt.** In W47 the scan runs once over all 7160 values; every value it flags is renamed with a legacy mapping in the same change. The labels in the frontend follow the renames.
- **Internal names.** Table and column names that carry metaphors (for example `ThreadRow`, `incident_threads`) never reach the model; their user-facing labels say what they hold ("incident arc").

### 47.7 Every value is read

**Guard.** `scripts/check_enum_values_read.py` fails when a value of any enum in `domain/enums` is not read by the engine, catalog, rules, services, agents, tools or epoch code (labels and API schemas do not count). It runs in the pre-commit gate.

**Wiring of the 83 values unread today:**

| Enum | Unread values | Wiring |
|---|---|---|
| `FoundableFaction` | 17 of 21: `merchant_guild`, `craft_guild`, `priesthood`, `warrior_order`, `noble_council`, `peasant_league`, `scholars_academy`, `secret_society`, `mercenary_company`, `interworld_federation`, `wandering_market`, `void_pirates`, `social_circle`, `crime_family` and the rest | the faction founding path (mortal tool `found_faction`, engine founding by needs and values) offers every kind; each kind maps to its faction kind, goals, membership rules and starting holdings in a total table; `void_pirates` renamed `route_raiders` (function name) |
| `OrderLaw` | `no_outer_dealings`, `share_discoveries`, `keep_secrecy` | magical and gifted orders read each law: dealings with outer beings punished, discoveries shared among members (research speed), secrecy (F53 truth kept by the order) |
| `WordOrder` | `sov`, `vso`, `vos`, `ovs`, `osv` | the grammar engine generates sentences and loanword adaptation by every order; word order drifts by language contact; typology shown in the language drawer |
| `LawArea` | `property`, `fiscal`, `penal`, `military`, `public_health`, `constitutional` | crimes (47.3.1), laws and courts read the area; reforms and law codes group by area; factions lobby by area |
| `ServitorRank` | `fury`, `psychopomp`, `choir` | 47.6.6 roles, each read by the servitor phase (avenger acts on offences to the god, guide of souls moves souls to strata, worshipper adds to the god's standing) |
| `AwakeningTrigger` | `desecration` | desecrating a holy place or a beast's lair can wake beasts there (beast awakening reads it) |
| `Locus` | the 13 school gift loci | the gift loci set aptitude per form for rites and innate powers (W45: born powers draw their form from the loci; rite learning speed reads them); loci names follow the forms (45.3) |
| `JobStatus` | `queued`, `interrupted` | the job runner records queued jobs and interrupted jobs (server restarts), resumes interrupted jobs and shows both states |
| `VehicleStatus` | `engaged`, `building` | vehicles under construction (`building`) and in battle (`engaged`) are set by the shipyard and battle phases and block other uses |
| `PseudoLinkKind` | `in_world` | links between places on one world without a route (overland reach) are drawn in the graph and read by travel |
| `BodyPart` | `left_antenna`, `right_antenna`, `left_branch`, `right_branch`, `left_fin`, `right_fin`, `left_foot`, `right_foot`, `left_foreleg`, `right_foreleg`, `left_midleg`, `right_midleg`, `left_wing`, `right_wing` | body plans (F4.1) for insectoid, arboreal, aquatic, avian and quadruped bodies use these parts; hits, injuries, maiming, prostheses, augments and capacities (flight, swimming, sensing) read them |
| `DimensionElement` | `earth`, `shadow`, `ice` | 47.6.7 |
| `StressComponent` | `population_pressure` | the structural-demographic cycle (F37) reads population against carrying capacity |
| `GoalState` | `dropped` | gods drop goals that become impossible or that their values turn against; the goal phase records it |
| `Manifestation` | `stern` | the dominion manifestation read by peoples' belief memory (stern: fear and obedience) |
| `EpochStepStatus` | `pending` | steps not yet started are marked pending and shown in the epoch progress view |
| `Aversion` | `holy_ground` | beasts with this aversion avoid holy places (beast movement and lair choice) |
| `RouteClosure` | `worn` | routes unused or unmaintained for long close as worn (route decay) |
| `AccountKind` | `inscription` | accounts carved or written on lasting objects survive collapses and are found by excavation |
| `JobKind` | `backup`, `simulation` | the backup job and the engine-only simulation job are registered kinds that the job runner executes |
| `ActionKind` | `chat`, `archive_record`, `convene_council`, `network_repair` | each action writes its ledger row with this kind when the player chats with an agent, archives a record, convenes the council or repairs the network step |

### 47.8 Thin spec sections, completed

Each text below completes the spec 13 section it names. Planned sections are built from it; built sections are audited against it and completed in W47 step 0. 9.2–9.6 are completed in 47.5.

Unless a subsection names its own, every table it adds takes a rules namespace named after the section (`nutrition`, `biases`, `purity`, `ideology`, `prophecy`, `events`, `celestial`, `community_relations`, `honour`, `feuds`, `journeys`, `rifts`, `needs`, `preferences`, `beliefs`, `gatherings`, `storyteller`, `conservation`, `households`, `norms`), and every field it adds gets the full surface set: create, edit, hold and delete levers registered in the action catalog; a drawer section or panel row; a typed context block entry; a labelled value in the Codex and the book; an integrity rule where a reference or range applies; and a legacy fixup that fills it for existing worlds.

#### 47.8.1 F39 Nutrition and diet quality

- **Diet** per household and cohort: shares of energy sources, protein, fats, fresh produce, salt and minerals, preserved foods and special foods, derived from consumption, cuisine (dishes, W23+) and storage; per biology, the nutrient set comes from the people's biology variant (phototrophs need light, lithovores minerals, essence feeders essence, made minds energy).
- **Nutrition score** per mortal and cohort: energy sufficiency plus balance across the biology's nutrient set; deficiencies are typed by nutrient (`NutrientNeed` rows per biology, so no world-specific nutrient is hardcoded).
- **Life-course effects:** childhood nutrition sets adult stature, strength and cognition attributes; adult nutrition sets immunity, fertility, childbirth risk, work output, healing and lifespan; deficiency diseases are F30 packages by nutrient; famine generations are smaller and weaker (L65).
- **Seasonality and storage:** lean seasons, stored food spoilage, preservation methods (salting, drying, smoking, cooling, canning, sealing, vat growth) by technique and climate.
- **Class and inequality:** diet differs by class, caste and household wealth; elite diets and famine foods (W23) are read by health and status.
- **Culture:** food taboos (F35, F41), feasts (F25), fasting (faith), food preferences (F15) and cuisines shape diet within what is available.
- **Policy:** granaries, rationing, provision laws (44.17), food aid (AidKind), fortification of foods by medicine level.
- **Tables and rules:** `diets`, `nutrition_scores`, `nutrient_needs`; namespace `nutrition`.
- **Levers and surfaces:** edit a diet, a score or a biology's nutrient set; household and people "Diet" sections; Codex and book diet tables per people.

#### 47.8.2 F40 Decision biases

- **Biases** (`DecisionBias`): overconfidence, sunk cost, loss aversion, confirmation, recency, groupthink, hostile attribution, optimism, status quo, availability, anchoring, in-group favour, authority deference, scarcity panic, fatalism, risk seeking, planning fallacy, halo (judging a person by one trait), projection (assuming others share one's values).
- **Who carries them:** every deciding actor (mortals, rulers, councils, commanders, gods, made minds by make, beasts by temperament) has bias weights derived from facets, traits, stress, mood, age and culture; councils and selectorates combine their members' biases by influence; made minds' biases come from their make and training, and can be none.
- **Where they act:** every engine decision function applies biases to its option scores: war declaration and peace, sieges and retreats, trade and investment, migration, conversion, alliances, succession choices, scheme targets, belief updates (F22), law adoption, research choices, god goals.
- **Counters:** institutions (councils with dissent, courts, auditors, free press), skills (strategy, administration), values (knowledge) and information (networks, spies) dampen biases; stress, isolation and flattery raise them.
- **Tables and rules:** `bias_weights` (holder × bias); namespace `biases`.
- **Levers and surfaces:** edit any holder's bias weights; "Biases" in the mind section with the effect each had on recent decisions; Codex and book list each holder's strong biases.

#### 47.8.3 F41 Purity and pollution

- **Purity states** (`purity`: holder, state, source, until) under doctrine and culture.
- **Sources of impurity** are typed rows per culture (`impurity_sources`): contact with the dead, birth, bodily fluids, foods, species, professions, outsiders, places, objects, acts, made things or made minds, augments, designed bodies (W44, W46) and breaches of taboo; each culture holds its own set, written from its doctrine and the seed.
- **Effects:** exclusion from rites, temples, gatherings, professions, unions and shared meals until purification; spread of impurity by contact rules; social distance (F18) and opinion (F7).
- **Purification** rows per culture: time, washing, fasting, offering, rite, confession, payment, ordeal; costs and success.
- **Caste and rank:** hereditary purity ranks are culture data combining purity, role norms, union rules, commensality and occupation; movement between ranks by law, wealth, conversion or revolt; castes interact with classes (W42) and with powers and designs where values tie them.
- **Spatial purity:** pure and impure districts and places; sacred space protection (8.6 desecration) reads purity.
- **Change:** reform movements, conversions and contact with other cultures shift purity rules over generations.
- **Tables and rules:** `purity`, `impurity_sources`, `purifications`, `purity_ranks`; namespace `purity`.
- **Levers and surfaces:** edit every row; people "Purity and rank" section; Codex and book tables.

#### 47.8.4 8.5 Ideology, completed reference pass

- **Movements and parties:** ideologies found movements (F32) and parties (where selectorates allow), with programmes (typed laws they press for), leaders, members by class and funding.
- **Constitutions:** revolutions led by an ideology write constitutions (typed: offices, selectorate, rights, law areas), read by the polity system.
- **Emergence:** new ideologies arise from typed causes: crises, new classes, new media (printing, broadcast, networks), contact, revelation, made minds and powers; printing houses, universities and networks raise the base rate.
- **Schisms and synthesis:** ideologies split over tenets and merge by contact; each split and merge is an incident.
- **Ideology and faith:** secular tenets interact with doctrines (alliance, rivalry, absorption); anti-god creeds lower son existence where they spread.
- **Levers and surfaces:** create, edit, split, merge, hold and delete ideologies; ideology drawer with members, programme and spread map.

#### 47.8.5 8.7 Prophecy, completed reference pass

- **Conditions** reference event collections, titles, foresights (45.9, the `foresights` table of W25) and every typed state through the predicate language.
- **Retelling:** prophecies distort as legends do (8.2); each retelling may change a predicate's argument by rule, and believers follow the version they know.
- **Rival prophecies** compete for belief; a fulfilled one raises its seer's tradition, a failed one lowers it.
- **Prophecy as lever:** rulers and cults use prophecies for legitimacy; forged prophecies are forgery (44.14).

#### 47.8.6 8.8 Event, completed reference pass

- **Phases with effects:** every multi-season event has typed phases (onset, peak, aftermath, memory) and per-phase effects on its footprint.
- **Collections:** events are the visible face of event collections; nested events (a siege inside a war) inherit footprint and casualties.
- **Kinds:** the event kind list is the full incident kind list (5.16 and spec 13), so every incident family can be an event.
- **Memory:** events leave memories, accounts (F33), notable years and festivals of remembrance by culture.

#### 47.8.7 10.3 Celestial body, completed

- **Influence by domain** is read through the god's domains and the culture's omen readings; no fixed body-to-meaning mapping exists in our text (spec 13's "moon → divination, comet → fire" is removed; each culture's readings are written from its doctrine and the seed).
- **Cycles** (orbital elements, 10.9) give returns; returns create omens, festivals, dating systems (cycle count) and prophecy conditions.
- **Visibility** by season, latitude and weather; cultures without sky (subterranean, ocean deep) do not read celestial bodies.
- **Sources:** celestial bodies can be loci of power sources (F52, tides).

#### 47.8.8 4.10 Community relations

- **Components:** the relation between two communities is the mean of opinion components (F7) of their populations and rulers, with typed components: trade, kinship, faith, war memory, help received, insult, rivalry, language, values distance.
- **Behaviours:** relations drive migration, assimilation, intermarriage, trade, alliance, ethnic tension inside polities, riots, persecution and secession; diaspora ties (W20) carry relations across distance.
- **Inside polities:** majority and minority relations set rights, offices, representation and unrest.
- **Levers and surfaces:** edit components; relation drawer with components and history.

#### 47.8.9 4.8 Oaths and honour, completed

- **Oaths** of every `OathKind` (widened in 47.4) with typed terms, witnesses (gods, persons, institutions), deadlines and penalties.
- **Honour models** (`honour_model` per culture: `honour` (reputation for keeping word and courage), `face` (standing before others), `dignity` (inner worth), `none`), read by insults, duels, feuds, oaths and suicide or exile customs.
- **Breaking:** honour loss by model, memories, divine wrath where a god witnessed, curses where a natural law binds oaths.
- **Release:** oaths can be released by the recipient, a priest or a god.

#### 47.8.10 5.9 Vendettas and blood feuds

- **Feud state** (`feuds`): sides (houses, communities, peoples), grievance balance, escalation level (`insult`, `blood`, `raid`, `war`), age, mediator.
- **Acts per epoch** by honour, grievance, means and law: raid, ambush, assassination, abduction, property destruction, demand compensation, seek mediation, call allies.
- **Brakes:** compensation law and custom, intermarriage, mediators (priests, rulers, councils), common enemies, exile, law banning feuds, memory decay; a feud ends by settlement, extinction of a side or law.
- **Spread:** allies and kin join by obligation; feuds can become wars and wars can leave feuds.
- **Levers and surfaces:** create, edit, settle, hold, delete feuds; feud drawer with balance and history.

#### 47.8.11 5.11 Interconnections of conflict

The conflict couplings are extended with the subsystems of W44–W47: made minds (soldiers, commanders, command networks), networks (intrusion, outages), surveillance (detection of plots), replicators (weapons, consumption), abundance (war over feedstock and patterns), powers and sources (powered units, contested density), concealment (hidden factions at war), living craft (bioweapons, living units), gods (council resolutions and divine wars). Each coupling is an edge in the interconnection registry.

#### 47.8.12 10.5 Journey

- **Cargo, passengers, convoys and encounters** as spec 13, with encounter kinds as typed rows per route environment (sea, land, air, space, rift, network for minds) instead of a fixed list.
- **Carriers** from 47.2.4; supplies consumed per day; morale and health of passengers; births and deaths on long journeys; generation journeys whose passengers' descendants arrive.
- **Arrival:** passengers become settlers, refugees or invaders by typed outcome; diseases, ideas and languages travel with them.

#### 47.8.13 10.14 Rifts

- **Rift kinds** by cause; **rift control** (sealing works, stabilising works, gates built over rifts, tolls on passage); **rift ecology** (life adapting near rifts); **rift politics** (polities claiming rifts, wars over them, council resolutions); **rift travel** for armies, traders and migrants; **made realm gates** (44.10a) as a kind of rift with a host.

#### 47.8.14 10.16 Interconnections of the cosmic scales

Extended with made realms, interworld networks, replicator lines across systems, sources with cosmic scope, outer beings' plans and the council's cross-world resolutions; each as a registry edge.

#### 47.8.15 F8 Needs and pressures

- **Needs** gain `autonomy`, `knowledge` (curiosity), `beauty`, `rest`, `stimulation`, `continuity` (fear of ending; for made minds and others whose values hold it), `upkeep` (for made and living things), each with sources of satisfaction and the effects of deprivation.
- **Pressures** gain those of 47.4 (`pollution`, `unemployment`, `oppression`, `disease_burden`, `purposelessness`).
- **Biology and make:** which needs exist and their weights come from the biology variant and the mind's make.
- **Satisfaction sources** are typed per need (goods, activities, relations, faith, achievements) and read by economy, gatherings, faith and households.

#### 47.8.16 F15 Preferences

- **Kinds** gain `technology`, `made_thing`, `power`, `source`, `living_line`, `network`, `sound`, `scent`, `texture`, `story_form`, `game`, `place_kind`, `profession`.
- **Formation:** from culture with deviation, experiences, mentors, trauma, addiction and fashion cycles (W26 novelty); preferences can invert after bad experiences.
- **Effects** as spec 13 plus prices of preferred goods, art movements, migration toward preferred places and choice of partners.

#### 47.8.17 F22 Belief state

- **Sources** gain `network`, `foresight`, `mind_reading`, `intrusion`, `surveillance`, `made_mind_report`.
- **Trust in sources** per actor (by past accuracy, F19 reputation and information trust, 44.14) weighs updates.
- **Deception** acts on beliefs through forgery, impersonation, false flags, cover stories and mind powers.
- **Shared beliefs** of communities aggregate members' beliefs and feed public opinion.

#### 47.8.18 F25 Activities and gatherings

- **Kinds** gain those of W42 and W45 (`testing`), plus `exhibition`, `trade_fair`, `summit_of_gods` (the council as a gathering), `network_gathering` (held through a network), `realm_gathering` (held in a made realm), `mourning`, `initiation`, `sport_match`.
- **Activities** of daily life (`activities`: work, rest, worship, learning, play, care, travel, art) take time budgets per class and culture (W29) and satisfy needs.

#### 47.8.19 F27 Storyteller

- **Profiles** (steady, rising, cyclic, chaotic) plus `slow_burn` and `episodic`; per-world target curves editable as points.
- **Palette** from the registry of 47.6.5.
- **Tension** measured per subsystem and per region, so a calm world can still have one region in crisis.
- **Never forcing:** the storyteller changes chances of events whose causes hold; it creates nothing a world's laws exclude.

#### 47.8.20 F28 Conservation and stock-flow invariants

Extended to every new stock: minds (made, copied, merged, divided, ended, states), energy by kind, feedstock and fabricated goods, replicator mass, source density, living line populations and feed, saved states, realm contents, essence across gods and worshippers. Each invariant is a test.

#### 47.8.21 F29 Households and dwellings

- **Household forms** (`HouseholdForm`): nuclear, extended, stem, joint, polygamous, communal, single, institutional (monastery, barracks, dormitory), mixed (born and made members), chosen (non-kin).
- **Dwellings** by housing level (widened with W42), crowding, quality, ownership (owned, rented, granted, squatted), heating and light by energy kind.
- **Care economy** of children, elders, the sick, the maimed and dependent made minds; inheritance within the household by succession customs and union axes (47.3.4).

#### 47.8.22 F35 Social norms and volition

- **Situations** gain `network_space`, `realm`, `workplace`, `council`, `encounter_with_made_mind`, `encounter_with_gifted`, `encounter_with_hidden`.
- **Behaviours** gain `augment_display`, `power_display`, `data_sharing`, `copy_disclosure`.
- **Norm change:** norms drift by generation, contact, law and movements; norm breakers are punished by the community by stance.

#### 47.8.23 F42 Luck, charms and witchcraft, completed

- **Input.** Witchcraft and every other attribution of misfortune read the mishaps of 47.10, the unexplained ones above all; without mishaps there is nothing to attribute.
- **The accused** are chosen by typed social factors only: social distance, envy of the accuser, outsider status, isolation and lack of kin who defend them, eccentric traits, earlier grievances, earlier accusations, and the accuser's beliefs (F22). The spec 13 wording that names a gendered group is removed; no group is a default target.
- **Attributions** (`MishapAttribution`): `chance`, `known_cause`, `witchcraft`, `curse`, `god`, `spirit`, `ancestor`, `omen`, `fate`, `enemy_scheme`, `impurity` (F41), `broken_oath`, `made_mind` (W44), `hidden_people` (W45). Each culture weights them by doctrine, knowledge level and luck beliefs; a community's attribution of a mishap drives its response (rites, offerings, charms, accusations, lawsuits, safety customs, nothing).
- **Luck beliefs** (`luck_beliefs` per culture): lucky and unlucky days of the culture's calendar, numbers, signs, gestures, places, acts and kinds of person, each typed by what it is believed to change; every belief is written from the culture and the seed, never from a list in our text.
- **Charms** are items with a believed effect; where the world makes them real (enchanted, blessed, a natural law, a power), they add a fortune source (47.10.3); otherwise they act through confidence and calm (F14). The player sees which is which.
- **Witch hunts, real casters and ghosts of the wrongly killed** as spec 13 F42.

### 47.9 Spec depth guard

`scripts/check_spec_depth.py` runs in the pre-commit gate over `13-depth-expansion.md` and this file. For every numbered foundation and section it fails unless the text names: the typed attributes or tables, the behaviours, the rules namespace, and the levers and surfaces (or a pointer to the section that holds them). A section that is complete by its nature (a decision, a notation) is listed in the script with the reason. This makes a thin section a failing check instead of a judgement.

### 47.10 Everyday mishaps and fortune

#### 47.10.1 What a mishap is

A mishap is harm or loss that comes from ordinary life: a fall, a burn, a tool slipping, a kick from a beast of burden, a house fire, spoiled stores, a lost purse, a drowned child. It differs from the existing hazards in two ways: it can strike anyone in daily life, not only a worker on a dangerous site, and its cause may be known or unknown to the people around it. Mishaps are driven by **exposure** and shaped by **fortune**; they are never pure dice.

#### 47.10.2 Exposure

Each named mortal (and each cohort in aggregate, 47.10.5) has a per-season mishap rate built from typed exposures, each a rule weight:

| Exposure family | Read from |
|---|---|
| activities | time budgets and activities (F25, W29): work, travel, play, care, worship, learning |
| profession and skill | role and profession (5.13, W42); skill lowers the rate of mishaps of that work |
| age and body | life stage (children and the old by biology), injuries, conditions, fatigue, intoxication, lost senses, pregnancy, augments' integration (44.9) |
| beasts and tools | beasts handled, tools and machines used, vehicles and carriers used (47.2.4) |
| dwelling and place | housing level and quality, crowding, heating and light by energy kind (47.8.21), fire-risk structures (47.1), terrain hazards, water nearby |
| weather and season | weather states, season, darkness, ice |
| law and care | safety laws, guild rules, preparedness (47.4), medicine tier (47.2.3), household care |
| fortune | 47.10.3 |

#### 47.10.3 Fortune

- **Fortune profile** (`fortune_profiles`, one per node; shown in `ThingSections` for every kind of node): `fortune` (−100 to 100), the sum of typed **fortune sources** (`fortune_sources`: blessing, curse, charm made real, divine favour or disfavour, a power of the `fate` form (45.3), a natural law, an oath kept or broken where a law binds oaths, an unlucky or lucky place, a lucky or unlucky day where the world's laws let beliefs shape reality, and the personal streak).
- **Personal streak.** Where the world's fortune law allows it (K.37), each being carries a small streak that drifts each season by a seeded walk and pulls back toward zero, so runs of good and bad fortune happen without any being fated for life.
- **What fortune touches.** Fortune shifts the mishap rate and the tail of the severity draw, and it enters every draw a person's fate depends on: contests and duels, disease symptoms (the existing `lucky` flag in `engine/disease/evolution.py` reads fortune), childbirth, harvests of a household, hunting yields, trade outcomes, discoveries, escapes, and the side luck of a battle (`cast_luck` adds the commander's fortune and the army's divine favour to its die).
- **Cursed misfortune now touches the bearer.** `CurseKind.MISFORTUNE` becomes a negative fortune source on the bearer (and on the household, where the curse says so), in addition to its effect on the home; `line_curse` and `place_curse` (47.4) work the same way on lines and places.
- **Gods and worlds.** Gods grant and withdraw fortune by the divine power grammar (verbs `bless`, `curse`, object fortune); a world's or a place's fortune is a source for everyone in it; the Creator's and gods' own profiles show the fortune they grant rather than draws on themselves.

#### 47.10.4 Mishap kinds, severity and consequences

- **`MishapKind`** (function words): `fall`, `crush`, `cut`, `burn`, `scald`, `drowning`, `beast` (kick, bite, goring, trampling by animals people keep), `tool`, `machine`, `vehicle`, `collapse` (of a dwelling or work), `house_fire`, `poisoning` (food, plants, water, fumes), `choking`, `exposure` (cold or heat), `lightning`, `sport`, `brawl` (existing), `lost_way`; and losses without bodily harm: `stores_spoiled`, `livestock_lost`, `field_blight`, `goods_lost`, `purse_lost`, `theft_suffered`, `tool_broken`; and `near_miss` (fright only, F14).
- **Each kind** has its exposures, a damage type, body region weights by body plan, a severity distribution and the conditions that raise or lower it (a fall from height, a fall on ice). Severity is always drawn through `severity_of` with a per-kind magnitude and the victim's fortune shifting the tail: most mishaps are small, some are grave, a few kill or maim. A crushing fall can break a back, a machine can take fingers, a beast can blind, a house fire can scar a face.
- **Consequences** go through the existing systems: injuries and maiming, conditions, deaths with their causes, memories for the victim and witnesses, lost work and care burdens in the household, debts, mourning, lawsuits and compensation under the culture's liability custom and the polity's labour and safety laws, insurance where it exists (W30), votive offerings and rites of recovery, and changes to preferences and fears (a burned child fears fire).
- **Notable mishaps.** A mishap that strikes a ruler, an heir, a hero, a commander or a seer is an incident with its consequences (a ruler's riding fall can start a succession crisis); its rate follows the same exposures, so it is rare but real.
- **Made things and made minds** suffer their own mishaps through the same model: machine accidents wear or break made things; a made mind's stability (F50) can give it glitches of kind `machine` that harm its work or its seat; living craft (W46) can sicken or turn by temperament.
- **The true cause and the believed cause.** Each mishap records its true causes (the exposures and fortune sources that drove it) and whether the community can explain it (its knowledge and medicine levels against the cause). Unexplained mishaps are the input of F42 attributions; the player always sees both the true and the believed cause.

#### 47.10.5 Cohorts and demography

Cohorts take mishaps in aggregate: per season, accidental injuries and deaths by age band and exposure enter the demography (maimed shares, accidental mortality by age), so a dangerous industry, a careless law or a cold winter shows in the population, and children's and elders' accident deaths exist in every world.

#### 47.10.6 Harm is never fixed by a literal

- **Every harm call draws its severity.** The fourteen calls that pass a literal severity (`economy/extraction.py`, `relations/interactions.py`, `relations/passions.py`, `polity/trials.py`, `law/prisons.py` (two), `mortal/justice.py` (two), `mortal/course.py`, `mortal/acts.py` (three), `mind/inspiration.py`, `phases/mind.py`) pass a magnitude and a severity band from a rule key instead; `severity_of` draws within the band; armour and momentum then apply as for every other harm. Deliberate harm (punishments, ordeals) uses a narrow band set by the punishment's harshness rule.
- **Injury kinds come from the damage type** through `kind_for`, not from a fixed kind, so a cave-in (blunt or crush) can crush or sever, a felling accident can sever, a goring can pierce a vital part. `HAZARD_HARM` gives damage types and magnitudes, not kinds.
- **A fixed kind only where the body makes it so.** A bite is a bite and venom is venom: such kinds are listed in `FIXED_HARM_KINDS` (`catalog/anatomy.py`) with the reason.
- **Totality.** `hazard_chance` and every table keyed by a hazard or mishap kind are `total()` tables, so new hazard kinds (47.2.6) cannot be skipped.
- **Guard.** `scripts/check_fixed_harm.py` fails when a `Harm(...)` or `gain_condition(...)` call passes a literal severity, or passes `kind=` with a kind outside `FIXED_HARM_KINDS`.

#### 47.10.7 Every kind of thing, every kind of world

Fortune and mishaps reach every kind of node through `ThingSections` ("Fortune", and "Mishaps" in the body and history sections). A world without magic can still have fortune (K.37 `personal` or `causes_only`); a world whose beliefs shape reality (a dream world, a law) makes luck beliefs real; a world without bodies for some beings gives them only the losses that fit them.

#### 47.10.8 Tables, rules, surfaces

- **Tables:** `fortune_profiles`, `fortune_sources`, `mishaps` (append-only history: victim, kind, true causes, explained, believed attribution, severity, harm and injury refs, witnesses, consequences), `luck_beliefs`, `cohort_mishap_rates` (derived per season).
- **Rules namespaces:** `mishaps` (rates per exposure, kind magnitudes and bands, notable weights), `fortune` (streak walk, pull to zero, source strengths, effect sizes per draw).
- **Phase:** `mishaps`, in the body stage after activities and weather; cohort rates in demography.
- **God levers:** `fortune:edit`, `fortune:hold`, `fortune_source:create/edit/delete`, `mishap:trigger` (typed, on any node), `mishap:edit/delete`, `luck_belief:*`.
- **Screens:** "Fortune" in `ThingSections` with sources and the streak over time; "Mishaps" timeline in the body and history sections with true and believed causes; people "Luck beliefs"; settlement "Accidents" with rates by exposure.
- **Tools and context:** son `bless_fortune`, `curse_fortune` (through the power grammar); mortal `seek_charm`, `consult_diviner`, `take_care` (a choice that lowers exposure at a cost); context block `fortune` (the actor's fortune as it believes it, and recent mishaps around it).
- **Codex and book:** fortune and mishaps in node entries; accident tables by settlement and people in Records of the Cosmos.
- **Integrity:** fortune within range; every mishap references an existing victim; harm refs exist.
- **Backfill:** every node gets a fortune profile from its existing blessings, curses, cursed items, divine favour and house luck (`engine/faith/souls.py`); no past mishaps are invented.

#### 47.10.9 Couplings, loops and stories

- **Couplings:** C50 Mishaps → body, households, demography, law, faith, beliefs; C51 Fortune → every personal draw.
- **Loops:** L107 (R) unexplained mishaps → witchcraft attribution → accusations → fear and isolation → more attributions (brakes: medicine and knowledge levels, courts that demand evidence); L108 (B) mishaps → safety laws and customs → fewer mishaps (brake: cost of the laws, forgetting after quiet years).
- **Stories:** AS49 **The Fall from the Saddle**: a ruler's riding mishap kills the ruler; an heir is a child; a regency follows (loop L22). AS50 **The Unlucky Season**: a cold season raises mishaps; several stay unexplained in a village whose culture holds a witchcraft belief; an outsider is accused; the trial finds the accused is a real caster in a world with rites, while two earlier accusations were false.

### 47.11 Compliance catalogue (W47)

| Section | Tables and enums | Phases | God levers | Screens | Tools and context | Codex and book | Integrity | Backfill |
|---|---|---|---|---|---|---|---|---|
| 47.1 structures | `STRUCTURE_OWN_EFFECTS`, `StructureEffect` | the phase of each effect | structure levers (existing) with own effects shown | structure drawer "What it does" listing own and fallback effects | tools describe kinds by effects; context lists effects of local structures | structure entries list own effects | every kind has a row | none (effects apply from the next epoch) |
| 47.2 eras and breadth | `technology_profiles`, widened enums | knowledge, industry, body, logistics, extraction | `technology:edit`, enum-typed levers | world and people "Technology" with family levels; logistics panel | genesis families; tool enum lists | technology tables | levels 0–10 | profiles from the world's era and peoples' knowledge levels |
| 47.3 law and customs | crime catalogue, widened punishments and trials, union axes, taxes | justice, households, finance, polity | law, custom and tax levers | justice panel, union customs in culture drawer, tax panel | ruler and mortal tools with full lists | law and custom tables | union axes valid | legacy crimes and union kinds mapped |
| 47.4 sweep | widened enums | their phases | existing levers | existing screens with new values | tool lists | labels | — | renames mapped |
| 47.5 god layer | divine power grammar, signs, attention, standing, covenants, chosen, depictions, pantheon structures, council rules and resolutions, law grammar, outer being plans | divine, dominion, god power, council, horror, doom | power, sign, covenant, chosen, council, law and outer being levers | son, foreign god and Creator drawers; council screen; natural law panel; outer being drawer | son tools for powers, signs, council, laws; context blocks for each | god entries; council records; law tables | grammar parts valid | presets become grammar rows |
| 47.6 typed models | horror events, quests, attacks and tissues, strata, palette registry, servitor roles, dimension aspects | horror, quests, ecology, afterlife, storyteller, mythic, cosmos | levers on every model row | panels of each subsystem | tool enum lists | tables | — | legacy values become rows |
| 47.7 every value read | — | as listed | — | — | — | — | `check_enum_values_read.py` | — |
| 47.8 thin sections | the tables named in each subsection | as named | create, edit, hold, delete for each table | the sections named | context blocks for each | typed sections and Records tables | per table | per table |
| 47.9 guards | — | — | — | — | — | — | `check_acts_as.py`, `check_enum_values_read.py`, `check_spec_depth.py`, `check_fixed_harm.py`, enum scan in `check_prompt_bias.py` | — |
| 47.10 mishaps and fortune | `fortune_profiles`, `fortune_sources`, `mishaps`, `luck_beliefs`, `cohort_mishap_rates`, `MishapKind`, `MishapAttribution` | `mishaps`, demography, every personal draw | fortune, source, mishap and belief levers | "Fortune" in `ThingSections`; "Mishaps" timelines; "Luck beliefs"; "Accidents" | son `bless_fortune`, `curse_fortune`; mortal `seek_charm`, `consult_diviner`, `take_care`; context `fortune` | node entries; accident tables | 47.10.8 | fortune from existing blessings, curses, cursed items and house luck |

**Couplings.** C44 Structures → every subsystem through own effects; C45 Technology families → industry, war, medicine, logistics; C46 Customs → households, inheritance, justice; C47 Divine powers → every subsystem by grammar object; C48 Council → gods and worlds; C49 Storyteller palette → every subsystem.

**Loops.**

| Id | Type | Loop | Brake or accelerator |
|---|---|---|---|
| L102 | R | Printing houses → literacy → ideologies → reforms → schools → more printing | censorship |
| L103 | B | Quarantine houses → slower epidemics → less fear → fewer quarantine houses → next epidemic spreads faster | memory of epidemics |
| L104 | R | Creator attention on a world → awe → essence → more attention possible there | other worlds' neglect |
| L105 | B | Council resolution → violation → escalation → divine war → council strength falls → fewer resolutions | the Creator's veto |
| L106 | R | Bias-driven war (overconfidence) → losses → sunk cost → more war | councils with dissent |

**Acceptance stories.**

1. **AS45 The Press and the Crown.** A printing house raises literacy in a city; an ideology spreads; a movement writes a constitution after a revolution; the polity's offices change.
2. **AS46 The Neglected World.** The Creator's attention leaves a world for many epochs; a son's autonomy rises; an outer being's plan advances through its stages; the Creator returns with a sign of warning and a covenant offer; the people's standing recovers.
3. **AS47 The Divided Council.** A son outlaws a source across worlds by council motion; another son's worshippers depend on it; violations escalate to a divine war; the Creator vetoes the resolution at an attention cost.
4. **AS48 The Lean Generation.** A famine in childhood produces a shorter, weaker adult cohort (F39); levies fall; a rival invades.

### 47.12 Decisions (W47)

Decided on 2026-11-14 on the same delegation as 5.12.

| Id | Question | Decision |
|---|---|---|
| K.33 | Does `ACTS_AS` remain? | Yes, only as a fallback for tables that do not distinguish kinds; every kind has own effects (47.1). |
| K.34 | One technology era or per-family levels? | Per-family levels; the era stays as a summary and as the genesis default when the families are not set. |
| K.35 | How are renamed values handled? | Recorded fixups map every renamed value once; stored overrides and legacy imports map through the same table. |
| K.36 | May the storyteller invent events? | No: it changes the chances of registered events whose causes hold (47.6.5). |
| K.37 | Is fortune real? | A natural law `fortune_law`: `causes_only` (mishaps come only from exposures and typed sources), `personal` (each being also carries a streak), `divine` (fortune is only the gods' favour), `belief_shaped` (the luck beliefs of peoples become real). The seed decides; when silent, `personal`. Bounds keep causes first: the personal streak stays within ±15 and halves back toward zero every four seasons; total fortune is capped at ±100; fortune shifts any single draw by at most ±20% of its base and the severity tail by at most one band. Fortune colours a life; exposure and choices decide it. |
| K.38 | Can a mishap kill or maim a named mortal? | Yes, by drawn severity like any harm; notable mishaps are rare because exposures and care keep them so, not because they are forbidden. Default rates (rules `mishaps.*`, balance-banded in 5.12a): an adult named mortal of ordinary exposure has about one small mishap per eight seasons, one grave mishap per eighty and one deadly mishap per four hundred; children and the old of their biology double the rate; dangerous work triples it; skill, care and safety law reduce it. |

---

## Part 8. W48 — Typed kinds: every concept a world can define in its own terms

### 48.0 Scope and the measurement behind it

On 2026-11-14 every enum of `domain/enums` (729) was classified by script (`classify.py`, results in the session scratchpad and reproduced in Appendix 48.A):

- **514** enums name kinds of things in the world (the rest are process states, outcomes and bookkeeping).
- **214** of the 514 (42%) have an **authored layer**: a table whose rows have names and use the enum as their category, so a world can hold its own named kinds (unit types, equipment models, vehicle types, building types, dishes, world materials, species, diseases, art forms, rites, traditions, laws).
- **300** have none: the world can only pick from a fixed list.
- **281** of the 514 have **no property catalogue**: their values differ by label and scattered branches, not by typed properties.
- **Parallel taxonomies** describe one concept twice (housing, abilities, servitors, factions, commodities, jobs, sexes, funeral customs, diets).
- **Values that carry images or gender** reach the model through tool enum lists: `Preservation.salted`, `LandAct.salt_soil`, `ScarKind.salted_earth`, `SoilKind.salt` and `SoilKind.bone` (the very motifs that once poisoned every generation), `TravelMethod.river_of_dead`, `cosmic_mount`, `swallowed`, `MaterialOrigin.dead_star`, `leak_crystal`, `god_remains`, `ContestStake.bride`, `AchievementKey.fathers_hand`, `LegendArchetype.return_of_the_king`, `ApocalypseVariant.twilight_of_gods`, `TitleRank` (`county`, `duchy`), `MortalRole.knight`, `ClergyOffice.monk` and `inquisitor`, `TraditionKind.siesta`, `war_dance`, `scar_rite`, `ContestKind.flyting`, `CircleKind.drinking_hall`, `PerkKind` names (`silver_tongue`, `iron_nerve`), `PhenomenonKind` and `BeingKind` scenes.
- **Correction of the first report:** `society.Commodity` (food, ore, goods) is a summary statistic of communities (55 uses); the detailed stock is `CommodityKind` (35 values, 186 uses). The limit is that the 35 are closed and no world can define a good of its own.

W48 gives every world-content concept the two-layer model, gives every content enum a property catalogue, unifies the parallel taxonomies, renames every value that carries an image or a gender, and adds guards so none of this can come back. Appendix 48.A lists each of the 300 enums without an authored layer with its decision; Appendix 48.B lists the authored-layer enums whose categories W48 widens or renames.

**Ownership.** W29 (intoxication cultures, naming, body modification, cuisines and taverns), W26 (games, art markets) and W47 (customs, eras) touch some of these concepts. The texts here are their complete typed specification; whichever wave runs first builds it (0.7).

### F57. Authored kinds (the two-layer model)

1. **Category enum.** Each concept has one category enum with function words that the engine needs to tell kinds apart. It is complete for its function and carries no images, cultures or genders.
2. **Authored kinds.** Each concept has a typed table of kinds (`<concept>_kinds`): `id`, `world_id`, `origin_node_id` (the people, culture, polity, faction, god or mortal that made it), `name`, `description` (written by the model from the seed, the culture and the typed fields), `category`, the concept's **typed properties** (columns, not JSON), `derived_from_id` (a kind it developed from), `created_epoch`, `retired`, `locked`.
3. **Where kinds come from.** The genesis output writes starting kinds for every people from the seed (5.2); awakening and deepening add kinds when peoples appear or grow; mortals invent kinds (mortal tool `invent_kind`, by skill, technique and need); sons create, bless or forbid kinds (son tool `shape_kind`); the god creates and edits any kind through levers; kinds spread by culture exchange, trade, conquest and migration, change into derived kinds, and retire when nobody uses them.
4. **How the engine reads them.** Every phase reads the category and the typed properties; names and descriptions are only shown and given to the model. A kind can do anything its properties say and nothing they do not.
5. **Legacy values become built-in rows.** The current values of each closed enum become built-in kinds (category plus properties) available to every world, so nothing existing is lost; the model names a world's own kinds beside them.
6. **Shared machinery.** Authored kinds reuse the made-kinds machinery of W23+ (`engine/phases/made_kinds.py`, `services/player/made_kinds.py`, the made-kinds screens), extended to every concept here.
7. **Rules namespace** `kinds` (invention rates, spread rates, retirement), plus each concept's own namespace below.

### 48.1 Goods

**Category** `GoodCategory`: `grain`, `root_and_tuber`, `vegetable`, `legume`, `fruit`, `nut_and_seed`, `oil_and_fat`, `sweetener`, `seasoning`, `mineral_seasoning`, `meat`, `fish_and_seafood`, `dairy`, `eggs`, `insects`, `fungi`, `algae`, `offal_and_blood`, `fodder`, `drink_base`, `stimulant`, `intoxicant`, `medicine`, `fibre`, `textile`, `hide_and_leather`, `timber`, `fuel`, `ore`, `metal`, `stone`, `clay_and_ceramic`, `glass`, `chemical`, `dye_and_pigment`, `scent_material`, `reagent`, `tools`, `weapons`, `armour`, `garments`, `furnishings`, `containers`, `instruments`, `ornaments`, `books_and_records`, `machines`, `parts`, `energy_store`, `data`, `living_goods`, `sacred_goods`, `luxuries`, `livestock`, `mounts`.

**Properties** (`good_kinds`): category; source (species, material, deposit, production method or making); perishability (seasons); bulk and weight; base value; nourishment per nutrient class of F39 and per biology; processing inputs and outputs (chains of 6.3 and F24); cargo class (47.2.4); preference kind (F15); tax and tariff class; legality; taboo hooks (F35, F41); sacred and prestige weights.

**Behaviours.** Markets, stocks, trade, tariffs, diets, cuisines, gifts, tribute, loot and preferences all read good kinds; a people's goods follow its species, materials, deposits and techniques, so a world of fungus eaters, of algae farmers or of machine peoples has goods of its own. `CommodityKind`'s 35 values become built-in goods; `society.Commodity` stays the summary statistic, computed from categories.

### 48.2 Food, cuisine and drink

**Dishes** (extending `dishes`): a dish has **steps** (`dish_steps`: order, `CookingMethod`, duration), **ingredients** by good kind with a role (`IngredientRole`: `base`, `protein`, `fat`, `seasoning`, `garnish`, `binder`, `liquid`, `leavening`, `preservative`, `colouring`), a **flavour profile** (numeric axes `sweet`, `sour`, `saline`, `bitter`, `savoury`, `pungent`, `cooling`, `numbing`, `smoky`, `fermented`; a biology may perceive other axes, set per biology), texture, serving temperature, **meal slot** (`MealSlot`: `daily_meal`, `snack`, `feast`, `rite`, `ration`, `remedy`, `travel_food`, `famine_food`), preparation skill and time, utensils (furnishing kinds), biology compatibility (diet and biochemistry), nutrition (F39), keeps, prestige and taboo flags. `DishCourse` maps to meal slot and ingredient roles.

**`CookingMethod`** gains `infused`, `distilled`, `churned`, `sprouted`, `alkali_treated`, `cultured` (by microbes), `cured_with_mineral`, `aged`, `extruded`, `pressure_cooked`.

**Cuisines** (`cuisines`, authored per culture): staples, signature methods, flavour signature (the mean of its dishes), etiquette rows (F35 norms at meals), meal times (time budgets), feast customs, taboo foods, and the cuisine's spread and fusion by contact.

**Drinks** (`drink_kinds`): category `DrinkCategory` (`water`, `infusion`, `fermented`, `distilled`, `pressed`, `milk_based`, `broth`, `stimulant_brew`, `intoxicant`, `medicinal`, `ritual`, `synthesised`), strength (intoxication), stimulation, nourishment, **water safety** (boiled, fermented or treated drinks lower waterborne disease), keeps, prestige, social role (`DrinkRole`: `daily`, `hospitality`, `feast`, `rite`, `medicine`, `trade`, `bond_making`), dependence package (F30), legality. Drinking places (taverns, inns, circles) and drinking customs read them.

### 48.3 Clothing, adornment, colour and scent

**Garments** (`garment_kinds`): category `GarmentCategory` (`body_wrap`, `upper`, `lower`, `full_body`, `outer_layer`, `head`, `face_covering`, `feet`, `hands`, `undergarment`, `fastening`, `ornament`, `uniform`, `ritual_dress`, `work_protection`, `environment_suit`, `body_marking` (paint and marks, W29)), materials (world materials), layer, warmth, protection, climate fit, cost, **status signal** (class, rank, office, faith), **modesty coverage** (read against the culture's norms), occasions, **wearing rule** (`WearingRule`: `anyone`, `by_role`, `by_class`, `by_age`, `by_faith`, `by_rank`, `by_gender_as_the_culture_holds`; the last is culture data only, never a default), colours, fashion cycle (novelty).

**Behaviours.** Dress codes (F35), sumptuary laws, uniforms of armies, offices, guilds and orders, fashion diffusion through prestige and contact, climate exposure (47.10 mishaps and exposure harm), textile and dye demand, identity facets (F43), emblems on dress, theft and gifting of fine dress.

**Colours** (`colour_terms` per language: basic colour terms by the language's stage, read by naming and description), **colour meanings** per culture (typed: `mourning`, `rank`, `sacred`, `danger`, `joy`, `faction`, `none`, written from culture and seed), and **colour availability** from dyes and pigments (rare colours carry prestige).

**Scents** (`scent_kinds`): category `ScentUse` (`burned`, `worn`, `anointed`, `household`, `ritual`, `medicinal`, `signal` (for peoples with scent language)), materials, prestige, uses in rites and trade.

**Emblems** (`emblem_systems` per culture: `EmblemSystem`: `heraldry` (the existing heraldic enums), `seal`, `banner`, `totem`, `badge`, `monogram`, `mark`, `glyph`), so heraldry is one emblem system among many.

### 48.4 Household goods, tools, instruments, games and substances

- **Furnishings** (`furnishing_kinds`): category `FurnishingCategory` (`sleeping`, `seating`, `storage`, `table`, `lighting`, `heating`, `cooking_vessel`, `tableware`, `household_textile`, `decoration`, `sanitation`, `shrine`), materials, comfort, prestige; dwelling quality, household wealth and household decisions (`sell_furnishing`) read them.
- **Tools** (`tool_kinds`): category `ToolCategory` (`cutting`, `digging`, `lifting`, `measuring`, `writing`, `fire_making`, `crafting`, `medical`, `navigation`, `computing`, `farming`, `fishing`, `hunting`), craft and skill bonuses, quality, wear (47.10 mishap exposure).
- **Instruments and music** (`instrument_kinds`: category `InstrumentCategory`: `string`, `wind`, `percussion`, `voice`, `keyboard`, `electronic`, `made`, `living`; range, loudness, ensemble role) and **musical traditions** (`music_traditions`: scale system, tuning, rhythm, ensemble forms, occasions), read by art forms, rites, gatherings and renown.
- **Games and sports** (`game_kinds`: category `GameCategory`: `board`, `chance`, `card`, `ball`, `racing`, `combat_sport`, `athletic`, `hunting_sport`, `wit`, `team`, `spectacle`, `gambling`, `network`; skills used, chance share, violence, team size, betting, spectators), leagues and fan factions (W26), gatherings (`sport_match`), renown of champions, injuries (47.10).
- **Substances** (`substance_kinds`: category `SubstanceCategory`: `stimulant`, `depressant`, `hallucinogen`, `analgesic`, `euphoriant`, `power_substance` (45.7), `medicinal`; effect packages (F30), dependence, legality, ritual use, trade value), read by intoxication cultures (W29), crime (47.3.1), health and faith.

### 48.5 Money, materials, preservation and the uses of living things

- **Money.** `currencies` gains `form` (`MoneyForm`: `coin`, `commodity`, `token`, `paper`, `ledger`, `network`, `reputation`, `energy`, `essence_backed`, `labour_hours`, `gift_tally`), `backing` (`metal`, `commodity`, `decree`, `trust`, `source`), convertibility and issuer kind; inflation, counterfeiting, debasement, intrusion (network money) and trust follow the form. The `metal` column applies only to coin and commodity money.
- **Building materials.** `BuildMaterial` (timber, stone) is replaced by world materials with structural properties (F23), so any material a world holds can build.
- **Preservation.** `Preservation` (none, salted, iced, magic) becomes `PreservationMethod`: `none`, `drying`, `smoking`, `curing`, `pickling`, `fermenting`, `chilling`, `freezing`, `sealing`, `canning`, `irradiating`, `by_working`, `living` (W46); each with a keeping factor, inputs and technique. `salted` maps to `curing`.
- **Uses of living things.** `YieldProduct` (13), `PlantYield` (10), `SpeciesUse` (9) and `HerdTraining` (3) are unified as **species products and roles** (`species_products`: species, good kind, part or process, yield; `species_roles`: species, `AnimalRole` (`draft`, `mount`, `dairy`, `fibre`, `meat`, `guard`, `hunting`, `war`, `companion`, `sacred`, `pest_control`, `messenger`, `sensing`, `entertainment`), training needed). Products derive from the species' generated anatomy and its biology.
- **Production methods.** `MethodKind` (53) becomes authored production methods with family, typed inputs, outputs, hands, energy and technique (F24, 44.17, 46.12); the 53 become built-in rows.

### 48.6 Society

- **Professions** (`profession_kinds`): category `ProfessionCategory` (`food_production`, `crafting`, `trade`, `transport`, `care`, `healing`, `learning`, `faith`, `rule_and_administration`, `law`, `war`, `security`, `art_and_entertainment`, `service`, `building`, `extraction`, `science_and_engineering`, `information`, `making_minds`, `living_craft`, `magic`, `exploration`), skills, tools, structures, class, guild, prestige, income, mishap exposures (47.10). The 25 `Profession` values and the 12 `Job` values become built-in rows (48.9).
- **Narrative roles.** `MortalRole` keeps its function list with function names (`knight` → `sworn_warrior`); a culture's own names for roles come from its language.
- **Classes and ranks.** `SocialClass` stays the engine's class set; cultures author `rank_kinds` (names, privileges, duties, mobility, dress, purity rank of F41) over it.
- **Titles.** `TitleRank` (lordship, county, duchy, kingdom, empire, see, archsee, high_seat, captaincy, guildmastership) becomes `TitleTier`: `local`, `district`, `regional`, `realm`, `imperial`, `faith_local`, `faith_high`, `faith_supreme`, `military`, `guild`; every title's name comes from its culture's language; legacy values map once.
- **Clergy.** `ClergyOffice` (high_priest, priest, monk, inquisitor) becomes authored clergy roles per faith over `ClergyFunction`: `leader`, `celebrant`, `teacher`, `ascetic`, `guardian_of_doctrine`, `healer`, `seer`, `keeper_of_sites`, `missionary`, `judge`, `scribe`.
- **Organisations.** `FactionKind` (27) and `FoundableFaction` (21) are unified as authored **organisation kinds** (`organisation_kinds`) on typed axes: `purpose` (`trade`, `craft`, `faith`, `war`, `learning`, `rule`, `crime`, `mutual_aid`, `leisure`, `secrecy`, `politics`, `exploration`, `making`, `care`), `ownership` (`members`, `shareholders`, `founder`, `state`, `faith`, `none`), `membership` (`open`, `by_trade`, `by_birth`, `by_oath`, `by_invitation`, `by_purchase`, `by_power`), `scale` (`FactionScale`), `legal_form` (`chartered`, `licensed`, `customary`, `outlawed`, `secret`), `governance` (`leader`, `council`, `assembly`, `hereditary`, `made_mind`); companies (44.15) are organisation kinds with a company profile; the 27 become built-in rows with function names (`void_pirates` → `route_raiders`).
- **Bound labour.** `LabourRegime` (indenture, peonage) gains `debt_bondage`, `levy_labour`, `bound_apprenticeship`, `contract_servitude`, `penal_labour`, `made_mind_servitude` (44.6), each with entry, terms, exit paths (`ManumissionPath`) and the laws that allow it.
- **Spies and sieges.** `SpyCover` is any profession kind; `SiegeWork` gains `bombardment`, `sapping`, `blockade_lines`, `air_assault`, `network_attack`, `rite_breach`.
- **Ship crews.** `CrewStation` (gunners, topmen, marines, officers, rowers) gains `pilots`, `engineers`, `sensor_operators`, `medics`, `handlers` (living vessels), `link_operators` (mind links), read per vehicle family.
- **Kinship.** Kinship enums keep their typological options with neutral, side-based names consistent with 47.3.4 (`KinshipDescent`: `through_first_line`, `through_second_line`, `bilateral`, `double`, `ambilineal`; `ResidenceRule`: `with_first_family`, `with_second_family`, `new_household`, `with_kin_of_the_first_line`; `MarriagePayment`: `to_one_family`, `from_one_family`, `service`, `none`; `MarriageCustom` merges into the union axes of 47.3.4; `InheritanceCustom` `matrilineal` → `through_second_line`; `RoleEligibility` and `GenderRule` keep their options as culture data with `any` as the default); new: **kin term systems** (`KinTermSystem`: `generational`, `lineal`, `bifurcate_merging`, `bifurcate_collateral`, `cross_parallel`, `descriptive`), **adoption and fosterage** (`AdoptionKind`: `heir`, `ward`, `foster`, `sponsor`, `blood_bond`, `chosen_kin`). Which side is "first" and "second" is the culture's own naming, never a gender default.
- **Sexes and reproduction.** `Sex` (2) and `MortalSex` (3) are unified on the reproductive system of the biology (`ReproductiveSystem`): each biology declares its sexes or none; `other` is always available; no value is a default.

### 48.7 Culture

- **Traditions.** `TraditionKind` becomes `TraditionFunction`: `festival`, `fast`, `rite_of_passage` (with stage: `birth`, `naming`, `coming_of_age`, `union`, `elderhood`, `death`), `taboo`, `offering`, `pilgrimage`, `hospitality`, `duel_custom`, `mourning`, `seasonal_rite`, `martial_display`, `body_marking`, `ancestral_rite`, `rest_custom`, `vigil`, `gift_custom`, `purification`, `commemoration`, `competition`; traditions stay authored entities with names from their culture; legacy values map (`siesta` → `rest_custom`, `war_dance` → `martial_display`, `scar_rite` → `body_marking`, `ancestor_feast` → `ancestral_rite`, `night_vigil` → `vigil`).
- **Art.** `ArtMedium` (12) and `ArtDiscipline` (9) become `ArtMode`: `verbal`, `musical`, `movement`, `flat_image`, `solid_image`, `built`, `worn`, `culinary`, `scent`, `light`, `recorded`, `interactive`, `landscape`, `body`, `ritual_performance`, `textile_image`, `made_mind_art`; art forms stay authored entities; legacy media map (`fresco` → `flat_image`, `tapestry` → `textile_image`, `epic_poem` → `verbal`).
- **Ideas and tenets.** `IdeologyTenet` (13), `IdeaKind` (16) and cult `TenetKind` keep their values as built-in rows; ideologies, ideas and doctrines author new tenets with typed value deltas (F5 axes) and typed rules (what they demand, forbid and favour).
- **Fears, dreams, goals and wants.** `FearKind` becomes fears over a typed object (any node kind, need, place kind or event kind) with strength; `DreamReading` becomes readings by culture (subject × valence); `LifeGoal` and `WantKind` become aim × object (the quest grammar of 47.6.2); built-in values remain as rows.
- **Perks.** `PerkKind` values are renamed to function names (`silver_tongue` → `persuasive`, `iron_nerve` → `steady_under_fear`, `swift_blade` → `fast_striker`, and every other image name) with their effects unchanged.
- **Legends.** `LegendArchetype` takes function names (`return_of_the_king` → `return_of_a_ruler`, `lost_paradise` → `lost_golden_age`, `flood` → `world_disaster`) and gains `founding`, `exile`, `transformation`, `bargain`, `sacrifice`, `rivalry`, `discovery`, `deception`, `union`, `ascent`, `fall`.
- **Contests and circles.** `ContestKind.flyting` → `insult_contest`; `ContestStake.bride` → `union`; `CircleKind.drinking_hall` → `drinking_circle`.
- **Aesthetics.** `Aesthetic` (austere, ornate, geometric, natural, macabre, celestial) becomes axes per culture: ornament level, geometric against organic, colour use, scale, symmetry, motif sources (typed node kinds), so a culture's style is described by its own values.

### 48.8 Nature and the cosmos

- **Soil.** `SoilKind` takes property names: `thin`, `loam`, `clay`, `sand`, `volcanic`, `peat`, `saline` (was `salt`), `tephra` (was `ash`), `crystalline`, `calcareous` (was `bone`), plus `laterite`, `permafrost`, `regolith`, `artificial`.
- **Scars and land acts.** `ScarKind.salted_earth` → `made_barren`; `LandAct.salt_soil` → `make_saline`.
- **Phenomena, cosmic beings, apocalypses, sky events, stars and material origins.** `PhenomenonKind`, `BeingKind`, `ApocalypseVariant`, `SkyEventKind`, the fantastic `StarType` values and `MaterialOrigin` become typed models in the style of 47.6.1: a phenomenon is target subsystem × effect × scope × persistence; a cosmic being is scale × agenda × substrate (F50) × manifestation sense; an apocalypse is cause × scope × what survives; a material origin is a source node kind (a dead god, a star, a beast, a rift, research, a god's gift). Legacy values become rows with the model writing names; `twilight_of_gods` → `fall_of_gods`.
- **Traits of peoples, houses and creatures.** `NaturalTrait` (10), `HouseTrait` (6) and `CreatureTrait` (32) become typed traits: body function or capacity × effect × strength (F30 packages where they change the body), authored per species, people or house; legacy values become rows (`giant_blooded` → size trait, `god_blooded` → divine descent trait).
- **Temperament.** `Temperament.abductor` → `seizes_prey`.
- **Travel methods and journey events.** `TravelMethod` (15) becomes a typed model: medium (`space`, `dimension`, `dream`, `death`, `divine`, `network`, `body` (carried inside a being)) × mechanism (`gate`, `fold`, `sail`, `mount`, `bridge`, `current`, `carrier_being`, `orbit`) with names by model; legacy values become rows (`river_of_dead` → medium death × current). `JourneyEventKind` follows the encounter model of 47.8.12.
- **Divine offices and realms.** `CosmicOffice` (6) and `MythicRealm` (4) become authored offices and realms over function categories (`OfficeDuty`: `the_dead`, `thresholds`, `the_sky`, `oaths`, `messages`, `the_hunt`, `judgement`, `memory`, `making`, `healing`; `RealmFunction`: `seat_of_gods`, `abode_of_dead`, `dream`, `sacred_site`, `prison`, `garden`); `Miracle` and `Disaster` follow the divine grammar (47.5.1).

### 48.9 One concept, one taxonomy

| Concept | Parallel enums | Unified into |
|---|---|---|
| housing | `HousingLevel` (11), `DwellingKind` (10) | `HousingLevel` for the ladder, `DwellingKind` as authored dwelling kinds over it |
| mind and body abilities | `Ability` (6), `Attribute` (19), `Stat` (9, sons) | `Attribute` for mortals and made minds; `Stat` for gods; `Ability` values map to attributes |
| servitors | `ServitorRank` (6), `ServitorRole` (5) | servitor roles of 47.6.6 |
| organisations | `FactionKind`, `FoundableFaction` | organisation kinds (48.6) |
| goods | `society.Commodity`, `CommodityKind` | good kinds (48.1); the summary computed from categories |
| work | `Job` (12), `Profession` (25) | profession kinds (48.6); `Job` becomes the cohort's work category |
| sexes | `Sex` (2), `MortalSex` (3) | reproductive systems (48.6) |
| funerals | `FuneralCustom` (9), `FuneralRite` (5) | `FuneralCustom` as categories, rites as authored traditions |
| diets | `Diet` (9, species), `FolkDiet` (9, peoples) | one `Diet` for species and peoples |
| marriage | `MarriageKind`, `MarriageCustom`, `MarriagePreference`, `MarriagePayment` | the union axes of 47.3.4 |
| art | `ArtMedium`, `ArtDiscipline` | `ArtMode` (48.7) |
| plant and animal uses | `PlantYield`, `YieldProduct`, `SpeciesUse`, `HerdTraining` | species products and roles (48.5) |

`catalog/concepts.py` (48.11) names one canonical enum per concept, so a second one cannot be added unnoticed.

### 48.10 Every value defined

Every content enum gets a **property catalogue**: a `total()` table in `catalog/kinds/` giving each value its typed properties (what it costs, what it needs, what it does, what reads it), so values differ by data, not by scattered branches. Of the 281 content enums without one, 250 need one (140 in Appendix 48.A, 110 in Appendix 48.B); the other 31 are bookkeeping and record kinds, marked as such in Appendix 48.A.

### 48.11 Guards

- **`catalog/concepts.py`** declares every enum of `domain/enums` as one of: `authored` (it has an authored kind table), `closed` (with the reason from Appendix 48.A), or `process` (states, outcomes, bookkeeping), and names the canonical enum for each concept.
- **`scripts/check_kind_layers.py`** fails when an enum is undeclared, when an `authored` enum has no kind table with typed properties, levers, tools and screens, or when two enums claim one concept.
- **`scripts/check_kind_definitions.py`** fails when a content enum has no property catalogue.
- **The enum scan of `check_prompt_bias.py`** (47.6.8) covers authored kind names and descriptions written by our templates as well as enum values.

### 48.12 Generation, surfaces, Codex and book

- **Genesis and growth.** The genesis output writes each people's starting kinds for goods, dishes, drinks, garments, colours, scents, furnishings, tools, instruments, games, substances, money, professions, ranks, titles, clergy roles, organisations, traditions, art modes, tenets and emblems from the seed; awakening, deepening and invention add more; the model receives the category and typed properties and writes names and descriptions with no example lists.
- **Every kind of thing.** Each people, culture, polity and organisation shows the kinds it holds; every node's `ThingSections` shows "Ways of life": the kinds it makes, uses, favours or forbids (for gods: the kinds they bless or forbid; for worlds and stars: the kinds found there).
- **Screens.** A **Kinds library** (every concept, filters by world, people and category, show-more paging, lineage of derived kinds, where each kind is used, create, edit, hold and delete with every property editable); a **Ways of life** section in people, culture and settlement drawers (cuisine, drink, dress, crafts, music, games, money, professions, ranks, traditions); atlas layers for the spread of cuisines, dress, money forms and organisations.
- **Codex and book.** Each people's entry gets a designed "Ways of life" chapter with labelled tables per concept; Records of the Cosmos gets the world's kind registry by concept. Nothing is truncated.
- **Context and tools.** Context block `ways_of_life` (the actor's own kinds and those it meets); mortal tools `invent_kind`, `adopt_kind`, `forbid_kind` (rulers and cults); son tool `shape_kind`; every tool lists every category value.
- **Legacy.** Recorded fixups create the built-in rows, map every renamed value (Appendix 48.B and the renames above), unify the parallel taxonomies, and give existing worlds' peoples kinds from what they already hold (their goods, dishes, traditions, art forms, factions and titles).

### 48.13 Compliance catalogue (W48)

| Section | Tables | Phases | God levers | Screens | Tools and context | Codex and book | Integrity | Backfill |
|---|---|---|---|---|---|---|---|---|
| F57 authored kinds | `<concept>_kinds` per concept | made kinds, culture exchange, trade | `kind:create/edit/delete/hold`, `kind:spread`, `kind:retire` per concept | Kinds library | `invent_kind`, `adopt_kind`, `forbid_kind`, `shape_kind`; `ways_of_life` | Ways of life chapters; kind registry | category valid; properties in range; derived kind exists | built-in rows from legacy values |
| 48.1 goods | `good_kinds` | markets, stocks, trade, diet | as F57 | library, market screens | trade tools list goods by kind | goods tables | sources exist | 35 commodities |
| 48.2 food and drink | `dish_steps`, `dish_ingredients` (roles), `cuisines`, `drink_kinds` | cuisine, nutrition, gatherings, epidemics (water safety) | as F57 | cuisine and drink sections | as F57 | cuisine chapters | ingredients exist | dishes keep their method as step one |
| 48.3 dress, colour, scent, emblems | `garment_kinds`, `colour_terms`, `colour_meanings`, `scent_kinds`, `emblem_systems` | culture, norms, economy, exposure | as F57 | dress section, emblems | as F57 | dress chapters | — | heraldry as one emblem system |
| 48.4 household, tools, instruments, games, substances | `furnishing_kinds`, `tool_kinds`, `instrument_kinds`, `music_traditions`, `game_kinds`, `substance_kinds` | households, production, culture, gatherings, health | as F57 | library sections | as F57 | chapters | — | items of these classes |
| 48.5 money and production | `currencies.form`, `currencies.backing`, `species_products`, `species_roles`, production methods | finance, economy, ecology | currency and method levers | finance and ecology screens | as F57 | tables | coin and commodity money only use metal | metal coins; 53 methods; species uses |
| 48.6 society | `profession_kinds`, `rank_kinds`, title tiers, clergy roles, `organisation_kinds`, kin terms, adoption | society, polity, faith, factions, households | as F57 | society, faith and faction drawers | as F57 | chapters | — | legacy values mapped |
| 48.7 culture | tradition functions, art modes, tenets, fears, readings, aims | culture, mind | as F57 | culture drawers | as F57 | chapters | — | legacy values mapped |
| 48.8 nature and cosmos | the typed models named | ecology, cosmos, travel, mythic | model levers | cosmos and ecology screens | tool lists | tables | — | legacy values become rows |
| 48.9–48.11 unification and guards | `catalog/concepts.py`, `catalog/kinds/*` | — | — | — | — | — | `check_kind_layers.py`, `check_kind_definitions.py` | parallel enums mapped |

**Couplings.** C52 Kinds → every subsystem through their typed properties; C53 Culture exchange → kinds spread and fuse.

**Loops.** L109 (R) a prestigious kind (a dish, a dress, a game) → adoption by neighbours → more prestige → wider spread (brake: novelty decline, W26); L110 (B) a kind tied to a scarce good → price rise → substitution by a derived kind.

**Acceptance stories.** AS51 **The Borrowed Feast**: two peoples trade; one adopts the other's drink kind for hospitality; a derived drink appears; its water safety lowers a waterborne disease. AS52 **The Dyed Rank**: a rare dye makes a colour prestigious; a sumptuary law restricts it to a rank; smuggling of the dye follows; a revolt tears the law down.

**Decisions.**

| Id | Question | Decision |
|---|---|---|
| K.39 | Do legacy values remain? | Yes, as built-in kinds every world can use; worlds add their own beside them. |
| K.40 | Who names authored kinds? | The model, from the seed, the culture and the typed fields; the engine never reads names. |
| K.41 | Are kinship and union options with gendered meanings removed? | No: they stay as culture data under neutral, side-based names; no gender is ever a default. |


### Appendix 48.A — The 300 enums without an authored layer

Generated from the enum classification of 48.0. "Catalogue" marks the enums that need a property catalogue (48.10).

| Enum | Module | Values | Decision | Catalogue |
|---|---|---|---|---|
| `ActionKind` | action | 256 | process: engine bookkeeping or record kind | has one |
| `ActionPolarity` | action | 3 | process: engine bookkeeping or record kind | — |
| `CureKind` | affliction | 5 | widened (47.4) | needed |
| `Transmission` | affliction | 10 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `Visibility` | affliction | 3 | process: engine bookkeeping or record kind | — |
| `AgentKind` | agent | 2 | process: engine bookkeeping or record kind | — |
| `CouncilCaller` | agent | 2 | process: engine bookkeeping or record kind | — |
| `CouncilVote` | agent | 3 | process: engine bookkeeping or record kind | — |
| `MessageIntent` | agent | 13 | process: engine bookkeeping or record kind | — |
| `PendingJobKind` | agent | 2 | process: engine bookkeeping or record kind | — |
| `PrayerRequest` | agent | 7 | process: engine bookkeeping or record kind | — |
| `AidKind` | agrarian | 3 | widened (47.4) | needed |
| `CommonsKind` | agrarian | 3 | widened (47.4) | needed |
| `PerennialKind` | agrarian | 4 | widened (47.4) | needed |
| `RebuildCause` | agrarian | 5 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `RebuildPlan` | agrarian | 2 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `BodyBuild` | body | 4 | closed: physical or typological set, complete | has one |
| `BodyFunction` | body | 15 | closed: physical or typological set, complete | has one |
| `BodyPart` | body | 50 | closed: physical or typological set, complete | needed |
| `BodyRegion` | body | 6 | closed: physical or typological set, complete | has one |
| `Capacity` | body | 8 | closed: physical or typological set, complete | has one |
| `ConditionKind` | body | 17 | closed: physical or typological set, complete | has one |
| `Consciousness` | body | 4 | closed: physical or typological set, complete | needed |
| `Handedness` | body | 3 | closed: physical or typological set, complete | needed |
| `HarmCause` | body | 24 | closed: physical or typological set, complete | needed |
| `HeightClass` | body | 4 | closed: physical or typological set, complete | has one |
| `InjuryKind` | body | 24 | closed: physical or typological set, complete | needed |
| `NerveDamage` | body | 3 | closed: physical or typological set, complete | needed |
| `StrikeStyle` | body | 5 | widened (47.4) | needed |
| `TissueKind` | body | 12 | closed: physical or typological set, complete | has one |
| `BondKind` | bond | 60 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `LinkGroup` | bond | 7 | process: engine bookkeeping or record kind | has one |
| `PseudoLinkKind` | bond | 3 | wired (47.7) | needed |
| `ChronicleAuditKind` | chronicle | 8 | process: engine bookkeeping or record kind | — |
| `ChronicleKind` | chronicle | 70 | process: engine bookkeeping or record kind | has one |
| `LegendaryQuestKind` | chronicle | 4 | typed model (47.6.2) | needed |
| `PartOfSpeech` | chronicle | 9 | process: engine bookkeeping or record kind | — |
| `TierCapability` | civilization | 10 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `AccountKind` | collective | 7 | widened (47.4) | needed |
| `AccountMedium` | collective | 4 | widened (47.4) | needed |
| `ArmsInk` | collective | 14 | emblem systems (48.3) | needed |
| `CollectiveActKind` | collective | 8 | process: engine bookkeeping or record kind | has one |
| `FormativeKind` | collective | 7 | widened (47.4) | has one |
| `MobEnd` | collective | 3 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `MobTarget` | collective | 7 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `SocialBias` | collective | 3 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `StoryletEffect` | collective | 16 | process: engine bookkeeping or record kind | — |
| `StoryletId` | collective | 8 | process: engine bookkeeping or record kind | has one |
| `DispatchContent` | communication | 9 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `EnvoyFate` | communication | 4 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `Medium` | communication | 7 | widened (47.4) | has one |
| `OpinionSubject` | communication | 5 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `SignalKind` | communication | 4 | renamed (47.2.5) | has one |
| `Causality` | cosmography | 3 | closed: physical or typological set, complete | has one |
| `ClusterKind` | cosmography | 13 | closed: physical or typological set, complete | has one |
| `DimensionElement` | cosmography | 11 | dimension aspects (47.6.7) | has one |
| `DimensionKind` | cosmography | 28 | closed: physical or typological set, complete | has one |
| `DimensionalEventKind` | cosmography | 8 | closed: physical or typological set, complete | has one |
| `GalacticEventKind` | cosmography | 12 | closed: physical or typological set, complete | has one |
| `GalacticNucleus` | cosmography | 5 | closed: physical or typological set, complete | has one |
| `GalacticZone` | cosmography | 10 | closed: physical or typological set, complete | has one |
| `GalaxyAge` | cosmography | 6 | closed: physical or typological set, complete | has one |
| `GalaxyType` | cosmography | 28 | closed: physical or typological set, complete | has one |
| `RiftCause` | cosmography | 7 | closed: physical or typological set, complete | has one |
| `SkyObject` | cosmography | 3 | process: engine bookkeeping or record kind | — |
| `StarAge` | cosmography | 6 | closed: physical or typological set, complete | has one |
| `WorldAge` | cosmography | 4 | closed: physical or typological set, complete | has one |
| `CreatorPassion` | creator | 8 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `CreatorSignKind` | creator | 4 | widened (47.5.2) | needed |
| `Capability` | culture | 2 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `RumourChannel` | culture | 6 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `ChallengeKind` | cycles | 5 | widened (47.4) | needed |
| `ChallengeResponse` | cycles | 3 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `GiftOccasion` | cycles | 8 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `LabourRegime` | cycles | 2 | widened (48.6) | needed |
| `ManumissionPath` | cycles | 5 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `StressComponent` | cycles | 4 | wired (47.7) | needed |
| `NaturalTrait` | demography | 10 | authored: typed traits (48.8) | needed |
| `AnomalyKind` | discovery | 4 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `ResearchIncident` | discovery | 8 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `DiseaseTarget` | disease | 5 | widened: every body function (F4) | needed |
| `SpreadPath` | disease | 7 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `CouncilMotion` | divine | 14 | widened (47.5.5) | needed |
| `DivineWoundKind` | divine | 4 | widened (47.4) | needed |
| `DomainActivity` | divine | 20 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `GodGoalKind` | divine | 14 | authored: aim × object (48.7, 47.5) | needed |
| `SonPunishment` | divine | 3 | council penalties (47.5.5) | needed |
| `WoundCause` | divine | 5 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `CreatureLesson` | dominion | 2 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `DivineScale` | dominion | 6 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `MagicSiteKind` | dominion | 4 | widened (47.4) | needed |
| `Manifestation` | dominion | 4 | wired (47.7) | needed |
| `PrayerTone` | dominion | 2 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `Aversion` | ecology | 5 | widened and wired (47.7) | needed |
| `BreathKind` | ecology | 5 | typed model (47.6.3) | needed |
| `FoodLink` | ecology | 3 | process: engine bookkeeping or record kind | — |
| `GazeKind` | ecology | 4 | typed model (47.6.3) | needed |
| `Habitat` | ecology | 5 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `PlantYield` | ecology | 10 | unified: species products (48.5, 48.9) | has one |
| `Temperament` | ecology | 6 | renamed value (48.8) | needed |
| `TissueMaterial` | ecology | 14 | property names (47.6.3) | has one |
| `YieldProduct` | ecology | 13 | authored: species products (48.5) | needed |
| `ExtractionKind` | economy | 7 | widened (47.2.6) | has one |
| `FoeNature` | economy | 3 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `HazardKind` | economy | 5 | widened (47.2.6) | needed |
| `TradeLoss` | economy | 4 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `ArchiveOverride` | entity | 2 | process: engine bookkeeping or record kind | — |
| `EngineKind` | entity | 57 | process: engine bookkeeping or record kind | has one |
| `ProphecyReading` | entity | 3 | process: engine bookkeeping or record kind | — |
| `LandUse` | environment | 5 | closed: physical or typological set, complete | needed |
| `ScarKind` | environment | 12 | renamed values (48.8) | needed |
| `WeatherEffect` | environment | 8 | closed: physical or typological set, complete | has one |
| `DeferredStepKind` | epoch | 3 | process: engine bookkeeping or record kind | — |
| `EpochStepKind` | epoch | 17 | process: engine bookkeeping or record kind | — |
| `FactionActionKind` | faction | 15 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `FactionGoalKind` | faction | 11 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `FoundableFaction` | faction | 21 | authored: organisation kinds (48.6) | needed |
| `ClergyOffice` | faith | 4 | authored: clergy roles (48.6) | needed |
| `ReincarnationGate` | faith | 4 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `TradePolicyKind` | finance | 3 | widened (47.3.5) | has one |
| `GatheringKind` | gathering | 25 | widened (47.8.18) | has one |
| `Milestone` | gathering | 3 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `DwellingKind` | genetics | 10 | closed: physical or typological set, complete | has one |
| `Locus` | genetics | 30 | closed: physical or typological set, complete | has one |
| `LocusGroup` | genetics | 3 | closed: physical or typological set, complete | has one |
| `LandAct` | happening | 12 | renamed values (48.8) | needed |
| `RiverShiftCause` | happening | 4 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `EnergyKind` | industry | 6 | widened (47.2.2) | has one |
| `MethodKind` | industry | 53 | authored production methods (48.5) | has one |
| `OwnerClass` | industry | 6 | widened (47.4) | has one |
| `Pollutant` | industry | 3 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `ProcessKind` | industry | 20 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `HarmForce` | integrity | 10 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `Disaster` | intervention | 7 | divine grammar (47.5.1) | has one |
| `InterventionKind` | intervention | 4 | divine grammar (47.5.2) | needed |
| `Miracle` | intervention | 4 | divine grammar (47.5.1) | has one |
| `HookDemand` | intrigue | 5 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `IntrigueSecret` | intrigue | 16 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `PlotKind` | intrigue | 19 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `JobKind` | job | 18 | process: engine bookkeeping or record kind | — |
| `TrialKind` | justice | 4 | widened (47.3.3) | needed |
| `KillMethod` | law_depth | 5 | widened: any damage type and harm cause (47.10) | has one |
| `RecruitMotive` | law_depth | 4 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `RegistryKind` | law_depth | 5 | widened (47.4) | has one |
| `AchievementKey` | meta | 17 | process; value `fathers_hand` renamed `creators_hand` (gendered) | has one |
| `ImageMime` | meta | 3 | process: engine bookkeeping or record kind | — |
| `LedgerOperation` | meta | 3 | process: engine bookkeeping or record kind | — |
| `ScenarioKey` | meta | 8 | process: engine bookkeeping or record kind | has one |
| `ScoreComponent` | meta | 8 | process: engine bookkeeping or record kind | — |
| `CaptiveFate` | military | 7 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `CasualtyFate` | military | 4 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `CommandArea` | military | 5 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `DuelContext` | military | 5 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `DuelEnd` | military | 5 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `FeudParty` | military | 2 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `OutcomeClass` | military | 7 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `PeaceTermKind` | military | 16 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `SabotageKind` | military | 4 | widened (47.3.6) | needed |
| `SackChoice` | military | 3 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `SiegeWork` | military | 6 | widened (48.6) | needed |
| `SpyCover` | military | 4 | authored: any profession kind (48.6) | needed |
| `SpyOperation` | military | 7 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `SpyOwnerKind` | military | 4 | widened (47.4) | needed |
| `TargetClass` | military | 2 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `VesselArmament` | military | 4 | widened: armament by vehicle family, from mounts and equipment (48.6) | needed |
| `WarAimKind` | military | 15 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `Attribute` | mind | 19 | canonical attribute set (48.9) | has one |
| `CareerChange` | mind | 3 | process: engine bookkeeping or record kind | — |
| `DreamKind` | mind | 6 | closed: dream kinds; readings authored (48.7) | has one |
| `DreamReading` | mind | 8 | authored: readings by culture (48.7) | has one |
| `Emotion` | mind | 24 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `Facet` | mind | 34 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `FacetGroup` | mind | 4 | process: engine bookkeeping or record kind | — |
| `FearKind` | mind | 8 | authored: fears over typed objects (48.7) | has one |
| `IdeaKind` | mind | 16 | authored: tenets (48.7) | has one |
| `InspirationKind` | mind | 3 | widened (47.4) | has one |
| `LifeGoal` | mind | 15 | authored: aim × object (48.7) | has one |
| `MemoryKind` | mind | 35 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `NeedGroup` | mind | 4 | process: engine bookkeeping or record kind | has one |
| `NeedKind` | mind | 23 | widened (47.8.15) | has one |
| `OpinionComponent` | mind | 5 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `PerkKind` | mind | 40 | renamed values (48.7) | has one |
| `PreferenceKind` | mind | 16 | widened (47.8.15) | has one |
| `SkillKind` | mind | 63 | widened (5.13) | has one |
| `ThoughtKind` | mind | 138 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `TraitEffect` | mind | 15 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `TraitKind` | mind | 40 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `ValueHolder` | mind | 6 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `WantKind` | mind | 12 | authored: aim × object (48.7) | has one |
| `Ability` | mortal | 6 | unified (48.9) | needed |
| `CrimeKind` | mortal | 5 | crime catalogue (47.3.1) | has one |
| `HarshnessScale` | mortal | 8 | process: engine bookkeeping or record kind | — |
| `MarriageEnd` | mortal | 4 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `MarriageKind` | mortal | 3 | union axes (47.3.4) | needed |
| `MortalSex` | mortal | 3 | unified (48.9) | needed |
| `PunishmentKind` | mortal | 10 | widened (47.3.2) | needed |
| `CosmicOffice` | mythic | 6 | authored: divine offices (48.8) | has one |
| `GeasLayer` | mythic | 3 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `HeroquestBoon` | mythic | 8 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `MythicRealm` | mythic | 4 | authored: divine realms (48.8) | has one |
| `OfficeChoice` | mythic | 4 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `QuestTrial` | mythic | 4 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `ActorKind` | node | 7 | process: engine bookkeeping or record kind | — |
| `CarrierKind` | operations | 6 | carriers (47.2.4) | has one |
| `QuirkKind` | operations | 12 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `ResolveKind` | operations | 8 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `ImpactBody` | physics | 4 | closed: physical or typological set, complete | needed |
| `LifeComplexity` | physics | 5 | closed: physical or typological set, complete | needed |
| `LifeEnvironment` | physics | 4 | closed: physical or typological set, complete | needed |
| `TerraformAim` | physics | 9 | closed: physical or typological set, complete | needed |
| `PlaceHeight` | place | 3 | closed: physical or typological set, complete | needed |
| `SacredClass` | place | 3 | closed: physical or typological set, complete | needed |
| `SecretKind` | place | 6 | widened (47.4) | needed |
| `ClaimBasis` | polity | 6 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `ClauseKind` | polity | 17 | widened (5.18) | needed |
| `DebtRemedy` | polity | 3 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `HouseTrait` | polity | 6 | authored: typed traits (48.8) | needed |
| `OathKind` | polity | 7 | widened (47.4) | needed |
| `OfficeKind` | polity | 20 | closed functions; office names from the culture's language (48.6) | has one |
| `OfficePower` | polity | 12 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `RevoltKind` | polity | 5 | widened (47.3.6) | needed |
| `Rarity` | rarity | 6 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `CredentialKind` | regime | 7 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `LegitimacyType` | regime | 3 | widened (47.4) | needed |
| `DangerHarm` | region | 6 | closed: physical or typological set, complete | needed |
| `HazardSeason` | region | 3 | closed: physical or typological set, complete | needed |
| `RegionMemoryKind` | region | 9 | closed: physical or typological set, complete | needed |
| `TerrainHazard` | region | 4 | closed: physical or typological set, complete | needed |
| `AppealKind` | relations | 5 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `ContestEnd` | relations | 3 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `ContestKind` | relations | 7 | renamed value (48.7) | has one |
| `ContestStake` | relations | 6 | renamed value (48.7) | has one |
| `GroupKind` | relations | 5 | widened (47.4) | has one |
| `InteractionKind` | relations | 21 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `PassionKind` | relations | 4 | widened (47.4) | has one |
| `PersuasionAim` | relations | 5 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `RelationType` | relations | 18 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `ClaimKind` | renown | 3 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `Currency` | renown | 4 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `LoreKind` | renown | 4 | widened (47.4) | has one |
| `LorePrice` | renown | 3 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `DistrictHarm` | settlement | 5 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `TreasuryEntry` | settlement | 17 | process: engine bookkeeping or record kind | — |
| `BattlefieldFeature` | site | 3 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `ExcavationFind` | site | 6 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `ExcavationRisk` | site | 4 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `RoomContentKind` | site | 4 | widened (47.4) | needed |
| `SiteChallenge` | site | 5 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `SiteRoomKind` | site | 15 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `Commodity` | society | 3 | summary computed from good categories (48.1, 48.9) | has one |
| `LoyaltyPart` | society_depth | 9 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `ShortfallEffect` | society_depth | 9 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `ExistenceBand` | son | 4 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `Passion` | son | 4 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `SonDeathCause` | son | 7 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `StatGroup` | son | 3 | process: engine bookkeeping or record kind | — |
| `CouncilTask` | statecraft | 6 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `CrisisDemand` | statecraft | 4 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `MandateKind` | statecraft | 8 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `ResolutionKind` | statecraft | 4 | widened (47.5.5) | needed |
| `RecoveryKind` | storyteller | 3 | registry (47.6.5) | needed |
| `SpontaneousKind` | storyteller | 5 | registry (47.6.5) | needed |
| `TensionBand` | storyteller | 3 | process: engine bookkeeping or record kind | — |
| `CapacityUnit` | structure | 14 | process: engine bookkeeping or record kind | — |
| `StructureGroup` | structure | 9 | process: engine bookkeeping or record kind | — |
| `LlmCallKind` | telemetry | 2 | process: engine bookkeeping or record kind | — |
| `TitleTenure` | titles | 6 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `SenseShift` | tongues | 6 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `SoundChangeCause` | tongues | 6 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `SoundChangeKind` | tongues | 5 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `SoundEnvironment` | tongues | 4 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `WordRegister` | tongues | 4 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `JourneyEventKind` | travel | 18 | authored: encounter model (47.8.12) | needed |
| `JourneyIntent` | travel | 5 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `RouteClosure` | travel | 7 | wired (47.7) | needed |
| `TravelMethod` | travel | 15 | authored: travel model (48.8) | has one |
| `CargoClass` | urban | 4 | widened (47.2.4) | needed |
| `CivicService` | urban | 5 | closed: physical or typological set, complete | needed |
| `LandCover` | urban | 8 | closed: physical or typological set, complete | needed |
| `LandGround` | urban | 7 | closed: physical or typological set, complete | needed |
| `Preservation` | urban | 4 | replaced by PreservationMethod (48.5) | needed |
| `UrbanService` | urban | 8 | closed: physical or typological set, complete | needed |
| `ZoneKind` | urban | 7 | widened (47.4) | has one |
| `MountArc` | vehicles | 4 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `MountKind` | vehicles | 13 | closed: the engine's own distinctions; instances are named through the kinds that use them | needed |
| `CasusBelliKind` | war | 10 | closed: the engine's own distinctions; instances are named through the kinds that use them | has one |
| `HeroQuestKind` | war | 5 | typed model (47.6.2) | needed |
| `Atmosphere` | world | 5 | closed: physical or typological set, complete | has one |
| `ClimateEra` | world | 5 | widened (47.4) | has one |
| `CosmosShape` | world | 3 | closed: physical or typological set, complete | has one |
| `CosmosSize` | world | 3 | closed: physical or typological set, complete | has one |
| `Discovery` | world | 4 | closed: physical or typological set, complete | has one |
| `GenesisTemplate` | world | 19 | closed: physical or typological set, complete | has one |
| `Gravity` | world | 3 | closed: physical or typological set, complete | has one |
| `HorrorEventKind` | world | 7 | typed model (47.6.1) | needed |
| `LanguageTexture` | world | 6 | widened (47.4) | has one |
| `SkyEventKind` | world | 9 | typed model (48.8) | has one |
| `StarType` | world | 32 | typed model (48.8) | has one |
| `TechnologyEra` | world | 6 | widened and per family (47.2.1) | has one |
| `WorldType` | world | 34 | closed: physical or typological set, complete | has one |


### Appendix 48.B — The 214 enums with an authored layer

Each keeps its authored layer. "Decision" names what W48 changes in its category set; "Catalogue" marks the enums that need a property catalogue (48.10).

| Enum | Module | Values | Decision | Catalogue |
|---|---|---|---|---|
| `PackageKind` | affliction | 14 | complete for its function; kept | has one |
| `KeystoneUse` | agrarian | 4 | widened: `energy`, `medicine`, `making`, `power`, `trade` | needed |
| `LandUseRing` | agrarian | 5 | complete for its function; kept | needed |
| `NutrientKind` | agrarian | 4 | complete (47.4) | needed |
| `PreparednessKind` | agrarian | 6 | widened (47.4) | needed |
| `SpellDuration` | arcana | 4 | complete for its function; kept | has one |
| `SpellForm` | arcana | 14 | widened (45.3) | has one |
| `SpellRange` | arcana | 4 | complete for its function; kept | has one |
| `SpellTarget` | arcana | 4 | complete for its function; kept | has one |
| `SpellTechnique` | arcana | 8 | widened (45.3) | has one |
| `BodyPlan` | body | 12 | read with biology variants (F46, 46.3) | has one |
| `BodyReading` | body | 4 | complete for its function; kept | needed |
| `DamageType` | body | 17 | complete for its function; kept | needed |
| `MaimedKind` | body | 9 | complete for its function; kept | needed |
| `WritingSystem` | chronicle | 8 | complete for its function; kept | has one |
| `ArmsRim` | collective | 6 | one emblem system (48.3) | has one |
| `ChargeArrangement` | collective | 7 | one emblem system (48.3) | has one |
| `DatingSystemKind` | collective | 4 | widened (47.4) | needed |
| `DesignComponentKind` | collective | 16 | complete for its function; kept | needed |
| `DesignKind` | collective | 5 | widened (47.4) | needed |
| `HeraldicCharge` | collective | 149 | one emblem system (48.3) | has one |
| `HeraldicDivision` | collective | 35 | one emblem system (48.3) | has one |
| `HeraldryHolderKind` | collective | 5 | widened (47.4) | needed |
| `NormBehaviour` | collective | 13 | widened (47.8.22) | has one |
| `NormSituation` | collective | 13 | widened (47.8.22) | has one |
| `PartitionLine` | collective | 10 | one emblem system (48.3) | has one |
| `RoleEligibility` | collective | 5 | culture data, default `any` (48.6) | needed |
| `RoleKind` | collective | 5 | complete (47.4) | needed |
| `ShieldShape` | collective | 9 | one emblem system (48.3) | has one |
| `SupporterPose` | collective | 4 | one emblem system (48.3) | has one |
| `Tincture` | collective | 16 | one emblem system (48.3) | has one |
| `ApocalypseVariant` | cosmography | 6 | typed model; `twilight_of_gods` renamed (48.8) | has one |
| `BeingAgenda` | cosmography | 9 | complete for its function; kept | has one |
| `BeingKind` | cosmography | 15 | typed model (48.8) | has one |
| `BeingScale` | cosmography | 5 | complete for its function; kept | has one |
| `GalacticStructureKind` | cosmography | 23 | complete for its function; kept | has one |
| `OceanCurrent` | cosmography | 3 | complete for its function; kept | needed |
| `OmenReading` | cosmography | 3 | complete for its function; kept | has one |
| `PhenomenonCause` | cosmography | 8 | complete for its function; kept | has one |
| `PhenomenonKind` | cosmography | 14 | typed model (48.8) | has one |
| `CookingMethod` | cuisine | 23 | widened (48.2) | needed |
| `DishCourse` | cuisine | 8 | mapped to meal slot and ingredient roles (48.2) | needed |
| `ArtMedium` | culture | 12 | unified into `ArtMode` (48.7) | has one |
| `BacklashKind` | culture | 5 | power hazards (F52) | needed |
| `CurseKind` | culture | 6 | widened (47.4) | needed |
| `CustomCatalog` | culture | 6 | complete for its function; kept | needed |
| `IdeologyTenet` | culture | 13 | built-in tenets; authored tenets (48.7) | has one |
| `ItemClass` | culture | 43 | widened with garment, furnishing, tool, instrument and ornament classes linked to their kinds (48.3, 48.4) | has one |
| `LanguageRegister` | culture | 4 | complete for its function; kept | needed |
| `LegendArchetype` | culture | 11 | renamed and widened (48.7) | has one |
| `MagicSchool` | culture | 14 | clusters of the spell grammar (8.6, 45.3) | has one |
| `ProphecyConsequence` | culture | 6 | complete for its function; kept | needed |
| `ProphecyPredicate` | culture | 7 | complete for its function; kept | needed |
| `ResearchChooser` | culture | 3 | complete for its function; kept | needed |
| `RiteEffectKind` | culture | 17 | widened (45.3) | needed |
| `SpeakerKind` | culture | 3 | complete (47.4) | needed |
| `SummonForm` | culture | 3 | widened (47.4) | needed |
| `Technique` | culture | 66 | widened (5.13) | has one |
| `TraditionEffectKind` | culture | 12 | complete for its function; kept | needed |
| `TraditionKind` | culture | 18 | `TraditionFunction` with renames (48.7) | needed |
| `CousinTerms` | cycles | 3 | kin term systems (48.6) | needed |
| `DescentGroup` | cycles | 4 | complete typology | needed |
| `KinshipDescent` | cycles | 5 | neutral names (48.6) | needed |
| `LegacyKind` | cycles | 7 | widened (47.4) | needed |
| `LongPlanKind` | cycles | 4 | widened (47.4) | needed |
| `MarriagePayment` | cycles | 4 | neutral names (48.6) | needed |
| `MarriagePreference` | cycles | 4 | union axes (47.3.4) | needed |
| `ReproductiveCaste` | cycles | 3 | complete for its function; kept | needed |
| `ReproductiveSystem` | cycles | 5 | canonical for sexes (48.6) | needed |
| `Aesthetic` | demography | 6 | axes per culture (48.7) | has one |
| `AgeBand` | demography | 3 | complete for its function; kept | needed |
| `CohortCondition` | demography | 6 | complete for its function; kept | needed |
| `FolkDiet` | demography | 9 | unified with `Diet` (48.9) | has one |
| `FuneralCustom` | demography | 9 | canonical funeral categories (48.9) | has one |
| `InheritanceCustom` | demography | 6 | neutral names (48.6) | needed |
| `Job` | demography | 12 | unified with professions (48.9) | has one |
| `MarriageCustom` | demography | 4 | union axes (47.3.4) | needed |
| `MartialStyle` | demography | 16 | complete for its function; kept | needed |
| `Sex` | demography | 2 | unified (48.9) | needed |
| `AgeKind` | discovery | 4 | widened (47.4) | has one |
| `ArtDiscipline` | discovery | 9 | unified into `ArtMode` (48.7) | has one |
| `BlueprintKind` | discovery | 4 | widened (47.4) | has one |
| `TheoryDomain` | discovery | 8 | widened: `engineering`, `information`, `power`, `life_craft` | has one |
| `ClimateAffinity` | disease | 5 | complete for its function; kept | needed |
| `DiseaseVector` | disease | 7 | complete for its function; kept | needed |
| `BargainGain` | divine | 3 | complete for its function; kept | needed |
| `BargainPrice` | divine | 3 | complete for its function; kept | needed |
| `LawException` | divine | 5 | complete for its function; kept | needed |
| `OuterHunger` | divine | 5 | typed consumption (47.5.7) | has one |
| `Domain` | domain | 47 | complete for its function; kept | has one |
| `PerceivedAlignment` | dominion | 3 | complete for its function; kept | has one |
| `BeastTemper` | ecology | 7 | complete for its function; kept | needed |
| `Biochemistry` | ecology | 6 | complete for its function; kept | has one |
| `Cultivation` | ecology | 4 | complete for its function; kept | needed |
| `Diet` | ecology | 9 | canonical diet set (48.9) | has one |
| `GrowthCycle` | ecology | 3 | complete for its function; kept | needed |
| `HerdTraining` | ecology | 3 | species roles (48.5) | needed |
| `RangeTrend` | ecology | 3 | complete for its function; kept | needed |
| `SizeClass` | ecology | 6 | complete for its function; kept | has one |
| `Sociality` | ecology | 4 | complete for its function; kept | needed |
| `SpeciesClass` | ecology | 4 | widened (47.4) | needed |
| `SpeciesUse` | ecology | 9 | species roles (48.5) | needed |
| `CommodityKind` | economy | 35 | built-in good kinds; category `GoodCategory` (48.1) | has one |
| `GoodsFlow` | economy | 19 | complete for its function; kept | needed |
| `WorkshopKind` | economy | 19 | complete for its function; kept | has one |
| `EntityFlag` | entity | 110 | complete for its function; kept | needed |
| `EntityType` | entity | 43 | gains `network` (F51) | has one |
| `CoastKind` | environment | 5 | closed: physical | needed |
| `NotableYearKind` | environment | 4 | widened (47.4) | needed |
| `PlaceCover` | environment | 3 | complete for its function; kept | needed |
| `RiverClass` | environment | 4 | closed: physical | needed |
| `SoilKind` | environment | 10 | property names; `salt`, `ash`, `bone` renamed (48.8) | needed |
| `TemperatureBand` | environment | 6 | complete for its function; kept | has one |
| `TerrainKind` | environment | 23 | complete for its function; kept | has one |
| `WeatherKind` | environment | 17 | complete for its function; kept | has one |
| `EvolvedTrait` | evolution | 9 | complete for its function; kept | needed |
| `PlagueResponse` | evolution | 6 | widened: `isolation_by_network`, `vaccination`, `rite`, `flight`, `scapegoating` | needed |
| `EstatePrivilege` | faction | 5 | complete for its function; kept | has one |
| `FactionKind` | faction | 27 | organisation kinds (48.6) | has one |
| `FactionScale` | faction | 4 | complete for its function; kept | needed |
| `MovementCause` | faction | 6 | complete for its function; kept | has one |
| `BindingKind` | faith | 6 | complete for its function; kept | needed |
| `FanaticismKind` | faith | 3 | widened (47.4) | has one |
| `FuneralRite` | faith | 5 | unified with `FuneralCustom` (48.9) | needed |
| `HoldingKind` | faith | 5 | widened (47.4) | needed |
| `JudgementDoctrine` | faith | 5 | complete for its function; kept | needed |
| `RebirthPath` | faith | 3 | complete for its function; kept | needed |
| `SpiritAlignment` | faith | 3 | complete for its function; kept | needed |
| `StratumKind` | faith | 6 | typed model (47.6.4) | has one |
| `TenetKind` | faith | 27 | built-in tenets; authored tenets (48.7) | has one |
| `ForeignGodPowerEffect` | foreign_god | 8 | divine power grammar (47.5.1) | has one |
| `CollectionKind` | gathering | 42 | widened with the incident families (5.16) | needed |
| `HouseholdDecision` | genetics | 9 | complete for its function; kept | has one |
| `Criticality` | integrity | 3 | complete for its function; kept | needed |
| `SectionHazard` | integrity | 8 | complete for its function; kept | needed |
| `Deposition` | justice | 3 | complete for its function; kept | needed |
| `JurisdictionClaim` | law_depth | 3 | complete for its function; kept | has one |
| `LegalSystem` | law_depth | 6 | complete for its function; kept | has one |
| `MaterialKind` | material | 31 | complete for its function; kept | has one |
| `ArmourType` | military | 11 | complete for its function; kept | has one |
| `CommanderTrait` | military | 10 | complete for its function; kept | has one |
| `Formation` | military | 12 | complete for its function; kept | has one |
| `ShieldType` | military | 6 | complete for its function; kept | has one |
| `Tactic` | military | 23 | complete for its function; kept | has one |
| `UnitKind` | military | 47 | complete for its function; kept | has one |
| `ActKind` | mind | 52 | complete for its function; kept | has one |
| `FocusKind` | mind | 8 | complete for its function; kept | has one |
| `HonourModel` | mind | 3 | `none` added (47.8.9) | has one |
| `PressureKind` | mind | 7 | widened (47.4) | needed |
| `Profession` | mind | 25 | profession kinds (48.6) | has one |
| `CareerPath` | mortal | 9 | complete for its function; kept | needed |
| `DeathCause` | mortal | 27 | complete for its function; kept | needed |
| `StressBreak` | mortal | 6 | complete for its function; kept | has one |
| `NodeKind` | node | 9 | complete for its function; kept | needed |
| `CrewStation` | operations | 5 | widened (48.6) | has one |
| `EchelonOrder` | operations | 5 | complete for its function; kept | needed |
| `ExpeditionGround` | operations | 4 | complete for its function; kept | has one |
| `PointOfSail` | operations | 5 | complete for its function; kept | needed |
| `ShotKind` | operations | 4 | widened (47.4) | has one |
| `AirNeed` | physics | 4 | complete for its function; kept | needed |
| `CosmicFeatureKind` | physics | 6 | complete for its function; kept | needed |
| `PlaceKind` | place | 38 | complete for its function; kept | has one |
| `GovernmentKind` | polity | 17 | complete for its function; kept | has one |
| `Jurisdiction` | polity | 3 | complete for its function; kept | needed |
| `LawArea` | polity | 9 | wired (47.3.1, 47.7) | needed |
| `LawKind` | polity | 40 | widened (47.3, 44.6) | has one |
| `LegitimacyBasis` | polity | 4 | complete for its function; kept | needed |
| `RegionalStanding` | polity | 4 | complete for its function; kept | needed |
| `TreatyKind` | polity | 15 | complete for its function; kept | has one |
| `Routinisation` | regime | 5 | complete for its function; kept | needed |
| `SelectorateKind` | regime | 9 | complete for its function; kept | needed |
| `CircleKind` | relations | 8 | renamed value (48.7) | has one |
| `BuildMaterial` | settlement | 2 | replaced by world materials (48.5) | has one |
| `DistrictKind` | settlement | 22 | complete for its function; kept | has one |
| `WaterSupply` | settlement | 4 | widened: `piped`, `desalination`, `condenser`, `reservoir`, `by_working` | needed |
| `CreatureTrait` | society | 32 | typed traits (48.8) | has one |
| `KnowledgeBranch` | society | 19 | read with the technology families (47.2.1) | has one |
| `NaturalLaw` | society | 23 | law grammar (47.5.6) | has one |
| `ResourceMechanic` | society | 6 | complete for its function; kept | has one |
| `SocialClass` | society | 15 | rank kinds over it (48.6) | has one |
| `DriftCause` | society_depth | 11 | complete for its function; kept | needed |
| `PowerEffect` | son | 13 | divine power grammar (47.5.1) | has one |
| `Stat` | son | 9 | complete for its function; kept | has one |
| `NobleWant` | statecraft | 4 | complete for its function; kept | needed |
| `SubjectKind` | statecraft | 7 | widened (47.4) | needed |
| `TaxKind` | statecraft | 5 | widened (47.3.5) | has one |
| `BuildScale` | structure | 4 | complete for its function; kept | needed |
| `BuilderKind` | structure | 6 | widened (47.4) | needed |
| `BuildingForm` | structure | 27 | complete for its function; kept | has one |
| `StaffScale` | structure | 4 | complete for its function; kept | needed |
| `StructureKind` | structure | 142 | own effects (47.1) | has one |
| `StructureSection` | structure | 43 | complete; each section has typed properties | needed |
| `LanguageModality` | tongues | 5 | widened: `data`, `mind`, `chemical` (0.7) | has one |
| `MorphologyType` | tongues | 4 | complete for its function; kept | has one |
| `NumberSystem` | tongues | 5 | complete for its function; kept | has one |
| `ScriptChangeCause` | tongues | 4 | complete for its function; kept | needed |
| `WordOrder` | tongues | 7 | wired (47.7) | needed |
| `VehicleKind` | travel | 4 | widened (47.2.4) | needed |
| `MarketPlay` | urban | 2 | complete for its function; kept | needed |
| `Morphology` | urban | 6 | complete for its function; kept | has one |
| `OrderLaw` | urban | 4 | wired (47.7) | needed |
| `RacketKind` | urban | 6 | widened (47.4) | needed |
| `TransportKind` | urban | 4 | carriers (47.2.4) | needed |
| `FireControl` | vehicles | 7 | complete for its function; kept | needed |
| `Propulsion` | vehicles | 18 | complete for its function; kept | has one |
| `VehicleDomain` | vehicles | 9 | complete for its function; kept | has one |
| `VehicleFrame` | vehicles | 128 | complete for its function; kept | has one |
| `VehicleSection` | vehicles | 55 | complete for its function; kept | has one |
| `VehicleSize` | vehicles | 5 | complete for its function; kept | has one |
| `WarCause` | war | 28 | complete for its function; kept | needed |
| `WarEnding` | war | 10 | complete for its function; kept | needed |
| `ImageStyle` | world | 6 | complete for its function; kept | needed |
| `LoreLanguage` | world | 2 | complete for its function; kept | has one |
| `SonDistribution` | world | 2 | complete for its function; kept | needed |


### Appendix 48.C — The 215 process enums

These hold states, stages, outcomes, sources, roles in events, scales, levels and bookkeeping. `catalog/concepts.py` declares each as `process`; they need neither an authored layer nor a property catalogue, and they stay under the enum-value scan of 47.6.8 and the read guard of 47.7. Those among them that W47 or W48 widens or renames are named in their sections (for example `TitleRank` in 48.6, `MedicineTier` in 47.2.3, `ServitorRank` in 47.6.6, `GenderRule` in 48.6).

| Module | Enums |
|---|---|
| agent | `ToolBlock`, `TurnCounter`, `Verdict` |
| agrarian | `CentralityRank`, `CommonsRule` |
| arcana | `LawSource`, `RechargeRule` |
| body | `InjuryState`, `MedicineTier`, `TreatmentStep` |
| bond | `BondCategory`, `BondRole`, `BondState` |
| chronicle | `FeedCategory`, `LegendaryQuestOutcome`, `MajorEventCategory`, `NotificationCategory`, `ThreadLinkRole`, `ThreadStatus` |
| collective | `AccountStance`, `CascadeOutcome`, `CollectiveTrigger`, `MobStatus`, `StoryletRole`, `StoryletStatus` |
| communication | `DispatchState`, `SignalState` |
| cosmography | `BeingPhase`, `RiftState`, `RouteScope` |
| creator | `CreatorMoodAxis`, `CreatorMoodLabel` |
| culture | `BoostTrigger`, `CalendarSlot`, `ItemDeed`, `MagicSource`, `ProphecyState` |
| cycles | `CyclePhase`, `GiftState`, `LongPlanStatus`, `MobilityMode`, `ResidenceRule` |
| discovery | `BlueprintSource`, `EraDeed`, `GreatField` |
| disease | `CureSource`, `OutbreakStatus` |
| divine | `DomainHook`, `GoalSource`, `GoalState`, `LawScope` |
| dominion | `BeliefStance`, `CreatureDeed`, `WorshipMode` |
| ecology | `AwakeningTrigger`, `DomesticationStage` |
| economy | `CommodityFamily`, `LoanStatus`, `MaterialFamily`, `MaterialOrigin`, `MaterialSlot`, `TradeMode`, `TradeRouteStatus` |
| entity | `CivilizationTier`, `EntityOrigin`, `EntityStatus`, `LegendCategory`, `MortalRole` |
| environment | `MovementMode`, `WaterSource` |
| epoch | `DeferredStepStatus`, `EngineStage`, `EpochPhase`, `EpochStepStatus` |
| equipment | `ArmamentSlot`, `EquipmentFamily` |
| evolution | `KeystoneRole`, `SuccessionStage`, `TrophicLevel` |
| faction | `FactionRank` |
| faith | `AfterlifeState` |
| finance | `CreditState`, `SpeculationStatus` |
| foreign_god | `ForeignGodStatus` |
| gathering | `AttendanceReason`, `CollectionRole`, `GatheringOutcome`, `GatheringStatus`, `GuestRole` |
| genetics | `GiftStance`, `HouseholdRole` |
| happening | `EventPhase` |
| industry | `QualityTier` |
| integrity | `SectionState` |
| intrigue | `BeliefSource`, `FavourOrigin`, `HookSource`, `HookStrength`, `IdentityReason`, `SchemePhase` |
| job | `JobStatus` |
| justice | `CaseStage`, `ProposalEvent`, `ProposalStance`, `ProposalState` |
| law_depth | `CourtLevel`, `MoleHuntOutcome` |
| meta | `ImageOrigin`, `ScenarioStatus` |
| military | `AgentStatus`, `ArmyRole`, `BattlePhase`, `ContractStatus`, `DefenderAction`, `FeudAction`, `FeudStatus`, `MoraleState`, `MutinyOutcome`, `SiegeAction`, `Stance`, `StarvationStage`, `UnitFamily`, `VesselStatus` |
| mind | `DreamState`, `EthicalStance`, `GriefStage`, `IdeaSource`, `IdeaState`, `InspirationState`, `KindFamily`, `MoodState`, `SkillFamily`, `SkillSource`, `TraitSource`, `ValueAxis` |
| modifier | `IncidentRole`, `ModifierOp`, `ModifierSource` |
| mortal | `EquipmentSlot`, `HarshnessProfile`, `LifeStage` |
| mythic | `GeasMode`, `GeasState`, `HeroquestState`, `MantlingState`, `ServitorOrigin`, `ServitorRank`, `ServitorRole` |
| operations | `EchelonLevel`, `ExpeditionEvent`, `ExpeditionRole`, `ExpeditionStatus` |
| physics | `ImpactOutcome`, `SurveyLevel`, `SystemRole` |
| place | `DiscoveryMode`, `SecretOrigin` |
| polity | `DecisionRule`, `GenderRule`, `OathStatus`, `PartyRole`, `SuccessionRule`, `TreatyStatus` |
| regime | `ClientRole`, `LeadershipMode`, `PowerStance`, `SegmentLevel` |
| region | `DangerOrigin`, `DangerSource`, `MemoryOrigin` |
| relations | `PassionSource` |
| renown | `ClaimStatus`, `ReputationAxis` |
| settlement | `SizeTier` |
| site | `ExcavationStage`, `ExcavationStatus` |
| society | `CommunityRelationLabel` |
| society_depth | `LabourReason`, `MobilityEvent` |
| son | `ExistenceMode`, `ReputationLabel`, `SonRelationLabel`, `SonStatus` |
| statecraft | `CourtPosition`, `CrisisSide`, `CrisisState`, `MandateState`, `ResolutionState` |
| storyteller | `StorytellerProfile` |
| structure | `ConstructionState`, `ConstructionStatus`, `SectionRole` |
| telemetry | `LlmCallStatus` |
| titles | `TitleRank` |
| tongues | `LanguagePolicy`, `LanguageStage` |
| travel | `HorizonStatus`, `JourneyStatus`, `RouteState` |
| urban | `ConvoyStatus`, `CrimeStance`, `HousingLevel`, `TribunalVerdict` |
| vehicles | `VehicleFamily`, `VehicleStatus` |
| war | `BattleOutcome`, `CaptiveStatus`, `DebtStatus`, `GodConflictOutcome`, `HeroQuestStatus`, `SiegeStatus`, `TributeStatus`, `WarSide`, `WarStatus` |
| world | `FateMode` |
