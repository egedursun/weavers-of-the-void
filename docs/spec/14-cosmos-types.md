# 14. Cosmos types and their wiring

This addendum widens the cosmos taxonomy (stars, worlds and moons, sky events, horror events, travel methods, journey events, route closures) and wires every type into the mechanics that exist today. It also fixes the cosmos bugs and dead values found by the inventory of 2026-11-03.

**Boundary.** Spec 13 Part 10 (W12, W12+: mass-based stellar evolution, derived orbital physics, star systems, cosmic features, impacts) and the F45 foundation rows for systems that are not built yet stay with the spec 13 waves. The new world types get F45 rows in 13-depth-expansion.md so those waves pick them up. Everything that exists today reads the new types now.

## 14.1 Stars

Each star type has a mechanics row (`engine/cosmos/star_types.py`, rules namespace `star_types`) and a catalogue row (`catalog/stars.py`: label, description, supernova remnant).

| Effect | Reader |
|---|---|
| brightness band (min–max) | `create_star`: the existing birth/hang brightness roll places the new star inside its type's band; supernova, extinguish and rekindle fit the new brightness into the band of the resulting type |
| heat | `temperature_of` (environment): every region of the star's worlds (moons through their root star) gets the type's heat plus `brightness_heat_pct` × (brightness − band middle). Temperature feeds bands, crops, harvest, weather and passability |
| capacity | `world_physics`: life capacity of the star's worlds (population growth, carrying capacity) |
| collapse weight | spontaneous supernova and black sun pick their star by this weight (0 = never); replaces the old binary collapsible set |
| remnant | what a supernova leaves: neutron star, black hole, white dwarf or star remnant |
| flare weight | the new **flare** sky event picks its star by this weight |
| eclipse weight | multiple suns add spontaneous eclipse weight, and the eclipse prefers their worlds |
| leak / leak repair | per-epoch leak of each of its worlds (`leak_delta`: 'star' and 'star's hold' lines) |
| sanity erosion | extra per-epoch sanity loss of everyone living under it (horror phase) |
| sail danger | extra danger of a light-sail route bound to it |
| instability | epochs cut from each climate age of its worlds |

| Type | Label | Brightness | Heat | Capacity % | Collapse | Flare | Remnant | Other |
|---|---|---|---|---|---|---|---|---|
| `yellow_dwarf` | Yellow dwarf | 55–85 | +0 | 100 | 0 | 1 | — | — |
| `blue_star` | Blue star | 85–100 | +14 | 82 | 3 | 2 | neutron_star | — |
| `blue_white_star` | Blue-white star | 75–95 | +9 | 92 | 1 | 1 | neutron_star | — |
| `white_star` | White star | 65–90 | +5 | 97 | 0 | 1 | — | — |
| `yellow_white_star` | Yellow-white star | 60–88 | +2 | 100 | 0 | 1 | — | — |
| `orange_dwarf` | Orange dwarf | 40–65 | -4 | 105 | 0 | 1 | — | — |
| `red_dwarf` | Red dwarf | 15–40 | -9 | 88 | 0 | 4 | — | — |
| `brown_dwarf` | Brown dwarf | 2–15 | -18 | 50 | 0 | 1 | — | — |
| `yellow_giant` | Yellow giant | 65–90 | +6 | 94 | 0 | 1 | — | — |
| `red_giant` | Red giant | 55–80 | +4 | 90 | 2 | 1 | white_dwarf | — |
| `blue_giant` | Blue giant | 80–100 | +11 | 88 | 2 | 2 | neutron_star | — |
| `red_supergiant` | Red supergiant | 60–85 | +6 | 85 | 4 | 2 | neutron_star | — |
| `blue_supergiant` | Blue supergiant | 90–100 | +15 | 80 | 4 | 2 | black_hole | — |
| `hypergiant` | Hypergiant | 92–100 | +17 | 72 | 6 | 3 | black_hole | instability 1 |
| `wolf_rayet` | Wolf-Rayet star | 88–100 | +16 | 70 | 5 | 3 | black_hole | sail danger +5 |
| `protostar` | Protostar | 20–50 | -6 | 70 | 0 | 4 | — | sail danger +5, instability 2 |
| `carbon_star` | Carbon star | 40–65 | +2 | 85 | 1 | 1 | white_dwarf | — |
| `white_dwarf` | White dwarf | 20–45 | -10 | 80 | 0 | 0 | — | — |
| `binary` | Binary star | 60–90 | +3 | 95 | 0 | 1 | — | eclipse +2 |
| `trinary` | Triple star | 60–90 | +4 | 90 | 0 | 1 | — | eclipse +3, instability 1 |
| `variable_star` | Variable star | 40–90 | +0 | 90 | 2 | 2 | neutron_star | instability 3 |
| `neutron_star` | Neutron star | 5–20 | -16 | 50 | 0 | 1 | — | sail danger +8 |
| `pulsar` | Pulsar | 10–30 | -14 | 50 | 1 | 2 | star_remnant | sail danger +10 |
| `magnetar` | Magnetar | 10–30 | -14 | 40 | 0 | 6 | — | sanity −1, sail danger +12 |
| `black_hole` | Black hole | 0–0 | -25 | 30 | 0 | 0 | — | sail danger +15 |
| `dead_star` | Dead star | 0–10 | -22 | 40 | 0 | 0 | — | — |
| `black_sun` | Black sun | 0–0 | -24 | 35 | 0 | 0 | — | sanity −1 |
| `broken_star` | Broken star | 30–60 | -6 | 70 | 3 | 3 | star_remnant | — |
| `star_remnant` | Star remnant | 10–25 | -15 | 50 | 0 | 0 | — | sail danger +5 |
| `reborn_star` | Reborn star | 70–85 | +2 | 100 | 0 | 1 | — | — |
| `chained_star` | Chained star | 30–55 | -3 | 90 | 0 | 1 | — | leak repair 1 |
| `watching_star` | Watching star | 40–70 | +0 | 95 | 0 | 1 | — | leak +1, sanity −2 |

Sets: dark = dead star, black sun, broken star, star remnant, black hole (leak source, LOST_STAR scenario). Extinguished = dead star, black sun, star remnant, black hole (rekindle target, dead-star quest).

## 14.2 Worlds and moons

A moon is a world with `parent_world_id`, so moon archetypes are world types: Europa-like moons are **ice-shell**, Titan-like moons **methane**, Io-like moons **lava**, small irregular moons **dwarf**. Every type has a row in every per-type table: catalogue, mechanics, climate weights, temperature, forced terrain and soil, seasons, endless day, terrain defaults and shape, cartography profile, place natures, signature minerals, disaster multipliers and the 3D surface.

New mechanics columns used by the new and existing types: `ore_yield_pct` (ore income of its communities), `disaster_pct` (multiplier per natural disaster), signature minerals (mineral layers), and the `artificial` flag (no earthquakes on artificial worlds).

| Type | Label | Temp | Capacity % | Gravity / air | Seasons | Climate weights | Special mechanics |
|---|---|---|---|---|---|---|---|
| `super_earth` | Super-earth | 64 | 110 | high / — | normal | rain 130 | earthquake ×1.5 |
| `ice_giant` | Ice giant | 10 | 35 | — / — | normal | ice age 250, scorching 20 | hidden route swallowed; storm ×2 |
| `hot_giant` | Hot giant | 98 | 20 | — / — | none | scorching 300, ice age 5 | route danger +5; hidden route swallowed; endless day (no night battles); storm ×2.5 |
| `iron` | Iron world | 58 | 55 | high / thin | normal | drought 200, rain 30 | ore yield 200%; earthquake ×1.2; storm ×0.5; iron, lead; ridges map |
| `carbon` | Diamond world | 55 | 60 | — / — | normal | drought 150 | ore yield 80%; earthquake ×1.2; gems |
| `greenhouse` | Greenhouse world | 97 | 30 | — / toxic | none | scorching 350, ice age 5, rain 20 | fertility decay 1; drought ×2.5; storm ×0.5; sulfur; terrain volcanic |
| `dwarf_planet` | Dwarf world | 6 | 40 | low / thin | two | ice age 300, scorching 10 | ore yield 70%; hidden route cosmic_mount; storm ×0; flood ×0; terrain ice_sheet |
| `chthonian` | Chthonian world | 96 | 20 | high / none | none | scorching 300, ice age 5, rain 10 | ore yield 180%; endless day (no night battles); earthquake ×2.5; iron, gold; terrain volcanic |
| `hycean` | Steam-ocean world | 78 | 90 | — / dense | normal | rain 250, drought 30 | storm ×2; flood ×1.5; salt |
| `jungle` | Jungle world | 72 | 120 | — / — | normal | rain 220, drought 40 | plague ×1.5; flood ×1.5; amber; terrain jungle |
| `forge` | Forge-world | 72 | 85 | — / dense | normal | scorching 180, drought 140, rain 50 | ore yield 160%, fertility decay 1, earthquakes ×1.5, iron and copper, terraced map |
| `fungal` | Fungal world | 56 | 95 | — / — | normal | rain 160, scorching 50 | sanity −1; hidden route dream_journey; plague ×2 |
| `shattered` | Shattered world | 45 | 70 | low / — | normal | drought 150 | ore yield 130%; route danger +8; leak +1; hidden route cosmic_mount; earthquake ×2; star_metal; fragments map |
| `hollow` | Hollow world | 60 | 100 | low / — | none | temperate 300 | leak repair 1; endless day (no night battles); earthquake ×0.5; gems |
| `ice_shell` | Ice-shell world | 10 | 45 | low / thin | normal | ice age 250, scorching 15 | earthquake ×1.5; storm ×0.3; salt; terrain ice_sheet |
| `methane` | Methane world | 5 | 35 | low / dense | normal | rain 150, ice age 200, scorching 10 | flood ×1.5; terrain tundra |

Existing types gain disaster multipliers: lava earthquakes ×2, ocean storms ×1.5, corpse-world plague ×1.5, living-world earthquakes ×1.5 (the world stirs). The god's palace and the generation ship (artificial) have no earthquakes.

## 14.3 Sky events

| Kind | Status | Mechanics |
|---|---|---|
| eclipse | existing | weight + the eclipse weight of multiple suns; the world is now chosen weighted by its moons and its star's companions instead of at random |
| comet, alignment, supernova, black sun, void storm | existing | supernova now leaves its type's remnant (14.1); supernova and black sun pick the star by collapse weight |
| **flare** | new | the star is picked by flare weight. Every region of its worlds loses `sky.flare_fertility_loss` fertility (crop failure); communities gain `sky.flare_piety_gain` piety (auroras as omens); each light-sail route bound to it is **scorched** shut (new closure `scorched`, route state `scorched`) with `sky.flare_sail_scorch_chance` for `sky.flare_sail_epochs`, and reopens by itself when it cools; journeys on it are lost (`travel_methods.sail_snap_loss_pct`) or wait; the aurora weather weight rises by `weather.flare_aurora_pct` on its worlds while it lasts |

Fixes:
- `SkyEventRow.until_epoch` is now set. Eclipse and flare last `sky.eclipse_lasting_epochs` / `sky.flare_lasting_epochs`, a comet `sky.comet_lasting_epochs`, a supernova's ash `sky.supernova_lasting_epochs`, an alignment until `cosmos.alignment_until_epoch`, a void storm for its sever duration. A black sun lasts until the star is rekindled (the rekindle closes it). Before, every past event stayed active for ever and its weather effects were permanent.
- Star events (supernova, black sun, flare) now act on the weather of **every** world of the star, not only on the one row's world.
- The spontaneous void storm of the afterlife phase now writes its sky event row, so its void rain shows in the weather like an ordered storm.

## 14.4 Horror events

| Kind | Status | Mechanics |
|---|---|---|
| stars align, eye in the sky, wave of silence, reverse rain, visit of the void | existing | unchanged |
| **the dimming** | new | the root star of the target world loses `cosmic_horror.dimming_brightness_loss` brightness. Through 14.1 its worlds cool (temperature, crops, weather); a dark star is not dimmed further |
| **whispers from beyond** | new | the most learned mortal (highest intellect) of the world, or else its strongest community, is taught a forbidden knowledge ("Whispers from Beyond"), which then feeds leak (forbidden holders), sanity erosion and military strength like any forbidden knowledge |

## 14.5 Travel

| Item | Status | Mechanics |
|---|---|---|
| **wormhole** | new travel method | a natural tunnel: needs astronomy and a ship; duration 1, danger 40; its throat is open only in some epochs (`travel_methods.wormhole_open_pct`, deterministic per route and epoch: state UNSTABLE when shut); not leaking; revealed by astronomers; exploration with astronomy opens wormholes |
| river of the dead | fix | passage now needs a realm-of-the-dead **or a corpse-world** end, because the corpse-world's own hidden route is the river (before, its river routes were unusable) |
| divine bridge collapse | fix | the route now gets closure **collapsed** (the value existed but was never set) and every journey on it gets a **bridge collapsed** event: it falls into the void (`travel_methods.bridge_collapse_loss_pct`) or turns back (recalled) |
| journey events | fix | **discovery** is recorded when an exploration journey discovers a resource or land on arrival; **stowaway** when stowaways arrive; **bridge collapsed** as above (all three existed but were never emitted) |
| frontend route state | fix | route records carry the engine's derived status (`status`: open, state, reason, opens and closes epoch), and the frontend shows it instead of guessing from active/closure (misaligned slingshots, collapsed bridges, scorched sails, shut wormholes) |

## 14.6 Other fixes

- Changing a world's type (player edit) re-applies the new type's forced gravity and atmosphere.
- The "planet stirs" button shows only for living worlds (the backend refuses corpse-worlds).
- The `artificial` flag is read: artificial worlds have no earthquakes (`world_physics.artificial_earthquake_pct`).

## 14.7 Visuals

- Every star type has a 3D look (core shader kind, corona, size, rays, companions) and a 2D colour (`--cosmos-star-*` tokens). New shader kinds: brown (banded dim ember), cocoon (protostar in dust), breathing (variable), chained (sigil rings), eye (watching), magnetar (pulse + field loops). Multiple suns draw two or three companions. The black hole reuses the photon ring and accretion disc.
- Every world type has a 3D surface code. New surfaces: hot gas, metal, shroud (greenhouse and methane hazes), forge, fungal, shattered, hollow, lineae (ice shell).
- The wormhole has a route look and colour token.

## 14.8 Prompts and text

- The hang-star tool lists every star type with its label (`star_types`), like world types.
- The star's description is given to the celestial deepener, the world line, world birth and the image prompter.

## 14.9 Database

One migration (`4b446c7e3bbb_cosmos_types`) widens the CHECK constraints of `stars.star_type`, `worlds.world_type`, `sky_events.kind`, `routes.method`, `routes.closure` and `horizon_intuitions.method`.

## 14.10 Tests

- Every star and world type has a row in every per-type table (catalogue completeness tests).
- Star heat, capacity, leak, sanity, collapse weight, remnant, flare, eclipse weight, sail danger and instability each change the outcome they claim.
- Every new world type's mechanics (ore yield, disaster multipliers, minerals, natures, seasons, endless day, forced physics) are read.
- The new events (flare, dimming, whispers), the wormhole and every fix have a test.
