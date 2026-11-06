# 12 — Frontend: information architecture, screens, and design defects

Source of truth (old app): `public/index.html` (the shell), `public/app.js` (bootstraps and owns the global click router), `public/core/*` (state, API client, DOM patcher, drawer system, forms, refresh loop, images), `public/views/*` (one module per screen/drawer), `public/kozmos3d.js` + `public/kozmos3d/*` (three.js cosmos), `public/harita-gen.js` (procedural map), `public/style.css` (≈200 KB, one file), `public/icons.js`, `public/marka.js`, `public/etiket.js`, `public/stil.html` (living style guide). Vanilla ES modules, no framework, no build step; d3 7.9 and GSAP 3.12 from cdnjs, three.js 0.170 from jsDelivr via an import map. All UI copy is Turkish; this spec gives English labels with the Turkish original in parentheses the first time.

API endpoints are referenced by their **old** paths (e.g. `GET /api/varliklar/:id`); the English proposed path for each is in `11-api.md`.

How to read this document:

1. **Part 1 — Information architecture** (this part): the shell, navigation model, every screen/drawer/overlay at a glance, and the data/refresh model.
2. **Part 2 — App shell, settings, onboarding and utility screens** (header, footer, keyboard, refresh loop, genesis wizard, settings and World Rules editor, notifications, ledger, prayers, records, palette, help, guide, epoch breakdown, model metrics, batch tools).
3. **Part 3 — Pantheon and record pages** (son cards; son / entity / creator / foreign-god drawers; drawer system; images and image generation).
4. **Part 4 — Cosmos and Map** (2D/3D cosmos, every cosmic action, the map renderer, and the procedural map generator).
5. **Part 5 — Live feed, Chronicle, Network, Atlas, Languages, Gallery, Goals** (including the complete realtime event table).
6. **Part 6 — Branding, recurring UI defects, design-token inventory** (the input for the new design system), followed by the per-screen defect lists gathered from Parts 2–5.

---

## Part 1 — Information architecture

### 1.1 Product shape

Weavers of the Void is a single-user, local, single-page web app that shows **one world at a time** (a world = a whole cosmos with one or more planets). The player is the **Creator** (Yaratıcı / Tanrı). Everything the player does is either (a) reading the living encyclopaedia the simulation writes, or (b) spending **divine essence** (Tanrısal öz) on interventions. Time advances only when the player presses **Complete epoch** (Çağı tamamla); an epoch is a long background job (minutes) whose progress streams into the **Live feed**.

There is no routing library: the active tab is stored in `location.hash` (`#panteon`, `#kozmos`, …) and `localStorage['aerona.tab']`; drawers are an in-memory history stack. No URL deep link opens a drawer (a smell — the new app should have routes for every record: `/sons/:id`, `/entities/:id`, `/foreign-gods/:id`, `/creator`, `/worlds/:id/guide`).

### 1.2 Screen map (old layout)

```
┌──────────────────────────── header.bar ─────────────────────────────────────────────┐
│ [logo] Weavers of the Void / <World name> / <Epoch line>   [9 tabs]   Essence | World filter |   │
│ Mood chip | Search | Book | Bell(n) | Records | Settings | Revelation | Summon son | │
│ Complete epoch | Stop                                                                │
│ ───────────── thin epoch progress bar (only while busy) ──────────────               │
├──────────────────────────────────────────────────────┬───────────────────────────────┤
│ main#main: exactly one <section class="view"> visible │ aside#live: Live feed          │
│  Pantheon | Cosmos | Map | Atlas | Network | Chronicle│  (collapsible; progress block, │
│  | Languages | Gallery | Prayers                      │  actor filter, category filter,│
│                                                       │  sound toggles, event lines)   │
├──────────────────────────────────────────────────────┴───────────────────────────────┤
│ footer.altbilgi: brand · discovery-mode band · world line · help/shortcuts · links     │
└───────────────────────────────────────────────────────────────────────────────────────┘
Overlays (above everything): Genesis screen (no world yet) · Drawer (right panel, record
pages and utility pages) · Command palette (⌘K) · Card-reveal animation · Lightbox · Toast ·
Epoch-breakdown modal · inline confirmation popovers.
```

### 1.3 Top-level tabs (`data-tab`, keys 1–9)

| # | Tab (old label) | Purpose | Primary data |
|---|---|---|---|
| 1 | Pantheon (Panteon) | Home. The creator's panel, son cards (god cards), goals/score, opportunities, this-age summary, threads, sibling-relations matrix, councils, card comparison. Whole cosmos (not filtered by world). | `/api/state`, `/api/hedefler`, `/api/firsatlar`, `/api/konseyler`, `/api/iplikler` |
| 2 | Cosmos (Kozmos) | Star systems, planets, moons, routes, voyages, foreign gods in a 3D (three.js) scene with a 2D fallback; side panel with world/star cards and every cosmic command. | `/api/kozmos` |
| 3 | Map (Harita) | Procedurally generated planet map of the selected world: regions, places, settlements, peoples, roads, routes, wars, events, notes; political / religion / language overlays; past-epoch time slider. | `/api/harita` |
| 4 | Atlas | Wiki-style browser of all entities by type/family with filters, search, archive ("history") toggle and a detail pane. | `/api/varliklar?durum=tum` |
| 5 | Network (Ağ) | Knowledge graph of every record and bond: 2D d3 force graph and 3D view, focus mode, path finder, network health & repair. | `/api/graf`, `/api/ag/*`, `/api/yol` |
| 6 | Chronicle (Kronik) | Epoch-by-epoch history: epoch narratives, chronicle lines with type filters and search, peoples' partisan histories, cosmic chronicle, threads, stats charts. | `/api/caglar`, `/api/kronik`, `/api/istatistik`, … |
| 7 | Languages (Diller) | Conlang dictionaries, language family tree, translation into a conlang, knowledge (technology) tree. | `/api/sozluk`, `/api/dil-agaci`, `/api/bilgiler` |
| 8 | Gallery (Galeri) | All images by target; "missing images" queue; local image generation. | `/api/gorseller`, `/api/galeri/eksik` |
| 9 | Prayers (Dualar) | Prayers from sons and mortals; answer with words and/or essence. Badge = unanswered count. | `/api/dualar` |

The **world filter** (Dünya süzgeci, header select, shown only when the cosmos has more than one world) filters Cosmos, Map, Atlas, Network, Chronicle, Languages, Gallery and Prayers to one planet; Pantheon is always the whole cosmos.

### 1.4 Drawers (right-side panel, `openDrawer(type, id)`)

| Drawer type | Opened by | Content |
|---|---|---|
| `o` Son page (Oğul) | any `[data-o]` link, son card click | Hero, god-power controls, chat, stats, powers, creations, bonds, messages, ledger, chronicle |
| `v` Entity page (Varlık) | any `[data-v]` link, auto-linked names | Hero, lore, stats, society, life/death, bonds, facts, knowledge, interventions, god's power, arrange & command |
| `t` Creator page (Yaratıcı) | `[data-tanri-ac]`, creator panel | Title/appearance edit, mood, reputation & passions, note, epic, depth, cult, traces |
| `y` Foreign-god page (Yabancı tanrı) | `[data-yabanci]` | Profile, worshippers, edit, drain/kill/devour |
| `rehber` Traveller's guide | `[data-rehber]` (world cards) | Per-world guide |
| `ayar` Settings (Ayarlar ve kodeks) | header gear | Game, models, rules editor, appearance, backups, import/export, health, batch tools |
| `vahiy` Revelation | header "Revelation" | Create one entity by decree |
| `bildirim` Notifications | header bell | Notification list & per-category settings |
| `kayit` Records (Kayıtların) | header records icon | Ledger (undo), personal notes, bookmarks, favourites, map notes |
| `yardim` Help | `?` key, footer | Shortcuts and glossary |

Drawers keep a back/forward history (Alt+←/→, buttons in the drawer nav), close with Esc / scrim click, trap focus, and re-render in place when the underlying data changes.

### 1.5 Overlays and global widgets

- **Genesis screen** (`#genesis`): full-screen form shown when `state.dunya == null`; includes the wizard (templates and sliders). See Part 2.
- **Command palette** (`#palet`, Ctrl/⌘+K): global search + quick commands.
- **Card reveal** (`#reveal`): gacha-style animated reveal when a new son arrives or ascends.
- **Lightbox** (`#lightbox`): image viewer with prev/next, cover/caption/delete.
- **Toast** (`#toast`): single toast slot; error toasts last 6.5 s, toasts with an action button (e.g. Undo) 7 s, others 3 s.
- **Epoch breakdown modal** (`core/dokum.js`): what moved the doom clock, leaks, population and essence in an epoch.
- **Inline confirmations**: buttons with `data-onay="Are you sure? <verb>"` turn into a confirm state on first click; destructive world operations need a typed token (RESET, RESTORE, REPLACE, MERGE).

### 1.6 Cross-cutting interaction conventions

- **Record links everywhere**: `data-v=<id>` (entity), `data-o=<id>` (son), `data-yabanci=<id>`, `data-tanri-ac`, `data-rehber=<worldId>`, `data-haritada=<id>` (show on map), `data-agda=<id>` (show in network), `data-tab-go=<tab>` (+`data-filter` for Atlas), `data-im-git="<epoch>.<lineId>"` (jump to a chronicle line), `data-copy`, `data-lb`/`data-glb` (lightbox), `data-karsi` (add to comparison), `data-palet`, `data-iklim-ac`, `data-kesif-bitir`. A single delegated click handler in `app.js` routes them.
- **Auto-linked names**: all prose is passed through a name→link regex built from `/api/adlar`, so every entity/son/foreign-god name in any text becomes a link (the Turkish version also had to strip/attach grammatical suffixes — LANGUAGE-SPECIFIC).
- **Cost chips**: every paid button shows `<icon essence> N` from the live rule value and is disabled (with a tooltip naming the rule) when the creator lacks essence or a job is busy.
- **Undo**: every successful god action shows a toast with an Undo button that tears the action's page out of the Ledger.
- **Declarative forms**: `<form data-post="/api/…" data-mesaj="success toast" data-onay="confirm">`, fields named with dot paths (`kisilik.mizac`) are serialised to JSON; numbers/ranges become numbers; checkboxes booleans.
- **Busy model**: while an exclusive job runs (`state.mesgul`), most write buttons are disabled; per-record parallel jobs (`state.isler`/`sira`) disable only that record's buttons.
- **Discovery mode**: a band in the footer and read-only behaviour (all POSTs blocked client-side) when browsing an imported world.

### 1.7 Data and refresh model (old)

1. Boot: `refresh()` → `GET /api/state` (everything) → render active tab; then backfill the live feed from `/api/gunluk`; then open the SSE stream `/api/olaylar`.
2. SSE events render feed lines immediately and schedule a **background refresh**: `GET /api/degisim?surum=<cursor>`; changed sons/entities are patched into the in-memory state; booleans (`baglar`, `dunyalar`, `dunya`, `iliskiler`) trigger targeted refetches; `tam:true` triggers a full `/api/state` reload.
3. Views re-render by building an HTML string and applying it through a tiny keyed DOM patcher (`yamala`): nodes are matched by tag + `data-k`/`id`; attributes and text are diffed; focused inputs and open `<details>` are preserved.
4. Heavy views cache their own data (`HARITA`, `KOZMOS`, `AG`, `ATLAS`, `KRONIK` module-level objects) and refetch only when their version counters change.

New app recommendation: React Query (or equivalent) caches per resource; a single WebSocket/SSE channel pushes typed events including `entity.changed`; components subscribe by key; no global HTML re-render.

### 1.8 Proposed information architecture for the rewrite (summary)

Keep the mental model (tabs = lenses on one world; drawers = record pages; live feed = the world's heartbeat) but:

- Make records routable (URL per record, drawer as a route-driven side sheet; browser back works).
- Group tabs: **Pantheon** (home), **World** (Cosmos, Map, Atlas, Network as sub-views of one "explore" area with a shared world selector), **History** (Chronicle, Languages, Gallery), **Prayers** stays top-level because it is a to-do inbox.
- Move header actions (Revelation, Summon, Complete epoch, Stop) into one consistent **Action bar** component with the cost chip pattern; keep Complete epoch as the single primary button.
- Settings becomes a full page (it is far too large for a drawer), with the World Rules editor as its own route.
- Treat the Live feed as a dockable panel with virtualised list.

---

## Part 2 — App shell, settings, onboarding and utility screens

### Scope and conventions (Part 2)

Scope: application shell (header bar, footer, refresh loop, keyboard shortcuts), the Creation screen (genesis), the Settings drawer (including the World Rules editor), Revelation drawer, Notifications, Records (action ledger / notes / bookmarks), Prayers tab, Traveller's guide, Help, Command palette, son-reveal overlay, epoch breakdown popover, model measurement, batch deepening, plus the shared text helpers (name auto-linking, labels, tool-name table, Turkish grammar helpers).

Conventions used below:
- `G.S` = cached response of `GET /api/state`; `G.K` = `G.S.kurallar` (static rules/constants shipped with state); `kural('X.y', default)` = live value of a World Rule from `GET /api/denge` (client cache in `core/kural.js`).
- "Two-click confirm" = first click swaps the button label to a confirmation phrase, second click performs the action.
- Numbers are formatted with `toLocaleString('tr-TR')` (dot thousands separator). The rewrite should use the English locale.
- All persisted UI state is `localStorage` key `aerona.<name>`, JSON-encoded by `yerel()/yerelYaz()` (`core/dom.js:52-53`), except `aerona.tab` and `aerona.harita` which are written raw (see defects).

---

### 2.1 Application shell layout (index.html)

Order of top-level regions inside `#app` (CSS grid; header spans both columns, main + footer in column 1, live feed in column 2):

1. `header.bar` — header bar (section 2).
2. `main#main` — nine `<section id="view-<tab>" class="view">` containers, one per tab; only the active one has class `on`.
3. `footer.altbilgi#altbilgi` — footer strip (section 3).
4. `aside#live.live` — Live feed panel (specified in Part 5; mentioned here only where the shell touches it: progress mirror, reopen button, sound settings).

Overlays outside `#app` (all `hidden` by default):
- `#genesis` — Creation screen (section 5), z-index 60.
- `#drawer` — right-side drawer: `.drawer-scrim[data-close]` (click closes), `.drawer-panel[role=dialog][aria-modal]` containing back/forward buttons (`[data-gecmis="-1"|"1"]`, titles "Back (Alt+←)" / "Forward (Alt+→)"), a close X (`[data-close]`, "Close (Esc)") and `#drawerBody`. z-index 50.
- `#palet` — command palette (section 12), z-index 92.
- `#reveal` — son card reveal overlay (section 13), z-index 85.
- `#lightbox` — image viewer, z-index 90 (specified in Part 3, Images).
- `#toast` — toast, z-index 95.
- `.dokum-pop` (created lazily by `core/dokum.js`) — epoch breakdown popover, z-index 120.

External libs loaded globally: d3 7.9.0 and GSAP 3.12.5 (cdnjs), three.js 0.170 via import map (`three/webgpu` is stubbed by `/three-webgpu-yok.js`). Fonts: Cormorant Garamond (display), Alegreya Sans (body), JetBrains Mono (numbers). `theme-color #111318`.

#### Drawer router (core/cekmece.js `openDrawer(tip, id, silent, fromHistory)`)
Drawer types relevant to this part: `ayar` (Settings), `vahiy` (Revelation), `bildirim` (Notifications), `kayit` (Records), `yardim` (Help), `rehber` (Traveller's guide, id = world id). Entity drawers `o` (son), `v` (entity), `t` (creator god), `y` (foreign god) are specified in Part 3, but share: a back/forward history stack (`GECMIS`, only entity drawers are pushed), "silent" re-render on refresh (only entity drawers re-render silently; utility drawers ignore silent refreshes), stale-response guard (`G.drawerIstek` counter), scroll reset + focus trap on open (Tab cycles within `.drawer-panel`; focus returns to the previously focused element on close), and an auto "section nav" bar (`.bolum-nav`, sticky) that appears when an entity drawer has ≥4 section headings (labels truncated at 26 chars).

---

### 2.2 Header bar (`header.bar`)

Grid areas: `"brand god" / "tabs tabs"`; an optional progress strip spans the full width below.

#### 2.2.1 Brand block (`.brand`)
- `#brandLogo`: inline SVG logo (`LOGO_SVG(38)` from `marka.js`), re-injected on every header render.
- `.marka-ad`: static text "Weavers of the Void".
- `#worldName`: `G.S.dunya.ad` (world name). Also sets `document.title` to the world name.
- `#epochLine` (single line, `white-space: nowrap; text-overflow: ellipsis`), spans in this order:
  1. "Epoch **N**" (`Çağ`) — `dunya.cag`.
  2. "Year **N**" (`Yıl`) — `dunya.yil`, number-formatted.
  3. Star of the epoch chip (`.star-now`, colour = legendary rarity colour, sky icon), only if a star exists: text `[World name: ]Star name[ · domain]`; `data-v=<star id>` → clicking opens that entity drawer. Tooltip: "[In the sky of World X ]star of the epoch: creations in the *domain* domain are *(100 − OGUL_ARAC.yildiz_indirim)*% cheaper [(each world has its own sky; pick a world above)]". Source:
     - single world: `G.S.cagin_yildizi {id, ad, alan}`;
     - multi-world: `G.S.dunyalar_durum[] {id, cagin_yildizi, iklim}` for the "bar world" (the selected world, or the lowest-id world when "Whole cosmos" is selected). Fallback for old servers: Cosmos data (`KOZMOS.veri.dunyalar[].cagin_yildizi` / `.iklim`), triggering a one-time background cosmos refetch and re-render.
  4. Climate chip (`.iklim-now.iklim-<evre>`, climate icon) if a climate era exists: `[World: ]<climate name>`; `data-iklim-ac` → click switches to the Cosmos tab, opens the "Create → Climate" panel and scrolls to `#kozmosIklim`. Tooltip: "[World X's climate (each world has its own climate; pick a world above) · ]<description> · since Epoch N, K more epochs · click: change the climate". Source: `G.S.iklim {evre, ad, aciklama, bas, kalan}` or `dunyalar_durum[].iklim` merged with `G.K.IKLIM[evre]`.
  5. Fate debt chip (`.borc-cip`, only if `G.S.kader_borc != null`): "Fate in debt since Epoch N" (`Kader Çağ N'den borçlu`). Tooltip: "Fate could not weigh the creations in Epoch N; everything created since then will be weighed together at the end of the next epoch."
  6. Doomsday clock chip (`.kiyamet-cip`, death icon, `data-dokum="kiyamet"`, focusable): "Doomsday **k**/threshold" or "Cosmic doomsday **k**/threshold" in multi-world. `k = dunya.kiyamet`, threshold = `G.K.DENGE.kiyamet_esik` (rule `DENGE.kiyamet_esik`, default 100). Colour class: `c-tehlike` (danger red) if k ≥ threshold × `KIYAMET.uyari2`% (default 80), `c-uyari` (warning amber) if ≥ threshold × `KIYAMET.uyari1`% (default 50). Tooltip: "Doomsday clock[ (the whole cosmos's)]: at *threshold*, *the world* / *the most-leaked world (on a tie the most godless one)* is destroyed by disasters (threshold is set in World Rules). Hover: last epoch's plus/minus items." Hover/focus opens the Epoch breakdown popover (section 15).
  7. "N sons waiting" (`N oğul bekliyor`) from `G.S.bekleyen.length`, or "everyone has acted" (`herkes davrandı`).
  8. "previous: **<epoch name>**" (`önceki`) if `G.S.cag.ad`.

#### 2.2.2 Tabs (`nav#tabs[role=tablist]`)
Nine buttons with `data-tab`; order defines number shortcuts 1–9. On boot (`yardim.js kur`) each gets an icon span `.tab-ic`, `role=tab`, `aria-keyshortcuts`, and title suffix "Shortcut: N".

| # | key | Label (TR) | Icon |
|---|---|---|---|
| 1 | panteon | Pantheon (Panteon) | son |
| 2 | kozmos | Cosmos (Kozmos) | sky |
| 3 | harita | Map (Harita) | map |
| 4 | atlas | Atlas (Atlas) | atlas |
| 5 | ag | Network (Ağ) | network |
| 6 | kronik | Chronicle (Kronik) | chronicle |
| 7 | sozluk | Languages (Diller) — title "Languages, dictionary and knowledge tree" | language |
| 8 | galeri | Gallery (Galeri) | gallery |
| 9 | dualar | Prayers (Dualar) + `#duaPill` count badge | prayer |

`#duaPill`: hidden when `G.S.dualar` is 0/falsy, else shows the count of unanswered prayers.

Tab selection: `sekmeAc(t)` sets `G.tab`, marks the button `on` + `aria-selected`, toggles `.view.on`, writes `location.hash = #<tab>` via `replaceState`, stores `aerona.tab`, and calls the view's render function. Visiting `harita` or `dualar` marks onboarding steps done (`aerona.adim.harita`, `aerona.adim.dualar`). Initial tab = URL hash if valid, else `aerona.tab`, else `panteon`. `hashchange` also switches tabs. On narrow screens (≤ ~600 px) tabs move to a fixed bottom bar (z-index 60) with icon + short label.

When leaving a tab the switcher also pauses other views' heavy work: cancels the Map animation frame and playback, stops the 2D Network d3 force simulation if still hot (`G.simDurdu=true`), pauses the 3D network animation. Cosmos 3D keeps running but self-pauses when invisible.

#### 2.2.3 God block (`.god`), left-to-right
1. Essence counter (`.essence`): small caps label "Divine Essence" (`Tanrısal Öz`; hidden on narrow screens) over `#godOz` = essence icon + `fmt(dunya.tanri_oz)` in mono accent colour. It is made focusable with `data-dokum="oz"` (hover → breakdown popover for essence). Tooltip: "Divine Essence: spent to summon sons, reveal, bless, grant stars and punish. Each epoch it refills by *DENGE.tanri_oz_yenilenme (20)* + the total faith of your sons ÷ *DUNYA_CAG_GECISI.inanc_oz_bolen (10)*."
2. World filter (`label#dunyaUst.dunya-ust`, globe icon + `select#dunyaSecim`, aria "World filter"): hidden unless the cosmos has >1 world (`G.S.dunyalar.length > 1`). Options: "Whole cosmos" (`Bütün kozmos`, value 0) + one per world (`G.S.dunyalar[].ad`). Selected value persisted as `aerona.dunyaSec`; the pill gets class `on` (tinted with the world-type colour) when a specific world is chosen. Tooltip: "Which world you are looking at: cosmos, map, atlas, network, chronicle, languages, gallery and prayers are filtered by it; the pantheon is the whole cosmos's." On change (`dunyaSecDegis`): stops map playback and sets map world (`aerona.haritaDunya`), sets Cosmos selection, sets Atlas world filter and resets Atlas paging, invalidates Network signature, clears an Atlas selection that belongs to another world, re-renders the header (star/climate now show the chosen world) and the current tab. Also updates the Summon button's target suffix and tooltip.
3. Mood chip (`#ruhCip.ruh-cip`, anger icon + mood label): hidden unless `G.S.tanri_ruh`. Text = `tanri_ruh.etiket`. Class by label: "angry" (`öfkeli`) danger red; "distant and silent" (`uzak ve sessiz`) faded; "lonely" (`yalnız`) purple; "pleased" (`hoşnut`) gold; "restless" (`huzursuz`) amber; "calm" (`dingin`) text colour. Tooltip: "<God name>'s mood: <label>. <description>\nAnger a · Contentment b · Interest c · Loneliness d" (`ofke`, `hosnutluk`, `ilgi`, `yalnizlik`). Descriptions: angry "The sky darkens; godless homelands should be afraid."; distant "The Creator is not looking; his sons do not hear his voice."; lonely "The Creator is lonely; seers dream his dream."; pleased "The Creator is pleased; those who worship him are blessed."; restless "The Creator is restless; the measures are unbalanced."; calm "The Creator is calm; the world goes its own way."
4. Search icon button (`[data-palet]`, title "Search everything (Ctrl/⌘+K)") → opens the palette.
5. Book link (`<a href="/kitap" target=_blank>`, title "The world's book: printable encyclopedia (new tab)").
6. Bell (`#btnBildirim`) with `#bildirimPill` unread count (hidden at 0, capped display "99+"); title "N unread notifications" or "Notifications" → opens Notifications drawer.
7. Records (`#btnKayit`, title "Your records: action ledger (undo), your notes and bookmarks") → Records drawer.
8. Settings (`#btnAyar`, title "Settings and codex") → Settings drawer.
9. Revelation (`#btnVahiy`, label "Revelation" (`Vahiy`) + `.cost` = `G.K.COSTS.vahiy`) → Revelation drawer (section 7).
10. Summon son (`#btnSummon`, "Summon son" (`Oğul çağır`) + `#summonHedef` "→ World X" when a world is selected + `.cost` = `G.K.COSTS.cagirma`) → `POST /api/cagir` body `{dunya_id}` if a world is selected else `{}`; via `act()` (button lock, refresh, undo offer); toast "New son being summoned for World X" only when a world is selected. Tooltip: "The new son is summoned to world X" / "Fate chooses the new son's world (pick a world above to summon there)".
11. Complete epoch (`#btnEpoch`, primary) → `POST /api/cag/tamamla` via `act()`. Label variants:
    - busy (`G.S.mesgul`): gear icon "Running…" (`Sürüyor…`), disabled, title "A job is running; its progress is in the live feed and the top strip."
    - half-finished epoch (`G.S.yarim_cag {cag, asama}`): "Complete epoch · resume (*asama*/5)" or "(gods' turn)".
    - normal: "Complete epoch (N)" where N = waiting sons (omitted if 0).
    - Tooltip (also `aria-description`) built by `cagIpucu()` (akis.js): line 1 "N sons waiting." / "All sons have acted this epoch." / "Epoch X was interrupted; everything after phase P resumes where it stopped." / "Epoch X was interrupted during the gods' turn; the turn continues with sons who have not yet acted."; line 2 "Complete epoch: N son turns + M mortal agents + world engine + Fate and chronicler; then growth, faith and essence are computed." (M = `dunya.olumlu_sayisi` or `OLUMLU_AJAN.varsayilan`); line 3 "Estimated time X (average of last n epochs | from step averages); last epoch took Y"; line 4 "This is model work; while running, 'Stop' halts it at a safe point, then it completes from where it stopped."
12. Stop (`#btnDurdur`, danger, hidden unless `G.S.mesgul.tur === 'cag'`): two-click confirm via `data-onay` ("Are you sure? Stop at a safe point", reverts after 4 s). Then `POST /api/cag/durdur` `{}`: 404 → toast "This server version doesn't know how to stop an epoch yet; the epoch continues." (error); 501 → server message; 409 → toast "No epoch is running" and hide; OK → button shows spinner "Stopping…" disabled, toast "The epoch will stop at a safe point; you can resume from where it stopped later", live-feed system line "Stop requested: the epoch will stop at a safe point."

Cost/disabled rule for Summon and Revelation (`renderBar → dugmeBedel`): disabled (plus `data-engel`) when busy ("A job is running; it opens when finished.") or when `tanri_oz < cost` ("*cost* essence required; you have *oz*."), tooltip prefixed with the action name. Revelation's enabled tooltip: "Create a single entity with your own hand (*cost* essence)".

Read-only (exploration) mode: `body.salt-okunur` toggled when `G.S.kesif` is set (CSS hides/disables mutating controls).

#### 2.2.4 Top progress strip (`#ustIlerleme`)
Visible only while the live feed's progress block is visible (a job is running). Contains a 2 px bar `#ustIlerlemeCubuk` (width = phase/5 × 100 %, min 4 %, gradient accent→legendary; indeterminate sliding animation when the job is not an epoch) and mono text `#ustIlerlemeMetin`: "<phase name> · <m:ss elapsed> · estimated <remaining> · <sub-status>" (copied from the live panel fields, ellipsized, pulsing dot prefix). Click → opens the live feed panel. Updated every second while running.

---

### 2.3 Footer (`footer.altbilgi`)
Height 30 px, left to right:
1. Brand: 14 px logo + "WEAVERS OF THE VOID" (mono, spaced caps).
2. Exploration banner `#kesifBant` (only in exploration mode): eye icon "**Exploration mode:** <guest world name> read-only" + primary button "Return to my world" (`Kendi dünyama dön`, `[data-kesif-bitir]`) → `POST /api/kesif/bitir`, toast "You returned to your own world", full page reload after 700 ms.
3. `#abDunya` stats (ellipsized): single world "<world name> · Epoch N · year Y · S sons · E entities"; multi-world "Cosmos · W worlds · Epoch N · …". E = sum of `G.S.sayim` (counts per entity type).
4. Shortcut hints (`.ab-kisa`, right-aligned, hidden on narrow screens): button "? help" (`[data-yardim]` → Help drawer) · "1–9 tabs" · "⌘K search" · "Alt+←→ back/forward" · "Esc close" · link "The world's book" (/kitap, new tab) · link "Codex (Markdown)" (`/api/kodeks.md`, download) · link "Style guide" (/stil.html, new tab).
5. `#liveReopen` "Live feed" button (pulse icon), visible only when the live panel is closed → reopens it. On narrow screens it floats bottom-right above the tab bar (z-index 61).

---

### 2.4 Refresh loop, realtime and action plumbing (core/yenile.js)

#### 2.4.1 `act(fn, okMsg)` — standard mutating action wrapper
1. Finds the button clicked within the last 600 ms (`G.sonTik`, captured by a global capture-phase click listener; buttons inside forms excluded) and locks it (`disabled`, `data-mesgul`, `aria-busy`).
2. Reads the newest god ledger entry id: `GET /api/defter?kim_tip=t&limit=1`.
3. Runs `fn()`, shows toast `okMsg` if given, awaits a full `refresh()`.
4. Undo offer: re-reads `GET /api/defter?kim_tip=t&limit=1`; if a new, not-undone god entry appeared, shows a toast with action button "Undo" (`Geri al`) for 7 s → `POST /api/defter/:id/geri-al`, toast "Undone" or "Undone; N conflicts skipped", refresh.
5. On error: red toast with `e.message` (6.5 s). Always unlocks the button (unless the refresh re-rendered it).
Returns `fn()`'s result or `true` (callers use the truthiness to close drawers).

Declarative forms (`core/formlar.js`, used by Settings): `<form data-post="/api/..." data-mesaj="..." [data-onay] [data-sifirla]>` — body built from named fields (dotted names nest; number/range → number, checkbox → boolean); optional two-click confirm on the submit button; posts via `act()`. Browser validation bubbles are replaced with localized messages (required, "Enter a number", "Must be at least X", "At most X[; this limit is a World Rule (path): raise it in Settings → Game → World Rules]" when the input has `data-kural`, etc.).

#### 2.4.2 Full refresh `refresh({arka})`
Coalescing: concurrent calls share one in-flight promise; a call during flight sets "again" so it loops once more. `yenile()`:
1. `GET /api/state` → `G.S`, `G.K = G.S.kurallar`.
2. Rule cache: if the epoch changed (or first load), reload `GET /api/denge` into the `kural()` cache and the cost table `G.DENGE` (`{path: value}`).
3. No world (`!G.S.dunya`) → show Creation screen, stop.
4. Hide Creation; invalidate Atlas full-list cache if the epoch changed and Atlas isn't the active tab.
5. Load name dictionary (`adlariYukle`, section 17) if counts changed.
6. Render header (`renderBar`), seed the live-feed source chips if empty, render the active tab (background flag passed through so views can avoid toasts), re-open the open drawer silently (entity drawers only).

#### 2.4.3 Background / incremental refresh
- `arkaYenile()` (called by SSE handlers): debounce 350 ms, then waits until the user has been idle ≥1200 ms (any pointerdown/keydown/wheel/touchstart updates `G.sonEtkilesim`) and no pointer is held (retry every 400 ms) before running. Runs `artimliYenile()` unless a full refresh was requested (`arkaTamYenile()` → `refresh({arka:true})`).
- `artimliYenile()` → `GET /api/degisim?surum=<G.S.surum>` (serialized via a promise chain). Response fields used:
  - `tam` (true → full refresh), `surum` (new version token).
  - `varliklar[]` / `varlik_silinen[]` (entity rows changed / deleted ids), `ogullar[]` / `ogul_silinen[]`, `kronik_yeni` (count of new chronicle rows), `baglar` (links changed flag), `dunyalar` (worlds changed), `dunya` (world row changed), `iliskiler` (son relations changed), `yabanci[]` (foreign god ids changed).
  - `durum {mesgul, isler[], sira[], gorsel_uret, tahmin, bildirim_okunmamis, yarim_cag, tanri_oz, cag}`.
- Application (`degisimUygula`):
  - `durum`: compares busy state and job/queue keys; updates `G.S.isler/sira/mesgul/bildirim_okunmamis/yarim_cag/tahmin`, essence; if `durum.cag` differs → full refresh; re-renders header. If busy-ness or the job list changed, re-renders the tab and open drawer (so "disabled while busy" buttons update) and refreshes the Network health boxes.
  - `iliskiler` → refetch `GET /api/iliskiler`.
  - `dunyalar`/`dunya` → refetch `/api/state` and copy only the world fields (`dunyalar, dunyalar_durum, yabanci_sayi, iklim, cagin_yildizi, tanri_ruh, kader_borc, iplikler, yaratici_inanc, yaratici_kult`, plus merged `dunya`) — `core/durum-yama.js`; if the epoch changed → full refresh.
  - `kronik_yeni` (without world change) → refetch open threads `GET /api/iplikler` (filtered to `durum=='acik'`, sorted by id).
  - Sons/entities patched row-by-row into `G.S.ogullar` and the Atlas cache; per-type counts `G.S.sayim` adjusted for rows entering/leaving counted statuses (`kanon`, `olu`, `gerceklesti`).
  - Name dictionary reloaded only when a name changed, something was deleted, or foreign gods changed.
  - Active tab re-rendered only if relevant: panteon (sons/entities/chronicle/relations/world/threads), atlas (entities/sons/worlds; Atlas gets a targeted set of changed ids), harita (entities/links/worlds), ag (entities/sons/links/worlds), kozmos (worlds/world/sons), kronik (chronicle/worlds), sozluk (entities), galeri (never), dualar (sons/chronicle). A change in world count re-renders any tab.
  - Open drawer refreshed silently only if its record changed (entity/son id match, creator drawer on chronicle/son/world change, foreign god on its id/chronicle/links).
- SSE (`/api/olaylar`, EventSource, auto-reconnect after 2 s) kinds that touch these screens: `serbest` (job ended) → `arkaYenile`; `bitti` (a son's turn ended) → `arkaYenile`; `cag_bitti` → toast "Epoch N began", refresh measurements, `arkaTamYenile`; `dunya_dogdu`, `konsey` → `arkaYenile`; `bildirim` → unread +1 and header re-render (achievements also go to the feed); `yeni_ogul` / `yukselis` → son reveal overlay; `vahiy` → toast "<name> appeared" and opens the new entity; `genesis_bitti` → full refresh; `hata` → red toast (and re-enables the Creation button if no world yet); `toplu_derin` → batch-deepening panel update; `gorsel_*` → image generation panel; `ag_onarim` → network repair boxes; `mesgul` → busy state and Stop button.

---

### 2.5 Creation screen / onboarding (`#genesis`, views/genesis.js, src/sihirbaz.js)

Purpose: shown full-screen (z-index 60, radial dark gradient) whenever `GET /api/state` returns no `dunya`. Single-page form (not multi-step); optional template + settings live in a collapsible block.

Layout (`form#genesisForm.genesis-card`):
1. Eyebrow "Creation" (`Yaratılış`), 56 px logo.
2. H1 "You are alone in the void." (`Boşlukta yalnızsın.`)
3. Lede: "Give a name and a seed. From this seed I will grow the world's cosmology, its language, your likeness, its first land, the first star you hang in the sky, and your first three sons. Your sons: one Common, one Rare, one Legendary."
4. "Name of the god" (`Tanrının adı`) — `#gTanri`, required, maxlength 40, placeholder "Aeron".
5. "World seed" (`Dünya tohumu`) — `#gTohum` textarea, required, 4 rows, placeholder "A world made of salt; the seas are fresh, the land is salty. The dead crystallize and keep their last thoughts inside them."
6. "Tone (optional)" (`Ton`) — `#gTon`, maxlength 120, placeholder "melancholic and strange, folkloric, bloody, cosmic horror…".
7. `#sihirbaz` — wizard block (below).
8. Submit "Create the world" (`Dünyayı yarat`, primary, big).
9. Note `#gNote`: "Creation is a language-model call and takes between a few seconds and a minute."

#### 2.5.1 Wizard block (`GET /api/sihirbaz` → `{sablonlar, secenekler}`; fetched once and cached; on failure the block is empty)
- Eyebrow "Templates — optional: fills in the seed, tone and settings".
- Template buttons (`role=radiogroup`, each `role=radio`, title = template seed): bold name + tone line. Clicking selects (class `on`) or deselects (click again). Selecting overwrites the seed and tone inputs and the settings fields with the template values.
- Collapsible "Settings: magic, darkness, technology, language, cosmos" (`details[data-k=sihirbaz-ayar]`) containing:
  - Magic (`Büyü`) — range 0–100 with live `<output>`, default rule `SIHIRBAZ.buyu` (50).
  - Darkness (`Karanlık`) — range 0–100, default `SIHIRBAZ.karanlik` (50).
  - Technology (`Teknoloji`) select, default `demir`.
  - Language texture (`Dilin dokusu`) select, default `karisik`.
  - Cosmos (`Kozmos`) select, default `tek`.
  - First peoples (`İlk halklar`) number, min 1, max `SIHIRBAZ.halk_en_cok` (5, `data-kural` so the validation message points to the rule), default `SIHIRBAZ.halk` (2).

Options (`SECENEKLER`), fully translated:

| Field | key | English label (Turkish) |
|---|---|---|
| technology | tas | stone age (taş çağı) |
| | tunc | bronze age (tunç çağı) |
| | demir | iron age (demir çağı) |
| | ortacag | middle ages (ortaçağ) |
| | ronesans | renaissance (rönesans) |
| | buhar | steam and gunpowder (buhar ve barut) |
| language | akici | flowing, vowel-rich, soft (l, m, n, y) (akıcı, ünlüsü bol, yumuşak) |
| | sert | hard-consonant, short-syllabled (k, t, g, r) (sert ünsüzlü, kısa heceli) |
| | girtlak | guttural, deep-throated (h, ğ, q, kh) (gırtlaksı, derinden) |
| | islikli | sibilant, fricative (s, ş, z, ç) (ıslıklı, sürtünmeli) |
| | uzun | long, agglutinative, many-syllabled (uzun, eklemeli, çok heceli) |
| | karisik | free (serbest) |
| cosmos | tek | single world (tek dünya) |
| | kucuk | small cosmos (1 + `SIHIRBAZ.kucuk_kozmos` worlds; default 2) (küçük kozmos) |
| | buyuk | large cosmos (1 + `SIHIRBAZ.buyuk_kozmos` worlds; default 3) (büyük kozmos) |

Templates (`SABLONLAR`), fully translated:

| key | Name | Tone | Magic | Dark | Tech | Language | Peoples | Cosmos | Seed |
|---|---|---|---|---|---|---|---|---|---|
| karanlik_fantazi | Dark fantasy (Karanlık fantazi) | gloomy, merciless, hope comes at a price | 60 | 80 | iron | guttural | 3 | single | A world built where the gods once died, on top of their corpses; every bounty comes from a rotting. |
| mitoloji | Mythic age (Mitolojik çağ) | epic, solemn, full of prophecies | 70 | 40 | bronze | flowing | 3 | single | Continents born from the sea and mountains that hold up the sky; every river has a name, every name a price. |
| kozmik_korku | Cosmic horror (Kozmik korku) | uneasy, quiet, in the shadow of incomprehensible things | 50 | 90 | steam | sibilant | 2 | small | A cosmos where something behind the sky is waking and the stars go out one by one. |
| masal | Fairy tale (Masal) | warm, strange, wise and a little sad | 85 | 25 | middle ages | long | 4 | single | A world where animals talk, forests move around, and dreams are taxed. |
| yildiz_mitosu | Star myth (Yıldız mitosu) | vast, full of wonder, on a cosmic scale | 55 | 45 | renaissance | flowing | 3 | large | A cosmos where star-wind fills ships' sails and worlds are strung on a thread like beads. |
| kum_ve_kul | Sand and ash (Kum ve kül) | harsh, arid, honourable | 35 | 60 | bronze | hard | 3 | single | A world where the sun once fell and left a desert; where water is worth more than money and the ashes speak prophecies. |
| primordial_dawn | Primordial dawn (İlk şafak) | raw, wondrous, everything happens for the first time | 75 | 35 | stone | free | 5 | single | A young world still warm from its making; the first fires are being lit, the first words spoken, and every hill waits for a name. |
| crowns_and_knives | Crowns and knives (Taçlar ve hançerler) | cunning, political, every oath hides a blade | 12 | 55 | medieval | hard | 4 | single | A world where magic has all but faded and power lives in bloodlines, marriages and whispered debts; every throne is one betrayal from falling. |
| drowned_world | Drowned world (Batık dünya) | salt-worn, restless, ruled by the tides | 55 | 50 | iron | sibilant | 3 | single | A world where the sea swallowed the continents long ago; peoples live on scattered islands, reefs and floating towns, and every map is wrong by the next tide. |
| long_winter | Long winter (Uzun kış) | stern, enduring, warmth must be earned | 40 | 65 | iron | guttural | 3 | single | A world whose sun has dimmed for a thousand years; the ice creeps further south each winter and the peoples burn their histories to stay warm. |
| after_the_fall | After the fall (Çöküşten sonra) | elegiac, scavenging, haunted by a greater past | 45 | 70 | medieval | long | 3 | single | A world built on the ruins of a civilization far greater than any living one; its towers still hum, its roads lead nowhere, and no one remembers how its wonders were made. |
| sky_islands | Sky islands (Gök adaları) | airy, adventurous, hopeful | 70 | 30 | renaissance | flowing | 3 | small | A cosmos of shattered worlds whose fragments drift on rivers of wind; peoples sail between the islands on kite-ships, and falling past the edge is the oldest fear. |
| age_of_engines | Age of engines (Makineler çağı) | curious, inventive, bright with possibility | 30 | 30 | steam | free | 4 | single | A world where the first engines have just learned to breathe; tinkers rival priests, railways cut through sacred forests, and every invention wakes an old spirit. |

The last seven templates are new in Weavers of the Void and have no legacy key; their key is the stored `GenesisTemplate` value.

#### 2.5.2 Submit
`POST /api/genesis` body `{tanri_adi, tohum, ton, sihirbaz: {buyu, karanlik, teknoloji, dil, kozmos, halk, sablon?}}`. On submit: button disabled, note becomes "The world is being thought… (about a minute)". Server: sanitizes wizard values (`sihirbazTemizle`: clamps numbers, whitelists option keys, fills blanks from the template, tone ≤300 chars, seed ≤2000 chars); 400 "God name and world seed are required."; 409 "A world already exists." / "Creation is already running."; runs creation in the background emitting SSE `mesgul {tur:'genesis'}`, then `genesis_bitti` (client does a full refresh which hides the screen) and a system line "The first mortal peoples are awakening…". On SSE `hata` before a world exists: button re-enabled, note "Try again." On a page reload mid-creation (`G.S.mesgul.tur === 'genesis'`) the button stays disabled with the "being thought" note.
Server-side effects of the wizard: settings are appended to the creation prompt (`sihirbazMetni`: "Magic density X/100: the world is {very/ / moderately / slightly / almost not} magical…", darkness, technology, language texture, cosmos) and after creation region magic/danger are pulled toward the chosen magic/darkness by `SIHIRBAZ.cekim`% (default 50); extra worlds per cosmos size.

---

### 2.6 Settings drawer (`openDrawer('ayar')`, views/ayarlar.js)

Opened by the header sliders icon (`#btnAyar`). Header: eyebrow (gear) "Settings" (`Ayarlar`), title "The order of the world" (`Dünyanın düzeni`). Below: segmented tab bar (`role=tablist`) with four tabs; selection persisted as `aerona.ayarSekme` (default `gorunum`). All sections are rendered into the DOM at once; non-selected sections are `hidden`. Switching scrolls the drawer to top.

| Tab key | Label | Icon |
|---|---|---|
| gorunum | Appearance (Görünüm) | eye |
| oyun | Game (Oyun) | gear |
| kayitlar | Records (Kayıtlar) | book |
| veri | Data (Veri) | backup |

On open `bindAyar` immediately loads (regardless of tab): measurement (`/api/olcum`), World Rules (`/api/denge`), health (`/api/saglik`), batch deepening (`/api/toplu/derin`), image generation (`/api/gorsel-uret`), network health (`/api/ag/saglik`), backups (`/api/yedekler`).

#### 2.6.1 Appearance tab
**a. Appearance and accessibility** (`Görünüm ve erişilebilirlik`, "remembered in this browser"), persisted as `aerona.gorunum {kontrast, yazi, hareket}`, applied at boot and on change:
- Checkbox "High contrast" — "brighter text, stronger lines and focus ring" → `html[data-kontrast]`; also clears the cached canvas colour table so Network/Map canvases re-read colours.
- Checkbox "Reduce motion" — "transitions and pulse animations stop" → `html[data-az-hareket]`. `hareketAz()` is also true when the OS `prefers-reduced-motion` is set.
- "Text size" segmented radio: Small 0.9 / Normal 1 / Large 1.15 / Very large 1.3 → CSS variable `--yazi`.

**b. Live feed and sound** (`Canlı akış ve ses`, "remembered in this browser"):
- "Live feed panel open" — "the event feed on the right; starts closed on narrow screens so it doesn't cover content" (`aerona.canliAcik`, default open if viewport > 1100 px).
- "Ambient sound" — "a low, synthesized hum; starts after the first click on the page" (`aerona.ortamSes`).
- "Feed sounds" — "every kind of world event plays a short tone" (`aerona.akisSes`).
- When feed sounds are on: "Which events make a sound:" checkbox per category (stored inverted as muted set `aerona.akisSessiz`): Ships and journeys (`yolculuk`), Gates and roads (`kapi`), Leakage and horror (`sizinti`), Wars (`savas`), Disasters (`afet`), Sky events (`gok`), Birth and death (`hayat`), Civilization (`medeniyet`), Other world events (`dunya`). Categories come from `G.K.AKIS_KATEGORILERI` + `dunya`.

**c. Guide and shortcuts** (`Rehber ve kısayollar`): "The first-epochs guide and the per-epoch to-do box sit at the top of the Pantheon; if you closed them, you can reopen them here. For shortcuts press ?." Buttons: "Show the guide and to-dos again" → sets `aerona.rehberKapali=false`, `aerona.yapilacakKapali=0`, toast "The guide will reappear in the Pantheon", closes drawer; "Shortcuts and terms" → Help drawer.

#### 2.6.2 Game tab (in order)
**a. Models** (`Modeller`): "Which job is done by which Claude model. Haiku is fastest, Sonnet balanced, Opus deepest but slowest. All are charged to the Max subscription." Grid of label + select, one per `G.K.MODEL_ETIKET` key; options `G.K.MODELLER` = haiku/sonnet/opus displayed capitalized ("Haiku"); current value `G.S.modeller[key]` (server default for every key: haiku). Keys: per rarity — Common sons (`yaygin`), Elite sons (`seckin`), Rare sons (`nadir`), Epic sons (`destansi`), Legendary sons (`efsanevi`), Mythic sons (`mitik`); per job — Fate and chronicler (`kader`), Creation (`yaratilis`), Son summoning (`cagirma`), Deepening (`derinlik`), The god's revelation (`vahiy`). "Save" → `POST /api/ayar {modeller:{key:model}}` (server ignores unknown keys/models) via `act()`, toast "Models saved".

**b. World Rules** (`Dünya kuralları`, "costs, essence regeneration, action points, summoning probabilities") — see section 6.6.

**c. Mortal agents** (`Ölümlü ajanlar`): "Each epoch, after the sons, how many of the most powerful mortal communities or intelligent creatures play their own turn (0 = none; no upper limit). They too produce, build, develop language, explore, trade and wage war." Multi-world adds: "**It is the total for the whole cosmos:** distributed among worlds according to their candidates; you can give a world's share manually via Cosmos → that world's card → 'Mortal agents'."
- Number input (min 0) = `dunya.olumlu_sayisi` ?? rule `OLUMLU_AJAN.varsayilan` (4); "Save" → `POST /api/ayar {olumlu_sayisi}` via `act()`, toast "Saved".
- Form "Thinking at once" (`Aynı anda düşünen`): number min 1 = `dunya.olumlu_paralel` (default 1) → `POST /api/ayar {olumlu_paralel}`; help: "How many mortals think at once (at least 1); more makes the epoch faster but fills the Max quota sooner."
- Note: "Awakening new peoples on empty lands moved to the 'Epoch' box in the Pantheon."

**d. Sons and council** (`Oğullar ve konsey`, "+ for the whole cosmos" in multi-world): form → `POST /api/ayar`:
- "Distribution of sons across worlds" select `ogul_dagitim`: "Automatic: they go to godless worlds by themselves" (`otomatik`) / "Manual: only you send them" (`elle`).
- "Council convenes by itself" number `konsey_sikligi` (min 0, default rule `KONSEY.siklik_varsayilan` 4) + "once every N epochs (0: never)".
- "Save", toast "Saved".

**e. Fate** (`Kader`): checkbox "Fate rejects inconsistent creations at the end of the epoch" — checked when `dunya.kader_modu === 'otomatik'`; change → `POST /api/ayar {kader_modu: 'otomatik'|'kapali'}`, toast "Setting saved".

**f. Image prompts** (`Görsel promptları`): "Everything that can have an image gets an English, photorealistic prompt. Right now N entities lack a prompt; they are completed automatically at the start of each epoch." (`G.S.promptsuz`). Button "Write all missing prompts now" → `POST /api/promptlar` via `act()`, toast "Writing prompts…", closes drawer. Disabled when busy or when `promptsuz` is 0 (tooltip "No entity is missing a prompt").

**g. Batch deepening** (`Toplu derinleştirme`, views/toplu.js): "All records not yet deepened[ (in all worlds)] are deepened one by one in order of importance. Each record is one model call; it uses your subscription. How many records run at once and the wait between them are set in World Rules → **Batch jobs**." Data: `GET /api/toplu/derin` → `{calisiyor, toplam, bitti, hata, atlandi, kalan, bekleyen, adsiz, suan[{ad}], gunluk[{zaman, seviye, metin}]}`; average deepening time from `GET /api/olcum` step "Derinleştirme" (`ort_ms`), fetched once.
- Not running: primary button "Deepen N records" (disabled + "All deepened" / title "No undeepened records left" when `bekleyen` = 0); two-click confirm: "Are you sure? N model calls (≈ duration)". Then `POST /api/toplu/derin/baslat {}`, toast "Batch deepening started". Side text: "estimated time ≈ X" or "no measured deepening yet for a time estimate".
- Running: danger "Stop" → `POST /api/toplu/derin/durdur {}`, toast "Stop requested; it will stop when the current record finishes"; chip "running"; text "processed / total · N done · N errors · remaining ≈ X".
- If `adsiz > 0`: button "Name N unnamed records" → `POST /api/adlandir {}`, toast "Unnamed records are being named"; note "Records the world engine opened with a temporary name; they are also named automatically at epoch end, on startup and before batch deepening."
- Progress bar (`role=progressbar`, % = (done+error+skipped)/total) when running or total > 0.
- "Now: **A**, **B**" (currently processed).
- Log (`.toplu-gunluk`, mono, last 200 lines, auto-scrolls to bottom): "HH:MM:SS message", coloured by level (info none, done green, warning amber, error red).
- Realtime: SSE `toplu_derin` events merge into the panel and append `e.satir` to the log.

**h. Image generation** (`Görsel üretimi`, from core/gorsel-uret.js): "All records without an image (creator, sons, foreign gods, worlds, then entities by importance) are imaged one by one with the local model on this computer. **Existing images are not touched**: only those with no image at all are handled; the generated image becomes the cover. An entity without a prompt gets its prompt written first. Size, step count and auto-start at epoch end are set in World Rules → **Image generation**." Data `GET /api/gorsel-uret` → `{kurulu, model, ayar{genislik, yukseklik, adim}, hazir, eksik, toplu{calisiyor, oto, toplam, bitti, hata, atlandi}, suren{ad,...}, sira[{ad}], gunluk[]}`. Status line: "Model: <name> · W×H, N steps · in memory, ready / loaded into memory on the first image" or red "The local image model is not installed (mflux not found)." Start button "Generate N missing images" (disabled: model not installed / "No record without an image left" / exploration mode), two-click "Are you sure? N images will be generated" → `POST /api/gorsel-uret/toplu/baslat {}`. Running: "Stop" → `/toplu/durdur`; chip "running[ · epoch end]"; counts; progress bar; current item with its own progress; "Queued: first 5 names and N more images"; log as above.

**i. Network repair** (`Ağ onarımı`, from views/ag.js; shared with the Network tab): explanation of "Repair loose ends" (rule-based links only from data) and "Let Fate suggest links" (evidence-based links with rationale; renames or closes vague "related" links). Data `GET /api/ag/saglik`: chips "N nodes · N links (N historical)", "avg. X links (median Y)", "main component P% · N components" (green if ≥ `AG.ana_obek_iyi` 95), "N isolated" (amber if >0), "N single-linked", "N related · N without description" (amber if >0); "Weakest:" linked list. Buttons: "Repair loose ends" → `POST /api/ag/onar {}` (toast "N loose ends linked[, N vague links named]" / "No loose ends to repair"); "Let Fate suggest links" → `POST /api/ag/kader {}` (disabled with spinner "Fate is looking at the network…" while job `ag:kader` runs); "Full repair" (two-click "Are you sure? Repair the whole network") → `POST /api/ag/kader {tam:true}`; while running "Stop" → `POST /api/ag/kader/durdur`. Also "N events, legends or traditions mentioned in the chronicle with unlinked participants are waiting for Fate", limits text (`AG.oneri_tavan` 3 links per record, `AG.tekrar_cag` 10 epochs), and "Recent repairs" log or "No repair yet in this session; it runs automatically at epoch end."

**j. Cheat: divine essence** (`Hile: tanrısal öz`): "The amount you enter is added to your divine essence. Not written to the chronicle." Number input min 1, max = rule `SUNUCU.hile_oz_tavan` (1,000,000; tooltip "At most X at once (World Rules → The god's actions)"), default 1000. "Add" → `POST /api/hile/oz {miktar}` → response `tanri_oz`; updates "Now: **N**", toast "+N essence added", refresh. (Not via `act()`: no lock, no undo.)

#### 2.6.3 Records tab
- **Action ledger** (`Eylem defteri`): "Changes each action wrote to the world, and undo, now live in the **Your records** button in the header (with your notes and bookmarks)." Button "Open the action ledger" → Records drawer.
- **Measurement** (`Ölçüm`, "language model calls in recent epochs: time, tokens, cost, errors") — section 11.
- **The world's book** (`Dünyanın kitabı`): "The whole world as a single printable book: cosmology, pantheon, peoples and their faiths, languages, epochs and councils. You can save it as PDF from the browser. A single son's or entity's page is printed with 'Print page' on its own page." Link button "Open the book" → `/kitap` new tab.
- **Codex (Markdown)** (`Kodeks`): "A single Markdown encyclopedia of the whole world: cosmology, pantheon, geography, legends, chronicle and image prompts." Link "Download the codex (Markdown)" → `/api/kodeks.md`.

#### 2.6.4 Data tab
**a. Share the world** (`Dünyayı paylaş`): "The whole world becomes a single `.aerona` file: database and images. You can put someone else's world in place of yours, or browse it read-only."
- Links: "Export (with images)" → `/api/dunya/disa-aktar` (download); "Without images" → `?gorseller=0`.
- Import form: file picker component (accept `.aerona,application/gzip`, title "Choose a .aerona file", hint "Click or drag the file here · .aerona", drag-and-drop) + "How should it open?" select: "Exploration: browse read-only, your own world waits aside" (`kesif`) / "Replace: take this world's place" (`degistir`). When Replace is chosen a field appears: "Type **DEĞİŞTİR** to replace" (rewrite: an English word, e.g. REPLACE). Submit "Import": validation toasts "Choose a .aerona file." / "Type DEĞİŞTİR to replace."; button shows spinner "Importing…"; `POST /api/dunya/ice-aktar?mod=<kesif|degistir>[&onay=DEĞİŞTİR]` with raw file body (`application/octet-stream`). Success toast "<name> opened read-only" / "<name> imported", page reload after 900 ms. Note: "A safety backup of the current world is taken before replacing."
- In exploration mode: amber chip "Exploration mode: <name>" + "Return to my world" button.

**b. Backups** (`Yedekler`): "Before every epoch starts, a full copy of the world is taken into the `data/yedekler` folder; the last *YEDEK.cag* (10) epoch backups are kept (every *YEDEK.onluk*-th (10th) epoch's is always kept). When you restore a backup a safety backup of the current state is taken first, so you can undo the restore too. Uploaded images stay as files."
- List from `GET /api/yedekler` → `[{dosya, boyut}]`: each row: filename (mono, truncated), size "N KB" (bytes/1024 rounded), link "Download" (`/yedek/<file>`, title "Database only (.db)"), ghost link "With images" (`/yedek/<file without .db>.aerona`, "Shareable .aerona file with its images"), button "Restore". Empty: "No backups yet." Loading: "Loading…".
- Restore: inserts one inline confirm box under the row (only one at a time): "The world returns to the moment **<file>**. Type **GERİ YÜKLE** to confirm." + input + danger "Restore" + "Cancel". Wrong text → toast "Type GERİ YÜKLE to confirm." → `POST /api/yedek/geri {dosya, onay:'GERİ YÜKLE'}` via `act()`, toast "The world returned to the backup", closes drawer.
- "Take a backup now" → `POST /api/yedek` → `{dosya}`, toast "Backup taken: <file>", re-lists.

**c. Health** (`Sağlık`, "server, database and disk") from `GET /api/saglik` (the whole section is removed silently if the endpoint fails). Key/value list:
- Status: chip "good" (green) or "warning"/"error" (red) from `durum` (`ok`/`iyi` → good); extra amber chip "read-only" if `salt_okunur`.
- Version: `surum · Node <node> · port <port>`.
- Uptime: `calisma_sn` → "D days H h" / "H h M min" / "M min S s".
- Database: `db.dosya · size (+wal journal) · integrity: sound/not done/<text>` (`quick_check` "ok" → "sound"). Sizes: >1 MiB "X.Y MB" else "N KB".
- Backups: "N backups · last: <file> <time>" or "none yet".
- Running job: `mesgul.tur` or "N content jobs" or "none".
- Log file: `gunluk` path (mono).
- Recent errors: collapsible "N recent errors" (last 5, mono) or "No recent errors."

**d. Reset the world** (`Dünyayı sıfırla`, danger box): "The whole world, sons, chronicle and uploaded images are permanently deleted. Type **SIFIRLA** to confirm." Input + danger "Delete". Wrong text → toast "Type SIFIRLA to confirm." → `POST /api/sifirla {onay:'SIFIRLA'}` via `act()`, toast "World deleted", closes drawer (refresh then shows the Creation screen). Server refuses while a job runs; it actually takes a safety backup (`sifirlama-oncesi`) and copies images to the backup folder first (UI text says "permanently").

#### 2.6.5 Settings: empty/loading/error states
Every async box shows "Loading…" first and replaces itself with a red error line (`e.message`) on failure, except Health (removed) and Backups (toast).

#### 2.6.6 World Rules editor (`Dünya kuralları`, `#dengeKutu`)

Purpose: edit every tunable balance number of the game (the old codebase's rule is "no un-tunable constant": every engine/agent/UI magic number is registered via `tanimla()` and editable here).

**API**
- `GET /api/denge` → array of `{yol, ad, grup, min, max, deger, varsayilan, degisti}`:
  - `yol` path like `SAVAS.yorgunluk` (namespace in caps + key; legacy tables also expose nested paths like `RARITIES.nadir.stat.0`, `GUC_SEVIYELERI.1`).
  - `ad` Turkish label; `grup` group name; `min` structural minimum (enforced); `max` *recommended* maximum (not enforced); `deger` current value; `varsayilan` factory default; `degisti` true if a saved override differs from default.
  - All values are integers; probabilities are stored as percents.
- `POST /api/denge` body `{degisiklikler: {path: integer|null}}` and/or `{sifirla: true}` (reset all overrides first). `null` removes the override (back to default). Values are rounded; errors: unknown path "Unknown rule: path", non-numeric "path must be a number.", below min "path must be at least min.", unsafe integer "path is too big.". Setting a value equal to the default removes the override. Overrides are persisted as JSON in `dunya.denge_ayar` and applied in place to the live rule objects immediately (engine, tools and UI see the change at once). Returns the updated list.

**Rule sources and grouping** (`src/denge.js`): the list is `alanlar()` in this order: legacy tables COSTS → DENGE → KOZMIK_BEDEL → MUDAHALE_BEDEL → OLUMLU_AJAN → OZELLIKLER (creature trait war bonus) → SEYAHAT_YONTEMLERI (duration, danger) → GUC_SEVIYELERI → every `tanimla()`-registered rule in module-load order → RARITIES (per rarity: action points, essence regen, stat min/max at summon, power cap, max turns, summon weight except mythic). Group = the registered `grup` (5th tuple element, default "Other"/`Diğer`), else the legacy table's fixed group. The UI groups by `grup` in order of first appearance.

Groups (exact, from a live `GET /api/denge` against a real world: **3,323 rules in 54 groups**, listed in the order the editor shows them, i.e. order of first appearance; every key is unique):

| # | English group | Turkish original | Rules |
|---|---|---|---|
| 1 | God and son costs | Tanrı ve oğul bedelleri | 56 |
| 2 | Major actions and essence | Büyük eylemler ve öz | 12 |
| 3 | Cosmic actions | Kozmik eylemler | 11 |
| 4 | Intervention in the mortal world | Ölümlü dünyaya müdahale | 4 |
| 5 | Mortal agents | Ölümlü ajanlar | 95 |
| 6 | Creatures | Yaratıklar | 134 |
| 7 | Cosmos and travel | Kozmos ve seyahat | 193 |
| 8 | Backups | Yedekler | 5 |
| 9 | Population and growth | Nüfus ve büyüme | 177 |
| 10 | Religion and language | Din ve dil | 161 |
| 11 | War and diplomacy | Savaş ve diplomasi | 305 |
| 12 | Heroes and mortals | Kahramanlar ve ölümlüler | 232 |
| 13 | Rarity classes | Nadirlik sınıfları | 100 |
| 14 | Creator and essence | Yaratıcı ve öz | 125 |
| 15 | Intervention | Müdahale | 51 |
| 16 | Epoch flow | Çağ akışı | 6 |
| 17 | Notifications | Bildirimler | 3 |
| 18 | Interface (incl. server page sizes) | Arayüz | 34 |
| 19 | Context budgets (prompt character budgets) | Bağlam bütçeleri | 102 |
| 20 | Son tools | Oğul araçları | 182 |
| 21 | Doomsday | Kıyamet | 38 |
| 22 | Language and names | Dil ve adlar | 54 |
| 23 | Agents and model | Ajanlar ve model | 39 |
| 24 | Reputation | İtibar | 60 |
| 25 | Opportunities | Fırsatlar | 26 |
| 26 | Atlas archive | Atlas arşivi | 19 |
| 27 | Death and resurrection | Ölüm ve diriliş | 53 |
| 28 | The Beyond (afterlife) | Ötesi | 86 |
| 29 | Cosmic horror | Kozmik korku | 92 |
| 30 | Civilization | Medeniyet | 161 |
| 31 | Economy | Ekonomi | 195 |
| 32 | Chronicle | Kronik | 11 |
| 33 | Sky | Gök | 60 |
| 34 | Exploration | Keşif | 39 |
| 35 | Foreign gods | Yabancı tanrılar | 21 |
| 36 | The god's power | Tanrının gücü | 76 |
| 37 | Mortals | Ölümlüler | 4 |
| 38 | Council | Konsey | 16 |
| 39 | Goals and achievements | Hedefler ve başarımlar | 48 |
| 40 | Records | Kayıtlar | 4 |
| 41 | Creation wizard | Yaratılış sihirbazı | 7 |
| 42 | Network (knowledge graph) | Ağ | 20 |
| 43 | Fate and chronicle | Kader ve kronik | 56 |
| 44 | Son summoning and birth | Oğul çağırma ve doğum | 13 |
| 45 | Creation | Yaratılış | 8 |
| 46 | Awakening of peoples | Halkların uyanışı | 33 |
| 47 | Content jobs | İçerik işleri | 24 |
| 48 | Codex and guide | Kodeks ve rehber | 5 |
| 49 | Cosmos | Kozmos | 3 |
| 50 | The god's actions | Tanrının eylemleri | 33 |
| 51 | Batch jobs | Toplu işler | 6 |
| 52 | Image generation | Görsel üretimi | 10 |
| 53 | Search | Arama | 11 |
| 54 | Server | Sunucu | 4 |

A fallback group "Other" (`Diğer`) exists for rules registered without a group; none occur.

**Layout of the editor**
1. Intro: "Numbers you change take effect immediately: the costs in the interface, the sons' tools and the world engine see the new value at the same time. [**N** rules differ from the default.]"
2. Toolbar: search input (`type=search`, placeholder "Search rules (e.g. doomsday, war, plague)…"), counter "N rules · G groups" (when filtering: "shown / total rules"), checkbox "Only changed" (`Yalnızca değişenler`). Search text and checkbox persist in module memory for the session (not localStorage).
3. `form#dengeForm`: one collapsible `<details>` per group, summary = group name + "N changed" (muted) if any; a group is open by default if it contains a changed rule (open state also preserved across re-renders by key `denge-<group>`).
4. Inside each group a responsive grid (`repeat(auto-fill, minmax(320px, 1fr))`), each row `label.denge-alan` = 4 columns `[label | 90px number | 34px | reset]`:
   - Label: `ad` with snake_case keys humanized (`duzyazi`), clamped to 3 lines, tooltip = rule path. Changed rows: label bold in legendary colour, input border tinted.
   - Number input: `name=path`, `min=min`, `value=deger`, `data-ilk` = initial value, `data-onerilen=max`, tooltip "Recommended range min–max; you can go above it". Values above the recommended max are accepted but the input gets the warning colour (`c-uyari`) live as you type.
   - Reset button (only when changed): undo icon + the default value in mono; tooltip "Reset to default (X)"; click → `POST {degisiklikler:{path:null}}`, toast "Rule reset to default". Unchanged rows get an empty placeholder span to keep the grid aligned.
5. Footer actions: primary "Save changes" (`Değişiklikleri kaydet`) and danger "Reset all to default" (disabled when nothing changed; two-click: label becomes "Are you sure? All rules will be reset", no timeout) → `POST {sifirla:true}`, toast "All rules reset to default".

**Filtering** (client-side, no re-render): each row has `data-ara` = lower-cased "humanized label + raw label + path". Query matches if contained in that string, or if the group name contains the query (then the whole group shows). "Only changed" hides rows without `degisti`. Groups with no visible rows are hidden; matching groups auto-open while filtering.

**Saving**: submit collects only inputs whose value differs from `data-ilk`; empty input sends `null` (reset). Nothing changed → toast "No rule has changed." Otherwise `POST /api/denge {degisiklikler}` → toast "N rules updated" → reload rule cache (`kurallariYukle(true)`), cost table (`dengeYukle`), full `refresh()`, and re-render the editor. Error → red toast with server message. Load error → red line in place of the editor.

**Where rules are referenced elsewhere**: UI copies cite rules as "World Rules → <group> → <PATH>" (`kuralYeri()` in `core/kural.js`), and number inputs that are capped by a rule carry `data-kural` so validation messages say where to raise the cap.

---

### 2.7 Revelation drawer (`openDrawer('vahiy')`, views/ayarlar.js)
Opened by the header "Revelation" button. Eyebrow "Revelation" (`Vahiy`), title "Create with your own hand" (`Kendi elinle yarat`). Subtitle: "Write an idea; it appears as a single entity tied to the world's language, cosmology and existing entities. Costs *COSTS.vahiy* divine essence."
Panel:
- "Your revelation" textarea `#vMetin` (5 rows, placeholder "In the north of the sky, a pale star that only the dying can see…").
- Grid: "Type" select (`Tür`): "Let Fate choose" (empty) + every `G.K.VARLIK_TURLERI` entry (label `ad`). "Mechanism (if it is a law)" select (`İşleyişi — yasaysa`), only visible when type is empty or `yasa` (law): "Let Fate choose" + keys of `G.K.YASA_MEKANIKLERI` (underscores → spaces; option tooltip = description); the chosen mechanism's description is shown beneath (`#vMekanikAcik`). Multi-world only: "World" select: "Let Fate choose" + worlds, preselected to the header world filter.
- Primary "Reveal" (`Vahyet`) + cost chip; disabled when busy or essence < cost (same tooltip rules as header).
Action: empty text → toast "Your revelation must have content." → `POST /api/vahiy {metin, tur|null, dunya_id|null, mekanik?}` via `act()`, toast "Revelation descending…", marks onboarding step `aerona.adim.vahiy`, closes drawer. The SSE `vahiy` event later toasts "<name> appeared" and opens the new entity drawer.

---

### 2.8 Notifications drawer (`openDrawer('bildirim')`, views/bildirim.js)
Opened by the bell. Eyebrow (chronicle icon) "Notifications", title "News from the world" (`Dünyadan haberler`). Subtitle: "**N** unread." / "All read." + "Deaths, rebellions, prophecies, cosmic events and the prayers made to you collect here."

Data: `GET /api/bildirimler?limit=<SUNUCU.bildirim_sayfa, 60>[&kategori=k][&okunmamis=1][&once=<id>]` → `{liste[], okunmamis, sayilar[{kategori, n, okunmamis}], kategoriler{key:{ad, onem}}, ayar{key:bool}}`. Opening also sets the header unread count. Multi-world also loads entity→world map (`/api/varliklar?durum=tum`).

Layout:
1. Filter row (horizontally scrollable chip group): "All" + one chip per category that has items: icon + name + count "unread/total" (or just total). Filter state `BILDIRIM.kategori` (session memory). Checkbox "only unread". Button "Mark this category read" / "Mark all read" (disabled when nothing unread) → `POST /api/bildirimler/oku {hepsi:true[, kategori]}`.
2. List of `article.bildirim` (classes: `okundu` when read, `onem-<1..4>`, `b-basarim` for achievements): icon; top line = category chip (gold for achievements), world chip (multi-world: target son's/entity's world), "E<cag>" mono with tooltip of local date/time (SQLite UTC timestamp), unread dot; title (link to target when `hedef_tip` ∈ v/o/y/t/d via `data-v/o/yabanci/tanri-ac/rehber`; text processed by `kimlikDuz` — `#id` / `oğul#id` tokens → names); body (if different from title) with `kimlikHtml` auto-linking; right: icon button toggle read/unread ("Mark read" check / "Mark unread" eye) → `POST /api/bildirimler/oku {ids:[id], okunmadi:bool}`, updated in place.
3. Paging: if a page is full, "Older notifications" button → fetches `once=<last id>` and appends; removed when a short page arrives.
4. Empty: icon + "**No notifications match this filter**" + "Pick another category or turn off 'only unread'."
5. Collapsible "Leave yourself a note" (`Kendine not düş`): title input (required, max 90, placeholder "Reminder: reconcile Hesmarak and Nevrahim") + details textarea → `POST /api/bildirimler {baslik, metin}`, toast "Note added", unread +1, re-render.
6. Collapsible "Which events should be notified?": checkbox per category with "importance N" (tooltip "Importance between 1 (low) and 4 (highest)"); note "Categories you turn off never enter the list. Those with importance *BILDIRIM.toast_onem* (3) and above also appear briefly as an on-screen alert (World Rules → Notifications)." Save → `POST /api/bildirimler/ayar {key: bool}`, toast "Notification preferences saved".

Categories (server `src/bildirim.js`; key, English, Turkish, importance, default on, icon): isyan Son rebellion (Oğul isyanı) 3 on; olum Death (Ölüm) 3 on; dogum Legendary birth (Efsanevi doğum) 3 on; kehanet Prophecy fulfilled (Kehanet gerçekleşti) 3 on; kiyamet Doomsday omen (Kıyamet alameti) 4 on; korku Cosmic horror (Kozmik korku) 3 on; savas War (Savaş) 2 on; dua Prayer to you (Sana dua) 2 on; kozmos Cosmic event (Kozmik olay) 2 on; yukselis Ascension (Yükseliş) 2 on; afet Disaster and sky (Afet ve gök) 2 off; cag Epoch ended (Çağ bitti) 1 on; basarim Achievement (Başarım) 2 on; toplum Society, lineage and debt (Toplum, soy ve borç) 2 on; itibar In the sons' eyes (Oğulların gözünde) 2 on; hata System error (Sistem hatası) 3 on; not The god's note (Tanrının notu) 1 on.
Legacy compatibility: a `kozmos` notification whose title starts with "Başarım:" is displayed as an achievement (prefix stripped).
Realtime: SSE `bildirim` increments the badge; the open drawer is not live-updated.

---

### 2.9 Records drawer (`openDrawer('kayit')`, views/kayitlar.js + views/defter.js)
Opened by the header Records button or Settings → Records. Eyebrow "Your records", title "Ledger, notes and bookmarks". Segmented tabs persisted as `aerona.kayitSekme` (default `defter`): "Action ledger" (`Eylem defteri`), "My notes" (`Notlarım`), "Bookmarks" (`Yer imleri`). Switching re-opens the drawer.

#### 2.9.1 Action ledger (Eylem defteri)
Intro: "The changes each action of the sons, the mortals, Fate and you wrote to the world. Tear out a page and its changes are undone."
Data: `GET /api/defter?limit=L[&cag=N][&kim_tip=t|o|v][&kim_id=id]` → `{kayitlar[{id, zaman, cag, kim_tip, kim_id, kim_ad, arac, degisiklik, ozet, geri_alindi, bagimli[{id, kim_ad}], satirlar[{islem, metin}]}], caglar[{cag, n, geri}]}`. Page size `SUNUCU.defter_sayfa` (80), max `SUNUCU.defter_tavan` (300).
Filters (reset paging): Epoch select "All epochs" + "Epoch N · n records[ · g undone]"; Who select "Everyone" / "You (<god name>)" (`t`) / "All sons" (`o`) / each son (`o:<id>`) / "Mortals" (`v`). Note: "Records of the last *DEFTER.sakla_cag* (6) epochs are kept; older ones are deleted at epoch end (World Rules → … → DEFTER.sakla_cag). Undo also refunds spent essence; a hung star also comes down from the sky."
Each `article.defter-kayit` (class `geri` when undone): header "#id · E<cag>" (tooltip date), actor (son link / entity link / bold "god"/"son"/"mortal"), action label via `eylemAdi(arac)` (section 18), world chip (multi-world), chip "N changes", then either chip "undone" or danger button "Undo" (`Geri al`). Summary text with auto-linking. Warning line if dependants: "The next N records touched what this created: #id name, …". Collapsible "Details": list of change lines with chip "added/changed/deleted" (`ekle/guncelle/sil`).
Undo: two-click (no timeout): "Are you sure? Undo" or, with dependants, "The next N records depend on this; undo anyway" → `POST /api/defter/:id/geri-al` (server 409 while an epoch runs: "A page can't be torn out of the ledger while the epoch is running.") → toast "Undone; N conflicts skipped" or "Page torn from the ledger: changes undone" → full refresh + re-render, then a result box "#id undone: N changes" with a conflict list if any.
Footer: "N[ / total] records shown" + "More older records" (grows limit by a page up to the cap) or "Pick an epoch for older ones." when capped.
Empty: "No record matches this filter." / "The ledger is empty. Every action of the sons, the mortals, Fate and you is written here as a page."

#### 2.9.2 My notes (Notlarım)
Three sections:
1. "Notes you left on entities" (count): from the full entity list (`/api/varliklar?durum=tum`, cached in Atlas) where `kisisel_not` is non-empty: type tag + entity link + first 220 chars. Empty: "What you write in the 'Your note' box on an entity's page collects here."
2. "Map notes" (count): for every world, its map notes (`GET /api/harita?dunya=<id>` → `notlar[{metin}]`, reusing the cached map data for the current map world): note text (+ world name in multi-world) + button "On the map" (`data-dunya-harita` → opens that world's map). Empty: "You have no map notes yet. Press the 'Note pin' button on the map and click a spot; the note stays there as a pin." + button "Open the map".
3. "Notes to yourself" (count): `GET /api/bildirimler?kategori=not&limit=50` → "E<cag>" + bold title + text. Empty: "What you wrote with Notifications → 'Leave yourself a note' is here."

#### 2.9.3 Bookmarks (Yer imleri)
1. "Favourite entities" (count) from `GET /api/favoriler` (server-side): type tag + link. Empty: "Entities you marked 'Favourite' on their page."
2. "Bookmarks" (count) from localStorage `aerona.imler` (list of `{t, id, ad, zaman}`, newest first, max 200; `t`: `o` son, `c` epoch, `kr` chronicle row with id "<epoch>.<row id>"): type tag (Son/Epoch/Chronicle) + link (son → drawer; epoch/chronicle → switches to Chronicle tab and scrolls to it) + trash icon "Remove bookmark" (toggles via the global `[data-im]` handler, toast "Bookmark removed", list re-renders). Empty: "What you added with the 'Bookmark' button on son pages and in the chronicle."

---

### 2.10 Prayers tab (`#view-dualar`, views/dualar.js)
Tab 9. Re-rendered (patched via `yamala`) on sons/chronicle changes.
Data: `GET /api/dualar` → `[{id, kimden_tip ('o' son | 'v' mortal entity), kimden_id, kimden_ad, kimden_tur, cag, istek, metin, cevaplandi}]`; multi-world also loads the entity→world map.
World filter: when a world is selected in the header, only prayers from that world (son's active world / entity's world) are shown.
Layout:
1. Page header (prayer icon) "Prayers". Text: "Your sons and the mortals pray to you. Sons hear your answer on their next turn; to mortals your answer descends as a dream, blesses them and binds them directly to a cult that worships you. Gifting essence raises loyalty and faith. [Showing those from **World X**.] [**N** prayers await an answer.]"
2. Filter chips (session-only `G.duaSuzgec`): All / Awaiting answer (`Cevap bekleyen`) / Sons (`Oğullar`) / Mortals (`Ölümlüler`), each with count.
3. Cards (`article.prayer`, `done` when answered, `olumlu-dua` for mortals): header left — mortal: type tag + entity link + "· mortal prayer"; son: son icon + son link; + world (multi-world, whole cosmos) + "· Epoch N"; header right — "wishes: **<wish>**" (wish labels: essence `oz`, blessing `kutsama`, permission `izin`, revenge `intikam`, forgiveness `af`; `hicbiri` none hidden) + chip "answered". Quote block with the prayer text (auto-linked).
4. Unanswered → inline form: text input (son: "Your answer (optional)"; mortal: "What should fall into their dream? (optional)"), number "Give essence (at most X)" min 0 max X where X = min(rule `TANRI_EYLEM.dua_oz_tavan` (100), current essence). Tooltip: mortal — "Every *YARATICI.dua_oz_bolen* (3) essence you give adds 1 to their prosperity, fertility, defence and health. At most X (…)"; son — "Essence is added to the son's essence; there is room for R, the excess is wasted. Every *TANRI_EYLEM.dua_oz_sadakat* (10) essence = +1 loyalty. At most X (…)". Button "Answer" (prayer icon) or "Answer with a dream" (dream icon).
Action: client validates 0 ≤ oz ≤ X (toast "You can give at most X essence to one prayer (…)") → `POST /api/dualar/:id/cevap {metin, oz}` via `act()`, toast "Answer and N essence sent" / "Answer sent".
Empty: "No prayer matches this filter." / "No prayers yet. They appear here when your sons or mortals wish for something."

---

### 2.11 Model measurement (Settings → Records, views/olcum.js)
Data: `GET /api/olcum?cag=<SUNUCU.olcum_cag, 10>` → `{toplam{cagri, ms, girdi, cikti, maliyet}, caglar[{cag, cagri, ms, girdi, cikti, hata, yeniden, yavas}], adimlar[{adim, cagri, ort_ms, en_uzun_ms, hata}], modeller[{model, cagri, ort_ms}], yavaslar[{cag, ad, model, ms}], son_hatalar[{cag, ad, hata, model}], yavas_esik_ms}`.
- Empty: "No measured language-model calls yet. They appear here when an epoch closes."
- Chip row: "N calls", total duration, "X input · Y output tokens" (compact numbers: k/M), "API equivalent ≈ $X" (tooltip "The calls' value at API prices. Not paid separately on the Max subscription; it counts against the quota."), "last N epochs" (tooltip: rule location).
- Table per epoch: Epoch ("E12"), Calls, Duration, Tokens "in / out", Errors (red if >0, "· N retried"), Slow.
- Collapsible "By step": Step, Calls, Average, Longest, Errors.
- Model chips: "Haiku · N calls · avg X".
- Collapsible "Slow steps (N)": epoch, name, model chip, duration (amber).
- Collapsible "Recent errors (N)" (red summary): epoch, "name: localized error" (via `hataTurkce`), model.
- Footer: "Calls over X count as slow."
Duration format (`sure()`): ≥1 h "H h M min", ≥1 min "M min S s", else "S.s s" (decimal comma).
Error: red line with message.

---

### 2.12 Command palette / global search (`#palet`, views/palet.js)
Open: Ctrl/⌘+K anywhere (even in inputs), header search icon, any `[data-palet]`. Remembers the previously focused element and restores focus on close. Close: Esc in the input, click on the backdrop, or selecting a result.
Layout: centered box (backdrop blurred, z-index 92): input `#paletIn` (placeholder "Search: entity, son, word, epoch, chronicle, note, prayer, council…", autocomplete off), result list `#paletList`, footer hint "↑↓ navigate · Enter open · Esc close · Ctrl/⌘+K from anywhere".
Behaviour:
- On open: input cleared, hint shown: "Type at least two letters: entity, son, word, epoch, chronicle record, note, prayer or council." Then `GET /api/favoriler`; if favourites exist and the user hasn't typed, shows group header "★ Favourites" + favourites as entity results.
- Typing: <2 chars → hint again. Otherwise debounce 140 ms → `GET /api/ara?q=` → result array; stale responses dropped if the input changed. First result highlighted.
- Row: type-coloured icon, bold name (truncated), muted subtitle (`alt`) [+ " · <world name>" in multi-world for sons/entities/foreign gods], right tag with type label. Empty: "No results for “q”."
- Keys: ↓/↑ move highlight (no re-render, scrolls into view), Enter opens, click opens.
Result types (`t`) → icon/label → action:
- `v` entity (label = entity type name) → entity drawer; `o` son → son drawer; `y` "foreign god" → foreign god drawer; `t` "god" → creator drawer.
- `d` "world" → Cosmos tab, select world, side panel = world card; `ys` "star" → Cosmos tab, star side panel.
- `k` "word" → Languages tab with the word selected and query set.
- `c` "epoch" / `kr` "chronicle" → Chronicle tab, scroll to the epoch (and row).
- `ks` "council" → Pantheon tab, show all councils, open/scroll/flash (1.6 s) the council `details`.
- `n` "note": entity note → entity drawer; map note → that world's Map tab; otherwise target-based.
- `m` "message" or "prayer" (prayer when `tur`/`niyet`/`alt` says dua): opens the linked son/entity if any; else prayers → Prayers tab, messages → Chronicle at their epoch; fallback Notifications drawer.

---

### 2.13 Son reveal overlay (`#reveal`, views/acilis.js)
Triggered by SSE `yeni_ogul` (title "<Rarity> son arrived" (`... bir oğul geldi`)) and `yukselis` ("Ascension · <Rarity>"). Fetches `GET /api/ogullar/:id`, sets CSS `--rc` to the rarity colour (background radial glow), shows the heading, the full son card (non-clickable, from the Pantheon card renderer) and buttons "Open card" (`Kartı aç` → closes overlay, opens son drawer) and "Close". Esc also closes it (before the drawer). Errors are swallowed silently. No queue: a second event replaces the first.

---

### 2.14 Traveller's guide drawer (`openDrawer('rehber', worldId)`, views/rehber.js)
Opened from any `[data-rehber=<world id>]` (world links in notifications, Cosmos). Data `GET /api/dunyalar/:id/rehber` → `{dunya{id, ad, tur, tur_ad, aciklama, kozmoloji, lehce, kesif, yildiz{ad,tur}, ana, fizik{zaman, atmosfer, yercekimi}, sizinti}, iklim, tehlikeler[], halklar[], kaynaklar[], rotalar[], yabanci_tanrilar[], gok[]}`. Accent colour `--dc` from the world-type palette.
Sections:
1. Header: eyebrow "Traveller's guide" + discovery chip (known `bilinen` / legend `efsane` / unknown `bilinmeyen` / forgotten `unutulmuş`); name + type name; description (auto-linked); chips: star (name + type), "moon of <parent>" (LANGUAGE-SPECIFIC possessive), "time: normal | slow (×k) | fast (×k)", "atmosphere X", "gravity X", "leakage N/100" (red-ish `st-surgun` ≥ `KORKU.uyari2` 60, amber ≥ `REHBER.sizinti` 30), climate chip "<name> N epochs". Buttons "Descend to its map" (`data-dunya-harita`) and "The cosmos's codex" (download `/api/kodeks.md`).
2. Cosmology (if any). 3. Local dialect (if any).
4. Dangers: icon by kind (place/species/outside/leakage), linked name + reason. Empty "No known danger. Be careful anyway."
5. Peoples and settlements: icon, link, "type · N souls · speaks L · worships G" (the last two are Turkish suffix constructs). Empty "No people lives here yet."
6. Resources: link, "original" tag, mechanism tags (decaying, addiction, sentient, depletion cost, fixed, sacred; tooltips from `G.K.KAYNAK_MEKANIKLERI`), description (ellipsis appended if cut mid-sentence). Empty "No known resource."
7. Roads: target world, route chips, "method · N epochs · danger D[ · reason]"; closed routes greyed with a broken-link icon. Server data overrides cached Cosmos route data. Empty "No road opens to other worlds."
8. Native gods (only if any): name, epithet, status label, "attitude to the pantheon ±N".
9. Sky (only if any): clickable chips to sky entities.

---

### 2.15 Epoch breakdown popover (`core/dokum.js`)
Any element with `data-dokum="kiyamet|sizinti|nufus|oz"` (header doomsday chip and essence counter; also used elsewhere). Hover or focus → after 180 ms shows `.dokum-pop` (`role=tooltip`, 300 px wide, centred under the element, clamped to the viewport, `aria-describedby` linked). On touch devices (`hover: none`) click toggles. Hides on mouseout/focusout, any scroll, or click elsewhere.
Data: `GET /api/dokum?cag=<current epoch − 1>` (cached per epoch for the session; 404 → "no breakdown"). Header "<Doomsday clock | Leakage | Population | Divine essence> · Epoch N [before → after]". List: top 10 items by absolute value, each "label  ±value" (sign "+", "−", "±"), coloured good/bad (for doomsday/leakage positive = bad; for population/essence positive = good). Footer "Net ±total". Empty: "No items were written for this epoch." / "No breakdown for this epoch." Item labels: godless communities, the cursed, restless souls, wars, rebel sons, miracles, faith, peace, wonders, temples, golden age, epoch turning, broken star, gate, priests (unknown keys humanized). The parser accepts several alternative response shapes (see defects).

---

### 2.16 Help drawer (`openDrawer('yardim')`, views/yardim.js)
Opened by `?`, the footer "? help" button, Settings. Eyebrow "Help", title "Shortcuts and terms".
**Keyboard shortcuts** list (rendered as `<kbd>`):
| Keys | Meaning |
|---|---|
| ? | This window: shortcuts and terms |
| 1 … 9 | Tabs: 1 Pantheon · 2 Cosmos · 3 Map · 4 Atlas · 5 Network · 6 Chronicle · 7 Languages · 8 Gallery · 9 Prayers |
| ⌘K / Ctrl+K | Search everything: entity, son, word, epoch, chronicle, note, prayer, council |
| Alt+← / Alt+→ | Back / forward in the open page (drawer history) |
| Esc | Close the open window |
| ↑ ↓ Enter | Navigate and open in search |
| ← → | Previous / next image in the image viewer |
| ↑ ↓ ← → | Navigate the Atlas tree; → expands a branch, ← collapses |
| ⌘Enter / Ctrl+Enter | Save the map note |
| Enter | Languages: translate the sentence in the translation box (Shift+Enter new line) |
Note: "While in a text box, digits and ? do not count as shortcuts."
**Terms** glossary (`TERIMLER`), translated:
- Chronicle — The record of epochs and events. Read and searched epoch by epoch in the Chronicle tab.
- The world's book — Printable encyclopedia; save as PDF from the browser. Son and entity pages can also be printed on their own.
- Codex (Markdown) — Export of the whole world as one Markdown file.
- Action ledger — The changes each action wrote to the world; tearing out a page undoes that action.
- Live feed — The sons' thoughts, tools and the world's events; flows in real time.
- Notification — Persistent list of important events; marked as read.
- Bookmark · Favourite — Bookmarks are kept in this browser (son, epoch, chronicle record); favourite entities are stored on the server.
- Complete epoch — Waiting sons, mortals, the world engine and Fate act in turn; the epoch closes. Can be stopped at a safe point and later completed from where it stopped.
- Divine essence — The price of commands; refills every epoch. The sons' essence is separate.
- Revelation — Creating a single entity with your own hand; spends essence. In a multi-world cosmos you can choose which world it descends to.
- World filter — The world selector in the header. Cosmos, map, atlas, network, chronicle, languages, gallery and prayers are filtered by the selected world; the pantheon is the whole cosmos's.
- Doomsday clock — The shared clock of the whole cosmos. Godless communities, wars and curses advance it; miracles and faith push it back. Doomsday comes at the threshold; threshold and speed are set in World Rules.
- Climate era — Each world's climate lasting several epochs (drought, warm era…); affects fertility and migrations. Changed via Cosmos → Create → Climate.
- Star of the epoch — The star hung in the sky this epoch; creations in its domain get cheaper.
- Mood — The god's balance of anger, contentment, interest and loneliness; the header chip's tooltip shows all four values.
- Leakage — The Outside seeping into a world (0–100). As it rises, cosmic horror events increase; sons can stitch the leak.
- World Rules — Settings → Game → World Rules: every cost, threshold and probability. A number you change takes effect immediately.
- Exploration mode — Browsing another, imported world read-only; your own world waits aside.

---

### 2.17 Global keyboard shortcuts and global click delegation

Keyboard (all `document` listeners):
- Ctrl/⌘+K: open palette (always, `preventDefault`).
- Alt+←/→ while the drawer is open: drawer history back/forward (clicks the nav buttons; disabled at the ends).
- Lightbox open: Esc closes; ←/→ cycle images (if >1); other keys ignored.
- Esc: closes the reveal overlay if visible, otherwise the drawer. (Palette Esc is handled by its input.)
- `?` (no modifiers, not typing, palette/lightbox closed): Help drawer.
- `1`–`9` (no modifiers, not typing, palette/lightbox closed, drawer closed, world exists): switch tab and focus its button.
- Tab: focus trap inside the topmost modal (lightbox > palette > drawer).
- Enter/Space on `[data-gu-portre]`: activate (image generation portraits).
- Mobile (≤600 px): scrolling `#main` down >60 px collapses the header (`body.bas-kucuk`), scrolling up/near top restores it.

Global click delegation (app.js), by attribute: `data-im` (toggle bookmark), `data-im-git="c|kr:<epoch>[.<row>]"` (go to Chronicle), `data-copy` (clipboard + toast "Copied" / "Couldn't copy; select the text and copy it."), `data-lb`/`data-glb` (lightbox), `data-v`/`data-o`/`data-yabanci`/`data-tanri-ac`/`data-rehber` (drawers), `data-haritada` (show on map), `data-kesif-bitir`, `data-iklim-ac`, `data-karsi` (pantheon compare, max 3, `aerona.karsi`), `data-dunya-harita`, `data-agda` (focus in Network), `data-gecmis`, `data-palet`, `data-tab-go[+data-filter]` (switch tab, optional Atlas filter), `data-close`. Generic two-click confirm for any `button[data-onay]` (4 s revert).

Toasts (`core/dom.js`): single toast element; info 3 s, error 6.5 s (red), with action button 7 s. Every message passes through `ekDuzelt()` (Turkish suffix fixer — drop in rewrite).

---

### 2.18 Shared text helpers

#### 2.18.1 Name auto-linking (`core/adlar.js`)
- `adlariYukle()`: `GET /api/adlar` → `[{t: 'v'|'o'|'y', id, ad, ek?}]` (all names; `ek` = per-name suffix dictionary entry, LANGUAGE-SPECIFIC). Re-fetched only when the signature (type counts + son count) changes or forced. Builds `G.ADLAR_ID` (key `t+id`, excludes foreign gods), and one giant case-insensitive regex of all names with length ≥ 4 (longest first, Unicode word boundaries).
- `linkle(html, exclude)`: on text segments outside tags/anchors, replaces name occurrences with `<a class="link wl" data-v|data-o|data-yabanci=id>`; skips the page's own record. Also humanizes raw snake_case keys first (`duzyazi`).
- `kimlikHtml(text)`: server texts embed id tokens; converts `Name (#123)` → linked Name, `#123 Name` / `#123` → linked entity name, `oğul#12` / `ogul#12` → linked son name (de-duplicating an immediately following repeated name), `iplik#5[ hikâye]` → quoted thread summary (≤40 chars) with tooltip = full thread text, falling back to "a story" (`bir hikâye`). Then `linkle`.
- `kimlikDuz(text)`: same token resolution to plain text (no links), unknown son → "a son".
Rewrite: keep token resolution (server-side preferred) but drop Turkish literals (`oğul`, `hikâyesi`).

#### 2.18.2 Labels for raw keys (`etiket.js`)
`etiket(key)` → label or key with underscores → spaces. Table (key → English): oz essence; kutsama blessing; izin permission; intikam revenge; af forgiveness; hicbiri none; dostluk friendship; ittifak alliance; ask love; tehdit threat; alay mockery; uyari warning; pazarlik bargaining; sohbet chat; silah weapon; zirh armour; kalkan shield; arac vehicle/tool; taki jewellery; calgi instrument; kitap book; kuraklik drought; firtina storm; sifa healing; baris peace; guc strength; kurnazlik cunning; yaraticilik creativity; savascilik martiality; bagnazlik zealotry; sagduyu sanity; yayginlik prevalence; tarim agriculture; yazi writing; mimarlik architecture; buyu magic; gokbilim astronomy; gokyuzu_seyri sky navigation; gemi_yapimi shipbuilding; kapi_bilimi gate lore; yol_biliciligi pathfinding; bosluk_yasami life in the void; olumsuzluk quest for immortality; biyobuyu biomancy; kesif exploration; harac tribute; muttefik alliance; olu dead; yok_edildi destroyed; gerceklesti fulfilled; uyanik awake; uyku asleep.
`DUA_ISTEK` (prayer wish verbs): oz "wished for essence", kutsama "wished for a blessing", izin "asked permission", intikam "wished for revenge", af "asked forgiveness". `SOZ_NIYET` (speech intents): dostluk "spoke in friendship", ittifak "proposed an alliance", ask "declared love", tehdit "spoke threateningly", alay "spoke mockingly", uyari "gave a warning", pazarlik "proposed a bargain".
`altTurEtiketle(s)` turns a raw subtype "key[: rest]" into "label: rest"; `hamAnahtarMi` detects raw keys (with a hard-coded exclusion list oz/af/ask/olu/uyku). `veListesi(names)` → "A, B and C" (LANGUAGE-SPECIFIC "ve" — use the locale list formatter).

#### 2.18.3 Tool and action names (`arac-ad.js`)
Used by the live feed (in-progress phrasing) and the Action ledger (`eylemAdi`: past phrasing preferred, then in-progress, then god actions; `prefix:sub` keys render "<prefix label> · <sub>"; unknown → underscores to spaces).

Son / mortal tools (`ARAC_AD` in-progress, `ARAC_EYLEM` past):

| key | in progress | past |
|---|---|---|
| dunya_ozeti | looking at the world | looked at the world |
| varlik_incele | examining | examined |
| varlik_ara | searching | searched |
| hafizam | searching their memory | searched their memory |
| kardesi_incele | sizing up a sibling | sized up a sibling |
| plan_yaz | writing their plan | wrote their plan |
| capa_sec | choosing their anchor | chose their anchor |
| kardese_seslen | calling to a sibling | called to a sibling |
| ahit_et | swearing a covenant | swore a covenant |
| meydan_oku | issuing a challenge | issued a challenge |
| armagan_ver | giving a gift | gave a gift |
| isyan_et | rebelling against their father | rebelled against their father |
| babaya_dua | praying | prayed |
| bag_kur | weaving a bond | wove a bond |
| kaynak_sag | harvesting a resource | harvested a resource |
| varligi_etkile | touching (an entity) | touched an entity |
| secilmis_ilan_et | proclaiming a chosen one | proclaimed a chosen one |
| lanetle | cursing | cursed |
| mucize | sending down a miracle | sent down a miracle |
| ruya_gonder | sending a dream | sent a dream |
| afet_gonder | sending a disaster | sent a disaster |
| bilgi_ver | teaching knowledge | taught knowledge |
| bilgi_ilham_et | inspiring knowledge | inspired knowledge |
| savas_kiskirt | inciting war | incited war |
| donustur | transforming | transformed |
| yok_et | destroying | destroyed |
| evlat_dogur | bearing a child | bore a child |
| dunyaya_yonel | turning to another world | turned to another world |
| kutsal_dunya_ilan | proclaiming their holy world | proclaimed their holy world |
| kapi_muhurle | sealing a gate | sealed a gate |
| yildiz_tutustur | rekindling a dead star | rekindled a dead star |
| ruh_kapla | encasing a soul | encased a soul |
| yildiz_as | hanging a star in the sky | hung a star in the sky |
| yildiz_sondur | extinguishing a star | extinguished a star |
| yabanci_tanriyla_konus | speaking with a foreign god | spoke with a foreign god |
| antlasma_yap | forging an inter-world treaty | forged an inter-world treaty |
| sizinti_dik | stitching the leak | stitched the leak |
| yatak_ac | opening a cosmic channel | opened a cosmic channel |
| yabanci_tanriyla_savas | declaring war on a foreign god | declared war on a foreign god |
| dis_varlikla_pazarlik | bargaining with the thing Outside | bargained with the thing Outside |
| dunya_dogur | giving birth to a world | gave birth to a world |
| dunyaya_bak | looking around | looked around |
| dil_kur | birthing their language | birthed their language |
| kelime_tureti | coining a word | coined a word |
| uret | producing | produced |
| insa_et | building | built |
| kultur_yarat | birthing a culture | birthed a culture |
| kaynak_kesfet | discovering | discovered a resource |
| sahiplen | claiming | claimed |
| yerlesim_kur | migrating | founded a settlement |
| ticaret_kur | establishing trade | established trade |
| savas_ilan_et | declaring war | declared war |
| tapin | worshipping | worshipped |
| yaraticiya_dua | praying to the Creator | prayed to the Creator |
| bilgi_gelistir | developing knowledge | developed knowledge |
| ogren | learning | learned |
| diplomasi | conducting diplomacy | conducted diplomacy |
| maceraya_cik | setting out on an adventure | set out on an adventure |
| rota_kesfet | seeking a road to another world | sought a road to another world |
| toprak_kesfet | setting out for unknown lands | set out for unknown lands |
| dirilis_ayini | holding a rite for their dead god | held a rite for their dead god |
| can_al | reaching for a mortal's life | reached for a mortal's life |
| kardesini_dirilt | plotting for a dead sibling | plotted for a dead sibling |
| kemikleri_dagit | scattering a dead sibling's bones | scattered a dead sibling's bones |
| gemi_yap | building a ship | built a ship |
| sefere_cik | setting out on an expedition | set out on an expedition |
| evcillestir | domesticating | domesticated |
| kimera_dok | weaving a chimera | wove a chimera |
| kalinti_ara | investigating ruins | investigated ruins |
| sabotaj | sabotaging | sabotaged |
| vaaz_et | preaching | preached |
| tanriya_meydan_oku | defying a god | defied a god |
| inkar_et | renouncing their god | renounced their god |
| kehanet_et | prophesying | prophesied |
| kac | attempting to flee | attempted to flee |
| fidye_ode | paying a ransom | paid a ransom |
| esiri_kurtar | trying to free a captive | tried to free a captive |
| ordu_topla | raising an army | raised an army |
| komutan_ata | appointing a commander | appointed a commander |
| casus_ag_kur | building a spy network | built a spy network |
| takas | bartering | bartered |
| borc_ver | lending | lent |
| borc_ode | paying a debt | paid a debt |
| evlat_edin | adopting | adopted |
| bolge_yarat | creating a region | created a region |
| yer_yarat | creating a place | created a place |
| kaynak_yarat | creating a resource | created a resource |
| tur_yarat | creating a species | created a species |
| halk_yarat | creating a people | created a people |
| olumlu_yarat | creating a mortal | created a mortal |
| esya_dov | forging an item | forged an item |
| yapit_insa | building a structure | built a structure |
| dil_yarat | creating a language | created a language |
| efsane_anlat | telling a legend | told a legend |
| gelenek_kur | founding a tradition | founded a tradition |
| tarikat_kur | founding a cult | founded a cult |
| hizip_kur | founding a faction | founded a faction |
| gok_cismi_as | hanging a celestial body | hung a celestial body |
| eser_yarat | creating a work | created a work |
| kanun_koy | laying down a statute | laid down a statute |
| ruh_cagir | summoning a spirit | summoned a spirit |
| kehanet_soyle | speaking a prophecy | spoke a prophecy |
| olay_baslat | starting an event | started an event |
| arac_yarat | creating a tool | created a tool |
| yasa_koy | laying down a law | laid down a law |

Creator-god actions (`TANRI_EYLEM`, past only): kutsa blessed; vahiy revealed; dirilt resurrected; sefer recalled the expedition; kesfe_yolla sent to explore; yol_arat showed the way through the sky; kesif_turu ordered an exploration tour; tanri_can_al took a mortal's life; ogul_oldur killed one of his sons; ayin_buyur ordered a resurrection rite; `oz_em:ogul` drained a son's essence; `yut:ogul` devoured a son; `oz_em:olumlu` drained a mortal's life; `yut:olumlu` devoured a mortal; hasat harvested faith; `oz_em:yabanci` drained a foreign god's power; `oldur:yabanci` killed a foreign god; `yut:yabanci` devoured a foreign god; `dirilt:olumlu` called a mortal back from death; tanrilastir raised a mortal to the heavens; alcalt demoted a son; guc_sok tore out a son's power; mutlak_buyruk gave an irrefusable command; peygamber chose a prophet; tezahur appeared while awake; soy_laneti cursed a lineage; `soy_laneti:kaldir` lifted a lineage's curse; cevir converted a community to himself; gazap destroyed with his wrath; `gazap:dunya` brought wrath upon a whole world.
Prefixes (`TANRI_ONEK`, for `prefix:sub` keys): mudahale intervened; ceza punished; kozmik cosmic action; yol road work; sefer expedition (`sefer:geri` → "recalled the expedition").

Helpers: `aracEmri(key)` renders a tool key as Turkish words via a word map `SOZ` (e.g. `ruya_gonder` → "rüya gönder") — LANGUAGE-SPECIFIC transliteration of ASCII keys back to Turkish spelling; in English just humanize keys or use the table. `aracAdlariniCevir(text)` wraps known tool keys appearing in prose as «words»; `duzyazi(text)` additionally replaces any remaining snake_case token with spaces (used before auto-linking and in rule labels).
Error localization (`hataTurkce`): maps raw model/SDK errors to friendly text: invalid tool arguments → "Invalid input to the «tool» tool: <field> should have been a number/text/yes-no/list/object/integer; … too small/too big/not an allowed value/unrecognized field/invalid"; overloaded/529 → "The model is overloaded right now (529); the job can be retried shortly."; rate limit/429/quota → "Max usage limit reached (429); retry when the limit resets."; credit/billing → "Your account's usage allowance is insufficient."; "process exited with code N" → "The Claude process closed unexpectedly (code N)."; timeout → "The model timed out."; network errors → "Network connection dropped."; aborted → "The job was interrupted."; invalid JSON/schema → "The model's reply wasn't in the expected format."; "Claude Code returned an error result" → "The model returned an error."; `error_max_turns` → "reached the turn limit"; `error_during_execution` → "failed while running"; budget → "reached the budget limit". A Turkish prefix before ": " is preserved (detected by Turkish letters — LANGUAGE-SPECIFIC heuristic).

#### 2.18.4 Turkish grammar helpers (`dil.js`) — LANGUAGE-SPECIFIC: drop or replace
Entire module exists only to make generated Turkish read correctly; none of it applies to English:
- `ekle(name, case)` / `ekDuzelt(text)`: vowel-harmony and consonant-assimilation engine that rewrites the suffix after an apostrophe (`Name'in`, `Name'a`, `Name'da`, `Name'dan`, `Name'daki`, `-sin`, `-dir`, plural `-ler`) to agree with the proper noun (including numbers read aloud via `sayiOkunus`, Roman numerals read as ordinals, compound-noun possessive detection, adjective detection, per-name pronunciation overrides from the `/api/adlar` `ek` dictionary loaded by `ekSozlugu`). Applied to every toast, header tooltips ("since Epoch N", "<god>'s mood"), traveller's guide ("moon of X", "worships X"). Replace with English templates ("X's", "since Epoch N").
- `yazimDuzelt(text)`: fixes Turkish capital dotted İ in sentence-initial words, root changes (`oğul`→`oğl-`, `şehir`→`şehr-` …), and "Name name+suffix" duplications.
- `cogulIyelik` (plural possessive), `toplulukIci(name, type)` ("among the X people", "within X", "X'de"), `yonetimUnvani` (ruler titles by entity type: Keeper/Owner/Bearer/Protector/Master/Narrator/Ruler — this one is a content mapping, could survive as English titles: law → Keeper, resource → Owner, item → Bearer, tradition → Protector, technology → Master, structure → Owner, work → Protector, language → Protector, legend → Narrator, default → Ruler).

---


---

## Part 3 — Pantheon and record pages (son, entity, creator, foreign god), drawer system, images

### 3.0 Scope and shared conventions used by every record page

Files covered: `public/views/varlik.js` (entity page), `public/views/ogul.js` (son page), `public/views/tanri.js` (creator-god page), `public/views/yabanci.js` (foreign-god page), `public/views/panteon.js` (Pantheon components: son card, god panel, threads, sibling matrix, council), `public/core/cekmece.js` (drawer), `public/core/gorsel.js` (gallery / lightbox / upload / prompt box), `public/core/gorsel-uret.js` (local image generation UI), `public/core/formlar.js` (declarative forms), `public/core/bilesen.js` (shared components). A few helpers from other files are described only where these pages depend on them (`core/yenile.js` `act`/`refresh`, `core/dom.js` `yamala`, `core/hedef.js`, `app.js` global click router, `views/palet.js` keyboard handler).

#### 3.0.1 Record types and link attributes

Every clickable name in the app is an `<a class="link">` carrying a data attribute. A single global click handler in `app.js` routes it (`app.js:70-109`):

| Attribute | Opens | Helper |
|---|---|---|
| `data-v="<id>"` | Entity drawer (`openDrawer('v', id)`) | `vlink(id, name)` |
| `data-o="<id>"` | Son drawer (`openDrawer('o', id)`) | `olink(id, name)` |
| `data-yabanci="<id>"` | Foreign-god drawer (`openDrawer('y', id)`) | `ylink(id, name)` |
| `data-tanri-ac` | Creator-god drawer (`openDrawer('t', 1)`) | `hlink('t', …)` |
| `data-rehber="<worldId>"` | World travel-guide drawer (`openDrawer('rehber', id)`) | `hlink('d', …)` |
| `data-haritada="<id>" data-dunya="<w>"` | Closes the drawer, switches to the Map tab and focuses the entity (switches map world if different) | — |
| `data-agda="<id>"` | Closes the drawer, opens the Graph tab focused on `v<id>` | — |
| `data-dunya-harita="<w>"` | Lands on that world's map (`haritaInis`) | — |
| `data-glb="<tip>:<id>"` | Fetches `GET /api/gorseller?tip=&id=` and opens the lightbox at image 0 (used on hero portraits) | — |
| `data-lb="<cacheKey>:<i>"` | Opens the lightbox on a gallery thumbnail | `galleryHtml` |
| `data-copy="<text>"` | Copies to clipboard; toast "Copied" (Kopyalandı) / error "Couldn't copy; select the text and copy it." | — |
| `data-im="<t>:<id>"` | Toggles a bookmark (yer imi) | `imDugme` |
| `data-tab-go="<tab>" [data-filter]` | Closes drawer and switches tab (optional Atlas type filter) | — |

`hlink(tip, id, name)` uses `hedefAttr` (core/hedef.js): tip `v|o|y|d` → the attribute above, `t` → `data-tanri-ac`; any unknown tip (or non-numeric id) renders the name as plain bold text so a wrong record is never opened.

#### 3.0.2 Declarative forms (Tanrının buyrukları) — `core/formlar.js`

Most god actions are `<form data-post="/api/..." data-mesaj="<success toast>" [data-onay="<confirm label>"] [data-donustur="<transform>"] [data-sifirla]>`. A single document `submit` listener:

1. If `data-onay` is set and the submit button has not been armed: the first submit turns the button red (adds `danger`) and replaces its label with a warning icon + the `data-onay` text (e.g. "Are you sure? Exile" / "Emin misin? Sürgün et"); returns. The second submit performs the action. (No timeout for form-based confirmations — the armed state lasts until the request finishes.)
2. Body is built from named fields: dotted names nest (`kisilik.mizac` → `{kisilik:{mizac}}`); `type=number`, `type=range` or `data-sayi` fields become numbers (`''` → `null`); checkboxes become booleans; disabled fields are skipped. Hidden inputs without `data-sayi` stay strings (e.g. `yut: "1"`).
3. `data-donustur` runs a named transform from `FORM_DONUSTUR` (may throw → error toast, request not sent).
4. The submit button is locked (`disabled`, `aria-busy`) for the request duration; `act()` runs the request, shows the success toast, refreshes state, and offers Undo.
5. `data-sifirla` resets the form on success.

Standalone destructive buttons use `<button data-onay="...">` (outside forms): a capturing click handler arms the button on first click (red, label replaced by the confirmation text), and reverts after **4 s** if not clicked again (`formlar.js:53-60`). The second click passes through to the button's own handler.

Validation messages for native constraints are replaced with localized text (required → "Fill in this field." / select → "Pick one from the list." / range overflow → "Can be at most N" plus, when the input has `data-kural="<RULE.path>"`, "; this limit is a World rule (RULE.path): you can raise it in Settings → Game → World rules").

Range sliders are rendered by `aralik(label, name, value, min=0, max=100)` as `<input type=range>` + live `<output>` showing the number.

Transforms registered:
- `bag` (bond create, see 3.1.12), `gercek` (fact), `etiket` (tag toggle), `hedef` (name→id resolver), `hami` (patron), `ek` (name-suffix form, language-specific), `tutku` (creator passions), `iplik` (story thread: comma-separated related names → ids, error `"X" diye bir varlık yok.` / "There is no entity called X").
- `adaKimlik(name, filter)` resolves a typed name to a record by exact case-insensitive (Turkish locale) match over the global name index `G.ADLAR_ID` (keys `v<id>`, `o<id>`…, each `{t, id, ad, tur, durum}`). Error if not found: "Pick the target from the list." (Hedefi listeden seç.)

#### 3.0.3 Action runner, cost gating and undo — `core/yenile.js`, `core/bilesen.js`

- `act(fn, okMsg)`: locks the last clicked button (if the click happened <600 ms ago), records the latest god-ledger id (`GET /api/defter?kim_tip=t&limit=1`), runs the request, shows `okMsg` toast (if given), does a full `refresh()` (`GET /api/state` + re-render current tab + silently re-render the open drawer). If a new god ledger entry appeared, the success toast gets an **"Undo" (Geri al)** button → `POST /api/defter/:id/geri-al`; toast "Undone" or "Undone; N conflicts skipped". Errors show the server `hata` as a red toast.
- `ozEngel(cost, {mesgul, ek})` returns attributes that disable a button with an explanatory tooltip (also `aria-description`, `data-engel`). Priority: explicit reason `ek`; then if `mesgul` and a world job is running: "A job is running; it opens when finished." (Süren bir iş var; bitince açılır.); then if creator essence `G.S.dunya.tanri_oz < cost`: "N essence needed; you have M." (N öz gerekir; şu an M.)
- `bedel(key)` looks up a cost: special keys `uyandir, bastir, konsey, ruya, dirilis, dunya` from `G.K.*_BEDEL` or the `/api/denge` table (`G.DENGE['DENGE.<k>']`), otherwise `G.K.COSTS[k]`, `G.K.MUDAHALE_BEDEL[k]`, `G.K.KOZMIK_BEDEL[k]`.
- Costs are always displayed inside the button as `<span class="cost">` + essence icon + number; gains as `<span class="cost kazanc">+N</span>`.
- `kural('GROUP.key', default)` reads a tunable World rule; `kuralYeri('GROUP.key')` renders "World rules → <group> → GROUP.key" — appended to tooltips so every number tells the player which rule controls it. NOTE: every call site carries a hard-coded client fallback default (e.g. `kural('TANRI_GUC.tanrilastir', 150)`); the rewrite should get all values from the server.
- Long-running jobs: `isSuruyor(key)` is true when `G.S.isler`/`G.S.sira` contains a job with that `anahtar`. Keys used here: `v<id>:derin`, `v<id>:prompt`, `o<id>:destan`, `y<id>:derin`, `t:destan`, `t:derin`, `t:suret`. While true the trigger button renders `disabled aria-busy="true"`.

#### 3.0.4 Rendering model and realtime

- All drawers are HTML strings patched into `#drawerBody` with a keyed DOM diff (`yamala`, core/dom.js): nodes are matched by `data-k` or `id`; open `<details>` stay open; a focused input/textarea keeps its value. That is why most collapsibles carry `data-k`.
- The open drawer is silently re-rendered (`openDrawer(tip, id, silent=true)`) after: any `act()`; any full refresh; SSE `is_sirada`/`is_basla`/`is_bitti` (job start/finish → re-enable buttons); SSE `gorsel_bitti` for the same record; and incremental `/api/degisim` patches when relevant: entity drawer if that `varliklar` id changed/deleted or world list/world row changed; son drawer if that son changed or `iliskiler` changed; creator drawer if new chronicle (`kronik_yeni`), any son, world row or worlds changed; foreign-god drawer if `yabanci` contains its id, new chronicle, or `baglar` changed. A change of `mesgul` (busy) also re-renders the drawer.
- SSE `basla` (son turn starts) adds the son to `G.acting`, toggling `.acting` on its Pantheon card; `bitti` removes it.

---

### 3.1 Entity page drawer (Varlık sayfası) — `views/varlik.js`

**Purpose.** Full record page for any entity (`varlik`: people/peoples/settlements/regions/items/knowledge/laws/languages/souls/"outer things" etc.), including every direct god intervention on it.

**How it opens.** Any `data-v="<id>"` click → `openDrawer('v', id)`; command palette results of type `v`; "Open page" buttons in Gallery. The same HTML is also embedded in the Atlas tab's detail pane (`#atlasMain`); `tekrarCiz(root,id)` re-renders whichever host it is in.

**Data loaded (parallel).**
- `GET /api/varliklar/:id` → main record (server `varlikDetayJson`).
- `GET /api/varliklar?tur=teknoloji` → list of all knowledge entities (cached in `BILGI` until `G.S.surum` changes; stored on `window._bilgiler` for the "Teach knowledge" select).
- If multi-world or any foreign gods exist: cosmos data (`kozmosVeriTaze()` → routes `rotalar`, journeys `yolculuklar`, foreign gods `yabanci_tanrilar`).
- If multi-world: `GET /api/varliklar?durum=tum` (Atlas full cache) → map entity id → world id (`DUNYA_HARITA`), used to label datalist options with their world.

**Key response fields used** (from `varlikDetayJson`): `id, ad, tur, alt_tur, durum, aciklama, statlar{}, etiketler[], guc_seviyesi, sinif` (rarity derived from power level), `alan` (domain), `cag` (epoch created), `kaynak` (`olumlu|dunya|…`), `yapan{id,ad}` (maker), `yaratan{id,ad}` (creating son), `dunya_id`, `favori`, `kisisel_not`, `kader_notu`, `arsiv, arsiv_sebep, arsiv_elle, onem, son_anma`, `bekleyen_ruya[{metin,cag}]`, `yol[{id,ad,tur}]` (location chain, max 8), `capasi_olan[{id,ad}]` (sons anchored here), `gorseller[]`, `gorsel_prompt`, `derinlik{cag,tarih,ozel{},sozler[{tur,metin}],ayrintilar[],soylentiler[],gizli_gercek}`, `gercekler[]`, `toplum{k{class:share},m{class:satisfaction},e{erzak,maden,mal,fiyat{}}}`, `kapasite{kapasite,bolge_nufus,doluluk,paylasan,bolge{id,ad}}`, `yasam{yas,taban,tip,onemli,etkin,zaman,cag_yil,olumsuz,olum_yili}` (mortals only), `olum{ogul_bedel,yuzde,koruyan[],tanri_bedel}` (living mortals), `oluTanrilar[{id,ad}]`, `kesif{yuzde,neden[],yol}`, `ek` (suffix settings), `benzerler[]`, `iliskiler[]`, `savaslar[]`, `icindekiler[]`, `baglar[]`, `kronik[]`, `kronik_sayisi`, `anildigi[]`, `sahip_olunanlar[]`, `urettikleri[]`, `bildikleri[]`, `bilenler[]`, `soy{ata[],torun[]}`, `dal`, `yasa_mekanik`, `sozluk[]`, `konusanlar[]`, `dil{id,ad}`, `inanclari[]`, `tarih_yazdiklari[]`, `son_eylem_cag`, `tur_ap`, `olum_cag`.

Type definitions come from `G.K.VARLIK_TURLERI[tur]` → `{ad, stat:[[key,label,min,max]…], konum:[allowed parent types]}`. Type colour `TUR_RENK[tur]` = CSS variable `--tur-<tur>` (resolved to a hex via a canvas, cached).

#### 3.1.1 Hero (header)

Left: **portrait**.
- Type `dis` ("outer thing", Dış Varlık): never shows a real image; shows an unnamed blurred shape (`.dis-sekil`, aria "A shape that is not named"); wrapped in the generate-image overlay if no image.
- Else cover image (`gorseller` with `kapak`, else first) at 320 px, `data-glb="v:<id>"` (opens lightbox).
- Else a type icon inside the "Generate image" portrait overlay (`portreUret`, see 3.7).
- Dead (`durum='olu'`): dagger "†" badge over the portrait; whole hero greyed (`--hc: var(--muted)`).

Right (hero-info), in order:
1. Breadcrumb of the location chain (`yol`), links joined by chevrons; if empty: "top level" (en üst düzey).
2. Name (`d-name`), prefixed with "†" when dead; subtitle = `alt_tur` or translated type name.
3. Action buttons: **Favourite** toggle (Favorile / Favori; star icon filled when on; gold class) → `POST /api/varliklar/:id/favori {favori: bool}`; optimistic update of button + Atlas cache entry; toast "Added to favourites" / "Removed from favourites". **Show on map** (Haritada göster; only if the type has location parents or is `bolge`). **Show in graph** (Ağda göster). **Print page** (Sayfasını yazdır) → link `/kitap?varlik=<id>` in new tab.
4. Meta chips row: type tag (coloured by type), rarity class chip (`cls(sinif)`, coloured `c-<rarity>`), power "G<guc_seviyesi>", domain chip with domain glyph, "Epoch N" (Çağ N), creator chip (mortal maker → mortal icon + link; `kaynak=dunya` → "the world's flow"; creating son → son link; else creator god name). Multi-world only: world chip (opens that world's map) + "guide" chip (opens travel guide). Archive chip "sank into history[: reason]" (tooltip "Importance X · last mentioned Epoch Y") when `arsiv`. Purple "dream pending[ · N]" chip when `bekleyen_ruya` non-empty (tooltip lists "Epoch c: text"). Status chip if not canon (status names map `DURUM_AD`: canon, rejected, destroyed, dead, fulfilled, merged, waiting, forgotten). Tag chips (3.1.3). "<son>'s anchor" chip per `capasi_olan`.

#### 3.1.2 Body sections (in render order)

A section navigator (3.6.3) is prepended when there are ≥4 section headings.

1. **Timeline strip** (`zamanCizgisi`) — shown if the entity spans ≥2 epochs or has ≥2 chronicle entries. One column per epoch from `min(v.cag, first chronicle epoch)` to current epoch; label "Ç<n>"; the birth epoch column has class `dogus`. A dot per epoch with entries: size `6 + min(10, count*2)` px; colour by the most important entry type in that epoch (priority olum 5 > kader/meydan/savas 4 > dunya/lanet/afet 3 > dogum 2 > yaratim 1): death/curse/disaster = danger red, fate = epic purple, battle/war/world = warn amber, birth = good green, else accent. Tooltip "Epoch N: K records". Clicking a dot scrolls to the first chronicle entry of that epoch (`[data-kcag]`) and flashes it (`.parla` for 1.6 s).
2. **Fate's note** — quote block "Fate: <kader_notu>" if present.
3. **Description** — large prose; entity names auto-linked (`linkle`).
4. **Canon facts (Kanon gerçekleri)** — subtitle "What Fate and you have fixed about this entity; all agents obey them". Rows: subject (bold if self, else link) · predicate (`iliski`) · object (link if `nesne_id`, else text, else "—") · "Ç<cag>" · trash button → form `POST /api/gercekler/:gid/sil`, confirm "Delete" (Sil), toast "Fact removed from canon". Empty: "No fact has been fixed yet." Collapsible **Add fact** (Gerçek ekle): fixed subject = this entity; `iliski` (required, max 80, placeholder "predicate: forbids, opens only at night…"), `nesne` (required, max 200, datalist of entity names, "object: an entity name or plain text"); → `POST /api/gercekler {ozne_id, iliski, nesne_id}` if the object matched an entity, else `{ozne_id, iliski, nesne}`; toast "Fact written into canon"; form resets.
5. **Stats (Statlar)** — shown if the type has stats, capacity or agent info.
   - Agent turn chips (types halk, yerlesim, hizip, tarikat, olumlu, tur): "last turn: Epoch N"; "remaining actions: N" (amber when >0).
   - Stat grid: for each type stat present: label, value (`fmt`), meter (only when max ≤100) in type colour. Plus **Sanity (Sağduyu)** if present: meter 0–100, red and warning text "Mind is cracking: open to outer cults and madness." when below `KORKU.bulaniklik_esik` (40); tooltip "Sanity: the mind's resistance against leaks, forbidden knowledge and Outer Things".
   - Life line (mortals, `yasamHtml`): "N years old · M years left" / "N years old · immortal" / "died at N years (world year Y)"; "lifespan base + medicine +x + important +y = effective"; "ages K years per epoch" or "time flows ×Z on this world: ages K years per epoch". Tooltip names rule `DUNYA_MOTORU.onemli_omur`.
   - Carrying capacity (`kapasiteHtml`, peoples/settlements): "[region link ·] region's carrying capacity", "pop / capacity", meter (red when ≥100 %), "full N%[ · K communities share][ · region is more crowded than it can carry; growth stops, famine and migration pressure rise]".
   - **Adjust stats** collapsible (`statDuzenHtml`): one mini-form per stat (type stats + Sanity for agent types + Devotion `adanmislik` 0..`DERIN_YASAM.adanmislik_tavan`(200) for cults or when present): label with "min–max", number input with min/max, ✓ button → `POST /api/varliklar/:id/stat {stat, deger}`; toast "<label> set".
6. **Society and economy (Toplum ve ekonomi)** (`toplumHtml`, peoples/settlements with `toplum.k`): stacked class-share bar (fixed order scribe, artisan, priest, merchant, warrior, farmer; unknown classes last in "other" colour; segment width ∝ share; tooltip "Class N%"). Per-class rows: coloured dot, class name + "%share", satisfaction value and meter (≥50 green, ≥`DERIN_TOPLUM.ayaklanma_memnuniyet`(22) amber, else red). Granary chips: Food (Erzak), Ore (Maden), Goods (Mal) with amount and price band: ≥`fiyat_ust`(400) "very expensive", ≥`fiyat_kitlik`(180) "expensive", ≤`fiyat_bolluk`(70) "cheap", else "normal"; tooltip shows price multiplier ×(price/100). Footnote: classes below the threshold may revolt.
7. **Wars (Savaşları)** — count; rows: status chip ("ongoing" red, or the outcome text / "ended"), war link, "N clashes".
8. **Relations with communities** (`iliskiler`, communities only) — rows: type icon, link, optional "blood feud · Epoch N" chip, history line "Epoch c: event (+d)" joined by " · ", right-aligned label + signed value; class `iyi` when ≥`KURAL.iliski_dost`(15), `kotu` when ≤ −`KURAL.iliski_dusman`(35).
9. **Depth (Derinlik)** — subtitle "written in Epoch N" or "history, rumours, mortals' sayings". Body: history prose; type-specific block (`G.K.OZEL[tur]` → title + definition list of `[label, value]`, e.g. a people's "What it really wants"); sayings cards (type + text); "Details" list; "Rumours" italic list; "Hidden truth" collapsible secret. Empty: "Not yet deepened: its history, rumours and mortals' sayings are not written. It also happens by itself at epoch end." Button **Deepen / Re-deepen** (Derinleştir / Yeniden derinleştir) → `POST /api/varliklar/:id/derinlestir`, toast "Deepening…", disabled while job `v<id>:derin`.
10. **Knowledge / law panel** — if a knowledge entity (`dal`): "<branch name> · level N", branch effect text, "Knowers: …" (or "nobody") and "former knowers: …". If a law (`yasa_mekanik`): "How the law works" + mechanic description from `G.K.YASA_MEKANIKLERI`.
11. **Knows (Bildikleri)** — chips "<name> · <branch> <level>" linking to the knowledge.
12. Peoples only: **Beliefs (İnançları)** — subtitle "tells of N gods in its own way" / "what they tell about the gods". Belief cards (3.2.6 `inancKart`): header "<son link> — what they tell", quoted name, narrative, collapsible "God's eye: the truth" with the misconception. Empty: "This people has not yet written its own story about the gods." + belief form (3.2.6, people fixed). **What its historians wrote** — cards "Epoch N · historian X / anonymous historian" + text, newest first; empty "This people has no historian yet. As epochs close it writes from its own eyes."
13. **Hand of God (Tanrının eli)** — 3.1.4 (only canon, not law/language).
14. **God's power (Tanrının gücü)** — 3.1.5.
15. **Arrange and command (Düzenle ve buyur)** — 3.1.6.
16. Maker / language chips: "maker: <link>", "language: <link>".
17. **Lexicon (Sözlük)** (languages) — "N words · speakers: …"; table Word / Meaning (+ part of speech, example in italics) / Origin; first 60 rows; then "Full list is in the Lexicon tab."
18. **Owns (Sahip oldukları)** — rows with 64 px thumbnail or type icon; for items: damage / protection / might; for resources: "abundance N · value M".
19. **Lineage (Soy)** — ancestors (oldest first, dead struck through) → **self** → descendants.
20. **Produced and founded (Ürettikleri)** — type tag + link + subtype.
21. **Bonds (Bağlar)** — 3.1.7.
22. **May be related (İlgili olabilir)** — "shared bonds, same region, same creator"; cards with type icon, name, subtype or type, reason, similarity score (decimal comma).
23. **How are they connected? (Nasıl bağlı?)** — "shortest bond chain between two things". Search input with datalist (all names except self, capped at 600) placeholder "How is <name> connected to …? Type a name…". On `change`: exact-name lookup in `G.ADLAR_ID` (error toast "Nothing has this name."), `GET /api/yol?a=v<id>&b=<t><id>`, result stored per entity in `YOL_SONUC` (survives re-renders) and drawn via `yolZinciriHtml` (Graph view helper; "No bond found within six steps…" when none).
24. **My notes (Notlarım)** — "only for you; saved automatically". Textarea (max 4000). Status line: "typing…" on input; autosave 900 ms after last keystroke and on blur → `POST /api/varliklar/:id/not {metin}`; "saving…" → "saved" / "could not save" + error toast.
25. **Mentioned in (Anıldığı yerler)** — "N entities · M chronicle records"; chips linking entities whose description/depth mention the name.
26. **Inside (İçinde)** — contained entities: type tag, link, subtype.
27. **Images (Görseller)** — count; gallery (3.7.1); "Generate image" + upload zone; for `dis` the block is blurred (`dis-bulanik`). "Image prompt" eyebrow + prompt box (3.7.4) + button **Write prompt / Rewrite prompt** → `POST /api/varliklar/:id/prompt-uret`, toast "Writing prompt…", disabled during job `v<id>:prompt`.
28. **In the chronicle (Kronikte)** (`#varlikKronik`) — all chronicle entries (each wrapped with `data-kcag`), rendered by the Chronicle view's `entry()`. Empty "No record."
29. **Edit name, subtype and description** collapsible — Name (required, max 80), Subtype (max 60), Description (required) → `POST /api/varliklar/:id/duzenle {ad, alt_tur, aciklama}`; toast "<name> updated". Note: "Renaming also fixes the old name in the chronicle, bonds and all texts."
30. **Dangerous operations (Tehlikeli işlemler)** collapsible (`tehlike-bolge`):
    - If canon: **Delete from canon** (Kanondan sil), red, button `data-onay="Are you sure? Delete from canon"` → `POST /api/varliklar/:id/kanon {durum:'reddedildi'}`; toast "Canon updated". If rejected: **Break Fate, take into canon** (Kader'i boz, kanona al) → `{durum:'kanon'}` (no confirmation).
    - **Merge with another entity** (Başka bir varlıkla birleştir): explanation "If two records are really the same: the chosen <type> record's bonds, contents, lexicon and images move to <name>; that record becomes 'merged'. Irreversible." Name input with datalist of same-type entities; **typed confirmation input placeholder "BİRLEŞTİR"** (MERGE); button Merge. Client errors: "No such entity of the same type was found." / "Type BİRLEŞTİR to confirm." → `POST /api/varliklar/:id/birlestir {diger_id, onay:'BİRLEŞTİR'}`; toast "<other> was merged into this record".

#### 3.1.3 Tag chips (etiketler) catalogue — `ETIKET_CIP`, `etiketChip`

Tags are strings on the entity. Known tags map to `[css class, icon, label, tooltip]`. Classes: `c-altin` gold, `c-uyari` amber, `st-surgun` red, `c-mor` purple, `c-yazi` blue/text, `c-tehlike` danger, `c-sonuk` faded, `st-hazir` green. Full list (English label — original):
legendary (efsanevi, gold), godless (tanrısız, amber), cursed (lanetli, red), ghost (hayalet, purple), sorcerer (büyücü), ruin (harabe), wonder of the world (harika), lost knowledge (kayıp), captive (esir), ongoing (suruyor), ended (bitti), god's corpse (tanrı cesedi), empty tomb (boş mezar), god-slayer (tanrı katili), prophecy came true (yorum:dogru), misread (yorum:yanlis_yorum), self-fulfilling (yorum:kendini_gerceklestiren), fable (masal), corrupted memory (bozulmuş bellek), born from belief (inançtan doğdu), unique resource (özgün kaynak), native (yerli), immortal (ölümsüz), worships the planet (gezegene tapar), cosmic archive (kozmik arşiv), ensouled (ruhlu), soul harvester (ruh hasatçısı), two-timed (iki zamanlı), time echo (zaman yankısı), golem, mirror (ayna), cosmic plague (kozmik salgın), planet closed (gezegen kapattı), omen (alamet), empire (imparatorluk), independent (bağımsız), chosen (seçilmiş), exile (sürgün), oath-breaker (yeminbozan), agent selected (ajan seçili), colony (koloni), outer cult (dış tarikat), mutant, chimera (kimera), hybrid (melez), megafauna, invasive (istilacı), cosmic resource (kozmik kaynak), cosmic monopoly (kozmik tekel), wandering market (gezgin pazar), void pirate (boşluk korsanı), depleted (tükendi), manifested (tezahür etti). Each has an English tooltip in the source (e.g. "Exiled to another world by a god").

Hidden internal tags (never shown): regex `^(dal|yasa|iplik|savas|ceset):` and `dilden-ad`.
Prefixed tags `prefix:value`: `unvan:` title (gold), `zafer:` "<x> victory", `sonuc:` outcome, `taraf:<id>` "side: <entity>" (link), `ortak:<sonId>` "joint creation" (son link), `dirilis:<sonId>` "awaiting resurrection" (son link), `sinif:` social class name, `ozellik:` species trait name (tooltip = trait effect), `bağımlı:<id>` "dependent: <resource>" (amber link), `mekanik:` resource mechanic, `basamak:<n>` civilization tier (names: tribe, city-state, kingdom, world empire, interstellar power, cosmic power), `yazi:` writing system (alphabet, syllabary, pictographic, knot script, carved script). Anything else: `#tag`.

#### 3.1.4 Hand of God panel (Tanrının eli) — `mudahaleHtml`

Shown when `durum='kanon'` and type is not `yasa`/`dil`. Subtitle "intervene directly with your divine essence". All buttons (except dream) → `POST /api/varliklar/:id/mudahale {eylem, tur, bilgi_id}` where `bilgi_id` is the current value of the knowledge select (sent always, may be undefined); success toast "Intervention done" (Müdahale gerçekleşti). Costs from `G.K.MUDAHALE_BEDEL` (server defaults mucize 15, afet 20, bilgi 12, lanet 15).

| Row | Buttons | Body | Confirm | Disabled when |
|---|---|---|---|---|
| Miracle (Mucize) | One per `G.K.MUCIZELER`: Healing (Şifa), Abundance (Bereket), Peace (Barış), Protection (Koruma); tooltip = effect text; shared cost shown once at row end | `{eylem:'mucize', tur:<key>}` | none | not enough essence; or the miracle would change nothing (client mirror of server rule, `mucizeBos`): Peace — "<name> is not hostile to anyone"; Abundance — no abundance/prosperity/plenty stat, or already 100; Healing — no population, followers or (mortal) life below `MUDAHALE.sifa_can`(100), and not cursed; Protection — already protected and defence 100. Cult with a `dirilis:` tag: every miracle allowed. |
| Disaster (Afet) — only regions, places, settlements | One red button per `G.K.AFETLER`: Earthquake, Flood, Plague (Salgın), Drought, Storm; tooltip effect | `{eylem:'afet', tur:<key>}` | button `data-onay` "Are you sure? Send <disaster>" | not enough essence |
| Curse (Lanet) | Curse (Lanetle) | `{eylem:'lanet', tur:''}` | "Are you sure? Curse" | not enough essence; already cursed and every curse stat (refah, bereket, guc, savunma, servet, bolluk, etki) is ≤0: "<name> is already cursed and has no stat left to lower" |
| Knowledge (Bilgi) — thinking types (halk, yerlesim, hizip, tarikat, olumlu, tur) and only if any knowledge exists | Select of not-yet-known, non-rejected knowledge ("<name> · <branch>[ · <world>]") + Teach knowledge (Bilgi öğret) | `{eylem:'bilgi', tur:'', bilgi_id}` | none | not enough essence; if all known, select replaced by "It already knows all knowledge in the world." |
| Send dream (Rüya gönder) — thinking types | Textarea (max 600; placeholder about a salt door in the north) + Send | `POST /api/varliklar/:id/ruya {metin}` | none; client error "The dream must have content." if <5 chars | not enough essence for `bedel('ruya')` (RUYA_BEDEL). Toast "Dream sent; it will see it on its next turn"; textarea cleared on success. Subtitle "<name> sees this on its next turn and interprets it". |

#### 3.1.5 God's power panel (Tanrının gücü) — `tanriGucuHtml`

Every button is a form `POST /api/varliklar/:id/<path>` with optional cost (disabled via `ozEngel(cost, {mesgul:true})` → also disabled while the world is busy) or a gain badge. All numbers come from World rules group `TANRI_GUC` (defaults in parentheses), and tooltips cite the rule location.

**Dead mortal** (`tur='olumlu'`, `durum='olu'`, not tagged `tanrılaştı` (deified)): the panel shows only header "<name> died · Epoch N" and **Recall from death** (Ölümden geri çağır) → `POST …/dirilt`; cost `olumlu_dirilt`(40) + power level × `olumlu_dirilt_guc`(2); confirm "Are you sure? <name> will rise"; toast "<name> returned from death"; tooltip: re-enters canon, life becomes `olumlu_dirilt_can`(50), if died of old age lifespan +`olumlu_dirilt_omur`(20) years, bonds closed by death stay closed.

Otherwise hidden unless `durum='kanon'` and type ≠ `bolge`. Rows:

- **Essence (Öz)** — living mortals:
  - **Drain from life** (Canından em) → `oz-em` (empty body); gain `round(round(life × olumlu_em_pay(50)/100) / olumlu_em_bolen(10))`; confirm "Are you sure? Its life will be drained"; toast "Drained from its life".
  - **Devour life and soul** (Canını ve ruhunu yut), red → `oz-em {yut:"1"}`; gain `round(life/olumlu_em_bolen + powerLevel × olumlu_guc_oz(2))`; confirm "Are you sure? <name> will die"; toast "<name> was devoured".
- **Choice (Seçim)** — living mortals:
  - If tagged `peygamber`: chip "your prophet"; else **Make my prophet** (Peygamberim yap) → `peygamber`; cost `peygamber`(20); no confirm; tooltip: charisma +`peygamber_karizma`(15), worships you, community faith +`peygamber_inanc`(10), each epoch `peygamber_donus_sans`(15)% chance to convert its people.
  - **Raise to heaven: deify** (Göğe al: tanrılaştır) → `tanrilastir`; cost `tanrilastir`(150); confirm "Are you sure? <name> will become a god"; toast "<name> joined your sons"; tooltip: becomes a new son of a rarity by power level (max Legendary); the mortal record stays in history; its worshippers worship the god.
- **Death (Ölüm)** — living mortals with `olum` info: input "how (optional)" (max 300, `nasil`) + **Take its life** (Canını al), red → `POST …/can-al {nasil}`; cost `olum.tanri_bedel`; confirm "Are you sure? <name> will die"; toast "<name>'s life was taken". Side note: "for a son: <ogul_bedel> essence and <yuzde>% chance · protectors: …" where protector kinds map hami→patron, yaratici→worships the creator, esya→protecting item, korunmuş→protected, seçilmiş→chosen (with names).
- **Harvest (Hasat)** — communities (halk, yerlesim, hizip, tarikat): **Harvest its faith** (İnancını hasat et), red → `hasat`; N = population or followers or members; sacrifice = round(N × `hasat_nufus`(10)/100); faith = min(stat faith, `hasat_inanc`(20)); gain = round(sacrifice / `hasat_nufus_bolen`(500) + faith × `hasat_inanc_oz`(1)); confirm "Are you sure? <sacrifice> lives will be sacrificed"; toast "Faith harvested".
- **Faith (İnanç)** — mortals and communities:
  - **Convert to yourself** (Kendine çevir) → `cevir`; cost `cevir`(30); confirm "Are you sure? It will abandon its previous god"; toast "<name> now worships you"; tooltip: stops worshipping sons/foreign gods; the robbed son's loyalty −`cevir_kin`(10).
  - If tagged `soy laneti`: **Lift lineage curse** → `soy-laneti {kaldir:"1"}`, cost `soy_laneti_kaldir`(20), no confirm. Else **Curse its lineage** (Soyunu lanetle), red → `soy-laneti`, cost `soy_laneti`(40), confirm "Are you sure? The whole lineage will be cursed"; tooltip: it and descendants up to `soy_derinlik`(6) generations, stats −`soy_stat`(10), the unborn inherit it.
  - **Appear awake and speak** (Uyanıkken görün ve konuş) form → `POST …/tezahur {soz}`; textarea required, max `tezahur_uzunluk`(600); cost `tezahur`(10); toast "<name> saw you"; form resets. Explanation: not a dream — heard as a clear command next turn; faith +`tezahur_inanc`(10); `tezahur_tapin_sans`(30)% chance to start worshipping you.
- **Wrath (Gazap)** — every non-mortal type: input "Why? Written in the chronicle" (`sebep`, max 300) + **Destroy** (Yok et), red → `POST …/gazap {sebep}`; cost `gazap_taban`(60) + power × `gazap_guc`(5); confirm "Are you sure? <name> will be destroyed"; toast "<name> was destroyed"; tooltip: record destroyed, contents fall to the parent location, named mortals inside die with `gazap_olum`(70)% chance.

#### 3.1.6 Arrange and command panel (Düzenle ve buyur) — `buyurHtml`

Header "Arrange and command — direct assignments; the world continues on its own from there". Each row = label (icon + name) + body. Rows appear conditionally:

| Row (Turkish) | Shown for | Control | Endpoint & body | Notes |
|---|---|---|---|---|
| Move (Taşı) | types with allowed parent types (`konum`) | name input with datalist of entities of allowed parent types (options labelled with their world in multi-world), button Move | `POST /api/varliklar/:id/tasi {konum_id}` (transform `hedef`, field from `data-alan`) | Toast "<name> moved". Multi-world note: moving to a place on another world moves it and its contents to that world. Datalist capped at 800. |
| Patron (Hamisi) | communities and mortals | "currently: <patron>" (creator name / son name / foreign god link "(foreign god)" / "godless"); select: creator "(the creator himself)" value 0, each living son (+ " · <world>"), optgroup "Foreign gods" (living foreign gods on this entity's world, plus the current one) value `y:<id>`, "Leave godless" value `yok` | `POST /api/varliklar/:id/hami` body `{ogul_id:<n>}` / `{ogul_id:null}` / `{yabanci_id:<n>}` | Toast "Patron assigned". Current patron = active outgoing `tapar` (worships) bond to o/t/y. |
| Command (Buyruk) | communities | select peace/alliance/trade/war + "with" + community name input (datalist: other non-rejected communities, labelled "<world>", "<world> · via open route" or "<world> · no route: peace only") + Command | `POST /api/varliklar/:id/buyruk {tur:'baris'|'ittifak'|'ticaret'|'savas', hedef_id}` | Toast "Command descended". Multi-world note when some worlds unreachable: war/alliance/trade only with communities on this world or worlds linked by an open route. |
| Agent (Ajan) | halk, yerlesim, hizip, tarikat, olumlu, tur | checkbox "Must act this epoch" — auto-submits on change (`data-otomatik`); green chip "agent selected" when on | `POST /api/varliklar/:id/ajan {secili: bool}` | Toast "Agent selection removed" / "Will surely act this epoch". Reflects tag `ajan seçili`. |
| Exile (Sürgün) | communities and mortals, multi-world only | select of other, non-forgotten (`kesif!=='unutulmus'`) worlds + red Exile | `POST /api/varliklar/:id/surgun {dunya_id}` | Confirm "Are you sure? Exile"; toast "<name> was exiled"; note "to that world's most dangerous land". |
| Pardon (Af) | entities tagged oath-breaker, exile or cursed | Pardon (Affet) | `POST /api/varliklar/:id/af {}` | Toast "<name> was pardoned"; note "oath-breaker, exile and curse marks are removed". |
| Bind soul (Kapla) | canon `ruh` (soul) | name input (items, vehicles, works) + Bind | `POST /api/kozmik/ruh {ruh_id, hedef_id}` | Cost `G.K.KOZMIK_BEDEL.ruh`; toast "Soul bound". |
| Bonds (Bağlar) | all | **Let Fate suggest bonds** | `POST /api/varliklar/:id/bag-oner {}` | Toast "Fate is looking at bonds for <name>"; tooltip "No bond without evidence; at most `AG.oneri_tavan`(3) bonds, with reasons"; side text "has N bonds". |
| Rite (Ayin) | canon entity with `oluTanrilar` (it worships a dead son) | select dead god, select rite: prayer (dua), wealth offering (servet), blood sacrifice (kan), life sacrifice (self; mortals only, `can`) + Order rite | `POST /api/varliklar/:id/ayin {ogul_id, tur}` | Toast "Rite offered"; note "devotion for the dead god's return; <name> pays the cost". |
| Exploration (Keşif) | canon communities/mortals | select "region or place" (''), "new region" (bolge), "new place" (yer) + Send exploring; multi-world: Search a path to the sky (Göğe yol arat) | `POST /api/varliklar/:id/kesif {tur}`; `POST /api/varliklar/:id/yol-ara {}` | Toasts "An unknown land was found" / "The sky's path was shown". Text "spontaneous exploration: N% per epoch (reasons)" from `kesif`. Sky tooltip depends on `kesif.yol`. |
| Expedition (Sefer) | communities/mortals | (a) currently travelling (`KOZMOS.veri.yolculuklar` with `yolcu_id`=id and `durum='yolda'`): "On the road: <target> · <intent> · arrives in N epochs / arrives this epoch" + ghost **Recall** button `data-sefer-geri` → `POST /api/yolculuklar/:id/geri`, confirm "Are you sure? Recall", toast "Expedition recalled". (b) else if open, known routes from this world: route select "<other world> · <method> · N epochs", intent select (colony, trade, exploration, conquest, pilgrimage), "% of population" number (min 1, max `TANRI_ELI.sefer_tavan`(30), default `sefer_yuzde`(10), only if it has population) + Send on expedition → `POST /api/varliklar/:id/sefer {rota_id, niyet, yuzde}`, toast "Expedition set out". (c) else multi-world canon: "There is no open route out of <world>; open one in Cosmos first or wait for a closed route." | |
| Archive (Arşiv) | all | chip "in history" / "in Atlas" + " · importance N" (tooltip reason); select auto / keep in Atlas / sink into history + Assign | `POST /api/varliklar/:id/arsiv {durum:'otomatik'|'atlas'|'tarih'}` | Toast "Archive state set"; note "Records whose importance falls sink into history automatically." Current = `arsiv_elle` 1→tarih, 0→atlas, null→otomatik. |
| Name suffixes (Ad ekleri) | all | `ekFormHtml` | `POST /api/ek {t:'v', id, okunus, tamlama, sifirla?}` | **LANGUAGE-SPECIFIC: drop.** Lets the player set how the name is "pronounced" for Turkish vowel/consonant harmony (`okunus`, e.g. "on") and whether it is a compound (`tamlama`), with live examples of genitive/dative/locative forms (`ekle(ad,'ilgi'|'yonelme'|'bulunma')`); "Automatic" (Kendiliğinden) button resets via an inline `onclick` setting hidden `sifirla_h`. |
| Cosmic deposit (Kozmik yatak) | regions and places | Open "<resource> deposit" | `POST /api/kozmik/yatak {bolge_id}` | Disabled with "Define the cosmos's travel resource in the Cosmos tab first" unless `G.S.dunya.kozmik_kaynak` (JSON) exists. Toast "Cosmic resource deposit opened". |
| Tags (Etiketler) | all | toggle-button grid (`filtre-dugme`, `on` + `aria-pressed` when present) for `G.K.ETIKETLER` (fallback list: wonder, cursed, godless, ruin, megafauna, invasive, cosmic resource, unique resource, chosen, native, colony, independent, empire, outer cult, fable) | `POST /api/varliklar/:id/etiket` `{ekle:[tag]}` or `{sil:[existingTag]}` | Toast "<tag> added/removed". A tag counts as present if equal or (for prefix tags) startsWith `tag:`. |
| Traits (Özellikler) | species (`tur`) | toggles `ozellik:<key>` labelled with `G.K.OZELLIKLER[k].ad` | same | |
| How it works (İşleyişi) | laws | toggles `yasa:<mechanic>` for each `G.K.YASA_MEKANIKLERI` except `yok` (tooltip = description) | same | |
| Resource rule (Kaynak kuralı) | resources | toggles `mekanik:<key>` for `G.K.KAYNAK_MEKANIKLERI` (except `kutsal`); sacred: if tagged `mekanik:kutsal:<sonId>` toggle "sacred: <son>", else son select + "make sacred" → `{ekle:['mekanik:kutsal:<sonId>']}` (toast "Resource was consecrated to a son") | same | Row tooltip lists all mechanics. |

#### 3.1.7 Bonds section (Bağlar) — `bagGruplari`, `bagKurHtml`

Header "Bonds N[ · K past]". Bonds come from `baglar[]` (`{id, tur, yon:'out'|'in', diger_tip, diger_id, diger_ad, aciklama, gecmis, borc?}`); incoming `icinde` (contains) bonds are excluded. Grouped by `direction:type`, groups sorted by size desc. Group header: outgoing "<name> **<label>** →", incoming "← **<label>** <name>", count. Label from `G.K.BAG_ETIKET[type]`.
- Each bond is a chip (link via `hedefAttr`; icon for son / god / world), past bonds prefixed "formerly" (eskiden) and styled `gecmis`; description appended truncated to 40 chars + "…".
- **Debt bonds** (`borclu` with `borc`): rendered as debt cards: "X owes Y N <what>" with chips "overdue · Epoch V" (red) or "due Epoch V"; group title "Debts" (out) / "Receivables" (in). (The Turkish sentence uses a dative suffix via `ekle` — LANGUAGE-SPECIFIC: drop.)
- **Break bond** button (scissors icon) on each bond except `icinde`: `data-bag-sil=<bondId>` + `data-onay="Break"` (two-click) → `POST /api/baglar/:id/sil`; toast "Bond broken".
- Empty: "No bonds."

**Create bond** collapsible (Bağ kur) — fields: Direction ("<name> → target" / "target → <name>"), Bond type select (all `G.K.BAG_TURLERI` except `icinde`, sorted by label), Target (name input with datalist of all non-rejected entities and sons except self, labelled with world; "son · <world>" for sons), Description (optional, max 200, placeholder "e.g. 12 silver; due Epoch 15"). Transform `bag` → `POST /api/baglar {kaynak_tip, kaynak_id, hedef_tip, hedef_id, tur, aciklama}` (swapped when direction is `in`); toast "Bond created"; form resets. Error "Pick the target from the list."

#### 3.1.8 Empty / loading / error states

The drawer has no skeleton: the previous content stays until the new HTML resolves; failures toast the error message (non-silent opens only). Empty texts are listed per section above.

---

### 3.2 Son page drawer (Oğul sayfası) — `views/ogul.js`

**Opened by** any `data-o`, Pantheon card click (`.card[data-o]`), palette. Marks onboarding step `kart` done.

**Data (parallel):** `GET /api/ogullar/:id` (server `ogulDetay` = `sonPublic` + detail), `GET /api/ogullar/:id/sohbet` (chat history; errors → []), `GET /api/defter?kim_tip=o&kim_id=:id&limit=60` (action ledger), opportunities (`firsatlariYukle`), world map of entities.

Fields used: `ad, unvan, nadirlik, nadirlik_ad, yildiz, model, seviye, xp, durum ('aktif'|'uykuda'|'surgun'|'olu'…), olum_cag, alan1, alan2, can, can_max, oz, oz_max, inanc, un, varlik, varlik_durumu{k,ad,etki}, eylem, guc_tavani, tur_ap, tur_cag, aktif_dunya, capa, ebeveyn, cocuklar[], plan, emir, emir_mutlak, asi, zincirli, statlar{9}, tutku{sadakat,hirs,ofke,merhamet}, gucler[{ad,etki,param,aciklama}], acik_guc, kisilik{gorunus,mizac,takinti,korku,uslup,sir}, varolus{doga,hal,tezahur,gercek_ad}, destan{baslik,dize,destan,cag}, yildiz_sarti{seviye,un,oz}|null, yukselis{seviye,un,oz,hedef}|null, oldur_bedel, dirilis{adanmislik,kalan,en_erken,sadik[],tarikatlar[]}, ceset_id, itibar{etiket,sevgi,korku,unutma,cevapsiz,son_temas,elle{}}, halklarin_gozunden[], kardesler[{id,ad,nadirlik,deger,kapak,not_}], baglar[], tapanlar[], yaratimlar[], mesajlar[], kronik[], gorseller[], gorsel_prompt, ek`. Also `G.S.bekleyen` (sons eligible to act this epoch) and `G.S.mesgul`.

#### 3.2.1 Hero

- Portrait: cover image 320 px (`data-glb="o:<id>"`) or procedural **sigil** (`sigil(name, rarityHex, raritySortIndex, 150)`) inside the generate-image overlay; dagger when dead.
- Eyebrow (in rarity colour, muted when dead): "<rarity name> ★★★☆☆ · <Model> · Level N[ · died, Epoch N]". Stars: `stars(n, YILDIZ_MAX=5)` = n filled "★" + remaining in `.off`. Model name: capitalised model id (`haiku` → "Haiku"), tooltip "The language model that makes this son think".
- Name ("†" prefix if dead), subtitle = title (`unvan`).
- Chips: domain 1, domain 2 (with domain glyphs); life "can/can_max"; essence "oz/oz_max"; faith (`fmt`); fame (`un`); existence chip `v-<state>` "<state name> <value>"; fading badge (`solusRozet`: red "being forgotten · fades in N epochs" with tooltip on existence/threshold/duration, from `G.S.solus`); "half turn · N actions left" (amber) if `tur_ap` set for the current epoch and alive (tooltip: "This epoch's turn stopped midway; Complete epoch resumes it"); "N actions · G<cap>" (tooltip "N actions per epoch; strongest thing it can create is power level cap"); multi-world: current-world button (opens map); "anchor: <entity>"; "parent: <son>"; "child: <son>" per child.
- Plan line (italic, ids rendered as names) if `plan`.
- Actions: **Print page** → `/kitap?ogul=<id>` (new tab; "you can save as PDF"), **Bookmark** toggle (Yer imi / Yer iminde; gold when on).

#### 3.2.2 Dead panel (only `durum='olu'`)

Header "<name> died · Epoch N". Text: body lies as "bones" (link to `ceset_id`); loyal followers' resurrection cult accumulates devotion; at `DERIN_YASAM.dirilis_adanmislik`(100) the resurrection rite succeeds with `DERIN.dirilis_sans`(50)% per epoch, no earlier than `OLUM.dirilis_en_az_cag`(3) epochs after death. If `dirilis`: chips "devotion X/threshold" (green when reached), "earliest in N epochs (Epoch E)" / "can return", "N loyal communities"; meter (legendary colour); "Waiting: cult (devotion), …" or "No resurrection cult left; the first rite spawns a new one."; "Loyal: …" (first `FIRSAT.liste_genis`(6)); explanatory paragraph about automatic return paths (`OLUM.ayin_sans` 20 %, `kurban_sans` 5 %, ×`hac_carpan`/100 at the bones, sibling schemes, enemies scattering bones). Button **Resurrect by your own hand** (Kendi elinle dirilt), gold → `POST /api/ogullar/:id/dirilt`; cost `G.K.DIRILIS_BEDEL`; disabled while busy / insufficient essence; toast "Death was withdrawn"; **no confirmation**.

#### 3.2.3 Hand of God panel (son) — all god-power controls

| Control (EN — TR) | Endpoint / body | Cost / gain | Confirm | Disabled / hidden | Toast |
|---|---|---|---|---|---|
| Order textarea (emir), prefilled with current `emir`, placeholder "Order for its next action: 'Send a plague to your brother's city.'" | — | — | — | — | — |
| **Announce order** (Emri bildir) | `POST /api/ogullar/:id/emir {metin}`; empty text clears the standing order | free | — | disabled when dead ("The dead take no orders") | "Order announced" / "Standing order removed"; marks onboarding step `emir` |
| **Absolute command** (Mutlak buyruk) | `POST /api/ogullar/:id/mutlak-buyruk {emir}` (uses the order textarea; focuses it if empty) | `TANRI_GUC.mutlak_buyruk`(25) | button `data-onay` "Are you sure? It cannot refuse" | dead; insufficient essence | "Irrefusable command given". Tooltip: does it first next turn; loyalty −`mutlak_sadakat`(5). Red chip "ongoing absolute command" when `emir_mutlak`. |
| **Act now** (Şimdi harekete geçir), primary | `POST /api/ogullar/:id/hareket` | free | — | dead ("A dead son cannot act"); not in `G.S.bekleyen` ("Acted this epoch, asleep, chained, exiled or fading"); world busy | none |
| Bless row (Kutsa): **+20 essence** | `POST /api/ogullar/:id/kutsa {tur:'oz', stat:<kStat>}` | `COSTS.kutsa_oz`(15) | — | dead; essence full ("Essence already full (x/y): blessing adds nothing"); insufficient | "Blessed"; marks step `emir`. Tooltip "Essence a/b → min(b, a+`TANRI_EYLEM.kutsa_oz`(20)); loyalty +`kutsa_sadakat`(3)" |
| **Fill life** (Canı doldur) | `{tur:'can'}` | `COSTS.kutsa_can`(15) | — | dead; life full | same |
| **Remember him (+20 existence)** (Onu an) | `{tur:'varlik'}` | `COSTS.kutsa_oz` | — | dead; existence ≥100 | same |
| Stat select (`kStat`): each son stat "Name · value", stats at 100 disabled "(at top)", first non-max preselected; **+5 stat** | `{tur:'stat', stat}` | `COSTS.kutsa_stat`(40) | — | dead; all stats 100; insufficient | same |
| Punish row (Cezalandır): **Lightning** (Yıldırım), red | `POST /api/ogullar/:id/cezalandir {tur:'yildirim'}` | `COSTS.yildirim`(10) | "Are you sure? Let lightning strike" | dead | "Judgment given" (Hüküm verildi) |
| **Chain this epoch** (Bu çağ zincirle), red | `{tur:'zincir'}` | free | "Are you sure? Chain this epoch" | dead; already chained; not eligible this epoch ("Already acted or cannot act; the chain doesn't carry to next epoch") | same |
| **Exile** (Sürgün et), red — or **Pardon** (Affet) when exiled/chained | `{tur:'surgun'}` / `{tur:'af'}` | free | exile: "Are you sure? Exile" | exile disabled when dead | same |
| Essence & death row (hidden when dead): **Drain its essence** (Özünü em) | `POST /api/ogullar/:id/oz-em` | gain `round(round(oz × ogul_em_pay(50)/100) × ogul_em_verim(80)/100)` | "Are you sure? Its essence will be drained" | essence 0 ("No essence left") | "Essence drained". Tooltip: loyalty −`ogul_em_sadakat`(10), anger +`ogul_em_ofke`(15); siblings bound by fear. |
| Reason input "Why? Written in the chronicle" (max 300) shared by Devour/Kill | — | — | — | — | — |
| **Devour** (Yut), red | `POST /api/ogullar/:id/yut {sebep}` | gain `oz + kudret × ogul_yut_kudret(3) + level × ogul_yut_seviye(20)` | "Are you sure? <name> will be devoured" | world busy | "Devoured; its essence passed to you" |
| **Kill** (Öldür), red | `POST /api/ogullar/:id/oldur {sebep}` | `oldur_bedel` ?? `OLUM.tanri_ogul_oldur`(100) | "Are you sure? <name> will die" | busy; insufficient | "Son died". Tooltip: body becomes a corpse, loyalists a resurrection cult; others bound by fear, friends angered. |
| Rebellion row (only `asi`): red chip "In rebellion against his father"; **Suppress rebellion** (İsyanı bastır), red | `cezalandir {tur:'bastir'}` | `bedel('bastir')` | "Are you sure? Suppress the rebellion" | insufficient | "Judgment given"; tooltip "Your power is tested against its will and power; if you fail the cost still falls". **Forgive** (Bağışla) → `{tur:'af'}` |
| Star row (Yıldız): **Give ★N+1**, gold | `POST /api/ogullar/:id/yildiz` | `yildiz_sarti.oz` | — | dead; level < required; fame < required; insufficient | "Another star shone". Requirement text "level a/b · fame c/d" (green `ok` / red `no` per item). |
| **Ascend to <next rarity>** (… sınıfına yükselt), gold — only when at ★5 and a higher class exists (`yukselis`) | `POST /api/ogullar/:id/yukselt` | `yukselis.oz` (rule `YUKSELIS.oz` 90; requires level 9, fame 90) | — | same | none |
| If neither: "Reached the highest class and star." | | | | | |
| Class & power row (hidden when dead): **Lower to <previous class>** / Demote (Alçalt), red | `POST /api/ogullar/:id/alcalt` | `TANRI_GUC.alcalt`(40) | "Are you sure? It will be demoted" | already lowest class | "Lowered by one class". Tooltip: stats drop to the lower class cap; loyalty −`alcalt_sadakat`(15), anger +`alcalt_ofke`(25). |
| Power select + **Rip out its power** (Gücünü sök), red | `POST /api/ogullar/:id/guc-sok {sira:<index>}` | `TANRI_GUC.guc_sok`(30) | "Are you sure? The power will be ripped out" | insufficient; if no powers: text "It has no power to rip out." | "Power ripped out". Tooltip: `guc_sok_oz`(15) essence returns to you; anger +`guc_sok_ofke`(20). |
| World row (multi-world, alive): world select (non-forgotten; current marked "(current)") + **Send to world** | `POST /api/ogullar/:id/dunya {dunya_id}` | free | — | — | "<name> was sent to its new world". If `G.S.dunya.ogul_dagitim !== 'elle'`: note that distribution is automatic and a hand-sent son is protected from auto-distribution for `TANRI_ELI.atama_koruma`(3) epochs. |

Footnote: "If its Will is above `TANRI_EYLEM.asi_irade`(70), punishment lowers loyalty and grows anger; below it, it bows in fear. Stars give each stat +`yildiz_stat`(3); ★5 adds an action and opens ascension."

#### 3.2.4 Remaining sections (render order)

1. **This epoch's opportunities** (alive, if any): list of opportunity sentences (from Goals view helpers).
2. **How he sees his father** (Babasını nasıl görüyor; alive with `itibar`): reputation label chip (colour map `ITIBAR_RENK`: loved green, respected gold, feared amber, hated red, forgotten/distant faded, known plain), "N unanswered prayers" chip, "last contact: Epoch N"; three meters (Love green, Fear red, Forgottenness muted, 0–100). Three nudge buttons, each a form `POST /api/ogullar/:id/itibar` with a single numeric field: **Win his heart** (Gönlünü çel) `{sevgi: +ITIBAR.elle_sevgi(10)}`, **Spread fear** (Korku sal) `{korku: +elle_korku(10)}`, **Remind him of you** (Kendini hatırlat) `{unutma: −elle_unutma(15)}`; toast "<name>: <action>". Disabled at the manual cap ±`ITIBAR.elle_tavan`(60) per axis (tooltip says it decays each epoch). Status: "your nudges: love +x, … (decay each epoch, remaining share `elle_kalan`(60)%)" or "Nudges fade each epoch; reputation also changes with your deeds."
3. **Talk with him** (Onunla konuş) — chat (3.2.5).
4. **Epic (Destanı)** — "written in Epoch N"; title, verse line, prose (auto-linked). Empty "No bard has written this son's epic yet." Button **Write / Rewrite epic** → `POST /api/ogullar/:id/destan`, toast "The bard is writing…", disabled during `o<id>:destan`.
5. **Powers (Güçler)** — 3 slots (`G.K.GUC_SEVIYELERI` = levels 1, 3, 5). Empty slot: locked card "Unawakened power". Filled: name, "<effect name>[ · <param type name>] · unlocked / unlocks at Lv N", effect description, italic flavour text; locked styling when index ≥ `acik_guc`.
6. **Existence (Varoluş)** — definition list: Essence nature, State, Manifestation; secret "True name (only you know)".
7. **Who he is (Kimdir)** — Appearance, Temperament, Obsession, Fear, Speech; secret "His secret".
8. **Edit** collapsible (title lists editable groups based on `G.K.OGUL_DUZEN_ALANLAR`) → `POST /api/ogullar/:id/duzenle`, toast "<name> edited". Fields: `ad` (max 60), `unvan` (max 120), `plan` (max 1200), `kisilik.{gorunus,mizac,takinti,korku,uslup,sir}` textareas, `tutku.{k}` sliders 0–100; if `statlar` editable: `statlar.{k}` sliders 1–100 with note (life/essence clamp to new caps; undoable from ledger); if `kaynak` editable: `nadirlik` select (Class), sliders `kaynak.yildiz` 1–5, `kaynak.oz` 0–oz_max, `kaynak.can` 0–can_max, `kaynak.varlik` 0–100, numbers `kaynak.un`, `kaynak.seviye`(min 1), `kaynak.inanc`; note "Changing class by hand is free and goes into the chronicle; use 'Class & power' above for an in-world demotion." Footer "Changes are canon; the son knows himself this way next turn." Inside also the **Name suffixes** row (LANGUAGE-SPECIFIC: drop) → `POST /api/ek {t:'o', …}`.
9. **Through the peoples' eyes** (Halkların gözünden) — belief cards "<people> remembers him so · Epoch N"; empty "No people has developed a belief about him yet. Peoples who worship him write their own stories as epochs pass." + belief form (son fixed).
10. **Stats** — full rows: icon, name + group (Body/Mind/Soul — Beden/Zihin/Ruh), value, meter in rarity colour, effect text (`SON_STATS[].etki`).
11. **Passions (Tutkular)** — "shape his actions and obedience": loyalty, ambition, anger, mercy; amber meters.
12. **Resources (Kaynaklar)** — life a/b, essence a/b, faith, fame, XP "xp/(level × `KURAL.xp_seviye`(100))", plus Existence row with state name, meter (epic colour) and text "Being worshipped, remembered and his anchor living feed existence."
13. **Images** — gallery + generate + upload; "Portrait prompt" box (saves via `POST /api/ogullar/:id/prompt {prompt}`).
14. **Siblings (Kardeşleri)** — per sibling: avatar, link, centred diverging bar (positive green to the right / negative red to the left, width |v|/2 %), label (`ilEtiket`: ≥`OGUL_ILISKI.baglilik`(60) devotion, ≥`dostluk`(25) friendship, >−`husumet`(25) distance, >−`nefret`(60) hostility, else hatred) and signed value; optional relationship note under it. Empty "No siblings."
15. **His hand in the world** (Dünyadaki eli) — bond groups (excluding `tapar`) with break buttons + **Create bond** form (source tip `o`). Empty "No trace in the world yet."
16. **Worshippers (Ona tapanlar)** — type tag, link, "N followers" / "N souls". Empty "Nobody yet."
17. **Creations (Yaratımları)** — thumbnail, link (struck through if rejected/destroyed), "subtype · Ç<n>[ · status]", type tag.
18. **Words (Sözler)** — messages excluding chat: icon (prayer / order from god / message), "**from** → to (intent): “text”", "Ç<n>". Intent labels via `etiket()`.
19. **Turns (Turları)** — "what he did each epoch · from the action ledger": grouped by epoch (newest first, first group open): summary "Ç<n> · K actions · M changes"; ordered list: tool display name (`eylemAdi(arac)`, raw tool id as tooltip), summary text; "undone" chip and `geri` class when `geri_alindi`. Empty "No turn of this son in the ledger."
20. **Trace in the chronicle** — entries; empty "None yet."

#### 3.2.5 Chat with the son (Onunla konuş) — `sohbetHtml`, `sohbetGonder`

State per son kept in memory map `SOHBET` (`{bekliyor, son, hata, taslak}`) so a pending message, last reply attitude and draft survive re-renders.
- Bubbles: god ("You · Epoch N") right; son (28 px avatar, auto-linked text, "<name> · Epoch N") left. While pending: the sent bubble ("You · now", class `gonderiliyor`) + typing indicator (three dots, "<name> is thinking…", `aria-live`).
- After reply: "Last reply" chip with attitude (`TAVIR`: loyal/grateful green, distant faded, frightened amber, rebellious red, mocking purple) + loyalty delta chip ("loyalty +d" green / "−d" red / "±0") and "→ new loyalty".
- Error: red line with message; the unsent text returns to the textarea.
- Empty: "You have never spoken with <name>. Say the first word." / dead: "You never spoke with <name>; now it's too late."
- Input textarea (max 800) disabled when dead or pending; placeholder "What do you say to <name>?" (LANGUAGE-SPECIFIC: hard-coded dative suffix `'e`) / dead "<name> is dead; your voice doesn't reach the bones." Send button **Say** (Söyle) → "Waiting" spinner. Enter sends, Shift+Enter newline (IME composition respected). Hint "Enter sends, Shift+Enter new line. The answer takes a few seconds."
- Send: `POST /api/ogullar/:id/sohbet {metin}` → response `{tavir, degisim, sadakat, …}`; re-renders the drawer and the Atlas detail if showing the same son, scrolls chat to bottom, then background `refresh()`.

#### 3.2.6 Belief card and form (shared with entity and creator pages)

- `inancKart({k, ust, ad, anlati, yanlis})`: header line, optional quoted given name, narrative (auto-linked), collapsible "God's eye: the truth" showing `yanlis` (what they got wrong).
- `inancFormHtml({halkId, ogulId, k})` collapsible "Add or change a people's account": People select (all peoples, sorted by world, "· <world>" in multi-world) unless fixed; God select (creator "(creator)" = 0, sons) unless fixed; "Name they gave him" (max 80, placeholder "Who Leaves the Shadow"); "What they tell" (required); "What they got wrong — only you see" → `POST /api/inanclar {halk_id, ogul_id, ad, anlati, yanlis}`; toast "Account written to canon"; overwrites an existing account for the same people+god; resets. If no peoples exist: "There is no people in the world yet; when one is born you can write its account here."

---

### 3.3 Creator-god page (Yaratıcı) — `views/tanri.js`

**Opened by** `data-tanri-ac` links, the god panel's **Epic and depth** button (`data-tanri-sayfa`) or **Images** button (`data-tanri-galeri`) on the Pantheon, command palette type `t`. Always `openDrawer('t', 1)`.

**Data:** `GET /api/tanri` (T), `GET /api/tanri/itibar` (IT), entity world map. If `/api/tanri` fails the drawer shows only the creator's image galleries (3.3.9).

#### 3.3.1 Hero
Portrait (cover `kapak` or gold sigil, generate overlay `t:1`, `data-glb="t:1"`). Eyebrow (gold) "Creator · immortal, indestructible". Name `T.ad`, subtitle `T.unvan`. Chips: mood label (class from `RUH_ETIKET`), "N faith" (or "less than 1" when cult exists but faith rounds to 0), "N communities worship", "N essence" (`G.S.dunya.tanri_oz`), gold "epic written" if any. Appearance prose. Button **Redraw his likeness** (Sureti yeniden çiz) `data-suret` → `POST /api/tanri/suret`; disabled during `t:suret`.

#### 3.3.2 Edit collapsible ("Edit title, appearance and temperament")
`POST /api/tanri {tanri_unvan (max 120), tanri_gorunus, tanri_mizac, tanri_prompt}`; toast "The creator's likeness updated"; note "A field left empty is deleted."

#### 3.3.3 Mood (Ruh hâli) — `ruhHtml(r, short)`
Subtitle "changes at each epoch end by faith, prayers and silence in the world". Header: eyebrow "Mood", label chip, explanation. Labels (`RUH_ETIKET`): angry (red) "The sky darkens; godless homes should fear.", distant and silent (faded), lonely (purple), pleased (gold), restless (amber), serene (blue). Four gauges (`RUH_OLCU`), each a 0–100 bar with a threshold tick and "active" chip when past threshold:
- Anger (Öfke), red, threshold `YARATICI.ofke_esik`(70), upward: wrath falls on godless/cursed lands.
- Contentment (Hoşnutluk), legendary gold, `hosnut_esik`(70), upward: blessing on worshippers.
- Attention (İlgi), accent, `ilgisiz_esik`(20), **downward** (active when ≤): sons feel abandoned, loyalty melts.
- Loneliness (Yalnızlık), epic purple, `yalniz_esik`(70), upward: the creator's light falls into seers' dreams.
Full mode adds the effect text and a "Last epoch: <input> +d · …" line from `r.girdi[key]` (decimal comma). Short mode (Pantheon god panel) omits both.
Collapsible "Set the mood yourself": four sliders → `POST /api/tanri/ruh {ofke, hosnutluk, ilgi, yalnizlik}`; toast "The creator's mood changed"; note: values are this epoch's starting point and drift afterwards.

#### 3.3.4 Reputation and passions (İtibarın ve tutkuların) — `itibarTanriHtml`
"In your sons' eyes" label chip + three meters (love/fear/forgottenness). List of sons: link, label chip, "love · fear · forgottenness" mono, "N unanswered prayers" chip. Passions chips (gold, tooltip hint) + "read from your recent deeds" (auto) or "chosen by you". Collapsible "Choose your passions yourself": checkbox per passion `t_<key>` (name + hint) and "Read automatically (drop my choice)"; transform `tutku` → `POST /api/tanri/tutku {tutkular:[...], otomatik:false}` or `{otomatik:true}`; errors "Pick at least one passion." / "You can pick at most `ITIBAR.tutku_sayi`(3) passions."; toast "Your passions were declared".

#### 3.3.5 Your own word (Kendi sözün — canon)
Explanation: everything written here is canon; every son, mortal, Fate and the chronicler sees it each turn. Textarea (max `TANRI_EYLEM.not_uzunluk`(6000)), **Write into canon** button → `POST /api/tanri/not {metin}`. Status line: on input "not saved"; on click "writing…" → "written to canon" / "could not write" (+ error toast); unchanged → "in canon". (Manual save, unlike the entity note's autosave.)

#### 3.3.6 Epic (Destanı)
"written in Epoch N · K chapters". Title, pull quote verse, chapters with Roman numeral (I–X, then arabic), chapter title, "Ç<start>[–<end>]", prose. Empty: "No bard has yet written the creator's epic. It is born from his traces, his sons and the peoples' tales." Button **Write / Rewrite his epic** → `POST /api/tanri/destan`, toast "The bard is writing the creator's epic…", disabled during `t:destan`.

#### 3.3.7 Depth
History prose; Names list (name, who calls him so, meaning); "His wish" quote; grid of lists Secrets / Fears / Prohibitions / Gifts; sayings; rumours; secret "Hidden truth (only you know)". Empty "The creator is not deepened yet: his names, secrets, fears and prohibitions are not written." Button Deepen → `POST /api/tanri/derinlestir`, toast "Deepening the creator…", disabled during `t:derin`.

#### 3.3.8 Peoples' eyes, cult, traces
- Through the peoples' eyes (belief cards + form with god fixed to 0/creator). Empty "No people has developed a belief about the creator yet."
- Cult (Kültü): "N communities worship him directly · total faith F"; list type tag + link. Empty "No community worships the creator directly yet. Answering mortals' prayers draws them closer."
- Traces of the god (Tanrının izleri): chronicle entries where the creator acted, newest first; empty "No trace yet."

#### 3.3.9 Image galleries (`tanriGaleriHtml`)
"The god's images" (`GET /api/gorseller?tip=t&id=1`): gallery + generate/upload + "Portrait prompt" box. "<world> world's images — map background, landscape, cover" (`GET /api/gorseller?tip=d&id=<selectedWorld or 1>`): gallery + upload. Multi-world with "whole cosmos" selected: note "Whole cosmos selected: the image is attached to the first world. To attach to another world pick it at the top."

---

### 3.4 Foreign-god page (Yabancı tanrı) — `views/yabanci.js`

**Opened by** `data-yabanci` links (Atlas, Cosmos foreign-god cards, text links). **Data:** `GET /api/yabanci/:id` (server `yabanciDetay`): the foreign-god row (`ad, unvan, durum ('uyanik'|'uykuda'|'yenik'|'olu'), alanlar, guc, inanc, tutum (−100..100), temas, olusturma_cag, yenilgi_cag, olum_cag, uyanis_baski, aciklama, gorsel_prompt, statlar, gucler, kisilik, varolus, derinlik`) + `dunya{id,ad,tur}`, `tapanlar[{id,ad,tur,alt_tur,nufus,murit,neden,cag,kapak}]`, `baglar[]`, `kronik[]` (recent entries mentioning the name, capped server-side), `ogullar[{id,ad,nadirlik,durum,burada,kronikte,kapak}]`, `gorseller[]`.

#### 3.4.1 Hero
Colour: mythic pink (`--r-mitik`), muted when dead. Portrait: cover or a purple god icon inside generate overlay (`y:<id>`); dagger when dead. Breadcrumb "Foreign god › <world>" (world is a link-button that closes the drawer, opens the Cosmos tab with the world panel and selects it). Name, title. Buttons: **Show his world in Cosmos**, **His world's guide** (`data-rehber`), **Open in book** → `/kitap#y-<id>`. Chips: status (`YT_DURUM`: awake amber, asleep faded, defeated purple, dead red), each domain, "power N", "N faith", "made contact with the pantheon" / "no contact yet" (faded), "Epoch N" (creation), "defeated in Epoch N", "died in Epoch N", for sleeping: "awakening P/`PANTEON.uyku_esik`(100)" with tooltip listing what wakes him.

#### 3.4.2 Sections
1. Description (or "No description yet; you can write one below.").
2. **Attitude to the pantheon** (`ytTutum`): diverging bar labelled enemy … friend; label: ≤ −`PANTEON.ogul_savas_tutum`(30) "enemy", <0 "suspicious", 0 "neutral", <`yabanci_dost_tutum`(40) "close", else "friend"; explanatory sentence per band (sons may declare war; may steal worshippers / raze temples; friendly adds prosperity to worshippers; neither).
3. **God's power panel** — dead: "<name> died · Epoch N" + "To revive him you can change his status in the edit form below." Otherwise:
   - **Drain from his power** (Gücünden em) → form `POST /api/yabanci/:id/oz-em`, confirm "Are you sure? His power will be drained", toast "Drained from his power"; amount `em = max(power>0 ? 1 : 0, round(power × TANRI_GUC.yt_em_pay(30)/100))`, gain shown `em × yt_guc_oz(3)`; disabled "No power left to drain" when em = 0; tooltip: attitude −`yt_em_tutum`(20); if power runs out he is defeated.
   - **Death** form → `POST /api/yabanci/:id/oldur {sebep, yut: bool}`: reason input, checkbox "devour (his power passes to you: +power×yt_guc_oz)", red **Kill** button; cost `round((yt_oldur_taban(60) + power × yt_oldur_guc(100)/100) × (has an 'olumsuz' (immortal) power ? yt_olumsuz_kat(2) : 1))`; confirm "Are you sure? <name> will die"; toast "<name> died"; tooltip: worshippers convert to you with `yt_tapan_donus`(50)% chance, others become godless.
4. **Stats** (`G.K.YT_STATLAR`, same nine as sons; tooltip = rule location), value or "—", meter in mythic colour, effect text.
5. **Powers** (`G.K.YT_GUC_ETKILERI`): cards; empty "No power written yet; deepening gives him powers, or add one yourself below."
6. **Personality and existence**: definition list of `G.K.YT_KISILIK` + `YT_VAROLUS` fields (excluding secret and true name) + secrets "Secret", "True name". Empty "Not written yet; deepening writes personality and existence."
7. **Depth**: history; `YT_DERIN_METIN` text fields; names; sayings; rumours; "Secrets (N)" collapsible list; "Hidden truth". Empty: "Not deepened yet. Deepening writes his personality, existence, powers and depth; it also happens by itself at epoch end." Button `data-yt-derin` → `POST /api/yabanci/:id/derinlestir`, toast "Deepening…", disabled during `y<id>:derin`; note "Personality/existence fields and powers you wrote by hand are kept; empty ones are filled, depth is rewritten."
8. **Worshippers**: thumbnail, link, "subtype · reason · since Epoch N", "N population" / "N followers". Empty "No community worships him now. While awake, ownerless communities on his world turn to him over time."
9. **Sons he encountered** (if any): avatar, link, "currently on this world" / "mentioned together in the chronicle", status chip unless active (asleep, exiled, dead, chained, fading).
10. **Bonds** (excluding incoming `tapar`): read-only list "→/← label", "past" chip, sentence, description. (No create/break controls here — inconsistency vs entity/son pages.)
11. **Images** (gallery + generate + upload + "Image prompt" box saving via `POST /api/yabanci/:id/duzenle {gorsel_prompt}`).
12. **In the chronicle** — "recent records mentioning his name"; empty "His name doesn't appear in the chronicle yet."
13. Two edit collapsibles:
    - "Edit name, title, attitude, power and status" (`ytDuzenForm`, transform `alanlar`) → `POST /api/yabanci/:id/duzenle {ad, unvan, alanlar (comma or / separated), tutum (slider −100..100), guc (0..100), durum (awake/asleep/defeated/dead), temas (checkbox "Contact made with the pantheon"), aciklama, gorsel_prompt}`; toast "<name> edited".
    - "Edit stats, powers, personality, existence and depth" (`ozellikForm`) → same endpoint with `statlar.{k}` sliders 1–100; `gucler.{i}.{ad, etki (select of YT_GUC_ETKILERI, "— effect —"), aciklama}` rows — clearing a name removes that power, the trailing empty row adds a new one; `kisilik.{k}` textareas; `varolus.{k}` inputs (`hal` is a select of `G.K.VAROLUS_HALLERI`: concrete, semi-concrete, conceptual, reflection, scattered); if depth exists: `derinlik.{k}` textareas (history 4 rows).

---

### 3.5 Pantheon tab components — `views/panteon.js`

The Pantheon tab (`#view-panteon`, rendered by `renderPanteon` in `views/hedefler.js`) lays out, top to bottom: onboarding steps, **God panel** (3.5.2), "This epoch" block, **Pantheon** section "N sons · click a card: order, bless, add star, ascend" with the **son card grid** (sorted by rarity desc, then stars desc, then id asc) and a "Compare cards" collapsible (2–3 sons), Goals block, **Council** block, **Open stories** (threads, first `IPLIK_ILK`=6 with "Show all threads (N more)" / "Show less"), **Brotherhood** matrix, "In the world" type-count chips (click → Atlas filtered by type), "Cosmology" + "Naming language" prose. Components defined in `panteon.js` follow.

#### 3.5.1 Son card (`sonCard(s, {noclick})`) — anatomy

`<article class="card" data-r="<rarity>" data-o="<id>">` (no `data-o` when `noclick`, e.g. the summon reveal screen). Classes: `acting` while the son's turn runs (SSE `basla`/`bitti`), `dim` when not active, `olu` when dead.

Rarity colours (both CSS vars `--r-*` and JS `RRENK` hex): common/Yaygın `#9097a0`, distinguished/Seçkin `#7fc489`, rare/Nadir `#6fa0e6`, epic/Destansı `#b48ae6`, legendary/Efsanevi `#e8ad48`, mythic/Mitik `#f07aa0`. The card border is a 1 px ring in the rarity colour (45 % mix); mythic gets an animated conic-gradient border spinning every 6 s.

1. **Art**: cover image (320 px, lazy) or procedural sigil (132 px, rarity colour, complexity by rarity index). Overlay badges: rarity name pill + stars (★ filled / dimmed up to max 5).
2. **Name** and **title**.
3. **Card depth** (`kartDerinHtml`, from `s.kart`): last words as a quote (tooltip "Epoch N"); last action "Ç<n> <summary>" (ids rendered as names); bond chips: closest sibling (mercy icon, "+value") and nemesis (anger icon, value) with tooltips "Closest sibling: X (+v)" / "Nemesis: X (v)". Server builds `kart` with text trimmed to 160 chars.
4. **Meta chips**: domain 1, domain 2 (glyph + name), "Lv N", status chip — dead "died · Epoch N" (`st-olu`), asleep "asleep · N epochs" (`st-uykuda`), exiled "in exile" (`st-surgun`), chained (`st-zincir`), ready (green "ready", son is in `G.S.bekleyen`) or "acted"; rebel chip "rebel" (red; tooltip "Rebelled against his father: ignores orders, steals divine essence each epoch"); fading badge "being forgotten · fades in N epochs"; reputation chip (label from `s.itibar` JSON or `s.kart.itibar`, colour `ITIBAR_RENK`, tooltip with love/fear/forgottenness); multi-world: current world chip; **model badge** (`chip model`, capitalised model id, tooltip "The language model that makes this son think (Settings → Models)"). Model is per rarity from server settings (`modeller()[nadirlik]`).
5. **Vitals**: three bars — Life `can/can_max` (red), Essence `oz/oz_max` (accent), Existence `varlik` (default `CAGIRMA.varlik_baslangic` 60) /100 coloured by state: radiant green, solid epic-purple, pale amber, fading red; tooltip "Existence: <state> — <effect>".
6. **Stat grid**: nine stats grouped Body (strength, endurance, agility), Mind (wisdom, cunning, will), Soul (creativity, charisma, might); each icon + name + value + meter (rarity colour); tooltip "Name: effect".
7. **Powers strip**: 3 slots; filled: name with power-card icon, locked styling + "(unlocks at Lv N)" tooltip if not yet unlocked; empty: lock "not awakened".
8. **Order or plan**: standing order quote (order icon) or plan line.
9. **Opportunity** (alive): eyebrow "Opportunity" / "Opportunities · N", first opportunity text, tooltip lists all.
10. **Footer**: faith, fame, XP "xp/(level×100)", actions per epoch, power cap "G<n>".

Click anywhere → son drawer.

#### 3.5.2 God panel (`godPanel`)
Portrait (cover `tanri_kapak` or gold sigil 140 px; `data-glb="t:1"`) + **Images** button (opens creator drawer). Body: eyebrow "Creator · immortal", name, title (or "Likeness not yet drawn."), gold **Epic and depth** button (opens creator drawer). Short mood widget (3.3.3). Appearance prose, temperament (italic muted). Stats chips: multi-world eyebrow "Whole cosmos" (numbers are totals across N worlds); reputation chip; gold "F faith · K cult" ("less than 1" rule); "N sons"; "N entities" (sum of `G.S.sayim`); "N open stories"; **Doom clock** chip "Doom clock k/threshold" (`data-dokum="kiyamet"`, hover shows last epoch's breakdown; colour amber ≥`KIYAMET.uyari1`(50)% of threshold, red ≥`uyari2`(80)%; tooltip explains the advancing/receding factors and that at threshold the world — in multi-world "the world leaking the most (ties: the most godless)" — is destroyed); "N rebel sons" (red); "N godless communities" (amber, each lowers essence income by `OZ.tanrisiz_kemirme`(3)); from `G.S.nabiz`: mortals (`data-dokum="nufus"` breakdown on hover), followers, "N languages · M words" (→ Lexicon tab), knowledge count, hostilities, trade routes, alliances; "N images"; gold "Star of the epoch: <entity>" (opens entity). Collapsible "Portrait prompt and likeness": prompt box `t:1` + **Redraw likeness** (`POST /api/tanri/suret`).

#### 3.5.3 Story threads (`threadsHtml(list, closed)`)
Each thread card: header "Story #id · Epoch N[ · advanced K times][ · closed Ç<n>]" or, for great quests (`buyuk` JSON), "Legendary expedition · <type name>" plus countdown "N epochs left" / "last epoch" (urgent style when ≤1) "· until Epoch E · declared by X". Text (auto-linked), closing text (muted), related entity chips. Open threads: collapsible "Close the story" with "How did it close? (optional)" (max 300) → `POST /api/iplikler/:id/kapat {nasil}`; toast "Story closed". (New-thread form lives in hedefler.js: `POST /api/iplikler {metin, ilgili:[ids]}`.)

#### 3.5.4 Brotherhood matrix (`matrixHtml`)
Hidden (<2 sons → "Brotherhood needs at least two sons."). Table N×N: column headers truncated names (8 chars long form / 4 chars short form for narrow screens, CSS var `--mx-n`), row headers son links; diagonal cells blank; cell text signed relation value (+ "⚭" if an alliance/covenant `G.S.ahitler` exists); background `color-mix(good|danger |v|×0.7 %, panel-2)`; tooltip "A ↔ B: <relation label> (v)[ · covenant]". Values from `G.S.iliskiler` (pairs stored a<b).

#### 3.5.5 Council of the gods (`konseyHtml(k, open)`)
Rendered from `GET /api/konseyler` (first `KONSEY_ILK`=3, "Show all councils (N more)" toggle; the newest is open). Each council is a `<details>`: summary "Epoch N", topic, outcome chip accepted (green) / rejected (red), "yes · no · abstain" counts. Body: eyebrow "Called by Fate" / "Called by <name>" (LANGUAGE-SPECIFIC: `ekDuzelt` applies Turkish genitive suffix harmony — drop) · "N speeches"; speeches with 34 px avatar ring in rarity colour (sigil fallback grey), speaker link, quote; "Motion" box; votes list (avatar, name, vote chip yes/no/abstain, reasoning); stacked vote bar (yes / abstain / no flex by count); result "Motion accepted/rejected"; notes list; transcript "Minutes · from a seer's dream". Convening (`POST /api/konsey {konu}`) is in hedefler.js.

---

### 3.6 Drawer system — `core/cekmece.js`

#### 3.6.1 Structure (index.html)
`#drawer` (hidden) → `.drawer-scrim` (`data-close`, click closes) + `.drawer-panel` (`role=dialog aria-modal=true tabindex=-1`) containing `.drawer-nav` with **Back** (`data-gecmis="-1"`, tooltip "Back (Alt+←)") and **Forward** (`data-gecmis="1"`, "Forward (Alt+→)") icon buttons, close X (`data-close`, "Close (Esc)"), and `#drawerBody`.

#### 3.6.2 `openDrawer(tip, id, silent=false, fromHistory=false)`
- Drawer kinds: `o` son, `v` entity, `t` creator, `y` foreign god, plus non-record kinds `ayar` (settings), `vahiy` (revelation), `bildirim` (notifications), `rehber` (world guide), `kayit` (records), `yardim` (help). Silent re-renders only apply to `o|v|t|y`.
- **History**: only for `o|v|t|y`, non-silent, not from history: if the new page differs from the current history entry, forward entries are truncated and `{tip,id}` pushed (`GECMIS = {list, i}`, in memory, unbounded). Back/forward buttons are disabled at the ends. Clicking them (or Alt+←/→ while the drawer is open) moves `i` and opens that entry with `fromHistory=true`. Non-record drawers do not enter history.
- Race guard: an incrementing request number (`G.drawerIstek`); stale responses are dropped.
- Non-silent open clears the body first (no transition), then patches; scrolls panel to top and focuses it (remembering the previously focused element). Silent opens patch in place (scroll and focus kept).
- Binds per kind (`bindVarlik`, `bindSonDrawer`, `bindTanri`, `bindYabanci`, …).
- `G.drawerOpen = {tip, id}` is used by refresh logic to re-render.
- Errors: toast (non-silent only).
- `closeDrawer()`: hides, clears `G.drawerOpen`, returns focus to the element focused before opening.
- Keyboard: Esc closes (or closes the reveal overlay first); Tab/Shift+Tab are trapped inside the topmost open modal (lightbox > palette > drawer panel).

#### 3.6.3 Section navigator (`bolumNavEkle`, `bolumIzle`)
For record drawers, if ≥4 headings (`.d-sec > h3` or first `h4` of a `.d-sec.panel-box`) exist, a sticky `nav.bolum-nav` (`data-k="bolum-nav"`) is prepended to `.d-inner` with one button per section. Button label = heading's own text nodes (subtitle spans excluded), truncated to 26 chars at a word boundary + "…" (full text as tooltip). Click → smooth scroll to the section. Scroll-spy: on panel scroll, the last section whose top is above (panel top + 90 px) is marked `on`.

---

### 3.7 Images: gallery, lightbox, upload, prompt box — `core/gorsel.js`

#### 3.7.1 Gallery (`galleryHtml(list)`)
Grid of thumbnails (`gsrc(file, 320)` → `/gorsel/<file>?w=320`; widths snap to 64/160/320/640), lazy; alt = valid caption or record name; "cover" badge on the cover image. The list is cached in `galleryHtml.cache["g<ids joined by ->"]` so a click (`data-lb`) can open the lightbox. Empty list renders nothing. Image order from server: cover first, then newest.

#### 3.7.2 Lightbox (`openLightbox(list, i)`)
`#lightbox` overlay: stage with full image (outer-thing images get a distortion class `dis-goruntu`); close × (`data-lbx`, initial focus); prev/next buttons when >1 image (wrap-around). Bottom bar: "i/N · <record name>", caption input → **Save caption** (`POST /api/gorseller/:id/baslik {baslik}`, toast "Caption saved"), cover chip or **Make cover** (`POST /api/gorseller/:id/kapak`, toast "Cover selected", closes), red **Delete**: first click changes label to "Are you sure? Delete permanently", second → `POST /api/gorseller/:id/sil`, toast "Image deleted", closes (on failure label resets; no timeout). Keyboard: Esc closes, ←/→ navigate. Click on the stage background closes. Captions are validated by `baslikGecerli` (filters junk like auto-generated filenames).

#### 3.7.3 Upload zone (`uploader(tip, id, label, hasImages)`)
Renders the generate-image box (3.8) followed by a drop zone label: upload icon, "<label>", hint "Drag & drop, click or paste · PNG, JPEG, WebP, GIF, AVIF", hidden multiple file input (accept those MIME types). Drag-over adds `.over`. Upload (`yukle`): non-images rejected ("Only image files can be uploaded."); files uploaded **sequentially** as raw body: `POST /api/gorsel?tip=<t>&id=<id>&baslik=<filename without extension, max 80, only if baslikGecerli>` with `content-type` = file type. Error "Upload failed: …". Success toast "Image saved" / "N images saved", then `refresh()`.
Global paste: pasting image files anywhere uploads to the first upload zone in the open drawer, else in the active view.
Record types for images: `v` entity, `o` son, `y` foreign god, `t` creator (id 1), `d` world.

#### 3.7.4 Prompt box (`promptBox(text, 'tip:id')`)
Shows the image prompt text (or "(no prompt)") with **Copy** and **Edit**. Edit swaps the text for a 5-row textarea and the button for **Save** → by tip: son `POST /api/ogullar/:id/prompt {prompt}`, entity `POST /api/varliklar/:id/duzenle {gorsel_prompt}`, foreign god `POST /api/yabanci/:id/duzenle {gorsel_prompt}`, creator `POST /api/tanri {tanri_prompt}`; toast "Prompt saved".

---

### 3.8 Local image generation UI — `core/gorsel-uret.js`

State lives in `G.S.gorsel_uret` (`{kurulu, hazir, model, ayar{genislik,yukseklik,adim}, suren{tip,id,ad,asama,adim,toplam,yuzde}, sira[{tip,id,ad}], toplu{calisiyor,oto,toplam,bitti,hata,atlandi}, eksik, gunluk[]}`) updated by SSE and `/api/degisim` `durum.gorsel_uret`. Buttons/indicators are re-patched in place (`guYenile`) without re-rendering pages.

Per-record status (`guDurum`): idle, queued (with "N ahead"), running (stage + percent). Stage labels: Queued, Preparing, Writing image prompt, Loading model into memory, Encoding prompt, Decoding image, "Denoising · 0/N" / "Step k/N done".

Disabled reasons: "Local image model is not installed (mflux)" when `!kurulu`; "No changes in exploration mode" when `G.S.salt_okunur`.

Three renderings:
1. **Box** (`uretKutu`, next to upload zones): idle → button "Generate image" (or "Generate one more image" when the record already has images; tooltip "Generates a W×H, N-step image with the local model[; existing images are untouched, the new one is added | and makes it the cover]"); queued/running → progress block with spinner, label, "%y" and bar.
2. **Mini** (`uretMini`, Atlas tree rows, only when installed): hover-revealed icon button; running → ring with percent (`--y`); queued → ring with spinner.
3. **Portrait overlay** (`portreUret`, hero portraits without an image, only when installed and not read-only): the whole empty portrait is a role=button (Enter/Space activates) showing "Generate image"; while running a large percent ring + stage text; queued "Queued · N ahead".

Clicking any `[data-gu="tip:id"]` (if idle) → `POST /api/gorsel-uret {tip, id}`; button disabled; error toast re-enables.

Live feed lines (from SSE): `gorsel_sirada` "<record> image queued · N ahead[ · bulk generation | · epoch end]" with progress; `gorsel_ilerleme` "<record> image being generated" with progress (same line updated in place, keyed by record); `gorsel_bitti` success: thumbnail (click opens the record), "<record> image generated", meta "s seconds · W×H · N steps[ · became cover]"; failure: "<record> image could not be generated: <error>" (error style). On success, if that record's drawer is open it re-renders silently; Atlas detail and Gallery tab re-render too. `gorsel_toplu` lines show bulk progress "(done/total)". `gorsel_durum` replaces the whole state. Replayed (history) events do not change state.

**Settings panel "Image generation"** (`gorselTopluHtml`, mounted in Settings → Game): explanation (all records without images — creator, sons, foreign gods, worlds, then entities by importance — are rendered one by one locally; existing images never touched; generated image becomes cover; prompts are written first if missing; size/steps/auto-start at epoch end in World rules → Image generation). Content (`GET /api/gorsel-uret`): "Model: <name> · W×H, N steps · in memory, ready / loads on first image" or red "Local image model not installed (mflux not found)". Button **Generate N missing images** (two-click: second label "Are you sure? N images will be generated") → `POST /api/gorsel-uret/toplu/baslat {}` (toast "Bulk image generation started"); disabled "Model not installed" / "No record without images left" / "Exploration mode"; label "All records have images" when none missing. While running: red **Stop** → `POST /api/gorsel-uret/toplu/durdur {}` (toast "Stop requested; it will stop after the current image"), green chip "running[ · epoch end]", counts "processed/total · generated · errors · skipped", progress bar, "Now: <name>" + progress, "Queued: first 5 names and N more", scrolling mono log (last 200 lines, timestamp HH:MM:SS, colour by level info/ok/warn/error). Bulk events re-render immediately and re-fetch the server summary debounced 1.5 s.

---

### 3.9 Shared components — `core/bilesen.js`

- **Families** (`AILELER`), used by graph/atlas legends: places (square), communities & people (circle), objects & knowledge (triangle), gods (diamond), culture & belief (hexagon), creatures & spirits (ring/hollow), events (star), other (plus). `sekilYolu(shape, r)` returns SVG path; colours from CSS `--aile-<k>`.
- `tag(type)` → coloured type label with icon; `cls(rarity)` → rarity text chip; `turAd` → type display name (special: son, world, creator, foreign god).
- `meter(v, max, colour)` → bar width clamp(0..100, v/max).
- `stars(n, max)`, `sonAvatar(son, size)` (cover thumbnail or sigil), `solusRozet` (fading badge), `ilEtiket` (sibling relation label), `hueOf(id)` (golden-angle hue for per-record colouring, used on historian cards).
- Depth helpers: `derinKv` (definition list skipping empty rows), `derinListe` (titled list, optional italic), `derinAdlar` (names list), `derinSir` (collapsible secret).
- `dosyaSecici` / `dosyaSeciciKur`: styled single-file picker with drag-drop, selected file name and size (KB/MB, Turkish number format), Remove button. `cokluSecici` / `cokluSeciciKur`: searchable checkbox list with "N selected[ · at least K]" counter; checked items stay visible while filtering.
- `gsrc(file, w)` image URL builder; `kimg` lazy `<img>`.

---

### 3.10 Persisted UI state

None of these files writes `localStorage` directly. Related persisted state elsewhere: `aerona.tab` (current tab, written on each render), bookmarks via `imDugme` (core/imler.js), compare selection `karsi` (`yerelYaz`). In-memory only (lost on reload): drawer history `GECMIS`, chat drafts/pending `SOHBET`, path results `YOL_SONUC`, knowledge cache `BILGI`, gallery cache, `KONSEY.hepsi`, `G.iplikHepsi`. Collapsible open state survives re-renders via keyed patching (`data-k`) but not reloads.

---


---

## Part 4 — Cosmos (2D/3D) and Map (including the procedural map generator)

### Cosmos tab (Kozmos) — overview and shell

**Files:** `public/views/kozmos.js` (DOM / side panel / 2D fallback), `public/kozmos3d.js` (three.js scene), `public/kozmos3d/golgelendiriciler.js` (GLSL shaders), `public/kozmos3d/yukle.js` (three.js loader), `public/three-webgpu-yok.js` (stub), `public/kozmos3d-test.html` (standalone debug page).

**Opened by:**
- The top tab bar `#tabs button[data-tab="kozmos"]`, or URL hash `#kozmos`. The last tab is persisted in `localStorage['aerona.tab']`.
- `[data-iklim-ac]` anywhere in the app (app.js:91): sets the side panel to "Command" (`KOZMOS.yan='yarat'`) with the Climate accordion open (`KOZMOS.acik='iklim'`), opens the tab and scrolls `#kozmosIklim` into view.
- The SSE event `dunya_dogdu` (views/akis.js:361) selects the newborn world (`KOZMOS.sec = e.dunya_id`, `KOZMOS.yan='dunya'`) and triggers a background refresh. It also shows a toast "`{ad}` was born" ("`{ad}` doğdu").
- The global world selector (core/dunya.js:17) keeps `KOZMOS.sec` in sync with `DUNYA.sec`. If the side panel was on "Star", it switches back to "World".

**Data source:** `GET /api/kozmos` (server `src/kozmos.js` `kozmos()`). The response shape, as far as the UI uses it:
```
{
  ufuk: { dunyalar:[{id, bolge, yer, oran, dar, kalabalik:[{id,ad,topluluk}], bulunan:[{id,ad,tur:'bolge'|'yer',cag,kasif_id,kasif_ad,bekliyor}]}],
          sezgiler:[{dunya_id, varlik_id, ad, cag, durum:'bekliyor'|'isleniyor'|...}] },
  yildizlar: [{id, ad, tur, parlaklik(0-100), x, y, aciklama, gorsel_prompt, ...}],
  dunyalar: [{id, ad, tur, tur_ad, yildiz_id, ana_id, yorunge, yercekimi, atmosfer, zaman_katsayi, kesif:'bilinen'|'efsane'|'bilinmeyen'|'unutulmus',
              tehlike, sizinti, iklim(JSON string {evre,kalan}), aciklama, kozmoloji, lehce, gorsel_prompt, seed, arazi{deniz,daglik,nem},
              olumlu_ajan(null=auto|int), koruyucu_ogul, koruyucu_oto, ayna_ikiz, cagin_yildizi(id|{id,ad}), yaratan_id,
              sayi:{bolge,halk,yerlesim,canli,nufus,dis}, ogullar:[{id,ad}] }],
  yabanci_tanrilar: [{id, ad, unvan, dunya_id, alanlar(JSON array or "a/b" text), tutum(-100..100), guc, inanc, durum:'uyanik'|'uykuda'|'yenik'|'olu', temas(bool), aciklama, gorsel_prompt, kapak}],
  rotalar: [{id, a_dunya, b_dunya, a_ad, b_ad, yontem, yontem_ad, sure, tehlike, bilinen(0/1), aktif, acik, durum, neden, acilis_cag, kapanis_cag, gizli, kuran_ogul, kontrol_id, kontrol_ad, kapali_son}],
  gok_takvimi: { sapan_acik, kapanis_cag, acilis_cag, sonraki_hiza, donem, metin },
  yolculuklar: [{id, yolcu_id, yolcu_ad, hedef_dunya, hedef_ad, rota_id, durum:'yolda'|'vardi'|'kayip'|'geri', kalan, niyet, nufus, arac_id, arac_ad, baslangic_cag, sonuc_id, olaylar:[{cag, olay, kayip}]}],
  turler: { <worldTypeKey>: {ad, palet[10]} },
  bolgeler: [{id, ad, tur:'bolge'|'yer', dunya_id}],
  topluluklar: [{id, ad, tur, dunya_id, nufus}],
  sefer_hedef: { olu_yildiz, muhurlu_kapi, arsiv, dis_kov }   // booleans
}
```
The 3D scene also receives `ogullar` from `G.S.ogullar` (state, fields `id, ad, durum, aktif_dunya, nadirlik, kapak`).

**Module state `KOZMOS`:**
- `veri`: the last `/api/kozmos` payload. `veriSurum`: the `G.S.surum` it was fetched at.
- `sec`: the selected world id. `secYildiz`: the selected star id.
- `yan`: the side-panel tab, one of `dunya|sefer|tanri|yarat|yildiz`.
- `yeniTur`: default `'olagan'`. `taslak`: draft of the world-inspiration text.
- `yer`: the placement mode for a new world (`kader|yildiz|ay|yeni`). `yerYildiz` and `yerAna` hold the chosen star / parent world.
- `yildizTaslak`: `{ad, tur:'sarı cüce', aciklama}`.
- `acik`: which accordion to force open (`yildiz|rota|gok|sefer|iklim|federasyon|kaynak|seferGonder`).
- `seferDunya`, `seferYolcu`, `yatakDunya`: form-select memory.
- `sahne3d`, `sahne3dKap`, `sahne3dKuruluyor`: the 3D scene handle, its container and the in-flight setup promise.
- Unused leftovers: `imza`, `tf`, `zaman`, `tween`, `konum`.

**Cached cosmos data for other tabs:** `kozmosVeriTaze()` re-fetches `/api/kozmos` only when `G.S.surum` changed. Atlas, Graph (ag) and the Genesis bar use it.

**Persisted UI state (localStorage, key prefix `aerona.`, JSON encoded):**
- `aerona.kozmosGorunum`: `'3b'` or `'2b'` (default `'3b'`).
- `aerona.kozmosKalite`: `'dusuk'`, `'orta'` or `'yuksek'` (default `'orta'`).
- `aerona.dunyaSec`: written when "Open in Atlas" is clicked.

**Realtime:**
- `core/yenile.js` polls `/api/degisim` (via `refresh`). It re-renders the Cosmos tab when any of these flags is set: `dunyalar` (dwDeg), `dunya` (tekDeg) or `ogullar` (oDeg). A change in `durum.mesgul` (busy flag) re-renders every tab, so the busy-disabled buttons refresh.
- A change of `cag` (epoch) causes a full refresh.
- The 3D scene survives tab switches. It pauses itself when invisible (IntersectionObserver, `document.hidden`, zero size). It is only destroyed when the container disappears, or when view/quality changes.

**Layout skeleton (`kozmosIskelet`):**
```
.kozmos
  .kozmos-sahne#kozmosSahne
     #kozmos3d.kozmos-3d            (3D canvas root or 2D SVG; class "iki-b" when 2D)
     .kozmos-ust.yuzer#kozmosUst    (floating top bar)
     .kozmos-lejant.yuzer#kozmosLejant (floating legend)
  aside.kozmos-yan#kozmosYan        (right side panel)
```

**Render flow (`renderKozmos`):**
1. Fetch `/api/kozmos`. Abort if the user left the tab.
2. Build the skeleton once and bind events (`kozmosBagla`).
3. If `KOZMOS.sec` is null or invalid, it defaults to the Map tab's world (`HARITA.dunya`) if that exists, else the first world.
4. Patch the top bar, legend and side panel. `yamala` is a DOM-diff patch keyed by `data-k`.
5. If 2D mode is on (`gorunum==='2b'` or WebGL unavailable), destroy any 3D scene and draw the SVG.
6. Otherwise, if a scene exists, call `sahne.guncelle(data, {secili})`.
7. Otherwise lazily `import('/kozmos3d.js')` (cached in `G.KOZMOS3D`). Then `kozmosSahnesi(container, opts)`. Any failure (module missing, `sahne.hata`, exception) sets `KOZMOS_AYAR.webglYok=true`, re-patches the top bar (the 3D button becomes disabled) and draws 2D. Refreshes that arrive during setup are applied once at the end with the latest data.

---

### Cosmos top bar (`#kozmosUst`)

Floating bar, left to right:

1. **Eyebrow** "Cosmos" ("Kozmos") with the `gok` (sky) icon.
2. **Summary text:**
   - "`{n}` stars · `{n}` worlds · `{n}` open routes".
   - If any routes are closed, a muted "(`{n}` closed)" follows.
   - If any voyages are under way, " · **`{n}`** voyages under way" follows ("sefer yolda"). It counts `yolculuklar` with `durum==='yolda'`.
   - "Open" uses `rotaAcik(r) = r.acik ?? !!r.aktif`.
3. **View / quality settings (`kozmosAyarHtml`):**
   - Segmented radio group "3D | 2D" ("3B | 2B"), `data-kgor="3b|2b"`. Clicking persists `aerona.kozmosGorunum` and rebuilds the scene (`kozmosYenidenKur`).
   - The 3D option is disabled when WebGL is missing, with the tooltip "This browser has no WebGL; using the 2D view" ("Bu tarayıcıda WebGL yok; 2B görünüm kullanılıyor").
   - **Quality** select `#kozmosKalite` ("Kalite"; options Low/Medium/High = Düşük/Orta/Yüksek). Shown only in 3D. Its tooltip explains that it controls pixel density, antialiasing, star count and bloom. Changing it persists `aerona.kozmosKalite` and fully rebuilds the scene.
4. **Sky calendar chip (`gokTakvimiHtml`):** shown only if any route uses method `sapan` (slingshot orbit). Source: `gok_takvimi`.
   - When open (gold chip `c-altin`): "Slingshot routes open · until the start of Epoch {kapanis_cag} · next alignment Epoch {sonraki_hiza}".
   - When closed (muted chip): "Slingshot routes closed · opens at the start of Epoch {acilis_cag}".
   - Tooltip: `T.metin`, plus the rule note "Period is a World rule: Cosmos and travel → Planetary alignment (currently {donem ?? SEYAHAT.hizalanma_donemi(5)} epochs)".
5. **Travel resource chip:** `button.chip[data-kacik="kaynak"]`. It reads `G.S.dunya.kozmik_kaynak` (a JSON string `{ad, aciklama, kural, yan_etki}`).
   - Label "Travel resource: {ad}" or "undefined" ("tanımsız").
   - Purple when defined, warning colour when undefined.
   - Tooltip: description + "Rule: …", or "The substance that fuels inter-world travel is not yet defined".
   - Click: switch the side panel to Command and open and scroll to the `#kozmosKaynak` accordion.

### Cosmos legend (`#kozmosLejant`)

- If there are no routes: "No known route between worlds yet." ("Dünyalar arasında henüz bilinen bir yol yok.")
- Otherwise the eyebrow is "Routes" ("Yollar"). Each distinct `yontem` (method) present gets a 28×10 SVG glyph and the method name from `G.K.SEYAHAT_YONTEMLERI[y].ad`.
  - The glyph is a straight line, or a curved one if the method has `kavis`. It uses that method's colour, width (capped at 2.4) and dash pattern.
  - The `kapi` method also draws a ring at each end.
- If any voyage is under way, there is an extra entry: an arrowhead glyph (#ece6d8) labelled "voyage under way" ("yoldaki sefer").

**2D route / legend line language (`YONTEM_CIZGI`)** — colour, dash, width, curvature:

| method (key) | name (rules) | colour | dash | width | curve |
|---|---|---|---|---|---|
| kapi | Ancient gate (Kadim kapı) | #b48ae6 | `1 5` | 1.4 | 0, end rings |
| katlama | Space folding (Uzay katlama) | #6fd0d8 | `10 3 2 3` | 1.6 | 0 |
| yelken | Light sail (Işık yelkeni) | #d8cfb8 | `7 5` | 1.4 | 0.12 |
| binek | Cosmic mount (Kozmik binek) | #e39b7b | `4 4` | 1.6 | 0.18 |
| ruya | Dream journey (Rüya yolculuğu) | #b48ae6 | `0.1 6` | 2.4 | 0.22 |
| olu_nehri | River of the dead (Ölüler nehri) | #8aa8b4 | `2 3` | 1.8 | −0.25 |
| kopru | Divine bridge (Tanrısal köprü) | #e8ad48 | solid | 2.4 | 0.32 |
| sapan | Slingshot orbit (Sapan yörüngesi) | #dcb45c | `1 7` | 1.8 | 0.4 |
| yutulma | Swallowing (Yutulma) | #dc735d | solid | 3.2 | −0.1, opacity 0.55 |
| (fallback) | — | #979387 | `4 4` | 1.2 | 0.1 |

Rule defaults (`SEYAHAT_YONTEMLERI`), for reference: kapi 1 epoch/danger 25; katlama 1/30; yelken 3/20; binek 2/35; ruya 1/45; olu_nehri 1/40; kopru 1/10; sapan 2/25; yutulma 2/60.

---

### Cosmos side panel (`#kozmosYan`)

**Tab strip** `.seg.kozmos-sekme[role=tablist]`, buttons `[data-kyan]`:
1. "World" ("Dünya", key `dunya`).
2. "Voyages" ("Seferler", key `sefer`), with a count badge of voyages under way.
3. "Gods" ("Tanrılar", key `tanri`), with a count badge of foreign gods.
4. "Command" ("Buyur", key `yarat`).
5. "Star" ("Yıldız", key `yildiz`). This tab appears only while a star is selected (`KOZMOS.secYildiz` is valid).

The body `.kozmos-govde[data-k="kg-{yan}"]` shows:
- the Star card, if `yan==='yildiz'` and a star is selected;
- otherwise Voyages, Gods or Command;
- otherwise the world chooser plus the World card for `KOZMOS.sec` (fallback: the first world).
- Empty state: "No world yet." ("Henüz bir dünya yok.")

#### World chooser (`dunyaSecimHtml`)
Shown only when there are 2 or more worlds. It is a filter-button row, one `[data-ksec=id]` button per world (keyboard-accessible alternative to the 3D scene). Forgotten worlds get a muted " · forgotten" ("unutulmuş") suffix. The current world has `.on` / `aria-pressed`. Clicking calls `kozmosSec(id)`: select, focus the 3D camera on it, scroll the panel to the top.

#### World card (`dunyaKartHtml`) — `article.dunya-kart[data-k="dk-{id}"]`, CSS var `--dc` = palette[4]

1. **Header:**
   - A disc with a radial gradient of the world-type palette indices [4], [3] and [1].
   - Eyebrow: `tur_ad` plus a discovery chip:
     - known (bilinen): green `st-hazir`
     - legend (efsane): purple `c-mor`
     - unknown (bilinmeyen): muted `c-sonuk`
     - forgotten (unutulmuş): muted `c-sonuk`
   - H3: the world name.
   - Muted line, in this order:
     - "{star name} · {star type}", or "starless" ("yıldızsız");
     - if a moon: "· {parent} moon" ("ayı"), parent as a link button `[data-ksec]`;
     - if it has moons: "· {n} moons: a, b";
     - if `yaratan_id` (the creating son) is set: "· {son link} gave birth" ("doğurdu"). Son name comes from `G.ADLAR_ID`, fallback "a son".
2. **Palette strip:** 10 colour swatches of the world type (`paletSerit(tur,'genis')`).
3. **Primary actions:**
   - **"Descend to its map"** ("Haritasına in", `data-inis`, primary). Runs `kozmosIn(id)`: the 3D camera flies to the world, then after 650 ms switches to the Map tab on that world. With no 3D scene, or with reduced motion, it switches immediately.
   - **"Open in Atlas"** ("Atlas'ta aç", `data-katlas`). Sets `DUNYA.sec`, persists `aerona.dunyaSec`, sets `ATLAS.dunya`, clears the Atlas collapse state and opens the Atlas tab.
   - **"Traveller's guide"** ("Gezgin rehberi", `data-rehber`). Opens the `rehber` drawer (`GET /api/dunyalar/:id/rehber`).
4. **Description** (prose, auto-linked entity names via `linkle`) and **cosmology** as a quote block.
5. **Count chips (from `sayi`):**
   - "{bolge} regions"
   - "{halk} peoples"
   - "{yerlesim} settlements"
   - "{canli} communities" ("topluluk")
   - "{nufus} souls" ("can"). Nufus is abbreviated via `kisa()` (e.g. 12.3k style).
6. **Physics key–value list:**

   | Field | Shown as |
   |---|---|
   | Mortal agents (Ölümlü ajan) | "automatic" ("otomatik") if `olumlu_ajan==null`, else "{n} communities" |
   | Orbit (Yörünge) | `yorungeYaz(yorunge)` + " units"; max 2 decimals, decimal comma |
   | Gravity (Yerçekimi) | raw value |
   | Atmosphere (Atmosfer) | raw value |
   | Time (Zaman) | "normal flow" if `zaman_katsayi`=1, "slow (×0,5)" if <1, "fast (×2)" if >1 |
   | Climate (İklim) | link button `[data-kacik="iklim"]`, see below |
   | Danger (Tehlike) | mono number + meter (0–100, `var(--danger)`) |
   | Leakage (Sızıntı) | mono number + meter (0–100, `var(--r-destansi)`), see below |

   - **Climate** text: `G.K.IKLIM[evre].ad`, plus " ({kalan} epochs)" when time remains. It reads the world's own `iklim` JSON; if absent, the global `G.S.iklim`; if that is also absent, "mild, uncertain" ("ılık, belirsiz"). Clicking opens Command → Climate.
   - **Leakage** colour classes:
     - `siz-orta` at ≥ `KORKU.uyari1` (default 30), with the warning text "Something is leaking in from outside." ("Dışarıdan bir şeyler sızıyor.")
     - `siz-yuksek` at ≥ `KORKU.uyari2` (default 60), with the danger text "Outsiders are taking root in this world; the mortals' sanity is being gnawed." ("Dışarıdan gelenler bu dünyada kök salıyor; ölümlülerin sağduyusu kemiriliyor.")
7. **Dialect accordion** (only if `lehce`): "Its dialect: how names are born here" ("Lehçesi: adlar burada nasıl doğar"). Persisted open state via `data-k="lehce-{id}"`.
8. **Star of the epoch** (only if `cagin_yildizi`): gold callout "This epoch's star: {entity link}" ("Bu çağın yıldızı"). The value may be an object `{id, ad}` or a bare id resolved through `G.ADLAR_ID`.
9. **Mirror twin** (only if `ayna_ikiz`): "Mirror twin: {world link}" ("Ayna ikizi").
10. **Guardian** (only if `koruyucu_ogul`): "Guardian: {son link}" ("Koruyucusu"). The muted note is either "became guardian automatically because most of its worshippers are here" (`koruyucu_oto`) or "declared this world sacred".
11. **"Sons present here"** ("Burada olan oğullar", from `w.ogullar`): chips with a son avatar (18 px) linking to the son drawer (`data-o`). Empty: "No son is in this world right now." ("Hiçbir oğul şu an bu dünyada değil.")
12. **"Routes"** ("Yolları") with a count badge. The list has one `.li.rota-li[data-k="rl-{id}"]` per route touching this world:
    - **Visual state:** class `bilinmez` if `bilinen` is falsy; `kapali` if closed. A 28×10 line glyph is drawn in the method colour, with dashes `2 5` when closed.
    - **Text:**
      - "**{method name}** → {other world (link)} · {sure} epochs · danger {tehlike}";
      - if `kontrol_id` is set: " · controlled by: {entity link}".
    - **Status chips (`rotaCipleri`):**
      - **Status chip,** from durum, or `acik` if `aktif`, else `muhurlu`:
        - open (`acik`): "open", green `st-hazir`
        - temporary (`gecici`): "temporarily open", warning
        - broken (`kopuk`): "broken", exile red `st-surgun`
        - collapsed (`coktu`/`cokmus`): "collapsed", exile red
        - sealed (`muhurlu`): "sealed", purple
        - not aligned (`hizasiz`): "not aligned", muted
        - forgotten (`unutulmus`): "in oblivion", muted
      - **Chip suffix:**
        - kopuk/hizasiz with `acilis_cag`: " · opens at the start of Epoch N";
        - gecici, or open with `kapanis_cag`: " · until the start of Epoch N". An open route with an end epoch shows a warning-coloured "open" chip.
      - **Chip tooltip:** `neden` (reason), plus a rule note:
        - for `sapan` (slingshot): open only while aligned, the cycle is every `SEYAHAT.hizalanma_donemi` (5) epochs;
        - for `kopuk` (broken): the duration is what the breaker chose, default `OTESI.kopar_sure` (3).
      - Hidden-route chip "hidden" ("gizli") if `gizli || bilinen===0`.
      - "built by: {son link}" if `kuran_ogul` is set.
    - If closed and a `neden` (reason) exists: muted reason paragraph.
    - **Route actions (`rotaEylemHtml`):** see the Cosmic actions catalogue (seal / break / re-raise / reveal).
    - Empty: "No known route to this world." ("Bu dünyaya bilinen bir yol yok.")
13. **Horizon section** (`ufukHtml`, only if `ufuk.dunyalar` has this world):
    - Eyebrow "Horizon · exploration" ("Ufuk · keşif").
    - Chips:
      - "{bolge} regions"
      - "{yer} places"
      - "{oran} communities per region" (decimal comma). Tooltip: land is cramped above `KESIF.dar_topluluk` (3).
      - "cramped lands" (warning) or "enough land" (green).
    - "Most crowded regions: {link} ({n}), …", the first `FIRSAT.liste_kisa` (4).
    - Found lands list: icon by type, entity link, then "region|place · E{cag} · found by: {link} · Kader will name it" (the last part when `bekliyor`). Empty: "No land has been discovered in this world yet."
    - Sensed worlds, `sezgiler` with durum `bekliyor` (waiting) or `isleniyor` (processing): "Sensed world: {link} (E{cag}), … · will be born at epoch end".
    - Explanatory text using rules `KESIF.taban_sans` (4%), `KESIF.cag_tavan` (2 per world per epoch) and `KESIF.rota_sans` (6%), plus the rule location.
    - Form **"Exploration round"** ("Keşif turu"): `POST /api/kesif/tur` with body `{dunya_id}`. Toast "Exploration round finished" ("Keşif turu bitti"). Disabled when busy, or with the tooltip "Exploration off (KESIF.cag_tavan = 0)". Note: "the engine's exploration dice are rolled now for this world".
14. **"Voyages coming here"** ("Buraya gelen seferler"): voyage cards (see Voyages) with `hedef_dunya===id` and `durum==='yolda'`.
15. **"This world's gods"** ("Bu dünyanın tanrıları"): foreign-god cards whose `dunya_id` is this world.
16. **"Creator's hand · cosmic actions"** ("Yaratıcının eli"), `.panel-box.kozmik-kutu`:
    - **Cleanse leakage** (`temizle`). If the world has no leakage and no Outsider entities inside (`sayi.dis==0`), the button is shown disabled with the tooltip "{world} has no leakage and no Outsider inside; nothing to cleanse".
    - **Bury in oblivion** (`unut`, danger). Hidden for world 1 and for already-forgotten worlds.
    - **Explanatory text:**
      - Cleansing reduces leakage by `PANTEON.temizle_sizinti` (40), "and may expel the Outsider(s) ({dis})".
      - Oblivion "wraps the world in mist and closes all its routes".
      - For a world already forgotten: "This world is already in oblivion."
      - For world 1: "The first world cannot be buried in oblivion: it is the home the pantheon and the sons return to."
    - **World wrath form** (hidden if forgotten). Label "World wrath" ("Dünya gazabı"), a select of disasters (`G.K.AFETLER`, name `ad`), and the button "Bring down on the whole world" ("Bütün dünyaya indir"). See the catalogue.
17. **"Edit world" accordion** ("Dünyayı düzenle: ad, tür, fizik, yörünge, anlatı"), `data-k="dunya-duzen-{id}"`. The form posts to `/api/dunyalar/{id}/duzenle` with transformer `dunya`. Toast "{ad} reshaped" ("yeniden biçimlendi"). Fields:
    - Name (Ad).
    - Type (Tür): all world types.
    - Gravity (Yerçekimi): low / normal / high (düşük / olağan / yüksek).
    - Atmosphere (Atmosfer): none / thin / normal / dense / toxic (yok / ince / olağan / yoğun / zehirli).
    - Time factor (Zaman katsayısı): number, min 0.01, `step=any`. Hint: "1 normal flow; 2 twice as fast, 0.5 half speed".
    - Discovery (Keşif): known / legend / unknown / forgotten. Forgotten is not offered for world 1.
    - Leakage slider (Sızıntı): 0–100.
    - Mortal agents (Ölümlü ajan): "automatic (by population)" or 0..`TANRI_ELI.olumlu_ajan_tavan` (12). Hint: "communities that play their own turn each epoch".
    - Orbit (Yörüngesi): default "don't change (currently around star X / currently moon of Y)". Options are "around star {Y}" (value `y:{id}`) and "moon of world {W}" (value `a:{id}`, top-level worlds only), with the current one disabled. Hint: the world moves only if a new orbit is chosen.
    - Guardian son (Koruyucu oğul): none, or living sons plus the current guardian.
    - Mirror twin (Ayna ikizi): none, or any other world.
    - Description, Cosmology, Dialect, Image prompt. Hint: "used when drawing its picture; leave blank to delete".
    - Transformer `FORM_DONUSTUR.dunya`:
      - removes `yorunge`; `y:N` becomes `yildiz_id=N` and `a:N` becomes `ana_id=N`;
      - `ayna_ikiz` and `koruyucu_ogul` become a number or null;
      - `olumlu_ajan` stays `'otomatik'` or becomes a number.

#### Star card (`yildizKartHtml`), opened by clicking a star (3D or 2D) — `KOZMOS.yan='yildiz'`
- **Header:**
  - A disc with a radial gradient from white to the star colour (`YILDIZ_RENK`).
  - Eyebrow "{type} · brightness {parlaklik}".
  - H3: the name.
  - Muted line: "{n} planets · position {x}, {y}". Only top-level worlds count; moons are excluded.
- Description.
- **Re-ignite** (gold `btn`), only if the type is in `OLU_YILDIZ`: dead star, black sun or star remnant (ölü yıldız / kara güneş / yıldız kalıntısı). See the catalogue. The note reads "The star burns again at {TANRI_ELI.tutustur_parlaklik (75)} brightness; leakage of the {n} worlds in its orbit drops by {TANRI_ELI.tutustur_sizinti (20)}".
- Chips for each orbiting world: "{world} orbit {yorunge}", each `[data-ksec]`. Empty: "No world around this star yet."
- **Edit-star form:** `POST /api/yildizlar/{id}/duzenle`, toast "{ad} edited". Fields:
  - Name.
  - Type: the current type plus `YILDIZ_TURLERI`, the 9 types sarı cüce, kızıl dev, mavi dev, beyaz cüce, ikiz yıldız, ölü yıldız, kara güneş, kırık yıldız, nabız yıldızı = yellow dwarf, red giant, blue giant, white dwarf, twin star, dead star, black sun, broken star, pulsar.
  - Brightness slider.
  - x, y (numbers).
  - Description, Image prompt.
- **Remove star** form (only if no worlds orbit it): `POST /api/yildizlar/{id}/sil`. Typed confirm, as two-click `data-onay`: "Are you sure? {ad} will be removed" ("Emin misin? {ad} kaldırılsın"). Toast "{ad} removed from the sky". Note: "No world around it; can be undone from the ledger."

#### Voyages panel (`seferlerHtml`)
- **Sorting:** order by durum in the sequence under way → arrived → recalled → lost (yolda → vardi → geri → kayip). Within a status, newest `baslangic_cag` first.
- **Empty state:**
  - If any open, known route exists: "No community has yet set out for another world. Open routes exist: communities may set out on their own (`SEYAHAT.sefer_taban` 6% per epoch, populations of at least `SEYAHAT.sefer_nufus` 1,200; World rules → Cosmos and travel) or you can send one below."
  - Otherwise the text says there is no open, known route, and to open one (Command → Open a route) or reveal a hidden one.
- **Voyage card (`seferKartHtml`),** `article.sefer.{durum}`:
  - Header: vehicle icon, "{traveller link} → {destination link}", and a status chip:
    - under way (yolda): "under way", class `acik-cip`
    - arrived (vardi): "arrived", green
    - lost (kayip): "lost", exile red
    - recalled (geri): "recalled", muted
  - **Meta chips:**
    - Only while under way and the route is closed with `kapali_son` set: "waiting for the seam to close · E{kapali_son}". Tooltip: the storm cut the route; the voyage is not lost and waits at the route mouth.
    - The intent: colony / trade / exploration / conquest / pilgrimage (koloni / ticaret / keşif / fetih / hac).
    - Population "{n}", if set.
    - Vehicle link (`data-v`), if set.
    - Method name.
    - "Set out in E{baslangic_cag}" ("Ç{n}'de çıktı").
  - **Under way:**
    - Progress bar, width = max(4%, (sure−kalan)/sure). Arrived shows 100%.
    - "Arrives in {kalan} epochs" or "Arrives this epoch".
    - Ghost button **"Recall"** ("Geri çağır"): `POST /api/yolculuklar/{id}/geri`, two-click confirm "Are you sure? Recall", toast "Voyage recalled". It is a document-level handler, so it also works in drawers.
  - Recalled: "The god recalled the voyage; the travellers returned home."
  - Arrived with `sonuc_id`: "They arrived and founded {entity link}."
  - Accordion "What happened on the road ({n})": a list of "E{cag} {event text} [−{loss}]".
- **"Send on a voyage" accordion (`seferGonderHtml`):**
  - Open by default if there are no voyages, or if `KOZMOS.acik==='seferGonder'`.
  - **Origin "From"** (`#seferDunya`): non-forgotten worlds. Changing it re-renders the panel and resets the traveller.
  - **"Traveller"** (`#seferYolcu`): communities from `topluluklar` on that world that are not already under way, sorted by population descending, then name. Each option reads "{ad} · {type name} · {nufus} souls".
  - **"Route"** (`rota_id`): open, known routes touching the origin world. Option text: "{other world} · {method} · {sure} epochs · danger {tehlike}".
  - **"Intent"** (`niyet`): the five intents.
  - **"Percent of population"** (`yuzde`), only if the traveller has a population. Range 1..`TANRI_ELI.sefer_tavan` (30), default `TANRI_ELI.sefer_yuzde` (10), `data-kural` set for validation messages.
  - **Submit "Set out"** ("Yola çıkar"): `POST /api/varliklar/{travellerId}/sefer`, body `{rota_id, niyet, yuzde?}`, toast "Voyage set out". Disabled with a reason when there is no open route from the origin world or no traveller.
  - Footnote: the population leaving is deducted; a god-commanded voyage ignores the vehicle/knowledge requirements.

#### Foreign gods panel (`yan='tanri'`)
- Intro: "Gods worshipped in other worlds, before or unaware of the pantheon. Their attitudes are toward the pantheon."
- **"Place an old god" accordion** ("Eski bir tanrı yerleştir"): `POST /api/yabanci`, transformer `alanlar`, reset after success, toast "A new foreign god has settled". Fields:
  - Name (required, max 60).
  - Title (max 120).
  - World: select, default the selected world.
  - Domains: comma or "/" separated, placeholder "zaman, kum".
  - Attitude slider −100..100, default 0.
  - Power: number; blank means rolled by dice.
  - Description, Image prompt.
  - Transformer: `alanlar` becomes a JSON array string; a blank `guc` is deleted, otherwise converted to a number.
  - The server then kicks off LLM deepening (`E.yabanciDerinlik`) in the background.
- Cards (`yabanciTanriHtml`), or the empty state "No known foreign god yet.":
  - **Header:** a round icon button (cover image 64 px, or the `tanri` icon) and the name link (`data-yabanci` opens the `y` drawer), the title, and a status chip:
    - awake (uyanik): "awake", warning
    - asleep (uykuda): "asleep", muted
    - defeated (yenik): "defeated", purple
    - dead (olu): "dead", exile
  - **Meta chips:** world chip (`data-ksec`), domain chips, "power {guc}", "{inanc} faith", and "no contact yet" when `!temas`.
  - **Attitude bar (`ytTutum`):** a bipolar bar from "enemy" (düşman) to "friend" (dost). Negative values fill leftward from 50% (class `kotu`); positive values fill rightward (`iyi`). The label is chosen as follows:

    | Value | Label |
    |---|---|
    | ≤ −`PANTEON.ogul_savas_tutum` (30) | "hostile" (düşman) |
    | < 0 | "suspicious" (kuşkulu) |
    | = 0 | "neutral" (tarafsız) |
    | < `PANTEON.yabanci_dost_tutum` (40) | "close" (yakın) |
    | otherwise | "friend" (dost) |

    The number is shown signed. The thresholds mirror the server: a negative attitude may attack, below the war threshold sons declare war, above the friend threshold the god helps.
  - Description. "Open its page" button plus the note "images, worshippers, chronicle".
  - **"Edit" accordion:** `POST /api/yabanci/{id}/duzenle`. Fields: name, title, domains, attitude, power slider, status select, a "Contact established with the pantheon" checkbox (`temas`), description, image prompt.

#### Command panel (`yan='yarat'`) — new world + cosmic commands
**New world (`dunyaYaratHtml`):**
- Eyebrow "New world"; intro "Pick a type and write an inspiration. Kader births the world with its own dialect, regions, sky, unique resource and natives; watch it in the live feed."
- **Type grid** (radio group `[data-ytur]`): one card per world type (`G.K.DUNYA_TURLERI`, falling back to the local table), each with a palette strip and the name. Default `olagan`.
- **"Inspiration (optional)"** textarea `#dunyaIlham`, max 600. Placeholder "A world where hours melt into sand; each grain holds a memory…". The draft persists in `KOZMOS.taslak` across re-renders.
- **"Where should it be born?"** segmented radio `[data-yer]`:
  - "Let Kader choose" (`kader`).
  - "Around a star" (`yildiz`). Shows the select `#yerYildiz`: "{star} · {type} · {n} planets".
  - "Moon of a world" (`ay`). Shows the select `#yerAna`: top-level worlds "{ad} · {type}".
  - "New star system" (`yeni`).
  - A per-mode explanatory sentence follows.
- **Gold button "Create the world"** ("Dünyayı yarat"):
  - Request: `POST /api/dunya-yarat`, body `{tur, ilham, yildiz_id? | ana_dunya_id? | yeni_yildiz:true}`.
  - Cost: `G.K.DUNYA_BEDEL` (rule `DENGE.dunya`, default 120 essence).
  - Toast "A new world is being born; watch the live feed".
  - The server runs it as a background job; SSE `dunya_dogdu` follows.
  - Disabled with "{bedel} essence needed; now {oz}." or "A job is running; opens when done."
  - On success the inspiration is cleared.

**Cosmic commands (`kozmosBuyrukHtml`):** six accordions, each `details.acilir[data-k]`, opened when `KOZMOS.acik` matches:
1. **"Ignite a star — a new star in the void"** ("Yıldız tutuştur"). Inputs:
   - `#yildizAd`: max 60; blank means Kader names it.
   - `#yildizTur`: 8 types (excludes pulsar — see defects).
   - `#yildizAciklama`: max 300. Placeholder "What kind of light? 'A pale eye only the dead can see…'".
   - Button **"Ignite"** (`data-kozmik="yildiz"`). The draft is kept in `KOZMOS.yildizTaslak` and reset on success.
2. **"Open a route between worlds"** ("Dünyalar arasına yol aç"): `POST /api/kozmik/rota`, body `{a, b, yontem}`.
   - `a` defaults to the selected world; `b` to the first other world. Only non-forgotten worlds are listed.
   - Method options read "{name} · {sure} epochs · danger {tehlike}".
   - Button "Open the route" ("Yolu aç"); no cost shown. Toast "A new route was opened".
3. **"Sky event"** ("Gök olayı"): `POST /api/kozmik/gok`. See the catalogue.
4. **"Proclaim a legendary quest"** ("Efsanevi sefer ilan et"):
   - Select `#buyukSefer` from `G.K.BUYUK_SEFERLER`:
     - `olu_yildiz` "Re-ignite the dead star"
     - `muhurlu_kapi` "Re-open the sealed gate"
     - `arsiv` "Reach the Cosmic Archive"
     - `dis_kov` "Expel the Outsider"
   - An option is disabled when `sefer_hedef[k]===false`, with a reason:
     - "no dead star in the cosmos"
     - "no sealed route"
     - "Cosmic Archive does not exist yet"
     - "no Outsider has got in"
   - The first available option is pre-selected.
   - Button "Proclaim" ("İlan et"). It is disabled when none is available: "No legendary quest currently has a target".
5. **"Climate cycle — each world's own climate"** ("İklim devri"), `#kozmosIklim`: `POST /api/kozmik/iklim`, body `{dunya_id|"" , evre, cag_sayisi}`.
   - World select: "All worlds" or each non-forgotten world as "{ad} · now {climate}".
   - Phase (evre) options from `G.K.IKLIM`, "{ad} · {aciklama}".
   - Epoch count: 1..`TANRI_ELI.iklim_cag_tavan` (50), default min(`TANRI_ELI.iklim_cag` (4), cap). Required.
   - Button "Start the cycle"; no cost. Toast "A new cycle was commanded to the sky". Note: each world's climate is separate and reverts on expiry.
6. **"Found a federation — communities in one union"** ("Federasyon kur"): `POST /api/federasyon`, transformer `federasyon`.
   - Multi-select (`cokluSecici`, label "Members", placeholder "Search community…", minimum 2, empty text "No living community."). Options are the canon community-type entities from `G.ADLAR_ID`, sorted by name; the sub-label is the type plus the world name when there are several worlds.
   - Optional name (max 80, placeholder "Northern Federation").
   - Body `{uyeler:[ids], ad?}`. Client-side error if fewer than 2: "Pick at least two communities for a federation."
   - Toast "Federation founded".
7. **"Cosmic travel resource"** ("Kozmik seyahat kaynağı"), `#kozmosKaynak`. Open by default if undefined.
   - Form `POST /api/kozmik/kaynak`, body `{ad (required), kural, aciklama, yan_etki}`. Placeholders "Hour sand", "Only gathered one season", "Gnaws the users' sanity". The button reads "Define" or "Update"; toast "The cosmos's travel resource was defined".
   - If a resource exists, a sub-form **"Open a new {resource} bed"**: `POST /api/kozmik/yatak`, body `{bolge_id}`.
     - World select `#yatakDunya`: changing it re-renders the panel and keeps the accordion open.
     - Region/place select from `bolgeler` on that world, "{ad} · {type}". It is required, or disabled showing "no region in this world".
     - Button "Open bed". Toast "A new {ad} bed was opened".

---

### Cosmic actions catalogue (every button, endpoint, body, cost)

Costs come only from rules. `kozmikBedel(k) = G.K.KOZMIK_BEDEL[k]`. Server defaults (`src/rules.js:428`): yildiz 80, muhur 30, temizle 80, unut 20, gok 50, tutustur 60, ruh 15, sefer 30. A cost is shown as `<span class="cost">{oz icon}{n}</span>`.

**Disabled logic (`ozEngel(bedel,{mesgul:true})`):** the button is disabled with a tooltip/aria-description:
- "A job is running; opens when done." when `G.S.mesgul` (busy);
- "{bedel} essence needed; now {oz}." when the god's essence (`G.S.dunya.tanri_oz`) is below the cost.

**Execution:** buttons run via `act()`, which shows the toast on success and an error toast on failure, then refreshes.

**Two-click confirmation:** `data-onay="…"` makes the first click turn the button red and show the confirm text. A second click within 4 s executes; otherwise the button reverts. For forms, the submit button is swapped in the same way.

| Action | UI location | Endpoint | Body | Cost | Confirm | Success toast | Hidden/disabled |
|---|---|---|---|---|---|---|---|
| Ignite star (Yıldız tutuştur) | Command → Ignite | POST `/api/kozmik/yildiz` | `{ad, tur, aciklama}` | KOZMIK_BEDEL.yildiz (80) | – | "A new star ignited" | busy / essence |
| Re-ignite dead star (Yeniden tutuştur) | Star card | POST `/api/kozmik/tutustur` | `{yildiz_id}` | KOZMIK_BEDEL.tutustur (60) | – | "The dead star burns again" | only dead types |
| Seal route (Mühürle) | World card → route row (open routes) | POST `/api/kozmik/muhur` | `{rota_id}` | KOZMIK_BEDEL.muhur (30) | – | "Route sealed" | tooltip "Seal the route: closes, leakage drops" |
| Break route (Kopar) | route row (open) | POST `/api/rotalar/{id}/kopar` | `{sure}` (number input "epochs", default `OTESI.kopar_sure` 3, min 1) | `OTESI.kopar_bedel` (40) | "Are you sure? Break" | "Route broke" | tooltip "Break for a few epochs; voyages on it fall into uncertainty" |
| Re-raise route (Yeniden dik) | route row (kopuk/muhurlu/coktu/cokmus) | POST `/api/rotalar/{id}/dik` | `{}` | `OTESI.dik_bedel` (40) | – | "Route re-raised" | – |
| Reveal hidden route (Açığa çıkar) | route row (gizli or bilinen=0) | POST `/api/rotalar/{id}/aciga` | `{}` | `SEYAHAT.aciga_bedel` (20) | – | "Hidden route revealed" | – |
| Cleanse leakage (Sızıntıyı temizle) | World card | POST `/api/kozmik/temizle` | `{dunya_id}` | KOZMIK_BEDEL.temizle (80) | – | "Leakage cleansed" | disabled if sizinti≤0 and no Outsider |
| Bury in oblivion (Unutuşa göm) | World card (danger) | POST `/api/kozmik/unut` | `{dunya_id}` | KOZMIK_BEDEL.unut (20) | "Are you sure? {ad} will be buried in mist" | "World buried in oblivion" | hidden for world 1 / already forgotten |
| World wrath (Bütün dünyaya indir) | World card form | POST `/api/dunyalar/{id}/gazap` | `{tur: disasterKey}` | `TANRI_GUC.dunya_gazap` (200) | "Are you sure? All of {ad} will be shaken" | "{ad} tasted wrath" | hidden if forgotten; tooltip: disaster strikes all regions at `TANRI_GUC.dunya_gazap_siddet`% (60) severity |
| Sky event (Göğe buyur) | Command → Sky event | POST `/api/kozmik/gok` | `{olay, dunya_id?, yildiz_id?, rota_id?, sure?}` | KOZMIK_BEDEL.gok (50) | – | "Something happened in the sky" | – |
| Legendary quest (İlan et) | Command | POST `/api/kozmik/sefer` | `{tur}` | KOZMIK_BEDEL.sefer (30) | – | "Legendary quest proclaimed; Kader will follow it as a story" | disabled with no target |
| Open route (Yolu aç) | Command | POST `/api/kozmik/rota` | `{a, b, yontem}` | none shown | – | "A new route was opened" | – |
| Climate cycle (Devri başlat) | Command | POST `/api/kozmik/iklim` | `{dunya_id, evre, cag_sayisi}` | none shown | – | "A new cycle was commanded…" | – |
| Define resource (Tanımla/Güncelle) | Command | POST `/api/kozmik/kaynak` | `{ad, kural, aciklama, yan_etki}` | none | – | "The cosmos's travel resource was defined" | – |
| Open bed (Yatak aç) | Command | POST `/api/kozmik/yatak` | `{bolge_id}` | none | – | "A new {ad} bed was opened" | disabled if world has no regions |
| Federation | Command | POST `/api/federasyon` | `{uyeler, ad?}` | none | – | "Federation founded" | – |
| Create world | Command | POST `/api/dunya-yarat` | `{tur, ilham, yildiz_id/ana_dunya_id/yeni_yildiz}` | DUNYA_BEDEL (120) | – | "A new world is being born; watch the live feed" | busy / essence |
| Exploration round | World card → Horizon | POST `/api/kesif/tur` | `{dunya_id}` | none | – | "Exploration round finished" | busy; cap 0 |
| Recall voyage | Voyage card | POST `/api/yolculuklar/{id}/geri` | – | none | "Are you sure? Recall" | "Voyage recalled" | only under way |
| Send voyage | Voyages panel | POST `/api/varliklar/{id}/sefer` | `{rota_id, niyet, yuzde}` | none | – | "Voyage set out" | no route/traveller |
| Edit world / star / foreign god | cards | POST `/api/dunyalar/{id}/duzenle`, `/api/yildizlar/{id}/duzenle`, `/api/yabanci/{id}/duzenle` | form fields | none | – | "… reshaped/edited" | – |
| Remove star | Star card | POST `/api/yildizlar/{id}/sil` | – | none | "Are you sure? {ad} will be removed" | "{ad} removed from the sky" | only if no worlds orbit |
| Place foreign god | Gods panel | POST `/api/yabanci` | form | none | – | "A new foreign god settled" | – |

The server also accepts `/api/kozmik/ruh` (cost 15), which is not used in these files.

**Sky event form specifics:**
- **Event select** (`[data-gok-olay]`), from `G.K.GOK_OLAYLARI`:
  - tutulma (Eclipse)
  - kuyruklu (Comet)
  - dizilim (Planetary alignment; opens slingshot/gate routes)
  - supernova (Supernova)
  - kara_gunes (Rise of a black sun)
  - firtina (Void storm). Disabled "· no open route" if no route is open.
  - Option tooltips carry the descriptions. All descriptions are also listed inline below the form.
- **"Which world's sky"** (`dunya_id`): default `dunyaSecili()` or the selected world.
- **"Or a star"** (`yildiz_id`): choosing one makes the event happen in that star system, and the world select is disabled.
- **When "firtina" is chosen,** a document-level change handler:
  - reveals and enables "Which route breaks" (`rota_id`, open routes "A ↔ B · method") and "How many epochs" (`sure`, default `GOK.firtina_sure` 3);
  - hides and disables the star and world fields.
  The body therefore always carries exactly one target: the route for a storm, else the star, else the world.

---

### Cosmos 2D fallback view (`kozmos2dHtml`)

Used when the user picks 2D, or when WebGL / three.js is unavailable. The SVG `svg.kozmos-2d` is drawn inside `#kozmos3d` (class `iki-b`) with `preserveAspectRatio xMidYMid meet`.

**Empty state:** "The void is still silent. It will appear here when the first star ignites." ("Boşluk henüz sessiz. İlk yıldız tutuştuğunda burada görünecek.")

**Layout algorithm:**
- **Hash:** `h01(s)` = FNV-1a 32-bit hash mod 10000 / 10000.
- **Star positions:**
  - With one star: (0,0).
  - With several stars spread out: normalise (x−minX)/span × 520 × √(N/2), and the same for y. `span` is the larger of the x and y ranges.
  - With all stars at the same point: place them on a circle of radius 300 by index.
- **Planets** (top-level worlds of each star, sorted by `yorunge` then id): k-th planet at radius 70+46k, angle h01('d'+id)·2π. A dashed orbit circle (#3a4152, `3 5`) is drawn per planet.
- **Orphan worlds** (no star) go on a ring of radius 240.
- **Moons** (3 passes): around the parent at radius 20 + 9·(number of placed siblings), angle h01('a'+id), with an orbit circle.
- **viewBox:** the bounds of all points padded by 110 horizontally and 90 vertically.

**Drawing:**
- **Routes:** quadratic paths. Control point = midpoint + perpendicular × `kavis`. Stroke = method colour, width min(2.4, gen).
  - Open: method dash.
  - Closed: dash `2 6`, opacity 0.3, class `k2d-kapali`.
  - Hidden (bilinen=0): opacity 0.4.
  - Otherwise opacity 0.9.
  - `<title>` tooltip: method name, " · hidden route the mortals don't know", status and reason.
- **Stars** (`g.k2d-yildiz[data-k2y]`, `tabindex=0`, `role=button`): a glow circle r=30 at opacity 0.12, a core r=15 in the star colour, and the name text below.
- **Worlds** (`g.k2d-dunya[data-k2d]`):
  - Invisible hit circle r=22.
  - Selection ring (r+7, #e8ad48, width 2) when selected.
  - Body circle r=11 (moons r=6), filled with the type palette[4], stroke #0b0d12.
  - Name below.
  - Class `unutulmus` if forgotten. `aria-pressed` and an aria-label are set.
- If WebGL is missing, a note below reads "This browser has no WebGL: cosmos is drawn in 2D."

**Interactions:**
- Click a world: `kozmosSec(id, false)` (no camera focus); the SVG is redrawn.
- Click a star: open the Star tab.
- Double-click a world: `kozmosIn` (go to its map).
- Keyboard: Enter or Space on a focused node acts as click. Enter on an already-selected world descends to its map.
- No zoom or pan in 2D.

---

### Cosmos 3D scene (`kozmos3d.js` → `kozmosSahnesi(container, opts)`)

**API:**
- `opts`:
  - `veri`, `secili:{dunya_id}`, `turler` (type palettes from the server), `ipucu` (show the help line), `azHareket` (fn or bool), `kalite` (`dusuk|orta|yuksek`).
  - Callbacks: `onDunya(w)`, `onDunyaCift(w)`, `onYildiz(y)`, `onRota(r)`, `onSefer(s)` (optional; falls back to `onRota` with the voyage's route), `onOgul(o)`.
- Returns `{guncelle(veri, {secili}), odakla({dunya_id}|{yildiz_id}|null, {anik}), sec({dunya_id}), hareket(), kalite, boyut(), yokEt(), _debug, _ekran(h)}`.
- `_ekran` maps a world, star or route to screen coordinates; it is used by tests.

**Loading (`kozmos3d/yukle.js`):**
- three.js r0.170.0.
- It first tries the page importmap (`three`, `three/addons/`), then falls back to the jsDelivr `+esm` bundles so that a single THREE instance is shared.
- Addons: OrbitControls, EffectComposer, RenderPass, UnrealBloomPass, OutputPass, CSS2DRenderer.
- The promise is memoised and reset on failure.
- `three-webgpu-yok.js` is mapped as `three/webgpu` in index.html's importmap. It is a stub class that throws "Weavers of the Void does not use the WebGPU renderer". It exists so that nothing pulls the WebGPU build.

**Fallbacks / error states:**
- Each of these renders the `.k3d-hata` panel and returns `{hata:true}` (the caller then switches to 2D):
  - no WebGL context;
  - three.js failed to load: sub-reason "three.js could not be loaded";
  - the renderer constructor throws;
  - no WebGL2: sub-reason "WebGL 2 required".
- Panel text: "The sky isn't visible here." / "This browser or device does not allow WebGL drawing ({reason}). Try enabling hardware acceleration and reloading."
- **Empty-cosmos overlay** `.k3d-bos` when there are no stars and no worlds: eyebrow "Cosmos", big italic "The void is still silent.", sub "It will shine here when the first star ignites." Auto-rotate is disabled in this state.
- **Help line** `.k3d-yardim` (bottom-right, when `opts.ipucu`): "drag: rotate · right-click: pan · wheel: zoom · double-click: on a world, descend to map; on a star, focus".

**Renderer and post-processing:**
- `WebGLRenderer({antialias:false, powerPreference:'high-performance', stencil:false})`.
- Tone mapping: Neutral (falls back to ACES), exposure 1. sRGB output. Clear colour #0b0d12.
- The canvas has `aria-label` "Cosmos: stars, worlds and routes" and `tabIndex 0`.
- **Quality presets (`KALITE`):**

  | Preset | pixel-ratio cap | MSAA samples | dust factor | bloom | sphere segments |
  |---|---|---|---|---|---|
  | dusuk (Low) | 1 | 0 | 0.3 | off | 40×24 |
  | orta (Medium) | 1.5 | 2 | 0.65 | on | 72×48 |
  | yuksek (High) | 2 | 4 | 1.0 | on | 96×64 |

- **Composer:** HalfFloat render target with MSAA → RenderPass → UnrealBloomPass(strength 0.55, radius 0.08, threshold 0.95) → OutputPass. Colours are produced in linear space and tone-mapped in the OutputPass.
- **Labels:** CSS2DRenderer overlay `.k3d-css`.
- **Camera:** `PerspectiveCamera(fov 40, near 0.5, far 40000)`, start (0,1600,1400). `near` is updated each frame to clamp(dist×0.01, 0.3, 30) when it changes by more than 5%.
- **OrbitControls:**
  - damping 0.07, rotate 0.55, zoom 0.9, pan 0.8, `screenSpacePanning=false`;
  - min distance 10, max distance max(1800, frame distance×2.4);
  - polar angle limits [0.04, 0.64π].
  - Auto-rotate at speed 0.18 when the cosmos is non-empty and reduced motion is off. It stops on the first user interaction.

**Scene composition (back to front):**
1. **Sky dome** (`gok` group, follows the camera): BackSide sphere of radius 14000 with shader GOK, plus a star-dust shell (7000 points × dust factor, radii 9000–12500).
2. **Deep layer** (`derin`), rebuilt when the cosmos bounds change (signature in 50-unit buckets):
   - a far dust shell of 2600 points (2.2R–4.5R);
   - a flattened galactic-disc dust of 2200 points (R 0–1.7R, thickness 0.5R, y −40, size attenuated);
   - 7 coloured nebula billboards (LEKE shader). Colours #6a4ab0, #3f8f8a, #8a5ac0, #4a6ab0, #b08048, #5a4aa8, #2f6f7a. They sit at hashed angles and radii 0.35–1.3R, y −160…−420, size R×(0.9–2.0), intensity 0.016–0.034.
   - Dust generator: a seeded LCG (16807). 38% of the points are flattened toward the equator. Warm/cool colour set #ffd6a0, #fff4e4, #dfe8ff, #a8c4ff, #ffb48a, lerped toward white. Brightness rnd^3.2×1.6+0.08; size 1+rnd^6×3.2; twinkle in the shader.
3. **System** (`sistem`): stars, worlds, orbit lines, routes, voyages.

**Orbit unit ORB:**
- `orbHesapla`: start at 58. For every star pair, ORB = min(ORB, 0.94 × distance / (outermost orbit_i + outermost orbit_j + 0.7)). Clamp to [24, 58].
- Star position: (x, hash-based y jitter ±25, z=y).

**Stars (`YILDIZ_TUR` table, type → look):**

| type | colour / colour2 | size | kind | rays | spike | light | extras |
|---|---|---|---|---|---|---|---|
| sarı cüce (yellow dwarf) | #ffd88a / #ff8a2a | 1.0 | 0 normal | 0.75 | 0.22 | #fff0d8 | |
| kızıl dev (red giant) | #ff7448 / #a8200a | 1.75 | 0 | 0.95 | 0.08 | #ffb89a | |
| mavi dev (blue giant) | #b4d4ff / #3a6ae8 | 1.4 | 0 | 0.85 | 0.5 | #d8e8ff | |
| beyaz cüce (white dwarf) | #f6f8ff / #a8bcff | 0.5 | 0 | 0.4 | 0.65 | #f4f6ff | |
| ikiz yıldız (twin) | #ffe0a0 / #ff9a4a + twin #a8ccff / #4a7ae0 | 0.74 | 0 | 0.6 | 0.2 | #fff0dc | two cores orbiting each other (sep 1.9 Rs, ratio 0.44/0.56, speed 0.22), shared faint halo |
| ölü yıldız (dead) | #7a7f86 / #2a2c30 | 0.85 | 1 dead ember | 0.05 | 0 | #9a8a80 dim | small, weak corona |
| kara güneş (black sun) | #d0894e / #000 | 1.0 | 2 | 0 | 0 | #e0a070 | dark light-eating halo (×6.4), purple photon ring (#8a5ac8), tilted accretion disk (1.35–3.9 Rs) |
| kırık yıldız (broken) | #ffc070 / #e8ad48 | 1.05 | 3 cracked plates | 1.5 | 0.3 | #ffe0b0 | 8 tetrahedron shards orbiting (r 1.28–1.83 Rs) |
| nabız yıldızı (pulsar) | #a8ecff / #3aa8d8 | 0.6 | 4 pulse | 0.5 | 0.7 | #d0f4ff | two beam cones (tilt 0.42, spin 1.6 rad/s), pulse = (0.5+0.5 sin 2.3t)^3 |
| yıldız kalıntısı (remnant) | #c890f0 / #6a4a9a | 0.38 | 5 | 0.2 | 0.35 | #d8c0f0 | nebula shell billboard ×16 |
| yeniden doğmuş yıldız (reborn) | #fff2cc / #ffaa50 | 0.95 | 6 | 0.9 | 0.4 | #fff4e0 | expanding shock ring ×9 |

- Star radius Rs = ORB × 0.15 × size.
- Brightness `parlaklik`/100 scales the core intensity (0.95+0.8p, or 0.7 if dim), the corona size (2.3+2.2p) and the corona intensity.
- The light colour used to light planets is scaled by 0.42 (dim), 0.6 (black sun), or otherwise 0.78+0.42p.
- Label: name with sub-label "{type} · {n} worlds".

**Worlds:**
- **Radius:** ORB × (0.075 + 0.05 × clamp(log10(population+1)/5.5) + 0.006 × min(regions, 8)). Gas giants ×1.75; moons ×0.55.
- **Group structure:** root → body (scaled) → axial tilt (hash ±0.35 rad) → spin. Spin rate 0.04–0.12 rad/s; 15% of worlds spin retrograde.
- **Surface:** GEZEGEN shader on the shared sphere; crystal worlds use an icosahedron (detail 2).
  - Uniforms: palette (10 colours from the server `turler` or the local table), arazi (sea, mountain, moisture), seed, type number, cloud amount, cloud colour, atmosphere colour and intensity.
  - City lights = clamp(log10(population+1)/5)×0.9. None for gas, dead or misty worlds.
  - Dim 0.93 for forgotten worlds, 0.86 for unknown. Opacity 0.6 for legend worlds (transparent).
  - "Breath" (vertex pulse) is enabled for living worlds.
- **Atmosphere presets:**

  | Atmosphere | intensity | shell radius × | clouds | colour override |
  |---|---|---|---|---|
  | yok (none) | — | — | — | — |
  | ince (thin) | 0.55 | 1.07 | 0.2 | — |
  | olağan (normal) | 1.0 | 1.11 | 0.4 | — |
  | yoğun (dense) | 1.5 | 1.16 | 0.68 | — |
  | zehirli (toxic) | 1.25 | 1.13 | 0.5 | #9bdc5a, clouds #b4d48a |

  - Gas giants are forced to intensity 0.8 / radius ×1.08 / no clouds, with atmosphere colour = palette[3].
  - **Atmosphere colour by type:**

    | Type | Colour |
    |---|---|
    | olagan (ordinary) | #7fb4ff |
    | okyanus (ocean) | #6cc4ff |
    | kum (sand) | #f0c890 |
    | buz (ice) | #cfe6ff |
    | lav (lava) | #ff7a3a |
    | kristal (crystal) | #c8b0ff |
    | yasayan (living) | #ff7a8a |
    | olu (dead) | #9aa4b0 |
    | ruya (dream) | #c0a0ff |
    | ayna (mirror) | #e6eef6 |

  - **Cloud colour:** lava #4a3c38, dead #9aa0a6, dream #f0e0ff, sand #f0dcb4, otherwise #f4f2ee.
  - The atmosphere shell intensity is ×0.25 for misty worlds and ×0.6 for legend worlds.
- **Gas giant ring:** ring geometry of 1.32–2.25 r (192 segments), tilt 0.24±0.125 and yaw ±0.35. Colours palette[2], [6], [4]. Opacity 0.15 if misty, 0.55 if legend, else 0.92.
- **Leakage (sizinti ≥ 5):**
  - A premultiplied halo billboard (SIZINTI) of radius r×(1.2 + z/100×1.9), strength 0.12 + z.
  - Round(z×1.2) purple spark particles (SIZINTI_P) drifting outward.
- **Fog** for unknown/forgotten worlds: SIS billboard ×5.2 r, alpha 0.6 or 0.75, colour #8e98aa.
- **Legend worlds:** dashed purple indicator ring (HALKA_GOSTERGE mode 2, ×3.1 r).
- **Foreign-god seal:** if a foreign god with `temas` that is not dead lives there, the first one gets a rotating billboard (MUHUR) of their procedural sigil (`sigil(name)` SVG rendered to a 512² canvas texture). Alpha 0.09; red #e07a68 if the attitude is negative, else lavender #c8a0ff. Size ×4.9 r (×7.2 for gas).
- **Selection ring:** copper #e8ad48, notched and rotating, ×3.0 r (×5.9 gas).
- **Hover ring:** bone #ece6d8, ×2.8 r (×5.6 gas). Alpha follows the hover easing.
- **Orbits:**
  - Planet: R = orbit × ORB. Angular speed 2π / (220 × orbit^1.5).
  - Moon: R = parent r × (2.55 if gas, else 1.75) + r×1.2 + orbit×ORB×0.75. Speed 2π / (40 + 90 × orbit).
  - Orbital plane inclination: ±0.045 rad for planets, ±0.35 rad for moons, about a hashed node axis. Phase is hashed.
  - The orbit line (256-segment loop, YORUNGE shader) has base alpha 0.085 (×0.35 misty, ×0.6 legend). A copper comet-tail trail follows behind the planet's current phase and brightens when selected.
- **Constant-size LOD:** each frame the body scale `s` = clamp(4.2 px / projected radius px, 1, 3.2 for planets / 2.2 for moons), so tiny far worlds stay ≥ ~4 px. Moons follow the parent scale.
- **Label:** the world name. Sub-label is the type name (+ " · legend"), or "unknown world" / "forgotten" when misty. Label CSS classes: `secili` (gold), `sisli` (italic grey), `efsane` (lavender).

**Sons on worlds:**
- Living sons with `aktif_dunya` are grouped per world. Up to 7 round 24 px avatar buttons (`.k3d-ogul`) float above the world:
  - border colour = rarity colour, from the CSS var `--r-{nadirlik}` or the fallback table (yaygin #9097a0, seckin #7fc489, nadir #6fa0e6, destansi #b48ae6, efsanevi #e8ad48, mitik #f07aa0);
  - cover image (64 px) or the procedural sigil.
- Click → `onOgul` (opens the son drawer). Hover shows a tooltip "**name** / {rarity} · son / on {world}".
- More than 7 sons: a "+N" chip, with the tooltip "N more sons on {world}; all are on the world card".

**Routes (ribbon shader):**
- A shared 120-segment ribbon geometry. The vertex shader evaluates a quadratic Bézier A→C→B and extrudes it in screen space by a pixel width, so the thickness stays constant on screen.
- **Control point** C = midpoint + up × (dist × 0.2 × kalk + a.r×2) + side × dist × bend. Bend for the n-th parallel route between the same pair is ±ceil(n/2) × 0.2.
- **Closed** when `acik===false`, or when `acik` is null and `aktif` is 0/false. Alpha 0.14 if closed, 1 if known, 0.38 if unknown. Closed routes stop flowing (`uFlow=0`).
- Width = gen × (1.15 − danger×0.45). Intensity = int × (1.25 − danger×0.6).
- **Method table (`YONTEM`):**

  | method | style # | colour | width (px) | intensity | lift | look (ROTA_FS) |
  |---|---|---|---|---|---|---|
  | kopru (bridge) | 0 | #f2b850 | 3.3 | 1.05 | 1 | solid gold arc with flowing shimmer |
  | yelken (sail) | 1 | #e8dcc0 | 3.0 | 1.0 | 1 | moving dashes (15 u period, 56% on) |
  | ruya (dream) | 2 | #b890ff | 3.8 | 1.3 | 1.15 | soft moving dots, hue drift purple↔blue |
  | olu_nehri (river of dead) | 3 | #7fa6b8 | 5.2 | 0.9 | −0.7 (sags down) | dark band (darkens behind it), cold edge glow, drifting specks |
  | katlama (folding) | 4 | #6fd8e0 | 3.2 | 1.3 | 0.6 | flickering segments (18 u, random per segment at 7 Hz) |
  | kapi (gate) | 5 | #b48ae6 | 2.6 | 1.0 | 0.35 | thin ley line with pulses; plus a torus portal ring and swirling vortex disc (GIRDAP) at each end, placed along the curve just outside each world and facing along the path |
  | binek (mount) | 6 | #e39b7b | 3.2 | 1.0 | 1.25 | long-short dash |
  | sapan (slingshot) | 7 | #dcb45c | 3.4 | 1.1 | 1.5 | sparse moving dots |
  | yutulma (swallowing) | 8 | #e0604a | 6.0 | 1.0 | 0.5 | thick red, peristaltic width pulse |
  | fallback | 1 | #a8a294 | 2.6 | 0.9 | 1 | |

- Ends fade over 3.5% of the length. Hover widens the ribbon ×1.7 and brightens it ×1.9.

**Voyages:**
- One additive sprite per voyage under way, with a 64 px canvas texture (radial glow plus a white arrowhead). The colour is the route colour lerped 55% to white ×1.7. Fixed 22 px on screen (×1.4 on hover), rotated along the screen-space tangent.
- A 16-point fading trail (IZ shader, 5 px).
- **Position:** progress p0 = 1 − kalan/sure and p1 = progress after one more epoch. The sprite ping-pongs between p0 and p1 over a 26 s ease-in-out cycle (phase hashed), clamped to [0.06, 0.94]. The direction is reversed if the destination is the route's `a` end. Opacity sin(πph)^0.35. Static at the midpoint under reduced motion.

**Interaction / picking:** screen-space picking, no raycasting. Priority order:
1. **Worlds:** within projected radius + 8 px; the best normalised distance wins.
2. **Stars:** within 1.3 Rs + 9 px.
3. **Voyages:** within 13 px.
4. **Routes:** within 8 px of the Bézier, sampled at 48 segments.

Pointer handling:
- **Hover:** cursor pointer, tooltip (`.k3d-ipucu`, follows the mouse, flips at the edges). Content:
  - World: name, type (or "unknown world"), " · {parent} moon", " · legend"; "{pop} souls · {n} regions · atmosphere X · leakage N"; "Foreign god: …"; hint "click: card · double-click: descend to its map".
  - Star: name, "{type} · brightness N", description.
  - Route: colour swatch, method name, "A ↔ B", "{sure} epochs · danger N · controlled by X · unknown route · until the start of Epoch N / closed, opens at the start of Epoch N", reason.
  - Voyage: "{traveller} → {dest}", intent and population, "arrives in N epochs" / "arrives this epoch" and vehicle.
- **Click** (pointer up < 600 ms, < 4 px movement, left button):
  - world → select + `onDunya` (does not move the camera);
  - star → `onYildiz`;
  - route → `onRota`. The panel selects an endpoint world (the current one if it is an endpoint), then scrolls to and highlights that route row (`.vurgu` for 1.6 s);
  - voyage → `onSefer`, else `onRota` with its route.
- **Double-click:** world → focus the camera + `onDunyaCift` (descend to map); star → focus the star.
- Right-click, or a ctrl / meta / shift-press, cancels follow mode. The context menu is suppressed.

**Camera framing / flights:**
- **Bounds:** the scene extent is computed from each star (radius = max(outermost orbit + 3r, 5 Rs)) plus starless worlds.
- **Overview framing:** elevation 0.92 rad. Distance to fit, then 8 iterations of project-and-recenter so everything fits within 90% × 82% of the viewport.
- **First frame:** snaps instantly (no animation).
- **`odakla` (focus) targets:**
  - World: distance max(r×9, 34), or enough to frame its moons. The camera follows the world afterwards (`takip`).
  - Star: frames its planetary system.
  - `null`: overview.
- **Flights:** spherical interpolation with log-radius. Duration clamp(1.1 + |ln(r1/r0)|×0.25 + travel/4000, 1.1, 2.4) s, `power3.inOut` (GSAP if present, else a manual cubic). Instant under reduced motion.

**Label layout (each frame):**
- **Opacity:**
  - World labels fade in once separated from their star / parent on screen: smoothstep 26→50 px (22→40 px for moons).
  - Selected or hovered labels are always opaque.
  - Unknown / forgotten worlds ×0.8.
- **Priority** (lower wins):
  - selected or hovered: 0
  - star: 2.5
  - planet: 2 − min(r/ORB, 0.4)
  - moon: 3
  - labels already visible: −0.3 (hysteresis)
- **Collision:** greedy rectangle collision against the planet discs and the labels already placed; colliding labels are hidden (opacity 0).
- **Sizes:** label sizes are measured once and re-measured after fonts load. Opacity is quantised to 1/50 to limit DOM writes.

**Performance:**
- Per-entity signature (JSON of the relevant fields); a mesh is rebuilt only when its signature changes.
- Shared geometries; disposal walks the scene graph (`birak`).
- The render loop pauses when the tab is hidden, off-screen or zero-sized.
- dt is clamped to 0.1 s. Reduced-motion is rechecked every 32 frames; it freezes the simulated time, auto-rotate and flights.
- ResizeObserver handles resizing.

### Shader catalogue (`kozmos3d/golgelendiriciler.js`)
All shaders are GLSL ES 3.0 for three.js ShaderMaterial. They share a 3D simplex noise, fBm and a Worley/cell noise.
- **BILLBOARD_VS:** a camera-facing quad of `uSize` world units, scaled by the object's world scale. Used by all halo-type FS.
- **GOK_VS/FS (sky):** procedural nebula on the inner sky sphere. Domain-warped fBm in copper (`uBakir` #e8ad48), purple (`uMor` #9a6ae0), teal (`uCam` #4fa8a0) and bone (`uKemik` #ece6d8) at very low intensity (≈1–2%) over the background `uBg`. A slightly tilted galactic band with dark dust lanes.
- **TOZ_VS/FS (star dust):** point sprites with per-point colour, size and seed. Twinkle 0.72–1.0. Optional distance attenuation (`uAtt`). Gaussian core + halo.
- **LEKE_FS:** soft fBm nebula blobs (`uCol`, `uInt`, `uSeed`, slow drift with `uTime`).
- **YILDIZ_VS/FS (star surface):** boiling granulation (fBm + simplex) mixing `uCol2`→`uCol`, limb darkening, centre white-hot. Hover rim. `uKind` variants:
  - 1 dead: dark grey with glowing orange cracks;
  - 2 black sun: pure black disk with an orange limb;
  - 3 broken: Worley plates with bright cracks;
  - 4 pulsar: brightness × `uPulse`.
- **TAC_FS (corona):** `uMode` variants:
  - 0: glow + noisy rays (`uRays`) + cross diffraction spikes (`uSpike`), pulsing;
  - 1: black-sun photon ring;
  - 2: remnant nebula shell with filaments (purple→teal);
  - 3: expanding shock ring.

  `uCore` is the core-to-billboard radius ratio.
- **KARANLIK_FS:** a normal-blended black disc that "eats light" around a black sun (`uCore`, `uAlpha`).
- **DISK_VS/FS (accretion disk):** differential rotation, streaky fBm, hot white→orange→purple gradient with radius, relativistic-style doppler brightening on the approaching side (`uNormal`, `uCenter`).
- **GEZEGEN_VS/FS (planet surface):** see the dedicated section below.
- **ATMOSFER_VS/FS:** additive back-face shell computing the ray's closest approach to the planet centre. Rim glow of `uCol` falling off with power 2.4 between the surface and `uRa`. Day-side lit, night side 12%.
- **HALKA_FS (gas-giant ring):** radial banding from two noise frequencies, an inner/outer fade, a Cassini-style gap at u=0.64, a three-colour mix, and the planet's shadow cast on the ring (darkening to 28%). Premultiplied.
- **SIZINTI_FS:** premultiplied leakage halo that darkens what is behind it, with violet tendrils (0.30,0.10,0.62 / 0.72,0.46,1.0) flowing outward and a bright rim. Strength `uStr`.
- **SIZINTI_P_VS/FS:** violet spark particles emitted along fixed random directions, life loop, lifting off up to 1+0.6+1.9·str radii.
- **SIS_FS:** grey fBm fog patches (premultiplied) over unknown/forgotten worlds.
- **HALKA_GOSTERGE_FS:** indicator rings by `uMode`:
  - 0 selection: thin copper ring + rotating 72-notch tick ring + 4 rotating corner brackets;
  - 1 hover: plain ring;
  - 2 legend: 40-dash rotating ring.
- **MUHUR_FS:** slowly rotating textured sigil card, tinted `uCol`, alpha `uAlpha`.
- **YORUNGE_VS/FS:** orbit line. Base colour × alpha (brighter when selected), plus a copper trail exp(−9·behind) behind the planet phase `uPhase`.
- **ROTA_VS/FS:** screen-space ribbon along the Bézier; 9 styles as tabulated above. Alpha channel used only for the "dark" river-of-the-dead band.
- **GIRDAP_FS:** swirling noise vortex inside gate rings.
- **ISIN_VS/FS:** pulsar beam cones, fresnel-weighted, brightest at the base.
- **IZ_VS/FS:** voyage trail points shrinking and fading along the tail.

**Planet surface shader (GEZEGEN_FS) detail:**
- `uTur` codes: 0 olagan, 1 okyanus, 2 kum, 3 buz, 4 lav, 5 kristal, 6 yasayan, 7 olu, 8 ruya, 9 gaz, 10 ayna.
- **Gas giant (9):** latitude bands with flow-twisted turbulence, palette sweep across indices 2–9, and a storm eye (palette 8/9) at a seeded position.
- **Rocky types:**
  - Elevation: warped fBm + ridged noise × `uMount`. Sea level from `uSea`: s = (sea−0.5)×0.72. Moisture from fBm + `uMoist`.
  - Water mixes pal[0]→pal[1] with depth.
  - Land: beach pal[2]; lowlands pal[3]/[4]/[5] by moisture; hills pal[6]/[7]; mountains pal[8]; peaks pal[9].
  - Polar caps for olagan, okyanus and buz.
  - Bump mapping from the height derivative.
  - Specular on water.
- **Type specials:**
  - lava: emissive seas and glowing cracks;
  - ice: sharper specular;
  - living: pulsing red veins + breathing;
  - dead: desaturated with drifting mist;
  - crystal: flat facets, high specular, twinkling facets;
  - dream: iridescent fresnel;
  - mirror: environment reflection + sharp specular.
- **Common:** star-direction lighting with a soft terminator (unlit worlds are lit from the view direction), clouds, night-side city lights (warm orange, only on land, × `uCity`), atmospheric fresnel rim, hover/selection warm rim, then fog-silhouette blend `uDim` for undiscovered worlds. Alpha = `uOpacity`.

### Cosmos 3D debug page (`kozmos3d-test.html`)
- Standalone page at `/kozmos3d-test.html`, full-screen. It uses the same importmap and GSAP.
- It fetches `/api/kozmos` and `/api/state` (for `ogullar`) unless `?bos` is given (empty cosmos). `?sec=ID` preselects a world.
- Callbacks write "world: X / star: X / route: X / son: X" into a corner `#olay` text.
- It exposes `window.k3d`, `window.k3dVeri` and `window.k3dHazir` for tests.
- The rebuild needs only an equivalent dev harness (optional).

---

### Map tab (Harita) — overview

**Files:** `public/views/harita.js` (UI, rendering, interaction) and `public/harita-gen.js`. The procedural map generator is **shared with the server**: `src/harita.js` imports `dunyaHaritasi`, `CEKIRDEK`, `W` and `H`, runs the same generation server-side, and persists `yeniXY` and `tasinan` positions into `varliklar.harita_xy`. Both sides must produce identical results, so the generator must live in one shared package (or be server-only, with the client receiving cell geometry).

**Opened by:**
- Tab `#harita` / `data-tab="harita"`.
- `haritaInis(id)`, used by: Cosmos "Descend to its map", the 3D double-click, the 2D double-click, `[data-dunya-harita=id]` (Graph, entity drawer chip).
  - It stops playback, saves the world, clears the past epoch, sets the descend-animation flag, closes the drawer and opens the tab.
- `[data-haritada=id]` ("show on map" from drawers, app.js:89). Sets `G.haritaOdak=id` (with optional `data-dunya` to switch world) and opens the tab; the map then zooms to it.

**Libraries:** global `window.d3` v7.9.0 (Delaunay/Voronoi, zoom, drag, selection) and optional `window.gsap` 3.12.5, both loaded from cdnjs script tags.
- If d3 is missing: "d3 could not be loaded for the map (internet connection required)." ("Harita için d3 yüklenemedi (internet bağlantısı gerekli).")

**State `HARITA`:**
- View and timing:
  - `tf`: the d3 zoom transform, preserved across re-renders of the same world.
  - `imza`: the full render signature.
  - `animNo`, `anim`: the ambient-animation rAF.
  - `giris`: a Set of world ids that have had their entrance animation.
- World and epoch:
  - `dunya`: the current world, persisted as `aerona.haritaDunya`, default 1.
  - `sonDunya`.
  - `cag`: the past epoch being viewed, or null for today.
  - `oynat`: the playback timer.
- Interaction:
  - `notMod`: note-pin mode.
  - `pop`: the popup context `{x,y}` or `{not:id}`.
  - `inis`: the descend-animation flag.
  - `veri = {data, vs, h}`.

`G.haritaCache = {imza, h}` holds the generated geometry, keyed by seed + type + arazi + the entity id/type/parent/xy list. `G.haritaOdak` is the focus request.

**Persisted (localStorage):**
- `aerona.harita` (raw JSON, written by `kaydetKatman`) = `G.haritaKatman` `{mod:'arazi'|'siyasi'|'bolge'|'yaratan'|'din'|'dil', yollar:bool, savas:bool, olay:bool, etiket:bool}`. Defaults: `{mod:'arazi', yollar:true, savas:true, olay:true, etiket:true}`. A legacy key `arka` is deleted.
- `aerona.haritaDunya`: the world id.
- `aerona.haritaLejant`: whether the legend is open. Default: open unless the viewport is ≤ 600 px wide.

**World sync:** when the global selector has a specific world (`dunyaSecili()`), the map follows it. Changing the map's world select calls `dunyaSecDegis`, which also changes the global selector (single source of truth `DUNYA.sec`). If the stored world no longer exists, the first world is used.

**Realtime:** `/api/degisim` re-renders the map when entities changed (`varliklar` / `varlik_silinen`), links changed (`baglar`), or world rows changed (`dunyalar` / `dunya`). Busy-flag changes re-render all tabs. Leaving the tab cancels the ambient rAF and stops playback (core/yenile.js:193).

**Data:** `GET /api/harita?dunya={id}[&cag={n}]`. The `cag` parameter is sent only when viewing a past epoch below the current one. Response:
```
{ seed, dunya: {...dunyalar row, arazi:{deniz,daglik,nem}, tur, sizinti, cagin_yildizi, ad},
  varliklar: [{id, ad, tur, alt_tur, konum_id, guc_seviyesi, statlar{nufus,…}, harita_xy, xy:[x,y]|null, yaratan_id, kaynak, durum, dunya_id, kapak}],
  bilgi: {regionId: {komsular[], kiyi, yukseklik:'dağlık'|'engebeli'|'ova'|'su', buyukluk, iklim:["biome %n",…]}},  // server-side generator output
  kapsam, rotalar: [{a, b, tur:'ticaret'|'dusman'|'yonetir'|'avlar', aciklama}],          // active entity links
  yildiz,                       // legacy star-of-epoch id for world 1
  bolgeDin: {regionId: sonId}, bolgeDil: {regionId: languageId}, diller: [{id, ad}],
  siyasi: {regionId: {hakim_id, hakim_ad, pay(%), cekisen(n)}},
  yollar: [{a, b, tur:'ticaret'|other, uzunluk}],   // road network between settlements
  notlar: [{id, x, y, metin, renk, dunya_id, olusturma}],
  zaman: {simdi, gosterilen, fotograflar:[epochs with snapshots]},
  kademeler: {settlementId: {kademe:'koy'|'kasaba'|'kent'|'buyuk_kent'|'baskent', ad, nufus, onceki_nufus}},
  isaretler: [{id, ad, tur:'muharebe'|'afet'|'harabe'|'kalinti'|'olay', alt_tur, konum_id, cag}],
  savaslar: [{id, ad, konum_id, cag, suruyor}] }
```
Past-epoch mode filters entities server-side, to those born ≤ that epoch and alive in that epoch's snapshot (regions are always kept). Populations are replaced from the snapshot, and politics come from the snapshot.

**Layout skeleton (`haritaIskelet`):**
```
#view-harita
  .h-sahne#hSahne            (canvas#hcanvas terrain, canvas#hanim ambient, svg#harita overlays)
  .sizinti-katman            (CSS leakage vignette, aria-hidden)
  .pusula                    (decorative compass SVG, 76px, north letter "K")
  .olcek-cubugu              (scale bar: line + #olcekYazi)
  .map-tools.yuzer#hArac     (toolbar)
  .gecmis-bant#hBant[hidden] (past-epoch banner)
  .map-lejant.yuzer#hLejant  (legend)
  .harita-alt
     .map-info.yuzer#mapInfo (hover info / status line)
     .zaman-panel.yuzer#hZaman (time slider)
  .harita-pop.yuzer#hPop[hidden] (note popup)
```
Toolbar, legend, time panel and banner are patched in place (`yamala`). Only the scene (canvases + SVG) is rebuilt, and only when the full signature changes.

### Map toolbar (`#hArac`, `haritaAracHtml`)
**Row 1, layers (`.katman-sira#hKatman`):**
- **Mobile:** this row becomes a bottom sheet with the header "Layers" and a close × (`data-katman-kapat`). It is opened by the "Layers" button (`data-katman-ac`, mobile only), which toggles the class `katman-acik` and `aria-expanded`.
- **Mode segmented control** (`data-hk="mod"`, `data-hv`). One active, `aria-pressed`. Persisted to `aerona.harita`, then the map re-renders.
  - "Terrain" (Arazi)
  - "Political" (Siyasi)
  - "Regions" (Bölgeler)
  - "Creators" (Yaratanlar)
  - "Religions" (Dinler)
  - "Languages" (Diller)
- **Toggles** (`data-ht`): `btn sm` with class `acik` (on, check icon) or `ghost` (off, own icon). Persisted the same way.
  - "Roads" (Yollar, icon `ag`)
  - "Wars" (Savaşlar, `meydan`)
  - "Events" (Olaylar, `olay`)
  - "Labels" (Etiketler, `kalem`)

**Row 2:**
- **World select** `#haritaDunya` (only with more than one world). Tooltip: choosing also switches the top selector.
- When the top selector is on "whole cosmos": a chip "Whole cosmos · map: **{world}**". Tooltip: the map always shows one world.
- "Layers" (mobile only).
- **"Legend"** (Lejant) toggle (`data-lejant-ac`): flips `aerona.haritaLejant`, shows/hides `#hLejant`, re-patches the toolbar.
- **Search** `#haritaAra` with datalist `#haritaListe` of every entity name that has a map position. Placeholder "Find on map…" ("Haritada bul…").
  - On change: case-insensitive exact name match (tr locale). On a match, focus that entity and clear the input; otherwise toast "No such place on the map." ("Haritada böyle bir yer yok.")
- **"Note pin"** (Not iğnesi) toggle `#notMod`, `aria-pressed`.
  - Disabled in past mode, with the tooltip "Cannot pin notes while looking at the past". Otherwise the tooltip is "Click the map, leave a note".
  - Toggling closes any popup, adds the class `not-modu` (crosshair cursor) to the view, and re-patches.

### Map legend (`#hLejant`, `haritaLejantHtml`)
Two `<details>` blocks with persisted open state (`data-k`).

**1. Layer block** (Political / Religion / Language / Creators only), open:
- Titles: "Political control" (Siyasi denetim), "Dominant faith" (Baskın inanç), "Dominant language" (Baskın dil), "Region creators" (Bölgeleri yaratan).
- **Political:** groups regions by ruler `hakim_id`, sorted by region count. Each row: a colour swatch, the ruler entity link (`data-v`), and small text "{region} %{pay} · {n} contending" per region.
  - Empty: "No community dominates any region yet."
- **Religion / Language / Creators:** a swatch + name + mono count per category in the palette. Then a grey "other: A n, B n" row for overflow.
  - Category names:
    - religion: the son's name;
    - language: the language name;
    - creator: the son's name, or "{god name} (the god himself)" for god-made regions (`kaynak==='tanri'` or no `yaratan_id`).
  - Empty texts: "No god is worshipped in any region yet." / "No language is spoken in any region yet." / "There is no region on this map."

**2. "Markers" block** (İşaretler): open if there is no layer block. It lists only markers actually present on this map:
- **Entity family rings,** one per family present: a circle stroked `var(--aile-{k})`, labelled with the family name, tooltip = the type names in it. Families come from `AILELER` in core/bilesen.js.
- **Settlement tiers present,** each with a glyph and a threshold note:
  - village (köy): "< 2,000"
  - town (kasaba): "≥ 2,000"
  - city (kent): "≥ 10,000"
  - great city (büyük kent): "≥ 50,000"

  Thresholds come from rules `SIYASET.kasaba` (2000), `SIYASET.kent` (10000) and `SIYASET.buyuk_kent` (50000).
- Capital (başkent), tooltip "Each ruling community's most populous settlement".
- "population rising / falling", if any settlement has a trend.
- Event marker types present: battle, disaster, ruin, relic, event. "battle" is omitted when wars are shown.
- **Line samples:**
  - road (#d8cfb8, 1.2, `3 3`)
  - trade road (#e8ad48, 2.4, solid)
  - hostility (#dc735d, 1.4, `6 4`)
  - rule (#b48ae6, 1, solid)
  - hunt (#dc735d, 1, `1 2`)
- war (crossed swords).
- "your note" (note pin), if notes exist for this world.
- Empty: "No markers on this map yet."

### Map time slider and past-epoch banner
**Time panel (`#hZaman`):**
- **Play/Pause** icon button `#zamanOynat`. Tooltip "Play epochs in order" / "Stop".
- **Range** `#zamanKay`, min 1, max = the current epoch `zaman.simdi`, step 1, value = the viewed epoch. Disabled when the current epoch < 2. The CSS var `--dolu` holds the fill percentage.
- **Label:** mono "E{n}", then "today" (bugün) if current, else "/ {simdi}".
- **Dragging:** stops playback and updates the label and fill live. Debounced 220 ms, it sets `HARITA.cag` (null if ≥ current) and re-renders.

**Playback (`haritaOynat`):**
- Starts at epoch 1 if at today. Each step renders, then waits 1500 ms before advancing.
- On reaching the current epoch it returns to today and stops.
- It stops on leaving the tab, on changing world, or on touching the slider.

**Banner (`#hBant`)**, only in past mode: chronicle icon, "**The world in Epoch {n}**", then one of:
- "photo taken at that epoch's end: the living and their populations" (when that epoch has a snapshot in `zaman.fotograflar`);
- "no photo for that epoch; showing those born up to then".

Button "Back to today" (`#bugunDon`, primary).

**Past mode effects:**
- Dragging markers is disabled and note-pin is disabled.
- War markers are filtered to `cag ≤ n` and never shown as ongoing.
- The star-of-epoch badge is hidden.
- The status line reads "You're looking at the past; markers can't be moved."

### Map scene rendering (`renderHarita`)

**Leakage:** `data.dunya.sizinti` ≥ `KORKU.uyari1` (30) adds class `sizinti-orta`; ≥ `KORKU.uyari2` (60) adds `sizinti-guclu`.
- These drive CSS: a breathing purple vignette layer, a desaturate/hue-rotate filter on the scene, and a flicker animation for strong leakage.
- Animations are disabled under reduced motion.

**Viewport fit:**
- k0 = min(W / (kapsam.w×1.12), H / (kapsam.h×1.12)). The offset centres the known area (`h.kapsam`), so the map auto-zooms out as the world grows.
- Changing world resets the zoom transform.

**Terrain (canvas):**
- **Offscreen pre-render:** drawn once to an offscreen canvas of the generator window (`h.pencere`) at resolution min(4, 4096/max(w,h)). Each zoom/pan frame only `drawImage`s it with the transform.
- **Background colour:** #0b1520 for ordinary worlds, else palette[1] darkened 70%.
- **Draw order:**
  1. Water and unknown cells. Unknown land #151a22, unknown water #0e1219, known water `araziRengi`.
  2. Coastline "wave rings": the coast path stroked 4 times at widths 26/17/10/5 with rgba(156,196,220) alpha 0.05/0.07/0.10/0.14.
  3. Known land cells: `araziRengi` shifted by the hillshade `golge`, with a 0.6 px same-colour stroke to hide seams.
  4. Layer tint per land cell (see below).
  5. A rgba(14,18,25,.45) fog overlay on fringe cells (`bilinen===2`).
  6. Mountain hachures: for known cells with normalised elevation ≥ 0.55, a small "^" stroke rgba(20,18,14,.55), 0.8 px, height 3+3e.
- **`araziRengi(h,i,tur)`:**
  - **Non-ordinary world types:** `palette[biyomIndeks(e,m,kara)]`, darkened −0.38 on land and −0.5 in water; −0.3 for water next to land.
  - **Ordinary type** (hand-tuned night palette):

    | Cell | Colour |
    |---|---|
    | water next to land | #1d3a4f |
    | water, e > −0.35 | #152d40 |
    | deep water | #0d1d2b |
    | land e < 0.05 (beach) | #6d6448 |
    | e < 0.32, moisture > 0.56 | #2f4a32 |
    | e < 0.32, moisture > 0.44 | #46583a |
    | e < 0.32, drier | #6b6343 |
    | e < 0.58, moisture > 0.5 | #3e4a37 |
    | e < 0.58, drier | #5e5644 |
    | e < 0.8 | #6a655c |
    | e ≥ 0.8 | #b9b4a8 |

- **`golge` hillshade:** Σ over neighbours of (neighbour − cell vector) × height difference; shade = clamp((dx+dy)×−0.012, −0.35, 0.3), applied as lighten/darken toward white/black (north-west light).
- **Layer tint:** filled per Voronoi cell on land, or on water cells of water regions.

  | Mode | Fill | Alpha |
  |---|---|---|
  | Regions | `hsl((regionId×97.3)%360, 42%, 58%)` per sub-region (or region) | 0.3 |
  | Creators | palette colour of the creator key of the sub-region's entity | 0.3 |
  | Religion | palette colour of `bolgeDin[top-level region]` | 0.42 |
  | Language | palette colour of `bolgeDil[top-level region]` | 0.42 |
  | Political | palette colour of `siyasi[sub-region or region].hakim_id` | 0.2 + min(0.2, pay/500) |
  | Terrain | none | — |

- **Category palette (`katmanPaleti`):** count the regions per category on this map and sort descending (ties by locale id). The top categories take `SERI` colours in order (#3987e5, #d95926, #199e70, #c98500, #d55181, #008300, #9085e9, #e66767). The rest share the grey `DIGER_RENK` #7a786f. The god himself (creator key 'tanri') is always gold #e8ad48.

**SVG overlay (`svg#harita`, group `gi` in map coordinates):**
- **Borders** (from `kenarlar(h)`: shared Voronoi edges between known cells):
  - Coastline: #d8cfb8, 1.1, opacity 0.75.
  - Region borders: political mode #f4ecda 2.2 solid 0.85; otherwise #ece6d8 1.2 dashed `5 3` 0.6.
  - Sub-region borders: #ece6d8, dashed `2 3`; political mode width 1.2 / opacity 0.6, otherwise 0.7 / 0.45.
- **Roads** (when Roads is on). Each road is routed by `yol(h,a,b)`: Dijkstra over Delaunay neighbours restricted to known cells. The cost is the Euclidean step × (1 + 2×max(0, elevation) on land, 3 on water), so roads prefer lowland.
  - `data.yollar`: trade (#e8ad48, 2.4, opacity 0.9, solid, class `h-ticaret`) or road (#d8cfb8, 1.1, opacity 0.6, `3 3`, class `h-yol`). Tooltip "Trade road / Road: A – B · {uzunluk/10} leagues (fersah)".
  - `data.rotalar` (entity links):
    - **ticaret** (trade) not already drawn: "Distant trade" in gold, 1.4, opacity 0.7, `1 3`, routed.
    - **dusman** (hostility): a straight line, #dc735d, 1.4, `6 4`, "Hostility: A – B · {aciklama}".
    - **yonetir** (rules): a straight line, #b48ae6, 1, opacity 0.7, "A rules: B".
    - **avlar** (hunts): a straight line, #dc735d, 0.8, `1 2`, "A hunts: B".
- **Region labels** (`g.bl`, one per region with a position):
  - **Text:** uppercase name (tr locale). Cormorant Garamond 700, letter-spacing .18em, size clamp(9 + √buyukluk×0.5, 12, 22). Fill #ece6d8, or #9cc4dc italic for water regions. Halo stroke #0b1520, width 3, opacity 0.7.
  - **Placement / collision:** labels are placed from the largest region down. A label is first tested against the settlement label boxes and then against labels already placed. It is shifted vertically ±0.9×height up to 4 tries, and hidden if it still collides. Placement is recomputed 120 ms after zoom.
  - Click opens the entity drawer.
  - **Hover info line:**
    - "**name** · {subtype} · {elevation class}, coastal · {top biomes} · neighbours: …";
    - for political data: "Ruler: {name} %{pay} · {n} communities contend".
  - Draggable (cursor `move`).
- **Point markers** (`g.mk`): every non-region entity with a position. Events already drawn as war/event markers are excluded. Screen-constant size (scale 1/(k0·zoom)).
  - **Settlements:** tier glyph (`yerlesimGlif`) in `var(--harita-yerlesim)` (#e0c06a); dashed if dead. Tier = server `kademeler[id].kademe` (koy/kasaba/kent/buyuk_kent/baskent → 0..4), falling back to the population thresholds.

    | Tier | Glyph | Radius |
    |---|---|---|
    | 0 village | dot | 4 |
    | 1 town | ring + dot | 6.5 |
    | 2 city | ring + castle | 9 |
    | 3 great city | double ring + castle + crown | 12.5 |
    | 4 capital | gold double ring + castle ×1.3 + gold star | 13.5 |

    - **Trend arrow:** green up / red down at the top-right when the population changed by ≥ `ARAYUZ.nufus_yon` (5%) vs `onceki_nufus`.
  - **Outsider (`dis`):** a dark purple halo r=14 + a blob shape.
  - **Others:** a dark circle stroked in the entity's family colour (`aileRengi(aileOf(tur))`), dashed if dead, with the type icon inside.
    - Radius: 7 for halk/hizip/tarikat (people / faction / cult); otherwise 5.5 + 0.35×guc_seviyesi (power level).
  - `<title>`: "name · tier name / type name · {pop} souls (previous epoch N, ±x%) / subtype".
  - Hover info: type tag + name + tier/subtype + population with delta.
  - **Labels** (when Labels is on): for settlements, places, resources, peoples, factions, or anything with power ≥ 5. Alegreya Sans, #ece6d8; settlement sizes 10/11/12.5/14/14.5 by tier (bold from town up), others 10.
    - **Visible when:** a city or above, or settlements at zoom > 1.3, or anything at zoom > 1.6.
- **War markers** (`g.sv`, Wars toggle): crossed-swords glyph offset (+13, −13).
  - Ongoing: #ff7a5c with a pulsing ring (CSS `savas-nabiz`). Ended: #9a8478.
  - Hover: "{name} · Epoch N · ongoing/ended". Click opens the drawer.
- **Event markers** (`g.is`, Events toggle), excluding those already shown as wars: a diamond (rotated rounded square, #12100e fill) at (−13, −13) with an inner glyph.

  | Type | Name | Colour | Glyph |
  |---|---|---|---|
  | muharebe | battle | #ff9a7a | X |
  | afet | disaster | #e8ad48 | lightning |
  | harabe | ruin | #b8a48c | columns |
  | kalinti | relic | #a8b4ff | diamond |
  | olay | event | #d8cfb8 | dot |

  Hover/tooltip "{name} · {type} / {subtype} · Epoch N". Click opens the drawer.
- **Note pins** (`g.np`): teardrop pins coloured by note colour (gold #e8ad48, red #dc735d, blue #6fa0e6, green #92c26d, purple #b48ae6 = altın/kırmızı/mavi/yeşil/mor). Only notes of this world (`dunya_id ?? 1`).
  - Click opens the read popup: "Your note · {date YYYY-MM-DD}", the text, and a "Delete" danger button with two-click confirm "Are you sure? Delete the note".
- **"Unexplored"** ("keşfedilmemiş") rotated italic text on the left and right of the known area (#3a4152).
- **Star of the epoch badge** (top-right, screen space; not in past mode): star icon + "{name} ascendant" ("yükselişte") in #f5e27a. The id comes from `data.dunya.cagin_yildizi` (fallback `data.yildiz`).

**Zoom / pan:**
- `d3.zoom().scaleExtent([0.3, 12])` on the SVG.
- **On zoom:** update the overlay transform, redraw the terrain canvas, re-apply the screen-constant marker transforms, update the scale bar, close the popup if it was user-initiated, re-place region labels (debounced 120 ms) and update label visibility.
- The previous transform is restored after a re-render, unless a focus request is pending.
- **Scale bar:** "{120 px in leagues} fersah", where 10 world units = 1 league (fersah). One decimal (comma) below 10.

**Focus ("show on map" / search):** zoom to k=3 centred on the entity. A teal (#7dbba8) pulsing ring (`odak-halka`, 3 pulses) is drawn. The info line reads "{tag} **name** · marked on the map".

**Drag-to-move:**
- `d3.drag().clickDistance(4)` on region labels and point markers.
- **Filter:** not in past mode, not in note mode, primary button only.
- On drag the element is raised and follows the pointer.
- On end, if it moved more than 2 map units: `POST /api/harita/konum` with body `{id, x, y}` (map coordinates, rounded by the server). Then clear `G.haritaCache` and the signature and re-render (the generator re-flows regions around the new seed). Error → toast.
- **Server effect:** sets `varliklar.harita_xy` and invalidates the server map cache.
- Note: dragging a region label moves the region's seed, so the whole territory re-grows around it.

**Notes (note-pin mode):**
- Clicking empty map (not a marker) opens the popup "New note" with:
  - textarea `#notMetin` (max 400, placeholder "What will happen here? A reminder to yourself…");
  - 5 colour swatches (radio, first selected);
  - "Pin" (İğnele, `#notKaydet`). Ctrl/Cmd+Enter also saves.
- Save: `POST /api/harita/not` with body `{x, y, metin, renk, dunya_id}`. An empty text gives the toast "A note must have text." Success toast "Note pinned".
- Delete: `POST /api/harita/not/{id}/sil`, toast "Note deleted".
- The popup is positioned above the click point and clamped 12 px from the view edges. Escape closes it.

**Ambient animation** (`canvas#hanim`, off under reduced motion):
- Water glints: up to 90 known coastal water cells (every 7th cell), blinking sin(t/700+phase) to alpha 0.55, radius 1.6.
- Clouds: 14 seeded drifting radial-gradient clouds (radius 180–520, speed 0.006–0.018 px/ms, alpha 0.035–0.085), wrapping horizontally across the window, with a slight vertical bob.
- The rAF keeps running while the signature is unchanged.

**Entrance animation:** once per world per session (GSAP): markers fade in with a random stagger over 0.8 s, region labels stagger 0.05 s, the terrain canvas fades 0.6 s. The CSS class `inis` on `.h-sahne` (0.9 s) plays when arriving via "descend".

**Status line (`#mapInfo`) default:**
- "{World} · {type name} · " (multi-world only).
- "Known {n} cells · {n} regions · {n} markers."
- Then a hint, one of:
  - past: "You're looking at the past; markers can't be moved."
  - note mode: "Note pin is on: click an empty spot."
  - otherwise: "Drag markers to move · click: open its page".

### Procedural map generator (`harita-gen.js`) — algorithm spec for re-implementation

**Constants:**
- `W=3000`, `H=2040`: the legacy canvas; its centre is used when nothing has coordinates.
- `CEKIRDEK={x:1000, y:680, w:1000, h:680}`: the server migrates old 0–1 normalised coordinates into this box.
- `BILINEN_ADIM=4`: fog rings beyond the known cells.
- `ARALIK=22`: jittered grid spacing.
- `PAY=900`: margin around entity coordinates.
- `YARICAP=320`: max top-level region flood radius.

**RNG / noise:**
- `hash(s)`: FNV-1a over code points, unsigned 32-bit.
- `mulberry(a)`: Mulberry32 PRNG.
- `gurultu(seed)`: value noise.
  - Permutation of 0..255 Fisher–Yates-shuffled with mulberry(seed), duplicated to 512.
  - Lattice value = perm[(perm[x&255]+y)&511]/255.
  - Bilinear interpolation with smoothstep fade.
  - fBm: `oct` octaves (default 5), amplitude ×0.5, frequency ×2.03, normalised by the sum of amplitudes. Output range ≈ 0..1.

**Terrain field `arazi(seed, ar)`** (memoised by seed + JSON(ar)):
- Parameters: `daglik` (mountainousness, default 1), `nem` (moisture offset, default 0), `deniz` (sea fraction, default 0.52).
- Three noise generators: g = gurultu(hash(seed+':h')), g2 = …':m', g3 = …':k'. Offsets ofx, ofy = 50 × mulberry(hash(seed+':o')).
- elevation(x,y) = g3(x/1500+ofx, y/1500+ofy, 3 oct)×0.95 + (g(x/300+ofx, y/300+ofy)×0.75 + g(x/90+ofx, y/90+ofy, 3 oct)×0.25) × daglik.
- moisture(x,y) = g2(x/330, y/330, 4 oct) + nem.
- **Sea level:**
  - Sample 4000 elevations at x ∈ [−6000, 9000), y ∈ [−6000, 8000), random via mulberry(hash(seed+':ornek')), and sort them.
  - Sea level = sample[clamp(floor(4000×deniz), 20, 4000−21)].
  - `alt` = sample[20]; `ust` = sample[len−20].

**`dunyaHaritasi({seed, varliklar, Delaunay, arazi, tur})`:**
1. **Window:** the bounding box of all entity `xy`, ±PAY, snapped outward to multiples of ARALIK. With no coordinates, use the point (W/2, H/2) ± PAY.
2. **Points:** one per grid cell (gx, gy). Position = ((gx+0.5+(r−0.5)×0.9)×22, (gy+0.5+(r'−0.5)×0.9)×22), with r from mulberry(hash(`${seed}:${gx}:${gy}`)). Points are therefore stable as the window grows.
3. **Topology:** Delaunay triangulation (d3.Delaunay); Voronoi clipped to the window; neighbour lists.
4. **Per cell:**
   - elevation `yuk`, moisture `nem`; `kara(i)` = elevation > sea level.
   - Normalised elevation `yNorm`: land = min(1, (e−sea)/(ust−sea)); water = −min(1, (sea−e)/(sea−alt)).
5. **Water components:** flood-fill connected water cells. `genisSu` (wide water) = a component of ≥ 40 cells. Candidate lists: land cells, and wide-water cells.
6. **Region classification:**
   - Regions (`tur==='bolge'`) with a parent region (`konum_id` pointing at a region) are sub-regions; the rest are top-level.
   - `suMu(v)` (is water region): the text `alt_tur + ' ' + ad` matches the water regex (deniz, okyanus, körfez, koy, göl, boğaz, lagün, su, sular, derinlik = sea/ocean/gulf/cove/lake/strait/lagoon/water/depth) and does not match the dry regex (sand/glass/cloud/salt/ash/dust/grass/bone/mist/light/star/fire/lava/ice followed by sea/lake/ocean; kuru/kurumuş = dry/dried; çöl = desert; kumul = dune). **LANGUAGE-SPECIFIC: drop or replace.** It infers whether a region is water from Turkish words in its name. Replace it with an explicit `is_water` / terrain flag on the region.
7. **Seed selection (`tohumSec`)** for each top-level region (candidates: wide water for water regions, else land):
   - **If the region has `xy`:** take the cell at xy. If it is not acceptable, BFS up to 40 rings for the nearest acceptable unused cell, and record the move in `tasinan` (moved).
   - **Without xy:** take 80 random candidates (mulberry(hash(seed+':'+id))). The score is −|dmin−300| + rnd×40, where dmin is the distance to the nearest used seed (spacing ~300). The first region scores −distance-to-window-centre + rnd×80. The best score wins, and the result is recorded in `yeniXY` (new position; persisted by the server).
8. **Territory growth (`taskin`, multi-source Dijkstra with a binary heap):**
   - Step cost = 1 + |Δelevation|×40 + (30 if crossing coastline).
   - Water regions grow only over water; land regions only over land.
   - Top-level regions are limited to Euclidean distance ≤ 320 from their seed.
   - Sub-regions then grow, unlimited, inside their parent's cells. Their seeds are chosen among the parent's cells (by xy, or the same scoring).
   - Result: `bolgeOf[i]`, `altOf[i]`.
9. **Region anchor (`konum[id]`):** the cell nearest the centroid of the region's cells.
10. **Point entities** (types yer, kaynak, yerlesim, halk, tarikat, hizip, olumlu, esya, olay, tur = place, resource, settlement, people, cult, faction, mortal, item, event, species), placed recursively up the `konum_id` chain (guard depth 8):
    - **If xy exists** and lies in or adjacent to its region's cells (or its parent is not a region), use xy exactly. Otherwise discard xy and mark it moved.
    - **Candidates:**
      - parent is a region: its land cells, or all its cells if it is a water region;
      - parent is a point: land cells within 2 neighbour rings of the parent's cell.
    - **Selection:** 24 random tries (mulberry(hash(seed+':n'+id))), skipping occupied cells. The score depends on the type:

      | Type | Score |
      |---|---|
      | settlement | (coastal ? 1 : 0) − yNorm×1.5 + rnd×0.5 (prefers low coast) |
      | resource | yNorm + rnd×0.5 (prefers high ground) |
      | other | rnd |

    - The result is recorded in `yeniXY` or `tasinan`.
11. **Known area (`bilinen`):** cells that belong to a region, or contain an entity, get value 1. If there are none, the centre cell. Then 4 BFS rings around them get value 2 (fog fringe). `kapsam` = the bounding box of known cells (min w 200, min h 140), plus `oran` (the known fraction) and `hucre` (the known count).
12. **Region info (`bilgi[id]`):**
    - `komsular`: neighbouring region / sub-region ids.
    - `kiyi`: coastal.
    - `yukseklik`: mean yNorm > 0.45 'dağlık' (mountainous), > 0.22 'engebeli' (hilly), > 0 'ova' (plain), else 'su' (water).
    - `buyukluk`: cell count.
    - `iklim`: up to the 3 biomes covering ≥ 12% of cells, as "{biome} %{pct}".

**Return:** `{W, H, pencere, pts, vor, del, komsu, yuk, nem, deniz, kara(), yNorm(), bolgeOf, altOf, konum{id:[x,y]}, yeniXY, tasinan, bilgi, bilinen, kapsam}`.

**Biome index (`biyomIndeks(e, m, kara)`)** → 0..9:
- Water: 0 shallow if e > −0.35, else 1 deep.
- Land: e < 0.05 → 2 (beach); e < 0.32 → 5 if m > 0.56, 4 if m > 0.44, else 3; e < 0.58 → 7 if m > 0.5, else 6; e < 0.8 → 8; else 9.

`biyom(e,m,kara,tur)` returns the type's biome name at that index. The same index selects the palette colour, both in the 2D map and in the planet shader's palette usage.

**World types (`DUNYA_TURLERI`)**, translated. `arazi` = {sea fraction, mountainousness, moisture offset}. Biomes and palette are both indexed 0–9 as: shallow water, deep water, shore, dry low, mid low, wet low, dry hills, wet hills, mountains, peaks.

| key | name | sea / mount / moist | biomes 0→9 | palette 0→9 |
|---|---|---|---|---|
| olagan | Ordinary world (Olağan dünya) | 0.52 / 1 / 0 | shallow sea, deep sea, beach, steppe, meadow, forest, barren hills, forested hills, rocky mountains, snowy peaks | #3b6a86 #1e3a52 #d8c79a #b9ad74 #8fae6a #4f7d4a #9a8a66 #5d7a52 #8b8478 #eef1f2 |
| okyanus | Ocean world (Okyanus dünyası) | 0.84 / 0.8 / 0.15 | coral shallows, abyssal sea, white beach, salt rocks, moss island, mangrove, rocky island, misty island, volcanic summit, icy peak | #3a9bb0 #0f2c4a #ece2c2 #a9a28a #6fa585 #3f7a5e #8a8576 #6b8a7a #5b4a44 #e8eef2 |
| kum | Sand world (Kum dünyası) | 0.06 / 0.9 / −0.35 | salt lake, dried sea, sand sea, dune, glass desert, oasis, red rocks, canyon, wind pillars, sand peak | #d8d2c0 #b8a888 #e8c88a #dfb26c #c9b49a #7c9a5a #b5643c #9a5434 #8a6a52 #f0dcb4 |
| buz | Ice world (Buz dünyası) | 0.45 / 1.1 / 0.05 | ice shards, black water, snow shore, ice field, tundra, needle forest, glacier, blue ice, ice mountain, storm peak | #9cc2d6 #1b2f45 #e6eef2 #d4e2ea #a9b8a4 #4c6a62 #bcd3e0 #8fb3cc #c8d6e0 #ffffff |
| lav | Lava world (Lav dünyası) | 0.38 / 1.4 / −0.25 | lava lake, magma ocean, obsidian shore, ash plain, basalt plain, sulphur swamp, coal hills, smoke valley, volcano, ember peak | #e8622c #7a1a0c #2a2226 #5a5050 #3c3434 #9a9a3c #463a36 #5c4c46 #2c2020 #ff9a3c |
| kristal | Crystal world (Kristal dünya) | 0.4 / 1.3 / 0 | light lake, prism depth, glass shore, quartz plain, echo meadow, crystal forest, ringing hills, rainbow valley, echoing mountains, pure peak | #8fd6e6 #2c3f7a #e8e4f4 #c8c4dc #a8d4c8 #7aa8c4 #b4a4d8 #d4a8c8 #9c8cc4 #ffffff |
| yasayan | Living planet (Yaşayan gezegen) | 0.42 / 0.9 / 0.25 | fluid lake, blood sea, membrane shore, skin plain, hair meadow, flesh forest, bone hills, vein valley, tooth ridges, eye peak | #b04a5a #4a1020 #d8a8a0 #c48a7c #a87a6a #8a3c44 #e0d4c0 #9a4a5a #f0e8dc #e8c8b8 |
| olu | Realm of the dead (Ölüler âlemi) | 0.5 / 0.9 / 0.1 | water of oblivion, black river, ash shore, bone plain, pale meadow, mist valley, grave hills, echo forest, silent mountains, dead peak | #4a5a6a #141a22 #8a8a86 #c8c0b0 #7a8478 #5a6670 #6a6460 #4a5450 #3c3a3a #d8d4cc |
| ruya | Dream realm (Rüya âlemi) | 0.6 / 1.2 / 0.2 | dream water, depth of sleep, cotton shore, floating island, violet meadow, whisper forest, slanted hills, inverted valley, cloud mountain, star peak | #8a9ae6 #2a2a6a #f0d8e8 #d4c4f0 #c4a8e0 #8a7ac8 #e0b4d4 #b4a0dc #e8e4ff #fff4c8 |
| ayna | Mirror world (Ayna dünya) | 0.48 / 1 / 0 | inverted water, silver depth, glass shore, reflecting plain, inverted meadow, mirror forest, echo hills, broken valley, silver mountains, inverted peak | #c4d0dc #5a6a80 #e8eef4 #b8c4d4 #a8b8c8 #8496ac #d4dce6 #9aaabc #74849a #ffffff |
| gaz | Gas giant (Gaz devi) | 0.9 / 0.6 / 0.3 | low cloud, pressure abyss, cloud shore, wind island, storm band, floating forest, cloud hill, lightning valley, vortex, eye storm | #d8b48a #7a4a2a #f0e0c4 #e4c8a0 #c8a87a #9a7a5a #f4e4cc #b48a6a #e89a5a #ffffff |

Per-world `arazi` stored on `dunyalar.arazi` (`{deniz, daglik, nem}`) overrides the type defaults; the 3D scene uses the same merge.

---


---

## Part 5 — Live feed, Chronicle, Network, Atlas, Languages, Gallery, Goals

<!-- Fragment C: Live feed, Chronicle, Network (2D/3D), Atlas, Charts, Languages, Gallery, Goals/Council/Comparison, Bookmarks. Source: /Users/egedogan_dursun/aerona/public (views/akis.js, kronik.js, ag.js, ag3d.js, atlas.js, grafik.js, diller.js, galeri.js, hedefler.js, core/imler.js, core/hedef.js). -->

### Conventions used in this part

- `aerona.<key>` = localStorage key written via the `yerel()/yerelYaz()` helpers (JSON-encoded values, every read/write in try/catch). Written below as `aerona.agMod` etc.
- `kural('PATH', default)` = a tunable world rule ("Dünya kuralları") loaded once from `GET /api/denge`; the UI never hard-codes balance numbers, it reads them with a fallback default. In the rewrite, these are the settings registry values; keep the fallback defaults listed here.
- `G.S` = the global state snapshot (`GET /api/state`), `G.K` = constants/catalogs sent by the server (rarities, entity types, chronicle categories, etc.).
- "Two-click confirm" = global pattern (core/formlar.js): a `button[data-onay="…"]` swallows the first click, swaps its label to the confirm text and turns red (`danger`); a second click within 4 s performs the action; otherwise it reverts. Forms with `data-post` + `data-onay` behave the same.
- `act(fn, okMsg)` = global action wrapper: locks the clicked button, runs the request, toasts `okMsg`, then does a full `refresh()` and offers "undo" from the god's action log.
- Entity link attributes (clicking opens the record drawer): `data-v="id"` (entity), `data-o="id"` (son), `data-yabanci="id"` (foreign god), `data-tanri-ac` (the creator god), `data-rehber="id"` (world traveller's guide), `data-dunya-harita="id"` (world map).
- Number formatting: `fmt()` = `toLocaleString('tr-TR')` (dot thousands separator). LANGUAGE-SPECIFIC: replace with `en-US` grouping.
- "Rarity colours" `RRENK`: common `#9097a0`, uncommon/"seçkin" `#7fc489`, rare `#6fa0e6`, epic `#b48ae6`, legendary `#e8ad48`, mythic `#f07aa0`.
- Entity "families" (shape + colour token `--aile-<k>`), used by the network graph and legends:
  | family key | label | shape (2D / 3D) | member types |
  |---|---|---|---|
  | `yer` | Places (Yerler) | square / cube | dunya, bolge, yer, yerlesim, gok |
  | `topluluk` | Communities & persons | circle / sphere | halk, olumlu, tarikat, hizip, ordu |
  | `nesne` | Objects & knowledge | triangle / 3-sided cone | esya, teknoloji, yapit, kaynak, arac |
  | `tanri` | Gods | diamond / octahedron | ogul, tanri, yabanci, dis |
  | `kultur` | Culture & belief | hexagon / hexagonal prism | efsane, gelenek, kehanet, dil, eser, kanun, yasa |
  | `canli` | Living things & spirits | ring (hollow) / torus | tur, ruh |
  | `olay` | Events | 5-point star / extruded star | olay |
  | `diger` | Other | plus / extruded plus | anything unknown |

---

### Live Feed sidebar ("Canlı akış")

**Purpose.** A right-hand sidebar that streams everything the simulation does in real time: sons' (LLM agents') thoughts, tool calls and results, mortal agents, world-engine notes, Fate/chronicler steps, background jobs, image generation, notifications. It also hosts the global progress indicator for long jobs and the "Stop" button for a running age.

**How it is opened / closed.**
- Always mounted in `#live` (aside). Header button `#liveToggle` (chevron icon, title "Hide live feed" / "Canlı akışı gizle") adds class `live-closed` to `#app`. A floating button `#liveReopen` ("Live feed" / "Canlı akış", pulse icon) appears to reopen it.
- Clicking the thin top progress strip `#ustIlerleme` (in the top bar) also opens it.
- Persisted: `aerona.canliAcik` (boolean). Default when unset: open if `window.innerWidth > 1100`, closed otherwise.
- Toggling re-renders the current tab if it is `ag`, `harita` or `kozmos` (canvas sizes change). A window `resize` also re-renders those three tabs (debounced 200 ms).

**Layout (top → bottom).**
1. **Header** (`.live-head`): title "Live feed" (Canlı akış); state pill `#liveState` (default "idle" / "sessiz", class `on` when busy); ambient-sound toggle `#ortamSes` (wave icon); feed-sound toggle `#liveSes` (speaker / speaker-muted inline SVG); hide button `#liveToggle`.
2. **Progress panel** `#liveIlerleme` (hidden when idle):
   - Row 1: `#liAd` job title (default "Preparing…" / "Hazırlanıyor…"), right side `#liSure` elapsed `m:ss` + `#liKalan` remaining-time text.
   - Bar `#liAsama` (title "Phases of the age"): width = `max(4%, phase/5 × 100%)`.
   - Row 2: `#liAlt` subtitle (who is thinking / what is being written), `#liAjan` "n/total" agent counter.
3. **Filter strip** (`.live-suzgec`, horizontally scrollable):
   - Actor filter `#liveFiltre` (static markup): "All" (Hepsi), "Gods" (Tanrılar → `ogul`), "Mortals" (Ölümlüler → `olumlu`), "World" (Dünya → `dunya`), "Fate" (Kader → `kader`). Single-select; handler lives in views/palet.js: toggles `on`, re-evaluates visibility of all lines, scrolls to bottom.
   - Separator, then world-event category filter `#liveAkis` (see below).
4. **Sound settings** `#liveSesAyar` (only rendered while feed sounds are ON): a `<details>` "Which events make sound" (Hangi olaylar ses çıkarsın) with one checkbox per category (icon + full category name) and a small play button "Listen" (Dinle) per row that previews the tone.
5. **"New events" badge** `#liveYeni` — floating button "`N` new events ↓" (`N yeni olay ↓`).
6. **Body** `#liveBody` — the scrolling list of lines. Empty-state paragraph: "When a son takes action, his thoughts, tools and words flow here. At the end of an age the mortal world's own events and Fate's verdict land here too."

**Line model.** Every line is a `div.ev.<classes>` appended at the bottom; attributes:
- `data-kat` = actor category for the actor filter (`ogul|olumlu|dunya|kader`). Assigned explicitly by the caller, else inferred: class starting with `world` → `dunya`; class containing `kader|asama|sys` AND html containing "Kader" or "kronikçi" → `kader` (LANGUAGE-SPECIFIC hack — text sniffing; replace with explicit category per event kind); else the "current actor category" `G.liveKat` which is set by `basla` (ogul), `olumlu_basla` (olumlu), `motor_basla` (dunya), `kader_adim` (kader). Default `ogul`.
- `data-ak` = world-event category (only `motor_not` lines).
- `data-zaman` = timestamp label `Ç{age} · HH:MM` (rendered by CSS `::before`), `title` = "Age N · full local datetime". If identical to the previous line's label the line gets `damga-ayni` (dimmed stamp). Age comes from `e.cag` (server stamp), else back-computed `_cag` for restored events, else current age.
- Visibility = actor filter AND category filter.
- Hard cap: 500 lines (oldest removed).
- **Every text node of every line is passed through `ekDuzelt`** (Turkish suffix/apostrophe harmony fixer). LANGUAGE-SPECIFIC: drop.

**Auto-scroll.** If the user is within 160 px of the bottom (or during journal replay) the body sticks to the bottom; otherwise new visible lines increment the badge counter instead. Clicking the badge or scrolling back near the bottom clears it. Streaming text (`akis`) uses the same "only if near bottom" rule.

**Actor headers & interleaving.** Several actors (sons in parallel, mortals) can stream simultaneously. Actor key = `o<ogul_id>` for son events, `v<varlik_id>` for mortal-agent events (only kinds `akis, dusunce, arac_hazirlaniyor, arac, arac_sonuc, bitti, olumlu_bitti, yeniden, hata`). If an event's actor differs from the last header's actor, a short header line is inserted: `[sigil] <Son name> continues` ("sürdürüyor"), class `who devam`; for mortals `<entity link> continues`.

**Grouping.**
- *Reading tools* (`dunya_ozeti, dunyaya_bak, varlik_incele, varlik_ara, hafizam, kardesi_incele` — must mirror server `OKUMA_ARACLARI`): consecutive read-only tool calls of the same son collapse into one "reading" line (eye icon, "okuma") showing the last 5 parts joined by " · " (prefix "… · " if more), plus a mono badge `×N` (title "N reading tools in a row").
- *World events* (`motor_not`): consecutive events of the same category form a group; first two visible, the rest get class `katli` (collapsed) and the group head gets a button "+N similar" (`+N benzer`) / "collapse" (`daralt`) with `aria-expanded`.

**World-event categories** (`G.K.AKIS_KATEGORILERI`, server-side keyword classification) plus a synthetic `dunya` = "Other world events":
| key | name | icon | sound tone [Hz, wave, sec, second note Hz] |
|---|---|---|---|
| yolculuk | Ships and journeys | arac | 523 sine 0.22 → 659 |
| kapi | Gates and routes | kilit | 392 triangle 0.30 → 294 |
| sizinti | Leakage and fear | dis | 98 sawtooth 0.60 → 92 |
| savas | Wars | meydan | 196 square 0.16 → 147 |
| afet | Disasters | yildirim | 131 sawtooth 0.40 → 110 |
| gok | Sky events | gok | 880 sine 0.50 → 1175 |
| hayat | Birth and death | dogum | 659 triangle 0.22 → 784 |
| medeniyet | Civilization | yerlesim | 440 triangle 0.24 → 554 |
| dunya | Other world events | dunya | 330 sine 0.14 (single note) |

Server classifies by Turkish regexes (src/akis.js) — LANGUAGE-SPECIFIC: in the rewrite the engine must emit the category explicitly.

Category filter row `#liveAkis`: "All events" (Tüm olaylar) + one button per category showing icon + **only the first word** of the name (`ad.split(' ')[0]`, LANGUAGE-SPECIFIC truncation hack — use proper short labels) with full name as title. Buttons of categories with no lines in the feed are hidden (the selected one always shown); the whole row hides if no world events exist. Selecting re-filters all lines and scrolls to bottom. Not persisted.

**Sounds.**
- Feed tones: WebAudio, synthesized (no files). Each note: oscillator → gain envelope (0.0001 → peak 0.09 for sine/triangle, 0.035 for square/sawtooth in 15 ms → exponential decay over duration). Second note starts at 55% of the first's duration. Throttled to one tone per 220 ms. Played only for live (`motor_not`) events, when feed sounds are on and the category isn't muted.
- Toggle `#liveSes`: title "Turn on feed sounds (each event type plays a short tone)" / "Turn off feed sounds"; toast "Feed sounds on/off" (Akış sesleri açık/kapalı); when turning on, plays the `gok` tone as a preview. Persisted `aerona.akisSes` (bool), mutes `aerona.akisSessiz` (array of category keys). The same prefs are also editable from Settings → Appearance.
- Ambient drone `#ortamSes`: 4 oscillators (55, 82.4, 110.3, 164.6 Hz; sine/triangle alternating; detune −6/−2/+2/+6 cents; gains 0.5/0.25/0.18/0.08) → low-pass 420 Hz Q 0.7 → master gain ramped to 0.045 over 3 s; LFO 0.05 Hz modulating cutoff ±180 Hz. Stop = 1.2 s fade-out. Persisted `aerona.ortamSes`; if saved ON it starts on the first `pointerdown` (autoplay policy). Toast "Ambient sound on/off".

**Progress & ETA.**
- Busy kind → title (`#liAd`) and state pill text:
  | `mesgul.tur` | progress title | state pill |
  |---|---|---|
  | cag | Age is closing (Çağ kapanıyor) | age running |
  | ogul | A son is acting | a son is acting |
  | cagirma | Summoning a new son | summoning |
  | genesis | World is being created | genesis |
  | vahiy | Revelation descending | revelation descending |
  | derinlik | Deepening | deepening |
  | destan | Writing an epic | writing epic |
  | uyandirma | Peoples awakening | peoples awakening |
  | prompt | Writing prompts | writing prompts |
  | tamamlama | Completing the world | completing world |
  | suret | (none) | drawing likeness |
  | other | Working | busy |
- On `merhaba` with an ongoing job: title "A job is running" (Süren bir iş var).
- Elapsed ticks every 1 s. Remaining text: "" (unknown), " · ~N min left" (`~N dk kaldı`), " · less than 1 min left" when < 60 s, " · taking longer than expected" (beklenenden uzun sürüyor) when estimate hits 0; tooltip "Estimated from recent step averages".
- ETA sources in priority order: (1) `G.S.tahmin` from `/api/degisim` `durum.tahmin` (`{calisiyor, kalan_sn}`), if fresher than 90 s; (2) `GET /api/cag/tahmin` → `{ort_cag_sn, ornek, asama_baslangic_ort_sn{phase:sec}}`: remaining = avg age − avg start of current phase − time in phase; (3) per-step averages from `GET /api/olcum` → `adimlar[{adim, ort_ms}]`: estimate the 5 phases as `[sons × son-turn, ceil(mortals/parallel) × mortal-turn, 0, fate+chronicler+peoples' voice, 0]`, refined within phase 1 by the son queue position. Non-age jobs use the step average named by job kind. If any of son/mortal/Fate steps was never measured → no estimate. Measurements cached 5 min (forced reload after each `cag_bitti`). LANGUAGE-SPECIFIC coupling: steps are matched by Turkish label prefixes ("oğul turu", "ölümlü turu", "kader", "kronikçi", "halkların sesi", "derinleştirme", …) — use stable step keys in the rewrite.
- **Top progress strip** `#ustIlerleme`: mirrors the panel even when the sidebar is closed: bar width = phase/5 (min 4%) for age jobs, indeterminate animation for other jobs; text = `title · elapsed · estimated <remaining> · subtitle`.
- **Complete-age button tooltip** (`cagIpucu`, used by the "Complete age" button rendered elsewhere): lines: (a) "Age N was interrupted; from phase K onward it resumes where it left off." / "Age N was interrupted during the gods' turn; the turn resumes with sons who haven't acted yet." / "N sons are waiting." / "All sons have acted this age."; (b) "Complete age: N son turns + M mortal agents + world engine + Fate and chronicler; then growth, faith and essence are computed."; (c) "Estimated time ~X min (average of last K ages)" or "(from step averages)"; plus "last age took ~X min" or "last age's model calls took ~X min"; (d) "It is model work; while running, 'Stop' halts it at a safe point, then it completes from where it stopped." M = `dunya.olumlu_sayisi ?? kural('OLUMLU_AJAN.varsayilan', 4)`.

**Stop button** `#btnDurdur` (top bar, red): visible only while `G.S.mesgul.tur === 'cag'`. Two-click confirm "Are you sure? Stop at a safe point" (Emin misin? Güvenli noktada durdur). Action `POST /api/cag/durdur` body `{}`:
- 404 → toast error "This server version doesn't know how to stop an age yet; the age continues."
- 501 → toast `hata` or "Stopping an age isn't supported yet."
- 409 → toast "No age is running"; hide button.
- OK → toast "The age will stop at a safe point; you can resume it afterwards"; feed line "[stop icon] Stop requested: the age will stop at a safe point."; button becomes disabled spinner "Stopping…" (Duruyor…, title "The age will stop at a safe point") until `serbest`.
- Idle label: "[■] Stop", title "Stop the age at a safe point; then 'Complete age' resumes it from where it stopped".

**Connection.** `new EventSource('/api/olaylar')`; each message is JSON `{kind, …}`. On error: close and reconnect after 2 s (no backoff). Server sends `merhaba` immediately and a `: ping` comment every 20 s. On `merhaba` any still-open "writing…" lines are closed with " · connection renewed; writing was interrupted" (marked error) and pending tool spinners cleared.

**Journal restore (on app load).** `GET /api/gunluk` → array of past events (server ring buffer, persisted in SQLite; excludes transient kinds `gorsel_sirada, gorsel_ilerleme, gorsel_durum, is_sirada, is_basla, is_bitti, mesgul, serbest, merhaba, sira, akis, arac_yaziliyor, yaziyor, arac_hazirlaniyor`). If non-empty: clear body, add "[chronicle icon] Previous feed (N events) restored." (Önceki akış (N olay) geri yüklendi.), then replay all events with `G.geriYukleniyor = true` (suppresses toasts, drawers, sounds, progress UI, streaming). Events missing `cag` get their age back-computed (walk backwards; every `cag_bitti` with `yeni_cag` sets age = yeni_cag − 1). Side-effect kinds (`bildirim, dunya_dogdu, yeni_ogul, yukselis, vahiy, cag_bitti, hata, genesis_bitti, mesgul, serbest`) are NOT replayed through the handler; only `cag_bitti` ("Age N began (the age lasted X min Y s).") and `hata` (error line) are re-rendered. Errors are swallowed silently.

**Misplaced code in this module** (belongs to Genesis screen): `#genesisForm` submit → disables `#gSubmit`, note "The world is being thought… (about a minute)", `POST /api/genesis` `{tanri_adi, tohum, ton, sihirbaz}`; on error toast + re-enable. The `hata` event also re-enables `#gSubmit` with note "Try again." if no world exists yet.

**Network-repair line renderer** (`agOnarimSatiri`, reused by the Network health panel): icon (checkmark for rule-based `kural`, Fate icon otherwise) + `metin`; if no links but `bakilan` present: " (looked at: A, B, …)"; if `baglar` present: `<details>` "N links" listing each: `<endpoint A> <b>link type label</b> (previously "related") <endpoint B> — justification`; closed links show "link closed" (bağı kapandı). Endpoints are typed links (`{t,id,ad}`); link labels from `G.K.BAG_ETIKET` else code with underscores → spaces.

---

### Realtime event kinds

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

---

### Chronicle tab ("Kronik")

**Opened by.** Tab button `data-tab="kronik"` (URL hash `#kronik`, persisted `aerona.tab`); from palette/bookmarks via `kronikGit({cag, id})` which opens the tab, opens and loads that age, scrolls to it and flashes the entry.

**Data loaded on render** (parallel):
- `GET /api/caglar` → closed ages, newest first: `{cag, ad, ozet, anlati, yil_bas, kronikci (object {ad, kim, unvan, halk_ad|halk, halk_id} or legacy string), dunyalar[{dunya_id, dunya_ad, anlati, ozet}]}`.
- `GET /api/kronik/caglar` → per-age counts `[{cag, ad, n}]` (optional).
- `GET /api/iplikler` → story threads `{id, metin, durum ('acik'|…), ilgili[{id,ad}], …}`.
- `GET /api/istatistik` → end-of-age snapshots `[{cag, simdi?, nufus, murit, varlik, dil, kelime, bilgi, savas, ticaret, ittifak, yapit, esya, olu, ogullar{<id>:{inanc, varlik}}, …}]` (last row = current age with `simdi: true`).
- `GET /api/bakislar` → biased per-people retellings `[{cag, halk_id, halk_ad, tarihci, metin}]`.
- `GET /api/kozmik-kronik?son=30` (only when multiple worlds) → `[{cag, ad, dunyalar[{dunya_id, olay_sayisi, basliklar[]}]}]`.
- Entries per age lazily: `GET /api/kronik?cag=N` → `[{id, cag, yil, tur, metin, varlik_ids[], ogul_id, …}]`. Cached in memory; the current age is always force-reloaded; closed-age caches are dropped when their server count changes or when that age just closed. Concurrent requests for the same age are shared.
- If a world is selected in the top bar: entity→world map (`varlikDunyalari()`) for filtering.

**Layout (top → bottom).**
1. **Page header**: "[chronicle] Chronicle" (Kronik); subtitle "At the end of every age the mortal world lives its own flow, Fate judges the creations and a chronicler tells what happened." + if a world is selected: "Showing the records of **World**; age narratives, the traces of ages and the comparison cover the whole cosmos." Action link "[codex] Download Codex (Markdown)" → `GET /api/kodeks.md` (download).
2. **Filter box**:
   - Search input `#kronikAra` placeholder "Search the whole chronicle…"; right-aligned mono counter: unfiltered "N records" (total from counts) or "N loaded"; filtered "matching / total". Tooltip: "k/n ages' records loaded · records matching World · N records in the whole chronicle".
   - "Clear" (Temizle) button when search or type filter active → clears both.
   - Type filter chips (horizontal scroll), one per chronicle type present in loaded ages (+ any selected), sorted by count desc: icon + readable type name + count. Multi-select toggle. Type `motor_ham` ("event log") lines are hidden unless that chip is selected.
   - Note when not all ages loaded: "Types and counts from opened ages (k/n)."; and when a type filter is active: "Type filter only works in opened ages (k/n ages loaded). [Load all ages]" (button shows spinner "Loading…" while running; loads with max 3 concurrent requests).
3. **Sticky age strip** `nav.cag-serit` ("Jump to age"): one button per closed age oldest→newest "ÇN" (tooltip age name · N records) + current age with a dot (class `suren`). The button for the age currently at the top of the viewport is highlighted (`on`) and auto-scrolled into view (scroll listener on `#main`, rAF-throttled).
4. **Search results** (when query ≥ 2 chars): while server search pending: "[spinner] Searching the whole chronicle…". Then section "[search] “q”  N records · in K ages · whole chronicle (· results in unopened ages can't be filtered by world)". Grouped by age desc: header "ÇN <age name> [→ Go to age]"; if the age name/narrative matched: "Appears in the age's name or narrative."; local matches (full entry, clickable, with bookmark button) and server-only matches (`{t:'kr', id, ad, alt, cag?, tur?}` rendered from summary). Age of a server result = `cag` field, else parsed from `alt` text "Ç5"/"Çağ 5" (LANGUAGE-SPECIFIC regex). Unknown age group: "Age unknown". Empty: "“q” doesn't appear in the whole chronicle." Server search: `GET /api/ara?q=` (case/diacritic-insensitive Turkish folding), filtered to `t==='kr'` (entries) and `t==='c'` (ages). Debounce 220 ms. Server-found ids also count as local matches.
5. **Cosmic chronicle** (multi-world only, `<details open>`): "[world] Cosmic chronicle  last N ages · what happened in each world at the same time". Grid: first column "Age" (ÇN + small name), one column per world (header = world name button → traveller's guide, coloured by world palette). Cell: "N events" + bullet list of headlines (auto-linked) or "quiet" (sessiz). Rows oldest→newest. Horizontal scroll.
6. **Traces of the ages** ("Çağların izi"): "[xp] Traces of the ages  a snapshot of the world/whole cosmos as each age closed" → charts (see Stats charts).
7. **Compare ages** (`<details>`, see below).
8. **Open stories** "[thread] Open stories N" → thread list (renderer from Pantheon module); **Closed stories (N)** in a collapsed `<details>`.
9. **Ages list**:
   - *Current age* article (only if it has entries): header "AGE N · ONGOING" + bookmark button; text "This age hasn't closed yet; the world engine, Fate and the chronicler will speak at its end."; entries (filtered) or "No records match the filter."
   - *Closed ages* newest first: header "AGE N · YEAR Y" + age name + bookmark; summary (`ozet`); delta chips vs previous age snapshot (population, words, knowledge, hostility, trade, works, dead: "+N"/"−N", compact numbers); narrative block (see below); collapsible log `<details>` "Records of the age (matching / N)" whose body loads on first open ("[spinner] Loading records…"); auto-opens when a filter is active and it has matches.
   - Empty: "The chronicle is empty. When you complete the first age it is told here."

**Entry rendering.** `div.entry.k-<type>` with `data-kid`, tooltip = type name; type icon (`KRONIK_IKON`) + text (strip `[iplik#N]` markers, Turkish suffix fix, auto-link known names) + `when` "ÇN · year Y". Clicking a search result entry jumps to its age and flashes it (class `parla`).

**Chronicle type names** (`KRONIK_AD`; unknown → code humanized): motor_ham event log; yaratim creation; soz word; meydan challenge; dua prayer; emir command; kader Fate; olum death; dogum birth; sistem system; mesaj message; tanri god; dunya world; ahit covenant; lanet curse; ruya dream; entrika intrigue; kaynak resource; varolus existence; yildiz star; yukselis ascension; kiyamet apocalypse; mucize miracle; isyan rebellion; tanri_savasi war of gods; inkar denial; macera adventure; bilgi knowledge; diplomasi diplomacy; afet disaster; dil language; uretim production; insa construction; kultur culture; kesif discovery; goc migration; ticaret trade; savas war; tapinma worship; konsey council; iklim climate; dirilis resurrection; armagan gift; dunya_dogusu birth of a world; sefer expedition; tanri_isareti the creator's sign; yabanci_tanri foreign god; kozmik cosmic; yasak prohibition; kozmik_hukuk cosmic law; gok sky; ruh spirit; cag_degisimi change of age; efsanevi_sefer legendary expedition; olumsuzluk immortality; medeniyet civilization; onceki_yaratilis previous creation; korku fear; dis from outside; evcillestirme domestication; kimera chimera; borc debt; dunya_yasi world's mourning; fidye ransom; kacis escape; kehanet prophecy; kurtaris rescue; ordu army; soy lineage; tanri_itibar the god's reputation.

**Age narrative block** (`cagAnlatiHtml`):
- If any people's retelling exists for the age: "Whose eyes" (Kimin gözünden) tab row: "Chronicler" + one tab per people (coloured dot, hue = `id × 137.5 mod 360`). Selection per age kept in memory only.
- Chronicler view: "[pen] Chronicler: **Name** (link to people if `halk_id`) · who · title · people"; narrative prose (auto-linked); per-world narratives (only if ≥ 2 worlds have one): collapsible sections "[world] World name  summary", the selected world first and open; hint "N peoples' historians wrote this age from their own eyes; pick one above."
- People view: header "[people] <People> people's historian **X** narrates" / "narrates without writing their name" + warning chip "[eye] biased account" (tooltip "This account is bent by the people's own interest and memory"); their text.

**Compare ages** (`<details>` "[network] Compare ages  how the world/whole cosmos looked at the end of two ages"): only if ≥ 2 snapshot rows. Two selects (`#karsiA`, `#karsiB`; options "ÇN · now" or "ÇN · first 28 chars of name") with "↔" and a swap button. Default = first and last snapshot (kept in memory). Grid columns: metric | A | B | Difference. Metrics: Mortal population (nufus), Disciples (murit), Canon entities (varlik), Languages (dil), Words (kelime), Knowledge (bilgi), Hostility (savas), Trade routes (ticaret), Alliances (ittifak), Works (yapit), Items (esya), Dead (olu), + any other numeric field present (key with `_`→space, gear icon), + "Total faith of the sons" (sum of `ogullar[*].inanc`). Difference: green "+N", red "−N", muted "±0" (compact numbers). Below: two summary cards "ÇN · name" with the age `ozet`, or "This age is ongoing; its summary is written at the end of the age." / "No summary."

**Realtime.** Re-renders on incremental refresh when `kronik_yeni > 0` or worlds changed. Bookmark buttons (`data-im`) handled globally.

---

### Stats charts ("Çağların izi", grafik.js)

Hand-built inline SVG line charts (no library).
- **Chart primitive** `cizgiGrafik(id, {baslik, seriler[{ad, renk, d[{x:age, y}]}], genis=280, ust, xs, yukseklik})`: width W (default 280), height 170 if W > 400 else 140 (or explicit); margins L 44, R 78 if multi-series else 14, T 12, B 22. Y max = fixed `ust` or "nice" ceiling (first digit rounded up at the power of ten). Gridlines at 0, 50%, 100% with compact labels. X labels "ÇN": at most ~8 (every ceil(n/8)-th), last always shown, earlier label dropped if it would overlap the last. Series: 2 px polyline + 4 px end dot with panel-coloured ring. Direct end labels for 2–4 series (first 11 chars, de-overlapped by 12 px). Legend chips for > 1 series. Caption shows the last value (mono) for single series.
- **Hover**: invisible hit-rect; nearest age → vertical guide line + tooltip "Age N" + per-series "● name value".
- **Palette** `SERI`: `#3987e5, #d95926, #199e70, #c98500, #d55181, #008300, #9085e9, #e66767` (son colour = index by son id order; `sonRengi`).
- **Compact number** `kisa()`: ≥ 1e6 → "1,2 mn"; ≥ 1e4 → "12 bin"; else locale integer; negative sign "−". LANGUAGE-SPECIFIC ("mn"/"bin", comma decimal): use English compact notation (1.2M, 12K).
- **Traces content** (`izHtml(ist)`): empty if < 2 snapshots: "Charts appear when the first age closes." Four single-series charts: Mortal population, Disciples, Words in the dictionary, Canon entities. Then "[son] Sons through the ages — each son separate; faith on the same scale for all sons": small multiples, one card per son that has data (sorted by id): son link (+ status if not active), two 240×100 charts sharing the age axis: "Faith" (shared Y max across all sons) and "Existence (0–100)" (Y max 100; missing → 60).

---

### Network tab ("Ağ") — 2D knowledge graph

**Opened by.** Tab `data-tab="ag"` (`#ag`). Mode persisted `aerona.agMod` (`2b`|`3b`).

**Data.** `GET /api/graf` → `{nodes, links}`:
- nodes: sons `{id:'o<id>', ad, tur:'ogul', nadirlik, g: 4 + raritySortIndex×2, cag: birth age, durum}`; entities (status kanon/olu/gerceklesti) `{id:'v<id>', ad, tur, g: 2 + power level, durum, yaratan, konum, cag}`; creator `{id:'t1', tur:'tanri', g: mythic size, cag 0}`; foreign gods `{id:'y<id>', tur:'yabanci', g: legendary size, durum}`.
- links: `{source, target, tur, cag, gecmis?:1}` (`gecmis` = inactive/ended relation).
- Client-side extension when multiple worlds (`agVeriGenislet`): each node gets `dunya` (entity→world map, son's world, foreign god's world); synthetic world nodes `{id:'w<id>', tur:'dunya', g:9}`; links `rota` (inter-world routes from cosmos data, `aktif` 0/1 via route open state), `dunyada` from root regions/places (no `konum_id`) and foreign gods to their world. If a world is selected in the top bar: keep only that world's nodes + neighbouring worlds (via routes) + world-less nodes.

**Layout.** Full-bleed `<canvas id="graph">` + floating top toolbar `#agUst` + floating info card `#agBilgi` + 3D container `#ag3Yer` + hover tooltip `#agIpucu`.

**Toolbar (row 1, `.atlas-ust`)**:
- Segmented "2D | 3D" (titles "Flat, top-down view" / "Three-dimensional, rotatable and navigable"). Persist `aerona.agMod`.
- Search `#agAra` "Search a node and focus…" with datalist of all node names. On change: exact case-insensitive name match → set focus; else toast "No such node in the network." (error).
- Link-group select `#agBag` (persist `aerona.agBag`): All links (hepsi); Excluding location links (konumsuz: all but `icinde`); Conflict (catisma: dusman, oldurdu, lanetledi, avlar, yok_etti, neden_oldu, taraf); Faith & narrative (inanc: tapar, kutsadi, kutlar, anlatir, ruhu_indi); Lineage, property & making (soy: soyundan, yonetir, sahip, uretti, insa_etti, gocetti, uyesi); Knowledge, language & trade (bilgi: bilir, konusur, kaynagi, ticaret, muttefik, bilirdi, konusurdu); Travel & trade network (yolculuk: rota, ticaret, gocetti, kesfetti, harac_oder — injected in `kur()`, but listed first in the select).
- Focus radius `#agDerin` "1/2/3 steps" (persist `aerona.agDerinlik`, default 2). Next to it a warning chip `#agAdimNot` shown when the radius was auto-reduced: "[gear] crowded: N steps shown" (tooltip: "World rules → Interface → Network: max nodes shown around focus (T). The Whole network button lifts the limit.").
- (multi-world only) "Cluster by world" toggle `#agKume` (persist `aerona.agKume`): resets positions and transform.
- Focus chip: if a focus is active: chip "[deepen] Name" (+ " · focus" when automatic; tooltip "Your chosen focus" / "Automatically chosen focus: selected record or most-connected one") + button "[network] Whole network" (`#agOdakKaldir`, tooltip "Show all nodes (may be crowded)") → clears focus, persist `aerona.agHepsi=true`. Otherwise button "[deepen] Focus view" (`#agOdakDon`, "Start with a focus node and its surroundings") → `aerona.agHepsi=false`.
- `<details>` "Connectivity" (Bağlılık) → network-health panel (see below), measured when opened.
- `<details>` "How are they connected?" (Nasıl bağlı?): two inputs (datalist) "First…" → "Second…", primary "Find" (Bul), "Clear" (when a path is shown), hint "or click a node, Shift+click the second". Validation toast: "Pick both nodes from the list." Path request `GET /api/yol?a=<id>&b=<id>` → `{yol:[ids], adlar{id:name}, adimlar[{a,b,tur,ileri,aciklama}]}` or `{yok:true}`.
- `<details>` "Types and links" (filter by type; meaning of link colours): per family, a row of toggle chips per type present (type icon + name + count), and a link-colour legend: conflict (`--danger`), faith & narrative (`--r-efsanevi`), inter-world route (`--aile-yer-yazi`), inside (location) (`--muted`), other links (`--accent`), past (ended) relation (muted, dotted).
- Row 2 **Time slider** "[chronicle] Time": `<input type=range id=agCag min=1 max=<current age>>`, fill via CSS `--dolu`; label "ÇN / max" or "ÇN today"; "Today" button when not at max. Debounced 200 ms; filters nodes and links with `cag ≤ N`. Not persisted.
- Row 3 **Family legend = filter**: one button per family present: glyph (shape in family colour) + family name + node count; tooltip lists member types. Click toggles all of its types hidden/shown (state on/partial `kismi`/off, `aria-pressed` true/mixed/false). Hover/focus highlights that family on the canvas. Hidden types persisted `aerona.agGizliTur`.

**Filtering pipeline.** link-group predicate & time → type hidden & time → drop dangling links → if focus: BFS up to N steps (world nodes are not expanded through, except the focus itself); if result > `kural('ARAYUZ.ag_odak_tavan', 10000)` nodes, reduce steps until ≤ cap or 1 step → otherwise (no focus, non-"all" link group) drop nodes without any link.
- **Default focus** (when no explicit focus and "Whole network" not chosen): the Atlas-selected record if present in the graph; else the highest-scoring non-world, non-hidden node with degree ≤ `kural('ARAYUZ.ag_oto_odak_bag', 50)` where score = degree×2 + g + (3 if son); fallback the best over-limit node. Degree excludes `icinde`/`dunyada` links.

**Rendering (2D, Canvas + d3-force + d3-zoom; `window.d3` global).**
- Node radius: world 16; else (son 6, other 3) + min(10, g×0.8 + √degree×1.4).
- Forces: link distance `icinde` 36, `rota` 240, `dunyada` 70, other 80; strength 0.8 / 0.05 / 0.22; charge −260 with focus, −150 without; center (W/2, H/2+30); collide r+5; cluster forces (if enabled) X/Y toward world centres on a circle of radius 0.32×min(W,H), strength 0.14 for nodes with a world.
- Position memory: node positions stored per id (`AG.konum`); kept across filter changes; cleared when the focus changes. If > 60% of nodes have known positions, simulation alpha 0.25 (no explosion). Zoom transform also remembered. A JSON signature of data+filters+viewport size skips all work when nothing changed (and resumes a paused simulation).
- Links: straight lines; colour by group (route/dunyada → route colour, icinde → muted, conflict, faith, other); alpha: route 0.85 (closed route 0.3), dunyada 0.16, icinde 0.24, conflict/faith 0.5, other 0.3; past links ×0.6 and dotted `[1,4]`; width 1 (route 2.4) divided by max(1, zoom×0.8). Hovered node's links: fg colour, 1.6 px, alpha 0.95, with mid-link label "(formerly) <link type>" when zoom > 0.6. When something is highlighted, other links dim to 0.12 (0.07 for path mode).
- Path ("How connected?") overlay: thick gold (faith colour) polyline 3 px with glow, through visible path nodes; path nodes get gold outline.
- Nodes: family shape via cached `Path2D`, filled in family colour; hollow shapes (ring) drawn as 30% fill + thick stroke; a 3 px background-coloured halo separates overlapping marks. World nodes: translucent disk (28%), ring, inner core (45% r). Dead nodes 45% alpha; non-highlighted nodes 18% alpha when a highlight is active. Hover/focus/selected get fg outline 2 px.
- Highlight priority: hovered node's neighbours > path nodes > legend-hovered family.
- Labels: candidates = important (hover/focus/selected/path), worlds, sons, all when zoom > 0.9, radius ≥ 9, or highlighted. Priority sort; greedy collision avoidance on a 48 px spatial grid (important labels always drawn); dimmed nodes get no label; fonts: world 700 15 px, son/focus 600 13 px, other 11 px "Alegreya Sans"; halo stroke in bg colour.
- Interactions: wheel/drag zoom-pan (scale 0.15–5); hover → pointer cursor + tooltip "**Name** <family glyph> Type · Family · N links"; click node → select + info card; click empty → close card (unless a path is shown); Shift+click a second node → find path; double-click node → open drawer (world → traveller's guide `rehber`; else by id prefix `v/o/y/t`). Double-click zoom disabled.
- Simulation is stopped when leaving the tab and resumed on return.

**Info card** `#agBilgi`: close "×"; eyebrow type icon + type name; name; "N links visible"; actions: worlds → "[book] Traveller's guide" + "[map] Its map"; others → "[deepen] Open its page"; "[network] Focus on its surroundings". Section "How are they connected? Shift+click another node or search:" with input "Second node…" (datalist); path result chain: breadcrumb of nodes with icons and arrows, ordered list "A **link label** B — description", "Connected in N steps." Not found: "No link within six steps; these two are in separate corners of the world." Link labels: `yaratti` created, `icinde` inside, `rota` inter-world route, `dunyada` in this world, else `G.K.BAG_ETIKET`.

**Empty/error states.** If `window.d3` missing the canvas is blank (no message). Path errors toast.

**Realtime.** Re-render on incremental refresh when entities, sons, links or worlds changed (signature check prevents redraw if nothing visible changed).

---

### Network 3D view (ag3d.js)

**Library.** three.js (from page importmap, v0.170) + `3d-force-graph@1.79.1` (with `three-render-objects@1.40.5`, `three-forcegraph@1.43.6`), `three-spritetext@1.10.0`, `d3-force-3d@3.0.5`, all loaded lazily from esm.sh (internet required). Load failure → toast "The 3D network library couldn't be loaded (internet connection required); switched back to 2D view." and mode reverts to 2D (persisted). No WebGL → toast "WebGL isn't enabled in this browser; the 3D network couldn't be drawn, switched back to 2D view."

**Same filtered nodes/links/focus as 2D.** Positions (x,y,z) remembered per id; cleared and "fit on first settle" when focus changes.

**Encoding.**
- Node object (THREE.Group): family 3D shape (box 1.6r, cone 1.35r×2.1r 3-sided, octahedron 1.3r, hex cylinder 1.1r×1.3r, torus 0.85r/0.34r, extruded star/plus depth 0.5r; default sphere) with Lambert material, emissive 0.18, opacity 0.95 (dead 0.45). World: 30% sphere + tilted ring (torus 1.35r) + 45% core. Highlight ring (RingGeometry 1.6r) billboarded every frame, colour `#ece6d8` or gold `#e8ad48` for path nodes. Sprite label above (size max(4, 0.9r), bold for worlds/sons, stroke in bg colour) visible for worlds, sons, focus, selected, r ≥ 9, path nodes; others only when highlighted/hovered.
- `nodeVal = r³`, `nodeRelSize 1`.
- Link colour: path → gold; hovered node's links `#a9dccb`; when highlighting, non-highlighted links `#262a31`; else same group colours as 2D; past links / closed routes / dunyada / icinde colours blended toward bg (`soldur`, average with `#0f1116`) since per-link opacity isn't available. Width: path 2.4, hovered 1.4, route 1.6, else 0 (hairline). Opacity 0.55. Directional particles: path 4 (gold `#ffd27a`, width 2.6), open routes 2 (`#bcd6f5`, 1.6); speed 0.006.
- Forces: same link distance/strength and charge as 2D; collide r×1.6+4; cluster X/Y toward a circle of radius max(320, √N×32) strength 0.3, Z → 0 strength 0.05.
- Cooldown 15 s if focus changed or < 50% positions known, else 4 s. Auto `zoomToFit(700 ms, 60 px)` after 1.4 s and again on engine stop for new layouts.

**Interactions.** Drag: rotate (orbit controls, damping); right-drag: pan; wheel: zoom; hover: highlight neighbours, tooltip "**Name** Type · Family · N links"; link hover tooltip = link label; click: select, info card, fly camera to node (distance 90 + 8r, 900 ms); double-click (two clicks < 350 ms on same node): open drawer; Shift+click: path; right-click node: set as focus; background click: deselect (unless path shown). Node drag enabled.

**Control strip** `#ag3Denetim`: "[search] Fit" (Sığdır, "Bring all nodes into view"); "[world] Rotate" toggle (auto-rotate speed 0.6, not persisted); "[network] Re-layout" (Yeniden yerleştir: clears all positions, reheat 15 s). Hint text: "drag: rotate · right-drag: pan · wheel: zoom · click: select · double-click: page · Shift+click: how connected · right-click: focus".

**Lifecycle.** Paused and hidden when switching to 2D or leaving the tab; resumed when signature unchanged on return. A ResizeObserver keeps size; a rAF loop billboards rings (runs forever once created).

---

### Network health / repair panel ("Bağlılık" / "Ağ onarımı")

Rendered in two places with identical content: the Network toolbar `<details>` (`#agSaglik`) and Settings → Game → Network repair (`agOnarimHtml()` wrapper `#agOnarim` with explanatory paragraph and `#agOnarimKutu`).

**Intro text (settings variant):** "[network] Network repair. The knowledge network's connectivity grows without forcing. **Repair loose ends** only creates links the data itself states: a located record to its location, an event to the place it struck, a prophecy to its whisperers and target, knowledge to its relic, a lonely record to its maker. Ended relationships are not deleted; they stay in the network and the counts as history. **Let Fate propose links** creates, for weakly connected records, only justified links supported by the chronicle and narrative, and names or closes (never deletes) vague "related" links. Both run automatically at the end of an age; tuned in World rules → **Network**."

**Data.** `GET /api/ag/saglik` → `{dugum, bag, gecmis_bag, ortalama_derece, medyan_derece, en_buyuk_pay, bilesen, yalitik, tek_bagli, ilgili, ilgili_aciklamasiz, zayif[{id:'v12', ad, derece}], oncelikli, gunluk[{zaman, tur, metin, baglar, bakilan}], …}`. Error → message text in each container. Loading: "Measuring…".

**Display.**
- Chips: "N nodes · M links (K past)"; "avg. X links (median Y)" (decimal comma — LANGUAGE-SPECIFIC); "main cluster P% · C clusters" (green `st-hazir` if P ≥ `kural('AG.ana_obek_iyi', 95)` else warning); "N isolated" (warning if > 0); "N single-link"; "N related · M without description" (warning if M > 0).
- "Weakest: <link> (degree), …".
- Actions:
  - "[✓] Repair loose ends" (`data-ag-onar`) → `POST /api/ag/onar` `{}` → `{toplam, ilgili_cevrilen, …}`; toast "N loose ends connected, M vague links named" or "No loose ends to repair"; re-render graph and panel.
  - "[Fate] Let Fate propose links" (primary, `data-ag-kader`) → `POST /api/ag/kader` `{}` (background job); toast "Fate is looking at the network; the links it creates and their reasons will appear in the feed". While job `ag:kader` runs: disabled with spinner "Fate is looking at the network…".
  - While running: "[chain] Stop" (danger, `data-ag-kader-dur`, "Finishes the current batch and stops") → `POST /api/ag/kader/durdur` `{}`; toast "Fate will finish its current batch and stop".
  - Otherwise: "[Fate] Full repair" (`data-ag-kader-tam`, confirm "Are you sure? Repair the whole network") → `POST /api/ag/kader` `{tam: true}`; toast "Fate started repairing the whole network; progress in the feed".
- If `oncelikli`: "**N** events, legends or traditions mentioned in the chronicle with unlinked participants are waiting for Fate."
- Rules note: "If Fate finds no evidence it creates no link; at most `kural('AG.oneri_tavan',3)` links per record per pass, with justification. It won't revisit a record for `kural('AG.tekrar_cag',10)` ages."
- "Recent repairs" `<details open>` list: "HH:MM <repair line>" or "No repair yet in this session; it happens automatically at the end of an age."

**Realtime.** Re-measured on `ag_onarim` events and when busy state changes (`/api/degisim`).

---

### Atlas tab ("Atlas") — entity wiki/browser

**Opened by.** Tab `data-tab="atlas"`. Also from Pantheon "In the world" type chips (`data-tab-go="atlas" data-filter="<type>"`) which preset the type filter.

**Data.** `GET /api/varliklar?durum=tum` → all entities `{id, ad, tur, alt_tur, aciklama, durum, konum_id, guc_seviyesi, sinif, cag, kaynak ('tanri'|'dunya'|'olumlu'|…), yaratan_id, dunya_id, favori, etiketler[], arsiv, arsiv_sebep, onem, kapak, …}`. Cached; re-fetched only when `G.S.surum` changed (incremental refresh patches the cache in place). Also cosmos data (stars, worlds incl. moons via `ana_id`, foreign gods) via `kozmosVeriTaze()`, and `G.S.ogullar`, `G.S.dunya`.

**Layout.** Two panes:
1. **Sidebar** `.atlas-side`:
   - Search `#atlasQ` "Search: name, type, description…" + match counter `#atlasSay`. Debounce 160 ms. Matches name + subtype + description (case-insensitive Turkish locale). Matches are highlighted with `<mark>`.
   - Filters: world select (`#atlasDunya`, permanently hidden — world filter moved to the top bar; dead control); Type `#atlasTur` "All types · N" + "Type · count" (counts respect every filter except type & search); Civilization tier `#atlasBasamak` (hidden unless any entity has a `basamak:N` tag) "All civilization tiers" / "N · tier name · count"; Status `#atlasDurum`: Living canon (yasayan = kanon+gerceklesti, default), Canon (kanon+olu+gerceklesti), Dead (olu), Realized (gerceklesti), Destroyed (yok_edildi), Rejected (reddedildi), All; Creator `#atlasYaratan`: All creators, each son, the creator god, "Mortals", "The world's flow"; Sort `#atlasSira`: By name, By importance (`onem` desc, then name), By age, By power, By type + direction toggle `#atlasYon` (up/down arrow, "Ascending order (flip)"/"Descending order (flip)").
   - Toolbar: segmented "[map] Tree | [chronicle] List" (persist `aerona.atlasMod`, default tree); favourites-only toggle (star icon, gold when on; not persisted); "[chronicle] History" toggle (`aerona.atlasTarih`; tooltip "History layer: also show records whose importance faded and descended into history"; badge with count of archived records); tree-only "Open" / "Close" all branches.
   - Tree/list container `#atlasTree` (role tree, focusable) + pager `#atlasSayfa`.
   - Keyboard hint: "↑ ↓ move · → open · ← close · Enter page".
2. **Main** `#atlasMain` (aria-live): the selected record's full page (same renderers as drawers: creator god page, foreign god page, son page, entity page) with a section nav. Empty: big icon "**Pick something** — Pick an entity, son, god or foreign god from the tree on the left; its page opens here." Missing: "**This record no longer exists** — It may have been deleted or rejected by Fate. Pick something else from the tree." Stale async results are discarded by a sequence number.

**Tree structure.**
- Single world (or world selected): "Pantheon" group (count = sons + 1; hidden when type/creator/favourite filter active) → creator god node (gold, "god" badge) + root sons (each son: rarity-coloured icon, stars ★×yildiz, "rebel" badge if `asi`, child sons nested by `ebeveyn_id`); then the world content: spatial roots (types whose `G.K.VARLIK_TURLERI[t].konum` is non-empty) as a location tree via `konum_id`, then one group per non-spatial type ("g:<type>@<world>"), then "Old and foreign gods" group.
- Multiple worlds and no world selected: root "Cosmos" (count = number of worlds) → Pantheon, "Foreign gods", Stars (`y:<id>`, gold) → their worlds (`w:<id>`), moons nested under their planet, worlds without a star at the end. Groups/worlds with zero matches are hidden when filtering.
- Entity row: caret (if children), type icon, name, status badge if not `kanon`, "history" badge if archived (tooltip reason), small image-generate button, child count. Dead/destroyed/rejected rows dimmed (`dead`). Rows that don't match but are ancestors of matches are styled `yol` (path).
- Expansion state: `aerona.atlasAcik` (array of keys: numeric entity ids, `g:<type>[@w]`, `o<id>`, plus `<key>-kapali` for default-open keys). Default-open keys: `g:panteon`, `g:yabanci`, all `w:`, `y:`, `k:` keys. While filtering, branches with matches auto-open (manual closes during a filter remembered in session only). Expanding/collapsing only inserts/removes that node's children container (no full redraw).
- Mouse: click caret or group header toggles; click row selects; double-click row toggles; "Generate image" mini-buttons don't select.
- Keyboard on tree: ↑/↓ select prev/next visible row (scroll into view); → expand; ← collapse or jump to parent; Enter opens the drawer for the selection (`t` → god, `yt<id>` → foreign god, `o<id>` → son, number → entity).

**List mode.** Table "Name | Class | Age", sortable by clicking headers (same column toggles direction; ▲/▼). Row: type icon + name (highlighted) + image mini-button; sub-line "Type · subtype · location name"; class badge (`sinif`, default common); "ÇN". Page size 40; pager "[◀] page / pages · N records [▶]". Empty: "No matches." Tree empty: "No matches. Loosen the search or filters."

**Selection.** `G.atlasSel`: number (entity), `'t'`, `'o<id>'`, `'yt<id>'`. If invalid after refresh → first match (or none). Also used by the Network default focus.

**Realtime.** On incremental refresh, the tree is patched when the data signature changes; detail re-rendered only if the selected record (or something located in it) changed; image completion re-renders detail.

---

### Languages tab ("Diller": dictionary, language tree, knowledge tree)

**Opened by.** Tab `data-tab="sozluk"` (label "Languages", tooltip "Languages, dictionary and knowledge tree").

**Data** (parallel): `GET /api/sozluk` → `[{id, ad, alt_tur, aciklama, kapak, konusanlar[{id,ad,tur}], kelimeler[{id, kelime, tur, anlam, ornek, koken, cag, ekleyen_ad}]}]`; `GET /api/bilgiler` → `[{id, ad, aciklama, dal, seviye, yayginlik, cag, temeller[{id,ad}], bilenler[{id,ad,gecmis?}], yapan}]`; `GET /api/dil-agaci` → `{diller[{id, ad, alt_tur, yazi, kelime, konusan, ust_id, ornek_adlar[]}], akrabalik[{a, b, ortak[{a, b, anlam_a, anlam_b}]}], yazi_turleri{key: description}}`. If a world is selected, languages and knowledge are filtered to that world (entity→world map).

**Header.** "[dictionary] Languages and knowledge"; subtitle "(In **World**) N languages, M words, K knowledge. As sons and mortals coin words, languages grow, split and become kin; new names are born from these words." Segmented view switch (persist `aerona.dilGorunum`, default `sozluk`): "Dictionary and translation", "Language tree", "Knowledge tree". Link "[book] The world's book" → `/kitap` (new tab).

**Dictionary view.**
- Empty: "No language yet. <Gate> sons can create languages; peoples and factions can give birth to their own languages. (World rules → … → NADIRLIK_KAPI.tur_dil)". Gate text from the type's rarity tier: "All" (lowest tier), "Only <Mythic>" (top tier), "<Rarity> and above", or "Some" if unknown.
- Left list of languages: button with name, word count, "subtype · script name", speakers list or "no speakers". Selection `G.sozlukSec` (memory only, default first).
- Right: search `#sozQ` "Search all languages (of this world): word, meaning, origin…" + result count; button "[deepen] <Language> page" (opens entity drawer). Debounce 180 ms. When searching, searches across all languages and shows "N results for “q” in all languages."; otherwise shows chips (script chip, "N words", "N speakers", "Names born in this language" + example names de-duplicated) and the language description, then the **translation box**.
- Word table: Word (+ language when searching) | Type | Meaning (+ italic example) | Origin | Coined by ("Name · ÇN", or just "ÇN" when coiner unknown or literally "#null"). Shows first `G.sozlukLimit` (150) rows; button "N more words" adds 300. Empty row: "No matching word."
- Script chip: "[script] Script name" (tooltip from `yazi_turleri`) or muted "unwritten" (tooltip "This language has no script yet").

**Translation box** (per language, state kept in memory per language id): title "[translate] Translate into <Language>  missing words are derived in the language's sound system and added to the dictionary"; textarea (2 rows, max 300, placeholder sample sentence); button "[translate] Translate" (Enter submits, Shift+Enter newline). Request `POST /api/cevir` `{dil_id, metin}` → `{ceviri, okunus, kelime_kelime[{kelime, anlam}], yeni_kelimeler[{kelime, anlam, koken}], not}`. While pending: textarea and button disabled ("[spinner] Translating"), indeterminate bar, "The scribe is leafing through <Language>'s dictionary… N s" (live seconds) + "· average of recent translations N s" if a step named like "çeviri" exists in `/api/olcum` (LANGUAGE-SPECIFIC match). Result: quoted source, translation (large), "/pronunciation/", word-by-word chips, "N new words added to the dictionary" chips (tooltip origin), note. Error: red text. After completion the tab reloads (new words) and toasts "N new words were added to <Language>'s dictionary".

**Language tree view.** Families (roots with children) as nested `<ul>` trees and "Languages without relatives" as a flat row. Card: name, subtype, script chip, word count chip, speaker count chip. Selected card (default first family root) → side panel: "Selected language", name, "subtype · born from <parent> (in another world)", chips, script description, "Names born in this language" chips, cognate blocks per parent/child: "[↑] Ancestor language X / [↓] Daughter language X, shared roots N" + rows "word (meaning) → word (meaning)" or "No shared root found; the languages drifted far apart." If none: "This language has no ancestor or daughter. Pick a language with relatives to see shared roots here." Actions: "[dictionary] Open its dictionary" (switches to dictionary view with that language, scrolls to top), "[deepen] Page". Empty: "No language yet in World." / "No language yet."

**Knowledge tree view.** "[tech] Knowledge tree  N knowledge · spreads by trade, alliance and conquest". Grouped by branch (`G.K.BILGI_DALLARI[d] = {ad, etki}`), earthly branches first, then "Cosmic knowledge — prerequisites of inter-world travel" (branches `gokyuzu_seyri, gemi_yapimi, kapi_bilimi, yol_biliciligi, bosluk_yasami`); unknown cosmic branches listed as locked chips "[lock] Branch · not yet known". Knowledge card (`data-v` opens page): name + level badge "Sv N" coloured by level (1–2 common, 3–4 uncommon, 5–6 rare, 7–8 epic, 9–10 legendary), "→ built on A, B", knowers (people list) or "no knower left", "ÇN · maker". Empty: "No knowledge yet. <Gate> sons can inspire knowledge; peoples develop their own knowledge. (rule path)".

**Realtime.** Re-render on incremental refresh when entities changed.

---

### Gallery tab ("Galeri")

**Data.** `GET /api/gorseller` → `[{id, dosya, baslik, kapak, hedef_tip ('v'|'o'|'y'|'t'|'d'), hedef_id, hedef_ad, hedef_tur, hedef_dunya}]` newest first; `GET /api/galeri/eksik` → important records without an image `[{t:'v', id, ad, tur, onem, prompt|gorsel_prompt, dunya_id}]` (optional; section hidden on error); world map if a world is selected.

**Layout.**
- Header "[gallery] Gallery"; subtitle "All images you produce are stored permanently in the `data/gorseller` folder and the database. You can upload from a son's, entity's, god's or foreign god's page, drag and drop, or paste from the clipboard." + "Showing images of **World**."
- Filter chips (`G.galeriFiltre`, memory): "All N", "Sons", "Entities", "Foreign gods", "God", "World" (each with count; zero-count hidden unless selected). Button "[upload] Upload for the god or a world" → opens the god drawer.
- **Missing images** `<details>` (open state memory): "[gallery] Important records missing an image  (top N when list is capped at `kural('SUNUCU.galeri_eksik',40)`) · copy the prompt, generate the image, drop it here". Rows: type tag + name link + importance chip; prompt text or "No image prompt yet; you can have one written from the record's page."; buttons "[copy] Copy prompt", "[deepen] Open its page"; drop-zone uploader "Drop or choose the image". Shows 12, "+ N more records (M left)" adds 12.
- **Wall**: figures (first 60, "+ N more images" adds 60, counter "n / N images"): thumbnail (320 px, lazy) opening the lightbox over the whole filtered list (`data-lb="wall:i"`), "cover" badge if `kapak`; caption with type tag + target link (entity/son/foreign god/god/world), title (only if not a filename-derived id). Records of type `dis` (outer beings) get a blur class `dis-bulanik`.
- World filtering: entity by its world, son by son's world, world image by its id, foreign god by `hedef_dunya`; god images always shown.
- Empty: "No images yet. Open a card's or entity's page, copy the prompt, generate the image and upload it back here."

**Realtime.** Not re-rendered by incremental refresh (`galeri: false`); re-rendered on `gorsel_bitti` success.

---

### Pantheon-page blocks in hedefler.js (Goals, Council, This age, First ages, Card comparison)

`renderPanteon()` (Pantheon tab, default tab) lives in this file. Fetches `GET /api/konseyler`, `GET /api/hedefler`, opportunities `GET /api/firsatlar`. Page order: First-ages guide → God panel (other module) → This-age box → "[son] Pantheon N sons · click a card: give orders, bless, add a star, ascend" with son cards (sorted rarity desc, stars desc, id) and the card comparison `<details>` (≥ 2 sons) → Goals → Council → Open stories (with "Open a new story" form) → Brotherhood matrix → "In the world" type count chips (click → Atlas filtered) → Cosmology prose + "Naming language" prose. (Cards, god panel, threads, matrix are specified in Part 3, Pantheon tab components.)

**First ages guide** (`ilkAdimlarHtml`): hidden if `aerona.rehberKapali === true`, or if unset and age > 3, or all steps done and age > 3. Title "[help] First ages  n/6 steps"; button "[✓] Got it, hide" (persist `rehberKapali=true`, toast "Guide hidden; you can bring it back from Settings → Appearance"). Steps (done = `aerona.adim.<k>` or condition): kart "Open one of your sons' cards: see who he is, his powers and plan." (set on opening a son drawer); emir "Give a son an order or bless him." (any son has `emir`); vahiy "Create something with your own hand by revelation." (set after a revelation); dualar "Look at the Prayers tab: your sons and mortals pray to you." (set on visiting tab); harita "See the world's geography on the Map." (visit); cag "Complete the age: sons, mortals, the world and Fate act in turn." (age > 1). Footer "Press ? for shortcuts. ⌘K to search everything."

**This age box** (`buCagHtml`): collapsible per age (`aerona.yapilacakKapali` = age number when hidden → shows a single button "[play] This age: to-dos and opportunities (N)"; "Hide for this age" / reopen sets 0). Title "[play] Age N  to-dos and what you can do this age". Left "To-do": "N prayers await an answer [Go to prayers]"; "Age N was interrupted; it can be completed from where it left off." or "N sons haven't acted this age yet. Click their card, give orders; then complete the age."; "N essence can be spent: reveal (cost), summon a new son (cost), convene council (cost), awaken peoples (cost)" or "; nothing affordable for now, it refills at the end of the age"; "N unread notifications [Notifications]". Right "What you can do this age": opportunity list from `/api/firsatlar` `genel[]` (server lines that duplicate the to-dos are filtered by Turkish regexes — LANGUAGE-SPECIFIC hack; have the server not send them) or "Opportunity list couldn't be fetched right now." / "No notable tension in the world right now." Opportunity formatting: an ALL-CAPS leading heading ("HAYAT ÜFLE: …") is converted to sentence case and bolded; other shouting words of ≥ 4 caps are lower-cased (LANGUAGE-SPECIFIC case handling with `tr` locale; better to send structured `{title, body}`). Actions: "[revelation] Reveal (cost `G.K.COSTS.vahiy`)" opens the revelation drawer; awaken row: number input (default 2, min 1; tooltip "Each `kural('UYANIS.tavan',3)` peoples are one batch (UYANIS.tavan); the cost is charged per batch"), world select when multi-world and `G.K.UYANDIR_DUNYA` ("Let Fate choose" or a world, default = selected world), button "[people] Awaken peoples (cost/batch)" → `act(POST /api/uyandir {sayi, dunya_id?})` toast "Peoples are awakening…"; tooltip "Awaken new peoples on empty lands: each is born with language, settlement, resource, knowledge, tradition and faith." + world sentence; "[ledger] Action ledger" opens the action-log drawer. Cost-gated buttons disabled with reason "N essence needed; you have M." or "A job is running; it opens when it ends." Opportunities cached per age + world version (`firsatBayat`).

**Goals ("Amaçların")** (`hedefBlokHtml`, data `GET /api/hedefler` → `{senaryolar[{anahtar, ad, aciklama, puan, gecmis[{id, durum, baslangic_cag, bitis_cag, sonuc}]}], suren[{id, anahtar, ad, baslangic_cag, yuzde, metin, basarisiz}], basarimlar[{anahtar, ad, aciklama, puan, kazanildi, cag}], puan{toplam, dokum{nufus, cesitlilik, diller, dunyalar, medeniyet, kiyamet, basarim, senaryo}}, puan_gecmisi[{cag, toplam}]}`):
- Title "[fame] Your goals  optional: set yourself a goal; progress is measured automatically at the end of each age".
- Score card: "Score" + big mono total + sparkline (220×44 SVG, legendary-gold stroke, only if ≥ 2 points) + breakdown "population +N", "diversity", "languages", "worlds", "civilization", "apocalypse" (negative in red), "achievements", "scenarios".
- Running scenarios: card "**Name**  since Age N  [Abandon]" (form `POST /api/senaryolar/<id>/birak`, two-click confirm "Are you sure? Abandon", toast "Scenario abandoned"), progress bar `yuzde%`, status text (red if `basarisiz`). Empty: "You have no running goal. You can pick one below."
- `<details>` "[+] Pick a new goal": each scenario: name, chip "+points", description, history "completed/failed/abandoned/running (ÇA–B)"; button "[play] Start" (form `POST /api/senaryolar` with `anahtar`, toast "You set a new goal"; disabled "Already running").
- `<details>` "[fame] Achievements  earned/total": grid; earned show "ÇN", locked show lock icon and "+points"; tooltip description.

**Council of the Gods** (`konseyBlokHtml`): title "[council] Council of the Gods  sons debate an agenda and vote on a motion; convenes automatically every N ages (frequency changes in Settings → World)" or "doesn't convene automatically, only when you call it". N = `dunya.konsey_sikligi ?? kural('KONSEY.siklik_varsayilan',4)`. Input "Agenda: “How can the doomsday clock be stopped?” (leave blank and Fate picks)" (max 200, Enter submits) + gold button "[council] Convene council (cost)" → `act(POST /api/konsey {konu})` toast "Council is convening; the debate is in the live feed"; clears input. Disabled reasons: busy; "The council needs at least two awake sons" (active or sleeping); insufficient essence (cost `bedel('konsey')`). List of past councils (first `KONSEY_ILK`, toggle "Show all councils (N more)" / "Show less"; first expanded). Empty: "The council has never convened. Write an agenda and call the brothers together."

**Card comparison ("Kartları karşılaştır")** (KARSI): `<details>` "[network] Compare cards  pick 2–3 sons: power, passions, reputation and relationships side by side". Son toggle chips (rarity colour; disabled "At most three sons" when 3 selected). Selection persisted `aerona.karsi` (array of son ids, pruned of missing sons); click handled globally in app.js (re-renders only `#karsiKutu`). < 2 selected: "Pick at least two sons to compare." Table (columns = sons, horizontally scrollable): header (avatar 40, name, title, rarity name + stars), rows: Level "Sv N"; Health (bar vs `can_max`, danger colour); Essence (vs `oz_max`, accent); Existence (vs 100, default `kural('CAGIRMA.varlik_baslangic',60)`); Faith; Fame; group "Stats" (each `G.K.SON_STATS` 0–100 bar in rarity colour); group "Passions" (each `G.K.TUTKULAR` bar, warn colour; no "best" highlight); group "How he sees his father": Reputation label chip (from `itibar` JSON or `kart.itibar`), Love, Fear, Forgottenness bars; group "Relationships": Closest (link + "+value" green), Rival (link + value red), "Towards the selected" (relation values between selected sons, signed), "Last word" (italic quote). Numeric rows highlight the maximum cell (`en`) when > 0.

---

### Bookmarks (core/imler.js)

Local-only bookmarks for sons (`o`), ages (`c`) and chronicle entries (`kr`, id `"<age>.<entryId>"`). Stored in `aerona.imler` as `[{t, id, ad (≤120 chars), zaman}]`, newest first, max 200. Entity favourites are server-side (`/api/varliklar/:id/favori`) and listed together with these in the "Your records" drawer (Part 2, Records drawer).
- Button `imDugme(t, id, ad)`: "[bookmark] Bookmark" (ghost, title "Add bookmark") / "[bookmark] Bookmarked" (gold, title "Remove from bookmarks"); `aria-pressed`. Global click handler toggles and updates the button in place; toast "Added to bookmarks" / "Bookmark removed". Used in Chronicle age headers, current age header and search result entries.

### Link-target resolver (core/hedef.js)

Pure helpers: `hedefAttr(tip, id)` returns the click attribute for a typed endpoint: `t` → `data-tanri-ac`; `v` → `data-v`; `o` → `data-o`; `y` → `data-yabanci`; `d` → `data-rehber`; anything else / invalid id → none (rendered as plain text, to avoid opening a same-id record of another type). `aramaHedefi(result)` maps a search/palette result to an action: `v/o/y` → open drawer, `t` → god drawer, `d` → focus world in Cosmos, `ys` → focus star; else null.

---

### Persisted UI state (Part 5 screens)

| key | meaning | default |
|---|---|---|
| `aerona.tab` | last tab (also URL hash) | panteon |
| `aerona.canliAcik` | live feed open | `innerWidth > 1100` |
| `aerona.akisSes` / `aerona.akisSessiz` | feed tones on / muted categories | false / [] |
| `aerona.ortamSes` | ambient drone | false |
| `aerona.agMod` | network 2D/3D | `2b` |
| `aerona.agDerinlik` | focus radius | 2 |
| `aerona.agGizliTur` | hidden node types | [] |
| `aerona.agBag` | link group | `hepsi` |
| `aerona.agHepsi` | "whole network" chosen | false |
| `aerona.agKume` | cluster by world | false |
| `aerona.atlasMod` / `atlasDurum` / `atlasSira` / `atlasTarih` / `atlasAcik` | Atlas tree/list, status filter, sort, history layer, expanded keys | agac / yasayan / ad / false / [] |
| `aerona.dilGorunum` | Languages sub-view | sozluk |
| `aerona.karsi` | compared son ids | [] |
| `aerona.imler` | bookmarks | [] |
| `aerona.rehberKapali`, `aerona.adim.<k>` | first-ages guide hidden / step done | null / false |
| `aerona.yapilacakKapali` | age for which "This age" box is hidden | 0 |

Not persisted (memory only, lost on reload): Chronicle search/type filters/open ages/narrator choice/compare pair; network focus, time slider, path; Atlas search, type, creator, favourite filter, sort direction, page, selection; Languages selected language/search/limit, translations; Gallery filter/page.

---


---

## Part 6 — Branding, recurring UI defects, design-token inventory

This part is the input for the new design system. "Current branding" captures what to keep; "Recurring UI defects" catalogues every class of layout/padding/overlap/icon/text-collision/inconsistency problem found in `style.css`, the views, the audit log (`DENETIM.md`) and the commit history, each with a structural prevention rule; "Design-token inventory" counts what exists so it can be consolidated. The last section gathers the per-screen defect evidence found while specifying Parts 2–5.

### Current branding

Sources read in full: `public/style.css` (2297 lines, about 1820 rules), `public/stil.html` (style guide, served at `/stil.html` and linked from the footer as "Style guide (Stil rehberi)"), `public/icons.js`, `public/marka.js`, `public/etiket.js`, `public/favicon.svg`, `public/index.html` (head and shell), `README.md`. I also searched `DENETIM.md` and the git log for UI work. Line numbers below refer to `public/style.css` unless another file is named.

#### Product name and wordmark
- **Name:** "Weavers of the Void". `<title>Weavers of the Void</title>`, `lang="tr"`. The style guide's title is "Weavers of the Void Stil Rehberi". The world name is shown separately and changes per save, for example "Dazbuş" or "Orvael".
- **Header wordmark (`.marka-ad`, line 195):** the text "WEAVERS OF THE VOID" in JetBrains Mono 700 at `--fs-2xs` (10.5px), uppercase, letter-spacing `.32em`, colour `--r-efsanevi` (legendary gold #e8ad48), 3px bottom margin. It sits above the **world name** (`.world-name`, line 196): Cormorant Garamond 700, `--fs-2xl` (26px), letter-spacing `.02em`, one line with ellipsis. Under that is the **epoch line** (`.epoch`, line 197; redefined at line 1925). It shows the epoch, climate, star of the epoch and doomsday clock in muted `--fs-sm`, and wraps onto two lines.
- **Footer wordmark (`.ab-marka`, line 217):** logo plus "WEAVERS OF THE VOID" in mono, uppercase, letter-spacing `.2em`, colour `--fg-2`.
- **Brand line (stil.html "Principles (İlkeler)"):** "Night-ink ground, bone-coloured text, copper-verdigris accent. Rarity colours carry the same meaning everywhere: card frame, seal, star, entity class. Status colours (good, warning, danger) are separate from the accent and are always paired with an icon or text. Headings Cormorant Garamond, body Alegreya Sans, numbers and code JetBrains Mono."

#### Logo construction (`marka.js` `LOGO_SVG(size = 34)`)
- 64×64 viewBox with `class="logo"`, `role="img"` and `aria-label="Weavers of the Void"`.
- **Gradient `lg-aerona`:** linear, top-left to bottom-right (x1 0, y1 0 → x2 1, y2 1), from **#e8ad48** (legendary gold) to **#7dbba8** (verdigris accent). The logo is literally a blend of the two brand colours.
- **Layers, back to front:**
  1. An outer ring: circle r=29, gradient stroke, width 2, no fill.
  2. An inner dotted ring: circle r=23, gradient stroke, width 1, `stroke-dasharray 1.5 3.5`, opacity .8.
  3. A four-pointed star or compass rose filled with the gradient at opacity .95. Its tips are at N (32,6), E (58,32), S (32,58) and W (6,32), with a narrow waist at 27/37.
  4. A horizontal almond or vesica ("eye"): `M20 32 Q32 22 44 32 Q32 42 20 32`, filled #111318. It punches a dark eye shape through the star's centre.
  5. A pupil: circle r=3.6 filled with the gradient.
- **Reading:** a gilded four-pointed star inside a ring, with an open eye at its heart (the all-seeing creator god).
- **Sizes and effects in use:**
  - Header: 34px, `drop-shadow(0 0 10px gold 30%)` (line 193). On phones it shrinks to 30px (line 1876) and is hidden when the header compacts on scroll (line 1853).
  - Genesis screen: `drop-shadow 22px gold 45%` (line 928).
  - Style guide: 64px.
  - Footer.
- **Favicon (`favicon.svg`):** the same mark in an app-icon tile:
  - A rounded square (rx 14) filled #111318.
  - A ring r=27 with stroke width 3. There is no dotted inner ring.
  - A thicker star with tips at 8/56.
  - The same eye, and a pupil of r=4.
  - The gradient id is `g`.
- `<meta name="theme-color" content="#111318">`.
  - **Mismatch:** #111318 is not a token. The page ground `--bg` is #0f1116.

#### Colour palette (`:root`, lines 22–109; 135 custom properties)
The app is dark-only (`color-scheme: dark`, line 108). There is no light theme and no `prefers-color-scheme` query. The one theme variant is **high contrast** (`:root[data-kontrast]`, lines 111–118). Settings → Appearance toggles it, and it is persisted in localStorage under `gorunum`.

| Token | Hex (default) | High contrast | Role |
|---|---|---|---|
| `--bg` | #0f1116 | #07080b | Page ground, drawer panel, sticky bars |
| `--bg-2` | #13161d | #0b0d11 | Recessed areas: header gradient end, footer, Atlas sidebar, kozmos sidebar, chat log, prompt box |
| `--panel` | #171a22 | #101218 | Default surface: cards, panel boxes, live column |
| `--panel-2` | #1e222c | #171a22 | Raised controls: buttons, inputs, chips, avatars |
| `--panel-3` | #262b37 | #222733 | Hover and selected fills, meter tracks |
| `--line` | #2a2f3b | #4b5366 | Hairline borders, dividers |
| `--line-2` | #363c4a | #67708a | Control borders, scrollbar thumb, empty-state icon colour |
| `--fg` | #ece6d8 | #ffffff | Primary text ("bone") |
| `--fg-2` | #cfc8b8 | #f1ece0 | Secondary text |
| `--muted` | #979387 | #cdc8ba | Tertiary text, labels, inactive icons |
| `--accent` | #7dbba8 | #8fe0c8 | Verdigris accent: primary button, focus ring, active tab underline, essence number, links, progress bars |
| `--accent-ink` | #0b1a15 | — | Text on accent fills |
| `--danger` | #dc735d | #ff8a70 | Destructive actions, death, errors, curses |
| `--good` | #92c26d | #b0e08a | Success, birth, alliance, "ready", tool success ✓ |
| `--warn` | #dcb45c | #f2cc6a | Warnings, open story threads, asleep, system lines, the `.pill` count badge |
| `--scrim` | rgba(5,6,9,.62) | — | Drawer backdrop |
| `--yuzer-bg` | color-mix(panel 90%, transparent) | `--panel` | Floating translucent panels over canvases (`.yuzer`) |
| `--halka` | 0 0 0 2px accent 55% | 0 0 0 3px accent | Focus ring (box-shadow form) |
| `--harita-yerlesim` | #e0c06a | — | Settlement glyph on the map (read by JS only) |

**Rarity scale (son cards, seals, stars, class badges, `.c-*` classes, `.card[data-r]` → `--rc`):**

| Turkish key | English | Token | Hex |
|---|---|---|---|
| yaygın | Common | `--r-yaygin` | #9097a0 (slate grey) |
| seçkin | Uncommon | `--r-seckin` | #7fc489 (green) |
| nadir | Rare | `--r-nadir` | #6fa0e6 (blue) |
| destansı | Epic | `--r-destansi` | #b48ae6 (violet) |
| efsanevi | Legendary | `--r-efsanevi` | #e8ad48 (gold). It doubles as the general "divine and gold" colour for the creator, sayings, legends, the wordmark and the `.c-altin` class. |
| mitik | Mythic | `--r-mitik` | #f07aa0 (pink). A Mythic card also gets an animated conic-gradient border (line 502). It cycles mitik → efsanevi → nadir → destansı over 6s, driven by `@property --a`. |

The same six hexes are duplicated in JS as `RRENK` (`core/bilesen.js:8`) and as the `r` map in stil.html.

**Categorical data palette (lines 25–26, validated dark-ground palette; fixed order, never cycled):**
- `--seri-1` #3987e5 blue
- `--seri-2` #d95926 orange
- `--seri-3` #199e70 teal
- `--seri-4` #c98500 amber
- `--seri-5` #d55181 magenta
- `--seri-6` #008300 green
- `--seri-7` #9085e9 lavender
- `--seri-8` #e66767 red (unused in CSS)
- `--seri-diger` #898781 "other" grey

`views/grafik.js SERI` mirrors these.

**Record families (`--aile-*`):** the seven entity families defined in `core/bilesen.js AILELER`. Each family carries a marker shape for the network graph and legends. A "-yazi" text tone mixes the family colour into `--fg` (50–62%) for legibility.

| Family | Colour | Shape | Types |
|---|---|---|---|
| Places (yer) | seri-1 | square | dunya, bolge, yer, yerlesim, gok |
| Communities and persons (topluluk) | seri-2 | circle | halk, olumlu, tarikat, hizip, ordu |
| Objects and knowledge (nesne) | seri-3 | triangle | esya, teknoloji, yapit, kaynak, arac |
| Gods (tanri) | seri-4 | diamond | ogul, tanri, yabanci, dis |
| Culture and belief (kultur) | seri-5 | hexagon | efsane, gelenek, kehanet, dil, eser, kanun, yasa |
| Living things and spirits (canli) | seri-6 | ring | tur, ruh |
| Events (olay) | seri-7 | star | olay |
| Other | seri-diger | plus | — |

**Type colours:** `--tur-<type>` aliases the family's "-yazi" tone (29 types). The `.t-<type>` classes use them (lines 373–397). Exception: `.t-ogul` uses `--r-efsanevi` instead of `--tur-ogul`.

**Status and other semantic colour assignments (all in rules, not tokens):**
- **Son status chips:**
  - `st-hazir` / `v-parlak` (ready / vivid) → good
  - `st-uykuda` / `v-solgun` (asleep / fading) → warn
  - `st-surgun`, `st-zincir`, `v-unutuluyor` (exiled, chained, being forgotten) → danger
  - `st-olu` (dead) → muted text on a 10% danger tint
- **Atlas tree status tag (`.tree .dur`):** 9px red uppercase. Variant `.c-altin` is gold and `.tarihte` (historical) is muted.
- **Chronicle entry icon colours by kind:**
  - Lines 779–785: kader, olum, lanet, isyan, tanri_savasi, inkar → danger; soz → accent; tanri, emir, yildiz, yukselis → gold; dogum, ahit → good; meydan, entrika, dunya → warn; ruya, varolus → epic violet.
  - Lines 1260–1264: tanri_isareti (the creator's sign) gets a gold gradient band and italic display text.
  - Lines 1332–1334: yabanci_tanri → mythic; kozmik → epic; yasak → warn.
- **Live-feed world-event categories (`--akc`, lines 1495–1503):**
  - voyage → rare blue
  - gate → #c9b896
  - leak → epic violet
  - war → #ff7a5c
  - disaster → gold
  - sky → #a8b4ff
  - life → good
  - civilisation → #e0c06a
  - world → warn
  - Four of these are raw hexes.
- **Live-feed row types (`.ev.*`, lines 899–921):**
  - who → accent
  - tool → rare blue
  - result ok → good
  - result error → danger
  - think → muted italic
  - speech → gold display italic
  - system → warn
  - stage → accent caps
  - council → epic
  - sign → gold
- **Climate (lines 955–957):** dry/hot → warn; ice → #8fc3e6; rain → rare.
- **Social classes (lines 938–944):** scribe, artisan, priest, merchant, warrior and farmer take seri-1…6; other takes seri-diger.
- **Relations and votes:** positive → good, negative → danger, abstain → line-2.
- **Map note colours (JS `NOT_RENK`, harita.js:93):** gold, red, blue, green and purple, written as raw hexes copied from the tokens.

**Ground gradients (hard-coded):**
- map: #0d1520 → #070a0f
- kozmos scene: #121626 → #07080d
- genesis: #1d2230 → bg
- card reveal: rarity colour mixed with #05060a
- Outer Being portrait: #000/#07050c/#140d1f

#### Typography
- **Loaded from Google Fonts** (index.html and, again, stil.html, `display=swap`):
  - Cormorant Garamond 500/600/700 plus italic 500
  - Alegreya Sans 400/500/700 plus italic 400
  - JetBrains Mono 400/600
- **Display (`--f-display`, Cormorant Garamond → Iowan Old Style → Georgia; 52 uses):**
  - Names and titles: world name, god name (`.god-name` 4xl), drawer and entity name (`.d-name` 4xl), card name (2xl, one line), epoch name (3xl), language names, council topic, foreign-god names.
  - Long-form narrative: `.age-prose` at fs-lg/1.7 with a 2.8em accent-coloured drop cap.
  - Quotes and sayings: `.saying`, the son's chat bubble in italic, `.bakis-metin` (a partisan narrator's quote with curly quotes coloured by the people's hue).
  - Genesis `h1`: 46px literal.
  - Dead-portrait cross: 96px literal.
- **Body (`--f-body`, Alegreya Sans → Segoe UI → system-ui):** all UI text; `body` is fs-md/1.5.
- **Mono (`--f-mono`, JetBrains Mono, tabular numbers):** numbers (essence, costs, meters, stat values, matrix), `.tag`, `.rarity`, `.cls` badges (2xs, uppercase), kbd, timestamps, wordmark, prompt boxes.
- **Scale (≈1.2 ratio, every size multiplied by `--yazi`).** Settings offers Small 0.9, Normal 1, Large 1.15 and Very large 1.3.

| Token | Size | Role per the style guide | Uses |
|---|---|---|---|
| `--fs-2xs` | 10.5px | Overline / eyebrow (caps), tags, counts | 38 |
| `--fs-xs` | 11.5px | Numbers, metadata | 60 |
| `--fs-sm` | 12.5px | Small text, chips, buttons `.sm` | 97 |
| `--fs-md` | 14.5px | Body | 26 |
| `--fs-lg` | 17px | Narrative / prose | 24 |
| `--fs-xl` | 21px | Sub-heading (`.block > h3`, `.d-sec > h3`) | 11 |
| `--fs-2xl` | 26px | Card name | 7 |
| `--fs-3xl` | 32px | Page title `h2.sec` | 6 |
| `--fs-4xl` | 40px | World or god name | 2 |

- **Other type tokens:**
  - Line-height: tight 1.1, snug 1.3, base 1.5, prose 1.65.
  - `--ls-caps` .12em.
  - Reading measure: `--okuma-max` 72ch.
- **Weights used:** 400 (8), 500 (12), 600 (52), 700 (50).
- **Heading hierarchy (stil.html "Layout rules"):**
  - page `h2.sec` fs-3xl
  - section `.block > h3` fs-xl display
  - box `.panel-box h4` fs-md body 700
  - `.alt-baslik` fs-md 700
  - `.eyebrow` fs-2xs caps 700

#### Spacing, radius, shadow, size tokens
- **Spacing (4px base):** `--sp-1` 4, `--sp-2` 8, `--sp-3` 12, `--sp-4` 16, `--sp-5` 20, `--sp-6` 24, `--sp-8` 32, `--sp-10` 40.
  - Usage counts: sp-2 282, sp-3 208, sp-4 106, sp-1 65, sp-5 34, sp-6 18, sp-8 8, sp-10 7.
  - Rules from the guide: between sections sp-8; between detail sections sp-6; inside a box sp-4; stacked items `.yigin` sp-3; inline `.actions` sp-2.
- **Radius:** `--rad-sm` 4 (tags), `--rad-md` 7 (controls), `--rad-lg` 10 (boxes, cards), `--rad-xl` 14 (large surfaces: god panel, son card, hero), `--rad-pill` 999 (chips, filter pills).
- **Shadows:**
  - `--sh-1`: 0 1px 0 rgba(0,0,0,.3), hairline (used once).
  - `--sh-2`: 0 12px 32px -16px rgba(0,0,0,.75), floating (10 uses).
  - `--sh-3`: 0 24px 60px -24px rgba(0,0,0,.85), modal or drawer (5 uses).
  - Cards add a rarity-tinted glow on hover.
- **Control heights:** `--h-sm` 28 (toolbars, inline actions), `--h-md` 34 (default), `--h-lg` 44 (one big call to action), `--h-chip` 24, `--h-tag` 20, `--h-hap` 26 (filter, section-nav and feed-filter pills).
- **Icon sizes:** `--ic-sm` 13, `--ic-md` 16, `--ic-lg` 20, `--ic-xl` 28.
- **Layout widths:**
  - `--live-w` 360 (live feed column)
  - `--yan-w` 320 (Atlas and Languages sidebar; 290 at ≤1280px, 270 at ≤960px)
  - `--drawer-w` 820
  - son-card grid `minmax(290px,1fr)`
  - card art 200px tall
- **Dead legacy aliases (defined, never used):** `--btn-h`, `--btn-h-sm`, `--btn-h-lg`, `--input-h`.

#### Iconography (`icons.js`)
- **Style:** 24×24 viewBox, `fill="none"`, `stroke="currentColor"`, stroke-width **1.6**, round caps and joins, `aria-hidden`. The SVG is created by `ic(key, cls)` with class `ic` (`.ic` 16px, `.lg` 20px, `.xl` 28px). An unknown key silently falls back to `sistem`. The style guide says: "24×24, 1.6 stroke, currentColor. Every entity type, stat, passion, resource and action has its own sign."
- **Count:** 110 named icons (`ICON_KEYS`), plus the alias `yabanci = tanri`.
- **Entity types** (Atlas tree, tags, network legend, search palette, drawer headings):
  - bolge region (mountain range on a baseline)
  - yer place (peak with a flag)
  - kaynak resource (faceted gem)
  - yerlesim settlement (two towers and a door)
  - tur species (eye/leaf shape)
  - halk people (three heads)
  - olumlu mortal (bust)
  - esya item (sword)
  - efsane legend (scroll)
  - gelenek tradition (flame on an altar)
  - tarikat cult (flame on a plinth)
  - hizip faction (pennant)
  - gok celestial body (four-point star)
  - kehanet prophecy (eye in a triangle)
  - olay event (lightning bolt)
  - yasa world law (twin tablets)
  - ogul son (crown on a baseline)
  - teknoloji knowledge or tech (gear/sun)
  - eser artwork (music notes)
  - kanun legal code (scales)
  - ruh spirit (ghost)
  - dil language (speech box with a glyph)
  - yapit monument (temple)
  - sozluk lexicon (book with a "W" glyph)
  - tanri god (radiant sun)
  - arac vessel (ship with a sail)
  - dis Outer Being (amorphous blob with an eye)
  - dunya world (globe)
  - ordu army (two flags)
  - harabe ruin (broken columns)
- **Stats** (stat grid, son card): guc strength (hammer), dayaniklilik endurance (shield), ceviklik agility (swoosh), bilgelik wisdom (eye), kurnazlik cunning (crescent), irade will (pillar), yaraticilik creativity (spiral), karizma charisma (sun), kudret might (globe-sphere).
- **Passions and vitals:**
  - sadakat loyalty (chain link)
  - hirs ambition (crown without a base)
  - ofke wrath (flame)
  - merhamet mercy (heart)
  - can health (heart with a pulse)
  - oz essence (droplet; the most used icon at 52 call sites)
  - inanc faith (candle)
  - un fame (five-point star)
  - xp (double chevron up)
- **Actions and chronicle kinds:**
  - eylem action (hourglass)
  - varlik entity (half-filled circle)
  - kader fate (crossed arcs)
  - kronik chronicle (book)
  - dua prayer (raised hands)
  - emir command (sceptre)
  - yildirim lightning
  - iklim climate (sun and cloud)
  - bereket fertility (wheat)
  - zincir chain
  - surgun exile (exit arrow)
  - kutsa bless (sparkle)
  - ahit covenant (two rings)
  - lanet curse (skull)
  - ruya dream (moon with "z")
  - mesaj message (bubble)
  - meydan challenge (crossed swords)
  - dogum birth (sprout)
  - olum death (hourglass)
  - dirilis resurrection (rising arrow and arc)
  - armagan gift (present)
  - konsey council (circle with four seats)
  - sohbet conversation (two bubbles)
  - ceviri translation (A/文 glyph)
  - yukselis ascension (arrow up)
  - vahiy revelation (eye with rays)
  - derin deepen (magnifier with a plus)
- **Navigation and UI:**
  - harita map (folded map)
  - ag network (three nodes)
  - atlas (grid with a plus)
  - galeri gallery (framed picture)
  - yukle upload
  - iplik thread (loom)
  - kodeks codex (book)
  - ayar settings (sliders)
  - capa anchor
  - guckart power card (hexagon)
  - kilit lock
  - sistem (dashed orbit; also the fallback)
  - kopya copy
  - kalem edit (34 call sites)
  - cop delete
  - sol / sag / asagi / yukari chevrons
  - onay check
  - ara search
  - arti plus
  - kopar unlink (broken chain)
  - kapat close
  - geri_al undo
  - oynat play
  - ok arrow
  - goz eye with lashes
  - kitap open book
  - yazi script / quill
  - defter ledger
  - yedek backup (archive box)
  - imler bookmarks
  - yardim help
  - basarim achievement (trophy)
- **Mapping tables:**
  - `KRONIK_IKON` maps about 90 chronicle kinds to icons.
  - `ARAC_IKON` maps about 150 agent tool names to icons; the live feed uses it.
- **Procedural marks:**
  - `sigil(seed, colour, rarityIndex, size)`: a deterministic seal derived from a name.
    - A seeded RNG chooses 3–7 star points and a skip value for a star polygon.
    - Then come spokes, an outer ring r=45 and a tick ring (8 + 4·rarity ticks).
    - From index ≥1 there is a second ring r=38; from ≥3 a dotted ring r=34; Mythic (index ≥5) adds 12 rays.
    - It ends with a centre circle and a dot.
    - It is the portrait fallback for sons and gods that have no image.
  - `alanGlif(domain)`: a 2–5-stroke glyph in a faint r=10.5 circle, seeded from the domain name. It is used for domain chips.
  - Family glyphs: `aileGlif` in bilesen.js.
- **Inline SVGs outside the set (index.html):** the bell for notifications, the pulse for "Live feed" and the book. They are hand-copied rather than produced by `ic()`. The bell and the pulse do not exist in icons.js at all.

#### Motion
- **Duration tokens:** `--sure-1` .14s (38 transitions), `--sure-2` .28s (used only as a fallback), `--sure-3` .6s.
- **Easing:** `--egri` cubic-bezier(.2,.8,.2,1).
- **Keyframes:** 24 `@keyframes`. One, `siz-don`, is unused.
  - `flip`: card reveal, 0.9s 3D flip.
  - `spin`: the mythic border.
  - `giris`: new feed lines slide up 6px.
  - `vurgu` and `parla`: highlight flashes.
  - `pulse`: live dot.
  - `parilti`: shimmer on the progress bar.
  - `belirsiz` and `gu-kayan`: two indeterminate bars that do the same job.
  - `yazma`: typing dots.
  - `imlec`: streaming text cursor ▍.
  - `inis`: zoom-in "landing" when moving from kozmos to a map.
  - `pusula-gir`: compass entrance.
  - `nabiz`, `savas-nabiz`: focus and war pulses.
  - `siz-nefes`, `siz-titre`, `dis-nefes`: the leak/eldritch overlay breathes and jitters.
  - `solus-nabiz`: a fading son's badge pulses.
- **GSAP 3.12.5** (cdnjs; d3 7.9.0 is also loaded globally):
  - `views/harita.js:614–616`: map markers fade in with a random stagger, labels stagger in, the canvas fades.
  - `kozmos3d.js:739`: camera tween (power3.inOut).
  - `three@0.170` drives the 3D cosmos and the 3D network.
- **Reduced motion:** honoured three ways.
  - `@media (prefers-reduced-motion)` kills all animation (line 1617).
  - `:root[data-az-hareket]` (user setting "Reduce motion (Hareketi azalt)") sets durations to 0.001ms (line 1614).
  - JS checks `hareketAz()` to skip GSAP and the 3D auto-rotate.

#### Accessibility and theme switches (Settings → Appearance, "Görünüm ve erişilebilirlik")
- High contrast (`data-kontrast`): brighter text, stronger lines, a 3px focus ring and solid link underlines (lines 1611–1613).
- Font size scale (`--yazi`).
- Reduce motion.
- Focus: `:focus-visible` gives a 2px accent outline, offset 2. Inputs show the `--halka` ring.
- All three are stored in localStorage (`gorunum`) and applied by `gorunumUygula()`. That function also clears the JS colour caches so canvases re-read the tokens.

#### Tone of voice of UI copy
The copy is mythic, solemn and second-person singular: the player *is* the creator god. Labels are short imperatives; explanations are calm declaratives. Translated examples:
- Genesis:
  - "You are alone in the void." (Boşlukta yalnızsın.)
  - "Give a name and a seed. From this seed I will grow the world's cosmology, its language, your likeness, its first land, the first star you hang in the sky, and your first three sons."
  - Button "Create the world" (Dünyayı yarat).
  - Placeholder "A world made of salt; the seas are sweet, the soil is salty. The dead crystallise and keep their last thoughts inside."
- Primary actions: "Complete the epoch" (Çağı tamamla), "Summon son" (Oğul çağır), "Revelation" (Vahiy), "Stop" (Durdur), with the confirmation "Are you sure? Stop at a safe point."
- Live feed placeholder: "When a son acts, his thoughts, tools and words flow here. At the end of the epoch the mortal world's own events and Fate's verdict land here too." Idle state: "quiet" (sessiz). New-items badge: "new events ↓".
- Empty states:
  - "The void is still silent. It will appear here when the first star ignites."
  - "No prayers yet. They appear here when your sons or mortals wish for something."
  - "The council has never convened. Write an agenda and call the brothers together."
  - "No images yet. Open a card's page and upload here."
- Rule transparency: disabled controls state why, often citing the rule. Examples: "The first world cannot be buried in oblivion: it is the home the pantheon and sons return to"; "crowded: showing 1 step".
- Toasts are terse past tense: "Note recorded", "Added to bookmarks", "Undone", plus an inline "Undo" (Geri al) action.
- **LANGUAGE-SPECIFIC: drop or replace.**
  - `toast()` passes every message through `ekDuzelt` (Turkish suffix harmony after numbers and names).
  - `etiket.js`:
    - `ETIKET` turns snake_case keys into Turkish words with diacritics.
    - `DUA_ISTEK` and `SOZ_NIYET` hold verb phrases for prayer requests and speech intents.
    - `veListesi` joins lists with "ve".
    - `altTurEtiketle` and `hamAnahtarMi` detect raw keys leaking into prose.
  - In English, replace all of this with an i18n label dictionary keyed by the enum. The leak detector becomes a test that checks every enum value has a label.

### Recurring UI defects

Defect classes are grouped below. Each lists evidence (`style.css` line, DENETIM item translated, commit hash) and ends with a **prevention rule** for the new React/TypeScript design system.

#### 1. Token drift and magic numbers despite a "tokens only" rule
- **The rule versus the file:** the header (lines 9–17) says "All measurements come from tokens" and the style guide says "Don't write magic numbers; use the token". In practice:
  - **6px** is the most common gap (62 `gap: 6px`, 110 occurrences of 6px across spacing properties). It is off the 4/8 grid; other off-grid values are 5px (20), 3px (36), 10px (16) and 7px.
  - There are 94 distinct `padding` values and 43 distinct `margin` values.
  - Radius `--rad-md` is 7px, which is also off the grid.
- **Magic offsets that encode the position of another element:**
  - `.card-body { margin-top: -34px }` (line 513): the card body overlaps the art fade.
  - `.hero-info { padding-right: 96px }` (line 574) and `.gezgin .rehber-bas { padding: … 96px … }` (line 1437): these clear the drawer's absolutely positioned back/forward/close buttons.
  - `.drawer-nav { right: 52px }` (line 565).
  - `.actions > .satir-not { padding-left: calc(92px + var(--sp-2)) }` (line 272) is coupled to `.etiket { min-width: 92px }` (line 326).
  - `.tanri-eli > .actions > .etiket:first-child { min-width: calc(108px + var(--sp-3) - var(--sp-2)) }` (line 1342) is coupled to the `.buyur-satir` 108px column (line 1338).
  - `.dil-agac li::before` / `::after` use 42px (lines 1076–1077) to hit a node's vertical centre.
  - `.balon-av { margin-bottom: 18px }` aligns the avatar to the bubble's last line.
  - `.zil-pill { top: -5px; right: -6px }`.
- **Commits:**
  - 7fd1735 "UI polish: spacing, alignment, undefined tokens and narrow-screen layout".
  - 6ee5055 "section spacing fixed with shared rules: … 'sticking' found by the measurement script".
  - 062e6b8 "panel spacing".
- **Prevention:**
  - The spacing scale is 4/8/12/16/24/32/48 only.
  - Lint with stylelint `declaration-strict-value` (or Tailwind with a closed theme) so raw px is rejected in padding, margin, gap, inset, radius, font-size and colour.
  - No component may know another component's size. Offsets come from layout primitives: grid areas, or a `DrawerHeader` in normal flow instead of absolute buttons.

#### 2. Hard-coded colours outside tokens (CSS and, above all, JS)
- **CSS rules:** 22 literal hexes and 17 `rgba()` values. Examples:
  - `.pill` text #1a1408 (line 213)
  - `.ak-kapi` #c9b896, `.ak-savas` #ff7a5c, `.ak-gok` #a8b4ff, `.ak-medeniyet` #e0c06a (lines 1496–1502). The last duplicates `--harita-yerlesim` instead of referencing it.
  - `.iklim-buzul` #8fc3e6 (line 956)
  - `.olcek-cubugu` / `.oc-cizgi` #d8cfb8 (lines 868–871)
  - grounds #0d1520, #070a0f, #121626, #07080d, #1d2230, #05060a, #0b0d12
  - lightbox rgba(4,5,8,.92); palette scrim rgba(5,6,9,.55), which differs from `--scrim` .62
  - leak overlay rgba(150,80,200,.22) etc. (line 1318)
  - mask `#000` (6 times)
- **JS:** **261 distinct hex literals**:
  - `harita-gen.js` 107
  - `kozmos3d.js` 99
  - `views/harita.js` 38 (for example `ISARET` marker colours, the compass rose and route strokes `#e8ad48` / `#d8cfb8` / `#dc735d` at lines 93–223)
  - `views/kozmos.js` 23
  - `grafik.js` 8
  - `ag3d.js` 7
  - `bilesen.js` 7 (`RRENK` re-declares the rarity tokens)
- **Consequence:** the high-contrast theme cannot reach canvas or SVG colours. `renkOnbellekTemizle` re-reads only `--tur-*` and `--aile-*`.
- **`theme-color` #111318** is not a token.
- **c3db094** "fixed colours to tokens" was a partial clean-up.
- **Prevention:**
  - One TypeScript token module (`tokens.ts`) generates CSS variables and also exports typed values for canvas, three.js and d3.
  - Ban hex literals outside that file with an ESLint rule (`no-restricted-syntax` on `/#[0-9a-f]{3,8}/`) and a stylelint `color-no-hex` rule.
  - Every semantic colour (marker kind, climate, feed category, note colour) is a named token.

#### 3. Undefined, dead and fallback-masked tokens
- **Commit 7fd1735:** "Undefined tokens: `--f-ui`, `--r-sm`, `--gold`, `--golge-2` replaced with defined ones (font rules now take effect)". Rules had silently done nothing.
- **Fallbacks that hide drift:**
  - `var(--fs-sm, .85rem)` at lines 2125, 2153, 2156.
  - `var(--sure-2, .15s)` at lines 2135 and 2147. `--sure-2` is actually .28s, so the fallback documents the wrong value.
  - `var(--h-sm, 28px)` (line 1633) and `var(--bg-2, var(--panel))` (line 1453).
- **Dead:** `--btn-h`, `--btn-h-sm`, `--btn-h-lg`, `--input-h`, `--seri-8`, `--sh-1` (used once).
- **Prevention:** tokens are TypeScript constants (or Tailwind theme keys), so a typo is a compile error. No `var(--x, fallback)` in component code. A CI check fails on unused tokens.

#### 4. Cascade-order violations, re-declared selectors and appendix layers
- **The promise (header, lines 6–8):** one-way layer order (tokens → base → layout → components → views → responsive → utilities → accessibility), and "the same selector is not redefined in a second place".
- **What the file does:**
  - Layer 8 claims to be "at the very end", yet after it come appendices: "S6 · shared additions" (line 1625), S6 chronicle (line 1630), S6 map (line 1658), S6 live (line 1718), S6 pantheon/mobile (line 1762), "S7 design sweep" (line 1908), S8-A/B (lines 2067–2120), image generation (line 2122), network 2D/3D (line 2159), "S9 design language" (line 2171) and a final spacing patch (lines 2291–2297).
  - **21 top-level selectors are declared twice, often contradicting themselves:**
    - `.epoch`: nowrap plus ellipsis (line 197), then wrap and visible (line 1925).
    - `.power`: fixed height plus ellipsis (line 535), then auto height with a two-line clamp (lines 1938–1939).
    - `.live-suzgec`: nowrap, scroll and mask (line 1730), then wrap with no mask (line 1929).
    - `.denge-alan`: 4 columns (line 1422), then 3 columns (line 1949).
    - `.stat-form`: lines 1350 and 1956.
    - `.rel`: grid columns at lines 591, 1589 (media) and 1993.
    - `.rota-li.kapali`: opacity .5 (line 1206), then 1 (line 2017).
    - `.rota-kopar .btn`: radius 0 (line 2023), then md (line 2075).
    - `.alan`: flex (line 694), then block (line 1913).
    - `.dz-kutu`, `.lj small`, `.eksik-satir .drop`, `.live`, `.li-sure`, `details.acilir[open] > summary`, and others.
  - **@media regression:** DENETIM "M-63 done" reports the 18 scattered `@media` blocks were reduced to 5, one per breakpoint. The file now has **30 `@media` blocks**: 15 separate `max-width: 600px` blocks, 4 at 780px, 3 at 960px, plus one-offs at 900px and 560px.
- **Prevention:**
  - Use component-scoped styles (CSS Modules, vanilla-extract or Tailwind), so a component's styles live only in its file.
  - Breakpoints are tokens, used through a `useBreakpoint` hook or container queries.
  - Enforce `no-duplicate-selectors` and `no-descending-specificity` in stylelint.
  - No "appendix" files per audit round.

#### 5. `!important` wars (13 uses)
- `[hidden] { display:none !important }` (line 141). It is then repeated redundantly: `.ust-ilerleme[hidden]`, `.dokum-pop[hidden]`, `.denge-alan[hidden], details[hidden]`, `.coklu-oge[hidden]`, `.v-mekanik[hidden]`, and again with `!important` for `#view-ag canvas[hidden], #graph3d[hidden]` (line 2160).
- Icon size overrides:
  - `.cost .ic { width:12px !important }` (line 265)
  - `.tree .caret .ic { 12px !important }` (line 742)
- Colour overrides: `.rh-tehlike > .ic { color: danger !important }` and the `.t-dis` / `.t-sizinti` variants (lines 1443–1444).
- Comparison table: `.kt-ad` / `.kt-grup` font-size `!important` (lines 1471–1472), needed to beat `.karsi-tablo > div`.
- `.dis-bulanik img { filter … !important }` (line 1327).
- `.gu-bar.bekliyor > span { width:35% !important }` beats an inline style width (line 2129).
- `.float-tooltip-kap { background:transparent !important; padding:0 !important }` fights a third-party library (line 2169).
- Reduced-motion resets (lines 1614, 1617). These are legitimate.
- **Prevention:** `!important` is allowed only in the reduced-motion reset. Components expose `size` and `tone` props instead of being overridden from outside. Visibility uses conditional rendering, not `[hidden]`.

#### 6. Long selectors and specificity hacks
- **Read-only (exploration) mode** disables actions with a 9-selector list, opacity .4 and `pointer-events:none` (line 1427): `.salt-okunur form[data-post] [type=submit], #btnEpoch, #btnSummon, #btnVahiy, [data-kozmik], [data-geri-al], [data-mu], [data-kutsa], [data-c]`. Any new action is not disabled until someone remembers to add it here.
- **44px touch-target retrofit:** a 30-selector list (lines 1699–1703) and a 9-selector list (line 1857).
- **A global spacing patch** using combinator algebra (lines 2296–2297): `:not(.yigin, .yigin-s) > :is(.filters, details.acilir) + :is(div, article, section, p, dl, ul, ol, table, form, figure):not(.filters, .actions)`.
- **`:has()` state queries across the page (11):**
  - `body:has(#drawer:not([hidden])) .altbilgi #liveReopen` (line 1849)
  - `.god:has(.dunya-ust:not([hidden])) :is(#btnVahiy,#btnSummon)` (line 1888)
  - `#view-harita:has(.gecmis-bant:not([hidden])) .map-tools { top: 84px }` (line 1125)
- **Selectors keyed on implementation details:**
  - `.goz-sec .filters button.on[style]` targets the inline style attribute (line 971).
  - `span[class^="t-"]` uses an attribute-prefix match (line 398).
  - `.st:has(> span:first-child:empty:not([class]))` (line 527) detects an icon-less stat by an empty unclassed span.
  - ID styling: `#btnEpoch`, `#kronikAra`, `#dengeAra`, `#view-harita`, `#liveSes.acik`.
- **Prevention:** state is expressed as props and data attributes on the component itself (`<Button disabled={readOnly}>` sourced from a `useReadOnly()` context). Touch-target minimums are built into `Button`, `IconButton`, `Chip` and `Input`. Never style by ID; never use `:has()` to read app state.

#### 7. Text overflow, truncation and wrapping (the most frequent class)
- **Counts:** 27 `text-overflow: ellipsis`, 8 `-webkit-line-clamp`, 29 `overflow-wrap: anywhere`.
- **`.kes` utility (line 145):** it means "ellipsis on one line", but it is overridden to two or three lines in `.benzer-govde .kes`, `.lang .small.kes`, `.wall-ad .kes` (line 1941) and `.denge-alan .kes` (line 1421). The name no longer means what it does.
- **Truncation reversals:**
  - Card stat icons are hidden to give names room (`.card .statgrid .st > .ic { display:none }`, line 1937).
  - Power names were cut, so they now wrap to two lines (line 1938).
  - The header epoch line was cut, so it now wraps (line 1925).
  - Long route descriptions in the guide were cut, so they now wrap (line 2080).
- **DENETIM:**
  - S6-47 "section tabs are cut in the middle of a word".
  - S6-42 "the feed filter row is cut off".
  - S8-B-23 "in the kinship table names were cut without an ellipsis".
  - S8-C-20 "text overflowed cosmic-chronicle cells: the grid was `min-width: max-content`, so rows did not wrap and the Dazbuş column was cut on the right" (the fix comment is at line 1446).
  - S8-A-30 "guide resource descriptions were truncated server-side mid-sentence".
  - S8-A-4 "orbit showed raw floats ('1.3440149226158604 units')".
  - S7 (8cdf226) "truncated texts".
  - S8-B-1 "SHOUTING uppercase headline in the opportunity line".
- **Fixed-width name columns that then need ellipsis:**
  - `.rel` 150px (with 100px and 90px media variants)
  - `.oy` 130px
  - `.defter-bas b { max-width:180px }`
  - `.btn .hedef-dunya { max-width:14ch }`
  - `.dunya-ust select { max-width:150px }`
- **Prevention:**
  - Every text slot declares its overflow policy through a `<Text truncate={1|2|3}>` prop that applies a tooltip with the full text automatically.
  - Proper nouns are never `text-transform`ed.
  - Number formatting is centralised (`formatNumber`, `formatDecimal(2)`).
  - Grids use `minmax(0,1fr)`, never `max-content`.
  - Storybook stories include a "long name" fixture (60 characters, no spaces) for every component.

#### 8. Absolutely positioned overlays colliding on canvas views (map, cosmos, network)
- **Scale:** 63 `position:absolute` and 11 `position:fixed`. Each canvas view has 4–7 floating panels, each placed by hand with magic offsets.
- **Map:**
  - `.map-tools` top-left with `max-width: calc(100% - 2·sp-4 - 300px)` (line 842)
  - `.map-lejant` `top: 60px`, `max-height: calc(100% - 250px)` (line 852)
  - `.harita-alt` `max-width: min(500px, calc(100% - 180px))` (line 849)
  - `.pusula` `right: 18px; bottom: 60px` (line 867)
  - `.olcek-cubugu` `right: 18px; bottom: 22px` (line 868)
  - `.gecmis-bant` top-centre (line 1121), which pushes `.map-tools` down with `top: 84px` (line 1125)
  - `.harita-pop` z 6
- **Network:**
  - `.ag-ust` top-left
  - `.ag-bilgi` bottom-right
  - `.ag3-denetim` `max-width: calc(100% - 2·sp-4 - 340px)` (line 2164)
  - `.ag-ipucu` tooltip
  - Three popovers at `top: calc(100% + 6px)`
- **Cosmos:**
  - `.kozmos-ust`, `.kozmos-lejant`, `.k2d-not`
  - Fix comment, line 1507: "so the 3D scene's hint line and the Routes legend don't collide in the bottom corner" (`bottom: calc(sp-4 + 22px)`).
  - Fix comment, line 2046: "On phones the top box and the route legend don't overlap".
- **DENETIM:**
  - §4 "Top bar overflowing, map label collisions, screen-size-fixed markers".
  - S8-A-27 "on phones the network's control box covered the whole graph".
  - S6-56 "mobile map and atlas cramped; legend starts open".
  - c3db094 "label collision" in the network.
- **Prevention:**
  - A `CanvasStage` layout component with named overlay slots (top-left toolbar, top-right legend, bottom-left info, bottom-right inspector, top-centre banner, bottom-centre timeline). The slots are laid out by CSS Grid over the canvas, so they can never overlap and they collapse into a bottom sheet under a breakpoint.
  - Canvas label collision avoidance belongs in the renderer (d3-force label layout or an occupancy grid), not in CSS.

#### 9. Drawer chrome overlapping content
- **The drawer's back, forward and close buttons** are absolutely positioned at the top right (`.drawer-nav` and `.drawer-x`, z 6, lines 565–566). Content therefore has to reserve space with magic numbers:
  - `.hero-info` padding-right 96px
  - `.gezgin .rehber-bas` padding-right 96px and, on mobile, margin-top 64px (line 2256)
  - `.d-form` padding-top 64px on mobile (line 2258)
  - `.d-inner h3, h4 { scroll-margin-top: 64px }` (line 1918)
  - `.d-sec { scroll-margin-top: 56px }`
  - `.ages > [data-kage] { scroll-margin-top: 56px }`
- **Inside the drawer** the sticky `.bolum-nav` (z 4) and the sticky `.cag-serit` (z 6) compete. A right-edge fade is faked with a sticky gradient pseudo-element because the mask exposed content scrolling underneath (line 612 comment; commit 7fd1735).
- **Prevention:** `Drawer` has a real header row (navigation and title in flow) and a scroll body below it. Sticky sub-navigation lives inside the scroll body with one z-level, and scroll-margin comes from a single `--sticky-offset` value computed by the component.

#### 10. z-index stacking without a scale
- **Values in use:**
  - Local: 1, 2, 3, 4, 5, 6.
  - Global: 40 (mobile live panel), 50 (drawer), 60 (genesis **and** the mobile bottom tab bar), 61 (mobile "Live feed" reopen button), 70 then **80** (mobile map layer sheet, raised in a second media block at line 1759 because `backdrop-filter` made the toolbar a containing block, per the comment at line 1755), 85 (card reveal), 90 (lightbox), 92 (search palette), 95 (toast), 120 (essence breakdown popover `.dokum-pop`).
- **Collisions and workarounds:**
  - Genesis and the mobile tabs share z 60; only DOM order decides.
  - The mobile tab bar (60) sits above the drawer (50), so the drawer needs `padding-bottom: calc(--alt-cubuk + sp-10)` (line 2254). The comment reads "the bottom tab bar sits over the drawer: the last section must not hide under it".
  - The floating "Live feed" button (61) covered drawer content. DENETIM S8-C-26: "on narrow screens the floating 'Live feed' button sat on top of the open drawer's content: it covered the ledger's 'Undo' button". It was fixed with a `body:has(#drawer:not([hidden]))` hide rule (line 1849).
  - The toast (95) covers the palette and lightbox, so it is `pointer-events:none` except when it carries an action.
  - The breakdown popover (120) sits above everything, including modals.
- **Prevention:** one named z-scale in tokens: `base 0`, `raised 10`, `sticky 20`, `overlay-ui 30`, `drawer 40`, `nav-mobile 45`, `modal 50`, `popover 60`, `toast 70`. No numeric literal z-index anywhere else. Render modals, toasts and popovers through a portal managed by one overlay manager (Radix UI), so stacking follows open order.

#### 11. Nested scroll regions, hidden scrollbars and scroll fighting
- **Counts:** 36 `overflow: auto` containers, 20 hidden-scrollbar declarations, 6 `mask-image` edge fades. `body { overflow:hidden }` with `#main` scrolling.
- **Inner scrollers inside the scrolling drawer or page:**
  - `.sohbet-akis` max 360px
  - `.coklu-liste` max 196px
  - `.toplu-gunluk` max 260px
  - `#paletList` 50vh
  - `.ag-turler-ic` 60vh
  - `.map-lejant` `calc(100% - 250px)`
  - mobile `.ag-ust` 52% (line 2103)
  - `.tree`
  - `.lex-wrap`, `.matrix`, `.kk-kaydir`, `.karsi-kaydir` (horizontal)
- **DENETIM S8-C-16:** "The ledger was cut off half-way and older entries were unreachable: the list sat in a second 480px scroller inside the drawer and the view ended in empty space". The fix comment is at line 1371: "no inner scroll (a second scroller inside the drawer cut the list in half)".
- **Horizontal scroll rows with hidden scrollbars** give no scroll affordance: `.tabs`, `.bolum-nav`, `.live-filtre`, `.akis-kat`, `.kozmos-sekme`, `.filters.kaydir`, `.atlas-suzgec`, `.atlas-arac`, mobile `.ag-ust .filters`.
- **Squashing:** "the Atlas tree shrank to 10px" (comment at line 1574; 7fd1735) and "the horizontally scrolling filter row dropped to 11px" (comment at line 2104).
- **Live feed:** S6-41 "the live feed forced a scroll to the bottom on every event". It was fixed with a "new events ↓" badge.
- **Prevention:**
  - At most one scroll container per region (page, drawer body, sidebar).
  - Lists longer than a threshold paginate or virtualise (react-virtuoso) instead of getting a fixed max-height.
  - Horizontal overflow uses a `ScrollRow` component with visible edge-shadow affordances and arrow buttons.
  - Flex children that hold scroll areas get `min-height: 0` from the primitive, not ad hoc.

#### 12. Duplicated near-identical components
- **Pills, chips, badges (at least 14 variants with different heights):**
  - `.chip` 24
  - `.tag` 20 (mono caps)
  - `.cls` 20
  - `.rarity` 20
  - `.pill` 18
  - `.filters button` 26
  - `.filtre-dugme` 26 (an identical copy of `.filters button`, lines 703–705)
  - `.bolum-nav button` 26
  - `.live-filtre button` 26
  - `.cag-serit button` min 28 / 36
  - `.ag-ust .filters button` 24 and `.akis-kat button` 24
  - `.ruh-cip` 24 (a re-implementation of chip)
  - `.coklu-oge` 24
  - `.ro-etkin` 18
  - `.kd-bag` with no height (1px 7px padding)
  - `.ev-kez`, `.kp` (9px font), `.gecmis-isaret`, `.ornek-adlar span` (6px 12px), `.dunya-ust` (a 34px pill), `.live-yeni` 28
- **Tab and segment controls (8 variants):** `.tabs`, `.seg`, `.bolum-nav`, `.live-filtre`, `.ayar-sekme` / `.kayit-sekme` (a `.seg` restyled to wrap), `.kozmos-sekme`, `.cag-serit`, `.yer-seg` (a `.seg` turned into a 2×2 grid, line 2069).
- **Progress and meter bars (about 12):**
  - `.meter` 5px
  - `.st .meter` 3px
  - `.li-cubuk` 4px
  - `.ust-ilerleme > i` 2px
  - `.sefer-ilerleme` 6px
  - `.ro-cubuk` 6px
  - `.ilerleme` 8px
  - `.gu-bar`
  - `.tutum-cubuk` 8px
  - `.rel .bar2` 6px
  - `.oy-cubuk` 6px
  - `.sinif-serit` 10px
  - `.palet-serit` 8 or 6px
  - `.kapasite .meter`
  - Two separate indeterminate animations: `belirsiz` and `gu-kayan`.
- **Disclosure carets (4 implementations):**
  - `details.acilir > summary::before` (a 6px rotated border box)
  - `.lj-blok > summary::after` (the same on the right)
  - `.konsey > summary::before` (7px)
  - the `.tree .caret` chevron icon rotated 90°
- **Close buttons (3):**
  - `.x` with a literal "×" glyph at 22px (5 uses in JS)
  - `.btn.icon` with the `kapat` SVG (`.drawer-x`, `.lb-x`)
  - `.ag-bilgi-x`
- **Surfaces:** 31 rules re-declare `background: var(--panel); border: 1px solid var(--line)` plus a radius and padding instead of reusing `.panel-box`: `.thread`, `.prayer`, `.inanc`, `.yt-kart`, `.sefer`, `.ogul-iz`, `.grafik`, `.dz-kutu`, `.lang`, `.dil-dugum`, `.benzer`, `.bildirim`, `.borc-kart`, `.kapasite`, `.yasam`, `.eksik-satir`, `.inanc-form`, `.duzen-form`, `.coklu-sec`, `.bag-kur`, `.tur-kart`, `.sablon`, `.ad-liste li`, `.konsey`, `.ag-saglik-ic`, `.ag-yol-form`, and others.
- **Left accent stripes:** 2px in `.thread`, `.quote`, `.saying`, `.entry.k-tanri_isareti`, `.kart-firsat`, `.kd-soz`, `.ev`, `.kr-ara-grup`, `.ad-liste li`; 3px in `.bakis`, `.cekme`, `.sefer`, `.prayer.olumlu-dua`, `.bildirim.onem-*`, `.borc-kart`, `.rehber-bas`, and the `.kt-bas` / `.kk-bas` top stripes.
- **Avatars and portraits (sizes 18, 26, 28, 30, 32, 34, 40, 56px):** `.rel .av`, `.balon-av`, `.konsey-av`, `.kt-av`, `.yt-ic`, `.dk-av`, `.li .thumb`, `.benzer-ic`, `.b-ic`, `.n-kapak`, `.gu-kucuk`. The sigil fallback sizes are hand-set for each.
- **Popovers:** `.ag-yol-form`, `.ag-saglik-ic` and `.ag-turler-ic` are each absolute at `top: calc(100% + 6px)` with z 5, and each has its own identical mobile "become static, full width" override (lines 1594–1598 and 2237–2238).
- **Empty states (9 forms):** `.empty`, `.empty.kucuk`, `.empty.buyuk`, `.empty.ikonlu`, `.palet-bos`, `.sohbet-bos`, `.lj-bos`, `.kk-hucre.bos`, and plain `p.muted`.
- **Loading indicators:** `.donen` spinner, `.li-cubuk`, `.gu-halka` (conic ring with a 7px label), `.yazma-nokta` typing dots, the `.ev.akiyor` cursor.
- **DENETIM:** S6-48 "record concepts are mixed up: Chronicle, Codex, Book, Ledger, Log; button text alternates between 'complete', 'close' and 'resume'".
- **Prevention:** a closed component library and a review rule that blocks one-off surfaces. The library: `Chip` (variants neutral/tone/rarity/status; sizes sm 20 / md 24; optional icon, count and remove; ellipsis built in), `Badge`, `Tabs`, `SegmentedControl`, `FilterPills`, `ProgressBar` (determinate/indeterminate, one height scale), `Disclosure`, `IconButton` (close is `IconButton icon="close"`), `Card`/`Surface` (variant: plain/accent-stripe/tone; stripe width a token), `Avatar` (xs 20, sm 28, md 40, lg 56; sigil fallback built in), `Popover` (Radix), `EmptyState` (icon, title, description, action), `Spinner`.

#### 13. Button, control and icon size drift and alignment nudges
- **Control heights:** about 17 distinct values beyond the three tokens: tabs 40, live-head 44, footer 30, palette input 52, palette row 38, tree row 30, `ab-yardim` 20, `kesif-bant .btn` 22, `live-reopen` 22, `gu-mini-btn` 22, `akis-ses-liste button` 22, `live-yeni` 28, `ust-ilerleme` 22, mobile tab bar 58, mobile reopen 40, `bag-kopar` 26, `ro-etkin` 18.
- **Icon sizes:** ten distinct, literal 12/13/14/15/20/22/28/40/44/84px, against four tokens. `.btn.sm .ic` is 14 (not a token); `.cost .ic` is 12 `!important`.
- **Baseline nudges:**
  - `.ic { vertical-align: -3px }`
  - `margin-top: 2px` or `3px` on icons in `.entry`, `.ia-liste`, `.konsey-notlar`, `.rehber-liste`, `.yasam`, `.lj-hakim`, `.lj-izgara`, `.rota-li`
  - `.buyur-satir > .etiket { padding-top: 5px }`
  - `.derin-kv > dt` padding-top `calc(sp-2 + (fs-md·lh-prose − fs-sm·lh-base)/2)` (line 2187), to align label and value baselines
- **DENETIM:**
  - S8-B-25 "Start buttons shifted with the description length".
  - S8-A-11 "the fourth 'Where should it be born?' option dropped alone onto its own line".
  - 7fd1735 "the 'pronunciation' label stuck to its box; stats: name and value drifted to the middle when a neighbour cell grew".
  - 96d8234 "the label column of the God's hand aligned with Edit and Command".
- **Prevention:**
  - `Button`, `IconButton`, `Input` and `Select` share one size prop (sm 28 / md 36 / lg 44) and one icon size per control size.
  - Icon-plus-text layout is `inline-flex; align-items: center` inside the primitive, with no per-site nudges.
  - Forms use a `FormRow` grid with a fixed label track defined once.
  - List items with leading icons use a `ListItem` primitive whose icon box matches the first line's height.

#### 14. Responsive and mobile breakage
- **Breakpoints:** seven: 1280, 1100, 960, 900, 780, 600, 560. The 900 and 560 values each appear once. Also `hover: none`. There are 30 `@media` blocks.
- **Touch targets** were retrofitted by enumerating selectors to reach 44px (lines 1699–1703 and 1857–1865). Consequences:
  - `.seg { height:auto }` because "fixed-height 44px buttons were clipped at the bottom" (line 1858).
  - Clickable chips get an invisible `::after` hit area `inset: calc((24px − 44px)/2) 0` (line 1862).
  - The header is re-ordered with `order: -2` / `-1` (lines 1882–1883). The comment reads "the world selector was squeezed into the first row; 'Summon son' fell alone onto its own row".
  - The compact header hides elements on scroll (`body.bas-kucuk`, lines 1852–1855).
- **DENETIM:**
  - S6-55 "at 390px the top bar takes about 30% of the screen; 3 of the tabs are off-screen; no bottom navigation; costs hidden".
  - S6-56 "touch targets 26px".
  - S6-61 "gallery single column on mobile".
  - S8-B-34 "the kinship table overflowed its box at 390px; the last son's column was invisible".
  - S8-A-27.
  - c3db094 "phone layouts".
  - 7fd1735 "narrow-screen layout".
- **The font-size setting `--yazi`** scales only the `--fs-*` tokens. Control heights (`--h-*` in px), the literal-px fonts (7, 9, 10, 13, 14, 15, 22, 46, 96px) and SVG text in canvases do not scale, so at "Very large" (1.3) text can overflow the fixed 34px controls.
- **Prevention:**
  - Mobile-first with three breakpoints as tokens (sm 640, md 1024, lg 1280), and container queries for components.
  - Minimum 44px hit areas are built into interactive primitives on coarse pointers (`@media (pointer: coarse)`).
  - Heights are in rem, so user font scaling works through the root font size.
  - Every screen ships a Storybook story or Playwright screenshot at 390, 768 and 1440 widths, including at 130% text scale.

#### 15. Contrast and legibility
- **Measured WCAG ratios:**
  - Text tokens pass: fg 11.4–15.2; muted 4.6–6.2; danger 4.5–6.0, falling to 4.49 on panel-3.
  - **Boundaries fail the 3:1 non-text minimum:**
    - `--line` reaches only 1.06–1.41 and `--line-2` 1.28–1.71 against the surfaces.
    - `--line-2` is the only border of inputs, selects, buttons and checkboxes.
    - The empty-state icon is coloured `--line-2` (lines 435 and 1945).
  - `--seri-6` #008300 (the "living things" family marker) is 2.86–3.82.
- **Tiny type:**
  - 7px in the `.gu-halka` percentage label (line 2143)
  - 9px in `.kp` and `.tree .dur` (lines 632 and 736)
  - 10px in `.tree .dur.yildiz`
  - 10.5px mono caps with opacity .7 for timestamps (`.ev[data-zaman]::before`, line 1720) and `.denge-varsayilan` (line 1953)
  - `.stars .off` at opacity .22
- **Dimming:** 18 distinct opacity values (.2–.9) express "disabled, dead, read, closed or past": `.btn:disabled` .42, checkbox .45, locked power .45, powercard .5, dead row .55, strike .6, read notification .6, done prayer .65, closed thread .7, past relation .72, recalled voyage .75, lost voyage .8, read-only .4.
- **Colliding meanings:**
  - Warn #dcb45c is close to legendary gold #e8ad48. Gold is also used for the creator, sayings and the `.t-ogul` type colour, so a warning looks like legendary or divine.
  - Good #92c26d is close to uncommon #7fc489.
  - Danger #dc735d, war-feed #ff7a5c, `seri-8` #e66767 and mythic pink are close to one another.
  - The style guide claims status colours are distinct from the accent, but not from rarity.
- **High contrast** swaps only base tokens; hard-coded hexes and canvases (see class 2) are unaffected.
- **Prevention:**
  - Contrast tests in CI (axe plus a token-pair checker): text ≥ 4.5, UI boundaries ≥ 3.
  - A minimum font size of 11px (0.6875rem) for any text.
  - Disabled, inactive and past states are three named visual states, not ad hoc opacities.
  - Status hues are chosen to be perceptually distinct from all six rarity hues, and always paired with an icon or shape.

#### 16. Iconography inconsistencies
- **Duplicates:**
  - Identical paths: `olay` = `yildirim` (bolt) and `sadakat` = `zincir` (link). `yabanci` aliases `tanri`.
  - Near-identical: `tanri` ≈ `karizma` (sun), `kurnazlik` ≈ `ruya` (moon), `eylem` ≈ `olum` (hourglass), `ogul` ≈ `hirs` (crown), `merhamet` ≈ `can` (heart).
  - DENETIM S6-49: "the same icon for different concepts".
  - `KRONIK_IKON` has duplicate keys (`mucize`, `tapinma`) and `ARAC_IKON` duplicates `yerlesim_kur`. Unknown keys silently render the `sistem` fallback (19 explicit `ic('sistem')` calls).
  - DENETIM S7-19: "35 tools had no icon in the feed". S8-C-19: "nine chronicle kinds had no name or icon".
- **Mixed systems:** the SVG set is mixed with Unicode glyphs:
  - × (19 uses), † (6, death or dead), ★ (5; stars `.stars`), ▲
  - ✓ ✗ via CSS `content` (lines 916 and 918)
  - ▍ cursor, ↓ in "new events ↓", ↺ in the rule-reset button
- **index.html** hand-inlines 10 SVGs. The bell and pulse icons are absent from the set, and some inline copies omit `stroke-linecap="round"`, so they render differently from `ic()`.
- **Prevention:**
  - A single typed `<Icon name>` component whose `name` is a union type: a missing icon is a compile error, and there is no silent fallback.
  - A uniqueness test over path data.
  - No Unicode glyph icons.
  - Use one maintained set (Lucide, with 1.5–1.75 stroke to match the current look) plus a small custom set for the domain (sigil, family glyphs).

#### 17. Duplicate SVG IDs and `[hidden]`-dependent rendering
- **Duplicate IDs:** `LOGO_SVG` hard-codes `<linearGradient id="lg-aerona">` and is rendered at least three times (header, footer, genesis). On mobile the header logo is set to `display:none` (`body.bas-kucuk #brandLogo`, line 1853). In Chromium, a gradient defined inside a `display:none` SVG stops resolving for other references, so the visible logos risk losing their fill.
- **Hidden-attribute fragility:** `[hidden]` handling depends on a global `!important` and on seven local re-declarations (class 5).
- **Prevention:** the logo is a React component using `useId()` for gradient IDs (or a static asset `<img src=logo.svg>`).

#### 18. Fonts: loaded weights versus used weights
- Alegreya Sans **600** is used (`.chip b`, `.b-baslik`, `.oy-ad`, `.kt-grup`, `.pu-etiket`, `.ogul-iz-ad`, …) but only 400/500/700 are loaded, so the browser substitutes 700 or synthesises a weight.
- JetBrains Mono **700** is used (the `.marka-ad` wordmark) but only 400/600 are loaded.
- Cormorant **italic 600** is used (`.ornek-adlar span`, `.ad-ad`) but only italic 500 is loaded, which gives faux bold.
- Cormorant **400** is used for prose and quotes but only 500+ is loaded.
- The Google Fonts link is duplicated in index.html and stil.html.
- `display=swap` without size-adjusted fallbacks causes a text reflow (layout shift) on first paint.
- **Prevention:** self-host the fonts through `@fontsource` with exactly the weights the type scale references, enforced by the typography token set; add `size-adjust` fallback faces.

#### 19. Layout shift, refresh flicker and re-render cost
- **Rendering by strings:** views render whole HTML strings and patch them with a home-made keyed DOM morph (`core/dom.js` `yamala` / `yamaCocuklar` / `yamaDugum`, keyed by `data-k` or `id`). It exists to keep focus and input values across SSE-driven refreshes.
- **Drawer:** a non-silent open clears the body first (`body.innerHTML = ''`, `core/cekmece.js:54`) and then resets the scroll, which causes a flash.
- **Broken images:** these get `visibility:hidden` (`img.kirik`, line 679), leaving holes.
- **Feed:** every new feed row animates (`giris`), and grouping and folding (`.ev.katli`) change heights after insertion.
- **DENETIM:**
  - S6-58 "a full refresh wipes the Atlas cache; with a world selected the 690 KB list downloads again"; "the chronicle renders closed `<details>` content too (16.5k nodes)".
  - S6-41 "the feed forced scroll to the bottom".
  - Commit 39dc001 "UI freezing: the engine breathes between steps".
- **Prevention:**
  - React with stable keys and query caching (TanStack Query) plus SSE-driven cache invalidation per entity, instead of whole-view refetches.
  - Skeleton placeholders with fixed dimensions for cards and images; `aspect-ratio` boxes for every image; a sigil fallback on image error rather than a hole.
  - Collapsed content is not mounted.
  - Long lists are virtualised.
  - Feed auto-scroll only when the user is pinned to the bottom (built into a `LogView` component).

#### 20. Inconsistent empty, disabled and explanatory states
- **Empty states:** nine forms (class 12). The copy differs between "Henüz … yok" ("No … yet"), "… yok" ("No …") and instructional sentences.
- **Disabled states:**
  - DENETIM S6-38: "button behaviour with insufficient essence is inconsistent: Bless, miracle, disaster, curse and '★ give' stay enabled and then error". The fix introduced `.btn[disabled][data-engel]` with a tooltip reason (line 1628).
  - S8-A-3 and S8-A-7: buttons enabled with nothing to act on.
- **Prevention:**
  - An `EmptyState` component with a required `title` and `description` and an optional `action`.
  - A `DisabledReason` prop on `Button` that renders an accessible tooltip and `aria-describedby`.
  - A lint or test check that every `disabled` button has a reason.

#### 21. LANGUAGE-SPECIFIC typography defects (drop for an English-only app, but keep the lesson)
- **Uppercase transforms:** `text-transform: uppercase` under `lang="tr"` turned the model name "Haiku" into "HAİKU" (S8-B-4). The fix was `.model-ad { text-transform:none }` (line 2088).
- **Raw keys leaking:** snake_case keys appeared in the UI (S8-A-25, S8-A-28, S8-A-29, S8-B-7, S8-C-1, S8-C-7, S8-C-19; `etiket.js`).
- **Suffix harmony:** fixed after the fact by `ekDuzelt` (toast, guide: "the 'ın ayı' suffix mismatched").
- **Prevention:**
  - All enum-to-label rendering goes through one typed i18n dictionary; a test asserts that every enum value has a label.
  - Never uppercase proper nouns; caps styling only on fixed UI labels.

### Design-token inventory

Measured on `public/style.css` (2297 lines, about 1821 rule blocks) with grep and awk. "Uses" counts declarations.

| Dimension | Distinct values in use | Detail | Consolidation target |
|---|---|---|---|
| Custom properties defined | 135 in `:root` plus 16 high-contrast overrides | 4 dead legacy aliases (`--btn-h*`, `--input-h`); `--seri-8` unused | Generated from `tokens.ts` |
| Hex colours in CSS | 60 | About 38 inside token blocks; 22 hard-coded in rules (#000 ×12 as mask/shadow; #e0c06a, #d8cfb8, #c9b896, #ff7a5c, #a8b4ff, #8fc3e6, #1a1408, plus 10 ground hexes) | All named tokens |
| `rgba()` colours | 17 | 7 black alphas (.3–.85) for shadows and vignettes; 3 near-black scrims (.55/.62/.92); 4 purple leak tints | Shadow and scrim tokens |
| `color-mix()` calls | 133 (111 distinct) | Mix percentages: 31 distinct values (2, 4, 5, 6, 7, 8, 9, 10, 12, 14, 18, 22, 25, 28, 30, 35, 40, 45, 50, 55, 58, 60, 62, 70, 75, 80, 85, 88, 90, 92, 94%) | A tint scale per hue (for example 8/16/32/56%) |
| Hex colours in JS | 261 distinct | harita-gen 107, kozmos3d 99, harita 38, kozmos 23, grafik 8, ag3d 7, bilesen 7 | Exported from `tokens.ts` |
| Font families | 3 | display 52 uses, mono 37, body 19 (plus inheritance) | Keep 3 |
| Font sizes | 9 tokens (10.5, 11.5, 12.5, 14.5, 17, 21, 26, 32, 40px) plus 9 literal px (7, 9, 10, 13, 14, 15, 22, 46, 96) plus 2.8em, 1em and .85rem fallbacks: about 21 effective sizes | Token use: sm 97, xs 60, 2xs 38, md 26, lg 24, xl 11, 2xl 7, 3xl 6, 4xl 2 | 8-step rem scale (12/13/14/16/18/22/28/36, plus display 48) |
| Font weights | 4 (400 ×8, 500 ×12, 600 ×52, 700 ×50) | 600 is not loaded for Alegreya Sans; 700 is not loaded for Mono | 400/500/600/700, loaded to match |
| Line heights | About 20 (1, .9, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3, 1.35, 1.4, 1.45, 1.5, 1.55, 1.6, 1.65, 1.7, 18px, plus 4 tokens) | Tokens used only 21 times | 4 tokens (tight, snug, base, prose) |
| Letter-spacing | 12 (0, .01, .02, .04, .06, .08, .1, .12, .2, .32em, 1px, normal) | | 3 (normal, caps .08em, wordmark .3em) |
| Padding | 94 distinct declarations | Most frequent: 0 (38), sp-3 (34), sp-2 (20), sp-4 (19), "sp-2 sp-3" (19). Raw px in spacing properties: 1px ×75, 2px ×75, 3px ×36, 4px ×40, 5px ×20, **6px ×110**, 7px ×2, 8px ×5, 10px ×16, 12px ×3, and 27 more values up to 150px | Spacing tokens only |
| Gap | 28 distinct | sp-2 133, sp-3 64, **6px 62**, 2px 26, sp-1 23, 4px 22, 5px 12, sp-4 9, … | 4/8/12/16/24 |
| Margin | 43 distinct | Includes negative -34px (card body) and -1px joins | Mostly removed (stack/gap layout) |
| Border radius | 21 distinct | rad-lg 44, rad-md 34, 50% 27, rad-pill 25, 0 12, rad-sm 9, 3px 7, 2px 7, rad-xl 5, inherit 3, 1px 2, 5px 1, an organic blob shape, plus 7 asymmetric combinations | 4 (sm 4, md 8, lg 12, full) |
| Box-shadow | 24 distinct | sh-2 ×10, sh-3 ×5, halka ×5, sh-1 ×1, plus 3 inset accent bars and 2 big inset vignettes | 3 elevations plus focus ring |
| Opacity values | 18 distinct | .2–.9 for dim and disabled states | 3 named states |
| z-index | 17 distinct (1, 2, 3, 4, 5, 6, 40, 50, 60 ×2, 61, 70, 80, 85, 90, 92, 95, 120) | Locally 1–6 used 27 times; global tie at 60 | 9-level named scale |
| Breakpoints | 7 widths (1280, 1100, 960, 900, 780, 600, 560) plus `hover:none` and `prefers-reduced-motion` | 30 `@media` blocks (600px ×15, 780 ×4, 960 ×3, others ×1) | 3 breakpoints plus container queries |
| Control heights | 6 tokens plus about 17 literal (18, 20, 22, 24, 26, 28, 30, 36, 38, 40, 44, 52, 58px, …) | | 3 sizes (28/36/44) plus chip 24 and tag 20 |
| Icon sizes | 4 tokens (13/16/20/28) plus 10 literal (12, 13, 14, 15, 20, 22, 28, 40, 44, 84px) | 14px alone ×16 | 4 (12/16/20/24) plus illustrative 40/80 |
| Fixed widths (px) | 58 distinct `width` / `min-width` / `max-width` px values | 1px to 1280px | Layout tokens plus `minmax()` |
| Transition durations | 5 (.14s token ×38, .15s ×6, .18s ×2, .2s ×1, .6s ×3 plus token) plus 24 keyframes (1 unused) | | 3 durations, 2 easings |
| `!important` | 13 | | 1 (reduced motion) |
| Positioning | absolute 63, fixed 11, sticky 7 | | Overlay slots and portals |
| Truncation helpers | ellipsis 27, line-clamp 8, `overflow-wrap:anywhere` 29 | | `<Text truncate>` |
| Hidden scrollbars / mask fades | 20 / 6 | | A `ScrollRow` with affordances |
| Duplicated top-level selectors | 21 | | 0 (lint) |
| `:has()` selectors | 11 | | 0 for app state |

### Per-screen defect evidence (from Parts 2–5)

Concrete file:line findings recorded while reading each screen. They are instances of the classes above (and a few logic/UX smells specific to one screen).

#### Shell, settings and utility screens

Shell / refresh
- `core/yenile.js:30` Button locking guesses the trigger as "the last button clicked within 600 ms" (`G.sonTik`); fragile; pass the button explicitly.
- `core/yenile.js:33,43-48` Every `act()` makes two extra `GET /api/defter` calls just to decide whether to offer Undo; the mutating endpoint should return the ledger id.
- `core/yenile.js:86,91` Magic idle gates (350 ms debounce, 1200 ms idle, 400 ms poll while pointer held) are hard-coded, not rules.
- `core/yenile.js:162` `(G.S.sayim[e.tur] || 1) - 1` — counts can silently go wrong; recompute server-side.
- `core/yenile.js:192` and `core/durum.js:28,49` / `views/harita.js:16` write `aerona.tab` / `aerona.harita` raw while everything else is JSON via `yerel()`; inconsistent storage format.
- `core/yenile.js:193-196` The tab switcher reaches into Map/Network/3D modules to pause them — tight coupling; each view should own its lifecycle.
- `views/genesis.js:59-60` Logo SVGs re-injected on every header render (every refresh).
- `views/genesis.js:73` Header render kicks off a background Cosmos fetch (side effect inside render).
- `views/genesis.js:87` Render mutates `dataset`/`tabIndex` of `.essence` once ("first render" hack).
- `views/genesis.js:111` and `views/akis.js:179` epoch phase count "/5" hard-coded in two places.
- `views/genesis.js:103` unread pill caps at "99+" (hard-coded).
- `index.html:43` / `views/akis.js:498` Stop button relies on the generic `data-onay` two-click with a 4 s timeout, while Ledger undo (`views/defter.js:45`), Reset-all rules (`views/ayarlar.js:173`), batch deepening (`views/toplu.js:45`) and image generation have their own two-click variants with no timeout and no revert — four different confirm patterns.
- `index.html:31` `.marka-ad` "Weavers of the Void" and `#worldName` default "Weavers of the Void" duplicate the brand while loading.
- `style.css:197` epoch line is a single `nowrap` ellipsized line holding up to 8 chips; chips silently disappear on narrower widths.
- z-index ladder is ad hoc: live panel (mobile) 40, drawer 50, genesis 60, mobile tab bar 60, live reopen 61, map tool sheet 70/80, reveal 85, lightbox 90, palette 92, toast 95, breakdown popover 120 (`style.css:562-1769`). The popover can sit above the palette/lightbox; genesis and the mobile tab bar share 60.
- Escape handling is split (`views/palet.js:90,103`); Esc does not close the breakdown popover; reveal overlay has no focus management.
- Footer shortcut hint (`index.html:75`) duplicates the Help list and goes stale independently.

Settings
- `views/ayarlar.js:66` Sections are tagged by regex-replacing the opening `<div class="d-sec` of an HTML string — brittle.
- `views/ayarlar.js:176` Opening Settings fires 7 requests (rules, measurement, health, batch, images, network health, backups) even for hidden tabs; the World Rules editor renders ≈3,300 inputs at once (comment at `:161` still says "over 2000") — no virtualization or lazy group rendering.
- `views/ayarlar.js:171` Clearing an input silently sends `null` = reset to default.
- `views/ayarlar.js:96,217` Cheat bypasses `act()` (no lock, no undo offer) unlike other actions.
- `views/ayarlar.js:117` Health section removes itself on any error (no error state).
- `views/ayarlar.js:119,136`, `views/olcum.js`, `views/rehber.js:23`, `views/ag.js` Decimal comma done by `String(x).replace('.', ',')` — use locale formatting.
- `views/ayarlar.js:204` Backup size uses its own "KB" rounding, different from Health's MB/KB formatter.
- `views/ayarlar.js:107-110,210-213,226` Typed confirmations "DEĞİŞTİR", "GERİ YÜKLE", "SIFIRLA" contain Turkish-only letters; the server checks the exact strings.
- `views/ayarlar.js:113` vs server: Reset says "permanently deleted" but the server takes a pre-reset safety backup — copy is misleading.
- `views/ayarlar.js:76,79` Copy hard-codes "Claude"/"Max subscription".
- Settings → Records → "Action ledger" section is only a pointer to another drawer (duplication).
- World Rules groups "Mortals" (4) and "Cosmos" (3) are tiny near-duplicates of "Mortal agents"/"Cosmos and travel"; "Interface" mixes UI and server page sizes; "God and son costs" is assigned to two legacy tables plus KURAL (grouping drift).

Records / notifications / prayers
- `views/kayitlar.js:24` "My notes" downloads the entire entity list to find personal notes; `:29` fetches every world's whole map just to list map notes (N requests).
- `views/bildirim.js:21` Achievement detection by Turkish title prefix "Başarım:" (legacy compatibility hack).
- `views/bildirim.js:28`, `views/defter.js:31` SQLite timestamp parsing via `replace(' ', 'T') + 'Z'` duplicated.
- `views/dualar.js` filter state not persisted; full list fetched on every render (no paging) though the server caps at `SUNUCU.dua_liste`.
- `core/dokum.js:11-16` Breakdown parser accepts many alternative field names (`deger ?? d ?? v ?? miktar`, `once ?? onceki`, …) — the API contract was never fixed.
- `core/dokum.js:42-45` Popover always placed below the anchor (no flip near the bottom edge), fixed 300 px width.
- `views/acilis.js:21` Errors silently swallowed; no queue when several sons arrive at once (later reveals overwrite earlier).
- `views/palet.js:84` 140 ms debounce hard-coded.

Text helpers
- `core/adlar.js:17` One regex alternation of every name (thousands) re-built on name changes; names shorter than 4 characters are never linked; `:21` HTML is split with a regex to avoid tags — fragile.
- `core/adlar.js:50-65` Server text carries ad-hoc id tokens (`#12`, `(#12)`, `oğul#3`, `iplik#5`) resolved client-side with Turkish literals; define a structured mention format server-side.
- `arac-ad.js:66` `duzyazi` blindly turns any snake_case token in prose into spaced words to hide leaked keys — masks server bugs.
- `arac-ad.js:94` Detects a "Turkish prefix" by checking for Turkish-specific letters.
- `etiket.js:16` Raw-key detection with a hand-maintained exclusion list.
- `core/dom.js:9` every toast runs `ekDuzelt` (Turkish suffix fixer).
- LANGUAGE-SPECIFIC, drop or replace: all of `dil.js` (`ekle`, `ekDuzelt`, `yazimDuzelt`, `sayiOkunus`, `cogulIyelik`, `toplulukIci`, `ekSozlugu` and the `ek` field of `/api/adlar`), `arac-ad.js` `SOZ`/`aracEmri`, apostrophe-suffix template strings in `views/genesis.js:82,90` and `views/rehber.js:30,37`, `etiket.js veListesi`, and `toLocaleLowerCase('tr')` everywhere (search/filter casing).

Open questions for the rewrite: whether the World Rules editor should stay a single giant form or become a searchable virtualized table with per-group pages; whether typed confirmations should be English words (REPLACE / RESTORE / RESET) or a world-name confirmation.
#### Pantheon and record pages

1. **Language-specific grammar (drop/replace):** `varlik.js:226-232` `ekFormHtml` + `/api/ek` (Turkish suffix pronunciation/compound settings, inline `onclick` at :231); `varlik.js:335` debt sentence uses `ekle(aa,'yonelme')` (dative); `panteon.js:143` `ekDuzelt(...'nin çağrısıyla')` (genitive); `toLocaleLowerCase('tr')` comparisons throughout (`varlik.js:148,476,483`, `formlar.js:27`). Hard-coded suffixes that ignore vowel harmony (wrong for many names): `varlik.js:83` `'in çapası`, `varlik.js:430` `'in canı alındı`, `ogul.js:68` `'e ne söylersin?`, `ogul.js:193` `%…'sini`, `varlik.js:423,434` `'si`/`'u`.
2. **String-replace HTML injection:** `varlik.js:274` and `ogul.js:259` add `data-donustur="ek"` by `.replace()` on generated markup.
3. **Global mutable state on window:** `varlik.js:46` `window._bilgiler` used by `mudahaleHtml` (`:395,401`).
4. **Fragile conditional markup:** `varlik.js:401` opens either a visible `<div class="actions">` or `<div class="actions" hidden>` in one ternary and closes in another; empty hidden rows remain in DOM.
5. **Duplicate IDs:** element ids (`#ruyaIn`, `#kStat`, `#sohbetIn`, `#emirIn`, `#birlesHedef`, `#yolHedef`, `#tezahurIn`, `#kisiselNot`…) can exist twice when the same record is shown in the drawer and the Atlas detail pane; `ogul.js:85` works around it with `[data-sohbet] #sohbetIn` + `$$`.
6. **Two different `modelAd` implementations:** `panteon.js:19` (capitalise anything) vs `bilesen.js:93` (regex haiku|sonnet|opus, "—" fallback).
7. **Rarity colours duplicated** in JS hex (`bilesen.js:8 RRENK`) and CSS vars (`style.css:59-64`); sigils use the hex, cards use CSS.
8. **Client-side duplicates of server rules:** `mucizeBos`/`lanetBos` (`varlik.js:380-390`) mirror server `mucizeUygula`; gain/cost formulas for drain/devour/harvest/kill are recomputed client-side (`varlik.js:414,422,433,445`, `ogul.js:189-190`, `yabanci.js:47-48`) and can drift from the server. Every `kural(key, fallback)` embeds a fallback default.
9. **Inconsistent confirmation patterns:** form `data-onay` (no timeout), button `data-onay` (4 s timeout), lightbox delete (custom two-step, no timeout), bulk-generate (custom `data-emin`), typed "BİRLEŞTİR" for merge. Several irreversible actions have **no** confirmation: Ascend (`ogul.js:204`), Give star, Resurrect son (`ogul.js:165`), Restore to canon (`varlik.js:62`), Make prophet, Lift lineage curse.
10. **Missing toasts:** "Act now" (`ogul.js:290`) and "Ascend" (`ogul.js:302`) call `act` without a success message.
11. **Magic numbers:** timeline dot `6+min(10,n*2)` px (`varlik.js:376`); description truncation 40 chars (`varlik.js:338`); lexicon 60 rows (`:120`); datalist caps 800/600 (`:36,129`, `formlar.js:28`) — silently truncates name search in large worlds; note autosave 900 ms (`:471`); highlight 1600 ms (`:494`); section-nav label 26 chars, min 4 sections, 90 px scroll-spy offset (`cekmece.js:17,22,32`); confirm timeout 4000 ms (`formlar.js:59`); click-lock window 600 ms (`yenile.js:30`); sibling bar width `|v|/2` % (`ogul.js:125`); matrix colour `|v|×0.7` % and header truncation 8/4 chars (`panteon.js:121,123`); Roman numerals only I–X (`tanri.js:72`); bulk log 200 lines and 1.5 s refetch (`gorsel-uret.js:150,185`).
12. **Number formatting inconsistencies:** decimal comma by `String(x).replace('.', ',')` (`varlik.js:127,184`, `tanri.js:31`) vs `fmt()` elsewhere; "1’den az" special case for faith (`tanri.js:49`, `panteon.js:86`).
13. **Inconsistent print/book links:** `/kitap?varlik=<id>`, `/kitap?ogul=<id>`, `/kitap#y-<id>`.
14. **Feature asymmetry:** foreign-god bonds are read-only (no create/break), son page lacks Wrath/Archive/Tags; creator note saves manually while entity note autosaves.
15. **Hidden-field typing:** hidden inputs without `data-sayi` send strings (`yut:"1"`, `kaldir:"1"`, `ogul_id` in rite/patron selects rely on server coercion or transforms).
16. **`hedef` transform ignores type filter:** `FORM_DONUSTUR.hedef` (`varlik.js:514`) resolves any entity with that name (first match), so two entities with the same name can resolve to the wrong one (e.g. move/command/soul-bind targets); datalists show world labels but values are bare names.
17. **Full re-render on every refresh:** drawers rebuild their whole HTML string after every action and many SSE events (relying on keyed diffing); heavy for large entities (all chronicle entries, all bonds, all images inline).
18. **Drawer has no loading state:** non-silent open clears nothing until data arrives, then wipes and repaints; slow requests look unresponsive.
19. **`openDrawer` history unbounded** and in-memory; no URL hash/deep-link for drawers.
20. **Icon inconsistencies:** dead marker is both a "†" text glyph and an icon chip; favourites use an inline SVG (`varlik.js:454`) while everything else uses `ic()`.
21. **Mixed language model naming:** model badge shows raw capitalised id; Opus/Sonnet/Haiku names leak into UI.

#### Cosmos and Map

**Cosmos (views/kozmos.js):**
- kozmos.js:23 — `KOZMOS` carries dead fields: `imza`, `tf`, `zaman`, `tween`, `konum`. `KOZMOS.imza=''` is written after every action (lines 428, 438, 488, 557, and akis.js:361) but never read. It is a leftover cache-busting mechanism that does nothing.
- kozmos.js:58 vs :371 — `YILDIZ_TURLERI` is defined twice. The local copy in the "Ignite a star" form shadows the export and omits "nabız yıldızı" (pulsar), so a pulsar cannot be created there but can be selected when editing. The server has a third list (src/kozmos.js:72). Use one shared enum.
- kozmos.js:24 — `KOZMIK_AD` has no `tutustur` or `sefer` labels; those labels are hard-coded at their buttons. The icon map in `kozBtn` (line 236) covers only 4 keys.
- **Colour tables duplicated and inconsistent between 2D and 3D:**
  - stars: `YILDIZ_RENK` (kozmos.js:76) vs `YILDIZ_TUR` (kozmos3d.js:6); e.g. dead star #9aa3ad vs #7a7f86, black sun #6a4a8a vs #d0894e;
  - routes: `YONTEM_CIZGI` (kozmos.js:79) vs `YONTEM` (kozmos3d.js:31); e.g. bridge #e8ad48 vs #f2b850, swallowing #dc735d vs #e0604a.
  
  The legend (2D table) therefore does not match the 3D ribbons exactly.
- kozmos.js:155 vs kozmos3d.js:48 — two different `h01` hash functions, so world angles differ between 2D and 3D.
- kozmos.js:90–93 — `ROTA_DURUM` has both `coktu` and `cokmus` (a legacy synonym). `rotaDurumu` falls back from `aktif`. kozmos.js:306 still reads the legacy `r.aktif` / `r.kapali_son` instead of `rotaAcik`. kozmos3d.js:522 re-implements open/closed detection a third way.
- kozmos.js:134 — the voyage "under way" chip uses class `acik-cip`, unlike the other status chips (`st-*` / `c-*`).
- kozmos.js:477 — magic 650 ms `setTimeout` between the camera flight and the tab switch (not tied to the flight's real duration, which is 1.1–2.4 s).
- kozmos.js:542–558 — `FORM_DONUSTUR.federasyon` and two `document` listeners are registered at module top level, outside `kur()`, so they register at import time. The comment says everything runs in original order inside `kur()`.
- kozmos.js:415 — `[data-kacik]` scroll target chosen by a ternary on the id (`Iklim` vs `Kaynak`). Fragile.
- kozmos.js:162 — magic 2D layout numbers (520, 300, 70+46k, 20+9k, 240, padding 110/90). Moons whose parent is not placed within 3 passes are silently dropped.
- kozmos.js:301–302 — progress bar has a minimum 4% hack.
- kozmos.js:237 — world id 1 is special-cased ("first world cannot be forgotten") in several places (here, 273). Make it an explicit `is_home` flag.
- **Many texts embed rule keys and Turkish rule-location strings** (e.g. "Dünya kuralları → Kozmos ve seyahat → Gezegen hizalanması") into tooltips. The rebuild should link to the settings screen instead.
- **Inline styles in templates:** the tutum bar width (line 38), `--dc`, the disc gradients.

**Cosmos 3D (kozmos3d.js):**
- kozmos3d.js:576–577 — the "+N more sons" overflow is appended **twice**: once as a `.k3d-ogul-fazla` chip and once as a `.k3d-alt` span. Visible duplicate.
- kozmos3d.js:55–87 — the whole component CSS is a JS string injected into `<head>`, with its own hard-coded colours and font stacks duplicating design tokens.
- kozmos3d.js:82 — `.k3d-yardim{max-width:calc(100% - 240px)}`: magic number reserving space for the legend.
- kozmos3d.js:72 — tooltip `z-index:3` within the root. Floating Cosmos panels sit above it (stacking relies on DOM order).
- kozmos3d.js:533 — an inline vertex shader string for the gate vortex, outside the shader module.
- Picking is screen-space only (no raycast). Routes are sampled at 48 segments per route per pointer-move. That is O(routes×48) projections on every mouse move.
- Label sizing reads `offsetWidth` and `offsetHeight` (forces layout); it is cached but reset on font load.
- `fmt` uses `tr-TR` number formatting (kozmos3d.js:52), and the tooltip texts are Turkish.

**Map (views/harita.js, harita-gen.js):**
- harita.js:122 — `yerelYaz('haritaDunya', id)` is called twice (also inside `haritaDunyaKaydet`).
- harita.js:324 — the full-render signature is `JSON.stringify(data)` of the entire map payload, plus the layer settings and size, on every render. Expensive for large worlds.
- harita.js:72–88 — `yol()` is Dijkstra with a linear-scan open list (O(N²)) run once per road and route on every scene rebuild. harita.js:50–55 — `ortakKenar` intersects polygon vertex lists per edge pair. Both are slow on big maps. Precompute them.
- harita.js:289, 570 — timers stored as properties on functions (`haritaBagla._t`, `renderHarita._ad`).
- harita.js:455 — `d.moved !== false` is always true (`moved` is never set); a dead condition.
- harita.js:546 — the note click handler references `tf`, which is declared later (line 564). It works only through closure timing.
- harita.js:556 — "unexplored" side labels use a magic 0.04 offset and a font size 18/k0 that scales with zoom (not screen-constant like the other labels).
- harita.js:562 — the star-of-epoch badge is built by string-replacing the icon's `class="ic "` attribute to inject width/height (an icon-markup hack).
- harita.js:512 — the type icon is embedded by regex-stripping the outer `<svg>` of the icon string.
- harita.js:127 — the compass "K" letter (Kuzey = North) is a hard-coded Turkish label. Use "N".
- harita.js:466, 515 — magic font sizes (9 + √size×0.5 clamped 12–22; tier sizes 10/11/12.5/14/14.5); label visibility zoom thresholds 1.3 and 1.6; drag threshold 2 units; click distance 4.
- harita.js:396–399 — layer alpha values hard-coded per mode (0.2 + pay/500, 0.42, 0.3).
- The legend lists the settlement thresholds from rules, but tier assignment prefers the server's `kademeler`, so they can disagree.
- The client recomputes the whole procedural map that the server already computed (`bilgi`, `kapsam` are sent but the client uses its own `h`), and the client is also the source of `yeniXY` and `tasinan` server-side via the shared module. The rebuild should compute geometry once (server) and ship cell polygons or tiles, or share one implementation.
- `window.d3` and `window.gsap` are globals from CDN script tags. Without d3 the map is unusable.
- harita-gen.js:4 — `SU_DESEN` contains `okyanus` twice. Water/dry detection by Turkish name regex (see LANGUAGE-SPECIFIC above).

**LANGUAGE-SPECIFIC: drop or replace:**
- **Decimal-comma formatting** via `String(x).replace('.', ',')`: `yorungeYaz` (kozmos.js:29), the time factor (238), the horizon ratio (292), the scale bar (harita.js:587). Also `toLocaleString('tr-TR')` in `fmt`, `localeCompare(…, 'tr')`, `toLocaleUpperCase('tr')` and `toLocaleLowerCase('tr')` in the region labels and search. Replace with an `Intl.NumberFormat('en')` / locale-neutral helper.
- **Turkish case suffixes glued to numbers or names without vowel harmony:**
  - "Ç{n}'de çıktı" (kozmos.js:306) and "Çağ {n}'deki dünya" (harita.js:243). These are locative "-de" after an apostrophe and are wrong for many numbers ('te/'da/'ta).
  - "{ad} dünyasının", "{ad} yıldızının etrafında", "{ad} ayı" (possessive -ı/-sı) in kozmos.js:242, 264, 276.
  - "`{n} dünyanın` / `dünyaların`" (genitive switch, kozmos.js:65).
  
  These exist only to make Turkish grammatical. English templates replace them ("set out in Epoch n", "the world in Epoch n", "moon of X").
- **Water-region detection by Turkish words** (harita-gen.js:4, 32). Replace with an explicit terrain/water flag.
- **Map units:** "fersah" (league), and the label "keşfedilmemiş" (unexplored). Translate.
#### Live feed, Chronicle, Network, Atlas, Languages, Gallery, Goals

**views/akis.js**
- :28 `ekli()` regex-rewrites every text node of every feed line with `ekDuzelt` (Turkish suffix fixer) — LANGUAGE-SPECIFIC, drop; also fragile HTML regex (`/>([^<]+)</g`) that can touch attribute-less text in odd markup.
- :52 actor category inferred by regex on CSS class and Turkish words ("Kader", "kronikçi") in the HTML — replace with explicit category per kind.
- :57 magic cap 500 lines; :41 160 px "near bottom" threshold; :403 220 ms tone throttle; :387 fixed 2 s reconnect without backoff/jitter; :137 5-min measurement cache — all hard-coded (the project rule says tunables belong in settings).
- :102 `OKUMA` set must be kept manually in sync with server `OKUMA_ARACLARI` (comment admits it). Server should flag reading tools.
- :118 mortal-agent events reuse `ogul_ad` for the mortal's name; confusing payload contract.
- :144/:147/:156 ETA matches server step labels by Turkish lowercase prefixes (`toLocaleLowerCase('tr')`, "oğul turu", "kader", …) — LANGUAGE-SPECIFIC coupling; use step ids.
- :154 `dkYaz` Turkish duration strings ("1 dk'dan az", "~N dk") with apostrophe suffix — LANGUAGE-SPECIFIC.
- :183 top-strip text built by reading other DOM nodes' `textContent` and `.replace(/^ ·/, '')` — string surgery on rendered text.
- :213 Turkish suffix in "geçen çağ … sürdü" composed by concatenation; tooltip lines rely on Turkish word order.
- :247–249 two parallel lookup tables of busy-kind labels (title vs state pill) that disagree (`suret` only in one, different casing) — unify into one table.
- :340 success tool results hidden by Turkish prefix regex (`DÜNYA|#\d|UZUN|oğul#|Sonuç yok|SEN:`) — LANGUAGE-SPECIFIC hack; server should mark "silent" results.
- :348 `motor_not` checks `e.etiketler` for `alamet`, but the server never sends `etiketler` → omen styling is dead; :317 `motor_bilgi` and :347 `tanri_isareti` handlers are dead (never emitted).
- :360 achievement detection also by Turkish title prefix `/^Başarım:/` and strips it — LANGUAGE-SPECIFIC.
- :414/:441–444/:448 inline SVG icons hard-coded here instead of the icon set (`ic()`); icon inconsistency.
- :435 category button labels truncated to the first word (`ad.split(' ')[0]`) — gives "Gemiler" for "Gemiler ve yolculuklar"; LANGUAGE-SPECIFIC truncation hack.
- :525–530 Genesis form submit handler lives in the live-feed module; :531 global window resize handler for other tabs also lives here (misplaced responsibilities).
- :379 journal replay suppresses side effects via a global mutable flag `G.geriYukleniyor` checked in dozens of places — error-prone; prefer rendering restored events through a pure formatter.
- Stop button state (:416–424) fights with the global two-click confirm by checking `dataset.onaylandi` before overwriting innerHTML.

**views/kronik.js**
- :20–27 big hard-coded Turkish type→label map; types missing from it fall back to humanized code (the comment notes earlier raw-code leaks). Server should send labels.
- :30 strips `[iplik#N]` markers client-side with a regex and runs `ekDuzelt` on every entry — LANGUAGE-SPECIFIC.
- :78 age of a server search result parsed from display text "Ç5"/"Çağ 5" — LANGUAGE-SPECIFIC hack; server should return `cag`.
- :199 entries for search results are produced by string-replacing the output of `entry()` (`.replace('<div class="entry', …)` and `.replace(/<\/div>$/, …)`) to inject attributes and a bookmark button — brittle HTML surgery.
- :163 option label truncates age names to 28 chars (`slice(0, 28)`) — magic number, no ellipsis.
- :221 local search compares both raw and `ekDuzelt`ed text with Turkish lowercase.
- :254 type chips in a horizontally scrolling row with no indication of overflow.
- :271 220 ms debounce hard-coded; :102 concurrency 3 hard-coded.
- :296–302 scroll listener attached to `#main` once per view lifetime and never removed; age strip auto-centering uses offset arithmetic.
- :245 current age is rendered only if it already has entries; otherwise the strip omits it (no visible "ongoing" age in an early chronicle).

**views/ag.js**
- :18 link groups are hard-coded lists of Turkish relation codes; :406 the "yolculuk" group is injected later in `kur()` (order dependency). Move to server metadata.
- :22 `bagAd` mixes local overrides with `G.K.BAG_ETIKET`.
- :100–102 `agYolBul` sends any node id to `/api/yol`, but the server only accepts `v<id>`/`o<id>` → paths involving worlds (`w`), the creator (`t1`) or foreign gods (`y`) fail with a 400 toast.
- :152/:172 "Full repair" button has its own two-step confirm (`dataset.onayli`) AND `data-onay`, so the global capture-phase confirm handler (core/formlar.js) intercepts first: in practice it takes four clicks and the label flickers between two confirm texts. Use one confirmation mechanism.
- :145 decimal comma formatting via `String(x).replace('.', ',')` — LANGUAGE-SPECIFIC.
- :186 change detection via `JSON.stringify` of the entire graph on every render (expensive on large graphs).
- :264, :294–300, :302, :323, :356–358, :363, :382 many magic layout/force/label numbers (radii 16/6/3, distances 36/240/70/80, strengths, charge −260/−150, 0.6 known-position threshold, alpha 0.25, label grid 48 px, zoom 0.15–5, label zoom thresholds 0.6/0.9) not in settings.
- :332 path glow colour hard-coded `rgba(232,173,72,.6)` instead of a token.
- :277 if `window.d3` is missing the tab silently shows an empty canvas (no error state).
- :381 tooltip element created lazily with classes shared with 3D (`ag3-ipucu ag-ipucu`); positioned with manual clamp using `offsetWidth`.
- :389 tooltip is mouse-only; no keyboard access to nodes on the canvas (accessibility gap).
- :58/:66/:98/:194 node lookup by exact lowercase name — duplicate names resolve to the first match.

**views/ag3d.js**
- :14–16 runtime imports from esm.sh CDN (requires internet in a local app; pinned old versions due to three 0.170).
- :28 `soldur` blends toward a hard-coded `[15,17,22]` background rather than the theme token; light theme would look wrong. :82, :103, :167, :169, :175 more hard-coded hex colours (`#ece6d8`, `#e8ad48`, `#a9dccb`, `#262a31`, `#ffd27a`, `#bcd6f5`).
- :24 home-made double-click detection (350 ms) because the library lacks dblclick.
- :157 rAF loop runs forever after first creation (even when paused/hidden), checking only identity.
- :154 ResizeObserver never disconnected.
- :226 long hint text line in the control strip overflows on narrow screens.

**views/atlas.js**
- :166/:199 world `<select>` is rendered, filled and kept in sync but permanently hidden (dead control).
- :17 favourites filter, creator filter and sort direction not persisted, while sibling filters are — inconsistent.
- :65 auto-open logic driven by string prefixes of keys (`g:`, `w:`, `y:`, `k:`, `o`) and mixed number/string keys (`atlasAnahtar`) — fragile key scheme.
- :91 son stars rendered as repeated "★" characters (icon inconsistency vs icon set).
- :84 status badge shows the raw status code (`esc(v.durum)`, e.g. "olu", "gerceklesti") instead of a label.
- :321 change detection via a huge `JSON.stringify` signature of all entities on every render.
- :17 page size 40 hard-coded.
- :30 highlight only marks the first occurrence; Turkish-locale lowercase index can misalign with original string for special characters (İ/ı) — LANGUAGE-SPECIFIC.

**views/grafik.js**
- :13 `kisa()` Turkish compact numbers ("mn", "bin", comma decimal) — LANGUAGE-SPECIFIC.
- :17, :27, :40, :43 magic margins, max 8 x-labels, 12 px label spacing, 11-char series label truncation without ellipsis.
- :85 missing son "existence" silently defaults to 60 (duplicates a rule default).
- Tooltip is mouse-only; no keyboard/touch support.

**views/diller.js**
- :25 level → rarity-class mapping as a hard-coded 10-element array.
- :52 average translation time found by matching a step name with `/çeviri/i` — LANGUAGE-SPECIFIC.
- :55 client works around server sending "#null" coiner names (regex) — fix server.
- :141 the language page button and search input share a row; long language names overflow (`kes` truncation class used elsewhere but not here).
- :143 dictionary table rendered fully into DOM up to the limit (150 + 300 per click) — no virtualization.
- :148–160 event handlers rebound on every redraw.
- :12–16 "who can create" sentence assembled from rarity names with Turkish grammar ("ve üstü", "Yalnızca …") — LANGUAGE-SPECIFIC phrasing.

**views/galeri.js**
- :20 tolerant parsing of three possible response shapes for `/api/galeri/eksik` (array, `.liste`, `.kayitlar`) — contract drift; fix the API.
- :14/:15 duplicate page-size constants (`GALERI.sayfa` initial 60 and `GALERI_SAYFA` 60); :41 "12 more" hard-coded.
- :52 subtitle exposes an internal folder path (`data/gorseller`).
- :57 world/god captions use `<a class="link">` without href (keyboard-inaccessible).
- :58 `&nbsp;` placeholder to keep caption height when no title.

**views/hedefler.js**
- :65 son `itibar` sometimes a JSON string, sometimes an object — parsed defensively in the UI.
- :100–102 opportunity text post-processing (ALL-CAPS heading → sentence case, shouting words lower-cased with `tr` locale) — LANGUAGE-SPECIFIC hack around prompt-oriented server text; server should send structured title/body for the UI.
- :141 server opportunities filtered by Turkish regexes to avoid duplicates of the to-do list — LANGUAGE-SPECIFIC hack.
- :148 inline `style="width:4.5em"` on the awaken count input.
- :39 scenario history labels map local; :36 `data-onay` confirm inside a `form[data-post]` (form-level confirm) vs button-level elsewhere — two confirm mechanisms.
- :50 sentence about council frequency built inline in an IIFE inside a template.
- :69 `grid-column:1 / -1` inline style for group rows.

**core/imler.js**
- Bookmarks are browser-local while favourites are server-side, so they don't sync between browsers and are merged in one drawer — consider storing bookmarks server-side in the rewrite.
- :12 silent cap at 200 bookmarks (oldest dropped without notice).

---

## Open questions and decisions for the rewrite (frontend)

Verified while writing (no longer open): the son-chat reply is `{cevap, tavir, sadakat, degisim}` (see `11-api.md` §2.6); entity-detail fields `derinlik` (object), `favori` (0/1), `kisisel_not`, `arsiv`/`arsiv_sebep`/`son_anma`/`onem` (importance spread) and `tur_ap` were confirmed against a live response; every god action is ledger-wrapped server-side, so the Undo toast is always backed by a ledger page.

To decide:

1. **Light theme.** The old app is dark-only (plus a high-contrast switch). Decide whether the new design system ships light + dark.
2. **One canonical palette for worlds.** The 2D and 3D cosmos use different colour tables and hash functions, so the same world looks different in each view; the map has its own terrain colours in JS. Pick one source of truth (world-type palette from the server `turler` table).
3. **Where map geometry is computed.** `harita-gen.js` runs in the browser *and* is imported by the server (`src/harita.js`), which persists computed positions. Recommend: compute once on the server (Python port), ship geometry to the client.
4. **Typed confirmation tokens** in English: `RESET`, `RESTORE`, `REPLACE`, `MERGE` (or "type the world name").
5. **Dead realtime kinds**: `motor_bilgi`, `tanri_isareti` and the omen branch of `motor_not` are handled by the UI but never emitted. Emit them (omens deserve visual emphasis) or drop.
6. **Path finder scope**: `/api/yol` accepts only entity/son ids; "how are these connected?" fails for worlds, the creator and foreign gods. Extend to all node types.
7. **Settlement tier thresholds**: the map legend shows tier thresholds from rules, while each settlement's tier comes from the server's `kademeler`; they can disagree. Legend should be derived from the same server data.
8. **World Rules editor format**: single giant form (≈3,300 inputs) vs. searchable, virtualised table with per-group routes. Recommend the latter.
9. **`/api/kozmik/ruh` (spirit possession, cost 15)** is reachable from the entity page only; confirm it should stay there.
10. **Double confirmation** on "Full network repair" (≈4 clicks). Use one confirmation pattern everywhere.
11. **Mortal-agent events** reuse the son-name field; adopt a neutral `actor {type, id, name}` in the event contract.
12. **Turkish-grammar helpers** (`dil.js`, `ekDuzelt`, suffix metadata `ek`, `/api/ek`, the name-linking suffix regex, prefix sniffing of tool results in the feed) are all LANGUAGE-SPECIFIC and not ported; English needs only possessive `'s` handling, and none of it should be needed in the UI if the server returns structured data.
