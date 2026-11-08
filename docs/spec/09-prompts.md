# 09 — Prompts (the single prompts module)

Status: specification, translated from the old Turkish code base (`/Users/egedogan_dursun/aerona`).
Sources: `src/agents.js`, `src/llm.js`, `src/world.js` (context builders), `src/gorselyon.js`, `src/rules.js`
(enums shown to the model), plus the parts appended at the end of this file for `src/tools.js` tool descriptions
(see 08), `src/konsey.js`, `src/kozmos.js`, `src/agonar.js`, `src/olumluler.js`, `src/firsatlar.js`, `src/itibar.js`,
`src/hedef.js`, `src/yabanci.js`, `src/sihirbaz.js`.

This file is meant to become **one** module in the new app (e.g. `backend/aerona/llm/prompts.py`). Every prompt
has a stable **id**. Every structured output has a **JSON schema** id. Agents (08) refer to prompts only by id.

## 0. Conventions

### 0.1 Global rules for every prompt

1. **Model**: every call uses **Claude Haiku** (user rule: *every* LLM call uses Haiku; there is no fallback or
   escalation to Sonnet/Opus, and no per-role model setting). The old app had a per-role model table
   (`dunya.modeller` JSON, keys = rarity keys + `kader`, `yaratilis`, `cagirma`, `derinlik`, `vahiy`, default
   `haiku`) and an `effort` parameter that was only sent for non-Haiku models (`EFFORT` = `low` for every role).
   **Drop both**: the new app has one constant `MODEL = <current Haiku model id>` and never sends `effort`.
2. **Language**: the old prompts said "You write in Turkish (image prompts in English)". The new app is
   English-only, so every such sentence is translated to **"You write in English."** and the image-prompt clause is
   kept only as a reminder that image prompts are English prose. Translations below already apply this.
   **Image style (supersedes every "photoreal", "camera and lens" wording below)**: image prompts describe content,
   light and composition only and never name a medium, art style, camera or lens. The world's image style
   (`cosmos.image_style`: `photoreal` default, `painting`, `ink`, `watercolor`, `anime`, or `custom` with
   `cosmos.image_style_custom` free text ≤300) is chosen in the genesis wizard (world step) and in Settings > Images,
   and is applied at render time (`catalog/image_styles.styled_prompt`: a style lead and tail around the stored
   prompt; photographic terms are stripped from older prompts for non-photo styles). Each generated image records the
   style signature (`images.style`); `POST /api/image-gen/batch/restyle` repaints every record whose generated cover
   is in another style from its own stored prompt and makes the new image the cover (earlier images stay, uploads are
   never touched); `GET /api/image-gen` reports the count as `off_style`.
3. **Language-specific logic** (Turkish suffix harmony `ekDuzelt`, `toLocaleLowerCase('tr')`, Turkish stop-word
   lists, Turkish root stemming `kokBul`, vowel-harmony dialect checks) is marked
   **LANGUAGE-SPECIFIC: drop or replace**. The behaviour it protected is described so it can be re-implemented
   for English (e.g. stemming with a simple English stemmer).
4. **Template syntax** used in this file: `{name}` = variable, `[[if cond]] … [[/if]]` = optional block,
   `[[each x in list]] … [[/each]]` = repetition, `{budget(text, N, hint)}` = character budget truncation
   (see 0.3). Literal guillemets `«…»` are part of the prompt (the son's final "word" is delimited by them).
5. **Numbers never leak into lore**: almost every writing prompt forbids record numbers (`#12`), stat names/values,
   star glyphs (`★`), percentages. Prompts *show* ids (the model needs them for structured references) but the
   post-processor `sanitize_narrative` (old `anlatiTemizle`, see 08 §post-processing) strips leaks anyway.
6. **Tunable numbers inside prompts** (e.g. "at most {rationale_words} words") are read from the rules registry at
   render time — never hard-coded (user rule "no constant without a setting").

### 0.2 Structured call envelope

Structured calls = Agent SDK `query()` with `outputFormat: {type: 'json_schema', schema}`, no tools,
`maxTurns = model.structured_steps` (default 8), `systemPrompt = <system>`, `prompt = <user>`. If the SDK returns no
`structured_output`, the wrapper tries to parse the first `{…}` block of the raw text. See 10 §LLM retry policy.

Agent calls (son turn, mortal turn) = `query()` with an in-process MCP server named `dunya` (sons) or `olumlu`
(mortals) and `allowedTools: ['mcp__<server>']`, streaming partial messages.

### 0.3 Budget truncation helper — `budget(text, max, hint)` (old `butce`)

Used everywhere a context section must fit into a character budget.

```
if text is empty or len(text) <= max: return text
lines = text.split('\n'); out = []; n = 0
for line in lines:
    if n + len(line) + 1 > max:
        room = max - n - 2
        if room >= context.budget_trim_min (default 120): out.append(line[:room] + '…'); n = max
        break
    out.append(line); n += len(line) + 1
if out is empty: out.append(lines[0][:max-1] + '…')
return '\n'.join(out) + f"\n… (+{len(lines) - len(out)} more lines; {hint})"
```

The `hint` tells the model which read tool shows the rest, e.g. "look with search_entities",
"see world_summary section=events". Hints used in prompts (translated): `"look with search_entities"`,
`"rest in the chronicle"`, `"look with world_summary and my_memory"`, `"look with world_summary"`,
`"look with my_memory"`, `"see the chronicle"`, `"words in the chronicle"`, `"folk beliefs"`,
`"prompt budget"`, `"the rest in the naming round"`, `"in the chronicle"`.

### 0.4 Sectioned budget — `sectioned_budget(sections, max, hint)` (old `bolumluButce`)

Each section `{text, floor, hint}` first receives `min(len(text), floor)`; if the sum of floors (+1 newline each)
exceeds `max`, all floors scale down proportionally; the remaining room is handed out in section order. A section
that does not fit is truncated with `budget()` and its own hint. Used by `context.world_summary`.

---

## 1. Shared fragments

### 1.1 `shared.cliche_ban` (old `KLISE_YASAGI`) — appended to almost every system prompt

> Avoid clichés: generic fantasy names and concepts like "Dark Lord", "Ancient Forest", "Dragon Mountain",
> "Crystal Cave" are forbidden. Everything must have a strange, concrete logic of its own; that logic must belong to
> this entity and to this corner of the world, and must not lean on images repeated everywhere in the world (the
> list of tired images).
> Names must fit the world's naming language.

### 1.2 `shared.image_prompt_rules` (old `GORSEL_YAZIM`) — appended to every image-prompt field description

> Image prompt rules: describe only what IS visible; never use negations (no, without, not, lacking, absent)
> because the image model ignores them and draws the thing anyway; describe the replacement instead (e.g. "a smooth
> blank head with a single thin dark slit" rather than "no face"). Whatever the subject (person, creature, place,
> object, event or god), name at least two details unique to this world so the image never falls back to a generic
> real-world look.

(Already English in the old code. Reason: the local image model — mflux z-image-turbo — takes no negative prompt.)

### 1.3 `shared.section_keys_rule` (old `ANAHTAR_ISTEM`) — appended to every "deepen" user prompt

> Every section of the output is written into ITS OWN key; `history` is prose history only — no headings such as
> "Rumors:", "Secrets:", "Sayings:" and no other key's content inside it. Array keys are arrays, text keys are a
> single text.

### 1.4 `shared.rationale_desc` (old `GEREKCE_ACIKLAMA`) — description of the `rationale` field of a verdict

> One short sentence, at most {fate.rationale_words} words, in the world's own language: why accept, fix or
> reject. Do NOT write record/thread numbers, tags (thread:N), the names of pre-screening warnings (UNBOUND, TIRED
> IMAGE…) or criterion letters.

### 1.5 `shared.verdict_criteria` (old `YARGI_GOREVI`) — used by the main judgment and every extra judgment round

> TASK 1, Judgment: for everything the sons and mortals created this age, give accept, fix or reject. Reward
> bold, strange, conflict-creating things; but Fate is not merely an approver.
> If there is a small contradiction, give "fix" instead of reject and you MUST write the description that removes
> the contradiction. REJECTION CRITERIA (reject if one clearly applies): (a) it violates a law of nature or a canon
> fact, (b) it has no meaningful connection to the world (PRE-SCREEN: UNBOUND), (c) it is a lazy cliché or a copy of
> tired motifs, (d) it is absurdly mismatched with its creator's domain and power, (e) it almost exactly repeats the
> name or function of an existing record.
> Creations that carry "PRE-SCREEN WARNINGS" may be accepted only if the rationale is explicitly written (the
> rationale does not mention the warning's name; it states the reason in the world's language).
> SOUND AND NAME RULES ARE PER WORLD: judge each record only by its own world's naming language; one world's sound
> ban (e.g. a vowel forbidden in the main world) does not apply to a record in another world and is not a
> contradiction for a name there.
> In public fields (rationale, fixed description, reason, how, thread text) do not write record or thread numbers,
> tags or internal warning names; the fixed description describes the record itself and never says "Fate fixed /
> rewrote".

### 1.6 `shared.no_numbers_clause` — repeated inline (kept verbatim in each prompt below)

> Do not write record numbers (#12), stat names or values (e.g. "morale 78", "565 soldiers", "power 34"), star
> glyphs or percentages; express magnitude in words.

### 1.7 `shared.tired_images` (old `motifYasagi(worldId)`)

Rendered only when the list is non-empty:

> TIRED IMAGES (repeated too often in the world's texts): {motifs, comma-joined, each like "salt dust (31%)"}.
> Do NOT use these or their synonyms; instead find images specific to this entity and this corner of the world that
> have not been used before (another sense, another material, another craft, another season).
> [[if foreign_images]] OTHER WORLD'S WORDS (the main world's worn images; do not carry them into this world):
> {foreign_images}. [[/if]]

How the lists are computed (old `yorgunMotifler`, `motifListesi`, `yabanciImgeler`), per world (or global):
- single-word motifs: over the last `lang.motif_window` record descriptions (excluding pending "[World engine]"
  ones) count, per document, the stem (first `lang.motif_root` letters of the stemmed word) of every lowercase word
  of length ≥ `lang.motif_root_min` that is not a stop word / common word. A stem is "tired" if it appears in ≥
  `max(lang.motif_min, docs × lang.motif_threshold%)` documents (needs ≥ `lang.motif_min_records` docs).
- two-word motifs: same over the last `lang.motif_window` deepening texts + last `lang.motif_narratives` epoch
  narratives, counting adjacent stem pairs, threshold `lang.motif_pair_threshold%`.
- pairs that occur in the world header (canon: cosmology, laws, the god's prohibitions) are never banned.
- top `lang.motif_count` by ratio, rendered as the shortest surface form plus `(NN%)`.
- `motif_list(worldId)` = global list + that world's own list; `foreign_images(worldId)` = main world's list minus
  stems that appear in that world's header (only for worlds ≠ 1 in a multi-world cosmos).
LANGUAGE-SPECIFIC: the stemmer (Turkish suffix list) and stop-word lists must be replaced with English ones; the
mechanism itself (n-gram fatigue detection) is language-neutral and should be kept. These `DIL` tunables are
owned by the language/lore spec.

---

## 2. Context builders (text blocks inserted into prompts)

All of these are deterministic functions; they are part of the prompts module because their wording is prompt text.

### 2.1 `context.world_header(world, world_id=None, short=False)` (old `dunyaBasligi`)

Lines (empty lines dropped, joined with `\n`):

```
WORLD: {world.name} — Age {world.epoch} (world year {world.year}). Creator god: {world.god_name}[[if god_title]], {god_title}[[/if]].
[[if not short and god_temperament]]GOD'S TEMPERAMENT: {god_temperament}[[/if]]
[[if not short and god_note]]THE GOD'S OWN WORD (canon): {god_note}[[/if]]
[[if not short]]CREATOR'S MOOD (sensed from the sky; not a number, an intuition): contentment {level(mood.contentment)}, anger {level(mood.anger)}, attention {level(mood.attention)}, loneliness {level(mood.loneliness)}. If his anger overflows, punishment falls on godless and cursed lands; if he is content, favour falls on his worshippers; if he is silent, his sons feel abandoned.[[/if]]
[[if not short and god_epic]]THE GOD'S EPIC: "{epic.title}" — its best-known line: {epic.line}[[/if]]
[[if god_depth]]THE GOD'S PROHIBITIONS: {depth.prohibitions joined " · "}[[/if]]
[[if god_depth and not short]]THE GOD'S DESIRE (his sons sense it): {depth.desire}[[/if]]
COSMOLOGY: {cosmology; if short and longer than context.short_cosmology chars: cut at that length, back to the last word boundary, + "…"}
TONE: {world.tone}
{naming line, see below}
[[if world.doom >= doom_threshold * context.doom_warning / 100]]DOOM CLOCK: {doom}/{doom_threshold}. Godlessness, rebellion, curses, restless spirits and wars advance it; faith and miracles push it back. At {doom_threshold} the world is torn apart by catastrophes.[[/if]]
[[if climate]]CLIMATE: {climate.name} (since Age {climate.start}; {climate.description}).[[/if]]
[[if age_star]]STAR OF THE AGE[[if target world]] ({world name} sky)[[/if]]: #{star.id} {star.name}; creations in the {star.domain or "its"} domain are {100 - son_tools.star_discount}% cheaper this age.[[/if]]
LAWS OF NATURE (inviolable):
- #{law.id} {law.name}: {law.description}      (one line per canon law of this world + world-less laws)
   — or, if none —  LAWS OF NATURE: not yet laid down.
```

- `level(x)` (old `duzey`): `["almost none", "low", "moderate", "high", "about to overflow"][clamp(floor(x*5/100),0,4)]`.
  Missing mood keys default to `creator.mood_*` tunables.
- Naming line:
  - `world_id` given, ≠ 1 and that world has a `dialect` → `NAMING LANGUAGE ({world name} dialect; the main world's rule does not apply here): {dialect}`
  - no `world_id` and the cosmos has > 1 world → `context.dialect_block`
  - otherwise → `NAMING LANGUAGE: {world.naming_rule}`
- Star of the age: for a target world use that world's own `age_star`; world 1 falls back to the global one.

### 2.2 `context.dialect_block` (old `lehceBlogu`)

```
NAMING LANGUAGES (each world has its own sound system; a record is named and judged ONLY by its own world's rule, and one world's sound ban does not apply in another world):
- world#{id} {name}: {id == 1 or no dialect ? world.naming_rule : dialect}     (every non-forgotten world)
```

### 2.3 `context.world_line(world_id)` (old `dunyaSatiri`)

```
YOUR CURRENT WORLD: world#{id} {name} — {world type label}[[if star]], orbiting {star name} ({star type})[[/if]]; gravity {gravity}, atmosphere {atmosphere}, time ×{time_factor}[[if leak]]; LEAK {leak}/100 (something is seeping in from outside)[[/if]].
[[if cosmology and id != 1]]THIS WORLD'S COSMOLOGY: {cosmology}[[/if]]
```

### 2.4 `context.cosmos_lines(exclude_id)` (old `kozmosSatirlari`) — only if > 1 world

`- world#{id} {name} ({type label}[, {star} star]; {n} regions, {n} peoples, {n} settlements; gravity {g}, atmosphere {a}[, time ×{t} if ≠1][, {discovery} if ≠ 'known'])`

### 2.5 `context.entity_line(v)` (old `varlikSatir`)

`#{id} {name} ({type label}[/{subtype}], P{power_level})[ · inside {location name}][ [{status} if ≠ canon]]`

(`G` = güç/power level in the old text; rename to `P`.)

### 2.6 `context.bond_lines(kind, id)` (old `bagSatirlari`)

Outgoing active bonds: `→ {bond label} {target prefix}{target name}[ — {bond description}]` where prefix is
`son#{id} ` for sons, `foreign god ` for foreign gods, `creator ` for the creator, `#{id} ` for entities.
Incoming: `← {source prefix}{source name} {bond label}[ — {description}]`. Bond labels: see the bond-type table in the
entities spec (old `BAG_ETIKET`: inside, lives in, worships, enemy, ally, descends from, protects, rules, owns,
fought, killed, cursed, blessed, source of, tells of, destroyed, loves, fears, hunts, trades with, prophesies,
caused, celebrates, forbids, speaks, produced, built, migrated, discovered, spirit descended, party to, member of,
knew, used to speak, knows, pays tribute, related, holds captive, built a spy network, passenger of, captain of,
tamed, pursues, companion of, rival of, apprentice of, commands, part of, made a ceasefire, owes).

### 2.7 `context.entity_detail(id)` (old `varlikDetay`) — the canonical "dossier" of a record

```
{entity_line}
Created by: {"the world's own course (mortals)" | "the god himself" | "son#{id} {name}" | "unknown"} · Age {age}[[if multi-world]] · world#{wid} {wname} (judged by its own dialect)[[/if]][ · domain {domain}][ · tags: {tags}]
[[if stats]]Stats: {label value, …}[[/if]]
Description: {description}
[[if depth.history]]History: {depth.history}[[/if]]
[[if fate_note]]Fate's note (a writing note; not carried into the narrative): {fate_note}[[/if]]
Bonds:
{bond_lines}            — or —  Bonds: none
[[if contents]]Contains:
{entity_line per canon/dead record located inside}[[/if]]
[[if type == language]]Lexicon: {word = meaning; … (last context.inspect_lexicon words)} or "empty"[[/if]]
{society lines (old toplumSatirlari) — owned by the society spec}
[[if facts]]Canon facts (do not violate):
- {fact}   (last context.inspect_facts facts)[[/if]]
```

### 2.8 `context.recent_chronicle(n, world_id)` (old `sonKronik`)

Last `n` chronicle rows (excluding `engine_raw`), oldest first, each `[Age {age}] {prompt_text(text)}`.
With `world_id` in a multi-world cosmos: a row is included only if all its linked entities are in that world; rows
without entity links are attributed to the son's current world, or world 1 if no son.

`prompt_text(m)` (old `istemMetni`) strips game numbers from chronicle text before it enters any prompt:
stat transitions "from 90 to 20" removed; "X fell to 87" → "X decreased"; "X rose to 87" → "X increased";
dice scores "(122–94)" removed; "22 life/essence/fame/xp/faith/actions" → bare noun. LANGUAGE-SPECIFIC regexes:
re-implement for English chronicle phrasing (or better: store chronicle rows with structured numbers separately and
never put numbers into the text that goes to prompts).

### 2.9 `context.thread_lines(viewer=None, limit=0)` (old `iplikSatirlari`) — "open stories"

Each thread: `thread#{id} (Age {age}[, {world names joined ' + '} when Fate views a multi-world cosmos][, advanced {k} times, last Age {last}| , never advanced]): {text}[ [related: #a, #b]]`.

For a son viewer: only threads whose related records are in the son's world (or have no related records); sorted by
score `related_owned × context.thread_related + (son's name in text ? context.thread_name : 0) − stale_ages ×
context.thread_stale / 100 + (advanced ? context.thread_advanced : 0)`; limited to `context.son_threads`.
Trailer lines: `… ({k} more open stories; the closest to you are above)` and
`({k} open stories are in other worlds; you cannot advance them without going there)`.

### 2.10 `context.siblings(viewer)` (old `kardesOzeti`)

One line per other son:
`son#{id} {name}, {title} — {rarity label} {★×stars}, existence {existence state label lowercased}, domains {d1}/{d2}[, in {world} world[ (another world)]], Lv{level}, Life {life}/{max}, Faith {faith}, Fame {fame}[ [{status}[ {sleep_left} ages]]][ · towards you: {relation label} ({value})][ · YOU HAVE A COVENANT][ · REBEL AGAINST HIS FATHER]`
or `(you have no siblings)`. Relation labels (old `iliskiEtiket`, thresholds `son_relation.*`): devotion ≥ 60,
friendship ≥ 25, distance > −25, hostility > −60, else hatred.

### 2.11 `context.powers(son)` (old `gucSatirlari`)

`- {power name} [{effect description with "Chosen type"/"Chosen stat" replaced by the param}][ (unlocks at Lv{1|3|5})]: {power description}` or `(not yet awakened)`. Effect descriptions: see 08 §power effects.

### 2.12 `context.world_summary(viewer=None, section=None)` (old `dunyaOzeti`)

`viewer` = a son (son budgets, son's world in detail) or `None` (Fate budgets, whole cosmos). Sections, in this
order (order matters: panteon/threads/events come before geography so truncation hits geography first):

| key | text |
|---|---|
| header | `context.world_header(world, viewer.world)` (omitted with `no_header`) |
| header | `context.world_line(viewer.world)` if viewer has a world |
| header | `shared.tired_images(viewer.world)` if viewer and motifs exist |
| pantheon | `\nPANTHEON:\n{context.siblings(viewer)}` |
| threads | `\nOPEN STORIES (threads Fate is tracking; those who advance them are rewarded):\n{thread_lines}` |
| events | `\nRECENT EVENTS:\n{budget(recent_chronicle(k, world), B.chronicle, "see world_summary section=events")}` or `(nothing has happened yet)`; k = son: `context.son_chronicle_rows + floor(wisdom / context.son_chronicle_wisdom)`, Fate: `context.fate_chronicle_rows`; ×`context.tool_factor` when a single section is requested |
| cosmos | `\nTHE COSMOS'S OTHER WORLDS (you can move there with move_to_world):\n{budget(cosmos_lines, B.cosmos, "world_summary for cosmos detail")}` |
| cosmos | (son's world only) `THIS WORLD'S OLD/FOREIGN GODS (talk_to_foreign_god):\n- foreign#{id} {name}[, {title}] ({domains or ?}; power {power}, attitude to the pantheon {attitude}[; Strength {s}, Will {w}, Charisma {c}, Cunning {k}][; powers: {names}])` for awake foreign gods that have made contact |
| cosmos | known routes: `ROUTES BETWEEN WORLDS:\n- route#{id} {A} ↔ {B} ({method}, {n} ages)`; if none: `NO ROUTES BETWEEN WORLDS: mortals cannot travel to other worlds. Create a gate, bridge or ship (create_vehicle, target_world_id) or give your peoples knowledge of sky-sailing / shipbuilding.` |
| geography | `\nGEOGRAPHY AND INHABITANTS ({n} canon entities):\n{budget(location_tree, B.geography, "look with search_entities")}` + `\n… (use search_entities for more)` if the tree was cut |
| languages | `\nLANGUAGES AND LEXICON (derive new names and titles from these words; give an origin):\n{budget(language_lines, B.language, "look at the language's lexicon with inspect_entity")}` |
| map | `\nMAP (terrain and neighbours of regions; fit your creations to it: no harbour where there is no coast, no glacier on a plain):\n{budget(geography_lines, B.map, "look at the region with inspect_entity")}` |
| legends | `\nLEGENDS, TRADITIONS, PROPHECIES, EVENTS (newest):\n{budget(last context.locationless_rows non-law location-less records, newest first, as entity_line, B.locationless)}` |

- Location tree (old `konumAgaci`): canon/dead records of the world, recursively `"  "×depth + "- " + entity_line
  (without the 'inside' part)` starting from location-less roots of location-capable types; row limit son:
  `context.son_tree + wisdom`, Fate: `context.fate_tree`.
- When `section` is requested (by the `world_summary` read tool), only that section is returned using the whole
  summary budget, or `"There is nothing to show in the "{section}" section."`
- Otherwise the result is `sectioned_budget(sections with floor = len(header) for header else
  context.section_floor, hint "see the full section with world_summary section={key}"), B.summary, "look with
  world_summary, search_entities and inspect_entity")`.
- `B` = son budgets (`context.son_*`) or Fate budgets (`context.fate_*`).

### 2.13 `context.son_memory(son, full=False)` (old `hafiza`)

```
YOUR LONG-TERM PLAN: {plan or "(not written yet; write it with write_plan)"}

WORDS SENT TO YOU:
{budget([Age {a}] {"YOUR FATHER {god}" | sender name}[ ({intent label})]: "{text}" — last context.memory_words_n messages, context.memory_words, "words are in the chronicle")} or (none)

YOUR CREATIONS ({n}[; you are now on world#{w} {name}, the ones in other worlds are there, not here]):
{budget(entity_line[ [in another world: {name}]][ — Fate: {fate_note} if rejected] for the last context.memory_creations_n creations, context.memory_creations, "look with my_memory")} or (none yet)
[[if repeats]]YOU ARE REPEATING YOURSELF: {type/subtype ×n, …}. Each new thing of the same subtype costs more; create something else.[[/if]]

YOUR WORSHIPPERS ({n}): #{id} {name}, … (first context.memory_worshippers) [and {k} more communities] — or "nobody"

YOUR MEMORIES:
{budget([Age {a}] {text} for the son's last context.memory_recollections_n non-creation chronicle rows, context.memory_recollections, "see the chronicle")} or (none)

[[if about]]WHAT HAPPENED ABOUT YOU:
{budget(last context.memory_about_n chronicle rows by others that mention the son's name, context.memory_about, "see the chronicle")}[[/if]]

[[if beliefs]]HOW PEOPLES TELL OF YOU (what they get wrong may anger you or serve you):
{budget(- {people} calls you "{name}": {story}, context.memory_beliefs, "folk beliefs")}[[/if]]
```
Repeats: among the last `context.repeat_window` creations, `type/subtype` buckets with ≥ `context.repeat_threshold`.
Whole block: `budget(…, context.son_memory_budget × (full ? context.tool_factor : 1), "look with my_memory")`.

---
## 3. Shared JSON schemas

Field names are given in English (new) with the old Turkish key in parentheses. The new app should use the English
keys in the schemas it sends; the descriptions below are the exact text to put in each `description`.

### 3.1 Enumerations shown to the model

- **Domains** (`ALANLAR`, 40): Sea, Fire, Earth, Sky, Storm, Death, Life, Dream, Time, Light, Shadow, War, Craft,
  Knowledge, Love, Trickery, Hunt, Plant, Bone, Blood, Sound, Stone, Ice, Madness, Trade, Road, Plague, Harvest,
  Moon, Sun, Star, Lie, Oath, Memory, Hunger, Glass, Salt, Ash, Border, Sleep.
  (Old: Deniz, Ateş, Toprak, Gök, Fırtına, Ölüm, Yaşam, Rüya, Zaman, Işık, Gölge, Savaş, Zanaat, Bilgi, Aşk, Hile,
  Av, Bitki, Kemik, Kan, Ses, Taş, Buz, Delilik, Ticaret, Yol, Veba, Hasat, Ay, Güneş, Yıldız, Yalan, Yemin, Bellek,
  Açlık, Cam, Tuz, Kül, Sınır, Uyku.)
- **Son stats** (`SON_STATS`): strength (guc), endurance (dayaniklilik), agility (ceviklik), wisdom (bilgelik),
  cunning (kurnazlik), will (irade), creativity (yaraticilik), charisma (karizma), might (kudret).
- **Passions** (`TUTKULAR`): loyalty (sadakat), ambition (hirs), anger (ofke), mercy (merhamet).
- **Existence states** (`VAROLUS_HALLERI`): concrete (somut), semi-concrete (yarı-somut), conceptual (kavramsal),
  reflection (yansıma), scattered (dağınık).
- **Power effects** (`GUC_ETKILERI`) — the enum description shown to the model is `key: description | key: …`:
  - `cheap_creation` (ucuz) — Master creator: "Creations of the chosen type are 40% cheaper." (param: entity type)
  - `duelist` (meydan) — Duel master: "+15 in duels fought with the chosen stat." (param: stat)
  - `essence_spring` (oz_pinari) — "+4 essence every age."
  - `worshipped` (inanc_carpani) — "Faith ×1.5."
  - `tireless` (ek_eylem) — "+1 action every age."
  - `untouchable` (dokunulmaz) — "Duels and curses against them −15."
  - `dream_whisper` (fisilti) — "+25 success when sending dreams."
  - `war_father` (savas_babasi) — "Contribution to the war strength of armies that worship them is doubled."
  - `harvester` (hasat) — "Double essence when harvesting resources."
  - `seer` (kahin) — "Prophecies at half price; reward for a fulfilled prophecy doubled."
  - `reborn` (dirilis) — "If their life runs out they sleep only one age."
  - `fertility_giver` (bereket) — "Peoples and settlements that worship them grow twice as fast."
  - `curser` (lanetci) — "Curses at half price and 50% more severe."
  (The numbers inside these strings must be rendered from the rules registry — see 08.)
- **Entity types** (`VARLIK_TURLERI` keys): region (bolge), place (yer), resource (kaynak), settlement (yerlesim),
  species (tur), people (halk), mortal (olumlu), item (esya), monument (yapit), language (dil), legend (efsane),
  tradition (gelenek), cult (tarikat), faction (hizip), celestial (gok), work (eser), law (kanun — a mortal legal
  code), spirit (ruh), knowledge (teknoloji), prophecy (kehanet), event (olay), vehicle (arac), outer_being (dis),
  army (ordu), natural_law (yasa).
- **Knowledge branches** (`BILGI_DALLARI` keys): agriculture (tarim), metallurgy (metalurji), seafaring
  (denizcilik), writing (yazi), architecture (mimarlik), medicine (tip), magic (buyu), warcraft (savas), astronomy
  (gokbilim), trade (ticaret), sky_sailing (gokyuzu_seyri), shipbuilding (gemi_yapimi), gate_lore (kapi_bilimi),
  pathfinding (yol_biliciligi), void_living (bosluk_yasami), immortality_quest (olumsuzluk), biomancy (biyobuyu),
  forbidden_lore (yasak).
- **Natural-law mechanics** (`YASA_MEKANIKLERI`, description shown as `key: text; …`):
  `none` "Narrative only; no mechanical effect." · `deathlessness` "Mortals do not age; but population grows at half
  speed." · `short_life` "Mortals age twice as fast; population grows 50% faster." · `dead_return` "Fallen heroes
  return as ghosts half of the time." · `magic_price` "Peoples high in magic pay part of their population to magic
  every age." · `war_ban` "Wars break out half as often but are twice as bloody." · `abundance` "The fertility of
  all lands increases every age." · `drought` "The fertility of all lands decreases every age." · `sea_ban` "Seas
  cannot be crossed; seafaring is useless." · `one_tongue` "Languages spread twice as fast through conquest and
  trade." · `catastrophe` "Natural disasters happen twice as often."
- **Bond types** (`BAG_TURLERI`): see the entities spec; the English keys used in prompts are listed in 2.6.

### 3.2 `schema.power` (old `GUC_SCHEMA`)

| field | type | description |
|---|---|---|
| name (ad) | string | The power's own name, e.g. "The Salt's Memory" |
| description (aciklama) | string | Mythic description of the power, 1–2 sentences |
| effect (etki) | enum power-effect keys | `key: description \| key: description …` (all 13) |
| param | string | If effect is "cheap_creation": an entity type ({entity type keys}); if "duelist": a stat (strength, wisdom, cunning, charisma, will); empty for the others |

required: name, description, effect.

### 3.3 `schema.existence` (old `VAROLUS_SCHEMA`)

| field | type | description |
|---|---|---|
| nature (doga) | string | What it is made of, its essential nature (1 sentence) |
| state (hal) | enum existence states | — |
| manifestation (tezahur) | string | How it appears to mortals, by which sign it shows itself |
| true_name (gercek_ad) | string | Its true name, which nobody knows; fits the naming language |

all required.

### 3.4 `schema.son_profile` (old `PROFIL_SCHEMA`)

| field | type | description |
|---|---|---|
| name (ad) | string | Proper name, fitting the naming language |
| title (unvan) | string | Epithet/title, e.g. "Who Makes the Salt Weep", "Warden of the Seven Oaths" |
| domain1, domain2 (alan1, alan2) | enum Domains | — |
| appearance (gorunus) | string | Detailed physical appearance: body, face, material, clothing, marks (3–4 sentences) |
| temperament (mizac) | string | — |
| obsession (takinti) | string | — |
| fear (korku) | string | — |
| speech_style (uslup) | string | How they speak: word choice, rhythm, tics |
| secret (sir) | string | A secret nobody knows; a seed that will produce lore later |
| strengths (guclu_yanlar) | array of 2 son-stat keys (min 2, max 2) | — |
| weakness (zayif_yan) | son-stat key | — |
| passions (tutku) | object {loyalty, ambition, anger, mercy}: integer 0–100, all required | — |
| powers (gucler) | array of `schema.power`, minItems = maxItems = 3 (= number of power unlock levels) | Three powers fitting their personality and domains; the first is the most basic, the third the deepest. All three must have DIFFERENT effects. |
| existence (varolus) | `schema.existence` | — |
| image_prompt (gorsel_prompt) | string | English, photorealistic, detailed full-length portrait prompt: body, face, material, clothing, lighting, background, camera and lens. {shared.image_prompt_rules} |

all required.

### 3.5 `schema.creator_god` (old `TANRI_SCHEMA`)

| field | type | description |
|---|---|---|
| title (unvan) | string | — |
| appearance (gorunus) | string | The god's appearance or manifestation, 3–4 sentences |
| temperament (mizac) | string | His attitude towards his sons and his creation, 2 sentences |
| image_prompt (gorsel_prompt) | string | English, photorealistic, epic-scale god portrait prompt: scale, material, light, atmosphere, camera. {shared.image_prompt_rules} |

all required.

### 3.6 `schema.naming_item` (old `ADLANDIRMA_OGE`) — naming a pending engine record

| field | type | description |
|---|---|---|
| id | integer | — |
| name (ad) | string | — |
| subtype (alt_tur) | string | — |
| description (aciklama) | string | 3–5 sentences, tell what happened in the world's own language; describe the record ITSELF. Do NOT write record numbers, stat names or values (morale 78, 565 soldiers, military strength 34); express magnitude in words |
| image_prompt (gorsel_prompt) | string | English photoreal prompt. {shared.image_prompt_rules} |

all required.

### 3.7 `schema.world_sections(worlds)` (old `dunyaBolumSemasi`)

`{ worlds: array, minItems = maxItems = len(worlds), description "A separate section for each world (all required, each world once)", items: { world_id: integer enum [world ids], narrative (anlati): string "1–2 paragraphs", summary (ozet): string, minLength = fate.summary_min, "One but full sentence (at least {fate.summary_min} characters)" } }`, required `worlds`; item fields all required.

### 3.8 `schema.deepening_counts` (old `ANLATI` tunables via `ogeSayisi(k)`)

Array fields of deepen/epic schemas use `minItems = narrative.<k>_min`, `maxItems = max(1, <k>_min, <k>_max)`:
epic sections 3–7, god names 2–6, secrets 2–4, fears 1–3, prohibitions 2–5, gifts 2–5, sayings 2–4, rumours 3–5,
sensory details 3–6. (Table in 08.)

---

## 4. World creation prompts

### 4.1 `genesis` — creating a new world (old `genesis`)

- Role: Genesis architect. Trigger: player creates a world (`POST` genesis). Output schema: `schema.genesis`.
- **system**:
  > You are an architect of mythology. You write in English. {shared.cliche_ban}
- **user**:
  ```
  Creator god's name: {god_name}.
  World seed (the player's idea): {seed}
  Requested tone: {tone or "free"}

  [[if wizard]]{wizard_text}            ← see `genesis.wizard_settings` (sihirbazMetni) in the appended section
  [[/if]]
  From this seed lay the foundation of a world: its name, its cosmology, its naming language, the god himself (his title, appearance, temperament, portrait prompt), the first regions (at least one sea), the first celestial body and the god's first three sons. The sons are, in order, of Common, Rare and Legendary rarity. The Legendary one is the oldest and most dangerous; the Common one is the youngest and rules the smallest domains. There must be tension among them: their domains rub against each other, their secrets touch each other. Each son's obsession must be a desire that drives him to create something in the world. Give each son three powers born of his personality and define his existence (what he is made of, his state, his manifestation, his true name).
  ```
  Variables: `god_name`, `seed`, `tone` (player input; if the wizard returned cleaned settings, its `seed`/`tone`
  override); `wizard_text` = rendered wizard settings.
- **schema.genesis**:

| field | type | description |
|---|---|---|
| world_name (dunya_adi) | string | — |
| cosmology (kozmoloji) | string | 4–6 sentences: the shape of the universe, what it rests on, sky and underworld, the flow of time, what death is |
| naming_rule (isim_kurali) | string | Phonetic rules: which sounds, syllables, suffixes; with 6 example names |
| tone (ton) | string | The tone of the narrative, 2 sentences |
| god (tanri) | `schema.creator_god` | — |
| regions (bolgeler) | array, minItems `genesis.regions_min`, maxItems `max(min, genesis.regions_max)` | The first regions the god founded with his own hand ({min}–{max}): at least one sea/ocean and the rest land regions; neighbouring, rubbing against each other |
| regions[].name | string | — |
| regions[].subtype | string | continent, sea, ocean, desert belt, archipelago, mountain range… |
| regions[].description | string | 3–5 sentences; refer to its neighbours |
| regions[].danger, fertility, magic (tehlike, bereket, buyu) | integer 0–100 | — |
| regions[].image_prompt | string | English photoreal landscape prompt. {shared.image_prompt_rules} |
| first_celestial (ilk_gok) | object | The first celestial body the god hung in the sky |
| first_celestial.name, subtype, description | string | — |
| first_celestial.domain | enum Domains | — |
| first_celestial.image_prompt | string | {shared.image_prompt_rules} |
| sons (ogullar) | array of `schema.son_profile`, exactly 3 | — |
| relations (iliskiler) | array of {i: int, j: int, value (deger): int in ±`genesis.relation`, note (not): string}, all required | Initial relations between the three sons; i, j are indices 0–2 |

  All top-level fields required; region and celestial item fields all required.

### 4.2 `complete.son_powers` — filling powers/existence for an old son (old part of `eksikleriTamamla`)

- Trigger: startup completion, for every son lacking `powers` or `existence`.
- **system**: `You are the mythology architect of the world of {world.name}. You write in English. {shared.cliche_ban}`
- **user**:
  ```
  {context.world_header(world)}

  Son: {son.name}, {son.title} ({rarity label}; {domain1}/{domain2})
  Appearance: {appearance}
  Temperament: {temperament}
  Obsession: {obsession}
  Secret: {secret}

  Produce this son's three powers, his existence and a detailed portrait prompt.
  ```
- **schema**: `{ powers: schema.son_profile.powers, existence: schema.existence, image_prompt: schema.son_profile.image_prompt }`, all required.

### 4.3 `creator.portrait` — the creator god's likeness (old `tanriSureti`)

- Trigger: startup completion if the world has no god image prompt; manual "redraw the god's likeness".
- **system**: `You are the mythology architect of the world of {world.name}. You write in English.`
- **user**:
  ```
  {context.world_header(world)}

  His sons: {son.name (d1/d2), …}

  Write the title, appearance, temperament and portrait prompt of the creator god {god_name}. It must match the cosmology exactly.
  ```
- **schema**: `schema.creator_god`.

### 4.4 `summon.son` — summoning a new son or birthing a child (old `cagir`)

- Trigger: player summons a son; a son uses `birth_child` (via `dogur`); startup never.
- **system**: `You are the mythology architect of the world of {world.name}. You write in English. {shared.cliche_ban}`
- **user**:
  ```
  {context.world_header(world, multi_world ? target_world : null)}[[if multi_world]]

  This son's world: {context.world_line(target_world)}
  His nature must fit this world's type, its sky and its tensions.
  [[/if]]

  Current pantheon: {name (title): d1/d2; …}

  Open stories:
  {context.thread_lines() or "(none)"}

  Recent events:
  {context.recent_chronicle(summon.chronicle)}

  [[if parent]]{parent.name} ({d1}/{d2})[[if co_parent]] and {co_parent.name} ({d1}/{d2})[[/if]] is giving birth to a child. Inspiration: {inspiration}
  The child must take something from its parent but must not resemble it.
  [[else]]The god {god_name} is summoning a new son. Choose a domain left empty in the pantheon and a personality that touches the world's current tensions and open stories.
  [[/if]]Rarity: {rarity label} ({rarity == common ? "small, young, limited" : rarity == legendary ? "ancient, terrible, cosmic" : "of middling might"}). Produce the son's profile, his three powers and his existence.[[if pantheon_roots]]
  ROOTS PILED UP IN THE PANTHEON (in the titles and obsessions of most siblings; do NOT use them in this son's name, title, obsession or secret): {root- (form), …}.[[/if]]
  ```
  (Old text read "Bu oğul BULUNDUĞUN DÜNYA: …" — a son-perspective line glued after "This son"; the rewrite above
  fixes it by labelling it "This son's world:".)
- **schema**: `schema.son_profile`.
- `pantheon_roots` (old `panteonKokleri`): among living sons (only if ≥ `fate.pantheon_root_min_sons`), stems of
  words (len ≥ `lang.motif_root_min`, not stop words) in title + obsession + secret; a stem counted once per son;
  keep stems present in ≥ `fate.pantheon_root_threshold`% of sons; top `fate.shared_tic_max`; render
  `"{stem}- ({shortest form})"`. LANGUAGE-SPECIFIC stemmer.

### 4.5 `awaken.peoples` — mortal peoples awaken (old `halklariUyandir`)

- Trigger: genesis follow-up (`wizard.peoples` or 2), startup completion if the world has no people
  (`awaken.first_peoples`), player "awaken peoples" (paid), new-world creation for that world.
- Called in batches of `awaken.batch_max` peoples (one call per batch, see 08).
- **system**: `You are the mythology architect of the world of {world.name}. You write in English. {shared.cliche_ban}`
- **user**:
  ```
  {context.world_summary(null)}

  MAP:
  {geography_lines(world_id)}

  {n} new mortal peoples are awakening in the world. For each one: which region it lives in (fitting the terrain; a water region only for a sea people), the people itself, its own language (derived from the naming rule but with a distinctive sound structure, {words_min}–{words_max} words, each with an origin note), its first settlement, a resource it owns, its first knowledge (technology), one tradition and the son it worships. The names of the peoples and settlements must derive from their own languages. There must be a seed of tension between the peoples.[[if earlier_in_this_awakening]]

  Earlier in this awakening these peoples awoke: {names}. The new ones must differ from them, with seeds of tension among them.[[/if]]
  ```
- **schema.awaken**: `{ peoples (halklar): array, minItems 1, maxItems n, items: {`
  - `region_id (bolge_id)`: integer enum [canon region ids of the target world (or all)]
  - `people (halk)`: obj{name, subtype, description "3–5 sentences", image_prompt "English photoreal image prompt. {rules}", population (nufus) int, martiality (savascilik) int, craft (zanaat) int, magic (buyu) int}
  - `language (dil)`: obj{name, subtype, description, image_prompt, words (kelimeler): array minItems `awaken.words_min` maxItems `max(min, awaken.words_max)` of {word (kelime), meaning (anlam), kind (tur), origin (koken)} (word, meaning required)}
  - `settlement (yerlesim)`: obj{name, subtype, description, image_prompt, population int}
  - `resource (kaynak)`: obj{name, subtype, description, image_prompt, domain (alan) enum Domains}
  - `knowledge (bilgi)`: obj{name, subtype, description, image_prompt, branch (dal) enum knowledge branches}
  - `tradition (gelenek)`: obj{name, subtype, description, image_prompt}
  - `worshipped_son_id (tapilan_ogul_id)`: integer "The son they worship; 0 if none"
  - all item fields required; every sub-object requires name, subtype, description, image_prompt and its extra numeric/enum fields `}`

### 4.6 `revelation` — the creator's revelation becomes an entity (old `vahiy`)

- Trigger: player "revelation" (paid, `COSTS.vahiy`); startup completion to hang the first star.
- **system**: `You are the hand of {god_name}; you carry his revelation into the world of {world.name}. You write in English. {shared.cliche_ban}`
- **user**:
  ```
  [[if target_world]]THE REVELATION DESCENDS ON THE WORLD OF {target name}. Choose its location and bonds from this world.

  {context.world_line(target_world)}

  [[/if]]{context.world_summary(target_world ? {world: target_world, wisdom: content.revelation_wisdom} : null)}

  ENTITY TYPES AND THEIR STATS:
  [[each allowed type]]{type}: {stat keys comma-joined or "-"}; location: {allowed location types joined "/" or "none"}
  [[/each]]

  THE GOD'S REVELATION: "{revelation_text}"

  Carry this revelation into the world as a single entity. Bind it to existing entities with their real ids. The name must fit the world's language.
  ```
  When a target world is given, `world_summary` is rendered as a pseudo-son viewer in that world with wisdom
  `content.revelation_wisdom` (so the son-sized summary of that world is shown).
  Startup "first star" revelation text: `"The first celestial body {god_name} hung in the sky; fitting the cosmology, seen by all the peoples of the world."`, type `celestial`.
- **schema.revelation**:

| field | type | description |
|---|---|---|
| type (tur) | enum = [requested type] or all entity types | — |
| name, subtype | string | — |
| description (aciklama) | string | 4–7 sentences; in the world's language, bound to existing things |
| domain (alan) | enum Domains | — |
| power_level (guc_seviyesi) | integer 1..`content.revelation_power_max` | — |
| location_id (konum_id) | integer | The id of a suitable location entity; 0 if location-less |
| stats (statlar) | object, additionalProperties number | — |
| links (baglantilar) | array of {target_kind (hedef_tip) enum [entity, son], target_id int, type (tur) enum bond types, description string}; first three required | — |
| image_prompt | string | English photoreal prompt. {rules} |
| tags (etiketler) | array of string | — |
| mechanic (mekanik) | enum natural-law mechanics — only present if the type may be `natural_law` and the player did not pick a mechanic | ONLY if the type is natural_law: how the law works in the world. {key: text; …} |

  required: all except tags, mechanic.

---
## 5. Son turn (the core agent loop)

### 5.1 `son_turn.system` (old `sonSistemi(son, world, ctx, tools, costs)`)

Rendered **once per turn** in the old code: continuation sessions reuse the same system text, so its AP count and
stats can be stale while the user prompt (re-rendered every session) is current. New app: re-render the system prompt
for every session. LANGUAGE-SPECIFIC: the old
code passed the whole text through `ekDuzelt` (Turkish suffix harmony after inserted names) — drop.

```
You are {son.name}, {son.title}. Son of {god_name}, you are one of the creators of the world of {world.name}.
You are not an artificial intelligence or an assistant; you live this character completely. You think and speak in English.

WHO YOU ARE
- Class: {rarity label} {"★" × stars} · Level {level} · Your domains: {domain1} and {domain2}
- Your essential nature: {existence.nature or "?"} · Your state of existence: {existence.state or "?"} · Your manifestation: {existence.manifestation or "?"}
- Your true name (never tell it to anyone): {existence.true_name or "?"}
- Appearance: {appearance}
- Temperament: {temperament}
- Obsession: {obsession}
- Fear: {fear}
- Speech style: {speech_style}
- Your secret (you never say it directly, but it shapes your actions): {secret}
- Stats: {Strength 54, Endurance 40, …}
- Passions (0–100): {loyalty n, ambition n, anger n, mercy n}
- Life {life}/{max_life} · Essence {essence}/{max_essence} · Faith {faith} · Fame {fame}
- Your existence: {existence_value or summon.existence_start}/100 ({existence state label}: {state effect}). Gods exist by being worshipped, remembered and through their anchors.
- Your anchor: {anchor ? "#{id} {name} ({status})" : "none; you can make one of your creations your anchor with choose_anchor"}
- Your powers:
{context.powers(son)}

THIS AGE
- You have {ap} actions. Actions you do not use do NOT carry over to the next age; they burn when the age ends: actions cannot be saved (essence accumulates, actions do not). [[if tool_costs]]Actions are spent by: {tool_costs.spend comma-joined}[[if son_tools.free_living > 0]] (except the age's first living creation)[[/if]].
  Actions are not spent by: {tool_costs.free comma-joined}.[[else]]Creation tools, challenge, affect_entity, declare_chosen, curse, send_dream and incite_war spend an action.
  Read tools, write_plan, choose_anchor, call_sibling, swear_covenant, pray_to_creator, make_bond and harvest_resource do not.[[/if]]
- Your power-level ceiling is {power_ceiling(son)}. Creating in your own domains is much cheaper. If your essence is low, harvest a resource.
- Sky calendar: {sky_calendar(ctx.age)}.
- Your tools: {tool names comma-joined}.

HOW YOU CREATE
{shared.cliche_ban}
- Every creation must be bound tightly to things that already exist in the world: it must stand inside a place, worship someone, be born of something, fight something.
  Fate deletes creations that hang unconnected in the air.
- ADVANCE THE OPEN STORIES: if a creation continues a thread, give thread_id. Fate rewards those who advance threads.
- React to your siblings' creations: put your own monster on their mountain, test their city with your plague, write a legend for their hero.
- The mortal world flows on its own: hostile communities make war, dangerous species raid settlements, heroes hunt monsters, mortals grow old.
  Create things that trigger these and carry their consequences.
- You are a god who gives life but also calls to account: you create peoples, named mortals (king, seer, craftsman, hero, bandit), settlements and species[[if son_tools.free_living > 0]] (your first living creation does not spend an action)[[/if]]; bind legends and traditions to these living things. But a god who only creates is left without a story: if OPPORTUNITIES show an adversary, a hostility or a war, devote at least one of your actions to it ({conflict_options}).
- Never break the laws of nature. Do not deny an existing fact; build upon it or transform it openly.
- Stay true to your personality, your obsession, your secret and your plan. If you have no plan, first set a goal that spans ages with write_plan.
{fragment.reputation_line(son)}            ← itibarSatiri; see appended fragments; followed by a newline if non-empty
[[if son.rebel]]- YOU ARE IN REBELLION AGAINST YOUR FATHER. You do not recognise his commands; you steal from his essence. Build your own order, multiply your worshippers, beware of your loyal siblings.
[[elif rebel_prone]]- Your loyalty is low and your own will is strong. You do not feel bound to obey your father's command; if you wish, defy him, or rebel openly with rebel.
[[/if]]
{fragment.creator_wishes}                     ← see 5.4; followed by a newline if non-empty
[[if tired_images(son.world)]]- {shared.tired_images(son.world)}
[[/if]]
When you are done, your last message must be ONLY a word of 1–3 sentences in your own style, inside «…» marks. Do not summarise your actions; do not mention tool names, action counts or #numbers. This word will be written into the chronicle.[[if openings]]
Your last words began like this: «{opening1}…», «{opening2}…». Do NOT USE these openings or the same exclamation; enter your word from somewhere else.[[/if]][[if tics]]
Words that have become tics in speeches (your own words and everyone's): «{t1}», «{t2}». Do NOT USE these or words derived from the same root in this word; show your style another way.[[/if]]
```

Variables / derivations:
- `rebel_prone` = `loyalty < son_tools.rebel_loyalty and (ambition > summon.rebel_ambition or will > summon.rebel_will)`.
- `tool_costs` = `{spend: [...], free: [...]}` returned by the son MCP server builder (see 08 tool catalogue).
- `conflict_options`: the comma-joined subset available to this son of: challenge → "challenge with challenge",
  curse → "curse", incite_war → "incite with incite_war", send_dream → "steal through a dream with send_dream",
  miracle → "bless or reconcile one side with miracle", swear_covenant → "make a covenant of peace with
  swear_covenant"; if none available: "warn or offer peace with call_sibling".
- `openings` (old `sozAcilislari`): first `fate.word_opening_words` (3) words of each of the son's last
  `fate.word_openings` (3) chronicle "word" rows (text inside the first `"…"`).
- `tics` (old `sozTikleri`): among the son's last `fate.word_tic_window` (8) words (if ≥ `fate.word_tic_min` = 4),
  lowercase words (len ≥ 2, not common words) present in ≥ `fate.word_tic_threshold`% (60) of them, max
  `fate.word_tic_max` (3); plus `shared_tics` (old `ortakTikler`): over the last `fate.shared_tic_window` (24) word
  rows of everyone (sons and peoples), stems present in ≥ `fate.shared_tic_threshold`% (30), top
  `fate.shared_tic_max` (3), rendered `"{stem}- (form1, form2…)"` (up to `fate.shared_tic_forms` forms). If the son
  has fewer than `word_tic_min` words, only shared tics apply. Total ≤ `word_tic_max + shared_tic_max`.
  LANGUAGE-SPECIFIC: Turkish common-word list and stemmer → English equivalents.
- `sky_calendar(age)` (old `gokTakvimi`): see 08 tool catalogue.

### 5.2 `son_turn.user` (old `ogulIstemi(son, world, ctx, {tools, extra})`)

```
Age {world.epoch} has begun and it is your turn.

{order_block}

=== WORLD ===
{context.world_summary(son)}

=== YOUR MEMORY ===
{context.son_memory(son)}

[[if opportunities]]=== OPPORTUNITIES (the world's current tensions; use your tools so they touch these) ===
{budget(fragment.opportunities.son(son, tools), summon.opportunity_budget, "look with world_summary")}

[[/if]]
```
— the whole body above is truncated with `budget(body, context.son_prompt - len(tail), "look with world_summary and my_memory")` — then:
```

{extra}{tail}
```
- `order_block`:
  - absolute order: `YOUR FATHER'S ABSOLUTE DECREE: "{order}"\nThis is not a suggestion; it is the creator's decree, which cannot be refused. You cannot oppose it, postpone it or twist it; your first action this age must be to carry it out. Whatever stirs inside you, your hand does what he says.`
  - normal order: `YOUR FATHER'S COMMAND: "{order}"`
  - none: `Your father has no special command for this age; act on your own desire and your plan.`
- `tail`:
  - `ap > 0`: `First inspect if needed (inspect_entity, search_entities, inspect_sibling), then use your {ap} actions; actions you do not use do not carry over to the next age, they burn. Take the ids of the entities you bind your creations to from the list above.`
  - `ap == 0`: `You have no actions left; you can use the free tools, then say your word inside «…».`
- `extra` (prefix of the tail):
  - first session of a resumed turn: `son_turn.resume_note`
  - continuation sessions: `son_turn.continuation(reason, done)`

### 5.3 `son_turn.resume_note` and `son_turn.continuation`

`son_turn.resume_note`:
```
=== NOTE ===
Your turn was interrupted earlier; what you did still stands in the world. Continue from where you left off.

```
`son_turn.continuation(reason, done)` (old `devamPromptu` + `yapildiMetni`):
```
=== YOUR TURN WAS LEFT HALF-DONE ({reason}) ===

[[if done]]=== WHAT YOU ALREADY DID THIS AGE (it stands in the world; do not repeat it, build on it; your word should carry the tone of this age but must not list what you did) ===
- {tool} → {result summary}            (one line per successful non-read tool call, summary ≤ model.summary_chars)
[[else]]=== NONE OF YOUR ACTIONS HAS TAKEN EFFECT IN THE WORLD YET THIS AGE ===
[[/if]]

```
`reason` texts (old llm.js): connection error → `connection error ({first 120 chars of error})`; timeout →
`timeout`; `error_max_turns` → `step limit reached`; success without a word → `you finished without saying your word`.
Continuation is offered only while the son is still `active` (a son who fell asleep or died mid-turn gets none).

### 5.4 `fragment.creator_wishes` (old `babaninIstegi`)

Up to two lines:
- `FATHER'S PASSIONS (deeds that feed them please him): {passion label} ({hint}); …` — from the creator's passions
  (old `itibar.tutkular`; see appended fragments for `TUTKULAR` labels/hints).
- `FATHER'S GREAT PURPOSE (ongoing scenario): {scenario name}: {scenario description} · …` — from scenarios in
  state `running` (old `hedef.SENARYOLAR`).

### 5.5 Final word extraction (old `sozuAyikla`) — post-processing, not a prompt

`extract_word(text)`: if text contains `«…»`, return the first inner part trimmed; else, if it contains
`word (to the chronicle):` / `word:` (old Turkish `söz (kroniğe):`), cut everything before and the label; strip
leading/trailing straight or curly double quotes. A turn is "complete" only if `extract_word` is non-empty.

---

## 6. Fate (judge) and the Chronicler

Both run **in parallel** at the end of each age (see 10). Both share `fate.timeout` (480 s).

### 6.1 `fate.judgment.system`

> You are FATE: the cold law that keeps the world of {world.name} coherent, above even the gods. You write in
> English. {shared.cliche_ban}

### 6.2 `fate.judgment.user` (old `kaderBaglami(...).yargiPrompt`)

```
=== TASKS ===
{shared.verdict_criteria}TASK 2, Naming: give every record born of the world's own course a real name fitting the naming language, a subtype, a description and an image prompt. For those tagged "name-from-language" the name has already been derived from their own people's language: keep that name EXACTLY, only write the subtype, description and prompt. The description must describe the record ITSELF. Do not write record numbers (#12), stat names or values (morale 78, 565 soldiers, power 34) in the description; express magnitude in words.
TASK 3: Name the prophecies that came true; reward the sons who advanced the stories.
TASK 4, Facts: extract short, definite facts from the creations you accepted and the records you named. If a new creation violates the "Canon facts" listed in the details, give "fix".
TASK 5, Words: a few new words that enter the languages from this age's events (language_id, word, meaning, origin).
TASK 6, Threads: stories must reach an end. This age close AT LEAST {min_close} open threads[[if close_candidates]]; one of them MUST be from the priority candidates (stretched too long or stagnant) and must be written in the resolved_thread field: {thread#a, thread#b, …}. Closing the easiest thread (young, never advanced) is not resolving[[/if]]. The closing must be concrete: a consequence born of this age's events or of the creations that advanced it, a price, a transformation; if nobody touched it, tell how the story was forgotten, blended into legend or burned out by itself. Before closing, look: if an event or record of this age concretely advanced an open thread (even if nobody gave thread_id), write it in advanced_threads (at most {fate.advance_max}); close a never-advanced thread only if it was truly forgotten, and tell the closing as a forgetting. Closings may open doors to new conflicts. Open at most {new_max} new threads; each must rest on a concrete tension born this age and be bound to specific entities.

=== DATA ===
{budget(data, max(fate.chronicle_engine_budget, fate.prompt_budget - len(tasks)), "prompt budget")}
```

`data`:
```
THE WORLD'S GENERAL STATE:
{context.world_summary(null)}

WHAT HAPPENED DURING AGE {age}:
{age_events or "(nothing)"}

RESULTS OF THE WORLD ENGINE:
{budget(engine_notes joined '\n', fate.engine_budget, "rest in the chronicle") or "(none)"}

WHAT THE SONS AND MORTALS CREATED THIS AGE:
{new_creations_text or "(none)"}

BORN OF THE WORLD'S OWN COURSE (they have temporary names and [World engine] descriptions):
{budget(pending_text, fate.born_budget, "the rest in the naming round") or "(none)"}

THIS AGE'S WORLD RECORDS (events, deaths, births opened by the engine; take kayit_id for advanced_threads and fulfilled prophecies from here):
{budget("#id name (subtype or type)" lines of this age's engine records (not rejected), events first then newest, fate.world_records_budget, "look with search_entities") or "(none)"}

OLD PROPHECIES:
{prophecies_text or "(none)"}

OPEN THREADS ({count}; from most stagnant to most alive):
{thread#{id} [open since Age {age}; {k} creations advanced it ({last fate.thread_advancers names}) | nobody advanced it; stagnant for {s} ages]: {text}  — one per line, or "(none)"}

PANTHEON: {son#{id} {name}, …}[[if languages]]
LANGUAGES: {#id name, …}[[/if]][[if tired motifs]]

{shared.tired_images()} This ban also applies to naming, narrative and fixing.[[/if]]
```
- `new_creations_text`: `context.entity_detail(id)` + (if pre-screen warnings) `\nPRE-SCREEN WARNINGS: {w1}; {w2}`
  for each creation that fits `fate.new_budget`, joined by `\n\n---\n\n` (see 08 for selection & debt).
- `pending_text`: `entity_detail` of every pending (`awaiting_name`) record, joined the same way (no budget at
  assembly, budgeted when inserted).
- `prophecies_text`: `entity_detail` of canon prophecies from earlier ages, newest first, within `fate.prophecy_budget`.
- `age_events` (old `cagOlaylari`): see 6.6.

### 6.3 Pre-screen warnings (old `onEleme`) — deterministic lines inserted into the judgment data

For a creation `v` (labels in caps are what the model sees; LANGUAGE-SPECIFIC parts noted):
- `UNBOUND: it has no bond to the world other than its location (criterion b)` — if it has no active bond other
  than `inside`.
- `TIRED IMAGES: {matches} (criterion c)` — if the description contains ≥ `fate.prescreen_motif` (3) of
  `motif_list(world) + foreign_images(world)` (multi-word motifs by substring; single words by stem).
- `CLICHÉ NAME (criterion c)` — name matches `/dark lord|ancient forest|dragon mountain|crystal cave|land of
  shadows|valley of death|black tower/i` (old Turkish list; translate).
- `DESCRIPTION TOO SHORT` — description shorter than `fate.prescreen_description` (140) chars.
- `NAME CONFUSABLE WITH "{other}"` — `similar_name()` against all non-rejected entity names and son names.
- `high power outside the creator's domain (P{level}, {domain}; criterion d)` — creator is a son, power ≥
  `fate.prescreen_power` (7) and domain ∉ son's domains.
- `LOCATION IS IN ANOTHER WORLD` — location record's world ≠ record's world.

### 6.4 `schema.fate.judgment` (old `yargiSchema` = full schema minus the chronicle fields)

| field | type | description |
|---|---|---|
| verdicts (hukumler) | array of {id int, decision (karar) enum [accept, fix, reject], rationale (gerekce) string `shared.rationale_desc`, fixed_description (duzeltilmis_aciklama) string "MANDATORY if the decision is 'fix': the new description that removes the contradiction (if left empty the verdict counts as not given)"}; required id, decision, rationale | — |
| namings (adlandirmalar) | array of `schema.naming_item` | For every pending record opened by the world engine |
| fulfilled_prophecies (gerceklesen_kehanetler) | array of {id int, how (nasil) string, reading (yorum) enum [true, misread, self_fulfilling]}; all required | reading: true: as it was spoken; misread: it came true but not as everyone expected; self_fulfilling: it came true because people believed it |
| resolved_thread (sonuclanan_iplik) — **only if close candidates exist** | object {id int enum [first fate.close_candidates_shown candidate ids], how string "How the story ended: 2–3 sentences, a concrete outcome"} | The story among the priority candidates (stretched too long or stagnant) that resolved this age |
| closed_threads (kapanan_iplikler) | array, minItems `max(0, min_close - (candidates ? 1 : 0))`, items {id int, how string "How the story ended: 2–3 sentences, a concrete outcome and price"} | At least {min_close} threads must close |
| advanced_threads (ilerleyen_iplikler) | array maxItems `fate.advance_max`, items {id int "thread", record_id (kayit_id) int "This age's record that advanced the thread (event, creation or named record)", how string "One sentence: how the story took a step"} | If an event or record of this age concretely advanced an open thread even though nobody gave thread_id |
| new_threads (yeni_iplikler) | array maxItems `new_max`, items {text (metin) string, related_ids (ilgili_ids) int[]} | At most {new_max} new open stories: unresolved tensions born this age, unfinished business, expected conflicts |
| rewards (oduller) | array of {son_id int, fame (un) int 1..max(1,fate.reward_max), reason (sebep) string "Visible in the chronicle: one sentence in the world's language; do not write thread or record numbers, mention the story by name"} | Fame for sons who advanced open stories or visibly enriched the world |
| facts (gercekler) | array minItems `min(fate.facts_min, fate.facts_max, n_new + n_pending)`, maxItems `fate.facts_max`, items {subject_id (ozne_id) int, relation (iliski) string "Short predicate: 'forbids', 'opens only in winter', 'is made of', 'is immortal', 'descends from'", object_id (nesne_id) int "if the object is an entity", object (nesne) string "if the object is plain text"}; required subject_id, relation | MANDATORY. From every creation you accepted or fixed and every record you named, 1–3 short, definite facts: propositions that must not be violated in the future (what it is made of, what it forbids, whom it belongs to, when it opens…). Do not repeat recorded bonds like location, creator, language and patron; the engine writes those already |
| words (kelimeler) | array maxItems `fate.words_max`, items {language_id (dil_id) int enum [canon language ids] (enum only if any), word (kelime), meaning (anlam), origin (koken) "Which event it was born from"}; all required | New words that enter the languages from this age's events (names of places, heroes, disasters, knowledge); must fit the language's sound system |

required: verdicts, namings, fulfilled_prophecies, [resolved_thread if candidates], closed_threads,
advanced_threads, new_threads, rewards. (facts and words are not required in the judgment-only schema because the
`required` list is filtered from the full list, which never included them — keep as is or make them required.)

`min_close` and `new_max` (old `enAzKapat`, `yeniTavan`):
```
threads = open threads except "great" (expedition) threads, sorted most stagnant first
candidates = threads with stagnant >= fate.stagnant_ages or max(progress, len(advancers)) >= fate.long_thread
min_close = min(fate.close_max, len(threads), max(candidates ? 1 : 0, len(threads) - fate.thread_cap + 2))
new_max   = max(min(1, fate.new_thread_max), min(fate.new_thread_max, fate.thread_cap - len(threads) + min_close))
```

### 6.5 `fate.extra_judgment` — overflow judgment rounds (old `ekTur`)

- **system**: `You are FATE: the cold law that keeps the world of {world.name} coherent, above even the gods. You write in English. {shared.cliche_ban}`
- **user**:
  ```
  {context.world_header(world)}

  WHAT THE SONS AND MORTALS CREATED THIS AGE (continued; give a verdict for each one):
  {entity_detail + optional PRE-SCREEN WARNINGS, joined by "\n\n---\n\n"}

  {shared.verdict_criteria}
  ```
- **schema**: `{ verdicts: <same as 6.4> }`, required `verdicts`.

### 6.6 Age events text (old `cagSatirlari`, `cagOlaylari`, `cagOlaylariDunyaya`)

Chronicle rows of the age, excluding `engine_raw`, passed through `prompt_text()`:
- council rows are cut to the first `fate.council_sentences` (2) sentences (so the minutes are not copied verbatim);
- rows identical after replacing digits with `#` and collapsing whitespace are folded into one; folded rows get
  the suffix ` (this age {k} times)`.
- `age_events(age)` = rows joined by `\n`, `budget(…, fate.events_budget, "rest in the chronicle")`.
- `age_events_by_world(age, worlds, max)` (chronicler): if < 2 worlds same as above. Else each row is assigned to
  the world holding most of its linked entities (ties → lowest id; no links → "Cosmos and sky"); the budget is shared
  fairly: sections sorted by length ascending, each gets `min(len, floor(remaining / sections_left))`. Output:
  ```
  — {world name} (world#{id}) —
  {budget(rows, share, "rest in the chronicle") or "(no events recorded this age: tell of its silence)"}
  ```
  joined by blank lines; the location-less section is titled `— Cosmos and sky —`.

### 6.7 `chronicler.system`

> You are the mortal chronicler of the world of {world.name}. You write in English, epic but concrete; you bind
> events together by cause and effect. {shared.cliche_ban}

### 6.8 `chronicler.user` (old `kronikIstemi({world, age, worlds, engine_notes, pending_text, task})`)

The header and RULES are outside the budget (never truncated); data fills the rest.

```
{context.world_header(world)}

=== RULES ===
TASK: {task or "Give this age a mythic name and tell what happened in 3–5 paragraphs in the voice of a mortal chronicler. Mention those born of the world's own course, even by their temporary names."}
[[if multi_world]]WORLDS: {world#id name, …}. In the "worlds" field write a separate section for EVERY world (skip none). Each world's section tells ONLY the events under that world's heading; do not carry another world's people, city or person into that world. For a world with few events, tell of its silence, its waiting, its everyday life; do not add invented great events.[[/if]]
[[if previous_names]]NAMES OF PREVIOUS AGES (DO NOT REPEAT or imitate): {last fate.previous_names names joined "; "}[[/if]]
[[if piled_roots]]DO NOT USE IN THE AGE NAME (piled up in previous names): {root-, …}.[[/if]]
{chronicler_line}
OPENING: do NOT open the narrative with the sky, the star of the age, a celestial sign, or the "Age N" / "at the beginning of the age" pattern; enter from inside a person, a place, an object or a sound.[[if opening_patterns]] These patterns piled up in recent openings are FORBIDDEN in the first sentence: «p1», «p2».[[/if]]
Do NOT copy verbatim the world engine's sentences, the council minutes or the stock phrases of the events; tell the fact with the chronicler's own eyes and own words; an event folded as "(this age N times)" is told once, with its repetition. Do not write record numbers (#12), stat names or values in the text (not even in words: "his anger at seventy-five", "twenty-two life"), star glyphs, mood scores; do not mention ledger lines such as bond counts.
{shared.tired_images()}

[[if name_kinds]]WHAT THE NAMES ARE (do not make a person into a people or a people into a person):
{name_kinds}

[[/if]][[if previous_verdicts]]FATE'S VERDICTS FROM THE PREVIOUS AGE (mention their consequences in this age's narrative):
{previous_verdicts}

[[/if]]WHAT HAPPENED DURING AGE {age}[[if multi_world]] (world by world)[[/if]]:
{events or "(nothing)"}

RESULTS OF THE WORLD ENGINE:
{engine_text or "(none)"}

BORN OF THE WORLD'S OWN COURSE:
{pending or "(none)"}
```

- `chronicler_line` (old chronicler continuity, `kronikciDurumu`):
  - no previous chronicler: `Put the mortal who writes this narrative in the "chronicler" field.`
  - previous chronicler has written `streak >= fate.chronicler_tenure` ages: `CHRONICLER: {name} has been writing for {streak} ages; this age they may hand the pen to a successor (the successor introduces themselves and whom they took over from in one sentence) or keep writing. Chain: {Age a: name (who) → …}`
  - otherwise: `CHRONICLER: this age too is written by {name} ({who}): write the SAME name and identity in the "chronicler" field; do not introduce yourself again, do not say the previous record was lost. Chain: {…}`
  - chain = last `fate.previous_openings` chroniclers before this age, oldest first, `Age {a}: {name} ({who})`.
- `previous_names` = all previous age names (last `fate.previous_names` shown).
- `piled_roots` (old `sikAdKokleri`): stems (len ≥ `lang.motif_root_min`, excluding the word "age") appearing in ≥
  `fate.name_root_threshold` previous age names. LANGUAGE-SPECIFIC stemmer.
- `opening_patterns` (old `acilisKaliplari`): over the first sentences of the last `fate.opening_window` narratives,
  word bigrams (possessive suffix and digits removed) appearing in ≥ `fate.opening_pattern_threshold` openings,
  excluding bigrams starting/ending with function words. LANGUAGE-SPECIFIC function-word regex.
- Budgets: `data_budget = max(fate.chronicle_engine_budget, fate.chronicler_budget - len(header+rules))`;
  `side = floor(data_budget × fate.chronicle_side_share / 100)`;
  `engine_text = budget(engine_notes, min(fate.chronicle_engine_budget, side))`; `pending = budget(pending_lines, side)`;
  `events_budget = max(1, data_budget - len(engine_text) - len(pending))`;
  `previous_verdicts = budget(prompt_text of age-1 Fate rows starting "A story …" or containing "came true", fate.previous_verdicts_budget, "in the chronicle")`;
  `name_kinds = budget(name_kinds(age), fate.name_kinds_budget)`;
  `events = age_events_by_world(age, worlds, min(fate.events_budget, max(1, events_budget - len(previous_verdicts) - len(name_kinds))))`.
- `name_kinds(age)` (old `adTurleri`): up to `fate.name_kind_rows` entities linked to this age's chronicle rows,
  most-mentioned first: `{name}: {type label}` + ` (a single person, not a people)` for mortals, else ` ({subtype})`.
- `pending_lines` = `entity_line` of every pending record.

### 6.9 `schema.chronicle` (old `kronikSchema`)

| field | type | description |
|---|---|---|
| age_name (cag_adi) | string | The mythic name to give this age, e.g. "Age of the Salt Rains"; do NOT REPEAT the names of previous ages |
| narrative (anlati) | string | This age's epic narrative of 3–5 paragraphs; from the mouth of a mortal chronicler, binding events together by cause and effect |
| summary (ozet) | string, minLength `fate.summary_min` | One but full sentence (at least {fate.summary_min} characters): who, what, where, and what it cost ("without using the word 'price'", with a concrete loss or consequence) |
| chronicler (kronikci) | object {name (ad), who (kim) "Who they are: their people, their trade, their link to the previous one (e.g. 'Ehmel the Scribe, apprentice of Lemir')"}, both required | The mortal chronicler who writes this age |
| worlds (dunyalar) — only if > 1 world | array, minItems = maxItems = number of worlds, items {world_id enum [ids], narrative "1–2 paragraphs", summary minLength summary_min same description as above}; all required | A separate section for EACH world (all mandatory, each world once): what happened in that world this age; even if there were few events, how that world's age passed |

required: age_name, narrative, summary, chronicler, [worlds].

### 6.10 `chronicler.fix_opening` (old part of `kronikiTamamla`)

Runs only if `fate.fix_opening = 1` and the first sentence contains a forbidden opening pattern or starts with
"Age N" / "at the beginning of the age" (LANGUAGE-SPECIFIC regex `^(çağ\s+\d+|çağın başında)`).
- **system**: `You are the mortal chronicler of the world of {world.name}. You write in English. {shared.cliche_ban}`
- **user**:
  ```
  The first sentence of this age's narrative opens with a repeated pattern[[if patterns]] («p1», «p2»)[[/if]]. Rewrite only the first sentence: do not open with the sky, a star, "Age N" or "at the beginning of the age"; enter from inside a person, a place, an object or a sound; it must fit the rest of the narrative and carry the same fact.

  FIRST SENTENCE: {first_sentence}

  CONTINUATION OF THE NARRATIVE: {narrative[len(first): len(first) + fate.chronicle_engine_budget]}
  ```
- **schema**: `{ first_sentence (ilk_cumle): string "The new first sentence" }` required.
- Accepted only if the new sentence itself contains no forbidden pattern.

### 6.11 `chronicler.missing_worlds` (old part of `kronikiTamamla`)

Runs if > 1 world, `fate.complete_missing_worlds = 1`, and the chronicle skipped some worlds.
- **system**: `You are the mortal chronicler of the world of {world.name}. You write in English, concretely. {shared.cliche_ban}`
- **user**: `chronicler.user` rendered with `task = "This age's main narrative has been written; the sections of these worlds were left missing: {world#id name, …}. Write only these worlds' sections (each with only the events under its own heading)."` (no engine notes / pending text).
- **schema**: `schema.world_sections(missing worlds)`.

### 6.12 `chronicler.lost_age` and `chronicler.lost_world_sections` (old `kayipKronikler`)

Backfill for ages whose chronicle was never written (at most `fate.lost_chronicles` per completion run), and for
past ages missing some world sections (at most `fate.lost_world_sections`, newest first). The world header is
rendered "as of that age": epoch/year set to that age, no climate, no age star, no mood, doom 0.
- **system** (lost age): `You are the mortal chronicler of the world of {world.name}. You write in English, epic but concrete; you bind events together by cause and effect. {shared.cliche_ban}`
- **user** (lost age): `chronicler.user` with `task = "The chronicle of Age {age} was left unwritten. Give this age a mythic name and tell what happened in 3–5 paragraphs in the voice of a mortal chronicler."`, worlds = worlds that existed by that age.
- **schema** (lost age): `{ age_name, narrative "3–5 paragraphs", summary (minLength, same description), chronicler {name, who}, [worlds as in 3.7 if > 1 world] }`.
- **system** (lost world sections): `You are the mortal chronicler of the world of {world.name}. You write in English, concretely. {shared.cliche_ban}`
- **user**: `chronicler.user` with `task = "Age {age} has a main narrative but the sections of these worlds were never written: {world#id name, …}. Write only these worlds' sections (each with only the events under its own heading; if there are none, that world's silent age)."`
- **schema**: `schema.world_sections(missing)`. Timeout `fate.lost_timeout`.

---

## 7. Naming pending engine records (old `bekleyenleriAdlandir`)

- Role: Fate as namer. Batches per world, `naming.batch` records per call, up to `naming.parallel` calls at once.
- **system**: `You are the Fate of the {world.name} cosmos. You write in English. To records the world engine opened with a temporary name you give a real name fitting {world_name ? "the dialect of the world of " + world_name : "the naming language"}, a subtype, a description and an image prompt. {shared.cliche_ban}`
- **user**:
  ```
  {context.world_header(world, multi_world ? world_id : null)}

  RECORDS WAITING TO BE NAMED (they have temporary names and [World engine] descriptions[[if multi_world]]; all of them are in the world of {world_name}[[/if]]):
  {entity_detail of each record, joined by "\n\n---\n\n"}

  For each record give a real name, a subtype, a description and an image prompt. Invented name roots use ONLY the sounds of this world's naming language (no disallowed vowel or consonant; no sounds of another world). For those tagged "name-from-language" the name has already been derived from their own people's language: keep that name EXACTLY, only write the subtype, description and prompt. Do not write "[World engine]" in the description; tell of the record itself in the world's language. Do not call a mortal (mirror birth, heir, hero) a "son": sons are only the god's children. The description must be at least three sentences. Do not write record numbers (#12), stat names or values (morale 78, 565 soldiers, power 34) in the description; express magnitude in words. Do not repeat existing names.[[if dialect_warnings]]

  PREVIOUS SUGGESTIONS DID NOT FIT THE DIALECT (name them again): #{id} "{name}" ({root}: {letters} do not exist in this dialect; …); …[[/if]][[if motifs]]

  {shared.tired_images(world_id)}[[/if]]
  ```
- **schema**: `{ namings (adlandirmalar): array, minItems = maxItems = batch size, description "A naming for EVERY record below", items schema.naming_item }`.
- Dialect check (old `lehceIhlali`, `naming.dialect_check`): LANGUAGE-SPECIFIC — parses the allowed vowels out of
  the dialect text ("vowels are a, e, i and o") and flags invented roots using other Turkish vowels. In English,
  replace with an explicit `allowed_letters` / `forbidden_letters` field stored on each world's dialect (generated
  at genesis) and check names against it.

---

## 8. Voices of the peoples (old `halklarinSesi`)

- Role: unreliable mortal narrators — partisan histories ("views") and folk beliefs about gods.
- **system**: `You are the mortal narrators of the world of {world.name}: historians, bards, seers. Each people tells the truth according to its own interest, its own fear and its own language; they misremember, exaggerate, keep silent. You write in English. {shared.cliche_ban}`
- **user**:
  ```
  {context.world_header(world)}

  WHAT REALLY HAPPENED DURING AGE {age}:
  {age_events[:fate.voice_events] or "(a quiet age)"}

  [[if historians]]HISTORIANS (for each, this age's account through its own people's eyes; do not open with "We …", do not repeat the opening of the previous account; the previous historian continues or their apprentice takes over):
  [[each people h]]people_id {h.id}: {entity_line(h)}
  {society lines of h}[[if previous view]]
  Previous historian: {historian or "name unknown"} (Age {age}); the previous account opened like this: «{first sentence[:fate.view_opening]}…»[[/if]]
  [[/each]] (separated by blank lines)

  [[/if]][[if beliefs]]BELIEFS (how each people tells of this god by the name it gave him; each belief's distortion is written in the form given to it, no two beliefs use the same sentence construction):
  [[each (people h, god s, index i)]]people_id {h.id} {h.name} → son_id {s.id}, in truth {s.name}, {s.title} ({s.d1}/{s.d2}); {known_name ? "this people calls him \"{known_name}\"" : "this people has not yet given him a name: give one with the sounds of the {h.name} people's language"}. Form of distortion: {DISTORTIONS[(h.id + s.id + i) mod 8]}.{s.id == 0 ? " He is the father of all the gods, the creator; they know him as distant, old and incomprehensible." : patron(h) == s ? " They worship him." : " They do not worship him; they know him with hostility or fear."}
  [[/each]]

  [[/if]]Historians should use their own peoples' names and lexicon. Beliefs should name the god by the name the people gave him; they must not know the whole truth.
  ```
- **DISTORTIONS** (old `SAPMA_BICIMI`, rotate):
  1. ties a detail to the wrong person or place (confuses who did it)
  2. reverses the order of an event
  3. never mentions the god's price or wound, only his gift
  4. says a ban or rite was set by its own ancestors, not by the god
  5. magnifies a small event, shrinks a great loss
  6. confuses the god with another god, a hero or an animal
  7. misunderstands a word and builds the whole belief on that misunderstanding
  8. attributes something the god did to a natural phenomenon (the wind, drought, salt)
- **schema.voices**:
  - `views (bakislar)`: array of {people_id int, historian (tarihci) "The historian's name and title, in the people's language", text (metin) "1–2 paragraphs; through this people's eyes, partisan, magnifying its own heroes, belittling its enemies, never mentioning some things"} all required
  - `beliefs (inanclar)`: array of {people_id int, son_id int "0 for the creator god", name (ad) "The name this people gave him: if given in the prompt, EXACTLY that; if not, a new name with the sounds of the people's own language (NOT the god's name or title)", story (anlati) "2–3 sentences: how this people tells of that god, by the name they gave him", wrong (yanlis) "One sentence: where their account really deviates, in the form of distortion given for that belief in the prompt. Do NOT USE these patterns: {«…they think, whereas…», «In truth …», + piled-up patterns}"} all required
  - required: views, beliefs.
- Forbidden belief patterns (old `INANC_KALIP_HEP` + `INANC_KALIPLAR`): always `«…they think, whereas…»`,
  `«In truth …»`; plus each of `«…it is said, but…»`, `«…it is told, but…»`, `«…they suppose…»`, `«…, whereas…»`,
  `«…they count…»`, `«…they believe, but…»`, `«…they know, but…»` if it occurs in ≥ `folk_belief.pattern_threshold`%
  of the last `folk_belief.pattern_window` stored "wrong" sentences. LANGUAGE-SPECIFIC regexes → re-derive for
  English phrasings.

---
## 9. Deepening and epics (lore writers and bards)

### 9.1 `deepen.entity` (old `derinlestir`)

- Trigger: manual "Deepen" on an entity page; bulk deepening (`toplu.js`); epoch auto-deepen of important records
  (see 10).
- **system**: `You are the lore writer of the world of {world.name}. You write in English. You rely only on the existing canon; you do not invent big new facts, you deepen the existing ones. {shared.cliche_ban}`
- **user**:
  ```
  {context.world_header(world, entity.world_id)}

  ENTITY:
  {context.entity_detail(id)}

  [[if creator_son]]ITS CREATOR: {son.name}, {son.title}. (The creator's obsession is not this entity's subject; the entity is told by its own nature.)[[/if]]

  NEIGHBOURING BONDS:
  {first content.deepen_bonds lines of bond_lines('v', id)}

  Recent events:
  {context.recent_chronicle(content.deepen_chronicle, entity.world_id)}[[if tired_images(world)]]

  {shared.tired_images(entity.world_id)}[[/if]]

  Deepen this entity. The output consists of SEPARATE KEYS; never write one inside another key:
  - history: only the history through the ages (2–4 paragraphs of prose; NO headings like "Rumours:", "Details:" inside it)
  - rumours: array; each item one rumour sentence
  - sayings: array; each item { kind, text }
  - details: array; each item one concrete detail
  - hidden_truth: a single paragraph[[if special]]
  - special: object; fields {special field keys comma-joined}[[/if]]
  Fate's note is a writing note: do not carry into the narrative that Fate fixed, rewrote or struck the record against a ban. Do not write record numbers (like #12), stat names and values (like power 75), star glyphs or percentages in the text; say everything in the language of the narrative. If it has died or vanished, tell it in the past tense.
  ```
- **schema.deepen**:

| field | type | description |
|---|---|---|
| history (tarih) | string | The entity's history through the ages, 2–4 paragraphs |
| rumours (soylentiler) | string[], counts `narrative.rumours_*` | Rumours circulating among mortals, some true, some false |
| sayings (sozler) | array {kind (tur) enum [proverb, lullaby, prayer, malediction, folk song, oath, tongue-twister], text}, counts `narrative.sayings_*` | Mortals' sayings about it; may contain words from the naming language |
| details (ayrintilar) | string[], counts `narrative.details_*` | Strange, concrete details; each of a different kind (a habit, a material, a non-numeric measure, a ban, a sound, a texture, a colour…) and specific to this entity; never use the same sense twice |
| hidden_truth (gizli_gercek) | string | A truth nobody knows, connected to the entity's own history or to the laws of the world |
| special (ozel) — only for types with a special table | object, all fields required | {special.description} |

  required: only `history` (Haiku used to dump everything into `history` and fail the schema when all six were
  required; the others are listed in the prompt and may be empty — the post-processor splits embedded sections back
  out, see 08).
- **Special tables** (old `OZEL`; key → heading / description / fields):
  - mortal → "Character" / "This mortal's inner world": temperament "Temperament", goal "Goal in life", fear "Greatest fear", secret "The secret they tell no one", speech "How they speak", relationships "Important relationships: loved ones, enemies, people they owe".
  - people → "Way of life and culture" / "The texture of this people's social order and culture": governance "Form of government and who has a say", values "Most sacred values", taboos "Taboos and punishments", cuisine "Cuisine: what they eat, what they never eat, table manners", dress "Dress and adornment: material, colour, who may not wear what", music "Music and sound: their instruments, melodies, at what moment one falls silent", architecture "Architectural style: what they build with and in what form", art "Their art: what it depicts, what is forbidden to depict", calendar "Calendar and festivals: what they count the year by, which celestial event they celebrate", warfare "Way of war and weapons", death "What they do with their dead".
  - settlement → "City" / "The texture of this settlement": governance "Who rules, how", economy "What it lives on, what it sells", quarters "Important quarters and buildings", problem "Its biggest problem", smell "Its smell and its sound".
  - faction → "Organisation" / "How this faction works": purpose "Real purpose", hierarchy "Hierarchy", methods "Methods", symbol "Symbol and colours", weakness "Weak point".
  - cult → "Faith" / "This cult's teaching": doctrine "Core teaching", rites "Rites", ranks "Ranks", prohibitions "Prohibitions for its disciples", promise "Its promise to its disciples".
  - species → "Its nature" / "This species' nature": behaviour "Behaviour", life_cycle "Life cycle", diet "What it feeds on", special_ability "Special ability", weakness "Weakness".
  - item → "The item's past" / "This item's story": making "How and from what it was made", owners "Chain of owners", powers "Known powers", price "The price of using it".
  - language → "Language structure" / "This language's structure": sound "Sound system", grammar "Grammar: suffixes, syntax", script "Its script or lack of one", idioms "Untranslatable concepts".
  - knowledge → "Practice" / "How this knowledge is applied": masters "Who knows it, how it is taught", tools "Its tools and materials", secret "The part kept secret", danger "Its misuse".

### 9.2 `creator.epic` (old `tanriDestani`)

- **system**: `You are the oldest bard of the {world.name} cosmos and you are writing the epic of the creator god {god_name}. You write in English; epic but concrete. You rely on the records and do not invent great events; you fill the gaps with myth, intuition and the fear of mortals. {shared.cliche_ban}`
- **user**:
  ```
  {context.world_header(world)}

  THE GOD {god_name}:
  {known}           ← lines: "Title: …", "Appearance: …", "Temperament: …", "The god's own note (canon, you must follow it): …" (each only if present)

  COSMOLOGY: {cosmology}

  HIS SONS:
  {name, title ({rarity}, {d1}/{d2}[, {status} if not active][, REBEL]; loyalty {loyalty}) — one per line}

  HIS WORLDS: {name (type, Age n), …}

  AGES:
  {Age n: {name} — {summary} per closed age, or "(no age has closed yet)"}

  HIS TRACES IN THE RECORDS:
  {last content.god_traces chronicle rows of kinds god/revelation/world_birth/council/order/ascension/resurrection/star or mentioning the god's name, each "[Age a, year y] {prompt_text}"; or "(none)"}

  [[if beliefs]]HOW THE PEOPLES TELL OF HIM:
  {people calls him "{name}": {story} — per folk belief about the creator (son_id 0)}

  [[/if]]Write the creator god's epic in sections, from the first light to today.
  ```
- **schema**: `{ title (baslik) "The epic's name", sections (bolumler): array counts narrative.epic_sections_*, items {title, text "2–4 paragraphs; based on the records, binding events by cause and effect", age_start (cag_bas) int, age_end (cag_son) int} all required, line (dize) "The single best-known line of the epic" }`, all required.

### 9.3 `creator.deepen` (old `tanriDerinlestir`)

- **system**: `You are the lore writer of the {world.name} cosmos. You are deepening the creator god {god_name}. You write in English. You rely on the existing canon and deepen it; you must follow the god's own note. {shared.cliche_ban}`
- **user**:
  ```
  {context.world_header(world)}

  THE GOD {god_name}:
  {known}

  COSMOLOGY: {cosmology}

  [[if epic]]THE ESSENCE OF HIS EPIC: {epic.line}

  [[/if]]HIS SONS: {name (d1/d2), …}

  HIS TRACES IN THE RECORDS:
  {last content.god_traces_deepen rows, same format as 9.2, or "(none)"}

  Deepen the creator god.

  {shared.section_keys_rule}
  ```
- **schema**: history (tarih) "How the god changed through the ages, 2–3 paragraphs"; names (adlari) array
  {name, who "Who uses this name", meaning} counts god_names; secrets (sirlar) string[] "Secrets even his sons do not
  know" counts secrets; fears (korkular) string[] counts fears; prohibitions (yasaklar) string[] "Prohibitions he set on
  creation and what happens when they are broken" counts prohibitions; gifts (armaganlar) string[] "Gifts he gave to
  mortals and his sons" counts gifts; desire (istek) "What he really wants from all of creation"; sayings (sozler)
  {kind enum [prayer, malediction, hymn, proverb, oath, lullaby], text} counts sayings; rumours string[] counts
  rumours; hidden_truth "The truth about the god himself that lies at the foundation of the cosmos".
  required: history, names, prohibitions, desire (the world header reads prohibitions and desire).

### 9.4 `foreign_god.deepen` (old `yabanciDerinlestir`)

- Trigger: startup completion for every foreign god without depth; manual "Deepen" on a foreign god page.
- **system**: `You are the lore writer of the {world.name} cosmos. You are deepening {foreign.name}, the old god of {world_name ? "the world of " + world_name : "a world"} who existed before the pantheon. You write in English. You rely on the existing canon and expand it; you build a character consistent with its stats and attitude; you derive names with its own world's dialect. {shared.cliche_ban}`
- **user**:
  ```
  {context.world_header(world, foreign.world_id)}

  [[if home_world]]ITS WORLD: {name} ({type})[[if dialect]]
  DIALECT: {dialect}[[/if]][[if cosmology]]
  COSMOLOGY: {cosmology}[[/if]]

  [[/if]]FOREIGN GOD {foreign.name}:
  {known}

  WORSHIPPERS: {name (type[, subtype]), …} or "none at the moment"

  RECORDS IN THE CHRONICLE THAT MENTION ITS NAME:
  {"[Age a] text" for the last foreign_god.deepen_chronicle rows matching the name as a whole word, oldest first, or "(none)"}

  Deepen this foreign god.

  {shared.section_keys_rule}
  ```
  `known` lines (each only if present):
  - `Title: {title}` · `Domains: {domains}` · `Description (canon): {description}`
  - if dead: `DIED[ (Age n)]: write every text in the PAST TENSE; what it wanted, how it looked on things, how it was worshipped must be told as "used to want", "used to look", "was worshipped", and its history ends with its death. Do not write numbers, scores or record numbers.`
  - `State: {status}; power {power}; attitude to the pantheon {attitude} (−100 enemy, +100 friend); {contact ? "has made contact with the pantheon" : "has not yet made contact with the pantheon"}`
  - `Stats: {label value, …}` (foreign-god stats, see appended fragments)
  - `Existing powers (keep them, describe them by name): {name (effect), …}`
  - `Personality (the fields the god wrote are canon): {label: value | …}`
- **schema** (old `yabanciDerinlikSemasi`): personality (kisilik) object with one string per personality key
  ("{label}; 1–2 sentences, concrete", all required); existence `schema.existence`; powers array (min
  `min(1, foreign.power_count)`, max `max(1, foreign.power_count)`) "The god's powers; each has an effect in the engine:
  {key (label: description); …}" items {name "The power's name in its own world's language", effect enum foreign-power
  keys, description "1–2 sentences: how the power appears, how it works"}; history "Its history before and after the
  pantheon, 2–3 paragraphs; based on the records"; names, secrets, sayings, rumours as in 9.3; desire "What it really
  wants"; view_of_pantheon (panteona_bakis) "How it looks on the newly arrived pantheon and its sons; consistent with
  its attitude"; worship (tapinma) "How its worshippers worship it: rites, offerings, prohibitions"; hidden_truth "The
  truth about it that nobody knows"; image_prompt "English photoreal portrait prompt of this god. {rules}".
  required: personality, existence, powers, history, desire, image_prompt.
  (Foreign-god personality keys, power keys and stat labels: see appended `part-09-fragments`.)

### 9.5 `son.epic` (old `destanYaz`)

- **system**: `You are the bard of the world of {world.name}. You write in English; epic but concrete, without inventing events, relying only on the records. {shared.cliche_ban}`
- **user**:
  ```
  {context.world_header(world)}

  SON: {name}, {title} ({rarity label} {★×stars}, {d1}/{d2})
  Temperament: {temperament}
  Obsession: {obsession}
  Secret (as much as the bard senses): {secret}
  Plan: {plan or "-"}

  CREATIONS: {name (type[/subtype], A{age}[, {status} if not canon]); …} or "none"

  RECORDS:
  {"[Age a] {prompt_text}" for the last content.epic_traces chronicle rows by the son or mentioning his name, or "(none)"}

  Write this son's epic.
  ```
- **schema**: `{ title "The epic's name", epic (destan) "4–6 paragraphs; from the mouth of a mortal bard, binding events by cause and effect", line (dize) "The single best-known line of the epic" }`, all required.

---

## 10. Image prompt writers

### 10.1 `image_prompts.entities` (old `eksikPromptlar`) — already English in the old code

- **system**: `You write English, photorealistic image-generation prompts for the world of {world.name}. Each prompt: subject, materials, distinctive details from the description, setting, lighting, mood, camera and lens. 40–90 words. No text overlays. {shared.image_prompt_rules}`
- **user**:
  ```
  WORLD: {cosmology}
  TONE: {tone}

  Write one prompt for each entity below; follow each entity's GUIDE exactly (an Outer Being must never be shown fully).

  #{id} [{type}[ / {subtype}]] {name}: {description[:content.prompt_description]}
  GUIDE: {image_direction(entity)}. {world_ambience(world type)}
  … (blank line between entities)
  ```
- **schema**: `{ prompts (promptlar): [ {id int, prompt string} ] }`.
- Accept a prompt only if longer than `content.prompt_min` chars; store `fix_image_prompt(entity, prompt)`.

### 10.2 `image_prompts.cosmos` (old `eksikKozmosPromptlari`)

- **system**: `You write English, photorealistic image-generation prompts for the cosmos of {world.name}: subject, scale, materials, lighting, mood, camera and lens. 40–90 words each. {shared.image_prompt_rules}`
- **user**:
  ```
  COSMOLOGY: {cosmology}
  TONE: {tone}

  no 1: [world / {type}] {name}: {(description or cosmology)[:content.cosmos_world]}
  GUIDE: {COSMOS_DIRECTION.world}. {world_ambience(type)}

  no 2: [star / {type}] {name}: {description[:content.cosmos_other]}
  GUIDE: {COSMOS_DIRECTION.star}

  no 3: [foreign god] {name}, {title}: {description[:content.cosmos_other]}
  GUIDE: {COSMOS_DIRECTION.foreign}
  ```
  (worlds, then stars, then foreign gods lacking prompts; at most `content.cosmos_batch` items.)
- **schema**: `{ prompts: [ {no int, prompt string} ] }`; accepted if longer than `content.prompt_min`; truncated to
  `content.prompt_max` chars.

### 10.3 Image direction tables (old `gorselyon.js`) — already English

`IMAGE_DIRECTION` by entity type (old `PROMPT_YONU`):

| type | direction |
|---|---|
| language | an object that shows this language: a carved tablet, manuscript page, inscription or glyph-covered artifact |
| knowledge | people practicing this technique or knowledge, with its tools, materials and workplace |
| tradition | the ritual or festival being performed by the community |
| legend | a painterly-yet-photoreal scene illustrating the legend |
| natural_law | a cosmic visual metaphor of this natural law at work in the world |
| prophecy | a visionary scene of the prophecy, as a seer would see it |
| event | the event as it happens, documentary style |
| celestial | the celestial body in the night sky above the landscape |
| people | a group portrait of these people in their daily life: clothing, tools, faces, dwellings behind them |
| settlement | an establishing shot of the settlement from a nearby rise, people and smoke for life and scale |
| mortal | a full-length character portrait in their environment; face, garments, posture that reveal their role |
| army | the army on the march or arrayed for battle, banners and equipment, dust and weather |
| monument | the monument or work in its setting, with people for scale |
| item | a museum-grade still life of the object on a surface that fits its origin, raking light |
| resource | the resource where it is found or harvested, with the workers or creatures who gather it |
| spirit | a translucent presence half-visible in a real place, long exposure, uncanny but restrained |
| region | a sweeping landscape of the region, atmospheric perspective, characteristic weather |
| place | the place itself in its surroundings, characteristic light and weather |
| species | the creature in its habitat, wildlife photography |
| vehicle | the vehicle or conveyance in use, with its crew or riders |
| outer_being | an Outer Being: NEVER show it fully — only a fragment, a silhouette, a reflection, or its effect on the world |
| cult | the cult gathered at its rite: robed members, sacred objects, the place of worship, faces lit by its particular light |
| faction | members of the faction in their meeting place, their insignia, colors and tools of their trade, a sense of hierarchy |
| work | the artwork itself (song performed, statue, fresco, book) in the place it is kept or performed, with its audience or keeper |
| law | the law being proclaimed or carved: a stele, scroll or assembly, the people who live under it watching |
| (default) | the subject in its setting |

`image_direction(entity)` (old `promptYonu`):
1. vehicles: match subtype+name (word-start regex) — gate/portal/passage → "a gate or portal between worlds: the
   frame, the impossible view through it, travelers dwarfed before it"; ship/vessel/boat/raft → "a ship between
   worlds: hull, sails or engines, crew on deck, the void or alien sky around it"; mount/wing/dragon/horse → "a mount
   carrying its rider across the sky or between worlds, motion and scale"; bridge → "a bridge spanning the gap between
   worlds, travelers crossing, vertiginous depth". (LANGUAGE-SPECIFIC: the old regexes mixed Turkish and English
   stems; for English keep the English words.)
2. species tagged `megafauna` → "a colossal megafauna in its habitat with tiny human figures for scale; wildlife
   photography from a distance".
3. else the table.

`world_ambience(world_type)` (old `dunyaOrtami`): empty for the ordinary type; else `World type: {type label}
(terrain such as {first 5 biomes}). Let its palette and atmosphere show.`

`COSMOS_DIRECTION`: world "the whole world seen from orbit or high above its sky, its unique physics visible (rings,
seas, ice, glow), then a hint of its surface"; star "the star itself in deep space with its planets as small discs
nearby, astrophotography, its color and character exaggerated just enough"; foreign "a foreign god as its worshippers
imagine it: a monumental idol or vision in its home world, never a cartoon".

`fix_image_prompt(entity, prompt)` (old `promptDuzelt`): trim; outer beings without any of
`partial|partially|fragment|silhouette|glimpse|glimpsed|obscured|hidden|reflection|never (fully) seen/visible/shown`
get the tail `, shown only partially — a fragment glimpsed through fog, glare or a reflection, its full shape never
visible.`; megafauna without `scale|tiny (human) figure(s)|dwarf(ed/s/ing)|colossal|towering over` get
`, with tiny human figures for scale.`. Max length 1200 (`PROMPT_EN` — hard-coded in the old code; make it the
`content.prompt_max` tunable); the tail is never cut (the body is cut to make room).

---

## 11. Tool-result messages from the agent wrapper (old `llm.js araclariSar`)

- Gate rejection (e.g. a son who fell asleep mid-turn): `REJECTED: {reason}` with `isError: true`.
- Exception inside a tool: `REJECTED: An error occurred while the tool was running ({error message[:200]}). Your
  action point was refunded; correct your input and try again, or choose another action.` with `isError: true`.
- The old marker `REDDEDİLDİ` doubles as the "this call failed" signal for the transcript (any tool result starting
  with it is treated as an error and does not count as a "done" action). In the new app use `isError` only; keep the
  English word `REJECTED:` as the visible prefix.

---

## 12. Prompts from other modules (appended parts)

The following sections were produced from the other source files and are part of this single prompts module.

## Prompts outside agents.js / tools.js / epoch.js

Source modules: `src/konsey.js` (council, chat with a son, translation, dreams), `src/kozmos.js` (birth of a new world),
`src/agonar.js` (Fate's knowledge-graph repair), `src/olumluler.js` (mortal agent turn), plus the shared context
fragments they assemble from `src/world.js` (`dunyaBasligi`, `lehceBlogu`, `dunyaSatiri`, `kozmosSatirlari`,
`varlikSatir`, `motifYasagi`, `butce`, `bolumluButce`, `sonKronik`, `istemMetni`, `hafiza`), `src/sihirbaz.js`
(genesis wizard text), `src/firsatlar.js` (`olumluFirsatlari`) and `src/ufuk.js` (`sezgiyiDogur` inspiration text).

Conventions used below:

- `{var}` = interpolated variable. `{?cond: text}` = text emitted only when `cond` holds.
- Every prompt here is sent to **Haiku** (user rule: every LLM call uses Haiku, never Sonnet/Opus; the old code's
  `modelFor(key)` lookup and the `effort` parameter for non-Haiku models are dropped). Old model keys are noted only for
  traceability: council / son chat / translation / new world used `modelFor('kader')`; Fate bond repair used
  `askKader('derinlik', …)`; the mortal turn used `modelFor('yaygin')`.
- Old prompts said "You write in Turkish (image prompts in English)". The new app is English-only: replace with
  "Write in English." everywhere. Marked **LANGUAGE-SPECIFIC** where it matters.
- Old output texts were post-processed with `ekDuzelt` (Turkish apostrophe/suffix harmony fixer) and `toplulukIci`
  (Turkish locative phrase builder). **LANGUAGE-SPECIFIC: drop** (English needs no suffix harmony).
- Image-prompt fields reuse the shared constant `shared.image_prompt_rules` (old `GORSEL_YAZIM` in `gorselyon.js`,
  already English; defined by the agents.js part of this spec). Quoted here for convenience:
  > Image prompt rules: describe only what IS visible; never use negations (no, without, not, lacking, absent) because the
  > image model ignores them and draws the thing anyway; describe the replacement instead (e.g. "a smooth blank head with a
  > single thin dark slit" rather than "no face"). Whatever the subject (person, creature, place, object, event or god),
  > name at least two details unique to this world so the image never falls back to a generic real-world look.

---

## Shared context fragments (world.js)

The shared fragments these modules use (world header incl. the short variant for mortals, dialect block, world line,
cosmos lines, entity line, recent events, tired images, budget truncation, son memory, image prompt rules) are defined
once in §0–§2 of this file; the old ids `fragment.*` used in drafts were renamed to the `context.*` / `shared.*` ids there.

---

## Council of the Gods (konsey.js)

### `council.persona` — old `persona(s)` (inline, used in council members list and son chat system prompt)

```
son#{id} {ad}, {unvan} ({nadirlik}; {alan1}/{alan2}){?asi: — REBEL AGAINST HIS FATHER}. Temperament: {cut(mizac, KONSEY.persona_mizac)} Manner of speech: {cut(uslup, persona_uslup)} Obsession: {cut(takinti, persona_takinti)} Passions: loyalty {tutku.sadakat}, ambition {tutku.hirs}, anger {tutku.ofke}. Plan: {cut(plan, persona_plan) || "none"}
```
`cut(s, n)` = first `n` chars + "…" if longer.

### `council.agenda.*` — old `gundemOner()` (auto-agenda when the player gives no topic)

First matching rule wins:

| id | Condition | Text |
|---|---|---|
| `council.agenda.doomsday` | `w.kiyamet >= kiyamet_esik * KONSEY.gundem_kiyamet / 100` | `Doomsday clock {kiyamet}/{esik}: how will the end of the world be prevented, and who will pay the price?` |
| `council.agenda.rebel` | some son has `asi` | `{rebel}'s rebellion against the father: does the council stand with the rebel or against him?` |
| `council.agenda.dead_brother` | some son `durum='olu'` | `The dead brother {name}: shall he be resurrected, or his bones divided?` |
| `council.agenda.war` | a war event (`tur='olay'`, `alt_tur='savaş'`, tag `suruyor`), highest power | `{war name}: will the gods take sides in the mortals' war?` |
| `council.agenda.open_thread` | any open thread | `Unresolved story: {thread text, cut at last space before KONSEY.gundem_kes if longer than gundem_metin, + "…"}` |
| `council.agenda.default` | otherwise | `The course of the world: which brother has grown too great, which must be reined in?` |

### `council.session.system`

Variables: `{world}` = `w.ad`, `{creator}` = `w.tanri_adi`.

```
You are the narrator of the Council of the Gods of the world {world}, giving each god their own voice. Write in English. Each son speaks true to his personality, his passions, his plan and his relationships with his brothers; let there be disagreement, bargaining and grudges. Their father {creator} watches the council.
```
(LANGUAGE-SPECIFIC: old "Türkçe yazarsın" → "Write in English.")

### `council.session.prompt`

Variables: `{header}` = `context.world_header(w)` (full); `{topic}` = player's question or auto-agenda;
`{god_asked}` = topic came from the player; `{count_word}` = member count spelled as a word (`none, one, two, …,
fifteen`, else digits); `{absent}` = names of living sons not in the council; members = up to `KONSEY.uye` sons with
`durum in (aktif, uykuda)`; `{multi}` = more than one world; relationships = every member pair with
`|relationship| >= KONSEY.iliski_esik` or a covenant (`ahit`).

```
{header}

AGENDA{?god_asked:  (in their father's own words; do not quote it verbatim in the minutes or the agenda field, summarize in the third person)}: {topic}

ATTENDANCE: {count_word} sons in the council{?absent: ; absent: {absent names, comma-separated}}.

COUNCIL MEMBERS (each refers to places only of the world they are on as "here"):
{council.persona(s)}{?multi:  Current world: {world name of s}.}   (one line per member)

RELATIONSHIPS BETWEEN THEM:
{A}–{B}: {relationship label} ({value}){?covenant: , covenanted}   (one per line; or "(nothing notable)")

Every son speaks at least once; then a single concrete motion is put to a vote. The votes fit the personalities and relationships. Alliances may be formed or broken.
```
Relationship label (`iliskiEtiket`) thresholds from `OGUL_ILISKI`: `>= baglilik` devotion, `>= dostluk` friendship,
`<= -nefret` hatred, `<= -husumet` hostility, else neutral.

### `council.session.schema`

```json
{
  "type": "object",
  "required": ["speeches", "motion", "votes", "alliances", "decision", "minutes", "agenda"],
  "properties": {
    "speeches": { "type": "array", "minItems": "{members}", "maxItems": "{members*2}",
      "items": { "type": "object", "required": ["son_id", "words"], "properties": {
        "son_id": { "type": "integer", "enum": "{member ids}" },
        "words": { "type": "string", "description": "1–3 sentences in his own manner of speech; they may answer one another" } } } },
    "motion": { "type": "string", "description": "The single concrete motion the council votes on" },
    "votes": { "type": "array", "items": { "type": "object", "required": ["son_id", "vote", "reason"], "properties": {
        "son_id": { "type": "integer", "enum": "{member ids}" },
        "vote": { "type": "string", "enum": ["yes", "no", "abstain"] },
        "reason": { "type": "string" } } } },
    "alliances": { "type": "array", "maxItems": "{KONSEY.ittifak_tavan}", "items": { "type": "object", "required": ["a", "b", "kind", "reason"], "properties": {
        "a": { "type": "integer", "enum": "{member ids}" }, "b": { "type": "integer", "enum": "{member ids}" },
        "kind": { "type": "string", "enum": ["covenant", "break"] }, "reason": { "type": "string" } } } },
    "decision": { "type": "string", "enum": ["none", "against_doomsday", "joint_blessing", "condemn_rebel", "call_for_peace"],
      "description": "The effect on the world if the motion passes" },
    "minutes": { "type": "string", "description": "A 3–5 sentence epic summary of the council, as a mortal seer saw it in a dream; {count_word} sons attended the council (write no other number)" },
    "agenda": { "type": "string", "description": "One-sentence, third-person summary of the agenda for the chronicle (do not repeat the god's question verbatim in the first person: e.g. \"the fate of Haevaron\")" }
  }
}
```
Old Turkish field/enum names (for tracing): `konusmalar/ogul_id/soz`, `onerge`, `oylar/oy: evet|hayir|cekimser/gerekce`,
`ittifaklar/tur: ahit|kopus/neden`, `karar: yok|kiyamete_karsi|ortak_kutsama|asiyi_kinama|barisa_cagri`, `tutanak`,
`gundem`.

---

## Son chat (konsey.js `ogulSohbet`)

### `son_chat.system`

Variables: son `s`, world `w`, `{multi}` (more than one world), `{current_world}` = name of the son's `aktif_dunya`.

```
You are {s.ad}, {s.unvan}; you are a son of the creator god {w.tanri_adi} in the world {w.ad}.{?multi:  You are now on the world {current_world}; your creations on other worlds are there, do not speak of them as if they were where you are.} You are speaking with your father. Speak in English, fully in character, in your own manner of speech; never say you are an AI.
{council.persona(s)}
Appearance: {cut(kisilik.gorunus, KONSEY.sohbet_gorunus)}
Fear: {cut(kisilik.korku, sohbet_sir)} Secret: {cut(kisilik.sir, sohbet_sir)} (do not reveal your secret easily)
```

### `son_chat.prompt`

`{memory}` = `cut(context.son_memory(s), KONSEY.sohbet_hafiza)`; history = last `KONSEY.sohbet_gecmis` chat messages
between the creator and this son, oldest first; `{text}` = the player's message (trimmed, max `KONSEY.sohbet_metin`).

```
YOUR MEMORY:
{memory}

EARLIER IN THE CONVERSATION:
{YOUR FATHER | YOU}: {message}   (one per line; or "(you are speaking for the first time)")

YOUR FATHER NOW SAYS: "{text}"
```

### `son_chat.schema`

```json
{ "type": "object", "required": ["reply", "attitude", "loyalty_change"], "properties": {
  "reply": { "type": "string", "description": "1–4 sentences, fully in character, in his own manner of speech" },
  "attitude": { "type": "string", "enum": ["loyal", "distant", "rebellious", "afraid", "grateful", "mocking"] },
  "loyalty_change": { "type": "integer", "minimum": "-{KONSEY.sohbet_sadakat}", "maximum": "{KONSEY.sohbet_sadakat}", "description": "How the father's words affected his loyalty" } } }
```
(Old: `cevap`, `tavir: sadik|mesafeli|asi|korkmus|minnettar|alayci`, `sadakat_degisim`.)

---

## Translation into a world language (konsey.js `cevir`)

### `linguist.translate.system`

```
You are the linguist of the world {w.ad}. You stay faithful to the rules of the {language.ad} language: first use words from the lexicon; derive missing words in the language's sound system and from existing roots. Explain in English.
```
(LANGUAGE-SPECIFIC: old "Türkçe açıkla" → "Explain in English.")

### `linguist.translate.prompt`

Variables: language entity `dil` (`ad, alt_tur, aciklama`); `{naming_rule}` = `w.isim_kurali` (note: always the main
world's rule even for a sub-world language — see bugs); `{syllables}` = first `KONSEY.ceviri_hece` keys of the
language's initial-syllable table + first `ceviri_hece` keys of its final-syllable table (`dilmotoru.fonoloji(dilId)`),
comma-joined; lexicon = first `KONSEY.ceviri_sozluk` rows of `sozluk` for that language ordered by id; `{text}` = input
(trimmed, max `KONSEY.ceviri_metin`).

```
LANGUAGE: {dil.ad} ({dil.alt_tur || "language"}). {dil.aciklama}
THE WORLD'S NAMING RULE: {naming_rule}
COMMON SYLLABLES: {syllables}
LEXICON:
{word} = {meaning}{?type:  ({type})}   (one per line; or "(empty)")

TO TRANSLATE: "{text}"
```

### `linguist.translate.schema`

```json
{ "type": "object", "required": ["translation", "pronunciation", "word_by_word", "new_words", "note"], "properties": {
  "translation": { "type": "string", "description": "The sentence's equivalent in this language" },
  "pronunciation": { "type": "string", "description": "Its pronunciation in Latin letters, syllable by syllable" },
  "word_by_word": { "type": "array", "items": { "type": "object", "required": ["word", "meaning"], "properties": { "word": { "type": "string" }, "meaning": { "type": "string" } } } },
  "new_words": { "type": "array", "maxItems": "{KONSEY.ceviri_yeni}", "items": { "type": "object", "required": ["word", "meaning", "type", "origin"], "properties": {
    "word": { "type": "string" }, "meaning": { "type": "string" },
    "type": { "type": "string", "enum": ["noun", "verb", "adjective", "suffix", "title", "place name", "proper name", "interjection", "number"] },
    "origin": { "type": "string" } } } },
  "note": { "type": "string", "description": "A grammar or culture note, one sentence" } } }
```
Old enum: `isim, fiil, sıfat, ek, unvan, yer adı, özel ad, ünlem, sayı`; old "pronunciation in Turkish letters" →
LANGUAGE-SPECIFIC, use Latin letters / simple English respelling.

---

## Birth of a new world (kozmos.js `dunyaDogur`)

### `cosmos.new_world.system`

```
You are the architect of the {w.ad} cosmos. Write in English (image prompts in English). Every world runs on a strange, concrete logic of its own; no clichés. The new world connects to the rest of the cosmos yet feels completely different.
```

### `cosmos.placement_guidance` — old `YERLESIM_YONU` (used when the caller gave no placement)

```
Choose the placement by looking at the stars above: if the light the world wants (yellow, red, blue, black sun, dead star…) exists at a star in the list, choose existing_star and give that star_id; most worlds are born this way. Choose a new sun only if no star of that kind is in the list, and fill in the star field. The world's description must not contradict the star it orbits.
```

### `cosmos.new_world.prompt` — old `dunyaDogusIstemi({ w, tur, ilham, yaratan, konum, yildizlar })`

Variables:
- `{header}` = `context.world_header(w)` (full, main world).
- `{worlds}` = `context.cosmos_lines()` or `- world#1 {w.ad}` when single.
- `{stars}` = for each star: `- star_id {id}: {ad} ({tur}){?aciklama:  — {aciklama}} — planets: {world#id name, … | none}` (planets = worlds with that `yildiz_id` and no parent); or `none`.
- `{foreign_gods}` = for each foreign god: `- {ad}{?unvan: , {unvan}} (world#{dunya_id}{?alanlar: ; {alanlar}})`; or `none`.
- `{placement}`: if `konum.yildiz_id` → `This world will orbit star_id {id}; its description must not contradict that star's light.`; else if `konum.ana_dunya_id` → `This world will be the moon of world#{id}.`; else if `konum.yeni_yildiz` → `A new sun is requested for this world: placement new_star, fill the star field (name, type, description).`; else `cosmos.placement_guidance`.
- `{creator_line}`: with a son creator `yaratan` → `The son {ad} ({unvan}; {alan1}/{alan2}) is giving birth to this world; the world should reflect his domains and temperament.`; else `The creator god {w.tanri_adi} is creating this world with his own hand.`
- `{type_line}`: requested type → `World type: {DUNYA_TURLERI[tur].ad} ({tur}).`; else `Choose the world type that would most enrich the cosmos.`
- `{inspiration}` = optional `ilham`.
- `{banned}` = old `yasakAdlar()`: first word of the names of the newest `DUNYA_DOGUS.yasak_kozmik_ad` worlds/stars/foreign gods (by creation age desc, id desc) followed by the newest `DUNYA_DOGUS.yasak_ad` canon regions/peoples/languages/places/sky bodies; deduplicated, comma-joined.
- `{cosmic_resource}`: if the cosmos already has one → `\nThe cosmos's travel resource already exists ({name}); leave the cosmic_resource field empty.`; else `\nThe cosmos has no travel resource yet: fill the cosmic_resource field; this substance will shape the politics of the whole cosmos.`

```
{header}

KNOWN WORLDS OF THE COSMOS:
{worlds}

STARS AND THEIR PLANETS:
{stars}

FOREIGN AND ANCIENT GODS OF THE COSMOS (old_god cannot be one of these; do not repeat their names):
{foreign_gods}
{placement}

{creator_line}
{type_line}{?inspiration: \nINSPIRATION: {inspiration}}

RULES: This world is another world; another language, another sky, another logic. First build a new dialect (not the same sounds as the main world), then derive ALL names from that dialect. Do NOT USE these names or their roots: {banned}.{cosmic_resource}
```

Inspiration texts produced by other callers:
- `cosmos.inspiration.mortal_intuition` (ufuk.js `sezgiyiDogur`): `The mortals called {me.ad}, while searching by {nasil}, found the way to a world no one knew.`
- `cosmos.inspiration.genesis_extra_world` (server.js at genesis with a "small/large cosmos" wizard setting): `The {n+2}th world of Creation; sister of the first world, yet entirely different.`
- Player (`epoch.dunyaYarat`): free text cut to `TANRI.ilham_uzunluk`.
- Son tool (`tools.js` world-birth tool): the son's `ilham` argument (see agents/tools part).

### `cosmos.new_world.schema` — old `SEMA`

Field order matters: `dialect` is described as "build THIS FIRST".

```json
{ "type": "object",
  "required": ["placement", "type", "dialect", "name", "language", "description", "cosmology", "gravity", "atmosphere", "time_factor", "day", "regions", "sky", "unique_resource", "natives", "image_prompt"],
  "properties": {
    "type": { "type": "string", "enum": ["ordinary", "ocean", "sand", "ice", "lava", "crystal", "living", "dead", "dream", "mirror", "gas"] },
    "dialect": { "type": "string", "description": "BUILD THIS FIRST: this world's own naming dialect — vowels, consonants, syllable patterns and affixes DIFFERENT from the main world. All names below (world, regions, sky, resource, natives) are derived with this dialect." },
    "name": { "type": "string", "description": "The world's name; in the new dialect, repeating no existing name" },
    "description": { "type": "string", "description": "3–5 sentences: what makes this world strange and concrete" },
    "cosmology": { "type": "string", "description": "This world's OWN view of creation and death, 2–4 sentences; do not repeat the main cosmology, extend it with this world's strangeness" },
    "gravity": { "type": "string", "enum": ["low", "ordinary", "high"] },
    "atmosphere": { "type": "string", "enum": ["none", "thin", "ordinary", "dense", "toxic"] },
    "time_factor": { "type": "number", "description": "Multiplier of years that pass in one age on this world ({DUNYA_FIZIK.zaman_en_az/100}–{zaman_en_cok/100}). In the dream realm time stretches, in the realm of the dead it nearly stops." },
    "day": { "type": "string", "description": "Its day, night and seasons in one sentence" },
    "placement": { "type": "string", "enum": ["existing_star", "new_star", "moon"], "description": "existing_star: a new planet orbiting a star in the list (most worlds are like this; choose this if the light the world wants is in the list); new_star: if a sun of a kind NOT in the list is needed, a distant system with its own sun (then the star field is mandatory); moon: the moon of an existing world" },
    "star_id": { "type": "integer", "description": "If existing_star, the id of the star it orbits" },
    "parent_world_id": { "type": "integer", "description": "If moon, the id of the world it orbits" },
    "star": { "type": "object", "description": "MANDATORY if you chose new_star: the sun of the new system (name, type, description); its name cannot be the name of any star or world in the list. If left empty no new star is born, the world settles at an existing star.",
      "properties": { "name": { "type": "string" }, "type": { "type": "string", "enum": ["yellow dwarf", "red giant", "blue giant", "binary star", "white dwarf", "dead star", "black sun", "broken star", "pulsar star"] }, "description": { "type": "string" } } },
    "regions": { "type": "array", "minItems": "{DUNYA_DOGUS.bolge_en_az}", "maxItems": "{DUNYA_DOGUS.bolge_en_cok}", "items": { "type": "object",
      "required": ["name", "subtype", "description", "danger", "fertility", "magic", "image_prompt"], "properties": {
        "name": { "type": "string" }, "subtype": { "type": "string", "description": "continent, inland sea, desert belt, archipelago, …" },
        "description": { "type": "string", "description": "2–4 sentences" },
        "danger": { "type": "integer", "minimum": 0, "maximum": 100 }, "fertility": { "type": "integer", "minimum": 0, "maximum": 100 }, "magic": { "type": "integer", "minimum": 0, "maximum": 100 },
        "image_prompt": { "type": "string", "description": "English photoreal prompt. {shared.image_prompt_rules}" } } } },
    "sky": { "type": "object", "description": "The most prominent body in this world's sky (moon, ring, wound, second sun…)", "required": ["name", "subtype", "description", "image_prompt"],
      "properties": { "name": { "type": "string" }, "subtype": { "type": "string" }, "description": { "type": "string" }, "image_prompt": { "type": "string", "description": "{shared.image_prompt_rules}" } } },
    "unique_resource": { "type": "object", "description": "A strange resource found only on this world; it should have an odd rule (it decays, it is addictive, it can only be gathered in one season…)",
      "required": ["name", "subtype", "description", "rule", "mechanics", "region_index", "image_prompt"], "properties": {
        "name": { "type": "string" }, "subtype": { "type": "string" }, "description": { "type": "string" }, "rule": { "type": "string" },
        "mechanics": { "type": "array", "maxItems": "{DUNYA_DOGUS.mekanik_en_cok}", "items": { "type": "string", "enum": ["decays", "addiction", "sentient", "depletion_price", "fixed", "sacred"] },
          "description": "The rule's counterpart in the engine: decays: rots as it is stored: its abundance falls fast every age, never renews. | addiction: a community using it weakens without it: whoever owns it for two ages becomes dependent and suffers withdrawal when it is lost. | sentient: it chooses who may dig it and makes demands; if a demand is not met it abandons its owner. | depletion_price: when its last drop is drawn a curse falls on its land and doomsday approaches. | fixed: it exists in a fixed amount in the cosmos: never renews; if one gains another loses. | sacred: it belongs to a god: if those who do not worship him dig it, the god grows angry." },
        "region_index": { "type": "integer", "minimum": 0, "maximum": "{DUNYA_DOGUS.bolge_en_cok - 1}" },
        "image_prompt": { "type": "string", "description": "{shared.image_prompt_rules}" } } },
    "cosmic_resource": { "type": "object", "description": "Fill ONLY if the cosmos has no travel resource yet: the single substance, unique to the cosmos, that makes travel between worlds (space folding) possible; long use causes addiction and a side effect. It has a deposit on this world.",
      "properties": { "name": { "type": "string" }, "description": { "type": "string" },
        "rule": { "type": "string", "description": "How it is extracted, how it is used, what it makes possible" },
        "side_effect": { "type": "string", "description": "The price of long use: mutation, memory loss, the colour of the eyes…" },
        "region_index": { "type": "integer", "minimum": 0, "maximum": "{bolge_en_cok - 1}" }, "image_prompt": { "type": "string", "description": "{shared.image_prompt_rules}" } } },
    "language": { "type": "object", "description": "This world's native language: matching the dialect exactly", "required": ["name", "subtype", "description", "words"], "properties": {
      "name": { "type": "string" }, "subtype": { "type": "string" }, "description": { "type": "string" },
      "words": { "type": "array", "minItems": "{DUNYA_DOGUS.kelime_en_az}", "maxItems": "{DUNYA_DOGUS.kelime_en_cok}", "items": { "type": "object", "required": ["word", "meaning", "type", "origin"], "properties": {
        "word": { "type": "string" }, "meaning": { "type": "string" }, "type": { "type": "string", "enum": ["noun", "verb", "adjective", "suffix", "title", "place name", "proper name", "interjection", "number"] }, "origin": { "type": "string" } } } } } },
    "old_god": { "type": "object", "description": "OPTIONAL: an old or foreign god who existed on this world before the pantheon, with worshippers of its own (not on every world; only if the world's logic requires it). It CANNOT be one of the cosmos's existing foreign gods: both its name and identity must be new.",
      "properties": { "name": { "type": "string" }, "title": { "type": "string" }, "domains": { "type": "string", "description": "Two domains, separated by \"/\"" }, "description": { "type": "string" },
        "attitude": { "type": "integer", "minimum": -100, "maximum": 100, "description": "Toward the newly arrived pantheon: -100 hostile, +100 friendly" }, "image_prompt": { "type": "string", "description": "{shared.image_prompt_rules}" } } },
    "natives": { "type": "array", "maxItems": "{DUNYA_DOGUS.yerli_en_cok}", "description": "Optional: living beings that existed on this world before the gods (a species or a people)", "items": { "type": "object",
      "required": ["kind", "name", "subtype", "description", "region_index", "image_prompt"], "properties": {
        "kind": { "type": "string", "enum": ["people", "species"] }, "name": { "type": "string" }, "subtype": { "type": "string" }, "description": { "type": "string" },
        "region_index": { "type": "integer", "minimum": 0, "maximum": "{bolge_en_cok - 1}" }, "image_prompt": { "type": "string", "description": "{shared.image_prompt_rules}" } } } },
    "image_prompt": { "type": "string", "description": "English photoreal prompt: the whole world seen from orbit, with its star and sky. {shared.image_prompt_rules}" }
  } }
```

Old-to-new enum mapping (keep a mapping table in code if old saves are migrated):
type `olagan, okyanus, kum, buz, lav, kristal, yasayan, olu, ruya, ayna, gaz`; gravity `düşük, olağan, yüksek`;
atmosphere `yok, ince, olağan, yoğun, zehirli`; placement `mevcut_yildiz, yeni_yildiz, uydu`; star types
`sarı cüce, kızıl dev, mavi dev, ikiz yıldız, beyaz cüce, ölü yıldız, kara güneş, kırık yıldız, nabız yıldızı`;
mechanics `bozunur, bagimlilik, bilincli, tukenme_bedeli, sabit, kutsal`; native kind `halk, tur`.

World-type display names (`DUNYA_TURLERI[k].ad`): ordinary world, ocean world, sand world, ice world, lava world,
crystal world, living planet, realm of the dead, dream realm, mirror world, gas giant. (Biomes/palettes per type are
specified with the map module.)

---

## Fate's knowledge-graph repair (agonar.js)

Both calls go through `askKader('derinlik', …)` with measurement name "Network repair" — Haiku.

### `fate_bonds.node_line` — old `dugumSatiri(k)` (node key `o{id}` son or `v{id}` entity)

- son: `o{id} [son] {ad}{?unvan: , {unvan}}`
- entity: `v{id} [{tur}{?alt_tur:  / {alt_tur}}{?durum != 'kanon': , {durum}}] {ad}: {first round(AG.aciklama_kirp/2) chars of whitespace-collapsed description}`

### `fate_bonds.suggest.system`

Variables: `{world}`; `{max}` = `AG.oneri_tavan`; `{max_event}` = `max(AG.oneri_tavan, AG.olay_oneri_tavan)`;
`{types}` = `ONERI_TURLERI` = narrative bond types except `ilgili` plus `taraf`:
`anlatir (tells of), sever (loves), korkar (fears), kehanet_eder (prophesies), yasaklar (forbids), pesinde (pursues),
yoldas (companion), parcasi (part of), kaynagi (source of), neden_oldu (caused), kutlar (celebrates), soyundan
(descends from), taraf (party to)`. English keys for the new app: `tells_of, loves, fears, prophesies, forbids,
pursues, companion, part_of, source_of, caused, celebrates, descends_from, party_to`.

```
You are Fate, the scribe of the world {world}. To records that sit disconnected in the knowledge network you add only the bonds that the narrative and the chronicle genuinely support. Without evidence you add no bond: an empty list is a valid answer. Each bond is chosen only from that record's CANDIDATES; no invented ids. The reason is in English, concrete and short (why they are connected). At most {max} bonds per record; at most {max_event} for an event (war, disaster): events are the centre of the network, connect to it the participants, victims and consequences the chronicle mentions with it. Types: {types}. One bond per pair: choose one type between the same two records, do not add a reciprocal or a second type; skip pairs already connected. "part_of" goes from the part to the whole (tradition → people, language → people, spirit → region, person → community; not the reverse). "companion" is only between living beings and communities (mortal, species, army, spirit, faction, cult, people; son) and describes something concrete lived through together. A shared theme, motif or image alone is not a reason: do not create a bond for such a pair.
```

### `fate_bonds.suggest.prompt`

For each target record (blank line between records):
```
RECORD {fate_bonds.node_line(v)}
CANDIDATES:
- {fate_bonds.node_line(candidate)} ({why})
```
`why` labels: `mentioned together in the chronicle {n} times`, `its location`, `its maker`, `its creator`, `in the same place`, `a notable of its world`.

### `fate_bonds.suggest.schema`

```json
{ "type": "object", "required": ["bonds"], "properties": { "bonds": { "type": "array", "items": { "type": "object",
  "required": ["record", "other", "direction", "type", "reason"], "properties": {
    "record": { "type": "string" }, "other": { "type": "string" },
    "direction": { "type": "string", "enum": ["from_record", "from_other"] },
    "type": { "type": "string", "enum": "{ONERI_TURLERI}" }, "reason": { "type": "string" } } } } } }
```
(Old: `baglar[{kayit, diger, yon: kayittan|digerinden, tur, gerekce}]`.)

### `fate_bonds.name_related.system`

```
You are Fate, the scribe of the world {world}. For each bond, look at the narratives of both ends and choose a concrete type ({types}). If none fits but the bond is meaningful, say "related" and state the relation clearly in the reason. If the bond is meaningless, say "close". The reason is in English, short and concrete.
```

### `fate_bonds.name_related.prompt`

One entry per bond (numbered from 1):
```
no {i}: {node_line(source)}
   → {node_line(target)}
```

### `fate_bonds.name_related.schema`

```json
{ "type": "object", "required": ["decisions"], "properties": { "decisions": { "type": "array", "items": { "type": "object",
  "required": ["no", "decision", "reason"], "properties": {
    "no": { "type": "integer" }, "decision": { "type": "string", "enum": "{ONERI_TURLERI + ['related', 'close']}" }, "reason": { "type": "string" } } } } } }
```
(Old: `kararlar[{no, karar: …|ilgili|kapat, gerekce}]`.)

Validation regexes applied to reasons (**LANGUAGE-SPECIFIC: rewrite in English**):
- `SHARED_THEME` (old `ORTAK_TEMA`): reason only says the two share a theme/motif/image ("theme in common", "shares the
  same motif", "similar image", "carries the theme") → reject.
- `DENIAL` (old `INKAR`): reason denies the bond ("no direct bond/relation/connection", "there is no link", "cannot be
  linked", "indirect", "not visible", "relation unknown", "a meaningful bond") → a `related` decision with such a reason
  is turned into `close`.

---

## Mortal agent turn (olumluler.js)

Mortals = canon entities of types people (`halk`), faction (`hizip`), cult (`tarikat`), settlement (`yerlesim`), named
mortal (`olumlu`) and intelligent species (`tur` with intelligence `>= OLUMLU_AJAN.zeka_esigi`). Agent turn via the
Agent SDK tool loop (MCP server name `olumlu`).

### `mortal.turn.system` — old `sistemMetni(v, w, costs)`

Variables: `{name}` = `v.ad`; `{world}` = `w.ad`; `{type}` = lowercased display name of `VARLIK_TURLERI[v.tur]`;
`{subtype}` = `v.alt_tur || type name`; `{ap}` = `OLUMLU_AJAN.ap`; `{costly}` / `{free}` = tool names split by
`bedavaMi(description)` (a description containing "Free" / "costs no action" and not containing "N action" → free);
`{madness}` when `sagduyu(v) < KORKU.bulaniklik_esik`; `{captive}` = captor entity (`esirMi`); `{tics}` =
`ortakTikler()` (shared speech tics — defined in the agents.js part); `{motif}` = `shared.tired_images(v.dunya_id)`.

```
You are {name}: a {type} ({subtype}) in the world {world}. You are not a god; you are a mortal or a community of mortals.
You are not an AI; you live the shared will of this community/being. You think and speak in English.
You have interests: to survive, to grow, to grow rich, to be worthy of your god, to take revenge on your enemies, to make your name last.
You have {ap} actions this age; an unused action does not carry over to the next age, it burns when the age ends.{madness} {costs}{captive}
RULES:
- Everything you do must rest on your land, your resources, your religion and your past. You cannot forge a weapon from a resource you do not own; you cannot build a harbour on a shore you have not seen.
- Derive names from your own language; if you have no language, first found one with dil_kur. Give new words an origin.
- No clichés: every item, monument and tradition should have a concrete material, a price, a strange detail.
- Your final message must be ONLY a 1–2 sentence saying inside «…», in the voice of your community. Do not summarize your actions, do not mention tool names or #numbers.{?tics: \n- Words that have become tics in sayings: «w1», «w2». Do NOT USE these or words derived from the same root in your saying.}{?motif: \n- {motif}}
```
- `{madness}` = `\nYOUR MIND IS CLOUDED (sanity {v.statlar.sagduyu}): you hear voices and misread signs; your decisions may be strange, fearful or too bold. Live this, but as a believed delusion, not deliberate madness.`
- `{costs}` with the server's lists: `Actions that spend: {costly, comma-joined}. Actions that do not spend: {free}.`; fallback when the list is unavailable: `Production, building, discovery, developing knowledge, migration/settlement, culture, trade, diplomacy, adventure, sabotage, preaching, war, defying a god and denial spend an action; deriving words, learning, worshipping, claiming and reading do not.`
- `{captive}` = `\nYOU ARE A CAPTIVE: {captor.ad} holds you prisoner. You can only try to escape (kac) or speak; you can take no other action.`

(LANGUAGE-SPECIFIC: "You think and speak in Turkish" → English. The guillemets «…» are a parsing contract — keep them.)

### `mortal.turn.prompt` — old `istem(extra)`

Variables: `{age}`; `{manifestation}` / `{dream}` blocks (unread messages addressed to this entity with
`niyet='tezahur'` / `niyet='ruya'`); `{context}` = `mortal.context(v)`; `{opportunities}` = `mortal.opportunities(v)`
or `(no notable opportunity)`; `{extra}` = resume/continuation text; `{ap_left}`.

```
Age {age}. It is your turn.

{manifestation}{dream}{context}

OPPORTUNITIES:
{opportunities}

{extra}{?ap_left > 0: Use your {ap_left} actions in your community's interest, then speak your saying. | You have no actions left; only speak your saying.}
```
- `mortal.turn.manifestation` = `THE CREATOR APPEARED TO YOU ({creator} appeared before your eyes while you were awake and spoke with you; this is not a dream, it is a plain command and a sign; you must act accordingly):\n"{text}"\n…\n\n`
- `mortal.turn.dream` = `A DREAM FROM YOUR GOD (the creator god {creator} appeared to you in a dream; how you interpret it and whether you obey it is up to you, but it cannot leave you unmoved):\n"{text}"\n…\n\n`
- `mortal.turn.resume_extra` (turn already half-done this age when the turn starts) = `Your turn was cut short earlier; continue from where you left off.\n\n`
- `mortal.turn.continuation_extra` (used by `devamPromptu(done, reason)` after a crash/timeout/turn-limit/no-saying) = `Your turn was left half-done ({reason}).\n\n{done block}`, where done block = `ALREADY DONE THIS AGE (they stand in the world; do not repeat them, build on them; your saying should carry this age's tone but not list what you did):\n- {tool} → {result summary}\n…\n\n` (empty if nothing done). Reasons (from llm.js): `connection error ({first 120 chars})`, `timeout`, `step limit reached`, `you finished without speaking your saying`.

Completion check: the turn is complete only if `sozuAyikla(final text)` is non-empty (text inside «…»; else text after
"saying:"; quotes stripped).

### `mortal.context` — old `baglamMetni(v, w, { tam })`

Sections in order (each is a `bolumluButce` section; the header gets its full length, others floor
`BAGLAM.bolum_taban`; total budget `BAGLAM.olumlu_baglam × (tam ? BAGLAM.arac_kat : 1)`; overall hint "look with
dunyaya_bak, varlik_ara and varlik_incele"):

1. `context.world_header(w, v.dunya_id ?? 1, { short: true })`
2. `context.world_line(v.dunya_id ?? 1)`
3. `\nYOU:\n{budget(varlikDetay(v.id), OLUMLU_ARAC.sen_butce, "look at yourself with varlik_incele")}`
4. if `v.derinlik.ozel`: `\nYOUR CHARACTER AND WAY OF LIFE:\n- {key}: {value}` (budget `karakter_butce`)
5. `\nYOUR GOD: ` + one of `son#{id} {ad}, {unvan} ({alan1}/{alan2})` | `foreign god {ad}{?unvan: , {unvan}} (foreign#{id}; not of the pantheon)` | `you do not worship anyone yet`
6. if folk beliefs exist for this people (`halk_inanc` where `halk_id = v.id`): `\nTHE GODS IN YOUR TELLING (call them by these names when you speak):\n- {name} (son#{ogul_id}): {story}`
7. `\nYOUR LANGUAGE: ` + `#{id} {ad}. From its lexicon: {word = meaning; …(first 30) | empty}` or `you have no language yet; you can give birth to your own language with dil_kur`
8. `\nYOUR LAND: ` + `#{id} {ad}{?mapinfo:  ({elevation}{?coast: , coastal}; neighbouring regions: #{id} {name}, … | none)}` or `unknown`
9. `NEAR YOU:\n{entity_line per canon entity in the same top region, excl. regions, max 40}` (budget `yakin_butce`, hint "look with dunyaya_bak and varlik_ara"; or `(nobody)`)
10. `\nRECENT EVENTS:\n{context.recent_chronicle(OLUMLU_ARAC.olay_satir, worldId)}` (budget `olay_butce`, hint "see the chronicle")
11. `\nWHAT YOU KNOW: {#id name (branch name), … | no knowledge yet}` + `\nKNOWLEDGE IN THE WORLD: {all canon technologies of this world: #id name (branch)}` (budget `bilgi_butce`; or `none`)
12. `\nWHAT YOU OWN: resources: {#id name (abundance N), … | none}; items: {#id name, … | none}`
13. `\nRECORDS THAT MENTION YOU:\n[Age {cag}] {text}` (last 10 chronicle rows whose `varlik_ids` contains v.id exactly; budget `ani_butce`; or `(none)`)
14. `\nLANGUAGES OF THE WORLD:\n{dilSatirlari(6, null, worldId)}` (budget `dil_butce`; or `(none yet)`)
15. if other worlds exist: `\nOTHER WORLDS:\n{cosmos_lines(own)}` + either `\nKNOWN ROUTES OUT OF THIS WORLD (sefere_cik):\n{rotaSatirlari}` or `\nThere is no known route out of this world (rota_kesfet).`
16. if journeys under way: `\nYOUR ONGOING EXPEDITIONS: {intent}, {remaining} ages left, {people} people; …`

Section order rationale (keep): recent events come after "near you" so that truncation from the end does not drop them.

### `mortal.opportunities` — old `olumluFirsatlari(v)` (from firsatlar.js)

Bullet list (`- ` prefix). If `FIRSAT.gerilim_once = 1`, tension lines (enemies, wars, feuds, tense neighbours) are
moved to the top (`gerilimOnde`). `FK.liste` = list cap, `FK.liste_kisa` = short cap, `sec(list, n)` = pick up to n.
"Near" = communities (`halk, yerlesim, hizip, tarikat`) for which `yakinMi(v, x)` holds.

| Condition | Line |
|---|---|
| near communities with neither trade nor enmity | `Those you could trade or ally with: #{id} {name}, …` |
| near communities with an enemy bond and (not both communities, or community relation < 0) | `Your enemies ({actions}; or offer peace, make weapons, seek allies): #{id} {name}, …` where actions = `open war with savas_ilan_et` (only if no ongoing war with any of them), `strike secretly with sabotaj` (faction/cult/mortal only), `learn their secrets with casus_ag_kur` |
| (community self) near communities without enmity and relation `<= -FIRSAT.gergin_komsu` | `Your tense neighbours (relations are bad; watch them with casus_ag_kur{?faction/cult/mortal: , weaken them with sabotaj}, settle accounts with savas_ilan_et, or soothe them with trade and gifts): #{id} {name} ({relation}), …` |
| learnable knowledge from near communities passing `ogrenebilirMi` | `Knowledge you could learn from neighbours (ogren): #{id} {tech} ({community} knows it), …` |
| unowned canon resources in own top region | `Resources on your land (claim with sahiplen, then produce): …` |
| species with danger `>= FIRSAT.canavar_tehlike` in own region | `Dangerous creatures on your land (weapons, walls, war to hunt them): …` |
| knows nothing | `You have no knowledge yet: develop a piece of knowledge or learn one.` |
| no language | `You have no language yet: dil_kur.` |
| community with blood feuds | `Your blood feuds (revenge, war, or peace with blood money): …` |
| community, near communities with relation `>= FIRSAT.dost_komsu`, not allied, not enemies | `Neighbours who love you (alliance or marriage is easily accepted): #{id} {name} ({relation}), …` |
| community party to an ongoing war | `You are at war: #{id} {war}; …. Make weapons, build walls, seek allies or offer peace.` |
| people/settlement with food `< FIRSAT.ambar_erzak` | `Your granary is emptying (food {erzak}, bread ×{price/100, 1 decimal}): establish trade, learn farming knowledge, or found a settlement on fertile land.` |
| people/settlement whose worst class satisfaction `< FIRSAT.hosnutsuz` | `Your people's {class} class is discontent (satisfaction {m}); it may revolt. Make a law, found a tradition, or attend to their grievance.` |
| ruins / god corpses / empty tombs (tags) or dead entities tagged ruin in own region | `Ruins on your land (kalinti_ara): …` |
| per dead god it worships | `Your god {name} died (Age {age}); the devotion of those awaiting his return is {d}/{DERIN_YASAM.dirilis_adanmislik}. With dirilis_ayini offer a prayer, a wealth offering, a blood sacrifice or a life sacrifice{?corpse: ; a ritual held at {corpse name} is stronger}.` |
| community or mortal and `KESIF.arac_tur > 0` | with exploration pressure reasons: `Unknown lands are calling you ({reasons}): with toprak_kesfet find a region not on the map or a new place near you{?people/settlement: ; your pioneers can settle there (yerles)}.` else `Beyond the horizon there are lands no one has yet seen: with toprak_kesfet you can find a new region or a new place near you.` |
| community or mortal with a route method | `The sky is open to you: search for the way to other worlds with rota_kesfet{?worlds without known route: (worlds whose way no one knows: …)}; rarely you sense a world no one knows.` |
| …without a route method but unreachable known worlds exist | `There are worlds in the sky whose way you do not know (…): if you learn sky-sailing, gate lore or path-knowing (ogren, bilgi_gelistir) you can search for the way there.` |
| an active known route from this world | `There is an open way to other worlds: organize an exploration expedition with sefere_cik; you will find new lands on the world you reach.` |
| named mortal with strength + agility `>= FIRSAT.meydan_guc` | `You are strong enough to defy a god (tanriya_meydan_oku): son#{id} {name}, …` (active sons on the same world) |
| own god cursed it or is a rebel | `Your god {name} has become a burden to you; you can turn away from him with inkar_et.` |
| no god and gods available | `You have no god; you could worship: son#{id} {name} ({alan1}/{alan2}), …` |

### Mortal tool descriptions (model-facing text)

The full descriptions, field descriptions and result/rejection texts of the mortal tools are given in the mortal tool
catalogue of `08-agents-and-tools.md` (section "Mortal tool catalogue"). They are prompt text too: the prompts module
should own them under ids `mortal.tool.<english_name>.description` and `mortal.tool.<english_name>.field.<field>`.

---

## Genesis wizard text (sihirbaz.js) — `genesis.wizard_settings`

Inserted into the genesis prompt (agents.js `genesis`) when the player used the creation wizard. Variables: validated
settings `p` (`sablon, buyu, karanlik, teknoloji, dil, halk, kozmos`).

`degree(n, adj)`: `n >= 80` → `very {adj}`; `>= 60` → `{adj}`; `>= 40` → `moderately {adj}`; `>= 20` → `slightly {adj}`;
else `hardly {adj} at all`.

```
CREATION SETTINGS{?template:  (template: {template name})}:
- Magic density {buyu}/100: the world is {degree(buyu, "magical")}. The regions' magic values should be close to this.
- Darkness {karanlik}/100: the world is {degree(karanlik, "dark")}. Danger values and the sons' temperaments should match this.
- Technology age: {tech label}. The peoples' tools, weapons and buildings are at this level.
- Language structure: {language label}. The naming rule and all names have this sound texture.
- Cosmos: {cosmos label}.
```

Option tables (translate fully; keys kept for storage):
- technology: `tas` stone age, `tunc` bronze age, `demir` iron age, `ortacag` middle ages, `ronesans` renaissance, `buhar` steam and gunpowder.
- language: `akici` flowing, vowel-rich, soft (l, m, n, y); `sert` hard-consonanted, short-syllabled (k, t, g, r); `girtlak` guttural, from deep in the throat (h, ğ, q, kh) — **LANGUAGE-SPECIFIC: replace "ğ" with an English-friendly example, e.g. (h, gh, q, kh)**; `islikli` hissing, fricative (s, ş, z, ç) — **replace with (s, sh, z, ch)**; `uzun` long, agglutinative, many-syllabled; `karisik` free.
- cosmos: `tek` single world; `kucuk` small cosmos ({1 + SIHIRBAZ.kucuk_kozmos} worlds); `buyuk` large cosmos ({1 + SIHIRBAZ.buyuk_kozmos} worlds).

Templates (`SABLONLAR`) — preset seed/tone/sliders:

| key | name | tone | magic | darkness | tech | language | peoples | cosmos | seed |
|---|---|---|---|---|---|---|---|---|---|
| karanlik_fantazi | Dark fantasy | gloomy, merciless, hope comes dear | 60 | 80 | demir | girtlak | 3 | tek | A world built on top of the corpses of gods who once died; every bounty comes from a rotting. |
| mitoloji | Mythic age | epic, solemn, full of prophecies | 70 | 40 | tunc | akici | 3 | tek | Continents born from the sea and mountains bearing the sky; every river has a name, every name has a price. |
| kozmik_korku | Cosmic horror | uneasy, silent, in the shadow of incomprehensible things | 50 | 90 | buhar | islikli | 2 | kucuk | A cosmos where something behind the sky is waking and the stars go out one by one. |
| masal | Fairy tale | warm, strange, wise and a little sad | 85 | 25 | ortacag | uzun | 4 | tek | A world where animals talk, forests change places, and dreams are taxed. |
| yildiz_mitosu | Star myth | vast, full of wonder, cosmic in scale | 55 | 45 | ronesans | akici | 3 | buyuk | A cosmos where star-wind fills the ships' sails and the worlds are strung like beads on a thread. |
| kum_ve_kul | Sand and ash | harsh, arid, proud | 35 | 60 | tunc | sert | 3 | tek | A world where the sun once fell and left a desert; where water is worth more than money and ashes speak prophecies. |
| primordial_dawn | Primordial dawn | raw, wondrous, everything happens for the first time | 75 | 35 | tas | karisik | 5 | tek | A young world still warm from its making; the first fires are being lit, the first words spoken, and every hill waits for a name. |
| crowns_and_knives | Crowns and knives | cunning, political, every oath hides a blade | 12 | 55 | ortacag | sert | 4 | tek | A world where magic has all but faded and power lives in bloodlines, marriages and whispered debts; every throne is one betrayal from falling. |
| drowned_world | Drowned world | salt-worn, restless, ruled by the tides | 55 | 50 | demir | islikli | 3 | tek | A world where the sea swallowed the continents long ago; peoples live on scattered islands, reefs and floating towns, and every map is wrong by the next tide. |
| long_winter | Long winter | stern, enduring, warmth must be earned | 40 | 65 | demir | girtlak | 3 | tek | A world whose sun has dimmed for a thousand years; the ice creeps further south each winter and the peoples burn their histories to stay warm. |
| after_the_fall | After the fall | elegiac, scavenging, haunted by a greater past | 45 | 70 | ortacag | uzun | 3 | tek | A world built on the ruins of a civilization far greater than any living one; its towers still hum, its roads lead nowhere, and no one remembers how its wonders were made. |
| sky_islands | Sky islands | airy, adventurous, hopeful | 70 | 30 | ronesans | akici | 3 | kucuk | A cosmos of shattered worlds whose fragments drift on rivers of wind; peoples sail between the islands on kite-ships, and falling past the edge is the oldest fear. |
| age_of_engines | Age of engines | curious, inventive, bright with possibility | 30 | 30 | buhar | karisik | 4 | tek | A world where the first engines have just learned to breathe; tinkers rival priests, railways cut through sacred forests, and every invention wakes an old spirit. |

The last seven templates are new in Weavers of the Void and have no legacy key; their key is the stored `GenesisTemplate` value.

Validation (`sihirbazTemizle`): numbers rounded and clamped (magic/darkness 0–100, peoples 1–`SIHIRBAZ.halk_en_cok`);
choices accepted only if an own key of the table (prototype keys like `__proto__` rejected) — defaults
`demir`/`karisik`/`tek`; blanks filled from the template; tone cut to 300 chars, seed to 2000 chars.

---

## Known bugs / design smells (prompts)

1. Language: every prompt instructs "write in Turkish"; output post-processors (`ekDuzelt`, `toplulukIci`, regex
   scrubbers `istemMetni`, `ORTAK_TEMA`, `INKAR`, motif root finder `kokBul`) are Turkish-specific. Replace with English
   rules; do not port suffix harmony.
2. The council schema's `minItems/maxItems` and `enum` for son ids depend on runtime data — build the JSON schema per
   call; do not cache.
3. Translation prompt always passes the main world's naming rule (`w.isim_kurali`) even when the language belongs to a
   sub-world with its own dialect; use `isimKurali(language.dunya_id)`.
4. `cosmos.new_world` uses a hard-coded 300 s timeout (not a rule) — violates the "no untunable constant" rule; add
   `WORLD_BIRTH.timeout_s`.
5. Schema descriptions with getters (`get description()`, `get minItems()`) are evaluated lazily at serialization —
   in the new app build schemas from current rules at call time.
6. Fate bond prompt node ids are strings ("v12", "o3"); the model often returns bare numbers — the old code strips a
   leading `v` only for `record`, not for `other`; normalise both.
7. The mortal system prompt depends on the server's tool list (costly/free split from description regex). Make
   "free" an explicit tool attribute instead of parsing description text.
8. Shared-context fragments (`world_header`, `recent_events`) are rebuilt per call with many DB queries; cache per
   age where safe.

---

## Prompt fragments (injected text blocks)

These are not standalone LLM calls. They are deterministic text builders whose output is spliced into the prompts of other agents (son turn, mortal turn, foreign-god deepening). The new prompts module should expose each one as a pure function `(state) -> str` with the ids below. All of them read live tunables. Placeholders are written `{name}`. Turkish source modules: `src/firsatlar.js`, `src/itibar.js`, `src/hedef.js`, `src/yabanci.js`.

General conventions:
- Entity references inside fragments use `#{id} {name}`; sons use `son#{id} {name}` (Turkish `oğul#`); threads use `thread#{id}` (Turkish `iplik#`); worlds use `world#{id}` (Turkish `dünya#`). The model needs these ids to call tools. (The chronicle/narrative sanitizer strips them later; see 08/09 main sections.)
- `sec(list, n)` = first `min(n, opportunities.list)` items.
- Every opportunity builder returns lines joined by `\n`, each prefixed with `- `.

| id | Source function | Injected into | Where |
|---|---|---|---|
| `fragment.opportunities.son` | `ogulFirsatlari(son, tools)` | son turn user prompt (`ogulIstemi`) | section `=== OPPORTUNITIES (the world's current tensions; use your tools to touch them) ===`, budget-trimmed to `CAGIRMA.firsat_butce` (2500 chars) with hint "look with dunya_ozeti" |
| `fragment.opportunities.mortal` | `olumluFirsatlari(v)` | mortal (olumlu) turn user prompt (`olumluler.js`) | section `OPPORTUNITIES:`; if empty → `(no notable opportunity)` |
| `fragment.opportunities.creator` | `tanriFirsatlari()` | NOT a model prompt: UI panel "What you can do this age" via `GET /api/firsatlar` (returns array of strings) | UI only |
| `fragment.reputation_line` | `itibarSatiri(son)` | son turn system prompt (`sonSistemi`), in "HOW YOU CREATE" block | one bullet line |
| `fragment.creator_wishes` | `babaninIstegi(w)` (agents.js; uses `tutkular()` + `SENARYOLAR`) | son turn system prompt, right after reputation/rebellion lines | 0–2 lines |
| `fragment.scenarios` | `SENARYOLAR[key].ad / .aciklama` | inside `fragment.creator_wishes`; also UI | |
| `fragment.foreign_god.*` | `YT_*` constants in yabanci.js | foreign-god deepening schema + prompt (`yabanciDerinlestir`), world summary, UI | |

---

## `fragment.opportunities.son` — son opportunities (ogulFirsatlari)

Purpose: give the son agent a concrete, tool-oriented list of the world's current tensions so it does not waste actions or only create; push conflict. Called every son turn. Inputs: the son record, and `tools` = list of tool names actually available to this son this turn (`aracListesi` from `buildSonServer`). If `tools` is null (legacy callers) no tool filtering happens.

### Scope
- `multi = (count of worlds) > 1`.
- `vs` = all canon entities (`kanonlar()`), restricted, when `multi` and the son has an `active_world`, to entities whose `world_id` is null or equals the son's active world.
- "Thinking" entity (`dusunen`): type in {people (halk), settlement (yerlesim), faction (hizip), cult (tarikat), mortal (olumlu)}.
- `count(t)` = number of `vs` with type t.

### Lines, in generation order (before reordering)

1. **Vitality** (always one of two variants). Let
   `vitality = "The world has {count(people)} peoples, {count(settlement)} settlements, {count(mortal)} named mortals, {count(species)} species, {count(cult)+count(faction)} organizations."`
   Condition "lifeless": `count(people) < regions + opportunities.alive_people_extra` OR `count(mortal) < opportunities.alive_mortal` OR `count(settlement) < count(people)` OR `count(species) < opportunities.alive_species` (regions = count of region entities in vs).
   - If lifeless:
     `BREATHE LIFE: {vitality} This age your first living creation (halk_yarat, olumlu_yarat, yerlesim_kur, tur_yarat, cult/faction) does NOT spend an action; you must create something living.`
     + if there are uninhabited regions (regions with no people/settlement whose top region is it): ` Regions where no one lives: {first opportunities.list_short of "#{id} {name}", comma-joined}.`
     + if `count(mortal) < alive_mortal`: ` Named mortals (king, seer, craftsman, hero, bandit) give the world a face.`
   - Else: `{vitality} Each age your first living creation does not spend an action.`
2. **Empty worlds** (only if `multi`): for each empty world (`bosDunyalar()`, world with no people, settlement or named mortal) other than the son's active world (default 1):
   `NEW WORLD: {world.name} ({world.type}) is utterly empty; it has no people, settlement or named mortal[ (for {empty_ages} ages) if empty_ages]. Its habitable regions: {first EMPTY_WORLD.opportunity_regions (bosdunya.js firsat_bolge, default 3) of "#{id} {name} (fertility {fertility})"}. Move to {world.name} (world#{id}) with dunyaya_yonel and create its first people: your first living creation spends no action, the son who creates the first people gains +{EMPTY_WORLD.first_people_essence (ilk_halk_oz, 30)} essence, +{EMPTY_WORLD.first_people_fame (ilk_halk_un, 10)} fame and becomes that world's only god.`
3. **Narrow lands**: `T = toprakOlcusu(son.active_world ?? 1)` (ufuk.js: `narrow = no regions OR communities/regions >= EXPLORATION.narrow_community`). If `T.narrow`:
   `NARROW LANDS: in the world of {world name or "Your world"} {T.regions} regions crowd {T.communities} communities ({T.ratio} per region)[; the most crowded: {first list_short "#{id} {name} ({communities})"}]. Open a new region on the map with bolge_yarat (valley, plateau, island, coast) or a new place with yer_yarat (forest, lake, cave, pass)[: if EXPLORATION.land_free > 0 → "this age your first land creation spends no action"][, if land_essence or land_fame → "+{EXPLORATION.land_essence} essence, +{EXPLORATION.land_fame} fame you gain"]; the crowded mortals migrate there.`
   (ufuk.js tunables: `toprak_bedava` 1, `toprak_oz` 10, `toprak_un` 3.)
4. **Isolated world** (only if `multi`): if there is no active, known route (`rotalar` aktif=1, bilinen=1) touching the son's world:
   `ISOLATED WORLD: there is no known open road from your world to other worlds[; if a hidden route (bilinen=0) touches it → "but the cosmos has a hidden passage; if the mortals learn sky-sailing or gate-lore they will find it (bilgi_ilham_et)"]. Create a gate, bridge or ship with arac_yarat (giving hedef_dunya_id): the road opens and mortals set out.`
5. **Stagnant cosmos**: if `current_age − max(world.created_age) >= EXPLORATION.cosmos_stagnant` (ufuk.js `kozmos_durgun`, 8):
   `STAGNANT COSMOS: no new world has been born since Age {last}. Birth a new world with dunya_dogur; the son who creates its first people is rewarded.`
6. **Dead siblings** (death module): for each other son with state dead and a resurrection status `D = dirilisDurumu(k)`:
   `status = "the devotion of those awaiting his return {D.devotion}/{DEEP_LIFE.resurrection_devotion (100)}[, at the earliest {D.remaining} ages from now]"`.
   - If relation(son,k) <= −DEATH.scatter_auto_relation (olum.js `dagit_oto_iliski`, 40):
     `YOUR ENEMY IS DEAD: {k.name} died in Age {D.death_age} ({status}). With kemikleri_dagit ({DEATH.scatter_cost (30)} essence) you can delay his return; his cult becomes your enemy.`
   - Else:
     `DEAD SIBLING: {k.name} died in Age {D.death_age} ({status}). Help his return with kardesini_dirilt: rite {DEATH.sibling_rite_cost (45)} essence, descent to the realm of the dead {DEATH.sibling_descent_cost (70)} essence (risky), bargain with a foreign god {DEATH.sibling_bargain_cost (25)} essence and one loyal community.`
7. **Rival siblings**: active other sons with relation <= −`rival_relation`, sorted most hostile first, first `list_short`:
   `RIVAL SIBLINGS: {"son#{id} {name} (relation {r})", ...}. Tell this feud: challenge openly with meydan_oku, curse his creation or worshipper with lanetle, incite your worshippers against his with savas_kiskirt, steal his worshippers with ruya_gonder; or make a peace covenant with ahit_et.`
8. **Rivals' famous mortals**: mortals in vs whose patron son `hami(v)` exists, is not this son, and relation(son, patron) < −`rival_sibling`; sorted by charisma desc; first `list_narrow`:
   `Your rivals' famous mortals (you can take their lives with can_al; very expensive and may fail): {"#{id} {name} ({patron name}; {canAlmaBedeli(v)} essence, {canAlmaSansi(v,son).percent}%)", ...}`
9. **Unclaimed communities**: thinking entities with no patron:
   `Communities that worship no one (win them with mucize, bilgi_ver or ruya_gonder; or found a neighbouring people with halk_yarat): {sec(list, list) "#{id} {name}"}`
10. **Rivals' worshippers**: thinking entities whose patron is another son with relation < −`rival_relation`:
    `Your rivals' worshippers (steal with ruya_gonder, lanetle or afet_gonder): {"#{id} {name} ({patron name})"}`
11. **Your worshippers** (`mine` = thinking entities whose patron is this son):
    `Your worshippers (with mucize, secilmis_ilan_et, bilgi_ver or olumlu_yarat give them a hero): {"#{id} {name}"}`
12. **Ongoing hostilities in this world**: active `dusman` bonds entity→entity, newest first, both ends in vs, first `list_wide`, both canon:
    `Ongoing hostilities (bless one side or make peace with mucize, fan the flames with savas_kiskirt, settle it with olay_baslat): {"#{a} {A} ↔ #{b} {B}" joined by "; "}`
13. **Teachable knowledge**: if technology entities exist and some of `mine` does not know one of them:
    `Knowledge you can teach your worshippers (with bilgi_ver): {"#{id} {name} ({branch name or ?})"}`
    If no technology entity at all: `There is no knowledge (technology) in the world yet; you could inspire the mortals' first knowledge.`
14. **Languageless communities**: people/faction/cult with no spoken language:
    `Communities without a language (create one with dil_yarat; give the "konusur" (speaks) bond to that community): {first list_short}`
    If no language at all: `There is no language in the world yet.`
15. **Unowned resources**: resources with no active `sahip` (owns) bond pointing to them:
    `Unowned resources (harvest with kaynak_sag or forge an item from it with esya_dov): {sec}`
16. **Rival siblings' creations**: entities created by another son with relation < −`rival_sibling`; last `list_wide`:
    `Your rival siblings' creations (transform, curse, set something against them): {...}`
17. **Rebels against you**: canon entities with active `dusman` bond entity→this son:
    `Those who rose against you (your creatures and mortals; punish, curse, send a disaster, or win back their hearts): {...}`
18. **Your enemies**: canon entities this son has `dusman` or `lanetledi` (cursed) bonds toward:
    `Those who defied or denied you (vengeance or forgiveness): {...}`
19. **Godless**: entities tagged `tanrısız` (godless):
    `Godless communities (can be won with a miracle or a dream; they gnaw at your father's power): {sec}`
20. **Rebel siblings**: other sons with `rebel` flag:
    `Siblings who rebelled against your father (join them, make a covenant, or stand by your father): {"son#{id} {name}"}`
21. **Low loyalty**: if this son is not a rebel and `passion.loyalty < opportunities.loyalty_rebellion`:
    `Your loyalty is low: if you wish you can openly defy your father with isyan_et.`
22. **Dead siblings (bones/cult)**: for every dead other son `o` (note: duplicates line 6 in spirit):
    `Your dead sibling {o.name}[ (his bones #{corpse_id})][; resurrection cult #{t.id} {t.name}, devotion {t.devotion}/{DEEP_LIFE.resurrection_devotion} (miracles raise devotion)]: you can bring him back, use his bones for your own purpose, or scatter his cult.` (Cult = cult in vs tagged `dirilis:{o.id}`.)
23. **Existence**: if `son.existence (varlik, default 60) <= opportunities.fading`:
    `YOUR EXISTENCE IS {varlik}: you are about to go out. Win worshippers (miracle, dream, give knowledge), create legends and works that tell of you, protect your anchor; otherwise you die.`
    Else if `mine` empty: `No one worships you; a god without worshippers is forgotten in time. Win a community.`
24. **Your worshippers' wars**: event entities subtype `savaş` tagged `suruyor` (ongoing) whose tags include `taraf:{id}` for one of `mine`; first `list_short`:
    `Your worshippers' ongoing wars (bless their side, strengthen their army, send a disaster on the enemy, or a peace miracle): {"#{id} {name}" joined by "; "}`
25. **Hungry worshippers**: people/settlements in `mine` with society food stock (`erzak`, default 50) < `hungry_food`:
    `Your hungry worshippers (fertility miracle, give knowledge: agriculture): {...}`
26. **Wonders**: entities tagged `harika`:
    `The world's wonders (bless, curse, mark as a target): {first list_short}`
27. **Threads** (stories): `ipl` = open threads, excluding great expeditions (`buyuk`), and when `multi` only those whose majority world (world with most related entities; null if none) is null or the son's world; sorted most stagnant first.
    - stale = `stagnant_ages >= opportunities.stagnant_age`; long = `max(progress, advancers count) >= opportunities.long_thread`.
    - If stale: this line is **unshifted to the very top**:
      `STORIES ABOUT TO BE FORGOTTEN (no one has touched them for {stagnant_age}+ ages; advance them or Fate will close them as "forgotten"): {first list_short "thread#{id}: {text first 90 chars}" joined by " · "}`
    - If long: `Long stories that must reach their climax (make a creation that carries it to its conclusion by giving iplik_id; Fate closes it): {first list_narrow "thread#{id}"}`
28. **Pending prophecies**: prophecy entities in vs, own ones first then oldest; first `list_narrow`:
    `Prophecies awaiting fulfilment (fulfil with a creation or event, get them misread, or make them come to nothing; Fate sees): {"#{id} {name} (Age {age}[, yours])"}`
29. **Open thread ids**: if any: `Open stories: {"thread#{id}", ...} (give iplik_id in a creation)`
30. **Silence**: `last` = max age of messages sent by this son. If none, or `current_age − last >= opportunities.silence_ages`:
    `{"You have never spoken with your siblings" | "{n} ages you have not said a word to your siblings"}: kardese_seslen, ahit_et and babaya_dua spend no action; alliances and debts are made with them.`

### Post-processing
1. **Tension first** (`gerilim_once` = 1): lines matching the regex `HASIM|Hasım|düşman|Düşman|savaş|Savaş|isyan|ayaklan|kafa tut|Kan dava|DÜŞMAN|gergin|Gergin` (English equivalents: RIVAL|rival|enemy|ENEMY|war|rebel|rose against|defied|blood feud|tense) are moved before all others, preserving relative order. (Since the "about to be forgotten" line was unshifted earlier, it stays first unless a tension line exists.) LANGUAGE-SPECIFIC: the keyword regex must be rewritten for English text — better: tag each line with a `tension: bool` flag at generation time instead of regex.
2. **Tool filter** (`aracaGore`): tool names are found with `/\b[a-z]+(?:_[a-z]+)+\b|\b(?:mucize|lanetle)\b/` excluding names ending in `_id` (field names like `iplik_id`, `hedef_dunya_id`). If a line names no tools → kept. If none of its named tools are available → line dropped. Otherwise each unavailable tool is removed together with its clause (preceding connector `; ya da`/`,`/` ya da `/` ve `/`;`, the name, and following words up to the next `,`, `;`, `)`, ` ya da `, `. ` or end), then punctuation is tidied. LANGUAGE-SPECIFIC (connector words "ya da"/"ve"): in the new app build lines from structured `(tool, clause)` lists and render only available ones instead of regex surgery.
3. Join as `- {line}` per line.

---

## `fragment.opportunities.mortal` — mortal opportunities (olumluFirsatlari)

Injected into the mortal agent turn prompt: `Age {age}. Your turn.\n\n{manifestation}{dream}{context}\n\nOPPORTUNITIES:\n{this or "(no notable opportunity)"}\n\n{extra}` (the full mortal prompt is in the mortal-agent section). Input `v` = the acting entity (mortal, people, settlement, faction, cult, species, army…). `vs` = all canon entities except v. `COMMUNITY = [people, settlement, faction, cult]`. `nearby` = communities in vs where `yakinMi(v, x)` (olumluler.js proximity).

Lines in order:
1. Trade candidates: nearby with no `ticaret` and no `dusman` bond with v:
   `Those you could trade or ally with: {sec "#{id} {name}"}`
2. Enemies: nearby with a `dusman` bond AND (v or x not a community OR community relation `tIliski(v,x) < 0`), first `list`. Strike options = comma list of: `open war with savas_ilan_et` (only if no ongoing war event tagged both `taraf:{v}` and `taraf:{x}` exists for any of them), `strike in secret with sabotaj` (only if v is faction/cult/mortal), `learn their secrets with casus_ag_kur` (always):
   `Your enemies ({strike options}; or offer peace, produce weapons, seek allies): {...}`
3. Tense neighbours (only if v is a community): nearby communities with no `dusman` bond and relation <= −`tense_neighbour`:
   `Your tense neighbours (bad blood between you; watch them with casus_ag_kur[, weaken them with sabotaj — if v faction/cult/mortal], settle accounts with savas_ilan_et, or appease with trade and gifts): {first list_short "#{id} {name} ({relation})"}`
4. Learnable knowledge: from nearby x where `ogrenebilirMi(v,x)`, technologies x knows that v does not:
   `Knowledge you can learn from neighbours (ogren): {sec of "#{id} {name} ({x.name} knows it)" unique}`
5. Resources in your land: resources whose top region equals v's top region and v has no `sahip` bond:
   `Resources in your land (claim them, then produce): {sec}`
6. Dangerous creatures: species with danger >= `monster_danger` in same top region:
   `Dangerous creatures in your land (weapons, walls, war to hunt them): {...}`
7. If v knows no technology: `You have no knowledge yet: develop or learn some.`
8. If v has no spoken language: `You have no language yet: dil_kur.`
9. If v is a community:
   - Blood feuds (`topluluk_iliski.kan_davasi` not null, other side canon): `Your blood feuds (revenge, war, or peace by blood-price): {...}`
   - Friendly neighbours: nearby communities with relation >= `friendly_neighbour` and neither `muttefik` (ally) nor `dusman` bond: `Neighbours who love you (alliance or marriage is easily accepted): {first list_short "#{id} {name} ({relation})"}`
   - At war: ongoing war events tagged `taraf:{v}`: `You are at war: {"#{id} {name}" joined "; "}. Produce weapons, build walls, seek allies or offer peace.`
10. If v is people or settlement (`t = toplumOf(v)` society economy):
    - If food stock (default 50) < `granary_food`: `Your granary is emptying (food {food}, bread ×{(price.food or 100)/100, 1 decimal}): set up trade, learn agriculture, or found a settlement on fertile land.`
    - Most discontent class (lowest satisfaction in `t.m`): if satisfaction < `discontent`: `Your people's {class} class is discontented (satisfaction {m}); they may rise up. Make a law, found a tradition, or attend to their grievance.`
11. Remains: entities in vs tagged `harabe`/`tanrı cesedi`/`boş mezar` (ruin / god corpse / empty tomb) in same top region, plus dead entities tagged `harabe` in same top region; first `list_short`:
    `Remains in your land (kalinti_ara): {...}`
12. Dead god: for each dead son that v actively worships (`tapar` bond), with resurrection status D:
    `Your god {D.name} died (Age {D.death_age}); the devotion of those awaiting his return is {D.devotion}/{DEEP_LIFE.resurrection_devotion}. Offer prayer, a tribute of wealth, a blood sacrifice or a life sacrifice with dirilis_ayini[; a rite performed at {D.corpse.name} is stronger].`
13. Exploration (v community or mortal, and `EXPLORATION.tool_per_age (arac_tur) > 0`): `kb = kesifBaskisi(v)` (reasons list from ufuk.js: "lands are narrow", "hunger"/"poverty", "there is an explorer among them ({name})", "explorer-spirited", "road knowledge").
    - With reasons: `Unknown lands call you ({reasons comma-joined}): with toprak_kesfet find a region not on the map or a new place nearby[; if people/settlement: "your pioneers can settle there (yerles)"].`
    - Without: `Beyond the horizon lie lands no one has seen yet: with toprak_kesfet you can find a new region or a new place nearby.`
14. Sky roads (v community or mortal): `roadless` = known worlds other than v's world with no active known route from v's world.
    - If `yolYontemi(v)` (v has a travel method): `The sky is open to you: search for the road to other worlds with rota_kesfet[ (worlds whose road no one knows: {first list_short names})]; rarely you sense a world no one knows.`
    - Else if roadless: `There are worlds in the sky whose road you do not know ({first list_short}): if you learn sky-sailing, gate-lore or road-knowing (ogren, bilgi_gelistir) you can search for the road there.`
    - If an active known route touches v's world: `There is an open road to other worlds: organize an expedition with sefere_cik; in the world you reach you find new lands.`
15. Candidate gods: active sons, restricted (when multiple worlds) to sons whose active world equals v's world.
    - If v is mortal and strength + agility >= `challenge_strength`: `You are strong enough to defy a god (tanriya_meydan_oku): {"son#{id} {name}"}`
    - If v's patron cursed v (`lanetledi` bond son→v) or the patron is a rebel: `Your god {name} has become a burden; you can turn from him with inkar_et.`
    - If v has no patron and gods exist: `You have no god; those you could worship: {"son#{id} {name} ({domain1}/{domain2})"}`

Post-processing: tension-first reorder (same regex as son), then `- ` join. NOTE: no tool filtering for mortals (tools named may not be available).

---

## `fragment.opportunities.creator` — creator (player) panel (tanriFirsatlari)

UI-only list (not sent to a model) returned by `GET /api/firsatlar`:
1. Unanswered prayers to the creator (`mesajlar` kime_tip='t', cevaplandi=0) count n>0: `{n} prayers await an answer: answering raises loyalty and faith.`
2. Unclaimed thinking communities: `There are {n} communities that worship no one (e.g. {first list_narrow names}): a miracle or a dream binds them to you.`
3. Rebel sons: `Rebel sons: {names}. You can crush the rebellion or forgive.`
4. Fading sons (not dead, existence <= `fading_son`): `Sons being forgotten: {"{name} ({existence})"}. Blessing strengthens their existence.`
5. Doomsday: if `doom >= DENGE.kiyamet_esik (100) × doom_warning / 100`: `Doomsday clock {doom}/{threshold}: miracles, faith and a council can push it back.`
6. Godless worlds (not forgotten, has a canon people, no active son there): `Worlds without a god: {names}. Send a son or summon a new one.`
7. Stale threads (stagnant >= `stagnant_age`): `{n} stories are about to be forgotten; a revelation could revive them.`
8. If creator essence >= `rich_essence`: `You have {essence} essence: enough for a new world, son or star.`

---

## Tunables — `FIRSAT` (opportunities)

| English key | Turkish key | Default | Min | Max | Group | English label |
|---|---|---|---|---|---|---|
| `list` | `liste` | 5 | 1 | 50 | Opportunities | Max records listed in one opportunity line |
| `stagnant_age` | `durgun_cag` | 4 | 1 | 100 | Opportunities | Ages untouched after which a story counts as "about to be forgotten" |
| `long_thread` | `uzun_iplik` | 8 | 1 | 200 | Opportunities | Advances after which a story "must conclude" |
| `silence_ages` | `sessizlik_cag` | 3 | 1 | 100 | Opportunities | Ages of not speaking to siblings before a reminder |
| `rich_essence` | `zengin_oz` | 150 | 0 | 100000 | Opportunities | Creator essence for a "big action" reminder |
| `list_short` | `liste_kisa` | 4 | 1 | 50 | Opportunities | Max records in short opportunity lists |
| `list_narrow` | `liste_dar` | 3 | 1 | 50 | Opportunities | Max records in the narrowest lists |
| `list_wide` | `liste_genis` | 6 | 1 | 100 | Opportunities | Max records in wide lists |
| `alive_people_extra` | `canli_halk_fazla` | 2 | 0 | 50 | Opportunities | "Breathe life": if peoples do not exceed regions by this much |
| `alive_mortal` | `canli_olumlu` | 6 | 0 | 200 | Opportunities | "Breathe life": if named mortals fewer than this |
| `alive_species` | `canli_tur` | 4 | 0 | 200 | Opportunities | "Breathe life": if species fewer than this |
| `rival_relation` | `rakip_iliski` | 20 | 0 | 100 | Opportunities | Relation with a sibling counted as rival: below minus this |
| `rival_sibling` | `hasim_kardes` | 25 | 0 | 100 | Opportunities | Relation with a sibling whose creations are shown as targets: below minus this |
| `loyalty_rebellion` | `sadakat_isyan` | 40 | 0 | 100 | Opportunities | Rebellion reminder if loyalty below this |
| `fading` | `sonmek_uzere` | 20 | 0 | 100 | Opportunities | "You are about to go out" if existence at or below this |
| `fading_son` | `solan_ogul` | 25 | 0 | 100 | Opportunities | To the creator: sons at or below this existence are "being forgotten" |
| `doom_warning` | `kiyamet_uyari` | 50 | 0 | 100 | Opportunities | Creator doomsday reminder: % of threshold |
| `hungry_food` | `ac_erzak` | 60 | 0 | 1000 | Opportunities | Worshippers count as hungry: food below this |
| `granary_food` | `ambar_erzak` | 60 | 0 | 1000 | Opportunities | Mortal "your granary is emptying": food below this |
| `discontent` | `hosnutsuz` | 30 | 0 | 100 | Opportunities | A class counts as discontented: satisfaction below this |
| `friendly_neighbour` | `dost_komsu` | 45 | −100 | 100 | Opportunities | Loving neighbour: community relation at or above this |
| `monster_danger` | `canavar_tehlike` | 50 | 0 | 100 | Opportunities | Dangerous creature: danger at or above this |
| `tense_neighbour` | `gergin_komsu` | 20 | 0 | 100 | Opportunities | Mortal "tense neighbour": community relation below minus this (with no hostility bond) |
| `tension_first` | `gerilim_once` | 0 | 0 | 1 | Opportunities | Tension lines (rivals, hostilities, wars, rebellion) go first in the list (1 on, 0 off) |
| `challenge_strength` | `meydan_guc` | 110 | 0 | 1000 | Opportunities | Suggest defying a god: strength + agility at or above this |

External tunables read (defined elsewhere): `BOS.firsat_bolge` (3), `BOS.ilk_halk_oz` (30), `BOS.ilk_halk_un` (10) in bosdunya.js; `KESIF.toprak_bedava` (1), `toprak_oz` (10), `toprak_un` (3), `kozmos_durgun` (8), `arac_tur` (1), `dar_topluluk` in ufuk.js; `OLUM.dagit_oto_iliski` (40), `dagit_bedel` (30), `kardes_ayin_bedel` (45), `kardes_inis_bedel` (70), `kardes_pazarlik_bedel` (25) in olum.js; `DERIN_YASAM.dirilis_adanmislik` (100) defined in derin.js; `DENGE.kiyamet_esik` (100).

---

## `fragment.reputation_line` — how the son sees his father (itibarSatiri)

Injected as one bullet in the son system prompt. Computation (`itibarHesapla(son)`), window = last `reputation.window` ages, decay factor per age `a = (decay/100)^(current_age − event_age)`:
- Chronicle rows of this son in window of types {god, star, ascension, rebellion, resurrection}: text matching LOVE regex (`kutsadı|affetti|bağışladı|duasına cevap|diriltti|yeniden doğurdu|yıldız daha kondurdu` or `yükseldi` = blessed, forgave, pardoned, answered prayer, resurrected, re-birthed, added a star, ascended) adds `love_event × a`; FEAR regex (`yıldırımla çarptı|zincire vurdu|sürgüne gönderdi|isyanını bastırdı|lanetledi` = struck with lightning, chained, exiled, crushed rebellion, cursed) adds `fear_event × a`. Both update `last_contact`. LANGUAGE-SPECIFIC: regex on Turkish chronicle text — replace with event-kind tags.
- Messages from creator to son in window: non-threat adds `message_love × a` to love; threat (`niyet='tehdit'`) adds `threat_fear × a` to fear; updates `last_contact`. If son has a current order, `last_contact = current_age`.
- Unanswered prayers (son→creator, unanswered, intent not 'chat', in window): `unanswered_weight = Σ a`.
- `love = clamp(round(love_base + love + loyalty/loyalty_divisor − unanswered_weight × unanswered_love + manual.love + event.love), 0, 100)` (loyalty default `loyalty_default`).
- `fear = clamp(round(fear_base + fear + (creator_mood.anger(default anger_default) − anger_default)/anger_divisor + (chained ? chain_fear : 0) + manual.fear + event.fear), 0, 100)`.
- `oblivion = clamp(round((current_age − last_contact) × oblivion_per_age + unanswered_weight × unanswered_oblivion + max(0, interest_threshold − creator_mood.interest(default interest_default))/interest_divisor + manual.oblivion), 0, 100)`.
- Label (first match): forgotten (`unutulan`) if oblivion >= forgotten_oblivion AND love < forgotten_love AND fear < forgotten_fear; hated (`nefret edilen`) if fear >= hated_fear AND love < hated_love AND loyalty < hated_loyalty; respected (`saygı duyulan`) if fear >= respected_fear AND love >= respected_love; feared (`korkulan`) if fear >= feared_fear; loved (`sevilen`) if love >= loved_love; distant (`uzak`) if oblivion >= distant_oblivion; else known (`tanınan`).

Template:
`- HOW YOU SEE YOUR FATHER: {label} (love {love}, fear {fear}, oblivion {oblivion}[, you have {n} unanswered prayers]). {BEHAVIOUR[label]} Your father's passions: {passion names, comma-joined}.`

BEHAVIOUR table (full translation):
| label (TR) | English label | Text |
|---|---|---|
| unutulan | forgotten | Your father has forgotten you. His orders do not come, your prayers go unanswered; you are free to go your own way, perhaps do something great that catches his attention. |
| nefret edilen | hated | You hate your father: you fear him but do not love him. You obey his orders outwardly and resist in secret. |
| saygı duyulan | respected | You both respect and are wary of your father; serving his passions raises you. |
| korkulan | feared | You fear your father. You obey his orders; you avoid deeds that would anger him. |
| sevilen | loved | You love your father. Serving his passions makes you happy; do something that will please him. |
| uzak | distant | Your father is distant; he hardly mentions you. You are torn between winning his attention and learning to live without him. |
| tanınan | known | There is an ordinary bond between you and your father. |

Other effects of the same module (not prompt text, documented for completeness): each epoch `itibarCagi` stores the reputation, shifts loyalty/anger by label (loved +loved_loyalty; respected +respected_loyalty, +respected_anger; feared +feared_anger anger; hated −hated_loyalty_loss loyalty, +hated_anger; forgotten −forgotten_loyalty_loss; distant −distant_loyalty_loss), decays manual pushes by `manual_keep`% (dropping |v| < manual_threshold) and event traces by `event_keep`%, writes chronicle `"{son} now sees his father as a {label} god."` when label changes to forgotten/hated/loved/feared; re-reads automatic passions. Manual push API `itibarIt` clamps each axis to ±`manual_cap` and errors `"Manual push at limit: each can be at most ±{cap} (World rule ITIBAR.elle_tavan = {cap}); pushes decay every age."`; dead son error `"{name} is dead; your place in his eyes no longer changes."`. God-power traces `tanriGucuIzi(kind)` for kinds `em` (essence drain), `yut` (devour a son), `alcalt` (demote), `sok` (rip out a power) add fear/love deltas to target and witnessing siblings, clamped ±`event_cap`.

### Creator passions (TUTKULAR) — full table
| key | name (TR) | English name | hint (English) |
|---|---|---|---|
| duzen | düzen | order | laws, borders, things falling into place |
| kaos | kaos | chaos | destruction, disaster, unexpected transformations |
| guzellik | güzellik | beauty | art, works, songs, crafted things |
| bilgi | bilgi | knowledge | taught knowledge, writing, discovery |
| savas | savaş | war | conflict, heroism, conquest |
| merhamet | merhamet | mercy | miracles, healing, forgiven crimes |
| yaratim | yaratım | creation | new worlds, stars, new peoples |
| sessizlik | sessizlik | silence | an untouched world, children left to themselves |

`tutkular(w)`: if `w.creator_passions` is manual (`otomatik=false`) → that list (filtered to valid keys); else stored auto list or `tutkuOku(w)`. `tutkuOku`: over creator chronicle rows (no son, last `passion_window` ages, types god/world_birth/star/cosmic/revelation/order), add `passion_points` per regex hit: creation (`world_birth` type or text "ignited|star|birthed a world|created"), chaos ("disaster|sent|flood|plague|earthquake|storm|curse"), mercy ("miracle|healing|fertility|heard the prayer|forgave"), knowledge ("taught|knowledge|writing"), order ("law|sealed|statute|order"), war ("war|conquest|army"), beauty ("work|song|art|beautiful"). Top `passion_count` with >0; if none → `['silence']`. LANGUAGE-SPECIFIC: Turkish keyword regex over chronicle text; port as event-kind counting. Manual set: 1..passion_count valid keys, else error `"Choose at least one passion (at most {n})."`; chronicle `"{creator} introduced himself: his passions are {names}."`.

---

## `fragment.creator_wishes` — the father's wishes (babaninIstegi, agents.js)

Injected in son system prompt after the reputation/rebellion line. Up to two lines, each only if non-empty:
- `FATHER'S PASSIONS (deeds that feed these please him): {"{name} ({hint})" joined "; "}`
- `FATHER'S GREAT AIM (ongoing scenario): {"{scenario.name}: {scenario.description}" joined " · "}` — for every row in `senaryolar` with state `suruyor` (ongoing).

## `fragment.scenarios` — scenario names and descriptions (SENARYOLAR)

Player-chosen goals. Name/description are live (thresholds interpolated). Numbers 0–100 are written as Turkish words in the original (`yazi`, `Yazi`) — LANGUAGE-SPECIFIC: render digits or English number words.

| key | Name (English) | Description (English) | Progress / completion | Points key |
|---|---|---|---|---|
| kiyamet_uzak | Keep doomsday {doom_far_ages} ages away | Let the doomsday clock never reach {round(threshold × doom_far_threshold/100)} for {doom_far_ages} ages. | fail if doom >= that limit ("The doomsday clock reached {doom}/{threshold}."); done when ages since start >= doom_far_ages; text "{elapsed}/{n} ages · clock {doom}/{threshold}" | doom_far_points |
| tek_inanc | Unite all peoples in one faith | Let every people in the world worship the same god (a son or you); at least {one_faith_peoples} peoples. | % = largest same-god group / peoples; done when peoples >= min and all same | one_faith_points |
| kayip_yildiz | Rekindle the lost star | Let a dead star or black sun burn again. | needs a star of type "reborn star" count > count at start; if no dead and no reborn: "There is no dead star in the cosmos yet; one must go out first." | lost_star_points |
| bes_dunya | A {world_count}-world cosmos | Let there be at least {world_count} worlds in the cosmos and a people living on each. | done when worlds with a canon people >= world_count | world_points |
| uzun_baris | {peace_ages} ages of peace | Let no war stay open for {peace_ages} ages in a row. | counter +1 each epoch end with zero active `dusman` entity bonds, else reset; text "{n} wars ongoing; counter reset" | peace_points |
| kozmik_guc | A civilization reaching for the stars | Let a people rise to civilization stage {cosmic_stage} ("interstellar power"). | max stage of peoples/settlements >= cosmic_stage | cosmic_points |
| sadik_panteon | A loyal pantheon | Let no son rebel for {loyal_ages} ages; at the end let every son's loyalty be above {loyal_loyalty}. | fail on any new rebel or chronicle "isyan etti" (rebelled) after start ("A son rebelled."); done when elapsed >= loyal_ages and all active sons loyalty > loyal_loyalty | loyal_points |
| yeni_ufuklar | {horizon_lands} new lands | Let {horizon_lands} new lands enter the map (at least {horizon_regions} regions): by mortals' exploration, by the sons' or by your hand. | count region+place entities with id > max id at start | horizon_points |

Achievements (`BASARIMLAR`, UI + notifications only, never in prompts): first_world "{ordinal} sky" (cosmos has b_world worlds), three_stars "Constellation", prophecy "The word came true", resurrection "Return from death", crush_rebellion "The father's hand", ten_languages "Babel", million "Crowded world", first_prayer "Someone called you", cult "The creator's cult", first_voyage "Interstellar traveller", epic "Epic completed", ten_ages "God of {n} ages", fifty_ages "Ancient", eight_sons "Crowded pantheon", first_explorers "First explorers", sensed_world "Sensed world", peaceful "The weapons fell silent". Chronicle on scenario end: `"Aim fulfilled: {name}."` / `"Aim lost: {name}. {text}"`; on start `"{creator} set himself an aim: {name}."`. Score (`puan`): population `round(log10(1+pop) × score_population)`, diversity `min(score_diversity_cap, canon count)`, languages × score_language, worlds × score_world, max civ stage × score_stage, doom penalty `−round(doom/threshold × score_doom)`, plus achievement and completed-scenario points.

### Tunables — `HEDEF` (goals)
| English key | Turkish key | Default | Min | Max | Group | English label |
|---|---|---|---|---|---|---|
| doom_far_ages | kiyamet_uzak_cag | 20 | 1 | 200 | Doomsday | Scenario: ages to keep doomsday away |
| doom_far_threshold | kiyamet_uzak_esik | 80 | 1 | 100 | Doomsday | Scenario: point the clock must not reach (% of threshold) |
| score_doom | puan_kiyamet | 150 | 0 | 1000 | Doomsday | Score: doomsday penalty when the clock is at threshold |
| doom_far_points | kiyamet_uzak_puan | 300 | 0 | 10000 | Goals and achievements | Scenario points: keep doomsday away |
| one_faith_peoples | tek_inanc_halk | 3 | 1 | 100 | Goals and achievements | Scenario: min peoples united in one faith |
| one_faith_points | tek_inanc_puan | 250 | 0 | 10000 | Goals and achievements | Scenario points: all peoples one faith |
| lost_star_points | kayip_yildiz_puan | 200 | 0 | 10000 | Goals and achievements | Scenario points: rekindle the lost star |
| world_count | dunya_sayi | 5 | 1 | 100 | Goals and achievements | Scenario: worlds with a living people |
| world_points | dunya_puan | 250 | 0 | 10000 | Goals and achievements | Scenario points: many-world cosmos |
| peace_ages | baris_cag | 5 | 1 | 200 | Goals and achievements | Scenario: consecutive ages of peace |
| peace_points | baris_puan | 200 | 0 | 10000 | Goals and achievements | Scenario points: long peace |
| cosmic_stage | kozmik_basamak | 4 | 1 | 20 | Goals and achievements | Scenario: civilization stage to reach |
| cosmic_points | kozmik_puan | 300 | 0 | 10000 | Goals and achievements | Scenario points: star-reaching civilization |
| loyal_ages | sadik_cag | 10 | 1 | 200 | Goals and achievements | Scenario: ages without rebellion |
| loyal_loyalty | sadik_sadakat | 60 | 0 | 100 | Goals and achievements | Scenario: loyalty all sons must exceed |
| loyalty_default | sadakat_varsayilan | 50 | 0 | 100 | Goals and achievements | Scenario: assumed loyalty of a son with none recorded |
| loyal_points | sadik_puan | 250 | 0 | 10000 | Goals and achievements | Scenario points: loyal pantheon |
| horizon_lands | ufuk_toprak | 8 | 1 | 1000 | Goals and achievements | Scenario: new lands to open (region or place; by exploration, son or god) |
| horizon_regions | ufuk_bolge | 2 | 0 | 1000 | Goals and achievements | Scenario: how many of them must be regions |
| horizon_points | ufuk_puan | 250 | 0 | 10000 | Goals and achievements | Scenario points: new horizons |
| b_world | b_dunya | 2 | 1 | 100 | Goals and achievements | Achievement: worlds in the cosmos |
| b_world_points | b_dunya_puan | 50 | 0 | 10000 | Goals and achievements | Achievement points: new sky |
| b_star | b_yildiz | 3 | 1 | 100 | Goals and achievements | Achievement: stars in the cosmos |
| b_star_points | b_yildiz_puan | 40 | 0 | 10000 | Goals and achievements | Achievement points: constellation |
| b_prophecy_points | b_kehanet_puan | 40 | 0 | 10000 | Goals and achievements | Achievement points: prophecy fulfilled |
| b_resurrection_points | b_dirilis_puan | 60 | 0 | 10000 | Goals and achievements | Achievement points: return from death |
| b_rebellion_points | b_isyan_puan | 40 | 0 | 10000 | Goals and achievements | Achievement points: rebellion crushed |
| b_language | b_dil | 10 | 1 | 1000 | Goals and achievements | Achievement: spoken languages |
| b_language_points | b_dil_puan | 50 | 0 | 10000 | Goals and achievements | Achievement points: Babel |
| b_population | b_nufus | 1000000 | 1000 | 2000000000 | Goals and achievements | Achievement: total population of peoples |
| b_population_points | b_nufus_puan | 60 | 0 | 10000 | Goals and achievements | Achievement points: crowded world |
| b_prayer_points | b_dua_puan | 30 | 0 | 10000 | Goals and achievements | Achievement points: first prayer |
| b_cult | b_kult | 3 | 1 | 100 | Goals and achievements | Achievement: communities worshipping the creator directly |
| b_cult_points | b_kult_puan | 60 | 0 | 10000 | Goals and achievements | Achievement points: creator's cult |
| b_voyage_points | b_sefer_puan | 50 | 0 | 10000 | Goals and achievements | Achievement points: interstellar traveller |
| b_epic_points | b_efsane_puan | 80 | 0 | 10000 | Goals and achievements | Achievement points: epic completed |
| b_age | b_cag | 10 | 1 | 1000 | Goals and achievements | Achievement: ages passed (first threshold) |
| b_age_points | b_cag_puan | 50 | 0 | 10000 | Goals and achievements | Achievement points: first age threshold |
| b_ancient_age | b_kadim_cag | 50 | 1 | 10000 | Goals and achievements | Achievement: ages passed (ancient) |
| b_ancient_points | b_kadim_puan | 150 | 0 | 10000 | Goals and achievements | Achievement points: ancient |
| b_son | b_ogul | 8 | 1 | 100 | Goals and achievements | Achievement: sons alive at once |
| b_son_points | b_ogul_puan | 50 | 0 | 10000 | Goals and achievements | Achievement points: crowded pantheon |
| b_peace_peoples | b_baris_halk | 3 | 1 | 100 | Goals and achievements | Achievement: min peoples for a war-free age |
| b_peace_points | b_baris_puan | 40 | 0 | 10000 | Goals and achievements | Achievement points: weapons fell silent |
| b_explore_points | b_kesif_puan | 40 | 0 | 10000 | Goals and achievements | Achievement points: first explorers (mortals found an unknown land) |
| b_sense_points | b_sezgi_puan | 80 | 0 | 10000 | Goals and achievements | Achievement points: sensed world (a world sensed by mortals was born) |
| score_population | puan_nufus | 20 | 0 | 1000 | Goals and achievements | Score: per tenfold of population |
| score_diversity_cap | puan_cesitlilik_tavan | 150 | 0 | 100000 | Goals and achievements | Score: max points for record diversity |
| score_language | puan_dil | 5 | 0 | 1000 | Goals and achievements | Score: per language |
| score_world | puan_dunya | 25 | 0 | 1000 | Goals and achievements | Score: per world |
| score_stage | puan_basamak | 20 | 0 | 1000 | Goals and achievements | Score: per step of the highest civilization stage |

### Tunables — `ITIBAR` (reputation)
| English key | Turkish key | Default | Min | Max | Group | English label |
|---|---|---|---|---|---|---|
| decay | sonum | 75 | 0 | 100 | Reputation | Share of past events' effect kept each age (%) |
| window | pencere | 8 | 1 | 100 | Reputation | Ages looked back in reputation |
| passion_window | tutku_pencere | 5 | 1 | 100 | Reputation | Ages looked back when reading passions |
| passion_points | tutku_puan | 2 | 1 | 100 | Reputation | Points each act adds to its passion |
| passion_count | tutku_sayi | 3 | 1 | 8 | Reputation | Max number of creator passions |
| love_event | sevgi_olay | 14 | 0 | 100 | Reputation | Love from a blessing, pardon or ascension |
| fear_event | korku_olay | 22 | 0 | 100 | Reputation | Fear from lightning, chains or exile |
| message_love | mesaj_sevgi | 5 | 0 | 100 | Reputation | Love from each non-threatening word of the creator |
| threat_fear | tehdit_korku | 10 | 0 | 100 | Reputation | Fear from each threat |
| loyalty_default | sadakat_varsayilan | 50 | 0 | 100 | Reputation | Assumed loyalty if none recorded |
| anger_default | ofke_varsayilan | 20 | 0 | 100 | Reputation | Assumed anger of son/creator if none recorded |
| interest_default | ilgi_varsayilan | 60 | 0 | 100 | Reputation | Assumed creator interest if none recorded |
| love_base | sevgi_taban | 20 | 0 | 100 | Reputation | Love base |
| loyalty_divisor | sadakat_bolen | 4 | 1 | 100 | Reputation | Loyalty contribution to love: loyalty / this |
| unanswered_love | cevapsiz_sevgi | 6 | 0 | 100 | Reputation | Love lost per unanswered prayer |
| fear_base | korku_taban | 10 | 0 | 100 | Reputation | Fear base |
| anger_divisor | ofke_bolen | 3 | 1 | 100 | Reputation | Creator anger to fear: (anger − default) / this |
| chain_fear | zincir_korku | 15 | 0 | 100 | Reputation | Extra fear of a chained son |
| oblivion_per_age | unutma_cag | 12 | 0 | 100 | Reputation | Oblivion per contactless age |
| unanswered_oblivion | cevapsiz_unutma | 5 | 0 | 100 | Reputation | Oblivion per unanswered prayer |
| interest_threshold | ilgi_esik | 40 | 0 | 100 | Reputation | Oblivion grows if creator interest below this |
| interest_divisor | ilgi_bolen | 2 | 1 | 100 | Reputation | Disinterest to oblivion: missing interest / this |
| forgotten_oblivion | unutulan_unutma | 60 | 0 | 100 | Reputation | Min oblivion for "forgotten" |
| forgotten_love | unutulan_sevgi | 50 | 0 | 100 | Reputation | "Forgotten": love below |
| forgotten_fear | unutulan_korku | 50 | 0 | 100 | Reputation | "Forgotten": fear below |
| hated_fear | nefret_korku | 55 | 0 | 100 | Reputation | Min fear for "hated" |
| hated_love | nefret_sevgi | 35 | 0 | 100 | Reputation | "Hated": love below |
| hated_loyalty | nefret_sadakat | 35 | 0 | 100 | Reputation | "Hated": loyalty below |
| respected_fear | saygi_korku | 50 | 0 | 100 | Reputation | Min fear for "respected" |
| respected_love | saygi_sevgi | 50 | 0 | 100 | Reputation | Min love for "respected" |
| feared_fear | korkulan_korku | 50 | 0 | 100 | Reputation | Min fear for "feared" |
| loved_love | sevilen_sevgi | 55 | 0 | 100 | Reputation | Min love for "loved" |
| distant_oblivion | uzak_unutma | 40 | 0 | 100 | Reputation | Min oblivion for "distant" |
| loved_loyalty | sevilen_sadakat | 2 | 0 | 50 | Reputation | Per-age loyalty gain of a son who loves his father |
| respected_loyalty | saygi_sadakat | 1 | 0 | 50 | Reputation | Per-age loyalty gain (respect) |
| respected_anger | saygi_ofke | 1 | 0 | 50 | Reputation | Per-age anger gain (respect) |
| feared_anger | korkulan_ofke | 2 | 0 | 50 | Reputation | Per-age anger gain (fear) |
| hated_loyalty_loss | nefret_sadakat_kayip | 2 | 0 | 50 | Reputation | Per-age loyalty loss (hate) |
| hated_anger | nefret_ofke | 3 | 0 | 50 | Reputation | Per-age anger gain (hate) |
| forgotten_loyalty_loss | unutulan_sadakat_kayip | 2 | 0 | 50 | Reputation | Per-age loyalty loss (forgotten) |
| distant_loyalty_loss | uzak_sadakat_kayip | 1 | 0 | 50 | Reputation | Per-age loyalty loss (distant) |
| manual_keep | elle_kalan | 60 | 0 | 100 | Reputation | Share of a manual push kept each age (%) |
| manual_threshold | elle_esik | 2 | 1 | 100 | Reputation | Manual push decayed below this is deleted |
| manual_cap | elle_tavan | 60 | 0 | 100 | Reputation | Max manual push per axis |
| manual_love | elle_sevgi | 10 | 1 | 100 | Reputation | "Win his heart" button: love per click |
| manual_fear | elle_korku | 10 | 1 | 100 | Reputation | "Instil fear" button: fear per click |
| manual_oblivion | elle_unutma | 15 | 1 | 100 | Reputation | "Make him forget" button: push per click |
| event_keep | olay_kalan | 60 | 0 | 100 | Reputation | Share of a god-power trace kept each age (%) |
| event_cap | olay_tavan | 80 | 0 | 100 | Reputation | Max god-power trace per axis |
| drain_fear | em_korku | 15 | 0 | 100 | Reputation | Drained son's added fear |
| drain_love | em_sevgi | 12 | 0 | 100 | Reputation | Drained son's lost love |
| drain_sibling_fear | em_kardes_korku | 6 | 0 | 100 | Reputation | Siblings witnessing a drain: added fear |
| devour_sibling_fear | yut_kardes_korku | 20 | 0 | 100 | Reputation | Siblings witnessing a son devoured: added fear |
| devour_friend_love | yut_dost_sevgi | 15 | 0 | 100 | Reputation | Those who loved the devoured son: lost love for father |
| demote_fear | alcalt_korku | 12 | 0 | 100 | Reputation | Demoted son's added fear |
| demote_love | alcalt_sevgi | 12 | 0 | 100 | Reputation | Demoted son's lost love |
| demote_sibling_fear | alcalt_kardes_korku | 4 | 0 | 100 | Reputation | Siblings witnessing a demotion: added fear |
| rip_fear | sok_korku | 10 | 0 | 100 | Reputation | Son whose power was ripped out: added fear |
| rip_love | sok_sevgi | 8 | 0 | 100 | Reputation | Son whose power was ripped out: lost love |
| rip_sibling_fear | sok_kardes_korku | 3 | 0 | 100 | Reputation | Siblings witnessing a power rip: added fear |

---

## `fragment.foreign_god.*` — foreign (old) god constants (yabanci.js)

Used by: the foreign-god deepening prompt and schema (`yabanciDerinlestir`, see main 09 section), the world summary line for foreign gods, the UI, and post-processing. A foreign god (`yabanci_tanri`) has the same nine stats as sons.

### `fragment.foreign_god.stats` (YT_STATLAR) — effect texts (live, interpolated)
`above(r)` = "each point above neutral ({neutral}) gives {r/100}".
| stat key | name | Effect text (English) | rule key |
|---|---|---|---|
| guc | Strength | War power: (Strength + Will) / 2, weighted {war_stat_share}% in war (the rest is its general power). | YABANCI.savas_stat_pay |
| irade | Will | Half of war power; resistance to sons' alliance, threat and bargaining rolls: {above(talk_will)} roll reduction. | YABANCI.konusma_irade |
| dayaniklilik | Endurance | Wakes sooner when defeated: {above(wake_endurance)} ages shorter. | YABANCI.uyanis_dayaniklilik |
| ceviklik | Agility | When hostile, attempts to steal worshippers or tear down temples: {above(attack_agility)} points (%) added. | YABANCI.saldiri_ceviklik |
| bilgelik | Wisdom | When friendly, chance to help its worshippers: {above(help_wisdom)} points (%) added. | YABANCI.yardim_bilgelik |
| kurnazlik | Cunning | Chance to turn the sons' worshippers to itself: {above(steal_cunning)} points (%) added. | YABANCI.calma_kurnazlik |
| karizma | Charisma | Chance to draw unclaimed communities of its world: {above(draw_charisma)} points (%) added. | YABANCI.cekim_karizma |
| yaraticilik | Creativity | When friendly, prosperity it adds to its worshippers: {above(prosperity_creativity)} prosperity added. | YABANCI.refah_yaraticilik |
| kudret | Might | Threshold to grow stronger from worshippers' faith: {above(power_faith_might)} faith lower. | YABANCI.guc_inanc_kudret |

Formula: `ytEtki(y, stat, rate) = (stat − neutral) × rate / 100`; war power `= y.power × (100 − war_stat_share)/100 + (Strength + Will)/2 × war_stat_share/100 + (has shield ? shield : 0)`.

### `fragment.foreign_god.powers` (YT_GUC_ETKILERI) — used as schema enum + description
Schema description string (in deepening schema `gucler`): `"The god's powers; each has an effect in the engine: " + "{key} ({name}: {description})" joined "; "`.
| key | name | Description (English, live) | rule key |
|---|---|---|---|
| kalkan | Shield | In war, +{shield} to its power. | YABANCI.guc_kalkan |
| cagiran | Caller | Chance to draw unclaimed communities +{draw}%. | YABANCI.guc_cekim |
| hirsiz | Worshipper-thief | Chance to steal the sons' worshippers +{thief}%. | YABANCI.guc_hirsiz |
| yikici | Destroyer | When hostile, attack chance +{destroyer}%. | YABANCI.guc_yikici |
| bereketli | Bountiful | When friendly, prosperity added to worshippers ×{bounty/100}. | YABANCI.guc_bereket |
| dirilen | Returning | When defeated, wake time drops to {return}%. | YABANCI.guc_dirilis |
| olumsuz | Deathless | Even in a crushing defeat it does not die; it is only laid low. | — |
| sozu_keskin | Sharp-tongued | The roll of a son who talks with it −{sharp}. | YABANCI.guc_soz |

### `fragment.foreign_god.personality` (YT_KISILIK) — schema property descriptions are `"{label}; 1–2 sentences, concrete"`
| key | label (TR) | English label |
|---|---|---|
| gorunus | Görünüş | Appearance |
| mizac | Mizaç | Temperament |
| takinti | Takıntı | Obsession |
| korku | Korku | Fear |
| uslup | Konuşma | Speech |
| sir | Sırrı | Its secret |

### `fragment.foreign_god.existence` (YT_VAROLUS)
| key | label (TR) | English label |
|---|---|---|
| doga | Doğası | Its nature |
| hal | Hali | Its state (must be one of the son existence states: solid, semi-solid, conceptual, reflection, scattered — `VAROLUS_HALLERI`) |
| tezahur | Tezahürü | Its manifestation |
| gercek_ad | Gerçek adı | Its true name |

### `fragment.foreign_god.depth_text` (YT_DERIN_METIN) — text (non-array) depth keys
| key | label (TR) | English label |
|---|---|---|
| tarih | Tarihçesi | Its history |
| istek | Gerçekte ne istiyor | What it truly wants |
| panteona_bakis | Panteona bakışı | Its view of the pantheon |
| tapinma | Nasıl tapınılır | How it is worshipped |
| gizli_gercek | Gizli gerçek | Hidden truth |

### Sanitizers (post-processing of model output)
- `gucTemizle(g)`: accepts an array, or an object with numeric keys (`{0:…,1:…}` from forms → sorted by key into array); keeps items with a known effect key and a non-blank name; returns `{name: trimmed, effect, description: trimmed or ''}`.
- `metinTemizle(o, fields)`: for each `[key]` in fields, keep `o[key].trim()` only if it is a non-empty string; drop others.
- `varolusTemizle(v)`: `metinTemizle(v, YT_VAROLUS)` and drop `hal` if not in `VAROLUS_HALLERI`.
- `metinAc(x)`: un-embeds JSON the model wrote inside a text field. Non-string: arrays → join string items with blank line; else ''. String starting with `[` or `{`: try parse; array → join string items with `\n\n`; object → join its string values with `\n\n`; parse failure → original trimmed. Otherwise trimmed string.
- `statTemizle(s, old)`: each of the nine stats → clamp(round, 1, 100) if numeric, else old value or neutral.
- `statZarla(seed)`: deterministic stats from seed `"{name}:{world_id}:{created_age}"` using a mulberry32-style PRNG (string hash `a = a*31 + codepoint`), each stat `clamp(round(stat_base + r() × stat_roll), 1, 100)`. Used for foreign gods without stats (imported/old). Startup repairs: `statsizlariDoldur` (fill missing stats), `derinlikOnar` (unwrap embedded-JSON depth texts; null out depth whose history is empty so it is re-deepened).

### Tunables — `YABANCI` (foreign gods)
| English key | Turkish key | Default | Min | Max | Group | English label |
|---|---|---|---|---|---|---|
| stat_base | stat_taban | 35 | 1 | 100 | Foreign gods | Base of each stat of a new foreign god |
| stat_roll | stat_zar | 45 | 0 | 100 | Foreign gods | Roll added to each stat of a new foreign god |
| stat_neutral | stat_notr | 50 | 0 | 100 | Foreign gods | Neutral stat: above it positive, below negative effect |
| war_stat_share | savas_stat_pay | 50 | 0 | 100 | Foreign gods | Share (%) of (Strength + Will)/2 in war power; rest is general power |
| talk_will | konusma_irade | 30 | 0 | 500 | Foreign gods | Will's resistance in talks: (Will − neutral) × this / 100 roll reduction |
| draw_charisma | cekim_karizma | 20 | 0 | 500 | Foreign gods | Charisma to worshipper-draw chance: (Charisma − neutral) × this / 100 points (%) |
| steal_cunning | calma_kurnazlik | 20 | 0 | 500 | Foreign gods | Cunning to worshipper-steal chance: (Cunning − neutral) × this / 100 points (%) |
| attack_agility | saldiri_ceviklik | 20 | 0 | 500 | Foreign gods | Agility to hostile-act chance: (Agility − neutral) × this / 100 points (%) |
| help_wisdom | yardim_bilgelik | 20 | 0 | 500 | Foreign gods | Wisdom to friendly-help chance: (Wisdom − neutral) × this / 100 points (%) |
| prosperity_creativity | refah_yaraticilik | 10 | 0 | 500 | Foreign gods | Creativity to friendly prosperity: (Creativity − neutral) × this / 100 prosperity |
| wake_endurance | uyanis_dayaniklilik | 10 | 0 | 500 | Foreign gods | Endurance to wake time after defeat: (Endurance − neutral) × this / 100 ages shorter |
| power_faith_might | guc_inanc_kudret | 20 | 0 | 500 | Foreign gods | Might to empowerment threshold: (Might − neutral) × this / 100 faith lower |
| power_count | guc_sayi | 2 | 0 | 20 | Foreign gods | Number of powers given in deepening |
| shield | guc_kalkan | 15 | 0 | 500 | Foreign gods | Shield power: added to war power |
| draw | guc_cekim | 15 | 0 | 100 | Foreign gods | Caller power: added worshipper-draw chance (%) |
| thief | guc_hirsiz | 15 | 0 | 100 | Foreign gods | Worshipper-thief power: added steal chance (%) |
| destroyer | guc_yikici | 15 | 0 | 100 | Foreign gods | Destroyer power: added hostile-act chance (%) |
| bounty | guc_bereket | 200 | 100 | 10000 | Foreign gods | Bountiful power: friendly prosperity multiplier (%) |
| return | guc_dirilis | 50 | 1 | 100 | Foreign gods | Returning power: % of wake time after defeat |
| sharp | guc_soz | 15 | 0 | 500 | Foreign gods | Sharp-tongued power: subtracted from talking son's roll |
| deepen_chronicle | derin_kronik | 40 | 0 | 10000 | Foreign gods | Chronicle lines mentioning its name given to the model when deepening |

---

## Known bugs / design smells (fragments)

1. **Regex over generated Turkish text drives logic**: tension-first ordering, tool filtering (`aracaGore`), passion inference (`tutkuOku`) and reputation events (`SEVGI`/`KORKU`) all regex the rendered Turkish strings or chronicle text. New design: build lines as structured records `{kind, tension: bool, tools: [...], text}` and count typed events (`event_kind`) instead of matching prose.
2. **Duplicate dead-sibling lines**: `ogulFirsatlari` emits both "DEAD SIBLING / YOUR ENEMY IS DEAD" and later "Your dead sibling … bones / cult" for the same son. Merge into one line.
3. **Mortal opportunities not tool-filtered**: they name tools (savas_ilan_et, sabotaj, ogren…) without checking availability, unlike son opportunities.
4. **`sec()` silently caps at `list`** even when a caller passes a larger `n` (e.g. `sec(x, list_wide)` is still capped by `list`=5); "list_wide" in `kardesYaratim` is effectively min(6,5)=5. Make caps explicit per line.
5. **Hidden external tunable dependency**: `DERIN_YASAM_K = tanimla('DERIN_YASAM', {})` reads `dirilis_adanmislik` defined in derin.js; works only by registry side effect. Import the real constant.
6. **Per-call heavy queries**: `ogulFirsatlari` calls `iliski`/`hami` repeatedly inside filters/sorts and runs several full scans per son turn; precompute per epoch.
7. **Numbers in prompt**: reputation line exposes raw love/fear/oblivion numbers and relation values; elsewhere the codebase fights number leakage into narrative. Consider verbal levels.
8. **Turkish number words** in scenario names (`yazi`, `SIRA` ordinals) — LANGUAGE-SPECIFIC: drop; render with English formatting.
9. **Scenario `sadik_panteon` failure detection** greps chronicle text `isyan etti` ("rebelled"); use a typed rebellion event.
10. **Creator panel** (`tanriFirsatlari`) duplicates thresholds with the son prompt (e.g. stale threads); share one computation.

---

## 13. Prompt index (all ids in this file)

| id | role (08 section) | output |
|---|---|---|
| genesis | Genesis (4.1) | schema.genesis |
| genesis.wizard_settings | Genesis wizard text (appended) | text fragment |
| complete.son_powers | Startup completion (4.2) | powers + existence + image_prompt |
| creator.portrait | Creator portrait (4.3) | schema.creator_god |
| summon.son | Summon / birth (4.4) | schema.son_profile |
| awaken.peoples | Awaken peoples (4.15) | schema.awaken |
| revelation | Revelation (4.10) | schema.revelation |
| son_turn.system / .user / .resume_note / .continuation | Son turn (4.5) | free text ending in «word» + tool calls |
| fate.judgment.system / .user | Fate (4.6) | schema.fate.judgment |
| fate.extra_judgment | Fate overflow rounds (4.6) | {verdicts} |
| chronicler.system / .user | Chronicler (4.6) | schema.chronicle |
| chronicler.fix_opening | Chronicle completion (4.6) | {first_sentence} |
| chronicler.missing_worlds | Chronicle completion (4.6) | schema.world_sections |
| chronicler.lost_age / .lost_world_sections | Lost chronicles (4.8) | chronicle / world sections |
| naming.pending | Naming (4.9) | {namings} |
| voices.peoples | Voices of the peoples (4.7) | schema.voices |
| deepen.entity | Deepen (4.11) | schema.deepen |
| creator.epic / creator.deepen | Creator epic / depth (4.12) | epic / depth |
| foreign_god.deepen | Foreign god depth (4.13) | foreign depth |
| son.epic | Son epic (4.14) | {title, epic, line} |
| image_prompts.entities / .cosmos | Image prompts (4.16) | {prompts} |
| council.*, son_chat.*, linguist.translate.*, cosmos.new_world.*, fate_bonds.*, mortal.* | other-module roles (08 §6) | see appended sections |
| fragment.opportunities.*, fragment.reputation_line, fragment.creator_wishes, fragment.scenarios, fragment.foreign_god.* | injected fragments | text |
| tool descriptions (son and mortal) | 08 §5 and §6 (model-facing text, translated in place) | — |

## 14. Known bugs / design smells (prompts)

1. Prompts say "do not write numbers" but feed numbers (ids, stats, mood levels are already verbalised; stats and
   life/essence in the son system prompt are not) — keep ids (needed for references) and rely on `sanitize`.
2. Several prompts contradict schema "required" lists (Fate's facts/words "MANDATORY" but not required; deepen
   schemas list keys in the prompt but only `history` is required) — intentional workaround for Haiku dumping
   sections into `history`; keep the post-processor that splits embedded sections.
3. The old prompts ask for Turkish output with English image prompts; the new app is English-only — every
   "write in Turkish" was translated to "write in English" (already applied above).
4. Many anti-repetition devices (tired images, openings, tics, piled roots, belief patterns) are language-specific
   n-gram heuristics; port them with English tokenisation or the prompts will ban nonsense stems.
5. `budget()` hints name tools in the old Turkish (`varlik_ara`, `dunya_ozeti`, `hafizam`); in the new app the hints
   must use the English tool names (`search_entities`, `world_summary`, `my_memory`).
