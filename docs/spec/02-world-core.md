# 02 — World Core: Accessors, Helpers, Maintenance, Persistence Services

Old files covered: `src/db.js`, `src/world.js`, `src/denge.js`, `src/bosdunya.js`, `src/gercek.js`, `src/degisim.js`, `src/akis.js`, `src/arsiv.js`, `src/onarim.js`, `src/lore-onar.js`, `src/kronik-onar.js`, `src/etiket-onar.js`, `src/ekonar.js`, `src/agonar.js`, `src/kesif.js`, `src/paylasim.js`, `src/sihirbaz.js`, `src/toplu.js`, `src/bildirim.js`, `src/olcum.js`, `src/defter.js`. Related helpers in `src/derin.js`, `src/ekonomi.js`, `src/ufuk.js` are summarized where the repair passes call them. Startup wiring is in `server.js`.

Schema and enums: see `01-data-model.md` (referenced as "01 §x").

Conventions used below:
- `Y` = years per epoch = rule `ZAMAN.cag_yil` (default 50).
- "canon-ish" = status in (`kanon`, `olu`, `gerceklesti`).
- "world of x" = `COALESCE(x.dunya_id, 1)`.
- Every number tagged `RULE AREA.key` is a tunable world rule (§3). Rule tables are given per module.
- **LANGUAGE-SPECIFIC** marks Turkish grammar logic that will not be ported. What it did is still explained.

---

## 1. Module map and cross-references

| Old module | Responsibility | Main callers |
|---|---|---|
| `db.js` | connection, schema, migrations, triggers, transactions, logging, backups, restore, WAL checkpoint | everything |
| `denge.js` | world-rule registry (`tanimla`), override persistence, rule list/edit API | every module that defines rules; `server.js` `/api/denge` |
| `world.js` | accessors, canon cache, chronicle writer, bonds, names, faith, languages, prompt context builders, text cleaners, tired motifs, rename, turn-context serialization | agents, tools, engine (`sim.js`, `derin.js` …), epoch, server |
| `gercek.js` | deterministic canon facts | Fate pipeline (`agents.js`), server startup |
| `bosdunya.js` | empty-but-habitable world detection (+ rules) | son distribution (`epoch.js`), opportunities (`firsatlar.js`), native-people guarantee (engine) |
| `degisim.js` | change feed for incremental UI refresh | server `/api/degisim`, `/api/state` |
| `akis.js` | live-feed categorisation by text | `bildirim.js`, UI |
| `arsiv.js` | importance score, archive ("history") layer | server (atlas list, gallery), epoch end |
| `onarim.js` + `lore-onar.js` + `kronik-onar.js` + `etiket-onar.js` + `ekonar.js` + `agonar.js` (part) | idempotent startup data repairs | `server.js` startup |
| `agonar.js` | knowledge-network health, rule-based dangling-end repair, LLM bond suggestions | epoch end (`epoch.js`), server `/api/ag/*` |
| `kesif.js` | map/wiki helpers: political control, roads, snapshots, map notes, pathfinding, similar entities, merge, favourites, notes, settlement tiers, event markers | server, engine (snapshot at epoch end) |
| `paylasim.js` | export / import (`.aerona` package), read-only discovery mode | server |
| `sihirbaz.js` | genesis wizard options and templates | genesis (`agents.js`), server |
| `toplu.js` | bulk deepening job | server `/api/toplu/derin*` |
| `bildirim.js` | notification centre | `world.addKronik`, epoch, server |
| `olcum.js` | LLM metrics, epoch ETA | `llm.js` hook, server |
| `defter.js` | undo ledger (action-level change capture and selective undo) | `llm.js` tool wrapper, `epoch.defterli` (creator actions), server |

---

## 2. Database access layer (`db.js`)

### 2.1 Query helpers

- `q.all/get/run(sql, ...params)`: prepared statements. `undefined` params become `NULL`.
- `parseSon(row)`, `parseVarlik(row)`, `parseKronik(row)`: decode JSON columns with defaults (sons: `kisilik {}`, `statlar {}`, `tutku {}`, `gucler []`, `varolus null`, `destan null`, `itibar*`/`ek` null; `zincirli` becomes bool. Entities: `statlar {}`, `etiketler []`, `derinlik null`, `bekliyor` becomes bool. Chronicle: `varlik_ids []`).

### 2.2 Transactions

- `tx(fn)`: if a transaction is already open, run `fn` inside it (join). Otherwise `BEGIN` → `fn` → `COMMIT`, with `ROLLBACK` on throw.
- `sonunaKadar(gen)` (run to completion): drives a generator synchronously and returns its return value.
- `txNefesli(gen, name)` ("breathing" transaction): `BEGIN` unless one is already open. After each `yield` it waits one macrotask (`setImmediate`) so the HTTP server stays responsive. HTTP requests served meanwhile **join the open transaction**. `COMMIT` at the end; on error, `ROLLBACK` and prefix the error message with `name`. An optional step profiler `adimOlcer(f)` receives `(stepName, ms)`.
- **Rewrite**: the async Python backend should run the long engine pass in a dedicated writer task with explicit, chunked transactions. Never let unrelated HTTP writes join an engine transaction (that is a source of subtle corruption and of rollbacks wiping user actions).

### 2.3 Logging

`data/log/aerona.log`: lines are `ISO-timestamp LEVEL message`, and continuation lines are indented. Levels are `BILGI` (info), `UYARI` (warn), `HATA` (error). The file rotates at 5 MB into `.1` … `.3`. The last 30 warnings and errors are kept in memory (`SON_HATALAR`, each text ≤2000 chars) for `/api/saglik` (health). Write failures are swallowed.

### 2.4 Checkpoint

`checkpoint()` runs `PRAGMA wal_checkpoint(TRUNCATE)` at epoch end and on SIGINT/SIGTERM/SIGHUP.

### 2.5 Planner statistics

`planIstatistikleri()` runs `ANALYZE` if `sqlite_stat1` is missing, otherwise `PRAGMA optimize`. It is called at startup and at epoch end.

---

## 3. World rules registry (`denge.js`) — "no unregistered constant"

Every balance number is a **world rule**: it has a dotted path `AREA.key`, a factory default, a min, a (soft) max, a group and a Turkish label. The player can override rules per world (Settings → World rules). Overrides are stored as `dunya.denge_ayar` JSON `{path: int}`.

### 3.1 `tanimla(area, defs, existingObj?)` (define)

- `area` must match `^[A-Z][A-Z0-9_]*$`.
- `defs = { key: [default, label, min=0, max=max(1000, |default|*10), group='Diğer'(Other)] }`.
- Returns a live object `area_obj` with `area_obj[key]` = saved override ?? default. If `existingObj` is passed (to break import cycles, e.g. `YEDEK_KOTA` in db.js, or the objects built in `rules.js` `ON_TANIMLAR`), that object is updated in place and registered.
- Registers `{label, min, max, group}` in `KAYIT` and `default` in `VARSAYILAN`. Defining the same area twice merges.
- Values are **integers**. Probabilities are stored as percents (use `/100`).
- Empty definitions (`tanimla('KORKU', {})`) are used to obtain a live reference to another module's area without a circular import.

### 3.2 Fixed (legacy) editable fields

Besides `tanimla` areas, these objects in `rules.js` are editable, with these bounds:

| Path pattern | Label | Min | Max |
|---|---|---|---|
| `COSTS.<k>` (summon 30, bless_essence 15, bless_hp 15, bless_stat 40, lightning 10, revelation 25, transform 15, bear_child 60, destroy 25, influence 6, curse 12, dream 10, incite 10, chosen 14, covenant 0, anchor 0) | per-key label (see table below) | 0 | 500 |
| `DENGE.<k>` (tanri_oz_yenilenme 20, oz_tavan 800, dirilis 150, dunya 120, dunya_dogur 70, konsey 20, ruya 8, uyandir 35, kiyamet_esik 100, kiyamet_hiz 100, bastir 20, baslangic_oz 150) | | 0 (kiyamet_esik: 1) | 1000 (oz_tavan: 100000; kiyamet_hiz: 300) |
| `KOZMIK_BEDEL.<k>` (yildiz 80, muhur 30, temizle 80, unut 20, gok 50, tutustur 60, ruh 15, sefer 30) | | 0 | 500 |
| `MUDAHALE_BEDEL.<k>` (mucize 15, afet 20, bilgi 12, lanet 15) | | 0 | 300 |
| `OLUMLU_AJAN.ap` (3), `.varsayilan` (4), `.maxTurns` (12), `.zeka_esigi` (55) | Mortal action points / Mortal agents per epoch / Mortal turn limit / Min intelligence of a creature playing as agent | 1/0/4/0 | 6/1000/20/100 |
| `OZELLIKLER.<trait>.savas` | "<trait> creature's war-power bonus" | 0 | 100 |
| `SEYAHAT_YONTEMLERI.<m>.sure` / `.tehlike` | "<method>: journey duration (epochs)" / "danger" | 1 / 0 | 20 / 100 |
| `GUC_SEVIYELERI.<i>` ([1,3,5]) | "Level at which the son's (i+1)th power unlocks" | 1 | 50 |
| `RARITIES.<r>.ap` / `.oz_yenilenme` / `.stat.0` / `.stat.1` / `.guc_tavan` / `.maxTurns` / `.agirlik` (not for mythic) | "<rarity>: action points / per-epoch essence regen / min stat on summon / max stat on summon / power level cap / son turn limit / summon weight" | 1/0/1/1/1/4/0 | 8/60/100/100/30/40/100 |

English labels for the `COSTS`/`DENGE`/`KOZMIK_BEDEL`/`MUDAHALE_BEDEL` keys (`AD` map): cagirma Son summoning; kutsa_oz Blessing (essence); kutsa_can Blessing (HP); kutsa_stat Blessing (stat); yildirim Lightning; vahiy Revelation; donustur Transform (son); evlat_dogur Bear a child (son); yok_et Destroy (son); etkile Influence (son); lanet Curse (son); ruya Dream (son); kiskirt Incite war (son); secilmis Declare chosen (son); ahit Covenant; capa Anchor; tanri_oz_yenilenme Creator's per-epoch essence; oz_tavan Creator essence soft cap; kiyamet_esik Doomsday threshold; kiyamet_hiz Doomsday speed (%; 0 = clock stops); dirilis Resurrection; dunya World creation; dunya_dogur World birthing (son); konsey Council; uyandir Awaken peoples; yildiz Kindle a star; muhur Seal a gate; temizle Cleanse leakage; unut Forget a world; gok Sky event; tutustur Rekindle a dead star; ruh Bind a spirit; sefer Legendary quest; mucize Miracle; afet Disaster; bilgi Teach knowledge; bastir Suppress uprising; baslangic_oz Creator's starting essence in a new cosmos.

Groups for these: COSTS/GUC_SEVIYELERI → "God and son costs"; DENGE → "Great acts and essence"; KOZMIK_BEDEL → "Cosmic acts"; MUDAHALE_BEDEL → "Intervention in the mortal world"; OLUMLU_AJAN → "Mortal agents"; RARITIES → "Rarity classes"; OZELLIKLER → "Creatures"; SEYAHAT_YONTEMLERI → "Cosmos and travel".

### 3.3 Operations

- `dengeUygula()` (apply rules): for every registered path, write `override ?? default` into the live object. It runs at load, after every edit, and on "world changed" (restore/import/reset).
- `dengeListesi()` (list rules): `[{yol, ad, grup, min, max, deger, varsayilan, degisti}]` (path, label, group, min, max, current value, default, changed), where changed = an override exists and differs from the default.
- `dengeAyarla(changes, {sifirla})` (edit rules):
  1. `sifirla` (reset) → start from `{}`; otherwise start from the saved overrides.
  2. For each `path → v`: unknown path → error "Unknown rule: <path>". `v === null` → delete the override. Otherwise `n = round(Number(v))`; non-finite → error "<path> must be a number."; `n < min` → error "<path> must be at least <min>." (**min is hard**); `!isSafeInteger` → error "<path> is too large." **Max is soft**: the UI shows a warning, but the server accepts any value. `n === default` → delete the override; else store it.
  3. Persist (NULL if empty), `dengeUygula()`, return the list.

### 3.4 Rules defined in this module

`YEDEK` (backups; updates `YEDEK_KOTA` in place):

| Key | English | Default | Min | Max | Group |
|---|---|---|---|---|---|
| `backup.epoch_keep` (`YEDEK.cag`) | Latest epoch backups kept | 10 | 1 | 200 | Backups |
| `backup.decade_every` (`YEDEK.onluk`) | Backups of epochs divisible by this are always kept | 10 | 1 | 100 | Backups |
| `backup.manual_keep` (`YEDEK.elle`) | Manual backups kept | 30 | 1 | 500 | Backups |
| `backup.safety_keep` (`YEDEK.guvenlik`) | Kept per safety-backup kind | 5 | 1 | 100 | Backups |
| `backup.secondary_keep` (`YEDEK.ikinci`) | Kept at the secondary target (`AERONA_YEDEK2`) | 20 | 1 | 1000 | Backups |

**Rewrite**: keep a single `RuleRegistry` with typed `RuleDef(key, default, min, max, group, label)`. Persist overrides in `rule_override`. Expose `rules.get("backup.epoch_keep")`. Make the soft max a UI hint only.

---

## 4. World accessors and the canon cache (`world.js`)

### 4.1 Accessors

| Function | Behaviour |
|---|---|
| `getWorld()` | `SELECT * FROM dunya WHERE id=1`, or null |
| `dunyaGerekli()` (require world) | throws "You need to create the world first." if none |
| `getSon(id)` / `allSons()` | parsed son(s), ordered by id |
| `getVarlik(id)` | parsed entity |
| `canonVarliklar()` | parsed entities with status canon/dead/fulfilled, by id |
| `kanonlar()` | parsed **canon-only** entities, by id (cached during engine runs, §4.2) |
| `modeller()` | `{...MODEL_VARSAYILAN, ...dunya.modeller}`. Defaults: every rarity key plus `kader`, `yaratilis`, `cagirma`, `derinlik`, `vahiy` → `haiku` |
| `modelFor(key)` | `modeller()[key] || 'haiku'` |
| `nameOf(tip, id)` | `o` → son name or `oğul#id`; `t` → creator name or "Tanrı" (God); `y` → foreign god name or `yabancı tanrı#id`; otherwise entity name or `#id` |
| `kapak(tip,id)` (cover) | cover image file name: `ORDER BY kapak DESC, id DESC LIMIT 1` |
| `cokDunya()` (multi-world) | `COUNT(dunyalar) > 1` |
| `dunyaBilgi(id)` | world row + `yildiz_ad`, `yildiz_tur` (star name, kind) |
| `cagYildizi(w)` | the epoch-star entity of world 1 (`w.cagin_yildizi`) |
| `yasalar(dunyaId?)` | canon natural laws (`tur='yasa'`), restricted to `dunya_id IS NULL OR = dunyaId` if given |
| `acikIplikler()` | open threads with `ilgili` parsed |
| `kiyametEsik()` | `DENGE.kiyamet_esik ?? 100` |
| `eylemHakkiVar(s)` (can act) | `(s.varlik ?? 60) >= KURAL.varlik_solgun` (12) |

### 4.2 Incremental canon cache

The engine calls `kanonlar()` dozens of times per step, and re-reading and parsing the whole table used to take half the engine time.

State: `KANON_ACIK` (nesting counter), `KANON_MAP: Map<id, entity>`, `KANON_DIZI` (sorted array), `KANON_SURUM` (version).

- `kanonOnbellek(true)` (open): installs (once per connection) the TEMP table `kanon_degisen(id PK)` and triggers that insert NEW.id / OLD.id on INSERT/UPDATE/DELETE of `varliklar`. It also installs TEMP `konum_surum(n)` (seeded with 0) and triggers that `n += 1` on INSERT, DELETE and `UPDATE OF konum_id, durum, tur`. Then it increments the counter and clears the map.
- `kanonOnbellek(false)`: decrements the counter (min 0) and clears the map.
- `kanonlar()`:
  1. Not open → full read (no cache).
  2. Map empty → clear the dirty table, load all canon rows into the map.
  3. Else read the dirty ids. If any: clear the table; for each chunk of `BAGLAM.kanon_parti` (500) ids, `SELECT * … WHERE id IN (…)`. For each id, if the row exists and is `kanon` put the parsed row in the map, else delete it from the map. Invalidate the array.
  4. If the array is invalid: rebuild it sorted by id and bump `KANON_SURUM`.
  5. Return a **shallow copy of the array** (objects are shared across callers; writers must persist via `saveStat` etc., and the trigger then re-reads them).
- `kanonSurumu()` → version while open, else null. `konumSurumu()` → `temp.konum_surum.n` while open, else null (used by region-memo caches in other modules).
- `kanonOnbellekSifirla()`: clear the map. Must be called after any rollback (e.g. a failed creator action inside a savepoint).
- Users: `sim.js` opens the cache around the engine pass and the epoch transition.

**Rewrite**: an identity map with a dirty set fed by the repository layer (no triggers needed). Invalidate on rollback.

### 4.3 Saving

- `saveSon(s)`: `UPDATE ogullar SET statlar, tutku, can=clamp(can,0,canMax), oz=clamp(oz,0,ozMax), inanc, un, xp, seviye, durum, uyku_kalan, zincirli(0/1), emir, son_eylem_cag, plan, yildiz(??1), varlik=clamp(varlik??60,0,100), capa_id, asi(0/1)`. `canMax = round(KURAL.can_taban + KURAL.can_dayaniklilik/100 * dayaniklilik)` (50 + 1.5×END). `ozMax = round(KURAL.oz_taban + KURAL.oz_kudret/100 * (kudret ?? KURAL.oz_kudret_varsayilan))` (40 + 1.6×MIGHT, might defaults to 20).
- `saveStat(v)`: `UPDATE varliklar SET statlar=? WHERE id=?`.

### 4.4 Location helpers

- `konumAgaci(limit = BAGLAM.kader_agac, dunyaId?)` (location tree): builds parent → children from canon-ish entities with status canon or dead, filtered to `dunya_id = dunyaId OR NULL` when given. It walks depth-first from the roots (konum_id NULL). At root level, location-less types (`konum=[]` in the taxonomy) are skipped. Each line is `"  "*depth + "- " + entityLine` (with the " · in X" part stripped), stopping at `limit` lines. Returns `{agac (text), konumsuz (location-less root list), toplam (count), kesildi (truncated)}`.
- `varlikSatir(v)` (entity line): `#<id> <name> (<type label>[/<subtype>], G<power>)[ · <location name> içinde][ [<status>]]`. Rewrite in English as `#id Name (Type/subtype, P5) · in <Location> [dead]`.

---

## 5. Chronicle writing

### 5.1 `addKronik(cag, ogul_id, tur, metin, ids=[])` → id

1. `text = suffixFix(repetitionFix(scrubIds(metin)))`:
   - `kimlikTemizle` (ID scrub, §12.1) removes "#12", "oğul#3", "iplik:108'i" style leaks.
   - `yinelemeDuzelt` (template-repetition fix): a capitalized word followed by a lowercase word with the same stem collapses into one when the stem is a record-type word (prophecy, knowledge, language, remnant(s), tradition, legend, war, coin, cult, law, army, caravan, uprising, plague, temple, ruin, tale, epic, rite). Example: "Kum Dili dili" (Sand Language language) → "Kum Dili". **LANGUAGE-SPECIFIC (stemming)**. In English, implement a simpler "Name Type type" duplicate-word collapse, or drop it.
   - `ekDuzelt`: Turkish suffix harmony. **LANGUAGE-SPECIFIC: drop.**
2. `INSERT INTO kronik (cag, ogul_id, tur, metin, varlik_ids, yil)` with `yil = kronikYili(cag)` (§5.2).
3. Notification hook: `bildirim.kronikten({id, cag, ogul_id, tur, metin, ids})` (§25). Errors are swallowed.

Cross-refs: almost every module writes chronicle lines through this. `kronik_varlik` is filled by trigger (01 §4).

### 5.2 In-world year of a chronicle line

The epoch is split into phase windows (rules `CAG_AKIS.yil_*`, defined in the epoch module): sons' turn years 0–`yil_ogul` (15), mortals' turn 15–`yil_olumlu` (30), the world engine 30–`yil_motor` (45), Fate and chronicler 45–`yil_kader` (49). After the transition, the new epoch's first years run 0–`yil_gecis` (4). The epoch runner calls `yilAraligi(start, end, cag=currentEpoch)` at each phase start.

```
kronikYili(cag):
  w = world; base = w.yil - (w.cag - cag) * Y            # start year of that epoch
  drop SON_YIL entries with key < cag - 2                  # SON_YIL: Map<epoch, last year used>
  [b, s] = (YIL_CAG != null and cag > YIL_CAG) ? [0, 1] : YIL_ARALIK
         # a line written into a newer epoch than the configured window gets that epoch's first year
  y = min(base + max(0, Y-1),
          max(SON_YIL.get(cag) ?? base,
              base + b + floor(random() * max(1, s-b) / 3)))
  SON_YIL[cag] = y
  return y
```

Properties: years never go backwards within an epoch (monotone per epoch). Writing to a past epoch does not disturb the current one's sequence. The `/3` factor makes years advance slowly within the window.

### 5.3 Prompt-safe chronicle (`sonKronik`, `istemMetni`)

`sonKronik(n = BAGLAM.kronik_sayi, dunyaId?)` (recent chronicle):
- Multi-world with `dunyaId` → select non-`motor_ham` rows where: (if the row references existing entities) **all** referenced entities are in that world; (else if it has a son) the son's `aktif_dunya` (default 1) equals the world; (else) the world is 1. `ORDER BY id DESC LIMIT n`.
- Otherwise the last `n` rows of any kind.
- Output oldest-first, formatted `[Çağ <cag>] <istemMetni(metin)>` (`[Epoch N] …`).

`istemMetni(m)` (prompt text) strips game numbers so models narrate events, not numbers:
- "from 90 to 20" stat transitions (Turkish `X'dan Y'ye`) are removed;
- "<stat> fell/dropped/receded to N" → "<stat> decreased"; "rose/increased to N" → "<stat> increased";
- dice scores "(122–94)" are removed;
- "N hp|essence|fame|xp|faith|action" → the bare noun;
- double spaces and spaces before punctuation are collapsed.

In English, implement the equivalent regexes for "from X to Y", "fell to N", "rose to N", "(N–M)", "N essence" etc. The patterns themselves are **LANGUAGE-SPECIFIC**; the intent (no numbers in narrative prompts) carries over.

---

## 6. Bonds

### 6.1 `addBag(kt, kid, ht, hid, tur, aciklama, cag)` → bond id

```
[kt,kid,ht,hid] = bagYonu(kt,kid,ht,hid,tur)                     # §6.3 direction normalization
ac = aciklama ? suffixFix(aciklama) : null
if kt=='v' and ht=='v' and not bagUcuGecerli(kid,hid,tur):        # §6.2
    return addBag(kt,kid,ht,hid,'ilgili', f"{tur}: {ac}" if ac else tur, cag)   # downgrade to narrative "related"
if tur not in OLAY_BAGLARI:                                        # state bond → unique
    role = tur in {'taraf','ilgili'}
    e = first active bond with same (kt,kid,ht,hid,tur) [and COALESCE(aciklama,'') == ac or '' if role], by id
    if e: if not role and ac and ac != e.aciklama: update e.aciklama = ac
          return e.id
if tur=='dusman' and kt==ht=='v':
    deactivate active 'muttefik' and 'ticaret' v-v bonds between kid and hid (either direction)
if tur=='yonetir' and kt==ht=='v' and kid is a mortal ('olumlu'):
    deactivate other active 'yonetir' bonds onto hid whose source is a mortal other than kid     # single throne
insert (kt,kid,ht,hid,tur,ac,cag) with aktif=1; return new id
```

`OLAY_BAGLARI` (event bonds, never deduplicated): dovdu, oldurdu, lanetledi, kutsadi, yok_etti, neden_oldu, gocetti, kesfetti, kehanet_eder.

### 6.2 Endpoint validity (`bagUcuGecerli(kid, hid, tur)`)

True if the type has no rule, or if either entity is missing. Otherwise: subject type ∈ `BAG_OZNE[tur]` (if defined) AND object type ∈ `BAG_NESNE[tur]` (if defined). The tables are in 01 §7.2.

### 6.3 Direction normalization (`bagYonu`)

- `tapar` with o→v → flip to v→o.
- If `BAG_YONU[tur]` exists and both are entities: let `a` = source type and `b` = target type. If `a ∈ rule.nesne AND b ∈ rule.ozne AND NOT (b ∈ rule.nesne AND a ∈ rule.ozne)` → swap. The table is in 01 §7.2.
- `bagTersMi(b)` (is reversed): true if normalization would change source or type.

### 6.4 Queries

- `bagVar(a, b, tur)` (bond exists): active v-v bond of `tur` between a and b in either direction.
- `ahitVar(x, y)` (covenant exists): active o-o `muttefik` bond either way.
- `bagSatirlari(tip, id)` (bond lines, for prompts): outgoing lines are `→ <label> <target prefix><name>[ — <desc>]`, where the prefix is `oğul#id ` for a son, "yabancı tanrı " (foreign god) for y, "yaratıcı " (creator) for t, or `#id ` for an entity. Incoming lines are `← <source prefix><name> <label>[ — <desc>]`. Active bonds only.
- `GORUNUR_BAG` (visible bond predicate): 01 §7.4.

### 6.5 Patron god

- `hami(v)` (patron): the son that `v` worships (`tapar` v→o, first found), else `v`'s creating son, else null.
- `yabanciHami(v)` (foreign patron): the foreign god row `v` worships (`tapar` v→y), or null.

### 6.6 Location bonds

- `konumBaginiTazele(id, konumId, cag)` (refresh location bond): deactivate active `icinde` v→v bonds from `id` whose target ≠ `konumId`, **except** those with description "ruh kaplama" (spirit binding, which is not a location). Then, if `konumId` is set and ≠ id, `addBag(v,id,v,konumId,'icinde')` (deduplicated).
- `icindekileriDevret(oldId, newId, cag, {yalnizKanon})` (hand over contents): when a place is destroyed or rejected, its contents move to its parent. Contents with status canon/fulfilled (and `kanon` only if `yalnizKanon`) are collected. `konum_id` is set to `newId` for all rows located in `oldId` (honouring `yalnizKanon`), and the location bond of each living one is refreshed. Dead entities keep their historical bonds. Returns the count of living contents moved.

---

## 7. Names: uniqueness, similarity, rename

### 7.1 Normalization (`aramaNorm`)

Lowercase with Turkish locale, then fold `ı`/`i̇` → `i`, and `â à` → a, `î ì` → i, `û ù` → u. **LANGUAGE-SPECIFIC** (Turkish dotless i). In English, use `casefold()` plus NFKD accent stripping.

### 7.2 Cosmos-wide uniqueness

The name pool is: entities with status ≠ rejected, ∪ sons, ∪ stars, ∪ worlds, ∪ foreign gods.
- `isimAlinmis(ad)` (name taken): any `aramaNorm(name) == aramaNorm(ad)`.
- `benzersizAd(ad)` (make unique): `kok = spellingFix(trim(ad))` (**LANGUAGE-SPECIFIC** `yazimDuzelt`, e.g. "Ilk" → "İlk"). Load the normalized pool once. Try `kok`, then `"kok II"`, `"kok III"` … (Roman numerals via `ROMA(n)` for 1–3999) until free. Return it.

### 7.3 Indistinguishable names (`benzerAd(ad, {aile, adlar})`) (similar name)

Only for single-word names (any whitespace → return null).
1. If `len(ad) ≤ DIL.benzer_uzunluk` (7): for every pool name `t` that is single-word, has `len(t) ≤ 7+1`, and is not normalization-equal: if the Levenshtein distance (normalized; early exit 2 if the length difference is >1) is ≤1 → return `t` (e.g. "Lemir" vs "Lesir").
2. If `aile` (family) and `len(ad) ≥ DIL.kok_harf` (4): prefix = first 4 normalized letters. If the count of single-word pool names with the same prefix is ≥ `DIL.aile_tavani` (3) → return the first such name (blocks "Lenmir, Lenmas, Lenmur…" families).
3. Else null.

Callers (tools, Fate) reject or rename the new name when a similar one is found.

### 7.4 Rename everywhere (`adDegistir(id, newName, {cagBas, tip='v'})`)

Purpose: renaming an entity (or a son with `tip='o'`) must update every text that mentions the old name.

1. Load the row; if missing, the name is empty, or it is unchanged → `{degisen:0}`.
2. `korunan` (protected) = names of other entities and sons that **contain** the old name (e.g. renaming "Ash Tower" must not touch "Ash Tower Guards").
3. In one transaction (joins an existing one):
   - `UPDATE <table> SET ad=new, ek=NULL`. Refresh the suffix dictionary (LANGUAGE-SPECIFIC).
   - For each text field in `AD_ALANLARI` (kronik.metin; kronik_bakis.metin; caglar.anlati/ozet; caglar_dunya.anlati/ozet; varliklar.aciklama/kader_notu; varliklar.derinlik (JSON); baglar.aciklama; iplikler.metin/kapanis; halk_inanc.anlati/yanlis; sozluk.koken/ornek; gercekler.nesne/iliski), skipping tables or columns that do not exist: select rows where the column contains the old name. If `cagBas` (from epoch) is given, rows of chronicle, historian views and epoch narratives are restricted to `cag >= cagBas` (used for temporary names). Replace with `adMetinde`. For JSON fields, replace only string values, recursively. Write each changed row; count them.
4. Return `{eski, yeni, degisen}` (old, new, changed).

`adMetinde(text, old, new, protected)` (name in text):
- Protected names that contain `old` are masked (longest first; word-boundary regex `(?<![\p{L}\p{N}])name(?![\p{L}\p{N}])`) with placeholders `\0<i>\0`.
- Replace `old` at word boundaries, **unless** it is followed by a Roman-numeral/number suffix (`\s+(I{1,3}|IV|VI{0,3}|IX|X{1,3}|\d+)` not followed by a letter or digit), because "Name II" is a different record.
- Unmask.
- In the old code each changed string also went through `ekDuzelt` (LANGUAGE-SPECIFIC).

### 7.5 Dialect (phonology) checks

Each world has a naming rule (`dunya.isim_kurali` for world 1, `dunyalar.lehce` for others).
- `isimKurali(dunyaId)` (naming rule): the dialect of world ≠1 if set, else the world-1 rule.
- `lehceBlogu(w)` (dialect block, for multi-world prompts without a specific world): see §11.2.
- `lehceUnluleri(text)` (dialect vowels): parse allowed vowels from rule text such as "Vowels are a, e, i and o" (regex: the word for "vowel", then within 40 chars, 2–8 single vowel letters separated by commas/"ve"/"ile"/"ya da"). Returns the set if ≥2 vowels, else null. **LANGUAGE-SPECIFIC regex**. In the rewrite, store the phonology structurally (`allowed_vowels`, `allowed_consonants`, `forbidden_sounds`) instead of parsing prose.
- `lehceIhlali(ad, dunyaId)` (dialect violation): for each word of the name (split on whitespace, comma, apostrophe, hyphen): skip if its 4-letter prefix is a known "real Turkish word" stem (computed from lowercase words appearing ≥`DIL.turkce_en_az` (3) times in the last `DIL.turkce_pencere` (3000) descriptions; cached per epoch) or if shorter than `DIL.lehce_kok_en_az` (3). Collect the vowels not allowed by the dialect. Returns `[{kok, yasak:[vowels]}]`. In English: real-word detection becomes a dictionary check. The concept (invented names must follow their world's phonology; ordinary words are exempt) is portable.

---

## 8. Faith computation and acting gate

`inancHesapla(sonId)` (compute faith) is called by the engine each epoch to set `ogullar.inanc`:

```
total = 0
for each active bond (v → o:sonId, 'tapar'):
    v = entity; skip unless v.durum == 'kanon'
    if v.tur == 'tarikat':  # cult
        total += max(INANC.topluluk_en_az, (murit or 0) / INANC.murit_bolen * (1 + (etki or 0)/100))
    elif v.tur in ('halk','yerlesim'):   # people / settlement
        piety = v.statlar.inanc ?? INANC.dindarlik       # 0 piety counts as 0 (not as unknown)
        total += max(INANC.topluluk_en_az * sign(piety), (nufus or 0) / INANC.nufus_bolen * piety/100)
    else:
        total += INANC.diger
if son has unlocked power 'inanc_carpani': total *= INANC.carpan / 100
return round(total)
```

Rules `INANC` (group "Religion and language"):

| Key (new) | Old | English | Default | Min | Max |
|---|---|---|---|---|---|
| faith.followers_per_point | murit_bolen | Faith: 1 point per this many cult followers | 50 | 1 | 100000 |
| faith.population_per_point | nufus_bolen | Faith: 1 point per this many pious population | 2000 | 1 | 10000000 |
| faith.default_piety | dindarlik | Piety of a community whose piety is unknown | 50 | 0 | 100 |
| faith.other_worshipper | diger | Contribution of any other worshipping entity | 2 | 0 | 1000 |
| faith.community_minimum | topluluk_en_az | Minimum contribution of each worshipping people, settlement and cult (so a small community's faith does not round to zero) | 1 | 0 | 1000 |
| faith.multiplier_power_pct | carpan | Effect of the faith-multiplier power (%) | 150 | 100 | 1000 |

---

## 9. Son ↔ son relations

- Stored ordered `(a<b)`.
- `iliski(x, y)` (get relation) → value or 0.
- `iliskiDegistir(x, y, delta, note)` (change relation): no-op if either is missing or x==y. `new = clamp(old+delta, -100, 100)`, rounded. Upsert keeps the old note if the new one is null. Returns new.
- `iliskiEtiket(v)` (label), thresholds `OGUL_ILISKI` (group "War and diplomacy"):

| Key | English | Default | Min | Max |
|---|---|---|---|---|
| son_relation.devotion | v ≥ this → "devotion" (bağlılık) | 60 | −100 | 100 |
| son_relation.friendship | v ≥ this → "friendship" (dostluk) | 25 | −100 | 100 |
| son_relation.hostility | v ≤ −this → "hostility" (husumet) | 25 | 0 | 100 |
| son_relation.hatred | v ≤ −this → "hatred" (nefret) | 60 | 0 | 100 |

Logic: `≥devotion` → devotion; `≥friendship` → friendship; `> −hostility` → "distance" (mesafe); `> −hatred` → hostility; else hatred.

Community relations (`topluluk_iliski`) use a different label set (`iliskiEtiketT` in rules, rules `KURAL.iliski_*`): ≤−70 blood enemy, ≤−35 enemy, ≤−10 cold, <15 neutral, <45 friend, <75 close friend, else brother. Read and write helpers live in `derin.js` (`tIliski`, `tIliskiDegistir`, `kanDavasi`), covered by the engine spec.

---

## 10. Languages and lexicon

- `diller()` (languages): canon language entities.
- `sozlukDil(dilId, limit = BAGLAM.sozluk_sayi)` (dictionary of a language): latest-first words.
- `konusulanDil(v)` (spoken language): the target of the newest active `konusur` bond from v whose language status is canon or dead. Rejected or destroyed languages do not count.
- `konusanlar(dilId)` (speakers): entities with an active `konusur` bond to the language.
- `sozlukEkle(dilId, words, addedByTip, addedById, cag)` (add words): skips empty words, words without a meaning, and words already present (case-insensitive). Truncates word to 60, meaning, etymology and example to 300. Returns the list of added words.
- `dilSatirlari(n, viewer?, dunyaId?)` (language lines, for prompts):
  - Multi-world with a world → only that world's languages.
  - With a viewer son: "near" languages = those spoken (via active `konusur`) by entities the son created or that worship him, plus languages he created. Near languages show `n + BAGLAM.dil_yakin_ek` sample words; others show `max(BAGLAM.dil_uzak_en_az, n − BAGLAM.dil_uzak_eksik)`.
  - Without a viewer: `n` words each.
  - Words are chosen with a seeded, deterministic order: `ORDER BY ((id*7919 + cag*31 + dilId) % 104729) LIMIT k`. The words are stable within an epoch and rotate between epochs (`RANDOM()` was avoided so retries get the same prompt).
  - Line: `- #<id> <name> (<subtype or 'language'>; <N> words; speakers: <names> | DEAD LANGUAGE: no living speaker): w1 = m1; w2 = m2 … | no words yet`.

---

## 11. Prompt context builders

Every text below is sent to an LLM. Turkish originals are translated in full. Variables are in `<angle brackets>`.

### 11.1 `dunyaBasligi(w, dunyaId?, {kisa})` — world header

`kisa` (short) is the variant for mortal agents: no creator temperament, word, mood, epic or wish, and a truncated cosmology. Natural laws and the creator's taboos are kept, because those cannot be broken. If `dunyaId` is given, that world's dialect, sky and laws are used.

Lines, in order (empty lines dropped):

1. `WORLD: <w.ad> — Epoch <cag> (world year <yil>). Creator god: <tanri_adi>[, <tanri_unvan>].`
2. (not short, if set) `THE GOD'S TEMPERAMENT: <tanri_mizac>`
3. (not short, if set) `THE GOD'S OWN WORD (canon): <tanri_notu>`
4. (not short) `THE CREATOR'S MOOD (sensed from the sky; an intuition, not a number): contentment <level>, wrath <level>, attention <level>, loneliness <level>. If his wrath overflows, punishment falls on godless and cursed lands; if he is content, grace on his worshippers; if he is silent, his sons feel abandoned.` Each `<level>` = `duzey(x)`, with defaults from `YARATICI.ruh_*` when the JSON is missing.
5. (not short, if epic) `THE GOD'S EPIC: "<baslik>" — its best-known verse: <dize>`; (if depth) `THE GOD'S TABOOS: <yasaklar joined " · ">` plus (not short) `\nTHE GOD'S WISH (his sons sense it): <istek>`.
6. `COSMOLOGY: <kozmoloji>`. In short mode it is cut to `BAGLAM.kisa_kozmoloji` chars at a word boundary, followed by "…".
7. `TONE: <ton>`
8. Naming:
   - world given, ≠1, with a dialect → `NAMING LANGUAGE (<world> dialect; the main world's rule does not apply here): <lehce>`;
   - no world and multi-world → `lehceBlogu` (§11.2);
   - else `NAMING LANGUAGE: <isim_kurali>`.
9. If `kiyamet ≥ kiyametEsik() * BAGLAM.kiyamet_uyari / 100`: `DOOMSDAY CLOCK: <kiyamet>/<threshold>. Godlessness, rebellion, curses, restless spirits and wars advance it; faith and miracles push it back. At <threshold> the world is destroyed by disasters.`
10. Climate (world-level JSON): `CLIMATE: <era name> (since Epoch <bas>; <era description>).`
11. Epoch star (that world's `cagin_yildizi`; for world 1 fall back to `dunya.cagin_yildizi`; with no world given use the world-1 star): `STAR OF THE EPOCH[ (<world> sky)]: #<id> <name>; creations in the <domain or "its"> domain are [<100 − OGUL_ARAC.yildiz_indirim>% ]cheaper this epoch.`
12. `NATURAL LAWS (unbreakable):\n- #<id> <name>: <desc>` per law, or `NATURAL LAWS: not yet set.`

`duzey(x)` (level word): `["almost none", "low", "medium", "high", "about to overflow"][clamp(floor(x*5/100), 0, 4)]`.

### 11.2 `lehceBlogu(w)` — dialect block

`NAMING LANGUAGES (each world has its own sound system; a record is named and judged ONLY by its own world's rule, and one world's sound ban does not apply in another):` followed by one line per non-forgotten world: `- world#<id> <name>: <rule>` (world 1 or a world without a dialect uses `isim_kurali`).

### 11.3 `dunyaSatiri(id)` — current world line (for sons)

`YOUR CURRENT WORLD: world#<id> <name> — <world-type label>[, around <star> (<star kind>)]; gravity <g>, atmosphere <a>, time ×<k>[; LEAKAGE <s>/100 (something is seeping in from outside)].` If world ≠1 and it has a cosmology: `\nTHIS WORLD'S COSMOLOGY: <kozmoloji>`.

### 11.4 `kozmosSatirlari(exceptId)` — other worlds

Empty if ≤1 world. Otherwise, one line per world except `exceptId`: `- world#<id> <name> (<type label>[, <star> star]; <B> regions, <H> peoples, <S> settlements; gravity <g>, atmosphere <a>[, time ×<k>][, <discovery if not known>])`. Counts are canon entities of that world.

### 11.5 `kardesOzeti(viewer)` — pantheon (siblings)

For each son except the viewer:
`son#<id> <name>, <title> — <rarity label> <★ x stars>, existence <band name lowercased>, domains <alan1>/<alan2>[, in world <world>[ (another world)]], Lv<level>, HP <can>/<canMax>, Faith <inanc>, Fame <un>[ [<status>[ <n> epochs]]]` + (with viewer) ` · towards you: <relation label> (<value>)[ · COVENANTED][ · REBEL AGAINST HIS FATHER]`.
The world part appears only in a multi-world cosmos; "(another world)" appears when it differs from the viewer's world. Sleeping sons show the epochs left. Empty result → "(you have no siblings)".

### 11.6 `iplikSatirlari(viewer?, limit)` — open threads

`iplikDurumlari()` (thread states) for each open thread:
- `ilerleten` (advancers) = canon-ish entities tagged `iplik:<id>`, by epoch;
- `son_cag` = max(thread epoch, advancers' epochs);
- `durgun` (stagnant epochs) = now − son_cag;
- `dunyalar` = distinct worlds of related entities (NULL world → 1).

Filtering for a viewer in a multi-world cosmos: keep threads with no world or with the viewer's world. `uzak` (remote) = the number removed.

Ranking for a viewer: `mine` = entities the son created ∪ entities worshipping him. `score = (#related ∈ mine)*BAGLAM.iplik_ilgili + (text contains son name ? BAGLAM.iplik_ad : 0) − durgun*BAGLAM.iplik_durgun/100 + (any advancer ? BAGLAM.iplik_ilerlemis : 0)`, sorted descending. Truncate to `limit`.

Line: `thread#<id> (Epoch <cag>[, <world names joined " + ">][, advanced <n> times, last Epoch <son_cag> | , never advanced]): <metin>[ [related: #a, #b]]`. World names are shown only to Fate (no viewer) in a multi-world cosmos.
Suffixes: `\n… (<k> more open stories; the ones closest to you are above)` and `\n(<u> open stories are in other worlds; you cannot advance them without going there)`.

### 11.7 `dunyaOzeti(viewer?, {baslikYok, bolum})` — world summary

The viewer is a son, or null for Fate. Budgets come from `BAGLAM_BUTCE.ogul` or `.kader`. `dId = viewer.aktif_dunya` (sons see their own world in detail; Fate sees all).

Sections (key → content):

| Key | Content |
|---|---|
| `baslik` | `dunyaBasligi(w, dId)` (unless `baslikYok`, no header) |
| `baslik` | `dunyaSatiri(dId)` if dId |
| `baslik` | `motifYasagi(dId)` (tired imagery ban, §13) — sons only, when motifs exist |
| `panteon` | `\nPANTHEON:\n<kardesOzeti>` |
| `iplikler` | `\nOPEN STORIES (threads Fate is tracking; those who advance them are rewarded):\n<threads>` (viewer limit `BAGLAM.ogul_iplik`) |
| `olaylar` | `\nRECENT EVENTS:\n<budgeted sonKronik(kn)>` or "(nothing has happened yet)". `kn` = `BAGLAM.ogul_kronik_satir + floor(wisdom / BAGLAM.ogul_kronik_bilgelik)` for sons, `BAGLAM.kader_kronik_satir` for Fate; ×`BAGLAM.arac_kat` when a single section is requested. Overflow hint: "look with dunya_ozeti section=olaylar" |
| `kozmos` | `\nTHE COSMOS'S OTHER WORLDS (you can move there with dunyaya_yonel):\n<kozmosSatirlari>` (budget `kozmos`, hint "for cosmos detail use dunya_ozeti") |
| `kozmos` | with a world: `THIS WORLD'S OLD/FOREIGN GODS (yabanci_tanriyla_konus):` then `- foreign#<id> <name>[, <title>] (<domains or ?>; power <guc>, stance towards the pantheon <tutum>[; Strength <s>, Will <w>, Charisma <c>, Cunning <k>][; powers: <names>])` for awake, contacted foreign gods of that world |
| `kozmos` | (multi-world) known active routes: `ROUTES BETWEEN WORLDS:\n- route#<id> <A> ↔ <B> (<method>, <n> epochs)`, or if none: `NO ROUTES BETWEEN WORLDS: mortals cannot travel to other worlds. Create a gate, bridge or ship (arac_yarat, hedef_dunya_id) or give your peoples sky-sailing/shipbuilding knowledge.` |
| `cografya` | `\nGEOGRAPHY AND INHABITANTS (<toplam> canon entities):\n<budgeted tree>` + (if truncated) `\n… (use varlik_ara for more)`. Tree limit: `BAGLAM.ogul_agac + wisdom` for sons, `BAGLAM.kader_agac` for Fate |
| `diller` | `\nLANGUAGES AND LEXICON (derive new names and titles from these words; give an etymology):\n<dilSatirlari>` (hint "look at the language's dictionary with varlik_incele") |
| `harita` | `\nMAP (terrain and neighbours of regions; fit your creations to it: no harbour on a coastless place, no glacier on a plain):\n<cografyaSatirlari(dId)>` (from `harita.js`) |
| `efsaneler` | `\nLEGENDS, TRADITIONS, PROPHECIES, EVENTS (newest):\n<last BAGLAM.konumsuz_satir location-less non-law roots, newest first, as varlikSatir>` |

- `bolum` given (one section) → return only that section's text joined, with the **whole** summary budget per section (the `dunya_ozeti` read tool uses this to show a section cut from the prompt); if empty → `"<bolum>" has nothing to show.`
- Otherwise → `bolumluButce(sections, B.ozet)` where header sections have floor = full length and the other sections have floor = `BAGLAM.bolum_taban`. Each section's hint is "see all with dunya_ozeti section=<key>".
- The order matters: pantheon, threads and recent events come **before** geography so they survive truncation.

`OZET_BOLUMLERI` (summary sections; valid section names for the tool): panteon, iplikler, olaylar, kozmos, cografya, diller, harita, efsaneler.

### 11.8 Budget helpers

- `butce(text, max, hint='look with varlik_ara')` (budget): if it fits, return it. Otherwise add whole lines while `n + len + 1 ≤ max`. The first line that does not fit is added truncated (`line[:max-n-2] + '…'`) only if the remaining space ≥ `BAGLAM.butce_kirp_en_az` (120). If no line fit at all, add the first line cut to `max-1` + '…'. Append `\n… (+<k> more lines; <hint>)`.
- `bolumluButce(sections, max, hint)` (sectioned budget): drop empty sections. `floor_i = min(len_i, taban_i)`. `total = Σfloor + count` (one newline each). `ratio = total > max ? max/total : 1`. `share_i = floor(floor_i*ratio)`. `left = max − Σshare − count`. Distribute `left` in section order, giving each section up to its full length. Each section is its full text if it fits its share, otherwise `butce(text, max(1, share_i), section hint)`. Join with "\n".

### 11.9 `hafiza(son, {tam})` — son's memory

Data:
- the last `BAGLAM.hafiza_yaratim_sayi` creations by the son;
- the last `hafiza_ani_sayi` chronicle rows by the son excluding `yaratim` (memories);
- the last `hafiza_hakkinda_sayi` rows by others whose text contains the son's name ("about you");
- the last `hafiza_soz_sayi` messages to the son;
- active worshipper bonds.

Repetition check: among the first `BAGLAM.tekrar_pencere` creations, count `type label/subtype`. Pairs with count ≥ `BAGLAM.tekrar_esik` are listed.

Text sections (joined with blank lines; the whole is budgeted to `BAGLAM.ogul_hafiza` × (`arac_kat` if `tam`), hint "look with hafizam"):
1. `YOUR LONG-TERM PLAN: <plan or "(you have not written one yet; write it with plan_yaz)">`
2. `WORDS SENT TO YOU:\n` + lines `[Epoch <c>] <"YOUR FATHER <creator>" | sender name>[ (<intent label>)]: "<text>"` (budget `hafiza_soz`) or "(none)".
3. `YOUR CREATIONS (<n>[; you are now on world#<id> <name>; those in other worlds are there, not here]):\n` + `varlikSatir` lines (+ ` [in another world: <name>]`; + ` — Fate: <kader_notu>` for rejected ones) (budget `hafiza_yaratim`) or "(none yet)" + optionally `\nYOU ARE REPEATING YOURSELF: <type/subtype ×n, …>. Something new of the same subtype costs more every time; create something else.`
4. `YOUR WORSHIPPERS (<n>): #<id> <name>, … (first hafiza_tapan)[ and <k> more communities]` or "no one".
5. `YOUR MEMORIES:\n[Epoch <c>] <text>…` (budget `hafiza_ani`) or "(none)".
6. If any: `WHAT HAPPENED ABOUT YOU:\n…` (budget `hafiza_hakkinda`).
7. If any folk beliefs about the son: `HOW THE PEOPLES TELL OF YOU (what they get wrong may anger you or may serve you):\n- <people> calls you "<name>": <account>` (budget `hafiza_inanc`).

### 11.10 `varlikDetay(id)` — entity inspection (for the `varlik_incele` inspect tool)

Lines:
- `varlikSatir`;
- `Creator: <"the world's own flow (mortals)" | "the god himself" | son#id name | "unknown"> · Epoch <cag>[ · world#<id> <name> (judged by its own dialect)][ · domain <alan>][ · tags: …]`;
- `Stats: <label> <value>, …` (type stats only);
- `Description: <aciklama>`;
- `History: <derinlik.tarih>`;
- `Fate's note (an editorial note; not carried into the narrative): <kader_notu>`;
- `Bonds:\n<bagSatirlari>` or `Bonds: none`;
- `Contained here:\n<varlikSatir of canon/dead children>`;
- for languages: `Lexicon: w = m; … (BAGLAM.incele_sozluk)` or "empty";
- `toplumSatirlari(v)`;
- `Canon facts (do not violate):\n- <subject> <predicate> <object>` (up to `BAGLAM.incele_gercek`).

`toplumSatirlari(v)` (society lines):
- tag `basamak:n` → `Civilization tier: <tribe | city-state | kingdom | world empire | interstellar power | cosmic power>`;
- `sagduyu` → `Sanity: <x>/100` + (if < `KORKU.bulaniklik_esik`) ` — THEIR MINDS ARE CLOUDED: strange rites, voices, misread signs`;
- society JSON → `Society: <Class> %<share> (satisfaction <m>), …` sorted by share, and `Granary: food <a>, ore <b>, goods <c>; prices: bread ×<p/100 1dp>, ore ×…, goods ×…`;
- the top 6 community relations by |value| with canon partners: `Relations with communities: #<id> <name>: [BLOOD FEUD, ]<label> (<v>); …`;
- ongoing wars (event subtype war tagged `suruyor` and `taraf:<id>`): `Ongoing wars: #<id> <name> (<muharebe> clashes); …`.

`gucSatirlari(son)` (power lines): `- <name> [<effect description with the param substituted>][ (unlocks at Lv<n>)]: <description>`, or "(not yet awakened)".

`gercekSatirlari(id, n)` (fact lines): active facts with the entity as subject or object, newest first: `"<subject name> <predicate> <object name or text>"`.

---

## 12. Narrative hygiene (text cleaners)

These exist because models copied internal IDs and editorial notes into lore. **The rewrite should prevent this upstream** by never putting raw `#id` markers into narrative prompts (use opaque handles in tool schemas instead) and by validating LLM output. The cleaners are still needed to sanitize model output.

### 12.1 `kimlikTemizle(s)` — ID scrub (chronicle lines)

In order:
1. Remove bracketed tags like `[iplik#12]` / `[#3, #4]`.
2. Remove parenthesized ids `(#795)`, `(thread#42)`, `(#2741 içinde)` ("(#2741 in)").
3. `thread#67 hikâyesi…` (story-of) → "a story" with the matching case form (**LANGUAGE-SPECIFIC case map** `HIKAYE_EK`).
4. `thread:108'i` / `son#3'ün` → "a story" / "a son" plus a harmonized case suffix (**LANGUAGE-SPECIFIC** `numaraSozu`).
5. `son#3 Haevaron` → `Haevaron` (drop a prefix id before a capitalized name).
6. A remaining `thread#N` / `son#N` → "a story" / "a son" (capitalized at sentence start).
7. Remove `world#N`, `route#N`, `foreign#N`, `star#N`.
8. Collapse spaces; remove spaces before punctuation.

English port: replace with "a story" / "a son" without case logic.

### 12.2 `anlatiTemizle(s)` — narrative clean (descriptions, depth, epoch narratives)

`kimlikTemizle`, then remove: HTML comments; lines starting "Not: Bu kayıt…" ("Note: This record…"); power-class labels "G7 olarak sınıflanan" ("classified as P7") and "(G7)"; dice phrases ("122'ye 94 ile", "(130–102)"); `(#12)`; `(son#3 Name)` → `(Name)`; any remaining `[type]#N `; numbered mentions such as "thread 95'i" → "a story" (LANGUAGE-SPECIFIC); `★n`. Then collapse spaces and trim.

### 12.3 `kaderNotuTemizle(s)` — Fate's public note clean

Fate's internal reasoning must not leak into its public note. Split into sentences. For any sentence matching `IC_UYARI` (internal warning: "ÖN ELEME" pre-screen, "BAĞSIZ" unbonded, "yorgun motif/imge" tired motif/image, "yorgun bir kopya" tired copy, "motif yasağı" motif ban, "klişe" cliché, "gerekçeyle kabul" accepted with justification, "uyarı…" warning, "ölçüt a–e" criterion a–e), split it further on `;` and drop the matching clauses (re-terminating with '.'). Re-clean, strip a leading conjunction ("However/But/Yet/Still/Despite this,"), and capitalize. Return null if nothing with letters remains (the caller then writes its own plain note: "Fate accepted." / "Fate corrected.").

### 12.4 `metaCumleSil(s)` — meta-sentence removal

Drops sentences matching `META_CUMLE`: sentences about Fate rewriting, correcting or changing the record's account or description, "the first account", "this record was corrected / rewritten". Fate's editing is an editorial event, not world history.

### 12.5 `sonuYaz(id, sentence)` / `sonlariYaz()` — "ending" sentences

- `sonuYaz` (write ending): cleans the sentence (suffix-fix + narrative clean) and appends it to `aciklama` only if not already present.
- `sonlariYaz()` (startup, idempotent): for dead/destroyed entities with `olum_cag` whose description does not mention `Çağ <olum_cag>` ("Epoch N"): take the last sentence of `kader_notu` that mentions that epoch, else the default "Died in Epoch N." (mortal) / "Vanished in Epoch N." (destroyed) / "Came to an end in Epoch N." (other). Append it.

### 12.6 `anlatilariTemizle()` — startup leak sweep

`SIZINTI` (leak) filter: the text contains `#<digit>`, `★`, `<!--`, "olarak sınıfla" ("classified as"), "Not: Bu kayıt", `<digit> ile ` ("with N"), or `(<digit>…<digit>)`. Applied to: entity `aciklama` and `derinlik` (JSON walked recursively; strings cleaned), `caglar.anlati/ozet`, `caglar_dunya.anlati/ozet`, `yabanci_tanrilar.aciklama` + JSON `derinlik`/`kisilik`, `kronik_bakis.metin`, `halk_inanc.anlati/yanlis`, `dunya.tanri_derinlik/tanri_destan` (JSON). Returns the count of rows changed.

---

## 13. Tired motifs (`yorgunMotifler`, `motifListesi`, `motifYasagi`)

Goal: find images over-used across the world's texts and ban them in every writing prompt (son, mortal, Fate, chronicler, deepening).

```
yorgunMotifler(n = DIL.motif_sayisi, dunyaId?):
  d = dunyaId if multi-world else None
  cache key = (d, epoch, n, all DIL motif rules, COUNT(varliklar)); LRU of DIL.motif_onbellek entries
  short = last DIL.motif_pencere descriptions of canon/dead entities (not starting "[Dünya motoru]") [in world d]
  long  = last DIL.motif_pencere depth texts (all JSON strings concatenated) [in world d]
          + last DIL.motif_anlati epoch narratives (caglar_dunya for d, else caglar)
  tokenization (sozcukleri): words = letter runs (apostrophe suffix dropped);
      a word shorter than DIL.motif_kok_en_kisa, or capitalized (proper noun), or a stop word resets the "previous word";
      stem = kokBul(lower(word))[:DIL.motif_kok]
  common = set of stems of the "ordinary words" list (SIRADAN)
  single: for each short text, the set of non-common stems → document frequency
  pair:   for each long text, the set of "prevStem stem" where not both are common → document frequency
  select(counts, total, pct): [] if total < DIL.motif_en_az_kayit
          else entries with count ≥ max(DIL.motif_en_az, total*pct/100)
  canon pairs = pairs occurring in dunyaBasligi(world, d)    # never ban canon imagery
  list = select(single, len(short), DIL.motif_esik) + select(pair, len(long), DIL.motif_cift_esik)
         minus canon pairs, sorted by ratio desc, first n,
         formatted "<shortest surface example> (%<round(ratio*100)>)"
```

- `kokBul(word)` (find stem): strip up to `DIL.motif_ek_adim` (3) Turkish suffixes from a fixed list, keeping a stem ≥ `DIL.motif_kok_en_kisa` (3). **LANGUAGE-SPECIFIC**: use an English stemmer (Snowball/Porter).
- Stop-word list `DURAK` and ordinary-word list `SIRADAN`: Turkish function and common words. **LANGUAGE-SPECIFIC**: replace with English stop words and a common-word list.
- `motifListesi(dunyaId)` (motif list) = global list + the world's own list (deduplicated by name).
- `yabanciImgeler(dunyaId)` (foreign images): only for world ≠1 in a multi-world cosmos — world 1's tired motifs, except those whose first-word stem appears in this world's header ("words of another world").
- `motifYasagi(dunyaId)` (motif ban) prompt line:
  - `TIRED IMAGERY (repeated too much in the world's texts): <list>. Do NOT use these or their synonyms; instead find imagery specific to this entity and this corner of the world that has not been used before (another sense, another material, another trade, another season).`
  - and, if any, ` WORDS OF ANOTHER WORLD (the main world's worn-out imagery; do not carry it to this world): <list>.`

Rules `DIL` (group "Language and names"):

| Key (new) | Old | English | Default | Min | Max |
|---|---|---|---|---|---|
| names.similar_max_len | benzer_uzunluk | Longest name length (letters) for which a one-letter difference is forbidden | 7 | 0 | 20 |
| names.family_cap | aile_tavani | Max names starting with the same stem (see stem letters) | 3 | 1 | 50 |
| motifs.single_pct | motif_esik | Tired motif: appears in this % of recent descriptions | 18 | 1 | 100 |
| motifs.count | motif_sayisi | Tired motifs shown in prompts | 14 | 0 | 60 |
| motifs.window | motif_pencere | Recent descriptions examined | 120 | 15 | 2000 |
| motifs.stem_len | motif_kok | Max letters of the compared stem (after suffix stripping) | 5 | 1 | 30 |
| motifs.pair_pct | motif_cift_esik | Tired two-word image: % of recent depths and epoch narratives | 15 | 1 | 100 |
| motifs.suffix_steps | motif_ek_adim | Max suffixes stripped from one word | 3 | 0 | 10 |
| motifs.min_stem | motif_kok_en_kisa | Min stem length after stripping; shorter words not counted | 3 | 1 | 20 |
| motifs.narratives | motif_anlati | Recent epoch narratives examined | 5 | 0 | 100 |
| motifs.min_count | motif_en_az | Min repetitions | 6 | 1 | 1000 |
| motifs.min_docs | motif_en_az_kayit | Min descriptions before measuring | 15 | 1 | 2000 |
| names.stem_letters | kok_harf | Name family and shared stem: letters compared from the start | 4 | 1 | 20 |
| motifs.cache_size | motif_onbellek | Cached measurements per world | 16 | 1 | 1000 |
| dialect.real_word_window | turkce_pencere | Dialect check: recent descriptions examined to identify real (Turkish) words | 3000 | 10 | 100000 |
| dialect.real_word_min | turkce_en_az | A lowercase word appearing at least this often in prose is a real word (not an invented stem) | 3 | 1 | 1000 |
| dialect.min_stem | lehce_kok_en_az | Min letters of an invented stem to check | 3 | 1 | 20 |

---

## 14. Canon facts (`gercek.js`)

`kesinGercekler(ids, cag)` (certain facts) writes deterministic facts so that contradiction checks have a basis even when Fate returns nothing. For each distinct id whose entity is canon-ish:

| Predicate (EN; old TR) | Condition | Object |
|---|---|---|
| is located in (`içinde bulunur`) | location exists and is canon-ish | location id |
| creator (`yaratanı`) | `yaratan_id` | son name (text) |
| language spoken (`konuştuğu dil`) | first active `konusur` v→v | language id |
| god worshipped (`taptığı tanrı`) | first active `tapar` | entity id if v, else god name text |
| descends from (`soyundandır`) | first active `soyundan` v→v | ancestor id |

A fact is skipped if an active fact with the same subject and predicate exists (one per predicate). `cag ?? v.cag`, `kaynak_id = v.id`. Returns the count. `gercekSayisi()` (fact count) = active facts. At startup, if there are 0 facts, run it over all canon-ish entities. Fate also writes interpretive facts (agents module).

---

## 15. Interrupted-turn context (`turCtxYaz` / `turCtxOku`)

A turn's in-memory counters are serialized after each tool call, so a crash resumes the turn mid-way.
- Write (serialize): skip keys `ap` and `cag` and functions. A `Set` becomes `{"$set": [numbers or strings]}`. Arrays keep number, string and plain-object items. Numbers, booleans, strings and null are kept as is.
- Read (deserialize): parse (invalid → `{}`); `{"$set": …}` becomes a `Set`.
- Rewrite: a typed Pydantic `TurnContext` model persisted to `agent_turn.context`.

---

## 16. Empty worlds (`bosdunya.js`)

`yasayanVar(worldId)` (has living): any canon people, settlement or mortal in the world.

`bosDunyalar(cag)` (empty worlds): for each world whose discovery is not `unutulmus` (forgotten) or `bilinmeyen` (unknown), and which has no living:
- habitable regions = canon regions of the world with `bereket` (fertility; default 50) ≥ `DERIN_YASAM.yasam_bereket` (the fertility threshold at which life appears spontaneously; defined in the engine module), sorted by fertility descending. Skip the world if there are none.
- empty-for = `cag − max(world.olusturma_cag ?? 1, MAX(COALESCE(olum_cag, cag)) over its peoples, settlements and mortals ever)`.
- returns `[{id, ad, tur, bos_cag, bolgeler:[{id, ad, alt_tur, bereket}]}]`.

Rules `BOS_DUNYA` (used by son distribution, opportunities and the engine):

| Key (new) | Old | English | Default | Min | Max | Group |
|---|---|---|---|---|---|---|
| empty_world.dispatch_after | dagit_bekle | A habitable world empty this many epochs gets a son dispatched automatically (0 = immediately) | 1 | 0 | 1000 | Cosmos and travel |
| empty_world.first_people_essence | ilk_halk_oz | Essence reward for the son creating the first people/settlement/named mortal of an empty world | 30 | 0 | 10000 | Cosmos and travel |
| empty_world.first_people_fame | ilk_halk_un | Fame reward for the same | 10 | 0 | 10000 | Cosmos and travel |
| empty_world.first_people_xp | ilk_halk_xp | XP reward for the same | 20 | 0 | 10000 | Cosmos and travel |
| empty_world.native_guarantee | yerli_guvence | A world without a people for this many epochs surely gets a native people (0 = no guarantee) | 3 | 0 | 1000 | Population and growth |
| empty_world.opportunity_regions | firsat_bolge | Habitable regions listed in a "new world" opportunity | 3 | 1 | 50 | Opportunities |

---

## 17. Change feed (`degisim.js`)

Purpose: the UI keeps a version token and fetches only the changed rows.

- At load: create `temp.degisim(seq AUTOINCREMENT, tablo, satir_id, islem)` and AFTER INSERT/UPDATE/DELETE triggers on the tracked tables **varliklar, ogullar, baglar, kronik, dunyalar, yildizlar, iliskiler, yabanci_tanrilar, rotalar, yolculuklar, dunya** (op codes `e` insert, `g` update, `s` delete).
- `DONEM` (period) = base-36 process start time. `tabanSeq` (base seq) = 0.
- `surum()` (version) = `"<DONEM>:<lastSeq>"`, where lastSeq = max(MAX(seq), sqlite_sequence value), so it never goes backwards after deletes.
- `degisimler(token)` (changes):
  - parse; if the period differs, seq is not a number, or `seq < tabanSeq` → `{surum, tam:true}` (full refresh).
  - Else group rows with `seq > token` by (table, row) → if the count > `ARAYUZ.degisim_sinir` → full refresh.
  - Else `{surum, tam:false, tablolar:{t:{degisen:[ids that still exist], silinen:[ids gone]}}}` (changed, deleted).
- `degisimSifirla()` (reset, after restore/import/reset): insert a dummy row to get a seq → `tabanSeq` = it; delete all. Any old token is now < base → full refresh.
- `degisimBuda(keep = ARAYUZ.degisim_tut)` (prune, epoch end): if `max − keep > tabanSeq` → `tabanSeq = max − keep`; delete `seq ≤ tabanSeq`.

The server adds to the response `durum` (busy flag, jobs, queue, image job, creator essence, epoch, unread notifications, half-finished epoch …).

Rules `ARAYUZ` (group "Interface"):

| Key (new) | Old | English | Default | Min | Max |
|---|---|---|---|---|---|
| ui.population_trend_pct | nufus_yon | Min change (%) for population to show as growing/shrinking on the map | 5 | 0 | 100 |
| ui.change_feed_max | degisim_sinir | Max changes in one incremental response (more → full refresh) | 1500 | 50 | 100000 |
| ui.change_log_keep | degisim_tut | Max entries kept in the change log (pruned at epoch end) | 20000 | 100 | 10000000 |

**Rewrite**: an in-process monotonically increasing `change_seq` emitted by the repository layer (or an outbox table), pushed over SSE/WebSocket.

---

## 18. Live-feed categories (`akis.js`)

`akisKategorisi(text)` (feed category) returns the first matching category, testing at **word starts** (`(?<![\p{L}\p{N}])` + pattern, case-insensitive). Otherwise it returns `dunya` (world). The patterns are Turkish word stems (**LANGUAGE-SPECIFIC**); the English equivalents are given.

| Key | Label | Turkish stems | English replacement stems |
|---|---|---|---|
| `yolculuk` | Ships and voyages | gemi, sefer, yolculuk, yola çıktı, vardı, kaçak yolcu, kervan, göç etti, koloni | ship, voyage, expedition, set out, arrived, stowaway, caravan, migrated, colony |
| `kapi` | Gates and routes | kapı, mühür, köprü, rota, yol açıldı, geçit, sapan | gate, seal, bridge, route, path opened, pass, slingshot |
| `sizinti` | Leakage and horror | sızıntı, dış varlık, hiçlik, sağduyu, delir, bulanık, yasak bilgi, fısıltı | leak, outer being, void, sanity, madness, clouded, forbidden knowledge, whisper |
| `savas` | Wars | savaş, muharebe, kuşat, ordu, fethetti, yağma, baskın | war, battle, siege, army, conquered, plunder, raid |
| `afet` | Disasters | sel, deprem, veba, salgın, kuraklık, fırtına, kıtlık, afet | flood, earthquake, plague, epidemic, drought, storm, famine, disaster |
| `gok` | Sky events | tutulma, kuyruklu, yıldız, gök, "ay ", hizalan, meteor | eclipse, comet, star, sky, moon, alignment, meteor |
| `hayat` | Birth and death | doğdu, öldü, ölümü, yaşında, varisi, dirildi, evcilleş, kimera, mutasyon | was born, died, death, aged, heir, resurrected, domesticated, chimera, mutation |
| `medeniyet` | Civilization | basamak, federasyon, bağımsız, imparatorluk, krallık, ticaret | tier, federation, independent, empire, kingdom, trade |

**Rewrite**: engine notes are template-generated, so classify them by the **template id** at write time instead of with regexes.

---

## 19. Importance and archive (`arsiv.js`)

Goal: keep the atlas from bloating. Entities fall into a "history" layer (hidden by the default filter) unless they are important.

`onemHesapla(cag)` (compute importance), for each non-rejected entity:
- `bag` (bonds) = active bond count where the entity is the v-source plus where it is the v-target;
- `anma` (mentions) = (count, max epoch) from `kronik_varlik ⋈ kronik`;
- `sonAnma` (last mention) = max(last mention epoch, birth epoch); `yas` (age) = cag − sonAnma.

```
onem = round( power*W.w_guc
            + min(W.w_bag_tavan, bag*W.w_bag)
            + min(W.w_anma_tavan, mentions*W.w_anma)
            + (favorite ? W.w_favori : 0)
            + max(0, W.w_taze - yas*W.w_taze_azalma)
            + (nufus ? min(W.w_nufus_tavan, log10(nufus+1)*W.w_nufus) : 0)
            - (durum == 'kanon' ? 0 : W.w_yasamayan) )
archive decision (first match):
  arsiv_elle == 1          → archived ("manually sent to history")
  arsiv_elle == 0 or fav   → not archived
  durum in (olu, yok_edildi) and yas ≥ olu_cag → archived ("dead; no longer mentioned" / "vanished")
  durum == gerceklesti and yas ≥ olu_cag       → archived ("fulfilled")
  type ∉ PERMANENT and ARSIV[type] defined and yas ≥ ARSIV[type] and onem < onem_esik
                                               → archived ("<yas> epochs without mention")
  else not archived
```

PERMANENT (only manually archivable) = region, people, language, celestial, mortal, species, natural law, social law, cult. Age thresholds exist only for types `olay, kehanet, ruh, yerlesim, esya, gelenek`.

Result per id: `{onem, arsiv, arsiv_sebep, son_anma}` (importance, archived, reason, last mention).
- Cache `onemler()` (importances) keyed by `(epoch, SQLite total_changes())`, so it is recomputed only after any write.
- `onemleriKaydet()` (save importances, epoch end and startup if any NULL) writes `varliklar.onem` where it changed.
- `arsivAyarla(id, 'tarih'|'atlas'|'otomatik')` (set archive: history / atlas / auto) sets `arsiv_elle` = 1 / 0 / NULL and returns the importance info. It runs through the creator ledger (`el('varlik:arsiv')`).
- `gorselsizOnemliler({limit=40, tur})` (important entities without images, for the image gallery): entities without a `v` image, sorted by importance desc then id desc.

Rules `ARSIV` (group "Atlas archive"):

| Key (new) | Old | English | Default | Min | Max |
|---|---|---|---|---|---|
| archive.event_epochs | olay | Event unmentioned this many epochs → history | 3 | 1 | 100 |
| archive.prophecy_epochs | kehanet | Prophecy → history after N epochs | 4 | 1 | 100 |
| archive.spirit_epochs | ruh | Spirit | 4 | 1 | 100 |
| archive.settlement_epochs | yerlesim | Settlement | 5 | 1 | 100 |
| archive.item_epochs | esya | Item | 6 | 1 | 100 |
| archive.tradition_epochs | gelenek | Tradition | 8 | 1 | 100 |
| archive.importance_floor | onem_esik | Entities above this importance never go to history | 60 | 0 | 500 |
| archive.w_power | w_guc | Importance per power level | 10 | 0 | 100 |
| archive.w_bond | w_bag | Per bond | 3 | 0 | 50 |
| archive.w_bond_cap | w_bag_tavan | Max from bonds | 40 | 0 | 500 |
| archive.w_mention | w_anma | Per chronicle mention | 2 | 0 | 50 |
| archive.w_mention_cap | w_anma_tavan | Max from mentions | 30 | 0 | 500 |
| archive.w_favorite | w_favori | Favourite bonus | 50 | 0 | 500 |
| archive.w_fresh | w_taze | Freshness bonus for a recently mentioned entity | 20 | 0 | 500 |
| archive.w_fresh_decay | w_taze_azalma | Freshness decay per epoch | 4 | 0 | 500 |
| archive.w_population | w_nufus | Per log10(population) | 4 | 0 | 100 |
| archive.w_population_cap | w_nufus_tavan | Max from population | 20 | 0 | 500 |
| archive.w_not_living | w_yasamayan | Penalty for no-longer-living records | 15 | 0 | 500 |
| archive.dead_epochs | olu_cag | Dead/destroyed/fulfilled entity unmentioned this many epochs → history | 2 | 0 | 100 |

---

## 20. Repair passes (idempotent data fix-ups)

Philosophy (old code): a bug fixed at its source still leaves traces in old data. Each repair finds **only rows that are still broken**, so re-running it is harmless. **Nothing is deleted** (except the legacy `bilirdi`/`konusurdu` bonds). Wrong bonds are closed (`aktif=0`, often with the description `"kapatıldı: <reason>"`) so they stay as history.

### 20.0 Startup order (`server.js` listen callback; all steps skipped in read-only discovery mode unless noted)

0. On module load (always): schema DDL, `addCol`s, triggers, `veriGecisleri()` (01 §11), rules load (`dengeUygula`), ledger and change-feed TEMP triggers, `ekleriDoldur()` (fill missing suffix info; LANGUAGE-SPECIFIC).
1. `dengeGecisi()` (balance migration; epoch module): one-time essence top-up when `denge_surum<2` (01 §11).
2. If any non-rejected entity has `onem IS NULL` → `onemleriKaydet()`.
3. `olcumBuda()` (prune LLM metrics).
4. `planIstatistikleri()`.
5. `onarimKos()` (run repair): if `veri_surum < 2` → `metinOnarimi()` (§20.9), then `veri_surum=2`.
6. `yasTutarliligi()` (age consistency; engine module): a dead mortal whose age exceeds its lifespan gets its base lifespan raised so the effective lifespan equals the age at death.
7. `veriOnarimi()` (§20.1), which includes the text repairs §20.2–§20.8. Logs the non-zero counters.
8. `ufuk.sezgiKurtar()` (recover intuitions): horizon intuitions stuck in `isleniyor` go back to `bekliyor`.
9. `aynalariEsle()` (pair mirrors; cosmos module): every mirror world without a twin gets one assigned.
10. `anlatilariTemizle()` (§12.6).
11. `sonlariYaz()` (§12.5).
12. `kopukUclariOnar()` (§21.2).
13. Image captions that fail `baslikGecerli` (e.g. a caption that is just a file name) → set to NULL.
14. If there are 0 canon facts → `kesinGercekler(all canon-ish ids)`.
15. `seyahat.dunyayiBagla(id)` (connect world) for every world: a world with no routes at all gets a hidden route (travel module).
16. After `SUNUCU.tamamla_gecikme` ms, unless `AERONA_LLM_YOK` is set or `AERONA_TAMAMLA=0`: `epoch.tamamla()` (complete) — an LLM job that fills in missing pieces (creator portrait prompt, son powers/existence, a celestial body, a first people, image prompts, foreign-god depth, naming pending records, and narratives of past epochs).

The same text repair `onarimKos()` also runs after "world changed" (restore, import, reset; §29).

**Rewrite**: a `FixupRegistry` of named fix-ups (`applied_fixup` table). Each is either one-shot (versioned) or "self-healing" (cheap, idempotent, runs every start). Run them in a background task after the server accepts connections, with progress events. The old code ran them synchronously before serving.

### 20.1 `veriOnarimi()` — data repair (one transaction for the structural part)

`cag` = current epoch. Steps, in order:

1. **Mechanical subtypes** (`mekanikAltTurler`): restore engine subtypes that renaming overwrote. Only `kaynak='dunya'` (engine-made) rows are touched:
   - `olay` tagged with any `"taraf:` and subtype not war/battle/siege → `savaş` (war);
   - subtype containing "muharebe" → `muharebe` (battle); containing "kuşatma" → `kuşatma` (siege);
   - `esya` whose subtype mentions coin/money/currency (`sikke`, `parası`, `para …`, `para birimi`) or whose name contains "Sikkesi" (coin) → `para birimi` (currency);
   - `kehanet` with a subtype containing "tutulma" (eclipse) → `tutulma kehaneti` (eclipse prophecy).
2. **Friend and enemy at once** (`dostDusman`): for every unordered pair that has an active v-v `dusman` and also an active `muttefik` or `ticaret`: if `tIliski(a,b) ≥ 0` (community relation not negative) → `barisYap(a, b, cag, 'kin söndü')` (make peace, reason "the grudge died out": closes the enemy bonds; writes a truce only if they actually fought a war, unless `DERIN.savassiz_ateskes`). Else deactivate their alliance and trade bonds.
3. **Shared thrones** (`ortakTahtlar`): for every target ruled (active `yonetir`) by more than one living mortal: keep the oldest bond (lowest id), deactivate the others, and write a `dunya`-kind chronicle line: "The shared throne over <place> has ended: <names> withdrew from rule, <keeper> reigns alone." (ids: place, keeper, withdrawn).
4. **Network type fixes** (`agTurleri`): active `neden_oldu` (caused) with description "kaderinde anılır" (mentioned in its fate) → `ilgili` (related). Active `neden_oldu` from a war/battle/siege event whose description mentions "taraf" (side) → `taraf`.
5. **Bond endpoints** (`bagUclari`): for active v-v bonds of types sahip, yonetir, ticaret, konusur, bilir, kutlar, tapar, yasar, evcil: if reversed (§6.3) → swap. Then if the endpoints are invalid (§6.2) → `tur='ilgili'`, `aciklama = "<type>[: <desc>]"`. Returns `{cevrilen, dusen}` (flipped, downgraded).
6. **Duplicate bonds** (`yinelenenBaglar`, after step 5, because flips can create duplicates): group active bonds by (kt, k, ht, h, type, [description if role type]). For groups of count > 1 of a non-event type, keep the lowest id and close the others with "kapatıldı: yinelenen bağ" (closed: duplicate bond).
7. **Rejection marks** (`redIsaretleri`): inactive bonds touching a rejected entity with `red_kapatti IS NULL` → `red_kapatti=1`.
8. **Thread tags** (`iplikEtiketleri`): remove `iplik:<id>` tags pointing to non-existent threads (via `etiketSil`). Fix `neden_oldu` bonds with the "kaderinde anılır" description that are dated before the target's birth: set `cag` = the target's birth epoch.
9. **Denying "related" bonds** (`inkarBaglari`): close active `ilgili` bonds whose description matches `INKAR` (denial: "no direct bond/relation/link", "indirect", "not visible", "relation unclear/none", "a meaningful bond …") with "kapatıldı: <original description>".
10. **Foreign-god deaths** (`tanriOlumleri`): for dead foreign gods with `olum_cag IS NULL`: find the latest chronicle row of kind `yabanci_tanri` whose text contains the god's name and "öldürdü" (killed). Set `olum_cag` = that row's epoch (or the current one). If that row has a son and there is no `oldurdu` o→y bond, add one with description "tanrılar savaşında" (in the war of gods) dated to that epoch.
11. **Bonds of the dead** (`derin.olulerinBaglari(cag)`):
    a. `olumCagiDoldur` (fill death epoch): dead or destroyed rows with NULL `olum_cag` get the last "Çağ N" (Epoch N) in `kader_notu` with birth ≤ N ≤ now; otherwise `cag` if born within the last epoch, else the birth epoch.
    b. Active `yasar` bonds from the dead with description "ruhu oraya indi" → type `ruhu_indi`.
    c. Deactivate the dead's **outgoing** state bonds of types: yasar, korur, tapar, konusur, yonetir, komutan, sahip, bilir, sever, yoldas, esir, casus, pesinde, evcil, muttefik, ticaret, dusman, harac_oder, ateskes, avlar, kaptan, yolcusu, hasim, ustasi, uyesi. For `sahip`/`yonetir` with a living target, find the heir (`mirasci`: the newest living descendant (`soyundan` → dead) that is a mortal or community; else the dead's location if it is a living community; else a living community reachable via the dead's `soyundan` target, its ruler, or what it protected). If the heir exists, is not the target itself, does not already hold the same bond, and (for `yonetir`) the target has no other active ruler → `addBag(heir → target, same type, "<dead name>'den miras" (inherited from <dead>))`.
    d. Deactivate **incoming** state bonds to the dead (yonetir, korur, komutan, sahip, tapar, muttefik, ticaret, dusman, harac_oder, sever, yoldas, casus, evcil, konusur, ateskes, kaptan, yolcusu, avlar, pesinde, esir, hasim, ustasi, uyesi).
    e. Routes controlled by the dead pass to the heir if it is a living community, else `kontrol_id = NULL`.
    Returns `{kapanan}` (closed).
12. **Gate travellers** (`gecitYolculari`): entities named like `İplik <n>'den Gelen Yolcu` ("The Traveller from Thread <n>", a temporary name) → replace that prefix with "<arrival place name>'e" ("to <place>") (suffix-fixed) via `adDegistir`. Their children ("… ile <old>'nun Çocuğu", "child of …") also get the new name substring.
13. **Auto patrons** (`otoKoruyucular`): legacy fix. Chronicle lines matching "…en çok tapanının yaşadığı…kutsal dünyası ilan etti" ("…declared the world where most of his worshippers live his holy world") identify patrons that an old auto-path assigned without the `koruyucu_oto` flag. Clear `koruyucu_ogul` for those worlds, then re-run `panteon.kutsalDunyalar(cag)` (redistribute holy worlds with a per-son cap).
14. **Stale location bonds** (`eskiKonumBaglari`): deactivate active `icinde` v-v bonds pointing to a place other than the entity's current `konum_id`, but only when a correct active `icinde` bond to the current location also exists.
15. **Ethnogenesis** (`derin.etnogenezOnar`): a people's active `yonetir` with description "yurdu" (homeland) → converted to `yasar` (or closed if `yasar` already exists). Then `tekYonetim()` (single rule): for each canon settlement, people, faction or cult target with more than one living ruler, keep the newest non-"homeland" rule and close or convert the others. Returns `{yurdu_yasar, yinelenen_yonetim}` (homeland→lives, duplicate rule).
16. **Inside bonds** (`ekonomi.icindeOnar`): deactivate active `icinde` (not "ruh kaplama") pointing to a region, place, settlement, people, faction or cult that is not the source's `konum_id`. For factions tagged "gezgin pazar" (wandering market), deactivate their trade bonds with partners in other worlds. Returns `{icinde, pazar_ticaret}` (inside, market trade).
17. **War and location** (`derin.savasVeKonumOnarimi`): unless `DERIN.savassiz_ateskes`, close active v-v `ateskes` (truce) bonds between pairs that never fought a war (no war event tagged with both sides). Add a missing `icinde` bond for every canon/fulfilled entity whose canon/fulfilled location has no such bond.

Then the text repairs (each opens its own transaction; the order matters):

18. `enumEtiketOnar()` (§20.4) → keys `etiket_alt_tur`, `etiket_kronik`.
19. `loreOnarimi()` (§20.2) → `lore_*`.
20. `ekOnar()` (§20.3) → `ek_*` (renames clear the suffix info; this rewrites it).
21. `agBagOnarimi()` (§21.4) → `ag_*`.
22. `ufuk.kesifNedenOnar()` (§20.8) → `kesif_*`.
23. `kronikTekrarOnar()` (§20.5) → `tekrar_gizlenen`.
24. `uyananTanriMetni()` (§20.6) → `uyanan_tanri`, `uyanan_kronik`.
25. `cagBasiYillari()` (§20.7) → `yil`.

Return: a flat dict of counters.

### 20.2 Lore repairs (`lore-onar.js`, `loreOnarimi`)

- `kimlikSizintiOnar` (ID-leak repair):
  - chronicle rows matching `KIMLIK` (thread/son `#` or `:` digit; parenthesized ids; `(#N lowercase-word)`; `world/route/foreign/star#N`) → `ekDuzelt(kimlikTemizle(text))`;
  - `kader_notu` matching KIMLIK, `IC_UYARI` or `#\d`: keep the prefix "Kader düzeltti:" (Fate corrected:) if present and clean the rest with `kaderNotuTemizle`. Result: "Fate corrected: <t>" / "Fate corrected." / "<t>" / "Fate accepted.";
  - entity `derinlik` (JSON strings) and `aciklama` matching KIMLIK or `META_CUMLE` → `metaCumleSil(anlatiTemizle(x))`;
  - all threads (`metin`, `kapanis`) and folk beliefs (`anlati`, `yanlis`) → `anlatiTemizle`.
- `lehceNotlariOnar` (dialect-note repair): for entities in worlds ≠1 whose Fate note mentions "<letter> sesi/sesini…" (the sound <letter>) together with "forbidden / contradicts / cannot be named / cannot be used", where that letter **is allowed** in the entity's own dialect: drop that sentence, and drop any following sentence referring to "this ban". Preserve the prefix.
- `inancAdlariOnar` (belief-name repair): a folk belief whose local god-name equals the son's (or creator's, id 0) name, title, or a comma/semicolon part of the title → regenerate it from the people's language via `agents.halkTanriAdi(people, son)`. Replace the old name in `anlati`/`yanlis` (`adMetinde` + suffix fix).
- `adUnvanOnar` (name/title repair): entities named "<oneword>, <epithet>" (epithet ≥3 chars, short name not used by another entity) → set `unvan` if empty, and `adDegistir(id, shortName)`.

### 20.3 Suffix and spelling repair (`ekonar.js`, `ekOnar`) — **LANGUAGE-SPECIFIC: do not port**

What it did, for the record: (0) fix name spelling ("Ilk" → "İlk") via rename when the fixed name is free; (1) recompute name suffix info unless manual; (3) drop the redundant type tail "… yarattı: Name (type)" (created: Name (type)) when the type is already said; (4) rewrite engine birth templates "X çiftçiler arasından … çıktı" → possessive form "X'in çiftçileri arasından … çıktı: Name" ("from among X's farmers rose …") and "X başına bir lider geçti" → "Name, X'in başına lider olarak geçti" ("Name became X's leader"), also in `[Dünya motoru]` descriptions; (5) "arasında" (among) vs "içinde" (inside) for single institutions; (6) rule titles by ruled type ("<Law> Hükümdarı" ruler → "<Law> Bekçisi" keeper …); (7) mortal descriptions "bir … oğuldur" ("is a son") → "bir … ölümlüdür" ("is a mortal"; "son" means god-son in this game); (2) run `ekDuzelt` on every narrative text in: kronik, kronik_bakis, caglar, caglar_dunya, varliklar (aciklama, kader_notu, unvan, derinlik JSON), baglar, iplikler, halk_inanc (ad, anlati, yanlis), mesajlar, ogullar (unvan, destan), yabanci_tanrilar (unvan, aciklama, derinlik JSON).

English rewrite equivalents worth keeping: (3) the type-tail dedupe; (4) generating templates correctly from the start; (6) a ruler-title table per ruled type (e.g. a law has a "Keeper", a settlement a "Lord"); (7) never call mortals "sons".

### 20.4 Enum-label repair (`etiket-onar.js`)

Raw enum keys leaked into text. `altTurDuzelt(subtype, type)` (tools module) normalizes subtypes: raw keys like "calgi" become their labels ("çalgı" instrument); "arac: tuz kefesi" becomes "araç: …"; truncated or uppercase copies are fixed. For each changed subtype, chronicle rows that reference the entity and contain `(<old subtype>` are updated.

`kronikEtiketle(text, kind)` (label the chronicle) rewrites:
- `"babasına dua etti (<key> diledi)"` → `"…, <DUA_ISTEK label>"` (prayed to his father, asked for essence / blessing / permission / vengeance / forgiveness);
- in message rows, `" (<intent key>): \""` → `" <SOZ_NIYET label>: \""` (spoke friendly, proposed an alliance, declared love, threatened, mocked, warned, proposed a bargain);
- `"guc|kurnazlik sınavında"` → labelled stat ("in a test of strength/cunning");
- `"üretti (<key>; hasar h, koruma k)"` (produced (…; damage, protection)) → `"üretti (<label>; <quality>)"` with quality = "usta işi" masterwork if h+k ≥ `OLUMLU.uret_usta`, "sağlam" solid if ≥ `uret_saglam`, else "kaba" crude;
- `"barışılanlar: a, b"` (made peace with) → `"a ve b ile düşmanlık sona erdi"` (hostility with a and b ended);
- `"(A sağduyu 73 → 85; …)"` (sanity) → `"(A ve B kendine geldi)"` (A and B came to their senses), keeping other notes;
- `" kesif seferine"` → `" keşif seferine"` (exploration expedition).

**Rewrite**: never format enum keys into text; render labels from enums at write time.

### 20.5 Chronicle duplicate hiding (`kronik-onar.js`)

Background: the engine's note path writes each note as a `dunya`-kind row at epoch end. Some functions also write the same event directly with their own kind (foreign-god awakening, first contact, civilization rise, interworld treaty …), which produced two rows per event.

- `sonKronikId()` (last chronicle id) = MAX(id).
- `tekrarMi(note, row, {kimlikSiki})` (is duplicate): normalized text equal (ignoring a trailing `.`/`!`) → true. Else compare entity ids: with `kimlikSiki` (strict ids) the id sets must be equal; otherwise if both are non-empty they must intersect. Then the note's **subject** (leading name before an apostrophe, punctuation or the first lowercase word) must appear in the row. Then ≥`KRONIK_TEKRAR.ortak`% of the note's non-subject word stems (first `KRONIK_TEKRAR.kok` letters; words longer than 2 chars; Turkish conjunctions excluded) must occur in the row.
- `motorTekrarlari(cag, notes, start)` (engine duplicates): each pending engine note carries `iz` (the last chronicle id when it was produced). A note is a duplicate if any direct (non-`dunya`/`motor_ham`) row of this epoch with id in (previous note's iz, next note's iz] satisfies `tekrarMi`. Such notes are written only as `motor_ham` (hidden).
- `kronikTekrarOnar()` (history fix): per epoch, for `dunya` rows: an identical (text + ids) second row → hidden. A folded summary row ending "; bu çağ aynı türden N olay daha yaşandı." ("; N more events of the same kind happened this epoch") whose N+1 following `motor_ham` members are all covered (strict) by earlier direct rows → hidden. Otherwise a row covered (strict) by an earlier direct row → hidden. "Hidden" = `tur: 'dunya' → 'motor_ham'`.

Rules `KRONIK_TEKRAR` (group "Chronicle"):

| Key (new) | Old | English | Default | Min | Max |
|---|---|---|---|---|---|
| chronicle_dedupe.stem_letters | kok | First letters counted as the word stem in duplicate comparison | 5 | 2 | 20 |
| chronicle_dedupe.overlap_pct | ortak | Min % of the note's stems present in the row to count as a duplicate | 50 | 1 | 100 |

**Rewrite**: give each engine event a stable `event_key` and write it once. A direct write and a note with the same key are merged at the source.

### 20.6 Awakened foreign-god text (`uyananTanriMetni`)

`uyanikMetin(text)` (awake text) rewrites "…, ama (o) henüz uyanmadı." ("…, but has not yet awoken.") → ". Uzun uykusundan sonunda uyandı." ("Finally woke from its long sleep."); "henüz uyanmadı" → "artık uyanık" ("now awake"); "Uykudaki"/"uykudaki" (sleeping) → "Uyanmış"/"uyanmış" (awakened). `uyanisMetniYaz(id)` (write awakening text) applies it to `unvan` and `aciklama` (the panteon module also calls it at awakening). The repair applies it to every non-sleeping foreign god, and to first-contact chronicle lines ("İlk temas:…" containing "uykudaki" or "henüz uyanmadı"). **Rewrite**: store `status` separately and render the title from the status, so the text never says "sleeping" on its own.

### 20.7 Epoch-start years (`cagBasiYillari`)

The bug: lines written into the new epoch during the transition took years from the *old* epoch's Fate window, and because years never decrease, the entire new epoch got stuck at a late year.

For each system line `"Çağ N başladı (dünya yılı Y)"` ("Epoch N began (world year Y)") in epoch N:
- If its own `yil` ≠ Y and `< Y + 0.5*Y_epoch` → set it to Y.
- Take the epoch's rows by id; the "stuck run" = leading rows with `yil ≥ Y + 0.5*Y_epoch`. If any: the anchor is the first row after the run (if the run reaches the end of a past epoch, its last row; in the current epoch, none). Re-spread the run by wall-clock creation time: `yil = Y + floor((anchorYear − Y) * clamp((t − t0)/(t1 − t0), 0, 1))` (all Y if t1 ≤ t0).

### 20.8 Discovery-reason text (`ufuk.kesifNedenOnar`)

Raw tag lists leaked into "X, <tags>, bilinmeyen topraklara açıldı" ("X, <tags>, set out for unknown lands") chronicle lines, `kesfetti` bond descriptions, and engine descriptions "(…) bilinmeyen topraklara açıldı ve onu buldu" ("… set out for unknown lands and found it"). Raw tags are replaced with a generated reason sentence (`kesifCumlesi`). Returns `{kronik, bag, aciklama}`.

### 20.9 One-time text repair (`world.metinOnarimi`, gated by `veri_surum<2`)

In one transaction: recompute non-manual suffix info for entities and sons (LANGUAGE-SPECIFIC); run `ekDuzelt` over every `AD_ALANLARI` text containing an apostrophe (LANGUAGE-SPECIFIC); flip reversed bonds for types in `BAG_YONU` + `tapar`. Returns `{ek, metin, bag}` (suffix, text, bond). Only the bond flip is portable.

---

## 21. Knowledge-network repair (`agonar.js`)

Goal: increase the graph's connectivity **only** with bonds the data itself implies, or that a justified narrative supports. Never invent bonds.

### 21.1 Health metrics (`agSagligi`)

Nodes: entities with status canon/dead/fulfilled and `bekliyor=0` (`v<id>`), all sons (`o<id>`), all foreign gods (`y<id>`), the creator (`t1`). Edges: **visible** bonds (§6.4 `GORUNUR_BAG`, active and past), undirected, between existing distinct nodes (a target of type `t` maps to `t1`).

Returns: node count; edge count; past-edge count; active edges; mean degree (2 decimals); median degree; density `2E/(N(N−1))`; the number of connected components; largest component size and share %; isolated count (degree 0); degree-1 count; weak count (degree ≤ `AG.zayif_derece`); active `ilgili` count and those without a description; the weakest `AG.liste` nodes (degree ascending, then importance descending) as `{id, ad, tur, derece}`; the in-memory repair log (newest first, ≤`AG.liste` entries); and the count of priority records (§21.3).

### 21.2 Rule-based dangling-end repair (`kopukUclariOnar(cag)`) — at startup, at epoch end when `AG.oto_onar`, and manually (`/api/ag/onar`, recorded in the ledger)

In one transaction:
1. `ilgiliCevir` (convert "related"): delete legacy `bilirdi`/`konusurdu` bonds. Convert `ilgili` by description: "ruhu oraya indi" → `ruhu_indi`; "taraf"/"galip"/"mağlup"/"galip (…" (side/victor/defeated) → `taraf`; "federasyon üyesi" (federation member) → `uyesi`; "keşfetti" (discovered) → `kesfetti`. → `ilgili_cevrilen`.
2. **Inside**: each canon-ish, non-pending entity whose location is canon-ish and has **no bond at all** to its location (either direction) → `addBag(v→loc, 'icinde')`.
3. **Event → place**: each canon-ish event with a location and with no outgoing `neden_oldu` and no non-`icinde` visible bond → `neden_oldu` to its location, "vurduğu yer" (the place it struck).
4. **Lost knowledge**: canon-ish knowledge entities with no active `bilir` bond → tag `kayıp` (lost). It can be rediscovered in ruins; past knowers stay linked through past bonds.
5. **Dead language**: canon-ish languages with no active `konusur` → tag `ölü dil` (dead language).
6. **Eclipse prophecy with no bonds at all** → `gok.tutulmaKahinleri(id, world, cag)` (the world's most important communities "whisper" it; sky module).
7. **Fulfilled prophecy** with no outgoing `kehanet_eder` → `kehanet_eder` ("gerçekleşti", fulfilled) to the entities named in its Fate note (`metindekiKayitlar`, same world).
8. **Previous-creation knowledge** (tag `önceki yaratılış`) with no incoming `kaynagi` → `kaynagi` from the first canon-ish place in the same world tagged `önceki yaratılış` ("kalıntılarda saklı", hidden in the ruins).
9. **Temple destruction**: chronicle rows of kind `yabanci_tanri` starting "<god>," and containing "yıktı" (destroyed) → for each referenced existing entity without an active `yok_etti` y→v bond: add `yok_etti` y→v ("tapınağını yıktı", destroyed its temple), dated to the row's epoch.
10. **Event centres** (`olayMerkezleri`), for each canon-ish non-pending event:
    - tagged `afet` (disaster): the disaster kind = first of deprem, sel, veba, kuraklik, firtina (earthquake, flood, plague, drought, storm) in the tags, else the subtype. Target = the first `neden_oldu` target, else its location. For each canon-ish descendant in the containment tree under the target (BFS) that existed at the event's epoch (born ≤ event epoch, and not died before it): communities (people, settlement, cult, faction) and structures → `neden_oldu` ("<kind> vurdu", <kind> struck). Dead mortals who died in the event's epoch and whose Fate note mentions the disaster word → `neden_oldu` ("orada öldü", died there).
    - war/battle/siege subtype: `taraf:<id>` tags → `taraf` ("savaşın tarafı", side of the war). Visible `esir` (captive) bonds whose description = event name → `neden_oldu` to the captive ("esir düştü", was captured). Visible `hasim` (rival) bonds whose description = event name → `taraf` for both duelists ("düelloya tutuştu", fought a duel). Commanders (`komutan`) of armies that are `parcasi` (part of) the event → `taraf` ("komutan", commander).
    - any event with name length ≥ `AG.ad_en_az`: other canon-ish non-pending entities whose Fate note contains the event's name: dead and the note after the name says "fell / died / gave his life / lost his life / perished" → `neden_oldu` ("orada can verdi", died there); else `ilgili` ("kaderinde anılır", mentioned in its fate). Dated `max(event epoch, entity birth)`.
    - Each addition is via `tekBag` (single bond): skip self-loops and skip if a visible same-direction same-type bond exists.
11. **Narrative bonds** (`anlatiBaglari`), for legends, traditions and artworks:
    - subjects = entities named in description + Fate note (same world, up to `AG.konu_tavan`, excluding self). For each with no visible v-v bond to it in either direction → `anlatir` ("konusu", its subject).
    - carrier: if no visible `kutlar`/`anlatir`/`uretti` from a people, settlement, cult, faction or mortal exists → carrier = maker (if a community or mortal), else location (if a community), else the first community among the subjects. Tradition → `kutlar` ("yaşatır", keeps it alive); others → `anlatir` ("anlatır", tells it).
12. **Still isolated** (no visible bond at all) entities with `yapan_id` → `uretti` from the maker (if it exists). Else with `yaratan_id` → `uretti` o→v ("yarattı", created).

Returns counters `{icinde, neden_oldu, uretti, olay, anlati, kehanet, kalinti, yikim, kayip, olu_dil, ilgili_cevrilen, toplam}`, where `toplam` (total) excludes kayip, olu_dil and ilgili_cevrilen. Logs "<total> dangling ends connected (inside …, struck place …, event …, narrative …, prophecy …, ruin …, destruction …, produced …)[; <n> vague bonds converted to concrete types]."

`metindekiKayitlar(text, {haric, dunyaId, limit = AG.oneri_tavan})` (records in text): canon-ish, non-pending entities with name length ≥ `AG.ad_en_az` whose name occurs in the text (SQL `instr`), optionally in the same world. Ordered by name length desc, then importance desc. Then a word-boundary check: no letter before, no lowercase letter after (so "Ala" does not match inside "Alaz"; a following suffix is allowed). Exclude `haric` (exclusions), take `limit`.

### 21.3 LLM bond suggestions (Fate)

**Candidate selection**:
- `zayifKayitlar(limit = AG.kader_parti)` (weak records): canon-ish non-pending entities not reviewed within `AG.tekrar_cag` epochs (`ag_bakis.cag > now − tekrar_cag`) with visible-degree ≤ `AG.zayif_derece`, ordered by degree asc, importance desc, id.
- `oncelikliKayitlar(limit)` (priority records): events, legends and traditions not recently reviewed, ranked by the number of distinct canon-ish entities co-mentioned with them in the chronicle but **not** bonded to them (desc), then importance. Only those with > 0.
- `adayKomsular(v)` (candidate neighbours, ordered, deduplicated, excluding self): co-mentioned in the chronicle (most frequent first, up to `max(AG.aday, cap*2)`), its location ("konumu"), its maker ("yapanı"), its creator son ("yaratanı"), siblings at the same location (by importance, up to `AG.aday`, "aynı yerde" same place), important entities of its world excluding regions ("dünyasının önemlisi", important in its world). Truncated to `max(AG.aday, cap*2)*2`. `cap` = `max(AG.oneri_tavan, AG.olay_oneri_tavan)` for events, else `AG.oneri_tavan`.
- `dugumSatiri(k)` (node line): sons → `o<id> [oğul] <name>[, <title>]`; entities → `v<id> [<type>[ / <subtype>][, <status if not canon>]] <name>: <description truncated to AG.aciklama_kirp/2>`.

**`kaderBagOner({sor, ids, yayinla})`** (Fate suggests bonds): targets = `ids` or `zayifKayitlar()`, canon-ish only, up to `AG.kader_parti`. Emits a system event "Fate is looking at <n> weakly connected records…". Calls the structured LLM `sor('derinlik', {...})` (model key "derinlik"; job name "Ağ onarımı" (network repair)).

Output schema:
```json
{"type":"object","required":["baglar"],"properties":{"baglar":{"type":"array","items":{"type":"object",
 "required":["kayit","diger","yon","tur","gerekce"],
 "properties":{"kayit":{"type":"string"},"diger":{"type":"string"},
   "yon":{"type":"string","enum":["kayittan","digerinden"]},
   "tur":{"type":"string","enum":"<ONERI_TURLERI>"},"gerekce":{"type":"string"}}}}}}
```
English field names for the rewrite: `bonds[].record`, `other`, `direction ∈ {from_record, from_other}`, `type`, `reason`. `ONERI_TURLERI` (suggestable types) = the narrative bonds without `ilgili`, plus `taraf`: anlatir, sever, korkar, kehanet_eder, yasaklar, pesinde, yoldas, parcasi, kaynagi, neden_oldu, kutlar, soyundan, taraf.

System prompt (translated in full):
> You are Fate, the scribe of the world of <world name>. For records that stand disconnected in the knowledge network, you build only the bonds that the narrative and the chronicle truly support. If there is no evidence you build no bond: an empty list is a valid answer. Each bond is chosen ONLY from that record's CANDIDATES; no invented ids are used. The reason is in <language>, concrete and short (why they are connected). At most <AG.oneri_tavan> bonds per record; at most <event cap> for an event (war, disaster): events are the centres of the network, so connect to them the participants, victims and consequences mentioned with them in the chronicle. Types: <comma list>. One bond per pair: choose one type between the same two records, do not build a reciprocal or a second type; skip a pair that is already bonded. "parcasi" goes from part to whole (tradition → people, language → people, spirit → region, person → community; not the reverse). "yoldas" is only between living beings and communities (mortal, species, army, spirit, faction, cult, people; son) and describes something concrete lived through together. A shared theme, motif or image alone is not a reason: do not build a bond for such a pair.

(Original: "Gerekçe Türkçe" = "the reason is in Turkish". In the rewrite, use English.)

User prompt: for each target, `KAYIT <node line>\nADAYLAR:\n- <node line> (<why candidate>)` ("RECORD …", "CANDIDATES:"), with targets separated by blank lines.

Application (one transaction), for each suggestion:
- resolve the record (`v` prefix optional) among the targets, and `other` among that target's candidates (exact key); else skip;
- reason must be ≥ `AG.gerekce_en_az` chars, must not match `ORTAK_TEMA` (shared-theme regex: "theme shared/same", "shared/same/similar theme/motif/image", "shares the motif", "carries the theme"), and the type must be in the suggestable list;
- per-record cap: `AG.oneri_tavan`, or for events `max(oneri_tavan, olay_oneri_tavan)`;
- direction: `from_other` → (other → record), else (record → other), then `bagYonu` (flips a reversed `parcasi`);
- skip if the two nodes already share **any** active bond in either direction (`ciftBagli`);
- `yoldas` (companion): both ends must be son, foreign god or companion types, and the reason must be ≥ `AG.yoldas_gerekce_en_az` chars with ≥ `AG.yoldas_sozcuk_en_az` words and not a shared theme;
- `addBag(…, reason, w.cag)`.

Then upsert `ag_bakis(varlik_id, cag)` for every target, write the repair log, and emit an `ag_onarim` event `{kind:'ag_onarim', tur:'kader', metin, baglar:[{a:{t,id,ad}, tur, b:{…}, gerekce}], bakilan:[…]}`. Summary text: "Fate looked at <n> records and built <k> justified bonds." / "…; it found no bond with enough evidence."

**`ilgiliAdlandir({sor, limit = AG.ilgili_parti, sonId})`** (name vague "related" bonds): active `ilgili` bonds without a description and `id > sonId` (cursor), ordered by id, up to `limit`, where both node lines resolve. Emits "Fate is naming <n> vague 'related' bonds…".

Output schema `{kararlar:[{no:int, karar: enum(ONERI_TURLERI + ['ilgili','kapat']), gerekce:str}]}` (decisions: number, verdict, reason). English: `decisions[].n`, `verdict ∈ suggestable ∪ {related, close}`, `reason`.

System prompt (translated):
> You are Fate, the scribe of the world of <world name>. For each bond, look at the narrative of its two ends and choose a concrete type (<types>). If none fits but the bond is meaningful, say "ilgili" (related) and state the relation clearly in the reason. If the bond is meaningless, say "kapat" (close). The reason is in <language>, short and concrete.

User prompt: `no <i>: <node line A>\n   → <node line B>` per bond.

Application: `kapat` → deactivate with description `"kapatıldı: <reason>"` (cut to `AG.aciklama_kirp`). `ilgili` with a reason matching `INKAR` (denial) → close the same way. Otherwise skip if the reason is shorter than `AG.gerekce_en_az` or the verdict is invalid. Else `UPDATE tur=verdict, aciklama=reason`. Summary: "Fate looked at <n> vague bonds: <a> named, <c> closed." Returns `{bakilan, adlandirilan, kapatilan, sonId: last id}` (reviewed, named, closed). The cursor prevents re-asking about bonds Fate left undecided.

Callers: epoch end (`epoch.js`, when `AG.kader_oto`): `kaderBagOner` over the weak + priority records (priority share `AG.oncelik_payi`%, total per epoch ≤ `AG.kader_cag_tavan`), and `ilgiliAdlandir` up to `AG.ilgili_cag_tavan`. Manual: `/api/ag/kader` (with `tam`, full), `/api/ag/kader/durdur` (stop), `/api/varliklar/:id/bag-oner` (a single entity).

### 21.4 Legacy network-repair cleanup (`agBagOnarimi`)

In one transaction:
- reversed active `parcasi` v-v → swap (`ters_parcasi`, reversed part-of);
- active `yoldas` (companion) with invalid ends → close with "yoldaşlık değil, yalnızca ortak tema" (not companionship, just a shared theme) if the description is a shared theme, else convert to `ilgili` (`yoldas_uc`); valid ends but a shared-theme description → close "yalnızca ortak tema" (only a shared theme) (`zayif_yoldas`);
- for "singular" narrative types (narrative types except `ilgili`, `neden_oldu`, `kehanet_eder`): group active bonds by type and unordered node pair. If there are more than one, keep the correctly-directed one with the lowest id and close the others "aynı çiftte yinelenen bağ" (duplicate bond on the same pair) (`yinelenen_cift`);
- active `yoldas` whose description ≠ "yol arkadaşlığı" (the engine's travelling-companion description) and where another active bond exists on the same ordered pair → close "aynı çiftte daha somut bir bağ var" (a more concrete bond exists on the same pair) (`fazla_yoldas`).

Closing appends the old description: `"kapatıldı: <reason> (<old desc>)"`, cut to `AG.aciklama_kirp`.

Rules `AG` (group "Network"):

| Key (new) | Old | English | Default | Min | Max |
|---|---|---|---|---|---|
| network.auto_repair | oto_onar | Dangling ends repaired automatically at epoch end (1 on, 0 off) | 1 | 0 | 1 |
| network.fate_auto | kader_oto | At epoch end Fate suggests justified bonds and names vague ones (1/0) | 1 | 0 | 1 |
| network.weak_degree | zayif_derece | Records with this many or fewer bonds count as weak | 1 | 0 | 100 |
| network.fate_batch | kader_parti | Max records per Fate request | 12 | 1 | 200 |
| network.fate_epoch_cap | kader_cag_tavan | Max weak records Fate reviews per epoch | 36 | 0 | 100000 |
| network.candidates | aday | Candidate neighbours shown per record | 10 | 1 | 100 |
| network.suggest_cap | oneri_tavan | Max new bonds per record per pass | 3 | 1 | 20 |
| network.reason_min | gerekce_en_az | Min reason length (chars) | 15 | 0 | 1000 |
| network.companion_reason_min | yoldas_gerekce_en_az | Min "companion" reason length (must describe something lived together) | 40 | 0 | 1000 |
| network.companion_words_min | yoldas_sozcuk_en_az | Min words in a "companion" reason | 6 | 0 | 100 |
| network.review_cooldown | tekrar_cag | Epochs before a reviewed record is re-reviewed | 10 | 0 | 10000 |
| network.related_batch | ilgili_parti | Max vague "related" bonds named per request | 40 | 1 | 1000 |
| network.related_epoch_cap | ilgili_cag_tavan | Max vague bonds named per epoch | 80 | 0 | 100000 |
| network.desc_clip | aciklama_kirp | Description length shown to Fate (chars) | 300 | 50 | 10000 |
| network.list_size | liste | Weakest records and recent repairs listed | 20 | 1 | 1000 |
| network.name_min | ad_en_az | Min name length to link a record mentioned in text (short names mismatch) | 4 | 1 | 100 |
| network.event_suggest_cap | olay_oneri_tavan | Max bonds per pass for a much-mentioned event (war/disaster participants) | 8 | 1 | 100 |
| network.priority_share_pct | oncelik_payi | Share of each Fate pass for priority events/legends/traditions (%) | 50 | 0 | 100 |
| network.subject_cap | konu_tavan | Max subjects linked for a legend/tradition/artwork from names in its description | 5 | 0 | 100 |
| network.healthy_main_pct | ana_obek_iyi | Connectivity shown as healthy when the main component exceeds this % | 95 | 0 | 100 |

---

## 22. Backups and archive policy (`db.js`)

### 22.1 Taking a backup (`yedekAl(label='elle')`)

1. `gorselleriYedekle()` (back up images): copy every referenced image (safe name `^[\w-][\w.-]*$`) from the image dir into the shared pool `yedekler/gorseller/` if it is not already there (content-addressed by name; each file is copied once).
2. File name: `aerona-<label sanitized to [\w-], ≤40, default 'elle'>-<local YYYY-MM-DDTHH-MM-SS-mmm>-<4 random base36>.db`.
3. `VACUUM INTO '<path>'` (consistent online copy).
4. `telemetriAyikla(path)` (strip telemetry): open the copy, `DELETE FROM gunluk, llm_olcum`, `VACUUM`.
5. Secondary target: if `$AERONA_YEDEK2` is set, copy the file there and keep the newest `YEDEK.ikinci` `aerona-*.db` files by mtime.
6. `yedekleriBuda()` (rotate); if anything was deleted → `havuzuBuda()` (prune the pool).
7. Return the file name.

Labels in use: `cag<N>` (before epoch N; taken at epoch start unless the epoch is being resumed), `elle` (manual: `/api/yedek`), and safety labels `geri-yukleme-oncesi` (before restore), `ice-aktarim-oncesi` (before import), `sifirlama-oncesi` (before reset).

Also: `gorseliHavuzaKoy(file)` (put image in pool) copies an uploaded or generated image into the pool immediately, so images newer than the last backup are not lost.

### 22.2 Rotation (`yedekleriBuda`)

The label is parsed from `^aerona-(.+?)-\d{4}-\d{2}-\d{2}T` (unparseable → `elle`). Sort all `.db` files by mtime desc.
- Epoch backups (`cag\d+`): delete those with index ≥ `YEDEK.cag` **unless** the epoch number is divisible by `YEDEK.onluk` (every 10th epoch is kept forever).
- Manual: keep the newest `YEDEK.elle`.
- Each other (safety) label: keep the newest `YEDEK.guvenlik` per label.

Returns the number deleted.

### 22.3 Image pool pruning (`havuzuBuda`)

Used = image file names referenced by the live DB ∪ every backup DB (opened read-only; if **any** backup cannot be opened, abort and delete nothing; backups without an image table are ignored). Delete pool files that are unused and have a safe name.

### 22.4 Listing and validation

- `yedekler()` (list backups): `[{dosya, boyut, tarih}]` (file, size, mtime ISO), newest first.
- `yedegiDogrula(path)` (validate backup): open read-only ("Could not open the backup file."), `PRAGMA quick_check == 'ok'` ("The backup file is corrupt."), and tables dunya, ogullar, varliklar, kronik all present ("This file is not an Weavers of the Void world.").

### 22.5 Restore (`yedektenDon(file)`) — `/api/yedek/geri` requires the confirmation text "GERİ YÜKLE" (RESTORE) and no running jobs

1. Sanitize the name (`[^\w.\-]` removed). It must exist in the backup dir ("No such backup.") and end in `.db` ("Only .db backups can be restored.").
2. Validate.
3. Safety backup `geri-yukleme-oncesi`.
4. `dosyadanDon(path, {koru: TELEMETRI})` (load from file, keeping telemetry).
5. The server's "world changed" hook (§29). Returns the safety backup name.

`dosyadanDon(path, {koru})` (generic load; used by restore, import and discovery):
1. `skip = koru ∪ {kronik_varlik}`.
2. `PRAGMA foreign_keys=OFF`; `ATTACH '<path>' AS yedek`.
3. Main tables = real tables not starting with `sqlite_`. Backup tables = real, non-virtual tables in the attached DB.
4. In one transaction, for each main table not skipped: `DELETE` all rows. If the backup has the table: the common columns are the intersection of the column names, and `INSERT INTO main.t (common) SELECT common FROM yedek.t`. Columns missing in old backups take their defaults; extra columns in the backup are ignored.
5. Commit (rollback on error), `DETACH`, `foreign_keys=ON`.
6. `gorselleriGeriGetir()` (restore images): copy back any referenced image missing from the live dir but present in the pool.
7. `veriGecisleri()` (01 §11): rebuilds `kronik_varlik`, the cosmos migration, year spreading, and so on, for old-schema backups.

### 22.6 Download

`GET /yedek/<file>.db` streams the raw backup. `GET /yedek/<name>.aerona` wraps a backup as an export package (§23.1, using `disaAktarDosya({kaynak: backupPath})`).

**Rewrite notes**: keep `VACUUM INTO` (it is fine for SQLite). Store the backup manifest (label, epoch, created, size, image refs) in a JSON sidecar to avoid opening every backup when pruning. Validate restores into a temp DB, then swap files atomically (instead of DELETE+INSERT into the live DB), and restart the connection pool.

### 22.7 Media store in the rewrite (decision 77)

The rewrite has no image directory and no backup image pool. Every image byte lives in one object store behind the `MediaStore` interface (`media/store.py`): an S3-compatible store (MinIO in Docker, `media/s3_store.py`) or a filesystem store for local development and tests (`media/file_store.py`), chosen by `AERONA_MEDIA_BACKEND`. The browser never reaches the store; it reads `/api/media/<file>` through the backend.

- **Keys.** Originals live at `originals/<file name>`, thumbnails at `thumbnails/<width>/<stem>.webp` for the fixed widths 64, 160, 320 and 640. Keys are validated segment by segment (no `..`, safe characters only, bounded length).
- **Content addressing.** An `images` row stores the `object_key`, the `sha256` of the original bytes, the MIME type and the size. Uploading or generating the same bytes twice for one record reuses the existing row; the same bytes for a different record share the stored object. The API image record exposes `content_type` (the MIME type) and `sha256`.
- **Thumbnails** are rendered on the first request for a width and cached in the store; every response carries an immutable cache header and an ETag.
- **Generated images** (SVC-109) go straight into the store as originals, exactly like uploads; there is no separate pool copy, because the store itself outlives the database and every backup references its objects by key.
- **Backups** record the object keys they reference in the JSON sidecar (`objects`). The live database plus every backup sidecar (or the backup file itself when the sidecar is missing) form the reference set.
- **Garbage collection** replaces the legacy pool pruning (§22.3): the collector deletes originals and thumbnails that no live row and no backup references and that are older than a grace period (one hour), so an image written between a reference scan and the sweep is never lost. If any backup cannot be read the sweep deletes nothing. It runs with the epoch-end prune and from Settings › Maintenance (`prune`).
- **Restore and reset** never delete objects; the next sweep removes what nothing references any more.

---

## 23. Export, import, discovery mode (`paylasim.js`)

### 23.1 Package format `.aerona`

Legacy version 1 was a gzip-compressed JSON object:
```json
{"bicim":"aerona-dunya","surum":1,"ad":"<world>","cag":<epoch>,"tanri":"<creator>","tarih":"<ISO>",
 "db":"<base64 of a telemetry-free SQLite file>","gorseller":{"<file name>":"<base64>"}}
```
The legacy file name is `<world name with non-letter/digit runs → '-', ≤40>-cag<epoch>.aerona`.

**Rewrite: package version 2** (`services/world_package.py`, decision 77). A `.aerona` file is a gzip-compressed tar stream with three kinds of members, written in this order:

1. `manifest.json` (at most 8 MB): `{"format":"aerona-world","version":2,"name","epoch","creator","date","objects":[{"key","sha256","size"}]}`. `objects` lists every original image the database references, by store key, with its digest and size.
2. `world.db`: the telemetry-free SQLite copy (`VACUUM INTO`), streamed from disk.
3. `media/<object key>`: one member per listed object, streamed from the media store.

The file name is `<world name with non-letter/digit runs → '-', ≤40>-epoch<epoch>.aerona`.

Reading streams the archive once and never holds it in memory. The manifest must come first, carry `format` = `aerona-world` and a `version` no newer than 2 ("This file was made with a newer Weavers of the Void version."). Each media member must be listed in the manifest, stay under 30 MB and match its declared `sha256` and size; unlisted, oversized or mismatching members are rejected. The total decompressed size is capped at 500 MB (compression-bomb guard) and the upload at 400 MB. An imported object whose digest is already in the store reuses the stored object; otherwise it is written under its own key, or under a fresh `imported-<token>-` key when different bytes already use that key. The imported database rows are then relinked to the stored keys, rows whose object never arrived are dropped, and covers are re-promoted. If the import fails, every object it wrote is deleted again. Version 1 packages are not read: the rewrite does not import legacy worlds through the package path (decision 2: the migrator handles legacy data).

### 23.2 Export

- `disaAktar({gorseller=true})` (export, in memory): `VACUUM INTO` a temp file in `data/kesif/`, strip telemetry, base64-embed the DB, and base64-embed every referenced image whose name is safe (`^[\w\-][\w.\-]*$`, ≤200 chars, raster extension png/jpg/jpeg/webp/gif/avif) and exists. Gzip. Delete the temp file.
- `disaAktarDosya({gorseller, kaynak})` (export to file, streaming; used by the API): the source = a copy of `kaynak` or `VACUUM INTO`. Strip telemetry. Read the name, epoch and creator, and the image list (safe names), from the copy. Stream the JSON: the header without its closing brace, then `,"db":"` + the DB base64 in chunks of 196,608 bytes (a multiple of 3, so the base64 pieces concatenate without padding), then `","gorseller":{` + `"name":"b64"` for each image found in the live dir or else the pool, then `}}`. The stream is piped through gzip into `data/kesif/disa-<id>.aerona`. Returns `{ad, yol, boyut, sil()}` (name, path, size, delete). The server streams the file and then deletes it.

### 23.3 Import (`iceriAktarAsync(buf, {mod})`; `/api/dunya/ice-aktar?mod=degistir|kesif`)

Preconditions: not in discovery mode ("You are in discovery mode; return to your own world first."), buffer not empty ("The file is empty."), size ≤ 400 MB ("The file is too large."), no jobs running; `mod=degistir` (replace) requires `onay=DEĞİŞTİR` (REPLACE).

1. Async gunzip with `maxOutputLength` = 500 MB. Overflow → "When opened, the file is too large (it may be a compression bomb)." Other failure → "This is not an Weavers of the Void world file (could not be opened)."
2. `paketAc` (open package): JSON parse. `bicim` must equal `aerona-dunya` ("This is not an Weavers of the Void world file."); `surum` ≤ 1 ("This file was made with a newer Weavers of the Void version."); `db` must be a non-empty string.
3. Write the DB to `data/kesif/ice-<ts>-<rand>.db`. Open it with FKs off and `trusted_schema=OFF`: `quick_check` ok; the 4 core tables exist; the world row exists; **no virtual tables**; drop all triggers and views; delete `gorseller` rows with unsafe names. Any failure → delete the file, "The database in the file is corrupt or not an Weavers of the Void world."
4. Write the images: for each safe name with a string value, write it to the image dir only if it does not exist (flag `wx`). Track the written ones; if this fails, delete the written ones and the DB file and rethrow.
5. Mode `kesif` (discovery):
   - `VACUUM INTO data/kesif/kendi-<ts>.db` (own world copy).
   - **First** write the state file `data/kesif.json` = `{kendi, misafir:{ad, cag, tanri, tarih}, gorseller:[written], baslangic}` (own copy, guest, images, start) atomically (tmp file + rename), so that a crash during the load still leaves discovery mode recoverable.
   - `dosyadanDon(importPath)`. On failure delete the state file and own copy, then rethrow.
   - Return `{tamam, mod:'kesif', dunya: package meta}` (ok, mode, world).
6. Mode `degistir` (replace): safety backup `ice-aktarim-oncesi`, then `dosyadanDon(importPath)`. Return `{tamam, mod, dunya, guvenlik}`.
7. On any failure, delete the images written by this import. Always delete the temp import DB.

The server then calls "world changed" with the message "Discovery mode: <name> (Epoch <n>) opened read-only. Your own world is waiting aside." or "<name> imported. The previous world was saved as <backup>."

### 23.4 Discovery (read-only guest) mode

- `kesifDurumu()` (discovery state): if `data/kesif.json` exists → its parsed content; if it is unparseable → `{bozuk:true, misafir:null}` (corrupt; still counts as discovery mode so the guest world cannot be written to and the own-world trail is not lost).
- `saltOkunur()` (read-only) = state exists. The server rejects every non-GET request except `/api/kesif/bitir` with "Discovery mode: this world is read-only. Return to your own world to make changes." Startup repairs, the completion job, bulk jobs and image generation are all skipped.
- `kesifBitir()` (end discovery): the state must exist ("You are not in discovery mode."). Own copy = the recorded path, else the same file name in `data/kesif/`, else the newest `kendi-*.db` there. None → "Your own world's copy was not found: <path>". `dosyadanDon(own)`. Delete the guest images that the own world does not reference. Delete the state file and own copy. Return `{tamam, misafir}` (ok, guest). The server: "Discovery ended; <guest name or 'the guest world'> closed, you are back in your own world."
- `/api/state` includes `kesif` = the guest meta or `{ad:'unknown guest world', bozuk:true}`.

**Rewrite**: open the guest DB as a separate read-only connection instead of swapping the live DB's contents. This removes the risk entirely and needs no own-world copy.

---

## 24. Genesis wizard (`sihirbaz.js`)

Inputs: sliders, choices, templates. `GET /api/sihirbaz` → `{sablonlar, secenekler}` (templates, options).

Options (`SECENEKLER`):
- `teknoloji` (technology): `tas` stone age · `tunc` bronze age · `demir` iron age · `ortacag` medieval · `ronesans` renaissance · `buhar` steam and gunpowder.
- `dil` (language texture): `akici` flowing, vowel-rich, soft (l, m, n, y) · `sert` hard consonants, short syllables (k, t, g, r) · `girtlak` guttural, deep (h, ğ, q, kh) · `islikli` sibilant, fricative (s, ş, z, ç) · `uzun` long, agglutinative, polysyllabic · `karisik` free.
- `kozmos`: `tek` single world · `kucuk` small cosmos (1 + `SIHIRBAZ.kucuk_kozmos` worlds) · `buyuk` large cosmos (1 + `SIHIRBAZ.buyuk_kozmos` worlds).

Templates:

The templates, their seeds and their typed values (storyteller, cosmos shape, first world kind, climate age, world age) are listed in `13-depth-expansion.md` §10.19, which supersedes the legacy table that stood here. Legacy keys map once on import: `karanlik_fantazi` → dark_fantasy, `mitoloji` → mythic_age, `kozmik_korku` → cosmic_horror, `masal` → fairy_tale, `yildiz_mitosu` → star_myth, `kum_ve_kul` → sand_and_ash.

`sihirbazTemizle(b)` (sanitize wizard input):
- `sablon` (template) only if it is an own key of `SABLONLAR` (prototype keys such as "toString" are rejected).
- Each field = `b[k] ?? template[k] ?? default`.
- `buyu` (magic) / `karanlik` (darkness, now **danger**): round and clamp to 0–100 (null or '' → default `setup_wizard.magic` / `setup_wizard.danger`). The new app adds the cosmos shape, the second layer kind and the first world's kind, water, high ground, moisture, climate age and age (13 §10.19).
- `teknoloji` → valid key, else `demir` (iron). `dil` → valid key, else `karisik` (free).
- `halk` (peoples): clamp to 1..`SIHIRBAZ.halk_en_cok`, default `SIHIRBAZ.halk`. `kozmos` → valid key, else `tek` (single).
- `ton` (tone) = `b.ton || template.ton`, ≤300 chars, else null. `tohum` (seed) = `b.tohum || template.tohum`, ≤2000 chars, else null.

`sihirbazMetni(p)` (wizard text; appended to the genesis prompt), translated:
```
GENESIS SETTINGS[ (template: <name>)]:
- Magic density <buyu>/100: the world is <degree(buyu, 'magical')>. Regions' magic values should be close to this.
- Danger <danger>/100: the world is <degree(danger, 'dangerous')>. Regions' danger values should be close to this.
  (new app: the first world's kind, surface, climate age and age, and the cosmos shape and second layer follow when chosen; 13 §10.19)
- Technology era: <tech label>. The peoples' tools, weapons and buildings are at this level.
- Language structure: <lang label>. The naming rule and all names use this sound texture.
- Cosmos: <cosmos label>.
```
`degree(n, a)`: n≥80 "very a"; ≥60 "a"; ≥40 "moderately a"; ≥20 "slightly a"; else "hardly a at all".

Applied in code after the LLM genesis:
- `bolgeEgilimi(stats, p)` (region bias): each genesis region's `buyu` and `tehlike` = `round(v*(100−c)/100 + target*c/100)`, with `c = setup_wizard.setting_pull_pct`, targets = magic and danger, missing values = 50. This is the only pull: the model's region values are stored as written before it, and the first world's danger becomes the mean of its pulled regions.
- The server wakes `p.halk` peoples (`halklariUyandir`), then births `ekDunyaSayisi(p)` (extra world count: single 0 / small `kucuk_kozmos` / large `buyuk_kozmos`) extra worlds via `kozmos.dunyaDogur`. New app: the inspiration is "The <n>th world of this creation, grown from the same seed as the first world: <seed>", with no mandate to differ; the first world is born around its own sun, and the further worlds circle that sun, circle suns of their own or lie in a second layer, by the cosmos shape (13 §10.19).
- The settings are saved in `dunya.yaratilis_ayar`.

Rules `SIHIRBAZ` (group "Genesis wizard"):

| Key (new) | Old | English | Default | Min | Max |
|---|---|---|---|---|---|
| wizard.magic | buyu | Default magic density | 50 | 0 | 100 |
| wizard.danger | karanlik | Default danger | 50 | 0 | 100 |
| wizard.peoples | halk | Default number of first peoples | 2 | 1 | 50 |
| wizard.peoples_max | halk_en_cok | Max first peoples | 5 | 1 | 50 |
| wizard.small_cosmos_extra | kucuk_kozmos | Small cosmos: worlds added at genesis | 1 | 0 | 20 |
| wizard.large_cosmos_extra | buyuk_kozmos | Large cosmos: worlds added at genesis | 2 | 0 | 20 |
| wizard.region_pull_pct | cekim | After genesis, region magic/danger are pulled this % toward the setting | 50 | 0 | 100 |

---

## 25. Notifications (`bildirim.js`)

### 25.1 Categories (`KATEGORILER`)

| Key | Label | Severity | Default on |
|---|---|---|---|
| isyan | Son's rebellion | 3 | ✔ |
| olum | Death | 3 | ✔ |
| dogum | Legendary birth | 3 | ✔ |
| kehanet | Prophecy fulfilled | 3 | ✔ |
| kiyamet | Omen of doomsday | 4 | ✔ |
| korku | Cosmic horror | 3 | ✔ |
| savas | War | 2 | ✔ |
| dua | Prayer to you | 2 | ✔ |
| kozmos | Cosmic event | 2 | ✔ |
| yukselis | Ascension | 2 | ✔ |
| afet | Disaster and sky | 2 | ✘ |
| cag | Epoch ended | 1 | ✔ |
| basarim | Achievement | 2 | ✔ |
| toplum | Society, lineage and debt | 2 | ✔ |
| itibar | In the sons' eyes | 2 | ✔ |
| hata | System error | 3 | ✔ |
| not | The god's note | 1 | ✔ |

### 25.2 Classification of chronicle rows (`kronikKategorisi(kind, text, sonId, ids)`)

1. `kader` and text starts with "Kehanet" (Prophecy) → `kehanet`.
2. `dogum` with a son and no entity ids → `dogum` (son summoned/born). A people awakening for a son also uses `dogum`, but it carries ids, so it is not a "legendary birth".
3. `dogum` and text matches /efsanevi|mitik|tanrısal/ (legendary|mythic|divine) → `dogum`.
4. `dunya` → map the live-feed category (§18): savas→savas, afet→afet, gok→afet, sizinti→korku, yolculuk→kozmos, kapi→kozmos, medeniyet→toplum; others (birth/death `hayat`, generic `dunya`) → none. Ordinary engine births and deaths are too frequent to notify.
5. Otherwise the kind table (01 §8): isyan→isyan; olum→olum; dirilis, yukselis→yukselis; kiyamet→kiyamet; korku, dis, olumsuzluk→korku; savas, tanri_savasi→savas; dua→dua; dunya_dogusu, yabanci_tanri, kozmik_hukuk, efsanevi_sefer, onceki_yaratilis, kozmik, yildiz→kozmos; afet, gok, iklim→afet; medeniyet, diplomasi, borc, soy→toplum; tanri_itibar→itibar; varolus→olum.

`kronikten(row)` (from chronicle; called by `addKronik`): category → `bildir` with title = text, body = text, target = `['v', ids[0]]` if ids, else `['o', sonId]` if a son, else none, plus the chronicle id and epoch.

### 25.3 `bildir({kategori, baslik, metin, hedef_tip, hedef_id, kronik_id, cag, onem, zorla})` (notify)

- Unknown category → null. Category disabled in `dunya.bildirim_ayar` (merged with defaults) and not `zorla` (forced) → null. The creator's own notes (`not`) are forced.
- raw = whitespace-collapsed `baslik || metin || category label`. For `hata` (error): title = `hataTurkce(raw)`, which translates English API/network errors into Turkish titles (**LANGUAGE-SPECIFIC**: in English, map error classes to friendly titles).
- If the title changed or is longer than 90 chars and there is no body → body = raw.
- Stored: epoch (given or current), category, severity (given or the category's), title cut to 89 + "…" if > 90, body (≤600) only if it differs from the title, target, chronicle id.
- Publish to the live bus: `{kind:'bildirim', id, …row, ad: category label}`. The UI toasts severity ≥ `BILDIRIM.toast_onem`.

### 25.4 Reading and settings

- `bildirimler({okunmamis, kategori, limit=60 (max 200), once})` (list; filters: unread, category, before id) → `{okunmamis: count, sayilar:[{kategori, n, okunmamis}], ayar, kategoriler, liste:[…, ad]}` (unread count, per-category counts, settings, categories, list), newest first. The server caps the limit with `SUNUCU.bildirim_tavan` and pages with `SUNUCU.bildirim_sayfa`.
- `okundu({ids | hepsi, kategori, okunmadi})` (mark read): set `okundu` 1 (or 0 if `okunmadi`, mark unread) for the ids, or for all (optionally in a category).
- `bildirimAyarla({cat: bool})` (settings): merge known categories and persist.
- `POST /api/bildirimler` with `{baslik, metin, hedef_tip, hedef_id}` → the creator's own note (forced `not`). An empty title is an error ("A note cannot be empty.").
- Epoch-end `bildirimBuda()` (prune): delete read rows with `id ≤ MAX(id) − BILDIRIM.okunmus_tut`. Then keep only the top `BILDIRIM.tavan` rows by (severity desc, id desc) and delete the rest (unread included).
- Ledger undo deletes notifications of removed chronicle rows (§27).

Rules `BILDIRIM` (group "Notifications"):

| Key (new) | Old | English | Default | Min | Max |
|---|---|---|---|---|---|
| notifications.read_keep | okunmus_tut | Read notifications kept | 1500 | 10 | 100000 |
| notifications.total_cap | tavan | Total notification cap | 5000 | 100 | 100000 |
| notifications.toast_min_severity | toast_onem | Notifications at or above this severity also show as a toast (5 = none) | 3 | 1 | 5 |

---

## 26. LLM metrics and epoch ETA (`olcum.js`)

- `olcumuBagla(epochFn)` (attach metrics) registers a hook in the LLM client. Each call inserts a row into `llm_olcum` (01 §2.30) with `deneme` (attempts) default 1, token counts and cost default 0. Every 50 writes → `olcumBuda()`.
- `olcumBuda(keep = OLCUM.sakla_cag)` (prune): delete rows with `cag ≤ MAX(cag) − keep`. Also runs at epoch end and at startup.
- `olcumOzeti({cag_sayisi=10})` (`/api/olcum`; summary) returns:
  - `toplam` (total): count, ms, cost, input and output tokens;
  - `caglar` (per epoch, last N): calls, ms, tokens, cost, errors, retried (`deneme>1`), slow (`ms > OLCUM.yavas_sn*1000`);
  - `modeller` (per model): calls, ms, avg ms, tokens, cost;
  - `adimlar` (per step, with names starting "Oğul turu:" / "Ölümlü turu:" (son turn / mortal turn) grouped): calls, avg ms, max ms, cost, errors, ordered by total ms;
  - `yavaslar`: the 12 slowest calls above the threshold;
  - `son_hatalar`: the last 8 errors;
  - `yavas_esik_ms` (slow threshold).
- `cagTahmini({basla, asama})` (epoch ETA; `/api/cag/tahmin`): read the last 400 `gunluk` events of kind `asama` (phase start: `{no, sure}` = phase number, seconds since epoch start) and `cag_bitti` (epoch done: `{cag, sure}`). Build per-epoch `{toplam, asama:{no: start sec}}` (a phase 1 event starts a new record). Take the last `OLCUM.ortalama_cag` completed epochs: the average total and the average start of each phase 1..5. If running (`basla` = start ms): elapsed = now − start. If the current phase is known and has an average start: `estimate = avgTotal − avgPhaseStart − max(0, elapsed − actualPhaseStart)`, else `avgTotal − elapsed`. `kalan_sn` = max(0, round(estimate)) (seconds left); `asildi` = estimate < 0 (overrun). Returns `{ornek, ort_cag_sn, asama_baslangic_ort_sn, calisiyor, gecen_sn, kalan_sn, asama, asildi}` (sample size, average epoch seconds, average phase starts, running, elapsed, left, phase, overrun).

Rules `OLCUM` (group "Records"):

| Key (new) | Old | English | Default | Min | Max |
|---|---|---|---|---|---|
| metrics.slow_seconds | yavas_sn | A model call over this many seconds counts as slow | 120 | 5 | 3600 |
| metrics.keep_epochs | sakla_cag | Epochs of model metrics kept | 100 | 1 | 10000 |
| metrics.eta_epochs | ortalama_cag | Remaining-time estimate: recent epochs averaged | 6 | 1 | 1000 |

---

## 27. The ledger "defter" (Fate's ledger: action log and selective undo)

### 27.1 Capture

- Every **world-changing tool call** by a son or mortal agent (the LLM tool wrapper in `llm.js`, excluding read-only tools `OKUMA_ARACLARI`) and every **creator action** (`epoch.defterli(action, fn)`, server `el(...)`) runs inside `defterdeKos(meta, fn)` (run in ledger).
- `defterdeKos`: insert `defter(cag, kim_tip, kim_id, kim_ad, arac, ozet)` (epoch, actor type, actor id, actor name, tool, summary). `ozet` (summary) = the first 80 chars of each of the input fields ad, tur, hedef_ad, metin, aciklama, neden, ilham (name, type, target name, text, description, reason, inspiration), joined with " · ", ≤220. Run `fn` inside an `AsyncLocalStorage` context `{grup, acik:true}` (group, open).
- The SQL function `defter_grup()` returns the group only while the context is open (background work spawned from a tool call inherits the context but cannot write after it closes).
- TEMP triggers on each whitelisted table (01 §1) insert `defter_satir(grup, tablo, rowid, islem, onceki, sonraki)` (group, table, row, op, before, after) with full-row JSON (`json_object`, split into `json_insert` chunks of 60 columns because of SQLite's argument limit).
- On close: if no rows were captured (a rejected or no-op action), delete the ledger entry. Otherwise `grubuSikistir` (compact group): for each `guncelle` (update) row keep only the changed keys plus the identifying keys (`id, ad, tur, metin, olusturma, kaynak_tip, kaynak_id, hedef_tip, hedef_id, a, b, halk_id, dil_id`).
- Creator actions (`defterli`) also wrap `fn` in `SAVEPOINT tanri_eli` (creator's hand): on error, roll back to it (so a refused action leaves no trace and refunds the spent essence), reset the canon cache, and rethrow.
- Ignored columns for diffs (`YOKSAY`): tur_cag, tur_ap, olusturma, zaman.

### 27.2 Reading (`defter({cag, kim_tip, kim_id, limit=80})`; `/api/defter`)

Returns `{cag: current, caglar:[{cag, n, geri}], kayitlar:[entry + sonuc parsed + degisiklik (visible row count) + satirlar (first 30 rows narrated) + bagimli]}` (epochs with entry and undone counts; entries with result, change count, rows, dependents). Visible rows = inserts, deletes, and updates with a real diff.

`satirAnlat(row)` (narrate a row):
- name: `ad`; for bonds "<src name> → <tgt name> (<bond label>)"; for chronicle the first 90 chars of the text; for community and son relations "A ↔ B"; else `#rowid`.
- insert: `"<table label>: <name>[ (<entity type label>)]"`. Table labels: varliklar "New entity", baglar "New bond", ogullar "Son", kronik "Chronicle", gercekler "Fact", iplikler "Thread", sozluk "Word", iliskiler "Relation", topluluk_iliski "Community relation", halk_inanc "Belief", rotalar "Route", dunyalar "World", yolculuklar "Journey", mesajlar "Message", dunya "Cosmos", yildizlar "Star", yabanci_tanrilar "Foreign god", caglar "Epoch narrative", caglar_dunya "World's epoch narrative", kronik_bakis "Historian's view", gorseller "Image", senaryolar "Scenario".
- delete: `"Deleted: <name>"`.
- update: `"<name> · <up to 4 field diffs>[ +k]"`. A field diff: arrays → `"+added, −removed"` (for `gecmis`, history: "N new entries"); objects → per-key `"<key>: a → b"`; scalars → `"<label>: a → b"`, where `aktif` shows yes/no, `dunya_id` shows the world name, `konum_id` shows the entity name, and values are truncated to 40 chars (`∅` for null, "yok" (none) for empty). Column labels: oz essence, un fame, xp experience, dunya_id world, statlar features, deger value, aktif active, gecmis history, varlik existence, konum_id location, nufus population, guc power, yayginlik spread, inanc faith, murit followers, …

`bagimlilar(grup)` (dependents): later, not-undone ledger entries that touched entities this entry inserted (updates to those entity rows, or bonds whose source or target is one of them) → `[{id, kim_ad, arac}]` (shown as a warning).

### 27.3 Undo (`geriAl(grup)`; `/api/defter/:id/geri-al`, refused while an epoch is running: "A page cannot be torn from the ledger while an epoch is running.")

Errors: "No such entry in the ledger." / "This entry was already undone."

Precompute:
- `eklenen` (inserted) = `table:row` keys inserted in this entry, except the permanent-birth tables `ogullar` and `dunyalar`.
- `dogan` (born) = son or world rows inserted in this entry that still exist. A born son or world is **never** removed, and **its birth cost is not refunded** (otherwise repeated undo would give free births): `DOGUM_BEDELI` = {ogullar: [oz], dunya: [tanri_oz]}.

For each row, **in reverse id order**, inside one transaction, each in its own `SAVEPOINT` (so one row's UNIQUE/FK failure does not abort the rest; failures become conflicts "<name> (<table>) could not be undone: <err>"):
- table not whitelisted → conflict "Unknown table skipped".
- **insert**: if the row is gone → skip. If the current row's identity columns (`olusturma, kaynak_tip, kaynak_id, hedef_tip, hedef_id, a, b, halk_id, dil_id`, compared where present on both sides) differ → conflict "… was later deleted and replaced by another record; left untouched". Then: entity → `durum='reddedildi'` (rejected); bond → `aktif=0`; son or world → conflict "not deleted (a born being cannot be undone); its birth cost is not refunded either"; anything else → `DELETE` (chronicle: also delete its notifications).
- **delete**: no before-image → skip. If a row exists with this rowid: if it has no diff from the before-image → skip (already restored); if the table has an `id` column → conflict "could not be rewritten: its number (#n) passed to another record"; else (composite-key table) insert without a rowid. `INSERT OR IGNORE` with the existing columns. If ignored → conflict "a new record with the same key is in its place".
- **update**: skip if this row was inserted in this entry (its own setup updates, e.g. the trigger's `dunya_id`) or is a born son/world. Row gone → conflict "… no longer exists". For each changed column `c` (diff excluding ignored columns) that still exists:
  - birth-cost columns with a decrease while something was born → conflict "<name> · <col> cost (<Δ>) not refunded: the born <son/world> is permanent";
  - current == after-value → restore the before-value;
  - else if `c` ∈ quantity columns `MIKTAR` (guc_seviyesi, can, oz, inanc, un, xp, seviye, uyku_kalan, yildiz, varlik, deger, sure, tehlike, sizinti, nufus, kalan, zaman_katsayi, tanri_oz, kiyamet, parlaklik, tutum, guc) and all three are numbers → `farkGeri(cur, before, after) = clamp(cur + (before − after), min(before, after, cur), max(before, after, cur))` (undo only this action's delta, never overshooting the observed range: "500 given, 480 spent" undoes to 0, not −480);
  - else if `c` ∈ {statlar, etiketler} → `birlestir` (merge): arrays: remove the elements this action added (those still present) and re-add the elements it removed (if absent); objects: per key, restore the before-value if the current value equals the after-value, apply the numeric delta merge if all three are numbers, else leave it. Unmergeable → conflict;
  - else → conflict "<name> · <col> changed later, left as is".
  - Write the restored columns; record "<name>: <cols> restored".
- Mark the entry `geri_alindi=1` (undone), `sonuc={yapilan, catisma}` (applied, conflicts).
- Chronicle line (`tanri` kind, no ids): "<creator>'s hand: a page was torn from Fate's ledger. <Actor>'s action (<action label from ARAC_EYLEM or tool name with spaces>) is considered never to have happened." (actor = "<name>'s", suffix-fixed, or "Someone's").

Return `{tamam, id, yapilan:[texts], catisma:[texts]}` (ok, id, applied, conflicts).

### 27.4 Retention

At epoch end `defterBuda(cag)` (prune ledger) deletes entries with `cag < now − DEFTER.sakla_cag`, and their rows. Then it deletes orphan rows whose group no longer exists.

Rules `DEFTER` (group "Records"):

| Key (new) | Old | English | Default | Min | Max |
|---|---|---|---|---|---|
| ledger.keep_epochs | sakla_cag | Epochs kept in the action ledger | 6 | 1 | 200 |

**Rewrite**: capture changes in the repository/unit-of-work (before/after snapshots per touched row) instead of TEMP triggers and AsyncLocalStorage. Keep the same undo semantics, which are well thought out: reject instead of delete for entities, deactivate bonds, delta-undo for quantities, merge for stats and tags, conflicts for text, permanent births.

---

## 28. Map and wiki helpers (`kesif.js`)

### 28.1 Political control (`siyasiHarita(vs?)`) — who dominates each region

Input: canon entities (`{id, ad, tur, konum_id, statlar, durum}`). Ruler map = active v-v `yonetir` (target → source, one per target).

For each canon people, settlement, faction or cult:
1. region = walk up `konum_id` (max 10 steps) to the first `bolge` (region); skip if there is none.
2. holder = the community itself. Walk the ruler chain from it up to `SIYASET.yonetim_zinciri` steps; whenever a link is a people, faction, settlement or cult, it becomes the holder. A settlement ruled by a mortal ruled by a people → the people.
3. share = faction: `(guc ?? hizip_varsayilan)*hizip_guc + (nufuz ?? hizip_varsayilan)*hizip_nufuz` (military power, influence); cult: `murit * tarikat_murit/100` (followers); people/settlement: `nufus` (population).
4. `power[region][holder] += share`.

Output per region: `{hakim_id, hakim_ad, tur, pay: round(top/total*100), cekisen: number of holders}` (dominant id, name, type, share %, contenders).

### 28.2 Road network (`yolAgi(positions, regionInfo, vs)`)

Stops = settlements and peoples that have a map position and are not rejected. Two stops are neighbours if their regions are the same or adjacent (`regionInfo[r].komsular`, from the map generator). Run Prim's algorithm **per connected island**, using only neighbour edges, weighted by Euclidean distance. Each tree edge → `{a, b, tur:'yol', uzunluk}` (road, length). An edge whose endpoints share an active v-v `ticaret` (trade) bond in either direction → `tur:'ticaret'` (trade road).

### 28.3 Epoch snapshots (time scrubbing)

- `cagFotografiAl(cag)` (take snapshot; called by the engine at epoch end): `{canli: ids canon/fulfilled, nufus: {id: round(population)} for canon peoples and settlements, siyasi: siyasiHarita(), savaslar: ids of war events tagged suruyor}` (alive, population, political map, ongoing wars) → upsert `harita_anlik`.
- `cagFotografi(cag)` (get snapshot) → parsed or null. `fotografCaglari()` (snapshot epochs) → list.

### 28.4 Map notes

- `haritaNotlari(worldId?)` (list notes): all, or `COALESCE(dunya_id,1) = worldId`.
- `haritaNotuEkle({x, y, metin, renk, dunya_id})` (add note): x and y must be finite ("Invalid position."); text trimmed to ≤400, non-empty ("A note needs a text."); world = the given one if it exists, else 1; colour ≤20 chars, default "altin" (gold); coordinates rounded.
- `haritaNotuSil(id)` (delete note): the server returns 404 "No such map note." if nothing was deleted.

### 28.5 "How are they connected?" (`yolBul(a, b, maxDepth=6)`; `/api/yol?a=v12&b=o3`) — pathfinding

Nodes are `v<id>` or `o<id>` (validated by `^[vo]\d+$`). Neighbours: every active bond touching the node, in both directions (`ileri` = forward when the node is the source), plus for entities the location (`icinde`, forward) and the creating son (`yaratti`, created, backward), plus for sons every entity they created (`yaratti`, forward). BFS up to `maxDepth` levels. Returns `{yol:[nodes], adlar:{node: name}, adimlar:[{a, b, tur, ileri, aciklama}]}` (path, names, steps), `{yol:[a], adimlar:[]}` when a = b, or `{yol:[], adimlar:[], yok:true}` (none).

### 28.6 Similar entities (`benzerler(id, n=6)`)

`mine` = the set of node keys this entity is bonded to (active, either direction). `region` = the entity's region (walk up). Candidates = entity neighbours ∪ up to 200 canon-ish entities (newest first) of the same type, same creator, or same location. For each canon-ish candidate: `score = 3*sharedNeighbours + 2*(same type) + 1.5*(same creator) + 1.5*(same region) + 1*(directly bonded)`. Keep score ≥ 2. Return the top `n` `{id, ad, tur, alt_tur, puan (1 decimal), neden}`, where the reason lists "<k> shared bonds", "same type", "same region", "same creator".

### 28.7 Merge (`birlestir(mainId, otherId)`; `/api/varliklar/:id/birlestir`, requires "BİRLEŞTİR" (MERGE), not while an epoch runs, recorded in the ledger)

Errors: "Pick two different entities." / "Only entities of the same type can be merged (<a> ≠ <b>)."

In one transaction:
1. Repoint B's bonds (source and target, v) to A, and delete self-loops on A.
2. B's contents' `konum_id` → A. B's lexicon → A. B's images → A (with `kapak=0`).
3. A.tags = A ∪ B (B's `dilden-ad…` tags dropped). `A.aciklama += "\n\n<B name> olarak da bilinir: <B desc>"` ("also known as <B>: …").
4. B: `durum='yok_edildi'` (destroyed), `kader_notu = "<A name> ile birleşti."` (merged with <A>).
5. Chronicle (`tanri` kind, ids [A, B]): "<creator>'s hand: <B> and <A> were in truth the same thing; their names merged."

Returns A. (Gap: B's chronicle mentions, facts and folk beliefs are not repointed. The rewrite should repoint these too.)

### 28.8 Favourites and personal notes

- `favoriDegistir(id, bool)` (toggle favourite). `kisiselNot(id, text)` (personal note): ≤4000 chars, empty → NULL. The server returns 404 if the entity is missing.
- `favoriler()` (favourites): favourite entities that are not destroyed, ordered by name.

### 28.9 Settlement tiers (`yerlesimKademeleri(vs, cag)`)

Tiers (`kademeler`): `koy` village ≥0, `kasaba` town ≥`SIYASET.kasaba`, `kent` city ≥`SIYASET.kent`, `buyuk_kent` great city ≥`SIYASET.buyuk_kent`. Invalid or non-numeric population counts as 0. The capital of each ruler = its most populous ruled canon settlement (via active `yonetir`). Output per canon settlement: `{kademe: 'baskent' (capital) | tier key, ad: label ('başkent' capital), nufus, onceki_nufus: population in the previous epoch's snapshot or null}` (tier, label, population, previous population).

### 28.10 Event markers (`olayIsaretleri(worldId=1)`)

Canon or dead entities of the world that are events, or are tagged/subtyped as ruin (`harabe`) or remnant (`kalıntı`). Kind: war/battle/siege subtype → `muharebe` (battle); tag `afet` → `afet` (disaster); tag `harabe` → `harabe` (ruin); `kalıntı` tag or subtype → `kalinti` (remnant); else `olay` (event). Only those with a location. Returns `{id, ad, tur, alt_tur, konum_id, cag}`. Corrupt tag JSON is tolerated.

Rules `SIYASET` (group "Civilization"):

| Key (new) | Old | English | Default | Min | Max |
|---|---|---|---|---|---|
| politics.faction_power_weight | hizip_guc | Region dominance: weight per faction military point | 200 | 0 | 1000000 |
| politics.faction_influence_weight | hizip_nufuz | Region dominance: weight per faction influence point | 50 | 0 | 1000000 |
| politics.faction_default | hizip_varsayilan | Faction with unknown power/influence | 30 | 0 | 100 |
| politics.cult_follower_pct | tarikat_murit | Region dominance: share of cult followers counted (%) | 30 | 0 | 1000 |
| politics.rule_chain_depth | yonetim_zinciri | Steps walked up the ruling chain | 4 | 0 | 50 |
| politics.town_population | kasaba | Settlement tier: town population | 2000 | 1 | 100000000 |
| politics.city_population | kent | Settlement tier: city population | 10000 | 1 | 100000000 |
| politics.great_city_population | buyuk_kent | Settlement tier: great city population | 50000 | 1 | 100000000 |

---

## 29. Reset and the "world changed" hook

- Reset: see 01 §12. Requires no running jobs (epoch, background jobs, bulk deepening, image generation: "First wait for running jobs to finish." / "Bulk deepening is running; stop it first …" / "Image generation is running; stop it first …").
- `dunyaDegisti(message)` (world changed; after restore, import, discovery start or end, reset):
  1. Invalidate the map cache. Clear the in-memory live log.
  2. Rebuild the suffix dictionary (LANGUAGE-SPECIFIC).
  3. `dengeUygula()` (the new world's rule overrides).
  4. `degisimSifirla()` (forces clients to do a full refresh).
  5. `onarimKos()` (run repair) in the background.
  6. Emit `{kind:'sistem', metin: message}` and `{kind:'serbest'}` (system message; free = not busy).
- **Rewrite**: also reset every in-memory cache (canon cache, motif cache, importance cache, Turkish-word cache, `SON_YIL`, the network-repair log). The old code relied on cache keys that included `COUNT(varliklar)` or `total_changes()`, which can collide after a restore.

---

## 30. Bulk deepening (`toplu.js`)

"Deepening" (derinleştirme) = an LLM job that writes an entity's `derinlik` lore (or a foreign god's). Bulk mode processes everything that has none.

- Queue (`sirasi`) = foreign gods with no depth (by id; few and important, so they go first), then entities with no depth ordered by `bekliyor` (pending ones last), importance desc, power desc, id.
- State `D` = `{calisiyor, durdur, toplam, bitti, hata, atlandi, suan:[{id, ad, yabanci?}], basla, bitis, gunluk:[]}` (running, stop requested, total, done, errors, skipped, now processing, start, end, log). Kept in memory; **not persisted**. After a restart a new run picks up only what is still undeepened.
- `baslat()` (start; `/api/toplu/derin/baslat`, refused in discovery mode): error if already running ("Bulk deepening is already running.") or if the queue is empty ("No undeepened records left."). Reset the counters and log "Bulk deepening started: <n> records, by importance." Start `calistir` in the background; on finish log "Stopped: <done> deepened, <errors> errors[, <skipped> skipped]." or "Done: <done> deepened, <errors> errors, <skipped> skipped." Unexpected crash: "The bulk job stopped unexpectedly: <msg>".
- `durdur()` (stop): error if not running ("No bulk deepening is running."). Sets the flag and logs "Stop requested; it will stop once the records in progress finish."
- `calistir(queue)` (run):
  1. If there are pending (unnamed) engine records, log "<n> unnamed records are also being named." and start `epoch.adlandirmaIsi()` (naming job) concurrently.
  2. `tur(queue)` (round): `TOPLU.eszamanli` concurrent workers; each pops items until the queue is empty or a stop is requested, waiting `TOPLU.bekle_sn` between items.
  3. If naming ran and no stop was requested: await it. Then queue newly undeepened entities that were not in the original queue (`toplam += k`) and run another round.
- `tekKayit(item)` (one record): reload it. Skip (`atlandi++`) if it is missing, already has depth, or (for entities) is not canon-ish. Add it to `suan` and log "Deepening: <name>". Loop:
  - call `epoch.yabanciDerinlik(id, {sira:false})` or `epoch.derinlestir(id, {sira:false})` (`sira:false`: do not take the global job queue);
  - on an error matching "at most N jobs" / "already being processed" / "Genesis" (pool full or busy): wait `TOPLU.havuz_bekle_sn` (unless stopping). If stopping → skip with "<name>: stopped while waiting in the queue; not processed." Else retry **without** counting an attempt;
  - on another error: if attempts ≥ `TOPLU.yeniden_dene` or stopping → fail (`hata++`, "<name> could not be deepened: <msg>"). Else log a warning "<name>: <msg>; retrying (<k>/<max>)." and wait `TOPLU.yeniden_bekle_sn`;
  - success → `bitti++`, "<name> deepened (<s> s)".
- Every log line (≤ `TOPLU.gunluk_satir` kept) is also published as `{kind:'toplu_derin', ...summary, satir}`.
- `ozet()` (summary) = the state without the log, plus `kalan = toplam − bitti − hata − atlandi` (remaining). `durum()` (status; `/api/toplu/derin`) = summary + the last log lines + `bekleyen` (queue length now) + `adsiz` (unnamed engine records).

Rules `TOPLU` (group "Bulk jobs"):

| Key (new) | Old | English | Default | Min | Max |
|---|---|---|---|---|---|
| bulk.concurrency | eszamanli | Records deepened at the same time | 1 | 1 | 4 |
| bulk.gap_seconds | bekle_sn | Wait between two records (s) | 0 | 0 | 600 |
| bulk.retries | yeniden_dene | Retries for a failed record | 2 | 0 | 5 |
| bulk.pool_wait_seconds | havuz_bekle_sn | Re-check interval when the job pool is full (s) | 5 | 1 | 600 |
| bulk.retry_wait_seconds | yeniden_bekle_sn | Wait before retrying a failed record (s) | 3 | 0 | 600 |
| bulk.log_lines | gunluk_satir | Lines kept in the bulk-job log | 200 | 20 | 5000 |

---

## 31. Remaining rule tables

### 31.1 `BAGLAM` — prompt context budgets (`world.js`; group "Context budgets" unless noted)

| Key (new) | Old | English | Default | Min | Max |
|---|---|---|---|---|---|
| canon_cache.batch | kanon_parti | Engine cache: changed entities re-read in batches of this size | 500 | 1 | 100000 |
| ctx.son_geography | ogul_cografya | Son: geography and inhabitants (chars) | 5000 | 500 | 100000 |
| ctx.son_map | ogul_harita | Son: map (chars) | 2500 | 200 | 50000 |
| ctx.son_cosmos | ogul_kozmos | Son: other worlds (chars) | 1500 | 200 | 30000 |
| ctx.son_languages | ogul_dil | Son: languages and lexicon (chars) | 1600 | 200 | 30000 |
| ctx.son_locationless | ogul_konumsuz | Son: legends and traditions (chars) | 1500 | 200 | 30000 |
| ctx.son_chronicle | ogul_kronik | Son: recent events (chars) | 2200 | 200 | 30000 |
| ctx.son_summary | ogul_ozet | Son: whole world summary (chars) | 14000 | 2000 | 200000 |
| ctx.son_memory | ogul_hafiza | Son: memory (chars) | 5000 | 500 | 100000 |
| ctx.son_prompt | ogul_istem | Son: whole turn prompt (chars) | 24000 | 4000 | 400000 |
| ctx.son_chronicle_lines | ogul_kronik_satir | Son: lines of recent events (+ wisdom/8) | 10 | 1 | 200 |
| ctx.tool_multiplier | arac_kat | Read tools: how many times longer recent events and memories are when a section cut from the prompt is shown in full | 3 | 1 | 50 |
| ctx.short_cosmology | kisa_kozmoloji | Cosmology length in mortals' short world header (chars) | 500 | 50 | 100000 |
| ctx.section_floor | bolum_taban | Minimum space for each context section (chars; whole section if shorter) | 600 | 0 | 100000 |
| ctx.clip_min | butce_kirp_en_az | Min space for a line that does not fit to enter clipped (chars) | 120 | 0 | 10000 |
| ctx.memory_worshippers | hafiza_tapan | Son memory: worshippers shown by name (rest as a count) | 12 | 0 | 1000 |
| ctx.son_threads | ogul_iplik | Son: open stories shown | 6 | 1 | 100 |
| ctx.fate_geography | kader_cografya | Fate: geography (chars) | 9000 | 500 | 200000 |
| ctx.fate_map | kader_harita | Fate: map (chars) | 4000 | 200 | 100000 |
| ctx.fate_cosmos | kader_kozmos | Fate: other worlds (chars) | 2500 | 200 | 50000 |
| ctx.fate_languages | kader_dil | Fate: languages (chars) | 3000 | 200 | 50000 |
| ctx.fate_locationless | kader_konumsuz | Fate: legends and traditions (chars) | 3000 | 200 | 50000 |
| ctx.fate_chronicle | kader_kronik | Fate: recent events (chars) | 4000 | 200 | 50000 |
| ctx.fate_summary | kader_ozet | Fate: whole world summary (chars) | 26000 | 2000 | 400000 |
| ctx.fate_chronicle_lines | kader_kronik_satir | Fate: lines of recent events | 24 | 1 | 400 |
| ctx.mortal_context | olumlu_baglam | Mortal: whole context (chars) | 12000 | 2000 | 200000 |
| ctx.memory_creations | hafiza_yaratim | Son memory: creations (chars) | 1600 | 200 | 50000 |
| ctx.memory_memories | hafiza_ani | Son memory: memories (chars) | 1200 | 200 | 50000 |
| ctx.memory_about | hafiza_hakkinda | Son memory: things about him (chars) | 900 | 100 | 50000 |
| ctx.memory_beliefs | hafiza_inanc | Son memory: folk beliefs (chars) | 900 | 100 | 50000 |
| ctx.memory_words | hafiza_soz | Son memory: incoming words (chars) | 1000 | 100 | 50000 |
| ctx.repeat_threshold | tekrar_esik | "You are repeating yourself" warning: creations of the same subtype (group "Son tools") | 3 | 2 | 50 |
| ctx.repeat_window | tekrar_pencere | Repetition check: recent creations examined (group "Son tools") | 20 | 1 | 500 |
| ctx.son_tree_lines | ogul_agac | Son: location-tree lines (+ wisdom) | 90 | 10 | 5000 |
| ctx.fate_tree_lines | kader_agac | Fate: location-tree lines | 220 | 10 | 10000 |
| ctx.son_chronicle_wisdom_step | ogul_kronik_bilgelik | Son: every this-much wisdom adds one recent-event line | 8 | 1 | 100 |
| ctx.son_language_samples | ogul_dil_ornek | Son: sample words per language | 6 | 0 | 200 |
| ctx.fate_language_samples | kader_dil_ornek | Fate: sample words per language | 10 | 0 | 200 |
| ctx.near_language_extra | dil_yakin_ek | Extra sample words in the son's near languages | 4 | 0 | 100 |
| ctx.far_language_fewer | dil_uzak_eksik | Fewer sample words in far languages | 3 | 0 | 100 |
| ctx.far_language_min | dil_uzak_en_az | Min sample words in far languages | 3 | 0 | 100 |
| ctx.locationless_rows | konumsuz_satir | Legends and traditions: newest records shown | 45 | 1 | 1000 |
| ctx.inspect_lexicon | incele_sozluk | Entity inspection: words shown from the language's lexicon | 40 | 0 | 2000 |
| ctx.inspect_facts | incele_gercek | Entity inspection: canon facts shown | 8 | 0 | 200 |
| ctx.fact_rows | gercek_sayi | Canon facts: default rows | 12 | 1 | 500 |
| ctx.chronicle_rows | kronik_sayi | Recent events: default rows | 12 | 1 | 500 |
| ctx.search_results | arama_sonuc | varlik_ara (entity search): max results | 25 | 1 | 500 |
| ctx.lexicon_rows | sozluk_sayi | Default words read from a lexicon | 400 | 1 | 100000 |
| ctx.memory_creation_count | hafiza_yaratim_sayi | Son memory: recent creations | 30 | 1 | 500 |
| ctx.memory_memory_count | hafiza_ani_sayi | Son memory: recent memories | 12 | 1 | 500 |
| ctx.memory_about_count | hafiza_hakkinda_sayi | Son memory: recent events about him | 10 | 1 | 500 |
| ctx.memory_word_count | hafiza_soz_sayi | Son memory: recent incoming words | 10 | 1 | 500 |
| ctx.thread_related_score | iplik_ilgili | Story priority: points per related record of the son | 3 | 0 | 100 |
| ctx.thread_name_score | iplik_ad | Story priority: points if the son's name is in the text | 4 | 0 | 100 |
| ctx.thread_stale_penalty | iplik_durgun | Story priority: points lost per stagnant epoch (in hundredths) | 50 | 0 | 1000 |
| ctx.thread_advanced_score | iplik_ilerlemis | Story priority: points if it was ever advanced | 1 | 0 | 100 |
| ctx.doom_visible_pct | kiyamet_uyari | Doomsday clock is visible in prompts at this % of the threshold (group "Doomsday") | 30 | 0 | 100 |

`entity search` (`varlikAra(query, type?, limit = ctx.search_results)`): non-rejected entities (optionally of a type), newest first; match the normalized query against the normalized name, subtype or description (substring); stop at the limit.

### 31.2 `DUNYA_FIZIK` — world physics (`world.js`; read by the cosmos module's world physics, world birth and the creator's world editing; group "Cosmos and travel")

| Key (new) | Old | English | Default | Min | Max |
|---|---|---|---|---|---|
| world_physics.time_min_pct | zaman_en_az | Min time factor Fate gives a world it births (%; 100 = normal; does not limit the creator's manual value) | 25 | 1 | 10000 |
| world_physics.time_max_pct | zaman_en_cok | Max time factor Fate gives a world it births (%) | 400 | 1 | 10000 |
| world_physics.capacity_none | kapasite_yok | Life capacity with no atmosphere (%) | 25 | 0 | 1000 |
| world_physics.capacity_thin | kapasite_ince | Thin atmosphere (%) | 60 | 0 | 1000 |
| world_physics.capacity_normal | kapasite_olagan | Normal atmosphere (%) | 100 | 0 | 1000 |
| world_physics.capacity_dense | kapasite_yogun | Dense atmosphere (%) | 115 | 0 | 1000 |
| world_physics.capacity_toxic | kapasite_zehirli | Toxic atmosphere (%) | 40 | 0 | 1000 |
| world_physics.war_low_gravity | savas_dusuk | Martiality modifier at low gravity | −4 | −100 | 100 |
| world_physics.war_normal_gravity | savas_olagan | Martiality modifier at normal gravity | 0 | −100 | 100 |
| world_physics.war_high_gravity | savas_yuksek | Martiality modifier at high gravity | 6 | −100 | 100 |

### 31.3 Rule references this core reads but that are defined elsewhere

`ZAMAN.cag_yil` (50, epoch years; rules); `KURAL.varlik_solgun` (12), `KURAL.can_taban` (50), `KURAL.can_dayaniklilik` (150), `KURAL.oz_taban` (40), `KURAL.oz_kudret` (160), `KURAL.oz_kudret_varsayilan` (20), `KURAL.iliski_*`, `KURAL.sinif_*` (rules); `DENGE.kiyamet_esik` (rules); `CAG_AKIS.yil_*` (epoch); `YARATICI.ruh_*` (creator mood defaults; creator module); `KORKU.bulaniklik_esik` (horror module); `OGUL_ARAC.yildiz_indirim` (son tools); `DERIN_YASAM.yasam_bereket` (engine); `DERIN.savassiz_ateskes`, `DERIN.ateskes_cag` (engine); `ILISKI.iliski_gecmis` (engine); `OLUMLU.uret_usta`, `OLUMLU.uret_saglam` (mortal agents); `SUNUCU.*` (server: `tamamla_gecikme`, `bildirim_tavan`, `bildirim_sayfa`, `defter_tavan`, `defter_sayfa`, `olcum_cag`, `olcum_cag_tavan`, `galeri_eksik_tavan`, `hile_oz_tavan`, `sozluk_kelime`, `konsey_liste`, `saglik_hata_liste`, `gunluk_api`).

---

## 32. Known bugs and design smells (and how the rewrite should avoid them)

1. **HTTP writes join the engine's open transaction** (`txNefesli` + a single connection). A failing engine step rolls back user actions made meanwhile, and user writes can see half-applied engine state. → A single writer queue; the engine commits in chunks; user actions are queued or run between chunks.
2. **Restore/import = DELETE + INSERT into the live DB** with FKs off. A crash mid-way leaves a mixed world (only the discovery state file was made crash-safe). → Validate into a temp file and atomically replace the DB file (close the pool first), or use a per-world DB file and a pointer.
3. **Discovery mode swaps the live DB contents** and relies on a state file plus an own-world copy. A corrupt state file locks the app read-only. → Open the guest DB read-only side by side.
4. **Caches keyed by weak signals**: motif cache by `COUNT(varliklar)`, importance cache by `total_changes()` (connection-local, resets on reconnect), the Turkish-word cache by epoch, and the year map `SON_YIL` survives restores. → Explicit invalidation on "world changed" and versioned caches.
5. **Text-based state**: bond descriptions carry state (debts, truces, closure); tags carry links; chronicle text is regex-parsed to infer deaths, killers, temple destruction and holy-world assignments (`tanriOlumleri`, `otoKoruyucular`, `olayMerkezleri`, `kesifNedenOnar`). → Typed columns and event records; derive narrative from data, never data from narrative.
6. **Repairs run synchronously at startup** and grow with world size (multiple full-table scans, regex over all chronicle rows). → A background fix-up runner with "applied" markers; self-healing checks made incremental.
7. **ID leaks into lore**: prompts contain `#123`, `oğul#3`, `iplik#5`, so models copy them, which is why §12 has a large set of cleaners. → Use opaque handles only inside tool arguments, keep narrative prompts id-free, and validate output.
8. **Name uniqueness by scanning five tables** per check; the similarity check is O(N) Levenshtein. → The `name_registry` table and a prefix index.
9. **`addBag` side effects are implicit** (enemy cancels alliance and trade; a mortal ruler dethrones others) and depend on the call path. → An explicit `BondService` with documented invariants and unit tests.
10. **Two notions of "closed" bond** (`aktif=0` vs hidden). Several queries forget one of them (e.g. `bagVarAra` checks only active bonds, while `tekBag` checks visible ones). → A single `state` enum and helper predicates.
11. **Merge (`birlestir`) leaves the merged entity's chronicle links, facts and beliefs pointing to B.** → Repoint every FK.
12. **Ledger capture via TEMP triggers + AsyncLocalStorage SQL function**: fragile, single-connection only, and background writes inherit the context. → Unit-of-work diffs.
13. **`dunya.kiyamet` comment says JSON** but it is an integer. `kaynak` and son `durum` enums are undocumented in the schema. → CHECK constraints.
14. **Language-specific logic everywhere** (suffix fixing `ekDuzelt`, possessives, dotless-i normalization, Turkish stemming for motifs and chronicle dedupe, Turkish regexes in the live-feed categories and in `istemMetni`). → Drop it, or replace it with English equivalents (casefold, Snowball stemmer, English templates).
15. **Rule max is soft** (only the min is enforced), so the UI must warn. Keep this behaviour, but document it.
16. **`bosDunyalar` treats a missing fertility as 50** and the threshold comes from another module's rule (`DERIN_YASAM.yasam_bereket`), which may be undefined at load (it falls back to `?? 0`). → Explicit defaults.
17. **The chronicle-year algorithm depends on in-memory state** (`YIL_ARALIK`, `YIL_CAG`, `SON_YIL`), which is lost on restart mid-epoch. Years after a restart can jump backwards, which `cagBasiYillari` later repairs. → Persist "last year used per epoch", or derive years from (phase, sequence) deterministically.
18. **Import accepts any schema version ≤1**, and columns are copied by name intersection. Renamed columns silently lose data. → Versioned export with an explicit migration step on import.

---

## 33. Open questions for the integrator

1. Keep **name uniqueness across all node kinds** (entities, sons, stars, worlds, foreign gods) in an English-only game? (Recommended: yes; it keeps prompts unambiguous.)
2. Keep the **per-world phonology** (naming rule as prose)? The rewrite could store a structured phonology (allowed vowels and consonants, banned sounds) and keep the prose for prompts. The `lehceIhlali` check depends on it.
3. Drop the **tired-motif detector**, or port it with an English stemmer? It is used in every writing prompt and is valuable for quality.
4. **Discovery mode**: keep it as "open someone else's world read-only"? The new design (side-by-side read-only DB) is simpler.
5. **Undo ledger scope**: the old system captures every tool call by sons and mortals, plus creator actions, for 6 epochs. Is this needed in v1 of the rewrite? It is a large subsystem.
6. **Startup LLM "completion" job** (`tamamla`): it fills missing data automatically after boot. Make it opt-in?
7. **Telemetry DB split**: is a separate SQLite file for LLM metrics and the live log acceptable?
