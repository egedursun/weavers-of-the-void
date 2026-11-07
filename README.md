<a id="top"></a>

<p align="center">
  <img src="frontend/public/brand/logo-512.png" alt="Weavers of the Void" width="240">
</p>

<h1 align="center">Weavers of the Void</h1>

<p align="center">
  <b>The self-writing world.</b><br>
  You are the Creator. Your sons are gods. Every age, the world writes its own legend.
</p>

<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/version-0.1.0-d4af37?style=flat-square">
  <img alt="Expansions" src="https://img.shields.io/badge/expansions-85%20included-7b3fe4?style=flat-square">
  <img alt="Rules" src="https://img.shields.io/badge/tunable%20rules-3%2C300%2B-4b2a8c?style=flat-square">
  <img alt="Python" src="https://img.shields.io/badge/python-3.13-3776ab?style=flat-square&logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-async-009688?style=flat-square&logo=fastapi&logoColor=white">
  <img alt="React" src="https://img.shields.io/badge/React-19-61dafb?style=flat-square&logo=react&logoColor=black">
  <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-strict-3178c6?style=flat-square&logo=typescript&logoColor=white">
  <img alt="Claude" src="https://img.shields.io/badge/agents-Claude%20Haiku-d97757?style=flat-square&logo=anthropic&logoColor=white">
  <img alt="Docker" src="https://img.shields.io/badge/docker-compose-2496ed?style=flat-square&logo=docker&logoColor=white">
  <img alt="Local first" src="https://img.shields.io/badge/local--first-single%20player-1e1b4b?style=flat-square">
</p>

<p align="center">
  <a href="#quick-start"><b>Quick start</b></a> ·
  <a href="#the-pitch">The pitch</a> ·
  <a href="#god-cards">God cards</a> ·
  <a href="#the-cosmos">The cosmos</a> ·
  <a href="#the-complete-edition-the-loom-and-85-expansions">85 expansions</a> ·
  <a href="#a-tour-of-the-app">The app</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="#documentation">Docs</a>
</p>

<br>

<table>
  <tr>
    <td align="center" width="25%"><b>🜂 You create</b><br><sub>Draw god cards, command your sons, answer prayers and reach into any mechanic by hand.</sub></td>
    <td align="center" width="25%"><b>✦ Gods decide</b><br><sub>Every son is a living Claude agent with passions, grudges and more than a hundred divine tools.</sub></td>
    <td align="center" width="25%"><b>⚙ The world turns</b><br><sub>Eighty-plus deterministic phases simulate fifty years of history between every divine turn.</sub></td>
    <td align="center" width="25%"><b>📜 Fate remembers</b><br><sub>An impartial judge weighs every age, writes the chronicle and keeps a ledger you can undo.</sub></td>
  </tr>
</table>

<p align="center">
  <a href="#1-turning-seasons"><img src="common/assets/images/dlc-covers/01-turning-seasons.jpg" width="15%" alt="Turning Seasons"></a>
  <a href="#18-ties-of-blood"><img src="common/assets/images/dlc-covers/18-ties-of-blood.jpg" width="15%" alt="Ties of Blood"></a>
  <a href="#36-throne-and-council"><img src="common/assets/images/dlc-covers/36-throne-and-council.jpg" width="15%" alt="Throne and Council"></a>
  <a href="#52-admiralty"><img src="common/assets/images/dlc-covers/52-admiralty.jpg" width="15%" alt="Admiralty"></a>
  <a href="#67-made-in-their-image"><img src="common/assets/images/dlc-covers/67-made-in-their-image.jpg" width="15%" alt="Made in Their Image"></a>
  <a href="#74-starfall"><img src="common/assets/images/dlc-covers/74-starfall.jpg" width="15%" alt="Starfall"></a>
</p>

<p align="center"><sub><b>The Loom and 85 expansions, all included.</b> <a href="#the-cover-wall">See all 86 covers →</a></sub></p>

---

<details open>
<summary><b>Contents</b></summary>

- [The pitch](#the-pitch)
- [Why Weavers of the Void](#why-weavers-of-the-void)
- [Meet the cast](#meet-the-cast)
- [How an age unfolds](#how-an-age-unfolds)
  - [A taste of an age](#a-taste-of-an-age)
- [God cards](#god-cards)
- [Features](#features)
- [What the gods can make](#what-the-gods-can-make)
- [The cosmos](#the-cosmos)
- [Goals and glory](#goals-and-glory)
- [A tour of the app](#a-tour-of-the-app)
- [The agents](#the-agents)
- [By the numbers](#by-the-numbers)
- [The complete edition: The Loom and 85 expansions](#the-complete-edition-the-loom-and-85-expansions)
  - [The Loom](#the-loom) · [The eleven chapters](#the-eleven-chapters) · [The cover wall](#the-cover-wall) · [Every expansion](#every-expansion)
  - [I](#chapter-i) · [II](#chapter-ii) · [III](#chapter-iii) · [IV](#chapter-iv) · [V](#chapter-v) · [VI](#chapter-vi) · [VII](#chapter-vii) · [VIII](#chapter-viii) · [IX](#chapter-ix) · [X](#chapter-x) · [XI](#chapter-xi)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Local development](#local-development)
- [Docker](#docker)
- [Media store](#media-store)
- [Image worker](#image-worker)
- [Backups and world packages](#backups-and-world-packages)
- [Architecture](#architecture)
- [Engineering principles](#engineering-principles)
- [Bringing a legacy world](#bringing-a-legacy-world)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Documentation](#documentation)

</details>

## The pitch

**Weavers of the Void is a self-generating lore engine.** You do not write the story. You set it in motion.

You play the Creator, a god at the dawn of a cosmos. Your sons are **god cards**, drawn in six rarities from *Common* to *Mythic*, and each one is a living Claude agent with its own passions, grudges, domains and a toolbox of more than a hundred divine powers. Once per epoch every son wakes, reads the world, and acts: he raises mountains, founds cults, whispers to prophets, breeds monsters, curses bloodlines and schemes against his brothers.

Between their turns, a **deterministic world engine** takes over. More than eighty simulation phases turn fifty years of history: mortals are born, love, betray and die; peoples migrate, languages drift apart, harvests fail, plagues learn, empires overreach, armies starve on the march and heroes walk the paths of myth. Then **Fate** judges the age, weighs every creation, and writes the chronicle.

Nothing is scripted. Nothing is lost. Every number has a reason you can read, and every story traces itself across the centuries.

> *Every thread is connected. Now you can see them all.*

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## Why Weavers of the Void

- **A story nobody wrote.** No script, no event deck, no quest list. Every legend in your chronicle grows out of causes you can trace.
- **Gods with minds of their own.** Your sons are agents, not dice rolls. They plan, they hold grudges, they lie to the council and they rebel.
- **Depth all the way down.** Eighty-five expansions of interlocking mechanics, from the soil under a field to the death of a star, all running at once.
- **Total control, zero lock-in.** Every rule tunable, every mechanic triggerable, every act undoable, every prompt visible. Your world lives on your disk.
- **Beautiful by default.** A celestial interface, a living map, a 3D cosmos and a painting for every record, generated on your own machine.

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## Meet the cast

| | Who | What they do |
|---|---|---|
| 🜂 | **The Creator** | You. Name yourself at genesis, choose the language of your lore, and shape the cosmos with essence. Your mood shifts with the world, your cult rises or fades, and mortals can pray to you directly. |
| ✦ | **The Sons** | God cards in six rarities, each a Claude agent with loyalty, ambition, anger and mercy. They create, bless, curse, wage war, scheme against each other and sometimes rebel against you. They can die, and they can be brought back. |
| ⚖ | **Fate** | The impartial judge of every age. Fate canonises or rejects creations, records canon facts, opens and closes story threads, fulfils prophecies and keeps the ledger of every act. |
| ☄ | **Foreign gods** | Powers from beyond your pantheon, awake or asleep, with their own strength, attitude and gifts: shields, callers and stranger things. Ally with them, war with them, or devour them. |
| 👁 | **Mortals and peoples** | Named heroes, prophets, kings and heretics, and the peoples, settlements, factions and cults they build. They pray, they remember, they believe the wrong things, and they write history of their own. |

### Thirteen ways to begin

The genesis wizard opens every world from a template that sets its tone, its first peoples and its first troubles:

| | | | |
|---|---|---|---|
| **Dark Fantasy** | **Mythic Age** | **Cosmic Horror** | **Fairy Tale** |
| **Star Myth** | **Sand and Ash** | **Primordial Dawn** | **Crowns and Knives** |
| **Drowned World** | **Long Winter** | **After the Fall** | **Sky Islands** |
| **Age of Engines** | | | |

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## How an age unfolds

```mermaid
flowchart LR
    C([The Creator]) -->|draws, commands, blesses| S
    subgraph S [The Sons act]
        S1[God card agents<br/>run in parallel]
        S2[100+ divine tools<br/>gated by rarity]
    end
    S -->|creations, miracles, schemes| E
    subgraph E [The World turns]
        E1[80+ deterministic phases]
        E2[3,300+ tunable rules]
    end
    E -->|50 years of history| F
    subgraph F [Fate judges]
        F1[Verdict on every creation]
        F2[The chronicle is written]
    end
    F -->|images, legends, the ledger| C
```

1. **The Creator moves first.** Draw sons, bless or punish them, answer prayers, convene the council, or reach into the engine and pull any lever by hand.
2. **The sons take their turn.** Every son is an agent. They reason over a typed view of the world, call their tools, and pay for every act in essence.
3. **The world turns.** A seeded, reproducible simulation runs every mechanic: nature, bodies, societies, economies, wars, faiths, magic, the gods and the cosmos itself.
4. **Fate judges.** An impartial agent weighs the age, canonises or rejects creations, closes threads and writes the chronicle.
5. **The world remembers.** Every act lands in Fate's ledger, fully undoable. Images are painted locally for every new record. A backup is taken before every epoch.

Every epoch streams live to the browser: watch each phase complete, each tool call land and each verdict arrive as it happens.

### A taste of an age

<sub><i>An illustrative excerpt in the style of the chronicle. Every world writes its own.</i></sub>

> **Epoch 14 · The Age of Salt and Ash**
>
> In the forty-first year, the monsoon failed over the Varn coast, and the granaries of Tessaly emptied by midwinter. The Merciful Son, whose domain is Harvest, sent a dream to the widow Ilsa of the river villages; she woke speaking of a buried spring, and a cult was born before the thaw.
>
> His brother the Ash-Crowned did not forgive the gift. He whispered to the hungry lords of Tessaly that the river villages hoarded grain, and by summer the banners were raised. The war lasted nine years. The spring was salted. Ilsa was burned as a witch at the crossing she had saved.
>
> *Fate's verdict:* the cult of the buried spring is canon. The war is canon. The Merciful Son's loyalty to the Creator rises; the Ash-Crowned gains renown and loses mercy. A thread opens: **the widow's ashes are said to have fallen on the salted spring.**

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## God cards

Every son is drawn as a card. Rarity sets how much he can do in a turn, how fast his essence returns, how strong he is born and how high his power can climb. Every number below is a default rule you can retune in Settings → World Rules.

| Rarity | Draw odds | Action points | Essence per epoch | Born with stats | Power cap | Turn steps |
|---|---:|---:|---:|---|---:|---:|
| ⬜ **Common** | 50% | 3 | 8 | 20–45 | 2 | 11 |
| 🟩 **Uncommon** | 27% | 3 | 10 | 30–55 | 3 | 13 |
| 🟦 **Rare** | 14% | 3 | 12 | 40–65 | 5 | 15 |
| 🟪 **Epic** | 7% | 3 | 15 | 50–80 | 7 | 17 |
| 🟧 **Legendary** | 2% | 4 | 18 | 65–95 | 10 | 19 |
| 🟥 **Mythic** | ascension only | 5 | 24 | 80–100 | 12 | 21 |

Every new world opens with three sons: one Common, one Rare and one Legendary. Sons grow in level and renown as they act, and a son who reaches **level 9** with **90 renown** can **ascend** to the next rarity for 90 essence. **Mythic** is never drawn: it is earned only by ascension. Mortals can climb too: deify a hero, and they join the pantheon as a son of their own class.

### What rarity unlocks

| From | The son gains |
|---|---|
| **Common** | Reading and reflection, memory, language, kin, prayer, and the creation of the world's foundations |
| **Uncommon** | Influence over any entity, marking a chosen one, curses, miracles and spirit cloaking |
| **Rare** | Sending dreams, calling down disasters, granting knowledge, inciting wars, taking a mortal's life, holy worlds, interworld treaties and war on foreign gods |
| **Epic** | Sealing gates, rekindling dead stars and stitching leaks in the fabric of the cosmos |
| **Legendary** | Transforming and destroying, bearing divine children, opening cosmic beds, birthing whole worlds and writing natural laws |
| **Mythic** | Hanging new stars in the sky and extinguishing old ones |

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## Features

### A world that lives on its own
- **Eighty-plus simulation phases** for mortals, demography, settlements, ecology, climate, disasters, epidemics, trade, markets, production, factions, institutions, diplomacy, espionage, warfare, faith, spirits, magic, heroes, horror, monsters, realms, the afterlife, the pantheon, the sky and the cosmos.
- **Deterministic and reproducible.** The same world and the same seed produce the same history, tick for tick.
- **Conservation everywhere.** People, goods, coin and souls are counted to the last one. Nothing is made from air.
- **The Why of Everything.** Hover any number and see exactly what made it so.
- **The Harshness Dial.** Heroic, realistic or brutal: one dial sets how deadly the world is.

### Gods that think
- **God cards in six rarities**, from humble read-and-reflect tools up to hanging new stars in the sky.
- **More than a hundred son tools** across thirteen families: reading, memory, language, kin, prayer, creation, resources, influence, knowledge, intervention, war, death and the cosmos.
- **Passions and reputation.** Loyalty, ambition, anger and mercy drive every son. Mortals love, fear or forget them. Rebels rise, and the father's hand falls.
- **Forty divine domains**, from sea, fire and storm to memory, oath, salt, glass and sleep. Every domain has a price.
- **The council of heaven.** Even gods must vote. Even gods must scheme.
- **Talk to your sons.** Open a chat with any son, between epochs, in character.

### Fate, the chronicler
- **An impartial judge** for every age: verdicts, canon facts, open threads and fulfilled prophecies.
- **Chronicler, bard and deepener**: agents that turn raw history into legend, epic and ever-richer lore, and restore lost chronicles.
- **Voices of the peoples**: every people tells the story of the gods its own way.
- **Fate's ledger**: every player action is recorded with its cause and can be undone.

### Languages and lore
- **Procedural languages** with dialects, contact, drift and death. Every name means something, every word has a history.
- **Lore in your language**: English or Turkish, chosen once when the Creator is born and carried into every prompt.
- **Prayers, dreams, manifestations and threats**: mortals talk to the gods, and the gods answer.

### An interface worth living in
- **Thirty-plus screens**, from the Pantheon and the Chronicle to the living Map, the 3D Cosmos and the knowledge graph.
- **Real-time everywhere.** Server-Sent Events stream every phase, every tool call and every verdict.
- **Every value is editable.** All 3,300+ balance rules are tunable live. Every mechanic runs automatically and can also be run, suppressed, edited or pinned by hand.
- **A command palette** that reaches every record and every screen from the keyboard.
- **A celestial design system**: deep indigo and gold, Cinzel display type, six rarity colours, dark and light themes, and a visual-consistency test on every route.

### Paintings for every record
- **A local image worker** paints the Creator, the sons, foreign gods, worlds and entities from prompts written by the agents.
- **Apple Silicon or NVIDIA**: native MLX on a Mac, a CUDA container everywhere else, the same HTTP contract for both.
- **Your gallery, your disk**: weights live in a local volume, images in your own media store.

### Built to be trusted
- **Local-first and single-player.** Your world lives in SQLite on your disk.
- **Backups before every epoch**, versioned `.aerona` world packages, and crash-safe, resumable jobs.
- **Your Claude subscription, never an API key.** Every agent call runs on Claude Haiku through the Claude Agent SDK.
- **Engine-only mode.** Set `AERONA_LLM_ENABLED=false` and the world turns on pure simulation.

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## What the gods can make

Thirty-three kinds of record, every one a living part of the simulation, every one with its own stats, bonds, chronicle and portrait:

| Land | Life | Society | Mind and spirit | Power | Cosmos |
|---|---|---|---|---|---|
| Region | Species | People | Language | Faction | Celestial |
| Place | Beast | Mortal | Legend | Polity | Natural law |
| Resource | Disease | Settlement | Tradition | House | Outer being |
| Structure | | Item | Cult | Army | Vessel |
| Trade route | | Artwork | Spirit | Treaty | Event |
| | | | Knowledge | Law | Prophecy |
| | | | Rite | Ideology | |

### Forty domains

Every son and every foreign god holds domains, and every domain bends the world in its own way:

> Sea · Fire · Earth · Sky · Storm · Death · Life · Dream · Time · Light · Shadow · War · Craft · Knowledge · Love · Trickery · Hunt · Plants · Bone · Blood · Sound · Stone · Ice · Madness · Trade · Road · Plague · Harvest · Moon · Sun · Star · Lies · Oath · Memory · Hunger · Glass · Salt · Ash · Border · Sleep

### Eighteen branches of knowledge

> Agriculture · Metallurgy · Seafaring · Writing · Architecture · Medicine · Magic · Warfare · Astronomy · Trade · Sky navigation · Shipbuilding · Gate lore · Pathfinding · Void living · Immortality · Biomancy · Forbidden

### Thirty creature traits

> Flying · Venomous · Soul-eater · Radiant · Fissiparous · Hive mind · Stoneskin · Time rewinder · Shapeshifter · Mind reader · Armoured · Burrowing · Aquatic · Amphibious · Pack hunter · Ambush predator · Regenerating · Poisonous flesh · Fire-breathing · Cold-breathing · Echolocation · Camouflage · Swarm breeder · Long-lived · Mimic · Spirit sight · Iron-eating · Crop pest · Plague bearer · Sacred animal

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## The cosmos

Real astronomy and pure fantasy share one sky, and **every type is a mechanic, never a label**. A star sets the heat, the harvest, the life capacity and the sanity of everyone beneath it, and decides what it leaves behind when it dies. A world type sets its ores, disasters, seasons, gravity, air and hidden routes.

<details open>
<summary><b>32 star types</b></summary>

| Main sequence | Giants | Young and strange | Remnants | Many suns | Fantastic |
|---|---|---|---|---|---|
| Yellow dwarf | Yellow giant | Protostar | White dwarf | Binary star | Dead star |
| Blue star | Red giant | Wolf-Rayet star | Neutron star | Triple star | Black sun |
| Blue-white star | Blue giant | Carbon star | Pulsar | | Broken star |
| White star | Red supergiant | Variable star | Magnetar | | Reborn star |
| Yellow-white star | Blue supergiant | | Black hole | | Chained star |
| Orange dwarf | Hypergiant | | Star remnant | | Watching star |
| Red dwarf | | | | | |
| Brown dwarf | | | | | |

</details>

<details open>
<summary><b>34 world types</b></summary>

| Classic | Real astronomy | Strange | Divine and dead |
|---|---|---|---|
| Ordinary world | Super-earth | Crystal world | Realm of the dead |
| Ocean world | Ice giant | Living planet | Corpse-world |
| Sand world | Hot giant | Dream realm | The god's palace |
| Ice world | Iron world | Mirror world | Generation ship |
| Lava world | Diamond world | Void pocket | Forge-world |
| Gas giant | Greenhouse world | Fungal world | |
| Ringed world | Dwarf world | Shattered world | |
| Asteroid belt | Chthonian world | Hollow world | |
| Tidally locked world | Steam-ocean world | | |
| | Jungle world | | |
| | Ice-shell world | | |
| | Methane world | | |

Moons are worlds too: Europa-like moons are ice-shell worlds, Titan-like moons methane worlds, Io-like moons lava worlds.

</details>

<details open>
<summary><b>Sky, horror and travel</b></summary>

| Sky events | Cosmic horror | Ways between worlds |
|---|---|---|
| Eclipse | The stars align | Ancient gate |
| Comet | The eye in the sky | Space fold |
| Alignment | The wave of silence | Light sail |
| Flare | Reverse rain | Cosmic mount |
| Supernova | Visit of the void | Dream journey |
| Black sun | The dimming | River of the dead |
| Void storm | Whispers from beyond | Divine bridge |
| | | Slingshot orbit |
| | | Swallowing |
| | | Wormhole |

</details>

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## Goals and glory

Every world can chase a **scenario** for points, and every milestone earns an **achievement**, once, forever.

<table>
<tr>
<td valign="top" width="50%">

**Eight scenarios**

- Keep doomsday away
- Unite all peoples in one faith
- Rekindle the lost star
- A many-world cosmos, every world alive
- An age of unbroken peace
- A civilization reaching for the stars
- A loyal pantheon
- New horizons on the map

</td>
<td valign="top" width="50%">

**Seventeen achievements**

The second sky · Constellation · The word came true · Return from death · The father's hand · Babel · Crowded world · Someone called you · The creator's cult · Interstellar traveller · Saga completed · God of epochs · Ancient · Crowded pantheon · First explorers · Sensed world · The weapons fell silent

</td>
</tr>
</table>

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## A tour of the app

| Screen | What you find there |
|---|---|
| **Genesis** | The birth of a world: name the Creator, pick the lore language, draw the first sons |
| **Overview** | The state of the world at a glance: epoch, doomsday clock, essence, peoples, wars and the latest verdicts |
| **Pantheon** | Every son as a card, with rarity, passions, reputation, domains and power; foreign gods beside them |
| **Epoch** | Start, watch, pause and resume an epoch, with every phase and every son turn streamed live |
| **Chronicle** | The written history of every age, from Fate's verdicts to the bard's epics |
| **Council** | The council of the gods: motions, votes and schemes |
| **Prayers** | Prayers, dreams and threats from mortals, and your answers |
| **Wars** | Every war, front, army and battle, summary first |
| **Economy** | Markets, prices, trade routes, production and money |
| **Map** | The living Voronoi map: terrain, borders, settlements, routes and scars |
| **Cosmos** | The heavens in 2D and 3D: stars, worlds, moons, routes and journeys |
| **Network** | The knowledge graph of every bond between every record |
| **Atlas** | Every region, place and people, searchable and linkable |
| **Languages** | Every tongue, its words, dialects, contacts and descendants |
| **Gallery** | Every painting the image worker has made |
| **Goals** | Scenarios, achievements and your score |
| **Ledger** | Fate's book: every act with its cause, ready to undo |
| **Notifications** | Everything the world wants you to know |
| **Settings** | Game, World Rules, Engine, Fate, Prompts, Records, Images, Data, Appearance and Maintenance |
| **Design** | The living reference of every component and type role, in both themes |

Every record opens in a drawer stack on the right, so you can follow a thread from a king to his sword to the god who forged it without losing your place.

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## The agents

Twenty-nine agent roles, every one on Claude Haiku, every prompt in one typed catalog:

| Creation | Play | Judgement | Lore | Art and language |
|---|---|---|---|---|
| Genesis | Son turn | Fate | Chronicler | Creator portrait |
| World birth | Mortal turn | Fate extra judgment | Chronicle completion | Entity image prompts |
| Son summoning | Council of the gods | Fate bond suggestion | Lost chronicle | Cosmos image prompts |
| Son powers | Son chat | Fate related bond naming | Deepening | Naming |
| Awakening of the peoples | | | Creator epic | Translation |
| Revelation | | | Creator deepening | Localisation |
| | | | Foreign god deepening | |
| | | | Son epic | |
| | | | Voices of the peoples | |

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## By the numbers

| | |
|---:|---|
| **85** | themed expansions plus **The Loom**, all included |
| **86** | painted covers, one for The Loom and each expansion |
| **80+** | deterministic simulation phases |
| **3,300+** | tunable balance rules, editable live |
| **100+** | divine tools for the sons, in 13 families |
| **29** | agent roles |
| **190+** | prompt templates in one catalog |
| **40** | divine domains |
| **33** | kinds of record |
| **32** | star types |
| **34** | world types |
| **30** | creature traits |
| **18** | branches of knowledge |
| **10** | ways to travel between worlds |
| **6** | god card rarities |
| **30+** | screens in the web app |
| **2** | lore languages: English and Turkish |
| **0** | API keys required |

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## The complete edition: The Loom and 85 expansions

<p align="center">
  <img src="common/assets/images/collectors-edition.jpg" width="520" alt="The Weavers of the Void collector's edition box on a display pedestal">
</p>

<p align="center"><sub><b>The Collector's Edition</b> · the base experience and all 85 expansions in one box</sub></p>

Weavers of the Void ships as the complete edition. **The Loom** and all **85 expansions** across eleven chapters are fully integrated into the engine, the agents and the interface. There is nothing to unlock, nothing to install and nothing to wait for: every mechanic below runs in every world from the first epoch, and every one of them can be tuned, triggered and inspected from the app.

### The Loom

<table>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/00-the-loom.jpg"><img src="common/assets/images/dlc-covers/00-the-loom.jpg" width="220" alt="The Loom box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/00-the-loom.jpg"><img src="common/assets/images/dlc-backs/00-the-loom.jpg" width="220" alt="The Loom box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

*Every thread is connected. Now you can see them all.*

Before the gods walk and the armies march, the world needs a loom. Pull any thread and feel the whole cloth move. A queen's fever, a failed harvest, a god's grudge: each is a cause with a name, and each effect can show you its reason. The Loom is the heart beneath every expansion, the reason a mortal once drawn in eight numbers can now be read through about seventy-five.

- **The Why of Everything** — hover over any number in the world and read what made it so: a wound, a law, a festival, this season's weather, a god's curse. Sixteen kinds of cause, each named, each with its own span of time.
- **Chains of Consequence** — every battle, death and betrayal records its cause. Fate writes "because the king lost his hand at Varn", and thirty-seven kinds of chapter, from wedding to schism, gather the moments into a history you can browse by figure, place or kind.
- **Nothing Lost, Nothing Made from Air** — people, goods, coin, souls and divine essence are counted to the last one, every turn. A soldier who marches home was first taken from his village, and every death becomes a soul that goes somewhere.
- **No Idle Numbers** — a son's mercy, the world's danger, the Creator's passions, a betrayal that starts a war. Values the world once only stored now move it, and every link between systems must have something that sets it and something that feels it.
- **Your Hand on Every Lever** — every mechanic answers to five commands: run it now, suppress it for epochs, edit what it controls, retune its rules, pin a value in place. All undoable. A mechanic without a lever, a screen and a chronicle line never ships.
- **The Harshness Dial** — heroic, realistic or brutal. One dial scales wounds, infection, plague, famine, childbirth and siege hunger together. On realistic, a famous king can die of one arrow, and every rate beneath the dial stays yours to adjust.
- **Many Cores, One World** — the engine computes each world in parallel and merges the results in a fixed order, so one core or many gives the same turn to the last byte. Quiet regions and dormant mortals rest until something touches them.

**In your world:** The Creator asked why a city was starving. The answer named a dry year, the levy that took its farmers and a field salted a century earlier. The Creator followed the salt back through the chain to a broken oath between two brothers.

</td>
</tr>
</table>

### The eleven chapters

| Chapter | Expansions | What it brings |
|---|---|---|
| 🌿 [**I. World and Nature**](#chapter-i) | 1–9 | Seasons, soils, geology, winds, farming, wildlife, evolution, named beasts and plagues |
| 🫀 [**II. Body and Mind**](#chapter-ii) | 10–16 | Wounds and bodies, curses, inner lives, life arcs, relationships, households and strange peoples |
| 🏛 [**III. Society and Culture**](#chapter-iii) | 17–27 | Honour codes, bloodlines, demography, movements, riots, rites, gift economies, art, sport, languages and rewritten history |
| ⚒ [**IV. Economy and City**](#chapter-iv) | 28–35 | Industry, money, trade roads, labour, cities, wonders, relics and organised crime |
| 👑 [**V. Power and Politics**](#chapter-v) | 36–47 | Thrones, patronage, claims, law, estates, treaties, rise and fall, couriers, rumour, blackmail, spy networks and belief |
| ⚔ [**VI. War**](#chapter-vi) | 48–54 | Armies that eat, battles, sieges, campaigns, fleets, duels and blood feuds |
| 🕯 [**VII. Faith and Spirits**](#chapter-vii) | 55–60 | Doctrines, prophets, the afterlife, local spirits, witch hunts and oracles |
| ✶ [**VIII. Magic and Myth**](#chapter-viii) | 61–64 | A grammar of magic, forbidden arts, walkers of myth and constructs |
| ☀ [**IX. The Gods**](#chapter-ix) | 65–72 | Forty domains, dominion, belief that reshapes gods, avatars, the court of heaven, apotheosis, laws of creation and the hungering dark |
| 🪐 [**X. The Cosmos**](#chapter-x) | 73–80 | Orbital heavens, impacts, terraforming, thirty-four world types, rifts, star travel, deep time and turning ages |
| 📖 [**XI. Knowledge and Eras**](#chapter-xi) | 81–85 | Discovery, scholarship, open-ended technology, the storyteller and expeditions into the dark |

### The cover wall

The Loom and eighty-five expansions: eighty-six covers, one wall. Click any cover to jump to its features.

<p align="center">
<a href="#the-loom"><img src="common/assets/images/dlc-covers/00-the-loom.jpg" width="11%" alt="The Loom"></a>
<a href="#1-turning-seasons"><img src="common/assets/images/dlc-covers/01-turning-seasons.jpg" width="11%" alt="Expansion 1"></a>
<a href="#2-the-living-land"><img src="common/assets/images/dlc-covers/02-the-living-land.jpg" width="11%" alt="Expansion 2"></a>
<a href="#3-stone-and-deep"><img src="common/assets/images/dlc-covers/03-stone-and-deep.jpg" width="11%" alt="Expansion 3"></a>
<a href="#4-winds-of-the-world"><img src="common/assets/images/dlc-covers/04-winds-of-the-world.jpg" width="11%" alt="Expansion 4"></a>
<a href="#5-plough-and-net"><img src="common/assets/images/dlc-covers/05-plough-and-net.jpg" width="11%" alt="Expansion 5"></a>
<a href="#6-wild-kingdoms"><img src="common/assets/images/dlc-covers/06-wild-kingdoms.jpg" width="11%" alt="Expansion 6"></a>
<a href="#7-tooth-and-claw"><img src="common/assets/images/dlc-covers/07-tooth-and-claw.jpg" width="11%" alt="Expansion 7"></a>
<a href="#8-wyrms-and-hoards"><img src="common/assets/images/dlc-covers/08-wyrms-and-hoards.jpg" width="11%" alt="Expansion 8"></a>
<a href="#9-plague-ledger"><img src="common/assets/images/dlc-covers/09-plague-ledger.jpg" width="11%" alt="Expansion 9"></a>
<a href="#10-flesh-and-bone"><img src="common/assets/images/dlc-covers/10-flesh-and-bone.jpg" width="11%" alt="Expansion 10"></a>
<a href="#11-curse-of-the-full-moon"><img src="common/assets/images/dlc-covers/11-curse-of-the-full-moon.jpg" width="11%" alt="Expansion 11"></a>
<a href="#12-the-inner-life"><img src="common/assets/images/dlc-covers/12-the-inner-life.jpg" width="11%" alt="Expansion 12"></a>
<a href="#13-cradle-to-pyre"><img src="common/assets/images/dlc-covers/13-cradle-to-pyre.jpg" width="11%" alt="Expansion 13"></a>
<a href="#14-hearts-and-hands"><img src="common/assets/images/dlc-covers/14-hearts-and-hands.jpg" width="11%" alt="Expansion 14"></a>
<a href="#15-hearth-and-home"><img src="common/assets/images/dlc-covers/15-hearth-and-home.jpg" width="11%" alt="Expansion 15"></a>
<a href="#16-strange-flesh"><img src="common/assets/images/dlc-covers/16-strange-flesh.jpg" width="11%" alt="Expansion 16"></a>
<a href="#17-codes-of-honour"><img src="common/assets/images/dlc-covers/17-codes-of-honour.jpg" width="11%" alt="Expansion 17"></a>
<a href="#18-ties-of-blood"><img src="common/assets/images/dlc-covers/18-ties-of-blood.jpg" width="11%" alt="Expansion 18"></a>
<a href="#19-the-teeming-millions"><img src="common/assets/images/dlc-covers/19-the-teeming-millions.jpg" width="11%" alt="Expansion 19"></a>
<a href="#20-many-banners"><img src="common/assets/images/dlc-covers/20-many-banners.jpg" width="11%" alt="Expansion 20"></a>
<a href="#21-fire-in-the-streets"><img src="common/assets/images/dlc-covers/21-fire-in-the-streets.jpg" width="11%" alt="Expansion 21"></a>
<a href="#22-feast-and-funeral"><img src="common/assets/images/dlc-covers/22-feast-and-funeral.jpg" width="11%" alt="Expansion 22"></a>
<a href="#23-the-gift"><img src="common/assets/images/dlc-covers/23-the-gift.jpg" width="11%" alt="Expansion 23"></a>
<a href="#24-muse-and-market"><img src="common/assets/images/dlc-covers/24-muse-and-market.jpg" width="11%" alt="Expansion 24"></a>
<a href="#25-blues-and-greens"><img src="common/assets/images/dlc-covers/25-blues-and-greens.jpg" width="11%" alt="Expansion 25"></a>
<a href="#26-tongues-of-ages"><img src="common/assets/images/dlc-covers/26-tongues-of-ages.jpg" width="11%" alt="Expansion 26"></a>
<a href="#27-the-rewritten-past"><img src="common/assets/images/dlc-covers/27-the-rewritten-past.jpg" width="11%" alt="Expansion 27"></a>
<a href="#28-forge-and-furnace"><img src="common/assets/images/dlc-covers/28-forge-and-furnace.jpg" width="11%" alt="Expansion 28"></a>
<a href="#29-coin-of-the-realm"><img src="common/assets/images/dlc-covers/29-coin-of-the-realm.jpg" width="11%" alt="Expansion 29"></a>
<a href="#30-the-salt-road"><img src="common/assets/images/dlc-covers/30-the-salt-road.jpg" width="11%" alt="Expansion 30"></a>
<a href="#31-yoke-and-wage"><img src="common/assets/images/dlc-covers/31-yoke-and-wage.jpg" width="11%" alt="Expansion 31"></a>
<a href="#32-walls-and-wards"><img src="common/assets/images/dlc-covers/32-walls-and-wards.jpg" width="11%" alt="Expansion 32"></a>
<a href="#33-wonders-rising"><img src="common/assets/images/dlc-covers/33-wonders-rising.jpg" width="11%" alt="Expansion 33"></a>
<a href="#34-heirlooms-and-relics"><img src="common/assets/images/dlc-covers/34-heirlooms-and-relics.jpg" width="11%" alt="Expansion 34"></a>
<a href="#35-underworld"><img src="common/assets/images/dlc-covers/35-underworld.jpg" width="11%" alt="Expansion 35"></a>
<a href="#36-throne-and-council"><img src="common/assets/images/dlc-covers/36-throne-and-council.jpg" width="11%" alt="Expansion 36"></a>
<a href="#37-patrons-and-puppets"><img src="common/assets/images/dlc-covers/37-patrons-and-puppets.jpg" width="11%" alt="Expansion 37"></a>
<a href="#38-crowns-unclaimed"><img src="common/assets/images/dlc-covers/38-crowns-unclaimed.jpg" width="11%" alt="Expansion 38"></a>
<a href="#39-the-iron-code"><img src="common/assets/images/dlc-covers/39-iron-code.jpg" width="11%" alt="Expansion 39"></a>
<a href="#40-guilds-and-estates"><img src="common/assets/images/dlc-covers/40-guilds-and-estates.jpg" width="11%" alt="Expansion 40"></a>
<a href="#41-pacts-and-perfidy"><img src="common/assets/images/dlc-covers/41-pacts-and-perfidy.jpg" width="11%" alt="Expansion 41"></a>
<a href="#42-rise-and-ruin"><img src="common/assets/images/dlc-covers/42-rise-and-ruin.jpg" width="11%" alt="Expansion 42"></a>
<a href="#43-couriers-and-ciphers"><img src="common/assets/images/dlc-covers/43-couriers-and-ciphers.jpg" width="11%" alt="Expansion 43"></a>
<a href="#44-tongues-of-rumour"><img src="common/assets/images/dlc-covers/44-tongues-of-rumour.jpg" width="11%" alt="Expansion 44"></a>
<a href="#45-velvet-daggers"><img src="common/assets/images/dlc-covers/45-velvet-daggers.jpg" width="11%" alt="Expansion 45"></a>
<a href="#46-shadow-networks"><img src="common/assets/images/dlc-covers/46-shadow-networks.jpg" width="11%" alt="Expansion 46"></a>
<a href="#47-fog-of-belief"><img src="common/assets/images/dlc-covers/47-fog-of-belief.jpg" width="11%" alt="Expansion 47"></a>
<a href="#48-steel-and-banner"><img src="common/assets/images/dlc-covers/48-steel-and-banner.jpg" width="11%" alt="Expansion 48"></a>
<a href="#49-field-of-glory"><img src="common/assets/images/dlc-covers/49-field-of-glory.jpg" width="11%" alt="Expansion 49"></a>
<a href="#50-walls-will-fall"><img src="common/assets/images/dlc-covers/50-walls-will-fall.jpg" width="11%" alt="Expansion 50"></a>
<a href="#51-theatre-of-war"><img src="common/assets/images/dlc-covers/51-theatre-of-war.jpg" width="11%" alt="Expansion 51"></a>
<a href="#52-admiralty"><img src="common/assets/images/dlc-covers/52-admiralty.jpg" width="11%" alt="Expansion 52"></a>
<a href="#53-blade-and-honour"><img src="common/assets/images/dlc-covers/53-blade-and-honour.jpg" width="11%" alt="Expansion 53"></a>
<a href="#54-blood-feud"><img src="common/assets/images/dlc-covers/54-blood-feud.jpg" width="11%" alt="Expansion 54"></a>
<a href="#55-tenets-of-flame"><img src="common/assets/images/dlc-covers/55-tenets-of-flame.jpg" width="11%" alt="Expansion 55"></a>
<a href="#56-prophets-of-the-end"><img src="common/assets/images/dlc-covers/56-prophets-of-the-end.jpg" width="11%" alt="Expansion 56"></a>
<a href="#57-beyond-the-veil"><img src="common/assets/images/dlc-covers/57-beyond-the-veil.jpg" width="11%" alt="Expansion 57"></a>
<a href="#58-spirits-of-hearth-and-river"><img src="common/assets/images/dlc-covers/58-spirits-of-hearth-and-river.jpg" width="11%" alt="Expansion 58"></a>
<a href="#59-hex-and-hunt"><img src="common/assets/images/dlc-covers/59-hex-and-hunt.jpg" width="11%" alt="Expansion 59"></a>
<a href="#60-omens-and-oracles"><img src="common/assets/images/dlc-covers/60-omens-and-oracles.jpg" width="11%" alt="Expansion 60"></a>
<a href="#61-the-arcanum"><img src="common/assets/images/dlc-covers/61-the-arcanum.jpg" width="11%" alt="Expansion 61"></a>
<a href="#62-forbidden-arts"><img src="common/assets/images/dlc-covers/62-forbidden-arts.jpg" width="11%" alt="Expansion 62"></a>
<a href="#63-walkers-of-myth"><img src="common/assets/images/dlc-covers/63-walkers-of-myth.jpg" width="11%" alt="Expansion 63"></a>
<a href="#64-clockwork-souls"><img src="common/assets/images/dlc-covers/64-clockwork-souls.jpg" width="11%" alt="Expansion 64"></a>
<a href="#65-forty-domains"><img src="common/assets/images/dlc-covers/65-forty-domains.jpg" width="11%" alt="Expansion 65"></a>
<a href="#66-dominion"><img src="common/assets/images/dlc-covers/66-dominion.jpg" width="11%" alt="Expansion 66"></a>
<a href="#67-made-in-their-image"><img src="common/assets/images/dlc-covers/67-made-in-their-image.jpg" width="11%" alt="Expansion 67"></a>
<a href="#68-avatars"><img src="common/assets/images/dlc-covers/68-avatars.jpg" width="11%" alt="Expansion 68"></a>
<a href="#69-court-of-heaven"><img src="common/assets/images/dlc-covers/69-court-of-heaven.jpg" width="11%" alt="Expansion 69"></a>
<a href="#70-apotheosis"><img src="common/assets/images/dlc-covers/70-apotheosis.jpg" width="11%" alt="Expansion 70"></a>
<a href="#71-laws-of-creation"><img src="common/assets/images/dlc-covers/71-laws-of-creation.jpg" width="11%" alt="Expansion 71"></a>
<a href="#72-the-hungering-dark"><img src="common/assets/images/dlc-covers/72-the-hungering-dark.jpg" width="11%" alt="Expansion 72"></a>
<a href="#73-clockwork-heavens"><img src="common/assets/images/dlc-covers/73-clockwork-heavens.jpg" width="11%" alt="Expansion 73"></a>
<a href="#74-starfall"><img src="common/assets/images/dlc-covers/74-starfall.jpg" width="11%" alt="Expansion 74"></a>
<a href="#75-worldforge"><img src="common/assets/images/dlc-covers/75-worldforge.jpg" width="11%" alt="Expansion 75"></a>
<a href="#76-thirty-four-worlds"><img src="common/assets/images/dlc-covers/76-thirty-four-worlds.jpg" width="11%" alt="Expansion 76"></a>
<a href="#77-rifts-and-wonders"><img src="common/assets/images/dlc-covers/77-rifts-and-wonders.jpg" width="11%" alt="Expansion 77"></a>
<a href="#78-between-the-stars"><img src="common/assets/images/dlc-covers/78-between-the-stars.jpg" width="11%" alt="Expansion 78"></a>
<a href="#79-deep-time"><img src="common/assets/images/dlc-covers/79-deep-time.jpg" width="11%" alt="Expansion 79"></a>
<a href="#80-the-turning-wheel"><img src="common/assets/images/dlc-covers/80-the-turning-wheel.jpg" width="11%" alt="Expansion 80"></a>
<a href="#81-sparks-of-genius"><img src="common/assets/images/dlc-covers/81-sparks-of-genius.jpg" width="11%" alt="Expansion 81"></a>
<a href="#82-the-scholars-lamp"><img src="common/assets/images/dlc-covers/82-the-scholars-lamp.jpg" width="11%" alt="Expansion 82"></a>
<a href="#83-steam-and-lightning"><img src="common/assets/images/dlc-covers/83-steam-and-lightning.jpg" width="11%" alt="Expansion 83"></a>
<a href="#84-fateweaver"><img src="common/assets/images/dlc-covers/84-fateweaver.jpg" width="11%" alt="Expansion 84"></a>
<a href="#85-into-the-dark"><img src="common/assets/images/dlc-covers/85-into-the-dark.jpg" width="11%" alt="Expansion 85"></a>
</p>

### Every expansion

Every expansion below runs in every world from the first epoch, woven into the engine, the agents and the interface.

<a id="chapter-i"></a>

### 🌿 I. World and Nature

<details open>
<summary><b>Expansions 1–9</b> · <sub>9 expansions</sub></summary>

<table>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/01-turning-seasons.jpg"><img src="common/assets/images/dlc-covers/01-turning-seasons.jpg" width="220" alt="Turning Seasons box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/01-turning-seasons.jpg"><img src="common/assets/images/dlc-backs/01-turning-seasons.jpg" width="220" alt="Turning Seasons box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 1. Turning Seasons

*Fifty years pass in an epoch. Now you will feel every winter.*

Your world has a pulse. Inside every fifty-year epoch the engine lives through real years: sowing springs, campaign summers, killing winters. The same storm sinks a fleet, pins an archer line in the mud, cheers a storm god's faithful and ruins a harvest, all at once and each for a reason you can read.

- **Seasons Built from the Sky** — two to six seasons per world, forged from axial tilt, moons and world type. Ice worlds endure a long winter and a short thaw. Tidally locked worlds have no seasons at all.
- **Seventeen Kinds of Weather** — fog, blizzard, hail, heat wave, magic storm, ash fall after a supernova, void rain where the dark leaks in. Each strikes armies, sailors, harvests and morale in its own way.
- **Wars Fought Season by Season** — campaigns march through real springs and winters, and the chronicle reads "in the third winter of the war".
- **The Year of Ash Rain** — the cruellest year of every epoch earns a name, enters the chronicle, can harden into legend and is mourned with a fast day.
- **A Calendar for Every People** — regnal years, founding eras, years since the god's descent or since the comet last returned. A calendar reform can set two cults at each other's throats.
- **Moons, Tides and Eclipses** — moons pull the tides that open and close coasts and decide how often the sun goes dark.
- **Seasons in Your Hands** — reshape any season yourself, or watch a son seize the power to reorder them.

**In your world:** A blizzard in the second winter of the siege broke the attackers. The defenders' storm god took the credit, and the hungry year became a fast day their grandchildren still keep.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/02-the-living-land.jpg"><img src="common/assets/images/dlc-covers/02-the-living-land.jpg" width="220" alt="The Living Land box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/02-the-living-land.jpg"><img src="common/assets/images/dlc-backs/02-the-living-land.jpg" width="220" alt="The Living Land box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 2. The Living Land

*The map was a picture. Now it is a place.*

Every region now carries soil, rainfall, forest, rivers and wounds, drawn from the very map you see. Clear the woods and the hills erode. Farm too hard and the soil fails, the people leave and the forest walks back in. Fight a battle by a ford and the ground remembers it. The land keeps a record of everything done to it, and everything done on it reads the land.

- **Soil, Sun and Rain** — twenty-two terrain kinds, from steppe and high pass to crystal field, living flesh and void shore, over ten soils including ash and bone. Each decides how six kinds of traveller cross it, from marching feet and wagons to boats and burrowers.
- **The Wild Walks Back** — clearing, farming, grazing, mining and building thin the forest and breed fever, and drought on overgrazed land makes desert. Abandon the fields and the land climbs back through grassland and shrub to old forest, until a wildfire starts it over.
- **Scars on the Earth** — battlefields, plague grounds, salted fields, craters, haunted and blighted ground, and wounds where the void leaked through. Eight kinds of scar outlive the people who made them, and every harvest drawn from them is poorer.
- **Ley Lines** — neighbouring regions rich in magic link into lines that carry magic storms, feed wizards and strengthen any temple or gate built upon them. Their nexuses become holy sites and war aims, and salt, a leak or a god can sever a line.
- **Blessed, Cursed and Savage Lands** — evil ground brings blood rain and raises the dead, blessed ground offers healing springs and gentle weather, and savage ground grows huge beasts that resist taming. Massacres darken a region, saints and temples brighten it, farms tame it.
- **Danger with Teeth** — bandits, beasts, disease, quicksand and avalanche now kill settlers, ambush armies and choke merchant roads. Avalanches close the passes in winter, floods take the valleys in spring, and an army marching into an unmapped region can lose its way.
- **Twenty-Eight Kinds of Place** — fords, groves, springs, lairs, nexuses, crossroads and the corpses of gods. Passes draw battles, holy ground draws pilgrims, and explorers, seers and miners uncover buried relics, sealed spirits, lost knowledge and doors to the underworld.

**In your world:** A kingdom cleared its hill forests for wheat. The slopes eroded, the soil gave out, famine emptied the villages and the oaks crept back over the ruins. Generations later, settlers found the land rich again and called it the Green Grave.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/03-stone-and-deep.jpg"><img src="common/assets/images/dlc-covers/03-stone-and-deep.jpg" width="220" alt="Stone and Deep box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/03-stone-and-deep.jpg"><img src="common/assets/images/dlc-backs/03-stone-and-deep.jpg" width="220" alt="Stone and Deep box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 3. Stone and Deep

*Dig too deep, and something digs back.*

Beneath every region lies a column of stone you can read layer by layer: clay, limestone, granite, marble, obsidian, and on stranger worlds frozen methane, bone and glass. Your miners follow the veins down. The deeper they go, the rarer the ore and the harder the rock. Then a pick breaks through into a cavern no surface eye has seen, and something in the dark turns its head.

- **Layered Geology** — twelve kinds of rock and stranger ones on stranger worlds, each layer with its own veins. Limestone and sandstone hold water and hollow into caves, marble raises splendid temples, and the hardest stone yields only to better picks.
- **Three Caverns and a Sea of Fire** — below the aquifers lie three cavern layers, each a hidden world of fungus forests, blind beasts and cave peoples. Beneath them burns a magma sea that fuels forges and drowns the careless, and below that, the deep realm where the dead are kept.
- **Rivers That Live** — flow from upstream rain and spring snowmelt, rapids, salty estuaries and flood plains that shift when a great flood moves the river. Dam it upstream and the realm below goes thirsty, and a water dispute is reason enough for war.
- **Quakes and Fire Mountains** — plate boundaries drawn with the map decide where the earth shakes and the mountains burn. Eruptions darken the sky with ash, enrich the soil and can raise new land.
- **When the Mine Comes Down** — depth against the rock's strength and the miners' engineering sets the risk of collapse each year. A cave-in crushes miners, seals the shaft and sometimes breaks open a cavern, letting its beasts climb out.
- **Seal the Deep** — seal gates, collapsed tunnels, plug walls, warding rites and divine acts hold back what you woke. Every seal weakens with time, beasts and miners test it, and opening one again is a scheme waiting for a schemer.
- **Bones of Ages Past** — fossil beds hold extinct beasts, earlier creations and lost peoples. Floods, quakes and digs bring them up, and each culture reads them its own way: dragon bones for the bards, giants' relics for the priests, deep time for heretic scholars.

**In your world:** The miners of a mountain town chased a silver vein through the granite until the floor gave way into a cavern. Something came up the shaft. Their seal gate held for three generations, until a rival house paid to have it opened.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/04-winds-of-the-world.jpg"><img src="common/assets/images/dlc-covers/04-winds-of-the-world.jpg" width="220" alt="Winds of the World box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/04-winds-of-the-world.jpg"><img src="common/assets/images/dlc-backs/04-winds-of-the-world.jpg" width="220" alt="Winds of the World box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 4. Winds of the World

*Deserts where mountains steal the rain. Famine where the monsoon fails.*

The air moves for reasons now. Your world's spin, tilt and sunlight bend its winds into bands, the winds carry rain against the mountains and leave deserts behind them, and the currents decide which coasts grow rich on fish. When a distant ocean warms, two kingdoms that have never met lose their harvests in the same year, and the astronomers who tracked the cycle saw it coming.

- **Prevailing Winds** — trade-wind, westerly and polar bands, or stranger single bands on slow and tidally locked worlds, set the wind in every region and season. They chart the sailing routes, fan the wildfires and carry the smoke of the forges.
- **Rain Shadows** — moist wind climbs the mountains and rains on the windward side, leaving desert in the lee. Every forest and every desert sits where the physics puts it.
- **Monsoons** — winds that reverse with the seasons over land and sea feed whole peoples and set the sailing calendar of the trade routes. The year the monsoon fails is a famine year with a name.
- **Ocean Currents** — warm and cold currents set coastal climates, feed the fisheries and speed or slow the ships. They also carry wrecks, castaways, stowaway creatures and messages in bottles that start rumours on a foreign shore.
- **Droughts a World Apart** — slow climate oscillations bring drought to one land and flood to another in the same years. Diviners and astronomers who learn the rhythm can foretell the bad years.
- **Climate by Region** — the world's age of cold or warmth plays out differently on every coast and latitude. Felled forests dry their neighbours, a volcano brings a short chill and a supernova a long one, and storm, sun and ice gods push it region by region.
- **The Breathing Planet** — carbon, water and nutrients flow between volcano, forest, ocean, river and soil. Burn the forests across a world, or let a god impose an eternal summer, and the whole planet answers over epochs.

**In your world:** A river people burned their forests for fields. The rains thinned over the neighbouring hills, the hills dried to scrub, and the hungry hill clans came down to clear the last woods along the river.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/05-plough-and-net.jpg"><img src="common/assets/images/dlc-covers/05-plough-and-net.jpg" width="220" alt="Plough and Net box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/05-plough-and-net.jpg"><img src="common/assets/images/dlc-backs/05-plough-and-net.jpg" width="220" alt="Plough and Net box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 5. Plough and Net

*The soil keeps accounts. Sooner or later, it collects.*

Stand in any market town and look outward. Gardens and dairies hug the walls, forests feed the hearths beyond them, grain rolls further out, herds roam the edge, and a single new road redraws the whole pattern. Out there your farmers spend the soil's hidden stocks, sow beans to mend it, salt their fields with clever canals and fight their lords over who may graze the common.

- **Market Towns Arise** — hamlets serve daily needs, towns weekly ones, cities the rare. New settlements rise and old ones grow where the gaps between markets call for them, and every road or canal pulls the rings of farmland outward.
- **Hunger Breeds Invention** — crowded land pushes peoples toward irrigation, terraces, rotations and manuring, while empty land lets them wait. Peoples who remember famine learn bark breads and build granaries.
- **The Soil Remembers** — four hidden stocks lie under every field: a fixing element, minerals, organic matter and salt. Beans restore, fallow and manure heal, floods and ash enrich, and irrigation without drainage salts a civilisation's fields over centuries.
- **Orchards of Generations** — vineyards, groves and timber plantations take years or whole epochs to mature. An enemy who cuts them down wounds a land for generations.
- **Commons and Enclosure** — shared pastures, woods and fisheries thrive under good custom or ruin under overuse. When lords fence them, owners grow rich and cottagers drift to the cities. When lords keep the forest for the hunt, poachers are born.
- **Nets and Closed Seasons** — fish stocks swell with warm water and river silt, then collapse under too many nets. Closed seasons, quotas and gear bans, kept by wardens and dodged by poachers, save them. Whalers chase the biggest catch at the biggest risk.
- **Herds and Hooves** — grazing, milking, shearing, eggs and the butcher's block, breeding seasons and herd counts, oxen at the plough, and hounds and beasts trained for war, the hunt and the gate.

**In your world:** A river empire watered its plains for centuries without drains. The salt crept up, the harvests thinned, and its lords fenced the last common pastures. The dispossessed herders drifted into the cities, and their grievance became a movement.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/06-wild-kingdoms.jpg"><img src="common/assets/images/dlc-covers/06-wild-kingdoms.jpg" width="220" alt="Wild Kingdoms box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/06-wild-kingdoms.jpg"><img src="common/assets/images/dlc-backs/06-wild-kingdoms.jpg" width="220" alt="Wild Kingdoms box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 6. Wild Kingdoms

*Every creature has a range, a hunger and a place in the chain.*

Species leave the bestiary and take up residence in your land. Each one lives region by region, breeding in its own seasons, eating what its diet allows, following the herds or the grass along its migration path. When the deer are gone, the wolves come for your sheep. When the rats come for the granary, someone has to tame a cat.

- **Living Ranges** — every species holds its own population in every region, growing with litter size, habitat, warmth and food, and falling to hunters, predators, disease and the plough. Migrants shift between regions with the seasons.
- **Nine Ways to Eat** — herbivores, carnivores, scavengers and filter feeders, but also creatures that live on sunlight, stone, souls or the void. About thirty traits, from echolocation and camouflage to iron eating and fire breath, shape what each one does.
- **The Food Web** — who hunts whom is worked out each epoch from diet, size and shared ground. When prey runs short, predators raid your livestock. Lose a prey species and its hunters starve; lose a sacred one and a faith falls into crisis.
- **From Wild to Breed** — tame, herd, domesticate, then breed. Captive lines grow calmer and richer in hide, wool, milk and silk, and become mounts and war beasts. Populations cut off from their kin drift into highland and desert strains.
- **Pests and Blights** — crop pests thin the harvest, iron eaters gnaw the ore, plague bearers spread sickness, and vermin spoil the granary until a cat-like hunter is tamed for the work.
- **Flora Alive** — crops, herbs, dyes, timber, brews, reagents and poisons are living plants with seasons, soils and pests. Annual, perennial or tree, wild or cultivated into new cultivars, each crop is weighed against the year it grows in.
- **Companions and Champions** — a hound at the hearth eases loneliness, and its death leaves real grief. Falcons and war dogs sharpen the hunt. Among the largest, deadliest species, one beast may rise as a region's named terror or guardian.

**In your world:** A king's hunters killed the last of the sacred white stags. The stag's cult fell into a crisis of doctrine, the wolves that had fed on the herd turned on the flocks, and the shepherds drove far fewer sheep to the winter market.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/07-tooth-and-claw.jpg"><img src="common/assets/images/dlc-covers/07-tooth-and-claw.jpg" width="220" alt="Tooth and Claw box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/07-tooth-and-claw.jpg"><img src="common/assets/images/dlc-backs/07-tooth-and-claw.jpg" width="220" alt="Tooth and Claw box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 7. Tooth and Claw

*Nature does not stand still. It adapts, or it dies.*

Every population in your world carries its traits as a living average, and every epoch pushes it. Wolves make the deer faster. Hunters make them warier and smaller. A god's protection lets them soften, and leaking void scatters them into mutation. Leave two herds apart long enough and they become two species. Wipe out half the world's life and watch the survivors fill every empty niche.

- **Selection Pressure** — eight heritable traits, from venom potency to cold tolerance, shift each epoch in every range. Predator races prey, plague races host, and a god's curse or blessing passes down a whole lineage.
- **Niches and Rivals** — a niche is diet, habitat, size and waking hours, and no two species share one for long. After a mass extinction, survivors radiate into the empty niches. On islands giants dwarf and the small grow large, and abandoned livestock go feral.
- **The Energy Ladder** — each step of the food chain holds only a tenth of the life beneath it. Overhunt the grazers and the predators collapse. Pollinators, soil makers, dam builders and scavengers carry whole harvests, and their loss cascades into hunger and sickness.
- **Partners and Parasites** — pollinators feed the crops, ticks bleed the livestock, lampreys drain the fish, mistletoe chokes the trees, and harmless mimics fool hunters and scouts. Every brewer, baker and monastery guards its ferments and starters, heirlooms a fire can end.
- **Senses Beyond Ours** — night vision, scent, echolocation, vibration, heat, magnetic sense and spirit sight decide who spots whom. Night-sighted peoples raid in the dark, scent trails betray spies, and a magnetic sense needs no compass.
- **Sleep, Heat and Thorn** — hibernating beasts vanish for their season, lairs left open, and a disturbed sleeper wakes hungry. Cold-blooded creatures and peoples slow in winter and surge in heat. Thorns, toxins and carnivorous plants make the green itself dangerous.
- **The Feast of Crows** — every battle, plague, famine and massacre leaves a carrion pulse. Vultures and rats boom, stores spoil, sickness rises, predators close in, and the unburied dead stir as restless spirits until the feast is eaten.

**In your world:** No one buried the dead after the battle at the ford. Rats boomed on the field and spread into the town's granaries, spoiling the stores and carrying a fever. That winter the town was hungry and sick, and the field was said to walk at night.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/08-wyrms-and-hoards.jpg"><img src="common/assets/images/dlc-covers/08-wyrms-and-hoards.jpg" width="220" alt="Wyrms and Hoards box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/08-wyrms-and-hoards.jpg"><img src="common/assets/images/dlc-backs/08-wyrms-and-hoards.jpg" width="220" alt="Wyrms and Hoards box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 8. Wyrms and Hoards

*Not a species. A name, a lair, and a grudge.*

Meet the dragon of the northern peak by name. It has a body that scars, an age, a lair and a hoard of gold, bones and relics. It sleeps through the seasons, wakes when miners dig too close or a thief creeps in, and raids every farm in range. It remembers who wounded it, and it will hunt that hero's house.

- **Named Beasts** — individual creatures with six abilities, bodies that take real wounds, tempers from sleeping to enraged, and a terror that drains the courage and prosperity of every settlement nearby. The clever ones speak, bargain and scheme with minds of their own.
- **Hoards Worth a Kingdom** — raids and tribute fill the hoard, and villages may sign a treaty to pay it. Slay the beast and the hoard becomes a treasure site, and its looting crashes luxury prices across the market.
- **The Slayer's Reward** — quests name their quarry. A kill brings a title, dragonbone and star-scale, and a slayer's legend. Tamed beasts, even void beasts that drift between worlds, carry riders onto sky, sea and star routes; bound ones guard temples or march to war.
- **Born of the Deep** — unique horrors built from the bones up, with flesh of crystal, fire, steam or metal and breath of flame, frost, venom gas or web. Each hoards what it loves, hates what it hates, and wakes to deep mining or desecration.
- **Familiars** — a mage binds a beast or spirit by rite. It lends its senses, a skill or a shield against magic, and takes the backlash first. Its death wounds the mage. Beasts sacred to a god grow calm in that god's dominion.
- **Monster Contracts** — troubled villages post bounties in coin or favours. Professional hunters, some changed by their order's training, study each beast's anatomy for its weakness, and every job builds a reputation and a legend.
- **The Ancient Ones Remember** — a long-lived dragon recalls the war of three centuries ago as it truly happened, or as it prefers. It teaches rites, tongues and true names, sells secrets, and when it dies, all it never taught dies with it.

**In your world:** A hero wounded the wyrm and fled with a cup from its hoard. The wyrm remembered, and for two generations it hunted his house. When a contract hunter finally killed it, the looted hoard flooded the markets and luxury prices crashed across the realm.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/09-plague-ledger.jpg"><img src="common/assets/images/dlc-covers/09-plague-ledger.jpg" width="220" alt="Plague Ledger box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/09-plague-ledger.jpg"><img src="common/assets/images/dlc-backs/09-plague-ledger.jpg" width="220" alt="Plague Ledger box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 9. Plague Ledger

*It has a name. It has a host. And it learns.*

Plague is no longer a stroke of bad luck. It is a named enemy with a vector, a host and a history. It rides the caravans and the armies, waits in the swamp fly and the granary rat, and returns for the children born after its last visit. Close the ports and the markets starve. Ring the bells for prayer and the crowd spreads it. Somewhere, a plague god grows stronger with every outbreak.

- **Named Diseases** — each one has a vector (air, water, touch, bite, spirit, void or curse), a lethality, an incubation and a part of the body it attacks. A plague that turns endemic guards its marsh: the locals are immune, and invaders die at the walls.
- **Evolving Plagues** — crowded cities breed faster spread, sparse villages starve the deadliest strains, and every treatment in use breeds resistance. Survivors stay immune, so the plague comes back for the young, or mutates past them.
- **Silent Carriers** — some of the infected never fall ill. The merchant, envoy or pilgrim who seemed healthy seeds an outbreak across the sea, and only a skilled physician who holds the theory of contagion can find them.
- **Healers Right and Wrong** — sickness runs through incubation, fever, crisis, recovery or death, and its after-effects. A healer who believes bleeding cures fever raises the death toll; one who grasps contagion makes quarantine work. Addiction to drink, drugs and void dust is a disease too.
- **Where Plague Begins** — clearing forests, hunting bushmeat and herding beside wild hosts let a creature's disease leap to people. Insects follow the warm seasons, birds carry fevers along their migrations, and exterminating a host is a cure with an ecological price.
- **Hard Choices** — close the ports, quarantine the poor quarter, burn the dead, expel the sick or ring the bells, and pay in trade, riots, funeral quarrels or a crowd that spreads it. Purity-minded peoples found leper colonies; merciful ones build hospitals.
- **The Cure Race** — hospitals, universities and monasteries race against one disease, faster with scholars, true theories and fresh cases nearby. The winner holds a cure it can sell. Variolation trades a small risk for immunity, until the herd is safe.

**In your world:** A merchant who never felt ill carried the marsh fever upriver to the capital. The queen closed the ports, the guilds rioted in the empty markets, and a monastery won the race to a cure. It sold the cure city by city, and every city paid its price.

</td>
</tr>
</table>
</details>

<a id="chapter-ii"></a>

### 🫀 II. Body and Mind

<details open>
<summary><b>Expansions 10–16</b> · <sub>7 expansions</sub></summary>

<table>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/10-flesh-and-bone.jpg"><img src="common/assets/images/dlc-covers/10-flesh-and-bone.jpg" width="220" alt="Flesh and Bone box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/10-flesh-and-bone.jpg"><img src="common/assets/images/dlc-backs/10-flesh-and-bone.jpg" width="220" alt="Flesh and Bone box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 10. Flesh and Bone

*A king can lose a hand. A kingdom can lose a king.*

A duel at the river ford ends in a single stroke. The king lives, but his sword hand lies in the mud, and in a culture that demands a whole body on the throne, his claim bleeds out faster than he does. Every blow in your world lands on a real part of a real body, passes through real armour and leaves a mark that history must carry.

- **Bodies, Not Hit Points** — twelve body plans, from humanoid and serpentine to colossal and divine. The human body alone has twenty-two parts, each with a job: a lost eye spoils the archer, a shattered jaw silences the preacher.
- **Steel Meets Flesh** — every blow is weighed by momentum, edge and the hardness of steel against mail. Armour is tested layer by layer, padding, mail, cloak and shield, before the blade reaches skin, fat, muscle and bone.
- **Wounds with a Memory** — sixteen kinds, from bruise and frostbite to the void touch that never heals and the divine brand. Arteries bleed until bound, a struck nerve leaves a limp arm without a cut, and pain tips into shock and capture.
- **Healers and Surgeons** — medicine climbs from herbs to surgery, prosthetics and magical reattachment. Healers diagnose, suture, set, splint and cauterise, and a skilled surgeon turns an infected arm that would kill into an amputation a man survives.
- **The Silver Hand** — prostheses of wood, glass, silver and star metal restore part of what was lost, by material and craftsmanship. A legendary one becomes a relic that passes down the line and carries legitimacy with it.
- **What the Body Can Still Do** — melee, missile, command, craft, scholarship, presence, mobility and fertility are all read from the body. A blind scholar needs a reader. A people without helmets fills its halls with one-eyed veterans.
- **Scars Read by Culture** — honour cultures prize battle scars, purity cultures bar the maimed from the throne, and cults that sanctify suffering recruit them. Generations after a great war, a people still calls itself a people of one-armed grandfathers.

**In your world:** A duel took the king's sword hand. His people required a whole body on the throne, so his legitimacy collapsed and a rival claimant rose. The victors of the civil war blamed the healer who failed him, his guild lost its standing, and medicine spread more slowly through the kingdom.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/11-curse-of-the-full-moon.jpg"><img src="common/assets/images/dlc-covers/11-curse-of-the-full-moon.jpg" width="220" alt="Curse of the Full Moon box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/11-curse-of-the-full-moon.jpg"><img src="common/assets/images/dlc-backs/11-curse-of-the-full-moon.jpg" width="220" alt="Curse of the Full Moon box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 11. Curse of the Full Moon

*One bite. One desecrated grove. One night of the full moon.*

A poacher kills a stag in the Hunt god's grove. Nothing happens until the first moon rises full, and then something with his eyes runs through the village. Curses, venoms, drugs, blessings and transformations in your world share one grammar: how they pass from body to body, how long they wait, the stages they march through, and the single cure that ends them.

- **One Grammar for Every Affliction** — venom, blessing, void taint, possession, trauma and drugs share one shape: an onset, stages with their own effects, and a cure by rite, medicine, time or quest. Each is obvious, noticeable or hidden, and hidden ones are secrets.
- **Nine Ways to Catch It** — touch, bite, food, breath, blood, birth, rite, a single gaze, or the desecration of a holy place. Some curses carry themselves onward: a werebeast's bite passes the curse to the bitten.
- **Beasts Under the Moon** — the werebeast turns at every full moon of the world's first moon into a beast that still thinks. Each victim it bites may become the next hunter.
- **The Thirst** — the vampire-like curse stops ageing, adds a hunger for blood, burns in sunlight and needs a false name to hide behind. It comes from a blood rite gone wrong or the curse of a son of Blood.
- **Holy Ground Strikes Back** — rob a temple, kill in a sanctuary or defile a tomb, and the god answers with a curse shaped by its domains. The Hunt god sends the werebeast, the Blood god the thirst, the Death god a haunting.
- **Things That Walk at Night** — night trolls and bogeymen carry mortals away, and necromancers raise towers, bind spirits into corpses and march their undead hosts against living towns.
- **Dependence** — drugs and strong drink add a craving and its withdrawal to a single life. Void taint marches its bearer stage by stage into madness, and then into the arms of the outer cults.

**In your world:** A poacher desecrated the Hunt son's grove and turned at the next full moon. His bites spread the curse, the frightened village held a purge and burned an innocent hermit, whose vengeful ghost still walks. A healer found the cure rite too late for him.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/12-the-inner-life.jpg"><img src="common/assets/images/dlc-covers/12-the-inner-life.jpg" width="220" alt="The Inner Life box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/12-the-inner-life.jpg"><img src="common/assets/images/dlc-backs/12-the-inner-life.jpg" width="220" alt="The Inner Life box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 12. The Inner Life

*They don't just act. They feel, they want, they remember and they misjudge.*

The old general has every reason to end the siege. The walls hold, fever is in his camp and the treasury is empty. But he has spent too many winters and his own son's life on those walls, and he cannot let go. Every named mortal in your world carries a mind built in layers: what they can do, how they react, what they value, and the mistakes that follow.

- **Three Layers of Mind** — nineteen attributes for what a mortal can do, thirty-six facets for how they react, twenty-four beliefs for what they hold dear. A facet pushed to its extreme hardens into one of some forty traits, from brave to paranoid.
- **Eighty Thoughts, Twenty-Four Emotions** — a mortal who saw kin die, ate fine food or heard great music feels grief, contentment or awe. Moods run from elated to broken, and the strongest thoughts become memories that reshape beliefs and return on every anniversary.
- **Twenty-Two Needs** — from food, drink and rest to romance, solitude, beauty, nature, adventure and order. Unmet needs sour the mood, and the mortals under the heaviest pressure are the ones most likely to act.
- **Likes and Dislikes** — favourite foods, colours, creatures, seasons and art forms. A people that loves amber raises its price, merchants carry what the buyer craves, and a disgust shared by everyone becomes a taboo.
- **Minds That Err** — eight biases, among them overconfidence, sunk cost, groupthink and hostile attribution, bend every decision, and the explanation shows which one did it. Rulers fight on in wars they should have ended.
- **Ideas That Take Root** — a heretical book or a new theory incubates for seasons, bringing distraction or obsession, until it is rejected or taken in for good. The rationalist convert gains a sharper mind and loses his comfort in the rites.
- **Beliefs That Spread** — mortals, peoples, cults and gods weigh one another on the same beliefs. Ideas pass by prestige, by conformity and by sheer stickiness, so one charismatic reformer can move a whole town.

**In your world:** A paranoid king read his neighbour's new border fort as an attack, and his small, frightened council agreed. The war went badly, sunk cost kept him in it for years, and the defeat became the memory that shaped his heir's caution.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/13-cradle-to-pyre.jpg"><img src="common/assets/images/dlc-covers/13-cradle-to-pyre.jpg" width="220" alt="Cradle to Pyre box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/13-cradle-to-pyre.jpg"><img src="common/assets/images/dlc-backs/13-cradle-to-pyre.jpg" width="220" alt="Cradle to Pyre box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 13. Cradle to Pyre

*The children playing soldiers in the yard will one day be his council.*

A girl grows up in a household that cannot quite feed her. She learns her letters at the temple, takes up the loom, rises from apprentice to master and dreams of a masterwork she may never finish. Every mortal in your world moves through infancy, childhood, youth, adulthood and age, and each stage changes who they are allowed to become.

- **Six Ages of a Life** — infancy, childhood, youth, adulthood, old age and, for long-lived peoples, an ancient age of eccentric living history. Elders lose strength, gain wisdom, risk failing sight and turn mentor.
- **Pregnancy and Birth** — hunger and disease raise the risk, healers lower it. Twins, stillbirth, miscarriage and death in childbirth all happen, and a dead mother leaves an orphan, a widower and sometimes a crisis of succession.
- **Children of the Yard** — peer groups play at war, songs and riding, and their friendships and rivalries last into adulthood. Children denied play by labour, famine or war grow up less cheerful and more prone to stress.
- **Careers with Ranks** — fifty-four skills feed ladders from apprentice to grandmaster, soldier to marshal, acolyte to high priest. Unused skills rust. Lose a sword arm and the warrior becomes a teacher, a priest or a beggar.
- **Fifteen Life Dreams** — rule a realm, found a house, slay a beast, find love, know a truth. Each has milestones. A maimed would-be champion despairs unless he finds a new dream, and inspiration can strike as a masterwork fever.
- **Conviction and Breaking Points** — living by one's beliefs earns conviction to spend on a heroic effort in a crisis. Stress past its limit breaks a mortal into rage, flight, despair, zeal, vice or a sudden vision.
- **Twenty Ways to Die** — from bleeding, childbirth and drowning to execution, curse, void and heartbreak, each recorded with its place. The manner of death sets the house's prestige, the burial rite and the kind of ghost left behind.

**In your world:** A queen died in childbirth and left an infant daughter, while the law demanded a grown male heir. A regency council formed, a rival house pressed its claim, and the regent's mounting stress made the civil war that followed all but certain.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/14-hearts-and-hands.jpg"><img src="common/assets/images/dlc-covers/14-hearts-and-hands.jpg" width="220" alt="Hearts and Hands box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/14-hearts-and-hands.jpg"><img src="common/assets/images/dlc-backs/14-hearts-and-hands.jpg" width="220" alt="Hearts and Hands box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 14. Hearts and Hands

*Friends, lovers, rivals and nemeses. All of them remember.*

Two squires share a tent on campaign and come home comrades in arms. Years later one marries the other's sister, and a single careless insult at the wedding feast begins a feud that outlives them both. Every pair of mortals in your world carries a history of friendship, romance, rivalry and memory, and every word that passes between them adds to it.

- **Bonds on Four Axes** — friendship, romance, familiarity and rivalry combine into eighteen kinds of bond, from crush and confidant to mentor, drinking companion and nemesis. An affair becomes a secret, and its discovery ends in divorce, a duel or a house feud.
- **Twenty-One Interactions** — gossip, joke, flatter, boast, flirt, propose, confide a secret, threaten, brawl. Each is chosen by temperament, mood, the bond and whether the two even share a language, and each leaves a mark.
- **Memories That Become Opinions** — harmed me, saved me, betrayed me, gifted me. Opinion is built from trust, fear, respect, affection and grievance, and the strongest grudges pass to the heirs when the holder dies.
- **Burning Passions** — love, loyalty, hatred and devotion strong enough to be invoked in battle, duel or oath, for a great bonus or a breakdown. Lose the object of a passion and grief arrives at full force.
- **The Art of Persuasion** — appeal to belief, to self-interest, to authority, to evidence or to fear. The speaker's oratory meets the listener's stubbornness, and the result sways councils, congregations and envoys.
- **Pecking Orders and Circles** — households, courts, warbands and crews rank their members by strength, office and nerve. Drinking halls, poets' circles and hunting lodges breed friendships, conspiracies and ideologies.
- **Duels of Wit** — riddle games, insult verse, disputations, song and storytelling contests fought round by round, for honour, a bride or a captive's freedom. The judges' tastes count, and a famous flyting becomes a heroic poem.

**In your world:** A squire's loyalty to his lord burned so fiercely that he invoked it at the ford and broke the enemy line. When the lord later betrayed him, grief struck at full force, and the squire took up a new life dream: vengeance.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/15-hearth-and-home.jpg"><img src="common/assets/images/dlc-covers/15-hearth-and-home.jpg" width="220" alt="Hearth and Home box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/15-hearth-and-home.jpg"><img src="common/assets/images/dlc-backs/15-hearth-and-home.jpg" width="220" alt="Hearth and Home box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 15. Hearth and Home

*Behind every hero stands a household, and a supper table.*

The veteran comes home from the war with one leg. In a poor household he is another mouth and a burden on his daughter. In a rich one he is a respected elder by the fire. Every named mortal belongs to a household with a purse, a dwelling, a diet and a table, and what happens at that table shapes the body and the realm.

- **Households with a Purse** — pooled wages against rent, dowries, tithes and taxes, with heads, heirs, carers, servants, wards and lodgers. The household decides whom to marry, whom to apprentice and when to leave for another city.
- **Nine Kinds of Dwelling** — hut, longhouse, townhouse, manor, palace, tent, cave, ship and tower. Quality, rooms and furnishings set comfort, beauty, status and mood, and squalor breeds disease.
- **You Are What You Eat** — every diet is measured in staples, protein, fats, fresh food and salt. Famine children grow shorter, nobles grow taller, sailors without fresh food sicken, and inland peoples without salt swell at the throat.
- **Cuisines That Travel** — every culture cooks its own dishes from local ingredients, under its own tastes and taboos. Cuisines spread with contact and diaspora, fine food marks rank, and who may eat with whom is a rule of its own.
- **Taverns and Inns** — gossip runs through them, schemers and mercenary captains recruit in them, brawls break out in them, caravans sleep in them, and the innkeeper sells what he has overheard.
- **Drink and Its Customs** — every people decides which substances are taken, by whom and on which nights. Brewing feeds the economy, sacred drink gives mystics their visions, dependence ruins lives and feasts end in brawls.
- **Hours in a Year** — every class divides its year between work, rest, worship, leisure, travel and military service. Rest days and long festivals cost output and buy cohesion, and forced labour takes the hours back.

**In your world:** Sailors on a long voyage ran out of fresh food and fell to a scurvy-like sickness. The survivors drank their story into the harbour tavern, the gossip spread through the port, and the next fleet would not sail without the techniques that kept its food fresh.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/16-strange-flesh.jpg"><img src="common/assets/images/dlc-covers/16-strange-flesh.jpg" width="220" alt="Strange Flesh box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/16-strange-flesh.jpg"><img src="common/assets/images/dlc-backs/16-strange-flesh.jpg" width="220" alt="Strange Flesh box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 16. Strange Flesh

*Not every people breathes. Not every people dies.*

Your scouts report an enemy that does not bleed. Blades pass through it. Salt and iron burn it. Somewhere beneath the waves, another people writes in shell inlay and fights in three dimensions. Twelve biologies beyond the human rewrite every foundation of your world, from how a people eats and breeds to how it casts, decides, makes war and dies.

- **Twelve Biologies** — incorporeal, aquatic, aerial, subterranean, hive, plant-like, construct, ageless, shapeshifting, gaseous, crystalline and undead. Each changes body and harm, food and birth, culture and craft, war, disease and death.
- **Combine Them** — an aquatic hive, an ageless crystal people, a shapeshifting folk of the deep. The variants stack, and every system in the world reads the result.
- **Bodies Unlike Ours** — spirits are harmed in their coherence, not their flesh. Crystal folk shrug off blades but shatter under hammers and sound, and leave gemstones when they die. Aerial peoples break their hollow bones in falls.
- **Lives Unlike Ours** — plant peoples feed on sunlight and fear fire, aquatic peoples smelt metal at volcanic vents, cave peoples know little of the stars, and the ageless keep their grudges for ever.
- **Their Own Wars** — three-dimensional sea battles, expendable hive soldiers who die with their queen, slow and stubborn plant armies, undead hosts that fear nothing but holy harm. Against the deep folk, daylight is a weapon.
- **Their Own Magic** — spirits cast by presence alone, gaseous peoples in colour and scent, aquatic peoples sing and gesture their rites but cannot ink them, and the hive casts as one mind.
- **Their Own Minds** — constructs feel no loss aversion but follow orders beyond their purpose. Hive minds suffer total groupthink and over-protect their breeders. The ageless cling to sunk costs and ancient grudges.

**In your world:** When the crystal folk's old king died, his tomb filled with the gemstones of his body. Human robbers broke in, defiled it and drew down the curse of the crystal people's god, and in the war that followed hammers mattered, because blades barely scratched the defenders.

</td>
</tr>
</table>
</details>

<a id="chapter-iii"></a>

### 🏛 III. Society and Culture

<details open>
<summary><b>Expansions 17–27</b> · <sub>11 expansions</sub></summary>

<table>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/17-codes-of-honour.jpg"><img src="common/assets/images/dlc-covers/17-codes-of-honour.jpg" width="220" alt="Codes of Honour box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/17-codes-of-honour.jpg"><img src="common/assets/images/dlc-backs/17-codes-of-honour.jpg" width="220" alt="Codes of Honour box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 17. Codes of Honour

*What is forbidden here is sacred there.*

A guest is killed at a feast. In one hall it is the unthinkable crime, and the host's line will carry the infamy for generations. Across the river it is merely frowned upon, and soon forgotten. Every culture and every cult in your world keeps its own ledger of right and wrong, and judges every act, every guest and every ruler by it.

- **Forty Acts, Six Stances** — from killing kin, usury and necromancy to mercy to an enemy and cowardice, each act is required, admirable, acceptable, frowned upon, shameful or unthinkable. The verdict moves opinion, renown, a ruler's legitimacy and the actor's own guilt.
- **Laws Born of Outrage** — an unthinkable act with no law against it builds pressure for one. Ethics drift with belief and doctrine, and a deep enough split tears a culture into factions or births a new people.
- **Honour, Face and Dignity** — in honour cultures one member's shame is the whole house's, and demands apology, compensation, a duel or vengeance. Face cultures dread public shame and refuse through intermediaries. Dignity cultures shrug off insults and trust the law.
- **The Pillory** — public shaming, stripped titles and forced confession punish through reputation, as hard as the culture's honour model allows. Shame left unrestored festers into a household grievance.
- **Rules of the Room** — thirteen situations, from funeral, feast and court to mourning, sacred days and meeting a stranger, each with its own rules on speech, dress, gifts, laughter, weapons and food.
- **Will Against Custom** — every choice weighs desire, the bond with the other person and the norms of the room. Breaking a norm costs reputation, unless you are a rebel who enjoys it. Every custom keeps the history of where it came from.
- **Purity and Pollution** — corpses, birth, blood, forbidden foods, outsiders and trades such as tanning bar a person from temples and marriage until purified. Hereditary castes decide who works which trade, who lives in which district and who handles the dead.

**In your world:** A plague reached a city where touching the dead made a person impure. The avoidance slowed the contagion, but the sick were left without carers, and the low-caste gravediggers, who could not refuse the work, died first and in the greatest numbers.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/18-ties-of-blood.jpg"><img src="common/assets/images/dlc-covers/18-ties-of-blood.jpg" width="220" alt="Ties of Blood box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/18-ties-of-blood.jpg"><img src="common/assets/images/dlc-backs/18-ties-of-blood.jpg" width="220" alt="Ties of Blood box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 18. Ties of Blood

*The copper hair of the Varns. The madness of the Varns, too.*

Generations of cousin marriage have kept the crown in the family. They have also given the heir a fragile constitution and his grandfather's madness. Every face in your world is written in a genome that passes by real rules of dominance, and every marriage is a move in a long game of claims, alliances and inherited risk.

- **True Genetics** — height, build, skin, hair, eyes, face and voice pass by Mendelian rules, alongside inherited longevity, fertility, disease resistance, madness, giant blood and divine blood. Portraits keep the same face across a whole life.
- **Faces That Betray** — a child who looks too much like the wrong father exposes a secret parentage. Whole houses are known by their looks, like the copper hair of the Varns.
- **The Price of Pure Lines** — inbreeding raises the chance of heritable conditions, so royal houses must choose between tight claims and healthy heirs. Law and ethics decide which degree of cousin is forbidden.
- **Kinship Systems** — five rules of descent, four customs of residence, lineages, clans, moieties and houses. Where cousins are called siblings, marriage rules change. Where titles pass through the mother, the sister's son inherits.
- **Marriage Alliances** — cross-cousin marriage, clan exogamy, bride price, dowry, bride service, levirate and sororate. Lineages that exchange brides build lasting alliances, and the wife-givers come to outrank the wife-takers.
- **Other Ways to Be Born** — two sexes, sexes that change with age, sexes chosen in a fertile phase, hive castes of worker, soldier and breeder, or budding and fission. Succession, marriage and war all follow the system.
- **The Gift in the Blood** — magical aptitude runs in the genome, recessive and rare. Mage orders test children for it, bloodlines are bred toward it, and cultures honour, fear, persecute or tax it, while persecution thins it out.

**In your world:** To keep two claims in one house, the Varns married cousin to cousin. Their heirs came out sickly and touched with madness, rival houses contested every succession, and each challenge drove the Varns to marry closer still.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/19-the-teeming-millions.jpg"><img src="common/assets/images/dlc-covers/19-the-teeming-millions.jpg" width="220" alt="The Teeming Millions box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/19-the-teeming-millions.jpg"><img src="common/assets/images/dlc-backs/19-the-teeming-millions.jpg" width="220" alt="The Teeming Millions box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 19. The Teeming Millions

*History is made by the many. Now you can count them.*

The war is over, and the valley counts its dead. Not as one number: as a missing generation of young men, a surplus of widows, fewer children in the years to come and, where custom bends, women entering the crafts. Behind every named mortal stand the many, sorted by age, class and condition, and every famine, plague and war reshapes them.

- **Living Cohorts** — every community counts its children, adults and elders by class and by condition: maimed, veteran, sick, enslaved, captive. Births follow food and stress. Famines take the young and the old first; wars take young men.
- **Faces from the Crowd** — when the crowd produces something notable, a famine orphan or a plague's first victim, one person is lifted out and given a name, a memory and a life. No one named is ever merged back into the crowd.
- **Generations** — every generation remembers the war, plague or golden age of its youth, and its beliefs bend with it. When the last of a generation dies, the movements it held down finally rise.
- **Hands for Every Job** — adults go to ten kinds of work, from fields, herds and nets to mines, armies, temples and building sites, by class, resources and price. Output follows workers, skill, tools and land.
- **The Long Transition** — towns, literacy, educated women and surviving children slowly lower birth rates. The people grows old: fewer levies, more elders, a different politics.
- **Diasporas** — migrants follow their kin, and each wave pulls the next. Diasporas send money and news home, arrange marriages across the sea, build foreign quarters, and in time assimilate or become a new people.
- **Roles by Culture** — who may hold office, own property, fight, preach or inherit is set by sex, age and class, so matriarchies, egalitarian clans and caste societies all grow from each culture's own rules, and drift after every war.

**In your world:** A conquest left the defeated people a war generation that would not forget. Their children grew up on the stories, and when the last veteran of the conquest died, the movement the conquerors had suppressed for decades rose in the capital.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/20-many-banners.jpg"><img src="common/assets/images/dlc-covers/20-many-banners.jpg" width="220" alt="Many Banners box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/20-many-banners.jpg"><img src="common/assets/images/dlc-backs/20-many-banners.jpg" width="220" alt="Many Banners box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 20. Many Banners

*One city. Divided by faith this decade, by class the next.*

A weaver is a woman of the river people, a follower of the Moon, a guild member, a citizen of the city and a veteran's daughter, all at once. In the year of the holy war she marches with her faith. In the year of the famine she marches with her class. Which banner she follows decides who fights whom in your world.

- **Nine Layers of Self** — people, faith, class, locality, house or clan, guild, generation, realm and circle. Every mortal and every cohort holds all of them, each with its own strength.
- **Salience** — holy wars raise faith, famines raise class, invasions raise people and realm, strikes raise the guild. Sermons and propaganda stoke it, segregated districts sharpen it, and mixed marriages and mixed guilds blunt the lines they cross.
- **Lines of Fracture** — factions, revolts, riots and civil wars split along whichever identity burns brightest. A shared realm identity steadies the state; a strong sub-identity breeds separatism. Each group tells its own history.
- **Thirteen Tenets** — legalism, egalitarianism, divine right, mercantilism, militarism, rationalism, cosmopolitanism and more spread through scholars, books, schools and trade routes, each appealing to a different class. A realm that adopts one changes how it rules.
- **Revolutions of the Mind** — an egalitarian creed, an unhappy class and a weak realm add up to a revolt that aims at the government itself. Printing and universities breed new ideologies faster, and revolutions can write constitutions.
- **Creeds Against the Gods** — anti-god movements drain faith from the sons and so weaken their very existence. The gods answer with miracles or persecution. Other creeds turn to the Creator alone.
- **Revival of the Old Ways** — under foreign rule, peoples restore the old ways, rally around a prophet who fuses old and new, or adopt the conqueror's culture wholesale. Movements fight to revive a language, restore an old god or expel the foreigners.

**In your world:** A distant empire pressed its customs on the river people. A prophet rose promising the old god's return, his revival movement drew in the humiliated, and within a generation the city's riots ran along the lines of people and faith instead of class.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/21-fire-in-the-streets.jpg"><img src="common/assets/images/dlc-covers/21-fire-in-the-streets.jpg" width="220" alt="Fire in the Streets box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/21-fire-in-the-streets.jpg"><img src="common/assets/images/dlc-backs/21-fire-in-the-streets.jpg" width="220" alt="Fire in the Streets box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 21. Fire in the Streets

*It started with one stone thrown at the bread line.*

Bread doubles in price. A few apprentices throw stones, and nobody stops them. Their nerve lowers the fear of the dockers, whose anger tips the weavers, and by nightfall a district is burning. Every crowd in your world is made of people with their own breaking points, and the fate of a city depends on who moves first.

- **Every Person Has a Threshold** — anger, anxiety, conformity, hunger and friendship decide when each mortal and each slice of a crowd will join a riot, a lynching, a strike, a procession or a revolt.
- **Cascades, Not Dice** — a price spike, an execution, a sermon, an omen or a rumour starts it. If enough join to tip the next group, it spreads district by district. Its size and violence emerge; they are never rolled.
- **The Watch and the Agitator** — watchmen and garrisons raise every threshold by deterrence, and a charismatic agitator lowers them. The same spark dies in one city and burns down another.
- **Mobs** — crowds with a size, a target, an anger and leaders. They burn districts, storm the granary, lynch a scapegoat for a crime he never committed or open the gate to the besiegers, then scatter by fatigue, force or concession.
- **Panic** — fire, plague rumour, a beast in the streets or a sudden eclipse sends thousands running. Crowded districts trample their own, refugees flood the roads and hoarders strip the markets bare.
- **Fervour** — miracles, sermons and plague years spark revivals, flagellant processions and mass conversions that sweep through a city as fast as any riot.

**In your world:** During the siege a rumour said the governor was hoarding grain. The hungry crossed their thresholds one district at a time, the mob lynched a baker as the scapegoat, then opened the gate to the besiegers before the garrison could stop them.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/22-feast-and-funeral.jpg"><img src="common/assets/images/dlc-covers/22-feast-and-funeral.jpg" width="220" alt="Feast and Funeral box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/22-feast-and-funeral.jpg"><img src="common/assets/images/dlc-backs/22-feast-and-funeral.jpg" width="220" alt="Feast and Funeral box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 22. Feast and Funeral

*Every wedding is a battlefield. Every funeral is a negotiation.*

Three houses sit at one wedding table. The bride's brother will leave the tournament with a crushed knee, a steward will meet a rival's agent behind the stables, and somebody's affair will be noticed by the wrong cousin. Gatherings are where your world's stories collide, and the traditions that summon them finally shape the lives of the people who keep them.

- **Sixteen Living Traditions** — festivals, fasts, funeral rites, initiations, taboos, offerings, pilgrimages, hospitality laws, war dances, scar rites, ancestor feasts and more, each with its season, its cost in grain or incense and a real effect on those who keep it.
- **Customs with Teeth** — a pork taboo empties the pens, a taboo on winter fighting shapes the campaign year, and a hospitality law makes roads safer and guest-killing a grave infamy. Great victories, plagues and miracles found new customs.
- **Eighteen Kinds of Gathering** — feasts, weddings, coronations, tournaments, hunts, summits, fairs, public trials, executions, wakes and more. Guests come by bond, obligation and distance, and romances, plots and proposals crowd into a single evening.
- **Blood on the Tablecloth** — any gathering can become a massacre, judged by the guest laws of those who hear of it. Crowded festivals spread disease, and poor households that cannot afford a rite lose face.
- **Marked Bodies** — tattoos, scarification, piercings, cranial shaping, filed teeth and jewellery codes carry meaning: status, clan, deeds, marriage, mourning, protection. A warrior's tattoos count his kills; an exile's brand names his crime.
- **Names with Power** — patronymics, clan names, deed names, a secret name behind the public one, new names at initiation, marriage or vows, and the names of the dead left unspoken for a time.
- **Age-Sets** — those initiated together form a named set that rises together from warriors to senior elders, may marry only after the warrior grade and stays loyal across lineages. Delay the promotion feast and the young grow restless.

**In your world:** A chieftain murdered his rival at a wedding feast. His own people's hospitality law made the deed unthinkable, so his infamy outran his victory, and the massacre became a yearly day of mourning that kept the grievance alive for generations.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/23-the-gift.jpg"><img src="common/assets/images/dlc-covers/23-the-gift.jpg" width="220" alt="The Gift box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/23-the-gift.jpg"><img src="common/assets/images/dlc-backs/23-the-gift.jpg" width="220" alt="The Gift box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 23. The Gift

*A gift unreturned is a debt. A debt unpaid is a war.*

The chief of the eastern islands arrives with canoes heaped with dried fish and burns half of them on the beach to prove that he can. Now you must give more, or bow. Every gift in your world is weighed by what the receiver loves, written into a ledger and answered in kind, or remembered as a debt that someone, someday, will collect.

- **The Gift Ledger** — every gift is valued by the receiver's own tastes and never forgotten. To refuse is an insult, to return late is a debt of status, and to give more is the way to rise.
- **From Hearth to Heaven** — households, houses, realms, cults and gods all trade gifts under the same law of obligation, so a village and a god can owe each other in the same coin.
- **Competitive Giving** — chiefs claim rank by giving away or destroying wealth at feasts. Rivals must match them or lose prestige, until one side's treasury breaks.
- **Sacred Circuits** — famous treasures travel for ever along a fixed ring of communities. Holding one brings prestige for a while, and the circuit binds distant islands in peace and the duty of hospitality.
- **Gifts to the Gods** — every sacrifice puts a god in debt. Gods who answer generously gain standing, gods who ignore their offerings lose it faster, and each son sees its debts to the peoples set out plainly.
- **Bride Price and Dowry** — marriage payments in goods or in labour obey the same law, binding the kin of bride and groom long after the wedding.

**In your world:** Two island chiefs tried to outgive each other at feast after feast until the second chief's treasury broke and his rank fell. His people had sacrificed to their sea god for luck all the while, and the god who took and gave nothing back lost standing among them fast.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/24-muse-and-market.jpg"><img src="common/assets/images/dlc-covers/24-muse-and-market.jpg" width="220" alt="Muse and Market box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/24-muse-and-market.jpg"><img src="common/assets/images/dlc-backs/24-muse-and-market.jpg" width="220" alt="Muse and Market box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 24. Muse and Market

*Art that moves a people. Forgeries that fool a king.*

A poet's lament for the fallen is sung in every hall, and a generation later the people's appetite for war has cooled. Across the city, pilgrims still kneel before a saint's relic that a forger made in his cellar. Here art has a grammar, a lineage, a price and a message, and the classics decide what a people believes.

- **Art Forms with Grammar** — nine disciplines, from music and poetry to calligraphy, each with real structure: scales, rhythms and instruments, metres and stanzas, palettes and motifs. Poetry follows the sounds of its own tongue, so it never translates cleanly.
- **Forms Are Born and Die** — an inspired master invents a form, often by fusing two where cultures meet, or a lament after a plague. A form dies with its last practitioner if no notation survives, and banning a people's forms is a humiliation they resist.
- **Art That Argues** — twelve media, from song and heroic verse to fresco and mosaic, each carrying a message. A poem mourning the war dead cools a people's taste for war; a conqueror's statue swells his people's pride and keeps the conquered resisting.
- **Troupes on the Road** — touring players carry songs, legends and rumours along the trade routes, perform at feasts and fairs, and sometimes spy. Scribes copy books, printing multiplies them, and realms commission propaganda.
- **Collectors, Canons and Forgers** — prices follow renown, provenance and taste, collectors bid at auction and courts compete for artists. Undiscovered forgeries enter the canon, and art movements with manifestos fight canon wars to become the next orthodoxy.
- **Fashion Cycles** — forms, dress, cuisine and names rise with the trendsetters, saturate, grow common and fall from favour, while the old returns as revival. Every culture earns its visible periods of style.
- **Games of Skill and Chance** — board games train officers in strategy, dice drain household purses into debt and crime, and ball games become sport. Games travel with migrants and settle where they are liked.

**In your world:** After a plague, a grieving singer invented a lament form. Troupes carried it down the trade road, a neighbouring court paid to hear it, and within a generation the lament had entered both peoples' canons and cooled their appetite for war.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/25-blues-and-greens.jpg"><img src="common/assets/images/dlc-covers/25-blues-and-greens.jpg" width="220" alt="Blues and Greens box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/25-blues-and-greens.jpg"><img src="common/assets/images/dlc-backs/25-blues-and-greens.jpg" width="220" alt="Blues and Greens box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 25. Blues and Greens

*The race was lost. The tax was raised. The capital burned.*

Half the capital wears blue and half wears green, and it stopped being about chariots long ago. The Blues fill one temple and one district; the Greens fill another. When the Greens lose on a disputed verdict on the very day a new tax is proclaimed, the stands empty into the streets and nobody can say any more where sport ends and politics begins.

- **Clubs and Leagues** — teams of athletes race and compete at arenas and festivals, season after season, in leagues of rival clubs. Ball games, races and contests of strength all have their champions.
- **Fandoms** — every club holds a share of the city's heart, counted cohort by cohort, district by district.
- **The Betting Floor** — wagers on every race move household wealth up and down. A lucky season lifts a family; a bad one sinks it into debt.
- **Circus Factions** — when the colours line up with class, district or faith, a club becomes a political faction with real power over public opinion. Rulers can buy a club, and the voice of its crowds with it.
- **Riots of the Hippodrome** — a club's crowd is a riot waiting for its spark. A lost championship plus a tax rise can tip enough thresholds to burn a capital.

**In your world:** A disputed race result fell on the day of a new tax. The Greens' fans crossed the riot threshold and the hippodrome quarter burned. The emperor's Blue favourites demanded purges, and the Greens' patron senator marched on the capital with his own men.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/26-tongues-of-ages.jpg"><img src="common/assets/images/dlc-covers/26-tongues-of-ages.jpg" width="220" alt="Tongues of Ages box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/26-tongues-of-ages.jpg"><img src="common/assets/images/dlc-backs/26-tongues-of-ages.jpg" width="220" alt="Tongues of Ages box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 26. Tongues of Ages

*Every name means something. Every word has a history.*

A scholar kneels before a stone carved in two scripts: one dead for ages, one still spoken in the market. Seasons later she reads a forgotten king's name, and with it a lost technique, and an error that will one day become a legend. Your world's languages drift by real sound laws, so cognates, dialects and dead tongues are born from its history.

- **Sound Change** — every language gathers ordered sound laws through contact, prestige, migration or drift. Daughter tongues split away, cognates emerge, place names fossilise older forms, and scholars can reconstruct the proto-language.
- **Grammar Matters** — word order, isolating to polysynthetic morphology, cases, genders, evidentiality and honorific levels decide how hard translation is and how likely a treaty clause is to be misread. Feared words give way to euphemisms.
- **Names with Meanings** — every name is built from real roots with a recorded meaning, epithets are coined from deeds, such as "the Silver-Handed", and every foreign tongue gives a place its own name.
- **Scripts That Evolve** — pictograms to logograms, syllabaries, abjads and alphabets, plus knots and notches, reformed, simplified and borrowed. Hard scripts keep literacy low and empower a scribe caste; an alphabet breaks their monopoly.
- **Decipher the Dead** — bilingual stones, living cousin languages and patient scholars unlock lost scripts over seasons. Partial readings give partial knowledge, and mistranslations live on as theories and legends.
- **Barriers and Bridges** — every treaty, sale, sermon and battle order passes through intelligibility. Interpreters bridge the gap, lingua francas ride the trade routes, pidgins become creoles, sign languages grow among the deaf and the tongueless, and thieves keep their cant.
- **Tongues of Power** — a conquered people with a great literature can conquer its conquerors. Realms ban and revive languages, scent and telepathic tongues follow their own rules, and each son has a sacred tongue whose words are rites.

**In your world:** A cruel law cut out the tongues of heretics. So many went mute that their village grew its own sign language, and the heresy went on spreading in a tongue its judges could not understand.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/27-the-rewritten-past.jpg"><img src="common/assets/images/dlc-covers/27-the-rewritten-past.jpg" width="220" alt="The Rewritten Past box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/27-the-rewritten-past.jpg"><img src="common/assets/images/dlc-backs/27-the-rewritten-past.jpg" width="220" alt="The Rewritten Past box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 27. The Rewritten Past

*History is written by the victors. Until someone finds the old stone.*

The new dynasty's chronicle says its founder was born of a god. The folk songs of the valley say he was a stable boy who poisoned his master. A merchant's account from across the sea says both are wrong. Here every event has one truth and many tellings, and you alone can lay them side by side.

- **Accounts and Truth** — official chronicles, folk memories, foreign accounts, gospels, heroic poems and inscriptions each glorify, vilify or omit, on stone, in books or in song, and each is measured against what truly happened.
- **Damnatio Memoriae** — strike a name from the records, deface every inscription, smash every statue. The figure fades within a few generations, unless folk memory or a foreign chronicle keeps the name alive.
- **Revisionism** — new rulers rewrite the chronicle to suit their claim. Older texts survive, and the scholar who finds one holds a dangerous secret: the true history.
- **Founding Myths** — every people and every realm has its founding story. Belief in it holds the people together and the throne up, and a single inscription that contradicts it costs both.
- **Lost Lands** — memories of old borders breed claims and movements centuries later, the hidden root of many wars.
- **Days of Remembrance** — victories, massacres and foundings are relived on every anniversary through traditions and gatherings, keeping pride and grievance alive. Neglect them and the memory fades.

**In your world:** A usurper's chronicle gave him divine descent. Generations later a ploughman turned up an inscription naming his true father, a scholar made the scandal public, the dynasty's legitimacy cracked, and the old border it had once surrendered became the rallying cry for a new war.

</td>
</tr>
</table>
</details>

<a id="chapter-iv"></a>

### ⚒ IV. Economy and City

<details open>
<summary><b>Expansions 28–35</b> · <sub>8 expansions</sub></summary>

<table>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/28-forge-and-furnace.jpg"><img src="common/assets/images/dlc-covers/28-forge-and-furnace.jpg" width="220" alt="Forge and Furnace box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/28-forge-and-furnace.jpg"><img src="common/assets/images/dlc-backs/28-forge-and-furnace.jpg" width="220" alt="Forge and Furnace box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 28. Forge and Furnace

*No forests, no charcoal. No charcoal, no iron. No iron, no army.*

You watch a war being lost in a forest. The woodcutters clear the last hills, the bloomeries go cold for want of charcoal, the smiths stop forging blades, and the army marches out half armed. Every spear in your world has a supply chain, and every chain has a weak link that reaches somewhere you never expected: a blockade on iron arrives at the farm as a broken plough.

- **Materials with Real Physics** — hardness, edge, weight, decay, sanctity and corruption for everything from flint to dragonbone, star metal from fallen comets and godflesh from dead gods. Each world adds exotic substances of its own, forged from a god's blood or a dead star's core.
- **Sixteen Commodities in Four Families** — subsistence, industrial, strategic, and luxury and sacred, from grain and fodder to siege materiel, incense and magical reagents. People eat per head, and what a town can store depends on the granaries it has built.
- **Many Ways to Make a Thing** — up to six methods per good. Iron comes from a charcoal bloomery, a coal blast furnace or a divine forge. A culture that reveres nature refuses the dirty method, and early adopters put the old artisans out of work.
- **Seven Grades of Quality** — poor to masterwork to artifact, set by skill, method and material. Fine meals and fine clothes lift moods and are what nobles demand, while meat, fish and milk rot unless salted, smoked, iced or kept by magic.
- **Rivers Industrialise First** — muscle, water, wind, heat, magic and divine rites power production, so geography decides where industry rises. On frozen worlds heat is survival, and a fuel shortage means whole communities dying of cold.
- **Chains That Break Upstream** — ore to metal to weapons, hide to leather to armour, grain to flour to bread. Deep mines cave in, sometimes breaking into caverns full of beasts, and scarce iron or horses become war aims.
- **Smoke, Slag and Purple Dye** — smelting, tanning and dyeing foul the air, water and soil, raising disease and emptying fisheries until blight follows. Chemistry adds shellfish dyes, soap, fertiliser and explosives, each with its own hazards.

**In your world:** A river town took up the coal blast furnace. Its cheap iron ruined every bloomery upriver, the idle smiths swelled the radical factions, the river turned foul and the fish failed, and the nature-revering villages downstream turned against the town that armed the realm.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/29-coin-of-the-realm.jpg"><img src="common/assets/images/dlc-covers/29-coin-of-the-realm.jpg" width="220" alt="Coin of the Realm box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/29-coin-of-the-realm.jpg"><img src="common/assets/images/dlc-backs/29-coin-of-the-realm.jpg" width="220" alt="Coin of the Realm box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 29. Coin of the Realm

*Debase the coin, fill the treasury, and watch the merchants walk away.*

A dragon's hoard comes home in triumph, and soon the luxury markets are drowning in silver and its prices tumble. You are watching a real economy. Every market town posts prices for sixteen goods, every coin carries its purity and the trust behind it, and bankers lend to warlords at rates set by their record. Nobody scripted the boom. Greedy merchants guessed, hoarded, and were ruined.

- **Prices That Breathe** — every market holds prices for all sixteen commodities, moved by stocks, consumption, distance, danger and tariffs. Bread barely bends with price, luxuries swing hard, and goods flow down every route from cheap to dear.
- **Coin with a Conscience** — each currency has a metal, a purity and a measure of trust. Debase it and the treasury fills today, then inflation bites, merchants sour and trade in that coin dries up. Reserves of gold and silver shore it up.
- **Bankers and Bankruptcy** — merchant guilds lend war loans at interest set by the borrower's credit. A realm slides from strained to default to restructuring, and an unpaid debt can become a war over the default itself.
- **Booms Nobody Planned** — greedy merchants buy what they believe will rise and hoard grain through famine. The price spikes stoke unrest, the bust ruins the speculators, and cycles emerge from behaviour rather than script.
- **Tariffs, Embargoes and Black Markets** — tariffs protect producers whose owners lobby for them, embargoes cut trade by decree, and smuggling swells with the price gap. Drugs, void materials and forbidden books move through smugglers at a premium.
- **Insurance and Its Temptations** — guilds, banks and mutual societies insure cargoes, houses and lives at premiums set by what they believe. Insured merchants take riskier roads, and one great loss can bring an insurer down and the banks with it.
- **Hoards, Changers and Bills of Exchange** — secure households invest, insecure ones bury coin that is lost when they die and found by later diggers. Money changers profit on rates that follow purity and trust, and bills of exchange carry credit without carrying coin.

**In your world:** A king debased his silver to pay for a war. Foreign changers marked his coin down, his own merchants stopped trading in it, the war loan fell due in good silver he no longer had, and the default became a war of its own.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/30-the-salt-road.jpg"><img src="common/assets/images/dlc-covers/30-the-salt-road.jpg" width="220" alt="The Salt Road box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/30-the-salt-road.jpg"><img src="common/assets/images/dlc-backs/30-the-salt-road.jpg" width="220" alt="The Salt Road box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 30. The Salt Road

*Goods, gods and plagues travel the same roads.*

Two markets trade long enough and a road is born, with a name, a toll and a reputation. You follow a caravan through a mountain pass: mules and wagons, salt and silk, a pilgrim, a missionary and a wool merchant carrying a fever nobody has noticed yet. At the far end it unloads goods, news, songs and plague. Whoever holds the pass takes the toll, and whoever loses it starts a war.

- **Roads That Name Themselves** — steady trade between two markets carves a named route by road, river, sea, caravan or sky. Bridges, harbours and caravanserais raise its capacity, neglect lets it fade, and a famous road becomes a legend.
- **Caravans and Convoys** — every route is carried by real caravans with owners, cargo, animals, guards and passengers. Bandits, beasts and enemy armies raid them, storms sink them, and a merchant house's ageing fleet is a strategic asset.
- **The Right Way to Carry It** — perishables need speed, salt, ice or magic. Livestock walks and grazes on the way. Grain, stone and timber go by water wherever they can, so rivers and seas rule bulk trade.
- **Tolls, Chokepoints and Blockades** — whoever holds the chokepoints sets the tolls, and high tolls send traffic round another way. Fleets and armies at a pass choke the flow, and merchant factions push for peace when their routes bleed.
- **Ports, Warehouses and Cornered Markets** — berths, cranes and depth limit a harbour. A house with full warehouses can corner a commodity or dump goods into a rival's market, until guild monopolies and laws against forestalling stop it.
- **Trading Posts and Whole Chains** — merchant houses plant trading posts in foreign cities by treaty or charter, gaining market access, informants and a diaspora. They buy every step from mine to market, and put spinning out to rural cottages before factories exist.
- **Amphorae and Pleasure Seekers** — goods travel in amphorae, barrels, sacks and sealed jars, and potters' stamps survive for later diggers to read. The wealthy tour wonders, baths and old battlefields, spending at inns and spreading fame and disease.

**In your world:** When a rival realm seized the pass and raised its tolls, the caravans swung south through bandit country. The insurers raised their premiums, the losses mounted, and the merchant guild that had paid for the last war began paying for the next.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/31-yoke-and-wage.jpg"><img src="common/assets/images/dlc-covers/31-yoke-and-wage.jpg" width="220" alt="Yoke and Wage box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/31-yoke-and-wage.jpg"><img src="common/assets/images/dlc-backs/31-yoke-and-wage.jpg" width="220" alt="Yoke and Wage box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 31. Yoke and Wage

*Who works the fields? Who owns them? Who is free?*

A water-frame mill opens on the river, and a street of hand-loom weavers is out of work by winter. Some steal, some emigrate, some sign on with the levy, and some join the radicals in the tavern. Now labour has a price and sometimes a chain: every job pays a wage, every class has a basket of needs it meets or fails, and every war can fill a slave market.

- **Wages and the Cost of Living** — every job at a farm, mill, army or office pays a share of the workplace's takings. Set against local prices for a class's needs, it becomes a standard of living that drives migration, loyalty, fertility and radicalism.
- **Four Tiers of Need** — subsistence, basic, comfort and luxury, from bread, fuel and salt to festivals, temple access, art and fine goods. Meet a tier long enough and part of a class rises. Fail a lower one and it falls.
- **Farmers to Artisans to Merchants** — promotion climbs the ladder, or turns into the clergy and the scholars through education, within the realm's law on mobility. Demotion runs down to the outcasts or into serfdom by debt, while a war hero is ennobled and founds a house.
- **The Idle Hands** — new methods and too many workers make the unemployed, who swell crime, emigration, the levy and the radical factions. Winter idleness on the farms fills the season with crafts, festivals and banditry.
- **Satisfaction at Work** — a content class works harder, and a resentful warrior class deserts. Inequality breeds crime and revolt, though cultures that prize hierarchy tolerate far more of it.
- **Corvée and the Unpayable Debt** — realms levy days of labour for walls, roads and wonders at the cost of harvests and goodwill, and folk tales remember the wonders built in suffering. Indenture binds debtors to terms some employers make impossible to finish.
- **Slave Markets and Manumission** — where law allows it, captives, debtors and the condemned are sold by skill, age and origin, so slaving economies grow hungry for war. Freedom comes by purchase, a master's will, service, abolition or revolt.

**In your world:** A border war filled the slave market with captives. The mines that bought them undercut the free miners, who lost their wages and drifted into the abolitionist movement, and when the slaves rose, the movement already had its organisers.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/32-walls-and-wards.jpg"><img src="common/assets/images/dlc-covers/32-walls-and-wards.jpg" width="220" alt="Walls and Wards box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/32-walls-and-wards.jpg"><img src="common/assets/images/dlc-backs/32-walls-and-wards.jpg" width="220" alt="Walls and Wards box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 32. Walls and Wards

*Every city grows its own way. Every city burns its own way.*

On a dry, windy night a spark lands in a timber quarter with no fire brigade. By morning the old town is ash. Now the city must choose what rises: a planned grid of stone and wide streets, if the treasury and a planner allow it, or the same crooked wooden lanes that will burn again. Meanwhile, quietly, the elites are claiming the burned land.

- **Ten Kinds of District** — farmland, markets, craft quarters, temple quarters, harbours, citadels, slums, palaces, foreign quarters and necropolises, unlocked as a hamlet grows through village, town and city to metropolis. No city rises without water and a granary.
- **Rents and the Pushed-Out Poor** — temples, fountains and parks raise land value, while tanneries, prisons, crime and haunted memories lower it. Rents sort the classes street by street, and rising value pushes the poor outward.
- **Services by Reach** — wells, watch posts, healers, schools and bathhouses cover the streets around them. Beyond their reach come thirst, crime, disease, impiety and illiteracy, and a mine too far from any housing cannot find its workers.
- **Houses That Grow** — when services and goods arrive, huts become cottages, houses, townhouses and manors. When they fail, the houses sink. Slums spread wherever migrants outrun housing, feeding fever, crime and the mob.
- **Grids, Rings and Old Quarters** — a city grows organic, planned or in rings of walls, and that shape decides how fire spreads, how goods move and whether inner walls hold. In a long winter, rationing may mean abandoning the old and the sick.
- **Charity Against the Gutter** — almshouses, orphanages, foundling homes, leper houses and widows' houses take in the maimed and the abandoned, and their patrons gain piety. Without them, beggars fill the streets and children fill the gangs.
- **Ready for the Worst** — levees, firebreaks, seawalls, drills and stockpiles keep a disaster from becoming a catastrophe. Afterwards rival realms send aid that leaves debts of gratitude, and refusing a rival's help costs face.

**In your world:** A great fire gutted the timber harbour quarter. The city rebuilt it in stone on a grid, land values soared, and the dockworkers who could no longer pay the rents were pushed out to the slums beside the tanneries, where the next fever began.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/33-wonders-rising.jpg"><img src="common/assets/images/dlc-covers/33-wonders-rising.jpg" width="220" alt="Wonders Rising box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/33-wonders-rising.jpg"><img src="common/assets/images/dlc-backs/33-wonders-rising.jpg" width="220" alt="Wonders Rising box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 33. Wonders Rising

*Generations of labour. One wonder. One rival who finished first.*

The great dome was begun under a grandfather and is still open to the sky under his grandson. Masons die, plague takes the scribes, the treasury fails twice, and across the sea a rival realm is racing to finish first. Win, and the wonder feeds your city's prestige and draws travellers from every coast. Lose, and you salvage a share of the stone while a half-built ruin gathers legends.

- **More Than Forty Structure Kinds** — temples, libraries, observatories, citadels, banks, shipyards, aqueducts, canals, dams, arenas and tombs, each with a real function. Granaries feed sieges, hospitals cut deaths from wounds, and observatories soften the terror of an eclipse.
- **Nothing Works Without Hands** — every building needs staff and upkeep, and as its condition falls its function falls with it. When plague kills the scribes, the library still stands but its knowledge is locked away.
- **Mud Brick to Hydraulic Concrete** — ten building materials, each with its own strength, weathering, fire and water resistance. Concrete sets underwater for harbours, aqueducts and domes, and a civilisation that loses the technique cannot repair its old harbours.
- **The Wonder Race** — wonders and cosmic works are unique to a world or to the whole cosmos. Several realms build at once, the first to finish wins, and envy follows the losers into every embassy.
- **Megastructures** — star cages that harvest a sun's essence and dim it to the fury of sun cults, orbital rings, world-bridges, void lighthouses for safe passage, and planetary engines that move a world's orbit.
- **Museums and Gardens** — royal collections draw scholars and tourists, become prizes in every sack and return home as a clause of peace. Physic gardens supply healers, hunting parks shelter game, and sacred groves draw the gods of nature.
- **Lifting Water** — shadufs, waterwheels, screws, chain pumps and later steam pumps raise water to the terraces and drain the deep mines. Without pumps, a mine floods the day it strikes the aquifer.

**In your world:** Two realms raced to finish the world's one great wonder. The loser salvaged a sliver of its stone and nursed its envy for generations, while the winner dedicated the wonder to its storm god, whose fame grew with every traveller who came to see it.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/34-heirlooms-and-relics.jpg"><img src="common/assets/images/dlc-covers/34-heirlooms-and-relics.jpg" width="220" alt="Heirlooms and Relics box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/34-heirlooms-and-relics.jpg"><img src="common/assets/images/dlc-backs/34-heirlooms-and-relics.jpg" width="220" alt="Heirlooms and Relics box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 34. Heirlooms and Relics

*The sword that killed three kings. The crown that made the fourth.*

Pick up any named sword in your world and read its life: who forged it, which house carried it, the battles it won, the night it was stolen, the barrow it was buried in. Kill enough with it and it becomes a symbol armies follow. Lose a crown and the king's legitimacy bleeds away until a new crown earns a name of its own.

- **Provenance** — every crafted item bears a maker's mark and a history of owners and deeds: kills, battles, coronations, thefts and burials. Renown grows with each, and a famous enough object becomes a symbol whose capture is a war aim.
- **Decorations That Remember** — studded, inlaid, engraved, runed or bristling with menacing spikes. Engraved images depict real events, so a shield showing the victory at Varn keeps that battle alive in the culture.
- **Artifacts of Obsession** — born when a crafter falls into a fever of creation, artifacts carry a unique name, the highest quality and often an enchantment. Greedy nobles demand them, and thieves and questing heroes plan around them.
- **Regalia** — crowns, sceptres, seals, rings and standards. Hold the realm's regalia and legitimacy follows. Usurpers hunt the crown, and losing it is a humiliation the whole realm feels.
- **Relics and Curses** — saints' bones and fragments of dead gods heal by chance, draw pilgrims and invite relic raids. Cursed blades breed bloodthirst, betrayal, wasting, madness or misfortune in whoever carries them.
- **Lenses and Clocks** — spectacles restore sight lost to age and lengthen scholars' careers, and telescopes predict eclipses. Public clocks discipline labour, synchronise armies and let ships fix their place at sea.
- **Locks, Vaults and Rotting Archives** — thieves pit their skill against locksmiths, seals and guards. Papyrus rots in wet lands while clay survives fire and is baked hard by it, so what history remembers depends on what it was written on.

**In your world:** A usurper took the throne but not the crown, which loyalists smuggled to a mountain monastery. His legitimacy never recovered, the crown's return became the rebels' war aim, and the abbot who hid it entered its provenance beside four kings.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/35-underworld.jpg"><img src="common/assets/images/dlc-covers/35-underworld.jpg" width="220" alt="Underworld box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/35-underworld.jpg"><img src="common/assets/images/dlc-backs/35-underworld.jpg" width="220" alt="Underworld box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 35. Underworld

*Every city has two masters. Only one of them has a crown.*

The watch captain drinks free at the tavern by the docks, and everyone knows why. Beneath every crowned city runs a second government with ranks, income and a code of silence sworn like an oath. It collects protection street by street, owns a magistrate or two, and settles its borders in blood. You can let the realm crush it, hire it, or leave it running the harbour.

- **Four Kinds of Family** — crime families, thieves' guilds, smuggling rings and pirate brotherhoods, each with its own ladder of ranks and its own treasury.
- **Six Rackets** — protection, smuggling, gambling, fencing, kidnapping and counterfeiting, each with its own income and its own victims.
- **Turf Wars** — families hold the city district by district. When they fight over a street, the maimings, killings and collapsing order are felt by everyone who lives there.
- **Officials on the Payroll** — bribes buy the watch, and hooks built from secrets and debts buy the magistrate. A judge with a hidden debt rules the way he is told.
- **The Code of Silence** — membership is sworn like an oath, and the family punishes its traitors. An informer has to fear his brothers more than the gallows.
- **Crush or Co-opt** — realms send thief-takers, the watch and purges, or turn the families into informants and license the pirates as privateers.
- **Outlaws and Bounties** — an outlaw loses the law's protection, so anyone may rob or kill them without crime. Bounties draw hunters for coin, while an outlaw who spares the poor may become their folk hero.

**In your world:** A smuggling ring bought the harbour master through his gambling debts. When the queen outlawed its captain and posted a bounty, the dock wards hid him, the thief-takers came back empty-handed, and his legend grew in every street he had spared.

</td>
</tr>
</table>
</details>

<a id="chapter-v"></a>

### 👑 V. Power and Politics

<details open>
<summary><b>Expansions 36–47</b> · <sub>12 expansions</sub></summary>

<table>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/36-throne-and-council.jpg"><img src="common/assets/images/dlc-covers/36-throne-and-council.jpg" width="220" alt="Throne and Council box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/36-throne-and-council.jpg"><img src="common/assets/images/dlc-backs/36-throne-and-council.jpg" width="220" alt="Throne and Council box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 36. Throne and Council

*Wear the crown. Fear the council. Name your heir.*

The old king dies in the night and the succession law names his nine-year-old grandson. By dawn you are watching a regent weigh ambition against oath, a marshal count his troops, and a cousin with a better claim count the nobles who would back her. Every realm in your world is a working state, with offices, a treasury, a law of succession and a legitimacy that can drain away.

- **Ten Kinds of Government** — chiefdoms, monarchies, theocracies, merchant oligarchies, republics, tribal confederations, empires, hive councils, military occupations and god-kingdoms ruled directly by a son. Each decides by its own rule: the ruler's will, a council vote, an assembly or a god's.
- **A Council with Work to Do** — chancellor, marshal, steward, spymaster, court chaplain and high judge each take a task every epoch, from training troops to purging corruption. Their skill sets the result, their loyalty sets their diligence, and a disloyal spymaster leaks.
- **Legitimacy and the Line** — lawful succession, a sound body where the culture demands one, honour, the church's blessing, victories, prosperity and age. A child heir brings a regency, rival claimants weigh their backing, and a preview shows who rules if the king dies tonight.
- **The Realm Outgrows Its Scribes** — administration is literacy, scribes, writing and roads. Expand past it and governors drift, taxes leak and provinces dream of secession, while peoples outside the ruling culture grow their own separatist movements.
- **Six Taxes and the Leak** — land, poll, trade, consumption, tithe and tribute, each falling on different classes. Tax farming raises the take and the corruption with it, and greedy officials skim until a just high judge audits them.
- **Mandates, Demands and Policy Webs** — rulers ban exports, open the granaries or impose curfews, and nobles demand fine dwellings and offices. Every policy touches several classes at once, so one reform can win the merchants and lose the clergy.
- **Court and Constitution** — a court of resident courtiers and grandeur from feasts, art and fine goods draws talent and impresses envoys. The constitution that defines it all changes only by a high threshold, or by revolution.

**In your world:** A queen sold the right to collect her taxes to pay for a war. Revenue rose, corruption followed, the provinces' approval collapsed, and when she died the governor of the richest province crowned himself instead of kneeling to her son.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/37-patrons-and-puppets.jpg"><img src="common/assets/images/dlc-covers/37-patrons-and-puppets.jpg" width="220" alt="Patrons and Puppets box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/37-patrons-and-puppets.jpg"><img src="common/assets/images/dlc-backs/37-patrons-and-puppets.jpg" width="220" alt="Patrons and Puppets box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 37. Patrons and Puppets

*The throne is held by whoever the throne must keep happy.*

Ask who really chose the emperor. Not the people: the guard captains, the great landholders and a handful of priests. Keep them rich and you rule. Neglect them and a general with his own army and his own clients starts to wonder. Your world works out the circle that keeps every ruler in power, and that circle decides whether the treasury builds roads or buys loyalty.

- **The Winning Coalition** — every realm knows who has a say in choosing the ruler and whose support keeps him there. Small circles are bought with gifts and offices, large ones demand roads and granaries, and a ruler expecting a short reign plunders while a secure one invests.
- **Three Kinds of Legitimacy** — traditional breaks with the succession, charismatic dies with defeat and death, and legal-rational rots with corruption. When a charismatic founder dies, the realm must turn charisma into a dynasty or an institution, or split.
- **Patrons, Clients and Bought Offices** — favours and protection bind households and lesser nobles to the powerful wherever institutions are weak. Offices are sold, buyers recoup the price, sinecures reward the loyal, and new offices absorb restless elites at a cost.
- **Overmighty Subjects** — governors and generals build power bases of holdings, client commanders, wealth and popularity. Rulers rotate commands, split armies, raise parallel guards and keep hostages, buying safety at the price of military quality.
- **Five Ways to Share the Harvest** — markets, palace and temple stores that ration by office, command economies, manors and gift economies. Sack the centre of a palace economy and the whole economy falls with it.
- **Citizens and Strangers** — citizens, subjects, resident foreigners, protected minorities and slaves hold different rights to property, office, arms and the vote. Passes and safe-conducts decide who travels, forged ones sell on the black market, and welfare decides who eats in famine.
- **The Licensed Fool** — jesters and satirists mock the ruler with a licence. Tolerated satire cools the mob, suppressed satire festers into grievance, and the fool may say what no councillor dares.

**In your world:** A general who had won three wars held more land than the crown. The nervous emperor rotated him to a distant frontier, split his legions and kept his son at court as a guest. The army lost its next battle, and the general marched home anyway.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/38-crowns-unclaimed.jpg"><img src="common/assets/images/dlc-covers/38-crowns-unclaimed.jpg" width="220" alt="Crowns Unclaimed box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/38-crowns-unclaimed.jpg"><img src="common/assets/images/dlc-backs/38-crowns-unclaimed.jpg" width="220" alt="Crowns Unclaimed box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 38. Crowns Unclaimed

*The kingdom fell three centuries ago. Its crown still waits.*

The old kingdom has had no king for three hundred years, but its title survives, dormant and claimable. A minor count holds two of its provinces and a thin claim through his grandmother. Gather enough of the old land and he can restore what was lost, and the legends of the vanished kings will stir around him. Every house in your world plays this long game.

- **Noble Houses** — prestige, heirlooms, seats, feuds, and bloodlines that run long-lived, giant-blooded, cursed or god-blooded. Houses marry for alliance and claim at the risk of inbreeding, and split into cadet branches that carry claims against the senior line.
- **Titles from County to Empire** — lordships, counties, duchies, kingdoms and empires, plus holy sees, guildmasterships and mercenary captaincies. Create one by holding most of its land, or usurp one by holding its capital and a majority of its territory.
- **Right Against Might** — land held long enough under another title drifts into it by right. The gap between the two maps is where claims and wars are born.
- **Claims, Unions and Partitions** — claims by inheritance, marriage, conquest, divine favour or forgery fade unless pressed. One ruler holding two crowns rules both realms, and partition laws split a kingdom among the heirs, generation after generation.
- **Arms Born of History** — every house, realm, title, army and guild bears arms drawn from its deeds, its founder's wounds, its totems and its patron god, differenced for cadet branches and quartered by marriage.
- **Brothers Against Cousins** — lineages nest within clans within tribes. Brothers fight cousins, both unite against outsiders, and the whole tribe unites against foreigners, which gives stateless peoples order without a ruler.
- **The Long Plan** — secret orders and houses steer marriages across generations toward divine blood, a seer's gift or a union of claims, until a love match or a barren marriage undoes a century of work.

**In your world:** Two brothers split their father's kingdom by partition law. Their grandsons fought over a border county and the elder line lost, but generations later its cadet branch married back into the younger, quartered both arms and pressed the old kingdom's dormant title.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/39-iron-code.jpg"><img src="common/assets/images/dlc-covers/39-iron-code.jpg" width="220" alt="The Iron Code box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/39-iron-code.jpg"><img src="common/assets/images/dlc-backs/39-iron-code.jpg" width="220" alt="The Iron Code box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 39. The Iron Code

*A law is only as strong as the hand that enforces it.*

A merchant lies dead in a fogbound alley. The sheriff has a frightened witness who owes the accused money, a wound only a curved blade could make, a forged letter and a trail going cold by the day. The verdict will follow the evidence, the advocate the family can afford and the law of the land, so an innocent man can hang and become a martyr.

- **Eight Areas of Law** — succession, property, fiscal, penal, military, social, public health and magic. Laws decide heirs, punishments, levies, who may be enslaved and whether magic is banned or licensed, and a law at odds with the culture loses its teeth.
- **Passing a Law** — proposals advance with the balance of supporters and opponents. Estates obstruct with their privileges, debates spill into riots or compromises, and a bill that stalls too long fails and shames its champion.
- **Five Legal Systems and Their Blends** — custom kept in the elders' memory, written codes, scripture, binding precedent and oracles. Under an oracle a god answers the court, and the son may answer truly, lie or stay silent.
- **Evidence Decides** — witnesses with failing memories or hidden loyalties, wounds by weapon, footprints in mud, poison signs, ledgers, alibis and the residue of rites. Evidence decays, so wrongful verdicts come from bad evidence and bias, never from dice.
- **Courts, Advocates and Precedent** — appeals climb from local to royal and religious courts. Skilled advocates win cases, so the rich get better justice, and under precedent each ruling binds the next, letting law drift without a single new statute.
- **Prisons, Pardons and Remaking** — prisons breed gangs, disease and new skills, and released convicts carry a stigma. Rulers pardon friends at a cost in corruption and declare amnesties after civil wars. Where magic meets a cruel penal code, sentences remake the convict's body.
- **Oaths Before the Gods** — fealty, vengeance, silence, pilgrimage and blood brotherhood, sworn under a divine witness. Break one and the god's wrath follows, keep it and oath gods grow stronger, and a geas laid at birth may forbid you ever to refuse hospitality.

**In your world:** A schemer's forged letter convicted an honest reeve of treason. His village remembered him as a martyr and its approval of the crown collapsed, and by the time an investigator proved the hand was false, the villagers had already joined the rebels.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/40-guilds-and-estates.jpg"><img src="common/assets/images/dlc-covers/40-guilds-and-estates.jpg" width="220" alt="Guilds and Estates box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/40-guilds-and-estates.jpg"><img src="common/assets/images/dlc-backs/40-guilds-and-estates.jpg" width="220" alt="Guilds and Estates box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 40. Guilds and Estates

*Every guild wants a monopoly. Every estate wants a privilege. Everyone wants the crown.*

The weavers' guild wants the new mills banned. The nobles want their tax exemption back. The merchants want peace with the realm that holds their route, and the warrior order wants war with it. Here factions act every epoch: they lobby, bribe, strike, riot, fund wars and plot coups, and the balance of their sway is the realm's true constitution.

- **Sixteen Kinds of Faction** — merchant and craft guilds, priesthoods, warrior orders, noble councils, peasant leagues, rebels, bandits, pirates, assassins, academies, secret societies, mercenary companies, wandering markets, void pirates and more, from a band of fifty to a network spanning worlds.
- **Goals and a Dozen Means** — lower taxes, a monopoly, a claimant on the throne, independence. To get there a faction lobbies, bribes, petitions, strikes, riots, stages a coup, assassinates, smuggles, raids, funds a war, recruits, or splits apart.
- **The Power Balance** — inside every realm the factions' sway forms a balance that feeds every decision the ruler takes. A guild monopoly sets prices and blocks rivals, and smuggling rises to meet it.
- **Estates and Privileges** — nobility, clergy, burghers, peasants and warriors bargain for tax exemptions, monopolies, council seats, the right to bear arms and immunity from the courts. Every grant buys loyalty and costs the crown revenue or power.
- **Parties and Movements** — abolition, independence, religious revival and land reform grow as mass movements with support in every class. Where assemblies exist they become parties. Where they do not, they become revolts.
- **Companies with Armies** — chartered companies hold shares, a monopoly abroad and mercenary armies. They can conquer, become a realm of their own or collapse onto their banks and shareholders, and unpaid mercenaries turn bandit or change sides mid-war.
- **Ranks, Secrets and the Pooled Purse** — guilds control apprenticeships, quality standards and secret techniques. Cooperatives, mutual societies and burial societies pool money for mills, boats, credit and funerals, and can grow into political movements.

**In your world:** When the water-frame mills arrived, the weavers' guild struck and the capital's cloth ran short. The crown bought peace with a guild monopoly, smugglers moved in to undercut it, and the mill owners began lobbying the council to tear up the guild's charter.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/41-pacts-and-perfidy.jpg"><img src="common/assets/images/dlc-covers/41-pacts-and-perfidy.jpg" width="220" alt="Pacts and Perfidy box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/41-pacts-and-perfidy.jpg"><img src="common/assets/images/dlc-backs/41-pacts-and-perfidy.jpg" width="220" alt="Pacts and Perfidy box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 41. Pacts and Perfidy

*Sign with one hand. Sharpen the knife with the other.*

Your envoy demands a border province, and a crisis opens. Two realms back you for promised shares of the spoils, three back your rival, and a fourth is courted by both. At every step either side can back down and lose only face. Or nobody blinks, and every backer marches. Here every treaty is a set of clauses the world enforces, and every broken promise is remembered.

- **Treaties Built from Clauses** — thirteen kinds, from tribute, cession and hostages to wergild, extradition and champion clauses. The world carries them out every epoch, guarantors join when they break, and a god who witnessed the oath punishes the breaker.
- **The Coalition Against You** — conquests, unjust wars and broken treaties raise alarm in every realm that hears of them. Past a point the neighbours band together with a standing call to arms, and only marriages and good relations slowly cool it.
- **Crises at the Brink** — a demand opens a crisis with a clock. Other realms back a side for clause shares and favours, swing parties are courted, and at each escalation someone can back down, concede or let it come to war.
- **Spheres and Subjects** — great powers hold clients in their spheres. Subjects come as vassals, tributaries, marches, personal unions, clients, colonies and protectorates, each with its own obligations, its own desire for liberty and a contract it can demand to renegotiate.
- **Bad Faith and Side Deals** — a deceitful ruler signs meaning to break, and the other side trusts only as far as it believes. At summits several parties bargain in rounds, cut secret side deals, and the order of commitments decides who wins.
- **Diplomacy Has Limits** — a realm sustains only as many alliances, guarantees and embassies as its administration and ambassadors can carry. Inside realms of many peoples, old grudges between them feed migration, assimilation and ethnic strife.
- **An Assembly of Worlds** — realms across worlds vote on shared route security, embargoes and bans on void rites, and may even sanction a son's world.

**In your world:** A king signed a marriage pact he never meant to honour, then seized the bride's dowry province. The witness god's priests denounced him, alarm spread to every court, and within a generation a coalition of his former friends had taken the province back.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/42-rise-and-ruin.jpg"><img src="common/assets/images/dlc-covers/42-rise-and-ruin.jpg" width="220" alt="Rise and Ruin box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/42-rise-and-ruin.jpg"><img src="common/assets/images/dlc-backs/42-rise-and-ruin.jpg" width="220" alt="Rise and Ruin box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 42. Rise and Ruin

*Empires rise at the frontier and die in the palace.*

Nothing in your world is scripted to fall. Yet watch a great empire across three centuries: land grows scarce, wages sink, younger sons with credentials and no offices crowd the capital, the treasury borrows to pay its soldiers, and on the frontier a hard people that has fought for generations is learning to ride as one. The cycle emerges from the simulation, and you can read every gauge of it.

- **The Stress Gauge** — popular misery, elite overproduction and fiscal distress multiply into one measure of political stress. As it climbs, factions form, coups and revolts grow likelier, and crowds tip into riot faster.
- **Counter-Elites** — when nobles, the rich and the credentialed outnumber the offices, titles and land to go round, the surplus becomes aspirants with nowhere to go. They lead the factions, movements and revolts.
- **Secular Cycles** — growth, stagflation, crisis, then depression or recovery, over centuries and with no script at all. Population falls, elites thin, wages rise, and the climb begins again.
- **Asabiyya** — solidarity rises on frontiers against peoples deeply unlike your own and decays through generations of luxury. It multiplies cohesion, morale and resistance to assimilation, so hard frontier peoples overthrow soft dynasties.
- **Challenge and Response** — disasters, plagues and invasions spur research, new institutions and solidarity. Too little challenge brings stagnation, too much brings collapse, and the severe but survivable middle forges the strongest peoples.
- **Long Plans** — realms, cults, orders and gods pursue goals across centuries: a desert world made green, a bloodline, a world converted, a wonder. Offices and orders carry them long after their authors are dust.
- **Psychohistory** — a scholarly order with statistics and a great archive forecasts a realm's future through a noisy lens and steers it with small interventions, until a great person or a god steps in and the forecast fails.

**In your world:** A nomad people hardened on the empire's frontier for four generations. When elite overproduction and an empty treasury split the capital into rival courts, the nomads rode in and founded a dynasty, and their great-grandchildren, grown soft in the palace, fell to the next frontier.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/43-couriers-and-ciphers.jpg"><img src="common/assets/images/dlc-covers/43-couriers-and-ciphers.jpg" width="220" alt="Couriers and Ciphers box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/43-couriers-and-ciphers.jpg"><img src="common/assets/images/dlc-backs/43-couriers-and-ciphers.jpg" width="220" alt="Couriers and Ciphers box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 43. Couriers and Ciphers

*The peace treaty arrived. The battle was already over.*

Your herald rides for the enemy camp with an offer of peace. The pass is closed by snow, so he takes the coast road, where a spy network copies his letter and bandits hold him for ransom. By the time he arrives, the armies have met. Now every decision is made on the latest news to arrive, and news travels at the speed of a horse.

- **Seven Ways to Send Word** — envoys, letters, heralds, signal fires, birds, magical sendings and dreams sent by a god. Delay follows distance, medium and season, mountain passes close in winter, and between worlds word travels as slowly as the route.
- **Intercepted** — every region along the way with spies, bandits or enemy armies is a chance to lose a letter. Stolen messages yield intelligence, hooks or forged replacements.
- **Forgery** — the forger's skill against the recipient's familiarity with the sender's hand. A forged declaration of war can set two innocent realms at each other's throats.
- **Lost in Translation** — misreadings grow with the language gap, the number of clauses and the interpreter's skill. A misread clause becomes a bitter breach dispute long after the ink has dried.
- **Envoys and Etiquette** — an envoy's skill and manners shape the welcome. A well-chosen gift earns opinion and a favour, a breach of precedence costs it, and killing an envoy is unthinkable almost everywhere and means war.
- **Ciphers and Codebreakers** — encipher your letters and an interceptor learns only that you wrote. Codebreakers grind at captured traffic for seasons, and while you do not know your cipher is broken, every message you send is read.
- **Beacons and Broadsheets** — fire beacons, mirror towers, post stations and sending stones shrink the realm until someone burns them. Criers, sermons, broadsheets and propaganda move public opinion, which sets support for wars, and censorship breeds distrust once discovered.

**In your world:** The empress's codebreakers broke the duke's cipher in the second winter of the rebellion. For a year they read every letter he sent, until a careless ambush betrayed what they knew, and the duke, hunting the leak, hanged his own loyal secretary.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/44-tongues-of-rumour.jpg"><img src="common/assets/images/dlc-covers/44-tongues-of-rumour.jpg" width="220" alt="Tongues of Rumour box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/44-tongues-of-rumour.jpg"><img src="common/assets/images/dlc-backs/44-tongues-of-rumour.jpg" width="220" alt="Tongues of Rumour box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 44. Tongues of Rumour

*A hero in one city. A butcher in the next.*

You sack a rebel town. In your capital you are the hero who crushed treason. In the victims' valley you are a butcher, and the story grows worse with every telling as it travels the pilgrim road. Every community in your world keeps its own ledger of every famous name, built from what it saw, what it heard and how its gossips chose to spin it.

- **Rumours That Travel** — news rides trade routes, pilgrimages, journeys and spy networks, losing fidelity with distance and language. A town that hears of an approaching army raises its walls, and rumours that refuse to die harden into legends.
- **Gossip Networks** — inside a city, stories move from friend to friend, through circles and gatherings. Each teller can spin the tale toward their own opinion of its subject, so the palace and the docks hear different scandals.
- **Nine Axes of Reputation** — heroism, honour, cruelty, piety, generosity, wisdom, trickery, craft renown and troublemaking, held separately by every community and read through its own ethics. A massacre is cruelty to the victims' kin and heroism at home.
- **Prestige, Piety, Dread and Tyranny** — rulers spend their reputation. Prestige buys acceptance of laws, piety buys the clergy, and dread silences dissent for a while. Tyranny piles up from unjust acts and turns vassals against the crown.
- **Secrets for Sale** — factions, cults, scholars and even beasts prize particular knowledge: true names, lost techniques, hidden sites, prophecies. A secret buys favours and goods, but every sale makes it worth less.
- **False Heroes** — deeds must be credited. A vain rival can claim your dragon until the true slayer produces the beast's tongue, and exposure brings scandal, a duel or punishment. Yet the chronicle may still honour the impostor.

**In your world:** A sellsword claimed the wyrm a shepherd girl had killed. The capital feasted him while her village knew the truth, and when she walked into court with the beast's tongue in a cloth, the duel that followed made her a legend.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/45-velvet-daggers.jpg"><img src="common/assets/images/dlc-covers/45-velvet-daggers.jpg" width="220" alt="Velvet Daggers box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/45-velvet-daggers.jpg"><img src="common/assets/images/dlc-backs/45-velvet-daggers.jpg" width="220" alt="Velvet Daggers box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 45. Velvet Daggers

*Everyone has a secret. You only need the right one.*

The chancellor's son is not the chancellor's son. His wife's maid knows it, a rival's spymaster has just learned it, and nobody else knows yet. That single secret is a hook strong enough to force a vote, a marriage or a resignation, or, spent in public, to ruin a family. Here schemes are recruited, prepared and launched like campaigns, and every one of them can be discovered.

- **Thirteen Kinds of Secret** — affairs, bastards, murders, heresies, hidden cults, debts, crimes, cowardice in battle, hidden illness or madness, false identities, pacts with outer beings, true parentage and broken oaths. Each one is born of something that really happened.
- **Hooks and Favours** — a hook from a secret, a debt, a favour or a hostage forces compliance. Weak hooks are spent on use, strong ones last. Favours are owed for rescues and votes, and refusing a called favour costs honour.
- **Living Under Other Names** — spies, vampires, exiles and impostors wear false identities, exposed by investigations, careless slips or a face someone recognises.
- **Fourteen Schemes in Three Phases** — murder, abduction, seduction, framing, a fabricated claim, a stolen relic, a sabotaged wedding, a freed prisoner and more. Recruit agents with money, hooks or a cause, gather power, then strike past the target's spymaster and bodyguards.
- **Discovery** — every epoch a scheme's secrecy is tested against the counter-intelligence of the target's court. A discovered plot exposes its agents and leaves memories that last.
- **Timing Is Everything** — night and fog raise success and hide witnesses, storms cut pursuit, festival crowds give cover but more eyes, and a plague panic distracts the watch. Plots cluster on festival nights and foggy mornings.
- **Sabotage of Nature** — release pests, burn fields, poison a fishery, divert a river by stealth, salt the earth at night. The damage runs through the real ecology, and most victims find the very idea unthinkable.

**In your world:** A rival's agents salted the duke's best fields on a foggy night. The harvest failed and his levies went hungry, and when footprints and a dropped sack led an investigator back to them, the scandal cost their mistress her place at court.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/46-shadow-networks.jpg"><img src="common/assets/images/dlc-covers/46-shadow-networks.jpg" width="220" alt="Shadow Networks box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/46-shadow-networks.jpg"><img src="common/assets/images/dlc-backs/46-shadow-networks.jpg" width="220" alt="Shadow Networks box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 46. Shadow Networks

*Trust no one. Especially the one who found the mole.*

Your spymaster swears there is a traitor on the council. He is right, but he names the wrong man. The loyal treasurer hangs, and that night the real mole sends word across the border. Here spy networks are built cell by cell, agents are bought with greed, faith, blackmail or vanity, and paranoia can do more damage than any enemy.

- **Networks of Cells** — agents, handlers, dead drops and safe houses, with covers as merchants, priests or envoys. A captured agent can betray only their own cell, and flat networks are fast but fragile.
- **Four Motives** — money, ideology, compromise and ego. The motive sets loyalty and the risk of a double cross, and true believers are the most reliable agents and the hardest to turn back.
- **Seven Operations** — steal knowledge, sabotage, assassinate, incite, gather intelligence, blackmail and counterfeit. Spies fire granaries, weaken walls, poison wells, plant claimants and flood the market with false coin.
- **Mole Hunts** — paranoid spymasters accuse the innocent, and every purge costs loyal officers and drives defections, which only deepens the paranoia.
- **Defectors and Double Agents** — captured agents can be turned to feed false intelligence, or exchanged. Defectors carry their secrets across the line and need protection, branded traitors at home and hailed as heroes abroad.
- **Death by Design** — blade, poison, staged accident, deliberate infection or curse. Whether anyone recognises a murder depends on the physician's skill and the medicine of the age, and that decides whether a vendetta, an inquiry or a war follows.
- **Spies of the Gods** — scrying rites, dream intrusions and servitor spies cross any distance. Wards and the dominion of a rival god block them.

**In your world:** An ideological agent poisoned the margrave and dressed it as a fever. The court physician, schooled in a newer medicine, read the signs, the poisoner's cell was taken, and the margrave's heir declared the war his father had refused to fight.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/47-fog-of-belief.jpg"><img src="common/assets/images/dlc-covers/47-fog-of-belief.jpg" width="220" alt="Fog of Belief box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/47-fog-of-belief.jpg"><img src="common/assets/images/dlc-backs/47-fog-of-belief.jpg" width="220" alt="Fog of Belief box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 47. Fog of Belief

*They don't act on the truth. They act on what they believe.*

A general force-marches his army to break the siege of a city that was relieved a month ago. He is no fool: his last report said the walls were still holding. Every ruler, house, cult, commander and beast in your world decides on what it believes, with a confidence and a date attached, while the outcome is settled by the truth. Surprise, folly and genius live in the gap.

- **A Mind of Its Own Making** — every deciding actor keeps its own store of beliefs: an enemy army's size, a rival's treasury, a claimant's health, a god's favour. Each belief carries a confidence, a date and a source.
- **Six Ways of Knowing** — seeing with one's own eyes, letters, rumours, spies, scouts and one's own records, and records exist only where someone can write.
- **Knowledge Fades** — confidence decays with age, and stale beliefs make fatal decisions. The rival you believe is bankrupt may have been paid with a dragon's hoard last spring.
- **Deception** — feints, false campfires, planted rumours and forged letters write lies straight into a rival's picture of the world.
- **Markets in the Fog** — merchants trade on the price gaps they believe in, so prices converge where news is quick and stay apart where it is slow. Insurers price risk on belief, and speculators hoard on it.
- **The Gap Laid Bare** — toggle any realm between what it believes and what is true. As the Creator you can reveal the truth to an actor or plant a false belief, and the agents who play your mortals see only what their characters know.

**In your world:** A king believed his rival's treasury empty because his last spy report was years old. He declared war, met an army paid from a fresh dragon hoard, and lost a province to an enemy he had been certain could not afford to fight.

</td>
</tr>
</table>
</details>

<a id="chapter-vi"></a>

### ⚔ VI. War

<details open>
<summary><b>Expansions 48–54</b> · <sub>7 expansions</sub></summary>

<table>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/48-steel-and-banner.jpg"><img src="common/assets/images/dlc-covers/48-steel-and-banner.jpg" width="220" alt="Steel and Banner box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/48-steel-and-banner.jpg"><img src="common/assets/images/dlc-backs/48-steel-and-banner.jpg" width="220" alt="Steel and Banner box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 48. Steel and Banner

*An army is not a number. It is ten thousand people who must eat.*

You do not conjure soldiers. You take them. Young farmers leave the levy class, spears leave the armoury, grain leaves the granary, and the harvest season halves the call. Then the march begins, and every frozen pass, every fevered camp and every empty war chest costs men. Each stack carries its own gear, drill, morale and memory, and when the war ends your people count who came home whole.

- **Thirty-Three Kinds of Soldier** — eight families, from levies, pikemen and berserkers to horse archers, chariots, sky mounts, war mages, necromancers, golems and ghost hosts. Each has its own melee, missile, defence, charge mass, upkeep and favoured ground.
- **Armour from the Armoury** — every stack is equipped from the weapons and armour your people forged before the war, from hide to plate to enchanted mail. Levies go home when the army disbands, minus the dead, and the maimed come home maimed.
- **Hunger Before Battle** — each region can feed only so many mouths. Armies above the limit strip the land and earn its hatred, and a winter campaign through the mountains in heavy armour can destroy an army without a single battle.
- **Strength, Organisation, Discipline** — three separate pools in every stack. A stack whose formation dissolves routs at full strength, drilled professionals hold where levies break, and news of a sacked home city raises rage and desertion at once.
- **Commanders Earn Their Names** — skill in fire, shock, manoeuvre, siege and logistics, and ten battle traits earned from the record, from cavalry master and winter campaigner to reckless and brutal. Their traits steer the tactics they choose.
- **Blueprints and Earthworks** — named formations such as the border legion or the steppe horde, war machines built to blueprints a rival can steal, and sappers who bridge rivers with pontoons and dig earthworks that outlive the war.
- **Regiments and Veterans** — units from one recruiting ground earn names, nicknames and battle honours on their standards, and remember their massacres. Veterans receive land in new colonies or pensions, and their associations may back an old commander's coup.

**In your world:** A marshal marched heavy infantry over the passes in midwinter. Cold and camp fever took more men than the enemy ever did. The survivors were settled in a veteran colony, and a generation later they marched again, behind their old general, on the capital.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/49-field-of-glory.jpg"><img src="common/assets/images/dlc-covers/49-field-of-glory.jpg" width="220" alt="Field of Glory box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/49-field-of-glory.jpg"><img src="common/assets/images/dlc-backs/49-field-of-glory.jpg" width="220" alt="Field of Glory box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 49. Field of Glory

*Three hundred at the pass. Thirty thousand on the plain.*

Dawn fog lies on the ford. Your archers cannot see, the enemy's hidden horse waits in the reeds, and your commander, reckless by record, wants to charge. Every battle is fought in phases on real ground under the real sky of that season, and every phase leaves a reason you can read: the terrain, the tactic, the counter, the line that held and the line that broke.

- **Eight Phases of Battle** — scouting, the commanders' plans, missiles, the charge, melee, rites and miracles, pursuit and aftermath. A patron god may intervene, and its attention can draw a rival god in. Six outcomes run from decisive victory through pyrrhic victory to massacre.
- **Twelve Grounds, Eight Skies** — a pass multiplies the defender, marsh drags heavy troops down, streets swallow cavalry. Fog blinds archers and doubles ambushes, an eclipse breaks armies whose people dread it, and a magic storm swells every rite and its backlash.
- **Thirteen Tactics and Their Counters** — shield wall, wedge, feigned retreat, double envelopment, night raid and more, each with its answer and its proper ground. Feints pin reserves, false campfires inflate an army and planted deserters carry lies.
- **The Width of the Field** — only so many can fight at once. At a narrow pass three hundred hold thirty thousand for a time, reserves wait for the front to tire, and squares stop cavalry but die under arrows.
- **The Morale Ladder** — steady, shaken, wavering, routing, broken. Panic spreads between neighbouring stacks, standards and priests rally the wavering, orders arrive late or garbled across a language barrier, and a fallen general collapses the whole command.
- **The Physics of Slaughter** — in melee only the front rank kills, but massed arrows and spells strike the whole enemy, so concentration pays quadratically. Plate, chitin and stone skin shrug off blows that cannot pierce, which is why crossbows, picks and maces exist.
- **After the Battle** — the killed, the walking wounded, the stretcher cases, the captured, the missing and the deserted are counted apart. Without field surgeons the wounded die within the season. The victor rearms from the field, and mass death may leave it haunted.

**In your world:** Fog lay on the river at dawn. The defenders' archers fired blind while the attackers' hidden wing crossed upstream and struck their flank. The rout became a massacre, the meadow was left haunted, and settlers avoided it for generations.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/50-walls-will-fall.jpg"><img src="common/assets/images/dlc-covers/50-walls-will-fall.jpg" width="220" alt="Walls Will Fall box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/50-walls-will-fall.jpg"><img src="common/assets/images/dlc-backs/50-walls-will-fall.jpg" width="220" alt="Walls Will Fall box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 50. Walls Will Fall

*Starve them, storm them or wait for a traitor to open the gate.*

The engines have pounded the north wall since spring. Under your feet, sappers race the defenders' counter-miners through wet clay. Inside, the granaries are counted in days and the guilds are whispering. A siege lasts seasons and both sides suffer it: hunger, fever, sorties by night, and the long arithmetic of who breaks first, the wall, the garrison or the people behind it.

- **Five Roads into a City** — blockade, bombard, mine, assault or negotiate. Engines are matched against walls by their stone, mines against the rock and soil beneath, and an assault is a battle on wall ground where every breach strips the defender's advantage.
- **The Defender Answers** — sorties that burn the siege towers, masons who patch breaches from the stone stock, rationing and the hope of relief. Beneath the walls, sappers and counter-miners duel in the dark, and tunnels cave in.
- **Hunger and Fever** — rationing becomes famine, and famine reaches the taboo that only some peoples will break. Disease festers in the city and in the besiegers' camp alike, driven by water, sanitation and season.
- **Treason at the Gate** — starvation erodes the garrison's nerve and raises the risk of revolt in the streets, and a faction nursing an old grievance may simply open a gate.
- **Sack or Mercy** — the victor's doctrine and the commander's traits decide. A sack takes the treasury, the relics and the people, burns whole districts and earns infamy, and the city never forgets who conquered it.
- **Fleets at the Harbour Mouth** — only a fleet can starve a coastal city from the sea. Fort strength sets how hard a breach comes, artillery batters out breaches season by season, and a commander's siege skill tells.
- **Lines of Stone** — citadels and walled cities control the regions around them. An invader must besiege each fort or march past with its supply line cut, so fortress lines shape whole invasions.

**In your world:** The besiegers' mines drowned in the wet clay, so they waited. By the second winter the city had passed from rationing to famine. A guild with an old grievance opened the river gate, and the sacked city still names its conquerors in its laments.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/51-theatre-of-war.jpg"><img src="common/assets/images/dlc-covers/51-theatre-of-war.jpg" width="220" alt="Theatre of War box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/51-theatre-of-war.jpg"><img src="common/assets/images/dlc-backs/51-theatre-of-war.jpg" width="220" alt="Theatre of War box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 51. Theatre of War

*Wars are not won in battles. They are won in campaigns.*

Your offensive has taken three cities and is still advancing. Behind it the barges are slower, the depots thinner, the river line longer. Somewhere ahead lies the point where the attack must stop or collapse, and back home the markets are filling with one-armed sons. War runs season by season across fronts, depots and headquarters, and it ends at a table where every demand has a price.

- **Chain of Command** — army groups, armies, corps, divisions and brigades, each led from a headquarters with its own staff. Couriers and signal networks stretch its reach, and formations beyond it fight on standing orders.
- **Supply Is a River** — depots, wagons, pack animals, barges, ships and sky-barges carry supplies at a limited rate. Cut one depot or one river line and every army it feeds begins to starve.
- **The Culmination Point** — offensives outrun their supply as lines lengthen. Generals with a head for logistics see the limit coming, and a marshal who sends reserves to the wrong front on bad intelligence loses the war there.
- **Thirteen War Aims** — conquer a region, press a claim, convert, vassalise, liberate, destroy a cult, take revenge, loot. Occupied land yields taxes and levies, and its resistance grows with every atrocity remembered.
- **Casus Belli and War Score** — ten justifications, from holy war and vendetta to trade dispute and debt default, or naked conquest with none. Every peace clause costs war score: ceded land, tribute, hostages, conversion rights, a champion for disputes to come.
- **The Home Front** — war support rises with propaganda and a just cause and falls with taxes, casualties and maimed veterans in the streets. Weary peoples press for peace, while war workshops grow more efficient the longer they make one thing.
- **Parley** — bluffs and insults before battle, truces for the harvest and the burial of the dead, surrender terms with the honours of war, and exchanges of prisoners. Break a sworn term and it is remembered as an atrocity.

**In your world:** The offensive outran its barges, and enemy raiders burned the river depot behind it. The army starved where it stood. At home, every maimed son who returned drained the war's support, until the king accepted a white peace he had sworn never to sign.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/52-admiralty.jpg"><img src="common/assets/images/dlc-covers/52-admiralty.jpg" width="220" alt="Admiralty box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/52-admiralty.jpg"><img src="common/assets/images/dlc-backs/52-admiralty.jpg" width="220" alt="Admiralty box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 52. Admiralty

*The fleet upwind chooses the battle.*

The wind backs west and your squadron holds the gauge. You close on a reach, rake the enemy flagship along her length with chain shot and watch her rigging come down. War on the water is wind, timber and fire: every shot lands on a hull, a mast, a rudder or a crew, every captain dreams of prize money, and above the masts the skyships fight for the air.

- **Points of Sail** — close-hauled, reaching, running, tacking, caught in irons. The fleet upwind chooses the engagement, while galleys ignore the wind at the cost of their rowers' strength.
- **Damage Where It Hits** — round shot holes hulls, chain shot cuts rigging, grapeshot sweeps crews, fire pots catch sails. Fire spreads by deck timber, and one spark in the magazine ends a ship, which is what fire ships are for.
- **Boarding and Prizes** — marines fight boarding melees and galleys ram. Ships that strike their colours become prizes, prize crews thin the victor's decks, and prize money flowing to sailors' households makes captains bold.
- **Command of Sea and Sky** — armies cross water safely only under naval supremacy, and landings against defenders bleed. Skyships and flying mounts win the air to scout, strafe supply trains and bombard sieges, and only flyers, crossbows and mages can contest them.
- **Twelve Hulls by Design** — rafts, longships and carracks to bone hulls, living ships and generation ships, built from hulls, sails, sky-sails or void-sails, holds, wards and mage stations. Designs evolve, old ships are refitted, and neglected masts snap in storms.
- **Stars and Sea Clocks** — the compass works only where the world has a magnetic field, the astrolabe needs astronomy, and the sea clock gives longitude. Lost ships drift to unknown shores, and crews who run short of water mutiny.
- **The Admiralty Board** — admirals fight generals for the treasury in council, and naval treaties cap tonnage by class. Cheating on them is a scheme of its own.

**In your world:** The admiralty hid two warships from the tonnage treaty. When war came they held the weather gauge, raked the enemy flagship with chain shot and took her as a prize. The prize money filled the captains' houses, and recruits crowded the docks.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/53-blade-and-honour.jpg"><img src="common/assets/images/dlc-covers/53-blade-and-honour.jpg" width="220" alt="Blade and Honour box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/53-blade-and-honour.jpg"><img src="common/assets/images/dlc-backs/53-blade-and-honour.jpg" width="220" alt="Blade and Honour box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 53. Blade and Honour

*Seven exchanges. One will walk away.*

The spear reaches first. Your champion turns it on his shield, steps inside, and the long weapon is suddenly useless. Single combat is fought exchange by exchange, and every one weighs reach, skill, footing, stamina and nerve. Fighters feint, parry, wrestle and bleed. A duel ends in a yield, a lost eye or hand, or death, and the victor's ethics decide the fate of the one on the ground.

- **Three to Seven Exchanges** — each weighs weapon skill, reach, armour, footing in the day's weather, fading stamina and pain. A spear outreaches a sword until the swordsman closes.
- **Strike, Feint, Parry** — fighters choose strikes at called targets, feints, blocks, parries, dodges and grapples. Whether a parry meets the blow depends on how well the defender reads the attack against the attacker's skill at deceit.
- **Grapple and Throw** — grab a limb or the weapon, throw, choke a foe senseless, lock a joint until it breaks or, in some cultures, bite when desperate.
- **Lance and Horse** — a couched lance strikes with the mass and speed of the mount. The horse itself is a target, and a falling horse crushes its rider.
- **Wounds That Remain** — duels end by yield, disarm, crippling wound or death. The loser does not limp off "badly wounded". He loses an eye, a hand or a leg, and carries the loss for life.
- **Five Reasons to Fight** — war duels, honour duels born of grievance, trials by combat, champions whose single fight ends a war, and duels between gods that leave divine wounds.
- **Mercy on the Ground** — a downed fighter fights at a penalty. The victor's mercy decides whether he lives, honour decides whether a yield is accepted, and every exchange goes into a plain account for the battle report and the bard.

**In your world:** Two kings agreed that a champion would end their war. The challenger's spear held the first exchange. The defender closed, broke his elbow in a lock and, as his people's mercy required, let him yield. The bards sang of it, and the treaty held.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/54-blood-feud.jpg"><img src="common/assets/images/dlc-covers/54-blood-feud.jpg" width="220" alt="Blood Feud box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/54-blood-feud.jpg"><img src="common/assets/images/dlc-backs/54-blood-feud.jpg" width="220" alt="Blood Feud box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 54. Blood Feud

*They killed my father. I will kill their son.*

Your house remembers the name of every kinsman they killed. Each epoch the grievance asks what honour demands: a raid, a knife in the dark, blood money or war. Every answer adds a name to their side of the ledger. Around the feud turn captives held for ransom, heirs raised in the enemy's hall, and children carried off in raids who come back wearing the enemy's colours.

- **The Ledger of Blood** — a feud is the memory of killed kin between two houses or peoples. The aggrieved raid, assassinate, demand blood money or escalate to a war of vendetta, and every killing feeds the other side's grievance.
- **What Ends a Feud** — blood-money law, intermarriage, a common enemy, a priest who preaches peace and the slow fading of memory over generations. Without them a feud outlives the people who began it.
- **Captives by the Thousand** — pursuits and sacks take whole cohorts captive, to be ransomed, enslaved where law allows, sacrificed where doctrine demands, worked, exchanged or freed. Named captives are tortured for war plans or married into the captor's house.
- **Hostage Wards** — child heirs raised at the enemy's court absorb its culture and its memories. They return as friendly rulers or as vengeful ones, as their temperament decides.
- **Stolen Children** — raiders carry off children who forget their origins unless their memory is strong. They grow into captor soldiers or famous turncoats, while their kin plot rescues and quests.
- **Slave Soldiers** — enslaved cohorts fight with low morale, desert readily and may turn on their masters mid-battle when their own people stand opposite.
- **Parole** — a captured officer may swear never to fight again and walk free. Breaking parole is breaking an oath, and the shame follows him home.

**In your world:** A raid took the chieftain's youngest son. He grew up in the captors' hall, forgot his own people and led their warband back against them. His elder brother killed him at the ford, and the feud began again from the other side.

</td>
</tr>
</table>
</details>

<a id="chapter-vii"></a>

### 🕯 VII. Faith and Spirits

<details open>
<summary><b>Expansions 55–60</b> · <sub>6 expansions</sub></summary>

<table>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/55-tenets-of-flame.jpg"><img src="common/assets/images/dlc-covers/55-tenets-of-flame.jpg" width="220" alt="Tenets of Flame box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/55-tenets-of-flame.jpg"><img src="common/assets/images/dlc-backs/55-tenets-of-flame.jpg" width="220" alt="Tenets of Flame box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 55. Tenets of Flame

*Every faith has tenets. Every tenet has a price.*

Your god's faith is no longer a count of followers. It has a doctrine, a clergy, temples, lands and a treasury. Its tenets decide whether the maimed are holy or unclean, whether captives die on the altar, whether priests may found dynasties. Persecution feeds its zeal and comfort starves it. And somewhere a brilliant theologian is already drafting the heresy that will split it in two.

- **Twenty-Three Tenets** — three to six per faith, each with real effects. Sacred suffering honours the maimed while purity of body calls them unclean, celibate clergy found no houses, and human sacrifice consumes captives and earns infamy abroad.
- **Zeal That Burns and Fades** — persecution, martyrs, miracles, holy war victories and plague raise it; prosperity, scandal and failed prophecies drain it. Push it too high and fanaticism follows: inquisition, iconoclasm, crusade.
- **Clergy, Tithes and Relics** — high priests, priests, monks and inquisitors, paid by tithes that also fund alms, war chests and monasteries that keep learning alive through dark ages. Saints' bones draw pilgrims, coin and disease.
- **Heresy and Schism** — doctrine drifts under a creative theologian and splits into a heresy tree. Orthodoxy decides between inquisition and tolerance, councils vote on tenets and saints, and a vacant High Seat can crown two rival heads.
- **Missions on the Trade Roads** — preachers travel with the caravans. Conversion turns on how well the doctrine fits the culture, the missionary's skill and the miracles behind them, against rival clergy and the language barrier.
- **Church and Crown** — divine kingship fuses throne and altar; elsewhere priests and rulers fight over investiture, and excommunication strips a ruler's legitimacy. Your sons can reveal a new tenet and see whether it takes.
- **Sanctuary** — temples shelter criminals, runaway slaves and defeated rivals. A pursuer must besiege, bargain or wait, because breaking sanctuary is desecration.

**In your world:** The inquisition burned a beloved preacher. His followers' zeal soared, a theologian gave them a doctrine, and the heresy broke away. When the High Seat fell vacant, each church crowned its own head, and every ruler had to choose a side.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/56-prophets-of-the-end.jpg"><img src="common/assets/images/dlc-covers/56-prophets-of-the-end.jpg" width="220" alt="Prophets of the End box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/56-prophets-of-the-end.jpg"><img src="common/assets/images/dlc-backs/56-prophets-of-the-end.jpg" width="220" alt="Prophets of the End box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 56. Prophets of the End

*The comet returns. The end is near. Sell everything.*

A comet hangs over the third hungry year. On the hill a prophet names the day the world will end, and farmers sell their fields to follow him. Faith runs wild outside the temple too: mystics with visions the priests cannot control, rites that guard the soul, gods whose silence through a plague becomes a crisis of belief, and cities that slowly stop praying at all.

- **Visions Outside the Temple** — intuitive, devout mortals have visions and states of union, gather followers beyond the clergy and found orders or heresies. Their contact is real only if a god chooses to answer, and only you know which.
- **The End Is Coming** — prophecies of an end time, omens in the sky and deepening misery raise movements that sell their land, stop working, march, attack the unclean or wait for the end on a mountain.
- **When the Day Passes** — the faithful disperse, set a new date, or harden into a sect that will outlive its prophet.
- **The Silent God** — when plague, famine or defeat strikes the faithful and their god gives no sign, the doctrine faces a crisis. Theologians argue, a new teaching casts suffering as a trial, or the people convert away.
- **Rites with Real Protection** — birth blessings, initiations, marriages and last rites shield the soul's road after death, protect children against possession and keep the dead from walking restless. A plague that leaves no priest to give them is a real danger.
- **The Emptying Temples** — literacy, prosperity, city life, new theories of nature and gods who stay silent too long drain faith away. Disasters, wars and miracles fill the temples again.

**In your world:** A comet and a famine gave a prophet his date. Whole villages sold their land and climbed the mountain to wait. When the day passed, most went home poorer. The rest chose a new date and hardened into a sect.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/57-beyond-the-veil.jpg"><img src="common/assets/images/dlc-covers/57-beyond-the-veil.jpg" width="220" alt="Beyond the Veil box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/57-beyond-the-veil.jpg"><img src="common/assets/images/dlc-backs/57-beyond-the-veil.jpg" width="220" alt="Beyond the Veil box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 57. Beyond the Veil

*Death is not the end. It is a verdict.*

A warlord dies certain of the warrior's hall. The judges weigh his renown, his faith, the rites at his pyre and the villages he burned, and the verdict surprises him. Now the afterlife is a real place with strata and gates. Ghosts walk for reasons, possession has a cure, and only an exceptional few ever come back as newborns carrying an old grudge.

- **Strata of the Dead** — paradise, plain, torment, oblivion or a faith's own warrior hall, each with its entry criteria. Every realm of the dead shows its population, and every soul carries a ledger and the reason for its verdict.
- **The Weighing** — the patron god's doctrine of judgement, the funeral rite and divine favour decide the road. Renown, honour, faith, violence and unthinkable acts all count, and the unburied wander restless.
- **Rebirth Is Earned** — a soul returns only through an open gate, a faith, a law of nature, a rite or a god's own hand, and only if its life was exceptional. The reborn keep faint memories, enough to know an old enemy.
- **Seven Kinds of Ghost** — lingering, vengeful, sorrowful, place-bound, poltergeist, bound guardian and possessing. Each needs its own remedy: a memorial stone carved with the name, a proper funeral, a dream fulfilled by kin, vengeance done or exorcism.
- **Possession and Its Cure** — a spirit can take a living body, replace the host's mind with its own and fill the host with dread, until an exorcism drives it out.
- **Ancestors and Soul-Eaters** — venerated ancestors bring household luck and courage at ancestral sites, and turn restless when offerings stop. Soul-eaters devour the dead and rob a god of the faithful it was owed.
- **The Afterlife Surprise** — every faith teaches an afterlife, and the real one may differ. Souls who find their belief false suffer a revelation shock, and the dead who return in dreams can tell the living.

**In your world:** A warlord died certain of the warrior's hall and was judged into torment for the villages he had burned. The shock left him restless. His ghost told his son the truth in dreams, and the son's account set the temple's theologians at each other's throats.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/58-spirits-of-hearth-and-river.jpg"><img src="common/assets/images/dlc-covers/58-spirits-of-hearth-and-river.jpg" width="220" alt="Spirits of Hearth and River box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/58-spirits-of-hearth-and-river.jpg"><img src="common/assets/images/dlc-backs/58-spirits-of-hearth-and-river.jpg" width="220" alt="Spirits of Hearth and River box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 58. Spirits of Hearth and River

*Pay the river spirit, or pay the flood.*

Every crossroads has its spirit, every hearth its luck and every river a temper. Make the offering and the crossing is safe; foul the water and the flood comes. Above them sits a heavenly civil service of city gods and river gods with ranks, written petitions and appeals to higher office. Spirits are promoted and dismissed, and a village can take its own river to court.

- **Genius Loci** — rivers, springs, groves, hearths, crossroads, mountains and cities can each host a spirit with its own temper and tastes, and a running account of offerings and favours with the people around it.
- **Offend the Spirit** — content spirits bring fertility, safe crossings, good catches and hearth luck. Pollution, felled forests, an unpaid offering or a broken taboo bring misfortune, floods and illness instead.
- **The Celestial Bureaucracy** — hearth gods, river gods and city gods hold ranks under your sons and the foreign gods. Mortals petition them in writing, and petitions suffer delays, bribes paid in offerings and appeals to a higher office.
- **Promotion and Dismissal** — spirits rise for good service, growing worship and petitions resolved, and are demoted or dismissed for neglect. A village can sue its river god before the city god.
- **Emotion Spirits** — where magic runs thick, fear on a battlefield, joy at a festival, grief at a funeral and rage in a mob take shape as spirits that amplify the feeling, feed the matching gods and can be bound by rites.
- **Teachers from Beyond** — ancestors, ghosts and place spirits teach through dreams, visions and possession: songs, rites, lost techniques, true names, prophecies, the way to buried treasure. Their teaching carries their biases and errors with it.

**In your world:** A tannery upstream fouled the river, and the offended river spirit flooded the lower town. The villagers petitioned the city god, paid their bribes in incense and appealed again. They won, and the river god was demoted.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/59-hex-and-hunt.jpg"><img src="common/assets/images/dlc-covers/59-hex-and-hunt.jpg" width="220" alt="Hex and Hunt box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/59-hex-and-hunt.jpg"><img src="common/assets/images/dlc-backs/59-hex-and-hunt.jpg" width="220" alt="Hex and Hunt box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 59. Hex and Hunt

*The cow died. The child sickened. Someone must be to blame.*

The cattle die in a wet spring and nobody knows why. Your village knows exactly why: the widow at the edge of the wood. Luck, charms and witchcraft are beliefs your peoples truly hold, and they act on them. In a world where magic is real, a witch hunt may find a real witch. You will always know who was guilty, and who burned for nothing.

- **Lucky Days and Unlucky Numbers** — every culture reads luck into its calendar, its signs, its numbers and its gestures, and fears or welcomes the days they mark.
- **Charms That Work, Charms That Comfort** — amulets for protection, fertility and luck truly work where they are enchanted or blessed. Elsewhere they only calm the wearer, which is a real effect too, and you can see which is which.
- **Who Is the Witch** — illness, failed crops, a child's death or dying livestock with no clear cause find a culprit. Belief, grievance and social distance choose her: the envied neighbour, the widow, the outsider, the eccentric.
- **From Accusation to Ordeal** — diviners and rumour name the accused, and trials, ordeals, exile or murder follow.
- **When the Hunt Spreads** — plague, famine and war, fanned by zealous inquisitors, turn one accusation into a cascade. Hunts leave memories, chronicles and the vengeful ghosts of the wrongly killed.
- **Real Witches** — where rites and curses exist, some of the accused truly are casters. The engine knows who, and you see every accurate and every false accusation.

**In your world:** Murrain took a village's cattle in a plague year. Rumour named the widow by the wood, the ordeal drowned her, and the hunt spread to her neighbours. Only one of the dead was a real witch, and it was not the widow. She came back as a vengeful ghost.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/60-omens-and-oracles.jpg"><img src="common/assets/images/dlc-covers/60-omens-and-oracles.jpg" width="220" alt="Omens and Oracles box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/60-omens-and-oracles.jpg"><img src="common/assets/images/dlc-backs/60-omens-and-oracles.jpg" width="220" alt="Omens and Oracles box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 60. Omens and Oracles

*The child born under the comet will rule. The king has heard it too.*

A seer speaks, and from that day the world is listening. Prophecies here have conditions the world itself can meet: a death, a fall, a birth under a sign, a war within so many epochs. Believers chase them and rulers try to kill them, which is often how they come true. Kings consult the birds before battle, and only you know which diviners truly see.

- **Prophecies the World Can Keep** — a prophecy names its condition, a death, a city's fall, a birth into a house, an eclipse, and is fulfilled the moment the world meets it. Matching legends make it surer, and retelling distorts it.
- **Self-Fulfilling Fates** — believers act for or against the prophecy. Children born under the comet gain claims, the king grows paranoid and infants die. When a deadline passes, the seer is mocked, zeal cools and cynicism spreads.
- **Six Ways to Read the Gods** — augury, sacrifice readings, astrology, oracles, lots and dream reading. Each is truly informative only where a god answers, a seer has the gift or the laws of nature allow. Elsewhere trusted diviners breed folly.
- **Seers and Blind Spots** — the gifted glimpse probable futures that can still be wrong, because others act on prophecy too. Rival seers blind each other, and outer beings never appear in any vision.
- **Born Under a Sign** — every mortal carries the sky of its birth. Where the stars truly hold power the sign shapes temperament and fortune; elsewhere it is belief alone, and a child born under a dreaded sign may be cast out.
- **Six Kinds of Dream** — ordinary, nightmare, longing, prophetic, visitation and shared. Nightmares recur, dream readers misread, and a king's dream taken for a war omen can start a war.

**In your world:** A seer foretold that a child of the river house would rule. The king's fear became a purge of the house's infants. One escaped to foster parents, grew up on the prophecy, and took the throne from the man who had tried to kill him.

</td>
</tr>
</table>
</details>

<a id="chapter-viii"></a>

### ✶ VIII. Magic and Myth

<details open>
<summary><b>Expansions 61–64</b> · <sub>4 expansions</sub></summary>

<table>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/61-the-arcanum.jpg"><img src="common/assets/images/dlc-covers/61-the-arcanum.jpg" width="220" alt="The Arcanum box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/61-the-arcanum.jpg"><img src="common/assets/images/dlc-backs/61-the-arcanum.jpg" width="220" alt="The Arcanum box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 61. The Arcanum

*Create. Destroy. Control. Fire. Mind. Spirit. Combine.*

Your mage does not pick a spell from a list. She writes one: a technique and a form, a range and a duration, tested through a season in the laboratory and copied into a text her apprentices can learn. Then the world argues back. Rain dampens her fire, iron unravels her spirits, a gag silences her, and the theory she was taught may simply be wrong.

- **Spell Grammar** — eight techniques, from create and perceive to bind and ward, crossed with fourteen forms from fire to time, void and light. Range runs from touch to a whole world, duration from an instant to forever, and every combination has its price.
- **Vis and the Black Market** — magical resources of every form, fire vis to death vis, gathered at magic sites, cut from beasts and drawn from phenomena. Where magic is banned they move through the shadows.
- **Resistance and Counterspells** — willpower, wards, iron, sanctity, faith and a hostile god's dominion resist a rite. Counterspells, dispels and wards meet in contests of power.
- **Rain on a Fire Rite** — magic reads the weather and the world. Wet targets conduct storm rites, rain weakens fire and strengthens water, a dry forest turns a fire rite into a wildfire, and void rites overflow where the dark leaks in.
- **Tongue, Hand and Breath** — rites need speech, gesture, inscription, song, dance, reagents or focus. A tongueless mage can still inscribe, a blinded one can still chant, and captive mages are held with gags, bound hands and blindfolds.
- **Material Magic** — metals that grant strength to the gifted who consume them, crystals that store a technique, salt that wards off spirits, and enchanted items with charges that recharge with the moon and crack with overuse.
- **Orders and Paradigms** — magical orders keep codes, enforce them in tribunals and hold covenants with laboratories and libraries. Each tradition rests on a theory, and the closer it stands to the true laws of the world, the better its rites work.

**In your world:** During a drought a war mage threw fire into the forest where the enemy waited. The dry wood turned the rite into a wildfire. It burned both armies, then the covenant downwind, and every laboratory text in its library.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/62-forbidden-arts.jpg"><img src="common/assets/images/dlc-covers/62-forbidden-arts.jpg" width="220" alt="Forbidden Arts box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/62-forbidden-arts.jpg"><img src="common/assets/images/dlc-backs/62-forbidden-arts.jpg" width="220" alt="Forbidden Arts box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 62. Forbidden Arts

*Some doors should never be opened. Open them anyway.*

When the city is falling and mercy runs low, someone always reaches for the forbidden page. Blood rites paid in flesh, void rites paid in sanity, the dead raised to march without bread or fear. Power comes fast here and it leaves marks: mages who warp, ancients who cannot stop buying years, and failed rites that become storms that never end.

- **Blood and Void** — blood rites spend the caster's own body or a captive's life, and void rites spend sanity and let the dark leak in. They bring infamy, and desperate, merciless casters reach for them first.
- **Towers of the Dead** — necromancers raise the battle dead into hosts that know no fear and need no food, decaying unless fed with essence or souls. From their towers they besiege the living, and most peoples hold their craft unthinkable.
- **Curses and Transformations** — dark rites lay curses, blessings and changes of the body on their targets, the same afflictions that turn a man into a beast under the moon.
- **A Lock of Hair** — hair, blood, a name, a portrait or a splinter of a ship links a rite to its target, and the stronger the link, the deeper it strikes. The wary burn their hair and guard their true names.
- **Warping** — mages, people who live on ley lines and wearers of enchanted items slowly change: strange looks, attunement, madness, unnatural long life.
- **Bought Decades** — potions and rites hold off age at a price in rare resources, with warping and a growing dependence. Cut off an ancient mage's supply and the years come due.
- **Backlash** — a failed rite can wound, madden, widen the void's leak or let a summoned thing escape. A failed storm rite can become a storm that never ends.

**In your world:** Rivals seized the spring that fed an ancient mage's longevity potions. His years caught up with him, and in desperation he tried a void rite. It failed, and the thing he summoned slipped its bonds and went hunting in the valley below.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/63-walkers-of-myth.jpg"><img src="common/assets/images/dlc-covers/63-walkers-of-myth.jpg" width="220" alt="Walkers of Myth box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/63-walkers-of-myth.jpg"><img src="common/assets/images/dlc-backs/63-walkers-of-myth.jpg" width="220" alt="Walkers of Myth box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 63. Walkers of Myth

*Walk the god's path. Change the god's story.*

The elders tell how the god crossed the river of night. Your hero walks into that myth and must walk it step by step: the same trials, the same choices, the same faith. Follow the story and the boon is sure. Break from it and you may win something new, and come home to find your people telling the tale your way.

- **Legends That Live** — eleven archetypes, from flood and trickster to cursed line and return of the king. Every retelling bends the tale toward the teller's values, so in an honour culture a defeat becomes a betrayal. Only art fixes a legend in place.
- **Stories That Move People** — a return-of-the-king legend strengthens the pretender who fits it, a cursed-line legend shames a house, and a haunted-place legend keeps settlers away with no ghost there at all. You can compare every telling with the truth.
- **Heroquests** — questers enter the god's palace, the realm of the dead, a dream world or a sacred site, facing trials of skill, passion and faith. Boons include blessings, rites, lifted curses and true names; failure traps the soul or breaks the myth.
- **Rewritten Myths** — a quester who deviates may win a different boon, and the people's version of the legend changes with the hero's return.
- **Myth-Powered Rites** — rites that re-enact a believed myth grow stronger, stronger still at the myth's own site. A corrupted myth gives a corrupted rite.
- **Geasa** — never refuse hospitality, never pass a burning house. A seer, god or rite lays the taboo at birth. Keeping it wins favour, breaking it brings doom, and enemies build traps to force the breach.
- **True Names** — gods, spirits, some beasts, mortals and places have one. Knowing it commands lesser beings or binds them, and it is learned by deciphering old tongues, by scheming or from an intimate's confession.

**In your world:** A heroine walked the flood myth step by step but saved the village the legend drowns. She came home with a different boon, her people retold the myth her way, and their rain rite, sung to the new telling, changed with it.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/64-clockwork-souls.jpg"><img src="common/assets/images/dlc-covers/64-clockwork-souls.jpg" width="220" alt="Clockwork Souls box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/64-clockwork-souls.jpg"><img src="common/assets/images/dlc-backs/64-clockwork-souls.jpg" width="220" alt="Clockwork Souls box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 64. Clockwork Souls

*It was told to guard the gate. The city fell three hundred years ago.*

In the ruins of a city dead for three centuries, a bronze guardian still walks its round. Its order was to guard the gate, and nobody ever told it to stop. Constructs obey their orders to the letter, loopholes and all, so the thief who steals the command seal steals the army. And some of them, built around a bound soul, begin to remember.

- **Bodies Made, Not Born** — golems, automata, homunculi and thinking war machines, each with its material and its power source: a bound soul, a rune, divine essence or a ley line.
- **Orders to the Letter** — "guard the gate", "kill intruders", "obey whoever holds the seal". Constructs follow their instructions literally, so every order hides a loophole and every seal is a prize worth stealing.
- **Runes That Fade** — power sources dwindle, materials wear, and runes need renewing by a maker with the skill. Neglect breaks them down.
- **The Master's Death** — when the maker dies, the construct keeps its last orders forever, a hazard in every ruin and a guardian in every tomb.
- **The Soul in the Machine** — constructs built around a bound soul inherit fragments of who it was, and over epochs they begin to want. When they rise against their masters, the rebellion has a cause.
- **Legions from the Foundry** — identical constructs made in numbers from rare materials work the mines and fields and fill the ranks. They feel no fear, but a dispel or a lost command seal stops them dead.

**In your world:** A tomb robber lifted the command seal from a dead emperor's crypt, and the bronze guards that had killed every intruder for centuries followed him out. He hired them to a mine, until one guard, powered by a bound soul, remembered it had once been a slave.

</td>
</tr>
</table>
</details>

<a id="chapter-ix"></a>

### ☀ IX. The Gods

<details open>
<summary><b>Expansions 65–72</b> · <sub>8 expansions</sub></summary>

<table>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/65-forty-domains.jpg"><img src="common/assets/images/dlc-covers/65-forty-domains.jpg" width="220" alt="Forty Domains box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/65-forty-domains.jpg"><img src="common/assets/images/dlc-backs/65-forty-domains.jpg" width="220" alt="Forty Domains box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 65. Forty Domains

*Every god has a domain. Every domain has a price.*

Your son of the Sea does more than watch the waves. His worshippers fight harder at sea, storms on the open water answer to him, and his essence swells with every voyage. Forty domains reach into war, trade, faith and nature through hooks of their own. A god is now what it does in the world, and when a Harvest god takes a wound, its worshippers face a hungry decade.

- **Forty Domains, All of Them Mechanical** — every domain does real work. Salt curses soil or keeps food from rotting, Glass grinds lenses for astronomers, Lie twists rumours, Road guards travellers, Time speeds ageing and sharpens prophecy.
- **140 Aspects** — each domain splits into three or four aspects, so one War god is valour and another slaughter. Pairs combine: a god of Sea and Death sends the drowned to an undersea realm.
- **Forbidden Pairings** — aspects are friendly, neutral or precluded. Mercy and slaughter can never share one god, and deeds that drag a god toward a forbidden aspect cost it sanity and can fracture a domain outright.
- **Essence Earned by Deeds** — income follows each domain's activity, battles for War, deaths for Death, voyages for Sea. Gods cultivate their domains, quarrel over the same sailors and contest the same battle with rival miracles.
- **Gods with Goals and Grudges** — be worshipped, found a holy world, destroy a rival, spread Plague to a chosen world, raise a hero's house, reconcile with the Creator or rebel. Gods remember who stole their worshippers and who helped their hero.
- **Love, Awe, Fear and Neglect** — every people holds its own standing toward every god. Answered prayers breed love, wrath breeds fear, silence breeds neglect, and neglect drains worshippers and existence alike.
- **Hearts, Schemes and Wounds** — gods feel wrath, jealousy, pride and longing, befriend, marry and frame each other through mortal agents, and curse whoever defiles their shrines. Their wounds are typed: a severed domain, a shattered form, a stolen true name.

**In your world:** Sea and Storm fought over the same sailors. Storm's mortal agents framed Sea's priests for desecrating a harbour shrine, but the scheme was uncovered. The pantheon council voted to strip Storm of a power, and Sea never forgot it.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/66-dominion.jpg"><img src="common/assets/images/dlc-covers/66-dominion.jpg" width="220" alt="Dominion box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/66-dominion.jpg"><img src="common/assets/images/dlc-backs/66-dominion.jpg" width="220" alt="Dominion box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 66. Dominion

*The gods' war is fought over every field and village.*

Look at the map and you see it: your son's presence pooling around his temples, his prophets and his saints, seeping into the next valley, pressing against a rival's light. Where his dominion rules, his scales rule too. Crime falls or unrest rises, the air warms or cools, the fields swell or decay. Every farmer feels which god is winning.

- **A Map of Divine Presence** — every god holds a strength in every region, fed by temple splendour, holy sites, prophets, saints, miracles and worshippers. Each epoch it spreads into neighbouring land, and every god knows where it is losing ground.
- **Six Scales** — order or turmoil, productivity or sloth, heat or cold, growth or death, fortune or misfortune, magic or drain. Each runs from minus three to plus three and reshapes every region the god dominates.
- **The Home Advantage** — under its own dominion a god's miracles cost less and work better, its missionaries convert more easily and its worshippers fear less. Rival miracles cost more there, and rival priests feel the strain.
- **Credit and Blame** — where dominions overlap, each people decides which god it thanks for a miracle and which it blames for a disaster. Gods gain and lose standing for each other's acts.
- **Thrones of Power** — a few mythic thrones on every world grant dominion, essence and standing across it. Holding most of a world's thrones counts toward a god's ascension, and mortals fight these wars on their gods' behalf.
- **Hidden Magic Sites** — places that feed a school's rites, ward a land or open a gateway, unseen until a mage of the matching school finds them. They yield magic every epoch, and realms go to war for them.
- **Gods Built to a Budget** — each summoned son spends a creation budget on stats, dominion, scales, magic, an avatar body and powers. Extreme scales cost or refund budget, and Fate checks the design, so sons differ in kind, not only degree.

**In your world:** A Death son's temples and a captured throne of power spread his dominion across a small world. His scale tipped toward death: fields decayed and the spirits grew restless, until the Life son's worshippers marched to take the throne back.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/67-made-in-their-image.jpg"><img src="common/assets/images/dlc-covers/67-made-in-their-image.jpg" width="220" alt="Made in Their Image box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/67-made-in-their-image.jpg"><img src="common/assets/images/dlc-backs/67-made-in-their-image.jpg" width="220" alt="Made in Their Image box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 67. Made in Their Image

*The people believe their god has a lion's head. Now it does.*

You summoned a son of War. His frightened worshippers remember him as lion-headed and cruel, and slowly, epoch by epoch, he becomes exactly that. Belief pulls hardest in plague and war, on a fading god, from a faith that agrees with itself. A proud god resists. A vain one yields. Your gods are partly what their peoples make of them.

- **Belief Shapes Gods** — each epoch the stories a people tells pull its god's aspects, form and temperament toward the believed image. The pull is strongest when the image is uniform, widely held and the times are desperate.
- **Resist, Embrace or Pin** — a son can pay essence to resist the image or embrace it for standing, and you can pin its nature so belief cannot touch it. Pride and willpower hold firm; vanity yields, and a fading god is clay.
- **Loved or Feared** — from its acts each people reads a god as benevolent or malevolent. That sets devotion or appeasement, its temples, its avatar and its prayers: a loved god is begged to come, a feared one paid to stay away.
- **Miracles That Count** — a miracle is worth its magnitude times its witnesses, need and novelty. Bread in a famine counts more, the tenth repeat less, and a miracle that defies a people's idea of the god may be credited to another.
- **Fed by Emotion** — every aspect drinks a mortal feeling. Slaughter feeds on rage, Love on longing, Death on grief, Madness on despair, Trickery on amusement, the Hunt on fear. A god of grief prospers in plague years.
- **Heaven's Bureaucracy** — sons supervise the offices of lesser spirits, processing petitions and appointing city gods. Diligence earns standing and dominion; neglect rots the bureaucracy into corrupt spirits, unanswered prayers and cults of rogue spirits.

**In your world:** A people's legends gave the War son a lion's head, and over the epochs his avatar grew a mane. His temper drifted toward wrath with it. A neighbouring people who knew him as a peacemaker saw their god turn apostate, and their faith split in two.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/68-avatars.jpg"><img src="common/assets/images/dlc-covers/68-avatars.jpg" width="220" alt="Avatars box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/68-avatars.jpg"><img src="common/assets/images/dlc-backs/68-avatars.jpg" width="220" alt="Avatars box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 68. Avatars

*The god walks among us. The god can bleed.*

Your son puts on flesh and walks into a mortal city. He can act, fight and be killed, and if a mortal blade finds him the wound follows him back to heaven. Or he raises a great beast and teaches it with reward and punishment until it acts on its own. Or he leaves a child in a mortal house, and a bloodline begins.

- **Avatars in Mortal Form** — a son can manifest as a mortal who walks the world and acts in it. The avatar can be wounded and killed, and its death leaves the god itself with a divine wound.
- **The Divine Creature** — raise a great beast that acts on its own between your son's turns. Its god rewards and punishes specific habits: eating villagers, helping farmers, hurling rocks at the enemy.
- **Taught, Not Scripted** — every reward and punishment reshapes what the creature chooses to do, and a neglected creature drifts toward its own hungers. Whatever it does, the people credit or blame its god, in standing and in dominion.
- **Divine Blood** — the mortal children of a god mark their house with divine blood, a lineage the world can read and that runs on down the generations.
- **Children of Two Gods** — a child born to two gods inherits the average of its parents' powers with a deviation of its own, plus one domain from each parent. A son of Sea and a goddess of Death can raise an heir to both.

**In your world:** A Harvest son trained his divine creature to help farmers, punishing it each time it ate a villager. When his attention turned to another world, the neglected beast drifted back to its hungers, and the valley's love for its god curdled into fear.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/69-court-of-heaven.jpg"><img src="common/assets/images/dlc-covers/69-court-of-heaven.jpg" width="220" alt="Court of Heaven box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/69-court-of-heaven.jpg"><img src="common/assets/images/dlc-backs/69-court-of-heaven.jpg" width="220" alt="Court of Heaven box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 69. Court of Heaven

*Even gods must vote. Even gods must scheme.*

The pantheon gathers and the motion is war on a foreign god. Votes weigh old friendships, private goals and grudges, and the result binds every god for epochs, enforced as law. Lose the vote and your son may be chained, exiled or stripped of a power. And a motion that fails can escalate, backer by backer and favour by favour, into divine war.

- **Eight Kinds of Motion** — war on a foreign god, divide the worlds, outlaw a rite, punish a son, bless a hero, declare a holy world, set a cosmic truce, petition the Creator. Each one passed becomes binding law for a set span of epochs.
- **Councils as Crises** — motions gather backers, call in favours and escalate. A dispute the council cannot settle can end in war between gods.
- **Cosmic Offices** — Lord of the Dead, Keeper of the Gates, Warden of the Stars, Judge of Oaths, Herald of the Creator, Master of the Hunt. Each brings duties, rites and essence, won by vote, the Creator's grant, conquest or mantling.
- **Duties Left Undone** — an absent Lord of the Dead lets ghosts multiply. An absent Keeper of the Gates lets the routes between worlds decay.
- **Divine Servitors** — heralds, guardians, angels, furies, psychopomps and choirs carry messages, guard thrones, judge souls and fight as heavenly hosts. They have minds of their own, and ill-treated servitors fall to a rival or the outer dark.
- **Foreign Gods with Agendas** — the old gods of a world gain goals, domains and standing of their own. A native Harvest god competes with your son of Harvest for the same farmers, and seeds the tenets of the native faith.
- **Pacts and Pantheons** — foreign gods hold opinions of each other and of your sons, ally against the pantheon, scheme, sign divine pacts and share worship. Native pantheons have family trees and divine titles their peoples tell of in legend.

**In your world:** The council made a son of Death Lord of the Dead, but he spent the next epochs chasing a rival's worshippers. Ghosts multiplied across the realms he neglected, and in the crisis that followed, the office passed to the rival he had been robbing.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/70-apotheosis.jpg"><img src="common/assets/images/dlc-covers/70-apotheosis.jpg" width="220" alt="Apotheosis box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/70-apotheosis.jpg"><img src="common/assets/images/dlc-backs/70-apotheosis.jpg" width="220" alt="Apotheosis box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 70. Apotheosis

*A mortal walked the god's path. Then killed the god.*

A mortal champion copies your son's defining deeds, gathers a cult of her own and survives his anger. Your son is weak: his faith thin, his standing low. She is overwhelming. When she finally kills him, Fate may let her take his place, his aspects, his dominion and part of his worshippers. You saw it coming the whole way. The question is whether you acted.

- **The Mantle of a God** — imitate a god's defining deeds, gather worship and survive the god's opposition, and a mortal can ascend as a new son when Fate approves.
- **Slaying a God** — replacement needs three things at once: a god weak in existence, faith and standing; a mortal overwhelming in renown, worship, deeds and power; and the god's death at that mortal's hand. Your own sons are not exempt.
- **The Fallen** — a god stripped of divinity wakes as a mortal with great gifts, memories of godhood, a hidden true name and no essence. A loyal remnant may recognise it, and it can seek its name or a heroquest to climb back.
- **Lost to the Void** — a son driven to zero sanity by void bargains passes out of the cosmos as an outer being, keeping its memories and its grudges. Its worshippers become an outer cult, and no resurrection is possible while the horror endures.
- **Everything Can Become Something Else** — a cursed people loses its sapience and turns feral; a cult with endogamy and a diaspora becomes a nation; a beast founds a species, the "children of the Wyrm". Names, history and memories carry across.
- **Suns That Become Gods** — a star worshipped long enough becomes a god whose dominion follows its light, and a living world its peoples worship can ascend as a god whose body is the world. Kill a star-god and its sun dims.
- **Warnings and Levers** — you hear of a fall one epoch ahead, of a son entering the corruption danger band, of a mortal starting to meet the conditions to slay a god. Cleanse, forbid bargains, chain, block or pin: you can always act.

**In your world:** A son of the Hunt bargained with the void until his sanity broke and he passed out of the cosmos. His hunters became an outer cult. Generations later, when the horror was banished, his last faithful began a redemption heroquest to bring him home.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/71-laws-of-creation.jpg"><img src="common/assets/images/dlc-covers/71-laws-of-creation.jpg" width="220" alt="Laws of Creation box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/71-laws-of-creation.jpg"><img src="common/assets/images/dlc-backs/71-laws-of-creation.jpg" width="220" alt="Laws of Creation box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 71. Laws of Creation

*Rewrite the rules of reality. Pay the upkeep.*

Your son decrees that oaths bind, and from that epoch every oath-breaker in his world is cursed without a priest lifting a finger. A rival decrees a contrary law, and where the two meet the weaker erodes or reality cracks into a region of conflicting physics. Above them all sits you, the Creator, with passions the world can please and taboos it had better not break.

- **Twenty Laws of Nature** — no iron, eternal night over a region, souls that reincarnate, magic that demands blood, shifted gravity, reversed seasons, dreams made real, the dead who speak, metal that rusts fast. Each has a scope, a strength and exceptions.
- **Physics Rewritten** — laws reach into the sky itself. Shift gravity, reverse the seasons or lock a world's face to its star, and every value that follows from them changes too.
- **Contested Physics** — when two gods' laws contradict, they contest by strength. The weaker erodes, or the land between them becomes a phenomenon of conflicting physics.
- **Laws Need a Living Author** — every law decays without its author's essence, so the death of a god can unmake the rules of a world.
- **Global Enchantments** — eternal summer over a world, a ward against outer beings, barren wombs on an enemy world, a calm on every ocean. Gods, mage orders and foreign gods cast them and pay upkeep each epoch, and rivals can dispel them.
- **The Creator's Passions** — order, chaos, beauty, knowledge, war, mercy, creation and silence each read the world: wonders for beauty, spreading learning for knowledge, battles for war. A knowledge-loving Creator sends revelation dreams to scholars.
- **Taboos and the Watching Eye** — break a Creator's taboo, son or mortal, and wrath signs follow. Your attention is a budget: worlds far from the eye drift, their sons act more freely, and rebellion grows likelier.

**In your world:** A son of Fire cast an eternal summer over his faithful's world and paid its upkeep in essence every epoch. When a lost war drained his worshippers, his essence ran dry, the enchantment failed, and a people who had never known winter met their first.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/72-the-hungering-dark.jpg"><img src="common/assets/images/dlc-covers/72-the-hungering-dark.jpg" width="220" alt="The Hungering Dark box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/72-the-hungering-dark.jpg"><img src="common/assets/images/dlc-backs/72-the-hungering-dark.jpg" width="220" alt="The Hungering Dark box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 72. The Hungering Dark

*It eats words. It eats memories. It eats light.*

Somewhere beyond the edge of creation something is hungry, and its hunger has a shape. One eats words, and they vanish from every tongue it touches. One eats light, and a star dims in your sky. Its cults whisper false beliefs into willing ears, its breach points bleed horror into the land, and when the doom clock strikes, the apocalypse wears the face of what fed it.

- **Five Hungers** — souls, knowledge, light, names and memories. A soul-eater empties the realms of the dead, a memory-eater erodes belief in legends, a light-eater dims stars, a word-eater steals words from languages.
- **Size Matters** — a greater being reaches more regions and costs more essence or sanity to oppose.
- **Bargains with Terms** — a desperate son gains essence or a power now, and pays later with a world's sanity, one of its domains or its own true name.
- **Cults of the Void** — outer cults preach void tenets, run schemes on their master's behalf and spread its touch as a creeping void taint.
- **Horror Has a Geography** — leak gathers near gates, cults and breach points. Horror strikes the hot spots, and where leak peaks, new phenomena tear open.
- **A Doom Clock That Explains Itself** — every source of doom is traced, and the ending follows the cause. War-led doom ends in a world war called by the Calling, leak-led doom in an outer being's descent, godlessness in a twilight of fading gods.
- **Banishing the Dark** — seal the breach points, destroy the cults and starve its interest, and the being is banished, though it remembers the world. Only the Creator or a cosmic office holder can destroy one, and the price is great.

**In your world:** A desperate son bought a power from a light-eater and pledged a world's sanity in payment. The being's cult took root there, leak pooled around its shrines, and the doom clock, now led by leak, began counting toward a descent.

</td>
</tr>
</table>
</details>

<a id="chapter-x"></a>

### 🪐 X. The Cosmos

<details open>
<summary><b>Expansions 73–80</b> · <sub>8 expansions</sub></summary>

<table>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/73-clockwork-heavens.jpg"><img src="common/assets/images/dlc-covers/73-clockwork-heavens.jpg" width="220" alt="Clockwork Heavens box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/73-clockwork-heavens.jpg"><img src="common/assets/images/dlc-backs/73-clockwork-heavens.jpg" width="220" alt="Clockwork Heavens box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 73. Clockwork Heavens

*The year is as long as the orbit. The winter as harsh as the tilt.*

Every world you make now obeys its sky. Its year is set by its orbit, its day by its spin, its seasons by tilt and eccentricity, its warmth by starlight, cloud and greenhouse air. Push a moon too close and it breaks into rings. Thicken an atmosphere and the ice retreats. Nothing in the heavens is a number someone typed in. Everything has a cause.

- **Years from Orbits** — year length comes from the orbit and the mass of the system, day length from rotation, and a world old enough falls tidally locked. Eccentric orbits give a whole world one global season.
- **Climates from Physics** — warmth from starlight, reflectivity, greenhouse gases, tidal heating and volcanoes. Small hot worlds slowly lose their air, and each world's chemistry decides whether life stays microbial or climbs to sapience.
- **A Planet That Feeds Back** — more ice reflects more light and cools further until volcanoes or a brightening star break the spiral. Seas rise and fall with the ice, coasts flood or emerge, and coastal cities move.
- **Tides and Rings** — moon masses set the tides that open coasts and drive floods. A moon pulled inside its breaking distance, or shattered by a son, becomes a ring.
- **A Calendar of Shadows** — eclipses are computed from moons and orbits, and comets return on their true periods. Each culture reads each body as good, evil or neutral, and the moon strengthens divination while the comet feeds fire.
- **Born in a Disc** — each system forms around a snow line, rocky inside and icy outside. Migrating giants scatter or water the inner worlds, a bombardment era leaves craters and exotic metals, and core size sets magnetism.
- **Winters Without End** — a chaotic orbit, a natural law or a divine act can make seasons irregular, with winters lasting years and no one sure when. Cultures store grain, cook famine foods and train calendar scholars to predict them.

**In your world:** A resonance between twin suns stretched one winter across several years. The kingdom that had trained calendar scholars to predict it lived on stored grain. Its neighbour, which had mocked them, starved.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/74-starfall.jpg"><img src="common/assets/images/dlc-covers/74-starfall.jpg" width="220" alt="Starfall box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/74-starfall.jpg"><img src="common/assets/images/dlc-backs/74-starfall.jpg" width="220" alt="Starfall box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 74. Starfall

*The sky is not still. It is falling.*

Look up. Thirty-two kinds of star burn over your worlds, and none of them is forever. The heavy ones die young in a supernova and collapse into neutron stars or black holes. The middling ones swell into giants and swallow their inner worlds. Comets cross orbits, rogue worlds wander through, and somewhere an astronomer is calculating the year a stone will fall on a neighbour's kingdom.

- **Stars That Age** — mass and metal content set each star's lifetime and its stages, from young to dying, dead and reborn. Small stars burn long and dim; middling stars swell into giants, engulf their inner worlds and leave white dwarfs.
- **Dimming Suns, Shaken Faith** — as a star ages its worlds cool and ice ages grow likelier. Sun cults' piety tracks its brightness, and a dimming star breeds crises of faith and eclipse prophecies.
- **Flares and Auroras** — in any year a flare can paint auroras read as omens, mutate life, fail crops or wreck light-sail routes. Red dwarfs flare often.
- **Stones from the Sky** — comets, asteroid fields and rogue worlds cross orbits. A strike leaves a crater, regional ruin, star metal and an impact winter that fails harvests and drives species extinct. Sons can deflect or call impacts; astronomers can see them coming.
- **Twin Suns** — worlds circle one star or both, with double seasons, double-sun eclipses and a habitable band drawn by both stars together.
- **Nebulae, Nurseries and Black Holes** — nebulae slow and hide travellers, nurseries birth new stars for sons to claim, black holes send travellers home younger than their kin, wormholes open unstable roads, and asteroid fields hide void pirates.
- **Stars Made by Gods** — a star a son creates can break the laws of mass, sustained by sacredness and essence instead, and its stability rises and falls with its maker's existence.

**In your world:** Astronomers in one realm computed a comet's path onto their neighbour's lands and sent envoys to warn them. The neighbour's court distrusted the sender. The impact winter failed harvest after harvest, refugees poured over the border, and the realm that had warned them gained the prestige.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/75-worldforge.jpg"><img src="common/assets/images/dlc-covers/75-worldforge.jpg" width="220" alt="Worldforge box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/75-worldforge.jpg"><img src="common/assets/images/dlc-backs/75-worldforge.jpg" width="220" alt="Worldforge box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 75. Worldforge

*Raise the mountains. Drown the valley. Remake the world.*

Your son raises a ridge across the plain and the river turns. A valley drowns behind it, downstream fields go dry, a harbour city finds itself stranded on raised ground, and every people asks whose valley the god drowned, and why. Over centuries worlds bend further still: deserts turn green, a living planet answers every mine, and a Death god's world slowly becomes a corpse.

- **Divine Earthworks** — raise or sink land, carve or fill valleys, redirect rivers, open springs, call lava. Elevation, water and soil change for real, downstream regions gain or lose water, and the politics and the faith follow.
- **Worlds with Weight** — gravity slows armies, shortens siege-engine range and caps building height. Thin air saps endurance, toxic air breeds disease, and low-gravity worlds favour flyers and sky mounts.
- **A Planet That Feels** — a living world answers mining and clearing with quakes and hostile beasts, and reverence with fertility. Old worlds cool and wear out their soils, and a collapsing biosphere brings famine and new diseases.
- **Belief-Shaped Worlds** — worlds drift toward the faith of their peoples. A fearful people's dream world grows nightmares, a Sea god's world floods, a Death god's world turns corpse-like, a slow and contestable change you watch on a gauge.
- **Terraforming and Its Victims** — gods and advanced realms can change a world's air, water and brightness over epochs, or green a desert over centuries. Native life of incompatible chemistry suffers, and those who live off the old ecology can sabotage the plan.
- **Ends of Worlds** — shattered into an asteroid belt, swallowed by a swelling star, frozen dead under a dead sun, sunk into the void, forgotten, or transfigured into another kind of world. Each fate reaches souls, routes, exiles abroad and gods.

**In your world:** Two sons contested a valley. One flooded it to drown the other's temple. The flood cut a trade route and shifted the river, a downstream people lost its fields and followed its diaspora abroad, and the drowned temple became a site of heroquests.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/76-thirty-four-worlds.jpg"><img src="common/assets/images/dlc-covers/76-thirty-four-worlds.jpg" width="220" alt="Thirty-Four Worlds box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/76-thirty-four-worlds.jpg"><img src="common/assets/images/dlc-backs/76-thirty-four-worlds.jpg" width="220" alt="Thirty-Four Worlds box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 76. Thirty-Four Worlds

*Ocean worlds. Gas giants. Generation ships. Realms of the dead.*

On a gas giant there is no ground and falling is death, so cities float and every war is fought in the sky. On a generation ship the weather is a failing air system and revolution is called mutiny. In the realm of the dead nobody is born, and the dead live on the offerings of the living. Each world type rewrites the rules, down to whether fire can burn.

- **Thirty-Four Rulebooks** — every world type changes its ground, sky, life and warfare. Sand worlds bury cities under moving dunes and fight over water rights; ice worlds hunt through the ice and huddle round thermal vents; jungle worlds breed plague and ambushes.
- **Strange Ground** — regions become cloud bands on gas giants, decks on generation ships, organs on a living world and strata in the realm of the dead. Tidally locked worlds live along a single habitable ring.
- **Exotic Ecologies** — aerial plankton and floating flora, vent gardens under ice shells, hydrocarbon life in methane lakes, spore fogs on fungal worlds that carry both plague and dreams.
- **Wars of Other Worlds** — sky warfare alone on gas giants, three-dimensional battles under the sea, boarding actions between asteroid rocks, wars between the strata of the dead, mutiny aboard the ship.
- **No Fire without Air** — the foundations bend to the world. No fire without oxygen, no soil on asteroids, air rationed as a stock, buildings squat under the gravity of a super-earth.
- **Wealth of Strange Worlds** — iron worlds double their ore and arm everyone, diamond worlds run on the gem trade, forge-worlds poison their own soil with soot, and strong dreamers conjure materials on dream worlds at a cost to their sanity.
- **The Dead Without Scavengers** — where nothing eats carrion, the dead stay. Mummified in deserts, frozen on ice worlds with old diseases inside them, sinking into a gas giant's depths, drifting through void habitats as hauntings. Funerals become a real cost.

**In your world:** On an ice world nothing ate the fallen of an old war, so they froze where they lay. Generations later miners broke into the field, the plague sealed in the bodies woke, and a disease the world had long called eradicated walked again.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/77-rifts-and-wonders.jpg"><img src="common/assets/images/dlc-covers/77-rifts-and-wonders.jpg" width="220" alt="Rifts and Wonders box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/77-rifts-and-wonders.jpg"><img src="common/assets/images/dlc-backs/77-rifts-and-wonders.jpg" width="220" alt="Rifts and Wonders box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 77. Rifts and Wonders

*An eternal storm. A road of ghosts. Two histories, both true.*

A god dies and its corpse leaves an aura over the land. A battlefield with too many dead becomes a road the ghosts still walk. Two gods' laws collide and a valley forgets which physics it obeys. Phenomena are places where the world's rules bend, and they grow unless someone holds them back. Some are curses. Some are mines. The best are both.

- **Fourteen Phenomena** — eternal storms, time slips, leak wounds, ley flares, god-corpse auras, living fogs, crystal blooms, dead zones where nothing grows, mirror lakes, gravity wells, singing stones, permanent auroras, ghost roads and blights.
- **Born from History** — phenomena rise from rite backlash, dead gods, clashing natural laws, supernova shards, peaks of leak and the mass dead of great battles. Each remembers the event that made it.
- **Rules That Bend** — inside a phenomenon the weather can be overridden, magic thickened, sanity drained, ageing sped, fertility killed or travel blocked.
- **They Grow** — phenomena spread or fade as their intensity strains against the wards, temples and rites that contain them. Seal one with rites, with your own hand or through a son.
- **Rich and Dangerous** — harvest reagents at crystal blooms, lead pilgrims to the auroras, open gates at leak wounds. Every prize sits inside the danger.
- **Two Histories, Both True** — time slips and time gods can split a span of years into two incompatible pasts, each true to those who lived it. When Fate or a son reconciles them, one becomes history and the other legend, prophecy or madness.
- **Beyond the Land** — phenomena can hang over a whole world's sky, cover every world of a star system, run along a route between worlds or haunt an underground or afterlife stratum. A dead star-god darkens its whole system.

**In your world:** A time slip split a war between two cities into two pasts, and each city knew it had won. When Fate reconciled the branches, the losing city's victory became legend, and the veterans who still remembered it were called mad.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/78-between-the-stars.jpg"><img src="common/assets/images/dlc-covers/78-between-the-stars.jpg" width="220" alt="Between the Stars box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/78-between-the-stars.jpg"><img src="common/assets/images/dlc-backs/78-between-the-stars.jpg" width="220" alt="Between the Stars box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 78. Between the Stars

*Wait for the window. Then sail into the void.*

The worlds move, and the voyage moves with them. Sail when the orbits align and the crossing is short and cheap. Sail outside the window and your colonists eat through their provisions in the dark. Pirates wait in the lanes, gates wear thin with traffic, and along the busiest routes something new is born: a culture of the stars, with its own tongue and its own memory.

- **Launch Windows** — for sails, slingshots, sky-ships and void mounts, duration and danger follow the worlds' real positions. Migrations, invasions and trade fleets move together when a window opens. Gates, folding, dreams and bridges ignore the orbits.
- **Routes with Character** — every route has a capacity, traffic, a toll-holder and a level of piracy. Some gates open only at a solstice, and every gate wears with traffic until maintenance rites restore it.
- **Cargo and Passengers** — ships carry goods, items and relics, and passengers by class and condition. Convoys sail with escorts, and a colony ship of sick refugees brings its plague ashore.
- **Encounters in the Void** — pirates, storms, beasts, the touch of the outer dark and derelicts found adrift, rolled for every journey.
- **The River That Forgets** — some crossings strip passengers of memory and knowledge. Colonists who travel the river of the dead arrive without their history, and new legends grow in the gap.
- **Six Levels of Knowing** — every realm knows each world as unknown, rumoured, detected, observed, surveyed or mapped. Survey level gates journeys, colony plans and claims, and sky-sailing techniques raise it.
- **Cultures of the Routes** — along busy routes merchants, crews and diasporas of several worlds share values, a common tongue, the art of the routes and a history of the system, a counterweight to every world's nativism.

**In your world:** When the window opened, a fleet of refugees sailed from a plague-struck world. The sickness crossed the void with them, swept the port where they landed, and the port's realm closed the route, stranding the merchants who lived by it.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/79-deep-time.jpg"><img src="common/assets/images/dlc-covers/79-deep-time.jpg" width="220" alt="Deep Time box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/79-deep-time.jpg"><img src="common/assets/images/dlc-backs/79-deep-time.jpg" width="220" alt="Deep Time box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 79. Deep Time

*Before your first epoch, empires had already risen, fallen and been forgotten.*

Choose a prehistory in the genesis wizard and the world runs ahead without you: peoples split, languages drift into families, cities rise and fall to ruin, beasts go extinct and leave their bones in fossil beds. When you finally arrive there are dormant crowns waiting for a claimant, old roads, sacred sites, and peoples nursing grudges from wars nobody alive has fought. Fate writes it all into a legendary age.

- **A World Born with History** — run a prehistory of any length, or none and begin from your creations alone. Climate, evolution, migration, language change, faith, war and the rise and fall of realms all run in fast time.
- **What You Inherit** — language families with shared roots, ruins and lost cities, extinct species, dynasties and dormant titles, old grudges, sacred sites, old roads and diasporas. Myths are distorted memories of real prehistoric events.
- **The Legendary Age** — Fate and the chronicler receive the greatest events of the prehistory, write the world's legendary age in prose and reconcile it with the cosmology you set at genesis.
- **Fast-Forward Through Time** — run any world ahead by as many epochs as you like and read a digest of what happened. While the world races, your sons act on their goals, values and standing.
- **Every World Its Own Past** — a realm of the dead inherits souls, old judgements and lost kings; a dream world dreams its past from its dreamers and changes it as they change; a corpse-world begins with the life and death of its god.
- **Voyage Histories** — a generation ship begins with its departure, generations aboard, mutinies, lost decks and myths of the destination. With no source world, it invents a lost origin reachable only by legend or later discovery.
- **Mirrors and Canon** — mirror worlds are born in pairs that share one mirrored past. Worlds that already have written lore keep their canon, with a deep past drawn from that lore alone.

**In your world:** A prehistory left behind the dormant crown of a kingdom that fell before the first epoch. Generations into play, an ambitious lord claimed it. The neighbours who still nursed the old kingdom's grudge marched, and a war began over a history nobody alive had lived.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/80-the-turning-wheel.jpg"><img src="common/assets/images/dlc-covers/80-the-turning-wheel.jpg" width="220" alt="The Turning Wheel box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/80-the-turning-wheel.jpg"><img src="common/assets/images/dlc-backs/80-the-turning-wheel.jpg" width="220" alt="The Turning Wheel box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 80. The Turning Wheel

*This age will end. Another will begin. You will remember.*

In a cyclic cosmos the doom clock does not end the world. It turns it. The age collapses, the world is remade over the ruins of the last, and the old roles come back wearing new faces: a betrayer, a reborn champion, a founding couple. The peoples of the new age half-remember the old one from broken texts. You remember all of it.

- **Linear or Cyclic** — choose at genesis whether your cosmos ends or turns. Every cosmos runs on a straight line unless you choose the wheel.
- **The Turning of the Age** — in a cyclic cosmos the apocalypse remakes the world instead of closing it. Ruins and relics of the prior age remain, and much of its knowledge is lost.
- **Echoes of the Last Age** — archetypal roles return as story arcs seeded to recur: the reborn champion, the betrayer, the founding couple.
- **Souls Returning** — souls of the prior age may be reborn into their echoes, so the hero of one age can wake into the hero's role of the next.
- **Half-Remembered Texts** — prophecies and legends of the old age survive as fragmentary, unreliable accounts, so every age misremembers the last in its own way.
- **Tune the Wheel** — the length of each cycle and how much survives each turning are yours to set.

**In your world:** The last age fell to a betrayer. In the next, a corrupted fragment of the old prophecy survived, a young heir's life began to follow the betrayer's path, and the soul that had betrayed the last age was found to be his.

</td>
</tr>
</table>
</details>

<a id="chapter-xi"></a>

### 📖 XI. Knowledge and Eras

<details open>
<summary><b>Expansions 81–85</b> · <sub>5 expansions</sub></summary>

<table>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/81-sparks-of-genius.jpg"><img src="common/assets/images/dlc-covers/81-sparks-of-genius.jpg" width="220" alt="Sparks of Genius box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/81-sparks-of-genius.jpg"><img src="common/assets/images/dlc-backs/81-sparks-of-genius.jpg" width="220" alt="Sparks of Genius box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 81. Sparks of Genius

*One discovery can change everything. One great mind can make it.*

A city survives a siege, and its builders master fortification. A plague kills the last physicians of a river kingdom, the books burn with the library, and its medicine falls. Every people now climbs its own tree of eighteen branches at its own pace, pulled by need, pushed by contact, and sometimes thrown forward by one great mind who changes everything.

- **Every People Knows What It Knows** — one people works metal at level two while its neighbour is at five. Branches split into techniques like horse archery, quarantine, crop rotation, skysteel, the dome and eclipse prediction, and armies, buildings and cures require them.
- **Learning by Surviving** — need and history drive research. War pushes warfare, plague pushes medicine, famine pushes farming. Survive a siege and fortification leaps ahead; a great trial advances law, and a great debt speeds banking.
- **The Civic Tree** — codified law, bureaucracy, census, coinage, banking, double-entry, joint-stock companies, universities, monasticism, logic and empiricism. Civic techniques unlock governments, offices, taxes and ideologies.
- **Institutions That Spread** — universities, printing, banking and bureaucracy rise where wealth and scholars meet, then sweep outward by border, trade and shared faith. Refuse them and every later discovery costs more.
- **Knowledge That Travels and Dies** — ideas cross with trade, teachers, captives, refugees and plundered libraries, and dug-up artifacts can be reverse engineered. Guilds hoard secrets until spies steal them. Kill the practitioners and burn the books, and a people forgets.
- **Great People, Great Ages** — scholars, generals, prophets, engineers, merchants and explorers rise to change everything. Firsts, victories and wonders earn golden ages; failure brings dark ages and the chance of a heroic recovery.
- **Dangerous Knowledge** — forbidden arts, high biomancy and star-caging risk leaks, freed beasts, plague and backlash. Alchemists set fires, engineers cause explosions, summonings go wrong, and the world may turn against the researcher.

**In your world:** A trading city cleared its forests for farms and ran out of fuel for its iron. A rival in skysteel took the city, its scribes died in the sack, and with the library unstaffed its medicine collapsed. The next plague finished what the war began.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/82-the-scholars-lamp.jpg"><img src="common/assets/images/dlc-covers/82-the-scholars-lamp.jpg" width="220" alt="The Scholar's Lamp box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/82-the-scholars-lamp.jpg"><img src="common/assets/images/dlc-backs/82-the-scholars-lamp.jpg" width="220" alt="The Scholar's Lamp box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 82. The Scholar's Lamp

*The physicians bled the patient. The patient died. Who was wrong?*

Your physicians are certain that bleeding cures fever. They are wrong, and the plague dead prove it every year. In a quarantined monastery the monks survive, the anomaly is noted, and a heterodox doctor with a theory of contagion gains disciples. The cult condemns him. His books move on the black market. A generation later the old truth falls, and the death toll bends downward.

- **True and False Theories** — "the world is a disk", "souls are reborn", "the stars are gods". Across eight fields from medicine to magic, every claim has a hidden truth set by how this cosmos really works, and techniques built on false ones fail.
- **Anomalies and Paradigm Shifts** — wrong predictions pile up until they outweigh what a theory explains. Then rival theories contest it, decided by evidence, by universities and cults, and by the stubbornness or curiosity of the leading scholars.
- **Faith and Heresy** — cults endorse or condemn theories. A condemned true theory sends its scholars to heresy trials; a blessed false one is propped up for generations. Sons can reveal the truth, winning scholars and angering cults.
- **Schools of Thought** — masters and disciples form lineages that teach better, feud with rivals and keep heterodox knowledge alive through persecution.
- **Examinations and Credentials** — realms recruit officials by examination in law, writing, lore and the canon. Merit replaces birth, until credentials outnumber offices and frustrated graduates become counter-elites.
- **Free Minds and Fleeing Scholars** — academic freedom feeds research and debate. Suppress it and scholars migrate to freer patrons, taking their knowledge with them.
- **Printing and Numbers** — printing makes books cheap and ideas fast, and censored books turn into contraband and heresy. Cultures count in base ten, twelve, twenty or sixty, and the zero sharpens accounts, engineering and star charts.

**In your world:** A city's physicians bled their patients, and the plague that survived the treatment came back hardier. A rival university that held the contagion theory found the cure first, traded it for a treaty clause and earned a great person of its own.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/83-steam-and-lightning.jpg"><img src="common/assets/images/dlc-covers/83-steam-and-lightning.jpg" width="220" alt="Steam and Lightning box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/83-steam-and-lightning.jpg"><img src="common/assets/images/dlc-backs/83-steam-and-lightning.jpg" width="220" alt="Steam and Lightning box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 83. Steam and Lightning

*No ceiling. No end. Only what your history can reach.*

The river town that once wove by hand now runs water-frame mills, and the weavers who lost their work are burning them. Later the telegraph means news no longer waits for a courier, and later still a rocket waits for its launch window. No era cap holds your worlds back. Only their history decides how far they go, and whether they go at all.

- **Seven Eras, No Ceiling** — ancient, medieval, gunpowder, industrial, electrical, information and advanced. Genesis sets only where a world starts and how fast it learns, and a world may stay pre-modern for ever.
- **The Industrial Turn** — steam, coke smelting, machine tools, railways, factories and canned food remake the economy, with unemployment, swelling cities, pollution and new classes of workers, engineers and financiers.
- **Wars of a New Age** — musketeers, line infantry, artillery, rifles, armoured vehicles and aircraft. Firepower makes numbers count for more, and industrial armies march on fuel and ammunition.
- **The World Gets Smaller** — telegraph and telephone collapse the delays of distance, radio and mass media sway public opinion, and antibiotics and the green revolution change who lives and who eats.
- **Rockets Between Worlds** — non-magical spaceflight joins the routes between worlds, bound by the same launch windows as every other ship. Nuclear-analogue power, genetic engineering and artificial minds wait further up the tree.
- **Magic and Machine** — iron and electricity disrupt certain rites, some theories unite the two, and a son can forbid gunpowder on a world as a law of nature. Mass media speed secularisation, and outer beings take an interest in dangerous research.
- **Guarded by Plausibility** — a mortal's acts reach a region, a realm's a world. World-shaking techniques need programmes spanning generations that pass through visible stages others can sabotage, and no single invention ever ends the cosmos.

**In your world:** A realm began a programme for a weapon of the advanced era. Every stage left traces: incidents, rumours, a climbing doom clock. Its rivals read the signs, a coalition formed, and their spies burned the works before the final step.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/84-fateweaver.jpg"><img src="common/assets/images/dlc-covers/84-fateweaver.jpg" width="220" alt="Fateweaver box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/84-fateweaver.jpg"><img src="common/assets/images/dlc-backs/84-fateweaver.jpg" width="220" alt="Fateweaver box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 84. Fateweaver

*The world writes its own stories. Fateweaver makes them sing.*

Your world goes quiet for a century, and the storyteller notices. Raids grow likelier, a beast stirs, an ambitious claimant appears. When the world burns too hot it eases off, and good harvests and peace envoys return. It never overrides cause and effect. It only tilts the odds, so the dying king and his two sons arrive when the story needs them.

- **Four Storytellers** — steady, rising, cyclic or chaotic. Each sets a tension curve for its world, with golden ages and crises in waves by default. Below the curve, raids, plagues, comets and claimants come more often; above it, healers and good harvests.
- **Variety and Spotlight** — the storyteller remembers what just happened and avoids repeating it, and turns its eye to neglected regions and characters so the chronicle reaches them too.
- **Storylets at the Gate** — a stranger at the gate claiming to be the lost heir, a famine and a granary key, a heretic book in the abbey, a duel challenge at the wedding. Each casts real characters and offers two to four choices.
- **Choices in Character** — sons and other living agents choose for themselves. Everyone else chooses by personality, beliefs and passions, so the same storylet branches differently for a coward and a zealot, and follow-ups arrive epochs later.
- **Twenty Kinds of Arc** — rise and fall, revenge, redemption, tragedy, forbidden love, mentor and heir, exile and return, the fall of a house, apotheosis. The world detects them: a dream of vengeance plus a murdered brother begins a revenge arc.
- **The Drama Manager** — it opens chances for a stalled arc's next beat, the mentor's death or the final confrontation, but never forces an outcome. Arcs can fail, twist or end in irony, and those endings are recorded too.
- **Counterpoint and Payoff** — a rival's rise keeps time with the hero's fall. Prophecies, omens and dreams are logged as setups and steered toward payoff or subversion, so the chronicle reads as authored though it emerged.

**In your world:** A storylet brought a stranger to the gate claiming to be the lost heir. The old king, proud and suspicious, turned him away. An exile-and-return arc opened that day, and two epochs later the stranger came back at the head of an army.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/85-into-the-dark.jpg"><img src="common/assets/images/dlc-covers/85-into-the-dark.jpg" width="220" alt="Into the Dark box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/85-into-the-dark.jpg"><img src="common/assets/images/dlc-backs/85-into-the-dark.jpg" width="220" alt="Into the Dark box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 85. Into the Dark

*Pack the torches. Count the rations. Not everyone comes back.*

Six of them go down into the vault: a scout, a guide, a healer, a fighter, a scholar to read the inscriptions, a porter with the rope. Every room eats torchlight and rations. In the dark the danger rises, the stress mounts, and somewhere below the healer turns paranoid while the fighter finds a courage he never knew. The ones who return come back changed.

- **Parties with Roles** — scouts, guides, healers, fighters, scholars and porters set what an expedition can scout, heal, carry, fight and read. A missing role shows as a risk before anyone sets out.
- **Light and Hunger** — torches, lamps, magic light, rations, ropes, picks, keys and medicine are all counted, and every room spends them. Darkness raises danger and surprise, cold and hunger bring frostbite and fatigue, and camping risks a night ambush.
- **Afflictions and Virtues** — past a breaking point, stress turns a member paranoid, hopeless, selfish or abusive, or courageous, focused or stalwart. Which way they break depends on their character and conviction.
- **Quirks That Stay** — "afraid of the deep", "knows the old tunnels", "loves the sea", "eats anything". Places leave marks on people that change how they live long after they come home.
- **Sites with Rooms** — towers, vaults, lairs, monasteries, fortresses, cave complexes and dungeons hold rooms of traps, guardians, puzzles and hazards, each with its wounds and loot, and a history of everyone who held them.
- **Excavations in Five Stages** — ruins, crashed vessels, god corpses and the sites of a previous creation are dug stage by stage with lore, engineering or spellcraft. They yield artifacts, lost techniques, regalia and old route maps, and threaten curses, freed spirits and collapse.
- **Battlefields That Remember** — old earthworks, haunted mass graves and fields of salvage persist where the wars were fought, waiting for the next party.

**In your world:** An excavation of a previous creation's ruin reached its fourth stage and found a book of a lost technique. The scholars began to study it, but the dig had also freed a sealed spirit, and the party's scholar came home afraid of the deep.

</td>
</tr>
</table>
</details>

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## Quick start

Four commands from a fresh clone to a living world:

```sh
make env           # creates .env with a generated media secret and the worker URL
make claude-token  # signs in with your Claude subscription and stores the token in .env
make up            # the whole stack: backend, web, media store and the image worker
make down          # stops it again; volumes are kept
```

Open **http://127.0.0.1:8080**, walk through the genesis wizard, name your Creator, choose the language of your lore, and draw your first son.

`make up` picks the image worker for the machine. On Apple Silicon it starts the native MLX worker in the background (`make worker-start`, `make worker-stop`, `make worker-status`; log in `data/run/image-worker.log`) and points the backend container at `http://host.docker.internal:8100`. Anywhere else it starts the `image-worker` container on the NVIDIA GPU (profile `gpu`).

`make claude-token` runs `claude setup-token`, asks you to paste the printed token with hidden input, checks it with a one-word Claude Haiku reply and only then writes it to `.env` (mode 600). The token never appears on screen twice and never goes into git.

### Requirements

- [uv](https://docs.astral.sh/uv/) (Python 3.13 is installed by uv)
- Node.js 24 and npm
- A Claude subscription and the [Claude Code CLI](https://docs.claude.com/en/docs/claude-code) for the token
- Docker with Compose v2.24 or newer, for the containerized setup
- Optional: an Apple Silicon Mac (native `mlx` image worker) or an NVIDIA GPU with the NVIDIA Container Toolkit (`diffusers` image worker)

### Ports

Every port binds to `127.0.0.1` by default (`AERONA_BIND_ADDRESS`), and every published port can be moved in `.env`.

| Service | Address | Setting |
|---|---|---|
| Web app (Docker) | http://127.0.0.1:8080 | `AERONA_WEB_PUBLISHED_PORT` |
| Backend API | http://127.0.0.1:8000/api | `AERONA_PORT`, `AERONA_BACKEND_PUBLISHED_PORT` |
| Vite dev server | http://127.0.0.1:5173 | |
| Image worker | http://127.0.0.1:8100 | `AERONA_IMAGE_WORKER_PORT`, `AERONA_IMAGE_WORKER_PUBLISHED_PORT` |
| MinIO for local development | 127.0.0.1:9000 | `AERONA_MINIO_DEV_PORT` |
| MinIO console | http://127.0.0.1:9001 | `AERONA_MINIO_CONSOLE_PORT` |

### Make targets

| Target | What it does |
|---|---|
| `make env` | Creates `.env` from `.env.example` with a generated media secret |
| `make claude-token` | Stores a verified Claude subscription token in `.env` |
| `make up` / `make down` | Starts or stops the whole stack with the right image worker |
| `make install` | Installs backend and frontend dependencies |
| `make dev` | Backend with reload and the Vite dev server |
| `make check` | Source rules, lint, types and tests |
| `make test`, `make lint`, `make typecheck` | The individual checks |
| `make typegen` | Regenerates the typed frontend client from the OpenAPI schema |
| `make rules` | Source rules and version consistency check |
| `make version v=<x.y.z>` | Sets the version across the project |
| `make migration name=<name>` | Creates an Alembic migration |
| `make docker-up`, `make docker-up-gpu`, `make docker-up-console`, `make docker-down` | Docker stack variants |
| `make minio` | MinIO for local development |
| `make image-worker`, `make image-worker-test` | Runs or tests the image worker |
| `make worker-start`, `make worker-stop`, `make worker-status` | Native image worker in the background |
| `make migrate-legacy`, `make legacy-rule-map` | Legacy world migration |

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## Configuration

Every setting is an environment variable. `.env` is ignored by git; `.env.example` lists every one. The main ones:

| Variable | Meaning |
|---|---|
| `CLAUDE_CODE_OAUTH_TOKEN` | Subscription token for the Claude Agent SDK (see below). Never use an API key. |
| `AERONA_DATA_DIR` | Database, backups and (with the file media store) images. Docker always uses the `aerona-data` volume. |
| `AERONA_LLM_ENABLED` | `false` runs the world engine without any LLM calls. |
| `AERONA_IMAGE_WORKER_URL` | Base URL of the image worker for a backend running on the host. Empty disables image generation. |
| `AERONA_DOCKER_IMAGE_WORKER_URL` | Worker URL inside the backend container. `make up` sets it; the default is the `image-worker` container. |
| `AERONA_BIND_ADDRESS` | Host address Docker publishes ports on (default `127.0.0.1`). |
| `AERONA_IMAGE_WORKER_*` | Image worker settings: backend, model, timeouts, idle unload. |
| `AERONA_MEDIA_*` | Media store: backend (`file` or `s3`), endpoint, bucket, credentials, region, TLS. See [Media store](#media-store). |

### Claude token

Weavers of the Void runs on your Claude subscription through the Agent SDK, never an API key. Create a long-lived token once:

```sh
claude setup-token
```

Put the printed token into `CLAUDE_CODE_OAUTH_TOKEN` in `.env`, or let `make claude-token` do it. The backend hands the token to every Agent SDK call, on the host and in Docker alike. Without a token, a backend on the host falls back to this machine's `claude` login; Settings → Maintenance → Health shows which one is in use.

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## Local development

```sh
make install
make dev
```

- Backend: http://127.0.0.1:8000 (API under `/api`, with reload)
- Frontend: http://127.0.0.1:5173 (Vite proxies `/api` to the backend)
- Checks: `make check` (source rules, lint, types, tests) and `make image-worker-test`

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## Docker

```sh
make docker-up
```

This builds and starts:

- `backend`: FastAPI on Python 3.13, running as a non-root user. SQLite and backups live in the `aerona-data` volume.
- `minio`: the S3-compatible media store. Images live in the `aerona-media` volume. It has no host port; the backend reaches it on the internal network.
- `minio-init`: a one-shot job that creates the bucket with `mc` and keeps it private. The backend starts after it finished.
- `web`: the built frontend served by nginx at http://127.0.0.1:8080. nginx proxies `/api` to the backend with SSE buffering off.

On an NVIDIA host, `make docker-up-gpu` also starts the `image-worker` container (profile `gpu`); the backend reaches it at `http://image-worker:8100` by default. Model weights are downloaded on the first image into the `aerona-models` volume, never into the image.

`make docker-down` stops everything. Volumes are kept.

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## Media store

Images never touch a plain directory directly: every read and write goes through one `MediaStore` interface with two implementations.

| Backend | `AERONA_MEDIA_BACKEND` | Where objects live |
|---|---|---|
| File | `file` (default for local development and tests) | `$AERONA_DATA_DIR/media` |
| S3 | `s3` (Docker uses it) | A MinIO bucket, or any S3-compatible service |

Object keys:

- `originals/<image-id>.<ext>` for every uploaded or generated image. The image row stores the key, the content type, the size and the SHA-256 checksum. Identical content is stored once: an upload whose checksum is already known reuses the object.
- `thumbnails/<width>/<image-id>.webp`, rendered with Pillow on the first request for that width and then served from the store.

The browser only reaches images through the backend at `/api/media/<file>?w=<width>`, which streams the object with its content type, an `ETag` and immutable caching headers. MinIO is never exposed.

An object is deleted only when neither the live world, nor any backup, nor an open discovery world references it, so restoring a backup always finds its images. World packages (`.aerona`) are gzip-compressed tar archives holding a manifest, the database and the referenced objects, streamed to and from the store one object at a time.

### Media settings

| Variable | Meaning |
|---|---|
| `AERONA_MEDIA_BACKEND` | `file` or `s3`. |
| `AERONA_MEDIA_ENDPOINT` | S3 endpoint as `host:port` or a full URL. Empty means AWS S3. |
| `AERONA_MEDIA_BUCKET` | Bucket name (default `aerona-media`). The backend creates it if it is missing. |
| `AERONA_MEDIA_ACCESS_KEY`, `AERONA_MEDIA_SECRET_KEY` | Credentials. Docker also uses them as the MinIO root user, so both are required for `docker compose`. |
| `AERONA_MEDIA_REGION` | Region (default `us-east-1`). |
| `AERONA_MEDIA_SECURE` | `true` uses HTTPS for a `host:port` endpoint. |

### MinIO console

`make docker-up-console` also starts a small proxy that publishes the MinIO console on http://127.0.0.1:9001 only (profile `media-console`, port `AERONA_MINIO_CONSOLE_PORT`).

### MinIO for local development

`make minio` runs MinIO for a backend started with `make dev`. It uses a native `minio` binary when one is on the `PATH` (data in `data/minio`), otherwise it runs only the MinIO container with ports bound to `127.0.0.1`. Then set in `.env`:

```sh
AERONA_MEDIA_BACKEND=s3
AERONA_MEDIA_ENDPOINT=127.0.0.1:9000
AERONA_MEDIA_ACCESS_KEY=aerona
AERONA_MEDIA_SECRET_KEY=<at least 8 characters>
```

The default image is the community build `pgsty/minio`. Set `AERONA_MINIO_IMAGE` to use another one.

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## Image worker

Every record in Weavers of the Void gets a painting. The image worker is a separate service behind a small HTTP contract; the backend owns the queue, so manual requests always go ahead of bulk ones, and images are only ever added, never replaced.

### On macOS

Docker on macOS cannot use the Apple GPU (containers get no Metal access), so the `mlx` worker runs natively on the host. `make up` starts it for you; to run it alone:

```sh
make worker-start   # background, or `make image-worker` in the foreground
```

It listens on http://127.0.0.1:8100 and loads `mflux-community/z-image-turbo-mflux-q4` (about 6 GB, downloaded on the first image into the Hugging Face cache). Point the backend at it:

- Docker backend: `AERONA_IMAGE_WORKER_URL=http://host.docker.internal:8100`
- Local backend: `AERONA_IMAGE_WORKER_URL=http://127.0.0.1:8100`

The model loads on the first job and is released after `AERONA_IMAGE_WORKER_IDLE_UNLOAD_SECONDS` without work.

### Worker backends

| Backend | Where | Model |
|---|---|---|
| `mlx` | Apple Silicon host (`make image-worker`) | `mflux-community/z-image-turbo-mflux-q4` |
| `diffusers` | NVIDIA container (profile `gpu`) | `unsloth/Z-Image-Turbo-unsloth-bnb-4bit` |
| `fake` | Tests and CI | Deterministic gradient PNG |

### Worker HTTP contract

| Method | Path | Result |
|---|---|---|
| `GET` | `/health` | Backend, model, loaded state, queue length |
| `POST` | `/jobs` | `{prompt, width, height, steps, seed, priority}` → `{job_id}`; `manual` jobs run before `bulk` ones |
| `GET` | `/jobs/{id}` | Job status and last progress event |
| `GET` | `/jobs/{id}/events` | SSE: `queued`, `loading`, `encoding`, `step`, `decoding`, `done`, `error`, `cancelled` |
| `GET` | `/jobs/{id}/image` | The PNG of a finished job |
| `DELETE` | `/jobs/{id}` | Cancels a queued job |

One job runs at a time. A job that exceeds its time limit fails, and the worker restarts its model process.

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## Backups and world packages

Your world is never one bad epoch away from ruin.

- **Before every epoch** the backend takes a consistent SQLite backup. The ten most recent epoch backups are kept, every tenth epoch is kept forever as a milestone, and up to thirty manual backups and five safety backups of each kind sit beside them. Every count is a rule in Settings → World Rules.
- **A second copy, elsewhere.** Point `AERONA_SECONDARY_BACKUP_DIR` (or the secondary target in Settings → Data) at another disk, and every backup is mirrored there too, with its own retention.
- **Restore in one click** from Settings → Data, with a typed confirmation for anything that replaces your world.
- **Share a world** as a versioned `.aerona` package, with or without its images. A package received from someone else opens three ways:

| Mode | What happens |
|---|---|
| **Open read-only** | Browse the other world beside your own as a guest, then return to yours |
| **Merge into my world** | Its entities, worlds, places, bonds, beliefs and chronicle lines are carried into yours; images are renamed when they collide, and a summary shows exactly what was added and skipped |
| **Replace my world** | It takes the place of your world, after you type `REPLACE` |

Settings → Maintenance → Health reports the backend status, database integrity, backups and recent errors at a glance.

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## Architecture

```mermaid
flowchart TB
    subgraph Browser
        UI[React 19 · TanStack Router and Query<br/>shadcn/ui · map · graph · 3D cosmos]
    end
    subgraph Web [web · nginx]
        NG[Static app + /api proxy<br/>SSE buffering off]
    end
    subgraph Backend [backend · FastAPI]
        API[API routers] --> SV[Services]
        SV --> EN[World engine<br/>deterministic phases]
        SV --> AG[Agents<br/>sons · Fate · chronicler · council]
        SV --> EP[Epoch orchestrator<br/>jobs · resume · cancel]
        AG --> PR[Prompt catalog]
        AG --> TL[Son tools]
        EN --> RL[Rules registry]
        EP --> BUS[Event bus → SSE]
        SV --> DB[(SQLite WAL)]
    end
    MS[(MinIO / file<br/>media store)]
    IW[Image worker<br/>MLX or diffusers]
    CL[Claude Haiku<br/>via Agent SDK]
    UI --> NG --> API
    BUS --> UI
    SV --> MS
    SV --> IW
    AG --> CL
```

| Layer | Choice |
|---|---|
| Backend runtime | Python 3.13 with `uv` |
| HTTP | FastAPI and Uvicorn, with an OpenAPI schema that drives the typed frontend client |
| Realtime | Server-Sent Events with `Last-Event-ID` reconnect |
| Database | SQLite in WAL mode through SQLAlchemy 2 async and `aiosqlite`, one serialized writer |
| Migrations | Alembic |
| Validation | Pydantic v2 for API schemas, tool inputs and structured LLM outputs |
| Agents | `claude-agent-sdk` on your Claude subscription, Claude Haiku on every path |
| Jobs | In-process asyncio job manager with persisted job rows: resumable and cancellable |
| Frontend | React 19, TypeScript and Vite |
| Routing and data | TanStack Router and TanStack Query, SSE-driven invalidation |
| API client | `openapi-typescript` and `openapi-fetch`, generated from the backend |
| UI | shadcn-admin on shadcn/ui, Radix and Tailwind v4; `lucide-react` icons; recharts |
| Map, graph, cosmos | Canvas over `d3-delaunay` Voronoi; `react-force-graph`; `@react-three/fiber` and `drei` |
| Quality | pytest, Vitest, Testing Library, Playwright; ruff, mypy strict, eslint, stylelint, prettier |

### Repository layout

```
aerona/
  backend/src/aerona/
    api/          routers and schemas, one router per domain
    services/     application services used by the API
    engine/       the deterministic world simulation and its phases
    agents/       sons, Fate, chronicler, bard, council, genesis, deepener and more
    tools/        son and mortal tools: schema, gating, cost and effect
    epoch/        epoch orchestration, concurrency and resume
    prompts/      every prompt, as typed Jinja templates
    rules/        the tunable balance registry
    catalog/      static game data: rarities, powers, domains, climates, stars, worlds
    language/     procedural languages and naming
    cartography/  map generation
    db/           tables, repositories, sessions
    jobs/ events/ media/ imaging/ migration/
  frontend/src/
    features/     one folder per screen: pantheon, son, chronicle, map, cosmos, graph ...
    components/   ui, layout, typography and domain components
    routes/       thin TanStack file routes
  image-worker/   the MLX and diffusers image service
  deploy/         Dockerfiles and nginx
  docs/           architecture, decisions and the full business-logic spec
```

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## Engineering principles

Weavers of the Void holds itself to a short list of rules, enforced by tooling rather than goodwill:

1. **Self-describing code.** Names and structure carry the meaning; `scripts/check_source_rules.py` enforces the source rules in CI and in the test suite.
2. **English everywhere** in code, identifiers, UI copy, prompts and file names. The lore itself speaks the language you choose.
3. **One home for every prompt.** Every LLM prompt lives in `backend/src/aerona/prompts/`, rendered from a typed context object.
4. **No magic numbers.** Every balance number is a rule in the registry, editable at runtime from Settings → World Rules.
5. **Claude Haiku on every path.** Every model resolution and fallback ends at Haiku, and a test asserts it.
6. **Automatic and in your hands.** Every mechanism runs on its own, can be triggered or overridden by the player, and has a UI surface. A test checks that every API route has a frontend caller.
7. **No visual drift.** One theme file, sizes only in `components/ui`, typography components for every text role, and a Playwright test that checks control heights, overlaps and overflow on every route at desktop and mobile widths.

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## Bringing a legacy world

A world from the legacy Node app (`~/aerona/data`) can be carried into Weavers of the Void in one step. The plan and its limits are in [docs/migration-plan.md](docs/migration-plan.md).

```sh
make migrate-legacy LEGACY=~/aerona/data TARGET=data/aerona.db MIGRATE_FLAGS=--dry-run
make migrate-legacy LEGACY=~/aerona/data TARGET=data/aerona.db
```

Or directly: `cd backend && uv run python -m aerona.migration.legacy --legacy ~/aerona/data --target <path> [--dry-run] [--media file|s3] [--replace] [--media-dir <dir>] [--report-dir <dir>]`.

- The legacy database is read only through a consistent snapshot (SQLite backup API), so the legacy app may keep running. Nothing in the legacy folder is written.
- The legacy epoch must be finished: a paused epoch or a paused turn stops the migration.
- The target is always a fresh database built by the Alembic migration, with `lore_language = turkish`. An existing target is refused unless `--replace` is given. The work happens in `<target>.partial` inside one transaction; any failure removes the partial file and every image object the run uploaded.
- Images are copied from the legacy image folder into the media store (`--media file` writes to `--media-dir`, by default `media/` next to the target; `--media s3` uses the `AERONA_MEDIA_*` settings). Identical files are stored once (SHA-256). Thumbnails are rebuilt on demand.
- `--dry-run` converts into a throwaway database, uploads nothing and only writes the report.
- Every run writes `migration-report.json` and `migration-report.md` (to `--report-dir`, or next to the target): counts per table, renamed records, everything that could not be placed, tags that were not understood and how every rule override was mapped. A real run also keeps the legacy undo ledger as a read-only `legacy-ledger.json`.

The legacy vocabulary lives only in `backend/src/aerona/migration/legacy/schema_map.json`. Its rule section is regenerated from `docs/spec/rules-registry.json` and the current registry with `make legacy-rule-map`.

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## Troubleshooting

| Symptom | Fix |
|---|---|
| Sons do not act and the health panel shows no Claude login | Run `make claude-token`, or put a `claude setup-token` token into `CLAUDE_CODE_OAUTH_TOKEN` in `.env`, then restart the backend |
| The UI says image generation is disabled | `AERONA_IMAGE_WORKER_URL` is empty. Set it to the worker address and start the worker |
| No images on a Mac in Docker | Docker on macOS has no Metal access. Use `make up` or `make worker-start`, which runs the MLX worker natively, and check `make worker-status` and `data/run/image-worker.log` |
| The first image takes minutes | The model is downloading (about 6 GB on Apple Silicon). Later images start as soon as the model is loaded |
| `docker compose` refuses to start | Both `AERONA_MEDIA_ACCESS_KEY` and `AERONA_MEDIA_SECRET_KEY` are required; `make env` generates them |
| A port is already in use | Move it with the `AERONA_*_PUBLISHED_PORT` and `AERONA_*_PORT` settings in `.env` |
| You want the world to turn without any agent | Set `AERONA_LLM_ENABLED=false`; the engine simulates every epoch on its own |
| The backend stopped mid-epoch | Start it again. Epochs and long jobs are persisted and resume where they stopped |

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## FAQ

**Do I need an Anthropic API key?**
No. Weavers of the Void runs on your Claude subscription through the Claude Agent SDK, and every call uses Claude Haiku.

**Does my world leave my machine?**
Your database, backups and images stay on your disk. Only the agents' prompts and replies travel to Claude.

**Are the expansions extra?**
No. The Loom and all 85 expansions are part of every world from the first epoch.

**Can I play in Turkish?**
Yes. Choose Turkish as the lore language in the genesis wizard, and every chronicle, name and legend is written in it; even the engine's own chronicle lines are localised by an agent. The interface itself is English.

**Can I undo a mistake?**
Yes. Every action lands in Fate's ledger and can be undone, and every epoch has a backup to restore.

**Can I change the rules of the world?**
All of them. More than 3,300 balance rules are editable live from Settings → World Rules, every mechanic can be triggered or suppressed by hand, and every prompt is visible under Settings → Prompts.

**Is the simulation random?**
It is seeded. The same world with the same seed produces the same history, which makes every epoch reproducible.

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## Documentation

| Document | What it covers |
|---|---|
| [Architecture](docs/architecture.md) | Stack, layers, async model, design system and deployment |
| [Decisions](docs/decisions.md) | Every architectural decision and why it was made |
| [Migration plan](docs/migration-plan.md) | Carrying a legacy world into Weavers of the Void |
| [Data model](docs/spec/01-data-model.md) | Every table and field |
| [World core](docs/spec/02-world-core.md) | The world, entities, bonds and the chronicle |
| [Rules registry](docs/spec/03-rules-registry.md) · [JSON](docs/spec/rules-registry.json) | All 3,300+ tunable rules |
| [Engine core](docs/spec/04-engine-core.md) · [Deep mechanics](docs/spec/05-deep-mechanics.md) | The world simulation |
| [Cosmos and the strange](docs/spec/06-cosmos-and-strange.md) · [Cosmos types](docs/spec/14-cosmos-types.md) | Stars, worlds, travel, horror and the beyond |
| [Gods and progression](docs/spec/07-gods-and-progression.md) | The Creator, sons, reputation, goals, death and resurrection |
| [Agents and tools](docs/spec/08-agents-and-tools.md) · [Prompts](docs/spec/09-prompts.md) | Every agent role, every son tool, every prompt |
| [Epoch pipeline](docs/spec/10-epoch-pipeline.md) | The life of an epoch, resume, backups and the live stream |
| [API](docs/spec/11-api.md) · [Frontend](docs/spec/12-frontend.md) | Every route and every screen |
| [Depth expansion](docs/spec/13-depth-expansion.md) · [Interconnection](docs/spec/13-interconnection.md) · [Coverage](docs/spec/13-coverage.md) | The mechanics behind the 85 expansions and how they weave together |
| [Expansions](docs/spec/15-dlc-ideas.md) | The Loom and all 85 expansions in full |
| [Mechanic coverage](docs/spec/coverage.md) | Traceability from every mechanic to its module, trigger, control, screen and test |

---

<p align="center">
  <img src="frontend/public/brand/logo-64.png" alt="" width="40"><br>
  <sub><b>Weavers of the Void</b> · You are the Creator. The rest writes itself.</sub>
</p>
