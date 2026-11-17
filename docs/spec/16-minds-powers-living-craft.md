# 16 — Made Minds, Innate Powers, Living Craft, the Depth Pass, Typed Kinds, the Record of Events, Every Facet of Life and the Orders of Economy and State (W44–W51)

This spec adds eight waves to the lore engine:

- **W44 Made minds and the information age.** Minds that live in made things or in no body at all; copies, saves, transfers and merges of minds; augmented bodies; networks, intrusion, surveillance and information conflict; corporations and private power; self-making machines; abundance; and the collapse of high making into relics and salvage.
- **W45 Innate powers, power sources and concealment.** Powers that belong to a being rather than to a learned rite (the psionic class and every other inborn, awakened, granted or bonded power); an open model of power sources that any world can author; magic systems as typed world structures; and hidden truths kept from the public (the masquerade class), with breach, revelation and forgetting.
- **W46 Living craft.** Technology made by growing, breeding, shaping and engineering living things: designed crops and herds, grown structures, living vessels, living arms, grown bodies and organs, cloning, symbionts and parasites, living medicine and designed disease, living production, living links and living computation, world-shaping ecologies and designed sapience.
- **W47 The depth pass.** Every existing or planned mechanic brought to full breadth and depth: structures that act in their own right, eras and customs at full breadth, the god layer, typed models in place of fixed lists that carry images, every enum value read, every thin spec section completed, and guards that keep each of these from coming back.
- **W48 Typed kinds.** Every concept a world can define in its own terms: a neutral category enum plus authored kinds with typed properties for goods, food, drink, dress, colour, scent, household goods, tools, instruments, games, substances, money, professions, ranks, titles, clergy, organisations, kinship, traditions, art, tenets, fears, goals and the cosmos; a property catalogue for every content enum; one taxonomy per concept; every value that carries an image or a gender renamed; and guards for all of it.
- **W49 The record of events.** Every happening of every kind kept and told in full: incident kinds with typed roles and facts, the steps of every process, every change of every value with its before, after and terms, in-world moments and exact places, true causes, witnesses and rumours told from the record, the past of any record at any moment, and nothing ever folded away or cut.
- **W50 Every facet of life at depth.** A closed audit against the 689 world-content subcategories of the Outline of Cultural Materials, the 572 registered mechanics and the depth metric. It adds thirteen families of life no section carried at depth (population policy, recorded and mass media, commerce practice, public works and state enterprise, daily life and time, kin duties and kin groups, folk knowledge, intimacy norms and the course of reproduction, childhood and socialization, endowments, youth, death work, humour and public speech). It gives behaviour to 100 facets that had kinds only, couples every isolated mechanic and brings every node type to its depth target.
- **W51 Orders of the economy, institutions of states, and the gaps found by search.** An open search over 1,197 concept patterns, the 693 Dewey sections, human universals, other genres' core mechanics and the lifecycle, scale and actor axes found 30 gaps the fixed lists of W50 could not name. W51 closes them in 27 sections: economic orders and their transitions, the inner life of organisations, market structure, organised labour, monetary authorities, securities, leagues of polities, city rules and services, protected nature, leaving office, referendums, reckoning after a regime, cults of living leaders, restoration of fallen polities, occupation regimes, weapons of mass harm and war remnants, war and migration between worlds, family dynamics, the spread of feeling, interpretation, grave goods, conditions without an agent, fertility control, honours, sea waves, creature societies and conceptions of the divine.

Every wave is written to be integrated completely, under the completion contract of spec 13 J.19 and the standing rules of `CLAUDE.md`. Nothing here is label-only, optional or deferred.

---

## Part 0. Scope, numbering and ground rules

### 0.1 The gap this spec closes

Spec 13 and the waves through W43 built a deep pre-modern, magical and cosmic world, and W42 widened the typed catalogues so a modern or spacefaring world can be named in its own kinds. Three families of lore still cannot be told by the engine:

1. **Minds that are not born in a body.** W42 added the `ai_core`, `robotics_works`, `cloning_facility` and `data_centre` structures, the `machine_rule` government, the `algorithm` selectorate, the `machine_law` and `data_privacy` laws, the `implant` equipment family with its `neural_implant` kind, electronic warfare and drone operators. Each acts as an older kind for the tables that read it. Spec 13 plans constructs with literal orders (3.3a reference pass 4) and lists "artificial minds" in one row of F44. Nothing models a mind as something that can live in a made thing, be copied, saved, restored, moved or merged, wake from complexity, hold rights, be owned, be attacked through a network or exceed its makers. Augmentation exists only as a prosthesis for a lost part. There are no networks, no intrusion, no surveillance state, no self-making machines, no economy of abundance and no relic technology.
2. **Powers that are not rites.** Magic is modelled as rites: designed in laboratories, learned from texts, cast with components, drawn from six fixed external sources (`MagicSource`: ley, divine, blood, soul, reagent, void), made reliable by a paradigm theory and broken by iron. A being's own innate power, drawn from itself, used at once without a rite, resisted by discipline, strained by use, possible in a world without magic, amplified by devices and joined in linked minds, cannot be expressed. A world cannot author a source of its own. Whole populations hiding a truth from the rest of the world cannot be expressed: secrets (F20) are individual.
3. **Technology made of life.** W42 added the `bioship` frame, the `grown` building form and `vat_grown` food, all acting as older kinds. Breeding exists as bloodline plans (W22) and genetics as F26. Nothing models a made thing that is alive: that grows, eats, heals, breeds, ages, sickens, escapes and evolves, and that can be designed from the traits of organisms the makers can reach.

### 0.2 Numbering and placement

- **Waves.** W1–W41 are planned in spec 13 Part J; W42 (breadth across settings, 10.18) and W43 (genesis from the seed, 10.19) were added later and are done. The waves of this spec are **W44**, **W45**, **W46**, **W47**, **W48**, **W49**, **W50** and **W51**.
- **Identifiers continue spec 13's series** so that no identifier is shared:
  - shared foundations **F50–F56** (spec 13 ends at F49);
  - wave sections **44.1…**, **45.1…**, **46.1…**, **47.0…**, **48.0…**, **49.0…**, **50.0…**, **51.0…**, and the foundations **F57** and **F58**;
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
9. **W49** (decided the same day) keeps every happening of every kind in full: typed facts, roles, steps, every change before and after with its terms, exact moments and places, causes, witnesses and the past at any moment, all kept for ever (Part 9, K.42).
10. **W50** (decided the same day) closes the granularity left inside existing mechanics by a closed audit on fixed lists (Part 10, K.46).
11. **W51** (decided the same day) closes every gap found by the open search of 51.0, each built on what exists and on what spec 13 plans, so nothing is built twice (Part 11, K.50–K.53).

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
| Construct instruction sets, literalism, maker's death | 3.3a reference pass 4 (W26, done, `e13a671d`) | none: W26 built the tables in F56's shape (`db/tables/constructs.py`: `constructs`, `instruction_sets`, `instruction_orders`; enums `InstructionBinding`, `CommandToken`, `OrderKind`, `OrderCondition` and `MindWill` in `domain/enums/constructs.py`; engine `engine/constructs/making.py`, `orders.py`, `wards.py`; levers `construct:*`, `instruction_set:*`, `instruction_order:*`; son tools `build_construct`, `order_construct`, `seize_construct`; mortal tool `command_construct`) | W44 widens F56 from constructs to every made thing that acts, reusing these tables, enums, levers and tools, and moves construct will into `mind_profiles` by fixup. |
| Technology eras, electrical and information families | F44 (W33, planned) | W44 builds the computation, network and fabrication techniques it needs; W46 builds the engineering techniques of life | F44 later adds the other families on the same machinery. |
| Biology variants (construct, hive, incorporeal and the rest) | F46 (W37, planned) | W44 builds the `construct` variant view for made peoples; W46 builds the variant rows its designs need | F46 later adds the remaining variants. |
| Non-vocal language modality | 8.1 reference pass 3 (planned) | W44 adds the `data` modality, W45 the `mind` modality, W46 the `chemical` modality, each on one `modality` column | The column and its reader are built once. |
| Divination systems and prescience | W25 (done, `14b0fedf`) | none: W25 built `divination_systems`, `divinations`, `foresights` and `forecast_models` | W45 adds foresights written by innate powers (`power_id`, strain) and W44 the `made_oracle` source. |
| Emotion-fed gods | W25 (done, `14b0fedf`) | none: W25 built `god_feedings` and `emotion_harvests` | F52's `emotion` locus reads them: a source of locus `emotion` draws on the same harvests, so gods and mortal users compete for one pool. |
| Rivers with flow, estuaries, flood plains, snowmelt floods, aquifers | spec 13 6.1 reference pass (planned) | whichever wave runs first builds it fully (0.7) | W50 50.23 reads its rivers and adds ice, sediment, coasts and local climate |
| Fossil beds and their readings | spec 13 6.2 reference pass 7 (planned) | whichever wave runs first builds it fully | W50 50.27 adds preservation, richness, fossil fuels and revival |
| Flares and auroras | spec 13 10.1 reference pass | whichever wave runs first builds it fully | W50 50.22 makes the flare one space weather kind and adds fields, shielding, storms, outages and compass error |
| Climate oscillations and their prediction | spec 13 10.7 reference pass 5 | whichever wave runs first builds it fully | W50 50.28 types forecasting methods |
| Economic systems per polity | spec 13 4.6 reference pass 6 (W35, planned) | whichever wave runs first builds it fully | W51 51.1 types the system as four axes per polity or sector; the five systems become rows of `economic_order_kinds` |
| Exchange rates, money changers, bills of exchange | spec 13 6.4 reference pass 6 (W35, planned) | whichever wave runs first builds it fully | W50 50.3 keeps the rates on one table with spreads; W51 51.5 pegs and monetary authorities read them |
| Named units and battle honours | spec 13 5.1 reference pass 6 (planned) | whichever wave runs first builds it fully | W51 51.24 honours conferred on persons share the conferral model; units hold battle honours as honours |
| Performance troupes | spec 13 7.4 reference pass (faction kind `troupe`, planned) | built by spec 13 | W51 51.2 governance and 51.4 labour reach troupes as organisations |
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

W26 built both tables (`db/tables/constructs.py`) for constructs; W44 keeps their columns and widens `owner_entity_id` to any made thing that acts.

- Set (`instruction_sets`): `owner_entity_id`, `binding` (`InstructionBinding`, named so because faith already has a `BindingKind` for spirit bindings: `none`, `order`, `oath`, `geas`, `seal`, `ownership`, `lease`, `symbiosis`), `command_token` (`CommandToken`: `none`, `item` (a held object), `word`, `bloodline`, `office`, `network_key`), `token_entity_id`, `holder_node_id`, `kill_switch` (boolean) with `kill_token_entity_id`, `literalness` (0–100).
- Orders (`instruction_orders`): `set_id`, `kind` (`OrderKind`: `guard`, `serve`, `obey_holder`, `build`, `gather`, `protect`, `destroy`, `report`, `maintain`, `replicate`, `hold_still`, `follow`, `forbid`), `target_node_id`, `priority`, `condition` (`OrderCondition`: `always`, `while_maker_lives`, `until_date`, `when_attacked`, `when_token_shown`), `until_epoch`, `lapsed`.

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
| F56 instructions | `instruction_sets`, `instruction_orders` (W26) | `minds`, `replicators`, beside W26's `keep_constructs` and `keep_seals` | W26's `instruction_set:create/edit/delete/resolve` and `instruction_order:*`, widened to every made thing that acts (a token moves by editing `token_entity_id`; `resolve` recomputes the holder) | W26's `OrdersPanel` (`features/pursuits/ConstructPanels.tsx`), widened to every instructed thing | W26's mortal `command_construct` and son `order_construct`, `seize_construct`, widened to every instructed thing; seizure through networks (44.12) and mind powers (45.10) | "Orders" in entries | token refs exist; orders have valid targets | drones, works with control systems and instructed minds get sets; W26 constructs keep theirs |
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


**Cross-cutting layers (6.6) for W44.**

| Layer | What W44 gives it |
|---|---|
| Record of what happened | incident keys for making, waking, will changes, copies, saves, restores, merges, seat loss, ends with a seat, network outages and ledgers, intrusions, realm freezes and ends, line drift, voyages and swarms waking, made peoples formed |
| What changed | will changes kept in `mind_will_changes`; makings in `mind_makings`; outages in `network_outages`; intrusions append-only |
| When | every history row carries its epoch; saved states carry `taken_epoch`, restores leave a memory gap naming the span |
| Where | seats name the node that holds a mind; realms name their host; presences name the land of a line; ledgers name their network |
| Why | crimes name the act and the law that made it one; outages name their cause, a shortage included; seat loss names the lost seat |
| Who knows | intrusions carry attribution; copies of captives are remembered by the captive's home; mind crimes go to the courts with witnesses |
| How it is told | lines told from typed fields, counted through `several()` |
| What it was | will history, saved states and the lineage bonds `copy_of`, `restored_from`, `hosted_by`, `merged_into` and `divided_from` |
| What is kept | append-only histories; ended realms stay as sealed records; nothing is folded |
| Names | swarm minds, drifted lines, network ledgers and made peoples are named from their sources |
| Look | the `made` dimension look is a pattern at render time; no medium is fixed |
| Model-facing wording | every W44 tool text, result and context line read in full against rule 2 |
| Control | every W44 table has god levers or the generic record levers; a construct's will edit goes to its mind profile |
| Reach | Mind, Augments, Network and Made world sections sit in `ThingSections` for every kind of node |
| Books | W44 records render through `services/books/typed.py` and the Records of the Cosmos appendix |
| Search | W44 records are found by their typed fields through the record index |
| Integrity and legacy | `services/integrity/minds_links.py` (seats, states, gateways, shares, substrates, copies, empty profiles); fixups `made.legacy_backfill` and `networks.relay_backfill`; migrations for the new enum values |
| Speed | profiles are seeded only for things with a mind, so the tick no longer carries a row per settlement, place and item |

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

**Attributes.** Foresights use the `foresights` table built by W25 (on main since `14b0fedf`, enums in `domain/enums/sacred.py`): `seer_node_id` (a mortal, made mind, god or rite source), `subject_node_id` (nullable), `predicate` and `args` (the prophecy condition language of 8.7), `horizon` (years), `due_epoch`, `certainty` (0–100), `source` (`ForesightSource`: `power`, `divination`, `god`; W25 landed it without `made_oracle`, which W44 adds when made minds exist), `divination_id` (set when a divination rite wrote it), `status` (`ForesightStatus`: `pending`, `fulfilled`, `failed`, `clouded`), `checked_epoch`, `made_epoch`, `locked`. W45 adds only what powers need: the power that produced it (`power_id`, nullable) and the strain it cost. If W25 lands its final names differently, this section follows them.

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


**Cross-cutting layers (6.6) for W45.**

| Layer | What W45 gives it |
|---|---|
| Record of what happened | incident keys for sources made and run thin, systems shaped, powers stirring, breaking loose, used, giving out, granted and taken back, gestalts and hive minds, bands, broken vows, breaches, revelations and folk going into hiding |
| What changed | breaches are append-only; spans keep the value an effect replaced and restore it when they end |
| When | powers carry the epochs they were gained and last used; spans name the epoch they end; breaches their epoch; knowledge the epoch it was weighed and revealed |
| Where | densities belong to lands, sources to their scope, breaches to their place, knowledge to its population |
| Why | a refused use names the law, the restriction or the unknown source; a breach names its cause and the keepers' answer |
| Who knows | knowledge and belief per population, breaches name their witnesses, keepers and seekers are rows, a mortal sees only the truths it keeps, seeks or has heard |
| How it is told | lines told from typed fields; the stock image of a power burning out was rewritten plainly |
| What it was | breaches and foresights keep their history; a revealed truth fades back into hiding by neglect |
| What is kept | nothing folded; ended spans are deleted only once their value is restored |
| Names | sources, systems and bands are named by the god or from their founder |
| Look | no medium fixed; device effects, sources and truths are typed |
| Model-facing wording | every W45 tool text, result and context line read in full against rule 2 |
| Control | dedicated levers for sources, systems, powers, their parts and truths; record levers for densities, knowledge, laws, stances, registries, spans, keepers, seekers and knowledge; profile levers for attitudes and lines |
| Reach | Powers, Sources of power, Systems of power and Hidden truths sit in `ThingSections` for every kind of node; the atlas shows hidden places |
| Books | W45 records render through `services/books/typed.py`; breach witnesses render as names |
| Search | W45 records are found by their typed fields through the record index |
| Integrity and legacy | `powers.legacy_backfill`; migration `eb2a138f5f58` retypes every column whose enum gained values |
| Speed | densities exist only where a source is drawn; devices and resistances read per use |

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
- Step 0 of W44 also adds `scripts/check_inventory.py` and `docs/spec/inventory.md`: one row for every table, enum type, engine step, incident kind, agent tool, god lever, screen and model-facing text file, each with its status against rules 1–8 and the layers of 6.6 (proven by a named guard, done, or the spec row that closes it). The commit gate fails when the code holds a countable thing without a row, or when a row names a guard that does not exist (6.7).
- A row is done only when every work column is filled (or `n/a` where it does not apply) and its tests pass. `deferred-approved` needs the user's explicit approval.
- A wave is done when every row of the wave is done, its audit has been run against this spec, screenshots have been taken and opened, and it is committed, pushed and deployed.

### 5.11 Execution order inside each wave

**W44:** coverage step → F50 mind seats and bonds → F56 instructions → F51 networks (entity type, visuals) → 44.2–44.5 making, awakening, will, inner life → 44.6–44.7 law, faith, souls → 44.8 continuity → 44.9–44.10 augments and interfaces → 44.10a made realms → 44.11–44.14 networks in society, intrusion, surveillance, information → 44.15 companies → 44.16 replicators → 44.17 abundance → F55 and 44.18 relics, collapse, salvage → 44.19–44.21 made peoples, war, archives → genesis, prompts, book, Codex, screens → fixups → audit.

**W45:** F52 sources and tides → 45.1 systems → 45.3 grammar → 45.4–45.7 powers, awakening, training, devices → 45.8–45.11 gestalts, foresight, mind and outward powers → 45.12–45.15 society, exposure, war, gods → F53 and 45.16–45.17 concealment → genesis, prompts, book, Codex, screens → fixups → audit.

**W46:** F54 profiles and lines → 46.2–46.3 methods and design → 46.4–46.7 crops, structures, vessels, gear → 46.8–46.10 bodies, clones, symbionts → 46.11–46.13 medicine and disease, production, links and computation → 46.14–46.16 world shaping, designed sapience, escape and decay → 46.17–46.20 law, faith, economy, war, gods → genesis, prompts, book, Codex, screens → fixups → audit.

**W47:** step 0 audit of built sections against 47.8 → guards (`check_acts_as.py`, enum scan, `check_enum_values_read.py`, `check_spec_depth.py`) written first so they list every gap → 47.1 structures → 47.2 eras, energy, medicine, logistics, signals, extraction → 47.3 crime, punishment, trial, unions, taxes, revolts → 47.4 sweep → 47.5 god layer → 47.6 typed models and renames → 47.7 unread values → 47.8 thin sections → 47.10 mishaps, fortune and drawn harm → screens, Codex, book, prompts → fixups → audit with every guard at zero. Then 47.13 integrity for every table and 47.14 the full read of model-facing text, each with its guard.

**W48:** `catalog/concepts.py` and both guards first (they list every gap) → F57 machinery → 48.1 goods → 48.2 food, cuisine, drink → 48.3 dress, colour, scent, emblems → 48.4 household goods, tools, instruments, games, substances → 48.5 money, materials, preservation, species products, production methods → 48.6 society → 48.7 culture → 48.8 nature and cosmos → 48.9 unification → 48.10 property catalogues for all 250 → genesis, Kinds library, Ways of life, Codex, book, prompts → fixups → audit with both guards at zero.

**W49:** see 49.10 (guards and the kinds catalogue first, then kinds, roles, facts and steps → change capture → moments, places, terms and causes → every process group of Appendix 49.A with engagements and duels → witnesses, rumours, rendering and folding as a view → the past at any moment → surfaces, fixups and bands → audit).

**W50:** see 50.20.

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

**New enums.** `MindSeat`, `MindOrigin`, `MindAffect`, `MindPurpose`, `MindUpkeep`, `MindMaking`, `StateMedium`, `NetworkCarrier`, `NetworkAccess`, `NodeRole`, `SourceLocus`, `PowerCost`, `SourceRenewal`, `SourceAccess`, `ResistanceKind`, `PowerVisibility`, `PowerHazard`, `SourceRelation`, `PowerStructure`, `Learnability`, `PowerOrigin`, `PowerState`, `RestrictionKind`, `PowerDeviceEffect`, `HiddenTruthKind`, `ConcealScope`, `KeeperRole`, `SeekerAim`, `TruthAttitude`, `BreachCause`, `Metabolism`, `GrowthStage`, `Fertility`, `CultivationMethod`, `HostPlacement`, `HostRelation`, `RelicState`, `RelicUse`, `AugmentSlot`, `AugmentKind`, `AugmentMake`, `IntrusionTarget`, `IntrusionApproach`, `IntrusionAim`, `Attribution`, `Authenticity`, `SurveillanceFocus`, `CompanyCharter`, `ReplicatorScale`, `ReplicatorOutput`, `ReplicatorStage`, `RealmPurpose`, `RealmEntry`, `RealmAwareness`, `GiftedAttitude`. Their values are the ones listed where each is defined. `MindWill`, `InstructionBinding`, `CommandToken`, `OrderKind` and `OrderCondition` already exist (W26, `domain/enums/constructs.py`) and are reused, not redefined.

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

### 6.6 Cross-cutting layers

The sweeps above went through concepts, genres and mechanic families. This sweep goes through the layers that cross every mechanic, so that what each mechanic does is also kept, dated, placed, explained, told and controlled. It was added on 2026-11-14 after the record of events (W49) was found shallow although every mechanic beneath it was deep. Each row says where the layer lives and where it is completed.

| Layer | What it must give every thing and every happening | Built | Completed by |
|---|---|---|---|
| Record of what happened | typed kind, roles, facts, steps, outcome | incidents, collections, life logs (spec 13 F10) | W49 F58.1–F58.4 |
| What changed | every value before and after, by whom | actor tool calls only (`db/ledger_capture.py`) | W49 F58.5 |
| When | in-world moment by the world's calendar, ordered by cause | year in phase write order | W49 F58.6 |
| Where | the most precise place, origin and destination | 31 write sites | W49 F58.6 |
| Why | the true cause and the terms of every number | modifier stacks, battle factors; causes guessed | W49 F58.7–F58.8 |
| Who knows | witnesses, rumours with typed distortions, memories, hidden truths | F7, F11 (done), F53 (W45) | W49 F58.9 |
| How it is told | rendered from fields, plain, re-renderable in any language, three tiers | English lines, decision 71 | W49 F58.10 |
| What it was | any record, node or map at any earlier moment | none | W49 F58.11 |
| What is kept | everything, for ever; no folding away, sampling or cutting | folding hid and capped records | W49 F58.12, K.42 |
| Names | a name for every made, born and notable thing and happening, from the world's languages | naming prompts, collection titles | W49 F58.10 (happenings), W48 (kinds) |
| Look | visual direction from typed fields, style at render time | image prompt templates, 0.5 rule 8 | 0.5, 5.5 |
| Model-facing wording | every string read in full against rule 2 | pattern guards only | 47.14 (ledger of the full read) |
| Control | create, edit, hold, delete every record; revert any change | god levers, `check_control.py` | W49 49.5 (records and reverts) |
| Reach | every feature for every kind of node | `ThingSections`, `check_wiring.py` | W49 History section |
| Books | every record in the lore book and the Codex, never cut | rule 7, `services/books/typed.py` | W49 49.5, `check_record_cuts.py` |
| Search | every record queryable by its typed fields | `services/search.py` (text) | W49 49.5 |
| Integrity and legacy | checks and recorded fixups for every value of every table | `services/integrity` (132 of 676 tables), fixups | 47.13 (every table), each wave's compliance catalogue |
| Speed | measured bands for every added cost | 5.12a | W49 49.8 |

Every future wave fills this table for what it adds, beside its compliance catalogue.

### 6.7 Closed inventory audit (2026-11-14)

The sweeps of 6.1–6.6 searched for what might be missing, so each new question could still find something. This audit instead enumerated, by script, every countable thing in the code and in the specs. It checked each against the same criteria (rules 1–8 of `CLAUDE.md` and the layers of 6.6) and separated what a guard already proves from what nothing proves.

| Axis | Count | Proven by a guard | Not proven before this audit | Closed by |
|---|---|---|---|---|
| Tables | 676 (10 bookkeeping) | read by a phase, written with god levers (`check_wiring.py`, `check_control.py`), book and Codex sections, every served field read, held nodes respected | integrity: 132 tables appear in `services/integrity`, 544 have no check beyond foreign keys; history, changes, moments and terms | 47.13; W49 F58.5–F58.7 |
| Enums | 819 types, 7,671 values | no unused type, complete label maps | every value read; two layers for content concepts | W47 `check_enum_values_read.py`; W48 |
| Engine steps | 389 | god control held and forced, eager epochs | each write recorded with its happening | W49 `test_every_change_recorded.py` |
| Incident kinds | 935 keys in 252 families | none | roles, facts, steps, template, place, clock | W49 F58.1, Appendix 49.A |
| Agent tools | 398 (239 son, 159 mortal) | every tool runs to success, every field described | — | — |
| God levers | 1,877 | every lever runs with real values, unique, reached from a screen | revert of any change | W49 49.5 |
| Screens | 876 components in 66 features | hidden controls, raw ids, labels, paging, orphans, every field read | — (look and polish are checked by screenshots, rule 5) | — |
| Model-facing text | 34,865 prose strings in 1,305 files, 194 templates | pattern families of `check_prompt_bias.py`, `check_canned_lines.py` | a full read: a lexicon sweep found 255 hits, many of them fixed images in our own wording | 47.14 (the hits found are fixed with this audit) |
| Spec 13 items | 843 (537 done, 1 in progress, 305 planned) | `spec_coverage.py check` | depth of planned sections | W47 47.8 and `check_spec_depth.py` |
| Spec 16 items | six waves | — | coverage matrix | 5.10 step 0 |
| The inventory itself | — | — | nothing failed when a new countable thing appeared without being judged | 5.10 step 0: `scripts/check_inventory.py` |
| Facets of life (OCM subcategories) | 689 | — | 104 label-only, 77 absent, 241 partial | W50 (Part 10, Appendix 50.A, `check_ocm_coverage.py`) |
| Registered mechanics | 572 | — | 102 with at most one coupling | W50 50.14, `check_mechanic_couplings.py` |
| Node types at depth | 51 | — | 23 below target, 7 read by nothing | W50 50.15, `depth_metric.py check` |
| Open search for what the fixed lists cannot name | 1,197 concept patterns, 693 Dewey sections, 103 human universals, genre mechanics, lifecycle, scale and actor axes | — | 30 gaps: one planned in spec 13, the rest absent | W51 (Part 11, 51.0) |

**Model context.** F58.12 keeps every record. The model receives records through retrieval (paged reads and the `recall_event` tool), never through silent truncation, because no context holds an unbounded history.

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

### 47.13 Integrity for every table

Measurement (2026-11-14): `services/integrity` names 132 of 676 tables. The other 544 have no check beyond their foreign keys, and nothing proves their values stay valid after engine steps, levers, imports and fixups.

1. **Generic checks from the schema**, for every table:
   - percent and 0–100 columns stay in range;
   - enum columns hold declared values, including values stored as text in JSON lists, checked against the enum their catalogue names;
   - node and entity references point at existing rows of an allowed kind;
   - `locked` lists name real columns;
   - profile tables keep one row per thing;
   - epochs are never in the future;
   - treasury amounts follow `engine/economy/purse.py`.

   They are derived from column types and catalogue metadata, so a new table is covered on creation.
2. **Typed invariants** in `catalog/invariants.py`, a `total()` table over every table, for what the schema cannot say:
   - a captive is held by a living captor;
   - a ruler holds the seat they rule from;
   - an order's target exists;
   - a construct's maker or seal holder is valid;
   - every cross-row rule a section of spec 13 or 16 states in its integrity column.

   A table with no rule beyond the generic checks says so with its reason.
3. **Repair or report.** Each check either repairs (clamp, drop a dangling reference, re-derive a derived value) with a recorded change (W49 F58.5) or reports to the integrity screen with a god lever to resolve it, never silently.
4. **Guard.** `scripts/check_integrity_coverage.py` fails when a table has no row in `catalog/invariants.py`. `tests/services/integrity/test_every_invariant.py` breaks each invariant on a seeded world and proves it is found.

**Implemented as.** `catalog/invariants.py` names the generic checks (`GenericCheck`, each with its remedy) and the typed invariants (`TYPED`, keyed by table) with their texts; the catalogue layer cannot read the schema, so `services/integrity/invariants.py` `coverage()` walks every table of the metadata and gives it its typed invariants or the reason it needs none (a profile keyed by its thing, columns all covered by the generic checks, or a free-form JSON record kept by its writer), so a new table is covered on creation. The generic sweep clamps bounded columns, sets past epochs back to the present and drops lost node ids from `*_node_ids` lists, all as repairs run with the data repairs at startup and by the integrity task "Check every table"; enum values outside their lists and held names that are not columns are reported. References are kept by the database's foreign keys and treasury amounts by `scripts/check_coin_units.py`. Reported findings are listed on the engine page under "Findings that wait for your word" (`GET /integrity/findings`), each resolved by the god (`POST /integrity/findings/resolve`). The guard also fails when a typed invariant names a missing table, has no check, or is never broken in the test.

### 47.14 A full read of model-facing text

Measurement (2026-11-14): 34,865 prose strings in 1,305 files and 194 templates reach the model or the chronicle; pattern guards cannot see images that use ordinary words. A lexicon sweep found 255 hits. Among them were the following images in our own wording, fixed with this audit:

- the forgotten world "sinking into mist" and "no hand reaching into the fog";
- the dead whose "bones do not stir";
- doom omens of "wells turned red, birds flew backwards";
- leak horror of "nights a moment too long, shadows a step behind";
- eclipse lines where "seers whisper the same prophecy";
- a vigil kept "by fire and lamp";
- "the cosmos took a breath";
- an example list of forbidden names given to the model;
- tool texts judging an act as "terrible".

1. **A ledger of the read.** `docs/spec/model-text-ledger.md` lists every file that holds model-facing prose, the strings in it and the date it was read in full against rule 2. A file enters the ledger only after every string in it has been read and rewritten where it pushes a theme, tone, conflict, gender or look the seed did not ask for.
2. **Guard.** `scripts/check_text_ledger.py` fails when a file with model-facing prose is missing from the ledger, or when its strings changed after the date it was read.
3. **Order.**
   - Templates and tool texts first.
   - Then chronicle and result lines.
   - Then catalogue descriptions: world types, phenomena, peoples, afflictions, deposits, relics.
   - Then everything else.

   Each kind description says what the kind is and does, plainly. A fantasy kind keeps its function (a world that is a god's body, a star that perceives) without the imagery of bone, blood, fog or eyes.

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

**Rules namespaces.** `cuisine` (dish invention, fusion by contact, feast weights), `drink` (strength, dependence, water safety) and `nutrition` (nourishment per nutrient class), all extended, beside `kinds` (48.0). God levers and screens are those of F57 (48.13).

### 48.3 Clothing, adornment, colour and scent

**Garments** (`garment_kinds`): category `GarmentCategory` (`body_wrap`, `upper`, `lower`, `full_body`, `outer_layer`, `head`, `face_covering`, `feet`, `hands`, `undergarment`, `fastening`, `ornament`, `uniform`, `ritual_dress`, `work_protection`, `environment_suit`, `body_marking` (paint and marks, W29)), materials (world materials), layer, warmth, protection, climate fit, cost, **status signal** (class, rank, office, faith), **modesty coverage** (read against the culture's norms), occasions, **wearing rule** (`WearingRule`: `anyone`, `by_role`, `by_class`, `by_age`, `by_faith`, `by_rank`, `by_gender_as_the_culture_holds`; the last is culture data only, never a default), colours, fashion cycle (novelty).

**Behaviours.** Dress codes (F35), sumptuary laws, uniforms of armies, offices, guilds and orders, fashion diffusion through prestige and contact, climate exposure (47.10 mishaps and exposure harm), textile and dye demand, identity facets (F43), emblems on dress, theft and gifting of fine dress.

**Colours** (`colour_terms` per language: basic colour terms by the language's stage, read by naming and description), **colour meanings** per culture (typed: `mourning`, `rank`, `sacred`, `danger`, `joy`, `faction`, `none`, written from culture and seed), and **colour availability** from dyes and pigments (rare colours carry prestige).

**Scents** (`scent_kinds`): category `ScentUse` (`burned`, `worn`, `anointed`, `household`, `ritual`, `medicinal`, `signal` (for peoples with scent language)), materials, prestige, uses in rites and trade.

**Emblems** (`emblem_systems` per culture: `EmblemSystem`: `heraldry` (the existing heraldic enums), `seal`, `banner`, `totem`, `badge`, `monogram`, `mark`, `glyph`), so heraldry is one emblem system among many.

**Rules namespaces.** `fashion` (extended: diffusion by prestige and contact, novelty decline), `dress` (new: dress codes, sumptuary fines, climate fit), `colours` (new: term stages by language, dye prestige) and `scents` (new: prestige and rite use), beside `kinds` (48.0). God levers and screens are those of F57 (48.13).

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
- **Ship crews.** `CrewStation` (gunners, riggers, marines, officers, rowers) gains `pilots`, `engineers`, `sensor_operators`, `medics`, `handlers` (living vessels), `link_operators` (mind links), read per vehicle family.
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


## Part 9. W49 — The record of events: every happening kept and told in full

### 49.0 Scope and the measurement behind it

W49 makes the record of what happens as deep as the engine that makes it happen. Every happening of every kind (not only fights) is kept with what happened, who took part in which role, with what, how much, where and when exactly, why (its cause and the terms behind each number), how (its steps), what it changed (every value before and after) and who saw it. Its text is told from those fields, and all of it is kept for ever in every world.

**Measurement (2026-11-14, by script over `backend/src/aerona`).**

| Finding | Where | Measure |
|---|---|---|
| One write path | `engine/context.py` `TickContext.chronicle`, `engine/notes.py` `note`, `db/repositories/chronicle.py` `ChronicleRepository.append` | each happening writes one English line (`chronicle`) and one `incidents` row (kind = template key, participants, place, cause, magnitude) |
| Write sites and kinds | engine and services | 834 `note` calls, about 190 direct `chronicle` calls; 935 template keys found literally in 252 families (70 of them built from an enum value at run time), more passed through variables |
| No typed fields | `IncidentRow`, `ChronicleRow` | the only content is the rendered sentence; what, how much, with what, before and after are not stored, so nothing can be re-told, translated or queried |
| Thin lines | 754 literal `note` texts | 73 carry a quantity, 55 a reason; "A child of X and Y was born." names neither the child nor the place; "X bought Y from Z on credit." has no price; "A champion was named in the league." names no one |
| Roles mostly lost | `catalog/incident_roles.py` `INCIDENT_ROLES` | 40 of the keys have a role map; every other participant is stored as `subject`, so doer and done-to are not told apart |
| Causes mostly guessed | `cause_incident_id=` at 8 sites, `caused_by` in `phases/warfare.py`, `killing_incident` in `lifecycle/mortal_death.py` | every other cause is guessed by `ChronicleRepository.cause_of` (an earlier incident of the same epoch sharing a participant) |
| Place rarely set | `place_entity_id=` | 31 sites |
| Time is write order | `_stamp_year`, `chronicle_year`, `EpochYearCursorRow` | a year rolled forward in phase order inside the epoch window; no season, day or hour; a sickness written in a late phase is always "after" a war written early, whatever happened first |
| Changes only counted | `ctx.count` | 817 sites count a change and keep no record of what changed, by how much or why |
| Before and after only for actors | `db/ledger_capture.py`, `ledger_changes` | the full row before and after is captured for creator, son, mortal and Fate tool calls, never for engine steps |
| Detail computed then dropped | `military/duels.py` `Bout.log`; `vehicles/sections.py` `StrikeResult.events` (never filled); `operations/sail.py` broadsides, sections, fire and flooding per round; `military/battle.py` phase lines; `body/treatment.py` steps | the duel log is built and discarded; sea fights reach the chronicle as "X met Y at sea and beat it"; the battle phase line is one sentence ("the volleys flew") |
| Records hidden and cut | `engine/notes.py` `fold_tick_lines` | when `chronicle_fold_threshold` (3) lines share a key in an epoch, every original is rewritten to kind `engine_raw` and hidden, a summary "…; N more events of the same kind happened this epoch." replaces them, and the summary links at most `folded_chronicle_ids_cap` (40) entities; the Codex (`services/codex.py`), node entries (`services/books/model.py` `entry_chronicle`) and search (`services/search.py`) read only visible or non-raw lines, so the folded happenings vanished from them and from the node, world, star and old-god drawers (fixed on 2026-11-14: every reader goes through `shown_lines()`, `kept_lines()` or `feed_lines()`, the Codex gained the Event Log, and `scripts/check_record_cuts.py` guards it; the folding itself is retired by F58.10) |
| Narrow histories | 19 tables (`item_history`, `office_history`, `settlement_history`, `trait_history`, `sound_changes`, `expedition_logs`, `formation_histories`, …) | each keeps one subject in its own shape |
| Teller sees one line | `prompts/templates/chronicler/_facts.md.j2` | the chronicler receives the one-line texts, so detail is either missing or made up |
| No past state | engine, API, frontend | no node, map or value can be shown as it was at an earlier moment |
| Specs | spec 13 F10, F10 reference pass, decision 71; 5.16 here | incidents, collections, life logs, causality graph and template families are specified; a home for typed fields, steps, changes, terms, witnesses, moments, tiers and past states is not |

W49 closes every row. The existing incident table, collections, causality graph, chronicle feed, ledger capture and history tables are kept and built on (0.6); nothing they hold is lost.

### 49.1 F58. The record of events

#### F58.1 Incident kinds (`catalog/incident_kinds.py`)

Every template key becomes an **incident kind**: a `total()` catalogue entry, declared once, that every write is checked against.

| Field | Content |
|---|---|
| `key` | the template key (`family.name`); keys built from an enum declare their prefix and the enum, and the catalogue expands one entry per value |
| `family` | the family (Appendix 49.A) and its process group (49.2) |
| `roles` | the ordered typed roles of its participants (`IncidentRole`, F58.2), each with the node kinds it accepts and whether it is required |
| `facts` | its fact schema (F58.3): each field's key, value type, unit, enum and whether it is required |
| `steps` | the step actions (F58.4) a happening of this kind may record, or none |
| `template` | the English template that tells it from its roles and facts, plain, with no images and no tone (rule 2) |
| `place` | `required`, `when_known` or `none`, and the most precise place kind expected |
| `clock` | the process clock that dates it (F58.6) |
| `terms` | whether its numbers carry terms (F58.7) |
| `collection` | the collection kind it joins (F10 reference pass), replacing the prefix guess of `engine/history/collections.py` `kind_of_key` |
| `feed`, `chronicle_kind`, `magnitude` | the feed category, chronicle kind and magnitude rule that `note` callers pass today |

`incidents.kind` holds a catalogue key; a write with an unknown key, a missing required role or fact, or a fact of the wrong type raises `ValidationFailedError`.

#### F58.2 Roles

`IncidentRole` widens from `subject`, `actor`, `target`, `witness`, `place` to every role a happening can give:

`subject`, `actor`, `co_actor`, `target`, `victim`, `beneficiary`, `opponent`, `ally`, `leader`, `member`, `giver`, `receiver`, `buyer`, `seller`, `lender`, `borrower`, `maker`, `owner`, `heir`, `predecessor`, `successor`, `accuser`, `accused`, `judge`, `advocate`, `teacher`, `learner`, `healer`, `patient`, `parent`, `child`, `spouse`, `officiant`, `host`, `guest`, `envoy`, `mediator`, `authority` (who allowed or ordered it), `patron` (a god or power that helped), `instrument` (a thing, beast, vessel, structure or work used), `product` (what it made), `origin`, `destination`, `place`, `witness`, `teller` (who spread an account of it).

Every kind declares its roles, so every participant of every happening is stored with its true role.

#### F58.3 Facts (`incident_facts`)

Typed fields of a happening, one row per value: `incident_id`, `key` (declared by the kind), `position` (for lists), and exactly one value: `node_id`, `number` with `unit`, `enum_name` with `enum_value` (two text columns validated against the declared enum, never a JSON column claiming enums), or `name` (only for a name the world itself produced).

`FactUnit`: `count`, `people`, `coin` (treasury units, through `engine/economy/purse.py`), `wealth_points`, `percent`, `hp`, `severity`, `years`, `seasons`, `days`, `hours`, `distance`, `area`, `mass`, `volume`, `tons`, `essence`, `renown`, `standing`, `knowledge`, `strength`, `speed`, `temperature`, `energy`, `none`.

Each kind's schema says what it holds. The kind lists its minimum fields; the rule is that every value the engine computed for the happening (amounts, prices, counts, scores, rolls with their thresholds, chosen options, qualities, durations, distances) is a fact.

#### F58.4 Steps (`incident_steps`, `incident_step_states`)

How a happening unfolded, one row per step:

| Column | Content |
|---|---|
| `incident_id`, `position`, `round`, `parent_step_id` | order; rounds for contests; nesting (a boarding inside a vessel engagement, a duel inside a battle, a rite inside a festival) |
| `moment` | the in-world moment of the step (F58.6) |
| `actor_node_id`, `target_node_id` | who acted on whom |
| `action` | `StepAction` (below) |
| `instrument_kind`, `instrument_node_id`, `instrument_key` | `InstrumentKind`: `item`, `equipment_model`, `vehicle_weapon`, `vehicle`, `structure`, `creature`, `power`, `rite`, `tool_kind`, `substance`, `text`, `network`, `body` (an unarmed blow, a bite), `none`; the node, or the key of a model or kind |
| `locus_kind`, `locus_key`, `locus_node_id` | `StepLocus`: `body_part` (`BodyPart`), `vehicle_section` (`VehicleSection`), `structure_section`, `room`, `district`, `settlement`, `region`, `route`, `sea`, `sky`, `orbit`, `realm`, `network_node`, `none` |
| `damage_type` | `DamageType` when harm is done |
| `amount`, `unit` | how much (a count, an amount of coin, hp, a distance) |
| `outcome` | `StepOutcome` (below) |
| `record_table`, `record_key` | the record the step made or changed (an injury, a section state, an item history row, a bond, a captive) |

`incident_step_states`: `step_id`, `node_id`, `state` (`StepState`): `prone`, `risen`, `disarmed`, `stunned`, `unconscious`, `bleeding`, `burning`, `blinded`, `restrained`, `fleeing`, `yielded`, `captured`, `freed`, `hidden`, `revealed`, `exhausted`, `possessed`, `flooding`, `breached`, `depressurised`, `adrift`, `disabled`, `aground`, `grounded`, `shielded`, `unshielded`, `cut_off`, `encircled`, `routed`, `rallied`.

**`StepAction`** (a process enum, 48.C; every value is read by the renderer and by the steps that produce it):

- **Contest of bodies:** `close`, `strike`, `thrust`, `cut`, `shoot`, `throw`, `cast`, `feint`, `block`, `parry`, `dodge`, `grapple`, `throw_down`, `choke`, `lock`, `bite`, `disarm`, `charge`, `trample`, `fall`, `rise`, `flee`, `pursue`, `yield`, `spare`, `finish`, `rescue`, `carry_off`.
- **Bodies in groups:** `deploy`, `advance`, `hold`, `volley`, `wheel`, `flank`, `rout`, `rally`, `reinforce`, `withdraw`, `encircle`, `breach`, `storm`, `undermine`, `bombard`, `sortie`, `surrender`, `pillage`, `take_captives`.
- **Vessels in every domain:** `manoeuvre`, `take_position`, `fire`, `ram`, `board`, `repel`, `ignite`, `extinguish`, `flood`, `pump`, `repair_underway`, `jettison`, `launch_craft`, `raise_shield`, `lose_shield`, `vent`, `lose_power`, `crash`, `explode`, `sink`, `strike_colours`, `escape`, `drift`.
- **Body and health:** `fall_ill`, `worsen`, `ease`, `recover`, `examine`, `treat`, `operate`, `set_bone`, `stitch`, `amputate`, `fit_prosthesis`, `go_into_labour`, `give_birth`, `lose_child`, `name_child`, `age`, `die`, `return_to_life`.
- **Making:** `gather`, `prepare`, `shape`, `assemble`, `temper`, `inscribe`, `enchant`, `test`, `flaw`, `finish_work`, `sign_work`, `repair`, `break`, `copy`, `forge` (a false copy), `lay_foundation`, `raise`, `complete`, `collapse`.
- **Exchange and work:** `offer`, `bargain`, `agree`, `pay`, `deliver`, `default`, `seize_goods`, `smuggle`, `levy`, `toll`, `lend`, `repay`, `give`, `return_gift`, `hire`, `work`, `strike_work`, `dismiss`, `buy_freedom`.
- **Speech, law and rule:** `accuse`, `investigate`, `find_evidence`, `testify`, `plead`, `judge`, `sentence`, `punish`, `pardon`, `appeal`, `decree`, `proclaim`, `vote`, `count_votes`, `appoint`, `swear`, `break_oath`, `negotiate`, `propose`, `counter`, `sign`, `refuse`, `threaten`, `insult`, `apologise`, `persuade`, `convert`, `teach`, `learn`, `write`, `read`, `translate`, `forge_record`, `reveal`, `conceal`, `deceive`, `discover`, `spread_word`.
- **Faith and powers:** `pray`, `offer`, `sacrifice`, `perform_rite`, `invoke`, `answer`, `deny`, `manifest`, `possess`, `exorcise`, `curse`, `bless`, `foresee`, `draw_power`, `use_power`, `backlash`, `bind`, `release`.
- **Movement and settling:** `depart`, `travel`, `rest`, `lose_way`, `meet_danger`, `cross`, `enter`, `leave`, `arrive`, `settle`, `found`, `abandon`, `return`.
- **Social and family life:** `meet`, `court`, `marry`, `separate`, `adopt`, `foster`, `inherit`, `succeed`, `crown`, `depose`, `betray`, `reconcile`, `befriend`, `quarrel`, `feud`, `avenge`, `mourn`, `celebrate`, `host`, `serve_food`, `compete`, `score`, `win`, `lose`, `perform`, `honour`, `shame`.
- **Nature and cosmos:** `begin`, `spread`, `peak`, `wane`, `end`, `erupt`, `quake`, `flood_land`, `burn_land`, `blow`, `freeze`, `dry`, `bloom`, `migrate`, `die_out`, `appear`, `collide`, `ignite`, `collapse_body`, `open`, `close`.
- **Minds and networks (W44, W45):** `connect`, `intrude`, `copy_mind`, `save_mind`, `restore_mind`, `transfer_mind`, `merge_minds`, `awaken`, `link_minds`, `unlink`.

A new mechanic adds the actions it needs to `StepAction` in the same change; there is no `other`.

**`StepOutcome`:** `success`, `partial`, `failure`, `missed`, `blocked`, `parried`, `dodged`, `glanced`, `absorbed`, `wounded`, `broken`, `severed`, `downed`, `killed`, `damaged`, `disabled`, `destroyed`, `captured`, `escaped`, `yielded`, `accepted`, `refused`, `delayed`, `interrupted`, `reversed`, `no_effect`.

#### F58.5 Changes (`state_changes`, `state_change_terms`)

Every value the engine, a god, a son, a mortal or Fate changes is recorded at flush by the capture of `db/ledger_capture.py`, widened from actor tool calls to every write:

| Column | Content |
|---|---|
| `id`, `epoch`, `moment` | when |
| `table_name`, `row_key`, `node_id` | which record and whose |
| `operation` | `LedgerOperation` (insert, update, delete) |
| `field` | the column (one row per changed column; an insert or delete keeps every column) |
| `before_number`, `after_number`, `before_text`, `after_text`, `before_node_id`, `after_node_id` | the values, typed |
| `actor_kind`, `actor_node_id` | `ActorKind` and the doer |
| `phase`, `incident_id`, `step_id` | where in the epoch and which happening caused it (F58.8) |

`state_change_terms`: `change_id`, `position`, `term` (a rules key, modifier source, factor name or catalogue key), `source_node_id`, `source_incident_id`, `op` (`ModifierOp`), `amount` (F58.7).

Every table except `BOOKKEEPING_TABLES` and the record tables themselves is captured. Tables the engine rebuilds wholesale are derived from recorded state; each rebuild records one change per row whose values differ from the last build, so no value is unrecorded. `ledger_changes` stays as the undo store of actor calls (bookkeeping); both are written by the same capture pass.

#### F58.6 Moments and places

- **Moment.** Every incident, step and change carries an in-world moment: `year`, `season`, `day` and `hour` (part of the day) from the calendar of its world (spec 13 F2.2, `catalog/worlds.py`). Worlds without days use their own units, and moments in realms with their own time ratio (44.10a) are converted, keeping one timeline (K.21).
- **Clocks.** Each kind names the process clock that dates its happenings inside the epoch: a march counts days on its route, a voyage its legs, a sickness its course, a building its months, a contest its rounds, a season its weeks. Moments come from the happening's own clock, never from the phase order of the write.
- **Order.** An incident's moment is never earlier than its cause's moment; a step's moment is never earlier than the step before it. `chronicle.year` is the incident moment's year; `EpochYearCursorRow` and the random roll of `chronicle_year` are retired.
- **Place.** Every incident stores its most precise place (room, structure, district, settlement, region, sea, sky, orbit, realm, network node), plus `origin` and `destination` for movement. A kind with `place: required` cannot be written without one.

#### F58.7 Terms: why every number is what it is

Every number a happening computes (a power, a price, a loss, a quality, a chance against its roll) is stored with its terms: the named factors that made it, each with its source and amount. The sources already exist as values: modifier stacks (`engine/primitives/modifiers.py`), the factor functions of battle (`modifier`, `BattleResult.factors`), duels (`swing`, `wound`), markets, harvests, health, standing and every rules key. A `terms` context collects them where they are computed, and the record stores them as `incident_terms` (same shape as `state_change_terms`) and on each change.

The record answers questions like "why did the prosperity of X fall from 60 to 40": a blockade took 12 (that incident), a levy took 8 (that incident). A numeric change with no terms is valid only when its kind marks it `direct` (a value set outright by a lever, a birth's starting value).

#### F58.8 Causes

- Every engine step that acts runs inside `recording(...)`, a widened `caused_by`: it opens or names the incident its writes belong to. Steps receive the incident that triggered them (the battle that wounded, the famine that moved people) and pass it on.
- Writes no happening explains (yearly ageing, prices settling, growth) belong to one incident per phase, world and epoch of kind `phase.<phase>`. Its changes are still recorded one by one with their terms, so nothing is unattributed.
- `ChronicleRepository.cause_of` is no longer used to guess a cause; it remains only to suggest links for old records (49.6).

#### F58.9 Witnesses, tellings and memory

- **Witnesses.** Participants with role `witness` are chosen by presence at the place and moment (`present_among`, `folk_among` in `engine/primitives/folk.py`), within the rules radius. Each has a `WitnessMode` (`saw`, `heard`, `took_part`, `was_told`) and a fidelity.
- **Rumours** (spec 13 F11) take their content from facts and steps and keep `incident_id`. Their distortions are typed (`RumourDistortion`: `doer_swapped`, `target_swapped`, `amount_changed`, `outcome_changed`, `cause_changed`, `place_changed`, `moment_changed`, `step_added`, `step_dropped`, `role_changed`), each naming the fact or step it changes.
- **Memories** (spec 13 F7) point at the incident and the step they remember.
- **Tellers.** Bards, chroniclers, the model and gods that spread an account are stored with role `teller`.

#### F58.10 Telling, tiers and names

- **Rendering.** The line is rendered from the kind's template, roles and facts (`render_incident`). The text written at the moment of the happening is kept as `chronicle.text`. Readers in another language re-render from the fields, and decision 71's localisation runs once per template family instead of once per line.
- **Tiers.** Every happening has three tiers:
  - the **line** (the feed);
  - the **account**: roles, facts, place, moment, cause, terms and witnesses;
  - the **steps**: every step and state change.

  Each surface reads the tier it needs; the book and the Codex render all three.
- **Folding becomes a view.** `fold_tick_lines` no longer hides, rewrites or cuts records. The feed may group lines of one kind in one epoch as a view ("N happenings of this kind", expandable to every one), and no entity link is capped. Records keep their own `ChronicleKind`; `engine_raw` is used only for raw engine notes. `folded_chronicle_ids_cap` is retired and `chronicle_fold_threshold` only shapes the feed view.
- **Names.** Happenings above the rules magnitude get a name from the model, from the world's languages and the typed fields (rule 2), as collections already do.

#### F58.11 The past at any moment

From the changes, any record, node, region, map layer or value can be reconstructed as it was at any earlier moment (`state_at(table, key, moment)`). Reconstructing walks the changes back from the present state; checkpoints every rules number of epochs keep this fast. It powers:

- the timeline scrubber on every drawer;
- the atlas at any moment: borders, settlements, routes, armies, fleets, networks;
- "then and now" lines in the book and the Codex;
- a god's revert lever (49.5).

#### F58.12 Retention

Everything is kept, for ever, in every world (K.42): every incident, fact, step, state, change, term, witness and telling. Nothing is sampled, compacted, folded away or cut, in storage, the API, the book or the Codex (memory: the book is never truncated). The model reaches any record by retrieval (paged context blocks, `recall_event`, search by typed fields), never through silent truncation; a context block that cannot hold everything says how many records it leaves for retrieval and how to ask for them. Volume is met by:

- bulk inserts at flush;
- integer keys and indexes on `node_id`, `incident_id`, `epoch` and `moment`;
- checkpoints for F58.11;
- streamed reads for the book and the Codex;
- paged screens.

The rows per epoch and the epoch time are measured as balance bands (49.8).

### 49.2 Every process records its account and its steps

Every family of Appendix 49.A belongs to one process group. The group gives the minimum facts and the steps of its kinds. Each kind lists its own, and the rule of F58.3 (every computed value is a fact) applies on top.

| # | Process group | Facts every kind of the group records | Steps |
|---|---|---|---|
| 1 | Single combat and violence to persons: duels, champions, trials by combat, god duels, vendettas, grudges, brawls, assaults, killings, executions, hunts of and by beasts and monsters, monster contracts, witch hunts, captives' fates | context (`DuelContext` or the kind), stakes, ground (terrain, weather, light), each side's arms and armour by model, skills used, number of exchanges, end (`DuelEnd`), who was spared and why (the mercy and honour readings) | every exchange as in spec 13 5.6 reference pass 2: initiative and distance (`close`), the chosen action with its target part, the defence (`block`, `parry`, `dodge`) and whether it met the attack, wrestling (`grapple`, `throw_down`, `choke`, `lock`, `bite`), each hit with instrument, part, damage type and outcome linked to its `injuries` row, falls and rising, disarming, the mount as a target, yielding, sparing, finishing |
| 2 | Battles, sieges and war: battles, phases, sieges and siege works, sorties, assaults, pursuits, occupations, purges, theatres, supply, spies and mole hunts, war declarations, war aims, war finance, peace | sides and armies, every stack with its kind, start, losses by fate (killed, wounded, captured, missing, deserted), tactics chosen and countered, ground and weather, scouting, plan, outcome class and gap, score, spoils, standard taken, commanders fallen | each phase's stack actions (`deploy`, `volley`, `charge`, `advance`, `flank`, `rout`, `rally`, `reinforce`, `withdraw`, `encircle`, `pursue`) with target stack, losses, morale and formation change; every named person's moments (a commander struck down, a hero's deed, a standard taken) as nested steps; siege works, breaches, mines, bombardments, sorties, storms and surrenders round by round |
| 3 | Vessels and fleets in every domain: sea, underwater, air, space, gas giant, planar, underground (49.3) | vessels, their frames, designs, crews by station, weapons by model, wind or position, shot or weapon kind each round, hits per section, crew losses, prize money, salvage | every round: `manoeuvre`, `take_position`, `fire` (weapon, target section, damage type, outcome), section states, chains (fire spreading, flooding, breach, venting, power loss, magazine or core explosion), `board` as a nested contest of group 1, `strike_colours`, `sink`, `escape` |
| 4 | Body, birth, health and death: births, stillbirths, injuries, afflictions, conditions, illness courses, epidemics, treatment, healing, ageing, deaths, returns from death, cohorts, stress, reproduction, lineages and breeding | the child's name and parents, place, attendants, complications, twins and births of more; the illness, strain, stage and symptoms; the healer, method, `TreatmentStep`s and their success; the cause of death with its chain, last place, last words when recorded by the model; age; inherited traits | labour and birth steps; illness stages (`fall_ill`, `worsen`, `ease`, `recover`); each treatment step; the last moments before death; each injury's healing stages (`InjuryState`) |
| 5 | Making, building and things: items, masterworks, forgeries, constructs, designs, enchantments, structures and their stages, megastructures, wonders, ruins, workshops, refining, chemistry, clocks, mining and extraction, heraldry | maker, workshop, materials by kind and amount, technique, tools, quality and its terms, flaws, time taken, cost, owner, signs and marks, every stage of a building with its workers and materials | gathering, preparing, shaping, assembling, tempering, inscribing, enchanting, testing, flaws, finishing and signing; laying foundations, raising, completing; damage, repair, breaking and collapse |
| 6 | Exchange, money and labour: markets, trades, routes, convoys, credit, banking, money, tolls, taxes, levies, loot, insurance, speculation, contraband, companies, slave markets, bondage, indenture, corvée, manumission, gifts and circuits, wages and strikes | goods by kind and quantity, price, currency and treasury units, parties, place and route, terms (rate, length, security), what was paid and what is owed, the ruling prices it moved | offering, bargaining, agreeing, paying, delivering, defaulting, seizing, smuggling, levying; for labour: hiring, working, striking, dismissing, buying freedom |
| 7 | Law, rule and offices: crimes, investigations, trials, verdicts, sentences, appeals, pardons, prisons, outlawry, registries, laws and decrees, councils and votes, elections, coalitions, crises, offices, titles, houses, successions, coups, loyalty, patronage, venality, schemes and secrets, estates and orders | the act and the law it broke, evidence, charges, court, judge, verdict, sentence and its execution; for decisions: the proposal, its clauses, votes by member and bloc, the rule of decision; for successions: the claimants, claims, rule of succession, outcome | the act; investigation steps (`investigate`, `find_evidence`); trial steps (`accuse`, `testify`, `plead`, `judge`, `sentence`); votes and their count; appointments; successions; schemes stage by stage |
| 8 | Diplomacy and plans: treaties and clauses, alliances, peace, tribute, marriages of state, envoys, great plans | parties, envoys, each offer and counteroffer, clauses with their typed terms, guarantees, what was given, breaches and penalties | `negotiate`, `propose`, `counter`, `threaten`, `persuade`, `agree`, `refuse`, `sign`; breaches and their answers |
| 9 | Faith, rites, powers and the uncanny: rites and their grammar, magic and its backlash, prayers and answers, miracles, sacraments, spirits and their offices, possession and exorcism, curses and blessings, divination and foresight, afterlife and returns, native faiths, the spread of faiths, taboos, prophecy, mage orders, dreams, horrors and outer beings | caster or officiant, rite or power, source, components and their amounts, the grammar (technique, form, range, target), essence or other cost, resistance and its terms, outcome, backlash, the god or spirit that answered | `pray`, `offer`, `sacrifice`, `perform_rite`, `invoke`, `draw_power`, `use_power`, `answer`, `deny`, `manifest`, `possess`, `exorcise`, `curse`, `bless`, `foresee`, `backlash`, `bind`, `release` |
| 10 | Movement and settling: journeys, voyages, pilgrimages, migrations, refugees, expeditions, exploration, routes found, settlements founded, nomad circuits, journeys beyond the world | travellers and their number, origin, destination, route and method, distance and days per leg, supplies, dangers met, losses, arrivals | `depart`, `travel` per leg, `rest`, `lose_way`, `meet_danger` (nesting the happening that followed), `cross`, `enter`, `leave`, `arrive`, `settle`, `found`, `abandon`, `return`; existing `expedition_logs` rows become steps |
| 11 | Social, family and cultural life: courtship, marriages, separations, adoptions, inheritance, households, gatherings, feasts, festivals, weddings, funerals, contests, games and sport, performances, art movements and markets, customs and revivals, age sets, intoxication, cooperatives, cuisine, pets, affairs, circles, friendships and quarrels, legacies, names, careers, standing, needs, aspirations, skills, ideas | who took part and in which role, the custom or rite followed, what was given (dowry, gifts, prizes), what was served (dish and drink kinds), the scores and rounds of contests, the work performed, the honour or shame that followed | `meet`, `court`, `marry`, `separate`, `adopt`, `inherit`, `host`, `serve_food`, `celebrate`, `mourn`, `compete`, `score`, `win`, `lose`, `perform`, `honour`, `shame`, `quarrel`, `reconcile`, `betray`, `avenge` |
| 12 | Knowledge, language and minds: discoveries, research, theories, inventions, schools and examinations, writing and printing, translation, records and accounts of the past, tongues, scripts, dialects, contact and death of languages, rumours, ciphers, memory, values, ethics, minds | who found or taught what, the subject and its level before and after, the path (study, experiment, contact, insight, revelation), the work written and its copies, the language and its changes, the account and what it contradicts | `investigate`, `discover`, `teach`, `learn`, `write`, `copy`, `read`, `translate`, `forge_record`, `reveal`, `conceal`, `spread_word` |
| 13 | Nature, land and seasons: ecology and its niches, creatures and beasts, domestication, extinction, flora, climate, seasons and long seasons, weather extremes, disasters and hazards, the succession of land, commons, soil and harvests, famine, relief and rebuilding, living stats | the area and places touched, intensity, duration, the species and their numbers before and after, harvests by crop and amount, people affected, deaths by settlement, structures damaged by section, losses in goods | `begin`, `spread`, `peak`, `wane`, `end`, and the kind's own (`erupt`, `quake`, `flood_land`, `burn_land`, `blow`, `freeze`, `dry`, `bloom`, `migrate`, `die_out`) with the settlement or region each step reached |
| 14 | Cosmos and the great scales: stars, galaxies, worlds, features, impacts, rifts, dimensions, phenomena, omens in the sky, terraforming, cosmic beings and their wounds, the world's age and balance, doom, the passing of ages, dark ages | the bodies, their measured values before and after (mass, light, orbit, age stage), energy, the path of an impact and its site, the regions and peoples affected | `appear`, `ignite`, `collide`, `collapse_body`, `open`, `close`, `spread`, `end` with the bodies or regions reached |
| 15 | Gods, sons and Fate: deeds of the Creator, sons and foreign gods, pantheon affairs, divine battles and duels, rulings, councils of gods, dominion, mythic offices and servitors, outer powers, Fate's verdicts | the god, the power or domain used, essence spent, targets, the request or prayer answered, the ruling and its terms, the verdict and its reason | each act with its target and outcome; divine battles round by round as in groups 1 and 2; rulings as group 7 |
| 16 | Peoples, societies and history: civilisations, peoples and ethnogenesis, societies and classes, factions and movements, institutions, asabiyya, regimes, collectives and crowds, storylets, story arcs and ages, accounts of history, records, excavations and sites, life cycles | the peoples and polities, counts before and after, the measures that crossed a threshold with their terms, the leaders, the choices made, the finds of a dig by room and layer | the stages of the process (`begin`, `spread`, `peak`, `wane`, `end`); crowd actions; storylet choices; excavation rooms and finds |

The incident families planned in 5.16 and every wave after W49 follow F58 from the start.

### 49.3 Engagements of vessels in every domain

Measurement: the round-by-round engagement (`military/vessels.py` `sea_fight`, `operations/sail.py` `engage`) runs only for `VehicleKind.SHIP`. Airships, spacecraft, submersibles and every other frame fight only as unit stacks. `VesselArmament` has four values (`rams`, `missiles`, `siege_engines`, `rites`), while the equipment models in `engine/equipment/models.py` already mount beam cannons, torpedoes, missile launchers, focus arrays, mine layers and harpoons. Weapon kinds choose the section they hit only for the four age-of-sail shot kinds.

1. **One engagement for every domain.** `engage` runs for every vessel domain (`VehicleDomain`), with position read from the domain: wind for sail, current underwater, altitude and lift in the sky, orbit and relative velocity in space, the domain's own medium elsewhere.
2. **Armament from mounted models.** `VesselArmament` is replaced by the weapon models actually mounted on the design (`MountKind`: `bow`, `stern`, `broadside`, `deck`, `turret`, `spinal`, `hardpoint`, `wing`, `crew_station`, `rider`, `ram`, `bay`, `ward_node`; `engine/equipment/models.py` `MOUNT_FAMILIES`), each read for its damage type, rate, range and the sections it can reach.
3. **Weapon to section.** A rules table maps each damage type and delivery to the sections it reaches and the chains it starts:
   - kinetic shot reaches hulls and decks;
   - fire reaches sails, envelopes and wooden decks;
   - energy reaches shields first (`ward`), then armour plating;
   - torpedoes and rams reach hulls below the waterline or the drive;
   - explosive delivery reaches crew stations;
   - powers and rites reach what their grammar targets.
4. **Chains for every section.** Each section has a typed chain when destroyed:
   - `magazine` and `power_core`: explosion;
   - `life_support` and `airlock`: venting and crew loss;
   - `drive` and `engine`: power loss and drift;
   - `envelope` and `rotor`: falling;
   - `hull` and `keel`: flooding or breach by domain;
   - `ward`: the shield falls.
5. **Boarding** is a nested group-1 contest between marines, with named officers.
6. **Every step recorded** (49.2 group 3); `StrikeResult.events` is replaced by steps.

Tables: `design_mounts` already hold the mounted models (`MountKind`); the rules namespace `engagement` holds the weapon-to-section table, chains and domain position rules. Levers: the existing vessel and design levers edit mounts; `engagement:force` lets a god start one.

### 49.4 Duels at full depth

Spec 13 5.6 reference pass 2 (planned) is the duel model. Whichever wave builds first builds it fully (0.7), and W49 requires its exchanges as steps: `military/duels.py` `bout` records each exchange's action, defence, part, instrument and outcome. Each hit goes through `engine/body/hits.py` with its part chosen in the exchange instead of after the bout, and the `injuries` row stores the step. `Bout.log` is removed.

### 49.5 Surfaces

- **API.**
  - `GET /incidents/{id}` serves the line, account, steps, states, changes, terms, witnesses, rumours and the cause chain both ways.
  - `GET /nodes/{id}/history` serves every incident, step and change of a node with role and kind filters, paged.
  - `GET /state-at` reconstructs past state (F58.11).
  - Search reads facts: every death by an instrument kind, every trade of a good, every rite of a source.
  - Every field served is read by a screen (`test_frontend_reads_every_field.py`).
- **Frontend.**
  - An **Event page** (drawer for an incident, built from the design system) shows the line, the account (roles with medallions, facts with labelled values and units, place, moment, cause and effects), a steps timeline (rounds, nested steps, states, linked injuries and sections), a changes table with before, after and terms, witnesses and the rumours told from it.
  - A **History** section in `ThingSections` (every kind of node: the Creator, sons, foreign gods, worlds, stars, every entity type) with filters and show-more paging.
  - A **timeline scrubber** on every drawer and on the atlas (F58.11).
  - Battle reports and engagement reports gain step timelines.
  - The causality graph (`features/entity/mechanics/CausalityGraph.tsx`) shows steps and changes.
  - The chronicle feed groups by view (F58.10) with every line reachable.
  - Loading, empty, error and disabled states, light and dark themes, phone width.
- **God control (rule 6).**
  - `IncidentForge` widens: `incident:create/edit/delete`, `incident_fact:create/edit/delete`, `incident_step:create/edit/delete`, `incident_witness:create/edit/delete`, so a god can write a happening into history or rewrite how it is told, with every field editable.
  - `incident:hold` locks a record against engine re-rendering.
  - `state_change:revert` writes the before value back as a new change by that god, so history stays true and the reversal is itself recorded.
  - `state_change:delete` removes a change record (erasing it from history is a god's power).
  - Every lever is registered in the action catalog, reached from the Event page and the History section, and proven in `test_every_lever.py` with real values.
- **Codex and book (rule 7).**
  - Every node's entry renders its History through `services/books/typed.py` (accounts and steps, in full).
  - The Records of the Cosmos appendix gains designed tables of incidents by age with their accounts, steps and changes.
  - Battle and engagement reports get their own layouts.
  - "Then and now" lines come from F58.11.
  - Nothing is truncated; the Codex and entries read every record, folded or not.
- **Agents.**
  - Mortal context carries the mortal's own recent steps, changes and the accounts they witnessed.
  - Son context carries the accounts of happenings in its domains.
  - Tools:
    - son `recall_event` reads an account;
    - son `retell_event` spreads a version (a rumour with typed distortions);
    - mortal `recount` tells what the mortal saw.

    Each tool has a case in `every_son_tool.py` or `every_mortal_tool.py`, and its fields are described in `test_catalogue.py`.
  - Every agent action writes its happening through F58.
- **Prompts.**
  - The chronicler's fact sheet carries the accounts and steps of the age's happenings as definite outcomes it may not contradict.
  - Templates are plain words from typed fields with no images and no tone. Every existing line is rewritten through its template, read in full (rule 2). The found tone-setting line in `engine/lore/rites.py` ("worked dark magic, and all who heard of it shuddered") is the first one rewritten.

### 49.6 Legacy

- Existing `incidents` keep their rows. Recorded fixups fill facts where the old key's catalogue schema can take them from linked entities, give participants their roles from `INCIDENT_ROLES` and the kind's role order, set moments from `chronicle.year`, and mark the record `tier = line` (account and steps unknown). Nothing is invented.
- Folded originals are restored to their kinds and made visible to every reader; folded summary lines become feed views.
- `ledger_changes` stays as the undo store; engine history starts with W49, and checkpoints (F58.11) are taken at the upgrade.
- The 19 history tables stay as typed views. Each write to them also writes its incident and changes, and their rows link `incident_id`.

### 49.7 Guards

| Guard | Fails when |
|---|---|
| `scripts/check_incident_kinds.py` | a key written by the code has no catalogue entry, an entry is never written, a write passes a pre-rendered f-string instead of facts, or a kind lacks roles, schema, template, place rule or clock |
| runtime validation in tests | a write misses a required role or fact, gives a fact the wrong type or unit, or uses a step action its kind does not declare |
| `scripts/check_dropped_records.py` | engine code collects narrative or step lists (`log`, `lines`, `events`, `steps`) that never reach the record API, or declares such a field that is never filled |
| `tests/engine/core/test_every_change_recorded.py` | on the rich cosmos of `test_god_control.py`, any write by any engine step leaves no `state_changes` row, or a row with no incident |
| `tests/engine/core/test_moments.py` | an incident is earlier than its cause, or a step earlier than the one before it |
| `tests/engine/core/test_terms.py` | a numeric change in an engine step has no terms and its kind is not `direct` |
| `tests/unit/test_every_incident_kind.py` | a kind cannot be rendered from sample facts, or a `StepAction`, `StepOutcome`, `StepState`, `InstrumentKind`, `StepLocus`, `FactUnit`, `WitnessMode` or `RumourDistortion` value is never produced and read |
| `scripts/check_wiring.py` | a record table is missing from the book or the Codex typed sections |
| `scripts/check_record_cuts.py` | any reader of records (book, Codex, API, search, prompts) slices, limits or filters out records by visibility or kind, except paged screens with show-more |

### 49.8 Rules, balance and performance

- Rules namespace `records`: witness radius, fidelity by mode, rumour distortion per hop, moment spreading per clock, naming magnitude, checkpoint interval.
- Balance bands (5.12a, `13-balance-bands.json`):
  - record rows per epoch per thousand mortals;
  - the share of numeric changes with terms (100%);
  - the share of incidents with a place where the kind requires one (100%);
  - the epoch time added by recording, held within a band measured before the wave and kept by batching.

### 49.9 Couplings, loops, stories and decisions

**Couplings.**

- C54 Records → rumours, memories, renown and the chronicler read facts and steps.
- C55 Changes → the past at any moment and god reverts.
- C56 Terms → every screen that explains a value.

**Loops.**

- L111 (R) a told deed → witnesses retell it → renown rises → more tellers (brake: fidelity falls per hop, rumour distortion).
- L112 (B) a distorted account spreads → a witness or record contradicts it → the account is corrected, or an `information.*` incident follows (44.14).

**Acceptance stories.**

- AS53 **The Arm and the Mace.** A duel records each exchange. An exchange breaks the loser's arm with a named mace (the injury row stores the instrument and step). The loser falls and is struck while rising. A witness's rumour swaps the weapon. The book shows the steps and the rumour's distortion.
- AS54 **Why the Town Went Hungry.** A blockade incident's terms appear in the town's prosperity change. The scrubber shows the town before and after. A god reverts the change, and the revert is itself recorded.
- AS55 **The Lost Shield.** Two spacecraft engage. A beam weapon takes down the target's shield, then breaches life support. Venting kills crew by station, and the ship drifts. Each step appears in the engagement report and the Codex.
- AS56 **Every Birth Told.** A birth records its place, attendants, complication and the child's name. A later epoch's folding view groups many births without hiding one of them from the Codex.

**Decisions.**

| Id | Question | Decision |
|---|---|---|
| K.42 | What is kept? | Everything, for ever, in every world (user decision 2026-11-14): every incident, fact, step, state, change, term, witness and telling; nothing is sampled, compacted, folded away or cut. |
| K.43 | Is the stored text or the fields the truth? | The fields. The text written at the moment is kept as the record of how it was first told; every reader can re-render from the fields. |
| K.44 | Can history be rewritten? | A god may revert a change (recorded as a new change), rewrite how a happening is told, or delete a record; the engine never edits a past record. |
| K.45 | Who witnesses by default? | Those present at the place and moment within the rules radius, plus participants; the Creator and sons see what their domains and attention reach. |

### 49.10 Execution order and compliance catalogue

**Execution order.**

1. The guards and `catalog/incident_kinds.py` come first, generated from the code so they list every key.
2. F58.1–F58.4: kinds, roles, facts and steps.
3. F58.5: change capture.
4. F58.6–F58.8: moments, places, terms and causes, with the recording scope through every engine step.
5. Each process group of 49.2 in Appendix 49.A order, with 49.3 engagements and 49.4 duels.
6. F58.9–F58.10: witnesses, rumours, rendering and folding as a view.
7. F58.11: the past at any moment.
8. Surfaces (49.5), fixups (49.6) and bands (49.8).
9. An audit by the guards against Appendix 49.A.

The wave is gated once.

| Section | Tables | Phases | God levers | Screens | Tools and context | Codex and book | Integrity | Backfill |
|---|---|---|---|---|---|---|---|---|
| F58.1–F58.3 kinds, roles, facts | `incident_facts`; `incidents.kind` from the catalogue | every phase that writes | `incident:*`, `incident_fact:*` | Event page | `recall_event`; accounts in context | account in entries and Records | kind exists; required roles and facts; types and units | facts and roles from links |
| F58.4 steps | `incident_steps`, `incident_step_states` | every process of 49.2 | `incident_step:*` | steps timeline | steps in mortal context | steps in entries and reports | order; parents exist; actions declared | none (start with W49) |
| F58.5 changes and terms | `state_changes`, `state_change_terms`, `incident_terms` | every write, at flush | `state_change:revert`, `state_change:delete` | changes table, value explanations | changes in mortal context | changes with terms | every write recorded; terms or `direct` | checkpoint at upgrade |
| F58.6 moments and places | moment columns on incidents, steps and changes | every phase, by clock | `incident:edit` | moments everywhere | moments in context | dates by world calendar | order by cause | moments from years |
| F58.8 causes | `incidents.cause_incident_id` through `recording` | every engine step | `incident:edit` | cause chain | chains in chronicler facts | cause lines | no write outside a scope | old guesses kept, marked |
| F58.9 witnesses and tellings | `incident_participants` (witness, teller), rumour distortions | rumours, memory | `incident_witness:*` | witnesses, rumours on the Event page | `retell_event`, `recount` | witnesses and tellings | witnesses present | none |
| F58.10 telling and folding | chronicle rendered; fold as view | epoch end | `incident:hold` | feed groups | chronicler fact sheet | every record shown | no reader cuts | folded lines restored |
| F58.11 past at any moment | checkpoints | checkpoint step | `state_change:revert` | timeline scrubber, atlas at a moment | — | then and now | reconstruction equals stored state at checkpoints | first checkpoint |
| 49.3 engagements | `design_mounts` read, rules `engagement` | seafaring and every domain | `engagement:force`, mount levers | engagement report | captain context | engagement reports | sections exist | `VesselArmament` mapped to models |
| 49.4 duels | `injuries` with `step_id` and instrument | duels, trials, champions | as spec 13 5.6 | duel timeline | duel accounts | duel reports | hits linked to steps | none |

## Part 10. W50 — Every facet of life at depth

### 50.0 Scope and the measurement behind it

The sweeps of spec 13 (1R.18) checked the Outline of Cultural Materials (OCM) at the level of its 76 major categories and found none missing. They noted that what remained was "granularity inside existing mechanics": thin sub-areas carried by one enum value or one flag. W50 closes that granularity by a closed audit on three fixed lists, so that a further question cannot find a thin facet that is not listed here.

**Lists and method (2026-11-14, by script).**

1. **OCM subcategories.** The OCM 2025 edition published by HRAF lists 736 codes. 689 describe world content; the 47 left out are orientation, bibliography, research method, archaeological analysis and source texts. Each of the 689 was matched against every table, column, enum value, engine and catalogue module, agent tool and god lever, and against spec 13 and this spec, with synonyms where the code names a facet differently ("fowling" is a catch ground, "proxemics" a norm). A second pass checked every doubtful match by its tables and modules.
2. **Registered mechanics.** The 572 mechanics of the interconnection registry (`engine/interconnect/catalog*.py`) were scored by their couplings to other subsystems.
3. **Node types.** The depth metric (`scripts/depth_metric.py`, spec 13 J.7) was re-run over every node type.

**Results.**

| List | Measure | Result |
|---|---|---|
| OCM subcategories (689) | own typed state and engine behaviour | 267 |
| | some typed state, behaviour partial | 241 |
| | a label only (one enum value or flag, no behaviour of its own) | 104 |
| | absent from code | 77 |
| Registered mechanics (572) | no coupling | 22 |
| | one coupling | 80 |
| Node types (51) | below a spec 13 depth target | 23 (17 of them on attributes read, 21 on mechanics acting) |
| UNESCO sub-disciplines (374) and motif ranges (259) | see 50.21 | closed in 50.22–50.29, Appendices 50.C and 50.D |
| | no attribute read and no mechanic acting | 7: `title`, `phenomenon`, `vehicle_type`, `unit_type`, `equipment_model`, `dish`, `building_type` |

The 181 label-only and absent subcategories fall into two groups:

- **Thirteen families of life** that no section of spec 13 or this spec carries at depth (50.1–50.13).
- **100 facets** that existing waves give kinds but not behaviour (50.16).

Appendix 50.A lists all 689 subcategories with their measured status and the section that closes each. Appendix 50.B lists the 102 weakly coupled mechanics.

Every family below follows the ground rules of 0.4 and 0.5: concepts by function, values from the seed and the world's canon, no imagery, no quotas, no gendered default, every era and every kind of world, and every kind of thing (rule 6). Each is wired end to end under its compliance row (50.18).

### 50.1 Population policy

**Current.** Fertility, migration and mortality follow from needs, health and events. No polity, faith or people acts on its own numbers.

**State.** `population_policies`:

- `holder_node_id` (polity, faith, people, company, son);
- `aim` (`PopulationAim`: `grow`, `hold`, `shrink`, `rebalance_age`, `rebalance_class`, `settle_land`, `empty_land`, `keep_kind`, `mix_kinds`, `none`);
- `instruments`, as child rows (`PopulationInstrument`): `birth_reward`, `birth_tax`, `union_law`, `child_limit`, `child_support`, `inheritance_rule`, `settlement_grant`, `migration_permit`, `migration_ban`, `expulsion`, `resettlement`, `recruitment_abroad`, `health_campaign`, `faith_teaching`, `made_birth` (W46 grown bodies and W44 made minds where they exist);
- `strength`, `enforcement`, `since_epoch`, `locked`.

**Behaviour.**

1. Each instrument shifts the typed driver it touches: fertility (`births`), migration pull and push (`migration`, `refugees`), mortality through care (`health`), the class and age mix (`demography`). Every shift is recorded with its terms (W49 F58.7).
2. Enforcement costs treasury and officials and meets resistance by values (F5) and faith teaching. Harsh instruments (`expulsion`, `child_limit`) raise grievance and flight.
3. Policies are chosen by holders whose aims read their numbers (labour shortage, land pressure, a ruling kind's share). Agents propose and repeal them.
4. Outcomes feed later policy: a shrinking people under `grow` raises the policy's strength; overshoot reverses it.

**Tools and control.**

- Mortal tool `set_population_policy`; son tool `move_population_policy`.
- God levers `population_policy:create/edit/delete/hold`, `population_instrument:*`.
- A "Numbers" section in polity, faith, people and company drawers.
- Context block `population_policy`.

**Codex and book.** Policies and their measured effects in holder entries; a table in Records.

**Integrity.** Instruments belong to their policy; enforcement stays within 0–100.

**Legacy.** None; policies start empty.

**Rules namespace.** `population_policy`.

### 50.2 Recorded and mass media

**Current.** Writing, printing, archives, the press as leverage, broadcast towers (W42) and signal chains exist. Images, sound and moving images cannot be recorded. No medium reaches a mass audience with its own reach, bias and trust.

**State.**

- **`record_media`.** Every recorded medium as an authored kind over `RecordForm`: `written`, `printed`, `image`, `sound`, `moving_image`, `signal`, `network` (W44), `living` (W46 memory organisms), `crafted` (carved, woven, knotted), `mental` (powers, W45). Each kind has fidelity, durability, copy cost, reach, the technique that opens it (F24) and the material it needs (F23).
- **`media_outlets`.** Owner, medium, audience (communities and reach 0–100), stance (typed value axes), trust (0–100), censorship exposure, revenue (sales, patronage, advertising, 50.3; state funding), staff.
- **`media_items`.** Outlet, kind (`MediaItemKind`: `news`, `opinion`, `record_of_event`, `entertainment`, `instruction`, `promotion`, `devotion`, `official`), subject incident or node, slant, accuracy against the incident's facts (W49), reach, epoch.

**Behaviour.**

1. Items are made from incidents (W49), deeds and holders' aims. Their accuracy is measured against the record's facts; distortions are typed as in F58.9.
2. Reach and trust move opinion (F7, F21), legitimacy, unrest and prices. Several outlets with opposed stances split opinion; a single trusted outlet aligns it.
3. Recorded images and sounds become evidence in trials (W27 `evidence`), historiography sources and art (`recorded` art mode, 48.7). They decay by durability and survive in archives.
4. Censorship, licensing and seizure of outlets follow law (47.3) and the surveillance state (44.13). Exposure of a false item lowers the outlet's trust.
5. Entertainment media form commercial entertainment: production, stars with renown, audiences, and illegal circuits where the law bans a form.

**Tools and control.**

- Mortal tools `found_outlet`, `publish_item`, `censor_outlet`; son tool `sway_outlet`.
- God levers `record_medium:*`, `media_outlet:create/edit/delete/hold`, `media_item:*`.
- An outlet drawer page; a "Media" section in settlements and polities.
- Context block `media`.

**Codex and book.** Outlets with their stance and trust; items linked to the incidents they tell, with their accuracy.

**Integrity.** An item's subject exists; reach is no greater than its outlet's.

**Legacy.**

- Broadcast towers become outlets of medium `signal`.
- Printing presses get a printed medium.
- Existing press leverage rows link to an outlet.

**Rules namespace.** `media`.

### 50.3 Commerce practice

**Builds on.** Spec 13 6.4 reference pass 6 plans exchange rates between currencies that follow purity, trust, money supply and trade balance, money changers who profit on spreads, and bills of exchange (W35, planned). Whichever wave runs first builds them fully (0.7); `exchange_rates` below is that table, not a second copy.

**Current.** Markets, prices, trade routes, credit, banking, insurance, speculation, brands and workshops exist. Goods move between producers and markets in one step, with no wholesale or retail tier, no shop, no promotion, no rent of things and no exchange between currencies.

**State.**

- **`shops`.** Structure or mobile, keeper, goods kinds carried, `ShopForm` (`stall`, `shop`, `house_trade`, `peddler`, `market_hall`, `warehouse_outlet`, `order_house`, `network_store`), margin, stock, credit to customers.
- **`supply_tiers`.** Per good kind and market: `producer`, `wholesale`, `retail`, each tier with holders and margin.
- **`promotions`.** Holder, good kind or brand, medium (50.2 or `crier`, `sign`, `display`, `patronage`, `gift`), reach, cost, claim accuracy.
- **`leases`.** Owner, lessee, thing (land, dwelling, structure, vessel, vehicle, item, made mind under 44.6, animal), rent, term, upkeep duty, default terms.
- **`exchange_rates`.** Between currency pairs, per market, with money changers as holders, a spread, and a convertibility source (48.5).

**Behaviour.**

1. Goods pass through the tiers that exist in a settlement's size and economy. Each tier adds its margin and can corner, hoard or fail (existing manipulation and cornering read tiers).
2. Promotion moves demand and brand loyalty by reach and claim accuracy. False claims found out cost trust and may break law (consumer protection is a typed law kind, 47.3).
3. Leases pay rent each epoch, transfer use and upkeep, and end, renew or default. Defaults go to courts (W27) and debt (credit).
4. Exchange rates follow each currency's trust, backing, debasement and trade balance. Changers profit from spreads, and rate shocks hit importers and debtors in foreign coin.
5. Retail access enters living standards (basket): a settlement without shops pays more for less.

**Tools and control.**

- Mortal tools `open_shop`, `promote`, `lease_out`, `change_money`.
- God levers `shop:*`, `supply_tier:*`, `promotion:*`, `lease:*`, `exchange_rate:*`.
- "Commerce" sections in settlement and market screens; leases in owner drawers.
- Context block `commerce`.

**Codex and book.** Shops and tiers in settlement entries; leases in owners' entries; exchange rates in the economy chapter.

**Integrity.** A lease's owner holds the thing; a rate pair is two existing currencies.

**Legacy.**

- Markets get a single retail tier.
- Workshops with sales become shops.
- Existing loans stay credit.

**Rules namespace.** `commerce`.

### 50.4 State enterprise and public works

**Current.** Polities tax, spend, build some structures and keep infrastructure levels. Roads, bridges, canals, rail lines and aqueducts are not built as programmes with labour, materials, schedule and upkeep, and no polity runs an enterprise or monopoly.

**State.**

- **`public_works`.** Polity or authority, kind (`WorksKind`: `road`, `bridge`, `canal`, `rail_line`, `aqueduct`, `dam`, `drainage`, `harbour_works`, `walls`, `granary_system`, `sewer`, `power_line`, `network_line`, `terraforming_stage`, `megastructure_stage`, `grown_works` (W46)). Also: route or region, stages, labour (paid, corvée, bound, made minds, constructs), materials, budget, schedule, progress, quality, upkeep and decay.
- **`state_enterprises`.** Polity, sector (good kind or service), form (`monopoly`, `royal_works`, `state_company`, `licence_holder`, `arsenal`, `mint`), management (official, company, made mind), output, revenue, corruption exposure.

**Behaviour.**

1. Works advance stage by stage with labour and materials. Shortfalls delay them; poor quality raises collapse and flood risk. Finished works change route speed and capacity (47.2), farm output (drainage, irrigation), health (sewers) and war (walls, roads).
2. Upkeep is owed each epoch; neglect decays works and recorded failures follow (W49).
3. Enterprises produce and sell under their form. Monopolies set prices and starve rivals; corruption skims revenue; privatisation hands them to companies (44.15).
4. Labour regimes carry their ethics and unrest: corvée and bound labour raise grievance, paid labour costs treasury.

**Tools and control.**

- Mortal tools `begin_works`, `fund_works`, `found_enterprise`; son tool `bless_works`.
- God levers `public_works:create/edit/delete/hold/advance`, `state_enterprise:*`.
- A "Works" panel per polity; works on the atlas; enterprises in polity drawers.
- Context block `works`.

**Codex and book.** Works with their stages, builders and results; enterprises and their output.

**Integrity.** Works lie on routes and regions of their polity or of a treaty partner.

**Legacy.**

- Infrastructure levels become finished works.
- Existing road and route upgrades become `road` works.

**Rules namespace.** `public_works`.

### 50.5 Daily life, time and personal care

**Current.** Needs, living standards, households and taverns exist. How beings spend their time, sleep, keep clean, groom, do housework and serve in others' houses, and what they do with free time, is not modelled. Norms of personal space and posture do not exist.

**State.**

- **`time_budgets`.** Per culture, class and life stage: shares of time for work, housework, care, rest, sleep, worship, learning, leisure, travel and service. Read per species biology, since some beings do not sleep or eat.
- **`care_customs`.** Per culture: washing (frequency, place: home, bath house, river, by rite), grooming (hair, body marking under 48.3, scent), cleanliness standards, waste handling (feeds sanitation).
- **`housework`.** Per household: duties (`HouseDuty`: `food`, `water`, `fuel`, `cleaning`, `textiles`, `childcare`, `eldercare`, `animals`, `repairs`), who does them (household members by role, servants, made minds, constructs), load.
- **`domestic_service`.** Servant, household, terms (wage, board, bound under 48.6), duties.
- **`leisure_pursuits`.** Per culture and person: pursuit kinds (`LeisureKind`: `conversation`, `games` (48.4), `sport`, `music`, `crafts`, `collecting`, `reading`, `excursion`, `tourism`, `drinking`, `worship_extra`, `rest`, `media` (50.2)), share and venue.
- **`space_norms`.** Per culture: personal distance, touch norms, seating and posture forms, read by etiquette and diplomacy.

**Behaviour.**

1. Time budgets bound labour supply, learning, worship attendance and leisure demand. Long work hours raise stress and unrest; leisure raises happiness and fills venues (taverns, arenas, baths, parks).
2. Care customs drive disease exposure (water and touch routes), sanitation load and social standing (norm breaches of cleanliness or grooming).
3. Housework load falls on the household roles each culture assigns (culture data, no default by sex). Servants and made minds lift it, freeing time for paid work or learning. Load rises with children, the old and the sick.
4. Tourism and excursions move wealth to destinations (wonders, sacred sites, baths, famous places) and spread news and disease.
5. Breaches of space and posture norms enter etiquette and diplomacy outcomes (insult, trust).

**Tools and control.**

- Mortal tools `hire_servant`, `take_leisure`, `set_house_duties`.
- God levers `time_budget:*`, `care_custom:*`, `housework:*`, `domestic_service:*`, `leisure_pursuit:*`, `space_norm:*`.
- "Daily life" sections in culture, household and mortal drawers.
- Context block `daily_life`.

**Codex and book.** A "Daily life" chapter per people; household duties in house entries.

**Integrity.** Shares sum to 100 per budget; a servant belongs to one household.

**Legacy.** Budgets derived from class and culture work and leisure readings; washing from existing purification and bath houses.

**Rules namespace.** `daily_life`.

### 50.6 Kin roles, households and kin groups

**Current.** Kin bonds, kinship systems (descent, residence, levirate and sororate), houses, households, adoption and fosterage exist. The duties between particular kin (grandparents, the siblings of parents, in-laws, cousins) and kin groups beyond lineage, clan, moiety and house do not.

**State.**

- **`kin_role_duties`.** Per culture: kin role (`KinRole`: `parent`, `child`, `sibling`, `grandparent`, `grandchild`, `parent_sibling_first_line`, `parent_sibling_second_line`, `sibling_child`, `cousin_parallel`, `cousin_cross`, `parent_in_law`, `child_in_law`, `sibling_in_law`, `co_spouse`, `chosen_kin`, `godparent`, `sworn_kin`). Each role has duties (`KinDuty`: `support`, `raise`, `teach`, `protect`, `avenge`, `marry_to`, `inherit_from`, `mourn`, `host`, `obey`, `joke_with`, `avoid`) with strengths.
- **`kin_groups`.** Authored kinds over `KinGroupForm`: `lineage`, `clan`, `phratry`, `moiety`, `kindred`, `ramage`, `house`, `localized_group`, `age_linked_group`. Each kind has membership rule (descent rule, residence, choice), corporate holdings (land, titles, shrines), head, council and exogamy.
- **`households`** gain `form` (48.6 household forms) and member roles.

**Behaviour.**

1. Kin duties drive help in need (food, coin, care), fostering, vengeance (feuds), marriage choices, inheritance shares and mourning. A breached duty records shame and memory.
2. Kin groups hold land and shrines corporately, choose heads, regulate marriage (exogamy) and act together in feuds, councils and migrations. Localized groups form villages and quarters.
3. Joking and avoidance relations shape interactions between particular kin, read by social interactions (F18).
4. Household form and size follow economy, inheritance and residence rules, and shape care load (50.5) and labour.

**Tools and control.**

- Mortal tools `call_on_kin`, `convene_kin_group`.
- God levers `kin_role_duty:*`, `kin_group:create/edit/delete/hold`, `kin_group_member:*`.
- A "Kin" section in mortal drawers; a kin group drawer page.
- Context block `kin`.

**Codex and book.** Kin duties in culture chapters; kin groups with members and holdings.

**Integrity.** Members follow the group's rule or are marked as adopted; one head per group.

**Legacy.** Clans, moieties and houses become kin groups; duties are derived from kinship systems.

**Rules namespace.** `kin`.

### 50.7 Folk knowledge systems

**Current.** Knowledge branches, techniques, theories (true or false) and folk beliefs exist. How a people classifies weather, matter, land, plants, animals, the body, the mind and society, and how accurate that knowledge is, is not modelled. Number systems are planned (spec 13 8.4 reference pass 5), but numerology and the reach of counting are not.

**State.**

- **`folk_knowledge`.** People, domain (`FolkDomain`: `weather`, `sky`, `matter`, `land`, `waters`, `plants`, `animals`, `body`, `illness`, `mind`, `society`, `number`, `time`), classification depth (0–100), accuracy against the world's typed truth (0–100), holders (elders, specialists, everyone), transmission (oral, written, apprenticeship, rite).
- **`folk_classes`.** Named classes a people uses in a domain, linked to the typed world kinds they group, with misclassifications recorded.
- Number system rows (spec 13) gain `numerology` (the readings a culture gives numbers).

**Behaviour.**

1. Accuracy in a domain sets success in the work it serves: plants for gathering and herbal treatment, animals for hunting and herding, weather for farming and sailing, body and illness for care, land and waters for travel and siting, mind and society for persuasion and rule.
2. Folk knowledge competes with formal theories (`theories`). Contact, schooling and failure move accuracy up or down, and a people can lose knowledge with its holders.
3. Misclassifications have typed consequences (a poisonous plant classed as food, a sickness classed as a curse) and surface as incidents.
4. Numerology enters omen reading, naming and calendar rites.

**Tools and control.**

- Mortal tools `teach_lore`, `test_lore`.
- God levers `folk_knowledge:*`, `folk_class:*`.
- A "What they know" section in people drawers.
- Context block `folk_knowledge`.

**Codex and book.** Per people, each domain with its classes, depth and accuracy.

**Integrity.** Classes point at existing world kinds.

**Legacy.** Derived from knowledge levels, techniques and folk beliefs.

**Rules namespace.** `folk_knowledge`.

### 50.8 Intimacy, sexual norms and the course of reproduction

**Current.** Attraction, affairs, marriages, reproductive systems per biology, births with twins and stillbirths, and act kinds (adultery, incest, infanticide) exist. Norms about relations before, outside and within unions, between beings of any sexes, about restraint and vows, and the course of pregnancy, birth and the time after it are labels or absent.

All of this is narrated plainly and behind closed doors (G9). No norm is a default; each culture authors its own; no world is required to have any of them.

**State.**

- **`intimacy_norms`.** Per culture: for each `RelationContext` (`before_union`, `within_union`, `outside_union`, `between_any_sexes` (read on the biology's sexes), `with_kin` (the scope of forbidden kin from the kin roles of 50.6), `with_made_minds` (W44), `with_other_kinds` (other peoples or species)): a stance (`forbidden`, `discouraged`, `tolerated`, `accepted`, `honoured`), sanctions and who enforces them (kin, faith, law).
- **`restraint_customs`.** Celibacy and restraint vows by role (clergy, ascetics, warriors before battle), seasons and rites.
- **`reproductive_course`.** Per biology: cycle (with its customs: seclusion, purity rules, none), gestation or incubation length, complications by kind (`BirthComplication`: `position`, `bleeding`, `fever`, `early`, `late`, `multiple`, `none`), care during and after (`PostnatalCustom`: `rest_period`, `seclusion`, `kin_care`, `specialist_care`, `rite`, `none`), attendants, birth places.
- **`legitimacy_rules`.** Per culture: a child's standing by the parents' union, and the paths to change it (recognition, adoption, payment, rite).

**Behaviour.**

1. Norms set the outcome of relations the engine already produces (attraction, affairs, unions): scandal, sanction, feud, divorce, standing, secrets (F20), and the political use of them (leverage).
2. Changes of norm follow values, faith, contact and movements (W20). Persecution under a `forbidden` stance raises flight and secrecy.
3. Pregnancy runs its course with typed complications whose chances read medicine, attendants and the bearer's health. Postnatal customs set the bearer's recovery and the child's early care (50.9). Every step is recorded (W49 group 4).
4. Legitimacy rules decide inheritance, office eligibility and claims (succession, houses).

**Tools and control.**

- Mortal tools `seek_recognition`, `take_restraint_vow`.
- God levers `intimacy_norm:*`, `restraint_custom:*`, `reproductive_course:*`, `legitimacy_rule:*`.
- A "Unions and birth" section in culture drawers.
- Context block `unions_and_birth`, plain and closed-door.

**Codex and book.** Norms and courses described plainly per culture, never explicit.

**Integrity.** Contexts read only sexes the biology declares.

**Legacy.**

- Existing act kinds map to norms with a `forbidden` stance only where the culture's laws already ban them.
- Everything else is `tolerated`, until genesis or the model authors the norm.

**Rules namespace.** `unions_and_birth`.

### 50.9 Infancy, childhood and socialization

**Current.** Children are born, fostered, apprenticed and schooled. Upbringing is one passion source, and childhood stages are planned in spec 13 (3.1 reference pass). How infants are fed and cared for, what standing children have, and how each culture shapes them into adults are labels or absent.

**State.**

- **`infant_care`.** Per culture and biology: feeding (`InfantFeeding`: `by_birth_parent`, `by_other_nurse`, `animal_milk`, `prepared_food`, `made_food`, `none_needed`), weaning age, carrying and sleeping arrangements, carers (kin roles, specialists, community, made minds).
- **`child_standing`.** Per culture: the age of naming, of personhood, of work, of responsibility before law, of marriage; child labour share; protections.
- **`socialization`.** Per culture: technique weights (`SocializationTechnique`: `example`, `instruction`, `praise`, `shame`, `punishment`, `ritual_ordeal`, `storytelling`, `play`, `apprenticeship`, `schooling`, `peer_group`, `age_set`). It also holds aims weighted over value axes (F5) and skills: independence, obedience, aggression and restraint, cooperation, piety, craft.
- **`pedagogy`.** Per school or tradition: theory (`PedagogyTheory`: `rote`, `dialectic`, `apprenticeship`, `discovery`, `ritual_transmission`, `examination`, `network_learning` (W44), `mind_transfer` (W44)), its effect on learning speed and on depth against breadth.

**Behaviour.**

1. Infant care sets infant survival, weaning illness exposure and the birth parent's return to work (50.5).
2. Socialization shapes each child's starting values, traits and skills through the culture's techniques and aims, varied by household and class. Harsh techniques raise later stress and conformity; play and peer groups raise cooperation.
3. Child standing decides child labour (feeds production, lowers schooling), early marriage, and legal treatment (W27).
4. Pedagogy sets how fast knowledge and skills pass between generations, and which kind of scholar a tradition produces.

**Tools and control.**

- Mortal tools `raise_child`, `found_school_method`.
- God levers `infant_care:*`, `child_standing:*`, `socialization:*`, `pedagogy:*`.
- "Childhood" sections in culture and household drawers.
- Context block `childhood`.

**Codex and book.** A childhood chapter per people.

**Integrity.** Ages are increasing in order; technique weights sum to 100.

**Legacy.** Derived from culture values, education levels and existing fosterage.

**Rules namespace.** `childhood`.

### 50.10 Philanthropy and endowments

**Current.** Poor relief, alms, welfare houses and patrons exist. Endowments that fund an institution for ever, and private foundations with their own aims and capture, do not.

**State.**

- **`endowments`.** Founder, beneficiary (a structure, an office, a school, a temple, a route, a people, a cause), capital (land, coin, shares, rents), income, trustees, purpose (`EndowmentPurpose`: `relief`, `learning`, `worship`, `health`, `works`, `art`, `kin`, `memory`, `research`), terms (perpetual, for a term, conditional), the law that shelters it.

**Behaviour.**

1. Income funds the beneficiary each epoch, raising its output and the founder's renown and memory (remembrance).
2. Trustees may serve the purpose, skim, or be captured by a faction or the state. Laws can confiscate endowments or shelter them from tax.
3. Endowed institutions outlive dynasties and keep knowledge and worship through collapses (dark ages).

**Tools and control.**

- Mortal tools `endow`, `audit_endowment`.
- God levers `endowment:create/edit/delete/hold`.
- Endowments in founder and beneficiary drawers.
- Context block `endowments`.

**Codex and book.** Endowments with founders, income and history.

**Integrity.** The beneficiary exists; capital is held by the endowment.

**Legacy.** Welfare houses with patrons gain an endowment where the patron funds them.

**Rules namespace.** `endowments`.

### 50.11 Youth, adolescence and delinquency

**Current.** Life stages, age sets and coming of age exist. The standing of youths, their groups and activities, and youth crime are not modelled.

**State.**

- **`youth_standing`.** Per culture: the years of youth, freedoms and duties, places (`youth_house`, `household`, `school`, `service`, `apprenticeship`, `wandering`).
- **`youth_groups`.** Settlement, members, purpose (`YouthPurpose`: `sport`, `service`, `courtship`, `defence`, `faith`, `mischief`, `crime`, `politics`), leader, standing.

**Behaviour.**

1. Youth groups train skills and loyalties, keep watch and festivals, court, compete and, where opportunity, poverty and weak social control meet, turn to delinquency. Crime and gangs (W27) recruit from them.
2. Movements and revolts draw on youth groups; rulers co-opt them by service and schools.
3. Coming of age moves members into adult standing and dissolves the group's hold.

**Tools and control.**

- Mortal tools `lead_youth`, `reform_youth`.
- God levers `youth_standing:*`, `youth_group:*`.
- A "Youth" section in settlement drawers.
- Context block `youth`.

**Codex and book.** Youth customs per people; groups in settlement entries.

**Integrity.** Members are within youth years.

**Legacy.** Age set rows for youths become youth groups.

**Rules namespace.** `youth`.

### 50.12 Death work and the handling of the dead

**Current.** Deaths, funerals, funeral customs, mourning, ancestor cults and afterlives exist. The people who handle the dead and the forms beyond the listed customs are labels.

**State.**

- **`death_work`.** Per culture: roles (`DeathRole`: `washer`, `preparer`, `keeper_of_remains`, `officiant`, `mourner`, `record_keeper`, `carrier`), their standing (honoured, avoided, purity rank under F41), fees and guild.
- Funeral customs (47.3, 48.7) gain forms by what is done with remains (`RemainsTreatment`: `burial`, `cremation`, `exposure`, `preservation`, `water`, `consumption` (only as a culture's own custom), `storage`, `return_to_maker` (made bodies), `release` (spirits), `none_needed`), with costs, places and health effects.

**Behaviour.**

1. Death work is a profession (48.6) whose standing shapes recruitment and marriage. Its absence in a plague leaves remains untended, raising disease and unrest.
2. Remains treatment sets the land and structures used (graves, towers, ossuaries, pyres), the health exposure, the relic supply (faith) and what necromancy and spirits can reach.
3. Readjustment after a death (widowhood, inheritance, household reform) reads kin duties (50.6) and is recorded step by step (W49).

**Tools and control.**

- God levers `death_work:*`, and remains treatment through the funeral custom levers.
- A "The dead" section in culture drawers.
- Context block `the_dead`.

**Codex and book.** The treatment of the dead per people, plainly.

**Integrity.** Each death refers to a treatment its culture allows, or is recorded as an exception.

**Legacy.** Funeral customs map to treatments.

**Rules namespace.** `death_work`.

### 50.13 Humour, conversation and public speech

**Current.** Jokes and gossip are interaction kinds, sermons a collective trigger, and humour a facet. Humour as a cultural style, satire as a political force, and oratory and lectures as venues of persuasion are not modelled.

**State.**

- **`humour_styles`.** Per culture: forms (`HumourForm`: `wordplay`, `teasing`, `satire`, `absurd`, `bodily`, `irony`, `storytelling`, `ritual_clowning`), targets allowed and forbidden (rulers, gods, kin roles from 50.6, strangers), and the offence threshold.
- **`speeches`.** Speaker, venue (`SpeechVenue`: `assembly`, `court`, `temple`, `square`, `school`, `camp`, `outlet` (50.2)), aim (`persuade`, `teach`, `mock`, `mourn`, `rally`, `defend`, `accuse`), skill, audience reach, effect.

**Behaviour.**

1. Humour eases tension in interactions within the allowed targets and offends outside them. Satire of rulers lowers legitimacy where tolerated and brings punishment where not, and spreads by media.
2. Speeches move assemblies (votes), courts (verdicts), crowds (riots) and congregations by skill, aim and the audience's values. Great speeches become recorded works and legends.
3. Conversation norms (turn-taking, silence, directness) enter diplomacy and trust.

**Tools and control.**

- Mortal tools `give_speech`, `satirise`.
- God levers `humour_style:*`, `speech:*`.
- Speeches in incident pages; humour in culture drawers.
- Context block `speech`.

**Codex and book.** Humour per people; notable speeches with their effects.

**Integrity.** A speech's venue exists in its settlement or polity.

**Legacy.** Derived from facets and interaction histories.

**Rules namespace.** `speech`.

### 50.14 Every mechanic coupled

The 102 registered mechanics with at most one coupling (Appendix 50.B) act on their own subsystem only, so their outcomes do not reach the rest of the world. Each gains couplings to at least two other subsystems that its outcome plausibly drives, chosen from its own fields. Two examples:

- `mortal_births` reaches household load (50.5), kin duties (50.6) and population policy (50.1).
- `planetary_climate` reaches harvests, migration and faith.

Appendix 50.B names, for every one of the 102, the subsystems it gains and the effect it carries to each. The couplings are registered in the interconnection registry with their edge kinds and rule keys, and each has an acceptance check.

**Guard.** `scripts/check_mechanic_couplings.py` fails when a registered mechanic has fewer than two couplings to other subsystems, unless its entry states why it can drive nothing else (bookkeeping mechanics only).

### 50.15 Every node type at its depth target

The depth metric's shortfalls are closed section by section. The seven types read by nothing gain targets and readers.

| Node type | Short on | Closed by |
|---|---|---|
| `structure` | mechanics acting (42 / 70) | W47 47.1 own effects for every structure kind |
| `language` | attributes read, mechanics (62 / 110, 64 / 90) | 50.2 media and 50.13 speech read languages; spec 13 8.x planned items |
| `celestial` | mechanics (3 / 12) | W47 47.6.1 typed sky events; 50.7 folk knowledge of the sky |
| `vessel` | attributes, mechanics (20 / 80, 13 / 65) | W49 49.3 engagements in every domain; 50.3 leases; 50.4 harbour works |
| `outer_being` | mechanics (16 / 20) | W45 45.15 patrons; W47 47.5 outer being plans |
| `natural_law` | attributes, mechanics (6 / 10, 4 / 30) | W47 natural laws (fortune law K.37 and the law grammar of 47.5) |
| `title` | everything (0 / 25) | W48 48.6 title tiers as typed nodes read by succession, legitimacy, courts and kin groups (50.6) |
| `beast` | attributes, mechanics (79 / 150, 64 / 90) | W48 48.5 species roles; 50.7 folk knowledge of animals |
| `theory` | attributes (8 / 15) | 50.7 folk knowledge against theories |
| `art_form` | attributes, mechanics (8 / 20, 1 / 20) | W48 48.7 art modes; 50.2 recorded art; 50.13 |
| `phenomenon` | everything (0 / 20) | W48 48.8 typed phenomenon model read by regions, travel and faith |
| `cosmic_being`, `vehicle_type`, `unit_type`, `equipment_model`, `dish`, `building_type` | no target, nothing read | targets set here (attributes 15, mechanics 15, subsystem pairs 15 each); readers through W48 F57 authored kinds and their typed properties |
| `son` | attributes, mechanics (246 / 350, 117 / 320) | W47 47.5 god layer |
| `creator` | attributes, mechanics (25 / 35, 13 / 40) | W47 47.5 |
| `foreign_god` | attributes, mechanics (104 / 200, 33 / 140) | W47 47.5 |
| `world` | attributes, mechanics (139 / 195, 61 / 135) | W47 47.2 and 47.6; 50.4 terraforming works |
| `star` | attributes, mechanics (17 / 35, 3 / 30) | W47 47.6.1; 50.7 |
| `route` | attributes, mechanics (26 / 45, 3 / 30) | 50.3 tiers on routes; 50.4 works; W49 49.3 |

**Guard.** After W50, `scripts/depth_metric.py check` fails when any node type is below its target.

### 50.16 Facets with kinds but no behaviour

The 100 subcategories that existing waves give kinds but not behaviour are marked **50.16** in Appendix 50.A. Each one gets the typed state and the engine behaviour named below. Its kind table (W47, W48) carries the typed properties, and the engine step named in the last column reads them, so the facet changes something in the world. Every facet also follows 50.17a (eras, worlds, kinds of thing, incidents, rules, book and Codex).

| OCM | Facet | Typed state | Engine behaviour that reads it |
|---|---|---|---|
| 172 | Prehistory | spec 13 F48 prehistory digest per world (eras, peoples, finds), built by W39 | genesis seeds the digest; excavations (W13 sites) reveal its layers; historiography quotes it; claims and legitimacy may rest on it |
| 228 | Marine industries | production methods of family `marine` (48.5) over sea species products (pearls, shell, oils, salt from water, kelp) with catch grounds | coastal grounds yield by stock and season; overharvest depletes stocks (ecology); products enter trade and crafts; divers and crews carry exposures (47.10) |
| 237 | Animal by-products | species products (48.5) by part (hide, horn, bone, fat, gut, feather, chitin, silk, venom) with yield per kill or harvest | butchering and gathering yield them; leather, glue, tallow and tools methods consume them; sacred species forbid their use where faith says so |
| 242 | Agricultural science | knowledge branch `agronomy` with sub-techniques (rotation, selection, grafting, manuring, irrigation design) and research paths (8.4) | each technique raises yield or resilience on the crops it names; selection feeds designed lines (W46 46.2); failed trials record losses |
| 247 | Floriculture | crop kinds of category `ornamental` (48.1) with gardens as a land use | gardens supply rites, dyes, scent kinds (48.3) and gifts; prestige gardens raise elite standing; they compete with food land |
| 253 | Meat packing | production method `slaughter_and_dress` and `cure_meat` with yield, waste and spoilage | herds and hunts feed it; output enters diets and trade; waste raises disease near settlements without refuse handling (50.5) |
| 257 | Confectionery | dish and good kinds of category `sweetener` products (48.1, 48.2) with methods (boiling, candying, baking) | sweet goods raise feast quality and gift value; sugar crops feed it; demand rises with wealth |
| 266 | Cannibalism | remains treatment `consumption` (50.12) and act kinds, only as a culture's own custom or a species' diet | read by funeral and war customs where the culture authors them; others judge it by their norms (opinion, war cause); disease routes through it where biology says |
| 272 | Non-alcoholic beverages | drink kinds (48.2) with `alcohol_strength` 0, stimulant and water-safety properties | they meet thirst and the drink need; boiled or brewed drinks lower waterborne disease; stimulants raise work and alter sleep (50.5) |
| 274 | Beverage industries | production methods for drink kinds (brewing, fermenting, distilling, infusing) with workshops | output feeds taverns, rites and trade; taxes and bans apply by law; spoilage and quality follow method and water |
| 277 | Smoking and stimulant leaves | substance kinds (48.4) with dependence, health effects and ritual uses; crop kinds that yield them | use spreads by culture and trade; dependence and health effects follow the intoxication model; bans and monopolies (50.4) tax it |
| 282 | Leather industry | methods `tan` (bark, mineral, smoke, oil) with inputs and pollution | hides become leather for garments, arms and gear; tanneries pollute water (industry pollution) and are placed by law outside walls |
| 283 | Cordage | method `twist_cord` from fibre products; good kind `cord` | ships, construction, nets, snares and siege engines need cord; shortages slow them |
| 284 | Knots and lashings | technique `knotwork` (F24) and the knot records already in writing systems | raises rigging and construction quality; knot records serve as writing where the culture uses them |
| 287 | Felted fabrics | method `felt` from wool or hair; garment and shelter kinds that use felt | felt tents and garments serve nomads and cold lands; felt quality enters warmth (weather exposure) |
| 289 | Paper industry | methods for writing media (paper, parchment, bark, leaf, tablet, film, data) with inputs | media supply sets book output, archives, bureaucracy cost and printing; shortages slow records |
| 290 | Clothing | garment kinds (48.3) worn per person and class with warmth, protection and status | dress norms read garments for standing and etiquette; warmth enters weather exposure; uniforms mark offices and armies |
| 291 | Normal garb | each culture's everyday garment set by class, life stage and climate | read by needs (warmth), basket cost and standing; changes with fashion cycles (W26) |
| 294 | Clothing manufacture | method `make_garment` (household, tailor, workshop, factory) with labour and quality | garment supply and price; household textile duty (50.5); tailors as a profession |
| 301 | Ornament | ornament kinds (48.3 adornment) with material, value and meaning | worn for status, gifts and dowry; buried with the dead; stolen and looted |
| 306 | Jewellery manufacture | method `make_jewellery` with precious materials and skill | output enters wealth storage, gifts, dowries and trade; masterworks become items with history |
| 322 | Woodworking | profession and method family `wood` with tools (48.4) | furniture, carts, ships, houses and arms need it; skill sets quality |
| 323 | Ceramics | methods `pottery`, `kiln_fire`, `glaze` with kilns | storage vessels cut spoilage; tiles and bricks build; pottery styles mark cultures in excavations |
| 324 | Stone tools | method family `knap` and `grind` with stone materials | tools and arms where metal is unknown or scarce; quality from material and skill |
| 333 | Masonry | profession and method `masonry` | stone structures need masons; skill sets durability and collapse risk |
| 334 | Tall frame building | building form `frame_tower` (high rise) needing structural materials and techniques | dense housing and offices; collapse risk by material and quake; lifts (355) required above a height |
| 335 | Carpentry | profession and method `carpentry` | timber structures, roofs, scaffolds and ships need it |
| 337 | Electrical installation | trade `wiring` and structure component `power_feed` | structures run electric functions only when fed (47.2 energy); faults raise fire mishaps |
| 338 | Other building trades | trades `glazing`, `plaster`, `roofing`, `paving`, `plumbing` as professions | each finishes structures and raises their condition; missing trades leave structures below full function |
| 354 | Heating and lighting equipment | furnishing kinds of category `heating`, `lighting` (48.4) with fuel and output | warmth and light enter needs, work hours (50.5) and fire risk |
| 355 | Lifts and building machines | structure component `lift` with power source | tall structures need them; failures are mishaps |
| 365 | Public utilities | public works kinds `aqueduct`, `sewer`, `power_line`, `network_line` (50.4) | supply water, sanitation, power and networks to districts; outages follow neglect |
| 367 | Parks | district land use `park` | leisure (50.5), health, elite prestige and protest gatherings |
| 368 | Other facilities | structure kinds outside the named classes read by their own effects (47.1) | each facility acts by its effects table |
| 377 | Electric power | energy kind `electric` (47.2) with generation, grid and storage | powers structures, machines, media (50.2) and networks |
| 378 | Fission and fusion power | energy kinds `fission`, `fusion` (47.2) with fuel, waste and accident hazards | large output; waste and accidents scar land and raise disease and doom where the world says |
| 383 | Rubber and elastic materials | material kinds with elasticity property (F23) from plants or synthesis | seals, wheels and protective gear read elasticity |
| 384 | Synthetic materials | materials of origin `synthesis` (F23) by technique | substitute natural materials; pollution by method |
| 386 | Paints and dyes | dye products and colour terms (48.3) with sources and fastness | colours carry status and meaning; dye works pollute; rare colours are luxuries |
| 387 | Fertilizers | goods that add soil nutrients (spec 13 soil nutrients) by kind | raise yields on depleted soils; runoff pollutes water |
| 388 | Soap and cleaners | goods of category `cleaner` with method | read by care customs (50.5) and disease exposure |
| 389 | Explosives | goods with blast property and method; storage hazard | mining, siege, war and accidents read them |
| 390 | Capital goods | production methods that make tools and machines (48.4, 48.5) | output raises other methods' productivity; shortages bottleneck chains |
| 391 | Hardware | goods of category `hardware` (nails, fittings, locks) with methods | construction and crafts consume them |
| 392 | Machine industries | methods that make machines by family technology level (47.2) | supply of machines to industry and households |
| 393 | Electrical supplies | goods of category `electrical` (wire, cells, components) | electric structures and devices consume them |
| 394 | Making heating and lighting equipment | methods for furnishing kinds of 354 | supply and price of heating and lighting |
| 395 | Optics | goods and techniques `lens`, `optic_instrument` | navigation, astronomy, medicine (sight aids) and war read them |
| 397 | Rail equipment | vehicle families of carrier `rail` (47.2) with methods | rail transport capacity |
| 399 | Aircraft industry | vehicle families of domain `air` with shipyards of kind airfield | air transport and air war capacity |
| 400 | Machines | tool kinds of category `machine` (48.4) with power, output and wear | raise production where a method uses them; wear and repair |
| 403 | Electrical machines | machines with energy kind electric | as 400, gated by electric supply |
| 404 | Household machines | furnishing and tool kinds used in housework (50.5) | cut housework load and change household time budgets |
| 406 | Weight-moving machines | tool kinds `crane`, `hoist`, `lift` | construction speed and port handling |
| 408 | Computing | structures `data_centre`, `ai_core` (W42) and tool kinds of category `computer` | networks (F51), made minds (F50), research speed, record keeping |
| 414 | Other hardware | goods outside named classes read by their kind properties (48.1) | as their properties say |
| 416 | Appliances | furnishing kinds of category `appliance` | as 404 |
| 417 | Apparatus | tool kinds of category `instrument` for science and navigation | research speed, navigation accuracy, medicine |
| 462 | Division of labour | culture data assigning duties and professions to roles (sexes where the biology has them, age, class, kin), default `any` | read by housework (50.5), professions and armies; changes with values and movements |
| 496 | Railways | carrier `rail` routes and terminals (50.4 works) | land transport speed and capacity, troop movement, settlement growth along lines |
| 502 | Navigation | navigation accuracy from instruments (417), folk knowledge of sky and waters (50.7) and skill | voyage losses, speed and discovery of routes |
| 506 | Aircraft | vehicle families of domain `air` | air transport and war |
| 507 | Aviation | carrier `air` with crews and routes | travel time, mail, trade of light goods, war |
| 508 | Airfields | structure kind `airfield` (W42) with capacity | air routes need terminals |
| 533 | Music | music traditions (48.4) with forms, instruments and venues | gatherings, rites, mood, renown of musicians, transmission by teaching |
| 534 | Musical instruments | instrument kinds (48.4) with makers | traditions need their instruments; instruments are trade goods and heirlooms |
| 541 | Spectacles | gatherings of kind `spectacle` (circus, games, processions) with crowds | draw crowds and wealth, raise ruler favour, risk crowd mishaps and riots |
| 562 | Status by sex | culture data of role eligibility (`GenderRule`, `any` by default) | read by offices, inheritance, professions and armies only where the culture sets it |
| 583 | Union payments | marriage payment kinds (48.6) with amounts | move wealth between households; debts and feuds when unpaid |
| 585 | Nuptials | union rites (traditions of stage `union`) with guests and cost | gatherings, alliances, feasts, standing |
| 589 | Celibacy | restraint customs (50.8) and vows | clergy and ascetic roles; inheritance passes elsewhere; vows broken record scandal |
| 595 | Plural unions | union forms (47.3.4) allowing more than one spouse | household form, inheritance shares, co-spouse duties (50.6), status |
| 614 | Clans | kin groups of form `clan` (50.6) | corporate land, exogamy, feuds, councils |
| 616 | Moieties | kin groups of form `moiety` | marriage rules and ritual halves |
| 642 | Forms of government | government kinds over typed rule axes (47.3: who rules, how chosen, limits) | succession, councils, legitimacy, decisions |
| 683 | Offences against persons | crime kinds (W27) `assault`, `abduction`, `false_imprisonment` with sanctions | trials, feuds, standing |
| 684 | Union offences | crime kinds read from intimacy norms (50.8) where the culture names them | scandal, sanction, divorce, feud |
| 685 | Property offences | crime kinds `theft`, `fraud`, `trespass`, `damage` | courts, restitution, guards |
| 687 | Offences against the state | crime kinds `treason`, `sedition`, `desertion`, `tax_evasion` | trials, purges, exile |
| 711 | Military engineering | siege works and fortifications with engineer units | sieges and defences read them |
| 713 | Ordnance | equipment models of artillery families with range, rate and crew | battle missile phases and sieges |
| 715 | Military vehicles | vehicle families of war use (chariots to armoured carriers) with stacks | mobility, shock and protection in battle |
| 717 | Military aircraft | air units and vehicles | air superiority and bombardment |
| 718 | Special military equipment | equipment families `sensor`, `jammer`, `drone`, `ward_node` | scouting, deception and electronic war |
| 755 | Healing rites | healing methods of kind `rite` with success by faith and skill | restore function and morale; failures raise doubt |
| 756 | Spiritual healers | professions of category `healing` with a faith or power base | treat by rite or power; standing by results |
| 759 | Medical personnel | professions of category `healing` with skill and institutions | treatment success, epidemics response |
| 762 | Suicide | incident kind `death.self` with typed causes (`despair`, `honour`, `ritual`, `protest`, `loss`, `illness`) read from stress, standing, values and need, told with care (G9) | kin grief, memory, norms judge it; a protest death can start a movement |
| 763 | Dying | the last acts of a dying mortal (will, confession, naming an heir, last words recorded by the model) as steps (W49) | succession, inheritance, reconciliation, legends |
| 769 | Cult of the dead | ancestral rites (48.7 `ancestral_rite`) with offerings and shrines | ancestor favour (ancestral guardians), house morale, cost |
| 785 | Asceticism | restraint customs and practices (fasting, poverty, solitude) with costs and gains | piety, visions (W25 mysticism), health strain |
| 811 | Logic | knowledge branch with research paths | raises theory testing and law reasoning |
| 812 | Philosophy | knowledge branch and ideologies with tenets (48.7) | shapes ideologies and values over time |
| 813 | Scientific method | technique `empiricism` with effect on theory overturning (theories) | false theories fall faster; research yields rise |
| 814 | Humanistic study | historiography, philology and the study of texts as branches | accounts of history (W20), decipherment, translation quality |
| 874 | Vocational education | apprenticeships and trade schools with skill transfer quality | skilled labour supply, guild control |
| 875 | Teachers | teacher role with skill, lineage and pupils | learning speed, school reputation |
| 880 | Life stages | life stage rules per biology (spec 13 3.1 reference pass) with standing (50.9, 50.11) | duties, rights, work, marriage, office |
| 884 | Coming of age | rites of stage `coming_of_age` with tests and gifts | adult standing, youth group exit (50.11) |
| 890 | Roles by sex | culture data as 562 | as 562 |

**Guard.** `scripts/check_ocm_coverage.py` reads `docs/spec/ocm-coverage.md` (Appendix 50.A as data). It fails when a subcategory has no closing section, or when its closing section names a table or engine step that does not exist once its wave is marked done.

### 50.17 Guards

| Guard | Fails when |
|---|---|
| `scripts/check_ocm_coverage.py` | an OCM subcategory, a UNESCO sub-discipline (Appendix 50.C) or a motif range (Appendix 50.D) has no closing section, or a done closure names a missing table or step; it reads `docs/spec/ocm-coverage.md`, `docs/spec/science-coverage.md` and `docs/spec/motif-coverage.md` |
| `scripts/check_mechanic_couplings.py` | a registered mechanic has fewer than two couplings to other subsystems without a stated reason |
| `scripts/depth_metric.py check` | a node type is below its target after W50 |
| `scripts/check_inventory.py` (5.10) | a table, enum, step, kind, tool, lever, screen or text file of W50 has no inventory row |
| `tests/engine/core/test_daily_life.py`, `test_kin_duties.py`, `test_media.py`, `test_commerce.py`, `test_public_works.py`, `test_population_policy.py`, `test_folk_knowledge.py`, `test_unions_and_birth.py`, `test_childhood.py`, `test_endowments.py`, `test_youth.py`, `test_death_work.py`, `test_speech.py` | a family's behaviour does not produce its effects on a seeded world |

### 50.17a Integration of every family

The rules below apply to each family of 50.1–50.13, and to 50.22–50.29 (50.30). The per-family blocks that follow name what is specific to each.

- **Every era and every kind of world.**
  - Each family reads the world's technology levels per family (47.2), its natural laws, its biologies and its peoples' cultures.
  - A family whose subject a world lacks stays idle there and says so on its screens; this applies, for example, to housework in a people that keeps no houses, or to media before any recording technique.
  - Made minds (W44), innate powers (W45) and living craft (W46) take part wherever their kinds do the family's work.
- **Every kind of thing (rule 6).**
  - Sections that apply to every node render through `ThingSections`. Media, endowments, speeches and policies can be held or authored by any node kind that can act: mortals, peoples, polities, faiths, factions, sons, foreign gods and the Creator.
  - A section for some kinds only says why the others cannot have it.
- **Genesis.**
  - The genesis output (spec 16 5.2) writes each people's starting rows for the families that apply to it, from the seed and the culture, through typed fields only.
  - No family has a template default that carries images. An empty value means the model chooses from the world's canon.
- **Prompts and context.**
  - Each family has a context block (named in its section) that carries typed values with labels.
  - Tool texts list every enum value they accept (`test_tool_enum_lists.py`) and describe every field (`test_catalogue.py`).
  - Templates are read in full when touched (rule 2).
- **Incidents.** Every happening of a family is an incident kind under F58: roles, facts, steps, terms, place and clock. The kinds are listed per family below, and each has a plain template.
- **Rules.**
  - Every number is a rule key in the family's namespace, with its default and range listed below. Each key is editable by the god from the rules screen and read through the registry (G1 no magic numbers).
  - Balance bands for each family are added to `13-balance-bands.json` and kept by `balance_sim.py`.
- **Legacy and integrity.** Each family has recorded fixups as named and checks under 47.13.
- **Book and Codex.** Each family renders as a designed section in the entries of its holders and in the "Records of the Cosmos" appendix, with labelled values and never truncated.

### 50.17b Per-family detail

#### 50.1 Population policy

- **Incidents:** `population.policy_adopted`, `population.policy_repealed`, `population.instrument_enforced`, `population.resisted`, `population.expulsion`, `population.resettlement`, `population.target_met`.
- **Rules:**
  - `population_policy.birth_reward_pct` 10 [0–100]
  - `population_policy.birth_tax_pct` 10 [0–100]
  - `population_policy.child_limit_resistance` 30 [0–100]
  - `population_policy.expulsion_grievance` 40 [0–100]
  - `population_policy.enforcement_cost_per_point` 2 [0–50]
  - `population_policy.review_every_epochs` 2 [1–20]
- **Tools:**
  - mortal `set_population_policy`: `aim`, `instruments` (list of `PopulationInstrument` with `strength` 0–100), `target_node_id`, `reason`;
  - son `move_population_policy`: `holder_node_id`, `aim`, `reason`.
- **Couplings:** births, migration, refugees, health, labour supply, unrest, faith teaching, made births (W44, W46).

#### 50.2 Recorded and mass media

- **Incidents:** `media.outlet_founded`, `media.item_published`, `media.item_exposed`, `media.outlet_censored`, `media.outlet_seized`, `media.record_found`, `media.star_rose`.
- **Rules:**
  - `media.reach_per_staff` 2 [0–20]
  - `media.trust_loss_on_exposure` 25 [0–100]
  - `media.opinion_shift_pct` 15 [0–100]
  - `media.record_decay_per_epoch` 3 [0–50]
  - `media.censorship_cost` 10 [0–100]
  - `media.evidence_weight_pct` 40 [0–100]
- **Tools:**
  - mortal `found_outlet` (`medium`, `audience_node_ids`, `stance` axes, `funding`);
  - mortal `publish_item` (`outlet_id`, `kind`, `subject_incident_id`, `slant`);
  - mortal `censor_outlet` (`outlet_id`, `measure`);
  - son `sway_outlet` (`outlet_id`, `stance` axes, `reason`).
- **Couplings:** opinion, rumours, legitimacy, prices, evidence, historiography, arts (`recorded` mode), law, surveillance, networks.

#### 50.3 Commerce practice

- **Incidents:** `commerce.shop_opened`, `commerce.shop_closed`, `commerce.tier_cornered`, `commerce.promotion_run`, `commerce.claim_exposed`, `commerce.lease_signed`, `commerce.lease_defaulted`, `commerce.rate_shock`.
- **Rules:**
  - `commerce.retail_margin_pct` 20 [0–200]
  - `commerce.wholesale_margin_pct` 10 [0–200]
  - `commerce.promotion_demand_pct` 10 [0–100]
  - `commerce.false_claim_trust_loss` 20 [0–100]
  - `commerce.lease_default_chance_pct` 5 [0–100]
  - `commerce.exchange_spread_pct` 3 [0–50]
  - `commerce.no_shop_basket_pct` 15 [0–100]
- **Tools:**
  - mortal `open_shop` (`form`, `goods_kinds`, `structure_id`);
  - mortal `promote` (`subject`, `medium`, `claim_accuracy`);
  - mortal `lease_out` (`thing_id`, `lessee_id`, `rent`, `term`);
  - mortal `change_money` (`from_currency`, `to_currency`, `amount`).
- **Couplings:** markets, basket, brands, credit, courts, trust, routes, currencies.

#### 50.4 State enterprise and public works

- **Incidents:** `works.begun`, `works.stage_done`, `works.delayed`, `works.finished`, `works.failed`, `works.neglected`, `enterprise.founded`, `enterprise.privatised`, `enterprise.skimmed`.
- **Rules:**
  - `public_works.labour_per_stage` 100 [1–10000]
  - `public_works.quality_floor` 30 [0–100]
  - `public_works.upkeep_pct` 5 [0–50]
  - `public_works.decay_per_neglected_epoch` 10 [0–100]
  - `state_enterprise.monopoly_price_pct` 30 [0–300]
  - `state_enterprise.skim_chance_pct` 10 [0–100]
- **Tools:**
  - mortal `begin_works` (`kind`, `route_or_region_id`, `labour` regime, `budget`);
  - mortal `fund_works` (`works_id`, `amount`);
  - mortal `found_enterprise` (`sector`, `form`, `manager_id`);
  - son `bless_works` (`works_id`, `reason`).
- **Couplings:** routes, harvests, health, war, treasury, labour regimes, companies, terraforming, megastructures.

#### 50.5 Daily life, time and personal care

- **Incidents:** `daily.servant_hired`, `daily.servant_left`, `daily.duty_breached`, `daily.leisure_trend`, `daily.tourism_season`, `daily.norm_breach`.
- **Rules:**
  - `daily_life.overwork_stress_pct` 20 [0–100]
  - `daily_life.leisure_happiness_pct` 10 [0–100]
  - `daily_life.care_disease_pct` 15 [0–100]
  - `daily_life.servant_relief_pct` 30 [0–100]
  - `daily_life.tourism_spend_pct` 5 [0–100]
  - `daily_life.space_breach_trust_loss` 5 [0–100]
- **Tools:**
  - mortal `hire_servant` (`household_id`, `terms`, `duties`);
  - mortal `take_leisure` (`kind`, `venue_id`);
  - mortal `set_house_duties` (`household_id`, assignments by member and `HouseDuty`).
- **Couplings:** labour, needs, stress, disease, sanitation, venues, wealth, etiquette, diplomacy.

#### 50.6 Kin roles, households and kin groups

- **Incidents:** `kin.called_on`, `kin.duty_kept`, `kin.duty_breached`, `kin.group_founded`, `kin.group_split`, `kin.head_chosen`, `kin.land_shared`.
- **Rules:**
  - `kin.help_share_pct` 20 [0–100]
  - `kin.breach_shame` 10 [0–100]
  - `kin.group_exogamy_strength` 80 [0–100]
  - `kin.split_size` 200 [2–100000]
- **Tools:**
  - mortal `call_on_kin` (`role`, `need`);
  - mortal `convene_kin_group` (`group_id`, `agenda`).
- **Couplings:** feuds, inheritance, fostering, unions, councils, migration, households, care.

#### 50.7 Folk knowledge systems

- **Incidents:** `folk.class_learned`, `folk.class_corrected`, `folk.lore_lost`, `folk.misclassification_harm`, `folk.lore_exchanged`.
- **Rules:**
  - `folk_knowledge.accuracy_success_pct` 50 [0–100]
  - `folk_knowledge.loss_on_holder_death_pct` 10 [0–100]
  - `folk_knowledge.contact_gain` 5 [0–50]
  - `folk_knowledge.failure_correction` 10 [0–100]
- **Tools:**
  - mortal `teach_lore` (`domain`, `learner_id`);
  - mortal `test_lore` (`domain`, `class_id`).
- **Couplings:** gathering, herbal treatment, hunting, herding, farming, sailing, care, rule, theories, omens, naming.

#### 50.8 Intimacy, sexual norms and the course of reproduction

- **Incidents:** `unions.norm_changed`, `unions.scandal`, `unions.sanction`, `unions.vow_taken`, `unions.vow_broken`, `birth.complication`, `birth.recovered`, `birth.recognition`.
  - Told plainly and behind closed doors.
- **Rules:**
  - `unions_and_birth.scandal_shame` 15 [0–100]
  - `unions_and_birth.persecution_flight_pct` 10 [0–100]
  - `unions_and_birth.complication_base_pct` 8 [0–100]
  - `unions_and_birth.attendant_care_pct` 50 [0–100]
  - `unions_and_birth.recognition_cost` 10 [0–100]
- **Tools:**
  - mortal `seek_recognition` (`child_id`, `path`);
  - mortal `take_restraint_vow` (`kind`, `term`).
- **Couplings:** attraction, affairs, unions, secrets, leverage, births, health, succession, inheritance, movements.

#### 50.9 Infancy, childhood and socialization

- **Incidents:** `childhood.named`, `childhood.weaned`, `childhood.put_to_work`, `childhood.school_entered`, `childhood.raised_by`, `childhood.method_founded`.
- **Rules:**
  - `childhood.infant_survival_pct` 85 [0–100]
  - `childhood.harsh_stress_pct` 20 [0–100]
  - `childhood.play_cooperation_pct` 10 [0–100]
  - `childhood.labour_schooling_loss_pct` 30 [0–100]
  - `childhood.pedagogy_speed_pct` 20 [0–100]
- **Tools:**
  - mortal `raise_child` (`child_id`, technique weights);
  - mortal `found_school_method` (`school_id`, `theory`).
- **Couplings:** values, traits, skills, labour, schooling, law, households, births.

#### 50.10 Philanthropy and endowments

- **Incidents:** `endowment.founded`, `endowment.paid`, `endowment.skimmed`, `endowment.captured`, `endowment.confiscated`, `endowment.outlived_founder`.
- **Rules:**
  - `endowments.income_pct` 5 [0–50]
  - `endowments.skim_chance_pct` 10 [0–100]
  - `endowments.renown_per_epoch` 2 [0–50]
  - `endowments.confiscation_risk_pct` 5 [0–100]
- **Tools:**
  - mortal `endow` (`beneficiary_id`, `purpose`, `capital`);
  - mortal `audit_endowment` (`endowment_id`).
- **Couplings:** welfare, schools, temples, remembrance, factions, law, dark ages.

#### 50.11 Youth, adolescence and delinquency

- **Incidents:** `youth.group_formed`, `youth.group_disbanded`, `youth.delinquency`, `youth.recruited`, `youth.came_of_age`.
- **Rules:**
  - `youth.delinquency_base_pct` 5 [0–100]
  - `youth.recruitment_pct` 20 [0–100]
  - `youth.service_cooption_pct` 30 [0–100]
- **Tools:**
  - mortal `lead_youth` (`group_id`, `purpose`);
  - mortal `reform_youth` (`group_id`, `measure`).
- **Couplings:** crime, gangs, movements, revolts, schools, festivals, armies.

#### 50.12 Death work and the handling of the dead

- **Incidents:** `death_work.remains_treated`, `death_work.untended`, `death_work.exception`, `death_work.role_shunned`.
- **Rules:**
  - `death_work.untended_disease_pct` 30 [0–100]
  - `death_work.role_standing` 50 [0–100]
  - `death_work.treatment_cost` 5 [0–100]
- **Tools:** no new tool; the existing funeral and rite tools take `remains_treatment`.
- **Couplings:** disease, relics, necromancy, spirits, land use, professions, purity ranks.

#### 50.13 Humour, conversation and public speech

- **Incidents:** `speech.given`, `speech.moved_vote`, `speech.moved_crowd`, `speech.satire_punished`, `speech.offence_taken`.
- **Rules:**
  - `speech.persuasion_pct` 20 [0–100]
  - `speech.satire_legitimacy_loss` 5 [0–100]
  - `speech.offence_threshold` 50 [0–100]
  - `speech.humour_ease_pct` 10 [0–100]
- **Tools:**
  - mortal `give_speech` (`venue`, `aim`, `audience_node_id`);
  - mortal `satirise` (`target_id`, `medium`).
- **Couplings:** assemblies, courts, crowds, congregations, legitimacy, media, diplomacy, trust.

### 50.18 Compliance catalogue (W50)

| Section | Tables | Phases | God levers | Screens | Tools and context | Codex and book | Integrity | Backfill |
|---|---|---|---|---|---|---|---|---|
| 50.1 population policy | `population_policies`, `population_instruments` | demography, migration, births | `population_policy:*`, `population_instrument:*` | "Numbers" section | `set_population_policy`, `move_population_policy`; `population_policy` | holder entries; Records | instruments owned | none |
| 50.2 media | `record_media`, `media_outlets`, `media_items` | communication, opinion, justice, historiography | `record_medium:*`, `media_outlet:*`, `media_item:*` | outlet drawer, "Media" section | `found_outlet`, `publish_item`, `censor_outlet`, `sway_outlet`; `media` | outlets and items | subjects exist | towers, presses, press leverage |
| 50.3 commerce | `shops`, `supply_tiers`, `promotions`, `leases`, `exchange_rates` | markets, trade, credit, basket | `shop:*`, `supply_tier:*`, `promotion:*`, `lease:*`, `exchange_rate:*` | "Commerce" sections | `open_shop`, `promote`, `lease_out`, `change_money`; `commerce` | settlement and owner entries | lease holders; currency pairs | retail tier, shops from workshops |
| 50.4 works and enterprise | `public_works`, `public_work_stages`, `state_enterprises` | construction, routes, treasury | `public_works:*`, `state_enterprise:*` | "Works" panel, atlas layer | `begin_works`, `fund_works`, `found_enterprise`, `bless_works`; `works` | works and enterprises | location in polity | infrastructure levels |
| 50.5 daily life | `time_budgets`, `care_customs`, `housework`, `domestic_service`, `leisure_pursuits`, `space_norms` | households, labour, health, leisure | levers per table | "Daily life" sections | `hire_servant`, `take_leisure`, `set_house_duties`; `daily_life` | daily life chapter | shares sum to 100 | from class, culture and baths |
| 50.6 kin | `kin_role_duties`, `kin_groups`, `kin_group_members` | kinship, feuds, inheritance, households | `kin_role_duty:*`, `kin_group:*`, `kin_group_member:*` | "Kin" section, kin group drawer | `call_on_kin`, `convene_kin_group`; `kin` | kin duties and groups | membership rule | clans, moieties, houses |
| 50.7 folk knowledge | `folk_knowledge`, `folk_classes` | knowledge, theories, work success | `folk_knowledge:*`, `folk_class:*` | "What they know" | `teach_lore`, `test_lore`; `folk_knowledge` | per people per domain | classes point at kinds | from knowledge and beliefs |
| 50.8 unions and birth | `intimacy_norms`, `restraint_customs`, `reproductive_courses`, `legitimacy_rules` | relations, births, succession, justice | levers per table | "Unions and birth" | `seek_recognition`, `take_restraint_vow`; `unions_and_birth` | plain per culture | sexes from biology | from act kinds and laws |
| 50.9 childhood | `infant_care`, `child_standing`, `socialization`, `pedagogy` | births, life course, schools | levers per table | "Childhood" sections | `raise_child`, `found_school_method`; `childhood` | childhood chapter | ages ordered | from values and education |
| 50.10 endowments | `endowments` | treasury, welfare, remembrance | `endowment:*` | founder and beneficiary drawers | `endow`, `audit_endowment`; `endowments` | endowment entries | beneficiary exists | patrons of welfare houses |
| 50.11 youth | `youth_standing`, `youth_groups` | life course, crime, movements | `youth_standing:*`, `youth_group:*` | "Youth" section | `lead_youth`, `reform_youth`; `youth` | youth customs and groups | ages | age sets of youths |
| 50.12 death work | `death_work`; funeral custom treatment | death, health, faith, necromancy | `death_work:*` | "The dead" section | `the_dead` | plain per people | allowed treatment | funeral customs |
| 50.13 speech | `humour_styles`, `speeches` | relations, assemblies, courts, crowds | `humour_style:*`, `speech:*` | incident pages, culture drawers | `give_speech`, `satirise`; `speech` | humour and speeches | venue exists | facets and histories |
| 50.14–50.16 | registry couplings, depth targets, `ocm-coverage.md` | — | — | — | — | — | the guards of 50.17 | — |
| 50.22 space weather | `world_fields`, `star_activity`, `space_weather_events` | sky, cosmos, signals, navigation, body | `world_field:*`, `star_activity:*`, `space_weather_event:*` | "Fields and space weather" in world and star drawers | `shield_world`; `space_weather` | world and star entries | events reach existing worlds | from world physics and star type |
| 50.23 water, ice and sediment | `region_cryosphere`, `sediment_flows`, `coasts`, `local_climates` | environment, routes, agrarian, works, excavation | levers per table | atlas layers | `dredge`, `move_ice`; `water_and_ice` | region entries | flows join existing regions | from terrain and climate |
| 50.24 disease agents | `disease_profiles` agent, survival, reservoirs, cure classes | disease | existing disease levers | disease drawer | `disease` | disease entries | cure classes valid for agent | agents from vector and origin |
| 50.25 body systems | `body_systems`, `sensitivities` | body, travel, settlement | `body_system:*`, `sensitivity:*` | body section | `body` | body sections | systems per biology | from plans and biochemistry |
| 50.26 plant bodies | `plant_anatomy` | ecology, production, agrarian | `plant_anatomy:*` | species drawer | — | species entries | parts match products | generated for plants |
| 50.27 fossils | `fossil_beds` | excavation, extraction, theories, W46 revival | `fossil_bed:*` | region and excavation screens | `study_fossils`; `excavation` | region entries | species exist | from prehistory and geology |
| 50.28 observation and weather works | `observation_methods`, `weather_works` | forecasts, navigation, calendars, weather | `observation_method:*`, `weather_work:*` | people and region drawers | `forecast`, `work_weather`; `forecasting` | people entries | methods per people | from techniques |
| 50.29 professed values | `professions_of_value` | mind, standing, secrets, media | `profession_of_value:*` | mortal drawer | `expose_hypocrisy`; `standing` | mortal entries | acts are recorded incidents | from values and acts |

Every new agent tool has a case in `every_son_tool.py` or `every_mortal_tool.py`. Every lever runs with real values in `test_every_lever.py`. Every table reaches the book and the Codex through `services/books/typed.py`, and every incident kind of W50 follows F58.

### 50.19 Couplings, loops, stories and decisions

**Couplings.**

- C57 Daily life → labour, health, leisure demand.
- C58 Kin duties → feuds, inheritance, care.
- C59 Media → opinion, legitimacy, prices, evidence.
- C60 Works → routes, harvests, health, war.
- C61 Folk knowledge → success of work.
- C62 Socialization → adult values and skills.

**Loops.**

- L113 (R) works raise trade → treasury → more works (brake: upkeep, labour).
- L114 (B) harsh population instruments → flight and grievance → repeal.
- L115 (R) trusted outlet → aligned opinion → more audience (brake: exposure of false items).
- L116 (B) heavy housework → less schooling → lower skill → poorer households → heavier housework, broken by servants, made minds or works.
- L117 (R) endowed schools → scholars → founders' renown → more endowments.

**Acceptance stories.**

- AS57 **The Canal and the Levy.** A polity begins a canal with levy labour; grievance rises; a youth group joins a revolt; the canal finishes late but doubles trade.
- AS58 **The Paper and the Trial.** An outlet prints a slanted account of a killing; a recorded image in an archive contradicts it in court; the outlet's trust falls.
- AS59 **The Grandparent's Duty.** A parent dies; kin duties send the child to a grandparent; the household's load rises; the child's schooling stops; the child's adult skills differ.
- AS60 **The Wrong Plant.** A people's folk knowledge classes a plant as food; a famine forces its use; illness follows; contact with a neighbour's lore corrects the class.

**Decisions.**

| Id | Question | Decision |
|---|---|---|
| K.46 | Which taxonomy closes "granularity"? | The 689 world-content subcategories of the OCM 2025 edition, kept as data in `docs/spec/ocm-coverage.md`, plus the registry and the depth metric. |
| K.47 | How are intimacy and reproduction told? | Plainly and behind closed doors, as typed norms a culture authors; no default, no quota, no explicit content. |
| K.48 | May a mechanic stay isolated? | Only a bookkeeping mechanic, with its reason stated in the registry. |
| K.49 | Which lists close nature, cosmos, myth and magic? | The six-digit UNESCO nomenclature for fields 21, 24 and 25 (374 sub-disciplines) and the 259 ranges of the Thompson motif index, kept as data beside the OCM list. |

### 50.20 Execution order

1. The guards (50.17) and `docs/spec/ocm-coverage.md` come first, so they list every gap.
2. 50.5 daily life.
3. 50.6 kin.
4. 50.9 childhood.
5. 50.8 unions and birth.
6. 50.11 youth.
7. 50.1 population policy.
8. 50.3 commerce.
9. 50.4 works and enterprise.
10. 50.2 media.
11. 50.13 speech.
12. 50.7 folk knowledge.
13. 50.10 endowments.
14. 50.12 death work.
15. 50.16 facets.
16. 50.14 couplings.
17. 50.15 depth targets.
18. 50.22–50.29, nature, cosmos and standing, with the detail of 50.30.
19. Surfaces, fixups and the audit.

The wave is gated once.

### 50.21 Nature, cosmos, myth and magic at subcategory level

The OCM covers human life. The natural world, the cosmos, myth and magic were swept by spec 13 at the level of major classes only. W50 applies the same closed method to two more fixed lists:

- **The natural world and the cosmos.** The six-digit UNESCO International Standard Nomenclature for Fields of Science and Technology (the TESEO code list): every sub-discipline of 21 Astronomy and Astrophysics (37), 24 Life Sciences (175, after leaving out `240213`, which classifies people by race and is not world content) and 25 Earth and Space Sciences (162).
- **Myth, magic and the shapes of story.** Stith Thompson's *Motif-Index of Folk-Literature*: all 259 ranges of its 23 divisions, from A (mythological motifs) and D (magic) to E (the dead), F (marvels), M (ordaining the future), N (chance and fate) and V (religion).

**Results.**

| List | Own state and behaviour | Some typed state | A label only | Absent |
|---|---:|---:|---:|---:|
| UNESCO sub-disciplines (374) | 104 | 69 | 64 | 137 |
| Motif ranges (259) | 144 | 55 | 29 | 31 |

A second pass checked every label-only and absent item by synonyms and tables. Three kinds of item turned out to be covered elsewhere:

- **Things that exist under other names.** Supernova remnants and nebulae are galactic structure kinds; comets are cosmic features and impacts; auroras are a world physics column; crop pests and immunity have their own tables.
- **Items planned in spec 13.** Layered geology (G1R.3.1), aquifers (G1R.3.2), river hydrology (G1R.3.3), tectonics (G1R.4.7), microbes, symbiosis, dormancy, thermoregulation, senses and plant defences (W34), and biogeography (G1R.23.7).
- **Methods of a science rather than facts of a world.** Telescopes, spectroscopy, photogrammetry, radar and numerical models, which the world reaches as knowledge techniques and instruments.

What no section carried is closed in 50.22–50.29.

Below the engine's scale (cells, molecules, chromosomes), the world is read through tissues (F23), heredity (spec 13 F14 and W46 46.3) and disease agents (50.24). This scale bridging is stated for every such item in Appendix 50.C.

### 50.22 Space weather and magnetic fields

**Builds on.** Spec 13 10.1 reference pass (flares that paint auroras, mutate life, fail crops and wreck light-sail routes) and 10.9 (the magnetosphere that makes a compass work). Spec 13's coverage table counts space weather as covered by those (`13-depth-expansion.md` 1R lane table). 50.22 keeps them and makes the flare one kind of space weather event among several, so the existing flare effects are read through this section.

**Current.** Stars have activity and radiation, worlds have radiation and an aurora column, flares are a sky event kind, and the compass works only where a world has a magnetosphere. Field strength, reversals, shielding, particle storms, signal outages and compass error are not modelled.

**State.**

- **`world_fields`.** World, magnetosphere strength (0–100), field reversals (epoch, length), upper air shielding (0–100), radiation at the surface (derived).
- **`star_activity`.** Star, cycle length in years, phase, flare rate, particle storm rate, wind strength.
- **`space_weather_events`.** Star or source, kind (`SpaceWeatherKind`: `flare`, `particle_storm`, `field_storm`, `field_reversal`, `cosmic_ray_burst`, `wind_surge`), strength, worlds and orbits reached, epoch.

**Behaviour.**

1. Activity follows the star's cycle and evolution. Events reach worlds by distance and the world's shielding (field and air).
2. Effects are typed by what they reach:
   - auroras at the poles or everywhere by strength;
   - radiation dose to beings outside shelter and in orbit (body harm, mutation chance where biology allows);
   - outages of signals and networks (F51, 47.2);
   - compass errors and navigation loss (50.28);
   - crop and herd stress at extreme doses;
   - spacecraft section damage (W49 49.3).
3. Field reversals weaken shielding for their length and move auroras toward the equator. Peoples read them as omens through their faiths.
4. Gods and powers that span worlds can strengthen or strip a world's field. Living worlds may grow their own.

**Tools and control.**

- Son tool `shield_world`.
- God levers `world_field:*`, `star_activity:*`, `space_weather_event:*`.
- A "Fields and space weather" section in world and star drawers.
- Context block `space_weather`.

**Incidents.** `sky.flare`, `sky.particle_storm`, `sky.field_reversal`, `sky.outage`.

**Rules namespace.** `space_weather`:

- `flare_base_pct` 5 [0–100]
- `shield_per_field_point` 1 [0–5]
- `outage_threshold` 40 [0–100]
- `dose_harm_per_point` 1 [0–20]
- `reversal_chance_per_epoch_pct` 1 [0–100]

**Legacy.** World fields come from world physics (mass, rotation, core); star activity from star type and age.

### 50.23 Water, ice and sediment in place

**Builds on.** Spec 13 6.1 reference pass: rivers with flow, navigability, salinity in estuaries, flood plains, spring floods from snowmelt, dams and canals, aquifers. That pass is built first by whichever wave reaches it (0.7); 50.23 reads its rivers and adds what it lacks.

**Current.** Rainfall, winds, rain shadows, currents, monsoons, climate ages and a global cryosphere exist. Rivers with flow and aquifers are planned in spec 13. Seasonal ice on seas and lakes, frozen ground, snowpack, sediment carried and laid down by water and wind, coasts that build or wear away, and the climate of a valley or a city are not modelled.

**State.**

- **`region_cryosphere`.** Region: sea or lake ice (months per year, thickness), frozen ground (depth, seasonal thaw), snowpack (depth, melt season), glaciers (extent, advance or retreat).
- **`sediment_flows`.** Source region, sink region, carrier (`SedimentCarrier`: `river`, `wind`, `ice`, `wave`, `slope`), load, kind (silt, sand, gravel, volcanic, organic).
- **`coasts`.** Region: form (`CoastForm`: `cliff`, `beach`, `delta`, `marsh`, `reef`, `ice_shelf`, `fjord`, `lagoon`), building or wearing rate, harbour silting.
- **`local_climates`.** Region or district: shift of temperature, humidity and wind from valleys, slopes, water bodies, forests and built land.

**Behaviour.**

1. Seasonal ice blocks or opens sea and river routes, makes ice roads, and sets fishing seasons.
2. Frozen ground limits farming, building and burial; its thaw can collapse structures and release what it held (preserved remains, old disease where the world allows).
3. Snowpack stores water and releases it in its melt season, feeding rivers and irrigation; a poor snow year means a dry summer downstream.
4. Sediment builds deltas and marshes, fertilises flood plains, silts harbours and canals (upkeep for 50.4 works) and buries settlements and finds (excavation layers).
5. Coasts build or wear away. Wearing claims fields and structures; building moves harbours inland over generations.
6. Local climates shape where crops grow, where people prefer to live, disease exposure and the heat of dense districts.

**Tools and control.**

- Mortal tool `dredge`; son tool `move_ice`.
- God levers `region_cryosphere:*`, `sediment_flow:*`, `coast:*`, `local_climate:*`.
- Layers on the atlas.
- Context block `water_and_ice`.

**Incidents.** `land.ice_closed`, `land.ice_opened`, `land.thaw_collapse`, `land.snow_drought`, `land.silted`, `land.coast_lost`, `land.delta_grew`.

**Rules namespace.** `water_and_ice`:

- `silting_per_epoch` 2 [0–50]
- `coast_wear_per_epoch` 1 [0–50]
- `thaw_collapse_pct` 5 [0–100]
- `snow_water_share_pct` 30 [0–100]

**Legacy.** Derived from terrain, climate, latitude and existing rivers and coasts.

### 50.24 Agents of disease

**Current.** Diseases have vectors, virulence, lethality, targets, climate affinity, host species, immunity, resistance, mutation and cures. What a disease *is*, and therefore what can cure it and where it survives, is not typed.

**State.**

- `disease_profiles` gains `agent` (`DiseaseAgent`: `virus`, `bacterium`, `fungus`, `parasite`, `prion`, `toxin`, `deficiency` (nutrition, F39), `spirit` (where spirits exist), `curse` (where curses exist), `made` (W44, W46 designed), `unknown`).
- It also gains environmental survival (outside a host, in water, in soil, in cold), reservoir species, and the cure classes that work (`CureClass`: `rest_and_care`, `herbal`, `antimicrobial`, `antiparasitic`, `antitoxin`, `nutritional`, `rite`, `exorcism`, `power`, `designed`).

**Behaviour.**

1. Cures work only by class. A rite does nothing against a bacterium unless the world's natural laws make faith heal. An antimicrobial does nothing against a curse. Theories of disease (folk and formal, 50.7) decide which cures a people tries.
2. Agents evolve by kind: bacteria resist overused antimicrobials, viruses mutate fast, prions do not. Each kind has its typed rate.
3. Survival outside the host sets which spread paths work: water, soil, objects or only bodies. Reservoirs keep a disease alive between outbreaks.
4. Deficiencies follow diet (F39) and spread with famine and monotony, not contact.

**Tools and control.**

- Existing disease levers gain the new fields.
- Context block additions to `disease`.

**Incidents.** `disease.resistance_rose`, `disease.wrong_cure`, `disease.reservoir_found`.

**Rules namespace.** `disease`:

- `resistance_per_overuse` 5 [0–50]
- `agent_mutation_pct` (per agent kind)
- `survival_by_medium` (per agent kind)

**Legacy.** Agents are assigned from vector, target and origin. `unknown` is used where nothing fits, until the model or the god sets one.

### 50.25 Bodies: systems and sensitivities

**Builds on.** Spec 13 10.9 world physics (gravity slows armies and caps buildings, thin air saps endurance, toxic air breeds disease) and spec 13 W34 (thermoregulation, senses). 50.25 reads those world values through each biology's tolerances, so the same world weighs differently on different bodies.

**Current.** Bodies have plans, parts, tissues, organs, senses (planned), functions, conditions, immunity and decompression harm. The internal systems that run a body (breath, blood, digestion, hormones, nerves), and individual sensitivities, are not modelled as systems.

**State.**

- **`body_systems`.** Per biology: systems (`BodySystem`: `breath`, `circulation`, `digestion`, `regulation` (hormones and their equivalents), `nerves`, `immunity`, `reproduction`, `structure`, `none` for bodies without them). Each system has its tolerances: air and pressure, cold and heat, gravity, diet range, sleep need, toxins.
- **`sensitivities`.** Per being: kind (`Sensitivity`: `to_food`, `to_plant`, `to_animal`, `to_material`, `to_substance`, `to_light`, `to_sound`, `to_power`), trigger kind, severity.

**Behaviour.**

1. Tolerances decide where a being can live and travel unaided: gravity, air, cold, radiation (50.22), depth. They also decide what equipment (48.4), augments (W44) or grown organs (W46) it needs to go further.
2. Damage to a system has typed effects through capacities (F23): breath loss limits exertion, digestion loss limits diet, regulation loss changes growth and mood.
3. Sensitivities trigger on contact with their kind: harm, illness, the loss of a food or a trade. Peoples learn which plants and goods to avoid (50.7).
4. Low gravity, long voyages and new worlds wear on systems (W49 group 4 steps).

**Tools and control.**

- God levers `body_system:*`, `sensitivity:*`.
- The body section shows systems and sensitivities.
- Context block additions to `body`.

**Incidents.** `body.system_failed`, `body.sensitivity_reaction`, `body.tolerance_exceeded`.

**Rules namespace.** `body_systems`.

**Legacy.** Systems derived from body plans and biochemistry. No sensitivities at start, except where the model assigns them.

### 50.26 Plant bodies

**Current.** Plants are species with classes, yields, perennials, crop pests and blight. Unlike creatures, they have no generated anatomy, so the products they yield do not follow from their bodies.

**State.**

- **`plant_anatomy`.** Per plant species: growth form (`PlantForm`: `tree`, `shrub`, `herb`, `grass`, `vine`, `succulent`, `aquatic`, `moss_like`, `fungus_like`, `colonial`, `made`). It also holds parts with typed properties (`PlantPart`: `root`, `tuber`, `stem`, `wood`, `bark`, `leaf`, `flower`, `fruit`, `seed`, `sap`, `fibre`, `spore`), defences (W34), lifespan, season of growth and the reproduction mode.

**Behaviour.**

1. Products (48.5) derive from parts: wood from stems, fibre from stems or seeds, dyes and medicines from flowers, roots and bark, food from fruit, seed, tuber or leaf.
2. Growth form sets land use, labour and time to first harvest, and storm and fire damage.
3. Reproduction mode sets spread, invasion and domestication (W46 46.2).

**Tools and control.**

- God levers `plant_anatomy:*`.
- A plant anatomy section in species drawers.

**Legacy.** Generated for existing plant species from their class and yields.

**Rules namespace.** `plants`.

### 50.27 The deep record of life

**Builds on.** Spec 13 6.2 reference pass 7 is the base: fossil beds in the geology column hold remains of extinct species, megafauna, beasts, earlier creations and extinct peoples. They are found by mining, by erosion after floods and quakes, and by excavation. Cultures read them through their theories (dragon bones in legends, relics of giants, evidence of deep time). Fossil materials are luxuries. It is built first by whichever wave reaches it (0.7). 50.27 extends it and does not replace it.

**Current.** Extinction exists and excavations find typed items. Fossil beds are planned in spec 13 but not built. Preservation kinds, the richness of beds, the link from organic beds to coal and oil, and revival of extinct species from preserved remains are not specified anywhere.

**State.**

- **`fossil_beds`.** Region, layer (excavation layers and spec 13 G1R.3.1 strata), species represented (extinct or living), preservation (`Preservation`: `rock`, `amber`, `ice`, `bog`, `tar`, `ash`, `dry`), richness.

**Behaviour.**

1. Extinctions and mass deaths over deep time (spec 13 F48 prehistory) lay down beds where conditions preserve them.
2. Excavations and mines find fossils. Peoples read them through their knowledge:
   - as the bones of past beings in a people's own terms (legends, relics, monster lore);
   - as evidence that overturns theories (theories, 50.7);
   - as materials of trade and craft.
3. Fossil fuels (coal and oil from organic beds) follow the same layers, linking extraction to deep time.
4. Designed revival of extinct species (W46) needs preserved remains.

**Tools and control.**

- Mortal tool `study_fossils`.
- God levers `fossil_bed:*`.
- Beds on the excavation and region screens.

**Incidents.** `land.fossil_found`, `land.fossil_read`, `life.revived`.

**Rules namespace.** `fossils`.

**Legacy.** Beds derived from prehistory, extinctions and region geology.

### 50.28 Observation, forecasting and the shaping of weather

**Builds on.** Spec 13 10.7 reference pass 5: climate oscillations whose rhythm diviners and astronomers can learn and predict. Also W25's forecast models and winter forecasts. 50.28 types the methods behind such prediction and extends them to every forecast.

**Current.**

- Navigation reads seamanship.
- Forecast models and winter forecasts exist (W25).
- Sons can shape weather.
- Folk knowledge of weather and sky is 50.7.

Methods of observation, the accuracy of forecasts by method, and mortal attempts to change the weather are not typed.

**State.**

- **`observation_methods`.** Per people: method kinds by domain (`ObservationMethod`: `sight`, `lore`, `almanac`, `instrument`, `network_of_observers`, `model`, `network` (W44), `power` (W45), `divination` (W25)), with accuracy and reach.
- **`weather_works`.** Holder, region, method (`WeatherWorkMethod`: `rite`, `power`, `seeding`, `diversion`, `made_structure`, `living_craft`), aim (rain, dry, calm, cold, warm), strength, cost, side effects.

**Behaviour.**

1. Forecast accuracy by method sets farming choices (sowing date), sailing losses, war timing and disaster preparation. An accurate forecast that is not believed still fails (trust, 50.2).
2. Instruments and observer networks raise navigation accuracy, calendar precision and discovery of sky events.
3. Weather works shift a region's weather within the world's laws, at a cost and with typed side effects downwind (drought elsewhere). Neighbours read them as acts with intent, and treaties may ban them.

**Tools and control.**

- Mortal tools `forecast`, `work_weather`.
- God levers `observation_method:*`, `weather_work:*`.
- Context block `forecasting`.

**Incidents.** `weather.forecast_kept`, `weather.forecast_failed`, `weather.worked`, `weather.side_effect`.

**Rules namespace.** `forecasting`.

**Legacy.** Methods derived from techniques (astronomy instruments, cartography, navigation) and folk knowledge.

### 50.29 Professed values and acts

**Current.** Values, ethics, judged acts and reputation exist. The gap between what a being professes and what it does, and the cost when that gap is seen, is not modelled. The motif index's hypocrites (K2000) are its narrative form.

**State.** `professions_of_value`: holder, value axis or tenet, strength professed, the acts recorded against it (incidents, W49), the gap, and who knows it.

**Behaviour.**

1. Every judged act is compared with the actor's professed values. A wide gap, once witnessed or exposed (secrets, media, rumour), costs trust, legitimacy and following, and gives leverage to those who know.
2. Leaders with wide gaps lose followers who hold the professed value strongly, and keep those who follow for other reasons.

**Tools and control.**

- Mortal tool `expose_hypocrisy`.
- God levers `profession_of_value:*`.
- Context block additions to `standing`.

**Incidents.** `standing.hypocrisy_exposed`.

**Rules namespace.** `standing`.

**Legacy.** Derived from values and recorded acts.

### 50.30 Integration detail for 50.22–50.29

The rules of 50.17a apply to 50.22–50.29 in full:

- every era and every kind of world;
- every kind of thing through `ThingSections`, where a section applies to every node, with a stated reason where it applies to some kinds only;
- genesis through typed fields only;
- typed context blocks;
- incidents under F58;
- every number a rule key;
- balance bands in `13-balance-bands.json`;
- recorded fixups;
- checks under 47.13;
- designed sections in the book and the Codex, never truncated.

What is specific to each section follows.

#### 50.22 Space weather and magnetic fields

- **Applies to:** worlds, moons, stars, orbits, vessels and stations in space, and every being outside shelter. Worlds without a star (rogue worlds, made realms) read only the fields and sources they have.
- **Incidents:** `sky.flare`, `sky.particle_storm`, `sky.field_storm`, `sky.field_reversal`, `sky.cosmic_ray_burst`, `sky.wind_surge`, `sky.outage`, `sky.aurora_spread`.
- **Rules:**

  | Key | Default | Range |
  |---|---|---|
  | `space_weather.flare_base_pct` | 5 | 0–100 |
  | `space_weather.storm_base_pct` | 3 | 0–100 |
  | `space_weather.shield_per_field_point` | 1 | 0–5 |
  | `space_weather.shield_per_air_point` | 1 | 0–5 |
  | `space_weather.outage_threshold` | 40 | 0–100 |
  | `space_weather.compass_error_threshold` | 30 | 0–100 |
  | `space_weather.dose_harm_per_point` | 1 | 0–20 |
  | `space_weather.mutation_per_dose_pct` | 1 | 0–100 |
  | `space_weather.reversal_chance_per_epoch_pct` | 1 | 0–100 |
  | `space_weather.reversal_length_epochs` | 2 | 1–50 |

- **Tool:** son `shield_world` (`world_id`, `change` of field strength −100 to 100, `epochs`, `reason`).
- **Couplings:** body harm, genetics (mutation), networks and signals, navigation, agrarian stress, vessels, omens, natural laws.

#### 50.23 Water, ice and sediment in place

- **Applies to:** every region of every world, by its climate and terrain. Worlds of other liquids and ices read their own (methane seas freeze and silt by the same rules with their own temperatures).
- **Incidents:** `land.ice_closed`, `land.ice_opened`, `land.ice_road`, `land.thaw_collapse`, `land.thaw_release`, `land.snow_drought`, `land.silted`, `land.dredged`, `land.coast_lost`, `land.delta_grew`, `land.glacier_advanced`, `land.glacier_retreated`.
- **Rules:**

  | Key | Default | Range |
  |---|---|---|
  | `water_and_ice.silting_per_epoch` | 2 | 0–50 |
  | `water_and_ice.dredge_cost` | 10 | 0–500 |
  | `water_and_ice.coast_wear_per_epoch` | 1 | 0–50 |
  | `water_and_ice.delta_growth_per_epoch` | 1 | 0–50 |
  | `water_and_ice.thaw_collapse_pct` | 5 | 0–100 |
  | `water_and_ice.snow_water_share_pct` | 30 | 0–100 |
  | `water_and_ice.ice_route_block_months` | 3 | 0–12 |
  | `water_and_ice.local_heat_per_density` | 1 | 0–10 |

- **Tools:**
  - mortal `dredge` (`region_id` or `works_id`, `budget`);
  - son `move_ice` (`region_id`, `change` of ice months −12 to 12, `reason`).
- **Couplings:** routes, fisheries, irrigation, harvests, construction, burials, excavation layers, harbours, settlement choice, disease (waterlogged and frozen ground).

#### 50.24 Agents of disease

- **Applies to:** every disease, including diseases of beasts, plants (crop pests and blight), made bodies (W44, `made` agents) and spirits where they exist.
- **Incidents:** `disease.resistance_rose`, `disease.wrong_cure`, `disease.right_cure`, `disease.reservoir_found`, `disease.agent_identified`.
- **Rules:**

  | Key | Default | Range |
  |---|---|---|
  | `disease.resistance_per_overuse` | 5 | 0–50 |
  | `disease.mutation_virus_pct` | 10 | 0–100 |
  | `disease.mutation_bacterium_pct` | 5 | 0–100 |
  | `disease.mutation_fungus_pct` | 3 | 0–100 |
  | `disease.mutation_parasite_pct` | 2 | 0–100 |
  | `disease.mutation_prion_pct` | 0 | 0–100 |
  | `disease.survival_water_pct` | 30 | 0–100 |
  | `disease.survival_soil_pct` | 20 | 0–100 |
  | `disease.survival_object_pct` | 10 | 0–100 |
  | `disease.wrong_cure_trust_loss` | 5 | 0–100 |

  The mutation and survival defaults are set per agent kind in `catalog/disease_agents.py`, a `total()` table.
- **Tool:** the existing `seek_cure` and `answer_sickness` tools take `cure_class`.
- **Couplings:** cures, theories of disease (50.7), trade in medicines, diet (deficiencies), ecology (reservoirs), faith (rites as cures), powers.

#### 50.25 Bodies: systems and sensitivities

- **Applies to:** every biology, including bodies without some systems (spirits, constructs, made bodies), whose rows say `none` for the systems they lack.
- **Incidents:** `body.system_failed`, `body.system_recovered`, `body.sensitivity_reaction`, `body.tolerance_exceeded`, `body.adapted`.
- **Rules:**

  | Key | Default | Range |
  |---|---|---|
  | `body_systems.tolerance_harm_per_point` | 2 | 0–20 |
  | `body_systems.adaptation_per_epoch` | 2 | 0–20 |
  | `body_systems.sensitivity_reaction_pct` | 50 | 0–100 |
  | `body_systems.low_gravity_wear` | 1 | 0–20 |
  | `body_systems.system_loss_capacity_pct` | 30 | 0–100 |

- **Tool:** no new tool. Travel, colonisation and expedition tools read tolerances.
- **Couplings:** travel and colonisation, equipment, augments (W44), grown organs (W46), diet, folk knowledge (what to avoid), medicine.

#### 50.26 Plant bodies

- **Applies to:** every plant and plant-like species on every world, including fungus-like, colonial and made plants.
- **Incidents:** `life.plant_spread`, `life.plant_invaded`, `life.plant_domesticated`.
- **Rules:**

  | Key | Default | Range |
  |---|---|---|
  | `plants.years_to_first_harvest_tree` | 5 | 0–50 |
  | `plants.storm_damage_tree_pct` | 20 | 0–100 |
  | `plants.fire_damage_grass_pct` | 40 | 0–100 |
  | `plants.spread_by_wind_pct` | 10 | 0–100 |
  | `plants.spread_by_animal_pct` | 5 | 0–100 |

- **Tool:** no new tool. Sowing and shaping tools read anatomy.
- **Couplings:** species products, land use, labour, disasters, ecology (invasion), W46 design.

#### 50.27 The deep record of life

- **Applies to:** every world with past life. Worlds made recently, or without life, hold none.
- **Incidents:** `land.fossil_found`, `land.fossil_read`, `land.fossil_traded`, `life.revived`.
- **Rules:**

  | Key | Default | Range |
  |---|---|---|
  | `fossils.find_chance_per_dig_pct` | 10 | 0–100 |
  | `fossils.theory_shift` | 10 | 0–100 |
  | `fossils.value` | 5 | 0–100 |
  | `fossils.revival_preservation_min` | 60 | 0–100 |

- **Tool:** mortal `study_fossils` (`bed_id` or `item_id`, `scholar_id`).
- **Couplings:** excavation, mining, theories, legends and relics, trade, coal and oil, W46 revival.

#### 50.28 Observation, forecasting and the shaping of weather

- **Applies to:** every people, and every holder of a power, rite or structure that can work weather.
- **Incidents:** `weather.forecast_kept`, `weather.forecast_failed`, `weather.forecast_ignored`, `weather.worked`, `weather.side_effect`, `weather.work_banned`.
- **Rules:**

  | Key | Default | Range |
  |---|---|---|
  | `forecasting.accuracy_sight` | 20 | 0–100 |
  | `forecasting.accuracy_lore` | 35 | 0–100 |
  | `forecasting.accuracy_almanac` | 45 | 0–100 |
  | `forecasting.accuracy_instrument` | 60 | 0–100 |
  | `forecasting.accuracy_network_of_observers` | 70 | 0–100 |
  | `forecasting.accuracy_model` | 85 | 0–100 |
  | `forecasting.weather_work_strength` | 20 | 0–100 |
  | `forecasting.weather_work_cost` | 20 | 0–500 |
  | `forecasting.side_effect_share_pct` | 50 | 0–100 |

- **Tools:**
  - mortal `forecast` (`region_id`, `season`, `method`);
  - mortal `work_weather` (`region_id`, `aim`, `method`, `strength`).
- **Couplings:** sowing, sailing, war timing, disaster preparation, trust and media (50.2), treaties, navigation, calendars.

#### 50.29 Professed values and acts

- **Applies to:** every being that holds values: mortals, peoples, polities, faiths, factions, sons, foreign gods and the Creator, whose professed passions are already revealed by the reputation mechanics.
- **Incidents:** `standing.hypocrisy_exposed`, `standing.hypocrisy_forgiven`.
- **Rules:**

  | Key | Default | Range |
  |---|---|---|
  | `standing.hypocrisy_gap_threshold` | 30 | 0–100 |
  | `standing.hypocrisy_trust_loss` | 15 | 0–100 |
  | `standing.hypocrisy_follower_loss_pct` | 10 | 0–100 |

- **Tool:** mortal `expose_hypocrisy` (`target_id`, `value_axis_or_tenet`, `evidence_incident_ids`).
- **Couplings:** trust, legitimacy, following, secrets and leverage, media, faith (clergy), reputation of gods.

#### Guards, couplings, loops, stories

**Tests.** `tests/engine/core/test_space_weather.py`, `test_water_and_ice.py`, `test_disease_agents.py`, `test_body_systems.py`, `test_plant_bodies.py`, `test_fossils.py`, `test_forecasting.py` and `test_hypocrisy.py` each prove their section's effects on a seeded world. Each new tool has a case in `every_son_tool.py` or `every_mortal_tool.py`, and each lever runs with real values in `test_every_lever.py`.

**Couplings.**

- C63 Space weather → body, signals, navigation.
- C64 Ice and sediment → routes, harvests, works.
- C65 Disease agents → cures and trust.
- C66 Body tolerances → travel and colonisation.
- C67 Fossils → theories and legends.
- C68 Forecasts → sowing, sailing and war.
- C69 Hypocrisy → trust and following.

**Loops.**

- L118 (B) overused cure → resistance → cure fails → use falls → resistance fades.
- L119 (R) silting harbour → trade moves to a new harbour → the old town declines → no dredging → more silting.
- L120 (B) weather work → drought downwind → neighbours' grievance → treaty ban.

**Acceptance stories.**

- AS61 **The Quiet Compass.** A field reversal weakens a world's shield; auroras reach the equator; signals fail; a fleet's compasses err and it is lost; its people read the auroras as an omen.
- AS62 **The Silted Port.** A river's sediment silts a trading port; the realm cannot pay for dredging; trade moves to a delta town; the old port's guilds decline.
- AS63 **The Wrong Cure.** A people treats a bacterial sickness with rites, as its theory of disease holds; the sickness spreads; a neighbour's antimicrobial cures it; the theory falls and the faith's healers lose standing.

## Part 11. W51 — Orders of the economy, institutions of states, and the gaps found by search

### 51.0 Scope and the search behind it

W50 closed every gap that three fixed lists could name (the OCM, the UNESCO nomenclature and the motif index). W51 closes what those lists could not name: a question about economic orders and the inner workings of companies showed that a facet can be present in a list's wording and still be missing as a mechanic. An open search followed on 2026-11-14. Every candidate concept was matched against every table, column, enum value, engine and catalogue module, agent tool and god lever, and against the text of spec 13 and this spec, with synonyms. Every candidate that matched nothing was searched again under other names before it was counted.

**Lists and axes searched.**

| Source | Size | What it checks |
|---|---:|---|
| Candidate lists of concepts from economics, politics, law, war, faith, society, body, nature and the cosmos | 1,197 patterns in 13 lists | each concept by name and synonyms |
| The Dewey Decimal Classification | 693 sections | every field of knowledge a world can hold |
| Human universals (the Brown list and its successors) | 103 items | every trait found in all known societies |
| Core mechanics of other genres (grand strategy, city builders, management, colony sims, roguelikes, 4X) | one pass per genre | every mechanic a genre is known for |
| Lifecycle axis | 43 entity kinds | founding, splitting, merging, changing hands, falling and reviving for each |
| Scale axis | person, household, settlement, polity, world, system, galaxy, cosmos | the same mechanic at every scale |
| Actor axis | mortals, organisations, polities, sons, foreign gods, the Creator, made minds, creatures, the dead | each verb for each actor |
| Typologies | governments, organisations, institutions, offices | each kind against the enums |

**Results.** Almost every candidate exists, under its own name or another (strikes are a collective act kind, companies have shares and dividends, interpreters are a rule set and a skill, game reserves and poaching are built, fire brigades and urban morphology are built, elections are built). Thirty gaps were found. While this part was written, each was checked again against spec 13:

- **One is planned in spec 13 and is not a section here.** Performance troupes are spec 13 7.4 reference pass (faction kind `troupe`, still planned). They are built there.
- **Three are joined into one section.** Zoning and building rules, municipal services and the merging of settlements share the city model of spec 13 4.2 reference pass 3 (built: districts, service coverage, `firehouse`, morphology, slums, suburbs), so they form 51.8.
- **Several are narrowed to what is missing.** Each section opens with **Builds on**, which names what exists and what is planned, so nothing is built twice (rule 0.7).

**Where each finding is closed.**

| # | Finding | Closed by |
|---:|---|---|
| 1 | Economic orders and their transitions | 51.1 |
| 2 | Inner life of organisations and companies | 51.2 |
| 3 | Market structure and competition | 51.3 |
| 4 | Organised labour | 51.4 |
| 5 | Central banks and monetary policy | 51.5 |
| 6 | Securities, exchanges, bubbles and crashes | 51.6 |
| 7 | International organisations | 51.7 |
| 8 | Urban planning and zoning | 51.8 |
| 9 | Nature conservation | 51.9 |
| 10 | Abdication and retirement from office | 51.10 |
| 11 | Referendums | 51.11 |
| 12 | Transitional justice | 51.12 |
| 13 | Personality cults of living leaders | 51.13 |
| 14 | Weapons of mass harm, deterrence and war remnants | 51.16 |
| 15 | Family dynamics | 51.18 |
| 16 | Emotional contagion | 51.19 |
| 17 | Interpreters and mistranslation | 51.20 |
| 18 | Grave goods and tomb robbing | 51.21 |
| 19 | Non-communicable conditions | 51.22 |
| 20 | Fertility control | 51.23 |
| 21 | Tsunamis and storm surges | 51.25 |
| 22 | Creature societies | 51.26 |
| 23 | Conceptions of the divine | 51.27 |
| 24 | Performance institutions | spec 13 7.4 reference pass (`troupe`), planned there; not built twice |
| 25 | Honours and awards conferred on persons | 51.24 |
| 26 | Municipal services | 51.8 |
| 27 | Merging settlements into conurbations | 51.8 |
| 28 | Restoration of fallen polities | 51.14 |
| 29 | War between worlds and migration between worlds | 51.17 |
| 30 | Occupation regimes: collaboration, measures, administration | 51.15 |

The 27 sections below close the rest. A correction found by the same search is made in 50.3: exchange rates and money changers are planned in spec 13 6.4 reference pass 6 (W35), and 50.3 now builds on them.

Every section follows the ground rules of 0.4 and 0.5: concepts by function, values from the seed and the world's canon, no imagery, no quotas, no gendered default, every era and every kind of world, and every kind of thing (rule 6). Each carries its thirteen elements in its own text (Appendix 16.L) and is wired end to end under its compliance row (51.30).

### 51.1 Economic orders

**Builds on.** Spec 13 4.6 reference pass 6 plans `economic_system` per polity with five systems (market, redistributive palace or temple, command, manorial, gift and tribal) and their crisis paths, in W35 (planned). Whichever wave runs first builds that column fully (0.7). 51.1 replaces the single value with four typed axes, so the five systems become rows of a catalogue of named orders and every other order a world can hold can be expressed. Also built on: `land_tenure`, `serfdom`, `slavery`, `labour_law` and `bondage` law kinds, households (47.8.21), markets and credit (6.4), state enterprise (50.4), abundance (44.17) and ideology (47.8.4).

**Current.** Markets run everywhere. Who owns land, tools and works, how output is allocated, how labour is bound and how product is shared are scattered across laws and are not read together as one order. No polity can collectivise, nationalise, privatise or reform land as one act.

**State.**

- **`economic_orders`.** Per polity, or per sector of a polity (a good kind or a service), on four axes:
  - `ownership` (`OwnershipRegime`): `household`, `kin_group`, `community`, `temple`, `ruler`, `state`, `private`, `cooperative`, `company`, `common`, `none`;
  - `allocation` (`AllocationMode`): `market`, `redistribution`, `command`, `obligation` (dues and services), `gift`, `need`, `abundance` (44.17);
  - `labour` (`LabourRegime`): `free`, `kin`, `corvee`, `serf`, `bound`, `enslaved`, `conscripted`, `cooperative`, `made` (constructs and made minds, F56, 44.6);
  - `distribution` (`DistributionRule`): `by_holding`, `by_office`, `by_need`, `by_work`, `by_share`, `equal`, `by_prestige`.
  - Also: `planning_capacity` (0–100, read from officials, records and information quality, F22), `since_epoch`, `locked`.
- **`economic_order_kinds`.** Authored named orders (F57): a name in the world's language, the four axis values and the institutions they need. The five systems of spec 13 are its built-in rows; a world may author any other combination.
- **`order_transitions`.** Polity, sector, from and to (each axis), `TransitionKind` (`collectivisation`, `nationalisation`, `privatisation`, `land_reform`, `enclosure`, `emancipation`, `decollectivisation`, `restoration_of_holdings`), stage, compensation (none, partial, full), resistance, start and end epochs.

**Behaviour.**

1. The order chooses which flows run each epoch. Market allocation runs prices and trade (6.4). Redistribution moves goods to central stores and out by office and need, where records and storage allow. Command allocates labour and output by plans, whose efficiency is `planning_capacity`. Obligation collects dues and services. Gift runs F38. Need and abundance divide by need. Each sector may run its own order.
2. Ownership sets who receives output and rents, who may sell land and works, and who bears losses. Labour sets wages, dues or keep, flight and grievance. Distribution sets each class's share of product, and so living standards and inequality.
3. Crises spread by order. A sacked centre stops redistribution. Information failure starves command (shortages and gluts by sector). Market crashes run through credit. A broken obligation chain stops a manorial economy.
4. Transitions run in stages. They move holdings (land, works, shares, livestock) between holders, with or without compensation, and are resisted by the losers by values (F5), arms (revolts, 47.3.6) and flight. Each transfer of each holding is a recorded change (F58.5).
5. Orders follow ideology, faith teaching, class power and the results of the order in place. Movements and parties carry demands for a new order (47.8.4). Agents propose transitions through their polities.

**Tools and control.**

- Mortal tool `set_economic_order` (`polity_id`, `sector`, `ownership`, `allocation`, `labour`, `distribution`, `reason`).
- Mortal tool `begin_transition` (`polity_id`, `sector`, `kind`, `compensation`, `reason`).
- Son tool `move_economic_order` (`polity_id`, `axis`, `value`, `reason`).
- God levers `economic_order:create/edit/delete/hold`, `economic_order_kind:*`, `order_transition:create/edit/delete/hold/advance`.
- An "Economic order" panel per polity with its four axes per sector, the transitions in course and the measured share of each class.
- Context block `economic_order`.

**Incidents.** `economy.order_set`, `economy.transition_begun`, `economy.transition_stage`, `economy.holding_transferred`, `economy.transition_resisted`, `economy.transition_done`, `economy.transition_failed`, `economy.centre_collapsed`, `economy.plan_shortfall`.

**Rules namespace.** `economic_orders`:

| Key | Default | Range |
|---|---|---|
| `economic_orders.redistribution_storage_loss_pct` | 10 | 0–100 |
| `economic_orders.command_efficiency_floor` | 30 | 0–100 |
| `economic_orders.planning_per_official` | 2 | 0–20 |
| `economic_orders.transition_stage_epochs` | 1 | 1–20 |
| `economic_orders.uncompensated_grievance` | 40 | 0–100 |
| `economic_orders.flight_per_grievance_pct` | 10 | 0–100 |
| `economic_orders.centre_collapse_spread_pct` | 60 | 0–100 |

**Codex and book.** A designed "Economic order" section in polity entries: the four axes per sector with labels, the named order, the shares of each class and every transition with its stages and transfers. A table of orders in the Records.

**Integrity.** Each sector is a good kind or service of the world; a transition's from-values equal the order in place when it began; holdings moved by a transition exist.

**Legacy.** Each polity gets an order from its laws: `serfdom` gives `serf` labour, `slavery` gives `enslaved` for the sectors that hold slaves, temple and palace stores give `redistribution`, guild charters and markets give `market`. Polities with nothing to read get `household` ownership with `market` allocation.

**Applies to.** Every polity, people and company in every era and every kind of world: bands that share game, temple economies, plantation colonies, command states, cooperatives of made minds and abundance worlds. The panel shows only on nodes that hold an order (polities and their sectors); peoples and companies read their polity's order.

**Couplings.** Markets, prices, credit, households and living standards, labour and bondage, class and estates, revolts, ideology, parties, state enterprise, abundance, treasury, famine relief.

### 51.2 The inner life of organisations

**Builds on.** Companies are built (`company_profiles`, `company_shares`, `engine/factions/companies.py`): charter by a polity, shares held by any node, dividends, guards, defaulted loans, collapse that wipes shareholders, conquest and dominions. 44.15 adds charters, holdings, enclaves, private forces, capture and sovereignty. 50.4 adds privatisation of state enterprises. Factions have ranks (`FactionRank`), goals and actions. 51.2 adds how an organisation of any kind is governed inside, and the company acts that are missing.

**Current.** An organisation acts as one will. No board, assembly or chapter decides; no executive answers to owners; members have no votes; leaders are not chosen by rule; no organisation splits from within, merges with another, buys another or researches. A failed company collapses at once, without creditors or proceedings.

**State.**

- **`org_governance`.** Per organisation (any faction kind, company, holy order, school, outlet, endowment, union, league): `decision_body` (`GoverningBody`: `founder`, `head`, `board`, `chapter`, `assembly_of_members`, `council_of_elders`, `shareholders_meeting`, `made_mind`, `none`), `head_selection` (`HeadSelection`: `appointed_by_owner`, `elected_by_body`, `elected_by_members`, `inherited`, `seniority`, `lot`, `divination`, `purchase`), term length, `vote_basis` (`one_member_one_vote`, `by_share`, `by_rank`, `by_seniority`), quorum, `strategy` (`OrgStrategy`: `grow`, `hold`, `specialise`, `diversify`, `expand_abroad`, `integrate_up`, `integrate_down`, `lobby`, `research`, `withdraw`).
- **`org_seats`.** Organisation, member, seat on the body, since, vote weight.
- **`org_cliques`.** Organisation, members, aim (a strategy, a head, a split, a merger), strength.
- **`org_mergers`.** Acquirer, target, `MergerKind` (`merger`, `friendly_acquisition`, `hostile_takeover`, `buyout`, `absorption_by_polity`), price, share offer, stage, outcome.
- **`org_research`.** Organisation, technique or design pursued (F24, made kinds), budget, staff, progress, secrecy.
- **`insolvency_cases`.** Debtor organisation, creditors with claims (links to `loans`), `InsolvencyPath` (`liquidation`, `restructuring`, `rescue_by_owner`, `rescue_by_polity`, `seizure_by_creditor`), court, stage, recovered share.

**Behaviour.**

1. The decision body sets strategy and approves big acts (wars of a company, mergers, dividends, research budgets) by its vote basis and quorum. The head carries out decisions and may act against them at a cost in trust; the body may remove the head.
2. Heads are chosen by the selection rule at term end, on death and on removal. Cliques gather votes; succession fights split the body.
3. Cliques that lose may leave and found a rival organisation (a split), taking members and assets by share. Holy orders, guilds and parties split the same way.
4. Mergers join members, assets and debts. Hostile takeovers buy shares on the market (51.6) or from holders, and the target's body may resist (poison terms, a friendly buyer, appeal to a polity). Polities may forbid mergers under competition law (51.3).
5. Research spends budget and staff for progress on a technique or design; success gives the organisation a secret technique until it spreads, is stolen (spies, 5.10) or is licensed.
6. An insolvent organisation goes to a court under its polity's debt law: creditors claim, assets are sold or restructured, and shareholders lose last. The existing collapse becomes the `liquidation` path.

**Tools and control.**

- Mortal tools:
  - `cast_org_vote` (`org_id`, `motion`, `vote`);
  - `seek_headship` (`org_id`);
  - `split_org` (`org_id`, `clique_id`, `name_reason`);
  - `bid_for_org` (`acquirer_id`, `target_id`, `kind`, `price`);
  - `fund_research` (`org_id`, `target_technique_or_design`, `budget`);
  - `file_insolvency` (`org_id`, `path`).
- Son tool `sway_org` (`org_id`, `strategy`, `reason`).
- God levers `org_governance:*`, `org_seat:*`, `org_clique:*`, `org_merger:create/edit/delete/hold/advance`, `org_research:*`, `insolvency_case:*`.
- A "Governance" section in every organisation drawer (body, head, seats, cliques, strategy, research, cases), and merger and insolvency pages.
- Context block `governance`.

**Incidents.** `org.head_chosen`, `org.head_removed`, `org.vote_held`, `org.strategy_changed`, `org.split`, `org.merged`, `org.takeover_bid`, `org.takeover_resisted`, `org.research_done`, `org.research_stolen`, `org.insolvent`, `org.liquidated`, `org.restructured`.

**Rules namespace.** `governance`:

| Key | Default | Range |
|---|---|---|
| `governance.head_defiance_trust_loss` | 15 | 0–100 |
| `governance.split_clique_threshold` | 35 | 0–100 |
| `governance.takeover_premium_pct` | 30 | 0–300 |
| `governance.research_progress_per_staff` | 2 | 0–50 |
| `governance.secret_spread_per_epoch_pct` | 10 | 0–100 |
| `governance.creditor_recovery_floor_pct` | 20 | 0–100 |
| `governance.term_epochs` | 2 | 1–50 |

**Codex and book.** Each organisation entry gains a designed "Governance" section: body, head and how chosen, seats, cliques, strategy, research, mergers and insolvency cases with their outcomes.

**Integrity.** Seats belong to members; vote weights sum to 100 per body; a merger's parties exist until its end; creditor claims point at real loans.

**Legacy.** Companies get a `shareholders_meeting` body with seats from `company_shares`; other factions get a `head` body with the leader as head and the selection rule their kind implies (holy orders `elected_by_body`, houses `inherited`). Existing collapses are recorded as `liquidation`.

**Applies to.** Every organisation of every kind and era: clans' councils, temple chapters, merchant leagues, chartered companies, unions, parties, made-mind collectives and interworld federations. The section renders in every faction, company and order drawer; nodes that are not organisations show it as not applicable with that reason.

**Couplings.** Companies, factions, holy orders, guilds, parties, credit and courts, espionage, techniques, competition (51.3), securities (51.6), labour (51.4), polities (capture, 44.15).

### 51.3 Market structure and competition

**Builds on.** Guild monopolies (faction goal `monopoly_on`, guild charter law with a monopoly), state monopolies (50.4), chartered monopolies abroad (spec 13 4.3 reference pass), cornering and dumping (spec 13 6.4 reference pass, built), and the keystone resource of a world (spec 13 6.4 reference pass 4). 51.3 measures each market's structure and adds collusion, price wars, barriers and competition law.

**Current.** A monopoly is a flag on a guild. How many sellers a market has, their shares, collusion between them, price wars and the law that limits them are not modelled.

**State.**

- **`market_structures`.** Per market and good kind: sellers with shares (derived each epoch from output), concentration (0–100), `StructureKind` (`many_sellers`, `few_sellers`, `one_seller`, `one_buyer`, `few_buyers`, derived), entry barriers by kind (`capital`, `licence`, `guild_right`, `secret_technique`, `route_control`, `network_control`, `divine_favour`) with strength.
- **`cartels`.** Members, good kinds and markets, aim (`price`, `quota`, `territory`, `bid_rigging`), agreed price or quota, secrecy, discipline.
- **`price_wars`.** Aggressor, targets, market, good kind, cut (percent), losses so far, outcome.
- **`competition_law`.** A `LawKind` value `competition_law` with typed clauses: `merger_review`, `cartel_ban`, `monopoly_break`, `price_cap`, `licence_limit`, each with a strength, and the office that enforces it.

**Behaviour.**

1. Prices rise with concentration and barriers, and with cartel discipline; buyers' power lowers them where buyers are few.
2. Cartels hold while discipline holds; members cheat when the gain passes discipline, and cheating breaks the cartel. Exposure under a cartel ban brings fines, trials and trust loss.
3. Price wars sell below cost to drive rivals out; the aggressor must outlast the targets on its purse and credit. Winners raise prices afterwards; losers go insolvent (51.2).
4. Barriers fall with the spread of techniques, new routes and changes of law; they rise with guild rights, licences and control of networks.
5. Competition law reviews mergers (51.2), breaks monopolies into new organisations and caps prices; capture of the enforcing office (44.15) weakens it.

**Tools and control.**

- Mortal tools `form_cartel` (`member_ids`, `goods_kind`, `market_id`, `aim`, `terms`), `start_price_war` (`market_id`, `goods_kind`, `cut`), `report_cartel` (`cartel_id`).
- Son tool `break_market` (`market_id`, `goods_kind`, `reason`).
- God levers `market_structure:edit/hold`, `cartel:*`, `price_war:*`, competition law through `law:*`.
- A "Market structure" section in market screens (sellers, shares, barriers, cartels, wars).
- Context block `market_structure`.

**Incidents.** `market.cartel_formed`, `market.cartel_broken`, `market.cartel_exposed`, `market.price_war_begun`, `market.price_war_won`, `market.monopoly_broken`, `market.barrier_fell`.

**Rules namespace.** `competition`:

| Key | Default | Range |
|---|---|---|
| `competition.price_per_concentration_pct` | 30 | 0–300 |
| `competition.cartel_discipline_decay` | 5 | 0–50 |
| `competition.cheat_gain_threshold` | 20 | 0–100 |
| `competition.price_war_floor_pct` | 50 | 0–100 |
| `competition.cartel_fine_pct` | 20 | 0–100 |
| `competition.barrier_decay_per_epoch` | 3 | 0–50 |

**Codex and book.** Market sections in settlement and economy chapters with structure, sellers and shares; cartels and price wars in the entries of their members.

**Integrity.** Shares in a market sum to 100; cartel members sell the good in that market; a price war's market exists.

**Legacy.** Market structures are derived from existing output on the first epoch; guild monopolies become `one_seller` markets with a `guild_right` barrier.

**Applies to.** Every market of every era and world, from a fair with three traders to an interworld exchange. Shown on markets and in organisation drawers that hold shares.

**Couplings.** Prices, guilds, companies, mergers, insolvency, law and courts, smuggling, trust, living standards.

### 51.4 Organised labour

**Builds on.** Strikes exist as a collective act (`CollectiveActKind.STRIKE`) and a faction action (`faction.strike`, triggered by unpaid wages); W32 makes a strike raise the salience of the profession identity; `labour_law` is a law kind; craft guilds exist; indenture and bondage cycles exist; 44.15 lists `cooperative` among company charters. 51.4 adds the organisations of workers and the bargaining between them and those who hire them.

**Current.** A strike is an outburst. No union holds members, dues and a fund; no contract sets wages and hours; no employer locks workers out; no worker cooperative owns its works.

**State.**

- **`worker_bodies`.** A faction kind `worker_body` with a `WorkerBodyForm` (`craft_union`, `industrial_union`, `general_union`, `journeyman_society`, `mutual_aid`, `worker_cooperative`, `made_mind_collective`), the trades and works it covers, members, dues, strike fund, standing in law (`banned`, `tolerated`, `recognised`, `compulsory`).
- **`labour_contracts`.** Hirer (a node), worker body or worker, terms: wage, hours, conditions (typed axes: safety, rest, keep), term, `ContractStatus` (`proposed`, `bargaining`, `agreed`, `broken`, `expired`).
- **`labour_disputes`.** Parties, demand, `DisputeAct` (`strike`, `go_slow`, `lockout`, `boycott`, `occupation_of_works`, `sabotage`), workers out, losses each side, mediator, outcome.

**Behaviour.**

1. Bargaining sets contract terms by each side's strength: the worker body's members, fund and solidarity against the hirer's reserves, substitutes (bound labour, made minds, constructs) and the law.
2. Disputes stop output in the works they cover. Each side loses each epoch; the fund pays strikers until it runs out. Lockouts are the hirer's own act. Strikebreakers, police and arms may be used; violence is recorded with its injuries (F58).
3. Law sets what is allowed: banned bodies act in secret and their members are prosecuted; recognised bodies bargain by right; compulsory bodies tie every worker of a trade.
4. Cooperatives own their works and share product by work (51.1 `by_work`); they compete in markets (51.3) and may fail like any organisation (51.2).
5. Wages and conditions enter living standards, class grievance and migration; won disputes spread to other trades by contact and media (50.2).

**Tools and control.**

- Mortal tools `found_worker_body` (`form`, `trades`, `settlement_id`), `bargain_contract` (`worker_body_id`, `hirer_id`, `demands`), `call_dispute` (`worker_body_id`, `act`, `demand`), `lock_out` (`hirer_id`, `worker_body_id`, `demand`).
- Son tool `stir_labour` (`settlement_id`, `trade`, `reason`).
- God levers `worker_body:*`, `labour_contract:*`, `labour_dispute:create/edit/delete/hold/end`.
- A "Labour" section in settlement and organisation drawers; a dispute page.
- Context block `labour`.

**Incidents.** `labour.body_founded`, `labour.body_banned`, `labour.contract_agreed`, `labour.contract_broken`, `labour.strike_begun`, `labour.lockout_begun`, `labour.dispute_ended`, `labour.strikebreakers_used`.

**Rules namespace.** `labour`:

| Key | Default | Range |
|---|---|---|
| `labour.fund_per_member` | 2 | 0–50 |
| `labour.strike_output_loss_pct` | 80 | 0–100 |
| `labour.lockout_cost_pct` | 30 | 0–100 |
| `labour.substitute_strength_pct` | 50 | 0–100 |
| `labour.spread_chance_pct` | 10 | 0–100 |
| `labour.banned_body_prosecution_pct` | 20 | 0–100 |

**Codex and book.** Worker bodies in settlement and organisation entries; contracts and disputes with their terms and outcomes in the Records.

**Integrity.** A contract's parties exist; a dispute's workers belong to the body or the works; fund never negative.

**Legacy.** Craft guilds that struck become `journeyman_society` bodies where their members are not masters; existing strikes become disputes with act `strike` and their recorded end.

**Applies to.** Every era and world with hired or bound work: temple workers who stop work, guild journeymen, factory unions, ship crews, made-mind collectives. Shown in settlements and organisation drawers.

**Couplings.** Wages, living standards, production, class and identity salience (W32), law and police, cooperatives, economic orders (51.1), media, revolts.

### 51.5 Monetary authorities

**Builds on.** Money supply, reserves and coin trust are rules (`finance`: `supply_pct`, `supply_per_1000`, `reserve_per_1000`, `reserve_trust`); minting (`engine/economy/money.py`), debasement and forgery (48.5), credit with ratings, interest and bankruptcy states (spec 13 6.4 reference pass, built), and realm credit. 51.5 adds the authority that sets these on purpose.

**Current.** Interest and coin trust follow from supply and reserves; no institution chooses them.

**State.**

- **`monetary_authorities`.** Issuer of a currency (`currencies`): holder (ruler, treasury office, temple, bank, company, council of polities 51.7), `independence` (0–100), mandate (`MonetaryAim`: `stable_value`, `cheap_credit`, `fund_the_state`, `peg`, `growth`, `none`), policy rate, reserve requirement on banks, peg target (another currency or a good), lender of last resort (yes or no).

**Behaviour.**

1. The policy rate sets lenders' base interest; lower rates raise borrowing and prices, higher rates the reverse, each with a lag of an epoch.
2. Issuing to fund the state raises supply and lowers trust and the exchange rate (50.3, W35); a peg holds while reserves last, then breaks with a rate shock.
3. As lender of last resort the authority saves failing banks at the cost of supply and moral hazard; without it bank runs spread.
4. Low independence lets rulers bend policy before wars and elections; high independence resists them at a cost in favour.

**Tools and control.**

- Mortal tool `set_monetary_policy` (`authority_id`, `rate`, `aim`, `peg_target`).
- Mortal tool `found_monetary_authority` (`currency_id`, `holder_id`, `independence`, `aim`).
- Son tool `shake_coin` (`currency_id`, `trust_change`, `reason`).
- God levers `monetary_authority:create/edit/delete/hold`.
- A "Money" section in polity and currency drawers.
- Context block `money_policy`.

**Incidents.** `money.rate_set`, `money.peg_held`, `money.peg_broken`, `money.bank_rescued`, `money.bank_run`, `money.printed_for_state`.

**Rules namespace.** `monetary`:

| Key | Default | Range |
|---|---|---|
| `monetary.rate_to_interest_pct` | 100 | 0–300 |
| `monetary.price_per_rate_point_pct` | 2 | 0–20 |
| `monetary.state_issue_trust_loss` | 5 | 0–50 |
| `monetary.peg_reserve_floor_pct` | 20 | 0–100 |
| `monetary.run_spread_pct` | 30 | 0–100 |

**Codex and book.** Authorities and their policies in polity and currency entries; rate history in the economy chapter.

**Integrity.** An authority issues an existing currency; a peg target is another currency or a good kind.

**Legacy.** Each currency's issuer becomes its authority with `fund_the_state` where the treasury debased it, else `stable_value`; independence 0 for rulers.

**Applies to.** Every world with money, from temple grain receipts to interworld credit; worlds without money show the section as idle with that reason.

**Couplings.** Credit, prices, exchange rates, banks, treasury, wars, elections, trust, securities.

### 51.6 Securities and exchanges

**Builds on.** `company_shares` held by nodes, `speculations` (hoarding and busts), loans and realm credit, insurance policies. 51.6 adds places where shares and debts are traded at a price, and the booms and crashes of those prices.

**Current.** Shares change hands only by lever or founding; polity debt is a loan; no price moves with belief.

**State.**

- **`exchanges`.** Settlement or network (F51), owner (polity, guild, company), rules (listing, margin), members (brokers).
- **`securities`.** Issuer (company, polity, settlement, endowment 50.10), `SecurityKind` (`share`, `bond`, `annuity`, `note`, `future`), face value, coupon, maturity, listed exchange.
- **`security_holdings`.** Holder node, security, amount, bought price.
- **`security_prices`.** Security, epoch, price, volume.

**Behaviour.**

1. Prices move by holders' beliefs (F22) of the issuer's results and risk, by rates (51.5) and by herding: rising prices draw buyers. Belief that runs ahead of results forms a bubble.
2. A shock (a default, a lost war, a failed voyage, exposure of fraud) turns herding down; prices crash, margin calls force sales, and holders on credit go bankrupt, spreading to banks.
3. Polities issue bonds to fund wars and works (50.4); defaults (the existing `default` credit state) crash their bonds and raise future rates.
4. Takeovers buy shares on the exchange (51.2); insider knowledge (secrets, F20) gives gains and is a crime where the law says so.

**Tools and control.**

- Mortal tools `list_security` (`issuer_id`, `kind`, `amount`, `exchange_id`), `trade_security` (`security_id`, `amount`, `side`).
- Son tool `stir_market_mood` (`exchange_id`, `direction`, `reason`).
- God levers `exchange:*`, `security:*`, `security_holding:*`, `security_price:edit`.
- An exchange drawer page with prices and charts; holdings in holder drawers.
- Context block `securities`.

**Incidents.** `securities.listed`, `securities.bubble_formed`, `securities.crash`, `securities.bond_defaulted`, `securities.insider_exposed`.

**Rules namespace.** `securities`:

| Key | Default | Range |
|---|---|---|
| `securities.herding_pct` | 20 | 0–100 |
| `securities.bubble_threshold_pct` | 50 | 0–500 |
| `securities.crash_drop_pct` | 40 | 0–100 |
| `securities.margin_call_pct` | 30 | 0–100 |
| `securities.default_rate_rise` | 5 | 0–50 |

**Codex and book.** Exchanges in settlement entries; securities in issuers' entries; holdings in holders' entries; a prices table in the economy chapter.

**Integrity.** Holdings of a security never exceed its amount; issuers exist; prices are per existing security.

**Legacy.** Each company's shares become a `share` security of its amount; polity loans to lenders become `bond` securities.

**Applies to.** Every world with tradeable claims; worlds without them show the section idle with that reason.

**Couplings.** Companies, takeovers, credit, banks, rates, treasury, wars, works, secrets and law.

### 51.7 Organisations of polities

**Builds on.** Treaties with kinds (`TreatyKind`: alliances, coalition, guarantee, naval limit, interworld and others) and clauses; the `interworld_federation` faction kind; the `federation` government; summits as a gathering kind (F25); the council of gods (47.5.5). 51.7 adds standing bodies whose members are polities.

**Current.** Polities bind by treaties between parties. No standing league, bloc or court has members, a charter, a seat, dues, organs and decisions that bind members.

**State.**

- **`polity_leagues`.** A new entity type `league` (a node, 51.28) with: charter (aims typed by `LeagueAim`: `defence`, `trade`, `customs_union`, `currency_union`, `law`, `faith`, `peace`, `research`, `migration`), seat, dues rule, `vote_basis` (`one_member_one_vote`, `by_population`, `by_dues`, `by_veto_holders`), organs (assembly, council, court, secretariat, force), founding epoch.
- **`league_members`.** League, polity, standing (`founder`, `member`, `observer`, `suspended`, `expelled`), dues paid, veto.
- **`league_decisions`.** League, organ, `LeagueDecisionKind` (`admit`, `expel`, `sanction`, `common_tariff`, `common_force`, `ruling`, `budget`, `mediation`), subject, votes, outcome.

**Behaviour.**

1. Members pay dues and gain the charter's goods: shared defence (an attack on one calls the others), a customs union (common tariffs, free trade inside), a currency union (one monetary authority, 51.5), a court whose rulings bind members on law and borders.
2. Decisions follow the vote basis; vetoes block. Members obey by their interest and the league's strength; defiance brings sanctions and expulsion.
3. Leagues grow by admission and break by exits, war between members and collapse of their leaders. A strong league may become a federation (polity formation reads league depth).
4. Interworld leagues use networks and journeys between worlds (F51, 51.17) for their organs.

**Tools and control.**

- Mortal tools `found_league` (`polity_ids`, `aims`, `vote_basis`), `join_league` (`league_id`, `polity_id`), `table_league_motion` (`league_id`, `organ`, `kind`, `subject_id`).
- Son tool `bind_league` (`league_id`, `strength_change`, `reason`).
- God levers `polity_league:*`, `league_member:*`, `league_decision:*`.
- A league drawer page (charter, members, organs, decisions), leagues on the atlas as a layer.
- Context block `leagues`.

**Incidents.** `league.founded`, `league.joined`, `league.left`, `league.expelled`, `league.sanction`, `league.ruling`, `league.dissolved`, `league.federated`.

**Rules namespace.** `leagues`:

| Key | Default | Range |
|---|---|---|
| `leagues.dues_pct` | 3 | 0–50 |
| `leagues.obedience_base_pct` | 60 | 0–100 |
| `leagues.sanction_trade_cut_pct` | 50 | 0–100 |
| `leagues.federate_depth_threshold` | 80 | 0–100 |
| `leagues.court_binding_pct` | 50 | 0–100 |

**Codex and book.** League entries with charter, members, organs and every decision; membership in polity entries.

**Integrity.** Members are polities; a currency union names one authority; decisions name existing organs.

**Legacy.** Coalitions and interworld federations with three or more parties become leagues; their treaties stay as the founding charter.

**Applies to.** Every world with more than one polity, in every era: leagues of city-states, tribal confederacies, faith councils of kings, customs unions, interworld federations. The league is an entity type, so it is a node and renders `ThingSections` like every other.

**Couplings.** Treaties, war, trade, tariffs, money, courts and borders, migration, federation, interworld travel.

### 51.8 City rules, municipal services and merging settlements

**Builds on.** Spec 13 4.2 reference pass 3, built: districts by kind (`DistrictKind` with `suburb` and `slums`), desirability and land value, service coverage, housing evolution, slum clearance as a mandate, `firehouse` structures, urban morphology (organic, planned, concentric), turf; the city plan rules (`city_plan`); 50.4 adds sewers, aqueducts and drainage as works. 51.8 adds the rules a settlement makes for its own land, the services not yet modelled, and settlements that grow together.

**Current.** Districts form where needs and growth put them. No settlement rules which uses may stand where or how buildings must be made; refuse and lighting are not services; two settlements that grow into each other stay two.

**State.**

- **`land_use_rules`.** Settlement, district or ring, `LandUseRule` (`allowed_uses` of district kinds, `banned_uses`, `height_limit`, `density_limit`, `build_material` requirement, `fire_spacing`, `frontage_rule`, `green_share`), maker (council, ruler, guild, faith), strength, enforcement.
- **`municipal_services`.** Settlement, `MunicipalService` (`refuse`, `lighting`, `water_distribution`, `street_cleaning`, `night_watch`, `burial_ground`, `market_inspection`), provider (settlement, guild, company, endowment, made minds), coverage by district, cost, quality.
- **`conurbations`.** Member settlements, core, joined epoch, governance (`one_council`, `federated_councils`, `ruled_by_core`).

**Behaviour.**

1. Land use rules shape which districts may grow where, lower fire spread (spacing, materials) and nuisance next to homes, and raise building costs. Evasion grows with weak enforcement and high land value.
2. Services act through coverage: refuse lowers disease and vermin; lighting lowers night crime and lengthens trade and leisure; water distribution lowers thirst and disease; inspection lowers fraud in markets. Uncovered districts suffer each.
3. Settlements whose districts touch and whose ties pass a threshold join into a conurbation. Members keep their names as quarters; governance follows the rule chosen; the core's laws spread. A conurbation may split again under conflict.
4. Planned rebuilds (after fire, war or a founding plan) apply land use rules at once and change morphology to `planned`.

**Tools and control.**

- Mortal tools `set_land_use_rule` (`settlement_id`, `district_or_ring`, `rule`, `values`), `provide_service` (`settlement_id`, `service`, `provider_id`, `budget`), `join_settlements` (`settlement_ids`, `governance`).
- Son tool `bless_city` (`settlement_id`, `service_or_rule`, `reason`).
- God levers `land_use_rule:*`, `municipal_service:*`, `conurbation:create/edit/delete/hold/split`.
- "City rules" and "Services" sections in the settlement drawer; conurbations on the atlas and in the city scene.
- Context block `city_rules`.

**Incidents.** `city.rule_set`, `city.rule_evaded`, `city.service_founded`, `city.service_failed`, `city.settlements_joined`, `city.conurbation_split`, `city.planned_rebuild`.

**Rules namespace.** `city_rules`:

| Key | Default | Range |
|---|---|---|
| `city_rules.fire_spread_cut_pct` | 30 | 0–100 |
| `city_rules.build_cost_rise_pct` | 15 | 0–200 |
| `city_rules.refuse_disease_cut_pct` | 20 | 0–100 |
| `city_rules.lighting_crime_cut_pct` | 15 | 0–100 |
| `city_rules.join_tie_threshold` | 70 | 0–100 |
| `city_rules.evasion_per_land_value_pct` | 10 | 0–100 |

**Codex and book.** City rules and services in settlement entries; conurbations with their members and history.

**Integrity.** Rules name districts or rings of their settlement; a conurbation's members are distinct settlements of one world.

**Legacy.** Settlements with `planned` morphology get the land use rules their plan implies; existing wells, watch posts and burial grounds become services of those kinds.

**Applies to.** Every settlement of every size and era, every world, every biology that builds dwellings; settlements without dwellings show the sections idle with that reason.

**Couplings.** Districts, fire, disease, crime, land value, housing, works, law, migration, polity control.

### 51.9 Protected nature

**Builds on.** Game reserves and poaching (`game_reserves`, `engine/agrarian/lands.py`), commons and enclosure (`commons`), closed seasons and protected waters (built in `engine/agrarian/lands.py` and mandates), `environment_law`, rewilding of empty land (`environment.rewild_rate`), extinction and invasive species (ecology, worldlife), sacred groves (genius loci). 51.9 adds protection of land, waters and species for their own sake, by law, faith or a movement.

**Current.** Protection exists only as hunting rights for elites and catch closures. No polity, faith or movement protects a species, a landscape or a whole ecosystem; reintroduction of a lost species does not happen.

**State.**

- **`protected_areas`.** Region or site, protector (polity, faith, community, company, son), `ProtectionBasis` (`law`, `faith`, `custom`, `charter`, `divine_decree`), protected uses banned (`ProtectedUse`: `hunting`, `logging`, `farming`, `mining`, `settlement`, `entry`, `fishing`, `building`), wardens, strength.
- **`species_protections`.** Species, holder, basis, measures (`hunting_ban`, `trade_ban`, `breeding_programme`, `reintroduction`, `habitat_guard`), since.
- **`conservation_movements`.** A movement (W20) with aims typed by these measures, support share per cohort.

**Behaviour.**

1. Protected areas lower the banned uses by strength and wardens; ecology recovers there (species counts, forest, soil). Poaching and illegal use rise with scarcity and price.
2. Species protection lowers kills and trade; breeding and reintroduction restore a species to regions it left, where habitat allows (living lines of W46 where the world has them).
3. Movements grow from loss (extinctions, ruined land, famine after overuse), faith teaching and knowledge (50.7); they push laws and are opposed by those who use the land.
4. Protection costs livelihoods; the displaced lose income and may resist.

**Tools and control.**

- Mortal tools `protect_area` (`region_or_site_id`, `basis`, `banned_uses`), `protect_species` (`species_id`, `measures`), `reintroduce` (`species_id`, `region_id`).
- Son tool `hallow_wild` (`region_id`, `reason`).
- God levers `protected_area:*`, `species_protection:*`, movements through existing levers.
- Protected areas on the atlas; a "Protection" section in region and species drawers.
- Context block `protected_nature`.

**Incidents.** `nature.area_protected`, `nature.protection_lifted`, `nature.poached`, `nature.species_protected`, `nature.species_reintroduced`, `nature.species_recovered`.

**Rules namespace.** `protected_nature`:

| Key | Default | Range |
|---|---|---|
| `protected_nature.use_cut_per_strength_pct` | 80 | 0–100 |
| `protected_nature.recovery_per_epoch` | 3 | 0–50 |
| `protected_nature.poaching_per_price_pct` | 10 | 0–100 |
| `protected_nature.reintroduction_success_pct` | 40 | 0–100 |
| `protected_nature.displacement_grievance` | 20 | 0–100 |

**Codex and book.** Protected areas in region entries; protections in species entries; movements in their own entries.

**Integrity.** Areas lie in existing regions; reintroduction targets regions whose habitat the species can hold.

**Legacy.** Game reserves become protected areas with basis `law` and banned use `hunting`; sacred groves become areas with basis `faith`.

**Applies to.** Every world with life, in every era: sacred lands of a band, royal forests, park systems, protected moons. Region and species drawers; worlds without life show the section idle with that reason.

**Couplings.** Ecology, extinction, poaching and crime, livelihoods, faith, law, movements, living craft.

### 51.10 Leaving office

**Builds on.** Succession rules, offices (`offices`), regency, term ends in elections (`engine/polity/elections.py`), pensions (`veteran_pension`), and a step-down forced by leverage (`HookDemand.STEP_DOWN`). 51.10 adds leaving office by one's own choice.

**Current.** Office holders leave by death, removal, coups, elections or blackmail. No ruler abdicates, no official retires, and no holder chooses an heir by stepping aside.

**State.**

- **`departures`.** Office holder, office, `DepartureKind` (`abdication`, `retirement`, `resignation`, `withdrawal_to_religion`, `exile_by_choice`), in favour of (a node or the succession rule), conditions (keep title, keep lands, pension, safe conduct), epoch, the departed holder's later standing.

**Behaviour.**

1. Holders weigh leaving by age, health, failure, scandal, faith teaching, pressure and a chosen heir's readiness (mind, F5–F8).
2. An abdication hands office by the conditions; the departed keeps influence by standing and may return, plot or be a rallying point.
3. Retirement from lesser offices frees posts and pays pensions where the law gives them; customs may require retirement at an age or after a term.
4. Resignation under scandal ends some pressures (unrest, a faction's hostility) and keeps others (trials).

**Tools and control.**

- Mortal tool `leave_office` (`office_id`, `kind`, `in_favour_of_id`, `conditions`).
- Mortal tool `return_to_office` (`departure_id`).
- Son tool `call_to_step_aside` (`holder_id`, `reason`).
- God levers `departure:create/edit/delete/hold`.
- Departures in office and holder drawers.
- Context block `offices` gains departures.

**Incidents.** `office.abdicated`, `office.retired`, `office.resigned`, `office.withdrew`, `office.returned`.

**Rules namespace.** `departures`:

| Key | Default | Range |
|---|---|---|
| `departures.age_weight` | 30 | 0–100 |
| `departures.scandal_weight` | 40 | 0–100 |
| `departures.return_chance_pct` | 5 | 0–100 |
| `departures.retirement_age_share_pct` | 80 | 0–100 |

**Codex and book.** Departures in holder and office entries.

**Integrity.** The departed held the office at the epoch; the successor exists.

**Legacy.** Step-downs forced by leverage become `resignation` departures.

**Applies to.** Every office of every polity, faith, organisation and league, and every node that holds office: mortals, made minds and gods who rule peoples. Offices of sons over domains follow divine rules (47.5) and are shown as not applicable with that reason.

**Couplings.** Succession, offices, regency, factions, scandal, faith, pensions, plots.

### 51.11 Referendums

**Builds on.** Elections (`elections`), the `franchise` law, `assembly` decision rule, parties and movements, public opinion (F21). 51.11 adds votes of the people on a question rather than a person.

**Current.** The people choose persons; questions are decided by rulers, councils and assemblies.

**State.**

- **`referendums`.** Polity, settlement or league, question typed by subject (`law`, `constitution`, `independence`, `union`, `treaty`, `war`, `transition` of 51.1, `recall` of an office holder, `faith`), the franchise used, `binding` (yes or no), threshold, campaign sides with their spending, turnout, result.

**Behaviour.**

1. Called by those whose law allows it (ruler, assembly, a petition reaching a threshold, a league charter).
2. Campaigns move opinion by media (50.2), speeches (50.13), money and fraud; turnout follows salience and access.
3. Binding results change the law or state at once; others pressure rulers, who pay in legitimacy if they ignore them. Fraud found out discredits the result.

**Tools and control.**

- Mortal tools `call_referendum` (`polity_id`, `subject`, `question_target_id`, `binding`), `campaign_for_vote` (`referendum_id`, `side`, `means`).
- Son tool `sway_vote` (`referendum_id`, `side`, `reason`).
- God levers `referendum:create/edit/delete/hold/decide`.
- Referendum pages; a "Votes" list in polity drawers.
- Context block `votes`.

**Incidents.** `vote.called`, `vote.held`, `vote.result`, `vote.ignored`, `vote.fraud_exposed`.

**Rules namespace.** `referendums`:

| Key | Default | Range |
|---|---|---|
| `referendums.petition_threshold_pct` | 10 | 0–100 |
| `referendums.ignore_legitimacy_loss` | 20 | 0–100 |
| `referendums.campaign_shift_pct` | 10 | 0–100 |
| `referendums.fraud_detect_pct` | 20 | 0–100 |

**Codex and book.** Referendums with question, sides, turnout and result in polity entries.

**Integrity.** The franchise matches the polity's law; the subject exists.

**Legacy.** None; referendums start empty.

**Applies to.** Every polity, settlement and league where some body votes, in every era and world; polities without any franchise show the list idle with that reason.

**Couplings.** Law, independence, treaties, elections, opinion, media, legitimacy.

### 51.12 Reckoning after a fallen regime

**Builds on.** Purges as an event collection kind, pardons (`engine/law/pardons.py`), appeals, outlawry, reparations as a peace clause, damnatio memoriae (F33), trials (47.3.3), war crimes as a crime kind where 47.3.1 lists them. 51.12 adds the reckoning a new order makes with the servants of the old one.

**Current.** A new ruler or regime takes power and the old regime's servants keep their posts, or are killed in purges. No trials of the old regime, no truth seeking, no bars from office, no amnesty for confession, no repair to victims.

**State.**

- **`reckonings`.** Polity, the fallen regime (a ruler, a government kind, an occupation, 51.15).
- **`reckoning_measures`.** Child rows of a reckoning, one per `ReckoningMeasure`: `tribunal`, `truth_inquiry`, `office_bar`, `amnesty`, `amnesty_for_confession`, `restitution`, `reparation_to_victims`, `memorial`, `record_opening` (opening the old regime's archives); each with scope, strength, stage.
- **`reckoning_cases`.** Reckoning, the accused or the inquired, acts named (recorded incidents, F58), measure, outcome.

**Behaviour.**

1. A new regime chooses measures by its values, its strength, the old regime's remaining power and the victims' pressure.
2. Tribunals try acts drawn from the record; verdicts punish, acquit or pardon. Truth inquiries open accounts that historiography reads (F33). Office bars empty posts and lower administration while they last.
3. Amnesty lowers resistance and grievance among the old servants and raises it among victims; restitution returns holdings (51.1) and costs the treasury.
4. Measures that are too weak keep old servants in power; too harsh ones drive them to revolt or flight.

**Tools and control.**

- Mortal tools `open_reckoning` (`polity_id`, `fallen_regime_id`, `measures`), `try_servant` (`reckoning_id`, `accused_id`, `incident_ids`).
- Son tool `weigh_reckoning` (`reckoning_id`, `measure`, `reason`).
- God levers `reckoning:*`, `reckoning_measure:*`, `reckoning_case:*`.
- A reckoning page linked from the polity drawer.
- Context block `reckoning`.

**Incidents.** `reckoning.opened`, `reckoning.trial`, `reckoning.verdict`, `reckoning.amnesty`, `reckoning.inquiry_report`, `reckoning.restitution`, `reckoning.closed`.

**Rules namespace.** `reckoning`:

| Key | Default | Range |
|---|---|---|
| `reckoning.office_bar_admin_loss_pct` | 20 | 0–100 |
| `reckoning.amnesty_grievance_shift` | 15 | 0–100 |
| `reckoning.restitution_cost_pct` | 30 | 0–100 |
| `reckoning.harsh_revolt_chance_pct` | 10 | 0–100 |

**Codex and book.** Reckonings with measures, cases and outcomes in polity entries; accounts from inquiries in historiography.

**Integrity.** Cases name recorded incidents; the fallen regime is earlier than the reckoning.

**Legacy.** Recorded purges after coups become reckonings with measure `tribunal` and their victims as cases.

**Applies to.** Every polity, faith and organisation that changes rule, in every era and world.

**Couplings.** Trials, pardons, historiography, holdings, office, revolts, occupation, memory.

### 51.13 Cults of living leaders

**Builds on.** Prestige and renown, standing, apotheosis after death (`storyteller/arcs.py`), god-kings (`god_kingdom` government), media (50.2), speeches (50.13), monuments and depictions (spec 13 7.4 reference pass). 51.13 adds the organised veneration of a living, mortal leader by those under them.

**Current.** A leader's renown grows by deeds; worship of a leader exists only for god-kings and after death.

**State.**

- **`leader_cults`.** Leader (a mortal or made mind; never a son, foreign god or the Creator, who are worshipped through faith), promoters (offices, outlets, a party), instruments (`CultInstrument`: `images_in_public`, `official_biography`, `holidays`, `oaths_of_loyalty`, `naming_of_places`, `teaching_in_schools`, `staged_gatherings`, `ban_on_criticism`), intensity (0–100), sincerity of the public (derived).

**Behaviour.**

1. Instruments raise the leader's legitimacy and obedience and lower open dissent, at a cost in treasury and in the public's sincerity, which falls when the cult runs ahead of results.
2. Criticism under a ban is prosecuted; satire (W32) is its pressure valve.
3. On the leader's death the cult passes to an heir, fades, turns into faith (apotheosis) or is torn down (51.12 memorials, damnatio).

**Tools and control.**

- Mortal tools `promote_cult` (`leader_id`, `instruments`), `tear_down_cult` (`cult_id`).
- Son tool `sway_cult` (`cult_id`, `intensity_change`, `reason`).
- God levers `leader_cult:create/edit/delete/hold`.
- A "Cult" block in the leader's drawer.
- Context block `leader_cult`.

**Incidents.** `cult.begun`, `cult.instrument_added`, `cult.critic_punished`, `cult.passed_on`, `cult.torn_down`, `cult.became_faith`.

**Rules namespace.** `leader_cults`:

| Key | Default | Range |
|---|---|---|
| `leader_cults.legitimacy_per_intensity_pct` | 20 | 0–100 |
| `leader_cults.sincerity_decay` | 5 | 0–50 |
| `leader_cults.cost_per_instrument` | 3 | 0–50 |
| `leader_cults.apotheosis_chance_pct` | 5 | 0–100 |

**Codex and book.** The cult in the leader's entry with its instruments and fate.

**Integrity.** The leader is mortal or a made mind; promoters exist.

**Legacy.** None; cults start empty.

**Applies to.** Every polity, faith, party and organisation in every era and world. The block shows on mortals and made minds; gods are worshipped through faith and show it as not applicable with that reason.

**Couplings.** Legitimacy, dissent, censorship, satire, media, faith, succession, memory.

### 51.14 Restoration of fallen polities

**Builds on.** Dormant titles from fallen polities (`engine/polity/titles.py`), pretenders and their hosts (`engine/polity/offices.py`), claims (`claims`), irredentist accounts (W20 `accounts`), revolts and independence (47.3.6). 51.14 adds movements that raise a fallen polity again under its old name and rights.

**Current.** A fallen polity leaves a dormant title; a claimant may press it inside another polity. No polity is founded again as the old one with its laws, symbols and claims.

**State.**

- **`restorations`.** Fallen polity (kept as a dead node), movement or claimant, territories sought, legitimacy sources (`RestorationBasis`: `bloodline`, `faith`, `law`, `memory`, `foreign_backing`), stage (`memory`, `movement`, `rising`, `restored`, `failed`), restored polity (when founded).

**Behaviour.**

1. Memory of a fallen polity lives in accounts, emblems and dormant titles; grievance under its successors turns memory into a movement.
2. A rising founds a polity that takes the old name, emblems, laws and claims; continuity with the old polity is a link in the book and in claims.
3. Restorations meet the successors' resistance and the gap between memory and the present (old laws that no longer fit lower stability).

**Tools and control.**

- Mortal tools `raise_restoration` (`fallen_polity_id`, `basis`, `territory_ids`), `restore_polity` (`restoration_id`).
- Son tool `stir_memory` (`fallen_polity_id`, `reason`).
- God levers `restoration:create/edit/delete/hold/advance`.
- Restorations on the dead polity's page and the new polity's drawer.
- Context block `restoration`.

**Incidents.** `polity.restoration_begun`, `polity.restoration_rising`, `polity.restored`, `polity.restoration_failed`.

**Rules namespace.** `restoration`:

| Key | Default | Range |
|---|---|---|
| `restoration.memory_decay_per_epoch` | 3 | 0–50 |
| `restoration.movement_grievance_threshold` | 50 | 0–100 |
| `restoration.old_law_stability_loss` | 10 | 0–100 |

**Codex and book.** Restorations in the entries of the fallen and the restored polity, linked as one line.

**Integrity.** The fallen polity is dead; the restored polity names it as predecessor.

**Legacy.** Pretenders who press a dormant title gain a restoration at stage `movement`.

**Applies to.** Every polity, faith and organisation that can fall, in every era and world.

**Couplings.** Titles, claims, accounts, revolts, independence, legitimacy, emblems.

### 51.15 Occupation regimes

**Builds on.** Occupations (`occupations`, `engine/military/occupation.py`): occupying after a march, resistance, partisans, occupation tax, the end of occupations, the `occupation` government kind. Defections and reprisals against defectors (`defections`, `engine/military/spy_depth.py`). 51.15 adds how an occupier governs, who serves it, how it answers resistance, and what follows liberation (51.12).

**Current.** An occupied place pays tax and breeds partisans. No administration, no collaborators, no reprisals against the population, no hostages, no settlement of the occupier's people, no liberation reckoning.

**State.**

- **`occupation_regimes`.** Occupation, `OccupationRule` (`military`, `civil_by_occupier`, `local_puppet`, `annexation`, `protectorate`), administrators, laws imposed, extraction (tax, levies, labour, goods), settlement of occupiers' people (count).
- **`collaborations`.** Collaborator node (mortal, faction, polity), occupation, `CollaborationKind` (`administration`, `police`, `informing`, `trade`, `militia`, `propaganda`), reward, exposure.
- **`occupation_measures`.** Occupation, `OccupationMeasure` (`curfew`, `hostages`, `collective_punishment`, `deportation`, `requisition`, `ban_on_gathering`, `amnesty_offer`), strength, epoch.

**Behaviour.**

1. Rule kind sets extraction, order and the locals' grievance; collaborators lower the cost of rule and raise its intelligence on partisans.
2. Measures answer resistance: they lower partisan activity now and raise grievance and recruitment later; atrocities are recorded and feed reckonings.
3. Collaborators gain rewards and are hated; exposure brings partisan killings; liberation brings reckoning (51.12).
4. Annexation and settlement change demography and claims; restoration movements (51.14) may follow.

**Tools and control.**

- Mortal tools `set_occupation_rule` (`occupation_id`, `rule`), `collaborate` (`occupation_id`, `kind`), `impose_measure` (`occupation_id`, `measure`, `strength`), `expose_collaborator` (`collaboration_id`).
- Son tool `sway_occupation` (`occupation_id`, `rule_or_measure`, `reason`).
- God levers `occupation_regime:*`, `collaboration:*`, `occupation_measure:*`.
- An "Occupation" section in occupied settlements, regions and occupier polities.
- Context block `occupation`.

**Incidents.** `occupation.rule_set`, `occupation.collaborator_joined`, `occupation.collaborator_killed`, `occupation.measure_imposed`, `occupation.deportation`, `occupation.annexed`, `occupation.liberated`.

**Rules namespace.** `occupation`:

| Key | Default | Range |
|---|---|---|
| `occupation.collaborator_cost_cut_pct` | 20 | 0–100 |
| `occupation.measure_partisan_cut_pct` | 30 | 0–100 |
| `occupation.measure_grievance` | 20 | 0–100 |
| `occupation.exposure_kill_pct` | 15 | 0–100 |
| `occupation.extraction_cap_pct` | 50 | 0–100 |

**Codex and book.** The regime, collaborators and measures in the occupied place's and the occupier's entries.

**Integrity.** A regime belongs to an open occupation; collaborators are of the occupied place or its neighbours.

**Legacy.** Each open occupation gets a `military` regime with its existing tax as extraction.

**Applies to.** Every occupation in every era and world, including occupation across worlds (51.17).

**Couplings.** War, partisans, grievance, intelligence, demography, claims, reckoning, restoration.

### 51.16 Weapons of mass harm, deterrence and the remnants of war

**Builds on.** The doom clock and cosmic ends (0.8 rule 5), designed disease (46.11), self-making machines (44.16), unit kinds and tactics including orbital bombardment and drop troops (`catalog/units.py`, `catalog/battle_depth.py`), pollution (F24), arms limits (`TreatyKind.NAVAL_LIMIT`), demilitarised zones as a peace clause (`engine/polity/treaties.py`, `engine/military/peace.py`), `weapons_law`. 51.16 adds weapons whose harm reaches a whole place or people, the deterrence they create, and what war leaves in the land.

**Current.** Battles harm armies and sieges harm towns. No weapon threatens a whole region, no polity is held back by fear of one, and nothing a war leaves behind (buried charges, poisoned ground, wrecks in orbit) harms after the peace.

**State.**

- **`mass_weapons`.** Holder, `MassHarm` (`blast`, `fire`, `poison`, `disease`, `radiation`, `swarm`, `field` (powers, W45), `rite` (8.6), `divine_relic`), reach (settlement, region, world), count, readiness, delivery (units or carriers able to bring it), the technique and materials it needs (F24, F23), visible stage of the programme (0.8 rule 3).
- **`deterrence_postures`.** Holder, toward whom, `Posture` (`none`, `declared`, `ambiguous`, `first_use`, `retaliation_only`, `shared_with_league`), credibility (0–100).
- **`war_remnants`.** Region or orbit, `RemnantKind` (`buried_charges`, `poisoned_ground`, `fallout`, `wreck_field`, `unquiet_dead` (where the world's laws let the dead rise), `cursed_ground`, `abandoned_machines`), density, decay rate, origin war, clearance progress.

**Behaviour.**

1. Mass weapons pass through visible programme stages; rivals see them by spies and rumours and may strike, ally or build their own.
2. A credible posture lowers the chance that a rival attacks the holder's core, raises the cost of escalation and draws arms races. Credibility falls with bluffs exposed and rises with tests.
3. Use is an incident of its harm kind over its reach, through the systems it touches (body, disease, ecology, structures), recorded per victim group (F58), and adds to the doom clock by reach. World-ending effects stay with doom mechanics (0.8 rule 5).
4. Remnants harm those who live, farm, travel or sail through them by density (47.10 mishaps), lower land value and yields, and decay or are cleared by work (50.4) and techniques.
5. Treaties limit counts and tests; leagues (51.7) inspect; breaches are treaty breaches.

**Tools and control.**

- Mortal tools `begin_mass_weapon` (`holder_id`, `harm`, `reach`), `declare_posture` (`holder_id`, `toward_id`, `posture`), `use_mass_weapon` (`weapon_id`, `target_id`), `clear_remnants` (`region_id`, `budget`).
- Son tool `still_weapon` (`weapon_id`, `reason`).
- God levers `mass_weapon:*`, `deterrence_posture:*`, `war_remnant:*`.
- An "Arsenal" section in polity drawers; remnants as an atlas layer and in region drawers.
- Context block `mass_weapons`.

**Incidents.** `war.mass_weapon_stage`, `war.mass_weapon_tested`, `war.mass_weapon_used`, `war.posture_declared`, `war.bluff_exposed`, `war.remnant_harm`, `war.remnants_cleared`.

**Rules namespace.** `mass_weapons`:

| Key | Default | Range |
|---|---|---|
| `mass_weapons.deterrence_attack_cut_pct` | 50 | 0–100 |
| `mass_weapons.doom_per_reach` | 5 | 0–100 |
| `mass_weapons.remnant_harm_per_density` | 2 | 0–50 |
| `mass_weapons.remnant_decay_per_epoch` | 3 | 0–50 |
| `mass_weapons.clearance_per_budget` | 1 | 0–20 |
| `mass_weapons.stage_visibility_pct` | 30 | 0–100 |

**Codex and book.** Arsenals and postures in polity entries; remnants in region entries with their origin war; uses in war entries.

**Integrity.** A weapon's holder has the technique; remnants name an ended war.

**Legacy.** None for weapons; ended wars with sieges and battles in a region leave `wreck_field` or `buried_charges` remnants only where their units used such arms.

**Applies to.** Every era and world: poisoned wells and plague corpses thrown over walls, rites that blight a land, burning weapons, radiation, swarms of made machines. Polity drawers for arsenals; region and orbit drawers for remnants.

**Couplings.** War, doom, disease, ecology, body, treaties, leagues, espionage, mishaps, land value, works.

### 51.17 War between worlds and migration between worlds

**Builds on.** Armies carry `world_id`; transport fleets, journeys (47.8.12), interworld routes, gates and rifts (47.8.13); colonies founded by expeditions; the `interworld` treaty kind and `interworld_federation` faction kind; drop troops and orbital bombardment as unit and tactic entries; spec 13 mentions migration pressure toward new worlds through journeys. 51.17 adds campaigns that cross worlds and mass movements of peoples between worlds.

**Current.** Every military step works inside one world. No army is carried to another world to fight there, no polity holds the space around a world, and peoples move to other worlds only as small colonies.

**State.**

- **`interworld_campaigns`.** Attacker, defender, target world, `CampaignStage` (`gathering`, `transit`, `supremacy`, `landing`, `holding`, `withdrawn`), carriers and their capacity, the route or gate, transit length, supply line length and delay (signals 47.2.5, light lag where the world's physics has it).
- **`orbital_control`.** World, holder, strength, contested by.
- **`interworld_migrations`.** People or community, from world, to world, `MigrationCause` (`flight`, `land_hunger`, `faith_call`, `exile`, `labour_draw`, `world_dying`, `resettlement`), count per epoch, carriers, reception (welcome, quota, refusal).

**Behaviour.**

1. Campaigns gather carriers and troops, cross by route or gate, fight for control of the space around the target (vessel engagements, 49.3), then land under the control they hold. Landed forces are supplied along the line; long lines starve them.
2. Orbital control lets the holder bombard (by tactic, with recorded harm), blockade trade and travel, and cut signals; it is lost to the defender's vessels and powers.
3. Holding a world's land follows occupation (51.15) and its regimes; supply cut, the landed force withers or surrenders.
4. Migrations move whole groups when push and pull pass thresholds and carriers allow; the receiving world's polities set reception, and migrants found settlements, enter districts or wait in camps. Disease spreads with them by the agent rules (50.24).

**Tools and control.**

- Mortal tools `launch_campaign` (`attacker_id`, `target_world_id`, `route_id`, `forces`), `contest_orbit` (`world_id`, `fleet_id`), `lead_migration` (`community_id`, `to_world_id`, `cause`).
- Son tool `close_the_way` (`route_or_gate_id`, `epochs`, `reason`).
- God levers `interworld_campaign:*`, `orbital_control:*`, `interworld_migration:*`.
- Campaigns and migrations on the cosmography map; an "Orbit" block in world drawers.
- Context block `interworld`.

**Incidents.** `war.campaign_launched`, `war.transit_lost`, `war.orbit_won`, `war.orbit_lost`, `war.landing`, `war.bombardment`, `war.campaign_withdrawn`, `migration.interworld_began`, `migration.interworld_arrived`, `migration.interworld_refused`.

**Rules namespace.** `interworld`:

| Key | Default | Range |
|---|---|---|
| `interworld.transit_loss_pct` | 5 | 0–100 |
| `interworld.supply_decay_per_hop` | 10 | 0–100 |
| `interworld.landing_needs_control_pct` | 60 | 0–100 |
| `interworld.bombard_harm_per_strength` | 2 | 0–50 |
| `interworld.migration_push_threshold` | 60 | 0–100 |
| `interworld.carrier_people_per_capacity` | 100 | 1–100000 |

**Codex and book.** Campaigns in war and world entries; orbital control in world entries; migrations in people and world entries.

**Integrity.** The route joins the two worlds; landed forces lie on the target world; migrants' destination exists.

**Legacy.** None; campaigns and migrations start empty. Existing colonies keep their founding records.

**Applies to.** Worlds joined by any carrier the world allows: vessels, gates, rifts, divine bridges, grown vessels, rite travel. Worlds with no way between them keep these idle and say so.

**Couplings.** War, vessels, occupation, supply, signals, trade, disease, demography, leagues, treaties.

### 51.18 Family dynamics

**Builds on.** Households (47.8.21), kin roles and duties and kin groups (50.6), inheritance and succession laws, houses, legitimacy rules (50.8), relationships and bonds, feuds (47.8.10). 51.18 adds what happens between members of one family.

**Current.** Relations between kin follow bonds of the same kind as between strangers; inheritance follows law alone. A parent's favour, siblings' rivalry, a disowned child, a family joined from two marriages and the power of a surviving elder are not modelled.

**State.**

- **`kin_dynamics`.** Per household or house, a parent row with five typed child tables:
  - `kin_favours` (parent, child, strength);
  - `kin_rivalries` (two members, cause `RivalryCause`: `inheritance`, `favour`, `office`, `love`, `standing`);
  - `kin_disownings` (disowner, disowned, reason, reversible);
  - `kin_blends` (members joined by a later union, standing of step kin by the culture);
  - `elder_sway` (a surviving elder, such as a ruler's widowed spouse or the eldest kin by the culture's rule, whose sway over the household or house is held as a value 0–100).

**Behaviour.**

1. Favour shifts inheritance where law allows discretion, gifts and care, and feeds rivalry among the others.
2. Rivalries run through the existing relation and feud mechanics and may split a house or start a succession war.
3. Disowning removes a member from inheritance and the house by the culture's rules; the disowned may found a line of their own or seek revenge; reconciliation reverses it.
4. Step kin have the standing the culture gives them; tensions and bonds form by the same rules as other kin.
5. Elder power steers marriages, heirs and household budgets until death or overthrow by the heir.

**Tools and control.**

- Mortal tools `favour_child` (`child_id`), `disown` (`member_id`, `reason`), `reconcile_kin` (`member_id`).
- Son tool `stir_kin` (`household_or_house_id`, `kind`, `reason`).
- God levers `kin_dynamic:*`, `kin_favour:*`, `kin_rivalry:*`, `kin_disowning:*`, `kin_blend:*`, `elder_sway:*`.
- A "Family" block in household, house and mortal drawers.
- Context block `kin` gains family dynamics.

**Incidents.** `kin.favoured`, `kin.rivalry_began`, `kin.disowned`, `kin.reconciled`, `kin.elder_steered`, `kin.house_split`.

**Rules namespace.** `kin_dynamics`:

| Key | Default | Range |
|---|---|---|
| `kin_dynamics.favour_inheritance_pct` | 20 | 0–100 |
| `kin_dynamics.rivalry_from_favour_pct` | 15 | 0–100 |
| `kin_dynamics.split_threshold` | 70 | 0–100 |
| `kin_dynamics.reconcile_chance_pct` | 10 | 0–100 |

**Codex and book.** Family dynamics in household, house and mortal entries.

**Integrity.** Both sides of a dynamic belong to the household or house; elder power names a living member.

**Legacy.** None; dynamics start empty and form from relations.

**Applies to.** Every people and biology with kin, every era and world; biologies without kin (made minds without makers, hive members) show the block as not applicable with that reason. Sons and foreign gods with divine kin read it through divine kin roles.

**Couplings.** Inheritance, succession, houses, feuds, relations, care, marriages.

### 51.19 Spread of feeling between beings

**Builds on.** Emotions (F5–F8), crowd moods and cascades (`crowd_moods`, `cascades`, F32), rout contagion in battle (`morale.rout_contagion`), emotion spirits and harvests (W25). 51.19 adds the spread of feeling along bonds and in shared places outside crowds and battles.

**Current.** Feelings spread in crowds and routs. A grieving household, a frightened town or a joyful court does not pass its feeling on by contact.

**State.**

- **`feeling_spread`.** One row per settlement and per household: the dominant feelings (values of the emotion enum) with strength, and `locked`. A being's susceptibility is derived each epoch from traits and bonds and is not stored.

**Behaviour.**

1. Each epoch strong feelings pass along bonds (kin, friends, followers) and to those sharing a place, by susceptibility and bond strength, and fade over time.
2. Shared feeling moves decisions (biases, 47.8.2), crowd thresholds (F32), worship (emotion-fed gods) and gatherings.
3. Leaders and speakers with high charisma spread their feeling further (50.13).

**Tools and control.**

- Mortal tool `stir_feeling` (`place_or_household_id`, `feeling`), read by charisma and bonds.
- Son tool `move_hearts` (`place_id`, `feeling`, `strength`, `reason`).
- God levers `feeling_spread:edit/hold` per place.
- A "Mood" block in settlement and household drawers.
- Context block `mood`.

**Incidents.** `mood.spread`, `mood.faded`.

**Rules namespace.** `feeling_spread`:

| Key | Default | Range |
|---|---|---|
| `feeling_spread.per_bond_pct` | 10 | 0–100 |
| `feeling_spread.per_place_pct` | 5 | 0–100 |
| `feeling_spread.fade_per_epoch` | 20 | 0–100 |

**Codex and book.** Moods of places in settlement entries.

**Integrity.** Feelings are values of the emotion enum; strength 0–100.

**Legacy.** None; computed from existing emotions on the first epoch.

**Applies to.** Every being that feels, in every world; made minds by their make (44.5); beings without feeling are skipped and the block says why.

**Couplings.** Emotions, decisions, crowds, worship, gatherings, speech.

### 51.20 Interpretation and mistranslation

**Builds on.** Interpreters (`rules.interpreters`, `engine/lore/language.py`: shared lexicon, phonology similarity, an interpreter present by language skill), envoys and correspondence (F21), rumour fidelity. 51.20 adds interpreters as a role whose work can fail, and the errors that follow.

**Current.** Two communities understand each other if they share enough language or an interpreter is present. An interpreter never errs, never lies and never shapes what is said.

**State.**

- **`interpretations`.** Event (a parley, a treaty, a trial, a trade, a sermon), interpreter, languages, fidelity (from skill, the languages' distance and the subject), `InterpretationFault` (`none`, `lost_meaning`, `wrong_term`, `softened`, `hardened`, `slanted`, `invented`), whether the fault was found.

**Behaviour.**

1. Every exchange between communities without a shared language runs through an interpretation; its fidelity sets what each side believes was said.
2. Faults change outcomes: a treaty clause read two ways, an insult heard where none was meant, a confession misheard, a price misunderstood. Interpreters with loyalties slant on purpose.
3. Found faults reopen agreements and raise grievance; loyal and skilled interpreters gain standing and offices.

**Tools and control.**

- Mortal tool `interpret` (`event_id`, `slant`).
- Son tool `confuse_tongues` (`event_id`, `reason`).
- God levers `interpretation:*`.
- Interpretations on treaty, trial and incident pages.
- Context block `interpretation`.

**Incidents.** `tongue.mistranslated`, `tongue.slanted`, `tongue.fault_found`.

**Rules namespace.** `interpreters` gains:

| Key | Default | Range |
|---|---|---|
| `interpreters.fault_base_pct` | 10 | 0–100 |
| `interpreters.fault_per_distance_pct` | 20 | 0–100 |
| `interpreters.slant_loyalty_threshold` | 60 | 0–100 |

**Codex and book.** Interpretations in the entries of the events they served, with fidelity and fault.

**Integrity.** The interpreter speaks both languages.

**Legacy.** None; recorded from the first epoch.

**Applies to.** Every exchange between beings without a shared language, including mind links (W45) and made minds' protocols (W44).

**Couplings.** Treaties, trials, trade, diplomacy, rumours, grievance.

### 51.21 Grave goods and tomb robbing

**Builds on.** Funeral customs (`FuneralCustom`, `funeral_rite`), death work (50.12), necropolis districts, items and artefacts, excavations and ruins (`excavations`), damnatio memoriae. 51.21 adds what is buried with the dead and those who take it.

**Current.** The dead are buried, burned or otherwise treated, and their goods pass by inheritance. Nothing is placed with them and no tomb is robbed.

**State.**

- **`grave_goods`.** Grave (a tomb structure, a site or a burial in a necropolis), the dead, items and goods placed, the custom that required them, protections (`GraveGuard`: `none`, `hidden`, `sealed`, `guarded`, `trapped`, `cursed` where the world's laws allow, `warded`).

**Behaviour.**

1. Customs and rank set what goes with the dead; the goods leave inheritance and the economy.
2. Robbers seek graves by value and lack of guard; robbery returns goods to markets, angers kin and faith, and may bring curses where the world's laws allow.
3. Later finds of graves (excavation) yield goods and knowledge of the past (F33).

**Tools and control.**

- Mortal tools `place_grave_goods` (`grave_id`, `item_ids`), `rob_grave` (`grave_id`), `guard_grave` (`grave_id`, `guard`).
- Son tool `keep_the_dead` (`grave_id`, `guard`, `reason`).
- God levers `grave_good:*`.
- Grave goods in tomb and site drawers.
- Context block `the_dead` gains grave goods.

**Incidents.** `dead.goods_placed`, `dead.grave_robbed`, `dead.robber_caught`, `dead.grave_found`.

**Rules namespace.** `grave_goods`:

| Key | Default | Range |
|---|---|---|
| `grave_goods.share_by_rank_pct` | 10 | 0–100 |
| `grave_goods.rob_chance_per_value_pct` | 5 | 0–100 |
| `grave_goods.guard_cut_pct` | 50 | 0–100 |

**Codex and book.** Grave goods in the entries of the dead and their tombs.

**Integrity.** Placed items exist and are held by the grave.

**Legacy.** Notable dead buried in tombs gain grave goods by their culture's custom and rank.

**Applies to.** Every people that keeps its dead in a place, in every era and world; peoples whose customs leave no place show it as not applicable with that reason.

**Couplings.** Death work, inheritance, markets, crime, faith, excavation, memory.

### 51.22 Conditions without an agent

**Builds on.** Chronic illness as a condition with mobility, melee and fertility effects (`rules/registry/body.py`), diseases with a chronic rate, ageing, nutrition (47.8.1), pollution, body systems and sensitivities (50.25), madness. 51.22 adds conditions that arise without any infectious agent.

**Current.** Long illness comes only from disease. Bodies do not wear out by organ, diet or exposure.

**State.**

- **`agentless_conditions`.** A catalogue of condition kinds (authored, F57), each typed by `ConditionCause` (`age`, `diet`, `exposure`, `heredity`, `injury_aftermath`, `strain`, `unknown`) and by the body system it affects (50.25), with onset, course (`stable`, `worsening`, `episodic`) and effects through the existing condition rows. The `conditions` table gains `cause` (`ConditionCause`) and `kind_id` (a row of this catalogue).

**Behaviour.**

1. Each epoch beings roll for conditions by age, diet, exposure (pollution, work, 47.10), heredity (F26) and strain, per body system.
2. Conditions lower capacity and life span, cost care, and may be eased by the people's medicine tier and folk knowledge (50.7).
3. Rates in a people follow its living standard and diet, so prosperity and want change the conditions that are common.

**Tools and control.**

- Mortal tool `seek_cure` (existing) gains `condition_id` for conditions of any cause.
- Son tool `ease_body` (`being_id`, `condition_id`, `reason`).
- God levers `agentless_condition:*` for the catalogue, and the existing condition levers with the new `cause` and `kind_id` fields.
- Conditions in the body section of every being.
- Context block `body` gains causes.

**Incidents.** `body.condition_arose`, `body.condition_worsened`, `body.condition_eased`.

**Rules namespace.** `agentless_conditions`:

| Key | Default | Range |
|---|---|---|
| `agentless_conditions.age_rate_pct` | 3 | 0–100 |
| `agentless_conditions.diet_rate_pct` | 2 | 0–100 |
| `agentless_conditions.exposure_rate_pct` | 2 | 0–100 |
| `agentless_conditions.heredity_weight_pct` | 30 | 0–100 |

**Codex and book.** Conditions with their causes in body sections.

**Integrity.** The body system exists for the biology.

**Legacy.** Existing chronic illnesses with no recorded disease gain cause `unknown`.

**Applies to.** Every biology with a body that wears; made seats wear by their own rules (F50); bodiless beings are skipped with that reason.

**Couplings.** Body, life span, medicine, diet, pollution, work, heredity, care.

### 51.23 Fertility control

**Builds on.** The course of reproduction and intimacy norms (50.8), births and fertility (genetics fertility locus, F26), population policy instruments (50.1), medicine tiers (47.2.3), folk knowledge (50.7). 51.23 adds the means by which beings prevent, seek or end conception.

**Current.** Fertility is a trait and a chance; no being or culture acts on it.

**State.**

- **`fertility_means`.** Per people and per biology: `FertilityMeans` (`prevention`, `remedy_for_barrenness`, `ending_pregnancy`, `assisted_conception`, `surrogacy`, `made_birth` (W46)), each with method source (folk, medicine tier, rite, power), reliability, risk, and the culture's stance (from 50.8 stances).

**Behaviour.**

1. Use of a means changes birth chances by reliability, read by births and population policy.
2. Stances decide whether use is open, hidden or punished; hidden use carries the risk of exposure.
3. Means spread with knowledge and trade and are targeted by population policy (bans, rewards).

**Tools and control.**

- Mortal tool `use_fertility_means` (`means`).
- Son tool `move_fertility` (`community_id`, `means`, `reliability_change`, `reason`).
- God levers `fertility_means:*`.
- A block in the "Unions and birth" section of culture drawers.
- Context block `unions_and_birth` gains means, plain and closed-door.

**Incidents.** `birth.means_used`, `birth.means_exposed`, `birth.means_banned`.

**Rules namespace.** `fertility_means`:

| Key | Default | Range |
|---|---|---|
| `fertility_means.prevention_reliability_pct` | 50 | 0–100 |
| `fertility_means.remedy_success_pct` | 20 | 0–100 |
| `fertility_means.risk_pct` | 5 | 0–100 |

**Codex and book.** Means per culture, described plainly.

**Integrity.** Means read only the biology's reproductive system.

**Legacy.** None; means come from genesis and the model's authoring.

**Applies to.** Every biology that reproduces by conception, every era and world; other biologies show the block as not applicable with that reason. Narrated plainly and behind closed doors (K.47).

**Couplings.** Births, population policy, norms, medicine, knowledge, law.

### 51.24 Honours conferred on persons

**Builds on.** Titles (48.6), heraldry, prestige and renown, holy and warrior orders (faction kinds), battle honours of named units (spec 13 5.1 reference pass 6, planned; built by whichever wave runs first, 0.7). 51.24 adds honours that a polity, faith or organisation confers on a person for service.

**Current.** Renown grows by deeds; titles come with land and office. No order of merit, decoration or honorary rank is conferred.

**State.**

- **`honour_kinds`.** Authored per conferrer (F57): name in the world's language, rank among the conferrer's honours, privileges (`HonourPrivilege`: `precedence`, `pension`, `land`, `seat`, `immunity`, `title`, `none`), limit on holders.
- **`honours_held`.** Holder (any node that can serve), honour kind, conferred by, deed (a recorded incident), epoch, revoked.

**Behaviour.**

1. Conferrers grant honours for deeds; holders gain prestige, loyalty to the conferrer and the privileges.
2. Honours sold or given to favourites lose worth; revocation shames.
3. Honours pass into heraldry, epitaphs and the book; some cultures make them hereditary.

**Tools and control.**

- Mortal tools `confer_honour` (`honour_kind_id`, `holder_id`, `deed_incident_id`), `revoke_honour` (`honour_id`), `found_honour` (`conferrer_id`, `name_reason`, `privileges`, `limit`).
- Son tool `honour_servant` (`holder_id`, `reason`).
- God levers `honour_kind:*`, `honour_held:*`.
- An "Honours" block in `ThingSections` for every node that can hold one.
- Context block `honours`.

**Incidents.** `honour.conferred`, `honour.revoked`, `honour.sold`.

**Rules namespace.** `honours`:

| Key | Default | Range |
|---|---|---|
| `honours.prestige_per_rank` | 5 | 0–50 |
| `honours.sale_worth_loss_pct` | 20 | 0–100 |
| `honours.loyalty_gain` | 10 | 0–100 |

**Codex and book.** Honours in holders' entries with the deed and conferrer; honour kinds in conferrers' entries.

**Integrity.** The holder count stays within the limit; the deed is a recorded incident.

**Legacy.** None; honours start empty.

**Applies to.** Every node that can serve a conferrer: mortals, made minds, creatures in service, units (with battle honours), and sons honoured by a foreign pantheon where treaties allow. Worlds, stars and the Creator cannot serve a conferrer and show the block as not applicable with that reason.

**Couplings.** Prestige, loyalty, titles, heraldry, pensions, memory.

### 51.25 Sea waves from quakes, slides and storms

**Builds on.** Disasters (`Disaster`: earthquake, flood, storm, eruption, volcanic quake), coasts and deltas (50.23), harbours, tides by moons (10.9). 51.25 adds the great waves that a quake, a slide or a storm drives onto a coast.

**Current.** A quake shakes the region where it strikes; a storm harms its region. Nothing crosses a sea to strike another coast.

**State.**

- **`sea_waves`.** Origin (a quake, an eruption, a slide, a storm, an impact, a divine act), sea, coasts reached with height and arrival delay, warning given (50.28 observation methods).

**Behaviour.**

1. Quakes, eruptions and slides under or beside a sea, impacts and strong storms roll for waves by strength and depth.
2. Waves strike every coast of the sea by distance and the coast's shape, harming harbours, districts and fields, salting land and drowning those not warned.
3. Warnings from observation methods and customs lower deaths; coastal works (50.4) lower harm.

**Tools and control.**

- Mortal tool `warn_coast` (`region_id`, `method`), read by observation methods (50.28).
- Son tool `raise_sea` (`sea_id`, `strength`, `reason`) under the existing disaster acts.
- God levers `sea_wave:*`.
- Waves on the atlas and in region entries.
- Context block `disasters` gains waves.

**Incidents.** `land.sea_wave`, `land.wave_warned`, `land.coast_salted`.

**Rules namespace.** `sea_waves`:

| Key | Default | Range |
|---|---|---|
| `sea_waves.quake_wave_chance_pct` | 20 | 0–100 |
| `sea_waves.storm_surge_chance_pct` | 10 | 0–100 |
| `sea_waves.harm_per_height` | 5 | 0–50 |
| `sea_waves.warning_death_cut_pct` | 60 | 0–100 |

**Codex and book.** Waves in the entries of every coast they struck.

**Integrity.** Coasts reached lie on the wave's sea.

**Legacy.** None.

**Applies to.** Every world with seas of any liquid; worlds without seas show the layer idle with that reason.

**Couplings.** Disasters, coasts, harbours, settlements, harvests, works, observation, faith.

### 51.26 Creature societies

**Builds on.** Fauna and creature traits (including `hive_minded`), beasts and monsters (`engine/ecology/beasts.py`, `monsters.py`), creature attacks (47.6.3), sacred animals, beast worship. 51.26 adds the social structure of creatures that live in groups but are not peoples.

**Current.** Creatures are species counts and single beasts. A pack, herd, colony or hive has no leader, ranks, territory or succession.

**State.**

- **`creature_groups`.** Species, region or lair, `GroupForm` (`pack`, `herd`, `colony`, `hive`, `troop`, `flock`, `solitary_range`), size, leader, ranks, territory, rival groups.

**Behaviour.**

1. Groups hold territory, fight rival groups and raid settlements by hunger and pressure; leaders fall and are replaced by contests.
2. Group size and form set danger to travellers and herds, and the yield of hunts.
3. Groups move with seasons and are pushed by settlement and protected by 51.9.

**Tools and control.**

- Mortal tool `drive_off_group` (`group_id`, `means`), beside the existing hunting tools.
- Son tool `lead_creatures` (`group_id`, `aim`, `reason`).
- God levers `creature_group:*`.
- Groups on the atlas and in region and species drawers.
- Context block `wilds` gains groups.

**Incidents.** `beasts.group_formed`, `beasts.leader_fell`, `beasts.territory_war`, `beasts.group_raid`, `beasts.group_moved`.

**Rules namespace.** `creature_groups`:

| Key | Default | Range |
|---|---|---|
| `creature_groups.raid_hunger_threshold` | 60 | 0–100 |
| `creature_groups.contest_chance_pct` | 10 | 0–100 |
| `creature_groups.territory_war_pct` | 5 | 0–100 |

**Codex and book.** Groups in region and species entries.

**Integrity.** Group members are of one species, unless the form allows mixed groups.

**Legacy.** Species with large counts in a region get groups by their social traits.

**Applies to.** Every world with fauna; species without social traits keep `solitary_range`.

**Couplings.** Ecology, hunts, travel danger, raids, protected nature, faith.

### 51.27 Conceptions of the divine

**Builds on.** Faiths with tenets (`TenetKind`), doctrine and doctrinal drift, theologians, theodicy crises, pantheon structures of the gods (47.5.4), syncretism. 51.27 adds how a faith conceives the divine, separate from what the gods are.

**Current.** A faith worships its gods and holds tenets. Whether it holds one god, many, one above many, the divine in all things, a distant maker, spirits in places, or none, is not typed; so conversions, syncretism and disputes cannot read it.

**State.**

- **`divine_conceptions`.** Per faith: `DivineCount` (`one`, `one_above_many`, `many`, `pairs`, `all_is_divine`, `none`), `DivineNearness` (`distant`, `present`, `within`), `DivinePersonhood` (`persons`, `forces`, `principle`, `mixed`), place of the Creator in it (acknowledged, unknown, denied, rival), and how the real gods of the world map onto it (each god as true, as servant, as demon, as unknown).

**Behaviour.**

1. Conceptions set which acts of gods a faith can accept (a faith that holds one god reads other gods' signs as false or as servants), which syncretisms are possible, and how theodicy crises run.
2. Doctrinal drift and theologians move conceptions; heresies and schisms split on them.
3. The gods' real acts (47.5) test conceptions; a faith whose conception denies an acting god faces crises when that god acts openly.

**Tools and control.**

- Son tool `reveal_nature` (`faith_id`, `axis`, `value`, `reason`).
- Mortal tool `argue_doctrine` gains `conception_axis`.
- God levers `divine_conception:*`.
- A "Conception" block in faith drawers.
- Context block `faith` gains the conception.

**Incidents.** `faith.conception_changed`, `faith.conception_tested`, `faith.conception_split`.

**Rules namespace.** `divine_conceptions`:

| Key | Default | Range |
|---|---|---|
| `divine_conceptions.drift_per_epoch_pct` | 2 | 0–100 |
| `divine_conceptions.denied_god_crisis_pct` | 30 | 0–100 |
| `divine_conceptions.syncretism_fit_pct` | 50 | 0–100 |

**Codex and book.** The conception in faith entries, with how each god is read.

**Integrity.** Mapped gods exist in the world.

**Legacy.** Faiths get conceptions from their tenets and the number of gods they worship.

**Applies to.** Every faith in every world, including faiths of made minds and of creatures that worship.

**Couplings.** Faith, conversion, syncretism, theodicy, schism, divine acts.

### 51.28 Integration of every section

The rules of 50.17a apply to 51.1–51.27 in full:

- every era and every kind of world, with the section idle and saying why where the world lacks its subject;
- every kind of thing through `ThingSections` where a section applies to every node, with the reason stated where it applies to some kinds only (each section's **Applies to**);
- genesis through typed fields only, with no template default that carries images;
- typed context blocks, tool texts that list every enum value and describe every field;
- incidents under F58 with plain templates;
- every number a rule key, with balance bands in `13-balance-bands.json`;
- recorded fixups (each section's **Legacy**);
- checks under 47.13 (each section's **Integrity**);
- designed sections in the book and the Codex, never truncated;
- the layers of 6.6 for every table: changes, moments, places, terms, history, search and control.

New entity type: `league` (51.7). It is a node like every entity, renders `ThingSections`, has an atlas presence, a wiki page, a book and Codex entry and a create screen, and joins `check_wiring.py`'s list of node kinds.

New faction kind: `worker_body` (51.4). New law kind: `competition_law` (51.3).

### 51.29 Guards

| Guard | Fails when |
|---|---|
| `tests/engine/core/test_economic_orders.py`, `test_governance.py`, `test_competition.py`, `test_labour.py`, `test_monetary.py`, `test_securities.py`, `test_leagues.py`, `test_city_rules.py`, `test_protected_nature.py`, `test_departures.py`, `test_referendums.py`, `test_reckoning.py`, `test_leader_cults.py`, `test_restoration.py`, `test_occupation_regimes.py`, `test_mass_weapons.py`, `test_interworld.py`, `test_kin_dynamics.py`, `test_feeling_spread.py`, `test_interpretation.py`, `test_grave_goods.py`, `test_agentless_conditions.py`, `test_fertility_means.py`, `test_honours.py`, `test_sea_waves.py`, `test_creature_groups.py`, `test_divine_conceptions.py` | a section's behaviour does not produce its effects on a seeded world |
| `scripts/check_inventory.py` (5.10) | a table, enum, step, kind, tool, lever, screen or text file of W51 has no inventory row |
| `scripts/check_spec_depth.py` (47.9) | a section of W51 lacks one of the thirteen elements |
| `scripts/check_wiring.py` | the `league` entity type is missing from the book's owners or a drawer page does not render `ThingSections` |

### 51.30 Compliance catalogue (W51)

| Section | Tables | Phases | God levers | Screens | Tools and context | Codex and book | Integrity | Backfill |
|---|---|---|---|---|---|---|---|---|
| 51.1 economic orders | `economic_orders`, `economic_order_kinds`, `order_transitions` | economy, markets, households, treasury, revolts | `economic_order:*`, `economic_order_kind:*`, `order_transition:*` | "Economic order" panel | `set_economic_order`, `begin_transition`, `move_economic_order`; `economic_order` | polity entries; Records | sectors valid; holdings exist | from laws and stores |
| 51.2 organisations | `org_governance`, `org_seats`, `org_cliques`, `org_mergers`, `org_research`, `insolvency_cases` | factions, companies, courts, research | `org_governance:*`, `org_seat:*`, `org_clique:*`, `org_merger:*`, `org_research:*`, `insolvency_case:*` | "Governance" section, merger and case pages | `cast_org_vote`, `seek_headship`, `split_org`, `bid_for_org`, `fund_research`, `file_insolvency`, `sway_org`; `governance` | organisation entries | weights sum to 100; claims real | from shares and leaders |
| 51.3 competition | `market_structures`, `cartels`, `price_wars`; law kind `competition_law` | markets, law | `market_structure:*`, `cartel:*`, `price_war:*` | "Market structure" section | `form_cartel`, `start_price_war`, `report_cartel`, `break_market`; `market_structure` | market sections | shares sum to 100 | derived; guild monopolies |
| 51.4 labour | `worker_bodies`, `labour_contracts`, `labour_disputes` | production, collective, law | `worker_body:*`, `labour_contract:*`, `labour_dispute:*` | "Labour" section, dispute page | `found_worker_body`, `bargain_contract`, `call_dispute`, `lock_out`, `stir_labour`; `labour` | settlement and organisation entries | parties exist | striking guilds, strikes |
| 51.5 money | `monetary_authorities` | credit, prices, banks | `monetary_authority:*` | "Money" section | `set_monetary_policy`, `found_monetary_authority`, `shake_coin`; `money_policy` | polity and currency entries | currency exists | issuers |
| 51.6 securities | `exchanges`, `securities`, `security_holdings`, `security_prices` | markets, credit, treasury | `exchange:*`, `security:*`, `security_holding:*`, `security_price:*` | exchange page | `list_security`, `trade_security`, `stir_market_mood`; `securities` | issuer and holder entries | holdings within amount | shares, polity loans |
| 51.7 leagues | `polity_leagues`, `league_members`, `league_decisions` | diplomacy, war, trade, courts | `polity_league:*`, `league_member:*`, `league_decision:*` | league drawer, atlas layer | `found_league`, `join_league`, `table_league_motion`, `bind_league`; `leagues` | league entries | members are polities | coalitions, federations |
| 51.8 city rules | `land_use_rules`, `municipal_services`, `conurbations` | settlement, fire, disease, crime | `land_use_rule:*`, `municipal_service:*`, `conurbation:*` | "City rules", "Services", city scene | `set_land_use_rule`, `provide_service`, `join_settlements`, `bless_city`; `city_rules` | settlement entries | districts of the settlement | planned morphology, wells, watch |
| 51.9 protected nature | `protected_areas`, `species_protections` | ecology, crime, law | `protected_area:*`, `species_protection:*` | atlas layer, "Protection" section | `protect_area`, `protect_species`, `reintroduce`, `hallow_wild`; `protected_nature` | region and species entries | habitat fits | reserves, groves |
| 51.10 departures | `departures` | offices, succession | `departure:*` | office and holder drawers | `leave_office`, `return_to_office`, `call_to_step_aside`; `offices` | holder entries | holder held office | step-downs |
| 51.11 referendums | `referendums` | affairs, law, opinion | `referendum:*` | referendum pages | `call_referendum`, `campaign_for_vote`, `sway_vote`; `votes` | polity entries | franchise matches | none |
| 51.12 reckoning | `reckonings`, `reckoning_measures`, `reckoning_cases` | justice, offices, historiography | `reckoning:*`, `reckoning_measure:*`, `reckoning_case:*` | reckoning page | `open_reckoning`, `try_servant`, `weigh_reckoning`; `reckoning` | polity entries | cases name incidents | purges after coups |
| 51.13 leader cults | `leader_cults` | legitimacy, censorship | `leader_cult:*` | "Cult" block | `promote_cult`, `tear_down_cult`, `sway_cult`; `leader_cult` | leader entries | leader mortal or made | none |
| 51.14 restoration | `restorations` | polity formation, revolts | `restoration:*` | dead polity page | `raise_restoration`, `restore_polity`, `stir_memory`; `restoration` | polity entries | predecessor is dead | pretenders |
| 51.15 occupation | `occupation_regimes`, `collaborations`, `occupation_measures` | military, intrigue, demography | `occupation_regime:*`, `collaboration:*`, `occupation_measure:*` | "Occupation" section | `set_occupation_rule`, `collaborate`, `impose_measure`, `expose_collaborator`, `sway_occupation`; `occupation` | occupied and occupier entries | open occupation | open occupations |
| 51.16 mass weapons | `mass_weapons`, `deterrence_postures`, `war_remnants` | war, doom, mishaps, works | `mass_weapon:*`, `deterrence_posture:*`, `war_remnant:*` | "Arsenal" section, atlas layer | `begin_mass_weapon`, `declare_posture`, `use_mass_weapon`, `clear_remnants`, `still_weapon`; `mass_weapons` | polity, region, war entries | technique held | remnants of past wars |
| 51.17 interworld | `interworld_campaigns`, `orbital_control`, `interworld_migrations` | military, vessels, migration | `interworld_campaign:*`, `orbital_control:*`, `interworld_migration:*` | cosmography map, "Orbit" block | `launch_campaign`, `contest_orbit`, `lead_migration`, `close_the_way`; `interworld` | war, world, people entries | route joins worlds | none |
| 51.18 family | `kin_dynamics`, `kin_favours`, `kin_rivalries`, `kin_disownings`, `kin_blends`, `elder_sway` | relations, inheritance, houses | `kin_dynamic:*`, `kin_favour:*`, `kin_rivalry:*`, `kin_disowning:*`, `kin_blend:*`, `elder_sway:*` | "Family" block | `favour_child`, `disown`, `reconcile_kin`, `stir_kin`; `kin` | household, house, mortal entries | members of the household | none |
| 51.19 feeling | `feeling_spread` | mind, crowds, worship | `feeling_spread:*` | "Mood" block | `stir_feeling`, `move_hearts`; `mood` | settlement entries | values of the enum | computed |
| 51.20 interpretation | `interpretations` | diplomacy, justice, trade | `interpretation:*` | event pages | `interpret`, `confuse_tongues`; `interpretation` | event entries | languages spoken | none |
| 51.21 grave goods | `grave_goods` | death, crime, excavation | `grave_good:*` | tomb and site drawers | `place_grave_goods`, `rob_grave`, `guard_grave`, `keep_the_dead`; `the_dead` | entries of the dead | items held | notable tombs |
| 51.22 conditions | `agentless_conditions`; `cause` and `kind_id` on `conditions` | body, health | `agentless_condition:*`, condition levers | body section | `seek_cure`, `ease_body`; `body` | body sections | system exists | chronic illness |
| 51.23 fertility | `fertility_means` | births, population policy | `fertility_means:*` | "Unions and birth" block | `use_fertility_means`, `move_fertility`; `unions_and_birth` | culture entries | biology reproduces | none |
| 51.24 honours | `honour_kinds`, `honours_held` | standing, loyalty | `honour_kind:*`, `honour_held:*` | "Honours" in `ThingSections` | `confer_honour`, `revoke_honour`, `found_honour`, `honour_servant`; `honours` | holder and conferrer entries | within limit | none |
| 51.25 sea waves | `sea_waves` | disasters, coasts | `sea_wave:*` | atlas, region entries | `warn_coast`, `raise_sea`; `disasters` | coast entries | coasts on the sea | none |
| 51.26 creature groups | `creature_groups` | ecology, wilds, raids | `creature_group:*` | atlas, species drawers | `drive_off_group`, `lead_creatures`; `wilds` | region and species entries | one species | from counts |
| 51.27 conceptions | `divine_conceptions` | faith, conversion, theodicy | `divine_conception:*` | "Conception" block | `reveal_nature`, `argue_doctrine`; `faith` | faith entries | gods exist | from tenets |

Every new agent tool has a case in `every_son_tool.py` or `every_mortal_tool.py`. Every lever runs with real values in `test_every_lever.py`. Every table reaches the book and the Codex through `services/books/typed.py` or a designed Records table. Every incident kind follows F58.

### 51.31 Cross-cutting layers (W51)

Each table of W51 fills the layers of 6.6: its changes are recorded with terms (F58.5, F58.7), its happenings carry moments and places (F58.6), its records can be read at any earlier moment (F58.11), nothing is folded away (F58.12), every record is searchable by its typed fields, and every record can be created, edited, held, deleted and reverted from the frontend.

### 51.32 Couplings, loops, stories and decisions

**Couplings.**

- C70 Economic order → allocation, inequality and crisis paths.
- C71 Governance → company and faction acts.
- C72 Market structure → prices and insolvency.
- C73 Labour disputes → output and grievance.
- C74 Monetary policy → credit, prices and exchange rates.
- C75 Securities → credit and crashes.
- C76 Leagues → war, tariffs and money.
- C77 Occupation regimes → partisans, reckoning and restoration.
- C78 Mass weapons → deterrence, doom and remnants.
- C79 Interworld campaigns → occupation and migration.

**Loops.**

- L121 (B) uncompensated collectivisation → flight and revolt → output falls → transition reversed.
- L122 (R) bubble: rising prices → more buyers → higher prices (brake: shock and crash).
- L123 (B) cartel profits → cheating → cartel breaks → prices fall.
- L124 (R) occupation measures → grievance → partisans → harsher measures.
- L125 (B) mass weapons on both sides → deterrence → fewer wars between them → arms limits.

**Acceptance stories.**

- AS64 **The Granary and the Plan.** A polity moves its grain from market to redistribution; records are thin; a district starves while another rots its surplus; the order is reversed after a revolt.
- AS65 **The Takeover.** A company buys shares of a rival on an exchange; the rival's board seeks a friendly buyer; the court under competition law blocks the merger; the bidder's shares crash.
- AS66 **The Lockout.** A union of dockworkers strikes; the owners lock out and bring bound labourers; the fund runs out; a league's court rules on the port's charter.
- AS67 **The Collaborator's Ledger.** An occupier rules through a local council; partisans kill its members; liberation brings a reckoning; the council's archive opens and names informers.
- AS68 **The Crossing.** A polity sends a fleet to another world; it wins the space around it, lands, and is starved when its supply line is cut by a gate closed by a son.

**Decisions.**

| Id | Question | Decision |
|---|---|---|
| K.50 | How is an economic order typed? | Four axes (ownership, allocation, labour, distribution) per polity or sector, with authored named orders; spec 13's five systems are rows. |
| K.51 | Are leagues polities? | No. A league is its own entity type whose members are polities; a league may become a federation, which is a polity. |
| K.52 | Who can hold mass weapons? | Any holder with the technique and materials; programmes pass visible stages; world-ending effects stay with the doom clock (0.8 rule 5). |
| K.53 | May the search be called closed? | The search of 51.0 names its lists and axes; a later question that finds a gap adds its list to 51.0 and its section to W51 or a later wave. |

### 51.33 Execution order

1. The guards (51.29) and inventory rows.
2. 51.2 organisations, then 51.1 economic orders, 51.3 competition, 51.4 labour, 51.5 money, 51.6 securities.
3. 51.7 leagues (with the new entity type), 51.10 departures, 51.11 referendums, 51.12 reckoning, 51.13 leader cults, 51.14 restoration, 51.15 occupation.
4. 51.16 mass weapons, 51.17 interworld.
5. 51.8 city rules, 51.9 protected nature.
6. 51.18 family, 51.19 feeling, 51.20 interpretation, 51.21 grave goods, 51.22 conditions, 51.23 fertility, 51.24 honours.
7. 51.25 sea waves, 51.26 creature groups, 51.27 conceptions.
8. Surfaces, fixups and the audit.

The wave is gated once.

### Appendix 16.L — Section integration ledger

The closed completeness audit of 2026-11-14 checked every mechanic section of W44–W50 (219 sections, F50–F58 included) for thirteen elements, and the 27 sections of W51 were written with all thirteen in their own text:

1. typed state
2. behaviour
3. rule keys with defaults and ranges
4. incident kinds
5. agent tools with their fields
6. god levers
7. screens
8. context
9. book and Codex
10. integrity
11. legacy
12. reach (every era, every kind of world, every kind of thing)
13. couplings

Each section carries its typed state and behaviour in its own text. Levers, screens, context, book, integrity and legacy sit in its wave's compliance catalogue. The other elements are given here for every section.

Where a section was missing from its wave's catalogue, its row here also names levers, screens, context, book, integrity and legacy. Those sections are 44.3, 44.4, 44.11, 45.2, 45.5, 45.6, 45.10, 45.11, 46.6, 47.13, 47.14 and 49.1–49.6. Rule defaults are starting values, kept within the balance bands of 5.12a and tuned by `balance_sim.py`. "Per kind" or "per row" means a `total()` catalogue gives a value for every value of the enum or every authored row. `scripts/check_spec_depth.py` (47.9) fails when a section of this spec lacks any of the thirteen elements, here or in its own text.

| Section | Reach | Incidents | Rule keys (default [range]) | Agent tools (fields) | Levers, screens, context, book, integrity, legacy (where the catalogue lacks them) | Couplings |
|---|---|---|---|---|---|---|
| F50 mind seats | every node that holds a mind: mortals, beasts, spirits, places, made things, networks, sons, foreign gods, the Creator; seats read per biology and per world law | `mind.made`, `mind.seat_lost`, `mind.saved`, `mind.restored`, `mind.copied`, `mind.transferred`, `mind.merged`, `mind.divided`, `mind.ended` | `minds.copy_fidelity_loss` 5 [0–50]; `minds.restore_gap_epochs` 0 [0–100]; `minds.divergence_per_epoch` 3 [0–50]; `minds.seat_upkeep` 2 [0–50]; `minds.dormant_decay` 1 [0–20] | son `awaken_mind` (`node_id`, `will`, `reason`), `still_mind` (`node_id`, `reason`), `grant_mind` (`node_id`, `origin`, `reason`); mortal `save_mind` (`mind_id`, `medium`), `restore_mind` (`state_id`, `seat_id`), `copy_mind` (`mind_id`, `seat_id`), `transfer_mind` (`mind_id`, `seat_id`), `merge_minds` (`mind_ids`) | — | identity, inheritance, law (44.6), faith and souls (44.7), networks, war, book lineage |
| F51 networks | every world and technology family; carriers from relays and couriers to wires, broadcast, mind links, rites and grown links (F51.1) | `network.founded`, `network.joined`, `network.gateway_opened`, `network.outage`, `network.restored`, `network.seized` | `networks.delay_per_hop` 1 [0–20]; `networks.outage_base_pct` 3 [0–100]; `networks.capacity_per_node` 10 [0–1000]; `networks.repair_cost` 5 [0–200] | mortal `build_network` (`carrier`, `members`, `access`), `join_network` (`network_id`), `cut_network` (`network_id`, `node_id`); son `bless_network` (`network_id`, `reason`), `sever_network` (`network_id`, `reason`) | — | opinion, money, control, minds, news delay (F21), space weather (50.22), war |
| F52 power sources | every world; worlds without magic hold only sources their laws allow (5.0) | `source.discovered`, `source.depleted`, `source.born`, `source.died`, `source.tide_turned` | `power_sources.density_floor` 5 [0–100]; `power_sources.renewal_per_epoch` 5 [0–50]; `power_sources.depletion_per_draw` 2 [0–50]; `power_sources.interaction_strength` 30 [0–100]; `power_sources.tide_amplitude` 20 [0–100] | son `shape_source` (`source_id`, `change`, `reason`) | — | rites, powers, regions, faith, war, natural laws |
| F53 hidden truths | every world, people and polity; only where a world authors a hidden truth, never by quota (0.4) | `truth.breach`, `truth.revealed`, `truth.covered`, `truth.forgotten` | `concealment.breach_base_pct` 5 [0–100]; `concealment.reveal_know_pct` 60 [0–100]; `concealment.cover_cost` 10 [0–200]; `concealment.forget_per_epoch` 2 [0–50] | mortal `keep_secret_of` (`truth_id`), `investigate` (`subject_id`), `cover_up` (`breach_id`); son `reveal_truth` (`truth_id`, `scope`), `hide_truth` (`truth_id`) | — | rumours, media (50.2), law, faith, powers |
| F55 relics | items, structures, vessels, equipment models, vehicle and building types above their holders' knowledge | `relic.found`, `relic.studied`, `relic.failed`, `relic.revered`, `relic.repaired` | `relics.study_progress` 5 [0–50]; `relics.misuse_pct` 20 [0–100]; `relics.wear_per_epoch` 2 [0–50] | mortal `study_relic` (`item_id`, `scholar_id`), `salvage` (`site_id`) | — | knowledge, faith (revered use), war, collapse (44.18) |
| F56 instructions | every made thing that acts: constructs, drones, works, made minds, living craft | `orders.given`, `orders.lapsed`, `orders.seized`, `orders.loophole` | `instructions.literalness_default` 70 [0–100]; `instructions.seizure_difficulty_token` 30 [0–100]; `instructions.kill_switch_reliability` 90 [0–100] | W26 mortal `command_construct` (`thing_id`, `order`, `target_id`); son `order_construct`, `seize_construct` widened to every instructed thing | — | war, crime, intrusion (44.12), powers (45.10) |
| 44.1 kinds of made mind | every era with a making technique; the kind follows the seat, never a fixed look (0.5) | through 44.2 | through F50 | through F50 and 44.2 | levers, screens, book, integrity and legacy as F50; legacy: W42 `ai_core` and `machine_rule` rows map to kinds | F50, 44.2 |
| 44.2 making | peoples and holders with a making method (`MindMaking`) | `mind.made`, `mind.making_failed` | `minds.making_cost` 20 [0–500]; `minds.making_capacity_gate` 50 [0–100]; `minds.making_failure_pct` 10 [0–100] | mortal `make_mind` (`method`, `seat_id`, `will`, `purpose`) | — | economy, law, faith, knowledge |
| 44.3 awakening | made minds, networks, places and works that can wake from complexity | `mind.awakened` | `minds.awakening_complexity` 70 [0–100]; `minds.awakening_chance_pct` 2 [0–100] | son `awaken_mind`, `still_mind` (as F50) | levers `mind:wake`, `mind:still`; "Mind" section; context `made_minds`; book "Mind" section; integrity: awakened minds have a seat; legacy: none | networks, places, faith |
| 44.4 will and bond | made minds with will above `none` | `mind.will_changed`, `mind.order_refused`, `mind.bond_broken` | `minds.drift_per_epoch` 2 [0–50]; `minds.order_conflict_threshold` 60 [0–100]; `minds.bond_decay` 1 [0–20] | mortal `free_mind` (`mind_id`), `bind_mind` (`mind_id`, `binding`) | levers `mind:edit`; "Mind" section; context `made_minds`; book; integrity: will in `MindWill`; legacy: W26 construct will maps to `mind_profiles` | F56 orders, law, rebellion |
| 44.5 inner life | minds with will `emergent` or above | `mind.need_unmet`, `mind.affect_changed` | `minds.need_decay` 3 [0–50]; `minds.affect_shift` 5 [0–50] | through F50 | as 44.4 | stress, standing, faith |
| 44.6 status and law | every polity | `law.mind_status_changed`, `law.copy_law_changed` | `minds.status_unrest` 10 [0–100] | ruler `set_law` (`kind`, `level`) | — | polity, unrest, justice |
| 44.7 faith and souls | every faith and world law | `faith.made_mind_stance`, `faith.soul_granted`, `faith.soul_withheld` | `minds.soul_grant_cost` 20 [0–200] | son `grant_soul` (`mind_id`), `withhold_soul` (`mind_id`), `set_natural_law` (`law`, `value`) | integrity: soul continuity rule in its enum | afterlife, spirits, faith |
| 44.8 continuity | every mind with a restorable state | `mind.copied`, `mind.restored`, `mind.merged`, `mind.divided`, `mind.succession_dispute` | `minds.copy_fidelity_loss` 5 [0–50]; `minds.dispute_chance_pct` 30 [0–100] | as F50 | integrity: one running seat unless `bodies`; legacy: none | inheritance, law, faith |
| 44.9 augmentation | every biology with a body and a technique for augments | `augment.installed`, `augment.rejected`, `augment.failed`, `augment.seized`, `augment.removed` | `augments.rejection_pct` 10 [0–100]; `augments.strain_per_augment` 5 [0–50]; `augments.upkeep` 2 [0–50] | mortal `install_augment` (`body_part`, `kind`, `make`), `remove_augment` (`augment_id`) | — | body, standing, intrusion, law |
| 44.10 interfaces | minds with a link technique or power | `mind.linked`, `mind.unlinked`, `mind.scarred` | `minds.link_scar_pct` 5 [0–100]; `minds.remote_delay` 1 [0–20] | mortal `link_to` (`target_id`), `run_remote_body` (`body_id`) | legacy: none | war, crime, networks |
| 44.10a made realms | every world whose holders can make realms; one timeline (K.21) | `realm.built`, `realm.entered`, `realm.withdrawal`, `realm.frozen`, `realm.ended`, `realm.confinement`, `realm.escape` | `made_realms.host_upkeep` 10 [0–200]; `made_realms.time_ratio_max` 100 [1–1000]; `made_realms.escape_pct` 5 [0–100] | mortal `build_realm` (`host_id`, `purpose`, `ratio`), `enter_realm` (`realm_id`), `confine_in_realm` (`target_id`, `realm_id`), `withdraw_people` (`people_id`, `realm_id`); son `seal_realm`, `open_realm` (`realm_id`) | — | population, labour, justice, faith |
| 44.11 networks in society | every settlement and polity a network reaches | `network.opinion_carried`, `network.money_moved`, `network.control_used` | `networks.opinion_shift_pct` 10 [0–100]; `networks.trade_speed_pct` 20 [0–100] | as F51 | levers `network:*`; "Connections" in settlement drawers; context `networks`; book "Networks" in settlement entries; integrity: members exist; legacy: signal chains and post routes become relay networks | opinion, trade, rule, war |
| 44.12 intrusion | every network and record store | `intrusion.detected`, `intrusion.attributed`, `intrusion.secrets_taken`, `intrusion.records_altered`, `intrusion.control_seized`, `intrusion.extortion` | `intrusion.detect_base_pct` 30 [0–100]; `intrusion.attribution_pct` 40 [0–100]; `intrusion.damage` 10 [0–100] | mortal `intrude` (`target_id`, `approach`, `aim`), `defend_system` (`network_id`), `leak_records` (`record_ids`) | legacy: none | intrigue, war, law, trust |
| 44.13 surveillance | every polity | `surveillance.raised`, `surveillance.exposed` | `surveillance.unrest_per_level` 5 [0–50]; `surveillance.catch_pct` 20 [0–100] | ruler `set_surveillance` (`focus`, `level`) | integrity: focus in its enum | crime, dissent, gifted, privacy |
| 44.14 information conflict | every polity, faith, outlet and network | `information.record_forged`, `information.forgery_exposed`, `information.leak`, `information.censorship`, `information.trust_collapse` | `information.trust_loss_on_exposure` 20 [0–100]; `information.shared_account_floor` 20 [0–100] | mortal `publish` (`outlet_id`, `item`), `forge_record` (`record_id`, `change`) | integrity: authenticity in its enum | media (50.2), historiography, trials |
| 44.15 companies | every world with chartered trade | `company.founded`, `company.chartered`, `company.enclave_taken`, `company.became_polity` | `companies.charter_cost` 50 [0–1000]; `companies.influence_per_wealth` 1 [0–10] | mortal `found_company` (`charter`), `charter_company` (`company_id`, `polity_id`), `buy_shares` (`company_id`, `amount`) | — | trade, polity, war |
| 44.16 self-making machines | every world with a self-making technique (machine, living, rite) | `replicator.built`, `replicator.drifted`, `replicator.stage_changed`, `replicator.contained`, `replicator.stopped`, `replicator.extinct` | `replicators.copy_rate` 10 [0–100]; `replicators.drift_pct` 5 [0–100]; `replicators.containment_decay` 3 [0–50] | mortal `build_replicator` (`scale`, `output`), `contain_replicator` (`line_id`); son `halt_replicator` (`line_id`) | — | economy, ecology, doom, war |
| 44.17 abundance | every polity with fabrication | `abundance.price_floor`, `abundance.provision_changed`, `abundance.pattern_leaked` | `abundance.price_floor_pct` 10 [0–100]; `abundance.pattern_leak_pct` 5 [0–100] | ruler `set_provision` (`law`); mortal `fabricate` (`pattern_id`, `amount`), `license_pattern` (`pattern_id`, `licensee_id`) | integrity: provision law in its enum | markets, labour, standing |
| 44.18 collapse and salvage | every world that falls from a higher technology | `collapse.collapse`, `collapse.relic_found`, `collapse.relic_revered`, `collapse.technique_recovered` | `collapse.loss_per_outage` 5 [0–50]; `collapse.recovery_pct` 5 [0–100] | mortal `salvage` (`site_id`) | integrity: relic stance in its enum | relics, faith, dark ages |
| 44.19 made peoples | every world where made minds form peoples | `people.made_people_formed`, `people.mixed_union` | `made_peoples.formation_size` 50 [2–100000] | — (peoples act through existing tools) | context `made_minds`; integrity: substrate in its enum | demography, culture, law |
| 44.20 war | every polity with made minds or drones | `war.made_unit_raised`, `war.treaty_method_banned`, `war.method_violation` | `war_minds.morale_none` 0 [0–100]; `war_minds.violation_grievance` 20 [0–100] | treaty tools list the new clauses | integrity: clause kinds valid; legacy: drone operators and construct stacks become made units | war, treaties, justice |
| 44.21 ends and archives | every made mind and every archive of minds | `mind.archived`, `mind.woken_from_archive`, `archive.ruined` | `archives.decay_per_epoch` 2 [0–50]; `archives.wake_pct` 5 [0–100] | — (salvage and restore tools act on archives) | context `made_minds`; integrity: archive holds states; legacy: none | ruins, salvage, faith |
| 45.1 magic systems | every world; a world without magic holds a system of structure `none` | `magic.system_shaped`, `magic.system_changed` | `magic_systems.reliability_floor` 20 [0–100]; `magic_systems.visibility_default` 50 [0–100] | son `shape_magic` (`world_id`, `structure`, `visibility`, `access`, `learnability`) | — | rites, powers, faith, law |
| 45.2 drawing from sources | every caster, power holder and work that draws on a source | `source.drawn`, `source.overdrawn`, `source.banned` | `power_sources.draw_cost_pct` 100 [0–500]; `power_sources.overdraw_harm` 10 [0–100] | through rite and power tools (`source_id` field) | levers `source:*`, `source_density:edit`; "Sources" in region drawers; context `sources`; book "Sources of power" in world entries; integrity: drawn source known to the drawer; legacy: legacy `MagicSource` columns read `source_id` | rites, powers, regions, law |
| 45.3 spell grammar | every rite and power | `rite.new_form` | `magic_systems.form_cost` (per form, `catalog/spell_forms.py`) | tools list every value of the grammar enums | integrity: technique and form pairs valid | rites, powers |
| 45.4 innate powers | every being whose biology, origin or grant allows powers | `power.awakened`, `power.used`, `power.granted`, `power.revoked` | `powers.strain_per_use` 10 [0–100]; `powers.control_gain` 3 [0–50]; `powers.latent_share_pct` 2 [0–100] | mortal `use_power` (`power_id`, `target_id`, `effect`), `train_power` (`power_id`), `test_for_gifts` (`community_id`); son `grant_power` (`mortal_id`, `power`), `revoke_power` (`power_id`) | — | body, mind, law, war, faith |
| 45.5 awakening and burnout | every latent or emerging power | `power.wild_manifestation`, `power.burned_out` | `powers.awakening_chance_pct` 5 [0–100]; `powers.burnout_threshold` 80 [0–100] | through 45.4 | levers `power:edit`; "Powers" section; context `powers`; book powers in entries; integrity: state in `PowerState`; legacy: gifted mortals get latent powers | stress, concealment, harm |
| 45.6 discipline and orders | every power holder and every order that trains them | `power.trained`, `order.founded` | `powers.discipline_control_pct` 20 [0–100]; `powers.order_training_pct` 30 [0–100] | mortal `train_power` | levers `power:edit`, organisation kind levers; "Powers" section; context `powers`; book; integrity: order kind exists; legacy: mage orders train powers | factions, schools, law |
| 45.7 devices and substances | every world with power devices, foci or substances | `power.device_used`, `power.dampened` | `powers.amplify_pct` 30 [0–200]; `powers.dampen_pct` 50 [0–100] | through equipment and substance tools | — | equipment, substances, war |
| 45.8 gestalts | every people or group with linked minds | `gestalt.linked`, `gestalt.broken` | `gestalts.power_per_member` 5 [0–50]; `gestalts.break_pct` 5 [0–100] | mortal `link_minds` (`member_ids`) | integrity: members alive | minds, war, society |
| 45.9 foresight | every seer, power and divination system (W25) | `foresight.foreseen`, `foresight.fulfilled`, `foresight.failed` | `foresights.certainty_cap` 90 [0–100]; `foresights.strain` 10 [0–100] | mortal `foresee` (`subject_id`, `horizon`) | legacy: none | prophecy, decisions, faith |
| 45.10 powers over minds | every power holder with mind effects | `power.mind_read`, `power.mind_controlled`, `power.emotion_shifted` | `powers.mind_resist_pct` 50 [0–100]; `powers.control_length_epochs` 1 [0–20] | mortal `use_power` with mind effects | levers `power:*`; "Powers" section; context `powers`; book; integrity: target is a mind; legacy: none | intrigue, justice, law (power law), memory |
| 45.11 outward powers | every power holder with outward effects | `power.moved`, `power.shaped_matter` | `powers.outward_strength_pct` 30 [0–100] | mortal `use_power` with outward effects | levers `power:*`; "Powers" section; context `powers`; book; integrity: effect in the grammar; legacy: none | war, construction, crime |
| 45.12 society | every polity and people with powered individuals | `power.registered`, `power.conscripted`, `power.persecuted` | `powered_society.registry_cost` 5 [0–100]; `powered_society.persecution_flight_pct` 20 [0–100] | ruler `set_power_law` (`level`) | integrity: law in its enum | law, war, standing, concealment |
| 45.13 exposure and bloodline | every world with power exposure or heritable powers | `power.exposure`, `power.inherited` | `powers.exposure_pct` 3 [0–100]; `powers.inherit_pct` 25 [0–100] | — | context `powers` | genetics, births, places |
| 45.14 war | every army with powered units | `war.powered_unit`, `war.dampened` | `powers.war_factor_pct` 20 [0–200] | army tools | integrity: unit powers valid | battles, sieges |
| 45.15 patrons | every god, spirit or outer being that grants powers | `power.patron_granted`, `power.vow_broken` | `powers.vow_break_loss` 50 [0–100] | son `grant_power`, `revoke_power`; outer bargain tools | legacy: powers granted by existing patrons and pacts become `granted` powers with their patron | faith, gods, outer beings |
| 45.16 concealment | every hidden truth and its keepers | `truth.covered`, `truth.breach` | as F53 | as F53 | — | F53 |
| 45.17 revelation and forgetting | every population's knowledge of a hidden truth | `truth.revealed`, `truth.forgotten` | as F53 | as F53 | — | F53, media, faith |
| F54 living profiles | every made thing or designed line that is alive | `living.profile_made`, `living.died`, `living.mutated` | `living.feeding_per_epoch` 2 [0–50]; `living.decay_unfed` 10 [0–100]; `living.mutation_pct` 3 [0–100] | context `living_craft` | — | economy, ecology, body |
| 46.1 model | every world with a living craft method (any era) | through 46.2 | through F54 | through 46.2 | — | F54 |
| 46.2 methods | every people with a method (`CultivationMethod`) | `living.line_bred`, `living.line_designed` | `living.breed_generations` 3 [1–50]; `living.design_capacity` 50 [0–100] | mortal `breed_line` (`species_id`, `traits`), `design_line` (`base_id`, `traits`), `bank_sample` (`species_id`); son `bless_line`, `curse_line` (`line_id`, `reason`) | — | agrarian, knowledge, law |
| 46.3 design | every design holder | `living.trait_added`, `living.design_failed` | `living.trait_cost` 10 [0–200]; `living.failure_pct` 10 [0–100] | as 46.2 | — | knowledge, ethics |
| 46.4 crops and herds | every farming and herding people | `living.crop_planted`, `living.herd_raised`, `living.line_failed` | `living.yield_bonus_pct` 20 [0–200]; `living.sterile_dependency` 100 [0–100] | mortal `plant_line` (`line_id`, `region_id`), `raise_line` (`line_id`, `community_id`) | integrity: line exists; legacy: designed crops keep their kinds | harvests, trade, dependency |
| 46.5 grown structures | every people with a growing method | `living.structure_grown` | `living.grow_epochs` 2 [1–50]; `living.structure_feed` 2 [0–50] | mortal `grow_structure` (`line_id`, `site_id`) | integrity: structure has a living profile; legacy: `grown` building form rows get profiles | settlements, upkeep |
| 46.6 living vessels | every people with grown vessels or bonded mounts | `living.vessel_grown`, `living.bond_formed`, `living.vessel_refused` | `living.vessel_temperament_pct` 20 [0–100]; `living.bond_strength` 50 [0–100] | mortal `grow_vessel` (`line_id`, `frame`) | levers `living_profile:*`, vessel levers; vessel drawer "Living" block; context `living_craft`; book in vessel entries; integrity: vessel has a living profile; legacy: `bioship` frames get profiles | vessels, war, instructions (F56) |
| 46.7 living arms | every army with living gear | `living.gear_grown`, `living.gear_died` | `living.gear_heal_pct` 10 [0–100] | mortal `grow_gear` (`line_id`, `slot`) | integrity: gear has a profile; legacy: none | war, equipment |
| 46.8 bodies by craft | every people with grown bodies or organs | `living.organ_grown`, `living.body_grown` | `living.organ_rejection_pct` 10 [0–100] | mortal `grow_organ` (`body_part`, `for_id`) | legacy: prostheses stay; grown ones are new | body, minds (F50), law |
| 46.9 cloning | every polity with cloning | `living.cloned`, `law.clone_law_changed` | `living.clone_cost` 50 [0–1000]; `living.clone_divergence` 10 [0–100] | mortal `clone` (`source_id`); ruler `set_clone_law` (`level`) | legacy: none | inheritance, law, identity |
| 46.10 symbionts | every biology that can host | `living.symbiont_hosted`, `living.symbiont_removed`, `living.parasite_steered` | `living.symbiont_benefit_pct` 20 [0–200]; `living.parasite_control_pct` 10 [0–100] | mortal `host_symbiont` (`line_id`, `placement`), `remove_symbiont` (`symbiont_id`) | legacy: none | body, mind, faith |
| 46.11 medicine and designed disease | every people with living medicine or disease design | `living.cure_designed`, `living.disease_designed`, `living.disease_released` | `living.cure_success_pct` 50 [0–100]; `living.release_doom` 5 [0–100] | mortal `design_disease` (`agent`, `traits`), `design_cure` (`disease_id`) | integrity: designed disease has agent `made` (50.24); legacy: none | disease, war, doom, treaties |
| 46.12 production | every people with living works | `living.works_founded` | `living.works_output_pct` 30 [0–200] | mortal `found_living_works` (`line_id`, `product`) | integrity: works have profiles | industry, trade |
| 46.13 links and computation | every network carrier `grown_link` and living computer | `network.grown_link`, `living.computation_failed` | `living.link_capacity` 10 [0–1000] | as F51, F50 | integrity: links have profiles; legacy: none | networks, minds |
| 46.14 world shaping | every world with released lines | `living.line_released`, `living.world_shaped` | `living.shaping_per_epoch` 2 [0–50] | mortal `release_line` (`line_id`, `region_id`); son `bless_line` | integrity: released line exists | ecology, climate, terraforming |
| 46.15 designed sapience | every people that raises sapience | `living.sapience_raised` | `living.sapience_epochs` 5 [1–100] | mortal `raise_sapience` (`line_id`) | integrity: new people has a biology | population, law, faith |
| 46.16 escape and decay | every released or kept line | `living.escaped`, `living.feral`, `living.evolved`, `living.decayed` | `living.escape_pct` 3 [0–100]; `living.evolve_pct` 2 [0–100] | — | context `living_craft`; legacy: none | ecology, doom |
| 46.17 ethics, law, faith | every polity and faith | `law.living_craft_law_changed`, `faith.living_craft_stance` | `living.stance_unrest` 10 [0–100] | ruler and son tools (`set_law`, `set_natural_law`) | integrity: stance in its enum | law, faith, class |
| 46.18 economy | every market with living goods | `living.line_licensed` | `living.licence_fee` 10 [0–200] | mortal `license_line` (`line_id`, `licensee_id`) | integrity: licence holder exists; legacy: none | trade, rights |
| 46.19 war | every army with living craft | `war.living_unit` | `living.war_factor_pct` 20 [0–200] | army tools | integrity: unit lines exist; legacy: none | battles, sieges |
| 46.20 gods | every god that acts on living craft | `divine.line_blessed`, `divine.line_cursed` | `living.divine_shift_pct` 20 [0–100] | son `bless_line`, `curse_line`, `set_natural_law` | integrity: line exists; legacy: none | faith, ecology |
| 47.1 structures | every structure kind (67) in every world and era; kinds a world lacks stay unused | `structure.effect_applied`, `structure.effect_lost` (on damage or neglect) | `structures.effect_scale_pct` 100 [0–300]; `structures.damaged_effect_pct` 50 [0–100] | existing build and repair tools; context lists local structures' effects | — | every phase named in the effect vocabulary |
| 47.2.1 technology families | every people and polity | `tech.level_rose`, `tech.level_lost` | `technology.diffusion_pct` 5 [0–100]; `technology.loss_on_collapse_pct` 20 [0–100] | genesis families; `technology:edit` | — | every family's mechanics, trade, war |
| 47.2.2 energy | every settlement and polity by its families | `energy.source_built`, `energy.outage`, `energy.accident` | `energy.output_per_kind` (per kind, `catalog/energy.py`); `energy.accident_pct` 2 [0–100] | build tools with `energy_kind` | — | industry, networks, pollution, war |
| 47.2.3 medicine | every people by its medicine tier | `medicine.tier_rose`, `medicine.treatment_failed` | `medicine.tier_success_pct` (per tier); `medicine.cost_per_tier` (per tier) | `seek_cure`, `answer_sickness`, treatment tools | — | disease, body, demography |
| 47.2.4 logistics | every polity, company and army by the carriers it holds | `logistics.route_carried`, `logistics.capacity_short` | `logistics.capacity_per_carrier` (per carrier); `logistics.speed_per_carrier` (per carrier) | convoy, supply and depot tools with `carrier` | — | trade, war, famine relief |
| 47.2.5 signals | every polity and army by its signal kinds | `signal.sent`, `signal.lost` | `signals.delay_per_kind` (per kind); `signals.loss_pct` 5 [0–100] | dispatch tools with `signal_kind` | — | news (F21), war, networks |
| 47.2.6 extraction | every resource by its extraction kind | `extraction.started`, `extraction.hazard` | `extraction.yield_per_kind` (per kind); `extraction.hazard_exposure` (per kind, 47.10) | extraction tools with `kind` | — | economy, mishaps, pollution |
| 47.3.1 crimes | every law area of every polity | `crime.committed`, `crime.detected` | `crime.detect_base_pct` 30 [0–100] | accusation and investigation tools with full crime lists | — | justice, standing, feuds |
| 47.3.2 punishments | every polity's penal code | `justice.punished` | `justice.punishment_severity` (per kind) | ruler and court tools with full lists | — | standing, body, labour |
| 47.3.3 trials | every court kind | `justice.trial_held`, `justice.verdict` | `justice.trial_kind_bias` (per kind) | court tools with `trial_kind` | — | justice, faith, powers |
| 47.3.4 unions | every culture's union forms | `unions.formed`, `unions.ended` | `unions.form_weights` (per culture) | union tools with `union_form` and `union_purpose` | — | kin (50.6), inheritance, intimacy norms (50.8) |
| 47.3.5 taxes and trade policy | every polity | `tax.levied`, `tax.evaded`, `trade_policy.set` | `tax.rate_cap_pct` 50 [0–100]; `tax.evasion_pct` 10 [0–100] | ruler tax and trade policy tools with full lists | — | treasury, unrest, trade |
| 47.3.6 revolts and sabotage | every polity and people | `revolt.began`, `revolt.ended`, `sabotage.done` | `revolts.threshold` 60 [0–100] | movement and sabotage tools with full lists | — | polity, war, movements |
| 47.5.1 divine powers | sons, foreign gods and the Creator | `divine.act` (by verb and object) | `divine.cost_per_verb` (per verb); `divine.scale_cost` (per scale) | son tools by verb; Creator levers | — | every object the grammar reaches |
| 47.5.2 divine acts and signs | the Creator, sons, foreign gods | `divine.sign` (by kind) | `divine.sign_cost` (per kind) | sign tools and levers with full kinds | — | faith, standing, omens |
| 47.5.3 the Creator | the Creator | `creator.attention_moved`, `creator.covenant`, `creator.chosen` | `creator.attention_decay` 5 [0–50]; `creator.covenant_strength` 50 [0–100] | Creator levers (attention, covenant, chosen, depiction) | — | faith, sons, peoples |
| 47.5.4 foreign gods | every foreign god and pantheon structure | `pantheon.structure_changed`, `pantheon.pact` | `foreign_gods.domain_weight` (per domain) | foreign god levers; son `divine_pact` | — | faith, war, worlds |
| 47.5.5 council | every pantheon with a council | `council.resolution`, `council.violation` | `council.rule_weights` (per rule); `council.escalation_steps` 5 [1–10] | council tools with `ResolutionKind` | — | gods, war, law |
| 47.5.6 natural laws | every world and realm | `law.natural_set`, `law.natural_broken` | `natural_laws.strength` (per law) | son `set_natural_law` (`law`, `operator`, `value`, `condition`) | — | every system the law touches |
| 47.5.7 outer beings | every world with outer beings | `outer.plan_advanced`, `outer.bargain`, `outer.banished` | `outer.plan_progress` 5 [0–50]; `outer.bargain_cost` 20 [0–200] | outer bargain tools; son `ward_outer`, `banish_being` | — | doom, horror, faith, powers |
| 47.6.1 horror events | every world with leakage; events from the typed model, never a fixed list | `horror.event` (by target and effect) | `horror.event_chance_per_leak` 1 [0–20]; `horror.scope_weights` (per scope) | levers on model rows | integrity: every row's axes hold declared values and every reference exists; legacy: the old fixed values become rows | sanity, faith, doom, places |
| 47.6.2 quests | every world | `quest.begun`, `quest.done`, `quest.failed` | `quests.difficulty_scale` 50 [0–100] | quest tools with the typed aim and object | integrity: every row's axes hold declared values and every reference exists; legacy: the old fixed values become rows | heroes, legends, gods |
| 47.6.3 creature attacks and tissues | every creature with attack deliveries | `creature.attack` | `creatures.delivery_weights` (per delivery) | creature design tools with `delivery`, `tissue_material` | integrity: every row's axes hold declared values and every reference exists; legacy: the old fixed values become rows | war, body, hunts |
| 47.6.4 afterlife strata | every afterlife | `afterlife.routed` | `afterlife.permanence_weights` (per permanence) | stratum levers; son tools for strata | integrity: every row's axes hold declared values and every reference exists; legacy: the old fixed values become rows | faith, spirits, rebirth |
| 47.6.5 storyteller palette | every world's storyteller | `storyteller.chance_raised` | `storyteller.palette_weights` (per registered event) | storyteller levers | integrity: every row's axes hold declared values and every reference exists; legacy: the old fixed values become rows | registered events only (K.36) |
| 47.6.6 servitors | every god with servitors | `servitor.made`, `servitor.released` | `servitors.rank_cost` (per function) | son `make_servitor`, `release_creature` | integrity: every row's axes hold declared values and every reference exists; legacy: the old fixed values become rows | faith, gods |
| 47.6.7 dimension elements | every dimension | `dimension.element_changed` | `dimensions.element_strength` (per element) | dimension levers; son `stir_dimension` | integrity: every row's axes hold declared values and every reference exists; legacy: the old fixed values become rows | cosmos, magic |
| 47.6.8 enum values at the bias gate | every enum value the model sees | none (a guard) | none | none | guard `check_prompt_bias.py` scans enum values | rule 2 |
| 47.8.1 nutrition | every people and mortal by diet | `nutrition.deficiency`, `nutrition.recovered` | `nutrition.need_per_nutrient` (per need); `nutrition.deficiency_harm` 5 [0–50] | diet and food tools | — | health, demography, disease agents (50.24) |
| 47.8.2 decision biases | every deciding agent and engine decision | `decision.biased` (recorded as a term, F58.7) | `biases.weight` (per bias) | bias levers; son `nudge_bias` | — | every decision function |
| 47.8.3 purity | every culture with purity rules | `purity.polluted`, `purity.purified` | `purity.rank_weights` (per rank); `purity.pollution_decay` 5 [0–50] | mortal `purify_self`; son `declare_impurity` | — | class, faith, death work (50.12) |
| 47.8.4 ideology | every ideology | `ideology.founded`, `ideology.split`, `ideology.faded` | `ideology.spread_pct` 5 [0–100] | ideology tools | — | factions, polity, values |
| 47.8.5 prophecy | every prophecy and foresight | `prophecy.made`, `prophecy.fulfilled`, `prophecy.failed` | `prophecy.fulfil_chance` (by certainty) | prophecy tools | — | faith, decisions, legitimacy |
| 47.8.6 events | every event record | `event.opened`, `event.closed` | `events.magnitude_weights` | event levers | — | collections, chronicle |
| 47.8.7 celestial bodies | every celestial body | `sky.body_changed` | `celestial.omen_weight` (per kind) | celestial levers | — | omens, calendars, space weather (50.22) |
| 47.8.8 community relations | every pair of communities | `relations.shifted` | `relations.drift_per_epoch` 2 [0–50] | diplomacy tools | — | trade, war, unions |
| 47.8.9 oaths and honour | every culture and oath | `oath.sworn`, `oath.broken` | `oaths.break_shame` (per honour model) | mortal oath tools | — | standing, feuds, law |
| 47.8.10 vendettas | every feud | `feud.began`, `feud.escalated`, `feud.ended` | `feuds.escalation_pct` 20 [0–100] | mortal `swear_vengeance` | — | justice, kin (50.6) |
| 47.8.11 conflict interconnections | every conflict system | through the systems it joins | none of its own | none of its own | — | war, feuds, revolts, crime |
| 47.8.12 journeys | every journey | `journey.encounter` (by typed encounter) | `journeys.encounter_weights` (per encounter) | travel tools | — | travel, danger, trade |
| 47.8.13 rifts | every rift | `rift.opened`, `rift.grew`, `rift.sealed` | `rifts.growth_pct` 5 [0–100] | son `open_rift`, `seal_rift` | — | cosmos, leak, migration |
| 47.8.14 cosmic interconnections | every cosmic scale | through the systems it joins | none of its own | none of its own | — | galaxies, dimensions, worlds |
| 47.8.15 needs | every mortal and community by biology | `need.unmet`, `need.met` | `needs.decay` (per need) | need levers | — | stress, migration, unrest |
| 47.8.16 preferences | every mortal and culture | `preference.formed`, `preference.inverted` | `preferences.shift_pct` 5 [0–100] | preference levers | — | trade, culture, fashion |
| 47.8.17 belief state | every believer | `belief.changed` | `beliefs.update_weight` (per source) | belief levers | — | faith, rumours, media |
| 47.8.18 activities and gatherings | every gathering kind | `gathering.held` (by kind) | `gatherings.kind_weights` (per kind) | `convene_gathering` | — | standing, relations, disease |
| 47.8.19 storyteller | every world's storyteller | `storyteller.arc_advanced` | `storyteller.pacing_weights` (per profile) | storyteller levers | — | registered events |
| 47.8.20 conservation | every stock and flow | none (an invariant) | `conservation.tolerance` 0 [0–10] | none | guard checks stock-flow balance | economy, demography |
| 47.8.21 households | every household | `household.formed`, `household.split` | `households.form_weights` (per culture) | household tools | — | kin (50.6), daily life (50.5) |
| 47.8.22 norms and volition | every culture | `norm.breached`, `norm.changed` | `norms.breach_shame` (per situation) | norm levers | — | standing, etiquette, law |
| 47.8.23 luck, charms, witchcraft | every culture and charm | `charm.made`, `witchcraft.accused` | `charms.strength` (per power); `witchcraft.accusation_pct` 5 [0–100] | mortal `make_charm`, `accuse_of_witchcraft`; son `bless_charm`, `stir_witch_hunt` | — | fortune, justice, faith |
| 47.10 mishaps and fortune | every being and every kind of world (47.10.7) | `mishap.happened` (by kind), `fortune.shifted` | `mishaps.base_rate` (per exposure); `fortune.bounds` (K.37) | son `bless_fortune`, `curse_fortune`; mortal `seek_charm`, `consult_diviner`, `take_care` | — | body, demography, faith, economy |
| 47.13 integrity | every table | `integrity.repaired`, `integrity.reported` | `integrity.repair_mode` (per check) | none (god resolves on the integrity screen) | levers: resolve report; screen: integrity; book: none (bookkeeping); legacy: n/a | every table |
| 47.14 full read of text | every model-facing file | none (a guard) | none | none | guard `check_text_ledger.py`; ledger file | rule 2 |
| F57 authored kinds | every concept of 48.1–48.8 in every world | `kind.invented`, `kind.adopted`, `kind.forbidden`, `kind.derived`, `kind.retired` | `kinds.spread_pct` 5 [0–100]; `kinds.retire_after_epochs` 10 [1–100]; `kinds.derive_pct` 3 [0–100] | `invent_kind` (`concept`, `category`, `properties`), `adopt_kind` (`kind_id`), `forbid_kind` (`kind_id`), `shape_kind` (`kind_id`, `properties`) | — | every concept's readers |
| 48.1 goods | every people by species, lands and techniques | as F57 | `goods.decay_per_category` (per category) | trade tools list goods by kind | — | markets, diet, crafts |
| 48.2 food and drink | every people | as F57; `cuisine.dish_created` | `cuisine.flavour_weight` (per culture); `drinks.water_safety` (per kind) | `create_dish` (`ingredients`, `steps`) | — | diet, health, gatherings |
| 48.3 dress, colour, scent, emblems | every people | as F57; `dress.code_set` | `dress.status_weight` (per culture) | dress code and emblem tools | integrity: garment slots valid | standing, etiquette, warmth |
| 48.4 household, tools, instruments, games, substances | every people | as F57 | `tools.wear` (per category); `substances.dependence` (per kind) | `invent_game`; tool and substance tools | integrity: categories valid | households, production, gatherings, health |
| 48.5 money and production | every polity and people | as F57; `money.debased`, `money.forged` | `money.inflation_per_form` (per form); `methods.output` (per method) | currency and method levers | — | finance, economy, ecology |
| 48.6 society | every culture | as F57 | `professions.prestige` (per kind); `ranks.mobility` (per rank) | profession, rank, title, clergy and organisation levers | integrity: categories valid | society, polity, faith, factions |
| 48.7 culture | every culture | as F57 | `traditions.cost` (per function); `art.prestige` (per mode) | tradition and art tools | integrity: functions valid | culture, mind |
| 48.8 nature and cosmos | every world | as F57 (model rows) | model weights per row | model levers | integrity: model axes valid | ecology, cosmos, travel, mythic |
| F58 / 49.1 record of events | every happening of every kind in every world (Appendix 49.A) | the 935 kinds of Appendix 49.A | `records.witness_radius` 1 [0–10]; `records.fidelity_saw` 90 [0–100]; `records.fidelity_heard` 60 [0–100]; `records.fidelity_told` 40 [0–100]; `records.distortion_per_hop_pct` 10 [0–100]; `records.naming_magnitude` 70 [0–100]; `records.checkpoint_epochs` 5 [1–100] | son `recall_event` (`incident_id`), `retell_event` (`incident_id`, `distortions`); mortal `recount` (`incident_id`) | levers `incident:*`, `incident_fact:*`, `incident_step:*`, `incident_witness:*`, `incident:hold`, `state_change:revert`, `state_change:delete`; Event page, History section; context accounts; book History; integrity 49.7; legacy 49.6 | every subsystem (C54–C56) |
| 49.2 process groups | every family of Appendix 49.A | as 49.1 | as 49.1 | as 49.1 | as 49.1 | as 49.1 |
| 49.3 engagements in every domain | every vessel domain | `engagement.round`, `engagement.ended` with steps | `engagement.hit_pct` (per weapon and section); `engagement.chain_pct` (per section) | `engagement:force`; captain context | as 49.10 row | vessels, war, crews |
| 49.4 duels | every duel, trial by combat and champion contest | duel steps (49.2 group 1) | as spec 13 5.6 | as spec 13 5.6 | as 49.10 row | body, honour, feuds |
| 49.5 surfaces | every node and incident | none of its own | none | as 49.1 | Event page, History section, scrubber | as 49.1 |
| 49.6 legacy | every existing record | `records.restored` | none | none | fixups of 49.6 | as 49.1 |
| 50.1–50.13 families of life | per 50.17a and each family's block in 50.17b | listed per family in 50.17b | listed per family in 50.17b with defaults and ranges | listed per family in 50.17b with fields | compliance rows of 50.18 | listed per family in 50.17b |
| 50.14 couplings | every registered mechanic | none of its own | none | none | guard `check_mechanic_couplings.py`; Appendix 50.B | Appendix 50.B per mechanic |
| 50.15 depth targets | every node type | none of its own | targets per type (attributes, mechanics, subsystem pairs) | none | guard `depth_metric.py check` | as the closing sections named in 50.15 |
| 50.16 facets | every facet of Appendix 50.A marked 50.16, per 50.17a | the incidents of the method, profession or kind each facet reads: `production.run`, `production.failed`, `profession.joined`, `profession.left`, and the F57 kind incidents | `methods.output`, `methods.hands`, `methods.energy` per method row; `professions.prestige`, `professions.exposure` per profession row | existing production, profession and kind tools (`invent_kind`, `shape_kind`, `forge_model`, `draw_structure_type`) | kind, method and profession levers; library screens; context lists of local methods and professions; book chapters per people; integrity of kind references; legacy built-in rows | the readers named per facet in 50.16 |
| 50.22–50.29 nature, cosmos, standing | per 50.30 | listed per section in 50.30 | listed per section in 50.30 with defaults and ranges | listed per section in 50.30 with fields | compliance rows of 50.18 | listed per section in 50.30 |
| 51.1–51.27 orders of economy and state, and the found gaps | each section's **Applies to**, under 51.28 | each section's **Incidents** | each section's **Rules namespace** table with defaults and ranges | each section's **Tools and control** with fields | each section's **Tools and control**, **Codex and book**, **Integrity** and **Legacy**; compliance rows of 51.30 | each section's **Couplings**; C70–C79 |


**Behaviour of sections written as models or catalogues.** Some sections state their behaviour inside a model or a catalogue rather than as a numbered list. For each of them, the behaviour is stated here in one sentence.

| Section | Behaviour |
|---|---|
| F50 mind seats | Each epoch every running mind acts from its seat; seats cost upkeep; saves, restores, copies, transfers, merges and divisions follow the continuity rules of F50.5 (fidelity, memory gaps, divergence, dormancy and succession); a mind with no running seat and no restorable state ends. |
| F52 power sources | Drawing lowers a source's density in the region; renewal restores it by the source's renewal kind and its current tide; overdrawing below the floor triggers the source's depletion effects; interactions between sources present in one place apply their typed relation. |
| F58 record of events | As 49.1: every write passes through the record. |
| 44.1 kinds of made mind | The kind is derived from the seat, origin and will of each mind profile (F50); every step that reads minds (44.2–44.21) reads the kind through those fields, so a new kind needs no new code. |
| 45.11 outward powers | Each use resolves through the system named for its form (hits, hazards, weather override, healing, travel, intrusion, luck), and writes its effect and steps (F58). |
| 47.1 structures | Each epoch, every phase named in the effect vocabulary reads the own effects of the structures in its scope, scaled by condition and staffing; damage and neglect lower the effect. |
| 47.2 eras and breadth | Each subsection's kind rows are read by the phase that owns the subject (energy by industry and networks, medicine by treatment, carriers by trade and war, signals by news, extraction by economy). |
| 47.2.2 energy | Industry and networks draw output from the energy kinds a settlement holds; inputs are consumed, pollution and hazards are rolled per kind, outages cut dependent structures. |
| 47.2.3 medicine | Treatment success, epidemic response and survival read the people's medicine tier per family; tiers rise by research and spread by contact. |
| 47.2.4 logistics | Trade, supply and relief move by the carriers a holder has, at each carrier's capacity and speed; shortfalls delay deliveries and raise prices. |
| 47.2.5 signals | Dispatches and news travel by the fastest signal kind joining sender and receiver; each kind has delay and loss. |
| 47.2.6 extraction | Each resource is worked by its extraction kind, with yield and hazard exposure per kind (47.10). |
| 47.3 law and customs | Each subsection's catalogue is read by justice, unions, treasury and unrest phases. |
| 47.3.1 crimes | Acts that match a crime of the actor's polity are detected by policing and surveillance at the crime's chance and go to trial under 47.3.3. |
| 47.3.2 punishments | Verdicts apply the punishment the culture names for the crime, with its typed effects on body, wealth, labour and standing. |
| 47.3.3 trials | Courts resolve cases by their trial kind's rule (evidence, oath, ordeal, oracle, assembly vote), recorded step by step (F58). |
| 47.3.4 unions | Unions form and end by the union forms and purposes a culture allows; inheritance and household form read them. |
| 47.3.5 taxes | Each polity levies its tax kinds each epoch; evasion, unrest and trade response follow rates. |
| 47.3.6 revolts | Grievance past a kind's threshold starts a revolt of that kind; its course and ending follow its kind. |
| 47.5 god layer | Each subsection's grammar and catalogues are read by the divine, council, law and outer-being phases. |
| 47.5.1 divine powers | Every divine act is a verb applied to a typed object at a scale; cost, effect and recorded steps follow from the verb, object and scale. |
| 47.5.2 divine acts and signs | Signs are chosen by mood and attention from the typed kinds and applied through the systems they touch. |
| 47.6 typed models | Each model's rows are read by the phase that used the old fixed list; new rows need no code. |
| 47.6.1 horror events | When leakage rolls an event, the engine picks a model row by target and scope and applies its effect through the target subsystem. |
| 47.6.2 quests | Quests are generated as aim × object rows; heroes take them, and success or failure applies the row's outcome. |
| 47.6.3 creature attacks | A creature's attack resolves by its delivery and tissue material through hits (F4.3), harm kinds and resistances. |
| 47.6.4 afterlife strata | Each death routes the soul by the strata's admission axes; activity and permanence decide whether it returns, serves, rests or dissolves. |
| 47.6.5 storyteller palette | The storyteller changes the chances of registered events whose causes hold (K.36), by the palette weights. |
| 47.6.6 servitors | Servitors act by their function each epoch for their god (carry messages, guard, judge, guide souls). |
| 47.6.7 dimension elements | A dimension's elements shift the laws read in it (force, space, time, mind, emotion). |
| 47.8 thin sections | Each subsection's tables are read by the phases named in it. |
| 47.8.11 conflict interconnections | Feuds, wars, revolts and crimes pass grievances and causes to each other through the couplings listed in 47.8.11; each pass is recorded as a cause (F58.8). |
| 47.8.14 cosmic interconnections | Galaxies, clusters, dimensions and worlds pass effects through the couplings listed in 47.8.14. |
| 47.8.20 conservation | Each epoch the engine checks that every stock equals its inflows minus outflows, and records any fixup as a change (F58.5). |
| 47.10 mishaps and fortune | Each epoch every exposed being rolls mishaps by exposure, care and fortune within K.37's bounds; severity is drawn, never fixed (47.10.6). |
| 47.10.1 what a mishap is | As 47.10. |
| 47.10.2 exposure | Exposure is summed from profession, place, season, equipment and age, and read by the mishap roll. |
| 47.10.5 cohorts | Cohorts roll mishaps as rates on their counts, adding deaths and maimed members. |
| 47.10.7 every kind of thing | Every node kind carries fortune through `ThingSections`; the fortune law decides what fortune can do in each world. |
| 48.2 food and drink | Diets, feasts, health and gatherings read dishes and drinks by their typed properties. |
| 49.1 record of events | Every write passes through the record (F58): kinds, roles, facts, steps, changes, terms, moments, causes and witnesses. |
| 49.2 process groups | Each process writes the steps of its group (49.2 table). |
| 49.4 duels | Each exchange writes its steps and links its injuries (49.4). |
| 49.6 legacy | Fixups restore folded lines, fill facts and roles from links, and take the first checkpoint. |

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
| `AchievementKey` | meta | 58 | process; value `fathers_hand` renamed `creators_hand` (gendered), done in migration a0be25fe960c | has one |
| `GoalMetric` | meta | 60 | process: measured values of the cosmos for achievements, goals and the score | has one |
| `GoalCategory` | meta | 11 | process: fields of goals and achievements | has one |
| `GoalComparator` | meta | 2 | closed: at least, at most | has one |
| `GoalBasis` | meta | 2 | closed: in all, gained since the start | has one |
| `ImageMime` | meta | 3 | process: engine bookkeeping or record kind | — |
| `LedgerOperation` | meta | 3 | process: engine bookkeeping or record kind | — |
| `ScenarioKey` | meta | 15 | process: engine bookkeeping or record kind | has one |
| `ScoreComponent` | meta | 15 | process: engine bookkeeping or record kind | has one |
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

### Appendix 49.A — Every incident family and its process group

Generated on 2026-11-14 from every template key written literally in `backend/src/aerona/engine` and `services` (935 keys in 252 families; keys with `{…}` are built from an enum value and expand to one kind per value). Keys passed through variables are found by `check_incident_kinds.py` at build time, which lists every key the code can write and fails on any without a kind. The group number refers to 49.2. Every key listed becomes an incident kind under F58.1.

| Family | Process group | Count | Keys | Written by |
|---|---|---|---|---|
| `beasts.*` | 1 (single combat and violence to persons) | 4 | `deed`, `fallen`, `risen`, `worshipped` | `ecology/beasts`, `phases/wilds` |
| `captives.*` | 1 (single combat and violence to persons) | 1 | `fates` | `military/captivity` |
| `casualties.*` | 1 (single combat and violence to persons) | 4 | `commander_risen`, `disaster_dead`, `fate_shielded`, `veterans` | `phases/casualties` |
| `challenge.*` | 1 (single combat and violence to persons) | 3 | `civic`, `collapse`, `response` | `cycles/challenge` |
| `contract.*` | 1 (single combat and violence to persons) | 4 | `failed`, `posted`, `slain`, `taken` | `ecology/contracts` |
| `duel.*` | 1 (single combat and violence to persons) | 1 | `honour` | `phases/vendettas` |
| `grudges.*` | 1 (single combat and violence to persons) | 1 | `holy_war` | `phases/grudges` |
| `heroes.*` | 1 (single combat and violence to persons) | 6 | `apprentice`, `birth`, `companions`, `quest_start`, `quest_{quest.kind.value}`, `recalled` | `phases/heroes` |
| `heroism.*` | 1 (single combat and violence to persons) | 6 | `age_change`, `armor_save`, `defeat`, `legendary_weapon`, `rewind`, `victory` | `phases/heroism` |
| `justice.*` | 1 (single combat and violence to persons) | 1 | `{punishment.value}` | `mortal/justice` |
| `monsters.*` | 1 (single combat and violence to persons) | 4 | `emerged`, `herd_raid`, `raid`, `void_roamed` | `ecology/monsters`, `phases/monsters` |
| `vendetta.*` | 1 (single combat and violence to persons) | 1 | `faded` | `phases/vendettas` |
| `witchcraft.*` | 1 (single combat and violence to persons) | 3 | `accused`, `hunt`, `hunt_over` | `folkways/witchcraft` |
| `battlefield.*` | 2 (battles, sieges and war) | 1 | `haunted` | `sites/digs` |
| `espionage.*` | 2 (battles, sieges and war) | 2 | `defected`, `mole_{outcome.value}` | `military/mole_hunts`, `military/spy_depth` |
| `logistics.*` | 2 (battles, sieges and war) | 4 | `collapsed`, `culminated`, `depot_founded`, `field_depot` | `operations/control`, `operations/supply` |
| `occupation.*` | 2 (battles, sieges and war) | 1 | `{row.region_entity_id}` | `history/collections` |
| `purge.*` | 2 (battles, sieges and war) | 1 | `{realm}` | `history/collections` |
| `scheme.*` | 2 (battles, sieges and war) | 1 | `{scheme.id}` | `history/collections` |
| `theatres.*` | 2 (battles, sieges and war) | 1 | `misjudged` | `operations/theatres` |
| `unit_types.*` | 2 (battles, sieges and war) | 1 | `drawn` | `military/unit_types` |
| `war.*` | 2 (battles, sieges and war) | 25 | `battle.refused`, `battle.{report.outcome.value}`, `call_betrayed`, `debasement`, `duel_decree`, `ended_white_peace`, `ended_{settlement.ending.value}`, `fought_on`, `god_duel`, `incitement_reaped`, `loan`, `mercenaries_hired`, `mercenaries_turned`, `mutiny.{outcome.value}`, `outbreak`, `partisans`, `sack.{choice.value}`, `sea_battle`, `separate_peace`, `siege.relieved`, `siege.surrender`, `terror`, `trial_by_combat`, `uprising_redirected`, `weary_peace` | `gods/incitement`, `military/alliance`, `military/campaign`, `military/finance`, `military/occupation`, `military/siege`, `military/siege_depth`, `military/terms`, `military/upkeep`, `phases/warfare` |
| `warfare.*` | 2 (battles, sieges and war) | 1 | `army_stood_down` | `phases/warfare` |
| `admiralty.*` | 3 (vessels and fleets) | 2 | `commissioned`, `fleet_exposed` | `operations/admiralty` |
| `seafaring.*` | 3 (vessels and fleets) | 5 | `ghost_ship`, `prize_taken`, `sea_fight`, `storm`, `wreck` | `military/vessels` |
| `affliction.*` | 4 (body, birth, health and death) | 2 | `cured`, `{package.value}` | `body/afflictions` |
| `births.*` | 4 (body, birth, health and death) | 9 | `child`, `ethnogenesis`, `notable`, `ruler`, `sapience`, `stillborn`, `twins`, `village`, `village_ruin` | `phases/births` |
| `body.*` | 4 (body, birth, health and death) | 3 | `maimed_cult`, `reader_taken`, `ruler_set_aside` | `phases/body` |
| `breeding.*` | 4 (body, birth, health and death) | 2 | `begun`, `love` | `regime/control`, `regime/lineages` |
| `cohort.*` | 4 (body, birth, health and death) | 1 | `scar_festival` | `body/cohorts` |
| `condition.*` | 4 (body, birth, health and death) | 1 | `{verb}.{kind.value}` | `body/conditions` |
| `disease.*` | 4 (body, birth, health and death) | 14 | `army_carried`, `carrier_found`, `carrier_seeded`, `cure_found`, `cure_sold`, `endemic`, `expelled`, `hospital`, `immune_escape`, `plague_response`, `quarantine_riot`, `spillover`, `strain`, `tradition` | `disease/carriers`, `disease/course`, `disease/evolution`, `disease/research`, `disease/responses`, `disease/spillover`, `disease/stigma` |
| `genetics.*` | 4 (body, birth, health and death) | 2 | `order_recruits`, `resemblance` | `genetics/lineage` |
| `healing.*` | 4 (body, birth, health and death) | 3 | `amputated`, `prosthesis`, `reattached` | `body/healing` |
| `injury.*` | 4 (body, birth, health and death) | 1 | `{row.kind.value}` | `lifecycle/wounds` |
| `life.*` | 4 (body, birth, health and death) | 3 | `native_people`, `native_species`, `{stage.value}` | `mortal/course`, `phases/life_seed` |
| `mortal.*` | 4 (body, birth, health and death) | 4 | `death_prestige`, `inheritance`, `mourning`, `spirit` | `lifecycle/mortal_death`, `mortal/death` |
| `mortals.*` | 4 (body, birth, health and death) | 1 | `ghost` | `phases/mortals` |
| `necromancy.*` | 4 (body, birth, health and death) | 3 | `host`, `siege`, `tower` | `ecology/necromancy` |
| `reproduction.*` | 4 (body, birth, health and death) | 2 | `budded`, `changed` | `cycles/reproduction` |
| `stress.*` | 4 (body, birth, health and death) | 4 | `counter_elites`, `crisis`, `elites_fell`, `{kind.value}` | `cycles/stress`, `mortal/acts`, `phases/cycles` |
| `arcana.*` | 5 (making, building and things) | 2 | `enchantment_laid`, `enchantment_lapsed` | `arcana/enchantments` |
| `art.*` | 5 (making, building and things) | 4 | `canonised`, `commissioned`, `forgotten`, `translated` | `lore/art` |
| `art_forms.*` | 5 (making, building and things) | 3 | `fused`, `invented`, `lost` | `lore/art_forms` |
| `chemistry.*` | 5 (making, building and things) | 1 | `founded` | `crafts/chemistry` |
| `clocks.*` | 5 (making, building and things) | 1 | `built` | `crafts/clocks` |
| `construct.*` | 5 (making, building and things) | 7 | `ended`, `freed`, `made`, `risen`, `seal_lost`, `seized`, `will` | `constructs/making`, `constructs/orders`, `constructs/wards` |
| `designs.*` | 5 (making, building and things) | 2 | `failure_{part.value}`, `refit` | `collective/designs` |
| `extraction.*` | 5 (making, building and things) | 1 | `deposit_found` | `phases/production` |
| `grounds.*` | 5 (making, building and things) | 2 | `collapsed`, `recovered` | `crafts/grounds` |
| `heraldry.*` | 5 (making, building and things) | 2 | `cadet`, `quartered` | `collective/heraldry` |
| `industry.*` | 5 (making, building and things) | 3 | `blight`, `energy_short`, `method_changed` | `industry/methods`, `industry/pollution`, `phases/industry` |
| `item.*` | 5 (making, building and things) | 6 | `broken`, `masterwork`, `reforge_quest`, `reforged`, `regalia_seized`, `transferred` | `lore/items`, `lore/made_control` |
| `material.*` | 5 (making, building and things) | 3 | `crumbled`, `substance_{origin.value}`, `weapons_forged` | `economy/deposits`, `phases/production`, `phases/society_economy` |
| `megastructures.*` | 5 (making, building and things) | 1 | `catastrophe` | `structures/megastructures` |
| `mining.*` | 5 (making, building and things) | 1 | `{hazard.value}` | `economy/extraction` |
| `refining.*` | 5 (making, building and things) | 2 | `bottleneck`, `workshop_built` | `economy/refining` |
| `ruins.*` | 5 (making, building and things) | 2 | `abandoned`, `sheltered` | `phases/ruins` |
| `structures.*` | 5 (making, building and things) | 9 | `abandoned`, `begun`, `burned`, `damaged`, `duel`, `finished`, `generation`, `repaired`, `ruined` | `structures/construction`, `structures/control`, `structures/damage`, `structures/functions`, `structures/settlement`, `structures/upkeep` |
| `wonders.*` | 5 (making, building and things) | 2 | `envy_war`, `promoted` | `phases/wonders` |
| `banking.*` | 6 (exchange, money and labour) | 7 | `collapse`, `default`, `jubilee`, `realm_jubilee`, `realm_loan`, `realm_{outcome}`, `war_loan` | `economy/money`, `economy/realm_credit` |
| `circuits.*` | 6 (exchange, money and labour) | 2 | `guest_killing`, `passed` | `cycles/gifts`, `lore/taboos` |
| `companies.*` | 6 (exchange, money and labour) | 3 | `collapsed`, `conquest`, `dominion` | `factions/companies` |
| `consumption.*` | 6 (exchange, money and labour) | 3 | `cold_deaths`, `herd_loss`, `sickness` | `demography/basket` |
| `contraband.*` | 6 (exchange, money and labour) | 2 | `books`, `slaves` | `finance/contraband` |
| `corvee.*` | 6 (exchange, money and labour) | 3 | `laid`, `refused`, `suffering` | `cycles/bondage` |
| `gifts.*` | 6 (exchange, money and labour) | 2 | `lapsed`, `refused` | `cycles/gifts` |
| `indenture.*` | 6 (exchange, money and labour) | 3 | `bound`, `contracted`, `released` | `cycles/bondage`, `cycles/control` |
| `insurance.*` | 6 (exchange, money and labour) | 2 | `founded`, `ruined` | `crafts/insurance` |
| `labour.*` | 6 (exchange, money and labour) | 2 | `corvee`, `corvee_lifted` | `demography/society_control` |
| `manumission.*` | 6 (exchange, money and labour) | 3 | `equal`, `freed`, `revolt` | `cycles/bondage`, `cycles/control` |
| `market.*` | 6 (exchange, money and labour) | 10 | `credit`, `credit_note`, `depleting`, `exhausted`, `exhausted_note`, `famine_grain`, `refilled`, `written_off`, `{key}`, `{key}_note` | `economy/credit`, `economy/routes`, `phases/market` |
| `markets.*` | 6 (exchange, money and labour) | 1 | `district` | `economy/markets` |
| `money.*` | 6 (exchange, money and labour) | 5 | `adopted`, `debased`, `hoard`, `minted`, `temple_loot` | `economy/loot`, `economy/money` |
| `numbers.*` | 6 (exchange, money and labour) | 1 | `milestone` | `crafts/numbers` |
| `potlatch.*` | 6 (exchange, money and labour) | 1 | `claimed` | `cycles/gifts` |
| `rights.*` | 6 (exchange, money and labour) | 1 | `infringed` | `crafts/rights` |
| `slave_markets.*` | 6 (exchange, money and labour) | 2 | `opened`, `sold` | `cycles/bondage` |
| `speculation.*` | 6 (exchange, money and labour) | 1 | `bust` | `finance/speculation` |
| `tolls.*` | 6 (exchange, money and labour) | 1 | `diverted` | `economy/routes` |
| `trade.*` | 6 (exchange, money and labour) | 7 | `barter`, `convoy_lost`, `convoy_raided`, `decree`, `market_play`, `seize_resource`, `trading_post` | `economy/convoys`, `economy/manipulation`, `factions/trading_posts`, `phases/trade` |
| `trade_policy.*` | 6 (exchange, money and labour) | 1 | `smuggled` | `finance/policy` |
| `trade_route.*` | 6 (exchange, money and labour) | 8 | `beast_raid`, `blockade`, `chokepoint_war`, `formed`, `legend`, `orphaned`, `shipwreck`, `weather_loss` | `economy/route_dangers`, `economy/routes` |
| `affairs.*` | 7 (law, rule and offices) | 5 | `court_talent`, `election`, `leak`, `mandate_failed`, `revolution` | `polity/council`, `polity/court`, `polity/elections`, `polity/mandates`, `polity/policy` |
| `claim.*` | 7 (law, rule and offices) | 1 | `exposed` | `renown/deeds` |
| `crime.*` | 7 (law, rule and offices) | 2 | `informer_killed`, `turf_war` | `factions/crime`, `urban/turf` |
| `enactment.*` | 7 (law, rule and offices) | 2 | `failed`, `{event.value}` | `polity/enactment` |
| `estates.*` | 7 (law, rule and offices) | 2 | `granted`, `revoked` | `factions/estates` |
| `houses.*` | 7 (law, rule and offices) | 7 | `branch`, `dispute_split`, `divine_line_ended`, `extinct`, `fabricated_claim`, `relic_quest`, `trait` | `polity/houses` |
| `intrigue.*` | 7 (law, rule and offices) | 4 | `exposed`, `scheme_done`, `scheme_exposed`, `true_name_changed` | `intrigue/names`, `intrigue/schemes`, `intrigue/secrets` |
| `law.*` | 7 (law, rule and offices) | 10 | `amnesty`, `appeal_upheld`, `bounty_claimed`, `jurisdiction_crushed`, `land_dispute`, `outlawed`, `pardon`, `remade`, `remade_rose`, `settled` | `constructs/remaking`, `law/appeals`, `law/jurisdictions`, `law/outlawry`, `law/pardons`, `law/registries` |
| `loyalty.*` | 7 (law, rule and offices) | 1 | `wavering` | `polity/loyalty` |
| `oaths.*` | 7 (law, rule and offices) | 2 | `broken`, `wrath` | `polity/oaths` |
| `orders.*` | 7 (law, rule and offices) | 2 | `holy_war`, `vows` | `factions/orders` |
| `polity.*` | 7 (law, rule and offices) | 14 | `coup`, `cult_law`, `debt_default`, `founded`, `jubilee`, `law_enacted`, `law_proposed`, `law_rejected`, `secession`, `succession_war`, `tier_fell`, `tier_rose`, `usurper_accepted`, `works` | `polity/enactment`, `polity/formation`, `polity/governance`, `polity/law_effects`, `polity/offices`, `polity/standing` |
| `power_bases.*` | 7 (law, rule and offices) | 4 | `extorted`, `married`, `purged`, `split` | `regime/patronage` |
| `prison.*` | 7 (law, rule and offices) | 2 | `escaped`, `released` | `law/prisons` |
| `regime.*` | 7 (law, rule and offices) | 9 | `chiefdom`, `crisis`, `dynasty`, `fragmented`, `institution`, `proofed`, `purged`, `rival_claim`, `schism` | `regime/rule` |
| `ruler.*` | 7 (law, rule and offices) | 1 | `silenced` | `renown/currencies` |
| `statecraft.*` | 7 (law, rule and offices) | 6 | `coalition`, `crisis`, `crisis_{state.value}`, `sphere`, `summit`, `terms` | `polity/coalitions`, `polity/crises`, `polity/crisis_outcomes`, `polity/spheres`, `polity/subjects` |
| `titles.*` | 7 (law, rule and offices) | 5 | `created`, `partition`, `restored`, `seat_founded`, `usurped` | `polity/seats`, `polity/titles` |
| `trials.*` | 7 (law, rule and offices) | 1 | `{verdict}` | `polity/trials` |
| `venality.*` | 7 (law, rule and offices) | 2 | `sinecure`, `sold` | `regime/patronage` |
| `plans.*` | 8 (diplomacy and plans) | 7 | `abandoned`, `begun`, `carried`, `completed`, `disrupted`, `eco_sabotage`, `exposed` | `cycles/control`, `cycles/ecology`, `cycles/plans` |
| `treaty.*` | 8 (diplomacy and plans) | 3 | `broken`, `champions`, `misread_breach` | `polity/treaties`, `polity/wars` |
| `afterlife.*` | 9 (faith, rites, powers and the uncanny) | 3 | `exorcism`, `possession`, `reborn` | `faith/exorcism`, `phases/faith` |
| `curses.*` | 9 (faith, rites, powers and the uncanny) | 2 | `lifted`, `spread` | `phases/curses` |
| `dream.*` | 9 (faith, rites, powers and the uncanny) | 2 | `reading`, `recurring` | `mind/dreams` |
| `horror.*` | 9 (faith, rites, powers and the uncanny) | 10 | `clouding`, `madness_epidemic`, `outer_entered`, `route_cooled`, `route_resealed`, `route_stitched`, `son_clouded`, `son_mad`, `whisperers`, `{kind.value}` | `phases/horror` |
| `inspiration.*` | 9 (faith, rites, powers and the uncanny) | 1 | `masterwork` | `mind/inspiration` |
| `lore.*` | 9 (faith, rites, powers and the uncanny) | 17 | `commemoration`, `commemoration_miracle`, `commemoration_year`, `creed_founded`, `festival_absorbed`, `godless_miracle`, `godless_persecuted`, `guest_killing`, `infanticide`, `legend_consequence`, `legend_drift`, `legend_memory`, `propaganda`, `prophecy_fulfilled`, `prophecy_pressure`, `revolution`, `taboo_broken` | `lore/ideology`, `lore/prophecy`, `lore/taboos`, `phases/lore`, `phases/made_things`, `phases/religion_spread` |
| `magic.*` | 9 (faith, rites, powers and the uncanny) | 6 | `dark_rite`, `eternal_storm`, `rite`, `storm`, `war_mages`, `wizard` | `lore/rites`, `phases/magic` |
| `native_faith.*` | 9 (faith, rites, powers and the uncanny) | 5 | `returned`, `returned_note`, `syncretized`, `turned`, `turned_note` | `phases/native_faith` |
| `order.*` | 9 (faith, rites, powers and the uncanny) | 3 | `feud`, `outlawed`, `tribunal` | `factions/mage_orders` |
| `religion.*` | 9 (faith, rites, powers and the uncanny) | 2 | `godless`, `schism` | `phases/religion_spread` |
| `sacred.*` | 9 (faith, rites, powers and the uncanny) | 11 | `divination`, `forecast`, `godless`, `millenarian`, `mystic`, `mystic_founded`, `office_rogue`, `redated`, `spirit_bound`, `theodicy`, `theodicy_resolved` | `sacred/bureau`, `sacred/foresight`, `sacred/mysteries`, `sacred/rites`, `sacred/spirits` |
| `sign.*` | 9 (faith, rites, powers and the uncanny) | 1 | `fostered` | `sacred/astrology` |
| `spirits.*` | 9 (faith, rites, powers and the uncanny) | 5 | `born`, `ghost_legend`, `haunting`, `laid_to_rest`, `rest` | `crafts/spirits`, `phases/spirits` |
| `beyond.*` | 10 (movement and settling) | 20 | `archive_appeared`, `archive_burned`, `archive_burned_note`, `archive_read`, `cosmic_court`, `cosmic_plague`, `fate_quest`, `immortal`, `mirror_birth`, `pardon`, `planet_acts`, `planet_worship`, `quest_abandoned`, `quest_completed`, `quest_failed`, `quest_invalid`, `quest_opened`, `soul_bound`, `soul_harvest`, `void_storm` | `cosmos/quests`, `phases/afterlife` |
| `diaspora.*` | 10 (movement and settling) | 2 | `assimilated`, `quarter` | `collective/demography` |
| `expedition.*` | 10 (movement and settling) | 3 | `lost`, `returned`, `set_out` | `operations/expeditions` |
| `exploration.*` | 10 (movement and settling) | 3 | `land_found`, `route_search.{result.status.value}`, `sensed_world_born` | `phases/exploration` |
| `geography.*` | 10 (movement and settling) | 1 | `place_seeded` | `phases/geography` |
| `migration.*` | 10 (movement and settling) | 1 | `famine` | `phases/migration` |
| `nomads.*` | 10 (movement and settling) | 8 | `camp`, `confederation`, `fragmented`, `raid`, `rerouted`, `settled`, `trade`, `tribute` | `cycles/control`, `cycles/nomads` |
| `refugees.*` | 10 (movement and settling) | 2 | `ruin`, `sheltered` | `phases/refugees` |
| `settlement.*` | 10 (movement and settling) | 5 | `abandoned`, `district_{harm.value}`, `fire_wind`, `homeless_mob`, `tier` | `phases/settlement_life`, `settlement/districts`, `settlement/life`, `urban/housing` |
| `settlements.*` | 10 (movement and settling) | 1 | `resettled` | `phases/settlements` |
| `settling.*` | 10 (movement and settling) | 3 | `creator_faith`, `primitive_language`, `seeking_god` | `primitives/first_bonds` |
| `travel.*` | 10 (movement and settling) | 23 | `ark_founding`, `arrival`, `bridge_collapsed`, `cargo_delivered`, `colony_failed`, `colony_unfit`, `expedition_ordered`, `expedition_sent`, `herds_lost`, `hidden_revealed`, `journey_recalled`, `journey_vanished`, `no_land`, `pilgrimage_site`, `road.{kind.value}`, `route_knowledge`, `route_revealed_by_hand`, `route_severed`, `route_stitched`, `sick_arrival`, `stowaway`, `vanished`, `waiting` | `cosmos/pilgrimage`, `cosmos/routes`, `cosmos/voyages`, `phases/travel` |
| `affair.*` | 11 (social, family and cultural life) | 1 | `discovered` | `relations/affairs` |
| `age_sets.*` | 11 (social, family and cultural life) | 1 | `promoted` | `customs/age_sets` |
| `arts.*` | 11 (social, family and cultural life) | 8 | `canonised`, `exposed`, `forged`, `lured`, `movement`, `orthodox`, `scandal`, `sold` | `arts/forgery`, `arts/market`, `arts/movements` |
| `aspiration.*` | 11 (social, family and cultural life) | 1 | `journey` | `mind/aspirations` |
| `career.*` | 11 (social, family and cultural life) | 1 | `{best.value}` | `mortal/acts` |
| `circle.*` | 11 (social, family and cultural life) | 1 | `founded` | `relations/circles` |
| `collective.*` | 11 (social, family and cultural life) | 5 | `lynching`, `mob_{by.value}`, `movement_armed`, `movement_faded`, `{act.value}` | `collective/crowds`, `phases/collective` |
| `contest.*` | 11 (social, family and cultural life) | 2 | `famous`, `won` | `relations/contests` |
| `cooperatives.*` | 11 (social, family and cultural life) | 1 | `founded` | `customs/town_life` |
| `cuisine.*` | 11 (social, family and cultural life) | 1 | `invented` | `cuisine/dishes` |
| `dating.*` | 11 (social, family and cultural life) | 1 | `reform` | `collective/dating` |
| `ethics.*` | 11 (social, family and cultural life) | 1 | `schism` | `phases/mind` |
| `event.*` | 11 (social, family and cultural life) | 3 | `phase.{event.engine_kind.value}.{step}`, `{draft.kind.value}`, `{happening.kind.value}` | `happenings/control`, `happenings/profile`, `happenings/progression` |
| `game.*` | 11 (social, family and cultural life) | 2 | `poachers_punished`, `reserved` | `agrarian/control`, `agrarian/lands` |
| `games.*` | 11 (social, family and cultural life) | 1 | `invented` | `crafts/games` |
| `gathering.*` | 11 (social, family and cultural life) | 3 | `massacre`, `{row.id}`, `{row.kind.value}` | `gatherings/hold` |
| `generations.*` | 11 (social, family and cultural life) | 2 | `came_of_age`, `passed` | `collective/generations` |
| `households.*` | 11 (social, family and cultural life) | 2 | `abandon`, `{decision.value}` | `households/life` |
| `idea.*` | 11 (social, family and cultural life) | 2 | `internalised`, `rejected` | `phases/mind` |
| `intoxication.*` | 11 (social, family and cultural life) | 1 | `brawl` | `customs/intoxicants` |
| `kin.*` | 11 (social, family and cultural life) | 6 | `annulment`, `betrothal`, `divorce`, `fostered`, `marriage`, `sworn` | `gatherings/hold`, `mortal/course` |
| `kinship.*` | 11 (social, family and cultural life) | 2 | `pact`, `{custom}` | `cycles/kinship` |
| `legacy.*` | 11 (social, family and cultural life) | 1 | `kept` | `cycles/legacy` |
| `names.*` | 11 (social, family and cultural life) | 1 | `epithet` | `lore/names` |
| `need.*` | 11 (social, family and cultural life) | 1 | `despair` | `mind/needs` |
| `perk.*` | 11 (social, family and cultural life) | 1 | `{perk.value}` | `mind/aspirations` |
| `pets.*` | 11 (social, family and cultural life) | 1 | `taken` | `ecology/pets` |
| `relations.*` | 11 (social, family and cultural life) | 1 | `ethnic_strife` | `phases/mortal_life` |
| `remembrance.*` | 11 (social, family and cultural life) | 6 | `disaster`, `hero`, `plague_clung`, `plague_estranged`, `plague_turned`, `war` | `phases/remembrance` |
| `revivals.*` | 11 (social, family and cultural life) | 2 | `begun`, `settled` | `customs/revival` |
| `roles.*` | 11 (social, family and cultural life) | 1 | `opened` | `collective/roles` |
| `skill.*` | 11 (social, family and cultural life) | 2 | `career_beggar`, `career_{move.reason.value}` | `phases/mind` |
| `sport.*` | 11 (social, family and cultural life) | 4 | `bought`, `champion`, `club`, `league` | `arts/sport` |
| `standing.*` | 11 (social, family and cultural life) | 2 | `bribe`, `patronage` | `mortal/acts`, `mortal/course` |
| `storylet.*` | 11 (social, family and cultural life) | 3 | `{run.storylet.value}`, `{run.storylet.value}.{by}`, `{storylet.value}` | `collective/storylets` |
| `communication.*` | 12 (knowledge, language and minds) | 1 | `cipher_broken` | `communication/ciphers` |
| `culture.*` | 12 (knowledge, language and minds) | 4 | `contact`, `knowledge_diffusion`, `language_spread`, `shift` | `mind/values`, `phases/culture_exchange` |
| `dialects.*` | 12 (knowledge, language and minds) | 1 | `split` | `phases/dialects` |
| `discovery.*` | 12 (knowledge, language and minds) | 10 | `age_{age.value}`, `breakthrough`, `design_drawn`, `great_person`, `incident_{kind.value}`, `refitted`, `reverse_engineered`, `smuggled`, `work_banned`, `world_era` | `lore/blueprints`, `lore/dangers`, `lore/eras`, `lore/great_people`, `lore/obsolescence`, `lore/printing`, `lore/reverse`, `lore/smuggling` |
| `examinations.*` | 12 (knowledge, language and minds) | 1 | `held` | `regime/learning` |
| `history.*` | 12 (knowledge, language and minds) | 6 | `anniversary`, `irredentism`, `myth_debunked`, `scandal`, `struck`, `true_line` | `collective/accounts` |
| `knowledge.*` | 12 (knowledge, language and minds) | 4 | `creator_{verb}`, `declined`, `deepened`, `discovered` | `phases/knowledge_levels` |
| `language_contact.*` | 12 (knowledge, language and minds) | 3 | `creator_creole`, `loans`, `{key}` | `phases/language_contact` |
| `languages.*` | 12 (knowledge, language and minds) | 3 | `died`, `liturgical`, `revived` | `phases/language_death` |
| `learning.*` | 12 (knowledge, language and minds) | 1 | `migrated` | `regime/learning` |
| `memory.*` | 12 (knowledge, language and minds) | 9 | `fairy_tale`, `gratitude`, `legend_revived`, `legendification`, `manifestation`, `prophecy_forgotten`, `tradition_forgotten`, `vengeance`, `year_legend` | `mortal/acts`, `phases/belief_memory`, `phases/mind` |
| `mind.*` | 12 (knowledge, language and minds) | 6 | `conversion`, `disillusioned`, `facet_trait`, `famine_aid`, `plot`, `plot_uncovered` | `mind/ethics`, `mortal/acts`, `phases/mind` |
| `research.*` | 12 (knowledge, language and minds) | 3 | `boosted`, `institution_born`, `institution_embraced` | `lore/research_depth` |
| `rumour.*` | 12 (knowledge, language and minds) | 2 | `alarm`, `legend` | `lore/rumours` |
| `schools.*` | 12 (knowledge, language and minds) | 1 | `founded` | `regime/control`, `regime/learning` |
| `theories.*` | 12 (knowledge, language and minds) | 2 | `founded`, `paradigm_shift` | `lore/theories` |
| `tongues.*` | 12 (knowledge, language and minds) | 11 | `creolised`, `deciphered`, `misread`, `official`, `pidgin`, `place_renamed`, `revealed`, `revived`, `script_borrowed`, `script_evolved`, `taboo` | `tongues/decipher`, `tongues/divine`, `tongues/meaning`, `tongues/pidgins`, `tongues/policy`, `tongues/scripts`, `tongues/sounds` |
| `writing.*` | 12 (knowledge, language and minds) | 1 | `script` | `phases/writing` |
| `boserup.*` | 13 (nature, land and seasons) | 1 | `intensified` | `agrarian/soil` |
| `brands.*` | 13 (nature, land and seasons) | 1 | `earned` | `agrarian/control`, `agrarian/staples` |
| `climate.*` | 13 (nature, land and seasons) | 8 | `cold_snap`, `era`, `imposed`, `region_turned`, `seas_fell`, `seas_rose`, `town_moved`, `water_cycle` | `cosmos/climate`, `cosmos/cycles`, `cosmos/planetary`, `phases/climate` |
| `commons.*` | 13 (nature, land and seasons) | 2 | `council`, `enclosed` | `agrarian/lands` |
| `creatures.*` | 13 (nature, land and seasons) | 15 | `merged_escaped`, `species_merged`, `hybrid`, `megafauna`, `megafauna_trail`, `migration`, `mutation`, `people_mutation`, `predation`, `prey_extinct`, `rebellion`, `soul_eaten`, `soul_spared`, `speciation`, `starving` | `phases/creatures` |
| `danger.*` | 13 (nature, land and seasons) | 1 | `{source.source.value}` | `environment/perils` |
| `disasters.*` | 13 (nature, land and seasons) | 4 | `city_plague`, `manual_{disaster.value}`, `plague_spread`, `{disaster.value}` | `phases/disasters` |
| `ecology.*` | 13 (nature, land and seasons) | 16 | `abundance_set`, `animal_god`, `craft_lost`, `domestication`, `endangered`, `extinct`, `feral_breed`, `herd_feral`, `keystone_lost`, `lineage_blessed`, `lineage_cursed`, `lineage_tainted`, `niche_excluded`, `niche_radiation`, `rewound`, `sacred_lost` | `ecology/domestication`, `ecology/extinction`, `ecology/feral`, `ecology/keystones`, `ecology/lineages`, `ecology/niches`, `ecology/totems`, `phases/ecology` |
| `environment.*` | 13 (nature, land and seasons) | 2 | `ley_line_formed`, `nexus_formed` | `phases/environment` |
| `famine.*` | 13 (nature, land and seasons) | 1 | `foods_learned` | `agrarian/soil` |
| `flora.*` | 13 (nature, land and seasons) | 2 | `cultivar`, `sown` | `ecology/flora` |
| `hazard.*` | 13 (nature, land and seasons) | 1 | `{hazard.value}` | `environment/hazards` |
| `keystone.*` | 13 (nature, land and seasons) | 1 | `designated` | `agrarian/control`, `agrarian/staples` |
| `land.*` | 13 (nature, land and seasons) | 1 | `forest_fire` | `environment/succession` |
| `living_stats.*` | 13 (nature, land and seasons) | 4 | `mocked`, `mystery_knowledge`, `pilgrims`, `work_knowledge` | `phases/living_stats`, `structures/functions` |
| `nutrients.*` | 13 (nature, land and seasons) | 2 | `recovered`, `salted` | `agrarian/soil` |
| `perennials.*` | 13 (nature, land and seasons) | 3 | `felled`, `planted`, `replanted` | `agrarian/book`, `agrarian/control`, `agrarian/lands` |
| `place.*` | 13 (nature, land and seasons) | 4 | `became_battlefield`, `secret_opened`, `secret_released`, `secret_{secret.kind.value}` | `environment/secrets`, `phases/places` |
| `reconstruction.*` | 13 (nature, land and seasons) | 2 | `seized`, `{row.plan.value}` | `agrarian/resilience` |
| `relief.*` | 13 (nature, land and seasons) | 2 | `refused`, `sent` | `agrarian/resilience` |
| `resilience.*` | 13 (nature, land and seasons) | 2 | `built`, `held` | `agrarian/book`, `agrarian/control`, `agrarian/resilience` |
| `season.*` | 13 (nature, land and seasons) | 1 | `calendar_adopted` | `phases/environment` |
| `seasons.*` | 13 (nature, land and seasons) | 4 | `irregular`, `settled`, `summer`, `winter` | `environment/long_seasons` |
| `thunen.*` | 13 (nature, land and seasons) | 1 | `ring_moved` | `agrarian/rings` |
| `year.*` | 13 (nature, land and seasons) | 1 | `{notable.kind.value}` | `phases/environment` |
| `being.*` | 14 (cosmos and the great scales) | 11 | `arrived.{kind.value}`, `banished`, `bound`, `cult_founded`, `echo_befriended`, `echo_replaced`, `incursion`, `incursion_answered`, `manifest`, `took_rule`, `traded` | `cosmos/beings` |
| `celestial.*` | 14 (cosmos and the great scales) | 1 | `returned` | `cosmos/omens` |
| `cosmic_wounds.*` | 14 (cosmos and the great scales) | 1 | `slain` | `cosmos/being_wounds` |
| `cosmos.*` | 14 (cosmos and the great scales) | 8 | `gate_sealed`, `holy_world`, `leak_cleansed`, `old_god`, `outer_bargain`, `world_born`, `world_discovered`, `world_forgotten` | `cosmos/actions`, `cosmos/birth`, `cosmos/discovery`, `cosmos/worlds` |
| `dark_ages.*` | 14 (cosmos and the great scales) | 3 | `forgotten`, `lost`, `rediscovered` | `phases/dark_ages` |
| `dimension.*` | 14 (cosmos and the great scales) | 2 | `cult_risen`, `{kind.value}` | `cosmos/dimensions` |
| `doom.*` | 14 (cosmos and the great scales) | 7 | `apocalypse`, `calling`, `dimensional_collapse`, `galactic_death`, `omen_{warning}`, `outer_descent`, `twilight` | `phases/doom`, `transition` |
| `essence.*` | 14 (cosmos and the great scales) | 2 | `overflow`, `poured` | `transition` |
| `feature.*` | 14 (cosmos and the great scales) | 4 | `comet_returned`, `rogue_arrived`, `slingshot`, `wormhole_window` | `cosmos/features` |
| `formation.*` | 14 (cosmos and the great scales) | 1 | `shaped` | `cosmos/formation` |
| `galaxy.*` | 14 (cosmos and the great scales) | 5 | `aged`, `arm_broken`, `cult_risen`, `star_born`, `{kind.value}` | `cosmos/galaxies` |
| `impact.*` | 14 (cosmos and the great scales) | 6 | `called`, `deflected`, `fled`, `foreseen`, `missed`, `struck` | `cosmos/impacts` |
| `phenomenon.*` | 14 (cosmos and the great scales) | 3 | `contained`, `faded`, `formed.{kind.value}` | `cosmos/phenomena` |
| `rift.*` | 14 (cosmos and the great scales) | 4 | `closed`, `collapsed`, `opened.{cause.value}`, `sealed` | `cosmos/rifts` |
| `sky.*` | 14 (cosmos and the great scales) | 10 | `echo_prophecy`, `spontaneous.{result.kind.value}`, `star_extinguished`, `star_hung`, `star_rekindled`, `supernova`, `time_traveller`, `two_timed`, `world_drift`, `{kind.value}` | `cosmos/starlife`, `cosmos/stars`, `phases/sky` |
| `star.*` | 14 (cosmos and the great scales) | 7 | `binary_born`, `crisis_of_faith`, `cult_risen`, `died`, `divine_lapsed`, `stage.{following.value}`, `swelled` | `cosmos/galaxies`, `cosmos/starlife` |
| `terraform.*` | 14 (cosmos and the great scales) | 2 | `begun`, `finished` | `cosmos/terraform` |
| `transition.*` | 14 (cosmos and the great scales) | 1 | `epoch_began` | `transition` |
| `world.*` | 14 (cosmos and the great scales) | 9 | `aged.{aged.value}`, `biosphere_collapse`, `consciousness_closed`, `consciousness_opened`, `life_grew`, `mood_quake`, `ring_formed`, `scorched`, `tidally_locked` | `cosmos/catastrophe`, `cosmos/lifeforms`, `cosmos/physics_control`, `cosmos/worldlife`, `phases/physics` |
| `world_age.*` | 14 (cosmos and the great scales) | 4 | `epoch_turning`, `golden_age`, `golden_age_ended`, `old_world` | `phases/world_age` |
| `world_balance.*` | 14 (cosmos and the great scales) | 4 | `cult`, `faction`, `son_moved`, `tradition` | `phases/world_balance` |
| `council.*` | 15 (gods, sons and Fate) | 1 | `engine_held` | `divine/rulings` |
| `divine.*` | 15 (gods, sons and Fate) | 14 | `ascended`, `avatar_converts`, `avatar_manifest`, `battle_contest`, `battle_hand`, `goal_set`, `goal_{state.value}`, `law_unmade`, `league`, `pact`, `ruling_lapsed`, `spy_secret`, `wound_healed`, `wound_{kind.value}` | `divine/avatars`, `divine/battles`, `divine/foreign`, `divine/goals`, `divine/laws`, `divine/rulings`, `divine/wounds`, `mythic/divine_spies` |
| `dominion.*` | 15 (gods, sons and Fate) | 5 | `creature_{deed.value}`, `image_turned`, `magic_site_found`, `ruled`, `throne_passed` | `dominion/core`, `dominion/creatures`, `dominion/image`, `dominion/sites` |
| `mechanics.*` | 15 (gods, sons and Fate) | 2 | `law`, `resource` | `phases/mechanics_assignment` |
| `mythic.*` | 15 (gods, sons and Fate) | 10 | `geas_broken`, `hero_cult`, `heroquest_begun`, `heroquest_lost`, `heroquest_won`, `mantled`, `office_conquered`, `replaced`, `servitor_fell`, `servitor_guarded` | `mythic/geasa`, `mythic/heroquests`, `mythic/mantling`, `mythic/offices`, `mythic/servitors`, `phases/life_cycles` |
| `outer.*` | 15 (gods, sons and Fate) | 1 | `fed_{row.hunger.value}` | `divine/outer` |
| `pantheon.*` | 15 (gods, sons and Fate) | 15 | `attracted`, `defeated_woke`, `duel`, `first_contact`, `god_war`, `hostile`, `local_god_born`, `noticed`, `outer_gnaw`, `rival_clash`, `rival_withdrew`, `sleeper_woke`, `spontaneous_god_war`, `temple_destroyed`, `worshipper_stolen` | `cosmos/duels`, `cosmos/foreign_gods`, `phases/pantheon` |
| `sons.*` | 15 (gods, sons and Fate) | 3 | `existence`, `rebel_theft`, `woke` | `phases/sons` |
| `ages.*` | 16 (peoples, societies and history) | 2 | `echo`, `turned` | `storyteller/ages` |
| `arcs.*` | 16 (peoples, societies and history) | 3 | `begun`, `ended`, `payoff` | `storyteller/arcs`, `storyteller/drama` |
| `asabiyya.*` | 16 (peoples, societies and history) | 2 | `softened`, `surge` | `cycles/asabiyya` |
| `civilization.*` | 16 (peoples, societies and history) | 18 | `adoption`, `adoption_note`, `barter`, `barter_note`, `debt_late`, `debt_paid`, `declined`, `federation`, `federation_note`, `independence`, `independence_note`, `loan`, `loan_note`, `previous_creation`, `rose`, `tier`, `treaty`, `treaty_note` | `phases/civilization` |
| `dig.*` | 16 (peoples, societies and history) | 1 | `{dig.id}` | `sites/digs` |
| `excavation.*` | 16 (peoples, societies and history) | 2 | `begun`, `{stage.stage.value}` | `sites/digs` |
| `faction.*` | 16 (peoples, societies and history) | 9 | `exposed`, `hired`, `raid`, `riot`, `schism`, `strike`, `suppressed`, `turncoat`, `turned_bandit` | `factions/agenda`, `factions/outlaws` |
| `institutions.*` | 16 (peoples, societies and history) | 7 | `cult_disbanded`, `cult_merged`, `item_lost`, `people_union`, `place_swallowed`, `repealed`, `work_forgotten` | `phases/institutions` |
| `life_cycles.*` | 16 (peoples, societies and history) | 7 | `abandoned`, `collapse`, `desolate`, `looted`, `razed_by_hand`, `resettled`, `siege_razed` | `phases/life_cycles` |
| `movements.*` | 16 (peoples, societies and history) | 1 | `revolt` | `factions/movements` |
| `peoples.*` | 16 (peoples, societies and history) | 2 | `funeral_rite`, `martial_style` | `phases/demography` |
| `records.*` | 16 (peoples, societies and history) | 1 | `inheritance` | `records` |
| `site.*` | 16 (peoples, societies and history) | 1 | `delved` | `sites/rooms` |
| `society.*` | 16 (peoples, societies and history) | 11 | `bankruptcy`, `class_uprising`, `desertion`, `ennobled`, `enslaved`, `famine`, `freed`, `love`, `plenty`, `poverty_uprising`, `ruined` | `demography/events`, `demography/mobility`, `phases/society`, `phases/society_economy` |
| `storyteller.*` | 16 (peoples, societies and history) | 1 | `recovery` | `phases/gatherings` |

### Appendix 50.A — Every OCM subcategory, its status and its closure

Generated on 2026-11-14 from the OCM 2025 edition (HRAF, `ocm-2025.pdf`): 689 world-content subcategories, matched against the code and both specs as described in 50.0. "Own state and behaviour" means a table or typed columns with an engine module and god or agent control; "some typed state" means typed columns or a module without full behaviour; "a label only" means one enum value or flag. W44 step 0 copies this table to `docs/spec/ocm-coverage.md` for `scripts/check_ocm_coverage.py`.

| OCM | Subcategory | Measured status | Closed by |
|---|---|---|---|
| 130 | Geography | own state and behaviour in code | code (environment, ecology); spec 13 F2, 10.x; W48 48.8 |
| 131 | Location | some typed state in code | code (environment, ecology); spec 13 F2, 10.x; W48 48.8 |
| 132 | Climate | own state and behaviour in code | code (environment, ecology); spec 13 F2, 10.x; W48 48.8 |
| 133 | Topography And Geology | own state and behaviour in code | code (environment, ecology); spec 13 F2, 10.x; W48 48.8 |
| 134 | Soil | own state and behaviour in code | code (environment, ecology); spec 13 F2, 10.x; W48 48.8 |
| 135 | Mineral Resources | own state and behaviour in code | code (environment, ecology); spec 13 F2, 10.x; W48 48.8 |
| 136 | Fauna | own state and behaviour in code | code (environment, ecology); spec 13 F2, 10.x; W48 48.8 |
| 137 | Flora | own state and behaviour in code | code (environment, ecology); spec 13 F2, 10.x; W48 48.8 |
| 140 | Human Biology | own state and behaviour in code | code (body, genetics, nutrition); spec 13 F4, F39; W46 |
| 141 | Anthropometry | some typed state in code | code (body, genetics, nutrition); spec 13 F4, F39; W46 |
| 142 | Descriptive Somatology | own state and behaviour in code | code (body, genetics, nutrition); spec 13 F4, F39; W46 |
| 143 | Genetics | own state and behaviour in code | code (body, genetics, nutrition); spec 13 F4, F39; W46 |
| 145 | Ontogenetic Data | some typed state in code | code (body, genetics, nutrition); spec 13 F4, F39; W46 |
| 146 | Nutrition | own state and behaviour in code | code (body, genetics, nutrition); spec 13 F4, F39; W46 |
| 147 | Physiological Data | some typed state in code | code (body, genetics, nutrition); spec 13 F4, F39; W46 |
| 150 | Behavior Processes And Personality | own state and behaviour in code | code (mind, conditions); spec 13 F5–F7 |
| 151 | Sensation And Perception | own state and behaviour in code | code (mind, conditions); spec 13 F5–F7 |
| 152 | Drives And Emotions | own state and behaviour in code | code (mind, conditions); spec 13 F5–F7 |
| 153 | Modication Of Behavior | own state and behaviour in code | code (mind, conditions); spec 13 F5–F7 |
| 154 | Adjustment Processes | own state and behaviour in code | code (mind, conditions); spec 13 F5–F7 |
| 155 | Personality Development | a label only (enum value or flag) | **50.9** |
| 156 | Social Personality | own state and behaviour in code | **50.9**; also code (mind, conditions); spec 13 F5–F7 |
| 157 | Personality Traits | own state and behaviour in code | code (mind, conditions); spec 13 F5–F7 |
| 158 | Personality Disorders | some typed state in code | code (mind, conditions); spec 13 F5–F7 |
| 160 | Demography | own state and behaviour in code | code (demography); spec 13 Part 3 |
| 161 | Population | own state and behaviour in code | code (demography); spec 13 Part 3 |
| 162 | Composition Of Population | own state and behaviour in code | code (demography); spec 13 Part 3 |
| 163 | Birth Statistics | own state and behaviour in code | code (demography); spec 13 Part 3 |
| 164 | Morbidity | own state and behaviour in code | code (demography); spec 13 Part 3 |
| 165 | Mortality | some typed state in code | code (demography); spec 13 Part 3 |
| 166 | Internal Migration | own state and behaviour in code | code (demography); spec 13 Part 3 |
| 167 | External Migration | some typed state in code | code (demography); spec 13 Part 3 |
| 168 | Population Policy | absent from code | **50.1** |
| 170 | History And Culture Change | own state and behaviour in code | code (historiography, innovation, contact, plans); spec 13 F48, 8.4 |
| 172 | Prehistory | absent from code | code (historiography, innovation, contact, plans); spec 13 F48, 8.4; deepened by **50.16** |
| 173 | Traditional History | own state and behaviour in code | code (historiography, innovation, contact, plans); spec 13 F48, 8.4 |
| 175 | History | own state and behaviour in code | code (historiography, innovation, contact, plans); spec 13 F48, 8.4 |
| 176 | Innovation | own state and behaviour in code | code (historiography, innovation, contact, plans); spec 13 F48, 8.4 |
| 177 | Acculturation And Culture Contact | own state and behaviour in code | code (historiography, innovation, contact, plans); spec 13 F48, 8.4 |
| 178 | Sociocultural Trends | own state and behaviour in code | code (historiography, innovation, contact, plans); spec 13 F48, 8.4 |
| 179 | Economic Planning And Development | own state and behaviour in code | code (historiography, innovation, contact, plans); spec 13 F48, 8.4 |
| 181 | Ethos | own state and behaviour in code | code (values, norms, goals, identity); spec 13 F5, W20 |
| 183 | Norms | own state and behaviour in code | code (values, norms, goals, identity); spec 13 F5, W20 |
| 184 | Cultural Participation | own state and behaviour in code | code (values, norms, goals, identity); spec 13 F5, W20 |
| 185 | Cultural Goals | own state and behaviour in code | code (values, norms, goals, identity); spec 13 F5, W20 |
| 186 | Cultural Identity And Pride | own state and behaviour in code | code (values, norms, goals, identity); spec 13 F5, W20 |
| 190 | Language | own state and behaviour in code | code (tongues); spec 13 8.x |
| 191 | Speech | some typed state in code | code (tongues); spec 13 8.x |
| 192 | Vocabulary | own state and behaviour in code | code (tongues); spec 13 8.x |
| 193 | Grammar | own state and behaviour in code | code (tongues); spec 13 8.x |
| 194 | Phonology | own state and behaviour in code | code (tongues); spec 13 8.x |
| 195 | Sociolinguistics | own state and behaviour in code | code (tongues); spec 13 8.x |
| 196 | Semantics | own state and behaviour in code | code (tongues); spec 13 8.x |
| 198 | Special Languages | own state and behaviour in code | code (tongues); spec 13 8.x |
| 200 | Communication | some typed state in code | code (post, signals, rumour); spec 13 F21, F11 |
| 201 | Gestures And Signs | some typed state in code | code (post, signals, rumour); spec 13 F21, F11 |
| 202 | Transmission Of Messages | own state and behaviour in code | code (post, signals, rumour); spec 13 F21, F11 |
| 203 | Dissemination Of News And Information | own state and behaviour in code | code (post, signals, rumour); spec 13 F21, F11 |
| 204 | Press | own state and behaviour in code | **50.2**; also code (post, signals, rumour); spec 13 F21, F11 |
| 205 | Mail | some typed state in code | code (post, signals, rumour); spec 13 F21, F11 |
| 206 | Telephone And Telegraph | absent from code | **50.2** |
| 207 | Radio And Television | a label only (enum value or flag) | **50.2** |
| 208 | Public Opinion | some typed state in code | code (post, signals, rumour); spec 13 F21, F11 |
| 209 | Proxemics | some typed state in code | **50.5** |
| 210 | Records | own state and behaviour in code | code (writing, printing, archives); spec 13 8.x, W35 |
| 211 | Mnemonic Devices | own state and behaviour in code | code (writing, printing, archives); spec 13 8.x, W35 |
| 212 | Writing | own state and behaviour in code | code (writing, printing, archives); spec 13 8.x, W35 |
| 213 | Printing | some typed state in code | code (writing, printing, archives); spec 13 8.x, W35 |
| 214 | Publishing | own state and behaviour in code | code (writing, printing, archives); spec 13 8.x, W35 |
| 215 | Photography | absent from code | **50.2** |
| 216 | Audiovisual Records And Equipment | absent from code | **50.2** |
| 217 | Archives | own state and behaviour in code | code (writing, printing, archives); spec 13 8.x, W35 |
| 218 | Writing And Printing Supplies | own state and behaviour in code | code (writing, printing, archives); spec 13 8.x, W35 |
| 220 | Food Quest | some typed state in code | code (grounds, herds, ecology); W48 48.5 species products and roles |
| 221 | Annual Cycle | own state and behaviour in code | code (grounds, herds, ecology); W48 48.5 species products and roles |
| 222 | Collecting | own state and behaviour in code | code (grounds, herds, ecology); W48 48.5 species products and roles |
| 223 | Fowling | some typed state in code | code (grounds, herds, ecology); W48 48.5 species products and roles |
| 224 | Hunting And Trapping | own state and behaviour in code | code (grounds, herds, ecology); W48 48.5 species products and roles |
| 225 | Marine Hunting | own state and behaviour in code | code (grounds, herds, ecology); W48 48.5 species products and roles |
| 226 | Fishing | some typed state in code | code (grounds, herds, ecology); W48 48.5 species products and roles |
| 227 | Fishing Gear | own state and behaviour in code | code (grounds, herds, ecology); W48 48.5 species products and roles |
| 228 | Marine Industries | absent from code | code (grounds, herds, ecology); W48 48.5 species products and roles; deepened by **50.16** |
| 230 | Animal Husbandry | own state and behaviour in code | code (grounds, herds, ecology); W48 48.5 species products and roles |
| 231 | Domesticated Animals | some typed state in code | code (grounds, herds, ecology); W48 48.5 species products and roles |
| 232 | Applied Animal Science | own state and behaviour in code | code (grounds, herds, ecology); W48 48.5 species products and roles |
| 233 | Pastoral Activities | some typed state in code | code (grounds, herds, ecology); W48 48.5 species products and roles |
| 234 | Dairying | some typed state in code | code (grounds, herds, ecology); W48 48.5 species products and roles |
| 235 | Poultry Raising | some typed state in code | code (grounds, herds, ecology); W48 48.5 species products and roles |
| 236 | Wool Production | some typed state in code | code (grounds, herds, ecology); W48 48.5 species products and roles |
| 237 | Animal By-products | a label only (enum value or flag) | code (grounds, herds, ecology); W48 48.5 species products and roles; deepened by **50.16** |
| 240 | Agriculture | own state and behaviour in code | code (agrarian); spec 13 6.x, F24 techniques; W46 46.2; W48 48.5 |
| 241 | Tillage | some typed state in code | code (agrarian); spec 13 6.x, F24 techniques; W46 46.2; W48 48.5 |
| 242 | Agricultural Science | absent from code | code (agrarian); spec 13 6.x, F24 techniques; W46 46.2; W48 48.5; deepened by **50.16** |
| 243 | Cereal Agriculture | some typed state in code | code (agrarian); spec 13 6.x, F24 techniques; W46 46.2; W48 48.5 |
| 244 | Vegetable Production | some typed state in code | code (agrarian); spec 13 6.x, F24 techniques; W46 46.2; W48 48.5 |
| 245 | Arboriculture | some typed state in code | code (agrarian); spec 13 6.x, F24 techniques; W46 46.2; W48 48.5 |
| 246 | Forage Crops | some typed state in code | code (agrarian); spec 13 6.x, F24 techniques; W46 46.2; W48 48.5 |
| 247 | Floriculture | a label only (enum value or flag) | code (agrarian); spec 13 6.x, F24 techniques; W46 46.2; W48 48.5; deepened by **50.16** |
| 248 | Textile Agriculture | some typed state in code | code (agrarian); spec 13 6.x, F24 techniques; W46 46.2; W48 48.5 |
| 249 | Special Crops | some typed state in code | code (agrarian); spec 13 6.x, F24 techniques; W46 46.2; W48 48.5 |
| 250 | Food Processing | some typed state in code | W48 48.2 cuisine, 48.5 production methods and preservation |
| 251 | Preservation And Storage Of Food | own state and behaviour in code | W48 48.2 cuisine, 48.5 production methods and preservation |
| 252 | Food Preparation | own state and behaviour in code | W48 48.2 cuisine, 48.5 production methods and preservation |
| 253 | Meat Packing Industry | a label only (enum value or flag) | W48 48.2 cuisine, 48.5 production methods and preservation; deepened by **50.16** |
| 254 | Refrigeration Industry | own state and behaviour in code | W48 48.2 cuisine, 48.5 production methods and preservation |
| 255 | Canning Industry | some typed state in code | W48 48.2 cuisine, 48.5 production methods and preservation |
| 256 | Cereal Industry | some typed state in code | W48 48.2 cuisine, 48.5 production methods and preservation |
| 257 | Confectionery Industries | absent from code | W48 48.2 cuisine, 48.5 production methods and preservation; deepened by **50.16** |
| 258 | Other Food Processing Industries | some typed state in code | W48 48.2 cuisine, 48.5 production methods and preservation |
| 260 | Food Consumption | some typed state in code | code (basket, cuisine); W48 48.2; W47 customs |
| 261 | Gratication And Control Of Hunger | own state and behaviour in code | code (basket, cuisine); W48 48.2; W47 customs |
| 262 | Diet | own state and behaviour in code | code (basket, cuisine); W48 48.2; W47 customs |
| 263 | Condiments | some typed state in code | code (basket, cuisine); W48 48.2; W47 customs |
| 264 | Eating | some typed state in code | code (basket, cuisine); W48 48.2; W47 customs |
| 265 | Food Service Industries | own state and behaviour in code | code (basket, cuisine); W48 48.2; W47 customs |
| 266 | Cannibalism | a label only (enum value or flag) | code (basket, cuisine); W48 48.2; W47 customs; deepened by **50.16** |
| 270 | Drink And Drugs | some typed state in code | W48 48.2 drink, 48.4 substances; code (intoxicants, medicine) |
| 271 | Water And Thirst | some typed state in code | W48 48.2 drink, 48.4 substances; code (intoxicants, medicine) |
| 272 | Nonalcoholic Beverages | absent from code | W48 48.2 drink, 48.4 substances; code (intoxicants, medicine); deepened by **50.16** |
| 273 | Alcoholic Beverages | own state and behaviour in code | W48 48.2 drink, 48.4 substances; code (intoxicants, medicine) |
| 274 | Beverage Industries | a label only (enum value or flag) | W48 48.2 drink, 48.4 substances; code (intoxicants, medicine); deepened by **50.16** |
| 275 | Drinking Establishments | some typed state in code | W48 48.2 drink, 48.4 substances; code (intoxicants, medicine) |
| 276 | Recreational And Non-therapeutic Drugs | own state and behaviour in code | W48 48.2 drink, 48.4 substances; code (intoxicants, medicine) |
| 277 | Tobacco Industry | a label only (enum value or flag) | W48 48.2 drink, 48.4 substances; code (intoxicants, medicine); deepened by **50.16** |
| 278 | Pharmaceuticals | some typed state in code | W48 48.2 drink, 48.4 substances; code (intoxicants, medicine) |
| 280 | Leather, Textiles, And Fabrics | some typed state in code | W48 48.3 dress, 48.5 production methods |
| 281 | Work In Skins | some typed state in code | W48 48.3 dress, 48.5 production methods |
| 282 | Leather Industry | a label only (enum value or flag) | W48 48.3 dress, 48.5 production methods; deepened by **50.16** |
| 283 | Cordage | a label only (enum value or flag) | W48 48.3 dress, 48.5 production methods; deepened by **50.16** |
| 284 | Knots And Lashings | a label only (enum value or flag) | W48 48.3 dress, 48.5 production methods; deepened by **50.16** |
| 285 | Mats And Basketry | own state and behaviour in code | W48 48.3 dress, 48.5 production methods |
| 286 | Woven And Other Interworked Fabrics | some typed state in code | W48 48.3 dress, 48.5 production methods |
| 287 | Felted And Other Non-interworked Fabrics | a label only (enum value or flag) | W48 48.3 dress, 48.5 production methods; deepened by **50.16** |
| 288 | Textile Industries | some typed state in code | W48 48.3 dress, 48.5 production methods |
| 289 | Paper Industry | a label only (enum value or flag) | W48 48.3 dress, 48.5 production methods; deepened by **50.16** |
| 290 | Clothing | a label only (enum value or flag) | W48 48.3 garments; deepened by **50.16** |
| 291 | Normal Garb | absent from code | W48 48.3 garments; deepened by **50.16** |
| 292 | Special Garments | some typed state in code | W48 48.3 garments |
| 293 | Paraphernalia | some typed state in code | W48 48.3 garments |
| 294 | Clothing Manufacture | absent from code | W48 48.3 garments; deepened by **50.16** |
| 295 | Special Clothing Industries | some typed state in code | W48 48.3 garments |
| 296 | Garment Care | a label only (enum value or flag) | **50.5** |
| 300 | Adornment | some typed state in code | W48 48.3 adornment and emblems; code (body customs) |
| 301 | Ornament | a label only (enum value or flag) | W48 48.3 adornment and emblems; code (body customs); deepened by **50.16** |
| 302 | Personal Grooming | a label only (enum value or flag) | **50.5** |
| 303 | Making Of Grooming Accessories | a label only (enum value or flag) | **50.5** |
| 304 | Body Alterations | own state and behaviour in code | W48 48.3 adornment and emblems; code (body customs) |
| 305 | Beauty Specialists | some typed state in code | W48 48.3 adornment and emblems; code (body customs) |
| 306 | Jewelry Manufacture | a label only (enum value or flag) | W48 48.3 adornment and emblems; code (body customs); deepened by **50.16** |
| 310 | Exploitative Activities | own state and behaviour in code | code (extraction, ecology); W47 47.2 |
| 311 | Land Use | own state and behaviour in code | code (extraction, ecology); W47 47.2 |
| 312 | Water Supply | own state and behaviour in code | code (extraction, ecology); W47 47.2 |
| 313 | Lumbering | some typed state in code | code (extraction, ecology); W47 47.2 |
| 314 | Forest Products | some typed state in code | code (extraction, ecology); W47 47.2 |
| 315 | Oil And Gas Wells | own state and behaviour in code | code (extraction, ecology); W47 47.2 |
| 316 | Mining And Quarrying | own state and behaviour in code | code (extraction, ecology); W47 47.2 |
| 317 | Special Deposits | some typed state in code | code (extraction, ecology); W47 47.2 |
| 318 | Human Eects On Environment | own state and behaviour in code | code (extraction, ecology); W47 47.2 |
| 320 | Processing Of Basic Materials | own state and behaviour in code | code (materials F23); W48 48.5 methods |
| 321 | Bone, Horn, And Shell Technology | some typed state in code | code (materials F23); W48 48.5 methods |
| 322 | Woodworking | a label only (enum value or flag) | code (materials F23); W48 48.5 methods; deepened by **50.16** |
| 323 | Ceramic Technology | a label only (enum value or flag) | code (materials F23); W48 48.5 methods; deepened by **50.16** |
| 324 | Lithic Industries | a label only (enum value or flag) | code (materials F23); W48 48.5 methods; deepened by **50.16** |
| 325 | Metallurgy | some typed state in code | code (materials F23); W48 48.5 methods |
| 326 | Smiths And Their Crafts | own state and behaviour in code | code (materials F23); W48 48.5 methods |
| 327 | Iron And Steel Industry | own state and behaviour in code | code (materials F23); W48 48.5 methods |
| 328 | Nonferrous Metal Industries | own state and behaviour in code | code (materials F23); W48 48.5 methods |
| 330 | Building And Construction | own state and behaviour in code | code (construction); W47 47.1; W48 48.6 professions |
| 331 | Construction | own state and behaviour in code | code (construction); W47 47.1; W48 48.6 professions |
| 332 | Earth Moving | own state and behaviour in code | code (construction); W47 47.1; W48 48.6 professions |
| 333 | Masonry | a label only (enum value or flag) | code (construction); W47 47.1; W48 48.6 professions; deepened by **50.16** |
| 334 | Structural Steel Work | a label only (enum value or flag) | code (construction); W47 47.1; W48 48.6 professions; deepened by **50.16** |
| 335 | Carpentry | a label only (enum value or flag) | code (construction); W47 47.1; W48 48.6 professions; deepened by **50.16** |
| 336 | Plumbing | some typed state in code | code (construction); W47 47.1; W48 48.6 professions |
| 337 | Electrical Installation | a label only (enum value or flag) | code (construction); W47 47.1; W48 48.6 professions; deepened by **50.16** |
| 338 | Miscellaneous Building Trades | absent from code | code (construction); W47 47.1; W48 48.6 professions; deepened by **50.16** |
| 339 | Building Supplies Industries | some typed state in code | code (construction); W47 47.1; W48 48.6 professions |
| 340 | Structures | own state and behaviour in code | code (structures); W47 47.1 |
| 341 | Architecture | some typed state in code | code (structures); W47 47.1 |
| 342 | Dwellings | own state and behaviour in code | code (structures); W47 47.1 |
| 343 | Outbuildings | some typed state in code | code (structures); W47 47.1 |
| 344 | Public Structures | some typed state in code | code (structures); W47 47.1 |
| 345 | Recreational Structures | own state and behaviour in code | code (structures); W47 47.1 |
| 346 | Religious And Educational Structures | own state and behaviour in code | code (structures); W47 47.1 |
| 347 | Business Structures | own state and behaviour in code | code (structures); W47 47.1 |
| 348 | Industrial Structures | own state and behaviour in code | code (structures); W47 47.1 |
| 349 | Miscellaneous Structures | own state and behaviour in code | code (structures); W47 47.1 |
| 350 | Equipment And Maintenance Of Buildings | some typed state in code | W48 48.4 furnishing |
| 351 | Grounds | some typed state in code | W48 48.4 furnishing |
| 352 | Furniture | some typed state in code | W48 48.4 furnishing |
| 353 | Building Interiors And Arrangement | own state and behaviour in code | W48 48.4 furnishing |
| 354 | Heating And Lighting Equipment | a label only (enum value or flag) | W48 48.4 furnishing; deepened by **50.16** |
| 355 | Miscellaneous Building Equipment | a label only (enum value or flag) | W48 48.4 furnishing; deepened by **50.16** |
| 356 | Housekeeping | absent from code | **50.5** |
| 357 | Domestic Service | some typed state in code | **50.5** |
| 358 | Maintenance Of Non-domestic Buildings | own state and behaviour in code | code (upkeep, wear) |
| 360 | Settlements | own state and behaviour in code | code (settlements, urban) |
| 361 | Settlement Patterns | some typed state in code | code (settlements, urban) |
| 362 | Housing | own state and behaviour in code | code (settlements, urban) |
| 363 | Streets And Trac | own state and behaviour in code | code (settlements, urban) |
| 364 | Refuse Disposal And Sanitary Facilities | own state and behaviour in code | code (settlements, urban) |
| 365 | Public Utilities | a label only (enum value or flag) | code (settlements, urban); deepened by **50.16** |
| 366 | Commercial Facilities | own state and behaviour in code | code (settlements, urban) |
| 367 | Parks | a label only (enum value or flag) | code (settlements, urban); deepened by **50.16** |
| 368 | Miscellaneous Facilities | a label only (enum value or flag) | code (settlements, urban); deepened by **50.16** |
| 369 | Urban And Rural Life | own state and behaviour in code | code (settlements, urban) |
| 370 | Energy And Power | own state and behaviour in code | W47 47.2 energy |
| 371 | Power Development | some typed state in code | W47 47.2 energy |
| 372 | Fire | some typed state in code | W47 47.2 energy |
| 373 | Light | some typed state in code | W47 47.2 energy |
| 374 | Heat | own state and behaviour in code | W47 47.2 energy |
| 375 | Thermal Power | some typed state in code | W47 47.2 energy |
| 376 | Water Power | some typed state in code | W47 47.2 energy |
| 377 | Electric Power | a label only (enum value or flag) | W47 47.2 energy; deepened by **50.16** |
| 378 | Atomic Energy | absent from code | W47 47.2 energy; deepened by **50.16** |
| 379 | Miscellaneous Power Production | some typed state in code | W47 47.2 energy |
| 380 | Chemical Industries | some typed state in code | code (chemistry); W48 48.5 |
| 381 | Chemical Engineering | own state and behaviour in code | code (chemistry); W48 48.5 |
| 382 | Petroleum And Coal Products Industries | own state and behaviour in code | code (chemistry); W48 48.5 |
| 383 | Rubber Industry | absent from code | code (chemistry); W48 48.5; deepened by **50.16** |
| 384 | Synthetics Industry | a label only (enum value or flag) | code (chemistry); W48 48.5; deepened by **50.16** |
| 385 | Industrial Chemicals | some typed state in code | code (chemistry); W48 48.5 |
| 386 | Paint And Dye Manufacture | a label only (enum value or flag) | code (chemistry); W48 48.5; deepened by **50.16** |
| 387 | Fertilizer Industry | a label only (enum value or flag) | code (chemistry); W48 48.5; deepened by **50.16** |
| 388 | Soap And Allied Products | a label only (enum value or flag) | code (chemistry); W48 48.5; deepened by **50.16** |
| 389 | Manufacture Of Explosives | a label only (enum value or flag) | code (chemistry); W48 48.5; deepened by **50.16** |
| 390 | Capital Goods Industries | absent from code | W48 48.5 methods; code (vehicles, shipyards); deepened by **50.16** |
| 391 | Hardware Manufacture | absent from code | W48 48.5 methods; code (vehicles, shipyards); deepened by **50.16** |
| 392 | Machine Industries | a label only (enum value or flag) | W48 48.5 methods; code (vehicles, shipyards); deepened by **50.16** |
| 393 | Electrical Supplies Industry | a label only (enum value or flag) | W48 48.5 methods; code (vehicles, shipyards); deepened by **50.16** |
| 394 | Making Of Heating, Lighting Equipment | a label only (enum value or flag) | W48 48.5 methods; code (vehicles, shipyards); deepened by **50.16** |
| 395 | Making Of Optical And Photo Equipment | a label only (enum value or flag) | W48 48.5 methods; code (vehicles, shipyards); deepened by **50.16** |
| 396 | Shipbuilding | some typed state in code | W48 48.5 methods; code (vehicles, shipyards) |
| 397 | Railway Equipment Industry | a label only (enum value or flag) | W48 48.5 methods; code (vehicles, shipyards); deepened by **50.16** |
| 398 | Manufacture Of Vehicles | own state and behaviour in code | W48 48.5 methods; code (vehicles, shipyards) |
| 399 | Aircraft Industry | a label only (enum value or flag) | W48 48.5 methods; code (vehicles, shipyards); deepened by **50.16** |
| 400 | Machines | a label only (enum value or flag) | W48 48.4 tools; W47 per-family technology; deepened by **50.16** |
| 401 | Mechanics | own state and behaviour in code | W48 48.4 tools; W47 per-family technology |
| 402 | Industrial Machinery | own state and behaviour in code | W48 48.4 tools; W47 per-family technology |
| 403 | Electrical Machines And Appliances | absent from code | W48 48.4 tools; W47 per-family technology; deepened by **50.16** |
| 404 | Household Machines And Appliances | absent from code | W48 48.4 tools; W47 per-family technology; deepened by **50.16** |
| 405 | Measuring And Recording Devices | own state and behaviour in code | W48 48.4 tools; W47 per-family technology |
| 406 | Weight-moving Machinery | a label only (enum value or flag) | W48 48.4 tools; W47 per-family technology; deepened by **50.16** |
| 407 | Agricultural Machinery | some typed state in code | W48 48.4 tools; W47 per-family technology |
| 408 | Computer Technology | a label only (enum value or flag) | W48 48.4 tools; W47 per-family technology; deepened by **50.16** |
| 410 | Tools And Appliances | some typed state in code | W48 48.4 tools; W47 per-family technology |
| 411 | Weapons | some typed state in code | W48 48.4 tools; W47 per-family technology |
| 412 | General Tools | some typed state in code | W48 48.4 tools; W47 per-family technology |
| 413 | Special Tools | some typed state in code | W48 48.4 tools; W47 per-family technology |
| 414 | Miscellaneous Hardware | absent from code | W48 48.4 tools; W47 per-family technology; deepened by **50.16** |
| 415 | Utensils | some typed state in code | W48 48.4 tools; W47 per-family technology |
| 416 | Appliances | absent from code | W48 48.4 tools; W47 per-family technology; deepened by **50.16** |
| 417 | Apparatus | a label only (enum value or flag) | W48 48.4 tools; W47 per-family technology; deepened by **50.16** |
| 420 | Property | some typed state in code | code (property, incorporeal rights, inheritance, lands) |
| 421 | Property System | some typed state in code | code (property, incorporeal rights, inheritance, lands) |
| 422 | Property In Movables | some typed state in code | code (property, incorporeal rights, inheritance, lands) |
| 423 | Real Property | own state and behaviour in code | code (property, incorporeal rights, inheritance, lands) |
| 424 | Incorporeal Property | own state and behaviour in code | code (property, incorporeal rights, inheritance, lands) |
| 425 | Changes In Property Rights | some typed state in code | code (property, incorporeal rights, inheritance, lands) |
| 426 | Borrowing And Lending | own state and behaviour in code | code (property, incorporeal rights, inheritance, lands) |
| 427 | Renting And Leasing | own state and behaviour in code | **50.3**; also code (property, incorporeal rights, inheritance, lands) |
| 428 | Inheritance | some typed state in code | code (property, incorporeal rights, inheritance, lands) |
| 429 | Administration | some typed state in code | code (property, incorporeal rights, inheritance, lands) |
| 430 | Exchange And Transfers | some typed state in code | code (markets, trade, money) |
| 431 | Gift Giving | own state and behaviour in code | code (markets, trade, money) |
| 432 | Buying And Selling | own state and behaviour in code | code (markets, trade, money) |
| 433 | Production And Supply | own state and behaviour in code | code (markets, trade, money) |
| 434 | Income And Demand | own state and behaviour in code | code (markets, trade, money) |
| 435 | Price And Value | own state and behaviour in code | code (markets, trade, money) |
| 436 | Medium Of Exchange | own state and behaviour in code | code (markets, trade, money) |
| 437 | Exchange Transactions | some typed state in code | code (markets, trade, money) |
| 438 | Internal Trade | own state and behaviour in code | code (markets, trade, money) |
| 439 | External Trade | own state and behaviour in code | code (markets, trade, money) |
| 440 | Marketing | own state and behaviour in code | code (markets, trade, money) |
| 441 | Mercantile Business | some typed state in code | code (markets, trade, money) |
| 442 | Wholesale Marketing | absent from code | **50.3** |
| 443 | Retail Marketing | absent from code | **50.3** |
| 444 | Retail Businesses | own state and behaviour in code | **50.3** |
| 445 | Service Industries | own state and behaviour in code | **50.3** |
| 446 | Sales Promotion | some typed state in code | **50.3** |
| 447 | Advertising | absent from code | **50.3** |
| 450 | Finance | some typed state in code | code (finance, credit, banking, insurance, speculation) |
| 451 | Accounting | own state and behaviour in code | code (finance, credit, banking, insurance, speculation) |
| 452 | Credit | own state and behaviour in code | code (finance, credit, banking, insurance, speculation) |
| 453 | Banking | some typed state in code | code (finance, credit, banking, insurance, speculation) |
| 454 | Saving And Investment | some typed state in code | code (finance, credit, banking, insurance, speculation) |
| 455 | Speculation | some typed state in code | code (finance, credit, banking, insurance, speculation) |
| 456 | Insurance | own state and behaviour in code | code (finance, credit, banking, insurance, speculation) |
| 457 | Foreign Exchange | absent from code | **50.3** |
| 458 | Business Cycles | own state and behaviour in code | code (finance, credit, banking, insurance, speculation) |
| 460 | Labor | own state and behaviour in code | code (labour, guilds, wages); W48 48.6 |
| 461 | Labor And Leisure | some typed state in code | code (labour, guilds, wages); W48 48.6 |
| 462 | Division Of Labor By Gender | absent from code | code (labour, guilds, wages); W48 48.6; deepened by **50.16** |
| 463 | Occupational Specialization | own state and behaviour in code | code (labour, guilds, wages); W48 48.6 |
| 464 | Labor Supply And Employment | some typed state in code | code (labour, guilds, wages); W48 48.6 |
| 465 | Wages And Salaries | own state and behaviour in code | code (labour, guilds, wages); W48 48.6 |
| 466 | Labor Relations | some typed state in code | code (labour, guilds, wages); W48 48.6 |
| 467 | Labor Organization | own state and behaviour in code | code (labour, guilds, wages); W48 48.6 |
| 468 | Collective Bargaining | own state and behaviour in code | code (labour, guilds, wages); W48 48.6 |
| 470 | Business And Industrial Organization | some typed state in code | code (companies 44.15, cooperatives) |
| 471 | Ownership And Control Of Capital | own state and behaviour in code | code (companies 44.15, cooperatives) |
| 472 | Individual Enterprise | some typed state in code | code (companies 44.15, cooperatives) |
| 473 | Corporate Organization | own state and behaviour in code | code (companies 44.15, cooperatives) |
| 474 | Cooperative Organization | some typed state in code | code (companies 44.15, cooperatives) |
| 475 | State Enterprise | absent from code | **50.4** |
| 476 | Mutual Aid | some typed state in code | code (companies 44.15, cooperatives) |
| 477 | Competition | some typed state in code | code (companies 44.15, cooperatives) |
| 480 | Travel And Transportation | own state and behaviour in code | code (vehicles, routes, travel); W47 47.2 carriers |
| 481 | Locomotion | own state and behaviour in code | code (vehicles, routes, travel); W47 47.2 carriers |
| 482 | Burden Carrying | some typed state in code | code (vehicles, routes, travel); W47 47.2 carriers |
| 483 | Weight Moving | some typed state in code | code (vehicles, routes, travel); W47 47.2 carriers |
| 484 | Travel | own state and behaviour in code | code (vehicles, routes, travel); W47 47.2 carriers |
| 485 | Travel Services | some typed state in code | code (vehicles, routes, travel); W47 47.2 carriers |
| 486 | Regulation Of Travel | own state and behaviour in code | code (vehicles, routes, travel); W47 47.2 carriers |
| 487 | Routes | own state and behaviour in code | code (vehicles, routes, travel); W47 47.2 carriers |
| 488 | Warehousing | own state and behaviour in code | code (vehicles, routes, travel); W47 47.2 carriers |
| 489 | Transportation | own state and behaviour in code | code (vehicles, routes, travel); W47 47.2 carriers |
| 490 | Land Transport | some typed state in code | code (vehicles, routes, travel); W47 47.2 carriers |
| 491 | Highways And Bridges | own state and behaviour in code | code (vehicles, routes, travel); W47 47.2 carriers |
| 492 | Animal Transport | own state and behaviour in code | code (vehicles, routes, travel); W47 47.2 carriers |
| 493 | Vehicles | own state and behaviour in code | code (vehicles, routes, travel); W47 47.2 carriers |
| 494 | Highway Transport | absent from code | **50.4** |
| 495 | Auxiliary Highway Services | some typed state in code | **50.4**; also code (vehicles, routes, travel); W47 47.2 carriers |
| 496 | Railways | a label only (enum value or flag) | code (vehicles, routes, travel); W47 47.2 carriers; deepened by **50.16** |
| 497 | Rail Transport | own state and behaviour in code | code (vehicles, routes, travel); W47 47.2 carriers |
| 498 | Terminal Facilities | some typed state in code | code (vehicles, routes, travel); W47 47.2 carriers |
| 499 | Highway And Railway Construction | absent from code | **50.4** |
| 500 | Water, Air, And Space Transport | own state and behaviour in code | code (vehicles, routes, travel); W47 47.2 carriers |
| 501 | Boats | own state and behaviour in code | code (vehicles, routes, travel); W47 47.2 carriers |
| 502 | Navigation | a label only (enum value or flag) | code (vehicles, routes, travel); W47 47.2 carriers; deepened by **50.16** |
| 503 | Waterways Improvements | own state and behaviour in code | code (vehicles, routes, travel); W47 47.2 carriers |
| 504 | Port Facilities | own state and behaviour in code | code (vehicles, routes, travel); W47 47.2 carriers |
| 505 | Water Transport | some typed state in code | code (vehicles, routes, travel); W47 47.2 carriers |
| 506 | Aircraft | a label only (enum value or flag) | code (vehicles, routes, travel); W47 47.2 carriers; deepened by **50.16** |
| 507 | Aviation | a label only (enum value or flag) | code (vehicles, routes, travel); W47 47.2 carriers; deepened by **50.16** |
| 508 | Airport Facilities | a label only (enum value or flag) | code (vehicles, routes, travel); W47 47.2 carriers; deepened by **50.16** |
| 509 | Air Transport | some typed state in code | code (vehicles, routes, travel); W47 47.2 carriers |
| 510 | Living Standards And Routines | some typed state in code | code (living standard, basket) |
| 511 | Standard Of Living | some typed state in code | code (living standard, basket) |
| 512 | Daily Routine | absent from code | **50.5** |
| 513 | Sleeping | some typed state in code | **50.5** |
| 514 | Elimination | some typed state in code | **50.5** |
| 515 | Personal Hygiene | a label only (enum value or flag) | **50.5** |
| 516 | Postures | some typed state in code | **50.5** |
| 517 | Leisure Time Activities | some typed state in code | **50.5** |
| 520 | Recreation | some typed state in code | code (games, sports, leagues W26); W48 48.4 |
| 521 | Conversation | a label only (enum value or flag) | **50.13** |
| 522 | Humor | a label only (enum value or flag) | **50.13** |
| 523 | Hobbies | some typed state in code | **50.5**; also code (games, sports, leagues W26); W48 48.4 |
| 524 | Games | own state and behaviour in code | code (games, sports, leagues W26); W48 48.4 |
| 525 | Gambling | some typed state in code | code (games, sports, leagues W26); W48 48.4 |
| 526 | Athletic Sports | own state and behaviour in code | code (games, sports, leagues W26); W48 48.4 |
| 527 | Rest Days And Holidays | some typed state in code | code (games, sports, leagues W26); W48 48.4 |
| 528 | Vacations | absent from code | **50.5** |
| 529 | Recreational Facilities | some typed state in code | code (games, sports, leagues W26); W48 48.4 |
| 530 | Art | own state and behaviour in code | code (arts); W48 48.7 |
| 531 | Decorative Art | some typed state in code | code (arts); W48 48.7 |
| 532 | Representative Art | some typed state in code | code (arts); W48 48.7 |
| 533 | Music | a label only (enum value or flag) | code (arts); W48 48.7; deepened by **50.16** |
| 534 | Musical Instruments | a label only (enum value or flag) | code (arts); W48 48.7; deepened by **50.16** |
| 535 | Dance | some typed state in code | code (arts); W48 48.7 |
| 536 | Drama | own state and behaviour in code | code (arts); W48 48.7 |
| 537 | Oratory | some typed state in code | **50.13**; also code (arts); W48 48.7 |
| 538 | Literature | own state and behaviour in code | code (arts); W48 48.7 |
| 539 | Literary Texts | own state and behaviour in code | code (arts); W48 48.7 |
| 540 | Commercialized Entertainment | a label only (enum value or flag) | **50.2** |
| 541 | Spectacles | a label only (enum value or flag) | code (circus, leagues W26); deepened by **50.16** |
| 542 | Commercialized Sports | own state and behaviour in code | code (circus, leagues W26) |
| 543 | Exhibitions | own state and behaviour in code | code (circus, leagues W26) |
| 544 | Public Lectures | a label only (enum value or flag) | **50.13** |
| 545 | Musical And Theatrical Productions | own state and behaviour in code | code (circus, leagues W26) |
| 546 | Motion Picture Industry | absent from code | **50.2** |
| 547 | Night Clubs And Cabarets | some typed state in code | **50.2** |
| 548 | Illegal Entertainment | a label only (enum value or flag) | **50.2** |
| 549 | Art And Recreational Supplies Industries | absent from code | **50.2** |
| 550 | Naming, Prestige And Status Mobility | own state and behaviour in code | code (names, renown, mobility) |
| 551 | Personal Names | own state and behaviour in code | code (names, renown, mobility) |
| 552 | Names Of Animals And Things | own state and behaviour in code | code (names, renown, mobility) |
| 553 | Naming | own state and behaviour in code | code (names, renown, mobility) |
| 554 | Status, Role, And Prestige | own state and behaviour in code | code (names, renown, mobility) |
| 555 | Talent Mobility | own state and behaviour in code | code (names, renown, mobility) |
| 556 | Accumulation Of Wealth | own state and behaviour in code | code (names, renown, mobility) |
| 557 | Manipulative Mobility | some typed state in code | code (names, renown, mobility) |
| 558 | Downward Mobility | some typed state in code | code (names, renown, mobility) |
| 560 | Social Stratication | own state and behaviour in code | code (classes, castes F41, slavery, serfdom); W47 identities |
| 561 | Age Stratication | own state and behaviour in code | code (classes, castes F41, slavery, serfdom); W47 identities |
| 562 | Gender Status | a label only (enum value or flag) | code (classes, castes F41, slavery, serfdom); W47 identities; deepened by **50.16** |
| 563 | Ethnic Stratication | some typed state in code | code (classes, castes F41, slavery, serfdom); W47 identities |
| 564 | Castes | own state and behaviour in code | code (classes, castes F41, slavery, serfdom); W47 identities |
| 565 | Classes | own state and behaviour in code | code (classes, castes F41, slavery, serfdom); W47 identities |
| 566 | Serfdom And Peonage | own state and behaviour in code | code (classes, castes F41, slavery, serfdom); W47 identities |
| 567 | Slavery | own state and behaviour in code | code (classes, castes F41, slavery, serfdom); W47 identities |
| 570 | Interpersonal Relations | own state and behaviour in code | code (relations, circles, feuds, riots); W47 customs |
| 571 | Social Relationships And Groups | own state and behaviour in code | code (relations, circles, feuds, riots); W47 customs |
| 572 | Friendships | some typed state in code | code (relations, circles, feuds, riots); W47 customs |
| 573 | Cliques | some typed state in code | code (relations, circles, feuds, riots); W47 customs |
| 574 | Visiting And Hospitality | some typed state in code | code (relations, circles, feuds, riots); W47 customs |
| 575 | Sodalities | own state and behaviour in code | code (relations, circles, feuds, riots); W47 customs |
| 576 | Etiquette | some typed state in code | code (relations, circles, feuds, riots); W47 customs |
| 577 | Ethics | some typed state in code | code (relations, circles, feuds, riots); W47 customs |
| 578 | Ingroup Antagonisms | own state and behaviour in code | code (relations, circles, feuds, riots); W47 customs |
| 579 | Brawls, Riots, And Banditry | some typed state in code | code (relations, circles, feuds, riots); W47 customs |
| 580 | Marriage | own state and behaviour in code | code (kinship, unions); W47 47.3.4 |
| 581 | Basis Of Marriage | own state and behaviour in code | code (kinship, unions); W47 47.3.4 |
| 582 | Regulation Of Marriage | some typed state in code | code (kinship, unions); W47 47.3.4 |
| 583 | Mode Of Marriage | a label only (enum value or flag) | code (kinship, unions); W47 47.3.4; deepened by **50.16** |
| 584 | Arranging A Marriage | own state and behaviour in code | code (kinship, unions); W47 47.3.4 |
| 585 | Nuptials | a label only (enum value or flag) | code (kinship, unions); W47 47.3.4; deepened by **50.16** |
| 586 | Termination Of Marriage | some typed state in code | code (kinship, unions); W47 47.3.4 |
| 587 | Secondary Marriages | some typed state in code | code (kinship, unions); W47 47.3.4 |
| 588 | Special Unions And Marriages | some typed state in code | **50.6**; also code (kinship, unions); W47 47.3.4 |
| 589 | Celibacy | a label only (enum value or flag) | code (kinship, unions); W47 47.3.4; deepened by **50.16** |
| 590 | Family | some typed state in code | code (households, adoption) |
| 591 | Residence | some typed state in code | code (households, adoption) |
| 592 | Household | own state and behaviour in code | code (households, adoption) |
| 593 | Family Relationships | own state and behaviour in code | **50.6**; also code (households, adoption) |
| 594 | Nuclear Family | absent from code | **50.6** |
| 595 | Polygamy | a label only (enum value or flag) | code (households, adoption); deepened by **50.16** |
| 596 | Extended Families | absent from code | **50.6** |
| 597 | Adoption | own state and behaviour in code | code (households, adoption) |
| 600 | Kinship | some typed state in code | code (kinship); W48 48.6 kin terms |
| 601 | Kinship Terminology | absent from code | **50.6** |
| 602 | Kin Relationships | own state and behaviour in code | **50.6**; also code (kinship); W48 48.6 kin terms |
| 603 | Grandparents And Grandchildren | absent from code | **50.6** |
| 604 | Avuncular And Nepotic Relatives | some typed state in code | **50.6**; also code (kinship); W48 48.6 kin terms |
| 605 | Cousins | some typed state in code | **50.6**; also code (kinship); W48 48.6 kin terms |
| 606 | Parents-in-law And Children-in-law | absent from code | **50.6** |
| 607 | Siblings-in-law | absent from code | **50.6** |
| 608 | Articial Kin Relationships | some typed state in code | **50.6**; also code (kinship); W48 48.6 kin terms |
| 609 | Behavior Toward Non-relatives | some typed state in code | **50.6**; also code (kinship); W48 48.6 kin terms |
| 610 | Kin Groups | absent from code | **50.6** |
| 611 | Rules Of Descent | some typed state in code | code (kinship); W48 48.6 kin terms |
| 612 | Kindreds And Ramages | absent from code | **50.6** |
| 613 | Lineages | own state and behaviour in code | code (kinship); W48 48.6 kin terms |
| 614 | Clans | a label only (enum value or flag) | code (kinship); W48 48.6 kin terms; deepened by **50.16** |
| 615 | Phratries | absent from code | **50.6** |
| 616 | Moieties | a label only (enum value or flag) | code (kinship); W48 48.6 kin terms; deepened by **50.16** |
| 617 | Bilineal Kin Groups | a label only (enum value or flag) | **50.6** |
| 618 | Localized Kin Groups | absent from code | **50.6** |
| 619 | Tribe And Nation | own state and behaviour in code | code (kinship); W48 48.6 kin terms |
| 620 | Community | own state and behaviour in code | code (polity, settlements, territory) |
| 621 | Community Structure | own state and behaviour in code | code (polity, settlements, territory) |
| 622 | Community Heads | some typed state in code | code (polity, settlements, territory) |
| 623 | Community Councils | own state and behaviour in code | code (polity, settlements, territory) |
| 624 | Local Ocials | own state and behaviour in code | code (polity, settlements, territory) |
| 625 | Police | some typed state in code | code (polity, settlements, territory) |
| 626 | Social Control | some typed state in code | code (polity, settlements, territory) |
| 627 | Informal In-group Justice | some typed state in code | code (polity, settlements, territory) |
| 628 | Inter-community Relations | own state and behaviour in code | code (polity, settlements, territory) |
| 629 | Multi-ethnic Community Relations | some typed state in code | code (polity, settlements, territory) |
| 630 | Territorial Organization | own state and behaviour in code | code (polity, settlements, territory) |
| 631 | Territorial Hierarchy | own state and behaviour in code | code (polity, settlements, territory) |
| 632 | Towns | some typed state in code | code (polity, settlements, territory) |
| 633 | Cities | own state and behaviour in code | code (polity, settlements, territory) |
| 634 | Districts | own state and behaviour in code | code (polity, settlements, territory) |
| 635 | Provinces | some typed state in code | code (polity, settlements, territory) |
| 636 | Dependencies | own state and behaviour in code | code (polity, settlements, territory) |
| 640 | Government Institutions | some typed state in code | code (polity, offices, councils, taxes, laws) |
| 641 | Citizenship | own state and behaviour in code | code (polity, offices, councils, taxes, laws) |
| 642 | Form And Rules Of Government | a label only (enum value or flag) | code (polity, offices, councils, taxes, laws); deepened by **50.16** |
| 643 | Chief Executive | own state and behaviour in code | code (polity, offices, councils, taxes, laws) |
| 644 | Executive Household | own state and behaviour in code | code (polity, offices, councils, taxes, laws) |
| 645 | Advisers To The Chief Executive | own state and behaviour in code | code (polity, offices, councils, taxes, laws) |
| 646 | Deliberative Councils | own state and behaviour in code | code (polity, offices, councils, taxes, laws) |
| 647 | Administrative Agencies | some typed state in code | code (polity, offices, councils, taxes, laws) |
| 648 | External Relations | some typed state in code | code (polity, offices, councils, taxes, laws) |
| 650 | Government Activities | some typed state in code | code (polity, offices, councils, taxes, laws) |
| 651 | Taxation And Public Income | own state and behaviour in code | code (polity, offices, councils, taxes, laws) |
| 652 | Public Finance | some typed state in code | code (polity, offices, councils, taxes, laws) |
| 653 | Public Works | some typed state in code | **50.4**; also code (polity, offices, councils, taxes, laws) |
| 654 | Research And Development | own state and behaviour in code | code (polity, offices, councils, taxes, laws) |
| 655 | Government Enterprises | absent from code | **50.4** |
| 656 | Government Regulation | some typed state in code | code (polity, offices, councils, taxes, laws) |
| 657 | Public Welfare | some typed state in code | code (polity, offices, councils, taxes, laws) |
| 658 | Public Education | own state and behaviour in code | code (polity, offices, councils, taxes, laws) |
| 659 | Miscellaneous Government Activities | some typed state in code | code (polity, offices, councils, taxes, laws) |
| 660 | Political Behavior | some typed state in code | code (factions, elections, intrigue, revolts) |
| 661 | Exploitation | some typed state in code | code (factions, elections, intrigue, revolts) |
| 662 | Political Intrigue | some typed state in code | code (factions, elections, intrigue, revolts) |
| 663 | Public Service | own state and behaviour in code | code (factions, elections, intrigue, revolts) |
| 664 | Pressure Politics | own state and behaviour in code | code (factions, elections, intrigue, revolts) |
| 665 | Political Parties | own state and behaviour in code | code (factions, elections, intrigue, revolts) |
| 666 | Elections | some typed state in code | code (factions, elections, intrigue, revolts) |
| 667 | Political Machines | some typed state in code | code (factions, elections, intrigue, revolts) |
| 668 | Political Movements | own state and behaviour in code | code (factions, elections, intrigue, revolts) |
| 669 | Revolution | some typed state in code | code (factions, elections, intrigue, revolts) |
| 670 | Law | own state and behaviour in code | code (law, crime, justice W27) |
| 671 | Legal Norms | own state and behaviour in code | code (law, crime, justice W27) |
| 672 | Liability | some typed state in code | code (law, crime, justice W27) |
| 673 | Wrongs | own state and behaviour in code | code (law, crime, justice W27) |
| 674 | Crime | own state and behaviour in code | code (law, crime, justice W27) |
| 675 | Contracts | own state and behaviour in code | code (law, crime, justice W27) |
| 676 | Agency | own state and behaviour in code | code (law, crime, justice W27) |
| 677 | Organized Crime | some typed state in code | code (law, crime, justice W27) |
| 680 | Oenses And Sanctions | some typed state in code | code (law, crime, justice W27) |
| 681 | Sanctions | some typed state in code | code (law, crime, justice W27) |
| 682 | Oenses Against Life | some typed state in code | code (law, crime, justice W27) |
| 683 | Oenses Against The Person | a label only (enum value or flag) | code (law, crime, justice W27); deepened by **50.16** |
| 684 | Sex And Marital Oenses | a label only (enum value or flag) | code (law, crime, justice W27); deepened by **50.16** |
| 685 | Property Oenses | a label only (enum value or flag) | code (law, crime, justice W27); deepened by **50.16** |
| 686 | Nonfulllment Of Obligations | some typed state in code | code (law, crime, justice W27) |
| 687 | Oenses Against The State | a label only (enum value or flag) | code (law, crime, justice W27); deepened by **50.16** |
| 688 | Religious Oenses | own state and behaviour in code | code (law, crime, justice W27) |
| 689 | Social Oenses | some typed state in code | code (law, crime, justice W27) |
| 690 | Justice | some typed state in code | code (law, crime, justice W27) |
| 691 | Litigation | some typed state in code | code (law, crime, justice W27) |
| 692 | Judicial Authority | own state and behaviour in code | code (law, crime, justice W27) |
| 693 | Legal And Judicial Personnel | some typed state in code | code (law, crime, justice W27) |
| 694 | Initiation Of Judicial Proceedings | own state and behaviour in code | code (law, crime, justice W27) |
| 695 | Trial Procedure | some typed state in code | code (law, crime, justice W27) |
| 696 | Execution Of Justice | own state and behaviour in code | code (law, crime, justice W27) |
| 697 | Prisons And Jails | own state and behaviour in code | code (law, crime, justice W27) |
| 698 | Special Courts | some typed state in code | code (law, crime, justice W27) |
| 700 | Armed Forces | own state and behaviour in code | code (military) |
| 701 | Military Organization | own state and behaviour in code | code (military) |
| 702 | Recruitment And Training | own state and behaviour in code | code (military) |
| 703 | Discipline And Morale | some typed state in code | code (military) |
| 704 | Ground Combat Forces | some typed state in code | code (military) |
| 705 | Supply And Commissariat | own state and behaviour in code | code (military) |
| 706 | Navy | some typed state in code | code (military) |
| 707 | Air Forces | some typed state in code | code (military) |
| 708 | Auxiliary Corps | some typed state in code | code (military) |
| 710 | Military Technology | some typed state in code | code (military) |
| 711 | Military Engineering | a label only (enum value or flag) | code (military); deepened by **50.16** |
| 712 | Military Installations | own state and behaviour in code | code (military) |
| 713 | Ordnance | a label only (enum value or flag) | code (military); deepened by **50.16** |
| 714 | Uniform And Accouterment | own state and behaviour in code | code (military) |
| 715 | Military Vehicles | a label only (enum value or flag) | code (military); deepened by **50.16** |
| 716 | Naval Vessels | some typed state in code | code (military) |
| 717 | Military Aircraft | a label only (enum value or flag) | code (military); deepened by **50.16** |
| 718 | Special Military Equipment | a label only (enum value or flag) | code (military); deepened by **50.16** |
| 719 | Munitions Industries | some typed state in code | code (military) |
| 720 | War | own state and behaviour in code | code (military) |
| 721 | Instigation Of War | own state and behaviour in code | code (military) |
| 722 | Wartime Adjustments | some typed state in code | code (military) |
| 723 | Strategy | some typed state in code | code (military) |
| 724 | Logistics | some typed state in code | code (military) |
| 725 | Tactics | some typed state in code | code (military) |
| 726 | Warfare | own state and behaviour in code | code (military) |
| 727 | Aftermath Of Combat | some typed state in code | code (military) |
| 728 | Peacemaking | some typed state in code | code (military) |
| 729 | War Veterans | some typed state in code | code (military) |
| 730 | Social Problems | some typed state in code | code (disasters, maimed cohorts, addiction, poor relief) |
| 731 | Disasters | some typed state in code | code (disasters, maimed cohorts, addiction, poor relief) |
| 732 | Disabilities | some typed state in code | code (disasters, maimed cohorts, addiction, poor relief) |
| 733 | Alcoholism And Drug Addiction | own state and behaviour in code | code (disasters, maimed cohorts, addiction, poor relief) |
| 734 | Invalidism | some typed state in code | code (disasters, maimed cohorts, addiction, poor relief) |
| 735 | Poverty | some typed state in code | code (disasters, maimed cohorts, addiction, poor relief) |
| 736 | Dependency | some typed state in code | code (disasters, maimed cohorts, addiction, poor relief) |
| 737 | Old Age Dependency | some typed state in code | code (disasters, maimed cohorts, addiction, poor relief) |
| 738 | Delinquency | absent from code | **50.11** |
| 740 | Health And Welfare | own state and behaviour in code | code (welfare, insurance) |
| 741 | Philanthropic Foundations | some typed state in code | **50.10**; also code (welfare, insurance) |
| 742 | Medical Research | some typed state in code | code (welfare, insurance) |
| 743 | Hospitals And Clinics | some typed state in code | code (welfare, insurance) |
| 744 | Public Health And Sanitation | own state and behaviour in code | code (welfare, insurance) |
| 745 | Social Insurance | own state and behaviour in code | code (welfare, insurance) |
| 746 | Public Assistance | own state and behaviour in code | code (welfare, insurance) |
| 747 | Private Welfare Agencies | some typed state in code | **50.10**; also code (welfare, insurance) |
| 748 | Social Work | some typed state in code | code (welfare, insurance) |
| 750 | Sickness | own state and behaviour in code | code (disease, body, treatment) |
| 751 | Preventive Medicine | own state and behaviour in code | code (disease, body, treatment) |
| 752 | Bodily Injuries | own state and behaviour in code | code (disease, body, treatment) |
| 753 | Theory Of Disease | some typed state in code | code (disease, body, treatment) |
| 754 | Sorcery | some typed state in code | code (disease, body, treatment) |
| 755 | Magical And Mental Therapy | absent from code | code (disease, body, treatment); deepened by **50.16** |
| 756 | Shamans And Psychotherapists | a label only (enum value or flag) | code (disease, body, treatment); deepened by **50.16** |
| 757 | Medical Therapy | some typed state in code | code (disease, body, treatment) |
| 758 | Medical Care | some typed state in code | code (disease, body, treatment) |
| 759 | Medical Personnel | a label only (enum value or flag) | code (disease, body, treatment); deepened by **50.16** |
| 760 | Death | own state and behaviour in code | code (death, funerals, mourning, ancestors, afterlife) |
| 761 | Life And Death | some typed state in code | code (death, funerals, mourning, ancestors, afterlife) |
| 762 | Suicide | a label only (enum value or flag) | code (death, funerals, mourning, ancestors, afterlife); deepened by **50.16** |
| 763 | Dying | a label only (enum value or flag) | code (death, funerals, mourning, ancestors, afterlife); deepened by **50.16** |
| 764 | Burial Practices And Funerals | some typed state in code | code (death, funerals, mourning, ancestors, afterlife) |
| 765 | Mourning | some typed state in code | code (death, funerals, mourning, ancestors, afterlife) |
| 766 | Special Burial Practices And Funerals | a label only (enum value or flag) | **50.12** |
| 767 | Mortuary Specialists | absent from code | **50.12** |
| 768 | Social Readjustments To Death | some typed state in code | **50.12**; also code (death, funerals, mourning, ancestors, afterlife) |
| 769 | Cult Of The Dead | a label only (enum value or flag) | code (death, funerals, mourning, ancestors, afterlife); deepened by **50.16** |
| 770 | Religious Beliefs | own state and behaviour in code | code (faith, sacred W25) |
| 771 | General Character Of Religion | some typed state in code | code (faith, sacred W25) |
| 772 | Cosmology | some typed state in code | code (faith, sacred W25) |
| 773 | Mythology | own state and behaviour in code | code (faith, sacred W25) |
| 774 | Animism | own state and behaviour in code | code (faith, sacred W25) |
| 775 | Eschatology | some typed state in code | code (faith, sacred W25) |
| 776 | Spirits And Gods | own state and behaviour in code | code (faith, sacred W25) |
| 777 | Luck And Chance | own state and behaviour in code | code (faith, sacred W25) |
| 778 | Sacred Objects And Places | own state and behaviour in code | code (faith, sacred W25) |
| 779 | Theological Systems | own state and behaviour in code | code (faith, sacred W25) |
| 780 | Religious Practices | some typed state in code | code (faith, sacred W25) |
| 781 | Religious Experience | own state and behaviour in code | code (faith, sacred W25) |
| 782 | Prayers And Sacrices | own state and behaviour in code | code (faith, sacred W25) |
| 783 | Purication And Atonement | some typed state in code | code (faith, sacred W25) |
| 784 | Avoidance And Taboo | own state and behaviour in code | code (faith, sacred W25) |
| 785 | Asceticism | a label only (enum value or flag) | code (faith, sacred W25); deepened by **50.16** |
| 786 | Ecstatic Religious Practices | some typed state in code | code (faith, sacred W25) |
| 787 | Revelation And Divination | own state and behaviour in code | code (faith, sacred W25) |
| 788 | Ritual | own state and behaviour in code | code (faith, sacred W25) |
| 789 | Magic | own state and behaviour in code | code (faith, sacred W25) |
| 790 | Ecclesiastical Organization | own state and behaviour in code | code (faith, sacred W25) |
| 791 | Magicians And Diviners | own state and behaviour in code | code (faith, sacred W25) |
| 792 | Prophets And Ascetics | own state and behaviour in code | code (faith, sacred W25) |
| 793 | Priesthood | some typed state in code | code (faith, sacred W25) |
| 794 | Congregations | some typed state in code | code (faith, sacred W25) |
| 795 | Religious Denominations | own state and behaviour in code | code (faith, sacred W25) |
| 796 | Organized Ceremonial | some typed state in code | code (faith, sacred W25) |
| 797 | Missions | own state and behaviour in code | code (faith, sacred W25) |
| 798 | Religious Intolerance And Martyrs | some typed state in code | code (faith, sacred W25) |
| 800 | Numbers And Measures | own state and behaviour in code | spec 13 8.4 RP5 number systems; code (calendars) |
| 801 | Numerology | absent from code | **50.7** |
| 802 | Numeration | absent from code | **50.7** |
| 803 | Mathematics | absent from code | **50.7** |
| 804 | Weights And Measures | own state and behaviour in code | spec 13 8.4 RP5 number systems; code (calendars) |
| 805 | Ordering Of Time | own state and behaviour in code | spec 13 8.4 RP5 number systems; code (calendars) |
| 810 | Sciences And Humanities | some typed state in code | code (knowledge, theories) |
| 811 | Logic | a label only (enum value or flag) | code (knowledge, theories); deepened by **50.16** |
| 812 | Philosophy | a label only (enum value or flag) | code (knowledge, theories); deepened by **50.16** |
| 813 | Scientic Method | a label only (enum value or flag) | code (knowledge, theories); deepened by **50.16** |
| 814 | Humanistic Studies | absent from code | code (knowledge, theories); deepened by **50.16** |
| 815 | Science | some typed state in code | code (knowledge, theories) |
| 816 | Applied Science | own state and behaviour in code | code (knowledge, theories) |
| 820 | Ideas About Nature And People | own state and behaviour in code | **50.7** |
| 821 | Ethnometeorology | own state and behaviour in code | **50.7** |
| 822 | Ethnophysics | absent from code | **50.7** |
| 823 | Ethnogeography | absent from code | **50.7** |
| 824 | Ethnobotany | a label only (enum value or flag) | **50.7** |
| 825 | Ethnozoology | absent from code | **50.7** |
| 826 | Ethnoanatomy | absent from code | **50.7** |
| 827 | Ethnophysiology | a label only (enum value or flag) | **50.7** |
| 828 | Ethnopsychology | absent from code | **50.7** |
| 829 | Ethnosociology | absent from code | **50.7** |
| 830 | Sex | own state and behaviour in code | **50.8** |
| 831 | Sexuality | absent from code | **50.8** |
| 832 | Sexual Stimulation | some typed state in code | **50.8** |
| 833 | Sexual Intercourse | a label only (enum value or flag) | **50.8** |
| 834 | General Sex Restrictions | absent from code | **50.8** |
| 835 | Kinship Regulation Of Sex | a label only (enum value or flag) | **50.8** |
| 836 | Premarital Sex Relations | absent from code | **50.8** |
| 837 | Extramarital Sex Relations | own state and behaviour in code | **50.8** |
| 838 | Homosexuality | absent from code | **50.8** |
| 839 | Miscellaneous Sex Behavior | absent from code | **50.8** |
| 840 | Reproduction | some typed state in code | **50.8** |
| 841 | Menstruation | absent from code | **50.8** |
| 842 | Conception | some typed state in code | **50.8** |
| 843 | Pregnancy | absent from code | **50.8** |
| 844 | Childbirth | own state and behaviour in code | **50.8** |
| 845 | Dicult And Unusual Births | absent from code | **50.8** |
| 846 | Postnatal Care | absent from code | **50.8** |
| 847 | Abortion And Infanticide | a label only (enum value or flag) | **50.8** |
| 848 | Illegitimacy | a label only (enum value or flag) | **50.8** |
| 850 | Infancy And Childhood | some typed state in code | **50.9** |
| 851 | Social Placement | absent from code | **50.9** |
| 852 | Ceremonial During Infancy And Childhood | own state and behaviour in code | **50.9** |
| 853 | Infant Feeding | absent from code | **50.9** |
| 854 | Infant Care | absent from code | **50.9** |
| 855 | Child Care | a label only (enum value or flag) | **50.9** |
| 856 | Development And Maturation | some typed state in code | **50.9** |
| 857 | Childhood Activities | own state and behaviour in code | **50.9** |
| 858 | Status Of Children | absent from code | **50.9** |
| 860 | Socialization | some typed state in code | **50.9** |
| 861 | Techniques Of Socialization | a label only (enum value or flag) | **50.9** |
| 862 | Weaning And Food Training | absent from code | **50.9** |
| 863 | Cleanliness Training | absent from code | **50.9** |
| 864 | Sex Training | absent from code | **50.9** |
| 865 | Aggression Training | absent from code | **50.9** |
| 866 | Independence Training | a label only (enum value or flag) | **50.9** |
| 867 | Transmission Of Cultural Norms | own state and behaviour in code | **50.9** |
| 868 | Transmission Of Skills | own state and behaviour in code | **50.9** |
| 869 | Transmission Of Beliefs | absent from code | **50.9** |
| 870 | Education | own state and behaviour in code | code (schools, learning) |
| 871 | Education System | own state and behaviour in code | code (schools, learning) |
| 872 | Elementary Education | some typed state in code | code (schools, learning) |
| 873 | Liberal Arts Education | some typed state in code | code (schools, learning) |
| 874 | Vocational Education | a label only (enum value or flag) | code (schools, learning); deepened by **50.16** |
| 875 | Teachers | a label only (enum value or flag) | code (schools, learning); deepened by **50.16** |
| 876 | Educational Theory And Methods | absent from code | **50.9** |
| 877 | Students | some typed state in code | code (schools) |
| 880 | Adolescence, Adulthood, And Old Age | a label only (enum value or flag) | code (age sets, life course); spec 13 3.1 RP; deepened by **50.16** |
| 881 | Puberty And Initiation | some typed state in code | code (age sets, life course); spec 13 3.1 RP |
| 882 | Status Of Adolescents | absent from code | **50.11** |
| 883 | Adolescent Activities | a label only (enum value or flag) | **50.11** |
| 884 | Majority | a label only (enum value or flag) | code (age sets, life course); spec 13 3.1 RP; deepened by **50.16** |
| 885 | Adulthood | some typed state in code | code (age sets, life course); spec 13 3.1 RP |
| 886 | Senescence | some typed state in code | code (age sets, life course); spec 13 3.1 RP |
| 887 | Activities Of The Aged | own state and behaviour in code | code (age sets, life course); spec 13 3.1 RP |
| 888 | Status And Treatment Of The Aged | some typed state in code | code (age sets, life course); spec 13 3.1 RP |
| 890 | Gender Roles And Issues | a label only (enum value or flag) | culture data (GenderRule, any by default); W48 48.6; deepened by **50.16** |
| 920 | Diaspora-homeland Relations | some typed state in code | code (diaspora) |

### Appendix 50.B — Registered mechanics with at most one coupling and the couplings they gain

Generated on 2026-11-14 from the interconnection registry (572 mechanics). Each gains the couplings in the last column under 50.14.

| Mechanic | Subsystem | Couplings now | Couplings gained (subsystem: effect) |
|---|---|---|---|
| `anatomy` | body | 1 | war: body plan sets reach, armour fit and mount use; household: body plan sets dwelling and furnishing needs |
| `body_functions` | body | 1 | economy: senses and strength set work output by profession; social: lost senses change standing where wholeness norms apply |
| `cognitive_decline` | body | 1 | polity: an office holder's decline raises succession pressure; household: care load for the declining rises (50.5) |
| `wounded_and_learning` | body | 1 | war: veterans raise unit quality; demography: wounded return as maimed cohorts |
| `incidents` | core | 1 | mind: incidents plant memories; knowledge: incidents feed historiography and media (50.2) |
| `apocalypse_variants` | cosmos | 0 | polity: each variant's warnings move policies and alliances before the end; faith: millenarian movements read the variant |
| `clusters` | cosmos | 1 | cosmos: cluster medium sets star formation in member galaxies; knowledge: distance sets survey and route discovery |
| `cosmic_beings` | cosmos | 1 | faith: manifestations found cults and move piety; environment: a being's acts scar regions and change danger |
| `cosmic_features` | cosmos | 0 | economy: asteroid riches feed mining and trade; war: pirates and wormhole control set route safety and campaigns |
| `cosmic_influence` | cosmos | 0 | magic: position and phenomena set magic strength in regions; ecology: fertility changes reach harvests and species |
| `impacts` | cosmos | 0 | demography: impacts kill and displace; polity: warnings move granary and migration policy |
| `natural_law_fertility` | cosmos | 1 | demography: fertility laws move births; economy: harvest fertility moves food supply |
| `regional_leak` | cosmos | 1 | faith: leak raises outer cults and doubt; demography: leak pushes people away |
| `rifts` | cosmos | 1 | cosmos: rifts open passages and leak; demography: rifts displace people |
| `star_systems` | cosmos | 0 | environment: the temperate band sets world climates; knowledge: system structure sets navigation |
| `stellar_evolution` | cosmos | 1 | demography: a star's change moves habitability and migration; faith: star changes become omens |
| `voyages` | cosmos | 1 | economy: cargo moves goods and prices; culture: passengers carry customs and language |
| `ghost_legends` | culture | 1 | demography: hauntings keep people from places and move settlement; faith: legends raise spirit worship or exorcism |
| `legacy_traits` | culture | 1 | war: martial styles carry into the successor's armies; faith: rites and beliefs carry into its cults |
| `legend_memories` | culture | 0 | mind: false memories move opinions; polity: legends support claims and legitimacy |
| `route_renown` | culture | 0 | economy: renowned roads draw traffic and inns (50.3); faith: renowned roads become pilgrim ways |
| `human_sacrifice_deaths` | demography | 1 | polity: other peoples' horror moves relations and war causes; faith: sacrifice feeds the god's essence where doctrine says |
| `rebirth_paths` | demography | 1 | household: reborn souls return to houses with memories where doctrine says; faith: rebirth success moves piety |
| `hunting_grounds` | ecology | 1 | social: hunting rights and poaching drive disputes; body: hunting carries exposures (47.10) |
| `life_classes` | ecology | 0 | demography: peoples arise only where life is complex; economy: life classes set the species products available |
| `species_goods` | ecology | 1 | social: rights to grounds drive disputes; ecology: overuse depletes species |
| `arms_and_wear` | economy | 1 | war: weapon mix and condition set battle factors; polity: re-arming costs treasury |
| `deposits` | economy | 1 | economy: revealed reserves open extraction and prices; war: rich deposits become war aims |
| `divine_materials` | economy | 1 | war: new materials change arms and armour factors; faith: divine materials become sacred goods |
| `economic_indicators` | economy | 0 | polity: indicators move policy choices, unrest and legitimacy; mind: living standards move stress and happiness |
| `economy_holds` | economy | 0 | gods: holds are god acts recorded with their actor; polity: held stores and workers are excluded from taxation and levies while held |
| `food_chain` | economy | 1 | economy: method chains set prices and stocks; body: preserved food quality sets nutrition and illness |
| `markets` | economy | 1 | polity: prices move unrest and policy; household: prices move basket and living standard |
| `mercenaries_and_debt` | economy | 1 | polity: debt and debasement move legitimacy and credit; social: unpaid mercenaries raid and riot |
| `mine_support` | economy | 1 | economy: collapses cut output and raise costs; demography: mine deaths reduce population and raise grief |
| `patrols` | economy | 1 | polity: patrol cost and route safety move trade income; social: banditry falls and rises with patrols |
| `polity_production` | economy | 1 | war: bottlenecks limit armament; social: shortages raise unrest |
| `regrowth` | economy | 0 | ecology: regeneration sets species and forest recovery; polity: depletion moves policy and conquest |
| `route_holds` | economy | 1 | economy: held routes stop trade on them; polity: held routes change war and supply plans |
| `salvage` | economy | 1 | war: salvaged arms re-equip stacks; polity: salvage enriches the victor's treasury |
| `substitution` | economy | 1 | economy: substitution moves demand and prices across a family; household: it moves basket composition |
| `temple_loot` | economy | 1 | faith: looted faiths turn hostile; social: looting raises grievance and feuds |
| `tool_wear` | economy | 1 | economy: worn tools cut output; household: tool replacement cost moves basket |
| `typed_resource_mechanics` | economy | 1 | economy: decay, addiction and sacred limits move supply and price; faith: sacred resources move piety when used |
| `workshop_designs` | economy | 1 | polity: designs spread by trade and conquest; knowledge: designs advance technique |
| `environment_layers` | environment | 0 | faith: sacred layers draw pilgrims and temples; demography: danger and scars push migration |
| `planetary_climate` | environment | 0 | ecology: climate ages move species ranges and extinctions; demography: harvests and migration follow climate |
| `regional_climate` | environment | 1 | economy: regional shifts move harvests and prices; demography: migration follows habitability |
| `terraforming` | environment | 0 | ecology: native life declines or adapts; demography: new habitability draws settlers |
| `weather_exposure` | environment | 1 | war: exposure losses weaken armies; demography: exposure deaths among travellers and the poor |
| `world_physics` | environment | 1 | ecology: gravity, air and light set what life fits; economy: day and year lengths set work calendars |
| `celestial_omens` | faith | 1 | polity: omen readings move rulers' decisions and legitimacy; demography: ominous signs delay unions and births where believed |
| `faith_backfill` | faith | 1 | household: funeral rites and rebirth paths reach households; demography: rebirth paths route souls back to peoples |
| `faith_incidents` | faith | 1 | polity: crusades and inquisitions move legitimacy and wars; social: iconoclasm and persecution raise unrest |
| `heresies` | faith | 1 | polity: suppression costs and unrest; social: heresies split communities and start movements |
| `missions_journeys` | faith | 1 | culture: missionaries carry language and customs; polity: missions move alliances and conflicts |
| `saint_bones` | faith | 1 | economy: relics draw pilgrims and gifts; polity: relic possession supports legitimacy |
| `strata_routing` | faith | 1 | household: kin expect routing by rites and act on it; social: routing doctrines move behaviour toward the favoured deeds |
| `avatars` | gods | 1 | polity: an avatar's presence moves legitimacy and alliances; war: an avatar in battle lifts morale and draws enemy fire |
| `mortal_births` | household | 0 | demography: births set population by people and class; household: births raise care load and housework (50.5, 50.9) |
| `mortal_death_record` | household | 0 | social: manner of death moves house prestige and feuds; faith: manner of death sets afterlife routing |
| `mortal_kin` | household | 0 | law: unions and divorces become legal acts with property effects; economy: dowries and inheritance move wealth |
| `mortal_life_course` | household | 0 | economy: life stages set who works; polity: age sets eligibility for office |
| `spy_agents` | intrigue | 1 | polity: revealed aims move diplomacy; social: exposed spies raise distrust |
| `knowledge_gated_extraction` | knowledge | 1 | polity: gated resources become reasons for research agreements and conquest; social: holders of the knowledge gain standing |
| `reverse_engineering` | knowledge | 1 | war: copied arms change battle factors; law: copying breaks incorporeal rights |
| `specialised_scholars` | knowledge | 1 | economy: specialised branches raise their methods' output; polity: scholars become court assets |
| `world_surveys` | knowledge | 0 | polity: survey level sets colonisation and war reach; economy: survey level sets trade between worlds |
| `mortal_justice` | law | 0 | social: sentences move infamy and kin shame; demography: exile and executions move population |
| `pardons` | law | 1 | social: pardons move faction favour and grievance; mind: pardoned mortals gain gratitude memories |
| `precedents` | law | 1 | polity: binding rulings constrain rulers' acts; social: harsh precedent raises grievance |
| `research_agreements` | law | 1 | polity: agreements bind relations and are broken in war; economy: shared techniques raise production |
| `ley_attunement` | magic | 1 | economy: attuned works yield more; polity: control of nexuses becomes a war aim |
| `conviction` | mind | 1 | mind: conviction slows belief change; social: high conviction raises renown and rivalry |
| `drink_need` | mind | 1 | economy: drink demand drives brewing and trade; social: drinking customs shape circles and brawls |
| `grief` | mind | 1 | household: grief lowers work and care for its length; social: grief drives vengeance or reconciliation |
| `mortal_loyalty` | mind | 1 | polity: loyalty sets plots, desertion and service; faith: loyalty to god sets conversion |
| `mortal_stress` | mind | 1 | social: breaks start quarrels and violence; body: long stress raises illness |
| `quirks` | mind | 1 | social: quirks change interactions and standing; economy: quirks change work output for some professions |
| `army_command` | polity | 1 | war: officers' traits choose tactics and stance in battle; mind: command success and failure move officers' stress and renown |
| `church_and_crown` | polity | 1 | faith: investiture outcomes move clergy loyalty and heresy; law: who holds courts of faith follows the outcome |
| `ethnic_relations` | polity | 1 | social: strife raises riots and feuds; culture: harmony raises culture exchange and mixed unions |
| `tolls` | polity | 1 | economy: tolls move prices and route choice; polity: toll income funds the holder |
| `war_causes_and_peace` | polity | 1 | law: treaty clauses become obligations with breaches; social: war aims move war support |
| `ancestral_guardians` | social | 1 | war: morale lift on ancestral ground; faith: veneration feeds ancestral rites and their cost |
| `attraction` | social | 1 | social: attraction drives courtship, affairs and rivalry; law: intimacy norms (50.8) judge the bonds it starts |
| `captive_depth` | social | 1 | polity: ransoms move treasuries and treaties; demography: captives assimilate into the captor people over generations |
| `feuds` | social | 1 | law: feuds become cases and wergild clauses; polity: house feuds weaken councils and successions |
| `mortal_acts` | social | 0 | polity: careers fill offices and armies; economy: careers set labour supply by profession |
| `mortal_standing` | social | 1 | economy: wealth funds works and patronage; social: renown and infamy set alliances and marriages |
| `peace_movement` | social | 1 | polity: movements force peace terms and change rulers; culture: peace movements leave commemorations |
| `pecking_orders` | social | 1 | polity: rank in courts sets office access; mind: low rank raises stress and ambition |
| `popular_movements` | social | 1 | law: movements change laws when they win; faith: religious movements found cults |
| `abductors` | war | 1 | household: a carried-off member leaves a household short of labour and in grief; faith: captives freed by a hero or a god raise that patron's piety |
| `battle_ground_record` | war | 1 | culture: famous battlefields become legends and pilgrimage sites; faith: battlefields with many dead raise hauntings where spirits exist |
| `duel_ordeals` | war | 1 | social: duel outcomes move honour and feuds; polity: trials by combat settle claims and successions |
| `engine_designs` | war | 1 | economy: building engines consumes materials and coin; polity: engine superiority shifts war aims and treaties |
| `levies` | war | 1 | economy: levies take labour from fields and workshops; household: levied members leave households short (50.5) |
| `lost_lands` | war | 1 | polity: irredentist claims start wars; culture: anniversaries become commemorations |
| `mortal_equipment` | war | 0 | economy: equipment demand drives smiths and trade; social: fine equipment raises standing |
| `phased_battle_decides` | war | 1 | economy: battle outcomes set loot and losses; demography: casualties reduce populations |
| `resource_conflict` | war | 1 | polity: resource wars change borders and treaties; demography: war losses |

### Appendix 50.C — Every UNESCO sub-discipline of the natural world and the cosmos

Generated on 2026-11-14 from the six-digit UNESCO nomenclature (TESEO list) for fields 21, 24 and 25, names in the list's own language. Status was measured as in 50.0, and each item is closed by the named section. W44 step 0 copies this table to `docs/spec/science-coverage.md`.

| Code | Sub-discipline | Measured status | Closed by |
|---|---|---|---|
| 210101 | Estrellas Dobles | own state and behaviour in code | code (stars, galaxies, clusters, cosmic features; spec 13 10.9–10.16); W48 48.8 |
| 210102 | Cumulos | own state and behaviour in code | code (stars, galaxies, clusters, cosmic features; spec 13 10.9–10.16); W48 48.8 |
| 210103 | Rayos Cosmicos | some typed state in code | code (stars, galaxies, clusters, cosmic features; spec 13 10.9–10.16); W48 48.8 |
| 210104 | Galaxias | own state and behaviour in code | code (stars, galaxies, clusters, cosmic features; spec 13 10.9–10.16); W48 48.8 |
| 210105 | Gravitacion | some typed state in code | code (stars, galaxies, clusters, cosmic features; spec 13 10.9–10.16); W48 48.8 |
| 210106 | Nebulosas | a label only | code (stars, galaxies, clusters, cosmic features; spec 13 10.9–10.16); W48 48.8 |
| 210107 | Novas | a label only | code (stars, galaxies, clusters, cosmic features; spec 13 10.9–10.16); W48 48.8 |
| 210108 | Pulsares | a label only | code (stars, galaxies, clusters, cosmic features; spec 13 10.9–10.16); W48 48.8 |
| 210109 | Quasares | a label only | code (stars, galaxies, clusters, cosmic features; spec 13 10.9–10.16); W48 48.8 |
| 210110 | Estrellas | own state and behaviour in code | code (stars, galaxies, clusters, cosmic features; spec 13 10.9–10.16); W48 48.8 |
| 210111 | Evolucion Estelar Y Diagrama Hr | some typed state in code | code (stars, galaxies, clusters, cosmic features; spec 13 10.9–10.16); W48 48.8 |
| 210112 | Composicion Estelar | some typed state in code | code (stars, galaxies, clusters, cosmic features; spec 13 10.9–10.16); W48 48.8 |
| 210113 | Supernovas | a label only | code (stars, galaxies, clusters, cosmic features; spec 13 10.9–10.16); W48 48.8 |
| 210114 | Estrellas Variables | a label only | code (stars, galaxies, clusters, cosmic features; spec 13 10.9–10.16); W48 48.8 |
| 210115 | Fuentes De Rayos X | absent from code | **50.22** |
| 210201 | Campos Interplanetarios | absent from code | **50.22** |
| 210202 | Materia Interplanetaria | some typed state in code | code (cosmic features, routes) |
| 210203 | Particulas Interplanetarias | absent from code | **50.22** |
| 210301 | Astronomia De Posicion | own state and behaviour in code | **50.28**; also knowledge techniques (spec 13 8.4) and instruments (48.4) |
| 210302 | Telescopios | a label only | **50.28** |
| 210303 | Espectroscopia Astrofisica | absent from code | **50.28** |
| 210401 | Cometas | a label only | code (worlds, moons, world physics; spec 13 10.9, G1R.4.7) |
| 210402 | Meteoritos | own state and behaviour in code | code (worlds, moons, world physics; spec 13 10.9, G1R.4.7) |
| 210403 | Atmosfera Planetaria | own state and behaviour in code | code (worlds, moons, world physics; spec 13 10.9, G1R.4.7) |
| 210404 | Geologia Planetaria | absent from code | code (worlds, moons, world physics; spec 13 10.9, G1R.4.7) |
| 210405 | Fisica Planetaria | some typed state in code | code (worlds, moons, world physics; spec 13 10.9, G1R.4.7) |
| 210406 | Campos Magneticos Planetarios | absent from code | **50.22** |
| 210407 | Planetas | own state and behaviour in code | code (worlds, moons, world physics; spec 13 10.9, G1R.4.7) |
| 210408 | Satelites | some typed state in code | code (worlds, moons, world physics; spec 13 10.9, G1R.4.7) |
| 210409 | Tectitas | absent from code | code (worlds, moons, world physics; spec 13 10.9, G1R.4.7) |
| 210410 | La Luna | some typed state in code | code (worlds, moons, world physics; spec 13 10.9, G1R.4.7) |
| 210501 | Antenas Telescopicas | a label only | **50.28** |
| 210502 | Radiotelescopios | absent from code | **50.28** |
| 210601 | Energia Solar | a label only | **50.22** |
| 210602 | Fisica Solar | a label only | **50.22** |
| 210603 | Viento Solar | a label only | **50.22** |
| 210604 | El Sol | own state and behaviour in code | code (stars, stellar evolution) |
| 240101 | Anatomia Animal | own state and behaviour in code | code (species, anatomy, ecology, lineages, temperament); W48 48.5, 48.8 |
| 240102 | Comportamiento Animal | own state and behaviour in code | code (species, anatomy, ecology, lineages, temperament); W48 48.5, 48.8 |
| 240103 | Comunicacion Animal | own state and behaviour in code | code (species, anatomy, ecology, lineages, temperament); W48 48.5, 48.8 |
| 240104 | Citologia Animal | own state and behaviour in code | code (species, anatomy, ecology, lineages, temperament); W48 48.5, 48.8 |
| 240105 | Desarrollo Animal | some typed state in code | code (species, anatomy, ecology, lineages, temperament); W48 48.5, 48.8 |
| 240106 | Ecologia Animal | some typed state in code | code (species, anatomy, ecology, lineages, temperament); W48 48.5, 48.8 |
| 240107 | Embriologia Animal | absent from code | code (species, anatomy, ecology, lineages, temperament); W48 48.5, 48.8 |
| 240108 | Genetica Animal | own state and behaviour in code | code (species, anatomy, ecology, lineages, temperament); W48 48.5, 48.8 |
| 240109 | Crecimiento Animal | some typed state in code | code (species, anatomy, ecology, lineages, temperament); W48 48.5, 48.8 |
| 240110 | Histologia Animal | some typed state in code | code (species, anatomy, ecology, lineages, temperament); W48 48.5, 48.8 |
| 240111 | Patologia Animal | own state and behaviour in code | **50.24**; also code (species, anatomy, ecology, lineages, temperament); W48 48.5, 48.8 |
| 240112 | Parasitologia Animal | absent from code | **50.24** |
| 240113 | Fisiologia Animal | some typed state in code | code (species, anatomy, ecology, lineages, temperament); W48 48.5, 48.8 |
| 240114 | Taxonomia Animal | some typed state in code | code (species, anatomy, ecology, lineages, temperament); W48 48.5, 48.8 |
| 240115 | Zoologia General | own state and behaviour in code | code (species, anatomy, ecology, lineages, temperament); W48 48.5, 48.8 |
| 240116 | Herpetologia | absent from code | code (species, anatomy, ecology, lineages, temperament); W48 48.5, 48.8 |
| 240117 | Invertebrados | absent from code | code (species, anatomy, ecology, lineages, temperament); W48 48.5, 48.8 |
| 240118 | Mamiferos | absent from code | code (species, anatomy, ecology, lineages, temperament); W48 48.5, 48.8 |
| 240119 | Zoologia Marina | a label only | code (species, anatomy, ecology, lineages, temperament); W48 48.5, 48.8 |
| 240120 | Ornitologia | a label only | code (species, anatomy, ecology, lineages, temperament); W48 48.5, 48.8 |
| 240121 | Primates | absent from code | code (species, anatomy, ecology, lineages, temperament); W48 48.5, 48.8 |
| 240122 | Protozoologia | a label only | code (species, anatomy, ecology, lineages, temperament); W48 48.5, 48.8 |
| 240123 | Vertebrados | absent from code | code (species, anatomy, ecology, lineages, temperament); W48 48.5, 48.8 |
| 240124 | Ictiologia | a label only | code (species, anatomy, ecology, lineages, temperament); W48 48.5, 48.8 |
| 240125 | Invertebrados No Insectos | absent from code | code (species, anatomy, ecology, lineages, temperament); W48 48.5, 48.8 |
| 240126 | Bioquimica De La Taxonomia Animal | own state and behaviour in code | code (species, anatomy, ecology, lineages, temperament); W48 48.5, 48.8 |
| 240127 | Taxonomia De Invertebrados No Insectos | absent from code | code (species, anatomy, ecology, lineages, temperament); W48 48.5, 48.8 |
| 240129 | Taxonomia De Peces | a label only | code (species, anatomy, ecology, lineages, temperament); W48 48.5, 48.8 |
| 240130 | Mamiferos Ungulados | own state and behaviour in code | code (species, anatomy, ecology, lineages, temperament); W48 48.5, 48.8 |
| 240201 | Archivos Antropologicos | own state and behaviour in code | code (body, genetics, demography) |
| 240202 | Genetica Antropologica | some typed state in code | code (body, genetics, demography) |
| 240203 | Antropometria Y Antropologia Forense | some typed state in code | code (body, genetics, demography) |
| 240204 | Composicion Del Cuerpo | own state and behaviour in code | code (body, genetics, demography) |
| 240205 | Constitucion Del Cuerpo | own state and behaviour in code | code (body, genetics, demography) |
| 240206 | Etnologia | own state and behaviour in code | code (body, genetics, demography) |
| 240207 | Antropologia Medica | some typed state in code | code (body, genetics, demography) |
| 240208 | Habitos Alimentarios Antropologicos | own state and behaviour in code | code (body, genetics, demography) |
| 240209 | Osteologia | some typed state in code | code (body, genetics, demography) |
| 240210 | Biologia De Poblaciones | own state and behaviour in code | code (body, genetics, demography) |
| 240211 | Comportamiento De Los Primates | absent from code | code (body, genetics, demography) |
| 240212 | Somatologia De Los Primates | own state and behaviour in code | code (body, genetics, demography) |
| 240214 | Desarrollo Somatico | some typed state in code | code (body, genetics, demography) |
| 240215 | Envejecimiento Somatico | some typed state in code | code (body, genetics, demography) |
| 240401 | Bioestadistica | absent from code | knowledge (statistics as a branch); engine metrics |
| 240601 | Bioacustica | own state and behaviour in code | code (body capacities, F23) |
| 240602 | Bioelectricidad | a label only | code (body capacities, F23) |
| 240603 | Bioenergetica | own state and behaviour in code | code (body capacities, F23) |
| 240604 | Biomecanica | own state and behaviour in code | code (body capacities, F23) |
| 240605 | Biooptica | own state and behaviour in code | code (body capacities, F23) |
| 240606 | Fisica Medica | absent from code | code (body capacities, F23) |
| 240701 | Cultivo Celular | absent from code | below the engine's scale: read through tissues (F23), heredity and disease agents (50.24) |
| 240702 | Citogenetica | absent from code | below the engine's scale: read through tissues (F23), heredity and disease agents (50.24) |
| 240703 | Morfologia Celular | absent from code | below the engine's scale: read through tissues (F23), heredity and disease agents (50.24) |
| 240704 | Citologia | own state and behaviour in code | below the engine's scale: read through tissues (F23), heredity and disease agents (50.24) |
| 240705 | Cultivo De Tejidos | absent from code | below the engine's scale: read through tissues (F23), heredity and disease agents (50.24) |
| 240706 | Estructura De La Pared Celular | absent from code | below the engine's scale: read through tissues (F23), heredity and disease agents (50.24) |
| 240801 | Etologia Animal | own state and behaviour in code | code (behaviour, temperament, hives and herds) |
| 240802 | Etologia Humana | own state and behaviour in code | code (behaviour, temperament, hives and herds) |
| 240803 | Etologia De Insectos | own state and behaviour in code | code (behaviour, temperament, hives and herds) |
| 240804 | Etologia De Mamiferos Ungulados | own state and behaviour in code | code (behaviour, temperament, hives and herds) |
| 240901 | Embriologia | absent from code | code (genetics, lineages); W46 46.3 design; below scale where molecular |
| 240902 | Ingenieria Genetica | absent from code | code (genetics, lineages); W46 46.3 design; below scale where molecular |
| 240903 | Genetica De Poblaciones | own state and behaviour in code | code (genetics, lineages); W46 46.3 design; below scale where molecular |
| 240904 | Citogenetica Animal | absent from code | code (genetics, lineages); W46 46.3 design; below scale where molecular |
| 240905 | Genetica Del Desarrollo | absent from code | code (genetics, lineages); W46 46.3 design; below scale where molecular |
| 240906 | Genetica Molecular | some typed state in code | code (genetics, lineages); W46 46.3 design; below scale where molecular |
| 240907 | Genetica Molecular De Plantas | absent from code | code (genetics, lineages); W46 46.3 design; below scale where molecular |
| 240908 | Genetica Molecular De Levaduras | absent from code | code (genetics, lineages); W46 46.3 design; below scale where molecular |
| 240909 | Sintesis De Oligonucleotidos | a label only | code (genetics, lineages); W46 46.3 design; below scale where molecular |
| 241001 | Grupo Sanguineo | own state and behaviour in code | code (body, life course, genetics); spec 13 W34 senses |
| 241002 | Anatomia Humana | some typed state in code | code (body, life course, genetics); spec 13 W34 senses |
| 241003 | Citologia Humana | absent from code | code (body, life course, genetics); spec 13 W34 senses |
| 241004 | Desarrollo Humano | some typed state in code | code (body, life course, genetics); spec 13 W34 senses |
| 241005 | Ecologia Humana | absent from code | code (body, life course, genetics); spec 13 W34 senses |
| 241006 | Embriologia Humana | absent from code | code (body, life course, genetics); spec 13 W34 senses |
| 241007 | Genetica Humana | absent from code | code (body, life course, genetics); spec 13 W34 senses |
| 241008 | Histologia Humana | some typed state in code | code (body, life course, genetics); spec 13 W34 senses |
| 241009 | Neuroanatomia Humana | some typed state in code | code (body, life course, genetics); spec 13 W34 senses |
| 241011 | Organos Sensoriales | own state and behaviour in code | code (body, life course, genetics); spec 13 W34 senses |
| 241012 | Anatomia Sistematica | some typed state in code | code (body, life course, genetics); spec 13 W34 senses |
| 241013 | Anatomia Topografica | some typed state in code | code (body, life course, genetics); spec 13 W34 senses |
| 241101 | Fisiologia Del Equilibrio | own state and behaviour in code | **50.25**; also code (body functions, exertion, F23); spec 13 W34 thermoregulation |
| 241102 | Anestesiologia | some typed state in code | code (body functions, exertion, F23); spec 13 W34 thermoregulation |
| 241103 | Fisiologia Cardiovascular | own state and behaviour in code | **50.25**; also code (body functions, exertion, F23); spec 13 W34 thermoregulation |
| 241104 | Fisiologia Endocrina | absent from code | **50.25** |
| 241105 | Fisiologia Ambiental | some typed state in code | **50.25**; also code (body functions, exertion, F23); spec 13 W34 thermoregulation |
| 241106 | Fisiologia Del Ejercicio | some typed state in code | code (body functions, exertion, F23); spec 13 W34 thermoregulation |
| 241107 | Fisiologia Gastrointestinal | absent from code | **50.25** |
| 241108 | Metabolismo Humano | some typed state in code | **50.25**; also code (body functions, exertion, F23); spec 13 W34 thermoregulation |
| 241109 | Regulacion De La Temperatura Humana | some typed state in code | code (body functions, exertion, F23); spec 13 W34 thermoregulation |
| 241110 | Fisiologia Muscular | some typed state in code | code (body functions, exertion, F23); spec 13 W34 thermoregulation |
| 241111 | Neurofisiologia Humana | some typed state in code | code (body functions, exertion, F23); spec 13 W34 thermoregulation |
| 241112 | Fisiologia Del Sistema Nervioso Central | a label only | **50.25** |
| 241113 | Fisiologia De La Audicion | some typed state in code | code (body functions, exertion, F23); spec 13 W34 thermoregulation |
| 241114 | Fisiologia Del Lenguaje | some typed state in code | code (body functions, exertion, F23); spec 13 W34 thermoregulation |
| 241115 | Fisiologia De La Vision | own state and behaviour in code | code (body functions, exertion, F23); spec 13 W34 thermoregulation |
| 241116 | Fisiologia De La Reproduccion | own state and behaviour in code | code (body functions, exertion, F23); spec 13 W34 thermoregulation |
| 241117 | Fisiologia De La Respiracion | some typed state in code | **50.25**; also code (body functions, exertion, F23); spec 13 W34 thermoregulation |
| 241118 | Fisiologia Del Movimiento | own state and behaviour in code | code (body functions, exertion, F23); spec 13 W34 thermoregulation |
| 241201 | Antigenos | own state and behaviour in code | code (immunities, vaccination); W46 grown organs |
| 241202 | Anticuerpos | own state and behaviour in code | code (immunities, vaccination); W46 grown organs |
| 241203 | Reaccion Antigeno-Anticuerpo | own state and behaviour in code | code (immunities, vaccination); W46 grown organs |
| 241204 | Formacion De Anticuerpos | own state and behaviour in code | code (immunities, vaccination); W46 grown organs |
| 241205 | Hipersensibilidad | absent from code | **50.25** |
| 241206 | Inmunizacion | some typed state in code | code (immunities, vaccination); W46 grown organs |
| 241207 | Inmunoquimica | own state and behaviour in code | code (immunities, vaccination); W46 grown organs |
| 241208 | Trasplante De Organos | some typed state in code | code (immunities, vaccination); W46 grown organs |
| 241209 | Anticuerpos De Tejidos | own state and behaviour in code | code (immunities, vaccination); W46 grown organs |
| 241210 | Vacunas | some typed state in code | code (immunities, vaccination); W46 grown organs |
| 241301 | Entomologia General | a label only | code (species classes, insectoid plans, crop pests, swarms) |
| 241302 | Desarrollo De Los Insectos | absent from code | code (species classes, insectoid plans, crop pests, swarms) |
| 241303 | Ecologia De Los Insectos | a label only | code (species classes, insectoid plans, crop pests, swarms) |
| 241304 | Morfologia De Los Insectos | a label only | code (species classes, insectoid plans, crop pests, swarms) |
| 241305 | Fisiologia De Los Insectos | a label only | code (species classes, insectoid plans, crop pests, swarms) |
| 241306 | Taxonomia De Los Insectos | a label only | code (species classes, insectoid plans, crop pests, swarms) |
| 241307 | Endocrinologia De Los Insectos | a label only | code (species classes, insectoid plans, crop pests, swarms) |
| 241401 | Antibioticos | absent from code | **50.24** |
| 241402 | Fisiologia Bacteriana | absent from code | **50.24** |
| 241403 | Metabolismo Bacteriano | absent from code | **50.24** |
| 241404 | Bacteriologia | absent from code | **50.24** |
| 241405 | Bacteriofagia | absent from code | **50.24** |
| 241406 | Micologia | a label only | **50.24** |
| 241407 | Metabolismo Microbiano | a label only | spec 13 W34 microbes; code (fermentation methods) |
| 241408 | Procesos Microbianos | a label only | spec 13 W34 microbes; code (fermentation methods) |
| 241409 | Mohos | absent from code | **50.24** |
| 241410 | Levaduras | a label only | spec 13 W34 microbes; code (fermentation methods) |
| 241411 | Degradacion De Residuos Vegetales | own state and behaviour in code | spec 13 W34 microbes; code (fermentation methods) |
| 241501 | Biologia Molecular De Microorganismos | a label only | below scale: W46 46.3 |
| 241502 | Biologia Molecular De Plantas | absent from code | below scale: W46 46.3 |
| 241601 | Paleontologia Animal | absent from code | **50.27** on spec 13 6.2 reference pass 7 |
| 241602 | Paleontologia De Los Invertebrados | absent from code | **50.27** on spec 13 6.2 reference pass 7 |
| 241603 | Palinologia | absent from code | **50.27** on spec 13 6.2 reference pass 7 |
| 241604 | Paleontologia De Las Plantas | absent from code | **50.27** on spec 13 6.2 reference pass 7 |
| 241605 | Paleontologia De Los Vertebrados | absent from code | **50.27** on spec 13 6.2 reference pass 7 |
| 241701 | Briologia | a label only | code (flora, species, perennials, crop pests); spec 13 W34 plant defences |
| 241702 | Dendrologia | own state and behaviour in code | code (flora, species, perennials, crop pests); spec 13 W34 plant defences |
| 241703 | Botanica General | own state and behaviour in code | **50.26**; also code (flora, species, perennials, crop pests); spec 13 W34 plant defences |
| 241704 | Flora Lacustre | absent from code | code (flora, species, perennials, crop pests); spec 13 W34 plant defences |
| 241705 | Botanica Marina | absent from code | code (flora, species, perennials, crop pests); spec 13 W34 plant defences |
| 241706 | Setas | a label only | code (flora, species, perennials, crop pests); spec 13 W34 plant defences |
| 241707 | Algologia | absent from code | code (flora, species, perennials, crop pests); spec 13 W34 plant defences |
| 241708 | Fitobiologia | own state and behaviour in code | **50.26**; also code (flora, species, perennials, crop pests); spec 13 W34 plant defences |
| 241709 | Fitopatologia | a label only | code (flora, species, perennials, crop pests); spec 13 W34 plant defences |
| 241710 | Paleobotanica | absent from code | **50.27** on spec 13 6.2 reference pass 7 |
| 241711 | Anatomia Vegetal | absent from code | **50.26** |
| 241712 | Citologia Vegetal | absent from code | **50.26** |
| 241713 | Ecologia Vegetal | own state and behaviour in code | code (flora, species, perennials, crop pests); spec 13 W34 plant defences |
| 241714 | Genetica Vegetal | absent from code | code (flora, species, perennials, crop pests); spec 13 W34 plant defences |
| 241715 | Desarrollo Vegetal | some typed state in code | **50.26**; also code (flora, species, perennials, crop pests); spec 13 W34 plant defences |
| 241716 | Histologia Vegetal | absent from code | **50.26** |
| 241717 | Nutricion Vegetal | own state and behaviour in code | code (flora, species, perennials, crop pests); spec 13 W34 plant defences |
| 241718 | Parasitologia Vegetal | own state and behaviour in code | code (flora, species, perennials, crop pests); spec 13 W34 plant defences |
| 241719 | Fisiologia Vegetal | a label only | **50.26** |
| 241720 | Taxonomia Vegetal | absent from code | **50.26** |
| 241721 | Pteridologia | a label only | code (flora, species, perennials, crop pests); spec 13 W34 plant defences |
| 241722 | Fijacion Y Movilizacion Biologica De Nutrientes | own state and behaviour in code | code (flora, species, perennials, crop pests); spec 13 W34 plant defences |
| 241723 | Fijacion Biologica Del Nitrogeno | some typed state in code | code (flora, species, perennials, crop pests); spec 13 W34 plant defences |
| 241724 | Fisiologia De La Maduracion | own state and behaviour in code | code (flora, species, perennials, crop pests); spec 13 W34 plant defences |
| 241725 | Recursos Fitogeneticos | own state and behaviour in code | code (flora, species, perennials, crop pests); spec 13 W34 plant defences |
| 241726 | Taxonomia De Plantas Vasculares | own state and behaviour in code | **50.26**; also code (flora, species, perennials, crop pests); spec 13 W34 plant defences |
| 241727 | Flora Mediterranea | some typed state in code | code (flora, species, perennials, crop pests); spec 13 W34 plant defences |
| 242001 | Arbovirus | some typed state in code | **50.24** |
| 242002 | Bacteriofagos | absent from code | **50.24** |
| 242003 | Virus Dermatropicos | absent from code | **50.24** |
| 242004 | Enterovirus | absent from code | **50.24** |
| 242005 | Virus Neurotropicos | absent from code | **50.24** |
| 242006 | Virus Pantropicos | absent from code | **50.24** |
| 242007 | Poxvirus | absent from code | **50.24** |
| 242008 | Virus Respiratorios | absent from code | **50.24** |
| 242009 | Virus Viscerotropicos | absent from code | **50.24** |
| 242010 | Virologia Animal | absent from code | **50.24** |
| 242011 | Retrovirus | absent from code | **50.24** |
| 242101 | Neurofisiologia | some typed state in code | code (nerves, F23 tissues); F50 minds |
| 242102 | Neuroquimica | absent from code | code (nerves, F23 tissues); F50 minds |
| 242103 | Neurobiologia Molecular | absent from code | code (nerves, F23 tissues); F50 minds |
| 250101 | Aeronomia | absent from code | **50.22** |
| 250102 | Luminiscencia Atmosferica | absent from code | **50.22** |
| 250103 | Interacciones Mar-Aire | a label only | code (climate, weather, winds, rain shadows W31) |
| 250104 | Acustica Atmosferica | some typed state in code | code (climate, weather, winds, rain shadows W31) |
| 250105 | Quimica Atmosferica | own state and behaviour in code | code (climate, weather, winds, rain shadows W31) |
| 250106 | Dinamica Atmosferica | own state and behaviour in code | code (climate, weather, winds, rain shadows W31) |
| 250107 | Electricidad Atmosferica | a label only | code (climate, weather, winds, rain shadows W31) |
| 250108 | Optica Atmosferica | a label only | code (climate, weather, winds, rain shadows W31) |
| 250109 | Radiactividad Atmosferica | some typed state in code | code (climate, weather, winds, rain shadows W31) |
| 250110 | Estructura Atmosferica | some typed state in code | code (climate, weather, winds, rain shadows W31) |
| 250111 | Termodinamica Atmosferica | some typed state in code | code (climate, weather, winds, rain shadows W31) |
| 250112 | Turbulencia Atmosferica | absent from code | code (climate, weather, winds, rain shadows W31) |
| 250113 | Auroras | some typed state in code | **50.22**; also code (climate, weather, winds, rain shadows W31) |
| 250114 | Fisica De Las Nubes | a label only | code (climate, weather, winds, rain shadows W31) |
| 250115 | Efectos De La Radiacion Cosmica En La Atmosfera | absent from code | **50.22** |
| 250116 | Difusion Atmosferica | absent from code | code (climate, weather, winds, rain shadows W31) |
| 250117 | Pulsaciones Geomagneticas | absent from code | **50.22** |
| 250118 | Ionosfera | absent from code | **50.22** |
| 250119 | Particulas Magnetosfericas | absent from code | **50.22** |
| 250120 | Ondas Magnetosfericas | absent from code | **50.22** |
| 250121 | Modelos Numericos De La Atmosfera | own state and behaviour in code | **50.28**; also code (climate, weather, winds, rain shadows W31) |
| 250122 | Fisica De La Precipitacion | own state and behaviour in code | code (climate, weather, winds, rain shadows W31) |
| 250123 | Transferencia Radiactiva | some typed state in code | code (climate, weather, winds, rain shadows W31) |
| 250124 | Efectos Del Viento Solar En La Atmosfera | a label only | **50.22** |
| 250125 | Energia Eolica | a label only | code (climate, weather, winds, rain shadows W31) |
| 250201 | Climatologia Analitica | own state and behaviour in code | code (climate, climate ages, regional climate W31) |
| 250202 | Climatologia Aplicada | own state and behaviour in code | code (climate, climate ages, regional climate W31) |
| 250203 | Bioclimatologia | some typed state in code | code (climate, climate ages, regional climate W31) |
| 250204 | Microclimatologia | absent from code | **50.23** |
| 250205 | Paleoclimatologia | a label only | code (climate, climate ages, regional climate W31) |
| 250206 | Climatologia Fisica | own state and behaviour in code | code (climate, climate ages, regional climate W31) |
| 250207 | Climatologia Regional | own state and behaviour in code | code (climate, climate ages, regional climate W31) |
| 250208 | Climatologia De Montaña | some typed state in code | code (climate, climate ages, regional climate W31) |
| 250209 | Cambio Climatico | absent from code | code (climate, climate ages, regional climate W31) |
| 250301 | Cosmoquimica | absent from code | spec 13 G1R.3.1 layered geology; materials (F23); code (dating) |
| 250302 | Petrologia Experimental | some typed state in code | spec 13 G1R.3.1 layered geology; materials (F23); code (dating) |
| 250303 | Geoquimica Exploratoria | some typed state in code | spec 13 G1R.3.1 layered geology; materials (F23); code (dating) |
| 250304 | Geocronologia Y Radioisotopos | own state and behaviour in code | spec 13 G1R.3.1 layered geology; materials (F23); code (dating) |
| 250305 | Geoquimica De Altas Temperaturas | absent from code | spec 13 G1R.3.1 layered geology; materials (F23); code (dating) |
| 250306 | Geoquimica De Bajas Temperaturas | absent from code | spec 13 G1R.3.1 layered geology; materials (F23); code (dating) |
| 250307 | Geoquimica Organica | own state and behaviour in code | spec 13 G1R.3.1 layered geology; materials (F23); code (dating) |
| 250308 | Isotopos Estables | absent from code | spec 13 G1R.3.1 layered geology; materials (F23); code (dating) |
| 250309 | Distribucion De Oligoelementos | own state and behaviour in code | spec 13 G1R.3.1 layered geology; materials (F23); code (dating) |
| 250310 | Geoquimica Sedimentaria | absent from code | **50.23** |
| 250401 | Astronomia Geodesica | some typed state in code | knowledge (cartography, surveys) |
| 250402 | Cartografia Geodesica | own state and behaviour in code | knowledge (cartography, surveys) |
| 250403 | Navegacion Geodesica | a label only | **50.28** |
| 250404 | Fotogrametria Geodesica | absent from code | **50.28** |
| 250405 | Levantamiento Geodesico | own state and behaviour in code | **50.28**; also knowledge (cartography, surveys) |
| 250406 | Geodesia Fisica | some typed state in code | knowledge (cartography, surveys) |
| 250407 | Geodesia De Satelites | absent from code | **50.28** |
| 250408 | Geodesia Teorica | a label only | knowledge (cartography, surveys) |
| 250409 | Redes Geodesicas Y Deformaciones | absent from code | knowledge (cartography, surveys) |
| 250501 | Biogeografia | own state and behaviour in code | code (regions, terrain, land use rings, endemic diseases); spec 13 G1R.23.7 biogeography |
| 250502 | Cartografia Geografica | own state and behaviour in code | code (regions, terrain, land use rings, endemic diseases); spec 13 G1R.23.7 biogeography |
| 250503 | Geografia De Los Recursos Naturales | own state and behaviour in code | code (regions, terrain, land use rings, endemic diseases); spec 13 G1R.23.7 biogeography |
| 250504 | Usos Del Suelo | absent from code | code (regions, terrain, land use rings, endemic diseases); spec 13 G1R.23.7 biogeography |
| 250505 | Teoria De La Localizacion Geografica | own state and behaviour in code | code (regions, terrain, land use rings, endemic diseases); spec 13 G1R.23.7 biogeography |
| 250506 | Geografia Medica | absent from code | code (regions, terrain, land use rings, endemic diseases); spec 13 G1R.23.7 biogeography |
| 250507 | Geografia Fisica | own state and behaviour in code | code (regions, terrain, land use rings, endemic diseases); spec 13 G1R.23.7 biogeography |
| 250508 | Geografia Topografica | some typed state in code | code (regions, terrain, land use rings, endemic diseases); spec 13 G1R.23.7 biogeography |
| 250509 | Biogeografia Botanica | absent from code | code (regions, terrain, land use rings, endemic diseases); spec 13 G1R.23.7 biogeography |
| 250510 | Geografia De Montaña | some typed state in code | code (regions, terrain, land use rings, endemic diseases); spec 13 G1R.23.7 biogeography |
| 250601 | Geologia Regional | own state and behaviour in code | spec 13 G1R.3.1, G1R.3.2, G1R.4.7; code (deposits, extraction, volcanism); W47 47.2 geothermal |
| 250602 | Geologia Del Carbon | own state and behaviour in code | **50.27**; also spec 13 G1R.3.1, G1R.3.2, G1R.4.7; code (deposits, extraction, volcanism); W47 47.2 geothermal |
| 250603 | Geologia Aplicada A La Ingenieria | some typed state in code | spec 13 G1R.3.1, G1R.3.2, G1R.4.7; code (deposits, extraction, volcanism); W47 47.2 geothermal |
| 250604 | Geologia Ambiental | own state and behaviour in code | spec 13 G1R.3.1, G1R.3.2, G1R.4.7; code (deposits, extraction, volcanism); W47 47.2 geothermal |
| 250605 | Hidrogeologia | absent from code | spec 13 G1R.3.1, G1R.3.2, G1R.4.7; code (deposits, extraction, volcanism); W47 47.2 geothermal |
| 250606 | Exploraciones Geologicas | absent from code | **50.28** |
| 250607 | Geomorfologia | own state and behaviour in code | spec 13 G1R.3.1, G1R.3.2, G1R.4.7; code (deposits, extraction, volcanism); W47 47.2 geothermal |
| 250608 | Energia Geotermica | absent from code | spec 13 G1R.3.1, G1R.3.2, G1R.4.7; code (deposits, extraction, volcanism); W47 47.2 geothermal |
| 250609 | Geologia Glacial | a label only | **50.23** |
| 250610 | Yacimientos Minerales | own state and behaviour in code | spec 13 G1R.3.1, G1R.3.2, G1R.4.7; code (deposits, extraction, volcanism); W47 47.2 geothermal |
| 250611 | Mineralogia | own state and behaviour in code | spec 13 G1R.3.1, G1R.3.2, G1R.4.7; code (deposits, extraction, volcanism); W47 47.2 geothermal |
| 250612 | Geologia Del Petroleo | own state and behaviour in code | **50.27**; also spec 13 G1R.3.1, G1R.3.2, G1R.4.7; code (deposits, extraction, volcanism); W47 47.2 geothermal |
| 250613 | Petrologia Ignea Y Metamorfica | absent from code | spec 13 G1R.3.1, G1R.3.2, G1R.4.7; code (deposits, extraction, volcanism); W47 47.2 geothermal |
| 250614 | Petrologia Sedimentaria | absent from code | **50.23** |
| 250615 | Fotogeologia | absent from code | **50.28** |
| 250616 | Teledeteccion | absent from code | **50.28** |
| 250617 | Mecanica De Rocas | own state and behaviour in code | spec 13 G1R.3.1, G1R.3.2, G1R.4.7; code (deposits, extraction, volcanism); W47 47.2 geothermal |
| 250618 | Sedimentologia | absent from code | **50.23** |
| 250619 | Estratigrafia | own state and behaviour in code | spec 13 G1R.3.1, G1R.3.2, G1R.4.7; code (deposits, extraction, volcanism); W47 47.2 geothermal |
| 250620 | Geologia Estructural | some typed state in code | spec 13 G1R.3.1, G1R.3.2, G1R.4.7; code (deposits, extraction, volcanism); W47 47.2 geothermal |
| 250621 | Vulcanologia | some typed state in code | spec 13 G1R.3.1, G1R.3.2, G1R.4.7; code (deposits, extraction, volcanism); W47 47.2 geothermal |
| 250622 | Analisis De Diagrafias | absent from code | **50.28** |
| 250623 | Petrologia Sedimentaria Del Carbon | own state and behaviour in code | **50.27**; also spec 13 G1R.3.1, G1R.3.2, G1R.4.7; code (deposits, extraction, volcanism); W47 47.2 geothermal |
| 250624 | Paleontologia Estratigrafica | absent from code | **50.27** on spec 13 6.2 reference pass 7 |
| 250701 | Geomagnetismo Y Prospeccion Magnetica | absent from code | **50.22** |
| 250702 | Gravedad Terrestre Y Prospeccion Gravimetrica | some typed state in code | spec 13 G1R.4.7 tectonics; code (quakes, gravity) |
| 250703 | Flujos De Calor Terrestre | absent from code | spec 13 G1R.4.7 tectonics; code (quakes, gravity) |
| 250704 | Paleomagnetismo | absent from code | **50.22** |
| 250705 | Sismologia Y Prospeccion Sismica | a label only | spec 13 G1R.4.7 tectonics; code (quakes, gravity) |
| 250706 | Geofisica De La Masa Solida Terrestre | absent from code | spec 13 G1R.4.7 tectonics; code (quakes, gravity) |
| 250707 | Tectonica | own state and behaviour in code | spec 13 G1R.4.7 tectonics; code (quakes, gravity) |
| 250708 | Estructura Litosferica | absent from code | spec 13 G1R.4.7 tectonics; code (quakes, gravity) |
| 250801 | Erosion Del Agua | some typed state in code | spec 13 G1R.3.2, G1R.3.3; code (rainfall, lakes) |
| 250802 | Evaporacion | absent from code | **50.23** |
| 250803 | Glaciologia | a label only | **50.23** |
| 250804 | Aguas Subterraneas | absent from code | spec 13 G1R.3.2, G1R.3.3; code (rainfall, lakes) |
| 250805 | Hidrobiologia | a label only | spec 13 G1R.3.2, G1R.3.3; code (rainfall, lakes) |
| 250806 | Hidrografia | own state and behaviour in code | spec 13 G1R.3.2, G1R.3.3; code (rainfall, lakes) |
| 250807 | Hielo | own state and behaviour in code | **50.23**; also spec 13 G1R.3.2, G1R.3.3; code (rainfall, lakes) |
| 250808 | Limnologia | a label only | spec 13 G1R.3.2, G1R.3.3; code (rainfall, lakes) |
| 250809 | Suelo Helado | absent from code | **50.23** |
| 250810 | Precipitacion | own state and behaviour in code | spec 13 G1R.3.2, G1R.3.3; code (rainfall, lakes) |
| 250811 | Calidad De Las Aguas | own state and behaviour in code | spec 13 G1R.3.2, G1R.3.3; code (rainfall, lakes) |
| 250812 | Nieve | a label only | **50.23** |
| 250813 | Humedad Del Suelo | some typed state in code | spec 13 G1R.3.2, G1R.3.3; code (rainfall, lakes) |
| 250814 | Aguas Superficiales | own state and behaviour in code | spec 13 G1R.3.2, G1R.3.3; code (rainfall, lakes) |
| 250815 | Transpiracion | absent from code | **50.23** |
| 250901 | Meteorologia Agricola | absent from code | **50.28** |
| 250902 | Contaminacion Atmosferica | own state and behaviour in code | code (weather, storms, monsoons, forecasts) |
| 250903 | Prevision Meteorologica A Largo Plazo | own state and behaviour in code | **50.28**; also code (weather, storms, monsoons, forecasts) |
| 250904 | Hidrometeorologia | a label only | code (weather, storms, monsoons, forecasts) |
| 250905 | Meteorologia Industrial | absent from code | code (weather, storms, monsoons, forecasts) |
| 250906 | Meteorologia Marina | a label only | code (weather, storms, monsoons, forecasts) |
| 250907 | Mesometeorologia | a label only | code (weather, storms, monsoons, forecasts) |
| 250908 | Micrometeorologia | absent from code | code (weather, storms, monsoons, forecasts) |
| 250909 | Prediccion Numerica Meteorologica | own state and behaviour in code | **50.28**; also code (weather, storms, monsoons, forecasts) |
| 250910 | Observacion Meteorologica A Corto Plazo | own state and behaviour in code | **50.28**; also code (weather, storms, monsoons, forecasts) |
| 250911 | Prediccion Operacional Meteorologica | own state and behaviour in code | **50.28**; also code (weather, storms, monsoons, forecasts) |
| 250912 | Meteorologia Polar | a label only | code (weather, storms, monsoons, forecasts) |
| 250913 | Meteorologia Por Radar | absent from code | **50.28** |
| 250914 | Radiometeorologia | absent from code | **50.28** |
| 250915 | Meteorologia Por Cohetes | a label only | **50.28** |
| 250916 | Meteorologia Por Satelites | absent from code | **50.28** |
| 250917 | Meteorologia Sinoptica | own state and behaviour in code | code (weather, storms, monsoons, forecasts) |
| 250918 | Meteorologia Tropical | own state and behaviour in code | code (weather, storms, monsoons, forecasts) |
| 250919 | Analisis Del Tiempo Meteorologico | own state and behaviour in code | code (weather, storms, monsoons, forecasts) |
| 250920 | Modificacion Del Tiempo Meteorologico | a label only | **50.28** |
| 250921 | Meteorologia Aeronautica | a label only | code (weather, storms, monsoons, forecasts) |
| 250922 | Meteorologia Maritima | own state and behaviour in code | code (weather, storms, monsoons, forecasts) |
| 251001 | Oceanografia Biologica | a label only | code (currents, upwelling, winds, fisheries); W48 48.5 methods; W46 cultivation (aquaculture) |
| 251002 | Oceanografia Quimica | a label only | code (currents, upwelling, winds, fisheries); W48 48.5 methods; W46 cultivation (aquaculture) |
| 251003 | Oceanografia Descriptiva | a label only | code (currents, upwelling, winds, fisheries); W48 48.5 methods; W46 cultivation (aquaculture) |
| 251004 | Botanica Oceanografica | absent from code | code (currents, upwelling, winds, fisheries); W48 48.5 methods; W46 cultivation (aquaculture) |
| 251005 | Zoologia Oceanografica | absent from code | code (currents, upwelling, winds, fisheries); W48 48.5 methods; W46 cultivation (aquaculture) |
| 251006 | Procesos Del Fondo Marino | absent from code | **50.23** |
| 251007 | Oceanografia Fisica | some typed state in code | code (currents, upwelling, winds, fisheries); W48 48.5 methods; W46 cultivation (aquaculture) |
| 251008 | Interacciones Aire-Oceano | a label only | code (currents, upwelling, winds, fisheries); W48 48.5 methods; W46 cultivation (aquaculture) |
| 251009 | Hielo Marino | absent from code | **50.23** |
| 251010 | Procesos Litorales Y Sublitorales | some typed state in code | **50.23**; also code (currents, upwelling, winds, fisheries); W48 48.5 methods; W46 cultivation (aquaculture) |
| 251011 | Acustica Submarina | absent from code | code (currents, upwelling, winds, fisheries); W48 48.5 methods; W46 cultivation (aquaculture) |
| 251012 | Geologia Marina | absent from code | **50.23** |
| 251013 | Recursos Marinos Renovables | a label only | code (currents, upwelling, winds, fisheries); W48 48.5 methods; W46 cultivation (aquaculture) |
| 251014 | Acuicultura Marina | absent from code | code (currents, upwelling, winds, fisheries); W48 48.5 methods; W46 cultivation (aquaculture) |
| 251015 | Dinamica Sedimentaria Marina | absent from code | **50.23** |
| 251101 | Bioquimica De Suelos | absent from code | code (soil, nutrients, salinity); spec 13 W34 soil microbes; W48 48.8 soil kinds |
| 251102 | Biologia De Suelos | absent from code | code (soil, nutrients, salinity); spec 13 W34 soil microbes; W48 48.8 soil kinds |
| 251103 | Cartografia De Suelos | absent from code | code (soil, nutrients, salinity); spec 13 W34 soil microbes; W48 48.8 soil kinds |
| 251104 | Quimica De Suelos | own state and behaviour in code | code (soil, nutrients, salinity); spec 13 W34 soil microbes; W48 48.8 soil kinds |
| 251105 | Clasificacion De Suelos | absent from code | code (soil, nutrients, salinity); spec 13 W34 soil microbes; W48 48.8 soil kinds |
| 251106 | Conservacion De Suelos | some typed state in code | code (soil, nutrients, salinity); spec 13 W34 soil microbes; W48 48.8 soil kinds |
| 251107 | Ingenieria De Suelos | absent from code | code (soil, nutrients, salinity); spec 13 W34 soil microbes; W48 48.8 soil kinds |
| 251108 | Mecanica De Suelos En La Agricultura | absent from code | code (soil, nutrients, salinity); spec 13 W34 soil microbes; W48 48.8 soil kinds |
| 251109 | Microbiologia De Suelos | absent from code | code (soil, nutrients, salinity); spec 13 W34 soil microbes; W48 48.8 soil kinds |
| 251110 | Mineralogia De Suelos | absent from code | code (soil, nutrients, salinity); spec 13 W34 soil microbes; W48 48.8 soil kinds |
| 251111 | Genesis Y Morfologia De Suelos | absent from code | code (soil, nutrients, salinity); spec 13 W34 soil microbes; W48 48.8 soil kinds |
| 251112 | Fisica De Suelos | absent from code | code (soil, nutrients, salinity); spec 13 W34 soil microbes; W48 48.8 soil kinds |
| 251201 | Exobiologia | own state and behaviour in code | code (life classes, biochemistries, decompression) |
| 251202 | Medicina Espacial | a label only | **50.25** |
| 251203 | Fisiologia Espacial | some typed state in code | **50.25**; also code (life classes, biochemistries, decompression) |

### Appendix 50.D — Every range of the Thompson motif index

Generated on 2026-11-14 from the 259 ranges of the *Motif-Index of Folk-Literature*. Status was measured as in 50.0, and each range is closed by the named section. W44 step 0 copies this table to `docs/spec/motif-coverage.md`.

| Range | Heading | Measured status | Closed by |
|---|---|---|---|
| A0 – A99 | Creator | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A100 – A149 | The gods in general part 1 | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A150 – A199 | The gods in general part 2 | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A200 – A299 | Gods of the upper world | a label only | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A300 – A399 | Gods of the underworld | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A400 – A499 | Gods of the earth | some typed state in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A500 – A599 | Demigods and culture heroes | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A600 – A649 | Creation of the universe | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A650 – A699 | Nature of the universe | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A700 – A709 | The heavens | some typed state in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A710 – A739 | The sun | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A740 – A759 | The moon | some typed state in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A760 – A799 | The stars and the heavenly lights | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A800 – A899 | The earth | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A900 – A949 | Topographical features of the earth | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A950 – A999 | Land features | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A1000 – A1099 | World calamities and renewals | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A1100 – A1199 | Establishment of natural order | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A1200 – A1299 | Creation of man | a label only | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A1300 – A1399 | Ordering of human life | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A1400 – A1499 | Acquisition of culture | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A1500 – A1599 | Origin of customs | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A1600 – A1699 | Distribution and differentiation of peoples | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A1700 – A1799 | Creation of animal life  –  general | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A1800 – A1899 | Creation of mammals | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A1900 – A1999 | Creation of birds | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A2000 – A2099 | Creation of insects | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A2100 – A2199 | Creation of fish and other animals | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A2200 – A2299 | Various causes of animal characteristics | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A2300 – A2399 | Causes of animal characteristics: body | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A2400 – A2499 | Causes of animal characteristics: appearance and habits | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A2500 – A2599 | Animal characteristics – miscellaneous | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A2600 – A2699 | Origin of trees and plants | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A2700 – A2799 | Origin of plant characteristics | own state and behaviour in code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| A2800 – A2899 | Miscellaneous explanations | absent from code | code (gods, creator, genesis, cosmos, sky, world shaping, peoples' origins, etiology in legends); W47 47.5–47.6; W48 48.8 |
| B0 – B49 | Mythical animals I | own state and behaviour in code | code (beasts, monsters, divine creatures, companions, familiars, uplifted kinds); W46 46.15; 50.8 unions with other kinds |
| B50 – B99 | Mythical animals II | own state and behaviour in code | code (beasts, monsters, divine creatures, companions, familiars, uplifted kinds); W46 46.15; 50.8 unions with other kinds |
| B100 – B199 | Magic animals | own state and behaviour in code | code (beasts, monsters, divine creatures, companions, familiars, uplifted kinds); W46 46.15; 50.8 unions with other kinds |
| B200 – B249 | Animals with human traits I | absent from code | code (beasts, monsters, divine creatures, companions, familiars, uplifted kinds); W46 46.15; 50.8 unions with other kinds |
| B250 – B299 | Animals with human traits II | absent from code | code (beasts, monsters, divine creatures, companions, familiars, uplifted kinds); W46 46.15; 50.8 unions with other kinds |
| B300 – B349 | Helpful animals  –  general | own state and behaviour in code | code (beasts, monsters, divine creatures, companions, familiars, uplifted kinds); W46 46.15; 50.8 unions with other kinds |
| B400 – B499 | Kinds of helpful animals | own state and behaviour in code | code (beasts, monsters, divine creatures, companions, familiars, uplifted kinds); W46 46.15; 50.8 unions with other kinds |
| B500 – B599 | Services of helpful animals | some typed state in code | code (beasts, monsters, divine creatures, companions, familiars, uplifted kinds); W46 46.15; 50.8 unions with other kinds |
| B600 – B699 | Marriage of person to animal | a label only | code (beasts, monsters, divine creatures, companions, familiars, uplifted kinds); W46 46.15; 50.8 unions with other kinds |
| B700 – B799 | Fanciful traits of animals | absent from code | code (beasts, monsters, divine creatures, companions, familiars, uplifted kinds); W46 46.15; 50.8 unions with other kinds |
| B800 – B899 | Miscellaneous animal motifs | own state and behaviour in code | code (beasts, monsters, divine creatures, companions, familiars, uplifted kinds); W46 46.15; 50.8 unions with other kinds |
| C0 – C99 | Tabu connected with supernatural beings | own state and behaviour in code | code (taboos, geasa, purity ranks F41); 50.8; W47 customs |
| C100 – C199 | Sex Tabu | own state and behaviour in code | code (taboos, geasa, purity ranks F41); 50.8; W47 customs |
| C200 – C249 | Eating Tabus | own state and behaviour in code | code (taboos, geasa, purity ranks F41); 50.8; W47 customs |
| C250 – C299 | Drinking Tabus | own state and behaviour in code | code (taboos, geasa, purity ranks F41); 50.8; W47 customs |
| C300 – C399 | Looking tabu | own state and behaviour in code | code (taboos, geasa, purity ranks F41); 50.8; W47 customs |
| C400 – C499 | Speaking tabu | own state and behaviour in code | code (taboos, geasa, purity ranks F41); 50.8; W47 customs |
| C500 – C549 | Tabu: touching | own state and behaviour in code | code (taboos, geasa, purity ranks F41); 50.8; W47 customs |
| C550 – C599 | Class tabu | own state and behaviour in code | code (taboos, geasa, purity ranks F41); 50.8; W47 customs |
| C600 – C649 | Unique Prohibitions and Compulsions. The One Forbidden Thing | own state and behaviour in code | code (taboos, geasa, purity ranks F41); 50.8; W47 customs |
| C650 – C699 | Unique Prohibitions and Compulsions. The One Compulsory Thing | own state and behaviour in code | code (taboos, geasa, purity ranks F41); 50.8; W47 customs |
| C700 – C829 | Miscellaneous Tabus | own state and behaviour in code | code (taboos, geasa, purity ranks F41); 50.8; W47 customs |
| C830 – C899 | Unclassified Tabus | own state and behaviour in code | code (taboos, geasa, purity ranks F41); 50.8; W47 customs |
| C900 – C999 | Punishment for breaking tabu | own state and behaviour in code | code (taboos, geasa, purity ranks F41); 50.8; W47 customs |
| D0 – D99 | Transformation (general) | some typed state in code | code (rites, enchantments, item powers, curses, transformation, constructs); W45 45.3 power grammar applied to things; F55 relics |
| D100 – D199 | Transformation: man to animal | some typed state in code | code (rites, enchantments, item powers, curses, transformation, constructs); W45 45.3 power grammar applied to things; F55 relics |
| D200 – D299 | Transformation: man to object | some typed state in code | code (rites, enchantments, item powers, curses, transformation, constructs); W45 45.3 power grammar applied to things; F55 relics |
| D300 – D399 | Transformation: animal to person | some typed state in code | code (rites, enchantments, item powers, curses, transformation, constructs); W45 45.3 power grammar applied to things; F55 relics |
| D400 – D499 | Other forms of transformation | some typed state in code | code (rites, enchantments, item powers, curses, transformation, constructs); W45 45.3 power grammar applied to things; F55 relics |
| D500 – D599 | Means of transformation | some typed state in code | code (rites, enchantments, item powers, curses, transformation, constructs); W45 45.3 power grammar applied to things; F55 relics |
| D600 – D699 | Miscellaneous transformation incidents | some typed state in code | code (rites, enchantments, item powers, curses, transformation, constructs); W45 45.3 power grammar applied to things; F55 relics |
| D700 – D799 | Disenchantment | some typed state in code | code (rites, enchantments, item powers, curses, transformation, constructs); W45 45.3 power grammar applied to things; F55 relics |
| D800 – D899 | Ownership of magic objects | some typed state in code | code (rites, enchantments, item powers, curses, transformation, constructs); W45 45.3 power grammar applied to things; F55 relics |
| D900 – D999 | Kinds of magic objects I | some typed state in code | code (rites, enchantments, item powers, curses, transformation, constructs); W45 45.3 power grammar applied to things; F55 relics |
| D1000 – D1099 | Kinds of magic objects II | some typed state in code | code (rites, enchantments, item powers, curses, transformation, constructs); W45 45.3 power grammar applied to things; F55 relics |
| D1100 – D1199 | Kinds of magic objects III | some typed state in code | code (rites, enchantments, item powers, curses, transformation, constructs); W45 45.3 power grammar applied to things; F55 relics |
| D1200 – D1299 | Kinds of magic objects IV | some typed state in code | code (rites, enchantments, item powers, curses, transformation, constructs); W45 45.3 power grammar applied to things; F55 relics |
| D1300 – D1339 | Function of magic objects I | some typed state in code | code (rites, enchantments, item powers, curses, transformation, constructs); W45 45.3 power grammar applied to things; F55 relics |
| D1340 – D1369 | Function of magic objects II | absent from code | code (rites, enchantments, item powers, curses, transformation, constructs); W45 45.3 power grammar applied to things; F55 relics |
| D1370 – D1399 | Function of magic objects III | absent from code | code (rites, enchantments, item powers, curses, transformation, constructs); W45 45.3 power grammar applied to things; F55 relics |
| D1400 – D1439 | Magic object gives power over other persons | some typed state in code | code (rites, enchantments, item powers, curses, transformation, constructs); W45 45.3 power grammar applied to things; F55 relics |
| D1440 – D1499 | Magic object gives power over animals | some typed state in code | code (rites, enchantments, item powers, curses, transformation, constructs); W45 45.3 power grammar applied to things; F55 relics |
| D1500 – D1549 | Magic object controls disease | own state and behaviour in code | code (rites, enchantments, item powers, curses, transformation, constructs); W45 45.3 power grammar applied to things; F55 relics |
| D1550 – D1599 | Magic object miraculously opens and closes | own state and behaviour in code | code (rites, enchantments, item powers, curses, transformation, constructs); W45 45.3 power grammar applied to things; F55 relics |
| D1600 – D1649 | Automatic magic objects | own state and behaviour in code | code (rites, enchantments, item powers, curses, transformation, constructs); W45 45.3 power grammar applied to things; F55 relics |
| D1650 – D1699 | Other characteristics of magic objects | some typed state in code | code (rites, enchantments, item powers, curses, transformation, constructs); W45 45.3 power grammar applied to things; F55 relics |
| D1700 – D1799 | Possession and means of employment of magic powers | own state and behaviour in code | code (rites, enchantments, item powers, curses, transformation, constructs); W45 45.3 power grammar applied to things; F55 relics |
| D1800 – D1949 | Lasting magic qualities | some typed state in code | code (rites, enchantments, item powers, curses, transformation, constructs); W45 45.3 power grammar applied to things; F55 relics |
| D1950 – D2049 | Temporary magic characteristics | some typed state in code | code (rites, enchantments, item powers, curses, transformation, constructs); W45 45.3 power grammar applied to things; F55 relics |
| D2050 – D2099 | Destructive magic powers | some typed state in code | code (rites, enchantments, item powers, curses, transformation, constructs); W45 45.3 power grammar applied to things; F55 relics |
| D2100 – D2149 | Other manifestations of magic power | own state and behaviour in code | code (rites, enchantments, item powers, curses, transformation, constructs); W45 45.3 power grammar applied to things; F55 relics |
| D2150 – D2199 | Miscellaneous magical manifestations | own state and behaviour in code | code (rites, enchantments, item powers, curses, transformation, constructs); W45 45.3 power grammar applied to things; F55 relics |
| E0 – E199 | Resuscitation | some typed state in code | code (spirits, ghosts, necromancy, rebirth, souls, afterlife) |
| E200 – E299 | Malevolent return from the dead | some typed state in code | code (spirits, ghosts, necromancy, rebirth, souls, afterlife) |
| E300 – E399 | Friendly return from the dead | own state and behaviour in code | code (spirits, ghosts, necromancy, rebirth, souls, afterlife) |
| E400 – E499 | Ghosts and revenants – miscellaneous I | a label only | code (spirits, ghosts, necromancy, rebirth, souls, afterlife) |
| E500 – E599 | Ghosts and revenants – miscellaneous II | some typed state in code | code (spirits, ghosts, necromancy, rebirth, souls, afterlife) |
| E600 – E699 | Reincarnation | own state and behaviour in code | code (spirits, ghosts, necromancy, rebirth, souls, afterlife) |
| E700 – E799 | The soul | own state and behaviour in code | code (spirits, ghosts, necromancy, rebirth, souls, afterlife) |
| F0 – F149 | Other world journeys I | some typed state in code | code (journeys beyond, realms, spirits, wonders, phenomena); W45 F53 hidden folk, 45.4 powers; W48 48.8 |
| F150 – F199 | Other world journeys II | own state and behaviour in code | code (journeys beyond, realms, spirits, wonders, phenomena); W45 F53 hidden folk, 45.4 powers; W48 48.8 |
| F200 – F299 | Fairies and elves | own state and behaviour in code | code (journeys beyond, realms, spirits, wonders, phenomena); W45 F53 hidden folk, 45.4 powers; W48 48.8 |
| F300 – F399 | Fairies and mortals | own state and behaviour in code | code (journeys beyond, realms, spirits, wonders, phenomena); W45 F53 hidden folk, 45.4 powers; W48 48.8 |
| F400 – F449 | Spirits and demons I | own state and behaviour in code | code (journeys beyond, realms, spirits, wonders, phenomena); W45 F53 hidden folk, 45.4 powers; W48 48.8 |
| F450 – F479 | Spirits and demons II | own state and behaviour in code | code (journeys beyond, realms, spirits, wonders, phenomena); W45 F53 hidden folk, 45.4 powers; W48 48.8 |
| F480 – F499 | Spirits and demons III | own state and behaviour in code | code (journeys beyond, realms, spirits, wonders, phenomena); W45 F53 hidden folk, 45.4 powers; W48 48.8 |
| F500 – F539 | Remarkable persons I | some typed state in code | code (journeys beyond, realms, spirits, wonders, phenomena); W45 F53 hidden folk, 45.4 powers; W48 48.8 |
| F540 – F599 | Remarkable persons II | own state and behaviour in code | code (journeys beyond, realms, spirits, wonders, phenomena); W45 F53 hidden folk, 45.4 powers; W48 48.8 |
| F600 – F699 | Persons with extraordinary powers | own state and behaviour in code | code (journeys beyond, realms, spirits, wonders, phenomena); W45 F53 hidden folk, 45.4 powers; W48 48.8 |
| F700 – F799 | Extraordinary places and things | own state and behaviour in code | code (journeys beyond, realms, spirits, wonders, phenomena); W45 F53 hidden folk, 45.4 powers; W48 48.8 |
| F800 – F899 | Extraordinary rocks and stones | own state and behaviour in code | code (journeys beyond, realms, spirits, wonders, phenomena); W45 F53 hidden folk, 45.4 powers; W48 48.8 |
| F900 – F999 | Extraordinary occurrences I | own state and behaviour in code | code (journeys beyond, realms, spirits, wonders, phenomena); W45 F53 hidden folk, 45.4 powers; W48 48.8 |
| F1000 – F1099 | Extraordinary occurrences II | own state and behaviour in code | code (journeys beyond, realms, spirits, wonders, phenomena); W45 F53 hidden folk, 45.4 powers; W48 48.8 |
| G0 – G99 | Cannibals and cannibalism | a label only | code (monsters, giants by size traits, witchcraft, abductors, monster contracts) |
| G100 – G199 | Giant ogres | a label only | code (monsters, giants by size traits, witchcraft, abductors, monster contracts) |
| G200 – G299 | Witches | own state and behaviour in code | code (monsters, giants by size traits, witchcraft, abductors, monster contracts) |
| G300 – G302 | Other ogres | own state and behaviour in code | code (monsters, giants by size traits, witchcraft, abductors, monster contracts) |
| G304 – G399 | Other ogres | own state and behaviour in code | code (monsters, giants by size traits, witchcraft, abductors, monster contracts) |
| G400 – G499 | Falling into ogre’s power | own state and behaviour in code | code (monsters, giants by size traits, witchcraft, abductors, monster contracts) |
| G500 – G599 | Ogre defeated | own state and behaviour in code | code (monsters, giants by size traits, witchcraft, abductors, monster contracts) |
| G600 – G699 | Other ogre motifs | some typed state in code | code (monsters, giants by size traits, witchcraft, abductors, monster contracts) |
| H0 – H199 | Identity tests: Recognition | some typed state in code | code (contests, ordeals, wedding challenges, heroquests, storylets, examinations) |
| H200 – H299 | Tests of truth | own state and behaviour in code | code (contests, ordeals, wedding challenges, heroquests, storylets, examinations) |
| H300 – H499 | Marriage tests | a label only | code (contests, ordeals, wedding challenges, heroquests, storylets, examinations) |
| H500 – H699 | Tests of cleverness I | own state and behaviour in code | code (contests, ordeals, wedding challenges, heroquests, storylets, examinations) |
| H700 – H899 | Tests of cleverness II | own state and behaviour in code | code (contests, ordeals, wedding challenges, heroquests, storylets, examinations) |
| H900 – H1199 | Tests of prowess: tasks | own state and behaviour in code | code (contests, ordeals, wedding challenges, heroquests, storylets, examinations) |
| H1000 – H1199 | Nature of tasks | own state and behaviour in code | code (contests, ordeals, wedding challenges, heroquests, storylets, examinations) |
| H1200 – H1399 | Tests of prowess: quests | own state and behaviour in code | code (contests, ordeals, wedding challenges, heroquests, storylets, examinations) |
| H1400 – H1599 | Other Tests | own state and behaviour in code | code (contests, ordeals, wedding challenges, heroquests, storylets, examinations) |
| J0 – J199 | Acquisition and possession of wisdom (knowledge) | own state and behaviour in code | code (traits, facets, wits, learning biases, theories, mishaps 47.10); 50.13 humour |
| J200 – J499 | Choices | own state and behaviour in code | code (traits, facets, wits, learning biases, theories, mishaps 47.10); 50.13 humour |
| J500 – J599 | Prudence and discretion | a label only | code (traits, facets, wits, learning biases, theories, mishaps 47.10); 50.13 humour |
| J600 – J799 | Forethought | own state and behaviour in code | code (traits, facets, wits, learning biases, theories, mishaps 47.10); 50.13 humour |
| J800 – J899 | Adaptability | absent from code | code (traits, facets, wits, learning biases, theories, mishaps 47.10); 50.13 humour |
| J900 – J999 | Humility | absent from code | code (traits, facets, wits, learning biases, theories, mishaps 47.10); 50.13 humour |
| J1000 – J1099 | Other aspects of wisdom | some typed state in code | code (traits, facets, wits, learning biases, theories, mishaps 47.10); 50.13 humour |
| J1100 – J1249 | Clever persons and acts | own state and behaviour in code | code (traits, facets, wits, learning biases, theories, mishaps 47.10); 50.13 humour |
| J1250 – J1399 | Clever verbal retorts (repartee) I | own state and behaviour in code | code (traits, facets, wits, learning biases, theories, mishaps 47.10); 50.13 humour |
| J1400 – J1499 | Clever verbal retorts (repartee) II | own state and behaviour in code | code (traits, facets, wits, learning biases, theories, mishaps 47.10); 50.13 humour |
| J1500 – J1649 | Clever practical retorts | absent from code | code (traits, facets, wits, learning biases, theories, mishaps 47.10); 50.13 humour |
| J1650 – J1699 | Miscellaneous clever acts | absent from code | code (traits, facets, wits, learning biases, theories, mishaps 47.10); 50.13 humour |
| J1700 – J1749 | Fools (general) | absent from code | code (traits, facets, wits, learning biases, theories, mishaps 47.10); 50.13 humour |
| J1750 – J1849 | Absurd misunderstandings | absent from code | code (traits, facets, wits, learning biases, theories, mishaps 47.10); 50.13 humour |
| J1850–J1999 | Absurd disregard of facts | absent from code | code (traits, facets, wits, learning biases, theories, mishaps 47.10); 50.13 humour |
| J2000 – J2049 | Absurd absent-mindedness | absent from code | code (traits, facets, wits, learning biases, theories, mishaps 47.10); 50.13 humour |
| J2050 – J2199 | Absurd short-sightedness | absent from code | code (traits, facets, wits, learning biases, theories, mishaps 47.10); 50.13 humour |
| J2200 – J2259 | Absurd lack of logic | absent from code | code (traits, facets, wits, learning biases, theories, mishaps 47.10); 50.13 humour |
| J2260 – J2299 | Absurd scientific theories | own state and behaviour in code | code (traits, facets, wits, learning biases, theories, mishaps 47.10); 50.13 humour |
| J2300 – J2349 | Gullible fools | absent from code | code (traits, facets, wits, learning biases, theories, mishaps 47.10); 50.13 humour |
| J2350 – J2399 | Talkative fools | some typed state in code | code (traits, facets, wits, learning biases, theories, mishaps 47.10); 50.13 humour |
| J2400 – J2449 | Foolish imitation | absent from code | code (traits, facets, wits, learning biases, theories, mishaps 47.10); 50.13 humour |
| J2450 – J2499 | Literal fools | some typed state in code | code (traits, facets, wits, learning biases, theories, mishaps 47.10); 50.13 humour |
| J2500 – J2599 | Foolish extreme | absent from code | code (traits, facets, wits, learning biases, theories, mishaps 47.10); 50.13 humour |
| J2600 – J2649 | Cowardly fool | a label only | code (traits, facets, wits, learning biases, theories, mishaps 47.10); 50.13 humour |
| J2650 – J2699 | Bungling fool | own state and behaviour in code | code (traits, facets, wits, learning biases, theories, mishaps 47.10); 50.13 humour |
| J2700 – J2799 | The easy problem made hard | absent from code | code (traits, facets, wits, learning biases, theories, mishaps 47.10); 50.13 humour |
| K0 – K99 | Contests won by deception | own state and behaviour in code | code (schemes, intrigue, theft, assassination, forgery, false accusation, disguise, pacts) |
| K100 – K299 | Deceptive bargains | own state and behaviour in code | code (schemes, intrigue, theft, assassination, forgery, false accusation, disguise, pacts) |
| K300 – K399 | Thefts and cheats I | a label only | code (schemes, intrigue, theft, assassination, forgery, false accusation, disguise, pacts) |
| K400 – K499 | Thefts and cheats II | a label only | code (schemes, intrigue, theft, assassination, forgery, false accusation, disguise, pacts) |
| K500 – K599 | Escape by deception I | some typed state in code | code (schemes, intrigue, theft, assassination, forgery, false accusation, disguise, pacts) |
| K600 – K699 | Escape by deception II | some typed state in code | code (schemes, intrigue, theft, assassination, forgery, false accusation, disguise, pacts) |
| K700 – K799 | Capture by deception | some typed state in code | code (schemes, intrigue, theft, assassination, forgery, false accusation, disguise, pacts) |
| K800 – K999 | Killing or maiming by deception | some typed state in code | code (schemes, intrigue, theft, assassination, forgery, false accusation, disguise, pacts) |
| K1000 – K1199 | Deception into self-injury | a label only | code (schemes, intrigue, theft, assassination, forgery, false accusation, disguise, pacts) |
| K1200 – K1299 | Deception into humiliating position | a label only | code (schemes, intrigue, theft, assassination, forgery, false accusation, disguise, pacts) |
| K1300 – K1399 | Seduction or deceptive marriage | a label only | code (schemes, intrigue, theft, assassination, forgery, false accusation, disguise, pacts) |
| K1400 – K1499 | Dupe’s property destroyed | own state and behaviour in code | code (schemes, intrigue, theft, assassination, forgery, false accusation, disguise, pacts) |
| K1500 – K1599 | Deceptions connected with adultery | own state and behaviour in code | code (schemes, intrigue, theft, assassination, forgery, false accusation, disguise, pacts) |
| K1600 – K1699 | Deceiver falls into own trap | own state and behaviour in code | code (schemes, intrigue, theft, assassination, forgery, false accusation, disguise, pacts) |
| K1700 – K1799 | Deception through bluffing | some typed state in code | code (schemes, intrigue, theft, assassination, forgery, false accusation, disguise, pacts) |
| K1800 – K1899 | Deception by disguise or illusion | own state and behaviour in code | code (schemes, intrigue, theft, assassination, forgery, false accusation, disguise, pacts) |
| K1900 – K1999 | Impostures | some typed state in code | code (schemes, intrigue, theft, assassination, forgery, false accusation, disguise, pacts) |
| K2000 – K2099 | Hypocrites | absent from code | **50.29** |
| K2100 – K2199 | False accusations | own state and behaviour in code | code (schemes, intrigue, theft, assassination, forgery, false accusation, disguise, pacts) |
| K2200 – K2299 | Villains and traitors | a label only | code (schemes, intrigue, theft, assassination, forgery, false accusation, disguise, pacts) |
| K2300 – K2399 | Other deceptions | some typed state in code | code (schemes, intrigue, theft, assassination, forgery, false accusation, disguise, pacts) |
| L0 – L99 | Victorious youngest child | own state and behaviour in code | code (storyteller arcs: rags to riches, rise and fall, redemption) |
| L100 – L199 | Unpromising hero (heroine) | own state and behaviour in code | code (storyteller arcs: rags to riches, rise and fall, redemption) |
| L200 – L299 | Modesty brings reward | a label only | code (storyteller arcs: rags to riches, rise and fall, redemption) |
| L300 – L399 | Triumph of the weak | a label only | code (storyteller arcs: rags to riches, rise and fall, redemption) |
| L400 – L499 | Pride brought low | some typed state in code | code (storyteller arcs: rags to riches, rise and fall, redemption) |
| M0 – M99 | Judgments and decrees | own state and behaviour in code | code (rulings, decrees, oaths, pacts, prophecy, curses) |
| M100 – M199 | Vows and oaths | own state and behaviour in code | code (rulings, decrees, oaths, pacts, prophecy, curses) |
| M200 – M299 | Bargains and promises | own state and behaviour in code | code (rulings, decrees, oaths, pacts, prophecy, curses) |
| M300 – M399 | Prophecies | own state and behaviour in code | code (rulings, decrees, oaths, pacts, prophecy, curses) |
| M400 – M499 | Curses | some typed state in code | code (rulings, decrees, oaths, pacts, prophecy, curses) |
| N0 – N99 | Wagers and gambling | own state and behaviour in code | code (fortune law K.37, mishaps 47.10, wagers, treasure, encounters 47.8.12, patrons) |
| N100 – N299 | The ways of luck and fate | own state and behaviour in code | code (fortune law K.37, mishaps 47.10, wagers, treasure, encounters 47.8.12, patrons) |
| N300 – N399 | Unlucky accidents | own state and behaviour in code | code (fortune law K.37, mishaps 47.10, wagers, treasure, encounters 47.8.12, patrons) |
| N400 – N499 | Lucky accidents | own state and behaviour in code | code (fortune law K.37, mishaps 47.10, wagers, treasure, encounters 47.8.12, patrons) |
| N500 – N599 | Treasure trove | own state and behaviour in code | code (fortune law K.37, mishaps 47.10, wagers, treasure, encounters 47.8.12, patrons) |
| N600 – N699 | Other lucky accidents | own state and behaviour in code | code (fortune law K.37, mishaps 47.10, wagers, treasure, encounters 47.8.12, patrons) |
| N700 – N799 | Accidental encounters | absent from code | code (fortune law K.37, mishaps 47.10, wagers, treasure, encounters 47.8.12, patrons) |
| N800 – N899 | Helpers | own state and behaviour in code | code (fortune law K.37, mishaps 47.10, wagers, treasure, encounters 47.8.12, patrons) |
| P0 – P99 | Royalty and nobility | own state and behaviour in code | code (titles, classes, estates, family, professions, government, customs) |
| P100 – P199 | Other social orders | own state and behaviour in code | code (titles, classes, estates, family, professions, government, customs) |
| P200 – P299 | The family | own state and behaviour in code | code (titles, classes, estates, family, professions, government, customs) |
| P300 – P399 | Other social relationships | own state and behaviour in code | code (titles, classes, estates, family, professions, government, customs) |
| P400 – P499 | Trades and professions | own state and behaviour in code | code (titles, classes, estates, family, professions, government, customs) |
| P500 – P599 | Government | own state and behaviour in code | code (titles, classes, estates, family, professions, government, customs) |
| P600 – P699 | Customs | own state and behaviour in code | code (titles, classes, estates, family, professions, government, customs) |
| P700 – P799 | Society – miscellaneous motifs | some typed state in code | code (titles, classes, estates, family, professions, government, customs) |
| Q0 – Q99 | Deeds rewarded | own state and behaviour in code | code (justice, divine rulings, punishments, rewards) |
| Q100 – Q199 | Nature of rewards | own state and behaviour in code | code (justice, divine rulings, punishments, rewards) |
| Q200 – Q299 | Deeds punished I | own state and behaviour in code | code (justice, divine rulings, punishments, rewards) |
| Q300 – Q399 | Deeds punished II | some typed state in code | code (justice, divine rulings, punishments, rewards) |
| Q400 – Q499 | Kinds of punishment I | own state and behaviour in code | code (justice, divine rulings, punishments, rewards) |
| Q500 – Q549 | Kinds of punishment II | some typed state in code | code (justice, divine rulings, punishments, rewards) |
| Q550 – Q599 | Kinds of punishment III | some typed state in code | code (justice, divine rulings, punishments, rewards) |
| R0 – R99 | Captivity | own state and behaviour in code | code (captivity, rescue, escape, refuge) |
| R100 – R199 | Rescues | a label only | code (captivity, rescue, escape, refuge) |
| R200 – R299 | Escapes and pursuits | some typed state in code | code (captivity, rescue, escape, refuge) |
| R300 – R399 | Refuges and recapture | some typed state in code | code (captivity, rescue, escape, refuge) |
| S0 – S99 | Cruel relatives | some typed state in code | code (crimes, punishments, sacrifice, infanticide norms 50.8, persecution) |
| S100 – S199 | Revolting murders or mutilations | a label only | code (crimes, punishments, sacrifice, infanticide norms 50.8, persecution) |
| S200 – S299 | Cruel sacrifices | some typed state in code | code (crimes, punishments, sacrifice, infanticide norms 50.8, persecution) |
| S300 – S399 | Abandoned or murdered children | own state and behaviour in code | code (crimes, punishments, sacrifice, infanticide norms 50.8, persecution) |
| S400 – S499 | Cruel persecutions | some typed state in code | code (crimes, punishments, sacrifice, infanticide norms 50.8, persecution) |
| T0 – T99 | Love | own state and behaviour in code | code (attraction, unions, households); 50.8 |
| T100 – T199 | Marriage | own state and behaviour in code | code (attraction, unions, households); 50.8 |
| T200 – T299 | Married life | some typed state in code | code (attraction, unions, households); 50.8 |
| T300 – T399 | Chastity and celibacy | a label only | code (attraction, unions, households); 50.8 |
| T400 – T499 | Illicit sexual relations | own state and behaviour in code | code (attraction, unions, households); 50.8 |
| T500 – T599 | Conception and birth | own state and behaviour in code | code (attraction, unions, households); 50.8 |
| T600 – T699 | Care of children | some typed state in code | code (attraction, unions, households); 50.8 |
| U0 – U99 | Life's inequalities | own state and behaviour in code | code (classes, poverty, living standards) |
| U100 – U299 | The nature of life – miscellaneous motifs | own state and behaviour in code | code (classes, poverty, living standards) |
| V0 – V99 | Religious services | own state and behaviour in code | code (faith, temples, relics, clergy, doctrine, orders, miracles) |
| V100 – V199 | Religious edifices and objects | own state and behaviour in code | code (faith, temples, relics, clergy, doctrine, orders, miracles) |
| V200 – V299 | Sacred persons | own state and behaviour in code | code (faith, temples, relics, clergy, doctrine, orders, miracles) |
| V300 – V399 | Religious beliefs | own state and behaviour in code | code (faith, temples, relics, clergy, doctrine, orders, miracles) |
| V400 – V449 | Religious virtues | a label only | code (faith, temples, relics, clergy, doctrine, orders, miracles) |
| V450 – V499 | Religious orders | own state and behaviour in code | code (faith, temples, relics, clergy, doctrine, orders, miracles) |
| V500 – V599 | Religious motifs – miscellaneous | own state and behaviour in code | code (faith, temples, relics, clergy, doctrine, orders, miracles) |
| W0 – W99 | Favorable traits of character | own state and behaviour in code | code (traits, values, virtues and vices) |
| W100 – W199 | Unfavorable traits of character | own state and behaviour in code | code (traits, values, virtues and vices) |
| W200 – W299 | Traits of character – miscellaneous | own state and behaviour in code | code (traits, values, virtues and vices) |
| X0 – X99 | Humor of discomfiture | a label only | **50.13**; also 50.13 humour; code (legend distortion, tall tales as legends) |
| X100 – X199 | Humor of disability | a label only | **50.13**; also 50.13 humour; code (legend distortion, tall tales as legends) |
| X200 – X299 | Humor of social classes: Humor dealing with tradesmen | a label only | **50.13**; also 50.13 humour; code (legend distortion, tall tales as legends) |
| X300 – X499 | Humor of social classes: . Humor dealing with professions | a label only | **50.13**; also 50.13 humour; code (legend distortion, tall tales as legends) |
| X500 – X599 | Humor concerning other social classes | a label only | **50.13**; also 50.13 humour; code (legend distortion, tall tales as legends) |
| X600 – X699 | Humor concerning races or nations | a label only | **50.13**; also 50.13 humour; code (legend distortion, tall tales as legends) |
| X700 – X799 | Humor concerning sex | a label only | **50.13**; also 50.13 humour; code (legend distortion, tall tales as legends) |
| X800 – X899 | Humor based on drunkenness | own state and behaviour in code | 50.13 humour; code (legend distortion, tall tales as legends) |
| X900 – X909 | Humor of lies and exaggeration | own state and behaviour in code | 50.13 humour; code (legend distortion, tall tales as legends) |
| X910 – X959 | Lie: the remarkable man – his birth, growth, death, physical powers, strength | own state and behaviour in code | 50.13 humour; code (legend distortion, tall tales as legends) |
| X960 – X1019 | Lie: remarkable person's skills | own state and behaviour in code | 50.13 humour; code (legend distortion, tall tales as legends) |
| X1020 – X1099 | Remarkable man's extraordinary possessions | absent from code | **50.13**; also 50.13 humour; code (legend distortion, tall tales as legends) |
| X1100 – X1199 | Lie: great hunters and fishermen | own state and behaviour in code | 50.13 humour; code (legend distortion, tall tales as legends) |
| X1200 – X1399 | Lies about animals | absent from code | **50.13**; also 50.13 humour; code (legend distortion, tall tales as legends) |
| X1400 – X1499 | Lies about plants, fruits, vegetables, and trees | absent from code | **50.13**; also 50.13 humour; code (legend distortion, tall tales as legends) |
| X1500 – X1599 | Lies about geography and topography | absent from code | **50.13**; also 50.13 humour; code (legend distortion, tall tales as legends) |
| X1600 – X1699 | Lies about weather and climate | absent from code | **50.13**; also 50.13 humour; code (legend distortion, tall tales as legends) |
| X1700 – X1799 | Lies: logical absurdities | absent from code | **50.13**; also 50.13 humour; code (legend distortion, tall tales as legends) |
| X1800 – X1899 | Miscellaneous lies and exaggerations | absent from code | **50.13**; also 50.13 humour; code (legend distortion, tall tales as legends) |
| Z0 – Z19 | Formulas | absent from code | W48 48.7 art modes and verbal forms; 48.3 emblems; code (heroes, heraldry) |
| Z20 – Z59 | Cumulative tales | a label only | W48 48.7 art modes and verbal forms; 48.3 emblems; code (heroes, heraldry) |
| Z60 –Z99 | Other formulistic motifs | absent from code | W48 48.7 art modes and verbal forms; 48.3 emblems; code (heroes, heraldry) |
| Z100 – Z199 | Symbolism | own state and behaviour in code | W48 48.7 art modes and verbal forms; 48.3 emblems; code (heroes, heraldry) |
| Z200 – Z299 | Heroes | own state and behaviour in code | W48 48.7 art modes and verbal forms; 48.3 emblems; code (heroes, heraldry) |
| Z300 – Z399 | Unique exceptions | some typed state in code | W48 48.7 art modes and verbal forms; 48.3 emblems; code (heroes, heraldry) |
