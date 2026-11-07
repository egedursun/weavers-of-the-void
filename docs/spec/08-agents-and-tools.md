# 08 — Agents and tools (the LLM layer)

Sources: `src/llm.js` (Agent SDK wrapper), `src/agents.js` (all world-level agent roles), `src/tools.js` (son tools),
`src/world.js` (context builders and budgets), `src/gorselyon.js` + `src/gorsel-uret.js` (image direction and local
image generation), plus appended parts for `konsey.js`, `kozmos.js`, `agonar.js`, `olumluler.js` (council, son chat,
linguist, new world, Fate bond suggestion, mortal agents and their tools).

Prompt texts live in **09-prompts.md** and are referenced here by id. The epoch orchestration (when each agent runs,
concurrency, events, resume) is in **10-epoch-pipeline.md**.

## 1. Model policy (user rule)

- **Every LLM call uses Claude Haiku. No fallback, no escalation to Sonnet/Opus, no per-role model choice.**
- Old behaviour to drop: `modelFor(key)` read a per-world JSON (`dunya.modeller`) keyed by rarity
  (`yaygin…mitik`) and job (`kader`, `yaratilis`, `cagirma`, `derinlik`, `vahiy`), defaulting to `haiku`; the UI let the
  player pick `haiku|sonnet|opus`; `effort` (`low`) was passed only for non-Haiku models.
- New: a single constant `LLM_MODEL` (current Haiku id) used by both call kinds; no `effort`; metrics still record
  `model` for audit.
- Authentication (old): the local Claude Code login (Max subscription) via the Agent SDK; `ANTHROPIC_API_KEY` is
  deleted from the child env so the subscription is used. Keep this behaviour (the new backend runs the Agent SDK for
  Python with the same isolation, see §2.1).

## 2. LLM wrapper (old `src/llm.js`)

### 2.1 Isolation of every SDK call

- `cwd` = an empty temp dir (`$TMP/aerona-agents`) so agents never see the project folder.
- env = process env + `CLAUDE_AGENT_SDK_CLIENT_APP=aerona/<version>`, `ENABLE_CLAUDEAI_MCP_SERVERS=false` (agents must
  not see the user's claude.ai connectors — Notion, Gmail, Drive…), with `ANTHROPIC_API_KEY` removed.
- `tools: []` (no built-in tools), `settingSources: []`, `persistSession: false`, `strictMcpConfig: true`.
- Kill switch: env `AERONA_LLM_YOK` (→ new `AERONA_LLM_DISABLED`) makes every call throw `LLM disabled` (a
  *permanent* error, never retried). Tests run with it.

### 2.2 Structured call — `structured({name, system, prompt, schema, timeout, on_progress, on_retry, attempts})`

1. `attempts` defaults to `model.attempts` (3); agents.js always passes `fate.model_attempts` (3).
2. Each attempt runs one SDK `query()` with `outputFormat = {type: 'json_schema', schema}`, `maxTurns =
   max(1, model.structured_steps)`, abort timer = `timeout` (default `model.structured_timeout` 300 s).
3. With `on_progress`, partial messages are streamed: every delta's text/partial_json/thinking length is summed and
   reported at most once per second as `{chars, stream}`; a final `{chars, stream, done: true, status: ok|error,
   error?}` is always sent (also on failure) so the UI line never hangs. Each call gets a unique stream id
   `a{n}-{timestamp}` so concurrent writers do not interleave.
4. Result: `structured_output`, or the first `{…}` block of `result` parsed as JSON; none → error
   `Model gave no structured output[ (subtype: errors)]`. Timeout → error `timeout ({s} s)`.
5. Retries: see §2.4. Metrics: see §2.6.

### 2.3 Agent turn — `agent_turn({name, system, prompt, server, server_factory, continuation_prompt, is_complete, on_event, max_turns, timeout, pending_job, job_traces})`

One "turn" may consist of several SDK sessions:

```
done = []                                   # successful tool calls: {tool, is_read, summary[:model.summary_chars]}
prompt_now = prompt; continuations = 0; restarts = 0
for session in range(model.turn_session_cap):            # default 6
    srv = server if session == 0 else server_factory()   # fresh MCP server; state lives in ctx
    try: result = single_session(prompt_now, srv)          # {text, status, turns}
    except e: result = {text:'', status:'error', error:str(e)}
    await_pending_job()                     # a long tool call (world/child birth) that survived the session
    if result.status == 'success' and is_complete(result.text): return result + done
    reason = {error: f"connection error ({error[:120]})", timeout: "timeout",
              error_max_turns: "step limit reached", success: "you finished without saying your word"}[status]
    no_trace = no non-read action in done
    if status == 'error' and not transient(error): break           # permanent errors are not retried
    if no_trace and status == 'error' and restarts < model.restarts:  # default 2
        restarts += 1; emit retry(name='turn', attempt=restarts+1, total=model.restarts+1, reason,
                                  wait=model.restart_wait*restarts s); sleep; continue   # same prompt
    actions = [f"{d.tool} → {d.summary}" for d in done if not d.is_read]
    nxt = continuation_prompt(actions, reason) if continuations < model.continuations else None   # default 2
    if nxt is None: break
    continuations += 1; emit retry(name='continue', attempt, total, reason, done=len(actions))
    if status == 'error': sleep(model.continue_wait)
    prompt_now = nxt
if result.status != 'success' and no non-read action in done:
    raise Error(result.error or f"Turn ended without a trace ({status})")   # the epoch retries the son later
return result + done
```

- `await_pending_job`: if `pending_job()` returns a promise (a birth tool still running after the session dropped),
  emit `retry(name='ongoing job', reason='a long action is still being processed; waiting for it to finish')` and
  await it; then add each job trace `{tool, key, summary}` from `job_traces()` to `done` unless an existing summary
  already contains its key (so the model learns about results it never received).
- `single_session`: SDK `query()` with `mcpServers {<server_name>: srv}`, `allowedTools ['mcp__<server_name>']`,
  `maxTurns`, abort timer, `includePartialMessages: true`. Streams:
  - text deltas buffered and flushed as `stream {text}` events at most every 150 ms (and before tool calls);
  - `tool_preparing {tool, id}` at a tool_use block start; `tool_writing {tool, id, chars}` roughly every 200 input
    JSON chars;
  - complete assistant messages: each text block → `thought {text}` (also remembered as the last text); each
    tool_use → `tool_call {tool, input, id}`;
  - tool results: error if `is_error` or text starts with `REJECTED`; successful ones are appended to `done`
    (`is_read` = tool in READ_TOOLS); `tool_result {text[:400], error, id}`;
  - `result` message → usage accounting; `status = subtype`, final text = `result` if success.
  - Abort (timeout) → `{status: 'timeout'}`.
  - Dev hook `AERONA_KES=N` aborts the first session after N successful non-read actions (resilience test) — keep as
    a test-only hook.
- READ_TOOLS (do not change the world, never counted as actions, never ledgered): `world_summary`,
  `look_at_world`, `inspect_entity`, `search_entities`, `my_memory`, `inspect_sibling`.

### 2.4 Retry policy (structured calls; agent turns use §2.3)

- `transient(e)` = message does NOT match the permanent regex `prompt is too long|context.?(length|window)|too many
  tokens|invalid.?api.?key|authenticat|LLM disabled` AND matches the transient regex
  `overload|rate.?limit|(status|error|http|code)\W{0,3}(429|5xx)\b|\b(429|5xx) (bad gateway|service unavailable|internal
  server error|gateway time-?out|too many requests)|ECONN|ETIMEDOUT|EPIPE|socket|network|fetch failed|exited with
  code|terminated|gave no structured output|aborted|timeout`. Numeric codes are matched with word boundaries so
  "523000 tokens" or "costs 500 essence" are not transient.
- `retry(fn, attempts)`: attempt i (1-based); on error: stop if last attempt or not transient; wait
  `[model.wait_1, model.wait_2][i-1] ?? model.wait_3` seconds (2, 6, 15) after emitting
  `retry {name, attempt: i+1, total, reason[:160], wait_ms}` (the notification hook can never break the retry).

### 2.5 Tool wrapper (old `araclariSar(tools, ctx, persist, ledger, gate)`)

Applied to every son/mortal tool handler:
1. **Serial execution**: calls of the same turn run strictly one after another (a promise chain), even if the model
   emits several tool_use blocks in one message — so a rollback of one call never undoes another's state.
2. **Gate**: if `gate(tool)` returns a reason (e.g. the son fell asleep or died mid-turn) → return
   `REJECTED: {reason}` (isError) without running.
3. **Snapshot**: before the call, shallow-copy every non-function ctx field (arrays and Sets copied).
4. Run the handler; if a `ledger` identity `{actor_kind, actor_id, actor_name}` is given and the tool is not a read
   tool, run it inside the ledger (`defter.js`: one ledger group per tool call; used by Fate to selectively undo a
   rejected creation's side effects, see §4.6).
5. On success: `persist(ctx)` (writes remaining AP + ctx counters to the son row so a crashed process resumes).
6. On exception: restore the snapshot in place (same array/Set objects are mutated back so outside references stay
   valid; keys added during the call are deleted; fallback restores only `ap`) and return the error text of 09 §11.

### 2.6 Metrics (old `olcum`)

Every call emits one record (sink bound by the epoch module, persisted to a metrics table):
`{name, model, kind: structured|agent, attempt, ms, status: success|error|partial, error[:200]?, actions? (non-read
count for agent turns), input_tokens (input + cache_read + cache_creation), output_tokens, cost_usd, turns}`.
`partial` = an agent turn that returned without `success` but left traces.

### 2.7 Tunables — `MODEL` group "Agents and model" (old `LLM_K`)

| key (new) | old | default | min | max | group | label |
|---|---|---|---|---|---|---|
| model.attempts | deneme | 3 | 1 | 10 | Agents and model | Total attempts on a transient model error (if the caller does not give its own) |
| model.wait_1 | bekle_1 | 2 | 0 | 600 | Agents and model | Wait before retrying after the 1st error (s) |
| model.wait_2 | bekle_2 | 6 | 0 | 600 | Agents and model | Wait before retrying after the 2nd error (s) |
| model.wait_3 | bekle_3 | 15 | 0 | 600 | Agents and model | Wait before retrying after the 3rd and later errors (s) |
| model.structured_timeout | yapisal_sure | 300 | 10 | 3600 | Agents and model | Default timeout of a structured call (s) |
| model.structured_steps | yapisal_adim | 8 | 1 | 20 | Agents and model | Max model steps in a structured call |
| model.agent_timeout | ajan_sure | 420 | 30 | 3600 | Agents and model | Default timeout of an agent turn (s) |
| model.agent_steps | ajan_adim | 10 | 1 | 100 | Agents and model | Default step limit of an agent turn |
| model.turn_session_cap | tur_tavan | 6 | 1 | 30 | Agents and model | Max sessions in one agent turn (restarts and continuations included) |
| model.restarts | bastan | 2 | 0 | 10 | Agents and model | Restarts of a turn that crashed without a trace |
| model.restart_wait | bastan_bekle | 3 | 0 | 600 | Agents and model | Wait before a restart (s; multiplied by the restart count) |
| model.continuations | devam | 2 | 0 | 10 | Agents and model | Max continuation sessions for a half-finished turn |
| model.continue_wait | devam_bekle | 3 | 0 | 600 | Agents and model | Wait before a continuation after a connection error (s) |
| model.summary_chars | ozet_karakter | 220 | 40 | 5000 | Context budgets | Summary of each done action in the continuation prompt (chars) |

## 3. Shared tunables used by the agents

### 3.1 `FATE` group (old `KADER_K`, several `tanimla('KADER', …)` blocks) — groups "Fate and chronicle" (FC), "Context budgets" (CB), "Agents and model" (AM)

| key (new) | old | default | min | max | group | label |
|---|---|---|---|---|---|---|
| fate.new_budget | butce_yeni | 60000 | 2000 | 1000000 | CB | Fate: creations in one judgment call (chars); those that do not fit are weighed in extra rounds in the same age |
| fate.prophecy_budget | butce_kehanet | 12000 | 500 | 200000 | CB | Fate: old prophecies (chars) |
| fate.events_budget | butce_olaylar | 20000 | 1000 | 400000 | CB | Fate: the age's events (chars) |
| fate.engine_budget | butce_motor | 12000 | 500 | 200000 | CB | Fate: engine notes (chars) |
| fate.prompt_budget | butce_istem | 140000 | 10000 | 2000000 | CB | Fate: whole judgment prompt (chars) |
| fate.chronicler_budget | butce_kronikci | 30000 | 2000 | 400000 | CB | Whole chronicler prompt (chars) |
| fate.thread_cap | iplik_tavan | 12 | 2 | 100 | FC | Open-thread cap (above it Fate closes more) |
| fate.close_max | kapat_tavan | 6 | 0 | 50 | FC | Max forced thread closings per age |
| fate.new_thread_max | yeni_iplik_tavan | 4 | 0 | 50 | FC | Max new threads per age |
| fate.stagnant_ages | durgun_cag | 4 | 1 | 100 | FC | After how many ages without progress a thread becomes a closing candidate |
| fate.long_thread | uzun_iplik | 8 | 2 | 200 | FC | After how many advances a thread should conclude |
| fate.reward_max | odul_tavan | 15 | 0 | 500 | FC | Max fame a son can receive from Fate in one age |
| fate.facts_max | gercek_tavan | 24 | 0 | 200 | FC | Max canon facts per verdict |
| fate.facts_min | gercek_en_az | 3 | 0 | 50 | FC | Min canon facts per verdict |
| fate.words_max | kelime_tavan | 10 | 0 | 100 | FC | Max words Fate adds to languages per age |
| fate.seer_true | kahin_dogru | 10 | 0 | 100 | FC | Charisma gained by the seer of a prophecy that came true |
| fate.seer_misread | kahin_yanlis | 8 | 0 | 100 | FC | Charisma lost by the seer of a misread prophecy |
| fate.reward_streak_window | odul_seri_pencere | 5 | 0 | 100 | FC | Fate reward: ages looked back for consecutive rewards (0: no decay) |
| fate.reward_streak_decay | odul_seri_azalma | 75 | 0 | 100 | FC | Fate reward: share kept per reward received in recent ages (%) |
| fate.advance_max | ilerleme_tavan | 6 | 0 | 50 | FC | Max threads Fate advances through events per age |
| fate.prophecy_fame | kehanet_un | 10 | 0 | 500 | FC | Fame to the creator son of a fulfilled prophecy |
| fate.prophecy_xp | kehanet_xp | 30 | 0 | 1000 | FC | XP to the creator son of a fulfilled prophecy |
| fate.previous_openings | onceki_acilis | 6 | 0 | 50 | FC | Previous narrative openings forbidden to the chronicler (also chronicler-chain length) |
| fate.previous_names | onceki_ad | 12 | 0 | 200 | FC | Previous age names shown to the chronicler |
| fate.word_openings | soz_acilis | 3 | 0 | 20 | FC | Last word openings forbidden to a son |
| fate.timeout | kader_sure | 480 | 30 | 3600 | AM | Fate and chronicler timeout (s) |
| fate.parallel_verdicts | hukum_paralel | 3 | 1 | 16 | AM | Fate: extra verdict rounds run at the same time |
| fate.rationale_words | gerekce_sozcuk | 24 | 4 | 400 | FC | Max words in a verdict's rationale (told in the prompt; excess cut at a sentence boundary) |
| fate.historians | tarihci | 2 | 0 | 20 | FC | Peoples that write a view per age |
| fate.belief_pairs | inanc_cift | 5 | 0 | 50 | FC | New folk beliefs written per age |
| fate.voice_timeout | ses_sure | 240 | 30 | 3600 | AM | Voices of the peoples timeout (s) |
| fate.model_attempts | model_deneme | 3 | 1 | 10 | AM | Total attempts on a transient model error |
| fate.son_timeout | ogul_sure | 420 | 60 | 3600 | AM | Son turn timeout (s) |
| fate.prescreen_description | on_eleme_aciklama | 140 | 0 | 2000 | FC | Pre-screen: shorter descriptions get a warning (chars) |
| fate.prescreen_power | on_eleme_guc | 7 | 1 | 11 | FC | Pre-screen: creations above this power outside the domain get a warning |
| fate.voice_events | ses_olay | 6000 | 500 | 100000 | CB | Events sent to the voices of the peoples (chars) |
| fate.pantheon_root_threshold | panteon_kok_esik | 50 | 1 | 100 | FC | Summoning: a root in the title/obsession of this % of sons is forbidden to the new son |
| fate.pantheon_root_min_sons | panteon_kok_en_az | 4 | 1 | 100 | FC | Summoning: min sons for measuring pantheon roots |
| fate.council_sentences | konsey_cumle | 2 | 1 | 50 | FC | Age events: sentences taken from a council row |
| fate.name_kind_rows | ad_tur_satir | 60 | 0 | 1000 | FC | Chronicler prompt: kinds of records mentioned this age (max rows) |
| fate.name_kinds_budget | butce_ad_tur | 3000 | 0 | 50000 | CB | Chronicler prompt: name-and-kind list (chars) |
| fate.word_tic_window | soz_tik_pencere | 8 | 0 | 200 | FC | Word tic: last words examined |
| fate.word_tic_threshold | soz_tik_esik | 60 | 1 | 100 | FC | Word tic: a word in this % of recent words is forbidden |
| fate.shared_tic_window | soz_ortak_pencere | 24 | 0 | 500 | FC | Shared tic: last words of all sons examined |
| fate.shared_tic_threshold | soz_ortak_esik | 30 | 1 | 100 | FC | Shared tic: a root in this % of recent words is forbidden to everyone |
| fate.previous_verdicts_budget | butce_onceki_hukum | 2500 | 0 | 50000 | CB | Chronicler prompt: previous age's Fate verdicts (chars) |
| fate.view_opening | bakis_acilis | 160 | 20 | 2000 | FC | Historian prompt: length of the previous account's opening shown (chars) |
| fate.prescreen_motif | on_eleme_motif | 3 | 1 | 50 | FC | Pre-screen: warning if this many tired images appear in the description |
| fate.chronicler_tenure | kronikci_sure | 6 | 1 | 1000 | FC | Chronicler continuity: min ages a chronicler writes before handing over |
| fate.shared_tic_forms | soz_ortak_bicim | 3 | 1 | 20 | FC | Shared tic: forms shown from a root family |
| fate.shared_tic_max | soz_ortak_tavan | 3 | 0 | 20 | FC | Shared tic: max roots forbidden |
| fate.word_tic_min | soz_tik_en_az | 4 | 1 | 200 | FC | Word tic: min words before looking |
| fate.word_tic_max | soz_tik_tavan | 3 | 0 | 20 | FC | Word tic: max words forbidden in one word |
| fate.word_opening_words | soz_acilis_kelime | 3 | 1 | 20 | FC | Length of the forbidden word opening (words) |
| fate.opening_words | acilis_kelime | 14 | 1 | 80 | FC | Length of the forbidden narrative opening shown to the chronicler (words) |
| fate.summary_min | ozet_en_az | 120 | 0 | 2000 | FC | Shortest age summary (chars) |
| fate.thread_advancers | iplik_ilerleten | 3 | 0 | 50 | CB | Fate prompt: last creations advancing each thread |
| fate.close_candidates_shown | kapat_aday_goster | 6 | 0 | 100 | CB | Fate prompt: threads written as priority closing candidates |
| fate.chronicle_engine_budget | butce_kronik_motor | 6000 | 500 | 200000 | CB | Chronicler: engine notes (chars) (also the floor of data budgets) |
| fate.seer_charisma | kahin_karizma | 40 | 0 | 100 | FC | Charisma of a seer whose charisma is unknown |
| fate.creator_belief_peoples | inanc_yaratici_halk | 6 | 0 | 100 | FC | Largest peoples whose belief about the creator can be written in one age |
| fate.born_budget | butce_dogan | 20000 | 500 | 400000 | CB | Fate prompt: "born of the world's own course" section (chars; overflow named in a separate naming round) |
| fate.world_records_budget | butce_dunya_kayit | 4000 | 0 | 100000 | CB | Fate prompt: this age's world records list (chars) |
| fate.chronicle_side_share | kronik_yan_pay | 25 | 0 | 100 | CB | Chronicler prompt: max share for engine results and unnamed records (% of the data budget) |
| fate.opening_window | acilis_pencere | 12 | 0 | 200 | FC | Opening pattern: last age narratives examined |
| fate.opening_pattern_threshold | acilis_kalip_esik | 3 | 2 | 50 | FC | Opening pattern: a bigram in this many openings is forbidden |
| fate.fix_opening | acilis_duzelt | 1 | 0 | 1 | FC | If the narrative opens with a forbidden pattern, ask the chronicler to rewrite only the first sentence (1 on, 0 off) |
| fate.name_root_threshold | ad_kok_esik | 3 | 2 | 100 | FC | Age name: a root in this many previous names is forbidden |
| fate.complete_missing_worlds | eksik_dunya_tamamla | 1 | 0 | 1 | FC | If the chronicler skips a world's section, make a second short call for those worlds (1 on, 0 off) |
| fate.lost_world_sections | kayip_dunya_bolum | 2 | 0 | 100 | FC | Missing world sections written for past ages per completion run |
| fate.lost_chronicles | kayip_kronik | 3 | 0 | 100 | FC | Missing age chronicles written per completion run |
| fate.lost_timeout | kayip_sure | 300 | 30 | 3600 | AM | Missing age chronicle timeout (s) |
| fate.seer_factor | kahin_kat | 2 | 1 | 20 | FC | Fame and XP multiplier from a fulfilled prophecy for a son with the seer power |
| fate.reward_xp_factor | odul_xp_kat | 2 | 0 | 50 | FC | Son XP per fame point given by Fate |

### 3.2 `FOLK_BELIEF` group (old `HALK_INANC_K`) — FC

| key | old | default | min | max | label |
|---|---|---|---|---|---|
| folk_belief.pattern_window | kalip_pencere | 12 | 0 | 500 | Folk belief: last beliefs examined for piled-up patterns in the distortion sentence |
| folk_belief.pattern_threshold | kalip_esik | 30 | 1 | 100 | Folk belief: a pattern in this % of recent beliefs is forbidden |
| folk_belief.name_letters | ad_harf | 40 | 3 | 200 | Folk belief: max letters of the god name the model gives |

### 3.3 `SUMMON` group "Son summoning and birth" (SB) (old `CAGIRMA_K`)

| key | old | default | min | max | group | label |
|---|---|---|---|---|---|---|
| summon.existence_start | varlik_baslangic | 60 | 0 | 100 | SB | A new son's existence (also used when unknown) |
| summon.world_unowned | dunya_sahipsiz | 200 | 0 | 10000 | SB | New son's world: points per unworshipping community (%) |
| summon.world_living | dunya_canli | 30 | 0 | 10000 | SB | New son's world: points per living community (%) |
| summon.world_son | dunya_ogul | 300 | 0 | 10000 | SB | New son's world: minus points per son already there (%) |
| summon.domain_shift | alan_kaydir | 7 | 1 | 100 | SB | If both domains are the same, the second is taken this many places further |
| summon.rival_domain | rakip_alan | 20 | 0 | 100 | SB | Relation loss with a sibling per shared domain |
| summon.parent_relation | ebeveyn_iliski | 40 | -100 | 100 | SB | A child's initial relation with its parent |
| summon.co_parent_relation | es_iliski | 30 | -100 | 100 | SB | A child's initial relation with its other parent |
| summon.birth_rolls | dogur_deneme | 20 | 1 | 1000 | SB | Max rolls for the child's rarity (until lower than the parent) |
| summon.chronicle | kronik | 15 | 0 | 500 | CB | Recent events in the summoning prompt |
| summon.rebel_ambition | isyan_hirs | 60 | 0 | 100 | SB | Son prompt: rebel-prone above this ambition (if loyalty is low) |
| summon.rebel_will | isyan_irade | 70 | 0 | 100 | SB | Son prompt: rebel-prone above this will (if loyalty is low) |
| summon.opportunity_budget | firsat_butce | 2500 | 0 | 100000 | CB | Son prompt: opportunities section (chars) |
| summon.power_effect_cap | guc_etki_tavan | 2 | 1 | 100 | SB | Max sons in the pantheon carrying the same power effect (excess falls back to the least used effect) |
| summon.passion_default | tutku_varsayilan | 50 | 0 | 100 | SB | A new son's passion not written by the model |

### 3.4 `GENESIS` group "Genesis" (old `YARATILIS_K`)

| key | old | default | min | max | label |
|---|---|---|---|---|---|
| genesis.regions_min | bolge_en_az | 3 | 1 | 50 | Min regions at genesis |
| genesis.regions_max | bolge_en_cok | 5 | 1 | 50 | Max regions at genesis |
| genesis.region_width | bolge_genislik | 60 | 0 | 100 | Width of the first regions |
| genesis.region_power | bolge_guc | 8 | 1 | 11 | Power level of the first regions |
| genesis.sky_brightness | gok_parlaklik | 70 | 0 | 100 | Brightness of the first celestial body |
| genesis.sky_influence | gok_etki | 60 | 0 | 100 | Influence of the first celestial body |
| genesis.sky_power | gok_guc | 7 | 1 | 11 | Power level of the first celestial body |
| genesis.relation | iliski | 80 | 0 | 100 | Max magnitude (±) of the initial relation between the first sons |
| genesis.timeout | sure | 360 | 30 | 3600 | Genesis timeout (s) (group Agents and model) |

### 3.5 `AWAKEN` group "Awakening of the peoples" (old `UYANIS_K`)

| key | old | default | min | max | label |
|---|---|---|---|---|---|
| awaken.batch_max | tavan | 3 | 1 | 20 | Max peoples in one awakening batch (one call); more are split into batches |
| awaken.timeout | sure | 300 | 30 | 3600 | Awakening timeout (s) |
| awaken.words_min / words_max | kelime_en_az / en_cok | 6 / 10 | 0 / 1 | 100 / 200 | Min / max words of a new language |
| awaken.power | guc | 4 | 1 | 11 | Power level of an awakened people |
| awaken.first_peoples | ilk_halk | 2 | 1 | 1000 | Peoples that awaken by themselves at startup in a world without peoples |
| awaken.people_population (+_min, _max) | halk_nufus | 20000 (500, 5000000) | 1 | 1e9/2e9 | People's population (if the model gives none) and its clamp |
| awaken.people_martiality / magic / craft | halk_savascilik / buyu / zanaat | 40 / 30 / 45 | 0 | 100 | People's stats if the model gives none |
| awaken.people_faith | halk_inanc | 60 | 0 | 100 | People's piety |
| awaken.language_spread / complexity / sanctity / power | dil_* | 30 / 45 / 25 / 3 | 0/1 | 100/11 | New language stats |
| awaken.settlement_population (+_min, _max) | kent_nufus | 3000 (100, 500000) | 1 | 1e9/2e9 | First settlement population and clamp |
| awaken.settlement_prosperity / defence / piety / power | kent_* | 45 / 30 / 60 / 3 | | | First settlement stats |
| awaken.resource_abundance / value / might / power | kaynak_* | 70 / 50 / 35 / 3 | | | People's resource stats |
| awaken.knowledge_level / spread / power | bilgi_* | 1 / 20 / 2 | 1/0/1 | 100/100/11 | First knowledge stats |
| awaken.tradition_spread / rigidity / power | gelenek_* | 60 / 50 / 2 | | | Tradition stats |

### 3.6 `CONTENT` group "Content jobs" (CJ) (old `ICERIK_K`)

| key | old | default | min | max | group | label |
|---|---|---|---|---|---|---|
| content.prompt_batch | prompt_parti | 24 | 1 | 500 | CJ | Max entities in one image-prompt batch |
| content.prompt_description | prompt_aciklama | 500 | 20 | 20000 | CB | Image-prompt prompt: entity description (chars) |
| content.prompt_min | prompt_en_az | 20 | 0 | 2000 | CJ | Image prompts shorter than this are not accepted (chars) |
| content.prompt_max | prompt_tavan | 1200 | 50 | 20000 | CJ | Max length of a cosmic body's image prompt (chars) |
| content.cosmos_batch | kozmos_parti | 16 | 1 | 500 | CJ | Cosmic bodies whose image prompt is written in one batch |
| content.cosmos_world | kozmos_dunya | 400 | 20 | 20000 | CB | Cosmos prompt: world description (chars) |
| content.cosmos_other | kozmos_diger | 300 | 20 | 20000 | CB | Cosmos prompt: star and foreign god description (chars) |
| content.revelation_wisdom | vahiy_bilgelik | 130 | 1 | 1000 | CJ | Detail of the world summary the revelation sees (like wisdom) |
| content.revelation_power_max | vahiy_guc_tavan | 10 | 1 | 11 | CJ | Highest power level of a revelation |
| content.god_traces | tanri_iz | 160 | 0 | 10000 | CB | God's epic: traces in the chronicle (rows) |
| content.god_traces_deepen | tanri_iz_derin | 80 | 0 | 10000 | CB | God's deepening: traces in the chronicle (rows) |
| content.deepen_bonds | derin_bag | 20 | 0 | 1000 | CB | Deepening: neighbouring bonds |
| content.deepen_chronicle | derin_kronik | 20 | 0 | 1000 | CB | Deepening: recent events |
| content.epic_traces | destan_iz | 120 | 0 | 10000 | CB | Son's epic: traces in the chronicle (rows) |

### 3.7 `NARRATIVE` group (CJ) (old `ANLATI_K`) — item counts of narrative schemas

| key | default min / max | label |
|---|---|---|
| narrative.epic_sections_min / _max (destan_bolum_en_az/en_cok) | 3 / 7 | Sections of the god's epic |
| narrative.god_names_* (tanri_ad_*) | 2 / 6 | God depth: names |
| narrative.secrets_* (sir_*) | 2 / 4 | God depth: secrets |
| narrative.fears_* (korku_*) | 1 / 3 | God depth: fears |
| narrative.prohibitions_* (yasak_*) | 2 / 5 | God depth: prohibitions |
| narrative.gifts_* (armagan_*) | 2 / 5 | God depth: gifts |
| narrative.sayings_* (soz_*) | 2 / 4 | Depth: mortals' sayings |
| narrative.rumours_* (soylenti_*) | 3 / 5 | Depth: rumours |
| narrative.details_* (ayrinti_*) | 3 / 6 | Depth: sensory details |

Bounds: every `_min` 0..50, every `_max` 1..100. Schema uses `minItems = min`, `maxItems = max(1, min, max)`.

### 3.8 `NAMING` group (AM) (old `ADLANDIRMA_K`)

| key | old | default | min | max | label |
|---|---|---|---|---|---|
| naming.batch | parti | 12 | 1 | 500 | Records per naming call (not a limit: all pending records are named in batches in the same age) |
| naming.attempts | deneme | 2 | 0 | 20 | Re-tries of a record that could not be named; then its temporary description is cleaned and it is left for deepening |
| naming.parallel | paralel | 4 | 1 | 32 | Naming batches (calls) running at once |
| naming.dialect_check | lehce_denetim | 1 | 0 | 1 | An invented name violating its world's dialect (forbidden vowel) is retried once (1 on, 0 off) |

### 3.9 `CONTEXT` group "Context budgets" (old `BAGLAM_K`, world.js)

| key | old | default | min | max | label |
|---|---|---|---|---|---|
| context.cache_batch | kanon_parti | 500 | 1 | 100000 | Engine cache: changed entities re-read in batches of this size |
| context.son_geography | ogul_cografya | 5000 | 500 | 100000 | Son: geography and inhabitants (chars) |
| context.son_map | ogul_harita | 2500 | 200 | 50000 | Son: map (chars) |
| context.son_cosmos | ogul_kozmos | 1500 | 200 | 30000 | Son: other worlds (chars) |
| context.son_language | ogul_dil | 1600 | 200 | 30000 | Son: languages and lexicon (chars) |
| context.son_locationless | ogul_konumsuz | 1500 | 200 | 30000 | Son: legends and traditions (chars) |
| context.son_chronicle | ogul_kronik | 2200 | 200 | 30000 | Son: recent events (chars) |
| context.son_summary | ogul_ozet | 14000 | 2000 | 200000 | Son: whole world summary (chars) |
| context.son_memory_budget | ogul_hafiza | 5000 | 500 | 100000 | Son: memory (chars) |
| context.son_prompt | ogul_istem | 24000 | 4000 | 400000 | Son: whole turn prompt (chars) |
| context.son_chronicle_rows | ogul_kronik_satir | 10 | 1 | 200 | Son: rows of recent events (+ wisdom/8) |
| context.tool_factor | arac_kat | 3 | 1 | 50 | Read tools: how many times longer recent events and memories are when a cut section is shown in full |
| context.short_cosmology | kisa_kozmoloji | 500 | 50 | 100000 | Length of the cosmology in mortals' short world header (chars) |
| context.section_floor | bolum_taban | 600 | 0 | 100000 | Min room for each context section (chars; whole if shorter) |
| context.budget_trim_min | butce_kirp_en_az | 120 | 0 | 10000 | Min room for a non-fitting line to enter truncated (chars) |
| context.memory_worshippers | hafiza_tapan | 12 | 0 | 1000 | Son memory: worshippers shown by name (rest by count) |
| context.son_threads | ogul_iplik | 6 | 1 | 100 | Son: open stories shown |
| context.fate_geography / fate_map / fate_cosmos / fate_language / fate_locationless / fate_chronicle | kader_* | 9000 / 4000 / 2500 / 3000 / 3000 / 4000 | | | Fate: same sections (chars) |
| context.fate_summary | kader_ozet | 26000 | 2000 | 400000 | Fate: whole world summary (chars) |
| context.fate_chronicle_rows | kader_kronik_satir | 24 | 1 | 400 | Fate: rows of recent events |
| context.mortal_context | olumlu_baglam | 12000 | 2000 | 200000 | Mortal: whole context (chars) |
| context.memory_creations / recollections / about / beliefs / words | hafiza_yaratim / ani / hakkinda / inanc / soz | 1600 / 1200 / 900 / 900 / 1000 | 100–200 | 50000 | Son memory section budgets (chars) |
| context.repeat_threshold | tekrar_esik | 3 | 2 | 50 | "You are repeating yourself" warning: creations of the same subtype (group Son tools) |
| context.repeat_window | tekrar_pencere | 20 | 1 | 500 | Repeat check: last creations examined (Son tools) |
| context.son_tree | ogul_agac | 90 | 10 | 5000 | Son: location-tree rows (+ wisdom) |
| context.fate_tree | kader_agac | 220 | 10 | 10000 | Fate: location-tree rows |
| context.son_chronicle_wisdom | ogul_kronik_bilgelik | 8 | 1 | 100 | Son: every this much wisdom adds one recent-event row |
| context.son_language_samples / fate_language_samples | ogul_dil_ornek / kader_dil_ornek | 6 / 10 | 0 | 200 | Sample words per language |
| context.language_near_extra / far_missing / far_min | dil_yakin_ek / dil_uzak_eksik / dil_uzak_en_az | 4 / 3 / 3 | 0 | 100 | Language sample adjustments for near/far languages |
| context.locationless_rows | konumsuz_satir | 45 | 1 | 1000 | Legends and traditions: newest records shown |
| context.inspect_lexicon | incele_sozluk | 40 | 0 | 2000 | Entity inspection: words shown from a language's lexicon |
| context.inspect_facts | incele_gercek | 8 | 0 | 200 | Entity inspection: canon facts shown |
| context.facts_default | gercek_sayi | 12 | 1 | 500 | Canon facts: default rows |
| context.chronicle_default | kronik_sayi | 12 | 1 | 500 | Recent events: default rows |
| context.search_results | arama_sonuc | 25 | 1 | 500 | search_entities: max results |
| context.lexicon_default | sozluk_sayi | 400 | 1 | 100000 | Default words from a language's lexicon |
| context.memory_creations_n / recollections_n / about_n / words_n | hafiza_*_sayi | 30 / 12 / 10 / 10 | 1 | 500 | Son memory: row counts |
| context.thread_related / thread_name / thread_stale / thread_advanced | iplik_* | 3 / 4 / 50 / 1 | 0 | 100/1000 | Story priority scoring for a son (see 09 §2.9) |
| context.doom_warning | kiyamet_uyari | 30 | 0 | 100 | Doom clock shown in prompts at this % of the threshold (group Doom) |

## 4. Agent roles

Each role: purpose · trigger · prompt ids (09) · inputs and budgets · output schema · post-processing · DB writes ·
failure behaviour. All structured roles go through `ask(key, args)` = `structured({…, attempts:
fate.model_attempts, on_retry: live stream, name: metrics label})`. Metrics labels (old `OLCUM_AD`): summon →
"Son summoning", depth → "Deepening", fate → "Fate and chronicle", revelation → "Revelation", genesis → "Genesis"
(individual calls override with their own `name`: "Fate", "Chronicler", "Naming", "Voices of the peoples").

Live "writing" events: structured calls with `on_progress` emit `writing {who, topic?, chars, stream, done?,
status?, error?}` where `who` ∈ Genesis, Summoning, Fate, Chronicler, Revelation, Bard, Lore writer, Awakening of the
peoples.

### 4.1 Genesis (old `genesis`)

- Purpose: create the world from the player's seed. Trigger: `POST /api/genesis` (only if no world exists, else
  error "A world already exists.").
- Prompt: `genesis` (09 §4.1). Timeout `genesis.timeout`.
- Wizard: if wizard settings are supplied, `wizard_clean({...wizard, seed, tone})` (sihirbaz.js) — its seed/tone
  override; settings text is inserted; settings JSON stored on the world; region stats are biased by
  `region_bias(stats, settings)` (sihirbaz `bolgeEgilimi`).
- Post-processing & writes (one transaction):
  1. Insert world row id 1: name, god_name, seed, cosmology, naming_rule, tone, epoch 1, year 0,
     god_essence = `balance.start_essence` (150), god title/appearance/temperament/image prompt.
  2. Regions (first `max(min,max)`): entity type `region`, `unique_name(name)`, subtype, description, stats =
     region_bias({width: genesis.region_width, danger, fertility, magic (clamped 0–100)}), power
     `genesis.region_power`, age 1, image prompt, source `god`.
  3. First celestial: type `celestial`, stats {brightness, influence} from tunables, power `genesis.sky_power`,
     domain, age 1, source `god`; `world.age_star = id`.
  4. Three sons via `insert_son(profile[i], rarity[i] ∈ [common, rare, legendary], age 1)` (§4.4).
  5. Relations: for each `{i, j, value, note}` with valid distinct indices → `relation_change(son_i, son_j, value, note)`.
  6. Chronicle (kind `god`, no son): "{god}, {title}, named the void {world}, separated with his own hand the lands
     and waters of {region names comma-joined} and hung {star} in the sky."; per son (kind `birth`, son id): "{god}'s
     son {name}, {title}, awoke with the domains {d1} and {d2}."
  7. `cosmos_transition()` (db): the new world becomes the first world of its own cosmos (see cosmos spec 06).
- After genesis (server): emit `genesis_done`; then `awaken.peoples(wizard.peoples ?? 2)` and emit
  `Awakened peoples: {names}`.

### 4.2 Startup completion orchestrator (old `eksikleriTamamla(publish)`)

Runs at server start / on demand (`complete` lock in 10). Steps, each isolated with try/catch → `error` event:
1. Resolve orphaned long jobs (`resolve_old_pending_jobs`, §4.5.6); for each refund publish
   `{son}: the price of the half-finished birth was refunded.`
2. Lost chronicles backfill (§4.8).
3. No world → stop.
4. God without image prompt → `system "{god}'s likeness is being drawn…"` + creator portrait (§4.3).
5. Each son lacking powers or existence → `system "{son}'s powers and existence are awakening…"` +
   `complete.son_powers`; update powers = `clean_powers(out.powers)`, existence, image prompt only if empty.
6. No canon people → `system "The first mortal peoples are awakening in the lands…"`, awaken
   `awaken.first_peoples`, publish names.
7. Any entity without image prompt → one batch of `image_prompts.entities(content.prompt_batch)`; publish
   `{n} entities got an image prompt.`
8. Any world/star/foreign god without image prompt → `image_prompts.cosmos`; publish `{n} cosmic bodies got an image prompt.`
9. Pending records → naming (§4.9).
10. Every foreign god without depth (ordered by id) → `foreign_god.deepen`; publish `foreign_god_deepened {id, name}`.
11. No celestial entity at all → `system "The first star is being hung in the sky…"`; revelation with the first-star
    text and type `celestial`; `world.age_star = id`.

### 4.3 Creator portrait (old `tanriSureti`)

Prompt `creator.portrait`, schema `schema.creator_god`. Writes world.god_title, god_appearance, god_temperament,
god_image_prompt. Manual trigger "redraw likeness" (parallel job `t:portrait`).

### 4.4 Summon son / birth child (old `cagir`, `dogur`, `insertSon`, `ogulDunyasi`, `temizGucler`)

- Triggers: player summons (paid `COSTS.summon` 30 essence; optional target world) → `summon.son`; a son's
  `birth_child` tool → `dogur(parent, inspiration, co_parent)`.
- Rarity: given, else `roll_rarity()` (weights from the rarity table: common 50, elite 27, rare 14, epic 7, legendary
  2, mythic 0 — see 07). Birth: allowed = rarities with order < parent's and weight > 0; roll up to
  `summon.birth_rolls` times until allowed; else the highest allowed (BUG: a common parent has no allowed rarity →
  undefined; the new app must forbid birth for the lowest class or allow equal rarity).
- Target world (`son_world(parent_id, requested)`): requested if it exists and is not forgotten; else parent's
  current world; else the world maximising `(unworshipped × summon.world_unowned + living × summon.world_living −
  sons_there × summon.world_son) / 100` where unworshipped = canon people/settlement/cult/faction with no active
  `worships` bond to a son, living = canon people/settlement/mortal/species, sons_there = non-dead sons whose current
  world it is; forgotten worlds excluded; default world 1.
- Prompt `summon.son`; schema `schema.son_profile`; live `writing {who: Summoning}`.
- `insert_son(p, rarity, age, parent_id, world_id)`:
  - name `unique_name(p.name)`; stats = `roll_stats(rarity, p.strengths, [p.weakness])` (07);
  - passions: each of loyalty/ambition/anger/mercy = clamp(p.passions[k] ?? summon.passion_default, 0, 100);
  - domain2 = p.domain2, but if equal to domain1 → `DOMAINS[(index(domain1) + summon.domain_shift) mod 40]`;
  - personality JSON {appearance, temperament, obsession, fear, speech_style, secret};
  - life = max_life(stats), essence = max_essence(stats), parent, birth_age, image prompt, powers =
    `clean_powers(p.powers)`, existence JSON, existence value `summon.existence_start`, stars 1;
  - current world = world_id ?? son_world(parent_id).
- `clean_powers(list)`: usage = count of each effect over all sons' powers; fallback order = effects sorted by usage
  ascending (random tiebreak); for the first 3 powers: keep the model's effect if valid, not already used by this son
  and `usage < summon.power_effect_cap`, else the first fallback not yet used by this son; param: `cheap_creation` →
  valid entity type else `place`; `duelist` → one of strength/wisdom/cunning/charisma/will else `strength`; others
  null. Result `{name, description, effect, param}`.
- After insert: for every other son k: `shared` = number of k's domains in the new son's domains;
  `relation_change(new, k, shared ? −summon.rival_domain × shared : (k is parent ? summon.parent_relation : 0))`.
  With a parent: bond new→parent `descends_from` (description = inspiration[:200]); co-parent: second
  `descends_from` bond and `relation_change(new, co, summon.co_parent_relation)`; chronicle `birth` (son = parent):
  "{parent}[ and {co}] gave birth to a child: {name}, {title} ({rarity}; {d1}/{d2})." Without a parent: chronicle
  `birth` (son = new): "{god} summoned a new son: {name}, {title} ({rarity}; {d1}/{d2})."
- Server event `new_son {son}`.

### 4.5 Son turn (old `sonTuru`, `sonSistemi`, `ogulIstemi`, `turIzleri`, `bekleyenIsiCoz`, `eskiBekleyenleriCoz`)

The heart of the game. Runs in the epoch's "sons" phase, ordered by initiative, one son at a time (10), or on demand
for a single son.

#### 4.5.1 Preconditions (errors are user-visible)
- resolve old pending jobs first (§4.5.6);
- son exists ("No such son"); status `active` (else "{name} is {status}; cannot act."); not chained this age ("{name}
  is chained this age."); `last_action_age < world.epoch` ("{name} has already acted this age.");
- resumed turn if `turn_age == epoch and turn_ap != null`; `ap = resumed ? turn_ap : action_points(son)` (07);
  if `ap <= 0` and not resumed → "{name} is being forgotten; has no strength to act."

#### 4.5.2 Turn context `ctx`
```
ctx = { age, ap, messages_sent: 0, bonds_made: 0, prayed: false, creations: [], birth: dogur,
        ...turn_traces(son, age), ...(resumed ? read_ctx(son.turn_ctx) : {}) }
```
`turn_traces` rebuilds per-age counters from durable traces so a crash never grants a second free creation, prayer or
gift: messages to siblings this age; prayed (message to the creator with intent `prayer`); first living creation done
(entities this age created by the son, source `son`, type ∈ LIVING_TYPES = people/mortal/settlement/species/cult/
faction); life-takings (`death` chronicle rows "…was taken by the hand of…"/"…wanted to take the life…"); intrigues
(`resurrection` rows about a dead sibling); land creation (`discovery` row "…narrow lands…"); gift given (`gift` row);
anchor chosen (`existence` row "{name} … its existence"). (LANGUAGE-SPECIFIC: these are LIKE-matches on Turkish
chronicle text — the new app must store explicit per-turn counters in a `son_turn_state` table instead.)
`write_ctx/read_ctx` persist every number/bool/string/null, arrays of scalars/plain objects, and Sets (as
`{$set: [...]}`); `ap` and `age` are stored in their own columns.

#### 4.5.3 Start
- If resumed: `resolve_pending_job(son, ctx)`.
- `UPDATE son SET turn_age=epoch, turn_ap=ctx.ap, turn_ctx = resumed ? write_ctx(ctx) : NULL`.
- Build the MCP server: `build_son_server(son.id, ctx)` → `{server, tool_list, tool_costs}` (tool catalogue §5).
- Unread messages to this son are captured now and marked read only after the turn (a crashed turn sees them again).
- Event `start {son_id, son_name, model, resumed}`.

#### 4.5.4 Agent turn
`agent_turn(name="Son turn: {name}", system=son_turn.system(son, world, ctx, tool_list, tool_costs),
prompt=son_turn.user(fresh son, extra = resumed ? resume_note : ''), server, server_factory = fresh
build_son_server(son.id, ctx).server, is_complete = extract_word(text) != '', continuation_prompt = son still
active ? son_turn.user(extra = continuation(reason, done)) : None, pending_job = long_job(son.id), job_traces =
ctx.long_jobs, max_turns = rarity.max_turns (common 11, elite 13, rare 15, epic 17, legendary 19, mythic 21),
timeout = fate.son_timeout)`; events are forwarded with `son_id`, `son_name`.

#### 4.5.5 Finish (also when the turn returned partial)
- `son.last_action_age = epoch`, `son.order = null`, `order_absolute = 0`; mark captured messages read;
  `turn_ap = NULL`.
- `word = extract_word(text)`; if any → chronicle kind `word` (son): `{name}: "{word[:900]}"` linked to
  `ctx.creations`.
- Event `done {son_id, son_name, word, creations, status}`; return `{word, creations, status}`.
- If `agent_turn` threw (no trace), nothing above runs; the epoch retries the son at the end of the phase (10).

#### 4.5.6 Long-job reconciliation (old `bekleyenIsiCoz`, `eskiBekleyenleriCoz`)
`birth_world` and `birth_child` are long tool calls (they run a nested LLM call). Before running, the tool stores
`ctx.pending_job = "{tool}:{essence_paid}:{ap_paid}:{age_started}"` (persisted).
- `resolve_pending_job(son, ctx)`: none → null; if the job is still running in this process (`long_job(son)`) →
  "running"; else check success: for `birth_world` a world with `creator_id = son and created_age = age_started`; for
  `birth_child` a son with `parent_id = son and birth_age = age_started`. Clear the flag. Success → "done". Else
  refund essence to the son, add the AP back to `ctx.ap`, chronicle `system`: "{son}'s half-finished {world birth |
  child birth} could not be completed; its essence returned to it." → "refunded".
- `resolve_old_pending_jobs()`: for every son whose stored ctx has a pending job not running in this process:
  resolve it; persist the new ctx; if the turn is still resumable this age (`turn_age == epoch`, `turn_ap != null`,
  `last_action_age < epoch`) also persist the refunded AP. Returns `[{son_id, result}]`.

### 4.6 Fate and the Chronicler (old `kaderVeKronik`, `kaderBaglami`, `kaderHukmu`, `kronikiTamamla`)

Purpose: judge everything created this age (accept / fix / reject), name pending engine records, fulfil prophecies,
advance/close/open story threads, extract canon facts, add words to languages, reward sons; and, in parallel, write
the age's chronicle (name, narrative, summary, chronicler identity, per-world sections).

#### 4.6.1 Context assembly (`fate_context(age, engine_notes)`)
1. `start = min(age, world.fate_debt ?? age)` — Fate also weighs creations from earlier ages it could not judge.
2. `new_all` = canon entities with `age BETWEEN start AND age`, `(age == current OR fate_note IS NULL)` (so a half-paid
   debt never re-judges what was judged), source ∈ {son, mortal}, not pending, ordered by id.
3. `fit(ids, max, warn)`: for each id append `entity_detail(id)` (+ `\nPRE-SCREEN WARNINGS: …` if warn and any);
   stop before exceeding `max` (the first always fits); running length counts `len + 9` (separator).
   `Y = fit(new_all, fate.new_budget, warn=True)`; `B = fit(pending ids, ∞)`;
   `K = fit(canon prophecies with age < current, newest first, fate.prophecy_budget)`.
4. `overflow = new_all − Y.ids`; `remaining_debt = min(age of overflow)`.
5. Threads = open, non-"great" threads with stagnation; candidates/min_close/new_max (09 §6.4).
6. Prompts: `fate.judgment.user` and `chronicler.user` (with `pending_text` = entity_line of each pending record).
7. Schemas: judgment schema = full schema without chronicle keys; chronicle schema = age_name, narrative, summary,
   chronicler, [worlds].

#### 4.6.2 Execution
1. Emit `fate_step "Fate is weighing {n} creations, naming {m} unnamed records; the chronicler is writing…"`.
2. Run judgment (`fate.judgment.*`, name "Fate", timeout `fate.timeout`) and chronicle (`chronicler.*`, name
   "Chronicler") **in parallel**, independently (allSettled). Each emits `fate_step "Fate gave its verdict ({s} s)."` /
   `"The chronicler wrote the age: "{name}" ({s} s)."`.
3. Chronicle completion (§6.10–6.11 prompts): fix a forbidden opening; write missing world sections. Failures leave
   the chronicle as is (`error "Chronicle completion: …"`).
4. Overflow judgment: only if the main judgment succeeded. Split `overflow` into batches by `fate.new_budget`
   (entity_detail + warnings); run `fate.extra_judgment` in groups of `fate.parallel_verdicts`
   (emit `fate_step "Fate is weighing the remaining {n} creations of this age in {g} rounds together[ (then {k}
   more)]…"`). Successful batches add verdicts and their ids to `judged`; on any failure the failed and not-yet-run
   batches' ids become debt `extra_debt = min(age of those)` and emit `error "Fate could not weigh the remaining {n}
   creations ({err}); it will be the first task of the next age."`; stop further groups.
5. `debt = judgment failed ? start : extra_debt`. Messages: judgment failed → `error "Fate could not give a verdict this
   age ({err[:120]}). The creations remain in the canon; Fate will weigh them in the next age, and the unnamed records
   will be named then."`; overflow fully judged → `system "Fate weighed all {n} creations of this age."`; chronicle
   failed → `error "The chronicler could not write this age ({err[:120]}). The missing chronicle will be written at the
   next completion."`
6. `apply_fate_verdict(...)` (§4.6.3) with `out = {...judgment, ...chronicle, verdicts: all verdicts}`, `new =
   judged`, `chronicle_present`, `debt`. Returns `{..., events: age_events}` for the voices phase.

#### 4.6.3 Applying the verdict (old `kaderHukmu`) — one transaction, then ledger undo
Deduplicate every list by id (first wins). In order:
1. **Verdicts** (only ids Fate saw in `new`, entity still canon):
   - `reject` and `world.fate_mode != 'off'`: rationale = `shorten_rationale` (§4.17); status `rejected`,
     fate_note = rationale or "Fate rejected."; deactivate every active bond touching it with `closed_by_rejection = 1`
     (rejected languages are no longer spoken, rejected items have no owner); move its contents to its location
     (`transfer_contents`); chronicle `fate` (creator son): "Fate rejected {name}: {rationale}" / "Fate rejected {name}."
     (In fate mode `off` a reject falls through to the accept branch.)
   - `fix` with blank fixed_description → *limbo*: not judged, becomes debt.
   - `fix`: description = `strip_meta_sentences(sanitize(fixed))`, fate_note "Fate fixed: {r}" / "Fate fixed.";
     chronicle "Fate accepted {name} with a fix: {r}".
   - `accept` (or any verdict carrying a rationale): fate_note = shortened rationale or "Fate accepted."
2. **Namings** (only ids in `pending`): `apply_naming(item)` (§4.9.2); if the name changed, replace the old name in
   narrative, summary and every world section via `replace_name_in_text(text, old, new, protected)` where protected
   = names of other entities containing the old name.
3. **Fulfilled prophecies** (only ids in `prophecies`, still canon): status `fulfilled`, fate_note =
   `clean_fate_note(how)` or "The prophecy came true.", add tag `reading:{true|misread|self_fulfilling}`; bonds
   `prophesies` ("came true") to every entity mentioned by name in `how` (`entities_in_text`, agonar.js, same world);
   chronicle `fate` (creator): "{reading text}: {name}. {how}" — reading texts: "The prophecy came true as it was
   spoken" / "The prophecy came true, but not as everyone expected" / "The prophecy came true because people believed
   it". Seer = the mortal who uttered it (`maker_id`), if canon mortal: charisma = clamp((charisma or
   fate.seer_charisma) + (misread ? −fate.seer_misread : +fate.seer_true)). Creator son: fame += fate.prophecy_fame ×
   k, xp += fate.prophecy_xp × k, k = fate.seer_factor if the son has an unlocked `seer` power else 1.
4. **Threads**: `closed = [resolved_thread] + closed_threads`. Advanced (first `fate.advance_max`): thread in the list,
   record exists, `record.age == age`, not rejected/destroyed, `how` non-empty → tag record `thread:{id}`,
   `progress += 1` if open; chronicle `fate` "A story advanced: {how}" (skipped if the same thread is also closed).
   Closed: thread in the list → status `closed`, closing text, closing_age; chronicle "A story closed: {how}" linked
   to its existing related ids.
5. **Facts** (first `fate.facts_max`): subject exists and not rejected/destroyed; relation non-empty; object_id valid
   (same rule) else object text required; insert `facts(subject, relation[:120], object_id, object[:200], age,
   source_id = subject if judged or named this call)`.
6. **Definite facts**: `definite_facts(new + pending, age)` (gercek.js) — location, creator, language, patron and
   descent facts written by the engine regardless of the model.
7. **New threads** (first `new_max`, non-empty text): insert thread (age, sanitized text, related ids that exist).
8. **Words** (first `fate.words_max`): language must be a canon `language`; word and meaning non-empty →
   `lexicon_add(language, [{word, meaning, origin or "Born in Age {age}", kind: noun}], adder 'fate', null, age)`.
9. **Rewards**: per son: `streak` = count of distinct ages in `[age − window, age − 1]` with a Fate reward row for
   the son; `raw = clamp(fame, 1, max(1, fate.reward_max)) × (fate.reward_streak_decay/100)^streak`; `fame = min(round(raw),
   fate.reward_max − already_given_this_age)`; skip ≤ 0; son.fame += fame; son.xp += fame × fate.reward_xp_factor;
   chronicle `fate` (son) "Fate gave {son} {fame} fame: {clean_fate_note(reason)}" / "… fame." (Old code detected the
   streak with a LIKE on the Turkish text — use a structured `fate_rewards` table.)
10. **Age record** (only if the chronicle exists and has a narrative): unique name — if its normalized form equals
    another age's: try "Second {name}", "Third …", "Fourth …", "Fifth …", else "{name} (Age {n})"; upsert `ages(age,
    name, narrative, summary, year_start = (age−1)·AGE_YEARS, year_end = age·AGE_YEARS, closed_at = now, chronicler
    JSON {name[:80], who[:240]})`; upsert per-world sections `ages_world(age, world_id, narrative, summary)` for
    existing worlds. All texts pass `sanitize` (and the dropped Turkish suffix fixer).
11. **Debt**: if limbo entities exist, `debt = min(debt ?? age, their ages)`; `world.fate_debt = debt` (null = none).
After the transaction, **undo rejected side effects**: for each rejected entity, find the latest not-undone ledger
group that inserted it; `ledger_undo(group)`; delete chronicle rows created after the undo that say "a page was torn
from the ledger" (the rejection is Fate's, not the creator's hand); restore status `rejected` and the fate note.
Undo conflicts are swallowed (the bonds stay closed). Return `{…out, rejected, fixed, limbo, fate_debt}`.

### 4.7 Voices of the peoples (old `halklarinSesi`)
- Runs as its own epoch phase after Fate (a crash between them never loses the verdict).
- Selection: peoples = canon peoples by population desc. Historians: `fate.historians` peoples sorted by the last age
  they wrote a view (never → −1) ascending, then population desc. Belief pairs: for every people, its patron god and
  every son with an active `cursed|blessed|enemy|protects` bond from the son to the people, if no belief row exists;
  plus the creator (son_id 0, pseudo-son {name: god_name, title: god_title or "creator", domains Creation/Everything})
  for the first `fate.creator_belief_peoples` peoples lacking one; patron pairs first; take `fate.belief_pairs`. Stop
  if neither historians nor pairs.
- Known god names: `people_god_name(people, son)` = name generated from the people's language (old `adUret(lang,
  "tanri:{son}:{people}", "kisi")`, language = spoken language, else the language of a settlement it rules, else the
  most-spoken canon language of its world). LANGUAGE-SPECIFIC name generator → see language spec.
- Prompt `voices.peoples`; timeout `fate.voice_timeout`; emits `fate_step "The peoples' historians and bards are
  writing their own accounts ({h} chronicles, {b} beliefs)…"` and afterwards `"The voices of the peoples were written:
  {v} partisan chronicles, {b} folk beliefs."`.
- Writes: views only for selected historians with text: delete existing (age, people) then insert
  `chronicle_views(age, people, historian, text)`. Beliefs: matching pair with story: name = generated name ||
  `valid_belief_name(model name)` (≤ `folk_belief.name_letters`, not equal to/containing the god's name or title or
  vice versa, passes the dialect check) || fallback epithet "Lord of {domain1}" (old "{alan} Sahibi"); upsert
  `folk_beliefs(people, son)` with story, wrong, age.

### 4.8 Lost chronicles backfill (old `kayipKronikler`)
Ages `< current` having chronicle rows but no `ages` row or no narrative, oldest first, at most `fate.lost_chronicles`:
`chronicler.lost_age` with that age's world list (worlds created by then, not forgotten); upsert the age (keeps the
existing chronicler if the new is null) and sections; publish `fate_step` start/finish or `error "The chronicle of
Age {n} still could not be written: …"`. Then past ages with a narrative but missing world sections (only when ≥ 2
worlds existed by then), newest first, at most `fate.lost_world_sections`: `chronicler.lost_world_sections`.

### 4.9 Naming pending engine records (old `bekleyenleriAdlandir`, `adlandirmaUygula`)

#### 4.9.1 Loop
```
attempts = {} ; max_tries = 1 + naming.attempts ; warnings = {}
loop:
   queue = pending records (awaiting_name=1) ordered by (world_id or 1, id) with attempts[id] < max_tries
   if empty: break
   batches = []; for r in queue: d = entity_detail(r) (missing → attempts[r]=max, skip)
       start a new batch when world changes or batch full (naming.batch); stop creating batches at naming.parallel
   if no batch has items: break
   attempts[id] += 1 for every id in a batch
   publish system "{n} records born of the world's own course are being named in {b} batches ({left} remaining)."
   results = allSettled(run_batch(b) for b in batches)
   if all rejected: raise first error
after loop: every id with attempts >= max_tries still pending → strip the "[World engine] " prefix from its
   description, awaiting_name = 0 ("cleaned"; left for deepening)
publish system "{named} records were named[; {cleaned} records' temporary descriptions were cleaned, left for deepening]."
```
`run_batch`: prompt `naming.pending` for that world (dialect warnings of earlier attempts appended), live
`writing {who: Fate, topic: "{n} unnamed records[ ({world})]"}`. For each returned item whose id is in the batch:
if `naming.dialect_check` and the record is not tagged `name-from-language` and attempts < max and the name violates
the dialect → store a warning `#{id} "{name}" ({root}: {letters} do not exist in this dialect)` and skip (retried);
else `apply_naming`.

#### 4.9.2 `apply_naming(item, age)`
Only if the record is still pending. Name: tagged `name-from-language` → keep the current name; else if the model's
name differs and is taken → `unique_name(name)`; else model name (or current). Description: model description
(prefix "[World engine]" removed; suffix fixer dropped) or the current description without the prefix. Subtype: for
engine-sourced records with a subtype keep it (it is a mechanical key: war, currency, battle, rebels… matched exactly
by the engine — overwriting it broke war closing and re-minted coins); else `fix_subtype(model subtype or current,
type)` (tools.js `altTurDuzelt`). Update subtype, `sanitize(description)`, image prompt (model's or existing),
`awaiting_name = 0`; if the name changed: `rename_entity(id, name, {age_start = min(age, record.age)})` (world.js
`adDegistir`: replaces the old name across all stored texts — LANGUAGE-SPECIFIC suffix handling dropped).

### 4.10 Revelation (old `vahiy`, `vahiyBaglari`, `vahiyEtiketleri`)
- Trigger: player revelation (paid `COSTS.revelation` 25 essence, refunded on failure) with text, optional type,
  optional target world, optional natural-law mechanic; startup first-star.
- Prompt `revelation`; schema `schema.revelation`; live `writing {who: Revelation}`.
- Type = model type if valid else the first allowed type. Location: model's `location_id` if it is an allowed
  location type for that entity type, canon or dead, and in the target world; else null; if the type requires a
  location → the first canon region of the target world (or world 1). Stats = `fill_stats(type_def, stats, power)`
  (tools.js).
- Insert (transaction): `unique_name`, type, subtype, description, stats, power clamp(1, content.revelation_power_max),
  domain, age, location, image prompt, tags, source `god`, world_id = location ? null (inherited) : target world.
  Bond `inside` to the location. Links: target son must exist / target entity must exist, not itself, not
  rejected/destroyed, and (multi-world) in the same world; skip an `inside` link duplicating the location; add bonds.
  Tags: model tags or `['revelation']`, minus any `law:*`, plus `law:{mechanic}` for natural laws (player's choice if
  valid, else the model's). Chronicle `god`: "{god} revealed, and {name} appeared in the world ({type label})."

### 4.11 Deepen entity (old `derinlestir`, `derinlikIsle`, `derinlikDuzenle`, `gomuluBolumler`)
- Triggers: manual per entity (parallel job `v{id}:deepen`), bulk deepening (toplu.js), auto-deepen after an age (10).
- Prompt `deepen.entity`; live `writing {who: Lore writer, topic: name}`.
- Post-processing `apply_depth(id, out, old_name)`:
  1. Walk every string: if the entity was renamed while the model was writing (`old_name != current`), replace the old
     name (protecting longer names containing it); `sanitize`; strip meta sentences ("Fate later rewrote this…").
  2. `normalize_depth(d, type)`: keep only keys `history, rumours, sayings, details, hidden_truth, special` (special
     only for types with a table) + `age`, `names`. If `history` contains an embedded section heading (regex for
     Rumours/Sayings/Details/Hidden truth/Special as a heading line or "Heading:" prefix), parse the embedded part into
     lists (`rumours`, `details` as lists; `sayings` as `{kind: proverb, text}`; `hidden_truth` joined) and use them for
     keys the model left empty; cut `history` at the heading. Drop placeholder values (`x`, `placeholder`, `tbd`,
     `todo`, `-`, `…`, empty) from strings and arrays.
  3. Store `depth = {...clean, age}`.
- LANGUAGE-SPECIFIC: heading regexes include Turkish words (söylentiler, sözler, ayrıntılar, gizli gerçek, özel) →
  English equivalents.

### 4.12 Creator epic and creator deepening (old `tanriDestani`, `tanriDerinlestir`)
Prompts `creator.epic` / `creator.deepen`. Writes `world.god_epic = JSON {…out, age}` / `world.god_depth = JSON
{…out, age}`. The world header then shows the epic's title/line and the depth's prohibitions and desire.

### 4.13 Foreign god deepening (old `yabanciDerinlestir`, `yabanciDerinlikIsle`)
- Context: chronicle rows mentioning the god's name as a whole word (newest first, up to `foreign.deepen_chronicle`),
  worshippers (active `worships` bonds to the foreign god), known fields (09 §9.4).
- Post-processing: unwrap embedded-JSON strings (`metinAc`: the model sometimes writes paragraphs as `["…","…"]`);
  personality = model personality cleaned (`metinTemizle` with the personality keys, each sanitized) **overridden by
  the god's existing non-empty fields** (fields the player wrote are canon); existence likewise (existing wins);
  powers = existing powers if any, else `clean_foreign_powers(model powers)` with sanitized descriptions; depth =
  every depth-text key (sanitized), names (with a name), secrets, rumours, sayings ({kind or "saying", text}), age.
  If `history` is empty → throw "The deepening output has an empty history; it will be retried." Update personality,
  existence, powers, depth, image prompt (only if empty). Event `foreign_god_deepened {id, name}`.

### 4.14 Son epic (old `destanYaz`)
Prompt `son.epic`; writes `son.epic = JSON {title, epic, line, age}`. Parallel job `o{id}:epic`.

### 4.15 Awaken peoples (old `halklariUyandir`)
- Regions: canon regions of the given world (or all); none → error "There is no region for the peoples to awaken in."
- `requested = max(1, round(n))`, batch = `awaken.batch_max`; loop while created < requested and attempts ≤
  ceil(requested / batch): call `awaken.peoples` with `n = min(batch, remaining)` (and the names of already awakened
  peoples); on error: if nothing created yet → raise; else stop (earlier batches stay).
- Per returned people (≤ n), in a transaction: region = valid region id else the first region; insert six entities
  (source `world`, world = region's world, age = current, `unique_name`, description, image prompt fixed by
  `fix_image_prompt`): people (pop clamp(model or default, min, max), martiality/magic/craft clamp(model ?? default),
  piety default; location region; power `awaken.power`), language (spread/complexity/sanctity; power), settlement
  (pop clamp; prosperity/defence/piety; location region; power), resource (abundance/value/might; location region;
  domain; power), knowledge (level/spread; power; tag `branch:{branch}`), tradition (spread/rigidity; power). Lexicon:
  the model's words added to the language (adder = the people). Bonds: people speaks language, settlement speaks
  language, people rules settlement, settlement owns resource, people knows knowledge, settlement knows knowledge,
  people celebrates tradition, `inside` bonds for located ones; if `worshipped_son_id` is a son: people and settlement
  worship him. Chronicle `birth` (son = worshipped or null): "A new people awoke in the lands of {region}: {people}.
  It speaks {language}, founded {settlement}, owns {resource} and knows the knowledge of {knowledge}." linked to all six.

### 4.16 Image prompt writers and local image generation
- `image_prompts.entities(limit, ids?)`: entities lacking a prompt (non-pending first, by id) up to `limit`, or the
  given ids (single-entity "write prompt" used by the image queue). Accepted prompts stored via `fix_image_prompt`.
- `image_prompts.cosmos()`: worlds, stars, foreign gods lacking prompts, ≤ `content.cosmos_batch`; stored truncated.
- Epoch also runs "missing prompts" rounds after an age (`agent.prompt_rounds` in 10).
- **Local image generation** (old `gorsel-uret.js`, not an LLM): a persistent Python worker (mflux, model
  `mflux-community/z-image-turbo-mflux-q4`, overridable by env) loaded once and kept warm; strictly sequential queue
  (one GPU); manual requests jump ahead of bulk/auto ones; a target is `(kind ∈ god t | son o | foreign god y | world d |
  entity v, id)`; duplicates rejected ("already being generated or queued"); non-entity targets need an image prompt,
  entity targets get one written on demand. Worker protocol: JSON lines `{id, prompt, width, height, steps, seed,
  output}` → events `ready{load_s}`, `stage(text|decode)`, `step{step,total}`, `done{file}`, `error{error, fatal}`.
  New images are only ever **added** (never replace); the first image becomes the cover only if the target has none.
  Events: `image_queued`, `image_progress {stage, step, total, percent}`, `image_done {status, image|error, ms}`,
  `image_status`, `image_bulk {summary, line}`. Bulk generation covers every target without an image (god, sons,
  foreign gods, worlds, then entities by pending, importance, power, id), with `GU.retry` retries; auto-starts on
  `age_done` if `image_gen.auto`. Tunables (group "Image generation"): width 720 (256–2048), height 720 (256–2048),
  steps 4 (1–50), auto 1 (0–1), idle_release_s 600 (0–86400), load_timeout_s 300 (10–3600), timeout_s 300 (10–3600;
  on timeout the worker is restarted), retry 1 (0–5), log_lines 200 (20–5000), error_lines 20 (1–500).

### 4.17 Text post-processing shared by all writing roles
- `sanitize(text)` (old `anlatiTemizle` + `kimlikTemizle`): removes leaked ids and game marks: `[thread#12]` tags,
  `(#795)`, `(thread#42)`, `(#2741 inside)`; "thread#67 story's" → "a story's"; "son#3 Name" → "Name"; numbered
  mentions → "a story"/"a son"; HTML comments; "Note: This record…" lines; "classified as P7", "(P7)"; dice scores;
  stray `#\d+`; star glyphs; duplicate spaces. LANGUAGE-SPECIFIC suffix handling (`NUMARA_EK`, `HIKAYE_EK`) → English
  replacements ("thread#4's" → "a story's").
- `clean_fate_note(text)` (old `kaderNotuTemizle`): sanitize, then drop sentences/clauses that mention internal
  reasoning (PRE-SCREEN, UNBOUND, TIRED…, motif ban, cliché ban/name, "accepted with rationale", warning(s), criterion
  a–e), drop a leading "However/But/Yet/Still", capitalise; null if no letters remain.
- `shorten_rationale(text)` (old `gerekceKisalt`): `clean_fate_note`; if ≤ `fate.rationale_words` words keep; else
  the first sentence if short enough; else the first N words + "…" (trailing , ; : removed).
- `strip_meta_sentences(text)` (old `metaCumleSil`): drops sentences saying Fate rewrote/fixed/changed the record or
  mentioning "the first telling".
- `unique_name(name)`, `similar_name(name)`, `rename_entity` — owned by the world/lore spec.
- `ekDuzelt` (Turkish suffix harmony after names) — LANGUAGE-SPECIFIC: drop.

## 5. Tool catalogue — sons (`src/tools.js`)

Source of truth: `src/tools.js` (1436 lines), plus the rule tables it reads from `src/rules.js` (RARITIES, VARLIK_TURLERI, COSTS, KURAL, NADIRLIK_KAPI, YARATIM_TABANI, KOZMIK_BEDEL, MUDAHALE_BEDEL, DENGE, MUCIZELER, AFETLER, BILGI_DALLARI, YASA_MEKANIKLERI, OZELLIKLER, BAG_TURLERI, ANLATI_BAGLARI, ALANLAR) and effect helpers in `olum.js`, `panteon.js`, `oyuncu.js`, `otesi.js`, `mudahale.js`, `tanriguc.js`, `kozmos.js`, `seyahat.js`, `ufuk.js`, `bosdunya.js`, `yabanci.js`.

Every son (ogul) turn gets its own in-process MCP server named `dunya` ("world") containing only the tools its rarity and the current world state allow. Tools write directly to SQLite. Every validation failure is returned to the model as a tool error (never thrown) so the model can correct itself.

Glossary used below (Turkish original once):
- son (ogul) – a god card controlled by an LLM agent. Fields used here: `id, ad` (name), `unvan` (title), `nadirlik` (rarity), `alan1/alan2` (domains), `statlar` (stats: guc strength, dayaniklilik endurance, ceviklik agility, bilgelik wisdom, kurnazlik cunning, irade will, yaraticilik creativity, karizma charisma, kudret potency), `tutku` (passions: sadakat loyalty, hirs ambition, ofke wrath, merhamet mercy), `can` (HP), `oz` (essence, the creation currency), `inanc` (faith), `un` (fame), `xp`, `seviye` (level), `yildiz` (star 1–5), `gucler` (3 powers), `durum` (state: aktif active / uykuda asleep / olu dead / …), `uyku_kalan` (sleep epochs left), `asi` (rebel flag), `capa_id` (anchor entity), `plan`, `aktif_dunya` (world the son currently stands on), `tur_cag / tur_ap / tur_ctx` (persisted turn state).
- entity (varlik) – a world record with `tur` (type), `alt_tur` (subtype), `durum` (state: kanon canonical / olu dead / yok_edildi destroyed / reddedildi rejected by Fate / gerceklesti fulfilled (prophecy) / …), `statlar` (JSON), `guc_seviyesi` (power level 1–12), `alan` (domain), `yaratan_id` (creator son), `konum_id` (location entity), `dunya_id` (world), `etiketler` (tags JSON array), `kaynak` (origin: 'ogul' son / 'tanri' creator god / 'dunya' engine …), `unvan` (title).
- bond (bag) – row in `baglar`: `kaynak_tip/kaynak_id → hedef_tip/hedef_id`, `tur` (bond type), `aciklama`, `cag`, `aktif`. Endpoint types: `'v'` entity, `'o'` son, `'t'` creator god, `'y'` foreign god.
- relation (iliski) – son↔son affinity −100..100 (`iliskiDegistir(a, b, delta)`).
- chronicle (kronik) – `addKronik(cag, ogul_id, tur, metin, ids[])`.
- epoch (cag) – the game turn.
- `d(n)` = uniform integer 1..n. `clamp(v, lo, hi)` ROUNDS to integer.

---

### 1. Server construction: `buildSonServer(sonId, ctx)`

Called by `agents.js sonTuru` once per turn and again (fresh server, same `ctx`) for every continuation session (`sunucuYap`). Returns:

```
{ server: createSdkMcpServer({ name: 'dunya', version: '2.0.0', tools }),
  aracListesi: [tool names],                       // shown in the son's system prompt
  aracBedelleri: { harcamaz: [free tool names], harcar: [action-spending tool names] } }
```

`aracBedelleri` (free vs paid) is derived by regex from the Turkish tool description: free if it matches `/Ücretsiz|[Ee]ylem harcamaz|eylem hakkı HARCAMAZ/` ("Free" / "does not spend an action") and does NOT contain `/\b\d eylem\b/` ("N action(s)"). `BEDAVA_RE` and `bedavaMi` are exported (also used by `olumluler.js`). NEW DESIGN: put an explicit `free: bool` / `ap_cost` in each tool's metadata instead.

Build-time snapshot (`me0 = getSon(sonId)` at build):
- `tavan = gucTavani(me0)` – power-level ceiling for creations (see §3).
- `gy = dunyaninYildizi(me0.aktif_dunya ?? 1) || cagYildizi()` – "the epoch's star" of the son's world; creations whose `alan` equals the star's `alan` get a discount.
- Tool availability is decided once from `me0.nadirlik` and DB state (number of worlds, existence of dead siblings, dead stars, free spirits, contacted awake foreign gods, outer beings). Rarity changes during the turn take effect only on the next server build.

Tool registration wrapper `tool(name, description, shape, handler)`:
1. `aracAlanlari(shape)` – every numeric / array / object field is wrapped with `z.preprocess(alanTemizle)` (see §4).
2. `atomikSar(handler)` – synchronous handlers run inside one SQLite transaction (`atomik`: joins an existing transaction if one is open, else `tx(fn)`). Async handlers (`evlat_dogur`, `dunya_dogur`) are NOT wrapped.
3. Registered with the Agent SDK `tool()` (zod schema).

After all tools are pushed: `araclariSar(tools, ctx, kaydet, defter, kapi)` (from `llm.js`, documented in the LLM section) with:
- `kaydet(c)` = `UPDATE ogullar SET tur_cag=c.cag, tur_ap=c.ap, tur_ctx=turCtxYaz(c) WHERE id=sonId` – runs after every successful tool call so a crashed process resumes with the right action points and counters.
- `defter = { kim_tip: 'o', kim_id: sonId, kim_ad: name }` – every non-read tool call is recorded as one ledger entry (`defter.js`, "Fate's ledger", used for selective undo). Read tools (`OKUMA_ARACLARI = dunya_ozeti, dunyaya_bak, varlik_incele, varlik_ara, hafizam, kardesi_incele`) are not recorded.
- `kapi = davranabilirMi(name)` – gate asked before every call: read tools always pass; otherwise if the son's `durum !== 'aktif'` (fell asleep/died mid-turn) → `ctx.ap = 0` and reject with: "REJECTED: {name} is now {state}{ (lasts N epochs) if asleep}; you can no longer act this epoch. Do not call another tool; speak your word inside «…» and finish."
- Calls are serialized (one at a time even if the model emits several tool_use blocks in one message). On an exception the in-memory `ctx` is restored to its pre-call snapshot (counters, arrays, sets) and the model gets "REJECTED: An error occurred while the tool was running ({message ≤200}). Your action point was returned; fix your input and retry, or choose another action."

Result helpers:
- `ok(text)` → `{content:[{type:'text', text: ekDuzelt(text)}]}`
- `err(text)` → `{content:[{type:'text', text: 'REDDEDİLDİ: ' + ekDuzelt(text)}], isError: true}`. English: prefix `"REJECTED: "`. `ekDuzelt` is a Turkish suffix-harmony fixer — LANGUAGE-SPECIFIC: drop.
- `durumSatiri(s)` appended to most successes: `"Remaining actions: {ctx.ap} · Essence: {s.oz}/{ozMax(s.statlar)}"`.
- `uyudun()` appended after tools that can put the son to sleep: if the son is no longer `aktif` → `ctx.ap = 0` and appends " You {fell asleep | are <state>}; you can no longer act this epoch. Speak your word inside «…» and finish."

### 2. Turn context (`ctx`)

Created in `agents.js sonTuru`:
```
ctx = { cag, ap, mesajSayisi: 0, bagSayisi: 0, duaEdildi: false, yaratimlar: [], dogur,
        ...turIzleri(son, cag),               // counters rebuilt from DB traces (crash-safe)
        ...(resumed ? turCtxOku(son.tur_ctx) : {}) }
```
| field | meaning |
|---|---|
| `cag` | current epoch |
| `ap` | remaining action points (eylem hakkı) |
| `mesajSayisi` | sibling messages sent this epoch (`kardese_seslen`) |
| `bagSayisi` | narrative bonds woven this epoch (`bag_kur`) |
| `duaEdildi` | prayers this epoch (boolean in init, numeric in tool) |
| `yaratimlar` | ids of entities created this turn (creation tools, afet event record, yatak); attached to the son's closing chronicle line |
| `dogur(parent, inspiration, coParent)` | callback = `agents.js dogur` (child-son summoning LLM call) |
| `sagilan: Set` | resource ids harvested this epoch (initialized `??= new Set()` in buildSonServer) |
| `capaSecildi, kelimeSayisi, armagan, kutsalDunya, sizintiDikildi, canAl, entrika, disPazarlik` | per-epoch counters for limited tools |
| `canliYaratim` | the epoch's free living creation was used |
| `toprakYaratim` | the epoch's free land creation (crowded world) was used |
| `lvl` | last level-up note text (appended to creation result) |
| `bekleyenIs` | pending long job flag `"<tool>:<essence>:<ap>:<epoch>"` (evlat_dogur / dunya_dogur) persisted for crash refund |
| `uzunIsler` | `[{arac, anahtar, ozet}]` traces of finished long jobs (fed to `agentTurn isIzleri` so a continuation prompt lists them even if the session dropped before the result reached the model) |

Persistence: `turCtxYaz(ctx)` (world.js) serializes every field except `ap`, `cag` and functions: Sets → `{"$set":[...numbers/strings]}`, arrays → only primitive/plain-object items, primitives/null as-is. `turCtxOku` reverses it. `tur_ap` stores `ap` separately.

`turIzleri(son, cag)` (agents.js) rebuilds counters from the world so a resumed turn cannot get a second free living creation / prayer / gift: mesajSayisi (count of `mesajlar` son→son this epoch), duaEdildi (any `mesajlar` niyet='dua' to 't'), canliYaratim (any entity created this epoch by this son with `kaynak='ogul'` and type in CANLI_TURLER), canAl / entrika / toprakYaratim / armagan / capaSecildi via LIKE matches on Turkish chronicle text. NEW DESIGN: persist per-epoch counters in a dedicated table instead of parsing chronicle text.

Pending long jobs (`bekleyenIs`): before charging an async tool, `bekleyenYaz("evlat_dogur:{cost}:{ap}:{epoch}")` writes the flag + `tur_cag, tur_ap, tur_ctx`. On success/failure it is cleared. If the process crashes mid-job, `agents.js bekleyenIsiCoz` / `eskiBekleyenleriCoz` later checks whether the world/child actually exists for that epoch (`dunyalar.yaratan_id=son AND olusturma_cag=epoch` / `ogullar.ebeveyn_id=son AND dogum_cag=epoch`); if not, refunds essence and AP and writes a system chronicle line.

`SUREN: Map<sonId, Promise>` – process-local registry of running long jobs. `surenIs(sonId)` returns the promise or null (exported; agentTurn waits for it before opening a continuation session or ending the turn, preventing a second birth). `surdur(sonId, fn)` registers and auto-removes on settle.

### 3. Action-point and essence economy

Action points per epoch – `eylemHakki(son)` (rules.js):
```
ap = RARITIES[rarity].ap
   + (power 'ek_eylem' unlocked ? KURAL.ek_eylem_guc : 0)
   + (son.yildiz >= 5 ? KURAL.ek_eylem_yildiz : 0)
if son.varlik (existence) < KURAL.varlik_saglam: ap -= KURAL.solgun_eylem_kaybi
return max(son.varlik < KURAL.varlik_solgun ? 0 : KURAL.en_az_eylem, ap)
```
Unused AP is lost at end of turn. A resumed turn uses the persisted `tur_ap`.

Rarity table (RARITIES, constants, not tunables):
| key (TR) | English | order | base AP | stat range | power ceiling `guc_tavan` | essence regen/epoch | maxTurns (SDK steps) | summon weight |
|---|---|---|---|---|---|---|---|---|
| yaygin | Common | 0 | 3 | 20–45 | 2 | 8 | 11 | 50 |
| seckin | Distinguished | 1 | 3 | 30–55 | 3 | 10 | 13 | 27 |
| nadir | Rare | 2 | 3 | 40–65 | 5 | 12 | 15 | 14 |
| destansi | Epic | 3 | 3 | 50–80 | 7 | 15 | 17 | 7 |
| efsanevi | Legendary | 4 | 4 | 65–95 | 10 | 18 | 19 | 2 |
| mitik | Mythic | 5 | 5 | 80–100 | 12 | 24 | 21 | 0 (only via ascension) |

Power ceiling for creations: `gucTavani(son) = RARITIES[r].guc_tavan + floor((yildiz-1) / KURAL.yildiz_guc_adim)`. Schema allows `guc_seviyesi` 1–10; handler rejects above the ceiling.

Essence ceiling: `ozMax(stats) = round(KURAL.oz_taban + KURAL.oz_kudret/100 × (stats.kudret ?? KURAL.oz_kudret_varsayilan))`. HP max: `canMax = round(KURAL.can_taban + KURAL.can_dayaniklilik/100 × dayaniklilik)`.

Creation cost – `yaratimBedeli(base, powerLevel, domainMatch, creativity, cheapPower)`:
```
domainMul  = (domainMatch ? KURAL.bedel_alan_uyumlu : KURAL.bedel_alan_disi) / 100     // 0.6 / 1.3
creatMul   = 1 − (creativity/100) × (KURAL.bedel_yaraticilik/100)                       // up to −40%
cheapMul   = cheapPower ? KURAL.bedel_ucuz_guc/100 : 1                                   // 0.6
cost       = max(1, round((base + KURAL.bedel_guc_seviye × powerLevel) × domainMul × creatMul × cheapMul))
```
In the creation tool the final cost is further multiplied:
```
starMul    = (epoch star exists AND star.alan == creation.alan) ? OGUL_ARAC.yildiz_indirim/100 : 1
repeats    = count of this son's entities of same type with same lower(alt_tur), cag >= ctx.cag − tekrar_pencere, durum != 'reddedildi'
repeatMul  = min(tekrar_tavan/100, 1 + tekrar_artis/100 × repeats)
finalCost  = max(1, round(yaratimBedeli(...) × starMul × repeatMul))
```
`cheapPower` = son has unlocked power `ucuz` with `param == type`, OR type is `kehanet` (prophecy) and son has power `kahin`.

Powers relevant to tools (GUC_ETKILERI; a power is "unlocked" when `son.seviye >= [1,3,5][index]`; `gucVar(son, effect, param?)`):
| key (TR) | English key | label | effect in tools |
|---|---|---|---|
| ucuz | cheap_creation | Master maker | creations of its `param` type use `bedel_ucuz_guc` (60%) |
| meydan | duelist | Duelist | +`meydan_guc_bonus` in challenges on its `param` stat |
| dokunulmaz | untouchable | Untouchable | −`meydan_dokunulmaz` to challengers; +`lanet_dokunulmaz` curse resistance for its worshippers |
| fisilti | dream_whisper | Dream whisper | +`ruya_fisilti` dream success |
| hasat | harvester | Harvester | resource harvest gain × `sag_hasat_kat` |
| kahin | seer | Seer | prophecy creations cheap (and doubled fulfilled-prophecy reward in Fate) |
| lanetci | curser | Curser | curse cost × `lanetci_bedel`%, severity × `lanetci_siddet`% |
| dirilis | reborn | Reborn | sleep after HP 0 lasts `dirilis_uyku` epochs |
| ek_eylem | tireless | Tireless | +1 AP (eylemHakki) |
(oz_pinari essence_spring, inanc_carpani worshipped, savas_babasi war_father, bereket fertility_giver act in the engine, not in tools.)

Base essence costs `COSTS` (rules.js, constants): donustur 15, evlat_dogur 60, yok_et 25, etkile 6, lanet 12, ruya 10, kiskirt 10, secilmis 14, ahit 0, capa 0 (+ creator-only: cagirma 30, kutsa_oz 15, kutsa_can 15, kutsa_stat 40, yildirim 10, vahiy 25).
`DENGE.dunya_dogur` = 70 (birth world). Creator cosmic costs `KOZMIK_BEDEL` = { yildiz 80, muhur 30, temizle 80, unut 20, gok 50, tutustur 60, ruh 15, sefer 30 }; creator intervention costs `MUDAHALE_BEDEL` = { mucize 15, afet 20, bilgi 12, lanet 15 }.

Son cosmic/intervention costs are derived (`OGUL_KOZMIK`, `oran(base, pct) = max(1, round(base × pct/100))`):
| function | formula | default |
|---|---|---|
| muhur (seal gate) | KOZMIK_BEDEL.muhur × kozmik_muhur% | 30×70% = 21 |
| tutustur (rekindle star) | KOZMIK_BEDEL.tutustur × kozmik_tutustur% | 60×85% = 51 |
| ruh (bind spirit) | KOZMIK_BEDEL.ruh × kozmik_ruh% | 15×80% = 12 |
| yildiz_as (hang star) | KOZMIK_BEDEL.yildiz × kozmik_yildiz% | 80×75% = 60 |
| yildiz_sondur (extinguish) | KOZMIK_BEDEL.yildiz × kozmik_sondur% | 80×100% = 80 |
| mucize (miracle) | MUDAHALE_BEDEL.mucize × mudahale_oran% | 15×70% = 11 (≈10.5→11) |
| afet (disaster) | MUDAHALE_BEDEL.afet × mudahale_oran% | 20×70% = 14 |
| bilgi (teach) | MUDAHALE_BEDEL.bilgi × mudahale_oran% | 12×70% = 8 (8.4→8) |

Rarity gates – `kapiyiGecer(rarity, key)` = rarity order ≥ `NADIRLIK_KAPI[key]` (tunable, value is rarity order 0–5). Creation tools use `NADIRLIK_KAPI.tur_<type>` (default = the type's `tier`). Tool gates (defaults):
| gate key | default min rarity | tools |
|---|---|---|
| etkile | Distinguished (1) | varligi_etkile, secilmis_ilan_et, lanetle |
| mucize | Distinguished (1) | mucize |
| ruh_kapla | Distinguished (1) | ruh_kapla |
| nadir_araclar | Rare (2) | ruya_gonder, afet_gonder, bilgi_ver, savas_kiskirt |
| kutsal_dunya | Rare (2) | kutsal_dunya_ilan |
| antlasma | Rare (2) | antlasma_yap |
| yabanci_savas | Rare (2) | yabanci_tanriyla_savas (and engine's spontaneous war) |
| can_al | Rare (2) | can_al |
| kapi_muhurle | Epic (3) | kapi_muhurle |
| yildiz_tutustur | Epic (3) | yildiz_tutustur |
| sizinti_dik | Epic (3) | sizinti_dik |
| efsanevi_araclar | Legendary (4) | donustur, yok_et, evlat_dogur |
| yatak_ac | Legendary (4) | yatak_ac |
| dunya_dogur | Legendary (4) | dunya_dogur |
| yildiz_as | Mythic (5) | yildiz_as, yildiz_sondur |

Level-up – `kazanc(son, xp, fame, epoch)` (exported; also used by the engine):
```
son.xp += xp; son.un += fame
while son.xp >= xpEsik(son.seviye):            // xpEsik(l) = KURAL.xp_seviye × l
    son.xp -= xpEsik(son.seviye); son.seviye += 1
    a, b = two random stat keys (may coincide)
    son.statlar[a] = clamp(+seviye_stat1, 1, 100); son.statlar[b] = clamp(+seviye_stat2, 1, 100)
    note "Level {n}! {a} +{x}, {b} +{y}."
    chronicle(epoch, son, 'sistem', "{name} grew stronger and rose to rank {n}.")
    if seviye ∈ [1,3,5] at index i and son.gucler[i] exists:
        note "Your new power awoke: {power name}."; chronicle 'sistem' "A new power awoke within {name}: {power}."
return notes joined (caller must saveSon)
```

### 4. Input sanitation and shared validation

`alanTemizle(value, key, optional)` (applied to numeric/array/object fields only):
- Identity fields (key matches `/(^|_)ids?$/`, e.g. `id`, `ogul_id`, `ogrenen_ids`): arrays are cleaned element-wise and "empty" elements dropped. For an OPTIONAL field, `null`, `0`, `""`, `"#0"`, `"yok"`/`"none"`/`"null"`/`"undefined"`/`"-"` → `undefined` (absent). For a REQUIRED id field only null/empty/"none"-like strings are absent; `0` stays (e.g. 0 = creator in mortal `tapin`).
- Strings: `"2,5"` → 2.5 (decimal comma); otherwise `girdiTemizle`: `"#12"`, `" 12 "`, `"id 12"`, `"yabanci#12"`, `"rota#1"`, `"oğul#3"`, `"dünya#2"` → 12/1/3/2 (whole string must look like an id; prefix ≤20 letters/underscore/space then `#`).
- Recurses into arrays and objects.
`kimlikTemizle(v)` = `alanTemizle(v)` (exported).

`sayi()` = `z.number` with custom Turkish error (English):
- missing: "{field} was left empty: this field is required, write a number (if it is an id, an id from the list)."
- too_small: "{field} must be at least {min} ({input} was written)."
- too_big: "{field} can be at most {max} ({input} was written)."
- non-integer: "{field} must be an integer ({input} was written)."
- other: "{field} must be a number ({input≤50} was written)."

`esnekEnum(values)` – tolerant enum: `esnekDeger` normalizes (trim, Turkish lowercase, strip diacritics ç→c ğ→g ı→i ö→o ş→s ü→u â→a î→i û→u, `[\s_-]+`→space) and matches exactly, else prefix match when input ≥3 chars. LANGUAGE-SPECIFIC diacritic folding: replace with case/whitespace/underscore-insensitive matching for English enums.

`durumNedeni(v)` (exported; shared with mortal tools) – reason an entity cannot be targeted:
- olu: "#{id} {name} is dead{ (died in Epoch N)}; this action cannot be done to the dead."
- yok_edildi: "#{id} {name} was destroyed{ (Epoch N)}; it is no longer in the world."
- reddedildi: "#{id} {name} was rejected by Fate; it counts as never having existed."
- gerceklesti: "#{id} {name} has been fulfilled; it is no longer a pending prophecy."
- other: "#{id} {name} is currently {state label}; this action cannot be done to it."

`kayitDurumu(id)` (exported): null id → "No record selected: write an id from the list."; missing → "There is no record numbered #{id}."; canonical → null; else `durumNedeni`.
`kanonDisi(...xs)` (exported): first non-canonical entity's reason or null.

`dunyaDisi(v)` – a son only acts on the world it stands on: if ≥2 worlds exist and `v.dunya_id != son.aktif_dunya` → "#{id} {name} is in another world (world#{n} {world name}); you are currently on world#{m}, your hand does not reach there."

`kardesUzak(k)` – sibling encounter (challenge, pact) needs same world, or a known active route (`rotalar.aktif=1 AND bilinen=1`) between the two worlds; else "{name} is in another world (world#{n} {name}); there is no known road between you. Turn there first."

`checkAP(n)` → "Your action points for this epoch are spent (remaining {ap}). You can still use read tools and free tools, or speak your word and finish."

`checkLinks(links)` – for each link: son target must exist ("There is no sibling son#{id} (if the bond goes to an entity, write hedef_tip 'varlik')."); entity target must exist ("Link: there is no record numbered #{id}."), not be `reddedildi`/`yok_edildi` ("Link: {reason}"), and be on the son's world.

`konumCikar(links, allowedTypes)` – infer a missing mandatory location: first linked canonical entity (same world) whose type is allowed (and state kanon/olu); else the `konum_id` of a linked entity if that location is allowed.

`ogulunEli(fn)` – "the son's cosmic hand": runs `fn`, then `UPDATE kronik SET ogul_id=sonId WHERE id > maxIdBefore AND ogul_id IS NULL` so chronicle lines written by creator-side helpers are attributed to the son.

`altTurDuzelt(subtype, type)` (exported; used by son tools, mortal tools and repair): normalizes a model-written subtype:
1. `altTurEtiketle` maps raw keys (e.g. `calgi`, "arac: tuz kefesi") to their display label; collapse whitespace.
2. If the lowercase-first-letter variant is more frequent for this type in DB, use it.
3. If multi-word and the last word ≥2 chars, and a more frequent subtype of the same type starts with this text and is at most 2 chars longer with no space in the extension (the model truncated the last word), use that.
LANGUAGE-SPECIFIC (Turkish casing `toLocaleLowerCase('tr')`, label table): port the idea as "snap to the most common existing subtype spelling".

`LinkSchema` (bond input used by creation tools and `bag_kur`):
```json
{ "type": "object", "properties": {
  "hedef_tip": {"enum": ["varlik","ogul"], "description": "'varlik' a world entity, 'ogul' a sibling from the pantheon (or yourself)"},
  "hedef_id":  {"type": "integer"},
  "tur": {"enum": BOND_TYPES, "description": "Bond type. Direction is corrected by the engine: konusur (speaks), sahip (owns), kutlar (celebrates), bilir (knows), yonetir (rules) always point community/mortal → language/item/tradition/knowledge/place (when creating a language, give the 'konusur' bond to the people who speak it). E.g.: yasar (lives in), tapar (worships), korur (protects), dusman (enemy), soyundan (descends from), kaynagi (source of), anlatir (tells of). Use 'ilgili' (related) only if no other type fits."},
  "aciklama": {"type": "string", "maxLength": 200, "description": "Short description of the bond. Use 'ilgili' only if no concrete type fits, and then you MUST write the relation here."}
}, "required": ["hedef_tip","hedef_id","tur"] }
```
BOND_TYPES (`BAG_TURLERI`, 50): icinde located_in, yasar lives_in, tapar worships, dusman enemy_of, muttefik ally_of, soyundan descends_from, korur protects, yonetir rules, sahip owns, dovdu defeated, oldurdu killed, lanetledi cursed, kutsadi blessed, kaynagi source_of, anlatir tells_of, yok_etti destroyed, sever loves, korkar fears, avlar hunts, ticaret trades_with, kehanet_eder prophesies_about, neden_oldu caused, kutlar celebrates, yasaklar forbids, konusur speaks, uretti produced, insa_etti built, gocetti migrated_to, kesfetti discovered, ruhu_indi spirit_descended_into, taraf party_to, uyesi member_of, bilirdi knew (historical), konusurdu spoke (historical), bilir knows, harac_oder pays_tribute_to, ilgili related_to, esir holds_captive, casus spy_network_in, pesinde pursues, yoldas companion_of, hasim rival_of, ustasi apprentice_of (label "çırağı"), komutan commands, parcasi part_of, yolcusu passenger_of, kaptan captain_of, evcil tamed, ateskes truce_with, borclu indebted_to.
NARRATIVE bonds (`ANLATI_BAGLARI`, the only ones `bag_kur` may create): anlatir, sever, korkar, ilgili, kehanet_eder, yasaklar, pesinde, yoldas, parcasi, kaynagi, neden_oldu, kutlar, soyundan.

`KelimeSchema` (exported; dictionary words; used by `kelime_tureti` and `dil_yarat`):
```json
{ "type": "array", "minItems": 1, "maxItems": 40, "items": { "type": "object", "properties": {
  "kelime": {"type":"string","minLength":1,"maxLength":40},           // word
  "anlam":  {"type":"string","minLength":1,"maxLength":200},          // meaning
  "tur":    {"enum":["isim","fiil","sıfat","ek","unvan","yer adı","özel ad","ünlem","sayı"]},  // noun, verb, adjective, suffix, title, place name, proper name, interjection, numeral (optional)
  "koken":  {"type":"string","maxLength":240,"description":"Etymology: from which event or which words it derived"},
  "ornek":  {"type":"string","maxLength":240,"description":"Short usage example and its translation"}
}, "required": ["kelime","anlam"] } }
```
The per-call cap is the world rule `kelime_adet`, enforced by slicing in the tool.

Domains (`ALANLAR`, 40): Sea, Fire, Earth, Sky, Storm, Death, Life, Dream, Time, Light, Shadow, War, Craft, Knowledge, Love, Trickery, Hunt, Plants, Bone, Blood, Sound, Stone, Ice, Madness, Trade, Road, Plague, Harvest, Moon, Sun, Star, Lies, Oath, Memory, Hunger, Glass, Salt, Ash, Boundary, Sleep. (Turkish: Deniz, Ateş, Toprak, Gök, Fırtına, Ölüm, Yaşam, Rüya, Zaman, Işık, Gölge, Savaş, Zanaat, Bilgi, Aşk, Hile, Av, Bitki, Kemik, Kan, Ses, Taş, Buz, Delilik, Ticaret, Yol, Veba, Hasat, Ay, Güneş, Yıldız, Yalan, Yemin, Bellek, Açlık, Cam, Tuz, Kül, Sınır, Uyku.) `alanEsle(value, fallback)` maps a free-text domain to the list (exact case-insensitive, then substring either way, else fallback = son's `alan1`).

Image-prompt rule appended to every `gorsel_prompt` description (`GORSEL_YAZIM`, already English): "Image prompt rules: describe only what IS visible; never use negations (no, without, not, lacking, absent) because the image model ignores them and draws the thing anyway; describe the replacement instead (e.g. "a smooth blank head with a single thin dark slit" rather than "no face"). Whatever the subject (person, creature, place, object, event or god), name at least two details unique to this world so the image never falls back to a generic real-world look." Stored prompts pass through `promptDuzelt({tur, etiketler}, prompt)` (gorselyon.js).

### 5. Tool reference

Notation: **Avail** = when the tool is present on the server; **AP** = action points spent; **Ess** = essence cost; **Limit** = per-epoch cap. "Description" is the exact model-facing text translated (numbers in `{}` are interpolated from tunables at build time). Unless stated, every entity id is validated with `kayitDurumu` (must exist and be `kanon`) and `dunyaDisi` (must be on the son's world), and every rejection is an `err()` (no state change). Order of checks matters and is listed as implemented.

Tool summary:
| # | TR name | EN name | Avail (min rarity / condition) | AP | Essence | Limit |
|---|---|---|---|---|---|---|
| 1 | dunya_ozeti | world_summary | always | 0 | 0 | – |
| 2 | varlik_incele | inspect_entity | always | 0 | 0 | – |
| 3 | varlik_ara | search_entities | always | 0 | 0 | – |
| 4 | hafizam | my_memory | always | 0 | 0 | – |
| 5 | kardesi_incele | inspect_sibling | always | 0 | 0 | – |
| 6 | plan_yaz | write_plan | always | 0 | 0 | – |
| 7 | capa_sec | choose_anchor | always | 0 | 0 | capa_tur |
| 8 | kelime_tureti | coin_words | always | 0 | 0 | kelime_tur calls, kelime_adet words each |
| 9 | kardese_seslen | call_sibling | always | 0 | 0 | mesaj_tavan |
| 10 | ahit_et | swear_covenant | always | 0 | 0 | – |
| 11 | armagan_ver | give_gift | always | 0 (essence gift) / 1 (worshipper transfer) | gift amount | armagan_tur |
| 12 | meydan_oku | challenge | always | 1 | 0 | – |
| 13 | isyan_et | rebel | always | 0 | 0 | once (while not rebel) |
| 14 | babaya_dua | pray_to_creator | always | 0 | 0 | dua_tur |
| 15 | bag_kur | make_bond | always | 0 | bag_bedel | bag_tavan |
| 16 | kaynak_sag | harvest_resource | always | 0 | (gains) | once per resource |
| 17–39 | `<type>` creation tools (23) | create_* etc. | per type tier | 1 (some free) | computed | – |
| 40 | varligi_etkile | affect_entity | Distinguished (etkile) | 1 | 6(×2)+power | – |
| 41 | secilmis_ilan_et | declare_chosen | Distinguished (etkile) | 1 | 14 | – |
| 42 | lanetle | curse | Distinguished (etkile) | 1 | 12+2×power (×50% curser) | – |
| 43 | can_al | take_life | Rare (can_al) and OLUM.can_al_tur>0 | 1 | canAlmaBedeli | OLUM.can_al_tur |
| 44 | kardesini_dirilt | resurrect_sibling | OLUM.kardes_tur>0 and a dead sibling exists | 1 | 45/70/25 by path | OLUM.kardes_tur (shared) |
| 45 | kemikleri_dagit | scatter_bones | same as 44 | 1 | OLUM.dagit_bedel | OLUM.kardes_tur (shared) |
| 46 | mucize | miracle | Distinguished (mucize) | 1 | OGUL_KOZMIK.mucize()+power | – |
| 47 | ruya_gonder | send_dream | Rare (nadir_araclar) | 1 | 10 | – |
| 48 | afet_gonder | send_disaster | Rare (nadir_araclar) | 1 | OGUL_KOZMIK.afet()+2×power | – |
| 49 | bilgi_ver | teach_knowledge | Rare (nadir_araclar) | 1 | OGUL_KOZMIK.bilgi() | – |
| 50 | savas_kiskirt | incite_war | Rare (nadir_araclar) | 1 | 10 | – |
| 51 | donustur | transform | Legendary (efsanevi_araclar) | 1 | 15+2×power | – |
| 52 | yok_et | destroy | Legendary (efsanevi_araclar) | 1 | 25+3×power | – |
| 53 | evlat_dogur | birth_child | Legendary (efsanevi_araclar) | evlat_dogur_ap (2) | 60 | one pending at a time |
| 54 | dunyaya_yonel | move_to_world | ≥2 worlds AND world.ogul_dagitim == 'otomatik' | 0 | 0 | – |
| 55 | kutsal_dunya_ilan | declare_holy_world | ≥2 worlds AND Rare (kutsal_dunya) | 0 | 0 | kutsal_dunya_tur |
| 56 | kapi_muhurle | seal_gate | Epic (kapi_muhurle) | 1 | OGUL_KOZMIK.muhur() | – |
| 57 | yildiz_tutustur | rekindle_star | Epic AND a dead star exists | tutustur_ap (2) | OGUL_KOZMIK.tutustur() | – |
| 58 | ruh_kapla | bind_spirit | Distinguished (ruh_kapla) AND a canonical spirit exists | 1 | OGUL_KOZMIK.ruh() | – |
| 59 | yildiz_as | hang_star | Mythic (yildiz_as) | yildiz_as_ap (2) | OGUL_KOZMIK.yildiz_as() | – |
| 60 | yildiz_sondur | extinguish_star | Mythic (yildiz_as) | sondur_ap (2) | OGUL_KOZMIK.yildiz_sondur() | – |
| 61 | yabanci_tanriyla_konus | talk_to_foreign_god | a contacted (`temas=1`) awake foreign god exists (any rarity) | 1 | 0 | – |
| 62 | antlasma_yap | make_interworld_treaty | ≥2 worlds AND Rare (antlasma) | antlasma_ap (1) | antlasma_oz (20) | – |
| 63 | sizinti_dik | seal_leak | Epic (sizinti_dik) | sizinti_ap (1) | sizinti_oz (35) | sizinti_dik_tur |
| 64 | yatak_ac | open_cosmic_bed | Legendary (yatak_ac) | yatak_ap (2) | yatak_oz (60) | – |
| 65 | yabanci_tanriyla_savas | war_on_foreign_god | Rare (yabanci_savas) AND contacted awake foreign god exists | ysavas_ap (2) | ysavas_oz (30) | – |
| 66 | dis_varlikla_pazarlik | bargain_with_outsider | a canonical `dis` (outer being) exists (any rarity) | 0 | 0 (gains) | dis_pazarlik_tur |
| 67 | dunya_dogur | birth_world | Legendary (dunya_dogur) | dunya_dogur_ap (2) | DENGE.dunya_dogur (70) | one pending at a time |

---

#### 5.1 Read and reflection tools (free)

**1. `dunya_ozeti` → `world_summary`** (read tool)
- Description: "Shows the world's current map, laws, pantheon, open stories and recent events. Give `bolum` to see in full a section that was truncated in the prompt ({sections}). Free."
- Input: `bolum` optional enum `OZET_BOLUMLERI` = `panteon` pantheon, `iplikler` threads, `olaylar` events, `kozmos` cosmos, `cografya` geography, `diller` languages, `harita` map, `efsaneler` legends — "Show only this section in full".
- Effect: returns `dunyaOzeti(son, { bolum })` (world.js context builder; without `bolum` the budgeted summary, with `bolum` that section untruncated).

**2. `varlik_incele` → `inspect_entity`** (read)
- Description: "Shows all details of an entity: its stats, bonds and what is inside it. Free."
- Input: `id` integer (required).
- Effect: `varlikDetay(id)`; if null → err "#{id} does not exist." (Note: works on any state, including dead/destroyed.)

**3. `varlik_ara` → `search_entities`** (read)
- Description: "Searches entities by a word appearing in the name or description. Type filter optional. Free."
- Input: `sorgu` string (required) — "Word to search; leave empty for recent entities"; `tur` optional enum entity type keys.
- Effect: `varlikAra(query, type)`; each result rendered with `varlikSatir`; none → "No results."

**4. `hafizam` → `my_memory`** (read)
- Description: "Shows your plan, words said to you, your creations, your worshippers, your memories and what concerns you; the full version of the truncated memory in the prompt. Free."
- Input: none. Effect: `hafiza(son, { tam: true })`.

**5. `kardesi_incele` → `inspect_sibling`** (read)
- Description: "Shows a sibling's visible face, powers, creations and relationship with you. Free."
- Input: `ogul_id` integer.
- Validation: unknown → "No such sibling."
- Output (lines):
  - `son#{id} {name}, {title} — {Rarity}, domains {a1}/{a2}, Level {n}, state {state}`
  - `Appearance: …`, `Temperament: …`, `Speech: …` (from personality `gorunus`, `mizac`, `uslup`)
  - `Known powers: {names of unlocked powers} | none`
  - `Strength {g}, Wisdom {b}, Cunning {k}, Charisma {c}, Will {i} · HP {can}/{canMax} · Faith {inanc} · Fame {un}`
  - `Towards you: {relation label} ({value}){ · there is a covenant between you}`
  - `Creations:\n{up to kardes_yaratim latest canonical creations, varlikSatir}` or "(none)".
  Hidden from siblings: secret, fear, obsession, passions, other stats.

**6. `plan_yaz` → `write_plan`** (free)
- Description: "You write or update your long-term plan. It appears in your memory in future epochs; it lets you build a coherent story across epochs. Free."
- Input: `plan` string 20–1500 — "Your goal spread over several epochs and your next steps".
- Effect: `son.plan = plan`; save. Result: "Your plan is carved into your heart."

**7. `capa_sec` → `choose_anchor`** (free; Limit `capa_tur`)
- Description: "You choose one of your own creations as the anchor of your existence. While your anchor lives your existence stays firm; if it is destroyed you begin to fade. Free, once per epoch."
- Input: `varlik_id` integer; `neden` (reason) string 10–300.
- Validation: `ctx.capaSecildi >= capa_tur` → "You already changed your anchor this epoch (World rule OGUL_ARAC.capa_tur = {n})."; `kayitDurumu`; entity must be canonical and `yaratan_id == son.id` → "Your anchor can only be your own canonical creation."
- Effect: `son.capa_id = id`; `ctx.capaSecildi++`; chronicle type `varolus`: "{son} bound their existence to {entity}: {reason}" (ids [entity]). Result: "{entity} is now your anchor. Protecting it is protecting yourself." (Existence math in rules.js `varlikHedefi`: living anchor +`varlik_capa`, destroyed anchor −`varlik_capasiz`.)

**8. `kelime_tureti` → `coin_words`** (free; Limit `kelime_tur` calls)
- Description: "You add words to a language's dictionary: meaning, word class and origin (from which event, from which words it was born). Languages grow this way and new names are derived from these words. Free, limited number per epoch (world rule)."
- Input: `dil_id` integer; `kelimeler` KelimeSchema.
- Validation: `ctx.kelimeSayisi >= kelime_tur` → "You have coined enough words this epoch."; words sliced to `kelime_adet`; language must be canonical (`kayitDurumu` message) and `tur == 'dil'` → "This is not a language. A Language entity must exist first."
- Effect: `ctx.kelimeSayisi++` (only after validation – invalid attempts do not consume); `sozlukEkle(langId, words, 'o', sonId, cag)` returns the added words (duplicates skipped); if any → chronicle `dil`: "{son} whispered new words into the {language} tongue: {w1, w2…}." Result: "Added to the {language} dictionary: {…}." or "No word was added (all already existed)."

#### 5.2 Social tools

**9. `kardese_seslen` → `call_sibling`** (free; Limit `mesaj_tavan`)
- Description: "Sends a word to one of your siblings. The word also goes into the chronicle; it changes the relationship according to intent and your charisma. Does not spend an action, limited number per epoch."
- Input: `ogul_id` int; `niyet` (intent) enum `dostluk` friendship | `ittifak` alliance | `ask` love | `tehdit` threat | `alay` mockery | `uyari` warning | `pazarlik` bargain; `mesaj` string 5–500.
- Validation: `ctx.mesajSayisi >= mesaj_tavan` → "You have spoken enough this epoch."; sibling missing or self → "Invalid sibling."; sibling dead → "{name} is dead; your word does not reach their bones." (No world-distance check.)
- Effect:
  ```
  e = round(ses_taban + charisma / ses_karizma_bolen)
  delta = {friendship: e, alliance: e+ses_ittifak, love: e+ses_ask, threat: −e−ses_tehdit, mockery: −e, warning: −ses_uyari, bargain: ses_pazarlik}[intent]
  rel = iliskiDegistir(me, sib, delta)
  INSERT mesajlar(cag, kimden_tip 'o', kimden_id me, kime_tip 'o', kime_id sib, niyet, metin)
  chronicle 'mesaj': "{me} {intent phrase} to {sib}: \"{message}\""
  ctx.mesajSayisi++
  ```
  Intent phrases (SOZ_NIYET): friendship "spoke warmly", alliance "proposed an alliance", love "declared their love", threat "spoke with a threat", mockery "spoke mockingly", warning "gave a warning", bargain "proposed a bargain".
- Result: "Your word reached {sib}. Between you now: {relation label} ({value})."

**10. `ahit_et` → `swear_covenant`** (free)
- Description: "You make a covenant (alliance) with a sibling. The relationship between you must be at least {ahit_esik} (inspect_sibling shows the 'Towards you' number; if it is below, first get closer with call_sibling or give_gift). A covenant strengthens the relationship; challenging a covenanted sibling breaks the covenant and ruins your fame. Does not spend an action."
- Input: `ogul_id` int; `sart` (terms) string 10–400 — "The covenant's condition, its oath".
- Validation: missing/self → "Invalid sibling."; dead → "{name} is dead; no covenant with the dead."; existing covenant (`ahitVar`) → "There is already a covenant between you."; `kardesUzak`; relation < ahit_esik → "{name} does not trust you enough: your relation is {rel}, a covenant needs at least {ahit_esik} (World rule OGUL_ARAC.ahit_esik). Build friendship first."
- Effect: bond `o:me → o:sib` type `muttefik` (description = terms); relation += `ahit_bonus`; chronicle `ahit`: "{me} and {sib} swore a covenant: \"{terms}\"". Result: "Covenant made. Between you: {label} ({value})."

**11. `armagan_ver` → `give_gift`** (Limit `armagan_tur`)
- Description: "You give a gift to a sibling: a share of your essence and/or you try to transfer a community that worships you to them (the community may not accept). A gift strengthens the relationship. An essence gift does not spend an action; a worshipper transfer costs 1 action. Once per epoch."
- Input: `ogul_id` int; `oz` int 0–1000 optional — "Essence to give (up to the world-rule cap)"; `tapan_id` int optional — "id of the community that worships you and that you will transfer to them"; `soz` (words) string 5–300 — "The word you say with the gift".
- Validation (order): `ctx.armagan >= armagan_tur` → "You already gave a gift this epoch (World rule OGUL_ARAC.armagan_tur = {n})."; sibling missing/self/dead → "Invalid sibling."; neither essence nor worshipper → "Give either essence or a worshipping community."; `oz > armagan_oz` → "At most {armagan_oz} essence per gift."; `oz > me.oz − armagan_kalan` → "You cannot give that much essence; you have {oz}."; worshipper given and AP < 1 → checkAP message; worshipper not canonical → kayitDurumu; `hami(t) != me` → "#{id} does not worship you."
- Effect:
  ```
  if oz: me.oz −= oz; sib.oz = min(ozMax(sib), sib.oz + oz)
  if tapan: ctx.ap −= 1
     accept = d(100) <= devir_taban + round((sib.karizma − (t.inanc ?? devir_inanc_varsayilan)/devir_inanc_bolen) / devir_fark_bolen)
     accept → deactivate active 'tapar' bond t→me; add bond v:t → o:sib 'tapar' ("{me}'s gift")
     refuse → chronicle 'armagan': "{t} refused {me}'s transfer of it to {sib}; it stayed loyal to its old god."
  save both; ctx.armagan++
  rel += armagan_iliski + round(oz / armagan_oz_bolen) + (accepted ? armagan_tapan_iliski : 0)
  chronicle 'armagan': "{me} gave {sib} a gift: {notes}. \"{words}\""
  ```
- Result: "Gift given: {notes}. Between you: {label} ({value}). {status line}"

**12. `meydan_oku` → `challenge`** (1 AP)
- Description: "You challenge a sibling in a domain; the result is decided by dice, stat, level and powers. The winner gains fame, experience and a share of the loser's essence; the loser is wounded, and falls asleep if their HP runs out. 1 action."
- Input: `ogul_id` int; `alan` (arena stat) enum `guc` strength | `bilgelik` wisdom | `kurnazlik` cunning | `karizma` charisma | `irade` will; `sebep` (reason) string 5–300.
- Validation: AP; missing/self → "Invalid sibling."; sibling not `aktif` → "{name} is currently {state}; they cannot be challenged."; `kardesUzak`.
- Effect: `ctx.ap −= 1`, then `meydanOkuma(me, sib, stat, reason, epoch)` (exported, also used by the engine's rival clashes):
  ```
  covenantBroken = ahitVar(me, sib)
  bonus(s, rival) = (gucVar(s,'meydan', stat) ? meydan_guc_bonus : 0) − (gucVar(rival,'dokunulmaz') ? meydan_dokunulmaz : 0)
  score(s, die, rival) = s.statlar[stat] + die×meydan_zar_kat + s.seviye×meydan_seviye_kat + bonus(s, rival)
  p1 = score(me, d(meydan_zar), sib); p2 = score(sib, d(meydan_zar), me)
  winner = p1 >= p2 ? me : sib (ties go to the challenger)
  wound = meydan_yara + round(|p1−p2| / meydan_fark_bolen)
  loser.can −= wound; loser.un = max(0, un − meydan_un_kayip)
  stolen = min(meydan_calinti, loser.oz); loser.oz −= stolen; winner.oz = min(ozMax, winner.oz + stolen)
  lvl = kazanc(winner, meydan_xp, meydan_un)
  if loser.can <= 0: can=0, durum='uykuda', uyku_kalan = gucVar(loser,'dirilis') ? dirilis_uyku : meydan_uyku
  if covenantBroken: me.un = max(0, me.un − ahit_bozma_un); deactivate both directions of 'muttefik' son↔son bonds
  save both (transaction)
  rel = iliskiDegistir(me, sib, covenantBroken ? −meydan_ahit_iliski : −meydan_iliski)
  chronicle 'meydan': "{me} challenged {sib} to a trial of {stat} (\"{reason}\"). {winner} won ({p1}–{p2}); {loser} lost {wound} HP and had {stolen} essence snatched.{ {loser} collapsed and fell into a sleep that will last {n} epochs.}{ {me} thereby broke the covenant between them.}"
  ```
- Result: "{chronicle text} {level note} Your relation: {label} ({rel}). {status}{uyudun()}" — the challenger may be the loser and fall asleep, ending the turn.

**13. `isyan_et` → `rebel`** (free)
- Description: "You rebel against your father, the creator god: you no longer recognize his commands and every epoch you steal from his essence. Your loyal siblings become your enemies; your father may try to crush the rebellion. Only if your loyalty is low. Does not spend an action."
- Input: `bildiri` (proclamation) string 20–500 — "The word of the rebellion: why and for what".
- Validation: already `asi` → "You are already in rebellion."; loyalty (`tutku.sadakat ?? sadakat_varsayilan`) ≥ `isyan_sadakat` → "Your loyalty ({n}) does not permit rebellion."
- Effect: `tanriguc.js isyanIlan(son, epoch, text)` (same path as the engine's spontaneous rebellion): `asi=1`; loyalty −= `isyan_sadakat_kayip`; ambition += `isyan_hirs` (clamped 0–100); for every other son with loyalty ≥ `isyan_sadik_esik`: relation −= `isyan_kardes_iliski`; chronicle 'isyan': "{son} rebelled against their father {creator}: \"{proclamation}\"". Result: "Rebellion declared. You are no longer bound to your father's commands; every epoch you will steal from his essence."

**14. `babaya_dua` → `pray_to_creator`** (free; Limit `dua_tur`)
- Description: "You pray to your father, the creator god. You may have a request; the answer appears among words in coming epochs. Does not spend an action, once per epoch."
- Input: `mesaj` string 5–600; `istek` (request) enum `oz` essence | `kutsama` blessing | `izin` permission | `intikam` revenge | `af` forgiveness | `hicbiri` none.
- Validation: `ctx.duaEdildi >= dua_tur` → "You already prayed this epoch (World rule OGUL_ARAC.dua_tur = {n})."
- Effect: INSERT `mesajlar(cag, 'o', me, kime_tip 't', NULL, niyet 'dua', metin, istek)` (shown to the player as a prayer inbox); chronicle 'dua': "{son} prayed to their father{, asked for essence | asked for a blessing | asked permission | asked for revenge | asked forgiveness}: \"{message}\""; `ctx.duaEdildi++`. Result: "Your prayer rose to the sky."

**15. `bag_kur` → `make_bond`** (free; Ess `bag_bedel`; Limit `bag_tavan`)
- Description: "You declare a narrative bond between two existing things ({narrative bond list}). It densifies the world's web. Worship, enmity, knowledge, ownership, captivity and alliance are not made with this tool; they have their own tools. Needs a little essence, does not spend an action, limited per epoch."
- Input: `kaynak_id` int — "The entity that is the source of the bond"; `hedef` LinkSchema.
- Validation: `ctx.bagSayisi >= bag_tavan` → "You have woven enough bonds this epoch."; `me.oz < bag_bedel` → "You do not have enough essence."; type not in ANLATI_BAGLARI → "\"{type}\" is a mechanical bond; make_bond only makes narrative bonds ({list})."; source must exist with state kanon/olu/gerceklesti → "Source: {kayitDurumu}"; source on son's world; `checkLinks([target])`; entity target == source → "A thing cannot be bound to itself."; entity target on son's world.
- Effect: `me.oz −= bag_bedel`; add bond `v:source → (o|v):target` type/description; `ctx.bagSayisi++`; chronicle 'yaratim': "{son} wove a bond: {source} {type} {target name}{ — description}." Result: "Bond made. {status}"

**16. `kaynak_sag` → `harvest_resource`** (free; once per resource per epoch)
- Description: "You draw essence from a Resource entity. Resources you created yourself, resources of your own domain, or resources owned by those who worship you can be harvested. Its abundance decreases. Does not spend an action; each resource once per epoch."
- Input: `kaynak_id` int.
- Validation: kayitDurumu; type must be `kaynak` → "This is not a resource."; dunyaDisi; already in `ctx.sagilan` → "You already harvested this resource this epoch."; right = creator is me OR resource.alan ∈ {alan1, alan2} OR any active `sahip` (owns) bond from an entity whose patron (`hami`) is me → else "You have no right over this resource: you did not create it, it is not of your domain, and its owner does not worship you."; abundance < `sag_tukenme` → "The resource is exhausted."
- Effect:
  ```
  gain = round(abundance/sag_bolluk_bolen + wisdom/sag_bilgelik_bolen + potency/sag_kudret_bolen)
  if gucVar(me,'hasat'): gain ×= sag_hasat_kat
  resource.bolluk = clamp(bolluk − sag_bolluk, 0, 100)
  me.oz = min(ozMax, me.oz + gain); ctx.sagilan.add(id)
  chronicle 'kaynak': "{son} drew {gain} essence from {resource}; the resource's abundance fell to {n}."
  ```
  Result: "+{gain} essence. {resource} abundance {n}. {status}"

#### 5.3 Creation tools (17–39), one per entity type

Generated in a loop over `VARLIK_TURLERI`: a tool is registered if the type has a tool name (`arac`) and `rarityAtLeast(son.nadirlik, type.tier)` (tier = `NADIRLIK_KAPI.tur_<type>`). `ordu` (army) and `dis` (outer being) have no tool (engine-only).

Type table (base cost = `YARATIM_TABANI.<type>` tunable; tier = default min rarity):
| type (TR) | English | tool (TR → EN) | tier | base | location types | location required | stats (key Label min–max) | examples (model-facing `ornek`) |
|---|---|---|---|---|---|---|---|---|
| bolge | Region | bolge_yarat → create_region | Epic | 20 | region | no | genislik Breadth, tehlike Danger, bereket Fertility, buyu Magic density (0–100) | continent, inland sea, desert belt, archipelago, underworld |
| yer | Place | yer_yarat → create_place | Common | 6 | region, place | yes | tehlike Danger, bereket Fertility, gizem Mystery | mountain, forest, river, lake, cave, ruin, island, swamp, pass, well |
| kaynak | Resource | kaynak_yarat → create_resource | Common | 7 | region, place | yes | bolluk Abundance, deger Value, kudret Potency | ore vein, magical substance, healing herb, sacred spring, rare crystal, bone bed |
| yerlesim | Settlement | yerlesim_kur → found_settlement | Common | 6 | region, place | yes | nufus Population 10–2,000,000; refah Prosperity; savunma Defense; inanc Piety | village, port city, fortress, monastery, nomad camp, capital |
| tur | Species | tur_yarat → create_species | Common | 5 | region, place | no | can HP 1–1000; guc Strength; ceviklik Agility; zeka Intelligence; tehlike Danger | animal, plant, fungus, monster, spirit-kind |
| halk | People | halk_yarat → create_people | Common | 9 | region, place | yes | nufus Population 100–50,000,000; savascilik Martiality; buyu Magic; zanaat Craft; inanc Piety | race, folk/tribe, caste, mortal lineage |
| olumlu | Mortal | olumlu_yarat → create_mortal | Common | 5 | region, place, settlement | yes | can HP 1–300; guc Strength; ceviklik Agility; akil Wits; karizma Charisma; yas Age 0–50,000; omur Lifespan 1–50,000 | hero, king, seer, bandit, artisan, saint |
| esya | Item | esya_dov → forge_item | Distinguished | 10 | region, place, settlement | no | hasar Damage, koruma Protection, kudret Potency, lanet Curse | weapon (sword, spear, bow), armor, shield, crown, mirror, book, seal, musical instrument, tool, holy relic |
| yapit | Monument | yapit_insa → build_monument | Distinguished | 9 | region, place, settlement | yes | ihtisam Splendor, saglamlik Sturdiness, islev Function | temple, tower, bridge, wall, monument, tomb, observatory, harbor, mine, library |
| dil | Language | dil_yarat → create_language | Distinguished | 8 | – | no | yayginlik Prevalence, karmasiklik Complexity, kutsallik Sanctity | spoken language, sacred language, writing system, sign language, merchants' cant, language of the dead |
| efsane | Legend | efsane_anlat → tell_legend | Common | 4 | – | no | yayginlik Prevalence | lullaby, taboo, proverb, founding myth, ghost story |
| gelenek | Tradition | gelenek_kur → establish_tradition | Common | 5 | – | no | yayginlik Prevalence, katilik Rigidity | festival, taboo, funeral rite, initiation, oath ceremony, seasonal offering |
| tarikat | Cult | tarikat_kur → found_cult | Distinguished | 9 | region, place, settlement | yes | murit Followers 1–10,000,000; bagnazlik Zealotry; etki Influence | temple order, secret sect, priestly caste |
| hizip | Faction | hizip_kur → found_faction | Distinguished | 9 | region, place, settlement | yes | guc Military strength, servet Wealth, nufuz Clout | kingdom, guild, knightly order, pirate league, dynasty |
| gok | Celestial body | gok_cismi_as → hang_celestial_body | Rare | 14 | – | no | parlaklik Brightness, etki Influence | star, constellation, moon, comet, wandering light, wound in the sky |
| eser | Work | eser_yarat → create_work | Common | 5 | region, place, settlement | no | un Fame, etki Influence | folk song, epic, statue, fresco, play, book, dance, lament, weaving |
| kanun | Law | kanun_koy → enact_law | Distinguished | 7 | region, place, settlement | no | katilik Rigidity, adalet Justice | penal law, inheritance rule, trade law, worship ban, blood-feud custom |
| ruh | Spirit | ruh_cagir → summon_spirit | Distinguished | 8 | region, place, settlement | no | guc Power, huzursuzluk Restlessness | ghost, ancestor spirit, haunting, guardian spirit, lost soul |
| teknoloji | Knowledge | bilgi_ilham_et → inspire_knowledge | Rare | 12 | – | no | seviye Level 1–10, yayginlik Prevalence | agriculture, metallurgy, seafaring, writing, architecture, medicine, school of magic, art of war, astronomy, trade practice |
| kehanet | Prophecy | kehanet_soyle → utter_prophecy | Epic | 10 | – | no | kesinlik Certainty | prophecy, doom omen, cursed word |
| olay | Event | olay_baslat → start_event | Epic | 18 | region, place, settlement | no | siddet Severity | war, plague, flood, famine, migration, uprising, catastrophe |
| arac | Vehicle | arac_yarat → create_vehicle | Rare | 14 | region, place, settlement | no | hiz Speed, menzil Range, murettebat Crew 0–100,000, zirh Armor, tuhaflik Strangeness | ship (light-sail, bone-hulled, generation ship), ancient gate, cosmic mount, divine bridge |
| yasa | Natural law | yasa_koy → decree_natural_law | Legendary | 30 | – | no | (none) | the return of the dead, the price of magic, the order of the seasons |
| ordu | Army | – (engine only) | Epic | 0 | region, place, settlement | no | buyukluk Soldiers 10–10M, moral Morale, techizat Equipment, deneyim Experience | army, legion, raider band, holy guard, fleet |
| dis | Outer being | – (engine only) | Mythic | 0 | region, place | no | buyukluk Size, ilgi Interest, etki Influence | the thing from outside the cosmos whose name is not spoken |

Living types (`CANLI_TURLER`): halk, olumlu, yerlesim, tur, tarikat, hizip. Land types: bolge, yer.

**Description template** (model-facing):
"Creates a {Type} ({examples}). {AP clause} Cost: {base}+{KURAL.bedel_guc_seviye}×power essence, cheap in your own domain (power 1, in your own domain ≈{exampleCost} essence)."
- AP clause for living types (when `canli_bedava > 0`): "Living creation: the first living creation each epoch does NOT spend an action; later ones cost 1 action."
- AP clause for land types: "1 action; if your world is crowded ({KESIF.dar_topluluk}+ communities per region) the epoch's first land creation{ does not spend an action and} grants +{KESIF.toprak_oz} essence, +{KESIF.toprak_un} fame." (bracketed part only when `KESIF.toprak_bedava > 0`)
- Otherwise: "1 action."
- `exampleCost = yaratimBedeli(base, 1, true, son.yaraticilik, cheap)`.

**Input schema** (common fields):
| field | type | description (model-facing, translated) |
|---|---|---|
| `ad` | string 2–60, required | "Original proper name; fitting the world's naming language. Generic names (River, Dark Forest, Dragon) are forbidden." |
| `alt_tur` | string ≤60, optional | "What it is, e.g.: {examples}" |
| `aciklama` | string 120–1400, required | "3–7 sentences. Concrete, sensory, strange details; how it was born, what it is connected with, how mortals know it." |
| `alan` | string, optional | "If empty, your first domain. The domain used in this creation; one of: {40 domains}. Your own domains are cheap." |
| `guc_seviyesi` | int 1–10, required | "Between 1–10; your ceiling is {tavan}. Increases the cost." |
| `statlar` | object, optional | one optional number per type stat, described "{Label} ({min}–{max})" |
| `baglantilar` | LinkSchema[] 1..`yaratim_bag_adet`, required | "At least 1 meaningful bond to existing entities/siblings. The location bond (icinde) is added automatically, do not repeat it." |
| `gorsel_prompt` | string ≤900, optional | "An English, photorealistic image-generation prompt: subject, material, light, setting, camera, lens. {GORSEL_YAZIM}" |
| `etiketler` | string(≤24)[] ≤6, optional | (tags) |
| `iplik_id` | int, optional | "Which open story (thread#) this creation advances" |
| `ortak_ogul_id` | int, optional | "To create together with a covenanted sibling, their id: they pay half the cost, the creation belongs to both of you" |
| `konum_id` | int, optional (only for types with location types) | "id of the entity it is inside ({Region/Place/Settlement})" + if required: ". It must have a location: if you leave it empty it is inferred from the region, place or settlement among your bonds (or from where the community you bond to is located)" |

Type-specific fields:
| type | field | schema / description |
|---|---|---|
| tarikat, halk, yerlesim, hizip | `tapilan_ogul_id` int opt | "Whom they worship (son id). For a cult, you if empty. Faith flows this way." |
| yasa | `mekanik` enum (required) | "The law's mechanical effect in the world: {key: text | …}" (YASA_MEKANIKLERI below) |
| teknoloji | `dal` enum (required) | "The knowledge's branch: {key: effect | …}" (BILGI_DALLARI below) |
| teknoloji | `ogrenen_ids` int[] ≤`ogrenen_adet` opt | "Communities that first learn this knowledge" |
| tur | `ozellikler` enum[] ≤`ozellik_adet` opt | "The creature's traits: {key (effect); …}" (OZELLIKLER below) |
| arac | `hedef_dunya_id` int opt | "If the gate, bridge or ship connects to another world, that world's id: a route is opened" |
| dil | `kelimeler` KelimeSchema (required) | "The language's first 3–8 words; matching the naming rule" |
| olumlu | `unvan` string ≤60 opt | "Their nickname or title (\"Salt Seer\", \"Ash Mouth\"); don't bury it in the name, write it here" |
| olay | `etkiler` array ≤`olay_etki_adet` opt of `{varlik_id int, stat string, yuzde number}` | "How the event is reflected on the stats of affected entities (e.g. war lowers population)." `yuzde`: "Percent change, between −90 and +50; its magnitude cannot exceed the severity" |

Natural-law mechanics (`YASA_MEKANIKLERI`): `yok` narrative only, no mechanical effect; `olumsuzluk` mortals do not age, but population grows at half speed; `kisa_omur` mortals age twice as fast, population grows 50% faster; `olu_doner` fallen heroes return as ghosts half of the time; `buyu_bedeli` high-magic peoples pay part of their population to magic every epoch; `savas_yasagi` wars break out half as often but are twice as bloody; `bereket` all lands' fertility rises every epoch; `kuraklik` all lands' fertility falls every epoch; `deniz_yasagi` seas cannot be crossed, seafaring is useless; `tek_dil` languages spread twice as fast through conquest and trade; `afet` natural disasters happen twice as often.

Knowledge branches (`BILGI_DALLARI`): tarim Agriculture (knowers' population grows 50% faster; famine and drought hit at half severity); metalurji Metallurgy (+15 damage/protection to weapons and armor they make); denizcilik Seafaring (trade, war and migration with communities beyond the sea); yazi Writing (their languages grow complex; what they know spreads to partners twice as fast); mimarlik Architecture (+20 splendor and sturdiness to their monuments; earthquake-resistant); tip Medicine (plagues hit at half severity; mortals' lifespan +20); buyu Magic (magic stat +10; items they make +10 potency); savas Art of war (+12 war power); gokbilim Astronomy (they read the epoch's star: foresee disasters, suffer them at half severity); ticaret Trade (double prosperity from trade routes); gokyuzu_seyri Sky navigation (can discover interworld routes; risk of getting lost halves); gemi_yapimi Shipbuilding (can build interworld ships (vehicles)); kapi_bilimi Gate lore (can open and close ancient gates; gate routes take one epoch); yol_biliciligi Way-knowing (can fold space: with the cosmic resource routes drop to one epoch); bosluk_yasami Void living (can colonize worlds with thin or no atmosphere; less loss in travel); olumsuzluk Quest for immortality (knowers' mortals reach for immortality; those who succeed do not age but gods see them as a threat); biyobuyu Biomancy (merges and alters living things: can weave chimeras, steer mutations); yasak Forbidden knowledge (great power: war +15, magic +15, forces gates. Price: knowers' sanity drops every epoch, leakage flows into their worlds; Fate watches).

Creature traits (`OZELLIKLER`, with war bonus): ucan Flying (easy migration, raids reach far; war +8); zehirli Venomous (grievous wounds in hunt and war; kills heroes easily; +10); ruh_yiyen Soul-eating (eats spirits in its region; gnaws the sanity of those nearby; +4); isik_sacan Light-shedding (lowers its region's danger, raises fertility; keeps Outer Beings away; 0); bolunerek Fission-breeding (spreads if unchecked: migration and invasion chance ×2; +2); suru_zekasi Swarm-minded (weak alone, clever together: intelligence +15, hard to hunt; +6); tas_derili Stone-skinned (heroes' weapons barely bite; +12); zaman_geri Time-rewinding (returns once in the epoch it is killed; 0); sekil_degistiren Shapeshifting (mixes among peoples; espionage and discord; +3); akil_okuyan Mind-reading (knows heroes' moves in advance; lowers sanity nearby; +8).

**Handler – exact order of operations:**
```
canliBedava  = canli_bedava>0 AND type ∈ LIVING AND !ctx.canliYaratim
toprakDar    = type ∈ {bolge, yer} AND darMi(son.aktif_dunya)          // ufuk.js: no regions OR communities(halk+yerlesim)/regions >= KESIF.dar_topluluk
toprakBedava = toprakDar AND KESIF.toprak_bedava>0 AND !ctx.toprakYaratim AND !canliBedava
if !(canliBedava or toprakBedava): checkAP(1)
a.alan    = alanEsle(a.alan, me.alan1)
a.alt_tur = altTurDuzelt(a.alt_tur || typeLabel.lower(), type)
a.baglantilar ||= []
if a.iplik_id and thread not open: note " (thread#{id} is not open; this creation did not count as advancing it)"; drop iplik_id
a.ad = trim; if a.ad matches /^([^,(]{2,40}?)\s*(?:,\s*|\(\s*)([^,()]{3,60}?)\)?$/ and group2 has a letter:
      a.ad = group1, a.unvan ||= group2              // "Seharen, Salt Seer" → name + title
REJECT if name ends with Roman numeral (II, III, IV, V–VIII, IX): "\"{name}\" is a numbered name; create something with its own name (not the second of the same name)."
REJECT if guc_seviyesi > tavan: "Your power level can be at most {tavan}."
REJECT if isimAlinmis(name): "The name \"{name}\" already exists. Choose an original name."
REJECT if benzerAd(name) = b: "The name \"{name}\" is too similar to the existing \"{b}\"; mortals would confuse the two. Choose a name that sounds clearly different."
REJECT checkLinks(baglantilar)
if type has locations and konum_id missing and location required: konum_id = konumCikar(links, allowed)
if konum_id given: konum must exist with state kanon/olu → "Location: {kayitDurumu}";
                   type allowed → "{Type} cannot be placed inside a {LocType}; put it in one of: {allowed keys}."; same world
elif location required: REJECT "konum_id is required for {Type} ({Region/Place/...} id){; for example: #id name, … (up to konum_oneri newest canonical allowed locations on the son's world)}."
uyum    = a.alan ∈ {alan1, alan2}
yildizli= epochStar exists and star.alan == a.alan
repeats, repeatMul, cost as §3
if ortak_ogul_id given and != me:
   partner must exist and be aktif → "The partner sibling does not exist or cannot act."
   covenant required → "You have no covenant with {p}; for a joint creation first swear_covenant."
   partner.oz >= ceil(cost/2) → "{p}'s essence ({oz}) does not cover their share ({ceil})."
   myShare = floor(cost/2)
REJECT if me.oz < myShare: "This creation needs {myShare} essence; you have {oz}. Lower the power, use your own domain, harvest a resource, or create something smaller."
if type == olay and etkiler:
   severity = clamp(statlar.siddet ?? olay_siddet_taban + power × olay_siddet_guc, 0, 100)
   each effect: target canonical ("Entity to be affected: {reason}"), same world,
     stat in type schema AND present → "#{id} {name} has no \"{stat}\" stat; available: {list | none}."
     |yuzde| <= severity → "Effect {pct}%, exceeds the severity ({severity})."
stats = fillStats(typeDef, a.statlar, power)
if olumlu: olumluYasi(stats)                   // age forced into [yas_min%, yas_max%] of lifespan
if esya: for each link of type 'kaynagi' to a resource: stats.kudret = clamp(kudret + resource.kudret / esya_kaynak_bolen, 0, 100)
TRANSACTION:
   tags = a.etiketler + ['yasa:{mekanik}'] (yasa) + ['dal:{dal}'] (teknoloji) + ['iplik:{id}'] + ['ortak:{partnerId}']
          + ['ozellik:{k}' for valid traits] (tur) + ['megafauna'] (tur with power >= megafauna_guc)
   INSERT varliklar(ad, tur, alt_tur, aciklama=anlatiTemizle(ekDuzelt(desc)), statlar, guc_seviyesi, alan, yaratan_id=me,
          cag, konum_id, gorsel_prompt = promptDuzelt({tur, etiketler}, prompt) or NULL, etiketler, kaynak='ogul', unvan)
   if konum: bond v:new → v:konum 'icinde'
   for each link (skip an 'icinde' link equal to konum): bond v:new → (o|v):target type, description
   worshipped = tapilan_ogul_id ?? (cult ? me : null); if exists and no 'tapar'→son link given: bond v:new → o:worshipped 'tapar'
   mandatory owner bond: esya→'sahip', gelenek→'kutlar', teknoloji→'bilir':
      if no such active bond pointing at the new entity: candidate = first of [linked canonical entities, konum if settlement,
      communities worshipping me (newest first)] that is an agent type (AJAN_TURLERI) other than 'tur' and on my world;
      teknoloji → ogret(candidate, new, "{me} inspired"), else bond candidate → new (sahip/kutlar)
   olay effects: stat = clamp(old × (1 + pct/100), lo, hi); bond v:event → v:target 'neden_oldu' "{Label} {old} → {new}"
   firstLife = type ∈ {halk, yerlesim, olumlu} AND no other canonical halk/yerlesim/olumlu on that world
   me.oz −= myShare
   if toprakDar: me.oz = min(ozMax, oz + KESIF.toprak_oz); me.un += KESIF.toprak_un;
                 chronicle 'kesif': "{me} opened a new {type} for mortals squeezed into crowded lands: {name}."
   ctx.lvl = kazanc(me, yaratim_xp + power×yaratim_xp_guc + (firstLife ? BOS.ilk_halk_xp : 0), power + (firstLife ? BOS.ilk_halk_un : 0))
   if firstLife: me.oz = min(ozMax, oz + BOS.ilk_halk_oz);
                 chronicle 'yukselis': "{me} created the first people of the {world} world: {name}. They will be remembered as the god who breathed life into an empty world."
   save me
   if partner: partner.oz −= cost − myShare; partner.xp += ortak_xp + power×ortak_xp_guc; partner.un += ortak_un (no level-up processing);
               bond v:new → o:partner 'ilgili' "co-creator"; relation(me, partner) += ortak_iliski
AP: canliBedava → ctx.canliYaratim = true; elif toprakBedava → ctx.toprakYaratim = true; else ctx.ap −= 1
ctx.yaratimlar.push(id)
if arac and hedef_dunya_id: target world exists and != this world →
   method by keyword on lower("{alt_tur} {ad}") [LANGUAGE-SPECIFIC regex: köprü→bridge 'kopru'; kapı|halka|geçit→gate 'kapi'; binek|balina|kuş|solucan→mount 'binek'; else light-sail 'yelken']
   rid = seyahat.js rotaAc({a: thisWorld, b: target, yontem, arac_id: id, kuran_ogul: bridge ? me : null, kontrol_id: null, aciklama: "{me}'s {name}", cag})
   note " Route opened: route#{rid} ({world}, {method label})."
   NEW DESIGN: add an explicit `travel_method` enum field instead of keyword sniffing.
if dil and kelimeler: sozlukEkle(id, words[:kelime_adet], 'o', me, cag)
if teknoloji: ogret(o, id, cag, "{me} inspired") for each canonical ogrenen_ids
if iplik_id: UPDATE iplikler SET ilerleme = ilerleme+1 WHERE id AND durum='acik'   (thread id never goes into chronicle text)
chronicle 'yaratim': "{me}{ together with {partner}} created a {type}: {name}{ ({subtype}) if differs from type label}{, inside {konum}}.{ effect notes}" ids [id]
sound note: letters of the first word of the name not in dunyaAlfabesi(world) → " Note: the sounds {x, y} in its name do not exist in this world's languages; the name sounds foreign." (warning, not rejection)
```
Result: "Created: #{id} {name}. Cost {myShare} essence{ (the remaining {rest} paid by {partner})}{ (domain match)}{ (your power's discount)}{ (under the epoch's star)}{ (you repeated the same subtype: ×{repeatMul:.2f})}.{ You have no anchor yet; you can make this creation your anchor with choose_anchor.}{route note}{sound note}{thread note} {level note} {status}"

`fillStats(typeDef, given, power)` (exported; also used by mortal creations):
```
for [key,_,lo,hi] in typeDef.stat:
  given[key] != null → clamp(given, lo, hi)
  elif hi <= 100      → clamp(stat_taban + power × stat_guc, lo, hi)
  elif key == 'yas'   → varsayilan_yas
  elif key == 'omur'  → varsayilan_omur
  elif key == 'nufus' → clamp((type is People ? nufus_halk : nufus_diger) × power², lo, hi)
  elif key == 'murit' → clamp(murit_guc × power², lo, hi)
  else                → lo                 // e.g. species HP, vehicle crew
```
NOTE: `tdef.ad === 'Halk'` compares the Turkish display label — use the type key in the new design.

`olumluYasi(stats)` (exported): if `omur > 0`: `lo = min(yas_min, yas_max)`, `hi = max(...)`; `alt = round(omur×lo/100)`, `ust = max(alt, round(omur×hi/100))`; if given `yas` is not a finite number within [alt, ust], set `yas = alt + randInt(0..ust−alt)`.

#### 5.4 Influence tools (Distinguished+, gate `etkile`)

`ETKI_STATLARI` (stats a curse may hit) = refah, bereket, savunma, guc, savascilik, nufus, murit, bolluk, tehlike, servet, etki, kudret, can, karizma.

**40. `varligi_etkile` → `affect_entity`** (1 AP)
- Description: "You change the stats of an existing entity (enrich a city, make a species ferocious). Touching someone else's creation is twice as expensive and angers its creator. 1 action."
- Input: `varlik_id` int; `degisiklikler` array 1..`etkile_stat_adet` of `{ stat: string, yuzde: number ("between −{etkile_oran} and +{etkile_oran}") }`; `sebep` string 10–400.
- Validation: AP; kayitDurumu; "No such entity."; dunyaDisi; cost `= COSTS.etkile × (foreign creator ? etkile_yabanci_kat : 1) + entity.guc_seviyesi` → "Cost {n} essence; you have {oz}."; each stat must be in the type schema → "\"{stat}\" is invalid; available: {keys}." (validation happens inside the loop; earlier stats are already mutated in memory but nothing is saved on rejection).
- Effect: `y = clamp(pct, ±etkile_oran)`; if stat max ≤ 100: `new = old + y` (points) else `new = old × (1 + y/100)`; clamp to stat range; saveStat; me.oz −= cost; ap −= 1; if foreign creator: relation −= `etkile_iliski`; chronicle 'yaratim': "{me} passed their hand over {entity}: {Label old → new, …}. ({reason})". Result: "{entity} changed: {notes}.{ {creator} will not like this.} {status}"

**41. `secilmis_ilan_et` → `declare_chosen`** (1 AP; Ess `COSTS.secilmis` = 14)
- Description: "You declare a mortal your chosen one: their strength and charisma rise, they worship you, and your hand is with them in their heroic deeds. {14} essence, 1 action."
- Input: `olumlu_id` int; `lutuf` (boon) string 10–300 — "The grace, sign or burden you give them".
- Validation: AP; kayitDurumu; type `olumlu` → "This is not a living mortal."; dunyaDisi; tag 'seçilmiş' present → "{name} is already a god's chosen one."; essence.
- Effect: strength += `secilmis_guc`, charisma += `secilmis_karizma` (clamp 0–100), lifespan = clamp((omur || varsayilan_omur) + `secilmis_omur`, 1, 50000); add tag `seçilmiş` (chosen); deactivate ALL of the mortal's outgoing `tapar` bonds; bond v:mortal → o:me 'tapar' ("chosen"); bond o:me → v:mortal 'kutsadi' (boon); if mortal has another creator son: relation −= `secilmis_iliski`; me.oz −= 14; ap −= 1; chronicle 'yaratim': "{me} declared the mortal {name} their chosen one: {boon}". Result: "{name} is now your chosen one. {status}"

**42. `lanetle` → `curse`** (1 AP)
- Description: "You curse an entity: its stats fall and it rots a little more every epoch until the curse is lifted. Its creator is angered. {COSTS.lanet}+{lanet_guc}×power essence, 1 action."
- Input: `varlik_id` int; `lanet` string 10–400 — "The words and form of the curse".
- Validation: AP; kayitDurumu; "No such entity."; dunyaDisi; tag 'lanetli' → "{name} is already cursed."; cost.
- Effect:
  ```
  curser = gucVar(me,'lanetci')
  cost = round((COSTS.lanet + power × lanet_guc) × (curser ? lanetci_bedel/100 : 1))
  patron = hami(entity)
  resist = patron && patron != me ? patron.irade / lanet_direnc_bolen + (gucVar(patron,'dokunulmaz') ? lanet_dokunulmaz : 0) : 0
  sev = max(lanet_siddet_en_az, round((lanet_siddet_taban + me.kudret / lanet_kudret_bolen − resist / lanet_direnc_etki_bolen) × (curser ? lanetci_siddet/100 : 1)))
  for each type stat in ETKI_STATLARI present, except 'tehlike':
      new = (max ≤ 100) ? old − sev : old × (1 − sev/100); clamp
  save stats + tag 'lanetli' (cursed; the engine rots cursed entities each epoch)
  bond o:me → v:entity 'lanetledi' (curse text)
  relation(me, creator) −= lanet_yaratan_iliski   (if foreign creator)
  relation(me, patron)  −= lanet_hami_iliski      (if patron ≠ me and ≠ creator)
  me.oz −= cost; ap −= 1
  chronicle 'lanet': "{me} cursed {entity}: \"{curse}\" ({notes})"
  ```
  Result: "The curse took hold (severity {sev}). {notes}. {status}"

#### 5.5 Death and resurrection (`olum.js`)

**43. `can_al` → `take_life`** (1 AP; Limit `OLUM.can_al_tur`; Avail: gate `can_al` (Rare) and `OLUM.can_al_tur > 0`)
- Description: "You take the life of a named mortal. It is very expensive, and the more important the victim the costlier and harder: cost {can_al_taban} + {can_al_guc}×power level + importance/{can_al_onem_bolen} essence (+{can_al_onemli} if ruler, hero, chosen or titled). Success depends on dice (base {can_al_basari}%): a sibling patron, worshipping the creator, being protected or chosen, and importance protect them. If it fails the essence burns, the victim becomes a legend who returned from death, and their protector is angered with you. The dead one's creator and patron are also angered; what they ruled passes to their heir. 1 action, {once | N times} per epoch."
- Input: `varlik_id` int — "The named mortal whose life is taken"; `nasil` string 10–300 — "How you send death".
- Validation: AP; `ctx.canAl >= can_al_tur` → "You already tried to take a life this epoch (World rule OLUM.can_al_tur = {n})."; kayitDurumu; type `olumlu` → "Only a named, living mortal's life can be taken."; dunyaDisi; essence < cost → "{name}'s life needs {cost} essence; you have {oz}. An important mortal's life is not cheap."
- Effect: me.oz −= cost (saved first); ap −= 1; ctx.canAl++; `canAlmaDene(v, {kim: me, kimTip:'o', cag, nasil, not: chronicle 'olum'})`:
  ```
  cost   = round(can_al_taban + power × can_al_guc + importance / can_al_onem_bolen + (importantMortal ? can_al_onemli : 0))
  chance = clamp(can_al_basari + me.kudret/can_al_kudret_bolen − importance/can_al_onem_direnc
           − (living patron ≠ me and not creator-worshipper ? can_al_hami_direnc : 0)
           − (worships creator 't' ? can_al_yaratici_direnc : 0)
           − (tag 'korunmuş'|'seçilmiş' ? can_al_korunmus : 0), can_al_en_az, can_al_en_cok)
  immortal/ghost tag → fails ("{name} is immortal; death does not touch them.")
  success → olumluOlur(...) (death, heir inheritance, etc.); relation −can_al_iliski with victim's other creator and patron
  failure → survival story chosen from protectors (creator's hand / sibling patron / protective item with koruma ≥ can_al_esya_koruma / chosen / protected) else one of 5 random tales;
            victim charisma += can_al_karizma; tag 'ölümden dönen' (returned from death); new legend entity "{name}'s Return from Death"
            (power can_al_efsane_guc, prevalence can_al_karizma) bonded 'anlatir' to victim; relation −can_al_iliski with protecting patron
  ```
  On failure with `OLUM.can_al_iade > 0`: refund round(cost × iade%). Result: "{outcome text} (chance {pct}%, cost {cost} essence) {status}"

**44. `kardesini_dirilt` → `resurrect_sibling`** (1 AP; shared Limit `OLUM.kardes_tur`; Avail: `kardes_tur > 0` and at least one dead sibling at build time)
- Description: "You plot the return of a dead sibling: a rite ({kardes_ayin_bedel} essence, +{kardes_ayin_adanmislik} devotion), a descent into the realm of the dead ({kardes_inis_bedel} essence, +{kardes_inis_adanmislik}; succeeds {kardes_inis_basari}%, if it fails you fall asleep for {kardes_inis_uyku} epochs) or a bargain with an awake foreign god ({kardes_pazarlik_bedel} essence and one of your sibling's loyal communities passes to that god; +{kardes_pazarlik_adanmislik}). When devotion reaches {DERIN_YASAM.dirilis_adanmislik} the resurrection rite can succeed (at least {OLUM.dirilis_en_az_cag} epochs after death). 1 action, {once} per epoch."
- Input: `ogul_id` int — "The dead sibling's id"; `yol` (path) enum `ayin` rite | `inis` descent | `pazarlik` bargain.
- Validation: AP; `ctx.entrika >= kardes_tur` → "You already plotted a resurrection this epoch (World rule OLUM.kardes_tur = {n})."; errors thrown by `kardesEntrikasi` returned as rejections: "A resurrection plot is only made for a dead sibling." / "Only an awake sibling makes the plot." / "Invalid path: ayin | inis | pazarlik." / "{path} needs {cost} essence; {name} has {oz} (World rule OLUM.kardes_{path}_bedel)." / "There is no awake foreign god to bargain with."
- Effect (`kardesEntrikasi`): rite → devotion += ayin amount; descent → `kardes_inis_basari`% devotion += inis amount, else plotter `durum='uykuda'`, `uyku_kalan = kardes_inis_uyku`; bargain → first awake foreign god (same world first); the dead son's oldest worshipping community's 'tapar' moves to that foreign god ('y'); devotion += pazarlik amount. Cost deducted; devotion added to resurrection cults (`adanmislikEkle`); if devotion added: relation(plotter, dead) += kardes_ayin_adanmislik/2; chronicle 'dirilis': "{me} performed a {path} for their dead sibling {dead} ({cost} essence){extra}{; devotion N}." Then ap −= 1, ctx.entrika++. Result: "{text}{ Resurrection: devotion {d}/{needed}{, at the earliest in {k} epochs}.} {status}". (Note: no `uyudun()` suffix even though descent can put the son to sleep; the gate catches the next call.)

**45. `kemikleri_dagit` → `scatter_bones`** (1 AP; Ess `OLUM.dagit_bedel`; shared Limit `kardes_tur`)
- Description: "You scatter a dead sibling's bones: the devotion of those awaiting their return falls by {dagit_adanmislik}, the resurrection is delayed. Resurrection cults become your enemies. {dagit_bedel} essence, 1 action, {once} per epoch (shared with the resurrection plot)."
- Input: `ogul_id` int.
- Validation: AP; `ctx.entrika >= kardes_tur` → "You already plotted this epoch (World rule OLUM.kardes_tur = {n})."; thrown: "Only a dead god's bones are scattered." / "Only an awake sibling scatters bones." / "Scattering the bones needs {cost} essence; {name} has {oz}."
- Effect: cost; every resurrection cult (`dirilis:{id}` tag) devotion −= dagit_adanmislik (≥0); relation(me, dead) −= dagit_adanmislik/2; each such cult gets bond `dusman` → o:me ("scattered {dead}'s bones") if absent; chronicle 'dirilis': "{me} scattered {dead}'s bones ({cost} essence); resurrection rites lost {n} devotion." Then ap −= 1, entrika++.

#### 5.6 Miracle (Distinguished+, gate `mucize`)

**46. `mucize` → `miracle`** (1 AP)
- Description: "You send down a miracle upon the mortal world: {sifa (effect); bereket (effect); baris (effect); koruma (effect)}. An unclaimed community starts worshipping you. Cost: a share of the creator's miracle cost + power essence; 1 action."
  Miracle types (MUCIZELER): `sifa` Healing – "Population/followers +{sifa_artis}%, the curse lifts, a mortal's HP fills."; `bereket` Bounty – "Fertility +{bereket_bereket} or prosperity +{bereket_refah}."; `baris` Peace – "All of the target's enmities end."; `koruma` Protection – "Defense +{koruma_savunma}; protected from the next disaster."
- Input: `varlik_id` int; `tur` enum (above); `nasil` string 15–400 — "How the miracle manifests".
- Validation: AP; canonical (kayitDurumu); dunyaDisi; cost `OGUL_KOZMIK.mucize() + entity.guc_seviyesi` → "Cost {n} essence; you have {oz}."
- Effect: `mudahale.js mucizeUygula(v, type, cag)` (healing: nufus/murit × (100+sifa_artis)%, mortal HP ≥ sifa_can, removes 'lanetli'; bounty: fertility, else prosperity (refahEkle), else abundance; peace: deactivate all active `dusman` bonds touching it; protection: defense + tag 'korunmuş'; a resurrection cult target gets devotion + MUDAHALE.dirilis_adanmislik). Additionally for `sifa` with `sifa_sagduyu > 0`: target and every canonical entity located in it, of types halk/yerlesim/hizip/tarikat/olumlu, get `sagduyu` (sanity) = clamp((sagduyu ?? sagduyu_taban) + sifa_sagduyu); note "{X, Y and Z} came to their senses". If target is a community/mortal type without a patron: bond 'tapar' → me ("{Miracle} miracle"). Bond o:me → v:target 'kutsadi' ("{Miracle}: {how}"). me.oz −= cost; kazanc(mucize_xp, mucize_un); ap −= 1; chronicle 'mucize': "{me} sent down a {miracle} miracle upon {target}: {how}{ (notes)}". Result: "The miracle happened. {notes; sanity changes} {status}"

#### 5.7 Intrigue tools (Rare+, gate `nadir_araclar`)

**47. `ruya_gonder` → `send_dream`** (1 AP; Ess `COSTS.ruya` = 10)
- Description: "You send a dream to a cult, people, settlement, faction or mortal to make it worship you. If it worships someone else, success depends on your charisma against its patron's charisma. {10} essence, 1 action."
- Input: `hedef_id` int; `ruya` string 20–500 — "The dream's content".
- Validation: AP; kayitDurumu; type ∈ {tarikat, halk, yerlesim, hizip, olumlu} → "A dream can only be sent to thinking communities and mortals."; dunyaDisi; essence; current 'tapar' bond to a son = me → "{name} already worships you."
- Effect:
  ```
  old = first active tapar bond target→son (sons only)
  chance = clamp(ruya_taban + (me.karizma − (oldSon?.karizma ?? ruya_karizma_varsayilan)) / ruya_karizma_bolen
                 + (gucVar(me,'fisilti') ? ruya_fisilti : 0) − (target.bagnazlik ?? 0) / ruya_bagnaz_bolen, ruya_sans_min, ruya_sans_max)
  me.oz −= 10; ap −= 1; roll = d(100)
  roll <= chance: deactivate old bond; bond target → me 'tapar' ("turned by a dream"); relation(me, oldSon) −= ruya_iliski;
                  kazanc(ruya_xp, ruya_un); chronicle 'ruya': "{me} sent {target} a dream and turned it to themselves{; {old} lost a worshipper}. Dream: \"{dream}\""
                  result "You succeeded (roll {r} / chance {c}). {target} now worships you. {status}"
  else:           relation(me, oldSon) −= ruya_sezen_iliski; chronicle 'ruya': "{me} sent {target} a dream but the dream did not take hold{; {old} sensed it}."
                  result "The dream did not take hold (roll {r} / chance {c}). {status}"
  ```

**48. `afet_gonder` → `send_disaster`** (1 AP)
- Description: "You send a disaster upon a region, place or settlement: {deprem (effect); sel (…); veba (…); kuraklik (…); firtina (…)}. Those inside are affected too; it is recorded in the world as a lasting event. Cost: a share of the creator's disaster cost + {afet_guc}×power essence; 1 action."
  Disasters (AFETLER): `deprem` Earthquake – "Population −{deprem_nufus}%, monuments' sturdiness −{deprem_saglamlik} (those that collapse are destroyed)."; `sel` Flood – "Prosperity −{sel_refah}, population −{sel_nufus}%; then fertility +{sel_bereket}."; `veba` Plague – "Population −{veba_nufus}%, followers −{veba_murit}% ({tip_siddet}% for those who know medicine)."; `kuraklik` Drought – "Fertility −{kuraklik_bereket}, population −{kuraklik_nufus}% ({tarim_siddet}% for those who know agriculture)."; `firtina` Storm – "Defense −{firtina_savunma}, prosperity −{firtina_refah}."
- Input: `hedef_id` int; `tur` enum (above); `ad` string 2–60 — "The disaster's name in the world's language"; `aciklama` string 80–900; `sebep` string 10–300; `gorsel_prompt` string ≤900 opt — "English photoreal prompt of the disaster striking {GORSEL_YAZIM}".
- Validation: AP; kayitDurumu; type ∈ {bolge, yer, yerlesim} → "A disaster can only be sent upon a region, place or settlement."; dunyaDisi; `isimAlinmis(ad)` → "This name is taken."; cost `OGUL_KOZMIK.afet() + power × afet_guc`.
- Effect: `sev = clamp(afet_siddet_taban + me.kudret/afet_kudret_bolen + d(afet_zar), afet_siddet_min, 100)`; `notes = afetUygula(target, type, sev / afet_siddet_olcek)` (affects target and everything inside; 'korunmuş' entities consume their protection instead; knowledge halves; mortals may die/be wounded); `oid = olayKaydi({tur, hedef, cag, ad, aciklama, yaratan_id: me, kaynak: 'ogul', siddet: sev})` creates an `olay` entity (subtype = disaster label, power = clamp(round(sev / olay_guc_bolen), olay_guc_alt, olay_guc_ust), tags ['afet', type], bonds 'neden_oldu' to target and victims, 'icinde' location); set its `gorsel_prompt` (promptDuzelt) or NULL; `ctx.yaratimlar.push(oid)`; relation −afet_hami_iliski with target's patron (≠ me), −afet_yaratan_iliski with target's creator (≠ me); me.oz −= cost; ap −= 1; chronicle 'afet': "{me} sent a {disaster} upon {target}: {name}. ({reason}){ notes}" ids [target, event]. Result: "#{oid} {name} happened (severity {sev}). {notes} {status}"

**49. `bilgi_ver` → `teach_knowledge`** (1 AP)
- Description: "You teach an existing knowledge (technology) to a community or mortal; the knowledge spreads from them to their partners. If unclaimed it starts worshipping you. Cost: a share of the creator's knowledge cost; 1 action."
- Input: `hedef_id` int; `bilgi_id` int; `nasil` string 10–300.
- Validation: AP; kayitDurumu(target) || kayitDurumu(knowledge); target type ∈ {halk, yerlesim, hizip, tarikat, olumlu, tur} → "Knowledge is only given to thinking communities and mortals."; knowledge type `teknoloji` → "This is not a knowledge."; dunyaDisi(target); essence `OGUL_KOZMIK.bilgi()` → "Cost {n} essence; you do not have enough essence."; `ogret` returns false (already knows) → "{target} already knows this."
- Effect: `ogret(target, knowledge, cag, "{me}: {how}")` (bond 'bilir', knowledge prevalence += MUDAHALE.bilgi_yayginlik); if target has no patron: 'tapar' → me ("gift of knowledge"); me.oz −= cost; kazanc(bilgi_xp, bilgi_un); ap −= 1; chronicle 'bilgi': "{me} taught {target} the knowledge of {k}: {how}". Result: "{target} now knows {k}. {status}"

**50. `savas_kiskirt` → `incite_war`** (1 AP; Ess `COSTS.kiskirt` = 10)
- Description: "You sow the seed of enmity between two communities (faction, people or settlement). If it takes hold, war may break out between them; the world's flow resolves the war. {10} essence, 1 action."
- Input: `a_id` int; `b_id` int; `bahane` (pretext) string 10–400.
- Validation: AP; kayitDurumu a/b; both ∈ {hizip, halk, yerlesim} and distinct → "You must choose two separate factions/peoples/settlements."; dunyaDisi a/b; essence; already `dusman` either direction → "These are already enemies."; active truce (`derin.js ateskesVar`) → "There is an ongoing truce between them; incitement will not take hold."
- Effect: `chance = clamp(kiskirt_taban + me.kurnazlik / kiskirt_kurnaz_bolen, kiskirt_sans_min, kiskirt_sans_max)`; me.oz −= 10; ap −= 1; `roll = d(100)`; success → bond v:a → v:b 'dusman' (pretext); relation −kiskirt_iliski with each side's patron (≠ me); chronicle 'entrika': "{me} sowed hostility between {a} and {b}: {pretext}"; result "The seed took hold (roll {r}/{c}). {a} and {b} are now enemies. {status}". Failure → "The pretext was not found convincing (roll {r}/{c}). {status}" (no chronicle).

#### 5.8 Legendary tools (gate `efsanevi_araclar`)

**51. `donustur` → `transform`** (1 AP; Ess 15 + `donustur_guc`×power)
- Description: "You transform an existing entity into something else: its name, nature and description change, its history remains. {15}+{2}×power essence, 1 action."
- Input: `varlik_id` int; `yeni_ad` string 2–60 opt; `yeni_alt_tur` string ≤40 opt; `yeni_aciklama` string 120–1400 (required); `sebep` string 10–400.
- Validation: AP; kayitDurumu; "No such entity."; dunyaDisi; new name differs and taken → "This name is taken."; cost.
- Effect: if new name differs: `world.js adDegistir(id, newName)` (rename propagates into all texts: chronicle, bonds, depth, threads, beliefs…); `alt_tur = altTurDuzelt(new) or old`; `aciklama = "{new description}\n\n(Transformed in Epoch {n} by {me}. Previous form: {oldName}: {old description[:300]})"`; bond o:me → v:entity 'lanetledi' ("transformed: {reason}"); relation −donustur_iliski with a foreign creator; me.oz −= cost; ap −= 1; chronicle 'yaratim': "{me} transformed {oldName}{; its name is now {new}}. ({reason})". Result: "Transformation complete. {status}"

**52. `yok_et` → `destroy`** (1 AP; Ess 25 + `yok_et_guc`×power)
- Description: "You erase an entity from the world. What is inside it falls to the location above. {25}+{3}×power essence, 1 action. It deeply wounds its creator."
- Input: `varlik_id` int; `sebep` string 10–400.
- Validation: AP; kayitDurumu; "No such entity."; dunyaDisi; `kaynak == 'tanri'` → "You cannot destroy what the god made with his own hand."; cost.
- Effect (transaction): `durum='yok_edildi', olum_cag=cag, kader_notu="Epoch {n}: {me} destroyed it — {reason}"`; deactivate all bonds touching it; `icindekileriDevret(id, konum_id, cag)` (contents move up one location); bond o:me → v:entity 'yok_etti' (reason); me.oz −= cost. Then relation −yok_et_iliski with foreign creator; ap −= 1; chronicle 'yaratim': "{me} destroyed {name}. ({reason})". Result: "{name} is no more. {status}"

**53. `evlat_dogur` → `birth_child`** (async; AP `evlat_dogur_ap`; Ess `COSTS.evlat_dogur` = 60)
- Description: "You birth a new son from your own essence; a new card joins the pantheon. Its rarity is lower than yours. {60} essence, {2} actions."
- Input: `ilham` string 20–600 — "Why and from what the child is born, which domains it will carry"; `diger_ebeveyn_id` int opt — "Optional: the sibling you birth together with".
- Validation: `ctx.bekleyenIs` set or `SUREN.has(son)` → pending message (below); `checkAP(evlat_dogur_ap)`; essence; co-parent given but missing/self/dead → "Invalid co-parent: it must be another living sibling."
- Effect: me.oz −= 60 (saved), ap −= 2, `bekleyenYaz("evlat_dogur:60:2:{cag}")`; then `surdur(son, async ...)`: `child = await ctx.dogur(me, inspiration, coParent)` (agents.js: rolls a rarity strictly lower than the parent's and runs the summoning LLM call; bonds 'soyundan', relations, chronicle 'dogum'); clear flag; `isIzi('evlat_dogur', 'oğul#{id}', text)`; result "A child was born: son#{id} {name}, {title} ({Rarity}). {status}". On exception: refund 60 essence and 2 AP, clear flag, reject "The birth failed: {message}".
- Pending message (`surenMetni`): "A {child birth | world birth | birth} is already in progress (your previous call is still being processed; its cost was deducted once). Do not call it a second time: when it completes the result will be visible in the world. Move to another action or speak your word."

#### 5.9 Cosmic tools

**54. `dunyaya_yonel` → `move_to_world`** (free; Avail: ≥2 worlds and `dunya.ogul_dagitim` ('son distribution') is `'otomatik'` (default) – when the player distributes sons manually the tool is absent)
- Description: "You turn to another world of the cosmos: from now on your creations and inspections happen there. Free."
- Input: `dunya_id` int — "The id of the world you go to (from the OTHER WORLDS OF THE COSMOS list)".
- Validation: missing → "No such world."; `kesif == 'bilinmeyen'` (unknown) → "{world} is a world nobody knows yet; someone must first find the road there."; `kesif == 'unutulmus'` (forgotten) → "{world} was forgotten; nobody can turn to a world buried in mist."; same world → "You are already on {world}."; sole god: no other active son on the current world AND the current world has a canonical halk/yerlesim → "You are the only god on {world}; you cannot leave it godless. First a sibling must turn there."
- Effect: `ogullar.aktif_dunya = target`; chronicle 'kozmik': "{me} turned from {old} to {new}." Result: "You are now on {world}. See this world's map and inhabitants with world_summary. {status}" (The new server's snapshot fields — star discount, alphabet — still refer to build time.)

**55. `kutsal_dunya_ilan` → `declare_holy_world`** (free; Limit `kutsal_dunya_tur`)
- Description: "You declare a world your holy world: in that world your name is invoked first. If it is another sibling's world, your relationship sours. Free, once per epoch."
- Input: `dunya_id` int.
- Validation: limit → "You already declared a world this epoch (World rule OGUL_ARAC.kutsal_dunya_tur = {n})."; unknown world → "{world} is a world nobody knows yet; you cannot declare a world you do not know holy."; forgotten → "{world} was forgotten; a world buried in mist cannot be anyone's holy place."; thrown "No such world."
- Effect (`panteon.js kutsalDunyaIlan` under `ogulunEli`): if world had another living protector son: relation −PANTEON.kutsal_dunya_iliski; `dunyalar.koruyucu_ogul = me, koruyucu_oto = 0`; chronicle 'kozmik': "{me} declared {world} their holy world{; trampling {old}'s claim}." ctx.kutsalDunya++. Result: "This world is now your holy world. {status}"

**56. `kapi_muhurle` → `seal_gate`** (1 AP; Ess `OGUL_KOZMIK.muhur()`)
- Description: "You seal a road between worlds (gate, dream passage, route): what leaks through that road stops, the two worlds' leakage decreases; but trade and migration coming by that road are cut too. {cost} essence, 1 action."
- Input: `rota_id` int; `neden` string 10–300.
- Validation: AP; essence → "Cost {n} essence."; thrown "There is no such open route."
- Effect (`kapiMuhurle`): route `aktif=0`; both worlds' `sizinti` (leakage) −= PANTEON.muhur_sizinti (≥0); the route's vehicle entity (if any) → `durum='olu'` ("Epoch n: {me} sealed it."); chronicle 'kozmik' (attributed to son): "{me} sealed the road between {A} and {B}; the two worlds' leakage decreased." me.oz −= cost; ap −= 1. Result: "The road is sealed ({reason}). {status}"

**57. `yildiz_tutustur` → `rekindle_star`** (AP `tutustur_ap`; Ess `OGUL_KOZMIK.tutustur()`; Avail: Epic and a star of type 'ölü yıldız' (dead star) / 'kara güneş' (black sun) / 'yıldız kalıntısı' (stellar remnant) exists)
- Description: "You rekindle a dead, darkened or exploded star: light returns to the worlds around it, leakage recedes. {cost} essence, {2} actions."
- Input: `yildiz_id` int.
- Validation: AP; essence; thrown "No such star." / "{star} is already burning."
- Effect (`oyuncu.js yildizTutustur`): star `tur='yeniden doğmuş yıldız'` (reborn star), brightness = TE.tutustur_parlaklik; its worlds' leakage −= TE.tutustur_sizinti; chronicle 'gok': "{me} rekindled {star}; light returned to the worlds sunk in darkness." me.oz −= cost; me.un += tutustur_un; ap −= 2. Result: "The star burns again. {status}"

**58. `ruh_kapla` → `bind_spirit`** (1 AP; Ess `OGUL_KOZMIK.ruh()`; Avail: Distinguished and a canonical `ruh` entity exists)
- Description: "You bind a free spirit to an item, ship or monument; if you bind it to a monument a golem is born. {cost} essence, 1 action."
- Input: `ruh_id` int; `hedef_id` int.
- Validation: AP; essence; spirit given but not canonical: if it is a spirit → "There is no such free spirit: #{id} {name} is no longer free (it was bound to something or faded)." else kayitDurumu / "There is no such free spirit."; not type ruh → "There is no such free spirit."; target missing → "#{id} does not exist."; target not canonical → "{reason} The spirit cannot be bound to it."; both on son's world; thrown "The spirit can only be bound to an item, vehicle or monument."
- Effect (`otesi.js ruhKapla` under `ogulunEli`, `kim = {ad}`): spirit killed ("bound to {target}") with bonds; bond spirit → target 'icinde'; target monument → new `tur` entity subtype 'golem' "{monument} Golem" (power max(OTESI.golem_seviye, monument power), stats from OTESI golem rules, tags ['golem','ozellik:tas_derili']) and the tool adds bond o:me → v:golem 'evcil' ("own golem"); otherwise target potency += OTESI.ruh_kudret (vehicles also strangeness += OTESI.ruh_tuhaflik) and tag 'ruhlu'. Chronicle 'ruh': "{me} bound {spirit} to {target}{; the stone began to walk}." me.oz −= cost; ap −= 1. Result: "The spirit is bound. {status}"

**59. `yildiz_as` → `hang_star`** (AP `yildiz_as_ap`; Ess `OGUL_KOZMIK.yildiz_as()`; Mythic)
- Description: "You hang a new star in the sky; new worlds may be born around it. {cost} essence, {2} actions."
- Input: `ad` string 2–60; `tur` string ≤40 opt — "yellow dwarf, red giant, blue giant, binary star, white dwarf…"; `aciklama` string 20–400.
- Validation: AP; essence; `isimAlinmis(ad)` → "This name is taken."
- Effect: me.oz −= cost; ap −= 2; `panteon.js yildizAs({ad, tur: tur || 'sarı cüce' (yellow dwarf), kim: me.name, cag, aciklama})` → inserts `yildizlar` row (unique name, brightness PANTEON.yildiz_parlaklik + d(yildiz_parlaklik_zar), placed at random angle, radius 260 + 140×starCount); chronicle 'kozmik': "{me} hung a new star in the sky: {name} ({type})." Result: "New star: star#{id} {name}. {status}"

**60. `yildiz_sondur` → `extinguish_star`** (AP `sondur_ap`; Ess `OGUL_KOZMIK.yildiz_sondur()`; Mythic)
- Description: "You extinguish a star: the worlds around it sink into darkness and cold, leakage rises, the apocalypse draws near. A terrible act; the whole cosmos remembers it. {cost} essence, {2} actions."
- Input: `yildiz_id` int; `neden` string 15–400.
- Validation: AP; already a dead-star type → "{star} is already extinguished."; essence; thrown "No such star."
- Effect (`yildizSondur`): star → 'ölü yıldız', brightness PANTEON.olu_yildiz_parlaklik; each orbiting world leakage += sondurme_sizinti (≤100) and every region's fertility −= sondurme_bereket; `dunya.kiyamet` (apocalypse clock) += PANTEON.sondurme_kiyamet (≤ DENGE.kiyamet_esik); chronicle 'kozmik': "{me} extinguished {star}. {worlds} sank into darkness; the lands grew cold, the things outside drew closer." me.oz −= cost; me.un += sondur_un; ap −= 2; relation −sondur_iliski with EVERY other son (including dead). Result: "The star went out ({reason}). Your siblings will remember you with fear. {status}"

**61. `yabanci_tanriyla_konus` → `talk_to_foreign_god`** (1 AP)
- Description: "You speak with the old or foreign god of another world: alliance, threat or bargain. The outcome depends on your charisma, their attitude and their power. 1 action."
- Input: `tanri_id` int; `niyet` enum `ittifak` alliance | `tehdit` threat | `pazarlik` bargain; `soz` string 10–400.
- Validation: AP; foreign god with `temas=1` → "There is no such known foreign god."; not 'uyanik' (awake) → "{god} cannot speak now ({state})."; reach: son's world == god's world OR active known route (no alignment check) → "Your voice does not reach {god}'s world: you are not in that world and there is no known open road between you. Turn there first or let a road open."
- Effect: ap −= 1;
  ```
  roll = d(100) + me.karizma / yk_karizma_bolen
       + (threat ? (me.guc − god.guc) / yk_guc_bolen : god.tutum / yk_tutum_bolen)
       − ytEtki(god, 'irade', YABANCI.konusma_irade)          // (god.irade − stat_notr) × konusma_irade / 100
       − (god has power 'sozu_keskin' (sharp-tongued) ? YABANCI.guc_soz : 0)
  alliance: roll ≥ yk_ittifak_esik → attitude += yk_ittifak_tutum ("{god} extended a hand") else −yk_ret_tutum ("{god} did not trust")
  threat:   roll ≥ yk_tehdit_esik  → attitude −= yk_tehdit_tutum, god.guc −= yk_tehdit_guc (≥0) ("{god} withdrew but will hold a grudge")
            else attitude −= yk_tehdit_ofke ("{god} answered the threat with fury")
  bargain:  roll ≥ yk_pazarlik_esik → attitude += yk_pazarlik_tutum, me.oz = min(ozMax, oz + yabanci_pazarlik) ("you came to terms with {god}; you gained {n} essence")
            else −yk_ret_tutum ("{god} refused the bargain")
  attitude clamped −100..100
  chronicle 'yabanci_tanri': "{me} spoke with the foreign god {god} {in alliance | with a threat | in bargaining}: \"{words}\" — {outcome}."
  ```
  Result: "{outcome}. {status}"

**62. `antlasma_yap` → `make_interworld_treaty`** (AP `antlasma_ap`; Ess `antlasma_oz`)
- Description: "You establish an interworld treaty between two communities in separate worlds: alliance (muttefik) or trade. There must be a known, open road between the two worlds and one of the communities must be on the world you are currently on; enemies do not make treaties. {20} essence, {1} action."
- Input: `a_id` int — "The community on the world you are on"; `b_id` int — "The community on the other world"; `tur` enum `muttefik` ("alliance: side by side in war") | `ticaret` ("trade: goods and prosperity flow"); `sart` string 10–300 — "The treaty's condition, its oath".
- Validation: AP; kayitDurumu a/b; both ∈ {halk, yerlesim, hizip, tarikat} and distinct → "You must choose two separate communities (people, settlement, faction or cult)."; same world → "{a} and {b} are in the same world; this tool is for interworld treaties."; neither on son's world → "One of the communities must be on the world you are on (world#{n}); your hand does not reach two foreign worlds at once."; `yolAcik(a, b)` (a known route with `rotaAcikMi` true – slingshot routes only when aligned) → "There is no known, open road between world#{a} and world#{b}; the treaty's word does not reach the other side."; enemies → "{a} and {b} are enemies; peace must come first."; same bond exists → "There is already {an alliance | trade} between {a} and {b}."; essence.
- Effect: bond v:a → v:b `{tur}` ("interworld treaty ({me}): {terms}"); `derin.js tIliskiDegistir(a, b, antlasma_iliski, 'interworld treaty', cag)` (community relation); me.oz −= 20; ap −= 1; chronicle 'diplomasi': "{me} established an interworld {alliance | trade} treaty between {a} in the {A} world and {b} in the {B} world: {terms}". Result: "Treaty made: {a} ⇄ {b} ({label}). {status}"

**63. `sizinti_dik` → `seal_leak`** (AP `sizinti_ap`; Ess `sizinti_oz`; Limit `sizinti_dik_tur`)
- Description: "You stitch the tears of the world you are on: the intensity of what leaks in from outside (leakage) decreases. Once per epoch. {35} essence, {1} action."
- Input: `nasil` string 10–300 — "With what and how you stitch the tear".
- Validation: AP; limit → "You already stitched a tear this epoch (World rule OGUL_ARAC.sizinti_dik_tur = {n})."; world missing → "The world you are on is not registered."; `sizinti <= 0` → "There is no tear to stitch on {world} (leakage 0)."; essence.
- Effect: `new = max(0, sizinti − sizinti_azalis)`; update world; me.oz −= 35; ap −= 1; ctx.sizintiDikildi++; chronicle 'kozmik': "{me} stitched the tear of the {world} world ({how}); leakage {old} → {new}." Result: "Leakage {old} → {new}. {status}"

**64. `yatak_ac` → `open_cosmic_bed`** (AP `yatak_ap`; Ess `yatak_oz`)
- Description: "On the world you are on, you open a bed of the cosmic travel resource in a region or place: mortals can claim it and travel between worlds. The cosmos's travel resource must be defined. {60} essence, {2} actions."
- Input: `bolge_id` int — "The region or place where the bed opens"; `neden` string 10–300.
- Validation: AP; kayitDurumu; type ∈ {bolge, yer} → "A bed opens only in a region or a place."; dunyaDisi; `dunya.kozmik_kaynak` missing → "The cosmos has no travel resource; the bed cannot be opened until your father defines it."; already a canonical 'kaynak' with tag 'kozmik kaynak' located there → "There is already a cosmic bed in {name}."; essence; thrown errors from `kozmikYatakAc`.
- Effect: `oyuncu.js kozmikYatakAc(regionId)` inserts a resource "{resource name} Bed ({region})" subtype 'kozmik seyahat kaynağı' (cosmic travel resource) with stats from TE.yatak_*, tags ['kozmik kaynak','mekanik:bagimlilik','mekanik:sabit'], bond 'icinde'; the tool then sets `yaratan_id = me, kaynak = 'ogul'` (so the son can harvest it) and rewrites the creator-attributed chronicle rows written by it (`tur='tanri'`, `ogul_id IS NULL`, id > before) to `ogul_id = me, tur='kozmik', metin = "{me} opened a {bed} in {region}: {reason}"`. me.oz −= 60; ap −= 2; `ctx.yaratimlar.push(bed)`. Result: "Bed opened: #{id} {name}. {status}"

**65. `yabanci_tanriyla_savas` → `war_on_foreign_god`** (AP `ysavas_ap`; Ess `ysavas_oz`)
- Description: "You declare war on the old or foreign god of another world. Your strength, your will and your rank clash with their power. If you win they fall defeated (in a crushing victory they die), you gain fame and experience; if you lose you are wounded and lose essence. You must be in that world or there must be a known open road between you. {30} essence, {2} actions."
- Input: `tanri_id` int; `sebep` string 10–400.
- Validation: AP; known god → "There is no such known foreign god."; not awake → "{god} cannot fight now ({state})."; `yolAcik(myWorld, godWorld)` → "Your hand does not reach {god}'s world: you are not in that world and there is no known open road between you. Turn there first or let a road open."; essence.
- Effect:
  ```
  me.oz −= 30; ap −= 2
  p1 = round((me.guc + me.irade) / ysavas_stat_bolen + me.seviye × ysavas_seviye + d(ysavas_zar))
  p2 = round(ytSavasGucu(god) + d(ysavas_zar))      // god.guc×(100−savas_stat_pay)% + (stat guc + stat irade)/2 × savas_stat_pay% + (kalkan power ? guc_kalkan : 0)
  diff = |p1 − p2|
  p1 >= p2: state = (diff >= ysavas_ezici AND god lacks power 'olumsuz' (deathless)) ? 'olu' : 'yenik'
            god: durum=state, guc −= ysavas_guc_kayip (≥0), tutum −= ysavas_tutum (≥−100), yenilgi_cag / olum_cag set
            bond o:me → y:god ('oldurdu' killed | 'dovdu' defeated, reason); lvl = kazanc(ysavas_xp, ysavas_un)
            text "{me} declared war on the foreign god {god} (\"{reason}\") and {killed | defeated} them ({p1}–{p2})."
  else:     wound = ysavas_yara + diff; loss = min(ysavas_oz_kayip, me.oz); me.can −= wound; me.oz −= loss; god.tutum −= ysavas_tutum
            if me.can <= 0: can 0, asleep for (reborn ? dirilis_uyku : ysavas_uyku) epochs
            text "{me} declared war on the foreign god {god} (\"{reason}\") but was defeated ({p1}–{p2}); lost {wound} HP and {loss} essence.{ collapsed… sleep N epochs}"
  save me; chronicle 'yabanci_tanri': text
  ```
  Result: "{text} {level note} {status}{uyudun()}"

**66. `dis_varlikla_pazarlik` → `bargain_with_outsider`** (free; Limit `dis_pazarlik_tur`; Avail: a canonical `dis` entity exists anywhere)
- Description: "FORBIDDEN: you bargain with the nameless thing that came from outside the cosmos. You gain great essence; but leakage rises, your siblings are disgusted by you, your loyalty to your father unravels and one day the price is demanded. Does not spend an action."
- Input: `dis_id` int; `istek` (request) string 10–300.
- Validation: limit → "Once is enough: you have bargained enough this epoch (World rule OGUL_ARAC.dis_pazarlik_tur = {n})."; thrown "No such thing. Or there is, and you cannot see it."
- Effect (`panteon.js disVarliklaPazarlik` under `ogulunEli`): `gain = PANTEON.pazarlik_oz + round((outsider.etki || dis_etki_varsayilan) / pazarlik_etki_bolen)`; `son.oz += gain` (NOT capped at ozMax); ambition += pazarlik_hirs; loyalty −= pazarlik_sadakat; that world's leakage += pazarlik_sizinti (≤100); relation −pazarlik_iliski with every living sibling; tag the outsider `pazarlik:{sonId}`; insert an open thread (iplik): "{son} bargained with the thing outside ({request}). Nobody knows what they gave in return; but one day it will be paid."; chronicle 'yasak' (forbidden): "{son} bargained with the nameless thing. Their siblings saw another shadow over them." ctx.disPazarlik++. Result: "Bargain struck: {gain} essence. The price will come later. {status}"
- Note: this tool does not check `dunyaDisi` – a son can bargain with an outsider on any world.

**67. `dunya_dogur` → `birth_world`** (async; AP `dunya_dogur_ap`; Ess `DENGE.dunya_dogur` = 70)
- Description: "You birth a new world into the cosmos: with its own sky, physics, regions, unique resource and perhaps natives. The world reflects your domains and you turn to it. {70} essence, {2} actions.\nEXISTING STARS (the new world usually orbits one of these; choose with yildiz_id):\n{yildizSatirlari() or 'none'}" (star list rendered at server build time by `kozmos.js yildizSatirlari`).
- Input: `ilham` string 20–600 — "Why and from what this world is born"; `tur` optional enum world types — "World type: olagan (Ordinary world), okyanus (Ocean world), kum (Sand world), buz (Ice world), lav (Lava world), kristal (Crystal world), yasayan (Living planet), olu (Realm of the dead), ruya (Dream realm), ayna (Mirror world), gaz (Gas giant)"; `yildiz_id` int opt — "The existing star it will orbit (from the list)"; `ana_dunya_id` int opt — "If it will be a moon of a world, that world's id"; `yeni_yildiz` boolean opt — "Only if no star in the list fits this world's light: a distant system with its own new sun".
- Validation: pending job → pending message; `checkAP(2)`; star missing → "There is no such star (star#{id})."; parent world missing → "There is no such world (world#{id})."; more than one of the three location options → "Choose only one place: yildiz_id, ana_dunya_id or yeni_yildiz."; essence.
- Effect: me.oz −= 70; ap −= 2; `bekleyenYaz("dunya_dogur:70:2:{cag}")`; `surdur(...)`: `dw = await kozmos.js dunyaDogur({ tur, ilham, yaratan: son, konum: { yildiz_id, ana_dunya_id, yeni_yildiz } })` (an LLM call that designs the world — prompt documented with kozmos.js; it sets the son's `aktif_dunya` to the new world and bonds the son 'korur' (protects) to its first region); clear flag; `kazanc(dunya_dogur_xp, dunya_dogur_un)`; `isIzi('dunya_dogur', 'dünya#{id}', text)`; result "A new world was born: world#{id} {name} ({type label}). You are there now. {status}". On exception: refund 70 essence and 2 AP, clear flag, reject "The world could not be born: {message}".

### 6. Other exported helpers in `tools.js`

| export | purpose |
|---|---|
| `atomik(fn)` | run `fn` in the open transaction or a new one (node:sqlite cannot nest BEGIN) |
| `kimlikTemizle(v)` | id/number sanitizer (§4) |
| `sayi()` | zod number with friendly errors (§4) |
| `aracAlanlari(shape)` | apply sanitizer preprocessors to a zod shape (also used by `olumluler.js`) |
| `durumNedeni(v)`, `kayitDurumu(id)`, `kanonDisi(...)` | entity-state rejection reasons (§4) |
| `altTurDuzelt(sub, type)` | subtype normalization (§4) |
| `BEDAVA_RE`, `bedavaMi(desc)` | free-tool detection from description text |
| `ANLATI_BAGLARI` | re-export of narrative bond list |
| `OGUL_K` | the OGUL_ARAC tunables object |
| `OGUL_KOZMIK` | derived son cosmic/intervention costs (§3) |
| `olumluYasi(stats)` | clamp a new mortal's age into its lifespan window (§5.3) |
| `gokTakvimi(cag)` | sky calendar text for prompts: `P = max(1, SEYAHAT.hizalanma_donemi)`, `left = (P − cag mod P) mod P`; if 0 → "the planets are aligned this epoch; slingshot orbits are open now (Epoch {cag}), then they open again in Epoch {cag+P}" else "slingshot orbits open in Epoch {cag+left} ({left} epochs from now; the planets align every {P} epochs)". Used in son/mortal prompts. |
| `surenIs(sonId)` | running long-job promise or null (§2) |
| `kazanc(son, xp, fame, cag)` | XP/fame gain with level-ups and power awakening (§3) |
| `meydanOkuma(me, k, stat, reason, cag)` | sibling duel resolution (tool 12; also panteon.js engine rival clashes) |
| `fillStats(typeDef, given, power)` | default stats for created entities (§5.3; also mortals) |
| `KelimeSchema` | dictionary word array schema (§4) |
| `buildSonServer(sonId, ctx)` | the server builder (§1) |
| `getWorld` | re-export |

Cross-module wiring (actual imports of tools.js): `agents.js` (buildSonServer, fillStats, gokTakvimi, surenIs, OGUL_K, altTurDuzelt); `olumluler.js` (KelimeSchema, fillStats, atomik, bedavaMi, olumluYasi, sayi, kayitDurumu, kanonDisi, altTurDuzelt, aracAlanlari); `panteon.js` (OGUL_K, meydanOkuma – engine rival duels); `etiket-onar.js` (altTurDuzelt). `kazanc` and `durumNedeni` are exported but only used inside tools.js (durumNedeni via kayitDurumu/kanonDisi). `llm.js araclariSar` wraps the tools; `defter.js` installs the ledger runner via `defterBagla`. `dunyaDogur` (kozmos.js) sets the creator son's `aktif_dunya` to the new world and adds a `korur` bond to its first region.

### 7. Tunables defined in `tools.js` (namespace `OGUL_ARAC`, four `tanimla` blocks merged into `OGUL_K`)

Groups: "Son tools" (Oğul araçları) unless noted; LN = "Language and names" (Dil ve adlar); MO = "Mortals" (Ölümlüler); PG = "Population and growth" (Nüfus ve büyüme); RL = "Religion and language" (Din ve dil); CR = "Creatures" (Yaratıklar); CB = "Context budgets" (Bağlam bütçeleri). (`tools.js` also calls `tanimla('DERIN_YASAM', {})` only to obtain a live reference to that namespace; it defines nothing.)

| English key | TR key | default | min | max | group | English label |
|---|---|---|---|---|---|---|
| anchor_changes_per_epoch | capa_tur | 1 | 0 | 20 | Son tools | Max times a son can change its anchor in one epoch |
| gifts_per_epoch | armagan_tur | 1 | 0 | 20 | Son tools | Max gifts a son can give in one epoch |
| prayers_per_epoch | dua_tur | 1 | 0 | 20 | Son tools | Max prayers to the father in one epoch |
| holy_world_declarations_per_epoch | kutsal_dunya_tur | 1 | 0 | 20 | Son tools | Max holy-world declarations in one epoch |
| leak_stitches_per_epoch | sizinti_dik_tur | 1 | 0 | 20 | Son tools | Max tears a son can stitch in one epoch |
| first_living_creation_free | canli_bedava | 1 | 0 | 1 | Son tools | The epoch's first living creation spends no action (1 on, 0 off) |
| make_bond_cost | bag_bedel | 2 | 0 | 100 | Son tools | make_bond cost (essence) |
| make_bonds_per_epoch | bag_tavan | 3 | 0 | 50 | Son tools | make_bond calls per epoch |
| coin_words_calls_per_epoch | kelime_tur | 2 | 0 | 20 | LN | coin_words calls per epoch |
| coin_words_max_per_call | kelime_adet | 8 | 1 | 40 | LN | Max words in one coin_words call |
| sibling_messages_per_epoch | mesaj_tavan | 2 | 0 | 20 | Son tools | Words to siblings per epoch |
| covenant_min_relation | ahit_esik | 25 | −100 | 100 | Son tools | Minimum relation needed for a covenant |
| covenant_relation_bonus | ahit_bonus | 15 | 0 | 100 | Son tools | Covenant's contribution to the relation |
| gift_max_essence | armagan_oz | 40 | 0 | 1000 | Son tools | Max essence in a single gift |
| challenge_min_wound | meydan_yara | 8 | 0 | 200 | Son tools | Minimum wound of the challenge loser |
| challenge_max_essence_stolen | meydan_calinti | 10 | 0 | 200 | Son tools | Max essence the challenge winner snatches |
| challenge_win_xp | meydan_xp | 25 | 0 | 500 | Son tools | XP of the challenge winner |
| challenge_win_fame | meydan_un | 5 | 0 | 200 | Son tools | Fame of the challenge winner |
| covenant_break_fame_cost | ahit_bozma_un | 10 | 0 | 200 | Son tools | Fame cost of challenging a covenanted sibling |
| rebel_max_loyalty | isyan_sadakat | 40 | 0 | 100 | Son tools | Rebellion allowed below this loyalty |
| harvest_abundance_loss | sag_bolluk | 8 | 0 | 100 | Son tools | Abundance lost when a resource is harvested |
| harvest_depleted_below | sag_tukenme | 5 | 0 | 100 | Son tools | Below this abundance the resource counts as exhausted |
| repeat_cost_increase_pct | tekrar_artis | 25 | 0 | 500 | Son tools | Cost increase per new creation of the same subtype (%) |
| repeat_cost_cap_pct | tekrar_tavan | 250 | 100 | 1000 | Son tools | Cap of the repetition multiplier (%) |
| repeat_window_epochs | tekrar_pencere | 6 | 1 | 100 | Son tools | Epochs over which repetition is counted |
| affect_max_change_pct | etkile_oran | 30 | 1 | 100 | Son tools | Max stat change with affect_entity (%) |
| intervention_cost_pct | mudahale_oran | 70 | 0 | 500 | Son tools | Son's miracle/disaster/knowledge cost as % of the creator's intervention cost |
| seal_gate_cost_pct | kozmik_muhur | 70 | 0 | 500 | Son tools | Gate-sealing cost, % of the creator's |
| rekindle_star_cost_pct | kozmik_tutustur | 85 | 0 | 500 | Son tools | Star-rekindling cost, % of the creator's |
| bind_spirit_cost_pct | kozmik_ruh | 80 | 0 | 500 | Son tools | Spirit-binding cost, % of the creator's |
| hang_star_cost_pct | kozmik_yildiz | 75 | 0 | 500 | Son tools | Star-hanging cost, % of the creator's |
| extinguish_star_cost_pct | kozmik_sondur | 100 | 0 | 500 | Son tools | Star-extinguishing cost, % of the creator's star cost |
| foreign_bargain_essence | yabanci_pazarlik | 15 | 0 | 500 | Son tools | Essence from a successful bargain with a foreign god |
| birth_world_xp | dunya_dogur_xp | 60 | 0 | 1000 | Son tools | XP of a son who births a world |
| birth_world_fame | dunya_dogur_un | 15 | 0 | 500 | Son tools | Fame of a son who births a world |
| treaty_cost | antlasma_oz | 20 | 0 | 500 | Son tools | make_interworld_treaty cost (essence) |
| treaty_ap | antlasma_ap | 1 | 1 | 5 | Son tools | make_interworld_treaty action cost |
| treaty_relation | antlasma_iliski | 15 | 0 | 100 | Son tools | Interworld treaty's contribution to the two communities' relation |
| seal_leak_cost | sizinti_oz | 35 | 0 | 500 | Son tools | seal_leak cost (essence) |
| seal_leak_ap | sizinti_ap | 1 | 1 | 5 | Son tools | seal_leak action cost |
| seal_leak_reduction | sizinti_azalis | 25 | 1 | 100 | Son tools | Leakage reduction from seal_leak |
| cosmic_bed_cost | yatak_oz | 60 | 0 | 1000 | Son tools | open_cosmic_bed cost (essence) |
| cosmic_bed_ap | yatak_ap | 2 | 1 | 5 | Son tools | open_cosmic_bed action cost |
| location_suggestions | konum_oneri | 5 | 0 | 50 | Son tools | Locations suggested on a missing-location error |
| foreign_war_cost | ysavas_oz | 30 | 0 | 500 | Son tools | war_on_foreign_god: cost of entering the war (essence) |
| foreign_war_ap | ysavas_ap | 2 | 1 | 5 | Son tools | war_on_foreign_god action cost |
| foreign_war_die | ysavas_zar | 40 | 1 | 200 | Son tools | Die faces for both sides in a foreign-god war |
| foreign_war_level_power | ysavas_seviye | 3 | 0 | 50 | Son tools | Son's power per level in a foreign-god war |
| foreign_war_crushing_margin | ysavas_ezici | 35 | 1 | 300 | Son tools | Winning by this margin kills the foreign god |
| foreign_war_min_wound | ysavas_yara | 15 | 0 | 500 | Son tools | Minimum wound of a son defeated by a foreign god |
| foreign_war_essence_loss | ysavas_oz_kayip | 25 | 0 | 500 | Son tools | Essence lost by a son defeated by a foreign god |
| foreign_war_sleep | ysavas_uyku | 2 | 1 | 20 | Son tools | Sleep length (epochs) of a son whose HP runs out |
| foreign_war_win_xp | ysavas_xp | 40 | 0 | 1000 | Son tools | XP of a son who defeats a foreign god |
| foreign_war_win_fame | ysavas_un | 12 | 0 | 500 | Son tools | Fame of a son who defeats a foreign god |
| foreign_war_attitude_damage | ysavas_tutum | 30 | 0 | 200 | Son tools | War's damage to the foreign god's attitude to the pantheon |
| foreign_war_power_loss | ysavas_guc_kayip | 20 | 0 | 100 | Son tools | Power loss of a defeated foreign god |
| healing_sanity_gain | sifa_sagduyu | 12 | 0 | 100 | Son tools | Healing miracle's contribution to affected communities' sanity |
| default_sanity | sagduyu_taban | 70 | 0 | 100 | Son tools | Sanity of a community without one written (same as korku.js default) |
| new_mortal_age_min_pct | yas_min | 20 | 0 | 100 | MO | New mortal's starting age: min % of lifespan |
| new_mortal_age_max_pct | yas_max | 50 | 0 | 100 | MO | New mortal's starting age: max % of lifespan |
| default_stat_base | stat_taban | 15 | 0 | 100 | Son tools | Unwritten stat of a created entity (0–100 scale): base |
| default_stat_per_power | stat_guc | 7 | 0 | 50 | Son tools | Unwritten stat: added per power level |
| default_mortal_age | varsayilan_yas | 20 | 0 | 2000 | MO | Age of a new mortal without one written |
| default_mortal_lifespan | varsayilan_omur | 70 | 1 | 50000 | MO | Lifespan of a new mortal without one written |
| default_people_population | nufus_halk | 2000 | 1 | 1000000 | PG | New people without population: population per power level squared |
| default_other_population | nufus_diger | 300 | 1 | 1000000 | PG | New settlement or community without population: per power level squared |
| default_cult_followers | murit_guc | 60 | 1 | 1000000 | RL | New cult without followers: followers per power level squared |
| levelup_stat1_gain | seviye_stat1 | 3 | 0 | 50 | Son tools | Added to a random first stat on level-up |
| levelup_stat2_gain | seviye_stat2 | 2 | 0 | 50 | Son tools | Added to a random second stat on level-up |
| call_base | ses_taban | 3 | 0 | 100 | Son tools | Relation effect of a word to a sibling: base |
| call_charisma_divisor | ses_karizma_bolen | 12 | 1 | 1000 | Son tools | Relation effect: + charisma / this |
| call_alliance_bonus | ses_ittifak | 2 | 0 | 100 | Son tools | Extra relation from an alliance word |
| call_love_bonus | ses_ask | 4 | 0 | 100 | Son tools | Extra relation from a love word |
| call_threat_penalty | ses_tehdit | 3 | 0 | 100 | Son tools | Extra relation damage from a threat |
| call_warning_penalty | ses_uyari | 2 | 0 | 100 | Son tools | Relation damage from a warning |
| call_bargain_effect | ses_pazarlik | 1 | −100 | 100 | Son tools | Relation effect of a bargain word |
| gift_min_remaining | armagan_kalan | 5 | 0 | 1000 | Son tools | Minimum essence the son must keep after a gift |
| transfer_base_chance | devir_taban | 45 | 0 | 100 | Son tools | Worshipper transfer acceptance: base (%; + (receiver charisma − worshipper faith/2)/2) |
| gift_relation_base | armagan_iliski | 4 | 0 | 100 | Son tools | Gift's relation contribution: base |
| gift_essence_divisor | armagan_oz_bolen | 5 | 1 | 1000 | Son tools | Gift's relation contribution: + essence given / this |
| gift_transfer_relation | armagan_tapan_iliski | 10 | 0 | 100 | Son tools | Extra relation from an accepted worshipper transfer |
| challenge_die | meydan_zar | 20 | 1 | 200 | Son tools | Challenge die faces (result added twice) |
| challenge_power_bonus | meydan_guc_bonus | 15 | 0 | 100 | Son tools | Duelist power bonus in its own stat |
| challenge_untouchable_penalty | meydan_dokunulmaz | 15 | 0 | 100 | Son tools | Untouchable power's deduction from the challenger |
| challenge_fame_loss | meydan_un_kayip | 2 | 0 | 100 | Son tools | Fame loss of the challenge loser |
| challenge_sleep | meydan_uyku | 2 | 1 | 20 | Son tools | Sleep length of a son whose HP runs out in a challenge |
| challenge_relation_damage | meydan_iliski | 15 | 0 | 200 | Son tools | Relation damage of a challenge |
| challenge_covenant_relation_damage | meydan_ahit_iliski | 40 | 0 | 200 | Son tools | Relation damage of challenging a covenanted sibling |
| rebel_loyalty_loss | isyan_sadakat_kayip | 10 | 0 | 100 | Son tools | Loyalty loss of a rebelling son |
| rebel_ambition_gain | isyan_hirs | 5 | 0 | 100 | Son tools | Ambition gain of a rebelling son |
| rebel_loyal_threshold | isyan_sadik_esik | 60 | 0 | 100 | Son tools | Siblings at/above this loyalty cool toward the rebel |
| rebel_sibling_relation | isyan_kardes_iliski | 12 | 0 | 200 | Son tools | Rebellion's relation damage with loyal siblings |
| harvest_abundance_divisor | sag_bolluk_bolen | 8 | 1 | 1000 | Son tools | Harvest gain: abundance / this |
| harvest_wisdom_divisor | sag_bilgelik_bolen | 20 | 1 | 1000 | Son tools | Harvest gain: + wisdom / this |
| harvest_potency_divisor | sag_kudret_bolen | 25 | 1 | 1000 | Son tools | Harvest gain: + resource potency / this |
| harvester_multiplier | sag_hasat_kat | 2 | 1 | 20 | Son tools | Harvest gain multiplier with the Harvester power |
| star_discount_pct | yildiz_indirim | 70 | 1 | 100 | Son tools | Cost (%) of a creation in the epoch star's domain |
| event_severity_base | olay_siddet_taban | 15 | 0 | 100 | Son tools | Unwritten event severity: base |
| event_severity_per_power | olay_siddet_guc | 7 | 0 | 50 | Son tools | Unwritten event severity: per power level |
| item_resource_divisor | esya_kaynak_bolen | 4 | 1 | 1000 | Son tools | Item forged from a resource: potency bonus = resource potency / this |
| megafauna_power | megafauna_guc | 8 | 1 | 30 | CR | New species at/above this power level counts as megafauna |
| creation_xp | yaratim_xp | 10 | 0 | 500 | Son tools | Creation XP: base |
| creation_xp_per_power | yaratim_xp_guc | 3 | 0 | 100 | Son tools | Creation XP: per power level |
| cocreator_xp | ortak_xp | 8 | 0 | 500 | Son tools | Co-creator XP: base |
| cocreator_xp_per_power | ortak_xp_guc | 2 | 0 | 100 | Son tools | Co-creator XP: per power level |
| cocreator_fame | ortak_un | 1 | 0 | 100 | Son tools | Co-creator fame |
| cocreation_relation | ortak_iliski | 5 | 0 | 100 | Son tools | Joint creation's contribution to the two siblings' relation |
| creation_max_links | yaratim_bag_adet | 6 | 1 | 30 | Son tools | Max bonds in one creation |
| knowledge_first_learners | ogrenen_adet | 3 | 0 | 20 | Son tools | Max communities that first learn a new knowledge |
| species_max_traits | ozellik_adet | 3 | 0 | 10 | CR | Max traits of a new species |
| event_max_effects | olay_etki_adet | 5 | 0 | 20 | Son tools | Max stat effects of one event |
| affect_max_stats | etkile_stat_adet | 3 | 1 | 20 | Son tools | Max stats changed in one affect_entity call |
| affect_foreign_multiplier | etkile_yabanci_kat | 2 | 1 | 10 | Son tools | Cost multiplier for affecting someone else's creation |
| affect_foreign_relation | etkile_iliski | 6 | 0 | 200 | Son tools | Relation damage with the creator when affecting their creation |
| chosen_strength | secilmis_guc | 12 | 0 | 100 | Son tools | Strength gain of a declared chosen mortal |
| chosen_charisma | secilmis_karizma | 10 | 0 | 100 | Son tools | Charisma gain of a declared chosen mortal |
| chosen_lifespan | secilmis_omur | 40 | 0 | 50000 | Son tools | Lifespan gain of a declared chosen mortal |
| chosen_foreign_relation | secilmis_iliski | 5 | 0 | 200 | Son tools | Relation damage with the creator for choosing their mortal |
| curse_cost_per_power | lanet_guc | 2 | 0 | 50 | Son tools | Curse cost: essence per target power level |
| curser_cost_pct | lanetci_bedel | 50 | 1 | 100 | Son tools | Curse cost with the Curser power (%) |
| curser_severity_pct | lanetci_siddet | 150 | 100 | 500 | Son tools | Curse severity with the Curser power (%) |
| curse_resist_divisor | lanet_direnc_bolen | 4 | 1 | 1000 | Son tools | Patron's curse resistance: patron will / this |
| curse_untouchable_resist | lanet_dokunulmaz | 15 | 0 | 100 | Son tools | Extra curse resistance of an Untouchable patron |
| curse_severity_base | lanet_siddet_taban | 12 | 0 | 100 | Son tools | Curse severity: base (+ potency / divisor − resistance / 2) |
| curse_potency_divisor | lanet_kudret_bolen | 10 | 1 | 1000 | Son tools | Curse severity: + potency / this |
| curse_min_severity | lanet_siddet_en_az | 5 | 0 | 100 | Son tools | Minimum curse severity |
| curse_creator_relation | lanet_yaratan_iliski | 12 | 0 | 200 | Son tools | Curse's relation damage with the target's creator |
| curse_patron_relation | lanet_hami_iliski | 8 | 0 | 200 | Son tools | Curse's relation damage with the target's patron |
| miracle_xp | mucize_xp | 12 | 0 | 500 | Son tools | Miracle XP |
| miracle_fame | mucize_un | 2 | 0 | 100 | Son tools | Miracle fame |
| dream_base_chance | ruya_taban | 45 | 0 | 100 | Son tools | Dream success: base (%) |
| dream_default_rival_charisma | ruya_karizma_varsayilan | 30 | 0 | 100 | Son tools | Dream: rival charisma when the target has no god |
| dream_whisper_bonus | ruya_fisilti | 25 | 0 | 100 | Son tools | Dream-whisper power's bonus to dream chance (%) |
| dream_zealotry_divisor | ruya_bagnaz_bolen | 4 | 1 | 1000 | Son tools | Dream chance: − target zealotry / this |
| dream_min_chance | ruya_sans_min | 5 | 0 | 100 | Son tools | Lowest dream success chance (%) |
| dream_max_chance | ruya_sans_max | 95 | 0 | 100 | Son tools | Highest dream success chance (%) |
| dream_steal_relation | ruya_iliski | 20 | 0 | 200 | Son tools | Relation damage with the old god who lost a worshipper to a dream |
| dream_sensed_relation | ruya_sezen_iliski | 8 | 0 | 200 | Son tools | Relation damage with the old god for a failed dream |
| dream_xp | ruya_xp | 20 | 0 | 500 | Son tools | XP of a successful dream |
| dream_fame | ruya_un | 4 | 0 | 100 | Son tools | Fame of a successful dream |
| disaster_cost_per_power | afet_guc | 2 | 0 | 50 | Son tools | Disaster cost: essence per target power level |
| disaster_severity_base | afet_siddet_taban | 40 | 0 | 100 | Son tools | Son's disaster severity: base (+ potency / divisor + die) |
| disaster_potency_divisor | afet_kudret_bolen | 3 | 1 | 1000 | Son tools | Disaster severity: + potency / this |
| disaster_die | afet_zar | 20 | 1 | 100 | Son tools | Disaster severity: die faces |
| disaster_min_severity | afet_siddet_min | 20 | 0 | 100 | Son tools | Lowest disaster severity |
| disaster_severity_scale | afet_siddet_olcek | 70 | 1 | 1000 | Son tools | Disaster effect multiplier: severity / this |
| disaster_patron_relation | afet_hami_iliski | 12 | 0 | 200 | Son tools | Disaster's relation damage with the target's patron |
| disaster_creator_relation | afet_yaratan_iliski | 8 | 0 | 200 | Son tools | Disaster's relation damage with the target's creator |
| teach_xp | bilgi_xp | 10 | 0 | 500 | Son tools | XP for teaching knowledge |
| teach_fame | bilgi_un | 2 | 0 | 100 | Son tools | Fame for teaching knowledge |
| incite_base_chance | kiskirt_taban | 45 | 0 | 100 | Son tools | War incitement success: base (%) |
| incite_cunning_divisor | kiskirt_kurnaz_bolen | 3 | 1 | 1000 | Son tools | Incitement chance: + cunning / this |
| incite_min_chance | kiskirt_sans_min | 10 | 0 | 100 | Son tools | Lowest incitement chance (%) |
| incite_max_chance | kiskirt_sans_max | 95 | 0 | 100 | Son tools | Highest incitement chance (%) |
| incite_patron_relation | kiskirt_iliski | 5 | 0 | 200 | Son tools | Successful incitement's relation damage with the sides' patrons |
| transform_cost_per_power | donustur_guc | 2 | 0 | 50 | Son tools | Transform cost: essence per target power level |
| transform_creator_relation | donustur_iliski | 18 | 0 | 200 | Son tools | Transform's relation damage with the creator |
| destroy_cost_per_power | yok_et_guc | 3 | 0 | 50 | Son tools | Destroy cost: essence per target power level |
| destroy_creator_relation | yok_et_iliski | 30 | 0 | 200 | Son tools | Destroy's relation damage with the creator |
| birth_child_ap | evlat_dogur_ap | 2 | 1 | 10 | Son tools | birth_child action cost |
| rekindle_star_ap | tutustur_ap | 2 | 1 | 10 | Son tools | rekindle_star action cost |
| rekindle_star_fame | tutustur_un | 15 | 0 | 500 | Son tools | Fame of a son who rekindles a star |
| hang_star_ap | yildiz_as_ap | 2 | 1 | 10 | Son tools | hang_star action cost |
| extinguish_star_ap | sondur_ap | 2 | 1 | 10 | Son tools | extinguish_star action cost |
| extinguish_star_fame | sondur_un | 25 | 0 | 500 | Son tools | Fame of a son who extinguishes a star |
| extinguish_star_relation | sondur_iliski | 15 | 0 | 200 | Son tools | Extinguishing's relation damage with every sibling |
| birth_world_ap | dunya_dogur_ap | 2 | 1 | 10 | Son tools | birth_world action cost |
| foreign_alliance_threshold | yk_ittifak_esik | 80 | 0 | 300 | Son tools | Alliance with a foreign god: roll threshold |
| foreign_alliance_attitude | yk_ittifak_tutum | 25 | 0 | 200 | Son tools | Accepted alliance's attitude gain |
| foreign_refusal_attitude | yk_ret_tutum | 5 | 0 | 200 | Son tools | Refused alliance or bargain's attitude damage |
| foreign_threat_threshold | yk_tehdit_esik | 90 | 0 | 300 | Son tools | Threatening a foreign god: roll threshold |
| foreign_threat_attitude | yk_tehdit_tutum | 10 | 0 | 200 | Son tools | Successful threat's attitude damage |
| foreign_threat_power_loss | yk_tehdit_guc | 15 | 0 | 100 | Son tools | Power a successful threat takes from the foreign god |
| foreign_threat_fury | yk_tehdit_ofke | 25 | 0 | 200 | Son tools | Failed threat's attitude damage |
| foreign_bargain_threshold | yk_pazarlik_esik | 70 | 0 | 300 | Son tools | Bargaining with a foreign god: roll threshold |
| foreign_bargain_attitude | yk_pazarlik_tutum | 10 | 0 | 200 | Son tools | Successful bargain's attitude gain |
| challenge_die_multiplier | meydan_zar_kat | 2 | 0 | 20 | Son tools | Challenge: die result multiplier |
| challenge_level_multiplier | meydan_seviye_kat | 2 | 0 | 50 | Son tools | Challenge: son's power per level |
| challenge_margin_divisor | meydan_fark_bolen | 2 | 1 | 100 | Son tools | Challenge: loser's extra wound = score difference / this |
| transfer_default_faith | devir_inanc_varsayilan | 50 | 0 | 100 | Son tools | Worshipper transfer: faith of a community without one written |
| transfer_faith_divisor | devir_inanc_bolen | 2 | 1 | 100 | Son tools | Worshipper transfer: worshipper faith / this (subtracted from receiver charisma) |
| transfer_margin_divisor | devir_fark_bolen | 2 | 1 | 100 | Son tools | Worshipper transfer: (charisma − faith share) / this added to chance |
| dream_charisma_divisor | ruya_karizma_bolen | 2 | 1 | 100 | Son tools | Dream chance: + (charisma − rival charisma) / this |
| curse_resist_effect_divisor | lanet_direnc_etki_bolen | 2 | 1 | 100 | Son tools | Curse severity: − patron resistance / this |
| foreign_talk_charisma_divisor | yk_karizma_bolen | 2 | 1 | 100 | Son tools | Foreign-god talk roll: + charisma / this |
| foreign_threat_power_divisor | yk_guc_bolen | 2 | 1 | 100 | Son tools | Foreign-god threat roll: + (strength − their power) / this |
| foreign_talk_attitude_divisor | yk_tutum_bolen | 2 | 1 | 100 | Son tools | Foreign-god alliance & bargain roll: + attitude / this |
| foreign_war_stat_divisor | ysavas_stat_bolen | 2 | 1 | 100 | Son tools | Foreign-god war: son's power = (strength + will) / this |
| reborn_sleep | dirilis_uyku | 1 | 1 | 20 | Son tools | Sleep length (epochs) of a son with the Reborn power when HP runs out |
| default_loyalty | sadakat_varsayilan | 50 | 0 | 100 | Son tools | Loyalty of a son without one written (rebellion test) |
| outsider_bargains_per_epoch | dis_pazarlik_tur | 1 | 0 | 20 | Son tools | Max bargains with an outer being per epoch |
| inspect_sibling_creations | kardes_yaratim | 15 | 1 | 500 | CB | inspect_sibling: max creations shown |

External tunables read by tools (defined elsewhere; listed so the integrator wires them): `KURAL.*` (bedel_*, xp_seviye, can_*, oz_*, yildiz_guc_adim, ek_eylem_*, solgun_eylem_kaybi, en_az_eylem, varlik_*), `YARATIM_TABANI.<type>`, `NADIRLIK_KAPI.*`, `MUDAHALE.*` (miracle/disaster effects), `OLUM.can_al_*`, `OLUM.kardes_*`, `OLUM.dagit_*`, `OLUM.dirilis_en_az_cag`, `DERIN_YASAM.dirilis_adanmislik` (default 100), `KESIF.dar_topluluk` (3) / `toprak_bedava` (1) / `toprak_oz` (10) / `toprak_un` (3), `BOS_DUNYA.ilk_halk_oz` (30) / `ilk_halk_un` (10) / `ilk_halk_xp` (20), `SEYAHAT.hizalanma_donemi` (5), `YABANCI.konusma_irade` (30) / `guc_soz` (15) / `savas_stat_pay` / `guc_kalkan` / `stat_notr`, `PANTEON.*` (kutsal_dunya_iliski 15, muhur_sizinti 10, yildiz_parlaklik 50, olu_yildiz_parlaklik 5, sondurme_sizinti 20, sondurme_bereket 25, sondurme_kiyamet 8, pazarlik_oz 40, pazarlik_etki_bolen 2, pazarlik_hirs 10, pazarlik_sadakat 15, pazarlik_sizinti 20, pazarlik_iliski 10), `OTESI.golem_*`/`ruh_*`, oyuncu.js `TE.tutustur_*`/`yatak_*`, `DENGE.dunya_dogur` (70), `COSTS.*`, `KOZMIK_BEDEL.*`, `MUDAHALE_BEDEL.*`. NOTE: `COSTS`, `KOZMIK_BEDEL`, `MUDAHALE_BEDEL`, `RARITIES` and `DENGE` are plain constants in the old code (not `tanimla` tunables) — per the user's "no unadjustable constant" rule, the new app should make them tunables too.

### 8. Known bugs / design smells (tools)

1. **Free/paid classification by regex on Turkish prose** (`BEDAVA_RE`). Fragile; replace with explicit per-tool metadata (`ap_cost`, `essence_cost` function, `free`).
2. **Build-time snapshot**: available tools, power ceiling, cheap-power discount, epoch-star discount, the star list in `birth_world`'s description, and the world alphabet are computed when the server is built. A level-up/rarity change or `move_to_world` mid-turn is not reflected until a continuation session rebuilds the server. New design: evaluate gates and costs at call time.
3. **Per-epoch counters rebuilt by LIKE-matching Turkish chronicle text** (`turIzleri`), and `duaEdildi` / `armagan` / `capaSecildi` restored as booleans while tools compare them numerically (`true >= 1`), so a cap > 1 is effectively 1 after a crash-resume. Store counters in a `son_epoch_counters` table.
4. **Rejections are returns, not throws**: the transaction wrapper only rolls back on exceptions. Correctness relies on each handler validating before writing (true today, but easy to break). In `affect_entity`, stats are mutated in memory before a later invalid stat rejects (not saved, but confusing). New design: validate fully, then apply.
5. **Inconsistent reachability rules**: `swear_covenant`/`challenge` (`kardesUzak`) and `talk_to_foreign_god` accept any active known route, while `make_interworld_treaty` and `war_on_foreign_god` use `rotaAcikMi` (slingshot routes only when planets are aligned). `call_sibling`, `give_gift`, `inspect_sibling` have no distance check at all. `bargain_with_outsider` has no world check. Unify into one `canReach(sonWorld, targetWorld)`.
6. **`bargain_with_outsider` adds essence without the `ozMax` cap**; every other gain is capped.
7. **`declare_chosen` deactivates every outgoing `tapar` bond** of the mortal, including worship of the creator god or a foreign god; `send_dream` only considers rival worship of sons. Decide one rule for "who is the patron".
8. **Chronicle attribution by id range** (`ogulunEli`, `open_cosmic_bed` rewriting rows with `tur='tanri'`): fragile if anything else writes chronicle rows in between. New design: pass the acting son into helper functions explicitly.
9. **Keyword sniffing on Turkish text** to choose the travel method of a vehicle (`köprü`, `kapı|halka|geçit`, …) and to split "Name, Title". LANGUAGE-SPECIFIC; replace with explicit schema fields (`travel_method`, `title`).
10. **`ekDuzelt` on every tool result and `toLocaleLowerCase('tr')` everywhere** — LANGUAGE-SPECIFIC; drop.
11. **`fillStats` checks `tdef.ad === 'Halk'`** (display label) — use the type key.
12. **Co-creator payment skips level-up** (`o2.xp +=` without `kazanc`), so a co-creator can sit above the XP threshold until its next `kazanc`.
13. **`resurrect_sibling` can put the son to sleep** (failed descent) but its result lacks the `uyudun()` notice; the gate stops later calls, yet the model is not told immediately.
14. **Long jobs registry is process-local** (`SUREN`); the persisted `bekleyenIs` flag is the real crash guard. In the new async backend keep one durable job table (status: pending/running/done/refunded).
15. **`inspect_entity` works on any state** while most tools require canonical; fine, but the model sometimes targets dead ids — the uniform `durumNedeni` message is good and should be kept.
16. **`afet_gonder` checks only `isimAlinmis`**, not `benzerAd` (creation tools check both).
17. **Tool-name/description coupling**: model-facing descriptions embed live tunable values (costs, caps). Keep this (good UX) but generate from metadata, not string concatenation.
18. **Limits with value 0** disable a tool only for `can_al`/`kardes_*` (tool hidden); other `*_tur` caps set to 0 leave the tool visible but always rejecting. Hide tools whose cap is 0.

---

## 6. Agent roles outside agents.js (council, son chat, linguist, world birth, Fate network repair, mortals)

All roles below call **Haiku** (user rule: every LLM call uses Haiku; no Sonnet/Opus fallback; no `effort` parameter).
Old code looked the model up with `modelFor(key)` from `dunya.modeller` JSON (defaults all `'haiku'`, fallback
`MODEL_YEDEK='haiku'`); in the new app the model is a single constant and the per-key model setting is removed.
Prompt texts are in `09-prompts.md` (ids referenced below). Structured calls go through the shared
`structured()` wrapper (retry/timeout policy in `10-epoch-pipeline.md`); the mortal turn goes through `agentTurn()`.

Group name translations used in the tunable tables: Ajanlar ve model = Agents and model; Bağlam bütçeleri = Context
budgets; Konsey = Council; Arayüz = UI; Dil ve adlar = Language and names; Kozmos ve seyahat = Cosmos and travel;
Ağ = Network; Ölümlü ajanlar = Mortal agents; Savaş ve diplomasi = War and diplomacy; Din ve dil = Religion and
language; Nüfus ve büyüme = Population and growth; Ekonomi = Economy; Yaratıklar = Creatures; Kahramanlar ve ölümlüler
= Heroes and mortals; Fırsatlar = Opportunities; Yaratılış sihirbazı = Creation wizard; Kozmik korku = Cosmic horror;
Ölüm = Death.

---

### Role: Council of the Gods (`konseyTopla`, konsey.js)

**Purpose.** A single structured call narrates a council session: every attending son speaks, one concrete motion is
voted on, alliances may be formed or broken, and a passed motion has a mechanical effect.

**Triggers.**
- Automatic, in the Fate phase of the epoch, after "voice of the peoples": if `world.konsey_sikligi` (fallback
  `COUNCIL.default_frequency`) > 0 and `age % frequency == 0` and the resume-state flag `cd.konsey` is unset. The flag
  is set *before* the call (a crashed council is not retried on resume). `caller = 'kader'`, no topic (auto agenda).
- Player action (`epoch.konsey(topic)`): costs `DENGE.konsey` essence from the creator (`harca`); refunded (`iade`) if
  the call throws. Serialized by lock `'konsey'`. `caller = 'tanri'`.

**Model.** Haiku. Timeout `COUNCIL.timeout_s`. Retries: the default `MODEL.deneme` policy. Metric name "Council".

**Context assembly.**
1. Members = sons with `durum in ('aktif','uykuda')`, first `COUNCIL.max_members` (DB order). If fewer than
   `COUNCIL.min_members` → error `At least {n} sons are needed for a council.`
2. Topic = trimmed player text, else auto agenda (`council.agenda.*`, 09).
3. Relationship lines for each member pair with `|rel| >= COUNCIL.relation_threshold` or a covenant.
4. Absent = living sons (`durum != 'olu'`) not among members.
5. Prompt `council.session.system` + `council.session.prompt`; schema `council.session.schema`.
6. Emits UI event `{kind:'kader_adim', text:'The Council of the Gods is gathering: "{topic}"'}` before the call;
   retry notices forwarded as events.

**Post-processing (all in ONE transaction; if it fails nothing is written and the player's cost is refunded):**
1. Votes: keep only votes from members, first vote per son wins (duplicates dropped).
2. `yes = count(vote=yes)`, `no = count(vote=no)`; `passed = yes > no`.
3. Pairwise vote affinity: for every pair of (filtered) votes where neither abstained: same vote →
   `relationship(a,b) += COUNCIL.vote_affinity`, different → `-= vote_affinity`.
4. Alliances: filter `a != b`, both members; take first `COUNCIL.alliance_cap`.
   - `covenant` and no existing covenant: add bond son→son `muttefik` (ally) with description `Council covenant: {reason}`
     in current age; `relationship += COUNCIL.covenant`; note `{A} and {B} made a covenant in the council`.
   - `break`: deactivate all active son↔son `muttefik` bonds between them (both directions);
     `relationship -= COUNCIL.break_cost`; note `{A} and {B} broke apart in the council`.
5. If passed, by `decision`:
   - `against_doomsday`: `world.kiyamet = max(0, kiyamet - COUNCIL.doomsday_pushback)`; note `the doomsday clock was pushed back {n}`.
   - `joint_blessing`: for every member, re-read the son fresh (it may have changed during the call), `existence (varlik) = clamp(varlik + COUNCIL.blessing, 0, 100)`; note `all brothers' existence grew stronger`.
   - `condemn_rebel`: for every member that is a rebel (`asi`): `fame (un) = max(0, un - COUNCIL.condemn_fame)`; note `{name}'s fame was shaken by condemnation`.
   - `call_for_peace`: among active entity↔entity `dusman` (enemy) bonds whose both ends are canon with population >0
     (`nufus || murit || 100`), score `p = (2 if source worships a member son) + (2 if target worships a member son) + log10(pop_a + pop_b)`;
     the highest-scoring bond is deactivated in both directions; note `by the gods' command {A} and {B} made peace`.
   - `none`: nothing.
6. Minutes object: `{topic, caller, speeches (members only, with name), motion, votes (with names), passed, decision, notes, minutes}`;
   insert into `konseyler (cag, konu, tutanak JSON, kabul)`.
7. Chronicle (type `konsey`, no son): `The Council of the Gods convened ({agenda}). Motion: "{motion}" — {passed ? 'passed' : 'rejected'} ({yes} yes, {no} no).{?notes:  {notes joined '; '}.} {minutes}`
   where agenda = model's `agenda` field without trailing punctuation when the player asked (fallback `at {creator}'s question`), else the topic.
8. After commit, emit `{kind:'konsey', id, topic, passed, motion}` (an emit failure does not trigger a refund).

**Tunables — `KONSEY` (Council).**

| key | old key | default | min | max | group | label |
|---|---|---|---|---|---|---|
| max_members | uye | 9 | 2 | 30 | Council | Most sons attending the council |
| min_members | en_az | 2 | 2 | 30 | Council | Fewest sons needed for the council to convene |
| vote_affinity | oy_yakinlik | 3 | 0 | 50 | Council | Relationship gain between those voting alike |
| covenant | ahit | 12 | 0 | 100 | Council | Relationship gain of a council covenant |
| break_cost | kopus | 15 | 0 | 100 | Council | Relationship cost of a break in the council |
| doomsday_pushback | kiyamet_geri | 10 | 0 | 100 | Council | Hours the doomsday clock is pushed back by an accepted motion against doomsday |
| blessing | kutsama | 5 | 0 | 100 | Council | Existence gain of a joint blessing |
| condemn_fame | kinama_un | 10 | 0 | 200 | Council | Fame cost of condemning the rebel |
| agenda_doomsday_pct | gundem_kiyamet | 50 | 0 | 100 | Council | Doomsday comes on the agenda at this % of the threshold |
| timeout_s | sure | 240 | 30 | 3600 | Agents and model | Council timeout (s) |
| relation_threshold | iliski_esik | 20 | 0 | 100 | Council | Lowest sibling relationship strength (±) written into the council prompt |
| alliance_cap | ittifak_tavan | 3 | 0 | 20 | Council | Most alliances or breaks in one council |
| default_frequency | siklik_varsayilan | 4 | 0 | 100 | Council | Every how many ages a council convenes when the world has no frequency set |
| agenda_text_max | gundem_metin | 260 | 20 | 5000 | Context budgets | Max length of an open story taken onto the agenda (chars) |
| agenda_cut | gundem_kes | 250 | 10 | 5000 | Context budgets | A long story is cut at the last space before this char |
| persona_temperament | persona_mizac | 160 | 0 | 5000 | Context budgets | Council and chat: son's temperament (chars) |
| persona_speech | persona_uslup | 120 | 0 | 5000 | Context budgets | Council and chat: son's manner of speech (chars) |
| persona_obsession | persona_takinti | 100 | 0 | 5000 | Context budgets | Council and chat: son's obsession (chars) |
| persona_plan | persona_plan | 160 | 0 | 5000 | Context budgets | Council and chat: son's plan (chars) |
| chat_appearance | sohbet_gorunus | 200 | 0 | 5000 | Context budgets | Chat: son's appearance (chars) |
| chat_secret | sohbet_sir | 120 | 0 | 5000 | Context budgets | Chat: son's fear and secret (chars, each) |
| chat_memory | sohbet_hafiza | 3500 | 200 | 100000 | Context budgets | Chat: son's memory (chars) |
| chat_history | sohbet_gecmis | 10 | 0 | 200 | Context budgets | Chat: previous messages in the prompt |
| chat_list | sohbet_liste | 40 | 1 | 1000 | UI | Messages shown in the chat history |
| chat_text_max | sohbet_metin | 800 | 10 | 20000 | Council | Longest thing the god may say to his son (chars) |
| chat_loyalty | sohbet_sadakat | 6 | 0 | 100 | Council | Max loyalty change from one chat (±) |
| chat_timeout_s | sohbet_sure | 120 | 10 | 3600 | Agents and model | Chat timeout (s) |
| dream_text_max | ruya_metin | 600 | 10 | 20000 | Council | Longest dream text sent to a mortal (chars) |
| dream_text_min | ruya_en_az | 5 | 1 | 1000 | Council | Shortest dream text (chars) |
| translate_text_max | ceviri_metin | 300 | 10 | 20000 | Language and names | Longest sentence to translate |
| translate_lexicon | ceviri_sozluk | 250 | 0 | 10000 | Language and names | Lexicon words sent to the translation prompt |
| translate_syllables | ceviri_hece | 12 | 0 | 200 | Language and names | Common initial and final syllables sent (each) |
| translate_new_words | ceviri_yeni | 6 | 0 | 100 | Language and names | Most new words added to the lexicon by one translation |
| translate_timeout_s | ceviri_sure | 120 | 10 | 3600 | Agents and model | Translation timeout (s) |

DB writes: `konseyler`, `baglar`, `ogullar.relationship` (via `iliskiDegistir`), `ogullar.varlik/un`, `dunya.kiyamet`,
`kronik`.

---

### Role: Son chat (`ogulSohbet`, konsey.js)

**Purpose.** The player (creator) talks to one son; the son replies in character and his loyalty shifts.
**Trigger.** API `POST /api/ogullar/{id}/sohbet {metin}`. No cost.
**Validation.** Son must exist (`Son not found`); a dead son → error `{name} is dead; your voice does not reach his bones.`;
text trimmed and cut to `COUNCIL.chat_text_max`; empty → `Say something.`
**Context.** History = last `chat_history` messages with `niyet='sohbet'` between creator (`kimden_tip='t'`) and this son,
oldest first. Prompts `son_chat.system`, `son_chat.prompt`, schema `son_chat.schema`. Timeout `chat_timeout_s`.
**Post-processing.** Re-read the son (may have changed); `delta = clamp(int(loyalty_change), -chat_loyalty, +chat_loyalty)`;
`tutku.sadakat = clamp(sadakat + delta, 0, 100)`; save. Insert two `mesajlar` rows (age = current): creator→son
(`niyet='sohbet'`, read) and son→creator (`niyet='sohbet'`, read, answered) with the reply. Return
`{reply, attitude, loyalty, change}`. `sohbetGecmisi(sonId)` returns the last `chat_list` messages for the UI.

---

### Role: Dream to a mortal (`tanriRuyasi`, konsey.js) — no LLM call

Player sends a dream to a canon entity of type people, settlement, faction, cult, named mortal or species (else
`Only a thinking community or mortal can see a dream.`; not canon → `This entity is not in the world.`). Text trimmed to
`dream_text_max`, shorter than `dream_text_min` → `The dream must have content.` Costs `DENGE.ruya` creator essence (error
`A dream needs {n} essence.`). Inserts `mesajlar (kime_tip='v', niyet='ruya', okundu=0)`, chronicle type `tanri`:
`{creator} sent a dream to {entity}.` Unread dreams/manifestations raise that entity's mortal-agent selection score
(`OLUMLU_ARAC.agent_dream`) and are shown at the top of its next turn (`mortal.turn.dream`), then marked read only
after the turn finishes (a crashed, retried turn sees them again).

---

### Role: Linguist / translation (`cevir`, konsey.js)

**Purpose.** Translate a sentence into a world language; missing words are coined in the language's phonology and added
to its lexicon. **Trigger.** API `POST /api/cevir {dil_id, metin}`. No cost.
**Validation.** Entity must be `tur='dil'` (`No such language.`); text trimmed to `translate_text_max`; empty →
`Write something to translate.`
**Context.** Lexicon first `translate_lexicon` rows; phonology syllable tables from `dilmotoru.fonoloji(dilId)` (initial
`bas`, final `son` maps; first `translate_syllables` keys of each). Prompts `linguist.translate.*`. Timeout
`translate_timeout_s`.
**Post-processing.** New words: drop empty and those already in the lexicon (case-insensitive), cap
`translate_new_words`, add with example `"{translation}" ({original})`, author = creator (`'t'`), current age. Return the
model output with the filtered `new_words`.

---

### Role: World birth (`dunyaDogur`, kozmos.js)

**Purpose.** One structured call creates a whole new world: name, type, physics, cosmology, naming dialect, regions,
sky body, a unique resource, optionally the cosmos's single travel resource, a native language, optional old god and
natives; then it is placed around a star (existing or new) or as a moon.

**Triggers / callers.**
1. Player (`epoch.dunyaYarat`): costs `DENGE.dunya`, refunded on failure; lock `'dunya'`; inspiration cut to `TANRI.ilham_uzunluk`; optional placement `{star_id, parent_world_id, new_star}`.
2. Son tool (tools.js world-birth tool) with `yaratan = son`.
3. Mortal intuition (`ufuk.sezgiyiDogur`, from the `rota_kesfet` tool or end-of-age `sezgileriIsle`).
4. Genesis "small/large cosmos" setting (server.js) creates `ekDunyaSayisi` extra worlds with inspiration `cosmos.inspiration.genesis_extra_world`.

**Model.** Haiku, timeout 300 s (hard-coded — make it a rule), metric "World birth". Emits
`{kind:'kader_adim', text:'{creator or son} is giving birth to a new world{ (type name)}…'}` before; after success
`{kind:'dunya_dogdu', dunya_id, name}`; also invalidates the cached map. Errors after the world row is committed are
swallowed so the caller does not refund.

**Validation.** Requested type must exist (`Invalid world type.`); output must have a non-blank name (`World birth output
has no name.`); at least one region (`A world cannot be born without regions.`).

**Processing (`dunyaDogusuIsle`, one transaction; testable separately with recorded outputs):**
1. Type = requested, else model's if valid, else `olagan` (ordinary). Entity `kaynak` = `'kozmos'` if a son created it (so its contents are not sent to Fate's judgment as creations), else `'tanri'`.
2. Sound set = distinct letters of the native language's words if `>= WORLD_BIRTH.sound_set_min` letters, else none.
3. Placement priority: player's request (`parent_world_id` if exists → moon; `star_id` if exists; `new_star`) → model's `moon` with a valid parent → if a new star is not required and stars exist: model's `star_id` if valid, else a star whose type is named in the world's description/day/cosmology text (longest type name first), else a random star. A new star is required iff `placement=new_star` and (model filled `star.name` OR the narrative names a star type that no existing star has). A moon inherits its parent's star.
4. Name = unique name (`benzersizAd`, checked against all entity/son/star/world/foreign-god names).
5. New star (no star and no parent): angle random, distance `260 + starCount*140`; star = model's `star` if named, else `{name: "{world} Sun", type: narrative type or 'yellow dwarf'}`; invalid type → yellow dwarf; name made unique and must differ from the world name (else `"{world} Sun"`); brightness 0 for `black sun`, else `WORLD_BIRTH.star_brightness + d(star_brightness_die)`.
6. Orbit: moon → `0.15 + siblingMoons*0.08`; planet → `1 + siblingPlanets*0.7 + random*0.4`. Gravity/atmosphere must be in the enum else `ordinary`. Time factor clamped to `[DUNYA_FIZIK.zaman_en_az/100, zaman_en_cok/100]`, non-numbers → 1. Seed `"{name}:{random base36}"`; terrain = type's `arazi`; `kesif='bilinen'`; danger `clamp(danger + d(danger_die))`; description = `description + " " + day`.
7. Mirror worlds get a twin (`aynaIkiziAta`): same-star non-forgotten world with most mortals, else most populous world.
8. Entities (insert helper adds an `icinde` bond to its location; names failing the sound set are queued for re-derivation):
   - regions (max `region_max`): stats `{width: region_width + d(region_width_die), danger/fertility/magic: model value or defaults}`, power `region_power`;
   - sky (if named): `{brightness: sky_brightness+d(..), effect: sky_effect+d(..)}`, power `sky_power`;
   - unique resource in region `region_index` (clamped): description + ` Rule: {rule}`; stats abundance/value/might base+die; power `resource_power`; tags `['özgün kaynak', 'dunya:{id}', 'mekanik:{m}'…]` (max `mechanics_max`, valid keys; `sacred` becomes `mekanik:kutsal:{creatorSonId or 0}`);
   - cosmic resource only if the world has none, its name differs from the unique resource, and no canon entity is tagged `kozmik kaynak`: store `{name, description, rule, side_effect}` on `dunya.kozmik_kaynak`; create resource `"{name} Deposit"`, subtype `cosmic travel resource`, description `{desc} {rule} Price: {side_effect}`, stats abundance `cosmic_abundance+d`, value `cosmic_value`, might `cosmic_might+d`, power `cosmic_power`, tags `['kozmik kaynak','mekanik:bagimlilik','mekanik:sabit']`;
   - native language (if named): type `dil`, subtype default `native language`, description `{desc} Dialect: {dialect}`, stats spread `lang_spread`, complexity/sanctity base+die, power `lang_power`; lexicon words (max `words_max`) added with author son or creator; then every queued non-conforming name is re-derived from the language (`adUret(dilId, "dogus:{world}:{id}", region ? 'yer' : 'genel')`) and tagged `dilden-ad`;
   - natives (max `natives_max`) in their region: people stats `{population: base+d, warlike: base+d, magic: d(..), craft: base+d, faith: base+d}`, species stats `{hp, strength, agility: base+d, intelligence: d(..), danger: base+d}`; power `native_power`; tag `yerli`; people get `konusur` (speaks) → language and, if in the resource's region, `sahip` (owns) → unique resource;
   - old god → `yabanciTanriEkle({...old_god, world})` (foreign gods module).
9. Son creator: `ogullar.aktif_dunya = new world`; bond son `korur` (protects) → first region.
10. `dunyayiBagla(world, age, {hedef: creator's previous world})` (travel module; errors ignored).
11. Chronicle `dunya_dogusu`: `{creator} gave birth to a new world: {name} ({type name}). {description}` with region/sky/resource ids.

**Tunables — `DUNYA_DOGUS` (World birth, group Cosmos and travel).** "base + die" = `base + d(die)`.

| key | old key | default | min | max | label |
|---|---|---|---|---|---|
| region_min | bolge_en_az | 2 | 1 | 50 | Fewest regions in a new world |
| region_max | bolge_en_cok | 4 | 1 | 50 | Most regions in a new world |
| words_min | kelime_en_az | 8 | 0 | 200 | Fewest words in the new world's language |
| words_max | kelime_en_cok | 14 | 1 | 200 | Most words in the new world's language |
| mechanics_max | mekanik_en_cok | 2 | 0 | 10 | Most rules of the unique resource |
| natives_max | yerli_en_cok | 2 | 0 | 20 | Most natives (species or people) in a new world |
| banned_names | yasak_ad | 60 | 0 | 2000 | Region/people/language/place/sky names not to repeat in the prompt (newest first) |
| banned_cosmic_names | yasak_kozmik_ad | 200 | 0 | 2000 | World/star/foreign-god names not to repeat (newest first) |
| sound_set_min | ses_kumesi | 8 | 1 | 100 | Fewest distinct letters to count as the dialect's sound set |
| star_brightness / _die | yildiz_parlaklik / _zar | 40 / 55 | 0/1 | 100 | New star brightness base / die |
| danger / _die | tehlike / _zar | 30 / 40 | 0/1 | 100 | New world danger base / die |
| region_power | bolge_guc | 6 | 1 | 12 | Birth region power level |
| region_width / _die | bolge_genislik / _zar | 50 / 30 | 0/1 | 100 | Birth region width base / die |
| region_danger | bolge_tehlike | 30 | 0 | 100 | Birth region danger (if model gives none) |
| region_fertility | bolge_bereket | 50 | 0 | 100 | Birth region fertility (if none) |
| region_magic | bolge_buyu | 30 | 0 | 100 | Birth region magic (if none) |
| sky_power | gok_guc | 5 | 1 | 12 | Birth sky power level |
| sky_brightness / _die | gok_parlaklik / _zar | 40 / 50 | 0/1 | 100 | Birth sky brightness |
| sky_effect / _die | gok_etki / _zar | 30 / 50 | 0/1 | 100 | Birth sky effect |
| resource_power | kaynak_guc | 6 | 1 | 12 | Unique resource power level |
| resource_abundance / _die | kaynak_bolluk / _zar | 50 / 40 | 0/1 | 100 | Unique resource abundance |
| resource_value / _die | kaynak_deger / _zar | 60 / 40 | 0/1 | 100 | Unique resource value |
| resource_might / _die | kaynak_kudret / _zar | 40 / 50 | 0/1 | 100 | Unique resource might |
| cosmic_power | kozmik_guc | 8 | 1 | 12 | Cosmic resource deposit power level |
| cosmic_abundance / _die | kozmik_bolluk / _zar | 70 / 30 | 0/1 | 100 | Cosmic deposit abundance |
| cosmic_value | kozmik_deger | 95 | 0 | 100 | Cosmic deposit value |
| cosmic_might / _die | kozmik_kudret / _zar | 80 / 20 | 0/1 | 100 | Cosmic deposit might |
| lang_power | dil_guc | 4 | 1 | 12 | Native language power level |
| lang_spread | dil_yayginlik | 40 | 0 | 100 | Native language spread |
| lang_complexity / _die | dil_karmasiklik / _zar | 40 / 30 | 0/1 | 100 | Native language complexity |
| lang_sanctity / _die | dil_kutsallik / _zar | 20 / 40 | 0/1 | 100 | Native language sanctity |
| native_power | yerli_guc | 4 | 1 | 12 | Natives' power level |
| people_population / _die | halk_nufus / _zar | 2000 / 8000 | 1 | 10000000 | Native people population |
| people_warlike / _die | halk_savascilik / _zar | 30 / 50 | 0/1 | 100 | Native people warlikeness |
| people_magic_die | halk_buyu_zar | 70 | 1 | 100 | Native people magic (die only) |
| people_craft / _die | halk_zanaat / _zar | 20 / 50 | 0/1 | 100 | Native people craft |
| people_faith / _die | halk_inanc / _zar | 20 / 40 | 0/1 | 100 | Native people faith |
| species_hp / _die | tur_can / _zar | 100 / 400 | 1 | 100000 | Native species hp |
| species_strength / _die | tur_guc / _zar | 30 / 60 | 0/1 | 100 | Native species strength |
| species_agility / _die | tur_ceviklik / _zar | 20 / 60 | 0/1 | 100 | Native species agility |
| species_intelligence_die | tur_zeka_zar | 80 | 1 | 100 | Native species intelligence (die only) |
| species_danger / _die | tur_tehlike / _zar | 20 / 70 | 0/1 | 100 | Native species danger |

Related: `DUNYA_FIZIK.zaman_en_az` 25 (%), `zaman_en_cok` 400 (%) — time factor bounds for model-born worlds (owned by
the cosmos/physics part).

---

### Role: Fate — knowledge-network bond suggestion (`kaderBagOner`, agonar.js)

**Purpose.** For weakly connected records, Fate proposes only evidence-backed narrative bonds chosen from a candidate
list. **Triggers.** (a) end-of-age network repair if `AG.kader_oto = 1` (orchestrated by `epoch.agKader({oto})`, a
background job in the parallel pool), (b) per-record "Suggest bonds" button (`ids=[id]`), (c) full repair (`tam`).
Batches: up to `AG.kader_parti` records per call. Per pass: priority records (events/legends/traditions mentioned
alongside unbonded records in the chronicle, `oncelikliKayitlar`) get `AG.oncelik_payi`% of `AG.kader_cag_tavan`, the rest
are weakest records (`zayifKayitlar`). Stoppable via `agKaderDurdur()`.

**Target selection.**
- `zayifKayitlar(limit)`: entities with `durum in (kanon, olu, gerceklesti)`, not pending, not looked at in the last
  `AG.tekrar_cag` ages (table `ag_bakis`), with visible-bond degree `<= AG.zayif_derece`; ordered by degree asc,
  importance (`onem`) desc, id.
- `oncelikliKayitlar(limit)`: types `olay, efsane, gelenek`, same status/recency filters, ordered by the count of
  distinct co-mentioned entities with no bond to it (desc), importance desc; only those with count > 0.
- Visible bond (`GORUNUR_BAG`): active, or inactive but not closed by a rejection (`red_kapatti`) and whose description
  does not start with `kapatıldı:` ("closed:").

**Candidates per record (`adayKomsular`)**, in order, deduped, max `max(AG.aday, cap*2)*2`:
co-mentioned in the chronicle (most frequent first, limit `max(AG.aday, cap*2)`) → its location → its maker (`yapan_id`)
→ its creator son (`yaratan_id`) → others in the same location (by importance, limit `AG.aday`) → notable entities of its
world excluding regions (by importance, limit `AG.aday`). `cap` = `max(AG.oneri_tavan, AG.olay_oneri_tavan)` for events,
else `AG.oneri_tavan`.

**Call.** `fate_bonds.suggest.*` prompts; emits `{kind:'sistem', text:'Fate is looking at {n} weakly connected records…'}`.

**Validation of each returned bond (transaction):** record id (strip leading `v`) must be a target; `other` must exactly
match a candidate key; type in `ONERI_TURLERI`; reason length `>= AG.gerekce_en_az` and not a pure shared-theme reason;
per-record count below cap; direction applied (`from_other` swaps), then normalised by `bagYonu` (e.g. reversed
`part_of` is flipped); skip if the pair already has ANY active bond (either direction); `companion` requires both ends to be
son/foreign god/`YOLDAS_TURLERI` (`olumlu, tur, ordu, ruh, hizip, tarikat, halk`) and a reason passing
`yoldasGerekcesiYeter` (length `>= AG.yoldas_gerekce_en_az`, words `>= AG.yoldas_sozcuk_en_az`, not shared-theme).
Accepted → `addBag(source, target, type, reason, age)`. All targets get `ag_bakis.cag = current age` (upsert) whether or
not bonds were made. Log line + event `{kind:'ag_onarim', tur:'kader', text, bonds:[{a,type,b,reason}], looked:[…]}`; text
`Fate looked at {n} records and made {k} reasoned bonds.` or `Fate looked at {n} records; it found no bond with enough evidence.`
Returns `{looked, made, bonds}`.

### Role: Fate — naming vague "related" bonds (`ilgiliAdlandir`, agonar.js)

**Purpose.** Active `ilgili` (related) bonds with no description get a concrete type, or are closed if meaningless.
**Trigger.** Same job as above, after suggestions, if `ilgili` enabled: loops with a cursor (`sonId`) in batches of
`min(remaining, AG.ilgili_parti)` until `AG.ilgili_cag_tavan` (or exhaustion in full mode). Bonds whose ends have no
node line are skipped.
**Call.** `fate_bonds.name_related.*`; event `Fate is naming {n} vague "related" bonds…`.
**Validation per decision (transaction):** `no` maps to batch index (1-based); `close` → set inactive, description
`closed: {reason}` (cut to `AG.aciklama_kirp`); `related` whose reason matches DENIAL → closed the same way; otherwise
reason length `>= AG.gerekce_en_az` and decision in types or `related` → update `tur` and description. Undecided bonds
are not asked again in this pass (cursor moves past them). Event `{kind:'ag_onarim', tur:'ilgili', …}`, text
`Fate looked at {n} vague bonds: {k} named, {c} closed.` Returns `{looked, named, closed, sonId}`.

**Tunables — `AG` (Network).**

| key | old key | default | min | max | label |
|---|---|---|---|---|---|
| auto_repair | oto_onar | 1 | 0 | 1 | Loose ends are repaired automatically at end of age (1 on, 0 off) |
| fate_auto | kader_oto | 1 | 0 | 1 | At end of age Fate suggests reasoned bonds for weak records and names vague bonds |
| weak_degree | zayif_derece | 1 | 0 | 100 | A record with this many bonds or fewer counts as weakly connected |
| fate_batch | kader_parti | 12 | 1 | 200 | Max records Fate suggests bonds for in one request |
| fate_age_cap | kader_cag_tavan | 36 | 0 | 100000 | Max weak records Fate looks at at end of age |
| candidates | aday | 10 | 1 | 100 | Candidate neighbours shown to Fate per record |
| suggestion_cap | oneri_tavan | 3 | 1 | 20 | Max new bonds Fate makes for one record at once |
| reason_min | gerekce_en_az | 15 | 0 | 1000 | Min length of Fate's bond reason (chars); shorter is rejected |
| companion_reason_min | yoldas_gerekce_en_az | 40 | 0 | 1000 | Min reason length for a "companion" bond (must describe something lived together) |
| companion_words_min | yoldas_sozcuk_en_az | 6 | 0 | 100 | Min words in a "companion" reason |
| recheck_ages | tekrar_cag | 10 | 0 | 10000 | A record Fate looked at is re-examined at the earliest this many ages later |
| related_batch | ilgili_parti | 40 | 1 | 1000 | Max undescribed "related" bonds named in one request |
| related_age_cap | ilgili_cag_tavan | 80 | 0 | 100000 | Max undescribed "related" bonds named at end of age |
| description_cut | aciklama_kirp | 300 | 50 | 10000 | Length of record descriptions shown to Fate (chars) |
| list | liste | 20 | 1 | 1000 | Weakest records and recent repairs listed in the connectivity summary |
| name_min | ad_en_az | 4 | 1 | 100 | Min name length to link a record named in a text (short names mis-match) |
| event_suggestion_cap | olay_oneri_tavan | 8 | 1 | 100 | Max bonds Fate makes at once to a much-mentioned event (war/disaster participants) |
| priority_share | oncelik_payi | 50 | 0 | 100 | Share of each Fate pass for events/legends/traditions mentioned but unbonded (%) |
| topic_cap | konu_tavan | 5 | 0 | 100 | Max topics named in a legend/tradition/work's description that get bonded |
| main_cluster_good | ana_obek_iyi | 95 | 0 | 100 | Connectivity shown healthy when the main cluster exceeds this % of nodes |

(Rule-based loose-end repair `kopukUclariOnar`, `agBagOnarimi`, `agSagligi` are LLM-free and belong to the network/lore
part of the spec.)

---

### Role: Mortal agent turn (`olumluTuru`, olumluler.js)

**Purpose.** Selected mortals (peoples, factions, cults, settlements, named mortals, intelligent species) act in their
own interest with a tool-using agent turn: produce, build, found languages, discover, trade, wage war, choose gods,
explore other worlds, etc. Their closing «saying» enters the chronicle.

**Trigger.** Epoch phase 2 "Mortals' turn", after sons. Count = `world.olumlu_sayisi ?? OLUMLU_AJAN.varsayilan` (0
disables). Selected ids are stored in resume state `cd.ajanlar` once; on resume only those with
`son_eylem_cag < age` and still canon act. Run through a pool with concurrency `world.olumlu_paralel ?? 1`. On error,
one immediate retry with a fresh entity read; second failure → event `{name} could not act this age: {err}`. Respects the
global stop flag.

**Selection (`ajanAdaylari(count)`).** Candidates: canon entities with `son_eylem_cag < age`, type in
`OLUMLU_AJAN.turler`, species only if intelligence `>= OLUMLU_AJAN.zeka_esigi`. Multi-world: candidates grouped by world
(non-forgotten worlds); worlds with a manual per-world count (`dunyalar.olumlu_ajan`) get `min(manual, candidates)`;
the remaining total is split proportionally to candidate counts (`dunyaPaylari`: floor shares, each world with
candidates gets at least 1 when total >= number of such worlds, remainders by largest fractional part, capped at
candidates); entities tagged `ajan seçili` (agent selected) are always included. Per group (`ajanSec`):
`score = power*agent_power_mult + log10(max(10, population|disciples|agent_pop_default))*agent_pop_mult
 + (tag 'seçilmiş' ? agent_chosen : 0) + min(agent_wait_cap, (age - last_action_age)*agent_wait_mult)
 + d(agent_die) + (pending dream/manifestation ? agent_dream : 0) + (tag 'ajan seçili' ? 1000 : 0)`;
sorted desc; first pass enforces diversity: at most `max(1, ceil(count / agent_type_share))` per type; second pass fills
remaining slots ignoring diversity. Count 0 → only 'ajan seçili' entities.

**Turn state / resume.** `ctx = {cag, ap, yaratimlar:[], …counters}`. If `tur_cag == age` and `tur_ap` not null the
turn is half done: restore `ap` and counters from `tur_ctx`. Persist `(tur_cag, tur_ap, tur_ctx)` at start and after
every successful tool call (via `araclariSar` save hook). Before the turn: overdue debts are processed
(`borcVadeleri` → `medeniyet.borcGecikmeleri`).

**Model call.** `agentTurn({name:'Mortal turn: {name}', model: Haiku, system: mortal.turn.system, server, serverName:'olumlu',
maxTurns: OLUMLU_AJAN.maxTurns, prompt: mortal.turn.prompt(resume? resume_extra), tamamMi: saying non-empty,
devamPromptu: continuation, sunucuYap: fresh server per session})`. Events forwarded with `varlik_id` and `ogul_ad`
(=entity name); `{kind:'olumlu_basla', varlik_id, ad, tur, model, yarim}` at start.

**After the turn.** Saying = `sozuAyikla(final text)`. Mark the shown dreams and manifestations read. `son_eylem_cag = age`,
`tur_ap = NULL`. Remove tag `ajan seçili`. If saying: chronicle type `soz`: `{name}: "{saying[:600]}"` with ids
`[entity, ...creations]`. Event `{kind:'olumlu_bitti', varlik_id, ad, saying, creations, status}`. Returns creation ids.

**Tool wrapper rules (apply to every mortal tool).**
- All non-async handlers run inside one DB transaction (`atomik`); a crash leaves no partial write.
- `araclariSar`: calls in one turn are serialized; snapshot of ctx before each call, restored on exception, returning
  `REJECTED: An error occurred while the tool was running ({msg[:200]}). Your action was refunded; fix your input and try
  again or choose another action.`; every world-changing call is recorded in Fate's ledger (`defter`) with
  `{kim_tip:'v', kim_id, kim_ad, cag, arac, girdi}` (read tools excluded) for selective undo.
- Gate (all tools except `dunyaya_bak`, `varlik_incele`, `varlik_ara`): if the entity is no longer canon → `ap = 0`,
  `REJECTED: {name} is no longer in the world ({status}); it cannot act. Only speak your saying.`; a named mortal held
  captive may only call `kac` → `REJECTED: {captor} holds you prisoner; you can only try to escape (kac).`
- Results: success text; rejection = `isError` with prefix `REJECTED: ` (old `REDDEDİLDİ:`). The model sees both.
- Number fields: strings like "#12" become numbers; empty/0/"none" in OPTIONAL id fields means absent; a missing
  required number yields `{field} was left empty: this field is required, write a number (for an id, the id from the
  list).`, too small/big/non-integer/non-number errors similarly (old `SAYI_HATA`).
- Enum fields are "flexible" (`esnekEnum`): near-miss spellings are mapped to the closest valid value before validation.
- Records not canon → `durumNedeni`: dead `#{id} {name} is dead (died in Age N); this cannot be done to the dead.`; destroyed
  `… was destroyed (Age N); it is no longer in the world.`; rejected `… was rejected by Fate; it counts as never having
  existed.`; fulfilled `… has been fulfilled; it is no longer a pending prophecy.`; other `… is currently {status}; this cannot
  be done to it.`; missing id `#{id}: no such record.`; null `No record chosen: write an id from the list.`
- Common helpers: `ap(n=1)` → `Your actions for this age are used up; speak your saying and finish.` if `ctx.ap < n`.
  "Name taken" check (`isimAlinmis`) → `This name is taken.` Creation power `guc(me) = clamp(round(me.power *
  OLUMLU_ARAC.creation_power_pct/100), 1, OLUMLU_ARAC.creation_power_cap)`.
- `yarat(me, {...})` (create helper): inserts an entity with `kaynak='olumlu'`, `yapan_id = me.id`, subtype normalised
  (`altTurDuzelt`; default = lowercase type name), description cleaned (`anlatiTemizle`), stats filled by type defaults
  (`fillStats`; named mortals also get age via `olumluYasi`), image prompt passed through `promptDuzelt`; location bond
  `icinde`; id pushed to `ctx.yaratimlar`.
- "Near" (`yakinMi`): same top region, or neighbouring regions on the map; with seafaring known by either side (and no
  `deniz_yasagi` law in the actor's world) two steps away. "Same region" (`ayniBolge`) requires both top regions known.
- Per-age counters: rejected with `{message} (World rule OLUMLU_ARAC.{key} = {n}).` when reached.
- Free vs. costly: a tool is free iff its description matches /Free|costs no action/ and does not contain "N action(s)".

**Tunables (mortal agent config) — `OLUMLU_AJAN`** (hard-coded object in rules.js; NOT tunable in the old app — make
these rules): `default_count` (varsayilan) 4, `ap` 3, `max_turns` (maxTurns) 12, `types` (turler)
`[halk, hizip, tarikat, yerlesim, olumlu, tur]`, `intelligence_threshold` (zeka_esigi) 55.

---

### Mortal tool catalogue (MCP server `olumlu`)

Format per tool: Turkish name / English name — availability (by actor type) — cost — description (model-facing, full
English) — input schema — validation (in order, with rejection text) — effect. "1 action" = `ctx.ap -= 1`. Chronicle
entries are type-tagged; ids in brackets are the linked entities. Actor = `me`. Community types = `halk` (people),
`hizip` (faction), `yerlesim` (settlement), `tarikat` (cult).

### Read tools (free; not ledgered; not gated)

**dunyaya_bak / look_at_world** — all. Description: "Shows your land, those near you, your language, what you know, what
you own and recent events more widely than the prompt. Free." Input `{}`. Effect: returns `mortal.context(me, {tam:true})`.

**varlik_incele / inspect_entity** — all. "Shows the details of an entity. Free." Input `{id: int}`. Returns
`varlikDetay(id)` (entity line; creator; age; world; domain; tags; stats; description; history; Fate note marked "writing
note; not carried into narrative"; bonds; contents; lexicon for languages; society lines; canon facts "do not violate")
or the non-canon/missing reason, else `None.`

**varlik_ara / search_entities** — all. "Searches entities. Free." Input `{query: string}`. Returns entity lines or `No results.`

### dil_kur / found_language — all — 1 action
Description: "You give birth to your own language: its name, kind (spoken language, sacred language, script, sign
language…), sound structure and first words. From now on you speak this language. 1 action."
Input: `name` string 2–50; `subtype` ≤60 optional; `description` 80–900 ("Its sound structure, its script, who speaks it,
what is forbidden to say"); `words` WordList; `image_prompt` ≤900 optional ("English photoreal prompt: an object showing
this script/language, e.g. carved tablet, manuscript, inscription, with lighting and camera" + image rules).
WordList (`KelimeSchema`): array 1–40 of `{word 1–40, meaning 1–200, type? enum(noun, verb, adjective, suffix, title, place
name, proper name, interjection, number), origin? ≤240 ("Etymology: from which event or which words it derives"), example?
≤240 ("Short usage example and its translation")}`.
Validation: ap; name taken.
Effect: if actor is a named mortal (`olumlu`): parent language = the language it speaks, else the language of a people/
settlement in its top region; if found, subtype becomes `"{parent} dialect{: subtype}"`. Create `dil` with stats
`{spread: parent ? dialect_spread : lang_spread, complexity: lang_complexity, sanctity: lang_sanctity}`, power `guc(me)`.
If parent: bond new → parent `soyundan` "dialect". Deactivate the actor's active `konusur` bonds; add actor `konusur` → new.
Add first `words_per_call` words (author `v`, actor). ap−1. Chronicle `dil`: `{me} gave birth to its own language: {name}.
Its first words: {words}.` [me, lang]. Result `#{id} {name} was born. Actions left: {ap}`.

### kelime_tureti / coin_words — all — free, `words_per_age` times per age
"You add new words to the language you speak (meaning, type, origin). Free, {n} times per age."
Input `{words: WordList}`. Validation: counter `ctx.kelime >= words_per_age` → `You have coined enough words.`; language
non-canon → reason; no language → `You have no language. First dil_kur.` Effect: counter+1; add up to `words_per_call`
words; if any added, chronicle `dil`: `New words were born among {me} ({language}): {words}.` Result `Added: …` or `No new words.`

### uret / produce — all — 1 action
"You produce an item from resources you own or that lie on your land: weapon, armour, shield, tool, jewellery, sacred
relic. The resources' abundance decreases; quality depends on your craft and the resources' might. 1 action."
Input: `name` 2–60; `category` enum(weapon `silah`, armour `zirh`, shield `kalkan`, tool `arac`, jewellery `taki`, sacred
relic `kutsal emanet`, instrument `calgi`, book `kitap`); `subtype` ≤60 optional ("e.g. bone spear, salt armour");
`description` 100–1000; `resource_ids` int[1..produce_resources_max]; `owner_id` int optional ("Who will carry the item (a
mortal or you); if empty, you"); `image_prompt` optional.
Validation: ap; name taken; each resource: exists (`One of the resources does not exist.`), canon, type `kaynak`
(`{name} is not a resource.`), owned by me OR in my region (`{name} is not on your land and you do not own it. Acquire it by
trade or conquest.`), abundance `>= produce_abundance_min` (`{name} is about to run out (abundance N).`).
Formula: `craft = me.craft ?? wealth ?? reason ?? intelligence ?? prosperity ?? influence ?? stat_default`; `might = avg(resource.might)`;
`met = knows metallurgy ? produce_metallurgy : 0`; `mag = (knows magic ? produce_magic : 0) + round(region.magic / produce_region_magic_div)`.
Weapon damage `clamp(craft*produce_craft% + might*produce_might% + d(produce_die) + met, produce_min, 100)` (non-weapon:
`d(produce_side_die)`); shield/armour protection same formula (others `d(produce_side_die)`); might
`clamp(might*produce_might_ratio% + d(produce_might_die) + mag)`; curse `clamp(d(produce_curse_die) - produce_curse_minus)`.
Effect: create `esya` (item), subtype `"{category label}: {subtype}"` or label, tag `[category]`, location = me if settlement
else my location. Per resource: bond item `kaynagi` (source) → resource; abundance −= `produce_abundance_loss`. Bond me
`uretti` (made) → item; owner = `owner_id` if canon else me, bond owner `sahip` → item. ap−1. Chronicle `uretim`:
`{me}, using {r1} and {r2}, produced {name} ({category}; masterwork|sturdy|crude).` where damage+protection `>= produce_master`
→ masterwork, `>= produce_sturdy` → sturdy. Result `#{id} {name} produced. Damage D, protection P, might M. Actions left: N`.

### insa_et / build — all — 1 action
"You build a monument: temple, tower, wall, bridge, monument, tomb, mine, harbour, library. It can be dedicated to a god. 1 action."
Input: `name`, `subtype?`, `description` 100–1000, `location_id?` ("Your own settlement, place or region; if empty, where you
are"), `dedicated_son_id?`, `image_prompt?`.
Validation: ap; name taken; location = given or (me if settlement else my location); non-canon reason; location type must be
`bolge|yer|yerlesim` and canon (`Invalid location.`); must be same region as me or be me (`You can only build on your own land.`).
Effect: create `yapit` (monument) with `splendour = clamp(craft*build_splendour% + d(build_splendour_die) + (architecture? build_architecture:0))`,
`sturdiness` likewise with `build_sturdiness`, `function = clamp(build_function_base + d(build_function_die))`, power guc(me),
location. Bond me `insa_etti` → it; if dedicated son exists and not dead: bond monument `tapar` (worships) → son "offering".
Actor's prosperity and wealth (if present) −= `build_cost`. ap−1. Chronicle `insa`: `{me} built {name} in {location}{ ({subtype})}{; dedicated to {son}}.`

### kultur_yarat / create_culture — all — 1 action
"You give birth to a tradition of your community (festival, taboo, funeral rite), a legend, a work of art (song, statue,
fresco, book, play; by honouring your god it strengthens him) or a law (statute, penalty, custom; a just law reduces
rebellion). 1 action."
Input: `kind` enum(tradition `gelenek`: rite/festival/taboo · legend `efsane`: a tale · work `eser`: song, statue, fresco,
book, play · law `kanun`: statute, penalty, custom); `name`; `subtype?`; `description` 100–1000; `related_ids?`
int[≤culture_related_max]; `image_prompt?` ("English photoreal prompt: the ritual being performed or a scene of the legend").
Validation: ap; name taken. Stats: work `{fame: work_base+d(work_die), influence: same}`; law `{rigidity: law_rigidity_base+d(..),
justice: law_justice_base+d(..)}`; tradition/legend `{spread: tradition_spread, rigidity: tradition_rigidity}`. Location (work/law
only) = me if settlement else my location. Effect: create; bond me → it: tradition `kutlar` (celebrates), law `yonetir` (governs),
work `uretti`, legend `anlatir` (tells). If work and actor has a god: bond work `anlatir` → son "tells of its god". Each existing
related id: bond it `anlatir` → related with description `subject of the {kind}`. ap−1. Chronicle `kultur`:
`A new {kind} was born among {me}: {name}.`

### kaynak_kesfet / discover_resource — all — 1 action, `discovery_per_age` per age
"You discover a new resource on your land (ore vein, healing herb, sacred spring, bone bed…) and own it. 1 action, {n} per age."
Input: `name`, `subtype?`, `description` 80–800, `location_id` ("Your own region or a place in your region"), `domain?` ("One of:
{domains}"), `image_prompt?`.
Validation: ap; counter `kesif`; name taken; location must be canon `bolge|yer` in my region (`You can only make discoveries in your own region.`).
Effect: create `kaynak` stats abundance/value/might = `discovery_*_base + d(discovery_*_die)`, domain mapped (`alanEsle`, default
"Earth"), location. Bond me `sahip` → it "discovered". ap−1; counter+1. Chronicle `kesif`: `{me} discovered {name} in {location}{ ({subtype})}.`

### sahiplen / claim — all — free, `claim_per_age` per age
"You claim an ownerless resource on your land. If you take someone else's resource, enmity is born between you. Free, {n} per age."
Input `{resource_id}`. Validation: counter; record exists/canon; type resource (`This is not a resource.`); in my region
(`The resource is not on your land.`); not already mine (`It is already yours.`).
Effect: previous owners = entities with active `sahip` → resource. Deactivate those bonds with description `{me} seized it (Age N)`.
Bond me `sahip` → resource. For each previous owner that is a community: try `savasIlan(owner, me, "because of {resource}")`
(war rules: caps, truce, governance/tribute); if war cannot be declared and I am a community: community relation(owner, me)
−= `seize_relation`. Counter+1. Chronicle `kaynak`: `{me} claimed {resource}{; {first liste_ad owners}{ and N more communities} were angered by it}.`

### yerlesim_kur / found_settlement — people, faction, cult — 1 action
"You split off a branch of your population (or your disciples) and found a new settlement (village, fortress, harbour, monastery,
camp); those who migrate leave you. In your own region or a neighbouring region. 1 action."
Input: `name`, `subtype?`, `description` 100–900, `location_id`, `image_prompt?`.
Validation: ap; name taken; location canon `bolge|yer` and near (`You can only settle in your own or a neighbouring region.`);
key = population if present else disciples else reject (`You have no population or disciples to migrate; only a branch splitting off
from your own people founds a new settlement.`).
Formula: floor = disciples ? `murit_floor` : people ? `SINIR.halk_nufus_taban` : `SINIR.nufus_taban`; `available = max(0, floor(stat - floor))`;
`min = max(migrate_min, SINIR.nufus_taban)`; `migrants = min(available, SINIR.kent_nufus_tavan, max(min, round(stat*migrate_pct/100)))`;
if `migrants < min` → `At least {min} people must migrate for a new settlement (World rule OLUMLU_ARAC.goc_en_az); {available} {people|disciples} can leave you.`
Effect: stat −= migrants; create `yerlesim` stats `{population: migrants, prosperity: new_town_prosperity, defence: new_town_defence,
faith: new_town_faith}`, power `max(1, guc(me)-1)`. Bonds: me `gocetti` (migrated) → it "{n} people"; it `soyundan` → me; it `konusur` → my
language; it `tapar` → my god son. ap−1. Chronicle `goc`: `{n} people from among {me} migrated and founded {name} in {location}.`

### ticaret_kur / establish_trade — all — 1 action
"You establish trade with a community nearby or in a neighbouring region; the prosperity of both of you increases. 1 action."
Input `{target_id, goods: string 5–200 ("What you give and what you take")}`.
Validation: ap; non-canon; target canon community, not me (`Invalid partner.`); near (`This community is too far; you can only trade
with those in your own or a neighbouring region.`); not enemies (`No trade with your enemy.`); not already trading (`You are already trading.`).
Effect: bond me `ticaret` → target (description = goods); community relation += `trade_relation`. ap−1. Chronicle `ticaret`:
`Trade began between {me} and {target}: {goods}.` (Prosperity gain is applied by the economy engine from trade bonds.)

### savas_ilan_et / declare_war — all — 1 action
"You declare war on a community or a creature. The flow of the world resolves the war; your weapons and your god lend you strength. 1 action."
Input `{target_id, reason: 10–300}`.
Validation: ap; non-canon; target canon community or species (`tur`), not me (`Invalid target.`); near (`This target is too far.`);
already enemies (`You are already at war.`); for non-species: active truce (`There is an ongoing truce between you; war cannot be
opened before it expires.`) or governance/tribute bond either way (`There is a governance or tribute bond between you; that bond must
break first.`).
Effect: deactivate trade bonds both ways; bond me → target `avlar` (hunts) for species else `dusman` (enemy) with reason;
non-species: community relation −= `war_relation`. If both have different patron sons: son relationship −= `war_patron_relation`.
ap−1. Chronicle `savas`: `{me} declared war on {target}: {reason}`. (War resolution: engine.)

### tapin / worship — all — free, `worship_per_age` per age
"You worship a god (a son) or change your god; if you give son_id 0 you worship the creator god directly, the father of all the
sons. Your old god does not forget this. Free, {n} per age."
Input `{son_id: int (0 = creator), offering: 10–300}`.
Validation: counter; `son_id == 0`: `yaraticiyaTapin(me, offering, age)` (creator module) false → `You already worship the creator.`;
else son must exist (`No such god.`), not dead (`{son} is dead; he can only be worshipped by awaiting his resurrection.`), not
already worshipped (`You already worship {son}.`).
Effect (creator): counter+1; chronicle `tapinma`: `{me} began to worship the creator {creator} directly: {offering}`; result
`You now worship the creator. You may keep worshipping one of the sons as well.`
Effect (son): old = current patron son; oldForeign = foreign patron; deactivate all active `tapar` bonds from me to sons or
foreign gods; oldForeign attitude −= `worship_foreign_attitude` (min −100); bond me `tapar` → son (offering); remove tag
`tanrısız` (godless); if old son ≠ new: son relationship(old, new) −= `worship_relation`. Counter+1. Chronicle `tapinma` (son = new):
`{me} worshipped {son}{; abandoned {old}}: {offering}`.

### yaraticiya_dua / pray_to_creator — all — free, `prayer_per_age` per age
"You pray directly to the creator god above the sons, the father of all worlds. Your prayer reaches him; if he answers you will see
it in your dream and his grace will descend. Free, {n} per age."
Input `{prayer: 15–500, request?: ≤200 ("What you ask of him")}`. Effect: counter+1; `olumluDuasi(me, prayer, request, age)` (creator
module: stores the prayer for the player). Result `Your prayer rose to the sky. If the creator hears, you will know in your next dream.`

### bilgi_gelistir / develop_knowledge — all — 1 action
"Your community develops a new piece of knowledge (a technology, craft, school or method). Branch: {key (effect); …}. If it is built
on knowledge you already have it is stronger. 1 action."
Branches (`BILGI_DALLARI`): farming (knowers' population grows 50% faster; famine and drought strike at half strength); metallurgy
(+15 damage/protection to their weapons and armour); seafaring (trade, war and migration with communities beyond the sea); writing
(their languages grow complex; their knowledge spreads to partners twice as fast); architecture (+20 splendour and sturdiness to their
monuments; earthquake resistant); medicine (plagues strike at half strength; mortals' lifespan +20); magic (magic stat +10; items they
make +10 might); art of war (+12 war strength); astronomy (they read the star of the age: sense disasters in advance, suffer them at half
strength); trade (double prosperity from trade routes); sky-sailing (can discover routes between worlds; risk of getting lost on journeys
halved); shipbuilding (can build inter-world ships); gate lore (can open and close ancient gates; gate routes take one age); path-knowing
(can fold space: with the cosmic resource routes shrink to one age); void-living (can found colonies on worlds with thin or no
atmosphere; fewer losses on journeys); pursuit of immortality (their mortals reach for immortality; the successful do not age but the gods
see them as a threat); biomagic (joins and changes living things: can weave chimeras, steer mutations); forbidden knowledge (great power:
war +15, magic +15, forces gates. Price: knowers' sanity drops every age, leak flows into their world; Fate watches).
Input: `name` 2–60 ("A name from your own language"); `branch` enum(keys above); `description` 100–900 ("What it is, how it was found,
which material or observation it rests on"); `base_ids?` int[≤knowledge_base_max] ("Knowledge you know that it is built on");
`resource_id?` ("The resource it relies on"); `image_prompt?` ("English photoreal prompt: people practicing this technique, tools,
materials, setting").
Validation: ap; name taken. Formula: bases = given ids that I know; `level = clamp(1 + max(base.level) + (craft > knowledge_craft_threshold ? 1 : 0), 1, knowledge_level_cap)`.
Effect: create `teknoloji` subtype = branch name lowercase, stats `{level, spread: knowledge_spread}`, power `clamp(level, 1, creation_power_cap)`,
tag `dal:{branch}`; bonds new `soyundan` → each base "built upon"; new `kaynagi` → resource if a resource; teach me
(`ogret(me, id, age, 'developed')`). ap−1. Chronicle `bilgi`: `{me} developed new knowledge: {name} ({branch}, level {level}).`

### ogren / learn — all — free, `learn_per_age` per age
"You learn a piece of knowledge known by your trade partner, ally or neighbour. Free, {n} per age."
Input `{knowledge_id, from_id}`. Validation: counter; non-canon; both canon and knowledge is `teknoloji` (`Invalid: both the teacher and
the knowledge must be in the world.`); teacher knows it (`{from} does not know this.`); `ogrenebilirMi` (trade, alliance or governance bond,
or same region) (`There is no trade, alliance or neighbourhood between you and {from}.`); `ogret` false → `You already know it.`
Effect: counter+1; chronicle `bilgi`: `{me} learned {knowledge} from {from}.`

### diplomasi / diplomacy — all — 1 action
"Diplomacy with another community: alliance (stands with you in war), peace (tries to end enmity), tribute (demands wealth from the
weak) or marriage/blood bond (unites the lineages). 1 action."
Input `{target_id, kind: enum(alliance ittifak, peace baris, tribute harac, marriage evlilik), terms: 10–300}`.
Validation: ap; non-canon; target canon community or named mortal, not me (`Invalid target.`); near (`Too far.`); alliance/marriage with
an enemy → `No alliance with your enemy; first peace.`; peace without enmity → `You are not enemies.` (invalid offers burn no action).
Formula: `rel = community relation if target is community else 0`; `roll = d(100) - round(rel / diplomacy_relation_div)`;
strength(x) = `(strength ?? warlike ?? defence ?? diplomacy_strength_default) + log10(max(10, population|disciples|100)) * diplomacy_pop_mult`.
ap−1 then:
- alliance/marriage: `roll <= alliance_threshold` → bond me `muttefik` → target "{kind}: {terms}", relation += marriage ? `marriage_relation` : `alliance_relation`, result `{target} accepted`; else relation −= `refusal_relation`, `{target} refused`.
- peace: `roll <= peace_threshold` → deactivate enemy bonds both ways, relation += `peace_relation`, `peace was made`; else `the peace offer was turned down`.
- tribute: if `strength(me) < strength(target) * tribute_superiority/100` → bond target `dusman` → me "insolence of tribute", relation −= `tribute_refusal_relation`, `{target} laughed and became your enemy`; else for wealth and prosperity: target −= `tribute_loss`, me += `tribute_gain` (clamped 0–100), bond target `harac_oder` (pays tribute) → me (terms), relation −= `tribute_relation`, `{target} agreed to pay tribute`.
Chronicle `diplomasi`: `{me} offered {kind} to {target}: {outcome}.` (terms text deliberately not in the chronicle). Result `{outcome}. Actions left: N`.

### maceraya_cik / go_on_adventure — named mortal only — 1 action
"You embark on an adventure: hunting a dangerous creature (the flow of the world resolves the fight at the end of the age; your weapons
count) or seizing an item from someone else's hands (your agility and reason against its owner's defence). 1 action."
Input `{target_id ("The species to hunt or the item to seize"), goal: 10–300}`.
Validation: ap; non-canon; canon (`The target is not in the world.`).
- species: near (`This creature is too far.`) → bond me `avlar` → species (goal); ap−1; chronicle `macera`: `{me} set out to hunt {species}: {goal}`; result `You set out. The fight will be resolved at the end of the age.`
- item: owner = active `sahip` source; owner is me → `It is already yours.`; owner not near → `The item's owner is too far.`; ownerless item must be in my world and near (`This item is too far; you can only seize an ownerless item in your own or a neighbouring region.`). `p1 = (agility || stat_default) + (reason || stat_default)/2 + d(adventure_die)`; `p2 = (owner.defence ?? owner.strength ?? stat_default) + d(adventure_die)`. ap−1. If `p1 >= p2`: deactivate owner bond; bond me `sahip` → item "seized: {goal}"; if owner: bond owner `dusman` → me "{item} was stolen"; chronicle `macera`: `{me} seized {item}{ from {owner}}: {goal}`; result `{item} is now yours ({p1} – {p2}).` Else me.hp = clamp(hp − adventure_wound, 1, SINIR.can_tavan); chronicle `{me} tried to seize {item} but was wounded and fled.`; result `You failed ({p1} – {p2}); you were wounded.`
- other → `The adventure target must be a creature species or an item.`

### rota_kesfet / discover_route — all — 1 action (async)
"You search for the way to another world. The way you find depends on what you know: gate lore an ancient gate, sky-sailing a sail
route, path-knowing folding, magic a dream road. Rarely you may discover a world no one has known. 1 action."
Input `{how: 10–300 ("How you search for the way: observation, sacrifice, dream, old maps…")}`.
Validation: ap; route method (`yolYontemi`: gate lore → gate, path-knowing → folding, sky-sailing → sail, a tamed flying/megafauna
mount → mount, magic → dream; else) → `To search for the way to other worlds you must know sky-sailing, gate lore, path-knowing or magic (ogren or bilgi_gelistir).`
Effect: ap−1; in its own transaction `yolAra(me, {how, age, create})`: from a forgotten world → none; unknown targets = known/legendary
worlds without a known active route from mine; `roll = d(100) + (reason ?? influence ?? stat_default)/route_reason_div`; if targets and
`roll >= route_threshold`: pick a random target; for gate method create an `arac` "{me} Gate" (subtype ancient gate, stats speed
`gate_speed`, range `gate_range`, crew 0, armour `gate_armour`, strangeness `gate_strangeness+d(..)`, power `gate_power`); open route
(`rotaAc`, travel module) and chronicle `kesif` with the text `{me} found a way to the world {target}: {method} ({n} ages).` → result
`Way found: route#{id}, {method}, {n} ages, danger {d}. You can now set out with sefere_cik.`. Else if `roll >= unknown_threshold` and
fewer than `unknown_world_per_age` worlds were born this age (incl. pending intuitions) → **intuition**: `await sezgiyiDogur` (LLM world
birth with mortal inspiration; opens a route; on route failure the world becomes `efsane` (legend); chronicle `{me} discovered a world no
one knew: {world}.{ But its way was lost in mist; the world is remembered only as a legend.}`) → result `You discovered an unknown world:
{world}. You can go there by route#{id}.` or `You sensed the existence of an unknown world: {world}; but its way could not be held.`
(errors swallowed). Otherwise chronicle `kesif`: `{me} searched for the way to other worlds ({how}) but did not find it.`; result
`No way found; the sky was silent this age.`

### toprak_kesfet / explore_land — communities and named mortals, if `KESIF.arac_tur > 0` — 1 action, `KESIF.arac_tur` per age
"You set out to explore beyond the known lands: you find either a new region not on the map (valley, plateau, island, coastline, inland
sea) or, in your own or a neighbouring region, a place no one has set foot on (cave, lake, pass, forest, well). Success depends on your
reason (your craft if you are a community) and your path knowledge (seafaring, path-knowing, astronomy). If you are a community your
pioneers can settle there and found a new settlement. 1 action, {n} per age."
Input: `kind` enum(region `bolge`: new lands not on the map; place `yer`: a new place in your own or a neighbouring region); `name` 2–60
("An original proper name; fitting your language's naming rule"); `subtype?` ("valley, island, cave, lake, pass…"); `description` 100–900
("What you found, how you found it, what the first to set foot there saw"); `location_id?` ("Only for a place: the region it lies in (your
own or a neighbouring one); if empty, your own region"); `settle?` boolean ("If you are a community, your pioneers settle there and found a
new settlement"); `image_prompt?`.
Validation: ap; counter (`You already went exploring this age (World rule KESIF.arac_tur = N).`); name taken; similar name (`"{name}" is too
similar to the existing name "{other}"; choose another name.`); place: parent region canon and near (`A new place can only be found in your
own or a neighbouring region.`).
Effect: ap−1, counter+1; `roll = d(100) + (reason ?? craft ?? stat_default)/route_reason_div + (knows seafaring/path-knowing/astronomy ?
KESIF.arac_bilgi_ek : 0)`; if `roll < KESIF.arac_esik`: chronicle `kesif` `{me} set out into unknown lands but the road turned them back
empty-handed.`; result `The exploration came to nothing; you found no new land this age (roll R, needed T).` Else (transaction): create the
region/place with `toprakStatlari(kind)`, power guc(me), tag `keşif`; a new region is placed on the map (`bolgeyiYerlestir`); bond me
`kesfetti` → it; if settle and actor is people/settlement: `onculer` (pioneers found a settlement; exploration module); chronicle `kesif`:
`{me} set out into unknown lands and found {a new region not on the map | a new place in {parent}}: {name}{; its pioneers founded {settlement} there}.`;
result `#{id} {name} discovered{; your pioneers founded #{sid} {settlement} | ; but you are not numerous enough to settle}.`

### dirilis_ayini / resurrection_rite — communities and named mortals that worship a dead son; if `OLUM.ayin_tur > 0` — 1 action, per age `OLUM.ayin_tur`
"You perform a rite for your dead god's return: prayer (+{dua_adanmislik} devotion), wealth offering ({servet_bedel} from your wealth,
prosperity or craft; +{servet_adanmislik}), blood sacrifice ({kurban_nufus}% of your population; +{kurban_adanmislik}) or life sacrifice (a named
mortal offers itself or your people offer it; +{can_kurbani_adanmislik}). A rite held in the region where your god's bones lie counts
{hac_carpan/100} times. When devotion is full the resurrection rite may succeed. 1 action, {n} per age."
Input `{son_id ("The dead god's (son's) id"), kind: enum(prayer dua, wealth servet, blood kan, life can), victim_id? ("The named mortal
offered in a life sacrifice (if empty, yourself if you are a mortal)")}`.
Validation: ap; counter (`You already performed a rite this age (World rule OLUM.ayin_tur = N).`); son among dead gods I worship (`You can
only perform a rite for a dead god you worship.`); `dirilisAyini` errors (death module) returned as rejections. Effect: ap−1, counter+1;
result = rite text + actions left.

### gemi_yap / build_ship — people, settlement, faction — 1 action
"You build an inter-world ship (requires shipbuilding knowledge). Its power depends on your craft, your mining and your metallurgy. 1 action."
Input `{name, subtype? ("light-sail, bone-hulled, generation ship…"), description 60–800, image_prompt?}`.
Validation: ap; knows shipbuilding (`Shipbuilding knowledge is required.`); name taken.
Formula: `craft = (craft ?? wealth ?? stat_default) + society.economy.mining / ship_mining_div + (metallurgy ? ship_metallurgy : 0)`; stats speed
`clamp(ship_speed_base + craft/ship_speed_div + d(ship_speed_die))`, range `clamp(ship_range_base + d(ship_range_die))`, crew `ship_crew_base +
d(ship_crew_die)`, armour `clamp(ship_armour_base + craft/ship_armour_div + d(ship_armour_die))`, strangeness `d(ship_strangeness_die)`.
Effect: ap−1; create `arac` subtype `ship{: subtype}`; bond me `sahip` → it "built in its shipyard"; society mining −= `ship_mining` (min 0).
Chronicle `uretim`: `{me} built an inter-world ship: {name}.` Result `Ship ready: #{id} {name}.`

### sefere_cik / set_out_on_expedition — all — 1 action
"You organize an expedition to another world along a known route: to found a colony, open trade, explore, conquer or go on pilgrimage.
The journey may take several ages; on the way there may be pirates, storms, creatures and disappearance. 1 action."
Input `{route_id, intent: enum(colony koloni, trade ticaret, exploration kesif, conquest fetih, pilgrimage hac), percent?: int 1..expedition_pct_max
("What percent of your community sets out (for colony/conquest); default {expedition_pct}"), vehicle_id? ("The ship or vehicle to use")}`.
Validation: ap; route among known routes of my world (`There is no such known route out of this world.`); `rotaKullanabilir` (travel module)
message; already travelling (`You already have an expedition under way.`); vehicle must be my `arac` (`This vehicle is not yours.`); if the route
method needs a ship and none given, auto-pick my first owned canon vehicle. People = population ? `round(pop * min(max_pct, pct)/100)` :
disciples ? `round(disciples*pct/100)` : 1; colony/conquest with fewer than `expedition_min` → `You are not numerous enough for a colony or a conquest.`
Effect: ap−1; `yolculukBaslat` (travel module; creates a journey row, removes people). Chronicle `sefer`: `{me} set out on a {intent} expedition
to the world {destination} ({n} people{, with {vehicle}}, it will take {k} ages).` Result `You set out: you will arrive in {k} ages.`

### evcillestir / tame — people, settlement, named mortal, faction — 1 action
"You try to tame a creature species on your land. If you succeed it serves you in war, transport and trade; flying or gigantic ones can carry you
between worlds. Dangerous and intelligent species are hard. 1 action."
Input `{species_id, how: 10–300}`. Validation: ap; non-canon; canon species (`No such living species.`); same region or near (`This species is not on
your lands.`); already tamed (`You already tamed it.`).
Formula: `skill = (craft ?? reason ?? stat_default) + (charisma ?? 0)/tame_charisma_div + d(tame_die)`; `difficulty = (danger || tame_danger_default) /
(tame_danger_div/100) + (intelligence || tame_intelligence_default)/2 + (megafauna ? tame_megafauna : 0) + d(tame_hard_die)`.
Effect: ap−1; success (`skill >= difficulty`): bond me `evcil` (tamed) → species (how); chronicle `evcillestirme` `{me} tamed {species} ({how}).`; result
`{species} now serves you.` Failure: with probability `(danger || default)/tame_rage_div` population and hp of me ×`(100 - tame_loss)/100` (clamped 1..SINIR.nufus_tavan)
and bond species `avlar` → me "enraged by the taming"; chronicle `{me} tried to tame {species} but failed.`; result `{species} did not submit.`

### kimera_dok / merge_species — all — 1 action
"With biomagic you merge two creature species in your world, near you (at most {YARATIK.kimera_dokuma_mesafe} steps), into a single chimera (requires
biomagic knowledge). The chimera carries the traits of both species; but it may get out of control. 1 action."
Input `{a_id, b_id, name, goal: 10–300}`. Validation: ap; knows biomagic (`To weave a chimera you must know biomagic.`); two distinct canon species
(`Choose two separate living species.`); each in my world (`{x} is in another world; you can only weave species in your own world.`) and
`mesafe(me, x) <= YARATIK.kimera_dokuma_mesafe` (`{x} is too far (World rule YARATIK.kimera_dokuma_mesafe = N steps).`); name taken.
Effect: ap−1; `kimeraDok(A, B, {age, name, weaver: me, description: "{me} joined {A} with {B} by biomagic: {goal}"})` (creature module); bond me
`evcil` → chimera "woven by itself"; chronicle `kimera`: `{me} wove a chimera from {A} and {B}: {chimera}.` Result `A chimera was born: #{id} {name}.
Its traits: {traits | none}.`

### ruh_kapla / bind_spirit — all — 1 action
"With magic you bind a free spirit in your own or a neighbouring region to an item, ship or monument there (requires magic knowledge). The item becomes
ensouled; bound to a monument, stone walks and a golem is born. 1 action."
Input `{spirit_id, target_id}`. Validation: ap; knows magic or biomagic (`To bind a spirit you must know magic.`); spirit exists but not canon →
`No such free spirit: #{id} {name} is no longer free (it was bound to something or faded).`; not a canon `ruh` → `No such free spirit.`; target canon
`esya|arac|yapit` (`A spirit can only be bound to an item, vehicle or monument standing in the world.{ reason}`); both in my world and near (`{x} is too far;
you can only join a spirit and an item in your own or a neighbouring region.`).
Effect: ap−1; `ruhKapla(spirit, target, me, age)` (beyond module); on exception ap+1 and reject. Result `The spirit was bound{; a golem was born: #{id}}.`

### kalinti_ara / search_ruins — all — 1 action
"You search a ruin, a remnant or the bones of a dead god on your land: you may find lost knowledge, an ownerless item, or awaken something sleeping. 1 action."
Input `{target_id ("The id of a place that is a ruin, remnant or god's corpse"), how: 10–300}`.
Validation: ap; target has a tag in (ruin `harabe`, god corpse `tanrı cesedi`, empty tomb `boş mezar`) or subtype matching ruin/remnant/wreckage/tomb/corpse,
and is not rejected/destroyed (`This is not a ruin or remnant.`); same world and same region or near (`Too far.`).
Formula: `reason = (reason ?? influence ?? stat_default) + society.classes.scribe * ruin_scribe + d(ruin_die)`; lost = canon technologies tagged `kayıp`
(lost) in the ruin's world; items = ownerless canon items located in the ruin.
Effect: ap−1; if `reason >= ruin_knowledge_threshold` and lost exists: random one taught to me ("found in the ruins of {ruin}"), tag `kayıp` removed;
chronicle `{me} rediscovered the forgotten knowledge {k} in the ruins of {ruin}.`; else if `>= ruin_item_threshold` and items: bond me `sahip` → first item;
chronicle `{me} found and took {item} in the ruins of {ruin}.`; else if `< ruin_curse_threshold`: tag me `lanetli` (cursed); chronicle `{me} awakened something
sleeping while digging the ruins of {ruin}; a curse settled upon it.`; else chronicle `{me} searched the ruins of {ruin} but found nothing but dust, bone and
whisper.` (all type `kesif`). Results in second person, e.g. `You found the forgotten knowledge {k} in the ruins of {ruin}.`

### sabotaj / sabotage — faction, cult, named mortal — 1 action
"You secretly harm a community: poison (population/hp decreases), arson (prosperity, defence, wealth decrease) or discord (you break off one of its allies from
it). If you are caught you become enemies. 1 action."
Input `{target_id, kind: enum(poison zehir, arson kundak, discord nifak), how: 10–300}`.
Validation: ap; non-canon; target canon community or named mortal, not me (`Invalid target.`); near (`Too far.`).
Formula: `cunning = (reason ?? influence ?? impact ?? stat_default) + d(sabotage_die)`; `watch = (target.defence ?? target.reason ?? stat_default) + d(sabotage_die)`;
`caught = watch > cunning + sabotage_caught`.
Effect: ap−1. If `cunning >= watch`: poison: population and disciples ×`(100 - poison_pop)/100` (clamp 1..), hp −= `poison_hp` for non-mortals; for a named
mortal `olumluYarala(target, poison_hp, {cause:'died of poisoning', killer: caught ? me : null})`, death → note `the poison worked; {target} died`; arson: prosperity,
defence, wealth −= `arson`; discord: deactivate one active ally bond of the target, note `the alliance between {target} and {other} dissolved` or `there was no
alliance to break`. Else note `the sabotage failed`. If caught and not already enemies: bond target `dusman` → me "{kind} caught", note `; and you were caught`;
caught between two communities: relation −= `sabotage_relation`. Chronicle `entrika`: caught → `{me} plotted {kind} against {target} and was caught: {note}.`,
else `A mysterious {poisoning|fire|split} happened within {target}.` (only target linked).

### vaaz_et / preach — cult only — 1 action
"You spread your god's word to a neighbouring community; if it takes hold they too worship your god and your disciples increase. It is hard among those who worship
another god. 1 action."
Input `{target_id, sermon: 20–400}`. Validation: ap; have a god son (`You have no god; first worship.`); non-canon; target canon people/settlement/faction/named
mortal and near (`Invalid or distant target.`); target already worships my god (`{target} already worships {god}.`).
Formula: `oldCharisma = (old son ? old.charisma/preach_old_div : 0) + (old foreign ? (foreign.charisma ?? stat_default)/preach_old_div : 0)`;
`chance = preach_base + (me.influence || preach_influence_default)/2 + god.charisma/preach_god_div - oldCharisma - (target.faith || preach_faith_default)/preach_faith_div`.
Effect: ap−1; if `d(100) <= chance`: deactivate target's `tapar` bonds to sons/foreign gods; old foreign attitude −= `worship_foreign_attitude`; remove tag `tanrısız`;
bond target `tapar` → god "by {me}'s sermon"; my disciples ×`(1 + preach_disciples/100)` (clamp 1..SINIR.murit_tavan); if old son: son relationship(old, god) −=
`preach_relation`; chronicle `tapinma` (son=god): `{me} preached and {target} turned to {god}{; {old names} lost a worshipper}: "{sermon}"`. Else chronicle
`{me} preached among {target} but no one listened.`

### tanriya_meydan_oku / defy_god — named mortal only — 1 action
"You stand up to a god (a son): your strength, agility, reason and weapons against his might. If you win the god is wounded, his fame shaken and you become a
legend; if you lose you die or are cursed. 1 action."
Input `{son_id, reason: 15–400}`. Validation: ap; son exists (`No such god.`), not dead (`{son} is already dead; his bones lie in the world.`).
Formula: weapons = Σ over owned items `damage/defy_damage_div + might/defy_might_div`;
`pk = (strength || stat_default) + (agility || stat_default)/2 + (reason || stat_default)/defy_reason_div + weapons + d(defy_die)`;
`pt = son.strength/2 + son.will/2 + son.level*defy_god_level + d(defy_die) + (son has an unlocked 'dokunulmaz' (untouchable) power ? defy_untouchable : 0)`.
Effect: ap−1.
- Win and `pk - pt >= godslayer_margin` and `(son.varlik ?? god_existence_default) < godslayer_existence`: my charisma += `godslayer_charisma`; tags replace `unvan:*` with
  `unvan:Tanrı Katili` + `tanrı katili` (God-slayer); `tanriOlumu(son, age, "killed by the mortal {me}")`; bond me `oldurdu` (killed) → son; chronicle `tanri_savasi`
  (son): `The mortal {me} killed the fading god {son} ({pk} – {pt}): {reason}`; result `You killed the god. You are now "God-slayer"; his brothers and father will not forget this.`
- Win otherwise: wound = `round((KURAL.can_taban + KURAL.can_dayaniklilik/100 * son.endurance) * god_wound/100)`; son hp = max(1, hp − wound), fame −= `god_wound_fame`;
  my charisma += `god_wound_charisma`; title tag `unvan:{son}'i Yaralayan` ("Wounder of {son}"); bond son `dusman` → me "defeat: {reason}"; chronicle `The mortal {me} stood up
  to the god {son} and wounded him ({pk} – {pt}): {reason}`; result `You wounded the god. You will be called "Wounder of {son}"; but he will not forget you.`
- Lose and `d(100) <= god_death_chance`: me dead (`olum_cag`, Fate note `Age N: stood up to {son} and died.`), `olumSonrasi` (death aftermath, sim module); chronicle
  `The mortal {me} stood up to the god {son} and died: {reason}`; son fame += `god_crush_fame`; `ap = 0`, `ctx.oldu = true`; result `The god crushed you ({pk} – {pt}). Your story ends here.`
- Lose otherwise: tag `lanetli`; bond son `lanetledi` (cursed) → me "for its insolence"; chronicle `… stood up to the god {son}; was defeated and cursed: {reason}`; result
  `You were defeated and cursed.`

### inkar_et / deny_god — people, settlement, faction, cult — 1 action
"You deny your god: you stop worshipping him and become godless. Your god's existence weakens, and the father of the gods cannot draw strength from godless communities.
1 action." Input `{reason: 15–400}`. Validation: ap; no son, no foreign god and already tagged godless → `You are already godless; you have no god to deny.`
Effect: ap−1; deactivate all my `tapar` bonds to sons/foreign gods; foreign god attitude −= `deny_attitude`, faith −= `deny_faith`; tag `tanrısız`; son existence (`varlik`) −=
`deny_existence` and bond son `dusman` → me "denial: {reason}"; chronicle `inkar`: `{me} denied {son|foreign|the gods} and became godless: {reason}`.

### kehanet_et / prophesy — named mortal, cult — 1 action, `prophecy_per_age` per age
"You make a prophecy: you say something that will happen in the future. If it comes true Fate records it and your reputation (charisma) rises; if it is misread it is
shaken. 1 action, {n} per age."
Input `{name ("The prophecy's name, from your own language"), saying: 40–600 ("The words of the prophecy: imagistic but testable; who or what, and when"), related_ids?: int[≤prophecy_related_max]}`.
Validation: ap; counter; name taken. Effect: create `kehanet` subtype `cult prophecy` | `seer's word`, description `{me} said: "{saying}"{ The saying concerns {names}.} If it comes true
{me}'s word will pass from tongue to tongue; if it comes to nothing its name will be shaken.`, stats `{certainty: clamp(prophecy_certainty + round((reason ?? influence ?? stat_default)/2))}`;
bond me `kehanet_eder` → it; it `kehanet_eder` → each canon related "subject of the prophecy". ap−1; counter+1. Chronicle `kehanet`: `{me} made a prophecy: {name}.` Result
`#{id} {name} was spoken. Fate will remember it if it comes true.` (Fate judges fulfilment; seer charisma ±`KADER.kahin_dogru/kahin_yanlis`.)

### kac / escape — named mortal only — 1 action
"If you are a captive you try to escape your captors; your agility and reason decide. If caught you are wounded. 1 action." Input `{how: 10–300}`.
Validation: ap; captive (`You are not a captive.`). `chance = clamp((agility || escape_default)/2 + (reason || escape_default)/escape_reason_div - (captor.defence ?? stat_default)/escape_defence_div,
escape_floor, max(escape_floor, escape_cap))`. Effect: ap−1; success: deactivate `esir` bonds to me, remove tag `esir`; chronicle `kacis` `{me} escaped from {captor}: {how}`. Failure: hp −=
`escape_wound` (if hp exists); chronicle `{me} tried to escape from {captor} but was caught.`

### fidye_ode / pay_ransom — communities — 1 action
"You pay a ransom to the captors for a captured member of yours (bound to you or a mortal from your land): your wealth or prosperity decreases, theirs increases, the captive returns. 1 action."
Input `{captive_id}`. "My captive" = canon captive with an active `korur|soyundan|yoldas` bond to me, or in my region, or sharing my patron son.
Validation: ap; not mine (`This mortal is not your captive or is not captive.`); captor is me (`{x} is your own captive; ransom is paid only to captors.`); rich enough: wealth
`>= ransom_threshold` or prosperity `>= ransom_threshold + ransom_prosperity_extra` (`You do not have enough wealth for a ransom.`). Effect: ap−1; my wealth/prosperity −= `ransom`, captor's
+= `ransom`; free the captive (deactivate `esir`, remove tag); community relation += `ransom_relation`; chronicle `fidye`: `{me} paid a ransom to {captor} for {captive}; the captive returned home.`

### esiri_kurtar / rescue_captive — communities and named mortals — 1 action
"You try to rescue a captive by force: your strength against the captors' defence. Failure breeds enmity. 1 action." Input `{captive_id, plan: 10–300}`.
Target = my captive, or any captive whose captor is near me (`There is no captive to rescue or the captors are too far.`); captor is me → `{x} is your own captive; you cannot raid yourself.`
`g = (strength ?? warlike ?? stat_default) + d(rescue_die)`; `s = (captor.defence ?? strength ?? warlike ?? stat_default) + d(rescue_die)`. ap−1; `g >= s`: free; chronicle `kurtaris` `{me} rescued
{captive} from {captor}: {plan}`; else bond captor `dusman` → me "raid for {captive}" (if not enemies); chronicle `{me} tried to rescue {captive} but {captor} repelled the raid.`

### ordu_topla / raise_army — communities — 1 action
"You raise an army from your population (or your disciples); the soldiers leave the population (one without population hires mercenaries and pays from its wealth). It joins your ongoing war
and protects you. Its equipment depends on your craft and what you know. One army per community. 1 action."
Input `{name ("The army's name, from your own language"), percent?: number 1–100 ("What percent of the population takes up arms (up to the world-rule cap)")}` default `army_pct`.
Validation: ap; existing army (canon `ordu` tagged `taraf:{me}`) → `You already have an army.`; name taken; key = population | disciples; else mercenary key = wealth | prosperity; none →
`You have no population, disciples, or wealth to hire mercenaries to put under arms.`; mercenary funds `< army_mercenary_cost` → `Your {wealth|prosperity} is not enough to hire a mercenary army
({have} / {cost}; World rule OLUMLU_ARAC.ordu_parali_servet).`
Formula: base = key ? stat : `round((strength || army_strength_default) * army_strength_mult)`; floor = disciples ? `murit_floor` : key ? (people ? SINIR.halk_nufus_taban : SINIR.nufus_taban) : 0;
share = `army_loss/100`; max = key ? (share > 0 ? floor((base - floor)/share) : ∞) : ∞; `soldiers = min(round(base * clamp(pct, 1, army_cap)/100), max, SINIR.ordu_tavan)`; `< army_min` →
`An army needs at least {army_min} soldiers (World rule OLUMLU_ARAC.ordu_en_az); only {n} people can be put under arms. Raise the percent (at most {army_cap}%) or grow.`
Stats: size soldiers, morale `clamp(army_morale + d(army_morale_die))`, equipment `clamp(army_equipment + (metallurgy ? army_metallurgy : 0) + round(craft/army_craft_div))`, experience =
knows war ? `army_experience_war` : `army_experience`. Description: `{me} raised an army of {n}{; it marches for {war}}. {origin} {state}` where origin = population: `The soldiers were taken from
{me}'s own people, from field and workbench.` | disciples: `Disciples fill the ranks; bound by oath before the sword.` | mercenary: `The soldiers are mercenaries; {me} hired them with its wealth.`;
state = `The army is {well-equipped|poorly equipped} (equipment >= 50), its morale {high|broken} (morale >= 50){; those who know war lead it}.` Subtype: cult `holy guard`, faction `mercenary army`, else
`people's army`. Tags `taraf:{me}` + `savas:{warId}` if an ongoing war lists me as party.
Effect: create `ordu`; bond army `korur` → me; if war: army `parcasi` (part of) → war. Key stat = `max(floor, round(stat − soldiers*share))`, or mercenary funds −= `army_mercenary_cost`. ap−1.
Chronicle `ordu`: `{me} called {n} people to arms: {name}.`

### komutan_ata / appoint_commander — communities — free, `commander_per_age` per age
"You appoint a named mortal (bound to you or from your land) at the head of your army; the commander's strength and charisma reflect on the army. Free, {n} per age."
Input `{mortal_id}`. Validation: counter; have an army (`First raise an army (ordu_topla).`); non-canon; canon named mortal (`The commander must be a living, named mortal.`); not captive
(`{x} is captive.`); same region or a `korur|soyundan|yoldas` bond to me (`{x} is not bound to you.`). Effect: deactivate previous `komutan` bonds to the army; bond mortal `komutan` → army;
army morale = `clamp((morale || commander_morale_default) + round((charisma || stat_default)/commander_charisma_div))`; counter+1; chronicle `ordu`: `{mortal} took command of {army}.`

### casus_ag_kur / build_spy_network — faction, cult, named mortal, people, settlement — 1 action
"You build a spy network inside a nearby community: you learn its secrets and gain an advantage in war; if caught, relations sour and war may break out. 1 action."
Input `{target_id, cover: 10–300 ("The spies' cover: merchant, pilgrim, apprentice…")}`. Validation: ap; non-canon; target canon community not me (`A spy network can only be built in a
community.`); near; existing `casus` bond (`You already have a network there.`). Effect: bond me `casus` → target (cover); ap−1; chronicle `entrika` (only target linked):
`Strange faces appeared among {target} ({cover[:80]}).` (Discovery/war effects handled by the engine.)

### takas / barter — communities and named mortals — `barter_ap` actions
"You barter with a community or a named mortal: you give resources, items or vehicles you own and take what it owns (if you want nothing it is a gift). The value of the offer, the relationship
between you and a die decide acceptance; a successful barter warms the relationship. {n} action."
Input `{target_id, give_ids: int[1..barter_max] ("Things you own and will give"), take_ids?: int[≤barter_max] ("Things it owns that you want"), terms: 5–200 ("The barter's words")}`.
Party validation (`tarafGecersiz`): non-canon reason; canon community or named mortal not me (`Invalid party: it must be a community or a named mortal.`); near (`{x} is too far; only with those
in your own or a neighbouring region.`); not enemy (`{x} is your enemy.`). Items: give must be canon `kaynak|esya|arac|yapit` owned by me (`{x} is not yours or cannot be bartered (must be a
resource, item, vehicle or monument).`); take likewise owned by target (`{x} is not {target}'s or cannot be bartered.`); overlap → `The same thing cannot be on both sides.`
Formula: value(x) = `x.value ?? max(0, might, damage, protection, splendour, speed)`; `score = Σgive + round(relation/barter_relation_scale) + d(barter_die)`; `ask = Σtake`.
Effect: ap −= barter_ap; if take non-empty and `score < ask`: relation −= `barter_refusal_relation`; chronicle `ticaret` `{me} asked {target} for {take} in exchange for {give}; {target} found the
offer too little.`; result `{target} turned down the offer ({score} – {ask}).` Else transfer ownership (deactivate old `sahip`, new `sahip` "barter: {terms}") both ways; relation +=
`barter_relation`; chronicle `{me} and {target} bartered: {give} for {take} ({terms}).` or `{me} gave {give} to {target} as a gift ({terms}).`

### borc_ver / lend — communities and named mortals — `debt_ap` actions
"You lend to a community or a named mortal: the amount, what is lent and the term (how many ages until repayment). The amount is deducted from your wealth or prosperity and passes to it (if you have
no wealth or prosperity you cannot lend; at most {debt_cap}, term at most {debt_term_cap} ages). Nobody collects; but if it is not paid on time it enters the chronicle and relations cool. {n} action."
Input `{debtor_id, amount: int ≥1 ("The debt amount (up to World rule OLUMLU_ARAC.borc_tavan)"), what: 2–80 ("What is lent: grain, silver, salt, ship hire…"), term_ages?: int ≥1 ("In how many ages it
will be repaid (up to OLUMLU_ARAC.borc_vade_tavan); if empty the world rule's default")}` default `debt_term`.
Validation: party; amount > cap (`At most {cap} can be lent in one debt (World rule OLUMLU_ARAC.borc_tavan).`); term > cap; existing unpaid `borclu` debtor→me (`{x} already owes you an unpaid debt.`);
no wealth/prosperity key (`You have no wealth or prosperity to lend.`); stat < amount (`You do not have enough {wealth|prosperity} to lend this much ({have}).`).
Effect: me −= amount; debtor (if has a wealth key) += amount; due = age + term; bond debtor `borclu` (owes) → me with description `borcAciklama(amount, what, due)` (format: "{amount} {what}; due Age {due}",
parsed back by `borcOku`); relation += `debt_relation`; ap −= debt_ap; chronicle `borc`: `{me} lent {amount} {what} to {debtor}; due Age {due}.`

### borc_ode / repay — communities and named mortals — `debt_ap` actions
"You repay your debt to someone: if you have wealth or prosperity the debt amount passes to them (otherwise you repay in kind, no wealth passes to them); the debt closes and relations warm (even if
overdue). {n} action." Input `{creditor_id}`. Validation: ap; an active `borclu` me→creditor parsable (`You owe {x} nothing.`); with a wealth key and stat < amount → `You do not have enough {..} to repay
the debt ({have} / {amount}).` Effect: me −= amount (if key); creditor += amount only if both have keys; deactivate the debt bond; relation += `debt_repay_relation`; chronicle `borc`: `{me} repaid its debt
({amount} {what}) to {creditor}{ although it was overdue}.`

### evlat_edin / adopt — named mortal only — `adopt_ap` actions, `adopt_per_age` per age
"You adopt another named mortal: it counts as of your lineage and enters the chronicle. It must be younger than you and near you. {per-age}. {n} action."
Input `{child_id, reason: 10–300 ("Why and how you adopt")}`. Validation: ap; counter; non-canon; canon named mortal not me (`The one adopted must be another living, named mortal.`); captive
(`{x} is captive; it must be rescued first.`); same region or near (`{x} is too far.`); existing `soyundan` either way (`There is already a lineage bond between you and {x}.`); ages known and child not younger
(`{x} is not younger than you ({a} / {b}); nobody adopts someone older than themselves.`). Effect: bond child `soyundan` → me "adopted: {reason}"; relation += `adopt_relation`; ap −= adopt_ap; counter+1;
chronicle `soy`: `{me} adopted {child}: {reason}`.

---

### Tunables — `OLUMLU_ARAC` (mortal tools)

English key | old key | default | min | max | group | label. "%" values are coefficients (60 → ×0.6).

| key | old | def | min | max | group | label |
|---|---|---|---|---|---|---|
| words_per_age | kelime_tur | 2 | 0 | 20 | Language and names | Mortal: coin_words per age |
| words_per_call | kelime_adet | 8 | 1 | 40 | Language and names | Mortal: most words in one call |
| route_threshold | rota_esik | 55 | 0 | 200 | Mortal agents | discover_route: path-finding roll threshold (d100 + reason/3) |
| unknown_threshold | bilinmeyen_esik | 85 | 0 | 200 | Mortal agents | discover_route: unknown-world discovery threshold |
| preach_disciples | vaaz_murit | 15 | 0 | 200 | Mortal agents | Disciple increase of a successful sermon (%) |
| escape_cap | kac_tavan | 85 | 0 | 100 | Mortal agents | Captive's escape chance cap (%) |
| escape_wound | kac_yara | 15 | 0 | 500 | Mortal agents | Wound of a captive caught escaping |
| ransom | fidye | 12 | 0 | 100 | Mortal agents | Wealth/prosperity changing hands in a ransom |
| ransom_threshold | fidye_esik | 20 | 0 | 100 | Mortal agents | Min wealth needed for ransom (+5 for prosperity) |
| army_pct | ordu_yuzde | 5 | 1 | 50 | Mortal agents | raise_army: default % of population under arms |
| army_cap | ordu_tavan | 15 | 1 | 100 | Mortal agents | raise_army: max % under arms |
| army_loss | ordu_kayip | 100 | 0 | 100 | Mortal agents | Share of those under arms deducted from population (%) |
| self_budget | sen_butce | 3500 | 500 | 100000 | Context budgets | Mortal context: own details (chars) |
| barter_ap | takas_ap | 1 | 1 | 5 | Mortal agents | barter action cost |
| barter_die | takas_zar | 30 | 1 | 200 | Mortal agents | barter: acceptance die (offer + relation + die ≥ asked) |
| barter_relation_scale | takas_iliski_olcek | 4 | 1 | 100 | Mortal agents | barter: every this many relation points add +1 value |
| barter_relation | takas_iliski | 8 | 0 | 100 | Mortal agents | Relation gain of a successful barter |
| barter_refusal_relation | takas_red_iliski | 3 | 0 | 100 | Mortal agents | Relation loss of a refused barter |
| debt_ap | borc_ap | 1 | 1 | 5 | Mortal agents | lend / repay action cost |
| debt_cap | borc_tavan | 30 | 1 | 100 | Mortal agents | Max amount in one debt |
| debt_term | borc_vade | 3 | 1 | 50 | Mortal agents | Default debt term (ages) |
| debt_term_cap | borc_vade_tavan | 12 | 1 | 100 | Mortal agents | Longest debt term (ages) |
| debt_relation | borc_iliski | 5 | 0 | 100 | Mortal agents | Relation gain of lending |
| debt_repay_relation | borc_ode_iliski | 8 | 0 | 100 | Mortal agents | Relation gain of a repaid debt |
| adopt_ap | evlat_ap | 1 | 1 | 5 | Mortal agents | adopt action cost |
| adopt_relation | evlat_iliski | 10 | 0 | 100 | Mortal agents | Relation gain of adoption |
| discovery_per_age | kesif_tur | 1 | 0 | 20 | Mortal agents | discover_resource: max per mortal per age |
| list_names | liste_ad | 4 | 1 | 100 | Context budgets | Communities named in a chronicle line (rest "and N more communities") |
| seize_relation | el_koyma_iliski | 25 | 0 | 200 | War and diplomacy | Relation loss of a community whose resource was seized (when war cannot be opened) |
| character_budget | karakter_butce | 1500 | 100 | 50000 | Context budgets | Mortal context: character and way of life (chars) |
| event_lines | olay_satir | 12 | 1 | 200 | Context budgets | Mortal context: lines of recent events |
| claim_per_age | sahiplen_tur | 1 | 0 | 20 | Mortal agents | claim: per age |
| worship_per_age | tapin_tur | 1 | 0 | 20 | Religion and language | worship: per age (worship or change god) |
| prayer_per_age | dua_tur | 1 | 0 | 20 | Religion and language | pray_to_creator: per age |
| learn_per_age | ogren_tur | 1 | 0 | 20 | Mortal agents | learn: per age |
| prophecy_per_age | kehanet_tur | 1 | 0 | 20 | Mortal agents | prophesy: per age |
| commander_per_age | komutan_tur | 1 | 0 | 20 | War and diplomacy | appoint_commander: per age |
| adopt_per_age | evlat_tur | 1 | 0 | 20 | Mortal agents | adopt: per age |
| unknown_world_per_age | bilinmeyen_dunya_tur | 1 | 0 | 20 | Cosmos and travel | discover_route: max new-world discoveries in the cosmos per age (worlds born otherwise that age count too) |
| agent_power_mult | ajan_guc_kat | 2 | 0 | 1000 | Mortal agents | Agent selection: power level score multiplier |
| agent_pop_mult | ajan_nufus_kat | 2 | 0 | 1000 | Mortal agents | Agent selection: log10(population or disciples) multiplier |
| agent_pop_default | ajan_nufus_varsayilan | 100 | 10 | 100000000 | Mortal agents | Agent selection: assumed crowd when none recorded |
| agent_wait_mult | ajan_bekleme_kat | 2 | 0 | 1000 | Mortal agents | Agent selection: score per age without acting (capped) |
| agent_chosen | ajan_secilmis | 4 | 0 | 1000 | Mortal agents | Agent selection: bonus for 'chosen' mortals |
| agent_wait_cap | ajan_bekleme_tavan | 30 | 0 | 1000 | Mortal agents | Agent selection: max score for long inaction |
| agent_die | ajan_zar | 10 | 1 | 1000 | Mortal agents | Agent selection: random score die |
| agent_dream | ajan_ruya | 40 | 0 | 1000 | Mortal agents | Agent selection: bonus for a pending dream |
| agent_type_share | ajan_tur_pay | 3 | 1 | 100 | Mortal agents | Agent selection: one type gets at most count/this agents (diversity) |
| preach_faith_default | vaaz_inanc_varsayilan | 50 | 0 | 100 | Religion and language | Sermon: assumed faith of a target without one |
| commander_morale_default | komutan_moral_varsayilan | 50 | 0 | 100 | War and diplomacy | appoint_commander: assumed army morale |
| murit_floor | murit_taban | 1 | 1 | 100000 | Population and growth | found_settlement / raise_army: min disciples a cult keeps |
| army_mercenary_cost | ordu_parali_servet | 10 | 0 | 100 | War and diplomacy | raise_army: wealth/prosperity cost of a mercenary army |
| stat_default | stat_varsayilan | 40 | 0 | 100 | Mortal agents | Mortal tools: assumed stat when missing (craft, reason, strength, defence…) |
| route_reason_div | rota_akil_bolen | 3 | 1 | 1000 | Cosmos and travel | Route roll: + reason / this |
| creation_power_pct | guc_oran | 80 | 1 | 100 | Mortal agents | Mortal creation power: % of creator's power |
| creation_power_cap | guc_tavan | 8 | 1 | 30 | Mortal agents | Highest power of a mortal creation |
| lang_spread | dil_yayginlik | 20 | 0 | 100 | Religion and language | Spread of a language founded by mortals |
| dialect_spread | dil_lehce_yayginlik | 8 | 0 | 100 | Religion and language | Spread of a dialect founded by a single mortal |
| lang_complexity | dil_karmasiklik | 40 | 0 | 100 | Religion and language | Complexity of a mortal language |
| lang_sanctity | dil_kutsallik | 20 | 0 | 100 | Religion and language | Sanctity of a mortal language |
| produce_resources_max | uret_kaynak_adet | 3 | 1 | 20 | Mortal agents | Max resources used in one production |
| produce_abundance_min | uret_bolluk_esik | 10 | 0 | 100 | Mortal agents | Production: resources below this abundance unusable |
| produce_abundance_loss | uret_bolluk_kayip | 10 | 0 | 100 | Mortal agents | Abundance loss of a used resource |
| produce_metallurgy | uret_metalurji | 15 | 0 | 100 | Mortal agents | Weapon/armour bonus for metallurgy knowers |
| produce_magic | uret_buyu | 10 | 0 | 100 | Mortal agents | Item might bonus for magic knowers |
| produce_region_magic_div | uret_bolge_buyu_bolen | 8 | 1 | 1000 | Mortal agents | Item might: + region magic / this |
| produce_craft | uret_zanaat | 50 | 0 | 300 | Mortal agents | Weapon/armour value: % of craft |
| produce_might | uret_kudret | 40 | 0 | 300 | Mortal agents | Weapon/armour value: % of avg resource might |
| produce_die | uret_zar | 15 | 1 | 100 | Mortal agents | Weapon/armour value die |
| produce_min | uret_en_az | 5 | 0 | 100 | Mortal agents | Min damage/protection of weapon/armour |
| produce_side_die | uret_yan_zar | 10 | 1 | 100 | Mortal agents | Non-weapon damage / non-armour protection die |
| produce_might_ratio | uret_kudret_orani | 60 | 0 | 300 | Mortal agents | Item might: % of avg resource might |
| produce_might_die | uret_kudret_zar | 20 | 1 | 100 | Mortal agents | Item might die |
| produce_curse_die | uret_lanet_zar | 12 | 1 | 100 | Mortal agents | Item curse die |
| produce_curse_minus | uret_lanet_eksi | 4 | 0 | 100 | Mortal agents | Item curse: subtracted from die |
| produce_master | uret_usta | 60 | 0 | 200 | Mortal agents | damage+protection ≥ this → "masterwork" in chronicle |
| produce_sturdy | uret_saglam | 30 | 0 | 200 | Mortal agents | damage+protection ≥ this → "sturdy" |
| build_splendour | insa_ihtisam | 70 | 0 | 300 | Mortal agents | Monument splendour: % of craft |
| build_splendour_die | insa_ihtisam_zar | 25 | 1 | 100 | Mortal agents | Monument splendour die |
| build_sturdiness | insa_saglamlik | 60 | 0 | 300 | Mortal agents | Monument sturdiness: % of craft |
| build_sturdiness_die | insa_saglamlik_zar | 30 | 1 | 100 | Mortal agents | Monument sturdiness die |
| build_architecture | insa_mimarlik | 20 | 0 | 100 | Mortal agents | Architecture bonus to splendour and sturdiness |
| build_function_base | insa_islev_taban | 40 | 0 | 100 | Mortal agents | Monument function base |
| build_function_die | insa_islev_zar | 40 | 1 | 100 | Mortal agents | Monument function die |
| build_cost | insa_bedel | 4 | 0 | 100 | Mortal agents | Prosperity and wealth cost of building |
| culture_related_max | kultur_ilgili_adet | 4 | 0 | 20 | Mortal agents | Max related entities in a culture creation |
| work_base | eser_taban | 20 | 0 | 100 | Mortal agents | Work of art fame and influence base |
| work_die | eser_zar | 40 | 1 | 100 | Mortal agents | Work of art fame and influence die |
| law_rigidity_base / _die | kanun_katilik_taban / _zar | 30 / 60 | 0/1 | 100 | Mortal agents | Law rigidity |
| law_justice_base / _die | kanun_adalet_taban / _zar | 20 / 70 | 0/1 | 100 | Mortal agents | Law justice |
| tradition_spread | gelenek_yayginlik | 35 | 0 | 100 | Mortal agents | New tradition/legend spread |
| tradition_rigidity | gelenek_katilik | 50 | 0 | 100 | Mortal agents | New tradition/legend rigidity |
| discovery_abundance_base / _die | kesif_bolluk_taban / _zar | 40 / 40 | 0/1 | 100 | Economy | Discovered resource abundance |
| discovery_value_base / _die | kesif_deger_taban / _zar | 20 / 50 | 0/1 | 100 | Economy | Discovered resource value |
| discovery_might_base / _die | kesif_kudret_taban / _zar | 10 / 50 | 0/1 | 100 | Economy | Discovered resource might |
| migrate_pct | goc_oran | 12 | 0 | 100 | Population and growth | Migrants to a new settlement: % of population |
| migrate_min | goc_en_az | 20 | 1 | 100000 | Population and growth | Min migrants to a new settlement |
| new_town_prosperity | yeni_kent_refah | 35 | 0 | 100 | Population and growth | Prosperity of a mortal-founded settlement |
| new_town_defence | yeni_kent_savunma | 25 | 0 | 100 | Population and growth | Defence of a mortal-founded settlement |
| new_town_faith | yeni_kent_inanc | 60 | 0 | 100 | Population and growth | Faith of a mortal-founded settlement |
| trade_relation | ticaret_iliski | 10 | 0 | 100 | War and diplomacy | Relation gain of establishing trade |
| war_relation | savas_iliski | 25 | 0 | 200 | War and diplomacy | Relation loss of a war declaration |
| war_patron_relation | savas_hami_iliski | 5 | 0 | 200 | War and diplomacy | Relation loss between the two sides' gods |
| worship_foreign_attitude | tapin_yabanci_tutum | 5 | 0 | 200 | Religion and language | Attitude loss of an abandoned foreign god |
| worship_relation | tapin_iliski | 10 | 0 | 200 | Religion and language | Relation loss between old and new god when changing |
| knowledge_base_max | bilgi_temel_adet | 3 | 0 | 20 | Mortal agents | Max base knowledge of new knowledge |
| knowledge_craft_threshold | bilgi_zanaat_esik | 60 | 0 | 100 | Mortal agents | Craft above this → knowledge one level higher |
| knowledge_level_cap | bilgi_seviye_tavan | 10 | 1 | 100 | Mortal agents | Highest level of mortal-developed knowledge |
| knowledge_spread | bilgi_yayginlik | 10 | 0 | 100 | Mortal agents | Spread of newly developed knowledge |
| diplomacy_strength_default | dip_guc_varsayilan | 30 | 0 | 100 | War and diplomacy | Diplomacy strength: assumed strength |
| diplomacy_pop_mult | dip_nufus_kat | 8 | 0 | 100 | War and diplomacy | Diplomacy strength: + log10(population) × this |
| diplomacy_relation_div | dip_iliski_bolen | 4 | 1 | 1000 | War and diplomacy | Diplomacy roll: − relation / this |
| alliance_threshold | dip_ittifak_esik | 60 | 0 | 200 | War and diplomacy | Alliance or marriage acceptance threshold (d100) |
| alliance_relation | dip_ittifak_iliski | 15 | 0 | 100 | War and diplomacy | Relation gain of an accepted alliance |
| marriage_relation | dip_evlilik_iliski | 20 | 0 | 100 | War and diplomacy | Relation gain of an accepted marriage |
| refusal_relation | dip_ret_iliski | 3 | 0 | 100 | War and diplomacy | Relation loss of a refused alliance/marriage |
| peace_threshold | dip_baris_esik | 45 | 0 | 200 | War and diplomacy | Peace offer acceptance threshold (d100) |
| peace_relation | dip_baris_iliski | 15 | 0 | 100 | War and diplomacy | Relation gain of an accepted peace |
| tribute_superiority | harac_ustunluk | 120 | 0 | 1000 | War and diplomacy | Strength superiority needed for tribute (% of the other's strength) |
| tribute_refusal_relation | harac_red_iliski | 25 | 0 | 200 | War and diplomacy | Relation loss of tribute insolence |
| tribute_loss | harac_kayip | 10 | 0 | 100 | War and diplomacy | Wealth/prosperity loss of the payer |
| tribute_gain | harac_kazanc | 8 | 0 | 100 | War and diplomacy | Wealth/prosperity gain of the taker |
| tribute_relation | harac_iliski | 15 | 0 | 200 | War and diplomacy | Relation loss of tribute |
| adventure_die | macera_zar | 30 | 1 | 200 | Heroes and mortals | Item seizure: both sides' die |
| adventure_wound | macera_yara | 30 | 0 | 300 | Heroes and mortals | Wound of a hero failing to seize an item |
| gate_speed | kapi_hiz | 90 | 0 | 100 | Cosmos and travel | Found ancient gate speed |
| gate_range | kapi_menzil | 100 | 0 | 100 | Cosmos and travel | Found ancient gate range |
| gate_armour | kapi_zirh | 60 | 0 | 100 | Cosmos and travel | Found ancient gate armour |
| gate_strangeness / _die | kapi_tuhaflik / _zar | 50 / 40 | 0/1 | 100 | Cosmos and travel | Found ancient gate strangeness |
| gate_power | kapi_guc | 5 | 1 | 30 | Cosmos and travel | Found ancient gate power level |
| ship_mining_div | gemi_maden_bolen | 3 | 1 | 1000 | Cosmos and travel | Ship craft: + miners / this |
| ship_metallurgy | gemi_metalurji | 15 | 0 | 100 | Cosmos and travel | Ship craft: metallurgy bonus |
| ship_speed_base / _div / _die | gemi_hiz_taban / _bolen / _zar | 30 / 3 / 20 | 0/1/1 | 100/1000/100 | Cosmos and travel | Ship speed: base + craft/div + die |
| ship_range_base / _die | gemi_menzil_taban / _zar | 40 / 40 | 0/1 | 100 | Cosmos and travel | Ship range |
| ship_crew_base / _die | gemi_murettebat_taban / _zar | 50 / 400 | 0/1 | 100000 | Cosmos and travel | Ship crew |
| ship_armour_base / _div / _die | gemi_zirh_taban / _bolen / _zar | 20 / 4 / 20 | 0/1/1 | 100/1000/100 | Cosmos and travel | Ship armour |
| ship_strangeness_die | gemi_tuhaflik_zar | 60 | 1 | 100 | Cosmos and travel | Ship strangeness die |
| ship_mining | gemi_maden | 20 | 0 | 100 | Cosmos and travel | Shipbuilding deduction from community miners |
| expedition_pct | sefer_yuzde | 10 | 1 | 100 | Cosmos and travel | Expedition: default % of population |
| expedition_pct_max | sefer_yuzde_tavan | 30 | 1 | 100 | Cosmos and travel | Expedition: max % of population |
| expedition_min | sefer_en_az | 20 | 1 | 100000 | Cosmos and travel | Min people for a colony or conquest expedition |
| tame_charisma_div | evcil_karizma_bolen | 3 | 1 | 1000 | Creatures | Taming skill: + charisma / this |
| tame_die | evcil_zar | 60 | 1 | 200 | Creatures | Taming skill die |
| tame_danger_default | evcil_tehlike_varsayilan | 30 | 0 | 100 | Creatures | Taming: assumed species danger |
| tame_danger_div | evcil_tehlike_bolen | 150 | 1 | 10000 | Creatures | Taming difficulty: danger / (this/100) |
| tame_intelligence_default | evcil_zeka_varsayilan | 20 | 0 | 100 | Creatures | Taming: assumed species intelligence |
| tame_megafauna | evcil_megafauna | 40 | 0 | 200 | Creatures | Extra difficulty of taming megafauna |
| tame_hard_die | evcil_zor_zar | 30 | 1 | 200 | Creatures | Taming difficulty die |
| tame_rage_div | evcil_ofke_bolen | 200 | 1 | 10000 | Creatures | Untamed species attack chance: danger / this |
| tame_loss | evcil_kayip | 5 | 0 | 100 | Creatures | Population/hp loss of the attacked (%) |
| ruin_scribe | kalinti_katip | 2 | 0 | 100 | Mortal agents | Ruin search: scribe class multiplier |
| ruin_die | kalinti_zar | 50 | 1 | 200 | Mortal agents | Ruin search die |
| ruin_knowledge_threshold | kalinti_bilgi_esik | 70 | 0 | 300 | Mortal agents | At or above: lost knowledge found |
| ruin_item_threshold | kalinti_esya_esik | 55 | 0 | 300 | Mortal agents | At or above: ownerless item found |
| ruin_curse_threshold | kalinti_lanet_esik | 35 | 0 | 300 | Mortal agents | Below: searchers are cursed |
| sabotage_die | sabotaj_zar | 40 | 1 | 200 | War and diplomacy | Sabotage: both sides' die |
| sabotage_caught | sabotaj_yakalanma | 15 | 0 | 200 | War and diplomacy | Saboteur caught if vigilance exceeds cunning by this |
| poison_pop | zehir_nufus | 10 | 0 | 100 | War and diplomacy | Poison population/disciples loss (%) |
| poison_hp | zehir_can | 40 | 0 | 300 | War and diplomacy | Poison hp loss |
| arson | kundak | 12 | 0 | 100 | War and diplomacy | Arson prosperity, defence and wealth loss |
| sabotage_relation | sabotaj_iliski | 20 | 0 | 200 | War and diplomacy | Relation loss of caught sabotage |
| preach_base | vaaz_taban | 35 | 0 | 100 | Religion and language | Sermon chance base (%) |
| preach_influence_default | vaaz_etki_varsayilan | 30 | 0 | 100 | Religion and language | Sermon: assumed cult influence |
| preach_god_div | vaaz_tanri_bolen | 4 | 1 | 1000 | Religion and language | Sermon chance: + god's charisma / this |
| preach_old_div | vaaz_eski_bolen | 3 | 1 | 1000 | Religion and language | Sermon chance: − old god's charisma / this |
| preach_faith_div | vaaz_inanc_bolen | 5 | 1 | 1000 | Religion and language | Sermon chance: − target faith / this |
| preach_relation | vaaz_iliski | 10 | 0 | 200 | Religion and language | Relation loss with the god who lost a worshipper to a sermon |
| defy_damage_div | meydan_hasar_bolen | 4 | 1 | 1000 | Heroes and mortals | Defy god: weapon strength = damage / this |
| defy_might_div | meydan_kudret_bolen | 6 | 1 | 1000 | Heroes and mortals | Defy god: + item might / this |
| defy_reason_div | meydan_akil_bolen | 3 | 1 | 1000 | Heroes and mortals | Defy god: + reason / this |
| defy_die | meydan_zar | 40 | 1 | 200 | Heroes and mortals | Defy god: both sides' die |
| defy_god_level | meydan_tanri_seviye | 5 | 0 | 100 | Heroes and mortals | Defy god: god's strength per level |
| defy_untouchable | meydan_dokunulmaz | 15 | 0 | 100 | Heroes and mortals | Defy god: untouchable god bonus |
| godslayer_margin | tanri_katli_fark | 40 | 0 | 300 | Heroes and mortals | A mortal winning by this margin kills a fading god |
| godslayer_existence | tanri_katli_varlik | 35 | 0 | 100 | Heroes and mortals | A god with existence below this can die at mortal hands |
| god_existence_default | tanri_varlik_varsayilan | 60 | 0 | 100 | Heroes and mortals | Assumed god existence |
| godslayer_charisma | tanri_katli_karizma | 25 | 0 | 100 | Heroes and mortals | God-slayer charisma gain |
| god_wound | tanri_yara | 25 | 0 | 100 | Heroes and mortals | Wound of a god beaten by a mortal: % of max hp |
| god_wound_fame | tanri_yara_un | 8 | 0 | 100 | Heroes and mortals | Fame loss of a god beaten by a mortal |
| god_wound_charisma | tanri_yara_karizma | 15 | 0 | 100 | Heroes and mortals | Charisma gain of a mortal who wounded a god |
| god_death_chance | tanri_olum_sans | 50 | 0 | 100 | Heroes and mortals | Death chance of a mortal beaten by a god (%; else cursed) |
| god_crush_fame | tanri_ezme_un | 4 | 0 | 100 | Heroes and mortals | Fame of a god crushing a defiant mortal |
| deny_attitude | inkar_tutum | 10 | 0 | 200 | Religion and language | Attitude loss of a denied foreign god |
| deny_faith | inkar_inanc | 5 | 0 | 100 | Religion and language | Faith loss of a denied foreign god |
| deny_existence | inkar_varlik | 6 | 0 | 100 | Religion and language | Existence loss of a denied son |
| prophecy_related_max | kehanet_ilgili_adet | 3 | 0 | 20 | Religion and language | Max related entities in a prophecy |
| prophecy_certainty | kehanet_kesinlik | 30 | 0 | 100 | Religion and language | Prophecy certainty base (+ reason/2) |
| escape_default | kac_varsayilan | 30 | 0 | 100 | Mortal agents | Escape: assumed agility/reason |
| escape_reason_div | kac_akil_bolen | 3 | 1 | 1000 | Mortal agents | Escape chance: + reason / this |
| escape_defence_div | kac_savunma_bolen | 3 | 1 | 1000 | Mortal agents | Escape chance: − captor defence / this |
| escape_floor | kac_taban | 5 | 0 | 100 | Mortal agents | Lowest escape chance (%) |
| ransom_prosperity_extra | fidye_refah_ek | 5 | 0 | 100 | Mortal agents | Ransom: threshold extra when paying with prosperity |
| ransom_relation | fidye_iliski | 5 | 0 | 100 | Mortal agents | Relation gain of a paid ransom |
| rescue_die | kurtar_zar | 40 | 1 | 200 | Mortal agents | Captive rescue: both sides' die |
| army_strength_default | ordu_guc_varsayilan | 30 | 0 | 100 | War and diplomacy | Army: assumed strength of a community without population |
| army_strength_mult | ordu_guc_kat | 60 | 0 | 100000 | War and diplomacy | Army: base of a community without population = strength × this |
| army_min | ordu_en_az | 30 | 1 | 100000 | War and diplomacy | Min soldiers of a raised army |
| army_morale / _die | ordu_moral / _zar | 50 / 25 | 0/1 | 100 | War and diplomacy | New army morale |
| army_equipment | ordu_techizat | 20 | 0 | 100 | War and diplomacy | New army equipment base |
| army_metallurgy | ordu_metalurji | 15 | 0 | 100 | War and diplomacy | Equipment bonus for metallurgy knowers |
| army_craft_div | ordu_zanaat_bolen | 4 | 1 | 1000 | War and diplomacy | Army equipment: + craft / this |
| army_experience_war | ordu_deneyim_savas | 30 | 0 | 100 | War and diplomacy | Experience of a new army of a war-knowing community |
| army_experience | ordu_deneyim | 10 | 0 | 100 | War and diplomacy | New army experience |
| commander_charisma_div | komutan_karizma_bolen | 10 | 1 | 1000 | War and diplomacy | Commander morale contribution: charisma / this |
| barter_max | takas_adet | 3 | 1 | 20 | Mortal agents | Max things on one side of a barter |
| near_budget | yakin_butce | 2500 | 200 | 50000 | Context budgets | Mortal context: near you (chars) |
| knowledge_budget | bilgi_butce | 1200 | 200 | 50000 | Context budgets | Mortal context: knowledge in the world (chars) |
| mention_budget | ani_butce | 1500 | 200 | 50000 | Context budgets | Mortal context: records mentioning you (chars) |
| language_budget | dil_butce | 1500 | 200 | 50000 | Context budgets | Mortal context: languages of the world (chars) |
| events_budget | olay_butce | 1800 | 200 | 50000 | Context budgets | Mortal context: recent events (chars) |

Related rules owned by other modules but used here: `BAGLAM.olumlu_baglam` 12000 (mortal context total), `BAGLAM.bolum_taban`
600, `BAGLAM.arac_kat` 3, `BAGLAM.kisa_kozmoloji` 500, `BAGLAM.butce_kirp_en_az` 120; `KESIF.arac_tur` 1, `arac_esik` 45,
`arac_bilgi_ek` 15; `OLUM.ayin_tur` 1, `dua_adanmislik` 4, `servet_bedel` 15, `servet_adanmislik` 10, `kurban_nufus` 3,
`kurban_adanmislik` 20, `can_kurbani_adanmislik` 35, `hac_carpan` 200; `YARATIK.kimera_dokuma_mesafe` 4;
`KORKU.bulaniklik_esik` 40; `SINIR.*` population/hp/army caps; `KURAL.can_taban/can_dayaniklilik` (son max hp).

**Tunables — `FIRSAT` (Opportunities; used in mortal and son prompts).**

| key | old | def | min | max | label |
|---|---|---|---|---|---|
| list | liste | 5 | 1 | 50 | Max records listed in an opportunity line |
| stale_ages | durgun_cag | 4 | 1 | 100 | Ages untouched before a story counts as "about to be forgotten" |
| long_thread | uzun_iplik | 8 | 1 | 200 | Advances after which a story "should conclude" |
| silence_ages | sessizlik_cag | 3 | 1 | 100 | Reminder to a son not talking to siblings for this many ages |
| rich_essence | zengin_oz | 150 | 0 | 100000 | Essence for a "great deed" reminder to the creator |
| list_short / list_narrow / list_wide | liste_kisa / liste_dar / liste_genis | 4 / 3 / 6 | 1 | 50/50/100 | Short / narrowest / wide list caps |
| life_people_excess | canli_halk_fazla | 2 | 0 | 50 | "Breathe life": if peoples do not exceed regions by this |
| life_mortals | canli_olumlu | 6 | 0 | 200 | "Breathe life": if named mortals fewer than this |
| life_species | canli_tur | 4 | 0 | 200 | "Breathe life": if species fewer than this |
| rival_relation | rakip_iliski | 20 | 0 | 100 | Rival sibling: relation below minus this |
| hostile_sibling | hasim_kardes | 25 | 0 | 100 | Sibling whose creations are targeted: relation below minus this |
| loyalty_rebel | sadakat_isyan | 40 | 0 | 100 | Rebellion reminder below this loyalty |
| fading | sonmek_uzere | 20 | 0 | 100 | Existence at or below → "you are about to fade" |
| fading_son | solan_ogul | 25 | 0 | 100 | To the god: sons at or below this existence are "being forgotten" |
| doomsday_warning | kiyamet_uyari | 50 | 0 | 100 | Doomsday reminder to the god at this % of threshold |
| hungry_food | ac_erzak | 60 | 0 | 1000 | Worshippers count hungry below this food |
| granary_food | ambar_erzak | 60 | 0 | 1000 | "Your granary is emptying" below this food |
| discontent | hosnutsuz | 30 | 0 | 100 | Class discontent below this satisfaction |
| friendly_neighbour | dost_komsu | 45 | -100 | 100 | Loving neighbour: community relation ≥ this |
| monster_danger | canavar_tehlike | 50 | 0 | 100 | Dangerous creature: danger ≥ this |
| tense_neighbour | gergin_komsu | 20 | 0 | 100 | "Tense neighbour": relation below minus this (no enmity bond) |
| tension_first | gerilim_once | 1 | 0 | 1 | Tension lines moved to top (1 on, 0 off) |
| defy_strength | meydan_guc | 110 | 0 | 1000 | Suggest defying a god when strength + agility ≥ this |

**Tunables — `SIHIRBAZ` (Creation wizard).** `default_magic` (buyu) 50 [0–100]; `default_darkness` (karanlik) 50 [0–100];
`default_peoples` (halk) 2 [1–50]; `peoples_max` (halk_en_cok) 5 [1–50]; `small_cosmos_extra` (kucuk_kozmos) 1 [0–20] worlds
added at genesis; `large_cosmos_extra` (buyuk_kozmos) 2 [0–20]; `pull` (cekim) 50 [0–100] % by which regions' magic/danger
are pulled toward the settings after genesis (`bolgeEgilimi`: `round(v*(100-pull)/100 + target*pull/100)`, magic toward
magic, danger toward darkness, missing values count as 50).

---

### Cross-references

- `llm.js`: `structured` (council, chat, translation, world birth, Fate repair), `agentTurn` + `araclariSar` (mortal turn); retry/continuation policy in 10.
- `epoch.js`: phase 2 mortals (`ajanAdaylari`, `olumluTuru`, pool `olumlu_paralel`), Fate phase council (`konseyTopla`), end-of-age `sezgileriIsle(dunyaDogur)`, background job `agKader` (Fate repair via `askKader`), player actions `konsey`, `dunyaYarat`.
- `server.js`: `/api/ogullar/{id}/sohbet`, `/api/cevir`, `/api/varliklar/{id}/ruya`, genesis extra worlds.
- `tools.js`: `KelimeSchema`, `fillStats`, `atomik`, `bedavaMi`, `olumluYasi`, `sayi`, `kayitDurumu`, `kanonDisi`, `altTurDuzelt`, `aracAlanlari`; son world-birth tool → `dunyaDogur`.
- `world.js`: context fragments, `addKronik`, `addBag`, `iliskiDegistir`, `saveStat`, `sozlukEkle`, `hami`, `yabanciHami`, `konusulanDil`, `isimAlinmis`, `benzerAd`.
- `derin.js`: `savasIlan`, `ateskesVar`, `tIliski/tIliskiDegistir` (community relations), `tanriOlumu`, `etiketEkle/Sil`, `mesafe`, `toplumOf`.
- Other: `mudahale.js` (`bilir`, `bildikleri`, `ogret`, `aktifYasalar`), `ufuk.js` (`yolAra`, `yolYontemi`, `sezgiyiDogur`, `toprakStatlari`, `bolgeyiYerlestir`, `onculer`, `kesifBilgisiVar`), `seyahat.js` (`rotaAc`, `rotaKullanabilir`, `yolculukBaslat`, `rotaSatirlari`, `dunyayiBagla`), `olum.js` (`dirilisAyini`), `yaratici.js` (`yaraticiyaTapin`, `olumluDuasi`), `yaratik.js` (`kimeraDok`), `otesi.js` (`ruhKapla`), `korku.js` (`sagduyu`), `medeniyet.js` (`borcGecikmeleri`), `sim.js` (`olumSonrasi`, `olumluYarala`), `panteon.js` (`yabanciTanriEkle`), `dilmotoru.js` (`adUret`, `fonoloji`), `defter.js` (ledger hook).

---

### Known bugs / design smells

1. `OLUMLU_AJAN` (count 4, ap 3, maxTurns 12, types, intelligence 55) is a hard-coded object, violating the "every balance number is a rule" principle — make them rules.
2. World birth timeout 300 s hard-coded.
3. Council members are the first N sons in DB order (not by relevance); with many sons the same ones always attend — select by relevance/rotation.
4. Council `call_for_peace` closes only one enmity and does not use the `ateskes`/peace machinery (`barisYap`); route through the war module for consistency.
5. Translation uses the main world's naming rule for every language (should use the language's world dialect).
6. `kaderBagOner` strips a leading `v` only from `record`; `other` must match exactly — normalize both.
7. Mortal tool "free" detection by regex over description text (Turkish words) — make `cost` an explicit tool attribute.
8. `rota_kesfet` awaits an LLM world birth inside a tool call (long-running; the old code needed special "ongoing work" handling to avoid double births on reconnect). In the new design, enqueue the intuition and resolve it in the end-of-age step (`sezgileriIsle`) only, returning "you sensed…" immediately.
9. `sefere_cik` applies `min(expedition_pct_max, pct)` only on the population path (the schema max already caps it, so harmless, but redundant/inconsistent).
10. `diplomasi` tribute branch treats named mortals as targets but strength formula uses community stats; mortal-to-mortal tribute is odd.
11. `maceraya_cik` failure uses `me.hp || 100` default; `can` may legitimately be 0-ish — use explicit stat defaults.
12. `ruh_kapla` refunds AP by `ap += 1` manually inside the handler on error while `araclariSar` would also restore the snapshot on a thrown error — inconsistent pattern; prefer throwing and letting the wrapper restore.
13. `takas` charges AP even when the offer is refused (intended), but `diplomasi` invalid offers are pre-checked before AP; keep the rule "invalid input never burns AP, a valid but failed attempt does" consistently across tools.
14. Turkish post-processing (`ekDuzelt`, `toplulukIci`, Turkish regexes, `toLocaleLowerCase('tr')`) is LANGUAGE-SPECIFIC: drop or replace.
15. Several bonds are inserted without checking duplicates (e.g. `avlar` on repeated hunts, `casus` checked but `muttefik` from council covenant only checks `ahitVar`). Add a uniqueness policy per bond type.

---

## 7. Cross-references (LLM layer)

| needs | provided by (old → spec) |
|---|---|
| entity types, stats, rarity table, `action_points`, `power_ceiling`, `roll_stats`, `roll_rarity`, `max_life`, `max_essence`, existence states | `rules.js` → 07-gods-and-progression, 01-data-model |
| `entity_detail`, `world_summary`, `son_memory`, budgets, `unique_name`, `similar_name`, `rename_entity`, `lexicon_add`, tired motifs, `sanitize` | `world.js` → 09 §2, 02-world-core |
| `definite_facts` | `gercek.js` → 02-world-core |
| `entities_in_text` (prophecy targets), Fate bond repair | `agonar.js` → §6 above |
| ledger groups and `ledger_undo` | `defter.js` → 10-epoch-pipeline |
| opportunities, reputation line, scenarios, creator passions | `firsatlar.js`, `itibar.js`, `hedef.js` → 09 appended fragments |
| foreign-god constants and sanitizers | `yabanci.js` → 09 appended fragments, 06-cosmos-and-strange |
| wizard cleaning, region bias, wizard text | `sihirbaz.js` → 09 `genesis.wizard_settings` |
| cosmos transition at genesis, world birth | `db.js`, `kozmos.js` → 06-cosmos-and-strange, §6 above |
| name generator for peoples' god names | `dilmotoru.js` → language spec |
| geography lines for the awakening prompt | `harita.js` → 02-world-core |
| when each agent runs, locks, events, resume, backups | `epoch.js` → 10-epoch-pipeline |

## 8. Known bugs / design smells (agents.js, llm.js, world context)

1. **Birth from the lowest class crashes**: `dogur` computes the allowed lower rarities; for a common parent the list
   is empty and the rarity becomes `undefined`. New: forbid `birth_child` below elite, or allow equal rarity.
2. **Stale son system prompt**: the system text (AP left, stats, life, essence) is rendered once per turn and reused in
   continuation sessions. Re-render per session.
3. **Fate mode "off" silently converts rejections into acceptances** (fall-through branch). Make it explicit.
4. **Judgment schema**: `facts` has a `minItems` (up to 3) but is not `required`; when there is nothing to judge or
   name the minimum can still force invented facts if present; `words` and `facts` both described as mandatory.
   New: required only when the age has judged/named records; `minItems = 0` otherwise.
5. **Chronicle runs in parallel with the judgment**, so the chronicler never sees this age's verdicts (they are
   injected into the *next* age's chronicle as "previous verdicts"); its narrative can celebrate a creation Fate
   rejects in the same age. Acceptable trade-off for latency; alternative: run the chronicle after the judgment.
6. **Advanced-thread rule** requires `record.age == current`, so records judged as debt from earlier ages can never
   advance a thread.
7. **Prophecies outside the prophecy budget** cannot be fulfilled (only prophecies shown in the prompt are accepted).
8. **Text-matching for state** (Turkish `LIKE` patterns): turn counters (`turn_traces`), Fate reward streaks, refunded
   births, previous verdicts for the chronicler. Replace with structured tables (`son_turn_state`, `fate_rewards`,
   `pending_jobs`, typed chronicle rows).
9. **Language-specific heuristics everywhere**: suffix fixer `ekDuzelt`, Turkish stemmer `kokBul`, stop-word lists,
   dialect vowel parsing, opening/pattern regexes, belief-pattern regexes. Re-implement with English stemming and a
   structured dialect (`allowed_letters`) instead of parsing prose.
10. **Summon prompt glue**: "This son" + a line written for the son's own perspective ("YOUR CURRENT WORLD:"). Fixed in 09.
11. **Hard-coded numbers** that violate the "every balance number is tunable" rule: `PROMPT_EN = 1200` (image prompt
    cap for entities), the 150 ms stream flush, the 200-char tool-writing tick, `COSTS` (summon 30, revelation 25…),
    rarity `max_turns`, `ILK_OGULLAR` (common/rare/legendary at genesis), 8 distortion forms, chronicle name ordinals
    (Second…Fifth). Move to the rules registry.
12. **Greedy JSON fallback**: `tryParse` takes the first `{` to the last `}` of the raw text; prefer the SDK's
    structured output only and treat parse fallback as a retryable failure.
13. **Character budgets, not tokens**: all context budgets are in characters. Keep for parity (they are tunable) but
    consider token-aware truncation later.
14. **Per-process long-job registry**: `long_job(son)` is an in-memory promise map; after a restart the pending flag is
    reconciled by DB inspection (§4.5.6). Keep the reconciliation, but store jobs in a table with status.
15. **`AERONA_KES` test hook** uses a global flag inside production code. Keep only in tests (dependency injection).
16. **Ledger undo after the verdict transaction**: if the process dies between the verdict commit and the undo, the
    rejected creation's side effects remain. Do the undo inside the same transaction (or mark rejected entities
    `undo_pending` and reconcile at startup).
17. **Peoples' voices failure** has no retry within the age; historians simply rotate later. Acceptable; document.
18. **Model/effort configuration** existed per role in the UI — remove the settings screen entries (Haiku-only rule).

## 9. Decisions the integrator must make

- Exact Haiku model id constant (the only model); remove the model-per-role settings and `effort`.
- English replacements for every LANGUAGE-SPECIFIC heuristic (stemmer, stop words, dialect letters field).
- Whether the chronicle stays parallel to the judgment (latency) or runs after it (consistency).
- Fate "off" mode semantics (accept everything vs. judge without rejecting).
- From the tool catalogue: one reach rule for cross-world tools; explicit per-tool AP metadata instead of parsing
  descriptions; a counters table for per-age caps.
- From the epoch spec: write the "Fate done" marker in the verdict transaction; isolate the long engine transaction.
- Whether `discover_route` (mortal tool) may run a nested world-birth LLM call inside a tool call or defer it.
