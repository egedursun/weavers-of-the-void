# 01 — Data Model and Persistence

Source of truth (old repo, read-only): `src/db.js` (schema, migrations, triggers, backup), `src/rules.js` (entity and bond taxonomies), plus `ALTER TABLE` statements in `src/panteon.js` and `src/gok.js`. Real data was inspected from a copy of `data/aerona.db` (world "Orvael", epoch 48, 3,622 entities, 19,669 bonds, 9,852 chronicle rows, 6 worlds).

Companion document: `02-world-core.md` (accessors, helpers, repair passes, backup, export, ledger, and so on).

Notation: each Turkish identifier appears once in parentheses, e.g. "entity (varlik)". After that the English name is used. Types are SQLite affinities. "JSON" means a TEXT column that holds serialized JSON. The column order follows the real database.

---

## 0. Storage conventions

| Aspect | Old behaviour | Notes for the rewrite |
|---|---|---|
| Engine | `node:sqlite` `DatabaseSync`, a single connection for the whole process | Use `aiosqlite` or SQLAlchemy async with **one writer**. |
| Pragmas | `journal_mode=WAL; foreign_keys=ON; trusted_schema=OFF` | Keep them. FKs exist on only a few columns (see §3). |
| DB path | `$AERONA_DB` or `data/aerona.db`. Image dir `data/gorseller/` (images), backup dir `data/yedekler/` (backups), image pool `data/yedekler/gorseller/`, log dir `data/log/`, discovery dir `data/kesif/` and state file `data/kesif.json` | Make it configurable. |
| IDs | `INTEGER PRIMARY KEY` (rowid) on most tables; composite PKs on pair tables | — |
| Booleans | `INTEGER 0/1` | — |
| Timestamps | `TEXT DEFAULT (datetime('now'))` in UTC `YYYY-MM-DD HH:MM:SS`; telemetry uses an epoch-ms `INTEGER` | Use ISO-8601 UTC everywhere. |
| JSON | Stored as TEXT. Parsed tolerantly: invalid JSON falls back to a default (`{}`, `[]`, or null) | Use typed JSON columns validated by Pydantic. |
| Undefined → NULL | The query helper maps JS `undefined` params to `NULL` | — |
| Polymorphic node refs | A pair of `*_tip` (type code) + `*_id` columns. Codes are listed below | Replace with explicit FKs or a `node` table (see §13). |

### 0.1 Node type codes (`tip`)

These codes are used in `baglar.kaynak_tip/hedef_tip`, `mesajlar.kimden_tip/kime_tip`, `gorseller.hedef_tip`, `bildirimler.hedef_tip`, `defter.kim_tip`, `sozluk.ekleyen_tip`, and in graph node keys such as `"v12"` and `"o3"`.

| Code | Meaning | Target table |
|---|---|---|
| `v` | entity (varlık) | `varliklar` |
| `o` | son / god card (oğul) | `ogullar` |
| `t` | the creator god, i.e. the player (tanrı). Its id is 0, 1 or NULL; the node key is always `t1` | `dunya` singleton |
| `y` | foreign / elder god (yabancı tanrı) | `yabanci_tanrilar` |
| `d` | world / planet (dünya) — images only | `dunyalar` |
| `k` | Fate (Kader) — only as the author of a dictionary entry | — |
| `m` | world engine (motor) — only as the author of a dictionary entry | — |

---

## 1. Table catalogue (overview)

| Turkish table | English name | Kind | Tracked by ledger | Tracked by change feed |
|---|---|---|---|---|
| `dunya` | world_state (cosmos singleton + creator god) | core | ✔ | ✔ |
| `ogullar` | sons (god cards) | core | ✔ | ✔ |
| `varliklar` | entities (all lore records) | core | ✔ | ✔ |
| `baglar` | bonds (typed edges) | core | ✔ | ✔ |
| `iliskiler` | son_relations (son↔son affinity) | core | ✔ | ✔ |
| `topluluk_iliski` | community_relations (community↔community affinity) | core | ✔ | |
| `kronik` | chronicle (event log) | core | ✔ | ✔ |
| `kronik_varlik` | chronicle_entities (derived join table) | derived | | |
| `kronik_bakis` | historian_views (per-people retelling of an epoch) | lore | ✔ | |
| `caglar` | epochs (epoch name, narrative, summary) | lore | ✔ | |
| `caglar_dunya` | epoch_world_narratives | lore | ✔ | |
| `mesajlar` | messages (prayers, speeches, chat) | core | ✔ | |
| `sozluk` | lexicon (dictionary words of languages) | lore | ✔ | |
| `halk_inanc` | folk_beliefs (how a people tells of a god) | lore | ✔ | |
| `gercekler` | canon_facts (subject–predicate–object triples) | lore | ✔ | |
| `iplikler` | threads (open story hooks) | lore | ✔ | |
| `konseyler` | councils (son council minutes) | lore | | |
| `yildizlar` | stars | cosmos | ✔ | ✔ |
| `dunyalar` | worlds (planets) | cosmos | ✔ | ✔ |
| `rotalar` | routes (inter-world travel routes) | cosmos | ✔ | ✔ |
| `yolculuklar` | journeys (voyages on routes) | cosmos | ✔ | ✔ |
| `yabanci_tanrilar` | foreign_gods (elder/local gods) | cosmos | ✔ | ✔ |
| `ufuk_sezgi` | horizon_intuitions (mortals sensing an unknown world) | cosmos | | |
| `harita_anlik` | map_snapshots (per-epoch snapshot) | map | | |
| `harita_notlari` | map_notes (player pins) | map | | |
| `senaryolar` | scenarios (goal runs) | meta | ✔ | |
| `basarimlar` | achievements | meta | | |
| `puanlar` | scores (per-epoch score) | meta | | |
| `bildirimler` | notifications | UX | | |
| `defter` | ledger (one action = one group) | undo | | |
| `defter_satir` | ledger_rows (row diffs) | undo | | |
| `gorseller` | images | media | ✔ | |
| `llm_olcum` | llm_metrics | telemetry | | |
| `gunluk` | live_feed_log | telemetry | | |
| `cag_istatistik` | epoch_stats | stats | | |
| `ag_bakis` | network_review_marks | maintenance | | |
| TEMP `kanon_degisen`, `konum_surum`, `degisim` | canon_cache_dirty, location_version, change_log | per-connection | | |

The ledger whitelist (`DEFTER_TABLOLARI`) is: varliklar, baglar, ogullar, iliskiler, topluluk_iliski, kronik, gercekler, iplikler, sozluk, halk_inanc, rotalar, dunyalar, yolculuklar, mesajlar, dunya, yildizlar, yabanci_tanrilar, caglar, caglar_dunya, kronik_bakis, gorseller, senaryolar.

Telemetry tables (`TELEMETRI`) are `gunluk` and `llm_olcum`. They are stripped from backups and exports, and are not overwritten on restore.
Derived tables (`TURETILMIS`) contain only `kronik_varlik`. It is never copied and is rebuilt by triggers.

---

## 2. Tables in detail

### 2.1 `dunya` — world_state (singleton, `CHECK (id = 1)`)

This one row holds the cosmos-wide state and the creator god (the player). Individual planets live in `dunyalar`; world id 1 mirrors this row's name, cosmology and naming rule.

| Column | Type / default | Meaning |
|---|---|---|
| `id` | INTEGER PK, CHECK = 1 | singleton |
| `ad` | TEXT NN | name of the cosmos / first world (e.g. "Orvael") |
| `tanri_adi` | TEXT NN | creator god's name (e.g. "Aeron") |
| `tohum` | TEXT NN | player's seed idea ("First create light") |
| `kozmoloji` | TEXT NN | LLM-written cosmology paragraph (canon, appears in every prompt header) |
| `isim_kurali` | TEXT NN | naming rule / phonology of world 1 (e.g. "Only vowels a, e, i, o; U is forbidden …") |
| `ton` | TEXT NN | narrative tone |
| `cag` | INTEGER NN 1 | current epoch number (çağ) |
| `yil` | INTEGER NN 0 | world year at the **start** of the current epoch, always `(cag-1) * epoch_years` |
| `tanri_oz` | INTEGER NN | creator's essence (öz), the player's currency |
| `kader_modu` | TEXT NN 'otomatik' | Fate judging mode: `otomatik` (auto) \| `kapali` (off) |
| `olusturma` | TEXT now | created at |
| `modeller` | TEXT JSON | model per job: `{ "<rarity>"|"kader"|"yaratilis"|"cagirma"|"derinlik"|"vahiy": "haiku"|"sonnet"|"opus" }`. Missing keys fall back to the defaults (all `haiku`) |
| `tanri_unvan` | TEXT | creator's title / epithet |
| `tanri_gorunus` | TEXT | appearance |
| `tanri_mizac` | TEXT | temperament (shown to sons) |
| `tanri_prompt` | TEXT | image prompt for the creator portrait |
| `cagin_yildizi` | INTEGER → varliklar.id | "star of the epoch": a celestial (`gok`) entity rising this epoch in world 1. Creations in its domain are cheaper |
| `olumlu_sayisi` | INTEGER NN 4 | mortal agents per epoch (the player setting) |
| `harita_surum` | INTEGER NN 1 | map generator version |
| `kiyamet` | INTEGER NN 0 | doomsday clock value (threshold is the rule `DENGE.kiyamet_esik`, default 100). *The column comment says "JSON [x,y]" — stale; it is an integer.* |
| `cag_durum` | TEXT JSON | in-progress epoch state for resume: `{cag, asama, basladi?, ajanlar?, motor?}`. NULL when no epoch is in progress. `asama` = last completed phase (0 = within phase 1). `basladi` = 1 once the pre-epoch backup and son distribution are done |
| `kader_borc` | INTEGER | oldest epoch Fate failed to judge (Fate re-judges from there next time) |
| `iklim` | TEXT JSON | legacy world-level climate `{evre, kalan, bas}` (superseded by `dunyalar.iklim`) |
| `olumlu_paralel` | INTEGER NN 1 | how many mortal agents think concurrently |
| `denge_surum` | INTEGER NN 1 | one-time balance migration version (2 = essence-cap migration done) |
| `kozmos_surum` | INTEGER NN 0 | 1 = single-world → multi-world migration done |
| `kozmik_kaynak` | TEXT JSON | the cosmos's travel resource `{ad, aciklama, kural, yan_etki}` (name, description, rule, side effect) |
| `tanri_destan` | TEXT JSON | creator's epic `{baslik, dize, bolumler:[{baslik, metin, cag_bas, cag_son}], cag}` |
| `tanri_derinlik` | TEXT JSON | creator's depth (lore) — see §10.2 |
| `tanri_notu` | TEXT | the player's own canon note (shown in prompts as "THE GOD'S OWN WORD (canon)") |
| `tanri_ruh` | TEXT JSON | creator's mood `{hosnutluk, ofke, ilgi, yalnizlik, girdi:{<mood>:[{kalem, d}]}}` (contentment, wrath, attention, loneliness, each 0–100; `girdi` = contributions from the last tick) |
| `ogul_dagitim` | TEXT NN 'otomatik' | son-to-world distribution: `otomatik` \| `elle` (manual) |
| `konsey_sikligi` | INTEGER NN 4 | spontaneous council every N epochs (0 = never) |
| `bildirim_ayar` | TEXT JSON | `{<category>: bool}` notification opt-ins |
| `tanri_tutku` | TEXT JSON | creator passions `{tutkular:[string], otomatik: bool}` |
| `denge_ayar` | TEXT JSON | **world rule overrides** `{"<AREA>.<key>": int}`. Only values that differ from the factory default are stored (see 02 §3) |
| `yaratilis_ayar` | TEXT JSON | genesis wizard settings `{sablon, buyu, karanlik, teknoloji, dil, halk, kozmos, ton, tohum}` |
| `veri_surum` | INTEGER NN 0 | one-time data fix version: ≥1 cult-follower fix done, ≥2 one-time text repair done |
| `hizalanma_son` | INTEGER | last epoch in which a manual planetary alignment keeps slingshot routes open (added in `gok.js`) |

### 2.2 `ogullar` — sons (god cards / LLM agents)

| Column | Type / default | Meaning |
|---|---|---|
| `id` | INTEGER PK | |
| `ad` | TEXT NN | name (unique across the cosmos, see 02 §7) |
| `unvan` | TEXT NN | title / epithet |
| `nadirlik` | TEXT NN | rarity: `yaygin` common · `seckin` uncommon/elite · `nadir` rare · `destansi` epic · `efsanevi` legendary · `mitik` mythic |
| `alan1`, `alan2` | TEXT NN | two domains from the 40-item `ALANLAR` list (Sea, Fire, Earth, Sky, Storm, Death, Life, Dream, Time, Light, Shadow, War, Craft, Knowledge, Love, Trickery, Hunt, Plant, Bone, Blood, Sound, Stone, Ice, Madness, Trade, Road, Plague, Harvest, Moon, Sun, Star, Lie, Oath, Memory, Hunger, Glass, Salt, Ash, Border, Sleep) |
| `kisilik` | TEXT NN JSON | personality `{gorunus, mizac, takinti, korku, uslup, sir}` = appearance, temperament, obsession, fear, speaking style, secret |
| `statlar` | TEXT NN JSON | 9 stats 1–100: `guc` strength, `dayaniklilik` endurance, `ceviklik` agility, `bilgelik` wisdom, `kurnazlik` cunning, `irade` will, `yaraticilik` creativity, `karizma` charisma, `kudret` might |
| `tutku` | TEXT NN JSON | passions 0–100: `sadakat` loyalty, `hirs` ambition, `ofke` wrath, `merhamet` mercy |
| `can` | INTEGER NN | HP, clamped to `[0, canMax(stats)]` on save |
| `oz` | INTEGER NN | essence, clamped to `[0, ozMax(stats)]` on save |
| `inanc` | INTEGER NN 0 | faith (computed from worshippers, see 02 §8) |
| `un` | INTEGER NN 0 | fame |
| `xp` | INTEGER NN 0 | experience |
| `seviye` | INTEGER NN 1 | level |
| `durum` | TEXT NN 'aktif' | `aktif` active \| `uykuda` asleep \| `surgun` exiled \| `olu` dead (see §9) |
| `uyku_kalan` | INTEGER NN 0 | epochs of sleep left |
| `zincirli` | INTEGER NN 0 | chained (bool) |
| `emir` | TEXT | standing order from the creator |
| `son_eylem_cag` | INTEGER NN 0 | last epoch the son acted |
| `ebeveyn_id` | INTEGER → ogullar.id | parent son (for sons born of sons) |
| `dogum_cag` | INTEGER NN | birth epoch |
| `gorsel_prompt` | TEXT | portrait prompt (English) |
| `olusturma` | TEXT | |
| `gucler` | TEXT JSON | 3 powers `[{ad, aciklama, etki, param}]`. `etki` ∈ `GUC_ETKILERI` keys. Unlocked at levels `GUC_SEVIYELERI` = [1, 3, 5] |
| `yildiz` | INTEGER NN 1 | stars ★1–★5 within the rarity |
| `varolus` | TEXT JSON | existence `{doga, hal, tezahur, gercek_ad}` = nature, state (one of `somut` concrete, `yarı-somut` semi-concrete, `kavramsal` conceptual, `yansıma` reflection, `dağınık` scattered), manifestation, true name |
| `varlik` | INTEGER NN 60 | existence score 0–100 (bands: radiant ≥80, solid ≥30, faded ≥12, being-forgotten <12 = cannot act) |
| `capa_id` | INTEGER → varliklar.id | anchor entity (losing it reduces existence) |
| `plan` | TEXT | son's self-written long-term plan |
| `destan` | TEXT JSON | son's epic `{baslik, destan, …}` |
| `asi` | INTEGER NN 0 | rebel against the father (bool) |
| `tur_cag` | INTEGER NN 0 | epoch in which an interrupted turn began |
| `tur_ap` | INTEGER | action points left in the interrupted turn |
| `olum_cag` | INTEGER | death epoch |
| `ceset_id` | INTEGER → varliklar.id | corpse entity left behind |
| `solus` | INTEGER NN 0 | consecutive epochs with existence near zero ("fading", 3 → death) |
| `aktif_dunya` | INTEGER → dunyalar.id | world the son currently acts in |
| `ek` | TEXT JSON | suffix-behaviour hints for the name `{okunus, tamlama, elle?}` — **LANGUAGE-SPECIFIC: drop** |
| `itibar` | TEXT JSON | son's view of the father `{sevgi, korku, unutma, cevapsiz, son_temas, etiket, cag}` (love, fear, forgetting, unanswered prayers, last contact epoch, label, epoch computed) |
| `itibar_elle` | TEXT JSON | creator's manual push `{sevgi, korku, unutma}` (each ±`ITIBAR.elle_tavan`, decays each epoch) |
| `tur_ctx` | TEXT JSON | serialized turn context for resume (02 §15) |
| `tanri_atama_cag` | INTEGER | epoch the creator manually sent the son to a world (auto-distribution leaves him alone for a while) |
| `emir_mutlak` | INTEGER NN 0 | the standing order is absolute (cannot be refused) |
| `itibar_olay` | TEXT JSON | decaying trace left by divine power `{sevgi, korku}` |

### 2.3 `varliklar` — entities (every lore record)

| Column | Type / default | Meaning |
|---|---|---|
| `id` | INTEGER PK | |
| `ad` | TEXT NN | name (unique across the cosmos for non-rejected records) |
| `tur` | TEXT NN | entity type (25 values, §6) |
| `alt_tur` | TEXT | free subtype, e.g. "harbour city"; the engine uses fixed values for some types (§6.3) |
| `aciklama` | TEXT NN | description (canon prose). Engine-created rows start with `"[Dünya motoru] "` ("[World engine] ") until named |
| `statlar` | TEXT NN '{}' JSON | type-specific stats (§6.1) plus engine-added keys (§6.4) |
| `guc_seviyesi` | INTEGER NN 1 | power level 1–12+, which maps to a rarity class (§6.2) |
| `alan` | TEXT | domain (one of the 40 domains) |
| `yaratan_id` | INTEGER → ogullar.id | creating son (NULL = god, engine or mortal) |
| `cag` | INTEGER NN | birth epoch |
| `durum` | TEXT NN 'kanon' | status: `kanon` canon/alive · `reddedildi` rejected · `yok_edildi` destroyed · `olu` dead · `gerceklesti` fulfilled (prophecy) (§9.1) |
| `konum_id` | INTEGER → varliklar.id | location (containment tree) |
| `gorsel_prompt` | TEXT | image prompt |
| `kader_notu` | TEXT | Fate's note: a public editorial note, not narrative. Prefixes "Kader düzeltti: …" ("Fate corrected: …") and "Kader kabul etti." ("Fate accepted.") |
| `etiketler` | TEXT NN '[]' JSON array of strings | tags: free words plus system tags (§6.5) |
| `olusturma` | TEXT | |
| `derinlik` | TEXT JSON | "depth": LLM-generated lore (§10.1) |
| `kaynak` | TEXT NN 'ogul' | origin: `ogul` son · `tanri` creator · `dunya` world engine · `olumlu` made by a mortal agent · `kozmos` born with a world that a son birthed (§6.6) |
| `bekliyor` | INTEGER NN 0 | pending: an engine-created record waiting for Fate to name it |
| `harita_xy` | TEXT JSON `[x, y]` | pinned map coordinates (NULL = computed by the layout) |
| `yapan_id` | INTEGER → varliklar.id | maker (a mortal or creature entity that produced it) |
| `son_eylem_cag` | INTEGER NN 0 | last epoch this entity acted as a mortal agent |
| `tur_cag`, `tur_ap`, `tur_ctx` | | interrupted mortal-agent turn (same semantics as sons) |
| `toplum` | TEXT JSON | society for peoples and settlements (§10.3) |
| `favori` | INTEGER NN 0 | player favourite |
| `kisisel_not` | TEXT | player's private note (≤4000 chars) |
| `dunya_id` | INTEGER → dunyalar.id | world (set by trigger, §4) |
| `ek` | TEXT JSON | suffix info — **LANGUAGE-SPECIFIC: drop** |
| `arsiv_elle` | INTEGER | manual archive override: NULL auto · 1 force to "history" · 0 keep in atlas |
| `olum_cag` | INTEGER | death / destruction epoch |
| `onem` | INTEGER | importance score (recomputed at epoch end, 02 §19) |
| `unvan` | TEXT | title split off the name ("Name, Epithet" → `ad`="Name", `unvan`="Epithet") |

FKs: `yaratan_id`→ogullar, `konum_id`→varliklar. Other references are unenforced.

### 2.4 `baglar` — bonds (typed, directed edges)

| Column | Type / default | Meaning |
|---|---|---|
| `id` | INTEGER PK | |
| `kaynak_tip`, `kaynak_id` | TEXT NN, INTEGER NN | source node (subject) |
| `hedef_tip`, `hedef_id` | TEXT NN, INTEGER NN | target node (object) |
| `tur` | TEXT NN | bond type (49 values, §7) |
| `aciklama` | TEXT | description / role / reason. Special forms: `"kapatıldı: <reason>"` ("closed: …"), `"ruh kaplama"` (spirit binding), `"yurdu"` (homeland), `"<n> <what>; vade Çağ <n>"` (debt), `"ruhu oraya indi"` (its soul descended there), `"kaderinde anılır"` (mentioned in its fate) … |
| `cag` | INTEGER NN | epoch created |
| `aktif` | INTEGER NN 1 | 1 = active (mechanically effective). 0 = past (still lore) |
| `red_kapatti` | INTEGER | 1 = closed because an endpoint was rejected / removed from canon (hidden; reopened if the rejection is undone) |

Observed endpoint mixes: v→v 18,277; v→o 1,264 (worship); o→v 94; o→o 14; v→t 15; v→y 3; y→v 1; o→y 1.

### 2.5 `iliskiler` — son_relations

`PRIMARY KEY (a, b)`, `CHECK (a < b)`; `a`, `b` → ogullar.id. `deger` INTEGER −100 (hatred) … +100 (devotion), default 0. `not_` TEXT holds the latest narrative note on the relationship (COALESCE-preserved when the new note is NULL). Label thresholds: 02 §9.

### 2.6 `topluluk_iliski` — community_relations

`PRIMARY KEY (a,b)`, `CHECK (a<b)`; `a`, `b` → varliklar.id (communities). `deger` −100 (blood feud) … +100 (brotherhood). `gecmis` JSON: the latest events `[{cag, olay, d}]` (epoch, event label, delta), capped at `ILISKI.iliski_gecmis`. `kan_davasi` INTEGER: epoch a blood feud began (NULL = none). Rows are created lazily on first read with a computed initial value (shared patron god ±, shared language +, enemy/ally/trade/tribute bonds ±) — see the community module spec.

### 2.7 `kronik` — chronicle

| Column | Type | Meaning |
|---|---|---|
| `id` | INTEGER PK | ordering key |
| `cag` | INTEGER NN | epoch |
| `ogul_id` | INTEGER → ogullar | acting son (if any) |
| `tur` | TEXT NN | kind (§8) |
| `metin` | TEXT NN | line text (suffix-corrected and ID-scrubbed on write) |
| `varlik_ids` | TEXT NN '[]' JSON int[] | referenced entity ids |
| `olusturma` | TEXT | wall-clock time |
| `yil` | INTEGER | in-world year (02 §5.2) |

### 2.8 `kronik_varlik` — chronicle_entities (derived)

`(kronik_id, varlik_id)` PK, index on `varlik_id`. Maintained by triggers from `kronik.varlik_ids` (§4). It is rebuilt when the counts mismatch at startup, and always after restore or import.

### 2.9 `kronik_bakis` — historian_views

`id`, `cag`, `halk_id` (people entity), `tarihci` (historian name + title), `metin` (first-person retelling of the epoch from that people's biased view). Index on `cag`.

### 2.10 `caglar` — epochs

`cag` PK; `ad` (epoch name, e.g. "The Age of Dried Mouths"); `anlati` (chronicler's narrative); `ozet` (summary); `yil_bas`, `yil_son` (= `(cag-1)*Y`, `cag*Y`); `kapanis` (close timestamp, datetime('now')); `kronikci` JSON `{ad, kim}` = chronicler name and who they are (chroniclers persist for `KADER.kronikci_sure` epochs).

### 2.11 `caglar_dunya` — epoch_world_narratives

`(cag, dunya_id)` PK, `anlati`, `ozet`: a per-world narrative for the epoch.

### 2.12 `mesajlar` — messages

| Column | Meaning |
|---|---|
| `id`, `cag`, `olusturma` | |
| `kimden_tip`, `kimden_id` | sender (`o` son, `t` creator, `v` mortal entity). Creator id is NULL |
| `kime_tip`, `kime_id` | recipient (`o`, `t`, `v`) |
| `niyet` | intent. For son→son speech: `dostluk` friendly, `ittifak` alliance offer, `ask` love, `tehdit` threat, `alay` mockery, `uyari` warning, `pazarlik` bargain. Others: `dua` prayer, `cevap` (creator's answer), `sohbet` (chat), `ruya` (dream sent to a mortal) |
| `metin` | text |
| `istek` | prayer request: `oz` asked for essence, `kutsama` blessing, `izin` permission, `intikam` vengeance, `af` forgiveness, `hicbiri` none — or a free-text wish (from mortal prayers) |
| `okundu` | read flag |
| `cevaplandi` | answered flag (prayers). Unanswered prayers to `t` feed reputation and the creator's mood |

Observed flows: o→o 75, o→t 49, t→o 24, t→v 5, v→t 16.

### 2.13 `sozluk` — lexicon

`id`, `dil_id` → varliklar(language), `kelime` (word ≤60), `anlam` (meaning ≤300), `tur` (part of speech: `isim` noun, `fiil` verb, `sıfat` adjective, `ek` affix, `unvan` title, `yer adı` place name, `özel ad` proper name, `sayı` number, `ünlem` interjection), `koken` etymology ≤300, `ornek` usage example ≤300, `ekleyen_tip` / `ekleyen_id` (`o`, `t`, `v`, `k` Fate, `m` engine), `cag`, `olusturma`. Per language, uniqueness is case-insensitive on `kelime` (enforced in code).

### 2.14 `halk_inanc` — folk_beliefs

PK `(halk_id, ogul_id)`. `ogul_id = 0` means the creator god. `ad` = the name this people gives the god in its own language. `anlati` = the people's (partial, distorted) account. `yanlis` = where they are actually wrong (visible only to the player). `cag`.

### 2.15 `gercekler` — canon_facts

`id`, `ozne_id` (subject entity), `iliski` (short predicate, e.g. "contains", "forbids", "is made of X"), `nesne_id` (object entity) **or** `nesne` (plain-text object), `cag`, `kaynak_id` (the creation the fact was extracted from), `aktif`. Engine-written deterministic predicates (Turkish strings in old data): `içinde bulunur` (is located in), `yaratanı` (creator), `konuştuğu dil` (language spoken), `taptığı tanrı` (god worshipped), `soyundandır` (descends from).

### 2.16 `iplikler` — threads (open story hooks)

`id`, `cag` (opened), `metin` (hook text), `ilgili` JSON int[] (related entity ids), `durum` (`acik` open \| `kapandi` closed), `kapanis` (closing text), `kapanis_cag`, `ilerleme` (number of creations that advanced it), `buyuk` JSON for a "legendary quest" (efsanevi sefer): `{tur, hedef, son_cag, kim, acilis}` (quest kind e.g. `olu_yildiz` = rekindle a dead star, target id, deadline epoch, opener, opening epoch). An entity advances a thread by carrying the tag `iplik:<id>`.

### 2.17 `konseyler` — councils

`id`, `cag`, `konu` (topic), `tutanak` JSON minutes `{konu, cagiran, konusmalar:[{ogul_id, ad, soz}], onerge, oylar:[{ogul_id, ad, oy:'evet'|'hayir'|…, gerekce}], kabul, karar, notlar:[str], tutanak}`, `kabul` (motion passed, bool), `olusturma`.

### 2.18 `yildizlar` — stars

`id`, `ad`, `tur` (free kind: "sarı cüce" yellow dwarf, "kızıl dev" red giant, "ikiz yıldız" twin star, "ölü yıldız" dead star, "kara güneş" black sun, "kırık yıldız" broken star …), `parlaklik` 0–100 (60), `x`, `y` REAL (galaxy-map coordinates), `aciklama`, `gorsel_prompt`, `olusturma_cag`.

### 2.19 `dunyalar` — worlds (planets)

| Column | Default | Meaning |
|---|---|---|
| `id` | | world 1 is the original world |
| `ad` | | name |
| `tur` | 'olagan' | world type: `olagan` ordinary · `okyanus` ocean · `kum` sand · `buz` ice · `lav` lava · `kristal` crystal · `yasayan` living planet · `olu` realm of the dead · `ruya` dream realm · `ayna` mirror world · `gaz` gas giant |
| `yildiz_id` | | star it orbits (moons inherit their planet's star) |
| `ana_id` | | parent world if this is a moon |
| `yorunge` | 1 | relative orbit distance |
| `yercekimi` | 'olağan' | gravity: `düşük` low \| `olağan` normal \| `yüksek` high |
| `atmosfer` | 'olağan' | `yok` none \| `ince` thin \| `olağan` normal \| `yoğun` dense \| `zehirli` toxic |
| `zaman_katsayi` | 1 | years-per-epoch multiplier |
| `seed` | | terrain generator seed |
| `arazi` | | JSON `{deniz, daglik, nem}` (sea ratio, mountainousness, humidity; 0–1) |
| `kesif` | 'bilinen' | discovery: `bilinen` known · `efsane` legend · `bilinmeyen` unknown · `unutulmus` forgotten |
| `tehlike` | 20 | danger 0–100 |
| `sizinti` | 0 | leakage of outside things 0–100 |
| `kozmoloji`, `lehce`, `aciklama`, `gorsel_prompt` | | cosmology; dialect/naming rule (for world ≠1); description; image prompt |
| `yaratan_id` | | birthing son (NULL = creator) |
| `olusturma_cag` | 1 | |
| `koruyucu_ogul` | | patron son that declared it holy |
| `cagin_yildizi` | | this world's star of the epoch (a `gok` entity id) |
| `ayna_ikiz` | | for mirror worlds: the twin (what dies in one is born in the other) |
| `olumlu_ajan` | | per-world mortal agents per epoch (NULL = automatic share) |
| `iklim` | | JSON `{evre, kalan, bas}`: climate era key (`ilik` temperate, `kurak` drought, `yagmur` rains, `buzul` ice age, `sicak` scorching), epochs left, start epoch |
| `koruyucu_oto` | 0 | patron was auto-assigned (added in `panteon.js`) |

### 2.20 `rotalar` — routes

`id`, `a_dunya`, `b_dunya` (undirected pair), `yontem` (method key: `kapi` ancient gate, `katlama` space folding, `yelken` light sail, `binek` cosmic mount, `ruya` dream voyage, `olu_nehri` river of the dead, `kopru` divine bridge, `sapan` slingshot orbit, `yutulma` being swallowed), `sure` (epochs, 2), `tehlike` (30), `bilinen` (known, 1), `kontrol_id` (community controlling it), `arac_id` (vehicle entity that *is* the route, e.g. a gate or bridge), `kuran_ogul` (son who built a divine bridge), `aciklama`, `olusturma_cag`, `aktif` (1), `gecici_son` (epoch a temporarily opened route reseals), `kapali_son` (epoch a temporarily cut route reopens), `unutma_kapatti` (id of the forgotten world whose forgetting closed this route; see trigger §4).

### 2.21 `yolculuklar` — journeys

`id`, `yolcu_id` (travelling community or mortal entity), `rota_id`, `arac_id`, `hedef_dunya`, `niyet` (`koloni` colony \| `ticaret` trade \| `kesif` exploration \| `fetih` conquest \| `hac` pilgrimage), `nufus` (population carried), `kalan` (epochs to arrival), `durum` (`yolda` underway \| `vardi` arrived \| `kayip` lost), `olaylar` JSON `[{cag, olay, kayip}]`, `baslangic_cag`, `sonuc_id` (settlement founded on arrival, etc.).

### 2.22 `yabanci_tanrilar` — foreign_gods

`id`, `ad`, `unvan`, `alanlar` ("Earth/Memory"), `dunya_id` NN, `guc` (50), `inanc` (0), `tutum` (−100 hostile … +100 friendly towards the pantheon), `durum` (`uyanik` awake \| `uykuda` asleep \| `yenik` defeated \| `olu` dead), `temas` (first contact made), `aciklama`, `gorsel_prompt`, `olusturma_cag`, `yenilgi_cag` (epoch defeated), `statlar` / `kisilik` / `gucler` / `varolus` / `derinlik` JSON (same shapes as sons; `derinlik` §10.2 plus `panteona_bakis` view of the pantheon and `tapinma` worship), `uyanis_baski` INTEGER (awakening pressure accumulator), `olum_cag`, `uyanis_ortalama` REAL (running average used by the awakening rule). The last four columns are added in `panteon.js`.

### 2.23 `ufuk_sezgi` — horizon_intuitions

`id`, `varlik_id` (mortal who sensed it), `dunya_id` (world it happened in), `cag`, `nasil` (how), `yontem` (method), `durum` (`bekliyor` pending → `isleniyor` processing → `dogdu` born \| `bosa` wasted), `sonuc_dunya` (the world born from it). At epoch end Fate turns pending intuitions into new worlds.

### 2.24 `harita_anlik` — map_snapshots

`cag` PK, `veri` JSON `{canli:[ids alive/fulfilled], nufus:{id: population}, siyasi:{regionId:{hakim_id, hakim_ad, tur, pay, cekisen}}, savaslar:[ongoing war ids]}`. Written once per epoch (time-scrubbing on the map).

### 2.25 `harita_notlari` — map_notes

`id`, `x`, `y` INTEGER, `metin` ≤400, `renk` (≤20 chars, default "altin" gold), `olusturma`, `dunya_id` (NULL means world 1).

### 2.26 `senaryolar`, `basarimlar`, `puanlar` — meta game

- `senaryolar`: `id`, `anahtar` (scenario key, e.g. `bes_dunya` "five worlds", `kozmik_guc` "cosmic power"), `baslangic_cag`, `bitis_cag`, `durum` (`suruyor` running \| `tamam` done \| `basarisiz` failed \| `birakildi` abandoned), `veri` JSON, `sonuc` text.
- `basarimlar`: `anahtar` PK (achievement key, e.g. `ilk_dunya`, `kehanet`, `on_dil`), `cag`, `zaman`.
- `puanlar`: `cag` PK, `toplam`, `dokum` JSON breakdown `{nufus, cesitlilik, diller, dunyalar, medeniyet, kiyamet, basarim, senaryo}` (population, diversity, languages, worlds, civilization, doomsday, achievements, scenarios).

### 2.27 `bildirimler` — notifications

`id`, `cag`, `kategori` (17 keys, 02 §25), `onem` 1–4 (2), `baslik` ≤90 chars, `metin` ≤600, `hedef_tip` / `hedef_id`, `kronik_id`, `okundu`, `zaman`. Index `(okundu, id)`.

### 2.28 `defter` / `defter_satir` — ledger

- `defter`: `id` (group), `cag`, `kim_tip` (`o` son, `v` mortal agent, `t` creator), `kim_id`, `kim_ad`, `arac` (tool/action key), `ozet` (input summary ≤220), `zaman`, `geri_alindi` (undone flag), `sonuc` JSON `{yapilan: n, catisma: [string]}` (applied count, conflicts).
- `defter_satir`: `id`, `grup` → defter.id, `tablo`, `satir_id` (rowid), `islem` (`ekle` insert \| `guncelle` update \| `sil` delete), `onceki` / `sonraki` JSON row images (compacted to changed columns plus identifying columns after the group closes). Indexes on `grup` and `(tablo, satir_id)`.

### 2.29 `gorseller` — images

`id`, `hedef_tip` (`o`, `v`, `t`, `d`, `y`), `hedef_id`, `dosya` (file name in the image dir; must match `^[\w-][\w.-]*$`), `mime`, `baslik` (caption), `kapak` (cover flag), `boyut` (bytes), `olusturma`. Index `(hedef_tip, hedef_id)`. The cover is chosen by `ORDER BY kapak DESC, id DESC LIMIT 1`.

### 2.30 Telemetry and stats

- `llm_olcum`: `id`, `cag`, `ad` (job name, e.g. "Oğul turu: <name>" son turn, "Ölümlü turu: …" mortal turn, "Derinleştirme" deepening), `model`, `tur` (`ajan` agentic \| `yapisal` structured), `ms`, `durum` (`basarili` ok \| `hata` error), `deneme` (attempts), `turlar` (agent turns), `girdi` / `cikti` (tokens), `maliyet` (USD), `eylem` (actions), `hata`, `zaman`.
- `gunluk`: `id`, `zaman` epoch-ms, `veri` JSON event (the live feed bus event, `{kind, …}`).
- `cag_istatistik`: `cag` PK, `veri` JSON `{nufus, murit, varlik, kelime, bilgi, dil, savas, ticaret, ittifak, yapit, esya, olu, tanrisiz, kiyamet, ogullar:{id:{inanc, un, varlik, seviye}}, dokum:{kiyamet:[{kalem,d}], sizinti:[{dunya, dunya_id, kalemler:[{kalem,d}]}], nufus:[…], oz:[…]}}`.

### 2.31 `ag_bakis` — network_review_marks

`varlik_id` PK, `cag`: the last epoch Fate reviewed this entity for bond suggestions. It is re-reviewed only after `AG.tekrar_cag` epochs.

### 2.32 TEMP (per-connection) objects

| Object | Purpose |
|---|---|
| `temp.kanon_degisen(id PK)` + triggers `kanon_ekle/guncelle/sil` on `varliklar` | dirty set for the incremental canon cache (02 §4.2) |
| `temp.konum_surum(n)` + triggers on INSERT/DELETE and on UPDATE OF `konum_id, durum, tur` | location-tree version counter |
| `temp.degisim(seq AUTOINCREMENT, tablo, satir_id, islem 'e'|'g'|'s'|'x')` + triggers `dg_<t>_e/g/s` | change feed for incremental UI refresh (02 §17) |
| triggers `df_<t>_e/g/s` | ledger capture when the SQL function `defter_grup()` is non-NULL (02 §27) |
| SQL function `defter_grup()` | returns the current ledger group from async context, or NULL |

---

## 3. Indexes

| Index | Columns |
|---|---|
| ix_varlik_tur | varliklar(tur, durum) |
| ix_varlik_konum | varliklar(konum_id) |
| ix_varlik_yaratan | varliklar(yaratan_id) |
| ix_varlik_dunya | varliklar(dunya_id) |
| ix_varlik_yapan | varliklar(yapan_id) |
| ix_varlik_onem | varliklar(onem) |
| ix_bag_k | baglar(kaynak_tip, kaynak_id) |
| ix_bag_h | baglar(hedef_tip, hedef_id) |
| ix_bag_kh | baglar(kaynak_id, hedef_id) — for bidirectional pair queries |
| ix_bag_hk | baglar(hedef_id, kaynak_id) |
| ix_kronik_cag | kronik(cag) |
| ix_kronik_ogul | kronik(ogul_id) |
| ix_kronik_varlik_v | kronik_varlik(varlik_id) |
| ix_mesaj_kime / ix_mesaj_kimden | mesajlar(kime_tip, kime_id) / (kimden_tip, kimden_id) |
| ix_gorsel_hedef | gorseller(hedef_tip, hedef_id) |
| ix_sozluk_dil | sozluk(dil_id) |
| ix_bakis_cag | kronik_bakis(cag) |
| ix_gercek_ozne / ix_gercek_nesne | gercekler(ozne_id) / (nesne_id) |
| ix_bildirim_okundu | bildirimler(okundu, id) |
| ix_defter_cag | defter(cag) |
| ix_defter_satir_grup / _tablo | defter_satir(grup) / (tablo, satir_id) |
| ix_llm_olcum_cag | llm_olcum(cag) |
| ix_halk_inanc_ogul | halk_inanc(ogul_id) |

`ANALYZE` runs once if `sqlite_stat1` is missing; after that `PRAGMA optimize` runs at startup and at each epoch end (`planIstatistikleri`). Without statistics the planner picked the wrong index for bidirectional bond lookups.

---

## 4. Persistent triggers (dropped and recreated at every start)

1. **`tr_varlik_dunya`** (AFTER INSERT on varliklar): sets `dunya_id = COALESCE(NEW.dunya_id, world of konum_id, aktif_dunya of yaratan son, world of yapan entity, MIN(dunyalar.id), 1)`.
2. **`tr_varlik_konum_dunya`** (AFTER UPDATE OF konum_id, when not NULL): copies the new location's `dunya_id` (if that is not NULL).
3. **`tr_varlik_unvan`** (AFTER INSERT): when the name has the form `"<oneword>, <epithet>"` (comma at position >1, the first part has no space, the epithet has more than 2 chars, and no other entity already has the short name): `unvan = COALESCE(NULLIF(trim(unvan),''), epithet)` and `ad = <oneword>`.
4. **`tr_dunya_unutma`** (AFTER UPDATE OF kesif on dunyalar, becoming `unutulmus`): marks every active route touching the world with `unutma_kapatti = world.id`. The application then deactivates them.
5. **`tr_dunya_hatirlama`** (when leaving `unutulmus`): reactivates (`aktif=1, unutma_kapatti=NULL`) the routes this world's forgetting closed, provided neither endpoint is still forgotten. Routes closed for other reasons stay closed.
6. **`tr_kronik_varlik_e/g/s`**: maintain `kronik_varlik` from `kronik.varlik_ids` (insert; on update of varlik_ids delete then reinsert; on delete remove). Only valid JSON arrays are read, and only values whose JSON type is integer/real/text and that cast to a positive integer.

In the rewrite, implement 1, 2, 3 and 6 in the repository layer (explicit and testable) rather than as triggers. Keep 4 and 5 as an explicit "set world discovery" service method.

---

## 5. Polymorphism and containment

- **Containment tree**: `varliklar.konum_id`. Allowed parent types per entity type are given by `VARLIK_TURLERI[t].konum` (§6.1). Region (`bolge`) roots have `konum_id = NULL`; regions may nest. Location-less types (`dil`, `efsane`, `gelenek`, `gok`, `teknoloji`, `kehanet`, `yasa`) are not placed in the tree. Every placed entity also gets an active `icinde` bond to its location (kept in sync by `konumBaginiTazele`, 02 §6.6).
- **World membership**: `varliklar.dunya_id` (see trigger). `NULL` is treated as world 1 (`COALESCE(dunya_id,1)`) everywhere.
- **Graph**: `baglar` connects any two nodes of types v/o/t/y.

---

## 6. Entity taxonomy (`varliklar.tur`)

### 6.1 Types (`VARLIK_TURLERI`)

Columns: key; English name; creation tool name; min son rarity to create (`NADIRLIK_KAPI.tur_<key>`, tunable); allowed containers (`konum`); location required; stats as `[key: range]`; Turkish examples (translated).

| Key | English | Tool | Min rarity | Containers | Loc. req. | Stats (key: min–max) | Examples |
|---|---|---|---|---|---|---|---|
| `bolge` | Region | bolge_yarat | epic | bolge | no | genislik breadth 0–100, tehlike danger 0–100, bereket fertility 0–100, buyu magic 0–100 | continent, inland sea, desert belt, archipelago, underworld |
| `yer` | Place | yer_yarat | common | bolge, yer | yes | tehlike, bereket, gizem mystery (0–100) | mountain, forest, river, lake, cave, ruin, island, swamp, pass, well |
| `kaynak` | Resource | kaynak_yarat | common | bolge, yer | yes | bolluk abundance, deger value, kudret potency (0–100) | ore vein, magic substance, healing herb, holy spring, rare crystal, bone bed |
| `yerlesim` | Settlement | yerlesim_kur | common | bolge, yer | yes | nufus population 10–2,000,000; refah prosperity, savunma defence, inanc piety (0–100) | village, port city, fortress, monastery, nomad camp, capital |
| `tur` | Species / creature | tur_yarat | common | bolge, yer | no | can HP 1–1000; guc strength, ceviklik agility, zeka intelligence, tehlike danger (0–100) | animal, plant, fungus, monster, spirit kind |
| `halk` | People | halk_yarat | common | bolge, yer | yes | nufus 100–50,000,000; savascilik martiality, buyu magic, zanaat craft, inanc piety (0–100) | race, tribe, caste, mortal lineage |
| `olumlu` | Mortal (named person) | olumlu_yarat | common | bolge, yer, yerlesim | yes | can 1–300; guc, ceviklik, akil intellect, karizma (0–100); yas age 0–50,000; omur lifespan 1–50,000 | hero, king, seer, bandit, artisan, saint |
| `esya` | Item | esya_dov | uncommon | bolge, yer, yerlesim | no | hasar damage, koruma protection, kudret potency, lanet curse (0–100) | weapon, armour, shield, crown, mirror, book, seal, instrument, tool, relic |
| `yapit` | Structure | yapit_insa | uncommon | bolge, yer, yerlesim | yes | ihtisam splendour, saglamlik sturdiness, islev function (0–100) | temple, tower, bridge, wall, monument, tomb, observatory, harbour, mine, library |
| `dil` | Language | dil_yarat | uncommon | — | no | yayginlik spread, karmasiklik complexity, kutsallik sacredness (0–100) | spoken tongue, sacred tongue, script, sign language, merchant cant, language of the dead |
| `efsane` | Legend | efsane_anlat | common | — | no | yayginlik (0–100) | lullaby, taboo, proverb, founding myth, ghost story |
| `gelenek` | Tradition | gelenek_kur | common | — | no | yayginlik, katilik rigidity (0–100) | festival, taboo, funeral rite, initiation, oath ceremony, seasonal offering |
| `tarikat` | Cult / order | tarikat_kur | uncommon | bolge, yer, yerlesim | yes | murit followers 1–10,000,000; bagnazlik zealotry, etki influence (0–100) | temple order, secret sect, priest caste |
| `hizip` | Faction | hizip_kur | uncommon | bolge, yer, yerlesim | yes | guc military, servet wealth, nufuz influence (0–100) | kingdom, guild, knightly order, pirate league, dynasty |
| `gok` | Celestial body | gok_cismi_as | rare | — | no | parlaklik brightness, etki influence (0–100) | star, constellation, moon, comet, wandering light, wound in the sky |
| `eser` | Work of art | eser_yarat | common | bolge, yer, yerlesim | no | un fame, etki influence (0–100) | folk song, epic, statue, fresco, play, book, dance, lament, weaving |
| `kanun` | Law (social) | kanun_koy | uncommon | bolge, yer, yerlesim | no | katilik rigidity, adalet justice (0–100) | penal law, inheritance rule, trade law, worship ban, blood-feud custom |
| `ruh` | Spirit | ruh_cagir | uncommon | bolge, yer, yerlesim | no | guc power, huzursuzluk restlessness (0–100) | ghost, ancestor spirit, haunting, guardian spirit, lost soul |
| `teknoloji` | Knowledge ("Bilgi") | bilgi_ilham_et | rare | — | no | seviye level 1–10, yayginlik spread 0–100 | agriculture, metallurgy, seafaring, writing, architecture, medicine, magic school, art of war, astronomy, trade practice |
| `kehanet` | Prophecy | kehanet_soyle | epic | — | no | kesinlik certainty 0–100 | prophecy, doom sign, cursed word |
| `olay` | Event | olay_baslat | epic | bolge, yer, yerlesim | no | siddet severity 0–100 | war, plague, flood, famine, migration, uprising, catastrophe |
| `arac` | Vehicle / conveyance | arac_yarat | rare | bolge, yer, yerlesim | no | hiz speed, menzil range (0–100), murettebat crew 0–100,000, zirh armour, tuhaflik strangeness (0–100) | ship (light-sailer, bone-hulled, generation ship), ancient gate, cosmic mount, divine bridge |
| `dis` | Outer Being | — (engine/god only) | mythic | bolge, yer | no | buyukluk size, ilgi interest, etki influence (0–100) | something from outside the cosmos whose name is not spoken |
| `ordu` | Army | — (engine only) | epic | bolge, yer, yerlesim | no | buyukluk soldiers 10–10,000,000; moral, techizat equipment, deneyim experience (0–100) | army, legion, raider band, holy guard, fleet |
| `yasa` | Natural law | yasa_koy | legendary | — | no | (none) | return of the dead, price of magic, order of seasons |

Each type also has a creation base cost `YARATIM_TABANI.<key>` (rules module).

Observed counts: mortal 1099, tradition 298, legend 275, event 272, army 200, knowledge 200, place 160, item 142, settlement 139, species 102, resource 101, structure 98, art 92, people 76, region 75, language 67, spirit 65, faction 57, law 53, prophecy 21, celestial 14, cult 11, natural law 4, vehicle 1.

### 6.2 Entity power → rarity class (`varlikSinifi`)

`guc_seviyesi` ≥ `KURAL.sinif_mitik` (11) → mythic; ≥ `sinif_efsanevi` (9) legendary; ≥ `sinif_destansi` (7) epic; ≥ `sinif_nadir` (5) rare; ≥ `sinif_seckin` (3) uncommon; else common.

### 6.3 Engine-fixed subtypes (`MOTOR_ALT_TURLERI`)

- `olay` (event): `savaş` war, `muharebe` battle, `kuşatma` siege, `büyü fırtınası` magic storm, `deprem` earthquake, `sel` flood, `veba` plague, `kuraklık` drought, `fırtına` storm.
- `yapit`: `tapınak` temple, `sur` wall, `kütüphane` library, `kozmik arşiv` cosmic archive.
- `hizip`: `isyancılar` rebels, `tüccar loncası` merchant guild, `rahipler meclisi` priests' council, `savaşçı birliği` warrior band, `dünyalar arası federasyon` interworld federation.
- `ordu`: `halk ordusu` people's army, `kutsal muhafız` holy guard, `paralı ordu` mercenary army.
- `dil`: `lehçe` dialect, `ilkel dil` primitive language.
- Also: `esya/para birimi` currency, `kehanet/tutulma kehaneti` eclipse prophecy, `kaynak/kozmik seyahat kaynağı` cosmic travel resource.

The engine matches on these exact subtype strings, e.g. ongoing wars are `tur='olay' AND alt_tur='savaş'`. The rewrite should use an enum (`event_kind`) and keep `subtype` free text.

### 6.4 Engine-added stat keys (beyond §6.1)

Observed: peoples and settlements get `sagduyu` (sanity 0–100), `basamak_cag`, `basamak_onceki` (civilization tier change epoch and previous tier). Mortals get `sagduyu` and `olum_yili` (death year). Wars and events get `skor`, `muharebe` (battle count), `baslangic`, `son_carpisma` (last clash epoch), `bitis` (end epoch). Cults get `adanmislik` (devotion), `sagduyu`. Additional keys are documented by the engine module specs.

### 6.5 System tag conventions (`etiketler`)

Tags are a single string array mixing free descriptive words (e.g. "salt", "ash", "lullaby") with machine-readable flags. **The rewrite should split these into a `tags` table (free words) and typed columns or tables (flags).** Prefixed flags (value after `:`):

| Tag | Meaning |
|---|---|
| `iplik:<id>` | advances thread `<id>` |
| `taraf:<id>` | war/event participant (side) |
| `sonuc:<k>` | war outcome (e.g. `fetih` conquest) |
| `savas:<…>` | war-related marker |
| `basamak:<n>` | civilization tier 0–5 (0 tribe, 1 city-state, 2 kingdom, 3 world empire, 4 interstellar power, 5 cosmic power) |
| `dal:<key>` | knowledge branch (`BILGI_DALLARI` key: tarim agriculture, metalurji, denizcilik seafaring, yazi writing, mimarlik architecture, tip medicine, buyu magic, savas art of war, gokbilim astronomy, ticaret trade, gokyuzu_seyri sky-sailing, gemi_yapimi shipbuilding, kapi_bilimi gate science, yol_biliciligi path-knowing, bosluk_yasami void living, olumsuzluk immortality, biyobuyu biomagic, yasak forbidden) |
| `ozellik:<key>` | creature trait (`OZELLIKLER`: ucan flying, zehirli venomous, ruh_yiyen soul-eating, isik_sacan light-shedding, bolunerek fission, suru_zekasi swarm mind, tas_derili stone-skinned, zaman_geri time-rewinding, sekil_degistiren shapeshifter, akil_okuyan mind-reader) |
| `mekanik:<key>` | resource mechanic (`bozunur` decaying, `bagimlilik` addictive, `bilincli` sentient, `tukenme_bedeli` depletion curse, `sabit` fixed supply, `kutsal` sacred) |
| `yasa:<key>` | natural-law mechanic (`YASA_MEKANIKLERI`) |
| `imza:<…>` | phonetic signature of a language (`imza:u=hlsnrt;k=lt;s=al;l=1`) — LANGUAGE-generation data |
| `yazi:<tip>` | writing system (e.g. `alfabe` alphabet) |
| `senkretik:<sonId>` | syncretic worship merging with son |
| `bağımlı:<id>` | addicted to resource `<id>` |
| `hizip:<…>`, `sinif:<…>`, `unvan:<…>`, `zafer:<…>`, `kutsal:<…>`, `dirilis:<…>`, `katlama:<n>`, `pazarlik:<sonId>`, `arındı:<id>:<cag>` | faction link, class, title, victory, holy, resurrection, fold counter, bargain, purified |
| `dilden-ad…` | name derived from a language (dropped when merging) |
| plain flags | `suruyor` ongoing, `bitti` ended, `afet` disaster, `deprem`/`sel`/`veba`/`kuraklik`/`firtina` disaster kind, `kayıp` lost (knowledge), `ölü dil` dead language, `önceki yaratılış` previous creation, `harabe` ruin, `kalıntı` remnant, `lanetli` cursed, `tanrısız` godless, `imparatorluk` empire, `bağımsız` independent, `altın çağ` golden age, `ölümsüz` immortal, `kimera`, `mutasyon`, `yerli` native, `gezgin pazar` wandering market, `vahiy` revelation (created by god), `ruhu indi` soul descended … |

### 6.6 Origin (`kaynak`)

| Value | Meaning | Count |
|---|---|---|
| `ogul` | created by a son through a tool (judged by Fate) | 1018 |
| `olumlu` | created by a mortal agent (`yapan_id` set; judged by Fate) | 659 |
| `dunya` | created by the world engine (often `bekliyor=1` until Fate names it) | 1882 |
| `tanri` | created by the creator (genesis, revelation, manual) | 41 |
| `kozmos` | content of a world that a son birthed (not sent to Fate as a "creation") | 22 |

Migration rule: rows with `yaratan_id IS NULL AND kaynak='ogul'` are rewritten to `tanri`.

---

## 7. Bond taxonomy (`baglar.tur`)

### 7.1 All bond types

`BAG_TURLERI` (49 values). Category: **M** = mechanical state (read by the engine), **E** = event (`OLAY_BAGLARI`: a new row every time), **N** = narrative (`ANLATI_BAGLARI`: the only types the `bag_kur` tool and network repair may create). "Count" is from the real DB.

| Key | English label (`BAG_ETIKET`) | Cat. | Direction (subject → object) | Count |
|---|---|---|---|---|
| `icinde` | is inside / located in | M | thing → location | 2441 |
| `yasar` | lives in | M | dweller → region/place/settlement | 238 |
| `tapar` | worships | M | worshipper (v) → god (o/y/t). o→v is auto-flipped | 1229 |
| `dusman` | enemy of | M | symmetric (stored once) | 946 |
| `muttefik` | ally of | M | symmetric; o↔o = covenant (ahit) | 117 |
| `soyundan` | descends from | N | descendant → ancestor | 1282 |
| `korur` | protects | M | protector → protected | 652 |
| `yonetir` | rules | M | ruler → ruled | 702 |
| `sahip` | owns ("sahibi") | M | owner → item/resource/structure/vehicle | 853 |
| `dovdu` | beat (in a duel) | E | | 1 |
| `oldurdu` | killed | E | killer → victim | 39 |
| `lanetledi` | cursed | E | | 0 |
| `kutsadi` | blessed | E | | 116 |
| `kaynagi` | is the source of | N | source → derived | 488 |
| `anlatir` | tells of | N | teller/legend → subject | 1670 |
| `yok_etti` | destroyed | E | | 1 |
| `sever` | loves | N | | 168 |
| `korkar` | fears | N | | 18 |
| `avlar` | hunts | M | | 51 |
| `ticaret` | trades with | M | symmetric | 297 |
| `kehanet_eder` | prophesies about | E/N | prophecy → subject | 48 |
| `neden_oldu` | caused | E/N | cause → effect | 1152 |
| `kutlar` | celebrates | N/M | community → tradition | 343 |
| `yasaklar` | forbids | N | | 28 |
| `konusur` | speaks | M | speaker → language | 1140 |
| `uretti` | produced | M | maker → product | 134 |
| `insa_etti` | built | M | | 89 |
| `gocetti` | migrated (to) | E | | 89 |
| `kesfetti` | discovered | E | | 110 |
| `ruhu_indi` | soul descended to | M | dead → afterworld place | 961 |
| `taraf` | is a side/party of | N-ish | event → participant | 540 |
| `uyesi` | member of | M | | 7 |
| `bilirdi` / `konusurdu` | knew / spoke (past) | legacy | deleted by repair | 0 |
| `bilir` | knows | M | knower → knowledge | 788 |
| `harac_oder` | pays tribute | M | payer → overlord | 26 |
| `ilgili` | related | N | catch-all; vague | 1497 |
| `esir` | holds captive ("esir tutar") | M | captor → captive. aciklama = war name | 10 |
| `casus` | built a spy network | M | | 14 |
| `pesinde` | pursues | N/M | | 117 |
| `yoldas` | companion of | N | only between living beings / communities | 170 |
| `hasim` | rival / nemesis | M | aciklama = event name | 9 |
| `ustasi` | apprentice of ("çırağı") | M | apprentice → master | 38 |
| `komutan` | commands | M | commander → army | 114 |
| `parcasi` | is part of | N | part → whole | 635 |
| `yolcusu` | passenger of | M | | 3 |
| `kaptan` | captain of | M | | 1 |
| `evcil` | domesticated | M | community → species | 5 |
| `ateskes` | truce with | M | aciklama `"<reason>; Çağ <n>'e dek"` (until epoch n) | 283 |
| `borclu` | owes (debtor → creditor) | M | aciklama `"<amount> <what>; vade Çağ <n>"` plus `" · vadesi geçti"` when overdue | 9 |

Narrative set (`ANLATI_BAGLARI`): anlatir, sever, korkar, ilgili, kehanet_eder, yasaklar, pesinde, yoldas, parcasi, kaynagi, neden_oldu, kutlar, soyundan. The network repair can suggest these (except `ilgili`) plus `taraf`.

### 7.2 Endpoint constraints

Agent types (`AJAN_TURLERI`) = halk, yerlesim, hizip, tarikat, olumlu, tur, ordu. Companion types (`YOLDAS_TURLERI`) = olumlu, tur, ordu, ruh, hizip, tarikat, halk.

**Validity (`bagUcuGecerli`, v→v only)**: if the subject or object type is outside the allowed list, the bond is **downgraded to `ilgili`** with `aciklama = "<original type>: <original desc>"`.

| Bond | Allowed subject types | Allowed object types |
|---|---|---|
| sahip, yonetir (subject), ticaret, konusur, bilir, kutlar, yasar | agent types | — |
| tapar | agent types + ruh | — |
| yoldas | companion types | companion types |
| ticaret | — | agent types |
| yasar | — | bolge, yer, yerlesim, halk, hizip, tarikat |
| yonetir | — | bolge, yer, yerlesim, halk, hizip, tarikat, kanun, ordu |
| bilir | — | teknoloji |

**Direction normalization (`BAG_YONU`, v→v)**: if the stored subject's type is in the rule's object list **and** the object's type is in the subject list (and not ambiguously both), the endpoints are swapped.

| Bond | Object types | Subject types |
|---|---|---|
| konusur | dil | agents |
| sahip | kaynak, esya, yapit, arac | agents |
| kutlar | gelenek | agents |
| bilir | teknoloji | agents |
| yonetir | bolge, yer | olumlu, halk, hizip, tarikat, yerlesim |
| evcil | tur | halk, yerlesim, hizip, olumlu, tarikat |
| yasar | bolge, yer, yerlesim | olumlu, halk, hizip, tarikat, tur, ordu |
| parcasi | bolge, yer, yerlesim, halk, hizip, tarikat | dil, ruh, gelenek, kanun, teknoloji, olumlu, kaynak, yapit, esya, tur |

`tapar` with `kt='o' AND ht='v'` is always flipped to v→o.

### 7.3 Uniqueness and side effects (enforced in `addBag`, see 02 §6.1)

- State bonds (not in the event set) are unique per (source, target, type). For role bonds (`taraf`, `ilgili`) the key also includes the description. A duplicate insert only updates the description (non-role) and returns the existing id.
- An `dusman` (enemy) bond between two entities deactivates their active `muttefik` and `ticaret` bonds in both directions.
- A `yonetir` (rules) bond from a mortal deactivates every other mortal's active `yonetir` on the same target (one throne).

### 7.4 Visibility and lifecycle

- `aktif=1`: in force.
- `aktif=0`: history (still lore; shown in the graph and counted for connectivity).
- Hidden: `red_kapatti=1` (closed because an endpoint was rejected), or `aciklama LIKE 'kapatıldı:%'` (Fate or repair judged it meaningless or duplicate). The visible predicate is `GORUNUR_BAG = aktif=1 OR (COALESCE(red_kapatti,0)=0 AND COALESCE(aciklama,'') NOT LIKE 'kapatıldı:%')`.
- Death closes the dead entity's outgoing state bonds (`KAYNAK_DURUM` list) and incoming state bonds (`HEDEF_DURUM`). `sahip` and `yonetir` pass to an heir (02 §20.1 step "dead bonds").

---

## 8. Chronicle kinds (`kronik.tur`)

Union of values found in the code and in the data. "Notif." is the notification category (02 §25). `—` = none.

| Kind | Meaning | Notif. |
|---|---|---|
| `yaratim` | a son created something | — |
| `soz` | son speaks to son | — |
| `meydan` | duel / challenge between sons | — |
| `dua` | prayer to the creator | dua |
| `emir` | creator's order | — |
| `kader` | Fate's judgement line (`Kehanet…` = prophecy fulfilled) | kehanet if text starts with "Kehanet" |
| `olum` | death | olum |
| `dogum` | birth (son summoned, or legendary birth) | dogum (son birth with no entity ids, or text matches legendary/mythic/divine) |
| `sistem` | system ("Çağ N başladı (dünya yılı Y)" = "Epoch N began (world year Y)") | — |
| `mesaj` | message | — |
| `tanri` | creator's hand ("<God>'s hand: …") | — |
| `dunya` | world-engine summary line | via live-feed category: war→savas, disaster/sky→afet, leak→korku, voyage/gate→kozmos, civilization→toplum |
| `motor_ham` | raw engine note (hidden from the chronicle; event log only) | — |
| `bilgi` | knowledge spread | — |
| `kaynak` | resource harvest | — |
| `kultur` | culture (tradition, legend) | — |
| `ticaret` | trade | — |
| `kesif` | exploration | — |
| `diplomasi` | diplomacy | toplum |
| `uretim` | production (crafting) | — |
| `dil` | language | — |
| `mucize` | miracle | — |
| `medeniyet` | civilization tier change | toplum |
| `tanri_itibar` | creator's reputation among sons | itibar |
| `insa` | building | — |
| `varolus` | son fading / existence | olum |
| `ruya` | dream | — |
| `yildiz` | star events | kozmos |
| `tanri_isareti` | divine sign | — |
| `iklim` | climate | afet |
| `kozmik` | cosmic | kozmos |
| `borc` | debt | toplum |
| `yabanci_tanri` | foreign god (awakening, first contact "İlk temas: …") | kozmos |
| `dunya_yasi` | world age | — |
| `konsey` | council | — |
| `onceki_yaratilis` | previous creation | kozmos |
| `gok` | sky event | afet |
| `armagan` | gift | — |
| `tapinma` | worship | — |
| `dunya_dogusu` | world birth | kozmos |
| `kehanet` | prophecy | — |
| `ahit` | covenant | — |
| `ordu` | army | — |
| `yukselis` | ascension | yukselis |
| `goc` | migration | — |
| `efsanevi_sefer` | legendary quest | kozmos |
| `savas` | war | savas |
| `tanri_savasi` | war of gods | savas |
| `kozmik_hukuk` | cosmic law | kozmos |
| `korku` | cosmic horror | korku |
| `dis` | outer being | korku |
| `olumsuzluk` | immortality | korku |
| `isyan` | son's rebellion | isyan |
| `kiyamet` | doomsday | kiyamet |
| `dirilis` | resurrection | yukselis |
| `soy` | lineage | toplum |
| `afet` | disaster | afet |
| `macera`, `entrika`, `kurtaris`, `kimera`, `kacis`, `evcillestirme`, `cag_degisimi`, `sefer`, `ruh`, `lanet`, `inkar`, `fidye`, `yasak` | adventure, intrigue, rescue, chimera, escape, domestication, epoch change, expedition, spirit, curse, denial, ransom, prohibition | — |

The rewrite should make this an enum with an explicit `visible_in_chronicle` flag (to replace the `motor_ham` hack) and a notification mapping table.

---

## 9. Status lifecycles

### 9.1 Entity `durum`

```
            (created by tool / engine / god)
                       │
                       ▼
                    kanon ◄─────────── undo of rejection (god: kanonDegistir)
        ┌─────────┬────┴─────┬───────────────┐
        ▼         ▼          ▼               ▼
  reddedildi   olu       yok_edildi     gerceklesti
 (Fate/undo/  (death;    (destroyed;    (prophecy fulfilled)
  god reject)  olum_cag)  olum_cag;
                          merge target)
```

- `kanon`: alive / in force; the only state the engine mutates.
- `reddedildi`: rejected by Fate (with `kader_notu`), by ledger undo of the creating action, or by the creator. Excluded from name uniqueness and search. Its bonds close with `red_kapatti=1`.
- `olu`: dead (mortals, peoples, settlements, species …). `olum_cag` is set. A closing sentence is appended to `aciklama` ("Died in Epoch N.").
- `yok_edildi`: destroyed (including "merged into X"). `olum_cag`.
- `gerceklesti`: fulfilled prophecy. Treated as "living canon" for lore (`CANLI_DURUM = kanon, olu, gerceklesti`).
- `bekliyor=1` (orthogonal): engine-created, awaiting a name from Fate. Excluded from network nodes.
- Archive ("history" layer) is a **computed** flag (02 §19), not a status.

### 9.2 Son `durum`

`aktif` active → `uykuda` sleeping (HP reached 0 → sleep `uyku_kalan` epochs, 1 with the `dirilis` power) → `aktif`. `surgun` exiled. `olu` dead (via existence fading `solus`≥3, being killed or devoured by the creator, …; `olum_cag`, `ceset_id`). Resurrection costs `DENGE.dirilis`. `asi=1` = rebel flag (orthogonal). Existence band (`varlik`) gates acting: below `KURAL.varlik_solgun` (12) the son cannot act.

### 9.3 Foreign god `durum`

`uykuda` asleep → `uyanik` awake (awakening pressure; `temas` first contact) → `yenik` defeated (`yenilgi_cag`; may re-awaken) → `olu` dead (`olum_cag`). On awakening, the text is rewritten from "asleep" to "awake" (02 §20.6).

### 9.4 Other lifecycles

| Table | States |
|---|---|
| `iplikler.durum` | `acik` open → `kapandi` closed (`kapanis`, `kapanis_cag`) |
| `senaryolar.durum` | `suruyor` running → `tamam` done \| `basarisiz` failed \| `birakildi` abandoned |
| `yolculuklar.durum` | `yolda` underway → `vardi` arrived \| `kayip` lost |
| `ufuk_sezgi.durum` | `bekliyor` → `isleniyor` → `dogdu` \| `bosa` (startup recovery moves stuck `isleniyor` back to `bekliyor`) |
| `dunyalar.kesif` | `bilinen` ↔ `efsane` ↔ `bilinmeyen`; any → `unutulmus` forgotten (closes routes) → back (reopens) |
| `rotalar` | `aktif` 1/0 with timers `gecici_son` (temporary opening ends), `kapali_son` (temporary cut ends), `unutma_kapatti` |
| `mesajlar` | `okundu` 0→1; `cevaplandi` 0→1 (prayer answered; answering twice is an error) |
| `bildirimler.okundu` | 0 ↔ 1 (can be marked unread) |
| `defter.geri_alindi` | 0 → 1 (once only) |
| `dunya.cag_durum` | NULL → `{cag, asama:0, basladi:1}` → asama 1..5 → NULL at epoch end. Resumable when `cd.cag == world.cag AND (asama > 0 OR basladi)` |
| `dunya.kader_borc` | NULL ↔ oldest unjudged epoch |
| Bonds | active → past (`aktif=0`) → hidden (`red_kapatti` or "kapatıldı:") |

---

## 10. JSON blob shapes

### 10.1 `varliklar.derinlik` (entity depth)

```jsonc
{
  "tarih": "string",            // history paragraph(s)
  "soylentiler": ["string"],    // rumours
  "sozler": [{"tur": "ninni|atasözü|ilahi|dua|…", "metin": "string"}], // sayings: lullaby, proverb, hymn, prayer …
  "ayrintilar": ["string"],     // sensory details
  "gizli_gercek": "string",     // hidden truth (player-only)
  "ozel": { … },                // type-specific, e.g.
                                //  mortal: {mizac, hedef, korku, sir, konusma, iliskiler}
                                //          (temperament, goal, fear, secret, speech, relations)
                                //  language: {ses, dilbilgisi, yazi, deyimler}
                                //          (phonology, grammar, script, idioms)
  "cag": 38                     // epoch written
}
```

### 10.2 Creator / foreign god depth (`dunya.tanri_derinlik`, `yabanci_tanrilar.derinlik`)

```jsonc
{
  "tarih": "string",
  "adlari": [{"ad": "string", "kim": "who uses it", "anlam": "meaning"}],
  "sirlar": ["secret"], "korkular": ["fear"],
  "yasaklar": ["taboo"],           // creator: injected into every prompt as uncrossable taboos
  "armaganlar": ["gift"],
  "istek": "what the god wants",   // shown to sons ("sensed")
  "sozler": [{"tur": "ilahi|dua|…", "metin": "…"}],
  "soylentiler": ["rumour"], "gizli_gercek": "string",
  "panteona_bakis": "…", "tapinma": "…",   // foreign gods only
  "cag": 15
}
```

### 10.3 `varliklar.toplum` (society, peoples and settlements)

```jsonc
{
  "k": {"ciftci": 44.8, "zanaatkar": 17.1, "tuccar": 15.9, "rahip": 5.7, "savasci": 7.9, "katip": 8.7}, // class shares %
  "m": {"ciftci": 55, …},          // satisfaction per class 0–100
  "e": {"erzak": 200, "maden": 24, "mal": 62,          // food, ore, goods stock
        "fiyat": {"erzak": 38, "maden": 42, "mal": 59}} // prices, 100 = ×1.0
}
```

Classes: `ciftci` farmers, `zanaatkar` artisans, `tuccar` merchants, `rahip` priests, `savasci` warriors, `katip` scribes.

### 10.4 Other blobs

| Column | Shape |
|---|---|
| `ogullar.kisilik` | `{gorunus, mizac, takinti, korku, uslup, sir}` |
| `ogullar.gucler` | `[{ad, aciklama, etki, param}]` (`param` = entity type for `ucuz`, stat for `meydan`) |
| `ogullar.varolus` | `{doga, hal, tezahur, gercek_ad}` |
| `ogullar.itibar` | `{sevgi, korku, unutma, cevapsiz, son_temas, etiket, cag}` |
| `ogullar.tur_ctx` | `{<counter>: number|bool|string|null, <list>: [..], <set>: {"$set":[..]}}` e.g. `{mesajSayisi, bagSayisi, duaEdildi, yaratimlar:[ids], sagilan:{$set:[]}, lvl, canliYaratim, toprakYaratim}` |
| `dunya.cag_durum` | `{cag, asama, basladi?, ajanlar?, motor?}` |
| `dunya.tanri_ruh` | `{hosnutluk, ofke, ilgi, yalnizlik, girdi:{<k>:[{kalem, d}]}}` |
| `dunya.denge_ayar` | `{"AREA.key": int}` |
| `dunya.yaratilis_ayar` | `{sablon, buyu, karanlik, teknoloji, dil, halk, kozmos, ton, tohum}` |
| `dunya.kozmik_kaynak` | `{ad, aciklama, kural, yan_etki}` |
| `dunya.tanri_destan` | `{baslik, dize, bolumler:[{baslik, metin, cag_bas, cag_son}], cag}` |
| `caglar.kronikci` | `{ad, kim}` |
| `konseyler.tutanak` | see §2.17 |
| `harita_anlik.veri` | see §2.24 |
| `cag_istatistik.veri` | see §2.30 |
| `puanlar.dokum` | see §2.26 |
| `iplikler.buyuk` | `{tur, hedef, son_cag, kim, acilis}` |
| `yolculuklar.olaylar` | `[{cag, olay, kayip}]` |
| `topluluk_iliski.gecmis` | `[{cag, olay, d}]` |
| `dunyalar.arazi` | `{deniz, daglik, nem}` |
| `dunyalar.iklim` | `{evre, kalan, bas}` |
| `defter.sonuc` | `{yapilan, catisma:[string]}` |
| `defter_satir.onceki/sonraki` | full row as a JSON object (compacted after close) |
| `gunluk.veri` | bus event `{kind, …, zaman}` |
| `varliklar.harita_xy` | `[x, y]` |

---

## 11. Migrations (intent)

Schema evolution is additive and idempotent at every startup: `CREATE TABLE IF NOT EXISTS`, plus `addCol(table, col, def)` which runs `ALTER TABLE ADD COLUMN` when the column is missing. Columns added this way (grouped by intent):

- **Creator profile**: dunya.modeller, tanri_unvan, tanri_gorunus, tanri_mizac, tanri_prompt, tanri_destan, tanri_derinlik, tanri_notu, tanri_ruh, tanri_tutku.
- **Son progression and existence**: ogullar.gucler, yildiz, varolus, varlik, capa_id, plan, destan, asi, olum_cag, ceset_id, solus, itibar, itibar_elle, itibar_olay, emir_mutlak, tanri_atama_cag.
- **Resumable turns / epochs**: ogullar.tur_cag, tur_ap, tur_ctx; varliklar.tur_cag, tur_ap, tur_ctx, son_eylem_cag; dunya.cag_durum, kader_borc.
- **Entities**: derinlik, harita_xy, yapan_id, kaynak (default 'ogul'), toplum, favori, kisisel_not, dunya_id, ek, arsiv_elle, bekliyor, olum_cag, onem, unvan.
- **Cosmos**: dunya.cagin_yildizi, kozmos_surum, kozmik_kaynak, ogul_dagitim, konsey_sikligi, hizalanma_son; dunyalar.koruyucu_ogul, koruyucu_oto, olumlu_ajan, iklim, cagin_yildizi, ayna_ikiz; rotalar.gecici_son, kapali_son, unutma_kapatti; yabanci_tanrilar.yenilgi_cag, statlar, kisilik, gucler, varolus, derinlik, uyanis_baski, olum_cag, uyanis_ortalama; ogullar.aktif_dunya; harita_notlari.dunya_id.
- **UX / settings**: dunya.bildirim_ayar, yaratilis_ayar, denge_ayar, olumlu_sayisi, olumlu_paralel, harita_surum, kiyamet, iklim.
- **Versions**: dunya.veri_surum, denge_surum.
- **Bonds**: baglar.red_kapatti.
- **Chronicle**: kronik.yil; caglar.kronikci; iplikler.ilerleme, buyuk.

Data migrations (`veriGecisleri`), run at startup and after every restore/import, all idempotent:

1. **Chronicle years** (`kronikYillari`): rows with NULL `yil` get `(cag-1)*Y + floor((Y-1)*(rank-1)/max(1, count-1))`, spreading them evenly within their epoch by id order. `Y` = the world's `ZAMAN.cag_yil` override from `denge_ayar` (read directly so it works before rules load), else the default 50.
2. **Cosmos migration** (`kozmosGecisi`, gated by `kozmos_surum<1`): if `dunyalar` is empty, create star "<world> Güneşi" (Sun; yellow dwarf, brightness 70, at 0,0, description "The first light <world> circles.") and world id 1 (type `olagan`, orbit 1, seed = world name, terrain = the ordinary type's default terrain, cosmology, dialect = naming rule, description "<world>, <god>'s first world."). Then `varliklar.dunya_id=1` where NULL, `ogullar.aktif_dunya=1` where NULL, and `kozmos_surum=1`. Runs in its own transaction.
3. Sons with NULL `aktif_dunya` → `MIN(dunyalar.id)`.
4. `kaynak='tanri'` where `yaratan_id IS NULL AND kaynak='ogul'`.
5. Rebuild `kronik_varlik` if the count of distinct (kronik.id, entity id) pairs differs from the table count.
6. Delete `defter_satir` rows whose `tablo` is not in the ledger whitelist (imported foreign worlds).
7. Repair `caglar.yil_bas/yil_son` that are NULL or inverted to `(cag-1)*Y`, `cag*Y`.
8. Moons inherit their root planet's star (`aylariHizala`: BFS from each root over `ana_id`, cycle-safe).
9. One-time (`veri_surum<1`): canon cults founded before epoch 5 with followers ≤1 get `murit = 60 * power²`. Then `veri_surum=1`.

Other version-gated migrations elsewhere: `denge_surum<2` → every non-dead son's essence is raised to ≥ half of its max, with a system chronicle line "The balance of the sky changed: the gods' essence widened; now they can give life to more creatures." `veri_surum<2` → the one-time text repair (`metinOnarimi`), then `veri_surum=2`.

**Rewrite recommendation**: use Alembic versioned migrations, and a separate "data fix-ups" registry with ids recorded in a `applied_fixups` table, instead of version integers on the world row.

---

## 12. Reset (`resetAll`)

Deletes every row from every table in FK-safe order (null-out `varliklar.konum_id` and `ogullar.ebeveyn_id` first). Before that the server takes a `sifirlama-oncesi` (pre-reset) safety backup, and afterwards copies every image to the pool and deletes it from the live dir. Requires the confirmation text "SIFIRLA" (RESET).

---

## 13. Proposed normalized English schema (PostgreSQL-flavoured, works on SQLite)

Design goals: explicit FKs, no polymorphic `tip/id` pairs, flags out of the tag array, stats kept as JSON but typed by Pydantic per entity type, all language-specific columns dropped, an append-only event log separate from the narrative chronicle, and versioned migrations.

```sql
-- ===== Cosmos & player =====
CREATE TABLE cosmos (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  name TEXT NOT NULL, creator_name TEXT NOT NULL, creator_title TEXT,
  seed_idea TEXT NOT NULL, cosmology TEXT NOT NULL, tone TEXT NOT NULL,
  epoch INTEGER NOT NULL DEFAULT 1, epoch_start_year INTEGER NOT NULL DEFAULT 0,
  creator_essence INTEGER NOT NULL,
  doom_clock INTEGER NOT NULL DEFAULT 0,
  fate_mode TEXT NOT NULL DEFAULT 'auto' CHECK (fate_mode IN ('auto','off')),
  son_distribution TEXT NOT NULL DEFAULT 'auto' CHECK (son_distribution IN ('auto','manual')),
  council_every_epochs INTEGER NOT NULL DEFAULT 4,
  mortal_agents_per_epoch INTEGER NOT NULL DEFAULT 10, mortal_agent_parallelism INTEGER NOT NULL DEFAULT 1,
  unjudged_since_epoch INTEGER,            -- kader_borc
  alignment_until_epoch INTEGER,           -- hizalanma_son
  creator_profile JSON,                    -- appearance, temperament, image_prompt, note
  creator_depth JSON, creator_epic JSON, creator_mood JSON, creator_passions JSON,
  travel_resource JSON,
  genesis_settings JSON, notification_prefs JSON, model_prefs JSON,
  created_at TEXT NOT NULL
);
CREATE TABLE rule_override (key TEXT PRIMARY KEY, value INTEGER NOT NULL);    -- denge_ayar
CREATE TABLE epoch_run (                                                      -- cag_durum
  epoch INTEGER PRIMARY KEY, phase INTEGER NOT NULL DEFAULT 0, started INTEGER NOT NULL DEFAULT 0,
  state JSON);

CREATE TABLE star (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, kind TEXT NOT NULL,
  brightness INTEGER NOT NULL DEFAULT 60, x REAL NOT NULL, y REAL NOT NULL,
  description TEXT, image_prompt TEXT, created_epoch INTEGER NOT NULL);
CREATE TABLE world (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,
  kind TEXT NOT NULL,                    -- ordinary|ocean|sand|ice|lava|crystal|living|dead|dream|mirror|gas
  star_id INTEGER REFERENCES star(id), parent_world_id INTEGER REFERENCES world(id),
  orbit REAL NOT NULL DEFAULT 1, gravity TEXT NOT NULL, atmosphere TEXT NOT NULL,
  time_factor REAL NOT NULL DEFAULT 1, terrain_seed TEXT NOT NULL, terrain JSON,
  discovery TEXT NOT NULL DEFAULT 'known' CHECK (discovery IN ('known','legend','unknown','forgotten')),
  danger INTEGER NOT NULL DEFAULT 20, leakage INTEGER NOT NULL DEFAULT 0,
  cosmology TEXT, naming_rule TEXT, description TEXT, image_prompt TEXT,
  creator_son_id INTEGER REFERENCES son(id), patron_son_id INTEGER REFERENCES son(id),
  patron_auto INTEGER NOT NULL DEFAULT 0, epoch_star_entity_id INTEGER REFERENCES entity(id),
  mirror_twin_id INTEGER REFERENCES world(id), mortal_agents INTEGER,
  climate_era TEXT, climate_epochs_left INTEGER, climate_since_epoch INTEGER,
  created_epoch INTEGER NOT NULL);
CREATE TABLE route (id INTEGER PRIMARY KEY,
  world_a INTEGER NOT NULL REFERENCES world(id), world_b INTEGER NOT NULL REFERENCES world(id),
  method TEXT NOT NULL, duration_epochs INTEGER NOT NULL DEFAULT 2, danger INTEGER NOT NULL DEFAULT 30,
  known INTEGER NOT NULL DEFAULT 1, controller_entity_id INTEGER REFERENCES entity(id),
  vehicle_entity_id INTEGER REFERENCES entity(id), builder_son_id INTEGER REFERENCES son(id),
  description TEXT, created_epoch INTEGER NOT NULL, active INTEGER NOT NULL DEFAULT 1,
  temp_open_until_epoch INTEGER, temp_closed_until_epoch INTEGER,
  closed_by_forgetting_world_id INTEGER REFERENCES world(id));
CREATE TABLE journey (id INTEGER PRIMARY KEY, traveller_entity_id INTEGER NOT NULL REFERENCES entity(id),
  route_id INTEGER NOT NULL REFERENCES route(id), vehicle_entity_id INTEGER REFERENCES entity(id),
  destination_world_id INTEGER NOT NULL REFERENCES world(id),
  intent TEXT NOT NULL CHECK (intent IN ('colony','trade','exploration','conquest','pilgrimage')),
  population INTEGER NOT NULL DEFAULT 0, epochs_left INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'underway' CHECK (status IN ('underway','arrived','lost')),
  events JSON NOT NULL DEFAULT '[]', start_epoch INTEGER NOT NULL, result_entity_id INTEGER REFERENCES entity(id));
CREATE TABLE foreign_god (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, title TEXT, domains TEXT,
  world_id INTEGER NOT NULL REFERENCES world(id), power INTEGER NOT NULL DEFAULT 50,
  faith INTEGER NOT NULL DEFAULT 0, stance INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'awake' CHECK (status IN ('awake','asleep','defeated','dead')),
  contacted INTEGER NOT NULL DEFAULT 0, description TEXT, image_prompt TEXT,
  stats JSON, personality JSON, powers JSON, existence JSON, depth JSON,
  awakening_pressure INTEGER NOT NULL DEFAULT 0, awakening_avg REAL,
  defeated_epoch INTEGER, death_epoch INTEGER, created_epoch INTEGER NOT NULL);
CREATE TABLE horizon_intuition (id INTEGER PRIMARY KEY, mortal_entity_id INTEGER NOT NULL REFERENCES entity(id),
  world_id INTEGER REFERENCES world(id), epoch INTEGER NOT NULL, how TEXT, method TEXT,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','processing','born','wasted')),
  result_world_id INTEGER REFERENCES world(id));

-- ===== Sons =====
CREATE TABLE son (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
  rarity TEXT NOT NULL CHECK (rarity IN ('common','uncommon','rare','epic','legendary','mythic')),
  stars INTEGER NOT NULL DEFAULT 1, domain1 TEXT NOT NULL, domain2 TEXT NOT NULL,
  personality JSON NOT NULL, stats JSON NOT NULL, passions JSON NOT NULL, powers JSON NOT NULL DEFAULT '[]',
  existence_profile JSON, existence INTEGER NOT NULL DEFAULT 60, fading_epochs INTEGER NOT NULL DEFAULT 0,
  hp INTEGER NOT NULL, essence INTEGER NOT NULL, faith INTEGER NOT NULL DEFAULT 0, fame INTEGER NOT NULL DEFAULT 0,
  xp INTEGER NOT NULL DEFAULT 0, level INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','asleep','exiled','dead')),
  sleep_epochs_left INTEGER NOT NULL DEFAULT 0, chained INTEGER NOT NULL DEFAULT 0, rebel INTEGER NOT NULL DEFAULT 0,
  standing_order TEXT, order_absolute INTEGER NOT NULL DEFAULT 0,
  plan TEXT, epic JSON, anchor_entity_id INTEGER REFERENCES entity(id), corpse_entity_id INTEGER REFERENCES entity(id),
  parent_son_id INTEGER REFERENCES son(id), current_world_id INTEGER REFERENCES world(id),
  manually_assigned_epoch INTEGER, birth_epoch INTEGER NOT NULL, death_epoch INTEGER, last_acted_epoch INTEGER NOT NULL DEFAULT 0,
  reputation JSON, reputation_manual JSON, reputation_events JSON, image_prompt TEXT, created_at TEXT NOT NULL);
CREATE TABLE agent_turn (            -- replaces tur_cag/tur_ap/tur_ctx on son and entity
  agent_kind TEXT NOT NULL CHECK (agent_kind IN ('son','mortal')), agent_id INTEGER NOT NULL,
  epoch INTEGER NOT NULL, ap_left INTEGER, context JSON, PRIMARY KEY (agent_kind, agent_id));
CREATE TABLE son_relation (son_a INTEGER NOT NULL REFERENCES son(id), son_b INTEGER NOT NULL REFERENCES son(id),
  value INTEGER NOT NULL DEFAULT 0 CHECK (value BETWEEN -100 AND 100), note TEXT,
  PRIMARY KEY (son_a, son_b), CHECK (son_a < son_b));

-- ===== Entities =====
CREATE TABLE entity (id INTEGER PRIMARY KEY, name TEXT NOT NULL, title TEXT,
  type TEXT NOT NULL,                  -- region|place|resource|settlement|species|people|mortal|item|structure|language|legend|tradition|cult|faction|celestial|artwork|law|spirit|knowledge|prophecy|event|vehicle|outer_being|army|natural_law
  subtype TEXT, event_kind TEXT,       -- event_kind: war|battle|siege|magic_storm|earthquake|flood|plague|drought|storm …
  description TEXT NOT NULL, stats JSON NOT NULL DEFAULT '{}', power_level INTEGER NOT NULL DEFAULT 1, domain TEXT,
  origin TEXT NOT NULL CHECK (origin IN ('son','creator','engine','mortal','cosmos')),
  creator_son_id INTEGER REFERENCES son(id), maker_entity_id INTEGER REFERENCES entity(id),
  world_id INTEGER NOT NULL REFERENCES world(id), location_id INTEGER REFERENCES entity(id),
  status TEXT NOT NULL DEFAULT 'canon' CHECK (status IN ('canon','rejected','destroyed','dead','fulfilled')),
  pending_name INTEGER NOT NULL DEFAULT 0, fate_note TEXT, depth JSON, society JSON,
  birth_epoch INTEGER NOT NULL, end_epoch INTEGER, last_acted_epoch INTEGER NOT NULL DEFAULT 0,
  importance INTEGER, archive_override TEXT CHECK (archive_override IN ('history','atlas')),
  favorite INTEGER NOT NULL DEFAULT 0, private_note TEXT, map_x INTEGER, map_y INTEGER, image_prompt TEXT,
  civ_tier INTEGER, created_at TEXT NOT NULL);
CREATE UNIQUE INDEX ux_entity_name_live ON entity(lower(name)) WHERE status <> 'rejected';  -- or app-level cross-table check
CREATE TABLE entity_tag (entity_id INTEGER NOT NULL REFERENCES entity(id), tag TEXT NOT NULL, PRIMARY KEY (entity_id, tag));
CREATE TABLE entity_flag (entity_id INTEGER NOT NULL REFERENCES entity(id), flag TEXT NOT NULL, value TEXT,  -- trait:flying, branch:magic, mechanic:addictive, war_side:<id> …
  PRIMARY KEY (entity_id, flag, value));
CREATE TABLE thread_link (thread_id INTEGER NOT NULL REFERENCES thread(id), entity_id INTEGER NOT NULL REFERENCES entity(id),
  role TEXT NOT NULL CHECK (role IN ('related','advanced')), epoch INTEGER, PRIMARY KEY (thread_id, entity_id, role));
CREATE TABLE war_side (war_entity_id INTEGER NOT NULL REFERENCES entity(id), side_entity_id INTEGER NOT NULL REFERENCES entity(id),
  PRIMARY KEY (war_entity_id, side_entity_id));

-- ===== Graph =====
CREATE TABLE node (id INTEGER PRIMARY KEY, kind TEXT NOT NULL CHECK (kind IN ('entity','son','creator','foreign_god')),
  ref_id INTEGER NOT NULL, UNIQUE (kind, ref_id));   -- one row per graph node; FKs below point here
CREATE TABLE bond (id INTEGER PRIMARY KEY,
  source_node_id INTEGER NOT NULL REFERENCES node(id), target_node_id INTEGER NOT NULL REFERENCES node(id),
  type TEXT NOT NULL, description TEXT, role TEXT,      -- role split out of description for taraf/ilgili
  epoch INTEGER NOT NULL,
  state TEXT NOT NULL DEFAULT 'active' CHECK (state IN ('active','past','hidden_rejected','hidden_closed')),
  closed_reason TEXT, debt_amount INTEGER, debt_what TEXT, debt_due_epoch INTEGER, truce_until_epoch INTEGER);
CREATE INDEX ix_bond_src ON bond(source_node_id, type, state);
CREATE INDEX ix_bond_tgt ON bond(target_node_id, type, state);
CREATE TABLE community_relation (a INTEGER NOT NULL REFERENCES entity(id), b INTEGER NOT NULL REFERENCES entity(id),
  value INTEGER NOT NULL DEFAULT 0, blood_feud_since_epoch INTEGER, history JSON NOT NULL DEFAULT '[]',
  PRIMARY KEY (a,b), CHECK (a<b));

-- ===== Chronicle & lore =====
CREATE TABLE chronicle (id INTEGER PRIMARY KEY, epoch INTEGER NOT NULL, year INTEGER,
  kind TEXT NOT NULL, visible INTEGER NOT NULL DEFAULT 1,   -- replaces 'motor_ham'
  son_id INTEGER REFERENCES son(id), text TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE chronicle_entity (chronicle_id INTEGER NOT NULL REFERENCES chronicle(id) ON DELETE CASCADE,
  entity_id INTEGER NOT NULL REFERENCES entity(id), position INTEGER NOT NULL, PRIMARY KEY (chronicle_id, entity_id));
CREATE TABLE epoch (epoch INTEGER PRIMARY KEY, name TEXT, narrative TEXT, summary TEXT,
  year_start INTEGER, year_end INTEGER, closed_at TEXT, chronicler_name TEXT, chronicler_who TEXT);
CREATE TABLE epoch_world (epoch INTEGER NOT NULL, world_id INTEGER NOT NULL REFERENCES world(id),
  narrative TEXT, summary TEXT, PRIMARY KEY (epoch, world_id));
CREATE TABLE historian_view (id INTEGER PRIMARY KEY, epoch INTEGER NOT NULL, people_entity_id INTEGER NOT NULL REFERENCES entity(id),
  historian TEXT, text TEXT NOT NULL);
CREATE TABLE folk_belief (people_entity_id INTEGER NOT NULL REFERENCES entity(id), god_node_id INTEGER NOT NULL REFERENCES node(id),
  local_name TEXT, account TEXT NOT NULL, misconception TEXT, epoch INTEGER NOT NULL, PRIMARY KEY (people_entity_id, god_node_id));
CREATE TABLE canon_fact (id INTEGER PRIMARY KEY, subject_entity_id INTEGER NOT NULL REFERENCES entity(id),
  predicate TEXT NOT NULL, object_entity_id INTEGER REFERENCES entity(id), object_text TEXT,
  epoch INTEGER NOT NULL, source_entity_id INTEGER REFERENCES entity(id), active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE lexeme (id INTEGER PRIMARY KEY, language_entity_id INTEGER NOT NULL REFERENCES entity(id),
  word TEXT NOT NULL, meaning TEXT NOT NULL, part_of_speech TEXT, etymology TEXT, example TEXT,
  added_by_kind TEXT, added_by_id INTEGER, epoch INTEGER NOT NULL, created_at TEXT NOT NULL,
  UNIQUE (language_entity_id, word COLLATE NOCASE));
CREATE TABLE thread (id INTEGER PRIMARY KEY, epoch INTEGER NOT NULL, text TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','closed')), closing_text TEXT, closed_epoch INTEGER,
  progress INTEGER NOT NULL DEFAULT 0, quest JSON);
CREATE TABLE council (id INTEGER PRIMARY KEY, epoch INTEGER NOT NULL, topic TEXT NOT NULL, minutes JSON NOT NULL,
  passed INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
CREATE TABLE message (id INTEGER PRIMARY KEY, epoch INTEGER NOT NULL,
  from_node_id INTEGER REFERENCES node(id), to_node_id INTEGER REFERENCES node(id),
  intent TEXT, text TEXT NOT NULL, request TEXT, is_read INTEGER NOT NULL DEFAULT 0, answered INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL);

-- ===== Map, meta, UX =====
CREATE TABLE map_snapshot (epoch INTEGER PRIMARY KEY, data JSON NOT NULL);
CREATE TABLE map_note (id INTEGER PRIMARY KEY, world_id INTEGER NOT NULL REFERENCES world(id), x INTEGER NOT NULL, y INTEGER NOT NULL,
  text TEXT NOT NULL, color TEXT, created_at TEXT NOT NULL);
CREATE TABLE scenario (id INTEGER PRIMARY KEY, key TEXT NOT NULL, start_epoch INTEGER NOT NULL, end_epoch INTEGER,
  status TEXT NOT NULL DEFAULT 'running', data JSON, result TEXT);
CREATE TABLE achievement (key TEXT PRIMARY KEY, epoch INTEGER, achieved_at TEXT);
CREATE TABLE score (epoch INTEGER PRIMARY KEY, total INTEGER NOT NULL, breakdown JSON);
CREATE TABLE epoch_stats (epoch INTEGER PRIMARY KEY, data JSON NOT NULL);
CREATE TABLE notification (id INTEGER PRIMARY KEY, epoch INTEGER, category TEXT NOT NULL, severity INTEGER NOT NULL DEFAULT 2,
  title TEXT NOT NULL, body TEXT, target_node_id INTEGER REFERENCES node(id), chronicle_id INTEGER REFERENCES chronicle(id),
  is_read INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
CREATE INDEX ix_notification_unread ON notification(is_read, id);
CREATE TABLE image (id INTEGER PRIMARY KEY, target_node_id INTEGER, target_world_id INTEGER REFERENCES world(id),
  file_name TEXT NOT NULL, mime TEXT NOT NULL, caption TEXT, is_cover INTEGER NOT NULL DEFAULT 0, size_bytes INTEGER, created_at TEXT NOT NULL);
CREATE TABLE network_review (entity_id INTEGER PRIMARY KEY REFERENCES entity(id), epoch INTEGER NOT NULL);

-- ===== Undo ledger =====
CREATE TABLE ledger_entry (id INTEGER PRIMARY KEY, epoch INTEGER, actor_kind TEXT, actor_id INTEGER, actor_name TEXT,
  action TEXT, input_summary TEXT, created_at TEXT NOT NULL, undone INTEGER NOT NULL DEFAULT 0, undo_result JSON);
CREATE TABLE ledger_change (id INTEGER PRIMARY KEY, entry_id INTEGER NOT NULL REFERENCES ledger_entry(id) ON DELETE CASCADE,
  table_name TEXT NOT NULL, row_id INTEGER NOT NULL, op TEXT NOT NULL CHECK (op IN ('insert','update','delete')),
  before JSON, after JSON);

-- ===== Telemetry (separate DB file recommended) =====
CREATE TABLE llm_call (id INTEGER PRIMARY KEY, epoch INTEGER, job TEXT NOT NULL, model TEXT, kind TEXT, ms INTEGER, status TEXT,
  attempts INTEGER, turns INTEGER, input_tokens INTEGER, output_tokens INTEGER, cost_usd REAL, actions INTEGER, error TEXT, created_at TEXT);
CREATE TABLE live_event (id INTEGER PRIMARY KEY, ts_ms INTEGER NOT NULL, data JSON NOT NULL);
CREATE TABLE applied_fixup (key TEXT PRIMARY KEY, applied_at TEXT NOT NULL, result JSON);
```

Notes:

- `node` gives every graph participant one id, so `bond`, `message`, `folk_belief`, `notification` and `image` get real FKs. Creating an entity, son or foreign god inserts its node row in the same transaction.
- Name uniqueness is cosmos-wide across entity, son, star, world and foreign_god (02 §7). Implement it with a `name_registry(normalized_name PRIMARY KEY, kind, ref_id)` table, kept in sync on insert, rename and reject. This is O(1) and removes the full-table scans.
- `chronicle_entity.position` preserves `varlik_ids` order (the engine uses `ids[0]` as the main subject and `ids[1]` for e.g. the newborn).
- Drop: `ek` columns, `tur_*` resume columns (moved to `agent_turn`), the legacy `dunya.iklim`, and the `bilirdi`/`konusurdu` bond types.
- Telemetry goes in a second SQLite file, which makes backups simpler.

---

## 14. Data-model smells to avoid

1. **Polymorphic `tip/id` pairs with no FK** → orphaned bonds and messages are possible, and every query needs `kaynak_tip='v' AND …`. Fix: the `node` table.
2. **Tags double as data** (`taraf:12`, `iplik:5`, `basamak:3`) and are queried with `LIKE '%"taraf:12"%'` → slow and fragile (the old code once had `LIKE '%12%'` matching 112). Fix: typed link tables.
3. **Subtype strings as enums** (`alt_tur='savaş'`) that Fate's renaming could overwrite → required the "mechanical subtype" repair. Fix: a separate `event_kind` enum the LLM cannot edit.
4. **Bond description overloaded** (role, debt amount and due date, truce end, "closed: reason") and parsed with regexes. Fix: typed columns.
5. **Closed-bond semantics spread across three columns** (`aktif`, `red_kapatti`, `aciklama` prefix). Fix: a single `state` enum.
6. **`dunya.yil` vs epoch math** duplicated in four places. Fix: one `epoch_years()` service.
7. **Schema columns added from feature modules** (`panteon.js`, `gok.js`) → hidden schema. Fix: all DDL in migrations.
8. **Raw-engine chronicle rows** stored with `tur='motor_ham'` to hide them. Fix: a `visible` flag.
9. **Stale comments** (dunya.kiyamet "JSON [x,y]"; kaynak "ogul|tanri|dunya" while `olumlu` and `kozmos` exist; ogullar.durum missing `olu`). Fix: enums with CHECK constraints.
10. **Name uniqueness enforced only in code**, by scanning five tables per check.
11. **Ledger relies on TEMP triggers per connection** plus an AsyncLocalStorage-backed SQL function. This works only with one connection. Fix: explicit change capture in the repository layer (SQLAlchemy session events or a unit-of-work diff).
