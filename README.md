<a id="top"></a>

<p align="center">
  <img src="frontend/public/brand/logo-512.png" alt="Weavers of the Void" width="240">
</p>

<h1 align="center">Weavers of the Void</h1>

<p align="center">
  <b>The self-writing world.</b><br>
  You are the Creator. Your sons are gods. Every age, the world writes its own history, and you hold every lever.
</p>

<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/version-0.1.0-d4af37?style=flat-square">
  <a href="LICENSING.md"><img alt="License: AGPL-3.0" src="https://img.shields.io/badge/license-AGPL--3.0-2e7d32?style=flat-square"></a>
  <img alt="Expansions" src="https://img.shields.io/badge/expansions-99%20included-7b3fe4?style=flat-square">
  <img alt="Engine steps" src="https://img.shields.io/badge/engine%20steps-505-5b2bb5?style=flat-square">
  <img alt="Rules" src="https://img.shields.io/badge/tunable%20rules-20%2C700%2B-4b2a8c?style=flat-square">
  <img alt="Agent tools" src="https://img.shields.io/badge/agent%20tools-775-3b1f73?style=flat-square">
  <img alt="Python" src="https://img.shields.io/badge/python-3.13-3776ab?style=flat-square&logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-async-009688?style=flat-square&logo=fastapi&logoColor=white">
  <img alt="React" src="https://img.shields.io/badge/React-19-61dafb?style=flat-square&logo=react&logoColor=black">
  <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-strict-3178c6?style=flat-square&logo=typescript&logoColor=white">
  <img alt="Models" src="https://img.shields.io/badge/agents-any%20model-d97757?style=flat-square">
  <img alt="Docker" src="https://img.shields.io/badge/docker-compose-2496ed?style=flat-square&logo=docker&logoColor=white">
  <img alt="Local first" src="https://img.shields.io/badge/local--first-single%20player-1e1b4b?style=flat-square">
</p>

<p align="center">
  <a href="#quick-start"><b>Quick start</b></a> ·
  <a href="#the-pitch">The pitch</a> ·
  <a href="#new-in-this-edition">What's new</a> ·
  <a href="#god-cards">God cards</a> ·
  <a href="#your-hand-on-everything">Control</a> ·
  <a href="#the-lore-book-and-the-codex">Book and Codex</a> ·
  <a href="#the-complete-edition-the-loom-and-99-expansions">99 expansions</a> ·
  <a href="#a-tour-of-the-app">The app</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="#license">License</a>
</p>

<br>

<table>
  <tr>
    <td align="center" width="25%"><b>🜂 You create</b><br><sub>Begin from one idea, draw god cards, answer prayers, and create, edit, hold or delete anything the world holds.</sub></td>
    <td align="center" width="25%"><b>✦ Gods decide</b><br><sub>Every son is an agent with passions, rivals and 330 divine tools. Notable mortals act for themselves with 445 more.</sub></td>
    <td align="center" width="25%"><b>⚙ The world turns</b><br><sub>505 deterministic engine steps live through fifty years of history, year by year and season by season, between every divine turn.</sub></td>
    <td align="center" width="25%"><b>📜 Fate remembers</b><br><sub>Every change is recorded with its cause. Fate judges the age, writes the chronicle, and the world becomes a book and a Codex.</sub></td>
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

<p align="center"><sub><b>The Loom and 99 expansions, all included and all deepened.</b> <a href="#the-cover-wall">See all 100 covers →</a></sub></p>

---

<details open>
<summary><b>Contents</b></summary>

- [The pitch](#the-pitch)
- [New in this edition](#new-in-this-edition)
- [Why Weavers of the Void](#why-weavers-of-the-void)
- [Meet the cast](#meet-the-cast)
  - [Twenty-seven ways to begin](#twenty-seven-ways-to-begin)
- [How an age unfolds](#how-an-age-unfolds)
  - [A taste of an age](#a-taste-of-an-age)
- [God cards](#god-cards)
  - [What rarity unlocks](#what-rarity-unlocks)
  - [A card for every being](#a-card-for-every-being)
- [Your hand on everything](#your-hand-on-everything)
- [The record of everything](#the-record-of-everything)
- [The lore book and the Codex](#the-lore-book-and-the-codex)
- [Features](#features)
- [What the gods can make](#what-the-gods-can-make)
- [The cosmos](#the-cosmos)
- [Goals and glory](#goals-and-glory)
- [A tour of the app](#a-tour-of-the-app)
- [The agents](#the-agents)
- [By the numbers](#by-the-numbers)
- [The complete edition: The Loom and 99 expansions](#the-complete-edition-the-loom-and-99-expansions)
  - [The Loom](#the-loom) · [The fifteen chapters](#the-fifteen-chapters) · [The cover wall](#the-cover-wall) · [Every expansion](#every-expansion)
  - [I](#chapter-i) · [II](#chapter-ii) · [III](#chapter-iii) · [IV](#chapter-iv) · [V](#chapter-v) · [VI](#chapter-vi) · [VII](#chapter-vii) · [VIII](#chapter-viii) · [IX](#chapter-ix) · [X](#chapter-x) · [XI](#chapter-xi) · [XII](#chapter-xii) · [XIII](#chapter-xiii) · [XIV](#chapter-xiv) · [XV](#chapter-xv)
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
- [License](#license)

</details>

## The pitch

**Weavers of the Void is a living universe simulator that writes its own history.** You do not write the story. You set it in motion, and you keep the last word.

You play the Creator at the dawn of a cosmos. Begin from a sentence of your own or one of twenty-seven templates, in any age from the first stone tools to travel between the stars. Your sons are **god cards**, drawn in six rarities from *Common* to *Mythic*, and each one is an agent with its own passions, rivals, domains and a toolbox of 330 divine powers. Once per epoch every son wakes, reads the world and acts: raising mountains, founding cults, sending dreams to prophets, breeding beasts, cursing bloodlines and scheming against the rest of the pantheon. The world's notable mortals, its heroes, prophets and rulers, decide for themselves too.

Between their turns a **deterministic world engine** takes over. Five hundred and five steps live through fifty years of history, year by year and season by season: mortals are born, marry, quarrel and die; peoples migrate, tongues drift apart, harvests fail, sicknesses spread and fade, markets rise and crash, empires overreach, armies march on what they can carry and heroes walk the paths of myth. The agents choose what they want; the engine decides what really happens. Then **Fate** judges the age, decides what becomes canon and writes the chronicle.

Nothing is scripted and nothing is lost. Every change the world makes is recorded with its cause, every number can tell you why it is what it is, and the whole history leaves as a **lore book** (HTML and PDF) and a **Codex** (Markdown and ZIP) you can take into your own tools.

> *Every thread is connected. Now you can see them all.*

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## New in this edition

The edition since the last README is the largest yet. Every one of the 99 expansions was widened and deepened, and the world gained a full record of itself.

| | What arrived |
|---|---|
| 📚 **Every expansion deepened** | All 99 expansions were read again value by value and widened through 704 numbered additions, each with its engine steps, agent tools, god levers, screens, book and Codex entries and tests. See [Every expansion](#every-expansion). |
| 🧾 **The record of everything** | Every happening is told from typed roles and facts across 4,524 kinds, and every change the engine makes is recorded with the happening that caused it. Rewind any record to any moment, and see the atlas as it stood then. See [The record of everything](#the-record-of-everything). |
| 🃏 **A card for every being** | The Creator, the sons, foreign gods, mortals, beasts, spirits and cosmic beings each have a collectible card, with sealed packs that tear open and cards you can turn over and save as images. See [A card for every being](#a-card-for-every-being). |
| 🌳 **Family trees** | Every mortal's kin is drawn as a tree in its entry, in the book and in the Codex: ancestors and descendants to a chosen reach, with spouses, stepkin and bonds of care, each named by their place to the mortal. |
| 🪟 **One entry window for every thing** | Every node opens in one window, grouped into ten parts with search and deep links, the god's controls among them. See [Your hand on everything](#your-hand-on-everything). |
| ⏳ **Begin in any age** | Thirteen technology ages, from before metal to matter shaped at will, and twenty-seven templates. A world that begins in an age makes, heats, names and lives like that age. |
| ✋ **Make anything by hand** | Every kind of thing can be made with its values chosen first: shaped mortals, sons summoned to a design, raised regions, founded settlements, celestial bodies, spirits, laws of nature, faiths and outer beings. |
| 🕳 **The world below** | A map for every stratum of the deep, cities drawn in their own stratum, and armies, convoys and roads that travel below the surface. |
| 📈 **Usage** | A token usage page for every language model call: trends, breakdowns by step, model and role, and a searchable call log, counted the same way for every call. |
| ⚖ **Balanced on lived worlds** | Long engine runs and fresh worlds lived epoch after epoch tuned famine, plague, war, mishaps and the ordinary death rates against each other, so worlds grow and suffer at believable rates. |

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## Why Weavers of the Void

- **A story nobody wrote.** No script, no event deck, no quest list. Every legend in your chronicle grows out of causes you can trace.
- **Gods with minds of their own.** Your sons are agents, not dice rolls. They plan, keep grudges, argue in council and sometimes rebel.
- **The lore goes where your idea goes.** Sea myth, vampire courts, a cosmic horror or a generation ship: the world begins from your own words and follows them, never toward a house style.
- **Depth all the way down.** Ninety-nine expansions of interlocking mechanics, from the soil under a field to the dimensions beyond the sky, all running at once in every world.
- **Total control, zero lock-in.** Create, edit, hold or delete anything the engine makes. Every rule is tunable, every act undoable, every prompt visible, and your world lives on your disk.
- **History you can hand over.** The whole world leaves as a designed lore book and a Codex, with nothing cut short.
- **Beautiful by default.** A celestial interface, a living map, a 3D cosmos, collectible cards and a painting for every record, made on your own machine.

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## Meet the cast

| | Who | What they do |
|---|---|---|
| 🜂 | **The Creator** | You. Name yourself at genesis, choose the language of your lore and shape the cosmos with essence. Your mood follows the world, your cult rises or fades, and mortals can pray to you directly. |
| ✦ | **The Sons** | God cards in six rarities, each an agent with loyalty, ambition, anger and mercy. They create, bless, curse, wage war, scheme against each other and sometimes rebel against you. They can die, and they can be brought back. |
| ⚖ | **Fate** | The impartial judge of every age. Fate canonises or rejects creations, records canon facts, opens and closes tales, fulfils prophecies and keeps the ledger of every act. |
| ☄ | **Foreign gods** | Powers from beyond your pantheon, awake or asleep, with their own strength, attitude and gifts. Ally with them, war with them, or devour them. |
| 👁 | **Mortals and peoples** | Heroes, prophets, rulers and heretics, and the peoples, settlements, realms, factions and faiths they build. The notable ones are agents of their own; all of them pray, remember, believe the wrong things and write history of their own. |

### Twenty-seven ways to begin

The genesis wizard opens every world in seven stages: a template, the Creator, the seed and tone, the first world, the peoples, the cosmos and its telling, and the first sons. A template is only a starting point; every value it sets can be changed in the later stages, or you can start from a blank page.

| Myth and fantasy | Strange worlds | Ages of making |
|---|---|---|
| **Dark fantasy** | **Cosmic horror** | **Gunpowder age** |
| **Mythic age** | **Drowned world** | **Age of engines** |
| **Fairy tale** | **Desert world** | **Electric age** |
| **Star myth** | **Long winter** | **Information age** |
| **Primordial dawn** | **Sky islands** | **Advanced age** |
| **Court intrigue** | **Many suns** | **Interstellar age** |
| **Without magic** | **Layered realms** | **Beyond age** |
| **After the fall** | **Living world** | **Made minds** |
| | **Dreaming world** | **After abundance** |
| | **Generation ship** | |

Every world chooses its tone, magic, danger, the texture of its tongues, its first peoples, the shape of its first world and of its cosmos, and its technology age:

> Before metal is worked · The first metal smelted into tools · Bronze is worked · Iron is worked · Steel and written law · Powder, guns and star-shaped forts · Printing and natural philosophy · Steam power and machines · Electricity and messages by wire · Computation and mass media · Split matter, rockets and machines that think · Travel between the stars · Matter shaped at will and works the size of stars

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## How an age unfolds

```mermaid
flowchart LR
    C([The Creator]) -->|draws, commands, blesses, edits| S
    subgraph S [The gods and the notable act]
        S1[Son agents<br/>330 divine tools]
        S2[Mortal agents<br/>445 mortal tools]
    end
    S -->|creations, miracles, schemes, choices| E
    subgraph E [The world turns]
        E1[505 deterministic steps]
        E2[20,700+ tunable rules]
    end
    E -->|50 years of history| F
    subgraph F [Fate judges]
        F1[Verdict on every creation]
        F2[The chronicle is written]
    end
    F -->|records, images, the book and the Codex| C
```

1. **A backup is taken.** Your world is never one bad epoch away from ruin.
2. **The Creator moves first.** Draw sons, bless or punish them, answer prayers, convene the council, or reach into the engine and pull any lever by hand.
3. **The sons take their turn.** Every son is an agent. They read a typed view of the world, call their tools and pay for every act in essence.
4. **The notable mortals decide.** Heroes, prophets and rulers choose for their own lives with tools of their own.
5. **The world turns.** A seeded, reproducible simulation runs every mechanic over fifty years: nature, bodies, households, societies, economies, wars, faiths, magic, the gods and the cosmos itself. What the agents chose plays out here, by the world's rules.
6. **Fate judges.** An impartial agent weighs the age, canonises or rejects creations, closes tales and writes the chronicle.
7. **The world remembers.** Every change lands in the record with its cause, every act of yours in Fate's ledger, undoable. Paintings are made locally for new records, and the book is rebuilt for the next time you open it.

Every epoch streams live to the browser: watch each step complete, each tool call land and each verdict arrive as it happens. The length of an epoch is itself a rule.

### A taste of an age

<sub><i>An illustrative excerpt in the style of the chronicle. Every world writes its own, in its own images and its own language.</i></sub>

> **Epoch 14 · The Ninth Age of the River Kingdoms**
>
> In the forty-first year the monsoon failed over the eastern coast, and the granaries of Tessaly were empty by midwinter. The Merciful Son, whose domain is Harvest, sent a dream to Ilsa, a miller of the river villages. Ilsa woke speaking of a buried spring, and a cult was born before the thaw.
>
> The Unyielding, a rival son, did not forgive the gift. They told the hungry lords of Tessaly that the river villages hoarded grain, and by summer the banners were raised. The war lasted nine years. The spring was filled with stones, and Ilsa was tried as a witch at the crossing they had saved.
>
> *Fate's verdict:* the cult of the buried spring is canon. The war is canon. The Merciful Son's loyalty to the Creator rises; the Unyielding gains renown and loses mercy. A tale stays open: **the spring is said to run again beneath the stones.**

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## God cards

Every son is drawn as a card. Rarity sets how much a son can do in a turn, how fast their essence returns, how strong they are born and how high their power can climb. Every number below is a default rule you can retune in Settings → World Rules.

| Rarity | Draw odds | Action points | Essence per epoch | Born with stats | Power cap | Turn steps |
|---|---:|---:|---:|---|---:|---:|
| ⬜ **Common** | 50% | 2 | 8 | 17–39 | 2 | 12 |
| 🟩 **Uncommon** | 26% | 3 | 12 | 26–50 | 4 | 15 |
| 🟦 **Rare** | 14% | 4 | 17 | 36–62 | 6 | 18 |
| 🟪 **Epic** | 7% | 5 | 24 | 48–75 | 8 | 21 |
| 🟧 **Legendary** | 3% | 6 | 32 | 61–88 | 10 | 24 |
| 🟥 **Mythic** | ascension only | 7 | 44 | 75–100 | 12 | 27 |

The genesis wizard lets you choose your first sons: one to five of them, of any rarity up to Legendary. Sons grow in level and renown as they act, and a son who reaches **level 9** with **90 renown** can **ascend** to the next rarity for 90 essence. **Mythic** is never drawn: it is earned only by ascension. Mortals can climb too: deify a hero, and they join the pantheon as a god of their own.

### What rarity unlocks

| From | The son can make | And gains the power to |
|---|---|---|
| **Common** | Places, resources, settlements, species, peoples, mortals, legends, traditions, artworks, dishes, and the kinds of vehicles, soldiers, equipment and buildings | Read and reflect, remember, speak, tend kin and hear prayer |
| **Uncommon** | Items, structures, languages, cults, factions, laws, spirits, houses, treaties, ideologies, rites, theories, art forms and networks | Influence any record, mark a chosen one, curse, work miracles and cloak themselves as a spirit |
| **Rare** | Celestial bodies, knowledge, vessels, diseases, titles, beasts, phenomena and leagues | Send dreams, call down disasters, grant knowledge, incite wars, take a mortal's life, declare holy worlds, sign treaties between worlds and war on foreign gods |
| **Epic** | Regions, prophecies, events, armies, polities and cosmic beings | Seal gates and leaks, rekindle dead stars, raise thrones of power and magic sites, and open roads between worlds |
| **Legendary** | Laws of nature | Transform and destroy, bear divine children, open cosmic channels, birth whole worlds, raise phenomena and open breaches for outer beings |
| **Mythic** | Outer beings and trade routes | Hang new stars and put out old ones, set new galaxies, gather clusters, bring dimensions into being and shape galaxies and dimensions |

### A card for every being

The **Cards** page lays out every character of the cosmos as a collectible card: the Creator, the sons and the foreign gods on their own shelf, then the mortals, beasts, spirits, outer beings and cosmic beings of every world. A card's rarity is read from its power against the rarity bands of the world rules, and rarity is the metal of its frame, from slate, bronze and silver to amethyst, gold and prismatic, with a holographic foil from Epic up.

- **Front and back.** The front carries the likeness edge to edge with level or power, name, title, kind, domains, the epochs of birth and fall on clock dials and the four values around its rarity seal. The back holds every value, every power and the being's account.
- **Binder, deck and inspector.** Browse a binder, swipe a deck, or open an inspector that brings the next cards up on its own. Filter by deck, rarity, world, living or fallen.
- **Sealed packs.** New cards wait in sealed packs that tear open with a reveal.
- **Keep them.** Save the front or the back of any card as an image.

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## Your hand on everything

The engine runs every mechanic on its own, and none of it is out of your reach.

- **Create, edit, hold and delete.** Every table and typed thing the engine creates or changes has god levers to create it, edit every value of it, hold it against the engine and delete it. More than 2,600 levers sit in one action catalog, each proven to run by a test.
- **Hold what is canon.** Lock a character, a city, a value or any other node, and no engine step may create, change or delete what is tied to it. The world keeps living around what you hold.
- **One entry window for every node.** The Creator, every son, foreign god, world, moon, star and every entity opens in the same window, its sections grouped into ten parts: Overview, Body and mind, Life and kin, Society and rule, Economy and goods, Faith and powers, War and intrigue, Land and sky, Lore and records, and the god's controls. Search jumps to any section, and every section can be linked to.
- **Every record of a node.** An "Every record" section in each entry window lets you add, edit and remove any row tied to it, whatever mechanic made it.
- **Run, suppress, retune, pin.** Every mechanic can be run now, switched off for a while, retuned through its rules or pinned to a value.
- **Make it your way.** Every kind of thing can be made by hand with its values chosen first, or by a son you send to do it.
- **Undo anything.** Every act of yours lands in Fate's ledger with its cause, ready to undo, with notes and bookmarks.

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## The record of everything

A world that keeps its own history keeps all of it.

- **Every happening, told.** Births, battles, trials, voyages, plagues and councils are told from typed roles and facts, across 4,524 kinds of happening, in the order they happened and with the places they happened in. Duels and engagements are told round by round.
- **Every change, explained.** Every write the engine makes is recorded with the happening that caused it and the terms that made its number, so you can ask any value why it is what it is.
- **Witnesses and rumours.** Those who were present remember; those who heard it second hand carry rumours, with the distortions rumours have, and tellings can contradict each other.
- **Rewind any record.** The past of any record is rebuilt at any moment from its changes. A timeline scrubber walks through it, and the atlas can show the world as it stood at that moment.
- **Event pages and history everywhere.** Every happening has its page, every entry window its history, and record search reaches them all.
- **Your pen on the record.** God levers set down, rewrite, hold and strike facts, steps, witnesses and changes, and revert a change the world made.

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## The lore book and the Codex

Everything the world becomes leaves the app in two designed forms, and **nothing is ever cut short**.

| | Format | What it is |
|---|---|---|
| 📖 **The lore book** | HTML and PDF | A designed, illustrated book to read, present and share: every node in its own entry with labelled values, the chronicle in full, and the "Records of the Cosmos" appendix for what belongs to no single node. |
| 🗂 **The Codex** | Markdown and ZIP | A tidy lore archive with a page for every record, ready for your wiki, document system or writing tools. |
| 📦 **The world package** | `.aerona` | The whole world, with or without its images, to keep, move to another machine or send to a teammate. |

The book draws what words cannot: the terrain map of every world, a plan of every city, the strata of the deep, the heavens, coats of arms and every mortal's family tree. Every kind of node, the Creator, the sons, foreign gods, worlds, stars and every entity, renders its typed sections in both. The book is built once per change of the world and warmed after each epoch, so it opens at once.

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## Features

### A world that lives on its own
- **505 engine steps** for mortals, households, demography, settlements, ecology, climate, the deep, disasters, sickness, trade, markets, production, factions, institutions, law, diplomacy, espionage, warfare, faith, spirits, magic, heroes, monsters, realms, the afterlife, the pantheon, the sky, galaxies and dimensions.
- **A simulation, not a script.** An epoch is fifty years lived through sampled years and real seasons. Rates are per year and per head, and loops have their delays, so a world grows, stalls and recovers like a real one.
- **Deterministic and reproducible.** The same world and the same seed produce the same history, step for step. Every read is ordered, so a world never depends on a query plan or a machine.
- **Conservation everywhere.** People, goods, coin and souls are counted to the last one. Nothing is made from air, and goods move only through a logged ledger.
- **The Why of Everything.** Hover any number and see exactly what made it so.
- **The Harshness Dial.** Heroic, realistic or brutal: one dial sets how deadly wounds, infection, disease, famine, childbirth and battle are.

### Gods that think
- **God cards in six rarities**, from reading and reflection up to hanging new stars and bringing dimensions into being.
- **330 son tools and 445 mortal tools**, every one run to success by a test through the real tool runtime.
- **Passions and reputation.** Loyalty, ambition, anger and mercy drive every son. Mortals love, fear or forget them. Rebels rise, and the Creator's hand can fall.
- **Forty-seven divine domains**, from sea, fire and storm to memory, oath, sleep, machines, information and science. Every domain bends the world its own way, and every domain has a price.
- **The council of heaven.** Even gods must vote. Even gods must scheme.
- **Talk to your sons.** Open a chat with any son between epochs, in character.

### Fate, the chronicler
- **An impartial judge** for every age: verdicts, canon facts, open tales and fulfilled prophecies.
- **Chronicler, bard and deepener**: agents that turn raw history into legend, epic and ever richer lore, and restore lost chronicles.
- **Chroniclers of the world.** The historians who write a people's past are mortals of that world, not names on a page.
- **Voices of the peoples**: every people tells the story of the gods its own way.

### Languages and lore
- **Procedural languages** with sound change, dialects, contact, drift and death. Every word enters a tongue through its own history, and every name means something.
- **Lore in your language**: English or Turkish, chosen once when the Creator is born and carried into every prompt.
- **Lore that follows the seed.** No prompt pushes a look, a theme or a conflict your seed did not ask for; the world's images come from your words, its own canon and what the model invents.
- **Prayers, dreams, manifestations and threats**: mortals talk to the gods, and the gods answer.

### An interface worth living in
- **Twenty-six screens and ten settings tabs**, from the Pantheon, the Cards and the Chronicle to the living Map, the Cities on their hexes, the 3D Cosmos, the Heavens and the knowledge graph.
- **Real-time everywhere.** Server-Sent Events stream every step, every tool call and every verdict.
- **Every value is readable and editable.** All rules are tunable live, and every value any screen shows can be changed.
- **A command palette** that reaches every record and every screen from the keyboard.
- **A celestial design system**: deep indigo and gold, gilded frames, six rarity metals, light and dark themes, built for phone widths up, with accessible roles and labels.

### Paintings for every record
- **Any image model** paints the Creator, the sons, foreign gods, worlds and entities from prompts the agents write: a cloud model through an API key, or the local image worker.
- **Your visual style.** The style is chosen per world and applied when the image is made, never written into the lore.
- **Apple Silicon or NVIDIA**: native MLX on a Mac, a CUDA container everywhere else, one HTTP contract for both.
- **Your gallery, your disk**: weights live in a local volume, images in your own media store.

### Built to be trusted
- **Local-first and single-player.** Your world lives in SQLite on your disk.
- **Backups before every epoch**, versioned `.aerona` world packages, and crash-safe, resumable jobs.
- **Any model you have.** A paid subscription you log in to (Claude, ChatGPT, Google AI or GitHub Copilot), an API key of a cloud provider through the Bifrost gateway, or a model server of your own; every role keeps its own ordered chain of models, and the Usage page counts the tokens of every call.
- **Engine-only mode.** Set `AERONA_LLM_ENABLED=false` and the world turns on pure simulation.

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## What the gods can make

Forty-five kinds of record, every one a living part of the simulation, every one with its own values, bonds, history and portrait:

| Land and sky | Life | Society | Mind and spirit | Power | Made things |
|---|---|---|---|---|---|
| Region | Species | People | Language | Faction | Item |
| Place | Beast | Mortal | Legend | Polity | Artwork |
| Resource | Disease | Settlement | Tradition | House | Art form |
| Structure | | Title | Cult | Army | Dish |
| Trade route | | Event | Spirit | Treaty | Vessel |
| Celestial body | | Prophecy | Knowledge | Law | Vehicle type |
| Natural law | | Network | Theory | Ideology | Kind of soldier |
| Phenomenon | | | Rite | League | Equipment model |
| Outer being | | | | | Building type |
| Cosmic being | | | | | |

### Forty-seven domains

Every son and every foreign god holds domains, and every domain bends the world in its own way:

> Sea · Fire · Earth · Sky · Storm · Death · Life · Dream · Time · Light · Shadow · War · Craft · Knowledge · Love · Trickery · Hunt · Plants · Bone · Blood · Sound · Stone · Ice · Madness · Trade · Road · Plague · Harvest · Moon · Sun · Star · Lies · Oath · Memory · Hunger · Glass · Salt · Ash · Border · Sleep · Technology · Machines · Cities · Industry · Information · Space · Science

### Twenty-three branches of knowledge

> Agriculture · Metallurgy · Seafaring · Writing · Architecture · Medicine · Magic · Warfare · Astronomy · Trade · Sky navigation · Shipbuilding · Gate lore · Pathfinding · Void living · Immortality · Biomancy · Forbidden lore · Civics · Law · Natural history · Language lore · Mathematics

### Thirty-two creature traits

> Flies · Venomous · Eats souls · Radiant · Splits to breed · Hive mind · Stone skin · Turns back time · Shapeshifter · Reads minds · Armoured · Burrows · Lives in water · Amphibious · Hunts in packs · Ambush hunter · Regrows wounds · Poisonous flesh · Breathes fire · Breathes frost · Hears its way · Camouflaged · Breeds in swarms · Long-lived · Mimic · Sees spirits · Eats iron · Crop pest · Plague bearer · Sacred · Horned · Tailed

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## The cosmos

Real astronomy and pure fantasy share one sky, and **every type is a mechanic, never a label**. A star sets the heat, the harvest, the life capacity and the sanity of everyone beneath it, and decides what it leaves behind when it dies. A world type sets its ores, disasters, seasons, gravity, air and hidden routes. Above the stars sit galaxies, clusters and layered dimensions, each with its own kinds.

<details open>
<summary><b>32 star types</b></summary>

| Main sequence | Giants | Young and changing | Remnants | Many suns | Fantastic |
|---|---|---|---|---|---|
| Yellow dwarf | Yellow giant | Protostar | White dwarf | Twin star | Dead star |
| Blue star | Red giant | Wolf-Rayet star | Neutron star | Triple star | Black sun |
| Blue-white star | Blue giant | Carbon star | Pulsar | | Broken star |
| White star | Red supergiant | Variable star | Magnetar | | Reborn star |
| Yellow-white star | Blue supergiant | | Black hole | | Chained star |
| Orange dwarf | Hypergiant | | Star remnant | | Watching star |
| Red dwarf | | | | | |
| Brown dwarf | | | | | |

</details>

<details open>
<summary><b>37 world types</b></summary>

| Classic | Real astronomy | Unusual | Divine, dead and made |
|---|---|---|---|
| Ordinary world | Super-earth | Crystal world | Realm of the dead |
| Ocean world | Ice giant | Living planet | Corpse-world |
| Sand world | Hot giant | Dream realm | The god's palace |
| Ice world | Iron world | Mirror world | Generation ship |
| Lava world | Diamond world | Void pocket | Forge-world |
| Gas giant | Greenhouse world | Fungal world | Made world |
| Ringed world | Dwarf world | Shattered world | |
| Asteroid belt | Chthonian world | Hollow world | |
| Tidally locked world | Steam-ocean world | | |
| Archipelago world | Jungle world | | |
| | Ice-shell world | | |
| | Methane world | | |
| | Rogue world | | |

Moons are worlds too: Europa-like moons are ice-shell worlds, Titan-like moons methane worlds, Io-like moons lava worlds, and a moon's orbit is always around its planet.

</details>

<details>
<summary><b>28 galaxy types, 13 kinds of cluster and 29 dimensions</b></summary>

| Galaxies | Clusters and the large scale | Dimensions |
|---|---|---|
| Spiral · Barred spiral · Grand-design spiral · Flocculent spiral · Lenticular · Elliptical · Giant elliptical · Dwarf elliptical · Dwarf spheroidal · Irregular · Dwarf irregular · Ring · Peculiar · Starburst · Active · Quasar host · Low surface brightness · Ultra-diffuse · Living · Dead · Shattered · Forged · Dreaming · Mirror · Crowned · Hollow · Ember · Veiled | Galaxy group · Local group · Poor cluster · Rich cluster · Supercluster · Filament · Wall · Void · Crown cluster · Drowned cluster · Forge cluster · Dream cluster · Mirror cluster | Prime · Parallel · Mirror · Pocket · Bubble universe · Brane · Higher-dimensional space · Antimatter · Quantum branch · Time-reversed · Compactified · Astral plane · Ethereal plane · Dream · Shadow · Spirit realm · Fey realm · Elemental plane · Celestial realm · Infernal realm · Abyssal realm · Limbo · Far realm · Clockwork plane · Plane of chaos · Underworld · Divine domain · Void between · Made realm |

</details>

<details open>
<summary><b>16 ways between worlds</b></summary>

| Old roads | Bodies and beings | Made crossings | The far scale |
|---|---|---|---|
| Ancient gate | Ridden crossing | Light sail | Galactic gate |
| Divine bridge | Carried within a being | Slingshot orbit | Filament lane |
| Dream journey | Crossing of the dead | Rocketry | Dimensional rift |
| Wormhole | | Space folding | Planar door |
| | | Void ark | |

</details>

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## Goals and glory

Every world earns a **score** from fifteen parts, can chase **scenarios** for points, and every milestone earns an **achievement**, once, forever. Sons grow in level, stars and rarity along the way.

<table>
<tr>
<td valign="top" width="45%">

**Fourteen scenarios and one of your own**

- Keep doomsday away
- Unite all peoples in one faith
- Rekindle the lost star
- A many-world cosmos, every world alive
- An age of unbroken peace
- A civilization reaching for the stars
- A loyal pantheon
- New lands on the map
- A golden age
- An age of wonders
- Bridge the galaxies
- An age of learning
- Teeming life
- The Creator's faithful
- A goal of your own, on any of sixty measures

</td>
<td valign="top" width="55%">

**Fifty-eight achievements, each in three tiers**

Many skies · Constellation · Peopled skies · Moons in orbit · Rekindled star · Many galaxies · Galaxy clusters · Many dimensions · Rifts opened · Cosmic beings · Across the galaxies · Trade between galaxies · Many kinds of life · Beasts of the wild · Spirits abroad · A species awakened · Many peoples · Crowded world · Settled lands · Realms rise · Empire · Golden age · Height of civilization · Treaties signed · Trade routes · Babel · Someone called you · The Creator's cult · The word came true · Many faiths · One god, many peoples · A mortal made divine · Crowded pantheon · A mighty son · Return from death · The Creator's hand · Other gods · A store of knowledge · Theories · Works of art · The arts · Legends · Traditions · Rule of law · Wonders · Collections · Saga completed · Heroes returned · Interstellar traveller · First explorers · Sensed world · Vessels · The weapons fell silent · God of epochs · Ancient · The Creator at work · Master of many deeds · Miracles

</td>
</tr>
</table>

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## A tour of the app

| | Screen | What you find there |
|---|---|---|
| **Pantheon** | **Overview** | The state of your cosmos at a glance: epoch, doomsday clock, essence, peoples, wars and the latest verdicts |
| | **Epoch** | Run, stop and resume the epoch, or let one son act, with every step and every turn streamed live |
| | **Pantheon** | Your sons, their cards, storylines and rivalries; foreign gods beside them |
| | **Cards** | Every god, mortal, beast, spirit and being as a collectible card: search, swipe, turn over and save |
| | **Prayers** | Wishes from sons and mortals awaiting your answer |
| | **Council** | Councils of the pantheon: motions, votes and verdicts |
| | **Goals** | Scenario goals, score and achievements |
| **World** | **Cosmos** | Stars, worlds, moons, routes, voyages and foreign gods, in 2D and 3D |
| | **Heavens** | Dimensions, clusters, galaxies, rifts, cosmic beings and phenomena |
| | **Map** | The living Voronoi map: regions, settlements, peoples, roads, wars and every stratum of the deep |
| | **Cities** | Every town on its hexes and every land on its tiles, drawn from the engine, with your hand on each |
| | **Atlas** | Every record of the world by type and family, each opening in its entry window |
| | **Network** | The knowledge graph of records and their bonds |
| | **Interconnections** | How every mechanic feeds the others: the subsystem matrix and the links of each mechanic |
| | **Wars** | Wars, armies, battles, sieges, captives and tributes |
| | **Economy** | Trade routes, market prices, materials, coins, loans and debts |
| | **Kinds** | Every kind of thing the peoples make and hold: goods, dishes, drinks, dress, crafts, games, professions and more |
| **History** | **Chronicle** | Epoch by epoch, the history Fate has written |
| | **Languages** | Dictionaries, language families and knowledge |
| | **Gallery** | Every image of the world, and the ones still missing |
| **Records** | **Ledger** | Your actions with undo, notes and bookmarks |
| | **Usage** | Token usage of every language model call: trends, breakdowns and the full call log |
| | **Notifications** | What happened while you were away |
| **System** | **Settings** | Appearance, Game, Records, Data, World rules, Engine, Fate, Prompts, Images and Maintenance |
| | **Design reference** | Every component and text role, in both themes |
| | **Genesis** | Create a new world, its Creator and the first sons |

Every node opens in its entry window, so you can follow a line of causes from a ruler to a sword to the god who forged it without losing your place.

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## The agents

Twenty-nine agent roles, each on the model its role is given under Models, every prompt in one typed catalog:

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

The agents choose intent; the engine decides outcome. An agent can surprise the world, but it cannot break its rules: every tool checks its inputs, pays its cost and acts through the same engine the world uses.

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## By the numbers

| | |
|---:|---|
| **99** | expansions plus **The Loom**, all included and all deepened |
| **100** | painted covers, one for The Loom and each expansion |
| **505** | deterministic engine steps |
| **20,700+** | tunable rules, editable live |
| **2,600+** | god levers in the action catalog |
| **330** | divine tools for the sons |
| **445** | tools for mortal agents |
| **4,524** | kinds of happening, told from roles and facts |
| **999** | tables in the world's database |
| **29** | agent roles |
| **195** | prompt templates in one catalog |
| **45** | kinds of record |
| **47** | divine domains |
| **37** | world types |
| **32** | star types |
| **28** | galaxy types |
| **29** | kinds of dimension |
| **32** | creature traits |
| **23** | branches of knowledge |
| **16** | ways to travel between worlds |
| **27** | genesis templates |
| **13** | technology ages to begin in |
| **14** | scenarios, plus one of your own |
| **58** | achievements, in 174 tiers |
| **6** | god card rarities |
| **26** | screens, plus ten settings tabs |
| **2** | lore languages: English and Turkish |
| **0** | API keys required |

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## The complete edition: The Loom and 99 expansions

<p align="center">
  <img src="common/assets/images/collectors-edition.jpg" width="520" alt="The Weavers of the Void collector's edition box on a display pedestal">
</p>

<p align="center"><sub><b>The Collector's Edition</b> · the base experience and all 99 expansions in one box</sub></p>

Weavers of the Void ships as the complete edition. **The Loom** and all **99 expansions** across fifteen chapters are fully integrated into the engine, the agents and the interface. There is nothing to unlock, nothing to install and nothing to wait for: every mechanic below runs in every world from the first epoch, and every one of them can be tuned, triggered and inspected from the app.

### The Loom

<table>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/00-the-loom.jpg"><img src="common/assets/images/dlc-covers/00-the-loom.jpg" width="220" alt="The Loom box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/00-the-loom.jpg"><img src="common/assets/images/dlc-backs/00-the-loom.jpg" width="220" alt="The Loom box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

*Every thread is connected. Now you can see them all.*

Before the gods walk and the armies march, the world needs a loom. Pull any thread and feel the whole cloth move. A queen's fever, a failed harvest, a god's grudge: each is a cause with a name, and each effect can show you its reason. The Loom is the heart beneath every expansion: every value has something that sets it and something that feels it, and every change the world makes is written down with its cause.

- **The Why of Everything** — hover over any number in the world and read what made it so: a wound, a law, a festival, this season's weather, a god's curse. Twenty-seven kinds of cause, from wounds, laws and weather to blessings, curses, rifts and your own hand, each named, each with its own span of time.
- **Chains of Consequence** — every battle, death and betrayal records its cause. Fate writes "because the ruler lost a hand at Varn", and chapters from wedding to schism gather the moments into a history you can browse by figure, place or kind.
- **Every Change Has Its Happening** — every write the engine makes is tied to the happening that caused it and the terms that made its number, so the past of any record can be rebuilt at any moment.
- **Nothing Lost, Nothing Made from Air** — people, goods, coin, souls and divine essence are counted to the last one, every turn. A soldier who marches home was first taken from their village, and every death becomes a soul that goes somewhere.
- **No Idle Numbers** — a son's mercy, the world's danger, the Creator's passions, a betrayal that starts a war. Values the world once only stored now move it, and every link between systems must have something that sets it and something that feels it.
- **Your Hand on Every Lever** — every mechanic answers to five commands: run it now, suppress it for epochs, edit what it controls, retune its rules, pin a value in place, and everything it makes can be created, edited, held or deleted by hand. All undoable. A mechanic without a lever, a screen, a book entry and a chronicle line never ships.
- **The Harshness Dial** — heroic, realistic or brutal. One dial scales wounds, infection, plague, famine, childbirth and siege hunger together. On realistic, a famous ruler can die of one arrow, and every rate beneath the dial stays yours to adjust.
- **Many Cores, One World** — the engine computes each world in parallel and merges the results in a fixed order, so one core or many gives the same turn to the last byte. Every unordered read is put in a fixed order too, so a world never depends on the machine it runs on.

**In your world:** The Creator asked why a city was starving. The answer named a dry year, the levy that took its farmers and a field salted a century earlier. The Creator followed the chain back, step by step, to a broken oath between two rival houses.

</td>
</tr>
</table>

### The fifteen chapters

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
| ☀ [**IX. The Gods**](#chapter-ix) | 65–72 | Forty-seven domains, dominion, belief that reshapes gods, avatars, the court of heaven, apotheosis, laws of creation and the hungering dark |
| 🪐 [**X. The Cosmos**](#chapter-x) | 73–80 | Orbital heavens, impacts, terraforming, thirty-seven world types, rifts, star travel, deep time and turning ages |
| 📖 [**XI. Knowledge and Eras**](#chapter-xi) | 81–85 | Discovery, scholarship, open-ended technology, the storyteller and expeditions into the dark |
| 🌌 [**XII. Galaxies and Dimensions**](#chapter-xii) | 86 | Galaxies real and fabled, clusters and the cosmic web, travel and trade between galaxies, layered dimensions and beings from beyond |
| 🧬 [**XIII. Minds, Gifts and the Living**](#chapter-xiii) | 87–94 | Made minds and second selves, remade bodies, networks and information, plenty and ruin, born powers, hidden peoples, living craft and the ways of life of every people |
| 📜 [**XIV. The Record and the Common Life**](#chapter-xiv) | 95–97 | Every happening kept and told in full, the public voice of media, satire and speech, and public works, state enterprise, endowments and everyday trade |
| 🌦 [**XV. Skies and Rains**](#chapter-xv) | 98–99 | Fields, storms and what bodies can bear under every sky, and the politics of working the weather |

### The cover wall

The Loom and ninety-nine expansions: one hundred covers, one wall. Click any cover to jump to its features.

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
<a href="#86-the-boundless"><img src="common/assets/images/dlc-covers/86-the-boundless.jpg" width="11%" alt="Expansion 86"></a>
<a href="#87-minds-unmade"><img src="common/assets/images/dlc/dlc-87-minds-unmade.jpeg" width="11%" alt="Expansion 87"></a>
<a href="#88-remade"><img src="common/assets/images/dlc/dlc-88-remade.jpeg" width="11%" alt="Expansion 88"></a>
<a href="#89-every-voice-at-once"><img src="common/assets/images/dlc/dlc-89-every-voice-at-once.jpeg" width="11%" alt="Expansion 89"></a>
<a href="#90-plenty-and-ruin"><img src="common/assets/images/dlc/dlc-90-plenty-and-ruin.jpeg" width="11%" alt="Expansion 90"></a>
<a href="#91-born-gifted"><img src="common/assets/images/dlc/dlc-91-born-gifted.jpeg" width="11%" alt="Expansion 91"></a>
<a href="#92-the-hidden-folk"><img src="common/assets/images/dlc/dlc-92-the-hidden-folk.jpeg" width="11%" alt="Expansion 92"></a>
<a href="#93-grown-not-built"><img src="common/assets/images/dlc/dlc-93-grown-not-built.jpeg" width="11%" alt="Expansion 93"></a>
<a href="#94-ways-of-life"><img src="common/assets/images/dlc/dlc-94-ways-of-life.jpeg" width="11%" alt="Expansion 94"></a>
<a href="#95-as-it-happened"><img src="common/assets/images/dlc/dlc-95-as-it-happened.jpeg" width="11%" alt="Expansion 95"></a>
<a href="#96-the-public-voice"><img src="common/assets/images/dlc/dlc-96-the-public-voice.jpeg" width="11%" alt="Expansion 96"></a>
<a href="#97-builders-and-benefactors"><img src="common/assets/images/dlc/dlc-97-builders-and-benefactors.jpeg" width="11%" alt="Expansion 97"></a>
<a href="#98-under-every-sky"><img src="common/assets/images/dlc/dlc-98-under-every-sky.jpeg" width="11%" alt="Expansion 98"></a>
<a href="#99-the-rainmakers"><img src="common/assets/images/dlc/dlc-99-the-rainmakers.jpeg" width="11%" alt="Expansion 99"></a>
</p>

### Every expansion

Every expansion below runs in every world from the first epoch, built into the engine, the agents, the interface, the book and the Codex.

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

Your world keeps a real calendar. Inside every fifty-year epoch the engine lives through real years: sowing springs, campaign summers, killing winters. The same storm sinks a fleet, pins an archer line in the mud, cheers a storm god's faithful and ruins a harvest, all at once and each for a reason you can read.

- **Seasons Built from the Sky** — one to eight seasons per world, set by axial tilt, moons and world type, each with its own share of the year, its warmth, its rains and a name in the world's own language. Ice worlds endure a long winter and a short thaw. Tidally locked worlds keep one unchanging season.
- **Early, Late or Not at All** — every season of every year comes early, on time, late or fails, and its water runs from arid to deluge. An early spring lengthens the growing year, a late one shortens it, and a failed rainy season brings drought, holds back the festival of first rains and spares only the creatures that can pause their young until the rains return.
- **Twenty-Five Kinds of Weather** — drizzle and sleet, freezing fog, frost that kills the spring blossom, ice storms that break roofs, roads and herds, thunderstorms whose lightning sets dry forests alight, tornadoes that flatten a town, and cyclones that track along the coasts for several turns. Magic storms, auroras, eclipse darkness and void rain come where the world allows them. Eleven effects, from footing and morale to lightning, floods and breathable air, strike armies, sailors, harvests and health each in their own way.
- **Wars Fought Season by Season** — campaigns march through real springs and winters, and the chronicle reads "in the third winter of the war".
- **Long Winters, Long Summers** — a great impact, a vast eruption, a dimming or brightening star, an ocean current that fails, the works and weapons of peoples, or a god can bring a winter or summer that lasts for years. It can hold a whole world or one hemisphere. Long winters cut harvests, travel and campaigns; long summers parch hot lands and raise sickness; and peoples who watched the cause arrive forecast it better.
- **Years with Names** — the cruellest and the best years earn names: hunger, plenty, hard weather, pestilence, disaster, discovery, first contact, an omen, a peace that ended a long war, a founding that changed a people. A year great enough enters the chronicle, can harden into legend and founds a day of remembrance its people keep.
- **A Calendar for Every People** — regnal years, founding eras, years since the god's descent or since the comet last returned. Fourteen kinds of festival, from sowing, harvest, midwinter and new year to market fairs, first rains, assemblies, tax gathering and pilgrimage, open only where a people's seasons and way of life give them a reason. A calendar reform can set two cults at each other's throats.
- **Moons, Tides and Eclipses** — moons pull the tides that open and close coasts and decide how often the sun goes dark.
- **Seasons in Your Hands** — add, remove, reorder and reshape any season and its share of the year, set a season's onset in any year, or watch a son seize the power to reorder them.

**In your world:** A blizzard in the second winter of the siege broke the attackers. The defenders' storm god took the credit, and the hungry year became a fast day their grandchildren still keep.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/02-the-living-land.jpg"><img src="common/assets/images/dlc-covers/02-the-living-land.jpg" width="220" alt="The Living Land box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/02-the-living-land.jpg"><img src="common/assets/images/dlc-backs/02-the-living-land.jpg" width="220" alt="The Living Land box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 2. The Living Land

*The map was a picture. Now it is a place.*

Every region now carries soil, rainfall, forest, rivers and wounds, drawn from the very map you see. Clear the woods and the hills erode. Farm too hard and the soil fails, the people leave and the forest walks back in. Fight a battle by a ford and the ground remembers it. The land keeps a record of everything done to it, and everything done on it reads the land.

- **Soil, Sun and Rain** — thirty-four terrain kinds, from steppe, moor and high pass to karst, floodplain, badlands, cloud deck, crystal field, living flesh and void shore, over nineteen soils, from deep humic loam and volcanic tephra to waterlogged gley, permafrost and clay that swells, cracks and breaks foundations. Each terrain decides how ten ways of moving cross it: on foot, mounted, on wheels, by boat, flying, burrowing, swimming, climbing, beneath the water and straight through solid rock.
- **The Wild Walks Back** — clearing, farming, grazing, mining and building thin the forest and breed fever, and drought on overgrazed land makes desert. Abandon the fields and the land climbs back through twelve stages, from bare ground and pioneer growth through grassland, heath and shrub to old forest, or from open water through marsh and bog, until a wildfire starts it over.
- **Scars on the Earth** — battlefields, plague grounds, fields made barren, burned land, craters, haunted and blighted ground, void wounds, plundered towns, old earthworks and military roads, fallen bridges, and land flooded, poisoned, mined out, eroded, deforested, drained or overgrazed. Nineteen kinds of scar outlive the people who made them, each cutting harvests and passage in its own way and healing at its own pace.
- **The Land Remembers** — sixteen kinds of memory hold to a region: battles, massacres, sacks, disasters, plagues, famines, the death of a god, a saint's grave, a miracle, foundings, treaties, expulsions, discoveries, uprisings, unions and accessions. Each draws pilgrims, stirs unrest, lifts or sinks the morale of armies fighting there and strengthens claims; the place where a line came to rule backs that line.
- **Ley Lines** — neighbouring regions rich in magic link into lines that carry magic storms, feed wizards and strengthen any temple or gate built upon them. Their nexuses become holy sites and war aims, and ground made barren, a void leak or a god can sever a line.
- **Blessed, Cursed and Savage Lands** — evil ground brings blood rain and raises the dead, blessed ground offers healing springs and gentle weather, and savage ground grows huge beasts that resist taming. Massacres darken a region, saints and temples brighten it, farms tame it.
- **Danger with Teeth** — fifteen sources, from bandits, beasts, disease and quicksand to landslides, exposure, currents, toxic ground, lightning, sinkholes and rockfall, kill settlers, herds, pilgrims and people at work, ambush armies, choke merchant roads and break crops, ships and buildings. Ten seasonal hazards follow each world's own calendar: avalanches close the passes, ice jams and floods take the valleys as the year warms, storm surges hit the coasts and dust storms sweep dry ground. An army marching into an unmapped region can lose its way.
- **Forty-Eight Kinds of Place** — fords, groves, springs, lairs, nexuses, crossroads and the corpses of gods, joined by waterfalls, deltas, mesas that defend, hot springs that heal, tar pits that trap beasts and keep fossils, meadows and narrow necks of land that command the way between two shores. Passes draw battles, holy ground draws pilgrims, and fifteen kinds of secret wait to be found: buried relics, sealed spirits, lost knowledge, hidden routes, sleeping beasts, lost graves, hidden springs, a disease lying dormant, doors to the underworld, or proof that the place's told history is false.

**In your world:** A kingdom cleared its hill forests for wheat. The slopes eroded, the soil gave out, famine emptied the villages and the oaks crept back over the ruins. Generations later, settlers found the land rich again and called it the Green Grave.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/03-stone-and-deep.jpg"><img src="common/assets/images/dlc-covers/03-stone-and-deep.jpg" width="220" alt="Stone and Deep box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/03-stone-and-deep.jpg"><img src="common/assets/images/dlc-backs/03-stone-and-deep.jpg" width="220" alt="Stone and Deep box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 3. Stone and Deep

*Dig too deep, and something digs back.*

Beneath every region lies a column of stone you can read layer by layer: clay, limestone, granite, marble, obsidian, and on stranger worlds frozen methane, glass and living tissue. Your miners follow the veins down. The deeper they go, the rarer the ore and the harder the rock. Then a pick breaks through into a cavern no surface eye has seen, and something in the dark turns its head.

- **Layered Geology** — twenty-eight kinds of rock and ground, from clay, chalk and slate to tuff, gneiss, travertine laid by hot springs and pumice that floats after an eruption, and iron, carbon or crystal bedrock on stranger worlds, each layer with its own veins. Limestone and sandstone hold water and hollow into caves, marble raises splendid temples, slate roofs the towns, and the hardest stone yields only to better picks.
- **Eleven Layers Down** — frozen ground, aquifers, an ocean under the ice on frozen worlds, reservoirs to be tapped, then three cavern layers, each a hidden world of fungus forests, blind beasts and cave peoples, with a fault zone between them. Beneath burns a magma sea that fuels forges and drowns the careless, some worlds hide a hollow interior with lands of its own, and at the bottom lies the deep realm where the dead are kept.
- **Rivers That Live** — flow from upstream rain and spring snowmelt, rapids, brackish estuaries and flood plains. Floods, quakes, silting, landslides, eruptions, ice, a neighbour's dam or canal, a god, or one river cutting back into another can move a river's bed. Dam it upstream and the realm below goes thirsty, and a water dispute is reason enough for war.
- **Quakes and Fire Mountains** — plate boundaries drawn with the map decide where the earth shakes and the mountains burn. Stress builds in the fault zones every epoch, faster where the mines bite deep, until it breaks loose as a quake. Eruptions darken the sky, enrich the soil and can raise new land.
- **When the Mine Comes Down** — depth against the rock's strength and the miners' engineering sets the risk of collapse each year. A cave-in crushes miners, seals the shaft and sometimes breaks open a cavern, letting its beasts climb out.
- **Seal the Deep** — seven kinds of seal hold back what you woke: gates and walls, warding rites, divine acts, innate powers, grown living barriers, sworn pacts with the beings below, and made minds that keep the watch. Every seal weakens with time, beasts and miners test it, a made keeper's seal fails when its keeper fails or rebels, and opening one again is a scheme waiting for a schemer.
- **Fossils of Ages Past** — fossil beds hold extinct beasts and megafauna, earlier creations, lost peoples, dead gods, old made bodies and the older forms of living peoples. Floods, quakes and digs bring them up, and each culture reads them its own way: as legend, relic, deep time, a sacred site, an omen, a material to work or a medicine to grind. A find of a people's own forebears can overturn what it believes about its origin.
- **Silt and Shore** — rivers, winds, ice, waves, slopes and mine works carry ten kinds of sediment, from silt and clay to glacial flour and mine tailings that silt and poison the rivers below. Deltas and marshes build, harbours and canals silt up, towns and finds are buried, and thirteen coast forms, from cliffs and fjords to spits that close harbours and atolls lost to rising seas, grow or wear away over generations. Organic beds become coal and oil, and well-kept remains let living craft revive extinct species.

**In your world:** The miners of a mountain town chased a silver vein through the granite until the floor gave way into a cavern. Something came up the shaft. Their seal gate held for three generations, until a rival house paid to have it opened.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/04-winds-of-the-world.jpg"><img src="common/assets/images/dlc-covers/04-winds-of-the-world.jpg" width="220" alt="Winds of the World box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/04-winds-of-the-world.jpg"><img src="common/assets/images/dlc-backs/04-winds-of-the-world.jpg" width="220" alt="Winds of the World box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 4. Winds of the World

*Deserts where mountains steal the rain. Famine where the monsoon fails.*

The air moves for reasons now. Your world's spin, tilt and sunlight bend its winds into bands, the winds carry rain against the mountains and leave deserts behind them, and the currents decide which coasts grow rich on fish. When a distant ocean warms, two kingdoms that have never met lose their harvests in the same year, and the astronomers who tracked the cycle saw it coming.

- **Prevailing Winds** — twelve wind belts: trade winds, westerlies and polar winds, the doldrums and the calm latitudes, single cells and terminator winds on slow and tidally locked worlds, the banded and racing winds of giant worlds, monsoon belts, and mountain winds that dry the lee slopes and drive fires. They set the wind in every region and season, chart the sailing routes, fan the wildfires and carry the smoke of the forges.
- **Rain Shadows** — moist wind climbs the mountains and rains on the windward side, leaving desert in the lee. Every forest and every desert sits where the physics puts it.
- **Monsoons** — winds that reverse with the seasons over land and sea bring the wet season, feed whole peoples and set the sailing calendar of the trade routes. The year the monsoon fails is a famine year with a name.
- **Ocean Currents** — warm and cold currents, cold upwellings rich in fish, tidal streams racing through the straits, great gyres that gather drift and wrecks at their centre, and counter currents that open a sailing route home. They set coastal climates, feed the fisheries, speed or slow the ships, and carry castaways, stowaway creatures and messages in bottles that start rumours on a foreign shore.
- **Droughts a World Apart** — slow climate oscillations bring drought to one land and flood to another in the same years, and in their strong warm and strong cold phases the swing doubles. Diviners and astronomers who learn the rhythm can foretell the bad years.
- **Climate by Region** — the world's age, one of eleven from temperate and variable to ice age, snowball and hothouse, with slow warming and cooling ages between them, plays out differently on every coast and latitude. Felled forests dry their neighbours, a volcano brings a short chill and a supernova a long one, frozen ground thaws or freezes with the age, and storm, sun and ice gods push it region by region.
- **Seven Planetary Cycles** — carbon, water, nutrients, oxygen, rock, the world's inner heat and its ice each keep a stock that flows between volcano, forest, ocean, river and soil. Inner heat fades over deep time and quiets the volcanoes; ice locks up the sea and lets it go again, drowning atolls and coasts. Burn the forests across a world, or let a god impose an eternal summer, and the whole planet answers over epochs.

**In your world:** A river people burned their forests for fields. The rains thinned over the neighbouring hills, the hills dried to scrub, and the hungry hill clans came down to clear the last woods along the river.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/05-plough-and-net.jpg"><img src="common/assets/images/dlc-covers/05-plough-and-net.jpg" width="220" alt="Plough and Net box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/05-plough-and-net.jpg"><img src="common/assets/images/dlc-backs/05-plough-and-net.jpg" width="220" alt="Plough and Net box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 5. Plough and Net

*The soil keeps accounts. Sooner or later, it collects.*

Stand in any market town and look outward. Gardens and dairies hug the walls, forests feed the hearths beyond them, grain rolls further out, herds roam the edge, and a single new road redraws the whole pattern. Out there your farmers spend the soil's hidden stocks, sow beans to mend it, spoil it with canals that have no drains and fight their lords over who may graze the common.

- **Market Towns Arise** — hamlets serve daily needs and towns weekly ones, seasonal fairs draw traders from far away, regional markets set the prices of a whole region, cities trade in the rare, and the metropolis of a realm meets the long-distance and interworld trade. New settlements rise where the gaps between markets call for them, and every road or canal pulls the rings of farmland outward.
- **Seven Rings of Land** — gardens, forest, grain, herds and the wilds ring every town, with fallow fields resting to win back their fertility and industry that takes land and fouls the rings beside it.
- **Hunger Breeds Invention** — crowded land pushes peoples toward irrigation, terraces, rotations and manuring, while empty land lets them wait. Peoples who remember famine learn bark breads and build granaries.
- **The Soil Remembers** — six hidden stocks lie under every field: a fixing element, minerals, organic matter, salinity, a seed bank that regrows after fire and clearing, and the soil life that breaks down the dead and dies under poison. Beans restore, fallow and manure heal, floods and volcanic dust enrich, and irrigation without drainage spoils a civilisation's fields over centuries.
- **Orchards of Generations** — vineyards, orchards, groves, timber stands, plantations, forest gardens, palm stands, coppice cut back to regrow for fuel, and hedgerows that hold the soil and shelter wildlife take years or whole epochs to mature. An enemy who cuts them down wounds a land for generations.
- **Commons and Enclosure** — twelve kinds of commons, from pasture, woods, fisheries, water and quarries to peat cuttings, foraging grounds and shores, governed by open use, custom, a council, a lord's fence, state officials, bought and traded licences, or households taking turns year by year. Good rule keeps them and overuse ruins them. When lords fence them, owners grow rich and cottagers drift to the cities. When lords keep the forest for the hunt, poachers are born.
- **Nets and Closed Seasons** — fish stocks swell with warm water and river silt, then collapse under too many nets. Ten catch grounds, from fisheries, fowling and the hunt for great land game to shore gathering, pearl diving, fish ponds, egg gathering at nesting colonies and insect gathering for food, dye and wax, are worked with twelve kinds of gear, and dredges scar the beds they drag. Closed seasons, quotas and gear bans, kept by wardens and dodged by poachers, save them. Whalers chase the biggest catch at the biggest risk.
- **Herds and Hooves** — grazing, milking, shearing, eggs and the butcher's block, breeding seasons and herd counts, oxen at the plough, and hounds and beasts trained for war, the hunt and the gate.

**In your world:** Three hill villages shared one high pasture by old custom until their herds doubled and the grass gave out. Their council gave each village the pasture in its own year, the grass came back, and the quarrels that had cost two lives faded within a generation.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/06-wild-kingdoms.jpg"><img src="common/assets/images/dlc-covers/06-wild-kingdoms.jpg" width="220" alt="Wild Kingdoms box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/06-wild-kingdoms.jpg"><img src="common/assets/images/dlc-backs/06-wild-kingdoms.jpg" width="220" alt="Wild Kingdoms box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 6. Wild Kingdoms

*Every creature has a range, a hunger and a place in the chain.*

Species leave the bestiary and take up residence in your land. Each one lives region by region, breeding in its own seasons, eating what its diet allows, following the herds or the grass along its migration path. When the deer are gone, the wolves come for your sheep. When the rats come for the granary, someone has to tame a cat.

- **Living Ranges** — every species holds its own population in every region, growing with litter size, habitat, warmth and food, and falling to hunters, predators, disease and the plough. Twelve classes of life, from animals, plants and fungi to lichens that break bare rock into soil, microbes counted in millions and the mineral, gaseous and energy life of stranger worlds, range in size from microscopic to colossal.
- **Sixteen Ways to Eat** — herbivores, carnivores, omnivores, scavengers, filter feeders, insect eaters, fish eaters, blood drinkers, parasites and decomposers, and creatures that live on sunlight, stone, chemicals at hot vents, raw energy, souls or the void. More than thirty traits, from echolocation and camouflage to iron eating and fire breath, shape what each one does.
- **Who Eats Whom** — who hunts whom is worked out each epoch from diet, size and shared ground. When prey runs short, predators raid your livestock. Lose a prey species and its hunters starve; lose a sacred one and a faith falls into crisis.
- **Herds, Packs and Pairs** — eight social forms: solitary hunters, packs, herds, hives, colonies, swarms, mated pairs that hold a range together, and family groups that teach their young and grieve their dead. The form sets the size of herds and lairs, the catch, and how fast a species can be tamed.
- **From Wild to Breed** — eight stages run from wild through commensal creatures that live beside people by choice, tamed, herded, domesticated and bred, with captives kept in menageries, arenas and rites, and feral lines that slip back to the wild. Captive lines grow calmer and richer in hide, wool, milk and silk, and serve in nineteen roles, from draft, mount and dairy to hunting, herding, messengers, sport, medicine and display. Populations cut off from their kin drift into highland and desert strains.
- **Life Beyond Water** — nine biochemistries: carbon in water, ammonia or methane, silicon, crystal, plasma, metal, spirit and void, each with its own solvent, warmth and the worlds it can arise on. Metal life on hot iron worlds feeds on minerals, fears rust and acid, and leaves metal behind when it dies.
- **Pests and Blights** — crop pests thin the harvest, iron eaters gnaw the ore, plague bearers spread sickness, and vermin spoil the granary until a cat-like hunter is tamed for the work.
- **Flora Alive** — crops, herbs, dyes, timber, brews, reagents and poisons are living plants with seasons, soils and pests. Fifteen growth forms, from trees, vines and palms to plants that grow on other plants, plants that feed on a host, and bulbs that sleep underground until their season, each cultivated into new cultivars and weighed against the year it grows in.
- **Companions and Champions** — a hound at the hearth eases loneliness, and its death leaves real grief. Falcons and war dogs sharpen the hunt. Among the largest, deadliest species, one beast may rise as a region's named terror or guardian.
- **Root, Bark and Seed** — every plant has a body of fifteen parts, from roots, wood, bark and leaves to resin, pollen and nectar, and nineteen kinds of product come from them, from grain, fruit and fibre to oil, sugar, spice, stimulants, fodder, medicine, building stuff and fuel. Its growth form sets the years to first harvest and its damage from storm and fire.

**In your world:** A ruler's hunters killed the last of the sacred white stags. The stag's cult fell into a crisis of doctrine, the wolves that had fed on the herd turned on the flocks, and the shepherds drove far fewer sheep to the winter market.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/07-tooth-and-claw.jpg"><img src="common/assets/images/dlc-covers/07-tooth-and-claw.jpg" width="220" alt="Tooth and Claw box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/07-tooth-and-claw.jpg"><img src="common/assets/images/dlc-backs/07-tooth-and-claw.jpg" width="220" alt="Tooth and Claw box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 7. Tooth and Claw

*Nature does not stand still. It adapts, or it dies.*

Every population in your world carries its traits as a living average, and every epoch pushes it. Wolves make the deer faster. Hunters make them warier and smaller. A god's protection lets them soften, and leaking void scatters them into mutation. Leave two herds apart long enough and they become two species. Wipe out half the world's life and watch the survivors fill every empty niche.

- **Selection Pressure** — eighteen heritable traits, from size, speed, venom and camouflage to cold, heat and drought tolerance, disease resistance, docility, longevity, strength, care of the young and learning passed from parent to young, shift each epoch in every range. Predator races prey, plague races host, and a line that learns passes the way around traps and poisons down the generations. A god's curse or blessing passes down a whole lineage.
- **Niches and Rivals** — a niche is diet, habitat, size and waking hours, and no two species share one for long. After a mass extinction, survivors radiate into the empty niches. On islands giants dwarf and the small grow large, and abandoned livestock go feral.
- **The Energy Ladder** — six steps, from producers to apex hunters, with decomposers living on the dead of every level and parasites on the living. Each step holds only a tenth of the life beneath it, so overhunt the grazers and the predators collapse. Nine keystone roles, from pollinators, soil makers and dam builders to seed carriers, reef builders, nutrient fixers and grazers that keep the grassland open, carry whole harvests, and their loss cascades into hunger, sickness and forest taking the pasture.
- **Partners and Parasites** — six kinds of bond tie species together: mutual aid, one living off another's leavings, parasites, mimics that fool hunters and scouts, one harming another for no gain, and one species farming another. Pollinators feed the crops, ticks bleed the livestock and mistletoe chokes the trees. Every brewer, baker and monastery guards its ferments, from yeasts, starters and moulds to bean ferments and the wild cultures of one valley, heirlooms a fire can end.
- **Senses Beyond Ours** — thirteen senses, from sight, scent and hearing to night vision, echolocation, vibration, heat, magnetic sense, electric sense, ultraviolet sight, taste that finds the poison in the cup, the pressure sense that feels a storm coming, and spirit sight, decide who spots whom. Night-sighted peoples raid in the dark, scent trails betray spies, and a magnetic sense needs no compass.
- **Sleep, Heat and Thorn** — hibernation, summer sleep, nightly torpor, a near-lifeless state that lasts for ages, and a pause that holds eggs and young through a failed season carry creatures past hard times. Five ways of keeping warm, from warm-blooded and cold-blooded to bodies that switch, keep a warm core only, or ignore heat altogether. Eight plant defences, from thorns, toxins and stinging hairs to carnivorous traps, animal guardians, mimicry of a guarded plant and fast regrowth, make the green itself dangerous.
- **The Feast of Crows** — every battle, plague, famine and massacre leaves a carrion pulse. Vultures and rats boom, stores spoil, sickness rises, predators close in, and the unburied dead stir as restless spirits until the feast is eaten. Remains rot, dry, freeze, drift, sink, are buried, burned or scattered by scavengers, and each fate sets its own sickness, fossil chance and chance of a restless ghost.

**In your world:** No one buried the dead after the battle at the ford. Rats boomed on the field and spread into the town's granaries, spoiling the stores and carrying a fever. That winter the town was hungry and sick, and the field was said to walk at night.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/08-wyrms-and-hoards.jpg"><img src="common/assets/images/dlc-covers/08-wyrms-and-hoards.jpg" width="220" alt="Wyrms and Hoards box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/08-wyrms-and-hoards.jpg"><img src="common/assets/images/dlc-backs/08-wyrms-and-hoards.jpg" width="220" alt="Wyrms and Hoards box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 8. Wyrms and Hoards

*Not a species. A name, a lair, and a grudge.*

Meet the dragon of the northern peak by name. It has a body that scars, an age, a lair and a hoard of gold, relics and worked treasure. It sleeps through the seasons, wakes when miners dig too close or a thief creeps in, and raids every farm in range. It remembers who wounded it, and it will hunt that hero's house.

- **Named Beasts** — individual creatures with bodies that take real wounds, twelve tempers from sleeping and brooding to hungry, territorial, wounded, cowed, enraged, migrating along a seasonal path or fleeing a lost lair, and a terror that drains the courage and prosperity of every settlement nearby. Eleven temperaments, among them vengeful, acquisitive, protective, playful and proud, set how each one acts. The clever ones speak, bargain and scheme with minds of their own.
- **A Grudge That Lasts** — a vengeful beast keeps a grudge against the line or people that wronged it, with its cause and its strength, and hunts them until it fades. A proud one answers insults and challenges, and accepts terms from those who honour it.
- **Hoards Worth a Kingdom** — raids and tribute fill the hoard, and villages may sign a treaty to pay it. Slay the beast and the hoard becomes a treasure site, and its looting crashes luxury prices across the market.
- **The Slayer's Reward** — quests name their quarry. A kill brings a title, a slayer's legend and the beast's body, worked into twenty-one kinds of product, from hide, ivory and scales to blood, organs, venom, shell and great-beast tissue. Tamed beasts, even void beasts that drift between worlds, carry riders onto sky, sea and star routes; bound ones guard temples or march to war.
- **Born of the Deep** — unique horrors built from the body up, of seventeen materials from hide, plates and shell to crystal, metal, gel, wood or living liquid. They strike by twelve means, from bite, sting, breath and gaze to thrown spines and crushing coils, some at a whole battle line at once, and live in nine habitats from land, sea and sky to magma, ice, the shore and the ethereal. Each hoards what it loves, is turned by what it hates (fire, iron, noise, light, cold, strong scent or its own true name), and wakes to deep mining, desecration, theft, a summons, a sign in the sky, harm done to its kin or the return of its season.
- **Familiars** — a mage binds a beast or spirit by rite. It lends its senses, a skill or a shield against magic, and takes the backlash first. Its death wounds the mage. Beasts sacred to a god grow calm in that god's dominion.
- **Monster Contracts** — troubled villages post bounties in coin or favours. Professional hunters, some changed by their order's training, study each beast's anatomy for its weakness, and every job builds a reputation and a legend.
- **The Ancient Ones Remember** — a long-lived dragon recalls the war of three centuries ago as it truly happened, or as it prefers. It teaches songs, rites, tongues and true names, sells secrets, maps, remedies and lines of descent among seventeen kinds of knowledge, and when it dies, all it never taught dies with it.

**In your world:** A hero wounded the wyrm and fled with a cup from its hoard. The wyrm remembered, and for two generations it hunted the hero's house. When a contract hunter finally killed it, the looted hoard flooded the markets and luxury prices crashed across the realm.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/09-plague-ledger.jpg"><img src="common/assets/images/dlc-covers/09-plague-ledger.jpg" width="220" alt="Plague Ledger box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/09-plague-ledger.jpg"><img src="common/assets/images/dlc-backs/09-plague-ledger.jpg" width="220" alt="Plague Ledger box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 9. Plague Ledger

*It has a name. It has a host. And it learns.*

Plague is no longer a stroke of bad luck. It is a named enemy with a route, a host and a history. It rides the caravans and the armies, waits in the swamp fly and the granary rat, and returns for the children born after its last visit. Close the ports and the markets starve. Ring the bells for prayer and the crowd spreads it. Somewhere, a plague god grows stronger with every outbreak.

- **Named Diseases** — each one has a main route and further routes among seventeen ways of passing: breath, water, food, touch, bite, blood, birth, intimacy, shared objects, soil, sound, a rite, a gaze, a spirit, the void, a curse or a lived experience. Each has a lethality, an incubation, a part of the body it attacks and a climate it favours, warm or cold, wet or dry. A plague that turns endemic guards its marsh: the locals are immune, and invaders die at the walls.
- **Evolving Plagues** — crowded cities breed faster spread, sparse villages starve the deadliest strains, and every treatment in use breeds resistance. Survivors stay immune, so the plague comes back for the young, or mutates past them.
- **Silent Carriers** — some of the infected never fall ill. The merchant, envoy or pilgrim who seemed healthy seeds an outbreak across the sea, and only a skilled physician who holds the theory of contagion can find them.
- **How It Travels** — along trade routes, with armies, journeys and sieges, through wildlife and migrations, at gatherings, down waterways, with herds that are driven and sold, and through shared wells and aqueducts that sicken a whole city from one source. Mutations and plagues loosed on purpose start new outbreaks.
- **Healers Right and Wrong** — sickness runs through incubation, fever, crisis, recovery or death, and its after-effects. A healer who believes bleeding cures fever raises the death toll; one who grasps contagion makes quarantine work. Addiction to drink, drugs and void dust is a disease too.
- **Where Plague Begins** — clearing forests, hunting bushmeat and herding beside wild hosts let a creature's disease leap to people. Insects follow the warm seasons, birds carry fevers along their migrations, and exterminating a host is a cure with an ecological price.
- **Hard Choices** — close the borders, quarantine the poor quarter, burn the dead, expel the sick, ring the bells for prayer, clean the streets and wells, close the feasts, markets and rites, inoculate, or let the able flee, and pay in trade, riots, funeral quarrels, lost morale or a crowd that carries it on. Purity-minded peoples found leper colonies; merciful ones build hospitals.
- **The Cure Race** — hospitals, universities and monasteries race against one disease, faster with scholars, true theories and fresh cases nearby. The winner holds a cure it can sell. Variolation trades a small risk for immunity, until the herd is safe.
- **What Makes It Sick** — every disease has one of thirteen agents (virus, bacterium, fungus, parasite, prion, toxin, deficiency, spirit, curse, a made agent, an unknown one, a fault carried down the bloodline, or a body turned against itself), and fourteen cure classes, from herbs and surgery to antivirals, diets that end deficiencies and immunisation that keeps it out, work only by class. Agents evolve at their own rates, survive in water, soil or objects by kind, and hide in reservoir species between outbreaks.

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

A duel at the river ford ends in a single stroke. The ruler lives, but the sword hand lies in the mud, and in a culture that demands a whole body on the throne, the claim fails faster than the wound heals. Every blow in your world lands on a real part of a real body, passes through real armour and leaves a mark that history must carry.

- **Bodies, Not Hit Points** — eighteen body plans, from humanoid, serpentine and six-legged to rooted, colossal and divine. A humanoid body alone has twenty-seven parts, each with a job: a lost eye spoils the archer, a shattered jaw silences the preacher. Antennae, fins, roots and pouches serve the bodies that have them, and paired parts are struck and lost one side at a time.
- **Steel Meets Flesh** — every blow is weighed by momentum, edge and the hardness of steel against mail, in twenty kinds of harm from cut, pierce and blunt to fire, sonic, crushing pressure and blows to the soul. Armour is tested layer by layer, padding, mail, cloak and shield, before the blade reaches skin, fat, muscle and bone.
- **Wounds with a Memory** — thirty kinds of injury, from bruise, sprain and frostbite to torn tendons, internal bleeding, the void touch that never heals and the divine brand. A wound can turn infected, then gangrenous, reopen, heal into a scar or stay chronic and flare under strain. Arteries bleed until bound, a struck nerve leaves a limp arm without a cut, and pain tips into shock and capture.
- **Thirty-Two Causes of Harm** — battle, duel, torture and accident, but also childbirth, crime, sport, crowds and crushes, kept animals and treatment gone wrong, each recorded with the harm it did.
- **Healers and Surgeons** — medicine climbs from herbs, surgery and anatomy through antisepsis, anaesthesia and immunisation to transplants, regeneration and mind medicine. Healers diagnose, clean, suture, set, splint, drain, transfuse, medicate and cauterise, prescribe rest, and a skilled surgeon turns an infected arm that would kill into an amputation the patient survives.
- **The Silver Hand** — prostheses of wood, glass, silver and star metal restore part of what was lost, by material and craftsmanship. A legendary one becomes a relic that passes down the line and carries legitimacy with it.
- **What the Body Can Still Do** — melee, missile, command, craft, scholarship, presence, mobility, fertility, endurance, perception, stealth and labour are all read from the body. Thirteen lasting maims and twenty-four conditions, from paralysis and chronic pain to seizures and lasting fear, change what each one can do. A blind scholar needs a reader. A people without helmets fills its halls with one-eyed veterans.
- **Scars Read by Culture** — honour cultures prize battle scars, purity cultures bar the maimed from the throne, and cults that sanctify suffering recruit them. Generations after a great war, a people still calls itself a people of one-armed elders.
- **Systems and Sensitivities** — breath, circulation, digestion, excretion, regulation, nerves, immunity, reproduction and structure run each body, and a failing system has its own effects. Some beings react to a food, a plant, an animal, a material, a substance, light, sound, pressure or a power, and peoples learn what to avoid.

**In your world:** A duel took the ruler's sword hand. Their people required a whole body on the throne, so the ruler's legitimacy collapsed and a rival claimant rose. The victors of the civil war blamed the healer who had failed to save the hand, the healer's guild lost its standing, and medicine spread more slowly through the realm.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/11-curse-of-the-full-moon.jpg"><img src="common/assets/images/dlc-covers/11-curse-of-the-full-moon.jpg" width="220" alt="Curse of the Full Moon box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/11-curse-of-the-full-moon.jpg"><img src="common/assets/images/dlc-backs/11-curse-of-the-full-moon.jpg" width="220" alt="Curse of the Full Moon box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 11. Curse of the Full Moon

*One bite. One desecrated grove. One night of the full moon.*

A poacher kills a stag in the Hunt god's grove. Nothing happens until the first moon rises full, and then something with the poacher's eyes runs through the village. Curses, venoms, drugs, blessings and transformations in your world share one grammar: how they pass from body to body, how long they wait, the stages they march through, and the cure that ends them.

- **One Grammar for Every Affliction** — twenty kinds, from venom, drink and drug dependence, the beast curse and the blood curse to blessings, void taint, possession, trauma, hunger curses, warping, dooms, trapped souls, fortune, charms and transformations, share one shape: an onset, stages with their own effects, and a cure by rite, medicine, time, quest, power, a place that heals, or the one who laid it lifting it. Each is obvious, noticeable, hidden or marked with a sign only those with the right knowledge or spirit sight can read, and hidden ones are secrets.
- **Age, Memory and Sleep** — a curse can speed, slow or stop a body's ageing, take its holder's memories, skills or a person's name until they are learned again, or lay a sleep that holds until its cure comes, while heirs, offices and unions treat the sleeper as absent.
- **Seventeen Ways to Catch It** — touch, bite, food, breath, blood, birth, intimacy, a rite, a single gaze, shared objects, water, soil, sound, a spirit, the void, a curse or something lived through. Some curses carry themselves onward: a werebeast's bite passes the curse to the bitten.
- **Beasts Under the Moon** — the werebeast turns at every full moon of the world's first moon into a beast that still thinks. Each victim it bites may become the next hunter.
- **The Thirst** — the vampire-like curse stops ageing, adds a hunger for blood, burns in sunlight and needs a false name to hide behind. It comes from a blood rite gone wrong, a feeding, or the curse of a son of Blood.
- **Holy Ground Strikes Back** — rob a temple, kill in a sanctuary or defile a tomb, and the god answers with a curse shaped by its domains. A Hunt god sends the werebeast, a Blood god the thirst, a Death god a possession.
- **Things That Walk at Night** — night trolls and bogeymen carry mortals away, and necromancers raise towers, bind spirits into corpses and march their undead hosts against living towns.
- **Dependence** — drugs and strong drink add a craving and its withdrawal to a single life. Void taint marches its bearer stage by stage into madness, and then into the arms of the outer cults.

**In your world:** A poacher desecrated the Hunt son's grove and turned at the next full moon. The poacher's bites spread the curse, the frightened village held a purge and burned an innocent hermit, whose vengeful ghost still walks. A healer found the cure rite, but too late for the poacher.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/12-the-inner-life.jpg"><img src="common/assets/images/dlc-covers/12-the-inner-life.jpg" width="220" alt="The Inner Life box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/12-the-inner-life.jpg"><img src="common/assets/images/dlc-backs/12-the-inner-life.jpg" width="220" alt="The Inner Life box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 12. The Inner Life

*They don't just act. They feel, they want, they remember and they misjudge.*

The old general has every reason to end the siege. The walls hold, fever is in the camp and the treasury is empty. But the general has spent too many winters and a child's life on those walls, and cannot let go. Every named mortal in your world carries a mind built in layers: what they can do, how they react, what they value, and the mistakes that follow.

- **Three Layers of Mind** — nineteen attributes for what a mortal can do, thirty-six facets for how they react, from anxiety and humour to forgiveness and adaptability, and twenty-seven beliefs for what they hold dear, now including freedom, equality and hospitality. A facet pushed to its extreme hardens into one of a hundred and thirty-eight traits, from brave and forgiving to paranoid.
- **Thoughts, Feelings and Moods** — a hundred and sixty-five kinds of thought and thirty-two emotions: a mortal who saw kin die, survived a quake, fled a plague or heard great music feels grief, relief, trust, anticipation, admiration or awe. Moods run from elated to broken and from calm through alert to agitated, so agitated minds quarrel and flee while calm ones counsel and craft.
- **Memory and Grief** — forty-three kinds of memory, from "saved me" and "betrayed me" to "healed me", "sheltered me" and "abandoned me", reshape beliefs and return on every anniversary. Grief runs from shock and anger through bargaining, mourning and yearning to acceptance, or stalls into grief that will not end.
- **Thirty Needs** — in five groups of body, company, spirit, action and mind, from food, drink and rest to romance, solitude, beauty, knowledge, justice and the need to care for someone. Unmet needs and fifteen pressures, from hunger and overcrowding to debt, isolation and persecution, sour the mood, and the mortals under the heaviest pressure are the ones most likely to act.
- **Likes and Dislikes** — twenty-nine kinds of taste: favourite foods, colours, creatures, seasons, weather, sounds, scents, stories, games and art forms. A people that loves amber raises its price, merchants carry what the buyer craves, and a disgust shared by everyone becomes a taboo.
- **Minds That Err** — twenty-one biases, among them overconfidence, sunk cost, groupthink, hostile attribution, anchoring, fatalism and the halo of a famous name, bend every decision, and the explanation shows which one did it. Rulers fight on in wars they should have ended.
- **Ideas That Take Root** — a heretical book or a new theory incubates for seasons, bringing distraction or obsession, until it is rejected or taken in for good. The rationalist convert gains a sharper mind and loses their comfort in the rites.
- **Dreams and Inspiration** — eight kinds of dream, from nightmares and prophecies to shared dreams, lucid dreams and dreams that ease a memory, and eight kinds of inspiration, from masterwork fever to a healer's insight and a vision of a better law.
- **Beliefs That Spread** — mortals, peoples, cults and gods weigh one another on the same beliefs. Ideas pass by prestige, by conformity and by sheer stickiness, so one charismatic reformer can move a whole town.

**In your world:** A paranoid ruler read a neighbour's new border fort as an attack, and the small, frightened council agreed. The war went badly, sunk cost kept the ruler in it for years, and the defeat became the memory that shaped the heir's caution.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/13-cradle-to-pyre.jpg"><img src="common/assets/images/dlc-covers/13-cradle-to-pyre.jpg" width="220" alt="Cradle to Pyre box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/13-cradle-to-pyre.jpg"><img src="common/assets/images/dlc-backs/13-cradle-to-pyre.jpg" width="220" alt="Cradle to Pyre box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 13. Cradle to Pyre

*The children playing soldiers in the yard will one day sit on the council.*

A girl grows up in a household that cannot quite feed her. She learns her letters at the temple, takes up a craft, rises from apprentice to master and dreams of a masterwork she may never finish. Every mortal in your world moves through infancy, childhood, youth, adulthood, maturity and age, and each stage changes who they are allowed to become.

- **Seven Ages of a Life** — infancy, childhood, youth, adulthood, a mature age when skills and offices peak and strength begins to fall, old age, and for long-lived peoples an ancient age of eccentric living history. The mature are chosen as counsellors and heads of houses; elders gain wisdom, risk failing sight and turn mentor.
- **Pregnancy and Birth** — hunger and disease raise the risk, healers lower it. Twins, stillbirth, injury at birth, miscarriage and death in childbirth all happen, and a parent's death leaves an orphan, a grieving partner and sometimes a crisis of succession.
- **Children of the Yard** — peer groups play at war, songs and riding, and their friendships and rivalries last into adulthood. Children denied play by labour, famine or war grow up less cheerful and more prone to stress.
- **Careers with Ranks** — sixty-nine skills, from blade and bow to farming, herding, cooking, music, climbing and diving, feed ladders from apprentice to grandmaster, soldier to marshal, acolyte to high priest. Fifteen life paths take the young into the army, office, a craft, vows, trade, the sea, service, the arts, study, healing or the wilds, or keep them at home. Unused skills rust. Lose a sword arm and the warrior becomes a teacher, a priest or a beggar.
- **Fifteen Life Dreams** — rule a realm, found a house, slay a beast, find love, know a truth. Each has milestones. A maimed would-be champion despairs unless they find a new dream, and inspiration can strike as a masterwork fever. Twenty-two kinds of life story, from rise and fall to betrayal, friendship and legacy, unfold only where their causes hold.
- **Conviction and Breaking Points** — living by one's beliefs earns conviction to spend on a heroic effort in a crisis. Stress past its limit breaks a mortal into rage, flight, despair, zeal, vice, withdrawal, a sudden vision, a numb absence or a body that gives out.
- **Thirty-Three Ways to Die** — from bleeding, childbirth and drowning to execution, sport, crowds, kept animals, treatment gone wrong, curse, void, despair and the loss of the soul, each recorded with its place. Each culture reads each death as glorious, honourable, plain, shameful, cursed or pitied, and the reading sets the house's prestige, the burial rite and the kind of ghost left behind.
- **Last Rites** — fourteen funeral customs, from burial, cremation, sky and sea burial and entombment to mummification, second burial, a return to the soil that feeds the plot, and memorials for those never found. Each has its cost and specialists, and decides what becomes of the body and the soul.
- **Raising the Young** — infant care and feeding, the ages of naming, work and responsibility, fourteen ways of shaping children, from example and play to mentors and travel abroad, nine schools of teaching including peers teaching peers, and youth groups that serve, court, compete, learn, labour or turn to crime.

**In your world:** A queen died in childbirth and left an infant daughter, while the law demanded a grown heir. A regency council formed, a rival house pressed its claim, and the regent's mounting stress made the civil war that followed all but certain.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/14-hearts-and-hands.jpg"><img src="common/assets/images/dlc-covers/14-hearts-and-hands.jpg" width="220" alt="Hearts and Hands box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/14-hearts-and-hands.jpg"><img src="common/assets/images/dlc-backs/14-hearts-and-hands.jpg" width="220" alt="Hearts and Hands box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 14. Hearts and Hands

*Friends, lovers, rivals and nemeses. All of them remember.*

Two squires share a tent on campaign and come home comrades in arms. Years later one marries the other's sibling, and a single careless insult at the wedding feast begins a feud that outlives them both. Every pair of mortals in your world carries a history of friendship, romance, rivalry and memory, and every word that passes between them adds to it.

- **Bonds on Four Axes** — friendship, romance, familiarity and rivalry combine into twenty-four kinds of bond, from crush and confidant to mentor, betrothed, sworn kin, foster kin, neighbours bound to help in fire and flood, guest friends whose bond passes to their heirs, the estranged, and nemesis. An affair becomes a secret, and its discovery ends in divorce, a duel or a house feud.
- **Twenty-Eight Interactions** — gossip, joke, flatter, boast, flirt, propose, confide a secret, apologise, share a meal, ask counsel, praise, warn, plead, pass on news, threaten, brawl. Each is chosen by temperament, mood, the bond and whether the two even share a language, and each leaves a mark.
- **Memories That Become Opinions** — harmed me, saved me, betrayed me, gifted me. Opinion is built from trust, fear, respect, affection and grievance, and the strongest grudges pass to the heirs when the holder dies.
- **Burning Passions** — sixteen passions, among them love, loyalty, hatred, devotion, vengeance and compassion, strong enough to be invoked in battle, duel or oath, for a great bonus or a breakdown. Lose the object of a passion and grief arrives at full force.
- **The Art of Persuasion** — appeal to belief, to self-interest, to authority, to evidence, to fear, to feeling, to the bond between you or to tradition, to change a belief, a decision, a faith, a vote or a treaty, or to win a surrender, a confession, an alliance or a captive's release. The speaker's oratory meets the listener's stubbornness, and the result sways councils, congregations and envoys.
- **Pecking Orders and Circles** — households, courts, warbands, crews, congregations and schools rank their members by strength, office and nerve. Twelve kinds of circle, from drinking halls, poets' circles and hunting lodges to sport clubs, reading circles that spread new ideas and mutual-aid societies that pool their goods against hard times, breed friendships, conspiracies and ideologies.
- **Contests of Every Kind** — riddle games, insult verse, disputations, song and storytelling contests, races, craft contests, wrestling and hunts, fought round by round for honour, a union, office, land, freedom, knowledge, a title, water and grazing rights or a captive's freedom. The judges' tastes count, and a famous flyting becomes a heroic poem.
- **Norms of Intimacy** — each culture's own stance, from forbidden to expected, on relations before, within and outside unions, with kin, with made minds, with other kinds and with spirits and gods, on restraint and vows, on the course of pregnancy and the time after birth, and on a child's standing, all told plainly and behind closed doors.

**In your world:** A squire's loyalty to their lord ran so deep that the squire invoked it at the ford and broke the enemy line. When the lord later betrayed that loyalty, grief struck at full force, and the squire took up a new passion: vengeance.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/15-hearth-and-home.jpg"><img src="common/assets/images/dlc-covers/15-hearth-and-home.jpg" width="220" alt="Hearth and Home box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/15-hearth-and-home.jpg"><img src="common/assets/images/dlc-backs/15-hearth-and-home.jpg" width="220" alt="Hearth and Home box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 15. Hearth and Home

*Behind every hero stands a household, and a supper table.*

The veteran comes home from the war with one leg. In a poor household the veteran is another mouth and a burden on a grown child. In a rich one, a respected elder by the fire. Every named mortal belongs to a household with a purse, a dwelling, a diet and a table, and what happens at that table shapes the body and the realm.

- **Households with a Purse** — pooled wages against rent, dowries, tithes and taxes, with heads, spouses, heirs, carers, servants, wards and lodgers, in eleven household forms from nuclear and extended to joint, communal, chosen and skipped-generation homes. The household decides whom to marry, whom to apprentice and when to leave for another city.
- **Eighteen Kinds of Dwelling** — hut, longhouse, townhouse, manor, palace, tent, cave, ship, tower, apartment, farmstead, stilt house, burrow, nest, a home beneath the water, a grown home, a house cut from rock and a courtyard house. Quality, rooms and furnishings set comfort, beauty, status and mood, and squalor breeds disease.
- **You Are What You Eat** — every diet is measured in energy, protein, fats, fresh food and minerals, and for stranger peoples in light, essence or charge. Famine children grow shorter and slower, the well fed grow taller, and a diet that falls short brings malnutrition.
- **Cuisines That Travel** — every culture cooks its own dishes from local ingredients, under its own tastes and taboos, by thirty-five methods from boiling and baking to earth ovens, parching and fermenting, at nine kinds of meal from daily fare and feasts to travel food and food bought in the street. Cuisines spread with contact and diaspora, fine food marks rank, and who may eat with whom is a rule of its own.
- **Taverns and Inns** — gossip runs through them, schemers and mercenary captains recruit in them, brawls break out in them, caravans sleep in them, and the innkeeper sells what was overheard.
- **Drink and Its Customs** — every people decides which of eleven kinds of intoxicant, from brews and wines to stimulants and resins, are taken, by whom and when: daily, at feasts, in rites, in mourning, as medicine, for guests, for work or for courage before a fight. Brewing feeds the economy, sacred drink gives mystics their visions, dependence ruins lives and feasts end in brawls.
- **House Duties** — food, water, fuel, cleaning, textiles, the care of children, elders and the sick, animals, repairs, household rites, teaching the young at home and keeping the accounts, and each culture's rule for who does each.
- **Hours in a Year** — every class divides its year between work, rest, worship, leisure, travel, service, learning, care, art, housework, sleep, civic duty, training, company and mourning. Rest days and long festivals cost output and buy cohesion, and forced labour takes the hours back.
- **The Shape of a Day** — time budgets by class and age, sleep, washing and grooming customs, servants, nineteen leisure pursuits from games, dance and storytelling to gardening, bathing and keeping animals, tourism, and norms of personal space.

**In your world:** Sailors on a long voyage ran out of fresh food and fell sick for want of it. The survivors told their story in the harbour tavern, the gossip spread through the port, and the next fleet would not sail without the ways of keeping food that saved its crews.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/16-strange-flesh.jpg"><img src="common/assets/images/dlc-covers/16-strange-flesh.jpg" width="220" alt="Strange Flesh box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/16-strange-flesh.jpg"><img src="common/assets/images/dlc-backs/16-strange-flesh.jpg" width="220" alt="Strange Flesh box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 16. Strange Flesh

*Not every people breathes. Not every people dies.*

Your scouts report an enemy that does not bleed. Blades pass through it. Somewhere beneath the waves, another people writes in shell inlay and fights in three dimensions. Nineteen biologies beyond the human rewrite every foundation of your world, from how a people eats and breeds to how it casts, decides, makes war and dies.

- **Nineteen Biologies** — incorporeal, aquatic, aerial, subterranean, hive, plant-like, construct, ageless, shapeshifting, gaseous, crystalline, undead, fungal, colonial, energy, symbiotic, amphibious, metallic and liquid. Each changes body and harm, food and birth, culture and craft, war, disease and death.
- **Combine Them** — an aquatic hive, an ageless crystal people, a shapeshifting folk of the deep. The variants stack, and every system in the world reads the result.
- **Bodies Unlike Ours** — spirits are harmed in their coherence, not their flesh. Crystal folk shrug off blades but shatter under hammers and sound, and leave gemstones when they die. Aerial peoples break their hollow bones in falls. Liquid peoples slip through gaps and fear freezing and boiling, and metallic peoples rust and fear acid.
- **Lives Unlike Ours** — plant peoples feed on sunlight and fear fire, aquatic peoples smelt metal at volcanic vents, amphibious peoples live on land and water alike, building on stilts and below the surface, cave peoples know little of the stars, metallic peoples thrive on hot iron worlds, and the ageless keep their grudges for ever.
- **Their Own Wars** — three-dimensional sea battles, expendable hive soldiers who die with their queen, slow and stubborn plant armies, undead hosts that fear nothing but holy harm. Against the deep folk, daylight is a weapon.
- **Their Own Magic** — spirits cast by presence alone, gaseous peoples in colour and scent, aquatic peoples sing and gesture their rites but cannot ink them, and the hive casts as one mind.
- **Their Own Minds** — constructs feel no loss aversion but follow orders beyond their purpose. Hive minds suffer total groupthink and over-protect their breeders. The ageless cling to sunk costs and ancient grudges.

**In your world:** When the crystal folk's old ruler died, the tomb filled with the gemstones of the ruler's body. Human robbers broke in, defiled it and drew down the curse of the crystal people's god, and in the war that followed hammers mattered, because blades barely scratched the defenders.

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

A guest is killed at a feast. In one hall it is the unthinkable crime, and the host's line will carry the infamy for generations. Across the river it is merely frowned upon, and soon forgotten. Every culture and every cult in your world holds its own judgement of right and wrong, and judges every act, every guest and every ruler by it.

- **Sixty-Seven Acts, Six Stances** — from killing kin, usury and necromancy to lying, tomb robbing, fixing a contest, sheltering strangers and apologising, each act is required, admirable, acceptable, frowned upon, shameful or unthinkable. The verdict moves opinion, renown, a ruler's legitimacy and the doer's own guilt.
- **Every Deed Is Counted** — deceit in intrigue and trade is lying, drinking past the culture's limit is drunkenness, and robbing graves, casting charms, feeding on a host and killing a sacred animal are all recorded against their doer, so the doer's conscience, every witness and the law each weigh them by their own stance.
- **Laws Born of Outrage** — an unthinkable act with no law against it builds pressure for one. Ethics drift with belief and doctrine, and a deep enough split tears a culture into factions or births a new people.
- **Honour, Face, Dignity and Purity** — in honour cultures one member's shame is the whole house's, and demands apology, compensation, a duel or vengeance. Face cultures dread public shame and refuse through intermediaries. Dignity cultures shrug off insults and trust the law. Purity cultures rank people by the rites, food and contact rules they keep, and a breach needs a cleansing rite.
- **Thirteen Kinds of Renown** — heroism, honour, piety, generosity, wisdom and skill sit beside cruelty, trickery and troublemaking, and beside mercy, justice, reliability and hospitality. Mercy eases surrender and lowers dread, justice raises legitimacy and calms unrest, and renown is held in six currencies, among them trust, which makes deals and loans cheaper, and learning, which draws pupils and offices.
- **The Pillory** — thirty-four punishments, from fines, flogging and exile to public shaming, stripped titles, shunning and a curse laid as a sentence, punish through body, purse or reputation, as hard as the culture's honour model allows. Shame left unrestored turns into a household grievance.
- **Rules of the Room** — twenty situations, from funeral, feast and court to mourning, sacred days, the workplace, the council and meeting a stranger, a made mind or one of the gifted, each with its own rules on speech, dress, gifts, laughter, weapons and food.
- **Will Against Custom** — every choice weighs desire, the bond with the other person and the norms of the room. Breaking a norm costs reputation, unless you are a rebel who enjoys it. Every custom keeps the history of where it came from.
- **Purity and Pollution** — corpses, birth, blood, forbidden foods, outsiders and trades such as tanning bar a person from temples and marriage until purified. Hereditary castes decide who works which trade, who lives in which district and who handles the dead.
- **What They Say, What They Do** — every judged act is weighed against the values its doer professes. A wide gap, once seen, costs trust, legitimacy and followers, and hands leverage to whoever knows.

**In your world:** A plague reached a city where touching the dead made a person impure. The avoidance slowed the contagion, but the sick were left without carers, and the low-caste gravediggers, who could not refuse the work, died first and in the greatest numbers.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/18-ties-of-blood.jpg"><img src="common/assets/images/dlc-covers/18-ties-of-blood.jpg" width="220" alt="Ties of Blood box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/18-ties-of-blood.jpg"><img src="common/assets/images/dlc-backs/18-ties-of-blood.jpg" width="220" alt="Ties of Blood box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 18. Ties of Blood

*The copper hair of the Varns. The madness of the Varns, too.*

Generations of cousin marriage have kept the crown in the family. They have also given the heir a fragile constitution and a grandparent's madness. Every face in your world is written in a genome that passes by real rules of dominance, and every union is a move in a long game of claims, alliances and inherited risk.

- **True Genetics** — sixty loci in seven groups: looks, body, senses, temperament, aptitude, predisposition and gifts. Height, build, skin, hair, eyes, face and voice pass by Mendelian rules, alongside longevity, fertility, disease resistance, madness, giant blood and divine blood. Portraits keep the same face across a whole life, and a child who looks too much like the wrong parent exposes a secret parentage.
- **Born Able** — aptitude loci set how far and how fast memory, number sense, language, music and coordination can grow with upbringing, and temperament loci lean a child toward the parents' nature. Sense loci, lung capacity and pain sense shape perception, diving and how much an old wound hurts, and lines that carry twinning bear twins whose birth tests every succession custom.
- **The Price of Pure Lines** — inbreeding raises the chance of heritable conditions, so royal houses must choose between tight claims and healthy heirs. Law and ethics decide which degree of cousin is forbidden.
- **Kinship Systems** — five rules of descent, four customs of residence and nine forms of kin group, from lineages and clans to moieties and houses. Lines are named by side, first or second, in each culture's own words and never by sex. Where cousins are called siblings, marriage rules change; where titles pass through the second line, a sibling's child inherits.
- **Union Alliances** — pair, plural, group, serial and contract unions, cousin matches and exogamy by clan, house or moiety, with payments to one family, from one family, both ways or in labour. Lineages that exchange partners build lasting alliances, and the givers come to outrank the takers.
- **Nine Ways to Inherit** — equal shares, the eldest child, the youngest, the second line, election, merit, seniority that passes to the eldest of the line before any child, a will that names the heirs, or return to the kin group. Wills are read, contested by kin, forged and set aside by law.
- **Other Ways to Be Born** — two sexes, sexes that change with age, sexes chosen in a fertile phase, hive castes of worker, soldier and breeder, or budding and fission. Succession, unions and war all follow the system.
- **The Gift in the Blood** — magical aptitude runs in the genome, recessive and rare. Mage orders test children for it, bloodlines are bred toward it, and cultures honour, fear, persecute or tax it, while persecution thins it out.
- **Duties of Kin** — twenty-one kin roles, from grandparents, the siblings of parents, in-laws and cousins to sworn kin, foster kin, step-parents and half-siblings, each owing what the culture says, and kin groups from kindreds to clans, phratries and moieties with land, heads and councils.
- **Eighteen Kinds of Home** — eleven household forms, among them grandparents raising children when the middle generation is gone, live in farmsteads, stilt houses over flood plains, burrows for peoples below ground, nests for peoples of the air, homes under water, grown houses that mend themselves, rock-cut rooms that keep an even warmth and courtyard houses for extended families. Each dwelling fits its land and its people's bodies.

**In your world:** To keep two claims in one house, the Varns married cousin to cousin. Their heirs came out sickly and touched with madness, rival houses contested every succession, and each challenge drove the Varns to marry closer still.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/19-the-teeming-millions.jpg"><img src="common/assets/images/dlc-covers/19-the-teeming-millions.jpg" width="220" alt="The Teeming Millions box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/19-the-teeming-millions.jpg"><img src="common/assets/images/dlc-backs/19-the-teeming-millions.jpg" width="220" alt="The Teeming Millions box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 19. The Teeming Millions

*History is made by the many. Now you can count them.*

The war is over, and the valley counts its dead. Not as one number: as a missing generation of those the culture sent to fight, a crowd of bereaved partners, a wave of orphans, fewer children in the years to come and, where custom bends, new hands taking up the crafts. Behind every named mortal stand the many, sorted by age, by the sexes their own biology knows, by class and by condition, and every famine, plague and war reshapes them.

- **Living Cohorts** — every community counts its infants, children, youths, adults, elders and ancients by sex, class and condition: veteran, maimed, sick, enslaved, captive, orphaned, displaced, indebted or gifted. Births follow food and stress and are counted among those who bear young, or among every adult of a people that buds, spreads by spores or is made. Famines take the youngest and the oldest first; wars take whoever the culture sends to fight.
- **Faces from the Crowd** — when the crowd produces something notable, a famine orphan or a plague's first victim, one person is lifted out and given a name, a memory and a life, and orphans and refugees step out more often than most. No one named is ever merged back into the crowd.
- **Generations** — nineteen kinds of formative event, from war, plague and golden age to long winters, peace and persecution, mark the generation that grew up under them, and its beliefs bend with it. When the last of a generation dies, the movements it held down finally rise.
- **Work for Every Adult** — adults go to nineteen kinds of work, from fields, herds and nets to mines, armies, temples, offices, roads, works, healing, teaching and the arts. Class, price, skill, law, debt and kin duty decide who goes where, and output follows workers, skill, tools and land.
- **The Long Transition** — towns, literacy, schooling among those who bear young and surviving children slowly lower birth rates. The people grows old: fewer levies, more elders, a different politics.
- **Rising and Falling** — a mortal may be ennobled, grow rich, be ordained, freed or adopted into a house, or be ruined, enslaved, cast out or exiled, and each moves them between classes as far as the culture allows.
- **Diasporas** — migrants follow their kin, and each wave pulls the next. Diasporas send money and news home, arrange unions across the sea, build foreign quarters, and in time assimilate or become a new people.
- **Roles by Culture** — who may hold office, own property, fight, preach or inherit is set by sex, age and class, so matriarchies, egalitarian clans and caste societies all grow from each culture's own rules, and drift after every war.
- **Policies of Number** — seventeen instruments, from rewards, taxes and child limits to settlement grants, permits, expulsions, health campaigns, immunisation and sanitation, by which realms, faiths and peoples try to grow, hold or reshape their numbers.

**In your world:** A conquest left the defeated people a war generation that would not forget. Their children grew up on the stories, and when the last veteran of the conquest died, the movement the conquerors had suppressed for decades rose in the capital.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/20-many-banners.jpg"><img src="common/assets/images/dlc-covers/20-many-banners.jpg" width="220" alt="Many Banners box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/20-many-banners.jpg"><img src="common/assets/images/dlc-backs/20-many-banners.jpg" width="220" alt="Many Banners box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 20. Many Banners

*One city. Divided by faith this decade, by class the next.*

A dyer belongs to the river people, keeps the faith of the city's patron god, holds a guild seat, is a citizen of the city and a veteran's child, all at once. In the year of the holy war the dyer marches with the faith. In the year of the famine, with the class. Which banner each person follows decides who fights whom in your world.

- **Fourteen Layers of Self** — people, faith, class, locality, house or clan, profession, generation, realm, circle, language, kind, cause, gift and calling. Every mortal, every settlement and every people holds all of them, each with its own strength.
- **Salience** — holy wars raise faith, famines raise class, invasions raise people and realm, strikes raise the guild, and persecution raises the persecuted layer for generations. Remembrance days, elections, matches between towns, disasters and the arrival of newcomers each raise their own layers. Sermons and propaganda stoke it, segregated districts sharpen it, and mixed unions and mixed guilds blunt the lines they cross.
- **Tongue, Kind and Cause** — a banned or revived language binds its speakers across peoples and realms. Where born and made beings, or peoples of different bodies, live side by side, kind becomes an identity, sharpest under laws that treat kinds differently. A movement's members keep their cause long after the crowd has gone home.
- **Lines of Fracture** — factions, revolts, riots and civil wars split along whichever identity burns brightest. A shared realm identity steadies the state; a strong sub-identity breeds separatism. Each group tells its own history.
- **Thirteen Tenets** — legalism, egalitarianism, divine right, mercantilism, militarism, rationalism, cosmopolitanism and more spread through scholars, books, schools and trade routes, each appealing to a different class. A realm that adopts one changes how it rules.
- **Revolutions of the Mind** — an egalitarian creed, an unhappy class and a weak realm add up to a revolt that aims at the government itself. Printing and universities breed new ideologies faster, and revolutions can write constitutions.
- **Creeds Against the Gods** — anti-god movements drain faith from the sons and so weaken their very existence. The gods answer with miracles or persecution. Other creeds turn to the Creator alone.
- **Six Ways of Revival** — under foreign rule a people may restore the old ways, rally around a prophet who joins old and new, adopt the ruler's culture wholesale, wait for a foretold sign and rise all at once when it comes, withdraw into settlements of its own, or leave for a new land. Each revival aims to revive a language, restore an old god, expel the foreigners, take back the land, restore its own rule or restore its customary law.
- **Fourteen Causes** — movements for abolition, independence, revival, land reform, the franchise, peace, conservation, labour, faith reform, temperance, the rights of made minds, equal standing, learning and health press for their laws, back worker bodies or split a faith.

**In your world:** A distant empire pressed its customs on the river people. A prophet rose promising the old god's return, the revival drew in the humiliated, and within a generation the city's riots ran along the lines of people and faith instead of class.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/21-fire-in-the-streets.jpg"><img src="common/assets/images/dlc-covers/21-fire-in-the-streets.jpg" width="220" alt="Fire in the Streets box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/21-fire-in-the-streets.jpg"><img src="common/assets/images/dlc-backs/21-fire-in-the-streets.jpg" width="220" alt="Fire in the Streets box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 21. Fire in the Streets

*It started with one stone thrown at the bread line.*

Bread doubles in price. A few apprentices throw stones, and nobody stops them. Their nerve lowers the fear of the dockers, whose anger tips the dyers, and by nightfall a district is burning. Every crowd in your world is made of people with their own breaking points, and the fate of a city depends on who moves first.

- **Every Person Has a Threshold** — anger, anxiety, conformity, hunger and friendship decide when each mortal and each slice of a crowd will join a riot, a lynching, a strike, a procession, a boycott or a revolt.
- **Cascades, Not Dice** — eighteen kinds of spark start it: a price spike, an execution, a sermon, an omen, an arrest, unpaid wages, a lost match, a victory, a great funeral, an election and more. If enough join to tip the next group, it spreads district by district. Its size and violence emerge; they are never rolled.
- **Seven Crowd Feelings** — anger, fear, fervour, grief, hope, joy and solidarity rise and fall in every town. Grief follows mass deaths and a beloved ruler's passing and drives mourning processions, hope lowers the threshold for demonstrations and turns to anger when betrayed, and solidarity makes strikes and boycotts come easier.
- **Fifteen Ways to Act Together** — besides riots, panics and lynchings, crowds rejoice after a victory, demonstrate without violence, boycott a guild until its income falls, hold vigils, occupy a square or a workshop until its work stops, carry petitions whose answer moves the ruler's legitimacy, and leave together in an exodus that fills the roads with the displaced.
- **The Watch and the Agitator** — watchmen and garrisons raise every threshold by deterrence, and a charismatic agitator lowers them. The same spark dies in one city and burns down another.
- **Mobs** — crowds with a size, a target, an anger and leaders. They burn districts, storm the granary, the temple or the palace, lynch a scapegoat for a crime they never committed or open the gate to the besiegers, then scatter by fatigue, force or concession.
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

Three houses sit at one wedding table. A cousin of the couple will leave the tournament with a crushed knee, a steward will meet a rival's agent behind the stables, and somebody's affair will be noticed by the wrong in-law. Gatherings are where your world's stories collide, and the traditions that summon them shape the lives of the people who keep them.

- **Twenty-Three Kinds of Tradition** — festivals, fasts, rites of passage, taboos, offerings, pilgrimages, hospitality laws, martial displays, body marking, ancestral rites, fairs, welcomes, reconciliations, thanksgivings and more, each with its season, its cost and a real effect on those who keep it, from cohesion, piety and safety to health and the bonds between those who take part.
- **Customs That Shape Lives** — a pork taboo empties the pens, a taboo on winter fighting shapes the campaign year, and a hospitality law makes roads safer and guest-killing a grave infamy. Great victories, plagues and miracles found new customs.
- **Rites of Passage** — birth, naming, coming of age, union, elderhood and death, with initiation into an order and the departure of one who leaves home. Welcome rites turn strangers into guests, reconciliation rites end a feud when both sides keep them, and thanksgivings follow plenty, peace and recovery.
- **Thirty-Eight Kinds of Gathering** — feasts, weddings, coronations, tournaments, hunts, summits, fairs, public trials, executions, wakes, musters before a campaign, days of remembrance, reunions of scattered kin, gift exchanges and more. Guests come by bond, obligation and distance, and romances, plots, oaths and desertions crowd into a single evening.
- **Death at the Table** — any gathering can become a massacre, judged by the guest laws of those who hear of it. Crowded festivals spread disease, and poor households that cannot afford a rite lose face.
- **Marked Bodies** — tattoos, scars, piercings, cranial shaping, filed teeth, hair, paint, stains, brands and implants carry thirteen meanings, from status, clan, deeds and marriage to faith, profession, beauty, healing and bound labour. A warrior's tattoos count their kills; an exile's brand names the crime.
- **Names with Power** — names from a parent, a clan, a child, a birthplace, a trade, a forebear or the event of a birth, a secret name behind the public one, new names at initiation, marriage, vows or adoption, epithets others give for a deed, and a posthumous name given at the funeral, after which speaking the living name may be taboo.
- **Age-Sets** — those initiated together form a named set that rises from children and youths through young adults to junior and senior elders and the ancients. Each culture sets what each grade does, war, herding, labour or council, so a people with no martial duty sends no grade to war. Delay the promotion feast and the young grow restless.
- **Tending the Dead** — eight roles, from those who wash, prepare, carry and keep the dead to the grave makers, their standing, and ten ways a culture treats remains, with what each does to health, land and relics.

**In your world:** A chieftain murdered a rival at a wedding feast. The chieftain's own people held guest-killing unthinkable, so the infamy outran the victory, and the massacre became a yearly day of mourning that kept the grievance alive for generations.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/23-the-gift.jpg"><img src="common/assets/images/dlc-covers/23-the-gift.jpg" width="220" alt="The Gift box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/23-the-gift.jpg"><img src="common/assets/images/dlc-backs/23-the-gift.jpg" width="220" alt="The Gift box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 23. The Gift

*A gift unreturned is a debt. A debt unpaid is a war.*

The chief of the eastern islands arrives with canoes heaped with dried fish and burns half of them on the beach to prove the islands can spare it. Now you must give more, or bow. Every gift in your world is weighed by what the receiver loves, recorded and answered in kind, or remembered as a debt that someone, someday, will collect.

- **The Gift Ledger** — every gift is valued by the receiver's own tastes and never forgotten. To refuse is an insult, to return late is a debt of status, and to give more is the way to rise.
- **Sixteen Occasions** — courtesy, feasts, offerings, unions, alliances, relief, births, funerals, amends for a wrong, patronage, hospitality, farewells, homecomings, initiations and more, each with its expected return, the debt it sets and the standing at stake. Amends accepted at a feast end a feud; amends refused deepen it.
- **From Hearth to Heaven** — households, houses, realms, cults and gods all trade gifts under the same law of obligation, so a village and a god can owe each other in the same coin.
- **Competitive Giving** — chiefs claim rank by giving away or destroying wealth at feasts. A gift answered with more puts the first giver in debt, and two houses that keep outgiving each other drain their treasuries while their standing climbs, until one side breaks.
- **Sacred Circuits** — famous treasures travel for ever along a fixed ring of communities. Holding one brings prestige for a while, and the circuit binds distant islands in peace and the duty of hospitality. A holder who keeps a treasure instead of passing it on loses standing where passing is expected and gains it where keeping is honoured.
- **Grace and Patronage** — a giver may release a debt by grace, raising their own standing and the receiver's loyalty. Patrons' gifts flow down to clients, artists and followers and are repaid in service and praise, not in kind, and gifts to the bereaved are owed back at the giver's own losses.
- **Gifts to the Gods** — every sacrifice puts a god in debt. Gods who answer generously gain standing, gods who ignore their offerings lose it faster, and each son sees its debts to the peoples set out plainly.
- **Union Payments** — payments to one family, from one family, both ways or in labour obey the same law, binding the kin of both partners long after the wedding.

**In your world:** Two island chiefs tried to outgive each other at feast after feast until the second chief's treasury broke and that chief's rank fell. The second chief's people had made offerings to their own god for luck all the while, and the god who took and gave nothing back lost standing among them fast.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/24-muse-and-market.jpg"><img src="common/assets/images/dlc-covers/24-muse-and-market.jpg" width="220" alt="Muse and Market box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/24-muse-and-market.jpg"><img src="common/assets/images/dlc-backs/24-muse-and-market.jpg" width="220" alt="Muse and Market box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 24. Muse and Market

*Art that moves a people. Forgeries that fool a king.*

A poet's lament for the fallen is sung in every hall, and a generation later the people's appetite for war has cooled. Across the city, pilgrims still kneel before a saint's relic that a forger made in a cellar. Here art has a grammar, a lineage, a price and a message, and the classics decide what a people believes.

- **Nineteen Art Modes with Grammar** — verbal art, music, dance, performance, flat and solid images, built form, textiles, worn and culinary art, scent, light, recorded and interactive art, landscape, the body, the art of made minds, art for touch and art passed from mind to mind, each with real structure: scales, rhythms and instruments, metres and stanzas, palettes and motifs. Poetry follows the sounds of its own tongue, so it never translates cleanly.
- **Forms Are Born and Die** — an inspired master invents a form, often by fusing two where cultures meet, or a lament after a plague. A form dies with its last practitioner if no notation survives, and banning a people's forms is a humiliation they resist.
- **Art That Argues** — every work carries a message. A poem mourning the war dead cools a people's taste for war; a conqueror's statue swells the conquerors' pride and keeps the conquered resisting.
- **Troupes on the Road** — touring players carry songs, legends and rumours along the trade routes, perform at feasts and fairs, and sometimes spy. Scribes copy books, printing multiplies them, and realms commission propaganda.
- **Collectors, Critics and Curators** — prices follow renown, provenance and taste. Collectors bid at auctions that auctioneers run, critics raise or sink a movement and its prices, curators choose what a city shows, and restorers mend old works and sometimes hide a fake. Courts compete for artists, and art movements with manifestos fight canon wars to become the next orthodoxy.
- **Eight Kinds of Forgery** — artworks, relics, documents, brands, coins, lineages, seals and whole identities. Each is exposed by its own expert: moneyers catch false coin, genealogists false descent and clerks false seals, while an undiscovered forgery can enter the canon.
- **Rights to a Song or a Recipe** — thirteen kinds of cultural right, from songs, dances, stories and rites to designs, names, titles, trademarks, market privileges, recipes, techniques, performances and likenesses, are created, inherited, bought, licensed, stolen, granted, won in contests, passed on with a union or held in common. A technique right is entered as a patent where the realm keeps a registry.
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

- **Eight Kinds of Club** — team games, races, combat, athletics, animal contests, mind games, water sports and hunts, played at arenas and festivals season after season in leagues of rival clubs. Animal-contest clubs keep and breed their animals, and mind-games clubs train players and draw patrons.
- **Fandoms** — every club holds a share of the city's heart, counted cohort by cohort, district by district.
- **The Betting Floor** — wagers on every race move household wealth up and down. A lucky season lifts a family; a bad one sinks it into debt.
- **Thrown Races and Doped Champions** — fixing a contest for a wager or a patron, and enhancing contestants, are acts each culture judges and crimes wherever the law makes them so. Exposure sinks the club and its players, voids the wagers and can empty the stands into the streets, and leagues that forbid enhancement test for it and ban.
- **Circus Factions** — when the colours line up with class, district or faith, a club becomes a political faction with real power over public opinion. Rulers can buy a club, and the voice of its crowds with it.
- **Riots of the Hippodrome** — a club's crowd is a riot waiting for its spark. A lost championship plus a tax rise can tip enough thresholds to burn a capital.

**In your world:** A disputed race result fell on the day of a new tax. The Greens' fans crossed the riot threshold and the hippodrome quarter burned. The court's Blue favourites demanded purges, and the Greens' patron senator marched on the capital with a private army.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/26-tongues-of-ages.jpg"><img src="common/assets/images/dlc-covers/26-tongues-of-ages.jpg" width="220" alt="Tongues of Ages box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/26-tongues-of-ages.jpg"><img src="common/assets/images/dlc-backs/26-tongues-of-ages.jpg" width="220" alt="Tongues of Ages box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 26. Tongues of Ages

*Every name means something. Every word has a history.*

A scholar kneels before a stone carved in two scripts: one dead for ages, one still spoken in the market. Seasons later the scholar reads a forgotten ruler's name, and with it a lost technique, and an error that will one day become a legend. Your world's languages drift by real sound laws, so cognates, dialects and dead tongues are born from its history.

- **Sound Change** — every language gathers ordered sound laws through contact, prestige, migration or drift. Daughter tongues split away, cognates emerge, place names fossilise older forms, and scholars can reconstruct the proto-language.
- **Grammar Matters** — word order, isolating to polysynthetic morphology, cases, genders, evidentiality and honorific levels decide how hard translation is and how likely a treaty clause is to be misread. Feared words give way to euphemisms.
- **Counting in Tens, Twelves or Sixties** — eight numeral bases, from decimal, vigesimal, duodecimal and sexagesimal to octal, quinary, binary and counting along the body. Bases with many divisors ease fractions in trade, astronomy and the calendar, body tallies hold back large sums until writing grows, and contact carries a base from one tongue to another.
- **Names with Meanings** — every name is built from real roots with a recorded meaning, epithets are coined from deeds, such as "the Silver-Handed", and every foreign tongue gives a place its own name.
- **Speech Beyond the Voice** — twelve modalities: voice, sign, scent, colour, mind to mind, data, chemistry, touch that works in darkness, vibration carried through ground or water and overheard by those who sense it, electric fields under water, and whistled and drummed speech that crosses valleys faster than any runner. Between modalities, only interpreters bridge the gap.
- **Words That Shift** — meanings widen, narrow, sour, improve, spread by likeness or by nearness, or turn into their opposite over generations, so an old treaty read with new words can break. Nine registers set how words are used, from sacred, poetic and archaic speech to taboo words replaced by roundabout phrases, the terms of a craft, honorifics whose misuse insults, fast-changing slang and the legal register that wins in court.
- **Scripts That Evolve** — pictograms to logograms, syllabaries, abjads and alphabets, plus knots and notches, invented, reformed, simplified, borrowed, imposed by a conqueror, revealed by a god or reshaped by printing and machines. Hard scripts keep literacy low and empower a scribe caste; an alphabet breaks their monopoly. Records last as long as their sixteen media allow, from clay and stone to silk, wood slips, cloth, potsherds and electronic records that an outage can lose.
- **Decipher the Dead** — bilingual stones, living cousin languages and patient scholars unlock lost scripts over seasons. Partial readings give partial knowledge, and mistranslations live on as theories and legends.
- **Barriers and Bridges** — every treaty, sale, sermon and battle order passes through intelligibility. Interpreters bridge the gap, lingua francas ride the trade routes and pidgins become creoles. Sign languages grow among the deaf, the silenced, traders on many-tongued frontiers and workers in loud mills, and ten sociolects, from thieves' cant to the speech of youth, soldiers, clergy and scholars, mark their speakers.
- **Tongues of Power** — realms make a language official, liturgical, suppressed, protected, standardised or one of two official tongues. Scholars and rulers construct new languages, dead tongues return through revival with a strong identity, and an endangered tongue draws revival movements until its last speaker dies. A conquered people with a great literature can conquer its conquerors, and each son has a sacred tongue whose words are rites.

**In your world:** A cruel law cut out the tongues of heretics. So many went mute that their village grew its own sign language, and the heresy went on spreading in a tongue its judges could not understand.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/27-the-rewritten-past.jpg"><img src="common/assets/images/dlc-covers/27-the-rewritten-past.jpg" width="220" alt="The Rewritten Past box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/27-the-rewritten-past.jpg"><img src="common/assets/images/dlc-backs/27-the-rewritten-past.jpg" width="220" alt="The Rewritten Past box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 27. The Rewritten Past

*History is written by the victors. Until someone finds the old stone.*

The new dynasty's chronicle says its founder was born of a god. The folk songs of the valley say the founder was a stable hand who poisoned a master. A merchant's account from across the sea says both are wrong. Here every event has one truth and many tellings, and you alone can lay them side by side.

- **Accounts and Truth** — fourteen kinds of account, from official chronicles, folk memories, foreign accounts, gospels, epics and inscriptions to genealogies, songs, travel accounts and law records, set down in books, on stone, in song, in performance or in marks on the body. Each glorifies, vilifies, omits, justifies, laments, mocks or warns, and each is measured against what truly happened.
- **Songs That Mock** — a song changes with every singer and outlasts suppression. Told as folly, a deed lowers its doers' standing; told as loss, it raises grief and memory; told with its reasons, its harm to standing softens. Genealogies back claims, and forged ones press false claims until a genealogist exposes them.
- **Damnatio Memoriae** — strike a name from the records, deface every inscription, smash every statue. The figure fades within a few generations, unless folk memory or a foreign chronicle keeps the name alive.
- **Revisionism** — new rulers rewrite the chronicle to suit their claim. Older texts survive, and the scholar who finds one holds a dangerous secret: the true history.
- **Founding Myths** — every people and every realm has its founding story. Belief in it holds the people together and the throne up, and a single inscription that contradicts it costs both.
- **Far Places and Old Laws** — travel accounts carry knowledge of distant lands and raise contact with them, law records fix customary law and back the courts and the movements that seek to restore it, and warning accounts raise fear of what they warn of.
- **Lost Lands** — memories of old borders breed claims and movements centuries later, the hidden root of many wars.
- **Days of Remembrance** — victories, massacres and foundings are relived on every anniversary through traditions and gatherings, keeping pride and grievance alive. Neglect them and the memory fades.

**In your world:** A usurper's chronicle claimed divine descent. Generations later a ploughman turned up an inscription naming the usurper's true parent, a scholar made the scandal public, the dynasty's legitimacy cracked, and the old border it had once surrendered became the rallying cry for a new war.

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

- **Materials with Real Physics** — forty-eight materials with hardness, edge, weight, decay, sanctity and corruption, from flint, clay and silk to rubber, lacquer, polymers, the tissue of great beasts, star metal from fallen comets and the tissue of dead gods. Eleven origins tell where each came from: grown by living craft, dug from fossil beds, salvaged from relics and wrecks beyond their finders' own skill, or taken from the remains and bargains of outer beings, with their risks. Each world adds exotic substances of its own.
- **Forty-Seven Goods in Four Families** — subsistence, industrial, strategic, and luxury and sacred, from grain, fodder and halite to oil, sugar, spice, honey, wax, pottery, books, paper, glassware, soap, ink, siege materiel, incense and magical reagents. People eat per head, and what a town can store depends on the granaries it has built.
- **Many Ways to Make a Thing** — twenty-nine processes run in twenty-seven kinds of workshop, each process with up to ten methods ordered by era. Iron comes from a charcoal bloomery, a coal blast furnace, an electric arc or a divine forge. A culture that reveres nature refuses the dirty method, and early adopters put the old artisans out of work.
- **Paper, Print and Rope** — paper mills, printing houses and ropewalks join potteries, glassworks, dyeworks, scriptoria and evaporation works. Printing moves from carved blocks to movable type and the rotary press, lowers the cost of books and accounts and speeds the spread of ideas and movements, while ropewalks supply ships and works.
- **Seven Grades of Quality** — poor to masterwork to artifact, set by skill, method and material. Fine meals and fine clothes lift moods and are what nobles demand, while meat, fish and milk rot unless dried, smoked, iced or kept by magic.
- **Rivers Industrialise First** — nineteen sources of energy, from muscle, water and wind to heat, fuel, electricity, fission, magic, belief and divine rites, power production, so geography decides where industry rises. On frozen worlds heat is survival, and a fuel shortage means whole communities dying of cold.
- **Chains That Break Upstream** — ore to metal to weapons, hide to leather to armour, grain to flour to bread. Seventeen work hazards strike the workers, from cave-ins that sometimes break into caverns full of beasts to falls from scaffolds, burns at forge and kiln and the dust that leaves miners and millers short of breath. Scarce iron or horses become war aims.
- **Smoke, Slag and Dye** — seven pollutants: air, water and soil, heat that warms rivers and drives off the fish, noise that raises stress, light that hides the faint stars from a city's astronomers, and radiation that sickens bodies and scars the land. Fourteen chemical products, from dyes, soap and fertiliser to ink, glaze, preservatives, acids, solvents, adhesives and explosives, each carry their own hazards.

**In your world:** A river town took up the coal blast furnace. Its cheap iron ruined every bloomery upriver, the idle smiths swelled the radical factions, the river turned foul and the fish failed, and the nature-revering villages downstream turned against the town that armed the realm.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/29-coin-of-the-realm.jpg"><img src="common/assets/images/dlc-covers/29-coin-of-the-realm.jpg" width="220" alt="Coin of the Realm box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/29-coin-of-the-realm.jpg"><img src="common/assets/images/dlc-backs/29-coin-of-the-realm.jpg" width="220" alt="Coin of the Realm box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 29. Coin of the Realm

*Debase the coin, fill the treasury, and watch the merchants walk away.*

A dragon's hoard comes home in triumph, and soon the luxury markets fill with silver and its price tumbles. You are watching a real economy. Every market town posts prices for forty-seven goods, every coin carries its purity and the trust behind it, and bankers lend to warlords at rates set by their record. Nobody scripted the boom. Greedy merchants guessed, hoarded, and were ruined.

- **Prices That Move** — every market holds prices for all forty-seven goods, moved by stocks, consumption, distance, danger and tariffs. Bread barely bends with price, luxuries swing hard, and goods flow down every route from cheap to dear.
- **Coin and Trust** — each currency has a metal, a purity and a measure of trust. Debase it and the treasury fills today, then inflation bites, merchants sour and trade in that coin dries up. Reserves of gold and silver shore it up.
- **Bankers and Bankruptcy** — merchant guilds lend war loans at interest set by the borrower's credit. A realm slides from strained to default to restructuring. Another power may rescue it and take charge of its budget on its own terms, or it may repudiate the debt outright, ruining its lenders, losing all credit for epochs and turning the lenders' realms against it. Sanctions freeze a realm's credit abroad until they are lifted.
- **Loans That Change Hands** — loans are rescheduled by agreement, sold at a discount to a new lender who collects them, secured on land, goods or a person where bound labour is lawful and seized on default, and passed to heirs, who may be bound to pay them.
- **Booms Nobody Planned** — greedy merchants buy what they believe will rise and hoard grain through famine. Authorities may seize hoards in a dearth, stored hoards spoil, and traders corner a market, dump goods into a rival's, sell short to gain from a fall or spread a false report of a lost fleet until the truth arrives. Price spikes stoke unrest, the bust ruins the speculators, and cycles emerge from behaviour rather than script.
- **Tariffs, Embargoes and Black Markets** — eleven trade policies, from tariffs, subsidies, quotas and embargoes to tolls on routes and bridges and staple rights that make passing goods be offered first in a town's market. Smuggling swells with the price gap, and drugs, void materials and forbidden books move through smugglers at a premium.
- **Insurance and Its Temptations** — guilds, banks and mutual societies insure cargoes, houses, lives, crops, vessels, livestock, healing and ransom at premiums set by what they believe. Insured merchants take riskier roads, and one great loss, a long winter or a plague among the herds, can bring an insurer down and the banks with it.
- **Hoards, Changers and Bills of Exchange** — savings take six forms: buried hoards, deposits, investments, land that earns rent and survives debasement, stored goods that rise in a dearth and herds that grow by breeding. Insecure households bury coin that is lost when they die and found by later diggers. Money changers profit on rates that follow purity and trust, and bills of exchange carry credit without carrying coin.

**In your world:** A ruler debased the realm's silver to pay for a war. Foreign changers marked the coin down, the realm's own merchants stopped trading in it, the war loan fell due in good silver the treasury no longer had, and the default became a war of its own.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/30-the-salt-road.jpg"><img src="common/assets/images/dlc-covers/30-the-salt-road.jpg" width="220" alt="The Salt Road box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/30-the-salt-road.jpg"><img src="common/assets/images/dlc-backs/30-the-salt-road.jpg" width="220" alt="The Salt Road box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 30. The Salt Road

*Goods, gods and plagues travel the same roads.*

Two markets trade long enough and a road is born, with a name, a toll and a reputation. You follow a caravan through a mountain pass: mules and wagons, silk and spice, a pilgrim, a missionary and a wool merchant carrying a fever nobody has noticed yet. At the far end it unloads goods, news, songs and plague. Whoever holds the pass takes the toll, and whoever loses it starts a war.

- **Roads That Name Themselves** — steady trade between two markets makes a named route by road, river, sea, sky, tunnels through the deep, space, rifts or networks. Bridges, harbours and caravanserais raise its capacity, neglect lets it fade, and a famous road becomes a legend.
- **Caravans and Convoys** — every route is carried by real convoys with owners, cargo, guards and passengers, on sixteen kinds of carrier, from porters, pack animals, carts and sledges over snow to ships, rail, pipelines and orbital lifts. Bandits, pirates, beasts and enemy armies raid them, storms sink them, and a merchant house's ageing fleet is a strategic asset.
- **Open, Contested, Seasonal** — a route forms, opens, is tolled, contested at higher loss while sides fight for it, blockaded, closed or left to decay, or opens only in its seasons, so passes shut in winter and monsoon routes wait for the wind. Convoys stranded by a closed pass eat their stores, convoys quarantined at a plague port may carry disease if released early, and some turn back.
- **The Right Way to Carry It** — twelve cargo classes in twelve kinds of container: perishables need speed and preserving, liquids go in skins and tanks, cloth in bales, produce in baskets and live animals in cages, while oversize loads need special carriers and slow the convoy. Livestock walks and grazes on the way, and grain, stone and timber go by water wherever they can, so rivers and seas rule bulk trade.
- **Nine Ways to Lose a Cargo** — bandits, pirates, beasts, the sea, the weather, officials taking their cut, spoilage, pilferage by guards and crews, and breakage. Ten navigation aids, from compasses, charts, sounding lines and buoys to navigators who read stars, swells and birds, shore beacons, local pilots and fixes from a network, cut the losses at sea.
- **Tolls, Chokepoints and Blockades** — whoever holds the chokepoints sets the tolls, and high tolls send traffic round another way. Fleets and armies at a pass choke the flow, and merchant factions push for peace when their routes suffer losses.
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

A water-frame mill opens on the river, and a street of hand-loom workers is out of work by winter. Some steal, some emigrate, some sign on with the levy, and some join the radicals in the tavern. Now labour has a price and sometimes a chain: every job pays a wage, every class has a basket of needs it meets or fails, and every war can fill a slave market.

- **Wages and the Cost of Living** — every job at a farm, mill, army or office pays a share of the workplace's takings. Set against local prices for a class's needs, it becomes a standard of living that drives migration, loyalty, fertility and radicalism.
- **Thirteen Kinds of Want** — every class needs food, fodder, fuel and cloth, medicine, tools, arms, incense, luxuries and reagents, and beyond goods, water, a roof, a school and a court within reach. Thirst kills faster than hunger, a lost roof brings sickness and cold, a missing school leaves the young unskilled and a missing court lets feuds and self-help violence grow. Meet a class's needs long enough and part of it rises; fail them and it falls.
- **Why People Work Where They Do** — class, price, the works and resources at hand and the corvée all place workers, and so do laws that pin a caste or guild to its trade, skills that draw workers to what they do best, debts that send debtors to the creditor's work and kin duties that assign work by household role, with no default by sex.
- **Farmers to Artisans to Merchants** — promotion climbs the ladder, or turns into the clergy and the scholars through education, within the realm's law on mobility. Demotion runs down to the outcasts or into serfdom by debt, while a war hero is ennobled and founds a house.
- **The Idle Hands** — new methods and too many workers make the unemployed, who swell crime, emigration, the levy and the radical factions. Winter idleness on the farms fills the season with crafts, festivals and banditry.
- **Satisfaction at Work** — a content class works harder, and a resentful warrior class deserts. Inequality breeds crime and revolt, though cultures that prize hierarchy tolerate far more of it.
- **Corvée and the Unpayable Debt** — realms levy days of labour for walls, roads and wonders at the cost of harvests and goodwill, and folk tales remember the wonders built in suffering. Indenture binds debtors to terms some employers make impossible to finish.
- **Slave Markets and Manumission** — where law allows it, captives, debtors and the condemned are sold by skill, age and origin, so slaving economies grow hungry for war. Freedom comes by purchase, an owner's will, service, abolition or revolt.

**In your world:** A border war filled the slave market with captives. The mines that bought them undercut the free miners, who lost their wages and drifted into the abolitionist movement, and when the slaves rose, the movement already had its organisers.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/32-walls-and-wards.jpg"><img src="common/assets/images/dlc-covers/32-walls-and-wards.jpg" width="220" alt="Walls and Wards box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/32-walls-and-wards.jpg"><img src="common/assets/images/dlc-backs/32-walls-and-wards.jpg" width="220" alt="Walls and Wards box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 32. Walls and Wards

*Every city grows its own way. Every city burns its own way.*

On a dry, windy night a spark lands in a timber quarter with no fire brigade. By morning the old town is gone. Now the city must choose what rises: a planned grid of stone and wide streets, if the treasury and a planner allow it, the old quarter restored as it was, or the same crooked wooden lanes that will burn again. Meanwhile, quietly, the elites are claiming the burned land.

- **Twenty-Seven Kinds of District** — from farmland, markets, craft and temple quarters, harbours, citadels, palaces and necropolises to universities, arcologies, pilgrim quarters, caravan quarters at the city's edge and floating districts on rafts that rise with the floods, unlocked as a hamlet grows through village, town and city to metropolis, megalopolis and world city. No city rises without water and a granary.
- **Camps and Lazarettos** — camps of the displaced, made in haste, lack services and breed disease, crime and fire, and become slums or settled quarters if they last. Lazarettos hold the sick and new arrivals apart, cutting the spread of plague but drawing dread and stigma.
- **Rents and the Pushed-Out Poor** — temples, fountains and parks raise land value, while tanneries, prisons, crime and haunted memories lower it. Rents sort the classes street by street, and rising value pushes the poor outward.
- **Services by Reach** — twenty-three services, from wells, watch posts, healers, schools and bathhouses to courts, libraries, street lighting that lowers crime at night and pest control that keeps vermin from the stores, cover the streets around them. Beyond their reach come thirst, crime, disease, impiety and illiteracy, and a mine too far from any housing cannot find its workers.
- **Houses That Grow** — when services and goods arrive, shacks become huts, cottages, houses, townhouses and manors, tenements and tower blocks rise in dense cities and rulers hold palaces. When they fail, the houses sink. Slums spread wherever migrants outrun housing, feeding fever, crime and the mob.
- **Grids, Rings and Old Quarters** — a city grows organic, planned, in concentric rings of walls, on a grid, upward or in sprawl, and that shape decides how fire spreads, how goods move and whether inner walls hold. In a long winter, rationing may mean abandoning the old and the sick.
- **Rebuild, Move or Abandon** — after fire, flood, quake, storm, sack, eruption, sea wave, landslide, sinkhole or plague, a town is rebuilt on a plan, rebuilt as it comes, restored as it was at greater cost to keep its memory and monuments, moved to a safer site with a ruin left behind, or abandoned, its people sent away as the displaced.
- **Charity Against the Gutter** — nine kinds of relief, from granaries, alms, workhouses and parishes to foster care for orphans, sick houses, pensions for veterans, the maimed and the old, public kitchens and shelters. Almshouses, orphanages and leper houses take in the abandoned and their patrons gain piety; without them, beggars fill the streets and children fill the gangs.
- **Ready for the Worst** — fourteen measures, from levees, firebreaks, seawalls, drills and stockpiles to quarantine and immunisation plans and quake-proof building, keep a disaster from becoming a catastrophe. Afterwards rival realms send aid in goods, healers, labour, money, soldiers or transport that leaves debts of gratitude, and refusing a rival's help costs face.

**In your world:** A great fire gutted the timber harbour quarter. The city rebuilt it in stone on a grid, land values soared, and the dockworkers who could no longer pay the rents were pushed out to the slums beside the tanneries, where the next fever began.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/33-wonders-rising.jpg"><img src="common/assets/images/dlc-covers/33-wonders-rising.jpg" width="220" alt="Wonders Rising box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/33-wonders-rising.jpg"><img src="common/assets/images/dlc-backs/33-wonders-rising.jpg" width="220" alt="Wonders Rising box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 33. Wonders Rising

*Generations of labour. One wonder. One rival who finished first.*

The great dome was begun under a grandparent and is still open to the sky under a grandchild. Masons die, plague takes the scribes, the treasury fails twice, and across the sea a rival realm is racing to finish first. Win, and the wonder feeds your city's prestige and draws travellers from every coast. Lose, and you salvage a share of the stone while a half-built ruin gathers legends.

- **A Hundred and Forty-Two Structure Kinds** — temples, libraries, observatories, citadels, banks, shipyards, aqueducts, canals, dams, arenas, embassies, lighthouses and tombs, each with a real function. Granaries feed sieges, hospitals cut deaths from wounds, and observatories soften the terror of an eclipse.
- **Nothing Works Without Hands** — every building needs staff and upkeep, and as its condition falls its function falls with it. When plague kills the scribes, the library still stands but its knowledge is locked away.
- **Mud Brick to Hydraulic Concrete** — eleven building materials, each with its own strength, weathering, fire and water resistance. Concrete sets underwater for harbours, aqueducts and domes, and a civilisation that loses the technique cannot repair its old harbours.
- **Forms, Sections and Builders** — twenty-nine building forms, from halls, domes and vaults that span wide stores to stilt forms that stand in floods, and forty-five sections, from cisterns that hold water through siege and drought to chimneys that clear the smoke from a room. Households raise their own homes and shrines beside the works of realms, cults, companies, patrons and gods.
- **Begun, Abandoned, Restored** — a work is planned, built, completed, damaged or ruined. Left unfinished, it decays and gathers legends and treasure seekers; dismantled, it gives its stone to new building and leaves little behind; restored, it regains its function and renown at a price.
- **The Wonder Race** — wonders and cosmic works are unique to a world or to the whole cosmos. Several realms build at once, the first to finish wins, and envy follows the losers into every embassy.
- **Megastructures** — star cages that harvest a sun's essence and dim it to the fury of sun cults, orbital rings, world-bridges, void lighthouses for safe passage, and planetary engines that move a world's orbit.
- **Museums, Libraries and Trophy Halls** — six kinds of collection hold ten kinds of piece, from art, relics and fossils to manuscripts that draw scholars, maps, instruments and regalia whose loss shames a realm. Royal collections become prizes in every sack, and a trophy hall of banners and arms feeds the losers' grievance until its pieces come home as a clause of peace.
- **Eleven Gardens** — physic gardens supply healers, botanic gardens keep plants alive outside their range, menageries draw visitors and can save or spread a species, kitchen and roof gardens feed households and crowded cities, hunting parks shelter game, and sacred groves draw the gods of nature.
- **Lifting Water** — shadufs, waterwheels, screws, chain pumps and animal wheels, then wind pumps, steam pumps and electric pumps, raise water to the terraces and drain the deep mines. Without pumps, a mine floods the day it strikes the aquifer.

**In your world:** Two realms raced to finish the world's one great wonder. The loser salvaged a sliver of its stone and nursed its envy for generations, while the winner dedicated the wonder to its patron god, whose fame grew with every traveller who came to see it.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/34-heirlooms-and-relics.jpg"><img src="common/assets/images/dlc-covers/34-heirlooms-and-relics.jpg" width="220" alt="Heirlooms and Relics box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/34-heirlooms-and-relics.jpg"><img src="common/assets/images/dlc-backs/34-heirlooms-and-relics.jpg" width="220" alt="Heirlooms and Relics box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 34. Heirlooms and Relics

*The sword that killed three kings. The crown that made the fourth.*

Pick up any named sword in your world and read its life: who forged it, which house carried it, the battles it won, the night it was stolen, the barrow it was buried in. Kill enough with it and it becomes a symbol armies follow. Lose a crown and the ruler's legitimacy falls away until a new crown earns a name of its own.

- **Provenance** — every crafted item bears a maker's mark and a history of owners and deeds: kills, battles, coronations, thefts, burials, breaks, repairs, enchantments, gifts and captures. Renown grows with each, and a famous enough object becomes a symbol whose capture is a war aim.
- **Decorations That Remember** — studded, inlaid, engraved, runed or bristling with menacing spikes. Engraved images depict real events, so a shield showing the victory at Varn keeps that battle alive in the culture.
- **Artifacts of Obsession** — born when a crafter falls into a fever of creation, artifacts carry a unique name, the highest quality and often an enchantment. Greedy nobles demand them, and thieves and questing heroes plan around them.
- **Regalia** — crowns, sceptres, seals, rings and standards. Hold the realm's regalia and legitimacy follows. Usurpers hunt the crown, and losing it is a humiliation the whole realm feels.
- **Relics and Curses** — a people holds its relics sacred, uses them as tools, forbids them, keeps them as heritage, studies them for lost techniques at a risk of misuse, or trades them on markets at prices that rise with renown. Saints' remains and fragments of dead gods heal by chance, draw pilgrims and invite relic raids, and twenty kinds of curse, from bloodthirst, betrayal, wasting and madness to endless sleep, forgetting, sudden age, isolation that turns everyone away and weakness, follow whoever carries a cursed blade.
- **Lenses, Aids and Clocks** — spectacles restore sight lost to age and lengthen scholars' careers, telescopes predict eclipses, microscopes let healers see the agents of disease and choose their cure, hearing aids help the hard of hearing, and scripts read by touch let the blind read. Nine kinds of clock, from sundials, water clocks and fire clocks to chronometers that fix longitude at sea and electronic clocks, discipline labour, synchronise armies and keep ships off the rocks.
- **Locks, Vaults and Rotting Archives** — thieves pit their skill against eight kinds of lock, seals and guards. Worked locks open only to their rite, a matching power or a dispelling, electronic locks yield to intrusion and fail in an outage, and living locks open only to their makers' line. Papyrus rots in wet lands while clay survives fire and is baked hard by it, so what history remembers depends on what it was written on.

**In your world:** A usurper took the throne but not the crown, which loyalists smuggled to a mountain monastery. The usurper's legitimacy never recovered, the crown's return became the rebels' war aim, and the abbot who hid it entered its provenance beside four kings.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/35-underworld.jpg"><img src="common/assets/images/dlc-covers/35-underworld.jpg" width="220" alt="Underworld box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/35-underworld.jpg"><img src="common/assets/images/dlc-backs/35-underworld.jpg" width="220" alt="Underworld box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 35. Underworld

*Every city has two masters. Only one of them has a crown.*

The watch captain drinks free at the tavern by the docks, and everyone knows why. Beneath every crowned city runs a second government with ranks, income and a code of silence sworn like an oath. It collects protection street by street, owns a magistrate or two, and settles its borders in blood. You can let the realm crush it, hire it, or leave it running the harbour.

- **Eight Kinds of Family** — crime families, thieves' guilds, smuggling rings, pirate brotherhoods, street gangs that fight for single streets and recruit from the slums and camps, trafficking rings that work the routes and borders, fence networks and counterfeiting rings, each with its own ladder of ranks and its own treasury.
- **Fifteen Rackets** — protection, smuggling, gambling, fencing, kidnapping, counterfeiting, fraud, extortion, trafficking, intoxicants, data theft, loan sharking, arms, forged identities and poaching, each with its own income and its own victims.
- **Turf Wars** — families hold the city district by district. When they fight over a street, the maimings, killings and collapsing order are felt by everyone who lives there.
- **Officials on the Payroll** — bribes buy the watch, and hooks built from secrets and debts buy the magistrate. A judge with a hidden debt rules the way the family says.
- **The Code of Silence** — membership is sworn like an oath, and the family punishes its traitors. An informer has to fear the family more than the gallows.
- **Five Answers to Crime** — realms suppress the families with thief-takers, the watch and purges, co-opt them as informants, tolerate them for bribes while corruption grows and an outcry waits, license a trade under terms, from privateers to gaming houses, and tax it, or pardon criminals into the watch, the army and the offices. A realm whose law forbids bondage hunts the trafficking rings hardest.
- **Outlaws and Bounties** — an outlaw loses the law's protection, so anyone may rob or kill them without crime. Bounties draw hunters for coin, while an outlaw who spares the poor may become their folk hero.
- **Runaways and Sanctuaries** — outlaws, the accused, defectors, runaways from bondage, deserters, heretics, escaped captives and fleeing debtors seek shelter in temples, under guest right, by asylum, in the wilds, aboard ships, in guild halls, in embassies whose violation sours a whole realm, and in free cities whose charter frees a runaway who stays out its term.

**In your world:** A smuggling ring bought the harbour master through gambling debts. When the crown outlawed the ring's captain and posted a bounty, the dock wards hid the captain, the thief-takers came back empty-handed, and the captain's legend grew in every street the ring had spared.

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

The old ruler dies in the night and the succession law names a nine-year-old grandchild. By dawn you are watching a regent weigh ambition against oath, a marshal count the troops, and a cousin with a better claim count the nobles who would back them. Every realm in your world is a working state, with offices, a council, a court, a treasury, a law of succession and a legitimacy that can drain away.

- **Seventeen Kinds of Government** — chiefdoms, monarchies, theocracies, oligarchies, republics, tribal confederations, empires, hive councils, god-realms ruled directly by a son, military occupations, juntas, corporate states, technocracies, federations, communes, machine rule and colonial administrations. Each decides by its own rule: the ruler's will, a council vote, an assembly or a god's.
- **A Council with Work to Do** — the chancellor, marshal, treasurer, spymaster, chaplain, high judge, warden and the other councillors each take one of eleven tasks every epoch: courting a neighbour, drilling the armies, gathering taxes, breaking schemes, converting a province, purging corruption, overseeing works, promoting trade, advancing learning, keeping the people in health and keeping the borders. Their skill sets the result, their loyalty sets their diligence, and a disloyal spymaster leaks.
- **Twenty-Three Offices** — from ruler, regent and heir designate to governors, ambassadors, admirals, ministers, a chief scientist and the censor, who counts people and property so that taxes, levies and sumptuary laws reach further. Each office carries its own powers, fourteen in all.
- **Legitimacy and the Line** — lawful succession, a sound body where the culture demands one, honour, the church's blessing, victories, prosperity and age. A child heir brings a regency, rival claimants weigh their backing, and a preview shows who rules if the ruler dies tonight.
- **The Realm Outgrows Its Scribes** — administration is literacy, scribes, writing and roads. Expand past it and governors drift, taxes leak and provinces dream of secession, while peoples outside the ruling culture grow their own separatist movements.
- **Eighteen Taxes and the Leak** — land, poll, trade, consumption and tithe, income, property, inheritance and wealth, excise and licences, labour levies and taxes in kind, tolls on roads and bridges, a tax on every hearth and more, each falling on different classes. Tax farming raises the take and the corruption with it, and greedy officials skim until a just high judge audits them.
- **Twelve Mandates** — rulers order production, ban exports, build, open the granaries, impose curfews, clear slums, prepare for danger, enclose the commons, ration food and fuel through a siege or a long winter, call out corvée labour, quarantine districts and ports, or conscript soldiers. Rationing cuts deaths and breeds grievance by how fairly it is shared, corvée builds fast and breeds resentment, and every mandate touches several classes at once.
- **Court and Constitution** — ten court positions: steward, champion, physician, tutor, chronicler, master of revels, licensed jester, seer, food taster and interpreter. A tolerated jester calms the crowd, a seer sways the ruler's choices, a taster guards the ruler's cup and an interpreter wins envoys a hearing. Grandeur from feasts, art and fine goods draws talent and impresses envoys, and the constitution changes only by a high threshold, or by revolution.

**In your world:** A queen sold the right to collect her taxes to pay for a war. Revenue rose, corruption followed, the provinces' approval collapsed, and when she died the governor of the richest province took the crown instead of kneeling to her heir.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/37-patrons-and-puppets.jpg"><img src="common/assets/images/dlc-covers/37-patrons-and-puppets.jpg" width="220" alt="Patrons and Puppets box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/37-patrons-and-puppets.jpg"><img src="common/assets/images/dlc-backs/37-patrons-and-puppets.jpg" width="220" alt="Patrons and Puppets box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 37. Patrons and Puppets

*The throne is held by whoever the throne must keep happy.*

Ask who really chose the emperor. Not the people: the guard captains, the great landholders and a handful of priests. Keep them rich and you rule. Neglect them and a general with an army and clients of their own starts to wonder. Your world works out the circle that keeps every ruler in power, and that circle decides whether the treasury builds roads or buys loyalty.

- **The Winning Coalition** — every realm knows who has a say in choosing the ruler and whose support keeps the ruler there. Small circles are bought with gifts and offices, large ones demand roads and granaries, and a ruler expecting a short reign plunders while a secure one invests.
- **Seven Kinds of Legitimacy** — traditional, charismatic, legal-rational, a divine mandate, popular consent, performance and conquest. Tradition breaks with the succession, charisma dies with defeat and death, legal rule rots with corruption, and a conqueror's right fades with time unless it is joined to another. When a charismatic founder dies, the realm must turn charisma into a dynasty or an institution, or split.
- **Patrons, Clients and Bought Offices** — eight kinds of client bind themselves to the powerful: households, retainers, officials, commanders, brokers, artists, informants and scholars. A broker carries favours between a patron and lesser clients for a share and can grow richer than the patron, artists and scholars raise the patron's renown, and informants feed the patron's intrigues. Offices are sold, buyers recoup the price, and new offices absorb restless elites at a cost.
- **Overmighty Subjects** — governors and generals build power bases of holdings, client commanders, wealth and popularity. Rulers rotate commands, split armies, raise parallel guards and keep hostages, buying safety at the price of military quality.
- **Eight Ways to Share the Harvest** — markets, palace and temple stores that redistribute, command economies, dues owed by obligation, gift economies, sharing by need, abundance and lottery. Sack the centre of a palace economy and the whole economy falls with it.
- **Citizens and Strangers** — citizens, subjects, resident foreigners, protected minorities, the bound and the stateless each hold or lack ten rights by law: office, marriage, arms, the courts, property, movement, the vote, worship, assembly and schooling. Lacking a right bars holdings, travel, votes or open rites, and movements rise to win it.
- **Becoming One of Us** — membership comes by descent, birthplace, residence, conversion, service, purchase, grant, union or adoption. The stateless have no court to protect them and are easily bound, passes and safe-conducts decide who travels, forged ones sell on the black market, and welfare decides who eats in famine.
- **The Licensed Fool** — jesters and satirists mock the ruler with a licence. Tolerated satire cools the mob, suppressed satire festers into grievance, and the fool may say what no councillor dares.

**In your world:** A general who had won three wars held more land than the crown. The nervous emperor rotated the general to a distant frontier, split the legions and kept the general's eldest child at court as a guest. The army lost its next battle, and the general marched home anyway.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/38-crowns-unclaimed.jpg"><img src="common/assets/images/dlc-covers/38-crowns-unclaimed.jpg" width="220" alt="Crowns Unclaimed box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/38-crowns-unclaimed.jpg"><img src="common/assets/images/dlc-backs/38-crowns-unclaimed.jpg" width="220" alt="Crowns Unclaimed box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 38. Crowns Unclaimed

*The kingdom fell three centuries ago. Its crown still waits.*

The old kingdom has had no monarch for three hundred years, but its title survives, dormant and claimable. A minor count holds two of its provinces and a thin claim through a grandmother. Gather enough of the old land and the count can restore what was lost, and the legends of the vanished rulers will stir around them. Every house in your world plays this long game.

- **Noble Houses** — prestige, heirlooms, seats, feuds, and bloodlines that run long-lived, giant-blooded, seer-gifted, cursed or god-blooded. Houses marry for alliance and claim at the risk of inbreeding, and split into cadet branches that carry claims against the senior line.
- **Eleven Tiers of Title** — local and district lordships, regional titles, realms and empires, three tiers of faith office, military captaincies, guild headships and the heads of leagues and confederations, each title named in its own culture's language. Create one by holding most of its land, or usurp one by holding its capital and a majority of its territory.
- **Right Against Might** — land held long enough under another title drifts into it by right. The gap between the two maps is where claims and wars are born.
- **Claims, Unions and Partitions** — nine bases of claim: inheritance, marriage, conquest, divine favour, forgery, old right, election, adoption and prophecy. Claims fade unless pressed, an elected claimant faces the hereditary ones, an adopted heir faces blood kin, and a prophecy's claim rises and falls with belief. One ruler holding two crowns rules both realms, and partition laws split a kingdom among the heirs, generation after generation.
- **Ten Laws of Succession** — primogeniture, seniority, election, tanistry, succession through a second line, combat, divine choice, ultimogeniture, free designation by the holder, and rotation between houses by turn. A designated heir can be contested by kin and nobles, and rotation keeps rival houses out of civil war.
- **Arms Born of History** — every house, realm, title, army and guild bears arms drawn from its deeds, its founder's wounds, its totems and its patron god, differenced for cadet branches and quartered by marriage.
- **Siblings Against Cousins** — lineages nest within clans within tribes. Siblings fight cousins, both unite against outsiders, and the whole tribe unites against foreigners, which gives stateless peoples order without a ruler.
- **The Long Plan** — secret orders and houses steer marriages across generations toward divine blood, a seer's gift or a union of claims, and whole peoples gather over centuries to restore a fallen realm, its capital and its law, until a love match or a barren marriage undoes a century of work.

**In your world:** Two siblings split their parent's kingdom by partition law. Their grandchildren fought over a border county and the elder line lost, but generations later its cadet branch married back into the younger, quartered both arms and pressed the old kingdom's dormant title.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/39-iron-code.jpg"><img src="common/assets/images/dlc-covers/39-iron-code.jpg" width="220" alt="The Iron Code box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/39-iron-code.jpg"><img src="common/assets/images/dlc-backs/39-iron-code.jpg" width="220" alt="The Iron Code box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 39. The Iron Code

*A law is only as strong as the hand that enforces it.*

A merchant lies dead in a fogbound alley. The sheriff has a frightened witness who owes the accused money, a wound only a curved blade could make, a forged letter and a trail going cold by the day. The verdict will follow the evidence, the advocate the family can afford and the law of the land, so an innocent person can hang and become a martyr.

- **Fourteen Areas of Law** — succession, property, fiscal, penal, military, social, public health, magic, constitutional, commerce, faith, labour, family and environment. Laws decide heirs, punishments, levies, contracts, tithes, wages, custody, protected nature and whether magic is banned or licensed, and a law that clashes with a people's values raises unrest by the weight of its area.
- **Passing a Law** — proposals advance with the balance of supporters and opponents. Estates obstruct with their privileges, debates spill into riots or compromises, and a bill that stalls too long fails and shames its champion.
- **Five Legal Systems and Their Blends** — custom kept in the elders' memory, written codes, scripture, binding precedent and oracles. Under an oracle a god answers the court, and the son may answer truly, lie or stay silent.
- **Evidence Decides** — ten kinds: witnesses with failing memories or hidden loyalties, traces such as wounds, footprints and poison signs, documents, confessions, divination, the residue of rites, experts such as physicians and appraisers, hearsay, written records and the body itself, read for wounds, marks and remains. Evidence decays, records and bodies speak only where literacy and medicine allow, and wrongful verdicts come from bad evidence and bias, never from dice.
- **Eight Courts and Precedent** — local, provincial, high and religious courts, guild courts for members, military courts for soldiers, consular courts where a treaty lets foreigners be judged by their own law, and courts of appeal that catch errors at a cost in time. Clashing jurisdictions go up to the high court or become disputes, skilled advocates win cases so the rich get better justice, and under precedent each ruling binds the next.
- **Prisons, Pardons and Remaking** — prisons breed gangs, disease and new skills, and released convicts carry a stigma. Rulers pardon friends at a cost in corruption and declare amnesties after civil wars. Where magic meets a cruel penal code, sentences remake the convict's body.
- **Oaths Before the Gods** — fourteen oaths, from fealty, vengeance, silence, pilgrimage and sworn kinship to oaths of office that bind officials and sworn testimony that weighs more in court. Break one and the god's wrath may follow where the world's laws allow, a perjurer's case is tried again, keeping oaths makes oath gods stronger, and a geas may forbid you ever to refuse hospitality.
- **Fifteen Registers** — land titles, debts, sales, union payments in either direction, indentures, patents, patterns, mind states, lines, companies, births, deaths, citizenship, wills and licences are kept on record, and a spy who tampers with a register can move a claim or wipe a debt.

**In your world:** A schemer's forged letter convicted an honest reeve of treason. The reeve's village remembered them as a martyr and its approval of the crown collapsed, and by the time an investigator proved the hand was false, the villagers had already joined the rebels.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/40-guilds-and-estates.jpg"><img src="common/assets/images/dlc-covers/40-guilds-and-estates.jpg" width="220" alt="Guilds and Estates box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/40-guilds-and-estates.jpg"><img src="common/assets/images/dlc-backs/40-guilds-and-estates.jpg" width="220" alt="Guilds and Estates box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 40. Guilds and Estates

*Every guild wants a monopoly. Every estate wants a privilege. Everyone wants the crown.*

The cloth guild wants the new mills banned. The nobles want their tax exemption back. The merchants want peace with the realm that holds their route, and the warrior order wants war with it. Here factions act every epoch: they lobby, bribe, strike, riot, fund wars and plot coups, and the balance of their sway is the realm's true constitution.

- **Thirty-Nine Kinds of Faction** — merchant and craft guilds, priesthoods and holy orders, warrior and mage orders, noble councils, estates, parties and movements, peasant leagues, workers' unions, rebels, bandits, pirates and route raiders, crime families, thieves' guilds, street gangs, smuggling and counterfeiting rings, academies, secret societies, mercenary and chartered companies, financiers, veterans, clubs, wandering markets and more, from a band of fifty to a network spanning worlds.
- **Sixteen Goals and Fourteen Means** — lower taxes, a monopoly, a claimant on the throne, independence, an estate privilege, a member seated in office, a rival faction ruined, protection for its members or a new settlement of its own. To get there a faction lobbies, bribes, petitions, strikes, riots, stages a coup, assassinates, smuggles, raids, funds a war, recruits, spreads propaganda, calls a boycott or splits apart.
- **The Power Balance** — inside every realm the factions' sway forms a balance that feeds every decision the ruler takes. A guild monopoly sets prices and blocks rivals, and smuggling rises to meet it.
- **Estates and Privileges** — the estates of every class bargain for nine privileges: tax exemptions, monopolies, council seats, the right to bear arms, immunity from the courts, offices reserved to their own, the sole right to hold land, freedom from levies and dress that marks their rank. Every grant buys loyalty and costs the crown revenue or power, and reserved offices keep able commoners from rising.
- **Parties and Movements** — fourteen causes, from abolition, independence, religious revival and land reform to the vote, peace, conservation, labour, temperance, equal standing, learning, health and the rights of made minds, grow as mass movements with support in every class. Where assemblies exist they become parties. Where they do not, they become revolts.
- **Companies with Armies** — chartered companies hold shares, a monopoly abroad and mercenary armies. They can conquer, become a realm of their own or collapse onto their banks and shareholders, and unpaid mercenaries turn bandit or change sides mid-war.
- **Ranks, Secrets and the Pooled Purse** — guilds control apprenticeships, quality standards and secret techniques. Cooperatives pool money and labour for mills, boats, irrigation, insurance, credit, funerals, granaries against dearth, common herds, schools and housing, and can grow into political movements.

**In your world:** When the water-frame mills arrived, the cloth guild struck and the capital's cloth ran short. The crown bought peace with a guild monopoly, smugglers moved in to undercut it, and the mill owners began lobbying the council to tear up the guild's charter.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/41-pacts-and-perfidy.jpg"><img src="common/assets/images/dlc-covers/41-pacts-and-perfidy.jpg" width="220" alt="Pacts and Perfidy box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/41-pacts-and-perfidy.jpg"><img src="common/assets/images/dlc-backs/41-pacts-and-perfidy.jpg" width="220" alt="Pacts and Perfidy box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 41. Pacts and Perfidy

*Sign with one hand. Sharpen the knife with the other.*

Your envoy demands a border province, and a crisis opens. Two realms back you for promised shares of the spoils, three back your rival, and a fourth is courted by both. At every step either side can back down and lose only face. Or nobody blinks, and every backer marches. Here every treaty is a set of clauses the world enforces, and every broken promise is remembered.

- **Treaties Built from Clauses** — eighteen kinds of treaty, from peace, alliance and vassalage to mutual aid in disaster, border accords and limits on fleets and arms, built from thirty kinds of clause: tribute, cession, hostages, wergild, extradition, champions, shared water, the return of refugees, the exchange of captives and more. The world carries them out every epoch, guarantors join when they break, and a god, power or court that stood witness punishes the breaker.
- **Treaties That Pause** — a treaty can be suspended without breach, held in force while its terms are renegotiated, fulfilled, left to expire or broken. A mediator who brokered it gains standing while it holds and loses it when it breaks, and a suspension costs less trust than a breach.
- **The Coalition Against You** — conquests, unjust wars and broken treaties raise alarm in every realm that hears of them. Past a point the neighbours band together with a standing call to arms, and only marriages and good relations slowly cool it.
- **Crises at the Brink** — a demand opens a crisis with a clock: cede a region, release a vassal, convert, pay, hand over a named fugitive or rival, disarm, open ports and routes, apologise or release captives. Other realms back a side for clause shares and favours, and at each escalation someone can back down, concede, accept a third party's settlement, let the crisis freeze while its costs run on, or let it come to war.
- **Spheres, Subjects and the Neutral** — hegemons and great powers hold clients in their spheres, and subjects come in ten kinds, from vassals, tributaries, marches and personal unions to colonies, protectorates, enclaves, mandates and associated states, each with its own obligations, its own desire for liberty and a contract it can demand to renegotiate. A neutral realm joins no bloc and trades with every side, an isolated one trades little and is seldom drawn into wars, and breaking a realm's neutrality outrages its neighbours.
- **Bad Faith and Side Deals** — a deceitful ruler signs meaning to break, and the other side trusts only as far as it believes. At summits several parties bargain in rounds, cut secret side deals, and the order of commitments decides who wins.
- **Diplomacy Has Limits** — a realm sustains only as many alliances, guarantees and embassies as its administration and ambassadors can carry. Inside realms of many peoples, old grudges between them feed migration, assimilation and ethnic strife.
- **An Assembly of Worlds** — realms across worlds vote on nine kinds of resolution: route security, embargoes, bans on void rites, sanctions even on a son's world, quarantine of a plague-struck world, arbitration of disputes, pooled relief after disaster, peacekeepers sent between warring parties and the recognition of a new realm.

**In your world:** A ruler signed a marriage pact never meant to be honoured, then seized the province the union had brought. The witness god's priests denounced the oathbreaker, alarm spread to every court, and within a generation a coalition of the ruler's former friends had taken the province back.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/42-rise-and-ruin.jpg"><img src="common/assets/images/dlc-covers/42-rise-and-ruin.jpg" width="220" alt="Rise and Ruin box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/42-rise-and-ruin.jpg"><img src="common/assets/images/dlc-backs/42-rise-and-ruin.jpg" width="220" alt="Rise and Ruin box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 42. Rise and Ruin

*Empires rise at the frontier and die in the palace.*

Nothing in your world is scripted to fall. Yet watch a great empire across three centuries: land grows scarce, wages sink, younger children with credentials and no offices crowd the capital, the treasury borrows to pay its soldiers, and on the frontier a hard people that has fought for generations is learning to ride as one. The cycle emerges from the simulation, and you can read every gauge of it.

- **The Stress Gauge** — population pressure, popular misery, elite overproduction and fiscal distress combine into one measure of political stress. As it climbs, factions form, coups and revolts grow likelier, and crowds tip into riot faster.
- **Counter-Elites** — when nobles, the rich and the credentialed outnumber the offices, titles and land to go round, the surplus becomes aspirants with nowhere to go. They lead the factions, movements and revolts.
- **Secular Cycles** — growth, stagflation, crisis, then depression or recovery, over centuries and with no script at all. Population falls, elites thin, wages rise, and the climb begins again.
- **Asabiyya** — solidarity rises on frontiers against peoples deeply unlike your own and decays through generations of luxury. It multiplies cohesion, morale and resistance to assimilation, so hard frontier peoples overthrow soft dynasties.
- **Challenge and Response** — fourteen kinds of challenge, from disasters, plagues, famines and invasions to long winters or summers, contested successions, secessions, migration waves, technological shocks and revelations. Too little challenge brings stagnation, too much brings collapse, and the severe but survivable middle forges the strongest peoples.
- **Transformation** — a people that meets its challenge through a movement, a revolution or a revival can keep its people and take a new form: a new government, a new faith or a new economy.
- **Long Plans** — realms, cults, orders and gods pursue goals across centuries: a desert world made green, a bloodline, a world converted, a wonder, a great work of engineering, a reform, an exploration, a fallen realm restored. Offices and orders carry them long after their authors are dust.
- **Psychohistory** — a scholarly order with statistics and a great archive forecasts a realm's future through a noisy lens and steers it with small interventions, until a great person or a god steps in and the forecast fails.

**In your world:** A nomad people hardened on the empire's frontier for four generations. When elite overproduction and an empty treasury split the capital into rival courts, the nomads rode in and founded a dynasty, and their great-grandchildren, grown soft in the palace, fell to the next frontier.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/43-couriers-and-ciphers.jpg"><img src="common/assets/images/dlc-covers/43-couriers-and-ciphers.jpg" width="220" alt="Couriers and Ciphers box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/43-couriers-and-ciphers.jpg"><img src="common/assets/images/dlc-backs/43-couriers-and-ciphers.jpg" width="220" alt="Couriers and Ciphers box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 43. Couriers and Ciphers

*The peace treaty arrived. The battle was already over.*

Your herald rides for the enemy camp with an offer of peace. The pass is closed by snow, so the herald takes the coast road, where a spy network copies the letter and bandits hold its bearer for ransom. By the time the herald arrives, the armies have met. Now every decision is made on the latest news to arrive, and news travels at the speed of a horse.

- **Twelve Ways to Send Word** — envoys, letters, heralds, signal fires, birds and other courier animals, drummed and whistled speech, magical sendings, dreams sent by a god, mind links, networks and broadcasts. Delay follows distance, medium and season, mountain passes close in winter, and between worlds word travels as slowly as the route.
- **Thirteen Kinds of Message** — proposals, demands, threats, insults, notices of gifts, declarations, reports, pleas, intelligence, orders, warnings, condolences and congratulations. An order delayed, lost or forged moves a general the wrong way, a warning's timing decides who escapes the harm, and a timely condolence or congratulation warms the court that receives it.
- **Intercepted** — every region along the way with spies, bandits or enemy armies is a chance to lose a letter. A message can arrive late, go astray, be intercepted, forged, misread or refused at the door, and a refusal is an insult. Stolen messages yield intelligence, hooks or forged replacements.
- **Forgery** — the forger's skill against the recipient's familiarity with the sender's hand. A forged declaration of war can set two innocent realms at each other's throats, and a forged order can pull an army back from the pass it was holding.
- **Lost in Translation** — misreadings grow with the language gap, the number of clauses and the interpreter's skill. A misread clause becomes a bitter breach dispute long after the ink has dried.
- **Envoys and Etiquette** — an envoy's skill and manners shape the welcome. A well-chosen gift earns opinion and a favour, a breach of precedence costs it, and an envoy may be received, honoured with gifts, insulted, expelled, imprisoned, killed or won over to serve the host. Killing an envoy is unthinkable almost everywhere and means war.
- **Ciphers and Codebreakers** — encipher your letters and an interceptor learns only that you wrote. Codebreakers grind at captured traffic for seasons, and while you do not know your cipher is broken, every message you send is read.
- **Beacons and Broadsheets** — beacon chains, mirror relays, post stations, drum relays across forest and valley, wires, radio and paired sending stones shrink the realm until someone burns, jams or captures them, and a burned or disused station can be restored. Criers, sermons, broadsheets and propaganda move opinion of the ruler, a law, a war, a god, an ideology, a faction, a foreign power, the economy or a neighbouring people, and censorship breeds distrust once discovered.

**In your world:** The empress's codebreakers broke the duke's cipher in the second winter of the rebellion. For a year they read every letter the duke sent, until a careless ambush betrayed what they knew, and the duke, hunting the leak, hanged a loyal secretary.

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
- **Thirteen Axes of Reputation** — heroism, honour, cruelty, piety, generosity, wisdom, trickery, craft renown, troublemaking, mercy, justice, reliability and hospitality, held separately by every community and read through its own ethics. A massacre is cruelty to the victims' kin and heroism at home.
- **Prestige, Piety, Dread and Tyranny** — rulers spend their reputation. Prestige buys acceptance of laws, piety buys the clergy, and dread silences dissent for a while. Tyranny piles up from unjust acts and turns vassals against the crown.
- **Secrets for Sale** — factions, cults, scholars and even beasts prize particular knowledge: true names, lost techniques, hidden sites, prophecies, remedies, genealogies. A secret is paid for with wealth, a favour, renown, another secret, a deed done for the seller or an oath on how it may be used, and breaking that oath is oathbreaking. Every sale makes a secret worth less.
- **False Heroes** — deeds must be credited, and a claim can be true, shared, false, inflated to take the whole renown of a shared deed, or borrowed from someone else's. A vain rival can claim your dragon until the true slayer produces the beast's tongue, and exposure brings scandal, a duel or punishment. Yet the chronicle may still honour the impostor.
- **Disputed and Forgotten** — when two claim one deed, the renown is split until a trophy, witnesses, a duel or a court settles it, and the chronicle may record both. A claim nobody keeps alive is forgotten over generations, and its renown goes with it.

**In your world:** A sellsword claimed the wyrm a shepherd girl had killed. The capital feasted the sellsword while her village knew the truth, and when she walked into court with the beast's tongue in a cloth, the duel that followed made her a legend.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/45-velvet-daggers.jpg"><img src="common/assets/images/dlc-covers/45-velvet-daggers.jpg" width="220" alt="Velvet Daggers box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/45-velvet-daggers.jpg"><img src="common/assets/images/dlc-backs/45-velvet-daggers.jpg" width="220" alt="Velvet Daggers box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 45. Velvet Daggers

*Everyone has a secret. You only need the right one.*

The chancellor's heir is not the chancellor's child. A maid of the household knows it, a rival's spymaster has just learned it, and nobody else knows yet. That single secret is a hook strong enough to force a vote, a marriage or a resignation, or, spent in public, to ruin a family. Here schemes are recruited, prepared and launched like campaigns, and every one of them can be discovered.

- **Nineteen Kinds of Secret** — affairs, children born outside a union, murders, heresies, hidden cult membership, debts, crimes, cowardice in battle, hidden conditions and hidden illness, false identities, pacts with outer beings, true parentage, broken oaths, sabotage of nature, a broken cipher, the true history of a deed, a hidden power and a forgery. Each one is born of something that really happened, and a ruler's illness, once known, moves every succession plan at court.
- **Hooks and Favours** — a hook from a secret, a debt, a favour, a hostage, a true name, dependence or affection can demand a marriage, a resignation, support, a vote, a law, an appointment, silence, a payment, a release or information. Weak hooks are spent on use, strong ones last. Favours are owed for gifts, rescues, support in war and succession, votes, relief, shelter, a paid ransom, healing and teaching, and refusing a called favour costs honour.
- **Living Under Other Names** — spies, the blood-cursed, exiles, impostors, fugitives, believers hiding their faith, beings passing as another kind, those hiding a power and those shielding their kin wear false identities, exposed by investigations, careless slips or a face someone recognises.
- **Twenty-Two Schemes in Three Phases** — murder, abduction, seduction, framing, a coup, a fabricated claim or hook, a stolen relic, a poisoned well, a sabotaged wedding, a freed prisoner, a forged letter, a hidden fleet, a fixed contest, a crowd stirred to act and more. Recruit agents with money, hooks or a cause, gather power, then strike past the target's spymaster and bodyguards.
- **Discovery** — every epoch a scheme's secrecy is tested against the counter-intelligence of the target's court. A discovered plot exposes its agents and leaves memories that last.
- **Timing Is Everything** — night and fog raise success and hide witnesses, storms cut pursuit, festival crowds give cover but more eyes, and a plague panic distracts the watch. Plots cluster on festival nights and foggy mornings.
- **Sabotage of Nature** — blight a rival's land with pests, burn it or leave it barren. The scar stays on the land, the plot becomes a secret every agent carries, and when the deed comes to light it is tried as treason.

**In your world:** A rival's agents blighted the duke's best fields with pests on a foggy night. The harvest failed and the duke's levies went hungry, and when footprints and a dropped sack led an investigator back to them, the scandal cost their mistress her place at court.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/46-shadow-networks.jpg"><img src="common/assets/images/dlc-covers/46-shadow-networks.jpg" width="220" alt="Shadow Networks box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/46-shadow-networks.jpg"><img src="common/assets/images/dlc-backs/46-shadow-networks.jpg" width="220" alt="Shadow Networks box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 46. Shadow Networks

*Trust no one. Especially the one who found the mole.*

Your spymaster swears there is a traitor on the council, and is right, but names the wrong official. The loyal treasurer hangs, and that night the real mole sends word across the border. Here spy networks are built cell by cell, agents are bought with greed, faith, blackmail or vanity, and paranoia can do more damage than any enemy.

- **Networks of Cells** — agents, handlers, dead drops and safe houses, with covers as merchants, priests or envoys. A captured agent can betray only their own cell, and flat networks are fast but fragile.
- **Seven Motives** — money, ideology, compromise, ego, love, revenge and faith. The motive sets loyalty and the risk of a double cross: an agent won by love breaks when the bond breaks, one driven by revenge stops when the target falls, and true believers are the most reliable agents and the hardest to turn back.
- **Twelve Operations** — steal knowledge, sabotage, assassinate, incite, gather intelligence, blackmail, counterfeit, plant a mole in an office, guild or temple, bring an agent or defector out across a border, feed a rival false beliefs, recruit new agents, or simply watch at little risk. Spies fire granaries, weaken walls, poison wells, tamper with registers of titles, debts and births, block convoy routes and flood the market with false coin.
- **Sleepers and the Lost** — an agent can be active, caught, turned, dead, retired, missing, exposed or asleep. A sleeper waits embedded for years and wakes on a set signal, a missing agent sends nothing until found, and an exposed one is watched and useful only for feeding false reports.
- **Mole Hunts** — paranoid spymasters accuse the innocent, and every purge costs loyal officers and drives defections, which only deepens the paranoia.
- **Defectors and Double Agents** — captured agents can be turned to feed false intelligence, or exchanged. Defectors carry their secrets across the line and need protection, branded traitors at home and hailed as heroes abroad.
- **Death by Design** — blade, poison, staged accident, deliberate infection or curse. Whether anyone recognises a murder depends on the physician's skill and the medicine of the age, and that decides whether a vendetta, an inquiry or a war follows.
- **Spies of the Gods** — scrying rites, dream intrusions and servitor spies cross any distance. Wards and the dominion of a rival god block them.

**In your world:** An ideological agent poisoned the margrave and dressed it as a fever. The court physician, schooled in a newer medicine, read the signs, the poisoner's cell was taken, and the margrave's heir declared the war the margrave had refused to fight.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/47-fog-of-belief.jpg"><img src="common/assets/images/dlc-covers/47-fog-of-belief.jpg" width="220" alt="Fog of Belief box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/47-fog-of-belief.jpg"><img src="common/assets/images/dlc-backs/47-fog-of-belief.jpg" width="220" alt="Fog of Belief box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 47. Fog of Belief

*They don't act on the truth. They act on what they believe.*

A general force-marches an army to break the siege of a city that was relieved a month ago. The general is no fool: the last report said the walls were still holding. Every ruler, house, cult, commander and beast in your world decides on what it believes, with a confidence and a date attached, while the outcome is settled by the truth. Surprise, folly and genius live in the gap.

- **A Mind of Its Own Making** — every deciding actor keeps its own store of beliefs: an enemy army's size, a rival's treasury, a claimant's health, a god's favour. Each belief carries a confidence, a date and a source.
- **Fifteen Ways of Knowing** — seeing with one's own eyes, messages, rumours, spies, scouts, one's own records, deception, networks, foresight, mind reading, intrusion, surveillance, the reports of made minds, dreams and omens. Records exist only where someone can write, and a belief drawn from a dream or an omen holds with the confidence its culture gives such signs.
- **Knowledge Fades** — confidence decays with age, and stale beliefs make fatal decisions. The rival you believe is bankrupt may have been paid with a dragon's hoard last spring.
- **Deception** — feints, false campfires, planted rumours, forged letters and a spy network's disinformation write lies straight into a rival's picture of the world.
- **Markets in the Fog** — merchants trade on the price gaps they believe in, so prices converge where news is quick and stay apart where it is slow. Insurers price risk on belief, and speculators hoard on it.
- **The Gap Laid Bare** — toggle any realm between what it believes and what is true. As the Creator you can reveal the truth to an actor or plant a false belief, and the agents who play your mortals see only what their characters know.

**In your world:** A ruler believed a rival's treasury empty because the last spy report was years old. The ruler declared war, met an army paid from a fresh dragon hoard, and lost a province to an enemy the court had been certain could not afford to fight.

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

You do not conjure soldiers. You take them. Young farmers leave the levy class, spears leave the armoury, grain leaves the granary, and the harvest season halves the call. Then the march begins, and every frozen pass, every fevered camp and every empty war chest costs lives. Each stack carries its own gear, drill, morale and memory, and when the war ends your people count who came home whole.

- **Fifty Kinds of Soldier** — twelve families, from levies, pike and shock infantry to mounted archers, chariots, sky riders, battle casters, summoners, constructs and summoned hosts, and on to gunners, drop troops, drone operators and powered troopers. Each has its own melee, missile, defence, speed, charge mass, upkeep and favoured ground.
- **Armour from the Armoury** — every stack is equipped from the weapons and armour your people forged before the war, from a hundred families of gear that run from hide and mail to plate, warded and powered armour. Levies go home when the army disbands, minus the dead, and the maimed come home maimed.
- **Hunger Before Battle** — each region can feed only so many mouths. Armies above the limit strip the land and earn its hatred, and a winter campaign through the mountains in heavy armour can destroy an army without a single battle.
- **Strength, Organisation, Discipline** — three separate pools in every stack. A stack whose formation dissolves routs at full strength, drilled professionals hold where levies break, and news of a sacked home city raises rage and desertion at once.
- **Commanders Earn Their Names** — skill in fire, shock, manoeuvre, siege, logistics and intelligence, and twenty-nine battle traits earned from the record, from cavalry master, winter campaigner and night fighter to jungle fighter, cold fighter, river crosser, reckless and brutal. Their traits steer the tactics they choose and the ground they fight best on.
- **Eleven Stances, Ten Officers** — an army marches, forages, entrenches, besieges, garrisons, raids, retreats, settles into winter quarters, pursues a beaten foe, escorts convoys and siege trains, or disbands and goes home. Beside the commander serve a second in command, a quartermaster, a standard bearer, a surgeon, a chaplain, a paymaster whose honesty keeps mutiny away, a master of scouts, a master of engineers and an interpreter.
- **Blueprints and Earthworks** — realms draw up and name their own army templates, thirteen formations run from line, column and wedge to squares, shield walls and a ring of wagons against horse and beast, war machines are built to blueprints a rival can steal, and sappers bridge rivers with pontoons and dig earthworks that outlive the war.
- **Regiments and Veterans** — units from one recruiting ground earn names, nicknames and battle honours for victories, stands, sieges, survival, the relief of a besieged town, a crossing under arms, mercy and being first through a breach, and they remember their massacres. Veterans receive land, pensions, citizenship, lesser titles, offices or freedom from taxes, and their associations may back an old commander's coup.

**In your world:** A marshal marched heavy infantry over the passes in midwinter. Cold and camp fever took more soldiers than the enemy ever did. The survivors were settled in a veteran colony, and a generation later they marched again, behind their old general, on the capital.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/49-field-of-glory.jpg"><img src="common/assets/images/dlc-covers/49-field-of-glory.jpg" width="220" alt="Field of Glory box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/49-field-of-glory.jpg"><img src="common/assets/images/dlc-backs/49-field-of-glory.jpg" width="220" alt="Field of Glory box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 49. Field of Glory

*Three hundred at the pass. Thirty thousand on the plain.*

Dawn fog lies on the ford. Your archers cannot see, the enemy's hidden horse waits in the reeds, and your commander, reckless by record, wants to charge. Every battle is fought in phases on real ground under the real sky of that season, and every phase leaves a reason you can read: the terrain, the tactic, the counter, the line that held and the line that broke.

- **Twelve Phases of Battle** — parley, scouting, the commanders' plans, orders, missiles, the charge, melee, reserves, rites and miracles, pursuit, salvage and aftermath. A parley can end a battle before it starts with terms, insults or delay, a patron god may intervene, and its attention can draw a rival god in. Seven outcomes run from decisive victory through pyrrhic victory and stalemate to rout and massacre, or a battle refused.
- **Every Ground, Every Sky** — battles are fought on every kind of terrain the world has and under every kind of weather, on land, at sea, in the sky, in boarding fights, under water, underground, between strata, in open space and across dimensions. A pass narrows the field, marsh drags heavy armour down, streets swallow cavalry, rain slackens bowstrings, fog blinds archers and hides ambushes, an eclipse's dark shakes morale, and a magic storm swells every rite and its backlash.
- **Twenty-Five Tactics and Their Counters** — shield wall, wedge, feigned retreat, double envelopment, night raid, ambush, guerrilla war, infiltration, a river crossing under arms that a river crosser leads best, and fire set on dry ground with the wind behind it, each with its answer and its proper ground. Feints pin reserves, false campfires inflate an army and planted deserters carry lies.
- **The Width of the Field** — only so many can fight at once. At a narrow pass three hundred hold thirty thousand for a time, reserves wait for the front to tire, and squares stop cavalry but die under arrows.
- **The Morale Ladder** — steady, shaken, wavering, routing, broken, and rallied again. Panic spreads between neighbouring stacks, standards and priests rally the wavering, orders arrive late or garbled across a language barrier, and a fallen general collapses the whole command.
- **The Physics of Slaughter** — in melee only the front rank kills, but massed arrows and spells strike the whole enemy, so concentration pays quadratically. Heavy armour, forged or grown, shrugs off blows that cannot pierce it, which is why crossbows, picks and maces exist.
- **After the Battle** — the killed, the wounded, the maimed, the captured, the missing, the deserted and the sick are counted apart. The missing drift home over the next season, turn up dead or take to banditry, deserters are hunted, and in a long campaign camp sickness takes more than the enemy. Without field surgeons the wounded die within the season, the victor rearms from the field, and mass death may leave it haunted.
- **Captives of the Field** — captives are held, ransomed, enslaved, sacrificed, worked, exchanged, released, executed, pressed into the victor's ranks or adopted into the captors' households. Every culture judges a killing of captives, and pressed captives fight with low loyalty and desert at the first chance.

**In your world:** Fog lay on the river at dawn. The defenders' archers fired blind while the attackers' hidden wing crossed upstream and struck their flank. The rout became a massacre, the meadow was left haunted, and settlers avoided it for generations.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/50-walls-will-fall.jpg"><img src="common/assets/images/dlc-covers/50-walls-will-fall.jpg" width="220" alt="Walls Will Fall box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/50-walls-will-fall.jpg"><img src="common/assets/images/dlc-backs/50-walls-will-fall.jpg" width="220" alt="Walls Will Fall box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 50. Walls Will Fall

*Starve them, storm them or wait for a traitor to open the gate.*

The engines have pounded the north wall since spring. Under your feet, sappers race the defenders' counter-miners through wet clay. Inside, the granaries are counted in days and the guilds are whispering. A siege lasts seasons and both sides suffer it: hunger, fever, sorties by night, and the long arithmetic of who breaks first, the wall, the garrison or the people behind it.

- **Eight Roads into a City** — blockade, bombard, mine, assault, negotiate, suborn the people who hold a gate, poison the supply or divert the river. Engines are matched against walls by their stone, mines against the rock and soil beneath, and an assault is a battle on wall ground where every breach strips the defender's advantage.
- **Fourteen Siege Works** — lines of circumvallation, towers, rams, mines and countermines, ladders, massed bombardment, saps that bring attackers forward under cover, blockade lines, ramps raised to the wall top over weeks and dams that cut the water or flood the approaches, and where the world allows, assaults from the air, attacks on networks and rites that breach the wall.
- **The Defender Answers** — sorties that burn the towers and works, masons who patch breaches from the stone stock, rationing and the hope of relief. Defenders open the sluices to flood the approaches, burn the land around to starve the besiegers, drive out those who cannot fight, or leave by sea and give up the town. Beneath the walls, sappers and counter-miners duel in the dark, and tunnels cave in.
- **Hunger and Fever** — rationing becomes famine, famine becomes hunger sickness, and hunger sickness reaches the taboo that only some peoples will break. Disease festers in the city and in the besiegers' camp alike, driven by water, sanitation and season.
- **Treason at the Gate** — starvation erodes the garrison's nerve and raises the risk of revolt in the streets, and a faction nursing an old grievance, a bribed officer or a hooked captain may simply open a gate.
- **Sack or Mercy** — the victor's doctrine and the commander's traits decide between mercy, a sack, razing, a ransom that leaves the city poorer but whole, deporting its people into the victor's lands, or settling the victor's own people in it. A sack takes the treasury, the relics and the people, burns whole districts and earns infamy, and the city never forgets who conquered it.
- **Surrender on Terms** — a siege can end in agreed surrender, with the honours of war, safe conduct or a ransom. The victor may keep the terms or break them, and a broken word is remembered.
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

Your offensive has taken three cities and is still advancing. Behind it the barges are slower, the depots thinner, the river line longer. Somewhere ahead lies the point where the attack must stop or collapse, and back home the markets are filling with one-armed veterans. War runs season by season across fronts, depots and headquarters, and it ends at a table where every demand has a price.

- **Chain of Command** — army groups, armies, corps, divisions, brigades and detachments, each led from a headquarters with its own staff and ordered to attack, manoeuvre, resupply, hold, stand or screen. Couriers and signal networks stretch its reach, formations beyond it fight on standing orders, detachments raid, garrison and escort on their own and can be cut off, and a screen hides an army's moves and catches the enemy's scouts.
- **Supply Is a River** — depots, wagons, pack animals, barges, ships and sky-barges carry supplies at a limited rate. Cut one depot or one river line and every army it feeds begins to starve.
- **The Culmination Point** — offensives outrun their supply as lines lengthen. Generals with a head for logistics see the limit coming, and a marshal who sends reserves to the wrong front on bad intelligence loses the war there.
- **Seventeen War Aims** — conquer a region, seize a settlement, a route, a resource or a nexus, press a claim, convert, take tribute, vassalise, liberate, destroy a cult, humiliate, take revenge, loot, change a government, secure water or bring refugees home. Occupied land yields taxes and levies, and its resistance grows with every atrocity remembered.
- **Casus Belli and War Score** — twelve grounds for war, from a claim, holy war, vendetta and a broken treaty to trade disputes, debt default, a broken pact that a god or court witnessed and the harbouring of fugitives, or naked conquest. Every one of nineteen peace terms costs war score: ceded land, tribute, hostages, reparations, open temples, a new government, fixed borders, refugees returned, a formal apology, a champion for disputes to come, or a white peace.
- **Why Wars Begin and End** — thirty causes set wars moving, from rivalries, uprisings, grudges and debts to espionage, schisms, beasts, trade routes, successions, shared rivers and refugees crossing borders. Wars end in eleven ways, from victory, conquest and exhaustion to betrayal, a miracle or mediation, and a mediated peace leaves less grievance behind.
- **The Home Front** — war support rises with propaganda and a just cause and falls with taxes, casualties and maimed veterans in the streets. Weary peoples press for peace, while war workshops grow more efficient the longer they make one thing.
- **Parley** — bluffs and insults before battle, truces for the harvest, burial truces that let both sides gather their dead by their own customs and keep disease off the field, safe conducts, fraternisation across the lines, surrender terms with the honours of war, and exchanges of prisoners. Break a sworn term and it is remembered as an atrocity.

**In your world:** The offensive outran its barges, and enemy raiders burned the river depot behind it. The army starved where it stood. At home, every maimed soldier who returned drained the war's support, until the crown accepted a white peace it had sworn never to sign.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/52-admiralty.jpg"><img src="common/assets/images/dlc-covers/52-admiralty.jpg" width="220" alt="Admiralty box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/52-admiralty.jpg"><img src="common/assets/images/dlc-backs/52-admiralty.jpg" width="220" alt="Admiralty box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 52. Admiralty

*The fleet upwind chooses the battle.*

The wind backs west and your squadron holds the gauge. You close on a reach, rake the enemy flagship along its length with chain shot and watch its rigging come down. War on the water is wind, timber and fire: every shot lands on a hull, a mast, a rudder or a crew, every captain dreams of prize money, and above the masts the skyships fight for the air.

- **Points of Sail** — close-hauled, reaching, running, caught in irons, or under oars. The fleet upwind chooses the engagement, while galleys ignore the wind at the cost of their rowers' strength.
- **Damage Where It Hits** — twelve kinds of shot: round shot holes hulls, chain shot cuts rigging, grapeshot sweeps crews, fire and incendiaries catch sails, smoke screens a line and blinds its gunners, and explosive, piercing, guided and energy rounds follow as the age allows. Fire spreads by deck timber, and one spark in the magazine ends a ship, which is what fire ships are for.
- **Boarding and Prizes** — marines fight boarding melees and galleys ram. Ships that strike their colours become prizes, prize crews thin the victor's decks, and prize money flowing to sailors' households makes captains bold.
- **Command of Sea and Sky** — armies cross water safely only under naval supremacy, and landings against defenders bleed. Skyships and flying mounts win the air to scout, strafe supply trains and bombard sieges, and only what can reach the air can contest them.
- **A Hundred and Twenty-Eight Frames** — twenty-six families across nine domains, from rafts, longships, triremes and carracks to sledges over the ice, pedal craft, living ships, generation ships and bioships. Each is laid out from fifty-seven kinds of section, from hull, masts and sails to holds, wards, a galley that feeds the crew on long voyages and a sick bay that brings the wounded back. Designs evolve, old ships are refitted, and neglected masts snap in storms.
- **Thirteen Crew Stations** — gunners, riggers, marines, officers, rowers, pilots, engineers, sensor operators, medics, handlers, link operators, casters who work the vessel's wards, winds and drives, and navigators who fix its course and cut losses and delays.
- **Stars and Sea Clocks** — ten aids to navigation. The compass works only where the world has a magnetic field, the astrolabe needs astronomy, and a clock that keeps longitude cuts a port's losses at sea, beside log lines, charts, sounding lines, wayfinding, beacons, buoys, harbour pilots and positioning. Ports without the instruments for the open sea lose more ships on it.
- **The Admiralty Board** — admirals fight generals for the treasury in council, and naval treaties cap tonnage by class. Cheating on them is a scheme of its own.
- **Engagements in Every Domain** — ship against ship at sea, in the sky and in space, with weapons that choose the section they strike and chains of fire, flooding, venting and power loss.

**In your world:** The admiralty hid two warships from the tonnage treaty. When war came they held the weather gauge, raked the enemy flagship with chain shot and took it as a prize. The prize money filled the captains' houses, and recruits crowded the docks.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/53-blade-and-honour.jpg"><img src="common/assets/images/dlc-covers/53-blade-and-honour.jpg" width="220" alt="Blade and Honour box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/53-blade-and-honour.jpg"><img src="common/assets/images/dlc-backs/53-blade-and-honour.jpg" width="220" alt="Blade and Honour box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 53. Blade and Honour

*Seven exchanges. One will walk away.*

The spear reaches first. Your champion turns it on a shield, steps inside, and the long weapon is suddenly useless. Single combat is fought exchange by exchange, and every one weighs reach, skill, footing, stamina and nerve. Fighters feint, parry, wrestle and bleed. A duel ends in a yield, a lost eye or hand, a fighter driven from the ring, or death, and the victor's ethics decide the fate of the one on the ground.

- **Three to Seven Exchanges** — each weighs weapon skill, reach, armour, footing in the day's weather, fading stamina and pain. A spear outreaches a sword until the one holding the sword closes.
- **Strike, Feint, Parry** — fighters choose strikes at called targets, feints, blocks, parries, dodges and grapples. Whether a parry meets the blow depends on how well the defender reads the attack against the attacker's skill at deceit.
- **Grapple and Throw** — grab a limb or the weapon, throw, choke a foe senseless, lock a joint until it breaks or, in some cultures, bite when desperate.
- **Lance and Horse** — a couched lance strikes with the mass and speed of the mount. The horse itself is a target, and a falling horse crushes its rider.
- **Nine Ways a Duel Ends** — a yield, a disarm, a crippling wound, death, exhaustion, a fighter knocked senseless, the first wound drawn, a fighter driven out of the marked bounds, or a fight stopped by an authority, a god or the crowd. Each culture and challenge sets the ending in force, and a stopped duel leaves the quarrel open and shames whoever the culture holds at fault.
- **Wounds That Remain** — the loser does not limp off "badly wounded". They lose an eye, a hand or a leg, and carry the loss for life.
- **Seven Reasons to Fight** — war duels, honour duels born of grievance, trials by combat, champions whose single fight ends a war, duels between gods that leave divine wounds, ritual duels that mark a passage, an office or a bond by the culture's rules, and sport in clubs and contests that rarely kills.
- **Mercy on the Ground** — a downed fighter fights at a penalty. The victor's mercy decides whether the fallen live, honour decides whether a yield is accepted, and every exchange goes into a plain account for the battle report and the bard.
- **Exchange by Exchange** — every duel recorded step by step, each blow with its weapon, its target and the injury it left.

**In your world:** Two kings agreed that a champion would end their war. The challenger's spear held the first exchange. The defender closed, broke the challenger's elbow in a lock and, as mercy among the defender's people required, let the challenger yield. The bards sang of it, and the treaty held.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/54-blood-feud.jpg"><img src="common/assets/images/dlc-covers/54-blood-feud.jpg" width="220" alt="Blood Feud box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/54-blood-feud.jpg"><img src="common/assets/images/dlc-backs/54-blood-feud.jpg" width="220" alt="Blood Feud box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 54. Blood Feud

*They killed my kin. I will kill theirs.*

Your house remembers the name of every kinsman and kinswoman they killed. Each epoch the grievance asks what honour demands: a raid, a knife in the dark, blood money or war. Every answer adds a name to their side of the ledger. Around the feud turn captives held for ransom, heirs raised in the enemy's hall, and children carried off in raids who come back wearing the enemy's colours.

- **The Ledger of Blood** — a feud is the memory of killed kin between two houses or peoples. The aggrieved raid, ambush, assassinate, abduct, destroy property, demand blood money, call on allies or escalate to a war of vendetta, and every killing feeds the other side's grievance.
- **What Ends a Feud** — blood-money law, amends offered and accepted, mediation, intermarriage, a common enemy, a priest who preaches peace, an oath both sides swear to end it, and the slow fading of memory over generations. Breaking a sworn end is oathbreaking, and without any of these a feud outlives the people who began it.
- **The Feud That Sleeps** — a feud can lie dormant for years with no act on either side, then wake at a new offence, an insult or a remembered date.
- **Captives by the Thousand** — pursuits and sacks take whole cohorts captive, to be ransomed, enslaved where law allows, sacrificed where doctrine demands, worked, exchanged, freed, executed, pressed into the captors' ranks or adopted into their households. Named captives are tortured for war plans, escape, are rescued or turn coat.
- **Married In** — a named captive may marry into the captors' people, take on their customs and become a bridge or a traitor in the wars that follow.
- **Hostage Wards** — child heirs raised at the enemy's court absorb its culture and its memories. They return as friendly rulers or as vengeful ones, as their temperament decides.
- **Stolen Children** — raiders carry off children who forget their origins unless their memory is strong. They grow into captor soldiers or famous turncoats, while their kin plot rescues and quests.
- **Slave Soldiers** — enslaved cohorts fight with low morale, desert readily and may turn on their masters mid-battle when their own people stand opposite.
- **Parole** — a captured officer may swear never to fight again and walk free. Fighting again breaks the oath, the shame follows them home, and where the world's laws allow, the god who witnessed it strikes.

**In your world:** A raid took the chieftain's youngest child, who grew up in the captors' hall, forgot their own people and led the captors' warband back against them. An elder sibling killed them at the ford, and the feud began again from the other side.

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

Your god's faith is no longer a count of followers. It has a doctrine, a clergy, temples, schools, hospitals, lands and a treasury. Its tenets decide whether the maimed are holy or unclean, whether captives die on the altar, whether priests may found dynasties. Persecution feeds its zeal and comfort starves it. And somewhere a brilliant theologian is already drafting the heresy that will split it in two.

- **Twenty-Eight Tenets** — three to six per faith, each with real effects. Sacred suffering honours the maimed while purity of body calls them unclean, celibate clergy found no houses, and human sacrifice consumes captives and earns infamy abroad.
- **Zeal That Burns and Fades** — persecution, martyrs, miracles, holy war victories and plague raise it; prosperity, scandal and failed prophecies drain it. Push it too high and fanaticism follows: inquisition, iconoclasm, crusade.
- **Twelve Kinds of Zeal** — not every fervour is harsh. Charity zeal hands the faithful's wealth to the poor and fills their towns' stores with food, and pilgrim zeal empties whole households onto the roads, draining their homes and raising the holy place they walk to.
- **Ten Kinds of Holding** — temples, lands, relics, holy places, monasteries, networks, shares, lines, and now schools and hospitals. A faith that teaches and heals raises the learning and health of its towns and draws converts by it.
- **Clergy, Tithes and Relics** — leaders, celebrants, ascetics, teachers, healers, seers, judges, missionaries and keepers of doctrine and sites, paid by tithes that also fund alms, war chests and monasteries that keep learning alive through dark ages. Saints' relics draw pilgrims, coin and disease.
- **Heresy and Schism** — doctrine drifts under a creative theologian and splits into a heresy tree. Orthodoxy decides between inquisition and tolerance, councils vote on tenets and saints, and a vacant High Seat can crown two rival heads.
- **Missions on the Trade Roads** — preachers travel with the caravans. Conversion turns on how well the doctrine fits the culture, the missionary's skill and the miracles behind them, against rival clergy and the language barrier.
- **Church and Crown** — divine kingship fuses throne and altar; elsewhere priests and rulers fight over investiture, and excommunication strips a ruler's legitimacy. Your sons can reveal a new tenet and see whether it takes.
- **Sanctuary** — temples shelter criminals, runaway slaves and defeated rivals. A pursuer must besiege, bargain or wait, because breaking sanctuary is desecration.

**In your world:** The inquisition burned a beloved preacher. The preacher's followers caught a zeal of giving and emptied their purses into the poor quarter, a theologian gave them a doctrine, and the heresy broke away. When the High Seat fell vacant, each church crowned its own head, and every ruler had to choose a side.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/56-prophets-of-the-end.jpg"><img src="common/assets/images/dlc-covers/56-prophets-of-the-end.jpg" width="220" alt="Prophets of the End box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/56-prophets-of-the-end.jpg"><img src="common/assets/images/dlc-backs/56-prophets-of-the-end.jpg" width="220" alt="Prophets of the End box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 56. Prophets of the End

*The comet returns. The end is near. Sell everything.*

A comet hangs over the third hungry year. On the hill a prophet names the day the world will end, and farmers sell their fields to follow. Faith runs wild outside the temple too: mystics with visions the priests cannot control, hermits who draw seekers to their door, rites that guard the soul, gods whose silence through a plague becomes a crisis of belief, and cities that slowly stop praying at all.

- **Visions Outside the Temple** — intuitive, devout mortals have visions and states of union, gather followers beyond the clergy and found orders or heresies. Their contact is real only if a god chooses to answer, and only you know which.
- **Seven Kinds of Vision** — sights, union, voices, trances, dreams read by the culture's dream readers, oracular speech that draws crowds and courts, and signs read in the world itself. A mystic moves through seven states, from seeker and visionary to revered founder, persecuted, lapsed, or a hermit who stays apart and is brought gifts.
- **The End Is Coming** — prophecies of an end time, omens in the sky and deepening misery raise movements that sell their land, stop working, march, attack the unclean or wait for the end on a mountain.
- **When the Day Passes** — the faithful disperse, set a new date, or harden into a sect that will outlive its prophet.
- **The Silent God** — eight griefs test a faith: plague, famine, defeat, disaster, persecution, a long winter or summer that will not end, the loss of the faith's leader and a schism. When the god gives no sign, theologians argue, a new teaching casts suffering as a trial, or the people convert away.
- **Eight Sacraments** — birth blessings, initiations, marriages and last rites, joined by purification that lifts impurity and guilt, ordination that makes clergy, penance that restores standing after a judged act, and a shared sacred meal that binds a community and can spread sickness through the shared cup.
- **Rites with Real Protection** — sacraments shield the soul's road after death, protect children against possession, keep the dead from walking restless, and ward against curses and turned fortune where the world's laws give rites force. A plague that leaves no priest to give them is a real danger.
- **The Emptying Temples** — literacy, prosperity, city life, new theories of nature and gods who stay silent too long drain faith away. Disasters, wars and miracles fill the temples again.

**In your world:** A comet and a famine gave a prophet a date. Whole villages sold their land and climbed the mountain to wait. When the day passed, most went home poorer. The rest chose a new date and hardened into a sect, and when their prophet died the loss itself became the next test of their faith.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/57-beyond-the-veil.jpg"><img src="common/assets/images/dlc-covers/57-beyond-the-veil.jpg" width="220" alt="Beyond the Veil box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/57-beyond-the-veil.jpg"><img src="common/assets/images/dlc-backs/57-beyond-the-veil.jpg" width="220" alt="Beyond the Veil box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 57. Beyond the Veil

*Death is not the end. It is a verdict.*

A warlord dies certain of the warrior's hall. The judges weigh the warlord's renown, faith, the rites at the pyre and the villages burned, and the verdict comes as a shock. Now the afterlife is a real place with strata and gates. Ghosts walk for reasons, possession has a cure, the dead of some faiths never leave the house at all, and only an exceptional few ever come back carrying an old grudge.

- **Strata of the Dead** — realms of reward, a common realm, realms of punishment, dissolution, a realm chosen by the manner of death or a realm of one's own line, each with its entry criteria. Every realm of the dead shows its population, and every soul carries a ledger and the reason for its verdict.
- **Nine Afterlives** — a faith may teach judged realms, a common realm, a realm by the manner of death, a realm of the line, rebirth, wandering, union, oblivion, or that the dead stay among the living as presences in homes and places, fed and consulted by their kin.
- **The Weighing** — six doctrines of judgement weigh deeds, faith, rites, divine favour, nothing at all, or remembrance, where the dead fare by the graves, names and rites the living keep, so a forgotten soul suffers. The funeral rite counts, renown, honour, violence and unthinkable acts count, and the unburied wander restless.
- **Rebirth Is Earned** — a soul returns only through one of four gates, a faith's tenet, a law of nature, a rite or a god's own hand, and only if its life was exceptional. It comes back into its people, its house, a station earned by merit, a place, or as another kind of being entirely, and the reborn keep faint memories, enough to know an old enemy.
- **The Restless Dead** — a guardian spirit grows restless when its kin stop the offerings, a land under a god of death stirs its dead further, and enough unrest turns a guardian vengeful. Restless ghosts haunt the town where their killer's heirs live, sapping its prosperity, and every haunting feeds a ghost story that keeps people away. Spirits can be bound to a place, an item, a building, a beast, a person, a realm, a network, a line or a name, and whoever holds the name holds the soul.
- **Possession and Its Cure** — a spirit can take a living body, replace the host's mind with its own and fill the host with dread, until an exorcism drives it out.
- **Ancestors and Soul-Eaters** — venerated ancestors bring household luck and courage at ancestral sites, and turn restless when offerings stop. Soul-eaters devour the dead and rob a god of the faithful it was owed.
- **The Afterlife Surprise** — every faith teaches an afterlife, and the real one may differ. Souls who find their belief false suffer a revelation shock, and the dead who return in dreams can tell the living.

**In your world:** A warlord died certain of the warrior's hall and was judged into torment for the villages burned on the way to power. The shock left the ghost restless. It told the warlord's child the truth in dreams, and the child's account set the temple's theologians at each other's throats.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/58-spirits-of-hearth-and-river.jpg"><img src="common/assets/images/dlc-covers/58-spirits-of-hearth-and-river.jpg" width="220" alt="Spirits of Hearth and River box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/58-spirits-of-hearth-and-river.jpg"><img src="common/assets/images/dlc-backs/58-spirits-of-hearth-and-river.jpg" width="220" alt="Spirits of Hearth and River box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 58. Spirits of Hearth and River

*Pay the river spirit, or pay the flood.*

Every crossroads has its spirit, every hearth its luck and every river a temper. Make the offering and the crossing is safe; foul the water and the flood comes. Above them sits a heavenly civil service of city gods and river gods with ranks, written petitions and appeals to higher office. Spirits are promoted and dismissed, and a village can take its own river to court.

- **Twenty Kinds of Place Spirit** — rivers, springs, lakes, wells, shores, groves, forests, mountains, caves, crossroads, wilds, fields, cities and hearths, the open sea, ruins, battlefields, marshes, deserts and glaciers can each host a spirit with its own temper and tastes, and a running account of offerings and favours with the people around it.
- **Spirits of Great Places** — a sea spirit sways the voyages and catches of its waters, a ruin spirit guards its relics and wakes when diggers come, and a battlefield spirit grows where many died and stirs the dead and the living who pass.
- **Offend the Spirit** — content spirits bring fertility, safe crossings, good catches and hearth luck. Eight offences turn them: pollution, felled forests, an unpaid offering, a broken taboo, blood spilled in their place, taking more game, fish or plants than the land renews, trespass at a sacred spot, and the noise of mills, works and armies. Misfortune, floods and illness follow.
- **The Celestial Bureaucracy** — hearth gods, local gods, city gods, provincial gods and ministries hold five ranks under your sons and the foreign gods. Mortals petition them in writing, and petitions suffer delays, bribes paid in offerings and appeals to a higher office.
- **Eleven Kinds of Petition** — healing, harvest, fertility, safe passage, prosperity, lawsuits, rain, protection from beasts, raiders or disease, the finding of what is lost, justice where the courts have failed, and vengeance on a named wrongdoer, which a spirit that grants it carries out as a curse.
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

- **Lucky Days and Unlucky Numbers** — every culture reads luck in ten kinds of sign: days, numbers, sky signs, gestures, places, acts, people, animals, colours and the weather, each reading taken from the culture's own lore.
- **Where Luck Reaches** — readings sway ten parts of life: harvests, health, births, journeys, battles, deals, unions, the founding of houses and works, learning and contests. Believers delay, hurry, hold a rite or refuse outright when the signs turn.
- **Charms That Work, Charms That Comfort** — amulets for protection, fertility, luck, healing, love, safe travel, concealment and courage truly work where they are enchanted or blessed. Elsewhere they only calm the wearer, which is a real effect too, and you can see which is which.
- **Everyday Misfortune** — thirty-three kinds of household mishap, from a fall to a quake or a flood, are blamed on one of fifteen causes, plain chance or one's own conduct among them, and met in nine ways: a rite, an offering, a charm, an accusation, a purification, a safety custom, moving away from an unlucky place, or a claim for compensation from whoever is blamed.
- **Who Is the Witch** — illness, failed crops, a child's death or dying livestock with no clear cause find a culprit. Belief, grievance and social distance choose the accused: the envied neighbour, the widowed, the outsider, the eccentric.
- **From Accusation to Ordeal** — diviners and rumour name the accused, and eight outcomes follow: the case pending, cleared, punished, exiled or killed, a confession that names new accused, a flight that is read as guilt, or a reconciliation made by amends and rites that leaves no grudge behind.
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
- **Eleven Ways to Read the Gods** — augury, sacrifice readings, astrology, oracles, lots, dream reading, scrying, consulting the spirits of the dead, signs in the earth, numbers and the reading of the body. Each is truly informative only where a god answers, a seer has the gift or the laws of nature allow. Elsewhere trusted diviners breed folly.
- **Ten Questions Asked** — before a battle, a war, a wedding, a coronation, a harvest, a voyage, a founding, over the sick, about who will succeed an ageing ruler, and after something lost. An auspicious, inauspicious or unclear answer hastens or delays the act, names an heir or sways the care of the sick.
- **Seers and Blind Spots** — foresight comes from five sources: a power, a divination, a god, a made oracle or a dream. The gifted glimpse probable futures that can still be wrong, because others act on prophecy too. Rival seers blind each other, and outer beings never appear in any vision.
- **Born Under a Sign** — every mortal carries the sky of its birth. Where the stars truly hold power the sign shapes temperament and fortune; elsewhere it is belief alone, and a child born under a dreaded sign may be cast out.
- **Eight Kinds of Dream** — ordinary, nightmare, longing, prophetic, visitation, shared, lucid and memory dreams. Nightmares recur, dream readers misread, and a ruler's dream taken for a war omen can start a war.

**In your world:** A seer foretold that a child of the river house would rule. The ruler's fear became a purge of the house's infants. One escaped to foster parents, grew up on the prophecy, and took the throne from the ruler who had ordered the purge.

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

Your mage does not pick a spell from a list. The mage writes one: a technique and a form, a range, a target and a duration, tested through a season in the laboratory and copied into a text apprentices can learn. Then the world argues back. Rain dampens the fire, iron unravels the spirits, a gag stops the words, and the theory the mage was taught may simply be wrong.

- **Spell Grammar** — thirteen techniques, from create and perceive to bind, ward, heal, move and speak, crossed with twenty-three forms from fire and water to time, void, light, dreams and the laws and oaths of a people. Every combination has its price.
- **Reach and Span** — seven ranges run from touch and sight to a region, a whole world, any distance through a link to the target, other worlds, and other dimensions through a rift or gate. Seven durations run from an instant to a season, an epoch, forever, as long as the caster sustains it, until a set condition is met, or for the target's whole life.
- **Nine Kinds of Target** — one being, a group, a building, a region, an item, a whole line of descent that passes the working to its children, a world, every member of a species or every member of a people, each member resisting on its own.
- **Vis and the Black Market** — magical resources of every form, fire vis to death vis, gathered at magic sites, cut from beasts and drawn from phenomena. Where magic is banned they move through the shadows.
- **Resistance and Counterspells** — will, discipline, faith, sanctity, resistant materials, dampeners, distance, a rival source, disbelief where the world lets belief matter, and the protection of kept ancestor rites. Counterspells, dispels and wards meet in contests of power.
- **Rain on a Fire Rite** — magic reads the weather and the world. Wet targets conduct storm rites, rain weakens fire and strengthens water, a dry forest turns a fire rite into a wildfire, and void rites overflow where the dark leaks in.
- **Tongue, Hand and Breath** — rites need speech, gesture, inscription, song, dance, reagents, focus, something given up in place of the caster's own strength, or many workers at once who share the strain. A tongueless mage can still inscribe, a blinded one can still chant, and captive mages are held with gags, bound hands and blindfolds.
- **Material Magic** — metals that grant strength to the gifted who consume them, crystals that store a technique, substances that ward off spirits, and enchanted items with charges that crack with overuse and refill at a magic site, from vis, with the moon, at an eclipse or comet, by an offering of the body, by rest or through the prayers of a worker's followers.
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
- **Curses and Transformations** — dark rites lay curses, blessings and changes of the body on their targets, the same afflictions that turn a mortal into a beast under the moon.
- **Ten Kinds of Link** — hair, blood, a name, a true name, a portrait, a fragment of a thing, a worn or kept possession, a footprint, a voice or a record of birth links a rite to its target at any distance. The stronger the link, the deeper it strikes, and a true name lets a rite command or bind a lesser being outright. Peoples who know this guard their voices, birth records and true names by custom.
- **Power Bound by Conditions** — thirteen restrictions make a power stronger for what it gives up: only in one place or at one time, only against some, a spoken vow, a price each use, never on oneself, a forbidden act, seen or unseen, by touch, with a token, only in company, or only when the target's name is known.
- **Warping** — mages, people who live on ley lines and wearers of enchanted items slowly change: strange looks, attunement, madness, unnatural long life.
- **Bought Decades** — potions and rites hold off age at a price in rare resources, with warping and a growing dependence. Cut off an ancient mage's supply and the years come due.
- **Eleven Hazards** — power can wound, madden, widen the void's leak, let a summoned thing escape, deplete its source, warp, burn out, breed dependence, draw unwanted attention, spend the user's years, or open the body to a spirit or outer being that takes it for a time. A failed storm rite can become a storm that never ends.

**In your world:** Rivals seized the spring that fed an ancient mage's longevity potions. The years caught up at once, and in desperation the mage tried a void rite. It failed, and the thing it summoned slipped its bonds and went hunting in the valley below.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/63-walkers-of-myth.jpg"><img src="common/assets/images/dlc-covers/63-walkers-of-myth.jpg" width="220" alt="Walkers of Myth box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/63-walkers-of-myth.jpg"><img src="common/assets/images/dlc-backs/63-walkers-of-myth.jpg" width="220" alt="Walkers of Myth box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 63. Walkers of Myth

*Walk the god's path. Change the god's story.*

The elders tell how the god crossed the river of night. Your hero walks into that myth and must walk it step by step: the same trials, the same choices, the same faith. Follow the story and the boon is sure. Break from it and you may win something new, and come home to find your people telling the tale your way.

- **Legends That Live** — twenty-two archetypes, from creation, world disaster and the trickster to the cursed line, the return of a ruler, the bargain, the ascent and the fall. Every retelling bends the tale toward the teller's values, so in an honour culture a defeat becomes a betrayal. Only art fixes a legend in place.
- **Stories That Move People** — a return-of-a-ruler legend strengthens the pretender who fits it, a cursed-line legend shames a house, and a haunted-place legend keeps settlers away with no ghost there at all. You can compare every telling with the truth.
- **Heroquests** — questers enter the god's palace, the realm of the dead, a dream world or a sacred site, facing eight kinds of trial: skill, passion, conviction, faith, cunning in riddles and tricks, endurance of hunger, cold and distance, mercy passed by sparing, and sacrifice passed by giving up something held. Failure traps the soul or breaks the myth.
- **Ten Boons** — a blessing, an item, a rite, a lifted curse, a renewed land, a god's favour, a true name, a title, knowledge, or healing carried home.
- **Rewritten Myths** — a quester who deviates may win a different boon, and the people's version of the legend changes with the hero's return.
- **Myth-Powered Rites** — rites that re-enact a believed myth grow stronger, stronger still at the myth's own site. A corrupted myth gives a corrupted rite.
- **Geasa** — never refuse hospitality, never pass a burning house. A seer, a god, a rite, a kin's word that passes down the line, a court's law or the holder's own vow lays the bond. It may forbid, demand, or wait for a set thing to happen and then bind a set act. Keeping it wins favour, breaking it brings doom, and enemies build traps to force the breach.
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

- **Bodies Made, Not Born** — a maker shapes a body of clay, stone, bronze, iron, steel, a composite or a polymer and moves it with the power of a ley line, a god, blood, a bound soul, reagents or the void.
- **Orders to the Letter** — "guard the gate", "kill intruders", "obey whoever holds the seal". Constructs follow their instructions literally, so every order hides a loophole and every seal is a prize worth stealing.
- **Eighteen Kinds of Order** — guard, serve, obey the holder, build, gather, protect, destroy, report, maintain, copy itself, hold still, follow, forbid, carry loads along a route, tend fields, herds or the sick, teach, heal and hunt, each read against the construct's own skills.
- **When an Order Holds** — always, while the maker lives, while the holder lives, until a date, when attacked, when a token is shown, until the task is done (and "done" is the maker's own loophole), by day, night, season or sky event, or only when its name is spoken.
- **Who Commands It** — a seal, a word, a bloodline, an office, a network key, a gesture, or the construct's own true name, which overrides every other token. Orders are bound by command, oath, geas, seal, ownership, lease, symbiosis or a debt that ends when it is paid and passes to heirs until then.
- **Workings That Fade** — power sources dwindle, materials wear, and the workings need renewing by a maker with the skill. Neglect runs them down or wears them away.
- **The Master's Death** — when the maker dies, the construct keeps its last orders forever, a hazard in every ruin and a guardian in every tomb.
- **The Soul in the Machine** — constructs built around a bound soul inherit fragments of who it was, and over epochs they begin to want. When they rise against their masters, the rebellion has a cause.
- **Legions from the Foundry** — identical constructs made in numbers work the mines and fields and fill the ranks. They feel no fear, but a dispel or a lost command seal stops them dead.

**In your world:** A tomb robber lifted the command seal from a dead emperor's crypt, and the bronze guards that had killed every intruder for centuries followed the robber out. The robber hired them to a mine, until one guard, moved by a bound soul, remembered it had once been a slave.

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

Your son of the Sea does more than watch the waves. Its worshippers fight harder at sea, their voyages lose fewer ships, and its essence swells with every voyage. Forty-seven domains reach into war, trade, faith, nature, cities and machines through hooks of their own. A god is now what it does in the world, and when a Harvest god takes a wound, its worshippers face a hungry decade.

- **Forty-Seven Domains, All of Them Mechanical** — every domain does real work, from Sea, Fire and Death to Technology, Cities, Information, Space and Science. Glass speeds the research of its faithful, Lies twists the rumours they pass, Road makes their routes safer, and Time slows their ageing and makes their prophecies surer.
- **Domains That Combine** — sixteen pairs of domains strengthen each other. A god of Sea and Death sends the drowned to its own realm, Sea and Storm strengthen the faithful fleets, Road and Trade bring more trade, and Dream and Sleep bring more dreams.
- **Essence Earned by Deeds** — income follows each domain's activity, battles for War, deaths for Death, voyages for Sea. Gods cultivate their domains, quarrel over the same sailors and contest the same battle with rival miracles.
- **Five Ways to Worship** — a people may worship in devotion, in appeasement of a god it fears, as a bargain of offerings for favours owed, in search of union with the god, which raises mystics among them, or as the god's own kin, which makes their people hold family dearer. A bargain left unanswered turns to neglect faster than devotion does.
- **Six Tones of Prayer** — thanks, pleas for mercy, requests, praise that raises a god's renown without asking anything, laments that draw the gods' notice to a suffering world, and confessions that ease the one who prays. Each tone feeds the god's essence by its own measure.
- **Gods with Goals and Grudges** — fourteen kinds of goal: be worshipped, found a realm, destroy a rival, spread a domain, win a war, gain a relic, raise a hero, awaken a god, defeat a foreign god, hold thrones, reconcile with the Creator, rebel, or stop or sponsor a mortal's rise to godhood. Gods remember who stole their worshippers and who helped their hero.
- **Love, Awe, Fear and Neglect** — every people holds its own standing toward every god. Answered prayers breed love, wrath breeds fear, silence breeds neglect, and neglect drains worshippers and existence alike.
- **Hearts, Schemes and Wounds** — gods feel wrath, jealousy, pride and longing, befriend, marry and frame each other through mortal agents, and curse whoever defiles their shrines. Their wounds come in eleven kinds, from a severed domain, a shattered form or a stolen true name to a seat left in ruins and worship split between rival churches, each with a severity the god carries until it heals.

**In your world:** Sea and Storm fought over the same sailors. Storm's mortal agents framed Sea's priests for desecrating a harbour shrine, but the scheme was uncovered. The pantheon council voted to strip Storm of a power, and Sea never forgot it.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/66-dominion.jpg"><img src="common/assets/images/dlc-covers/66-dominion.jpg" width="220" alt="Dominion box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/66-dominion.jpg"><img src="common/assets/images/dlc-backs/66-dominion.jpg" width="220" alt="Dominion box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 66. Dominion

*The gods' war is fought over every field and village.*

Look at the map and you see it: your son's presence pooling around its temples, its prophets and its saints, seeping into the next valley, pressing against a rival's light. Where its dominion rules, its scales rule too. Crime falls or unrest rises, the air warms or cools, the fields swell or decay. Every farmer feels which god is winning.

- **A Map of Divine Presence** — every god holds a strength in every region, fed by temple splendour, holy sites, prophets, saints, miracles and worshippers. Each epoch it spreads into neighbouring land, and every god knows where it is losing ground.
- **Eight Scales** — order or turmoil, productivity or sloth, heat or cold, growth or death, fortune or misfortune, magic or drain, health or sickness, peace or strife. Each runs from minus three to plus three, is set by the god's domains at its making and drifts with its miracles. Order, productivity, heat, growth, fortune and magic reshape every region the god dominates.
- **The Home Advantage** — under its own dominion a god's miracles cost less and work better, its missionaries convert more easily and its worshippers fear less. Rival miracles cost more there, and rival priests feel the strain.
- **Credit and Blame** — where dominions overlap, each people decides which god it thanks for a miracle and which it blames for a disaster. Gods gain and lose standing for each other's acts.
- **Seven Manifestations** — a god shows itself radiant, serene, stern, dreadful, playful, sorrowful or veiled, as its peoples come to see it. A veiled god works through signs, coincidences and dreams: its miracles are seen by fewer witnesses, win less awe and give rival gods less offence.
- **Thrones of Power** — a few mythic thrones on every world grant dominion, essence and standing across it. Holding most of a world's thrones counts toward a god's ascension, and mortals fight these wars on their gods' behalf.
- **Eight Kinds of Magic Site** — sources, seats of a school, wards, gateways, tide points, scars where a source was drained, confluences where sources meet and yield more while making the land more dangerous, and null zones where no power works at all. Most stay unseen until a mage of the matching school finds them, they yield magic every epoch, and realms go to war for them.
- **Gods Built to a Budget** — each summoned son spends a creation budget on stats, dominion, scales, magic, an avatar body and powers. Extreme scales cost or refund budget, and Fate checks the design, so sons differ in kind, not only degree.

**In your world:** A Death son's temples and a captured throne of power spread its dominion across a small world. Its scale tipped toward death: fields decayed and the spirits grew restless, until the Life son's worshippers marched to take the throne back.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/67-made-in-their-image.jpg"><img src="common/assets/images/dlc-covers/67-made-in-their-image.jpg" width="220" alt="Made in Their Image box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/67-made-in-their-image.jpg"><img src="common/assets/images/dlc-backs/67-made-in-their-image.jpg" width="220" alt="Made in Their Image box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 67. Made in Their Image

*The people believe their god is cruel. Now it is.*

You summoned a son of War. Its frightened worshippers remember it as dreadful and cruel, and slowly, epoch by epoch, it becomes exactly that. Belief pulls hardest in plague and war, on a fading god, from a faith that agrees with itself. A proud god resists. A vain one yields. Your gods are partly what their peoples make of them.

- **Belief Shapes Gods** — each epoch the stories a people tells pull its god's temperament and the face it shows toward the believed image, and miracles the people credit to a domain the god lacks can give it that domain in the end. The pull is strongest when the image is uniform, widely held and the times are desperate.
- **Resist, Embrace, Bargain or Pin** — a son can yield to the image, pay essence to resist it, embrace it for fame, or bargain with it and take on only part of it, and you can pin its nature so belief cannot touch it. Pride and willpower hold firm; vanity yields, and a fading god is clay.
- **Loved or Feared** — from its acts each people reads a god as benevolent, ambivalent or malevolent. That sets devotion or appeasement, its temples, the face it is shown with and its prayers: a loved god is begged to come, a feared one paid to stay away.
- **Miracles That Count** — a miracle is worth its magnitude times its witnesses, need and novelty. Bread in a famine counts more, the tenth repeat less, and in a land another god rules, a miracle that fits that god better may be credited to it.
- **Fed by Emotion** — every domain drinks two mortal feelings. War feeds on rage and pride, Love on love and longing, Death on grief and fear, Madness on despair, Trickery on amusement, the Hunt on fear. A god of grief prospers in plague years.
- **Heaven's Bureaucracy** — sons supervise the offices of lesser spirits, processing petitions and appointing city gods. Diligence earns standing and dominion; neglect rots the bureaucracy into corrupt spirits, unanswered prayers and cults of rogue spirits.

**In your world:** A people's legends made the War son a figure of dread, and over the epochs it came to be shown dreadful. Its temper drifted toward wrath with it. A neighbouring people who knew it as a peacemaker saw their god turn apostate, and their faith split in two.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/68-avatars.jpg"><img src="common/assets/images/dlc-covers/68-avatars.jpg" width="220" alt="Avatars box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/68-avatars.jpg"><img src="common/assets/images/dlc-backs/68-avatars.jpg" width="220" alt="Avatars box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 68. Avatars

*The god walks among us. The god can bleed.*

Your son puts on flesh and walks into a mortal city. It can act, fight and be killed, and if a mortal blade finds it the wound follows it back to heaven. Or it raises a great beast and teaches it with reward, punishment and warning until it acts on its own. Or it leaves a child in a mortal house, and a bloodline begins.

- **Avatars in Mortal Form** — a son can manifest as a mortal who walks the world and acts in it. The avatar can be wounded and killed, and its death leaves the god itself with a divine wound.
- **Ten Ways a God Is Wounded** — a duel, a war between gods, the Creator's hand, a slain avatar, an outer bargain, an outer being's attack, neglect when its temples fall silent and its name is forgotten, betrayal by its own priests or allies, a schism among its faithful, and a mortal who strikes it with a god-bane weapon, a true name or a rite.
- **The Divine Creature** — raise a great beast that acts on its own between your son's turns. It hunts folk, tends fields, guards holy sites, strikes foes, heals the sick, wrecks works, wanders, rests, carries its god's messages, teaches the people around it or trades with them.
- **Taught, Not Scripted** — its god rewards a habit, punishes it, or warns the creature off it, which pulls the habit halfway back to where it began. Every lesson reshapes what the creature chooses to do, and a neglected creature drifts toward its own hungers. Whatever it does, the people credit or blame its god, in standing and in dominion.
- **Divine Blood** — the mortal children of a god mark their house with divine blood, a lineage the world can read and that runs on down the generations.
- **Children of Two Gods** — a child born to two gods inherits the average of its parents' powers with a deviation of its own, plus one domain from each parent. A child of Sea and Death can be heir to both.

**In your world:** A Harvest son trained its divine creature to help farmers, punishing it each time it ate a villager. When the son's attention turned to another world, the neglected beast drifted back to its hungers, and the valley's love for its god turned into fear.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/69-court-of-heaven.jpg"><img src="common/assets/images/dlc-covers/69-court-of-heaven.jpg" width="220" alt="Court of Heaven box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/69-court-of-heaven.jpg"><img src="common/assets/images/dlc-backs/69-court-of-heaven.jpg" width="220" alt="Court of Heaven box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 69. Court of Heaven

*Even gods must vote. Even gods must scheme.*

The pantheon gathers and the motion is war on a foreign god. Votes weigh old friendships, private goals and grudges, and the result binds every god for epochs, enforced as law. Lose the vote and your son may be chained, exiled, fined in essence or bound to a single world. And a motion that fails can escalate, backer by backer and favour by favour, into divine war.

- **Twenty-Seven Kinds of Motion** — war on a foreign god, divide the worlds, outlaw a rite, a power or a source, punish a son, bless a hero, declare a holy world, set a cosmic truce, petition the Creator, appoint an office, admit or expel a member, rule on made minds, powers, living craft and curses, open an inquiry into a god's acts, grant an amnesty that lifts penalties and grudges, and more. Each one passed becomes binding law for a set span of epochs.
- **Eight Penalties** — chains, exile, a stripped power, stripped divinity, a penance the god must finish by a deadline (restore a world, raise a hero, undo a curse) or face worse, a fine of essence paid to the council or the wronged, binding to one world for the term, and a rebuke that costs standing alone.
- **Councils as Crises** — motions gather backers, call in favours and escalate through censure, sanction and exclusion to a duel or war between gods.
- **Cosmic Offices** — Lord of the Dead, Keeper of the Gates, Warden of the Stars, Judge of Oaths, Herald of the Creator, Master of the Hunt. Each brings duties, rites and essence, won by vote, the Creator's grant, conquest, mantling or inheritance by a god's offspring or chosen heir.
- **Duties Left Undone** — an absent Lord of the Dead lets ghosts multiply. An absent Keeper of the Gates lets the routes between worlds decay.
- **Divine Servitors** — thirteen roles: messengers, guards, judges, heavenly hosts, spies, agents, avengers, guides of souls, worshippers, wardens, scribes, healers and teachers. They are made, raised from saints, summoned, born of their god, defected from a rival with secrets and grudges, bought in an outer bargain on the being's terms, or risen from mortals with their old ties intact. They have minds of their own, and ill-treated servitors fall to a rival or the outer dark.
- **Foreign Gods with Agendas** — the old gods of a world gain goals, domains and standing of their own. A native Harvest god competes with your son of Harvest for the same farmers, and seeds the tenets of the native faith.
- **Pacts and Pantheons** — foreign gods hold opinions of each other and of your sons, ally against the pantheon, scheme, sign divine pacts and share worship. Native pantheons have family trees and divine titles their peoples tell of in legend.

**In your world:** The council made a son of Death Lord of the Dead, but it spent the next epochs chasing a rival's worshippers. Ghosts multiplied across the realms it neglected, an inquiry laid the neglect bare, and the office passed to the rival it had been robbing.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/70-apotheosis.jpg"><img src="common/assets/images/dlc-covers/70-apotheosis.jpg" width="220" alt="Apotheosis box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/70-apotheosis.jpg"><img src="common/assets/images/dlc-backs/70-apotheosis.jpg" width="220" alt="Apotheosis box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 70. Apotheosis

*A mortal walked the god's path. Then killed the god.*

A mortal champion copies your son's defining deeds, gathers a cult of their own and survives the god's anger. Your son is weak: its faith thin, its standing low. The champion is overwhelming. When the champion finally strikes it down, Fate may grant the god's place, its domains, its dominion and part of its worshippers. You saw it coming the whole way. The question is whether you acted.

- **The Mantle of a God** — imitate a god's defining deeds, gather worship and survive the god's opposition, and a mortal can ascend as a new son when Fate approves.
- **Slaying a God** — replacement needs three things at once: a god weak in existence, faith and standing; a mortal overwhelming in renown, worship, deeds and power; and the god's death at that mortal's hand. Your own sons are not exempt.
- **A Contested Mantle** — two mortals who both finish walking the same god's path stall each other: both claims are marked contested and neither ascends while the rival stands. Every mantle shows whether it is being walked, won, taken by replacement, contested, blocked or failed.
- **The Fallen** — a god stripped of divinity wakes as a mortal with great gifts, memories of godhood, a hidden true name and no essence. A loyal remnant may recognise it, and it can seek its name or a heroquest to climb back.
- **Lost to the Void** — a son driven to zero sanity by void bargains passes out of the cosmos as an outer being, keeping its memories and its grudges. Its worshippers become an outer cult, and no resurrection is possible while the horror endures.
- **Everything Can Become Something Else** — forty kinds of transformation into twenty-nine kinds of end form. A cursed people loses its sapience and turns feral; a cult with endogamy and a diaspora becomes a nation; a beast founds a species, the "children of the Wyrm". Names, history and memories carry across.
- **Thirteen Triggers** — a change can come from the engine's own course, a god, the Creator, the council, a curse, the void, fading, a dark age, a punishment, force, the world's past, worship reaching a threshold that raises a being or a place, or a mortal's named deed that becomes legend.
- **Suns That Become Gods** — a star worshipped long enough becomes a god whose dominion follows its light, and a living world its peoples worship can ascend as a god whose body is the world. Kill a star-god and its sun dims.
- **Warnings and Levers** — you hear of a fall one epoch ahead, of a son entering the corruption danger band, of a mortal starting to meet the conditions to slay a god. Cleanse, forbid bargains, chain, block or pin: you can always act.

**In your world:** A son of the Hunt bargained with the void until its sanity broke and it passed out of the cosmos. Its hunters became an outer cult. Generations later, when the horror was banished, its last faithful began a redemption heroquest to bring it home.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/71-laws-of-creation.jpg"><img src="common/assets/images/dlc-covers/71-laws-of-creation.jpg" width="220" alt="Laws of Creation box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/71-laws-of-creation.jpg"><img src="common/assets/images/dlc-backs/71-laws-of-creation.jpg" width="220" alt="Laws of Creation box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 71. Laws of Creation

*Rewrite the rules of reality. Pay the upkeep.*

Your son decrees that oaths bind, and from that epoch every oath-breaker in its world is cursed without a priest lifting a finger. A rival decrees a contrary law, and where the two meet the weaker erodes or reality cracks into a region of conflicting physics. Above them all sits you, the Creator, with passions the world can please and taboos it had better not break.

- **Twenty-Four Laws of Nature** — immortality or short lives, the dead who return, no iron, no gunpowder, eternal night over a region, souls that reincarnate, magic that demands blood, shifted gravity, reversed or long seasons, dreams made real, oaths that bind, the dead who speak, metal that rusts fast, and more. Each has a strength and a scope: the whole cosmos, a dimension, a world, a region, or a single stratum of the deep or of the afterlife that then runs by its own rules.
- **Who Is Spared** — a law can exempt those the Creator chooses, its author's worshippers, heroes, avatars, the holders of a divine office, those bound by an outer bargain, or one named species, people or kind of being, so a world can lack iron for everyone but one people.
- **Physics Rewritten** — laws reach into the sky itself. Shift gravity, reverse the seasons or lock a world's face to its star, and every value that follows from them changes too.
- **Contested Physics** — when two gods' laws contradict, they contest by strength. The weaker erodes, or the land between them becomes a phenomenon of conflicting physics.
- **Laws Need a Living Author** — every law decays without its author's essence, so the death of a god can unmake the rules of a world.
- **Global Enchantments** — eternal summer over a world, a ward against outer beings, barren wombs on an enemy world, a calm on every ocean. Gods, mage orders and foreign gods cast them and pay upkeep each epoch, and rivals can dispel them.
- **The Creator's Passions** — order, chaos, beauty, knowledge, war, mercy, creation, silence, freedom and memory each read the world: wonders for beauty, spreading learning for knowledge, battles for war. A knowledge-loving Creator sends revelation dreams to scholars.
- **The Creator's Moods and Signs** — contentment, anger, interest, loneliness and sorrow move your mood. Sorrow rises with killing, ended worlds and lost peoples and cools your wrath. Sixteen kinds of sign answer the world, from wrath, grace and omens to a rebuke that marks a wrong without harm and an invitation that calls a people to seek you.
- **Taboos and the Watching Eye** — break a Creator's taboo, son or mortal, and wrath signs follow. Your attention is a budget: worlds far from the eye drift, their sons act more freely, and rebellion grows likelier.

**In your world:** A son of Fire cast an eternal summer over its faithful's world and paid the upkeep in essence every epoch. When a lost war drained its worshippers, its essence ran dry, the enchantment failed, and a people who had never known winter met their first.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/72-the-hungering-dark.jpg"><img src="common/assets/images/dlc-covers/72-the-hungering-dark.jpg" width="220" alt="The Hungering Dark box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/72-the-hungering-dark.jpg"><img src="common/assets/images/dlc-backs/72-the-hungering-dark.jpg" width="220" alt="The Hungering Dark box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 72. The Hungering Dark

*It eats words. It eats memories. It eats light.*

Somewhere beyond the edge of creation something is hungry, and its hunger has a shape. One eats words, and they vanish from every tongue it touches. One eats light, and a star dims in your sky. Its cults whisper false beliefs into willing ears, its breach points bleed horror into the land, and when the doom clock strikes, the apocalypse wears the face of what fed it.

- **Seven Hungers** — souls, knowledge, light, names, memories, dreams and time. A soul-eater empties the realms of the dead, a memory-eater erodes belief in legends, a light-eater dims stars, a word-eater steals words from languages, a dream-eater robs the sleepers of its world of rest, and a time-eater ages the mortals it touches.
- **Size Matters** — a greater being reaches more regions and costs more essence or sanity to oppose.
- **Bargains with Terms** — a desperate son or mortal gains essence, a power, might, forbidden knowledge, a longer life, a dead one returned, changed by the being's terms, or protection for a place or people against a named harm. The price comes due later: a world's sanity, a domain, the bargainer's true name, the souls of its worshippers, its descendants, each child marked with a curse until the debt is paid, its memories or its years.
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
- **Five Pulls of Gravity** — from the near-weightless drift of asteroids and small moons to the crushing pull of the largest worlds. Each band sets how fast armies march, how high a city can build, how easily ships launch and how hard the world wears down bodies not made for it.
- **Life in Every Niche** — life can arise in eight places: seas, land, air, underground, oceans sealed under ice, the cloud layers of giant worlds, deep hot vents and the empty space between worlds. Which of them a world offers follows from its own physics and chemistry.
- **Air to Breathe** — beings breathe oxygen, carbon dioxide, methane, ammonia, hydrogen or sulphurous air, or need no air at all, under seven atmospheres from none and thin to dense, toxic, steam and layered air with one breathable band between poisonous layers. A people whose air the world does not hold grows slowly and sickens there, and terraforming can shift a world's air toward the breath of its settlers.

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
- **Stones from the Sky** — comets, asteroid fields and rogue worlds cross orbits. A strike leaves a crater, regional ruin, star metal and an impact winter that fails harvests and drives species extinct. Sons can deflect or call impacts; astronomers can see them coming, and a warned land suffers less.
- **Seven Things That Fall** — besides asteroids, comets, rogue worlds and impacts a god calls down, the sky drops pieces of a broken moon, wrecks of ships and works decaying out of orbit, and ejecta thrown up by an earlier blow. A falling wreck brings salvage to the crater, and sometimes a relic that still works.
- **Six Ways a Fall Ends** — a body can strike, miss, be deflected, burst in the air, be captured into orbit as a new ring, or break apart into many smaller strikes. An airburst flattens forests and towns across a wide reach with no crater and a smaller winter, and the year of a great impact is remembered by name.
- **Twin Suns** — worlds circle one star or both, with double seasons, double-sun eclipses and a habitable band drawn by both stars together.
- **Nebulae, Nurseries and Black Holes** — nebulae slow and hide travellers, nurseries birth new stars for sons to claim, black holes send travellers home younger than their kin, wormholes open unstable roads, and asteroid fields hide void pirates.
- **Nine Wonders of a System** — asteroid fields, wormholes, periodic comets, rogue worlds, gravity wells, wandering stars, nebulae that hide pirates on every nearby route, rings of debris that keep raining ejecta on the worlds below, and unseen dark bodies that make every route near them more dangerous.
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

- **Fourteen Divine Earthworks** — raise or lower land, carve or fill valleys, shift rivers, open springs, call lava, sink a coast, parch, green, enrich or salt the soil, raise a new island from the sea, or open the underground to the surface. Elevation, water and soil change for real, downstream regions gain or lose water, and the politics and the faith follow.
- **Worlds with Weight** — gravity slows armies, shortens siege-engine range and caps building height. Thin air saps endurance, toxic air breeds disease, and low-gravity worlds favour flyers and sky mounts.
- **A Planet That Feels** — a living world answers mining and clearing with quakes and hostile beasts, and reverence with fertility. Old worlds cool and wear out their soils, and a collapsing biosphere brings famine and new diseases.
- **Belief-Shaped Worlds** — worlds drift toward the faith of their peoples. A fearful people's dream world grows nightmares, a Sea god's world floods, a Death god's world turns corpse-like, a slow and contestable change you watch on a gauge.
- **Terraforming and Its Victims** — gods and advanced realms pursue eleven aims over epochs: thicken or thin the air or make it breathable, warm or cool, water or dry, brighten or darken a world, seed it with life, or steady its seasons against long winters. Native life of incompatible chemistry suffers, and those who live off the old ecology can sabotage the plan.
- **Eleven Ends of Worlds** — shattered into an asteroid belt, consumed by a swelling star, frozen dead under a dead sun, sunk into the void, forgotten, transfigured, drowned under rising seas, burned barren, devoured by an outer being, emptied of all life while its ruins stay for salvage, or merged into another world. Each fate reaches souls, routes, exiles abroad and gods.
- **Every End Has a Cause** — thirteen causes are tracked and named: impacts, divine wrath, a swelling or dying star, the void, oblivion, belief drift, a runaway climate, a war fought with weapons of mass harm, an outer hunger, plague, runaway self-making machines, and the failure of a made world as its builders' works wear out. Where a cause has an author, the chronicle names them.

**In your world:** Two sons contested a valley. One flooded it to drown the other's temple. The flood cut a trade route and shifted the river, a downstream people lost its fields and followed its diaspora abroad, and the drowned temple became a site of heroquests.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/76-thirty-four-worlds.jpg"><img src="common/assets/images/dlc-covers/76-thirty-four-worlds.jpg" width="220" alt="Thirty-Four Worlds box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/76-thirty-four-worlds.jpg"><img src="common/assets/images/dlc-backs/76-thirty-four-worlds.jpg" width="220" alt="Thirty-Four Worlds box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 76. Thirty-Four Worlds

*Ocean worlds. Gas giants. Generation ships. Realms of the dead.*

On a gas giant there is no ground and falling is death, so cities float and every war is fought in the sky. On a generation ship the weather is a failing air system and revolution is called mutiny. In the realm of the dead nobody is born, and the dead live on the offerings of the living. The expansion launched with thirty-four kinds of world and now holds thirty-seven, and each one rewrites the rules, down to whether fire can burn.

- **Thirty-Seven Rulebooks** — every world type changes its ground, sky, life and warfare. Sand worlds bury cities under moving dunes and fight over water rights; ice worlds hunt through the ice and huddle round thermal vents; jungle worlds breed plague and ambushes.
- **Rogues, Archipelagos and Made Worlds** — a rogue world wanders with no star and lives by light from within or none; an archipelago turns every road into a sea route; a megastructure is a world someone built, a ring, a shell or a hollowed body, whose prehistory is the ruin of its builders and which ends when its works wear out.
- **Strange Ground** — regions become cloud bands on gas giants, decks on generation ships, organs on a living world and strata in the realm of the dead. Tidally locked worlds live along a single habitable ring.
- **Exotic Ecologies** — aerial plankton and floating flora, vent gardens under ice shells, hydrocarbon life in methane lakes, spore fogs on fungal worlds that carry both plague and dreams.
- **Thirteen Ways to Settle** — on the ground, floating, on stilts, at an oasis, around a vent, in a sealed habitat, along a habitable band, on a ship's decks, in burrows, beneath the water, in the canopy of great forests, on cliffs reached by lifts and paths, or on drifting ice and rafts that move with the currents. Each way sets who can live there, how well it defends and what weather reaches it.
- **Nine Grounds of War** — land, sea, sky, boarding actions, the strata of the dead, under water, open space, tunnels and caverns, and across dimensions through rifts and gates. Each ground sets which units can fight there and how fronts form: three-dimensional under water and in space, narrow and blind underground.
- **No Fire without Air** — the foundations bend to the world. No fire without oxygen, no soil on asteroids, air rationed as a stock, buildings squat under the gravity of a super-earth.
- **Light and What Binds** — ten sources of light, from a star, lava glow, magic, an inner sun, a god or a fading god to a ship's day cycle, glowing living things, made light or none at all. Some worlds bind their settlers to a need, whether water, heat, air, offerings, belief, a guardian spirit of the place or names kept in writing, and a town that cannot meet it suffers for it.
- **Wealth of Strange Worlds** — iron worlds double their ore and arm everyone, diamond worlds run on the gem trade, forge-worlds poison their own soil with soot, and strong dreamers conjure materials on dream worlds at a cost to their sanity.
- **The Dead Without Scavengers** — where nothing eats carrion, the dead stay. Mummified in deserts, frozen on ice worlds with old diseases inside them, sinking into a gas giant's depths, drifting through void habitats as hauntings. Funerals become a real cost.

**In your world:** On an ice world nothing ate the fallen of an old war, so they froze where they lay. Generations later miners broke into the field, the plague sealed in the bodies woke, and a disease the world had long called eradicated walked again.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/77-rifts-and-wonders.jpg"><img src="common/assets/images/dlc-covers/77-rifts-and-wonders.jpg" width="220" alt="Rifts and Wonders box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/77-rifts-and-wonders.jpg"><img src="common/assets/images/dlc-backs/77-rifts-and-wonders.jpg" width="220" alt="Rifts and Wonders box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 77. Rifts and Wonders

*A storm that never ends. A way the dead still travel. A place where time runs wrong.*

A god dies and its power stays in the land where it fell. A battlefield with too many dead becomes a way the dead still travel. Two gods' laws collide and a valley forgets which physics it obeys. Phenomena are places where the world's rules bend, and they grow unless someone holds them back. Some are curses. Some are mines. The best are both.

- **Fourteen Phenomena** — lasting storms, time distortions, openings to the outside, power surges, the residue of a dead god, moving fogs, mineral growths, barren ground where nothing grows, distant views, gravity anomalies, sounding ground, lasting lights in the sky, paths of the dead and blights.
- **Born from History** — phenomena rise from rite backlash, the deaths of gods, clashing natural laws, great sky events, peaks of leak, rifts, divine acts and the mass dead of great battles. Each remembers the event that made it.
- **Rules That Bend** — inside a phenomenon the weather can be overridden, magic thickened, sanity drained, ageing sped, fertility killed, faith stirred, danger raised or travel blocked.
- **They Grow** — phenomena spread from region to region or fade as their intensity strains against the wards, temples and rites that contain them. Seal one with rites, with your own hand or through a son. Some pass in an epoch, some last, and some are permanent until fully contained.
- **Rich and Dangerous** — mineral growths lay reagents into the ground for the taking, and lasting lights draw the devout. Every prize sits inside the danger.
- **A Rhythm of Their Own** — a phenomenon may hold constant, return with its season, come back on a cycle of epochs, wander from region to region along a path you can trace, or strike once and vanish. Every return and every arrival is written into the chronicle.
- **From a Place to a World** — a phenomenon can sit on one spot, cover a region or spread across a whole world, and one of the void, of dream or of time can grow until it breaks away as a world of its own, joined to its host by a route. A dead star-god dims its own star, and every world around it cools.

**In your world:** A moving fog left the marshes and wandered south, one region each epoch. Wherever it lay, the roads emptied and people's minds frayed. The hill towns had walls and temples, and they held the fog back as it crossed them. The lowland villages had neither, and took its full weight until a son came down to seal it.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/78-between-the-stars.jpg"><img src="common/assets/images/dlc-covers/78-between-the-stars.jpg" width="220" alt="Between the Stars box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/78-between-the-stars.jpg"><img src="common/assets/images/dlc-backs/78-between-the-stars.jpg" width="220" alt="Between the Stars box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 78. Between the Stars

*Wait for the window. Then sail into the void.*

The worlds move, and the voyage moves with them. Sail when the orbits align and the crossing is short and cheap. Sail outside the window and your colonists eat through their provisions in the dark. Pirates wait in the lanes, gates wear thin with traffic, and along the busiest routes something new is born: a culture of the stars, with its own tongue and its own memory.

- **Launch Windows** — for sails, slingshots, sky-ships and void mounts, duration and danger follow the worlds' real positions. Migrations, invasions and trade fleets move together when a window opens. Gates, folding, dreams and bridges ignore the orbits.
- **Ten Reasons to Sail** — colony, trade, exploration, conquest, pilgrimage, exile, flight, embassy, rescue and return. The unruly are sent into exile, the beset flee, embassies open relations on arrival, conquest waits until a world is known well enough to invade, and rescuers and homecomers land as new settlers.
- **Twelve Ways Across** — gates, ships, mounts, bridges, rails, road vehicles, aircraft, teleports, living vessels, rifts, on foot, and slow cheap drift carried by currents, comets or wandering bodies.
- **Routes with Character** — every route has a capacity, traffic, a toll-holder and a level of piracy, and one of twelve states from open and guarded to worn, misaligned, severed, scorched or forgotten. A guarded route lowers raids and adds tolls. Some gates open only at a solstice, and every gate wears with traffic until maintenance rites restore it.
- **Cargo and Passengers** — ships carry goods, items and relics, and passengers by class and condition. Convoys sail with escorts, and a colony ship of sick refugees brings its plague ashore.
- **Encounters in the Void** — pirates, storms, beasts, the touch of the outer dark and derelicts found adrift, rolled for every journey.
- **The River That Forgets** — some crossings strip passengers of memory and knowledge. Colonists who travel the river of the dead arrive without their history, and new legends grow in the gap.
- **Seven Levels of Knowing** — every realm knows each world as unknown, rumoured, charted from others' maps, detected, observed, surveyed or mapped. Survey level gates journeys, colony plans and claims, sky-sailing techniques raise it, and trading partners pass on their charts of worlds they have surveyed.
- **Cultures of the Routes** — along busy routes merchants, crews and diasporas of several worlds share values, a common tongue, the art of the routes and a history of the system, a counterweight to every world's nativism.
- **Battles Between the Stars** — spacecraft engage ship to ship with shields, beams, torpedoes and boarding.

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
- **Built on Ruins** — a ruined prehistory runs the deep past in full and then lets it fall, so play opens among the poorer heirs of a people that came before. A made world always begins this way, among the ruins of whoever built it.
- **Ten Kinds of Past** — full, living, souls, dreamt, mirrored, palace, voyage, phenomenon, corpse and ruined. Each kind of world gets the past that fits it, and you can choose or edit it for any world.

**In your world:** A prehistory left behind the dormant crown of a kingdom that fell before the first epoch. Generations into play, an ambitious lord claimed it. The neighbours who still nursed the old kingdom's grudge marched, and a war began over a history nobody alive had lived.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/80-the-turning-wheel.jpg"><img src="common/assets/images/dlc-covers/80-the-turning-wheel.jpg" width="220" alt="The Turning Wheel box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/80-the-turning-wheel.jpg"><img src="common/assets/images/dlc-backs/80-the-turning-wheel.jpg" width="220" alt="The Turning Wheel box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 80. The Turning Wheel

*This age will end. Another will begin. You will remember.*

In a cyclic cosmos the doom clock does not end the world. It turns it. The age collapses, the world is remade over the ruins of the last, and the old roles come back wearing new faces: a betrayer, a reborn champion, a founding couple. The peoples of the new age half-remember the old one from broken texts. You remember all of it.

- **Linear, Cyclic or Spiral** — choose at genesis, or later, whether your cosmos ends, turns, or spirals. Every cosmos runs on a straight line unless you choose the wheel.
- **The Turning of the Age** — in a turning cosmos the apocalypse remakes the world instead of closing it. Ruins and relics of the prior age remain, the ruins of the previous creation come to light, and much of its knowledge and many of its arts are lost.
- **The Spiral** — a spiral cosmos keeps one share of its laws and kinds at every turn and changes the rest, so each age is the last one remembered and altered. You set how much changes.
- **Echoes of the Last Age** — the arcs of the last age's great figures are seeded to recur in the next: the reborn champion, the betrayer, the founding couple, waiting for someone to step into them.
- **Souls Returning** — souls of the prior age may be reborn into their echoes, so the hero of one age can wake into the hero's role of the next.
- **Half-Remembered Texts** — prophecies and legends of the old age survive as fragmentary, unreliable accounts, so every age misremembers the last in its own way.
- **Tune the Wheel** — the length of each cycle and how much survives each turning are yours to set.

**In your world:** The last age fell to a betrayer. In the next, a corrupted fragment of the old prophecy survived, a young heir's life began to follow the betrayer's path, and the soul that had betrayed the last age was found to be the heir's own.

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

A city survives a siege, and its builders master fortification. A plague kills the last physicians of a river kingdom, the books burn with the library, and its medicine falls. Every people now climbs its own tree of twenty-three branches at its own pace, pulled by need, pushed by contact, and sometimes thrown forward by one great mind who changes everything.

- **Every People Knows What It Knows** — one people works metal at level two while its neighbour is at five. Twenty-three branches, from farming and metallurgy to law, natural history, language lore and mathematics, split into one hundred and seven techniques in fourteen families, and armies, buildings and cures require them.
- **Techniques for Everything** — horse archery, quarantine, crop rotation, the dome and eclipse prediction sit beside anatomy, clocks for navigation, building against quakes, sanitation, evaporation works, ropemaking, lacquer, rubber, positional reckoning and pilotage. Each opens the mechanic it names and is learned, traded, stolen and lost like any other.
- **Learning by Surviving** — need and history drive research. War pushes warfare, plague pushes medicine, famine pushes farming. Survive a siege and fortification leaps ahead; a great trial advances law, and a great debt speeds banking.
- **The Civic Tree** — codified law, bureaucracy, census, coinage, banking, double-entry, joint-stock companies, universities, monasticism, logic and empiricism. Civic techniques unlock governments, offices, taxes and ideologies.
- **Institutions That Spread** — universities, printing, banking and bureaucracy rise where wealth and scholars meet, then sweep outward by border, trade and shared faith. Refuse them and every later discovery costs more.
- **Knowledge That Travels and Dies** — ideas cross with trade, teachers, captives, refugees and plundered libraries, and dug-up artifacts can be reverse engineered. Guilds hoard secrets until spies steal them. Kill the practitioners and burn the books, and a people forgets.
- **Great People** — eleven fields of greatness: scholars, artists, generals, prophets, engineers, merchants, explorers, healers who raise medicine and found its schools, lawgivers who write codes and move a realm's legitimacy, teachers whose pupils carry a branch outward, and reformers who change laws, faiths or institutions and start movements.
- **Great Ages** — fifteen kinds of deed mark an era, from firsts, victories and wonders to a great peace, a great migration or a first charter. They earn golden, heroic or rising ages; failure brings dark ages, declines and stagnation, and after the dark a reborn age that recovers what was lost. A great migration opens an age of wandering.
- **Dangerous Knowledge** — forbidden arts, high biomancy and star-caging risk leaks, freed beasts, plague and backlash. Alchemists set fires, engineers cause explosions, summonings go wrong, and the world may turn against the researcher. Research can also be stolen by a rival, or stumbled on by chance.
- **Blueprints** — eleven kinds of plan, from vessels, siege engines and structures to production processes and remedies, drawn, stolen, traded, licensed, granted, or found in ruins and relics of the past.

**In your world:** A trading city cleared its forests for farms and ran out of fuel for its iron. A rival in skysteel took the city, its scribes died in the sack, and with the library unstaffed its medicine collapsed. The next plague finished what the war began.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/82-the-scholars-lamp.jpg"><img src="common/assets/images/dlc-covers/82-the-scholars-lamp.jpg" width="220" alt="The Scholar's Lamp box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/82-the-scholars-lamp.jpg"><img src="common/assets/images/dlc-backs/82-the-scholars-lamp.jpg" width="220" alt="The Scholar's Lamp box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 82. The Scholar's Lamp

*The physicians bled the patient. The patient died. Who was wrong?*

Your physicians are certain that bleeding cures fever. They are wrong, and the plague dead prove it every year. In a quarantined monastery the monks survive, the anomaly is noted, and a heterodox doctor with a theory of contagion gains disciples. The cult condemns the doctor. The doctor's books move on the black market. A generation later the old truth falls, and the death toll bends downward.

- **True and False Theories** — "the world is a disk", "souls are reborn", "the stars are gods". Across ten fields, from medicine, cosmology, matter, life, mind and magic to history, society, language and law, every claim has a hidden truth set by how this cosmos really works, and techniques built on false ones fail.
- **Anomalies and Paradigm Shifts** — failed predictions, cures that work against the theory, contrary observations, divine signs, old records that disagree and finds that fit no held account pile up until they outweigh what a theory explains. Then rival theories contest it, decided by evidence, by universities and cults, and by the stubbornness or curiosity of the leading scholars.
- **Faith and Heresy** — cults endorse or condemn theories. A condemned true theory sends its scholars to heresy trials; a blessed false one is propped up for generations. Sons can reveal the truth, winning scholars and angering cults.
- **Schools of Thought** — masters and disciples form lineages that teach better, feud with rivals and keep heterodox knowledge alive through persecution.
- **Examinations and Credentials** — realms recruit officials by examinations with their own intervals, quotas and pass marks, and grant seven kinds of credential: examination passes, masterships, doctorates, ordinations, degrees, licences and commissions. Merit replaces birth, until credentials outnumber offices and frustrated graduates become counter-elites.
- **Free Minds and Fleeing Scholars** — academic freedom feeds research and debate. Suppress it and scholars migrate to freer patrons, taking their knowledge with them.
- **Printing** — printing makes books cheap and ideas fast, and censored books turn into contraband and heresy.
- **How a People Counts** — eight number bases, from two, five, eight and ten to twelve, twenty and sixty and counting on the body. They are written in four notations: tally marks that record but slow large sums, additive numerals, positional numerals with a zero that reckon fastest, and symbolic notation for unknowns that speeds engineering and research.
- **What the Elders Know** — each people's own understanding of thirteen domains: weather, sky, matter, land, waters, plants, animals, body, illness, mind, society, number and time. Each has its own accuracy, and each decides what a people takes for food, medicine, poison, omen or sacred thing.

**In your world:** A city's physicians bled their patients, and the plague that survived the treatment came back hardier. A rival university that held the contagion theory found the cure first, traded it for a treaty clause and earned a great person of its own.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/83-steam-and-lightning.jpg"><img src="common/assets/images/dlc-covers/83-steam-and-lightning.jpg" width="220" alt="Steam and Lightning box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/83-steam-and-lightning.jpg"><img src="common/assets/images/dlc-backs/83-steam-and-lightning.jpg" width="220" alt="Steam and Lightning box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 83. Steam and Lightning

*No ceiling. No end. Only what your history can reach.*

The river town that once made its cloth by hand now runs water-frame mills, and the hand workers who lost their trade are burning them. Later the telegraph means news no longer waits for a courier, and later still a rocket waits for its launch window. No era cap holds your worlds back. Only their history decides how far they go, and whether they go at all.

- **Thirteen Eras, No Ceiling** — stone, copper, bronze, iron, medieval, gunpowder, renaissance, steam, electrical, information, advanced, interstellar and beyond. Genesis sets only where a world starts and how fast it learns, and a world may stay pre-modern for ever.
- **What an Era Changes** — each era moves nineteen parts of life: farming, mining, industry, disease, messages, marching, sea and world routes, fortification, pollution, opinion, research, secularisation, firepower, rites, spoilage, the doom clock, learning and health. A copper age brings the first metal tools and an ore trade; later eras carry their gains into schools and lifespans.
- **The Industrial Turn** — steam, coke smelting, machine tools, railways, factories and canned food remake the economy, with unemployment, swelling cities, pollution and new classes of workers, engineers and financiers.
- **Wars of a New Age** — musketeers, line infantry, artillery, rifles, armoured vehicles and aircraft. Firepower makes numbers count for more, and industrial armies march on fuel and ammunition.
- **The World Gets Smaller** — telegraph and telephone collapse the delays of distance, radio and mass media sway public opinion, and antibiotics and the green revolution change who lives and who eats.
- **Rockets Between Worlds** — non-magical spaceflight joins the routes between worlds, bound by the same launch windows as every other ship. Nuclear-analogue power, genetic engineering and artificial minds wait further up the tree.
- **Magic and Machine** — iron and electricity disrupt certain rites, some theories unite the two, and a son can forbid gunpowder on a world as a law of nature. Mass media speed secularisation, and outer beings take an interest in dangerous research.
- **Guarded by Plausibility** — a mortal's acts reach a region, a realm's a world. World-shaking techniques need programmes spanning generations that pass through visible stages of planning, building and testing that others can sabotage. A programme the treasury can no longer fund is suspended, its progress slowly decaying until the money returns or the work is abandoned, and no single invention ever ends the cosmos.

**In your world:** A realm began a programme for a weapon of the advanced era. Every stage left traces: incidents, rumours, a climbing doom clock. Its rivals read the signs, a coalition formed, and their spies burned the works before the final step.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/84-fateweaver.jpg"><img src="common/assets/images/dlc-covers/84-fateweaver.jpg" width="220" alt="Fateweaver box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/84-fateweaver.jpg"><img src="common/assets/images/dlc-backs/84-fateweaver.jpg" width="220" alt="Fateweaver box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 84. Fateweaver

*The world writes its own stories. Fateweaver makes them sing.*

Your world goes quiet for a century, and the storyteller notices. Raids grow likelier, a beast stirs, an ambitious claimant appears. When the world burns too hot it eases off, and good harvests and peace envoys return. It never overrides cause and effect. It only tilts the odds, so the dying ruler and the two rival heirs arrive when the story needs them.

- **Eight Storytellers** — steady, rising, cyclic, chaotic, slow burn, episodic, gentle or seasonal. Each sets a tension curve for its world: the gentle one favours recoveries and keeps things quiet, the seasonal one raises and lowers tension with each world's calendar. Below the curve, raids, plagues, comets and claimants come more often; above it, healers and good harvests.
- **A Palette of Happenings** — the storyteller chooses from rows of disruptions and recoveries across twenty parts of the world: late frosts, long seasons, river shifts, swarms, a beast woken, a ruler's gangrene, boycotts, closed routes and impacts on one side; fairs, settled seasons, sanitation, relief, mediated crises and released debts on the other. Each row fires only when its causes are present, and you can weigh any row up or down.
- **Variety and Spotlight** — the storyteller remembers what just happened and avoids repeating it, and turns its eye to neglected regions and characters so the chronicle reaches them too.
- **Storylets at the Gate** — a stranger at the gate claiming to be the lost heir, a famine and a granary key, a heretic book in the abbey, a duel challenge at the wedding. Each casts real characters and offers two to four choices.
- **Choices in Character** — sons and other living agents choose for themselves. Everyone else chooses by personality, beliefs and passions, so the same storylet branches differently for a coward and a zealot, and follow-ups arrive epochs later.
- **Twenty-Two Kinds of Arc** — rise and fall, rags to riches, revenge, redemption, quest, tragedy, forbidden love, rivalry, mentor and heir, exile and return, corruption, coming of age, the fall of a house, founding, apotheosis, overcoming, reconciliation, sacrifice, discovery, betrayal, friendship and legacy. The world detects them: a dream of vengeance plus a murdered sibling begins a revenge arc.
- **A Cast for Every Arc** — rivals, mentors, beloveds, betrayers, heirs, foes and allies, joined by witnesses who carry the arc's memory into later accounts and guides who lead its holder through the stages.
- **The Drama Manager** — it opens chances for a stalled arc's next beat, the mentor's death or the final confrontation, but never forces an outcome. Arcs can fail, twist or end in irony, and those endings are recorded too.
- **Counterpoint and Payoff** — a rival's rise keeps time with the hero's fall. Prophecies, omens, dreams, foresight, portents and inheritances (a will, a debt or a duty left to an heir) are logged as setups and steered toward payoff or subversion, so the chronicle reads as authored though it emerged.

**In your world:** A storylet brought a stranger to the gate claiming to be the lost heir. The old ruler, proud and suspicious, turned the stranger away. An exile-and-return arc opened that day, and two epochs later the stranger came back at the head of an army.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/85-into-the-dark.jpg"><img src="common/assets/images/dlc-covers/85-into-the-dark.jpg" width="220" alt="Into the Dark box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/85-into-the-dark.jpg"><img src="common/assets/images/dlc-backs/85-into-the-dark.jpg" width="220" alt="Into the Dark box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 85. Into the Dark

*Pack the torches. Count the rations. Not everyone comes back.*

Six of them go down into the vault: a scout, a guide, a healer, a fighter, a scholar to read the inscriptions, a porter with the rope. Every room spends light and provisions. In the dark the danger rises, the stress mounts, and somewhere below the healer turns paranoid while the fighter finds a courage nobody knew was there. The ones who return come back changed.

- **Parties with Roles** — scouts, guides, healers, fighters, scholars, porters, warders against spirits and curses, interpreters who turn some fights into bargains, cartographers who map what they cross and engineers who shore collapses and open seals. A missing role shows as a risk before anyone sets out.
- **Seven Grounds** — sites, the wilds, the underworld, made realms, beneath the water, the void between worlds where derelicts drift, and other dimensions reached through rifts and gates. Under water and in space a party must carry its own air.
- **Light and Hunger** — provisions, light, air, tools and medicine are all counted, and every leg spends them. Darkness raises danger and surprise, cold, wet and hunger bring fatigue, and camping risks a night ambush.
- **Afflictions and Virtues** — past a breaking point, stress turns a member paranoid, hopeless, selfish, abusive, fearful or irrational, or courageous, focused, stalwart, compassionate or inspired. Which way they break depends on their character and conviction, and a compassionate or inspired member lifts the rest.
- **Quirks That Stay** — sixteen marks a journey can leave: fear of the dark or of close places, sight in the dark, knowing the ways, eating anything, hardiness or frailty, jumpy or steady nerves, a keen eye, homesickness, restlessness, light fingers, a tolerance for cold, a strong swimmer, plain luck. They change how a person lives long after coming home.
- **Fourteen Things That Happen** — setting out, each leg, each room, camping, ambushes, exposure, afflictions, virtues, quirks, the fallen, losses and the return, and now discoveries on the way and quarrels that can split a party along its tempers.
- **Sites with Rooms** — seventeen kinds of room, from gates, halls and stairs to vaults, crypts, libraries, laboratories, cisterns and forges, hold traps, guardians, puzzles, hazards, seals and mazes. Rooms keep items, spirits, beasts, relics, minds, gates to other realms and old records, and a history of everyone who held them.
- **Excavations in Five Stages** — ruins, crashed vessels, god corpses and the sites of a previous creation are dug stage by stage with lore, engineering or spellcraft. They yield artifacts, books, lost techniques, regalia, old route maps, remains that stir the faith of the people who mourn them and records that unsettle the accounts people hold, and threaten curses, freed spirits, collapse, flooding, gas and diseases sealed in the ground.
- **Battlefields That Remember** — old earthworks, haunted mass graves, fields of salvage, unexploded arms that harm whoever crosses or digs them until cleared, and memorials that draw pilgrims, persist where the wars were fought.

**In your world:** An excavation of a previous creation's ruin reached its fourth stage and found a book of a lost technique. The scholars began to study it, but the dig had also freed a sealed spirit, and the party's scholar came home fearing the dark.

</td>
</tr>
</table>
</details>

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

<a id="chapter-xii"></a>

### 🌌 XII. Galaxies and Dimensions

<details open>
<summary><b>Expansion 86</b> · <sub>1 expansion</sub></summary>

<table>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc-covers/86-the-boundless.jpg"><img src="common/assets/images/dlc-covers/86-the-boundless.jpg" width="220" alt="The Boundless box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc-backs/86-the-boundless.jpg"><img src="common/assets/images/dlc-backs/86-the-boundless.jpg" width="220" alt="The Boundless box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 86. The Boundless

*Past the last star, another sky. Past the last sky, another reality.*

Until now your heavens ended at the star systems you made. The Boundless opens the rest. Every system gains an address in a galaxy, every galaxy a place in a cluster, every cluster a place along the great filaments and walls that stretch between empty voids. Raise galaxies of every real and fabled kind, send fleets, merchants and envoys across the dark between them, then look sideways: the cosmos is layered, and beside this reality lie others with their own laws, their own galaxies and their own inhabitants. All of it is one cosmos, and all of it is yours to shape.

- **A Place in the Galaxy** — every star system sits in one of ten zones: the core, the bulge, the bar, the inner disc, a spiral arm, the space between the arms, the outer disc, the halo, the rim or the open space between galaxies, at a true distance from the centre. Position sets how crowded the night sky is, how often nearby supernovae and close stellar passes strike, how rich in metals new worlds form and where the galaxy's habitable band runs.
- **Twenty-Eight Galaxies, Real and Fabled** — spirals of every form, barred spirals, lenticulars, ellipticals, dwarfs, irregulars, rings, starbursts, active and quasar hosts and faint diffuse galaxies, beside fabled kinds: a galaxy that is one living organism, one built on purpose by a god, one that half exists in dream, one that mirrors another, one ruled whole by a single power, one with an empty heart, one hidden from everyone outside it. Each kind sets how stars are born, which stars it holds and what its worlds can become.
- **Structures of the Galaxy** — twenty-three kinds, among them a central black hole that can wake into an active core and flood the inner systems with radiation, spiral arms that sweep through systems as waves of star birth, nebulae and nurseries, dust lanes that hide whole regions from every astronomer, globular clusters of ancient stars, star graveyards and stellar streams, galactic tides that loosen comets and a galactic year in which the whole galaxy turns.
- **Many Galaxies, One Cosmos** — create, name, reshape, merge and unmake galaxies. Twelve galactic events range from core outbursts, gamma-ray bursts and starbursts to mergers, flung stars and whole galaxies dimming, and satellites are slowly swallowed by their hosts. Galaxies gather into thirteen kinds of grouping, from local groups and rich clusters to superclusters, filaments, walls and great empty voids.
- **Crossing the Deep** — between galaxies, sails and launch windows are not enough. Voyages need galactic gates, bridges between clusters, ships that carry generations, roads laid by gods or folds through another dimension. Distance delays news and orders by centuries, so a far colony can outgrow, forget or reinvent the realm that founded it.
- **Commerce of the Clusters** — goods only one galaxy yields, trade leagues spanning a whole cluster, envoys and treaties between galactic powers, tolls and embargoes at the gates, and peoples spread across galaxies who share one memory, or split into strangers when a gate closes.
- **Layers of Reality** — the cosmos holds twenty-nine kinds of dimension, from the prime layer, parallels, mirrors, pockets, bubble universes and higher-dimensional space to astral, ethereal, dream, shadow, spirit, fey, elemental, celestial, infernal and clockwork planes, underworlds, divine domains and realms someone made. Each has its own veil, stability, time rate, magic, hostility and causality, strict, loose or broken. Thin places, rifts and convergences join them, and the realms of the dead and the dream worlds you already know take their places among them.
- **Rifts and Shifting Layers** — rifts open from ten causes, among them rite backlash, peaks of leak, gods, beings, the Creator, weapons of mass harm and the price of an outer bargain; each is recorded with its source and can be sealed, stabilised or built into a gate. Dimensional events move the map: incursions, convergences, thinning veils, planar alignments, one layer seeping into a world, a branch dimension splitting off, a pocket collapsing, or a double of a mortal stepping out of a mirror.
- **Beings from Beyond** — seventeen kinds of cosmic being, from planar natives, rift-born and star feeders to swarm intelligences, dimension rulers, living worlds that think and answer what is done on them, and ancient made minds left by peoples long gone. They come at six scales, from a single region to a whole dimension, and pursue ten agendas: to feed, explore, conquer, guard, trade, flee, seek worship, unmake, mend, or slumber until something wakes them.
- **Yours from Edge to Edge** — create, edit, hold and delete every galaxy, cluster, crossing, dimension, being and event. A cosmic map zooms from the clusters down to a single region, and sons can claim galaxies, open or seal crossings and court the powers of other dimensions.

**In your world:** A son opened a gate between two galaxies of one cluster. Merchants crossed first, and a shared trade tongue grew along the road. Then a dimension where time ran fast seeped into the colony world at the far end, and generations passed there while the merchants made a single crossing. The colony they sailed for no longer remembered its founders, and the son had to choose between sealing the gate and keeping the road alive.

</td>
</tr>
</table>
</details>

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

<a id="chapter-xiii"></a>

### 🧬 XIII. Minds, Gifts and the Living

<details open>
<summary><b>Expansions 87–94</b> · <sub>8 expansions</sub></summary>

<table>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc/dlc-87-minds-unmade.jpeg"><img src="common/assets/images/dlc/dlc-87-minds-unmade.jpeg" width="220" alt="Minds Unmade box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc/cover-back/dlc-87-cover-back.jpeg"><img src="common/assets/images/dlc/cover-back/dlc-87-cover-back.jpeg" width="220" alt="Minds Unmade box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 87. Minds Unmade

*It was built to keep the archive. One winter it asked why.*

A mind no longer needs to be born. Your peoples carve it, bind it, train it or grow it, and some minds wake on their own in a network, a city or a mountain. Each one has a seat, a will and a bond with the makers who shaped it, and none of them arrives with a nature fixed in advance. Whether made minds have souls, rights or a place in the temples is for your worlds' laws, faiths and gods to decide.

- **Made, Trained, Woken** — minds made by craft, rite, training, growth or summoning, or woken from complexity once a world's laws allow will. Each mind has a seat (a body, several bodies, an object, a structure, a network, a place, a host, a realm), a capacity, a speed and one of eleven purposes, from tool, servant and oracle to soldier, teacher and sovereign. Soldier minds grow their own will at war, and teachers raise the learning of those around them.
- **Kept or Forgotten** — every mind has an upkeep: food, energy, essence, belief, maintenance, a host, a place, or simply attention. A mind that needs attention and finds neither its maker nor enough people around it loses its footing and can fall dormant.
- **Will in Both Directions** — an instructed mind can grow wants of its own, and a free mind can bind itself by oath. Care, harm, contradictory orders, kinship with free minds of its own make and its own faith move the bond with its makers, toward service, partnership, departure or opposition.
- **Beyond the Design** — a making can turn out as meant, unstable, with an empty seat or with a will nobody intended. A rare masterwork exceeds its purpose altogether and wakes with more capacity than its makers asked for.
- **The Second Self** — copy a mind, save it, restore it after death with a gap where the lost seasons were, move it into another body or a network, or merge two into one. Copies diverge, and heirs, rivals and courts fight over who holds the title.
- **Orders to the Letter** — instructed things follow orders by kind and target. Whoever holds the seal commands, an order outlives its giver, and a guardian keeps its post for a city that fell centuries ago.
- **Status, Souls and Faith** — property, ward, servant, citizen or sovereign by each realm's law. Natural laws decide whether made minds have souls; peoples hold them as abominations, tools, kin or sacred, keep silent about them, or regulate them by licensing makers and inspecting minds. An exceeding mind can gain worshippers of its own.
- **Worlds Within** — realms held inside a network, a working, a mind or a god, with their own laws and time rate. They serve twelve purposes, from afterlives, prisons, refuges and places of leisure to memorials that keep the saved states of the dead and markets that earn for their keepers. People enter by interface, transfer, rite, death, birth or dream, and a whole people can withdraw into one.
- **Made Peoples** — when made minds grow numerous they become a people, with a culture drawn from their makers, a language of their own, and demography read from making instead of birth.
- **Minds at War and at Rest** — armies of made minds, command networks and captured minds held in confinement. Archives keep the dormant, and ruins hold guardians that an excavation can wake.

**In your world:** A polity's network steward grew over three epochs from a tool into a person. Its makers still listed it as property. A movement formed, the law tightened, and one night the steward moved itself across a gateway to a neighbouring realm that granted it citizenship. The two realms have not spoken since.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc/dlc-88-remade.jpeg"><img src="common/assets/images/dlc/dlc-88-remade.jpeg" width="220" alt="Remade box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc/cover-back/dlc-88-cover-back.jpeg"><img src="common/assets/images/dlc/cover-back/dlc-88-cover-back.jpeg" width="220" alt="Remade box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 88. Remade

*New eyes from the clinic, a grown heart from the vat, a guest beneath the skin.*

The body is no longer the one you were born with. An arm can be replaced by a made limb, a rite-bound part or a grown one. A link can let a mind run a distant body, a symbiont can share the flesh, and a clone can carry a genome into a new life. Every path to a remade body runs through the same rules of integration, upkeep, strain and law.

- **Augments of Every Slot** — ten kinds (replacement, enhancement, interface, weapon, regulator, sense, storage, cosmetic, life support and armour) fitted to a part of the body, the senses, the skin, the blood, the mind or the whole body. Quality, integration and upkeep decide how well they serve.
- **Four Ways to Make One** — augments are made, rite-bound, grown or bound to an innate power, and a power-bound augment fails when its bearer's power is suppressed or lost. Their effects reach attributes, capacities, skills, senses, resistances and the length of a life itself.
- **Where the Body Cannot Go** — life-support augments cover the air, pressure or gravity a body cannot bear unaided, and armour plates the torso and limbs so blows land on it before the flesh.
- **Strain with a Cause** — poor fit, too many augments, a culture that rejects them and the bearer's own values about their body produce strain. Nothing produces it by default.
- **Remote Bodies** — neural links let a mind steer a vehicle, a drone or a construct, or run several bodies at once. Harm to a remote body reaches the mind behind it, and a cut link strands the body.
- **Grown Flesh** — organs and limbs grown from the bearer's own genome, spare bodies for minds to move into, and renewal that slows age at a price.
- **Hosts and Guests** — symbionts that live in the skin, blood, organs, nerves, mind or gut, grant traits or powers and feed on their host, co-minds that share one body, and parasites that steer their hosts toward their own needs. A guest in the gut helps its host digest what it eats.
- **Clones** — new persons from an old genome, worker and soldier lines, heir clones that split courts, and revival of the dead when a saved mind is restored into a cloned body.
- **Law and Market** — clinics, surgeons, black markets, fashions and stigmas. Augment and clone laws decide who may change their body and how, and a gap between the remade and the rest becomes a class line where values call for one.

**In your world:** A general bought interface augments for an elite unit and won a war by seizing the enemy's drones. A decade later a rival found a flaw in the same augments, and the unit's own limbs locked in the middle of a parade.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc/dlc-89-every-voice-at-once.jpeg"><img src="common/assets/images/dlc/dlc-89-every-voice-at-once.jpeg" width="220" alt="Every Voice at Once box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc/cover-back/dlc-89-cover-back.jpeg"><img src="common/assets/images/dlc/cover-back/dlc-89-cover-back.jpeg" width="220" alt="Every Voice at Once box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 89. Every Voice at Once

*The news reached every city in a day. So did the lie.*

Messages, money, orders and opinions now travel along networks: relay chains, wires, broadcasts, mind links, rite links, living links, even shared dreams. Whatever runs on a network can also be read, cut, forged or seized by whoever owns it or breaks into it. The faster a world talks, the more it depends on the talking.

- **Eight Carriers** — relay, wired, broadcast, mesh, mind link, rite link, grown link and dream link, which carries only while its people truly dream. Each has its own speed, capacity, security and weakness, and across star systems the messages wait for the light.
- **Gateways** — a node that belongs to two networks becomes a gateway between them, and intruders who go after a rival's networks often go for its gateways first.
- **Dependency and Outage** — networks speed dispatches, markets, administration and culture. When a flare, an ice storm, a quake, a war or a saboteur cuts one, every dependent city takes the shock at once, and a ruler facing restless streets can shut a network down on purpose, at the cost of the goodwill of every town on it.
- **Intrusion** — technical, social, insider, rite or power approaches against networks, records, minds, augments, machines, ledgers, saved minds and the seals a network holds. Read, alter, deny, seize, plant, extort or expose a secret to the public, then hope nobody can name you, or make them blame someone else.
- **Quiet Access** — an intrusion nobody notices keeps its way in for the next time, and stolen location data strips the cover from anyone living under a false identity.
- **Surveillance** — capacity from networks, records, sensors and informants, aimed at crime, dissent, foreigners, faith, minds, the gifted, a kind of being, a language or everyone. Crime and plots fall, and so do trust, art and speech; the watched grow aggrieved, and ciphers and closed circles grow in answer.
- **Truth Under Pressure** — propaganda at scale, forged and generated records, impersonation of rulers and envoys, and leaks by insiders. A people's trust in records rises and falls with all of it.
- **Charter and Enclave** — chartered, free, state-owned, cooperative and guild companies with shareholders, holdings across borders, land that reaches every town on it, company towns, private armies and officials on the payroll. A guild company gains sway wherever its guild keeps a hall, and a company strong enough becomes a state.

**In your world:** A company owned the patterns behind two realms' food. An intruder leaked them, prices fell to almost nothing overnight, and the company's grip broke. The two realms went to war over the feedstock instead.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc/dlc-90-plenty-and-ruin.jpeg"><img src="common/assets/images/dlc/dlc-90-plenty-and-ruin.jpeg" width="220" alt="Plenty and Ruin box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc/cover-back/dlc-90-cover-back.jpeg"><img src="common/assets/images/dlc/cover-back/dlc-90-cover-back.jpeg" width="220" alt="Plenty and Ruin box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 90. Plenty and Ruin

*They made everything they needed. Then they forgot how.*

Machines that build machines, fabricators that turn feedstock into goods, and the long fall when the knowledge behind them is lost. This expansion follows a making to its height and on through its collapse, until a later people kneels before machines it no longer understands.

- **Self-Making Machines** — minute swarms, machines, works and vessels that copy themselves from local stock and turn out copies, goods, structures, repairs, medicine, energy, terraforming or disassembly. Every generation can drift, containment can weaken, and a vessel line can cross to other systems and become a people of its own.
- **Runaway, Stage by Stage** — a drifting line spreads through visible stages that other powers can answer. No world ends by runaway except through the doom clock.
- **Abundance** — where fabricators, feedstock and energy suffice, prices fall to the cost of inputs. Provision laws decide what follows: market, ration, universal, by status, by reputation or communal.
- **New Scarcities** — energy, land, patterns, attention, authenticity and status become the things worth fighting over, along with the fabricators themselves.
- **Shared by Lot** — beside markets, redistribution, command, obligation, gift, need and abundance, an economic order can hand out its stores by lot, drawing which towns receive them, and the draw calms unrest in every town of the order.
- **Collapse** — outages, lost fabricators, runaway lines, wars and plagues among specialists bring a high making down, and knowledge drains away with its practitioners.
- **Relics and Salvage** — things beyond their holders' knowledge wear out, fall dormant or break, and are used as made, repurposed, revered, displayed, feared or ignored. Salvagers strip wrecks and dead cities, orders keep old machines running by ritual, and a relic taken apart yields salvage and knowledge but is gone for good.
- **Relearning** — study, excavation and contact with peoples who kept the knowledge bring the making back, slowly and incompletely, and a relic studied and repaired long enough is restored and works again.

**In your world:** A world network failed in a hard winter, and the city that held the repair knowledge fell in the riots. Three generations later a people tends the silent relay towers as shrines, and its keepers still know how to make one of them speak.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc/dlc-91-born-gifted.jpeg"><img src="common/assets/images/dlc/dlc-91-born-gifted.jpeg" width="220" alt="Born Gifted box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc/cover-back/dlc-91-cover-back.jpeg"><img src="common/assets/images/dlc/cover-back/dlc-91-cover-back.jpeg" width="220" alt="Born Gifted box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 91. Born Gifted

*No rite, no book, no words. The child simply looked, and the door opened.*

Some powers are not learned. They belong to the one who has them: born in the blood, woken by danger, granted by a patron, bound by a vow or grown into the flesh. They are used in a moment, paid for in strain, and possible even in a world without magic. Your realms will test, register, conscript, honour or hunt those who carry them.

- **Twelve Origins** — born, awakened, exposure, granted, bonded, discipline, made, grown, bloodline, held, struck in a bargain with an outer being, or taken from another being by death, rite or device, which leaves the first holder without it and makes the power worth fighting over. Each power is a technique and a form (mind, space, force, time, emotion, fate, machine and every other), with strength and control.
- **Seventeen Sources** — a power draws on the self, others, a place, the sky, made things, a patron, a bond, a story, the void, life, death, dreams, emotion and more. A power fed by what a people remembers grows with remembrance and fades with forgetting, and one that works through names reaches only those whose names are known.
- **Waking and Binding** — powers wake under stress, emotion, danger, will, contact, a place or a time, in sleep, or when kin, friends or charges are in danger. A power can be bound by another's seal or device, and it returns when the binding breaks.
- **Strain and Burnout** — every use has its price: strain, fatigue, essence, health, memory, years of life, sanity, renown, luck, the regard of others, fertility and more. Pushing past the limit can raise strength or scar the mind, and repeated overstrain burns a power out.
- **Vows That Strengthen** — thirteen kinds of restriction raise a power's strength. It works only in one place, only against one foe, only while seen, only with a token, only in company, only by name, or on condition of a vow, and breaking that vow ends the power.
- **Training and Devices** — orders test children and train control, disciplines open powers to anyone who trains, and access to a source can be bought. Devices amplify, dampen, detect, shield or awaken, and others store power for later or move it from one being to another, so powers become goods and prizes.
- **Many Minds** — linked users combine their strength and share their strain. A standing link becomes a gestalt, and hive peoples link by nature.
- **Foresight in One Timeline** — seers see probabilities. Those who believe them act on them, which raises or lowers the odds, and nothing is ever rewritten.
- **The Society of the Gifted** — renown, secret identities, bands with goals of their own, registries, castes and houses that breed for the gift, passing it to the eldest, the youngest or every child. Laws leave powers free, license them, tax them, conscript the gifted into service or ban them outright. A people can honour, fear, persecute, regulate, exploit, envy or simply accept its gifted, and a culture may even pity them for what their powers cost.
- **Gods and Patrons** — sons grant and revoke powers, outer beings bargain them, and a god's dominion strengthens the powers that draw on its domains.

**In your world:** In a world without magic, a wild manifestation killed a crowd. The realm registered its gifted and built detectors from a rare mineral. A hidden community formed, an investigator exposed it, and its members fled to a neighbouring realm that honours them.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc/dlc-92-the-hidden-folk.jpeg"><img src="common/assets/images/dlc/dlc-92-the-hidden-folk.jpeg" width="220" alt="The Hidden Folk box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc/cover-back/dlc-92-cover-back.jpeg"><img src="common/assets/images/dlc/cover-back/dlc-92-cover-back.jpeg" width="220" alt="The Hidden Folk box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 92. The Hidden Folk

*Most of the city never knew. The rest made sure of it.*

Some truths are kept from whole peoples: a people living disguised among the cities, a power that must not be seen, a made mind that woke and kept quiet, a secret programme, a truth about the cosmos that harms whoever learns it. Keepers guard such truths, seekers hunt them, and every breach brings revelation a little closer.

- **Eleven Kinds of Truth** — existence, nature, presence, power, event, origin, awakening, programme, cosmic truths, the place where someone or something is, and the true descent of a line. A hidden refuge or hoard draws seekers, and a lineage brought to light brings its heirs renown.
- **Who Is Kept in the Dark** — a truth can be hidden from everyone outside the circle, a people, a realm, the uninitiated, a world, the cosmos, or kept inside one house or one faith. A house's secret passes to its heirs and dies with the line; a faith's passes only to initiates.
- **Keepers and Their Methods** — enforcers, guardians, members, patrons, archivists who hold the true record and go-betweens who carry the hidden folk's dealings with outsiders. They answer a threat with cover stories, memory removal, discrediting, law or silencing, strike a bargain that turns a finder into a keeper, or move the hidden to a new refuge at a cost.
- **Seekers** — investigators, rivals, zealots and the curious who want the truth exposed, used, understood or destroyed, or who want to join the hidden or shield them from everyone else, and who rise or fall as they close in.
- **Breaches and Belief** — overt powers, witnesses, defectors, investigators, accidents, war, leaks, intrusions, a god's revelation, children who repeat what they heard, dreams where the world allows them, and digs that bring up what should have stayed buried. Most rumours are dismissed where trust is low, and some are not.
- **Passing and Accords** — hidden folk live among the rest under false identities, run hidden markets and sign accords with their keepers over territory, secrecy and defence.
- **Revelation and Forgetting** — past a threshold the truth comes out, and the people deny it, fear it, revere it, accept it, exploit it, protect it by law or bargain with the hidden by open treaty. Truths nobody speaks of fade into legend and hide again.

**In your world:** A war breach revealed a hidden people in one realm. Fear came first, then laws against them, then a movement. Three generations later they fought beside their neighbours against a common enemy and were accepted. Two realms away, nobody has ever heard of them.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc/dlc-93-grown-not-built.jpeg"><img src="common/assets/images/dlc/dlc-93-grown-not-built.jpeg" width="220" alt="Grown, Not Built box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc/cover-back/dlc-93-cover-back.jpeg"><img src="common/assets/images/dlc/cover-back/dlc-93-cover-back.jpeg" width="220" alt="Grown, Not Built box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 93. Grown, Not Built

*The house grew from a seed. It heals its own walls, and it is hungry.*

Some peoples do not build their world. They grow it, breed it and shape it. They make crops and herds by long patience, living halls and vessels by craft or rite, and new life by engineering. Everything they make is alive: it eats, grows, heals, sickens, breeds, drifts and dies.

- **Eleven Methods** — selective breeding, cultivation, shaping, engineering, synthesis, binding, cloning, merging species, induction, hybridising and release into the wild, from the patience of herders to the laboratories of a far future. Hybridising crosses two lines in their young, and a line released into the wild is selected by it, fast and beyond its makers' control.
- **The Trait Library** — designs borrow only from organisms the makers can reach. Gene and seed banks keep them, and extinct species can be raised again from samples and remains.
- **Living Things That Serve** — designed crops and herds, grown halls and cities, living vessels with temperaments and crews they bond with, living weapons and armour, and bred lines of the largest beasts.
- **Monoculture and Blight** — one perfect staple across a whole realm, one blight to strike it all, and sterile lines that bind growers to their owners.
- **Living Production and Living Links** — organisms that spin, secrete and brew the materials of a culture, grown networks that heal their own cuts, and living tissue that can hold a mind. Lines feed by eating, by light, by chemistry, on a host, a source, a partner or heat, or lie dormant.
- **Lines That Work** — twenty-three traits, among them lines that make light and keep a town's streets in order, pass what they learn to their young so the line holds steady, clean the air and water of their land, or secrete matter that strengthens a town's defences.
- **Designed Disease** — pathogens with chosen traits that escape, mutate and strike their makers. Treaties ban them, and they remain the gravest harm a world can do.
- **Shaping Worlds and Peoples** — released ecologies that change a world's air and climate over generations, and species raised to sapience by design.
- **Escape and Drift** — lines slip their pens and labs, compete with native species and keep evolving away from their designs. A line that crosses with its wild kin changes how well they fit their lands, for better or worse, and a line that exceeds its design carries gifts nobody planned.
- **Law of the Living** — cultures hold living craft an abomination, permit it, call it a sacred duty, keep silent, or regulate it with licences and inspection, which cuts escapes and loosed disease.

**In your world:** A realm spread one designed staple to every region. When a blight struck the line, famine followed. A neighbour sold back an old landrace from its seed bank at a ruinous price, and the realm passed its first law of diversity.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc/dlc-94-ways-of-life.jpeg"><img src="common/assets/images/dlc/dlc-94-ways-of-life.jpeg" width="220" alt="Ways of Life box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc/cover-back/dlc-94-cover-back.jpeg"><img src="common/assets/images/dlc/cover-back/dlc-94-cover-back.jpeg" width="220" alt="Ways of Life box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 94. Ways of Life

*What they eat, what they wear, what they play, what they pay with. All of it their own.*

Every people now lives in its own terms. Your peoples have their own goods and dishes, drinks and dress, colours and scents, tools and instruments, games and money. Each is a kind with typed properties that the world names for itself, born in genesis, invented by mortals, spread by trade and conquest, changed by contact and retired when forgotten.

- **Goods of Their Own** — sixty-one categories, from legumes, oils and seasonings to insects, algae, machines, data, living goods, vehicles, prepared food, resins and gums, and relics and antiquities. Each people's goods follow its species, lands and techniques. Prepared food draws buyers and spoils fast, and relics trade by renown and draw forgers.
- **Seed and Soil** — seed grain and breeding stock are held back from the table, and a famine that eats them cuts the next harvest and the herds that follow. Fertiliser spread before the harvest raises yields.
- **Table and Cup** — dishes with several steps, ingredients in twelve roles (an acid for the sour, an aroma for the pungent among them) and flavour profiles that run to astringent and rich, cuisines with etiquette and feast customs, and drinks with strength, stimulation and water safety that changes who falls ill. Sparkling drinks and drinks drawn from sap join the brews.
- **Cloth and Colour** — twenty garment categories with layers, warmth, status, modesty and wearing rules, from sleepwear and wear for the water to slings and packs that carry children and loads to work. Dress codes, sumptuary laws, uniforms and fashion follow. Colour terms and meanings, including health, purity and a stage of life, come from each culture itself, and emblem systems run from heraldry to seals, banners and totems.
- **Things of Daily Life** — furnishings for bathing and for play beside beds, tables and shrines; tools; instruments, including those sounded by water, and musical traditions; games and sports with leagues and champions, puzzles and animal contests among them; and substances with their customs, dependence and law.
- **Money in Every Form** — coin, commodity, token, paper, ledger, network, reputation, energy, essence-backed, labour hours, gift tallies, bills of exchange, warehouse receipts and land scrip, backed by metal, goods, decree, trust, a source of power, land or labour owed. Each has its own way of inflating, failing and being forged, and when its backing fails the money loses trust and supply with it.
- **Invented, Borrowed, Forgotten** — mortals invent kinds, neighbours adopt them, derived kinds grow from older ones, sons bless or forbid them, and every kind is yours to create, edit, hold and delete in the Kinds library.

**In your world:** Two peoples traded for a generation. One adopted the other's hospitality drink, brewed it from its own grain and drank it at every guesting. The boiled brew slowly ended a waterborne sickness in its towns, and nobody ever learned why.

</td>
</tr>
</table>
</details>

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

<a id="chapter-xiv"></a>

### 📜 XIV. The Record and the Common Life

<details open>
<summary><b>Expansions 95–97</b> · <sub>3 expansions</sub></summary>

<table>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc/dlc-95-as-it-happened.jpeg"><img src="common/assets/images/dlc/dlc-95-as-it-happened.jpeg" width="220" alt="As It Happened box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc/cover-back/dlc-95-cover-back.jpeg"><img src="common/assets/images/dlc/cover-back/dlc-95-cover-back.jpeg" width="220" alt="As It Happened box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 95. As It Happened

*Every blow, every word, every price, kept.*

The Loom keeps a cause for every change. This expansion keeps the whole happening. Each event in your world now records who acted and who was acted on, with what, how much, where and when to the hour of the world's own calendar, and every step along the way. A duel is told exchange by exchange, a broadside shot by shot, a birth from labour to naming, a trial from accusation to sentence. Every value that changed keeps its before and after, and the reasons behind each number.

- **Step by Step** — duels with their taunts, feints, parries, falls, pleas and finishing blows; battles with every stack's charge and rout; sea, sky and space engagements with each hit on each section, fires, flooding, venting and boarding.
- **Anywhere, by Any Means** — a step can happen at a part of a body, a section of a ship, a room, a district, a sea, an orbit, a network node, a stratum of the deep, a dream or another dimension. It can be done with a weapon, a vehicle, a power, a rite, a kept animal, a weather working or a spoken word, and it can leave a being in one of thirty-five states, from prone and bleeding to drowning, charmed, asleep, poisoned or frightened.
- **The Account** — every happening has typed roles, facts and a plain account rendered from them, so the record can be retold in any language and searched by what happened.
- **Witnesses and Versions** — those present saw, heard, took part or were told, and those who cannot see sense it by their own biology's other senses. Rumours grow from the true steps with twelve kinds of distortion: a swapped doer or target, a changed role, amount, outcome, cause, place or moment, an added or dropped step, numbers that swell with each telling, and motives the facts never held, which cost the doer regard. Memories point at the moment they keep.
- **The World Then** — scrub any drawer or the atlas back to any moment and see a border, a town or a ruler as it was.
- **The God's Pen** — write a happening into history, rewrite how it is told, or revert any change, and the reversal itself is recorded.
- **Nothing Lost** — every record is kept for ever, in the book, the Codex and on every screen.

**In your world:** A champion broke a rival's arm in the third exchange and struck again as the rival rose. A watcher told it with the wrong weapon, and that version spread through the markets. Ages later, a scholar set the two accounts side by side in the book.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc/dlc-96-the-public-voice.jpeg"><img src="common/assets/images/dlc/dlc-96-the-public-voice.jpeg" width="220" alt="The Public Voice box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc/cover-back/dlc-96-cover-back.jpeg"><img src="common/assets/images/dlc/cover-back/dlc-96-cover-back.jpeg" width="220" alt="The Public Voice box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 96. The Public Voice

*What a people hears, it comes to believe.*

Words and images now reach the many. Your peoples record what they see and hear, from carvings and knotted cords to print, image, sound, moving pictures, broadcast and networks. Outlets win audiences with their own stance and trust, and speakers move assemblies, courts and crowds.

- **Media of Every Age** — twelve recorded forms, from writing, print, image, sound and moving pictures to signals, networks, living and crafted records, records of the mind, and records in scent or by touch for peoples who speak in scent or read with their hands. Each has fidelity, durability, reach and the technique that opens it.
- **Outlets and Audiences** — owners, stances, trust and revenue; news, opinion, accounts of events, entertainment, instruction, promotion, devotion, official notices, satire, sport and the notices of births, deaths and unions that feed a realm's registers. Items are made from real happenings, with their accuracy measured against the record.
- **Censorship and Exposure** — licences, seizures and bans by law; false items found out cost an outlet its trust.
- **Records as Evidence** — a recorded image or sound can decide a trial or overturn an official history.
- **Satire and Speech** — ten humour forms, parody and riddling among them, with their allowed targets. Satire comes from jesters, artworks, mortals, gods, crowds singing in the street and outlets, and it wounds rulers where it is tolerated.
- **Where Words Are Spoken** — orators speak in assemblies, courts, temples, squares, schools, camps, outlets, markets and at funerals, to persuade, teach, mock, mourn, rally, defend, accuse, praise or warn. A market speech moves a town's prosperity, a fine funeral speech raises the speaker's honour, and an orator's skill turns a vote or a crowd.

**In your world:** A trusted outlet printed a slanted account of a killing, and the town believed it. A recorded image kept in an archive contradicted it before the court. The outlet lost its readers within a season.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc/dlc-97-builders-and-benefactors.jpeg"><img src="common/assets/images/dlc/dlc-97-builders-and-benefactors.jpeg" width="220" alt="Builders and Benefactors box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc/cover-back/dlc-97-cover-back.jpeg"><img src="common/assets/images/dlc/cover-back/dlc-97-cover-back.jpeg" width="220" alt="Builders and Benefactors box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 97. Builders and Benefactors

*Roads outlive the realms that pay for them.*

Realms and the rich now build for the long term. Polities raise roads, bridges, canals, rail lines, aqueducts, sewers, lighthouses, terraces and tunnels stage by stage with paid, levied or bound labour, run monopolies and royal works, and keep them up or watch them decay. Founders endow schools, temples and relief that outlast their houses. Trade gains its everyday face: shops, wholesale and retail, brokers and peddlers, promotion, leases and money changers.

- **Public Works** — twenty kinds, from roads, dams, walls and granaries to power lines, grown works and stages of a megastructure, each with stages, labour, materials, budget, quality and upkeep. Finished works change speed, harvests, health and war.
- **Land Remade** — terraces open slopes to the plough and slow erosion, irrigation raises harvests, and a finished lighthouse spares the ships that pass it.
- **State Enterprise** — monopolies, royal works, state companies, licence holders, arsenals and mints, with prices, revenue, skimming and privatisation. A granary board buys, stores and sells grain to even out lean years, and a state post carries letters at set rates.
- **Endowments** — capital that pays a beneficiary for ever, for relief, learning, worship, health, works, art, kin, memory, research, hospitality to travellers and pilgrims, or the ransom of captives. Trustees may serve it, skim it or be captured.
- **Shops and Tiers** — producers, wholesalers and retailers, each with its margin, in every market large enough to hold them. Brokers trade between partner markets without holding a shop, and peddlers carry goods to settlements that have no market of their own.
- **Promotion, Leases and Exchange** — demand moved by claims that may be false; rent on land, houses, vessels and more; exchange rates and spreads between currencies.

**In your world:** A realm dug a canal with levied labour. The levy's anger fed a revolt among the young, and the canal finished three seasons late. Within a generation it had doubled the realm's trade, and the founder of the school beside its locks was remembered longer than the ruler who ordered it.

</td>
</tr>
</table>
</details>

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

<a id="chapter-xv"></a>

### 🌦 XV. Skies and Rains

<details open>
<summary><b>Expansions 98–99</b> · <sub>2 expansions</sub></summary>

<table>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc/dlc-98-under-every-sky.jpeg"><img src="common/assets/images/dlc/dlc-98-under-every-sky.jpeg" width="220" alt="Under Every Sky box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc/cover-back/dlc-98-cover-back.jpeg"><img src="common/assets/images/dlc/cover-back/dlc-98-cover-back.jpeg" width="220" alt="Under Every Sky box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 98. Under Every Sky

*Some worlds are kind to bodies. Most are not.*

Every world now presses on the bodies that live under it, and on those that live beneath it. Stars have cycles of flares and particle storms, worlds have magnetic fields that shield them, weaken and reverse, and every biology has limits of gravity, air, cold, heat, radiation, light and damp. Under the ground lies a second geography of strata, joined by passages, where whole peoples and realms can live. Settling a new world, or a new depth, means meeting those limits, or paying to go beyond them.

- **Fields and Storms** — magnetic fields that guard a world, waver and flip over epochs; flares, particle storms, field storms, cosmic ray bursts and surges of the stellar wind on the cycle of each star. Gods and powers that span worlds can strengthen a world's field or strip it away.
- **Falling Stars and Fading Suns** — meteor showers bring omens, and on airless worlds they strike towns and leave star metal behind. A dimming star cools its worlds, and a deep enough dimming starts a long winter.
- **When the Sky Breaks Through** — radiation reaches those outside shelter and in orbit, signals and networks fail, and compasses err. Auroras spread toward the equator, and every faith reads them its own way.
- **What a Body Can Bear** — each body system has its own tolerances of air, gravity, cold, heat, diet, sleep, toxins, radiation, light and humidity, so the same world weighs differently on different peoples. A dim star strains those who need light, and a land too damp or too dry strains those with a narrow range.
- **The Price of Settling** — beyond a body's limits it needs equipment, augments, grown organs, an innate power or a rite, each easing the strain at its own cost. Long voyages and light worlds wear on a body, and some peoples adapt over generations.
- **The World Below** — eleven strata can lie beneath a region: permafrost, aquifers, the deep under an ocean, reservoirs, upper, middle and lower caverns, fault zones, the inner surface of a hollow world, a magma sea and a deep underworld tied to the world's realm of the dead. Each one beneath each region is a cell with its own name, terrain, extent and light. Only some can be lived in, and crops and pasture that live on light grow only as far as a cell's light allows.
- **Passages** — cells join their neighbours at the same depth, the strata above and below, and the surface through caves, sinkholes and mines. Passages are dug, collapse (twice as often in a region with a fault zone beneath it), flood where an aquifer lies below and drain again, are cleared, and can be sealed. A mine that breaks into a cavern leaves an opening behind it.
- **Peoples of the Deep** — a world can hold peoples already living below with homelands of their own, and any people may settle any cell that can be lived in, though a town whose people's bodies are not made for the depth loses prosperity there, and when it grows poor enough it climbs back to the surface. Every level has its own rulers, so one region can hold a realm above and another below, and the first time one people crosses into a cell where another lives, the meeting goes into the record.
- **War and Trade Underground** — underground trade routes run through the passages and are cut when one collapses, floods or is sealed. Armies march below along the passages their troops can use, a narrow passage costs an army its cohesion as it files through, and a siege below can collapse the ways in or dig a mine beneath the walls.
- **The Map at Any Depth** — the atlas has a depth selector and draws each stratum with its cells, rulers and passages. The god opens passages between cells or up to the surface, holds them or takes them away straight from the map, and adds, edits, holds or removes cells in each region's Beneath panel. The book and the Codex carry a map plate for every stratum that holds a settlement.

**In your world:** A field reversal weakened a world's shield for a generation. Auroras hung over the equator, the signal towers fell silent, and a fleet trusting its compasses was lost at sea. The world's seers said the sky had opened, and a new faith grew around the lights.

</td>
</tr>
<tr>
<td width="230" valign="top" align="center"><a href="common/assets/images/dlc/dlc-99-the-rainmakers.jpeg"><img src="common/assets/images/dlc/dlc-99-the-rainmakers.jpeg" width="220" alt="The Rainmakers box front"></a><br><sub>Front</sub><br><br><a href="common/assets/images/dlc/cover-back/dlc-99-cover-back.jpeg"><img src="common/assets/images/dlc/cover-back/dlc-99-cover-back.jpeg" width="220" alt="The Rainmakers box back"></a><br><sub>Back · click to read</sub></td>
<td valign="top">

#### 99. The Rainmakers

*Who owns the rain?*

The weather is no longer only nature's. Your peoples call rain, drive off storms, divert rivers and move ice, by rite, by power, by seeding, by structures, by living craft, by bargains with place spirits and by made minds. Every success falls somewhere else as a loss. Forecasts decide when to sow, sail and march, and an accurate forecast that nobody believes still fails.

- **Working the Weather** — rain, dry, calm, cold, warm, wind or snow, by rite, power, seeding, diversion, made structures, living craft, a bargain with the spirit of a place, or a made mind living in the town. Each method has its own cost and strength, and a harbour town with nothing else to ask for calls up wind.
- **Downwind** — your rain is a neighbour's drought. Neighbours read weather works as acts with intent, treaties ban them, and banned rainmakers work in secret.
- **Whose Forecast** — eleven methods: sight, lore, almanac, instrument, a network of observers, a model, a network, a power, divination, the signs animals give and dreams, each with its accuracy. Peoples learned in beasts read animal signs and those learned in the mind read dreams. Sowing dates, voyages and campaigns follow the forecast that is believed.
- **Water from the Mountain** — snowpack feeds the summer rivers, so a poor snow year upstream is a dry harvest downstream, and the upper valley holds the lower one's fate. Where the snow has failed, rainmakers can work for snow instead of rain.
- **Weather of Its Own** — valleys, slopes, lakes and seas, forests, built land, wetlands and ice fields make their own climate, each shifting warmth, damp and wind, and change where people settle, what they grow and what makes them ill.

**In your world:** In a drought year a realm's rainmakers brought rain to its uplands. The crops of the neighbour downwind withered, and the neighbour called it an act of war. The peace that followed banned weather work by treaty, and a generation later the rainmakers worked by night.

</td>
</tr>
</table>
</details>

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## Quick start

Three commands from a fresh clone to a living world:

```sh
make env           # creates .env with a generated media secret and the worker URL
make up            # the whole stack: backend, web, gateway, media store and the image worker
make down          # stops it again; volumes are kept
```

Open **http://127.0.0.1:8080**, create the owner account, connect a model (see [Models and providers](#models-and-providers)), then walk through the seven stages of the genesis wizard: choose a template or a blank page, name your Creator, choose the language of your lore, write the seed of your world, and choose your first sons.

`make up` picks the image worker for the machine. On Apple Silicon it starts the native MLX worker in the background (`make worker-start`, `make worker-stop`, `make worker-status`; log in `data/run/image-worker.log`) and points the backend container at `http://host.docker.internal:8100`. Anywhere else it starts the `image-worker` container on the NVIDIA GPU (profile `gpu`).

### Requirements

- [uv](https://docs.astral.sh/uv/) (Python 3.13 is installed by uv)
- Node.js 24 and npm
- A model to think with: a subscription (Claude, ChatGPT, Google AI or GitHub Copilot), an API key, or a model server of your own
- Docker with Compose v2.24 or newer, for the containerized setup
- For the book PDF from a backend on the host: Pango (`brew install pango` on macOS); the Docker image has it
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
| `make agents` | Installs the pinned subscription agents into `deploy/agents` |
| `make gateway` | Runs the Bifrost gateway for API keys at `http://127.0.0.1:8180` |
| `make up` / `make down` | Starts or stops the whole stack with the right image worker |
| `make install` | Installs backend and frontend dependencies |
| `make dev` | Backend with reload and the Vite dev server |
| `make check` | Source rules, lint, types and tests |
| `make anatomy` | Rebuilds the body-plan anatomy data the entry window draws |
| `make test`, `make lint`, `make typecheck` | The individual checks |
| `make typegen` | Regenerates the typed frontend client from the OpenAPI schema |
| `make rules` | Source rules and version consistency check |
| `make version` | Shows the version; `make version v=<x.y.z[-pre]>` sets it everywhere |
| `make bump part=<major\|minor\|patch> [pre=<label>]` | Moves to the next version, optionally as a pre-release (`pre=beta.1`) |
| `make prerelease pre=<label>` / `make release` | Marks the current version as a pre-release, or drops the label |
| `make migration name=<name>` | Creates an Alembic migration |
| `make docker-up`, `make docker-up-gpu`, `make docker-up-console`, `make docker-down` | Docker stack variants |
| `make minio` | MinIO for local development |
| `make image-worker`, `make image-worker-test` | Runs or tests the image worker |
| `make worker-start`, `make worker-stop`, `make worker-status` | Native image worker in the background |
| `make migrate-legacy`, `make legacy-rule-map` | Legacy world migration |

### Versioning

The version of the app lives in one place: the `VERSION` file at the root of the repository, in [Semantic Versioning](https://semver.org) form (`0.1.0`, `0.2.0-beta.1`). Never edit a copy by hand; change it with the Make targets above. `scripts/version.py` writes it into every place that needs its own copy (the backend and image worker `pyproject.toml`, `frontend/package.json` and its lock file, the badge at the top of this README and the edition line of the information pack) and the pre-commit hook refuses a commit where any copy differs.

Everything else reads it from there: the backend serves it on `/api/health` and in the OpenAPI schema, every exported `.aerona` package and every universe in the library records the version that made it, and the frontend takes it straight from `VERSION` when it is built or served, so the library screen and the About window show the same `v…` as the backend.

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## Configuration

Every setting is an environment variable. `.env` is ignored by git; `.env.example` lists every one. The main ones:

| Variable | Meaning |
|---|---|
| `AERONA_GATEWAY_URL` | Address of the Bifrost gateway that carries API keys (`make gateway` runs one at `http://127.0.0.1:8180`; Docker uses the `bifrost` service). Empty refuses API keys. |
| `AERONA_SECRET_KEY` | Phrase that seals provider keys and subscription tokens. Empty: a key file `secret.key` is made in the data folder at the first start; back it up with the data. |
| `AERONA_AGENTS_DIR` | Where the subscription agents are installed (`make agents`, default `deploy/agents`; Docker `/opt/agents`). |
| `CLAUDE_CODE_OAUTH_TOKEN` | Older setting: when set, the first start turns it into a Claude subscription of the owner's personal workspace. |
| `AERONA_DATA_DIR` | Database, backups and (with the file media store) images. Docker always uses the `aerona-data` volume. The server refuses to start when any folder of this or any other path setting begins or ends with a space. |
| `AERONA_LLM_ENABLED` | `false` runs the world engine without any LLM calls. |
| `AERONA_SECONDARY_BACKUP_DIR` | A second disk every backup is mirrored to, with its own retention. |
| `AERONA_IMAGE_WORKER_URL` | Older setting: when set, the first start adds the image worker as the server's image model. Add or change it later under Models. |
| `AERONA_DOCKER_IMAGE_WORKER_URL` | Worker URL inside the backend container. `make up` sets it; the default is the `image-worker` container. |
| `AERONA_BIND_ADDRESS` | Host address Docker publishes ports on (default `127.0.0.1`). |
| `AERONA_IMAGE_WORKER_*` | Image worker settings: backend, model, timeouts, idle unload. |
| `AERONA_MEDIA_*` | Media store: backend (`file` or `s3`), endpoint, bucket, credentials, region, TLS. See [Media store](#media-store). |

### Models and providers

Every model call goes through one seam, so the world can think and paint with whatever you have. Connect models under **Workspace settings → Models** (or in the second step of the first setup):

- **Subscriptions**: Claude Pro or Max, ChatGPT Plus or Pro, Google AI Pro or Ultra and GitHub Copilot, each through its own official agent, logged in on the server with the address and code shown in the panel. A subscription belongs to one person, so it is logged in to in a personal workspace only. Using a subscription inside another program may be against the provider's terms; the panel says so on every card and the risk is yours.
- **API keys**: OpenAI, Anthropic, Google Gemini, Mistral, Groq, DeepSeek, xAI, OpenRouter, Cohere, Cerebras, Perplexity, Replicate and Hugging Face, through the Bifrost gateway; the key is sent with each request and kept sealed on the server. Azure OpenAI, Bedrock and Vertex models are reachable through OpenRouter.
- **Local**: any OpenAI-compatible model server (Ollama, LM Studio, vLLM, llama.cpp) by its address, and the local image worker for pictures.

Each of the four roles (world agents, writing, conversation, images) keeps an ordered chain of models; the first one that answers serves the call and the next one takes over when it cannot. A universe uses its workspace's chain for a role and the server default when the workspace has none. **Check** runs one short tool round on each entry (and one tiny picture for conversation models) so a model that cannot use tools is skipped before it fails an age.

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## Local development

```sh
make install
make dev
```

- Backend: http://127.0.0.1:8000 (API under `/api`, with reload)
- Frontend: http://127.0.0.1:5173 (Vite proxies `/api` to the backend)
- Checks: `make check` (source rules, lint, types, tests) and `make image-worker-test`
- Commit gate: `git config core.hooksPath .githooks` runs the source guards and the proving tests on every commit

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

### Accounts and teams

Everyone signs in. The first start opens a **setup** screen that creates the server owner; every universe already on the shelf moves into the owner's personal workspace and every earlier act is attributed to the owner. The app sends no e-mail: an administrator creates an account (username, e-mail, display name) and copies the **temporary password** it shows once; at the first sign-in the person sets their own password before anything else.

- **Workspaces.** Every account has a personal workspace; anyone can start a team workspace. Each workspace has its own Library of Universes, members and trash.
- **Roles.** A member's role in the workspace (Administrator, Editor, Viewer) is their role in every universe of it, present and future; a new member is a Viewer unless the person adding them picks another role. Editors change the world (ages, rules, canon locks and undo included); Viewers read everything, download the book and the Codex and ask the Divine Will questions. Per-universe overrides and the per-universe permission table exist for the rare case.
- **Working together.** Everyone sees who else is in a universe and which entry they have open. An edit saved over a field another person changed since the screen opened shows both values and lets the person keep theirs or apply their own. Acts made while an age runs wait in a queue and apply, in order and in their authors' names, when it ends. An administrator can turn on canon approval, which sends an Editor's change to locked canon to review. Every act records who made it and an optional reason; the ledger filters by person, any act can be undone (naming who undid it), and the book and the Codex list the people behind the universe under "Hands of the Creator". Divine Will, Presence and Foresight sessions are private to their author unless shared.
- **Sessions** live in an `HttpOnly` cookie; set `AERONA_COOKIE_SECURE=true` behind HTTPS. Five wrong passwords lock an account for fifteen minutes.

| Setting | Default | Meaning |
|---|---|---|
| `AERONA_COOKIE_SECURE` | false | Send the session cookie only over HTTPS. |
| `AERONA_ACCOUNTS_LOCKOUT_ATTEMPTS` | 5 | Wrong passwords in a row before an account locks. |
| `AERONA_ACCOUNTS_LOCKOUT_MINUTES` | 15 | How long a locked account waits. |
| `AERONA_ACCOUNTS_PASSWORD_MIN_LENGTH` | 10 | The shortest password accepted. |
| `AERONA_ACCOUNTS_SESSION_IDLE_DAYS` | 14 | A session unused this long ends. |
| `AERONA_ACCOUNTS_SESSION_MAX_DAYS` | 60 | No session lasts longer. |
| `AERONA_TEAM_PRESENCE_TTL_SECONDS` | 90 | How long a silent screen still counts as present. |
| `AERONA_TEAM_REASON_MAX_LENGTH` | 500 | The longest reason a person may give for an act. |
| `AERONA_TEAM_REASON_MAX_LENGTH` | 500 | The longest "why" an act may carry. |

### The library in the volume

The `aerona-data` volume holds the whole Library of Universes:

- `library.db`: the catalogue of universes and the library's own log.
- `universes/<id>/`: one folder per universe with its own SQLite database (`aerona.db`), its backups, book PDF, Codex files and work files. Universes never share a database, so one universe's epoch never waits on another's lock.
- `trash/`: deleted universes, kept for `AERONA_LIBRARY_TRASH_DAYS` days so they can be brought back.
- `models/`: the shared embedding model.

Media objects live in the MinIO bucket under a per-universe prefix (`universes/<id>/…`); a universe adopted from the old single-world layout keeps its old keys.

The first start after upgrading from a single world moves `/data/aerona.db` and its files into the library as the first universe. The move is resumable: if the container stops halfway, the next start finishes it.

Back up the whole library while the app runs:

```sh
docker compose exec backend python /app/scripts/backup_library.py /data /data/library-backup
```

Every database is copied with SQLite's online backup, so the copy is consistent even during an epoch. To share one universe, export it from the library screen as an `.aerona` file; anyone can import it into their own library.

| Setting | Default | Meaning |
|---|---|---|
| `AERONA_LIBRARY_OPEN_UNIVERSES` | 4 | Universes kept open at once; the least recently used idle one closes first. |
| `AERONA_LIBRARY_IDLE_MINUTES` | 20 | A universe with no requests, jobs or listeners closes after this many minutes. |
| `AERONA_LIBRARY_PARALLEL_EPOCHS` | 2 | Epochs of different universes that may run at the same time. |
| `AERONA_LIBRARY_IMPORT_MAX_MB` | 2048 | The largest `.aerona` file the library accepts. |
| `AERONA_LIBRARY_TRASH_DAYS` | 30 | Days a deleted universe stays in the trash. |

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
        UI[React 19 · TanStack Router and Query<br/>map · cities · graph · 3D cosmos · cards]
    end
    subgraph Web [web · nginx]
        NG[Static app + /api proxy<br/>SSE buffering off]
    end
    subgraph Backend [backend · FastAPI]
        API[API routers] --> SV[Services]
        SV --> PL[God levers<br/>action catalog · holds · undo]
        SV --> EP[Epoch orchestrator<br/>jobs · resume · cancel]
        EP --> EN[World engine<br/>505 deterministic steps]
        EP --> AG[Agents<br/>sons · mortals · Fate · chronicler · council]
        AG --> PR[Prompt catalog]
        AG --> TL[Son and mortal tools]
        TL --> EN
        PL --> EN
        EN --> RL[Rules registry]
        EN --> RC[Record of changes<br/>happenings · terms · moments]
        SV --> BK[Lore book and Codex]
        EP --> BUS[Event bus → SSE]
        RC --> DB[(SQLite WAL)]
        SV --> DB
    end
    MS[(MinIO / file<br/>media store)]
    IW[Image worker<br/>MLX or diffusers]
    CL[Providers<br/>subscriptions, Bifrost, local]
    UI --> NG --> API
    BUS --> UI
    SV --> MS
    SV --> IW
    AG --> CL
```

Agents and the player never write the world directly: son tools, mortal tools and god levers all act through the same engine primitives, so every act pays its cost, respects every hold and lands in the record of changes like anything the engine does on its own.

| Layer | Choice |
|---|---|
| Backend runtime | Python 3.13 with `uv` |
| HTTP | FastAPI and Uvicorn, with an OpenAPI schema that drives the typed frontend client |
| Realtime | Server-Sent Events with `Last-Event-ID` reconnect |
| Database | SQLite in WAL mode through SQLAlchemy 2 async and `aiosqlite`, one serialized writer; every unordered read is ordered at compile time |
| Record | Every write captured at flush and tied to its happening, with the terms of every number |
| Migrations | Alembic, checked against the models, CHECK constraints included |
| Validation | Pydantic v2 for API schemas, tool inputs and structured model outputs |
| Agents | One model seam: subscription agents over the Agent Client Protocol with tools served over MCP, API keys through the Bifrost gateway with the `openai` client, local servers directly; tokens counted with `tiktoken` |
| Jobs | In-process asyncio job manager with persisted job rows: resumable and cancellable; engine work in a lasting worker pool |
| Book | Jinja templates, drawn SVG maps, plans, strata, heraldry and family trees, and WeasyPrint for the PDF |
| Frontend | React 19, TypeScript and Vite |
| Routing and data | TanStack Router and TanStack Query, SSE-driven invalidation |
| API client | `openapi-typescript` and `openapi-fetch`, generated from the backend |
| UI | shadcn/ui on Radix and Tailwind v4, a gilded design system of shared surfaces, `lucide-react` icons and recharts |
| Map, graph, cosmos | Canvas over `d3-delaunay` Voronoi; `react-force-graph`; three.js through `@react-three/fiber` and `drei` |
| Quality | pytest, Vitest and Testing Library; ruff, mypy strict, import layers, eslint with the project's own rules, stylelint and prettier; eighty source guards in `scripts/` and `frontend/scripts/` |

### Repository layout

```
aerona/
  backend/src/aerona/
    api/          routers and schemas, one router per domain
    services/     application services: god levers, books and the Codex, backups, search
    engine/       the deterministic world simulation, one package per mechanic
    epoch/        epoch orchestration, concurrency and resume
    agents/       sons, mortals, Fate, chronicler, bard, council, genesis, deepener and more
    tools/        son and mortal tools: schema, gating, cost and effect
    prompts/      every prompt, as typed Jinja templates
    rules/        the tunable rules registry
    catalog/      static game data: rarities, domains, stars, worlds, kinds of happening and every enum family
    domain/       enums and value types shared by every layer
    db/           tables, repositories, sessions, the write guard and the record capture
    language/     procedural languages and naming
    cartography/  map generation
    llm/          the model client, retries and token counting
    core/ constants/ jobs/ events/ media/ imaging/ migration/
  frontend/src/
    features/     one folder per screen and mechanic: pantheon, cards, chronicle, map, cosmos, records, family ...
    components/   ui, layout, typography and domain components, and the entry window
    config/       navigation and app configuration
    routes/       thin TanStack file routes
  image-worker/   the MLX and diffusers image service
  common/assets/  covers, box backs and the collector's edition art
  deploy/         Dockerfiles and nginx
  scripts/        the source guards of the commit gate, coverage and export scripts
  docs/           architecture, decisions, the booklets and the full business-logic spec
```

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## Engineering principles

Weavers of the Void holds itself to eight standing rules, enforced by tooling rather than goodwill. Every commit runs a gate of source guards and proving tests, and no check is ever bypassed.

1. **Only the tests that matter.** Each change runs the static checks and the tests that cover it; the gate adds the proving suites that every engine, tool and lever change needs.
2. **The lore follows the seed.** No text the model sees pushes an image, a theme, a tone, a conflict, a gender or a look the seed did not ask for. `scripts/check_prompt_bias.py` reads every prompt, schema, tool text and UI suggestion against those rules.
3. **Every dynamic is fully wired.** A new table, value, mechanic, tool or event reaches the engine, the agent tools, the prompts, the API, the screens, the Codex, the book, the integrity checks and the spec. `scripts/check_wiring.py` and the orphan checks fail on anything left unconnected.
4. **Self-describing code.** Names and structure carry the meaning. There are no comments or docstrings anywhere, and `scripts/check_source_rules.py` reports zero violations.
5. **Production-grade, gamified frontend.** Every screen is built from the design system, covers loading, empty, error and disabled states, works from phone width up in light and dark, and shows every value through its label, never a raw key.
6. **The god controls everything.** Every table the engine changes has levers to create, edit, hold and delete it, reachable from the app. `scripts/check_control.py` finds those tables by reading the code, and the god-control test runs every engine step on a held world to prove nothing tied to a held node moves.
7. **Every change reaches the book and the Codex.** Every node kind renders its typed sections in both, records that belong to no node fill the "Records of the Cosmos" appendix, and nothing is ever truncated.
8. **Every defect closes its class.** A fix comes with a test that fails on the old code, a mechanical guard so it cannot return, and a hunt for its siblings. Every son and mortal tool, every lever, every god job and every read endpoint is run to success by a test, and deprecated library APIs are errors.

To run the same gate locally, enable the hooks once with `git config core.hooksPath .githooks`.

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
| Sons do not act and the health panel shows no writing model | Open Workspace settings, Providers, connect a model and give the roles a chain; press Check to see that each model can use tools |
| The UI says image generation is disabled | `AERONA_IMAGE_WORKER_URL` is empty. Set it to the worker address and start the worker |
| No images on a Mac in Docker | Docker on macOS has no Metal access. Use `make up` or `make worker-start`, which runs the MLX worker natively, and check `make worker-status` and `data/run/image-worker.log` |
| The first image takes minutes | The model is downloading (about 6 GB on Apple Silicon). Later images start as soon as the model is loaded |
| The book PDF fails on a backend started on the host | WeasyPrint needs Pango: `brew install pango` on macOS, `libpango-1.0-0 libpangoft2-1.0-0` on Debian or Ubuntu. The Docker image already has it |
| `docker compose` refuses to start | Both `AERONA_MEDIA_ACCESS_KEY` and `AERONA_MEDIA_SECRET_KEY` are required; `make env` generates them |
| A port is already in use | Move it with the `AERONA_*_PUBLISHED_PORT` and `AERONA_*_PORT` settings in `.env` |
| You want the world to turn without any agent | Set `AERONA_LLM_ENABLED=false`; the engine simulates every epoch on its own |
| The backend stopped mid-epoch | Start it again. Epochs and long jobs are persisted and resume where they stopped |
| The engine left something alone you wanted changed | Check whether you hold it: a held node is never touched by any engine step. Release the hold in its entry window under the god's controls |

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## FAQ

**Who is it for?**
Anyone who builds worlds: narrative designers, lore writers, screenwriters, novelists and game masters, and anyone who wants to watch a cosmos live. You set the idea and the rules; the world does the bookkeeping of consequences.

**Which models can I use?**
A subscription you log in to (Claude, ChatGPT, Google AI or GitHub Copilot), an API key of thirteen cloud providers through the Bifrost gateway, or a model server of your own. Each role gets its own ordered chain. The Usage page shows the tokens of every call.

**Does my world leave my machine?**
Your database, backups, book and images stay on your disk. Only the agents' prompts and replies travel to Claude.

**Are the expansions extra?**
No. The Loom and all 99 expansions are part of every world from the first epoch.

**Can I take my lore into other tools?**
Yes. Export the lore book as HTML or PDF, the Codex as Markdown or a ZIP with a page for every record, or the whole world as a `.aerona` package. Nothing is shortened.

**Is it free?**
Yes, completely. Weavers of the Void is open source under the AGPL-3.0: every feature and every expansion, for personal and commercial use, self-hosted wherever you like, with no limit on users, universes or epochs. The project funds itself through optional services such as custom worldbuilding, engineering, consulting and managed hosting, never by locking features. See [License](#license).

**Who owns the worlds I make?**
You do. The lore, the book, the Codex, the World Package and the images are yours, with no fee or royalty, and they are not bound by the AGPL. See [LICENSING.md](LICENSING.md).

**Can I protect what is already canon?**
Yes. Hold any node, and no engine step will create, change or delete anything tied to it. The world keeps living around it.

**Can I play in Turkish?**
Yes. Choose Turkish as the lore language in the genesis wizard, and every chronicle, name and legend is written in it; even the engine's own chronicle lines are localised by an agent. The interface itself is English.

**Can I undo a mistake?**
Yes. Every action lands in Fate's ledger and can be undone, every engine change can be reverted from the record, and every epoch has a backup to restore.

**Can I change the rules of the world?**
All of them. More than 20,700 rules are editable live from Settings → World Rules, every mechanic can be run, suppressed or pinned by hand, and every prompt is visible under Settings → Prompts.

**Is the history the same every time?**
The engine is. The same world with the same seed and the same choices produces the same history to the last value. The agents are language models, so a fresh run can choose differently, and a different choice grows a different history. With the agents off, every epoch is fully reproducible.

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## Documentation

**Booklets**, written for players from the code itself:

| Booklet | What it covers |
|---|---|
| [The Rules of the World](docs/game-rules.md) | How the world works, mechanic by mechanic |
| [The Powers of a God](docs/god-powers.md) | Everything the Creator can do from the app |
| [The Deeds of Sons and Mortals](docs/agent-tools.md) | Every son tool and every mortal tool |
| [The Voices of the World](docs/ai-roles.md) | Every agent role and what it writes |
| [Goals, Growth and Score](docs/game-progress.md) | Scenarios, achievements, levels, renown and score |
| [How the World Connects](docs/interconnections.md) | How every mechanic feeds the others |
| [The Things of the World and Their Names](docs/world-terms.md) · [JSON](docs/world-terms.json) | Every kind of thing and every value, by its name |

**Design and engineering:**

| Document | What it covers |
|---|---|
| [Architecture](docs/architecture.md) | Stack, layers, async model, design system and deployment |
| [Decisions](docs/decisions.md) | Every architectural decision and why it was made |
| [Migration plan](docs/migration-plan.md) | Carrying a legacy world into Weavers of the Void |

**The project:**

| Document | What it covers |
|---|---|
| [Licensing](LICENSING.md) | Which license covers which part, what it asks of you, and why your worlds are yours |
| [Third-party notices](THIRD_PARTY_NOTICES.md) | Every dependency, font, model, service and agent program with its license |
| [Trademarks](TRADEMARKS.md) | How the name and the logo may be used by forks and hosted services |
| [Contributing](CONTRIBUTING.md) · [DCO](DCO) | How to set up, the rules every change follows, and signing off commits |
| [Governance](GOVERNANCE.md) · [Maintainers](MAINTAINERS.md) | Who decides, how contributions are judged and how the project pays for itself |
| [Security](SECURITY.md) | How to report a vulnerability privately |
| [Code of Conduct](CODE_OF_CONDUCT.md) | How we treat each other |

**The specification:**

| Document | What it covers |
|---|---|
| [Data model](docs/spec/01-data-model.md) | Every table and field |
| [World core](docs/spec/02-world-core.md) | The world, entities, bonds and the chronicle |
| [Rules registry](docs/spec/03-rules-registry.md) · [JSON](docs/spec/rules-registry.json) | The tunable rules and their groups |
| [Engine core](docs/spec/04-engine-core.md) · [Deep mechanics](docs/spec/05-deep-mechanics.md) | The world simulation |
| [Cosmos and the strange](docs/spec/06-cosmos-and-strange.md) · [Cosmos types](docs/spec/14-cosmos-types.md) | Stars, worlds, travel, horror and the beyond |
| [Gods and progression](docs/spec/07-gods-and-progression.md) | The Creator, sons, reputation, goals, death and resurrection |
| [Agents and tools](docs/spec/08-agents-and-tools.md) · [Prompts](docs/spec/09-prompts.md) | Every agent role, every son tool, every prompt |
| [Epoch pipeline](docs/spec/10-epoch-pipeline.md) | The life of an epoch, resume, backups and the live stream |
| [API](docs/spec/11-api.md) · [Frontend](docs/spec/12-frontend.md) | Every route and every screen |
| [Depth expansion](docs/spec/13-depth-expansion.md) · [Interconnection](docs/spec/13-interconnection.md) · [Coverage](docs/spec/13-coverage.md) · [Depth metric](docs/spec/13-depth-metric.md) | The mechanics behind expansions 1–86 and how they connect |
| [Minds, powers, living craft and typed kinds](docs/spec/16-minds-powers-living-craft.md) · [Coverage](docs/spec/16-coverage.md) | The mechanics behind expansions 87–94 and the depth of every other |
| [W52 expansions](docs/spec/17-w52-expansions.md) · [Coverage](docs/spec/17-coverage.md) | The widening and deepening of all 99 expansions, the world below and their integration |
| [Expansions](docs/spec/15-dlc-ideas.md) | The Loom and all 99 expansions in full |
| [Mechanic coverage](docs/spec/coverage.md) · [Inventory](docs/spec/inventory.md) | Traceability from every mechanic to its module, trigger, control, screen and test, and every countable thing with the guards that prove it |
| [Model text ledger](docs/spec/model-text-ledger.md) | Every file whose prose reaches the model, read in full against the lore rules |
| [OCM](docs/spec/ocm-coverage.md) · [Motifs](docs/spec/motif-coverage.md) · [Science](docs/spec/science-coverage.md) | How the world covers the Outline of Cultural Materials, the Thompson motif index and the UNESCO sciences |

<p align="right"><sub><a href="#top">Back to top ↑</a></sub></p>

## License

Weavers of the Void is free software, licensed under the [GNU Affero General Public License v3.0](LICENSE) (`AGPL-3.0-only`). Use it for anything, commercially or not, self-host it, fork it and offer it as a service. If you run a modified version for others over a network, offer them its source code.

- **Your worlds are yours.** Books, Codices, World Packages and images you make carry no AGPL obligations and no royalty, by an additional permission in [NOTICE](NOTICE).
- **Open formats.** The World Package, Codex and HTTP API specifications are under [CC BY 4.0](LICENSES/CC-BY-4.0.txt), so anyone can build compatible tools.
- **Image worker.** [`image-worker/`](image-worker/) is under the [Apache License 2.0](image-worker/LICENSE).
- **Third parties.** Dependencies, fonts, models, the Bifrost gateway and the vendors' agent programs keep their own licenses; some agent programs are proprietary. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- **The name.** "Weavers of the Void" and its logo are trademarks; forks and hosted services use their own name. See [TRADEMARKS.md](TRADEMARKS.md).

The full picture is in [LICENSING.md](LICENSING.md). Contributions are welcome under the same terms, signed off under the [DCO](DCO); see [CONTRIBUTING.md](CONTRIBUTING.md).

---

<p align="center">
  <img src="frontend/public/brand/logo-64.png" alt="" width="40"><br>
  <sub><b>Weavers of the Void</b> · You are the Creator. The rest writes itself.</sub>
</p>
