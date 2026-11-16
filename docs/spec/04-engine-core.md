# 04 — Engine core: world tick, mortals, interventions, map, language

Status: specification of the OLD legacy implementation (`/Users/egedogan_dursun/aerona`), written for the rewrite. English names are used throughout; the Turkish original is given in parentheses the first time (e.g. "epoch (çağ)") so every rule can be traced back to the old code.

Source files covered:

| Old file | What it does | Section |
|---|---|---|
| `src/sim.js` | The LLM-free world engine: the per-epoch tick `dunyaMotoru` and everything it orchestrates in order; mortal aging/death/succession; hero-vs-monster; chronicle folding; carrying capacity; the epoch transition `cagGecisi` (growth, sons' renewal, apocalypse clock, creator essence) | §1, §2 |
| `src/derin.js` (excerpts only) | Peoples/settlements/notables/rulers spawning, first language & faith, ruin refounding — summarized in §1 because the tick depends on them; full spec belongs to the derin.js part | §1 |
| `src/olumluler.js` | Mortal agents: who acts each epoch, region helpers, the mortal tool set (LLM-driven actions of peoples, factions, cults, settlements, heroes, intelligent creatures), their prompts | §3 |
| `src/harita.js`, `public/harita-gen.js` | Map generation (Voronoi), regions, adjacency, elevation/coast classes | §4 |
| `src/dilmotoru.js`, `public/dil.js` | Procedural language & naming; Turkish grammar helpers (to be dropped) | §5 |
| `src/mudahale.js` | Laws resolver, knowledge/teaching, disasters, event records, miracles | §6 |

Order of the document:

1. World engine tick (sim.js) — pipeline, mortal lifecycle, heroism, chronicle, capacity, epoch transition, spawning, bugs
2. Tunables of the world engine (sim.js)
3. Mortal agents (olumluler.js)
4. Map generation
5. Procedural language and naming
6. Interventions, knowledge, disasters, miracles
7. Open questions for the integrator

Global conventions used in every section:

- Percent tunables are stored as integers (30 = 30% = probability 0.30).
- `d(n)` = uniform integer in 1..n. `clamp(v, lo, hi)` ROUNDS to an integer (old `rules.js` behaviour); `sinirla` clamps without rounding.
- Entity = row of `varliklar` (fields: id, tur/kind, alt_tur/subtype, ad/name, durum/status, konum_id/location, dunya_id/world, guc_seviyesi/power level, statlar/stats JSON, etiketler/tags JSON, cag/epoch created, kaynak/source, bekliyor/pending flag, unvan/title, yaratan_id/creator son, kader_notu/fate note, olum_cag/death epoch). Bond = row of `baglar` (kaynak_tip, kaynak_id, hedef_tip, hedef_id, tur/kind, aciklama/description, cag, aktif). Type codes: `'v'` entity, `'o'` son (god), `'y'` creator.
- Tunables are referenced as `AREA.original_key` (e.g. `DUNYA_MOTORU.kin_sans`); each table lists the English snake_case key coined for the rewrite next to the original key.
- "LANGUAGE-SPECIFIC: drop or replace" marks Turkish-grammar logic that the English-only rewrite does not port.

## 1. World engine tick (sim.js)

The world engine ("dünya motoru") is the LLM-free, rule-and-dice simulation that runs once per epoch (çağ) after the sons (god agents) have acted and before Fate (Kader) narrates. It never calls a model. Entities/events it creates are flagged as "pending" (`bekliyor`) so that Fate can later name them and fold them into the narrative; the notes (`not`) it emits are the raw material Fate reads.

Source: `src/sim.js` (1614 lines). It orchestrates dozens of sub-engines that live in other modules (mostly `src/derin.js`, plus `kozmos.js`, `seyahat.js`, `ufuk.js`, `olum.js`, `ekonomi.js`, `yaratici.js`, `tanriguc.js`, `itibar.js`, `hedef.js`, `gercek.js`, `korku.js`, `yaratik.js`, `panteon.js`, `medeniyet.js`, `kronik-onar.js`, `gok.js`, `otesi.js`, `kesif.js`). Those sub-engines are specified in their own spec files; here we specify the exact ORDER in which they are called, every rule implemented inline in `sim.js`, and the contracts between them.

All tunables referenced below as `AREA.key` (e.g. `DUNYA_MOTORU.kin_sans`) are listed in the section "Tunables of the world engine (sim.js)" with English keys. Local aliases used in the code: `KY`=`KIYAMET`, `OZ`=`OZ`, `DM`=`DUNYA_MOTORU`, `SG`=`DUNYA_SAVAS_GUCU`, `DE`=`DUNYA_ETKI`, `KH`=`DUNYA_AV`, `CG`=`DUNYA_CAG_GECISI`. `SINIR.*` (global limits) and `DENGE.*`/`KURAL.*` live in `rules.js` (spec'd elsewhere).

### Conventions and primitives

- **Entity (varlik)**: row of table `varliklar` with `id, tur (kind), ad (name), durum (status: 'kanon' = canonical/alive in the world, 'bekliyor' = pending Fate's naming, others e.g. 'olu', 'yok'), konum_id (location parent entity id), dunya_id (world/planet id, default 1), guc_seviyesi (power level 1..12), statlar (JSON stats), etiketler (JSON tag list), son_eylem_cag, ...`. Kinds referenced here: `bolge` (region), `yerlesim` (settlement), `halk` (people), `hizip` (faction), `tarikat` (cult/sect), `olumlu` (individual mortal), `tur` (creature species), `esya` (item), `kaynak` (resource), `dil` (language), `kanun` (law), `gelenek` (tradition), `efsane` (legend), `ruh` (spirit), `yapit` (structure), `para` (currency), etc.
- **Bond (bag)**: row of table `baglar`: `kaynak_tip ('v' entity | 'o' son | 'y' creator...), kaynak_id, hedef_tip, hedef_id, tur (bond kind), aciklama (description), cag (epoch created), aktif (1/0)`. Bond kinds used here: `konusur` (speaks language), `tapar` (worships), `sahip` (owns), `korur` (protects), `avlar` (hunts / raids), `oldurdu` (killed), `ticaret` (trade), `dusman` (enemy), `muttefik` (ally), `lanetledi` (cursed), `yonetir` (rules), `es` (spouse), `sevgili` (lover), `rakip` (rival), `cocugu` (child of), `anlatir` (depicts), `musallat` (haunts) and more.
- `addBag(srcType, srcId, dstType, dstId, kind, description, epoch)`, `bagVar(a, b, kind)` (does an active bond exist in either direction), `saveStat(entity)` (persist `statlar`), `addKronik(...)` (chronicle row), `hami(entity)` (patron son of an entity = the son it worships), `iliski(sonA, sonB)` (son-son relation −100..100), `iliskiDegistir`, `nameOf(type,id)`: all from `world.js`.
- `kanonlar()`: all canonical entities (cached during the tick, see `kanonOnbellek` in derin.js).
- `clamp(v, lo, hi)` = `max(lo, min(hi, round(Number(v)||0)))` — **note: clamp always rounds to integer**.
- `d(n)` = uniform integer 1..n (`1 + floor(random()*n)`). `sans(p)` = `random() < p`. Percent tunables are divided by 100 before `sans`.
- `karistir(arr)` = Fisher–Yates shuffle using `Math.random` (the code comments say `Math.random` is seeded so the engine is deterministic; SQL `RANDOM()` is avoided for that reason).
- `sinirla(v, lo, hi)` = clamp without rounding.
- `adKoku(name, suffixRegex)`: strips repeated derived-name suffixes (and trailing roman numeral or number), up to 20 times, so that "X's Heir's Heir II" → "X". Used so names don't grow across generations.
- `buyuklukEsigi(list, stat, pct, lo, hi)` (derin.js): returns a per-world threshold function. For each world, sort the stat values ascending, take the value at index `min(n-1, floor(n*pct))`, threshold = `min(hi, max(lo, value))`; worlds with no entries get `hi`. Used for "the top X% of the world" relative thresholds.

#### Map distance helpers (sim.js-local)

- `atalar(v)`: list of ancestor ids following `konum_id` upward, at most 8.
- `mesafe(a, b)` ("distance in steps"): `A = [a.id, ...atalar(a)]`, `B = [b.id, ...atalar(b)]`; for i over A, if `A[i]` found at index j in B return `i + j`; if no common ancestor return 99. (So two settlements in the same region are distance 2; a settlement and its own region 1.) **This is a containment-tree distance, not the map-adjacency distance** (`yakinMi` / `komsular` from the Voronoi map is used elsewhere).

#### Military strength (used by wars/campaigns in derin.js `seferler`)

Passed to `seferler` as the helper bag `H = { askeriGuc, muttefikGucu, hamiBonus, silahGucu, olumSonrasi, kahramanlik }`.

- `hamiBonus(v)`: `h = hami(v)`; if none → `{h:null, b:0}`; else `b = round(h.statlar.guc / SG.hami_guc_bolen × (h has power 'savas_babasi' (war father) ? SG.savas_babasi_carpan : 1))`.
- `techizat(v)` (equipment): all active `sahip` bonds from v to canonical entities of kind `esya`.
- `silahGucu(v, k=1)` = `round(Σ_items (hasar/SG.silah_hasar_bolen + koruma/SG.silah_koruma_bolen + kudret/SG.silah_kudret_bolen) × k)` (hasar = damage, koruma = protection, kudret = potency).
- `askeriGuc(v)` (military strength):
  - `savasci` (warrior-class bonus) for kinds `halk`, `yerlesim`: `(toplumOf(v).k.savasci − SG.savasci_esik) × SG.savasci_katsayi/100` where `toplumOf(v).k.savasci` is the warrior class share % from the society model (derin.js); 0 for other kinds. (Can be negative.)
  - `V = SG.varsayilan_stat`.
  - base by kind:
    - `tarikat`: `(bagnazlik ?? SG.varsayilan_bagnazlik) × SG.tarikat_bagnazlik/100 + log10(max(10, murit||10)) × SG.tarikat_murit_log` (bagnazlik = zealotry, murit = followers)
    - `hizip`: `(guc ?? V) + (nufuz ?? V) × SG.hizip_nufuz/100` (nufuz = influence)
    - `halk`: `(savascilik ?? V) + savasci` (savascilik = martiality)
    - `yerlesim`: `(savunma ?? V) × SG.yerlesim_savunma/100 + savasci` (savunma = defense/walls)
    - `olumlu`: `(guc ?? V) + (ceviklik ?? V)/SG.olumlu_ceviklik_bolen`
    - `tur`: `(tehlike ?? V) + (guc ?? 0)/SG.tur_guc_bolen`
    - other: `guc ?? savascilik ?? savunma ?? V`
  - total = base + `silahGucu(v)` + (knows 'savas' (warfare) ? `SG.savas_bilgisi`) + (knows 'yasak' (forbidden knowledge) ? `SG.yasak_bilgi`) + `basamakOf(v) × SG.basamak_guc` (civilization tier, medeniyet.js) + `evcilGucu(v)` (tamed creatures, yaratik.js) + (kind `tur` ? `ozellikSavas(v)` (creature trait combat bonus)) + (kinds halk/yerlesim/hizip ? `dunyaFizigi(v.dunya_id).savas` (world physics war modifier, kozmos.js)).
- `muttefikGucu(v)` = Σ over canonical entities linked to v by an active `muttefik` (ally) bond in either direction of `askeriGuc(ally) × SG.muttefik_pay/100`.

#### Prosperity gain with diminishing returns (`refahKazanci`, `refahEkle`)

Every positive prosperity (refah) gain anywhere in the game (trade, resources, monopoly, market, sales, wonders, golden age, common currency, travel, foreign gods, planet, miracles, ransom, society economy) goes through this; losses apply directly.

```
refahKazanci(refah, gain):
  if gain <= 0 or refah <= DE.refah_hedef: return gain
  return gain * max(0, 100 - refah) / max(1, 100 - DE.refah_hedef)
refahEkle(stats, gain):            # no-op (returns null) if stats.refah is null
  stats.refah = clamp(round(stats.refah + refahKazanci(stats.refah, gain)), 0, 100)
```
(Full gain at/below the equilibrium `refah_hedef`=50, zero at 100.)

#### Overflowing essence distribution (`tasanOzuDagit(tasan)`)

Essence (öz) above the son's cap leaks into the world as fertility (bereket):
```
regions = canonical 'bolge' with bereket != null and bereket < OZ.tasma_bereket_ust
budget  = max(1, round(tasan / OZ.tasma_bereket))
given = 0
while given < budget and regions not empty:
   b = region with minimum bereket (first minimum in list order)
   b.bereket += 1 ; mark changed
   if b.bereket >= OZ.tasma_bereket_ust: remove b from regions
   given += 1
save all changed regions; return {budget, given}
```
Leftover budget is lost.

### Entry points and transaction model

- `dunyaMotoru(cag, canli = noop, isaretle = null)`: synchronous. Enables the canonical-entity cache (`kanonOnbellek(true)`), runs the generator `motorAdimlari(cag, canli, isaretle)` to completion inside ONE DB transaction (`tx(() => sonunaKadar(gen))`), disables the cache in `finally`. Used by tests and legacy callers.
- `dunyaMotoruNefesli(cag, canli, isaretle)` ("breathing"): async; same generator executed by `txNefesli(gen, 'dünya motoru')`, which keeps one transaction open but yields to the Node event loop at every `yield` so the HTTP server stays responsive while the engine runs (UI doesn't freeze). Same cache on/off.
- `canli(message)`: live callback; every note is pushed to it (used for live streaming of engine notes to the UI).
- `isaretle()`: called as the LAST step inside the transaction (e.g. epoch.js's "engine finished" marker) so that the marker commits atomically with the engine's writes; if the process crashes between, the engine won't run twice for the same epoch.
- `motorAdimlari` is a generator; each `yield '<phaseName>'` is a breathing point (and names the phase that just finished).
- Return value: see end of pipeline (the list of notes `notlar`, plus extras).

New design: model this as an async pipeline of named phases inside one DB transaction (or one unit-of-work), with cooperative yielding between phases; keep the "engine done" marker in the same transaction.

### Note collection and chronicle folding

```
notlar  = []                 # raw notes returned to the caller (Fate reads these)
bekleyen = []                # pending chronicle lines, written at the end of the tick
bas = sonKronikId()          # id of the last chronicle row before the tick (kronik-onar.js)
not(text, ids = [], son = null):
    m = ekDuzelt(text)       # LANGUAGE-SPECIFIC: Turkish suffix-harmony fix ("X'e" etc.); drop
    notlar.push(m)
    bekleyen.push({ metin: text, ids, ogul: son, iz: sonKronikId() })   # iz = last chronicle id when the note was written
    canli(m)
```
`ids` = entity ids the line links to; `ogul` = son id if the line concerns a son. `iz` is used by `motorTekrarlari` (kronik-onar.js) to detect that a sub-engine already wrote the same event with its own chronicle kind right next to the note, so the note is a duplicate. At the end of the tick, `kronikYaz` folds lines (see "Chronicle writing").

### Tick pipeline (`motorAdimlari(cag, canli, isaretle)`) — exact order

`Y = yasaCozucu()` (mudahale.js) is computed first: a per-world active-law resolver; `Y.has(lawKey, entity)` checks the law in the entity's own world.

#### Phase 0 — Cleanup and bootstrapping

0.1 `olulerinBaglari(cag, not)` (derin.js): closes remaining state bonds of entities that died (via tools, Fate, or the previous epoch). → `yield 'olulerinBaglari'`.

0.2 `ateskesleriBitir(cag)` (derin.js): ends ceasefires whose term expired.

0.3 Language & first faith bootstrap: candidates = canonical entities of kind `halk|yerlesim|hizip|tarikat` that do NOT have tag `tanrısız` (godless) or `gezegene tapar` (worships the planet), AND (have no active `konusur` (speaks) bond OR (have no active `tapar` (worships) bond AND don't have tag `tanrı arayışı` (seeking a god))). Take the first `DE.dil_inanc_tavan` of them (in `kanonlar()` order) and call `dilVeInancBagla(v, cag, not)` (derin.js) for each: the community adopts the nearest language, the region's god, or a primitive language.

0.4 Snapshot: `vs = kanonlar()`; `topluluk` (communities) = `vs` filtered to kinds `hizip|halk|yerlesim|tarikat`. **Note: `vs` is a snapshot; many later phases re-read `getVarlik(id)` to check the entity is still canonical.**

#### Phase 1 — Divine grudges leak to mortals ("kin")

```
kin = 0
hamiOf = map community.id -> hami(community)
for i < j over topluluk (pairs in list order), while kin < DE.kin_tavan:
    ha, hb = patrons of a, b
    skip if !ha or !hb or ha.id == hb.id or a.world != b.world or mesafe(a,b) > DE.kin_mesafe
    if iliski(ha.id, hb.id) <= -DE.kin_iliski and sans(DM.kin_sans/100):
        holy = a.kind == 'tarikat' or b.kind == 'tarikat'
        reason = holy ? "holy war: {ha} and {hb}" : "the grudge between {ha} and {hb}"
        if !savasIlan(a, b, reason, cag): continue      # derin.js: refuses if ceasefire, rule/tribute bond, war cap...
        kin += 1
        not(holy ? "The grudge between {ha} and {hb} turned into a holy war: {a} and {b} drew swords on each other."
                 : "The grudge between {ha} and {hb} leaked to the mortals: {a} and {b} became enemies.", [a.id, b.id])
```

#### Phase 2 — Sub-engines (each followed by a `yield` with its name)

In this exact order:

| # | Call | Module | Purpose (spec'd in its module) |
|---|---|---|---|
| 2.1 | `diplomasi(cag, not)` | derin.js | community relations turn into war declarations, peace, alliances, betrayal |
| 2.2 | `seferler(cag, not, Y, H)` | derin.js | multi-epoch wars: armies, battles, sieges, captives (uses helper bag `H` above) |
| 2.3 | `seyahatMotoru(cag, not)` | seyahat.js | inter-world journeys |
| 2.4 | `kesifMotoru(cag, not)` | ufuk.js | exploration: unknown lands, new cosmic routes, sensed worlds, lands raised by foreign gods |
| 2.5 | `kaynakMekanikleri(cag, not)` | ekonomi.js | strange resources |
| 2.6 | `kozmikEkonomi(cag, not)` | ekonomi.js | cosmic economy |
| 2.7 | `korkuMotoru(cag, not)` | korku.js | cosmic horror: leakage, sanity, Outer Beings, horror events |
| 2.8 | `yaratikMotoru(cag, not)` | yaratik.js | creatures: traits, mutation, hybrids & chimeras, megafauna, ecology |
| 2.9 | `panteonMotoru(cag, not)` | panteon.js | foreign gods and cosmic threats to the creator |
| 2.10 | `olumMotoru(cag, not)` | olum.js | death & resurrection: rites/sacrifices for dead gods, sibling intrigues, foreign god collisions |
| 2.11 | `medeniyetMotoru(cag, not)` | medeniyet.js | civilization tiers, colony independence, federations, prior creation |
| 2.12 | `gokMotoru(cag, not)` | gok.js | sky events, time echoes |
| 2.13 | `otesiMotoru(cag, not)` | otesi.js | soul economy, planetary consciousness, cosmic archive, plagues, void storms, mirror world, legendary expeditions, immortality |

#### Phase 3 — Monster raids and heroes

Uses snapshot `vs`.
```
yerlesimler = vs where kind == 'yerlesim'
canavarEsik = buyuklukEsigi(vs where kind=='tur', 'tehlike', DM.canavar_yuzde/100, DM.canavar_alt, DM.canavar_ust)
canavarlar (monsters) = vs where kind=='tur' and (tehlike||0) >= canavarEsik(v)
```
(i.e. a species is a monster if its danger is at least the world's (canavar_yuzde)th percentile, clamped into [canavar_alt, canavar_ust]: default top 20%, at least 40, always if ≥55.)

3.1 Raids — for each monster `c`:
```
targets = settlements with mesafe(c, y) <= DE.baskin_mesafe
if no targets or not sans((c.tehlike||0) / DM.baskin_bolen): continue
y = random target
protector = first canonical 'olumlu' that has an active 'korur' (protects) bond -> y
if protector and c still canonical:
    kahramanlik(protector, c(fresh), cag, not, "while protecting {y}")   ; continue
if c no longer canonical: continue
loss = (c.tehlike || DE.baskin_tehlike) / DM.baskin_kayip_bolen          # fraction
y.nufus  = clamp((y.nufus || DE.baskin_nufus) * (1 - loss), SINIR.nufus_taban, SINIR.kent_nufus_tavan)
y.refah  = clamp((y.refah ?? DE.bilinmeyen_refah) - DE.baskin_refah, 0, 100)
y.savunma = clamp((y.savunma ?? DE.bilinmeyen_stat) + DE.baskin_savunma, 0, 100)   # walls are raised after a raid
save; if no 'avlar' bond c->y: addBag(c -> y, 'avlar', "raids")
not("{c} raided {y}; {round(loss*100)}% of the population was lost.", [c, y])
```
3.2 Sworn hunts — every active `avlar` bond from entity h to entity c where h is canonical `olumlu` and c is canonical `tur`: deactivate that bond, then `kahramanlik(h, c, cag, not, "in a sworn hunt")`. (Note: the raid bonds of 3.1 go from species→settlement so they don't match.)

3.3 Glory hunts — for each `olumlu` in `vs` with `guc + ceviklik >= DM.av_guc` and still canonical:
```
prey = monsters still canonical with mesafe(h, c) <= DE.av_mesafe and no 'oldurdu' (killed) bond h-c
if prey empty or not sans((h has tag 'seçilmiş' (chosen) ? DM.av_secilmis_sans : DM.av_sans)/100): continue
kahramanlik(h, random prey, cag, not, "in pursuit of glory")
```

#### Phase 4 — Trade, resources, prosperity reversion, curses

4.1 Trade income: for every active `ticaret` (trade) bond between two entities, for both endpoints that are canonical, accumulate `refah += DE.ticaret_refah × (endpoint knows 'ticaret' (trade) ? DE.ticaret_bilgi_carpan : 1)`, `servet += DE.ticaret_servet`. Then per entity: `refahEkle(stats, min(refah, DE.ticaret_refah_tavan))`; if it has `servet` (wealth): `servet = clamp(servet + min(servet_gain, DE.ticaret_servet_tavan), 0, 100)`; save. (Caps apply to the sum over all routes.)

4.2 Cursed decay: for each canonical entity tagged `lanetli` (cursed): for each stat in `refah, bereket, nufus, murit, bolluk, guc, servet` that exists: `nufus`/`murit` → `clamp(x × DE.lanet_nufus_kalan/100, 1, SINIR.nufus_tavan)`; others → `clamp(x − DE.lanet_stat, 0, 100)`. Save. If it's an `olumlu` and `DM.lanet_can > 0`: find the latest active `lanetledi` (cursed) bond targeting it (source type+id = the curser) and call `olumluYarala(v, DM.lanet_can, {sebep: "melted away under the curse and died", cag, not, katil: curser, katilTip: curser type})` — the curser is recorded as the killer if it dies.

4.3 Resource economy: for each canonical `kaynak` (resource) k: owners = canonical sources of active `sahip` bonds → k. Skip if none or `k.bolluk < DE.kaynak_bolluk_esik` (bolluk = abundance). For each owner: `gain = DE.kaynak_kazanc + round((k.deger || DE.bilinmeyen_stat)/DE.kaynak_deger_bolen)` (deger = value); for each of `refah`, `servet`, `zanaat` (craft) the owner has: refah via `refahEkle(gain)`, the others `clamp(round(x + gain), 0, 100)`; save if changed. Then `k.bolluk = clamp(k.bolluk − DE.kaynak_tuketim × owners, 0, 100)`; save. (Regeneration `kaynak_yenilenme` is applied in the epoch transition.)

4.4 Prosperity mean-reversion: for every canonical `halk|yerlesim|hizip|tarikat` with `refah != null`: `r = clamp(round(refah + (DE.refah_hedef − refah) × DE.refah_donus/100), 0, 100)`; save if changed.

4.5 Spontaneous resource barter & rivalry:
```
sahipKaynak = map ownerId -> set of canonical 'kaynak' ids it owns (active 'sahip' bonds)
tuccarlar (traders) = canonical 'yerlesim'|'hizip'|'halk'
yeniTicaret = 0
for i<j over traders while yeniTicaret < DE.ticaret_tavan:
    skip unless both own >=1 resource, no 'ticaret' and no 'dusman' (enemy) bond between them
    skip unless same top region (ustBolge(a).id == ustBolge(b).id)   # undefined==undefined counts as same here (smell)
    different = a owns something b doesn't AND b owns something a doesn't
    if not different:
        if sans(DM.rekabet_sans/100) and savasIlan(a, b, "rivalry over the same resource", cag):
            not("{a} and {b} fell out over the same resource.", [a,b])
        continue
    if sans(DM.takas_sans/100):
        addBag(a -> b, 'ticaret', "{a's resources joined ', '} in exchange for {b's resources}", cag)
        yeniTicaret += 1
        not("Resource barter began between {a} and {b}.", [a,b])
```

4.6 Curse lifting: for each canonical entity tagged `lanetli`: `p = (DM.lanet_kalkma + (knows 'buyu' (magic) ? DM.lanet_buyu_ek : 0) + (knows 'tip' (medicine) ? DM.lanet_tip_ek : 0))/100`; on success remove the tag and `not("The curse upon {v} was lifted.", [v])`.

4.7 Cursed items: for each canonical `esya` with `lanet >= DE.esya_lanet_esik`: owner = first active `sahip` bond source, must be canonical.
- if owner has `can` (HP) and is NOT `olumlu`: `can = clamp(can − round(lanet/DE.lanet_can_bolen), 1, SINIR.can_tavan)`.
- `refah`, `savunma` if present: `−round(lanet/DE.lanet_stat_bolen)`, clamp 0..100. Save.
- if owner is `olumlu` with `can`: `olumluYarala(o, round(lanet/DE.lanet_can_bolen), {sebep: "gave up their life to {item}'s curse", cag, not})`; if it returns `'oldu'` (died) → next item.
- `sans(DM.lanet_bulas_sans/100)` and owner not already cursed → add tag `lanetli` to owner and `not("{item}'s curse spread to its owner {o}.", [e, o])`.

4.8 Magic storms: for each canonical `bolge` with `buyu` (magic density) `>= DE.buyu_firtina_esik`, with probability `DM.buyu_firtina_sans/100`:
- affected = canonical `kaynak`/`esya` whose top region is r. For each: `kudret = clamp((kudret||0) + DE.firtina_kudret, 0, 100)`; with prob `DM.buyu_firtina_lanet/100`: `lanet = clamp((lanet||0) + DE.firtina_lanet, 0, 100)`; save.
- create event entity via `yerTut` (= `kayitAc`, see "Engine-created records"): `{tur:'olay', alt_tur:'büyü fırtınası' (magic storm), ad:"{r} Magic Storm", guc: DE.firtina_guc, konum_id: r, statlar:{siddet (severity): DE.firtina_siddet_taban + d(DE.firtina_siddet_zar)}, aciklama:"[World engine] The dense magic of {r} overflowed; resources and items grew stronger, some were cursed."}`.
- `not("A magic storm broke out in {r}; {n} resources and items grew stronger.", [r, event])`.

4.9 Resource regeneration: every canonical `kaynak`: `bolluk = clamp((bolluk||0) + DE.kaynak_yenilenme, 0, 100)`; save.

#### Engine-created records (`yerTut` = derin.js `kayitAc`)

`kayitAc({tur, alt_tur, ad, aciklama, statlar, konum_id, cag, guc = ILISKI.kayit_guc, etiketler = [], unvan = null})`:
1. `ad` made unique (`benzersizAdR`), `aciklama` passed through `kendiniAnlat` (self-description helper).
2. INSERT into `varliklar` with `kaynak='dunya'` (source = world engine), `bekliyor=1` (pending Fate's naming/narration), given stats/power/epoch/location/tags/title(unvan). Status defaults to canonical.
3. If `konum_id` set (and ≠ self): bond `id -icinde(inside)-> konum_id`.
4. Returns new id.

The `[Dünya motoru]` prefix ("[World engine]") in descriptions marks engine-authored descriptions which Fate later rewrites.

#### Phase 5 — Society dynamics

5.1 Cult schisms (at most `DE.bolunme_tavan` per tick):
```
threshold = buyuklukEsigi(canonical tarikat, 'murit', DE.bolunme_yuzde/100, DM.bolunme_alt, DE.bolunme_ust)
eligible t: tarikat with murit >= threshold(t) and (cag - t.cag) >= DE.bolunme_yas
            and (bagnazlik >= DM.bolunme_bagnazlik  OR  (murit >= DM.bolunme_buyuk and cag - t.cag >= DE.bolunme_buyuk_yas))
for t in eligible:
    if bolunme >= DE.bolunme_tavan: continue
    p = (bagnazlik >= DM.bolunme_bagnazlik ? DM.bolunme_bagnaz_sans : DM.bolunme_buyuk_sans)/100 ; if !sans(p) continue
    oldPatron = hami(t)
    candidate = son with highest karizma among active sons (durum 'aktif') != oldPatron whose aktif_dunya (current world, default 1) == t's world;
                fallback: highest-karizma active son != oldPatron anywhere; none -> continue
    split = round(t.murit * DM.bolunme_pay/100); t.murit -= split; save
    new = kayitAc({tur:'tarikat', alt_tur:'ayrılıkçı mezhep' (separatist sect), ad: adKoku(t.ad, ' Ayrıkları') + " Ayrıkları" ("{root} Schismatics"),
                   guc: max(DE.ayrilan_guc_taban, t.guc - 1), konum_id: t.konum_id,
                   statlar:{murit: split, bagnazlik: clamp(t.bagnazlik + DE.bolunme_bagnazlik_artis), etki: clamp((t.etki || DE.bilinmeyen_stat) - DE.bolunme_etki_dusus)},
                   aciklama:"[World engine] A schism occurred within {t}; {split} followers broke away and turned to {candidate}."})
    savasIlan(new, t, 'schism', cag)
    bond new -tapar(worships)-> son candidate ; if t speaks language L: new -konusur-> L
    if oldPatron: iliskiDegistir(oldPatron, candidate, -DE.bolunme_iliski)
    bolunme++ ; not("{t} split: {split} followers turned to {candidate}.", [t, new], son=candidate)
```

5.2 Creature migration (at most `DE.goc_tavan`): `bilgiH = haritaHesapla().bilgi` (map info by region id: `komsular` neighbours, `yukseklik` elevation class, `kiyi` coastal; see Map section). For each canonical `tur` with `tehlike >= DE.yaratik_goc_tehlike`: if cap reached or `!sans(DM.yaratik_goc_sans/100)` skip; r = top region of c; neighbours = canonical regions in `bilgiH[r].komsular` whose elevation is not `'su'` (water); target = first neighbour without an existing `yasar` (lives in) bond c→x; if found: bond `c -yasar-> target` ("Epoch {cag} migration"), `not("Herds of {c} spilled out of {r} and spread into the lands of {target}.", [c, target])`.

5.3 Spontaneous hero birth (at most `DE.kahraman_tavan`):
```
threshold = buyuklukEsigi(canonical halk|yerlesim, 'nufus', MOTOR.kahraman_yuzde/100, DM.kahraman_alt, DE.kahraman_ust)   # MOTOR = derin.js tunables
for h in canonical halk|yerlesim with nufus >= threshold(h):
    p = (DM.kahraman_sans + (h has any active 'dusman' bond ? DM.kahraman_savas_ek : 0))/100
    if cap reached or !sans(p): continue
    name = dildenAd(h, "{h.id}:{cag}:kahraman", 'kisi')     # name from h's language, deterministic seed string, 'person' type
    k = kayitAc({tur:'olumlu', alt_tur:'kahraman' (hero), ad: name || "{h} Hero", guc: DE.kahraman_guc_seviye,
                 etiketler: name ? ['dilden-ad'] : [],      # 'dilden-ad' = "name derived from language"
                 konum_id: h.kind=='yerlesim' ? h.id : h.konum_id,
                 statlar:{can: DE.kahraman_can, guc: DE.kahraman_guc_taban+d(DE.kahraman_guc_zar), ceviklik: DE.kahraman_cev_taban+d(DE.kahraman_cev_zar),
                          akil: DE.kahraman_akil_taban+d(DE.kahraman_akil_zar), karizma: DE.kahraman_kar_taban+d(DE.kahraman_kar_zar),
                          yas: DE.kahraman_yas_taban+d(DE.kahraman_yas_zar), omur: DE.kahraman_omur_taban+d(DE.kahraman_omur_zar)},
                 unvan: "{h} Hero", aciklama:"[World engine] From among {h}, a hero arose in answer to the troubles of the age."})
    bonds: k -soyundan(descends from)-> h ; k -tapar-> hami(h) if any ; k -konusur-> language of h if any
    not("A new hero was born among {h}.", [h, k])
```
Mortal stats: `can` HP, `guc` strength, `ceviklik` agility, `akil` intellect, `karizma` charisma, `yas` age (years), `omur` lifespan (years).

5.4 Knowledge and language diffusion: for every active bond of kind `ticaret|muttefik|yonetir|harac_oder` (trade, ally, rules, pays tribute) between canonical entities A,B; for both directions (x→y):
- for each knowledge t that x knows (`bildikleri(x)`, mudahale.js): skip if `yayilim >= DE.yayilim_tavan` or y knows t; with prob `DM.bilgi_yayilim_sans/100 × (x knows 'yazi' (writing) ? DE.yazi_carpan : 1)`: `ogret(y, t, cag, "spread from {x}")`, `yayilim++`, `not("Knowledge of {t} spread from {x} to {y}.", [x,y,t])`.
- after both directions: if law `tek_dil` (one language) is active in B's world (`Y.has('tek_dil', B)`): L = language A speaks; if L and B doesn't already speak L and `sans(DM.dil_yayilim_sans/100)`: bond `B -konusur-> L` ("spread"), `not("The {L} language spread among {B}.", [B, L])` (uses `toplulukIci` = LANGUAGE-SPECIFIC "inside community" locative phrase).
Note: language spread is one-directional (A→B, i.e. bond source to target) and B does not drop its old language.

5.5 `kulturAlisverisi(cag, not)` (derin.js): cultural exchange at first contact and along trade routes (loan words, traditions, knowledge, gods). → `yield 'kulturAlisverisi'`.

5.6 Natural disasters (shared counter `afet`, cap `DM.afet_tavan`):
- `carpanAfet(x) = Y.has('afet' (disaster law), x) ? DE.afet_yasasi_carpan : 1`; `vebaCarpan(x) = (iklimOf(world).veba || 1) × carpanAfet(x)` (climate plague multiplier from derin.js climate).
- Region disasters: iterate canonical `bolge` having map info and elevation ≠ `'su'` (break when cap reached). Candidate list in this order:
  - elevation `'dağlık'` (mountainous) or `'engebeli'` (hilly) → `['deprem' earthquake, DM.deprem_sans/100]`
  - coastal (`kiyi`) → `['sel' flood, DM.sel_sans/100]`, `['firtina' storm, DM.firtina_sans/100]`
  - `bereket (?? DE.bilinmeyen_bereket) < DE.kurak_bereket` OR law `kuraklik` (drought) active → `['kuraklik' drought, DM.kuraklik_sans/100]`
  - regional population = Σ nufus of canonical halk/yerlesim in region; if `>= DM.bolge_veba_nufus` → `['veba' plague, DM.bolge_veba_sans/100 + min(DE.veba_ek_tavan/100, pop/DE.veba_nufus_bolen)]`
  - For each candidate in order: roll `sans(p × carpanAfet(r) × (veba ? climate.veba||1 : 1))`; on the FIRST success: `siddet = DE.afet_siddet_taban + d(DE.afet_siddet_zar)`; `results = afetUygula(r, kind, siddet/DE.afet_siddet_olcek)` (mudahale.js; returns list of effect strings); `oid = olayKaydi({tur: kind, hedef: r, cag, siddet})` (event record, mudahale.js); `afet++`; `not("Nature raged over {r}: {AFETLER[kind].ad lowercased}. {results joined '; '}.", [r, oid])`; stop processing this region (max one disaster per region).
- City plague: `kentEsik = buyuklukEsigi(canonical yerlesim, 'nufus', DE.kent_veba_yuzde/100, DM.kent_veba_alt, DE.kent_veba_ust)`; `savastaMi(id)` = has an active `dusman` bond; `acMi(y)` = `(toplumOf(y).e.erzak ?? DE.erzak_varsayilan) < DE.ac_erzak` (erzak = granary/food store in the society economy model).
  For each canonical settlement with `nufus >= DE.kent_veba_en_az` and (crowded `nufus >= kentEsik` or hungry or at war): `p = ((crowded? DM.kent_veba_sans) + (hungry? DM.ac_veba_sans) + (war? DM.savas_veba_sans))/100`; skip if cap reached or `!sans(p × vebaCarpan(y))`; else severity as above, `afetUygula(y, 'veba', siddet/DE.afet_siddet_olcek)`, `olayKaydi(...)`, `afet++`, `not("An epidemic broke out in crowded {y}. {results}.", [y, oid])`.
- Plague spreading along routes: for each canonical `olay` tagged `veba` with `olay.cag >= cag − DE.veba_yayilim_cag`: source = target of its first active `neden_oldu` (caused) bond. Partners = distinct canonical entities linked to the source by active `ticaret|harac_oder|yonetir` bonds and not already linked from the event by `neden_oldu`. For each partner: roll `(partner knows 'tip' ? DM.veba_yayilim_tip_sans : DM.veba_yayilim_sans)/100`; skip unless kind in `halk|yerlesim|tarikat|hizip`; `afetUygula(x, 'veba', DE.veba_yayilim_siddet/100)`; bond `event -neden_oldu-> x` ("spread along the roads"); `not("{event} jumped to {x}; merchants, tribute bearers and governors carried the disease too.", [event, x])`. (Not counted toward `afet` cap.)

5.7 Famine migration (at most `DE.kitlik_tavan`): for canonical `yerlesim|halk` with `nufus > DE.kitlik_nufus` (break when cap reached):
```
hungry = (toplumOf(y).e.erzak ?? DE.erzak_varsayilan) < DE.ac_erzak  or  (refah ?? DE.bilinmeyen_refah) < DE.kitlik_refah
if !hungry or !sans(DM.kitlik_goc_sans/100): continue
r = top region; srcB = r.bereket ?? DE.bilinmeyen_bereket
target = among bilgiH[r].komsular: canonical 'bolge' in same world, not water, bereket > srcB + DE.kitlik_bereket_fark; pick highest bereket
if none: continue
goc = round(y.nufus * MOTOR.kitlik_goc_pay/100); y.nufus -= goc; save
name = dildenAd(y, "{y.id}:{cag}:goc", 'yer')    # place name from language
ruin = harabeyeKur(target, y, goc, cag, 'those fleeing famine')   # derin.js: refound an existing ruin in target region if any; returns id or null
newY = ruin || kayitAc({tur:'yerlesim', alt_tur:'göçmen yerleşimi' (migrant settlement), ad: name || "{y} Migrants", etiketler: name? ['dilden-ad'] : [],
                         guc: max(DE.ayrilan_guc_taban, y.guc-1), konum_id: target,
                         statlar:{nufus: goc, refah: DE.gocmen_refah, savunma: DE.gocmen_savunma, inanc: DE.gocmen_inanc},
                         aciklama:"[World engine] {goc} people fleeing famine in {y} migrated to the lands of {target} and founded a new settlement."})
bond y -gocetti(migrated)-> newY ("famine: {goc} people"); if not ruin: newY -soyundan-> y
dilVeInancBagla(newY, cag, not, {kaynak: y})        # inherit language & faith from source
not(ruin ? "Famine drove {goc} people from {y} to the lands of {target}; they rebuilt the ruin of {newY}."
         : "Famine drove {goc} people from {y} to the lands of {target}; there they founded a new settlement.", [y, newY, target])
```

5.8 `multeciler(cag, not)` (derin.js): refugees fleeing war and disaster. → `yield 'multeciler'`.

5.9 Uprisings (at most `DE.isyan_tavan`):
```
threshold = buyuklukEsigi(canonical yerlesim, 'nufus', DE.isyan_yuzde/100, DM.isyan_alt, DE.isyan_ust)
for y in canonical yerlesim with (refah ?? DE.bilinmeyen_refah) < DM.isyan_refah and nufus >= threshold(y):
    just = exists canonical 'kanun' (law) with konum_id = y and adalet (justice) >= DE.adil_kanun
    if cap reached or !sans((just ? DM.isyan_adil_sans : DM.isyan_sans)/100): continue
    ruler = source of first active 'yonetir' bond -> y
    h = kayitAc({tur:'hizip', alt_tur:'isyancılar' (rebels), ad:"{y} Rebels", guc: DE.isyanci_guc_seviye, konum_id: y,
                 statlar:{guc: DE.isyanci_guc_taban+d(DE.isyanci_guc_zar), servet: DE.isyanci_servet_taban+d(..zar), nufuz: DE.isyanci_nufuz_taban+d(..zar)},
                 aciklama:"[World engine] Poverty and crowding in {y} gave birth to an uprising."})
    savasIlan(h, isyanHedefi(y), 'uprising', cag, {tavan: false})   # isyanHedefi (derin.js): the ruling community or the city itself (never a mortal ruler); war cap ignored
    h -konusur-> language of y
    y.savunma = clamp((savunma ?? DE.bilinmeyen_stat) - DE.isyan_savunma); y.refah = clamp((refah ?? DE.bilinmeyen_stat) - DE.isyan_refah)  # note: refah default here uses bilinmeyen_stat (30), not bilinmeyen_refah
    not("Poverty in {y} turned into an uprising; the rebels defied {ruler ? ruler's rule : 'the order of the city'}.", [y, h])
```

5.10 `ruhlarDiner(cag, not)` (derin.js): spirits calm down over time or pass to the land of the dead; a place keeps at most a few spirits. → `yield 'ruhlarDiner'`.

5.11 Hauntings: for each canonical `ruh` (spirit) with `huzursuzluk` (restlessness) `>= KY.huzursuz_esik`: y = first canonical settlement in the same top region; with prob `DM.ruh_musallat_sans/100`: `y.refah −= DE.musallat_refah` (clamp, default `bilinmeyen_refah`), `r.huzursuzluk −= DE.musallat_huzur`; `not("{r} haunted {y}; no one goes out into the streets at night.", [r, y])`. (No bond is created.)

5.12 Laws: for each canonical settlement with ≥1 canonical `kanun` located in it: `adalet = mean(k.adalet || DE.bilinmeyen_adalet)`; `savunma += (adalet >= DE.kanun_adil_esik ? DE.kanun_savunma : 0)` (clamp 0..100, default `bilinmeyen_stat`); if `adalet < DE.kanun_adaletsiz`: `refah −= DE.kanun_refah`; save.

5.13 Currency (coinage):
- `paraOf(id)` = first canonical `esya` with `alt_tur = 'para birimi'` (currency) owned (active `sahip`) by id.
- Minting: for canonical `yerlesim|hizip` that know 'ticaret' and have `refah >= DE.sikke_esik` or `servet >= DE.sikke_esik` (missing = 0): skip if it already has a currency or `!sans(DM.sikke_sans/100)`; create `kayitAc({tur:'esya', alt_tur:'para birimi', ad:"{t} Coin", guc: DE.sikke_guc, konum_id: settlement ? t : t.konum_id, statlar:{hasar:0, koruma:0, kudret: DE.sikke_kudret_taban + d(DE.sikke_kudret_zar), lanet:0}, aciklama:"[World engine] {t} began to mint its own money."})`; bonds `t -uretti(produced)-> coin` ("minting") and `t -sahip-> coin`; `not("{t} began minting its own coin.", [t, coin])`.
- Adoption along trade: `paraUcu(id)` = entity is canonical `halk|yerlesim|hizip|tarikat`; `ayniYer(a,b)` = same world (dunya_id default 1) OR an active, known (`bilinen=1`) route exists in table `rotalar` between their worlds (either direction). For every active `ticaret` bond a→b with both ends valid and `ayniYer`:
  - a has currency pa, b has none, `sans(DM.para_benimse_sans/100)` → bond `b -sahip-> pa` ("adopted through trade"), `not("{b} began using {a}'s money.", [a,b,pa])`;
  - else symmetric case for b's currency;
  - else if both use the same currency: each end with refah gets `refahEkle(DE.ortak_para_refah)`.

5.14 Wizards: for each canonical `olumlu` with `akil >= DE.buyucu_akil` that knows 'buyu' (magic):
- if not tagged `büyücü` (wizard): add tag, `not("{b} deciphered the language of magic; now a wizard.", [b])`.
- `sans(DM.buyucu_eylem_sans/100)` else skip. `home = getVarlik(b.konum_id)`. `enemy` = the other end of the first active `dusman` bond of home.
- if enemy and `sans(DM.buyucu_lanet_sans/100)`: enemy must be canonical; add tag `lanetli` to enemy; bond `b -lanetledi-> enemy` ("by magic"); `not("Wizard {b} cursed {home}'s enemy {enemy}.", [b, enemy])`.
- else if home kind is `yerlesim` or `yer` (place): `mucizeUygula(home, sans(DE.buyucu_koruma_sans/100) ? 'koruma' (protection) : 'bereket' (fertility), cag)` (mudahale.js); `not("Wizard {b} wove a protective spell over {home}.", [b, home])` (same text even when it's a fertility spell — smell).

5.15 Creature rebellion: for each canonical `tur` with a creator (`yaratan_id` = creating son), `zeka >= DE.yaratik_isyan_zeka` and `tehlike >= DE.yaratik_isyan_tehlike`, with prob `DM.yaratik_isyan_sans/100`: creator son must exist; add bond `species -dusman-> son` ("rebellion against its creator") if not present; worshipper = first canonical `halk|yerlesim|tarikat` in same world whose patron is that son; if found: `nufus`/`murit` ×`DE.yaratik_isyan_kalan/100` (clamp 1..SINIR.nufus_tavan); `UPDATE ogullar SET varlik = max(0, varlik − DE.yaratik_isyan_varlik)` (son's existence/varlik stat); `not("{t} rose up against its creator {son}[; it attacked {worshipper} who worships them].", [t, worshipper?], son)`. (Repeats every tick with probability; no cooldown.)

5.16 Godlessness: canonical `halk|yerlesim|hizip` with no patron, no tags `tanrısız|tanrı arayışı|gezegene tapar`, `inanc (?? DE.bilinmeyen_inanc) < DE.tanrisizlik_inanc` and no active outgoing `tapar` bond: with prob `DM.tanrisizlik_sans/100` add tag `tanrısız` (godless) and `not("{v} turned its back on the gods; now godless.", [v])`. (Worshipping the creator directly is a `tapar` bond to type 'y', so those are excluded.)

5.17 Species evolution (at most `DE.evrim_tavan`, break on cap): for each canonical `tur`: `g` = its oldest active `yasar` (lives in) bond created at epoch `<= cag − DE.evrim_cag`; if none or `!sans(DM.evrim_sans/100)` skip; home = g.target (canonical). New stats = copy; for each of `guc, ceviklik, zeka, tehlike` present: `clamp(x + d(2s+1) − s − 1, 0, 100)` with `s = DE.evrim_sapma` (uniform in [−s, +s]). Create `kayitAc({tur:'tur', alt_tur:'alt tür' (subspecies), ad:"{home} {t}" (Turkish: "{home} {t}i", possessive compound — LANGUAGE-SPECIFIC), guc: t.guc, konum_id: home, statlar, aciklama:"[World engine] Over generations in the lands of {home}, {t} changed into a distinct subspecies (intelligence {zeka}, danger {tehlike})."})`; bond `new -soyundan-> t` ("evolution"); deactivate the `yasar` bond t→home; `not("{t} diverged into a new subspecies in the lands of {home}.", [t, new, home])`.

5.18 Births from couples (at most `DE.dogum_tavan`, break on cap): for each active bond of kind `sever` (loves) or `muttefik` (ally) between two canonical `olumlu`, with prob `DM.dogum_sans/100`:
```
sap() = d(2*DE.kalitim_sapma + 1) - DE.kalitim_sapma - 1                  # uniform [-s, s]
avg(k) = clamp(((A[k] || DE.kalitim_stat) + (B[k] || DE.kalitim_stat))/2 + sap(), 0, 100)
name = dildenAd(A, "{A}:{B}:{cag}:cocuk", 'kisi') || dildenAd(B, "{B}:{A}:{cag}:cocuk", 'kisi')
c = kayitAc({tur:'olumlu', alt_tur:'çocuk' (child), ad: name || "Child of {A} and {B}", etiketler: name? ['dilden-ad'] : [],
             guc: max(1, round((A.guc+B.guc)/2) - 1), konum_id: A.konum_id,
             statlar:{can: DE.cocuk_can, guc: avg('guc'), ceviklik: avg('ceviklik'), akil: avg('akil'), karizma: avg('karizma'), yas: 0,
                      omur: clamp(((A.omur||DE.omur_varsayilan)+(B.omur||DE.omur_varsayilan))/2 + sap(), DE.cocuk_omur_en_az, DE.omur_tavan)},
             aciklama:"[World engine] A child was born from the union of {A} and {B}."})
bonds c -soyundan-> A, c -soyundan-> B, c -konusur-> (lang(A) || lang(B)), c -tapar-> (hami(A) || hami(B))
not("A child of {A} and {B} was born.", [A, B, c])
```
(Note the bond kinds used are `sever` and `muttefik`, not `es`/`sevgili`; the tunable label says "lovers or spouses".)

5.19 Love and rivalry: `olumlular` = canonical `olumlu` with `yas >= DE.ask_yas`. For every pair i<j with the same `konum_id`, no `sever` and no `dusman` bond, `sans(DM.ask_rekabet_sans/100)`: `love = sans(DM.ask_orani/100)`; bond `A -(love ? 'sever' : 'dusman')-> B` (description "love"/"rivalry"); `not(love ? "Love blossomed between {A} and {B}." : "A rivalry began between {A} and {B}.", [A,B])`. **No cap; O(n²) over all adult mortals.** (Note: `A.konum_id === B.konum_id` is also true when both are null.)

5.20 Dialect divergence (at most `DE.lehce_tavan`, break on cap): for canonical `yerlesim` with `cag − y.cag >= DE.lehce_cag`:
```
L = konusulanDil(y) ; none -> skip            # world.js: the language an entity speaks
homeland = canonical halk|yerlesim (≠ y) speaking L
linked(x) = any of 'ticaret','yonetir','muttefik','harac_oder' bonds between x and y
cutOff = homeland non-empty and no homeland member is in y's top region or linked to y
if !cutOff or !sans(DM.lehce_sans/100): continue
D = kayitAc({tur:'dil', alt_tur:'lehçe' (dialect), ad:"{y} Dialect", guc: DE.lehce_guc,
             statlar:{yayginlik (prevalence): DE.lehce_yayginlik, karmasiklik (complexity): DE.lehce_karmasiklik, kutsallik (sacredness): DE.lehce_kutsallik},
             aciklama:"[World engine] The branch of the {L} language that diverged over time in {y}, far from its homeland."})
bond D -soyundan-> L ("divergence"); deactivate y -konusur-> L; bond y -konusur-> D
copy DE.lehce_kelime random words: shuffle(SELECT * FROM sozluk WHERE dil_id=L ORDER BY id) take first N;
   INSERT sozluk(dil_id=D, kelime, anlam, tur, koken="from the word \"{kelime}\" in the {L} language", ekleyen_tip='v', ekleyen_id=y, cag)
not("The {L} spoken in {y} broke from its homeland and began to diverge into a new language.", [y, L, D])
```
(Dialect has no `konum_id`.) Vocabulary table `sozluk`: `dil_id, kelime (word), anlam (meaning), tur (word class), koken (etymology), ekleyen_tip/ekleyen_id (who added), cag`.

5.21 `dilOlumu(cag, not)` (derin.js): a language with no living speakers dies (if it had writing it can be deciphered in ruins). → `yield 'dilOlumu'`.

5.22 Law "price of magic" (`buyu_bedeli`): if active in any world (`Y.has('buyu_bedeli')` with no entity = union of all worlds), for every canonical `halk` with `buyu > DE.buyu_bedeli_esik` whose own world has the law: `nufus = clamp(nufus × DE.buyu_bedeli_kalan/100, SINIR.halk_nufus_taban, SINIR.nufus_tavan)`.

5.23 Architecture: every canonical settlement that knows 'mimarlik' (architecture): `savunma = clamp((savunma ?? DE.bilinmeyen_stat) + DE.mimarlik_savunma, 0, 100)`. (No cap other than 100 — combined with 5.12 and raids, walls trend upward monotonically.)

#### Phase 6 — Society sub-engines (derin.js), each followed by `yield`

In order: `toplumEkonomi(cag, not, Y)` (social strata & economy: classes, granary/erzak, taxes), `kahramanlar(cag, not, H)` (heroes' quests), `dogumlar(cag, not)` (births of notable mortals in communities), `hizipler(cag, not)` (factions), `yapitlar(cag, not)` (structures/works), `dinYayilimi(cag, not)` (religion spread), `yasamTohumu(cag, not)` (seed of life — spontaneous life/peoples in empty lands), `yazilar(cag, not)` (writings), `inancVeBellek(cag, not)` (faith and memory), `casusluk(cag, not)` (espionage), `harikalar(cag, not)` (wonders), `karanlikCaglar(cag, not)` (dark ages), `harabeler(cag, not)` (ruination of abandoned settlements). All specified in the derin.js spec.

#### Phase 7 — Mortal aging and death

```
tipBolgeleri = set of top-region ids of canonical yerlesim|halk that know 'tip' (medicine)     # computed once
wNow = getWorld()
# 7.1 mortal wounds
for v in canonical olumlu with can != null and can <= 0 and not olumsuzMu(v):
    olumluOlur(v, cag, not, {sebep: "succumbed to their wounds"})
# 7.2 aging
for v in canonical olumlu:                                      # note: kanonlar() re-read, so those who just died are excluded
    Yv = Y.of(v)                                                 # laws of v's world
    if Yv.has('olumsuzluk' (immortality law)) or olumsuzMu(v): continue
    first = (v.cag == cag)                                       # created this epoch
    omur0 = v.omur || DE.omur_varsayilan
    if first and (v.yas||0) >= omur0 - DE.yasli_pay:             # created too old to survive its own birth epoch -> rejuvenate
        v.yas = round(omur0 * (DE.genclesme_taban/100 + random() * DE.genclesme_zar/100))
    dur = first ? (v.kaynak == 'dunya' ? DM.ilk_cag_motor : DM.ilk_cag_ogul) : CAG_YIL   # engine-born appear ~year 35, son/mortal-created ~year 15 of a 50-year epoch
    mult = (Yv.has('kisa_omur' (short life law)) ? DE.kisa_omur_carpan : 1) * dunyaFizigi(v.dunya_id).zaman   # world time factor (dream realm faster, realm of the dead nearly frozen)
    before = v.yas || 0
    v.yas = before + round(dur * mult)
    omur = etkinOmur(v, tipBolgeleri).etkin
    if v.yas < omur: save; continue
    deathAge = max(before, omur)
    deathYear = (wNow.yil ?? 0) + (first ? CAG_YIL - dur : 0)
                + min(CAG_YIL - 1, max(0, round((deathAge - before) / max(0.1, mult))))
    v.yas = deathAge; save
    if Yv.has('olu_doner' (the dead return law)) and sans(DM.hayalet_sans/100):
        tags += 'hayalet' (ghost); kader_notu (fate note) += " Epoch {cag}, world year {deathYear}: died at age {deathAge} and returned as a ghost."
        not("{v} died but the law of the world called them back: now a ghost.", [v], son = v.yaratan_id)
        continue
    olumluOlur(v, cag, not, {dogal: true, yil: deathYear})
```
`CAG_YIL` = rule `ZAMAN.cag_yil` (default 50 years per epoch, range 1..100000, group "Epoch flow"); it is a live binding (re-read every use). `wNow.yil` = current world year (start of the epoch).

7.3 `olulerinBaglari(cag, not)` again: close state bonds of this epoch's dead; property passes to heirs. → `yield 'olulerinBaglari'`.

7.4 `kronikYaz(cag, bekleyen, bas)` — write the chronicle (below).

7.5 `isaretle(notlar)` if provided (inside the transaction).

Return `notlar` (array of strings, suffix-fixed).

### Mortal lifecycle helpers

- `olumsuzMu(v)` (is immortal): has tag `ölümsüz` (immortal) or `hayalet` (ghost).
- `onemliOlumlu(v)` (important mortal): has any tag in `seçilmiş` (chosen), `yönetici` (ruler), `çağ değiştiren` (age-changer), `büyücü` (wizard), or any tag starting with `unvan:` (title:), OR `alt_tur` matches regex `/kahraman|hükümdar|reis|başrahip|lider|bilge|kâhin/i` (hero, sovereign, chief, high priest, leader, sage, seer), OR `karizma >= DE.onemli_karizma`.
- `etkinOmur(v, tipBolgeleri = null)` (effective lifespan; the UI shows the same calculation): `taban = v.omur || DE.omur_varsayilan`; `tip = (v's top region contains a canonical yerlesim|halk that knows 'tip') ? DM.tip_omur : 0` (uses the precomputed set if given, else scans); `onemli = onemliOlumlu(v) ? DM.onemli_omur : 0`; returns `{taban, tip, onemli, etkin: taban+tip+onemli}`.
- `yasTutarliligi()` (age consistency; run at startup, idempotent): for every dead `olumlu` whose `yas > omur` (as integers): if `yas > etkinOmur.etkin`, set `omur = clamp(yas − (etkin − taban), 1, DE.omur_tavan)` so the effective lifespan equals the death age. Returns count fixed.

#### `olumluYarala(v, damage, opts)` — wound a mortal

```
v = fresh entity; if not canonical 'olumlu' -> return null
if olumsuzMu(v): return 'ölümsüz' (immortal)
v.can = max(0, round((v.can ?? DE.varis_can) - damage)); save
if v.can > 0: return 'yarali' (wounded)
return olumluOlur(v, opts.cag ?? world.cag, opts.not || noop, opts) ? 'oldu' (died) : 'yarali'
```
`opts` = `{sebep, cag, not, katil, katilTip}` forwarded to `olumluOlur`.

#### `olumluOlur(v, cag, not, {sebep='öldü' (died), katil=null, katilTip='v', yil=null, dogal=false, zorla=false})` — THE single death path for named mortals

```
v = fresh; require kind 'olumlu' and durum in ('kanon','gerceklesti' (realized))  else return null
if !zorla and olumsuzMu(v): return null            # zorla = force, kills even immortals
deathYear = yil ?? (world.yil ?? 0) + d(CAG_YIL) - 1
v.statlar.olum_yili = deathYear
UPDATE varliklar SET statlar, durum='olu' (dead), olum_cag=cag,
       kader_notu += dogal ? " Epoch {cag}, world year {deathYear}: died at age {yas}."
                           : " Epoch {cag}, world year {deathYear}: {sebep} (age {yas ?? '?'})."
if katil.id != null: addBag(katilTip, katil.id -> v, 'oldurdu' (killed), sebep)
sonuYaz(v.id, dogal ? "Died in epoch {cag}, at age {yas}." : "In epoch {cag} {sebep} (age {yas ?? '?'}).")   # world.js: writes the entity's "ending" text
heir = yonetimiDevret(v, cag)
text = dogal ? "{v} died at age {yas}{heir ? '; an heir took their place' : '. Their name now lives only in the tales'}."
             : "{v} {sebep}{heir ? '; an heir took their place' : ''}."
not(text, [v, heir?, (katil if katilTip=='v')], son = katilTip=='o' ? katil.id : v.yaratan_id)
olumSonrasi(v, cag, not)
olulerinBaglari(cag, noop, v.id)          # close this one entity's state bonds now
return {id, varis: heir, metin: text}
```
Note: `sebep` is a Turkish verb phrase that is appended directly after the name ("{name} {sebep}") — in English the reason strings must be full predicates, e.g. "succumbed to their wounds".

#### `yonetimiDevret(v, cag)` — succession (rulership passes to an heir on every death path)

```
bonds = active 'yonetir' (rules) bonds from v
shared(b) = b targets an entity also ruled (active 'yonetir') by ANOTHER canonical 'olumlu'   # co-throne
for b in bonds where shared(b): deactivate b          # the co-ruler keeps it; no heir
ruled = bonds not shared ; if empty: return null
ruledEntities = targets (entity type only)
primary = first ruledEntity whose kind in HUKUMDARLIK = ['yerlesim','halk','hizip','tarikat','bolge','yer'], else first ruledEntity
heirName = kisiAdi([v, primary], "{v.id}:{cag}:varis", v.dunya_id)      # derin.js: tries language names (4 seeds × sources, then world's top-3 languages)
           || adKoku(adKoku(v.ad, "'in Varisi"), "'nin Varisi|'ın Varisi|'un Varisi|'ün Varisi")   # fallback: dead ruler's root name (never "X's Heir")
title = primary ? yonetimUnvani(primary.ad, primary.kind) : "of the line of {adKoku(v.unvan || v.ad, "'in Varisi")}"   # yonetimUnvani (dil.js): ruler title by governed kind
sap() = uniform [-DE.kalitim_sapma, +DE.kalitim_sapma]
heir = kayitAc({tur:'olumlu', alt_tur:'varis' (heir), ad: heirName, etiketler:['dilden-ad','yönetici' (ruler)], guc: max(1, v.guc-1),
                konum_id: v.konum_id, unvan: title,
                statlar:{can: DE.varis_can, guc/ceviklik/akil/karizma: clamp((v[k] || DE.kalitim_stat) + sap(), 0, 100),
                         yas: DE.varis_yas_taban + d(DE.varis_yas_zar),
                         omur: clamp((v.omur || DE.omur_varsayilan) + uniform[-DE.varis_omur_sapma, +DE.varis_omur_sapma], DE.varis_omur_en_az, DE.omur_tavan)},
                aciklama:"[World engine] {v} died and left what they ruled to them."})
bond heir -soyundan-> v
bond heir -konusur-> (lang(v) || lang(primary))
bond heir -tapar-> hami(v) if that son isn't dead
for b in ruled: deactivate b; addBag('v', heir, b.hedef_tip, b.hedef_id, 'yonetir', 'inheritance')
return heir
```
(Comment says the fallback is "X II" with a roman numeral; the actual code returns the bare root, and `kayitAc`'s `benzersizAdR` makes it unique — probably by appending a numeral.)

#### `olumSonrasi(v, cag, not)` — consequences of a death

```
underworlds = canonical 'bolge' whose "{ad} {alt_tur}" matches OBUR_DUNYA_DESEN
   (regex /ölü|yeraltı|öbür|cehennem|cennet|ruhlar|dip|mezar|ahiret|karanlık kat|alt dünya/i —
    dead|underground|otherworld|hell|heaven|spirits|depths|grave|afterlife|dark floor|underworld; LANGUAGE-SPECIFIC: replace with a region flag)
underworld = first in v's own world, else first located in a world whose dunyalar.tur == 'olu' (realm of the dead), else null
if underworld: bond v -ruhu_indi(soul descended)-> underworld ("the soul descended there")
for each son whose domain alan1 or alan2 in OLUM_ALANLARI = ['Ölüm' Death,'Kemik' Bone,'Bellek' Memory,'Uyku' Sleep,'Kül' Ash]:
    s.oz = min(ozMax(s.statlar), s.oz + DE.olum_alani_oz); s.varlik = min(100, (s.varlik ?? DE.varlik_varsayilan) + DE.olum_alani_varlik); saveSon
# inheritance of items
heirRow = latest active 'soyundan' bond whose TARGET is v (i.e. a descendant of v)
place = v.konum_id entity
receiver = heir entity if any, else place if place kind in yerlesim|halk|tarikat|hizip, else null
for each active 'sahip' bond v -> x: deactivate; if receiver canonical: bond receiver -sahip-> x ("inherited from {v}")
if any items: not("{n} items of {v} {receiver ? 'passed to ' + receiver : 'were left ownerless; they wait in the grave or on the battlefield'}.", [v, items..., receiver?])
famous = karizma >= DE.unlu_karizma or tag 'seçilmiş' or v has >= 1 active 'oldurdu' bond as killer
# restless spirit
spiritPlace = underworld?.id ?? v.konum_id
spiritsThere = count canonical 'ruh' with konum_id = spiritPlace
if famous and sans(DM.ruh_dogus_sans/100) and spiritsThere < MOTOR.ruh_tavan
   and count('ruh' created this epoch by 'dunya' with alt_tur in ('huzursuz ruh','ata ruhu')) < DE.olum_sonrasi_tavan:
    base = (v was killed: an active 'oldurdu' bond targets v) ? DE.ruh_huzursuz_katil : DE.ruh_huzursuz_dogal
    r = kayitAc({tur:'ruh', alt_tur: base > DE.ruh_huzursuz_sinif ? 'huzursuz ruh' (restless spirit) : 'ata ruhu' (ancestor spirit),
                 ad:"Spirit of {v}", guc: max(DE.ayrilan_guc_taban, v.guc-1), konum_id: spiritPlace,
                 statlar:{guc: clamp((v.guc || DE.kalitim_stat)/DE.ruh_guc_bolen + DE.ruh_guc_ek, 0, 100), huzursuzluk: base + d(DE.ruh_huzursuz_zar)},
                 aciklama:"[World engine] After {v} died, their spirit {underworld ? 'refused to descend to ' + underworld + ' or returned from there' : 'returned from the world'}."})
    bond r -soyundan-> v ("their spirit")
    not("The spirit of {v} found no rest; it wanders {restless ? 'as a restless spirit' : 'among the ancestors'}.", [v, r])
# mourning tradition
if famous and place and sans(DM.yas_ayini_sans/100) and count('gelenek' alt_tur 'yas ayini' created this epoch) < DE.olum_sonrasi_tavan:
    g = kayitAc({tur:'gelenek', alt_tur:'yas ayini' (mourning rite), ad:"Mourning of {adKoku(v.ad, \"'in Varisi\")}", guc: DE.yas_guc,
                 statlar:{yayginlik: DE.yas_yayginlik, katilik (rigidity): DE.yas_katilik},
                 aciklama:"[World engine] After the death of {v}, the people of {place} began to commemorate them every year."})
    bond g -anlatir(depicts)-> v ; if place kind yerlesim|halk: place -kutlar(celebrates)-> g
    not("{place} began a mourning tradition for {v}.", [v, place, g])
```
Note: the restless-ness test `base > DE.ruh_huzursuz_sinif` uses the base before the die is added.

#### `efsaneyiTasiyan(h, legendId, description, cag)` — who carries a hero's legend

`k = location of h`; carrier = k if k's kind in `yerlesim|halk|tarikat|hizip`; else the target of h's latest (`ORDER BY aktif DESC, id DESC`) `yasar` (lives in) or `soyundan` (descends from) bond whose target is one of those kinds. If a carrier is found: bond `carrier -anlatir(tells)-> legend` (description).

### Heroism: hero vs monster encounter (`kahramanlik(h, c, cag, not, context)`)

`context` is a phrase like "while protecting {y}", "in a sworn hunt", "in pursuit of glory" (also passed by `seferler` via helper bag).

```
H = hami(h)                                            # hero's patron son
ph = h.guc + h.ceviklik/KH.ceviklik_bolen + h.akil/KH.akil_bolen + d(KH.zar)*KH.zar_carpan
     + (H ? round(H.karizma/KH.hami_karizma_bolen) : 0) + silahGucu(h, KH.silah_carpan)
     + (h tagged 'büyücü' ? round(h.akil/KH.buyucu_akil_bolen) : 0)
pc = c.guc + c.ceviklik/KH.ceviklik_bolen + c.tehlike/KH.tehlike_bolen + d(KH.zar)*KH.zar_carpan
     + ozellikSavas(c) + (c tagged 'megafauna' ? KH.megafauna_guc : 0)
single = c.guc_seviyesi >= KH.tekil_guc                # a unique monster (high power level) dies on one defeat
(missing stats count as 0)
```
**Hero wins (`ph >= pc`)**:
1. `c.tehlike = clamp(c.tehlike − KH.tehlike_kaybi, 0, 100)`; `death = single or c.tehlike <= KH.olum_tehlike`.
2. Time-rewind: if death and the species has trait `zaman_geri` (`ozellikleri(c)`, yaratik.js) and isn't tagged `geri döndü` (returned): `c.tehlike += KH.geri_sarma_tehlike` (clamp), add tag `geri döndü`, save; `not("{c} died but rewound time; {h} will see it once more.", [c, h])`. Treated as not dead below.
3. else if death: save, `oldur(c.id, cag, "Epoch {cag}: killed by {h}.")` (derin.js: sets durum 'olu', olum_cag, kader_notu). else save.
4. Megafauna slain (death, not rewound, tagged `megafauna`): h's tags: remove any `unvan:*`, add `unvan:{c} Slayer` and `çağ değiştiren` (age-changer); `guc_seviyesi = min(KH.guc_tavan, guc + KH.megafauna_guc_artis)`. Create legend `kayitAc({tur:'efsane', alt_tur:'çağ değiştiren destan' (age-changing epic), ad:"The Fall of {c}", guc: KH.destan_guc, statlar:{yayginlik: KH.destan_yayginlik}, aciklama:"[World engine] {h} slew {c}, as old as the world. This death was the end of an age."})`; bonds legend -anlatir-> h, legend -anlatir-> c; `efsaneyiTasiyan(h, legend, "tells their epic")`; chronicle row directly: `addKronik(cag, null, 'cag_degisimi' (age change), "{h} slew the megafauna {c}. The balance of the world changed; nothing will be the same again.", [h, c, legend])`.
5. `h.karizma += KH.zafer_karizma` (clamp); save. If death and h has no `unvan:` tag: add `unvan:{c} Slayer`.
6. Bond `h -oldurdu-> c` (context) — **created even when the monster only retreated** (smell: 'killed' bond on a non-kill; it also prevents re-hunting via 3.3).
7. If H: `H.un += KH.hami_un` (fame), `H.xp += KH.hami_xp`; saveSon.
8. Best weapon (highest `hasar` among equipment): `kudret += KH.silah_kudret` (clamp); victory counter in tag `zafer:N` incremented; if `N >= KH.efsane_zafer` add tag `efsanevi` (legendary) and `guc_seviyesi = min(KH.guc_tavan, guc+1)` (**applied on every subsequent victory too**, since the condition is `>=`); bond `weapon -oldurdu-> c` ("in the hands of {h}"); if `N == KH.efsane_zafer`: `not("{weapon} became legendary with its second victory.", [weapon, h])` (text hard-codes "second").
9. If death: legend `kayitAc({tur:'efsane', alt_tur:'kahramanlık türküsü' (heroic ballad), ad:"{h} and {c}", guc: KH.turku_guc, statlar:{yayginlik: KH.turku_yayginlik}, aciklama:"[World engine] {h}, {context}, killed {c}. The mortals began to tell of it."})`; bonds legend -anlatir-> h and c; `efsaneyiTasiyan(h, legend, "sings their ballad")`.
10. `not("{h}, {context}, faced {c} and {death ? 'killed it' : 'drove it back'}.", [h, c, legend?], son = H?.id)`.

**Hero loses**:
1. Armor save: `armor` = equipment with highest `koruma`. If `armor.koruma >= KH.zirh_esik` and `sans(KH.zirh_sans_taban/100 + armor.koruma/KH.zirh_sans_bolen)`: `h.can = clamp((h.can || KH.bilinmeyen_can) − KH.zirh_can, 1, SINIR.can_tavan)`; `armor.koruma −= KH.zirh_asinma` (clamp); `savasIlan(c, h, context, cag, {tavan: false})` (a blood feud — enmity through the single war-declaration path, ignoring the war cap); `not("{h} was defeated by {c} but {armor} saved them from death; they withdrew gravely wounded.", [h, c, armor], H?.id)`; return.
2. Else death: `olumluOlur(h, cag, noop, {sebep: "fell before {c}", katil: c})`; if that returned null (e.g. h is immortal/ghost? — note olumluOlur refuses immortals, then this fallback force-kills them via oldur): `oldur(h.id, cag, "Epoch {cag}: fell before {c}.")`, `olumSonrasi(h, cag, not)`, bond `c -oldurdu-> h` (context).
3. Lament: `kayitAc({tur:'efsane', alt_tur:'ağıt' (lament), ad:"Lament for {h}", guc: KH.agit_guc, statlar:{yayginlik: KH.agit_yayginlik}, aciklama:"[World engine] {h}, {context}, gave their life before {c}."})`; bond legend -anlatir-> h; `efsaneyiTasiyan(h, legend, "sings their lament")`.
4. `not("{h}, {context}, fell before {c}.", [h, c, legend], H?.id)`.

### Chronicle writing (`kronikYaz(cag, lines, bas)`)

```
kalip(text, ids):  # skeleton of a line
    names = [nameOf('v', id) for ids if len >= 2] sorted by length desc
    replace each name occurrence with '§'; replace numbers /\d+([.,]\d+)*/ with '#'; collapse whitespace; trim
dup = (bas == null) ? {} : motorTekrarlari(cag, lines, bas)    # kronik-onar.js: lines already written by a sub-engine with its own kind
for s in dup: addKronik(cag, s.ogul, 'motor_ham' (raw engine), s.metin, s.ids)     # kept only in the event ledger
rest = lines not in dup
groups = group rest by kalip(...)
folded = all lines in groups with size >= DM.katlama_esik
for s in rest (in order):
    if s not folded: addKronik(cag, s.ogul, 'dunya' (world), s.metin, s.ids); continue
    if its group already written: continue
    g = group; ids = unique(flatten(g.ids))[: CG.kronik_id_tavan]
    addKronik(cag, g[0].ogul, 'dunya', "{g[0].metin without trailing . or !}; {len(g)-1} more events of the same kind happened this epoch.", ids)
    for x in g: addKronik(cag, x.ogul, 'motor_ham', x.metin, x.ids)
```
Chronicle kinds used: `dunya` (visible world line), `motor_ham` (raw engine ledger line, hidden from main chronicle), `cag_degisimi` (age change). The notes passed to Fate are the raw unfolded `notlar`.

### World snapshot (`dunyaFotografi()`) — for charts and chronicle

Returns `{ nufus: Σ halk.nufus + Σ yerlesim.nufus, murit: Σ tarikat.murit, varlik: #canonical entities, kelime: #rows in sozluk, bilgi: #canonical 'teknoloji' (knowledge), dil: #'dil', savas: #active 'dusman' v-v bonds, ticaret: #'ticaret', ittifak: #'muttefik', yapit: #'yapit', esya: #'esya', olu: #entities with durum 'olu' (any kind), tanrisiz: #canonical tagged 'tanrısız', ogullar: {sonId: {inanc (faith), un (fame), varlik (existence, default DE.varlik_varsayilan), seviye (level)}} }` (sums rounded).

### Carrying capacity

Land carrying capacity is per top region (all communities in the same region share it). Used by the epoch transition's population growth; `tasimaKapasitesi(vId)` exposes the same calculation to the UI.

- `bereketOf(v, place = v.konum_id entity)` (effective fertility): `regionB = ustBolge(v).bereket`. If place is itself a `bolge` or regionB is null → `place.bereket ?? DE.bilinmeyen_bereket`; else `round(placeB × CG.konum_bereket_pay/100 + regionB × (100 − CG.konum_bereket_pay)/100)` (a people living in a cave/sub-place is also fed by its region).
- `kapasiteOf(B, v, bereket)` with `B = {nufus: region population, tarim: population of communities that know 'tarim' (agriculture), halk: list of communities sharing the region, r: region}`:
```
fz = dunyaFizigi(v.dunya_id)                      # world physics: fz.kapasite multiplier
genislik (breadth) = B.r.genislik ?? DE.bilinmeyen_genislik
tarimPay = B.nufus ? B.tarim / B.nufus : 0
mimar = (v is yerlesim and knows 'mimarlik') ? CG.kapasite_mimarlik/100 : 1
cap = fz.kapasite * DM.kapasite
      * (CG.kapasite_bereket_taban/100 + bereket/CG.kapasite_bereket_bolen)
      * (CG.kapasite_genislik_taban/100 + genislik/100)
      * (1 + DM.kapasite_tarim/100 * tarimPay)
      * mimar
      * min(DM.kapasite_kalabalik/100, max(1, sqrt(len(B.halk))))
```
With defaults: 60000 × (0.3 + bereket/60) × (0.5 + genislik/100) × (1 + 1.2·tarimShare) × … × min(1.5, max(1, √n)).
- `tasimaKapasitesi(vId)`: only for `halk|yerlesim`. Region key `b{regionId}` or, for region-less communities, `d{worldId}` (all region-less communities of the same world share). Region totals (communities, total population, agricultural population) are memoized per `kanonSurumu()` (canon version) while the cache is on. Returns `{kapasite: round(cap), bolge_nufus, doluluk (occupancy %) = round(pop/max(1,cap)*100), bolge: {id, ad} | null, paylasan (sharing count)}`.

### Epoch transition (`cagGecisi` / `cagGecisiNefesli`) — runs AFTER Fate

Same transaction/breathing model as the engine (`gecisAdimlari()` generator; `cagGecisi` = one transaction to completion; `cagGecisiNefesli` = `txNefesli(gen, 'çağ geçişi')`; canonical cache on during the run). Returns `notlar` (strings).

```
w = getWorld(); newEpoch = w.cag + 1; newYear = w.yil + CAG_YIL; notlar = []; Y = yasaCozucu()
```

T1 **Laws change the land**: if any world has law `bereket` (fertility) or `kuraklik` (drought): for each canonical `bolge|yer` with `bereket != null` and either law active in its world: `bereket = clamp(bereket + (fertility? CG.yasa_bereket) − (drought? CG.yasa_kuraklik), 0, 100)`.

T2 **Population baselines** (for the population breakdown): `toplamNufus()` = Σ nufus of canonical halk|yerlesim; `oncekiFoto` = `veri` JSON of the latest `cag_istatistik` row with `cag < w.cag`; `nufus0 = toplamNufus()`.

T3 `iklimGecis(newEpoch, notlar)` (derin.js climate cycle) → `yield 'iklimGecis'`; `nufusIklim = toplamNufus()`.

T4 **Population and follower growth** (logistic; carrying capacity per region shared):
```
growing = canonical halk|yerlesim|tarikat
key(v) = top region ? "b{regionId}" : "d{worldId}"
regions[key] = {nufus, murit, halk:[], tarikat:[], tarim, r}   # sums over growing
for v in growing:
    bereket = bereketOf(v, place)
    H = hami(v); mult = (H has power 'bereket') ? CG.bereket_gucu_carpan : 1
    B = regions[key(v)]
    if v is tarikat:
        kar = H?.karizma ?? CG.tarikat_karizma_varsayilan
        r = (DM.tarikat_buyume_taban/100 + (v.etki||0)/DM.tarikat_etki_bolen + kar/DM.tarikat_karizma_bolen) * mult
        K = max(CG.tarikat_kapasite_en_az, B.nufus * MOTOR.tarikat_oran/100)        # cult ceiling = % of region population
        before = v.murit || 1
        rate = r * (1 - B.murit / K)
        new = clamp(before * (1 + max(-CG.tarikat_kucilme_ust/100, min(CG.tarikat_buyume_ust/100, rate))), 1, SINIR.murit_tavan)
        delta = new - before ; v.murit = new ; B.murit += delta
        if delta > 0 and B.nufus > 0:                         # converts are drawn from the region's peoples proportionally
            for h in B.halk: share = delta * h.nufus / B.nufus
                h.nufus = max(h is halk ? SINIR.halk_nufus_taban : SINIR.nufus_taban, round(h.nufus - share)); save h
                (accumulate into nufusTarikat)
    else:
        farming = knows(v,'tarim'); fz = dunyaFizigi(v.dunya_id); K = kapasiteOf(B, v, bereket)
        r = max(DM.buyume_en_az/100,
                DM.buyume_taban/100 + bereket/DM.buyume_bereket_bolen
                + (v is yerlesim ? ((v.refah ?? DE.bilinmeyen_refah) - CG.buyume_refah_esik)/DM.buyume_refah_bolen : 0))
            * (bereket >= CG.bereket_pozitif ? mult : 1)
            * sqrt(fz.zaman)
            * (farming ? DM.buyume_tarim/100 : 1)
            * (law 'olumsuzluk' in v's world ? CG.olumsuzluk_buyume/100 : 1)
            * (law 'kisa_omur' in v's world ? CG.kisa_omur_buyume/100 : 1)
        rate = r * (1 - B.nufus / max(1, K))
        before = v.nufus || SINIR.nufus_taban
        v.nufus = clamp(before * (1 + max(-DM.kucilme_ust/100, min(DM.buyume_ust/100, rate))),
                        halk ? SINIR.halk_nufus_taban : SINIR.nufus_taban,
                        halk ? SINIR.nufus_tavan : SINIR.kent_nufus_tavan)
        B.nufus += v.nufus - before   # sequential: later communities in the region see the updated total
    save v
```
Note: the region total `B.nufus` is updated in iteration order so ordering affects results; famine/war/disaster losses are applied elsewhere; here only what the land can carry.

T5 **Star of the epoch**: among canonical `gok` (celestial bodies), weighted random by `CG.gok_taban_agirlik + parlaklik (brightness)`; fallback first. Then `cagYildizlariSec()` (gok.js) chooses per-world stars; if it returns one for world 1 that replaces the global star. `yield 'adim'`.

T6 **Sons' renewal** (for each son not `olu`):
- `zincirli` (chained) = false.
- if `uykuda` (sleeping): `uyku_kalan -= 1`; at ≤0 → `durum='aktif'`, `uyku_kalan=0`, `can = round(canMax(stats)/CG.uyanis_can_bolen)`, chronicle `sistem`: "{s} woke from their sleep." Else: `can += CG.iyilesme_taban + round(dayaniklilik (endurance)/CG.iyilesme_bolen)` (no cap here — capped elsewhere?).
- `inanc = inancHesapla(s.id)` (world.js, faith from worshippers); `toplamInanc += inanc`.
- `un = floor(un × OZ.un_sonme/100)` (fame decays).
- anchor (`capa_id`, an entity anchoring the son): `capaYasiyor` = no anchor OR anchor canonical/realized. `tapanSay` = number of canonical entities with active `tapar` bond to the son.
- `target = varlikHedefi({inanc, un, capaYasiyor, tapanSay})` (rules.js: `clamp(KURAL.varlik_taban + min(KURAL.varlik_inanc_tavan, inanc/KURAL.varlik_inanc_bolen) + min(KURAL.varlik_un_tavan, un/KURAL.varlik_un_bolen) + (capaYasiyor ? KURAL.varlik_capa : −KURAL.varlik_capasiz) − (tapanSay ? 0 : KURAL.varlik_tapansiz), 0, 100)`).
- `varlik` (existence) moves toward target by at most `CG.varlik_adim`. If the existence state (`varlikDurumu`: ≥`varlik_parlak` "Radiant", ≥`varlik_saglam` "Solid", ≥`varlik_solgun` "Fading", else "Being forgotten") changes: chronicle `varolus` (existence) + note: "{s}'s existence became {state}.[ Because their anchor perished, they began to fade.]"
- essence regen: `regen = RARITIES[rarity].oz_yenilenme + floor(inanc/CG.inanc_oz_bolen) + (power 'oz_pinari' (essence spring) ? CG.oz_pinari) + (state 'parlak' ? CG.parlak_oz) + (the star of the son's current world (dunyaninYildizi) or the global star has a domain (alan) equal to son's alan1/alan2 ? CG.yildiz_alan_oz)`; `oz += (durum == 'surgun' (exiled) ? floor(regen × OZ.surgun_oz/100) : regen)`. saveSon.

T7 `tanrilarinKaderi(newEpoch, notlar)` (derin.js: forgotten gods fade; dead gods may return via resurrection cults) → `yield`.

T8 **Works remember gods**: for each active `anlatir` bond from a canonical `eser` (artwork) or `efsane` (legend) to a son: `un += CG.eser_un`, `varlik = min(100, varlik + CG.eser_varlik)`. (Per bond; no cap.)

T9 **Domain rivalry**: for each pair of non-dead sons sharing `n` domains (alan1/alan2): `il = iliski(a,b)`; if `il > −CG.alan_rekabet_taban`: `iliskiDegistir(a, b, −min(CG.alan_rekabet × n, il + CG.alan_rekabet_taban))` (never pushes below −taban).

T10 **Rebel sons steal essence**: each son with `asi` (rebel) and `aktif`: `c = CG.asi_calma_taban + seviye × CG.asi_calma_seviye`; `s.oz += c`; `calinan += c`; chronicle `isyan`: "Rebel {s} stole {c} from their father's essence."

T11 **Apocalypse clock (kıyamet)**:
```
tanrisiz   = #canonical tagged 'tanrısız'
lanetli    = #canonical tagged 'lanetli'
huzursuzRuh= #canonical 'ruh' with huzursuzluk >= KY.huzursuz_esik
savasSay   = toplulukSavasSayisi()          # derin.js: number of hostile community pairs (mortal rivalries excluded)
asiSay     = #sons asi and not dead
mucizeSay  = #chronicle rows of epoch w.cag with tur='mucize' or text LIKE '%mucizesi indirdi%'   # LANGUAGE-SPECIFIC text match: use an event kind instead
harikaSay  = #canonical 'yapit' tagged 'harika' (wonder)
tapinakSay = #canonical 'yapit' whose "{ad} {alt_tur}" matches /tapınak|mabet|sunak/i (temple|shrine|altar) — LANGUAGE-SPECIFIC; use a structure subtype
yas  = dunyaYasi(newEpoch, notlar)          # derin.js: {altin: #worlds in golden age, donum: age-turning bonus}
kult = kultEtkisi()            # yaratici.js: {kiyamet: clock push-back, oz: essence from the creator's cult}
items = {
  tanrisiz: tanrisiz*KY.tanrisiz, lanetli: lanetli*KY.lanetli, huzursuz_ruh: huzursuzRuh*KY.huzursuz_ruh,
  savas: floor(savasSay/KY.savas_bolen), asi: asiSay*KY.asi,
  mucize: -mucizeSay*KY.mucize, inanc: -min(KY.inanc_tavan, floor(toplamInanc/KY.inanc_bolen)),
  baris: (savasSay == 0 ? -KY.baris : 0), harika: -min(KY.harika_tavan, harikaSay),
  tapinak: -min(KY.tapinak_tavan, floor(tapinakSay/CG.tapinak_bolen)),
  altin_cag: -KY.altin_cag * yas.altin, cag_donumu: -yas.donum, kult: -kult.kiyamet }
kEsik = max(1, DENGE.kiyamet_esik ?? 100)                       # default 100
artis = round(sum(items) * (DENGE.kiyamet_hiz ?? 100)/100)      # 0 stops the clock
clock = clamp(w.kiyamet + artis, 0, kEsik)
crossed(a) = w.kiyamet < a <= clock
if crossed(kEsik*KY.uyari1/100): chronicle 'kiyamet': "Omens fell from the sky: wells turned red, birds flew backwards. Seers whisper that the end of the world is near."
if crossed(kEsik*KY.uyari2/100): chronicle 'kiyamet': "The apocalypse is very near: the stars shifted from their places, the dead spoke in their sleep. If the gods do nothing the world will shatter."
if clock >= kEsik and kiyametCagri(newEpoch):     # korku.js: the apocalypse becomes a call/quest (summons) instead of destruction
    clock = round(kEsik*KY.cagri_sonrasi/100)
elif clock >= kEsik:                              # destruction of ONE world
    target = world with max dunyalar.sizinti (leakage), ties -> more godless entities, then lower id
    regions = canonical 'bolge' in target world
    for r in regions: afetUygula(r, random of ['deprem','sel','kuraklik','firtina'], CG.kiyamet_siddet/100)
    if regions: olayKaydi({tur:'deprem', hedef: regions[0], cag: w.cag, siddet: CG.kiyamet_olay_siddet, ad: null})
    chronicle 'kiyamet' (ids = first CG.kiyamet_kronik_id regions): "APOCALYPSE: {target or world name} was shaken. All its regions were destroyed by disasters; the survivors awoke to a new age."
    clock = round(kEsik*KY.yikim_sonrasi/100)
UPDATE dunya SET kiyamet = clock
```

T12 **Creator's essence (tanrı özü)** with soft cap:
```
ozNow = fresh dunya.tanri_oz (may have changed during transition)
income = DENGE.tanri_oz_yenilenme + floor(toplamInanc / CG.inanc_oz_bolen)       # DENGE default 20
cap = DENGE.oz_tavan                                                            # default 800
tasan = 0; halved = 0
if ozNow > cap:
    keep = floor(income * OZ.tavan_gelir/100); halved = income - keep; income = keep
    tasan = ceil((ozNow - cap) * OZ.tasma/100)
tanriOz = max(0, ozNow + income - tasan - calinan - tanrisiz*OZ.tanrisiz_kemirme) + kult.oz   # cult essence bypasses the cap
if tasan > 0: tasanOzuDagit(tasan); if tasan >= CG.oz_tasma_not: notlar.push("{tasan} units of the Creator's overflowing essence seeped into the world; the most barren lands grew fertile.")
```

T13 **Epoch statistics**: `dokum` (breakdown) with three lists of `{kalem (item label), d (rounded delta)}` (zero items dropped):
- `kiyamet`: labels godless communities, cursed, restless spirits, wars, rebel sons, miracles, faith, age of peace, wonders, temples, golden age, age turning / world age, creator's cult, + "apocalypse speed (world rules)" (difference due to `kiyamet_hiz` ≠ 100) + "post-apocalypse reset" (difference due to reset).
- `sizinti` (leakage): per world `{dunya, dunya_id, kalemler: sizintiDokumu.get(id) || []}` (korku.js).
- `nufus` (population): "war, disasters, migration and births (engine)" = `nufus0 − oncekiFoto.nufus` (if previous snapshot), "climate" = `nufusIklim − nufus0`, "logistic growth" = nufusBuyume, "joined cults" = nufusTarikat.
- `oz`: creator's own regen, sons' faith, income halved above the cap (−), overflowing essence (−), stolen by rebel sons (−), gnawed by the godless (−), creator's cult.
Upsert `cag_istatistik(cag = w.cag, veri = JSON({...dunyaFotografi(), kiyamet: clock, dokum}))`. Then `cagFotografiAl(w.cag)` (kesif.js, errors swallowed) → `yield`.

T14 **Advance**: `UPDATE dunya SET cag=newEpoch, yil=newYear, tanri_oz=tanriOz, cagin_yildizi=star.id`; chronicle `sistem` for newEpoch: "Epoch {newEpoch} began (world year {newYear}).[ Star of the epoch: {star}.]" → `yield`.

T15 Post-steps, each wrapped in try/catch (errors swallowed) and followed by `yield`: `yaraticininCagi(w.cag, newEpoch, notlar)` (yaratici.js: creator's mood and spontaneous signs; after essence update so the cult's faith is included), `tanriGucununCagi(w.cag, newEpoch, notlar)` (tanriguc.js: divine power), `itibarCagi(notlar)` (itibar.js: reputation), `hedefCagi(notlar)` (hedef.js: goals), `ekleriDoldur()` (world.js: LANGUAGE-SPECIFIC fills Turkish suffix forms of names — drop), `kesinGercekler(ids of entities created in epoch w.cag with durum in kanon|olu|gerceklesti, w.cag)` (gercek.js: lock "certain facts").

Return `notlar`.

### Cross-module call map (who calls sim.js exports)

| Export | Used for |
|---|---|
| `dunyaMotoru`, `dunyaMotoruNefesli` | epoch.js: end-of-epoch engine before Fate |
| `cagGecisi`, `cagGecisiNefesli` | epoch.js: after Fate |
| `olumluOlur`, `olumluYarala`, `olumSonrasi` | olumluler.js tools, derin.js (`olumYolu`), Fate tools — the single named-mortal death path |
| `etkinOmur`, `onemliOlumlu`, `olumsuzMu` | UI age/lifespan display, derin.js |
| `yasTutarliligi` | startup repair |
| `tasimaKapasitesi` | UI and ufuk.js exploration |
| `dunyaFotografi` | statistics |
| `refahKazanci`, `refahEkle` | every prosperity gain in the codebase |
| `tasanOzuDagit` | creator essence overflow (also elsewhere) |

Imports used by sim.js: `ustBolge`, `ustBolgeId`, `yakinMi` (olumluler.js); `yasaCozucu`, `bilir`, `bildikleri`, `ogret`, `afetUygula`, `olayKaydi`, `mucizeUygula` (mudahale.js); `haritaHesapla` (harita.js); `dildenAd` (dilmotoru.js); `ekDuzelt`, `yonetimUnvani`, `toplulukIci` (public/dil.js); many derin.js engines listed above.

### Peoples, settlements, notables and rulers spawning (derin.js functions called by the tick)

These live in `src/derin.js` and are called from Phase 0/5/6 above. They are summarized here because they are the core "world fills itself" mechanics; tunables are `DERIN.*`, `DERIN_YASAM.*` (alias `DK` in derin.js), `DERIN_TOPLUM.*` (alias `TOPLUM_K`), `BOS.*` (empty-world guarantees) — their full tables belong to the derin.js spec.

#### `dilVeInancBagla(v, cag, not, {kaynak = null})` — first language and first faith

1. Skip if v is not alive/canonical.
2. Language, if v speaks none: `L = kaynak's language` (source community, e.g. the settlement migrants came from) `|| enYakinDil(v)`. If no canonical L: `L = ilkelDil(v, cag)` (new primitive language). Bond `v -konusur-> L` (description "first sounds" if new, else "nearest language"); if new: `not("{v} began to speak its own primitive language.", [v, L])`.
   - `enYakinDil(v)` (nearest language), in order: (a) language of v's location if that location is a living community (`halk|yerlesim|hizip|tarikat`); (b) language of any entity v descends from (`soyundan` targets, any status bond); (c) weighted vote over all other communities in the same world speaking a canonical language: weight `DK.dil_bolge_agirlik` if in v's top region else 1; highest weight wins, tie → lower language id.
   - `ilkelDil(v, cag)`: root = first word of v's name. `kayitAc({tur:'dil', alt_tur:'ilkel dil' (primitive language), ad:"{root} Language", guc:1, konum_id: v.konum_id, statlar:{yayginlik: DK.ilkel_yayginlik, karmasiklik: DK.ilkel_karmasiklik, kutsallik: DK.ilkel_kutsallik}, etiketler:['ilkel'], aciklama:"[World engine] A language among {v}, learned from no one, born of signs and first sounds."})`; set its `dunya_id` = v's world. Seed 8 vocabulary words for meanings `ILK_SOZLER = water, fire, earth, mother, sky, road, dead, bread` (Turkish `su, ateş, toprak, ana, gök, yol, ölü, ekmek`): word i = `adUret(L, "ilk:{i}", 'genel')` (dilmotoru.js) or fallback `syllables(root)[i % n] + ['a','u','en','ir','o','el','um','is'][i]`; inserted lowercased into `sozluk` with `tur='isim'` (noun), `koken='ilk sesler'` (first sounds), added by v.
3. Faith: if v already has an active outgoing `tapar` bond → done. `inherited = hami(kaynak)` if kaynak's patron is not dead. If no inheritance and `!sans(DK.ilk_inanc_sans/100)` → done (v stays without faith this tick; it may become godless later). `h = inherited || ilkInancTanrisi(v)`; if h: bond `v -tapar-> son h` ("first faith"); done.
   - `ilkInancTanrisi(v)`: weighted random over sons: for each other community in the same world with a living patron, add weight `DK.tanri_bolge_agirlik` (same top region) or 1 to that patron; transform `w = n^(DK.ilk_inanc_us/100)` (diminishing); every active son whose `aktif_dunya` is this world gets `+DK.ilk_inanc_ogul`; candidates sorted by son id; roulette. Fallback: the world's `koruyucu_ogul` (protector son) or the first active son in that world.
4. If no god found: with `DERIN.yaratici_ilk_inanc`% → `yaraticiyaTapin(v, 'first faith', cag)` (yaratici.js: worship the Creator directly) and `not("{v} began praying directly to the creator in the sky.")`; else tag `tanrı arayışı` (seeking a god) and `not("{v} is looking for a god; they wait for someone to hear their prayers.")`.

#### `harabeyeKur(region, source, population, cag, reason)` — refound a ruin

Find a dead settlement tagged `harabe` (ruin) and not `boşluk` (void) in the region's world whose location is the region or a direct child of it; newest `olum_cag` first. If found: restore `durum='kanon'`, `olum_cag=NULL`, `alt_tur` = the original subtype parsed from `"harabe (eski X)"` (ruin (former X)) or 'köy' (village); stats `nufus = max(DK.harabe_nufus_alt, round(population))`, `refah = DK.harabe_refah`, `savunma = max(DK.harabe_savunma_alt, round((savunma ?? DK.harabe_savunma_yedek)/DK.harabe_savunma_bolen))`; append fate note "Epoch {cag}: {reason} rebuilt the ruin."; remove tag `harabe`, add `yeniden kuruldu` (refounded); bond `ruin -soyundan-> source` ("those who rebuilt the ruin"); … returns id (null if none).

#### `dogumlar(cag, not)` — notables, rulers, villages, ethnogenesis, uplifted species

Runs `tekYonetim()` first (single-ruler invariant: if a community `yerlesim|halk|hizip|tarikat` has active `yonetir` bonds from >1 canonical sources, keep the newest one whose description isn't `'yurdu'` (homeland) — else the newest — and close the others; a closed `'yurdu'` bond is converted to `yasar` (lives in) instead).

(a) **Notables** (`unlu`): `cap = clamp(ceil(#halk|yerlesim × DK.unlu_oran/100), DK.unlu_alt, DERIN.unlu_tavan)`. Iterate communities in random order: require `nufus >= DERIN.unlu_nufus`; `living` = # living `olumlu` descending (`soyundan`) from t; skip if `living >= DK.unlu_yasayan_taban + floor(log10(n))`; chance `DERIN.unlu_sans/100 + min(DK.unlu_kalabalik_ust/100, log10(n)/DK.unlu_kalabalik_bolen)`. Pick a social class by roulette over `toplumOf(t).k` (class shares: ciftci farmers, zanaatkar artisans, tuccar merchants, rahip priests, savasci warriors, katip scribes); pick one role uniformly from `ROLLER[class]`:

| class | roles (title suffix → subtype; boosted stats) |
|---|---|
| farmers | Leader → people's leader (guc, karizma); Shepherd → shepherd (ceviklik, guc); Midwife → midwife (akil, karizma) |
| artisans | Master → master artisan (akil, ceviklik); Smith → smith (guc); Architect → architect (akil) |
| merchants | Merchant → merchant (akil, karizma); Caravaneer → caravaneer (ceviklik, guc); Money-changer → money-changer (akil) |
| priests | Seer → seer (akil, karizma); Healer → healer (akil, karizma); Bard → bard (karizma) |
| warriors | Warrior → hero (guc, ceviklik); Hunter → hunter (ceviklik, guc); Guardian → guardian warrior (guc, karizma) |
| scribes | Sage → sage (akil); Historian → historian (akil, karizma); Cartographer → cartographer (akil, ceviklik) |

Stat boosts come from tunables `DK.rol_{class}_{role}_{stat}`. Create via `olumluDogur(t, {ad: "{t} {RoleTitle}", alt_tur, st: boosts, omurEk: warriors ? DK.unlu_savasci_omur : 0, aciklama: "[World engine] From among {t}'s {class plural} rose a renowned {subtype}."})`; `not("From among {t}'s {class} rose a renowned {subtype}: {name}.")`.

`olumluDogur(t, {ad, alt_tur, st, cag, aciklama, etiketler, omurEk})` (engine-born mortal): stat `s(k) = clamp(DK.dogum_stat_taban + (st[k]||0) + d(DK.dogum_stat_zar), 0, 100)` for guc/ceviklik/akil/karizma; name = `kisiAdi([t], "{t.id}:{cag}:{alt_tur}:{random}", t.dunya_id)` — if found, the role name becomes the title (`unvan`), description prefixed with the name, tag `dilden-ad`; `omur = DK.dogum_omur + d(DK.dogum_omur_zar) + omurEk`; `yas = round(omur × (DK.dogum_yas_alt/100 + random × DK.dogum_yas_aralik/100))`; `guc_seviyesi = clamp(round(t.guc × DK.dogum_guc_pay/100) + 1, 1, DK.dogum_guc_ust)`; `can = DK.dogum_can`; location = t if settlement else t.konum_id. Bonds: `-soyundan-> t`, `-korur(protects)-> t`, `-tapar-> hami(t)`, `-konusur-> lang(t)`.

(b) **Rulers**: for canonical `halk|yerlesim|hizip|tarikat` with `(nufus || murit) >= DERIN.hukumdar_nufus` OR any `hizip`; cap `DERIN.hukumdar_tavan`; skip if `yoneticiVar(t)` (already ruled by a canonical entity) or `!sans(DERIN.hukumdar_sans/100)`. Subtype: cult → `başrahip` (high priest), faction → `lider` (leader), people → `reis` (chief), settlement → `hükümdar` (sovereign). `olumluDogur(t, {ad:"{t} {High Priest|Leader|Chief|Sovereign}", st:{karizma: DK.hukumdar_karizma, akil: DK.hukumdar_akil}, omurEk: DK.hukumdar_omur, etiketler:['yönetici'], aciklama:"[World engine] took the head of {t} as {subtype}."})`; bond `ruler -yonetir-> t` ("took the throne"); `not("{name} became {subtype} of {t}.")`.

(c) **New villages**: for canonical `halk` with `nufus >= DERIN.koy_ilk_nufus`, cap `DK.koy_tavan`: r = top region (required). `existing` = settlements in r that descend from h or speak h's language. If existing and `nufus < DERIN.koy_ek_nufus` skip; skip if `existing >= ceil(nufus/DERIN.koy_basina)` or `!sans(existing ? DK.koy_ek_sans : DK.koy_ilk_sans)`. `goc = min(max(DERIN.koy_en_az, round(nufus × DK.koy_goc_pay/100)), max(0, nufus − DERIN.koy_kalan))`; skip if `< DERIN.koy_en_az`; `h.nufus -= goc`. Try `harabeyeKur(r, h, goc, cag, "as {h} grew crowded")` — if a ruin is refounded: bond `h -yonetir-> ruin` ("homeland of its own people") unless already ruled; note "{h} grew crowded; settled in the ruin of {x} and rebuilt it." Else name `dildenAd(h, "{h.id}:{cag}:koy:{existing}", 'yer')`; `kayitAc({tur:'yerlesim', alt_tur: existing ? 'köy' (village) : 'ana yurt' (homeland), ad: name || "{h} {Village|Homeland}", guc: max(DK.turev_guc_alt, h.guc−1), konum_id: h.konum_id, statlar:{nufus: goc, refah: DK.koy_refah, savunma: DK.koy_savunma, inanc: h.inanc ?? TOPLUM_K.stat_varsayilan}, aciklama:"[World engine] {h} grew crowded; {goc} people founded a new settlement within {r}."})`; bonds `y -soyundan-> h`, `h -yonetir-> y` ("homeland of its own people"), `y -konusur-> lang(h)`, `y -tapar-> hami(h)`; note "{h} grew crowded; founded a new settlement within {r}."

(d) **Ethnogenesis** (new people from a settlement), cap `DK.yeni_halk_tavan` shared with (e): for canonical settlements with age `>= DERIN.etnogenez_cag` epochs and `nufus >= DERIN.etnogenez_nufus`: ancestor A = target of the first active `soyundan` bond; require A is `halk|yerlesim` in a DIFFERENT top region; skip if this settlement already birthed a people (`kavimDogurdu`) or `!sans(DERIN.etnogenez_sans/100)`. Name `dildenAd(y, "{y.id}:{cag}:halk", 'halk')`; `split = round(y.nufus × min(100, DK.etnogenez_nufus_pay)/100)`; create `halk` (alt_tur 'yeni kavim' new tribe, name or "{y} People", at region, stats `nufus: split, savascilik: DK.etno_stat_taban + d(DK.etno_stat_zar), buyu: d(DK.etno_buyu_zar), zanaat: DK.etno_stat_taban + d(DK.etno_stat_zar), inanc: y.inanc ?? default`); `y.nufus −= split` (clamp); bonds `people -soyundan-> A` ("divergence"), `y -soyundan-> people`, `people -yasar-> y` ("homeland"), language and patron of y; `dilVeInancBagla(people, cag, not, {kaynak: y})`; note "From the line of {A}, {y} turned over generations into a separate people."

(e) **Uplifted species**: canonical `tur` with `zeka >= DK.akillanma_zeka` and not tagged `halk oldu` (became a people), chance `DERIN.akillanma_sans`: create `halk` (alt_tur 'akıllanan tür' (uplifted species), "{t} Lineage", at its region or its first `yasar` home; stats `nufus: DK.akil_nufus + d(DK.akil_nufus_zar)`, `savascilik: clamp((t.guc || DK.akil_guc_yedek) + d(DK.akil_savas_zar))`, `buyu: d(DK.akil_buyu_zar)`, `zanaat: d(DK.akil_zanaat_zar)`, `inanc: DK.akil_inanc + d(DK.akil_inanc_zar)`); bond `-soyundan-> t` ("uplift"); tag species `halk oldu`; if the species has a creator son: `people -tapar-> creator` ("to its creator"); `dilVeInancBagla`; note "A branch that learned to speak arose among {t}; now a people named {x}."

#### `yasamTohumu(cag, not)` — seed of life (spontaneous peoples and species in empty worlds)

For each world not `kesif='unutulmus'` (forgotten):
- fertile regions = canonical `bolge` in that world with `bereket (?? default) >= DK.yasam_bereket`; none → skip. `pick()` = random among the top `DK.yasam_bolge_secim` most fertile.
- `emptyFor` = epochs this world has been empty (`bosDunyalar(cag)`, bosdunya.js).
- If the world has no `halk` and (`sans(DERIN.yerli_halk_sans/100)` or (`BOS.yerli_guvence` and `emptyFor >= BOS.yerli_guvence`) — a guarantee after N empty epochs): create `halk` `alt_tur:'yerli halk'` (native people), name "{region} Natives", tag `yerli`, `guc: DK.yerli_halk_guc`, stats `nufus: DK.yerli_halk_nufus + d(..zar)`, `savascilik/buyu/zanaat: DK.yerli_halk_stat + d(DK.yerli_halk_stat_zar)` (each rolled), `inanc: DK.yerli_halk_inanc + d(..zar)`; description "[World engine] In {world}, in the lands of {region}, a people appeared whom no one created: they were born of the earth itself, of the long patience of water and light."; note "A people appeared spontaneously in {world} ({region})."; then `dilVeInancBagla`.
- If the world has no `tur` and `sans(DERIN.yerli_tur_sans/100)`: create `tur` `alt_tur:'yerli canlı'` (native creature), "{region} Creatures", tag `yerli`, `guc: DK.yerli_tur_guc`, stats can/guc/ceviklik/zeka/tehlike = `DK.yerli_tur_X + d(DK.yerli_tur_X_zar)`; note "The first living species appeared in {world}."

### Known bugs and design smells in sim.js (and how the rewrite should avoid them)

1. **Non-determinism.** Comments claim `Math.random` is seeded so the engine is deterministic, but `Math.random` is only replaced in tests (`test/yardim.js`). Production runs are non-reproducible. → Use an explicit per-epoch seeded PRNG (e.g. seeded from world id + epoch) passed through every phase; never call the global RNG.
2. **Two notions of distance.** `mesafe()` counts steps in the containment tree (`konum_id` chain); `yakinMi()`/Voronoi `komsular` use map adjacency. Raids, hunts and divine grudges use the former, migration/famine the latter. → Define one spatial model (region graph distance) and use it everywhere.
3. **Region-less entities compare as "same region".** `ustBolge(a)?.id !== ustBolge(b)?.id` is false when both are undefined (barter/rivalry 4.5, dialect homeland check 5.20, hauntings 5.11, wizard home). `ayniBolge()` in olumluler.js fixes this for tools but sim.js doesn't use it. → Treat "unknown region" as never equal.
4. **'Killed' bond on a non-kill.** In `kahramanlik`, the hero gets an `oldurdu` bond to the monster even when it only retreated; this also blocks future glory hunts against it.
5. **Legendary weapon level creep.** After `efsane_zafer` victories every further victory adds +1 power level (capped by `guc_tavan`); the note text hard-codes "second victory".
6. **Wizard fertility spell reported as protective** (5.14).
7. **Inconsistent defaults.** Uprising uses `bilinmeyen_stat` (30) as the default prosperity while everything else uses `bilinmeyen_refah` (50).
8. **Unbounded / O(n²) loops.** Love/rivalry (5.19) has no cap and pairs all adult mortals at the same location (also pairs mortals with `konum_id = null`); kin and barter loops are O(n²) over communities. Births treat `muttefik` (ally) bonds between mortals as couples.
9. **No cooldowns** for creature rebellion (5.15): a qualifying species can drain its creator's `varlik` and its worshippers every tick.
10. **Walls only go up.** Raids (+), just laws (+), architecture (+) raise `savunma` every epoch; only uprisings/curses lower it → most settlements converge on 100.
11. **Stale snapshot.** `vs` (taken in phase 0) is reused in phase 3 after many sub-engines ran; code compensates with fresh `getVarlik` checks. → Re-query per phase or use an identity map with status checks.
12. **Language-dependent logic in rules**: miracle counting by chronicle text `LIKE '%mucizesi indirdi%'`, temples by name regex, underworld by name regex (`OBUR_DUNYA_DESEN`), important mortals by subtype regex, derived-name stripping with Turkish possessive suffixes (`'in Varisi`). → Replace with explicit flags/enums (event kind `miracle`, structure subtype `temple`, region flag `underworld`, mortal role enum, separate `base_name` + `generation` fields).
13. **Fallback heir names**: comment says "X II" but code returns the bare root and relies on the uniquifier. → Store dynasty name + regnal number explicitly.
14. **Text concatenation of reasons** (`"{name} {sebep}"`) assumes Turkish verb-final phrasing; English needs full-sentence templates.
15. **Errors swallowed** in epoch-transition post-steps (`try {…} catch {}`) hide failures. → Log and surface them.
16. **Kıyamet "peace" item** uses `toplulukSavasSayisi()` computed twice (`savasSay` and `toplulukSavas`) — harmless duplication.
17. Sons' HP regeneration in the transition (`can += …`) has no explicit cap here (presumably capped on read via `canMax`); verify in the gods spec.

## 2. Tunables of the world engine (sim.js)

Percentages are stored as integers (e.g. 30 → 0.30 probability); "die (1–X)" means `d(X)` = a uniform integer 1..X; "/ this number" means the stat is divided by the tunable value; an "age" is one world era (çağ), and "per age" means once per era tick.

### Apocalypse clock (`KIYAMET`; local alias `KY`)
Items of the apocalypse clock (threshold and speed live in `DENGE.kiyamet_esik` / `DENGE.kiyamet_hiz`).

| key | original key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| godless_people | tanrisiz | 2 | 0 | 50 | Apocalypse | Each godless community advances the clock |
| cursed_entity | lanetli | 1 | 0 | 50 | Apocalypse | Each cursed entity advances the clock |
| restless_spirit | huzursuz_ruh | 2 | 0 | 50 | Apocalypse | Each restless spirit advances the clock |
| restless_threshold | huzursuz_esik | 60 | 0 | 100 | Apocalypse | Restlessness at which a spirit counts as restless |
| war_divisor | savas_bolen | 2 | 1 | 100 | Apocalypse | Every this many hostility bonds advance the clock by 1 |
| rebel_son | asi | 4 | 0 | 50 | Apocalypse | Each rebel son advances the clock |
| miracle | mucize | 3 | 0 | 50 | Apocalypse | Each miracle pushes the clock back |
| faith_divisor | inanc_bolen | 40 | 1 | 10000 | Apocalypse | Every this much faith pushes the clock back by 1 |
| faith_cap | inanc_tavan | 4 | 0 | 100 | Apocalypse | Most that faith can push the clock back in one age |
| peace | baris | 2 | 0 | 50 | Apocalypse | An age with no war at all pushes the clock back |
| wonder_cap | harika_tavan | 3 | 0 | 50 | Apocalypse | Most that wonders can push the clock back (1 per wonder) |
| temple_cap | tapinak_tavan | 2 | 0 | 50 | Apocalypse | Most that temples can push the clock back (1 per two temples) |
| golden_age | altin_cag | 3 | 0 | 50 | Apocalypse | Each world in a golden age pushes the clock back |
| warning1 | uyari1 | 50 | 1 | 100 | Apocalypse | Point at which the first omen arrives (% of the threshold) |
| warning2 | uyari2 | 80 | 1 | 100 | Apocalypse | Point at which the final warning arrives (% of the threshold) |
| after_summons | cagri_sonrasi | 60 | 0 | 100 | Apocalypse | Where the clock drops to when the apocalypse turns into a summons (% of the threshold) |
| after_destruction | yikim_sonrasi | 40 | 0 | 100 | Apocalypse | Where the clock drops to after the apocalypse destroys (% of the threshold) |

### Essence (`OZ`; local alias `OZ`)

| key | original key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| overflow | tasma | 8 | 0 | 100 | Creator and essence | Share of essence above the cap that overflows into the world each age (%) |
| overflow_fertility | tasma_bereket | 10 | 1 | 1000 | Creator and essence | Every this much overflowing essence gives regions 1 fertility in total (shared out starting from the most barren region) |
| overflow_fertility_max | tasma_bereket_ust | 70 | 0 | 100 | Creator and essence | Overflowing essence does not raise a region's fertility above this |
| godless_erosion | tanrisiz_kemirme | 3 | 0 | 100 | Creator and essence | Essence each godless community gnaws away per age |
| fame_decay | un_sonme | 95 | 0 | 100 | Creator and essence | Share of a son's fame retained per age (%) |
| over_cap_income | tavan_gelir | 50 | 0 | 100 | Creator and essence | Share of the creator's per-age income kept while above the essence cap (DENGE.oz_tavan) (%) |
| exile_essence | surgun_oz | 0 | 0 | 100 | Creator and essence | Ratio of an exiled son's per-age essence regeneration to normal regeneration (%) |

### World engine (`DUNYA_MOTORU`; local alias `DM`)

| key | original key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| fold_threshold | katlama_esik | 3 | 2 | 100 | Chronicle | This many chronicle lines of the same pattern are folded into a single line |
| raid_divisor | baskin_bolen | 160 | 10 | 10000 | Creatures | Monster raid probability: danger / this number |
| raid_loss_divisor | baskin_kayip_bolen | 400 | 10 | 10000 | Creatures | Population lost in a raid: danger / this number |
| monster_percentile | canavar_yuzde | 80 | 0 | 100 | Creatures | Species counted as monsters: those above the world's X-th percentile of danger |
| monster_min | canavar_alt | 40 | 0 | 100 | Creatures | Minimum danger to count as a monster |
| monster_max | canavar_ust | 55 | 0 | 100 | Creatures | A species at this danger is always a monster |
| hunt_chance | av_sans | 30 | 0 | 100 | Heroes and mortals | A strong mortal hunts a monster in pursuit of fame (%) |
| hunt_chosen_chance | av_secilmis_sans | 50 | 0 | 100 | Heroes and mortals | A chosen mortal hunts a monster (%) |
| hunt_power | av_guc | 90 | 0 | 200 | Heroes and mortals | Strength + agility total for a mortal to count as a hunter |
| curse_lift | lanet_kalkma | 12 | 0 | 100 | Heroes and mortals | A curse lifts on its own (%) |
| curse_hp | lanet_can | 10 | 0 | 1000 | Heroes and mortals | HP a cursed mortal loses each age (if it runs out the curse kills them; 0 = off) |
| curse_magic_bonus | lanet_buyu_ek | 15 | 0 | 100 | Heroes and mortals | Contribution of knowing magic to escaping a curse (%) |
| curse_medicine_bonus | lanet_tip_ek | 10 | 0 | 100 | Heroes and mortals | Contribution of knowing medicine to escaping a curse (%) |
| schism_zealot_chance | bolunme_bagnaz_sans | 22 | 0 | 100 | Religion and language | A zealous cult splits (%) |
| schism_large_chance | bolunme_buyuk_sans | 10 | 0 | 100 | Religion and language | A large, old cult splits over a doctrinal dispute (%) |
| schism_zealotry | bolunme_bagnazlik | 60 | 0 | 100 | Religion and language | Zealotry at which a cult counts as zealous |
| schism_min | bolunme_alt | 400 | 0 | 1000000 | Religion and language | Minimum followers of a cult that can split |
| schism_large | bolunme_buyuk | 800 | 0 | 1000000 | Religion and language | Followers required for a non-zealous cult to split |
| schism_share | bolunme_pay | 30 | 0 | 100 | Religion and language | Share of followers who leave in a schism (%) |
| hero_chance | kahraman_sans | 12 | 0 | 100 | Heroes and mortals | A hero is born from a populous people (%) |
| hero_war_bonus | kahraman_savas_ek | 15 | 0 | 100 | Heroes and mortals | Added chance of a hero being born from a people at war (%) |
| hero_min_pop | kahraman_alt | 1500 | 0 | 1000000 | Heroes and mortals | Minimum population of a community that produces heroes |
| knowledge_spread_chance | bilgi_yayilim_sans | 18 | 0 | 100 | Religion and language | Knowledge spreads along trade and governance bonds (%) |
| disaster_cap | afet_tavan | 2 | 0 | 20 | Population and growth | Most natural events per age |
| earthquake_chance | deprem_sans | 8 | 0 | 100 | Population and growth | Earthquake in a mountainous region (%) |
| flood_chance | sel_sans | 6 | 0 | 100 | Population and growth | Flood on the coast (%) |
| storm_chance | firtina_sans | 6 | 0 | 100 | Population and growth | Storm on the coast (%) |
| drought_chance | kuraklik_sans | 10 | 0 | 100 | Population and growth | Drought in a barren region (%) |
| region_plague_pop | bolge_veba_nufus | 3000 | 0 | 10000000 | Population and growth | Region population at which plague can occur as a natural event |
| region_plague_chance | bolge_veba_sans | 6 | 0 | 100 | Population and growth | Plague in a populous region (%) |
| city_plague_min | kent_veba_alt | 3000 | 0 | 10000000 | Population and growth | Minimum crowding for a city plague |
| city_plague_chance | kent_veba_sans | 10 | 0 | 100 | Population and growth | Plague in a crowded city (%) |
| hungry_plague_chance | ac_veba_sans | 12 | 0 | 100 | Population and growth | Plague in a starving city (%) |
| war_plague_chance | savas_veba_sans | 8 | 0 | 100 | Population and growth | Plague in a city at war (%) |
| plague_spread_chance | veba_yayilim_sans | 35 | 0 | 100 | Population and growth | Epidemic jumps along bonds to a neighbour (%) |
| plague_spread_medicine_chance | veba_yayilim_tip_sans | 18 | 0 | 100 | Population and growth | Epidemic jumps to one who knows medicine (%) |
| revolt_chance | isyan_sans | 22 | 0 | 100 | War and diplomacy | Uprising in a poor city (%) |
| revolt_just_chance | isyan_adil_sans | 8 | 0 | 100 | War and diplomacy | Uprising in a city with just laws (%) |
| revolt_prosperity | isyan_refah | 30 | 0 | 100 | War and diplomacy | A city below this prosperity can rise up |
| revolt_min_pop | isyan_alt | 600 | 0 | 1000000 | War and diplomacy | Minimum population of a rebelling city |
| first_age_engine | ilk_cag_motor | 15 | 0 | 50 | Heroes and mortals | Years an engine-born mortal lives within the age of its birth |
| first_age_son | ilk_cag_ogul | 35 | 0 | 50 | Heroes and mortals | Years a son-created mortal lives within the age of its creation |
| notable_lifespan | onemli_omur | 15 | 0 | 500 | Heroes and mortals | Extra lifespan of notable mortals (years) |
| medicine_lifespan | tip_omur | 20 | 0 | 500 | Heroes and mortals | Extra lifespan in a region that knows medicine (years) |
| growth_base | buyume_taban | 6 | 0 | 100 | Population and growth | Base of population growth (% per age) |
| growth_min | buyume_en_az | 3 | 0 | 100 | Population and growth | Minimum rate of population growth (%) |
| growth_fertility_divisor | buyume_bereket_bolen | 600 | 10 | 100000 | Population and growth | Fertility contribution to growth: fertility / this number |
| growth_prosperity_divisor | buyume_refah_bolen | 400 | 10 | 100000 | Population and growth | Prosperity contribution to growth in a city: (prosperity − 40) / this number |
| growth_agriculture | buyume_tarim | 140 | 0 | 1000 | Population and growth | Growth multiplier for those who know agriculture (%) |
| growth_max | buyume_ust | 60 | 0 | 1000 | Population and growth | Maximum growth in one age (%) |
| shrink_max | kucilme_ust | 25 | 0 | 100 | Population and growth | Maximum shrinkage in one age (%) |
| capacity | kapasite | 60000 | 100 | 100000000 | Population and growth | Base carrying capacity of a region (people) |
| capacity_agriculture | kapasite_tarim | 120 | 0 | 1000 | Population and growth | Contribution of agriculture to capacity (scaled by the share who know agriculture, %) |
| capacity_crowded | kapasite_kalabalik | 150 | 100 | 1000 | Population and growth | Capacity ceiling of a region with many communities (%) |
| cult_growth_base | tarikat_buyume_taban | 5 | 0 | 100 | Population and growth | Base of cult growth (%) |
| cult_influence_divisor | tarikat_etki_bolen | 400 | 10 | 100000 | Population and growth | Influence contribution to cult growth: influence / this number |
| cult_charisma_divisor | tarikat_karizma_bolen | 500 | 10 | 100000 | Population and growth | Patron's charisma contribution to cult growth: charisma / this number |
| grudge_chance | kin_sans | 30 | 0 | 100 | War and diplomacy | The gods' grudge seeps down to mortals (% per pair) |
| rivalry_chance | rekabet_sans | 15 | 0 | 100 | War and diplomacy | Rivalry war over the same resource (%) |
| barter_chance | takas_sans | 30 | 0 | 100 | Economy | Resource barter between neighbours begins (%) |
| curse_contagion_chance | lanet_bulas_sans | 25 | 0 | 100 | Heroes and mortals | A cursed item infects its owner (%) |
| magic_storm_chance | buyu_firtina_sans | 8 | 0 | 100 | Cosmic horror | Magic storm in a magic-dense region (%) |
| magic_storm_curse | buyu_firtina_lanet | 30 | 0 | 100 | Cosmic horror | An item is cursed in a magic storm (%) |
| creature_migration_chance | yaratik_goc_sans | 15 | 0 | 100 | Creatures | A dangerous species migrates to a neighbouring region (%) |
| language_spread_chance | dil_yayilim_sans | 20 | 0 | 100 | Religion and language | Under the one-language law, language spreads along bonds (%) |
| famine_migration_chance | kitlik_goc_sans | 25 | 0 | 100 | Population and growth | Famine migration (%) |
| spirit_haunt_chance | ruh_musallat_sans | 30 | 0 | 100 | Beyond (afterlife) | A restless spirit haunts a settlement (%) |
| coin_chance | sikke_sans | 25 | 0 | 100 | Economy | A wealthy community mints coins (%) |
| currency_adopt_chance | para_benimse_sans | 30 | 0 | 100 | Economy | A trade partner adopts the currency (%) |
| mage_action_chance | buyucu_eylem_sans | 30 | 0 | 100 | Heroes and mortals | A mage casts magic this age (%) |
| mage_curse_chance | buyucu_lanet_sans | 50 | 0 | 100 | Heroes and mortals | A mage curses an enemy (otherwise protects) (%) |
| creature_revolt_chance | yaratik_isyan_sans | 8 | 0 | 100 | Creatures | An intelligent creature rebels against its creator (%) |
| godlessness_chance | tanrisizlik_sans | 15 | 0 | 100 | Religion and language | A community of weak faith becomes godless (%) |
| evolution_chance | evrim_sans | 18 | 0 | 100 | Creatures | A migrated species diverges into a subspecies (%) |
| birth_chance | dogum_sans | 30 | 0 | 100 | Heroes and mortals | A child from lover or married mortals (%) |
| love_rivalry_chance | ask_rekabet_sans | 8 | 0 | 100 | Heroes and mortals | Love or rivalry between mortals in the same place (%) |
| love_ratio | ask_orani | 55 | 0 | 100 | Heroes and mortals | Share of these that are love (%) |
| dialect_chance | lehce_sans | 15 | 0 | 100 | Religion and language | Dialect divergence in an isolated settlement (%) |
| ghost_chance | hayalet_sans | 50 | 0 | 100 | Beyond (afterlife) | If the dead return, the deceased becomes a ghost (%) |
| spirit_birth_chance | ruh_dogus_sans | 30 | 0 | 100 | Beyond (afterlife) | The spirit of a famous dead person finds no rest (%) |
| mourning_rite_chance | yas_ayini_sans | 40 | 0 | 100 | Heroes and mortals | A mourning tradition for a famous dead person (%) |

### War strength (`DUNYA_SAVAS_GUCU`; local alias `SG`)
Components of war strength (askeriGuc, hamiBonus, silahGucu, muttefikGucu).

| key | original key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| patron_power_divisor | hami_guc_bolen | 8 | 1 | 1000 | War and diplomacy | Patron god's war contribution: god's power / this number |
| war_leader_multiplier | savas_babasi_carpan | 2 | 1 | 20 | War and diplomacy | The war-father power multiplies the patron contribution (×) |
| weapon_damage_divisor | silah_hasar_bolen | 8 | 1 | 1000 | War and diplomacy | A weapon's war contribution: damage / this number |
| armor_protection_divisor | silah_koruma_bolen | 10 | 1 | 1000 | War and diplomacy | Armour's war contribution: protection / this number |
| item_might_divisor | silah_kudret_bolen | 20 | 1 | 1000 | War and diplomacy | An item's might as war contribution: might / this number |
| warrior_threshold | savasci_esik | 10 | 0 | 100 | War and diplomacy | The warrior class adds war strength if above this share (%) |
| warrior_coefficient | savasci_katsayi | 60 | 0 | 1000 | War and diplomacy | Coefficient of the warrior-class share in war strength (%) |
| cult_zealotry | tarikat_bagnazlik | 60 | 0 | 1000 | War and diplomacy | Zealotry coefficient in a cult's war strength (%) |
| default_zealotry | varsayilan_bagnazlik | 50 | 0 | 100 | War and diplomacy | Zealotry in war of a cult with no recorded zealotry |
| cult_follower_log | tarikat_murit_log | 8 | 0 | 100 | War and diplomacy | Coefficient of follower count (log10) in a cult's war strength |
| faction_sway | hizip_nufuz | 20 | 0 | 1000 | War and diplomacy | Sway coefficient in a faction's war strength (%) |
| settlement_defense | yerlesim_savunma | 80 | 0 | 1000 | War and diplomacy | Walls (defence) coefficient in a settlement's war strength (%) |
| mortal_agility_divisor | olumlu_ceviklik_bolen | 2 | 1 | 100 | War and diplomacy | Agility contribution to a mortal's war strength: agility / this number |
| species_strength_divisor | tur_guc_bolen | 2 | 1 | 100 | War and diplomacy | Strength contribution to a creature species' war strength: strength / this number |
| default_stat | varsayilan_stat | 30 | 0 | 100 | War and diplomacy | Default strength of a community with no recorded war stat |
| war_knowledge | savas_bilgisi | 12 | 0 | 200 | War and diplomacy | War-strength bonus for those who know the art of war |
| forbidden_knowledge | yasak_bilgi | 15 | 0 | 200 | War and diplomacy | War-strength bonus for those who know forbidden knowledge |
| tier_strength | basamak_guc | 5 | 0 | 100 | War and diplomacy | War-strength bonus per civilization tier |
| ally_share | muttefik_pay | 40 | 0 | 100 | War and diplomacy | Share of their strength that allies add to a war (%) |

### World event effects (`DUNYA_ETKI`; local alias `DE`)
Effects of world-engine events: caps, stat changes, dice, thresholds.

| key | original key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| post_death_cap | olum_sonrasi_tavan | 2 | 0 | 50 | Beyond (afterlife) | Most mourning traditions or spirits (each) arising from deaths per age |
| language_faith_cap | dil_inanc_tavan | 4 | 0 | 100 | Religion and language | Most communities that acquire a language or faith per age |
| grudge_cap | kin_tavan | 1 | 0 | 20 | War and diplomacy | Most new hostilities arising from divine grudges per age |
| grudge_distance | kin_mesafe | 3 | 0 | 20 | War and diplomacy | Maximum map distance between communities a grudge can seep across (steps) |
| grudge_relation | kin_iliski | 40 | 0 | 100 | War and diplomacy | For a grudge, the patron gods' relation must be at most minus this much |
| raid_distance | baskin_mesafe | 2 | 0 | 20 | Creatures | Maximum distance at which a monster can raid (steps) |
| raid_prosperity | baskin_refah | 6 | 0 | 100 | Creatures | Prosperity loss of a raided settlement |
| raid_defense | baskin_savunma | 2 | 0 | 100 | Creatures | Increase in a settlement's walls (defence) after a raid |
| unknown_stat | bilinmeyen_stat | 30 | 0 | 100 | Population and growth | Default for unrecorded defence, influence or value (and for prosperity in uprisings) |
| unknown_prosperity | bilinmeyen_refah | 50 | 0 | 100 | Population and growth | Default for unrecorded prosperity (raid, famine, haunting, law, growth) |
| unknown_fertility | bilinmeyen_bereket | 50 | 0 | 100 | Population and growth | Default for unrecorded fertility (drought, famine migration, growth) |
| unknown_extent | bilinmeyen_genislik | 50 | 0 | 100 | Population and growth | Extent used in carrying capacity for a region with no recorded extent |
| unknown_justice | bilinmeyen_adalet | 50 | 0 | 100 | War and diplomacy | Justice of a law with no recorded justice |
| unknown_faith | bilinmeyen_inanc | 50 | 0 | 100 | Religion and language | Faith used in the godlessness check for a community with no recorded faith |
| raid_danger | baskin_tehlike | 50 | 0 | 100 | Creatures | Danger used in a raid for a monster with no recorded danger |
| raid_population | baskin_nufus | 100 | 1 | 1000000 | Creatures | Population used in a raid for a settlement with no recorded population |
| hunt_distance | av_mesafe | 3 | 0 | 20 | Heroes and mortals | Maximum distance of a monster a hero can hunt (steps) |
| trade_prosperity | ticaret_refah | 3 | 0 | 100 | Economy | Prosperity a trade route gives each age |
| trade_wealth | ticaret_servet | 3 | 0 | 100 | Economy | Wealth a trade route gives each age |
| trade_knowledge_multiplier | ticaret_bilgi_carpan | 2 | 1 | 20 | Economy | Trade-prosperity multiplier for those who know trade (×) |
| trade_prosperity_cap | ticaret_refah_tavan | 6 | 0 | 100 | Economy | Most prosperity trade routes give one community in one age (all routes together) |
| trade_wealth_cap | ticaret_servet_tavan | 6 | 0 | 100 | Economy | Most wealth trade routes give one community in one age (all routes together) |
| prosperity_target | refah_hedef | 50 | 0 | 100 | Economy | Equilibrium value prosperity is pulled toward in the long run; trade and resource gains above it have diminishing returns |
| prosperity_reversion | refah_donus | 10 | 0 | 100 | Economy | Share of the gap to the equilibrium value that prosperity closes each age (%) |
| curse_population_kept | lanet_nufus_kalan | 95 | 0 | 100 | Heroes and mortals | Share of population and followers a cursed community keeps each age (%) |
| curse_stat | lanet_stat | 3 | 0 | 100 | Heroes and mortals | Prosperity, fertility, strength and wealth a cursed entity loses each age |
| resource_abundance_threshold | kaynak_bolluk_esik | 15 | 0 | 100 | Economy | Minimum abundance of a resource that yields gains to its owners |
| resource_gain | kaynak_kazanc | 1 | 0 | 100 | Economy | Base prosperity, wealth and craft a resource owner gains each age |
| resource_value_divisor | kaynak_deger_bolen | 40 | 1 | 1000 | Economy | Value contribution to resource gain: value / this number |
| resource_consumption | kaynak_tuketim | 2 | 0 | 100 | Economy | Abundance each owner consumes from a resource per age |
| resource_regeneration | kaynak_yenilenme | 4 | 0 | 100 | Economy | Abundance regeneration of resources per age |
| barter_cap | ticaret_tavan | 2 | 0 | 50 | Economy | Most resource barters established spontaneously per age |
| item_curse_threshold | esya_lanet_esik | 50 | 0 | 100 | Heroes and mortals | Minimum curse of an item that harms its owner |
| curse_hp_divisor | lanet_can_bolen | 5 | 1 | 1000 | Heroes and mortals | HP damage a cursed item deals its owner: curse / this number |
| curse_stat_divisor | lanet_stat_bolen | 20 | 1 | 1000 | Heroes and mortals | Prosperity and defence damage of a cursed item: curse / this number |
| magic_storm_threshold | buyu_firtina_esik | 70 | 0 | 100 | Cosmic horror | Minimum magic of a region where a magic storm can break out |
| storm_might | firtina_kudret | 5 | 0 | 100 | Cosmic horror | Might increase of resources and items in a magic storm |
| storm_curse | firtina_lanet | 10 | 0 | 100 | Cosmic horror | Curse increase of an item cursed in a magic storm |
| storm_power | firtina_guc | 5 | 1 | 12 | Cosmic horror | Power level of the magic-storm event |
| storm_severity_base | firtina_siddet_taban | 40 | 0 | 100 | Cosmic horror | Base of magic-storm severity |
| storm_severity_die | firtina_siddet_zar | 40 | 1 | 100 | Cosmic horror | Die added to magic-storm severity (1–X) |
| schism_cap | bolunme_tavan | 1 | 0 | 20 | Religion and language | Most cult schisms per age |
| schism_percentile | bolunme_yuzde | 50 | 0 | 100 | Religion and language | Cults that can split: those above the world's X-th percentile of following |
| schism_max | bolunme_ust | 3000 | 0 | 10000000 | Religion and language | A cult with this many followers can always split |
| schism_age | bolunme_yas | 2 | 0 | 100 | Religion and language | Minimum age of a cult that can split (ages) |
| schism_large_age | bolunme_buyuk_yas | 4 | 0 | 100 | Religion and language | Minimum age for a non-zealous cult to split (ages) |
| schism_zealotry_gain | bolunme_bagnazlik_artis | 10 | 0 | 100 | Religion and language | Zealotry increase of the breakaway sect |
| schism_influence_drop | bolunme_etki_dusus | 10 | 0 | 100 | Religion and language | Influence deficit of the breakaway sect |
| schism_relation | bolunme_iliski | 10 | 0 | 100 | Religion and language | Relation loss between the old and new patron in a schism |
| splinter_power_base | ayrilan_guc_taban | 2 | 1 | 12 | Population and growth | Lowest power level of a new entity that splits off, migrates or returns |
| creature_migration_danger | yaratik_goc_tehlike | 45 | 0 | 100 | Creatures | Minimum danger of a species that can migrate to a neighbouring region |
| migration_cap | goc_tavan | 1 | 0 | 20 | Creatures | Most creature migrations per age |
| hero_max_pop | kahraman_ust | 8000 | 0 | 100000000 | Heroes and mortals | A people this populous can always produce a hero (people) |
| hero_cap | kahraman_tavan | 1 | 0 | 20 | Heroes and mortals | Most spontaneously born heroes per age |
| hero_power_level | kahraman_guc_seviye | 4 | 1 | 12 | Heroes and mortals | Power level of a spontaneously born hero |
| hero_hp | kahraman_can | 120 | 1 | 1000 | Heroes and mortals | HP of a spontaneously born hero |
| hero_strength_base | kahraman_guc_taban | 45 | 0 | 100 | Heroes and mortals | Hero's strength: base |
| hero_strength_die | kahraman_guc_zar | 40 | 1 | 100 | Heroes and mortals | Hero's strength: added die (1–X) |
| hero_agility_base | kahraman_cev_taban | 40 | 0 | 100 | Heroes and mortals | Hero's agility: base |
| hero_agility_die | kahraman_cev_zar | 40 | 1 | 100 | Heroes and mortals | Hero's agility: added die (1–X) |
| hero_intellect_base | kahraman_akil_taban | 30 | 0 | 100 | Heroes and mortals | Hero's intellect: base |
| hero_intellect_die | kahraman_akil_zar | 50 | 1 | 100 | Heroes and mortals | Hero's intellect: added die (1–X) |
| hero_charisma_base | kahraman_kar_taban | 30 | 0 | 100 | Heroes and mortals | Hero's charisma: base |
| hero_charisma_die | kahraman_kar_zar | 50 | 1 | 100 | Heroes and mortals | Hero's charisma: added die (1–X) |
| hero_age_base | kahraman_yas_taban | 16 | 0 | 200 | Heroes and mortals | Age at which the hero appears: base (years) |
| hero_age_die | kahraman_yas_zar | 6 | 1 | 200 | Heroes and mortals | Die added to the hero's age (1–X years) |
| hero_lifespan_base | kahraman_omur_taban | 75 | 1 | 50000 | Heroes and mortals | Hero's lifespan: base (years) |
| hero_lifespan_die | kahraman_omur_zar | 40 | 1 | 50000 | Heroes and mortals | Die added to the hero's lifespan (1–X years) |
| spread_cap | yayilim_tavan | 4 | 0 | 100 | Religion and language | Most pieces of knowledge spreading along bonds per age |
| writing_multiplier | yazi_carpan | 2 | 1 | 20 | Religion and language | Knowledge-spread multiplier from those who know writing (×) |
| disaster_law_multiplier | afet_yasasi_carpan | 2 | 1 | 20 | Population and growth | Frequency multiplier of natural events under the disaster law (×) |
| drought_fertility | kurak_bereket | 35 | 0 | 100 | Population and growth | Drought can occur in a region below this fertility |
| plague_extra_cap | veba_ek_tavan | 5 | 0 | 100 | Population and growth | Most that crowding can add to the regional plague probability (%) |
| plague_pop_divisor | veba_nufus_bolen | 1000000 | 1000 | 1000000000 | Population and growth | Crowding contribution to regional plague: population / this number |
| disaster_severity_base | afet_siddet_taban | 30 | 0 | 100 | Population and growth | Base of natural-event severity |
| disaster_severity_die | afet_siddet_zar | 50 | 1 | 100 | Population and growth | Die added to natural-event severity (1–X) |
| disaster_severity_scale | afet_siddet_olcek | 70 | 1 | 1000 | Population and growth | Impact strength of a natural event: severity / this number |
| city_plague_percentile | kent_veba_yuzde | 80 | 0 | 100 | Population and growth | Cities that can suffer plague: those above the world's X-th percentile of population |
| city_plague_max | kent_veba_ust | 40000 | 0 | 100000000 | Population and growth | A city this populous can always suffer plague (people) |
| city_plague_floor | kent_veba_en_az | 1500 | 0 | 10000000 | Population and growth | Minimum population of a city that can suffer plague (even if starving or at war) |
| default_provisions | erzak_varsayilan | 60 | 0 | 100 | Population and growth | Default provisions of a community with no recorded granary |
| hungry_provisions | ac_erzak | 15 | 0 | 100 | Population and growth | A community below these provisions counts as starving |
| plague_spread_ages | veba_yayilim_cag | 1 | 0 | 20 | Population and growth | How long an epidemic spreads along roads (epidemics of the last X ages) |
| plague_spread_severity | veba_yayilim_siddet | 60 | 0 | 100 | Population and growth | Severity of an epidemic caught via roads (% of the original epidemic) |
| famine_pop | kitlik_nufus | 1500 | 0 | 10000000 | Population and growth | Minimum population of a community that can undertake famine migration |
| famine_cap | kitlik_tavan | 1 | 0 | 20 | Population and growth | Most famine migrations per age |
| famine_prosperity | kitlik_refah | 20 | 0 | 100 | Population and growth | A community below this prosperity counts as in famine |
| famine_fertility_gap | kitlik_bereket_fark | 5 | 0 | 100 | Population and growth | The destination region must be at least this much more fertile than the origin |
| migrant_prosperity | gocmen_refah | 30 | 0 | 100 | Population and growth | Starting prosperity of a migrant settlement |
| migrant_defense | gocmen_savunma | 20 | 0 | 100 | Population and growth | Starting defence of a migrant settlement |
| migrant_faith | gocmen_inanc | 55 | 0 | 100 | Population and growth | Starting piety of a migrant settlement |
| revolt_percentile | isyan_yuzde | 50 | 0 | 100 | War and diplomacy | Cities that can rise up: those above the world's X-th percentile of population |
| revolt_max_pop | isyan_ust | 5000 | 0 | 100000000 | War and diplomacy | A poor city this populous can always rise up (people) |
| just_law | adil_kanun | 60 | 0 | 100 | War and diplomacy | Minimum justice for a law to count as just |
| revolt_cap | isyan_tavan | 1 | 0 | 20 | War and diplomacy | Most uprisings per age |
| rebel_power_level | isyanci_guc_seviye | 3 | 1 | 12 | War and diplomacy | Power level of the rebel faction |
| rebel_strength_base | isyanci_guc_taban | 30 | 0 | 100 | War and diplomacy | Rebels' strength: base |
| rebel_strength_die | isyanci_guc_zar | 30 | 1 | 100 | War and diplomacy | Die added to the rebels' strength (1–X) |
| rebel_wealth_base | isyanci_servet_taban | 10 | 0 | 100 | War and diplomacy | Rebels' wealth: base |
| rebel_wealth_die | isyanci_servet_zar | 15 | 1 | 100 | War and diplomacy | Die added to the rebels' wealth (1–X) |
| rebel_sway_base | isyanci_nufuz_taban | 25 | 0 | 100 | War and diplomacy | Rebels' sway: base |
| rebel_sway_die | isyanci_nufuz_zar | 30 | 1 | 100 | War and diplomacy | Die added to the rebels' sway (1–X) |
| revolt_defense | isyan_savunma | 10 | 0 | 100 | War and diplomacy | Defence loss of a rebelling city |
| revolt_prosperity_loss | isyan_refah | 5 | 0 | 100 | War and diplomacy | Prosperity loss of a rebelling city |
| haunt_prosperity | musallat_refah | 6 | 0 | 100 | Beyond (afterlife) | Prosperity loss of a settlement haunted by a spirit |
| haunt_restlessness | musallat_huzur | 5 | 0 | 100 | Beyond (afterlife) | Decrease in the restlessness of a haunting spirit |
| law_just_threshold | kanun_adil_esik | 50 | 0 | 100 | War and diplomacy | Walls grow stronger if the average justice of the laws is above this |
| law_defense | kanun_savunma | 2 | 0 | 100 | War and diplomacy | Per-age defence increase of a settlement with just laws |
| law_unjust_threshold | kanun_adaletsiz | 30 | 0 | 100 | War and diplomacy | Prosperity falls if the average justice of the laws is below this |
| law_prosperity | kanun_refah | 2 | 0 | 100 | War and diplomacy | Per-age prosperity loss of a settlement with unjust laws |
| coin_threshold | sikke_esik | 50 | 0 | 100 | Economy | Minimum prosperity or wealth of a community that can mint coins |
| coin_power | sikke_guc | 3 | 1 | 12 | Economy | Power level of a currency |
| coin_might_base | sikke_kudret_taban | 10 | 0 | 100 | Economy | Might of a currency: base |
| coin_might_die | sikke_kudret_zar | 20 | 1 | 100 | Economy | Die added to a currency's might (1–X) |
| shared_currency_prosperity | ortak_para_refah | 2 | 0 | 100 | Economy | Per-age prosperity increase of trade partners using a shared currency |
| mage_intellect | buyucu_akil | 60 | 0 | 100 | Heroes and mortals | Minimum intellect of a mortal who can become a mage |
| mage_protect_chance | buyucu_koruma_sans | 50 | 0 | 100 | Heroes and mortals | A mage weaves a protection spell over their homeland (otherwise a fertility spell) (%) |
| creature_revolt_intellect | yaratik_isyan_zeka | 50 | 0 | 100 | Creatures | Minimum intelligence of a creature that can rebel against its creator |
| creature_revolt_danger | yaratik_isyan_tehlike | 55 | 0 | 100 | Creatures | Minimum danger of a creature that can rebel against its creator |
| creature_revolt_kept | yaratik_isyan_kalan | 92 | 0 | 100 | Creatures | Share of population remaining in the community attacked by a rebelling creature (%) |
| creature_revolt_presence | yaratik_isyan_varlik | 4 | 0 | 100 | Creatures | Presence loss of the son whose creature rebels |
| godlessness_faith | tanrisizlik_inanc | 35 | 0 | 100 | Religion and language | A community below this faith can become godless |
| evolution_ages | evrim_cag | 2 | 0 | 100 | Creatures | Minimum time for a migrated species to diverge into a subspecies (ages) |
| evolution_cap | evrim_tavan | 1 | 0 | 20 | Creatures | Most species evolutions per age |
| evolution_deviation | evrim_sapma | 15 | 0 | 100 | Creatures | Deviation of a subspecies' stats from its ancestor (±) |
| birth_cap | dogum_tavan | 2 | 0 | 50 | Heroes and mortals | Most births from lovers and spouses per age |
| inherit_stat | kalitim_stat | 40 | 0 | 100 | Heroes and mortals | Default for an unrecorded mortal stat (inheritance and spirits) |
| inherit_deviation | kalitim_sapma | 10 | 0 | 100 | Heroes and mortals | Deviation of children's and heirs' stats from the parent (±) |
| child_hp | cocuk_can | 80 | 1 | 1000 | Heroes and mortals | HP of a newborn child |
| default_lifespan | omur_varsayilan | 70 | 1 | 50000 | Heroes and mortals | Lifespan of a mortal with no recorded lifespan (years) |
| child_lifespan_min | cocuk_omur_en_az | 20 | 1 | 50000 | Heroes and mortals | Shortest lifespan of a newborn child (years) |
| lifespan_cap | omur_tavan | 50000 | 1 | 1000000 | Heroes and mortals | Longest lifespan of mortals (years) |
| love_age | ask_yas | 16 | 0 | 200 | Heroes and mortals | Minimum age of a mortal who can enter love or rivalry |
| dialect_ages | lehce_cag | 4 | 0 | 100 | Religion and language | Minimum age of a settlement for dialect divergence (ages) |
| dialect_cap | lehce_tavan | 1 | 0 | 20 | Religion and language | Most dialect divergences per age |
| dialect_power | lehce_guc | 2 | 1 | 12 | Religion and language | Power level of a new dialect |
| dialect_prevalence | lehce_yayginlik | 15 | 0 | 100 | Religion and language | Prevalence of a new dialect |
| dialect_complexity | lehce_karmasiklik | 40 | 0 | 100 | Religion and language | Complexity of a new dialect |
| dialect_sacredness | lehce_kutsallik | 10 | 0 | 100 | Religion and language | Sacredness of a new dialect |
| dialect_words | lehce_kelime | 5 | 0 | 1000 | Religion and language | Words carried over from the parent language to a new dialect |
| magic_price_threshold | buyu_bedeli_esik | 60 | 0 | 100 | Population and growth | Under the price-of-magic law, minimum magic of a people that pays the price |
| magic_price_kept | buyu_bedeli_kalan | 95 | 0 | 100 | Population and growth | Under the price-of-magic law, share of population a people keeps each age (%) |
| architecture_defense | mimarlik_savunma | 5 | 0 | 100 | Civilization | Per-age walls increase of a settlement that knows architecture |
| notable_charisma | onemli_karizma | 70 | 0 | 100 | Heroes and mortals | Minimum charisma of a mortal counted as notable (lives longer) |
| elder_margin | yasli_pay | 10 | 0 | 3000 | Heroes and mortals | A created mortal with this many years (or fewer) left of its lifespan in the age of its birth is rejuvenated (years) |
| rejuvenate_base | genclesme_taban | 20 | 0 | 100 | Heroes and mortals | Age of a rejuvenated mortal: at least this % of its lifespan |
| rejuvenate_die | genclesme_zar | 30 | 0 | 100 | Heroes and mortals | Random share of lifespan added to a rejuvenated mortal's age (at most %) |
| short_life_multiplier | kisa_omur_carpan | 2 | 1 | 20 | Heroes and mortals | Ageing multiplier under the short-life law (×) |
| heir_hp | varis_can | 80 | 1 | 1000 | Heroes and mortals | HP of an heir |
| heir_age_base | varis_yas_taban | 16 | 0 | 200 | Heroes and mortals | Heir's age: base (years) |
| heir_age_die | varis_yas_zar | 12 | 1 | 200 | Heroes and mortals | Die added to the heir's age (1–X years) |
| heir_lifespan_deviation | varis_omur_sapma | 15 | 0 | 1000 | Heroes and mortals | Deviation of the heir's lifespan from the deceased's (± years) |
| heir_lifespan_min | varis_omur_en_az | 45 | 1 | 50000 | Heroes and mortals | Shortest lifespan of an heir (years) |
| death_domain_essence | olum_alani_oz | 2 | 0 | 100 | Beyond (afterlife) | Essence a god with the death domain gains on each death |
| death_domain_presence | olum_alani_varlik | 1 | 0 | 100 | Beyond (afterlife) | Presence increase of a god with the death domain on each death |
| default_presence | varlik_varsayilan | 60 | 0 | 100 | Creator and essence | Presence value of a son with no recorded presence |
| famous_charisma | unlu_karizma | 60 | 0 | 100 | Beyond (afterlife) | Minimum charisma of a dead person counted as famous |
| spirit_restless_slain | ruh_huzursuz_katil | 70 | 0 | 100 | Beyond (afterlife) | Base restlessness of the spirit of a famous person who was killed |
| spirit_restless_natural | ruh_huzursuz_dogal | 40 | 0 | 100 | Beyond (afterlife) | Base restlessness of the spirit of a famous person who died of natural causes |
| spirit_restless_die | ruh_huzursuz_zar | 20 | 1 | 100 | Beyond (afterlife) | Die added to a spirit's restlessness (1–X) |
| spirit_restless_class | ruh_huzursuz_sinif | 50 | 0 | 100 | Beyond (afterlife) | A spirit with restlessness above this counts as a restless spirit (below it, an ancestor spirit) |
| spirit_power_divisor | ruh_guc_bolen | 2 | 1 | 100 | Beyond (afterlife) | A spirit's strength: the deceased's strength / this number |
| spirit_power_bonus | ruh_guc_ek | 20 | 0 | 100 | Beyond (afterlife) | Amount added to a spirit's strength |
| mourning_power | yas_guc | 2 | 1 | 12 | Heroes and mortals | Power level of a mourning tradition |
| mourning_prevalence | yas_yayginlik | 50 | 0 | 100 | Heroes and mortals | Prevalence of a mourning tradition |
| mourning_rigidity | yas_katilik | 40 | 0 | 100 | Heroes and mortals | Rigidity of a mourning tradition |

### Monster hunt (`DUNYA_AV`; local alias `KH`)
Heroism: the encounter between a hero and a monster.

| key | original key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| intellect_divisor | akil_bolen | 3 | 1 | 100 | Heroes and mortals | Intellect contribution to the hero's power: intellect / this number |
| agility_divisor | ceviklik_bolen | 2 | 1 | 100 | Heroes and mortals | Agility contribution in the encounter: agility / this number |
| danger_divisor | tehlike_bolen | 2 | 1 | 100 | Heroes and mortals | Danger contribution to the monster's power: danger / this number |
| die | zar | 20 | 1 | 100 | Heroes and mortals | Encounter die (1–X) |
| die_multiplier | zar_carpan | 3 | 0 | 20 | Heroes and mortals | Multiplier of the encounter die |
| patron_charisma_divisor | hami_karizma_bolen | 10 | 1 | 1000 | Heroes and mortals | Patron god's contribution to the hero: charisma / this number |
| weapon_multiplier | silah_carpan | 2 | 0 | 20 | Heroes and mortals | Multiplier of the hero's weapons in the encounter (×) |
| mage_intellect_divisor | buyucu_akil_bolen | 3 | 1 | 100 | Heroes and mortals | Extra power of a mage hero: intellect / this number |
| megafauna_power | megafauna_guc | 40 | 0 | 500 | Creatures | Extra power of megafauna in the encounter |
| singular_power | tekil_guc | 5 | 1 | 12 | Creatures | A monster of this power level dies after a single defeat |
| danger_loss | tehlike_kaybi | 25 | 0 | 100 | Creatures | Danger loss of a defeated monster |
| death_danger | olum_tehlike | 5 | 0 | 100 | Creatures | A monster whose danger drops to this dies |
| rewind_danger | geri_sarma_tehlike | 20 | 0 | 100 | Creatures | Danger a time-rewinding creature gains upon its return |
| megafauna_power_gain | megafauna_guc_artis | 2 | 0 | 12 | Heroes and mortals | Power-level increase of a megafauna slayer |
| power_cap | guc_tavan | 10 | 1 | 12 | Heroes and mortals | Power-level cap of heroes and items |
| epic_power | destan_guc | 8 | 1 | 12 | Heroes and mortals | Power level of an age-changing epic |
| epic_prevalence | destan_yayginlik | 90 | 0 | 100 | Heroes and mortals | Prevalence of an age-changing epic |
| victory_charisma | zafer_karizma | 5 | 0 | 100 | Heroes and mortals | Charisma increase of a victorious hero |
| patron_fame | hami_un | 4 | 0 | 100 | Heroes and mortals | Fame gained by the patron god on the hero's victory |
| patron_xp | hami_xp | 12 | 0 | 1000 | Heroes and mortals | Experience gained by the patron god on the hero's victory |
| weapon_might | silah_kudret | 6 | 0 | 100 | Heroes and mortals | Might increase of the hero's weapon on victory |
| legend_victories | efsane_zafer | 2 | 1 | 100 | Heroes and mortals | Victories needed for a weapon to become legendary |
| ballad_power | turku_guc | 3 | 1 | 12 | Heroes and mortals | Power level of a heroic ballad |
| ballad_prevalence | turku_yayginlik | 55 | 0 | 100 | Heroes and mortals | Prevalence of a heroic ballad |
| armor_threshold | zirh_esik | 40 | 0 | 100 | Heroes and mortals | Minimum protection of armour that can turn death into a wound |
| armor_chance_base | zirh_sans_taban | 50 | 0 | 100 | Heroes and mortals | Probability that armour saves the hero from death: base (%) |
| armor_chance_divisor | zirh_sans_bolen | 250 | 1 | 10000 | Heroes and mortals | Contribution to the armour's saving probability: protection / this number |
| armor_hp | zirh_can | 60 | 0 | 1000 | Heroes and mortals | HP loss of a hero saved by their armour |
| unknown_hp | bilinmeyen_can | 100 | 1 | 1000 | Heroes and mortals | HP before armour damage of a hero with no recorded HP |
| armor_wear | zirh_asinma | 15 | 0 | 100 | Heroes and mortals | Protection loss of armour that saved the hero |
| lament_power | agit_guc | 2 | 1 | 12 | Heroes and mortals | Power level of a fallen hero's lament |
| lament_prevalence | agit_yayginlik | 45 | 0 | 100 | Heroes and mortals | Prevalence of a fallen hero's lament |

### Age transition (`DUNYA_CAG_GECISI`; local alias `CG`)
Age transition: the effect of laws on the land, population growth, regeneration of the sons, essence income.

| key | original key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| law_fertility | yasa_bereket | 3 | 0 | 100 | Population and growth | Per-age fertility increase of lands under the fertility law |
| law_drought | yasa_kuraklik | 3 | 0 | 100 | Population and growth | Per-age fertility loss of lands under the drought law |
| capacity_architecture | kapasite_mimarlik | 120 | 0 | 1000 | Population and growth | Carrying-capacity multiplier of a settlement that knows architecture (%) |
| capacity_fertility_base | kapasite_bereket_taban | 30 | 0 | 1000 | Population and growth | Share of carrying capacity independent of fertility (%) |
| capacity_fertility_divisor | kapasite_bereket_bolen | 60 | 1 | 1000 | Population and growth | Fertility contribution to carrying capacity: fertility / this number |
| capacity_extent_base | kapasite_genislik_taban | 50 | 0 | 1000 | Population and growth | Share of carrying capacity independent of extent (%) |
| location_fertility_share | konum_bereket_pay | 40 | 0 | 100 | Population and growth | For one living at a place outside a region, the place's share of their fertility (%; the rest is the region's) |
| fertility_power_multiplier | bereket_gucu_carpan | 2 | 1 | 20 | Population and growth | Growth multiplier from a patron with the fertility power (×) |
| fertility_positive | bereket_pozitif | 35 | 0 | 100 | Population and growth | Minimum fertility at which the fertility power multiplies growth |
| cult_default_charisma | tarikat_karizma_varsayilan | 30 | 0 | 100 | Population and growth | Default charisma in the growth of a cult with no patron |
| cult_capacity_min | tarikat_kapasite_en_az | 150 | 0 | 10000000 | Population and growth | Lowest ceiling on cult followers in a region (people) |
| cult_shrink_max | tarikat_kucilme_ust | 20 | 0 | 100 | Population and growth | Maximum shrinkage of a cult in one age (%) |
| cult_growth_max | tarikat_buyume_ust | 50 | 0 | 1000 | Population and growth | Maximum growth of a cult in one age (%) |
| growth_prosperity_threshold | buyume_refah_esik | 40 | 0 | 100 | Population and growth | A city above this prosperity grows faster (below it, slower) |
| immortality_growth | olumsuzluk_buyume | 50 | 0 | 1000 | Population and growth | Population growth rate under the immortality law (%) |
| short_life_growth | kisa_omur_buyume | 150 | 0 | 1000 | Population and growth | Population growth rate under the short-life law (%) |
| sky_base_weight | gok_taban_agirlik | 5 | 0 | 1000 | Sky | Base weight of each celestial body when choosing the star of the age |
| awaken_hp_divisor | uyanis_can_bolen | 2 | 1 | 100 | Creator and essence | HP of a son waking from slumber: maximum HP / this number |
| heal_base | iyilesme_taban | 5 | 0 | 1000 | Creator and essence | A son's per-age HP healing: base |
| heal_divisor | iyilesme_bolen | 10 | 1 | 1000 | Creator and essence | Endurance contribution to a son's healing: endurance / this number |
| presence_step | varlik_adim | 10 | 0 | 100 | Creator and essence | Most a son's presence can approach its target in one age |
| faith_essence_divisor | inanc_oz_bolen | 10 | 1 | 1000 | Creator and essence | Essence income from faith: faith / this number (son and creator) |
| essence_spring | oz_pinari | 4 | 0 | 100 | Creator and essence | Extra essence income of a son with the essence-spring power |
| radiant_essence | parlak_oz | 3 | 0 | 100 | Creator and essence | Extra essence income of a son whose presence is radiant |
| star_domain_essence | yildiz_alan_oz | 3 | 0 | 100 | Sky | Extra essence income of a son who holds the domain of the age's star |
| work_fame | eser_un | 1 | 0 | 100 | Creator and essence | Per-age fame contribution of a work that tells of a god |
| work_presence | eser_varlik | 1 | 0 | 100 | Creator and essence | Per-age presence contribution of a work that tells of a god |
| domain_rivalry | alan_rekabet | 3 | 0 | 100 | Creator and essence | Per-age relation loss of sons sharing the same domain (per shared domain) |
| domain_rivalry_floor | alan_rekabet_taban | 70 | 0 | 100 | Creator and essence | Domain rivalry lowers the relation to at most minus this value (deeper enmity comes from conflict and slowly recovers) |
| rebel_theft_base | asi_calma_taban | 6 | 0 | 1000 | Creator and essence | Essence a rebel son steals from his father: base |
| rebel_theft_level | asi_calma_seviye | 2 | 0 | 100 | Creator and essence | Extra essence a rebel son steals per level |
| temple_divisor | tapinak_bolen | 2 | 1 | 100 | Apocalypse | Number of temples that push the apocalypse back by 1 |
| apocalypse_severity | kiyamet_siddet | 90 | 0 | 100 | Apocalypse | Severity of the apocalypse's region-destroying catastrophes (%) |
| apocalypse_event_severity | kiyamet_olay_siddet | 100 | 0 | 100 | Apocalypse | Severity of the apocalypse event record |
| apocalypse_chronicle_ids | kiyamet_kronik_id | 12 | 0 | 1000 | Chronicle | Most regions linked to the apocalypse chronicle entry |
| chronicle_id_cap | kronik_id_tavan | 40 | 0 | 1000 | Chronicle | Most entities linked to a folded chronicle line |
| essence_overflow_note | oz_tasma_not | 20 | 0 | 100000 | Chronicle | A note is written to the chronicle when overflowing essence exceeds this amount |

## 3. Mortal agents (olumluler.js)

Source: `src/olumluler.js` (1405 lines). This module makes **mortal entities** (peoples, factions, cults, settlements, named mortals and intelligent species) act as LLM agents once per epoch with their own self-interest: they produce items, build, create culture and languages, discover resources and lands, trade, wage war, worship / deny gods, preach, sabotage, raise armies, travel between worlds, etc. It contains:

1. Tunable balance numbers (namespace `OLUMLU_ARAC`, "mortal tools").
2. Region / adjacency helpers used across the engine (`ustBolge`, `ustBolgeId`, `ayniBolge`, `yakinMi`).
3. Agent selection per epoch (`ajanAdaylari`, `dunyaPaylari`, `ajanSec`).
4. Prompt building (`baglamMetni` context, `sistemMetni` system prompt).
5. The MCP tool server for one mortal turn (`buildOlumluServer`) with ~43 tools.
6. The turn runner (`olumluTuru`).
7. Small exported helpers (`esirMi`, `ogrenebilirMi`, `borcVadeleri`, re-export of `borcOku`).

Mortal agents never cost the player anything; they are driven by a cheap model (`modelFor('yaygin')` = the model configured for the "common" rarity tier). Everything a mortal creates goes **directly to canon** (`durum='kanon'` is the DB default); it is NOT judged by Fate (Kader) before entering the world. Created entity ids are collected in `ctx.yaratimlar` and attached to the mortal's final utterance chronicle entry.

### Cross-references (who calls this module, what it calls)

Callers:
- `epoch.js` phase 2 ("Mortals' turn"): `sayi = world.olumlu_sayisi ?? OLUMLU_AJAN.varsayilan (4)`; if `sayi > 0` and phase not done: `cd.ajanlar = ajanAdaylari(sayi).map(id)` saved in the epoch checkpoint (only computed once per epoch, so resuming an interrupted epoch reuses the same picks); filters to still-canon entities with `son_eylem_cag < cag`; runs `olumluTuru(v, publish)` for each via a concurrency pool of size `max(1, world.olumlu_paralel ?? 1)`; if a turn throws, it is retried once with a fresh entity read; second failure only publishes an error event (`"{name} could not act this epoch: {msg}"`).
- `firsatlar.js` uses `ustBolge`, `yakinMi`, `ogrenebilirMi` (opportunity hints).
- `sim.js` uses `ustBolge`, `ustBolgeId`, `yakinMi`.
- `ufuk.js` uses `ustBolge` and many `OLUMLU_K` numbers (`rota_esik`, `bilinmeyen_esik`, `bilinmeyen_dunya_tur`, `rota_akil_bolen`, `kapi_*`, `stat_varsayilan`).
- `etiket-onar.js` uses `OLUMLU_K.uret_usta` / `uret_saglam` (item quality labels).

Callees (do not spec here; wire them in the new design):
- `db.js`: `q` (query helpers), `tx`.
- `llm.js`: `agentTurn` (agent loop with retries/continuations), `araclariSar` (tool wrapper: serialization, ctx snapshot/rollback, ctx persistence).
- `rules.js`: `OLUMLU_AJAN`, `VARLIK_TURLERI`, `ALANLAR`, `BILGI_DALLARI`, `GUC_SEVIYELERI`, `KURAL`, `SINIR`, `clamp`, `d`, `alanEsle`, `esnekDeger`, `girdiTemizle`, `borcAciklama`, `borcOku`, `SEYAHAT_YONTEMLERI`.
- `mudahale.js`: `bilir`, `bildikleri`, `ogret`, `dalOf`, `aktifYasalar`.
- `world.js`: `getWorld`, `getSon`, `getVarlik`, `kanonlar`, `addKronik`, `addBag`, `bagVar`, `hami`, `yabanciHami`, `iliskiDegistir`, `saveStat`, `modelFor`, `dunyaBasligi`, `dunyaSatiri`, `kozmosSatirlari`, `varlikDetay`, `varlikAra`, `varlikSatir`, `isimAlinmis`, `benzerAd`, `konusulanDil`, `sozlukEkle`, `sozlukDil`, `dilSatirlari`, `nameOf`, `sonKronik`, `turCtxYaz`, `turCtxOku`, `butce`, `bolumluButce`, `BAGLAM_BUTCE`, `BAGLAM_K`, `motifYasagi`, `anlatiTemizle`, `konumSurumu`.
- `tools.js`: `KelimeSchema`, `fillStats`, `atomik`, `bedavaMi`, `olumluYasi`, `sayi`, `kayitDurumu`, `kanonDisi`, `altTurDuzelt`, `aracAlanlari`.
- `public/dil.js`: `ekDuzelt`, `toplulukIci` (Turkish grammar; LANGUAGE-SPECIFIC).
- `public/etiket.js`: `etiket` (display label for an enum key).
- `gorselyon.js`: `promptDuzelt`, `GORSEL_YAZIM`.
- `denge.js`: `tanimla` (tunable registry).
- `agents.js`: `sozuAyikla`, `ortakTikler`.
- `seyahat.js`: `rotalar`, `rotaKullanabilir`, `yolculukBaslat`, `rotaSatirlari` (`rotaAc` imported but unused here).
- `kozmos.js`: `dunyaDogur` (LLM world birth).
- `olum.js`: `OLUM`, `dirilisAyini`, `AYIN_TURLERI`.
- `ufuk.js`: `KESIF`, `yolAra`, `yolYontemi`, `sezgiyiDogur`, `toprakStatlari`, `bolgeyiYerlestir`, `onculer`, `kesifBilgisiVar`.
- `konsey.js`: `ruyalar`, `bekleyenRuya`.
- `yaratici.js`: `yaraticiyaTapin`, `olumluDuasi`.
- `yaratik.js`: `kimeraDok` (+ `YARATIK.kimera_dokuma_mesafe`).
- `korku.js`: `sagduyu` (+ `KORKU.bulaniklik_esik`).
- `otesi.js`: `ruhKapla`.
- `derin.js`: `tanriOlumu`, `tIliski`, `tIliskiDegistir`, `toplumOf`, `etiketEkle`, `etiketSil`, `mesafe`, `savasIlan`, `ateskesVar`.
- `yabanci.js`: `ytStatlar`.
- `medeniyet.js`: `borcGecikmeleri`.
- `firsatlar.js`: `olumluFirsatlari`.
- `harita.js`: `haritaHesapla`.
- `sim.js`: `olumSonrasi`, `olumluYarala`.

### Glossary used in this module

Entity types (`varliklar.tur`):

| Turkish | English | Notes |
|---|---|---|
| halk | people | community |
| hizip | faction | community |
| yerlesim | settlement | community |
| tarikat | cult / religious order | community |
| olumlu | named mortal (individual hero) | |
| tur | species (creature species) | acts as an agent only if `zeka >= 55` |
| bolge | region | top of the location chain |
| yer | place | inside a region |
| kaynak | resource | |
| esya | item | |
| yapit | structure / monument | |
| dil | language | |
| gelenek / efsane / eser / kanun | tradition / legend / artwork / law | culture |
| teknoloji | knowledge (technology) | branch stored as tag `dal:<branch>` |
| arac | vehicle / craft (ship, ancient gate) | |
| ordu | army | owner stored as tag `taraf:<id>` |
| kehanet | prophecy | |
| olay | event (wars are `olay` with `alt_tur='savaş'`) | |
| ruh | spirit | |

"Communities" (`TOPLULUK_TURLERI`) = `halk, hizip, yerlesim, tarikat`. "Parties" (`TARAF_TURLERI`) = communities + `olumlu`.

Stats (`statlar` JSON) referenced: `nufus` population, `murit` disciples, `refah` prosperity, `servet` wealth, `savunma` defense, `inanc` faith, `guc` strength, `savascilik` martial prowess, `zanaat` craft, `akil` wits/intellect, `zeka` intelligence (species), `etki` influence, `nufuz` sway, `karizma` charisma, `ceviklik` agility, `can` health, `yas` age, `omur` lifespan, `sagduyu` sanity, `hasar` damage, `koruma` protection, `kudret` potency, `lanet` curse, `bolluk` abundance, `deger` value, `ihtisam` grandeur, `saglamlik` sturdiness, `islev` function, `un` fame, `katilik` rigidity, `adalet` justice, `yayginlik` prevalence, `karmasiklik` complexity, `kutsallik` sacredness, `seviye` level, `hiz` speed, `menzil` range, `murettebat` crew, `zirh` armor, `tuhaflik` strangeness, `buyukluk` size, `moral` morale, `techizat` equipment, `deneyim` experience, `kesinlik` certainty, `tehlike` danger, region `buyu` magic. Stats on the 0–100 scale are clamped with `clamp` (which also **rounds to integer**).

Son (god, `ogullar` row) fields used: `can` health, `un` fame, `varlik` existence (0–100), `statlar.{guc, irade (will), karizma, dayaniklilik (endurance)}`, `seviye` level, `gucler` (array of powers, each with `etki`), `durum` (`olu` = dead), `ad`, `unvan` title, `alan1/alan2` domains.

Bond types (`baglar.tur`, directed `kaynak → hedef`, endpoint types `v` entity, `o` son, `y` foreign god, `t` creator): `icinde` located-in, `konusur` speaks, `soyundan` descends-from, `sahip` owns, `kaynagi` made-from, `uretti` produced, `insa_etti` built, `tapar` worships, `kutlar` celebrates, `yonetir` governs, `anlatir` tells-of, `gocetti` migrated-to, `ticaret` trades-with, `dusman` enemy, `avlar` hunts, `muttefik` ally, `harac_oder` pays-tribute-to, `bilir` knows, `evcil` tamed, `kesfetti` discovered, `oldurdu` killed, `lanetledi` cursed, `esir` holds-captive (captor → captive), `korur` protects, `yoldas` companion, `komutan` commands, `parcasi` part-of, `casus` spies-on, `borclu` owes-debt-to (debtor → creditor), `kehanet_eder` prophesies-about. `bagVar(a, b, tur)` checks an active `v–v` bond of that type in **either direction**. Deactivation = `aktif=0` (history kept).

Two relationship tables: `iliskiler` (son ↔ son, via `iliskiDegistir`, −100..100) and `topluluk_iliski` (entity ↔ entity, via `tIliski`/`tIliskiDegistir` in derin.js, with history).

Dice: `d(n)` = uniform integer in `1..n`. `sans2(p)` = `random() < p`.

Tags used: `ajan seçili` (agent selected — forced pick, set by the player/UI), `seçilmiş` (chosen one), `tanrısız` (godless), `lanetli` (cursed), `esir` (captive), `kayıp` (lost knowledge), `harabe` (ruin), `tanrı cesedi` (god corpse), `boş mezar` (empty tomb), `megafauna`, `ozellik:<trait>` (creature trait, e.g. `ozellik:ucan` flying), `unvan:<title>`, `tanrı katili` (god-slayer), `keşif` (discovered land), `taraf:<id>`, `savas:<id>`, `suruyor` (ongoing war), `dal:<branch>`.

### Tunables (`tanimla('OLUMLU_ARAC', ...)`)

`tanimla(namespace, {key: [default, label, min, max, group]})` registers player-adjustable "World rules" and returns a live object; repeated calls with the same namespace merge into the same object (`OLUMLU_K`). Five separate `tanimla('OLUMLU_ARAC', …)` blocks exist in the file (all merged below). Percent-labelled values are coefficients (60 → ×0.6). 223 keys total; every one is used (some only from `ufuk.js`).

| key (English) | original key | default | min | max | group | English label |
|---|---|---|---|---|---|---|
| word_coin_per_epoch | kelime_tur | 2 | 0 | 20 | Language & names | coin_words: calls per epoch |
| words_per_call | kelime_adet | 8 | 1 | 40 | Language & names | Max words accepted per call (dil_kur / coin_words) |
| route_find_threshold | rota_esik | 55 | 0 | 200 | Mortal agents | find_route: success threshold for d100 + wits/rota_akil_bolen |
| unknown_world_threshold | bilinmeyen_esik | 85 | 0 | 200 | Mortal agents | find_route: threshold to sense an unknown world |
| sermon_disciple_gain_pct | vaaz_murit | 15 | 0 | 200 | Mortal agents | Successful sermon: disciple increase (%) |
| escape_chance_cap | kac_tavan | 85 | 0 | 100 | Mortal agents | Captive escape chance cap (%) |
| escape_fail_wound | kac_yara | 15 | 0 | 500 | Mortal agents | Wound (health loss) of a captive caught escaping |
| ransom_amount | fidye | 12 | 0 | 100 | Mortal agents | Wealth/prosperity that changes hands in a ransom |
| ransom_min_wealth | fidye_esik | 20 | 0 | 100 | Mortal agents | Minimum wealth to pay ransom (+fidye_refah_ek if paying with prosperity) |
| army_default_pct | ordu_yuzde | 5 | 1 | 50 | Mortal agents | raise_army: default % of population under arms |
| army_max_pct | ordu_tavan | 15 | 1 | 100 | Mortal agents | raise_army: max % of population under arms |
| army_population_deduct_pct | ordu_kayip | 100 | 0 | 100 | Mortal agents | Share (%) of conscripts subtracted from population |
| ctx_self_budget | sen_butce | 3500 | 500 | 100000 | Context budgets | Mortal context: own detail section (chars) |
| barter_ap_cost | takas_ap | 1 | 1 | 5 | Mortal agents | barter: action cost |
| barter_die | takas_zar | 30 | 1 | 200 | Mortal agents | barter: acceptance die faces (offer + relation + die >= asked) |
| barter_relation_scale | takas_iliski_olcek | 4 | 1 | 100 | Mortal agents | barter: every N relation points add +1 value |
| barter_relation_gain | takas_iliski | 8 | 0 | 100 | Mortal agents | Relation gain from a successful barter |
| barter_reject_relation_loss | takas_red_iliski | 3 | 0 | 100 | Mortal agents | Relation loss from a rejected barter |
| debt_ap_cost | borc_ap | 1 | 1 | 5 | Mortal agents | lend / repay_debt: action cost |
| debt_max_amount | borc_tavan | 30 | 1 | 100 | Mortal agents | Max amount of a single loan |
| debt_default_term | borc_vade | 3 | 1 | 50 | Mortal agents | Default loan term (epochs) |
| debt_max_term | borc_vade_tavan | 12 | 1 | 100 | Mortal agents | Longest loan term (epochs) |
| debt_lend_relation_gain | borc_iliski | 5 | 0 | 100 | Mortal agents | Relation gain from lending |
| debt_repay_relation_gain | borc_ode_iliski | 8 | 0 | 100 | Mortal agents | Relation gain from a repaid loan |
| adopt_ap_cost | evlat_ap | 1 | 1 | 5 | Mortal agents | adopt: action cost |
| adopt_relation_gain | evlat_iliski | 10 | 0 | 100 | Mortal agents | Relation gain from adoption |
| resource_discovery_per_epoch | kesif_tur | 1 | 0 | 20 | Mortal agents | discover_resource: max discoveries per mortal per epoch |
| chronicle_list_names | liste_ad | 4 | 1 | 100 | Context budgets | Max communities named in a chronicle line (rest: "and N more communities") |
| seizure_relation_loss | el_koyma_iliski | 25 | 0 | 200 | War & diplomacy | Relation loss of a community whose resource was seized (when war could not be declared) |
| ctx_character_budget | karakter_butce | 1500 | 100 | 50000 | Context budgets | Mortal context: character & way-of-life section (chars) |
| ctx_events_lines | olay_satir | 12 | 1 | 200 | Context budgets | Mortal context: lines of recent events |
| claim_per_epoch | sahiplen_tur | 1 | 0 | 20 | Mortal agents | claim: max claims per epoch |
| worship_per_epoch | tapin_tur | 1 | 0 | 20 | Religion & language | worship: max worship / god changes per epoch |
| pray_per_epoch | dua_tur | 1 | 0 | 20 | Religion & language | pray_to_creator: max prayers per epoch |
| learn_per_epoch | ogren_tur | 1 | 0 | 20 | Mortal agents | learn: max knowledge learned per epoch |
| prophecy_per_epoch | kehanet_tur | 1 | 0 | 20 | Mortal agents | prophesy: max prophecies per epoch |
| commander_per_epoch | komutan_tur | 1 | 0 | 20 | War & diplomacy | appoint_commander: max appointments per epoch |
| adopt_per_epoch | evlat_tur | 1 | 0 | 20 | Mortal agents | adopt: max adoptions per epoch |
| unknown_worlds_per_epoch | bilinmeyen_dunya_tur | 1 | 0 | 20 | Cosmos & travel | find_route: max new worlds discovered in the cosmos per epoch (worlds born by other means that epoch count too) |
| select_power_weight | ajan_guc_kat | 2 | 0 | 1000 | Mortal agents | Agent selection: score per power level |
| select_population_weight | ajan_nufus_kat | 2 | 0 | 1000 | Mortal agents | Agent selection: score per log10(population or disciples) |
| select_default_population | ajan_nufus_varsayilan | 100 | 10 | 100000000 | Mortal agents | Agent selection: assumed crowd for entities with no population/disciples |
| select_wait_weight | ajan_bekleme_kat | 2 | 0 | 1000 | Mortal agents | Agent selection: score per epoch without acting (capped by select_wait_cap) |
| sermon_default_faith | vaaz_inanc_varsayilan | 50 | 0 | 100 | Religion & language | Sermon: assumed faith of a target with no faith stat |
| commander_default_morale | komutan_moral_varsayilan | 50 | 0 | 100 | War & diplomacy | appoint_commander: assumed morale of an army with none |
| cult_min_disciples | murit_taban | 1 | 1 | 100000 | Population & growth | found_settlement / raise_army: minimum disciples a cult keeps |
| mercenary_cost | ordu_parali_servet | 10 | 0 | 100 | War & diplomacy | raise_army: wealth/prosperity cost of a mercenary army for a community without population/disciples |
| default_stat | stat_varsayilan | 40 | 0 | 100 | Mortal agents | Mortal tools: assumed stat of a party lacking it (craft, wits, strength, defense…) |
| select_chosen_bonus | ajan_secilmis | 4 | 0 | 1000 | Mortal agents | Agent selection: bonus for a "chosen one" |
| select_wait_cap | ajan_bekleme_tavan | 30 | 0 | 1000 | Mortal agents | Agent selection: max score for long inactivity |
| select_die | ajan_zar | 10 | 1 | 1000 | Mortal agents | Agent selection: random score die faces |
| select_dream_bonus | ajan_ruya | 40 | 0 | 1000 | Mortal agents | Agent selection: bonus for having a pending dream/manifestation |
| select_type_divisor | ajan_tur_pay | 3 | 1 | 100 | Mortal agents | Agent selection: one entity type gets at most ceil(count / N) agents (diversity) |
| ctx_nearby_budget | yakin_butce | 2500 | 200 | 50000 | Context budgets | Mortal context: those near you (chars) |
| ctx_knowledge_budget | bilgi_butce | 1200 | 200 | 50000 | Context budgets | Mortal context: knowledge in the world (chars) |
| ctx_mentions_budget | ani_butce | 1500 | 200 | 50000 | Context budgets | Mortal context: records mentioning you (chars) |
| ctx_languages_budget | dil_butce | 1500 | 200 | 50000 | Context budgets | Mortal context: languages of the world (chars) |
| ctx_events_budget | olay_butce | 1800 | 200 | 50000 | Context budgets | Mortal context: recent events (chars) |
| creation_power_pct | guc_oran | 80 | 1 | 100 | Mortal agents | Power level of a mortal creation: % of the creator’s power level |
| creation_power_cap | guc_tavan | 8 | 1 | 30 | Mortal agents | Max power level of a mortal creation |
| language_prevalence | dil_yayginlik | 20 | 0 | 100 | Religion & language | Prevalence of a language founded by mortals |
| dialect_prevalence | dil_lehce_yayginlik | 8 | 0 | 100 | Religion & language | Prevalence of a dialect founded by a single mortal |
| language_complexity | dil_karmasiklik | 40 | 0 | 100 | Religion & language | Complexity of a mortal-founded language |
| language_sacredness | dil_kutsallik | 20 | 0 | 100 | Religion & language | Sacredness of a mortal-founded language |
| produce_max_resources | uret_kaynak_adet | 3 | 1 | 20 | Mortal agents | Max resources used in one production |
| produce_min_abundance | uret_bolluk_esik | 10 | 0 | 100 | Mortal agents | Production: resources below this abundance are unusable |
| produce_abundance_loss | uret_bolluk_kayip | 10 | 0 | 100 | Mortal agents | Abundance lost by each resource used |
| produce_metallurgy_bonus | uret_metalurji | 15 | 0 | 100 | Mortal agents | Weapon/armor bonus for knowing metallurgy |
| produce_magic_bonus | uret_buyu | 10 | 0 | 100 | Mortal agents | Item potency bonus for knowing magic |
| produce_region_magic_divisor | uret_bolge_buyu_bolen | 8 | 1 | 1000 | Mortal agents | Item potency: + region magic / N |
| produce_craft_pct | uret_zanaat | 50 | 0 | 300 | Mortal agents | Weapon/armor value: % of craft |
| produce_potency_pct | uret_kudret | 40 | 0 | 300 | Mortal agents | Weapon/armor value: % of resources’ mean potency |
| produce_die | uret_zar | 15 | 1 | 100 | Mortal agents | Weapon/armor value die faces |
| produce_min_value | uret_en_az | 5 | 0 | 100 | Mortal agents | Min damage/protection of a weapon/armor |
| produce_side_die | uret_yan_zar | 10 | 1 | 100 | Mortal agents | Damage of non-weapons and protection of non-armor: die faces |
| produce_item_potency_pct | uret_kudret_orani | 60 | 0 | 300 | Mortal agents | Item potency: % of resources’ mean potency |
| produce_item_potency_die | uret_kudret_zar | 20 | 1 | 100 | Mortal agents | Item potency die faces |
| produce_curse_die | uret_lanet_zar | 12 | 1 | 100 | Mortal agents | Item curse: die faces |
| produce_curse_minus | uret_lanet_eksi | 4 | 0 | 100 | Mortal agents | Item curse: subtracted from the die |
| produce_masterwork_threshold | uret_usta | 60 | 0 | 200 | Mortal agents | damage+protection >= this → chronicle says "masterwork" |
| produce_sturdy_threshold | uret_saglam | 30 | 0 | 200 | Mortal agents | damage+protection >= this → chronicle says "sturdy" |
| build_grandeur_pct | insa_ihtisam | 70 | 0 | 300 | Mortal agents | Structure grandeur: % of craft |
| build_grandeur_die | insa_ihtisam_zar | 25 | 1 | 100 | Mortal agents | Structure grandeur: die faces |
| build_sturdiness_pct | insa_saglamlik | 60 | 0 | 300 | Mortal agents | Structure sturdiness: % of craft |
| build_sturdiness_die | insa_saglamlik_zar | 30 | 1 | 100 | Mortal agents | Structure sturdiness: die faces |
| build_architecture_bonus | insa_mimarlik | 20 | 0 | 100 | Mortal agents | Grandeur & sturdiness bonus for knowing architecture |
| build_function_base | insa_islev_taban | 40 | 0 | 100 | Mortal agents | Structure function: base |
| build_function_die | insa_islev_zar | 40 | 1 | 100 | Mortal agents | Structure function: die faces |
| build_cost | insa_bedel | 4 | 0 | 100 | Mortal agents | Prosperity and wealth lost by building |
| culture_max_related | kultur_ilgili_adet | 4 | 0 | 20 | Mortal agents | Max related entities in a culture creation |
| artwork_base | eser_taban | 20 | 0 | 100 | Mortal agents | Artwork fame and influence: base |
| artwork_die | eser_zar | 40 | 1 | 100 | Mortal agents | Artwork fame and influence: die faces |
| law_rigidity_base | kanun_katilik_taban | 30 | 0 | 100 | Mortal agents | Law rigidity: base |
| law_rigidity_die | kanun_katilik_zar | 60 | 1 | 100 | Mortal agents | Law rigidity: die faces |
| law_justice_base | kanun_adalet_taban | 20 | 0 | 100 | Mortal agents | Law justice: base |
| law_justice_die | kanun_adalet_zar | 70 | 1 | 100 | Mortal agents | Law justice: die faces |
| tradition_prevalence | gelenek_yayginlik | 35 | 0 | 100 | Mortal agents | Prevalence of a new tradition or legend |
| tradition_rigidity | gelenek_katilik | 50 | 0 | 100 | Mortal agents | Rigidity of a new tradition or legend |
| discovery_abundance_base | kesif_bolluk_taban | 40 | 0 | 100 | Economy | Discovered resource abundance: base |
| discovery_abundance_die | kesif_bolluk_zar | 40 | 1 | 100 | Economy | Discovered resource abundance: die faces |
| discovery_value_base | kesif_deger_taban | 20 | 0 | 100 | Economy | Discovered resource value: base |
| discovery_value_die | kesif_deger_zar | 50 | 1 | 100 | Economy | Discovered resource value: die faces |
| discovery_potency_base | kesif_kudret_taban | 10 | 0 | 100 | Economy | Discovered resource potency: base |
| discovery_potency_die | kesif_kudret_zar | 50 | 1 | 100 | Economy | Discovered resource potency: die faces |
| migration_pct | goc_oran | 12 | 0 | 100 | Population & growth | New settlement migrants: % of population |
| migration_min | goc_en_az | 20 | 1 | 100000 | Population & growth | Minimum migrants for a new settlement |
| new_settlement_prosperity | yeni_kent_refah | 35 | 0 | 100 | Population & growth | Prosperity of a mortal-founded settlement |
| new_settlement_defense | yeni_kent_savunma | 25 | 0 | 100 | Population & growth | Defense of a mortal-founded settlement |
| new_settlement_faith | yeni_kent_inanc | 60 | 0 | 100 | Population & growth | Faith of a mortal-founded settlement |
| trade_relation_gain | ticaret_iliski | 10 | 0 | 100 | War & diplomacy | Relation gain from establishing trade |
| war_relation_loss | savas_iliski | 25 | 0 | 200 | War & diplomacy | Relation loss from declaring war |
| war_patron_relation_loss | savas_hami_iliski | 5 | 0 | 200 | War & diplomacy | Relation loss between the two sides’ gods on a war declaration |
| worship_foreign_attitude_loss | tapin_yabanci_tutum | 5 | 0 | 200 | Religion & language | Attitude loss of an abandoned foreign god |
| worship_switch_relation_loss | tapin_iliski | 10 | 0 | 200 | Religion & language | Relation loss between old and new god on a god switch |
| knowledge_max_bases | bilgi_temel_adet | 3 | 0 | 20 | Mortal agents | Max base knowledge for new knowledge |
| knowledge_craft_threshold | bilgi_zanaat_esik | 60 | 0 | 100 | Mortal agents | Craft above this → developed knowledge is one level higher |
| knowledge_level_cap | bilgi_seviye_tavan | 10 | 1 | 100 | Mortal agents | Max level of mortal-developed knowledge |
| knowledge_prevalence | bilgi_yayginlik | 10 | 0 | 100 | Mortal agents | Prevalence of newly developed knowledge |
| diplomacy_default_power | dip_guc_varsayilan | 30 | 0 | 100 | War & diplomacy | Diplomatic power: assumed power of a party with none |
| diplomacy_population_weight | dip_nufus_kat | 8 | 0 | 100 | War & diplomacy | Diplomatic power: + log10(population) × N |
| diplomacy_relation_divisor | dip_iliski_bolen | 4 | 1 | 1000 | War & diplomacy | Diplomacy roll: − relation / N |
| diplomacy_alliance_threshold | dip_ittifak_esik | 60 | 0 | 200 | War & diplomacy | Alliance or marriage offer acceptance threshold (d100) |
| diplomacy_alliance_relation_gain | dip_ittifak_iliski | 15 | 0 | 100 | War & diplomacy | Relation gain from an accepted alliance |
| diplomacy_marriage_relation_gain | dip_evlilik_iliski | 20 | 0 | 100 | War & diplomacy | Relation gain from an accepted marriage |
| diplomacy_refusal_relation_loss | dip_ret_iliski | 3 | 0 | 100 | War & diplomacy | Relation loss from a refused alliance or marriage |
| diplomacy_peace_threshold | dip_baris_esik | 45 | 0 | 200 | War & diplomacy | Peace offer acceptance threshold (d100) |
| diplomacy_peace_relation_gain | dip_baris_iliski | 15 | 0 | 100 | War & diplomacy | Relation gain from accepted peace |
| tribute_superiority_pct | harac_ustunluk | 120 | 0 | 1000 | War & diplomacy | Power superiority required for tribute (% of the other side’s power) |
| tribute_insolence_relation_loss | harac_red_iliski | 25 | 0 | 200 | War & diplomacy | Relation loss from tribute insolence |
| tribute_payer_loss | harac_kayip | 10 | 0 | 100 | War & diplomacy | Wealth/prosperity lost by the tribute payer |
| tribute_receiver_gain | harac_kazanc | 8 | 0 | 100 | War & diplomacy | Wealth/prosperity gained by the tribute receiver |
| tribute_relation_loss | harac_iliski | 15 | 0 | 200 | War & diplomacy | Relation loss from tribute |
| adventure_die | macera_zar | 30 | 1 | 200 | Heroes & mortals | Item seizure: die faces for both sides |
| adventure_fail_wound | macera_yara | 30 | 0 | 300 | Heroes & mortals | Wound of a hero failing to seize an item |
| route_wits_divisor | rota_akil_bolen | 3 | 1 | 1000 | Cosmos & travel | Route roll: + wits / N (also used by explore_land) |
| gate_speed | kapi_hiz | 90 | 0 | 100 | Cosmos & travel | Found ancient gate: speed |
| gate_range | kapi_menzil | 100 | 0 | 100 | Cosmos & travel | Found ancient gate: range |
| gate_armor | kapi_zirh | 60 | 0 | 100 | Cosmos & travel | Found ancient gate: armor |
| gate_strangeness_base | kapi_tuhaflik | 50 | 0 | 100 | Cosmos & travel | Found ancient gate: strangeness base |
| gate_strangeness_die | kapi_tuhaflik_zar | 40 | 1 | 100 | Cosmos & travel | Found ancient gate: strangeness die faces |
| gate_power | kapi_guc | 5 | 1 | 30 | Cosmos & travel | Found ancient gate: power level |
| ship_ore_divisor | gemi_maden_bolen | 3 | 1 | 1000 | Cosmos & travel | Ship craft: + economy ore / N (label says "miners") |
| ship_metallurgy_bonus | gemi_metalurji | 15 | 0 | 100 | Cosmos & travel | Ship craft: metallurgy bonus |
| ship_speed_base | gemi_hiz_taban | 30 | 0 | 100 | Cosmos & travel | Ship speed: base |
| ship_speed_craft_divisor | gemi_hiz_bolen | 3 | 1 | 1000 | Cosmos & travel | Ship speed: + craft / N |
| ship_speed_die | gemi_hiz_zar | 20 | 1 | 100 | Cosmos & travel | Ship speed: die faces |
| ship_range_base | gemi_menzil_taban | 40 | 0 | 100 | Cosmos & travel | Ship range: base |
| ship_range_die | gemi_menzil_zar | 40 | 1 | 100 | Cosmos & travel | Ship range: die faces |
| ship_crew_base | gemi_murettebat_taban | 50 | 0 | 100000 | Cosmos & travel | Ship crew: base |
| ship_crew_die | gemi_murettebat_zar | 400 | 1 | 100000 | Cosmos & travel | Ship crew: die faces |
| ship_armor_base | gemi_zirh_taban | 20 | 0 | 100 | Cosmos & travel | Ship armor: base |
| ship_armor_craft_divisor | gemi_zirh_bolen | 4 | 1 | 1000 | Cosmos & travel | Ship armor: + craft / N |
| ship_armor_die | gemi_zirh_zar | 20 | 1 | 100 | Cosmos & travel | Ship armor: die faces |
| ship_strangeness_die | gemi_tuhaflik_zar | 60 | 1 | 100 | Cosmos & travel | Ship strangeness: die faces |
| ship_ore_cost | gemi_maden | 20 | 0 | 100 | Cosmos & travel | Ore subtracted from the community economy by shipbuilding (label says "miners") |
| expedition_default_pct | sefer_yuzde | 10 | 1 | 100 | Cosmos & travel | Expedition: default % of population departing |
| expedition_max_pct | sefer_yuzde_tavan | 30 | 1 | 100 | Cosmos & travel | Expedition: max % of population departing |
| expedition_min_people | sefer_en_az | 20 | 1 | 100000 | Cosmos & travel | Min people for a colony or conquest expedition |
| tame_charisma_divisor | evcil_karizma_bolen | 3 | 1 | 1000 | Creatures | Taming skill: + charisma / N |
| tame_skill_die | evcil_zar | 60 | 1 | 200 | Creatures | Taming skill: die faces |
| tame_default_danger | evcil_tehlike_varsayilan | 30 | 0 | 100 | Creatures | Taming: assumed danger of a species with none |
| tame_danger_divisor | evcil_tehlike_bolen | 150 | 1 | 10000 | Creatures | Taming difficulty: danger / (N / 100) |
| tame_default_intelligence | evcil_zeka_varsayilan | 20 | 0 | 100 | Creatures | Taming: assumed intelligence of a species with none |
| tame_megafauna_penalty | evcil_megafauna | 40 | 0 | 200 | Creatures | Extra difficulty for taming megafauna |
| tame_difficulty_die | evcil_zor_zar | 30 | 1 | 200 | Creatures | Taming difficulty: die faces |
| tame_attack_divisor | evcil_ofke_bolen | 200 | 1 | 10000 | Creatures | Untamed species attack chance: danger / N |
| tame_attack_loss_pct | evcil_kayip | 5 | 0 | 100 | Creatures | Population/health loss when attacked (%) |
| ruin_scribe_weight | kalinti_katip | 2 | 0 | 100 | Mortal agents | Ruin search: scribe class multiplier |
| ruin_die | kalinti_zar | 50 | 1 | 200 | Mortal agents | Ruin search: die faces |
| ruin_knowledge_threshold | kalinti_bilgi_esik | 70 | 0 | 300 | Mortal agents | At or above: lost knowledge found |
| ruin_item_threshold | kalinti_esya_esik | 55 | 0 | 300 | Mortal agents | At or above: unowned item found |
| ruin_curse_threshold | kalinti_lanet_esik | 35 | 0 | 300 | Mortal agents | Below: searchers are cursed |
| sabotage_die | sabotaj_zar | 40 | 1 | 200 | War & diplomacy | Sabotage: die faces for both sides |
| sabotage_caught_margin | sabotaj_yakalanma | 15 | 0 | 200 | War & diplomacy | Saboteur caught if target vigilance exceeds cunning by this much |
| poison_population_loss_pct | zehir_nufus | 10 | 0 | 100 | War & diplomacy | Poison: population/disciple loss (%) |
| poison_health_loss | zehir_can | 40 | 0 | 300 | War & diplomacy | Poison: health loss |
| arson_loss | kundak | 12 | 0 | 100 | War & diplomacy | Arson: prosperity, defense and wealth loss |
| sabotage_caught_relation_loss | sabotaj_iliski | 20 | 0 | 200 | War & diplomacy | Relation loss from caught sabotage |
| sermon_base_chance | vaaz_taban | 35 | 0 | 100 | Religion & language | Sermon success chance: base (%) |
| sermon_default_influence | vaaz_etki_varsayilan | 30 | 0 | 100 | Religion & language | Sermon: assumed influence of a cult with none |
| sermon_god_charisma_divisor | vaaz_tanri_bolen | 4 | 1 | 1000 | Religion & language | Sermon chance: + god charisma / N |
| sermon_old_god_divisor | vaaz_eski_bolen | 3 | 1 | 1000 | Religion & language | Sermon chance: − target’s old god charisma / N |
| sermon_faith_divisor | vaaz_inanc_bolen | 5 | 1 | 1000 | Religion & language | Sermon chance: − target faith / N |
| sermon_relation_loss | vaaz_iliski | 10 | 0 | 200 | Religion & language | Relation loss with the god that lost a worshipper to a sermon |
| challenge_damage_divisor | meydan_hasar_bolen | 4 | 1 | 1000 | Heroes & mortals | Challenge god: weapon power = damage / N |
| challenge_potency_divisor | meydan_kudret_bolen | 6 | 1 | 1000 | Heroes & mortals | Challenge god: + item potency / N |
| challenge_wits_divisor | meydan_akil_bolen | 3 | 1 | 1000 | Heroes & mortals | Challenge god: + wits / N |
| challenge_die | meydan_zar | 40 | 1 | 200 | Heroes & mortals | Challenge god: die faces for both sides |
| challenge_god_level_weight | meydan_tanri_seviye | 5 | 0 | 100 | Heroes & mortals | Challenge god: god power per level |
| challenge_untouchable_bonus | meydan_dokunulmaz | 15 | 0 | 100 | Heroes & mortals | Challenge god: bonus for an "untouchable" god |
| godslay_margin | tanri_katli_fark | 40 | 0 | 300 | Heroes & mortals | A mortal winning by this margin kills a fading god |
| godslay_existence_threshold | tanri_katli_varlik | 35 | 0 | 100 | Heroes & mortals | A god with existence below this can die at mortal hands |
| god_default_existence | tanri_varlik_varsayilan | 60 | 0 | 100 | Heroes & mortals | Assumed existence of a god with none |
| godslayer_charisma_gain | tanri_katli_karizma | 25 | 0 | 100 | Heroes & mortals | God-slayer charisma gain |
| god_wound_pct | tanri_yara | 25 | 0 | 100 | Heroes & mortals | Wound of a god beaten by a mortal: % of max health |
| god_wound_fame_loss | tanri_yara_un | 8 | 0 | 100 | Heroes & mortals | Fame loss of a god beaten by a mortal |
| god_wounder_charisma_gain | tanri_yara_karizma | 15 | 0 | 100 | Heroes & mortals | Charisma gain of the mortal who wounded a god |
| challenge_death_chance | tanri_olum_sans | 50 | 0 | 100 | Heroes & mortals | Chance (%) a defeated challenger dies (otherwise cursed) |
| god_crush_fame_gain | tanri_ezme_un | 4 | 0 | 100 | Heroes & mortals | Fame gained by a god crushing a defiant mortal |
| deny_foreign_attitude_loss | inkar_tutum | 10 | 0 | 200 | Religion & language | Attitude loss of a denied foreign god |
| deny_foreign_faith_loss | inkar_inanc | 5 | 0 | 100 | Religion & language | Faith loss of a denied foreign god |
| deny_son_existence_loss | inkar_varlik | 6 | 0 | 100 | Religion & language | Existence loss of a denied son |
| prophecy_max_related | kehanet_ilgili_adet | 3 | 0 | 20 | Religion & language | Max related entities in a prophecy |
| prophecy_certainty_base | kehanet_kesinlik | 30 | 0 | 100 | Religion & language | Prophecy certainty: base (+ wits / 2) |
| escape_default_stat | kac_varsayilan | 30 | 0 | 100 | Mortal agents | Escape: assumed agility/wits of a captive lacking them |
| escape_wits_divisor | kac_akil_bolen | 3 | 1 | 1000 | Mortal agents | Escape chance: + wits / N |
| escape_defense_divisor | kac_savunma_bolen | 3 | 1 | 1000 | Mortal agents | Escape chance: − captor defense / N |
| escape_min_chance | kac_taban | 5 | 0 | 100 | Mortal agents | Minimum escape chance (%) |
| ransom_prosperity_extra | fidye_refah_ek | 5 | 0 | 100 | Mortal agents | Ransom: threshold surcharge when paying with prosperity |
| ransom_relation_gain | fidye_iliski | 5 | 0 | 100 | Mortal agents | Relation gain from paid ransom |
| rescue_die | kurtar_zar | 40 | 1 | 200 | Mortal agents | Rescue raid: die faces for both sides |
| army_default_power | ordu_guc_varsayilan | 30 | 0 | 100 | War & diplomacy | Army: assumed strength of a community without population |
| army_power_multiplier | ordu_guc_kat | 60 | 0 | 100000 | War & diplomacy | Army: base for a community without population = strength × N |
| army_min_soldiers | ordu_en_az | 30 | 1 | 100000 | War & diplomacy | Minimum soldiers in a raised army |
| army_morale_base | ordu_moral | 50 | 0 | 100 | War & diplomacy | New army morale: base |
| army_morale_die | ordu_moral_zar | 25 | 1 | 100 | War & diplomacy | New army morale: die faces |
| army_equipment_base | ordu_techizat | 20 | 0 | 100 | War & diplomacy | New army equipment: base |
| army_metallurgy_bonus | ordu_metalurji | 15 | 0 | 100 | War & diplomacy | Army equipment bonus for knowing metallurgy |
| army_craft_divisor | ordu_zanaat_bolen | 4 | 1 | 1000 | War & diplomacy | Army equipment: + craft / N |
| army_experience_war | ordu_deneyim_savas | 30 | 0 | 100 | War & diplomacy | Experience of a new army of a community knowing war-craft |
| army_experience | ordu_deneyim | 10 | 0 | 100 | War & diplomacy | Experience of a new army |
| commander_charisma_divisor | komutan_karizma_bolen | 10 | 1 | 1000 | War & diplomacy | Commander morale contribution: charisma / N |
| barter_max_items | takas_adet | 3 | 1 | 20 | Mortal agents | Max things on one side of a barter |

#### Other constants and cross-module tunables read by this module

| Where | Key | Default | Meaning here |
|---|---|---|---|
| rules.js `OLUMLU_AJAN` (plain constant, NOT tunable) | `varsayilan` | 4 | default mortal agents per epoch when `world.olumlu_sayisi` is null (a stale comment calls it "how many years per epoch") |
| | `ap` | 3 | action points (AP) per mortal turn |
| | `maxTurns` | 12 | max LLM turns per agent session |
| | `turler` | `[halk, hizip, tarikat, yerlesim, olumlu, tur]` | entity types eligible to act |
| | `zeka_esigi` | 55 | min `zeka` for a species (`tur`) to act |
| world row | `olumlu_sayisi` | null | player-set agents per epoch (0 disables the phase) |
| world row | `olumlu_paralel` | null→1 | concurrent mortal turns |
| `dunyalar.olumlu_ajan` | per-world manual agent count | null = automatic share |
| `SINIR` (rules.js) | `nufus_taban` 10, `halk_nufus_taban` 100, `kent_nufus_tavan` 2,000,000, `nufus_tavan` 50,000,000, `murit_tavan` 10,000,000, `ordu_tavan` 10,000,000, `can_tavan` 300 | | floors/caps |
| `KURAL` (rules.js) | `can_taban` 50, `can_dayaniklilik` 150 | | son max health = can_taban + can_dayaniklilik/100 × endurance (used for god wound size) |
| `GUC_SEVIYELERI` | `[1, 3, 5]` | | son power i unlocks at level `GUC_SEVIYELERI[i]` |
| `BAGLAM` (world.js) | `olumlu_baglam` 12000, `bolum_taban` 600, `arac_kat` 3 | | total mortal context chars; min share per section; multiplier for the `dunyaya_bak` read tool |
| `KORKU` (korku.js) | `bulaniklik_esik` 40 | | sanity below this → "clouded mind" paragraph in system prompt |
| `YARATIK` (yaratik.js) | `kimera_dokuma_mesafe` 4 | | max location-chain steps for chimera weaving |
| `KESIF` (ufuk.js) | `arac_tur` 1, `arac_esik` 45, `arac_bilgi_ek` 15 (+ `oncu_*`, stat bases) | | explore_land tool |
| `OLUM` (olum.js) | `ayin_tur` 1, `dua_adanmislik` 4, `servet_bedel` 15, `servet_adanmislik` 10, `kurban_nufus` 3, `kurban_adanmislik` 20, `can_kurbani_adanmislik` 35, `hac_carpan` 200 | | resurrection rite tool (values shown in its description) |
| `MUDAHALE` (rules.js) | `bilgi_yayginlik` 8 | | `ogret()` adds this prevalence to a knowledge every time someone learns it |

### Region and adjacency helpers (exported)

Locations form a chain via `konum_id` (place → region, settlement → place/region, …).

- `ustBolgeHam(v)`: walk `v → getVarlik(v.konum_id) → …` at most 10 steps; return the **last** (topmost) entity with `tur='bolge'` seen, else null. (Regions can be nested; the top one wins.)
- `ustBolgeId(v)` ("top region id"): memoized per `konumSurumu()` (a global location-version counter that changes whenever any `konum_id` changes). If no version is available or `v.id` missing → compute directly. Cache: `Map(entityId → regionId|null)`, cleared when the version changes.
- `ustBolge(v)`: the region entity for `ustBolgeId(v)`, read fresh each time (its stats such as fertility may have changed).
- `ayniBolge(a, b)` ("same region"): true only if both have a known top region and the ids are equal. An entity with no region is never in the "same region" as anything (prevents two regionless entities from matching via `undefined === undefined` across worlds).
- `yakinMi(a, b)` ("near"):
  1. `ra = ustBolge(a)`, `rb = ustBolge(b)`; if either null → false.
  2. same id → true.
  3. `kom(x) = haritaHesapla().bilgi[x].komsular` (map adjacency list). If `rb ∈ kom(ra)` or `ra ∈ kom(rb)` → true.
  4. Seafarers: if the active laws of `a`'s world (`aktifYasalar(a.dunya_id ?? 1)`) do NOT contain `deniz_yasagi` (sea ban) AND (`a` or `b` knows branch `denizcilik` (seafaring)) → true if some neighbor `m` of `ra` has `rb` in `kom(m)` (two steps, "across a sea").
  5. else false.
- Private helpers:
  - `sahipOldugu(vId, tur?)`: entities that `vId` owns (active `sahip` bonds v→v), canon only, optionally filtered by type.
  - `zanaatGucu(v)` ("craft power") = first non-null of `zanaat, servet, akil, zeka, refah, etki`, else `default_stat`.
  - `servetAnahtari(v)` = `'servet'` if the stat exists, else `'refah'` if it exists, else null (which stat acts as "money").
  - `orduOf(me)` = first canon `ordu` whose tags JSON contains `"taraf:{me.id}"` (LIKE match).
  - `esirMi(v)` (exported, "is captive"): the captor entity = source of an active `esir` bond (v→v) whose target is `v`; else null.
  - `ogrenebilirMi(me, o)` (exported, "can learn from"): active bond of type `ticaret` OR `muttefik` OR `yonetir` between them (either direction) OR `ayniBolge(me, o)`.
  - `borcVadeleri(cag)` (exported): runs `medeniyet.borcGecikmeleri(cag)` in a transaction (the single owner of overdue-debt logic; also run by the engine every epoch).

### Agent selection: who acts this epoch

`ajanAdaylari(sayi)` ("agent candidates"):
1. `cag = world.cag`.
2. Candidates = all canon entities with `(son_eylem_cag || 0) < cag` AND `tur ∈ OLUMLU_AJAN.turler` AND (`tur != 'tur'` OR `statlar.zeka >= 55`).
3. Worlds = rows of `dunyalar` with `kesif != 'unutulmus'` (not forgotten).
4. If fewer than 2 worlds → return `ajanSec(candidates, sayi, cag)`.
5. Otherwise group candidates by `dunya_id` (null → first world; an entity whose world is not in the list — e.g. a forgotten world — is also put into the **first** world's group).
6. `pay = dunyaPaylari([{id, elle: world.olumlu_ajan, aday: groupSize}], sayi)`.
7. For each world: `ajanSec(group, pay[id] || 0, cag)`; concatenate.
8. Append any candidate tagged `ajan seçili` not already selected.

`dunyaPaylari(list, total)` ("world shares"), largest-remainder apportionment:
1. Manual worlds (`elle != null`): `share = min(elle, aday)`. Note: manual shares are NOT subtracted from `total`; automatic worlds share the full `total` on top of the manual ones.
2. `auto` = worlds with `elle == null` and `aday > 0`. If none or `total <= 0` → return.
3. `adaySum = Σ auto.aday`; `x_i = total × aday_i / adaySum`.
4. `share_i = min(aday_i, max(total >= |auto| ? 1 : 0, floor(x_i)))` (every auto world gets at least 1 when there are enough agents to go round).
5. `remaining = total − Σ share_i` (may be negative; then nothing more is distributed).
6. Sort auto worlds by fractional part of `x_i` descending; give +1 to each while `remaining > 0` and `share < aday`.

`ajanSec(candidates, n, cag)` ("pick agents"):
1. If `n <= 0`: return only candidates tagged `ajan seçili`.
2. Score each candidate:
   ```
   p = guc_seviyesi × select_power_weight
     + log10(max(10, nufus || murit || select_default_population)) × select_population_weight
     + (tag 'seçilmiş' ? select_chosen_bonus : 0)
     + min(select_wait_cap, (cag − (son_eylem_cag || 0)) × select_wait_weight)
     + d(select_die)
     + (bekleyenRuya(id) ? select_dream_bonus : 0)       // unread message with niyet 'ruya' or 'tezahur'
     + (tag 'ajan seçili' ? 1000 : 0)                     // hard-coded, not tunable
   ```
   Sort descending.
3. Pass 1 (diversity): `typeCap = max(1, ceil(n / select_type_divisor))`; walk the list, skip a candidate if its type already has `typeCap` picks; stop at `n`.
4. Pass 2: fill up to `n` from the sorted list ignoring the cap.

Single-world path does not append extra `ajan seçili` candidates beyond `n` (multi-world path does).

### Mortal turn runner: `olumluTuru(v, onEvent)`

1. `w = getWorld()`. `yarim` ("half-done") = `v.tur_cag == w.cag && v.tur_ap != null` (a turn of this epoch was interrupted and its state persisted).
2. `try borcVadeleri(w.cag)` (overdue debts are chronicled before the mortal thinks; errors ignored).
3. `ctx = { cag: w.cag, ap: yarim ? v.tur_ap : OLUMLU_AJAN.ap, yaratimlar: [], ...(yarim ? turCtxOku(v.tur_ctx) : {}) }` — per-turn counters (e.g. `kelime`, `kesif`, `tapindi`, …) are restored from the persisted JSON when resuming.
4. Persist `varliklar.tur_cag = cag, tur_ap = ctx.ap, tur_ctx = (yarim ? v.tur_ctx : null)`.
5. `model = modelFor('yaygin')`. Emit event `{kind:'olumlu_basla', varlik_id, ad, tur, model, yarim}`.
6. `ruya` = unread `mesajlar` with `kime_tip='v', kime_id=v.id, niyet='ruya'` (dreams; NOT marked read yet, so a crashed turn sees them again). `tezahurler` = unread `mesajlar` with `niyet='tezahur'` (waking manifestations of the creator, from `tanriguc.tezahurIc`).
7. Build `server = buildOlumluServer(v.id, ctx)` and call `agentTurn({...})` with:
   - `ad: "Mortal turn: {v.ad}"`, `model`, `system: sistemMetni(v, w, server.aracBedelleri)`, `server`, `serverName: 'olumlu'`, `maxTurns: 12`,
   - `sunucuYap`: builds a fresh server (same `ctx`) for each continuation session,
   - `prompt: istem(yarim ? RESUME_NOTE : '')`,
   - `tamamMi(m)`: the turn is complete when `sozuAyikla(m)` returns a non-empty utterance,
   - `devamPromptu(done, reason)`: `istem("Your turn was left unfinished ({reason}).\n\n" + yapildiMetni(done))`,
   - `onEvent`: forwards with `varlik_id`, `ogul_ad: v.ad`.
   `agentTurn` semantics (llm.js): if a session crashes with no successful tool call it is retried from scratch with the same prompt; if it crashes/times out/hits maxTurns/ends without an utterance after having done something, a continuation session opens with `devamPromptu(list of done actions, reason)`.
8. `soz = sozuAyikla(res.metin)` (utterance extraction: text inside `«…»`; else text after a `söz:` / `söz (kroniğe):` marker; strip surrounding quotes — LANGUAGE-SPECIFIC marker word).
9. Mark the fetched dreams and manifestations read (`okundu=1`, only those ids).
10. `UPDATE varliklar SET son_eylem_cag = cag, tur_ap = NULL`.
11. If the original `v` had tag `ajan seçili`, remove it (re-reading current tags).
12. If `soz`: chronicle `kind 'soz'`: `{v.ad}: "{soz[0:600]}"`, entity ids `[v.id, ...ctx.yaratimlar]`.
13. Emit `{kind:'olumlu_bitti', varlik_id, ad, soz, yaratimlar, durum: res.durum}`; return `ctx.yaratimlar`.

### Prompts (translated in full)

The original instructs the model to "think and speak in Turkish"; the new app is English-only, so replace with "in English". All prompt text is passed through `ekDuzelt` (Turkish suffix/apostrophe fixer) — LANGUAGE-SPECIFIC: drop.

#### System prompt — `sistemMetni(v, w, costs)`

Variables: `{name}` = `v.ad`; `{typeLabel}` = `VARLIK_TURLERI[v.tur].ad` lowercased (e.g. "people", "faction", "named mortal", "species"); `{subtype}` = `v.alt_tur || typeLabel`; `{world}` = `w.ad`; `{AP}` = `OLUMLU_AJAN.ap`.

```
You are {name}: a {typeLabel} in the world of {world} ({subtype}). You are not a god; you are a mortal, or a community of mortals.
You are not an AI; you live out the shared will of this community/being. You think and speak in English.
You have interests: to survive, to grow, to grow rich, to be worthy of your god, to take revenge on your enemies, to make your name endure.
In this epoch you have {AP} action points; points you do not use do not carry over to the next epoch — they burn when the epoch ends.{CLOUDED} {COSTS}{CAPTIVE}
RULES:
- Ground everything you do in your land, your resources, your religion and your past. You cannot forge a weapon from a resource you do not own; you cannot build a harbor on a shore you have not seen.
- Derive names from your own language; if you have no language, first create one with dil_kur. Give new words an origin.
- No clichés: every item, work and tradition must have a concrete material, a cost, a strange detail.
- Your final message must be ONLY a 1–2 sentence utterance inside «…», in the voice of your community. Do not summarize your actions; do not mention tool names or #numbers.{TICS}{MOTIFS}
```

- `{CLOUDED}` (only if `sagduyu(v) < KORKU.bulaniklik_esik`):
  `\nYOUR MIND IS CLOUDED (sanity {v.statlar.sagduyu}): you hear voices and misread signs; your decisions may be strange, fearful or overly bold. Live this — not as deliberate madness, but as a delusion you believe in.`
- `{COSTS}`: if `costs` given: `Actions that cost a point: {costs.harcar joined ", "}. Actions that cost nothing: {costs.harcamaz joined ", "}.` Fallback (never used in practice): `Production, building, discovery, developing knowledge, migration/settlement, culture, trade, diplomacy, adventure, sabotage, preaching, war, challenging a god and denial cost an action; coining words, learning, worshipping, claiming and reading do not.`
- `{CAPTIVE}` (if `esirMi(v)`): `\nYOU ARE A CAPTIVE: {captor.ad} holds you prisoner. You can only try to escape (kac) or speak; you cannot take any other action.`
- `{TICS}` (if `ortakTikler()` non-empty — recurring words across recent utterances of sons and mortals, from agents.js): `\n- Words that have become tics in utterances: «w1», «w2», … Do NOT USE these, or words derived from the same root, in your utterance.`
- `{MOTIFS}` (if `motifYasagi(v.dunya_id)` non-empty, from world.js): `\n- ` + up to two sentences:
  - `TIRED IMAGES (repeated too often in the world's texts): {list}. Do NOT USE these or their synonyms; instead find images specific to this being and this corner of the world, never used before (another sense, another material, another profession, another season).`
  - `WORDS OF ANOTHER WORLD (the worn images of the home world; do not carry them into this world): {list}.`

`costs` (`srv.aracBedelleri`) is derived from tool descriptions: a tool is "free" iff its description matches `/Ücretsiz|[Ee]ylem harcamaz|eylem hakkı HARCAMAZ/` and does not match `/\b\d eylem\b/` (`bedavaMi`). New design: make cost explicit tool metadata instead of parsing descriptions.

#### User prompt — `istem(extra)`

```
Epoch {w.cag}. It is your turn.

{MANIFESTATION}{DREAM}{CONTEXT}

OPPORTUNITIES:
{olumluFirsatlari(currentEntity) or "(no notable opportunity)"}

{extra}{CLOSING}
```
- `{MANIFESTATION}` (if any unread `tezahur`): `THE CREATOR APPEARED TO YOU ({w.tanri_adi} appeared before your eyes while you were awake and spoke with you; this is not a dream but a plain command and a sign; you must act accordingly):\n"{msg1}"\n"{msg2}"…\n\n`
- `{DREAM}` (if any unread `ruya`): `DREAM FROM YOUR GOD (the creator god {w.tanri_adi} appeared to you in your dream; how you interpret it and whether you obey is up to you, but you cannot remain unaffected):\n"{msg}"…\n\n`
- `{CONTEXT}` = `baglamMetni(currentEntity, w)` (below). The current entity is re-read each time the prompt is built.
- `olumluFirsatlari` (firsatlar.js) lists concrete opportunities; errors → empty.
- `{CLOSING}`: `ctx.ap > 0` → `Use your {ctx.ap} actions in your community's interest, then speak your word.` else `You have no actions left; only speak your word.`
- `RESUME_NOTE` (first prompt when `yarim`): `Your turn was interrupted earlier; continue from where you left off.\n\n`
- Continuation: `extra = "Your turn was left unfinished ({reason}).\n\n" + yapildiMetni(done)` where `yapildiMetni(done)` (if non-empty) = `WHAT YOU HAVE ALREADY DONE THIS EPOCH (they stand in the world; do not repeat them, build on them; your utterance should carry this epoch's tone but not list what you did):\n- {item}\n- …\n\n`.

Expected output: free text whose final message contains the utterance in `«…»`. Tool calls happen via MCP.

#### Context block — `baglamMetni(v, w, {tam=false})`

`dId = v.dunya_id ?? 1`; `region = ustBolge(v)`; `neighbors` = canon entities ≠ v, `tur != 'bolge'`, same top region, first 40; `lang = konusulanDil(v)`; `god = hami(v)` (active `tapar` → son; fallback: the son who created `v`); `resources/items = sahipOldugu(v.id, 'kaynak'|'esya')`; `mapInfo = haritaHesapla().bilgi[region.id]`; `mentions` = last 10 chronicle rows whose `varlik_ids` JSON array contains exactly `v.id` (exact match via `json_each`, not LIKE), oldest first; `allKnowledge` = canon `teknoloji` of this world.

Sections in order (empty ones dropped), each heading translated:
1. `dunyaBasligi(w, dId, {kisa:true})` — short world header (world.js).
2. `dunyaSatiri(dId)` — one-line world summary (world.js).
3. `\nYOU:\n{budget(varlikDetay(v.id), ctx_self_budget, hint "look at yourself with varlik_incele")}`
4. If `v.derinlik.ozel` (depth/character object): `\nYOUR CHARACTER AND WAY OF LIFE:\n- {key}: {value}…` budget `ctx_character_budget`, same hint.
5. `\nYOUR GOD: ` + one of: `son#{id} {name}, {title} ({domain1}/{domain2})` | `foreign god {y.ad}[, {y.unvan}] (yabanci#{y.id}; not of the pantheon)` | `you do not yet worship anyone`.
6. If rows in `halk_inanc` for this entity (per-people names/tellings of gods): `\nTHE GODS IN YOUR TELLING (refer to them by these names when you speak):\n- {i.ad} (son#{i.ogul_id}): {i.anlati}`.
7. `\nYOUR LANGUAGE: ` + `#{id} {name}. From your lexicon: {word} = {meaning}; … (up to 30 via sozlukDil) or "empty"` | `you have no language yet; you can give birth to your own language with dil_kur`.
8. `\nYOUR LAND: ` + `#{region.id} {region.ad}` + (mapInfo ? ` ({elevation}{", coastal" if kiyi}; neighboring regions: #{k} {name}, … or "none")`) | `unknown`.
9. `NEAR YOU:\n{budget(neighbors.map(varlikSatir) lines, ctx_nearby_budget, "look with dunyaya_bak and varlik_ara") or "(no one)"}`.
10. `\nRECENT EVENTS:\n{budget(sonKronik(ctx_events_lines, dId), ctx_events_budget, "look at the chronicle")}` (placed after "near you" so truncation does not drop it).
11. `\nWHAT YOU KNOW: #{id} {name} ({branchName}), … or "no knowledge yet"` + `\nKNOWLEDGE IN THE WORLD: {budget(list, ctx_knowledge_budget, "look with varlik_ara")} or "none"`.
12. `\nWHAT YOU OWN: resources: #{id} {name} (abundance {bolluk}), … or none; items: #{id} {name}, … or none`.
13. `\nRECORDS THAT MENTION YOU:\n[Epoch {cag}] {text}…` budget `ctx_mentions_budget`, hint "look at the chronicle", or `(none)`.
14. `\nLANGUAGES OF THE WORLD:\n{budget(dilSatirlari(6, null, dId), ctx_languages_budget, "look at the language with varlik_incele")}` or `(none yet)`.
15. If `kozmosSatirlari(dId)` non-empty: `\nOTHER WORLDS:\n{cosmos}` + (routes ? `\nKNOWN ROUTES LEAVING THIS WORLD (sefere_cik):\n{routes}` : `\nThere is no known route leaving this world (rota_kesfet).`).
16. If journeys `yolculuklar` with `yolcu_id=v.id, durum='yolda'`: `\nYOUR ONGOING EXPEDITIONS: {intent}, {remaining} epochs left, {people} people; …`.

Overall budget: `bolumluButce(sections with base = (index 0 ? full length : BAGLAM.bolum_taban), BAGLAM.olumlu_baglam × (tam ? BAGLAM.arac_kat : 1), hint "look with dunyaya_bak, varlik_ara and varlik_incele")` — each section receives at least its base share (scaled down proportionally if the bases alone exceed the total), the rest is handed out in order; overflowing sections are cut line-wise by `butce` with a `… (+N more lines; {hint})` footer.

### Tool server: `buildOlumluServer(vId, ctx)`

Builds an in-process MCP server named `olumlu` exposing the tools below to one mortal for one turn. `ctx` is shared across continuation sessions (`sunucuYap` rebuilds the server with the same `ctx`).

#### Common machinery

- **Tool wrapper** `tool(name, description, shape, handler)`:
  - Input shape passes through `aracAlanlari` (tools.js): every numeric/id field is pre-processed — strings like `"#12"`, `"id 12"`, `"son#12"` become 12; for optional id fields (`id`, `*_id`, `*_ids`) the values `null`, `0`, `""`, `"yok"`/`"none"`/`"null"`/`"-"`, `"#0"` mean "absent" (dropped from arrays); for required id fields 0 is a real value (`tapin` uses `ogul_id=0` = creator); decimal strings with comma become numbers; missing required numbers give a readable error naming the field ("{field} left empty: this field is required, write a number (for an id, the id from the list)", "{field} must be at least {min}", "{field} can be at most {max}", "{field} must be an integer", "{field} must be a number").
  - Synchronous handlers run inside one DB transaction (`atomik`) so a crash leaves no partial writes; async handlers (`rota_kesfet`) are not wrapped.
  - Enum fields use `esnekEnum`: fuzzy match (normalized exact, else prefix match either way when the input has ≥3 chars) before strict enum validation.
- **Results**: `ok(text)` → text content; `err(text)` → `"REJECTED: " + text`, `isError: true`. Texts go through `ekDuzelt` (LANGUAGE-SPECIFIC). Most success texts end with `" Actions left: {ctx.ap}"` (`Kalan eylem`).
- **AP check** `ap(n=1)`: if `ctx.ap < n` → reject `"Your action points for this epoch are spent; speak your word and finish."`. AP is deducted (`ctx.ap -= cost`) only after all validations pass (rejections never burn AP); dice failures DO burn AP.
- **Per-epoch counters** (`turDolu`/`turSay`): `ctx[field]` counts uses this turn; when `>= OLUMLU_K[rule]` reject with `"{message} (World rule OLUMLU_ARAC.{rule} = {value})."`. A rule value of 0 disables the tool. Counters live in `ctx` and are persisted in `tur_ctx`.
- **Name check** `isimAlinmis(name)` (world.js): normalized name already used by any non-rejected entity, son, star, world or foreign god → `"This name is taken."`.
- **Non-canon reasons** `kanonDisi(x…)` (first non-canon record among args): `"#{id} {name} is dead (died in Epoch {n}); this cannot be done to the dead."` | `"#{id} {name} was destroyed (Epoch {n}); it is no longer in the world."` | `"#{id} {name} was rejected by Fate; it counts as never having existed."` | `"#{id} {name} has come to pass; it is no longer a pending prophecy."` | `"#{id} {name} is currently {status}; this cannot be done to it."`. `kayitDurumu(id)`: `"No record selected: write an id from the list."` / `"There is no record numbered #{id}."`.
- **Creation helper** `yarat(me, {tur, ad, alt_tur, aciklama, statlar, guc, konum_id, alan, gorsel_prompt, etiketler=[]})`:
  - `INSERT varliklar(ad=trim(ad), tur, alt_tur=altTurDuzelt(alt_tur || typeLabel lowercased, tur), aciklama=anlatiTemizle(ekDuzelt(aciklama)), statlar=fillStats(typeDef, statlar, guc) [+olumluYasi if tur='olumlu'; never happens here], guc_seviyesi=guc, alan, cag=ctx.cag, konum_id, gorsel_prompt=(gp ? promptDuzelt({tur, etiketler}, gp) : null), etiketler, kaynak='olumlu', yapan_id=me.id)`. `durum` defaults to `kanon`. A DB trigger sets `dunya_id` from the location, else the creating son's world, else `yapan_id`'s world, else the first world.
  - `fillStats`: provided stats are clamped to the type's stat ranges; missing 0–100 stats default to `OGUL.stat_taban + guc × OGUL.stat_guc` (tools.js); other missing stats get type defaults.
  - If `konum_id`: bond `new → konum` `icinde`.
  - Push id to `ctx.yaratimlar`.
- **Creation power** `guc(me) = clamp(round(me.guc_seviyesi × creation_power_pct/100), 1, creation_power_cap)`.
- **`gorsel_prompt`** (optional, ≤900 chars, on most creation tools): English photoreal image prompt; descriptions append `GORSEL_YAZIM` = *"Image prompt rules: describe only what IS visible; never use negations (no, without, not, lacking, absent) because the image model ignores them and draws the thing anyway; describe the replacement instead (e.g. "a smooth blank head with a single thin dark slit" rather than "no face"). Whatever the subject (person, creature, place, object, event or god), name at least two details unique to this world so the image never falls back to a generic real-world look."*
- **Gating wrapper** (applied to every tool except the read tools `dunyaya_bak`, `varlik_incele`, `varlik_ara`), evaluated before the handler on every call:
  1. If the mortal no longer exists or `durum != 'kanon'` (died, destroyed, rejected mid-turn): `ctx.ap = 0`; reject `"{name or 'This mortal'} is no longer in the world ({status or 'none'}); it cannot act. Only speak your word."`.
  2. If tool ≠ `kac` and `me.tur == 'olumlu'` and `esirMi(me)`: reject `"{captor} holds you captive; you can only try to escape (kac)."`.
- **`araclariSar`** (llm.js) wraps all tools: calls of one turn run strictly sequentially; before each call `ctx` is snapshotted; on an exception `ctx` is restored (AP and counters refunded) and the result is `"REJECTED: An error occurred while the tool was running ({message[0:200]}). Your action point has been returned; fix your input and try again, or choose another action."`; after each successful call `ctx` is persisted to `varliklar.tur_cag/tur_ap/tur_ctx` (`turCtxYaz`).
- `srv.aracBedelleri = {harcar: [names of tools that cost], harcamaz: [free tools]}`.

#### Tool availability matrix

Availability is decided once when the server is built, from the mortal's type (`tip0 = V().tur`). "C" = communities (`halk, hizip, yerlesim, tarikat`). Suggested English tool names in the second column.

| Original tool | English name | Who gets it | Cost | Per-epoch cap |
|---|---|---|---|---|
| dunyaya_bak | look_at_world | all | free (read) | – |
| varlik_incele | inspect_entity | all | free (read) | – |
| varlik_ara | search_entities | all | free (read) | – |
| dil_kur | found_language | all | 1 AP | – |
| kelime_tureti | coin_words | all | free | word_coin_per_epoch (2) |
| uret | produce_item | all | 1 AP | – |
| insa_et | build_structure | all | 1 AP | – |
| kultur_yarat | create_culture | all | 1 AP | – |
| kaynak_kesfet | discover_resource | all | 1 AP | resource_discovery_per_epoch (1) |
| sahiplen | claim_resource | all | free | claim_per_epoch (1) |
| yerlesim_kur | found_settlement | halk, hizip, tarikat | 1 AP | – |
| ticaret_kur | establish_trade | all | 1 AP | – |
| savas_ilan_et | declare_war | all | 1 AP | – |
| tapin | worship | all | free | worship_per_epoch (1) |
| yaraticiya_dua | pray_to_creator | all | free | pray_per_epoch (1) |
| bilgi_gelistir | develop_knowledge | all | 1 AP | – |
| ogren | learn_knowledge | all | free | learn_per_epoch (1) |
| diplomasi | diplomacy | all | 1 AP | – |
| maceraya_cik | go_on_adventure | olumlu | 1 AP | – |
| rota_kesfet | find_route | all | 1 AP | (world-level: unknown_worlds_per_epoch) |
| toprak_kesfet | explore_land | C + olumlu, only if `KESIF.arac_tur > 0` | 1 AP | KESIF.arac_tur (1) |
| dirilis_ayini | resurrection_rite | C + olumlu, only if `OLUM.ayin_tur > 0` and the mortal worships ≥1 dead son at build time | 1 AP | OLUM.ayin_tur (1) |
| gemi_yap | build_ship | halk, yerlesim, hizip | 1 AP | – |
| sefere_cik | launch_expedition | all | 1 AP | one ongoing journey |
| evcillestir | tame_species | halk, yerlesim, olumlu, hizip | 1 AP | – |
| kimera_dok | merge_species | all | 1 AP | – |
| ruh_kapla | bind_spirit | all | 1 AP | – |
| kalinti_ara | search_ruins | all | 1 AP | – |
| sabotaj | sabotage | hizip, tarikat, olumlu | 1 AP | – |
| vaaz_et | preach | tarikat | 1 AP | – |
| tanriya_meydan_oku | challenge_god | olumlu | 1 AP | – |
| inkar_et | deny_god | halk, yerlesim, hizip, tarikat | 1 AP | – |
| kehanet_et | prophesy | olumlu, tarikat | 1 AP | prophecy_per_epoch (1) |
| kac | escape | olumlu | 1 AP | – |
| fidye_ode | pay_ransom | C | 1 AP | – |
| esiri_kurtar | rescue_captive | C + olumlu | 1 AP | – |
| ordu_topla | raise_army | C | 1 AP | one army per community |
| komutan_ata | appoint_commander | C | free | commander_per_epoch (1) |
| casus_ag_kur | build_spy_network | hizip, tarikat, olumlu, halk, yerlesim (= C + olumlu) | 1 AP | one per target |
| takas | barter | C + olumlu | barter_ap_cost (1) | – |
| borc_ver | lend | C + olumlu | debt_ap_cost (1) | – |
| borc_ode | repay_debt | C + olumlu | debt_ap_cost (1) | – |
| evlat_edin | adopt | olumlu | adopt_ap_cost (1) | adopt_per_epoch (1) |

An intelligent species (`tur`) agent gets only the "all" tools.

Chronicle entries are written with `addKronik(cag, sonId|null, kind, text, entityIds)`. Below, "Chronicle `kind`" gives the kind and the translated template; `{me}` = acting mortal's name. Templates using `toplulukIci(name, type)` (Turkish locative phrase: olumlu → "around {name}", halk → "among the {name} people", hizip/tarikat/ordu → "within {name}", else "in {name}") are LANGUAGE-SPECIFIC; render as "Among/within {name}, …".

### Tools — reading

**dunyaya_bak** — *"Shows your land, those near you, your language, what you know, what you own and recent events in more breadth than the prompt. Free."* Input: none. Returns `baglamMetni(me, world, {tam: true})` (total budget ×3; per-section budgets unchanged).

**varlik_incele** — *"Shows the details of an entity. Free."* Input: `id` int. Returns `varlikDetay(id)` (world.js) or rejects with `kayitDurumu(id) || "None."`.

**varlik_ara** — *"Searches for entities. Free."* Input: `sorgu` string. Returns matching `varlikSatir` lines or `"No results."`.

Note: read tools are not restricted to the mortal's world or knowledge.

### Tools — language

**dil_kur** (found_language) — *"You give birth to your own language: its name, its kind (spoken language, sacred language, script, sign language…), its sound structure and its first words. From now on you speak this language. 1 action."*
Input:
- `ad` string 2–50;
- `alt_tur` string ≤60 optional;
- `aciklama` string 80–900 — *"Sound structure, script, who speaks it, what is forbidden to say"*;
- `kelimeler` `KelimeSchema`: array 1–40 of `{kelime: 1–40 chars, anlam (meaning): 1–200, tur?: enum noun|verb|adjective|suffix|title|place name|proper name|interjection|number (isim, fiil, sıfat, ek, unvan, yer adı, özel ad, ünlem, sayı), koken? ≤240 "Etymology: which event or which words it derived from", ornek? ≤240 "Short usage example and its translation"}`;
- `gorsel_prompt` ≤900 optional — *"English photoreal prompt: an object showing this script/language, e.g. carved tablet, manuscript, inscription, with lighting and camera" + GORSEL_YAZIM*.
Logic:
1. AP check; name check.
2. Dialect rule: if `me.tur == 'olumlu'`: `parent = konusulanDil(me)` (the language with the newest active `konusur` bond; may be a dead language) or, if none, the language of the first canon `halk`/`yerlesim` in the same top region that speaks one. If `parent`: `alt_tur = "{parent.ad} dialect" + (alt_tur ? ": " + alt_tur : "")`. (A single mortal cannot birth a full language; it founds a dialect.)
3. `yarat(dil, stats {yayginlik: parent ? dialect_prevalence : language_prevalence, karmasiklik: language_complexity, kutsallik: language_sacredness}, guc(me), gorsel_prompt)`.
4. If parent: bond `new → parent` `soyundan` "dialect".
5. Deactivate all of `me`'s active `konusur` bonds; bond `me → new` `konusur`.
6. `added = sozlukEkle(new, kelimeler[0:words_per_call], 'v', me.id, cag)` — inserts into `sozluk(dil_id, kelime[≤60], anlam[≤300], tur, koken[≤300], ornek[≤300], ekleyen_tip, ekleyen_id, cag)`, skipping words already in that dictionary (case-insensitive) or with empty meaning.
7. `ctx.ap -= 1`.
8. Chronicle `dil`: `"{me} gave birth to its own language: {ad}. Its first words: {added joined ', '}."` ids `[me, new]`.
Returns `"#{id} {ad} was born. Actions left: {ap}"`.

**kelime_tureti** (coin_words) — *"You add new words (meaning, kind, origin) to the language you speak. Free, {word_coin_per_epoch} times per epoch."*
Input: `kelimeler` KelimeSchema.
Logic: if `ctx.kelime >= word_coin_per_epoch` → `"You have coined enough words."`; `lang = konusulanDil(me)`; if lang non-canon → its `kanonDisi` reason; if no lang → `"You have no language. First dil_kur."`; `ctx.kelime += 1` (counted even if nothing is added); `added = sozlukEkle(lang, words[0:words_per_call], …)`; if any: chronicle `dil`: `"{Among me}, new words were born ({lang}): {added}."` ids `[me, lang]`. Returns `"Added: {added}"` or `"No new words."`.

### Tools — production, building, culture, resources

**uret** (produce_item) — *"You produce an item from resources you own or that lie on your land: weapon, armor, shield, tool, jewelry, holy relic. The resources' abundance decreases; quality depends on your craft and the resources' potency. 1 action."*
Input: `ad` 2–60; `kategori` enum `silah` weapon | `zirh` armor | `kalkan` shield | `arac` tool | `taki` jewelry | `kutsal emanet` holy relic | `calgi` musical instrument | `kitap` book; `alt_tur` ≤60 optional (*"e.g. bone spear, salt armor"*); `aciklama` 100–1000; `kaynak_ids` int[1..produce_max_resources]; `sahip_id` int optional (*"Who will carry the item (a mortal or you); if empty, you"*); `gorsel_prompt` (*"English photoreal prompt" + GORSEL_YAZIM*).
Logic:
1. AP; name.
2. For each resource id (duplicates are NOT removed): missing → `"One of the resources does not exist."`; non-canon → reason; `tur != 'kaynak'` → `"{name} is not a resource."`; not (owned by me OR same region as me) → `"{name} is not on your land and you do not own it. Acquire it through trade or conquest."`; `bolluk < produce_min_abundance` → `"{name} is nearly exhausted (abundance {bolluk})."`.
3. `craft = zanaatGucu(me)`; `pot = mean(resource.kudret || 0)`; `weapon = kategori=='silah'`; `armor = kategori ∈ {zirh, kalkan}`; `met = knows('metalurji') ? produce_metallurgy_bonus : 0`; `mag = (knows('buyu') ? produce_magic_bonus : 0) + round((topRegion.statlar.buyu || 0) / produce_region_magic_divisor)`.
4. Stats:
   ```
   main = craft×produce_craft_pct/100 + pot×produce_potency_pct/100 + d(produce_die) + met
   hasar  = weapon ? clamp(main, produce_min_value, 100) : clamp(d(produce_side_die), 0, 100)
   koruma = armor  ? clamp(main', produce_min_value, 100) : clamp(d(produce_side_die), 0, 100)   // main' = independent roll of the same formula
   kudret = clamp(pot×produce_item_potency_pct/100 + d(produce_item_potency_die) + mag, 0, 100)
   lanet  = clamp(d(produce_curse_die) − produce_curse_minus, 0, 100)
   ```
5. `yarat(esya, alt_tur = alt_tur ? "{label(kategori)}: {alt_tur}" : label(kategori), stats, guc(me), konum = (me is settlement ? me : me.konum_id), tags [kategori])`.
6. For each resource: bond `item → resource` `kaynagi`; `resource.bolluk = clamp(bolluk − produce_abundance_loss, 0, 100)`.
7. Bond `me → item` `uretti`. Owner = `sahip_id` if it refers to a canon entity (any type, any distance), else me; bond `owner → item` `sahip`.
8. `ctx.ap -= 1`.
9. Chronicle `uretim`: `"{me}, using {r1 and r2 and …}, produced {ad} ({label(kategori)}; {quality})."` where quality = `masterwork` if hasar+koruma ≥ produce_masterwork_threshold, `sturdy` if ≥ produce_sturdy_threshold, else `crude`. ids `[me, item, …resources]`.
Returns `"#{id} {ad} was produced. Damage {hasar}, protection {koruma}, potency {kudret}. Actions left: {ap}"`.

**insa_et** (build_structure) — *"You build a structure: temple, tower, wall, bridge, monument, tomb, mine, harbor, library. It can be dedicated to a god. 1 action."*
Input: `ad` 2–60; `alt_tur` ≤60 opt; `aciklama` 100–1000; `konum_id` opt (*"Your own settlement, place or region; if empty, where you are"*); `adanan_ogul_id` opt (dedicated son); `gorsel_prompt` (GORSEL_YAZIM).
Logic:
1. AP; name.
2. `loc = konum_id ?? (me is settlement ? me : me.konum_id)`; non-canon → reason; missing or type ∉ {bolge, yer, yerlesim} or not canon → `"Invalid location."`; not (same region as me OR loc is me) → `"You can only build on your own land."`.
3. `craft = zanaatGucu(me)`; `arch = knows('mimarlik') ? build_architecture_bonus : 0`.
   `ihtisam = clamp(craft×build_grandeur_pct/100 + d(build_grandeur_die) + arch, 0, 100)`; `saglamlik = clamp(craft×build_sturdiness_pct/100 + d(build_sturdiness_die) + arch, 0, 100)`; `islev = clamp(build_function_base + d(build_function_die), 0, 100)`.
4. `yarat(yapit, …, guc(me), konum=loc)`; bond `me → structure` `insa_etti`.
5. If `adanan_ogul_id` is an existing son not dead: bond `structure → son` (type `o`) `tapar` "offering".
6. For `refah` and `servet` (each only if present): `−build_cost` (clamp 0–100). Save.
7. `ctx.ap -= 1`.
8. Chronicle `insa`: `"{me} built {ad} in {loc}{ ({alt_tur})}{; it was dedicated to {son name}}."` ids `[me, structure]`. (The dedication clause appears whenever `adanan_ogul_id` was given, even if the son is invalid/dead.)
Returns `"#{id} {ad} rose. Actions left: {ap}"`.

**kultur_yarat** (create_culture) — *"You give birth to a tradition of your community (festival, taboo, funeral rite), a legend, an artwork (folk song, statue, fresco, book, play; by evoking your god it strengthens them) or a law (statute, punishment, custom; a just law reduces rebellion). 1 action."*
Input: `tur` enum `gelenek` tradition | `efsane` legend | `eser` artwork | `kanun` law (*"tradition: rite/festival/taboo · legend: narrative · artwork: folk song, statue, fresco, book, play · law: statute, punishment, custom"*); `ad` 2–60; `alt_tur` ≤60 opt; `aciklama` 100–1000; `ilgili_ids` int[≤culture_max_related] opt; `gorsel_prompt` (*"English photoreal prompt: the ritual being performed or a scene of the legend" + GORSEL_YAZIM*).
Logic:
1. AP; name.
2. Stats: artwork `{un: artwork_base + d(artwork_die), etki: artwork_base + d(artwork_die)}` (independent rolls); law `{katilik: law_rigidity_base + d(law_rigidity_die), adalet: law_justice_base + d(law_justice_die)}`; tradition/legend `{yayginlik: tradition_prevalence, katilik: tradition_rigidity}`.
3. Location: artwork and law → (me if settlement else me.konum_id); tradition/legend → none.
4. `yarat(tur, …, guc(me))`.
5. Bond `me → new`: tradition `kutlar`, law `yonetir`, artwork `uretti`, legend `anlatir`.
6. If artwork and `god = hami(me)`: bond `artwork → son` `anlatir` "tells of its god" (engine uses this to strengthen the god).
7. For each existing id in `ilgili_ids` (canon not checked): bond `new → i` `anlatir` with description "subject of the tradition | legend | artwork | law".
8. `ctx.ap -= 1`.
9. Chronicle `kultur`: `"{Among me}, a new {tradition|law|artwork|legend} was born: {ad}."` ids `[me, new]`.
Returns `"#{id} {ad}. Actions left: {ap}"`.

**kaynak_kesfet** (discover_resource) — *"You discover a new resource on your land (ore vein, healing herb, sacred spring, bone bed…) and you own it. 1 action, {once|N times} per epoch."*
Input: `ad` 2–60; `alt_tur` ≤60 opt; `aciklama` 80–800; `konum_id` int required (*"Your own region or a place in your region"*); `alan` string opt (*"One of: {ALANLAR}"* — the domain list); `gorsel_prompt`.
Logic: AP; counter `kesif` vs `resource_discovery_per_epoch` (`"You already made a discovery this epoch"`); name; `loc` must be canon `bolge`/`yer` in my region → else `"You can only explore within your own region."`. `yarat(kaynak, stats {bolluk: discovery_abundance_base + d(discovery_abundance_die), deger: discovery_value_base + d(discovery_value_die), kudret: discovery_potency_base + d(discovery_potency_die)}, guc(me), konum=loc, alan=alanEsle(alan, 'Toprak' (Earth)))`. Bond `me → resource` `sahip` "discovered". `ap -= 1`; counter++. Chronicle `kesif`: `"{me} discovered {ad} in {loc}{ ({alt_tur})}."`. Returns `"#{id} {ad} is now yours. Actions left: {ap}"`.
`alanEsle(value, fallback)`: case-insensitive exact match in `ALANLAR`, else substring either way, else fallback.

**sahiplen** (claim_resource) — *"You claim an unowned resource on your land. If you take someone else's resource, enmity is born between you. Free, {once} per epoch."*
Input: `kaynak_id` int.
Logic:
1. Counter `sahiplendi` vs `claim_per_epoch` (`"You already claimed something this epoch"`).
2. Missing → `"No such record."`; non-canon → reason; not `kaynak` → `"This is not a resource."`; not same region → `"The resource is not on your land."`; already owner → `"It is already yours."`.
3. `oldOwners` = sources of active `sahip` bonds (from entities) to the resource.
4. Deactivate those bonds, setting their description to `"{me} seized it (Epoch {cag})"`; bond `me → resource` `sahip`.
5. For each old owner that is a community: `savasIlan(old, me, "because of {resource}", cag)` (derin.js: succeeds only if `savasAcilabilir` — both alive, same world or connected, not already enemies, no ceasefire, no governance/tribute bond, and global war cap not reached for community pairs; on success breaks alliance+trade and adds `old → me` `dusman`). If the war could NOT be declared and `me` is a community: `tIliskiDegistir(old, me, −seizure_relation_loss, "{resource} was seized")`.
6. Counter++.
7. Chronicle `kaynak`: `"{me} claimed {resource}{; {first chronicle_list_names old owners joined ', '}{ and {k} more communities} were angered by this}."` ids `[me, resource]`.
Returns `"{resource} is now yours."`.

**yerlesim_kur** (found_settlement; halk, hizip, tarikat) — *"You split a branch off your population (or your disciples) and found a new settlement (village, fortress, harbor, monastery, camp); the migrants are subtracted from you. In your own region or a neighboring one. 1 action."*
Input: `ad` 2–60; `alt_tur` ≤60 opt; `aciklama` 100–900; `konum_id` int; `gorsel_prompt`.
Logic:
1. AP; name.
2. `loc` must be canon `bolge`/`yer` and `yakinMi(me, loc)` → else `"You can only settle in your own or a neighboring region."`.
3. `key = 'nufus'` if present else `'murit'` if present else none → `"You have no population or disciples to send; a new settlement can only be founded by a branch splitting off from your own people."`.
4. `floor = key=='murit' ? cult_min_disciples : (me is halk ? SINIR.halk_nufus_taban : SINIR.nufus_taban)`; `canLeave = max(0, floor(stat − floor))`; `minMig = max(migration_min, SINIR.nufus_taban)`; `migrants = min(canLeave, SINIR.kent_nufus_tavan, max(minMig, round(stat × migration_pct/100)))`.
5. If `migrants < minMig` → `"At least {minMig} people must migrate to found a new settlement (World rule OLUMLU_ARAC.goc_en_az); {canLeave} {disciples|people} among you can leave."`.
6. `stat −= migrants` (population conserved). Save.
7. `yarat(yerlesim, stats {nufus: migrants, refah: new_settlement_prosperity, savunma: new_settlement_defense, inanc: new_settlement_faith}, guc = max(1, guc(me) − 1), konum=loc)`.
8. Bonds: `me → new` `gocetti` "{migrants} people"; `new → me` `soyundan`; if `me` speaks a language: `new → lang` `konusur`; if `god = hami(me)`: `new → son` `tapar` (a foreign-god patron is not inherited).
9. `ap -= 1`. Chronicle `goc`: `"{migrants} people from among {me} migrated and founded {ad} in {loc}."` ids `[me, new]`.
Returns `"#{id} {ad} was founded ({migrants} people). Actions left: {ap}"`.

### Tools — trade, war, diplomacy

**ticaret_kur** (establish_trade) — *"You establish trade with a community nearby or in a neighboring region; both of your prosperity increases. 1 action."*
Input: `hedef_id` int; `mal` string 5–200 (*"What you give and what you take"*).
Logic: AP; target non-canon → reason; missing / not canon / not a community / self → `"Invalid partner."`; `!yakinMi(me, h)` → `"This community is too far; you can only establish trade with those in your own or a neighboring region."`; enemies (either direction) → `"No trade with your enemy."`; already trading → `"You are already trading."`. Bond `me → h` `ticaret` (description = `mal`); `ap -= 1`; `tIliskiDegistir(me, h, +trade_relation_gain, "trade")`. Chronicle `ticaret`: `"Trade began between {me} and {h}: {mal}."` ids `[me, h]`. Returns `"Trade established. Actions left: {ap}"`. (The prosperity effect of trade bonds is applied by the engine, not here.)

**savas_ilan_et** (declare_war) — *"You declare war on a community or a creature. The world's flow resolves the war; your weapons and your god lend you strength. 1 action."*
Input: `hedef_id` int; `sebep` (reason) 10–300.
Logic:
1. AP; non-canon → reason; missing / not canon / type ∉ {halk, hizip, yerlesim, tarikat, tur} / self → `"Invalid target."`; `!yakinMi` → `"This target is too far."`; already enemies → `"You are already at war."`.
2. If target is not a species: active ceasefire (`ateskesVar`, bond `ateskes` younger than `MOTOR.ateskes_cag`) → `"There is an ongoing ceasefire between you; war cannot be declared until it expires."`; governance (`yonetir`) or tribute (`harac_oder`) bond either way → `"There is a governance or tribute bond between you; that bond must break first."`.
3. Deactivate trade bonds in both directions.
4. Bond `me → h`: `avlar` (hunts) if species, else `dusman`; description = `sebep`. `ap -= 1`. If not species: `tIliskiDegistir(me, h, −war_relation_loss, "declaration of war")`.
5. `g1 = hami(me)`, `g2 = hami(h)`: if both and different → `iliskiDegistir(g1, g2, −war_patron_relation_loss)` (son↔son).
6. Chronicle `savas`: `"{me} declared war on {h}: {sebep}"` ids `[me, h]`.
Returns `"War declared. Actions left: {ap}"`. Battles are resolved by the engine from `dusman`/`avlar` bonds. Note: unlike `derin.savasIlan`, this does not check the global war cap and does not break alliances.

**diplomasi** (diplomacy) — *"Diplomacy with another community: alliance (it stands by you in war), peace (tries to end hostility), tribute (demands wealth from the weak) or marriage/blood bond (unites lineages). 1 action."*
Input: `hedef_id` int; `tur` enum `ittifak` alliance | `baris` peace | `harac` tribute | `evlilik` marriage; `sart` (terms) 10–300.
Logic:
1. AP; non-canon → reason; missing / not canon / self / type ∉ {halk, hizip, yerlesim, tarikat, olumlu} → `"Invalid target."`; `!yakinMi` → `"Too far."`.
2. `power(x) = (x.guc ?? x.savascilik ?? x.savunma ?? diplomacy_default_power) + log10(max(10, x.nufus || x.murit || 100)) × diplomacy_population_weight` (the 100 is hard-coded).
3. `rel = target is a community ? tIliski(me, h) : 0`.
4. Pre-checks (no AP burned): alliance/marriage with an enemy → `"No alliance with your enemy; make peace first."`; peace when not enemies → `"You are not enemies anyway."`.
5. `roll = d(100) − round(rel / diplomacy_relation_divisor)` (good relations make acceptance easier). `ap -= 1`.
6. Alliance / marriage: if `roll <= diplomacy_alliance_threshold`: bond `me → h` `muttefik` with description `"{tur}: {sart}"`; result `"{h} accepted"`; relation `+diplomacy_marriage_relation_gain` (marriage) or `+diplomacy_alliance_relation_gain` (alliance), note = tur. Else result `"{h} refused"`; relation `−diplomacy_refusal_relation_loss`, note "{tur} refusal".
7. Peace: if `roll <= diplomacy_peace_threshold`: deactivate `dusman` bonds both ways; result `"peace was made"`; relation `+diplomacy_peace_relation_gain` "peace". Else `"the peace offer was turned down"`. (No ceasefire bond is created.)
8. Tribute (deterministic, no roll used): if `power(me) < power(h) × tribute_superiority_pct/100`: bond `h → me` `dusman` "tribute insolence"; relation `−tribute_insolence_relation_loss`; result `"{h} laughed and became your enemy"`. Else: for `servet` and `refah` independently: if `h` has it, `−tribute_payer_loss`; if `me` has it, `+tribute_receiver_gain` (clamp 0–100); save both; bond `h → me` `harac_oder` (description = `sart`); relation `−tribute_relation_loss` "tribute"; result `"{h} agreed to pay tribute"`.
9. Chronicle `diplomasi`: `"{me} offered {alliance|peace|tribute|marriage} to {h}: {result}."` (the free-text terms are deliberately not chronicled). ids `[me, h]`.
Returns `"{result}. Actions left: {ap}"`.

**casus_ag_kur** (build_spy_network; C + olumlu) — *"You build a spy network inside a nearby community: you learn its secrets and gain an advantage in war; if it is caught, relations sour and war may break out. 1 action."*
Input: `hedef_id` int; `ortu` (cover) 10–300 (*"The spies' cover: merchant, pilgrim, apprentice…"*).
Logic: AP; non-canon → reason; missing / not canon / not a community / self → `"A spy network can only be built in a community."`; `!yakinMi` → `"This community is too far."`; existing active `casus` bond me→h → `"You already have a network there."`. Bond `me → h` `casus` (description = cover); `ap -= 1`. Chronicle `entrika`: `"{Within h}, strange faces appeared ({ortu[0:80]})."` ids `[h]` (the spymaster is not revealed). Returns `"Network established. Actions left: {ap}"`. Effects (secrets, war bonus, discovery) are engine-side.

**sabotaj** (sabotage; hizip, tarikat, olumlu) — *"You secretly harm a community: poison (population/health falls), arson (prosperity, defense, wealth fall) or discord (you break one of its alliances). If caught, you become enemies. 1 action."*
Input: `hedef_id` int; `tur` enum `zehir` poison | `kundak` arson | `nifak` discord; `nasil` (how) 10–300.
Logic:
1. AP; non-canon → reason; missing / not canon / self / type ∉ {halk, hizip, yerlesim, tarikat, olumlu} → `"Invalid target."`; `!yakinMi` → `"Too far."`. `ap -= 1`.
2. `cunning = (me.akil ?? me.nufuz ?? me.etki ?? default_stat) + d(sabotage_die)`; `vigilance = (h.savunma ?? h.akil ?? default_stat) + d(sabotage_die)`; `caught = vigilance > cunning + sabotage_caught_margin`.
3. If `cunning >= vigilance` (success):
   - poison: for `nufus`, `murit` (if present): `clamp(x × (100 − poison_population_loss_pct)/100, 1, SINIR.nufus_tavan)`; if `h.can` exists and `h` is not `olumlu`: `can = clamp(can − poison_health_loss, 1, SINIR.can_tavan)`; note `"the poison took effect"`.
   - arson: `refah`, `savunma`, `servet` (each if present) `−arson_loss` (clamp 0–100); note `"a fire broke out"`.
   - discord: first active `muttefik` bond involving `h`: deactivate; note `"the alliance between {h} and {other} dissolved"`; else `"there was no alliance to break"`.
   - Save `h`. If poison and `h` is `olumlu`: `olumluYarala(h, poison_health_loss, {sebep: "died of poisoning", cag, katil: caught ? me : null})` (sim.js; health damage, may kill); if it returns `'oldu'` (died) note = `"the poison took effect; {h} died"`.
   Else note `"the sabotage failed"`.
4. If `caught` and not already enemies: bond `h → me` `dusman` "{tur} caught"; note += `"; and you were caught"`. If `caught` and both are communities: `tIliskiDegistir(me, h, −sabotage_caught_relation_loss, "caught {tur}")`.
5. Chronicle `entrika`: caught → `"{me} organized {tur} against {h} and was caught: {note}."` ids `[h, me]`; not caught → `"A mysterious {poisoning|fire|rift} occurred within {h}."` ids `[h]` (written even when the sabotage failed).
Returns `"{note}. Actions left: {ap}"`.
Note: success requires `cunning >= vigilance` while caught requires `vigilance > cunning + margin`, so they are mutually exclusive — the `katil` (killer) argument is always null on success.

### Tools — religion

**tapin** (worship) — *"You worship a god (a son) or change your god; if you give ogul_id 0 you worship the creator god directly, the father of all the sons. Your old god does not forget this. Free, {once} per epoch."*
Input: `ogul_id` int (required; 0 = creator); `adak` (vow/offering text) 10–300.
Logic:
1. Counter `tapindi` vs `worship_per_epoch` (`"You already worshipped this epoch"`).
2. If `ogul_id == 0`: `yaraticiyaTapin(me, adak, cag)` (yaratici.js: if an active `tapar` bond `me → creator` (type `t`) exists → false; else add it and remove tag `tanrısız`). False → `"You already worship the creator."`. Counter++. Chronicle `tapinma` (son null): `"{me} began to worship the creator {world.tanri_adi} directly: {adak}"` ids `[me]`. Returns `"You now worship the creator. You may also keep worshipping one of the sons."` (son worship is untouched).
3. Else `s = getSon(ogul_id)`: missing → `"No such god."`; dead → `"{s} is dead; they can only be worshipped by awaiting their resurrection."`; `old = hami(me)`; existing active `tapar` me→s → `"You already worship {s}."`.
4. `oldForeign = yabanciHami(me)`. Deactivate all of me's active `tapar` bonds to sons (`o`) and foreign gods (`y`) (creator worship `t` is kept). If `oldForeign`: `yabanci_tanrilar.tutum = max(−100, tutum − worship_foreign_attitude_loss)`.
5. Bond `me → s` `tapar` (description = adak). Remove tag `tanrısız`. If `old` and `old ≠ s`: `iliskiDegistir(old, s, −worship_switch_relation_loss)`.
6. Counter++. Chronicle `tapinma` (son = s): `"{me} worshipped {s}{; abandoned {old}}: {adak}"` ids `[me]`.
Returns `"You now worship {s}."`.

**yaraticiya_dua** (pray_to_creator) — *"You pray directly to the creator god above the sons, the father of all worlds. Your prayer reaches him; if he answers you will see it in your dream and his grace will descend. Free, {once} per epoch."*
Input: `dua` (prayer) 15–500; `istek` (request) ≤200 opt (*"What you ask of him"*).
Logic: counter `duaEtti` vs `pray_per_epoch` (`"You already prayed to the creator this epoch"`); counter++; `olumluDuasi(me, dua, istek, cag)` (yaratici.js: inserts `mesajlar(cag, kimden_tip 'v', kimden_id me, kime_tip 't', kime_id NULL, niyet 'dua', metin, istek)` for the player's inbox and chronicles `dua`: `"{me} prayed to the creator: "{dua[0:200]}""`). Returns `"Your prayer rose to the heavens. If the Creator hears it, you will know in your next dream."`. (The player's answer — `olumluDuasiniCevapla` — later sends a `ruya` message.)

**vaaz_et** (preach; tarikat only) — *"You spread your god's word to a neighboring community; if it takes, they too worship your god and your disciples grow. It is hard with those who worship another god. 1 action."*
Input: `hedef_id` int; `vaaz` (sermon) 20–400.
Logic:
1. AP; `god = hami(me)` null → `"You have no god; worship first."`; target non-canon → reason; missing / not canon / type ∉ {halk, yerlesim, hizip, olumlu} / `!yakinMi` → `"Invalid or distant target."`.
2. `old = hami(h)`; `old == god` → `"{h} already worships {god}."`. `oldForeign = yabanciHami(h)`.
3. `oldCharisma = (old ? old.statlar.karizma / sermon_old_god_divisor : 0) + (oldForeign ? (ytStatlar(oldForeign).karizma ?? default_stat) / sermon_old_god_divisor : 0)`.
4. `ap -= 1`.
5. `chance = sermon_base_chance + (me.etki || sermon_default_influence)/2 + god.statlar.karizma / sermon_god_charisma_divisor − oldCharisma − (h.inanc || sermon_default_faith) / sermon_faith_divisor`.
6. If `d(100) <= chance`: deactivate `h`'s `tapar` bonds to `o`/`y`; if `oldForeign`: its `tutum −= worship_foreign_attitude_loss` (min −100); remove tag `tanrısız` from `h`; bond `h → god` `tapar` "by {me}'s sermon"; `me.murit = clamp((me.murit || 100) × (1 + sermon_disciple_gain_pct/100), 1, SINIR.murit_tavan)`; if `old`: `iliskiDegistir(old, god, −sermon_relation_loss)`. Chronicle `tapinma` (son = god): `"{me} preached and {h} turned to {god}{; {old and oldForeign names joined ' and '} lost a worshipper}: "{vaaz}""` ids `[me, h]`. Returns `"{h} now worships {god}. Actions left: {ap}"`.
7. Else chronicle `tapinma`: `"{me} preached among {h}, but no one listened."` ids `[me, h]`; returns `"The sermon did not take hold. Actions left: {ap}"`.

**inkar_et** (deny_god; halk, yerlesim, hizip, tarikat) — *"You deny your god: you stop worshipping them and become godless. Your god's existence weakens, and the father of the gods cannot draw strength from godless communities either. 1 action."*
Input: `neden` (reason) 15–400.
Logic: AP; `h = hami(me)` (includes the creator-son fallback), `y = yabanciHami(me)`; if none and already tagged `tanrısız` → `"You are already godless; you have no god to deny."`. `ap -= 1`. Deactivate `tapar` bonds to `o`/`y`. If `y`: `tutum = max(−100, tutum − deny_foreign_attitude_loss)`, `inanc = max(0, inanc − deny_foreign_faith_loss)`. Add tag `tanrısız`. If `h`: `ogullar.varlik = max(0, varlik − deny_son_existence_loss)`; bond `h(o) → me` `dusman` "denial: {neden}". Chronicle `inkar` (son = h?.id): `"{me} denied {h | y | 'the gods'} and became godless: {neden}"` ids `[me]`. Returns `"You are now godless.{ {h} will not forget this.} Actions left: {ap}"`.

**kehanet_et** (prophesy; olumlu, tarikat) — *"You make a prophecy: you foretell something that will happen. If it comes true, Fate records it and your reputation (charisma) rises; if it is misread, it is shaken. 1 action, {once} per epoch."*
Input: `ad` 2–60 (*"The prophecy's name, from your own language"*); `soz` 40–600 (*"The words of the prophecy: imagistic but testable; who or what, and when"*); `ilgili_ids` int[≤prophecy_max_related] opt.
Logic: AP; counter `kehanet` vs `prophecy_per_epoch` (`"You already prophesied this epoch"`); name. `relatedNames` = names of canon entities in `ilgili_ids`. `yarat(kehanet, alt_tur = tarikat ? "cult prophecy" : "seer's word", aciklama = '{me} said: "{soz}"{ The word concerns {relatedNames}.} If it comes true, {me}'s word will pass from tongue to tongue; if it comes to nothing, their name will be shaken.', stats {kesinlik: clamp(prophecy_certainty_base + round((me.akil ?? me.etki ?? default_stat)/2), 0, 100)}, guc(me))`. Bonds: `me → prophecy` `kehanet_eder`; `prophecy → each canon related` `kehanet_eder` "subject of the prophecy". `ap -= 1`; counter++. Chronicle `kehanet`: `"{me} made a prophecy: {ad}."` ids `[me, prophecy]`. Returns `"#{id} {ad} was spoken. Fate will remember it if it comes true. Actions left: {ap}"`. (Fulfilment and the charisma effect are judged by Fate elsewhere.)

**dirilis_ayini** (resurrection_rite) — available only when `OLUM.ayin_tur > 0`, the mortal is a community or `olumlu`, and at build time it has an active `tapar` bond to at least one son with `durum='olu'`. Description (values interpolated): *"You perform a rite for the return of your dead god: prayer (+{dua_adanmislik} devotion), wealth offering ({servet_bedel} from your wealth, prosperity or craft; +{servet_adanmislik}), blood sacrifice ({kurban_nufus}% of your population; +{kurban_adanmislik}) or life sacrifice (a named mortal offers themselves or your people offers them; +{can_kurbani_adanmislik}). A rite performed in the region where the god's bones lie counts {hac_carpan/100}×. When devotion is full, a resurrection rite may take hold. 1 action, {once} per epoch."*
Input: `ogul_id` int (*"The id of the dead god (son)"*); `tur` enum `dua` prayer | `servet` wealth offering | `kan` blood sacrifice | `can` life sacrifice; `kurban_id` int opt (*"The named mortal offered in a life sacrifice (if empty and you are a mortal, yourself)"*).
Logic: AP; `ctx.ayin >= OLUM.ayin_tur` → `"You already performed a rite this epoch (World rule OLUM.ayin_tur = {n})."`; `ogul_id` not among the dead gods I worship (re-queried) → `"You can only perform a rite for a dead god you worship."`; `r = olum.dirilisAyini(me, ogul_id, {tur, cag, kurbanId})` — any thrown error → reject with its message; `ap -= 1`; `ctx.ayin += 1`. Returns `"{r.metin} Actions left: {ap}"`. (Rite mechanics are specified in olum.js.)

### Tools — knowledge

**bilgi_gelistir** (develop_knowledge) — description: *"Your community develops a new knowledge (a technology, craft, school or method). Branch: {for each branch: key (effect)} joined '; '. If built on knowledge you already know it is stronger. 1 action."*
Input: `ad` 2–60 (*"A name from your own language"*); `dal` enum = keys of `BILGI_DALLARI`; `aciklama` 100–900 (*"What it is, how it was found, which material or observation it rests on"*); `temel_ids` int[≤knowledge_max_bases] opt (*"Knowledge you know that it is built upon"*); `kaynak_id` opt (*"The resource it relies on"*); `gorsel_prompt` (*"English photoreal prompt: people practicing this technique, tools, materials, setting" + GORSEL_YAZIM*).
Knowledge branches (`BILGI_DALLARI`, rules.js; shown to the model):

| key | name | effect text |
|---|---|---|
| tarim | Agriculture | Knowers' population grows 50% faster; famine and drought strike at half strength. |
| metalurji | Metallurgy | +15 damage/protection on weapons and armor they make. |
| denizcilik | Seafaring | Trade, war and migration with communities beyond the sea. |
| yazi | Writing | Their languages grow more complex; what they know spreads to partners twice as fast. |
| mimarlik | Architecture | +20 grandeur and sturdiness on their structures; earthquake-resistant. |
| tip | Medicine | Plagues strike at half strength; mortals' lifespan +20. |
| buyu | Magic | Magic stat +10; items they make +10 potency. |
| savas | Art of war | +12 to war power. |
| gokbilim | Astronomy | They read the epoch's star: sense disasters in advance and suffer them at half strength. |
| ticaret | Commerce | Twice the prosperity from trade routes. |
| gokyuzu_seyri | Sky navigation | Can discover interworld routes; risk of getting lost on a journey halves. |
| gemi_yapimi | Shipbuilding | Can build interworld ships (vehicles). |
| kapi_bilimi | Gate lore | Can open and close ancient gates; gate routes take one epoch. |
| yol_biliciligi | Wayfinding | Can fold space: with a cosmic resource, routes drop to one epoch. |
| bosluk_yasami | Void living | Can found colonies on worlds with thin or no atmosphere; less loss on journeys. |
| olumsuzluk | Quest for immortality | Knowers' mortals reach for immortality; those who succeed do not age, but the gods see them as a threat. |
| biyobuyu | Biomancy | Merges and alters living things: can weave chimeras, steer mutations. |
| yasak | Forbidden knowledge | Great power: war +15, magic +15, forces gates. Price: knowers' sanity drops each epoch, leakage flows into their world; Fate watches. |

(Several effect texts state numbers that are actually tunables elsewhere — e.g. metallurgy +15 = `produce_metallurgy_bonus`; generate the text from the tunables in the new app.)
Logic:
1. AP; name.
2. `known = set(bildikleri(me))` (active `bilir` bonds to canon `teknoloji`); `bases = temel_ids ∩ known` (unknown ids silently dropped).
3. `level = clamp(1 + max(0, max(base.seviye || 1)) + (zanaatGucu(me) > knowledge_craft_threshold ? 1 : 0), 1, knowledge_level_cap)` (no bases → 1 or 2).
4. `yarat(teknoloji, alt_tur = branch name lowercased, stats {seviye: level, yayginlik: knowledge_prevalence}, guc = clamp(level, 1, creation_power_cap)` (note: not `guc(me)`), tags [`dal:{dal}`]).
5. For each base: bond `new → base` `soyundan` "built upon". If `kaynak_id` is a `kaynak`: bond `new → resource` `kaynagi`.
6. `ogret(me, new, cag, "developed")` (mudahale.js: bond `me → new` `bilir`; `yayginlik += MUDAHALE.bilgi_yayginlik` (8) → a new knowledge starts at 18 prevalence by default).
7. `ap -= 1`. Chronicle `bilgi`: `"{me} developed a new knowledge: {ad} ({branch name}, level {level})."` ids `[me, new]`.
Returns `"#{id} {ad} (level {level}). Actions left: {ap}"`.

**ogren** (learn_knowledge) — *"You learn a knowledge known by your trade partner, your ally or your neighbor. Free, {once} per epoch."*
Input: `bilgi_id` int; `kimden_id` (from whom) int.
Logic: counter `ogrendi` vs `learn_per_epoch` (`"You already learned this epoch"`); `kanonDisi(o, t)` → reason; missing either / `t` not `teknoloji` / not canon → `"Invalid: both the teacher and the knowledge must be in the world."`; `o` does not know `t` → `"{o} does not know this."`; `!ogrenebilirMi(me, o)` → `"There is no trade, alliance or neighborliness between you and {o}."`; `ogret(me, t, cag, "learned from {o}")` returns false → `"You already know it."`. Counter++. Chronicle `bilgi`: `"{me} learned the knowledge {t} from {o}."` ids `[me, o, t]`. Returns `"{t} is now your knowledge too."`.

### Tools — heroes (named mortals only)

**maceraya_cik** (go_on_adventure; olumlu) — *"You set out on an adventure: hunting a dangerous creature (the world's flow resolves the fight at epoch end; your weapons count) or seizing an item held by someone else (your agility and wits against its owner's defense). 1 action."*
Input: `hedef_id` int (*"The species to hunt or the item to seize"*); `amac` (purpose) 10–300.
Logic:
1. AP; non-canon → reason; missing / not canon → `"The target is not in the world."`.
2. Species (`tur`): `!yakinMi` → `"This creature is too far."`; bond `me → species` `avlar` (description = purpose); `ap -= 1`; chronicle `macera`: `"{me} set out to hunt {h}: {amac}"` ids `[me, h]`; returns `"You set out. The fight will be resolved at the end of the epoch. Actions left: {ap}"`.
3. Item (`esya`): `ownerBond` = first active `sahip` bond (from an entity) to the item; `owner` = its source.
   - owner is me → `"It is already yours."`; owner exists and `!yakinMi(me, owner)` → `"The item's owner is too far."`; no owner and (different world or `!yakinMi(me, item)`) → `"This item is too far; you can only seize an unowned item in your own or a neighboring region."`.
   - `p1 = (me.ceviklik || default_stat) + (me.akil || default_stat)/2 + d(adventure_die)`; `p2 = (owner?.savunma ?? owner?.guc ?? default_stat) + d(adventure_die)`. `ap -= 1`.
   - `p1 >= p2`: deactivate `ownerBond`; bond `me → item` `sahip` "seized: {amac}"; if owner: bond `owner → me` `dusman` "{item} was stolen"; chronicle `macera`: `"{me} seized {item}{ from {owner}}: {amac}"` ids `[me, item, owner?]`; returns `"{item} is now yours ({round p1} – {round p2}). Actions left: {ap}"`.
   - else `me.can = clamp((me.can || 100) − adventure_fail_wound, 1, SINIR.can_tavan)` (cannot die from this); chronicle `macera`: `"{me} tried to seize {item} but was wounded and fled."`; returns `"You failed ({p1} – {p2}); you were wounded. Actions left: {ap}"`.
4. Other types → `"The adventure target must be a creature species or an item."`.

**tanriya_meydan_oku** (challenge_god; olumlu) — *"You defy a god (a son): your strength, agility, wits and weapons against their might. If you win, the god is wounded, their fame is shaken and you become a legend; if you lose, you die or are cursed. 1 action."*
Input: `ogul_id` int; `neden` (reason) 15–400.
Logic:
1. AP; `s = getSon(ogul_id)` missing → `"No such god."`; dead → `"{s} is already dead; their bones lie in the world."`. No distance/world check. `ap -= 1`.
2. `weapons = Σ over items I own (active sahip → canon? (not checked) esya): hasar/challenge_damage_divisor + kudret/challenge_potency_divisor`.
3. `pk = (me.guc || default_stat) + (me.ceviklik || default_stat)/2 + (me.akil || default_stat)/challenge_wits_divisor + weapons + d(challenge_die)`.
4. `pt = s.statlar.guc/2 + s.statlar.irade/2 + s.seviye × challenge_god_level_weight + d(challenge_die) + (s has a power i with etki 'dokunulmaz' (untouchable) and s.seviye >= GUC_SEVIYELERI[i] ? challenge_untouchable_bonus : 0)`.
5. **Win** (`pk >= pt`):
   - **God-slaying** if `pk − pt >= godslay_margin` AND `(s.varlik ?? god_default_existence) < godslay_existence_threshold`: `me.karizma = clamp((me.karizma || default_stat) + godslayer_charisma_gain, 0, 100)`; tags: remove all `unvan:*`, add `unvan:God-Slayer` (`Tanrı Katili`) and `tanrı katili`; `derin.tanriOlumu(s, cag, "killed by the mortal {me}")` (son death: corpse falls into the son's world, etc.); bond `me → s(o)` `oldurdu` (description = reason); chronicle `tanri_savasi` (son s): `"The mortal {me} killed the fading god {s} ({pk} – {pt}): {neden}"` ids `[me]`; returns `"You killed the god. You are now "God-Slayer"; their brothers and their father will not forget this. Actions left: {ap}"`.
   - **Wound** otherwise: `wound = round((KURAL.can_taban + KURAL.can_dayaniklilik/100 × s.statlar.dayaniklilik) × god_wound_pct/100)` (percentage of the unrounded max health); `ogullar.can = max(1, can − wound)`, `un = max(0, un − god_wound_fame_loss)`; `me.karizma = clamp((karizma || default_stat) + god_wounder_charisma_gain, 0, 100)`; tags: remove `unvan:*`, add `unvan:Wounder of {s}` (original `"{s}'i Yaralayan"` — LANGUAGE-SPECIFIC accusative suffix); bond `s(o) → me` `dusman` "defeat: {neden}"; chronicle `tanri_savasi`: `"The mortal {me} defied the god {s} and wounded them ({pk} – {pt}): {neden}"`; returns `"You wounded the god. You will now be remembered as "Wounder of {s}"; but they will not forget you. Actions left: {ap}"`.
6. **Loss**:
   - with `d(100) <= challenge_death_chance`: `UPDATE varliklar SET durum='olu', olum_cag=cag, kader_notu="Epoch {cag}: defied {s} and gave their life."`; `try sim.olumSonrasi(me, cag, notifier → chronicle kind 'dunya')` (after-death processing: inheritance etc.); chronicle `tanri_savasi`: `"The mortal {me} defied the god {s} and gave their life: {neden}"`; `ogullar.un += god_crush_fame_gain` (no cap); `ctx.ap = 0; ctx.oldu = true`; returns `"The god crushed you ({pk} – {pt}). Your story ends here."` (all further tool calls are blocked by the gating wrapper).
   - otherwise: add tag `lanetli` (cursed); bond `s(o) → me` `lanetledi` "for their insolence"; chronicle `tanri_savasi`: `"The mortal {me} defied the god {s}; was defeated and cursed: {neden}"`; returns `"You were defeated and cursed ({pk} – {pt}). Actions left: {ap}"`.

**evlat_edin** (adopt; olumlu) — *"You adopt another named mortal: they count as your lineage and it enters the chronicle. They must be younger than you and near you. {Once} per epoch. {adopt_ap_cost} action."*
Input: `evlat_id` int; `neden` 10–300 (*"Why and how you adopt"*).
Logic: `ap(adopt_ap_cost)`; counter `evlat` vs `adopt_per_epoch` (`"You already adopted this epoch"`); non-canon → reason; missing / not canon / not `olumlu` / self → `"The one to adopt must be another living, named mortal."`; captive → `"{c} is a captive; they must be rescued first."`; not (same region or near) → `"{c} is too far."`; any active `soyundan` bond either way → `"There is already a lineage bond between you and {c}."`; both ages known and `c.yas >= me.yas` → `"{c} is not younger than you ({c.yas} / {me.yas}); no one adopts someone older than themselves."`. Bond `c → me` `soyundan` "adopted: {neden}"; `tIliskiDegistir(me, c, +adopt_relation_gain, "adoption")`; `ap −= adopt_ap_cost`; counter++. Chronicle `soy`: `"{me} adopted {c}: {neden}"` ids `[me, c]`. Returns `"{c} is now your child. Actions left: {ap}"`.

### Tools — cosmos and travel

**rota_kesfet** (find_route) — *"You search for the way to another world. The way you find depends on what you know: gate lore an ancient gate, sky navigation a sail route, wayfinding folding, magic a dream road. Rarely you may discover a world no one knows. 1 action."* (async tool, not wrapped in a single transaction)
Input: `nasil` 10–300 (*"How you search for the way: observation, sacrifice, dream, old maps…"*).
Logic:
1. AP. `method = ufuk.yolYontemi(me)` = first of: knows `kapi_bilimi` → `kapi` (gate); `yol_biliciligi` → `katlama` (fold); `gokyuzu_seyri` → `yelken` (light-sail); has tamed a canon species tagged `ozellik:ucan` or `megafauna` → `binek` (mount); knows `buyu` → `ruya` (dream road); else null → `"To search for the way to other worlds you must know sky navigation, gate lore, wayfinding or magic (ogren or bilgi_gelistir)."` (message omits the mount option).
2. `ap -= 1` (before the outcome).
3. In a transaction: `r = ufuk.yolAra(me, {nasil, cag, yarat: creator-helper bound to me})`:
   - If my world is `unutulmus` (forgotten) → `{durum:'yok'}`.
   - `unknown` = worlds ≠ mine with `kesif ∈ {bilinen, efsane}` and no active known route (`rotalar.aktif=1, bilinen=1`) linking them with mine.
   - `roll = d(100) + (me.akil ?? me.nufuz ?? default_stat) / route_wits_divisor`.
   - If `unknown` non-empty and `roll >= route_find_threshold`: target = random of `unknown`; if method = gate: create an `arac` via `yarat`: name `"{me} Gate"` (`"{me.ad} Kapısı"`), alt_tur "ancient gate", description `"An ancient stone ring found by {me}, opening onto the world {target}. {nasil}"`, stats `{hiz: gate_speed, menzil: gate_range, murettebat: 0, zirh: gate_armor, tuhaflik: gate_strangeness_base + d(gate_strangeness_die)}`, power `gate_power`, location me (if settlement) or me.konum_id. Then `seyahat.rotaAc({a: myWorld, b: target, yontem: method, kontrol_id: me.id, arac_id, aciklama: nasil, cag})` → route id; result `{durum:'yol', rid, hedef, yontem, arac_id, sure, tehlike, metin: "{me} found a way to the world {target}: {method name} ({sure} epochs)."}`; the tool chronicles `kesif` with `metin`, ids `[me, gate?]`.
   - Else if `roll >= unknown_world_threshold` and (worlds created this epoch + pending `ufuk_sezgi` rows) `< unknown_worlds_per_epoch` → `{durum:'sezgi', yontem}` (intuition).
   - Else `{durum:'yok'}`.
4. `yol` → returns `"Way found: route#{rid}, {method name}, {sure} epochs, danger {tehlike}. You can now set out with sefere_cik. Actions left: {ap}"`.
5. `sezgi` → `await ufuk.sezgiyiDogur(me, {nasil, yontem, cag, dunyaDogur})`: calls `kozmos.dunyaDogur({ilham: "Mortals named {me}, while searching for {nasil}, found the way to a world no one knew."})` (an LLM-driven world birth, inside the tool call); if born, tries `rotaAc` (failure → the world is marked `kesif='efsane'`); chronicles `kesif`: `"{me} discovered a world no one knew: {world}.{ But its way was lost in the mist; the world is remembered only as a legend.}"`. Tool returns `"You discovered an unknown world: {world}. You can travel there via route#{rid}. Actions left: {ap}"` or `"You sensed the existence of an unknown world: {world}; but its way could not hold. Actions left: {ap}"`. Errors or null fall through to failure.
6. Failure: chronicle `kesif`: `"{me} searched for the way to other worlds ({nasil}) but did not find it."` ids `[me]`; returns `"No way was found; the sky was silent this epoch. Actions left: {ap}"`.

**toprak_kesfet** (explore_land; C + olumlu, if `KESIF.arac_tur > 0`) — *"You set out to explore beyond the known lands: you find either a new region that is not on the map (valley, plateau, island, coastline, inland sea) or, in your own or a neighboring region, a place no one has set foot in (cave, lake, pass, forest, well). Success depends on your wits (your craft if you are a community) and your way-knowledge (seafaring, wayfinding, astronomy). If you are a community, your pioneers can settle there and found a new settlement. 1 action, {once} per epoch."*
Input: `tur` enum `bolge` (*"new lands not on the map"*) | `yer` (*"a new place in your own or a neighboring region"*); `ad` 2–60 (*"A unique proper name; following your language's naming rules"*); `alt_tur` ≤60 opt (*"valley, island, cave, lake, pass…"*); `aciklama` 100–900 (*"What you found, how you found it, what the first to set foot there saw"*); `konum_id` opt (*"Only for a place: the region it lies in (your own or a neighboring region); if empty, your own region"*); `yerles` boolean opt (*"If you are a community, your pioneers settle there and found a new settlement"*); `gorsel_prompt`.
Logic:
1. AP; `ctx.toprakKesif >= KESIF.arac_tur` → `"You already went exploring this epoch (World rule KESIF.arac_tur = {n})."`; name taken; `benzerAd(ad)` (near-duplicate of an existing single-word name: one-letter edit distance for short names, etc.) → `""{ad}" is too similar to the existing name "{b}"; choose another name."`.
2. `own = ustBolge(me)`. For `yer`: `parent = konum_id ? entity : own`; must be canon `bolge` and `yakinMi(me, parent)` → else `"A new place can only be found in your own or a neighboring region."`.
3. `ap -= 1`; `ctx.toprakKesif += 1`.
4. `roll = d(100) + (me.akil ?? me.zanaat ?? default_stat) / route_wits_divisor + (knows any of denizcilik, yol_biliciligi, gokbilim, gokyuzu_seyri ? KESIF.arac_bilgi_ek : 0)`.
5. `roll < KESIF.arac_esik`: chronicle `kesif`: `"{me} set out for unknown lands, but the road turned them back empty-handed."`; returns `"The exploration came to nothing; you found no new land this epoch (roll {round roll}, needed {KESIF.arac_esik}). Actions left: {ap}"`.
6. Success (transaction): `yarat(tur, stats = ufuk.toprakStatlari(tur)` (each stat of the type: base + die from KESIF, with special bases for `bereket` fertility and `tehlike` danger), `guc(me), konum = parent?.id (null for a region), tags ['keşif'])`; if region: `ufuk.bolgeyiYerlestir(id, myWorld, own)` (places it on the map near my region); bond `me → new` `kesfetti`; if `yerles` and me is `halk`/`yerlesim`: `oncuId = ufuk.onculer(me, new, cag)` (pioneer settlement: takes `KESIF.oncu_pay`% of population above the floor, requires `max(KESIF.oncu_en_az, SINIR.nufus_taban)`, creates a `yerlesim` "pioneer settlement" with a language-derived name, links language and faith; may return null). Chronicle `kesif`: `"{me} set out for unknown lands and found {a new region not on the map | a new place within {parent}}: {ad}{; its pioneers founded {settlement} there}."` ids `[me, new, oncu?]`. Returns `"#{id} {ad} was discovered{; your pioneers founded #{oncuId} {name} | ; but you are not numerous enough to settle (when yerles was requested but no settlement was made)}. Actions left: {ap}"`.

**gemi_yap** (build_ship; halk, yerlesim, hizip) — *"You build an interworld ship (requires shipbuilding knowledge). Its strength depends on your craft, your ore and your metallurgy. 1 action."*
Input: `ad` 2–60; `alt_tur` ≤60 opt (*"light-sailer, bone-hulled, generation ship…"*); `aciklama` 60–800; `gorsel_prompt`.
Logic: AP; not knows `gemi_yapimi` → `"Shipbuilding knowledge is required."`; name. `ap -= 1`. `soc = derin.toplumOf(me)` (society JSON: classes `k`, satisfaction `m`, economy `e{erzak food, maden ore, mal goods, fiyat}`; a default is synthesized if missing). `craft = (me.zanaat ?? me.servet ?? default_stat) + (soc.e.maden || 0)/ship_ore_divisor + (knows metallurgy ? ship_metallurgy_bonus : 0)`. `yarat(arac, alt_tur = "ship" + (alt_tur ? ": " + alt_tur : "")` (original `gemi…`; seyahat.js detects ships with `alt_tur LIKE '%gemi%'`), stats `{hiz: clamp(ship_speed_base + craft/ship_speed_craft_divisor + d(ship_speed_die), 0, 100), menzil: clamp(ship_range_base + d(ship_range_die), 0, 100), murettebat: ship_crew_base + d(ship_crew_die), zirh: clamp(ship_armor_base + craft/ship_armor_craft_divisor + d(ship_armor_die), 0, 100), tuhaflik: d(ship_strangeness_die)}`, `guc(me)`, location me|me.konum_id)`. Bond `me → ship` `sahip` "built in its shipyard". `soc.e.maden = max(0, maden − ship_ore_cost)`; write `varliklar.toplum` JSON (also for entities that had no society JSON before). Chronicle `uretim`: `"{me} built an interworld ship: {ad}."`. Returns `"Ship ready: #{id} {ad}. Actions left: {ap}"`.

**sefere_cik** (launch_expedition) — *"You organize an expedition along a known route to another world: to found a colony, open trade, explore, conquer or go on pilgrimage. The journey may take several epochs; on the way there may be pirates, storms, creatures and getting lost. 1 action."*
Input: `rota_id` int; `niyet` (intent) enum `koloni` colony | `ticaret` trade | `kesif` exploration | `fetih` conquest | `hac` pilgrimage; `yuzde` int 1..expedition_max_pct opt (*"What percent of your community sets out (for colony/conquest); default {expedition_default_pct}"*); `arac_id` opt (*"The ship or vehicle to use"*).
Logic:
1. AP; `route` = the route with that id among `seyahat.rotalar(myWorld)` → else `"There is no such known route leaving this world."`.
2. `seyahat.rotaKullanabilir(me, route)` error text → reject (requires the method's knowledge unless trading with the route's controller; mount method needs a tamed flying/megafauna species; ship method needs an owned ship; dead-river only via the realm of the dead; fold needs cosmic-resource access; route must be currently open).
3. Ongoing journey (`yolculuklar.yolcu_id = me, durum='yolda'`) → `"You already have an expedition on the road."`.
4. `arac_id` given: must be an `arac` owned by me → else `"This vehicle is not yours."`. If none given and the method requires a ship: auto-pick the first canon `arac` I own (any vehicle, not necessarily a ship).
5. `people = me.nufus ? round(nufus × min(expedition_max_pct, yuzde)/100) : me.murit ? round(murit × yuzde/100) : 1`.
6. Intent colony/conquest and `people < expedition_min_people` → `"You are not numerous enough for a colony or conquest."`.
7. `ap -= 1`. `y = seyahat.yolculukBaslat({yolcu: me, rota, niyet, nufus: people, arac_id, cag})` (caps departing population at `nufus − SINIR.nufus_taban`, deducts it from home, computes remaining epochs from route duration, vehicle speed and folding).
8. Chronicle `sefer`: `"{me} set out on a {label(niyet)} expedition to the world {other end's name} ({people} people{, with {vehicle}}, it will take {y.kalan} epochs)."` ids `[me, vehicle?]` (uses the pre-cap `people`).
Returns `"You set out: you will arrive in {y.kalan} epochs. Actions left: {ap}"`.

### Tools — creatures, spirits, ruins

**evcillestir** (tame_species; halk, yerlesim, olumlu, hizip) — *"You try to tame a creature species on your land. If you succeed it serves you in war, transport and trade; flying or gigantic ones can carry you between worlds. Dangerous and intelligent species are hard. 1 action."*
Input: `tur_id` int; `nasil` 10–300.
Logic: AP; if the entity is a species but non-canon → reason; not a canon species → `"No such living species."`; not near → `"This species is not on your land."`; already tamed (`evcil` bond) → `"You have already tamed it."`. `ap -= 1`.
```
skill      = (me.zanaat ?? me.akil ?? default_stat) + (me.karizma ?? 0)/tame_charisma_divisor + d(tame_skill_die)
difficulty = (t.tehlike || tame_default_danger) / (tame_danger_divisor/100)
           + (t.zeka || tame_default_intelligence)/2
           + (t has tag 'megafauna' ? tame_megafauna_penalty : 0)
           + d(tame_difficulty_die)
```
Success (`skill >= difficulty`): bond `me → species` `evcil` (description = how); chronicle `evcillestirme`: `"{me} tamed {t} ({nasil})."`; returns `"{t} now serves you. Actions left: {ap}"`.
Failure: with probability `(t.tehlike || tame_default_danger) / tame_attack_divisor`: for `nufus` and `can` (if present) `x = clamp(x × (100 − tame_attack_loss_pct)/100, 1, SINIR.nufus_tavan)`; save; bond `species → me` `avlar` "enraged by the taming attempt". Chronicle `evcillestirme`: `"{me} tried to tame {t} but failed."`; returns `"{t} did not submit. Actions left: {ap}"`.

**kimera_dok** (merge_species; all) — *"With biomancy you merge two creature species of your world that are near you (at most {YARATIK.kimera_dokuma_mesafe} steps) into a single chimera (requires biomancy knowledge). The chimera carries traits of both species; but it may slip out of control. 1 action."*
Input: `a_id`, `b_id` int; `ad` 2–60; `amac` 10–300.
Logic: AP; not knows `biyobuyu` → `"You must know biomancy to weave a chimera."`; A, B must be distinct canon species → `"Choose two separate living species."`; for each: different world → `"{t} is in another world; you can only weave species of your own world."`; `derin.mesafe(me, t) > YARATIK.kimera_dokuma_mesafe` (steps through the location chains to the nearest common ancestor; 99 if none) → `"{t} is too far (World rule YARATIK.kimera_dokuma_mesafe = {n} steps)."`; name taken. `ap -= 1`. `k = yaratik.kimeraDok(A, B, {cag, ad, dokuyan: me, aciklama: "{me} merged {A} with {B} through biomancy: {amac}"})` (creates the chimera species; not added to `ctx.yaratimlar`). Bond `me → k` `evcil` "self-woven". Chronicle `kimera`: `"{me} wove a chimera from {A} and {B}: {k}."` ids `[me, A, B, k]`. Returns `"A chimera was born: #{k.id} {k.ad}. Traits: {ozellik:* tags without prefix, or 'none'}. Actions left: {ap}"`.

**ruh_kapla** (bind_spirit; all) — *"With magic you bind a free spirit in your own or a neighboring region to an item, ship or structure there (requires magic knowledge). The item becomes ensouled; if bound to a structure the stone walks and a golem is born. 1 action."*
Input: `ruh_id`, `hedef_id` int.
Logic: AP; knows neither `buyu` nor `biyobuyu` → `"You must know magic to bind a spirit."`; spirit exists but not canon → `"No such free spirit: #{id} {name} is no longer free (it was bound to something or faded)."`; not a canon spirit → `"No such free spirit."`; target not canon `esya`/`arac`/`yapit` → `"A spirit can only be bound to an item, vehicle or structure standing in the world.{ + non-canon reason}"`; for spirit and target: different world or `!yakinMi(me, x)` → `"{x} is too far; you can only join a spirit and an item in your own or a neighboring region."`. Then `ap -= 1; result = otesi.ruhKapla(ruh_id, hedef_id, me, cag)`; on a thrown error: `ap += 1` and reject with the message. Returns `"The spirit was bound{; a golem was born: #{id}} (if result is an id of a species). Actions left: {ap}"`.

**kalinti_ara** (search_ruins; all) — *"You investigate a ruin, remains or a dead god's bones on your land: you may find a lost knowledge, an unowned item, or wake something sleeping. 1 action."*
Input: `hedef_id` int (*"The id of a ruin, remains, or a place with a god's corpse"*); `nasil` 10–300.
Logic:
1. AP; `isRuin` = target has a tag in {`harabe` ruin, `tanrı cesedi` god corpse, `boş mezar` empty tomb} OR its `alt_tur` matches `/harabe|kalıntı|yıkıntı|mezar|ceset/i` (ruin|remains|rubble|tomb|corpse — LANGUAGE-SPECIFIC: replace with tags); and `durum ∉ {reddedildi, yok_edildi}` (dead/`olu` is allowed) → else `"This is not a ruin or remains."`.
2. Different world or not near → `"Too far."`. `ap -= 1`.
3. `score = (me.akil ?? me.nufuz ?? default_stat) + (toplumOf(me).k.katip || 0) × ruin_scribe_weight + d(ruin_die)` (scribe class headcount from the society JSON; a default society is used if none).
4. `lost` = canon `teknoloji` tagged `kayıp` in the ruin's world; `loose` = canon `esya` with `konum_id = ruin` and no active owner.
5. Outcome (first match):
   - `score >= ruin_knowledge_threshold` and `lost` non-empty: random lost knowledge `t`; `ogret(me, t, cag, "found in the remains of {h}")`; remove tag `kayıp` from `t`. Agent text: `"You found the forgotten knowledge {t} in the remains of {h}"`; chronicle: `"{me} rediscovered the forgotten knowledge {t} in the remains of {h}."`
   - `score >= ruin_item_threshold` and `loose` non-empty: first item; bond `me → item` `sahip` "found it in the remains of {h}". Agent: `"{item} was found in the remains of {h} and is now yours"`; chronicle: `"{me} found and took {item} in the remains of {h}."`
   - `score < ruin_curse_threshold`: tag me `lanetli`. Agent: `"Something sleeping in the remains of {h} awoke; a curse settled upon you"`; chronicle: `"{me}, digging in the remains of {h}, woke something sleeping; a curse settled upon them."`
   - else: agent `"You searched the remains of {h}; you found nothing but dust, bone and whispers"`; chronicle `"{me} searched the remains of {h} but found nothing but dust, bone and whispers."`
6. Chronicle kind `kesif`, ids `[me, h]` (the agent's free-text "how" is not chronicled). Returns `"{agent text}. Actions left: {ap}"`.

### Tools — captivity

Captivity = an active `esir` bond `captor → captive` (both entities) plus tag `esir` on the captive. Captives (`olumlu`) can only use `kac` (gating wrapper).

Helper `benimEsirim(me, id)` ("my captive member"): `e` = canon entity; `t = esirMi(e)` must exist; linked if: active bond `e → me` of type `korur`, `soyundan` or `yoldas` (protects / descends / companion) OR `ayniBolge(e, me)` OR (`hami(e)` and `hami(me)` are the same son and me has one). Returns `{e, t}` or null.

**kac** (escape; olumlu) — *"If you are a captive you try to escape your captors; your agility and wits decide. If caught you are wounded. 1 action."*
Input: `nasil` 10–300.
Logic: AP; `captor = esirMi(me)` null → `"You are not a captive."`. `ap -= 1`. `chance = clamp((me.ceviklik || escape_default_stat)/2 + (me.akil || escape_default_stat)/escape_wits_divisor − (captor.savunma ?? default_stat)/escape_defense_divisor, escape_min_chance, max(escape_min_chance, escape_chance_cap))`. `d(100) <= chance`: deactivate all active `esir` bonds targeting me; remove tag `esir`; chronicle `kacis`: `"{me} escaped from the hands of {captor}: {nasil}"` ids `[me, captor]`; returns `"You escaped. Actions left: {ap}"`. Else: if `me.can` exists, `can = clamp(can − escape_fail_wound, 1, SINIR.can_tavan)`; chronicle `kacis`: `"{me} tried to escape from {captor} but was caught."`; returns `"You were caught. Actions left: {ap}"`.

**fidye_ode** (pay_ransom; communities) — *"You pay ransom to the captors for a member of yours who fell captive (a mortal bound to you or from your land): your wealth or prosperity decreases, theirs increases, the captive returns. 1 action."*
Input: `esir_id` int.
Logic: AP; `x = benimEsirim(me, esir_id)` null → `"This mortal is not one of your captives, or is not a captive."`; captor is me → `"{e} is your own captive; ransom is only paid to captors."`; `rich = (me.servet ?? 0) >= ransom_min_wealth OR (me.refah ?? 0) >= ransom_min_wealth + ransom_prosperity_extra` → else `"You do not have enough wealth for a ransom."`. `ap -= 1`. For `servet` and `refah` independently: me `−ransom_amount` if present; captor `+ransom_amount` if present (clamp 0–100) — a payer with both stats pays twice. Deactivate captive's `esir` bonds; remove tag `esir`; if captor is a community: `tIliskiDegistir(me, captor, +ransom_relation_gain, "ransom")`. Chronicle `fidye`: `"{me} paid ransom to {captor} for {e}; the captive returned home."` ids `[me, e, captor]`. Returns `"{e} returned. Actions left: {ap}"`.

**esiri_kurtar** (rescue_captive; C + olumlu) — *"You try to free a captive by force: your strength against the captors' defense. Failure breeds enmity. 1 action."*
Input: `esir_id` int; `plan` 10–300.
Logic: AP; `x = benimEsirim(me, id)` or else (any captive whose captor is near me) → null → `"There is no captive to rescue, or the captors are too far."`; captor is me → `"{e} is your own captive; you cannot raid yourselves."`. `ap -= 1`. `g = (me.guc ?? me.savascilik ?? default_stat) + d(rescue_die)`; `s2 = (t.savunma ?? t.guc ?? t.savascilik ?? default_stat) + d(rescue_die)`. `g >= s2`: free the captive (deactivate `esir`, remove tag); chronicle `kurtaris`: `"{me} rescued {e} from the hands of {captor}: {plan}"`; returns `"{e} was rescued ({g}–{s2}). Actions left: {ap}"`. Else: if not already enemies, bond `captor → me` `dusman` "raid for {e}"; chronicle `kurtaris`: `"{me} tried to rescue {e}, but {captor} repelled the raid."`; returns `"The raid was repelled ({g}–{s2}). Actions left: {ap}"`. Chronicle ids `[me, e, captor]`.

### Tools — armies

**ordu_topla** (raise_army; communities) — *"You raise an army from your population (or disciples); the soldiers are subtracted from the population (a community without population hires mercenaries and pays from its wealth). It joins your ongoing war and protects you. Equipment depends on your craft and knowledge. One army per community. 1 action."*
Input: `ad` 2–60 (*"The army's name, from your own language"*); `yuzde` number 1–100 opt (*"What percent of the population goes under arms (up to the world-rule cap)"*), default `army_default_pct`.
Logic:
1. AP; `orduOf(me)` exists → `"You already have an army."`; name.
2. `key` = `nufus` | `murit` | none; `purse = key ? null : servetAnahtari(me)`. Neither → `"You have no population or disciples to put under arms, nor wealth to hire mercenaries."`. Purse and `me[purse] < mercenary_cost` → `"Your {wealth|prosperity} is not enough to keep a mercenary army ({value} / {mercenary_cost}; World rule OLUMLU_ARAC.ordu_parali_servet)."`.
3. `base = key ? me[key] : round((me.guc || army_default_power) × army_power_multiplier)`.
4. `floor = key=='murit' ? cult_min_disciples : key ? (halk ? SINIR.halk_nufus_taban : SINIR.nufus_taban) : 0`.
5. `share = army_population_deduct_pct/100`; `maxSoldiers = key ? (share > 0 ? floor(max(0, base − floor)/share) : ∞) : ∞`.
6. `soldiers = min(round(base × clamp(yuzde, 1, army_max_pct)/100), maxSoldiers, SINIR.ordu_tavan)`.
7. `soldiers < army_min_soldiers` → `"An army needs at least {army_min_soldiers} soldiers (World rule OLUMLU_ARAC.ordu_en_az); only {soldiers} people can be put under arms. Raise the percentage (at most {army_max_pct}%) or grow."`.
8. `war` = first `olay` with `alt_tur='savaş'` whose tags contain `"suruyor"` (ongoing) and `"taraf:{me.id}"`.
9. Stats: `buyukluk = soldiers`; `moral = clamp(army_morale_base + d(army_morale_die), 0, 100)`; `techizat = clamp(army_equipment_base + (knows metallurgy ? army_metallurgy_bonus : 0) + round(zanaatGucu(me)/army_craft_divisor), 0, 100)`; `deneyim = knows 'savas' ? army_experience_war : army_experience`.
10. Description: `"{me} raised an army of {soldiers}{; it marches for {war name}}. {origin} {state}"` where origin = population: `"The soldiers were taken from {me}'s own people, from the field and the workbench."` | disciples: `"Disciples fill the ranks; they are bound by oath before the sword."` | mercenary: `"The soldiers are mercenaries; {me} hired them with its wealth."`; state = `"The army is {well-equipped (techizat >= 50) | under-equipped}, its morale {high (moral >= 50) | broken}{; those who know war lead it (if knows 'savas')}."` (50s hard-coded).
11. `yarat(ordu, alt_tur = tarikat ? "holy guard" : hizip ? "mercenary army" : "people's army", stats, guc(me), location me|me.konum_id, tags ["taraf:{me.id}", "savas:{war.id}" if war])`. Bonds: `army → me` `korur`; if war: `army → war` `parcasi`.
12. Deduct: `key` → `me[key] = max(floor, round(me[key] − soldiers × share))`; purse → `me[purse] = clamp(me[purse] − mercenary_cost, 0, 100)`. Save. `ap -= 1`.
13. Chronicle `ordu`: `"{me} called {soldiers} people to arms: {ad}."` ids `[me, army]`. Returns `"#{id} {ad} was raised ({soldiers} soldiers). Actions left: {ap}"`.

**komutan_ata** (appoint_commander; communities) — *"You appoint a named mortal (bound to you or from your land) at the head of your army; the commander's strength and charisma reflect on the army. Free, {once} per epoch."*
Input: `olumlu_id` int.
Logic: counter `komutan` vs `commander_per_epoch` (`"You already appointed a commander this epoch"`); `army = orduOf(me)` null → `"Raise an army first (ordu_topla)."`; non-canon → reason; not a canon `olumlu` → `"The commander must be a living, named mortal."`; captive → `"{k} is a captive."`; not same region and no active bond `k → me` of type `korur`/`soyundan`/`yoldas` → `"{k} is not bound to you."`. Deactivate the army's existing `komutan` bonds; bond `k → army` `komutan`; `army.moral = clamp((army.moral || commander_default_morale) + round((k.karizma || default_stat)/commander_charisma_divisor), 0, 100)`. Counter++. Chronicle `ordu`: `"{k} took command of {army}."` ids `[k, army, me]`. Returns `"{k} is now the commander of {army}."`.

### Tools — barter, debt

Shared: tradable kinds `TAKAS_TURLERI` = `kaynak, esya, arac, yapit`; `value(x) = x.deger ?? max(0, x.kudret, x.hasar, x.koruma, x.ihtisam, x.hiz)` (missing → 0). Party validation `tarafGecersiz(me, h)`: non-canon → (intended) reason; missing / not canon / self / not a party type → `"Invalid party: must be a community or a named mortal."`; `!yakinMi` → `"{h} is too far; only with those in your own or a neighboring region."`; enemies → `"{h} is your enemy."`.

**takas** (barter; C + olumlu) — *"You barter with a community or a named mortal: you give resources, items or vehicles you own and take things they own (if you want nothing, it is a gift). The offer's value, your relation and a die decide acceptance; a successful barter warms the relation. {barter_ap_cost} action."*
Input: `hedef_id` int; `ver_ids` int[1..barter_max_items] (*"Things you own and will give"*); `al_ids` int[0..barter_max_items] opt (*"Things they own that you want"*); `sart` 5–200 (*"The terms of the barter"*).
Logic:
1. `ap(barter_ap_cost)`; party validation.
2. Dedupe ids. Each give: canon, tradable kind, owned by me → else `"{x or 'This'} is not yours or cannot be traded (it must be a resource, item, vehicle or structure)."`. Each take: owned by `h` → else `"{x or 'This'} is not {h}'s or cannot be traded."`. Overlap → `"The same thing cannot be on both sides."`.
3. `offer = Σ value(give)`; `ask = Σ value(take)`; `rel = tIliski(me, h)`; `score = offer + round(rel / barter_relation_scale) + d(barter_die)`. `ap −= barter_ap_cost`.
4. If takes non-empty and `score < ask`: relation `−barter_reject_relation_loss` "rejected barter"; chronicle `ticaret`: `"{me} asked {h} for {takes} in exchange for {gives}; {h} found the offer too low."` ids `[me, h]`; returns `"{h} turned down the offer ({score} – {ask}). Actions left: {ap}"`.
5. Else transfer: for each give → deactivate all active `sahip` bonds to it, bond `h → x` `sahip` "barter: {sart}"; for each take → same to me. Relation `+barter_relation_gain` ("barter" or "gift"). Chronicle `ticaret`: with takes `"{me} and {h} bartered: {gives} in exchange for {takes} ({sart})."`; gift `"{me} gave {gives} to {h} as a gift ({sart})."` ids `[me, h, …gives, …takes]`. Returns `"The barter went through. Actions left: {ap}"`.

**borc_ver** (lend; C + olumlu) — *"You lend to a community or a named mortal: amount, what is lent, and term (after how many epochs it is repaid). The amount is subtracted from your wealth or prosperity and passes to them (if you have neither you cannot lend; at most {debt_max_amount}, term at most {debt_max_term} epochs). No one collects; but if it is not repaid by the due date it enters the chronicle and relations cool. {debt_ap_cost} action."*
Input: `borclu_id` int; `miktar` int ≥1 (*"Amount of the debt (up to World rule OLUMLU_ARAC.borc_tavan)"*); `ne` 2–80 (*"What is lent: grain, silver, salt, ship hire…"*); `vade_cag` int ≥1 opt (*"After how many epochs it is due (up to World rule OLUMLU_ARAC.borc_vade_tavan); if empty, the world-rule default"*), default `debt_default_term`.
Logic: `ap(debt_ap_cost)`; party validation; `miktar > debt_max_amount` → `"At most {debt_max_amount} can be lent in a single loan (World rule OLUMLU_ARAC.borc_tavan)."`; `vade_cag > debt_max_term` → `"The term can be at most {debt_max_term} epochs (World rule OLUMLU_ARAC.borc_vade_tavan)."`; existing active `borclu` bond `h → me` → `"{h} already owes you an unpaid debt."`; `kv = servetAnahtari(me)` null → `"You have no wealth or prosperity to lend."`; `me[kv] < miktar` → `"You do not have enough {wealth|prosperity} to lend this much ({me[kv]})."`. `me[kv] −= miktar` (clamp 0–100); if `kb = servetAnahtari(h)`: `h[kb] += miktar` (clamp). `due = cag + vade_cag`. Bond `h → me` `borclu` with description `borcAciklama(miktar, ne.trim(), due)` = `"{miktar} {ne}; vade Çağ {due}"` (machine-parsed later — use structured columns in the new app). Relation `+debt_lend_relation_gain` "debt". `ap −= debt_ap_cost`. Chronicle `borc`: `"{me} lent {miktar} {ne} to {h}; due in Epoch {due}."` ids `[me, h]`. Returns `"{h} is now in your debt: {miktar} {ne}, due Epoch {due}. Actions left: {ap}"`.
Overdue processing (`medeniyet.borcGecikmeleri`, run at the start of each mortal turn and by the engine): unpaid debts past `due` are chronicled, marked `vadesi geçti` (overdue) in the description and cool the creditor's relation (spec in medeniyet.js).

**borc_ode** (repay_debt; C + olumlu) — *"You repay your debt to someone: if you have wealth or prosperity, the debt amount passes to them (otherwise you repay in kind and no wealth passes); the debt closes and relations warm (even if overdue). {debt_ap_cost} action."*
Input: `alacakli_id` (creditor) int.
Logic: `ap(debt_ap_cost)`; `b` = oldest active `borclu` bond `me → h`; `m = borcOku(b)` (parses `^(\d+) (.*?); vade Çağ (\d+)` → `{miktar, ne, vade, gecti: description contains "vadesi geçti"}`); none → `"You have no debt to {h or 'them'}."`. `kv = servetAnahtari(me)`, `kh = servetAnahtari(h)`. If `kv` and `me[kv] < miktar` → `"You do not have the {wealth|prosperity} to repay the debt ({me[kv]} / {miktar})."`. If `kv`: `me[kv] −= miktar`; if `kv && kh`: `h[kh] += miktar`. Deactivate the bond. Relation `+debt_repay_relation_gain` "debt repaid". `ap −= debt_ap_cost`. Chronicle `borc`: `"{me} repaid its debt to {h} ({miktar} {ne}){ even though it was overdue}."` ids `[me, h]`. Returns `"Debt repaid. Actions left: {ap}"`.

### Chronicle kinds written by this module

`dil` (language), `uretim` (production), `insa` (building), `kultur` (culture), `kesif` (discovery/exploration/ruins), `kaynak` (resource claim), `goc` (migration), `ticaret` (trade/barter), `savas` (war declaration), `tapinma` (worship/sermon), `bilgi` (knowledge), `diplomasi`, `macera` (adventure), `sefer` (expedition), `evcillestirme` (taming), `kimera`, `entrika` (intrigue: sabotage, spies), `inkar` (denial), `kehanet` (prophecy), `kacis` (escape), `fidye` (ransom), `kurtaris` (rescue), `ordu` (army), `borc` (debt), `soy` (lineage/adoption), `tanri_savasi` (god combat), `dunya` (after-death notes), `soz` (final utterance), plus `dua` (via yaratici.js).

### Exports summary

| Export | Purpose |
|---|---|
| `OLUMLU_K` | live tunables object (namespace OLUMLU_ARAC) |
| `ustBolgeId(v)`, `ustBolge(v)`, `ayniBolge(a,b)`, `yakinMi(a,b)` | region/adjacency helpers |
| `ajanAdaylari(n)`, `dunyaPaylari(list, total)` | agent selection |
| `ogrenebilirMi(me, o)` | can `me` learn from `o` |
| `baglamMetni(v, w, {tam})` | mortal context text |
| `borcOku` (re-export), `borcVadeleri(cag)` | debts |
| `esirMi(v)` | captor of `v` |
| `buildOlumluServer(vId, ctx)` | MCP tool server for one turn (with `.aracBedelleri`) |
| `olumluTuru(v, onEvent)` | run one mortal's turn; returns created ids |

### Bugs, design smells and notes for the rewrite

- `tarafGecersiz` returns `err(kd)` (a result object) for non-canon parties; the caller wraps it again with `err(g)`, producing a garbage rejection text. Return a string.
- `savas_ilan_et` bypasses `derin.savasIlan`: it does not check the global war cap (`MOTOR.savas_tavan`) and does not dissolve alliances, so two parties can be allies and enemies at once. Diplomacy's tribute-insolence path and adventure theft add `dusman` bonds directly, also bypassing ceasefire/cap rules. Route all hostility through one function.
- Peace via `diplomasi` deactivates enmity but creates no ceasefire (the engine's peace does), so war can be redeclared immediately.
- `hami()` falls back to the creating son (`yaratan_id`) when there is no `tapar` bond, so `inkar_et` can be repeated every epoch against the creator son, draining its existence each time; godless entities still "have" that patron. Denial also leaves creator (`t`) worship intact.
- `sabotaj`: success and "caught" are mutually exclusive, so the poison `katil` (killer) is always null; and when the sabotage fails without being caught, the chronicle still reports "a mysterious poisoning/fire/rift occurred".
- `ruh_kapla` and `dirilis_ayini` catch exceptions inside the transaction and return a rejection, so partial writes made before the throw are committed (the transaction is not rolled back). `rota_kesfet` deducts AP outside any transaction and runs an LLM world birth inside the tool call.
- `uret` does not dedupe `kaynak_ids` (one resource counted/drained twice); `sahip_id` accepts any canon entity anywhere (regions, gods' items far away).
- `insa_et` chronicles a dedication even when `adanan_ogul_id` is invalid/dead.
- `kultur_yarat` links `ilgili_ids` without canon/world checks.
- `komutan_ata` re-adds the charisma morale bonus on every appointment (even re-appointing the same commander) → morale pumping each epoch.
- `fidye_ode` deducts both wealth and prosperity when both exist (double cost) and credits both.
- `toprak_kesfet` prints "not numerous enough to settle" when `yerles` was requested by a type that cannot settle (hizip/tarikat/olumlu). Its roll uses `akil ?? zanaat` while `rota_kesfet` uses `akil ?? nufuz`.
- `gemi_yap` writes a synthesized default society JSON into entities that had none; tunable labels say "miners" but the code uses economy ore stock.
- `sefere_cik` auto-picks any owned vehicle (even a gate) for ship routes; the chronicle shows the requested headcount, not the capped one actually deducted by `yolculukBaslat`.
- `tanriya_meydan_oku` has no proximity/world check and no per-epoch cap; a god's fame gain `un += tanri_ezme_un` is uncapped; death is written directly (`durum='olu'`) instead of through a single death service.
- `maceraya_cik`/`vaaz_et`/`diplomasi` contain hard-coded defaults (`can || 100`, `murit || 100`, population default 100) and `ajanSec` hard-codes the 1000 bonus for `ajan seçili`; ordu description thresholds (50) are hard-coded. Make them tunables (project rule: no untunable constants).
- Many stat fallbacks use `||` (treats 0 as missing) vs `??` elsewhere — inconsistent; decide one semantics.
- `ajanAdaylari` puts entities of forgotten (or unknown) worlds into the first world's group, so they can still act; the single-world path does not append forced (`ajan seçili`) picks beyond `n` while the multi-world path does; `dunyaPaylari` does not subtract manual per-world counts from the total.
- Read tools (`varlik_ara`, `varlik_incele`) are omniscient (any world, any entity).
- Per-section budgets in `baglamMetni` are fixed, so `dunyaya_bak`'s ×3 "wider" view only widens the overall cap, not the sections.
- Debt terms and amounts are encoded in the bond description string and parsed by regex (`borcAciklama`/`borcOku`), and ships are detected by `alt_tur LIKE '%gemi%'`; ruins by a Turkish regex on `alt_tur`. Use structured columns/tags.
- Tool cost (free vs 1 AP) is inferred by regex over Turkish descriptions (`bedavaMi`); make it explicit metadata.
- `dil_kur` lets a community found unlimited new languages (1 AP each), each switching its `konusur` bond; its settlements keep the old language and no dialect link is made for communities.
- Mortal creations go straight to canon with no Fate review; decide whether the new design should route them through Fate like son creations.
- LANGUAGE-SPECIFIC (drop or replace): `ekDuzelt` (suffix/apostrophe fixing on all tool texts and prompts), `toplulukIci` (locative phrase), `kez()` ("once"/"N times"), the `"{god}'i Yaralayan"` title, `"{X} lehçesi"` dialect naming, the `söz:` utterance marker in `sozuAyikla`, `toLocaleLowerCase('tr')`, the instruction "You think and speak in Turkish", and the Turkish ruin regex.

## 4. Map generation (harita.js, harita-gen.js)

### Overview and file roles

- `public/harita-gen.js` is a **pure, dependency-injected ES module** shared by the server (Node) and the browser. It holds the whole generator `dunyaHaritasi` (world map), the noise and RNG, the world-type table `DUNYA_TURLERI` (world types) with biomes and palettes, the biome classifier `biyom` / `biyomIndeks`, and the water-region test `suMu`. It does no I/O. The caller passes in the Delaunay implementation:
  - The server imports `Delaunay` from npm `d3-delaunay@6.0.4`.
  - The browser uses `d3.Delaunay` from the global d3 v7.9.0 bundle (cdnjs), which contains d3-delaunay 6.x.
- `src/harita.js` is the server wrapper. It does the DB reads, migrates legacy coordinates, caches the map per world (`haritaHesapla`), **persists newly placed coordinates** back to `varliklar.harita_xy`, offers manual invalidation (`haritaGecersiz`), and builds the LLM context text (`cografyaSatirlari`).
- No Lloyd relaxation is used. Points come from a **jittered grid** (one point per 22-px grid cell, jitter ±45% of the cell size). The generator builds a Delaunay triangulation of all points. Each point's Voronoi cell is a map "cell". Regions are grown over the cell adjacency graph by a multi-source Dijkstra flood. Elevation and moisture come from seeded fractal value noise.
- The map is "infinite" in principle. The computed window is the bounding box of every positioned entity plus a 900-px pad, snapped to the 22-px grid. Grid points depend only on `(seed, gx, gy)`, so geometry stays stable when the window grows. Cell **indices** change, and so can adjacency near the old border (see smells).

### Constants (hard-coded, NOT tunable in the old code)

| Constant | Original | Value | Meaning |
|---|---|---|---|
| core_width / core_height | `W`, `H` | 3000, 2040 | Nominal world size. The server exports it as `HARITA_BOYUT`. `ufuk.js` uses it to clamp new frontier region seeds. |
| legacy_core_rect | `CEKIRDEK` | `{x:1000, y:680, w:1000, h:680}` | Target rectangle when migrating v1 (0–1 normalized) coordinates. |
| known_ring_steps | `BILINEN_ADIM` | 4 | Number of BFS rings of "fog" (known=2) around known cells. |
| grid_spacing | `ARALIK` | 22 | Grid cell size in map units (px). |
| window_pad | `PAY` | 900 | Padding around the entity bounding box. |
| region_radius | `YARICAP` | 320 | Max distance from a top-level region seed that its flood may reach. |
| wide_water_min_cells | literal | 40 | A water component must have at least this many cells to count as "wide water" (sea) for water-region seeds. |
| seed_attempts | literal | 80 | Random candidates tried when placing a new region seed. |
| seed_spacing_target | literal | 300 | Preferred distance from the nearest existing region seed. |
| seed_jitter_spacing / center | literal | 40 / 80 | Random score noise amplitudes (spaced case / first-seed case). |
| relocate_bfs_rings | literal | 40 | Max BFS rings when relocating a region seed that sits on the wrong terrain. |
| point_attempts | literal | 24 | Random candidates when placing a point entity. |
| point_parent_ring | literal | 2 | Ring radius around a non-region parent point. |
| point_place_recursion_guard | literal | 8 | Max parent-recursion depth in `yerlestir`. |
| sea_sample_count | literal | 4000 | Elevation samples used to find sea level. |
| sea_sample_trim | literal | 20 | Sample-index trim for the `alt` and `ust` extremes. |
| min_extent_w / h | literal | 200 / 140 | Minimum width/height of the known-area bounding box (`kapsam`). |
| flood edge cost | literal | `1 + |Δelev|·40 + (coast crossing ? 30 : 0)` | Dijkstra edge weight. |
| climate share min | literal | 0.12 | A biome must cover at least 12% of a region to be listed. |
| elevation label thresholds | literal | 0.45 / 0.22 / 0 | Thresholds for mountainous / hilly / plain / water. |

> New design: per the project rule "no untunable constants", expose these as `map.*` settings. They should still be fixed per world, because changing them reshapes existing maps.

### Tunables declared in harita.js (UI network graph, unrelated to map generation)

| key (English snake_case) | original key | default | min | max | group | English label |
|---|---|---|---|---|---|---|
| network_focus_node_cap | `ARAYUZ.ag_odak_tavan` | 10000 | 10 | 100000 | Interface (Arayüz) | Network: max nodes shown around the focus. If exceeded, the step count is reduced automatically and the UI says so. The "whole network" view ignores this. |
| network_auto_focus_max_links | `ARAYUZ.ag_oto_odak_bag` | 50 | 3 | 100000 | Interface | Network: max links of an automatically chosen focus node, so hub nodes do not become the focus and turn the view into a tangle. |

Related tunables elsewhere: `KESIF.harita_uzaklik` (300, 50–2000, "distance of a new region's seed from its source region, close enough to be neighbours") and `KESIF.harita_deneme` (attempt count) in `ufuk.js`.

### Hash and RNG (exact)

**String hash, `hash(s)`: 32-bit FNV-1a over Unicode code points.**
```
h = 2166136261
for each code point c in String(s):      // JS for..of iterates code points; uses c.codePointAt(0)
    h = h XOR c
    h = imul(h, 16777619)                 // 32-bit wrap-around multiply
return h as unsigned 32-bit
```

**PRNG, `mulberry(a)`: standard mulberry32. Returns floats in [0,1).**
```
state a (int32)
next():
    a = (a + 0x6D2B79F5) mod 2^32
    t = imul(a XOR (a >>> 15), 1 | a)
    t = (t + imul(t XOR (t >>> 7), 61 | t)) XOR t
    return ((t XOR (t >>> 14)) >>> 0) / 4294967296
```

Python reference port (verified against JS to produce identical output):
```python
M32 = 0xFFFFFFFF
def fnv1a32(s: str) -> int:
    h = 2166136261
    for ch in s:                       # code points
        h ^= ord(ch); h = (h * 16777619) & M32
    return h
def imul(a, b): return (a * b) & M32
def mulberry32(seed: int):
    a = seed & M32
    def nxt():
        nonlocal a
        a = (a + 0x6D2B79F5) & M32
        t = imul(a ^ (a >> 15), a | 1)
        t = ((t + imul(t ^ (t >> 7), t | 61)) & M32) ^ t
        return ((t ^ (t >> 14)) & M32) / 4294967296
    return nxt
```
Test vectors (from the running old code):
- `hash("") = 2166136261`, `hash("Aerona") = 216979349`, `hash("Aerona:h") = 1646082319`, `hash("çağ") = 3116089038`.
- `mulberry(hash("Aerona"))` gives `0.9770483230240643, 0.40212616417557, 0.5175353118684143`.

### Value noise (`gurultu(seed)`)

```
perm = uint16[512]; r = mulberry(seed)
p = [0..255]
for i = 255 down to 1: j = floor(r() * (i+1)); swap p[i], p[j]          // Fisher–Yates
for i in 0..511: perm[i] = p[i & 255]
val(x, y) = perm[(perm[x & 255] + y) & 511] / 255                         // x, y are integers (int32 semantics; & on negatives = two's complement)
smooth(t) = t*t*(3 - 2t)
n2(x, y):
    xi = floor(x), yi = floor(y), xf = x - xi, yf = y - yi
    a = val(xi, yi), b = val(xi+1, yi), c = val(xi, yi+1), d = val(xi+1, yi+1)
    u = smooth(xf), v = smooth(yf)
    return a + (b-a)u + (c-a)v + (a-b-c+d)uv
fbm(x, y, oct=5):
    t = 0, amp = 1, f = 1, norm = 0
    repeat oct times: t += amp * n2(x*f, y*f); norm += amp; amp *= 0.5; f *= 2.03
    return t / norm                                                       // range ~[0,1]
```
Test vectors with `g = gurultu(hash("Aerona:h"))`: `g(0.5,0.5) = 0.2811705769571603`, `g(10.3,-4.7,3) = 0.4057523126927773`, `g(-123.456,789.01) = 0.49524498099103353`.

### Terrain field (`arazi(seed, ar)`, cached forever per `seed|JSON(ar)`)

Inputs come from the world's terrain record (`ar`, `dunyalar.arazi` JSON):
- mountainousness `daglik` (default 1)
- moisture offset `nem` (default 0)
- sea fraction `deniz` (default 0.52)

```
g  = gurultu(hash(seed + ':h'))    // elevation detail
g2 = gurultu(hash(seed + ':m'))    // moisture
g3 = gurultu(hash(seed + ':k'))    // continents
r  = mulberry(hash(seed + ':o')); ofx = r()*50; ofy = r()*50
elevation(x,y) = g3(x/1500 + ofx, y/1500 + ofy, 3) * 0.95
               + ( g(x/300 + ofx, y/300 + ofy) * 0.75 + g(x/90 + ofx, y/90 + ofy, 3) * 0.25 ) * daglik
moisture(x,y)  = g2(x/330, y/330, 4) + nem                  // NOTE: no offset
rr = mulberry(hash(seed + ':ornek'))
samples = [ elevation(-6000 + rr()*15000, -6000 + rr()*14000) for k in 0..3999 ]   // x's rr() first, then y's
sort ascending
sea_level = samples[ min(len-21, max(20, floor(len * deniz))) ]
alt (lowest) = samples[20]; ust (highest) = samples[len-20]
```
In the old code the cache (`araziOnbellek`) is an unbounded module-level Map.

### `dunyaHaritasi({seed, varliklar, Delaunay, arazi, tur})`: full algorithm

Inputs:
- `varliklar`: entities, each `{id, ad, tur, alt_tur, konum_id, xy: [x,y] | null, ...}`, ordered by id.
- `tur`: world type key or null.

**1. Window.**
```
bbox over every entity with xy (all types). If none: x0 = x1 = W/2 (1500), y0 = y1 = H/2 (1020).
x0 = floor((x0 - 900)/22)*22; y0 = floor((y0 - 900)/22)*22
x1 = ceil((x1 + 900)/22)*22;  y1 = ceil((y1 + 900)/22)*22
pencere (window) = {x: x0, y: y0, w: x1-x0, h: y1-y0}
```

**2. Points (row-major, y outer).**
```
for gy in [y0/22, y1/22): for gx in [x0/22, x1/22):
    r = mulberry(hash(`${seed}:${gx}:${gy}`))
    px = (gx + 0.5 + (r()-0.5)*0.9) * 22
    py = (gy + 0.5 + (r()-0.5)*0.9) * 22
```
An empty world has a window of 1826×1826 at (594,110) and N = 6889 points.

**3. Triangulation.**
- `del = Delaunay.from(pts)`
- `vor = del.voronoi([x0,y0,x1,y1])` (used only for rendering polygons)
- `komsu[i] = [...del.neighbors(i)]` (adjacency, in d3's iteration order)
- `hucre(xy) = del.find(x, y)` (nearest point)

**4. Per-cell fields.**
- `yuk[i] = elevation(pts[i])` and `nem[i] = moisture(pts[i])`. Both are stored in **Float32Array**, so values are rounded to float32.
- `deniz = sea_level` (a float64).
- `kara(i) = yuk[i] > deniz` (land; strict).
- `yNorm(i)` (normalized elevation):
  - land: `min(1, (yuk-deniz)/(ust-deniz))`
  - water: `-min(1, (deniz-yuk)/(deniz-alt))`
  - The range is [-1, 1].
- The old code also creates an unused `rnd = mulberry(hash(seed))` (dead code).

**5. Region sets.**
- `bolgeler` = entities with `tur == 'bolge'` (region).
- `ustBolge(v)` = the parent entity if `v.konum_id` points to an entity **in the list** whose type is `bolge`.
- `ustler` = top-level regions. `altlar` = sub-regions (the parent is a region).

**6. Water components.**
- Flood-fill (stack DFS) over water cells (`!kara`) via `komsu`. Each water cell gets a component id and the size of its component.
- `genisSu(i)` (wide water) = `!kara(i) && componentSize >= 40`.
- `karaHucre` = land cells in index order. `suHucre` = wide-water cells in index order.

**7. Region seed selection, `tohumSec(v, candidates, isSub=false)`.** It uses a shared set `kullanilan` (used seed cells) and the outputs `yeniXY` (new coordinates to persist) and `tasinan` (relocated coordinates to persist).
```
if v.xy:
    i0 = hucre(v.xy)
    wanted(i) = isSub ? (i in candidates)
              : suMu(v) ? genisSu(i)
              : kara(i)
    if wanted(i0): return i0                      // NOTE: even if i0 is already used by another region
    BFS from i0, up to 40 rings, visiting komsu in order:
        for j not yet seen: if wanted(j) and j not in kullanilan:
            tasinan[v.id] = [round(pts[j].x), round(pts[j].y)]; return j
    return i0                                     // nothing acceptable found: keep original cell
else:
    r = mulberry(hash(seed + ':' + v.id))
    center = window center
    best = -1, bestScore = -inf
    repeat 80 times:
        i = candidates[floor(r()*len)]            // r() consumed
        if i undefined or i in kullanilan: continue   // no second r()
        dmin = min distance from pts[i] to every used seed cell
        score = kullanilan nonempty ? -|dmin - 300| + r()*40
                                    : -dist(pts[i], center) + r()*80
        if score > bestScore: best = i, bestScore = score
    if best < 0: best = candidates[0] ?? 0
    yeniXY[v.id] = [round(pts[best].x), round(pts[best].y)]
    return best
```
Top-level regions are seeded in entity (id) order:
```
seed = tohumSec(v, suMu(v) ? suHucre : karaHucre)
add seed to kullanilan
```

**8. Flood fill, `taskin(seeds, allowed, owner[], unbounded=false)`.** This is a multi-source Dijkstra with an exact binary min-heap.

Heap details (`Yigin`), needed for identical tie-breaking:
- Entries are `[cost, cell, id]` and are compared on cost only.
- push: append, then sift up while `parent.cost > child.cost`. It stops when `parent.cost <= child.cost`.
- pop: take the root and move the last element to the root. Sift down: pick the left child if its cost is strictly less than the current minimum, then the right child if strictly less than that. Stop when neither is smaller.

```
cost = Float32Array(N).fill(+inf)                 // float32 storage, see smells
center[id] = pts[seedCell]
for (id, i) in seeds: cost[i] = 0; owner[i] = id; push [0, i, id]
while heap: [c, i, id] = pop()
    if c > cost[i]: continue                      // c is float64, cost[i] float32
    for j in komsu[i]:
        if not allowed(j, id): continue
        nc = c + 1 + |yuk[j] - yuk[i]|*40 + (kara(i) != kara(j) ? 30 : 0)
        if not unbounded and dist(pts[j], center[id]) > 320: continue
        if nc < cost[j]: cost[j] = nc; owner[j] = id; push [nc, j, id]
```
- Top level: `taskin(topSeeds, allowed = isWaterRegion(id) ? !kara(j) : kara(j), bolgeOf)`. A cell is owned by at most one top-level region. Water regions grow over any water (lakes included). Land regions grow over land only.
- Sub-regions are grouped by parent id (Map in `altlar` order). For each parent:
  - `cells = [i | bolgeOf[i] == parent]` (index order). If there are none, skip; the sub-regions get no cells.
  - Seeds: `tohumSec(v, cells, true)`, each added to `kullanilan`.
  - Then `taskin(subSeeds, allowed = bolgeOf[j] == parent, altOf, unbounded=true)`.

**9. Cells per region.**
- `bolgeHucreleri[id]` collects every cell `i` where `bolgeOf[i] == id` or `altOf[i] == id`, in index order. A parent's cell list therefore includes all its sub-regions' cells.

**10. Display position of regions (`konum`).**
- Compute the centroid of the region's cell points.
- `konum[id]` = the point of the cell nearest to that centroid (first strict minimum of squared distance), unrounded.
- The persisted `harita_xy` stays the **seed** point, not this centroid cell.

**11. Point entities.**
- Point types (`noktaTurleri`): `yer` (place), `kaynak` (resource), `yerlesim` (settlement), `halk` (people), `tarikat` (cult), `hizip` (faction), `olumlu` (mortal), `esya` (item), `olay` (event), `tur` (species).
- They are processed in entity order with `yerlestir(v, guard=0)` (place):
```
if konum[v.id] set or guard > 8: return
p = byId(v.konum_id)                               // parent; may be any type in the list
if v.xy:
    i0 = hucre(v.xy)
    inside = !p || p.tur != 'bolge' || any cell i of region p with (i == i0 or i0 in komsu[i])   // region or its 1-ring
    if inside: konum[v.id] = v.xy (exact); dolu.add(i0); return
    v = copy with xy = null; mark v.id as relocated
if !p: return                                      // parentless point without xy: not placed
if p.tur != 'bolge' and !konum[p.id]: yerlestir(p, guard+1)  // place parent first (even non-point types)
r = mulberry(hash(seed + ':n' + v.id))
if p.tur == 'bolge': cand = cells of p filtered by (kara(i) || suMu(p))
elif konum[p.id]:    cand = land cells within 2 BFS rings of del.find(konum[p.id]) (center included)
if cand empty: return
best = -1, bestScore = -inf
repeat 24: i = cand[floor(r()*len)]; if i in dolu: continue
    coast = any komsu of i is water
    score = v.tur == 'yerlesim' ? (coast?1:0) - yNorm(i)*1.5 + r()*0.5     // settlements: coastal, lowland
          : v.tur == 'kaynak'   ? yNorm(i) + r()*0.5                       // resources: highland
          : r()
    if score > bestScore: best, bestScore = i, score
if best < 0: best = cand[0]
dolu.add(best); konum[v.id] = pts[best]
(relocated ? tasinan : yeniXY)[v.id] = [round(x), round(y)]
```

**12. Known area / fog (`bilinen`, Uint8 per cell).**
- 1 = known: cells owned by a top-level region, plus the cell of every `konum` point.
- If nothing is known, the window-center cell is known.
- Then 4 BFS rings mark unknown neighbours as 2 (fog / frontier).
- `kapsam` (extent) = bbox of all cells with known ≥ 1: `{x, y, w: max(200, w), h: max(140, h), oran: knownCount/N, hucre: knownCount}`. The UI uses it for framing and the "known N cells" label.

**13. Region info (`bilgi`).** One record per id in `bolgeHucreleri`; Map order is by first cell index.
```
neighbours = set; coast = false; sumElev = 0; biomeCount = {}
for i in cells(id):
    sumElev += yNorm(i)
    biomeCount[biyom(yNorm(i), nem[i], kara(i), tur)] += 1
    for j in komsu[i]:
        o = (altOf[j] && altOf[j] != id && altOf[i] == id) ? altOf[j]                 // sub-region: other sub-regions only
          : (bolgeOf[j] != bolgeOf[i] && bolgeOf[i] == id) ? bolgeOf[j] : 0           // top region: other top regions
        if o: neighbours.add(o)
        if kara(i) != kara(j): coast = true
avg = sumElev / count
climate = top 3 biomes by count (stable sort desc), keep those with share >= 0.12, format "<biome> %<round(share*100)>"
bilgi[id] = {
  komsular: [...neighbours],   // neighbour region ids, insertion order
  kiyi: coast,                 // bool; true for any land/water boundary incl. lakes
  yukseklik: avg > 0.45 ? 'dağlık' (mountainous) : avg > 0.22 ? 'engebeli' (hilly) : avg > 0 ? 'ova' (plain) : 'su' (water),
  buyukluk: count,             // size in cells
  iklim: climate               // list of strings; English format should be "<biome> <n>%"
}
```
Example output for seed "Aerona" with a land region 1 "Kuzey", a sea region 2 "Mavi Deniz" and a settlement 3 under region 1:
- `yeniXY = {1:[1367,719], 2:[1238,979], 3:[1586,609]}`
- `bilgi[1] = {komsular:[2], kiyi:true, yukseklik:'engebeli', buyukluk:256, iklim:['bozkır %32','kıraç tepeler %32','ormanlı tepeler %16']}`
- `bilgi[2] = {komsular:[1], kiyi:true, yukseklik:'su', buyukluk:632, iklim:['derin deniz %68','sığ deniz %32']}`

**14. Return value.**
`{W: w, H: h, pencere, pts, vor, del, komsu, yuk, nem, deniz, kara, yNorm, bolgeOf, altOf, konum, yeniXY, tasinan, bilgi, bilinen, kapsam}`.
- The server keeps only `bilgi`, `konum` and `kapsam`, plus the world record.
- The browser and `kitap.js` (the SVG map in the exported book) use everything.

### Biome classifier

`biyomIndeks(e, m, land)` takes e = yNorm and m = moisture:

| Condition | Index | Ordinary-world biome |
|---|---|---|
| water, e > -0.35 | 0 | shallow sea (sığ deniz) |
| water, e ≤ -0.35 | 1 | deep sea (derin deniz) |
| land, e < 0.05 | 2 | beach (kumsal) |
| land, e < 0.32, m > 0.56 | 5 | forest (orman) |
| land, e < 0.32, m > 0.44 | 4 | meadow (çayır) |
| land, e < 0.32, else | 3 | steppe (bozkır) |
| land, e < 0.58, m > 0.5 | 7 | wooded hills (ormanlı tepeler) |
| land, e < 0.58, else | 6 | barren hills (kıraç tepeler) |
| land, e < 0.8 | 8 | rocky mountains (kayalık dağlar) |
| land, e ≥ 0.8 | 9 | snowy peaks (karlı doruklar) |

`biyom(e, m, land, tur)` returns `DUNYA_TURLERI[tur].biyom[index]` when `tur` is known. Otherwise it returns the ordinary names above.

### World types (`DUNYA_TURLERI`): full table

Each world type has:
- `ad` (display name)
- `arazi` (terrain defaults: `deniz` sea fraction, `daglik` mountainousness, `nem` moisture offset)
- `biyom` (10 biome names, indexed 0–9 as above)
- `palet` (10 colours, same indices)

When a world is created or its type is changed, its `dunyalar.arazi` is set to the type's `arazi` (`oyuncu.js:295`, `db.js:681`).

| key | English name (Turkish) | sea | mount. | moist. | biomes 0–9 (English) | palette 0–9 |
|---|---|---|---|---|---|---|
| `olagan` | Ordinary world (Olağan dünya) | 0.52 | 1 | 0 | shallow sea, deep sea, beach, steppe, meadow, forest, barren hills, wooded hills, rocky mountains, snowy peaks | #3b6a86 #1e3a52 #d8c79a #b9ad74 #8fae6a #4f7d4a #9a8a66 #5d7a52 #8b8478 #eef1f2 |
| `okyanus` | Ocean world (Okyanus dünyası) | 0.84 | 0.8 | 0.15 | coral shallows, abyssal sea, white beach, salt cliffs, moss island, mangrove, rocky island, misty island, volcanic summit, icy peak | #3a9bb0 #0f2c4a #ece2c2 #a9a28a #6fa585 #3f7a5e #8a8576 #6b8a7a #5b4a44 #e8eef2 |
| `kum` | Sand world (Kum dünyası) | 0.06 | 0.9 | -0.35 | salt lake, dried-up sea, sand sea, dune, glass desert, oasis, red crags, canyon, wind pillars, sand peak | #d8d2c0 #b8a888 #e8c88a #dfb26c #c9b49a #7c9a5a #b5643c #9a5434 #8a6a52 #f0dcb4 |
| `buz` | Ice world (Buz dünyası) | 0.45 | 1.1 | 0.05 | ice floes, black water, snow shore, ice field, tundra, needle forest, glacier, blue ice, ice mountain, storm peak | #9cc2d6 #1b2f45 #e6eef2 #d4e2ea #a9b8a4 #4c6a62 #bcd3e0 #8fb3cc #c8d6e0 #ffffff |
| `lav` | Lava world (Lav dünyası) | 0.38 | 1.4 | -0.25 | lava lake, magma ocean, obsidian shore, ash plain, basalt plain, sulphur marsh, coal hills, smoke valley, volcano, ember peak | #e8622c #7a1a0c #2a2226 #5a5050 #3c3434 #9a9a3c #463a36 #5c4c46 #2c2020 #ff9a3c |
| `kristal` | Crystal world (Kristal dünya) | 0.4 | 1.3 | 0 | light lake, prism depths, glass shore, quartz plain, echo meadow, crystal forest, chiming hills, rainbow valley, echoing mountains, pure peak | #8fd6e6 #2c3f7a #e8e4f4 #c8c4dc #a8d4c8 #7aa8c4 #b4a4d8 #d4a8c8 #9c8cc4 #ffffff |
| `yasayan` | Living planet (Yaşayan gezegen) | 0.42 | 0.9 | 0.25 | fluid lake, blood sea, membrane shore, skin plain, hair meadow, flesh forest, bone hills, vein valley, tooth ridges, eye peak | #b04a5a #4a1020 #d8a8a0 #c48a7c #a87a6a #8a3c44 #e0d4c0 #9a4a5a #f0e8dc #e8c8b8 |
| `olu` | Realm of the dead (Ölüler âlemi) | 0.5 | 0.9 | 0.1 | water of oblivion, black river, ash shore, bone plain, pale meadow, mist valley, grave hills, echo forest, silent mountains, dead peak | #4a5a6a #141a22 #8a8a86 #c8c0b0 #7a8478 #5a6670 #6a6460 #4a5450 #3c3a3a #d8d4cc |
| `ruya` | Dream realm (Rüya âlemi) | 0.6 | 1.2 | 0.2 | dream water, sleep depths, cotton shore, floating island, violet meadow, whisper forest, slanted hills, inverted valley, cloud mountain, star peak | #8a9ae6 #2a2a6a #f0d8e8 #d4c4f0 #c4a8e0 #8a7ac8 #e0b4d4 #b4a0dc #e8e4ff #fff4c8 |
| `ayna` | Mirror world (Ayna dünya) | 0.48 | 1 | 0 | inverted water, silver depths, glass shore, reflecting plain, inverted meadow, mirror forest, echo hills, broken valley, silver mountains, inverted peak | #c4d0dc #5a6a80 #e8eef4 #b8c4d4 #a8b8c8 #8496ac #d4dce6 #9aaabc #74849a #ffffff |
| `gaz` | Gas giant (Gaz devi) | 0.9 | 0.6 | 0.3 | low cloud, pressure abyss, cloud shore, wind island, storm band, floating forest, cloud hill, lightning valley, vortex, eye-storm | #d8b48a #7a4a2a #f0e0c4 #e4c8a0 #c8a87a #9a7a5a #f4e4cc #b48a6a #e89a5a #ffffff |

`DUNYA_TUR_KEYS` = the keys above, in the order listed. They serve as the world-type enum in the son tool `dunya_dogur` (`tools.js:1388`), in world birth (`kozmos.js`), in the cosmos UI, and in image-prompt styling (`gorselyon.js`).

### Water-region detection (`suMu(v)`): LANGUAGE-SPECIFIC, drop or replace

A region is water when `v.tur == 'bolge'`, `"${alt_tur} ${ad}"` matches the water regex, and it does not match the dry regex.
- Water regex `/deniz|okyanus|körfez|koy|göl|boğaz|lagün|su\b|sular|derinlik|okyanus/i` covers sea, ocean, gulf, bay, lake, strait, lagoon, water, waters, depth.
- Dry regex `/(kum|cam|bulut|tuz|kül|toz|ot|kemik|sis|ışık|yıldız|ateş|lav|buz)\s+(deniz|göl|okyanus)|kuru(muş)?|çöl|kumul/i` catches "sand/glass/cloud/salt/ash/dust/grass/bone/mist/light/star/fire/lava/ice sea|lake|ocean", "dry/dried", "desert" and "dune".

Replacement: add an explicit `terrain: 'land' | 'water'` (or `is_water`) field to regions. Set it from the creation tool schema and the LLM output. Keep an English keyword regex only as a fallback for migration.

### Server wrapper (`src/harita.js`)

- `haritaVarliklari(dunyaId=null)` (map entities):
  - `SELECT id, ad, tur, alt_tur, konum_id, guc_seviyesi, statlar, harita_xy, yaratan_id, kaynak, durum, dunya_id FROM varliklar WHERE durum IN ('kanon','olu','gerceklesti') [AND dunya_id=?] ORDER BY id`
  - These are canon, dead and realized entities.
  - It parses `statlar` and sets `xy = JSON(harita_xy) or null`.
- `dunyaKaydi(id)` returns the `dunyalar` row with `arazi` parsed. `dunyaIdleri()` returns all world ids in ascending order.
- `gocEt()` migrates v1 to v2 once:
  - Precondition: `dunya.harita_surum < 2`.
  - Every `harita_xy` with x ≤ 1.0001 and y ≤ 1.0001 becomes `[round(1000 + x*1000), round(680 + y*680)]`.
  - Then it sets `harita_surum = 2`. The new design can drop this.
- `haritaHesapla(dunyaId=null)` (compute map):
  1. If the singleton `dunya` row is missing, return null. Run `gocEt()`.
  2. If `dunyaId == null`:
     - With at most 1 world, recurse with `ids[0] ?? 1`.
     - Otherwise compute every world and merge: `{bilgi: Object.assign(all), konum: Object.assign(all), kapsam: first world's}`.
     - The merge is safe because region ids are globally unique. The engine mostly calls this argument-less form.
  3. `dk = dunyaKaydi(dunyaId)`; `seed = dk.seed || dunya.ad` (world name); `arazi = dk.arazi || {}`; `tur = dk.tur || null`.
  4. Signature (`imzaKur`):
     - `seed + '|' + JSON(arazi) + '|' + join(',', "id:tur:konum_id:harita_xy" for canon/dead/realized rows [of that world] ORDER BY id)`.
     - If `dk` is null, there is no world filter.
     - On a signature match with the per-world cache (`onbellekler` Map), return the cached result.
  5. Otherwise:
     - Load the entities and run `dunyaHaritasi`.
     - **Persist** `yeniXY` with `UPDATE varliklar SET harita_xy=? WHERE id=? AND harita_xy IS NULL`.
     - Persist `tasinan` with an unconditional `UPDATE ... SET harita_xy=?`.
  6. Result: `{bilgi, konum, kapsam, dunya: dk}`. The cache signature is **recomputed after persisting**, so the next call hits.
- `haritaGecersiz()` clears all caches. Callers:
  - world birth (`kozmos.js:171`)
  - moving an entity between worlds / editing a world (`oyuncu.js:99,343`)
  - full reset (`server.js:329`)
  - manual marker drag `POST /api/harita/konum` (`server.js:586`), which writes `harita_xy = [round(x), round(y)]` with no validation beyond finiteness
- Other code paths reset `harita_xy = NULL` to force re-placement when an entity moves (`derin.js:2550`, `otesi.js:360,363`, `oyuncu.js:94,98`).
- `ufuk.js` writes the seed for **new frontier regions** (`bolgeKonumu`):
  - It tries `KESIF.harita_deneme` angles starting from a random angle, at distance `KESIF.harita_uzaklik` from the source region's `konum`.
  - Each candidate is clamped to [0, 3000] × [0, 2040].
  - It picks the candidate whose minimum distance to the other regions' `konum` is largest.
  - It writes with `WHERE harita_xy IS NULL`.

### How server and browser share it

1. `GET /api/harita?dunya=<id>[&cag=<n>]` calls `haritaHesapla(dunyaId)` **first**, which persists any new coordinates. It then reads `haritaVarliklari(dunyaId)`, so the browser receives entities whose `xy` are already fixed.
2. The response includes:
   - `seed`, `dunya` (world row with parsed `arazi`), `varliklar` (with `xy`, plus `kapak` cover image)
   - `bilgi`, `kapsam`, `rotalar` (active v–v bonds of type ticaret/dusman/yonetir/avlar)
   - `bolgeDin` and `bolgeDil` (per region: dominant god and language, weighted by `log10(max(10, nufus|murit|100))` of canon communities)
   - `diller`, `siyasi`, `yollar`, `notlar`, `zaman`, `kademeler`, `isaretler`, `savaslar`
   - For historical epochs, entities are filtered by an epoch snapshot.
3. The browser (`public/views/harita.js`) runs **the same `dunyaHaritasi`** locally with `d3.Delaunay`. It caches on `seed + tur + JSON(arazi) + JSON([[id, tur, konum_id, harita_xy]...])`. It renders the Voronoi cells (biome colour or world-type palette), hillshade, coast and borders. Dragging a marker POSTs the new position.
4. Determinism depends on identical floating-point math, identical Delaunay neighbour order and identical persisted `xy` on both sides.

### LLM context text (`cografyaSatirlari(dunyaId)`), translated

```
The world is infinite; its known part is only {N} regions. Beyond is unexplored: new regions are born at the edge of the known world and extend the map in that direction.
- #{id} {name}: {elevationLabel}[, has a coast   ← only if kiyi and label != water], size {cells}[, terrain: {iklim joined ", "}]; neighbours: #{k} {name}, …
  (or "; no neighbours (isolated)")
```
The Turkish elevation labels are dağlık (mountainous), engebeli (hilly), ova (plain) and su (water). Names are looked up one query per id. The text is used by:
- `agents.js:1711` (the "peoples awaken" prompt, section `HARİTA:` = MAP:)
- `world.js:568` (world context)

### Consumers of `bilgi` (cross-reference)

- `derin.js:665` `komsuMu`: two communities are neighbours if their top regions are equal or listed in `komsular`. If either has no region, the fallback is `mesafe <= ILISKI_K.komsu_mesafe`.
- `derin.js:2015-2017`: climate effect, using `kiyi` and the mountainous/hilly labels.
- `derin.js:2525`.
- `sim.js:730,775-790`: natural disasters.
  - Regions with label ≠ 'su' are eligible.
  - Mountainous or hilly regions can get earthquakes.
  - Coastal regions can get floods and storms.
  - Drought needs low fertility or the drought law.
  - Plague needs a crowded region.
- `olumluler.js:330,392,403`: mortal-agent context, translated as "YOUR LAND: #id name (label[, coastal]; neighbouring regions: …)".
- `kesif.js:54`, `ufuk.js:177` (exploration).
- `kitap.js:205` (SVG map for the book export).

---

## 5. Procedural language and naming (dilmotoru.js, dil.js)

### Concepts and storage

- A **language** (dil) is an ordinary entity: `varliklar` row with `tur = 'dil'` (language).
  - `alt_tur` is free text, for example "ilkel dil" (primitive language), "yerli dil" (native language), or "X lehçesi: …" (dialect of X).
  - Stats: `yayginlik` (spread 0–100), `karmasiklik` (complexity), `kutsallik` (sacredness).
  - Tags (`etiketler`) include `imza:…` (phonological signature), `yazi:<script>` (writing system) and `ilkel` (primitive).
- **Speaks** relation: bond `konusur` (speaks) from a v-entity to the language (v→v). The current language of a speaker is the **latest active** `konusur` bond.
  - `konusulanDil(v)` (`world.js`) also requires the language to be `kanon` or `olu`.
  - `dildenAd` does **not** check that.
- **Ancestry**: bond `soyundan` (descends from), language → parent language. A dialect is a child language with the bond description `'lehçe'` (dialect).
- **Lexicon** (sozluk) table:
  - Columns: `id`, `dil_id`, `kelime` (word, ≤60), `anlam` (meaning, ≤300, required), `tur` (part of speech: isim noun / fiil verb / sıfat adjective / ek suffix / unvan title / yer adı place name / özel ad proper noun), `koken` (etymology ≤300), `ornek` (example ≤300), `ekleyen_tip` + `ekleyen_id` (who added it), `cag` (epoch), `olusturma` (created at).
  - `ekleyen_tip` values: 'v' entity, 'o' son, 't' god, 'm' engine. For 'm', `ekleyen_id` = the commemorated entity.
  - `sozlukEkle(dilId, words, addedByType, addedById, epoch)` (`world.js`) inserts words. It skips words that are empty, missing a meaning, or already present (case-insensitive) in that language. It returns the list of inserted words.
- **World script and phonology are per world.** A world's "alphabet" filters out letters that leak in from Turkish names.

### Where languages come from (cross-reference)

1. **World birth** (`kozmos.js:275-285`). The LLM's world-birth response may include `dil` (name, alt_tur, description, words) and `lehce` (a dialect/phonology description text, stored in `dunyalar.lehce`).
   - The native language is inserted and its words added.
   - Region, sky and resource names that do not fit the dialect are **renamed** with `adUret(dilId, 'dogus:{worldId}:{entityId}', bolge ? 'yer' : 'genel')` and tagged `dilden-ad` (name-from-language).
2. **Agent tool `dil_kur`** (found a language, `olumluler.js:465`). It is available to mortal agents and creates a language from LLM-supplied name, type, description and words.
   - If the actor is a single mortal (`olumlu`), it can only found a **dialect** of its spoken language, or of the language of a halk/yerleşim in its region. Then `alt_tur = "{parent} dialect[: …]"` and the bond `soyundan` 'lehçe' is added.
   - The actor's old `konusur` bonds are deactivated and a new one is added.
3. **Engine primitive language** (`derin.js:2429 ilkelDil`). It is created when a community has no language anywhere nearby.
   - Name: `"{firstWordOfCommunityName} Dili"` (= "{X} Language"). `alt_tur` 'ilkel dil' (primitive language), tag `ilkel`.
   - It gets 8 root words with meanings su/ateş/toprak/ana/gök/yol/ölü/ekmek (water, fire, earth, mother, sky, road, dead, bread).
   - Each word is `adUret(id, 'ilk:{i}', 'genel')`. The fallback is `syllable[i % n] + ['a','u','en','ir','o','el','um','is'][i]`.
4. **Nearest language assignment** (`derin.js:2414 enYakinDil`): the parent community's language, then the ancestors' languages, then a weighted majority in the region or world.

### Syllabifier (`hecele(word)`)

Vowels `UNLU = 'aeıioöuüâîû'`.
```
k = lowercase(word, 'tr') with all chars not in [a-zçğıöşüâîû] removed
out = []; i = 0
while i < len(k):
    h = consume consonants (onset) + consume vowels (nucleus)     // vowel runs stay in one syllable
    j = index of next vowel after i (or end)
    cluster = k[i:j]
    if j >= len(k): h += cluster; i = j           // word-final consonants -> coda
    elif len(cluster) >= 2: h += cluster[0]; i += 1   // first of a cluster -> coda, rest -> next onset
    // single intervocalic consonant -> next onset
    if h: out.append(h)
return out
```
This is a generic onset-nucleus-coda splitter and is **not Turkish-specific**. Keep it, but define the vowel set for the new app's conlang alphabet (e.g. `aeiou` plus any diacritic vowels you allow). Optionally treat `y` as a vowel.

### World alphabet (`dunyaAlfabesi(worldId)`)

```
cache key `${worldId}:${currentEpoch}` (FIFO, max 50 entries)
count every letter (\p{L}) of lowercase(kelime) over all sozluk words of languages whose dunya_id IS worldId
if total >= DIL.alfabe_en_az (60): alphabet = { c | count[c]/total >= DIL.alfabe_binde/1000 (0.005) }
else alphabet = null   // no filtering
```
Also used by `tools.js:866` to warn: "Note: the sounds {letters} in its name do not exist in this world's languages; the name sounds foreign."

### Dialect-text sample names (`lehceOrnekleri(text)`): partly LANGUAGE-SPECIFIC

It extracts sample names from the world's `lehce` description:
1. Quoted words (straight or curly quotes, `«»`), 3–14 letters (hyphen allowed after the first).
2. Capitalized words of 3–14 letters that are not sentence-initial. The word must be preceded by a character that is not `.!?:` or newline, followed by whitespace. Words in the stop list are excluded.
3. Words after "örn", "örnek", "örneğin" or "ör." (= "e.g.", "example", "for example"), up to the newline or period, split on `, ; /` and whitespace. Each must be 3–14 letters or hyphens and not in the stop list.

Results are capped at `DIL.lehce_ornek` (30).

Stop list (Turkish → English): örnek example, örneğin for example, örn e.g., ünlüler vowels, ünsüzler consonants, sert hard, yumuşak soft, hece syllable, heceler syllables, ekler suffixes, sesler sounds, adlar names, isimler names, kurallar rules, kural rule, sonek suffix, önek prefix, bu this, ve and, ile with.

English replacement: the same three extractors, with markers "e.g.", "for example", "such as", "like" and an English stop list. A better option is to ask the LLM for an explicit `sample_names: string[]` field in the world-birth schema instead of parsing prose.

### Phonology (`fonoloji(langId)`)

Cache key `${langId}:${epoch}:${all DIL values joined}` (FIFO, max 200).
```
langs = [langId] + up to DIL.soy_derinlik (3) ancestors via the first active 'soyundan' bond (kaynak_tip='v', LIMIT 1, no ORDER BY; stops on a cycle)
corpus = all sozluk.kelime of langs
firstWord(s) = first whitespace-separated token
lang = entity; world = dunyalar row of lang.dunya_id ?? 1 (name, lehce)
worldRoot = lowercase(firstWord(world.ad))
isTurkishName(x) = x ends with /(ça|çe|ca|ce|dili|ce)$/i  OR  lowercase(x) starts with worldRoot[0:DIL.kok_harf]
        // LANGUAGE-SPECIFIC: catches language names like "Dazbuşça" (= world name + Turkish "-ish" suffix) and names derived from the world's Turkish name
if lang and !isTurkishName(firstWord(lang.ad)): corpus += firstWord(lang.ad)
if |corpus| < DIL.kelime_en_az (8) and world.lehce and world id != 1: corpus += lehceOrnekleri(world.lehce)
if |corpus| < 8: corpus += firstWord(name) of every entity with an active 'konusur' bond to langId whose kaynak != 'dunya'
if |corpus| < 8: corpus += firstWord(ad) of up to 60 entities (tur in halk, bolge, yer, dil; kaynak != 'dunya'; same world; ORDER BY id), excluding isTurkishName
alphabet = dunyaAlfabesi(world)
for each token (corpus split on whitespace) that is pure letters and (alphabet null or every lowercase char in alphabet):
    syl = hecele(token); skip if empty or len > DIL.hece_en_cok (6)
    lengths.push(len(syl))
    bas[syl[0]] += 1                         // word-initial syllable distribution
    if len > 1: son[syl[-1]] += 1            // word-final
    for s in syl[1:-1]: orta[s] += 1         // medial
f = { bas, orta, son, ort: mean(lengths) or DIL.ort_hece/10 (2.4), kelime: |corpus| }
```
`kaynak = 'dunya'` marks engine-made entities. They are excluded so that engine names do not feed back into the corpus.

English replacement for `isTurkishName`: drop the "-ça/-ce/dili" rule. Exclude language names ending in "-ish/-ese/-ian/-ic", or containing "language/tongue/speech", and any token that equals the world's name root.

### Seeded RNG for names (`rng(seed)`)

This is the same mulberry32 as the map, seeded by FNV-1a. One difference: the hash uses `c.charCodeAt(0)` per code point, i.e. **the high surrogate only** for characters above U+FFFF. Seeds are normally ASCII or Turkish, so the output is identical to the map RNG (verified: `rng("Aerona")` gives `0.9770483230240643, 0.40212616417557, 0.5175353118684143`). A Python port can reuse `fnv1a32` + `mulberry32`. For astral code points, substitute `0xD800 + ((cp - 0x10000) >> 10)`.

`agirlikliSec(dist, r)` (weighted pick):
```
entries in insertion order
x = r() * total
for (k, n) in entries: x -= n; if x <= 0: return k
return first key
```
An empty distribution returns `''`.

### Language signature (`dilImzasi(langId)`)

Each language picks a persistent "accent":
- `u`: liked consonants (a string of chars)
- `k`: a liked consonant cluster of two chars, or ''
- `s`: its own name ending (suffix, ≤ 4 letters)
- `l`: a syllable-length bias in {-1, 0, 1}

It is stored as the tag `imza:u=lmnrv;k=rn;s=ar;l=1` and cached in memory forever (`IMZALAR`).
```
if cached: return
if lang has tag starting 'imza:': parse and cache    // BUG: see smells (parser drops `u`)
r = rng(`imza:${langId}`)
parent = first active 'soyundan' v->v bond target
f = fonoloji(langId)
syllables = keys(f.bas) ++ keys(f.orta) ++ keys(f.son)       // distinct syllable TYPES
consonants = distinct chars of syllables.join('') matching /[bcçdfgğhjklmnprsştvyzqxw]/, in first-appearance order
vowels = distinct chars in UNLU, in first-appearance order
if |consonants| < DIL.imza_en_az_unsuz (3) or no vowels: return null (not cached)
if parent and parent != langId and (P = dilImzasi(parent)):          // inherit with drift
    u = chars of P.u; newOnes = consonants not in u
    if newOnes and |u| > DIL.imza_miras_unsuz (3):
        u[floor(r()*|u|)] = newOnes[floor(r()*|newOnes|)]          // shift one consonant
    s = P.s ? P.s.replace(first [aeıioöuü], vowels[floor(r()*|vowels|)]) : ''   // r() consumed whenever P.s is non-empty
    sig = { u: dedupe(u).join, k: P.k, s, l: P.l }
else:                                                                  // fresh
    freq[c] = number of occurrences of consonant c across the concatenated syllable-type list (each distinct syllable counted once per distribution it appears in; not weighted by corpus frequency)
    ranked = consonants stable-sorted by freq desc
    u = [c for idx, c in ranked if idx < DIL.imza_kalici_unsuz (2) or r() < DIL.imza_unsuz/100 (0.62)]   // r() only for idx >= 2
    while |u| < min(DIL.imza_unsuz_en_az (5), |ranked|): append next ranked consonant not in u
    k1 = u[floor(r()*|u|)]; k2 = (u without k1)[floor(r()*(|u|-1))] or ''
    endings = keys(f.son) whose consonants are all in u
    s = endings ? random ending (r()) with leading consonants stripped : vowels[0] + u[0]
    sig = { u: u.join, k: (k1 and k2) ? k1+k2 : '', s: s[0:DIL.imza_ek_harf (4)], l: floor(r()*3) - 1 }
persist: UPDATE varliklar SET etiketler = (tags without 'imza:*') + ['imza:u=..;k=..;s=..;l=..']
cache and return
```
`imzaliDag(dist, sig)` (signature filter):
- If `sig.u` is set, keep only the syllables whose consonants are all in `sig.u`.
- If fewer than 2 syllables remain, use the unfiltered distribution.

### Ugly-name filter (`adCirkinMi(name)`)

The name is ugly (true) if any of these hold, on the lowercased name:
- Any doubled non-vowel character (e.g. "Ovvir").
- Two adjacent identical syllables.
- Some syllable onset (leading consonant run) occurs in at least `DIL.cirkin_ayni_bas` (3) syllables (e.g. "Hehahe").
- The name has exactly 2 syllables, both of length ≤ 2, starting with the same character.

### Name generation (`adUret(langId, seed, kind='genel')`)

`kind` is one of `'kisi'` (person), `'yer'` (place), `'halk'` (people), `'ordu'` (army) or `'genel'` (general).
```
f = fonoloji(langId); if f.bas is empty: return null
sig = try dilImzasi(langId) catch null
takenNames = all varliklar.ad (durum != 'reddedildi') UNION ALL ogullar.ad      // for the similarity check
fallback = null
for attempt in 0 .. DIL.ad_deneme-1 (24):
    r = rng(`${langId}:${kind}:${seed}:${attempt}`)
    bias = kind=='kisi' ? DIL.hece_kisi/10 (-0.3) : kind in (yer, halk) ? DIL.hece_yer/10 (+0.4) : 0
    target = clamp(round(f.ort + bias + (sig.l or 0)*0.5 + (r() - 0.5)), DIL.ad_hece_en_az (2), DIL.ad_hece_en_cok (4))
    B = imzaliDag(f.bas, sig); M = imzaliDag(f.orta or f.bas, sig); E = imzaliDag(f.son or f.bas, sig)
    parts = [pick(B)]
    add(D): h = pick(D); up to DIL.hece_tekrar_deneme (4) times, while h == parts[-1] or h[0:2] == parts[-1][0:2]: h = pick(D); parts.push(h)
    for i in 1 .. target-2: add(M)
    if target > 1: add(E)
    if sig.s and target > 1 and r() < DIL.imza_son/100 (0.5):          // r() only if the first two hold
        parts[-1] = leadingConsonants(parts[-1]) + sig.s
    name = parts.join('')
    if sig.k and r() < DIL.imza_kume/100 (0.3):
        name = replace FIRST /([aeıioöuü])([^aeıioöuü])([aeıioöuü])/ with $1 + sig.k + $3   // V C V -> V kk V
    name = collapse runs of the same vowel to one; collapse runs of the same non-vowel non-space char to one
    if len(name) < DIL.ad_harf_en_az (3) or > DIL.ad_harf_en_cok (12): continue
    name = uppercaseFirst(name, 'tr')
    if isimAlinmis(name) or adCirkinMi(name): continue
    if benzerAd(name, {aile: true, adlar: takenNames}): fallback ??= name; continue
    return name
return fallback          // may be null; callers fall back to placeholder names
```
Helpers in `world.js` (cross-reference):
- `aramaNorm(x)` (search normalization): lowercase (tr), `ı→i`, dotted `i̇→i`, `â/à→a`, `î/ì→i`, `û/ù→u`. LANGUAGE-SPECIFIC; in English use casefold plus strip diacritics.
- `isimAlinmis(name)` (name taken) is true if `aramaNorm(name)` equals that of any name in varliklar (not rejected), ogullar, yildizlar (stars), dunyalar (worlds) or yabanci_tanrilar (foreign gods). Names are cosmos-unique.
- `harfUzakligi(a,b)` (letter distance): if the normalized lengths differ by more than 1, return 2. Otherwise return the full Levenshtein distance.
- `benzerAd(name, {aile, adlar})` (similar name):
  - Multi-word names never conflict (return null).
  - If `len ≤ DIL.benzer_uzunluk` (7): any single-word existing name `t` with `len(t) ≤ 8`, not equal, and Levenshtein ≤ 1 is a conflict (return `t`).
  - If `aile` and `len ≥ DIL.kok_harf` (4): count single-word names sharing the first 4 normalized letters. If the count ≥ `DIL.aile_tavani` (3), return the first of them.
- `benzersizAd(name)` (unique name) appends Roman numerals " II", " III", … until the name is unique.

`dildenAd(speaker, seed, kind)` (name from the speaker's language) picks the latest active `konusur` v→v bond of the speaker (`ORDER BY id DESC`) and calls `adUret`. Without a bond it returns null.

Callers (seed templates are part of determinism):
- `sim.js:742` hero `'{h}:{epoch}:kahraman'` kisi
- `sim.js:834` migration `'{y}:{epoch}:goc'` yer
- `sim.js:964` child `'{A}:{B}:{epoch}:cocuk'` kisi
- `derin.js:896` army `'{t}:{war}:ordu'` ordu, then the name gets " Ordusu" (Army)
- `derin.js:1118` battle `…:muharebe` yer
- `derin.js:1789` apprentice
- `derin.js:2136` `kisiAdi`: tries each speaker with 4 seeds, then the 3 most-spoken languages of the world with kinds kisi then genel
- `derin.js:2240` village, `derin.js:2257` people, `derin.js:2604` structure, `derin.js:2645` faction
- `ufuk.js:196,221` discoveries, `seyahat.js:350` colony
- `agents.js:1250` god-name `'tanri:{son}:{halk}'`, `epoch.js:477` local god `'yerel-tanri:{world}'`
- `kozmos.js:283` world birth renames
- `server.js:841`: 3 sample names `'ornek{i}'` kisi for the languages UI

### Cognates (`kognatlar(langA, langB)`)

All pairs of lexicon words (A × B, O(n·m)) where the lowercase forms are equal, or both have length ≥ `DIL.kok_harf` (4) and share the first 4 letters. The result is `[{a, b, anlam_a, anlam_b}]`, capped at `DIL.kognat_en_cok` (30). It is used by `GET` languages tree (`server.js:840-843`) to compute `akrabalik` (kinship) edges between a language and its parent.

### Writing systems (`YAZI_TURLERI`, `yaziOf`)

A language gains the tag `yazi:<key>` when its speakers learn writing (set elsewhere). `yaziOf(lang)` returns the key or null.

| key | English | Turkish description |
|---|---|---|
| `alfabe` | alphabet: one sign per sound | her sese bir işaret |
| `hece` | syllabary: one sign per syllable | her heceye bir işaret |
| `resim` | pictographic: signs born from pictures of objects | nesnelerin resimlerinden doğan işaretler |
| `dugum` | knot-record: records kept with knots tied in cords | iplere atılan düğümlerle tutulan kayıt |
| `oyma` | carved notches: notches carved into stone and bone | taşa ve kemiğe oyulan çentikler |

### Words of the epoch (`cagKelimeleri(epoch, {dilBasi, toplam})`)

It is called at the end of every epoch (`epoch.js:364`). It broadcasts the system message "{n} new words entered the languages." (`Dillere N yeni kelime girdi.`). On error it broadcasts "Words of the epoch: {error}".
```
TYPES = [yer, yerlesim, olumlu, olay, teknoloji, tur, esya, yapit, gelenek, efsane, kaynak]
       (place, settlement, mortal, event, knowledge, species, item, structure, tradition, legend, resource)
entities = varliklar WHERE cag = epoch AND durum IN (kanon, olu) AND bekliyor = 0 AND tur IN TYPES ORDER BY guc_seviyesi DESC, id
perLang = {}; added = []
for v in entities:
    if |added| >= toplam (DIL.kelime_toplam 12): break
    lang = yerelDil(v); if none: continue
    if perLang[lang] >= dilBasi (DIL.kelime_dil_basi 3): continue
    if sozluk has row (dil_id = lang, ekleyen_tip = 'm', ekleyen_id = v.id): continue
    word = v has tag 'dilden-ad' ? lowercase(firstWord(v.ad)) : lowercase(adUret(lang, `kelime:${v.id}`, 'genel') or '')
    if !word or len(word) < DIL.kelime_harf_en_az (3): continue
    sozlukEkle(lang, [{kelime: word, anlam: MEANING[v.tur](v) or v.ad,
                       tur: v.tur in (yer, yerlesim, olumlu) ? 'özel ad' (proper noun) : 'isim' (noun),
                       koken: "Entered the language in Epoch {epoch} when {v.ad} ({type label, lowercase}) was born"}],
               'm', v.id, epoch)
    if inserted: perLang[lang]++; added.push({dil_id, kelime, varlik_id})
return added
```
`yerelDil(v)` (local language) tries these in order:
1. `konusulanDil(v)`, if canon.
2. The language of `v.yapan_id` (maker), if canon.
3. Walk `konum_id` up to `DIL.yerel_dil_derinlik` (6) levels. At each level take the first canon community (halk/yerlesim/hizip/tarikat, ORDER BY id) located at or equal to that level that speaks a canon language.

`MEANING` templates (translated):

| type | meaning template |
|---|---|
| yer | `{alt_tur or "place"}: {name}` |
| yerlesim | `{name} city; those who live there` |
| olumlu | `one who is like {name}; {alt_tur or "person"}` |
| olay | `{alt_tur or "event"}; a calamity or turning point like {name}` |
| teknoloji | `knowledge of {name}; one who knows it` |
| tur | `the creature called {name}` |
| esya | `{name}; {alt_tur or "item"}` |
| yapit | `{name}; {alt_tur or "structure"}` |
| gelenek | `{name} day; that rite` |
| efsane | `the tale of {name}` |
| kaynak | `{alt_tur or "resource"}: {name}` |

### Tunables: `DIL` group (dilmotoru.js). Group "Dil ve adlar" (Language and names)

| key (English snake_case) | original key | default | min | max | group | English label |
|---|---|---|---|---|---|---|
| signature_consonant_keep_pct | `DIL.imza_unsuz` | 62 | 10 | 100 | Language and names | Language signature: share of the world's consonants kept (%) |
| signature_suffix_pct | `DIL.imza_son` | 50 | 0 | 100 | Language and names | Chance a name ends with the language's own suffix (%) |
| signature_cluster_pct | `DIL.imza_kume` | 30 | 0 | 100 | Language and names | Chance the language's favourite consonant cluster appears in a name (%) |
| name_attempts | `DIL.ad_deneme` | 24 | 1 | 200 | Language and names | Max attempts per name generation |
| epoch_words_per_language | `DIL.kelime_dil_basi` | 3 | 0 | 50 | Language and names | Words of the epoch: max per language |
| epoch_words_total | `DIL.kelime_toplam` | 12 | 0 | 200 | Language and names | Words of the epoch: max in total |
| alphabet_min_samples | `DIL.alfabe_en_az` | 60 | 1 | 100000 | Language and names | World alphabet: min letter samples before filtering starts |
| alphabet_min_permille | `DIL.alfabe_binde` | 5 | 0 | 1000 | Language and names | World alphabet: min frequency (per mille) for a letter to count |
| dialect_sample_names_max | `DIL.lehce_ornek` | 30 | 0 | 500 | Language and names | Max sample names taken from the dialect text |
| ancestry_depth | `DIL.soy_derinlik` | 3 | 0 | 20 | Language and names | Ancestor-language generations included in the phonology |
| phonology_min_words | `DIL.kelime_en_az` | 8 | 0 | 200 | Language and names | Min sample words for the phonology (topped up from names if fewer) |
| phonology_max_word_syllables | `DIL.hece_en_cok` | 6 | 1 | 30 | Language and names | Max syllables of a word admitted to the phonology |
| default_avg_syllables_x10 | `DIL.ort_hece` | 24 | 10 | 100 | Language and names | Average syllables when there are no samples (tenths) |
| signature_required_consonants | `DIL.imza_en_az_unsuz` | 3 | 1 | 30 | Language and names | Min consonants needed to build a signature |
| signature_always_kept_consonants | `DIL.imza_kalici_unsuz` | 2 | 0 | 30 | Language and names | Most-frequent consonants always kept in the signature |
| signature_min_consonants | `DIL.imza_unsuz_en_az` | 5 | 1 | 30 | Language and names | Min consonants in a signature |
| signature_suffix_max_letters | `DIL.imza_ek_harf` | 4 | 1 | 20 | Language and names | Max letters of the signature suffix |
| signature_inherit_shift_min | `DIL.imza_miras_unsuz` | 3 | 0 | 30 | Language and names | Min consonants for a consonant shift in an inherited signature |
| ugly_same_onset_count | `DIL.cirkin_ayni_bas` | 3 | 2 | 20 | Language and names | Ugly name: number of syllables starting with the same consonant |
| name_min_syllables | `DIL.ad_hece_en_az` | 2 | 1 | 10 | Language and names | Min syllables of a generated name |
| name_max_syllables | `DIL.ad_hece_en_cok` | 4 | 1 | 20 | Language and names | Max syllables of a generated name |
| person_syllable_bias_x10 | `DIL.hece_kisi` | -3 | -50 | 50 | Language and names | Syllable bias for person names (tenths) |
| place_syllable_bias_x10 | `DIL.hece_yer` | 4 | -50 | 50 | Language and names | Syllable bias for place and people names (tenths) |
| syllable_repeat_retries | `DIL.hece_tekrar_deneme` | 4 | 0 | 50 | Language and names | Re-picks to avoid the same syllable twice in a row |
| name_min_letters | `DIL.ad_harf_en_az` | 3 | 1 | 30 | Language and names | Min letters of a generated name |
| name_max_letters | `DIL.ad_harf_en_cok` | 12 | 1 | 60 | Language and names | Max letters of a generated name |
| cognates_max | `DIL.kognat_en_cok` | 30 | 0 | 1000 | Language and names | Max shared roots shown between two languages |
| local_language_depth | `DIL.yerel_dil_derinlik` | 6 | 1 | 50 | Language and names | Location-chain depth searched for a local language (words of the epoch) |
| epoch_word_min_letters | `DIL.kelime_harf_en_az` | 3 | 1 | 30 | Language and names | Min letters of an epoch word |

The same `DIL` namespace is also declared in `world.js` (`DIL_K`). Keys used by this module: `benzer_uzunluk`, `aile_tavani`, `kok_harf`. The others belong to "tired motif" detection and the Turkish-word check elsewhere, and are listed for completeness.

| key | original key | default | min | max | group | English label |
|---|---|---|---|---|---|---|
| similar_name_max_length | `DIL.benzer_uzunluk` | 7 | 0 | 20 | Language and names | Longest name (letters) for which a one-letter difference is forbidden |
| name_family_cap | `DIL.aile_tavani` | 3 | 1 | 50 | Language and names | Max names starting with the same root (first `kok_harf` letters) |
| root_letters | `DIL.kok_harf` | 4 | 1 | 20 | Language and names | Name family and cognates: letters compared from the start |
| motif_threshold_pct | `DIL.motif_esik` | 18 | 1 | 100 | Language and names | Tired motif: share (%) of recent descriptions it appears in |
| motif_count | `DIL.motif_sayisi` | 14 | 0 | 60 | Language and names | Tired motifs shown in the prompt |
| motif_window | `DIL.motif_pencere` | 120 | 15 | 2000 | Language and names | Recent descriptions examined for tired motifs |
| motif_root_letters | `DIL.motif_kok` | 5 | 1 | 30 | Language and names | Tired motif: max letters of the compared root (after stripping suffixes) |
| motif_pair_threshold_pct | `DIL.motif_cift_esik` | 15 | 1 | 100 | Language and names | Tired two-word image: share (%) of recent depths and epoch narratives |
| motif_suffix_steps | `DIL.motif_ek_adim` | 3 | 0 | 10 | Language and names | Tired motif: max suffixes stripped from a word (LANGUAGE-SPECIFIC) |
| motif_min_root | `DIL.motif_kok_en_kisa` | 3 | 1 | 20 | Language and names | Tired motif: min root length after stripping; shorter words are not counted |
| motif_narratives | `DIL.motif_anlati` | 5 | 0 | 100 | Language and names | Tired motif: recent epoch narratives examined |
| motif_min_repeats | `DIL.motif_en_az` | 6 | 1 | 1000 | Language and names | Tired motif: min repetitions |
| motif_min_records | `DIL.motif_en_az_kayit` | 15 | 1 | 2000 | Language and names | Tired motif: min descriptions before checking starts |
| motif_cache | `DIL.motif_onbellek` | 16 | 1 | 1000 | Language and names | Tired motif: cached measurements per world |
| turkish_window | `DIL.turkce_pencere` | 3000 | 10 | 100000 | Language and names | Dialect check: recent descriptions scanned to separate Turkish words (LANGUAGE-SPECIFIC) |
| turkish_min_occurrences | `DIL.turkce_en_az` | 3 | 1 | 1000 | Language and names | Dialect check: a word seen lowercase in prose at least this often is Turkish, not an invented root (LANGUAGE-SPECIFIC) |
| dialect_min_root | `DIL.lehce_kok_en_az` | 3 | 1 | 20 | Language and names | Dialect check: min letters of an invented root examined |

### public/dil.js: Turkish grammar helpers (LANGUAGE-SPECIFIC: drop or replace)

This file is loaded by both the browser and the server. All of it exists to put correct Turkish case suffixes after proper nouns ("Kessa'nın", "Orvael'e"), because LLM output and templates glue suffixes on with an apostrophe. Several other parts depend on it:
- DB columns `varliklar.ek` and `ogullar.ek` (JSON `{okunus, tamlama, elle}`)
- the repair passes in `ekonar.js`
- `addBag`, which runs `ekDuzelt` on every bond description

The new app should not port any of this.

| Export | Purpose | Replacement in the English app |
|---|---|---|
| `sayiOkunus(n)` | Turkish word for the last significant digit-group of a number (bir/iki/…/on/…/yüz/bin/milyon) so suffix harmony can follow numbers ("5'i"). Tables `BIRLER` (ones), `ONLAR` (tens). | Drop. |
| `ekSozlugu(records)` | Loads a per-name suffix dictionary: name → `{okunus (pronunciation tail), tamlama (is a possessive compound), elle (manually set)}`. Also builds the sets of all name words and single-word names. | Drop (and drop the `ek` columns). |
| `ekSozluguBoyut()` | Size of that dictionary. | Drop. |
| `ekBilgisi(name)` | Computes `{okunus, tamlama}` for a name. `okunus` is the substring from the last vowel, the number word, or the Roman-numeral ordinal (`ROMA_OKUNUS`: I birinci … X onuncu). `tamlama` is true if the last word looks possessive (`-sı/-ğı/-ları/-ımı/-rı`; exception list deri, peri, sarı, geri, ileri, yarı, kuru, doğru, öteri) or ends in a high vowel and is not an adjective. | Drop. |
| `ekle(name, family, info?)` | Returns the harmonised suffix for a case family. Families: `ilgi` genitive (-(n)ın), `yonelme` dative (-(y)a/-na), `belirtme` accusative (-(y)ı/-nı), `bulunma` locative (-da/-ta/-nda), `ayrilma` ablative (-dan), `bulunmaKi` locative+relative (-daki), `kopulaSen` 2sg copula (-sın), `kopulaDir` copula (-dır), `cogul` plural (-lar). Applies vowel harmony (back/front, rounded) and consonant hardening after `fstkçşhp`. | Drop. English uses "of X", "to X", "X's", plain plural. |
| `yazimDuzelt(text)` | Orthography fixer. (1) Capital dotless `I` → dotted `İ` at the start of known Turkish i-words (`I_KOK`, ~50 roots such as ilk, iki, insan, işaret, imparator…) plus suffixes, unless the token is a known proper name. (2) Vowel-dropping stems before suffixes (`KOK_DEGISIR`: ahit→ahd, akıl→akl, oğul→oğl, şehir→şehr, nehir→nehr, isim→ism, fikir→fikr, hak→hakk, his→hiss, …). (3) "Name namesuffix" repetition → "Name'suffix". | Drop. Optionally use an English normaliser for "a/an" before vowel-initial names and "s's" → "s'". |
| `ekDuzelt(text)` | Runs `yazimDuzelt`, then rewrites every `Number'suffix` and `Capitalized Name'suffix` so the suffix agrees with the name. Applied to most stored narrative text. | Drop. Use a no-op or the light English normaliser above. |
| `cogulIyelik(plural)` | Plural noun + 3rd-person possessive (`-lar` → `-ları`, else `+i`). Used in "X'in köylüleri arasından" (= "from among X's peasants"). | Template "from among {X}'s {plural}". |
| `toplulukIci(name, type)` | "Among/inside community" phrase. Port this as English game text (see the table below). | Port as a small English helper. |
| `yonetimUnvaniEki(type)` / `yonetimUnvani(name, type)` | Title of whoever "governs/holds" an entity, chosen by the **type of the governed entity** (not by government form). Turkish form is "{name} {Title-poss}". Used for heirs' titles (`sim.js:1118`) and title repair (`ekonar.js:81`, which uses `'Hükümdarı'` as the "default title" sentinel). | Port as English data (see the table below). The format becomes "{Title} of {name}". |

`toplulukIci` in English:

| entity type | Turkish | English |
|---|---|---|
| olumlu (mortal) | `{X}'in çevresinde` | around {X} |
| halk (people), name ends with Halkı/Kavmi/Boyu/Kabilesi (People/Folk/Clan/Tribe) | `{X} arasında` | among the {X} |
| halk, otherwise | `{X} halkı arasında` | among the {X} people |
| hizip (faction) / tarikat (cult) / ordu (army) | `{X} içinde` | within {X} |
| anything else | `{X}'de` | in {X} |

`yonetimUnvani` titles:

| governed entity type | Turkish title | English title |
|---|---|---|
| kanun (law) | Bekçisi | Keeper |
| kaynak (resource) | Sahibi | Owner |
| esya (item) | Taşıyıcısı | Bearer |
| gelenek (tradition) | Koruyucusu | Guardian |
| teknoloji (knowledge) | Ustası | Master |
| yapit (structure) | Sahibi | Owner |
| eser (artwork) | Koruyucusu | Guardian |
| dil (language) | Koruyucusu | Guardian |
| efsane (legend) | Anlatıcısı | Teller |
| any other (settlement, people, region, …) | Hükümdarı | Ruler |

---

## 6. Interventions, knowledge, disasters, miracles (mudahale.js)

### Purpose and callers

`src/mudahale.js` holds the shared rules for affecting the world. Four kinds of caller use the same functions: the sons' tools, mortal agents, the world engine, and the god's own hand.

| Function | Callers |
|---|---|
| `afetUygula` (apply disaster) | `epoch.js:975` god intervention (severity `TANRI_EYLEM.afet_siddet`/100 = 1.1); `tools.js:1068` son tool `afet_gonder`; `sim.js:788` natural regional disasters; `sim.js:802` city plague; `sim.js:816` plague spreading along trade/tribute/rule bonds (no event record); `sim.js:1531` apocalypse (every region, random type; one event for the first region); `yaratici.js:202` creator's wrath; `tanriguc.js:434` world wrath; `otesi.js:154,210` (beyond/cosmic: quake, cosmic plague) |
| `mucizeUygula` (apply miracle) | `epoch.js:970` god; `tools.js:1005` son tool `mucize`; `sim.js:916` a wizard protects or blesses their homeland; `yaratici.js:211` creator's favour (bereket) |
| `olayKaydi` (event record) | Same callers as the disasters, right after `afetUygula`. |
| `ogret` / `bilir` / `bildikleri` / `dalOf` | Throughout `sim.js`, `derin.js`, `olumluler.js`, `seyahat.js`, `epoch.js` (god's "bilgi" gift), son tool `bilgi_ver`. |
| `yasaCozucu` / `aktifYasalar` | Engine modules check natural-law mechanics, e.g. `Y.has('afet', region)` doubles disaster chance, `Y.has('kuraklik', r)`. |

God intervention entry point: `POST /api/varliklar/:id/mudahale {eylem, tur, bilgi_id}` → `E.tanriMudahale` (`epoch.js:958`). The action `eylem` is one of `mucize` (miracle), `afet` (disaster), `bilgi` (knowledge) or `lanet` (curse). It works like this:
- The cost comes from `MUDAHALE_BEDEL` and is paid from the creator's essence (öz).
- A miracle or curse that changes nothing is refunded with an error message.
- A disaster is only allowed on a bolge, yer or yerlesim (region, place, settlement).
- Knowledge must be a `teknoloji` entity; teaching it again is refunded.
- A curse lowers refah, bereket, guc, savunma, servet, bolluk and etki by `TANRI_EYLEM.lanet_stat` (15) and adds the tag `lanetli` (cursed).
- A chronicle line of type 'tanri' (god) is written.

### Knowledge (bilgi)

- **`dalOf(tech)`** (branch of): the value of the tag `dal:<branch>` on a `teknoloji` (knowledge) entity, else null.
- **`bildikleri(vId)`** (what v knows): targets of active bonds `bilir` (knows), with `kaynak_tip='v'`, `kaynak_id=vId`, `hedef_tip='v'`, where the target is `tur='teknoloji'` and `durum='kanon'`.
- **`bilir(vId, branch)`** (knows): `bildikleri(vId)` has some tech with `dalOf == branch`. Each call runs 1 + n queries.
- **`ogret(vId, techId, epoch, note=null)`** (teach):
  1. If an active `bilir` bond vId→techId exists, return false.
  2. Otherwise `addBag('v', vId, 'v', techId, 'bilir', note, epoch)`.
  3. Then `tech.statlar.yayginlik = clamp(yayginlik + MUDAHALE.bilgi_yayginlik (8), 0, 100)`. Save and return true.
  4. It does not check that techId is a technology; callers do.

**Knowledge branches** (`BILGI_DALLARI`). The effect texts are shown to players and LLM agents. The mechanics are implemented in other modules.

| key | English name (Turkish) | Effect text (translated) |
|---|---|---|
| tarim | Agriculture (Tarım) | Knowers' population grows 50% faster; famine and drought hit at half severity. |
| metalurji | Metallurgy (Metalurji) | +15 damage/protection on the weapons and armour they make. |
| denizcilik | Seafaring (Denizcilik) | Trade, war and migration with communities beyond the sea. |
| yazi | Writing (Yazı) | Their languages grow more complex; what they know spreads to partners twice as fast. |
| mimarlik | Architecture (Mimarlık) | +20 splendour and sturdiness on their structures; resistant to earthquakes. |
| tip | Medicine (Tıp) | Plagues hit at half severity; mortals' lifespan +20. |
| buyu | Magic (Büyü) | Magic stat +10; items they make +10 power. |
| savas | Art of war (Savaş sanatı) | +12 to war strength. |
| gokbilim | Astronomy (Gökbilim) | They read the epoch's star: they sense disasters in advance and suffer them at half severity. |
| ticaret | Trade (Ticaret) | Double prosperity from trade routes. |
| gokyuzu_seyri | Sky navigation (Gökyüzü seyri) | Can discover routes between worlds; the risk of getting lost in travel is halved. |
| gemi_yapimi | Shipbuilding (Gemi yapımı) | Can build ships (vehicles) for travel between worlds. |
| kapi_bilimi | Gate lore (Kapı bilimi) | Can open and close ancient gates; gate routes complete in one epoch. |
| yol_biliciligi | Path-knowing (Yol biliciliği) | Can fold space: with a cosmic resource, routes drop to one epoch. |
| bosluk_yasami | Void living (Boşlukta yaşam) | Can found colonies on worlds with thin or no atmosphere; losses in travel are reduced. |
| olumsuzluk | Quest for immortality (Ölümsüzlük arayışı) | Knowers' mortals reach for immortality; those who succeed do not age, but the gods see them as a threat. |
| biyobuyu | Biomancy (Biyobüyü) | Merges and alters living things: can weave chimeras and steer mutations. |
| yasak | Forbidden knowledge (Yasak bilgi) | Great power: war +15, magic +15, forces gates. The price: knowers' sanity falls every epoch, leakage flows into their world; Fate is watching. |

The first ten are terrestrial; the last eight are cosmic or travel branches.

### Natural laws (doğa yasaları)

- A **law** is an entity `tur='yasa'` (law). Its mechanics are encoded as tags `yasa:<mechanic>`.
- **`aktifYasalar(worldId=null)`** (active laws) returns the set of mechanic keys from all **canon** law entities.
  - If `worldId` is given, only laws with `(dunya_id ?? 1) == worldId` count. World-less legacy laws belong to world 1.
  - With no `worldId`, the set covers the whole cosmos.
- **`yasaCozucu()`** (law resolver) returns `{has(law, x?), of(x)}`.
  - It caches per-world sets for the resolver's lifetime (callers create one per epoch step).
  - `x` may be an entity, in which case its `dunya_id ?? 1` is used, or a world id.
  - `has(law)` without `x` checks the cosmos-wide union (also cached).
  - A plain `Set` can be passed instead; its `has(law)` ignores the second argument.

**Law mechanics** (`YASA_MEKANIKLERI`). Descriptions are translated; they are implemented by the engine modules.

| key | English description |
|---|---|
| yok | Narrative only; no mechanical effect. |
| olumsuzluk | Mortals do not age, but population grows at half speed. |
| kisa_omur | Mortals age twice as fast; population grows 50% faster. |
| olu_doner | Dead heroes return as ghosts half the time. |
| buyu_bedeli | Peoples with high magic pay part of their population to magic every epoch. |
| savas_yasagi | Wars break out half as often but are twice as bloody. |
| bereket | Every land's fertility rises each epoch. |
| kuraklik | Every land's fertility falls each epoch. |
| deniz_yasagi | Seas cannot be crossed; seafaring is useless. |
| tek_dil | Languages spread twice as fast through conquest and trade. |
| afet | Natural disasters happen twice as often. |

### Disasters (`afetUygula(target, type, severity=1)`)

`type` is one of: `deprem` (earthquake), `sel` (flood), `veba` (plague), `kuraklik` (drought), `firtina` (storm). `severity` is a multiplier, 1 = nominal; callers pass e.g. `siddet / scale`.

**Affected set** (`etkilenenler`):
- BFS from the target over `varliklar WHERE konum_id = id AND durum = 'kanon'`, with a visited set so location cycles terminate.
- It includes the target itself, whatever its status, followed by every canon descendant by location (communities, structures, mortals, items, …).

**Per affected entity x:**
```
if x has tag 'korunmuş' (protected):
    remove the tag; persist etiketler; notes.push("{x.ad} was protected"); continue      // shield consumed per entity
k = severity * (bilir(x.id, 'gokbilim') ? MUDAHALE.gokbilim_siddet/100 : 1)            // astronomy halves
st = x.statlar; before = st.nufus ?? st.murit ?? null
if x.tur == 'olumlu' (named mortal):
    p = MUDAHALE[`${type}_olumlu_olum`]/100 * k * (type == 'veba' ? (bilir(x,'tip') ? tip_siddet/100 : 1) : 1)
    if random() < p:
        if olumluOlur(x, currentEpoch, noop, {sebep: DEATH_TEXT[type] or "died in the disaster"}): dead.push(x)
    elif random() < MUDAHALE.afet_yara_sans/100 and
         olumluYarala(x, round(MUDAHALE.afet_yara * k), {sebep: "<DEATH_TEXT> died of wounds received", cag}) == 'oldu':
        dead.push(x)
    continue                                   // mortals never take stat changes
reduce(key, frac): if st[key] != null: st[key] = clamp(st[key] * (1 - frac*k), key=='murit' ? 1 : SINIR.nufus_taban, SINIR.nufus_tavan)
drop(key, n):      if st[key] != null: st[key] = clamp(st[key] - n*k, 0, 100)
// clamp() rounds to integer
switch type:
  deprem:   reduce('nufus', deprem_nufus/100)
            if x.tur == 'yapit' (structure):
                drop('saglamlik', deprem_saglamlik * (bilir(x.yapan_id || 0, 'mimarlik') ? mimarlik_siddet/100 : 1))
                if st.saglamlik <= 0:
                    UPDATE varliklar SET durum='yok_edildi', olum_cag=<current epoch>, kader_notu='Collapsed in the earthquake.' WHERE id=x.id
                    destroyed.push(x); continue          // stats not saved
  sel:      drop('refah', sel_refah); reduce('nufus', sel_nufus/100)
            if st.bereket != null: st.bereket = clamp(bereket + sel_bereket, 0, 100)   // NOT scaled by k
  veba:     t = bilir(x,'tip') ? tip_siddet/100 : 1
            reduce('nufus', veba_nufus/100 * t); reduce('murit', veba_murit/100 * t)
  kuraklik: t = bilir(x,'tarim') ? tarim_siddet/100 : 1
            drop('bereket', kuraklik_bereket * t); reduce('nufus', kuraklik_nufus/100 * t)
  firtina:  drop('savunma', firtina_savunma); drop('refah', firtina_refah)
saveStat(x)
if x.tur in (halk, yerlesim, tarikat, hizip, yapit):
    effect.communities.push({id: x.id, loss: before and after non-null ? max(0, round(before - after)) : null})
```

After the loop:
- Set the module-global `SON_ETKI = {hedef, tur, topluluk, olen, yikilan}` (last effect: target, type, communities, dead, destroyed).
- Notes are returned as sentences:
  - "{A}, {B} and {C} collapsed" if any structures were destroyed.
  - "{…} perished" if any mortals died.
  - The list is joined as "A" / "A and B" / "A, B and C" (Turkish `ile` / `ve`).
- Return `notes: string[]`.

**Death causes** (`AFET_OLUM`), translated:

| type | Turkish | English |
|---|---|---|
| deprem | depremde enkaz altında kaldı | was buried under rubble in the earthquake |
| sel | selde boğuldu | drowned in the flood |
| veba | vebadan öldü | died of the plague |
| kuraklik | kuraklıkta açlıktan öldü | starved in the drought |
| firtina | fırtınada can verdi | perished in the storm |

The wound-death cause is built as `"{cause} aldığı yaralardan öldü"`, which reads ungrammatically ("drowned in the flood died of the wounds received"). In English write "died of wounds suffered in the {disaster}".

**Disaster catalogue** (`AFETLER`). Its effect texts are generated live from the current tunables.

| key | English name (Turkish) | Effect text template |
|---|---|---|
| deprem | Earthquake (Deprem) | Population −{deprem_nufus}%, structures' sturdiness −{deprem_saglamlik} (collapsed ones are destroyed). |
| sel | Flood (Sel) | Prosperity −{sel_refah}, population −{sel_nufus}%; then fertility +{sel_bereket}. |
| veba | Plague (Salgın) | Population −{veba_nufus}%, followers −{veba_murit}% ({tip_siddet}% for those who know medicine). |
| kuraklik | Drought (Kuraklık) | Fertility −{kuraklik_bereket}, population −{kuraklik_nufus}% ({tarim_siddet}% for those who know agriculture). |
| firtina | Storm (Fırtına) | Defence −{firtina_savunma}, prosperity −{firtina_refah}. |

### Disaster event record (`olayKaydi({tur, hedef, cag, ad, aciklama, yaratan_id=null, kaynak='dunya', siddet=50})`)

A disaster leaves a permanent `olay` (event) entity. If no name is given, Fate names it at the end of the epoch.
```
pending = ad ? 0 : 1                                     // bekliyor: awaiting Fate's naming
name = ad or `${hedef.ad} ${SUFFIX[tur]} (Çağ ${cag})`
   SUFFIX: veba 'Salgını' (Plague), deprem 'Depremi' (Earthquake), sel 'Seli' (Flood), kuraklik 'Kuraklığı' (Drought), anything else 'Fırtınası' (Storm)
   English: "{Target} {Plague|Earthquake|Flood|Drought|Storm} (Epoch {cag})"
location = hedef.tur in (bolge, yer, yerlesim) ? hedef.id : hedef.konum_id
INSERT varliklar (ad=name, tur='olay', alt_tur=label(tur), aciklama = aciklama or "[World engine] {label(tur)} over {hedef.ad}.",
                  statlar={siddet}, guc_seviyesi = clamp(round(siddet / olay_guc_bolen), olay_guc_alt, olay_guc_ust),
                  yaratan_id, cag, konum_id=location, etiketler=['afet', tur], kaynak, bekliyor=pending)
     // durum defaults to 'kanon'; dunya_id set by the DB trigger (from konum, then creator son's active world, …)
addBag(event → hedef, 'neden_oldu' (caused))
if location: addBag(event → location, 'icinde' (inside))
if SON_ETKI and SON_ETKI.hedef == hedef.id and SON_ETKI.tur == tur:
    for community c in SON_ETKI.topluluk, c != hedef: addBag(event → c, 'neden_oldu', c.loss ? "{loss} lives lost" : "struck")
    for dead mortal o: addBag(event → o, 'neden_oldu', "died there")
    for destroyed y:   addBag(event → y, 'neden_oldu', "was destroyed")
    SON_ETKI = null
return eventId
```
- `kaynak` values: `'dunya'` (engine), `'tanri'` (god), `'ogul'` (son).
- `label(tur)` uses the display-label map (deprem, sel, veba, kuraklık, fırtına).
- Typical severities passed in: god = `TANRI_EYLEM.afet_olay` (75); son = the computed severity; engine = `DE.afet_siddet_taban + d(zar)`.

### Miracles (`mucizeUygula(target, type, epoch)`)

`type` is one of: `sifa` (healing), `bereket` (abundance), `baris` (peace), `koruma` (protection). The `epoch` argument is unused.
```
st = target.statlar; notes = []
if target.tur == 'tarikat' and has a tag starting 'dirilis:' (resurrection cult for a dead god):
    st.adanmislik = clamp(adanmislik + MUDAHALE.dirilis_adanmislik (25), 0, DERIN_YASAM.adanmislik_tavan (200))
    notes.push("resurrection devotion {adanmislik}/{DERIN_YASAM.dirilis_adanmislik (100)}")
switch type:
  sifa:    if nufus != null: nufus = clamp(nufus * (100 + sifa_artis)/100, SINIR.nufus_taban, SINIR.nufus_tavan)
           if murit != null: murit = clamp(murit * (100 + sifa_artis)/100, 1, SINIR.murit_tavan)
           if target.tur == 'olumlu' and can != null: can = max(can, sifa_can)       // not capped at max HP
           if tag 'lanetli' (cursed): remove, persist etiketler, notes.push("the curse was lifted")
  bereket: if bereket != null: bereket = clamp(bereket + bereket_bereket, 0, 100)
           elif refah != null: refahEkle(st, bereket_refah)        // sim.js: diminishing-returns prosperity gain, clamp 0..100
           elif bolluk != null: bolluk = clamp(bolluk + bereket_bolluk, 0, 100)
  baris:   rows = active 'dusman' (enemy) bonds where (kaynak_tip='v' and kaynak_id=target) or (hedef_tip='v' and hedef_id=target)
           set aktif=0 on each
           if rows: notes.push("hostility with {A, B and C} ended")    // names via nameOf('v', otherEndId)
  koruma:  if savunma != null: savunma = clamp(savunma + koruma_savunma, 0, 100)
           add tag 'korunmuş' (protected) if missing; persist   // consumed by the next disaster that touches this entity
saveStat(target)
return notes
```

**Miracle catalogue** (`MUCIZELER`):

| key | English name (Turkish) | Effect text |
|---|---|---|
| sifa | Healing (Şifa) | Population/followers +{sifa_artis}%, the curse is lifted, the mortal's health is restored. |
| bereket | Abundance (Bereket) | Fertility +{bereket_bereket} or prosperity +{bereket_refah}. |
| baris | Peace (Barış) | All of the target's hostilities end. |
| koruma | Protection (Koruma) | Defence +{koruma_savunma}; protected from the next disaster. |

The son tool `mucize` adds two things on top: healing also raises sanity (`OGUL.sifa_sagduyu`) of the target and its direct children, and an unpatroned community starts worshipping the son.

### Intervention costs (`MUDAHALE_BEDEL`, plain constant in rules.js, NOT tunable)

These are the god's essence costs per action. Sons pay a share through `OGUL_KOZMIK.*()` plus a power-level term.

| key | original | value |
|---|---|---|
| miracle_cost | `MUDAHALE_BEDEL.mucize` | 15 |
| disaster_cost | `MUDAHALE_BEDEL.afet` | 20 |
| knowledge_cost | `MUDAHALE_BEDEL.bilgi` | 12 |
| curse_cost | `MUDAHALE_BEDEL.lanet` | 15 |

New design: make these tunables (group "Intervention").

### Tunables: `MUDAHALE` group (declared in two places, same namespace). Group "Müdahale" (Intervention)

From `rules.js` (`MUDAHALE_ETKI`):

| key (English snake_case) | original key | default | min | max | group | English label |
|---|---|---|---|---|---|---|
| knowledge_spread_gain | `MUDAHALE.bilgi_yayginlik` | 8 | 0 | 100 | Intervention | Spread increase of a taught piece of knowledge |
| astronomy_disaster_pct | `MUDAHALE.gokbilim_siddet` | 50 | 0 | 100 | Intervention | Disaster severity for those who know astronomy (%) |
| quake_population_loss_pct | `MUDAHALE.deprem_nufus` | 10 | 0 | 100 | Intervention | Earthquake: population loss (%) |
| quake_sturdiness_loss | `MUDAHALE.deprem_saglamlik` | 25 | 0 | 100 | Intervention | Earthquake: structures' sturdiness loss |
| architecture_quake_pct | `MUDAHALE.mimarlik_siddet` | 50 | 0 | 100 | Intervention | Earthquake severity on structures whose maker knows architecture (%) |
| flood_prosperity_loss | `MUDAHALE.sel_refah` | 12 | 0 | 100 | Intervention | Flood: prosperity loss |
| flood_population_loss_pct | `MUDAHALE.sel_nufus` | 5 | 0 | 100 | Intervention | Flood: population loss (%) |
| flood_fertility_gain | `MUDAHALE.sel_bereket` | 5 | 0 | 100 | Intervention | Flood: fertility that follows |
| plague_population_loss_pct | `MUDAHALE.veba_nufus` | 18 | 0 | 100 | Intervention | Plague: population loss (%) |
| plague_follower_loss_pct | `MUDAHALE.veba_murit` | 10 | 0 | 100 | Intervention | Plague: follower loss (%) |
| medicine_plague_pct | `MUDAHALE.tip_siddet` | 50 | 0 | 100 | Intervention | Plague severity for those who know medicine (%) |
| drought_fertility_loss | `MUDAHALE.kuraklik_bereket` | 20 | 0 | 100 | Intervention | Drought: fertility loss |
| drought_population_loss_pct | `MUDAHALE.kuraklik_nufus` | 6 | 0 | 100 | Intervention | Drought: population loss (%) |
| agriculture_drought_pct | `MUDAHALE.tarim_siddet` | 50 | 0 | 100 | Intervention | Drought severity for those who know agriculture (%) |
| storm_defence_loss | `MUDAHALE.firtina_savunma` | 10 | 0 | 100 | Intervention | Storm: defence loss |
| storm_prosperity_loss | `MUDAHALE.firtina_refah` | 8 | 0 | 100 | Intervention | Storm: prosperity loss |
| healing_growth_pct | `MUDAHALE.sifa_artis` | 10 | 0 | 1000 | Intervention | Healing miracle: population and follower increase (%) |
| healing_health | `MUDAHALE.sifa_can` | 100 | 1 | 100000 | Intervention | Healing miracle: value the mortal's health rises to |
| abundance_fertility_gain | `MUDAHALE.bereket_bereket` | 20 | 0 | 100 | Intervention | Abundance miracle: land fertility increase |
| abundance_prosperity_gain | `MUDAHALE.bereket_refah` | 15 | 0 | 100 | Intervention | Abundance miracle: prosperity increase for targets without fertility |
| abundance_plenty_gain | `MUDAHALE.bereket_bolluk` | 25 | 0 | 100 | Intervention | Abundance miracle: resource plenty increase |
| protection_defence_gain | `MUDAHALE.koruma_savunma` | 20 | 0 | 100 | Intervention | Protection miracle: defence increase |
| resurrection_devotion_gain | `MUDAHALE.dirilis_adanmislik` | 25 | 0 | 200 | Intervention | Devotion increase when a miracle falls on a resurrection cult |
| disaster_event_power_divisor | `MUDAHALE.olay_guc_bolen` | 12 | 1 | 100 | Intervention | Disaster event power level: severity / this |
| disaster_event_power_min | `MUDAHALE.olay_guc_alt` | 2 | 1 | 12 | Intervention | Lowest power level of a disaster event |
| disaster_event_power_max | `MUDAHALE.olay_guc_ust` | 9 | 1 | 12 | Intervention | Highest power level of a disaster event |

From `mudahale.js` (`AO`). All probabilities are for severity 1.

| key | original key | default | min | max | group | English label |
|---|---|---|---|---|---|---|
| quake_mortal_death_pct | `MUDAHALE.deprem_olumlu_olum` | 12 | 0 | 100 | Intervention | Earthquake: chance a named mortal at the struck place dies (%) |
| flood_mortal_death_pct | `MUDAHALE.sel_olumlu_olum` | 8 | 0 | 100 | Intervention | Flood: chance a named mortal dies (%) |
| plague_mortal_death_pct | `MUDAHALE.veba_olumlu_olum` | 15 | 0 | 100 | Intervention | Plague: chance a named mortal dies (%; medicine mitigates) |
| drought_mortal_death_pct | `MUDAHALE.kuraklik_olumlu_olum` | 4 | 0 | 100 | Intervention | Drought: chance a named mortal dies (%) |
| storm_mortal_death_pct | `MUDAHALE.firtina_olumlu_olum` | 5 | 0 | 100 | Intervention | Storm: chance a named mortal dies (%) |
| disaster_wound_chance_pct | `MUDAHALE.afet_yara_sans` | 30 | 0 | 100 | Intervention | Chance a named mortal who survives a disaster is wounded (%) |
| disaster_wound_damage | `MUDAHALE.afet_yara` | 25 | 0 | 1000 | Intervention | Health lost by a wounded mortal (scaled by severity) |

Referenced from other groups:

| key | original key | default | min | max | group | English label |
|---|---|---|---|---|---|---|
| resurrection_devotion_cap | `DERIN_YASAM.adanmislik_tavan` | 200 | 1 | 10000 | Creator and essence | Cap of resurrection devotion |
| resurrection_devotion_needed | `DERIN_YASAM.dirilis_adanmislik` | 100 | 0 | 10000 | Creator and essence | Devotion needed for the resurrection rite |
| settlement_population_floor | `SINIR.nufus_taban` | 10 | 1 | 100000 | Population and growth | Lowest population of settlements and communities |
| people_population_cap | `SINIR.nufus_tavan` | 50000000 | 1000 | 2000000000 | Population and growth | Highest population of a people |
| cult_follower_cap | `SINIR.murit_tavan` | 10000000 | 1000 | 2000000000 | Religion and language | Most followers of a cult |
| god_disaster_severity_pct | `TANRI_EYLEM.afet_siddet` | 110 | 0 | 1000 | (god actions) | Severity multiplier of the god's hand-sent disaster (%) |
| god_disaster_event_severity | `TANRI_EYLEM.afet_olay` | 75 | 0 | 100 | (god actions) | Severity of the god's disaster in its event record |
| god_curse_stat_loss | `TANRI_EYLEM.lanet_stat` | 15 | 0 | 100 | (god actions) | Stat loss from the god's curse on a community |

Tunable mechanics (`tanimla`):
- `tanimla(area, {key: [default, label, min=0, max=max(1000, |default|·10), group='Diğer' (Other)]})` registers each key as `AREA.key`.
- The live value is the saved override from `dunya.denge_ayar` JSON, else the default.
- `rules.js` has a local pre-registration copy, which `denge.js` re-registers at boot.

### Random helpers used

- `clamp(v, lo, hi)` = `max(lo, min(hi, round(Number(v) || 0)))`. It **always rounds to an integer**.
- `d(n)` = `1 + floor(random() * n)` (a die). It is re-exported by mudahale.js.
- Disasters and miracles use the unseeded `Math.random()`, so they are not reproducible.

---

### Bugs, design smells and notes for the rewrite (this slice)

**Map**
- **Float32 storage.**
  - `yuk`, `nem` (Float32Array) and the Dijkstra `maliyet` (Float32Array) are float32, while the costs pushed on the heap are float64.
  - `c > maliyet[i]` can be true right after a push if float32 rounding went down, so that cell is never expanded. In an 8-region test this changed 5 cells.
  - Exact reproduction needs float32 emulation (numpy float32). A clean rewrite should use float64 and accept different maps.
- **Delaunay dependency for exact parity.** Neighbour order (`del.neighbors`), `find` and heap tie-breaking affect results.
  - A Python backend cannot reproduce maps exactly without a faithful Delaunator/d3-delaunay port.
  - Decision needed: (a) port Delaunator to Python and keep parity with existing saves, or (b) make the backend the only generator and ship cell polygons and fields to the React client instead of recomputing there.
- **Two regions on the same seed cell.** If a region's stored `xy` cell is acceptable, `tohumSec` returns it even when another region already uses that cell. The later seed overwrites the owner at cost 0, and the earlier region may get no cells.
- **Third-level regions vanish.** Sub-sub-regions get no cells because `bolgeOf` only holds top-level ids, so they are missing from `bilgi` and adjacency.
- **Sub-region adjacency is partial.** A sub-region only neighbours other sub-regions, never top-level regions.
- **`suMu` is Turkish-regex based** and unanchored. `koy` matches "koyun" (sheep) and "Koyu…", and `su\b` matches any word ending in "su". Renaming a region can flip it between land and water.
- **Cache signature gaps.** The signature omits `ad`/`alt_tur` (which drive `suMu`) and world `tur` (which drives biome names). A rename or type-only change can serve a stale map. Manual `haritaGecersiz` calls cover some cases, not all.
- **Cache check cost.** The cache check reads every row (`imzaKur`) on every call. `derin.js` had to add a per-step context to avoid O(n²) slowdowns. The new design should use an explicit version counter bumped on writes.
- **Unbounded caches.** `haritaHesapla()` without an argument recomputes per world; `araziOnbellek` is unbounded.
- **"Infinite world" vs clamping.** `ufuk.js` clamps new frontier seeds to 3000×2040, contradicting the infinite-world design. Dragging markers has no bounds at all.
- **Window growth shifts the map.** It changes cell indices and can change Delaunay adjacency and flood results near the old border. Adjacency (`komsular`) can therefore change retroactively when a far entity is added.
- **Dead code:** `rnd = mulberry(hash(seed))`.
- **Hard-coded constants:** all map constants are untunable (see the constants table).
- **Seed vs display position.** The persisted region `harita_xy` is the seed, not the displayed centroid cell (`konum`). Both concepts must be kept.

**Language**
- **BUG: signature parser.** `imzaOku` uses `e.slice(6)` on `"imza:u=…"`, but the prefix `imza:` is 5 characters. The consonant set lands under key `''` and `u` is lost: parsing `imza:u=lmnrv;k=rn;s=ar;l=1` gives `{'': 'lmnrv', k, s, l}`.
  - After a restart every stored signature loses its consonant filter.
  - Worse, a child language whose parent signature is read from a tag hits `[...undefined]` and throws, so `adUret` silently runs without a signature. This is confirmed in live data: tags like `imza:u=hlsnrt;…` exist.
  - Fix: parse after `'imza:'` (5 characters) or store the signature as JSON.
- **Signature recursion has no cycle guard** beyond direct self-reference. A↔B ancestry overflows the stack; the error is caught upstream.
- **Inconsistent vowel sets.** `UNLU` includes `âîû`, but the suffix and cluster regexes use `[aeıioöuü]`.
- **Inconsistent name-collision lists.** `adUret`'s similarity list includes only varliklar and ogullar, while `isimAlinmis` also checks stars, worlds and foreign gods.
- **Ancestry lookups are nondeterministic in principle.** `fonoloji` follows 'soyundan' bonds without `hedef_tip='v'` and both use `LIMIT 1` with no ORDER BY.
- **`dildenAd` does not check language status** (`durum`). It can generate from a rejected language.
- **Cache key cost.** The `fonoloji` cache key concatenates all DIL values on every call.
- **Quadratic cost.** `kognatlar` is O(n·m) over full lexicons. `adUret` loads all names on each call.
- **Heavy Turkish coupling.** `isTurkishName`, `lehceOrnekleri`, `aramaNorm`, `tr` locale casing and the whole `dil.js` are LANGUAGE-SPECIFIC.
- **`yonetimUnvani` naming.** It is keyed by the governed entity's type, not by government form. Its sentinel use of the string 'Hükümdarı' in `ekonar.js` should become an enum.

**Interventions**
- **`SON_ETKI` is a hidden module-global coupling** between `afetUygula` and `olayKaydi`.
  - Callers that apply a disaster without recording an event (`sim.js:816` plague spread) leave a stale effect.
  - The apocalypse (`sim.js:1531-1532`) applies to many regions and then records one event for `bolgeler[0]`, so the links match only if the last region is the first.
  - New design: return the effect object from `afetUygula` and pass it explicitly to `olayKaydi`.
- **Unknown disaster types.** The default event-name suffix for any unknown type is "Storm".
- **Ungrammatical wound-death text** (see above).
- **Peace miracle problems.**
  - It deactivates enemy bonds whose other end may be a son (`'o'`), yet names that end with `nameOf('v', id)`, which is the wrong table.
  - It does not end ongoing war events. Decide whether peace should also close wars.
- **Inconsistent clamps.**
  - `reduce('murit')` clamps to `nufus_tavan` instead of `murit_tavan`.
  - Peoples use the settlement floor `nufus_taban` (10) instead of `halk_nufus_taban`.
  - Healing sets mortal health to `max(can, 100)` without a max-HP cap.
  - Flood fertility gain is not scaled by severity.
- **Disaster loss is not persisted on collapse.** A collapsed structure's stat change is not saved (harmless). A protected target shields only itself, not its contents; this is intended per entity but worth confirming.
- **`bilir()` cost.** It runs 1 + n queries and is called up to three times per affected entity.
- **Name collision.** `MUDAHALE.dirilis_adanmislik` (+25 gain) vs `DERIN_YASAM.dirilis_adanmislik` (100 threshold): same key name, different meanings.
- **`MUDAHALE_BEDEL` is untunable**, contrary to the project's "no untunable constants" rule.
- **Non-reproducible.** `Math.random()` everywhere in disasters makes tests nondeterministic. The new design should inject a seeded RNG.


## 7. Open questions for the integrator

1. **Determinism.** The old engine uses unseeded `Math.random()` everywhere (the map/naming code has its own seeded mulberry32). Decide: one seeded PRNG per epoch (recommended, makes ticks replayable) vs. non-deterministic.
2. **Map parity.** Reproducing existing saves' maps exactly needs a Python port of d3-delaunay/Delaunator with float32 emulation and identical heap tie-breaking (§4). Alternative: backend becomes the only generator and ships polygons to the client; old saves get new maps.
3. **Spatial model.** sim.js uses containment-tree distance (`mesafe`), tools and migration use Voronoi adjacency (`yakinMi`/`komsular`). Pick one region-graph distance for everything.
4. **Water regions** are detected by Turkish name regex — replace with an explicit `is_water`/terrain field (and similarly underworld regions, temples, miracles, ships, debt terms: explicit fields instead of string matching).
5. **War declaration paths.** Mortal tool `savas_ilan_et`, tribute insolence and adventure theft create enmity bypassing `savasIlan` (war cap, ceasefire, alliance breaking). Route all through one war service?
6. **Mortal creations go straight to canon** (no Fate review) while engine creations are `pending` for Fate. Keep?
7. **Mortal read tools see all worlds/entities.** Limit to what the mortal can know?
8. **Peace miracle** doesn't end ongoing war events — should it?
9. **Hard-coded constants** (map constants, intervention costs, several fallbacks) violate the project rule "every balance number is a tunable"; the rewrite should make them tunables.
10. **Turkish-only tunables** (tired-motif / Turkish-detection DIL keys) — drop?
