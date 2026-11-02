# 05 — Deep Mechanics (`src/derin.js`)

Source: `/Users/egedogan_dursun/aerona/src/derin.js` (2,753 lines). Turkish name of the module: *Derin mekanikler* ("deep mechanics", internal milestone S2/S6). This file is **LLM-free**: every function is rule-based and runs inside the world engine (`sim.js`) or the epoch transition. It owns:

1. Community relations (score, history, blood feud) and diplomacy (war declaration, peace, alliance, marriage alliance, betrayal, truces, grudge fading).
2. Campaigns: multi-epoch wars, armies, commanders, named battles, sieges, duels, prisoners, ransom, tribute, conquest.
3. Social classes and economy: class shares, satisfaction, food/ore/goods, prices, famine, weapon forging, guild bankruptcy, class uprisings, trade flows.
4. Heroes: quests, companions, nemeses, master–apprentice chains.
5. Dark ages: knowledge forgotten and rediscovered from ruins; knowledge spread.
6. Espionage, wonders, abandonment into ruins.
7. Climate eras per world.
8. God (son) death, corpse, shade, resurrection cult, resurrection, fading by being forgotten.
9. Spontaneous births: notable mortals, rulers, villages, ethnogenesis (new peoples), sapient species.
10. Writing systems; belief & memory (legend spread, manifestation, legendification, fairy tales, tradition and prophecy forgetting).
11. Life seeding of empty worlds; first language and first faith; ruin resettlement; refugees; spirits resting; language death; engine-built works; spontaneous factions; religion spread; cultural exchange; world age / golden ages.
12. Low-level helpers used across the codebase: record creation (`kayitAc`), death (`oldur`, dead-bond sweep), tag add/remove, distance, truce/war-cap primitives.

All prose below uses English names; Turkish originals appear once in parentheses. Wherever text is emitted (chronicle notes, descriptions) the Turkish template is translated; Turkish grammar helpers (`ekDuzelt`, `cogulIyelik`, apostrophe+suffix like `'in`, `'e`, `'den`) are **LANGUAGE-SPECIFIC: drop** — English templates do not need suffix harmony.

---

## 0. Conventions used in this document

| Notation | Meaning (original) |
|---|---|
| `chance(p%)` | `Math.random() < p/100` (`sans`) |
| `d(n)` | uniform integer in `1..n` (`rules.d`) |
| `clampi(v, lo, hi)` | `max(lo, min(hi, round(v)))` — **rounds to integer** (`rules.clamp`); a non-numeric `v` becomes 0 |
| `clampf(v, lo, hi)` | same without rounding (`sinirla`), used for probabilities |
| `pick(arr)` | uniform random element (`sec`) |
| `canon(x)` | `x` exists and `x.status == 'canon'` (`canli`, i.e. alive/active) |
| `COMMUNITY` | the four community types `['people','settlement','faction','cult']` (`TOPLULUK = ['halk','yerlesim','hizip','tarikat']`) |
| `ENGINE.k` | tunable in rule group `DERIN` (also aliased as `MOTOR`) |
| `REL.k` | tunable in rule group `DERIN_ILISKI` |
| `CAMP.k` | tunable in rule group `DERIN_SEFER` |
| `SOC.k` | tunable in rule group `DERIN_TOPLUM` |
| `LIFE.k` | tunable in rule group `DERIN_YASAM` |
| `LIMITS.k` | hard stat limits from `rules.js` group `SINIR`: `population_floor`=10 (`nufus_taban`), `town_population_cap`=2,000,000 (`kent_nufus_tavan`), `population_cap`=50,000,000 (`nufus_tavan`), `followers_cap`=10,000,000 (`murit_tavan`), `army_size_cap`=10,000,000 (`ordu_tavan`), `hp_cap`=300 (`can_tavan`) |
| `note(text, ids[], sonId?)` | engine note callback (`not`). In `sim.js` it (a) pushes the text to the notes list sent to Fate (Kader), (b) queues a chronicle line with linked entity ids and optional son id; queued lines are written at epoch end and lines with an identical template (after removing names/numbers) beyond a fold threshold are folded into one summary line. |
| `notes.push` + `chronicle(...)` | epoch-transition functions (`iklimGecis`, `tanriOlumu`, `dirilt`, `tanrilarinKaderi`, `dunyaYasi`) write directly with `addKronik(epoch, sonId, kind, text, ids)` and push to the `notlar` array. |
| `Y` | per-world law resolver from `sim.js` (`yasaCozucu`). `Y.has(lawKey, entity?)` = is that law active in the entity's world. Laws referenced here: `war_ban` (`savas_yasagi`), `fertility` (`bereket`). |
| `H` | helper bundle passed by `sim.js`: `militaryPower(v)` (`askeriGuc`), `allyPower(v)` (`muttefikGucu`), `patronBonus(v) → {h: son|null, b: number}` (`hamiBonus`), `weaponPower(v, mult=1)` (`silahGucu`), `afterDeath` (`olumSonrasi`), `heroicDeed(hero, creature, epoch, note, context)` (`kahramanlik`). These are specified in the `sim.js` spec. |

"Epoch" = *çağ* (one epoch = 50 in-world years, `CAG_YIL`). Every `_chance` tunable is a percent.

---

## 1. Data model touched by this module

### 1.1 Entity (`varliklar`) fields used

| Field (orig) | Meaning |
|---|---|
| `id`, `ad` (name), `tur` (type), `alt_tur` (subtype), `aciklama` (description) | identity |
| `statlar` (stats, JSON) | numeric stats, see 1.3 |
| `guc_seviyesi` (power level) | 1..12 rank of importance |
| `cag` (epoch created) | |
| `konum_id` (location id) | parent place in the location tree |
| `etiketler` (tags, JSON array of strings) | see 1.5 |
| `kaynak` (source) | `'dunya'` = created by the world engine (as opposed to a son/agent/creator) |
| `bekliyor` (pending) | `1` = waiting for Fate (Kader) to name/judge it; all engine records are created pending |
| `unvan` (title) | e.g. role title of a born mortal |
| `durum` (status) | `kanon` canon/alive · `olu` dead · `yok_edildi` destroyed · `reddedildi` rejected · `gerceklesti` fulfilled |
| `olum_cag` (death epoch) | |
| `kader_notu` (fate note) | free-text death/fate log |
| `dunya_id` (world id) | multi-world cosmos; `null` treated as world 1 everywhere (`?? 1`) |
| `toplum` (society JSON) | only for peoples and settlements, see 1.4 |
| `yaratan_id` (creator son id) | |
| `harita_xy` | cached map position |

Entity types referenced (`tur`): `olumlu` mortal · `yerlesim` settlement · `halk` people · `hizip` faction · `tarikat` cult · `tur` species · `olay` event · `yapit` work (building/monument) · `esya` item · `dil` language · `efsane` legend · `gelenek` tradition · `ruh` spirit · `ordu` army · `kaynak` resource · `teknoloji` knowledge · `yer` place · `kehanet` prophecy · `gok` celestial body · `dis` outer being · `bolge` region · `kanun` law code (has `adalet` justice stat) · `eser` artwork/text · `yasa` law.

`TUR_AD` (type → display noun, used in self-introducing descriptions): mortal→"mortal", settlement→"settlement", people→"people", faction→"faction", cult→"cult", species→"species of creature", event→"event", work→"work", item→"item", language→"language", legend→"legend", tradition→"tradition", spirit→"spirit", army→"army", resource→"resource", knowledge→"knowledge", place→"place", prophecy→"prophecy", celestial→"celestial body", outer→"outer being".

### 1.2 Bond (`baglar`) — directed edge

Columns: `id, kaynak_tip` (source kind: `v` entity, `o` son/god, `t` the creator, `y` foreign god), `kaynak_id, hedef_tip, hedef_id, tur` (type), `aciklama` (description), `cag` (epoch made), `aktif` (1 active / 0 closed; closed bonds are kept as history).

Bond types used here (orig → English, direction):

| Orig | English | Direction / meaning |
|---|---|---|
| `yasar` | lives_in | entity → place/home |
| `korur` | protects / belongs_to | mortal/army → community it serves |
| `tapar` | worships | entity → son (`o`), creator (`t`) or foreign god |
| `konusur` | speaks | community/mortal → language |
| `yonetir` | rules | ruler → ruled community |
| `komutan` | commands | mortal → army |
| `sahip` | owns | owner → item/resource/work |
| `bilir` | knows | community → knowledge (`teknoloji`) |
| `sever` | loves | mortal → mortal (marriage) |
| `yoldas` | companion | mortal ↔ mortal (undirected meaning) |
| `esir` | holds_prisoner | captor (community) → prisoner (mortal) |
| `casus` | spies_on | faction → target community (spy network) |
| `pesinde` | pursues (quest) | hero → quest target |
| `muttefik` | ally | community ↔ community |
| `ticaret` | trade | community ↔ community (trade route) |
| `dusman` | enemy | community/mortal ↔ community/mortal (hostility; not the same as an ongoing war) |
| `harac_oder` | pays_tribute | payer → receiver |
| `ateskes` | truce | community ↔ community, time-limited |
| `hasim` | nemesis | mortal ↔ mortal |
| `ustasi` | apprentice_of | apprentice → master |
| `uyesi` | member_of | |
| `soyundan` | descends_from | child → parent/origin |
| `oldurdu` | killed | killer → victim |
| `anlatir` | tells_of | legend/corpse/text → subject |
| `uretti` | produced | community → item |
| `insa_etti` | built | community → work |
| `gocetti` | migrated_to | source → destination |
| `icinde` | inside | entity → its location (structural) |
| `parcasi` | part_of | army/battle → war |
| `taraf` | side | war/battle → participant (description: `taraf` side, `galip` victor, `mağlup` loser, `komutan` commander, `düelloya tutuştu` dueled, `galip (<result>)`) |
| `neden_oldu` | caused | event → affected entity |
| `kaynagi` | sourced_from | manifestation → legend |
| `kutlar` | celebrates | community/mortal → tradition |
| `ruhu_indi` | soul_descended | dead mortal → afterlife place (historic) |
| `ilgili` | related | generic |
| (also closed on death) `evcil` tamed, `avlar` hunts, `kaptan` captain, `yolcusu` passenger | | |

Helper `bagVar(a, b, type)` (world.js) = active `v→v` bond of that type in **either direction**.
`hami(v)` (world.js) = patron god: the son targeted by v's first active `tapar` bond, else `v.yaratan_id`'s son, else null. **Note:** falls back to the creator son even without a worship bond.

### 1.3 Stats (`statlar`) keys used

Communities: `nufus` population · `refah` prosperity (0–100) · `servet` wealth · `guc` power · `nufuz` influence · `savunma` defence · `inanc` faith/piety · `murit` followers (cult) · `bagnazlik` zeal (cult) · `etki` influence (cult) · `savascilik` martiality (people) · `zanaat` craft · `buyu` magic · `adanmislik` devotion (resurrection cult).
Mortals: `can` HP · `guc` power · `ceviklik` agility · `akil` intellect · `karizma` charisma · `yas` age (years) · `omur` lifespan (years).
Species: `can, guc, ceviklik, zeka` intelligence, `tehlike` danger.
Army (`ordu`): `buyukluk` size (soldiers), `moral` morale, `techizat` equipment, `deneyim` experience.
War event (`olay` / `savaş`): `siddet` violence, `skor` score (positive favours side A), `muharebe` battle count, `baslangic` start epoch, `son_carpisma` last clash epoch, `bitis` end epoch.
Places: `bereket` fertility, `tehlike`, `gizem` mystery.
Works: `ihtisam` splendour, `saglamlik` durability, `islev` function.
Items: `hasar` damage, `koruma` protection, `kudret` might, `lanet` curse. Resources: `bolluk` abundance, `deger` value, `kudret`.
Knowledge / legend / tradition / language: `yayginlik` spread (0–100); language also `karmasiklik` complexity, `kutsallik` sacredness. Spirit: `huzursuzluk` unrest.

### 1.4 Society JSON (`toplum`) — peoples and settlements only

```
society = {
  k: { farmer, artisan, merchant, priest, warrior, scribe }      // class shares %, sum 100, 1 decimal (ciftci, zanaatkar, tuccar, rahip, savasci, katip)
  m: { farmer, artisan, merchant, priest, warrior, scribe }      // satisfaction 0..100 (memnuniyet)
  e: { food, ore, goods, price: { food, ore, goods } }           // stores and prices % (erzak, maden, mal, fiyat)
}
```
Default (`toplumOf` when missing/incomplete): `k` = base class shares (SOC.class_*), `m` all = SOC.initial_satisfaction, `e` = {food: SOC.initial_food, ore: SOC.initial_ore, goods: SOC.initial_goods, price all 100}. **Note:** factions and cults never have a society, so every call of `toplumOf` on them returns the defaults (e.g. scribe share 5%).

Class display names (`SINIFLAR`, rules.js): farmer "Farmers"/"Farmer", artisan "Artisans"/"Artisan", merchant "Merchants"/"Merchant", priest "Priests"/"Priest", warrior "Warriors"/"Warrior", scribe "Scribes"/"Scribe".

### 1.5 Tags used (orig → English)

| Tag | Meaning |
|---|---|
| `suruyor` / `bitti` / `sonuc:<r>` | war ongoing / ended / result (results: `barış` peace, `yorgunluk barışı` exhaustion peace, `yorgunluk` exhaustion, `aynı savaşın cephesi` front of same war, `taraf kalmadı` no side left, `fetih` conquest, `haraç` tribute, `beyaz barış` white peace) |
| `taraf:<id>` | war/army side |
| `savas:<id>` | army belongs to war |
| `esir` | mortal is a prisoner |
| `seçilmiş` | the Chosen (hero) |
| `iplik:<id>` | hero pursuing story thread |
| `harika` | work is a wonder |
| `kayıp` | knowledge is lost |
| `harabe` / `yeniden kuruldu` / `boşluk` | ruin / rebuilt / void (excluded from resettling) |
| `tanrısız` | godless (apostate) |
| `tanrı arayışı` | seeking a god |
| `senkretik:<sonId>` | syncretic secondary worship |
| `tanrı cesedi`, `ceset:<sonId>`, `boş mezar` | god corpse / empty tomb |
| `dirilis:<sonId>`, `diriliş tamam` | resurrection cult / resurrection completed |
| `yönetici` | ruler mortal |
| `dilden-ad` | name generated from a language |
| `halk oldu` | species already became a people |
| `yazi:<type>` | language has a script (`alfabe` alphabet, `hece` syllabary, `resim` pictographic, `dugum` knot, `oyma` notch) |
| `ölü dil`, `çözülebilir` | dead language / decipherable |
| `tezahür etti`, `inançtan doğdu` | legend manifested / born of belief |
| `bozulmuş bellek`, `masal` | corrupted memory (event-legend) / fairy tale |
| `yerli` | native (spontaneous) |
| `ilkel` | primitive language |
| `sinif:<class>` | class uprising faction |
| `hizip:<kind>:<communityId>` | faction kind marker (`lonca` guild, `meclis` council, `birlik` brotherhood) |
| `altın çağ` | in golden age |
| `lanetli` | cursed |
| `ölüler diyarına geçti` | spirit crossed to the land of the dead |
| `afet` | event is a disaster |

### 1.6 Other tables

- **`topluluk_iliski`** (community relation): `a < b` (ordered pair, CHECK), `deger` value −100…+100, `gecmis` history JSON `[{cag, olay, d}]` (last REL.relation_history_length entries), `kan_davasi` epoch the blood feud started (NULL = none).
- **`iliskiler`** (son–son relation, −100…+100) — only read/modified via world.js `iliskiDegistir`.
- **`iplikler`** (story threads): `cag, metin, ilgili` (JSON ids), `durum` `acik`/`kapandi`.
- **`sozluk`** (lexicon): `dil_id, kelime, anlam, tur, koken` (etymology), `ekleyen_tip, ekleyen_id, cag`.
- **`dunyalar`** (worlds): `id, ad, tur` (world type: `olagan` ordinary, `okyanus`, `kum`, `buz`, `lav`, `olu` dead-world …), `iklim` JSON `{evre, kalan, bas, tanri?}`, `kesif` (`unutulmus` = forgotten, skipped everywhere), `olusturma_cag`, `koruyucu_ogul` (guardian son).
- **`dunya`** (singleton row id=1): `cag, yil, ad, tanri_adi` (creator's name), `iklim` (copy of first world's climate), `tanri_oz` (creator essence), `kiyamet` (doom clock).
- **`ogullar`** (sons/gods): `durum` (`aktif`, `olu`, `surgun` exiled), `olum_cag, ceset_id, solus` (fading counter), `varlik` existence, `oz` essence, `un` fame, `xp`, `can`, `statlar`, `tutku.ofke` (passion: anger), `asi` (rebel flag), `aktif_dunya`, `capa_id` (anchor entity), `alan1/alan2` (domains), `unvan`.
- **`rotalar`** (routes): `kontrol_id` controller; **`yolculuklar`** (journeys): `durum='vardi'` arrived.

---

## 2. Engine call order (where each mechanic runs)

### 2.1 Per-epoch world engine (`sim.js motorAdimlari(cag)`), relevant steps in order

1. `olulerinBaglari(cag, note)` — close bonds of the dead (§4.3).
2. `ateskesleriBitir(cag)` — expire truces (§5.1).
3. For up to `DE.dil_inanc_tavan` canon communities lacking a language or a faith (and not tagged godless / planet-worship / god-seeking): `dilVeInancBagla(v, cag, note)` (§24).
4. (sim.js) gods' feuds leak to mortals → `savasIlan` calls.
5. `diplomasi(cag, note)` (§8).
6. `seferler(cag, note, Y, H)` (§10–12).
7. … (journeys, other sim steps) … `kulturAlisverisi(cag, note)` (§32).
8. … famine migration uses `harabeyeKur` (§25) and `ENGINE.famine_migration_share`; then `multeciler(cag, note)` (§26).
9. (sim.js) poverty uprisings use `buyuklukEsigi` and `isyanHedefi`.
10. `ruhlarDiner(cag, note)` (§27).
11. … `dilOlumu(cag, note)` (§28).
12. `toplumEkonomi(cag, note, Y)` (§13) → `kahramanlar(cag, note, H)` (§14) → `dogumlar(cag, note)` (§21) → `hizipler(cag, note)` (§30) → `yapitlar(cag, note)` (§29) → `dinYayilimi(cag, note)` (§31) → `yasamTohumu(cag, note)` (§23) → `yazilar(cag, note)` (§22) → `inancVeBellek(cag, note)` (§22b) → `casusluk(cag, note)` (§16) → `harikalar(cag, note)` (§17) → `karanlikCaglar(cag, note)` (§15) → `harabeler(cag, note)` (§18).
13. Mortal ageing/deaths (sim.js), then `olulerinBaglari(cag, note)` again.

### 2.2 Epoch transition (`sim.js gecisAdimlari`)

- `iklimGecis(newEpoch, notes)` early (§19), before population growth.
- `tanrilarinKaderi(newEpoch, notes)` after son essence regeneration (§20).
- `toplulukSavasSayisi()` feeds the doom-clock war term; `dunyaYasi(newEpoch, notes)` returns `{altin, donum}` used as doom-clock relief terms (§33).

---

## 3. Export list and call sites

Exports used **only inside derin.js** (plus tests) are marked *internal*.

| Export | Kind | Called from (outside derin.js) |
|---|---|---|
| `DERIN` / `MOTOR` | rule object (alias) | `sim.js` (`MOTOR.kahraman_yuzde`, `.tarikat_oran`, `.kitlik_goc_pay`, `.ruh_tavan`); `korku.js` (`MOTOR.genc_dunya`); `yaratici.js` re-declares `tanimla('DERIN', {})` to read `savas_tavan` |
| `TOPLULUK` | constant | ekonomi, firsatlar, olum, otesi, oyuncu, seyahat, tanriguc, tools |
| `kanonlar` (re-export of world.js) | canon snapshot | ~20 modules (sim, ekonomi, gok, korku, medeniyet, olum, olumluler, otesi, panteon, seyahat, tanriguc, ufuk, yaratici, yaratik, agents, hedef, epoch, mudahale, firsatlar) |
| `kanonOnbellek` (re-export) | cache toggle | sim.js (engine start/end) |
| `benzersizAdR` | unique name | *internal* (kayitAc), tests |
| `kayitAc` | create engine record | ekonomi, gok, korku, medeniyet, olum, otesi, oyuncu, seyahat, sim (`yerTut`), ufuk, yaratik |
| `oldur` | kill/retire entity | epoch, korku, otesi, sim, tanriguc, yaratik |
| `olumYolu` | death path | *internal* |
| `olumCagiDoldur` | backfill death epoch | otesi.js (afterlife engine) |
| `olulerinBaglari` | dead-bond sweep | sim.js (start & end of engine, single death in `olumluOlur`), onarim.js (open-time repair) |
| `ateskesVar` | truce check | olumluler.js (mortal war tool), tools.js (incite tool) |
| `ateskesleriBitir` | expire truces | sim.js |
| `savastilarMi` | ever fought | *internal* |
| `barisYap` | make peace | gok.js (comet omen peace), onarim.js, oyuncu.js (creator's decree) |
| `savasVeKonumOnarimi` | repair | onarim.js |
| `toplulukSavasSayisi` | hostile pair count | sim.js (doom clock) |
| `surenSavaslar` | ongoing wars | *internal*, tests |
| `surenSavasSayisi` | ongoing war count | yaratici.js (creator mood: anger from wars) |
| `savasAcilabilir` | can open war | *internal*, tests |
| `savasIlan` | declare war | sim.js (god feud, resource rivalry, cult schism, poverty uprising, other), medeniyet.js, olumluler.js, seyahat.js (first-contact invasion) |
| `dinDegistir` | convert | *internal*, tests |
| `etiketEkle` / `etiketSil` | tag add/remove | ~15 modules |
| `mesafe` | tree distance | medeniyet, olumluler, otesi, sim (own copy too), world, yaratik |
| `tIliski` / `tIliskiDegistir` | community relation get/change | firsatlar, medeniyet, olumluler, onarim, otesi, oyuncu, seyahat, tools |
| `kanDavasi`, `kanDavasiVar` | blood feud | *internal* |
| `iliskiEtiketT` (re-export of rules.js) | relation label | rules/world |
| `iliskiListesi` | relation list | server.js entity detail API (`iliskiler` field) |
| `tarafOf` | mortal's side | *internal*, tests |
| `iliskiSonmesi` | mean reversion | *internal* (diplomasi), tests |
| `diplomasi` | diplomacy step | sim.js |
| `seferBitir` | end campaign | oyuncu.js (creator decree peace) |
| `tavaniAsanSavaslar` | enforce war caps | *internal*, tests |
| `isyanHedefi` | uprising target | sim.js |
| `seferler` | campaign step | sim.js |
| `toplumOf` | society read | server.js (entity detail), firsatlar, korku, olumluler, sim (`askeriGuc`, famine), ufuk |
| `toplumEkonomi` | economy step | sim.js |
| `kahramanlar` | heroes step | sim.js |
| `karanlikCaglar` | dark ages | sim.js |
| `casusluk` | espionage | sim.js |
| `harikalar` | wonders | sim.js |
| `harabeler` | abandonment | sim.js |
| `iklimGecis` | climate transition | sim.js |
| `iklimOf` | read climate | server.js (world + per-world climate), kodeks.js, sim.js (plague multiplier) |
| `tanriOlumu` | god death | epoch.js (creator kills son), olum.js (`aeronOgluOldurur`), olumluler.js (mortal kills a god), tanriguc.js (creator devours son) |
| `dirilt` | resurrect god | epoch.js (creator resurrects) |
| `solusDurumu` | fading status | server.js (`solus` in world state) |
| `tanrilarinKaderi` | gods' fate | sim.js |
| `kisiAdi` | person name | epoch.js (star naming fallback), sim.js (heir names) |
| `yoneticiVar`, `tekYonetim` | single-ruler rule | *internal* |
| `etnogenezOnar` | repair | onarim.js |
| `dogumlar` | births | sim.js |
| `yazilar` | writing | sim.js |
| `inancVeBellek` | belief & memory | sim.js |
| `yasamTohumu` | life seeding | sim.js |
| `buyuklukEsigi` | relative threshold | sim.js (monster, cult schism, hero, plague, uprising thresholds) |
| `dilVeInancBagla` | first language & faith | sim.js, seyahat.js (colonists), ufuk.js (explorers) |
| `harabeyeKur` | resettle ruin | sim.js (famine migration) |
| `multeciler` | refugees | sim.js |
| `ruhlarDiner` | spirits rest | sim.js |
| `dilOlumu` | language death | sim.js |
| `yapitlar` | engine works | sim.js |
| `hizipler` | factions | sim.js |
| `baskinlikCarpani` | dominance multiplier | *internal*, tests |
| `dinYayilimi` | religion spread | sim.js |
| `kulturTemasi` | one contact | seyahat.js (first contact, both directions, `ilk: true`) |
| `kulturAlisverisi` | trade-route culture | sim.js |
| `dunyaYasi` | world age | sim.js |

Rule groups shared with other modules (read live via `tanimla('<GROUP>', {})`): `DERIN_YASAM` is read by firsatlar.js (`dirilis_adanmislik`), tools.js (`dirilis_adanmislik`), bosdunya.js (`yasam_bereket` = habitability threshold), olum.js (`dirilis_tarikat_guc/_bagnazlik/_etki`, `adanmislik_tavan`, `dirilis_adanmislik`), mudahale.js, oyuncu.js (`adanmislik_tavan`). **New design:** expose rule groups through one typed settings service instead of re-declaring empty groups.

### 3.1 Imports (dependencies of this module)

`db.q` · rules.js: `clamp, d, IKLIM, SINIFLAR, canMax, ozMax, iliskiEtiketT, ROMA, iklimAgirligi, SINIR` · world.js: `getWorld, getSon, allSons, getVarlik, kanonlar, kanonOnbellek, saveSon, saveStat, addKronik, addBag, bagVar, hami, iliskiDegistir, nameOf, benzersizAd, konusulanDil, isimAlinmis, sonuYaz, konumBaginiTazele` · public/dil.js: `ekDuzelt, cogulIyelik` (LANGUAGE-SPECIFIC) · mudahale.js: `bilir, bildikleri, ogret, dalOf` (knowledge: `bilir(id, branch)` = knows any canon knowledge of that branch; branches used: `tarim` agriculture, `ticaret` trade, `yazi` writing, `metalurji` metallurgy, `denizcilik` seafaring, `savas` warcraft, `mimarlik` architecture; `ogret(v, tech, epoch, desc)` adds `bilir` bond if absent and raises the tech's spread) · olumluler.js: `ustBolge` (top-level region of an entity) · sim.js: `olumluOlur` (mortal death path), `refahEkle` (prosperity add with diminishing returns: positive gains above `DE.refah_hedef` are scaled by `(100−refah)/(100−target)`; losses apply fully) · olum.js: `diriliseKalan(son, epoch)` (epochs until resurrection allowed: `max(0, death_epoch + OLUM.dirilis_en_az_cag − epoch)`) · harita.js: `haritaHesapla()` (map; `.bilgi[regionId] = {komsular: ids, kiyi: coastal bool, yukseklik: 'dağlık'|'engebeli'|…}`) · dilmotoru.js: `dildenAd(source, seed, kind)` (name from source's language; kinds `kisi` person, `yer` place, `halk` people, `ordu` army), `adUret(langId, seed, kind)`, `hecele(word)` (syllabify) · yaratici.js: `yaraticiyaTapin(v, offering, epoch)` (worship the creator: bond `v → t:1 tapar`, removes `tanrısız`) · otesi.js: `kozmikMahkeme(traitor, victim, epoch)` (cosmic court: tags traitor `yeminbozan` oath-breaker + `lanetli` cursed, neighbours' relations drop) · denge.js: `tanimla` · bosdunya.js: `BOS.yerli_guvence`, `bosDunyalar(epoch)` (`[{id, bos_cag}]` epochs a world has been without a people).

---

## 4. Record creation and death primitives

### 4.1 `benzersizAdR(name)` — unique name with Roman numerals
1. `root = ekDuzelt(trim(name))` (Turkish suffix fixer; LANGUAGE-SPECIFIC → in English just trim/normalise). If empty → world.js `benzersizAd(name)`.
2. `core = root.length > 2 ? root[1:] : root` (drop first letter so the LIKE search is case-insensitive on the initial).
3. `taken` = lowercase set of names of all entities with status ≠ rejected **and** all sons whose name contains `core`.
4. If `root` not in `taken` and `isimAlinmis(root)` is false (cosmos-wide: stars, worlds, foreign gods) → return `root`.
5. Else for `i = 2..3999`: candidate `"<root> <ROMAN(i)>"` (II, III, … never Arabic digits); return the first free one.
6. Fallback: `benzersizAd(root)`.

### 4.2 `kayitAc({type, subtype, name, description, stats, locationId, epoch, power = REL.record_power_level, tags = [], title = null})` → id
1. `name = benzersizAdR(name)`.
2. Self-introduction (`kendiniAnlat`): if the description starts with the marker `"[Dünya motoru]"` ("[World engine]"), strip the marker and a leading `"<name>:"`, then rebuild as: `"[World engine] <name>, a <subtype or TUR_AD[type]> in <location name>. <body>"` (the "in <location>" part only if a location is given). Otherwise unchanged.
3. INSERT entity: `source='dunya'` (engine), `pending=1` (Fate will judge/name), stats JSON, tags JSON, title.
4. If `locationId` and ≠ id: add bond `id → location 'icinde'` (inside).
5. Return id.

### 4.3 Death
**`oldur(id, epoch, note = null, {status='olu', append=false, closeBonds=false})`**
1. If `note`: `sonuYaz(id, note)` (append the sentence to the description once).
2. UPDATE status, `olum_cag = epoch`; fate note: if `append` → concatenate `note`, else replace with `note` when given (keep old otherwise).
3. If `closeBonds` → `olulerinBaglari(epoch, noop, id)`.

**`olumYolu(x, epoch, cause, killer = null, bondDesc = null)`** — if `x` is a mortal and `sim.olumluOlur(x, epoch, noop, {sebep: cause, katil: killer})` returns truthy, done (that path handles heir, inheritance, soul descent, killer bond, death year). Otherwise `oldur(x.id, epoch, "Epoch <n>: <cause>.")` and, if `killer`, bond `killer → x 'oldurdu'` (killed) with `bondDesc || cause`. Caller writes the chronicle text.

**`olumCagiDoldur(epoch, singleId = null)`** — backfill: for dead/destroyed entities (or the single id) with NULL `olum_cag`: parse all `"Çağ N"` occurrences in the fate note, keep those with `created ≤ N ≤ epoch`, use the last; else `epoch` if `created ≥ epoch−1`, otherwise `created`. *LANGUAGE-SPECIFIC & legacy: in the new design death epoch is always stored at death; drop this.*

**`olulerinBaglari(epoch, note = noop, singleId = null)`** — dead-bond sweep (whole world, or one entity). Returns `{closed, transferred}`.
1. `olumCagiDoldur(epoch, singleId)`.
2. Active `yasar` bonds of dead entities with description `'ruhu oraya indi'` ("their soul descended there") become type `ruhu_indi` (historic trace, not "lives in").
3. **Source-side state bonds** — for active bonds from a dead/destroyed entity of types `SOURCE_STATE = [lives_in, protects, worships, speaks, rules, commands, owns, knows, loves, companion, holds_prisoner, spies_on, pursues, tamed, ally, trade, enemy, pays_tribute, truce, hunts, captain, passenger, nemesis, apprentice_of, member_of]` (ordered by id):
   - deactivate;
   - if type ∈ {owns, rules} and target is a canon entity: heir = `mirasci(dead)` (memoised per dead); skip if no heir, heir is the target, heir already has the same active bond to the target, or (rules) the target already has another active ruler; else add bond `heir → target <same type>` described "inherited from <dead name>"; `transferred++`.
4. **Target-side state bonds** — deactivate active bonds pointing to a dead entity of types `TARGET_STATE = [rules, protects, commands, owns, worships, ally, trade, enemy, pays_tribute, loves, companion, spies_on, tamed, speaks, truce, captain, passenger, hunts, pursues, holds_prisoner, nemesis, apprentice_of, member_of]`.
5. Routes (`rotalar`) controlled by a dead entity → `mirasci(dead)` if it is a canon community, else NULL.
6. Historic bonds (descends_from, killed, tells_of, produced, built, migrated_to) are untouched.
7. If whole-world sweep and `transferred > 0`: note "The dead's <n> properties and rulerships passed to their heirs." (no ids). Bond counts are never chronicled.

`mirasci(dead)` (heir): (1) newest canon descendant (entity with `soyundan → dead`) of type mortal or community; (2) the dead's location if it is a canon community; (3) among (a) the community the dead descends from, (b) the dead's rulers, (c) communities the dead protected — first canon community; else null.

---

## 5. Truce and war-cap primitives

### 5.1 Truce
- `ateskesVar(a, b, epoch)` = an active `truce` bond between a and b (either direction) with `bond.epoch > epoch − ENGINE.truce_duration`.
- `ateskesleriBitir(epoch)`: deactivate all active truces with `bond.epoch ≤ epoch − ENGINE.truce_duration`.
- `savastilarMi(a, b)` = any war event (type event, subtype `savaş`, any status) tagged both `taraf:a` and `taraf:b`.

### 5.2 `barisYap(a, b, epoch, reason = 'barış', {truce = false})` → bool
1. Deactivate all enemy bonds between a and b (both directions).
2. If `!truce && ENGINE.truce_without_war == 0 && !savastilarMi(a, b)` → return false (grudge closed silently, no truce).
3. If no active truce: add bond `a → b 'ateskes'` described `"<reason>; until Epoch <epoch + truce_duration>"`. Return true.
Design note: earlier every faded grudge wrote a 3-epoch truce that locked dozens of pairs; now only pairs that actually fought (or explicit creator decrees with `truce: true`) get truces.

### 5.3 `savasVeKonumOnarimi(epoch)` (open-time repair, idempotent)
- If `truce_without_war == 0`: deactivate active truces between pairs that never fought.
- For every canon/fulfilled entity with a canon/fulfilled location ≠ itself and no active `inside` bond to it → add `inside` bond.
- Returns `{truces_closed, inside_added}`.

### 5.4 War counts
- `toplulukSavasSayisi()` = number of **distinct unordered pairs** of canon communities with an active enemy bond (hostility pairs, not wars).
- `surenSavaslar()` = war events tagged `suruyor` (ordered by id) → `{id, sides: [ids from taraf: tags]}`, keeping only those with ≥2 sides, all canon.
- `surenSavasSayisi(sideId = null)` = count of those (optionally involving `sideId`).

### 5.5 `savasAcilabilir(a, b, epoch, {cap = true})` — can a new war open?
False if: either not canon, or same entity; different worlds and **no arrived journey** (`yolculuklar.durum='vardi'`) on a route between the two worlds; already enemies; active truce; a rules or pays_tribute bond between them (either direction); `cap` and both are communities and `surenSavasSayisi() ≥ ENGINE.world_war_cap`. Else true.

### 5.6 `savasIlan(a, b, description, epoch, opts)` → bool
If `savasAcilabilir(a, b, epoch, opts)`: deactivate ally and trade bonds between them, add bond `a → b 'dusman'` (enemy) with the description, return true. **Does not check the per-community war cap** — callers must.

### 5.7 `dinDegistir(v, newGod, epoch, reason, {syncretic = false})` → bool (religion change primitive)
False if v not canon, no god or god dead, or `hami(v)` already is `newGod`. If syncretic and v has an old god → only add tag `senkretik:<newGod.id>` (no bond!) and return true. Else deactivate all v's worship bonds to sons, add `v → newGod 'tapar'` with reason, remove tags `tanrısız` / `tanrı arayışı`. Return true.

### 5.8 Tags
`etiketEkle(v, ...tags)` = set-union then persist; `etiketSil(v, filter)` = remove tags equal to `filter` or for which `filter(tag)` is true, persist. Both mutate the in-memory object.

### 5.9 Distance and neighbourhood
- `atalar(v)` = chain of location ancestors (max 8).
- `mesafe(a, b)` = for the chains `[a, ...ancestors(a)]`, `[b, ...ancestors(b)]`, the first common element at indices i, j → `i + j`; else 99.
- `komsuBaglami()` = context `{info: haritaHesapla().bilgi (or {}), top(v): memoised ustBolge(v)}` — compute once per pass.
- `komsuMu(a, b, ctx)` (are neighbours): if either has no top region → `mesafe(a, b) ≤ REL.neighbour_distance`; same top region → true; else `top(b).id ∈ info[top(a).id].komsular`.
- `bagKumesi(types)` = per-pass snapshot of active v–v bonds of those types; `.any(a,b,type)` undirected, `.directed(a,b,type)`.

---

## 6. Community relations

Pair key: `(min(a,b), max(a,b))`.

### 6.1 Initial relation (`baslangicIliski(a, b)`) — computed lazily on first read
```
x = 0
if hami(A) and hami(B): x += (same god ? REL.initial_shared_god : -REL.initial_different_god)
if both speak a language and it is the same: x += REL.initial_shared_language
if enemy bond:        x -= REL.initial_enemy
if ally bond:         x += REL.initial_ally
if trade bond:        x += REL.initial_trade
if pays_tribute bond: x -= REL.initial_tribute
return clampi(x, -100, 100)
```

### 6.2 API
- `tIliski(a, b)`: `a == b` → 100. Read the row; if missing, compute initial, INSERT, return it.
- `tIliskiDegistir(a, b, delta, event = null, epoch = current)`: no-op if `a == b` or `delta == 0`. Ensure row. If `event` given: push `{epoch, event, d: round(delta)}` to history, keep the last `REL.relation_history_length`. `value = clampi(old + delta, −100, 100)`.
- `kanDavasi(a, b, epoch, reason)` (blood feud): ensure row; `blood_feud_epoch = COALESCE(existing, epoch)`; `tIliskiDegistir(a, b, −REL.blood_feud_penalty, reason || 'blood feud', epoch)`.
- `kanDavasiVar(a, b)` = row has non-null blood-feud epoch.
- `iliskiListesi(id, n = 6)`: rows involving id ordered by `|value|` desc, limit n → for each canon counterpart `{id, name, type, value, label: iliskiEtiketT(value), blood_feud, history: last 3}`. Server uses `n = SK.iliski_liste`.
- `iliskiEtiketT(v)` (rules.js; thresholds in `KURAL`): ≤ −blood → "blood enemy" (`kan düşmanı`), ≤ −enemy → "enemy", ≤ −cold → "cold", < friend → "neutral", < close → "friend", < sibling → "close friend", else "sworn kin" (`kardeş`).

## 7. Sides of mortals (`tarafOf`, `kahramanlariOf`)
- `tarafOf(h)` (side of): community → itself. Else the first canon community targeted by h's active `protects`, then `rules`, then `descends_from` bonds; else h's location if a canon community; else the first canon **people** whose top region equals h's top region; else null.
- `kahramanlariOf(t)` (heroes of community t) = all canon mortals **not tagged `esir`**, in t's world, whose `tarafOf == t`. Note: this is *all mortals* of the side, not only those passing the hero test (§14).

### 7.1 Mortal grudges forgetting (`olumluKinleri(epoch)`)
If `ENGINE.mortal_grudge_forget_age == 0` → off. For each active enemy bond with bond epoch ≤ `epoch − N` where at least one end is a mortal and both ends are mortal/community: if any other bond (any type, active or not) between the two ends was created after `epoch − N`, keep; otherwise deactivate. Mortal hostilities never turn into wars by themselves.

### 7.2 Mean reversion (community relations) (`iliskiSonmesi()`)
With `E = REL.relation_decay_threshold`, `P = REL.relation_decay_share` (if P = 0 → off). For every relation row with `|value| > E`:
```
if value > E:  value -= round((value - E) * P / 100)
else:          value += round((-E - value) * P / 100)
```
Returns number of changed rows. (Prevents relations sticking at ±100 forever.)

---

## 8. Diplomacy (`diplomasi(epoch, note)`) — once per epoch

Order of operations:

**8.1** `iliskiSonmesi()`.

**8.2** `ts` = canon communities. Counters `declared, peaces, alliances, betrayals, exhaustionPeaces = 0`.

**8.3 Candidates** = active enemy bonds grouped by unordered pair → `{a, b, c = min(bond epoch)}`, **shuffled uniformly**.

**8.4 Grudge pool:**
```
pairs   = toplulukSavasSayisi()
pool    = max(1, round(ENGINE.world_war_cap * ENGINE.grudge_pool_pct / 100))      // default 6*300% = 18
excess  = max(0, pairs - pool)
fadeCap = ENGINE.grudge_fade_cap + round(excess * ENGINE.grudge_overflow_share / 100)
forgetAge = ENGINE.grudge_forget_age > 0
          ? max(ENGINE.grudge_fade_min_age, round(ENGINE.grudge_forget_age * min(1, pool / max(1, pairs))))
          : 0
```

**8.5 Fading grudges** — for each candidate until `faded ≥ fadeCap`:
- skip if `epoch − c < ENGINE.grudge_fade_min_age`; skip unless both are canon communities; skip if an **ongoing war** exists between them.
- `improved = tIliski ≥ ENGINE.grudge_fade_relation`; `forgotten = forgetAge > 0 && epoch − c ≥ forgetAge`. If neither → skip.
- `barisYap(A, B, epoch, improved ? 'grudge faded' : 'grudge forgotten')`; mark candidate faded; `faded++`.
- Note: improved → "The old grudge between A and B has faded; no one remembers why they called each other enemies." forgotten → "The grudge between A and B lasted <n> epochs without a sword drawn and was forgotten; only the elders remember the enmity." ids [A, B].

**8.6** `olumluKinleri(epoch)`.

**8.7 Exhaustion peace of long wars** (any distance) — for each non-faded candidate until `exhaustionPeaces ≥ ENGINE.exhaustion_peace_cap`: both canon communities; requires ongoing war `sv`; `dur = epoch − (sv.start ?? sv.epoch)`; skip if `dur < ENGINE.exhaustion_start`; `chance(min(ENGINE.exhaustion_chance_cap, ENGINE.exhaustion_growth * dur))`; then `barisYap(A, B, 'exhaustion peace')`, `tIliskiDegistir(+REL.exhaustion_peace_relation, 'exhaustion peace')`, `seferBitir(A, B, epoch, 'exhaustion peace', note)` (errors swallowed); note "The <dur>-epoch war between A and B ended in exhaustion." Exhaustion is measured by the war's own age, never by the hostility bond's age.

**8.8 Neighbour pair loop.** Snapshots after 8.5–8.7: neighbour context, bond set of {trade, ally, enemy, pays_tribute}, memoised patron and language per community, set of blood-feud pairs. For every pair `i < j` of `ts` that are neighbours (`komsuMu`):

1. **Drift** (`dlt`):
   - same patron god → `+REL.drift_shared_god`; else if both have gods and either is a cult → `−REL.drift_cult_other_god`;
   - same language → `+REL.drift_shared_language`;
   - trade → `+REL.drift_trade`; ally → `+REL.drift_ally`; enemy → `−REL.drift_enemy`; tribute → `−REL.drift_tribute`; blood feud → `−REL.drift_blood_feud`.
   - if `dlt ≠ 0`: `tIliskiDegistir(a, b, dlt)` (no history entry).
2. `r = tIliski(a, b)`; `enemy`, `ally` from the snapshot.
3. If enemy: `sv = ongoing war`; `dur = sv ? epoch − sv.start : 0`; `tired = sv && dur ≥ REL.neighbour_exhaustion_start && chance(min(REL.neighbour_exhaustion_cap, REL.neighbour_exhaustion_growth * dur))`.
4. Exactly one of (if/else-if chain):
   - **a. War declaration**: `!enemy && r ≤ ENGINE.grudge_threshold && declared < ENGINE.war_declaration_cap && ongoingWars(a) < ENGINE.community_war_cap && ongoingWars(b) < cap && chance(ENGINE.war_declaration_chance) && savasIlan(a, b, bloodFeud ? 'blood feud turned to war' : 'accumulated grudge')` → `declared++`; note "The grudge that had built up for years between A and B turned into war<; the blood feud is now a campaign>."
   - **b. Peace**: `enemy && ((r ≥ ENGINE.peace_threshold && chance(ENGINE.peace_chance)) || tired) && peaces < ENGINE.peace_cap` → `barisYap(a, b, 'peace')`, `+REL.peace_relation` ('peace'), `seferBitir(a, b, 'peace')`; note "A and B laid down arms; <envoys swore a peace oath | worn out by <dur> epochs of war the two sides made a truce>."
   - **c. Alliance**: `!enemy && !ally && r ≥ ENGINE.alliance_threshold && alliances < ENGINE.alliance_cap && chance(ENGINE.alliance_chance)`:
     - `marriage` = a has a mortal (from `kahramanlariOf`) with `age ≥ REL.marriage_min_age` (unknown age = `REL.default_hero_age`) AND b has one AND `chance(ENGINE.marriage_alliance_chance)`.
     - bond `a → b 'muttefik'` described `marriage ? 'marriage alliance' : 'oath of friendship'`; `alliances++`.
     - marriage: x = first eligible of a, y = first of b; if both and no `loves` bond → bond `x → y 'sever'` ('marriage alliance'); `+REL.marriage_relation` ('marriage'); note "A and B were bound by a marriage<: X married Y>." ids [a, b, x, y]. Else note "A and B became allies by an oath of friendship."
   - **d. Betrayal**: `ally && r < 0 && betrayals < REL.betrayal_cap && chance(ENGINE.betrayal_chance)`:
     - deactivate ally bonds both ways;
     - traitor = side with higher `(influence ?? power ?? REL.betrayal_default_power)`, ties → a; victim = other;
     - `−REL.betrayal_relation` ('betrayal'); `betrayals++`;
     - `chance(ENGINE.betrayal_war_chance)` → `savasIlan(traitor, victim, 'betrayal')`;
     - note "<traitor> stabbed its ally <victim> in the back; the oath was broken.";
     - if the cosmos has ≥ 2 worlds → `kozmikMahkeme(traitor, victim, epoch)` (cosmic court, otesi.js; errors swallowed).

---

## 9. Campaign helpers

- `mevcutSavas(a, b)` = first ongoing war event tagged `taraf:a` and `taraf:b`.
- `orduOf(t, war)` = canon army tagged `taraf:t` and `savas:war`.
- **`askerSayisi(t)`** (soldiers):
  - cult: `round((followers || CAMP.cult_default_followers) * CAMP.cult_soldier_share / 100)`;
  - faction: `round((power || CAMP.faction_default_power) * CAMP.faction_soldiers_per_power + (wealth || CAMP.faction_default_wealth) * CAMP.faction_soldiers_per_wealth)`;
  - people/settlement: `round((population || CAMP.default_population) * max(CAMP.min_soldier_share/100, warriorShare/100))`, warriorShare = society warrior class share or `SOC.class_warrior`.
  - (`||` means 0 is treated as unknown.)
- **`orduKur(t, war, epoch, weaponPower)`** (raise army):
  - commander = mortal of `kahramanlariOf(t)` with max `power + charisma`.
  - record type army, subtype `cult → 'holy guard'` (`kutsal muhafız`), `faction → 'mercenary army'` (`paralı ordu`), else `'people's army'` (`halk ordusu`); name `"<dildenAd(t, '<t>:<war>:ordu', 'army') || t.name> Army"`; power `clampi(t.power, CAMP.army_power_min, CAMP.army_power_max)`; location t if settlement else t's location;
  - stats: `size = clampi(askerSayisi(t), CAMP.army_min_size, LIMITS.army_size_cap)`; `morale = clampi(CAMP.army_morale_base + d(CAMP.army_morale_die) + (cult ? round((zeal || CAMP.cult_default_zeal)/CAMP.army_morale_zeal_divisor) : 0), 0, 100)`; `equipment = clampi(CAMP.army_equipment_base + weaponPower(t)*CAMP.army_equipment_weapon_mult + (knows metallurgy ? CAMP.army_equipment_metallurgy : 0), 0, 100)`; `experience = knows warcraft ? CAMP.army_experience_warcraft : CAMP.army_experience_base`;
  - tags `taraf:t`, `savas:war`; description "[World engine] <t> raised an army of <n> for <war><; <commander> leads it>."
  - bonds: army → t `protects`; army → war `part_of`; if commander: commander → army `commands`, war → commander `side` ('commander').
- `komutanOf(army)` = canon source of an active `commands` bond to the army.
- **`savasKapat(war, epoch, result)`**: remove tag `suruyor`, add `bitti` and `sonuc:<result>`; `war.end = epoch`; every canon army tagged `savas:war` → `oldur(army, epoch, "Epoch <n>: disbanded when <war> ended (<result>).", {closeBonds: true})`.
- **`seferBitir(a, b, epoch, result, note, victor = null, loser = null)`**: if an ongoing war exists → `savasKapat`; if victor and loser → bond war → victor `side` described `"victor (<result>)"`.
- `sonCarpisma(war)` (last clash epoch) = `war.last_clash ?? max(epoch of bonds: battle-event part_of war, or war side 'loser') ?? war.start ?? war.epoch`.

### 9.1 `tavaniAsanSavaslar(epoch, note)` — enforce war caps
1. `open` = ongoing wars with their last clash, sorted ascending by last clash, then id (quietest first).
2. `close(x)`: `savasKapat(x.war, 'exhaustion')`; `barisYap(A, B, 'exhaustion peace')`; `+REL.exhaustion_peace_relation`; note: if `epoch − lastClash ≥ 2` → "The war between A and B, with no sword drawn for <n> epochs, burnt out in exhaustion; the two sides made a truce." else "The war between A and B burnt out in exhaustion as the fronts multiplied; the two sides made a truce." ids [war, A, B].
3. Community cap: loop — among open wars where any side has more than `ENGINE.community_war_cap` open wars, close one whose **both** sides exceed (one closure fixes two excesses), else the first (quietest). Repeat until none.
4. World cap: walk the quietest-first list closing wars while open count > `ENGINE.world_war_cap`.

### 9.2 `bayatSavaslar(epoch, note)` — stale wars (internal)
For ongoing war events by id: sides x, y from tags. If the unordered side pair was already seen → `savasKapat(war, 'front of the same war')`. If both canon and still enemies → keep. Else `savasKapat(war, both canon ? 'peace' : 'no side left')`. Then `tavaniAsanSavaslar`.

### 9.3 Uprisings
- `isyanHedefi(v)` (uprising target) = v's newest active ruler if it is a canon community other than v; else v itself. (The war engine only works between communities; an uprising against a mortal ruler would never clash. Winning against the ruling community conquers it → that is how rulers are overthrown.)
- `isyanMi(x)` = faction whose subtype matches `isyancı|ayaklanma` (rebels|uprising) or has a `sinif:` tag.
- **`isyanYonlendir(epoch, note)`** (redirect): for active enemy bonds where one side is a faction and not both are communities: if one side is an uprising faction `h` and the other side `o` is not a community: deactivate the bond; if both canon: `t` = communities ruled by `o` (excluding h), preferring h's location, then same location as h, then the first; if `t && savasAcilabilir(h, t, {cap: false})` → bond `h → t 'enemy'` with the original description **and the original bond epoch** (start preserved); note "<h> defies <o>'s rule; the revolt is now an open war with <t>."

---

## 10. Campaigns (`seferler(epoch, note, Y, H)`)

1. `bayatSavaslar(epoch, note)`.
2. `isyanYonlendir(epoch, note)`.
3. **No war with subjects**: for every distinct active enemy bond row (a, b) where a rules or pays_tribute bond exists between them and both are canon communities: `barisYap(A, B, 'no war with subjects')`, `seferBitir(A, B, 'peace')`.
4. `haraclar(epoch, note, H)` (§11).
5. Hostile pairs = active enemy bonds whose both ends are canon communities (indexed by snapshot order), unique unordered.
6. `ongoing = surenSavaslar()`; `warPairs` = set of unordered side pairs.
7. Shuffle hostile pairs (random comparator sort — biased), then order **pairs with an ongoing war first**, then the rest.
8. Counters `battles = 0, newWars = 0`. For each pair:
   - break if `battles ≥ ENGINE.battle_cap && newWars ≥ ENGINE.new_war_cap`;
   - refresh a, b; skip unless both canon;
   - `war` = ongoing war if pair ∈ warPairs, else none;
   - skip if (war ? `battles ≥ battle_cap` : `newWars ≥ new_war_cap`);
   - if no war: skip if `ongoing.length ≥ ENGINE.world_war_cap` or either side's ongoing count ≥ `ENGINE.community_war_cap`;
   - `chance(Y.has('war_ban', a) ? ENGINE.battle_chance_under_ban : ENGINE.battle_chance)` (only a's world law is checked) else skip;
   - increment `battles` (existing war) or `newWars`.
   - **New war**: record event subtype `savaş`, name `"War of A and B"` (`A ile B Savaşı`), power `CAMP.war_record_power`, location b if settlement else b's location, stats `{violence: CAMP.war_initial_violence, score: 0, battles: 0, start: epoch}`, tags `['suruyor', 'taraf:a', 'taraf:b']`, description "[World engine] A war began between A and B. Cause: <newest active enemy bond description || 'old hostility'>." Bonds war → a `side` ('side'), war → b `side`. Push to `ongoing`.
   - Armies: `oa = orduOf(a, war) || orduKur(a, war, epoch, H.weaponPower)`, same for b.
   - If new: note "War broke out between A and B: <oa> (<n> soldiers) faces <ob> (<n> soldiers)." ids [war, a, b, oa, ob].
   - If new and `ENGINE.mobilization == 1` → **continue** (first epoch is mobilisation; first clash next epoch).
   - **Battle** — §10.1. Then war end — §10.4.
9. After the loop: `esirler(epoch, note, H)` (§12).

### 10.1 Battle resolution
```
besieged = first of [b, a] that is a settlement with defence >= CAMP.siege_min_defence     // b checked first
besieger = the other side (if besieged)
power(t, army) = H.militaryPower(t) * CAMP.power_community_share/100
               + H.allyPower(t)
               + log10(max(10, army.size)) * CAMP.power_size_mult
               + army.morale / CAMP.power_morale_divisor
               + army.equipment / CAMP.power_equipment_divisor
               + army.experience / CAMP.power_experience_divisor
               + (commander ? (cmd.power + cmd.intellect + cmd.charisma) / CAMP.power_commander_divisor : 0)
               + H.patronBonus(t).b
               + d(CAMP.battle_die) * CAMP.battle_die_mult
pa = power(a, oa); pb = power(b, ob)
(w, l, ow, ol) = pa >= pb ? (a, b, oa, ob) : (b, a, ob, oa)          // ties favour a
gap = |pa - pb|
war.battles += 1; war.last_clash = epoch
war.violence = clampi((war.violence || CAMP.war_initial_violence) + CAMP.violence_growth + round(gap / CAMP.violence_gap_divisor), 0, 100)
war.power_level = clampi(war.power_level + ((war.battles - 1) % CAMP.war_power_interval == 0 ? CAMP.war_power_step : 0), CAMP.war_power_min, CAMP.war_power_max)
place = besieged || (l is settlement ? l : location(l) || topRegion(l))
```

### 10.2 Siege branch (if `besieged`)
```
food = besieged.society.e.food ?? CAMP.siege_default_food
breach = (besieger == w) && chance%( 100 * clampf(gap / CAMP.breach_gap_divisor
                                           + (food < CAMP.breach_starving_food ? CAMP.breach_starving_bonus/100 : 0),
                                           CAMP.breach_min/100, CAMP.breach_max/100) )
if besieged == w:                                   // defenders won
    war.score += (w == a ? +1 : -1)
    ol.morale -= CAMP.siege_repulse_morale          // attacker's army
    summary = "<besieged> repulsed the siege from behind its walls"
elif breach:
    besieged.defence = clampi(defence - CAMP.breach_defence_loss, 0, 100)
    war.score += (besieger == a ? +CAMP.siege_breach_score : -CAMP.siege_breach_score)
    summary = "<besieger> breached the walls of <besieged>"
else:                                               // attacker won, walls hold: starvation round
    besieged.population = clampi((pop || CAMP.siege_default_population) * CAMP.siege_population_remaining/100, LIMITS.population_floor, LIMITS.town_population_cap)
    besieged.prosperity = clampi((prosperity ?? SOC.default_stat) - CAMP.siege_prosperity_loss, 0, 100)
    if society.e exists: food = clampi(food - CAMP.siege_food_loss, 0, SOC.storage_cap) (persist society)
    ol.morale -= CAMP.siege_attacker_morale_loss    // NOTE: ol here is the DEFENDER's army (bug, see §35)
    summary = "<besieger> laid siege to <besieged>; the walls hold but food is running low in the city"
save besieged
```
No score change in the starvation round.

### 10.3 Field battle branch (no siege)
`war.score += (w == a ? 1 : −1) * (gap ≥ CAMP.great_victory_gap ? CAMP.great_victory_score : 1)`; summary "<w> prevailed over <l>".

**Casualties and morale (both branches):**
```
lossL = CAMP.loser_loss_base/100 + min(CAMP.loser_loss_extra_max/100, gap / CAMP.loser_loss_divisor)
lossW = CAMP.winner_loss_base/100 + min(CAMP.winner_loss_extra_max/100, gap / CAMP.winner_loss_divisor)
ol.size = clampi(ol.size * (1 - lossL), 0, LIMITS.army_size_cap); ow.size likewise with lossW
ol.morale = clampi(ol.morale - CAMP.loser_morale_loss - round(gap / CAMP.loser_morale_gap_divisor), 0, 100)
ow.morale += CAMP.winner_morale_gain; ow.experience += CAMP.winner_experience_gain; ol.experience += CAMP.loser_experience_gain  (all clamped 0..100)
if l.population != null: l.population = clampi(pop * (1 - lossL / CAMP.community_loss_divisor), LIMITS.population_floor, LIMITS.population_cap)
if l.followers  != null: l.followers  = clampi(f * (1 - lossL / CAMP.community_loss_divisor), 1, LIMITS.followers_cap)
for k in (prosperity, wealth) if present on l: l[k] -= CAMP.loser_prosperity_loss
if w.wealth != null: w.wealth += CAMP.winner_wealth_gain
tIliskiDegistir(a, b, -CAMP.battle_relation, 'battle')
W = H.patronBonus(w); L = H.patronBonus(l)
if W.h: W.h.fame += CAMP.patron_fame; W.h.xp += CAMP.patron_xp (save son)
if W.h and L.h and different: son relation(W.h, L.h) -= CAMP.patron_relation
```

**Recording:** `recorded = besieged || gap ≥ ENGINE.battle_record_power_gap`.
- Not recorded: append to the war's description `" Epoch <n>, clash #<k> (<place or l>): <summary>."`; bond war → l `side` ('loser').
- Recorded: name root `dildenAd(place if settlement else l, '<war>:<k>:muharebe', 'place') || place.name || l.name`; record event subtype `kuşatma` (siege) / `muharebe` (battle), name `"Siege of <root>"` / `"Battle of <root>"`, power `clampi(CAMP.battle_record_power_min + round(gap / CAMP.battle_record_power_divisor), min, CAMP.battle_record_power_max)`, location place, stats `{violence: clampi(CAMP.battle_violence_base + round(gap), 0, 100)}`, description "[World engine] Clash #<k> of <war>. <ow> (<n> soldiers, morale <m>) against <ol> (<n> soldiers, morale <m>). <summary>." Bonds battle → war `part_of`, battle → w `side` ('victor'), battle → l `side` ('loser').

**Duel:** `hw = kahramanlariOf(w)`, `hl = kahramanlariOf(l)`; if both non-empty and `chance(ENGINE.duel_chance)`:
- `x = pick(hw)`, `y = pick(hl)`; bond `x → y 'hasim'` (nemesis, described with war name) if absent; war → x and war → y `side` ('dueled') if absent.
- duel power `p = power + agility / CAMP.duel_agility_divisor + H.weaponPower(m, CAMP.duel_weapon_mult) + d(CAMP.duel_die) * CAMP.duel_die_mult`; winner = higher (ties x).
- `chance(ENGINE.duel_death_chance)`: `olumYolu(loser, epoch, "fell in a duel with <winner> in <war>", winner, "<war> duel")`; bond (battle or war) → loser `caused` ('fell in a duel'); `winner.charisma += CAMP.duel_charisma_gain`; if both sides known → `kanDavasi(sideW, sideL, epoch, "<loser>'s blood")`; text " In a duel <winner> killed <loser>; now there is a blood feud between the two sides."
- else `loser.hp = clampi((hp || CAMP.default_hp) − CAMP.duel_wound, 1, LIMITS.hp_cap)`; text " <winner> and <loser> dueled; <loser> was badly wounded."

**Capture:** candidates `kahramanlariOf(l)` still canon; `chance(ENGINE.capture_chance)` → `e = pick`; bond `w → e 'esir'` (war name); tag `esir`; bond (battle or war) → e `caused` ('was captured'); text " <e> was taken prisoner."

Note: "<war>: <summary>.<hero texts>" ids [battle?, war, w, l, duelists…, prisoner], son = `W.h?.id`.

### 10.4 War end
```
score = war.score
routed = first of [oa, ob] with morale <= CAMP.rout_morale or size < CAMP.rout_size
tired  = war.battles >= CAMP.exhaustion_battles && chance(ENGINE.war_exhaustion_chance)
if |score| >= CAMP.victory_score or routed or tired:
    decisive = |score| >= CAMP.victory_score or |score| >= ENGINE.exhaustion_victory_margin
    victor = routed ? (routed is oa ? b : a) : (!decisive ? null : score > 0 ? a : score < 0 ? b : null)
    loser  = other side if victor
    barisYap(a, b, epoch, victor ? "end of <war>" : 'white peace')
    result = 'white peace'
    if victor:
        if victor.type in (faction, people) and loser.type == settlement:     // CONQUEST
            close all active rules bonds targeting loser
            bond victor -> loser 'rules' ("conquest of <war>"); result = 'conquest'
            if victor speaks L and loser doesn't speak L: bond loser -> L 'speaks' ('came with conquest')  // old language kept
            if a canon wonder is located in loser: text " <wonder> wonder is now in <victor>'s hands."
        else:                                                                   // TRIBUTE
            if active pays_tribute loser->victor exists: refresh its epoch and description (=war name)
            else bond loser -> victor 'harac_oder' (war name)
            result = 'tribute'
        gH = hami(victor), mH = hami(loser)
        if gH and gH != mH and chance(result == conquest ? ENGINE.conquest_conversion_chance : ENGINE.tribute_conversion_chance)
           and dinDegistir(loser, gH, epoch, "came with the <conquest|tribute> of <war>", {syncretic: mH != null && chance(ENGINE.conquest_syncretism_share)}):
            text " <loser> <converted to gH's faith | began to worship gH>."
        tIliskiDegistir(a, b, -(result == conquest ? CAMP.conquest_relation : CAMP.tribute_relation), result)
    else:
        tIliskiDegistir(a, b, +CAMP.white_peace_relation, 'exhaustion peace')
    seferBitir(a, b, epoch, result, note, victor, loser)
    note victor ? "<war> ended: <victor> won (<conquered loser | loser will pay tribute>).< <routed army> disbanded.><extra>"
               : "<war> ended with no victor; both sides were exhausted."   ids [war, a, b]
```
Conquest only happens for factions/peoples beating a settlement; everything else becomes tribute.

---

## 11. Tribute (`haraclar(epoch, note, H)`)
Active `pays_tribute` bonds ordered by epoch DESC, id DESC:
1. Duplicate (payer, receiver) beyond the first → close.
2. Either side not canon → close.
3. `epoch − bond.epoch ≥ ENGINE.tribute_duration` → close; `+CAMP.tribute_end_relation` ('tribute ended'); note "The tribute <payer> paid to <receiver> ended after <n> epochs."; continue.
4. Bond made this epoch → skip.
5. Flow: for prosperity and wealth (only if present): payer −= `ENGINE.tribute_flow`, receiver += `ENGINE.tribute_flow` (clamp 0..100; direct add, *not* diminishing `refahEkle`). If both have a society: `flow = round(payer.goods * ENGINE.tribute_goods_share / 100)`; if > 0 move it (receiver clamped to `SOC.storage_cap`).
6. Revolt: if `H.militaryPower(payer) > H.militaryPower(receiver) * ENGINE.tribute_revolt_power_ratio / 100 && chance(ENGINE.tribute_revolt_chance)` → close; `−CAMP.tribute_revolt_relation` ('tribute revolt'); `savasIlan(payer, receiver, 'tribute revolt')`; note "<payer> grew strong and refused to pay tribute to <receiver><; the two sides went to war again>."

## 12. Prisoners (`esirler(epoch, note, H)`)
For each active `holds_prisoner` bond captor → prisoner:
- `release(text)`: close bond, remove tag `esir`, note text if any (ids captor, prisoner, …).
- Prisoner not canon → release silently. Captor not canon → release "<e> was freed from captivity when <captor | 'the captors'> scattered."
- Bond made this epoch → skip.
- `home` = first canon community targeted by prisoner's active `protects`/`descends_from` bond. `rich = home && (home.wealth ?? 0 ≥ CAMP.ransom_min_wealth || home.prosperity ?? 0 ≥ CAMP.ransom_min_prosperity)`.
- In order (first match wins):
  1. **Ransom**: `rich && chance(ENGINE.ransom_chance)` → home wealth and prosperity −= `CAMP.ransom_cost` (if present); captor wealth += cost (clamped), captor prosperity via `refahEkle(+cost)`; `+CAMP.ransom_relation` (home↔captor, 'ransom'); release "<home> paid <captor> a heavy ransom for <e>; the prisoner returned home."
  2. **Escape**: `chance%(100 * ((agility || CAMP.prisoner_default_stat)/CAMP.escape_agility_divisor + (intellect || default)/CAMP.escape_intellect_divisor))` → release "<e> escaped from <captor>'s dungeon."
  3. **Execution**: `home && tIliski(home, captor) ≤ −CAMP.execution_relation && chance(ENGINE.execution_chance)` → close bond (tag stays; prisoner dies); `olumYolu(e, epoch, "executed by <captor>", captor, 'execution')`; `kanDavasi(home, captor, "<e>'s execution")`; note "<captor> executed its prisoner <e>; <home> swore vengeance."
  4. **Turncoat**: `epoch − bond.epoch ≥ CAMP.prisoner_turncoat_age && chance(ENGINE.prisoner_turncoat_chance)` → close bond, remove `esir`; deactivate e's `protects` bonds to any community other than the captor; bond `e → captor 'protects'` ('from captivity to loyalty'); note "After years of captivity <e> pledged to <captor> and joined their side."

---

## 13. Society and economy (`toplumEkonomi(epoch, note, Y)`)

Per-epoch caps: famines `SOC.famine_cap`, uprisings `SOC.uprising_cap`, bankruptcies `SOC.bankruptcy_cap`, weapon batches `SOC.weapon_cap`.

For each canon **people or settlement** `v` (fresh read):
1. `s = toplumOf(v)`; `climate = iklimOf(v.world)`; `atWar` = any active enemy bond involving v (with anything); `routes` = count of active trade bonds; `paysTribute`; `god = hami(v)` or, if v worships the creator (`tapar` to `t`), a creator marker.
2. **Class targets**: `target = base shares` then
   - knows agriculture: farmer += `SOC.target_agriculture_farmer`
   - knows trade **or** routes > 0: merchant += `SOC.target_trade_merchant + min(SOC.target_route_merchant_cap, routes * SOC.target_route_merchant)`
   - knows writing: scribe += `SOC.target_writing_scribe`
   - knows metallurgy or craft ≥ `SOC.target_craft_threshold`: artisan += `SOC.target_artisan`
   - knows seafaring: merchant += `SOC.target_seafaring_merchant`
   - at war: warrior += `SOC.target_war_warrior`
   - god and faith (?? `SOC.default_stat`) ≥ `SOC.target_faith_threshold`: priest += `SOC.target_priest`
   - tagged godless: priest = `SOC.target_godless_priest` (override)
   - normalise `target` to sum 100 (1 decimal). Drift: `k[c] = round1(k[c] + (target[c] − k[c]) * SOC.class_drift/100)`; normalise `k`.
3. **Fertility**: `place = location(v)`; `regionF = topRegion(v).fertility`; if place is a region or regionF is null → `fert = place.fertility ?? SOC.default_stat`; else `fert = round((place.fertility ?? default) * SOC.fertility_place_share/100 + regionF * SOC.fertility_region_share/100)`.
4. **Food**:
```
prod = (k.farmer / SOC.food_farmer_divisor)
     * (SOC.food_base/100 + fert / SOC.food_fertility_divisor)
     * (knows agriculture ? SOC.food_agriculture_mult/100 : 1)
     * (Y.has('fertility', v) ? SOC.food_fertility_law_mult/100 : 1)
     * (climate == drought ? SOC.food_drought_mult/100 : climate == rain ? SOC.food_rain_mult/100 : 1)
ratio = clampf(prod, SOC.food_ratio_min/100, SOC.food_ratio_max/100)
food = clampi((food ?? SOC.initial_food) + (ratio - 1) * SOC.food_ratio_effect - (atWar ? SOC.war_food_cost : 0)
              + (oldFood < SOC.food_low ? SOC.food_low_gain : 0), 0, SOC.storage_cap)
```
(Defaults: 55% farmers, fertility 50 → ratio ≈ 1.23.)
5. **Ore**: `mines` = canon resources owned by v (`owns`) whose name+subtype matches the ore regex (Turkish words: mine, ore, iron, copper, metal, stone, salt, crystal, coal, gold, silver, bone, obsidian, glass — LANGUAGE-SPECIFIC; in the new design give resources an explicit `category` instead). `ore = clampi((ore ?? SOC.initial_ore) + Σ(mine.abundance / SOC.ore_abundance_divisor) − SOC.ore_consumption, 0, cap)`.
6. **Goods**: `craft = (k.artisan / SOC.goods_artisan_divisor) * (ore > SOC.ore_plentiful ? SOC.goods_ore_mult/100 : 1) * (knows metallurgy ? SOC.goods_metallurgy_mult/100 : 1)`; `goods = clampi((goods ?? SOC.initial_goods) + craft * SOC.goods_production_mult − SOC.goods_consumption − round((prosperity ?? default) / SOC.goods_prosperity_divisor), 0, cap)`; if `goods > SOC.goods_ore_threshold && ore > threshold`: `ore −= round(craft * SOC.goods_ore_spend)`.
7. **Prices** (percent of normal):
   - food `= clampi(100 / max(SOC.price_ratio_floor/100, ratio) * (food < SOC.price_scarcity_food ? SOC.price_scarcity_mult/100 : food > SOC.price_plenty_food ? SOC.price_plenty_mult/100 : 1), SOC.price_min, SOC.price_food_max)`
   - ore `= clampi(100 * SOC.price_ore_equilibrium / max(min(SOC.price_stock_floor, SOC.price_ore_equilibrium), ore), SOC.price_min, SOC.price_max)`
   - goods `= clampi(100 * SOC.price_goods_equilibrium / max(SOC.price_stock_floor, goods), SOC.price_min, SOC.price_max)`
8. **Satisfaction targets** (`P = prosperity ?? default`):
   - farmer: `P + (food < SOC.sat_hungry_food ? −SOC.sat_farmer_hungry : +SOC.sat_farmer_fed) − (atWar ? SOC.sat_farmer_war : 0)`
   - artisan: `P + (ore > SOC.ore_plentiful ? +SOC.sat_artisan_plenty : −SOC.sat_artisan_scarce)`
   - merchant: `P + routes * SOC.sat_merchant_route − (atWar ? SOC.sat_merchant_war : 0) − (routes ? 0 : SOC.sat_merchant_no_route)`
   - priest: `(faith ?? default) + (god ? +SOC.sat_priest_god : −SOC.sat_priest_no_god) − (godless tag ? SOC.sat_priest_godless : 0)`
   - warrior: `SOC.sat_warrior_base + (atWar ? +SOC.sat_warrior_war : −SOC.sat_warrior_peace) + (knows warcraft ? SOC.sat_warrior_warcraft : 0)`
   - scribe: `P + (knows writing ? +SOC.sat_scribe_writing : −SOC.sat_scribe_no_writing)`
   - all classes: `− (paysTribute ? SOC.sat_tribute : 0) + (justice != null ? (justice − 50)/SOC.sat_justice_divisor : 0) − (tagged cursed ? SOC.sat_curse : 0)` where `justice` = average `adalet` of canon law codes (`kanun`) located at v.
   - drift: `m[c] = clampi(m[c] + (clampi(target,0,100) − m[c]) * SOC.sat_drift/100, 0, 100)`.
9. **Effects on community stats (every epoch, cumulative)**:
   - `refahEkle(prosperity, round((k.merchant − base.merchant)/SOC.effect_prosperity_divisor) + (goods > SOC.effect_goods_plenty ? SOC.effect_goods_prosperity : 0))`
   - faith (if present) += `round((k.priest − base.priest)/SOC.effect_faith_divisor)`
   - settlement defence `= clampi((defence ?? SOC.effect_default_defence) + round((k.warrior − base.warrior)/SOC.effect_defence_divisor), 0, 100)`
   - people martiality (if present) += `round((k.warrior − base.warrior)/SOC.effect_martial_divisor)`
10. **Famine**: `food ≤ SOC.famine_food && ratio < SOC.famine_ratio/100 && famines < cap` → population ×= `SOC.famine_population_remaining/100` (clamp), prosperity −= `SOC.famine_prosperity_loss`; note "<v>'s granaries emptied: bread now costs <price/100, 1 decimal>× as much, the farmers are hungry." ids [v, location].
11. **Weapon forging**: `ore ≥ SOC.weapon_ore_required && knows metallurgy && k.warrior ≥ SOC.weapon_warrior_share && batches < cap && chance(ENGINE.weapon_forging_chance)` → `ore −= SOC.weapon_ore_cost`; record item subtype `silah` (weapon) named `"Swords of <v>"` (`<v> Kılıçları`), power `SOC.weapon_power_level`, location v or v's location, stats `{damage: SOC.weapon_damage_base + d(die), protection: base + d(die), might: base + d(die), curse: 0}`, description "[World engine] <v>'s smiths forged a batch of weapons from their ore."; bonds v → item `produced` ('forge'), v → item `owns`; note "<v>'s forges hammered out new weapons."
12. **Guild bankruptcy**: `k.merchant ≥ SOC.bankruptcy_merchant_share && routes == 0 && prosperity < SOC.bankruptcy_prosperity && n < cap && chance(ENGINE.guild_bankruptcy_chance)` → merchant satisfaction −= `SOC.bankruptcy_satisfaction_loss`; merchant share −= `SOC.bankruptcy_share_loss`, normalise; prosperity −= `SOC.bankruptcy_prosperity_loss`; note "<v>'s merchant guilds went bankrupt; debtors are on the streets."
13. **Class uprising**: among classes with share ≥ `SOC.uprising_min_class_share`, the one with the lowest satisfaction `mk`; if `mk < SOC.uprising_satisfaction && population > SOC.uprising_min_population && n < cap && chance(ENGINE.class_uprising_chance)`:
    - record faction subtype `"<class singular> uprising"`, name `"<v> <Class> Uprising"`, power `SOC.uprising_power_level`, location, stats power `SOC.uprising_faction_power + d(die)`, wealth `SOC.uprising_wealth + d(die)`, influence `SOC.uprising_influence + d(die)`, tag `sinif:<class>`, description "[World engine] The <class plural> of <v> (satisfaction <mk>) rose up."
    - `savasIlan(faction, isyanHedefi(v), "<class plural> uprising", epoch, {cap: false})` (civil war ignores the world cap, otherwise the revolt would be born without war and dissolve).
    - faction speaks v's language; class satisfaction += `SOC.uprising_relief`; note "In <v> the <class plural> rose up: their satisfaction had fallen to <mk>."
14. Save stats and society.

**Trade flows** (after all communities): for each active trade bond between canon peoples/settlements A–B, for each store in (food, ore, goods): `gap = A − B`; if `|gap| < SOC.trade_min_gap` skip; `flow = round(gap / SOC.trade_flow_divisor)`; A −= flow, B += flow (unclamped); seller (A if flow > 0 else B) `refahEkle(+SOC.trade_seller_prosperity)` if it has prosperity. Persist both societies.

---

## 14. Heroes (`kahramanlar(epoch, note, H)`)

**Hero test** (`kahramanMi`): canon mortal, not tagged `esir`, and (subtype matches `kahraman|savaşçı|şövalye|avcı|seçilmiş` = hero|warrior|knight|hunter|chosen — LANGUAGE-SPECIFIC regex, use a role enum — or tagged `seçilmiş`, or `power + agility ≥ LIFE.hero_power_sum`).

Counters: new quests ≤ `LIFE.quest_new_cap`, resolved ≤ `LIFE.quest_resolve_cap`, companions ≤ `LIFE.companion_cap`, apprentices ≤ `LIFE.apprentice_cap`.

**14.1 Quests.** For each hero (fresh read):
- `active` = newest active `pursues` bond from h.
- If active and made before this epoch and resolved < cap → `resolved++`, `gorevSonucu` (14.3), next hero.
- If active, or new ≥ cap, or `!chance(ENGINE.quest_chance)` → next.
- `g = gorevBul(h)`; if none → next. `new++`; bond `h → g.target 'pesinde'` with `g.description`; if thread quest → tag `iplik:<threadId>`; note "<h> set out: <description>."

**14.2 Quest choice (`gorevBul(h)`)** — weighted candidates (`t = tarafOf(h)`):
| Kind | Candidates | Weight | Description |
|---|---|---|---|
| hunt | canon species with danger ≥ `LIFE.quest_hunt_min_danger`, `mesafe(h, x) ≤ LIFE.quest_max_distance`, not already killed by h | `LIFE.quest_weight_hunt` | "to hunt <x>" |
| thread | each open story thread: target = first related id that is canon, ≠ h, not a language/law, same world; eligible if `t` and (thread mentions t, or any related entity shares h's top region) | `LIFE.quest_weight_thread` | "to pursue the secret of the open story around <target>" |
| relic | canon items with no active owner within quest distance | `LIFE.quest_weight_relic + (power ≥ LIFE.quest_relic_strong_level ? LIFE.quest_relic_strong_bonus : 0)` | "to find the lost <item>" |
| knowledge | canon knowledge tagged `kayıp` in h's world | `LIFE.quest_weight_knowledge` | "to search the ruins for the lost <k> knowledge" |
| vengeance | if t: each blood-feud relation of t with a canon community E → first mortal of E | `LIFE.quest_weight_vengeance` | "to avenge the blood feud on <E> (<target>)" |
Weighted random pick (fallback first).

**14.3 Quest resolution (`gorevSonucu`)**:
- target missing, or not canon/dead, or dead but not a species → close silently.
- species: close; if still canon → `H.heroicDeed(h, target, epoch, note, 'at the end of a long hunt')` (fight resolved in sim.js). Return.
- `companions` = canon partners of h's active `companion` bonds.
- `p = clampf((power + agility + intellect)/LIFE.quest_success_divisor + companions.len * LIFE.quest_companion_bonus/100 + (chosen ? LIFE.quest_chosen_bonus/100 : 0), LIFE.quest_success_min/100, LIFE.quest_success_max/100)`; `age = epoch − bond.epoch`.
- **Success** (`chance p`): close; charisma += `LIFE.quest_charisma_gain`; h's patron fame += `LIFE.quest_fame_gain`; companion text " <names> were at their side."; by target type:
  - item → bond h → item `owns` ('found by quest'); note "<h> found the lost <item> and took it up."
  - knowledge → `side = tarafOf(h) || h`; `ogret(side, k, "<h> recovered it from the ruins")`; remove `kayıp`; note "<h> found the forgotten <k> knowledge among the ruins and brought it back to <side>."
  - mortal (vengeance) → `olumYolu(target, epoch, "killed by <h> avenging the blood feud", h, 'blood feud')`; note "<h> took revenge for the blood feud: <target> is dead."
  - else (thread) → note "<h> found what they sought on the road taken <description>: a hidden truth about <target> is now in their hands." (thread itself not closed, `iplik:` tag not removed.)
- **Failure**: `chance(ENGINE.quest_death_chance)` → close; `olumYolu(h, "died on the road <description>")`; note "<h> gave their life on the road <description>." Else if `age ≥ LIFE.quest_give_up_age` → close; note "<h> searched for years but came back empty-handed from the quest <description>." Else `hp = clampi((hp || CAMP.default_hp) − LIFE.quest_wound, 1, LIMITS.hp_cap)` (quest continues).

**14.4 Companions.** `living` = heroes still canon. Snapshot of companion/nemesis bonds; memoised side id. For pairs i<j until cap: skip if already companions or nemeses, different side ids (note: two side-less heroes compare `null == null` → allowed), or `!chance(ENGINE.companion_chance)`. Bond `a → b 'yoldas'` ('fellowship of the road'); note "<a> and <b> became companions of the road."

**14.5 Master–apprentice.** For each living hero until cap:
- `age = age || 0`, `life = lifespan || LIFE.apprentice_lifespan_fallback`; skip if `age < life * LIFE.apprentice_age_share/100`, or charisma < `LIFE.apprentice_min_charisma`, or h already has an apprentice (any active `apprentice_of` → h), or `!chance(ENGINE.apprentice_chance)`.
- `st(k) = clampi((h[k] || LIFE.apprentice_stat_fallback) * LIFE.apprentice_stat_share/100 + d(LIFE.apprentice_stat_die), 0, 100)`.
- name = `dildenAd(h, '<h>:<epoch>:cirak', 'person') || "<h>'s Apprentice"`; tag `dilden-ad` if language-made.
- record mortal subtype `çırak` (apprentice), power `max(1, h.power − LIFE.apprentice_power_gap)`, location h's location, stats `{hp: LIFE.apprentice_hp, power, agility, intellect, charisma: st(...), age: LIFE.apprentice_age, lifespan: clampi(life + d(LIFE.apprentice_lifespan_die) − LIFE.apprentice_lifespan_shift, LIFE.apprentice_lifespan_min, LIFE.lifespan_cap)}`, description "[World engine] The ageing <h> began passing on what they know to an apprentice."
- bonds: apprentice → h `ustasi`; → tarafOf(h) `protects`; → hami(h) `worships`; → h's language `speaks`.
- Weapon bequest: h's owned canon item with highest damage; `chance(ENGINE.weapon_bequest_chance)` → close h's owns bond; apprentice → item `owns` ("entrusted by <h>"); text " and entrusted <item> to them".
- note "<h> began training an apprentice<…>."

---

## 15. Dark ages (`karanlikCaglar(epoch, note)`)

**15.1 Forgetting** — for canon communities until `LIFE.dark_age_forget_cap`:
- skip if knows nothing.
- `devastation` = prosperity (?? default) < `ENGINE.dark_age_prosperity` **or** an event created this epoch at v or v's location with violence ≥ `LIFE.dark_age_violence` **or** an active `rules` bond to v made this epoch whose description ends with "conquest" (`…fethi`) **or** a settlement that died this epoch located at v's location or ruled by v. (A new ruler taking the throne is **not** devastation.)
- `protected` = society scribe share ≥ `LIFE.dark_age_scribe_share` **or** a canon work matching the knowledge-keeper regex (library|archive|school|inscription|bookcase|madrasa|wisdom|observatory) located at v or v's location **or** a canon `eser` whose subtype matches book|inscription|epic located at v.
- `chance(protected ? ENGINE.dark_age_protected_forget_chance : ENGINE.dark_age_forget_chance)` → pick a known knowledge; set that `knows` bond inactive with description `'unutuldu'` (forgotten); note "After the devastation <v> forgot the <k> knowledge; the masters died, the records burned."

**15.2 Lost marking** — each canon knowledge not tagged lost: if it has no active `knows` bond but had one historically → tag `kayıp`; note "No one is left who knows <k>; it is now a lost knowledge that leaves traces only in ruins."

**15.3 Spread** — for each canon knowledge: `n` = active knows bonds from canon entities; `target = lost ? 0 : min(100, LIFE.knowledge_spread_base + n * LIFE.knowledge_spread_per_knower)`; `y0 = spread ?? LIFE.knowledge_spread_fallback`; move toward target by at most `LIFE.knowledge_spread_step`.

**15.4 Rediscovery** — if any lost knowledge: for canon peoples/settlements with scribe share ≥ `LIFE.relic_scribe_share` until `LIFE.relic_rediscovery_cap`: `ruin` = any entity tagged `harabe` or subtype containing "ruin"/"remains" located at v's location or v's top region (no status/world filter); need `chance(ENGINE.relic_rediscovery_chance)`; pick a lost knowledge of v's world; `ogret(v, k, 'rediscovered from the ruins')`; remove `kayıp`; note "<v>'s scribes deciphered the forgotten <k> knowledge in the ruins of <ruin>."

---

## 16. Espionage (`casusluk(epoch, note)`)

**16.1 Founding** — for canon factions with influence ≥ `LIFE.spy_min_influence`: skip if founded ≥ `LIFE.spy_network_cap` this epoch or the faction already runs an active spy network. Target = canon community in the same world, ≠ self, with (enemy or tribute or truce bond with the faction, or relation ≤ −`LIFE.spy_target_coldness`); sort enemies first, then lowest relation, then id. `chance(ENGINE.spy_network_chance + (enemy or tribute ? ENGINE.spy_network_enemy_bonus : 0))` → bond `faction → target 'casus'` ('agent network'); note "<faction> began weaving a secret agent network inside <target>."

**16.2 Operations** — each active spy bond A → B: close if either not canon; skip if made this epoch.
- **Caught**: `chance%(LIFE.spy_capture_base + 100 * (B.influence || B.defence || LIFE.spy_capture_fallback) / LIFE.spy_capture_divisor)` → close; `−LIFE.spy_caught_relation` ('caught spies'); `war = chance(ENGINE.spy_war_chance) && savasIlan(B, A, 'espionage')`; note "<A>'s spies were caught in <B><; B declared war | ; the network was dismantled>." Next.
- `!chance(ENGINE.spy_action_chance)` → idle.
- Knowledge B has and A lacks; if any and `chance(ENGINE.spy_steal_share)` → steal: `ogret(A, k, "stolen from <B>")`; note "<A>'s agents stole the <k> knowledge from <B>."
- else sabotage: B's defence, power, wealth (if present) −= `LIFE.spy_sabotage`; note "<A>'s agents sabotaged <B>: granaries burned, sentries poisoned."

## 17. Wonders (`harikalar(epoch, note)`)
1. Promote: canon works not tagged `harika` with splendour ≥ `LIFE.wonder_min_splendour` **or** power ≥ `LIFE.wonder_min_power` → tag; note "<work> joined the wonders of the world; pilgrims and envious eyes from distant lands turn to it."
2. For each wonder: owner = its location if a community, else the source of the first active built/rules/owns bond. If canon owner: `refahEkle(+LIFE.wonder_prosperity)`; faith (if present) += `LIFE.wonder_faith`; owner's patron fame += `LIFE.wonder_fame`. For each neighbouring canon community k (≠ owner): if relation < `LIFE.wonder_envy_threshold` → `−LIFE.wonder_envy_relation` (no history). If relation ≤ −`LIFE.wonder_war_relation` and `chance(ENGINE.wonder_envy_war_chance)` and `savasIlan(k, owner, "for <work>")` → note "<k> coveted the <work> wonder and declared war on <owner>."

## 18. Abandonment into ruins (`harabeler(epoch, note)`)
Every canon settlement with `(population || 0) < ENGINE.ruin_threshold` and `epoch − created ≥ ENGINE.ruin_grace`: status `olu`, death epoch, fate-note append "Epoch <n>: abandoned, turned into a ruin."; tag `harabe` (subtype kept: village/town); `olulerinBaglari(epoch, noop, id)` (language, god, ownership, rule close; property passes to heir); note "<y> was abandoned and fell to ruin.< Left behind: <works and items located there>.>"

---

## 19. Climate eras

### 19.1 Era table (`IKLIM`, defined in rules.js; numbers in rule group `IKLIM_ETKI`)
| Key | Name | Description | Fertility per transition | Base weight | Extra |
|---|---|---|---|---|---|
| `ilik` | Temperate era (Ilıman devir) | "the seasons are in their place" | +1 | 40 | |
| `kurak` | Century of drought (Kuraklık yüzyılı) | "rivers are receding, the interior is scorched" | −5 | 18 | food ×0.8 (SOC) |
| `yagmur` | Rain era (Yağmur devri) | "the rain won't stop; floods on the coasts, plenty in the plains" | +4 | 18 | food ×1.1 |
| `buzul` | Ice age (Buz devri) | "winters lengthen, mountain passes close" | −4 | 12 | population −3%/transition |
| `sicak` | Scorching era (Kavurucu devir) | "the sun hangs low; disease and wrath increase" | −3 | 12 | plague frequency ×1.5 |
World-type multipliers (`IKLIM_TUR`, % on weight; default 100): ocean (ice 25, drought 30, rain 200), sand (drought 250, rain 30, scorching 180), ice (ice 300, scorching 20, drought 60), lava (scorching 300, …). `weight(worldType, era) = (IKLIM_TUR[type_era] ?? 100)/100 * IKLIM[era].weight`.

### 19.2 `iklimGecis(newEpoch, notes)` — epoch transition
For each non-forgotten world (by id; if none, a virtual world 1 of type ordinary):
1. `c = world.climate` or (first world) `dunya.iklim`. If missing/invalid → `{era: 'temperate', left: LIFE.climate_first_duration + d(LIFE.climate_first_die), start: current epoch}`.
2. If `c.god` (era ordered by a god/creator mid-epoch): apply effect once (19.3) and delete the flag. (Combined with the regular application below, an N-epoch order applies exactly N times.)
3. `c.left −= 1`. If `≤ 0`: choose a new era ≠ current by weights (> 0), `{era, left: LIFE.climate_duration + d(LIFE.climate_die), start: newEpoch}`; chronicle (kind `iklim`, no son) "<World name: (only if multi-world)><Era name> began: <description>." and push to notes.
4. Apply effect (19.3). Persist to `dunyalar.iklim`. First world's climate is copied to `dunya.iklim`. Returns first world's climate.

### 19.3 Effect (`iklimEtkisi`) for one transition in one world
For each canon region/place with a fertility stat in that world: `info = map info of its top region (or itself)`:
```
e = era.fertility
if drought and info.coastal: e = round(e / LIFE.climate_coast_drought_divisor)
if rain and info.coastal:    e += LIFE.climate_coast_rain_bonus
if ice and info.elevation in (mountainous, hilly): e -= LIFE.climate_mountain_ice_loss
f = fertility
f = clampi(f + e + (LIFE.fertility_equilibrium - f) / (f < eq ? ENGINE.fertility_recovery_divisor : ENGINE.fertility_decline_divisor), 0, 100)
```
If the era has a population factor (ice age): every canon people/settlement in the world `population = clampi(pop * (1 + factor), LIMITS.population_floor, LIMITS.population_cap)`.

### 19.4 `iklimOf(x = world row)`
Number → that world's climate; if none and x is the lowest world id → global `dunya.iklim`. Object → parse its `iklim`. Returns `{era, left, start, ...IKLIM[era]}` (name, fertility, weight, description, population?, plague?) or null.

---

## 20. God death, resurrection, fading

### 20.1 `tanriOlumu(son, epoch, cause, notes = [])` → corpse id
1. Regions = canon regions, preferring those in `son.aktif_dunya`.
2. `worshippers` = canon entities with an active worship bond to the son.
3. Resting land `home = topRegion(son.anchor) || topRegion(worshippers[0]) || pick(regions) || null`.
4. **Corpse**: record place subtype `tanrı cesedi` (god corpse), name `"Bones of <son>"`, power `LIFE.god_corpse_power`, location home, stats `{danger, fertility, mystery}` from LIFE.god_corpse_*, tags `['tanrı cesedi', 'ceset:<son>']`, description "[World engine] <son>, <title>, died (<cause>). Their body fell <onto the lands of home | to the world> and became a place; <domain1> and <domain2> still seep from it."
5. **Shade**: record spirit subtype `tanrı ruhu` (god spirit), name `"Shade of <son>"`, power `LIFE.god_shade_power_level`, location = corpse, stats `{power: LIFE.god_shade_power, unrest: LIFE.god_shade_unrest}`, description "[World engine] The shade of the dead god <son> wanders above their bones."
6. Bonds: corpse → son `tells_of` ('corpse'); shade → son `descends_from` ('shade').
7. Each worshipper: `chance(ENGINE.apostasy_chance)` → deactivate its worship of the son, tag `tanrısız`, apostates++; else loyal (keeps worshipping the dead god).
8. Cult followers `= clampi(Σ loyal (population || followers || LIFE.resurrection_cult_population_fallback) * LIFE.resurrection_cult_share/100, LIFE.resurrection_cult_min_followers, LIFE.resurrection_cult_max_followers)`.
9. **Resurrection cult**: record cult subtype `diriliş tarikatı`, name `"Those Who Await <son>'s Return"`, power `LIFE.resurrection_cult_power_level`, location corpse, stats `{followers, zeal: LIFE.resurrection_cult_zeal, influence: LIFE.resurrection_cult_influence, devotion: 0}`, tag `dirilis:<son>`, description "[World engine] Those who stayed loyal to <son> gathered at their bones; they believe the god will return." Bond cult → son `worships` ('to the dead god').
10. Story thread: "<son> died; their bones lie in <home | the world>. The loyal await the resurrection. Who will call them back, who will scatter the bones?" related [corpse, cult, shade].
11. Son: status `olu`, death epoch, `ceset_id`, `asi = 0`; persist; `solus = 0`.
12. Creator essence `dunya.tanri_oz += round(son.essence / LIFE.dead_god_essence_divisor)`.
13. Every other living son: relation to the dead ≤ −`LIFE.god_death_relation` → fame += `LIFE.god_death_enemy_fame`; ≥ +threshold → passion anger += `LIFE.god_death_friend_anger` (clamp 0..100).
14. Chronicle (kind `olum`, son id, ids [corpse, shade, cult]) "<creator name>'s son <son> died (<cause>). Their body became <corpse>; <apostates> of their worshippers fell into denial, <loyal> await their resurrection." Push to notes.

### 20.2 `dirilt(son, epoch, path, notes = [])` — resurrection
Status `aktif`; existence = `LIFE.resurrection_existence`; hp = `round(canMax(stats)/LIFE.resurrection_hp_divisor)`; essence = `round(ozMax(stats)/LIFE.resurrection_essence_divisor)`; fame += `LIFE.resurrection_fame`; every stat −= `LIFE.resurrection_stat_loss` (clamp 1..100). Persist; `olum_cag = NULL`, `solus = 0`. Corpse → subtype `boş mezar` (empty tomb), tag swap `tanrı cesedi` → `boş mezar`. Cults tagged `dirilis:<son>` → tag swap to `diriliş tamam` (resurrection complete), devotion = 0. Chronicle (kind `dirilis`) "<son> was reborn from where they died (<path>)<; <corpse> is now an empty tomb>. The mark of death is on them: their power slightly diminished, but now they know what death is." (Shade and thread are not removed.)

### 20.3 `solusDurumu()` — fading status (UI)
For each non-dead son: `{id, name, status, existence (?? LIFE.existence_fallback), threshold: LIFE.fading_threshold, fading_counter, duration: LIFE.fading_epochs, fading: existence ≤ threshold, left: fading ? max(0, duration − counter) : null}`.

### 20.4 `tanrilarinKaderi(newEpoch, notes)` — epoch transition
For each son:
- **Dead**: for each canon cult tagged `dirilis:<son>`: `devotion = clampi(devotion + round(log10(max(10, followers || 10)) * LIFE.devotion_followers_mult + influence/LIFE.devotion_influence_divisor + zeal/LIFE.devotion_zeal_divisor), 0, LIFE.devotion_cap)`; if `devotion ≥ LIFE.resurrection_devotion` and corpse is canon and `diriliseKalan(son, newEpoch) == 0` (minimum death time from `OLUM.dirilis_en_az_cag`) and `chance(ENGINE.resurrection_chance)` → `dirilt(son, newEpoch, "by the rite of <cult>")`, stop processing cults. Continue.
- **Alive**: if `existence (?? fallback) ≤ LIFE.fading_threshold`: `counter += 1` (persist); `left = LIFE.fading_epochs − counter`; chronicle (kind `varolus` existence):
  - `left == 2`: "<son> is nearly forgotten; their name lingers in only a few mouths. If two more epochs pass like this, they will fade."
  - `left == 1`: "<son>'s voice is no longer heard even in dreams; if they are forgotten one more epoch, they will fade."
  - `left > 2 && counter == 1`: "<son> is nearly forgotten; their name lingers in only a few mouths. If <left> more epochs pass like this, they will fade."
  - `left ≤ 0` → `tanriOlumu(son, newEpoch, 'faded away, forgotten')`.
  Else reset counter to 0.

---

## 21. Spontaneous births (`dogumlar(epoch, note)`)

### 21.1 Roles by class (`ROLLER`) — full table
| Class | Name suffix (title) | Subtype | Stat biases (LIFE.role_<class>_<role>_<stat>) |
|---|---|---|---|
| farmer | "<community> Leader" (Önderi) | folk leader (halk önderi) | power 10, charisma 15 |
| farmer | "… Shepherd" (Çobanı) | shepherd | agility 15, power 5 |
| farmer | "… Midwife" (Ebesi) | midwife | intellect 15, charisma 5 |
| artisan | "… Master" (Ustası) | master artisan | intellect 15, agility 10 |
| artisan | "… Smith" (Demircisi) | smith | power 20 |
| artisan | "… Architect" (Mimarı) | architect | intellect 20 |
| merchant | "… Merchant" (Tüccarı) | merchant | intellect 10, charisma 15 |
| merchant | "… Caravaneer" (Kervancısı) | caravaneer | agility 10, power 10 |
| merchant | "… Money-changer" (Sarrafı) | money-changer | intellect 20 |
| priest | "… Seer" (Kâhini) | seer | intellect 20, charisma 10 |
| priest | "… Healer" (Şifacısı) | healer | intellect 15, charisma 5 |
| priest | "… Bard" (Ozanı) | bard | charisma 20 |
| warrior | "… Warrior" (Savaşçısı) | hero (kahraman) | power 25, agility 15 |
| warrior | "… Hunter" (Avcısı) | hunter | agility 25, power 10 |
| warrior | "… Guard" (Muhafızı) | guard warrior | power 20, charisma 5 |
| scribe | "… Sage" (Bilgesi) | sage | intellect 25 |
| scribe | "… Historian" (Tarihçisi) | historian | intellect 20, charisma 5 |
| scribe | "… Cartographer" (Haritacısı) | cartographer | intellect 15, agility 10 |

### 21.2 `kisiAdi(sources, seed, worldId = null)` — person name
1. For `i = 0..3`, for each non-null source: `dildenAd(source, i ? "<seed>:<i>" : seed, 'person')` → return first non-null.
2. World = `worldId ?? first source's world ?? 1`. For the 3 canon languages of that world with the most active speakers: for kind in (`person`, `general`): `adUret(lang, "<seed>:<kind>", kind)` → return first.
3. null.

### 21.3 `olumluDogur(t, {name, subtype, biases, epoch, description, tags, extraLifespan})` (internal)
- `stat(k) = clampi(LIFE.birth_stat_base + biases[k] + d(LIFE.birth_stat_die), 0, 100)` for power/agility/intellect/charisma.
- `langName = kisiAdi([t], "<t>:<epoch>:<subtype>:<random>", t.world)`; if found: title = the role name (e.g. "Nevrahim Seer"), description gets `"<langName>: "` after the marker, name = langName, tag `dilden-ad`.
- `lifespan = LIFE.birth_lifespan + d(LIFE.birth_lifespan_die) + extraLifespan`.
- record mortal, power `clampi(round(t.power * LIFE.birth_power_share/100) + 1, 1, LIFE.birth_power_max)`, location t if settlement else t's location, stats `{hp: LIFE.birth_hp, …, age: round(lifespan * (LIFE.birth_age_min_share/100 + random * LIFE.birth_age_range_share/100)), lifespan}`.
- bonds: mortal → t `descends_from`, `protects`; → hami(t) `worships`; → t's language `speaks`.

### 21.4 Single ruler rule
- `yoneticiVar(targetId, except = null)` = an active `rules` bond to target from a canon source ≠ except.
- `tekYonetim()`: for every canon community ruled by > 1 distinct canon rulers: bonds newest first; keep the newest whose description ≠ `'yurdu'` ("homeland"), else the newest; for the others: if description `'yurdu'` → `yurduYasara` (convert to `lives_in`, or close if a `lives_in` already exists), else close. Returns closed count.
- `kavimDogurdu(settlementId)` = a people already sprang from this settlement (a people with `rules`/`lives_in` 'homeland' bond to it, or the settlement descends from a people created in the same epoch that has a `descends_from 'divergence'` bond).
- `etnogenezOnar()` (open-time repair): convert all active people→X `rules 'yurdu'` bonds to `lives_in`, then `tekYonetim()`. Returns `{homeland_to_lives_in, duplicate_rule}`.

### 21.5 `dogumlar` steps
0. `tekYonetim()`. `ts` = canon peoples and settlements.
1. **Notable mortals**: `cap = clampi(ceil(|ts| * LIFE.notable_cap_ratio/100), LIFE.notable_cap_min, ENGINE.notable_cap)`. For `t` in shuffled ts until cap:
   - `n = population`; skip if `n < ENGINE.notable_min_population`.
   - `living` = canon mortals descending from t; skip if `living ≥ LIFE.notable_living_base + floor(log10 n)` or `!chance%(ENGINE.notable_chance + 100*min(LIFE.notable_crowd_bonus_max/100, log10(n)/LIFE.notable_crowd_divisor))`.
   - class = weighted by t's class shares (default farmer); role = random of class.
   - `circle = "from among <t>'s <class plural>"`; `olumluDogur(t, {name: "<t> <role suffix>", subtype: role.subtype, biases, extraLifespan: warrior ? LIFE.notable_warrior_lifespan : 0, description: "[World engine] A <subtype> whose name is spoken arose <circle>."})`; note "A <subtype> whose name is spoken arose <circle>: <name>."
2. **Rulers**: for canon entities where (community with `(population || followers || 0) ≥ ENGINE.ruler_min_population`) or type faction, until `ENGINE.ruler_cap`: skip if `yoneticiVar(t)` or `!chance(ENGINE.ruler_chance)`. Role: cult → high priest (`başrahip`, "<t> High Priest"), faction → leader ("<t> Leader"), people → chieftain (`reis`, "<t> Chieftain"), settlement → sovereign (`hükümdar`, "<t> Sovereign"). `olumluDogur(… biases {charisma: LIFE.ruler_charisma, intellect: LIFE.ruler_intellect}, extraLifespan: LIFE.ruler_lifespan, tags ['yönetici'], description "[World engine] took the throne of <t> as <role>.")`; bond mortal → t `rules` ('took the throne'); note "<name> took the throne of <t> as <role>."
3. **Villages**: canon peoples with population ≥ `ENGINE.village_first_population`, until `LIFE.village_cap`:
   - `r` = top region (skip if none). `existing` = canon settlements in r that descend from h or speak h's language.
   - skip if `existing && pop < ENGINE.village_extra_population`; skip if `existing ≥ ceil(pop / ENGINE.village_per_population)` or `!chance(existing ? LIFE.village_extra_chance : LIFE.village_first_chance)`.
   - `migrants = min(max(ENGINE.village_min_population, round(pop * LIFE.village_migration_share/100)), max(0, pop − ENGINE.village_people_remaining))`; skip if `< ENGINE.village_min_population`. `h.pop −= migrants`.
   - Try `harabeyeKur(r, h, migrants, epoch, "when <h> grew crowded")`: if a ruin was rebuilt → if no ruler: bond h → ruin `rules` ("own people's homeland"); note "<h> grew crowded; they settled the ruin of <ruin> and rebuilt it." Continue.
   - Else new settlement: name `dildenAd(h, seed, 'place') || "<h> Village"` / `"<h> Homeland"`; subtype `köy` village (if existing) or `ana yurt` homeland; power `max(LIFE.derived_power_min, h.power − 1)`; location h's location; stats `{population: migrants, prosperity: LIFE.village_prosperity, defence: LIFE.village_defence, faith: h.faith ?? SOC.default_stat}`; description "[World engine] <h> grew crowded; <n> people founded a new settlement in <r>." Bonds: settlement → h `descends_from`; h → settlement `rules` ("own people's homeland"); settlement → h's language `speaks`; → hami(h) `worships`. Note "<h> grew crowded; they founded a new settlement in <r>."
4. **Ethnogenesis**: canon settlements with `epoch − created ≥ ENGINE.ethnogenesis_min_age` and population ≥ `ENGINE.ethnogenesis_min_population`, until `LIFE.new_people_cap`:
   - ancestor `A` = target of y's first active `descends_from`; must be a people/settlement in a **different** top region; skip if `kavimDogurdu(y)` or `!chance(ENGINE.ethnogenesis_chance)`.
   - `split = round(pop * min(100, LIFE.ethnogenesis_population_share)/100)`; record people subtype `yeni kavim` (new tribe), name `dildenAd(y, seed, 'people') || "People of <y>"`, power `max(min, y.power)`, location r or y's location, stats `{population: split, martiality: LIFE.ethno_stat_base + d(LIFE.ethno_stat_die), magic: d(LIFE.ethno_magic_die), craft: base + d(die), faith: y.faith ?? default}`, description "[World engine] Rooted in <r> and descended from <A>, the people of <y> became a distinct folk over generations, with its own customs, its own tongue and its own name."
   - `y.pop = clampi(pop − split, LIMITS.population_floor, LIMITS.town_population_cap)`.
   - bonds: people → A `descends_from` ('divergence'); y → people `descends_from`; people → y `lives_in` ('homeland'); people → y's language; people → hami(y). `dilVeInancBagla(people, epoch, note, {source: y})`. Note "Descended from <A>, <y> became a distinct people over generations."
5. **Sapience**: canon species with intelligence ≥ `LIFE.sapience_min_intelligence` not tagged `halk oldu`: skip if new peoples ≥ cap or `!chance(ENGINE.sapience_chance)`. `r = topRegion(t) || target of t's first active lives_in`. Record people subtype `akıllanan tür` (sapient species), name `"Lineage of <t>"`, power `max(min, t.power)`, location r, stats `{population: LIFE.sapient_population + d(die), martiality: clampi((t.power || LIFE.sapient_power_fallback) + d(LIFE.sapient_martial_die), 0, 100), magic: d(...), craft: d(...), faith: LIFE.sapient_faith + d(die)}`, description "[World engine] Among the <t> a branch arose that learned to speak, to make tools and to bury its dead; it is now a people." Bonds people → species `descends_from` ('sapience'); tag species `halk oldu`; if the species has a creator son → people `worships` it ('its creator'); `dilVeInancBagla(people, epoch, note)`; note "A branch that learned to speak arose among the <t>; it is now a people called <name>."

---

## 22. Writing systems (`yazilar(epoch, note)`)
For each canon language without a `yazi:` tag: speakers = canon sources of active `speaks` bonds; `writer` = first speaker that knows writing; need `chance(ENGINE.writing_chance)`. Weights with `k = toplumOf(writer).k`, language `L`:
```
alphabet    = LIFE.script_alphabet_base    + k.merchant / LIFE.script_alphabet_divisor
syllabary   = LIFE.script_syllabary_base   + L.complexity / LIFE.script_syllabary_divisor
pictographic= LIFE.script_pictographic_base+ L.sacredness / LIFE.script_pictographic_divisor
knot        = LIFE.script_knot_base        + k.farmer / LIFE.script_knot_divisor
notch       = LIFE.script_notch_base       + k.priest / LIFE.script_notch_divisor
```
Weighted pick → tag `yazi:<type>`; complexity = `clampi((complexity || LIFE.script_complexity_fallback) + LIFE.script_complexity_gain, 0, 100)`; note "<writer>'s scribes developed <an alphabet | a syllabary | a pictographic script | a knot script | a notch script> for the <L> language; words are now permanent."

## 22b. Belief and memory (`inancVeBellek(epoch, note)`)
1. **Legend spread**: each canon legend: `tellers` = active `celebrates`/`tells_of` bonds into it from canon entities; `spread = clampi((spread ?? LIFE.legend_spread_fallback) + tellers * LIFE.legend_teller_gain − LIFE.legend_decay, 0, 100)`.
2. **Traditions** older than `LIFE.tradition_grace`: `celebrants` = active bonds into it from canon entities where bond type is `celebrates` **or** the source is a community (any bond type). `y1 = clampi(y0 + (celebrants ? min(LIFE.tradition_celebrant_cap, celebrants) − 1 : (engine-made ? −LIFE.engine_tradition_decay : −LIFE.tradition_decay)), 0, 100)`. If `y1 ≤ LIFE.tradition_forget_spread` and no celebrants → `oldur(g, "Epoch <n>: no one left to celebrate it; forgotten.", closeBonds)`; note "The <g> tradition was forgotten; no one celebrates it any more." (One celebrant holds steady, two or more grow by 1.)
3. **Fairy tales forgotten**: legends tagged `masal` with `(spread || 0) ≤ LIFE.fairytale_forget_spread` and age ≥ `LIFE.fairytale_forget_age` → `oldur(… "Epoch <n>: its last teller died too; the tale was forgotten.", closeBonds)` (no note).
4. **Prophecies forgotten** (if `LIFE.prophecy_forget_age > 0`): canon prophecies older than that → `oldur(… "Epoch <n>: waited <age> epochs and was forgotten unfulfilled.", closeBonds)`; note "The <k> prophecy went unfulfilled for <age> epochs; no one knows it by heart any more."
5. **Manifestation** (belief changes reality): legends with spread ≥ `LIFE.manifestation_min_spread` not tagged `tezahür etti`, until `LIFE.manifestation_cap` and each `chance(ENGINE.manifestation_chance)`:
   - place = legend location, or target of its first active tells_of/related/inside bond that is a canon place/region/settlement; must be canon.
   - text = name + subtype + description → first matching rule:
     | Regex (Turkish keywords → English) | Creates | Subtype | Stats |
     |---|---|---|---|
     | monster, dragon, creature, serpent, wolf, giant, sleeps, guardian, hunter, claw, fang | species | creature from the legend | hp, power, agility, intelligence, danger = LIFE.manifest_creature_* base + d(die) |
     | spirit, ghost, shadow, dead, voice, whisper, echo | spirit | spirit born of belief | power, unrest |
     | spring, well, water, river, source, seed, crop | resource | hallowed resource | abundance, value, might |
     | (anything) | item | relic from the legend | damage d(), protection d(), might base+d(), curse d() |
     LANGUAGE-SPECIFIC: the Turkish regexes are substring matches without word boundaries (e.g. "su" water matches many words); in English use a keyword list with word boundaries or an explicit legend `category`.
   - record name `"Manifestation of <legend>"`, power `clampi(legend.power + LIFE.manifestation_power_bonus, LIFE.derived_power_min, LIFE.manifestation_power_max)`, location place, tag `inançtan doğdu`, description "[World engine] So many believed the legend of <e> for so long that what it told truly appeared in <place>." Bond new → legend `kaynagi` ('born of belief'); tag legend `tezahür etti`; note "So many believed the <e> legend that it became real in <place>: what was told is now there."
6. **Legendification**: events (canon or dead) older than `LIFE.legend_event_min_age` with violence ≥ `LIFE.legend_event_min_violence`, not yet the target of any `tells_of` bond, oldest first, until `LIFE.legendification_cap` with `chance(ENGINE.legendification_chance)` each: record legend subtype `bulanık hatıra` (blurred memory), name `"Tale of <event>"`, power `max(min, event.power − LIFE.legend_power_gap)`, stats `{spread: LIFE.legend_spread_base + d(LIFE.legend_spread_die)}`, tag `bozulmuş bellek`, description "[World engine] <event> of Epoch <n> became a legend through generations of retelling: details blurred, heroes grew, culprits changed, numbers were exaggerated." (no location). Bond legend → event `tells_of` ('distortingly'); note "<event> of Epoch <n> is now a legend no one fully remembers; every teller adds something."
7. **Fairy tales**: keepers = canon mortals with subtype sage|bard|seer|scribe|historian. Legends older than `LIFE.fairytale_min_age`, not tagged `masal`, with `(spread || 0) < LIFE.fairytale_spread`: skip if any keeper within `LIFE.fairytale_keeper_distance` (`mesafe`) or `!chance(ENGINE.fairytale_chance)`; tag `masal`; note "<e> is now only a fairy tale told to children; adults no longer believe it."

## 23. Life seeding (`yasamTohumu(epoch, note)`)
For each non-forgotten world: regions with fertility (?? default) ≥ `LIFE.life_min_fertility`; none → skip. `pickRegion()` = random among the top `LIFE.life_region_pick` regions by fertility. `emptyFor` = epochs without a people (`bosDunyalar`).
- No people and (`chance(ENGINE.native_people_chance)` or (`BOS.yerli_guvence > 0` and `emptyFor ≥ BOS.yerli_guvence`)) → record people subtype `yerli halk` (native people), name `"Natives of <region>"`, power `LIFE.native_people_power_level`, location region, tag `yerli`, stats population `LIFE.native_people_population + d(die)`, martiality/magic/craft `LIFE.native_people_stat + d(die)` each, faith `LIFE.native_people_faith + d(die)`, description "[World engine] In <world>, on the lands of <region>, a people no one created appeared: they were born of the earth itself, of the long patience of water and light." Note "A people appeared of its own accord in <world> (<region>)." Then `dilVeInancBagla`.
- No species and `chance(ENGINE.native_species_chance)` → record species subtype `yerli canlı` (native creature), name `"Creatures of <region>"`, power `LIFE.native_species_power_level`, tag `yerli`, stats hp/power/agility/intelligence/danger = LIFE.native_species_* base + d(die); description "[World engine] The first species stirred on the lands of <region> in <world>."; note "The first species appeared in <world>."
Fate will name these (pending records).

## 24. First language and first faith

- **`buyuklukEsigi(list, stat, pct, lo, hi)`** (relative threshold): per world, sort the stat values (missing = 0); threshold = `min(hi, max(lo, xs[min(len−1, floor(len*pct))] || 0))`. Returns `fn(v)` → threshold for v's world, else `hi`. (Small worlds still trigger events; big worlds approach the old absolute threshold.)
- **`enYakinDil(v)`** (nearest language): (1) location community's canon language; (2) language of each community v descends from; (3) among canon communities in the same world: count languages, weight `LIFE.language_region_weight` if same top region else 1; highest count wins (tie → lowest id).
- **`ilkelDil(v, epoch)`** (primitive language): root = first word of v's name; record language subtype `ilkel dil`, name `"<root> Language"` (Turkish "<root> Dili"), power 1, location v's location, stats spread/complexity/sacredness = LIFE.primitive_language_*, tag `ilkel`, description "[World engine] A language born among <v> from signs and first sounds, learned from no one."; set its world = v's world. Seed lexicon with 8 first words, meanings `[water, fire, earth, mother, sky, road, dead, bread]`: word = `adUret(lang, 'ilk:<i>', 'general')` or fallback `syllables[i % n] + ['a','u','en','ir','o','el','um','is'][i]` (from `hecele(root)`); insert into lexicon as noun with etymology "first sounds".
- **`ilkInancTanrisi(v)`** (god of first faith): for canon communities of v's world (≠ v) with a living patron: count worshippers per god, weight `LIFE.god_region_weight` if same top region else 1. `w(god) = count ^ (LIFE.first_faith_exponent/100)`; every **active** son whose active world is this world adds `LIFE.first_faith_son_weight`. Weighted pick among positive weights (ordered by id) → that son if alive. Fallback: the world's guardian son, else the first active son in the world; null if dead/none.
- **`dilVeInancBagla(v, epoch, note = noop, {source = null})`**:
  1. Not canon → return.
  2. No language: `L = speaks(source) || enYakinDil(v)`; if none/non-canon → `L = ilkelDil(v)` (new). Bond v → L `speaks` ('first sounds' if new else 'nearest language'); if new note "<v> began to speak its own primitive tongue."
  3. If v has any active worship bond (son, creator, foreign god) → return.
  4. `inherited` = hami(source) if alive. If none and `!chance(LIFE.first_faith_chance)` → return (stays a godlessness candidate; retried next epoch).
  5. `god = inherited || ilkInancTanrisi(v)`; if god → bond v → god `worships` ('first faith'); return.
  6. Else `chance(ENGINE.creator_first_faith_chance)` → `yaraticiyaTapin(v, 'first faith')`, note "<v> began praying directly to the creator in the sky."; else tag `tanrı arayışı`, note "<v> is seeking a god; they wait for someone to hear their prayers."

## 25. Ruin resettlement (`harabeyeKur(region, source, population, epoch, reason = 'migrants')`) → id | null
Find a dead settlement tagged `harabe`, not tagged `boşluk`, in the region's world (`region.world ?? source.world ?? 1`), located in the region or in a direct child of it; most recently died first, then id. If none → null. Restore: status canon, death epoch NULL, subtype = old subtype parsed from `"harabe (eski <X>)"` ("ruin (former X)") or kept or `'köy'` village; stats = old stats with population `max(LIFE.ruin_resettle_min_population, round(population))`, prosperity `LIFE.ruin_resettle_prosperity`, defence `max(LIFE.ruin_resettle_min_defence, round((defence ?? LIFE.ruin_defence_fallback)/LIFE.ruin_defence_divisor))`; fate note append "Epoch <n>: <reason> rebuilt the ruin."; tags −`harabe` +`yeniden kuruldu`; if source → bond ruin → source `descends_from` ('those who rebuilt the ruin'); `dilVeInancBagla(ruin, epoch, noop, {source})`. Old (closed) bonds are not restored.

## 26. Refugees (`multeciler(epoch, note)`)
- `defeated` = targets of `side`/`related` bonds described 'loser' made this epoch from siege/battle/war events.
- `disasterSites` = targets of `caused` bonds from events created this epoch tagged `afet` with violence ≥ `LIFE.refugee_disaster_violence`.
- For canon settlements/peoples with population ≥ `LIFE.refugee_min_population`, until `LIFE.refugee_cap`:
  - cause = "from war" if defeated; "from disaster" if v, v's location or v's top region is a disaster site; else skip. `chance(ENGINE.refugee_chance)`.
  - `n = round(pop * ENGINE.refugee_share/100)`; skip if `< LIFE.refugee_min_count`.
  - candidates: canon settlements/peoples in the same world, neighbours, not enemies of v, not defeated; score = ally·`refugee_weight_ally` + same language·`_language` + same god·`_god` + different top region·`_other_region`; sort desc, then id.
  - `v.pop −= n`. If best target → target.pop += n (unclamped); bond v → target `gocetti` ("refugees (<cause>): <n> people"); note "<n> refugees fleeing <cause> from <v> took shelter in <target>."
  - else: for neighbour regions of v's top region try `harabeyeKur(region, v, n, epoch, "refugees fleeing <cause> from <v>")`; none → restore n and continue (not counted); else bond to the ruin and note "<n> refugees fleeing <cause> from <v> settled the ruin of <ruin> and rebuilt it."
  - count++.

## 27. Spirits come to rest (`ruhlarDiner(epoch, note)`)
`deadWorld` = first non-forgotten world of type `olu` (land of the dead). For each canon engine-made spirit (`source='dunya'`) that is not a god shade:
1. `unrest = clampi((unrest ?? LIFE.spirit_unrest_fallback) − ENGINE.spirit_unrest_decay, 0, 100)` (saved).
2. `age = epoch − created`. If `age ≥ LIFE.spirit_rest_min_age && unrest < ENGINE.spirit_rest_threshold && chance(ENGINE.spirit_rest_chance)` → `oldur(r, "Epoch <n>: came to rest; no longer wanders.", closeBonds)`; rested++.
3. Else if deadWorld exists, spirit not in it, `age ≥ LIFE.spirit_crossing_min_age` and `chance(ENGINE.spirit_crossing_chance)` and the dead world has canon regions → move to a random one (location, clear map xy, refresh inside bond), tag `ölüler diyarına geçti`; crossed++.
4. Else group by location.
Per location over `ENGINE.spirits_per_place_cap`: sort by unrest asc then creation epoch asc; the excess (calmest, oldest) → `oldur(… "Epoch <n>: came to rest among the crowd of spirits.")`.
If anything happened: note "<n spirits came to rest><; ><n spirits crossed to <deadWorld>, the land of the dead>." (no ids).

## 28. Language death (`dilOlumu(epoch, note)`)
Canon languages older than `LIFE.language_death_grace`: `speakers` = active speaks bonds from canon entities.
- none and not tagged `ölü dil` → tag `ölü dil` (+ `çözülebilir` if it has a script); spread = 0; note (only the first `LIFE.language_death_note_cap` per epoch) "<L> is now a dead language: no one is left who speaks it<; its script waits in the ruins to be read>."
- speakers and tagged dead → remove both tags; note "<L> is spoken again."

## 29. Engine-built works (`yapitlar(epoch, note)`)
`prosperityOf(v) = prosperity ?? (people ? LIFE.work_people_prosperity_base + round(craft/LIFE.work_people_craft_divisor) : 0)`.

Work types (first matching in this order, and no existing work of the same kind at the site):
| Kind | Subtype | Name suffix | Condition | Effect | Existing-match regex (LANGUAGE-SPECIFIC) |
|---|---|---|---|---|---|
| temple | tapınak | "Temple" | has patron && faith (?? default) ≥ `LIFE.temple_min_faith` && priest share ≥ `LIFE.temple_min_priest_share` | faith += `LIFE.temple_faith_gain` | temple\|sanctuary\|altar |
| walls | sur | "Walls" | settlement && ((defence ?? `LIFE.wall_defence_fallback`) < `LIFE.wall_build_threshold` \|\| at war) | defence += `LIFE.wall_defence_gain` | wall\|castle\|rampart\|tower |
| library | kütüphane | "Library" | scribe share ≥ `LIFE.library_min_scribe_share` \|\| knows writing | none | knowledge-keeper regex (§15) |

Steps: for canon (settlement with pop ≥ `LIFE.work_town_min_population` or people with pop ≥ `LIFE.work_people_min_population`) with `prosperityOf ≥ ENGINE.work_min_prosperity`, until `ENGINE.work_cap`:
- `craftOK = artisan share ≥ LIFE.work_min_artisan_share || craft ≥ LIFE.work_min_craft || knows architecture`; need `craftOK && chance(ENGINE.work_chance)`.
- site = v if settlement else v's location; existing = canon works at site or built by v; at war = any enemy bond.
- choose kind; record work name `"<dildenAd(v, seed, 'place') || v> <suffix>"`, power `clampi(round(v.power * LIFE.work_power_share/100) + 1, LIFE.derived_power_min, LIFE.work_power_max)`, location site, stats splendour `LIFE.work_splendour_base + d(die) + (architecture ? LIFE.work_architecture_bonus : 0)`, durability `base + d(die)`, function `base + d(die)`; description "[World engine] The masters of prosperous <v> built a <subtype>." Bond v → work `insa_etti`. Effect; prosperity −= `LIFE.work_prosperity_cost`; goods `= clampi((goods ?? LIFE.work_goods_fallback) − LIFE.work_goods_cost, 0, SOC.storage_cap)`; note "The masters of <v> built a <subtype>."

**Splendour growth**: each canon work with splendour < 100: owner = location if canon community else the first (by id) source of active built/owns/rules bond; must be a canon community with `prosperityOf ≥ LIFE.splendour_min_owner_prosperity`; `splendour = clampi((splendour ?? LIFE.splendour_fallback) + ENGINE.splendour_growth + (artisan share ≥ LIFE.splendour_artisan_share ? LIFE.splendour_artisan_bonus : 0) + (architecture ? LIFE.splendour_architecture_bonus : 0), 0, 100)`. This is how works cross the wonder threshold (80).

## 30. Factions (`hizipler(epoch, note)`)
**Disband uprisings**: canon factions that are uprisings (subtype rebels/uprising or `sinif:` tag) older than `LIFE.uprising_disband_min_age`: skip if any active enemy bond or `!chance(ENGINE.uprising_disband_chance)`; `oldur(h, "Epoch <n>: the uprising died out; the rebels dispersed or melted back into the people.", closeBonds)`; note (first `LIFE.uprising_disband_note_cap` only) "<h> died out; the rebels buried their weapons and went home."

**Found factions** — for canon settlements/peoples with pop ≥ `LIFE.faction_min_population`, until `ENGINE.faction_cap`, each needing `chance(ENGINE.faction_chance)`; first matching kind without an existing canon faction tagged `hizip:<kind>:<v>`:
| Kind | Subtype | Name suffix | Condition | Base stats (power, wealth, influence) |
|---|---|---|---|---|
| guild (`lonca`) | merchant guild | "Guild" | merchant ≥ `LIFE.guild_min_merchant_share` && trade routes > 0 && prosperity (?? 0) ≥ `LIFE.guild_min_prosperity` | `LIFE.guild_power/wealth/influence` |
| council (`meclis`) | priests' council | "Priests' Council" | priest ≥ `LIFE.council_min_priest_share` && has patron | `LIFE.council_*` |
| brotherhood (`birlik`) | warrior brotherhood | "Warrior Brotherhood" | warrior ≥ `LIFE.brotherhood_min_warrior_share` \|\| (at war && warrior ≥ `LIFE.brotherhood_war_warrior_share`) | `LIFE.brotherhood_*` |
Record faction name `"<dildenAd(v, seed, 'people') || v> <suffix>"`, power `clampi(round(v.power * LIFE.faction_power_share/100) + 1, LIFE.derived_power_min, LIFE.faction_power_max)`, location, tag `hizip:<kind>:<v>`, each stat `clampi(base + d(LIFE.faction_stat_die) − LIFE.faction_stat_shift, 0, 100)`, description "[World engine] The <merchants | priests | warriors> of <v> organised among themselves." Bond faction → v `descends_from` ('born from within'); `dilVeInancBagla(faction, epoch, noop, {source: v})`; note "A <subtype> was founded in <v>."

## 31. Religion spread (`dinYayilimi(epoch, note)`)
- `worshipCount[god]` = canon communities worshipping each son; `total` = sum.
- **`baskinlikCarpani(sharePct)`** = `sharePct ≤ ENGINE.dominant_god_threshold ? 1 : max(0, (100 − sharePct) / max(1, 100 − threshold))`; `dominance(god) = baskinlikCarpani(total ? count/total*100 : 0)`.
- `cults` = canon cults with a living patron.
- For each canon people/settlement until both counters (conversions, syncretisms) ≥ `ENGINE.conversion_cap`:
  - `old = hami(v)`; `seeker = !old || tagged god-seeking || godless`.
  - sources: each cult in the same world and neighbouring (patron ≠ old): `p = LIFE.preaching_base/100 + cult.influence/LIFE.preaching_influence_divisor + min(LIFE.preaching_followers_max/100, cult.followers / max(LIFE.preaching_followers_floor, v.population * LIFE.preaching_population_mult))`, reason "through the sermons of <cult>". If seeker: each neighbouring canon people/settlement in the same world with a living patron ≠ old: `p = ENGINE.seeker_pull/100`, reason "from its neighbour <x>".
  - none → continue.
  - best = max over sources of `clampf(p + (god.fame − (old?.fame ?? 0))/LIFE.conversion_fame_divisor + (seeker ? LIFE.conversion_seeker_bonus/100 : 0), 0, ENGINE.conversion_chance_cap/100) * dominance(god)`.
  - `chance(best.p)` else continue. `syncretic = old && !seeker && chance(ENGINE.syncretism_chance)`; skip if that counter is full.
  - `dinDegistir(v, god, epoch, reason, {syncretic})`; if not syncretic, update worship counts (+1 new, −1 old).
  - notes: syncretic "<v> began making offerings to <god> too, without abandoning <old> (syncretism)."; conversion "<v> converted to the faith of <god> <reason><; the altars of <old> grew cold>." ids [v].

## 32. Cultural exchange
- `oduncKelime(A, B, epoch)` (loanword): both have languages and they differ; candidates = A's lexicon words not in B's lexicon (case-insensitive); random one inserted into B's lexicon with etymology "borrowed from the <A language> language", added by B. Returns `{word, language: B's}`.
- **`kulturTemasi(A, B, epoch, note, {first = false})`** (A influences B) — percent tunables with first-contact / trade variants:
  1. `chance(first ? LIFE.culture_first_word : LIFE.culture_word)` → loanword → "<B lang> borrowed the word "<w>"".
  2. A's celebrated canon traditions that B does not celebrate; `chance(first ? culture_first_tradition : culture_tradition)` → bond B → tradition `celebrates` ("passed from <A>") → "<B> adopted the <g> tradition".
  3. A's knowledge that B lacks (and, unless first contact, in B's world); `chance(first ? culture_first_knowledge : culture_knowledge)` → `ogret(B, k, "in contact with <A>")` → "the <k> knowledge passed to <B>".
  4. A's god alive and ≠ B's god; `chance(first ? culture_first_god : culture_god)` and `dinDegistir(B, godA, epoch, "contact with <A>", {syncretic: B has a god})` → "<B> began making offerings to <godA> too" / "<B> began to worship <godA>".
  If anything happened: note "Cultural exchange between <A> and <B>: <items joined by '; '>." Returns count.
- **`kulturAlisverisi(epoch, note)`**: active trade bonds by id, until `ENGINE.culture_exchange_cap` successful exchanges: both canon communities, `chance(ENGINE.culture_exchange_chance)`; direction random 50/50; `kulturTemasi(x, y, epoch, note)`; count if > 0.

## 33. World age (`dunyaYasi(newEpoch, notes)`) → `{altin, donum}`
`write(text, ids)` = chronicle kind `dunya_yasi` + push notes.
1. If `newEpoch % ENGINE.epoch_turning_interval == 0`: `donum += ENGINE.epoch_turning_doom_relief`; "Epoch turning: the world entered its <n>th epoch. The seers closed the old accounts; fears subsided for a while."
2. For each non-forgotten world: `age = newEpoch − (created || 1)`; if `age > 0 && age % ENGINE.world_age_step == 0`: `donum += LIFE.world_age_doom_relief`; "<world> is <age> epochs old: its mountains have worn down, its rivers have changed their beds; it is an old world now."
3. `ts` = canon peoples/settlements of the world; none → skip.
4. `warNow` = any active enemy bond between canon communities whose **source** is in this world. `recentWar` = any war event in the world that is ongoing or ended after `newEpoch − ENGINE.golden_age_peace`. `avgProsperity` over communities that have it (default `SOC.default_stat`).
5. `golden = !warNow && !recentWar && avg ≥ ENGINE.golden_age_prosperity && age ≥ LIFE.golden_age_min_world_age`; `inGolden` = any community tagged `altın çağ`.
6. golden → `altin++`; tag all ts `altın çağ`; each with prosperity `refahEkle(+LIFE.golden_age_prosperity_gain)`; if newly entered: write "<world> entered a golden age: wars are forgotten, granaries are full, masters are doing their finest work." linking the first `LIFE.golden_age_chronicle_links` communities. Else if inGolden → remove tags; "<world>'s golden age has ended."
`altin` counts worlds **currently** in a golden age (every epoch), used by sim.js as doom relief `−KY.altin_cag * altin`; `donum` is subtracted directly from the doom clock.

---

## 34. Tunables (all balance numbers of this module)

Every number is a world rule editable in *Settings → World rules* (`tanimla(group, {key: [default, label, min, max, uiGroup]})`). Stored overrides live in `dunya.denge_ayar` (JSON `{ "GROUP.key": value }`); values are integers; `min` is enforced structurally, `max` is only a recommended upper bound (UI warning). Percent keys (`*_chance`, `*_share`, `*_pct`, multipliers marked %) are divided by 100 at use. Suggested English group names are given; the "Original key" column allows tracing.

Notes on ownership:
- `DERIN` keys `cult_population_share` (`tarikat_oran`), `young_world_epochs` (`genc_dunya`), `hero_population_percentile` (`kahraman_yuzde`), `famine_migration_share` (`kitlik_goc_pay`), `spirits_per_place_cap` (`ruh_tavan`, also used here) are consumed by sim.js / korku.js. `world_war_cap` is also read by yaratici.js.
- `DERIN_YASAM` resurrection keys are also read by olum.js, mudahale.js, oyuncu.js, tools.js, firsatlar.js; `life_min_fertility` by bosdunya.js.
- `DERIN_ILISKI.olu_bag_not` (`dead_bond_note_threshold`) is **defined but never used**.

#### Rule group `DERIN` → suggested `deep_engine` (125 keys)

| English key | Original key | Default | Min | Max | UI group | Label |
|---|---|---|---|---|---|---|
| `battle_record_power_gap` | `muharebe_kayit_fark` | 30 | 0 | 1000 | War & diplomacy | Power gap required for a battle to get its own record (sieges always get one) |
| `spy_network_enemy_bonus` | `casus_ag_dusman_ek` | 20 | 0 | 100 | War & diplomacy | Bonus chance (%) to found a spy network against an enemy or a tribute partner |
| `grudge_threshold` | `kin_esik` | -60 | -100 | 0 | War & diplomacy | Neighbours with relation at or below this may declare war |
| `peace_threshold` | `baris_esik` | -15 | -100 | 100 | War & diplomacy | Enemies with relation at or above this may make peace |
| `alliance_threshold` | `ittifak_esik` | 55 | 0 | 100 | War & diplomacy | Neighbours with relation at or above this may ally |
| `war_declaration_cap` | `ilan_tavan` | 2 | 0 | 20 | War & diplomacy | Max war declarations per epoch |
| `peace_cap` | `baris_tavan` | 3 | 0 | 20 | War & diplomacy | Max neighbour peaces per epoch (by oath or truce) |
| `exhaustion_peace_cap` | `yorgunluk_baris_tavan` | 3 | 0 | 20 | War & diplomacy | Max exhaustion peaces per epoch (long wars; counted separately from neighbour peace) |
| `grudge_fade_relation` | `kin_sonme_iliski` | 0 | -100 | 100 | War & diplomacy | Fading grudge: hostility closes if relation rose to at least this and there is no ongoing war |
| `grudge_fade_min_age` | `kin_sonme_cag` | 3 | 0 | 100 | War & diplomacy | Fading grudge: minimum age of the hostility (epochs) |
| `grudge_forget_age` | `kin_unutma_cag` | 12 | 0 | 1000 | War & diplomacy | Forgotten grudge: hostility that lasted this many epochs without fighting closes even if relation is bad (0 = off) |
| `grudge_fade_cap` | `kin_sonme_tavan` | 6 | 0 | 1000 | War & diplomacy | Max faded grudges per epoch |
| `grudge_pool_pct` | `kin_havuz` | 300 | 100 | 10000 | War & diplomacy | Grudge pool: when hostile community pairs exceed this % of the world war cap, old grudges lock diplomacy; the excess raises the fade cap |
| `grudge_overflow_share` | `kin_asim_pay` | 25 | 0 | 1000 | War & diplomacy | Share (%) of pairs above the grudge pool added to the per-epoch grudge-fade cap |
| `truce_without_war` | `savassiz_ateskes` | 0 | 0 | 1 | War & diplomacy | Whether closing hostility between two communities that never fought writes a truce (1 yes, 0 no; pairs who fought always get a truce) |
| `mortal_grudge_forget_age` | `olumlu_kin_unutma_cag` | 8 | 0 | 1000 | War & diplomacy | A mortal's hostility (with a mortal or community) is forgotten after this many epochs with no new encounter (0 = off) |
| `alliance_cap` | `ittifak_tavan` | 2 | 0 | 20 | War & diplomacy | Max alliances per epoch |
| `community_war_cap` | `topluluk_savas_tavan` | 2 | 0 | 10 | War & diplomacy | Max simultaneous ongoing wars (war events) for one community |
| `battle_cap` | `muharebe_tavan` | 6 | 0 | 50 | War & diplomacy | Max battles per epoch (in ongoing wars; a new war's first clash counts against new_war_cap) |
| `mobilization` | `seferberlik` | 1 | 0 | 1 | War & diplomacy | First epoch of a new war is mobilisation; first clash is next epoch (1 on, 0 clash in declaration epoch) |
| `new_war_cap` | `yeni_savas_tavan` | 3 | 0 | 50 | War & diplomacy | Max new wars per epoch (from hostile pairs; only under the war caps) |
| `battle_chance` | `muharebe_sans` | 70 | 0 | 100 | War & diplomacy | Enemies clash this epoch (%) |
| `battle_chance_under_ban` | `muharebe_yasak_sans` | 35 | 0 | 100 | War & diplomacy | Clash chance while a war-ban law is in force (%) |
| `notable_min_population` | `unlu_nufus` | 800 | 0 | 1000000 | Heroes & mortals | Minimum population of a community that produces notable mortals |
| `notable_chance` | `unlu_sans` | 45 | 0 | 100 | Heroes & mortals | Base chance (%) that a populous community produces a notable mortal |
| `notable_cap` | `unlu_tavan` | 8 | 0 | 100 | Heroes & mortals | Max notable mortals born per epoch |
| `ruler_cap` | `hukumdar_tavan` | 2 | 0 | 50 | Heroes & mortals | Max rulers taking the throne per epoch |
| `ruler_min_population` | `hukumdar_nufus` | 800 | 0 | 1000000 | Heroes & mortals | Minimum population of a community that gets a ruler |
| `ethnogenesis_min_population` | `etnogenez_nufus` | 3000 | 0 | 10000000 | Population & growth | Minimum population of a settlement that becomes a new people |
| `ethnogenesis_min_age` | `etnogenez_cag` | 3 | 0 | 100 | Population & growth | Age (epochs) required to become a new people |
| `world_war_cap` | `savas_tavan` | 6 | 0 | 50 | War & diplomacy | Max simultaneous ongoing community wars in the world (war events; hostility bonds fade separately) |
| `truce_duration` | `ateskes_cag` | 3 | 0 | 20 | War & diplomacy | Truce duration after peace (epochs) |
| `tribute_duration` | `harac_cag` | 4 | 1 | 30 | War & diplomacy | Tribute duration (epochs) |
| `tribute_flow` | `harac_akis` | 2 | 0 | 20 | War & diplomacy | Prosperity and wealth transferred per epoch by tribute |
| `tribute_goods_share` | `harac_mal` | 15 | 0 | 100 | War & diplomacy | Share (%) of goods transferred by tribute |
| `tribute_revolt_power_ratio` | `harac_isyan_guc` | 125 | 100 | 500 | War & diplomacy | Power ratio (%) a tributary needs to revolt |
| `conquest_conversion_chance` | `fetih_din_sans` | 45 | 0 | 100 | Religion & language | Chance (%) the conquered converts to the victor's god |
| `tribute_conversion_chance` | `harac_din_sans` | 20 | 0 | 100 | Religion & language | Chance (%) a tributary converts to the victor's god |
| `spirits_per_place_cap` | `ruh_tavan` | 3 | 0 | 30 | Beyond (afterlife) | Max wandering spirits in one place |
| `spirit_unrest_decay` | `ruh_sonme` | 3 | 0 | 50 | Beyond (afterlife) | Spirit unrest decay per epoch |
| `spirit_rest_threshold` | `ruh_dinme_esik` | 40 | 0 | 100 | Beyond (afterlife) | Spirits below this unrest may come to rest |
| `cult_population_share` | `tarikat_oran` | 30 | 1 | 100 | Population & growth | Cap on cult followers: % of region population |
| `young_world_epochs` | `genc_dunya` | 6 | 0 | 50 | Cosmic horror | Young-world duration (epochs; leak growth is halved) |
| `hero_population_percentile` | `kahraman_yuzde` | 80 | 0 | 100 | Heroes & mortals | Percentile of communities that produce heroes (top X% most populous) |
| `dark_age_prosperity` | `karanlik_refah` | 12 | 0 | 100 | Civilisation | Prosperity below this counts as devastation (dark age) |
| `dark_age_forget_chance` | `karanlik_sans` | 30 | 0 | 100 | Civilisation | Chance (%) that knowledge is forgotten after devastation |
| `dark_age_protected_forget_chance` | `karanlik_korunan_sans` | 5 | 0 | 100 | Civilisation | Forget chance (%) when scribes or a library exist |
| `exhaustion_start` | `yorgunluk_bas` | 3 | 1 | 30 | War & diplomacy | Epoch of a long war at which exhaustion peace starts |
| `exhaustion_growth` | `yorgunluk_artis` | 10 | 0 | 100 | War & diplomacy | Per-epoch increase of exhaustion-peace chance (%) |
| `exhaustion_chance_cap` | `yorgunluk_tavan` | 50 | 0 | 100 | War & diplomacy | Cap of exhaustion-peace chance (%) |
| `exhaustion_victory_margin` | `yorgunluk_ustunluk` | 2 | 1 | 50 | War & diplomacy | Minimum score advantage to count as victor in an exhaustion peace (below: white peace) |
| `village_first_population` | `koy_ilk_nufus` | 600 | 50 | 100000 | Population & growth | Population at which a people founds its first homeland |
| `village_extra_population` | `koy_ek_nufus` | 1500 | 100 | 1000000 | Population & growth | Population at which a people founds additional villages |
| `village_min_population` | `koy_en_az` | 150 | 10 | 10000 | Population & growth | Minimum population of a new village |
| `village_people_remaining` | `koy_kalan` | 300 | 10 | 100000 | Population & growth | Minimum population left in the people after founding a village |
| `village_per_population` | `koy_basina` | 15000 | 1000 | 1000000 | Population & growth | One village per this many people in the region |
| `ruin_threshold` | `harabe_esik` | 60 | 0 | 10000 | Population & growth | A settlement below this population is abandoned |
| `ruin_grace` | `harabe_mehil` | 2 | 0 | 20 | Population & growth | Epochs a new settlement takes root before it can be abandoned |
| `fertility_recovery_divisor` | `bereket_toparlanma` | 8 | 1 | 100 | Population & growth | Speed of depleted soil returning to 50 (divisor) |
| `fertility_decline_divisor` | `bereket_inis` | 10 | 1 | 200 | Population & growth | Speed of fertile soil sinking to 50 (divisor; balanced by climate push: ~60 in temperate, ~90 in rain) |
| `work_cap` | `yapit_tavan` | 2 | 0 | 20 | Civilisation | Max works (buildings) the engine builds per epoch |
| `work_min_prosperity` | `yapit_refah` | 50 | 0 | 100 | Civilisation | Prosperity required to build a work |
| `splendour_growth` | `ihtisam_artis` | 2 | 0 | 50 | Civilisation | Per-epoch splendour added to a prosperous owner's work |
| `faction_cap` | `hizip_tavan` | 1 | 0 | 10 | Civilisation | Max spontaneously founded factions per epoch |
| `conversion_cap` | `din_gecis_tavan` | 1 | 0 | 10 | Religion & language | Max communities changing religion per epoch |
| `seeker_pull` | `arayan_cekim` | 12 | 0 | 100 | Religion & language | Chance (%) a god-seeking community converts to a neighbour's god |
| `conversion_chance_cap` | `din_sans_tavan` | 30 | 0 | 100 | Religion & language | Cap of a religion-change probability (%) |
| `dominant_god_threshold` | `din_baskin_esik` | 30 | 0 | 100 | Religion & language | Dominant god: if more than this % of worshipping communities follow one god, conversion chance to it shrinks with its share (to zero at 100%) |
| `culture_exchange_cap` | `kultur_tavan` | 2 | 0 | 20 | Religion & language | Max cultural exchanges per epoch |
| `golden_age_prosperity` | `altin_refah` | 50 | 0 | 100 | Doom | Average prosperity required for a golden age |
| `golden_age_peace` | `altin_baris` | 4 | 0 | 50 | Doom | Epochs without war required for a golden age |
| `epoch_turning_interval` | `cag_donumu` | 10 | 1 | 1000 | Doom | Epoch turning every N epochs |
| `epoch_turning_doom_relief` | `cag_donumu_kiyamet` | 5 | 0 | 100 | Doom | How much an epoch turning pushes the doom clock back |
| `world_age_step` | `dunya_yasi_adim` | 25 | 1 | 1000 | Doom | World ageing threshold (epochs) |
| `refugee_share` | `multeci_pay` | 8 | 0 | 100 | Population & growth | Refugee share of population (%) |
| `famine_migration_share` | `kitlik_goc_pay` | 15 | 0 | 100 | Population & growth | Famine migration share of population (%) |
| `war_declaration_chance` | `savas_ilan_sans` | 25 | 0 | 100 | War & diplomacy | Grudge turns into a war declaration (%) |
| `peace_chance` | `baris_sans` | 30 | 0 | 100 | War & diplomacy | Softened relation turns into peace (%) |
| `alliance_chance` | `ittifak_sans` | 20 | 0 | 100 | War & diplomacy | Friendly neighbours become allies (%) |
| `marriage_alliance_chance` | `evlilik_ittifak_sans` | 40 | 0 | 100 | War & diplomacy | Share (%) of alliances made by marriage |
| `betrayal_chance` | `ihanet_sans` | 30 | 0 | 100 | War & diplomacy | Betrayal in a souring alliance (%) |
| `betrayal_war_chance` | `ihanet_savas_sans` | 50 | 0 | 100 | War & diplomacy | Betrayal turns into war (%) |
| `duel_chance` | `duello_sans` | 30 | 0 | 100 | War & diplomacy | Heroes duel during a battle (%) |
| `duel_death_chance` | `duello_olum_sans` | 45 | 0 | 100 | War & diplomacy | Duel ends in death (%) |
| `capture_chance` | `esir_sans` | 20 | 0 | 100 | War & diplomacy | A hero of the loser is captured (%) |
| `war_exhaustion_chance` | `savas_yorgunluk_sans` | 25 | 0 | 100 | War & diplomacy | Exhaustion peace after four battles (%) |
| `conquest_syncretism_share` | `senkretizm_fetih` | 35 | 0 | 100 | Religion & language | Share (%) of conquest conversions that are syncretic |
| `tribute_revolt_chance` | `harac_isyan_sans` | 40 | 0 | 100 | War & diplomacy | A strengthened tributary revolts (%) |
| `ransom_chance` | `fidye_sans` | 40 | 0 | 100 | War & diplomacy | A rich homeland pays ransom (%) |
| `execution_chance` | `idam_sans` | 25 | 0 | 100 | War & diplomacy | A blood-feud captor executes the prisoner (%) |
| `prisoner_turncoat_chance` | `esir_donme_sans` | 30 | 0 | 100 | War & diplomacy | After long captivity the prisoner changes sides (%) |
| `weapon_forging_chance` | `silah_uretim_sans` | 20 | 0 | 100 | Economy | A forge makes weapons (%) |
| `guild_bankruptcy_chance` | `lonca_iflas_sans` | 18 | 0 | 100 | Economy | A merchant guild goes bankrupt (%) |
| `class_uprising_chance` | `sinif_ayaklanma_sans` | 22 | 0 | 100 | War & diplomacy | A discontented class rises up (%) |
| `quest_chance` | `gorev_sans` | 35 | 0 | 100 | Heroes & mortals | A hero sets out on a new quest (%) |
| `companion_chance` | `yoldas_sans` | 10 | 0 | 100 | Heroes & mortals | Two heroes of the same side become companions (%) |
| `apprentice_chance` | `cirak_sans` | 30 | 0 | 100 | Heroes & mortals | An ageing hero trains an apprentice (%) |
| `weapon_bequest_chance` | `silah_emanet_sans` | 50 | 0 | 100 | Heroes & mortals | Master hands their weapon to the apprentice (%) |
| `quest_death_chance` | `gorev_olum_sans` | 25 | 0 | 100 | Heroes & mortals | Death on a failed quest (%) |
| `relic_rediscovery_chance` | `kalinti_bulma_sans` | 12 | 0 | 100 | Heroes & mortals | Scribes decode lost knowledge from ruins (%) |
| `spy_network_chance` | `casus_ag_sans` | 20 | 0 | 100 | War & diplomacy | An influential faction founds a spy network (%) |
| `spy_war_chance` | `casus_savas_sans` | 30 | 0 | 100 | War & diplomacy | Caught spies lead to war (%) |
| `spy_action_chance` | `casus_eylem_sans` | 40 | 0 | 100 | War & diplomacy | A spy network acts this epoch (%) |
| `spy_steal_share` | `casus_bilgi_sans` | 50 | 0 | 100 | War & diplomacy | Share (%) of spy actions that steal knowledge (else sabotage) |
| `wonder_envy_war_chance` | `harika_kiskanc_sans` | 5 | 0 | 100 | War & diplomacy | A jealous neighbour goes to war over a wonder (%) |
| `apostasy_chance` | `inkar_sans` | 50 | 0 | 100 | Religion & language | A worshipper of a dead god falls into denial (%) |
| `resurrection_chance` | `dirilis_sans` | 50 | 0 | 100 | Religion & language | A devoted cult resurrects its god (%) |
| `ruler_chance` | `hukumdar_sans` | 50 | 0 | 100 | Heroes & mortals | A ruler takes over a leaderless community (%) |
| `ethnogenesis_chance` | `etnogenez_sans` | 20 | 0 | 100 | Population & growth | A detached settlement becomes a new people (%) |
| `sapience_chance` | `akillanma_sans` | 12 | 0 | 100 | Population & growth | An intelligent species becomes a people (%) |
| `writing_chance` | `yazi_sans` | 50 | 0 | 100 | Religion & language | A language whose speakers know writing gains a script (%) |
| `manifestation_chance` | `tezahur_sans` | 10 | 0 | 100 | Religion & language | A widespread legend becomes real (%) |
| `legendification_chance` | `efsanelesme_sans` | 25 | 0 | 100 | Religion & language | An old violent event turns into a legend (%) |
| `fairytale_chance` | `masal_sans` | 15 | 0 | 100 | Religion & language | An old legend turns into a fairy tale (%) |
| `native_people_chance` | `yerli_halk_sans` | 20 | 0 | 100 | Population & growth | A native people appears in a world without peoples (%) |
| `native_species_chance` | `yerli_tur_sans` | 25 | 0 | 100 | Population & growth | A species appears in a world without species (%) |
| `creator_first_faith_chance` | `yaratici_ilk_inanc` | 50 | 0 | 100 | Religion & language | A godless new people worships the creator (else seeks a god) (%) |
| `refugee_chance` | `multeci_sans` | 40 | 0 | 100 | Population & growth | Refugee migration after war or disaster (%) |
| `spirit_rest_chance` | `ruh_dinme_sans` | 30 | 0 | 100 | Beyond (afterlife) | A calm spirit comes to rest (%) |
| `spirit_crossing_chance` | `ruh_gecis_sans` | 12 | 0 | 100 | Beyond (afterlife) | A spirit crosses to the land of the dead (%) |
| `work_chance` | `yapit_sans` | 25 | 0 | 100 | Civilisation | A prosperous town builds a work (%) |
| `uprising_disband_chance` | `isyan_dagilma_sans` | 50 | 0 | 100 | War & diplomacy | An uprising whose war has ended disbands (%) |
| `faction_chance` | `hizip_sans` | 15 | 0 | 100 | Civilisation | A faction forms inside a community (%) |
| `syncretism_chance` | `senkretizm_sans` | 40 | 0 | 100 | Religion & language | Share (%) of religion changes that are syncretic |
| `culture_exchange_chance` | `kultur_sans` | 12 | 0 | 100 | Religion & language | Cultural exchange along a trade route (%) |

#### Rule group `DERIN_ILISKI` → suggested `deep_relations` (33 keys)

| English key | Original key | Default | Min | Max | UI group | Label |
|---|---|---|---|---|---|---|
| `record_power_level` | `kayit_guc` | 3 | 1 | 12 | Chronicle | Default power level of records the engine opens |
| `dead_bond_note_threshold` | `olu_bag_not` | 20 | 1 | 100000 | Chronicle | If this many dead bonds close at epoch end, note in chronicle (UNUSED in code) |
| `relation_history_length` | `iliski_gecmis` | 12 | 1 | 500 | Chronicle | Number of recent events kept in a community relation |
| `relation_decay_threshold` | `iliski_sonme_esik` | 50 | 0 | 100 | War & diplomacy | Mean reversion: relations beyond this (±) decay each epoch |
| `relation_decay_share` | `iliski_sonme_pay` | 25 | 0 | 100 | War & diplomacy | Mean reversion: share (%) of the excess beyond the threshold removed per epoch (0 disables) |
| `neighbour_distance` | `komsu_mesafe` | 3 | 0 | 20 | War & diplomacy | Max distance (steps) at which two communities with unknown map count as neighbours |
| `initial_shared_god` | `ilk_ortak_tanri` | 20 | 0 | 100 | War & diplomacy | Initial relation: bonus for worshipping the same god |
| `initial_different_god` | `ilk_farkli_tanri` | 5 | 0 | 100 | War & diplomacy | Initial relation: penalty for worshipping different gods |
| `initial_shared_language` | `ilk_ortak_dil` | 15 | 0 | 100 | War & diplomacy | Initial relation: bonus for speaking the same language |
| `initial_enemy` | `ilk_dusman` | 50 | 0 | 100 | War & diplomacy | Initial relation: penalty for hostility |
| `initial_ally` | `ilk_muttefik` | 45 | 0 | 100 | War & diplomacy | Initial relation: bonus for alliance |
| `initial_trade` | `ilk_ticaret` | 20 | 0 | 100 | War & diplomacy | Initial relation: bonus for trade |
| `initial_tribute` | `ilk_harac` | 15 | 0 | 100 | War & diplomacy | Initial relation: penalty for tribute |
| `blood_feud_penalty` | `kan_davasi` | 30 | 0 | 200 | War & diplomacy | Relation points removed by a blood feud |
| `exhaustion_peace_relation` | `yorgunluk_baris_iliski` | 15 | 0 | 100 | War & diplomacy | Relation bonus from an exhaustion peace |
| `drift_shared_god` | `kayma_ortak_tanri` | 2 | 0 | 50 | War & diplomacy | Per-epoch drift: shared god bonus |
| `drift_cult_other_god` | `kayma_tarikat_tanri` | 2 | 0 | 50 | War & diplomacy | Per-epoch drift: penalty when a cult has a different god |
| `drift_shared_language` | `kayma_ortak_dil` | 1 | 0 | 50 | War & diplomacy | Per-epoch drift: shared language bonus |
| `drift_trade` | `kayma_ticaret` | 3 | 0 | 50 | War & diplomacy | Per-epoch drift: trade bonus |
| `drift_ally` | `kayma_muttefik` | 2 | 0 | 50 | War & diplomacy | Per-epoch drift: alliance bonus |
| `drift_enemy` | `kayma_dusman` | 3 | 0 | 50 | War & diplomacy | Per-epoch drift: hostility penalty |
| `drift_tribute` | `kayma_harac` | 2 | 0 | 50 | War & diplomacy | Per-epoch drift: tribute penalty |
| `drift_blood_feud` | `kayma_kan_davasi` | 3 | 0 | 50 | War & diplomacy | Per-epoch drift: blood feud penalty |
| `neighbour_exhaustion_start` | `komsu_yorgunluk_cag` | 2 | 0 | 50 | War & diplomacy | War age (epochs) at which exhaustion peace starts for neighbouring enemies |
| `neighbour_exhaustion_growth` | `komsu_yorgunluk_artis` | 12 | 0 | 100 | War & diplomacy | Per-epoch increase of exhaustion-peace chance for neighbouring enemies (%) |
| `neighbour_exhaustion_cap` | `komsu_yorgunluk_tavan` | 60 | 0 | 100 | War & diplomacy | Cap of exhaustion-peace chance for neighbouring enemies (%) |
| `peace_relation` | `baris_iliski` | 10 | 0 | 100 | War & diplomacy | Relation bonus from peace |
| `marriage_min_age` | `evlilik_yas` | 16 | 0 | 200 | Heroes & mortals | Minimum age (years) of a hero who can enter a marriage alliance |
| `default_hero_age` | `varsayilan_yas` | 30 | 0 | 200 | Heroes & mortals | Age (years) assumed for a hero of unknown age |
| `marriage_relation` | `evlilik_iliski` | 10 | 0 | 100 | War & diplomacy | Relation bonus from a marriage alliance |
| `betrayal_cap` | `ihanet_tavan` | 1 | 0 | 20 | War & diplomacy | Max betrayals per epoch |
| `betrayal_default_power` | `hain_guc_varsayilan` | 40 | 0 | 100 | War & diplomacy | Power assumed for a side of unknown influence/power in a betrayal |
| `betrayal_relation` | `ihanet_iliski` | 30 | 0 | 200 | War & diplomacy | Relation points removed by betrayal |

#### Rule group `DERIN_SEFER` → suggested `deep_campaign` (100 keys)

| English key | Original key | Default | Min | Max | UI group | Label |
|---|---|---|---|---|---|---|
| `cult_soldier_share` | `tarikat_asker` | 15 | 0 | 100 | War & diplomacy | Share (%) of cult followers who join the cult's army |
| `faction_soldiers_per_power` | `hizip_asker_guc` | 60 | 0 | 10000 | War & diplomacy | Faction army: soldiers per power point |
| `faction_soldiers_per_wealth` | `hizip_asker_servet` | 20 | 0 | 10000 | War & diplomacy | Faction army: soldiers per wealth point |
| `faction_default_power` | `hizip_guc_varsayilan` | 30 | 0 | 100 | War & diplomacy | Power assumed for a faction of unknown power |
| `faction_default_wealth` | `hizip_servet_varsayilan` | 20 | 0 | 100 | War & diplomacy | Wealth assumed for a faction of unknown wealth |
| `cult_default_followers` | `murit_varsayilan` | 100 | 0 | 1000000 | War & diplomacy | Followers assumed for a cult of unknown follower count (army calc) |
| `default_population` | `nufus_varsayilan` | 1000 | 0 | 10000000 | War & diplomacy | Population assumed for a people/town of unknown population (army calc) |
| `cult_default_zeal` | `bagnazlik_varsayilan` | 50 | 0 | 100 | War & diplomacy | Zeal assumed for a cult of unknown zeal (holy guard morale) |
| `min_soldier_share` | `asker_en_az_pay` | 4 | 0 | 100 | War & diplomacy | Minimum share (%) of population in a people/town army |
| `army_power_min` | `ordu_guc_alt` | 2 | 1 | 12 | War & diplomacy | Lowest power level of an army |
| `army_power_max` | `ordu_guc_ust` | 8 | 1 | 12 | War & diplomacy | Highest power level of an army |
| `army_min_size` | `ordu_en_az` | 30 | 1 | 100000 | War & diplomacy | Minimum soldiers in an army |
| `army_morale_base` | `ordu_moral_taban` | 55 | 0 | 100 | War & diplomacy | Base morale of a new army |
| `army_morale_die` | `ordu_moral_zar` | 25 | 1 | 100 | War & diplomacy | Die added to a new army's morale (1–N) |
| `army_morale_zeal_divisor` | `ordu_moral_bagnaz_bolen` | 5 | 1 | 100 | War & diplomacy | Holy guard morale: zeal / this |
| `army_equipment_base` | `ordu_techizat_taban` | 20 | 0 | 100 | War & diplomacy | Base equipment of a new army |
| `army_equipment_weapon_mult` | `ordu_techizat_silah` | 2 | 0 | 20 | War & diplomacy | Multiplier of weapon power into equipment |
| `army_equipment_metallurgy` | `ordu_techizat_metalurji` | 15 | 0 | 100 | War & diplomacy | Equipment bonus for knowing metallurgy |
| `army_experience_warcraft` | `ordu_deneyim_savas` | 30 | 0 | 100 | War & diplomacy | Initial experience of an army that knows warcraft |
| `army_experience_base` | `ordu_deneyim` | 10 | 0 | 100 | War & diplomacy | Initial experience of a new army |
| `war_record_power` | `savas_olay_guc` | 4 | 1 | 12 | War & diplomacy | Initial power level of a war record |
| `war_initial_violence` | `savas_siddet_ilk` | 30 | 0 | 100 | War & diplomacy | Initial violence of a war |
| `siege_min_defence` | `kusatma_savunma` | 55 | 0 | 100 | War & diplomacy | Minimum defence of a settlement for a battle to be a siege |
| `power_community_share` | `guc_toplum_pay` | 60 | 0 | 500 | War & diplomacy | Share (%) of community military power entering battle power |
| `power_size_mult` | `guc_buyukluk` | 14 | 0 | 200 | War & diplomacy | Battle power: multiplier on log10(soldiers) |
| `power_morale_divisor` | `guc_moral_bolen` | 3 | 1 | 100 | War & diplomacy | Battle power: morale / this |
| `power_equipment_divisor` | `guc_techizat_bolen` | 4 | 1 | 100 | War & diplomacy | Battle power: equipment / this |
| `power_experience_divisor` | `guc_deneyim_bolen` | 5 | 1 | 100 | War & diplomacy | Battle power: experience / this |
| `power_commander_divisor` | `guc_komutan_bolen` | 12 | 1 | 100 | War & diplomacy | Battle power: commander power+intellect+charisma / this |
| `battle_die` | `muharebe_zar` | 20 | 1 | 200 | War & diplomacy | Battle luck die (1–N) |
| `battle_die_mult` | `muharebe_zar_carpan` | 2 | 0 | 20 | War & diplomacy | Battle luck die multiplier |
| `violence_growth` | `siddet_artis` | 8 | 0 | 100 | War & diplomacy | War violence increase per battle |
| `violence_gap_divisor` | `siddet_fark_bolen` | 10 | 1 | 1000 | War & diplomacy | Power-gap contribution to violence: gap / this |
| `war_power_min` | `savas_guc_alt` | 2 | 1 | 12 | War & diplomacy | Lowest power level of a war record |
| `war_power_max` | `savas_guc_ust` | 9 | 1 | 12 | War & diplomacy | Highest power level of a war record |
| `war_power_interval` | `savas_guc_aralik` | 2 | 1 | 100 | War & diplomacy | War record power level rises every N battles |
| `war_power_step` | `savas_guc_artis` | 1 | 0 | 12 | War & diplomacy | War record power-level increase on those battles |
| `breach_gap_divisor` | `yarma_fark_bolen` | 60 | 1 | 1000 | War & diplomacy | Wall-breach chance: power gap / this |
| `breach_starving_food` | `yarma_ac_erzak` | 15 | 0 | 200 | War & diplomacy | A besieged town below this food counts as starving |
| `breach_starving_bonus` | `yarma_ac_ek` | 35 | 0 | 100 | War & diplomacy | Breach-chance bonus against a starving town (%) |
| `breach_min` | `yarma_alt` | 10 | 0 | 100 | War & diplomacy | Floor of breach chance (%) |
| `breach_max` | `yarma_ust` | 85 | 0 | 100 | War & diplomacy | Ceiling of breach chance (%) |
| `siege_repulse_morale` | `kusatma_puskurtme_moral` | 6 | 0 | 100 | War & diplomacy | Attacker morale loss when a siege is repulsed |
| `breach_defence_loss` | `sur_yarma_savunma` | 25 | 0 | 100 | War & diplomacy | Town defence loss when walls are breached |
| `siege_breach_score` | `kusatma_skor` | 3 | 0 | 20 | War & diplomacy | War score from breaching walls |
| `siege_population_remaining` | `kusatma_nufus_kalan` | 94 | 0 | 100 | War & diplomacy | Town population remaining per siege round (%) |
| `siege_prosperity_loss` | `kusatma_refah` | 6 | 0 | 100 | War & diplomacy | Prosperity lost by a besieged town |
| `siege_food_loss` | `kusatma_erzak` | 20 | 0 | 200 | War & diplomacy | Food lost from a besieged town's granary |
| `siege_attacker_morale_loss` | `kusatma_moral` | 4 | 0 | 100 | War & diplomacy | Attacker morale loss during an ongoing siege |
| `siege_default_food` | `kusatma_erzak_varsayilan` | 50 | 0 | 100000 | War & diplomacy | Food assumed for a besieged town with no granary record |
| `siege_default_population` | `kusatma_nufus_varsayilan` | 100 | 0 | 10000000 | War & diplomacy | Population assumed for a besieged town with no population |
| `great_victory_gap` | `buyuk_zafer_fark` | 35 | 0 | 1000 | War & diplomacy | Power gap that counts as a great victory |
| `great_victory_score` | `buyuk_zafer_skor` | 2 | 0 | 20 | War & diplomacy | War score from a great victory |
| `loser_loss_base` | `maglup_kayip` | 12 | 0 | 100 | War & diplomacy | Loser army base loss (%) |
| `loser_loss_extra_max` | `maglup_kayip_ek` | 30 | 0 | 100 | War & diplomacy | Loser army max extra loss from power gap (%) |
| `loser_loss_divisor` | `maglup_kayip_bolen` | 220 | 1 | 100000 | War & diplomacy | Loser extra loss: power gap / this |
| `winner_loss_base` | `galip_kayip` | 4 | 0 | 100 | War & diplomacy | Winner army base loss (%) |
| `winner_loss_extra_max` | `galip_kayip_ek` | 10 | 0 | 100 | War & diplomacy | Winner army max extra loss from power gap (%) |
| `winner_loss_divisor` | `galip_kayip_bolen` | 600 | 1 | 100000 | War & diplomacy | Winner extra loss: power gap / this |
| `loser_morale_loss` | `maglup_moral` | 10 | 0 | 100 | War & diplomacy | Loser army morale loss |
| `loser_morale_gap_divisor` | `maglup_moral_bolen` | 8 | 1 | 1000 | War & diplomacy | Loser extra morale loss: power gap / this |
| `winner_morale_gain` | `galip_moral` | 4 | 0 | 100 | War & diplomacy | Winner army morale gain |
| `winner_experience_gain` | `galip_deneyim` | 6 | 0 | 100 | War & diplomacy | Winner army experience gain |
| `loser_experience_gain` | `maglup_deneyim` | 3 | 0 | 100 | War & diplomacy | Loser army experience gain |
| `community_loss_divisor` | `topluluk_kayip_bolen` | 5 | 1 | 100 | War & diplomacy | Losing community population loss: army loss / this |
| `loser_prosperity_loss` | `maglup_refah` | 5 | 0 | 100 | War & diplomacy | Losing community prosperity and wealth loss |
| `winner_wealth_gain` | `galip_servet` | 3 | 0 | 100 | War & diplomacy | Winning community wealth gain |
| `battle_relation` | `muharebe_iliski` | 8 | 0 | 100 | War & diplomacy | Relation points removed by a battle |
| `patron_fame` | `hami_un` | 2 | 0 | 50 | War & diplomacy | Fame per battle for the winner's patron god |
| `patron_xp` | `hami_xp` | 8 | 0 | 100 | War & diplomacy | XP per battle for the winner's patron god |
| `patron_relation` | `hami_iliski` | 5 | 0 | 100 | War & diplomacy | Relation removed between the two patron gods per battle |
| `battle_record_power_divisor` | `muharebe_olay_guc_bolen` | 20 | 1 | 1000 | War & diplomacy | Battle record power: power gap / this |
| `battle_record_power_min` | `muharebe_olay_guc_alt` | 2 | 1 | 12 | War & diplomacy | Lowest power level of a battle record |
| `battle_record_power_max` | `muharebe_olay_guc_ust` | 7 | 1 | 12 | War & diplomacy | Highest power level of a battle record |
| `battle_violence_base` | `muharebe_siddet_taban` | 30 | 0 | 100 | War & diplomacy | Base violence of a battle record |
| `duel_agility_divisor` | `duello_ceviklik_bolen` | 2 | 1 | 100 | Heroes & mortals | Duel power: agility / this |
| `duel_weapon_mult` | `duello_silah` | 2 | 0 | 20 | Heroes & mortals | Weapon power multiplier in duels |
| `duel_die` | `duello_zar` | 20 | 1 | 200 | Heroes & mortals | Duel luck die (1–N) |
| `duel_die_mult` | `duello_zar_carpan` | 2 | 0 | 20 | Heroes & mortals | Duel luck die multiplier |
| `duel_charisma_gain` | `duello_karizma` | 6 | 0 | 100 | Heroes & mortals | Charisma gain for the duel winner |
| `duel_wound` | `duello_yara` | 40 | 0 | 1000 | Heroes & mortals | HP lost by the duel loser |
| `default_hp` | `can_varsayilan` | 100 | 1 | 100000 | Heroes & mortals | HP assumed for a hero with no HP when wounded |
| `rout_morale` | `dagilma_moral` | 12 | 0 | 100 | War & diplomacy | An army below this morale disbands |
| `rout_size` | `dagilma_asker` | 30 | 0 | 100000 | War & diplomacy | An army below this many soldiers disbands |
| `victory_score` | `zafer_skor` | 3 | 1 | 50 | War & diplomacy | Decisive score that ends the war |
| `exhaustion_battles` | `yorgunluk_muharebe` | 4 | 1 | 100 | War & diplomacy | Battle count at which exhaustion peace becomes possible |
| `conquest_relation` | `fetih_iliski` | 25 | 0 | 200 | War & diplomacy | Relation points removed by conquest |
| `tribute_relation` | `harac_iliski` | 10 | 0 | 200 | War & diplomacy | Relation points removed by being made tributary |
| `white_peace_relation` | `beyaz_baris_iliski` | 8 | 0 | 100 | War & diplomacy | Relation bonus from a white peace |
| `tribute_end_relation` | `harac_bitti_iliski` | 5 | 0 | 100 | War & diplomacy | Relation bonus when tribute ends |
| `tribute_revolt_relation` | `harac_isyan_iliski` | 15 | 0 | 200 | War & diplomacy | Relation points removed by a tribute revolt |
| `ransom_min_wealth` | `fidye_servet` | 30 | 0 | 100 | Heroes & mortals | Minimum wealth of a homeland able to pay ransom |
| `ransom_min_prosperity` | `fidye_refah` | 50 | 0 | 100 | Heroes & mortals | Minimum prosperity of a homeland able to pay ransom |
| `ransom_cost` | `fidye_bedel` | 12 | 0 | 100 | Heroes & mortals | Wealth and prosperity cost of ransom |
| `ransom_relation` | `fidye_iliski` | 5 | 0 | 100 | Heroes & mortals | Relation bonus from ransom |
| `escape_agility_divisor` | `kacis_ceviklik_bolen` | 250 | 1 | 100000 | Heroes & mortals | Prisoner escape chance: agility / this |
| `escape_intellect_divisor` | `kacis_akil_bolen` | 400 | 1 | 100000 | Heroes & mortals | Prisoner escape chance: intellect / this |
| `prisoner_default_stat` | `esir_stat_varsayilan` | 30 | 0 | 100 | Heroes & mortals | Value assumed for a prisoner of unknown agility/intellect |
| `execution_relation` | `idam_iliski` | 70 | 0 | 100 | Heroes & mortals | Below minus this relation a prisoner may be executed |
| `prisoner_turncoat_age` | `esir_donme_cag` | 3 | 0 | 100 | Heroes & mortals | Captivity duration (epochs) after which a prisoner may change sides |

#### Rule group `DERIN_TOPLUM` → suggested `deep_society` (128 keys)

| English key | Original key | Default | Min | Max | UI group | Label |
|---|---|---|---|---|---|---|
| `class_farmer` | `sinif_ciftci` | 55 | 0 | 100 | Economy | Base farmer share of society (%) |
| `class_artisan` | `sinif_zanaatkar` | 15 | 0 | 100 | Economy | Base artisan share (%) |
| `class_merchant` | `sinif_tuccar` | 8 | 0 | 100 | Economy | Base merchant share (%) |
| `class_priest` | `sinif_rahip` | 7 | 0 | 100 | Economy | Base priest share (%) |
| `class_warrior` | `sinif_savasci` | 10 | 0 | 100 | Economy | Base warrior share (%) |
| `class_scribe` | `sinif_katip` | 5 | 0 | 100 | Economy | Base scribe share (%) |
| `initial_satisfaction` | `memnuniyet_ilk` | 55 | 0 | 100 | Economy | Initial satisfaction of classes |
| `initial_food` | `erzak_ilk` | 60 | 0 | 1000 | Economy | Community's initial food |
| `initial_ore` | `maden_ilk` | 10 | 0 | 1000 | Economy | Community's initial ore |
| `initial_goods` | `mal_ilk` | 20 | 0 | 1000 | Economy | Community's initial goods |
| `storage_cap` | `ambar_tavan` | 200 | 10 | 100000 | Economy | Cap of food, ore and goods storage |
| `default_stat` | `stat_varsayilan` | 50 | 0 | 100 | Economy | Value assumed for unknown prosperity, faith or fertility |
| `target_agriculture_farmer` | `hedef_tarim_ciftci` | 10 | 0 | 100 | Economy | Farmer share bonus for those who know agriculture |
| `target_trade_merchant` | `hedef_ticaret_tuccar` | 6 | 0 | 100 | Economy | Merchant share bonus for traders |
| `target_route_merchant` | `hedef_yol_tuccar` | 2 | 0 | 100 | Economy | Merchant share bonus per trade route |
| `target_route_merchant_cap` | `hedef_yol_tavan` | 6 | 0 | 100 | Economy | Max merchant share bonus from trade routes |
| `target_writing_scribe` | `hedef_yazi_katip` | 6 | 0 | 100 | Economy | Scribe share bonus for those who know writing |
| `target_craft_threshold` | `hedef_zanaat_esik` | 60 | 0 | 100 | Economy | Craft level that raises artisan share |
| `target_artisan` | `hedef_zanaatkar` | 7 | 0 | 100 | Economy | Artisan share bonus from metallurgy or high craft |
| `target_seafaring_merchant` | `hedef_deniz_tuccar` | 3 | 0 | 100 | Economy | Merchant share bonus for seafarers |
| `target_war_warrior` | `hedef_savas_savasci` | 10 | 0 | 100 | Economy | Warrior share bonus for a society at war |
| `target_faith_threshold` | `hedef_inanc_esik` | 60 | 0 | 100 | Economy | Piety that raises priest share |
| `target_priest` | `hedef_rahip` | 6 | 0 | 100 | Economy | Priest share bonus in a pious society |
| `target_godless_priest` | `hedef_tanrisiz_rahip` | 2 | 0 | 100 | Economy | Priest share in a godless society |
| `class_drift` | `sinif_kayma` | 25 | 0 | 100 | Economy | Per-epoch drift of class shares toward target (%) |
| `fertility_place_share` | `bereket_konum_pay` | 40 | 0 | 100 | Economy | Share (%) of the place's own fertility in soil fertility |
| `fertility_region_share` | `bereket_bolge_pay` | 60 | 0 | 100 | Economy | Share (%) of the parent region in soil fertility |
| `food_farmer_divisor` | `uretim_ciftci_bolen` | 45 | 1 | 1000 | Economy | Food production: farmer share / this |
| `food_base` | `uretim_taban` | 55 | 0 | 1000 | Economy | Fertility-independent base of food production (%) |
| `food_fertility_divisor` | `uretim_bereket_bolen` | 110 | 1 | 10000 | Economy | Food production: fertility / this |
| `food_agriculture_mult` | `uretim_tarim` | 135 | 0 | 1000 | Economy | Food production multiplier for agriculture (%) |
| `food_fertility_law_mult` | `uretim_bereket_yasasi` | 115 | 0 | 1000 | Economy | Food production multiplier under the fertility law (%) |
| `food_drought_mult` | `uretim_kurak` | 80 | 0 | 1000 | Economy | Food production multiplier in a drought era (%) |
| `food_rain_mult` | `uretim_yagmur` | 110 | 0 | 1000 | Economy | Food production multiplier in a rain era (%) |
| `food_ratio_min` | `uretim_alt` | 20 | 0 | 1000 | Economy | Floor of food production ratio (%) |
| `food_ratio_max` | `uretim_ust` | 300 | 0 | 10000 | Economy | Ceiling of food production ratio (%) |
| `food_ratio_effect` | `erzak_oran_carpan` | 30 | 0 | 1000 | Economy | Effect of production ratio on food per epoch |
| `war_food_cost` | `erzak_savas` | 6 | 0 | 200 | Economy | Food eaten by war per epoch |
| `food_low` | `erzak_dusuk` | 30 | 0 | 200 | Economy | Below this food the granary goes into saving |
| `food_low_gain` | `erzak_dusuk_ek` | 4 | 0 | 200 | Economy | Per-epoch food gain while saving |
| `ore_abundance_divisor` | `maden_bolluk_bolen` | 10 | 1 | 1000 | Economy | Ore gain: ore resource abundance / this |
| `ore_consumption` | `maden_tuketim` | 1 | 0 | 200 | Economy | Ore consumed per epoch |
| `goods_artisan_divisor` | `zanaat_bolen` | 15 | 1 | 1000 | Economy | Goods production: artisan share / this |
| `ore_plentiful` | `maden_bol` | 20 | 0 | 200 | Economy | Above this ore, artisans find plenty |
| `goods_ore_mult` | `zanaat_maden_carpan` | 140 | 0 | 1000 | Economy | Goods production multiplier with plentiful ore (%) |
| `goods_metallurgy_mult` | `zanaat_metalurji` | 130 | 0 | 1000 | Economy | Goods production multiplier for metallurgy (%) |
| `goods_production_mult` | `mal_uretim` | 6 | 0 | 100 | Economy | Goods production multiplier |
| `goods_consumption` | `mal_tuketim` | 3 | 0 | 200 | Economy | Goods consumed per epoch |
| `goods_prosperity_divisor` | `mal_refah_bolen` | 50 | 1 | 1000 | Economy | Prosperity's goods consumption: prosperity / this |
| `goods_ore_threshold` | `mal_maden_esik` | 10 | 0 | 200 | Economy | Goods/ore threshold above which goods production spends ore |
| `goods_ore_spend` | `mal_maden_harcama` | 1 | 0 | 100 | Economy | Ore-spending multiplier of goods production |
| `price_ratio_floor` | `fiyat_oran_alt` | 30 | 1 | 1000 | Economy | Floor of production ratio in food price (%) |
| `price_scarcity_food` | `fiyat_kitlik_erzak` | 60 | 0 | 200 | Economy | Below this food bread gets expensive |
| `price_scarcity_mult` | `fiyat_kitlik` | 180 | 0 | 10000 | Economy | Food price multiplier in scarcity (%) |
| `price_plenty_food` | `fiyat_bolluk_erzak` | 120 | 0 | 100000 | Economy | Above this food bread gets cheap |
| `price_plenty_mult` | `fiyat_bolluk` | 70 | 0 | 1000 | Economy | Food price multiplier in plenty (%) |
| `price_min` | `fiyat_alt` | 30 | 0 | 1000 | Economy | Floor of prices (%) |
| `price_food_max` | `fiyat_erzak_ust` | 900 | 100 | 100000 | Economy | Ceiling of food price (%) |
| `price_max` | `fiyat_ust` | 400 | 100 | 100000 | Economy | Ceiling of ore and goods price (%) |
| `price_goods_equilibrium` | `fiyat_denge` | 40 | 1 | 10000 | Economy | Stock at which goods are at normal price |
| `price_ore_equilibrium` | `fiyat_denge_maden` | 10 | 1 | 10000 | Economy | Stock at which ore is at normal price (ore stores run much lower than goods) |
| `price_stock_floor` | `fiyat_stok_alt` | 10 | 1 | 10000 | Economy | Floor of stock in ore and goods price |
| `sat_hungry_food` | `m_ac_erzak` | 60 | 0 | 200 | Economy | Below this food farmers are hungry |
| `sat_farmer_hungry` | `m_ciftci_ac` | 25 | 0 | 100 | Economy | Satisfaction loss of hungry farmers |
| `sat_farmer_fed` | `m_ciftci_tok` | 5 | 0 | 100 | Economy | Satisfaction gain of fed farmers |
| `sat_farmer_war` | `m_ciftci_savas` | 8 | 0 | 100 | Economy | Farmer satisfaction lost from war |
| `sat_artisan_plenty` | `m_zanaat_bol` | 8 | 0 | 100 | Economy | Artisan satisfaction gain with plentiful ore |
| `sat_artisan_scarce` | `m_zanaat_kit` | 6 | 0 | 100 | Economy | Artisan satisfaction loss with scarce ore |
| `sat_merchant_route` | `m_tuccar_yol` | 6 | 0 | 100 | Economy | Merchant satisfaction gain per trade route |
| `sat_merchant_war` | `m_tuccar_savas` | 12 | 0 | 100 | Economy | Merchant satisfaction lost from war |
| `sat_merchant_no_route` | `m_tuccar_yolsuz` | 10 | 0 | 100 | Economy | Merchant satisfaction loss with no trade route |
| `sat_priest_god` | `m_rahip_tanri` | 5 | 0 | 100 | Economy | Satisfaction gain of priests who have a god |
| `sat_priest_no_god` | `m_rahip_tanrisiz` | 15 | 0 | 100 | Economy | Satisfaction loss of priests without a god |
| `sat_priest_godless` | `m_rahip_inkar` | 30 | 0 | 100 | Economy | Extra priest satisfaction loss in a godless society |
| `sat_warrior_base` | `m_savasci_taban` | 45 | 0 | 100 | Economy | Warrior satisfaction base |
| `sat_warrior_war` | `m_savasci_savas` | 12 | 0 | 100 | Economy | Warrior satisfaction gain at war |
| `sat_warrior_peace` | `m_savasci_baris` | 5 | 0 | 100 | Economy | Warrior satisfaction loss at peace |
| `sat_warrior_warcraft` | `m_savasci_sanat` | 6 | 0 | 100 | Economy | Warrior satisfaction gain if warcraft is known |
| `sat_scribe_writing` | `m_katip_yazi` | 12 | 0 | 100 | Economy | Scribe satisfaction gain if writing is known |
| `sat_scribe_no_writing` | `m_katip_yazisiz` | 10 | 0 | 100 | Economy | Scribe satisfaction loss without writing |
| `sat_tribute` | `m_harac` | 8 | 0 | 100 | Economy | Satisfaction loss to all classes from paying tribute |
| `sat_justice_divisor` | `m_adalet_bolen` | 5 | 1 | 100 | Economy | Law justice into satisfaction: (justice-50) / this |
| `sat_curse` | `m_lanet` | 6 | 0 | 100 | Economy | Satisfaction loss to all classes from a curse |
| `sat_drift` | `m_kayma` | 30 | 0 | 100 | Economy | Per-epoch drift of satisfaction toward target (%) |
| `effect_prosperity_divisor` | `etki_refah_bolen` | 4 | 1 | 100 | Economy | Merchant share effect on prosperity: (share-base) / this |
| `effect_goods_plenty` | `etki_mal_bol` | 60 | 0 | 100000 | Economy | Above this goods prosperity rises extra |
| `effect_goods_prosperity` | `etki_mal_refah` | 1 | 0 | 100 | Economy | Per-epoch prosperity gain from plentiful goods |
| `effect_faith_divisor` | `etki_inanc_bolen` | 3 | 1 | 100 | Economy | Priest share effect on piety: (share-base) / this |
| `effect_defence_divisor` | `etki_savunma_bolen` | 4 | 1 | 100 | Economy | Warrior share effect on town defence: (share-base) / this |
| `effect_default_defence` | `etki_savunma_varsayilan` | 30 | 0 | 100 | Economy | Defence assumed for a town of unknown defence |
| `effect_martial_divisor` | `etki_savascilik_bolen` | 5 | 1 | 100 | Economy | Warrior share effect on people's martiality: (share-base) / this |
| `famine_ratio` | `kitlik_oran` | 90 | 0 | 1000 | Population & growth | Production ratio must be below this for famine (%) |
| `famine_food` | `kitlik_erzak` | 60 | 0 | 1000 | Population & growth | Food must drop to this for famine (granary self-refills via saving so rarely hits zero) |
| `famine_cap` | `kitlik_tavan` | 1 | 0 | 100 | Population & growth | Max famines per epoch |
| `famine_population_remaining` | `kitlik_nufus_kalan` | 92 | 0 | 100 | Population & growth | Population remaining in famine (%) |
| `famine_prosperity_loss` | `kitlik_refah` | 6 | 0 | 100 | Population & growth | Prosperity lost to famine |
| `weapon_ore_required` | `silah_maden` | 12 | 0 | 10000 | Economy | Ore required to forge weapons (ore stores are low in most communities) |
| `weapon_warrior_share` | `silah_savasci` | 12 | 0 | 100 | Economy | Warrior share required to forge weapons (%) |
| `weapon_cap` | `silah_tavan` | 2 | 0 | 100 | Economy | Max weapon batches per epoch |
| `weapon_ore_cost` | `silah_maden_bedel` | 8 | 0 | 10000 | Economy | Ore spent per weapon batch |
| `weapon_power_level` | `silah_guc` | 3 | 1 | 12 | Economy | Power level of forged weapons |
| `weapon_damage_base` | `silah_hasar` | 30 | 0 | 100 | Economy | Base damage of forged weapons |
| `weapon_damage_die` | `silah_hasar_zar` | 35 | 1 | 100 | Economy | Damage die of forged weapons (1–N) |
| `weapon_protection_base` | `silah_koruma` | 5 | 0 | 100 | Economy | Base protection of forged weapons |
| `weapon_protection_die` | `silah_koruma_zar` | 15 | 1 | 100 | Economy | Protection die of forged weapons (1–N) |
| `weapon_might_base` | `silah_kudret` | 5 | 0 | 100 | Economy | Base might of forged weapons |
| `weapon_might_die` | `silah_kudret_zar` | 10 | 1 | 100 | Economy | Might die of forged weapons (1–N) |
| `bankruptcy_merchant_share` | `iflas_tuccar` | 12 | 0 | 100 | Economy | Merchant share required for bankruptcy (%) |
| `bankruptcy_prosperity` | `iflas_refah` | 35 | 0 | 100 | Economy | Below this prosperity a guild may go bankrupt |
| `bankruptcy_cap` | `iflas_tavan` | 1 | 0 | 100 | Economy | Max guild bankruptcies per epoch |
| `bankruptcy_satisfaction_loss` | `iflas_memnuniyet` | 20 | 0 | 100 | Economy | Merchant satisfaction lost to bankruptcy |
| `bankruptcy_share_loss` | `iflas_pay` | 4 | 0 | 100 | Economy | Merchant share lost to bankruptcy |
| `bankruptcy_prosperity_loss` | `iflas_refah_kayip` | 5 | 0 | 100 | Economy | Prosperity lost to bankruptcy |
| `uprising_min_class_share` | `ayaklanma_sinif_pay` | 5 | 0 | 100 | War & diplomacy | Minimum share (%) of a class able to rise up |
| `uprising_satisfaction` | `ayaklanma_memnuniyet` | 22 | 0 | 100 | War & diplomacy | A class below this satisfaction may rise up |
| `uprising_min_population` | `ayaklanma_nufus` | 800 | 0 | 10000000 | War & diplomacy | Population required for a class uprising |
| `uprising_cap` | `ayaklanma_tavan` | 1 | 0 | 100 | War & diplomacy | Max class uprisings per epoch |
| `uprising_power_level` | `ayaklanma_guc` | 3 | 1 | 12 | War & diplomacy | Power level of the uprising faction |
| `uprising_faction_power` | `ayaklanma_hizip_guc` | 25 | 0 | 100 | War & diplomacy | Uprising faction power base |
| `uprising_faction_power_die` | `ayaklanma_hizip_guc_zar` | 30 | 1 | 100 | War & diplomacy | Uprising faction power die (1–N) |
| `uprising_wealth` | `ayaklanma_servet` | 5 | 0 | 100 | War & diplomacy | Uprising faction wealth base |
| `uprising_wealth_die` | `ayaklanma_servet_zar` | 15 | 1 | 100 | War & diplomacy | Uprising faction wealth die (1–N) |
| `uprising_influence` | `ayaklanma_nufuz` | 20 | 0 | 100 | War & diplomacy | Uprising faction influence base |
| `uprising_influence_die` | `ayaklanma_nufuz_zar` | 30 | 1 | 100 | War & diplomacy | Uprising faction influence die (1–N) |
| `uprising_relief` | `ayaklanma_rahatlama` | 15 | 0 | 100 | War & diplomacy | Satisfaction gain of the class that rose up |
| `trade_min_gap` | `ticaret_fark` | 20 | 0 | 1000 | Economy | Minimum stock gap at which a trade route carries goods |
| `trade_flow_divisor` | `ticaret_akis_bolen` | 4 | 1 | 100 | Economy | Trade flow: stock gap / this |
| `trade_seller_prosperity` | `ticaret_satan_refah` | 1 | 0 | 100 | Economy | Seller's prosperity gain per trade |

#### Rule group `DERIN_YASAM` → suggested `deep_life` (348 keys)

| English key | Original key | Default | Min | Max | UI group | Label |
|---|---|---|---|---|---|---|
| `hero_power_sum` | `kahraman_guc` | 90 | 0 | 200 | Heroes & mortals | Power + agility sum that makes a mortal a hero |
| `quest_resolve_cap` | `gorev_sonuc_tavan` | 4 | 0 | 50 | Heroes & mortals | Max hero quests resolved per epoch |
| `quest_new_cap` | `gorev_tavan` | 3 | 0 | 50 | Heroes & mortals | Max new hero quests per epoch |
| `companion_cap` | `yoldas_tavan` | 1 | 0 | 20 | Heroes & mortals | Max new companionships per epoch |
| `apprentice_cap` | `cirak_tavan` | 1 | 0 | 20 | Heroes & mortals | Max new apprentices per epoch |
| `apprentice_age_share` | `cirak_yas_pay` | 60 | 0 | 100 | Heroes & mortals | At least this % of lifespan must be lived to train an apprentice |
| `apprentice_min_charisma` | `cirak_karizma` | 50 | 0 | 100 | Heroes & mortals | Minimum charisma of a hero who trains an apprentice |
| `apprentice_stat_fallback` | `cirak_stat_yedek` | 40 | 0 | 100 | Heroes & mortals | Apprentice stat: value used for a missing master stat |
| `apprentice_stat_share` | `cirak_stat_pay` | 70 | 0 | 200 | Heroes & mortals | Apprentice stat: share (%) taken from master's stat |
| `apprentice_stat_die` | `cirak_stat_zar` | 25 | 1 | 100 | Heroes & mortals | Die added to apprentice stats (max) |
| `apprentice_hp` | `cirak_can` | 90 | 1 | 1000 | Heroes & mortals | Apprentice HP |
| `apprentice_power_gap` | `cirak_guc_fark` | 1 | 0 | 12 | Heroes & mortals | Apprentice power level is this much below master's |
| `apprentice_age` | `cirak_yas` | 16 | 0 | 200 | Heroes & mortals | Apprentice starting age (years) |
| `apprentice_lifespan_die` | `cirak_omur_zar` | 21 | 1 | 500 | Heroes & mortals | Apprentice lifespan: die added to master's lifespan (years) |
| `apprentice_lifespan_shift` | `cirak_omur_kayma` | 11 | 0 | 500 | Heroes & mortals | Apprentice lifespan: years subtracted after the die |
| `apprentice_lifespan_fallback` | `cirak_omur_yedek` | 70 | 1 | 50000 | Heroes & mortals | Lifespan assumed for a master with none recorded (years) |
| `apprentice_lifespan_min` | `cirak_omur_alt` | 30 | 1 | 50000 | Heroes & mortals | Apprentice minimum lifespan (years) |
| `lifespan_cap` | `omur_tavan` | 50000 | 10 | 1000000 | Heroes & mortals | A mortal's maximum lifespan (years) |
| `quest_hunt_min_danger` | `gorev_av_tehlike` | 50 | 0 | 100 | Heroes & mortals | Minimum species danger for a hunt quest |
| `quest_max_distance` | `gorev_mesafe` | 4 | 0 | 20 | Heroes & mortals | Max distance of a quest target (map steps) |
| `quest_weight_hunt` | `gorev_av_agirlik` | 3 | 0 | 100 | Heroes & mortals | Quest choice: hunt weight |
| `quest_weight_thread` | `gorev_iplik_agirlik` | 4 | 0 | 100 | Heroes & mortals | Quest choice: open story thread weight |
| `quest_weight_relic` | `gorev_emanet_agirlik` | 2 | 0 | 100 | Heroes & mortals | Quest choice: lost item weight |
| `quest_relic_strong_level` | `gorev_emanet_guclu_esik` | 5 | 0 | 12 | Heroes & mortals | Power level at which a lost item counts as strong |
| `quest_relic_strong_bonus` | `gorev_emanet_guclu_ek` | 2 | 0 | 100 | Heroes & mortals | Quest choice: extra weight of a strong lost item |
| `quest_weight_knowledge` | `gorev_bilgi_agirlik` | 2 | 0 | 100 | Heroes & mortals | Quest choice: lost knowledge weight |
| `quest_weight_vengeance` | `gorev_oc_agirlik` | 3 | 0 | 100 | Heroes & mortals | Quest choice: blood-feud vengeance weight |
| `quest_success_divisor` | `gorev_basari_bolen` | 300 | 1 | 10000 | Heroes & mortals | Quest success: (power + agility + intellect) / this |
| `quest_companion_bonus` | `gorev_yoldas_ek` | 10 | 0 | 100 | Heroes & mortals | Quest success bonus per companion (%) |
| `quest_chosen_bonus` | `gorev_secilmis_ek` | 12 | 0 | 100 | Heroes & mortals | Quest success bonus for the Chosen (%) |
| `quest_success_min` | `gorev_basari_alt` | 15 | 0 | 100 | Heroes & mortals | Minimum quest success probability (%) |
| `quest_success_max` | `gorev_basari_ust` | 90 | 0 | 100 | Heroes & mortals | Maximum quest success probability (%) |
| `quest_charisma_gain` | `gorev_karizma` | 4 | 0 | 100 | Heroes & mortals | Charisma gain for completing a quest |
| `quest_fame_gain` | `gorev_un` | 3 | 0 | 100 | Heroes & mortals | Fame gain of the hero's god for a completed quest |
| `quest_give_up_age` | `gorev_vazgecme_cag` | 3 | 1 | 50 | Heroes & mortals | Epochs after which an unresolved quest is abandoned |
| `quest_wound` | `gorev_yara` | 20 | 0 | 1000 | Heroes & mortals | HP lost by the hero in an unresolved quest epoch |
| `dark_age_forget_cap` | `karanlik_unutma_tavan` | 2 | 0 | 50 | Civilisation | Max knowledge forgotten per epoch |
| `dark_age_violence` | `karanlik_siddet` | 70 | 0 | 100 | Civilisation | Minimum violence of an event that counts as devastation |
| `dark_age_scribe_share` | `karanlik_katip` | 10 | 0 | 100 | Civilisation | Scribe share (%) that protects knowledge from being forgotten |
| `relic_rediscovery_cap` | `kalinti_bulma_tavan` | 1 | 0 | 20 | Civilisation | Max knowledge rediscovered from ruins per epoch |
| `relic_scribe_share` | `kalinti_katip` | 7 | 0 | 100 | Civilisation | Minimum scribe share (%) of a community that can decode ruins |
| `knowledge_spread_base` | `yayginlik_taban` | 8 | 0 | 100 | Civilisation | Base spread of a known knowledge |
| `knowledge_spread_per_knower` | `yayginlik_bilen` | 10 | 0 | 100 | Civilisation | Spread contribution per knowing community |
| `knowledge_spread_fallback` | `yayginlik_yedek` | 10 | 0 | 100 | Civilisation | Spread assumed for a knowledge with none recorded |
| `knowledge_spread_step` | `yayginlik_adim` | 5 | 0 | 100 | Civilisation | Max per-epoch change of knowledge spread |
| `spy_min_influence` | `casus_nufuz` | 50 | 0 | 100 | War & diplomacy | Minimum influence of a faction able to build a spy network |
| `spy_network_cap` | `casus_ag_tavan` | 1 | 0 | 20 | War & diplomacy | Max new spy networks per epoch |
| `spy_target_coldness` | `casus_iliski` | 30 | 0 | 100 | War & diplomacy | Coldness that makes a spy target (relation below minus this) |
| `spy_capture_base` | `casus_yakalanma` | 12 | 0 | 100 | War & diplomacy | Base probability (%) spies are caught |
| `spy_capture_fallback` | `casus_yakalanma_yedek` | 30 | 0 | 100 | War & diplomacy | Capture: value used if target has no influence/defence |
| `spy_capture_divisor` | `casus_yakalanma_bolen` | 400 | 1 | 100000 | War & diplomacy | Capture: target influence / this is added |
| `spy_caught_relation` | `casus_iliski_dusus` | 20 | 0 | 200 | War & diplomacy | Relation damage from caught spies |
| `spy_sabotage` | `casus_sabotaj` | 6 | 0 | 100 | War & diplomacy | Sabotage damage to defence, power and wealth |
| `wonder_min_splendour` | `harika_ihtisam` | 80 | 0 | 100 | Civilisation | Minimum splendour of a work that counts as a wonder |
| `wonder_min_power` | `harika_guc` | 7 | 0 | 12 | Civilisation | Minimum power level of a work that counts as a wonder |
| `wonder_prosperity` | `harika_refah` | 2 | 0 | 100 | Civilisation | Per-epoch prosperity a wonder gives its owner |
| `wonder_faith` | `harika_inanc` | 1 | 0 | 100 | Civilisation | Per-epoch faith a wonder gives its owner |
| `wonder_fame` | `harika_un` | 1 | 0 | 100 | Civilisation | Per-epoch fame for the owner's god |
| `wonder_envy_threshold` | `harika_kiskanclik_esik` | 10 | -100 | 100 | War & diplomacy | A neighbour below this relation envies the wonder |
| `wonder_envy_relation` | `harika_kiskanclik` | 2 | 0 | 100 | War & diplomacy | Relation lost by an envious neighbour (per epoch) |
| `wonder_war_relation` | `harika_savas_iliski` | 40 | 0 | 100 | War & diplomacy | Hostility of a neighbour that goes to war for a wonder (relation minus this) |
| `climate_first_duration` | `iklim_ilk_sure` | 3 | 1 | 100 | Population & growth | Base duration of the first climate era (epochs) |
| `climate_first_die` | `iklim_ilk_zar` | 3 | 1 | 100 | Population & growth | Die added to the first climate era (epochs) |
| `climate_duration` | `iklim_sure` | 3 | 1 | 100 | Population & growth | Base duration of a climate era (epochs) |
| `climate_die` | `iklim_zar` | 4 | 1 | 100 | Population & growth | Die added to a climate era (epochs) |
| `climate_coast_drought_divisor` | `iklim_kiyi_kurak_bolen` | 2 | 1 | 100 | Population & growth | Drought hits the coast divided by this |
| `climate_coast_rain_bonus` | `iklim_kiyi_yagmur` | 1 | 0 | 50 | Population & growth | Extra coastal fertility in a rain era |
| `climate_mountain_ice_loss` | `iklim_dag_buzul` | 3 | 0 | 50 | Population & growth | Extra fertility loss of mountainous regions in an ice era |
| `fertility_equilibrium` | `bereket_denge` | 50 | 0 | 100 | Population & growth | Long-term equilibrium value of fertility |
| `god_corpse_power` | `ceset_guc` | 8 | 1 | 12 | Creator & essence | Power level of a god's corpse |
| `god_corpse_danger` | `ceset_tehlike` | 45 | 0 | 100 | Creator & essence | Danger of a god's corpse |
| `god_corpse_fertility` | `ceset_bereket` | 30 | 0 | 100 | Creator & essence | Fertility of a god's corpse |
| `god_corpse_mystery` | `ceset_gizem` | 95 | 0 | 100 | Creator & essence | Mystery of a god's corpse |
| `god_shade_power_level` | `tanri_ruhu_guc` | 7 | 1 | 12 | Creator & essence | Power level of a dead god's shade |
| `god_shade_power` | `tanri_ruhu_stat_guc` | 70 | 0 | 100 | Creator & essence | Power stat of a dead god's shade |
| `god_shade_unrest` | `tanri_ruhu_huzursuzluk` | 75 | 0 | 100 | Creator & essence | Unrest of a dead god's shade |
| `resurrection_cult_population_fallback` | `dirilis_murit_yedek` | 500 | 0 | 1000000 | Creator & essence | Resurrection cult: population assumed for a loyal community with none recorded |
| `resurrection_cult_share` | `dirilis_murit_pay` | 10 | 0 | 100 | Creator & essence | Share (%) of loyal communities joining the resurrection cult |
| `resurrection_cult_min_followers` | `dirilis_murit_alt` | 50 | 1 | 1000000 | Creator & essence | Minimum followers of a resurrection cult |
| `resurrection_cult_max_followers` | `dirilis_murit_ust` | 1000000 | 1 | 100000000 | Creator & essence | Maximum followers of a resurrection cult |
| `resurrection_cult_power_level` | `dirilis_tarikat_guc` | 4 | 1 | 12 | Creator & essence | Resurrection cult power level |
| `resurrection_cult_zeal` | `dirilis_tarikat_bagnazlik` | 75 | 0 | 100 | Creator & essence | Resurrection cult zeal |
| `resurrection_cult_influence` | `dirilis_tarikat_etki` | 40 | 0 | 100 | Creator & essence | Resurrection cult influence |
| `dead_god_essence_divisor` | `olu_oz_bolen` | 2 | 1 | 100 | Creator & essence | A dead god's essence divided by this returns to the creator |
| `god_death_relation` | `tanri_olum_iliski` | 30 | 0 | 100 | Creator & essence | Hostility/friendship threshold toward the dead god |
| `god_death_enemy_fame` | `tanri_olum_dusman_un` | 5 | 0 | 100 | Creator & essence | Fame gained by the dead god's enemies |
| `god_death_friend_anger` | `tanri_olum_ofke` | 10 | 0 | 100 | Creator & essence | Anger gained by the dead god's friends |
| `resurrection_existence` | `dirilis_varlik` | 35 | 0 | 100 | Creator & essence | Existence of a resurrected god |
| `resurrection_hp_divisor` | `dirilis_can_bolen` | 2 | 1 | 100 | Creator & essence | Resurrected god HP: max HP / this |
| `resurrection_essence_divisor` | `dirilis_oz_bolen` | 3 | 1 | 100 | Creator & essence | Resurrected god essence: max essence / this |
| `resurrection_fame` | `dirilis_un` | 20 | 0 | 1000 | Creator & essence | Fame gained by a resurrected god |
| `resurrection_stat_loss` | `dirilis_stat_kayip` | 4 | 0 | 100 | Creator & essence | Loss in each stat of a resurrected god |
| `devotion_followers_mult` | `adanmislik_murit` | 6 | 0 | 100 | Creator & essence | Resurrection devotion: log10(followers) multiplier |
| `devotion_influence_divisor` | `adanmislik_etki_bolen` | 10 | 1 | 1000 | Creator & essence | Resurrection devotion: influence / this |
| `devotion_zeal_divisor` | `adanmislik_bagnaz_bolen` | 20 | 1 | 1000 | Creator & essence | Resurrection devotion: zeal / this |
| `devotion_cap` | `adanmislik_tavan` | 200 | 1 | 10000 | Creator & essence | Cap of resurrection devotion |
| `resurrection_devotion` | `dirilis_adanmislik` | 100 | 0 | 10000 | Creator & essence | Devotion required for the resurrection rite |
| `existence_fallback` | `varlik_yedek` | 60 | 0 | 100 | Creator & essence | Existence assumed for a son with none recorded |
| `fading_threshold` | `solus_esik` | 10 | 0 | 100 | Creator & essence | A son below this existence starts fading |
| `fading_epochs` | `solus_cag` | 3 | 1 | 50 | Creator & essence | Epochs a fading son takes to die |
| `role_farmer_leader_power` | `rol_ciftci_onder_guc` | 10 | 0 | 100 | Heroes & mortals | Born folk leader: power bias |
| `role_farmer_leader_charisma` | `rol_ciftci_onder_karizma` | 15 | 0 | 100 | Heroes & mortals | Born folk leader: charisma bias |
| `role_farmer_shepherd_agility` | `rol_ciftci_coban_ceviklik` | 15 | 0 | 100 | Heroes & mortals | Born shepherd: agility bias |
| `role_farmer_shepherd_power` | `rol_ciftci_coban_guc` | 5 | 0 | 100 | Heroes & mortals | Born shepherd: power bias |
| `role_farmer_midwife_intellect` | `rol_ciftci_ebe_akil` | 15 | 0 | 100 | Heroes & mortals | Born midwife: intellect bias |
| `role_farmer_midwife_charisma` | `rol_ciftci_ebe_karizma` | 5 | 0 | 100 | Heroes & mortals | Born midwife: charisma bias |
| `role_artisan_master_intellect` | `rol_zanaatkar_usta_akil` | 15 | 0 | 100 | Heroes & mortals | Born master artisan: intellect bias |
| `role_artisan_master_agility` | `rol_zanaatkar_usta_ceviklik` | 10 | 0 | 100 | Heroes & mortals | Born master artisan: agility bias |
| `role_artisan_smith_power` | `rol_zanaatkar_demirci_guc` | 20 | 0 | 100 | Heroes & mortals | Born smith: power bias |
| `role_artisan_architect_intellect` | `rol_zanaatkar_mimar_akil` | 20 | 0 | 100 | Heroes & mortals | Born architect: intellect bias |
| `role_merchant_merchant_intellect` | `rol_tuccar_tuccar_akil` | 10 | 0 | 100 | Heroes & mortals | Born merchant: intellect bias |
| `role_merchant_merchant_charisma` | `rol_tuccar_tuccar_karizma` | 15 | 0 | 100 | Heroes & mortals | Born merchant: charisma bias |
| `role_merchant_caravaneer_agility` | `rol_tuccar_kervanci_ceviklik` | 10 | 0 | 100 | Heroes & mortals | Born caravaneer: agility bias |
| `role_merchant_caravaneer_power` | `rol_tuccar_kervanci_guc` | 10 | 0 | 100 | Heroes & mortals | Born caravaneer: power bias |
| `role_merchant_moneychanger_intellect` | `rol_tuccar_sarraf_akil` | 20 | 0 | 100 | Heroes & mortals | Born money-changer: intellect bias |
| `role_priest_seer_intellect` | `rol_rahip_kahin_akil` | 20 | 0 | 100 | Heroes & mortals | Born seer: intellect bias |
| `role_priest_seer_charisma` | `rol_rahip_kahin_karizma` | 10 | 0 | 100 | Heroes & mortals | Born seer: charisma bias |
| `role_priest_healer_intellect` | `rol_rahip_sifaci_akil` | 15 | 0 | 100 | Heroes & mortals | Born healer: intellect bias |
| `role_priest_healer_charisma` | `rol_rahip_sifaci_karizma` | 5 | 0 | 100 | Heroes & mortals | Born healer: charisma bias |
| `role_priest_bard_charisma` | `rol_rahip_ozan_karizma` | 20 | 0 | 100 | Heroes & mortals | Born bard: charisma bias |
| `role_warrior_warrior_power` | `rol_savasci_savasci_guc` | 25 | 0 | 100 | Heroes & mortals | Born warrior: power bias |
| `role_warrior_warrior_agility` | `rol_savasci_savasci_ceviklik` | 15 | 0 | 100 | Heroes & mortals | Born warrior: agility bias |
| `role_warrior_hunter_agility` | `rol_savasci_avci_ceviklik` | 25 | 0 | 100 | Heroes & mortals | Born hunter: agility bias |
| `role_warrior_hunter_power` | `rol_savasci_avci_guc` | 10 | 0 | 100 | Heroes & mortals | Born hunter: power bias |
| `role_warrior_guard_power` | `rol_savasci_muhafiz_guc` | 20 | 0 | 100 | Heroes & mortals | Born guard: power bias |
| `role_warrior_guard_charisma` | `rol_savasci_muhafiz_karizma` | 5 | 0 | 100 | Heroes & mortals | Born guard: charisma bias |
| `role_scribe_sage_intellect` | `rol_katip_bilge_akil` | 25 | 0 | 100 | Heroes & mortals | Born sage: intellect bias |
| `role_scribe_historian_intellect` | `rol_katip_tarihci_akil` | 20 | 0 | 100 | Heroes & mortals | Born historian: intellect bias |
| `role_scribe_historian_charisma` | `rol_katip_tarihci_karizma` | 5 | 0 | 100 | Heroes & mortals | Born historian: charisma bias |
| `role_scribe_cartographer_intellect` | `rol_katip_haritaci_akil` | 15 | 0 | 100 | Heroes & mortals | Born cartographer: intellect bias |
| `role_scribe_cartographer_agility` | `rol_katip_haritaci_ceviklik` | 10 | 0 | 100 | Heroes & mortals | Born cartographer: agility bias |
| `birth_stat_base` | `dogum_stat_taban` | 35 | 0 | 100 | Heroes & mortals | Base stat of a born notable mortal |
| `birth_stat_die` | `dogum_stat_zar` | 30 | 1 | 100 | Heroes & mortals | Die added to a born notable mortal's stats |
| `birth_lifespan` | `dogum_omur` | 60 | 1 | 50000 | Heroes & mortals | Base lifespan of a born notable mortal (years) |
| `birth_lifespan_die` | `dogum_omur_zar` | 45 | 1 | 50000 | Heroes & mortals | Die added to a born notable mortal's lifespan (years) |
| `birth_power_share` | `dogum_guc_pay` | 70 | 0 | 200 | Heroes & mortals | Born mortal power level: share (%) of community's |
| `birth_power_max` | `dogum_guc_ust` | 6 | 1 | 12 | Heroes & mortals | Highest power level of a born mortal |
| `birth_age_min_share` | `dogum_yas_alt` | 18 | 0 | 100 | Heroes & mortals | Born mortal age: minimum share (%) of lifespan |
| `birth_age_range_share` | `dogum_yas_aralik` | 20 | 0 | 100 | Heroes & mortals | Born mortal age: random share (%) of lifespan added |
| `birth_hp` | `dogum_can` | 100 | 1 | 1000 | Heroes & mortals | Born mortal HP |
| `notable_cap_ratio` | `unlu_oran` | 80 | 0 | 1000 | Heroes & mortals | Per-epoch notable cap: share (%) of community count |
| `notable_cap_min` | `unlu_alt` | 2 | 0 | 100 | Heroes & mortals | Lowest per-epoch notable cap |
| `notable_living_base` | `unlu_yasayan_taban` | 2 | 0 | 100 | Heroes & mortals | Living notables per community: base (+ log10 population) |
| `notable_crowd_bonus_max` | `unlu_kalabalik_ust` | 25 | 0 | 100 | Heroes & mortals | Max contribution (%) of crowd size to notable chance |
| `notable_crowd_divisor` | `unlu_kalabalik_bolen` | 25 | 1 | 1000 | Heroes & mortals | Crowd contribution: log10(population) / this |
| `notable_warrior_lifespan` | `unlu_savasci_omur` | 10 | 0 | 500 | Heroes & mortals | Extra lifespan (years) of a notable born from the warrior class |
| `ruler_charisma` | `hukumdar_karizma` | 20 | 0 | 100 | Heroes & mortals | Charisma bias of a new ruler |
| `ruler_intellect` | `hukumdar_akil` | 10 | 0 | 100 | Heroes & mortals | Intellect bias of a new ruler |
| `ruler_lifespan` | `hukumdar_omur` | 10 | 0 | 500 | Heroes & mortals | Extra lifespan (years) of a new ruler |
| `village_cap` | `koy_tavan` | 2 | 0 | 50 | Population & growth | Max new villages per epoch |
| `village_first_chance` | `koy_ilk_sans` | 60 | 0 | 100 | Population & growth | Chance (%) a people with no homeland founds its first |
| `village_extra_chance` | `koy_ek_sans` | 30 | 0 | 100 | Population & growth | Chance (%) a populous people founds an extra village |
| `village_migration_share` | `koy_goc_pay` | 8 | 0 | 100 | Population & growth | Share (%) of population migrating to a new village |
| `village_prosperity` | `koy_refah` | 40 | 0 | 100 | Population & growth | New village prosperity |
| `village_defence` | `koy_savunma` | 20 | 0 | 100 | Population & growth | New village defence |
| `derived_power_min` | `turev_guc_alt` | 2 | 1 | 12 | Population & growth | Lowest power level of derived settlement, people, work and faction |
| `new_people_cap` | `yeni_halk_tavan` | 1 | 0 | 20 | Population & growth | Max new peoples per epoch (ethnogenesis or sapience) |
| `ethnogenesis_population_share` | `etnogenez_nufus_pay` | 50 | 0 | 100 | Population & growth | Population moving to the split-off people: share (%) of settlement (subtracted from settlement) |
| `ethno_stat_base` | `etno_stat_taban` | 30 | 0 | 100 | Population & growth | Split-off people's martiality and craft base |
| `ethno_stat_die` | `etno_stat_zar` | 40 | 1 | 100 | Population & growth | Die added to split-off people's martiality and craft |
| `ethno_magic_die` | `etno_buyu_zar` | 50 | 1 | 100 | Population & growth | Split-off people's magic (die) |
| `sapience_min_intelligence` | `akillanma_zeka` | 70 | 0 | 100 | Creatures | Minimum intelligence of a species able to become a people |
| `sapient_population` | `akil_nufus` | 800 | 1 | 10000000 | Creatures | Base population of a people born from a sapient species |
| `sapient_population_die` | `akil_nufus_zar` | 3000 | 1 | 10000000 | Creatures | Die added to that people's population |
| `sapient_power_fallback` | `akil_guc_yedek` | 40 | 0 | 100 | Creatures | Sapient species: power assumed if unrecorded |
| `sapient_martial_die` | `akil_savas_zar` | 20 | 1 | 100 | Creatures | Die added to sapient people's martiality |
| `sapient_magic_die` | `akil_buyu_zar` | 60 | 1 | 100 | Creatures | Sapient people's magic (die) |
| `sapient_craft_die` | `akil_zanaat_zar` | 40 | 1 | 100 | Creatures | Sapient people's craft (die) |
| `sapient_faith` | `akil_inanc` | 30 | 0 | 100 | Creatures | Sapient people's base faith |
| `sapient_faith_die` | `akil_inanc_zar` | 40 | 1 | 100 | Creatures | Die added to sapient people's faith |
| `script_alphabet_base` | `yazi_alfabe_taban` | 2 | 0 | 100 | Religion & language | Script choice: alphabet base weight |
| `script_alphabet_divisor` | `yazi_alfabe_bolen` | 4 | 1 | 1000 | Religion & language | Alphabet weight: merchant share / this |
| `script_syllabary_base` | `yazi_hece_taban` | 2 | 0 | 100 | Religion & language | Script choice: syllabary base weight |
| `script_syllabary_divisor` | `yazi_hece_bolen` | 20 | 1 | 1000 | Religion & language | Syllabary weight: language complexity / this |
| `script_pictographic_base` | `yazi_resim_taban` | 1 | 0 | 100 | Religion & language | Script choice: pictographic base weight |
| `script_pictographic_divisor` | `yazi_resim_bolen` | 15 | 1 | 1000 | Religion & language | Pictographic weight: language sacredness / this |
| `script_knot_base` | `yazi_dugum_taban` | 2 | 0 | 100 | Religion & language | Script choice: knot-script base weight |
| `script_knot_divisor` | `yazi_dugum_bolen` | 30 | 1 | 1000 | Religion & language | Knot-script weight: farmer share / this |
| `script_notch_base` | `yazi_oyma_taban` | 1 | 0 | 100 | Religion & language | Script choice: notch-script base weight |
| `script_notch_divisor` | `yazi_oyma_bolen` | 8 | 1 | 1000 | Religion & language | Notch-script weight: priest share / this |
| `script_complexity_gain` | `yazi_karmasiklik` | 8 | 0 | 100 | Religion & language | Complexity gain of a language that gains a script |
| `script_complexity_fallback` | `yazi_karmasiklik_yedek` | 30 | 0 | 100 | Religion & language | Complexity assumed for a language with none recorded |
| `manifest_creature_hp` | `tez_tur_can` | 200 | 1 | 100000 | Religion & language | Creature born of legend: base HP |
| `manifest_creature_hp_die` | `tez_tur_can_zar` | 300 | 1 | 100000 | Religion & language | Creature born of legend: HP die |
| `manifest_creature_power` | `tez_tur_guc` | 50 | 0 | 100 | Religion & language | Creature born of legend: base power |
| `manifest_creature_power_die` | `tez_tur_guc_zar` | 40 | 1 | 100 | Religion & language | Creature born of legend: power die |
| `manifest_creature_agility` | `tez_tur_ceviklik` | 30 | 0 | 100 | Religion & language | Creature born of legend: base agility |
| `manifest_creature_agility_die` | `tez_tur_ceviklik_zar` | 40 | 1 | 100 | Religion & language | Creature born of legend: agility die |
| `manifest_creature_intelligence` | `tez_tur_zeka` | 20 | 0 | 100 | Religion & language | Creature born of legend: base intelligence |
| `manifest_creature_intelligence_die` | `tez_tur_zeka_zar` | 40 | 1 | 100 | Religion & language | Creature born of legend: intelligence die |
| `manifest_creature_danger` | `tez_tur_tehlike` | 55 | 0 | 100 | Religion & language | Creature born of legend: base danger |
| `manifest_creature_danger_die` | `tez_tur_tehlike_zar` | 35 | 1 | 100 | Religion & language | Creature born of legend: danger die |
| `manifest_spirit_power` | `tez_ruh_guc` | 40 | 0 | 100 | Religion & language | Spirit born of belief: base power |
| `manifest_spirit_power_die` | `tez_ruh_guc_zar` | 40 | 1 | 100 | Religion & language | Spirit born of belief: power die |
| `manifest_spirit_unrest` | `tez_ruh_huzursuzluk` | 40 | 0 | 100 | Religion & language | Spirit born of belief: base unrest |
| `manifest_spirit_unrest_die` | `tez_ruh_huzursuzluk_zar` | 40 | 1 | 100 | Religion & language | Spirit born of belief: unrest die |
| `manifest_resource_abundance` | `tez_kaynak_bolluk` | 50 | 0 | 100 | Religion & language | Hallowed resource: base abundance |
| `manifest_resource_abundance_die` | `tez_kaynak_bolluk_zar` | 40 | 1 | 100 | Religion & language | Hallowed resource: abundance die |
| `manifest_resource_value` | `tez_kaynak_deger` | 40 | 0 | 100 | Religion & language | Hallowed resource: base value |
| `manifest_resource_value_die` | `tez_kaynak_deger_zar` | 40 | 1 | 100 | Religion & language | Hallowed resource: value die |
| `manifest_resource_might` | `tez_kaynak_kudret` | 30 | 0 | 100 | Religion & language | Hallowed resource: base might |
| `manifest_resource_might_die` | `tez_kaynak_kudret_zar` | 50 | 1 | 100 | Religion & language | Hallowed resource: might die |
| `manifest_item_damage_die` | `tez_esya_hasar_zar` | 40 | 1 | 100 | Religion & language | Relic from legend: damage (die) |
| `manifest_item_protection_die` | `tez_esya_koruma_zar` | 40 | 1 | 100 | Religion & language | Relic from legend: protection (die) |
| `manifest_item_might` | `tez_esya_kudret` | 40 | 0 | 100 | Religion & language | Relic from legend: base might |
| `manifest_item_might_die` | `tez_esya_kudret_zar` | 50 | 1 | 100 | Religion & language | Relic from legend: might die |
| `manifest_item_curse_die` | `tez_esya_lanet_zar` | 30 | 1 | 100 | Religion & language | Relic from legend: curse (die) |
| `legend_spread_fallback` | `efsane_yayginlik_yedek` | 30 | 0 | 100 | Religion & language | Spread assumed for a legend with none recorded |
| `legend_teller_gain` | `efsane_anlatan` | 2 | 0 | 100 | Religion & language | Per-epoch legend spread gain per teller |
| `legend_decay` | `efsane_sonme` | 2 | 0 | 100 | Religion & language | Per-epoch legend spread decay |
| `tradition_grace` | `gelenek_mehil` | 3 | 0 | 100 | Religion & language | Grace period (epochs) before a new tradition starts fading |
| `tradition_spread_fallback` | `gelenek_yayginlik_yedek` | 40 | 0 | 100 | Religion & language | Spread assumed for a tradition with none recorded |
| `tradition_celebrant_cap` | `gelenek_kutlayan_ust` | 2 | 1 | 100 | Religion & language | Tradition: this many celebrants raise spread by 1 (fewer preserve it) |
| `tradition_decay` | `gelenek_sonme` | 2 | 0 | 100 | Religion & language | Per-epoch decay of a tradition with no celebrants |
| `engine_tradition_decay` | `gelenek_dunya_sonme` | 4 | 0 | 100 | Religion & language | Per-epoch decay of an engine-made tradition with no celebrants |
| `prophecy_forget_age` | `kehanet_unutulma` | 20 | 0 | 1000 | Religion & language | Epochs after which an unfulfilled prophecy is forgotten (0 never) |
| `tradition_forget_spread` | `gelenek_unutma` | 5 | 0 | 100 | Religion & language | A tradition with no celebrants is forgotten at or below this spread |
| `fairytale_forget_spread` | `masal_unutma_yayginlik` | 3 | 0 | 100 | Religion & language | An old fairy tale is forgotten at or below this spread |
| `fairytale_forget_age` | `masal_unutma_cag` | 15 | 0 | 1000 | Religion & language | Age (epochs) at which a fairy tale can be forgotten |
| `manifestation_cap` | `tezahur_tavan` | 1 | 0 | 20 | Religion & language | Max legends becoming real per epoch |
| `manifestation_min_spread` | `tezahur_yayginlik` | 70 | 0 | 100 | Religion & language | Minimum spread of a legend that can become real |
| `manifestation_power_max` | `tezahur_guc_ust` | 8 | 1 | 12 | Religion & language | Highest power level of something born from legend |
| `manifestation_power_bonus` | `tezahur_guc_ek` | 1 | 0 | 12 | Religion & language | Power level of the manifestation above the legend's |
| `legend_power_gap` | `efsane_guc_fark` | 1 | 0 | 12 | Religion & language | Legend born from an event is this much below the event's power level |
| `legend_event_min_age` | `efsane_olay_yas` | 5 | 0 | 1000 | Religion & language | Minimum age (epochs) of an event that can become a legend |
| `legend_event_min_violence` | `efsane_siddet` | 60 | 0 | 100 | Religion & language | Minimum violence of an event that can become a legend |
| `legendification_cap` | `efsanelesme_tavan` | 1 | 0 | 20 | Religion & language | Max events becoming legends per epoch |
| `legend_spread_base` | `efsane_yayginlik` | 45 | 0 | 100 | Religion & language | Base spread of a legend born from an event |
| `legend_spread_die` | `efsane_yayginlik_zar` | 25 | 1 | 100 | Religion & language | Die added to that spread |
| `fairytale_min_age` | `masal_cag` | 10 | 0 | 1000 | Religion & language | Age (epochs) for a legend to become a fairy tale |
| `fairytale_spread` | `masal_yayginlik` | 50 | 0 | 100 | Religion & language | An old legend below this spread becomes a fairy tale |
| `fairytale_keeper_distance` | `masal_koruyucu_mesafe` | 3 | 0 | 20 | Religion & language | Distance (map steps) within which a sage or bard preserves a legend |
| `life_min_fertility` | `yasam_bereket` | 30 | 0 | 100 | Population & growth | Minimum fertility of a region where life appears spontaneously |
| `life_region_pick` | `yasam_bolge_secim` | 2 | 1 | 100 | Population & growth | Life appears in one of the N most fertile regions |
| `native_people_power_level` | `yerli_halk_guc` | 3 | 1 | 12 | Population & growth | Native people power level |
| `native_people_population` | `yerli_halk_nufus` | 400 | 1 | 10000000 | Population & growth | Native people base population |
| `native_people_population_die` | `yerli_halk_nufus_zar` | 500 | 1 | 10000000 | Population & growth | Die added to native people population |
| `native_people_stat` | `yerli_halk_stat` | 20 | 0 | 100 | Population & growth | Native people martiality, magic and craft base |
| `native_people_stat_die` | `yerli_halk_stat_zar` | 40 | 1 | 100 | Population & growth | Die added to native people martiality, magic and craft |
| `native_people_faith` | `yerli_halk_inanc` | 30 | 0 | 100 | Population & growth | Native people base faith |
| `native_people_faith_die` | `yerli_halk_inanc_zar` | 40 | 1 | 100 | Population & growth | Die added to native people faith |
| `native_species_power_level` | `yerli_tur_guc` | 2 | 1 | 12 | Creatures | Native species power level |
| `native_species_hp` | `yerli_tur_can` | 60 | 1 | 100000 | Creatures | Native species base HP |
| `native_species_hp_die` | `yerli_tur_can_zar` | 60 | 1 | 100000 | Creatures | Die added to native species HP |
| `native_species_power` | `yerli_tur_stat_guc` | 20 | 0 | 100 | Creatures | Native species base power |
| `native_species_power_die` | `yerli_tur_guc_zar` | 50 | 1 | 100 | Creatures | Die added to native species power |
| `native_species_agility` | `yerli_tur_ceviklik` | 20 | 0 | 100 | Creatures | Native species base agility |
| `native_species_agility_die` | `yerli_tur_ceviklik_zar` | 60 | 1 | 100 | Creatures | Die added to native species agility |
| `native_species_intelligence` | `yerli_tur_zeka` | 5 | 0 | 100 | Creatures | Native species base intelligence |
| `native_species_intelligence_die` | `yerli_tur_zeka_zar` | 30 | 1 | 100 | Creatures | Die added to native species intelligence |
| `native_species_danger` | `yerli_tur_tehlike` | 10 | 0 | 100 | Creatures | Native species base danger |
| `native_species_danger_die` | `yerli_tur_tehlike_zar` | 50 | 1 | 100 | Creatures | Die added to native species danger |
| `language_region_weight` | `dil_bolge_agirlik` | 3 | 1 | 100 | Religion & language | Nearest language: weight of a speaker in the same region |
| `god_region_weight` | `tanri_bolge_agirlik` | 3 | 1 | 100 | Religion & language | First faith: weight of a worshipper in the same region (elsewhere 1) |
| `first_faith_chance` | `ilk_inanc_sans` | 60 | 0 | 100 | Religion & language | Chance (%) a faithless community binds to a god this epoch (else stays a godlessness candidate; retries next epoch) |
| `first_faith_exponent` | `ilk_inanc_us` | 50 | 0 | 100 | Religion & language | First faith crowd pull: god weight = worshipper weight ^ (this/100); 100 linear, lower = diminishing |
| `first_faith_son_weight` | `ilk_inanc_ogul` | 2 | 0 | 100 | Religion & language | First faith: base weight of every active son in that world (young sons with no worshippers get a share) |
| `primitive_language_spread` | `ilkel_yayginlik` | 5 | 0 | 100 | Religion & language | Primitive language spread |
| `primitive_language_complexity` | `ilkel_karmasiklik` | 15 | 0 | 100 | Religion & language | Primitive language complexity |
| `primitive_language_sacredness` | `ilkel_kutsallik` | 10 | 0 | 100 | Religion & language | Primitive language sacredness |
| `ruin_resettle_min_population` | `harabe_nufus_alt` | 60 | 1 | 1000000 | Population & growth | Minimum population of a resettled ruin |
| `ruin_resettle_prosperity` | `harabe_refah` | 30 | 0 | 100 | Population & growth | Prosperity of a resettled ruin |
| `ruin_resettle_min_defence` | `harabe_savunma_alt` | 15 | 0 | 100 | Population & growth | Minimum defence of a resettled ruin |
| `ruin_defence_fallback` | `harabe_savunma_yedek` | 20 | 0 | 100 | Population & growth | Defence assumed for a ruin with none recorded |
| `ruin_defence_divisor` | `harabe_savunma_bolen` | 2 | 1 | 100 | Population & growth | A resettled ruin gets old defence / this |
| `refugee_min_population` | `multeci_nufus` | 600 | 0 | 10000000 | Population & growth | Minimum population of a community that can send refugees |
| `refugee_cap` | `multeci_tavan` | 1 | 0 | 20 | Population & growth | Max refugee migrations per epoch |
| `refugee_disaster_violence` | `multeci_afet_siddet` | 60 | 0 | 100 | Population & growth | Minimum violence of a disaster that creates refugees |
| `refugee_min_count` | `multeci_en_az` | 50 | 1 | 1000000 | Population & growth | Minimum people in a refugee migration |
| `refugee_weight_ally` | `multeci_muttefik_agirlik` | 3 | 0 | 100 | Population & growth | Refugee target: ally weight |
| `refugee_weight_language` | `multeci_dil_agirlik` | 2 | 0 | 100 | Population & growth | Refugee target: same-language weight |
| `refugee_weight_god` | `multeci_tanri_agirlik` | 1 | 0 | 100 | Population & growth | Refugee target: same-god weight |
| `refugee_weight_other_region` | `multeci_uzak_agirlik` | 1 | 0 | 100 | Population & growth | Refugee target: other-region weight |
| `spirit_unrest_fallback` | `ruh_huzursuzluk_yedek` | 40 | 0 | 100 | Beyond (afterlife) | Unrest assumed for a spirit with none recorded |
| `spirit_rest_min_age` | `ruh_dinme_yas` | 2 | 0 | 100 | Beyond (afterlife) | Age (epochs) at which a spirit can come to rest |
| `spirit_crossing_min_age` | `ruh_gecis_yas` | 1 | 0 | 100 | Beyond (afterlife) | Age (epochs) at which a spirit can cross to the land of the dead |
| `language_death_grace` | `dil_olum_mehil` | 2 | 0 | 100 | Religion & language | Grace period (epochs) before a new language can count as dead |
| `language_death_note_cap` | `dil_olum_not_tavan` | 3 | 0 | 100 | Chronicle | Max language deaths written to chronicle per epoch |
| `temple_min_faith` | `tapinak_inanc` | 50 | 0 | 100 | Civilisation | Minimum faith of a community that builds a temple |
| `temple_min_priest_share` | `tapinak_rahip` | 6 | 0 | 100 | Civilisation | Minimum priest share (%) of a community that builds a temple |
| `temple_faith_gain` | `tapinak_inanc_artis` | 8 | 0 | 100 | Civilisation | Faith contribution of a temple |
| `wall_defence_fallback` | `sur_savunma_yedek` | 30 | 0 | 100 | Civilisation | Defence assumed for a settlement with none recorded |
| `wall_build_threshold` | `sur_savunma` | 55 | 0 | 100 | Civilisation | A settlement below this defence builds walls |
| `wall_defence_gain` | `sur_artis` | 15 | 0 | 100 | Civilisation | Defence contribution of walls |
| `library_min_scribe_share` | `kutuphane_katip` | 7 | 0 | 100 | Civilisation | Minimum scribe share (%) of a community that builds a library |
| `work_people_prosperity_base` | `yapit_halk_refah` | 40 | 0 | 100 | Civilisation | A people's assumed prosperity: base |
| `work_people_craft_divisor` | `yapit_halk_zanaat_bolen` | 4 | 1 | 1000 | Civilisation | A people's assumed prosperity: craft / this |
| `work_town_min_population` | `yapit_kent_nufus` | 800 | 0 | 10000000 | Civilisation | Minimum population of a settlement able to build a work |
| `work_people_min_population` | `yapit_halk_nufus` | 2000 | 0 | 100000000 | Civilisation | Minimum population of a people able to build a work |
| `work_min_artisan_share` | `yapit_zanaatkar` | 13 | 0 | 100 | Civilisation | Minimum artisan share (%) to build a work |
| `work_min_craft` | `yapit_zanaat` | 50 | 0 | 100 | Civilisation | Minimum craft to build a work |
| `work_power_share` | `yapit_guc_pay` | 80 | 0 | 200 | Civilisation | Work power level: share (%) of builder's |
| `work_power_max` | `yapit_guc_ust` | 7 | 1 | 12 | Civilisation | Highest power level of an engine-built work |
| `work_splendour_base` | `yapit_ihtisam` | 25 | 0 | 100 | Civilisation | Base splendour of a new work |
| `work_splendour_die` | `yapit_ihtisam_zar` | 30 | 1 | 100 | Civilisation | Die added to a new work's splendour |
| `work_architecture_bonus` | `yapit_mimarlik_ek` | 10 | 0 | 100 | Civilisation | Extra splendour for a builder who knows architecture |
| `work_durability_base` | `yapit_saglamlik` | 45 | 0 | 100 | Civilisation | Base durability of a new work |
| `work_durability_die` | `yapit_saglamlik_zar` | 35 | 1 | 100 | Civilisation | Die added to a new work's durability |
| `work_function_base` | `yapit_islev` | 40 | 0 | 100 | Civilisation | Base function of a new work |
| `work_function_die` | `yapit_islev_zar` | 40 | 1 | 100 | Civilisation | Die added to a new work's function |
| `work_prosperity_cost` | `yapit_refah_bedel` | 4 | 0 | 100 | Civilisation | Prosperity cost of building a work |
| `work_goods_fallback` | `yapit_mal_yedek` | 20 | 0 | 1000 | Civilisation | Goods assumed for a community with no storage record |
| `work_goods_cost` | `yapit_mal_bedel` | 15 | 0 | 1000 | Civilisation | Goods cost of building a work |
| `splendour_min_owner_prosperity` | `ihtisam_refah` | 50 | 0 | 100 | Civilisation | Minimum prosperity of an owner who adorns their work |
| `splendour_fallback` | `ihtisam_yedek` | 30 | 0 | 100 | Civilisation | Splendour assumed for a work with none recorded |
| `splendour_artisan_share` | `ihtisam_zanaatkar` | 16 | 0 | 100 | Civilisation | Minimum artisan share (%) of owner for extra splendour |
| `splendour_artisan_bonus` | `ihtisam_zanaatkar_ek` | 2 | 0 | 100 | Civilisation | Per-epoch extra splendour for an artisan-rich owner |
| `splendour_architecture_bonus` | `ihtisam_mimarlik_ek` | 1 | 0 | 100 | Civilisation | Per-epoch extra splendour for an owner who knows architecture |
| `guild_min_merchant_share` | `lonca_tuccar` | 11 | 0 | 100 | War & diplomacy | Minimum merchant share (%) of a community founding a guild |
| `guild_min_prosperity` | `lonca_refah` | 45 | 0 | 100 | War & diplomacy | Minimum prosperity of a community founding a guild |
| `guild_power` | `lonca_guc` | 25 | 0 | 100 | War & diplomacy | Merchant guild base power |
| `guild_wealth` | `lonca_servet` | 55 | 0 | 100 | War & diplomacy | Merchant guild base wealth |
| `guild_influence` | `lonca_nufuz` | 45 | 0 | 100 | War & diplomacy | Merchant guild base influence |
| `council_min_priest_share` | `meclis_rahip` | 10 | 0 | 100 | War & diplomacy | Minimum priest share (%) of a community founding a priests' council |
| `council_power` | `meclis_guc` | 20 | 0 | 100 | War & diplomacy | Priests' council base power |
| `council_wealth` | `meclis_servet` | 30 | 0 | 100 | War & diplomacy | Priests' council base wealth |
| `council_influence` | `meclis_nufuz` | 55 | 0 | 100 | War & diplomacy | Priests' council base influence |
| `brotherhood_min_warrior_share` | `birlik_savasci` | 14 | 0 | 100 | War & diplomacy | Minimum warrior share (%) of a community founding a warrior brotherhood |
| `brotherhood_war_warrior_share` | `birlik_savasta_savasci` | 11 | 0 | 100 | War & diplomacy | Minimum warrior share (%) for a community at war |
| `brotherhood_power` | `birlik_guc` | 55 | 0 | 100 | War & diplomacy | Warrior brotherhood base power |
| `brotherhood_wealth` | `birlik_servet` | 25 | 0 | 100 | War & diplomacy | Warrior brotherhood base wealth |
| `brotherhood_influence` | `birlik_nufuz` | 40 | 0 | 100 | War & diplomacy | Warrior brotherhood base influence |
| `uprising_disband_min_age` | `isyan_dagilma_mehil` | 2 | 0 | 100 | War & diplomacy | Age (epochs) at which an uprising can disband |
| `uprising_disband_note_cap` | `hizip_dagilma_not_tavan` | 2 | 0 | 100 | War & diplomacy | Max disbanded uprisings written to chronicle per epoch |
| `faction_min_population` | `hizip_nufus` | 1000 | 0 | 100000000 | War & diplomacy | Minimum population of a community that can spawn a faction |
| `faction_power_share` | `hizip_guc_pay` | 70 | 0 | 200 | War & diplomacy | Faction power level: share (%) of community's |
| `faction_power_max` | `hizip_guc_ust` | 6 | 1 | 12 | War & diplomacy | Highest power level of an engine-founded faction |
| `faction_stat_die` | `hizip_stat_zar` | 25 | 1 | 100 | War & diplomacy | Die added to a new faction's stats |
| `faction_stat_shift` | `hizip_stat_kayma` | 5 | 0 | 100 | War & diplomacy | Subtracted from a new faction's stats after the die |
| `preaching_base` | `din_vaaz_taban` | 2 | 0 | 100 | Religion & language | Base chance (%) of conversion via cult preaching |
| `preaching_influence_divisor` | `din_vaaz_etki_bolen` | 800 | 1 | 100000 | Religion & language | Preaching chance: cult influence / this |
| `preaching_followers_max` | `din_vaaz_murit_ust` | 8 | 0 | 100 | Religion & language | Max contribution (%) of followers to preaching chance |
| `preaching_followers_floor` | `din_vaaz_murit_alt` | 500 | 1 | 1000000 | Religion & language | Preaching chance: followers / at least this |
| `preaching_population_mult` | `din_vaaz_nufus_carpan` | 4 | 1 | 1000 | Religion & language | Preaching chance: followers / (population × this) |
| `conversion_fame_divisor` | `din_un_bolen` | 1500 | 1 | 1000000 | Religion & language | Conversion: fame difference between gods / this |
| `conversion_seeker_bonus` | `din_arayan_ek` | 10 | 0 | 100 | Religion & language | Conversion bonus (%) for a god-seeking community |
| `culture_first_word` | `kultur_ilk_kelime` | 80 | 0 | 100 | Religion & language | Loanword on first contact (%) |
| `culture_word` | `kultur_kelime` | 50 | 0 | 100 | Religion & language | Loanword on trade contact (%) |
| `culture_first_tradition` | `kultur_ilk_gelenek` | 50 | 0 | 100 | Religion & language | Tradition transfer on first contact (%) |
| `culture_tradition` | `kultur_gelenek` | 25 | 0 | 100 | Religion & language | Tradition transfer on trade contact (%) |
| `culture_first_knowledge` | `kultur_ilk_bilgi` | 40 | 0 | 100 | Religion & language | Knowledge transfer on first contact (%) |
| `culture_knowledge` | `kultur_bilgi` | 10 | 0 | 100 | Religion & language | Knowledge transfer on trade contact (%) |
| `culture_first_god` | `kultur_ilk_tanri` | 30 | 0 | 100 | Religion & language | God transfer on first contact (%) |
| `culture_god` | `kultur_tanri` | 6 | 0 | 100 | Religion & language | God transfer on trade contact (%) |
| `world_age_doom_relief` | `dunya_yasi_kiyamet` | 2 | 0 | 50 | Doom | How much a world-age milestone pushes the doom clock back |
| `golden_age_min_world_age` | `altin_mehil` | 3 | 0 | 1000 | Civilisation | Minimum world age (epochs) to enter a golden age |
| `golden_age_prosperity_gain` | `altin_refah_artis` | 1 | 0 | 100 | Civilisation | Per-epoch prosperity gain of communities in a golden age |
| `golden_age_chronicle_links` | `altin_kronik_bag` | 6 | 0 | 100 | Chronicle | Max communities linked to the golden-age chronicle entry |

---

## 35. Known bugs, design smells, and how the new design should avoid them

1. **Siege starvation morale applied to the wrong army.** In the "attacker won but walls hold" branch the code lowers `ol.morale` — `ol` is the *loser's* (defender's) army — while the rule `siege_attacker_morale_loss` says the attacker loses morale. Decide intended behaviour (likely: attacker's army `ow` loses morale) and fix.
2. **Tribute bypasses diminishing returns.** Tribute adds prosperity directly (`+tribute_flow`), while the codebase rule is that every prosperity gain goes through `refahEkle`. Use the shared prosperity-gain function.
3. **Syncretism is only a tag** (`senkretik:<id>`); it is not counted as worship anywhere (patron lookup, worship counts, dominance). Model secondary worship as a real relation with a weight.
4. **Patron fallback to creator son** (`hami`) makes "has no god" rare; "seeker" logic relies on tags. Separate "worships" from "was created by".
5. **Relations read with side effects**: `tIliski` inserts a row on first read (even from prompt builders like firsatlar.js). Compute the initial value on read without writing, or materialise rows in the engine only.
6. **War membership via JSON tags** (`taraf:<id>`, `savas:<id>`, `suruyor`) queried with `LIKE` — slow and fragile. Use relational tables: `wars(id, status, start, end, result, score, battles, violence, last_clash)`, `war_sides(war_id, community_id)`, `armies(war_id, side_id, …)`.
7. **Hero/side scans are O(N²)**: `kahramanlariOf` filters all canon entities and runs `tarafOf` (several queries) per mortal, many times per battle and per diplomacy pair. Cache side membership per epoch (`mortal → side` map).
8. **Biased shuffles**: `array.sort(() => Math.random() − 0.5)` (seferler hostile pairs, dogumlar notable loop). Use Fisher–Yates with the seeded RNG. The engine depends on a seeded `Math.random` for determinism — in the new design pass an explicit seeded RNG.
9. **Per-world laws checked on one side only**: battle chance uses `Y.has('war_ban', a)` (a's world only); golden-age "war now" only checks the bond source's world.
10. **Cumulative society effects**: every epoch prosperity/faith/defence/martiality get `+(share − base)/divisor` again, so stats ratchet to the clamps for skewed societies. Consider applying the effect as an offset toward a target rather than an increment.
11. **Craft test trivially true**: `work_min_artisan_share` (13) is below the base artisan share (15), and factions/cults always get the default society — the "craft" requirement for works almost always passes. Also every `toplumOf` on factions/cults returns defaults (e.g. dark-age scribe protection never applies to them).
12. **Ruin check treats missing population as 0** (`(population || 0) < ruin_threshold`) — settlements without a population stat are abandoned after the grace period. Require an explicit population.
13. **Event-born legends never manifest**: legendified events get no location and their only `tells_of` bond points to an event (not a place), so the manifestation step cannot find a place for them.
14. **Thread quests** succeed without closing the story thread or removing the hero's `iplik:<id>` tag.
15. **Undefined-equality matches**: thread eligibility compares `topRegion(x)?.id === topRegion(h)?.id` (both undefined → true); companions allow two side-less heroes (`null === null`).
16. **Refugee target population unclamped** (`target.population += n`).
17. **Turkish-text parsing as logic** (LANGUAGE-SPECIFIC, drop): ore detection by name regex, manifestation kind by legend text regex, existing-work kind by name regex, hero test by subtype regex, keeper (sage/bard…) by subtype regex, death epoch parsed from "Çağ N" in fate notes, the `"[Dünya motoru]"` description marker, `'yurdu'` / `'mağlup'` / `'…fethi'` description strings used as semantic flags. Replace with enums/columns: `resource.category`, `legend.category`, `work.kind`, `mortal.role`, `bond.role` (`victor/loser/homeland/conquest`), `entity.death_epoch`, `entity.origin='engine'`.
18. **Rule groups re-declared** with empty `tanimla('DERIN', {})` in other modules to read keys owned here; and some keys owned here are only used elsewhere. Provide a single typed settings registry; move keys to their consumer modules.
19. **Unused tunable** `dead_bond_note_threshold` (`olu_bag_not`).
20. **Mixed responsibilities**: one 2,700-line file holds a dozen subsystems plus generic helpers (`kayitAc`, `oldur`, tags). Split into: `entities` (create/kill/tags), `relations`, `diplomacy`, `warfare`, `economy`, `heroes`, `knowledge`, `climate`, `divinity` (death/resurrection/fading), `demography` (births/villages/ethnogenesis/refugees/ruins), `culture` (language/writing/religion/legend).
21. **Hard-coded thresholds left in code** (contrary to the "no unconfigurable constants" rule): `−50` midpoint for justice, `100` price base, `0.5` direction coin in culture exchange, `2`-epoch wording switch in war-cap notes, `4000` Roman numeral limit, fading warnings at `left == 2/1`, `ILK_SOZLER` list and syllable suffixes, `log10(max(10, …))` floors, the 8-ancestor limit in `mesafe` and its `99` sentinel.
22. **Swallowed errors** (`try {} catch {}`) around `seferBitir` in exhaustion peace and around `kozmikMahkeme`; log them instead.
23. **`savasIlan` does not enforce the per-community war cap**; each caller must remember to check. Put both caps inside one `canOpenWar` with explicit opt-outs (`ignoreWorldCap` for civil wars).
24. **Exhaustion peace double path**: long wars can end in diplomacy (§8.7), neighbour peace (§8.8b), war-cap enforcement (§9.1) and in-battle exhaustion (§10.4) — four independent exits with different relation bonuses. Consider one "war resolution" service.

---

## 36. Open questions for the integrator

- Keep or fix the siege-morale target (§35.1) and tribute diminishing returns (§35.2)?
- Should syncretism become a first-class weighted worship relation (§35.3)?
- Replace Turkish-regex classifications with explicit categories set at creation time (needs the creating modules/LLM tools to supply `category`)?
- Suggested English rule-group names (`deep_engine`, `deep_relations`, `deep_campaign`, `deep_society`, `deep_life`) vs. regrouping by subsystem (recommended, see §35.20).
- Whether `notable_cap_min` > `notable_cap` should be validated (currently `clampi` silently lets the min win).
