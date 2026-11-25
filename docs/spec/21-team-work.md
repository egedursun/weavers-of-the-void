# 21 — Team Work

Several people work on the same universes at once. Everyone sees one up-to-date universe; every change names the person who made it and why. Accounts are local to the server (no SSO in this edition). Nothing is paid for: there are no licences, seats, prices or billing screens.

## 0. Decisions

| Question | Decision |
|---|---|
| Workspaces | Many per server. Every account has a **personal workspace**; any account can create **team workspaces** and be a member of several. Each workspace has its own Library of Universes (spec 20), members and trash. |
| Sign-in | Username or e-mail, and a password. Accounts carry username, e-mail and display name. The app sends no e-mail at all in this edition and has no mail code: an administrator creates the account and the app issues a **temporary password**, shown once to copy and hand over; at the first sign-in the person must set their own password before anything else. |
| Single player today | The first start shows a **setup** screen that creates the server owner. From then on everyone signs in. Every universe already in the library moves into the owner's personal workspace and every earlier act is attributed to the owner. |
| Billing | None. Behave as if the app is free. |
| Who acts in the world | Everyone is the hand of the **one Creator**. Essence is one shared pool. Ledger, chronicle, book and Codex name the person behind every act. |
| Same thing edited by two | **Presence + version check.** Everyone sees who is looking at and who is editing a record. A save over a record someone else changed since the screen loaded shows what they changed and lets the person keep theirs or apply their own over it. Nobody's work is lost silently. |
| Divine Will, Presence, Foresight | **Private to their owner**, shareable. Acts they take land in the shared universe like any other act. |
| Permissions | **Defaults carry the team.** A person's role in the workspace (Administrator, Editor, Viewer) is their role in every universe of it, present and future, with no grants to manage. Per-universe overrides (a different role for one person, or a permission turned on or off for a role in one universe) exist for the rare case and are never needed for ordinary work. |

## 1. Accounts

Accounts live in the process catalogue `library.db` (spec 20 §2), never in a universe database.

`accounts`: `id`, `username` (3–32, lowercase letters, digits, `.`, `_`, `-`; unique), `email` (unique, validated), `display_name` (1–80), `password_hash` (argon2id), `must_change_password`, `status` (`active`, `deactivated`), `server_role` (`owner`, `admin`, `member`), `created_by`, `created_at`, `last_sign_in_at`, `password_changed_at`, `failed_attempts`, `locked_until`, `avatar_tone` (one of the gem tones, chosen at creation from the name and editable).

- Exactly one `owner`. The owner can make others server `admin`s, take it back, and hand ownership to another active admin.
- **Create account** (server owner/admin, or a workspace administrator for their workspace, §2): username, e-mail, display name. The server draws a temporary password (16 characters from an unambiguous alphabet) and returns it once; it is stored only as a hash. `must_change_password` is set.
- **Reset password**: issues a new temporary password the same way, signs the person out everywhere.
- **Deactivate / reactivate**: a deactivated account cannot sign in, its sessions end at once, it keeps its memberships greyed out; everything it made stays attributed to it.
- **Delete account**: removes the sign-in and memberships; contributions stay attributed to the name it had, shown as a former member. The owner cannot be deleted or deactivated.
- **Own profile**: display name, e-mail, avatar tone; change password (needs the current one; signs out every other session); list of own sessions with device, address, last use, and sign-out of one or all.
- **Password rule**: 10 to 256 characters, not containing the username or the e-mail's local part; the screen shows a strength meter.
- **Lockout**: after 5 failed attempts the account locks for 15 minutes; a per-address throttle slows repeated attempts. Both numbers are rules (§9).
- Account acts by administrators go into the library log (`library_events`) with the acting account.

## 2. Workspaces and access

`workspaces`: `id`, `name`, `kind` (`personal`, `team`), `owner_account_id` (personal only), `created_by`, `created_at`.

`workspace_members`: `workspace_id`, `account_id`, `role` (`admin`, `editor`, `viewer`), `added_by`, `added_at`. A new member is a **Viewer** unless the person adding them picks another role; the add dialog offers the three roles with what each can do.

`universe_overrides`: `universe_id`, `account_id`, `role` (`admin`, `editor`, `viewer`, `none`), `set_by`, `set_at`. Only exceptions are stored; without a row the workspace role applies.

`universe_permissions`: `universe_id`, `role` (`editor`, `viewer`), `permission`, `allowed`. Only changes from the defaults are stored; missing rows mean the default.

The catalogue row of a universe (spec 20) gains `workspace_id`; its trash entries keep it.

- A personal workspace is made with every account and named after it. It has one member and cannot be deleted while the account exists.
- Any active account can create a team workspace and becomes its administrator. A workspace administrator renames it, adds members (an existing account, or a new account made on the spot with a temporary password, §1) with a workspace role, removes members, changes workspace roles, and deletes the workspace (its universes go to the trash). Any member can leave; the last administrator cannot leave or be demoted.
- **Universe roles come from the workspace.** A person's role in a universe is their workspace role, for every universe already there and every one made later; adding a member gives them the whole shelf at once. The person who creates or imports a universe is its Administrator. An administrator may set an override for one person in one universe (raise, lower, or `none` to keep a universe from them); the screen marks every override and offers "back to the workspace role".
- **Moving a universe** between workspaces the person administers drops its overrides; the target workspace's roles apply.

### Permissions

| Permission | What it allows | Editor default | Viewer default |
|---|---|---|---|
| `view` | Read the universe: every screen, chronicle, Atlas, the book on screen | on (fixed) | on (fixed) |
| `edit_world` | Every god lever that creates, edits, holds or deletes a thing, and every Divine Will act | on | off |
| `start_ages` | Run epochs, half epochs, prehistory and every job of the world group | on | off |
| `change_rules` | Rule and setting changes | on | off |
| `lock_canon` | Hold and release things, strike and restore canon, edit canon facts | on | off |
| `alternative_histories` | Foresight and other forks of the universe | on | off |
| `undo_own` | Undo one's own acts | on | off |
| `undo_any` | Undo anyone's act (every undo names who undid it, and can itself be undone) | on | off |
| `generate_images` | Image generation and restyling | on | off |
| `export` | Export the universe, duplicate it, download backups | on | off |
| `download_books` | Book PDF and Codex downloads | on | on |
| `divine_will_read` | Divine Will modes that only read (Ask Lore, Mechanics Guide, Creative Work without acts), off-the-record Presence | on | on |
| `presence_on_record` | Presence on the record | on | off |
| `manage_shelf` | Rename, notes, tags, cover, pin, archive in the library | on | off |

Administrators have every permission, plus: manage overrides and the permission table, turn canon approval on and off and decide proposals (§5), delete the universe. These are not in the table.

**Why these defaults.** A team works like a shared document: Editors can do everything to the world itself, including starting ages, changing rules, locking canon and undoing each other, because every act names its author, can be undone, and acts during an age wait in the queue instead of being lost. What Editors cannot do is change who has access or delete the universe. Viewers read everything, download the book and the Codex and ask the Divine Will questions, and change nothing. A team that wants a gate on canon turns on canon approval (§5) with one switch rather than editing permissions. With these defaults an ordinary team never opens the permission table.

**Enforcement.** Every API route declares what it needs: no session needed (setup state, sign-in, health), a session, a workspace role, or a universe permission. A route without a declaration fails `scripts/check_route_access.py` and `tests/api/test_route_access.py`. Every lever of the action catalogue maps to a permission (default `edit_world`; canon levers `lock_canon`; rule levers `change_rules`; world-group jobs `start_ages`; image levers `generate_images`); a catalogue entry without one fails `tests/unit/test_lever_permissions.py`. A refused request answers 403 with `code: "forbidden"`, the permission and the person's role.

**On screen** every control a person may not use stays visible and disabled with its reason ("Viewers of Haluvra cannot change its rules"), following `check_hidden_controls.py`.

## 3. Sessions and the request

- Signing in sets an opaque random token in an `HttpOnly`, `SameSite=Lax` cookie (`Secure` behind HTTPS: `AERONA_COOKIE_SECURE`). Only its SHA-256 is stored (`sessions`: `id`, `account_id`, `token_hash`, `created_at`, `last_used_at`, `expires_at`, `user_agent`, `address`). A session ends after 14 idle days or 60 days in all (rules). The existing `OriginGuard` keeps refusing cross-origin writes.
- Every request but the open ones resolves the account from the cookie; a missing or ended session answers 401 `code: "signed_out"`, and `must_change_password` answers 403 `code: "password_change_required"` for everything but the password and sign-out routes. No account at all answers 409 `code: "setup_required"`.
- The universe binding of spec 20 (`X-Aerona-Universe`) checks the person's access before the universe opens. The library lists only universes of the chosen workspace (`X-Aerona-Workspace`, remembered per tab like the universe) that the person can see.
- Media, book and Codex links are same-origin and carry the cookie, so images and PDFs keep working. SSE streams check the session on connect and drop when it ends.

## 4. Attribution and history

- Universe databases gain the person behind each act: `ledger_entries`, `action_records`, `state_changes`, chronicle lines told by the Creator's hand, notifications, Divine Will, Presence and Foresight records, and every queued act and proposal get `author_account_id` and `author_name` (the display name at the time, so a deleted account still reads right).
- Every act may carry a **reason** (up to 500 characters). Every act control's confirmation offers "Why (optional)"; Divine Will acts carry the person's message; a queued or proposed act keeps its reason.
- The Ledger screen filters by person, epoch, kind and date, shows author and reason, and undoes a single act (`undo_own`/`undo_any`); the undo names who undid it. Each entry window's history shows who changed each value. Epochs record who started them.
- Old rows have no author; the catalogue keeps `legacy_author_account_id` per universe (the owner after setup, §6), and every reader shows that account for them.
- **Book and Codex**: a "Hands of the Creator" section lists the people who shaped the universe with their acts; the Ledger appendix shows author and reason of every act; queued acts and proposals appear in the records appendix.

## 5. Working at the same time

**Presence.** Each open universe keeps an in-memory roster: who is in the universe, on which screen, which entry window, and whether they are editing it (an edit form open). Clients send it over `POST /api/presence` on change and every 30 seconds; it expires after 90 seconds of silence and is pushed to everyone on the universe's live stream. The top bar shows the faces of those present; an entry window shows who else is looking and who is editing.

**Version check.** Every record a screen edits carries `revision`: the id of the latest `state_changes` row touching it. Every editor lever accepts `expected_revision`; when the record changed since, by someone else, the lever answers 409 `code: "edit_conflict"` with each field that changed, its value then and now, who changed it and when. The screen shows them side by side with "Keep theirs" and "Apply mine over theirs"; the second sends again without the check. A change by the same person never conflicts.

**Edits while an age runs.** While the world group is busy (an epoch, half epoch or prehistory run), a lever does not run: it is stored as a **queued act** (`queued_acts`: author, lever, payload, reason, `queued_at`, `status` `queued`/`applied`/`failed`/`cancelled`, result, `applied_at`, `ledger_entry_id`) and answers 202 with it. Divine Will plans and Presence acts queue the same way. When the run ends, the queue applies in order through the normal runner, each act attributed to its author; a failed one keeps its reason and notifies its author. Everyone sees the queue in a tray in the top bar ("Waiting for the age to end"); the author or an administrator can cancel an act before it applies. Undo, rule changes and job starts follow the same queue.

**Live stream.** During an age everyone on the universe watches the same live stream (today's events), plus who started it; account and membership changes, queued acts, proposals and presence travel on it too.

**Canon approval.** An administrator can turn on canon approval for a universe. While it is on, an Editor's act that touches locked canon — a held thing, a canon strike or restore, a change to a canon fact, or any act whose rehearsed preview (Divine Will previews) changes a held thing — does not run. It becomes a **proposal** (`canon_proposals`: author, lever, payload, reason, the preview, `status` `pending`/`approved`/`rejected`/`withdrawn`, decider, decided at, note). Administrators review proposals in the universe's Team panel with the preview, approve (the act runs attributed to its author, with the approver recorded) or reject with a note; the author can withdraw. Both sides get notifications. Administrators' own acts never wait.

## 6. Setup and adoption

1. No account exists: the app opens on **Setup**: username, e-mail, display name, password twice. It creates the owner and the owner's personal workspace.
2. Every universe of the library (spec 20) gets `workspace_id` of that workspace and `legacy_author_account_id` of the owner; the trash entries the same. The owner is Administrator of all.
3. The setup is atomic and resumable like adoption in spec 20.

## 7. Screens

- **Sign-in** (username or e-mail, password; locked and deactivated accounts say so), **Setup** (§6), **Set your password** (forced after a temporary one; the temporary one is asked again), all in the app's gilded style with the logo, a clear error for every failure, and keyboard-only use.
- **Account menu** (avatar at the top right): profile, password, sessions, sign out.
- **Workspace switcher** in the top bar and on the Library: personal and team workspaces with their crests, create a team workspace.
- **Workspace settings** (administrators; members see a read-only view): General (name, default universe role, delete, leave); Members (paged table with avatar, name, username, e-mail, workspace role, status, last sign-in, universes; add member with existing account or new account and temporary password shown once with copy; change role; universe access; reset password; deactivate/reactivate; remove); Universes (per universe: the people with access and their roles, overrides marked with a way back to the workspace role, the permission table with every permission's meaning and its default, a "back to defaults" action, canon approval).
- **Server accounts** (owner and server admins): every account with the account acts of §1, server roles, ownership transfer.
- **In a universe**: present faces in the top bar; the queue tray; a **Team** panel (people with access and their roles, who is online, proposals to review, queued acts, the universe's permission table read-only for non-administrators); author and reason in the Ledger, the feed, entry history and Divine Will acts; the conflict dialog of §5.
- Every list is paged, every state (loading, empty, error, disabled with reason) is drawn, phone width and both themes work.

## 8. Private sessions

Divine Will sessions and plans, Presence sessions, Foresight runs and Divine Will writings belong to their author. Each has `shared` (off by default): shared ones are listed for everyone with `view` on the universe, read-only for others; only the author continues them. Acts they took are in the shared universe as usual.

## 9. Rules and settings

Accounts and presence belong to the process, not to a universe, so their numbers are settings: `AERONA_ACCOUNTS_LOCKOUT_ATTEMPTS` (5), `AERONA_ACCOUNTS_LOCKOUT_MINUTES` (15), `AERONA_ACCOUNTS_PASSWORD_MIN_LENGTH` (10), `AERONA_ACCOUNTS_SESSION_IDLE_DAYS` (14), `AERONA_ACCOUNTS_SESSION_MAX_DAYS` (60), `AERONA_TEAM_PRESENCE_TTL_SECONDS` (90), `AERONA_TEAM_REASON_MAX_LENGTH` (500), and `AERONA_COOKIE_SECURE`, all listed in `.env.example`, docker-compose and the README.

## 10. Proof

- Accounts: setup, sign-in by username and by e-mail, wrong password, lockout and its end, temporary password forcing a change, reset, deactivate and reactivate, delete with attribution kept, session expiry, sign-out everywhere on password change.
- Access: every route answers 401 signed out, 403 without its permission, success with it (generated from the route declarations); every lever refused for a Viewer and allowed for an Editor; a new member reaches every universe of the workspace, existing and later ones, with no further step; an override of `none` hides a universe; the permission table changes take effect at once and "back to defaults" clears them.
- Working together: two clients on one universe see each other's presence and changes; a conflicting edit returns the diff and both choices work; acts during an epoch queue and apply after it in order with their authors; a cancelled queued act never runs; canon approval turns an Editor's act on a held thing into a proposal that runs only when approved.
- Attribution: every act's ledger entry, action record and state change names its author and reason; undo names who undid; adoption attributes old acts to the owner; the book and the Codex show the people and their acts.
- Frontend: vitest for every new screen and the disabled reasons; tsc, eslint and every guard.

## 11. Contract for the build

### Modules

- `core/account_scope.py`: `AccountRef(id, name)`, `current_account()`, `acting_account(ref)` (a context variable set for every signed-in request, for every queued act and approved proposal applied later, and for every job a person started). Universe code reads the author only from here.
- `services/accounts/`: `store.py` (accounts, sessions, workspaces, members, overrides, permissions in `library.db`), `passwords.py` (argon2id, temporary passwords, rule checks), `sessions.py`, `setup.py` (§6), `access.py` (effective role and permissions of an account in a universe), `permissions.py` (the permission enum, defaults, lever mapping).
- `api/access.py`: route declarations `open_route`, `signed_in`, `workspace_role(role)`, `universe_permission(permission)`; `api/routers/auth.py`, `api/routers/accounts.py`, `api/routers/workspaces.py`.
- `services/team/`: `queue.py` (queued acts), `proposals.py`, `presence.py`, `revisions.py`; `api/routers/team.py`.
- `db/library` migrations for §1–§3; universe migrations for §4, §5 and §8.

### API

| Route | Access | Purpose |
|---|---|---|
| `GET /api/auth/state` | open | `{setup_required, account, must_change_password}` |
| `POST /api/auth/setup` | open while no account | create the owner (§6) |
| `POST /api/auth/sign-in` | open | `{login, password}` → account; sets the cookie |
| `POST /api/auth/sign-out` | signed in | ends this session |
| `POST /api/auth/password` | signed in (also while a change is required) | `{current, new}` |
| `PATCH /api/auth/profile` | signed in | display name, e-mail, avatar tone |
| `GET /api/auth/sessions`, `DELETE /api/auth/sessions/{id}`, `DELETE /api/auth/sessions` | signed in | own sessions |
| `GET/POST /api/accounts`, `PATCH/DELETE /api/accounts/{id}`, `POST /api/accounts/{id}/reset-password`, `POST /api/accounts/{id}/ownership` | server owner/admin | §1 |
| `GET/POST /api/workspaces`, `PATCH/DELETE /api/workspaces/{id}`, `POST /api/workspaces/{id}/leave` | member / admin | §2 |
| `GET/POST /api/workspaces/{id}/members`, `PATCH/DELETE /api/workspaces/{id}/members/{account_id}`, `POST …/reset-password`, `POST …/deactivate`, `POST …/reactivate` | workspace admin | members; a new account in the POST body returns its temporary password once |
| `GET /api/workspaces/{id}/universes/{universe_id}/access` | workspace member | people, effective roles, overrides, permission table, canon approval |
| `PUT/DELETE …/access/overrides/{account_id}`, `PUT/DELETE …/access/permissions`, `PUT …/access/canon-approval` | universe admin | §2, §5 |
| `POST /api/library/universes/{id}/move` | admin of both workspaces | §2 |
| `GET /api/team` | `view` | my role and permissions, people present, canon approval, counts of queued acts and pending proposals |
| `POST /api/presence` | `view` | `{screen, node_id, editing}` |
| `GET /api/team/queue`, `DELETE /api/team/queue/{id}` | `view` / author or admin | §5 |
| `GET /api/team/proposals`, `POST /api/team/proposals/{id}/approve`, `…/reject`, `…/withdraw` | `view` / admin / author | §5 |
| `PATCH` of Divine Will sessions and writings, Presence sessions and Foresight runs | author | `{shared}` |

The library routes of spec 20 take `X-Aerona-Workspace` (query `workspace` for links). Every lever and editor request accepts `reason` and `expected_revision`; an edit conflict answers 409 `edit_conflict` with `{changes: [{field, before, after, by, at}]}`; a lever during an age answers 202 with the queued act; a proposal answers 202 with the proposal.

