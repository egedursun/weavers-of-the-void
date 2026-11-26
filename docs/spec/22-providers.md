# 22 — Providers

The world can think and paint with any model the people running it have: a paid subscription they log in to, an API key of a cloud provider, or a model server of their own. One small seam carries every call; nothing outside it knows which provider answered.

## 0. Decisions

| Question | Decision |
|---|---|
| Subscriptions | Claude Pro/Max, ChatGPT Plus/Pro (Codex), Google AI Pro/Ultra (Gemini CLI) and GitHub Copilot, each logged in through its own official agent. Every subscription card carries the terms warning, personal workspaces included: the provider may not allow its subscription in another program, and the risk is the person's. |
| API keys | Through the Bifrost gateway (a sidecar service), with the key sent on each request (Bifrost "direct keys"), so the gateway holds no state of ours. Key-only providers: OpenAI, Anthropic, Google Gemini, Mistral, Groq, DeepSeek, xAI, OpenRouter, Cohere, Cerebras, Perplexity, Replicate, Hugging Face. Cloud-account providers that need endpoints, regions or projects (Azure OpenAI, AWS Bedrock, Google Vertex) are not offered; their models are reachable through OpenRouter. |
| Local models | An existing OpenAI-compatible server (Ollama, LM Studio, vLLM, llama.cpp or any other) by its address, called directly. Nothing is bundled. The local image worker stays and is one image provider. |
| Scope | Per workspace with a server default. A universe uses its workspace's setup for a role when the workspace has one, otherwise the server's. Subscriptions belong only in personal workspaces (one person, no sharing); team workspaces and the server default take API keys and local servers. |
| Models | Per role, each role an ordered chain: the first entry that answers serves the call; when it is unreachable, refused, out of quota or failing after its retries, the next one is tried. The administrator orders the chain; nothing else decides. |
| Embedding | The Divine Will index keeps its fixed on-device model (multilingual-e5-small). It is not a role and cannot be changed. |
| Cost | Not tracked. The cost column, tile and field leave the Model metrics, the API and the telemetry table. |
| Simplicity | One table of connections, one table of chain entries, one resolver, one panel used at both scopes, one agent protocol (ACP) for every subscription, one HTTP client (the official `openai` package) for every key and local server. |

## 1. Words

- **Connection**: one credential: a subscription login, an API key of one provider, or the address of a local model server or the image worker. It belongs to a workspace or to the server.
- **Role**: what a model is used for. `world_agents` (son, mortal and fallen turns of an age), `writing` (every structured call: genesis, chronicle, fate, councils, voices, deepening, naming, translation, image prompts and the rest), `conversation` (Divine Will and Presence) and `images`.
- **Chain**: the ordered entries `(connection, model)` of one role at one scope.
- **Scope**: the server, or one workspace.

## 2. Provider catalogue

`catalog/providers.py` holds one row per `ProviderKind`: its label, family (`subscription`, `api`, `local`), what it can serve (text, images), the fields it asks for (key, address), and for subscriptions the agent command, the login command, where the agent keeps its login, and the terms warning. Adding a provider is adding a row.

| Family | Kinds | Asks for | Serves |
|---|---|---|---|
| subscription | `claude_subscription`, `chatgpt_subscription`, `gemini_subscription`, `copilot_subscription` | a login (§5) | text |
| api | `openai`, `anthropic`, `gemini`, `mistral`, `groq`, `deepseek`, `xai`, `openrouter`, `cohere`, `cerebras`, `perplexity`, `replicate`, `huggingface` | an API key | text; images for `openai`, `gemini`, `replicate`, `huggingface` |
| local | `local_server` | an address, an optional key | text |
| local | `image_worker` | an address | images |

## 3. Data

In the process catalogue `library.db` (spec 20 §2):

`provider_connections`: `id`, `workspace_id` (null for the server), `kind`, `label` (1–60), `secret` (the key or the subscription token, encrypted), `secret_hint` (last four characters), `base_url`, `logged_in_at`, `created_by`, `created_at`.

`provider_chain_entries`: `id`, `workspace_id` (null for the server), `role`, `position`, `connection_id` (cascade), `model`, `tools_work`, `sees_images`, `checked_at`, `check_note`.

- A chain entry may name a connection of its own scope or of the server.
- A workspace connection is never used outside its workspace.
- Secrets are encrypted with Fernet. The key is `AERONA_SECRET_KEY` when set, otherwise `secret.key` in the process data directory, made at the first start with owner-only permissions. Secrets never leave the server; reads show `secret_hint`.
- A subscription connection keeps its agent's login under `providers/<connection id>/` in the process data directory, removed with the connection.
- Deleting a workspace deletes its connections and chains.

**Legacy mapping** at the first start of this edition, and again when the owner is created: `CLAUDE_CODE_OAUTH_TOKEN`, when set, becomes a logged-in Claude subscription of the owner's personal workspace (a subscription belongs to one person) serving its three text roles with the model the app used (`haiku`); `AERONA_IMAGE_WORKER_URL`, when set, becomes a server image worker connection serving `images`. Nothing the server did before stops.

## 4. Calling a model

- `llm/` carries neutral types only: `AgentTool(name, description, input_schema, handler)` returning `ToolReply(text, is_error)`, and the run events `TextDelta`, `ToolStarted`, `ToolInputDelta`, `ToolCalled`, `ToolFinished`, `Thought`. The stream reporter, the token meter and the Divine Will and Presence traces read these events.
- `LlmClient` keeps its methods (`structured`, `run_agent`, `capabilities`). On each call it resolves the chain of the call's role for its universe's current workspace (a universe moved to another workspace uses the new one at once) and walks it.
- A structured call is a run with one extra tool, `answer`, whose input schema is the output schema; the run ends when the model calls it. Every backend, every model, one path.
- **Subscription backend** (`llm/backends/acp.py`): the agent of the connection's kind speaks the Agent Client Protocol over stdio. One agent process per connection stays open; every run is a new session and is closed after. The run's tools are served to the agent from this server over MCP (streamable HTTP, `llm/tool_gate.py`, its own loopback port, a random path per run). The agent's own tools are switched off by its configuration (Claude: no SDK tools and the session mode `bypassPermissions`, which then covers only the run's tools; Codex: its shell, web, image, app and agent features off and the session mode `read-only`, so approvals come back to this server; Gemini: folder trust off and every built-in tool excluded; Copilot: only the tools of the `aerona` server available), and every permission request for anything but the run's tools is refused, the tool being found by its title or by the call it was announced with. Text an agent sends outside a model message (its own notices) never reaches the run when the agent marks its messages. The model is chosen through the session's model option; the system prompt goes in as the session's system prompt when the agent takes one, otherwise at the head of the prompt.
- **API and local backend** (`llm/backends/openai.py`): the `openai` client with streaming and tool calls, against the gateway (key in the request) or against the local server's address.
- **Images**: `imaging/` gains a provider for the gateway's `/v1/images/generations` beside the worker client; the queue walks the `images` chain. A picture that comes back in another format is stored as PNG.

## 5. Logging in to a subscription

A login runs the official agent's own login on the server in a pseudo-terminal one thousand columns wide (so a printed token never wraps), under the connection's login folder, with every browser opener of the system replaced by one that does nothing, and the panel shows what it prints with the address as a link and the code large while the login runs, plus a field to paste a code back:

| Kind | Command | Done when |
|---|---|---|
| `claude_subscription` | `claude setup-token` | it prints the token; the token is kept as the connection's secret |
| `chatgpt_subscription` | `codex login --device-auth` | it exits successfully |
| `gemini_subscription` | `gemini` with `NO_BROWSER=true` | its login file exists |
| `copilot_subscription` | `copilot login --device-code` | it exits successfully |

The login ends by itself after ten minutes. "Log in again" repeats it; "Log out" removes the login folder.

## 6. Checking a model

"Check" on a chain entry runs one short tool round and one `answer` call (`tools_work`); on a `conversation` entry also one tiny picture (`sees_images`). A failed check marks the entry with its reason; the entry stays in the chain and is skipped while marked. Image entries are not checked by drawing; the queue notes their last failure.

## 7. Screens

- **Models** part of the workspace settings (`/workspace?part=providers`): the workspace's connections (Subscriptions, API keys, Local), and its four role chains, with "uses the server default" when a role has none. Server owners and administrators switch between **This workspace** and **Server default** tabs, one scope shown at a time. Workspace administrators edit their workspace; others see it read-only.
- When a role has no model in the workspace or the server default, a banner at the top of the universe names the roles and links to Models; the Divine Will and Presence show the same notice where they wait, and every control that needs a model is disabled with a reason that names the missing role (or that the language model is turned off).
- Each connection card: kind, label, status (logged in, key set, reachable), the terms warning on subscriptions, log in / log out / replace key / remove. In a team workspace and at the server default the subscription cards are drawn disabled with their reason.
- Each role: the ordered chain with connection, model (picked from the connection's model list, or typed), check result and reorder, add, remove.
- **Setup** (spec 21 §6) gains a second step, the Server default panel, with "Continue" once any role has an entry and "Skip for now".
- The model names shown in Game settings, the Images settings, the Divine Will composer and the health panel come from the universe's own chains (`role_models` of the world state); the health endpoint, which belongs to no universe, only says whether the gateway is set.

## 8. Settings and deployment

- `AERONA_GATEWAY_URL` (empty: API connections are refused with their reason), `AERONA_SECRET_KEY` (optional), `AERONA_AGENTS_DIR` (where the agents are installed).
- `deploy/agents/package.json` pins the four agents; the backend image installs Node and them. docker-compose adds the `bifrost` service with `deploy/bifrost/config.json` (direct keys on, every provider of §2 listed without a key) and points the backend at it. `make dev` starts Bifrost natively next to the backend.

## 9. Proof

- Resolver: workspace chain over the server chain per role; a moved universe switches at once; a workspace connection never serves another workspace; subscriptions are refused outside personal workspaces.
- Chain: an unreachable or refusing entry hands the call to the next; a marked entry is skipped; the metrics name the model that answered.
- Backends, with no paid call: the real Bifrost against a local stand-in model server (tool round, streaming, `answer`, images, the key reaching the upstream); the real agents against stand-in model servers where they take a custom address, proving that only the run's tools reach the model and that the run's tool calls come back through the tool gate; a stand-in ACP agent for the rest.
- Login: each command's output parsed to its address and code; the paste field reaches the process; the Claude token is captured and stored encrypted.
- Secrets: encrypted at rest, never served, survive a restart.
- Legacy mapping of §3.
- Frontend: vitest for the panel at both scopes, disabled subscription cards with their reason, the login dialog, chain editing; tsc, eslint and every guard.

## 10. Contract for the build

### Modules

- `catalog/providers.py`; `domain/enums/providers.py` (`ProviderKind`, `ProviderFamily`, `ModelRole`).
- `db/library/tables.py` (§3) and its migration.
- `services/providers/`: `secrets.py`, `store.py`, `directory.py` (the resolver, a snapshot refreshed on every change), `service.py` (create, edit, remove, chains, checks), `login.py` (§5), `legacy.py` (§3).
- `llm/tools.py`, `llm/events.py`, `llm/backends/acp.py`, `llm/backends/openai.py`, `llm/tool_gate.py`, `llm/client.py`.
- `imaging/gateway.py`; `services/images/queue.py` walks the chain.
- `api/routers/providers.py`.
- Frontend `features/providers/`.

### API

| Route | Access | Purpose |
|---|---|---|
| `GET /api/workspaces/{id}/providers` | workspace member | catalogue for this scope, connections, chains, the server chains it inherits |
| `POST /api/workspaces/{id}/providers/connections`, `PATCH/DELETE …/connections/{connection_id}` | workspace admin | connections |
| `GET …/connections/{connection_id}/models` | workspace admin | the connection's models |
| `POST/GET/DELETE …/connections/{connection_id}/login`, `POST …/login/input` | workspace admin | §5 |
| `PUT …/roles/{role}`, `POST …/roles/{role}/check` | workspace admin | chain and its check |
| the same under `/api/server/providers` | server owner/admin | the server default |
