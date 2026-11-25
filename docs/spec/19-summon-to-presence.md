# 19 — Summon to Presence

The player summons any being of the world that can speak and talks with it one to one. The being answers as itself, from its own mind, memories, faith and place in the world, and may act only through the tools it already has in its own agent turns. Summon to Presence replaces the old son chat (`agents/son_chat.py`, `POST /api/sons/{id}/chat`, the "Talk with them" section): that chat moved a son's loyalty with every message and lived inside the son's entry; it is removed whole.

## 1. Who can be summoned

A **speaker** is a node that has a mind of its own:

- every son, in any status (active, asleep, exiled, fallen, dead);
- every foreign god, in any status (awake, asleep, defeated, dead);
- every entity of a minded type (`MINDED_TYPES` of `engine/minds/profiles.py`: mortals, spirits, cosmic beings, outer beings) and every beast whose intelligence reaches `rules.mortal_agents.creature_min_intelligence`;
- in any entity status (canon, dead, destroyed, forgotten).

The Creator is never a speaker (the player is the Creator). Collectives (peoples, factions, cults, settlements) are not speakers; their members are. One function, `speaker_of(node)` in `services/presence/speakers.py`, decides it, and every consumer (API, atlas button, picker, tests) asks it.

A speaker is **dead** when its status says so (`SonStatus.DEAD`, `ForeignGodStatus.DEAD`, `EntityStatus.DEAD`/`DESTROYED`). A dead speaker is summoned from death: it knows it died, when (epoch) and how (`death_cause` or its ending incident), and speaks as one called back. The screen marks it with a "Summoned from death" seal on the portrait, the header and every reply.

## 2. Guise and record

A session is opened with two choices that cannot change during the session.

**Guise** (`PresenceGuise`) — who the speaker believes it hears:

| Value | The speaker knows |
|---|---|
| `creator` | It speaks with its Creator, revealed. |
| `unnamed_power` | A divine presence speaks, but not which one. |
| `dream_voice` | A voice comes to it in a dream; it may doubt it is real. |
| `ordinary` | An ordinary being of its own world, unknown to it, speaks; nothing divine. |

**Record** (`PresenceRecord`):

- `on_record`: the session and every exchange are kept for good, appear in the speaker's entry of the lore book and the Codex, and the speaker remembers the audience afterwards (§5). The speaker may act through its own acting tools (§4).
- `off_record`: nothing is kept after the session ends; the speaker remembers nothing; it reads the world but never acts. Off-record sessions are deleted when the player ends them, begins anew, or opens another session with the same speaker.

## 3. Sessions and memory window

- One open session per speaker at a time. A session holds exchanges (player words → the speaker's answer).
- The speaker keeps the last `rules.presence.remembered_exchanges` (default 10, an editable game rule) finished exchanges of the session in its context; older ones stay on screen above a "Beyond memory" line.
- **Begin anew** (reset) closes the session after a ConfirmDialog: an on-record session is kept closed (readable in the speaker's past audiences, the book and the Codex); an off-record one is deleted. A new session starts empty.
- An exchange streams text and tool calls live, can be stopped, retries the model like every agent call, and runs on the same model as the rest of the game.

## 4. Tools

The speaker uses only what it has:

- **Read tools** (always): the read-only tools of its own toolset (`ToolMeta.read_only`), so it can look at the world as it would in its own turn.
- **Acting tools** (on the record, living speakers only): the acting tools its own turn would offer — a son through `son_may_use`, a mortal or beast or spirit through `mortal_may_use`. Acts spend the speaker's own action points of the current epoch through the real tool runtime (gate, precheck, ledger, records), exactly as in its own turn; when the points are spent the tool refuses and the speaker says so.
- Foreign gods have no agent toolset; they read only. The dead read only.
- Speaking never changes loyalty, devotion, mood or any stat by itself. Only acts the speaker performs through its tools change the world, and those are recorded like any act of its own turn.

## 5. What the speaker remembers

After each finished on-record exchange the speaker's answer carries a short `remember` line (structured output). It is kept as one memory of kind `MemoryKind.AUDIENCE` (holder: the speaker, subject: the Creator node, note: the line, magnitude from the speaker's own feeling, decaying like every memory). The guise is part of the note, so a speaker who heard a dream voice remembers a dream. These memories reach the speaker's later turns through `mind_lines` like every other memory.

## 6. Context

The speaker's system context is built from the same sources as its own turn: identity, personality and speech style, mind and memories, faith, kin and bonds, place, languages, its present situation, and the world summary. On top of it:

- the guise and what the speaker knows about who speaks;
- for the dead: that it died, when and how, and that it is called back;
- the record: on the record, that it may act through its tools and will remember; off the record, that nothing it says will be kept;
- the last remembered exchanges of this session.

The speaker answers in the player's language (detected as in spec 18 §language) with its own names and terms kept.

## 7. Tables

- `presence_sessions`: `id`, `node_id`, `guise`, `record`, `status` (`PresenceStatus`: open, closed), `dead_when_summoned` (bool), `title`, `opened_epoch`, `opened_at`, `closed_at`.
- `presence_exchanges`: `id`, `session_id`, `ordinal`, `epoch`, `player_text`, `reply_text`, `remember_text`, `status` (`PresenceExchangeStatus`: running, done, failed, cancelled), `error`, `model`, `input_tokens`, `output_tokens`, `steps`, `started_at`, `finished_at`.
- `presence_events`: `id`, `exchange_id`, `ordinal`, `kind` (`PresenceEventKind`: text, thought, tool_call, tool_result, error, retry), `tool`, `payload` (JSON), `created_at`.

## 8. Rules

`rules.presence`: `remembered_exchanges` (10), `max_steps` (24), `audience_magnitude` (the strength of an audience memory, 20), `audience_decay_pct` (10).

## 9. API

- `GET /api/presence/speakers?q=&group=&dead=` — paged speakers with name, kind, type, group (`sons`, `foreign_gods`, `mortals`, `spirits`, `beings`, `beasts`), dead flag, portrait, open session id.
- `GET /api/presence/speakers/{node_id}` — one speaker: identity card (name, epithet, kind, status, place, faith, languages, dead with epoch and cause), its open session and its past on-record sessions.
- `POST /api/presence/sessions` `{node_id, guise, record}` — opens a session (closes and, if off record, deletes an open one first).
- `GET /api/presence/sessions/{id}` — the session with its exchanges and events, the memory boundary.
- `POST /api/presence/sessions/{id}/exchanges` `{text}` — starts an exchange (409 while one runs).
- `POST /api/presence/exchanges/{id}/cancel`.
- `POST /api/presence/sessions/{id}/close` — begin anew.
- Streaming goes through the agent stream events with `channel = "presence:<exchange_id>"`; the live feed leaves them out like the Divine Will's.

## 10. Frontend

- Left menu: **Summon to Presence** (`/presence`) in the Pantheon group.
- The page: a rail of speakers to pick (search, groups, the dead toggled in, paged with show-more); the presence stage for the chosen speaker: portrait framed as the app's crests, name and kind, status, "Summoned from death" seal for the dead, the guise picker (four illustrated choices with a line each) and the record choice (On the record / Off the record, with what each keeps), then the transcript with streaming, tool cards, copy buttons on every message, a composer, stop, and Begin anew with a ConfirmDialog; past on-record audiences of the speaker below.
- Every node entry window of a speaker (son, foreign god, entity) shows a **Speak with them** button in its header that opens `/presence?node=<id>`; no chat is embedded in an entry window.
- Loading, empty, error and disabled states with reasons; light and dark; phone width.

## 11. Book and Codex

Every on-record session appears in its speaker's entry (sons, foreign gods, entities) as "Audiences": guise, record, epoch, whether the speaker was summoned from death, and the full transcript of every exchange with the acts it performed and the memory it kept. Off-record sessions never appear.

## 12. Removal

The old son chat goes in the same change: `agents/son_chat.py`, the son chat endpoints and schemas, `SON_CHAT` role, the `council.chat_*` rules, the son chat prompts, contexts and schemas, the `son.chat` event kind, `SonChat.tsx` and its section, its API hooks, tests and docs. `MessageIntent.CHAT` and `ActionKind.CHAT` stay for the history already written.

## 13. Proof

- Unit: `speaker_of` for every node kind and status; guise and record texts reach the context; the dead context; tool selection (read only off record, for the dead and foreign gods; own acting tools on record).
- Scripted-model tests: an exchange streams and records events; on record an act through a son tool spends its action points and is in the ledger; off record an acting tool is never offered; an audience memory is written on record and never off record; the memory window at N and N+1; begin anew keeps on-record and deletes off-record sessions; cancel.
- API tests for every endpoint; book and Codex render audiences and never off-record ones.
- Frontend tests: picker, guise and record choice, transcript with copy buttons, dead seal, Begin anew dialog, entry window button.
