[booklet]: # "Weavers of the Void® booklet: the voices of the world"

# Weavers of the Void®: The Voices of the World

The world engine lives the world by its rules. Language models give it a voice: they play your sons and the notable mortals, judge each epoch as Fate, write the chronicle and give words to everything the world makes. This booklet names every one of those roles, when it speaks, what it reads and what it writes.

| The voices at a glance | |
|---|---:|
| Roles | 28 |
| Roles when a world is made | 6 |
| Roles in every epoch | 12 |
| Roles when you ask, or the world needs it | 10 |
| Prompts the roles are given | 61 |

## Contents

1. [How to read this booklet](#how-to-read-this-booklet)
2. [The roles at a glance](#the-roles-at-a-glance)
3. [When a world is made](#s-making)
4. [In every epoch](#s-epoch)
5. [When you ask, or the world needs it](#s-asked)

## How to read this booklet

- The roles are gathered by **when they speak**: when a world is made, in every epoch, or when you ask.
- **Writes** lists what the role must give back. What it is shown first is laid out in its prompts. What a role writes is checked against the rules of the world before it enters the world; the engine decides what a deed does.
- The roles follow the world's own seed and canon. The game's own text gives them no images, themes, tone or conflict of its own, so a world becomes whatever kind of lore its seed asks for.
- Every prompt a role is given can be read in Settings › Prompts, and every call to a model, with its cost in tokens, is listed on the Usage screen.
- Every role in this build runs on Claude Haiku (`claude-haiku-5-5`). A call that fails is tried 3 times in all, and a turn that breaks off may continue 2 more times. These are world rules too.
- The companion booklet *The Deeds of Sons and Mortals* lists the tools the turns act through.

## The roles at a glance

| Role | When it speaks |
|---|---|
| [Genesis](#v-genesis) | When a world is made |
| [Creator portrait](#v-creator_portrait) | When a world is made |
| [Son summoning](#v-summoning) | When a world is made |
| [Son powers](#v-son_powers) | When a world is made |
| [Awakening of the peoples](#v-awakening) | When a world is made |
| [World birth](#v-world_birth) | When a world is made |
| [Son turn](#v-son_turn) | In every epoch |
| [Mortal turn](#v-mortal_turn) | In every epoch |
| [Fate](#v-fate) | In every epoch |
| [Fate extra judgment](#v-fate_extra) | In every epoch |
| [Chronicler](#v-chronicler) | In every epoch |
| [Chronicle completion](#v-chronicle_fix) | In every epoch |
| [Naming](#v-naming) | In every epoch |
| [Voices of the peoples](#v-voices) | In every epoch |
| [Council of the gods](#v-council) | In every epoch |
| [Fate bond suggestion](#v-bond_suggestion) | In every epoch |
| [Fate related bond naming](#v-bond_naming) | In every epoch |
| [Localisation](#v-localisation) | In every epoch |
| [Revelation](#v-revelation) | When you ask, or the world needs it |
| [Lost chronicle](#v-lost_chronicle) | When you ask, or the world needs it |
| [Deepening](#v-deepening) | When you ask, or the world needs it |
| [Creator epic](#v-creator_epic) | When you ask, or the world needs it |
| [Creator deepening](#v-creator_depth) | When you ask, or the world needs it |
| [Foreign god deepening](#v-foreign_god_depth) | When you ask, or the world needs it |
| [Son epic](#v-son_epic) | When you ask, or the world needs it |
| [Entity image prompts](#v-entity_image_prompts) | When you ask, or the world needs it |
| [Cosmos image prompts](#v-cosmos_image_prompts) | When you ask, or the world needs it |
| [Translation](#v-translation) | When you ask, or the world needs it |

<a id="s-making"></a>

## When a world is made

These roles speak when something new comes into being: a whole world at genesis, a new son, a new world in the cosmos, a people waking.

<a id="v-genesis"></a>

### Genesis

Turns your seed into a world at genesis: the world's name, its cosmology, its tone and way of naming, the Creator, the first world, its star and regions, and the first sons.

- **Writes** world name, cosmology, naming, tone, god, world, star, regions, first celestial, cosmic resource, layer, sons and relations.
- **Time allowed:** 360 seconds, set by the world rules.
- **Prompts** it is given, in Settings › Prompts: `genesis_system` and `genesis_user`.

<a id="v-creator_portrait"></a>

### Creator portrait

Writes the Creator's portrait: title, appearance and temperament.

- **Writes** title, appearance, temperament and image prompt.
- **Prompts** it is given, in Settings › Prompts: `creator_portrait_system` and `creator_portrait_user`.

<a id="v-summoning"></a>

### Son summoning

Writes a new son when you summon one or when a son bears a child: name, title, domains, appearance, temperament and inner life.

- **Writes** name, title, domain 1, domain 2, appearance, temperament, obsession, fear, speech style, secret, strengths, weakness, passions, powers, existence, design and image prompt.
- **Prompts** it is given, in Settings › Prompts: `summon_son_system` and `summon_son_user`.

<a id="v-son_powers"></a>

### Son powers

Gives a new son the powers and the way of existing that follow from its domains and nature.

- **Writes** powers, existence and image prompt.
- **Prompts** it is given, in Settings › Prompts: `son_powers_system` and `son_powers_user`.

<a id="v-awakening"></a>

### Awakening of the peoples

Writes the peoples of a world as they wake to awareness.

- **Writes** peoples.
- **Time allowed:** 300 seconds, set by the world rules.
- **Prompts** it is given, in Settings › Prompts: `awaken_peoples_system` and `awaken_peoples_user`.

<a id="v-world_birth"></a>

### World birth

Writes a new world when a son gives birth to one: where it lies, its type, name, language, cosmology and its physical nature.

- **Writes** placement, type, dialect, name, language, description, cosmology, gravity, atmosphere, time factor, day, star id, parent world id, star, regions, sky, unique resource, cosmic resource, old god, natives and image prompt.
- **Prompts** it is given, in Settings › Prompts: `new_world_system` and `new_world_user`.

<a id="s-epoch"></a>

## In every epoch

These roles speak in the order of an epoch: the sons act, the mortals act, the world engine lives the years, Fate judges, the chronicler writes and the peoples speak.

<a id="v-son_turn"></a>

### Son turn

Plays one son's turn. The son reads its world and its memory, decides what it wants and acts through its tools until its action points run out.

- **Acts through** the tools listed in [The Deeds of Sons and Mortals](agent-tools.md#a-son).
- **Prompts** it is given, in Settings › Prompts: `son_turn_continuation`, `son_turn_system` and `son_turn_user`.

<a id="v-mortal_turn"></a>

### Mortal turn

Plays the turn of a notable mortal or community, including the fallen who still act. It reads what it can see from where it stands and acts through its tools.

- **Acts through** the tools listed in [The Deeds of Sons and Mortals](agent-tools.md#a-mortal).
- **Prompts** it is given, in Settings › Prompts: `fallen_son_turn`, `mortal_turn_continuation`, `mortal_turn_system` and `mortal_turn_user`.

<a id="v-fate"></a>

### Fate

Judges the epoch once the turns and the world engine are done. Fate decides which new records stay as canon and which are rejected, names what needs a name, fulfils prophecies, opens, moves and closes the open stories of the world, and rewards the sons.

- **Writes** verdicts, namings, fulfilled prophecies, resolved story, closed stories, advanced stories, new stories, rewards, facts and words.
- **Time allowed:** 480 seconds, set by the world rules.
- **Prompts** it is given, in Settings › Prompts: `fate_judgment_system` and `fate_judgment_user`.

<a id="v-fate_extra"></a>

### Fate extra judgment

Judges the records that did not fit into Fate's main judgment, so none waits unjudged.

- **Writes** verdicts.
- **Time allowed:** 480 seconds, set by the world rules.
- **Prompts** it is given, in Settings › Prompts: `fate_extra_judgment_user` and `fate_judgment_system`.

<a id="v-chronicler"></a>

### Chronicler

Writes the history of the epoch after Fate has judged: the name of the age, its narrative, a one-sentence summary and a section for every world.

- **Writes** age name, narrative, summary, worlds and coverage.
- **Time allowed:** 480 seconds, set by the world rules.
- **Prompts** it is given, in Settings › Prompts: `chronicler_lost_age_user`, `chronicler_system` and `chronicler_user`.

<a id="v-chronicle_fix"></a>

### Chronicle completion

Completes the chronicle: writes the section of a world the chronicler left out, and rewrites a passage the chronicle audit found wanting.

- **Writes** narrative, worlds and coverage.
- **Time allowed:** 300 seconds and 480 seconds, set by the world rules.
- **Prompts** it is given, in Settings › Prompts: `chronicler_audit_fix_user`, `chronicler_concise_system`, `chronicler_lost_world_sections_user`, `chronicler_missing_worlds_user` and `chronicler_system`.

<a id="v-naming"></a>

### Naming

Names the records that came into being without a name, in the world's own way of naming.

- **Writes** namings.
- **Prompts** it is given, in Settings › Prompts: `naming_system` and `naming_user`.

<a id="v-voices"></a>

### Voices of the peoples

Writes the voices of the peoples after each epoch: how they see what happened and what they came to believe.

- **Writes** views and beliefs.
- **Time allowed:** 240 seconds, set by the world rules.
- **Prompts** it is given, in Settings › Prompts: `voices_system` and `voices_user`.

<a id="v-council"></a>

### Council of the gods

Holds a council of the gods: the speeches, the motion, the votes and alliances, the decision and its minutes. A council can meet in an epoch on its own or when you call one.

- **Writes** speeches, motion, votes, alliances, decision, target id, world id, school, punishment, penance deed, voting rule, minutes and agenda.
- **Time allowed:** 240 seconds, set by the world rules.
- **Prompts** it is given, in Settings › Prompts: `council_session_system` and `council_session_user`.

<a id="v-bond_suggestion"></a>

### Fate bond suggestion

Suggests bonds for records that stand alone, so that every record is tied into the world.

- **Writes** bonds.
- **Prompts** it is given, in Settings › Prompts: `bond_suggest_system` and `bond_suggest_user`.

<a id="v-bond_naming"></a>

### Fate related bond naming

Decides what to call a bond between related records.

- **Writes** decisions.
- **Prompts** it is given, in Settings › Prompts: `bond_name_related_system` and `bond_name_related_user`.

<a id="v-localisation"></a>

### Localisation

Writes the lines of the epoch in the world's lore language.

- **Writes** lines.
- **Prompts** it is given, in Settings › Prompts: `localise_system` and `localise_user`.

<a id="s-asked"></a>

## When you ask, or the world needs it

These roles speak when you call on them from a screen of the game, and some of them also when the world itself needs a text: a deeper account, an epic, a translation or the words for an image.

<a id="v-revelation"></a>

### Revelation

Writes a single record you create with your own hand, and records the world itself brings forth through some of its mechanics.

- **Writes** type, name, subtype, description, domain, power level, location id, stats, links, image prompt, tags, mechanic, commodity, material, resource mechanics and structure kind.
- **Prompts** it is given, in Settings › Prompts: `revelation_system` and `revelation_user`.

<a id="v-lost_chronicle"></a>

### Lost chronicle

Writes the chronicle of an epoch whose history was never written.

- **Writes** age name, narrative, summary, worlds and coverage.
- **Time allowed:** 300 seconds, set by the world rules.
- **Prompts** it is given, in Settings › Prompts: `chronicler_lost_age_user`, `chronicler_system` and `chronicler_user`.

<a id="v-deepening"></a>

### Deepening

Deepens a record, a star or a world: its history, rumours, sayings, details and hidden truth. Some records are also deepened on their own at the end of every epoch.

- **Writes** history, rumours, sayings, details, hidden truth, special and kinds.
- **Prompts** it is given, in Settings › Prompts: `deepen_celestial_system`, `deepen_celestial_user`, `deepen_entity_system` and `deepen_entity_user`.

<a id="v-creator_epic"></a>

### Creator epic

Writes the epic of the Creator.

- **Writes** title, sections and line.
- **Prompts** it is given, in Settings › Prompts: `creator_epic_system` and `creator_epic_user`.

<a id="v-creator_depth"></a>

### Creator deepening

Deepens the Creator: history, names, secrets, fears, prohibitions, gifts, desire and sayings.

- **Writes** history, names, secrets, fears, prohibitions, gifts, desire, sayings, rumours and hidden truth.
- **Prompts** it is given, in Settings › Prompts: `creator_deepen_system` and `creator_deepen_user`.

<a id="v-foreign_god_depth"></a>

### Foreign god deepening

Deepens a foreign god: personality, existence, powers, history, worship and its view of your pantheon.

- **Writes** personality, existence, powers, history, names, secrets, sayings, rumours, desire, view of pantheon, worship, hidden truth and image prompt.
- **Prompts** it is given, in Settings › Prompts: `foreign_god_deepen_system` and `foreign_god_deepen_user`.

<a id="v-son_epic"></a>

### Son epic

Writes a son's epic. Old epics are also written anew from time to time as the son's story moves on.

- **Writes** title, epic and line.
- **Prompts** it is given, in Settings › Prompts: `son_epic_system` and `son_epic_user`.

<a id="v-entity_image_prompts"></a>

### Entity image prompts

Writes the words an image of a record is drawn from, for the records that have none.

- **Writes** prompts.
- **Prompts** it is given, in Settings › Prompts: `entity_image_prompts_system` and `entity_image_prompts_user`.

<a id="v-cosmos_image_prompts"></a>

### Cosmos image prompts

Writes the words an image of a star, a world, a galaxy or another body of the cosmos is drawn from, for those that have none.

- **Writes** prompts.
- **Prompts** it is given, in Settings › Prompts: `cosmos_image_prompts_system` and `cosmos_image_prompts_user`.

<a id="v-translation"></a>

### Translation

Translates a text into one of the world's own languages, with its pronunciation and word-by-word meaning, and coins the new words it needs. The world also calls on it when it names things in its own tongues.

- **Writes** translation, pronunciation, word by word, new words and note.
- **Time allowed:** 120 seconds, set by the world rules.
- **Prompts** it is given, in Settings › Prompts: `translate_system` and `translate_user`.
