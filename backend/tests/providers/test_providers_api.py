from typing import Any

from pydantic import SecretStr
from sqlalchemy import select

from aerona.catalog.providers import TEAM_SUBSCRIPTION_REASON
from aerona.db.library.tables import ProviderConnectionRow
from aerona.domain.enums.providers import ModelRole
from aerona.settings import Settings
from tests.accounts.team import Team, team_of
from tests.library_support import accounts_of, opened_services

GATEWAY = "http://gateway.test"
KEY = "sk-live-0123456789abcdef"


def gated(settings: Settings) -> Settings:
    return settings.model_copy(update={"gateway_url": GATEWAY})


async def team_workspace(team: Team) -> int:
    made = await team.owner.post("/api/workspaces", json={"name": "Archivists"})
    assert made.status_code == 201, made.text
    return int(made.json()["id"])


async def connect(team: Team, base: str, kind: str, **fields: str) -> dict[str, Any]:
    made = await team.owner.post(f"{base}/connections", json={"kind": kind, **fields})
    assert made.status_code == 201, made.text
    return dict(made.json())


async def test_a_personal_workspace_takes_a_subscription_and_a_team_workspace_refuses_it(settings: Settings) -> None:
    async with team_of(gated(settings)) as team:
        personal = f"/api/workspaces/{team.workspace_id}/providers"
        view = (await team.owner.get(personal)).json()
        assert view["personal"] and view["editable"] and view["gateway_ready"]
        assert {kind["kind"]: kind["refusal"] for kind in view["kinds"]}["claude_subscription"] is None
        claude = await connect(team, personal, "claude_subscription")
        assert claude["label"] == "Claude Pro or Max" and claude["unusable"] == "This subscription is not logged in yet."
        shared = f"/api/workspaces/{await team_workspace(team)}/providers"
        refused = await team.owner.post(f"{shared}/connections", json={"kind": "chatgpt_subscription"})
        assert refused.status_code == 409 and TEAM_SUBSCRIPTION_REASON in refused.text
        kinds = {kind["kind"]: kind for kind in (await team.owner.get(shared)).json()["kinds"]}
        assert kinds["copilot_subscription"]["refusal"] == TEAM_SUBSCRIPTION_REASON and kinds["copilot_subscription"]["terms"]
        server = await team.owner.post("/api/server/providers/connections", json={"kind": "gemini_subscription"})
        assert server.status_code == 409


async def test_a_key_is_kept_sealed_and_never_served(settings: Settings) -> None:
    async with team_of(gated(settings)) as team:
        base = f"/api/workspaces/{await team_workspace(team)}/providers"
        missing = await team.owner.post(f"{base}/connections", json={"kind": "openai"})
        assert missing.status_code == 400
        openai = await connect(team, base, "openai", secret=KEY, label="Studio key")
        assert openai["secret_hint"] == KEY[-4:] and openai["unusable"] is None
        listed = await team.owner.get(base)
        assert KEY not in listed.text and KEY not in str(openai)
        async with accounts_of(team.app).store.read() as session:
            stored = await session.scalar(select(ProviderConnectionRow.secret).where(ProviderConnectionRow.id == openai["id"]))
        assert stored and KEY not in stored
        bad = await team.owner.post(f"{base}/connections", json={"kind": "local_server", "base_url": "ollama"})
        assert bad.status_code == 400
        local = await connect(team, base, "local_server", base_url="http://127.0.0.1:11434")
        renamed = await team.owner.patch(f"{base}/connections/{local['id']}", json={"label": "Desk server"})
        assert renamed.json()["label"] == "Desk server"
        assert (await team.owner.delete(f"{base}/connections/{local['id']}")).status_code == 200


async def test_chains_check_their_entries_and_use_server_connections(settings: Settings) -> None:
    async with team_of(gated(settings)) as team:
        server = await connect(team, "/api/server/providers", "openai", secret=KEY)
        worker = await connect(team, "/api/server/providers", "image_worker", base_url="http://127.0.0.1:8100")
        other = f"/api/workspaces/{await team_workspace(team)}/providers"
        foreign = await connect(team, other, "anthropic", secret=KEY)
        base = f"/api/workspaces/{team.workspace_id}/providers"
        no_model = await team.owner.put(f"{base}/roles/writing", json={"entries": [{"connection_id": server["id"], "model": ""}]})
        assert no_model.status_code == 400
        wrong_role = await team.owner.put(f"{base}/roles/writing", json={"entries": [{"connection_id": worker["id"], "model": ""}]})
        assert wrong_role.status_code == 400
        elsewhere = await team.owner.put(f"{base}/roles/writing", json={"entries": [{"connection_id": foreign["id"], "model": "m"}]})
        assert elsewhere.status_code == 404
        chain = await team.owner.put(f"{base}/roles/writing", json={"entries": [{"connection_id": server["id"], "model": "fast"}]})
        assert chain.status_code == 200 and chain.json()["entries"][0]["model"] == "fast"
        images = await team.owner.put("/api/server/providers/roles/images", json={"entries": [{"connection_id": worker["id"], "model": ""}]})
        assert images.status_code == 200
        roles = {role["role"]: role for role in (await team.owner.get(base)).json()["roles"]}
        assert roles["images"]["entries"] == [] and roles["images"]["server_entries"][0]["connection_id"] == worker["id"]


async def test_a_universe_uses_its_workspace_chain_over_the_server_chain_and_follows_a_move(settings: Settings) -> None:
    async with team_of(gated(settings)) as team:
        server = await connect(team, "/api/server/providers", "openai", secret=KEY, label="Server key")
        await team.owner.put("/api/server/providers/roles/writing", json={"entries": [{"connection_id": server["id"], "model": "general"}]})
        services = await opened_services(team.app, team.universe_id)
        model = services.application.model
        assert model.model_of(ModelRole.WRITING) == "general · Server key"
        own = await connect(team, f"/api/workspaces/{team.workspace_id}/providers", "groq", secret=KEY, label="Own key")
        await team.owner.put(f"/api/workspaces/{team.workspace_id}/providers/roles/writing", json={"entries": [{"connection_id": own["id"], "model": "quick"}]})
        assert model.model_of(ModelRole.WRITING) == "quick · Own key"
        assert model.model_of(ModelRole.CONVERSATION) == ""
        state = (await team.owner.get("/api/state")).json()
        assert {"role": "writing", "model": "quick · Own key"} in state["role_models"]
        moved = await team.owner.post(f"/api/library/universes/{team.universe_id}/move", json={"workspace_id": await team_workspace(team)})
        assert moved.status_code == 200, moved.text
        assert model.model_of(ModelRole.WRITING) == "general · Server key"


async def test_a_viewer_reads_the_providers_but_cannot_change_them(settings: Settings) -> None:
    async with team_of(gated(settings)) as team:
        shared = await team_workspace(team)
        viewer, _ = await team.member("quillon", "viewer", shared)
        base = f"/api/workspaces/{shared}/providers"
        read = await viewer.get(base)
        assert read.status_code == 200 and read.json()["editable"] is False
        assert (await viewer.post(f"{base}/connections", json={"kind": "openai", "secret": KEY})).status_code == 403
        assert (await viewer.get("/api/server/providers")).status_code == 403


async def test_the_old_settings_move_into_the_owner_workspace_and_the_server(settings: Settings) -> None:
    legacy = settings.model_copy(update={"claude_code_oauth_token": SecretStr("sk-ant-oat01-legacy-token"), "image_worker_url": "http://127.0.0.1:8100"})
    async with team_of(legacy) as team:
        personal = (await team.owner.get(f"/api/workspaces/{team.workspace_id}/providers")).json()
        claude = next(connection for connection in personal["connections"] if connection["kind"] == "claude_subscription")
        assert claude["logged_in_at"] is not None and not claude["from_server"]
        roles = {role["role"]: role for role in personal["roles"]}
        assert all(roles[role]["entries"][0]["model"] == "haiku" for role in ("world_agents", "writing", "conversation"))
        server = (await team.owner.get("/api/server/providers")).json()
        assert [connection["kind"] for connection in server["connections"]] == ["image_worker"]
        services = await opened_services(team.app, team.universe_id)
        assert services.application.images.model_name() == "Image worker"
