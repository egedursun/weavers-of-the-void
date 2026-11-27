# 10 — Epoch Pipeline, Concurrency, Events, Resume, Backups, LLM Retry Policy

Source of truth (old repo, read-only): `src/epoch.js` (whole file), plus the pieces it depends on:
`src/llm.js` (retry/timeout/continuation), `src/agents.js` (`sonTuru`, `kaderVeKronik`, `bekleyenleriAdlandir`,
`halklarinSesi`, `kayipKronikler`, `eksikleriTamamla` — orchestration only; their prompts are in 08/09),
`src/olumluler.js` (`ajanAdaylari`, `olumluTuru`), `src/sim.js` (`dunyaMotoruNefesli`, `cagGecisiNefesli`),
`src/db.js` (`txNefesli`, `yedekAl`, backup rotation, `checkpoint`, `planIstatistikleri`), `src/world.js`
(`yilAraligi`, `turCtxYaz/turCtxOku`, `modelFor`), `src/olcum.js` (metrics/ETA), `src/defter.js` (ledger/undo),
`src/bildirim.js` (notifications), `src/akis.js` (stream categories), `src/toplu.js` (bulk deepening),
`src/oyuncu.js` (`ogullariDagit`), `src/ufuk.js` (`sezgileriIsle`, `sezgiKurtar`), `src/onarim.js`, `server.js`
(routes, SSE, startup).

Naming used in this document (Turkish original in parentheses once):

| English | Turkish | Meaning |
|---|---|---|
| epoch / age | çağ | One simulation round. Integer counter `world.epoch` (`dunya.cag`). |
| year | yıl | `world.year` (`dunya.yil`); each epoch spans `ZAMAN.cag_yil` years (`CAG_YIL`, other spec). |
| son | oğul | A god card (LLM agent, tools). |
| mortal agent | ölümlü ajan | A mortal-side record (people, settlement, faction, cult, mortal, intelligent species) that acts as an LLM agent with its own tool server. |
| Fate | Kader | The judge agent; also does naming and the network repair. |
| chronicler | kronikçi | Writes the epoch narrative. |
| world engine | dünya motoru | Deterministic, LLM-free simulation (`sim.js`). |
| epoch transition | çağ geçişi | Deterministic end-of-epoch growth/belief/essence/sky step that increments the epoch. |
| busy lock | meşgul (`mesgul`) | Global single-flight lock for world-mutating LLM operations. |
| content job | içerik işi (`paralelIs`) | Bounded-concurrency background job writing only to its own record. |
| ledger | Kader'in defteri (`defter`) | Per-tool-call undo journal. |
| live stream | canlı akış | Event bus → SSE → UI. |
| creator / god / player | tanrı / yaratıcı | The player. "Essence" (`tanri_oz`) is the player's currency. |

Agent functions are referenced by old name + English name (detailed in 08/09):
`sonTuru` → **son_turn**, `olumluTuru` → **mortal_turn**, `kaderVeKronik` → **fate_and_chronicle**,
`kronikiTamamla` → **complete_chronicle**, `halklarinSesi` → **voices_of_peoples**, `cagOlaylari` → **epoch_events**,
`bekleyenleriAdlandir` → **name_pending_records**, `eksikleriTamamla` → **complete_missing**,
`kayipKronikler` → **missing_chronicles**, `vahiy` → **revelation**, `derinlestir` → **deepen**,
`destanYaz` → **write_epic**, `tanriDestani` / `tanriDerinlestir` → **creator_epic** / **creator_deepen**,
`yabanciDerinlestir` → **deepen_foreign_god**, `halklariUyandir` → **awaken_peoples**,
`eksikPromptlar` → **missing_image_prompts**, `kaderBagOner` → **fate_suggest_bonds**,
`ilgiliAdlandir` → **name_related_bonds**, `cagir` → **summon_son**, `tanriSureti` → **creator_portrait**,
`konseyTopla` → **convene_council**, `dunyaDogur` → **birth_world**, `sezgileriIsle` → **process_horizon_intuitions**,
`dunyaMotoruNefesli` → **run_world_engine**, `cagGecisiNefesli` → **run_epoch_transition**.

---

## 0. Model policy (user rule — mandatory for the new app)

**Every LLM call uses Claude Haiku. There is no fallback, escalation or per-role override to Sonnet/Opus.**

Old behaviour, for traceability only (do NOT port):
- `rules.js` `MODEL_YEDEK = 'haiku'`; `MODEL_VARSAYILAN` maps every rarity key (`yaygin…mitik`) and every job key
  (`kader`, `yaratilis`, `cagirma`, `derinlik`, `vahiy`) to `'haiku'`.
- `world.modeller` (`dunya.modeller` JSON column) let the user override a key with `'sonnet'`/`'opus'`
  (`MODELLER = ['haiku','sonnet','opus']`); `modelFor(key)` = override ∥ default ∥ `'haiku'`.
- `EFFORT = {ogul, kader, yaratilis, cagirma, derinlik, vahiy: 'low'}` was passed only when the model was not Haiku
  (Haiku does not support `effort`).
- Son turns used `modelFor(son.rarity)`; mortal turns used `modelFor('yaygin')`; Fate/chronicler/naming/voices/council
  used `modelFor('kader')`.

New app: a single constant `MODEL = "haiku"` (resolved to the current Haiku model id in config); no `modeller`
setting, no `effort` parameter, no UI model picker. Metrics still record the model string.

Auth note (old): Agent SDK used the local Claude Code login (Max subscription); `ANTHROPIC_API_KEY` was deleted from
the child env; `ENABLE_CLAUDEAI_MCP_SERVERS=false`, `CLAUDE_AGENT_SDK_CLIENT_APP=aerona/0.1`; cwd = an empty temp dir
`$TMPDIR/aerona-agents` so agents cannot see the project; `tools: []`, `settingSources: []`, `persistSession: false`,
`strictMcpConfig: true`. Agents may only use the MCP tools we register (`allowedTools: ["mcp__<serverName>"]`).
Kill switch: env `AERONA_LLM_YOK` (any value) → every LLM entry point throws `"LLM disabled"` immediately (permanent
error, never retried).

---

## 1. Concurrency model

### 1.1 Single process, single DB connection
- One Node process per world DB, enforced by a **process lock file** `<db dir>/aerona.lock` containing the PID
  (`kilitAl`): create with `wx`; if it exists and the PID is alive (`kill(pid,0)` succeeds or EPERM) → print
  "This world is already open in another Weavers of the Void process (pid N)…" and exit(1); stale → overwrite. Released on
  `exit`/SIGINT/SIGTERM/SIGHUP (after a WAL checkpoint).
- All DB writes go through one synchronous `node:sqlite` connection; JavaScript is single-threaded so DB writes are
  naturally serialized. "Parallel" in this document means *concurrent awaiting of LLM calls*; tool handlers and DB
  writes interleave only at `await` points.
- **Breathing transactions** (`txNefesli`, db.js): the world engine and the epoch transition are generator functions
  that `yield` between big steps. `txNefesli(gen, name)` opens `BEGIN` (unless already in a transaction), runs
  `gen.next()` until done and after every step awaits `setImmediate` so the HTTP server keeps answering (UI does not
  freeze); on success `COMMIT`, on error `ROLLBACK` and rethrow with message prefixed `"<name>: "`. The whole engine
  run / transition is therefore **one atomic transaction** even though it yields. (Danger: other code that writes
  while the transaction is open — e.g. a background content job finishing during the engine — writes *inside* that
  transaction and is rolled back with it if the engine fails. See §14.)
- While the engine/transition runs, the canon cache is enabled (`kanonOnbellek(true)`), disabled afterwards.

### 1.2 The busy lock (`mesgul`, "kilitle")
In-memory object `busy = {type, started_at, son_id?, son_ids?}` (`{tur, basla, ogul_id, ogul_ids}`); `null` when free.

`with_busy_lock(type, fn)` (`kilitle`):
1. If `busy` is set → throw `"Busy right now: <type>. Wait for it to finish."` (HTTP 409 via `arkaPlan`).
2. Set `busy = {type, started_at: now}`; emit `busy` (`mesgul`) event with the object.
3. Await `fn()`. On error emit `error` (`hata`) `{text: e.message}` and rethrow.
4. Finally `busy = null`; emit `free` (`serbest`).

Lock types used: `epoch` (`cag`), `son` (`ogul`, single son turn), `summon` (`cagirma`), `revelation` (`vahiy`),
`world` (`dunya`, create world), `council` (`konsey`), `awaken` (`uyandirma`), `prompt` (bulk image prompts),
`completion` (`tamamlama`, complete_missing), `genesis` (set directly by the genesis route by emitting `busy`
with `{tur:'genesis'}` — note the route does **not** set the in-memory `mesgul`; it only checks it; see §14).

The lock is **not persisted**: a crash frees it; resumability comes from persisted markers (§7).

### 1.3 Content-job pool (`paralelIs`)
For jobs that write only to their own record and may run while an epoch is running (deepen, epics, single image
prompt, creator portrait, foreign-god deepening, naming job, network repair):

State: `running: Map<key, job>` and `queue: Array<{job, start}>`, `job = {key, type, name, started_at, requested_at?}`.
Capacity `AJAN.eszamanli_is` (default 8).

`parallel_job(key, type, name, fn, {queue: allowQueue = true})`:
1. If `key` is running → throw `"<name> is already being processed; wait for it."`.
2. If `key` is queued → throw `"<name> is already queued; it will start when the pool frees."`.
3. If `busy.type == 'genesis'` → throw `"Wait while Genesis is running."`.
4. If `running.size >= capacity`: if `allowQueue == false` → throw `"At most N jobs can run at once; retry when one
   finishes."` (bulk deepen uses this to manage its own stoppable wait). Else push to queue, emit `job_queued`
   (`is_sirada`) `{job, ahead: queue.length-1, running: [...], queue: [...]}` and await until started.
   Otherwise put into `running` immediately.
5. Emit `job_start` (`is_basla`) `{job, running, queue}`; await `fn()`; on error emit `error` `{text: "<name>: <msg>"}`
   and rethrow; finally delete from `running`, emit `job_done` (`is_bitti`) `{job, running, queue}` and call
   `start_queued()`, which while `queue` non-empty and `running.size < capacity` shifts the next job, stamps
   `started_at`, **reserves the slot immediately** (`running.set`) and resolves its promise (prevents overfill).

Job keys: `v<id>:derin` (deepen record), `y<id>:derin` (deepen foreign god), `v<id>:prompt`, `o<id>:destan`
(son epic), `t:destan` (creator epic), `t:derin` (creator deepen), `t:suret` (creator portrait), `adlandirma`
(naming), `v<id>:bag` (bond suggestion for one record), `ag:kader` (network repair).

### 1.4 Bounded worker pool helper (`havuz`)
`pool(items, n, fn)`: copy items to a queue; start `min(n, len)` workers, each loops `while queue: await fn(queue.shift())`.
Used for sons (phase 1), mortals (phase 2) and auto-deepening.

### 1.5 Concurrency limits summary

| Where | Limit | Source |
|---|---|---|
| Son turns in phase 1 | `max(1, AJAN.ogul_paralel)` (default 2) | epoch.js |
| Mortal turns in phase 2 | `max(1, world.olumlu_paralel)` (world setting column, default 1) | `dunya.olumlu_paralel` |
| Tool calls inside one agent turn | strictly sequential (promise chain per turn) | llm.js `araclariSar` |
| Content jobs | `AJAN.eszamanli_is` (8) | epoch.js |
| Auto-deepening workers | `max(1, eszamanli_is − AJAN.oto_pay)` | epoch.js |
| Fate: main judgment ∥ chronicler | 2 concurrent calls (`Promise.allSettled`) | agents.js |
| Fate: overflow judgment batches | `KADER.hukum_paralel` (3) at a time | agents.js |
| Naming batches | `ADLANDIRMA.paralel` (4) at a time | agents.js |
| Bulk deepening | `TOPLU.eszamanli` (1) workers, each goes through the content pool with `{queue:false}` | toplu.js |
| Busy-lock operations | exactly 1 | epoch.js |

---

## 2. Entry points that start or touch an epoch

| HTTP | Function | Lock | Notes |
|---|---|---|---|
| `POST /api/cag/tamamla` ("complete the epoch") | `cagiTamamla` → `cagIc` | `epoch` | Runs in background; HTTP answers 202 `{tamam:true}` after one `setImmediate`, or 409/404 if the promise already rejected synchronously (`arkaPlan`). |
| `POST /api/cag/durdur` ("stop the epoch") | `cagiDurdur` | — | 409 "No epoch is running" if `busy.type != 'epoch'`. |
| `POST /api/ogullar/:id/hareket` ("son acts now") | `tekOgul(id)` → `son_turn` | `son` | Single son turn outside the epoch; sets `busy.son_id`. |
| `GET /api/cag/tahmin` | ETA (`cagTahmini`) | — | §10.4. |
| `GET /api/olaylar` | SSE stream | — | §10.2. |
| `GET /api/gunluk` | last `SUNUCU.gunluk_api` (300) events from the in-memory ring | — | §10.3. |
| `GET /api/dokum?cag=` | per-epoch statistics diff from `cag_istatistik` | — | §11.3. |
| Startup | `E.tamamla()` after `SUNUCU.tamamla_gecikme` ms (1500) | `completion` | Skipped if LLM disabled, `AERONA_TAMAMLA=0`, or read-only exploration mode. |

The UI shows "Epoch N was left half-done (phase k / gods' turn); 'Complete the epoch' resumes it" when
`epoch_state()` (§7) is non-null (`/api/durum.yarim_cag`, `firsatlar`).

---

## 3. Epoch lifecycle — `cagiTamamla` / `cagIc`

Phase numbering (`ASAMA`): `sons=1, mortals=2, engine=3, fate=4, transition=5`; `PHASE_COUNT = 5` (shown as
"phase n/5"). Phase 0 (son distribution) is not counted.

### 3.0 Wrapper (`cagiTamamla`)
```
require world exists (else "No world")
with_busy_lock('epoch'):
    STOP = false                       # flag cleared only after the lock is acquired, so a second request that
                                       # fails with "busy" cannot erase a pending stop request
    state_ref = null; save_ref = noop
    try:
        return await epoch_inner(bind=(state, save) => {state_ref=state; save_ref=save})
    except e:
        if not e.is_stop: raise
        save_ref()                     # persist cag_durum
        emit system "Epoch N stopped (after phase k | during the gods' turn). 'Complete the epoch' resumes it."
        return {stopped: true, phase: state_ref.phase ?? 0}
    finally:
        STOP = false
```

### 3.1 Pre-step: complete_missing
`await complete_missing(emit)`; errors are caught and emitted as `error "Completion: <msg>"`; the epoch continues.
What complete_missing does (orchestration; prompts in 09), in order:
1. `eskiBekleyenleriCoz` — resolve orphaned pending long jobs (§7.4); for each refunded one emit system
   "<son>: the cost of the half-finished birth was refunded."
2. `missing_chronicles` — for up to `KADER.kayip_kronik` (3) past epochs that have chronicle lines but no
   `caglar.anlati`, call the chronicler (timeout `KADER.kayip_sure` 300 s) and upsert `caglar`; then for up to
   `KADER.kayip_dunya_bolum` (2) past epochs whose per-world sections (`caglar_dunya`) are missing in a multi-world
   cosmos, write only the missing sections. Errors per epoch → `error` event, continue.
3. If world has no creator portrait prompt → creator_portrait.
4. For every son lacking `gucler` (powers) or `varolus` (existence) → structured call (key `cagirma`) to fill powers,
   existence and portrait prompt.
5. If no canon `people` (`halk`) exists → awaken_peoples(`UYANIS.ilk_halk` = 2).
6. If any record lacks `gorsel_prompt` → missing_image_prompts(`ICERIK.prompt_parti` = 24).
7. If any world/star/foreign god lacks an image prompt → missing cosmos image prompts.
8. If pending (unnamed) records exist → name_pending_records.
9. For every foreign god without `derinlik` → deepen_foreign_god (emit `foreign_god_deepened` per success).
10. If no `gok` (sky body) record exists → revelation of the first sky body and set `world.epoch_star`.

### 3.2 Resume decision and the epoch-state record
```
w = get_world()
state = parse(w.cag_durum) or null        # JSON column dunya.cag_durum
resuming = is_half(state, w)              # state != null and state.epoch == w.epoch and (state.phase > 0 or state.started)
if not resuming: state = {epoch: w.epoch, phase: 0}
save = () => UPDATE dunya SET cag_durum = json(state)
bind(state, save)
```
Epoch-state JSON (`cag_durum`) fields:

| Field | Turkish | Type | Meaning |
|---|---|---|---|
| `epoch` | `cag` | int | Epoch the state belongs to (stale state from an older epoch is ignored). |
| `phase` | `asama` | 0..5 | Highest completed phase. |
| `started` | `basladi` | 1 | Backup taken and distribution done (written right after the backup). |
| `agents` | `ajanlar` | int[] | Mortal agent record ids chosen for this epoch (chosen once). |
| `engine` | `motor` | string[] | World-engine notes (raw lines) — saved in the same transaction as the engine's writes. |
| `fate` | `kader` | 1 | Fate judgment + chronicle processed. |
| `voices` | `ses` | 1 | voices_of_peoples was attempted (set *before* running). |
| `council` | `konsey` | 1 | Automatic council attempted (set *before* running). |

If resuming: emit system "Epoch N was left half-done; everything after phase k continues where it stopped." or
(phase 0) "Epoch N was interrupted during the gods' turn; the turn continues with the remaining sons."

### 3.3 Pre-epoch backup (fresh epochs only)
```
try: file = backup(label="cag<N>"); emit system "A backup of the world was taken before Epoch N started (<file>)."
except e: emit error "Backup could not be taken: <msg>"     # epoch continues anyway
state.started = 1; save()
t0 = now
phase(no, name) = emit phase {no, total: 5, name, elapsed_s: round((now - t0)/1000)}
```
Backup algorithm in §9.

### 3.4 Phase 0 — distributing sons over worlds (fresh epochs only)
Two steps, each wrapped in try/catch → `error "Son distribution: <msg>"`:

**(a) `hamisizDunyalaraOgul` — patronless worlds get a fitting son** (only if `world.ogul_dagitim == 'auto'`):
For each world `d` not forgotten (`kesif != 'unutulmus'`), ordered by id:
1. `peoples = count(canon records of type halk|yerlesim in d)`.
2. If `peoples == 0`: the world qualifies only if it is an **empty habitable world** (`bosDunyalar(epoch)`, other
   spec) whose `empty_epochs >= BOS_DUNYA.dagit_bekle` (default 1). Otherwise skip.
3. Skip if an active son already has `aktif_dunya = d`.
4. Skip if any canon record in `d` has an active `tapar` (worships) bond to a son.
5. Wanted domains = `WORLD_TYPE_DOMAINS[d.type]` ∪ every domain name (from the domain enum `ALANLAR`) that appears
   (case-insensitive substring) in `alt_tur + ' ' + name` of any canon `bolge` (region) of `d`.
   `WORLD_TYPE_DOMAINS` (`DUNYA_ALAN`): ocean→Sea, Storm, Salt; sand→Stone, Sun, Salt, Hunger; ice→Ice, Sleep,
   Bone; lava→Fire, Ash, Stone; crystal→Glass, Light, Sound; living→Life, Blood, Bone, Plant; dead→Death, Bone,
   Memory, Shadow; dream→Dream, Sleep, Madness; mirror→Glass, Lie, Light; gas→Sky, Storm.
6. Candidates: active, not chained, not protected (`tanriKorur`: the god manually assigned it less than
   `TANRI_ELI.atama_koruma` epochs ago), not already in `d`, and whose current world keeps at least
   `TANRI_ELI.dagitim_verici_en_az` (2) active sons (counting itself). Score:
   `fit = |{domain1, domain2} ∩ wanted|`, `bond = number of active worship bonds to this son from records in its
   current world`. Sort by `fit DESC, bond ASC`; take the first.
7. Move: `UPDATE ogullar SET aktif_dunya = d`. Text = "<son> turned to the world <d> (where nobody lives | which
   has a people but no god)[ and will breathe life into it][ (its domains D1/D2 suit that world)]." → chronicle line
   type `kozmik` attributed to the son; emit system "Distribution: <text>".

**(b) `ogullariDagit` (oyuncu.js) — godless inhabited worlds** (only in auto mode): for each non-forgotten world
without an active son that has ≥1 canon `halk|yerlesim|tarikat|hizip|olumlu`, pick among active, unprotected sons whose
world keeps ≥ `dagitim_verici_en_az` active sons, the one with the lowest
`bond = worship bonds in its own world + (TANRI_ELI.koruyucu_bag if it is the guardian son of its world)`; move it;
chronicle `kozmik` "<son> turned to the godless world <d>." + system event.

### 3.5 Phase 1 — the gods' turn (son turns)
```
queue = (state.phase < 1) ? eligible_sons(epoch) : []
   eligible_sons = sons where status=='active' and not chained and last_action_epoch < epoch and has_action_points
order = queue mapped to (son, ini = initiative(son)) sorted by ini DESC
   initiative = agility + cunning/2 + d(KURAL.inisiyatif_zar)*2          # d(n) = uniform 1..n
emit epoch_start (cag_basla) {epoch, order: [{id, name, ini: round(ini)}], resuming}
set_year_range(0, CAG_AKIS.yil_ogul)
phase(1, "The gods' turn (<len> sons)")
i = 0; dropped = []; running = Set()
one_son(s):
    if STOP: return                           # safe point: running turns finish, no new one starts
    emit turn (sira) {no: ++i, total, name}
    running.add(s.id); busy.son_id = s.id; busy.son_ids = [...running]
    try: await son_turn(s.id, emit)
    except e: dropped.push(s); emit error {son_id, text: "<name>: <msg> — will be retried once at the end of the phase."}
    finally: running.delete(s.id); busy.son_ids = [...running]; busy.son_id = first(running) ?? null
await pool(order.sons, max(1, AJAN.ogul_paralel), one_son)
safe_point()                                   # throws Stop if STOP
for s in dropped:                              # retried sequentially
    safe_point()
    g = get_son(s.id); if not g or g.last_action_epoch >= epoch or g.status != 'active': continue
    emit retry (yeniden) {name, attempt: 2, total: 2, reason: "turn dropped on the first attempt"}
    busy.son_id = s.id
    try: await son_turn(s.id, emit)
    except e: emit error {son_id, text: "<name> could not act this epoch: <msg>"}
busy.son_id = null; busy.son_ids = []
state.phase = max(state.phase, 1); save()
safe_point()
```
Note: on resume with `state.phase < 1`, `eligible_sons` naturally excludes sons that already acted
(`son_eylem_cag == epoch`), and a son whose turn was interrupted resumes with its persisted turn context (§7.3).

### 3.6 Phase 2 — mortals' turn
```
count = world.olumlu_sayisi ?? OLUMLU_AJAN.varsayilan (4)          # world setting column; 0 disables
if count > 0 and state.phase < 2:
    if not state.agents: state.agents = [v.id for v in choose_mortal_agents(count)]; save()
    agents = [get(id) for id in state.agents] filtered: exists, status=='canon', (last_action_epoch||0) < epoch
    set_year_range(CAG_AKIS.yil_ogul, CAG_AKIS.yil_olumlu)
    phase(2, "The mortals' turn (<len>)")
    emit mortals_start (olumluler_basla) {agents: [{id, name, type}]}
    one(v):
        if STOP: return
        try: await mortal_turn(v, emit)
        except e:
            emit error "<name>: <msg> — retrying once."
            try: await mortal_turn(get(v.id), emit)
            except e2: emit error "<name> could not act this epoch: <msg2>"
    await pool(agents, max(1, world.olumlu_paralel ?? 1), one)
safe_point()          # a stopped mortals phase is NOT marked done: resume continues with mortals that did not act
state.phase = max(state.phase, 2); save()
```
`choose_mortal_agents(count)` (`ajanAdaylari`, olumluler.js): candidates = canon records with
`(last_action_epoch||0) < epoch`, type ∈ `OLUMLU_AJAN.turler` = [people `halk`, faction `hizip`, cult `tarikat`,
settlement `yerlesim`, mortal `olumlu`, species `tur`], and species only if `stats.intelligence >= OLUMLU_AJAN.zeka_esigi`
(55). Single world → `ajanSec(candidates, count, epoch)` (other spec). Multi-world: group candidates by world (records
without world → first world); quotas by `dunyaPaylari`: worlds with a manual quota (`dunyalar.olumlu_ajan` not null)
get `min(manual, candidates)`; remaining total is split over auto worlds proportionally to candidate counts
(`floor(total*cand/sum)`, at least 1 each when `total >= #autoWorlds`, capped at candidates), leftover units to the
largest fractional remainders. Then select per world; finally append any candidate tagged `"ajan seçili"`
("agent selected", set by the player) not yet chosen.

Mortal turn persistence mirrors son turns: `varliklar.tur_cag / tur_ap / tur_ctx`; AP = `OLUMLU_AJAN.ap` (3),
`maxTurns = OLUMLU_AJAN.maxTurns` (12). After the turn: `son_eylem_cag = epoch`, `tur_ap = NULL`, the tag
`"ajan seçili"` is removed, unread dreams/manifestations marked read, final utterance written as chronicle `soz`
(max 600 chars) with ids `[v.id, ...creations]`. Events `mortal_start`/`mortal_done` (§10.5).
At turn start `borcVadeleri(epoch)` writes overdue debts to the chronicle.

### 3.7 Phase 3 — the world's own course (engine)
```
engine_notes = state.engine
if state.phase < 3:
    set_year_range(CAG_AKIS.yil_olumlu, CAG_AKIS.yil_motor)
    phase(3, "The world's own course")
    emit engine_start (motor_basla) {}
    engine_notes = await run_world_engine(epoch,
        live = n => emit engine_note (motor_not) {text: n, category: stream_category(n)},
        mark = notes => { state.engine = notes; state.phase = 3; save() })     # executed as the LAST step inside the
                                                                                # engine transaction → the "engine done"
                                                                                # marker commits atomically with the
                                                                                # engine's writes; a crash can never run
                                                                                # the engine twice for one epoch
    emit engine_done (motor_bitti) {notes: engine_notes}
safe_point()
```
The engine itself is specified in the world-engine spec. It is deterministic given RNG; it opens unnamed placeholder
records (`bekliyor = 1`, description prefixed `[Dünya motoru]`) that Fate must name.

### 3.8 Phase 4 — Fate and the chronicler
```
fate = undefined
if state.phase < 4:
    if not state.fate:
        set_year_range(CAG_AKIS.yil_motor, CAG_AKIS.yil_kader)
        phase(4, "Fate and the chronicler")
        emit fate_start (kader_basla) {epoch}
        # Fate leaves no gaps: every unnamed engine record is named before judgment (no budget, batched)
        try: await name_pending_records(emit)
        except e: emit error "Naming of unnamed records: <msg>"
        try: fate = await fate_and_chronicle(epoch, engine_notes or [], emit)
        except e:
            UPDATE dunya SET kader_borc = MIN(COALESCE(kader_borc, epoch), epoch)     # "Fate debt"
            emit error "Fate: <msg> — will be compensated next epoch."
        emit fate_done (kader_bitti) {epoch, epoch_name: fate?.cag_adi, rejected: [names], corrected: [names]}
        state.fate = 1; save()
    safe_point()          # judgment is persisted; a resumed epoch never re-runs Fate
    if not state.voices:
        state.voices = 1; save()                        # attempted once; a crash inside does not re-run it
        try: await voices_of_peoples(epoch, fate?.olaylar ?? epoch_events(epoch), emit)
        except e: emit error "Voices of the peoples: <msg>"
    safe_point()
    freq = world.konsey_sikligi ?? KONSEY.siklik_varsayilan (4)            # world setting; 0 = never
    if not state.council and freq > 0 and epoch % freq == 0:
        state.council = 1; save()                       # attempted once
        try: await convene_council({emit, caller: 'fate'})
        except e: emit error "Council: <msg>"
    state.phase = 4; save()
safe_point()              # last safe point; the transition is not interruptible
```

**Inside `name_pending_records`** (orchestration): loop: select all `bekliyor=1` records ordered by world, id, that
have been tried fewer than `1 + ADLANDIRMA.deneme` times; build batches per world (a batch never mixes worlds, max
`ADLANDIRMA.parti` (12) records), at most `ADLANDIRMA.paralel` (4) batches per round; increment tries; emit system
"<n> records born from the world's own course are being named in <b> batches (remaining <r>)."; run batches with
`Promise.allSettled`; if **all** batches rejected → throw the first reason (model really unavailable); partial
failures are retried next round. Names violating the world's dialect (`lehceIhlali`) are not applied while tries
remain (`ADLANDIRMA.lehce_denetim`), and the next round gets a warning list. When tries are exhausted: strip the
`[Dünya motoru]` prefix from the description, set `bekliyor=0` (left for deepening). Final system event
"<n> records named[; <m> temporary descriptions cleared, left for deepening]."

**Inside `fate_and_chronicle`** (orchestration):
1. Build context (`kaderBaglami`): `start = min(epoch, world.kader_borc ?? epoch)`. Records to judge = canon,
   non-pending records created by sons/mortals (`kaynak in ('ogul','olumlu')`) with `epoch BETWEEN start AND epoch`
   and (`cag == epoch` or not yet judged: `kader_notu IS NULL`). Fit into `KADER.butce_yeni` chars (each with
   pre-screen warnings); the rest is *overflow*. Still-pending records (after naming) all included; old prophecies
   within `KADER.butce_kehanet`.
2. Emit `fate_step` (`kader_adim`) "Fate is weighing N creations, naming M unnamed records; the chronicler is writing…".
3. Run **judgment** and **chronicle** concurrently (`allSettled`), each a structured call with timeout
   `KADER.kader_sure` (480 s) and `KADER.model_deneme` (3) attempts; progress events `writing` with `who` = "Fate" /
   "Chronicler"; on success `fate_step` "Fate gave its verdict (<s> s)." / "Chronicler wrote the epoch: "<name>" (<s> s)."
4. If the chronicle succeeded → `complete_chronicle` (rewrite a banned opening sentence if `KADER.acilis_duzelt`;
   write sections for skipped worlds if `KADER.eksik_dunya_tamamla`). Errors → `error "Chronicle completion: …"`.
5. If judgment succeeded and overflow exists: split overflow into batches of ≤ `KADER.butce_yeni` chars; run
   `KADER.hukum_paralel` (3) batches at a time (same criteria prompt). If any batch in a group fails: all records of
   the failed batches **and of all not-yet-started batches** become debt; `extra_debt = min(epoch of those records)`;
   stop; emit error "Fate could not weigh the remaining K creations (<msg>); it will be the next epoch's first task."
6. `debt = judgment failed ? start : extra_debt`. If judgment failed → error event "Fate could not give a verdict
   this epoch (…). Creations stay canon; Fate will weigh them next epoch; unnamed records will be named then too."
   If overflow fully judged → system "Fate weighed all N creations of this epoch." If chronicle failed → error
   "The chronicler could not write this epoch (…). The missing chronicle will be written in the next completion."
7. `kaderHukmu(...)` applies everything in one go (verdicts, rewards, threads, canon facts, prophecies, chronicle rows,
   `kader_borc = debt` written inside the same transaction). Returns `{…, rejected, corrected, pending, kader_borc,
   olaylar}`.

**Fate debt (`kader_borc`)**: integer column = oldest epoch whose creations were not judged; NULL = no debt. Written
by `kaderHukmu` (normal path) or by the epoch catch block (whole call threw). Consumed by the next epoch's context
(step 1).

### 3.9 Phase 5 — epoch transition (not interruptible)
```
phase(5, "Epoch transition: growth, belief, essence, sky")
try: words = epoch_words(epoch); if words: emit system "<n> new words entered the languages."     # cagKelimeleri
except e: emit error "Epoch words: <msg>"
try: birth_local_gods(epoch)                                                                       # §3.9.1
except e: emit error "Local god: <msg>"
notes = await run_epoch_transition()      # one breathing transaction; increments world.epoch and world.year,
                                           # writes cag_istatistik(epoch) snapshot {…world photo, kiyamet, dokum}
update_planner_statistics()               # PRAGMA optimize if sqlite_stat1 exists, else ANALYZE
set_year_range(0, CAG_AKIS.yil_gecis)     # first years of the NEW epoch
UPDATE dunya SET cag_durum = NULL
if LLM enabled: try await process_horizon_intuitions({birth_world, emit}) except → error "Sensed worlds: <msg>"
try: if pending_count(): await name_pending_records(emit) except → error "Naming of unnamed records: <msg>"
try: refill_suffix_dictionary()           # ekleriDoldur — LANGUAGE-SPECIFIC (Turkish suffix harmony): drop
if AG.oto_onar: try network_rule_repair(epoch) except → error "Network repair: <msg>"
try ledger_prune(); try notifications_prune(); try changes_prune()      # silent
emit epoch_done (cag_bitti) {epoch, new_epoch: epoch+1, summary: notes, duration_s: round((now-t0)/1000)}
try auto_deepen()                 # background, not awaited
try refresh_stale_epics()         # background, not awaited
if AG.kader_oto and LLM enabled: network_fate_repair({auto: true}) (background, errors swallowed)
return {fate, engine: engine_notes, notes}
```
`epoch_words(epoch)` (`cagKelimeleri`, dilmotoru.js — language spec): from this epoch's named canon/dead records of
word-worthy types, add new vocabulary to local languages, capped per language and in total.

`process_horizon_intuitions` (ufuk.js): for each `ufuk_sezgi` row with status `waiting`: set `processing`; if the
sensing mortal is gone → `wasted`; else birth the sensed world via `birth_world` (LLM) → `born` with
`sonuc_dunya`, emit system "<mortal>'s sensed world was born: <world>."; on error reset to `waiting`, emit error
"The sensed world could not be born: <msg>" and **stop the loop**. At startup `sezgiKurtar` resets every
`processing` row back to `waiting` (crash recovery).

#### 3.9.1 `birth_local_gods(epoch)` (`yerelTanriDogur`)
For each non-forgotten world `d` (by id):
1. Skip if `epoch - (d.olusturma_cag ?? 0) < AJAN.yerel_tanri_cag` (3).
2. Skip if a foreign god of this world exists with `status != 'dead'` OR
   `epoch - COALESCE(death_epoch, epoch) < AJAN.yerel_tanri_yeniden_cag` (5, mourning period).
3. `people` = first canon `halk` in `d`; skip if none.
4. Language = first canon `dil` (language) of `d` by id; name = `language_name(lang, seed="yerel-tanri:<d.id>",
   kind="person")` or fallback "The Sleeper of <d>" (`<d>'in Uyuyanı`).
5. Domains = first two of `WORLD_TYPE_DOMAINS[d.type]` (default Earth/Memory).
6. Insert foreign god (`yabanciTanriEkle`): name, title "the sleeping <domain1 lower-case> god of the <people> people",
   domains "D1/D2", world d, attitude 0, description "When the peoples of <d> were left godless, a figure was born from
   their fears and hopes: <name>. They whisper its name, but it has not yet awoken.", power `AJAN.yerel_tanri_guc` (30).
   Then `status='uykuda'` (sleeping), `temas=0` (no contact).
7. Chronicle `kozmik`: "In the world <d> a sleeping local god was born from the whisper of the peoples: <name>."
   (ids [people]); emit system "A sleeping local god was born in the world <d>: <name>."

### 3.10 Post-epoch background work
**`auto_deepen()`** (`otoDerinlestir`): returns [] if no world, LLM disabled, or `AJAN.oto_derin <= 0`.
1. For every foreign god without `derinlik` whose job `y<id>:derin` is not running → fire `deepen_foreign_god` job
   (not awaited, errors swallowed).
2. `ids = auto_deepen_candidates(AJAN.oto_derin)` minus ids whose `v<id>:derin` is running:
   ```sql
   SELECT v.id FROM varliklar v WHERE (v.derinlik IS NULL OR v.derinlik='')
   ORDER BY v.bekliyor,                                   -- named first
            COALESCE(v.onem,0) DESC,                      -- importance score
            (active bonds touching v) + v.guc_seviyesi * :oto_derin_guc DESC,
            v.id
   LIMIT :n
   ```
3. If any: emit system "The epoch's N most important records are being deepened in the background."; run
   `pool(ids, max(1, eszamanli_is − oto_pay))`, each worker first waits while the content pool is full
   (poll every `AJAN.oto_bekle_sn` s, at most `AJAN.oto_bekle_deneme` times — leaves room for manual jobs), then
   calls `deepen(id)` (content job; errors swallowed). Not awaited.

**`refresh_stale_epics()`** (`bayatDestanlariTazele`): if LLM enabled:
`stale_epics(epoch, n = AJAN.destan_tazele_adet)`: threshold `AJAN.destan_tazele` (8; 0 = off). Candidates:
`t:destan` (creator epic JSON `dunya.tanri_destan`), `t:derin` (creator deepening `dunya.tanri_derinlik`), and for every
non-dead son with an epic `o<id>:destan`; `age = epoch − stored.cag`; keep `age >= threshold`; oldest first; take n.
Filter out running keys. Low priority: if `running.size >= max(1, eszamanli_is − oto_pay)` skip this epoch.
Otherwise fire `creator_epic` / `creator_deepen` / `write_epic(son)` jobs (not awaited) and emit system
"<n> outdated epics are being rewritten in the background."

**`network_fate_repair({auto:true})`** (`agKader`) — content job `ag:kader` (§6.4).

**Server hooks on `epoch_done`** (server.js listener): recompute importance scores (`onemleriKaydet`), prune LLM
metrics (`olcumBuda`), WAL checkpoint (`PRAGMA wal_checkpoint(TRUNCATE)`). Notification "Epoch N finished (M min)" (§10.6).

### 3.11 Year stamping of chronicle lines (`yilAraligi`)
Global mutable `YEAR_RANGE = [from, to]` and `YEAR_EPOCH` set by `set_year_range(from, to, epoch = current)`.
For a chronicle line in epoch `c`: `base = world.year − (world.epoch − c) × EPOCH_YEARS`; if `YEAR_EPOCH` is set and
`c > YEAR_EPOCH` the range is `[0,1]` else `YEAR_RANGE`;
`year = min(base + EPOCH_YEARS − 1, max(last_year_used[c] ?? base, base + from + floor(rand × max(1, to − from) / 3)))`;
remember `last_year_used[c] = year` (monotonic within an epoch; map keeps only the last 3 epochs).
Phase ranges (defaults): sons 0–15, mortals 15–30, engine 30–45, Fate 45–49, new epoch's first years 0–4.

---

## 4. A single son turn (`son_turn`, agents.js `sonTuru`) — orchestration and resume
Prompt contents are in 09; tool semantics in 08. Pipeline-relevant behaviour:
1. `eskiBekleyenleriCoz()` (refund orphaned births, §7.4).
2. Preconditions (throw): son exists; `status == 'active'` ("<son> is <status>; cannot act."); not chained
   ("<son> is chained this epoch."); `last_action_epoch < epoch` ("<son> already acted this epoch.").
3. `half = son.tur_cag == epoch and son.tur_ap != null`. `ap = half ? son.tur_ap : action_points(son)`; if `ap <= 0`
   and not half → throw "<son> is fading; has no strength to act."
4. Turn context `ctx = {epoch, ap, messageCount:0, bondCount:0, prayed:false, creations:[], birth_fn,
   ...turn_traces(son, epoch), ...(half ? deserialize(son.tur_ctx) : {})}` — `turn_traces` rebuilds per-epoch
   counters/flags from what the son already left in the world (messages to brothers, prayer to the god, free living
   creation, life-takings, intrigues, land creation, gift, anchor choice) so a resumed turn cannot get a second free
   creature/prayer/gift. If half → `bekleyenIsiCoz` (§7.4).
5. Persist `UPDATE ogullar SET tur_cag=epoch, tur_ap=ctx.ap, tur_ctx=(half ? serialize(ctx) : NULL)`.
6. Build a fresh MCP tool server for the son (`buildSonServer`), wrapped by `wrap_tools` (§12.4) whose `save(ctx)`
   persists `tur_cag/tur_ap/tur_ctx` after every successful tool call and whose gate refuses calls if the son fell
   asleep/died mid-turn.
7. Messages addressed to the son (`mesajlar` unread) are noted, marked read only after the turn completes.
8. Emit `start` (`basla`) `{son_id, son_name, model, half}`.
9. `agent_turn` with: name "Son turn: <name>", system prompt, user prompt (+ note "Your turn was interrupted earlier;
   your deeds remain in the world. Continue where you left off." if half), `rebuild_server`,
   `is_complete = (text) => extract_utterance(text) != null` (the final message must contain a «…» utterance),
   `continuation_prompt(done, reason)` = same prompt + "=== YOUR TURN WAS CUT OFF (<reason>) === … ALREADY DONE THIS
   EPOCH: - … " — but returns null (no continuation) if the son is no longer `active`;
   `pending_job = () => running_long_job(son)`, `job_traces = () => ctx.long_jobs`,
   `maxTurns = RARITIES[rarity].maxTurns` (11/13/15/17/19/21 for common…mythic), timeout `KADER.ogul_sure` (420 s).
   All agent events are re-emitted with `son_id`, `son_name` added.
10. After: `last_action_epoch = epoch`, `emir = NULL`, `emir_mutlak = 0`, mark noted messages read, `tur_ap = NULL`
    (the `tur_ctx`/`tur_cag` stay but are ignored because `tur_ap` is NULL). Utterance → chronicle `soz`
    "<son>: "<utterance ≤900 chars>"" with ids = creations. Emit `done` (`bitti`) `{son_id, son_name, utterance,
    creations, status}`.

Tool calls are recorded in the ledger as one group per call with `who_type='o'` (§8).

---

## 5. Stopping / cancellation

| What | Mechanism |
|---|---|
| Epoch | `POST /api/cag/durdur` → `cagiDurdur()`: only if `busy.type=='epoch'`; sets `STOP=true`; emits system "The epoch will be stopped once the current step finishes; it can be resumed afterwards." Safe points: before each new son/mortal turn starts (`if STOP return` — running turns finish), after the son pool, between dropped-son retries, after phases 1/2/3, after Fate, after voices, before the transition. A safe point throws `Stop`; wrapper persists `cag_durum` and returns `{stopped:true, phase}`. **In-flight LLM calls are never aborted**; the transition (phase 5) is not stoppable. |
| Network fate repair | `agKaderDurdur()` sets global `AG_STOP=true`; loops check it between batches; emits system summary "Fate's network repair was stopped: …". |
| Bulk deepening | `POST /api/toplu/derin/durdur` → `D.stop=true`; workers finish the current record, queued waits abort ("stopped while waiting; not processed" counted as skipped). |
| Image generation | own stop route (image spec). |
| LLM call timeout | `AbortController` per call (§12). |

There is no generic cancellation token; new design should add one (§14).

---

## 6. Other long operations (outside the epoch) defined in epoch.js

### 6.1 Busy-locked operations (cost → refund on failure)
All require a world; `harca(cost, rule)` throws "This requires <cost> divine essence; you have <oz>. (Cost World
rule <rule> = <cost>.)" and deducts `tanri_oz`; `iade(cost)` adds back exactly what was taken (even if the rule
changed meanwhile).

| Function | Lock | Cost rule | Body | Event |
|---|---|---|---|---|
| `yeniOgulCagir(world_id?)` summon son | `summon` | `COSTS.cagirma` | `summon_son({world_id})`; refund on error | `new_son` `{son}` |
| `vahiy(text, type, world_id?, mechanic?)` revelation | `revelation` | `COSTS.vahiy` | text required ("A revelation needs content."); cost spent **inside a ledger group** (`who_type='t'`, tool `vahiy`), refund on error inside the same group | `revelation` `{record}` |
| `dunyaYarat({type, inspiration ≤ ilham_uzunluk, star_id, parent_world_id, new_star})` | `world` | `DENGE.dunya` | `birth_world(...)` | (birth_world emits `world_born`) |
| `konsey(topic)` convene council | `council` | `DENGE.konsey` | `convene_council({topic, caller:'god'})` | `council` |
| `olumluleriUyandir(n=2, world_id?)` awaken peoples | `awaken` | `DENGE.uyandir × ceil(n / UYANIS.tavan)` | `awaken_peoples(n, world)` | system "Awakened peoples: …" |
| `promptlariYaz()` write missing image prompts | `prompt` | — | up to `AJAN.prompt_tur` (10) rounds of `missing_image_prompts(ICERIK.prompt_parti)`, stop when a round returns 0 | system "<n> records got image prompts." / "No record lacks a prompt." |
| `tamamla()` | `completion` | — | only if something is missing (creator prompt, son powers/existence, sky body, canon people, record/world/star prompts, foreign-god depth, pending records, past epochs without narrative) and not busy | — |
| `tekOgul(id)` | `son` | — | son_turn | son events |

`world_id` validation (`hedefDunya`): null/'' → null; unknown → "No such world."; forgotten → "<d> was forgotten;
no hand reaches into the fog."

### 6.2 Content jobs (pool, §1.3)
| Function | Key | Agent | Event |
|---|---|---|---|
| `derinlestir(id, opt)` | `v<id>:derin` | deepen | `deepened` `{record:{id,name}}` |
| `yabanciDerinlik(id, opt)` | `y<id>:derin` | deepen_foreign_god | `foreign_god_deepened` `{id, name}` |
| `sureti()` | `t:suret` | creator_portrait | system "<god>'s likeness was redrawn." |
| `tanriDestan()` | `t:destan` | creator_epic | system "<god>'s epic was written." |
| `tanriDerinlik()` | `t:derin` | creator_deepen | system "<god> was deepened." |
| `destan(son_id)` | `o<id>:destan` | write_epic | system "<son>'s epic was written: <title>" |
| `tekPrompt(id)` | `v<id>:prompt` | missing_image_prompts(1, ids=[id]) | system |
| `adlandirmaIsi()` | `adlandirma` | name_pending_records; refused if busy ("Busy: <type>. The epoch does its own naming.") | — |
| `agKader({ids, related=true, auto, full}, opt)` | `v<id>:bag` (one id) / `ag:kader` | fate_suggest_bonds, name_related_bonds | `network_repair` |

### 6.3 Synchronous god actions (ledger-wrapped, `defterli`)
`ledgered(tool, fn)`: opens a ledger group `{who_type:'t', who_id:0, who_name: god name, tool, epoch}` and inside it
runs `SAVEPOINT tanri_eli; fn(); RELEASE` — on exception `ROLLBACK TO` + `RELEASE` + reset canon cache and rethrow, so
a refused action leaves no trace (including spent essence). Ledger groups with no row changes are deleted.
Tools (ledger `arac` names): `dirilt`, `tanri_can_al`, `ogul_oldur`, `emir`, `kutsa`, `yildiz`, `yukselis`,
`ceza:<type>`, `dua`, `kanon:<status>`, `varlik:duzenle`, `tanri:duzenle`, `yol:<kopar|dik|aciga>`, `sefer:geri`,
`kozmik:<action>`, `mudahale:<action>`, `oz_em:ogul|olumlu|yabanci`, `yut:ogul|olumlu|yabanci`, `hasat`,
`oldur:yabanci`, `dirilt:olumlu`, `tanrilastir`, `alcalt`, `guc_sok`, `mutlak_buyruk`, `peygamber`, `tezahur`,
`soy_laneti[:kaldir]`, `cevir`, `gazap`, `gazap:dunya`.

Precise effects (all chronicle lines are type `tanri` unless noted; texts paraphrased into English):

- **Command** `emirVer(son, text)`: dead son + non-empty text → "dead sons take no commands". `son.emir = trimmed or
  NULL`; `emir_mutlak = 0`. If set: insert message (`t`→`o`, intent `emir`), chronicle `emir` "<god> commanded <son>:
  "<text>"".
- **Bless** `kutsa(son, type, stat)` — dead → refuse. Refuse (no cost) if nothing would change: essence full, HP full,
  stat already 100, existence already 100. Types: `oz` cost `COSTS.kutsa_oz`, `oz = min(oz_max, oz + kutsa_oz)`;
  `can` cost `COSTS.kutsa_can`, HP = max; `stat` (must be a son stat key) cost `COSTS.kutsa_stat`,
  `stat = clamp(stat + kutsa_stat, 1, 100)`; `varlik` cost `COSTS.kutsa_oz`, `existence = clamp((existence ??
  CAGIRMA.varlik_baslangic) + kutsa_varlik, 0, 100)`. All: `loyalty += kutsa_sadakat` (clamp 0..100).
- **Add star** `yildizEkle(son)`: dead → refuse; target = stars+1 ≤ `YILDIZ_MAX`; requires `level >= req.level` and
  `fame >= req.fame` (`yildizSarti`, KURAL.yildiz_seviye / yildiz_un); cost `req.oz`; every stat
  `+yildiz_stat` (clamp 1..100); HP = max; chronicle `yildiz`.
- **Ascend** `yukselt(son)`: needs next rarity, stars == max, `level >= YUKSELIS.seviye`, `fame >= YUKSELIS.un`;
  cost `YUKSELIS.oz`; in a transaction: each stat = max(current, randInt(new rarity range)); rarity = next; stars=1;
  HP and essence = max; existence `+yukselis_varlik`; insert pending legend record (type `efsane`, subtype
  "ascension myth", tag "yükseliş", source `dunya`, `bekliyor=1`, power = new rarity `guc_tavan`, stats
  `{prevalence: yukselis_efsane}`, description "[World engine] <son> ascended from <old> to <new>. Mortals saw a change
  in the sky."); bond legend→son `anlatir` (tells of); chronicle `yukselis`; emit `ascension` `{son}`.
- **Punish** `cezalandir(son, type)`: dead → refuse; exile when already exiled / chain when chained → refuse.
  `rebel = will > asi_irade`. `yildirim` (lightning): cost `COSTS.yildirim`, `HP = max(1, HP − round(hp_max ×
  yildirim_can/100))`. `zincir` (chain): refuse if son already acted this epoch; `chained = true` (no cost).
  `surgun` (exile): status `surgun` (no cost). Then loyalty/anger: rebel → `loyalty −= ceza_asi_sadakat, anger +=
  ceza_asi_ofke`, chronicle adds "<son> did not bow; a grudge grew inside."; else `loyalty += ceza_sadakat,
  anger += ceza_ofke`.
  `bastir` (suppress rebellion): requires `son.asi`; cost `DENGE.bastir`; `god = bastir_taban + floor(remaining
  essence / bastir_oz_bolen) + d(bastir_zar)`; `son = will + strength × bastir_guc/100 + level × bastir_seviye +
  d(bastir_zar)`. If `god >= son`: `asi=0`, loyalty `+bastir_sadakat`, `HP = max(1, round(HP × bastir_can/100))`,
  fame `−bastir_un` (≥0), chronicle `isyan` "<god> crushed <son>'s rebellion (g – s); the rebel knelt." Else: fame
  `+bastir_basarisiz_un`, ambition `+bastir_basarisiz_hirs`, god essence `−bastir_basarisiz_oz` (floor 0), chronicle
  `isyan` "… tried to crush … but failed (g – s); the rebel's fame grew."
  `af` (pardon): requires exiled or chained or rebel ("Nothing to pardon."); exiled→active; rebel→`asi=0` + chronicle
  `isyan` "<god> forgave the rebel son <son>; the rebellion ended."; `chained=false`; loyalty `+af_sadakat`.
- **Answer prayer** `duaCevapla(msg_id, text, essence=0)`: message must be addressed to the god; already answered →
  refuse; essence must be ≥0 and ≤ `dua_oz_tavan` (error names the rule). Mortal prayer (`from_type='v'`): spend
  essence, `olumluDuasiniCevapla` (dream answer, grace, belief — creator spec), mark answered+read, chronicle.
  Son prayer: spend, `son.oz = min(max, oz + essence)`, `loyalty += (text ? dua_sadakat : 0) + floor(essence /
  dua_oz_sadakat)`, existence `+dua_varlik`, mark answered; if text insert message (`t`→`o`, intent `cevap`).
- **Canon toggle** `kanonDegistir(record, 'kanon'|'reddedildi')`: refuse same status; restoring to canon only from
  `reddedildi` (dead mortals must use resurrection). Sets status and `kader_notu` ("<god> overturned Fate's verdict and
  took this back into canon." / "<god> struck this from canon."). Reject: close currently-active outgoing bonds and mark
  `red_kapatti=1`. Restore: reopen bonds with `red_kapatti=1` or (bond epoch = record epoch and old status was rejected).
- **Edit record** `varlikDuzenle(id, fields)`: name change → global rename (`adDegistir`, all texts); `alt_tur`,
  `aciklama`, `gorsel_prompt`: non-empty → set; empty → NULL except description (cannot be emptied).
- **Edit creator** `tanriDuzenle`: `tanri_unvan/gorunus/mizac/prompt` (empty → NULL). `ogulPromptDuzenle` edits a son's
  image prompt (not ledgered). `tanriNotu(text)` stores `tanri_notu` truncated to `not_uzunluk` (not ledgered).
- **Resurrect son** `ogluDirilt`: must be dead; cost `DENGE.dirilis`; `dirilt(son, epoch, "by <god>'s hand")`.
- **Take a mortal's life** `olumluCanAl(id, {how})`: canon `olumlu` only; cost `OLUM.tanri_can_al`; `canAlmaDene(…,
  certain=true)` (death spec). **Kill son** `ogluOldur(id, {reason})`: cost `OLUM.tanri_ogul_oldur`; `aeronOgluOldurur`.
- **Route actions** `yolEylemi('kopar'|'dik'|'aciga', route, {duration})`: costs `OTESI.kopar_bedel`,
  `OTESI.dik_bedel`, `SEYAHAT.aciga_bedel`; refund on error. `seferGeriCagir(id)` recalls a voyage.
- **Cosmic actions** `kozmikEylem(action, body)`, cost `KOZMIK_BEDEL[action]`, refund on error: `yildiz` (new star;
  empty name → generated from a living language of the world, else "The N-th Star of <world>'s sky" with roman N; name
  must be ≥2 chars; type default "yellow dwarf"), `muhur` (seal gate on route), `temizle` (mend leak; requires a world
  with leak > 0 or an `dis` (outer) record — else refuse without cost), `unut` (forget world), `tutustur` (ignite star),
  `ruh` (spirit possession), `sefer` (great expedition → `{thread_id}`), `gok` (sky event; requires world, star or
  route id and validates them).
- **Direct intervention** `tanriMudahale(record, {action, type, knowledge_id})` cost `MUDAHALE_BEDEL[action]` (0 valid):
  record must be canon. Fingerprint = JSON(stats, tags, active enemy-bond count). `mucize` (miracle type from
  `MUCIZELER`): apply; if fingerprint unchanged → refund + refuse "found nothing to change". `afet` (disaster from
  `AFETLER`): only on region/place/settlement; apply with severity multiplier `afet_siddet/100`; create event record
  with severity `afet_olay`. `bilgi` (teach a `teknoloji` record): refund + refuse if already known. `lanet` (curse):
  for stat keys in {prosperity, fertility, strength, defense, wealth, abundance, influence} subtract `lanet_stat`
  (clamp 0..100), add tag "lanetli" (cursed); unchanged → refund + refuse.
- **God-power delegations** (`tanriguc.js`, god-powers spec): essence drain from son/mortal/foreign god, devour, harvest
  community, kill/devour foreign god, resurrect mortal, deify (emits `new_son`), demote, grant power, absolute command,
  choose prophet, manifestation, lineage curse (+lift), convert, wrath, world wrath. Free-text args truncated to
  `ilham_uzunluk`.
- **One-off balance migration** `dengeGecisi()` (startup): if `denge_surum < 2`: every non-dead son's essence raised to
  at least `round(oz_max/2)`; set `denge_surum=2`; chronicle `sistem` "The balance of the sky changed: …".

### 6.4 Network repair (`agKader`, `agKuralOnar`)
- `network_rule_repair(epoch)` (`agKuralOnar` → `kopukUclariOnar`, rule-based, no LLM): if anything changed emit
  `network_repair` `{type:'rule', text:"Network repaired: N loose ends bonded (location a, struck place b, events c,
  narratives d, prophecy e, remnant f, destruction g, maker h)[; k vague bonds turned concrete].", counts}`.
- `network_fate_repair({ids, related=true, auto, full})`: content job. With ids: process in batches of
  `AG.kader_parti` (12) with `fate_suggest_bonds`. Otherwise: `remaining = full ? ∞ : AG.kader_cag_tavan (36)`,
  `priority = full ? ∞ : round(remaining × AG.oncelik_payi / 100)`; loop while remaining > 0 and not stopped:
  priority batch = `priority_records(min(priority, kader_parti))` (events/legends/traditions mentioned in chronicle but
  unbonded) else `weak_records(min(remaining, kader_parti))`; stop when empty or a pass looked at 0; decrement; in full
  mode emit progress system lines. Then if `related`: name vague `ilgili` bonds in batches of `AG.ilgili_parti` (40)
  up to `AG.ilgili_cag_tavan` (80) (∞ in full mode) using a cursor (`sonId`). Returns
  `{looked, built, named, closed}`; emits stop/finish summaries.

---

## 7. Resume after crash

### 7.1 What is persisted

| Data | Where | Written when | Used by |
|---|---|---|---|
| Epoch progress | `dunya.cag_durum` JSON (§3.2) | after backup, after each phase, engine marker inside engine tx, Fate/voices/council flags | `cagIc` resume; UI "half epoch" banner |
| Fate debt | `dunya.kader_borc` | `kaderHukmu` tx or epoch catch | next Fate context |
| Son turn | `ogullar.tur_cag`, `tur_ap`, `tur_ctx` | turn start; after every successful tool call; when a long job starts | `son_turn` resume |
| Son acted | `ogullar.son_eylem_cag` | end of turn | eligibility |
| Mortal turn | `varliklar.tur_cag`, `tur_ap`, `tur_ctx`, `son_eylem_cag` | same pattern | `mortal_turn` resume |
| Mortal agents of the epoch | `cag_durum.ajanlar` | once at phase 2 start | resume |
| Engine notes | `cag_durum.motor` | in the engine transaction | Fate prompt on resume |
| Pending long job | `tur_ctx.bekleyenIs = "<tool>:<essence>:<ap>:<epoch>"` | when a world/child birth starts | refund logic |
| Horizon intuitions | `ufuk_sezgi.durum` | per item | `sezgiKurtar` on startup |
| Live log | `gunluk` table | each event | UI after restart |

### 7.2 Phase idempotency matrix

| Crash during | On resume |
|---|---|
| complete_missing | Re-run (each step checks what is still missing). |
| Before `started` written | Treated as fresh: second backup, distribution again. |
| Phase 0/1 | `started` set → no new backup, no redistribution; phase 1 re-queues sons with `last_action_epoch < epoch`; interrupted son resumes its turn (§7.3). |
| Phase 2 | Same agent list; only agents that have not acted; interrupted ones resume. |
| Phase 3 | Engine tx rolled back → engine runs again from scratch (atomic). If committed, `phase=3` committed with it → skipped. |
| Phase 4 before `fate=1` | Naming re-runs (only pending records), Fate re-runs. Fate's `kaderHukmu` is a single transaction so it is all-or-nothing. **Gap:** if the crash happens after `kaderHukmu` committed but before `cag_durum.fate=1` is saved, Fate runs again; the second run judges only records with `kader_notu IS NULL` or `cag == epoch` — current-epoch records get judged/rewarded twice (see §14). |
| Voices / council | Flag set before the call → not re-run (accepted loss). |
| Phase 5 | Words and local gods run outside the transition transaction; transition is atomic. If the transition committed (epoch incremented) but `cag_durum` was not cleared, the stale state has `epoch != world.epoch` → ignored. If crash before the transition commit, words/local gods re-run on resume (local god guarded by its own check; words may be added twice — §14). |

### 7.3 Turn resume (sons and mortals)
- Serialization (`turCtxYaz`): JSON of ctx entries except `ap`, `cag` and functions; `Set` → `{"$set":[numbers|strings]}`;
  arrays keep numbers/strings/plain objects; primitives/null kept; everything else dropped. `turCtxOku` reverses it.
- `half = tur_cag == epoch and tur_ap != null` → AP and ctx restored; rebuilt traces are overridden by saved ctx.
- The user prompt gets "Your turn was interrupted earlier; your deeds remain in the world. Continue where you left off."
- Within a live process, `agent_turn` itself also restarts/continues after transient failures (§12.3).

### 7.4 Long-running tool calls (world birth, child birth)
Tools `dunya_dogur` (birth world) and `evlat_dogur` (birth child) take minutes (they call LLMs). The tool deducts cost
and AP, then writes `ctx.bekleyenIs = "<tool>:<essence>:<ap>:<epoch>"` and persists ctx immediately. The job promise
is registered in `SUREN[son_id]` (`surenIs(son_id)`), removed when it settles. When the job finishes it appends a trace
`{tool, key, summary}` to `ctx.uzunIsler` (`long_jobs`).

- `agent_turn` waits for the pending job before opening a continuation session or returning (`sureniBekle`), emitting
  `retry {name:"running job", reason:"a long action is still being processed; waiting for it"}`; then for each trace
  whose key is not already mentioned in a done-action summary it adds `{tool, read:false, summary}` to the done list
  (the model sees it in the continuation prompt; no second birth).
- `bekleyenIsiCoz(son, ctx)`: if no flag → null; if still running in this process → `'running'`; else parse; `done`
  = (world birth: a world with `yaratan_id=son and olusturma_cag=<epoch>` exists; child birth: a son with
  `ebeveyn_id=son and dogum_cag=<epoch>` exists). Clear flag. If done → `'done'`. Else refund: `son.oz += essence`,
  `ctx.ap += ap`, chronicle `sistem` "<son>'s half-finished world birth/child birth could not be completed; its essence
  returned to it." → `'refund'`.
- `eskiBekleyenleriCoz()` (start of each son turn and complete_missing): for every son whose `tur_ctx` contains a pending
  job not running in this process → `bekleyenIsiCoz`; persist ctx; restore AP to `tur_ap` only if the turn can still
  continue this epoch (`tur_cag == epoch`, `tur_ap != null`, son has not acted).

### 7.5 Startup sequence (server.js)
1. Acquire process lock. Open DB, run migrations, register tunables (`tanimla` loads overrides from
   `dunya.denge_ayar`), create ledger TEMP triggers.
2. epoch.js module load: load the last `CAG_AKIS.gunluk` (600) events from `gunluk` into the in-memory ring
   `GUNLUK`; bind live stream to agents (`canliBagla`) and notifications; bind metrics with an epoch getter;
   `ekleriDoldur()` (LANGUAGE-SPECIFIC).
3. On listen: `dengeGecisi()`; if not read-only: compute missing importance scores; prune metrics; planner statistics;
   one-time text repair (`onarimKos`, sets `veri_surum=2`); age consistency (`yasTutarliligi`); data repair
   (`veriOnarimi`, 11 idempotent repairs, see onarim.js header); `sezgiKurtar`; mirror-world pairing; identity-leak
   cleanup of narratives; endings for dead records; rule network repair; invalid image-title cleanup; canon facts if
   none; connect worlds (`dunyayiBagla`).
4. After `SUNUCU.tamamla_gecikme` ms: `tamamla()` (completion lock) unless disabled.
5. A half-done epoch is **not** auto-resumed; the player presses "Complete the epoch".

---

## 8. Ledger (Fate's book, `defter`) — as it relates to the pipeline
- Every world-changing tool call of a son (`who_type 'o'`) or mortal (`'v'`) and every god action (`'t'`) is one
  ledger group (`defter`: id, epoch, who_type, who_id, who_name, tool, summary, undone, result). Read-only tools
  (`dunya_ozeti`, `dunyaya_bak`, `varlik_incele`, `varlik_ara`, `hafizam`, `kardesi_incele`) are not ledgered.
- Summary = up to 220 chars joining (each ≤80) of input fields `ad, tur, hedef_ad, metin, aciklama, neden, ilham`.
- Row capture: TEMP triggers on whitelisted tables (`varliklar, baglar, ogullar, iliskiler, topluluk_iliski, kronik,
  gercekler, iplikler, sozluk, halk_inanc, rotalar, dunyalar, yolculuklar, mesajlar, dunya, yildizlar,
  yabanci_tanrilar, caglar, caglar_dunya, kronik_bakis, gorseller, senaryolar`) write `defter_satir` rows
  (insert/update/delete, before/after JSON) when the SQL function `defter_grup()` returns the open group id
  (AsyncLocalStorage; closed as soon as the call returns so late background writes are not captured). Empty groups are
  deleted; update rows are compacted to changed columns + identifying columns.
- Undo (`geriAl`, refused while an epoch runs: HTTP 409 "A ledger page cannot be torn out while the epoch is running.")
  is conflict-aware (inserted records → rejected / bonds deactivated / others deleted; updates reverted if unchanged
  since, numeric quantity columns get the delta reverted clamped to observed values, `statlar`/`etiketler` merged
  key-wise; deletes re-inserted; born sons/worlds are permanent and their cost not refunded). Chronicle line "<god>'s
  hand: a page was torn from Fate's book. <who>'s action (<tool>) is considered never to have happened."
- Pruning at each epoch end: groups older than `epoch − DEFTER.sakla_cag` (6) deleted, orphan rows deleted.
Full ledger semantics belong to the ledger spec; the pipeline only needs: ledger wrapping per tool call, prune at epoch end.

---

## 9. Backups

`backup(label='elle')` (`yedekAl`):
1. Copy every referenced image file into the image pool `<backups>/gorseller/` if not already there.
2. File name `aerona-<label sanitized [\w-], ≤40>-<YYYY-MM-DDTHH-MM-SS-mmm local>-<4 random base36>.db` in
   `<db dir>/yedekler/`.
3. `VACUUM INTO '<path>'` (consistent online copy).
4. Strip telemetry tables (`gunluk`, `llm_olcum`) from the copy, then `VACUUM` the copy.
5. Optional second target: env `AERONA_YEDEK2=<dir>` → copy there; keep newest `YEDEK.ikinci` (20) `aerona-*.db`.
6. Rotate (`yedekleriBuda`), newest first by mtime, kind = label part of the filename:
   - epoch backups (`cag<N>`): keep the newest `YEDEK.cag` (10); older ones are deleted unless `N % YEDEK.onluk == 0`
     (every 10th epoch kept forever);
   - manual (`elle`): keep newest `YEDEK.elle` (30);
   - every other label (safety backups: `geri-yukleme-oncesi`, import, reset…): newest `YEDEK.guvenlik` (5) per label.
   If anything was deleted → prune the image pool: delete pool images referenced neither by the live DB nor by any
   backup (if any backup cannot be opened, delete nothing).
7. Return the filename.

Epoch pipeline: one backup labelled `cag<N>` before every fresh epoch (§3.3); failure is reported, not fatal.
Restore (`yedektenDon`): validate (opens read-only, `PRAGMA quick_check == ok`, has tables dunya/ogullar/varliklar/kronik),
take a `geri-yukleme-oncesi` safety backup, then load all tables from the file in one transaction (telemetry tables
kept as-is, derived tables rebuilt by triggers, missing columns default), then data migrations; server calls
`dunyaDegisti` (clears in-memory log ring, re-applies tunables, reruns one-time repair, emits system + `free`).
Restore is refused while any job runs ("Wait for running jobs to finish first.").

---

## 10. Progress reporting and the live stream

### 10.1 Event bus
`bus` = in-process EventEmitter, single channel `'olay'`, max 50 listeners.
`emit(e)` (`yayinla`): adds `epoch` (`cag`, = `e.cag ?? current world epoch`, cached last value if the world cannot be
read) and `time` (`zaman`, ms) unless present, then emits. Code paths that call `bus.emit` directly (genesis route,
`toplu.js`, server `dunyaDegisti`) skip the epoch stamp (smell).

### 10.2 SSE
`GET /api/olaylar` → `text/event-stream`, `no-cache`, keep-alive. First message `{kind:'hello', busy}` (`merhaba`),
then every bus event as `data: <json>\n\n`; comment ping `: ping` every 20 s; listener removed on close. No event ids,
no replay — the client fetches `/api/gunluk` for history.

### 10.3 Persistent live log (`gunluk`)
Every event except the noisy kinds `{image_queued, image_progress, image_status, job_queued, job_start, job_done, busy,
free, hello, turn, stream, tool_writing, writing, tool_preparing}` (`GUNLUK_DISI`) is pushed into the in-memory ring
(max `CAG_AKIS.gunluk` = 600) and inserted into `gunluk(zaman, veri JSON)`; every 100 inserts rows older than the newest
`CAG_AKIS.gunluk_db` (1000) are deleted. Telemetry: excluded from backups.

### 10.4 ETA (`cagTahmini`, olcum.js)
From the last 400 `phase`/`epoch_done` events in `gunluk`: reconstruct past epochs (`phase` no=1 starts a new one;
record `phase[no] = elapsed_s`; `epoch_done` with duration closes it). Use the last `OLCUM.ortalama_cag` (6) epochs:
`avg_total`, `avg_phase_start[no]` for no 1..5. When running (`busy.type=='epoch'`, start = busy.started_at, current
phase = latest `phase` event since start): `elapsed = now − start`; if phase known:
`estimate = avg_total − avg_phase_start[no] − max(0, elapsed − phase.elapsed_s)` else `avg_total − elapsed`;
`remaining_s = max(0, round(estimate))`, `overrun = estimate < 0`. Output `{samples, avg_epoch_s,
avg_phase_start_s, running, elapsed_s, remaining_s, phase, overrun}`. Also included in `/api/durum` while an epoch runs.

### 10.5 Event catalogue
Every event additionally has `epoch` and `time`. "Logged" = goes to `gunluk`.

| Kind (old) | English | Payload | Emitted by | Logged |
|---|---|---|---|---|
| `merhaba` | hello | `busy` | SSE connect | no |
| `mesgul` | busy | `busy:{type, started_at, son_id?, son_ids?}` | lock acquire; genesis route | no |
| `serbest` | free | — | lock release; genesis end; world changed | no |
| `sistem` | system | `text` | many (info lines) | yes |
| `hata` | error | `text`, `son_id?` | many | yes |
| `asama` | phase | `no` (1..5), `total` (5), `name`, `elapsed_s` | epoch | yes |
| `cag_basla` | epoch_start | `epoch`, `order:[{id,name,ini}]`, `resuming` | epoch | yes |
| `sira` | turn | `no`, `total`, `name` | phase 1 | no |
| `yeniden` | retry | `name`, `attempt`, `total`, `reason`, `wait_ms?`, `done_count?` | llm retry; agent restart/continuation; dropped-son retry; pending job wait | yes |
| `basla` | start (son turn) | `son_id`, `son_name`, `model`, `half` | son_turn | yes |
| `bitti` | done (son turn) | `son_id`, `son_name`, `utterance`, `creations`, `status` | son_turn | yes |
| `olumluler_basla` | mortals_start | `agents:[{id,name,type}]` | phase 2 | yes |
| `olumlu_basla` | mortal_start | `record_id`, `name`, `type`, `model`, `half` | mortal_turn | yes |
| `olumlu_bitti` | mortal_done | `record_id`, `name`, `utterance`, `creations`, `status` | mortal_turn | yes |
| `dusunce` | thought | `text` (assistant text block) | agent_turn | yes |
| `akis` | stream | `text` (batched text deltas, ~150 ms) | agent_turn | no |
| `arac_hazirlaniyor` | tool_preparing | `tool`, `id` | agent_turn (content_block_start tool_use) | no |
| `arac_yaziliyor` | tool_writing | `tool`, `id`, `chars` (≈ every 200 chars of input JSON) | agent_turn | no |
| `arac` | tool_call | `tool`, `input`, `id` | agent_turn | yes |
| `arac_sonuc` | tool_result | `text` (≤400 chars), `error` (bool: `is_error` or text starts with "REFUSED"), `id` | agent_turn | yes |
| `yaziyor` | writing | `who`, `topic?`, `chars`, `stream_id`, `finished?`, `status?` ('ok'/'error'), `error?` | structured calls with progress (genesis, summon, naming, Fate, chronicler, revelation, bard, lore writer, awakening, …) | no |
| `motor_basla` | engine_start | — | phase 3 | yes |
| `motor_not` | engine_note | `text`, `category` (§10.7) | phase 3 | yes |
| `motor_bitti` | engine_done | `notes` | phase 3 | yes |
| `kader_basla` | fate_start | `epoch` | phase 4 | yes |
| `kader_adim` | fate_step | `text` | Fate, chronicle completion, voices, missing chronicles, council, world birth | yes |
| `kader_bitti` | fate_done | `epoch`, `epoch_name`, `rejected:[name]`, `corrected:[name]` | phase 4 | yes |
| `konsey` | council | `id`, `topic`, `accepted`, `motion` | council | yes |
| `cag_bitti` | epoch_done | `epoch`, `new_epoch`, `summary` (transition notes), `duration_s` | phase 5 | yes |
| `is_sirada` | job_queued | `job`, `ahead`, `running`, `queue` | content pool | no |
| `is_basla` | job_start | `job`, `running`, `queue` | content pool | no |
| `is_bitti` | job_done | `job`, `running`, `queue` | content pool | no |
| `derinlesti` | deepened | `record:{id,name}` | deepen job | yes |
| `yabanci_derinlesti` | foreign_god_deepened | `id`, `name` | job / complete_missing | yes |
| `vahiy` | revelation | `record` | revelation | yes |
| `yeni_ogul` | new_son | `son` | summon, deify | yes |
| `yukselis` | ascension | `son` | ascend | yes |
| `dunya_dogdu` | world_born | `world_id`, `name` | birth_world | yes |
| `genesis_bitti` | genesis_done | — | genesis route | yes |
| `ag_onarim` | network_repair | `type` ('rule'/'fate'/'related'), `text`, `counts?`, `bonds?`, `looked?:[{t,id,name}]` | network repair | yes |
| `toplu_derin` | bulk_deepen | bulk state summary + `line:{time, level, text, id?}` | toplu.js | yes |
| `bildirim` | notification | `id`, `epoch`, `category`, `importance`, `title`, `text`, `target_type`, `target_id`, `chronicle_id`, `name` | bildirim.js | yes |
| `gorsel_sirada` / `gorsel_ilerleme` / `gorsel_durum` / `gorsel_bitti` / `gorsel_toplu` | image_queued / image_progress / image_status / image_done / image_bulk | see image-generation spec | gorsel-uret.js | queued/progress/status no; done/bulk yes |

### 10.6 Notifications derived from the stream
Listener on the bus: `epoch_done` → notification category `cag` "Epoch N finished (M min)" with text = first
`CAG_AKIS.bildirim_ozet` (6) summary lines joined by " · ". `error` → category `hata` with title = text, target son if
`son_id` — **except** texts containing "will be retried" / "retrying" / "will be compensated"
(`/denenecek|deneniyor|telafi edilecek/`). Notification categories are filtered by the player's settings
(`dunya.bildirim_ayar`); error titles are translated from English SDK messages (`hataTurkce`); titles truncated to 90.

### 10.7 Stream categories (`akisKategorisi`)
Engine notes are classified by the first matching word-start regex, in order: voyage (ship, expedition, journey, set
out, arrived, stowaway, caravan, migrated, colony), gate (gate, seal, bridge, route, road opened, pass, deviating),
leak (leak, outer being, nothingness, sanity, went mad, blurred, forbidden knowledge, whisper), war (war, battle, siege,
army, conquered, plunder, raid), disaster (flood, earthquake, plague, epidemic, drought, storm, famine, disaster),
sky (eclipse, comet, star, sky, moon, alignment, meteor), life (born, died, death, aged, heir, resurrected,
domesticated, chimera, mutation), civilization (tier, federation, independent, empire, kingdom, trade); else `world`.
LANGUAGE-SPECIFIC: the old regexes are Turkish stems with a "not preceded by a letter" guard; the new app should tag
engine notes with an explicit category at emission time instead of regex classification.

---

## 11. Statistics and metrics

### 11.1 LLM call metrics (`llm_olcum`)
Every structured call and agent turn writes one row: `epoch, name, model, kind ('structured'|'agent'), ms, status
('ok'|'partial'|'error'), attempt (attempt number / session number), turns, input_tokens (input + cache read + cache
creation), output_tokens, cost_usd (`total_cost_usd` summed), actions (agent: non-read actions done), error (≤200)`.
Agent status = `ok` if final SDK subtype `success`, else `partial` (returned with world changes), or `error` (threw).
Prune: every 50 inserts and at each epoch end delete rows with `epoch <= max_epoch − OLCUM.sakla_cag` (100).
Summary API (`olcumOzeti`): totals; per-epoch (calls, ms, tokens, cost, errors, retried (`attempt>1`), slow
(`ms > OLCUM.yavas_sn×1000`)); per model; per step (names "Son turn: *" and "Mortal turn: *" grouped); top 12 slow
calls; last 8 errors.

### 11.2 Live log as statistics source
ETA uses `phase`/`epoch_done` events (§10.4).

### 11.3 Epoch statistics (`cag_istatistik`)
Written by the epoch transition (world-engine spec): `cag_istatistik(cag PK, veri JSON)` = world photo + doom level +
breakdown (`dokum`). `GET /api/dokum?cag=` returns `{epoch, previous_epoch, breakdown, values, diff: {key: {before,
now, diff}} for changed numeric keys, sons: {id: {key: delta}}}`.

---

## 12. LLM retry policy (llm.js)

### 12.1 Error classification
- **Permanent** (`KALICI`, never retried, checked first): `prompt is too long`, `context length|window`,
  `too many tokens`, `invalid api key`, `authenticat…`, the LLM-disabled message.
- **Transient** (`GECICI`): `overload`, `rate limit`, an HTTP-ish code 429/5xx preceded by `status|error|http|code|hata`
  (within 3 non-word chars) or followed by a standard reason phrase (bad gateway, service unavailable, internal server
  error, gateway timeout, too many requests), `ECONN*`, `ETIMEDOUT`, `EPIPE`, `socket`, `network`, `fetch failed`,
  `exited with code`, `terminated`, "model gave no structured output", `aborted`, "timeout". Numbers are matched with
  word boundaries so texts like "523000 tokens" or "costs 500 essence" do not count.
- `is_transient(e) = not PERMANENT(msg) and TRANSIENT(msg)`.
- New design: classify by typed SDK/HTTP exceptions (status codes, `overloaded_error`, timeouts) rather than regex on
  localized messages.

### 12.2 `retry(fn, {attempts = MODEL.deneme, name, notify})`
```
for i in 1..attempts:
    try: return await fn(i)
    except e:
        last = e
        if i == attempts or not is_transient(e): break
        wait = [MODEL.bekle_1, MODEL.bekle_2][i-1] ?? MODEL.bekle_3   (seconds)
        notify({kind:'retry', name, attempt: i+1, total: attempts, reason: msg[:160], wait_ms})   # errors in notify ignored
        sleep(wait)
raise last
```

### 12.3 Structured call (`structured`)
Input: `{model (always haiku), system, prompt, schema, timeout_ms = MODEL.yapisal_sure s, on_progress, on_retry, name,
attempts}`. Agents pass `attempts = KADER.model_deneme` (3) and role-specific timeouts.
- If LLM disabled → throw (permanent).
- `retry` around a single attempt; metrics row on final success/failure.
- Single attempt: AbortController with timeout; SDK `query` with `maxTurns = max(1, MODEL.yapisal_adim)`,
  `outputFormat: {type:'json_schema', schema}`, partial messages enabled iff progress callback. Progress: each attempt
  gets a stream id `a<counter>-<ms>`; emits `{chars:0, stream_id}` at start, then at most once per second
  `{chars, stream_id}` (chars = accumulated text/partial_json/thinking delta lengths), and exactly one final
  `{chars, stream_id, finished:true, status:'ok'|'error', error?}` in `finally`. Result: `structured_output` else
  first `{…}` block of the text parsed as JSON. No output → throw "Model gave no structured output[ (<subtype>:
  <errors>)]" (transient). Abort → throw "timeout (<s> s)" (transient).
- Note: schema validation is delegated to the SDK's JSON-schema output; callers additionally sanitize every field.

### 12.4 Tool wrapper (`araclariSar`) for agent turns
For each tool of a turn's MCP server:
- **Sequential**: all calls of one turn are chained on one promise (`sira`) even if the model emits several tool_use
  blocks in one message — so a failure restore never undoes another call's effects.
- **Gate** (`kapi(name)`): if it returns a reason → result `{isError:true, text:"REFUSED: <reason>"}` (e.g. the son fell
  asleep or died mid-turn).
- **Snapshot**: before the call, shallow-copy ctx (arrays copied, Sets copied, functions skipped).
- Run the handler inside a ledger group unless it is a read tool (`dunya_ozeti, dunyaya_bak, varlik_incele,
  varlik_ara, hafizam, kardesi_incele`).
- On success: `save(ctx)` (persist turn state; errors ignored) and return the result.
- On exception: restore ctx from the snapshot (arrays/Sets restored in place to keep outside references), fallback
  restore of just `ap`; return `{isError:true, text:"REFUSED: An error occurred while the tool ran (<msg ≤200>). Your
  action point was returned; fix your input and try again, or choose another action."}`. The turn is not burned.

### 12.5 Agent turn (`agentTurn`) — sessions, restart and continuation
Input: `{name, model, system, prompt, server, rebuild_server, continuation_prompt(done, reason), is_complete(text)
(default: non-empty), on_event, max_turns = MODEL.ajan_adim, timeout_ms = MODEL.ajan_sure, server_name='dunya',
pending_job, job_traces}`.
State: `done = []` (successful tool results: `{tool, read: is_read_tool, summary: text whitespace-collapsed[:MODEL.ozet_karakter]}`),
`restarts = 0`, `continuations = 0`, `prompt = initial`.
```
for session in 0 .. MODEL.tur_tavan-1:
    srv = session == 0 ? server : (rebuild_server ? rebuild_server() : server)     # fresh MCP server; state lives in ctx
    try: res = await one_session(prompt, srv, done)                               # see below
    except e: res = {text:'', status:'error', error: msg}
    await wait_pending_job()                                                      # §7.4
    if res.status == 'success' and is_complete(res.text): return {...res, done}
    reason = {error: "connection error (<err[:120]>)", timeout: "timeout", error_max_turns: "step limit reached",
              success: "you finished without speaking your word"}[res.status] or res.status
    no_trace = no non-read action in done
    if res.status == 'error' and not is_transient(res.error): break               # permanent: don't burn sessions
    if no_trace and res.status == 'error' and restarts < MODEL.bastan:            # restart from scratch is safe
        restarts += 1
        emit retry {name:'turn', attempt: restarts+1, total: MODEL.bastan+1, reason, wait_ms: MODEL.bastan_bekle*1000*restarts}
        sleep(MODEL.bastan_bekle * restarts); continue                            # same prompt
    actions = ["<tool> → <summary>" for non-read entries of done]
    next = (continuations < MODEL.devam and continuation_prompt) ? continuation_prompt(actions, reason) : null
    if next is null: break
    continuations += 1
    emit retry {name:'continuation', attempt: continuations, total: MODEL.devam, reason, done_count: len(actions)}
    if res.status == 'error': sleep(MODEL.devam_bekle)
    prompt = next
if res.status != 'success' and no non-read action in done: raise Error(res.error or "Turn ended without leaving a trace (<status>)")
return {...res, done}      # partial result: world changes stand; caller still finalizes the turn
```
A turn that changed nothing and failed throws → the epoch retries that son once at phase end. A turn that changed the
world but ended without the utterance still finalizes (son marked as acted, no chronicle utterance).

`one_session` (`tekAjanTuru`): AbortController timeout; SDK `query` with `mcpServers {server_name: srv}`,
`allowedTools ["mcp__<server_name>"]`, `maxTurns`, partial messages on. Streaming:
- `content_block_start` tool_use → flush text buffer, emit `tool_preparing {tool, id}`;
- `text_delta` → buffer, flushed as `stream {text}` at most every 150 ms (and at block stop);
- `input_json_delta` → count chars, emit `tool_writing {tool, id, chars}` roughly every 200 chars;
- `assistant` message → for text blocks emit `thought {text}` and remember last text; for tool_use emit
  `tool_call {tool, input, id}`;
- `user` tool_result → text; `error = is_error or text startswith "REFUSED"`; on success push to `done`;
  emit `tool_result {text[:400], error, id}`;
- `result` → add usage to metrics; final text = `result` if success; return `{text, status: subtype, turns}`.
- Abort → `{text: last, status: 'timeout'}`; other exceptions propagate; stream end without result →
  `{text, status: 'ended'}`.
- Test hook (drop): env `AERONA_KES=N` aborts the first session after N successful non-read tool calls.

### 12.6 Where timeouts and attempts come from

| Call | Timeout | Attempts |
|---|---|---|
| Son turn session | `KADER.ogul_sure` (420 s) | sessions ≤ `MODEL.tur_tavan`; restarts `MODEL.bastan`; continuations `MODEL.devam`; plus one phase-end retry by the epoch |
| Mortal turn session | `MODEL.ajan_sure` (420 s) | same session policy; epoch retries once immediately |
| Fate judgment / chronicler / overflow batches / chronicle fixes | `KADER.kader_sure` (480 s) | `KADER.model_deneme` (3) |
| Voices of the peoples | `KADER.ses_sure` (240 s) | 3 |
| Missing chronicles | `KADER.kayip_sure` (300 s) | 3 |
| Genesis | `YARATILIS.sure` (360 s) | 3 |
| Awakening | `UYANIS.sure` (300 s) | 3 |
| Other structured (summon, naming, deepen, revelation, epics, prompts) | `MODEL.yapisal_sure` (300 s) unless given | 3 |
| Council / chat / network repair (konsey.js, agonar.js) | default | `MODEL.deneme` (3) |

---

## 13. Tunables

Each tunable is registered with `tanimla(GROUP, {key: [default, label, min, max, ui_group]})`; current values are
the default overridden by `dunya.denge_ayar` JSON (`"GROUP.key": value`). English key = `group.key` in snake_case.

### 13.1 AJAN (agents & model) — epoch.js

| English key | Turkish key | Default | Min | Max | UI group | Label |
|---|---|---|---|---|---|---|
| `agents.max_concurrent_jobs` | `AJAN.eszamanli_is` | 8 | 1 | 32 | Agents & model | Max concurrent content jobs (deepen, epic, prompt); extra jobs are queued |
| `agents.auto_deepen_count` | `AJAN.oto_derin` | 3 | 0 | 20 | Agents & model | Records auto-deepened at epoch end (0 = off) |
| `agents.son_parallel` | `AJAN.ogul_paralel` | 2 | 1 | 6 | Agents & model | Sons thinking at the same time |
| `cosmos.local_god_epochs` | `AJAN.yerel_tanri_cag` | 3 | 1 | 200 | Cosmos | Epochs before a sleeping local god is born in a godless world |
| `cosmos.local_god_rebirth_epochs` | `AJAN.yerel_tanri_yeniden_cag` | 5 | 0 | 1000 | Cosmos | Epochs (mourning) before a new sleeping god is born where the local god died |
| `cosmos.local_god_power` | `AJAN.yerel_tanri_guc` | 30 | 1 | 100 | Cosmos | Power of the sleeping local god |
| `agents.auto_deepen_wait_s` | `AJAN.oto_bekle_sn` | 5 | 1 | 600 | Agents & model | Auto-deepen: poll interval while the job pool is full (s) |
| `agents.auto_deepen_wait_tries` | `AJAN.oto_bekle_deneme` | 60 | 0 | 10000 | Agents & model | Auto-deepen: max polls waiting for the pool to free |
| `agents.auto_reserve` | `AJAN.oto_pay` | 2 | 0 | 12 | Agents & model | Concurrent-job slots auto-deepening leaves to manual jobs |
| `agents.prompt_rounds` | `AJAN.prompt_tur` | 10 | 1 | 1000 | Agents & model | Manual "write prompts": max batches |
| `agents.auto_deepen_power_weight` | `AJAN.oto_derin_guc` | 2 | 0 | 100 | Agents & model | Auto-deepen ordering: weight of power level, in bonds |
| `agents.stale_epic_epochs` | `AJAN.destan_tazele` | 8 | 0 | 1000 | Agents & model | Stale epic: creator's and sons' epic/depth older than this many epochs is rewritten in background at epoch end (0 = off) |
| `agents.stale_epic_per_epoch` | `AJAN.destan_tazele_adet` | 1 | 0 | 20 | Agents & model | Stale epic: max refreshed per epoch (low priority: only when pool is idle) |

### 13.2 CAG_AKIS (epoch flow) — epoch.js

| English key | Turkish key | Default | Min | Max | UI group | Label |
|---|---|---|---|---|---|---|
| `epoch_flow.year_sons` | `CAG_AKIS.yil_ogul` | 15 | 0 | 100000 | Epoch flow | Gods' turn: chronicle years up to this year of the epoch |
| `epoch_flow.year_mortals` | `CAG_AKIS.yil_olumlu` | 30 | 0 | 100000 | Epoch flow | Mortals' turn: up to this year |
| `epoch_flow.year_engine` | `CAG_AKIS.yil_motor` | 45 | 0 | 100000 | Epoch flow | World's own course: up to this year |
| `epoch_flow.year_fate` | `CAG_AKIS.yil_kader` | 49 | 0 | 100000 | Epoch flow | Fate and chronicler: up to this year |
| `epoch_flow.year_transition` | `CAG_AKIS.yil_gecis` | 4 | 0 | 100000 | Epoch flow | After the transition: first years of the new epoch (up to this year) |
| `ui.live_log_memory` | `CAG_AKIS.gunluk` | 600 | 10 | 100000 | Interface | Last events kept in memory for the live stream |
| `ui.live_log_db` | `CAG_AKIS.gunluk_db` | 1000 | 10 | 1000000 | Interface | Last events of the live stream kept in the database |
| `ui.epoch_done_summary_lines` | `CAG_AKIS.bildirim_ozet` | 6 | 0 | 100 | Interface | Summary lines shown in the "epoch finished" notification |

### 13.3 TANRI_EYLEM (god's actions) — epoch.js

| English key | Turkish key | Default | Min | Max | UI group | Label |
|---|---|---|---|---|---|---|
| `god_action.bless_essence` | `kutsa_oz` | 20 | 0 | 1000 | God's actions | Essence given by an essence blessing |
| `god_action.bless_stat` | `kutsa_stat` | 5 | 0 | 100 | God's actions | Stat added by a stat blessing |
| `god_action.bless_existence` | `kutsa_varlik` | 20 | 0 | 100 | God's actions | Existence added by an existence blessing |
| `god_action.bless_loyalty` | `kutsa_sadakat` | 3 | 0 | 100 | God's actions | Loyalty added by every blessing |
| `god_action.star_stat` | `yildiz_stat` | 3 | 0 | 100 | God's actions | Each stat gained when adding a star |
| `god_action.ascend_existence` | `yukselis_varlik` | 25 | 0 | 100 | God's actions | Existence gained on ascension |
| `god_action.ascend_legend_prevalence` | `yukselis_efsane` | 80 | 0 | 100 | God's actions | Initial prevalence of the ascension myth |
| `god_action.rebel_will` | `asi_irade` | 70 | 0 | 100 | God's actions | Will above which a son does not bow to punishment |
| `god_action.lightning_hp_pct` | `yildirim_can` | 30 | 0 | 100 | God's actions | HP taken by lightning (% of max HP) |
| `god_action.suppress_base` | `bastir_taban` | 70 | 0 | 1000 | God's actions | Suppress rebellion: base of god's power |
| `god_action.suppress_essence_divisor` | `bastir_oz_bolen` | 10 | 1 | 10000 | God's actions | Suppress: essence / this is added to god's power |
| `god_action.suppress_die` | `bastir_zar` | 30 | 1 | 1000 | God's actions | Suppress: each side's die (1–this) |
| `god_action.suppress_strength_pct` | `bastir_guc` | 50 | 0 | 1000 | God's actions | Suppress: son's strength contribution (%) |
| `god_action.suppress_per_level` | `bastir_seviye` | 3 | 0 | 100 | God's actions | Suppress: son's contribution per level |
| `god_action.suppress_loyalty` | `bastir_sadakat` | 15 | 0 | 100 | God's actions | Loyalty gained by a suppressed rebel |
| `god_action.suppress_hp_pct` | `bastir_can` | 50 | 1 | 100 | God's actions | Remaining HP of a suppressed rebel (%) |
| `god_action.suppress_fame_loss` | `bastir_un` | 10 | 0 | 1000 | God's actions | Fame lost by a suppressed rebel |
| `god_action.suppress_fail_fame` | `bastir_basarisiz_un` | 10 | 0 | 1000 | God's actions | Fame gained by an unsuppressed rebel |
| `god_action.suppress_fail_ambition` | `bastir_basarisiz_hirs` | 5 | 0 | 100 | God's actions | Ambition gained by an unsuppressed rebel |
| `god_action.suppress_fail_essence` | `bastir_basarisiz_oz` | 20 | 0 | 10000 | God's actions | Extra essence the god loses on failed suppression |
| `god_action.pardon_loyalty` | `af_sadakat` | 8 | 0 | 100 | God's actions | Loyalty added by a pardon |
| `god_action.punish_rebel_loyalty` | `ceza_asi_sadakat` | 8 | 0 | 100 | God's actions | Loyalty lost by a rebellious son after punishment |
| `god_action.punish_rebel_anger` | `ceza_asi_ofke` | 8 | 0 | 100 | God's actions | Anger gained by a rebellious son after punishment |
| `god_action.punish_loyalty` | `ceza_sadakat` | 3 | 0 | 100 | God's actions | Loyalty gained by a submissive son after punishment |
| `god_action.punish_anger` | `ceza_ofke` | 4 | 0 | 100 | God's actions | Anger gained by a submissive son after punishment |
| `god_action.prayer_essence_cap` | `dua_oz_tavan` | 100 | 0 | 100000 | God's actions | Max essence that can be granted to one prayer |
| `god_action.prayer_loyalty` | `dua_sadakat` | 4 | 0 | 100 | God's actions | Loyalty from a verbal answer |
| `god_action.prayer_essence_per_loyalty` | `dua_oz_sadakat` | 10 | 1 | 10000 | God's actions | Every this much granted essence = +1 loyalty |
| `god_action.prayer_existence` | `dua_varlik` | 3 | 0 | 100 | God's actions | Existence gained by a son whose prayer was answered |
| `god_action.disaster_severity_pct` | `afet_siddet` | 110 | 0 | 1000 | God's actions | Severity multiplier of a disaster sent by the god (%) |
| `god_action.disaster_event_severity` | `afet_olay` | 75 | 0 | 100 | God's actions | Severity in the god's disaster event record |
| `god_action.curse_stat` | `lanet_stat` | 15 | 0 | 100 | God's actions | Taken from community stats by the god's curse |
| `context.god_note_chars` | `not_uzunluk` | 6000 | 100 | 200000 | Context budgets | Max length of the god's own note (enters prompts) |
| `context.inspiration_chars` | `ilham_uzunluk` | 600 | 10 | 20000 | Context budgets | Max length of inspiration/free-text args (world creation etc.) |

### 13.4 MODEL (llm.js)

| English key | Turkish key | Default | Min | Max | UI group | Label |
|---|---|---|---|---|---|---|
| `model.attempts` | `MODEL.deneme` | 3 | 1 | 10 | Agents & model | Total attempts on a transient model error (if the caller gives none) |
| `model.wait_1_s` | `MODEL.bekle_1` | 2 | 0 | 600 | Agents & model | Wait before retry after the 1st error (s) |
| `model.wait_2_s` | `MODEL.bekle_2` | 6 | 0 | 600 | Agents & model | Wait after the 2nd error (s) |
| `model.wait_3_s` | `MODEL.bekle_3` | 15 | 0 | 600 | Agents & model | Wait after the 3rd and later errors (s) |
| `model.structured_timeout_s` | `MODEL.yapisal_sure` | 300 | 10 | 3600 | Agents & model | Default timeout of a structured call (s) |
| `model.structured_max_steps` | `MODEL.yapisal_adim` | 8 | 1 | 20 | Agents & model | Max model steps in a structured call |
| `model.agent_timeout_s` | `MODEL.ajan_sure` | 420 | 30 | 3600 | Agents & model | Default agent session timeout (s) |
| `model.agent_max_steps` | `MODEL.ajan_adim` | 10 | 1 | 100 | Agents & model | Default step limit of an agent session |
| `model.turn_session_cap` | `MODEL.tur_tavan` | 6 | 1 | 30 | Agents & model | Max sessions in one agent turn (incl. restarts and continuations) |
| `model.restarts` | `MODEL.bastan` | 2 | 0 | 10 | Agents & model | Restarts of a turn that crashed without leaving a trace |
| `model.restart_wait_s` | `MODEL.bastan_bekle` | 3 | 0 | 600 | Agents & model | Wait before a restart (s; multiplied by restart number) |
| `model.continuations` | `MODEL.devam` | 2 | 0 | 10 | Agents & model | Max continuation sessions for an interrupted turn |
| `model.continuation_wait_s` | `MODEL.devam_bekle` | 3 | 0 | 600 | Agents & model | Wait before a continuation after a connection error (s) |
| `context.done_action_summary_chars` | `MODEL.ozet_karakter` | 220 | 40 | 5000 | Context budgets | Per done-action summary in the continuation prompt (chars) |

### 13.5 Related tunables used by the pipeline (defined elsewhere)

| Turkish key | Default | Min | Max | English label | Defined in |
|---|---|---|---|---|---|
| `KADER.kader_sure` | 480 | 30 | 3600 | Fate & chronicler timeout (s) | agents.js |
| `KADER.hukum_paralel` | 3 | 1 | 16 | Overflow judgment batches run concurrently | agents.js |
| `KADER.model_deneme` | 3 | 1 | 10 | Attempts on transient model error (all agents.js calls) | agents.js |
| `KADER.ogul_sure` | 420 | 60 | 3600 | Son turn timeout (s) | agents.js |
| `KADER.ses_sure` | 240 | 30 | 3600 | Voices of the peoples timeout (s) | agents.js |
| `KADER.kayip_sure` | 300 | 30 | 3600 | Missing epoch chronicle timeout (s) | agents.js |
| `KADER.kayip_kronik` | 3 | 0 | 100 | Missing chronicles written per completion | agents.js |
| `KADER.kayip_dunya_bolum` | 2 | 0 | 100 | Missing world sections written per completion | agents.js |
| `KADER.butce_yeni` | 60000 | 2000 | 1000000 | Creations per judgment call (chars) | agents.js |
| `ADLANDIRMA.parti` | 12 | 1 | 500 | Records per naming call | agents.js |
| `ADLANDIRMA.deneme` | 2 | 0 | 20 | Re-tries of an unnamed record | agents.js |
| `ADLANDIRMA.paralel` | 4 | 1 | 32 | Naming batches in parallel | agents.js |
| `ADLANDIRMA.lehce_denetim` | 1 | 0 | 1 | Retry names violating the world dialect | agents.js |
| `KONSEY.siklik_varsayilan` | 4 | 0 | 100 | Council every N epochs if world setting unset | konsey.js |
| `AG.oto_onar` | 1 | 0 | 1 | Rule network repair at epoch end | agonar.js |
| `AG.kader_oto` | 1 | 0 | 1 | Fate network repair at epoch end | agonar.js |
| `AG.kader_parti` | 12 | 1 | 200 | Records per bond-suggestion call | agonar.js |
| `AG.kader_cag_tavan` | 36 | 0 | 100000 | Weak records Fate looks at per epoch | agonar.js |
| `AG.oncelik_payi` | 50 | 0 | 100 | Share for unbonded events/legends/traditions (%) | agonar.js |
| `AG.ilgili_parti` | 40 | 1 | 1000 | Vague bonds named per call | agonar.js |
| `AG.ilgili_cag_tavan` | 80 | 0 | 100000 | Vague bonds named per epoch | agonar.js |
| `OLCUM.yavas_sn` | 120 | 5 | 3600 | A model call slower than this is "slow" (s) | olcum.js |
| `OLCUM.sakla_cag` | 100 | 1 | 10000 | Epochs of model metrics kept | olcum.js |
| `OLCUM.ortalama_cag` | 6 | 1 | 1000 | ETA: epochs averaged | olcum.js |
| `DEFTER.sakla_cag` | 6 | 1 | 200 | Epochs kept in the action ledger | defter.js |
| `YEDEK.cag` | 10 | 1 | 200 | Last epoch backups kept | denge.js |
| `YEDEK.onluk` | 10 | 1 | 100 | Backups of epochs that are multiples of this are always kept | denge.js |
| `YEDEK.elle` | 30 | 1 | 500 | Manual backups kept | denge.js |
| `YEDEK.guvenlik` | 5 | 1 | 100 | Safety backups kept per kind | denge.js |
| `YEDEK.ikinci` | 20 | 1 | 1000 | Backups kept in the second target | denge.js |
| `TOPLU.eszamanli` | 1 | 1 | 4 | Bulk deepen: records processed at once | toplu.js |
| `TOPLU.bekle_sn` | 0 | 0 | 600 | Bulk deepen: wait between records (s) | toplu.js |
| `TOPLU.yeniden_dene` | 2 | 0 | 5 | Bulk deepen: retries of a failed record | toplu.js |
| `TOPLU.havuz_bekle_sn` | 5 | 1 | 600 | Bulk deepen: re-check interval when pool is full (s) | toplu.js |
| `TOPLU.yeniden_bekle_sn` | 3 | 0 | 600 | Bulk deepen: wait before retrying a failed record (s) | toplu.js |
| `TOPLU.gunluk_satir` | 200 | 20 | 5000 | Bulk job log lines kept | toplu.js |
| `SUNUCU.gunluk_api` | 300 | 1 | 100000 | Events returned by the live-log history API | server.js |
| `SUNUCU.tamamla_gecikme` | 1500 | 0 | 600000 | Delay of automatic completion after startup (ms) | server.js |
| `BOS_DUNYA.dagit_bekle` | 1 | 0 | 1000 | Empty habitable world gets a son after this many empty epochs | bosdunya.js |
| `TANRI_ELI.dagitim_verici_en_az` | 2 | 1 | 100 | Min active sons that must remain in a world for one to leave in auto-distribution | oyuncu.js |

Non-tunable constants used by the pipeline (should become tunables in the new app per the user's "no unconfigurable
constants" rule): `OLUMLU_AJAN = {default_count: 4, ap: 3, max_turns: 12, types: [people, faction, cult, settlement,
mortal, species], intelligence_threshold: 55}`; `RARITIES[*].maxTurns` (11, 13, 15, 17, 19, 21); SSE ping 20 s;
stream text flush 150 ms; tool-writing event every ~200 chars; structured progress once per second; live-log prune
every 100 inserts; metrics prune every 50 inserts; notification title 90 chars; error reason truncations
(160/200/120/400).

World-setting columns (per world, UI settings, not `tanimla`): `olumlu_sayisi` (mortal agents per epoch, default 4),
`olumlu_paralel` (default 1), `konsey_sikligi` (default 4), `ogul_dagitim` ('otomatik'|'elle', default auto),
`modeller` (DROP — Haiku only), `bildirim_ayar`, `denge_ayar`; per world in a cosmos `dunyalar.olumlu_ajan` (manual
quota or NULL).

---

## 14. Known bugs / design smells (and how the new design should avoid them)

1. **Model override exists** (`dunya.modeller`, Sonnet/Opus, effort). Violates the Haiku-only rule → hard-code Haiku.
2. **Fate double-apply window**: `kaderHukmu` commits before `cag_durum.fate=1` is saved; a crash in between re-runs
   Fate on resume and re-judges/rewards current-epoch records. → Persist the phase marker in the same transaction as
   the verdict application (as the engine already does).
3. **Epoch words not idempotent**: `cagKelimeleri` and `yerelTanriDogur` run outside the transition transaction and
   before it; a crash before the transition commit re-adds words. → Move them into the transition transaction.
4. **Breathing transaction captures foreign writes**: while the engine/transition transaction is open (yielding to the
   event loop), concurrent content jobs and HTTP god actions write into the same SQLite transaction and are rolled
   back if the engine fails (and god-action `SAVEPOINT`s nest inside it). → Run the engine on a dedicated connection /
   worker, or block world writes from other jobs during engine/transition, or make background jobs queue their writes.
   *Rewrite:* each engine stage runs in a process of its own (`epoch/engine_process.py`, on by `AERONA_WORK_IN_PROCESSES`)
   with its own connection. One fair write gate is shared across threads and processes: a server write waits its turn
   asynchronously, and the engine yields between steps while a write is waiting. The generation that marks stale state
   is shared too. Events and step errors come back through a queue, and stats come back with the stage. The startup
   and background repairs run in the same process (`services/integrity/maintenance.py`), with their repair log and
   events sent back. The book is built, kept and rendered in a process of its own (`services/books/worker.py`). The
   server's loop therefore never waits on the engine, the repairs or the book. `tests/epoch/test_the_loop_stays_free.py`
   fails when any of them holds the loop longer than 0.3 s (measured on an epoch-8 world: up to 8.7 s before, 8 ms after).
5. **Global mutable year range** (`yilAraligi`): background jobs that write chronicle lines during a phase get that
   phase's year range; after the transition the range is reset only for the new epoch. → Pass the year (or phase)
   explicitly with each chronicle write.
6. **Genesis lock is fake**: the genesis route only emits `busy` and checks `mesgulMu()`; it never sets the in-memory
   lock, so other locked operations could start during genesis (content jobs check a `busy.type=='genesis'` that is
   never set). → Use the real lock.
7. **Stop is cooperative only at turn boundaries**; in-flight LLM calls continue for up to 7–8 minutes; the transition
   cannot be stopped. → Cancellation tokens propagated to LLM calls (abort), with resume semantics unchanged.
8. **Error classification by regex on (Turkish/English) message text** (transient vs permanent; notification filter
   `/denenecek|deneniyor|telafi edilecek/`). → Typed exceptions and an explicit `retryable`/`will_retry` field on
   error events.
9. **Single global stop flag for network repair** (`AG_DUR`) is reset on every new `agKader` start, so starting a job
   cancels a pending stop of another one. → Per-job cancellation.
10. **Local god rebirth blocked forever** if a dead foreign god has `olum_cag` NULL: `epoch − COALESCE(NULL, epoch) = 0
    < mourning` is always true. → Treat missing death epoch as "long ago".
11. **Auto-deepen candidates ignore status**: the query selects every record without depth, including rejected ones.
    → Filter to canon/dead/fulfilled like bulk deepening does.
12. **Stale-epic comment vs code**: comment says living sons' deepening is refreshed too; code only refreshes son epics
    and the creator's epic/deepening. Decide explicitly.
13. **Auto-deepen busy-waits** by polling (`oto_bekle_sn` × `oto_bekle_deneme`) and then still enqueues; bulk deepen
    does the same with `{queue:false}` and string-matching the error text (`/en çok \d+ iş|zaten işleniyor|Yaratılış/`).
    → A priority queue in the job pool (manual > auto > stale-epic) instead of polling and message matching.
14. **Events emitted via `bus.emit` directly** (toplu.js, genesis route, server) lack the epoch stamp. → One emit API.
15. **SSE without event ids/replay**; history comes from a separate endpoint and noisy kinds are not persisted. →
    Use `id:` + `Last-Event-ID` replay from the persisted log.
16. **Phase 0 not counted**, and phase events are only emitted for phases that actually run on resume, which confuses
    the ETA (resumed epochs have partial phase timings and long durations). → Record per-phase durations explicitly
    (table) instead of reconstructing from the live log; skip resumed epochs in ETA averages.
17. **`busy.son_id` mutation** with concurrent son turns is approximate (first of the running set). → Expose the set only.
18. **Voices and council are "attempt once"**: a crash or model failure silently skips them for the epoch. Acceptable
    but should be visible (event/notification) and optionally re-triable from the UI.
19. **Dropped sons after resume**: dropped-turn retry happens only in the same process; if the process restarts after
    phase 1 is marked done, sons that failed twice are simply skipped (they did not act). Fine, but surface it.
20. **Mortal phase retry is immediate** (no backoff) while son retry is deferred to phase end — inconsistent.
21. **Many hard-coded numbers** listed in §13.5 violate the user's "no unconfigurable constants" rule → make them
    tunables.
22. **Turn context serialization is lossy by type** (drops nested arrays/objects in non-array fields) and is a JSON blob
    on the son row; `tur_ctx` and `tur_cag` are left stale after the turn (only `tur_ap` is nulled). → Dedicated
    `agent_turn_state` table keyed by (agent, epoch) with explicit schema; delete on completion.
23. **Turkish-specific post-processing in the pipeline** (`ekleriDoldur` suffix dictionary, `ekDuzelt`, stream
    category regexes) — LANGUAGE-SPECIFIC: drop or replace.
24. **Backups use `VACUUM INTO` synchronously on the main connection** before each epoch; for large DBs this blocks the
    server. → Run in a worker/thread or use the SQLite online backup API incrementally.
</content>
</invoke>
