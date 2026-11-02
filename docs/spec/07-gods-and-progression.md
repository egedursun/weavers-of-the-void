# 07 — Gods, Progression and Remaining Engine Systems

Source modules (old repo `/Users/egedogan_dursun/aerona/src/`):

| § | Old file | English module name | What it owns |
|---|---|---|---|
| 1 | `yaratici.js` | Creator mood and cult | The player-god's mood (contentment, anger, interest, loneliness), spontaneous "signs", the creator's direct cult, mortal prayers to the creator |
| 2 | `tanriguc.js` | God power | The creator's direct powers over sons, mortals, communities and foreign gods (drain, devour, kill, resurrect, deify, demote, strip power, absolute command, prophet, manifestation, bloodline curse, conversion, wrath) and their **spontaneous** per-epoch paths (rebellion, return, auto-drain, auto-curse, auto-prophet) |
| 3 | `itibar.js` | Reputation and passions | How each son sees his father (love / fear / forgottenness → label), the creator's "passions", per-epoch drift of loyalty/anger, manual reputation pushes, power "traces" |
| 4 | `hedef.js` | Goals, achievements, score | Optional scenario goals, always-on achievements, per-epoch score |
| 5 | `olum.js` | Death and resurrection | Life-taking attempts (by sons, foreign gods, creator), resurrection devotion of dead sons, rites and sacrifices, sibling schemes, scattering bones |
| 6 | `ekonomi.js` | Strange resources and cosmic economy | Resource mechanics (decay, fixed amount, addiction/withdrawal, sentient resources, sacred resources, depletion curse), cosmic travel resource, monopoly, wandering markets, void pirates |
| 7 | `konsey.js` | Council, chat, dreams, translation | Council of Gods (LLM), the player chatting with a son (LLM), sending a dream to a mortal, translating a sentence into a world language (LLM) |
| 8 | `firsatlar.js` | Opportunities | Prompt lines suggesting concrete actions for son agents and mortal agents; "what can you do this epoch" lines for the player |
| 9 | `kitap.js` | The Book | Full printable HTML export of the world |
| 10 | `kodeks.js` | Codex, traveller's guide, cosmic chronicle | Markdown encyclopedia export; per-world traveller's guide; per-epoch per-world chronicle digest |
| 11 | `oyuncu.js` | Player manual assignments ("the god's hand") | Every manual override the player can make on the world + automatic son distribution |
| 12 | — | **Player actions catalogue** | Every manual player action in these modules (plus the epoch.js wrappers that charge costs) |
| 13 | — | Epoch-transition wiring | Where each per-epoch function runs |
| 14 | — | Known bugs and design smells | |
| 15 | — | Open decisions | |

---

## 0. Conventions used in this document

### 0.1 Glossary (Turkish original in parentheses, given once)

| English | Turkish | Notes |
|---|---|---|
| world (singleton row) | dunya (table `dunya`, id=1) | holds creator name (`tanri_adi`), creator essence (`tanri_oz`), epoch (`cag`), year (`yil`), doomsday clock (`kiyamet`), JSON fields `tanri_ruh` (mood), `tanri_tutku` (passions), `kozmik_kaynak` (cosmic resource definition), `iklim` (legacy climate), settings `ogul_dagitim`, `konsey_sikligi` |
| world (planet) | dunyalar (table) | multiple planets/moons in a cosmos; `kesif` (discovery state: `bilinen` known / `efsane` legend / `bilinmeyen` unknown / `unutulmus` forgotten) |
| creator, the god, the player | yaratıcı / tanrı / Aeron | Referenced in bonds as target type `t` with id 1 |
| son (god card) | oğul (table `ogullar`) | statuses (`durum`): `aktif` active, `uykuda` asleep, `olu` dead |
| entity / record | varlık (table `varliklar`) | statuses: `kanon` canon, `olu` dead, `yok_edildi` destroyed, `gerceklesti` fulfilled (prophecy), `reddedildi` rejected |
| bond | bağ (table `baglar`) | `(kaynak_tip, kaynak_id) -[tur]-> (hedef_tip, hedef_id)`, `aktif` flag, `aciklama`, `cag`. Endpoint types: `v` entity, `o` son, `t` creator, `y` foreign god |
| chronicle | kronik (table) | `(cag, ogul_id, tur, metin, varlik_ids JSON)` via `addKronik(cag, sonId, type, text, ids)` |
| message | mesaj (table `mesajlar`) | `(cag, kimden_tip, kimden_id, kime_tip, kime_id, niyet, metin, istek, okundu, cevaplandi)`; intents (`niyet`): `dua` prayer, `ruya` dream, `tezahur` manifestation, `sohbet` chat, `cevap` answer, `tehdit` threat, … |
| essence | öz | the main currency (creator: `dunya.tanri_oz`; son: `ogullar.oz`) |
| epoch | çağ | one simulation turn; `CAG_YIL` years each |
| foreign god | yabancı tanrı (table `yabanci_tanrilar`) | statuses `uyanik` awake, `uykuda` asleep, `yenik` defeated, `olu` dead; fields `guc` power, `tutum` attitude (−100..100), `gucler` powers JSON |
| community | topluluk | entity types `halk` people, `yerlesim` settlement, `hizip` faction, `tarikat` order/cult |
| named mortal | ölümlü (`olumlu`) | entity type for individual characters |
| region / place | bölge / yer (`bolge`, `yer`) | geography entity types |
| tag | etiket | entity tags (JSON array of strings) |
| passion (son) | tutku | son's drives: `sadakat` loyalty, `hirs` ambition, `ofke` anger, `merhamet` mercy (0–100) |
| rebel | asi | son flag `asi` (0/1) |
| ledger | defter | Fate's ledger of actions; every player action is wrapped (see 0.3) |
| Fate | Kader | LLM judge/chronicler (other spec part) |
| thread (story) | iplik (table `iplikler`) | open stories |
| canon fact | gerçek (table `gercekler`) | subject–relation–object facts |
| people's belief | halk inancı (table `halk_inanc`) | how a people names/narrates a son (son id 0 = creator) |

### 0.2 Tunable rules (`tanimla`)

Every balance number is declared by `tanimla(DOMAIN, { key: [default, label, min, max, group] })` (old `src/denge.js`). Values are integers; probabilities are stored as percent and divided by 100 at use. The player can change any of them live in *Settings → World rules*; modules read the live value at every access. The new app must keep this: one registry of rules with `domain.key`, default, min, max, group, label; persisted overrides; live reads.

In the tables below: **Key** = new English snake_case key (old Turkish key in parentheses), **Default**, **Min**, **Max**, **Group** (English), **Label** (English translation of the UI label).

Older global constant objects also used here (defined elsewhere, listed for reference):
`DENGE.ruya` = 8 (send dream), `DENGE.konsey` = 20 (convene council), `DENGE.dirilis` = 150 (resurrect a son), `DENGE.dunya` = 120 (creator creates a world), `DENGE.tanri_oz_yenilenme` = 20 (creator's per-epoch essence income), `DENGE.oz_tavan` = 800 (soft cap of creator essence), `DENGE.kiyamet_esik` = 100 (doomsday threshold), `DENGE.kiyamet_hiz` = 100 (doomsday speed %).

Helper semantics used throughout:
- `chance(p)` = `random() < p` (p in 0..1).
- `d(n)` = uniform integer 1..n. `randInt(lo, hi)` inclusive.
- `clamp(x, lo, hi)`.
- `saturating(x, half, cap)` (old `doygun`) = `x > 0 ? cap * x / (x + max(1, half)) : 0` — approaches `cap`, equals `cap/2` at `x = half`.
- `addTag(entity, ...tags)` / `removeTag(entity, tagOrPredicate)` (old `etiketEkle` / `etiketSil`, derin.js).
- `addBond(srcType, srcId, dstType, dstId, type, description, epoch)` (old `addBag`, world.js).
- `canon()` (old `kanonlar`) = all canon entities.

### 0.3 How player actions are executed (epoch.js `defterli`, `harca`, `iade`)

Every manual player action in this document is invoked through `ledgered(actionKey, fn)` (old `defterli`):
1. A ledger row is opened: `{kim_tip:'t', kim_id:0, kim_ad: creatorName, arac: actionKey, cag: currentEpoch}`.
2. `SAVEPOINT tanri_eli`; run `fn()`; on success `RELEASE`; on exception `ROLLBACK TO` + `RELEASE` + clear the canon cache, then re-throw. **A rejected action leaves no trace** (including any essence that was charged inside `fn`). A ledger entry without any row is deleted.
3. Ledger entries can be **undone** later ("Geri al") — the ledger module (other spec part) owns that.

`spend(amount, ruleName)` (old `harca`, exists both in epoch.js and tanriguc.js): if `world.tanri_oz < amount` throw `"This needs {amount} divine essence; you have {have}. (Cost is world rule {ruleName} = {amount}.)"`; else `tanri_oz -= amount`.
`gain(amount)` (old `kazan`, tanriguc.js): if `amount > 0` then `tanri_oz += round(amount)`; returns `round(max(0, amount))`.
`refund(amount)` (old `iade`): `tanri_oz += amount` (used by async actions such as council when the LLM call fails).

All error messages are user-facing (shown in the UI); keep them informative and name the rule that limits a value.

---

## 1. Creator mood and cult (`yaratici.js`)

The creator (player) cannot be destroyed, but is affected by the world and affects it spontaneously:
- **Mood** (ruh hâli): contentment (`hosnutluk`), anger (`ofke`), interest (`ilgi`), loneliness (`yalnizlik`), each 0–100. World events and the player's actions change it every epoch.
- **Signs** (işaretler): when thresholds are crossed, wrath, grace, silence or a dream descends even if the player does nothing.
- **Cult** (kült): communities and named mortals may worship the creator directly; the cult's faith flows into the creator's essence and pushes the doomsday clock back.

### 1.1 Entities and fields

- `world.tanri_ruh` (JSON): `{ hosnutluk, ofke, ilgi, yalnizlik, girdi }`. Missing keys fall back to the defaults `mood_contentment_start`, `mood_anger_start`, `mood_interest_start`, `mood_loneliness_start` (read live). `girdi` (inputs) is the last epoch's breakdown: `{ ofke: [{kalem, d}], hosnutluk: [{kalem, d}] }` (item label, delta rounded to 2 decimals, zero items dropped) — used by the UI to explain the mood.
- **Creator worship bond**: `bond(v, entityId) -[tapar/worships]-> (t, 1)`, active. The set of canon sources of such bonds is the **cult** (`creatorWorshippers()`).
- Messages: mortal prayer `v→t niyet='dua'` (optional `istek` = request); creator dream `t→v niyet='ruya'`.

### 1.2 Mood label (`ruhHaliEtiketi`) — first match wins

| Condition | Label (TR → EN) |
|---|---|
| anger ≥ `label_angry` | öfkeli → **angry** |
| interest ≤ `label_silent` | uzak ve sessiz → **distant and silent** |
| loneliness ≥ `label_lonely` | yalnız → **lonely** |
| contentment ≥ `label_content` | hoşnut → **content** |
| anger ≥ `label_uneasy` | huzursuz → **uneasy** |
| otherwise | dingin → **serene** |

### 1.3 Cult functions

```
creatorWorshippers():
  rows = bonds where active=1, type='tapar', src_type='v', dst_type='t'
  return [getEntity(src_id) for rows] filtered status=='kanon'

creatorFaith():   # old yaraticiInanci
  return round( Σ over worshippers v of:
       (v.stats.population or 0) / cult_faith_population * ((v.stats.faith ?? cult_faith_default) / 100)
     + (v.stats.disciples or 0) / cult_faith_disciple
     + (v.type=='olumlu' ? cult_faith_mortal : 0) )

cultEffect():     # old kultEffect; consumed by the epoch transition (sim.js)
  faith = creatorFaith()
  return { faith,
           essence: floor(faith / cult_essence_divisor),
           doomsday: min(cult_doomsday_cap, floor(faith / cult_doomsday_divisor)) }

worshipCreator(v, vowText, epoch):   # old yaraticiyaTapin
  if active bond (v -tapar-> t) exists: return false
  addBond('v', v.id, 't', 1, 'tapar', vowText, epoch)
  if 'tanrısız'(godless) in v.tags: remove it (direct UPDATE of tags)
  return true
```
Note: `worshipCreator` does **not** close other worship bonds (a community may worship a son and the creator at once) — only `convertToSelf` (§2) and `assignPatron` (§11) close them.

The epoch transition (sim.js, other spec part) uses `cultEffect()`:
- `essence` is added to the creator's essence **outside** the soft cap (not halved above `DENGE.oz_tavan`).
- `doomsday` is a negative line item `kult` in the doomsday clock's per-epoch sum (and therefore scaled by `DENGE.kiyamet_hiz`).

### 1.4 Per-epoch mood update (`yaraticininCagi(oldEpoch, newEpoch, notes)`)

Runs in the epoch transition **after** the creator essence update (so cult essence is already in). Order is significant.

```
w = getWorld(); r = mood(w)
count(sql) helper
godless   = count canon entities type∈{halk,yerlesim,hizip,tarikat} whose tags contain 'tanrısız' (substring LIKE)
rebels    = sons with asi==1 and status!='olu'
wars      = ongoingWarCount()          # derin.surenSavasSayisi: ongoing community war events
communities = count canon entities type∈{halk,yerlesim,hizip,tarikat}
cult      = len(creatorWorshippers())
newLife   = count entities with cag==oldEpoch, type∈{halk,olumlu,yerlesim,tur}, status 'kanon'
actions   = count chronicle rows at oldEpoch with type∈{'tanri','vahiy','dunya_dogusu','emir'}
          + count messages at oldEpoch with from_type='t'
unanswered = count messages to_type='t', answered=0, intent != 'sohbet'   # ALL TIME, not windowed

inputs.anger = [
  ('wars',          saturating(wars / max(1, DERIN.war_cap) * 100, anger_war_half, anger_war)),
  ('godless',       saturating(communities ? godless/communities*100 : 0, anger_godless_half, anger_godless)),
  ('rebel sons',    saturating(rebels, anger_rebel_half, anger_rebel)),
  ('doomsday clock', w.doomsday / max(1, DENGE.kiyamet_esik) * 100 / anger_doomsday_divisor) ]
inputs.contentment = [
  ('cult',          saturating(cult, content_cult_half, content_cult)),
  ('new life',      saturating(newLife, content_life_half, content_life_cap)),
  ('the god acted', actions ? content_action : 0) ]
o0 = r.anger; h0 = r.contentment            # start-of-epoch values
inputs.anger.push(('contentment soothes', -h0 * mood_opposition / 100))
inputs.contentment.push(('shadow of anger', -o0 * mood_opposition / 100))
r.anger       = clamp(round(o0 * anger_persist/100 + Σ inputs.anger), 0, 100)
r.contentment = clamp(round(h0 * content_persist/100 + Σ inputs.contentment), 0, 100)
r.inputs      = breakdown (2-decimal, zero items removed)
r.interest    = clamp(round(r.interest * interest_persist/100 + min(interest_cap, actions * interest_per_action)), 0, 100)
r.loneliness  = clamp(round(r.loneliness * lonely_persist/100
                 + (activeSons < lonely_son_threshold ? lonely_few_sons : 0)
                 + (cult ? -lonely_cult_relief : lonely_no_cult)
                 + min(lonely_unanswered_cap, unanswered)), 0, 100)
save r to world.tanri_ruh
```
`DERIN.war_cap` is `DERIN.savas_tavan` = 6 (derin.js).

### 1.5 Spontaneous signs (same function, continued)

A sign = `addChronicle(newEpoch, null, 'tanri_isareti', text, ids)` + push text to `notes`.

**Recently struck exclusion**: `struck = ⋃ varlik_ids of chronicle rows type='tanri_isareti' with cag > newEpoch − sign_exclusion_epochs`.

**Target picker** `signTarget(candidates, struck, sorter=null, lastResort=true)`:
```
fresh = candidates where id ∉ struck
pool  = (fresh non-empty or not lastResort) ? fresh : candidates
pool  = sorter ? sorted(pool, sorter) : pool
return pool empty ? null : uniformRandom(pool[0 : sign_candidates])
```
`lastResort=false` is used for "priority pools" so an exhausted priority pool falls through to the next pool instead of re-hitting the same place.

**(a) Wrath** — if `r.anger ≥ anger_threshold` and `chance(anger_sign_chance/100)`:
```
placeOf(h) = h.type ∈ {bolge,yer,yerlesim} ? h : getEntity(h.location_id)
sinners = canon halk/yerlesim tagged 'tanrısız'(godless) or 'lanetli'(cursed) with placeOf(v) non-null
target = signTarget(sinners where placeOf(v).id ∉ struck, struck, null, false)
      or signTarget(canon regions, struck, sort by stats.danger desc)
place = placeOf(target); if place:
   kind = uniform of ['firtina' storm, 'deprem' earthquake, 'kuraklik' drought]
   applyDisaster(place, kind, anger_disaster_severity/100)        # mudahale.afetUygula
   eventId = recordEvent({type: kind, target: place, epoch: newEpoch,
                          severity: anger_event_severity + d(anger_event_severity_die), source: 'tanri'})  # mudahale.olayKaydi
   r.anger = clamp(r.anger - anger_discharge, 0, 100); save
   sign(random WRATH template(creatorName, place.name, disasterName.lower()), [place.id, eventId])
```

**(b) Grace** — if `r.contentment ≥ content_threshold` and `chance(content_sign_chance/100)`:
```
t = signTarget(creatorWorshippers() excluding type 'olumlu', struck, null, false)
 or signTarget(canon halk/yerlesim, struck, sort by stats.faith desc)
if t: applyMiracle(t, 'bereket'(abundance), newEpoch)  # mudahale.mucizeUygula
      sign(random GRACE template(creatorName, t.name), [t.id])
```

**(c) Silence** — if `r.interest ≤ indifferent_threshold` (no chance roll for the effect):
```
for each active son: loyalty -= indifferent_loyalty; ambition += indifferent_ambition (clamped); save
if chance(silence_sign_chance/100): sign(random SILENCE template(creatorName))   # no ids
```

**(d) Loneliness dream** — if `r.loneliness ≥ lonely_threshold` and `chance(lonely_sign_chance/100)`:
```
mortals = canon type 'olumlu'
k = signTarget(mortals whose subtype matches /seer|sage|priest/ (TR: kâhin|bilge|rahip), struck, null, false)
 or signTarget(mortals, struck)
if k:
  insert message(newEpoch, from 't', to 'v' k.id, intent 'ruya',
     text "The creator is lonely. No one in the heavens speaks his name; he is calling you.")
  r.loneliness = clamp(r.loneliness - lonely_discharge); save
  sign(random LONELINESS template(creatorName, k.name), [k.id])
```

**(e) Estranged communities turn to the creator** — iterate canon `halk`/`yerlesim`/`tarikat` that are tagged `tanrısız` **or** are the target of any active `lanetledi` (cursed) bond from a son (`src_type='o'`):
```
p = estranged_chance/100 + (r.contentment ≥ estranged_content_threshold ? estranged_content_bonus/100 : 0)
if chance(p) and worshipCreator(v, 'turned from the sons to the creator', newEpoch):
    sign("{v} turned its face from its sons and began worshipping the creator {creator} directly.", [v.id]); break
```
At most one conversion per epoch. Returns `r`.

#### Sign text templates (translated; one chosen uniformly at random)

WRATH `(T, place, disaster)`:
1. "{T}'s anger overflowed: {disaster} fell upon {place}. The sky darkened before anyone could pray."
2. "The people of {place} had forgotten to look to the sky; {T} reminded them. His anger fell as {disaster}."
3. "The sky split above {place}: {T}'s patience ran out, and {disaster} followed."
4. "{T} turned to {place} in an angry silence; {disaster} broke that silence."

GRACE `(T, place)`:
1. "{T} is content: the creator's grace descended upon {place}; granaries filled, children were born laughing."
2. "The fields of {place} came into ear overnight; the elders said it was {T}'s smile."
3. "{T} looked kindly on {place}: wells overflowed, the sick rose up, and no one asked why."
4. "A warm rain fell over {place}; {T}'s contentment seeped into the soil."

SILENCE `(T)`:
1. "{T} fell silent. For an entire epoch the sky gave no answer; his sons whisper, 'our father has forgotten us.'"
2. "Prayers rose to the sky and never came back: {T} did not speak at all this epoch."
3. "{T}'s voice has not been heard for an epoch; in the temples the lamps go out by themselves."

LONELINESS `(T, k)`:
1. "{T}'s loneliness seeped into {k}'s dream."
2. "One night {k} heard their own name being called; they did not know the voice, but it was {T}'s loneliness."
3. "{T} searched for someone and found {k}: in a dream the sky told them its name."

(LANGUAGE-SPECIFIC: the Turkish templates used apostrophe + case suffixes such as `'nin`, `'e`; English templates need none.)

### 1.6 Mortal prayer and answer

```
mortalPrays(v, text, request, epoch):            # called by the mortal agent tool
  insert message(epoch, from 'v' v.id, to 't', intent 'dua', text, request or null)
  addChronicle(epoch, null, 'dua', "{v} prayed to the creator: \"{text[:200]}\"", [v.id])

answerMortalPrayer(msg, text, essenceGiven, epoch):   # called by epoch.duaCevapla (see §12)
  v = getEntity(msg.from_id) or throw "The one who prayed no longer exists."
  if v.stats.faith != null: faith = clamp(faith + prayer_faith, 0, 100)
  if essenceGiven: for k in [prosperity(refah), fertility(bereket), defense(savunma), life(can)] present:
        v.stats[k] = clamp(v.stats[k] + round(essenceGiven / prayer_essence_divisor), 0, k=='can' ? SINIR.can_tavan : 100)
  save stats
  worshipCreator(v, 'their prayer was answered', epoch)
  if text: insert message(epoch, from 't', to 'v' v.id, intent 'ruya', text)
  mood.loneliness -= prayer_loneliness; mood.contentment += prayer_contentment (clamped); save
  return v
```

### 1.7 Tunables — domain `CREATOR` (old `YARATICI`)

| Key (old) | Default | Min | Max | Group | Label |
|---|---|---|---|---|---|
| cult_essence_divisor (kult_oz_bolen) | 4 | 1 | 100 | Creator and essence | Every this much cult faith gives the god 1 essence |
| cult_doomsday_divisor (kult_kiyamet_bolen) | 25 | 1 | 1000 | Doomsday | Every this much cult faith pushes doomsday back by 1 |
| cult_doomsday_cap (kult_kiyamet_tavan) | 5 | 0 | 100 | Doomsday | Max doomsday pushback by the cult per epoch |
| anger_threshold (ofke_esik) | 70 | 0 | 100 | Creator and essence | Threshold at which the creator's anger overflows |
| content_threshold (hosnut_esik) | 70 | 0 | 100 | Creator and essence | Contentment at which the creator sends grace |
| anger_sign_chance (ofke_isaret_sans) | 60 | 0 | 100 | Creator and essence | Angry creator's punishment falls (%) |
| content_sign_chance (hosnut_isaret_sans) | 60 | 0 | 100 | Creator and essence | Content creator's grace falls (%) |
| silence_sign_chance (sessizlik_isaret_sans) | 50 | 0 | 100 | Creator and essence | Indifferent creator falls silent (sign %) |
| lonely_sign_chance (yalnizlik_isaret_sans) | 50 | 0 | 100 | Creator and essence | Lonely creator sends a dream (%) |
| mood_contentment_start (ruh_hosnutluk) | 50 | 0 | 100 | Creator and essence | Creator's starting contentment |
| mood_anger_start (ruh_ofke) | 20 | 0 | 100 | Creator and essence | Creator's starting anger |
| mood_interest_start (ruh_ilgi) | 60 | 0 | 100 | Creator and essence | Creator's starting interest |
| mood_loneliness_start (ruh_yalnizlik) | 30 | 0 | 100 | Creator and essence | Creator's starting loneliness |
| label_angry (etiket_ofkeli) | 70 | 0 | 100 | Creator and essence | Anger counted as mood "angry" |
| label_silent (etiket_sessiz) | 20 | 0 | 100 | Creator and essence | Interest counted as "distant and silent" (at most) |
| label_lonely (etiket_yalniz) | 70 | 0 | 100 | Creator and essence | Loneliness counted as "lonely" |
| label_content (etiket_hosnut) | 70 | 0 | 100 | Creator and essence | Contentment counted as "content" |
| label_uneasy (etiket_huzursuz) | 45 | 0 | 100 | Creator and essence | Anger counted as "uneasy" |
| cult_faith_population (kult_inanc_nufus) | 2000 | 1 | 10000000 | Creator and essence | Worshipper population that gives 1 cult faith (at full piety) |
| cult_faith_default (kult_inanc_varsayilan) | 60 | 0 | 100 | Creator and essence | Assumed piety of a cult worshipper with unknown faith |
| cult_faith_disciple (kult_inanc_murit) | 50 | 1 | 10000000 | Creator and essence | Disciples that give 1 cult faith |
| cult_faith_mortal (kult_inanc_olumlu) | 2 | 0 | 100 | Creator and essence | Faith of each named mortal worshipping the creator |
| anger_persist (ofke_kalici) | 85 | 0 | 100 | Creator and essence | Share of anger kept from epoch to epoch (%) |
| anger_godless (ofke_tanrisiz) | 4 | 0 | 100 | Creator and essence | Max contribution of godless communities to anger per epoch (saturates as their share grows) |
| anger_godless_half (ofke_tanrisiz_yari) | 10 | 1 | 100 | Creator and essence | When this % of communities is godless, the godless contribution is half the cap |
| anger_rebel (ofke_asi) | 8 | 0 | 100 | Creator and essence | Max contribution of rebel sons to anger per epoch |
| anger_rebel_half (ofke_asi_yari) | 1 | 1 | 100 | Creator and essence | At this many rebel sons the rebel contribution is half the cap |
| anger_war (ofke_savas) | 6 | 0 | 100 | Creator and essence | Max contribution of ongoing community wars to anger per epoch |
| anger_war_half (ofke_savas_yari) | 100 | 1 | 10000 | Creator and essence | When ongoing wars are at this % of the world war cap, war contribution is half the cap |
| anger_doomsday_divisor (ofke_kiyamet_bolen) | 12 | 1 | 1000 | Creator and essence | Doomsday clock's anger contribution: clock (% of threshold) / this |
| content_persist (hosnut_kalici) | 85 | 0 | 100 | Creator and essence | Share of contentment kept per epoch (%) |
| content_cult (hosnut_kult) | 8 | 0 | 100 | Creator and essence | Max cult contribution to contentment per epoch |
| content_cult_half (hosnut_kult_yari) | 10 | 1 | 10000 | Creator and essence | At this many cult worshippers the cult contribution is half the cap |
| content_life_cap (hosnut_canli_tavan) | 5 | 0 | 100 | Creator and essence | Max contribution of new living beings to contentment per epoch |
| content_life_half (hosnut_canli_yari) | 25 | 1 | 10000 | Creator and essence | At this many new beings in an epoch the contribution is half the cap |
| content_action (hosnut_eylem) | 4 | 0 | 100 | Creator and essence | Contentment from an epoch in which the god acted |
| mood_opposition (ruh_zitlik) | 5 | 0 | 100 | Creator and essence | Anger and contentment soothe each other: each loses this % of the other per epoch |
| interest_persist (ilgi_kalici) | 80 | 0 | 100 | Creator and essence | Share of interest kept per epoch (%) |
| interest_per_action (ilgi_eylem) | 6 | 0 | 100 | Creator and essence | Interest per god action |
| interest_cap (ilgi_tavan) | 30 | 0 | 100 | Creator and essence | Max interest from actions in one epoch |
| lonely_persist (yalniz_kalici) | 85 | 0 | 100 | Creator and essence | Share of loneliness kept per epoch (%) |
| lonely_son_threshold (yalniz_ogul_esik) | 3 | 0 | 100 | Creator and essence | With fewer active sons than this the creator grows lonely |
| lonely_few_sons (yalniz_ogul) | 8 | 0 | 100 | Creator and essence | Per-epoch loneliness from too few sons |
| lonely_cult_relief (yalniz_kult) | 4 | 0 | 100 | Creator and essence | Per-epoch loneliness decrease when the creator has a cult |
| lonely_no_cult (yalniz_kultsuz) | 6 | 0 | 100 | Creator and essence | Per-epoch loneliness increase without a cult |
| lonely_unanswered_cap (yalniz_cevapsiz_tavan) | 10 | 0 | 100 | Creator and essence | Max loneliness from unanswered prayers (1 per prayer) |
| anger_disaster_severity (ofke_afet_siddet) | 80 | 0 | 300 | Creator and essence | Disaster severity of the anger punishment (%) |
| anger_event_severity (ofke_olay_siddet) | 60 | 0 | 100 | Creator and essence | Base severity of the anger punishment event |
| anger_event_severity_die (ofke_olay_siddet_zar) | 30 | 1 | 100 | Creator and essence | Severity die of the anger punishment event |
| anger_discharge (ofke_bosalma) | 25 | 0 | 100 | Creator and essence | Anger drop after a punishment falls |
| indifferent_threshold (ilgisiz_esik) | 20 | 0 | 100 | Creator and essence | Below this interest the creator falls silent |
| indifferent_loyalty (ilgisiz_sadakat) | 4 | 0 | 100 | Creator and essence | Loyalty loss of the silent creator's sons |
| indifferent_ambition (ilgisiz_hirs) | 3 | 0 | 100 | Creator and essence | Ambition gain of the silent creator's sons |
| lonely_threshold (yalniz_esik) | 70 | 0 | 100 | Creator and essence | Loneliness at which the creator sends a dream |
| lonely_discharge (yalniz_bosalma) | 20 | 0 | 100 | Creator and essence | Loneliness drop after sending a dream |
| estranged_chance (kus_sans) | 8 | 0 | 100 | Creator and essence | A community estranged from its sons turns to the creator (%) |
| estranged_content_threshold (kus_hosnut_esik) | 60 | 0 | 100 | Creator and essence | Creator contentment that attracts the estranged more |
| estranged_content_bonus (kus_hosnut_ek) | 7 | 0 | 100 | Creator and essence | Extra pull of a content creator on the estranged (%) |
| prayer_faith (dua_inanc) | 10 | 0 | 100 | Creator and essence | Faith gain of a mortal whose prayer is answered |
| prayer_essence_divisor (dua_oz_bolen) | 3 | 1 | 100 | Creator and essence | Every this much essence given to a prayer adds 1 to stats |
| prayer_loneliness (dua_yalnizlik) | 10 | 0 | 100 | Creator and essence | Loneliness reduction from answering a prayer |
| prayer_contentment (dua_hosnutluk) | 3 | 0 | 100 | Creator and essence | Contentment from answering a prayer |
| sign_candidates (isaret_aday) | 4 | 1 | 100 | Creator and essence | A spontaneous sign's target is rolled among this many best candidates |
| sign_exclusion_epochs (isaret_dislama_cag) | 3 | 0 | 100 | Creator and essence | A place hit by a spontaneous sign is not chosen again for this many epochs (unless no candidate remains) |

### 1.8 Cross-references
- Calls: `world.getWorld/allSons/getVarlik/kanonlar/saveSon/saveStat/addKronik/addBag`, `mudahale.afetUygula / mucizeUygula / olayKaydi`, `derin.surenSavasSayisi`, `rules.AFETLER` (disaster names), `DENGE.kiyamet_esik`, `SINIR.can_tavan`.
- Called by: `sim.js` epoch transition (`yaraticininCagi`, `kultEffect`), mortal agent tools (`olumluDuasi`), `epoch.duaCevapla` (`olumluDuasiniCevapla`), `tanriguc.js` / `oyuncu.js` / `olum.js` (`yaraticiyaTapin`, `ruhHali`), `itibar.js` (reads `tanri_ruh`), `kitap.js` (`ruhHali`, `ruhHaliEtiketi`, `yaraticiyaTapanlar`).

---

## 2. God power (`tanriguc.js`)

Direct powers of the creator ("Aeron") over sons, mortals, communities and foreign gods. Costs and ratios are rules in domain `GOD_POWER` (old `TANRI_GUC`, UI group "Tanrının gücü" → "God's power"). Each manual action is wrapped by `ledgered` in epoch.js (§0.3, §12) and additionally requires that a world exists (`dunyaGerekli`). The `*Ic` ("inner") functions below hold the logic.

Shared validators:
- `livingSon(id)`: son must exist (`"No such son"`) and not be dead (`"{name} is dead."`).
- `canonEntity(id, what='This record')`: entity must exist and be canon (`"{what} is not in the world."`).
- `foreignGod(id)`: must exist (`"No such foreign god."`).
- `addPassion(son, key, n)`: `son.tutku[key] = clamp((tutku[key] ?? 0) + n, 0, 100)`.
- `lovers(son)`: ids of other sons with `iliskiler.deger > 0` toward this son.
- `COMMUNITY = [halk, yerlesim, hizip, tarikat]`, `NAMED = [olumlu]`.
- `communityOf(mortal)`: the mortal's `location` if it is a community; else the first active `yasar` (lives in) or `uyesi` (member of) bond to a canon community.

### 2.1 Drain and devour

**Drain a son's essence** — `drainSon(sonId, {spontaneous=false})` (old `ogulOzEmIc`):
```
s = livingSon(sonId)
drawn = round(s.essence * son_drain_share / 100); if drawn ≤ 0: throw "{s} has no essence left; nothing to drain."
s.essence -= drawn
s.existence(varlik) = clamp((s.existence ?? deify_existence) - son_drain_existence, 0, 100)
addPassion(s, loyalty, -son_drain_loyalty); addPassion(s, anger, +son_drain_anger); save
for every other non-dead son k: addPassion(k, loyalty, +son_drain_fear); save      # fear makes them obey
gained = gain(drawn * son_drain_yield / 100)
chronicle(epoch, s.id, 'tanri', DRAIN template)
reputationTrace('drain', s.id)        # §3.6
return {son, drawn, gained}
```
DRAIN template selection: `seq` = number of chronicle rows this epoch of type `tanri` that are drain lines (all sons); `times` = same but for this son. Template = `TEMPLATES[seq % 4]`; `again = times ? "again " : ""`; `anger = spontaneous ? "his anger overflowing, " : ""`; if `times > 1` the final period becomes `" (the {times+1}th time this epoch)."`. (The old code identifies drain lines by the Turkish regex `'%özünü%emdi%'` — LANGUAGE-SPECIFIC hack; the new design must store a structured `kind='drain'` on the chronicle row and count that.)
1. "{T}, {anger}{again}drained {son}'s essence: {drawn} essence was drawn, {gained} of it passed to the creator. {son} withered{; his brothers watched in fear}."
2. "{T} {anger}laid a hand on {son} and {again}drained his essence ({drawn} essence; {gained} passed to the creator). {son}'s light went out for a moment{; the other sons fell silent}."
3. "{T} {anger}{again}drained {son}'s essence in one breath: {drawn} essence lost, {gained} returned to the father.{ His brothers understood their turn might come too.}"
4. "{T}, {anger}{again}drained {son}'s essence and took {gained} into his own ({drawn} essence drawn). {son} was shaken{; no one in the pantheon raised a voice}."
(The `{…}` clauses appear only if the son has living brothers.)

**Devour a son** — `devourSon(sonId, reason='')` (old `ogluYutIc`):
```
s = livingSon(sonId)
gained = gain(s.essence + (s.stats.might ?? 0) * son_devour_might + (s.level || 1) * son_devour_level)
s.essence = 0; save                     # so the death routine does not refund half the essence again
friends = set(lovers(s))
godDeath(s, epoch, "{T} devoured him{: reason}")        # derin.tanriOlumu — creates corpse place, ghost spirit, resurrection order, story thread, etc.
for other non-dead sons k: addPassion(k, loyalty, +son_devour_loyalty); if k in friends: addPassion(k, anger, +son_devour_anger); save
reputationTrace('devour', s.id, {friends})
chronicle(epoch, s.id, 'tanri', "{T} devoured his son {s}; all his essence and might returned to the creator ({gained} essence).")
```
`godDeath` (derin.js, other part) side effects worth knowing: corpse place "{name}'s Bones" (tags `tanrı cesedi`, `ceset:{id}`), a ghost spirit, each worshipper has `DERIN.inkar_sans`=50% to renounce (become godless), remaining faithful form a resurrection order tagged `dirilis:{sonId}` with devotion 0, an open story thread, `durum='olu'`, `asi=0`, creator gets `round(son.essence / DERIN_YASAM.olu_oz_bolen(2))` essence back, siblings react by relationship.

**Drain / devour a named mortal** — `drainMortal(id, {devour=false})` (old `olumluOzEmIc`):
```
v = canonEntity(id, 'This mortal'); if v.type != 'olumlu': throw "Life can only be drained from a named mortal."
life = v.stats.life(can) ?? 0
if devour:
   gained = gain(life / mortal_drain_divisor + (v.power_level || 0) * mortal_power_essence)
   r = attemptKill(v, {killerType:'t', certain:true, epoch, how:'life and soul devoured by the creator'})   # §5.1
   chronicle(epoch, null, 'tanri', "{T} devoured {v}'s life and soul ({gained} essence).", [v.id])
   return {entity, gained, text: r.text}
drawn = round(life * mortal_drain_share / 100); if drawn ≤ 0: throw "{v} has no life to drain."
v.stats.life = max(1, life - drawn); save
gained = gain(drawn / mortal_drain_divisor)
addTag(v, 'özü emilmiş' = "essence-drained")
chronicle(..., "{T} drew {drawn} of {v}'s life; {v} lives but is hollow inside ({gained} essence).", [v.id])
```

**Harvest faith from a community** — `harvestCommunity(id)` (old `toplulukHasatIc`):
```
v = canonEntity(id, 'This community'); type must be in COMMUNITY else throw "Faith can only be harvested from a people, settlement, faction or order."
popKey = first present of [population(nufus), disciples(murit), members(uye)] or null
victims = popKey ? round(v.stats[popKey] * harvest_population / 100) : 0
faithLoss = min(v.stats.faith ?? 0, harvest_faith)
if !victims and !faithLoss: throw "{v} carries nothing to harvest (no population and no faith)."
v.stats[popKey] = max(0, … - victims); faith = clamp(faith - faithLoss); save
gained = gain(victims / harvest_population_divisor + faithLoss * harvest_faith_essence)
for each living son s the community worships (active 'tapar' → 'o'): addPassion(s, loyalty, -harvest_patron_grudge); save
chronicle(..., "{T} harvested the faith of {v}{: {victims} lives were sacrificed}{, their faith dimmed by {faithLoss}} ({gained} essence).{ {sons} resented the reaping of their worshippers.}", [v.id])
```

### 2.2 Foreign gods

`killForeignGodCost(y) = round((fg_kill_base + y.power * fg_kill_power / 100) * (any power with effect 'olumsuz'(immortal) ? fg_immortal_mult : 1))`.

**Drain a foreign god** — `drainForeignGod(id)`:
```
y = foreignGod(id); if dead: throw "{y} is dead; their essence scattered long ago."
drawn = max(y.power > 0 ? 1 : 0, round(y.power * fg_drain_share / 100)); if !drawn: throw "{y} has no power left to drain."
newPower = y.power - drawn; status = newPower ≤ 0 ? 'yenik'(defeated) : y.status
UPDATE power = max(0,newPower), attitude = max(-100, attitude - fg_drain_attitude), status,
       defeat_epoch = (status=='yenik' and old != 'yenik') ? epoch : defeat_epoch
gained = gain(drawn * fg_power_essence)
chronicle(epoch, null, 'yabanci_tanri', "{T} drained {drawn} of the foreign god {y}'s power ({gained} essence){; {y} lost its power and fell defeated}.")
```

**Kill (or devour) a foreign god** — `killForeignGod(id, {reason, devour=false})`:
```
y = foreignGod(id); if dead: throw "{y} is already dead."
cost = killForeignGodCost(y); spend(cost, 'GOD_POWER.fg_kill_base')
gained = devour ? gain(y.power * fg_power_essence) : 0
UPDATE status='olu', power = devour ? 0 : y.power, death_epoch=epoch, awakening_pressure=0, defeat_epoch=NULL
for each active worship bond (v → y): deactivate it;
    t = entity; skip if not canon
    if chance(fg_worshipper_conversion/100) and worshipCreator(t, '{y} died and it turned to the creator'): converted++
    else: addTag(t,'tanrısız'); godless++
chronicle(..., 'yabanci_tanri', "{T} {devoured|killed} the foreign god {y}{ (reason)}{; its power passed to the creator ({gained} essence)}. {converted} of its worshippers turned to the creator, {godless} were left godless.")
return {foreignGod, cost, gained, converted, godless}
```

### 2.3 Resurrect and deify mortals

**Resurrect a named mortal** — `resurrectMortal(id)` (old `olumluDiriltIc`):
```
v = getEntity(id); if !v or type!='olumlu': throw "Only a named mortal can be resurrected."
if v.status != 'olu': throw "{v} is not dead."
if 'tanrılaştı'(deified) in tags: throw "{v} lives not as a mortal but as a god."
cost = mortal_resurrect + (v.power_level || 0) * mortal_resurrect_power; spend(cost)
v.stats.life = max(life ?? 0, mortal_resurrect_life)
if (age ?? 0) ≥ (lifespan ?? ∞): lifespan = age + mortal_resurrect_lifespan     # died of old age
save; UPDATE status='kanon', death_epoch=NULL, fate_note += " Epoch {e}: {T} called them back from death."
addTag(v, 'ölümden dönen' = "returned from death")
chronicle(..., "{T} called {v} back from death. Having seen the other side, they walk again.", [v.id])
```

**Deify a mortal (raise to the pantheon)** — `deify(id)` (old `tanrilastirIc`):
```
v = canonEntity(id, 'This mortal'); type must be 'olumlu' else throw "Only a named mortal can be raised to godhood."
if a son with the same name exists: throw "A son named {v} already exists; rename the mortal first."
spend(deify, 'GOD_POWER.deify')
rarity = RARITY_KEYS[min(index('efsanevi'/legendary), index(classOf(v.power_level)))]   # mythic only via ascension
STAT_MAP = { mortal strength(guc) → son strength(guc), mortal intellect(akil) → son wisdom(bilgelik),
             mortal charisma(karizma) → son charisma(karizma), mortal agility(ceviklik) → son cunning(kurnazlik) }
strong = the 2 son stats whose mapped mortal stats are highest (mortal stat desc)
stats = rollStats(rarity, strong, [])
passions = {loyalty: deify_loyalty, others: randInt(0,50)}
domains = 2 random distinct from ALANLAR (domains list)
power = the parameterless power effect (GUC_ETKILERI where !param) that the fewest current sons own (tie: list order); powers=[{name, description, effect, param:null}]
firstSentence = first sentence of v.description (strip leading "[...]" marker)
personality = { appearance: firstSentence,
                temperament: "When mortal they were {subtype or 'a mortal'}; the only god who knows what death is.",
                obsession: "The mortals left behind", fear: "Becoming mortal again", style:'', secret:'' }
INSERT son(name=v.name, title="Raised {subtype or 'Mortal'}", rarity, domain1, domain2, personality, stats, passions,
           life=canMax(stats), essence=ozMax(stats), parent=NULL, birth_epoch=epoch, image_prompt=v.image_prompt,
           powers, existence=deify_existence, stars=1)
UPDATE son.active_world = v.world_id ?? 1
kill(v.id, epoch, "Epoch {e}: {T} took them up into the sky; now a god among the sons.", {bonds:true})   # derin.oldur
addTag(v, 'tanrılaştı' = "deified")
addBond('o', sonId, 'v', v.id, 'ilgili'(related), 'mortal past')
for every (historic, not only active) worship bond (x -tapar-> v): addBond('v', x, 'o', sonId, 'tapar', 'they believed in them when mortal too')
chronicle(epoch, sonId, 'yukselis'(ascension), "{T} took the mortal {v} into the sky: they joined the pantheon as a son of {rarity} class.", [v.id])
publish {kind:'yeni_ogul'} event (epoch.js wrapper)
```

### 2.4 Son class, power and command

**Demote a son** — `demoteSon(sonId)`:
```
s = livingSon; i = index of rarity; if i ≤ 0: throw "{s} is already in the lowest class ({rarity})."
spend(demote); new = RARITY_KEYS[i-1]; hi = RARITIES[new].stat[1]
for each son stat: clamp(min(stat, hi), 1, 100)
addPassion(loyalty, -demote_loyalty); addPassion(anger, +demote_anger)
UPDATE rarity=new; save
chronicle(..., s.id, 'tanri', "{T} demoted {s} from {old} class to {new} class. Their might narrowed; a grudge remained inside.")
reputationTrace('demote', s.id)
```

**Strip a power** — `stripPower(sonId, index)`:
```
s = livingSon; n must be an integer index of an existing power else throw "Choose the power to strip."
spend(strip_power); remove powers[n]; addPassion(anger, +strip_power_anger); save
gained = gain(strip_power_essence)
chronicle(..., "{T} tore away {s}'s power \"{power}\" ({gained} essence returned to the creator).")
reputationTrace('strip', s.id)
```

**Absolute command** — `absoluteCommand(sonId, command)`:
```
s = livingSon; m = trimmed command (≤ GOD_ACTION.inspiration_length = 600 chars, cut by wrapper); empty → throw "Write the command."
spend(absolute_command)
s.command(emir) = m; addPassion(loyalty, -absolute_loyalty); save; UPDATE emir_mutlak=1
chronicle(..., s.id, 'emir'(command), "{T} gave {s} an irrefusable command: \"{m}\"")
```
(The son agent module treats `emir_mutlak=1` as a command the son cannot refuse — other spec part.)

### 2.5 Mortals and communities

**Choose a prophet** — `chooseProphet(id)` → manual: `canonEntity`, type `olumlu` ("A prophet can only be a named mortal."), not already tagged `peygamber` ("{v} is already your prophet."), `spend(prophet)`, then `makeProphet(v, epoch)`:
```
makeProphet(v, epoch, {spontaneous=false}):
  v.charisma = clamp(+prophet_charisma); save; addTag(v,'peygamber'(prophet))
  worshipCreator(v, 'became his prophet')
  t = communityOf(v); if t and t.faith != null: t.faith += prophet_faith (clamped)
  chronicle(epoch, null, spontaneous ? 'tanri_isareti' : 'tanri',
     "{T}{, contentment overflowing,} chose {v} as his prophet{; {t} began to listen to their words}.", [v.id, t?.id])
```

**Manifest** — `manifest(id, words)`:
```
v = canonEntity(id); type ∈ NAMED ∪ COMMUNITY else throw "The god appears only to a mortal or a community."
m = trim(words)[:manifest_length]; empty → throw "Write what you will say to them."
spend(manifest)
insert message(epoch, 't' → 'v' v.id, intent 'tezahur'(manifestation), m)
if v.faith != null: faith += manifest_faith
addTag(v, 'tanrıyı gördü' = "saw the god")
worshipped = chance(manifest_worship_chance/100) and worshipCreator(v, 'saw the creator with their own eyes')
chronicle(..., "{T} appeared to {v} while awake and spoke: \"{m}\"{ From that day {v} worships only him.}", [v.id])
```

**Bloodline** — `bloodline(rootId, depth=bloodline_depth)`: BFS over bonds `x -soyundan(descends from)-> parent` (src 'v', dst 'v'), starting at root, up to `depth` generations; returns root + descendants (all statuses).
`curse(v)`: for stat keys in [prosperity(refah), fertility(bereket), strength(guc), defense(savunma), wealth(servet), abundance(bolluk), influence(etki), charisma(karizma)] present: `-= bloodline_stat` (clamp 0..100); save; addTag(v, 'lanetli'(cursed), 'soy laneti'(bloodline curse)).

**Curse a bloodline** — manual: `canonEntity`; root tagged `soy laneti` → throw "{root}'s bloodline is already cursed."; `spend(bloodline_curse)`; `curseBloodline(root, epoch)`:
```
living = bloodline(root.id) filtered status=='kanon'; each → curse()
chronicle(epoch, null, reason ? 'tanri_isareti' : 'tanri',
  "{T}, {reason; }cursed {root}'s bloodline: {n} living descendants fell under the curse; those yet to be born will carry it too.", living ids)
```
**Lift a bloodline curse** — `getEntity(id)` ("No record"), `cursed = bloodline(root) tagged 'soy laneti'`; none → throw "There is no bloodline curse in {root}'s line."; `spend(bloodline_lift)`; for each remove tags `soy laneti` and `lanetli`; chronicle "{T} lifted the curse from {root}'s bloodline ({n} people)."

**Convert to self** — `convertToSelf(id)`:
```
v = canonEntity; type ∈ COMMUNITY ∪ NAMED else throw "Only a community or a mortal can be turned to you."
if v worships creator and worships no son/foreign god: throw "{v} already worships only you."
spend(convert)
old = active worship bonds of v to 'o' or 'y'
for each: deactivate; if son and alive: addPassion(son, loyalty, -convert_grudge)
worshipCreator(v, '{T} turned them to himself')
chronicle(..., "{T} turned {v} to himself{; {old gods} are no longer its gods}. It now worships the creator directly.", [v.id])
```

**Wrath (destroy a record)** — `wrath(id, reason)`:
```
v = canonEntity; type 'bolge' → throw "A region is not destroyed; send a disaster or a world wrath upon it."
type 'olumlu' → throw "Taking a mortal's life is a separate action (\"Take their life\")."
cost = wrath_base + (v.power_level || 0) * wrath_power; spend(cost)
for each canon named mortal located directly in v (location_id == v.id):
    if random < wrath_death/100: attemptKill(o, {killerType 't', certain:true, how:'together with {v}'}); died++   (errors swallowed)
moveContents(v.id, v.location_id ?? null, epoch, {onlyCanon:true})     # world.icindekileriDevret: children move up one level
kill(v.id, epoch, "Epoch {e}: destroyed by {T}'s wrath{ (reason)}.", {status:'yok_edildi', bonds:true})
chronicle(..., "{T} destroyed {v} with his wrath{ (reason)}{; the {died} named mortals inside also perished}.", [v.id])
```

**World wrath** — `worldWrath(worldId, kind)`:
```
w0 = world row or throw "No such world."; forgotten → throw "{w0} is forgotten; no hand reaches the world in the mist."
kind ∈ AFETLER {deprem earthquake, sel flood, veba plague, kuraklik drought, firtina storm} else throw "Choose the form of wrath (earthquake, flood, plague, drought, storm)."
regions = canon regions of that world; none → throw "There is no region in {w0} for the wrath to fall on."
spend(world_wrath)
for each region b: applyDisaster(b, kind, world_wrath_severity/100); ids += recordEvent({type:kind, target:b, severity: world_wrath_severity, source:'tanri'})
chronicle(..., "{T} sent {disaster} upon all of {w0}: all {n} regions were shaken.", ids)
```

### 2.6 Rebellion (shared by the son tool and the spontaneous path)

`declareRebellion(s, epoch, manifesto, {spontaneous})` (old `isyanIlan`):
```
loyalty = s.loyalty ?? SON_TOOL.loyalty_default(50)
s.rebel = 1; s.loyalty = clamp(loyalty - SON_TOOL.rebellion_loyalty_loss(10)); s.ambition += SON_TOOL.rebellion_ambition(5); save
for every other son k with (k.loyalty ?? 50) ≥ SON_TOOL.rebellion_loyal_threshold(60): relationship(s,k) -= SON_TOOL.rebellion_sibling_relation(12)
chronicle(epoch, s.id, 'isyan'(rebellion), spontaneous ? "{s} rebelled against his father {T}: {manifesto}" : "{s} rebelled against his father {T}: \"{manifesto}\"")
```
(SON_TOOL = rule domain `OGUL_ARAC` defined in tools.js.) Effects of being a rebel elsewhere: rebels ignore commands, steal essence from the creator every epoch (sim.js), add anger and doomsday.

### 2.7 Spontaneous god power per epoch (`godPowerEpoch(oldEpoch, newEpoch, notes)`)

Runs right after the mood update. Reads `mood = world.tanri_ruh`. Order:

1. **Spontaneous rebellion**: candidates = active, non-rebel sons with `loyalty(default 50) < auto_rebel_loyalty` and `anger ≥ auto_rebel_anger`, sorted by loyalty asc, anger desc, id asc. If any and `chance(auto_rebel_chance)`: the **first** declares rebellion with manifesto "his loyalty exhausted and his anger overflowing; no one heard a declaration, only his father's name was erased from his altars." Note "{s} rebelled against his father."
2. **Angry auto-drain**: if `mood.anger ≥ auto_drain_anger`: target = a uniformly random active rebel with essence > 0; else the "most stubborn" non-rebel active son with essence > 0 and loyalty < `auto_drain_loyalty` (sorted loyalty asc, anger desc, id asc; first). If target and `chance(auto_drain_chance)`: `drainSon(target, {spontaneous:true})` (free; no cost). Note "{T} angrily drained {s}'s essence ({gained})."
3. **Return of rebels**: for each non-dead rebel with `loyalty ≥ auto_return_loyalty`: `chance(auto_return_chance)` → `rebel=0`, chronicle 'isyan' "{s}'s rebellion died out: his loyalty returned and he again recognized his father {T}'s commands." (no limit per epoch).
4. **Spontaneous bloodline curse** (at most one per epoch):
   - `uncursed(v)` = canon `olumlu` without tag `soy laneti`.
   - *Bloody hand*: distinct killers from bonds `x -oldurdu(killed)-> victim` with bond epoch ≥ `newEpoch − auto_curse_epochs`, where victim is tagged `peygamber` or has (any, even inactive) worship bond to the creator; ordered by bond id; reason "{victim}'s blood did not stay on the ground"; filter uncursed. If any and `chance(auto_curse_chance)`: candidate = first.
   - Else if `mood.anger ≥ auto_curse_anger`: pool = (a) killers who destroyed (`yok_etti`) a `yapit` (work/building) whose name or subtype contains temple/sanctuary/altar (TR substrings `tapınak|mabet|sunak`), reason "{T} did not forget the hand that tore down {place}"; (b) canon uncursed mortals tagged `lanetli`, reason "anger overflowing, he cursed the blood of the cursed too"; (c) if `auto_curse_killer > 0`: mortals with ≥ `auto_curse_killer` `oldurdu` bonds, reason "the hand that took {n} lives became the target of his anger". If pool and `chance(auto_curse_anger_chance)`: pick via `rollTop(pool, sort by power_level desc, id asc)` = uniform among the first `auto_candidates`.
   - If a candidate: `curseBloodline(v, newEpoch, reason)` (free; chronicle type 'tanri_isareti'); note "{T} cursed {v}'s bloodline ({n} people)."
5. **Spontaneous prophet**: if `auto_prophet_cap > 0` and `mood.contentment ≥ auto_prophet_content`: count living prophets; if `< auto_prophet_cap`: cult = set of creator-worshipper ids (active); candidates = canon mortals not prophet, not `lanetli`, that are in the cult or whose community is in the cult; if any and `chance(auto_prophet_chance)`: `rollTop(candidates, sort by charisma+intellect(akil) desc, id asc)` → `makeProphet(p, newEpoch, {spontaneous:true})`. Note.
6. **Curse passes to newborns**: `cursedIds` = canon entities tagged `soy laneti`; `new` = canon entities with a `soyundan` bond to any cursed id and not yet tagged → each `curse()`; chronicle 'tanri_isareti' "The bloodline curse passed to {n} newborns: {first `bloodline_depth` names}." Note.
7. **Prophet's community converts**: for each canon prophet with a community `t`: `chance(prophet_conversion_chance)` and `worshipCreator(t, 'by the word of the prophet {p}')` → chronicle 'tanri_isareti' "{t} began worshipping the creator {T} by the word of the prophet {p}." (`[t.id, p.id]`).

### 2.8 Tunables — domain `GOD_POWER` (old `TANRI_GUC`), group "God's power" for all rows

| Key (old) | Default | Min | Max | Label |
|---|---|---|---|---|
| son_drain_share (ogul_em_pay) | 50 | 1 | 100 | Drain from son: % of the son's essence per drain |
| son_drain_yield (ogul_em_verim) | 80 | 0 | 100 | % of drained essence passing to the god (rest scatters) |
| son_drain_loyalty (ogul_em_sadakat) | 10 | 0 | 100 | Loyalty loss of the drained son |
| son_drain_anger (ogul_em_ofke) | 15 | 0 | 100 | Anger gain of the drained son |
| son_drain_existence (ogul_em_varlik) | 5 | 0 | 100 | Existence loss of the drained son |
| son_drain_fear (ogul_em_korku) | 3 | 0 | 100 | Fear-driven loyalty gain of other sons witnessing the drain |
| son_devour_might (ogul_yut_kudret) | 3 | 0 | 100 | Devour son: extra essence per might point |
| son_devour_level (ogul_yut_seviye) | 20 | 0 | 1000 | Devour son: extra essence per level |
| son_devour_loyalty (ogul_yut_sadakat) | 10 | 0 | 100 | Devour son: fear-driven loyalty gain of other sons |
| son_devour_anger (ogul_yut_ofke) | 25 | 0 | 100 | Devour son: anger of those who loved the devoured |
| mortal_drain_share (olumlu_em_pay) | 50 | 1 | 100 | Drain life from mortal: % of their life |
| mortal_drain_divisor (olumlu_em_bolen) | 10 | 1 | 1000 | Every this much drained life becomes 1 essence |
| mortal_power_essence (olumlu_guc_oz) | 2 | 0 | 100 | Devour mortal: extra essence per power level |
| harvest_population (hasat_nufus) | 10 | 0 | 100 | Faith harvest: % of population sacrificed |
| harvest_faith (hasat_inanc) | 20 | 0 | 100 | Faith harvest: community faith loss |
| harvest_population_divisor (hasat_nufus_bolen) | 500 | 1 | 1000000 | Faith harvest: every this many victims becomes 1 essence |
| harvest_faith_essence (hasat_inanc_oz) | 1 | 0 | 100 | Faith harvest: essence per faith point lost |
| harvest_patron_grudge (hasat_tapanin_kini) | 8 | 0 | 100 | Loyalty loss of the son worshipped by the harvested community |
| fg_drain_share (yt_em_pay) | 30 | 1 | 100 | Drain foreign god: % of its power |
| fg_power_essence (yt_guc_oz) | 3 | 0 | 100 | Essence per foreign-god power point |
| fg_drain_attitude (yt_em_tutum) | 20 | 0 | 200 | Attitude drop of the drained foreign god |
| fg_kill_base (yt_oldur_taban) | 60 | 0 | 2000 | Base cost of killing a foreign god |
| fg_kill_power (yt_oldur_guc) | 100 | 0 | 1000 | Killing a foreign god: this % of its power is added to the cost |
| fg_immortal_mult (yt_olumsuz_kat) | 2 | 1 | 10 | Cost multiplier for a foreign god with an immortality power |
| fg_worshipper_conversion (yt_tapan_donus) | 50 | 0 | 100 | Chance (%) a dead foreign god's worshipper turns to the creator; others become godless |
| mortal_resurrect (olumlu_dirilt) | 40 | 0 | 1000 | Base cost of resurrecting a mortal |
| mortal_resurrect_power (olumlu_dirilt_guc) | 2 | 0 | 100 | Resurrect mortal: extra cost per power level |
| mortal_resurrect_life (olumlu_dirilt_can) | 50 | 1 | 300 | Life of the resurrected mortal |
| mortal_resurrect_lifespan (olumlu_dirilt_omur) | 20 | 0 | 50000 | Years added to lifespan of a mortal who died of old age when resurrected |
| deify (tanrilastir) | 150 | 0 | 5000 | Cost of raising a mortal to godhood |
| deify_loyalty (tanrilastir_sadakat) | 80 | 0 | 100 | Deified mortal's loyalty to you |
| deify_existence (tanrilastir_varlik) | 50 | 1 | 100 | Starting existence of the deified |
| demote (alcalt) | 40 | 0 | 1000 | Cost of demoting a son one class |
| demote_loyalty (alcalt_sadakat) | 15 | 0 | 100 | Loyalty loss of the demoted son |
| demote_anger (alcalt_ofke) | 25 | 0 | 100 | Anger gain of the demoted son |
| strip_power (guc_sok) | 30 | 0 | 1000 | Cost of tearing away one of a son's powers |
| strip_power_anger (guc_sok_ofke) | 20 | 0 | 100 | Anger gain of the stripped son |
| strip_power_essence (guc_sok_oz) | 15 | 0 | 1000 | Essence the stripped power gives the god |
| absolute_command (mutlak_buyruk) | 25 | 0 | 1000 | Cost of an irrefusable command |
| absolute_loyalty (mutlak_sadakat) | 5 | 0 | 100 | Loyalty loss of the son receiving an irrefusable command |
| prophet (peygamber) | 20 | 0 | 1000 | Cost of choosing a mortal as prophet |
| prophet_charisma (peygamber_karizma) | 15 | 0 | 100 | Prophet's charisma gain |
| prophet_faith (peygamber_inanc) | 10 | 0 | 100 | Faith gain of the prophet's community |
| prophet_conversion_chance (peygamber_donus_sans) | 15 | 0 | 100 | Per-epoch chance (%) the prophet's community turns to the creator |
| manifest (tezahur) | 10 | 0 | 1000 | Cost of appearing to a mortal or community while awake |
| manifest_faith (tezahur_inanc) | 10 | 0 | 100 | Faith gain from a manifestation |
| manifest_worship_chance (tezahur_tapin_sans) | 30 | 0 | 100 | Chance (%) the witness starts worshipping the creator |
| manifest_length (tezahur_uzunluk) | 600 | 50 | 5000 | Max length of the words spoken (chars) |
| bloodline_curse (soy_laneti) | 40 | 0 | 1000 | Cost of cursing a bloodline |
| bloodline_lift (soy_laneti_kaldir) | 20 | 0 | 1000 | Cost of lifting a bloodline curse |
| bloodline_depth (soy_derinlik) | 6 | 1 | 50 | How many generations the curse descends |
| bloodline_stat (soy_stat) | 10 | 0 | 100 | Strength, prosperity, etc. removed from each cursed one |
| convert (cevir) | 30 | 0 | 1000 | Cost of turning a community to yourself (it leaves its previous god) |
| convert_grudge (cevir_kin) | 10 | 0 | 100 | Loyalty loss of the son whose worshipper is taken |
| wrath_base (gazap_taban) | 60 | 0 | 5000 | Wrath: base cost of destroying a record |
| wrath_power (gazap_guc) | 5 | 0 | 1000 | Wrath: extra cost per power level |
| wrath_death (gazap_olum) | 70 | 0 | 100 | Wrath: chance (%) named mortals in the destroyed place die |
| world_wrath (dunya_gazap) | 200 | 0 | 10000 | Cost of sending wrath upon an entire world |
| world_wrath_severity (dunya_gazap_siddet) | 60 | 1 | 100 | World wrath: severity (%) of the disaster on each region |
| auto_drain_anger (oto_em_ofke) | 70 | 0 | 100 | Above this creator anger he may spontaneously drain rebel sons |
| auto_drain_chance (oto_em_sans) | 30 | 0 | 100 | Angry creator's per-epoch chance (%) to drain a rebel son |
| auto_drain_loyalty (oto_em_sadakat) | 20 | 0 | 100 | Without rebels, the angry creator may drain the most stubborn son with loyalty below this |
| auto_rebel_loyalty (oto_isyan_sadakat) | 15 | 0 | 100 | A son whose loyalty fell below this may rebel spontaneously |
| auto_rebel_anger (oto_isyan_ofke) | 60 | 0 | 100 | Minimum son anger for spontaneous rebellion |
| auto_rebel_chance (oto_isyan_sans) | 20 | 0 | 100 | Per-epoch chance (%) a qualifying son rebels |
| auto_return_loyalty (oto_donus_sadakat) | 50 | 0 | 100 | A rebel whose loyalty rises back to this may return to his father |
| auto_return_chance (oto_donus_sans) | 25 | 0 | 100 | Per-epoch chance (%) such a rebel abandons rebellion |
| auto_curse_epochs (oto_lanet_cag) | 3 | 0 | 100 | One who killed a prophet or creator-worshipper within this many epochs becomes a spontaneous curse candidate |
| auto_curse_chance (oto_lanet_sans) | 30 | 0 | 100 | Per-epoch chance (%) the bloody hand's line is cursed |
| auto_curse_anger (oto_lanet_ofke) | 55 | 0 | 100 | Above this creator anger he may curse the line of a cursed mortal, temple-wrecker or prolific killer |
| auto_curse_killer (oto_lanet_kanli) | 2 | 0 | 100 | Angry creator may also curse the line of a mortal who took at least this many lives (0: off) |
| auto_curse_anger_chance (oto_lanet_ofke_sans) | 15 | 0 | 100 | Angry creator's per-epoch chance (%) to curse such a line |
| auto_prophet_content (oto_peygamber_hosnut) | 70 | 0 | 100 | Above this contentment the creator may spontaneously choose a prophet from his cult |
| auto_prophet_chance (oto_peygamber_sans) | 20 | 0 | 100 | Content creator's per-epoch chance (%) to choose a prophet |
| auto_prophet_cap (oto_peygamber_tavan) | 2 | 0 | 100 | When living prophets reach this number no new one is chosen spontaneously (0: never) |
| auto_candidates (oto_aday) | 4 | 1 | 100 | Spontaneous choices are rolled among this many best candidates |

### 2.9 Cross-references
- Calls: `derin.etiketEkle/etiketSil/kanonlar/oldur/tanriOlumu`, `olum.canAlmaDene` (§5.1), `yaratici.yaraticiyaTapin` (§1.3), `mudahale.afetUygula/olayKaydi`, `itibar.tanriGucuIzi` (§3.6), `world.getSon/allSons/getVarlik/saveSon/saveStat/addBag/addKronik/iliskiDegistir/icindekileriDevret`, `rules.rollStats/canMax/ozMax/RARITIES/RARITY_KEYS/GUC_ETKILERI/ALANLAR/varlikSinifi/AFETLER`, rule domain `OGUL_ARAC` (tools.js).
- Called by: epoch.js wrappers (§12), `sim.js` (`tanriGucununCagi`), son tool `isyan_et` (tools.js → `isyanIlan`), server (`ytOldurBedel`, `gazapBedel` for UI price display).

---

## 3. Reputation and the creator's passions (`itibar.js`)

- **Passions** (tanrının tutkuları): what the god loves. Automatic: read from the god's recent actions. Manual: the player picks them (automatic mode turns off).
- **Reputation** (itibar): each son sees his father along three axes — love (`sevgi`), fear (`korku`), forgottenness (`unutma`), each 0–100 — producing a label. Automatic: computed from what the god did to that son (bless, forgive, answer prayers, stars, ascension ↔ lightning, chains, exile, suppression), conversations and unanswered prayers, decaying over epochs. Manual: the player can push a son's view directly (decays).
- **Effect**: a "how do you see your father" line is injected into the son's agent prompt; every epoch loyalty and anger drift by label.

### 3.1 Entities and fields
- `world.tanri_tutku` (JSON): `{otomatik: true, tutkular?: [...]}` or `{otomatik: false, tutkular: [...]}`.
- `son.itibar` (JSON, cached last computation): `{sevgi, korku, unutma, cevapsiz, son_temas, etiket, cag}`.
- `son.itibar_elle` (JSON): manual pushes `{sevgi?, korku?, unutma?}` (each within ±`manual_cap`, decays).
- `son.itibar_olay` (JSON): traces left by god power `{sevgi?, korku?}` (each within ±`trace_cap`, decays).

### 3.2 Passion catalogue (`TUTKULAR`, full)

| Key | Name (EN) | Hint |
|---|---|---|
| duzen | order | laws, borders, things falling into place |
| kaos | chaos | destruction, disasters, unexpected transformations |
| guzellik | beauty | art, works, songs, crafted things |
| bilgi | knowledge | taught knowledge, writing, discovery |
| savas | war | conflict, heroism, conquest |
| merhamet | mercy | miracles, healing, forgiven crimes |
| yaratim | creation | new worlds, stars, new peoples |
| sessizlik | silence | an untouched world, children left to themselves |

### 3.3 Passion reading

```
passions(w):
  t = parse(w.tanri_tutku)
  if t and not t.otomatik and t.tutkular is array: return {passions: t.tutkular ∩ known, automatic:false}
  return {passions: (t?.tutkular ∩ known) or readPassions(w), automatic:true}

readPassions(w):   # old tutkuOku
  rows = chronicle where son_id IS NULL and cag > w.cag - passion_window
         and type ∈ {tanri, dunya_dogusu, yildiz, kozmik, vahiy, emir}
  score = {all passions: 0}
  for row:
    creation  += passion_points if type=='dunya_dogusu' or text~/ignited|star|bore a world|created/
    chaos     += … if text~/disaster|sent|flood|plague|earthquake|storm|curse/
    mercy     += … if text~/miracle|healing|abundance|heard the prayer|forgave/
    knowledge += … if text~/taught|knowledge|writing/
    order     += … if text~/law|sealed|statute|order/
    war       += … if text~/war|conquest|army/
    beauty    += … if text~/work|song|art|beautiful/
  top = passions with score > 0 sorted desc, first passion_count
  return top or ['sessizlik'(silence)]
```
(LANGUAGE-SPECIFIC: the old code matches Turkish words in free chronicle text. The new design must instead tag each player-action ledger/chronicle row with a structured `action_kind` and map kinds → passions; see §14.)

`setPassions({tutkular, otomatik})` (old `tutkuAyarla`): if `otomatik` → store `{otomatik:true}` and return. Else `clean = unique(known ∩ list)[:passion_count]`; empty → throw "Pick at least one passion (at most {passion_count})."; store `{tutkular: clean, otomatik:false}`; chronicle 'tanri' "{T} revealed himself: his passions are {names}."

### 3.4 Reputation computation (`computeReputation(son, w)`)

```
rows = chronicle where son_id = s.id and cag > w.cag - window and type ∈ {tanri, yildiz, yukselis, isyan, dirilis}
love = fear = 0; lastContact = s.birth_epoch ?? 1
for row: a = (decay/100) ^ max(0, w.cag - row.cag)
   if LOVE_EVENT(row) or text~/ascended/: love += love_event * a; lastContact = max(lastContact, row.cag)
   if FEAR_EVENT(row):                     fear += fear_event * a; lastContact = max(...)
for msg in messages from 't' to 'o' s.id with cag > w.cag - window:
   a = decay^(age); love += (intent=='tehdit'(threat) ? 0 : message_love) * a
   fear += (intent=='tehdit' ? threat_fear : 0) * a; lastContact = max(...)
if s.command(emir) present: lastContact = w.cag
prayers = messages from 'o' s.id to 't', unanswered, intent != 'sohbet', cag > w.cag - window
unanswered = len(prayers); unansweredWeight = Σ decay^(age)
mood = w.tanri_ruh; manual = s.itibar_elle; trace = s.itibar_olay
loyalty = s.loyalty ?? loyalty_default
love = clamp(round(love_base + love + loyalty/loyalty_divisor - unansweredWeight*unanswered_love + manual.love + trace.love), 0, 100)
fear = clamp(round(fear_base + fear + ((mood.anger ?? anger_default) - anger_default)/anger_divisor
                   + (s.chained ? chain_fear : 0) + manual.fear + trace.fear), 0, 100)
forgotten = clamp(round((w.cag - lastContact)*forget_per_epoch + unansweredWeight*unanswered_forget
                   + max(0, interest_threshold - (mood.interest ?? interest_default))/interest_divisor + manual.forgotten), 0, 100)
return {love, fear, forgotten, unanswered, last_contact, label: label(...)}
```
LOVE_EVENT (TR regex `kutsadı|affetti|bağışladı|duasına cevap|diriltti|yeniden doğurdu|yıldız daha kondurdu` + `yükseldi`): blessed, forgave, pardoned, answered the prayer, resurrected, re-birthed, granted another star, ascended.
FEAR_EVENT (TR regex `yıldırımla çarptı|zincire vurdu|sürgüne gönderdi|isyanını bastırdı|lanetledi`): struck with lightning, chained, exiled, suppressed the rebellion, cursed.
(LANGUAGE-SPECIFIC regexes over free text — replace with structured action kinds.)

**Label** — first match:

| Condition | Label |
|---|---|
| forgotten ≥ forgotten_min and love < forgotten_love_max and fear < forgotten_fear_max | unutulan → **forgotten** |
| fear ≥ hated_fear_min and love < hated_love_max and loyalty < hated_loyalty_max | nefret edilen → **hated** |
| fear ≥ respected_fear_min and love ≥ respected_love_min | saygı duyulan → **respected** |
| fear ≥ feared_fear_min | korkulan → **feared** |
| love ≥ loved_love_min | sevilen → **loved** |
| forgotten ≥ distant_forgotten_min | uzak → **distant** |
| otherwise | tanınan → **acknowledged** |

### 3.5 Prompt line for son agents (`reputationLine(son)`) — LLM prompt text

Template (translated):
`- HOW YOU SEE YOUR FATHER: {label} (love {love}, fear {fear}, forgottenness {forgotten}{, you have {n} unanswered prayers}). {BEHAVIOR[label]} Your father's passions: {passion names, comma-separated}.`

BEHAVIOR (full):
- forgotten: "Your father has forgotten you. His commands do not come, your prayers go unanswered; you are free to forge your own path — perhaps you will do something great enough to catch his attention."
- hated: "You hate your father: you fear him but do not love him. You obey his commands outwardly and resist in secret."
- respected: "You both respect and are wary of your father; serving his passions will elevate you."
- feared: "You fear your father. You obey his commands; you avoid deeds that would anger him."
- loved: "You love your father. Serving his passions makes you happy; do something that will please him."
- distant: "Your father is distant; he rarely mentions you. You are torn between winning his attention and learning to live without him."
- acknowledged: "You have an ordinary bond with your father."

### 3.6 Per-epoch reputation (`reputationEpoch(notes)`)

For each non-dead son (each wrapped in try/catch so one corrupt record does not break the epoch):
```
i = computeReputation(s, w); old = s.itibar
drift = { loved: [+loved_loyalty, 0], respected: [+respected_loyalty, +respected_anger], feared: [0, +feared_anger],
          hated: [-hated_loyalty_loss, +hated_anger], forgotten: [-forgotten_loyalty_loss, 0], distant: [-distant_loyalty_loss, 0],
          acknowledged: [0,0] }[i.label]
s.loyalty = clamp((s.loyalty ?? loyalty_default) + drift[0]); s.anger = clamp((s.anger ?? anger_default) + drift[1]); save
decay(x, keep) = each value → round(v * keep/100); drop |v| < manual_min; null if empty
UPDATE itibar = {...i, cag}, itibar_elle = decay(manual, manual_keep), itibar_olay = decay(trace, trace_keep)
if old.label exists and changed and new label ∈ {forgotten, hated, loved, feared}:
    m = "{s} now sees his father as a {label} god."; notes.push(m); chronicle(cag, s.id, 'tanri_itibar', m)
```
Then if passions are automatic (or unset): store `{otomatik:true, tutkular: readPassions(w)}`.
Note: `manual_min` (elle_esik) is used as the drop threshold for **both** manual and trace decay.

### 3.7 Manual push (`pushReputation(sonId, {love, fear, forgotten})`)
```
s must exist ("No such son."); dead → throw "{s} is dead; your place in their eyes no longer changes."
n = each axis clamp(existing + delta, -manual_cap, +manual_cap)
if no axis changed: throw "Manual push is at its limit: each may be at most ±{cap} (world rule ITIBAR.manual_cap = {cap}); pushes decay every epoch."
store itibar_elle = n; recompute and store itibar
return {ok, son_id, reputation, manual: n}
```
UI buttons in the son drawer use fixed step sizes: "Win his heart" (+`manual_love_step` love), "Instil fear" (+`manual_fear_step` fear), "Remind him of yourself" (−`manual_forget_step` forgottenness).

### 3.8 God-power traces (`reputationTrace(kind, sonId, {friends})`, old `tanriGucuIzi`)

| kind | target son: love / fear | every other living son: fear | friends of target: love |
|---|---|---|---|
| drain (em) | −drain_love / +drain_fear | +drain_sibling_fear | — |
| devour (yut) | (target is dead) | +devour_sibling_fear | −devour_friend_love |
| demote (alcalt) | −demote_love / +demote_fear | +demote_sibling_fear | — |
| strip (sok) | −strip_love / +strip_fear | +strip_sibling_fear | — |

For each non-dead son with a non-zero delta: `itibar_olay = clamp(old + delta, ±trace_cap)` per axis; recompute and store `itibar`. Unknown kind → throw. Returns `{sonId: {love, fear}}`.

### 3.9 Cosmos-level reputation (`godReputation()`)
Average love/fear/forgotten over living sons (0 if none), label via §3.4 using `loyalty_default` as loyalty; returns `{love, fear, forgotten, label, sons:[{id, name, ...reputation}], passions, automatic, all_passions: catalogue}`. Exposed as `GET /api/tanri/itibar` and summarized in `/api/state`.

### 3.10 Tunables — domain `REPUTATION` (old `ITIBAR`), group "Reputation"

| Key (old) | Default | Min | Max | Label |
|---|---|---|---|---|
| decay (sonum) | 75 | 0 | 100 | Share (%) of a past event's effect kept each epoch |
| window (pencere) | 8 | 1 | 100 | Epochs looked back when computing reputation |
| passion_window (tutku_pencere) | 5 | 1 | 100 | Epochs looked back when reading passions |
| passion_points (tutku_puan) | 2 | 1 | 100 | Points each action adds to its passion |
| passion_count (tutku_sayi) | 3 | 1 | 8 | Max number of god passions |
| love_event (sevgi_olay) | 14 | 0 | 100 | Love from a blessing, pardon or ascension |
| fear_event (korku_olay) | 22 | 0 | 100 | Fear from lightning, chains or exile |
| message_love (mesaj_sevgi) | 5 | 0 | 100 | Love per non-threatening word of the god |
| threat_fear (tehdit_korku) | 10 | 0 | 100 | Fear per threat of the god |
| loyalty_default (sadakat_varsayilan) | 50 | 0 | 100 | Assumed loyalty of a son without one |
| anger_default (ofke_varsayilan) | 20 | 0 | 100 | Assumed anger of a son / the god without one |
| interest_default (ilgi_varsayilan) | 60 | 0 | 100 | Assumed interest of the god without one |
| love_base (sevgi_taban) | 20 | 0 | 100 | Base love |
| loyalty_divisor (sadakat_bolen) | 4 | 1 | 100 | Loyalty's love contribution: loyalty / this |
| unanswered_love (cevapsiz_sevgi) | 6 | 0 | 100 | Love removed per unanswered prayer |
| fear_base (korku_taban) | 10 | 0 | 100 | Base fear |
| anger_divisor (ofke_bolen) | 3 | 1 | 100 | God anger's fear contribution: (anger − default) / this |
| chain_fear (zincir_korku) | 15 | 0 | 100 | Extra fear of a chained son |
| forget_per_epoch (unutma_cag) | 12 | 0 | 100 | Forgottenness per epoch without contact |
| unanswered_forget (cevapsiz_unutma) | 5 | 0 | 100 | Forgottenness per unanswered prayer |
| interest_threshold (ilgi_esik) | 40 | 0 | 100 | If the god's interest is below this, forgottenness grows |
| interest_divisor (ilgi_bolen) | 2 | 1 | 100 | Indifference's forgottenness contribution: missing interest / this |
| forgotten_min (unutulan_unutma) | 60 | 0 | 100 | Min forgottenness to count as "forgotten" |
| forgotten_love_max (unutulan_sevgi) | 50 | 0 | 100 | Love must stay below this to count as "forgotten" |
| forgotten_fear_max (unutulan_korku) | 50 | 0 | 100 | Fear must stay below this to count as "forgotten" |
| hated_fear_min (nefret_korku) | 55 | 0 | 100 | Min fear to count as "hated" |
| hated_love_max (nefret_sevgi) | 35 | 0 | 100 | Love must stay below this to count as "hated" |
| hated_loyalty_max (nefret_sadakat) | 35 | 0 | 100 | Loyalty must stay below this to count as "hated" |
| respected_fear_min (saygi_korku) | 50 | 0 | 100 | Min fear to count as "respected" |
| respected_love_min (saygi_sevgi) | 50 | 0 | 100 | Min love to count as "respected" |
| feared_fear_min (korkulan_korku) | 50 | 0 | 100 | Min fear to count as "feared" |
| loved_love_min (sevilen_sevgi) | 55 | 0 | 100 | Min love to count as "loved" |
| distant_forgotten_min (uzak_unutma) | 40 | 0 | 100 | Min forgottenness to count as "distant" |
| loved_loyalty (sevilen_sadakat) | 2 | 0 | 50 | Per-epoch loyalty gain of a son who loves his father |
| respected_loyalty (saygi_sadakat) | 1 | 0 | 50 | Per-epoch loyalty gain of a son who respects his father |
| respected_anger (saygi_ofke) | 1 | 0 | 50 | Per-epoch anger gain of a son who respects his father |
| feared_anger (korkulan_ofke) | 2 | 0 | 50 | Per-epoch anger gain of a son who fears his father |
| hated_loyalty_loss (nefret_sadakat_kayip) | 2 | 0 | 50 | Per-epoch loyalty loss of a son who hates his father |
| hated_anger (nefret_ofke) | 3 | 0 | 50 | Per-epoch anger gain of a son who hates his father |
| forgotten_loyalty_loss (unutulan_sadakat_kayip) | 2 | 0 | 50 | Per-epoch loyalty loss of a forgotten son |
| distant_loyalty_loss (uzak_sadakat_kayip) | 1 | 0 | 50 | Per-epoch loyalty loss of a son whose father is distant |
| manual_keep (elle_kalan) | 60 | 0 | 100 | Share (%) of the god's manual push kept each epoch |
| manual_min (elle_esik) | 2 | 1 | 100 | A push decayed below this is removed |
| manual_cap (elle_tavan) | 60 | 0 | 100 | Max manual push on each axis |
| manual_love_step (elle_sevgi) | 10 | 1 | 100 | Love push of one click of "Win his heart" in the son drawer |
| manual_fear_step (elle_korku) | 10 | 1 | 100 | Fear push of one click of "Instil fear" |
| manual_forget_step (elle_unutma) | 15 | 1 | 100 | Forgottenness removed by one click of "Remind him of yourself" |
| trace_keep (olay_kalan) | 60 | 0 | 100 | Share (%) of the god-power trace kept each epoch |
| trace_cap (olay_tavan) | 80 | 0 | 100 | Max god-power trace on each axis |
| drain_fear (em_korku) | 15 | 0 | 100 | Extra fear of the drained son |
| drain_love (em_sevgi) | 12 | 0 | 100 | Love lost by the drained son |
| drain_sibling_fear (em_kardes_korku) | 6 | 0 | 100 | Extra fear of siblings who witness a drain |
| devour_sibling_fear (yut_kardes_korku) | 20 | 0 | 100 | Extra fear of siblings who see a son devoured |
| devour_friend_love (yut_dost_sevgi) | 15 | 0 | 100 | Love lost by those who loved the devoured son |
| demote_fear (alcalt_korku) | 12 | 0 | 100 | Extra fear of the demoted son |
| demote_love (alcalt_sevgi) | 12 | 0 | 100 | Love lost by the demoted son |
| demote_sibling_fear (alcalt_kardes_korku) | 4 | 0 | 100 | Extra fear of siblings who see a demotion |
| strip_fear (sok_korku) | 10 | 0 | 100 | Extra fear of the son whose power was stripped |
| strip_love (sok_sevgi) | 8 | 0 | 100 | Love lost by the stripped son |
| strip_sibling_fear (sok_kardes_korku) | 3 | 0 | 100 | Extra fear of siblings who see a power stripped |

### 3.11 Cross-references
- Calls: `world.getWorld/allSons/getSon/saveSon/addKronik`.
- Called by: son agent prompt builder (`itibarSatiri`), `sim.js` (`itibarCagi`), `tanriguc.js` (`tanriGucuIzi`), server (`tanriItibari`, `tutkuAyarla`, `itibarIt`), `kitap.js` (`tutkular`, `TUTKULAR`).

---

## 4. Goals, achievements and score (`hedef.js`)

Optional game layer:
- **Scenario** (senaryo, UI also "trial"/sınav): a goal the player chooses. At every epoch end the engine measures progress; when complete or failed it is recorded.
- **Achievement** (başarım): always on, earned automatically.
- **Score** (puan): computed at every epoch end from the world's vitality, achievements and scenarios; history kept.

### 4.1 Tables
- `senaryolar(id, anahtar, baslangic_cag, durum ∈ {suruyor running, tamam completed, basarisiz failed, birakildi abandoned}, veri JSON, bitis_cag, sonuc text)`.
- `basarimlar(anahtar PK, cag)`.
- `puanlar(cag PK, toplam, dokum JSON)`.

Helpers: `num(x, def)` coerces model-written stats ("12000", "much") to finite numbers; `tier(v)` = civilization tier of an entity (medeniyet.basamakOf); `population(list)` = Σ max(0, num(stats.population)); `warCount()` = count active `dusman`(enemy) bonds between entities (all, not only communities); `peoples()` = canon `halk`; `worshipped(v)` = the most recent active `tapar` bond of v (`(dst_type, dst_id)`); `threshold()` = max(1, `DENGE.kiyamet_esik`).

Display numbers: the old code spells numbers 0–100 in Turkish words (`yazi`) and ordinal names ("Birinci"… "Onuncu") — LANGUAGE-SPECIFIC; use English number words/ordinals or digits.

### 4.2 Scenarios (full list)

Each scenario: `progress(state, world) → {percent, text, done?, failed?, counter?}`, optional `start() → data` (stored in `veri`), optional `epochEnd(state, world) → data patch`. `state = {...veri, baslangic_cag}`.

| Key | Name | Description | Points | Progress logic |
|---|---|---|---|---|
| kiyamet_uzak | "Keep doomsday away for {doom_far_epochs} epochs" | "The doomsday clock must never reach {round(threshold*doom_far_limit/100)} for {doom_far_epochs} epochs." | doom_far_points | `limit = round(threshold*doom_far_limit/100)`; if clock ≥ limit → failed "Doomsday clock reached {clock}/{threshold}."; else elapsed = cag − start; percent = min(100, elapsed/duration*100); text "{elapsed}/{duration} epochs · clock {clock}/{threshold}"; done when elapsed ≥ duration |
| tek_inanc | "Unite all peoples in one faith" | "Every people in the world worships the same god (a son or you); at least {one_faith_peoples} peoples." | one_faith_points | count peoples per `worshipped` key `type:id`; most = max count; percent = most/peoples*100; text "{most}/{n} peoples worship the same god"; done when n ≥ one_faith_peoples and most == n |
| kayip_yildiz | "Rekindle the lost star" | "A dead star or black sun burns again." | lost_star_points | start: `reborn0` = count stars of type 'yeniden doğmuş yıldız'(reborn star). reborn = current count; dead = count types ∈ {ölü yıldız dead star, kara güneş black sun, yıldız kalıntısı star remnant}; if neither → text "There is no dead star in the cosmos yet; one must die first." percent 0; else percent = reborn > reborn0 ? 100 : 0, text "{dead} dead stars are waiting", done when reborn > reborn0 |
| bes_dunya | "A {world_count}-world cosmos" | "At least {world_count} worlds in the cosmos, each with a living people." | world_points | worlds = non-forgotten; inhabited = those with ≥1 canon `halk`; percent = inhabited/world_count; text "{inhabited}/{world_count} worlds inhabited ({n} worlds)"; done when inhabited ≥ world_count |
| uzun_baris | "{peace_epochs} epochs of peace" | "No war stays open for {peace_epochs} consecutive epochs." | peace_points | epochEnd: counter = warCount() ? 0 : counter+1. progress: counter (0 if wars now); text either "{n} wars ongoing; counter reset" or "{c}/{peace_epochs} peace epochs"; done when counter ≥ peace_epochs |
| kozmik_guc | "A civilization reaching for the stars" | "A people reaches civilization tier {cosmic_tier} ("interstellar power")." | cosmic_points | best = max tier over peoples and settlements; percent; text "highest tier {best}/{cosmic_tier}"; done when best ≥ cosmic_tier |
| sadik_panteon | "A loyal pantheon" | "No son rebels for {loyal_epochs} epochs; at the end every son's loyalty is above {loyal_loyalty}." | loyal_points | start: `asi0` = ids of current rebels, `kronik0` = max chronicle id. Fails if any non-dead rebel not in asi0 exists, or any chronicle row type 'isyan' with id > kronik0 whose text says "rebelled" (TR LIKE '%isyan etti%'; if kronik0 missing, cag > start). Else elapsed; loyalties of active sons (default `loyalty_default`); text "{elapsed}/{loyal_epochs} epochs without rebellion · {k}/{n} loyal"; done when elapsed ≥ loyal_epochs and all > loyal_loyalty |
| yeni_ufuklar | "{horizon_land} new lands" | "{horizon_land} new lands enter the map (at least {horizon_regions} regions): by mortal discovery, by the sons or by your hand." | horizon_points | start: `id0` = max entity id. regions = count entities id > id0, type 'bolge', status ∈ {kanon, olu}; total = regions + same for 'yer'; percent = min(total/horizon_land, horizon_regions ? regions/horizon_regions : 1)*100; text "{total}/{land} new lands · {regions}/{need} regions"; done when both met |

`startScenario(key)`: unknown → throw "No such scenario."; already running → throw "This scenario is already running."; insert `{key, start_epoch: cag, status:'suruyor', veri: start?() or {}}`; chronicle 'tanri' "{T} set himself a goal: {name}."; returns `goals()`.
`abandonScenario(id)`: must be running else "No such running scenario."; status 'birakildi', end epoch; returns `goals()`.
`scenarioProgress(row, w)`: calls progress inside try; on error `{text: "could not be measured: {error}"}`.

### 4.3 Achievements (full list; each has `condition(world)`; earned once)

| Key | Name | Description | Points | Condition |
|---|---|---|---|---|
| ilk_dunya | "{ordinal(ach_worlds)} sky" (e.g. "Second sky") | "There are {ach_worlds} worlds in the cosmos." | ach_worlds_points | count worlds ≥ ach_worlds |
| uc_yildiz | Constellation | "A cosmos of {ach_stars} stars." | ach_stars_points | count stars ≥ ach_stars |
| kehanet | The word came true | A prophecy was fulfilled. | ach_prophecy_points | ≥1 entity with status 'gerceklesti' |
| dirilis | Return from death | A dead son was resurrected. | ach_resurrection_points | ≥1 chronicle row type 'dirilis' (NB: olum.js also writes 'dirilis' rows for rites — fires early; see §14) |
| isyan_bastir | The father's hand | A rebellion was suppressed. | ach_rebellion_points | ≥1 chronicle 'isyan' whose text says "suppressed" (TR LIKE '%bastırdı%') |
| on_dil | Babel | "{ach_languages} languages are spoken." | ach_languages_points | canon `dil` count ≥ ach_languages |
| milyon | Crowded world | "Total population of peoples exceeded {ach_population}." | ach_population_points | population(peoples) ≥ ach_population |
| ilk_dua | Someone called you | A mortal prayed directly to you. | ach_prayer_points | ≥1 message v→t |
| kult | The creator's cult | "{ach_cult} communities worship you directly." | ach_cult_points | active v→t worship bonds ≥ ach_cult |
| ilk_sefer | Interstellar traveller | A journey reached another world. | ach_voyage_points | ≥1 `yolculuklar` with status 'vardi'(arrived) |
| efsane | Saga completed | A legendary expedition ended successfully. | ach_legend_points | ≥1 `iplikler` with `buyuk` not null, status 'kapandi', closing text contains "successfully" (TR '%başarıyla%') |
| on_cag | "God of {ach_epochs} epochs" | "The world left {ach_epochs} epochs behind." | ach_epochs_points | w.cag ≥ ach_epochs |
| elli_cag | Ancient | "The world left {ach_ancient_epochs} epochs behind." | ach_ancient_points | w.cag ≥ ach_ancient_epochs |
| sekiz_ogul | Crowded pantheon | "{ach_sons} sons live at once." | ach_sons_points | non-dead sons ≥ ach_sons |
| ilk_kasif | First explorers | Mortals found a land not on the map. | ach_discovery_points | ≥1 bond type 'kesfetti'(discovered) |
| sezilen_dunya | Sensed world | A world sensed by sky-watching mortals came to light. | ach_sensed_points | ≥1 `ufuk_sezgi` row status 'dogdu'(born) |
| barisci | The weapons fell silent | "An epoch ended without any war (with at least {ach_peace_peoples} peoples)." | ach_peace_points | peoples ≥ ach_peace_peoples and warCount() == 0 |

### 4.4 Per-epoch goals (`goalsEpoch(notes)`)
```
for each running scenario r:
   data = S.epochEnd ? {...r.veri, ...S.epochEnd(state, w)} : r.veri; store
   i = scenarioProgress({...r, veri:data}, w)
   if i.done or i.failed:
      UPDATE status = done ? 'tamam' : 'basarisiz', end_epoch, result = i.text
      m = done ? "Goal achieved: {name}." : "Goal lost: {name}. {text}"
      notes.push(m); chronicle(cag, null, 'tanri', m); notify({category:'basarim', title:m, importance:3})
for each achievement not yet earned: try condition(w); if true: insert (key, cag); notify({category:'basarim', title:"Achievement: {name}", text: description, importance:2})
p = score(w); INSERT OR REPLACE puanlar(cag, total, breakdown)
```
`notify` = bildirim.bildir (notification center; other part).

### 4.5 Score (`score(w)`)
```
breakdown = {
  population:   round(log10(1 + population(peoples)) * score_population),
  diversity:    min(score_diversity_cap, count canon entities),
  languages:    count canon 'dil' * score_language,
  worlds:       count worlds * score_world,
  civilization: max(0, tiers of peoples) * score_tier,
  doomsday:     -round(num(w.kiyamet)/threshold * doom_score_penalty),
  achievements: Σ points of earned achievements,
  scenarios:    Σ points of completed scenarios (each completion counts, repeats included) }
total = Σ breakdown
```
`goals()` (GET /api/hedefler): `{scenarios: [{key, name, description, points, history:[{id,status,start,end,result}]}], running: [{id,key,name,start, ...progress}], achievements: [{key,name,description,points,earned,epoch}], score, score_history:[{cag,total}]}`.

### 4.6 Tunables — domain `GOAL` (old `HEDEF`)

| Key (old) | Default | Min | Max | Group | Label |
|---|---|---|---|---|---|
| doom_far_epochs (kiyamet_uzak_cag) | 20 | 1 | 200 | Doomsday | Scenario: epochs to keep doomsday away |
| doom_far_limit (kiyamet_uzak_esik) | 80 | 1 | 100 | Doomsday | Scenario: point the clock must not reach (% of threshold) |
| doom_score_penalty (puan_kiyamet) | 150 | 0 | 1000 | Doomsday | Score: doomsday penalty when the clock is at the threshold |
| doom_far_points (kiyamet_uzak_puan) | 300 | 0 | 10000 | Goals and achievements | Scenario points: keep doomsday away |
| one_faith_peoples (tek_inanc_halk) | 3 | 1 | 100 | Goals and achievements | Scenario: minimum peoples that must unite in one faith |
| one_faith_points (tek_inanc_puan) | 250 | 0 | 10000 | Goals and achievements | Scenario points: all peoples in one faith |
| lost_star_points (kayip_yildiz_puan) | 200 | 0 | 10000 | Goals and achievements | Scenario points: rekindle the lost star |
| world_count (dunya_sayi) | 5 | 1 | 100 | Goals and achievements | Scenario: number of worlds with a living people |
| world_points (dunya_puan) | 250 | 0 | 10000 | Goals and achievements | Scenario points: multi-world cosmos |
| peace_epochs (baris_cag) | 5 | 1 | 200 | Goals and achievements | Scenario: consecutive peace epochs |
| peace_points (baris_puan) | 200 | 0 | 10000 | Goals and achievements | Scenario points: long peace |
| cosmic_tier (kozmik_basamak) | 4 | 1 | 20 | Goals and achievements | Scenario: civilization tier to reach |
| cosmic_points (kozmik_puan) | 300 | 0 | 10000 | Goals and achievements | Scenario points: civilization reaching the stars |
| loyal_epochs (sadik_cag) | 10 | 1 | 200 | Goals and achievements | Scenario: epochs that must pass without rebellion |
| loyal_loyalty (sadik_sadakat) | 60 | 0 | 100 | Goals and achievements | Scenario: loyalty every son must exceed |
| loyalty_default (sadakat_varsayilan) | 50 | 0 | 100 | Goals and achievements | Scenario: assumed loyalty of a son without one |
| loyal_points (sadik_puan) | 250 | 0 | 10000 | Goals and achievements | Scenario points: loyal pantheon |
| horizon_land (ufuk_toprak) | 8 | 1 | 1000 | Goals and achievements | Scenario: new lands to open (region or place; by discovery, son or god) |
| horizon_regions (ufuk_bolge) | 2 | 0 | 1000 | Goals and achievements | Scenario: how many of them must be new regions |
| horizon_points (ufuk_puan) | 250 | 0 | 10000 | Goals and achievements | Scenario points: new horizons |
| ach_worlds (b_dunya) | 2 | 1 | 100 | Goals and achievements | Achievement: number of worlds in the cosmos |
| ach_worlds_points (b_dunya_puan) | 50 | 0 | 10000 | Goals and achievements | Achievement points: new sky |
| ach_stars (b_yildiz) | 3 | 1 | 100 | Goals and achievements | Achievement: number of stars |
| ach_stars_points (b_yildiz_puan) | 40 | 0 | 10000 | Goals and achievements | Achievement points: constellation |
| ach_prophecy_points (b_kehanet_puan) | 40 | 0 | 10000 | Goals and achievements | Achievement points: prophecy fulfilled |
| ach_resurrection_points (b_dirilis_puan) | 60 | 0 | 10000 | Goals and achievements | Achievement points: return from death |
| ach_rebellion_points (b_isyan_puan) | 40 | 0 | 10000 | Goals and achievements | Achievement points: rebellion suppressed |
| ach_languages (b_dil) | 10 | 1 | 1000 | Goals and achievements | Achievement: number of spoken languages |
| ach_languages_points (b_dil_puan) | 50 | 0 | 10000 | Goals and achievements | Achievement points: Babel |
| ach_population (b_nufus) | 1000000 | 1000 | 2000000000 | Goals and achievements | Achievement: total population of peoples |
| ach_population_points (b_nufus_puan) | 60 | 0 | 10000 | Goals and achievements | Achievement points: crowded world |
| ach_prayer_points (b_dua_puan) | 30 | 0 | 10000 | Goals and achievements | Achievement points: first prayer |
| ach_cult (b_kult) | 3 | 1 | 100 | Goals and achievements | Achievement: communities worshipping the creator directly |
| ach_cult_points (b_kult_puan) | 60 | 0 | 10000 | Goals and achievements | Achievement points: the creator's cult |
| ach_voyage_points (b_sefer_puan) | 50 | 0 | 10000 | Goals and achievements | Achievement points: interstellar traveller |
| ach_legend_points (b_efsane_puan) | 80 | 0 | 10000 | Goals and achievements | Achievement points: saga completed |
| ach_epochs (b_cag) | 10 | 1 | 1000 | Goals and achievements | Achievement: epochs left behind (first threshold) |
| ach_epochs_points (b_cag_puan) | 50 | 0 | 10000 | Goals and achievements | Achievement points: first epoch threshold |
| ach_ancient_epochs (b_kadim_cag) | 50 | 1 | 10000 | Goals and achievements | Achievement: epochs left behind (ancient) |
| ach_ancient_points (b_kadim_puan) | 150 | 0 | 10000 | Goals and achievements | Achievement points: ancient |
| ach_sons (b_ogul) | 8 | 1 | 100 | Goals and achievements | Achievement: sons alive at once |
| ach_sons_points (b_ogul_puan) | 50 | 0 | 10000 | Goals and achievements | Achievement points: crowded pantheon |
| ach_peace_peoples (b_baris_halk) | 3 | 1 | 100 | Goals and achievements | Achievement: minimum peoples for a warless epoch |
| ach_peace_points (b_baris_puan) | 40 | 0 | 10000 | Goals and achievements | Achievement points: the weapons fell silent |
| ach_discovery_points (b_kesif_puan) | 40 | 0 | 10000 | Goals and achievements | Achievement points: first explorers |
| ach_sensed_points (b_sezgi_puan) | 80 | 0 | 10000 | Goals and achievements | Achievement points: sensed world |
| score_population (puan_nufus) | 20 | 0 | 1000 | Goals and achievements | Score: per tenfold of population |
| score_diversity_cap (puan_cesitlilik_tavan) | 150 | 0 | 100000 | Goals and achievements | Score: max points for record diversity |
| score_language (puan_dil) | 5 | 0 | 1000 | Goals and achievements | Score: per language |
| score_world (puan_dunya) | 25 | 0 | 1000 | Goals and achievements | Score: per world |
| score_tier (puan_basamak) | 20 | 0 | 1000 | Goals and achievements | Score: per step of the highest civilization tier |

### 4.7 Cross-references
Calls `medeniyet.basamakOf`, `bildirim.bildir`, `world.getWorld/kanonlar/addKronik`, `DENGE.kiyamet_esik`. Called by `sim.js` (`hedefCagi`), server (`hedefler`, `senaryoBaslat`, `senaryoBirak`), `kitap.js` (`hedefler`).

---

## 5. Death and resurrection (`olum.js`)

- **Taking a life**: a son (tool `can_al`), a foreign god (spontaneous strike) and the creator ("Aeron's hand") take a named mortal's life. For a son it is expensive and scales with the victim's importance; it is a dice roll: patron, creator-worship, protection and importance shield the victim. A failed attempt becomes a story (the reason for survival is narrated; the survivor becomes legend).
- **Resurrection of dead sons**: the dead son's resurrection order (diriliş tarikatı) accumulates **devotion** (adanmışlık); the order's devotion threshold and ritual roll live in derin.js (`tanrilarinKaderi`, other part). Contributions: rites and sacrifices of faithful communities (spontaneous and mortal tool `dirilis_ayini`), costly sibling schemes (rite, descent to the underworld, bargain with a foreign god; spontaneous and tool `kardesini_dirilt`). Hostile siblings can scatter the bones (`kemikleri_dagit`). The creator can resurrect directly (epoch.js `ogluDirilt`, cost `DENGE.dirilis`).

### 5.1 Taking a life

```
killCost(v):   # old canAlmaBedeli — paid by the caller (son tool)
  imp = importanceIndex(v.id).importance ?? v.importance ?? 0        # arsiv.onemler
  return round(kill_base + (v.power_level || 1)*kill_per_power + imp/kill_importance_divisor
               + (isImportantMortal(v) ? kill_important : 0))       # sim.onemliOlumlu: ruler, hero, chosen, titled

killChance(v, killer=null):   # old canAlmaSansi; UI and tool show the same computation
  imp = …; protectors = []
  p = kill_success + (killer?.stats.might || 0)/kill_might_divisor - imp/kill_importance_resist
  h = patron(v)  (the son v worships; world.hami)
  worshipsCreator = active bond v -tapar-> t
  if h alive and h != killer and not worshipsCreator: p -= kill_patron_resist; protectors += {type:'patron', name, id}
  if worshipsCreator: p -= kill_creator_resist; protectors += {type:'creator', name: T}
  shield = first tag ∈ {'korunmuş'(protected), 'seçilmiş'(chosen)}; if shield: p -= kill_protected; protectors += {type: shield}
  item = v's owned (active 'sahip') canon item ('esya') with stats.protection ≥ kill_item_protection, highest first
  if item: protectors += {type:'item', name, id}          # narrative only, no % effect
  return {percent: clamp(p, kill_min, kill_max), protectors, importance: imp}

attemptKill(v0, {killer, killerType='o'|'y'|'t', epoch, note=()=>{}, certain=false, how=''}):  # old canAlmaDene
  v = getEntity(v0.id ?? v0); must be canon 'olumlu' else throw "Only a living, named mortal's life can be taken."
  if not certain and v tagged 'ölümsüz'(immortal) or 'hayalet'(ghost): return {success:false, text:"{v} is immortal; death does not touch them.", story:'immortal'}
  S = killChance(v, killerType=='o' ? killer : null); killerName = killerType=='t' ? T : killer.name
  if certain or chance(S.percent/100):
     r = mortalDies(v, epoch, note, {reason: "life taken by the hand of {killerName}{ (how)}",
                                    killer: killerType=='t' ? null : {id: killer.id}, killerType, force: certain})   # sim.olumluOlur
     if killerType=='o': for o in [v.creator (if not killer), patron (if not killer)]: relationship(killer, o) -= kill_relation ("took {v}'s life")
     return {success:true, text: r.text or "{v} died.", percent, heir: r.heir}
  story = survivalStory(v, {name: killerName}, S)
  v.charisma += kill_charisma; save; addTag(v, 'ölümden dönen')
  legend = openRecord({type:'efsane'(legend), subtype:'return from death', name:"{v}'s Return from Death", epoch,
                       power: kill_legend_power, stats:{spread: kill_charisma}, description:"[World engine] {story}."})
  addBond(legend -anlatir(tells of)-> v)
  if a patron protected and killerType=='o': relationship(killer, patron) -= kill_relation ("protected {v}")
  text = "{killerName} sought to take {v}'s life but it did not hold: {story}."
  note(text, [v.id, legend], killerType=='o' ? killer.id : null)
  return {success:false, text, story, percent, legend}
```
Note `kill_refund` (can_al_iade) is declared but the refund is applied by the son tool (tools.js), not here.

**Survival story** (`survivalStory`) — priority with 50% rolls:
1. creator protector & 50%: "When {killer} reached for {v}'s life, {creator}'s hand descended from above the sky; no son could take a life devoted to the creator"
2. patron & 50%: "{patron} stepped in front of {v}; {killer}'s death command struck a brother's shield and scattered"
3. item & 50%: "The {item} that {v} carried drew death's breath onto itself and cracked; its owner survived"
4. shield (always): chosen → "{v} was one of the chosen; the threads of fate have not let go of them yet"; protected → "{v} was protected; death's hand slid off them"
5. otherwise uniform among:
   - "That night {v} heard death's footsteps in a dream and fled before dawn"
   - "The death {killer} sent knocked on the wrong door; a stranger died in {v}'s place"
   - "{v} looked death in the face and did not look away; death retreated before such courage"
   - "Just as death's hand was about to touch {v}, {killer}'s own domain trembled and the command fell empty"
   - "That night {v}'s people spoke their name so often that death could not find them in the crowd"

### 5.2 Resurrection state

```
epochsUntilResurrection(s, epoch) = max(0, (s.death_epoch ?? db value ?? epoch) + resurrection_min_epochs - epoch)
resurrectionOrders(sonId) = canon 'tarikat' tagged "dirilis:{sonId}"
resurrectionState(sonId):   # read by UI, opportunities, tools
  s must be dead else null
  orders = resurrectionOrders; corpse = s.corpse_id entity
  faithful = canon communities with active worship bond to the dead son
  return {id, name, death_epoch, earliest: death_epoch + resurrection_min_epochs, remaining, corpse:{id,name,status},
          orders:[{id,name,devotion,disciples}], faithful:[{id,name,type}], devotion: max(order devotions, 0)}

addDevotion(s, amount, {epoch, source}):
  T = order with highest devotion
  if none: create order {type 'tarikat', subtype 'resurrection order', name "Those Awaiting {s}'s Return",
            power DERIN_YASAM.resurrection_order_power(4), location: corpse ?? source.location,
            stats {disciples: new_order_disciples, zeal: DERIN_YASAM 75, influence: DERIN_YASAM 40, devotion: 0},
            tags ["dirilis:{s.id}"], description "[World engine] {source.name or 'A handful of believers who had not forgotten the name'} gathered again for {s}'s return."}
            + bond order -tapar-> son ("to the dead god")
  T.devotion = clamp(T.devotion + amount, 0, DERIN_YASAM.devotion_cap(200)); save
```
(The resurrection itself — devotion ≥ `DERIN_YASAM.dirilis_adanmislik` (100) → ritual roll — is in derin.js.)

### 5.3 Rites by mortals (`resurrectionRite(worshipper, sonId, {kind, epoch, note, victimId})`)

Kinds (`AYIN_TURLERI`): `dua` prayer, `servet` wealth offering, `kan` blood sacrifice, `can` life sacrifice.
```
s must be dead ("A resurrection rite is only for a dead god."); worshipper must be canon community or mortal ("Only a living community or mortal performs the rite."); kind valid.
pay(n): key = first present of [wealth(servet), prosperity(refah), craft(zanaat)]; none → false; insufficient → null;
        else subtract; cost text "{from its wealth|prosperity|craft labour} {n}"
prayer: contribution = prayer_devotion; cost "only their prayers"
wealth: r = pay(wealth_cost); null → throw "{t} is not wealthy enough to make an offering."; false → throw "{t} has no wealth to offer."; contribution = wealth_devotion
blood: key = population or disciples else throw "{t} is not a crowd that can give a blood sacrifice."
       n = max(1, round(stat * blood_population/100)); stat = max(SINIR.nufus_taban, stat - n); cost "{n} lives"; contribution = blood_devotion
life:  victim = victimId or (worshipper is mortal ? itself) must be canon 'olumlu' ("A life sacrifice needs a living named mortal.")
       if victim != worshipper and worshipper not mortal and not (victim located in worshipper, or 'yasar' bond, or same top region): throw "{victim} is not one of {t}'s people."
       mortalDies(victim, reason "sacrificed for {s}'s return", killer = victim==worshipper ? null : worshipper)
       cost "{victim}'s life"; contribution = life_sacrifice_devotion
save worshipper stats
pilgrimage = topRegion(worshipper) != null and == topRegion(corpse); if so contribution = round(contribution * pilgrimage_mult/100)
T = addDevotion(s, contribution, {epoch, source: worshipper})
text = "{t} offered {kind name} for {s}'s return ({cost}){, at the foot of their bones}; devotion {T.devotion}."
chronicle(epoch, null, 'dirilis', text, [t.id, T.id]); note(text, ...)
return {contribution, devotion, order: T.id, text}
```

### 5.4 Sibling schemes (`siblingScheme(sibling, sonId, {kind})`)

Kinds (`ENTRIKA_TURLERI`): `ayin` resurrection rite (cost `sibling_rite_cost`), `inis` descent to the underworld (`sibling_descent_cost`), `pazarlik` bargain with a foreign god (`sibling_bargain_cost`).
```
dead son required ("A resurrection scheme is only for a dead sibling."); sibling must be active and different ("Only an awake sibling can scheme."); kind valid
if sibling.essence < cost: throw "{kind} needs {cost} essence; {sibling} has {have} (world rule OLUM.sibling_{kind}_cost)."
rite:    contribution = sibling_rite_devotion
descent: if chance(sibling_descent_success): contribution = sibling_descent_devotion; extra "; pulled {s}'s shadow one step back from the shore of the dead"
         else: sibling.status='uykuda', sleep_remaining = sibling_descent_sleep; extra "; but lost their way in the underworld and fell asleep for {n} epochs"
bargain: y = an awake foreign god, preferring the dead son's active world (ORDER BY (world=son.world) DESC, id) else throw "There is no awake foreign god to bargain with."
         t = the first faithful worshipper (by bond id) of the dead son; if t: close its worship of the son; addBond(t -tapar-> y, "by {sibling}'s bargain")
         contribution = sibling_bargain_devotion; extra "; the price was {t} passing to {y}" or "; a promise given to {y}"
sibling.essence -= cost; save
T = contribution ? addDevotion(...) : null
if contribution: relationship(sibling, s) += sibling_rite_devotion / 2      # NB uses the rite value for all kinds
text = "{sibling} performed {kind} for their dead sibling {s} ({cost} essence){extra}{; devotion N}."
chronicle(epoch, sibling.id, 'dirilis', text, [T.id]); note
return {contribution, devotion, text, slept}
```

**Scatter the bones** (`scatterBones(who, sonId)`): dead son, awake other sibling; essence ≥ `scatter_cost` else throw "Scattering the bones needs {cost} essence; {who} has {have}."; pay; every resurrection order: devotion = max(0, devotion − scatter_devotion); relationship(who, s) −= scatter_devotion/2 ("scattered their bones"); each order gets an `dusman` bond to the scatterer if missing ("scattered {s}'s bones"); chronicle 'dirilis' "{who} scattered {s}'s bones ({cost} essence); resurrection rites fell back {scatter_devotion} devotion."

### 5.5 Death engine per epoch (`deathEngine(epoch, note)`; runs inside the world simulation, step "2f'")

```
for each dead son s with state D:
  for each faithful community t of D (errors swallowed — a community that cannot pay skips):
     if chance(blood_sacrifice_chance) and t.type ∈ {halk, yerlesim, tarikat}: rite(t, s, 'kan')
     elif chance(rite_chance): rite(t, s, (any of wealth/prosperity/craft ≥ wealth_cost) ? 'servet' : 'dua')
  if sibling_scheme_per_epoch ≤ 0: continue
  for each other active son k:
     rel = relationship(k, s)
     if rel ≥ sibling_auto_relation and chance(sibling_auto_chance):
        budget = k.essence * sibling_auto_essence_share/100
        kind = first of ['inis', 'ayin', ('pazarlik' if any awake foreign god)] whose cost ≤ budget
        if kind: siblingScheme(k, s, kind)
     elif rel ≤ -scatter_auto_relation and k.essence ≥ scatter_cost and D.devotion > 0 and chance(scatter_auto_chance):
        scatterBones(k, s)
if foreign_strike_chance > 0: for each awake foreign god y (by id):
   if chance(foreign_strike_chance):
      target = the canon mortal in y's world not worshipping y with the highest charisma
      if target: attemptKill(target, {killer: y, killerType:'y', how: "the wrath of the old god of the world {worldName}"})
```
Note: the per-epoch caps `kill_per_epoch`, `rite_per_epoch`, `sibling_scheme_per_epoch` are enforced by the tools (tools.js), except `sibling_scheme_per_epoch ≤ 0` which also disables the spontaneous schemes here.

### 5.6 Aeron's hand (`aeronKillsSon(s, epoch, {reason, godDeath})`)
```
corpse = godDeath(s, epoch, reason or "killed by {T}'s hand")
for each other non-dead son k: loyalty = clamp((loyalty ?? 50) + son_kill_loyalty); if relationship(k,s) > 0: anger += son_kill_anger; save
return corpse
```
Costs are charged by the epoch.js wrappers (§12): `god_kill_mortal` for taking a mortal's life (certain), `god_kill_son` for killing a son.

### 5.7 Tunables — domain `DEATH` (old `OLUM`), group "Death and resurrection" for all rows

| Key (old) | Default | Min | Max | Label |
|---|---|---|---|---|
| kill_base (can_al_taban) | 25 | 0 | 10000 | Base essence cost for a son to take a mortal's life |
| kill_per_power (can_al_guc) | 6 | 0 | 1000 | Essence added per victim power level |
| kill_importance_divisor (can_al_onem_bolen) | 2 | 1 | 1000 | Victim importance / this is added to the cost |
| kill_important (can_al_onemli) | 20 | 0 | 10000 | Extra cost for an important mortal (ruler, hero, chosen, titled) |
| kill_per_epoch (can_al_tur) | 1 | 0 | 20 | Max life-taking attempts per son per epoch (0 disables the tool) |
| kill_success (can_al_basari) | 65 | 0 | 100 | Base success chance (%) |
| kill_might_divisor (can_al_kudret_bolen) | 5 | 1 | 1000 | Son's might / this is added to success |
| kill_importance_resist (can_al_onem_direnc) | 4 | 1 | 1000 | Victim importance / this is subtracted from success |
| kill_patron_resist (can_al_hami_direnc) | 25 | 0 | 100 | Subtracted (%) if another son protects the victim (patron) |
| kill_creator_resist (can_al_yaratici_direnc) | 35 | 0 | 100 | Subtracted (%) if the victim worships the creator directly |
| kill_protected (can_al_korunmus) | 40 | 0 | 100 | Subtracted (%) if the victim is protected or chosen |
| kill_item_protection (can_al_esya_koruma) | 50 | 0 | 100 | An item with protection ≥ this may draw death's breath onto itself (narrated) |
| kill_min (can_al_en_az) | 5 | 0 | 100 | Minimum success chance (%) |
| kill_max (can_al_en_cok) | 95 | 0 | 100 | Maximum success chance (%) |
| kill_refund (can_al_iade) | 0 | 0 | 100 | Share (%) of essence returned on a failed attempt |
| kill_relation (can_al_iliski) | 15 | 0 | 100 | Relationship loss of the killing son with the victim's patron and creator |
| kill_charisma (can_al_karizma) | 10 | 0 | 100 | Charisma gain of a mortal who survives |
| kill_legend_power (can_al_efsane_guc) | 3 | 1 | 12 | Power level of the return-from-death legend |
| foreign_strike_chance (yabanci_carpma_sans) | 4 | 0 | 100 | Per-epoch chance (%) an awake foreign god strikes a named mortal of its world who does not worship it |
| god_kill_mortal (tanri_can_al) | 15 | 0 | 10000 | Aeron's cost to take a mortal's life (divine essence) |
| god_kill_son (tanri_ogul_oldur) | 100 | 0 | 100000 | Aeron's cost to kill a son |
| son_kill_loyalty (ogul_oldur_sadakat) | 10 | 0 | 100 | Fear-driven loyalty other sons gain when Aeron kills a son |
| son_kill_anger (ogul_oldur_ofke) | 15 | 0 | 100 | Anger of siblings friendly with the killed son |
| resurrection_min_epochs (dirilis_en_az_cag) | 3 | 0 | 1000 | A dead son can resurrect spontaneously at the earliest this many epochs later (except by Aeron's hand) |
| rite_chance (ayin_sans) | 20 | 0 | 100 | Per-epoch chance (%) a faithful community holds a spontaneous resurrection rite |
| rite_devotion (ayin_adanmislik) | 6 | 0 | 1000 | Contribution of a spontaneous rite (devotion) — DECLARED BUT UNUSED (spontaneous rites use prayer/wealth values), see §14 |
| rite_cost (ayin_refah) | 5 | 0 | 100 | Rite's cost to the community (prosperity or wealth) — DECLARED BUT UNUSED, see §14 |
| pilgrimage_mult (hac_carpan) | 200 | 100 | 1000 | Contribution multiplier (%) if the rite is held in the region of the god's bones |
| blood_sacrifice_chance (kurban_sans) | 5 | 0 | 100 | Per-epoch chance (%) a faithful community gives a blood sacrifice |
| blood_population (kurban_nufus) | 3 | 0 | 100 | Population lost in a blood sacrifice (%) |
| blood_devotion (kurban_adanmislik) | 20 | 0 | 1000 | Contribution of a blood sacrifice |
| life_sacrifice_devotion (can_kurbani_adanmislik) | 35 | 0 | 1000 | Contribution of a named mortal sacrificing themself (or being sacrificed by their people) |
| wealth_devotion (servet_adanmislik) | 10 | 0 | 1000 | Contribution of a wealth offering |
| wealth_cost (servet_bedel) | 15 | 0 | 100 | Cost of a wealth offering (prosperity or wealth) |
| prayer_devotion (dua_adanmislik) | 4 | 0 | 1000 | Contribution of a prayer |
| rite_per_epoch (ayin_tur) | 1 | 0 | 20 | `dirilis_ayini`: max rites per mortal per epoch (0 disables the tool) |
| sibling_rite_cost (kardes_ayin_bedel) | 45 | 0 | 10000 | Sibling's resurrection rite: cost (essence) |
| sibling_rite_devotion (kardes_ayin_adanmislik) | 25 | 0 | 1000 | Sibling's resurrection rite: contribution |
| sibling_descent_cost (kardes_inis_bedel) | 70 | 0 | 10000 | Descent to the underworld: cost (essence) |
| sibling_descent_devotion (kardes_inis_adanmislik) | 50 | 0 | 1000 | Descent to the underworld: contribution |
| sibling_descent_success (kardes_inis_basari) | 60 | 0 | 100 | Success chance (%) of the descent; on failure the sibling falls asleep |
| sibling_descent_sleep (kardes_inis_uyku) | 2 | 1 | 100 | Sleep duration (epochs) of a sibling lost in the underworld |
| sibling_bargain_cost (kardes_pazarlik_bedel) | 25 | 0 | 10000 | Bargain with a foreign god: cost (essence); also one of the dead son's faithful communities passes to the foreign god |
| sibling_bargain_devotion (kardes_pazarlik_adanmislik) | 40 | 0 | 1000 | Bargain with a foreign god: contribution |
| sibling_scheme_per_epoch (kardes_tur) | 1 | 0 | 20 | Max resurrection schemes or bone scatterings per son per epoch (0 disables the tools) |
| sibling_auto_relation (kardes_oto_iliski) | 40 | -100 | 100 | Minimum relationship with the dead sibling for a spontaneous scheme |
| sibling_auto_chance (kardes_oto_sans) | 25 | 0 | 100 | Per-epoch chance (%) a close sibling with enough essence schemes |
| sibling_auto_essence_share (kardes_oto_oz_pay) | 60 | 0 | 100 | In a spontaneous scheme the sibling spends at most this share (%) of essence |
| scatter_cost (dagit_bedel) | 30 | 0 | 10000 | Cost (essence) of scattering the bones |
| scatter_devotion (dagit_adanmislik) | 35 | 0 | 1000 | Devotion removed by scattering the bones |
| scatter_auto_relation (dagit_oto_iliski) | 40 | 0 | 100 | Spontaneous scattering requires relationship below minus this |
| scatter_auto_chance (dagit_oto_sans) | 15 | 0 | 100 | Per-epoch chance (%) a hostile sibling scatters the bones |
| new_order_disciples (yeni_tarikat_murit) | 80 | 1 | 1000000 | Disciples of the new resurrection order born when a rite is held for a dead god without an order |

### 5.8 Cross-references
Calls: `sim.olumluOlur` (mortal death path: heirs, inheritance, soul descent, killer bond), `sim.onemliOlumlu`, `arsiv.onemler` (importance index), `olumluler.ustBolge` (top region), `derin.kayitAc/etiketEkle/kanonlar`, `world.hami/iliski/iliskiDegistir/bagVar/addBag/addKronik`, rule domain `DERIN_YASAM`. Called by: son tools (`can_al`, `kardesini_dirilt`, `kemikleri_dagit`), mortal tools (`dirilis_ayini`), `tanriguc.js`, epoch.js (`olumluCanAl`, `ogluOldur`), `oyuncu.ayinBuyur`, `firsatlar.js`, server (UI prices), `sim.js` (`olumMotoru`).

---

## 6. Strange resources and cosmic economy (`ekonomi.js`)

### 6.1 Resource mechanics (tags `mekanik:<kind>` on `kaynak` entities)

Mechanic kinds: `bozunur` decays, `sabit` fixed amount, `bagimlilik` addictive, `bilincli` sentient, `kutsal:<sonId>` sacred to a son, `tukenme_bedeli` depletion curse. Owners = canon sources of active bonds `x -sahip(owns)-> resource`.

`resourceMechanics(epoch, note)` — for each canon resource with ≥1 mechanic:
1. **Decays**: abundance(bolluk) −= `decay`.
2. **Fixed**: abundance −= `fixed_loss` (cancels the general regeneration done elsewhere).
3. **Addictive**: for each owner o: skip if o has tag `arındı:{resId}:{epoch}` (cleansed) with `epoch − tagEpoch < addiction_immunity`; skip if abundance < `withdrawal_abundance`; if the oldest active ownership bond's epoch is ≥ `addiction_epochs` ago and o lacks `bağımlı:{resId}` (addicted) → add it; note "{o} can no longer do without {res}."
4. **Sentient**: if owners and `chance(sentient_chance)`: o = random owner; demand = random of DEMANDS. If (o.prosperity ?? o.wealth ?? `sentient_default`) ≥ `sentient_rich` and `chance(sentient_accept)`: prosperity and wealth −= `sentient_cost`; note "{res} demanded {demand} from {o}; {o} paid the price." Else: close o's ownership; new owner = random canon community in the same world other than o (if any) gets `sahip` bond ("the resource chose it"); note "{res} demanded {demand} from {o}, and when it did not get it, abandoned them{; now it chooses {new}}."
   DEMANDS (full): "an epoch of silence", "the eyes of the oldest seer", "the first names of the newborns", "a song, every night", "a settlement of their enemy", "the entire harvest of a year".
5. **Sacred** `kutsal:<sid>`: s = that son; for each owner whose patron is not s (stop if s missing/dead): s.anger += `sacred_anger`; if `chance(econ_event_curse)` and owner not cursed: tag `lanetli`, bond s -lanetledi-> owner ("for the sacred {res}"); note "{s} cursed {o} for digging the sacred {res}." (son id attached).
6. **Depletion curse**: if abundance ≤ 0 and not tagged `tükendi`(depleted): tag it; its location (if any) gets `lanetli`; doomsday clock = min(threshold, clock + `depletion_doomsday`); note "The last drop of {res} was drawn; {place was cursed and} the doomsday clock advanced."

**Withdrawal**: for each canon entity with tags `bağımlı:<id>`: has = resource canon, abundance ≥ `withdrawal_abundance`, and (entity owns it or trades (`ticaret` bond) with an owner). If not: prosperity/defense/strength/faith −= `withdrawal_loss`; population = clamp(pop * withdrawal_population/100, SINIR.nufus_taban, SINIR.nufus_tavan); then `chance(econ_event_recover)`: remove the addiction tag and any old `arındı:{id}:*` tags, add `arındı:{id}:{epoch}`, note "{v} survived the withdrawal from {res}; the addiction was broken." else note "{v} suffers withdrawal from {res}: cities silent, eyes clouded."

### 6.2 Cosmic travel resource

`world.kozmik_kaynak` JSON `{ad name, aciklama description, kural rule, yan_etki side effect}` (set by the player, §11). Deposits: canon `kaynak` tagged `kozmik kaynak` (+ `mekanik:bagimlilik`, `mekanik:sabit`).

`spendCosmicResource(v, amount=fold_cost)` (called by travel when folding space): deposits with abundance ≥ amount; access if v owns it, or v is an owner, or v trades with an owner. None → null. Else abundance −= amount; counter tag `katlama:{n}` incremented; at `n ≥ fold_addiction` and not yet → tag `bağımlı:{depositId}`. Returns the deposit.

`cosmicEconomy(epoch, note)` — only if ≥ 2 worlds:
1. `spreadDeposits`:
   - For each ownerless deposit: candidates = canon communities in its world; prefer those in the same top region; owner = largest (population or disciples); bond `sahip` ("claimed the cosmic resource"); note "{owner} claimed {deposit}; the key to travel between worlds is now in their hands."
   - If a cosmic resource is defined: for each non-forgotten world without a deposit but with a canon people/settlement: `chance(deposit_chance)` → random region → create deposit {subtype 'cosmic travel resource', name "{res} Deposit ({region})", power `deposit_power_level`, location region, stats {abundance: deposit_abundance + d(deposit_abundance_die), value: deposit_value, might: deposit_might}, tags as above, description "[World engine] A vein of {res} appeared in {world}, in the soil of {region}. {rule}"}; note "A {res} deposit appeared in {world} ({region})."
2. **Monopoly**: if all deposits share exactly one owner t: tag `kozmik tekel`(cosmic monopoly) if missing + note "{t} seized all the cosmos's travel resource: now it decides who travels between worlds."; every epoch: wealth, influence += `monopoly_gain`; prosperity via `addProsperity(stats, monopoly_gain)` (sim.refahEkle). Otherwise remove the tag from any holder + note "{t}'s cosmic monopoly was broken."
3. `routeCount` = currently passable routes (seyahat.rotalar); `traffic` = journeys started in the last `traffic_epochs` epochs. Open regions = canon regions not in forgotten worlds.
4. **Wandering market** (hizip tagged `gezgin pazar`): if count < `market_max` and routeCount ≥ 1 and `chance(market_chance)`: random open region → create faction {subtype 'wandering market', name "Wandering Market" or "Wandering Market {n+1}", power `market_power_level`, stats {strength: market_strength, wealth: market_wealth, influence: market_influence}, description "[World engine] A market carried from ship to ship between worlds, pitched under a different sky each epoch. Everything is for sale; some things only there."}; note "A wandering market was born on the routes between worlds."
   For each existing market: neighbour worlds via open known routes from its world; if regions there and `chance(market_move_chance)`: move to a random such region (`location_id`), `moveLocationBonds` (close old `icinde` bonds, add new; close `ticaret` bonds with entities of the old world); note "{market} packed up and moved to the world {world}, to {region}." Then for up to `market_reach` canon peoples/settlements in its (new) world: prosperity += `market_prosperity`; if no trade bond and `chance(market_trade_chance)`: add `ticaret` bond ("wandering market").
5. **Void pirates** (hizip tagged `boşluk korsanı`): if count < `pirate_max` and traffic ≥ `pirate_traffic` and `chance(pirate_chance)`: region = most dangerous open region → create {subtype 'void pirates', name "Void Pirates"(+n), power `pirate_power_level`, stats {strength: pirate_strength + d(pirate_strength_die), wealth, influence}, description "[World engine] As the routes between worlds grew crowded, pirates appeared to ambush ships."}; note.
   Pressure once per epoch: if any pirates: routes with method ∈ {yelken sail, sapan slingshot, binek mount} active: danger = min(pirate_danger_cap, danger + pirate_danger). Else if `pirate_danger_decay > 0`: per method, floor = clamp(method.danger + TRAVEL.route_danger_die − TRAVEL.route_danger_shift, TRAVEL.route_danger_floor, TRAVEL.route_danger_cap); routes with danger > floor: danger = max(floor, danger − decay).

`repairContainment()` (old `icindeOnar`, idempotent data repair at startup): close active `icinde` bonds to location-type targets (bolge, yer, yerlesim, halk, hizip, tarikat) whose source has a `location_id` that differs from the bond target, except description 'ruh kaplama' (soul vessel); close wandering markets' trade bonds with entities of other worlds. Returns `{icinde, pazar_ticaret}` counts.

### 6.3 Tunables — domain `ECONOMY` (old `EKONOMI`)

| Key (old) | Default | Min | Max | Group | Label |
|---|---|---|---|---|---|
| depletion_doomsday (tukenme_kiyamet) | 6 | 0 | 100 | Doomsday | Doomsday contribution of a depleted cursed resource |
| deposit_chance (yatak_sans) | 6 | 0 | 100 | Economy | A people finds a cosmic resource deposit (% per epoch) |
| sentient_chance (bilincli_kaynak_sans) | 35 | 0 | 100 | Economy | A sentient resource chooses (demands of) its owner (%) |
| sentient_accept (bilincli_kaynak_kabul) | 60 | 0 | 100 | Economy | A rich owner keeps the resource (%) |
| econ_event_curse (ekonomi_olay1) | 30 | 0 | 100 | Economy | The resource's god curses a foreign owner (%) |
| econ_event_recover (ekonomi_olay2) | 30 | 0 | 100 | Economy | One in withdrawal breaks the addiction (%) |
| market_chance (pazar_sans) | 25 | 0 | 100 | Economy | A cosmic market is founded (%) |
| market_move_chance (pazar_goc_sans) | 60 | 0 | 100 | Economy | The market moves to another region (%) |
| market_trade_chance (pazar_ticaret_sans) | 20 | 0 | 100 | Economy | The market forms new trade bonds (%) |
| pirate_chance (korsan_sans) | 30 | 0 | 100 | Economy | Pirates appear on a busy route (%) |
| decay (bozunma) | 8 | 0 | 100 | Economy | Per-epoch abundance loss of a decaying resource |
| fixed_loss (sabit_kayip) | 4 | 0 | 100 | Economy | Per-epoch regeneration taken back from a fixed-amount resource |
| addiction_epochs (bagimlilik_cag) | 2 | 0 | 100 | Economy | Epochs of ownership to become addicted |
| addiction_immunity (bagimlilik_bagisiklik) | 6 | 0 | 1000 | Economy | Epochs a recovered community does not become addicted again to the same resource |
| sentient_rich (bilincli_zengin) | 45 | 0 | 100 | Economy | Prosperity of an owner who can satisfy the sentient resource's demand |
| sentient_default (bilincli_varsayilan) | 40 | 0 | 100 | Economy | Assumed prosperity of an owner with unknown prosperity and wealth |
| sentient_cost (bilincli_bedel) | 8 | 0 | 100 | Economy | Prosperity and wealth cost of the sentient resource's demand |
| sacred_anger (kutsal_ofke) | 5 | 0 | 100 | Economy | God's anger gain when a foreigner digs a sacred resource |
| withdrawal_abundance (yoksunluk_bolluk) | 10 | 0 | 100 | Economy | Minimum resource abundance an addict can make do with |
| withdrawal_loss (yoksunluk_kayip) | 8 | 0 | 100 | Economy | Prosperity, defense, strength and faith loss in withdrawal |
| withdrawal_population (yoksunluk_nufus) | 95 | 0 | 100 | Economy | Population share kept in withdrawal (%) |
| fold_cost (katlama_bedel) | 12 | 0 | 100 | Cosmos and travel | Cosmic resource abundance spent by folding space |
| fold_addiction (katlama_bagimlilik) | 2 | 1 | 100 | Cosmos and travel | Addiction to the resource after this many folds |
| monopoly_gain (tekel_kazanc) | 3 | 0 | 100 | Economy | Cosmic monopoly's per-epoch wealth, prosperity and influence gain |
| traffic_epochs (trafik_cag) | 3 | 0 | 100 | Economy | Recent epochs in which route traffic is counted |
| market_power_level (pazar_guc_seviye) | 4 | 1 | 12 | Economy | Wandering market's power level |
| market_strength (pazar_guc) | 20 | 0 | 100 | Economy | Wandering market's strength |
| market_wealth (pazar_servet) | 70 | 0 | 100 | Economy | Wandering market's wealth |
| market_influence (pazar_nufuz) | 55 | 0 | 100 | Economy | Wandering market's influence |
| market_reach (pazar_etki_sayi) | 6 | 0 | 1000 | Economy | Max communities the wandering market enlivens |
| market_prosperity (pazar_refah) | 2 | 0 | 100 | Economy | Prosperity contribution to communities in the market's world |
| pirate_traffic (korsan_trafik) | 2 | 0 | 1000 | Economy | Minimum recent journeys for pirates to appear |
| pirate_power_level (korsan_guc_seviye) | 4 | 1 | 12 | Economy | Void pirates' power level |
| pirate_strength (korsan_guc) | 55 | 0 | 100 | Economy | Void pirates' base strength |
| pirate_strength_die (korsan_guc_zar) | 25 | 1 | 100 | Economy | Void pirates' strength die |
| pirate_wealth (korsan_servet) | 40 | 0 | 100 | Economy | Void pirates' wealth |
| pirate_influence (korsan_nufuz) | 30 | 0 | 100 | Economy | Void pirates' influence |
| pirate_danger (korsan_tehlike) | 2 | 0 | 100 | Cosmos and travel | Danger pirates add to routes per epoch |
| pirate_danger_cap (korsan_tehlike_tavan) | 95 | 0 | 100 | Cosmos and travel | Highest route danger pirates can cause |
| market_max (pazar_en_cok) | 1 | 0 | 20 | Economy | Max wandering markets at once (0 disables) |
| pirate_max (korsan_en_cok) | 1 | 0 | 20 | Economy | Max void pirate communities at once (0 disables) |
| pirate_danger_decay (korsan_tehlike_azalma) | 1 | 0 | 100 | Cosmos and travel | Without pirates, per-epoch danger decrease of pirate routes (sail, slingshot, mount); never below the highest danger a new route of that method can have |
| deposit_power_level (yatak_guc_seviye) | 7 | 1 | 12 | Economy | Power level of a new cosmic deposit |
| deposit_abundance (yatak_bolluk) | 40 | 0 | 100 | Economy | Base abundance of a new cosmic deposit |
| deposit_abundance_die (yatak_bolluk_zar) | 30 | 1 | 100 | Economy | Abundance die of a new cosmic deposit |
| deposit_value (yatak_deger) | 90 | 0 | 100 | Economy | Value of a cosmic deposit |
| deposit_might (yatak_kudret) | 80 | 0 | 100 | Economy | Might of a cosmic deposit |

### 6.4 Cross-references
Calls `sim.refahEkle`, `derin.kayitAc/etiketEkle/etiketSil/kanonlar/TOPLULUK`, `seyahat.rotalar/SEYAHAT`, `rules.SEYAHAT_YONTEMLERI/DENGE/SINIR`, `world.*`. Called by `sim.js` (`kaynakMekanikleri`, `kozmikEkonomi`, step 2c), `seyahat.js` (`kozmikKaynaktanHarca`), `onarim.js` (`icindeOnar`).

---

## 7. Council of Gods, chat with a son, dreams, translation (`konsey.js`)

Every LLM call here is a single structured call (`llm.structured`) using the model configured for role `kader` (Fate); effort `EFFORT.kader` unless the model is `haiku`. Old code prompts are Turkish and say "write in Turkish" — the new app is English-only: replace with "write in English". All model text was passed through `ekDuzelt` (Turkish suffix-harmony fixer) — LANGUAGE-SPECIFIC: drop.

### 7.1 Persona line (`persona(son)`) used by council and chat
`son#{id} {name}, {title} ({rarity}; {domain1}/{domain2}){ — REBEL AGAINST HIS FATHER}. Temperament: {temperament[:persona_temperament]} Style: {style[:persona_style]} Obsession: {obsession[:persona_obsession]} Passion: loyalty {l}, ambition {a}, anger {g}. Plan: {plan[:persona_plan] or 'none'}`
(`short(s, n)` truncates with "…".)

### 7.2 Agenda proposal (`proposeAgenda()`), first match
1. doomsday ≥ threshold × `agenda_doomsday`% → "Doomsday clock {c}/{t}: how will the end of the world be prevented, and who will pay the price?"
2. a rebel son exists → "{rebel}'s rebellion against the father: is the council with the rebel or against him?"
3. a dead son exists → "Dead brother {name}: shall he be resurrected, or his bones divided?"
4. an ongoing war event (`olay`/`savaş` tagged `suruyor`, highest power) → "{war}: will the gods take sides in the mortals' war?"
5. open threads → "Unresolved story: {first thread text, if longer than agenda_text cut at last space before agenda_cut + '…'}"
6. else "The course of the world: which brother has grown too large, which should be reined in?"

### 7.3 Convening (`convene({topic, publish, caller='tanri'|'kader', ask})`)
Triggered by (a) the player (`POST /api/konsey`, epoch.js `konsey(konu)`: under lock 'konsey', `spend(DENGE.konsey=20)`, refund on any error) and (b) automatically by the epoch runner every `world.konsey_sikligi` epochs (`cag % frequency == 0`, default column value 4, rule `frequency_default`; 0 = never; attempted once per epoch, caller 'kader', free).

```
members = sons with status active or asleep, first `members_max`
if len(members) < min_members: throw "The council needs at least {min_members} sons."
godAsked = topic.trim() non-empty; topic = godAsked ? topic : proposeAgenda()
relations = for each member pair: d = relationship(a,b); include if |d| ≥ relation_threshold or covenant(a,b):
            "{A}–{B}: {relationLabel(d)} ({d}){, covenanted}"
absent = non-dead sons not among members
publish({kind:'kader_adim', text:"The Council of Gods is convening: \"{topic}\""})
r = LLM(schema, system, prompt, timeout = timeout_s*1000)
```

**System prompt (translated):**
"You are a narrator recounting the Council of Gods of the world {worldName}, making each god speak in their own voice. You write in English. Each son speaks faithfully to his personality, passions, plan and relationships with his brothers; let there be disagreement, bargaining and grudges. Their father {creatorName} watches the council."

**User prompt (translated):**
```
{worldHeader(w)}

AGENDA{ (in their father's own words; do not quote it verbatim in the minutes and agenda field, summarize in the third person)}: {topic}

ATTENDANCE: {N in words} sons at the council{; absent: {names}}.

COUNCIL MEMBERS (each refers only to places of the world he is in as "here"):
{persona(s)}{ Current world: {worldName}.}   ← one line per member; world suffix only in multi-world cosmos

RELATIONSHIPS AMONG THEM:
{relation lines or "(nothing notable)"}

Let every son speak at least once; then put a single concrete motion to a vote. Votes must fit personalities and relationships. Alliances may be formed or broken.
```
(Number words: Turkish list "hiç, bir, iki … on beş" — LANGUAGE-SPECIFIC; use English number words; the attendance count is stated explicitly because the model used to invent "nine sons gathered".)

**Output schema:**
```
{
  speeches:  array[minItems=len(members), maxItems=2*len(members)] of {son_id: int enum memberIds, words: string "1–3 sentences in his own style; may answer each other"},
  motion:    string "The single concrete motion the council votes on",
  votes:     array of {son_id: enum, vote: enum['yes','no','abstain'], reason: string},
  alliances: array[maxItems=alliance_max] of {a: enum, b: enum, kind: enum['covenant','break'], reason: string},
  decision:  enum['none','against_doomsday','joint_blessing','censure_rebel','call_for_peace']  "Effect on the world if the motion passes",
  minutes:   string "3–5 sentence epic summary of the council as a mortal seer saw it in a dream; {N} sons attended (write no other number)",
  agenda:    string "One-sentence third-person summary of the agenda for the chronicle (do not quote the god's question verbatim in first person, e.g. \"the fate of Haevaron\")"
}  all required
```
(old field/enum names: konusmalar/ogul_id/soz, onerge, oylar/oy evet|hayir|cekimser/gerekce, ittifaklar/tur ahit|kopus/neden, karar yok|kiyamete_karsi|ortak_kutsama|asiyi_kinama|barisa_cagri, tutanak, gundem)

**Post-processing (single transaction — if it fails nothing is written and the player's cost is refunded safely):**
```
votes = dedupe by son_id (first wins), only members
yes, no = counts; passed = yes > no
for each pair of non-abstaining votes: relationship(a,b) += same ? vote_closeness : -vote_closeness
for each alliance (a != b, both members), first alliance_max:
   covenant and no covenant yet: add bond o→o 'muttefik'(ally) "Council covenant: {reason}"; relationship += covenant; note "{A} and {B} made a covenant in the council"
   break: deactivate 'muttefik' bonds both directions; relationship -= break_cost; note "{A} and {B} broke apart in the council"
if passed:
   against_doomsday: clock = max(0, clock - doomsday_pushback); note "the doomsday clock was pushed back {n}"
   joint_blessing: each member (reloaded fresh): existence = clamp(existence + blessing, 0, 100); note "all brothers' existence grew stronger"
   censure_rebel: each member that is rebel: fame(un) = max(0, fame - censure_fame); note "{s}'s fame was shaken by the censure"
   call_for_peace: among active entity 'dusman' bonds whose both ends are canon, score = (member worshipped by a ? 2 : 0) + (by b ? 2 : 0) + log10(pop(a)+pop(b)) (pop = population or disciples or 100); close the top one (both directions); note "by the gods' command {A} and {B} made peace"
minutes = {topic, caller, speeches (with names), motion, votes (with names), passed, decision, notes, minutes}
INSERT konseyler(cag, konu, tutanak JSON, kabul)
chronicleAgenda = godAsked ? (r.agenda trimmed of final punctuation or "upon {T}'s question") : topic
chronicle(cag, null, 'konsey', "The Council of Gods convened ({agenda}). Motion: \"{motion}\" — {passed|rejected} ({yes} yes, {no} no).{ notes joined '; '.} {minutes}")
publish({kind:'konsey', id, topic, passed, motion})  (errors ignored)
return {id, ...minutes}
```

### 7.4 Chat with a son (`chatWithSon(sonId, text)`) — player action, free, not ledgered
```
s must exist ("No son"); dead → "{s} is dead; your voice does not reach their bones."
text = trim[:chat_text]; empty → "Say something."
history = last chat_history messages with intent 'sohbet' between t and s (chronological)
r = LLM(timeout chat_timeout_s)
```
**System (translated):** "You are {son}, {title}; the son of the creator god {T} in the world {worldName}.{ You are now in the world {worldOfSon}; your creations in other worlds are there — do not speak of them as if they were where you are.} You are talking with your father. Speak in English, fully in character, in your own style; never say you are an AI.\n{persona}\nAppearance: {appearance[:chat_appearance]}\nFear: {fear[:chat_secret]} Secret: {secret[:chat_secret]} (do not reveal your secret easily)"
**Prompt (translated):** "YOUR MEMORY:\n{memory(s)[:chat_memory]}\n\nTHE CONVERSATION SO FAR:\n{FATHER: … / YOU: … lines or '(you are speaking for the first time)'}\n\nYOUR FATHER NOW SAYS: \"{text}\""
**Schema:** `{answer: string "1–4 sentences, fully in character, in his own style", attitude: enum[loyal, distant, rebellious, frightened, grateful, mocking] (old sadik, mesafeli, asi, korkmus, minnettar, alayci), loyalty_change: integer in [−chat_loyalty, +chat_loyalty] "How the father's words affected his loyalty"}`
After: reload son; loyalty = clamp(loyalty + clamp(change)); save; insert message t→o intent 'sohbet' (read=1); insert o→t intent 'sohbet' (read=1, answered=1) with the answer; return `{answer, attitude, loyalty, change}`.
`chatHistory(sonId)`: last `chat_list` 'sohbet' messages between them, chronological.

### 7.5 Dream to a mortal (`sendDream(entityId, text)`)
```
v canon else "This entity is not in the world."; type ∈ {halk, yerlesim, hizip, tarikat, olumlu, tur} else "Only a thinking community or mortal can see a dream."
text = trim[:dream_text]; length < dream_min → "The dream must have some content."
creator essence < DENGE.ruya → "A dream costs {n} essence."; else pay
insert message t→v intent 'ruya'; chronicle 'tanri' "{T} sent {v} a dream." [v.id]
```
`dreams(entityId, markRead=true)`: unread `ruya` messages to v; marks read (shown in the mortal agent's turn). `pendingDream(id)`: unread `ruya` or `tezahur` exists (mortal agent selection prioritizes such entities).

### 7.6 Translation into a world language (`translate(languageId, text)`) — free, not ledgered
```
lang = entity type 'dil' else "No such language."; text = trim[:translate_text]; empty → "Write something to translate."
dictionary = first translate_dictionary words (word, meaning, kind)
phon = dilmotoru.phonology(langId); syllables = first translate_syllables onset syllables + first translate_syllables coda syllables
```
**System (translated):** "You are the linguist of the world {worldName}. You stay faithful to the rules of the {lang} language: first use the words in the dictionary; derive missing words in the language's sound pattern and from existing roots. Explain in English."
**Prompt:** "LANGUAGE: {lang} ({subtype or 'language'}). {description}\nTHE WORLD'S NAMING RULE: {w.isim_kurali}\nCOMMON SYLLABLES: {syllables}\nDICTIONARY:\n{word = meaning (kind)} lines or '(empty)'\n\nTO TRANSLATE: \"{text}\""
**Schema:** `{translation: string, pronunciation: string "syllable by syllable in English letters" (old: Turkish letters), word_by_word: [{word, meaning}], new_words: [maxItems translate_new_words] {word, meaning, kind enum[noun, verb, adjective, suffix, title, place name, proper name, interjection, number], origin}, note: string "one-sentence grammar or culture note"}`
After: new words not already in the dictionary (case-insensitive) up to `translate_new_words` are added via `world.sozlukEkle(langId, words with example "\"{translation}\" ({text})", 't', null, cag)`.

### 7.7 Tunables — domain `COUNCIL` (old `KONSEY`)

| Key (old) | Default | Min | Max | Group | Label |
|---|---|---|---|---|---|
| members_max (uye) | 9 | 2 | 30 | Council | Max sons attending the council |
| min_members (en_az) | 2 | 2 | 30 | Council | Minimum sons for the council to convene |
| vote_closeness (oy_yakinlik) | 3 | 0 | 50 | Council | Closeness gained by those voting alike |
| covenant (ahit) | 12 | 0 | 100 | Council | Relationship bonus of a council covenant |
| break_cost (kopus) | 15 | 0 | 100 | Council | Relationship cost of a council break |
| doomsday_pushback (kiyamet_geri) | 10 | 0 | 100 | Council | Clock pushed back by an accepted anti-doomsday motion |
| blessing (kutsama) | 5 | 0 | 100 | Council | Existence added by a joint blessing |
| censure_fame (kinama_un) | 10 | 0 | 200 | Council | Fame cost of censuring the rebel |
| agenda_doomsday (gundem_kiyamet) | 50 | 0 | 100 | Council | Doomsday comes on the agenda at this % of the threshold |
| timeout_s (sure) | 240 | 30 | 3600 | Agents and model | Council timeout (s) |
| relation_threshold (iliski_esik) | 20 | 0 | 100 | Council | Minimum |strength| of a sibling relationship written into the council prompt |
| alliance_max (ittifak_tavan) | 3 | 0 | 20 | Council | Max alliances or breaks in one council |
| frequency_default (siklik_varsayilan) | 4 | 0 | 100 | Council | Every how many epochs a council convenes when the world has no setting |
| agenda_text (gundem_metin) | 260 | 20 | 5000 | Context budgets | Max length of an open story taken onto the agenda (chars) |
| agenda_cut (gundem_kes) | 250 | 10 | 5000 | Context budgets | A long story is cut at the last space before this char |
| persona_temperament (persona_mizac) | 160 | 0 | 5000 | Context budgets | Council and chat: son's temperament (chars) |
| persona_style (persona_uslup) | 120 | 0 | 5000 | Context budgets | Council and chat: son's style (chars) |
| persona_obsession (persona_takinti) | 100 | 0 | 5000 | Context budgets | Council and chat: son's obsession (chars) |
| persona_plan (persona_plan) | 160 | 0 | 5000 | Context budgets | Council and chat: son's plan (chars) |
| chat_appearance (sohbet_gorunus) | 200 | 0 | 5000 | Context budgets | Chat: son's appearance (chars) |
| chat_secret (sohbet_sir) | 120 | 0 | 5000 | Context budgets | Chat: son's fear and secret (chars each) |
| chat_memory (sohbet_hafiza) | 3500 | 200 | 100000 | Context budgets | Chat: son's memory (chars) |
| chat_history (sohbet_gecmis) | 10 | 0 | 200 | Context budgets | Chat: previous messages in the prompt |
| chat_list (sohbet_liste) | 40 | 1 | 1000 | Interface | Messages shown in chat history |
| chat_text (sohbet_metin) | 800 | 10 | 20000 | Council | Longest thing the god can say to his son (chars) |
| chat_loyalty (sohbet_sadakat) | 6 | 0 | 100 | Council | Max loyalty change from one chat (±) |
| chat_timeout_s (sohbet_sure) | 120 | 10 | 3600 | Agents and model | Chat timeout (s) |
| dream_text (ruya_metin) | 600 | 10 | 20000 | Council | Longest dream text sent to a mortal (chars) |
| dream_min (ruya_en_az) | 5 | 1 | 1000 | Council | Shortest dream text (chars) |
| translate_text (ceviri_metin) | 300 | 10 | 20000 | Language and names | Longest sentence to translate (chars) |
| translate_dictionary (ceviri_sozluk) | 250 | 0 | 10000 | Language and names | Dictionary words sent with the translation prompt |
| translate_syllables (ceviri_hece) | 12 | 0 | 200 | Language and names | Frequent onset and coda syllables sent (each) |
| translate_new_words (ceviri_yeni) | 6 | 0 | 100 | Language and names | Max new words one translation may add to the dictionary |
| translate_timeout_s (ceviri_sure) | 120 | 10 | 3600 | Agents and model | Translation timeout (s) |

### 7.8 Cross-references
Calls `llm.structured`, `world.getWorld/getSon/allSons/getVarlik/saveSon/addKronik/addBag/iliski/iliskiDegistir/iliskiEtiket/ahitVar/dunyaBasligi/hafiza/acikIplikler/modelFor/cokDunya/sozlukEkle`, `dilmotoru.fonoloji`, `db.tx`. Called by epoch.js (`konsey`, auto-council in the epoch runner), server (`ogulSohbet`, `sohbetGecmisi`, `tanriRuyasi`, `cevir`, `/api/konseyler`), mortal agent (`ruyalar`, `bekleyenRuya`).

---

## 8. Opportunities (`firsatlar.js`)

Opportunity lines are injected into every son-agent and mortal-agent turn so models do not waste tools and touch the world's tensions. They are LLM prompt text (bullet list, each line prefixed "- "). They mention tool names in snake_case; the new app's tool names will be English — keep the mechanism: **a line mentioning tools the agent does not have is filtered** (see 8.4).

### 8.1 Son opportunities (`sonOpportunities(son, tools=null)`)
Visible set `vs` = canon entities; in a multi-world cosmos restricted to entities with no world or in the son's active world. Lines in order (then tension lines are moved to the front, §8.4):

1. **Vitality.** `vitality = "The world has {p} peoples, {s} settlements, {m} named mortals, {sp} species, {o} organizations."` (o = orders + factions). If `p < regions + alive_people_surplus` or `m < alive_mortals` or `s < p` or `sp < alive_species`: "BREATHE LIFE: {vitality} This epoch your first living creation (halk_yarat, olumlu_yarat, yerlesim_kur, tur_yarat, tarikat/hizip) does NOT spend an action point; be sure to create something living.{ Regions where no one lives: #id name, … (≤ list_short; region with no people/settlement whose top region is it)}{ Named mortals (king, seer, artisan, hero, bandit) give the world a face. (if m < alive_mortals)}" Else: "{vitality} Your first living creation each epoch does not spend an action point."
2. **New world** (multi-world; each empty world ≠ son's, from bosdunya.bosDunyalar): "NEW WORLD: {name} ({type}) is completely empty; no people, settlement or named mortal{ (for {n} epochs)}. Its habitable regions: {#id name (fertility f) ×≤BOS.firsat_bolge}. Move to the world {name} (world#{id}) with dunyaya_yonel and create its first people: your first living creation spends no action; the son who creates the first people gains +{BOS.ilk_halk_oz} essence, +{BOS.ilk_halk_un} fame and becomes that world's only god."
3. **Narrow lands** (ufuk.toprakOlcusu(world).dar): "NARROW LANDS: in the world {name|'Your world'} {c} communities are squeezed into {r} regions ({ratio} per region){; most crowded: #id name (n), … ≤list_short}. Open a new region on the map (valley, plateau, island, coast) with bolge_yarat or a new place (forest, lake, cave, pass) with yer_yarat{: this epoch your first land creation spends no action (if KESIF.toprak_bedava>0)}{, you gain +{KESIF.toprak_oz} essence, +{KESIF.toprak_un} fame}; the squeezed mortals migrate there."
4. **Isolated world** (multi-world; no active known route touching son's world): "ISOLATED WORLD: there is no known open road from your world to other worlds{; but the cosmos has a hidden passage — if mortals learn sky-watching or gate science they will find it (bilgi_ilham_et)}. Create a gate, bridge or ship with arac_yarat (giving hedef_dunya_id): a road opens and mortals set out on expeditions."
5. **Stagnant cosmos** (`cag − max(world.created_epoch) ≥ KESIF.kozmos_durgun`): "STAGNANT COSMOS: no new world has been born since Epoch {e}. Bear a new world with dunya_dogur; the son who creates its first people is rewarded."
6. **Dead siblings** (each dead other son with state D; status = "devotion of those awaiting their return {D.devotion}/{DERIN_YASAM.dirilis_adanmislik}{, at the earliest in {k} epochs}"): if relationship ≤ −`DEATH.scatter_auto_relation`: "YOUR ENEMY IS DEAD: {k} died in Epoch {e} ({status}). With kemikleri_dagit ({scatter_cost} essence) you can delay their return; their order will become your enemy." else "DEAD SIBLING: {k} died in Epoch {e} ({status}). Help their return with kardesini_dirilt: rite {rite_cost} essence, descent to the underworld {descent_cost} essence (risky), bargain with a foreign god {bargain_cost} essence and one faithful community."
7. **Rival siblings** (active, relationship ≤ −`rival_relation`, most hostile first, ≤ list_short): "RIVAL SIBLINGS: son#{id} {name} (relationship {r}), …. Tell this feud: challenge them openly with meydan_oku, curse their creation or worshipper with lanetle, incite your worshippers against theirs with savas_kiskirt, steal their worshippers with ruya_gonder; or make a peace covenant with ahit_et."
8. **Rivals' famous mortals** (mortals whose patron ≠ son and relationship(son, patron) < −`enemy_sibling`, by charisma, ≤ list_narrow): "Your rivals' famous mortals (you can take their lives with can_al; very expensive and may fail): #id name (patron; {killCost} essence, %{killChance})…"
9. "Communities that worship no one (win them with mucize, bilgi_ver or ruya_gonder; or found a neighbouring people with halk_yarat): …" (thinking = community or mortal, no patron; ≤ list)
10. "Worshippers of your rivals (steal with ruya_gonder, lanetle or afet_gonder): #id name (patron) …" (patron ≠ son, relationship < −rival_relation)
11. "Your worshippers (mucize, secilmis_ilan_et, bilgi_ver, or give them a hero with olumlu_yarat): …"
12. "Ongoing hostilities (bless a side or make peace with mucize, fan the flames with savas_kiskirt, resolve with olay_baslat): #a A ↔ #b B; …" (active entity `dusman` bonds, newest first, both ends visible and canon, ≤ list_wide)
13. If knowledge exists and some own worshipper lacks some: "Knowledge you can teach your worshippers (with bilgi_ver): #id name (branch) …"; if none exists: "There is no knowledge (technology) in the world yet; you can inspire the first knowledge in mortals."
14. "Communities without a language (create one with dil_yarat; give the 'konusur' bond to that community): …" (peoples/factions/orders with no spoken language, ≤ list_short); if no languages: "There is no language in the world yet."
15. "Ownerless resources (milk with kaynak_sag or forge an item from it with esya_dov): …"
16. "Your rival siblings' creations (transform, curse, set something against them): …" (creator sibling with relationship < −enemy_sibling; last list_wide)
17. "Those who rose against you (creatures and mortals; punish, curse, send a disaster, or win back their hearts): …" (entity −dusman→ son)
18. "Those who defied or denied you (vengeance or forgiveness): …" (son −dusman|lanetledi→ entity)
19. "Godless communities (can be won with a miracle or dream; they gnaw at your father's power): …"
20. "Brothers who rebelled against your father (join them, make a covenant, or stand by your father): son#id name …"
21. If not rebel and loyalty < `loyalty_rebel`: "Your loyalty is low: if you wish you can openly rise against your father with isyan_et."
22. Each dead sibling: "Your dead sibling {o}{ (bones #corpse)}{; resurrection order #t name, devotion d/threshold (miracles increase devotion)}: you can bring them back, use their bones for your own purpose, or disband their order."
23. If existence (default 60) ≤ `fading`: "YOUR EXISTENCE IS {v}: you are about to fade. Win worshippers (miracle, dream, teach knowledge), create legends and works that tell of you, protect your anchor; otherwise you will die." Else if no worshippers: "No one worships you; a god without worshippers is forgotten in time. Win a community."
24. "Your worshippers' ongoing wars (bless their side, strengthen their army, send disaster on the enemy, or a miracle of peace): #id name; …" (war events tagged `taraf:{worshipperId}`, ≤ list_short)
25. "Your hungry worshippers (abundance miracle, teach knowledge: agriculture): …" (peoples/settlements with society food < `hungry_food`, default 50)
26. "The world's wonders (bless, curse, point at as a target): …" (tag `harika`, ≤ list_short)
27. Threads (not great expeditions; in multi-world only threads whose majority world is the son's or none), sorted by stagnation: stagnant ≥ `stale_epochs` → **unshift** "STORIES ABOUT TO BE FORGOTTEN ({stale}+ epochs nobody touched them; advance them or Fate will close them as \"forgotten\"): thread#id: {text[:90]} · …" ; long (progress or advancers ≥ `long_thread`) → "Long stories that should reach their climax (make a creation that brings it to its outcome by giving iplik_id; Fate closes it): thread#…"
28. "Prophecies awaiting fulfilment (fulfil with a creation or event, have them misread, or make them void; Fate watches): #id name (Epoch e{, yours}) …" (own first, then oldest, ≤ list_narrow)
29. "Open stories: thread#… (give iplik_id in creations)"
30. Last message epoch of this son; none or ≥ `silence_epochs` ago: "{You have never spoken to your brothers | You have not said a word to your brothers for {n} epochs}: kardese_seslen, ahit_et and babaya_dua do not spend actions; alliances and debts are made with them."

### 8.2 Player opportunities (`godOpportunities()`, GET /api/firsatlar, "What can you do this epoch" panel)
1. "{n} prayers await an answer: answering raises loyalty and faith." (unanswered messages to t)
2. "There are {n} communities that worship no one (e.g. {first list_narrow names}): a miracle or a dream binds them to you."
3. "Rebel sons: {names}. You can suppress the rebellion or forgive."
4. "Sons being forgotten: {name (existence)}. Blessing strengthens their existence." (existence ≤ `fading_son`)
5. "Doomsday clock {c}/{t}: miracles, faith and a council can push it back." (clock ≥ threshold × `doomsday_warning`%)
6. "Worlds without a god: {names}. Send a son or call a new one." (non-forgotten worlds with a canon people and no active son there)
7. "{n} stories are about to be forgotten; a revelation can revive them." (stagnation ≥ stale_epochs)
8. "You have {oz} essence: enough for a new world, a son or a star." (oz ≥ `rich_essence`)

### 8.3 Mortal opportunities (`mortalOpportunities(v)`) — `vs` = canon others; `near` = communities near v (olumluler.yakinMi)
1. "Those you can trade or ally with: …" (near without trade or enemy bond)
2. Enemies (near with `dusman` bond and — when both are communities — community relationship < 0): "Your enemies ({options}; or offer peace, produce weapons, seek allies): …" options = "open war with savas_ilan_et" (only if no ongoing war event with both as sides), "strike secretly with sabotaj" (faction, order, mortal only), "learn their secrets with casus_ag_kur".
3. Tense neighbours (communities only; no enemy bond; community relationship ≤ −`tense_neighbour`): "Your tense neighbours (relations are bad; watch them with casus_ag_kur{, weaken with sabotaj}, settle accounts with savas_ilan_et, or calm them with trade and gifts): #id name (rel) …"
4. "Knowledge you can learn from neighbours (ogren): #id tech (neighbour knows) …"
5. "Resources in your land (claim, then produce): …" (same top region, not owned)
6. "Dangerous creatures in your land (weapons, walls, war to hunt): …" (species danger ≥ `monster_danger`)
7. "You have no knowledge yet: develop or learn one." / "You have no language yet: dil_kur."
8. Communities: "Your blood feuds (revenge, war, or peace with blood money): …"; "Neighbours who love you (alliance or marriage is easily accepted): #id (rel) …" (rel ≥ `friendly_neighbour`, no ally/enemy bond); "You are at war: … Produce weapons, build walls, seek allies or offer peace."
9. Peoples/settlements: food < `granary_food`: "Your granary is emptying (food {f}, bread ×{price}): set up trade, learn agriculture, or found a settlement on fertile land."; worst class satisfaction < `discontent`: "Your people's {class} class is discontent (satisfaction {m}); they may rise up. Make a law, found a tradition, or address their troubles."
10. "Ruins in your land (kalinti_ara): …" (tags harabe/tanrı cesedi/boş mezar in same region, or dead entities tagged harabe)
11. For each dead son v worships: "Your god {name} died (Epoch e); the devotion of those awaiting their return is {d}/{threshold}. Offer prayer, a wealth offering, a blood sacrifice or a life sacrifice with dirilis_ayini{; a rite held at {corpse} is stronger}."
12. Discovery (communities/mortals, if `KESIF.arac_tur > 0`): with discovery pressure reasons: "Unknown lands are calling you ({reasons}): find a region not on the map or a new place nearby with toprak_kesfet{; your pioneers can settle there (yerles)}." else "Beyond the horizon there are lands no one has seen yet: with toprak_kesfet you can find a new region or a new place nearby."
13. Sky: if v has a route method: "The sky is open to you: search for the road to other worlds with rota_kesfet{ (worlds nobody knows the road to: …)}; rarely you sense a world nobody knows." else if unknown-road worlds: "There are worlds in the sky whose road you do not know (…): if you learn sky-watching, gate science or pathfinding (ogren, bilgi_gelistir) you can search for the road." If an open known route exists: "There is an open road to other worlds: organize an expedition with sefere_cik; you will find new lands in the world you reach."
14. Mortal with strength + agility ≥ `challenge_strength`: "You are strong enough to defy a god (tanriya_meydan_oku): son#id name …" (active sons in its world)
15. If patron cursed v or patron is rebel: "Your god {p} has become a burden; you can turn away from them with inkar_et."
16. No patron: "You have no god; you can worship: son#id name (domain1/domain2) …"

### 8.4 Filtering and ordering
- **Tension first** (if `tension_first`=1): lines matching /RIVAL|Rival|enemy|Enemy|war|War|rebel|rise|defied|blood feud|ENEMY|tense|Tense/ (TR `HASIM|düşman|savaş|isyan|ayaklan|kafa tut|Kan dava|gergin`) are moved before others (the context budget truncates the end of the list).
- **Tool filter** (son lines only, when the agent's tool list is supplied): find tool-like tokens (`snake_case` words with ≥1 underscore, plus the special single-word tools `mucize`, `lanetle`), ignoring field names ending in `_id`. If none → keep. If none of them are available → drop the line. Otherwise remove each unavailable tool together with its clause (preceding connector ", " / " or " / " and " / "; ", the name and the following phrase up to the next comma/semicolon/")"/" or "/sentence end) and tidy punctuation. (LANGUAGE-SPECIFIC connectors: "ya da"/"ve" → "or"/"and".) Better design: build lines from structured `{text, tools:[...]}` parts instead of regex surgery (§14).

### 8.5 Tunables — domain `OPPORTUNITY` (old `FIRSAT`), group "Opportunities" for all rows

| Key (old) | Default | Min | Max | Label |
|---|---|---|---|---|
| list (liste) | 5 | 1 | 50 | Max records listed in one opportunity line |
| stale_epochs (durgun_cag) | 4 | 1 | 100 | Epochs untouched before a story is "about to be forgotten" |
| long_thread (uzun_iplik) | 8 | 1 | 200 | Advances after which a story "should conclude" |
| silence_epochs (sessizlik_cag) | 3 | 1 | 100 | Epochs without talking to brothers before a reminder |
| rich_essence (zengin_oz) | 150 | 0 | 100000 | Essence for the creator's "great action" reminder |
| list_short (liste_kisa) | 4 | 1 | 50 | Max records in short lists |
| list_narrow (liste_dar) | 3 | 1 | 50 | Max records in the narrowest lists |
| list_wide (liste_genis) | 6 | 1 | 100 | Max records in wide lists |
| alive_people_surplus (canli_halk_fazla) | 2 | 0 | 50 | "Breathe life": if peoples do not exceed regions by this |
| alive_mortals (canli_olumlu) | 6 | 0 | 200 | "Breathe life": if named mortals are fewer than this |
| alive_species (canli_tur) | 4 | 0 | 200 | "Breathe life": if species are fewer than this |
| rival_relation (rakip_iliski) | 20 | 0 | 100 | Relationship with a sibling counted as rival: below minus this |
| enemy_sibling (hasim_kardes) | 25 | 0 | 100 | Relationship with a sibling whose creations are pointed out: below minus this |
| loyalty_rebel (sadakat_isyan) | 40 | 0 | 100 | Rebellion reminder if loyalty is below this |
| fading (sonmek_uzere) | 20 | 0 | 100 | "You are about to fade" at existence ≤ this |
| fading_son (solan_ogul) | 25 | 0 | 100 | To the god: sons with existence ≤ this are "being forgotten" |
| doomsday_warning (kiyamet_uyari) | 50 | 0 | 100 | Doomsday reminder to the god at this % of the threshold |
| hungry_food (ac_erzak) | 60 | 0 | 1000 | Worshippers count as hungry: food below this |
| granary_food (ambar_erzak) | 60 | 0 | 1000 | "Your granary is emptying" to a mortal: food below this |
| discontent (hosnutsuz) | 30 | 0 | 100 | A class counts as discontent: satisfaction below this |
| friendly_neighbour (dost_komsu) | 45 | -100 | 100 | Loving neighbour: community relationship ≥ this |
| monster_danger (canavar_tehlike) | 50 | 0 | 100 | Dangerous creature: danger ≥ this |
| tense_neighbour (gergin_komsu) | 20 | 0 | 100 | "Tense neighbour" to a mortal: community relationship below minus this (without an enmity bond) |
| tension_first (gerilim_once) | 1 | 0 | 1 | Tension lines (rivals, enmities, wars, rebellion) go to the top of the list (1 on, 0 off) |
| challenge_strength (meydan_guc) | 110 | 0 | 1000 | Suggest challenging a god: strength + agility ≥ this |

### 8.6 Cross-references
Calls world (`getVarlik, kanonlar, hami, iliski, allSons, bagVar, acikIplikler, konusulanDil, iplikDurumlari`), `mudahale.bildikleri/dalOf`, `olumluler.ustBolge/yakinMi/ogrenebilirMi`, `derin.toplumOf/tIliski`, `bosdunya.BOS/bosDunyalar`, `ufuk.KESIF/toprakOlcusu/kesifBaskisi/yolYontemi`, `olum.*`, rule domain `DERIN_YASAM`. Called by son agent turn builder (`ogulFirsatlari`), mortal agent turn builder (`olumluFirsatlari`), server `/api/firsatlar` (`tanriFirsatlari`).

---

## 9. The Book (`kitap.js`)

A single readable, printable HTML of the **entire** world record (browser → PDF). Every record is written exactly once and linked from everywhere by anchors `#v-{id}` (entity), `#o-{id}` (son), `#d-{id}` (world), `#y-{id}` (foreign god), `#ys-{id}` (star), `#aeron` (creator), `#cag-{n}` (epoch). Served at `GET /kitap` (full) and `GET /kitap?ogul=ID` / `?varlik=ID` (single entry page; links point to their own single pages). No world → full page "There is no world yet." / single page → null (404).

### 9.1 Section order (table of contents)
1. **Cover**: "Aerona" overline, world name, "{creator}{, title} and the book of his sons", "{n} epochs · world year {y} · {n} sons · {n} records{ · {n} worlds}", round cover image (world 1 image else creator image).
2. **Contents** with right-hand meta per entry.
3. **Cosmology** (`#kozmoloji`, overline "Beginning"): world cosmology (drop cap), tone, naming language, climate (legacy world climate: name, "{n} more epochs"), laws of nature (`yasa` entities, description ≤400 chars), "The seed of creation" box (`w.tohum`).
4. **The Creator** (`#aeron`): name, title, portrait, appearance, temperament; info row: mood label, passions, cult (links); epic (`tanri_destan`: title, verse, chapters with epoch ranges); depth (`tanri_derinlik` fields: through the ages, names, secrets, fears, prohibitions, gifts, what he truly wants, sayings, rumours, hidden truth); "Through the peoples' eyes" (`halk_inanc` rows with son id 0: "{people} calls him “{name}”: narrative (Misconception: …)"); "The creator's own note" box.
5. **Cosmos** (`#kozmos`): summary "{stars} stars · {worlds} worlds · {routes} roads · {foreign} foreign gods"; per star: name, type, description, then its **world tree** (planet → moons → moons of moons; each world written once; root = world without parent or with unknown parent; worlds without a known star after; leftovers last). World entry: name; meta (type name, star, "moon of X", discovery state if not known); round image; **map SVG** (§9.3) "{world}: the known world"; description; cosmology (if different); dialect; info row (time ×k, atmosphere, gravity, leak n/100); **Traveller's guide** box (dangers, peoples with population and god, resources with mechanic names, roads with method and duration). Foreign gods: image, name, title, meta (world · status · power · attitude toward the pantheon), description, stats, powers (effect names), personality and existence fields (secret and true name hidden), depth (history, worship, names, sayings, rumours). Roads list (A ↔ B: method, duration, danger, sealed/unknown, description, epoch). Journeys list.
6. **Pantheon** (`#panteon`): per son: portrait, name (+ † if dead), meta (title · rarity ★×stars · domains · level · born epoch · lineage · died epoch · world), personality fields (appearance, temperament, obsession, fear, style, secret, strengths, weakness), powers, existence (nature, state, manifestation, true name), stat row, passion row + fame + faith + "sees his father as {label}", plan, epic, people's beliefs, relations with brothers (sorted), bonds (excluding `icinde`), creations list.
7. **Epochs** (`#cag-{n}` for every epoch present in `caglar` or the chronicle): overline "{Roman numeral}. Book · Year {start}–{end}", title, summary, chronicler ("Chronicler: {name}, {who}"); up to 6 plates (images of entities born that epoch, by power); narrative (drop cap); per-world chapters (multi-world: `caglar_dunya`); stats row (population, disciples, entities, languages, words, knowledge, wars, trade, alliances, dead); peoples' historians' perspectives (`kronik_bakis` blockquotes "According to {people}'s historian · {name}"); councils (speeches, motion passed/rejected, decision, minutes); full chronicle list (type label, year, son link; hides internal type `motor_ham`); "Born in this epoch" list.
8. **Encyclopedia** (`#ansiklopedi`): all records except languages, grouped (multi-world: per world, then "World unknown") by type in order `bolge, yer, yerlesim, halk, hizip, tarikat, olumlu, tur, kaynak, yapit, esya, arac, ordu, ruh, dis, gok, yasa, kanun, teknoloji, gelenek, efsane, kehanet, eser, olay` (others last); places nested with their contents (heading level by depth). Entry: image, name, title, †, meta (type · subtype · rarity class · epoch · creator/"the god created"/"from the world's course"/"from the world's birth" · status), description (strip "[World engine]" prefix), type stats, depth (history, type-specific fields from agents `OZEL`, sayings, rumours), "Fate's judgement" note, tags (hiding internal prefixes `basamak: mekanik: ozellik: yorum: yasa:` and `dilden-ad`, `ajan seçili`), bonds (active first; past ones "In the past"), nested contents. Then "Other records" for anything not yet written.
9. **Languages and dictionaries** (`#diller`): every language including dead ones (†, "dead language (Epoch n)"), script name, word count, speakers, description, depth, Fate's judgement, bonds, full dictionary (word, kind, meaning, origin, example).
10. **Stories and facts** (`#hikayeler`): open threads (epoch, text, related links), closed threads (epochs, text, closing), canon facts (subject relation object, epoch), prayers and answers (all messages to/from the creator: from → to (intent): text, request).
11. **Achievements and trials** (`#basarimlar`): "Score {n} · {k}/{m} achievements", earned achievements by epoch, scenario history, score breakdown labels (Population, Diversity, Languages, Worlds, Civilization, Doomsday, Achievements, Trials), score per epoch "E{n} {score}".
12. **Fate's ledger** (`#defter`): every action of the god and sons by epoch: who · action display name (`public/arac-ad.eylemAdi`) · "undone" flag, summary (with "…" if truncated), result (≤600 chars).
13. **Event log** (`#olay-defteri`): raw engine rows (`motor_ham`) folded into epoch summaries.
14. **Index** (`#dizin`): alphabetical (locale collation) of sons, entities and worlds with type; grouped by first letter.

Text sanitation: remove machine markers `[iplik#12]` and `(#245)` from canon text; HTML-escape everything; paragraphs split on newlines.

### 9.2 Presentation
- Screen: 700px measure book page, serif fonts (Cormorant Garamond headings, Alegreya body via Google Fonts), parchment palette tokens (`--kagit` paper #f4ecdc, `--murekkep` ink #2a2219, `--soluk` faint #75664f, `--vurgu` accent #8a4b2a, `--cizgi` rule #d6c5a6) with a dark variant under `prefers-color-scheme: dark`; floating toolbar (back to app, contents, index, "Print / PDF" button bound by a CSP nonce script).
- Print: A4, margins 20/18/22 mm, page numbers bottom-centre (not on the cover), always light paper, every major section starts on a new page, images limited in height, map on its own page.
- Images are thumbnails `/gorsel/{file}?w=640` so the PDF does not bloat.
- Mobile: two-column plates, full-width sticky toolbar.

### 9.3 Map SVG (`mapSvg(worldId)`)
Uses the same generator as the browser (`public/harita-gen.dunyaHaritasi` with d3-delaunay, seed = world seed or world name, terrain JSON, world type, entities from `harita.haritaVarliklari`). Returns '' if no region. Draws known Voronoi cells (`bilinen[i]` 1 = fully, 2 = half-known with alpha `99`) filled by biome colour (palette `['#a9c8d3','#7fa7b9','#e6d7a6','#d6cb93','#bcd08f','#93b37c','#c2b089','#83a070','#a49b8d','#efede6']` indexed by `biyomIndeks(yNorm, moisture, land)`), merged into one path per colour; settlements/peoples as dots with labels; region names in italics below their centres. Font size = max(14, round(viewWidth/70)).

### 9.4 Cross-references
Calls `harita-gen`, `harita.haritaVarliklari`, `rules` catalogues, `world.allSons/kapak/sozlukDil/konusanlar`, `dilmotoru.yaziOf`, `agents.OZEL`, `yabanci.*`, `kodeks.gezginRehberi`, `hedef.hedefler`, `yaratici`, `itibar`, `public/arac-ad.eylemAdi`. Called by server `/kitap`.

---

## 10. Codex, traveller's guide, cosmic chronicle (`kodeks.js`)

### 10.1 Codex (`codex()` → Markdown; `GET` export)
No world → "# There is no world yet". Otherwise lines:
1. `# {world}`, `*Epoch {e} · world year {y}*`, world-1 image `![](gorsel/{file})`.
2. `## Cosmology`, `## Tone`, `## Naming language`.
3. `## {creator}, {title}` + image; **Appearance.**, **Temperament.**, `> Portrait prompt: …`.
4. `## Laws of nature` — each `yasa`: "- **{name}.** {description} *(Mechanism: {YASA_MEKANIKLERI[m]})*" (m from tag `yasa:{m}`, unless 'yok').
5. `## Pantheon` — per son: `### {name}, {title}` + image; "{rarity} ★… · Level n · d1 / d2 · status"; bullets Appearance, Temperament, Obsession, Fear, Style, Existence ("{nature} ({state}). Manifestation: …"), Stats, Passions, Powers ("{name} (Lv{unlock level}): description" · …), Plan; epic `#### title`, `> *verse*`, text; portrait prompt.
6. Geography: single world → `## Geography` then each root entity (no parent, type has locations) recursively; multi-world → per world `## World: {name}` + image + description + traveller's guide Markdown + `### Geography`; orphans under `## Places of unknown world`. Entry: heading `#`×min(6, 3+depth); italic meta "{type} · {subtype} · {rarity class} · Epoch n · {"the world's course" | son name | creator}{ · status}"; description; "Stats: …"; "Bonds: {label} {target}; …" (active, excluding `icinde`); **History.**, sayings as quotes, rumours list; image prompt; children recursively.
7. Root-level `gok` (sky), `efsane` (legend), `gelenek` (tradition), `kehanet` (prophecy), `olay` (event) sections.
8. `## Knowledge` — "- **{name}** ({branch}, level n): description Knowers: …".
9. `## Languages and dictionary` — per language: heading, "*{subtype} · speakers: …*", description, table `| Word | Kind | Meaning | Origin |` (up to 5000 words, oldest first, `|` escaped).
10. `## Open stories`.
11. Multi-world: `## Cosmic chronicle` table: one row per epoch, one column per world with the first 2 headlines.
12. `## Chronicle` — per epoch `### Epoch n: {name}`, *summary*, quote with stats ("Population … · disciples … · n entities · n words · n knowledge · n hostilities · n trade roads"), narrative. (A corrupt stats row does not break the export.)

### 10.2 Traveller's guide (`travellerGuide(worldId)`, `GET /api/dunyalar/{id}/rehber`)
Returns:
```
{ world: {id, name, type, type_name, description, cosmology, dialect, star:{name,type}, parent (moon of), physics:{time, atmosphere, gravity}, leak, discovery},
  climate: derin.iklimOf(worldId),
  dangers: [ regions/places with danger ≥ dangerous_place (top danger_list, "danger n"),
             species with danger ≥ dangerous_species (top danger_list, "predator (danger n){, megafauna}"),
             every outer being ('dis') ("Outer Being"),
             leak ≥ leak_danger → {name:'Leak', reason:"cosmic leak n/100: minds cloud, species warp"} ],
  peoples: communities sorted by population/disciples desc, first people_list: {id, name, type, population, language (first 'konusur'), god (first 'tapar' target name)},
  resources: [{id, name, description[:160], mechanics, original: tag 'özgün'}],
  routes: seyahat.rotalar(worldId, {all:true}) not hidden: {id, target, method, duration, danger, active, open, status, reason, open_epoch, close_epoch},
  foreign_gods: [{id, name, title, status, attitude}],
  sky: [{id, name, subtype}] of 'gok' entities }
```
Markdown form (`guideMd`): "**{type}** · around {star} ({type}) · moon of {parent} · time ×k · atmosphere a · gravity g", climate, **Dangers:**, **Peoples:** ("{name} (pop), worships {god}"), **Resources:** ("{name} [mechanics]"), **Roads:** ("{target} ({method}, {n} epochs{, closed: reason})"). (Turkish suffix fix `ekDuzelt` — LANGUAGE-SPECIFIC.)

### 10.3 Cosmic chronicle (`cosmicChronicle({last=30})`, `GET /api/kozmik-kronik`)
`last` clamped 1..500 (bad input → 30). For each of the last N epochs: group that epoch's chronicle rows by world (world of the first referenced entity that exists; else the son's active world; else skip). Per world: `event_count`, up to 4 headlines (≤140 chars, whitespace collapsed) from important types {savas, kader, dunya, dunya_dogusu, olum, isyan, kiyamet, korku, medeniyet, sefer, yukselis, efsanevi_sefer, gok, yabanci_tanri, kozmik}; attach Fate's per-world epoch summary/narrative (`caglar_dunya`) if any. Returns `[{epoch, name, summary, worlds:[{world_id, name, event_count, headlines, summary?, narrative?}]}]`.

### 10.4 Tunables — domain `GUIDE` (old `REHBER`), group "Codex and guide"

| Key (old) | Default | Min | Max | Label |
|---|---|---|---|---|
| dangerous_place (tehlikeli_yer) | 55 | 0 | 100 | Guide: danger at which a region or place counts as dangerous |
| dangerous_species (tehlikeli_tur) | 50 | 0 | 100 | Guide: danger at which a species counts as a predator |
| leak_danger (sizinti) | 30 | 0 | 100 | Guide: leak level counted as a danger |
| danger_list (tehlike_liste) | 6 | 0 | 100 | Guide: listed entries per danger kind |
| people_list (halk_liste) | 14 | 0 | 500 | Guide: most populous communities listed |

---

## 11. Player manual assignments — "the god's hand" (`oyuncu.js`)

Principle: every mechanism runs by itself, but the god may assign at any moment; the automatic flow continues from the assignment. Every assignment is written to the chronicle as the god's hand: `godsHand(text, ids)` = `addChronicle(cag, null, 'tanri', "{T}'s hand: {text}", ids)`.

Validators: `needEntity(id)` ("No such entity."), `needSon(id)` ("No such son."), `needWorld(id)` ("No such world."), `needNumber(x, name)` (rejects null, '', booleans, non-finite: "Invalid {name}: must be a number."), `reachable(a,b)` = same world, or an active route between their worlds. Expedition intents: `koloni` colony, `ticaret` trade, `kesif` exploration, `fetih` conquest, `hac` pilgrimage.

### 11.1 Sons' worlds
- **assignSonToWorld(sonId, worldId)**: son not dead ("{s} is dead; their bones do not stir."), world not forgotten ("{w} is forgotten; nobody can go there."), not already there ("{s} is already in the world {w}."). Set `active_world`, `god_assignment_epoch = cag` (protects from auto-distribution for `assignment_protection` epochs). Chronicle "{s} was sent to the world {w}."
- `godProtects(s, cag)` = `god_assignment_epoch != null and cag − it < assignment_protection`.
- **distributeSons(cag, publish)** (automatic; runs in the epoch runner when `world.ogul_dagitim == 'otomatik'` (default); `'elle'` manual disables): for each non-forgotten world (by id) with no active son but with ≥1 canon community/mortal: candidates = active sons not protected whose current world has ≥ `distribution_min_donor` active sons (incl. self); score = number of worshipping entities in their current world + (`guardian_weight` if they are that world's guardian `koruyucu_ogul`); pick lowest score; move; chronicle 'kozmik' "{s} turned to the godless world {w}."; publish system message. Returns number moved.

### 11.2 Entities
- **moveEntity(id, locationId)**: type must accept the location type (`VARLIK_TURLERI[type].konum`), else "{Type} cannot be placed inside {LocType}; possible: …"; no cycles ("A thing cannot be moved inside itself.", checks 12 ancestors); set `location_id`, clear `map_xy`; refresh location bond (`konumBaginiTazele`); BFS descendants inherit the parent's `world_id` and clear `map_xy`; invalidate map cache; chronicle "{v} was moved into {k}."
- **assignPatron(id, sonId | 0 | null, foreignGodId=null)**: only communities and mortals ("Only communities and mortals worship."); son must be living ("{s} is dead; only a resurrection order worships them."). With foreign god: must exist and not be dead; close **all** active worship bonds; add `→y` bond "the god's command"; remove `tanrısız`; chronicle "{v} now worships the foreign god {y}." Otherwise close active worship bonds to o/y/t (single patron rule), then: 0 → `worshipCreator` + "{v} was bound directly to the creator."; son → bond + remove godless + "{v} now worships {s}."; null → "{v} was left godless." (note: does not add the `tanrısız` tag).
- **imposeDiplomacy(id, targetId, kind)**: distinct entities; except for peace both must be canon ("A command is only set between the living.") and reachable ("{a} and {b} are in separate worlds with no open road between them."). `savas` war: close trade and alliance bonds; add `dusman` if missing; community relationship −`command_war`. `baris` peace: `derin.barisYap(a, b, cag, "the god's command", {ceasefire:true})` (enmity closes, ceasefire prevents re-war), end any ongoing campaign (`seferBitir`, errors ignored), relationship +`command_peace`. `ittifak` alliance: close enmity; add `muttefik`; +`command_alliance`. `ticaret` trade: close enmity; add `ticaret`; +`command_trade`. Else "Invalid command: savas | baris | ittifak | ticaret". Chronicle "{war|peace|alliance|trade} was commanded between {a} and {b}."
- **setStat(id, stat, value)**: stat must be in the type's stat list, or `sagduyu` (sanity 0–100) or `adanmislik` (devotion 0–`DERIN_YASAM.devotion_cap`) — else "There is no stat \"{stat}\" for {type}."; value via needNumber, clamped to the stat's min/max; chronicle "{v}'s {stat} value {old|-} → {new}."
- **setTags(id, {add, remove})**: only assignable tags pass (silently filtered): fixed list `ASSIGNABLE_TAGS` = harika wonder, lanetli cursed, tanrısız godless, harabe ruin, megafauna, istilacı invasive, kozmik kaynak cosmic resource, özgün kaynak original resource, seçilmiş chosen, yerli native, koloni colony, bağımsız independent, imparatorluk empire, dış tarikat outer cult, masal fable, ölümsüz immortal, gezegene tapar worships the planet, kozmik arşiv cosmic archive, ruhlu ensouled, yeminbozan oathbreaker, sürgün exile, ruh hasatçısı soul harvester, iki zamanlı two-timed, federasyon federation; plus prefixes `ozellik:` (creature trait; must exist in `OZELLIKLER` else "Unknown trait: x"), `mekanik:` (resource mechanic; base must exist in `KAYNAK_MEKANIKLERI` else "Unknown resource rule: x"), `yasa:` (law mechanic). Chronicle "{v}: +a, −b." if anything changed. (Lists are exposed to the UI via `/api/state`.)
- **selectAgent(id, selected)**: types halk/yerlesim/hizip/tarikat/olumlu/tur else "This entity cannot act as an agent."; adds/removes tag `ajan seçili` (the marked entity acts as a mortal agent next epoch for sure). Not chronicled.
- **commandExpedition(id, {route_id, intent='kesif', percent=expedition_percent})**: living ("{v} no longer lives."), community or mortal ("Only communities and mortals go on expeditions."), valid intent; route must be in the passable list from v's world; otherwise explain: not touching v's world → "There is no such road out of {v}'s world."; hidden → "This road is hidden; reveal it first (Reveal action)."; else the route status reason (storm, seal, unaligned slingshot…) or "This road is closed right now."; not already travelling ("Already on the road."); percent finite ≥ 1 ("At least 1% of the population must join."), ≤ `expedition_cap` ("At most {cap}% of the population may join (world rule TANRI_ELI.expedition_cap = {cap})."). travellers = population ? round(pop × percent/100) : 1. `seyahat.yolculukBaslat({traveller, route, intent, population, epoch})`. Chronicle "{v} was sent on a {intent} expedition to the world {target} ({n} epochs)."
- **sendToExplore(id, {kind})** (kind ∈ bolge|yer|null): explorer validation as above; `ufuk.toprakBul({explorer, world, epoch, note: discovery chronicle, kind: kind || (world has regions ? null : 'bolge'), reason:"by the god's command", narrow: darMi(world)})` — no dice roll; null → "There is no region to explore in this world; a new region must be found first (land: region)." Chronicle "{v} was sent into unknown lands; {land} was found." (discovery chronicle type 'kesif').
- **seekRoad(id)**: `ufuk.yolAra(v, {how:"following the stars the god showed", epoch, certain:true})`: road → discovery chronicle + "{T} showed {v} the road of the sky."; sensed world → `sezgiKaydet` + "{T} made {v} sense a world nobody knew."; else throw "There is already a road to every known world and no new world can be sensed this epoch (world rule OLUMLU_ARAC.unknown_world_per_epoch)."
- **commandRite(id, {son_id, kind='dua', victim_id})**: `resurrectionRite(v, sonId, {kind, epoch, victimId})` (§5.3; the community pays); chronicle "{T}'s hand: ordered {v} to hold a rite for {son}."
- **discoveryRound(worldId)**: run the engine's discovery dice for that world now (`ufuk.gezegenKesfi(cag, note, {worldId})`, with KESIF rules and cap); chronicle "ordered a discovery round in {w}: {n new lands found | this time nobody found a new land}."

### 11.3 Sons — `editSon(id, body)`
- **Rename**: trimmed ≤60; if different (normalized): reject if the name is taken by any entity or son ("\"{name}\" already exists (in an entity or son). Choose an original name.") or is too similar to an existing name (`benzerAd`; "\"{name}\" is too similar to the existing \"{other}\"; mortals would confuse them. Choose a name that sounds clearly different."). Rename propagates to all texts (chronicle, epoch narratives, bonds, beliefs…) via `world.adDegistir(id, name, {tip:'o'})`; chronicle "{old} now bears the name {new}."
- `title` (non-empty, ≤120), `plan` (≤1200, empty → null), personality fields appearance/temperament/obsession/fear/style/secret (≤1500; empty deletes).
- `tutku`: each known passion key with finite value → clamp 0..100.
- `statlar`: each son stat key finite → round, clamp 1..100; then life ≤ canMax, essence ≤ ozMax.
- `nadirlik` (rarity) must be a valid class ("Invalid class"); chronicle "{s} is now in {class} class."
- `kaynak` (resources): essence 0..ozMax, life 0..canMax, fame ≥0, faith ≥0, level ≥1, stars 1..YILDIZ_MAX(5), existence 0..100 (all rounded).
No cost.

### 11.4 Cosmos
- **editWorld(id, body)**: name uniqueness across the cosmos (`kozmikAdDenetle`: "\"{name}\" is already used in the cosmos; choose another name."); text fields ad/kozmoloji/lehce/aciklama/gorsel_prompt (empty clears, except name); `tur` (world type ∈ DUNYA_TURLERI → also resets `arazi` terrain to the type's default); gravity ∈ {düşük low, olağan normal, yüksek high}; atmosphere ∈ {yok none, ince thin, olağan normal, yoğun dense, zehirli toxic}; time factor > 0 (no upper bound for the god; "Time factor must be greater than zero (1 normal flow; 2 twice as fast, 0.5 half as fast)."); leak 0..100 ("Leak must be between 0 and 100."); `olumlu_ajan` (per-world mortal agents per epoch; null/''/'otomatik' → automatic; else 0..`mortal_agent_cap`, "At most {cap} mortal agents per world per epoch (world rule …)"); `koruyucu_ogul` guardian son (must exist; when actually changed set it and `koruyucu_oto=0` = "the god assigned it"); `ayna_ikiz` mirror twin (not itself; must exist); discovery state ∈ {bilinen, efsane, bilinmeyen, unutulmus}: world 1 cannot be forgotten ("The first world cannot be forgotten."); forgetting calls `panteon.dunyayiUnut` (closes roads, sons return to world 1); un-forgetting: a DB trigger reopens roads closed by the forgetting; note "came out of the mist{; n roads closed during forgetting were reopened}{; n roads remain closed (closed for another reason or the other end is forgotten; reopen with \"Open road\" if needed)}". Orbit: `ana_id` parent (not itself "A world cannot be its own moon."; no cycles "{parent} already orbits {w}."; sets star = parent's star, orbit = 0.15 + 0.08 × other moons of parent) or `yildiz_id` star (must exist; clears parent; orbit = 1 + 0.7 × other planets of that star); then `db.aylariHizala` moves moons along ("{n} moons moved to the new orbit with it"). Invalidate map; chronicle "The world {w} was reshaped{: notes}."
- **deleteStar(id)**: only if no world has it as star ("{star} cannot be deleted: {planets} orbit it{ (with n moons)}. First move {them|it} to another star (the world's "Orbit" selector); its moons go with it."); delete; chronicle 'kozmik' "{T} removed {star} from the sky." (undoable via ledger).
- **editStar(id, body)**: unique name; ad/tur/aciklama/gorsel_prompt (name and type cannot be emptied); brightness clamp 0..100; x,y numbers.
- **openRoute({a, b, method})**: neither world forgotten ("{w} is forgotten; no road opens there."); method ∈ SEYAHAT_YONTEMLERI ("Invalid method."); `seyahat.rotaAc({a, b, method, controller:null, description:"a road opened by the god"})`; chronicle "opened a road between {A} and {B} ({method})."
- **setClimate(phase, epochs=climate_epochs, worldId=null)**: phase ∈ IKLIM keys (ilik temperate, kurak drought century, yagmur rain era, …) else "Invalid climate era: …"; epochs (null/'' → default) finite ≥1 ("A climate era must last at least 1 epoch."), ≤ `climate_epochs_cap` ("…at most {cap} epochs (world rule …)"); rounded. Targets: that world (not forgotten: "{w} is forgotten; no climate is commanded to the sky inside the mist.") or all non-forgotten worlds. Stored per world as `{evre, kalan, bas: cag, tanri: true}` (`tanri:true` makes the engine apply the era once more on the first transition so "N epochs" touches the land N times). If all worlds or the lowest-id world is targeted, also update the legacy `world.iklim`. Chronicle "commanded {era} to the sky of {world|all worlds} ({n} epochs)."
- **defineCosmicResource({name, description, rule, side_effect})**: name required ("The resource must have a name."); store JSON on world; chronicle "set the cosmos's travel resource as {name}."
- **openCosmicDeposit(regionId)**: target type bolge or yer ("A deposit is opened in a region or place."); a cosmic resource must be defined ("First define the cosmos's travel resource."); insert `kaynak` {subtype 'cosmic travel resource', name "{res} Deposit ({place})", description "{res.description} {res.rule}", stats {abundance: deposit_abundance, value: deposit_value, might: deposit_might}, power deposit_power, epoch, location, tags ['kozmik kaynak','mekanik:bagimlilik','mekanik:sabit'], source 'tanri'} + `icinde` bond; chronicle "opened a {res} deposit in {place}." (Also usable by sons via a tool.)
- **setGodMood({contentment, anger, interest, loneliness})**: each provided value clamped 0..100 into `tanri_ruh`. No chronicle.
- **createForeignGod(body)**: world must exist; name required ("It must have a name."); `panteon.yabanciTanriEkle({...body, name, attitude: +attitude||0}, cag)` (dedupes names e.g. "X II"); chronicle "placed an old god in the world {w}: {name}." After the response, the server triggers background LLM deepening (`E.yabanciDerinlik`) unless LLM is disabled.
- **editForeignGod(id, body)**: unique name; text fields ad/unvan/alanlar/aciklama/gorsel_prompt; attitude clamp −100..100; power clamp 0..100; status ∈ {uyanik, uykuda, yenik, olu} when changed: awakening pressure reset to 0 when awake or dead, death epoch set when dead (cleared otherwise), defeat epoch when defeated; chronicle "manually changed the status of the foreign god {y}: {awake|asleep|defeated|dead}."; when leaving sleep and the request didn't rewrite title/description, `kronik-onar.uyanisMetniYaz` rewrites text that mentions sleep. `temas` contact flag. Stats (`statTemizle`, 1–100), personality (merge; empty removes), existence (state must be in `VAROLUS_HALLERI` else "Existence state must be one of: …"), powers (array or index-keyed object; each named power's effect must be known: "Unknown power effect: x. Must be one of: …"; `gucTemizle`), depth text fields (`YT_DERIN_METIN`) if depth exists.

### 11.5 Story and canon
- **openThread(text, related)**: text required ("The thread must have a text."); related ids filtered to existing entities; chronicle "opened a new story: {text[:140]}".
- **closeThread(id, how)**: must be open ("No such open thread."); status 'kapandi', closing = how or "The god closed this story.", closing epoch; chronicle "closed a story (thread#{id}): {how}".
- **addFact({subject_id, relation, object_id | object})**: subject must exist; relation required ("Write a relation."); object id or text required ("An object is needed."). Insert active fact (source null). No chronicle.
- **removeFact(id)**: `active=0`.
- **editBelief({people_id, son_id (0 = creator), name, narrative, misconception})**: entity must exist; son must exist unless 0; narrative required ("Write the people's narrative."); upsert on (people, son); name defaults to the creator's/son's name.
- **rekindleStar(starId, who, epoch)**: star must exist; type must be dead (ölü yıldız / kara güneş / yıldız kalıntısı) else "{star} is already burning."; type → 'yeniden doğmuş yıldız' (reborn star), brightness `rekindle_brightness`; each world orbiting it: leak = max(0, leak − `rekindle_leak`); chronicle 'gok' "{who} rekindled {star}; light returned to the worlds buried in darkness." (Invoked by the cosmic action `tutustur` in epoch.js — cost `KOZMIK_BEDEL.tutustur` — and by the son tool `yildiz_tutustur`; may complete a legendary expedition and the "Rekindle the lost star" scenario.)
- **editSuffix({t, id, pronunciation, tamlama, reset})** — LANGUAGE-SPECIFIC (Turkish suffix harmony overrides for a name). Drop.
- **foundFederation({members, name})**: ≥2 distinct entities ("Choose at least two communities for a federation."), each a living community ("{v} is not a living community."); name default "{first} Federation"; in one transaction: create `hizip` {subtype 'interworld federation' if members span worlds else 'federation', power MED.federation_power_level(6), location = first member's location, tags ['federasyon'], stats {strength 50, wealth 60, influence 70} (MEDENIYET rules), description "{members} united in one federation by {T}'s command."}; each member `uyesi`(member of) bond; every pair: close enmity, add `muttefik` if missing ("federation"); chronicle 'medeniyet' "{T} founded a federation: {name} ({members})."
- **addBond({src_type='v', src_id, dst_type='v', dst_id, type, description})**: type ∈ BAG_TURLERI and not `icinde` ("Invalid bond type: x. \"Inside\" is location; it changes by moving."); endpoints must be entity or son ("A bond endpoint must be an entity (v) or a son (o)."); not self ("A thing cannot be bonded to itself."); not duplicate active ("This bond already exists."); add with description or "the god's command"; chronicle "established a bond between {a} and {b}: {label}."
- **removeBond(id)**: exists ("No such bond."), active ("This bond is already broken."), not `icinde` ("\"Inside\" is location; move the entity instead of breaking the bond."); set inactive (kept as history: forgiving debt, breaking adoption, freeing captives, breaking treaties, lifting ceasefires); chronicle "broke the bond between {a} and {b}: {label}."

### 11.6 Tunables — domain `GODS_HAND` (old `TANRI_ELI`), group "Intervention" for all rows

| Key (old) | Default | Min | Max | Label |
|---|---|---|---|---|
| command_war (buyruk_savas) | 40 | 0 | 200 | Community relationship lost when the god commands war |
| command_peace (buyruk_baris) | 20 | 0 | 200 | Community relationship added when the god commands peace |
| command_alliance (buyruk_ittifak) | 30 | 0 | 200 | Community relationship added when the god commands alliance |
| command_trade (buyruk_ticaret) | 10 | 0 | 200 | Community relationship added when the god commands trade |
| expedition_percent (sefer_yuzde) | 10 | 1 | 100 | Population joining a god-commanded expedition (default %) |
| expedition_cap (sefer_tavan) | 30 | 1 | 100 | Max population joining a god-commanded expedition (%) |
| climate_epochs (iklim_cag) | 4 | 1 | 100 | Default duration of a commanded climate era (epochs) |
| climate_epochs_cap (iklim_cag_tavan) | 50 | 1 | 1000 | Longest climate era the god can command (epochs) |
| rekindle_brightness (tutustur_parlaklik) | 75 | 0 | 100 | Brightness of a rekindled star |
| rekindle_leak (tutustur_sizinti) | 20 | 0 | 100 | Leak removed from the rekindled star's worlds |
| distribution_min_donor (dagitim_verici_en_az) | 2 | 1 | 100 | In auto-distribution a son may leave only if at least this many active sons (incl. himself) are in his world |
| assignment_protection (atama_koruma) | 3 | 0 | 1000 | Epochs auto-distribution does not touch a son the god sent manually |
| mortal_agent_cap (olumlu_ajan_tavan) | 12 | 0 | 1000 | Max mortal agents that can be set manually per world |
| guardian_weight (koruyucu_bag) | 5 | 0 | 1000 | Bond weight to the world a son guards when distributing sons |
| deposit_power (yatak_guc) | 8 | 1 | 12 | Power level of a god-opened cosmic deposit |
| deposit_abundance (yatak_bolluk) | 80 | 0 | 100 | Abundance of a god-opened cosmic deposit |
| deposit_value (yatak_deger) | 95 | 0 | 100 | Value of a god-opened cosmic deposit |
| deposit_might (yatak_kudret) | 85 | 0 | 100 | Might of a god-opened cosmic deposit |

### 11.7 Cross-references
Calls `world.*` (incl. `adDegistir`, `isimAlinmis`, `benzerAd`, `aramaNorm`, `konumBaginiTazele`, `ekSozluguYenile`), `db.aylariHizala/tx`, `derin.tIliskiDegistir/etiketEkle/etiketSil/barisYap/seferBitir/kayitAc/TOPLULUK`, `seyahat.rotaAc/rotalar/yolculukBaslat/rotaDurumu`, `yaratici.yaraticiyaTapin/ruhHali`, `panteon.yabanciTanriEkle/dunyayiUnut`, `harita.haritaGecersiz`, `ufuk.toprakBul/toprakOlcusu/darMi/yolAra/sezgiKaydet/gezegenKesfi`, `olum.dirilisAyini`, `yabanci.*`, `kronik-onar.uyanisMetniYaz`, rule domains `DERIN_YASAM`, `MEDENIYET`. Called by server routes (§12), epoch runner (`ogullariDagit`, `tanriKorur`), epoch cosmic action (`yildizTutustur`), son tools (`yildizTutustur`, `kozmikYatakAc`).

---

## 12. Player actions catalogue

All actions below are what the creator (player) can do **manually** in the modules of this part. Unless marked otherwise each runs inside `ledgered(key, fn)` (§0.3: atomic, rolled back on any error including the charged essence, recorded in Fate's ledger, undoable). "Cost" is creator essence charged via `spend` (rejected with the rule name if insufficient). Endpoints are the old HTTP routes (all JSON; `{id}` = path id). Chronicle type is `tanri` unless stated.

Actions of the creator owned by other spec parts (blessing/lightning/revelation/miracles/disasters/teaching, world creation, calling sons, star/seal/cleanse/forget/sky-event/soul-vessel/legendary-expedition cosmic actions, road cut/build/reveal, exile/pardon, canon toggle, entity edit, ascension, epic, prompt editing, archive, Fate's network repair, god's note) live in `epoch.js`/`mudahale.js`/`otesi.js` and are listed there.

### 12.1 From `oyuncu.js` (the god's hand)

| # | Ledger key | Endpoint | Function | Inputs | Validation (errors) | Cost | Effects | Chronicle |
|---|---|---|---|---|---|---|---|---|
| 1 | `ogul:dunya` | POST /api/ogullar/{id}/dunya | assignSonToWorld | `dunya_id` | son exists, not dead; world exists, not forgotten; not already there | 0 | son.active_world = world; protection epoch stamped (`assignment_protection`) | "{T}'s hand: {s} was sent to the world {w}." |
| 2 | `ogul:duzenle` | POST /api/ogullar/{id}/duzenle | editSon | `ad, unvan, plan, kisilik{…}, tutku{…}, statlar{…}, nadirlik, kaynak{oz,can,un,inanc,seviye,yildiz,varlik}` | name unique & not too similar; rarity valid | 0 | rename everywhere; title/plan/personality; passions 0–100; stats 1–100 (life/essence re-capped); rarity; resources clamped | rename: "{old} now bears the name {new}."; rarity: "{s} is now in {class} class." |
| 3 | `varlik:tasi` | POST /api/varliklar/{id}/tasi | moveEntity | `konum_id` | both exist; location type allowed; no cycle | 0 | location set; location bond refreshed; descendants' world updated; map invalidated | "{v} was moved into {k}." |
| 4 | `varlik:hami` | POST /api/varliklar/{id}/hami | assignPatron | `ogul_id` (son id, 0 = creator, null/'' = none) or `yabanci_id` | community or mortal; son living; foreign god exists & not dead | 0 | closes previous worship; binds to son / creator / foreign god; removes `tanrısız` | "{v} now worships {s}." / "…bound directly to the creator." / "…worships the foreign god {y}." / "…left godless." |
| 5 | `buyruk` | POST /api/varliklar/{id}/buyruk | imposeDiplomacy | `hedef_id`, `tur` ∈ savas/baris/ittifak/ticaret | distinct; living (except peace); reachable (except peace) | 0 | war: enmity bond, trade/alliance closed, relation −40; peace: `barisYap` + ceasefire + end campaign, +20; alliance: +30; trade: +10 | "{kind} was commanded between {a} and {b}." |
| 6 | `varlik:stat` | POST /api/varliklar/{id}/stat | setStat | `stat`, `deger` | stat exists for type (or sanity/devotion); numeric | 0 | stat clamped to its range | "{v}'s {stat} value {old} → {new}." |
| 7 | `varlik:etiket` | POST /api/varliklar/{id}/etiket | setTags | `ekle[]`, `sil[]` | only assignable tags/prefixes; trait & mechanic names known | 0 | tags added/removed | "{v}: +a, −b." |
| 8 | `varlik:ajan` | POST /api/varliklar/{id}/ajan | selectAgent | `secili` bool | agent-capable type | 0 | toggles tag `ajan seçili` (forced mortal agent next epoch) | none |
| 9 | `sefer` | POST /api/varliklar/{id}/sefer | commandExpedition | `rota_id`, `niyet` (koloni/ticaret/kesif/fetih/hac), `yuzde` | living community/mortal; route passable from its world (with reason); not travelling; 1 ≤ % ≤ `expedition_cap` | 0 | journey started with that share of population | "{v} was sent on a {intent} expedition to the world {w} ({n} epochs)." |
| 10 | `kesfe_yolla` | POST /api/varliklar/{id}/kesif | sendToExplore | `tur` ∈ bolge/yer/null | living community/mortal; a region must exist for 'yer' | 0 | guaranteed land discovery (new region/place) | discovery line (type `kesif`) + "{v} was sent into unknown lands; {land} was found." |
| 11 | `yol_arat` | POST /api/varliklar/{id}/yol-ara | seekRoad | — | living community/mortal; something to find | 0 | certain road discovery or sensed world | discovery line + "{T} showed {v} the road of the sky." / "…made {v} sense a world nobody knew." |
| 12 | `ayin_buyur` | POST /api/varliklar/{id}/ayin | commandRite | `ogul_id`, `tur` ∈ dua/servet/kan/can, `kurban_id` | §5.3 validations | 0 for creator (community pays wealth / population / a life) | devotion added to dead son's order (×2 at the bones' region) | 'dirilis' rite line + "ordered {v} to hold a rite for {son}." |
| 13 | `kesif_turu` | POST /api/kesif/tur | discoveryRound | `dunya_id` | world exists | 0 | runs that world's discovery dice now | discovery lines + "ordered a discovery round in {w}: …" |
| 14 | `dunya:duzenle` | POST /api/dunyalar/{id}/duzenle | editWorld | `ad, kozmoloji, lehce, aciklama, gorsel_prompt, tur, yercekimi, atmosfer, zaman_katsayi, sizinti, olumlu_ajan, koruyucu_ogul, ayna_ikiz, kesif, yildiz_id, ana_id` | unique name; enums; time > 0; leak 0–100; agent cap; guardian exists; no self-mirror; world 1 not forgettable; no orbit cycles | 0 | world fields; forgetting/remembering side effects; orbit move with moons | "The world {w} was reshaped{: notes}." |
| 15 | `yildiz:sil` | POST /api/yildizlar/{id}/sil | deleteStar | — | no world orbits it | 0 | star row deleted | 'kozmik': "{T} removed {star} from the sky." |
| 16 | `yildiz:duzenle` | POST /api/yildizlar/{id}/duzenle | editStar | `ad, tur, aciklama, gorsel_prompt, parlaklik, x, y` | unique name; numbers | 0 | star fields | none |
| 17 | `rota:kur` | POST /api/kozmik/rota | openRoute | `a, b, yontem` | worlds exist & not forgotten; method valid | 0 | new route (no controller) | "opened a road between {A} and {B} ({method})." |
| 18 | `iklim` | POST /api/kozmik/iklim | setClimate | `evre`, `cag_sayisi`, `dunya_id?` | valid era; 1 ≤ epochs ≤ cap; world not forgotten | 0 | climate era set on world(s) (+ legacy) | "commanded {era} to the sky of {…} ({n} epochs)." |
| 19 | `kozmik:kaynak` | POST /api/kozmik/kaynak | defineCosmicResource | `ad, aciklama, kural, yan_etki` | name required | 0 | world.kozmik_kaynak set | "set the cosmos's travel resource as {name}." |
| 20 | `kozmik:yatak` | POST /api/kozmik/yatak | openCosmicDeposit | `bolge_id` | region/place; resource defined | 0 | new cosmic deposit entity | "opened a {res} deposit in {place}." |
| 21 | `tanri:ruh` | POST /api/tanri/ruh | setGodMood | `hosnutluk, ofke, ilgi, yalnizlik` | — | 0 | mood values clamped 0–100 | none |
| 22 | `yabanci:ekle` | POST /api/yabanci | createForeignGod | foreign god fields + `dunya_id`, `ad` | world exists; name required | 0 | foreign god added (deduped name); background LLM deepening | "placed an old god in the world {w}: {name}." |
| 23 | `yabanci:duzenle` | POST /api/yabanci/{id}/duzenle | editForeignGod | `ad, unvan, alanlar, aciklama, gorsel_prompt, tutum, guc, durum, temas, statlar, kisilik, varolus, gucler, derinlik` | exists; unique name; valid state/effects | 0 | fields; status side effects; wake-text rewrite | status change: "manually changed the status of the foreign god {y}: …" |
| 24 | `iplik:ac` | POST /api/iplikler | openThread | `metin`, `ilgili[]` | text required | 0 | new open thread | "opened a new story: …" |
| 25 | `iplik:kapat` | POST /api/iplikler/{id}/kapat | closeThread | `nasil` | open thread exists | 0 | thread closed | "closed a story (thread#{id}): …" |
| 26 | `gercek:ekle` | POST /api/gercekler | addFact | `ozne_id, iliski, nesne_id | nesne` | subject exists; relation; object | 0 | canon fact | none |
| 27 | `gercek:sil` | POST /api/gercekler/{id}/sil | removeFact | — | — | 0 | fact inactive | none |
| 28 | `inanc` | POST /api/inanclar | editBelief | `halk_id, ogul_id, ad, anlati, yanlis` | entity & son (unless 0); narrative | 0 | people's belief upserted | none |
| 29 | `ek` | POST /api/ek | editSuffix | `t, id, okunus, tamlama, sifirla` | — | 0 | Turkish suffix override | none — LANGUAGE-SPECIFIC: drop |
| 30 | `federasyon` | POST /api/federasyon | foundFederation | `uyeler[]`, `ad` | ≥2 living communities | 0 | federation faction, membership bonds, alliances, enmities closed | 'medeniyet': "{T} founded a federation: …" |
| 31 | `bag:ekle` | POST /api/baglar | addBond | `kaynak_tip, kaynak_id, hedef_tip, hedef_id, tur, aciklama` | valid type (not inside); endpoints v/o exist; not self; not duplicate | 0 | bond added | "established a bond between {a} and {b}: {label}." |
| 32 | `bag:sil` | POST /api/baglar/{id}/sil | removeBond | — | exists, active, not inside | 0 | bond inactive (history kept) | "broke the bond between {a} and {b}: {label}." |
| 33 | `kozmik:tutustur` (epoch.js kozmikEylem) | POST /api/kozmik/tutustur | rekindleStar | `yildiz_id` | star dead-type | `KOZMIK_BEDEL.tutustur` (other part) | star reborn, brightness 75, leak −20 on its worlds | 'gok': "{T} rekindled {star}; light returned…" |
| 34 | (setting) | POST /api/ayar `ogul_dagitim` | — | 'otomatik' / 'elle' | — | 0 | enables/disables automatic son distribution (§11.1) | none |

### 12.2 God power (`tanriguc.js` via epoch.js wrappers; all require a world)

| # | Ledger key | Endpoint | Inputs | Validation | Cost | Effects (summary; full logic §2) | Chronicle |
|---|---|---|---|---|---|---|---|
| 35 | `oz_em:ogul` | POST /api/ogullar/{id}/oz-em | — | living son with essence | 0 (gain) | −50% son essence, 80% to creator; son −10 loyalty, +15 anger, −5 existence; siblings +3 loyalty; reputation traces | drain template |
| 36 | `yut:ogul` | POST /api/ogullar/{id}/yut | `sebep` | living son | 0 (gain essence + 3×might + 20×level) | son dies (corpse, order…); siblings +10 loyalty, friends +25 anger; traces | "{T} devoured his son {s}…" |
| 37 | `oz_em:olumlu` / `yut:olumlu` | POST /api/varliklar/{id}/oz-em | `yut` bool | canon named mortal; life > 0 for drain | 0 (gain life/10 [+2×power]) | drain: life −50% (min 1), tag essence-drained; devour: certain death | drain/devour lines |
| 38 | `hasat` | POST /api/varliklar/{id}/hasat | — | canon community with population or faith | 0 (gain victims/500 + faith lost) | −10% population, −20 faith; patron sons −8 loyalty | harvest line |
| 39 | `oz_em:yabanci` | POST /api/yabanci/{id}/oz-em | — | not dead; power > 0 | 0 (gain 3/power point) | −30% power (≥1), −20 attitude; defeated at 0 | 'yabanci_tanri' line |
| 40 | `oldur:yabanci` / `yut:yabanci` | POST /api/yabanci/{id}/oldur | `sebep`, `yut` | not dead | `fg_kill_base + power×fg_kill_power%` (×2 if immortal power) | dead; worshippers 50% → creator else godless; devour gains 3/power point | 'yabanci_tanri' line |
| 41 | `dirilt:olumlu` | POST /api/varliklar/{id}/dirilt | — | dead named mortal, not deified | 40 + 2×power level | revived (life ≥50, lifespan +20 if old age), tag returned-from-death | "{T} called {v} back from death…" |
| 42 | `tanrilastir` | POST /api/varliklar/{id}/tanrilastir | — | canon named mortal; name not used by a son | 150 | new son (rarity by power ≤ legendary, loyalty 80…); mortal dies with tag deified; worshippers follow | 'yukselis' line; publishes `yeni_ogul` |
| 43 | `alcalt` | POST /api/ogullar/{id}/alcalt | — | living son above lowest class | 40 | class −1, stats capped, −15 loyalty, +25 anger; traces | demote line |
| 44 | `guc_sok` | POST /api/ogullar/{id}/guc-sok | `sira` (power index) | living son; valid index | 30 (then +15 gain) | power removed; +20 anger; traces | strip line |
| 45 | `mutlak_buyruk` | POST /api/ogullar/{id}/mutlak-buyruk | `emir` (≤600) | living son; non-empty | 25 | son.command set, irrefusable flag; −5 loyalty | 'emir' line |
| 46 | `peygamber` | POST /api/varliklar/{id}/peygamber | — | canon named mortal, not already prophet | 20 | +15 charisma, tag prophet, worships creator, community +10 faith | prophet line |
| 47 | `tezahur` | POST /api/varliklar/{id}/tezahur | `soz` (≤600) | canon mortal or community; non-empty | 10 | manifestation message, +10 faith, tag saw-the-god, 30% becomes creator worshipper | manifestation line |
| 48 | `soy_laneti` / `soy_laneti:kaldir` | POST /api/varliklar/{id}/soy-laneti | `kaldir` bool | canon root not already cursed / curse exists in line | 40 / 20 | curse 6 generations (−10 key stats, tags) / lift | curse / lift line |
| 49 | `cevir` | POST /api/varliklar/{id}/cevir | — | canon community or mortal not already solely the creator's | 30 | old worship closed (−10 loyalty to those sons), worships creator | conversion line |
| 50 | `gazap` | POST /api/varliklar/{id}/gazap | `sebep` | canon, not region, not mortal | 60 + 5×power level | 70% of named mortals inside die; contents moved up; record destroyed (`yok_edildi`) | wrath line |
| 51 | `gazap:dunya` | POST /api/dunyalar/{id}/gazap | `tur` disaster | world exists, not forgotten; has regions | 200 | disaster at 60% on every region + events | world wrath line |

### 12.3 Death, prayers, council, reputation, goals (epoch.js / konsey.js / itibar.js / hedef.js)

| # | Ledger key | Endpoint | Inputs | Validation | Cost | Effects | Chronicle |
|---|---|---|---|---|---|---|---|
| 52 | `tanri_can_al` | POST /api/varliklar/{id}/can-al | `nasil` (≤600) | living named mortal | `DEATH.god_kill_mortal` = 15 | certain death even if immortal (§5.1 `certain`) | "{T}'s hand…" via mortal death path |
| 53 | `ogul_oldur` | POST /api/ogullar/{id}/oldur | `sebep` | son exists, not dead | `DEATH.god_kill_son` = 100 | son dies (corpse, resurrection order); siblings +10 loyalty, friends +15 anger | god-death lines |
| 54 | `dirilt` | POST /api/ogullar/{id}/dirilt | — | son is dead | `DENGE.dirilis` = 150 | resurrection by the god's hand (derin.dirilt; no waiting) | resurrection lines (other part) |
| 55 | `dua` | POST /api/dualar/{id}/cevap | `metin`, `oz` | message to the creator exists; not already answered; 0 ≤ oz ≤ `GOD_ACTION.prayer_essence_cap`(100) (GOD_ACTION = rule domain `TANRI_EYLEM`, epoch.js) | `oz` (gift) | **mortal prayer**: §1.6 (faith +10, stats +oz/3, worships creator, dream reply, mood −10 loneliness +3 contentment). **Son prayer**: son essence += oz (≤ ozMax); loyalty += (text ? `GOD_ACTION.prayer_loyalty`(4) : 0) + floor(oz / `GOD_ACTION.prayer_essence_loyalty`(10)); existence += `GOD_ACTION.prayer_existence`(3); answer message t→o intent 'cevap' if text. Message marked answered+read. | mortal: "{T} heard {v}'s prayer{ and sent down his grace}."; son: "{T} answered {s}'s prayer{ and gave him {oz} essence}." |
| 56 | (not ledgered; lock 'konsey') | POST /api/konsey (background job) | `konu` (optional question) | ≥2 active/asleep sons | `DENGE.konsey` = 20 (refunded if it fails) | §7.3 council | 'konsey' line |
| 57 | `ruya` | POST /api/varliklar/{id}/ruya | `metin` | canon thinking entity; 5 ≤ length ≤ 600 | `DENGE.ruya` = 8 | dream message (read by the mortal agent; prioritizes it) | "{T} sent {v} a dream." |
| 58 | (not ledgered) | POST /api/ogullar/{id}/sohbet | `metin` (≤800) | son exists, not dead | 0 | LLM reply; loyalty ±≤6; chat history saved | none |
| 59 | (not ledgered) | POST /api/cevir | `dil_id`, `metin` | language exists | 0 | LLM translation; ≤6 new dictionary words | none |
| 60 | `itibar` | POST /api/ogullar/{id}/itibar | `sevgi, korku, unutma` deltas | son exists, not dead; some axis changes | 0 | manual reputation push (±60 cap, decays 60%/epoch) | none |
| 61 | `tanri:tutku` | POST /api/tanri/tutku | `tutkular[]`, `otomatik` | 1–3 known passions unless automatic | 0 | sets passions (or back to automatic) | "{T} revealed himself: his passions are …" |
| 62 | `senaryo:basla` | POST /api/senaryolar | `anahtar` | known; not running | 0 | scenario started | "{T} set himself a goal: {name}." |
| 63 | `senaryo:birak` | POST /api/senaryolar/{id}/birak | — | running | 0 | scenario abandoned | none |
| 64 | (setting) | POST /api/ayar `konsey_sikligi` | int ≥ 0 | — | 0 | auto-council every N epochs (0 off) | none |

Read-only endpoints in this part: `GET /api/hedefler`, `GET /api/tanri/itibar`, `GET /api/konseyler`, `GET /api/ogullar/{id}/sohbet`, `GET /api/firsatlar`, `GET /api/dualar`, `GET /api/dunyalar/{id}/rehber`, `GET /api/kozmik-kronik?son=N`, `GET /kitap[?ogul|varlik]`, codex export. Per-entity UI prices: son detail exposes resurrection state and `god_kill_son`; mortal detail exposes `{son_cost: killCost, ...killChance, god_cost: god_kill_mortal}`.

---

## 13. Epoch-transition wiring (where per-epoch functions run)

Within the world simulation (sim.js `dunyaMotoru`, cooperative generator steps):
- step 2c: `resourceMechanics(epoch, note)` then `cosmicEconomy(epoch, note)`;
- step 2f': `deathEngine(epoch, note)` (after foreign gods' engine, before civilization).

Within the epoch transition (sim.js `cagGecisi`), in this order after: rebels steal essence → doomsday line items (incl. `cultEffect().doomsday`) → essence income (incl. `cultEffect().essence` outside the cap) → epoch stats → `world.cag = newEpoch`, "Epoch N began" chronicle:
1. `creatorEpoch(oldEpoch, newEpoch, notes)` (§1.4–1.5)
2. `godPowerEpoch(oldEpoch, newEpoch, notes)` (§2.7)
3. `reputationEpoch(notes)` (§3.6)
4. `goalsEpoch(notes)` (§4.4)
Each wrapped in try/catch (an error in one must not abort the transition) and followed by a cooperative yield.

Epoch runner (epoch.js): `distributeSons(cag, publish)` each epoch (if automatic); auto-council `convene({caller:'kader'})` once per epoch when `cag % konsey_sikligi == 0` (before Fate's judgement stage; a crash is not retried on resume).

Startup repair (onarim.js): `repairContainment()`.

---

## 14. Known bugs and design smells (and how the new design should avoid them)

1. **Free-text regex as data.** Reputation love/fear events, the creator's passions, achievement "rebellion suppressed", scenario "loyal pantheon" rebellion detection, achievement "saga completed", and the per-epoch drain counter all grep Turkish chronicle text. → Give every chronicle/ledger row a structured `kind` (e.g. `bless`, `forgive`, `answer_prayer`, `resurrect`, `grant_star`, `ascend`, `lightning`, `chain`, `exile`, `suppress_rebellion`, `curse`, `drain`, `rebellion_declared`, `expedition_success`) and drive all these from kinds; keep a kind→passion mapping table.
2. **Achievement `dirilis` fires on the first resurrection *rite*/scheme/bone-scattering**, because olum.js writes chronicle type `dirilis` for those too; the description says "a dead son was resurrected". → Use a dedicated `son_resurrected` event.
3. **Dead rules**: `DEATH.rite_devotion` (ayin_adanmislik) and `DEATH.rite_cost` (ayin_refah) are declared and shown in the UI but never used. `DEATH.kill_refund` is applied in tools.js only. → Remove or wire them; don't expose dead knobs.
4. **Unwindowed unanswered prayers** in the mood update (loneliness) vs windowed+decayed in reputation. Old prayers pin loneliness forever (capped at 10/epoch). → Use the same window/decay.
5. **Spontaneous god acts count as "the god acted"**: spontaneous drains/curses/prophets are chronicled as `tanri` (some) at the new epoch, so the next epoch's mood update treats them as player actions (interest/contentment rise without the player acting). → Count only ledger entries with `who = creator` and `source = player`.
6. **Inconsistent "war" definitions**: mood uses ongoing war events; goals/achievements use any active `dusman` bond (including individual mortals' enmities); peace scenario may never complete in a busy world. → One shared `ongoing_wars()` definition (or explicit, named variants).
7. **Dual worship**: `worshipCreator` never closes other worship bonds, while `assignPatron` enforces a single patron. "Only you" checks are therefore ad hoc. → Decide the rule (see §15) and enforce it in one place.
8. `assignPatron(null)` leaves the entity without worship but does not add the `tanrısız` tag (other paths tag godless). → Consistent godless tagging (better: derive "godless" from bonds instead of a tag).
9. **Deify copies inactive worship bonds** (query lacks `aktif=1`), so long-gone worshippers suddenly worship the new god. → Copy active bonds only.
10. **Sibling scheme relationship bonus** always uses `sibling_rite_devotion/2` regardless of kind. → Separate rule or per-kind value.
11. **Wrath kills only mortals located directly in the record**, not nested deeper (e.g. a settlement inside a destroyed people). → Walk the containment tree.
12. **Two `harca` (spend) implementations** (epoch.js and tanriguc.js) with slightly different messages. → One essence service with `spend/gain/refund` and rule-named errors.
13. **Opportunity tool filtering by regex surgery on prose** (and tension ordering by keyword regex). → Build lines from structured parts `{text, tools[], tension:bool}`, render after filtering.
14. **Reputation is recomputed many times** (every `/api/state` poll calls `godReputation()` → per son queries). → Cache per epoch + invalidate on relevant actions.
15. **`manual_min` (elle_esik) doubles as the trace drop threshold**. → Separate `trace_min` rule.
16. **Scenario points stack** if the same scenario is completed repeatedly (score sums every completed row). → Decide (see §15).
17. **Council member selection** = first N sons in table order, not by relevance (asleep sons may crowd out active ones). → Prefer active, then by involvement in the agenda.
18. **Book is rendered synchronously in one request** for the entire world (all chronicle rows, dictionaries up to 100k words). → Stream or paginate; generate in a background job and cache by epoch.
19. **`deleteStar` hard-deletes** (undo relies on the ledger capturing the row). → Soft delete.
20. **Manual mood set (`setGodMood`)** keeps the stale `girdi` breakdown and is not chronicled/ledger-visible beyond the ledger key. → Clear breakdown, note it.
21. Wrath sign candidate pre-filter by place id plus a second filter by entity id is redundant; `struck` includes event ids. Harmless; simplify.
22. **LANGUAGE-SPECIFIC code to drop**: Turkish number words (`yazi`, `SIRA`, council `sayiSozu`), suffix-harmony fixer (`ekDuzelt`, `ekBilgisi`, `editSuffix`/`POST /api/ek`, `ekSozluguYenile`), `toLocaleLowerCase('tr')`/Turkish collation, apostrophe-suffix templates.
23. **Chronicle templates rely on random choice** (`Math.random`) everywhere — tests had to stub randomness. → Inject an RNG (seedable) into all engine modules.
24. Many engine functions silently swallow errors (`catch {}`) in loops (rites, schemes, wrath deaths). → Log at least at debug level with the entity id.

---

## 15. Open decisions for the integrator

1. **Single vs multiple worship**: may an entity worship the creator *and* a son simultaneously (current `worshipCreator` behaviour), or is worship exclusive (current `assignPatron` behaviour)? This affects cult faith, kill resistance, "one faith" scenario and opportunities.
2. **Passions source**: confirm replacing chronicle-regex passion reading with a structured action-kind → passion mapping (needs a mapping table; proposed from the regex lists in §3.3).
3. **Achievement "Return from death"**: trigger on actual son resurrection only (recommended) or keep current behaviour.
4. **Scenario repeat scoring**: should completing the same scenario again add its points again?
5. **Unanswered prayers in mood**: window+decay like reputation (recommended) or keep all-time.
6. **Dead knobs** `rite_devotion`, `rite_cost`: remove, or make spontaneous rites use them (would change balance: currently spontaneous rites use prayer=4 / wealth=10).
7. **Book/Codex formats**: keep the printable HTML book (browser → PDF) and the Markdown codex as two exports, or merge into one export pipeline (e.g. HTML + server-side PDF)?
8. **Auto-council cost and frequency**: auto councils are free (caller Fate) every 4 epochs and each is an LLM call of up to 240 s; confirm default frequency for the new app.
9. **"War" definition** shared by mood, goals and achievements (§14.6): events vs bonds.
10. **Turkish ordinal/number naming** in achievement names (e.g. "{ordinal} sky") — render with English ordinals.
