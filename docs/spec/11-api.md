# 11 — HTTP API and realtime event stream

Source of truth (old app): `server.js` (≈1,075 lines, a hand-rolled `node:http` router: an ordered array of `[method, regex, handler]`), plus the domain functions it calls in `src/*.js`. Response shapes in this document were taken from a live run of the old server against a copy of a real world database (epoch 48, ≈3,600 graph nodes, ≈19,000 links), not guessed.

This document gives, for every endpoint:

- **Proposed** method and English path for the new FastAPI backend.
- **Old** method and path (Turkish).
- **Inputs** (path, query, body).
- **Output** shape (English field names; Turkish originals in parentheses where they are not obvious; see the glossary in §1.6).
- **Side effects** (DB writes, ledger entry, essence spent, chronicle lines, events emitted).
- **Used by** (which frontend view calls it; see `12-frontend.md`).

Domain mechanics behind each action (costs, formulas, probabilities) are specified in the engine/agent modules of this spec set; this file is the contract surface only. The cost key named for each action is the tunable rule key that supplies the essence price (the old app reads it live from the World Rules / `DENGE` system).

---

## 1. Cross-cutting conventions

### 1.1 Transport, origin and security (old behaviour, keep it)

- The server binds to `127.0.0.1` only; default port 4747 (`PORT` env; `PORT=0` = random free port). A PID lock file `aerona.lock` next to the DB refuses to start a second process on the same world (message tells the user to close the other process or delete the stale lock). On SIGINT/SIGTERM/SIGHUP it runs a WAL checkpoint then exits.
- **Origin guard** (applied before routing, returns `403 {error}`):
  1. `Host` header must be `localhost`, `127.0.0.1` or `[::1]` (any port) — "This server can only be used via localhost."
  2. If `Origin: null` and the request is a write (anything but GET/HEAD) → reject.
  3. If `Origin` is present it must be a localhost host; for writes it must equal the `Host` exactly (same port).
  4. For writes, `Sec-Fetch-Site` (if present) must be `same-origin` or `none`.
  5. Writes must be `Content-Type: application/json`, except the two binary-upload endpoints (image upload, world import) which must NOT be a "simple" CORS type (`text/plain`, `application/x-www-form-urlencoded`, `multipart/form-data`) — they expect `application/octet-stream` or `image/*`.
- New app: keep this as middleware (CSRF protection for a local single-user app). Add an optional bearer token only if the server is ever exposed beyond localhost.

### 1.2 Request bodies and validation

- JSON body limit 2 MB; image upload limit 30 MB; world package import limit 400 MB. Exceeding → `413` "File too large (max N MB)".
- Empty body is treated as `{}`. Body must be a JSON object (not array) → else `400`.
- Some routes type-check specific fields (`text` must be string, `list` must be array) → `400 '"<field>" must be a text/list'`.
- Integer query params are validated: must be an integer within `[min,max]` → else `400 '"<name>" must be an integer' / 'must be between min and max'`.
- New app: Pydantic models per endpoint replace all of this. Every request model in this document lists the fields.

### 1.3 Responses and errors

- Success: `200` with JSON (`application/json; charset=utf-8`).
- Errors: JSON `{ "hata": "<human message>" }` → rename to `{ "error": "<message>", "code": "<machine_code>" }` in the new API. Status mapping used by the old server:

| Status | Old meaning (`HTTP` map) | When |
|---|---|---|
| 200 `ok` | success | |
| 202 `kabul` | accepted (background job) | see §1.4 |
| 400 `hatali` | invalid request / domain rule violated | default for any thrown domain `Error` (e.g. "This needs 30 divine essence; you have 12 (cost rule COSTS.summon = 30)") |
| 403 `yasak` | origin guard | §1.1 |
| 404 `yok` | not found | entity/son/prayer missing; unknown `/api/*` route → "Unknown endpoint" |
| 409 `cakisma` | conflict / busy | another job running, world already exists, epoch not running, etc. |
| 413 `cok_buyuk` | too large | uploads |
| 423 `kilitli` | locked | world is in read-only **Discovery mode** and the request is a write |
| 500 `sunucu` | server bug | only for programmer errors (TypeError/ReferenceError/RangeError/SyntaxError, SQLite errors). Body: "Server error (record `<6 hex>`); details in the log." The 6-hex id is logged with method/path/stack. |
| 501 `desteksiz` | not supported | `POST /api/cag/durdur` if stop is unavailable |

- Error messages are scrubbed of absolute filesystem paths (`/Users/...`, `/home/...`, the repo root and DB dir are replaced with `…`).
- Domain errors are deliberately explanatory and name the tunable rule key that caused a refusal (e.g. "Star ★3 needs level 5 (now 4; World rule KURAL.yildiz_seviye = …)"). Keep this: in the new app return `{error, code, rule_key?, rule_value?}` so the UI can link to the World Rules editor.
- The client maps statuses without a message: 400 "Invalid request.", 404 "Not found.", 409 "Can't do that right now: a job is running.", 413 "File too large.", 423 "This world is read-only.", 500 "Server error.", 502 "Server unreachable.", 503 "Server busy."; network failure → "Couldn't reach the server. Is Weavers of the Void running?".

### 1.4 Background jobs ("arkaPlan" pattern)

Long LLM-backed actions (genesis, summon, revelation, deepen, epoch completion, council, world creation, image generation…) are started by the handler and **not awaited**:

1. Handler starts the promise, attaches a catch that logs.
2. Waits exactly one event-loop tick (`setImmediate`).
3. If the promise already rejected (synchronous validation: not enough essence, busy lock, not found): respond `404` if the message matches the "not found" family (`Son missing.`, `Entity missing.`, `Prayer missing.`, `No such … exists.`), else `409`, body `{hata}`.
4. Otherwise respond `202 {"tamam": true}`.

The actual result arrives on the realtime stream (§4) as events (`yeni_ogul`, `vahiy`, `derinlesti`, `is_bitti`, `hata`, `serbest`, …) and via the incremental change feed (`/api/degisim`). There are two locking flavours in the engine:

- **Exclusive lock** (`kilitle(tur, fn)`): one "busy" (`mesgul`) slot for the whole world: `cag` (epoch), `genesis`, `cagirma` (summon), `vahiy` (revelation), `uyandirma` (awaken peoples), `dunya` (create world), `konsey` (council), `prompt` (write image prompts), `ogul` (single son turn), `tamamlama` (auto-complete missing content). While busy, another exclusive request fails with 409 "Busy right now: <kind>".
- **Parallel job pool** (`paralelIs(key, kind, label, fn)`): keyed jobs (`v123:derin`, `o4:destan`, `t:suret`, `ag:kader`, `adlandirma`, …) that queue in a pool; duplicates by key are rejected; state is exposed in `state.isler` (running) and `state.sira` (queued), each `{anahtar (key), tur (kind), ad (label), basla (startMs)}`.

New app: model this as a first-class **Job** resource: `POST` returns `202 {job_id}`; `GET /api/jobs` lists running/queued; job lifecycle is pushed over the event stream (`job.queued/started/finished/failed`). Keep the "validate synchronously, fail fast with 4xx" behaviour.

### 1.5 Ledger wrapping ("defterli" / `el`)

Almost every god action is executed inside `defterli(toolName, fn)`: a DB SAVEPOINT is opened, every row write is captured into the **Ledger of Fate** (eylem defteri) as one page attributed to the creator god (`kim_tip='t'`), and on error the savepoint is rolled back (so spent essence is refunded automatically and no partial writes remain). Each page can later be **undone** (`POST /api/defter/:id/geri-al`). In this document "Ledger: `<tool>`" means the action is recorded as an undoable ledger page under that tool name.

### 1.6 Field-name glossary (old → proposed)

| Old | New | Old | New |
|---|---|---|---|
| `id` | `id` | `ad` | `name` |
| `tur` | `type` (or `kind`) | `alt_tur` | `subtype` |
| `durum` | `status` | `aciklama` | `description` |
| `statlar` | `stats` | `etiketler` | `tags` |
| `cag` | `epoch` | `yil` | `year` |
| `dunya` | `world` (the singleton game/world row) | `dunyalar` | `worlds` (planets) |
| `dunya_id` | `world_id` | `ogul`/`ogullar` | `son`/`sons` |
| `varlik`/`varliklar` | `entity`/`entities` (on a son: `varlik` = *existence* 0–100) | `yabanci` / `yabanci_tanri` | `foreign_god` |
| `tanri` | `creator` (the player god) | `tanri_oz` | `creator_essence` |
| `oz` | `essence` | `can` | `hp` |
| `inanc` | `faith` | `un` | `renown` |
| `seviye` | `level` | `yildiz` | `stars` (★1–5) |
| `nadirlik` | `rarity` | `guc_seviyesi` | `power_level` |
| `sinif` | `class` (power class derived from power_level) | `kapak` | `cover_image` (file name) |
| `gorsel_prompt` | `image_prompt` | `gorseller` | `images` |
| `kronik` | `chronicle` | `baglar` | `links` (bonds/edges) |
| `kaynak_tip/kaynak_id` | `source_type/source_id` | `hedef_tip/hedef_id` | `target_type/target_id` |
| `aktif` | `active` | `gecmis` | `historical` (inactive link) |
| `derinlik` | `depth` (LLM-written lore block) | `kader_notu` | `fate_note` |
| `konum_id` | `location_id` | `harita_xy` | `map_xy` |
| `yaratan_id` | `creator_son_id` | `yapan_id` | `maker_entity_id` |
| `mesajlar` | `messages` | `niyet` | `intent` |
| `kimden_tip/_id` | `from_type/_id` | `kime_tip/_id` | `to_type/_id` |
| `okundu` | `read` | `cevaplandi` | `answered` |
| `iliski` / `iliskiler` | `relation(s)` (son↔son affinity −100..100) | `itibar` | `reputation` |
| `mesgul` | `busy` | `isler` / `sira` | `jobs_running` / `jobs_queued` |
| `hata` | `error` | `tamam` | `ok` |
| `bedel` | `cost` | `onay` | `confirm` (typed confirmation string) |
| `onem` | `importance` | `arsiv` | `archived` (hidden into "history") |
| `iplik` / `iplikler` | `thread(s)` (open story threads) | `konsey` | `council` |
| `dua` / `dualar` | `prayer(s)` | `vahiy` | `revelation` |
| `iklim` | `climate` | `sizinti` | `leak` (outside seeping in, 0–100) |
| `kiyamet` | `doom` (doomsday clock) | `kesif` | `discovery` (also: world's known-state; also read-only "discovery mode") |
| `rota` / `rotalar` | `route(s)` (inter-world) | `yolculuk` | `voyage` |
| `yildizlar` (table) | `stars` (celestial) | `harita` | `map` |
| `defter` | `ledger` | `bildirim` | `notification` |
| `denge` | `rules` (balance) | `hedefler` | `goals` |
| `senaryo` | `scenario` | `basarim` | `achievement` |
| `toplu derin` | `batch deepening` | `gorsel uret` | `image generation` |
| `sozluk` | `dictionary` | `dil` | `language` |
| `bilgi` | `knowledge` (tech) | `dal` | `branch` |

Target-type codes used everywhere (`tip`): `o` son, `v` entity, `t` creator god (id always 1), `d` world/planet (`dunyalar.id`), `y` foreign god, `m` (dictionary contributor: a place/entity, used in `ekleyen_tip`). New app: use string enums `son | entity | creator | world | foreign_god`.

Entity status (`durum`) values: `kanon` (canon, alive/active), `olu` (dead/destroyed), `gerceklesti` (fulfilled — prophecies), `reddedildi` (rejected by Fate / removed from canon), plus transient proposal states. "Visible" lists use `durum IN ('kanon','olu','gerceklesti')`.

### 1.7 Read-only Discovery mode

When another world package was imported in "discovery" mode, every non-GET request except `POST /api/kesif/bitir` returns `423` "Discovery mode: this world is read-only. Return to your own world to make changes." The client also short-circuits POSTs locally when `state.kesif` is set.

---

## 2. Endpoint catalogue

Notation: `Body {field: type}`; `?` = optional. "Async" = background job (§1.4, returns 202). "Ledger" = undoable ledger page (§1.5). "Cost" = essence deducted from the creator's pool (`dunya.tanri_oz`), refunded on failure.

### 2.1 Bootstrap, state and change feed

#### GET `/api/state` — old `GET /api/state`
Full application snapshot; fetched on load, after big changes, and as fallback when the change feed says `tam` (full).
- Output when no world exists: `{ dunya: null, kurallar, mesgul }`.
- Output with a world (all keys):
  - `world` (`dunya`): the singleton world row: `id, name (ad), creator_name (tanri_adi), seed (tohum), cosmology (kozmoloji), naming_rule (isim_kurali), tone (ton), epoch (cag), year (yil), creator_essence (tanri_oz), fate_mode (kader_modu: 'otomatik'|'kapali'), created_at, models (JSON|null), creator_title (tanri_unvan), creator_appearance (tanri_gorunus), creator_temperament (tanri_mizac), creator_image_prompt (tanri_prompt), epoch_star_id (cagin_yildizi), mortal_agent_count (olumlu_sayisi), map_version, doom (kiyamet), epoch_progress (cag_durum JSON|null), fate_debt (kader_borc), climate (iklim JSON), mortal_parallelism (olumlu_paralel), rules_version, cosmos_version, cosmic_resource (kozmik_kaynak JSON), creator_epic (tanri_destan JSON), creator_depth (tanri_derinlik JSON), creator_note (tanri_notu), creator_mood (tanri_ruh JSON), son_distribution ('otomatik'|'elle'), council_frequency (konsey_sikligi), notification_settings (JSON), creator_passions (tanri_tutku JSON), rule_overrides (denge_ayar JSON), genesis_settings (yaratilis_ayar), data_version, last_alignment` + computed `creator_cover` (`tanri_kapak`), `world_cover` (`dunya_kapak`).
  - `sons` (`ogullar`): array of **SonPublic** (see §3.1).
  - `counts` (`sayim`): `{ <entityType>: n }` for visible entities (e.g. `{bolge:75, dil:67, halk:76, olumlu:1099, …}`).
  - `prayers_pending` (`dualar`): count of unanswered prayers to the creator excluding chat.
  - `relations` (`iliskiler`): `[{a, b, value (deger), note (not_)}]` son↔son affinities.
  - `busy` (`mesgul`): `null | {tur: 'cag'|'genesis'|…, basla, ogul_id?}`.
  - `read_only` (`salt_okunur`): bool (discovery mode).
  - `version` (`surum`): change-feed cursor string `"<epochToken>:<seq>"`.
  - `jobs_running` (`isler`), `jobs_queued` (`sira`): `[{anahtar, tur, ad, basla}]`.
  - `batch_deepen` (`toplu_derin`): `{calisiyor, durdur, toplam, bitti, hata, atlandi, suan[], basla, bitis, kalan}`.
  - `image_gen` (`gorsel_uret`): `{kurulu (installed), model, hazir (ready), suren (current), sira (queue[]), toplu {calisiyor, durdur, oto, toplam, bitti, hata, atlandi, basla, bitis, kalan}, ayar {genislik, yukseklik, adim}}`.
  - `notifications_unread` (`bildirim_okunmamis`): int.
  - `discovery` (`kesif`): `null | {ad, cag, tanri, …}` (the guest world being browsed; `{ad:'unrecognized guest world', bozuk:true}` if broken).
  - `creator_reputation` (`tanri_itibar`): `{etiket (label), sevgi (love), korku (fear), unutma (forgetting), tutkular (passions[]), otomatik}`.
  - `models` (`modeller`): map `rarity|role → 'haiku'|'sonnet'|'opus'` (roles: `yaygin, seckin, nadir, destansi, efsanevi, mitik, kader, yaratilis, cagirma, derinlik, vahiy`).
  - `half_epoch` (`yarim_cag`): `null | {cag, asama, basladi, …}` — a stopped, resumable epoch.
  - `fate_debt` (`kader_borc`).
  - `climate` (`iklim`): `{evre (phase), kalan (epochs left), bas (start epoch), ad (label), bereket (fertility delta), agirlik, aciklama}` for world 1.
  - `worlds` (`dunyalar`): `[{id, ad, tur, kesif, sizinti}]`.
  - `foreign_god_count` (`yabanci_sayi`).
  - `worlds_status` (`dunyalar_durum`): `[{id, ad, cagin_yildizi: {id, ad, alan}|null, iklim: {evre, ad, kalan, bas}|null}]`.
  - `creator_mood` (`tanri_ruh`): `{hosnutluk (contentment), ofke (anger), ilgi (interest), yalnizlik (loneliness), girdi: {ofke: [...], hosnutluk: [...]}, etiket (label)}`.
  - `creator_faith` (`yaratici_inanc`): int; `creator_cult_size` (`yaratici_kult`): int.
  - `pending_sons` (`bekleyen`): ids of sons who have not yet acted this epoch.
  - `last_epoch` (`cag`): the previous epoch row `{cag, ad, anlati, ozet, yil_bas, yil_son, kapanis, kronikci (JSON chronicler)}`.
  - `loneliness` (`solus`): per-son solitude status list.
  - `threads` (`iplikler`): open story threads.
  - `epoch_star` (`cagin_yildizi`): `{id, ad, alan (domain), kapak}|null`.
  - `image_count` (`gorsel_sayisi`), `promptless_count` (`promptsuz`).
  - `pulse` (`nabiz`): live world snapshot = same shape as one row of `/api/istatistik` (`nufus, murit, varlik, kelime, bilgi, dil, savas, ticaret, ittifak, yapit, esya, olu, tanrisiz, ogullar{…}, kiyamet`).
  - `covenants` (`ahitler`): active son↔son alliance links `[{a, b, aciklama}]`.
  - `rules` (`kurallar`): the static/semi-static rules catalogue (§3.6).
- Side effects: none. Used by: app shell (`core/yenile.js`), every view.

#### GET `/api/changes?since=<version>` — old `GET /api/degisim?surum=`
Incremental change feed driven by SQLite triggers into a temp `degisim` table (table, rowid, op, seq).
- Output: `{ surum (new version), tam (full: bool), durum (status), … }` where
  - `durum` always present: `{mesgul, isler, sira, gorsel_uret, tanri_oz, cag, bildirim_okunmamis, yarim_cag, tahmin}` (`tahmin` = epoch ETA, only while an epoch runs, shape of `/api/cag/tahmin`).
  - If `tam: true` (cursor unknown/expired, server restarted, or more than `degisim_sinir` changed rows) the client must refetch `/api/state`.
  - Else additionally: `tablolar` (raw `{table: {degisen:[ids], silinen:[ids]}}`), `varliklar` (changed visible entities, full rows + `sinif`, `kapak`), `varlik_silinen` (deleted or now-rejected entity ids), `ogullar` (changed sons as SonPublic), `ogul_silinen`, `kronik_yeni` (count of new chronicle rows), `baglar` (bool: links changed), `dunyalar` (bool: worlds/stars/foreign gods/routes/voyages changed), `dunya` (bool: the world row changed *meaningfully* — ignoring volatile columns `tanri_oz, cag, yil, cag_durum, harita_surum, kozmos_surum, veri_surum, denge_surum, hizalanma_son`), `iliskiler` (bool), `yabanci` (changed/deleted foreign-god ids).
- Used by: `core/yenile.js` poller (after every SSE burst / on a timer). New app: replace with server-pushed `entity.changed` events over the WebSocket/SSE plus a `since` resync endpoint with the same semantics.

#### GET `/api/events` (SSE) — old `GET /api/olaylar`
See §4.

#### GET `/api/activity-log` — old `GET /api/gunluk`
Last `SUNUCU.gunluk_api` (300) events from the in-memory event ring buffer `E.GUNLUK` (same objects as SSE events plus `zaman` ms timestamp). Used by the live feed to backfill on page load. Ring buffer is cleared whenever the world is swapped (import/restore/reset).

#### GET `/api/health` — old `GET /api/saglik`
- Output: `{durum: 'iyi'|'uyari'|'kotu' (ok|warn|bad), surum (app version), node, pid, port, calisma_sn (uptime s), db: {dosya, boyut, wal, quick_check}, son_yedek: {dosya, tarih, yas_dk}|null, yedek_sayisi, mesgul, isler, sira, salt_okunur, gunluk (relative log path), son_hatalar: [{seviye, zaman, metin}]}`.
- `durum`: `kotu` if `PRAGMA quick_check != 'ok'`; `uyari` if any `HATA`-level log in the last `SUNUCU.saglik_hata_dk` (10) minutes; else `iyi`. `son_hatalar` = last `SUNUCU.saglik_hata_liste` (10) errors, newest first.
- Used by: Settings → health section.

#### GET `/api/names` — old `GET /api/adlar`
Name index for auto-linking names in prose and for datalist pickers.
- Output: array of `{t:'v', id, ad, tur, durum, ek}` for all non-rejected entities, `{t:'o', id, ad, tur:'ogul', nadirlik, ek}` for sons, `{t:'y', id, ad, tur:'yabanci_tanri', dunya_id}` for foreign gods. `ek` = Turkish suffix metadata `{okunus, tamlama}` (LANGUAGE-SPECIFIC: drop).
- Used by: `core/adlar.js` (builds the name→link regex), all forms with name pickers.

#### GET `/api/search?q=` — old `GET /api/ara?q=`
Global search (command palette). Query is folded (Turkish lower-case, dotless-i→i, circumflex removed) and must be ≥2 chars, else `[]`. Matches by substring across many tables; per-category limits (rule keys in group "Search"): sons 8 (name/title/domains), foreign gods 10, worlds 10 (name/description/cosmology), celestial stars 10, entities 25 (name/subtype/description/depth; name matches first, then newest), dictionary words 10 (word/meaning), epochs 5 (name/narrative/summary), chronicle 15 (text, excluding `sistem`), personal notes 6, map notes 6, messages 8 (text/request), councils 5. Total cap 60.
- Output: `[{t, id, ad, alt (subtitle), tur, …extra}]` where `t` ∈ `o` son, `y` foreign god, `d` world, `ys` celestial star, `v` entity, `k` dictionary word (id = language id), `c` epoch (id = epoch no.), `kr` chronicle line (`cag`), `n` note (`hedef: 'varlik'|'harita'`, `dunya_id` for map notes), `m` message (`cag`), `ks` council (`cag`). Snippets (`kesit`) are ~110 chars centred 40 chars before the hit with ellipses.
- Used by: command palette (`views/palet.js`), chronicle search (`views/kronik.js`). New app: use SQLite FTS5 with an English tokenizer.

### 2.2 Genesis (world creation / onboarding)

#### GET `/api/genesis/wizard` — old `GET /api/sihirbaz`
- Output: `{sablonlar (templates), secenekler (options)}`:
  - `templates`: new app `list[WizardTemplate {key, name, tone, magic, danger, technology, language, peoples, cosmos, seed, storyteller, shape, world_type?, climate_era?, world_age?}]` (legacy `{key: {ad, ton, buyu, karanlik, teknoloji, dil, halk, kozmos, tohum}}`) — keys `karanlik_fantazi` (Dark fantasy), `mitoloji` (Mythic age), `kozmik_korku` (Cosmic horror), `masal` (Fairy tale), `yildiz_mitosu` (Star myth), `kum_ve_kul` (Sand and ash), plus the new `primordial_dawn`, `crowns_and_knives`, `drowned_world`, `long_winter`, `after_the_fall`, `sky_islands`, `age_of_engines`, `many_suns`, `layered_realms`, `living_world`, `dreaming_world`, `generation_ship`, `without_magic`, and with W33 `electric_age`, `information_age` and `advanced_age`, so every technology era has a template. Full content is specified in `13-depth-expansion.md` §10.19.
  - New app options also carry `shapes` (shape, label, hint), `layer_kinds` (kind, label, description), `world_types` (world_type, label, description), `climate_eras` (era, label, description), `world_ages` and `first_sons`.
  - `options`: `teknoloji` {tas stone age, tunc bronze age, demir iron age, ortacag medieval, ronesans renaissance, buhar steam & gunpowder}; `dil` (phonetic flavour) {akici flowing, sert hard-consonant, girtlak guttural, islikli sibilant, uzun long agglutinative, karisik free}; `kozmos` {tek single world, kucuk small cosmos (2 worlds), buyuk large cosmos (3+ worlds)}.
- Used by: genesis screen.

#### POST `/api/genesis` — old `POST /api/genesis` (Async)
- Body: `{tanri_adi (creator_name): string, required; tohum (seed): string, required; ton (tone)?: string; sihirbaz (wizard)?: {sablon?, buyu?, karanlik?, teknoloji?, dil?, halk?, kozmos?}}`. New app wizard: `{template, magic, danger, technology, language, peoples, cosmos, shape, layer_kind, storyteller, world_type, sea_pct, mountains_pct, moisture_pct, climate_era, world_age, tone, seed}`; every choice may be null for "the seed decides". If `sihirbaz` is given it is sanitized (`sihirbazTemizle`) and may rewrite `tohum`/`ton`.
- Errors: 400 "Creator name and world seed are required."; 409 "World already exists."; 409 "Genesis already running."
- Side effects (background, in order): emit `mesgul {tur:'genesis'}` → run LLM genesis (cosmology, language, creator avatar, first land, first star, first three sons: one Common, one Rare, one Legendary) → emit `genesis_bitti` → emit `sistem` "The first mortal peoples are waking…" → awaken `wizard.halk ?? 2` peoples (emit `sistem` with names, or `hata` on failure) → for each extra world implied by `kozmos` (`ekDunyaSayisi`), birth a sibling world (`dunyaDogur`; new app inspiration "The Nth world of this creation, grown from the same seed as the first world: <seed>", placed by the cosmos shape, 13 §10.19) → finally emit `serbest`. Failure: `hata` "Genesis failed: …".
- Used by: genesis screen.

### 2.3 Epoch control

| Proposed | Old | Notes |
|---|---|---|
| POST `/api/epochs/current/complete` | POST `/api/cag/tamamla` | Async, exclusive lock `cag`. Runs/resumes the epoch: pending sons act, mortals act, world engine, Fate judgement, chronicle. Resumes from `half_epoch` stage if one exists. Emits the full epoch event sequence (§4). On end emits `cag_bitti`; server then recomputes importance scores, prunes model-metrics and checkpoints WAL. Used by: header "Complete epoch" button, command palette. |
| POST `/api/epochs/current/stop` | POST `/api/cag/durdur` | 409 "No epoch is running." if busy kind ≠ `cag`. Sets a stop flag; the epoch stops at the next safe point (between son turns, mortal turns or stages), saves `cag_durum`, emits `sistem` "Epoch N stopped (after stage k). 'Complete epoch' resumes it." Output `{tamam:true}`. Used by: header "Stop" button (with confirm "Are you sure? Stop at a safe point"). |
| GET `/api/epochs/current/estimate` | GET `/api/cag/tahmin` | `{ornek (sample count), ort_cag_sn (avg epoch seconds), asama_baslangic_ort_sn: {stage: avgStartSec}, calisiyor, gecen_sn (elapsed), kalan_sn (remaining), asama: {no, ad, sure, toplam}|null}` — computed from model-metrics history and the last `asama` event. Used by: live feed progress bar. |
| GET `/api/epochs` | GET `/api/caglar` | All closed epochs newest first: `[{cag, ad (name), anlati (narrative), ozet (summary), yil_bas, yil_son, kapanis (closed_at), kronikci: {ad, kim} (chronicler persona), dunyalar: [{cag, dunya_id, anlati, ozet, dunya_ad}] (per-world narratives)}]`. Used by: Chronicle. |
| GET `/api/epochs/{n}/breakdown` (default latest) | GET `/api/dokum?cag=` | `{cag, onceki_cag, dokum: {kiyamet: [{kalem (item), d (delta)}], sizinti: [{dunya, dunya_id, kalemler[]}], nufus: [...], oz: [...]}, deger (all stat values at epoch end), fark: {key: {once, simdi, fark}}, ogullar: {sonId: {stat: delta}}}`. 404 "No statistics for this epoch." Used by: epoch breakdown modal (`core/dokum.js`). |
| GET `/api/stats/epochs` | GET `/api/istatistik` | Per-epoch world statistics rows `[{cag, nufus (population), murit (devotees), varlik (entities), kelime (words), bilgi (knowledge), dil (languages), savas (wars), ticaret (trade links), ittifak (alliances), yapit (works), esya (items), olu (dead), tanrisiz?, kiyamet?, ogullar: {sonId: {inanc, un, varlik, seviye}}}]` plus a final live row `{cag: current, simdi: true, …pulse}`. `[]` if no world. Used by: Chronicle stats charts (`views/grafik.js`). |

### 2.4 Summon, revelation, awakening (creation acts)

| Proposed | Old | Body | Notes |
|---|---|---|---|
| POST `/api/sons/summon` | POST `/api/cagir` | `{dunya_id?: int}` | Async, lock `cagirma`. Cost `COSTS.cagirma` (30). Optional target world (error if missing or forgotten world). LLM creates a new son (random rarity by weights); emits `yeni_ogul {ogul}`. Refund on failure. Used by: header "Summon son", palette. |
| POST `/api/revelations` | POST `/api/vahiy` | `{metin (text): string, required; tur (entity type)?: string; dunya_id?: int; mekanik (law mechanic)?: string}` | Async, lock `vahiy`. Cost `COSTS.vahiy` (25) charged inside a ledger page `vahiy`. The creator personally creates one entity from the text. Emits `vahiy {varlik}`. Errors: "A revelation must have content." Used by: revelation modal (header "Revelation"). |
| POST `/api/peoples/awaken` | POST `/api/uyandir` | `{sayi (count)?: int=2, dunya_id?: int}` | Async, lock `uyandirma`. Count is split into batches of `UYANIS.tavan`; cost `DENGE.uyandir × batches`. Emits `sistem` "Awakened peoples: …". Used by: goals/actions panel (`views/hedefler.js`). |
| POST `/api/worlds` | POST `/api/dunya-yarat` | `{tur?: worldType, ilham (inspiration)?: string, yildiz_id?: int, ana_dunya_id? (parent world → moon), yeni_yildiz?: bool}` | Async, lock `dunya`. Cost `DENGE.dunya` (120). Births a new planet in the cosmos. Used by: Cosmos → Create. |
| POST `/api/councils` | POST `/api/konsey` | `{konu (topic): string}` | Async, lock `konsey`. Cost `DENGE.konsey` (20). Convenes all sons to debate & vote; emits `konsey` events. Used by: goals panel. |
| POST `/api/entities/prompts/write-missing` | POST `/api/promptlar` | — | Async, lock `prompt`. Writes missing image prompts in batches (`AJAN.prompt_tur` rounds × `ICERIK.prompt_parti`). Emits `sistem` "N entities got an image prompt." Used by: Settings. |
| POST `/api/names/assign-missing` | POST `/api/adlandir` | — | Parallel job `adlandirma`; 409-like reject if any exclusive lock is busy ("Busy: <kind>. The epoch names its own."). LLM names nameless engine-created records. Used by: Settings → batch section (`views/toplu.js`). |

### 2.5 Creator god (the player)

| Proposed | Old | Input | Output / side effects | Used by |
|---|---|---|---|---|
| GET `/api/creator` | GET `/api/tanri` | — | `{ad, unvan (title), gorunus (appearance), mizac (temperament), prompt (image prompt), not (note), kapak, destan (epic {baslik, dize, bolumler:[{baslik, cag_bas, cag_son, metin}], cag}), derinlik (depth {tarih, adlari:[{ad, kim, anlam}], sirlar[], korkular[], yasaklar[], armaganlar[], istek, sozler:[{tur, metin}], soylentiler[], gizli_gercek, cag}), ruh (mood + etiket), inanc (faith), kult: [{id, ad, tur}] (entities worshipping the creator), halklarin_gozunden (how peoples see him: [{halk_id, ogul_id:0, ad, anlati, yanlis (misbelief), cag, halk_ad}]), izler (last 40 chronicle traces of types tanri, vahiy, dunya_dogusu, konsey, tanri_isareti, emir: [{cag, yil, tur, metin}])}`. 404 "No world" | Creator drawer |
| PATCH `/api/creator` | POST `/api/tanri` | `{tanri_unvan?, tanri_gorunus?, tanri_mizac?, tanri_prompt?}` strings (empty → null) | Updates world row; returns world. Ledger `tanri:duzenle` | Creator drawer, image-prompt editor |
| POST `/api/creator/portrait` | POST `/api/tanri/suret` | — | Async parallel job `t:suret`: LLM redraws the creator's visage; emits `sistem`. | Goals panel |
| POST `/api/creator/epic` | POST `/api/tanri/destan` | — | Async job `t:destan`: LLM writes creator's epic. | Creator drawer |
| POST `/api/creator/deepen` | POST `/api/tanri/derinlestir` | — | Async job `t:derin`: LLM writes creator depth block. | Creator drawer |
| PUT `/api/creator/note` | POST `/api/tanri/not` | `{metin: string}` (cut to `TANRI.not_uzunluk`; empty → null) | `{not}`. Ledger `tanri:not`. The note is fed to agents as the creator's standing word. | Creator drawer |
| PUT `/api/creator/mood` | POST `/api/tanri/ruh` | `{hosnutluk?, ofke?, ilgi?, yalnizlik?}` 0–100 | Overwrites mood; returns new mood. Ledger `tanri:ruh` | Creator drawer |
| GET `/api/creator/reputation` | GET `/api/tanri/itibar` | — | `{sevgi, korku, unutma, etiket, ogullar: [{id, ad, sevgi, korku, unutma, cevapsiz (unanswered prayers), son_temas (last contact epoch), etiket}], tutkular: [keys], otomatik, tum_tutkular: {key: {ad, ipucu}}}`. Passion keys: `duzen` order, `kaos` chaos, `guzellik` beauty, `bilgi` knowledge, `savas` war, `merhamet` mercy, `yaratim` creation, `sessizlik` silence. | Creator drawer |
| PUT `/api/creator/passions` | POST `/api/tanri/tutku` | `{tutkular: string[] (≤ ITIBAR.tutku_sayi), otomatik?: bool}` | If `otomatik` → passions inferred automatically. Else validates ≥1; chronicle "X introduced himself: passions …". Ledger `tanri:tutku` | Creator drawer |
| POST `/api/sons/{id}/reputation-nudge` | POST `/api/ogullar/:id/itibar` | `{sevgi?, korku?, unutma?}` deltas | Adds to manual nudges, each clamped ±`ITIBAR.elle_tavan`; nudges decay every epoch. 400 if at cap or son dead. Ledger `itibar` | Son drawer |

### 2.6 Sons (god cards)

`GET /api/sons/{id}` — old `GET /api/ogullar/:id` → **SonDetail** (§3.2). 404 `{hata:'Yok'}`. Used by: son drawer, opening view (`views/acilis.js`).

All POSTs below return the updated son (raw row, not SonPublic) unless noted. "Alive" = `durum != 'olu'`.

| Proposed | Old | Body | Cost / rule | Effect | Ledger |
|---|---|---|---|---|---|
| POST `/sons/{id}/act` | `/ogullar/:id/hareket` | — | — | Async, lock `ogul`: run this son's agent turn now (thinks, uses tools, emits feed events). | (agent's own pages) |
| PUT `/sons/{id}/order` | `/ogullar/:id/emir` | `{metin: string}` (empty clears) | — | Sets standing order; clears absolute-command flag; inserts message `t→o` intent `emir`; chronicle "X commanded Y: '…'". Dead son + non-empty → 400. | `emir` |
| POST `/sons/{id}/bless` | `/ogullar/:id/kutsa` | `{tur: 'oz'|'can'|'stat'|'varlik', stat?: statKey}` | `COSTS.kutsa_oz` (15) for oz & varlik, `COSTS.kutsa_can` (15), `COSTS.kutsa_stat` (40) | oz: +`TANRI_EYLEM.kutsa_oz` essence (≤ max); can: full HP; stat: +`kutsa_stat` to one stat (≤100); varlik: +`kutsa_varlik` existence. +loyalty. Refuses (no cost) if already full. | `kutsa` |
| POST `/sons/{id}/punish` | `/ogullar/:id/cezalandir` | `{tur: 'yildirim'|'zincir'|'surgun'|'bastir'|'af'}` | `COSTS.yildirim` (10); `DENGE.bastir` | lightning: −HP%; chain: can't act this epoch (400 if already acted); exile: status `surgun`; suppress rebellion: contest creator power vs son power, success resets rebel flag, failure raises renown/ambition & costs extra essence; pardon (`af`): lifts exile/chain/rebellion. Loyalty/anger shifts differ for defiant sons (irade > threshold). | `ceza:<tur>` |
| POST `/sons/{id}/star` | `/ogullar/:id/yildiz` | — | `KURAL.yildiz_oz_taban + ★ × KURAL.yildiz_oz` | Requires level & renown thresholds; +stats, full HP; ★+1 (max 5). | `yildiz` |
| POST `/sons/{id}/ascend` | `/ogullar/:id/yukselt` | — | `YUKSELIS.oz` | Requires ★5, level & renown; rarity → next tier, re-rolls stats upward, ★ resets to 1, spawns a legend entity "X's Ascension"; emits `yukselis`. | `yukselis` |
| POST `/sons/{id}/epic` | `/ogullar/:id/destan` | — | — | Async job `o<id>:destan`: LLM writes the son's epic. | — |
| POST `/sons/{id}/resurrect` | `/ogullar/:id/dirilt` | — | `DENGE.dirilis` (150) | Only dead sons. | `dirilt` |
| POST `/sons/{id}/kill` | `/ogullar/:id/oldur` | `{sebep (reason)?: string}` | `OLUM.tanri_ogul_oldur` (100) | Son dies; corpse and resurrection cult remain; others bound by fear; friends angered. | `ogul_oldur` |
| POST `/sons/{id}/devour` | `/ogullar/:id/yut` | `{sebep?}` | per `TANRI_GUC` | Creator devours the son (gains essence). | `yut:ogul` |
| POST `/sons/{id}/drain` | `/ogullar/:id/oz-em` | — | gain | Draw essence from the son. | `oz_em:ogul` |
| POST `/sons/{id}/absolute-command` | `/ogullar/:id/mutlak-buyruk` | `{emir: string}` | `TANRI_GUC.*` | Order the son cannot refuse. | `mutlak_buyruk` |
| POST `/sons/{id}/demote` | `/ogullar/:id/alcalt` | — | | Rarity down one tier. | `alcalt` |
| POST `/sons/{id}/strip-power` | `/ogullar/:id/guc-sok` | `{sira: int}` (index into `gucler`) | `TANRI_GUC.guc_sok` | Removes one power. | `guc_sok` |
| PUT `/sons/{id}/world` | `/ogullar/:id/dunya` | `{dunya_id}` | — | Move son's active world (not if dead / forgotten world / already there). | `ogul:dunya` |
| PATCH `/sons/{id}` | `/ogullar/:id/duzenle` | `{ad?, unvan?, plan?, kisilik?: {gorunus, mizac, takinti, korku, uslup, sir}, tutku?: {sadakat, hirs, ofke, merhamet}, statlar?: {9 stats 1–100}, kaynak?: {oz, can, un, inanc, seviye, yildiz, varlik}, nadirlik?}` | — | Manual editor. Name change propagates through all texts and is rejected if taken or too similar to an existing name. | `ogul:duzenle` |
| PUT `/sons/{id}/image-prompt` | `/ogullar/:id/prompt` | `{prompt: string}` | — | | `ogul:prompt` |
| GET `/sons/{id}/chat` | GET `/ogullar/:id/sohbet` | — | | `[{kimden_tip: 't'|'o', metin, cag, olusturma}]` chat history (intent `sohbet`). | |
| POST `/sons/{id}/chat` | POST `/ogullar/:id/sohbet` | `{metin}` (≤ `KONSEY.sohbet_metin`) | — | **Synchronous** LLM call (timeout `KONSEY.sohbet_sure` s; structured output `{cevap (reply, 1–4 sentences in character), tavir (attitude: 'sadik' loyal / 'mesafeli' distant / 'asi' rebellious / 'korkmus' afraid / 'minnettar' grateful / 'alayci' mocking), sadakat_degisim (loyalty delta, ±KONSEY.sohbet_sadakat)}`). Applies the loyalty delta, stores both messages (intent `sohbet`). Returns `{cevap, tavir, sadakat (new loyalty), degisim (applied delta)}`. 400 if dead/empty. | |

Allowed fields for the son editor are published in `rules.OGUL_DUZEN_ALANLAR`.

### 2.7 Entities

#### GET `/api/entities` — old `GET /api/varliklar`
- Query: `tur` (type filter), `q` (substring of name/description/subtype; SQL LIKE), `durum` (`tum` = all statuses; a specific status; default visible statuses), `tarih=gizle` (hide archived "history" records).
- Output: array of full entity rows (`parseVarlik`: JSON columns parsed) + `sinif` (power class), `kapak`, and importance fields `{onem, arsiv, arsiv_sebep, son_anma}`. Ordered by id. **No pagination** (returns thousands; design smell — paginate in the new API).
- Used by: atlas, records drawer, world filter (`core/dunya.js`), tech picker in entity drawer.

#### GET `/api/entities/{id}` — old `GET /api/varliklar/:id` → **EntityDetail** (§3.3). 404.

#### Entity actions (all `POST /api/varliklar/:id/<x>` in the old app)

| Proposed | Old `<x>` | Body | Cost / rule | Effect | Ledger |
|---|---|---|---|---|---|
| PATCH `/entities/{id}` | `duzenle` | `{ad?, alt_tur?, aciklama?, gorsel_prompt?}` | | Rename propagates everywhere; empty subtype/prompt cleared; description cannot be emptied. | `varlik:duzenle` |
| PUT `/entities/{id}/canon` | `kanon` | `{durum: 'kanon'|'reddedildi'}` | | Reject: closes its open outgoing links (marked `red_kapatti`); restore: reopens only those. Dead mortals must use resurrect instead. Chronicle line. | `kanon:<durum>` |
| POST `/entities/{id}/intervene` | `mudahale` | `{eylem: 'mucize'|'afet'|'bilgi'|'lanet', tur?: miracleKey|disasterKey, bilgi_id?: techId}` | `MUDAHALE_BEDEL.{mucize 15, afet 20, bilgi 12, lanet 15}` | Miracle (`sifa` healing, `bereket` plenty, `baris` peace, `koruma` protection); disaster (`deprem` quake, `sel` flood, `veba` plague, `kuraklik` drought, `firtina` storm — only on region/place/settlement; creates an event entity); teach knowledge; curse (−stats, tag `lanetli`). No-op → refund + 400 explaining why. | `mudahale:<eylem>` |
| POST `/entities/{id}/dream` | `ruya` | `{metin}` (min/max `KONSEY.ruya_en_az/ruya_metin`) | `DENGE.ruya` (8) | Only thinking communities/mortals (`halk, yerlesim, hizip, tarikat, olumlu, tur`). Stored as unread message `kime_tip='v', niyet='ruya'`, interpreted on their next turn. | `ruya` |
| POST `/entities/{id}/deepen` | `derinlestir` | — | | Async job `v<id>:derin`; emits `derinlesti {varlik:{id, ad}}`. | |
| POST `/entities/{id}/image-prompt` | `prompt-uret` | — | | Async job `v<id>:prompt`. | |
| PUT `/entities/{id}/favorite` | `favori` | `{favori: bool}` | | `{id, favori}` | |
| PUT `/entities/{id}/note` | `not` | `{metin: string}` (≤4000) | | Personal note `{id, kisisel_not}` | |
| POST `/entities/{id}/merge` | `birlestir` | `{diger_id, onay: 'BİRLEŞTİR'}` → new confirm string `MERGE` | | Same-type entities only; 409 during an epoch. Moves links/chronicle refs from other into this one. | `birlestir` |
| POST `/entities/{id}/suggest-links` | `bag-oner` | — | | Async: Fate proposes justified links for this record (`agKader({ids:[id]})`). | |
| PUT `/entities/{id}/stat` | `stat` | `{stat, deger}` | | Clamped to the type's stat range. | `varlik:stat` |
| PATCH `/entities/{id}/tags` | `etiket` | `{ekle?: string[], sil?: string[]}` | | Only assignable tags (`rules.ETIKETLER`) or prefixes `ozellik:` (trait), `mekanik:` (resource mechanic), `yasa:` (law mechanic). | `varlik:etiket` |
| PUT `/entities/{id}/location` | `tasi` | `{konum_id}` | | Re-parent (contained-in). | `varlik:tasi` |
| PUT `/entities/{id}/patron` | `hami` | `{ogul_id?: int|null, yabanci_id?: int}` | | Set worshipped son or foreign god for communities/mortals (null clears). | `varlik:hami` |
| POST `/entities/{id}/decree` | `buyruk` | `{hedef_id, tur: 'baris'|'savas'|'ittifak'|'ticaret'}` | | Impose peace/war/alliance/trade between two entities (must be reachable worlds). | `buyruk` |
| PUT `/entities/{id}/agent` | `ajan` | `{secili: bool}` | | Toggle tag `ajan seçili` → this mortal/community acts as an LLM agent each epoch. | `varlik:ajan` |
| POST `/entities/{id}/explore` | `kesif` | `{tur?: 'bolge'|'yer'}` | | Send to discover new land; returns found entity. | `kesfe_yolla` |
| POST `/entities/{id}/seek-route` | `yol-ara` | — | | Reveal a route to another world or sense an unknown world. | `yol_arat` |
| POST `/entities/{id}/expedition` | `sefer` | `{rota_id, niyet: intent ('kesif' default; one of NIYETLER), yuzde (percent of population)}` | | Starts a voyage. | `sefer` |
| POST `/entities/{id}/exile` | `surgun` | `{dunya_id}` | | Banish to another world. | `surgun` |
| POST `/entities/{id}/pardon` | `af` | — | | | `af` |
| PUT `/entities/{id}/archive` | `arsiv` | `{durum: 'tarih'|'atlas'|'otomatik'}` | | Manual archive override (history / atlas / auto). Returns importance fields. | `varlik:arsiv` |
| POST `/entities/{id}/rite` | `ayin` | `{ogul_id, tur: 'dua'|… (prayer, wealth offering, blood, life sacrifice), kurban_id?}` | paid by the community | Rite to resurrect a dead son. | `ayin_buyur` |
| POST `/entities/{id}/take-life` | `can-al` | `{nasil (how)?: string}` | `OLUM.tanri_can_al` (15) | Certain death for a living named mortal (even immortal). | `tanri_can_al` |
| POST `/entities/{id}/drain` | `oz-em` | `{yut?: bool}` | gain | Drain/devour a mortal. | `oz_em:olumlu` / `yut:olumlu` |
| POST `/entities/{id}/harvest` | `hasat` | — | gain | Harvest faith from a community. | `hasat` |
| POST `/entities/{id}/resurrect` | `dirilt` | — | `TANRI_GUC.olumlu_dirilt + power×olumlu_dirilt_guc` | Dead mortal returns. | `dirilt:olumlu` |
| POST `/entities/{id}/deify` | `tanrilastir` | — | | Mortal becomes a new son; emits `yeni_ogul`. | `tanrilastir` |
| POST `/entities/{id}/prophet` | `peygamber` | — | | Choose as prophet. | `peygamber` |
| POST `/entities/{id}/manifest` | `tezahur` | `{soz (utterance)}` | | Creator manifests before them. | `tezahur` |
| POST `/entities/{id}/bloodline-curse` | `soy-laneti` | `{kaldir?: bool}` | | Curse / lift curse on lineage. | `soy_laneti[:kaldir]` |
| POST `/entities/{id}/convert` | `cevir` | — | | Turn a community to worship the creator. | `cevir` |
| POST `/entities/{id}/wrath` | `gazap` | `{sebep?}` | | Destroy. | `gazap` |

Exact costs/gains of the "creator's power" (`TANRI_GUC.*`) actions are specified in the god-powers module spec; the UI displays them from `GET /api/rules`.

#### Links, facts, beliefs, suffix metadata

| Proposed | Old | Body | Effect | Ledger | Used by |
|---|---|---|---|---|---|
| POST `/api/links` | POST `/api/baglar` | `{kaynak_tip='v', kaynak_id, hedef_tip='v', hedef_id, tur (link type from rules.BAG_TURLERI, excluding 'icinde'), aciklama?}` | Add bond (ends must be entity `v` or son `o`). | `bag:ekle` | Entity drawer |
| DELETE `/api/links/{id}` | POST `/api/baglar/:id/sil` | — | Deactivate bond. | `bag:sil` | Entity drawer |
| POST `/api/federations` | POST `/api/federasyon` | `{uyeler: int[] (≥2 living communities), ad?: string}` | Create federation entity; ends wars between members; adds mutual alliances; chronicle. | `federasyon` | Cosmos |
| POST `/api/facts` | POST `/api/gercekler` | `{ozne_id, iliski (relation text), nesne_id? , nesne? (free text)}` | Canon fact triple. | `gercek:ekle` | Entity drawer |
| DELETE `/api/facts/{id}` | POST `/api/gercekler/:id/sil` | — | `aktif=0`. | `gercek:sil` | Entity drawer |
| PUT `/api/beliefs` | POST `/api/inanclar` | `{halk_id, ogul_id (0 = creator), ad (local name), anlati (narrative, required), yanlis (misbelief)?}` | How a people sees a god. | `inanc` | Son drawer |
| PUT `/api/name-grammar` | POST `/api/ek` | `{t:'v'|'o', id, okunus?, tamlama?, sifirla?}` | **LANGUAGE-SPECIFIC: drop.** Turkish suffix pronunciation override for a name. | `ek` | Son/entity drawers |
| GET `/api/graph/path?a=&b=` | GET `/api/yol?a=v12&b=o3` | ids `v<id>`/`o<id>` | `{yol: [nodeIds], adlar: {nodeId: name}, adimlar: [{a, b, tur, ileri (forward), aciklama}]}` shortest bond path (≤6 hops). 400 on bad format. | | Network view, entity drawer ("how are these connected") |
| GET `/api/favorites` | GET `/api/favoriler` | — | Favourite entities (light rows). | | Records drawer, palette |

### 2.8 Foreign gods

| Proposed | Old | Input | Output / effect | Used by |
|---|---|---|---|---|
| GET `/api/foreign-gods/{id}` | GET `/api/yabanci/:id` | — | Full row (`ad, unvan, alanlar (domains, "A/B"), dunya_id, guc (power 0–100), inanc, tutum (attitude −100..100), durum ('uyanik' awake/'uykuda' asleep/'yenik' defeated/'olu' dead), temas (contact flag), aciklama, gorsel_prompt, olusturma_cag, yenilgi_cag, statlar (9 god stats), kisilik {gorunus, mizac, takinti, korku, uslup, sir}, gucler [{ad, etki, aciklama}], varolus {doga, hal, tezahur, gercek_ad}, derinlik {tarih, istek, panteona_bakis, tapinma, gizli_gercek, adlari[], sirlar[], soylentiler[], sozler[], cag}, uyanis_baski, olum_cag, uyanis_ortalama`) + `dunya {id, ad, tur}`, `tapanlar` (worshipping entities `[{id, ad, tur, alt_tur, durum, nufus, murit, neden, cag, kapak}]`), `baglar` (link list), `kronik` (≤80 chronicle lines mentioning the name as a whole word), `ogullar` (sons on that world or mentioned: `{id, ad, nadirlik, durum, burada, kronikte, kapak}`), `gorseller`. 404. | Foreign-god drawer |
| POST `/api/foreign-gods` | POST `/api/yabanci` | `{dunya_id, ad (required), tutum?, …other fields}` | Creates; returns row; then (if LLM enabled) fires background deepening. Ledger `yabanci:ekle` | Cosmos |
| PATCH `/api/foreign-gods/{id}` | POST `/api/yabanci/:id/duzenle` | `{ad?, unvan?, alanlar?, aciklama?, gorsel_prompt?, tutum?, guc?, durum?, temas?, statlar?, kisilik?, varolus?, gucler?, derinlik?}` | Validated edit (names unique across the cosmos; power effects must be from `YT_GUC_ETKILERI`; existence state from `VAROLUS_HALLERI`). Ledger `yabanci:duzenle` | Foreign-god drawer, Cosmos, image-prompt editor |
| POST `/api/foreign-gods/{id}/deepen` | POST `/api/yabanci/:id/derinlestir` | — | Async job `y<id>:derin`, emits `yabanci_derinlesti {id, ad}` | Foreign-god drawer |
| POST `/api/foreign-gods/{id}/drain` | POST `/api/yabanci/:id/oz-em` | — | Ledger `oz_em:yabanci` | Foreign-god drawer |
| POST `/api/foreign-gods/{id}/kill` | POST `/api/yabanci/:id/oldur` | `{sebep?, yut?: bool}` | Kill or devour. Ledger `oldur:yabanci`/`yut:yabanci` | Foreign-god drawer |

### 2.9 Cosmos (worlds, stars, routes, voyages, cosmic acts)

#### GET `/api/cosmos` — old `GET /api/kozmos`
- Output: `{ufuk (horizon/discovery summary = GET /api/kesif), yildizlar (stars: [{id, ad, tur (e.g. 'sarı cüce' yellow dwarf), parlaklik (brightness), x, y, aciklama, gorsel_prompt, olusturma_cag}]), dunyalar (worlds: full rows + tur_ad, sayi {bolge, halk, yerlesim, canli, nufus, dis}, ogullar[] (sons present)), yabanci_tanrilar (full rows + kapak), rotalar (routes: [{id, a_dunya, b_dunya, yontem (method key), sure (duration), tehlike (danger), bilinen (known), kontrol_id, arac_id, kuran_ogul, aciklama, olusturma_cag, aktif, gecici_son, kapali_son, unutma_kapatti, acik (open), durum, neden, acilis_cag, kapanis_cag, hizada, gizli (hidden), yontem_ad, a_ad, b_ad, kontrol_ad}]), gok_takvimi (sky calendar {cag, donem (period), hizada (aligned), sapan_acik, dongu_hizada, dizilim_son, sonraki_hiza (next alignment), acilis_cag, kapanis_cag, metin}), yolculuklar (voyages: [{id, yolcu_id, rota_id, arac_id, hedef_dunya, niyet, nufus, kalan, durum ('yolda'|'vardi'|…), olaylar[], baslangic_cag, sonuc_id, yolcu_ad, hedef_ad, arac_ad}]), turler (world types: {key: {ad, palet: [10 hex colours]}}), bolgeler (all regions/places `[{id, ad, tur, dunya_id}]`), topluluklar (communities `[{id, ad, tur, dunya_id, nufus}]`), sefer_hedef (great-expedition availability: {olu_yildiz, muhurlu_kapi, arsiv, dis_kov}: bool)}`.
- Used by: Cosmos view (2D/3D).

#### GET `/api/discovery-summary` — old `GET /api/kesif`
`{dunyalar: [{id, ad, dunya_id, bolge, yer, topluluk, oran, dar (crowded), kalabalik[], bulunan[]}], son (recent discoveries [{cag, metin, varlik_ids}]), sezgiler (sensed unknown worlds), kural: {cag_tavan, taban_sans, rota_sans, dar_topluluk}}`. Not called by the UI directly (embedded in `/api/kozmos` as `ufuk`).

#### GET `/api/worlds/{id}/guide` — old `GET /api/dunyalar/:id/rehber`
Traveller's guide: `{dunya: {id, ad, tur, tur_ad, aciklama, kozmoloji, lehce (dialect), yildiz {ad, tur}, ana (parent), fizik {zaman, atmosfer, yercekimi}, sizinti, kesif}, iklim, tehlikeler [{id, ad, neden, tur}], halklar [{id, ad, tur, nufus, dil, tanri}], kaynaklar [{id, ad, aciklama, mekanik[], ozgun}], rotalar [{id, hedef, yontem, sure, tehlike, aktif, acik, durum, neden, acilis_cag, kapanis_cag}], yabanci_tanrilar [{id, ad, unvan, durum, tutum}], gok [{id, ad, alt_tur}]}`. Used by: guide drawer (`views/rehber.js`).

#### World / star / route / voyage actions

| Proposed | Old | Body | Cost | Effect | Ledger |
|---|---|---|---|---|---|
| PATCH `/api/worlds/{id}` | POST `/api/dunyalar/:id/duzenle` | `{ad?, kozmoloji?, lehce?, aciklama?, gorsel_prompt?, tur? (world type; resets terrain), yercekimi? ('düşük'|'olağan'|'yüksek' low/normal/high), atmosfer? ('yok'|'ince'|'olağan'|'yoğun'|'zehirli' none/thin/normal/dense/toxic), zaman_katsayi? (>0, no upper bound), sizinti? 0–100, olumlu_ajan? (null/'otomatik' or 0..TANRI_ELI.olumlu_ajan_tavan), koruyucu_ogul? (guardian son), ayna_ikiz? (mirror twin world), kesif? ('bilinen' known/'efsane' legend/'bilinmeyen' unknown/'unutulmus' forgotten; world 1 can't be forgotten), yildiz_id? / ana_id? (re-orbit: around a star or as a moon; cycles rejected; moons move along)}` | | Returns world + notes. | `dunya:duzenle` |
| POST `/api/worlds/{id}/wrath` | POST `/api/dunyalar/:id/gazap` | `{tur: disasterKey}` | `TANRI_GUC.dunya_gazap` | Disaster strikes every region of the world. | `gazap:dunya` |
| POST `/api/worlds/{id}/discovery-round` | POST `/api/kesif/tur` | `{dunya_id}` | | Roll discovery dice now; `{bulunan: [...]}` | `kesif_turu` |
| PATCH `/api/stars/{id}` | POST `/api/yildizlar/:id/duzenle` | `{ad?, tur?, aciklama?, gorsel_prompt?, parlaklik? 0–100, x?, y?}` | | | `yildiz:duzenle` |
| DELETE `/api/stars/{id}` | POST `/api/yildizlar/:id/sil` | — | | Refused while planets orbit it (message names them). | `yildiz:sil` |
| POST `/api/routes` | POST `/api/kozmik/rota` | `{a, b (world ids), yontem (route method key)}` | | Open a route. Methods: `kapi` gate, `katlama` fold, `yelken` sail, `binek` mount, `ruya` dream, `olu_nehri` river of the dead, `kopru` bridge, `sapan` slingshot, `yutulma` swallowing. | `rota:kur` |
| POST `/api/routes/{id}/{sever|restore|reveal}` | POST `/api/rotalar/:id/(kopar|dik|aciga)` | `{sure? (epochs, for sever)}` | `OTESI.kopar_bedel`, `OTESI.dik_bedel`, `SEYAHAT.aciga_bedel` | Sever temporarily, re-stitch, reveal hidden route. | `yol:<e>` |
| POST `/api/voyages/{id}/recall` | POST `/api/yolculuklar/:id/geri` | — | | Recall an ongoing voyage. | `sefer:geri` |
| PUT `/api/climate` | POST `/api/kozmik/iklim` | `{evre: 'ilik'|'kurak'|'yagmur'|'buzul'|'sicak' (mild/drought/rain/glacial/hot), cag_sayisi (1..TANRI_ELI.iklim_cag_tavan), dunya_id? (all worlds if omitted)}` | | Sets climate era. | `iklim` |
| PUT `/api/cosmic-resource` | POST `/api/kozmik/kaynak` | `{ad (required), aciklama?, kural?, yan_etki?}` | | Define the cosmos's travel resource. | `kozmik:kaynak` |
| POST `/api/cosmic-resource/deposits` | POST `/api/kozmik/yatak` | `{bolge_id}` | | Open a deposit of the cosmic resource in a region/place (creates a resource entity). Requires defined resource. | `kozmik:yatak` |
| POST `/api/cosmic/{action}` | POST `/api/kozmik/(yildiz|muhur|temizle|unut|gok|tutustur|ruh|sefer)` | see below | `KOZMIK_BEDEL.<action>`: yildiz 80, muhur 30, temizle 80, unut 20, gok 50, tutustur 60, ruh 15, sefer 30 | | `kozmik:<action>` |

Cosmic action bodies:
- `yildiz` (hang a star): `{ad? (auto-named from a living language if empty; else "<World>'s Nth Star"), tur? (default 'sarı cüce'), aciklama?, dunya_id?}`.
- `muhur` (seal a gate): `{rota_id}`.
- `temizle` (stitch a leak): `{dunya_id}`; refused (no cost) if leak 0 and nothing from outside is inside.
- `unut` (forget a world into the mist): `{dunya_id}`.
- `gok` (sky event): `{olay: 'tutulma' eclipse|'kuyruklu' comet|'dizilim' alignment|'supernova'|'kara_gunes' black sun|'firtina' storm, dunya_id? | yildiz_id? | rota_id? (storm), sure?}` — at least one target required.
- `tutustur` (rekindle a dead star): `{yildiz_id}` (only `ölü yıldız`/`kara güneş`/`yıldız kalıntısı`).
- `ruh` (spirit possession): `{ruh_id, hedef_id}`.
- `sefer` (great expedition): `{tur: 'olu_yildiz'|'muhurlu_kapi'|'arsiv'|'dis_kov'}` → returns `{iplik_id}` (opens a story thread).

### 2.10 Map

#### GET `/api/worlds/{id}/map?epoch=` — old `GET /api/harita?dunya=&cag=`
- 409 "Create the world first." if no world.
- Output: `{seed, dunya (world row with parsed arazi {deniz, daglik, nem}), varliklar (map entities: `[{id, ad, tur, alt_tur, konum_id, guc_seviyesi, statlar, harita_xy, yaratan_id, kaynak, durum, dunya_id, xy:[x,y], kapak}]`), bilgi (per-region geography `{regionId: {komsular (neighbours), kiyi (coastal), yukseklik ('su' water|'ova' plain|'engebeli' hilly|'dağlık' mountainous), buyukluk (size), iklim (biome mix strings like "forest 57%")}}`), kapsam (viewport extent {x, y, w, h, oran, hucre}), rotalar (entity trade/enemy/rule/hunt links `[{a, b, tur, aciklama}]`), yildiz (epoch star id), bolgeDin (region → dominant worshipped son id, weighted by log10 population), bolgeDil (region → dominant language id), diller [{id, ad}], siyasi (political map {regionId: {hakim_id, hakim_ad, tur, pay (share %), cekisen (contested count)}}), yollar (road network [{a, b, tur, uzunluk}]), notlar (map notes), zaman {simdi (current epoch), gosterilen (shown epoch), fotograflar (epochs with snapshots)}, kademeler (settlement tiers {id: {kademe ('baskent' capital, …), ad, nufus, onceki_nufus}}), isaretler (event markers [{id, ad, tur, alt_tur, konum_id, cag}]), savaslar (wars/battles/sieges [{id, ad, konum_id, cag, suruyor (ongoing)}])}`.
- Historical view (`cag < current`): entities born after that epoch are removed; entities not alive in that epoch's snapshot are hidden (regions always kept); status/population taken from the snapshot; political map from the snapshot.
- Used by: Map view; records drawer (map notes).

| Proposed | Old | Body | Effect |
|---|---|---|---|
| PUT `/api/entities/{id}/map-position` | POST `/api/harita/konum` | `{id, x, y}` | Store rounded `[x,y]`; invalidates map cache. Ledger `harita:konum`. |
| POST `/api/map-notes` | POST `/api/harita/not` | `{x, y, metin (≤400), renk (colour key, default 'altin' gold), dunya_id}` | Returns note row. |
| DELETE `/api/map-notes/{id}` | POST `/api/harita/not/:id/sil` | — | 404 if missing. |

### 2.11 Chronicle, threads, perspectives

| Proposed | Old | Input | Output | Used by |
|---|---|---|---|---|
| GET `/api/chronicle` | GET `/api/kronik` | `cag?` (epoch), `once?` (before id, cursor), `limit?` (1..`kronik_sayfa_tavan` 500), `sayfa=1` (envelope) | Rows `{id, cag, yil, ogul_id, tur (line type), metin, varlik_ids[], olusturma}` ascending. No params → last `kronik_son` (600). `cag` only → that whole epoch. With `once`/`limit` → page of `kronik_sayfa` (200) newest-first then reversed. Envelope (`sayfa=1`): `{kayitlar, toplam, daha_var (has more), en_eski (oldest id)}`; else headers `x-toplam`, `x-daha-var`. | Chronicle (per epoch, lazily) |
| GET `/api/chronicle/epochs` | GET `/api/kronik/caglar` | — | `[{cag, ad, n (line count)}]` | Chronicle sidebar |
| GET `/api/chronicle/perspectives` | GET `/api/bakislar` | `cag?` | People-written partisan histories `[{id, cag, halk_id, tarihci (historian), metin, halk_ad}]` | Chronicle |
| GET `/api/chronicle/cosmic` | GET `/api/kozmik-kronik` | `son?` (1..200, default 30) | `[{cag, ad, ozet, dunyalar: [{dunya_id, ad, olay_sayisi, basliklar[], ozet, anlati}]}]` | Chronicle (cosmic tab) |
| GET `/api/threads` | GET `/api/iplikler` | — | `[{id, cag, metin, ilgili: [{id, ad}], durum ('acik' open/'kapali' closed), kapanis, kapanis_cag, buyuk (great expedition key), ilerleme (progress)}]` ordered by status then newest | Chronicle, goals panel, refresh loop |
| POST `/api/threads` | POST `/api/iplikler` | `{metin, ilgili?: int[]}` | Opens a thread. Ledger `iplik:ac` | Goals panel |
| POST `/api/threads/{id}/close` | POST `/api/iplikler/:id/kapat` | `{nasil (how)?: string}` | Ledger `iplik:kapat` | Pantheon |
| GET `/api/codex.md` | GET `/api/kodeks.md` | — | Whole world as one Markdown file (`content-disposition: attachment; filename="<world>-kodeks.md"`) | Footer, settings, chronicle, guide |
| GET `/book?son=&entity=` | GET `/kitap?ogul=&varlik=` | ints | Self-contained printable HTML encyclopaedia (or one article). Served with a strict CSP (`script-src 'nonce-…'; connect-src 'none'`). 404 if article missing. | Header book button, drawers ("print") |

### 2.12 Prayers, councils, messages

| Proposed | Old | Input | Output / effect | Used by |
|---|---|---|---|---|
| GET `/api/prayers` | GET `/api/dualar` | — | Up to 100 son prayers + up to 100 mortal prayers to the creator (excluding chat), merged, unanswered first then newest: `[{id, cag, kimden_tip ('o'|'v'), kimden_id, kime_tip:'t', niyet ('dua' prayer, …), metin, istek (request kind e.g. 'kutsama' blessing), okundu, cevaplandi, olusturma, kimden_ad, kimden_tur?}]` | Prayers tab |
| POST `/api/prayers/{id}/answer` | POST `/api/dualar/:id/cevap` | `{metin?: string, oz?: int (0..TANRI_EYLEM.dua_oz_tavan)}` | Son prayer: gifted essence goes to the son (≤ max), loyalty + existence up, reply message stored; mortal prayer: answer descends as a dream, grace + faith. Already answered → 400. Ledger `dua`. Returns son or `{varlik}`. | Prayers tab |
| GET `/api/councils` | GET `/api/konseyler` | — | Last 30: `[{id, cag, konu, tutanak: {konu, cagiran ('tanri'|son), konusmalar [{…}], onerge (motion), oylar [{…}], kabul, karar, notlar[], tutanak (minutes prose)}, kabul, olusturma}]` | Goals panel |

### 2.13 Network (knowledge graph)

| Proposed | Old | Output / effect | Used by |
|---|---|---|---|
| GET `/api/graph` | GET `/api/graf` | `{nodes, links}`. Nodes: sons `{id:'o<id>', ad, tur:'ogul', nadirlik, g (size = 4 + raritySira×2), cag (birth epoch), durum}`; visible entities `{id:'v<id>', ad, tur, g (2 + power_level), durum, yaratan, konum, cag}`; creator `{id:'t1', ad, tur:'tanri', g (mythic size), cag:0, durum:'aktif'}`; foreign gods `{id:'y<id>', ad, tur:'yabanci', g (legendary size), cag:0, durum}`. Links: all visible bonds whose both ends exist: `{source, target, tur, cag, gecmis?:1}`. **Unpaginated** (≈3.6k nodes / 19k links in a mature world). | Network 2D/3D |
| GET `/api/graph/health` | GET `/api/ag/saglik` | `{dugum (nodes), bag (links), gecmis_bag, etkin_bag, ortalama_derece, medyan_derece, yogunluk (density), bilesen (components), en_buyuk_bilesen, en_buyuk_pay (%), yalitik (isolated), tek_bagli (degree-1), zayif_sayi, ilgili (vague 'related' links), ilgili_aciklamasiz, zayif: [{id, ad, tur, derece}] (weakest 20), gunluk: [{zaman, tur, metin, baglar}] (repair log), oncelikli (priority queue size)}` | Network health panel |
| POST `/api/graph/repair` | POST `/api/ag/onar` | Rule-based repair of dangling ends (location, impact site, events, narratives, prophecy, remains, destruction, maker; converts vague links to concrete types). Returns counts; emits `ag_onarim`. Ledger `ag_onar`. | Network |
| POST `/api/graph/fate-link` | POST `/api/ag/kader` | Body `{ilgili?: bool=true, tam?: bool}`. Async parallel job `ag:kader`: Fate proposes justified links for priority records (events, legends, traditions mentioned in chronicle but unlinked) then weakest; then renames vague links. `tam` = run until everything is done. Emits progress `sistem` lines. | Network |
| POST `/api/graph/fate-link/stop` | POST `/api/ag/kader/durdur` | `{durduruluyor:true}` | Network |

### 2.14 Languages and knowledge

| Proposed | Old | Output | Used by |
|---|---|---|---|
| GET `/api/languages` | GET `/api/sozluk` | `[{id, ad, alt_tur, aciklama, kapak, konusanlar: [{id, ad, tur}], kelimeler: [{id, dil_id, kelime (word), anlam (meaning), tur (part of speech), koken (etymology), ornek, ekleyen_tip, ekleyen_id, cag, olusturma, ekleyen_ad}] (≤ `sozluk_kelime` 2000 per language)}]` | Languages tab |
| GET `/api/languages/tree` | GET `/api/dil-agaci` | `{diller: [{id, ad, alt_tur, yazi (script type), kelime (word count), konusan (speaker count), ust_id (parent language), ornek_adlar (3 sample generated names)}], akrabalik (kinship): [{a, b, ortak: [cognates]}], yazi_turleri (script types: alfabe alphabet, hece syllabary, resim pictographic, dugum knot-writing, oyma carved)}` | Languages tab (family tree) |
| POST `/api/languages/{id}/translate` | POST `/api/cevir` | Body `{dil_id, metin}`. Synchronous LLM translation into the conlang using its dictionary & phonology; may add words to the dictionary. | Languages tab |
| GET `/api/knowledge` | GET `/api/bilgiler` | Canon technologies: `[{id, ad, aciklama, dal (branch), seviye (level), yayginlik (spread), cag, temeller (prerequisites [{id, ad}]), bilenler (knowers [{id, ad, gecmis?}]), yapan (inventor name)}]` | Languages tab (knowledge tree) |

### 2.15 Images

| Proposed | Old | Input | Output / effect | Used by |
|---|---|---|---|---|
| GET `/media/{file}?w=` | GET `/gorsel/:file?w=64|160|320|640` | file name `^[\w-][\w.-]*$` | Original or cached thumbnail (old: macOS `sips -Z w`, ≤3 concurrent (`kucuk_esz`), 30 s timeout; GIF/SVG never resized; on failure falls back to the original). Headers: `cache-control: public, max-age=31536000, immutable`, `nosniff`. HEAD supported. 400 bad name / bad width. New app: use Pillow. | Everywhere (`core/bilesen.js` img helper, 3D textures) |
| GET `/api/images?type=&id=` | GET `/api/gorseller?tip=&id=` | optional target | `[{id, hedef_tip, hedef_id, dosya, mime, baslik (caption), kapak (is cover), boyut, olusturma, hedef_ad, hedef_tur, hedef_dunya?}]` (cover first, newest first); without params all images newest first. | Gallery, lightbox |
| POST `/api/images?type=&id=&caption=` | POST `/api/gorsel?tip=&id=&baslik=` | raw bytes, `Content-Type` image/png|jpeg|webp|gif|avif, ≤30 MB | Magic-byte check (content must match declared type), stored as `<tip><id>-<ms>-<6hex>.<ext>`, copied into a backup pool; first image of a target becomes cover; caption accepted only if it is not just a file name (`baslikGecerli`). Returns image row. | Upload control in every drawer |
| PUT `/api/images/{id}/cover` | POST `/api/gorseller/:id/kapak` | — | Make cover (unset others). Ledger `gorsel:kapak` | Lightbox/drawer gallery |
| PUT `/api/images/{id}/caption` | POST `/api/gorseller/:id/baslik` | `{baslik}` (≤120) | Ledger `gorsel:baslik` | Lightbox |
| DELETE `/api/images/{id}` | POST `/api/gorseller/:id/sil` | — | Removes row, keeps a copy in backup pool, deletes file + thumbnails; promotes newest remaining as cover. | Lightbox |
| GET `/api/gallery/missing?limit=&type=` | GET `/api/galeri/eksik` | limit 1..500 (default 40) | Important records without an image `[{t:'v', id, ad, tur, alt_tur, durum, dunya_id, gorsel_prompt, cag, onem, arsiv}]` | Gallery "missing images" |
| GET `/api/image-gen` | GET `/api/gorsel-uret` | — | Local image-generation status (state.image_gen) + `gunluk` (log) + `eksik` (missing count). | Image-generation panel |
| POST `/api/image-gen` | POST `/api/gorsel-uret` | `{tip ∈ HEDEF_TIPLERI, id}` | Async: generate one image with the local model. 423 in discovery mode; 404 target missing. | Drawers ("Generate image") |
| POST `/api/image-gen/batch/start` · `/stop` | POST `/api/gorsel-uret/toplu/baslat` · `durdur` | — | Start/stop batch generation over missing images; 409 with message on conflict. | Settings |

### 2.16 Batch deepening

| Proposed | Old | Output | Used by |
|---|---|---|---|
| GET `/api/batch-deepen` | GET `/api/toplu/derin` | `{calisiyor, durdur, toplam, bitti, hata, atlandi, suan[], basla, bitis, kalan, gunluk[], bekleyen (records awaiting depth), adsiz (nameless)}` | Settings → batch |
| POST `/api/batch-deepen/start` · `/stop` | POST `/api/toplu/derin/baslat` · `durdur` | status; 409 on conflict; 423 in discovery | Settings → batch |

### 2.17 Notifications

| Proposed | Old | Input | Output | Used by |
|---|---|---|---|---|
| GET `/api/notifications` | GET `/api/bildirimler` | `okunmamis=1` (unread only), `kategori`, `limit` (1..500, default 60), `once` (cursor id) | `{okunmamis (unread count), sayilar: [{kategori, n, okunmamis}], ayar (per-category enabled map), kategoriler: {key: {ad, onem (1–4 severity), varsayilan}}, liste: [{id, cag, kategori, onem, baslik, metin, hedef_tip, hedef_id, kronik_id, okundu, zaman, ad (category label)}]}` | Notifications drawer, records drawer (`kategori=not`) |
| POST `/api/notifications/read` | POST `/api/bildirimler/oku` | `{ids?: int[], hepsi?: bool, kategori?, okunmadi?: bool (mark unread)}` | status | Notifications drawer |
| PUT `/api/notifications/settings` | POST `/api/bildirimler/ayar` | `{<category>: bool, …}` | `{tamam, ayar}` | Notifications drawer |
| POST `/api/notifications` | POST `/api/bildirimler` | `{baslik (required), metin?, hedef_tip?, hedef_id?}` | `{id}` — a personal note stored as category `not`, forced even if disabled. | Notifications/records |

Categories: `isyan` son rebellion (sev 3), `olum` death (3), `dogum` legendary birth (3), `kehanet` prophecy fulfilled (3), `kiyamet` doom omen (4), `korku` cosmic horror (3), `savas` war (2), `dua` prayer to you (2), `kozmos` cosmic event (2), `yukselis` ascension (2), `afet` disaster & sky (2, off by default), `cag` epoch ended (1), `basarim` achievement (2), `toplum` society/lineage (2), `itibar` standing in sons' eyes (2), `hata` system error (3), `not` creator's note (1).

### 2.18 Ledger of Fate (undo)

| Proposed | Old | Input | Output |
|---|---|---|---|
| GET `/api/ledger` | GET `/api/defter` | `cag?`, `kim_tip?` (`t` creator / `o` son / `v` entity), `kim_id?`, `limit` (1..300, default 80) | `{cag, caglar: [{cag, n, geri (undone count)}], kayitlar: [{id, cag, kim_tip, kim_id, kim_ad, arac (tool), ozet (summary), zaman, geri_alindi (undone), sonuc, degisiklik (change count), satirlar: [{…row diffs}], bagimli: [ids of later pages depending on this one]}]}` |
| POST `/api/ledger/{id}/undo` | POST `/api/defter/:id/geri-al` | — | Reverts the page's row writes. 409 "A page can't be torn from the ledger while an epoch runs." |

Used by: Ledger drawer (`views/defter.js`), son drawer (son's pages), global undo shortcut (`core/yenile.js` fetches the creator's last page and undoes it).

### 2.19 Goals, scenarios, opportunities

| Proposed | Old | Output / input | Used by |
|---|---|---|---|
| GET `/api/goals` | GET `/api/hedefler` | `GoalsOverview {epoch, categories[{category, label}], metrics[{metric, category, label, value, lower_is_better}], scenarios[{key, category, name, description, points, next_tier, default_target, target_max, history[{id, status, name, tier, target, start_epoch, end_epoch, deadline_epoch, points, awarded_points, result}]}], running[{id, key, name, description, tier, target, start_epoch, deadline_epoch, held, hold_epochs, points, metric, comparator, basis, title, progress{percent, text, value, done, failed}}], achievements[{key, category, metric, title, value, tier, percent, tiers[{tier, name, description, threshold, points, epoch}]}], score{parts{population, diversity, languages, worlds, civilization, life, faith, culture, knowledge, wonders, scales, exploration, doomsday, achievements, scenarios}}, score_history[[epoch, total]]}` | Goals panel |
| GET `/api/goals/quote` | — | query `key, target?, deadline_epochs?, metric?, comparator, basis, hold_epochs` → `GoalQuote {name, description, target, start_value, points}`: the worth a start would fix | Goal dialogs, custom goal form |
| POST `/api/scenarios` | POST `/api/senaryolar` | `{key, target?, deadline_epochs?}` → action outcome; chronicle "X set a goal: …". Ledger `scenario:start` | Goal board |
| POST `/api/scenarios/custom` | — | `{metric, comparator, basis, target, hold_epochs, deadline_epochs?, title?}` → action outcome. Ledger `scenario:custom` | Custom goal form |
| POST `/api/scenarios/{id}/edit` | — | `{target, deadline_epochs?, hold_epochs, title?}`; the worth is weighed again. Ledger `scenario:edit` | Running goals |
| POST `/api/scenarios/{id}/hold` | — | `{held}`; a held goal is not measured and its deadline waits. Ledger `scenario:hold` | Running goals |
| POST `/api/scenarios/{id}/abandon` | POST `/api/senaryolar/:id/birak` | → action outcome. Ledger `scenario:abandon` | Running goals |
| POST `/api/scenarios/{id}/delete` | — | strikes the record and its awarded points. Ledger `scenario:delete` | Record of goals |
| GET `/api/opportunities` | GET `/api/firsatlar` | `{genel: string[] (hints: unanswered prayers, spendable essence, sons yet to act, sons without orders, sleeping sons with epochs left, resurrectable sons, open threads, records without image, unread notifications, half-finished epoch, creator-specific opportunities), ogullar: {sonId: string[]} (per-son opportunity hints from the agent context builder)}` | Goals panel |

### 2.20 Rules, settings, models

| Proposed | Old | Input | Output |
|---|---|---|---|
| GET `/api/rules` | GET `/api/denge` | — | Flat list of every tunable: `[{yol (key path e.g. "COSTS.cagirma"), ad (label), grup (group label), min, max, deger (value), varsayilan (default), degisti (changed)}]` (≈3,300 rows). |
| PATCH `/api/rules` | POST `/api/denge` | `{degisiklikler: {path: number|null (null = reset to default)}, sifirla?: bool (reset all first)}` | Validates: unknown key → 400; must be a finite integer; **min is enforced, max is only advisory** (UI warns); values equal to default are deleted from overrides. Persists to `dunya.denge_ayar` and applies immediately. Returns the new list. |
| PATCH `/api/settings` | POST `/api/ayar` | `{kader_modu?: 'otomatik'|'kapali' (Fate on/off), olumlu_sayisi?: int≥0 (mortal agents per epoch), ogul_dagitim?: 'otomatik'|'elle' (son distribution across worlds), konsey_sikligi?: int≥0 (council every N epochs, 0 = never), olumlu_paralel?: int≥1 (mortal turns in parallel), modeller?: {role: 'haiku'|'sonnet'|'opus'}}` | `{dunya, modeller}`. 409 if no world. |

The static rule catalogue (enums used to build forms) is delivered inside `GET /api/state` → `kurallar` (§3.6). New app: expose it as `GET /api/catalogue` (cacheable, versioned).

### 2.21 Backups, import/export, discovery mode, reset, cheats

| Proposed | Old | Input | Output / effect |
|---|---|---|---|
| GET `/api/backups` | GET `/api/yedekler` | — | `[{dosya (file), boyut (size), tarih (ISO mtime)}]` newest first. Kinds by file name: `cag<N>` (auto per epoch; pruned except every `onluk`th), `elle` (manual), safety kinds (`sifirlama-oncesi`, restore-safety, import-safety…). |
| POST `/api/backups` | POST `/api/yedek` | — | `{dosya}` manual backup. |
| POST `/api/backups/restore` | POST `/api/yedek/geri` | `{dosya, onay: 'GERİ YÜKLE'}` → new confirm `RESTORE` | 409 if any job runs (message names which: epoch/jobs, batch deepening, image generation — each with where to stop it). Takes a safety backup, restores, then "world changed" routine (§2.22). `{tamam, guvenlik (safety backup name)}`. |
| GET `/backups/{file}.db` | GET `/yedek/:file.db` | | Raw SQLite download (`application/vnd.sqlite3`). |
| GET `/backups/{name}.aerona` | GET `/yedek/:name.aerona` | | That backup packaged as a world package (with images). 404 if missing. |
| GET `/api/world/export?images=0|1` | GET `/api/dunya/disa-aktar?gorseller=0` | | Streams a `.aerona` package: gzip of JSON `{bicim (format id), surum (format version), ad, cag, tanri, tarih, db: base64(VACUUMed SQLite, telemetry stripped), gorseller: {fileName: base64}}`. File name `<world>-cag<N>.aerona`. |
| POST `/api/world/import?mode=replace|discovery&confirm=` | POST `/api/dunya/ice-aktar?mod=degistir|kesif&onay=DEĞİŞTİR` | raw package bytes ≤400 MB (decompressed size capped; "compression bomb" error) | Validates format, version (newer → refuse), `quick_check`, required tables; strips triggers/views and unsafe image names. `replace` requires confirm (`DEĞİŞTİR` → `REPLACE`); old world kept as a safety backup. `discovery` opens the guest world read-only and parks your own world. 409 if jobs run. Returns `{dunya: {ad, cag, …}, guvenlik?}` and runs §2.22 with a message. |
| POST `/api/discovery/end` | POST `/api/kesif/bitir` | — | Returns to your own world; deletes guest images not used by your world. `{tamam, misafir}`. Client reloads the page. |
| POST `/api/world/reset` | POST `/api/sifirla` | `{onay: 'SIFIRLA'}` → `RESET` | 409 if jobs run. Safety backup `sifirlama-oncesi`, wipes DB, moves image files to the backup pool, §2.22 "World deleted; its previous state is in the safety backup." `{tamam, guvenlik}`. |
| POST `/api/cheats/essence` | POST `/api/hile/oz` | `{miktar: 1..SUNUCU.hile_oz_tavan (1,000,000)}` | Adds creator essence. Ledger `hile:oz`. `{tanri_oz}`. |

#### 2.22 "World changed" routine (`dunyaDegisti`)
After import/restore/reset/discovery-end: invalidate map cache, clear the event ring buffer, rebuild suffix dictionary (LANGUAGE-SPECIFIC), re-apply rules overrides, reset the change-feed epoch (forces clients to full refresh), kick off one-off data repairs, emit `sistem {metin}` and `serbest`.

### 2.23 Model metrics

GET `/api/metrics/models?epochs=` — old `GET /api/olcum?cag=` (1..50, default 10):
`{toplam: {cagri (calls), ms, maliyet (USD cost), girdi (input tokens), cikti (output tokens)}, caglar: [{cag, cagri, ms, girdi, cikti, maliyet, hata, yeniden (retries), yavas (slow)}], modeller: [{model, cagri, ms, ort_ms, girdi, cikti, maliyet}], adimlar (by step name, e.g. "Deepening"): [{adim, cagri, ort_ms, en_uzun_ms, maliyet, hata}], yavaslar (slowest calls [{id, cag, ad, model, ms, durum, deneme, zaman}]), son_hatalar [{id, cag, ad, model, ms, hata, zaman}], yavas_esik_ms (slow threshold)}`. Used by: model-metrics panel (`views/olcum.js`), live feed, batch panel.

### 2.24 Static files

`GET /` → `index.html`; any other path → file under `public/` (`..` rejected; `cache-control: no-cache`). Unknown `/api/*` or `/yedek/*` → 404 JSON. `/stil.html` is a living style guide page; `/kozmos3d-test.html` a 3D test harness.

### 2.25 Server start-up side effects (not endpoints, but the integrator must reproduce them)

On listen: apply one-time balance migration; unless read-only: compute missing importance scores, prune model metrics, refresh SQLite planner stats, one-time text repair (`veri_surum < 2`), age-consistency fix for mortals, data repairs (`veriOnarimi`), requeue half-finished "intuitions", pair mirror worlds, scrub identity leaks from narratives, write endings for dead records' descriptions, repair dangling graph ends, clear captions that are just file names, write canon facts if none exist, connect every world's travel graph; then, if LLM enabled and `AERONA_TAMAMLA != 0`, after `SUNUCU.tamamla_gecikme` (1500 ms) run auto-completion of missing content (`tamamla`). On every `cag_bitti` event: recompute importance, prune metrics, WAL checkpoint.

Env vars: `PORT`, `AERONA_DB` (DB path; images/backups/logs live next to it), `AERONA_LLM_YOK=1` (no LLM), `AERONA_TAMAMLA=0` (no auto-complete).

---

## 3. Shared response objects

### 3.1 SonPublic (`sonPublic`)
All son columns (parsed) plus:
- Core: `id, ad (name), unvan (title), nadirlik (rarity key: yaygin common, seckin uncommon/"distinguished", nadir rare, destansi epic, efsanevi legendary, mitik mythic), alan1, alan2 (two domains from rules.ALANLAR), kisilik {gorunus appearance, mizac temperament, takinti obsession, korku fear, uslup speech style, sir secret}, statlar {guc strength, dayaniklilik endurance, ceviklik agility, bilgelik wisdom, kurnazlik cunning, irade will, yaraticilik creativity, karizma charisma, kudret might} (1–100), tutku (passions) {sadakat loyalty, hirs ambition, ofke anger, merhamet mercy} (0–100), can (hp), oz (essence), inanc (faith), un (renown), xp, seviye (level), durum ('aktif' active|'uykuda' asleep|'surgun' exiled|'olu' dead), uyku_kalan (sleep epochs left), zincirli (chained), emir (standing order), son_eylem_cag, ebeveyn_id (parent son), dogum_cag, gorsel_prompt, gucler (powers [{ad, aciklama, etki (effect key), param}]), yildiz (★1–5), varolus (existence {doga nature, hal state, tezahur manifestation, gercek_ad true name}), varlik (existence strength 0–100), capa_id (anchor entity), plan (agent's plan text), destan (epic {baslik, destan, dize, cag}), asi (rebel flag), tur_cag, olum_cag, ceset_id (corpse entity), solus, aktif_dunya (active world id), itibar (reputation {sevgi, korku, unutma, cevapsiz, son_temas, etiket, cag}), itibar_elle, emir_mutlak, …`
- Computed: `can_max, oz_max, nadirlik_ad (rarity label), model (LLM tier for this rarity), eylem (action points), guc_tavani (power cap), varlik_durumu {k, ad, etki} (existence band e.g. "Bright: +3 essence per epoch"), acik_guc (unlocked power count), kapak, kart (card summary: {son_eylem {cag, metin≤160}, son_soz (last utterance), itibar (label), dost {id, ad, deger} (best friend), hasim (worst rival)}), yildiz_sarti (next-star requirement {seviye, un, oz}|null), yukselis (ascension requirement + target rarity |null)`.

### 3.2 SonDetail (`ogulDetay`)
SonPublic plus: `dirilis` (resurrection status or null), `oldur_bedel` (kill cost), `halklarin_gozunden` (peoples' beliefs about him), `itibar` (full reputation calc + `elle`), `yaratimlar` (all his creations, newest first, with `kapak`), `kronik` (last 80 lines), `mesajlar` (last 40 messages to/from him with `kimden_ad`, `kime_ad`), `kardesler` (siblings with relation `deger` and `kapak`), `baglar` (link list, §3.4), `inanc_canli` (live faith), `tapanlar` (worshipping entities), `capa` (anchor entity), `ebeveyn {id, ad}`, `cocuklar [{id, ad}]`, `gorseller`.

### 3.3 EntityDetail (`varlikDetayJson`)
Entity row (parsed) plus:
- `sinif` (power class), `yaratan {id, ad}` (creator son), `yol` (location breadcrumb, up to 8 ancestors `[{id, ad, tur}]`).
- Mortals: `yasam` (life: `{taban, tip, onemli, etkin (effective lifespan), yas (age), zaman (world time factor), cag_yil (years per epoch), olumsuz (immortal), olum_yili}`); living mortals: `olum` (death options `{ogul_bedel (son's cost to kill), yuzde (chance %), koruyan [{tur, ad, id}] (protectors), onem, tanri_bedel}`).
- Communities & mortals (canon): `oluTanrilar` (dead sons they still worship), `kesif` (exploration pressure `{yuzde, neden[], kasif {id, ad}, yol}`).
- Importance: `onem, arsiv, arsiv_sebep, son_anma`; `ek` (LANGUAGE-SPECIFIC).
- `toplum` (society for peoples/settlements: `k` class shares %, `m` class morale, `e` economy `{erzak food, maden ore, mal goods, fiyat prices}`) — classes: ciftci farmer, zanaatkar artisan, tuccar merchant, rahip priest, savasci warrior, katip scribe.
- `benzerler` (similar records `[{id, ad, tur, alt_tur, puan, neden}]`), `bekleyen_ruya` (undelivered dreams), `gercekler` (≤30 canon facts `{ozne_ad, iliski, nesne_ad|nesne, cag}`), `inanclari` (people's beliefs about sons), `tarih_yazdiklari` (≤8 histories they wrote), `iliskiler` (≤10 inter-community relations `{id, ad, tur, deger, etiket, kan_davasi (blood feud), gecmis[]}`), `savaslar` (wars they're party to `{id, ad, suruyor, muharebe (battles), sonuc}`), `icindekiler` (contained entities), `baglar` (links), `kronik` (all chronicle lines tagged with it, ascending — can be 600+), `gorseller`, `capasi_olan` (sons anchored to it), `kapasite` (carrying capacity `{kapasite, bolge_nufus, doluluk %, bolge, paylasan}`), `yapan {id, ad}` (maker), `dil {id, ad}` (spoken language), `sozluk` (dictionary, languages only), `konusanlar` (speakers, languages only), `sahip_olunanlar` (owned items/resources), `urettikleri` (things it produced), `bildikleri` (knowledge known `{id, ad, dal, seviye}`), `bilenler` (knowers, tech only), `anildigi` (≤40 records whose text mentions it), `kronik_sayisi` (chronicle mention count), `soy {ata (ancestors ≤8), torun (descendants)}`, `dal` (knowledge branch), `yasa_mekanik` (law mechanic from tag `yasa:`).

### 3.4 Link list item (`bagListesi`)
`{id, kaynak_tip, kaynak_id, hedef_tip, hedef_id, tur, aciklama, cag, aktif, red_kapatti, gecmis (inactive), yon ('out'|'in'), diger_tip, diger_id, diger_ad, borc? (debt details for 'borclu')}` — outgoing first then incoming, active first. Visibility filter `GORUNUR_BAG` hides internal link kinds.

### 3.5 Image row
`{id, hedef_tip, hedef_id, dosya, mime, baslik, kapak (0/1), boyut (bytes), olusturma}`.

### 3.6 Rules catalogue (`state.kurallar`)
Static enums and current costs used to build every form: `OGUL_DUZEN_ALANLAR`, `ETIKETLER` (24 assignable tags), `ETIKET_ONEKLER` (`ozellik:`, `mekanik:`, `yasa:`), `BAG_TURLERI` (≈45 link types), `BAG_ETIKET` (link type → label), `YT_STATLAR / YT_GUC_ETKILERI / YT_KISILIK / YT_VAROLUS / YT_DERIN_METIN` (foreign-god editor schema), `VAROLUS_HALLERI` (somut concrete, yarı-somut semi-concrete, kavramsal conceptual, yansıma reflection, dağınık scattered), `RARITIES` (`{key: {ad, sira, ap, stat:[lo,hi], guc_tavan, oz_yenilenme, maxTurns, agirlik}}`), `SON_STATS` (9 stats `{k, ad, grup, etki}`), `TUTKULAR` (4 passions), `KAYNAKLAR` (son resources with effect text), `VARLIK_TURLERI` (25 entity types with stat schemas), `COSTS` (summon 30, bless essence 15, bless hp 15, bless stat 40, lightning 10, revelation 25, transform 15, beget child 60, destroy 25, influence 6, curse 12, dream 10, incite 10, chosen 14, covenant 0, anchor 0), `ALANLAR` (40 domains), `GUC_ETKILERI` (13 power effects), `GUC_SEVIYELERI` [1,3,5], `YILDIZ_MAX` 5, `DENGE` (core balance: essence regen, essence cap, resurrect 150, world 120, birth world 70, council 20, dream 8, awaken, doom threshold, doom speed, suppress, starting essence), `MODEL_ETIKET`, `MODELLER` [haiku, sonnet, opus], `OLUMLU_AJAN`, `OZEL` (special per-type depth fields), `BILGI_DALLARI` (18 knowledge branches), `YASA_MEKANIKLERI` (11 law mechanics), `AFETLER` (5), `MUCIZELER` (4), `MUDAHALE_BEDEL`, `SINIFLAR` (6 social classes), `IKLIM` (5 climate phases), `DIRILIS_BEDEL`, `SEYAHAT_YONTEMLERI` (9 route methods), `GOK_OLAYLARI` (6 sky events with label & description), `OZELLIKLER` (10 creature traits), `KAYNAK_MEKANIKLERI` (6 resource mechanics), `KONSEY_BEDEL`, `RUYA_BEDEL`, `KOZMIK_BEDEL`, `BUYUK_SEFERLER` (4 great expeditions), `AKIS_KATEGORILERI` (live-feed categories: yolculuk travel, kapi gate, sizinti leak, savas war, afet disaster, gok sky, hayat life, medeniyet civilization), `DUNYA_BEDEL`, `DUNYA_DOGUR_BEDEL`, `DUNYA_TURLERI` (11 world types). Values are documented in their owning module specs.

---

## 4. Realtime event stream

### 4.1 Transport (old)
`GET /api/olaylar` → `text/event-stream`. On connect the server immediately writes `data: {"kind":"merhaba","mesgul":<busy>}`. Every event published on the in-process bus (`E.bus.emit('olay', e)`, wrapped by `yayinla`) is written as `data: <json>\n\n`. A comment ping `: ping` every 20 s keeps the connection alive. There are no event ids or replay: on reconnect the client calls `/api/gunluk` (ring buffer of the last 300 events with `zaman`) and `/api/degisim` to catch up. The client (`views/akis.js`) reconnects with backoff when the stream errors.

New app: WebSocket or SSE with monotonically increasing event ids and `Last-Event-ID` replay from the ring buffer; same payloads with English names; every event carries `ts` and, when applicable, `epoch`, `world_id`, `job_id`.

### 4.2 Event kinds (complete catalogue)

Every kind found by grepping all `bus.emit('olay', …)` / `yayinla(…)` call sites. "UI rendering" describes the old live feed (see `12-frontend.md` → Live feed for the full rendering rules). The same table is reproduced in `12-frontend.md`.

All events arrive on `GET /api/olaylar` (SSE). Events emitted through `epoch.js`'s `yayinla` (and through it `agents.js` `CANLI`, `bildirim.js`) are stamped with `cag` (current age) and `zaman` (ms epoch). Events emitted directly via `E.bus.emit` in server.js, `gorsel-uret.js` and `toplu.js` carry no stamp (UI falls back to "now"). Son-turn events are wrapped by agents.js to add `ogul_id, ogul_ad`; mortal-agent turn events are wrapped by olumluler.js to add `varlik_id` and `ogul_ad` (= mortal's name, confusingly reusing the son field).

| kind | payload fields | emitted by / when | UI rendering (live feed unless stated) |
|---|---|---|---|
| `merhaba` | `mesgul` (`{tur, basla}` or null) | server.js on every SSE connect | Close dangling "writing" lines (" · connection renewed; writing was interrupted"); clear tool spinners; if busy: state "busy", start progress with title "A job is running" and `basla` as start time; show/hide Stop. |
| `mesgul` | `mesgul {tur, basla}` | epoch.js `kilitle()` when a global-lock job starts; server.js on genesis start | Store `G.S.mesgul`; progress panel on, title by `tur` (table above); state pill; Stop visibility; background refresh. No line. |
| `serbest` | — | epoch.js `kilitle()` finally; server.js after genesis and after world change (`dunyaDegisti`) | State "idle"; clear acting-son highlights; close all streaming lines; hide progress; reset ETA & stop state; clear tool spinners; background refresh. |
| `sistem` | `metin` | many: epoch.js (age stop/resume, backups, new words, deepening/epic batches, distribution, local god born, prompts, network repair results), agents.js (genesis steps, peoples awakening, prompts, naming batches, Fate summary), agonar.js (Fate looks at N weak records / names N "related" links), ufuk.js (sensed world born), oyuncu.js, server.js (world changed, genesis follow-ups) | `sys` line: gear icon + text. |
| `hata` | `metin`, optional `ogul_id` | agents.js, epoch.js (incl. `kilitle` catch), server.js, ufuk.js | `err` line with `hataTurkce(metin)` (English API errors → Turkish; LANGUAGE-SPECIFIC: replace with an English error humanizer); error toast. If no world yet, re-enable genesis submit with "Try again." Server also files a notification unless the text says it will be retried. |
| `kader_adim` | `metin` | agents.js (Fate weighing N creations / naming, verdict given in N s, chronicler wrote "Age name", peoples' historians writing, missing-age chronicles), konsey.js (council convening), kozmos.js (a new world is being born) | Sets actor category `kader`; `sys` line with Fate icon, category `kader`. |
| `kader_basla` | `cag` | epoch.js phase 4 start | Resets actor; line "Fate weighs the creations; the chronicler writes the age…" |
| `kader_bitti` | `cag, cag_adi, reddedilen[], duzeltilen[]` | epoch.js after Fate+chronicle | Line "Name of the age: **X**" + " · rejected: a, b" + " · corrected: c" or " · Fate accepted everything as it was." |
| `ag_onarim` | `tur` (`kural`/`kader`/`ilgili`), `metin`, `baglar?[{a:{t,id,ad}, tur, b:{…}, gerekce?, eski?:'ilgili', kapandi?}]`, `bakilan?[{t,id,ad}]` | epoch.js rule-based repair (`agKuralOnar`), agonar.js Fate link proposals and "related"-link naming | `sys` line via `agOnarimSatiri` (see above). Live: re-measure Network health boxes if open (`#agSaglik`, `#agOnarimKutu`). |
| `gorsel_sirada` | `tip, id, ad, kaynak, onde, suren, sira[]` | gorsel-uret.js when an image job is queued | (core/gorsel-uret.js `guOlay`) one line per target: "[gallery] <target> image queued · N images ahead <source>" with a progress widget; updates `G.S.gorsel_uret` and image buttons. Skipped during replay. |
| `gorsel_ilerleme` | `…suren` (target + progress fields), `suren, sira` | gorsel-uret.js progress callbacks | Same line updated: "<target> image being generated" + progress. Skipped during replay. |
| `gorsel_bitti` | `tip, id, ad, kaynak, durum ('tamam'/'hata'), gorsel{id,dosya,kapak}, sure_ms, genislik, yukseklik, adim, hata?, suren, sira` | gorsel-uret.js on success/failure | Success: thumbnail (click opens record) + "✓ <target> image generated" + meta (seconds, size, steps); failure: "<target> image could not be generated: error". Live: refreshes the open drawer / Atlas detail / Gallery tab of that target. |
| `gorsel_durum` | `kurulu, model, hazir, suren, sira, toplu, ayar{genislik,yukseklik,adim}` | gorsel-uret.js when queue empties / worker idles out | Replaces `G.S.gorsel_uret`, refreshes image buttons and panel. No line. |
| `gorsel_toplu` | bulk summary (`toplam, bitti, hata, atlandi, kalan, …`), `satir{seviye, metin}` | gorsel-uret.js bulk image run | Line (unless `seviye==='tamam'`): "[gallery] metin (done/total)"; `err` if seviye `hata`; updates bulk panel. |
| `toplu_derin` | bulk-deepen summary (`toplam, bitti, hata, atlandi, suan[], kalan, …`), `satir?{seviye, metin}` | toplu.js bulk deepening | Updates `G.S.toplu_derin` and bulk panel (`#topluKutu`); live line "[deepen] metin (done/total)" (`err` if hata). |
| `is_sirada` | `is{anahtar, ad,…}, onde, isler[], sira[]` | epoch.js `paralelIs` when the parallel-job pool is full | Store `G.S.isler/sira`; line "[pen] <job> was queued: N jobs running at once, M more ahead; it will start by itself when a slot opens."; re-render open drawer (to lock/unlock that record's buttons). |
| `is_basla` | `is, isler, sira` | epoch.js parallel job start | Line "<job> started · N jobs running at once" (suffix only if >1); re-render drawer. |
| `is_bitti` | `is, isler, sira` | epoch.js parallel job finished | Store lists; re-render open drawer. No line. |
| `cag_basla` | `cag, sira[{id,ad,ini}], surduruluyor` | epoch.js age start | Set job type `cag`, son queue length, compute ETA; line "[play] Age N is closing" / "resumes where it left off" + ". Order: A → B → C" (or "sons done" / "nobody"). |
| `asama` | `no, toplam (5), ad, sure` | epoch.js on entering each phase: 1 "Gods' turn (N sons)", 2 "Mortals' turn (N)", 3 "The world's own flow", 4 "Fate and chronicler", 5 "Age transition: growth, faith, essence, sky" | Progress title "no/total · name", bar advances; `asama` line "no/total name  N s"; state pill "no/total · name". |
| `sira` | `no, toplam, ad` | epoch.js before each son's turn in an age | State "son no/total · name"; progress agent counter and subtitle "<name> is thinking…". No line. |
| `yeniden` | `ad, deneme, toplam, sebep, bekle?, yapilan?` | llm.js retry hook (`ad`='tur' restart, 'devam' continue, 'süren iş' waiting for long action; or call name), agents.js `ask` retries, epoch.js son turn re-run | Closes the actor's stream; `sys yeniden` line: for `ad==='devam'`: "Turn interrupted (reason); keeping N successful steps, resuming where it left off (k/n)." else "<ad>: reason — retrying (k/n), in N s." |
| `basla` | `ogul_id, ogul_ad, model, yarim` | agents.js start of a son's turn | Actor category `ogul`; mark son acting (Pantheon cards get `acting`); `who` line: rarity sigil (22 px) + son link + mono "model name · resuming interrupted turn". |
| `akis` | `metin` (+ actor ids) | llm.js streaming text, buffered ~150 ms | Appends raw text to the actor's open `think akiyor` line (creates one if absent). Ignored during replay. |
| `dusunce` | `metin` (+ actor ids) | llm.js complete text block | Closes the actor's stream replacing its text with the final text (with id→name links), or adds a `think` line. |
| `arac_hazirlaniyor` | `arac, id` (+ actor) | llm.js tool_use block started | `tool bekliyor` line with spinner: "<tool label> preparing…". Tool label = friendly name from `ARAC_AD` (raw code name only in tooltip). |
| `arac_yaziliyor` | `arac, id, karakter` | llm.js every ~200 chars of tool JSON input | Appends/updates " · N characters writing" on the pending tool line. |
| `arac` | `arac, girdi{…}, id` (+ actor) | llm.js complete tool call | Fills the pending line (or new `tool` line): spinner + tool label + target (`girdi.ad` bold, or id → named link, or `"query"`) + optional sub-line: quoted `mesaj`, or `plan`/`aciklama` (first 260 chars, ids→links), or `ruya/lanet/bahane`. Reading tools get `think` style and are grouped (×N). Progress subtitle "<son> · <tool>". |
| `arac_sonuc` | `metin` (≤400), `hata`, `id` | llm.js tool result | Pending line gets `basarili`/`basarisiz`; on error a `res-err` line (first 260 chars, humanized); on success a `res-ok` line (first 240 chars) **unless** the text starts with "DÜNYA", "#<digit>", "UZUN", "oğul#", "Sonuç yok", "SEN:" or contains "\nSEN:" (LANGUAGE-SPECIFIC prefix sniffing to hide raw data dumps — replace with a server flag). |
| `bitti` | `ogul_id, ogul_ad, soz, yaratimlar, durum` | agents.js end of son's turn | Unmark acting; `soz` line with quoted final words; if `durum !== 'success'` an `err` line "Turn ended early: reason."; background refresh. |
| `olumluler_basla` | `ajanlar[{id,ad,tur}]` | epoch.js phase 2 start | Agent counter reset; line "[people] Mortals are acting: A → B → C". |
| `olumlu_basla` | `varlik_id, ad, tur, model, yarim` | olumluler.js start of a mortal agent turn | Actor category `olumlu`; counter `n/total`, subtitle "<name> is thinking…"; `who` line: type icon + entity link + "type · model". |
| `olumlu_bitti` | `varlik_id, ad, soz, yaratimlar, durum` | olumluler.js end of mortal turn | Quoted `soz` line if any. |
| `yaziyor` | `kim, konu?, akis, karakter, bitti?, durum?, hata?` | agents.js long structured writes (Kader, Kronikçi, Yaratılış/Genesis, Çağırma/Summoning, Vahiy, Ozan/Bard, Lore writer, Halkların uyanışı, Adlandırma), progress ~1/s | One line per stream id: spinner "[pen] <who · topic> is writing… N characters"; on `bitti`: "✓ <who> wrote N characters" or "<who> was interrupted <error>" (`err`). Progress subtitle shows the latest writer or "N writings in progress". Ignored during replay. |
| `motor_basla` | — | epoch.js phase 3 | Actor category `dunya`; line "[world] The mortal world lives its own flow…". |
| `motor_not` | `metin, kategori` | epoch.js world engine, one per note | `world vurgu ak-<cat>` line with category icon and auto-linked names; if the note has tag `alamet` (omen) it is styled `isaret` with sky icon and not grouped (note: payload never carries `etiketler`, so this branch is dead). Grouped by category; plays category tone; updates category filter row; progress subtitle = first 60 chars. |
| `motor_bitti` | `notlar[]` | epoch.js end of phase 3 | If no notes: line "[world] A quiet age among the mortals." |
| `cag_bitti` | `cag, yeni_cag, ozet[], sure` | epoch.js age finished | Remember last age duration; reload step measurements; line "[play] Age N began (the age lasted X min Y s). <summary sentences>"; toast "Age N began"; full background refresh. Server also files a notification. |
| `yeni_ogul` | `ogul{…}` | epoch.js summon / deification of a mortal | Line "[birth] A new son: **Name**, Title (Rarity)"; card-reveal animation "<Rarity> son arrived". |
| `yukselis` | `ogul{…}` | epoch.js rarity ascension | Line "[ascension] **Name** rose to <Rarity> class."; reveal "Ascension · <Rarity>". |
| `vahiy` | `varlik{…}` | epoch.js revelation done | Line "[revelation] Revelation descended: <entity link>"; toast "<name> appeared"; opens the entity drawer. |
| `derinlesti` | `varlik{id,ad}` | epoch.js deepening finished | Line "[deepen] <entity link> deepened." |
| `yabanci_derinlesti` | `id, ad` | epoch.js foreign god deepened | Line "Foreign god <link> deepened: personality, existence, powers and depth were written." |
| `bildirim` | `id, cag, kategori, onem, baslik, metin, hedef_tip, hedef_id, kronik_id, ad` (category name) | bildirim.js whenever a notification is filed | Increment unread counter, redraw top bar. If achievement (`kategori==='basarim'` or title starts "Başarım:"): line "[trophy] Achievement earned: **X**" + toast "Achievement: X". Else toast "<category>: <title>" if `onem >= kural('BILDIRIM.toast_onem', 3)`. Skipped in replay. |
| `dunya_dogdu` | `dunya_id, ad` | kozmos.js new world born | Line (category `kader`) "[world] A new world was born: **Name**"; toast "<Name> was born"; selects the world in Cosmos (`KOZMOS.sec`, side panel `dunya`); background refresh. |
| `konsey` | `id, konu, kabul, onerge` | konsey.js council finished | Line (category `kader`) "[council] Council of the Gods: “motion” · **accepted/rejected**"; toast "Council: motion accepted/rejected"; background refresh. |
| `genesis_bitti` | — | server.js after genesis | Line "World created."; full refresh. |
| `motor_bilgi` | — | **never emitted** (dead handler, no-op) | — |
| `tanri_isareti` | `metin` | **never emitted as an event** (only exists as a chronicle entry type) | Would render a highlighted sky-icon world line. Dead code. |

Notes for the new event contract:
- Two families of event (`akis` streaming text and `yaziyor` progress) are high-frequency (≈ every 150–1000 ms per active writer); throttle/coalesce server-side.
- `motor_bilgi` and `tanri_isareti` are handled by the old UI but never emitted; the omen branch of `motor_not` is dead (payload lacks tags). Decide whether to emit or drop.
- Mortal-agent turn events reuse `ogul_ad` for the mortal's name; use a neutral `actor {type, id, name}` object in the new API.
- Events emitted directly from `server.js`, `gorsel-uret.js` and `toplu.js` carry no `cag`/`zaman` stamp; stamp all events centrally.

---

## 5. Usage matrix (endpoint → views)

| View / module (old file) | Endpoints |
|---|---|
| App shell & refresh loop (`core/yenile.js`, `app.js`) | state, degisim, iliskiler, iplikler, denge, defter (+undo), gorseller (lightbox), kesif/bitir, olaylar, gunluk |
| Header actions | cag/tamamla, cag/durdur, cagir, vahiy (modal in `views/ayarlar.js`), kitap |
| Genesis (`views/genesis.js`, `akis.js`) | sihirbaz, genesis |
| Pantheon (`views/panteon.js`) | state (sons), iplikler/:id/kapat |
| Goals & actions panel (`views/hedefler.js`) | hedefler, senaryolar(+birak), firsatlar, konseyler, konsey, iplikler (POST), uyandir, tanri/suret |
| Son drawer (`views/ogul.js`, `acilis.js`) | ogullar/:id, defter?kim_tip=o, ogullar/:id/sohbet (GET/POST), all `ogullar/:id/*` actions, inanclar, ek, kitap?ogul |
| Creator drawer (`views/tanri.js`) | tanri (GET/POST), tanri/itibar, tanri/tutku, tanri/ruh, tanri/destan, tanri/derinlestir, tanri/not |
| Entity drawer (`views/varlik.js`) | varliklar/:id, varliklar?tur=teknoloji, varliklar?durum=tum, all `varliklar/:id/*` actions, baglar, gercekler, kozmik/ruh, kozmik/yatak, ek, yol, kitap?varlik, gorseller?tip=t/d |
| Foreign-god drawer (`views/yabanci.js`) | yabanci/:id, yabanci/:id/(duzenle|oz-em|oldur|derinlestir) |
| Cosmos (`views/kozmos.js`, `kozmos3d.js`) | kozmos, dunya-yarat, dunyalar/:id/(duzenle|gazap), yildizlar/:id/(duzenle|sil), kozmik/(rota|gok|iklim|kaynak|yatak|yildiz|muhur|temizle|unut|tutustur|sefer), rotalar/:id/*, yolculuklar/:id/geri, yabanci (POST), yabanci/:id/duzenle, federasyon, kesif/tur, varliklar/:id/sefer, /gorsel |
| Map (`views/harita.js`) | harita, harita/konum, harita/not(+sil) |
| Atlas (`views/atlas.js`) | varliklar?durum=tum |
| Network (`views/ag.js`, `ag3d.js`) | graf, yol, ag/saglik, ag/onar, ag/kader(+durdur) |
| Chronicle (`views/kronik.js`, `grafik.js`) | kronik?cag, kronik/caglar, caglar, bakislar, iplikler, istatistik, kozmik-kronik, ara, kodeks.md |
| Languages (`views/diller.js`) | sozluk, dil-agaci, bilgiler, cevir |
| Gallery (`views/galeri.js`, `core/gorsel*.js`) | gorseller, galeri/eksik, gorsel (upload), gorseller/:id/*, gorsel-uret(+toplu) |
| Prayers (`views/dualar.js`) | dualar, dualar/:id/cevap |
| Notifications (`views/bildirim.js`) | bildirimler (+oku, ayar, POST) |
| Ledger (`views/defter.js`) | defter, defter/:id/geri-al |
| Records drawer (`views/kayitlar.js`) | varliklar?durum=tum, bildirimler?kategori=not, harita (notes), favoriler |
| Command palette (`views/palet.js`) | ara, favoriler, cag/tamamla, cagir |
| Guide (`views/rehber.js`) | dunyalar/:id/rehber, kodeks.md |
| Settings (`views/ayarlar.js`, `toplu.js`, `olcum.js`) | ayar, denge, saglik, yedekler, yedek, yedek/geri, /yedek/*, dunya/disa-aktar, dunya/ice-aktar, sifirla, hile/oz, promptlar, toplu/derin(+baslat/durdur), adlandir, olcum, kodeks.md, kitap |
| Epoch breakdown (`core/dokum.js`) | dokum |
| Live feed (`views/akis.js`) | olaylar, gunluk, cag/tahmin, olcum, cag/durdur |
| Names (`core/adlar.js`) | adlar |

Unused by the UI: `GET /api/kesif` (data duplicated inside `/api/kozmos`).

---

## 6. Known API smells to fix in the new design

1. **Everything is POST with verbs in paths** (`/sil`, `/duzenle`, `/kapat`); deletes are POSTs. Use proper REST verbs.
2. **Giant unpaginated payloads**: `/api/state` (rules catalogue + all sons + pulse, recomputed on every call), `/api/graf` (19k links), `/api/varliklar` (all entities), `/api/varliklar/:id` (`baglar` 500+, `kronik` 600+). Paginate and split the static catalogue into a cacheable endpoint.
3. **Mixed raw and decorated shapes**: some actions return raw DB rows with JSON columns as strings (`ek`, `toplum`, `tur_ctx` in list endpoints), others parsed objects. Use Pydantic response models everywhere.
4. **Turkish-grammar plumbing leaks into the API** (`ek` objects, `/api/ek`, suffix dictionary rebuild). Drop.
5. **Polling + SSE double channel**: the client receives SSE then polls `/api/degisim`. Push entity-change events directly.
6. **Job results are only discoverable via side events**; there is no job id. Add a Job resource.
7. **Typed confirmations are Turkish strings** sent from the client (`SIFIRLA`, `GERİ YÜKLE`, `DEĞİŞTİR`, `BİRLEŞTİR`). Keep the pattern (server-side check) with English tokens.
8. **Max of a rule is advisory but min is enforced** — make this explicit in the rules schema (`hard_min`, `soft_max`).
9. **Error responses are free text**; the UI pattern-matches nothing but humans need the rule key. Return structured `{code, rule_key}`.
10. **Thumbnails depend on macOS `sips`** — use a portable image library.
11. **Search uses `instr()` over folded text on every column** (full scans). Use FTS5.
12. `GET /api/kronik` has two response formats depending on `sayfa=1`; pick the envelope.
