from collections.abc import AsyncIterator

import pytest

from aerona.constants.accounts import WORKSPACE_HEADER
from aerona.constants.library import UNIVERSE_HEADER
from aerona.core.errors import ForbiddenError
from aerona.services.accounts.guard import GrantedAccess, ensure_lever_allowed, enter_grant
from aerona.settings import Settings
from tests.accounts.team import Team, team_of
from tests.library.shelf import settled

CREATOR_EDIT = {"title": "Shaper"}


@pytest.fixture
async def team(settings: Settings) -> AsyncIterator[Team]:
    async with team_of(settings) as made:
        yield made


async def team_workspace(team: Team) -> int:
    made = await team.owner.post("/api/workspaces", json={"name": "The Guild"})
    assert made.status_code == 201, made.text
    workspace_id = int(made.json()["id"])
    moved = await team.owner.post(f"/api/library/universes/{team.universe_id}/move", json={"workspace_id": workspace_id})
    assert moved.status_code == 200, moved.text
    assert moved.json()["workspace_id"] == workspace_id
    team.owner.headers[WORKSPACE_HEADER] = str(workspace_id)
    return workspace_id


async def test_a_viewer_reads_and_is_refused_every_change_with_a_sentence(team: Team) -> None:
    workspace = await team_workspace(team)
    viewer, member = await team.member("vela", "viewer", workspace)
    assert member["role"] == "viewer"
    assert member["universe_count"] == 1
    assert (await viewer.get("/api/creator")).status_code == 200
    refused = await viewer.patch("/api/creator", json=CREATOR_EDIT)
    assert refused.status_code == 403
    body = refused.json()
    assert (body["code"], body["permission"], body["role"]) == ("forbidden", "edit_world", "viewer")
    name = (await team.owner.get(f"/api/library/universes/{team.universe_id}")).json()["name"]
    assert body["error"] == f"Viewers of {name} cannot change the world."
    rules = await viewer.patch("/api/rules", json={"changes": []})
    assert rules.json()["error"] == f"Viewers of {name} cannot change its rules."
    shelf = (await viewer.get("/api/library/universes")).json()
    assert [item["role"] for item in shelf["items"]] == ["viewer"]
    assert "edit_world" not in shelf["items"][0]["permissions"]


async def test_an_editor_changes_the_world_but_not_the_access(team: Team) -> None:
    workspace = await team_workspace(team)
    editor, _ = await team.member("eda", "editor", workspace)
    assert (await editor.patch("/api/creator", json=CREATOR_EDIT)).status_code == 200
    refused = await editor.put(f"/api/workspaces/{workspace}/universes/{team.universe_id}/access/canon-approval", json={"on": True})
    assert refused.status_code == 403
    assert refused.json()["error"].endswith("cannot manage who has access.")
    assert (await editor.post(f"/api/workspaces/{workspace}/members", json={"account_id": 1, "role": "viewer"})).status_code == 403


async def test_a_new_member_reaches_every_universe_and_later_ones(team: Team) -> None:
    workspace = await team_workspace(team)
    viewer, _ = await team.member("nia", "viewer", workspace)
    made = await team.owner.post("/api/library/universes", json={"name": "Second Shelf"})
    assert made.status_code == 201, made.text
    names = {item["name"] for item in (await viewer.get("/api/library/universes")).json()["items"]}
    assert "Second Shelf" in names
    assert len(names) == 2


async def test_an_override_hides_a_universe_and_back_to_the_workspace_role(team: Team) -> None:
    workspace = await team_workspace(team)
    viewer, member = await team.member("ola", "editor", workspace)
    account_id = member["account"]["id"]
    hidden = await team.owner.put(f"/api/workspaces/{workspace}/universes/{team.universe_id}/access/overrides/{account_id}", json={"role": "none"})
    assert hidden.status_code == 200, hidden.text
    person = next(person for person in hidden.json()["people"] if person["account"]["id"] == account_id)
    assert (person["role"], person["overridden"]) == ("none", True)
    assert (await viewer.get("/api/library/universes")).json()["total"] == 0
    blocked = await viewer.get("/api/creator")
    assert blocked.status_code == 403
    back = await team.owner.delete(f"/api/workspaces/{workspace}/universes/{team.universe_id}/access/overrides/{account_id}")
    assert next(person for person in back.json()["people"] if person["account"]["id"] == account_id)["role"] == "editor"
    assert (await viewer.get("/api/creator")).status_code == 200


async def test_the_permission_table_takes_effect_and_resets(team: Team) -> None:
    workspace = await team_workspace(team)
    viewer, _ = await team.member("pim", "viewer", workspace)
    table = await team.owner.put(f"/api/workspaces/{workspace}/universes/{team.universe_id}/access/permissions", json={"viewer": {"edit_world": True}})
    row = next(row for row in table.json()["permissions"] if row["permission"] == "edit_world")
    assert (row["viewer"], row["viewer_default"], row["label"]) == (True, False, "Change the world")
    assert (await viewer.patch("/api/creator", json=CREATOR_EDIT)).status_code == 200
    reset = await team.owner.delete(f"/api/workspaces/{workspace}/universes/{team.universe_id}/access/permissions")
    assert next(row for row in reset.json()["permissions"] if row["permission"] == "edit_world")["viewer"] is False
    assert (await viewer.patch("/api/creator", json=CREATOR_EDIT)).status_code == 403


async def test_a_lever_is_checked_by_its_own_permission(team: Team) -> None:
    workspace = await team_workspace(team)
    editor, _ = await team.member("lev", "editor", workspace)
    await team.owner.put(f"/api/workspaces/{workspace}/universes/{team.universe_id}/access/permissions", json={"editor": {"change_rules": False}})
    refused = await editor.post("/api/actions/lever:set", json={})
    assert refused.status_code == 403
    assert refused.json()["permission"] == "change_rules"


async def test_members_roles_and_the_last_administrator(team: Team) -> None:
    workspace = await team_workspace(team)
    _, member = await team.member("rio", "viewer", workspace)
    account_id = member["account"]["id"]
    promoted = await team.owner.patch(f"/api/workspaces/{workspace}/members/{account_id}", json={"role": "admin"})
    assert promoted.json()["role"] == "admin"
    owner_id = (await team.owner.get("/api/auth/state")).json()["account"]["id"]
    assert (await team.owner.patch(f"/api/workspaces/{workspace}/members/{owner_id}", json={"role": "viewer"})).status_code == 200
    last = await team.owner.patch(f"/api/workspaces/{workspace}/members/{account_id}", json={"role": "viewer"})
    assert last.status_code == 403
    personal = next(item for item in (await team.owner.get("/api/workspaces")).json() if item["kind"] == "personal")
    assert (await team.owner.post(f"/api/workspaces/{personal['id']}/leave")).status_code == 409


async def test_a_workspace_admin_resets_and_deactivates_only_its_own_people(team: Team) -> None:
    workspace = await team_workspace(team)
    admin, _ = await team.member("ada", "admin", workspace)
    member, record = await team.member("ben", "viewer", workspace)
    account_id = record["account"]["id"]
    reset = await admin.post(f"/api/workspaces/{workspace}/members/{account_id}/reset-password")
    assert reset.status_code == 200, reset.text
    assert reset.json()["temporary_password"]
    other = await team.owner.post("/api/workspaces", json={"name": "Elsewhere"})
    joined = await team.owner.post(f"/api/workspaces/{other.json()['id']}/members", json={"account_id": account_id, "role": "viewer"})
    assert joined.status_code == 201, joined.text
    assert (await admin.post(f"/api/workspaces/{workspace}/members/{account_id}/deactivate")).status_code == 403
    off = await team.owner.post(f"/api/workspaces/{workspace}/members/{account_id}/deactivate")
    assert off.json()["account"]["status"] == "deactivated"
    assert (await member.get("/api/workspaces")).status_code == 401
    assert (await admin.post(f"/api/workspaces/{workspace}/members/{account_id}/reactivate")).status_code == 403
    assert (await team.owner.post(f"/api/workspaces/{workspace}/members/{account_id}/reactivate")).json()["account"]["status"] == "active"


async def test_deleting_a_team_workspace_sends_its_universes_to_the_trash(team: Team) -> None:
    workspace = await team_workspace(team)
    gone = await team.owner.delete(f"/api/workspaces/{workspace}")
    assert gone.status_code == 200, gone.text
    personal = next(item for item in (await team.owner.get("/api/workspaces")).json() if item["kind"] == "personal")
    team.owner.headers[WORKSPACE_HEADER] = str(personal["id"])
    trash = (await team.owner.get("/api/library/trash")).json()
    assert [item["universe_id"] for item in trash["items"]] == [team.universe_id]


async def test_without_a_session_nothing_but_the_open_routes_answer(team: Team) -> None:
    stranger = team.client(**{UNIVERSE_HEADER: team.universe_id})
    assert (await stranger.get("/api/health")).status_code == 200
    assert (await stranger.get("/api/auth/state")).json()["setup_required"] is False
    refused = await stranger.get("/api/creator")
    assert (refused.status_code, refused.json()["code"]) == (401, "signed_out")


async def test_a_viewer_cannot_act_through_the_divine_will_or_presence_on_the_record(team: Team) -> None:
    workspace = await team_workspace(team)
    viewer, _ = await team.member("dov", "viewer", workspace)
    command = await viewer.post("/api/divine-will/cycles", json={"text": "raise a mountain", "mode": "command"})
    assert (command.status_code, command.json()["permission"]) == (403, "edit_world")
    foresight = await viewer.post("/api/divine-will/cycles", json={"text": "what if", "mode": "foresight"})
    assert (foresight.status_code, foresight.json()["permission"]) == (403, "alternative_histories")
    node_id = (await team.owner.get("/api/presence/speakers")).json()["speakers"][0]["node_id"]
    kept = await viewer.post("/api/presence/sessions", json={"node_id": node_id, "guise": "creator", "record": "on_record"})
    assert (kept.status_code, kept.json()["permission"]) == (403, "presence_on_record")


async def test_the_lever_runner_refuses_without_the_route(team: Team) -> None:
    workspace = await team_workspace(team)
    _, member = await team.member("rue", "viewer", workspace)
    record = await team.accounts.catalogue.require(team.universe_id)
    access = await team.accounts.universe_access(member["account"]["id"], record)
    enter_grant(GrantedAccess(access, record.name, record.canon_approval))
    try:
        with pytest.raises(ForbiddenError) as refused:
            ensure_lever_allowed("lever:suppress")
    finally:
        enter_grant(None)
    assert refused.value.permission == "lock_canon"


async def test_downloads_need_their_own_permission(team: Team) -> None:
    workspace = await team_workspace(team)
    viewer, _ = await team.member("dex", "viewer", workspace)
    assert (await viewer.get("/api/world/export")).json()["permission"] == "export"
    assert (await viewer.get("/api/backups/epoch-0001.db/database")).json()["permission"] == "export"
    await team.owner.put(f"/api/workspaces/{workspace}/universes/{team.universe_id}/access/permissions", json={"viewer": {"download_books": False}})
    assert (await viewer.get("/api/codex.md")).json()["permission"] == "download_books"
    assert (await viewer.get("/api/book.pdf")).json()["permission"] == "download_books"


async def test_nothing_of_another_workspace_or_a_hidden_universe_shows(team: Team) -> None:
    workspace = await team_workspace(team)
    stranger, member = await team.member("sol", "editor", workspace)
    second = await team.owner.post("/api/library/universes", json={"name": "Hidden Shelf", "tags": ["secret"]})
    assert second.status_code == 201, second.text
    hidden_id = second.json()["id"]
    await team.owner.put(f"/api/workspaces/{workspace}/universes/{hidden_id}/access/overrides/{member['account']['id']}", json={"role": "none"})
    exported = await team.owner.post(f"/api/library/universes/{hidden_id}/export")
    assert exported.status_code == 202, exported.text
    assert all(job["universe_id"] != hidden_id for job in (await stranger.get("/api/library/jobs")).json())
    await settled(team.owner, f"/api/library/exports/{exported.json()['id']}")
    assert (await team.owner.delete(f"/api/library/universes/{hidden_id}")).status_code == 200
    personal = next(item for item in (await team.owner.get("/api/workspaces")).json() if item["kind"] == "personal")
    other = await team.owner.post("/api/library/universes", json={"name": "Elsewhere Shelf"}, headers={WORKSPACE_HEADER: str(personal["id"])})
    assert other.status_code == 201
    listed = (await stranger.get("/api/library/universes")).json()
    assert {item["name"] for item in listed["items"]} == {listed["items"][0]["name"]}
    assert all(facet["value"] != "secret" for facet in listed["facets"]["tags"])
    events = (await stranger.get("/api/library/events")).json()["items"]
    assert all(event["universe_name"] not in {"Elsewhere Shelf"} for event in events)
    assert (await stranger.get("/api/library/trash")).json()["total"] == 0
    assert (await team.owner.get("/api/library/trash")).json()["total"] == 1
    assert all(event["universe_id"] != hidden_id for event in events)
    foreign = await stranger.get("/api/library/universes", headers={WORKSPACE_HEADER: str(personal["id"])})
    assert foreign.status_code == 403
    peek = await stranger.get(f"/api/library/universes/{other.json()['id']}")
    assert peek.status_code == 403


async def test_candidates_are_found_only_by_an_exact_name_or_mail(team: Team) -> None:
    workspace = await team_workspace(team)
    await team.owner.post("/api/accounts", json={"username": "marit", "email": "marit@example.test", "display_name": "Marit"})
    gone = (await team.owner.post("/api/accounts", json={"username": "maritza", "email": "mz@example.test", "display_name": "Maritza"})).json()
    await team.owner.patch(f"/api/accounts/{gone['account']['id']}", json={"status": "deactivated"})
    exact = (await team.owner.get(f"/api/workspaces/{workspace}/candidates", params={"q": "MARIT"})).json()
    assert [found["username"] for found in exact] == ["marit"]
    assert set(exact[0]) == {"id", "username", "display_name", "avatar_tone"}
    assert (await team.owner.get(f"/api/workspaces/{workspace}/candidates", params={"q": "mari"})).json() == []
    assert (await team.owner.get(f"/api/workspaces/{workspace}/candidates", params={"q": "mz@example.test"})).json() == []
    by_mail = (await team.owner.get(f"/api/workspaces/{workspace}/candidates", params={"q": "Marit@Example.test"})).json()
    added = await team.owner.post(f"/api/workspaces/{workspace}/members", json={"account_id": by_mail[0]["id"], "role": "viewer"})
    assert added.status_code == 201
    assert (await team.owner.get(f"/api/workspaces/{workspace}/candidates", params={"q": "marit"})).json() == []
    viewer, _ = await team.member("cara", "viewer", workspace)
    assert (await viewer.get(f"/api/workspaces/{workspace}/candidates", params={"q": "owner"})).status_code == 403


async def test_without_a_chosen_workspace_the_personal_one_answers(team: Team) -> None:
    workspace = await team_workspace(team)
    _, member = await team.member("wes", "viewer", workspace)
    bare = await team.sign_in("wes", "a brand new evening walk")
    bare.headers.pop(WORKSPACE_HEADER, None)
    listed = await bare.get("/api/library/universes")
    assert listed.status_code == 200
    assert listed.json()["total"] == 0
    foreign = await bare.get("/api/library/universes", headers={WORKSPACE_HEADER: "999"})
    assert foreign.status_code == 403
    assert foreign.json()["error"] == "This account is not a member of that workspace."
    assert member["account"]["username"] == "wes"


async def test_a_viewer_may_restore_only_what_they_deleted_and_fetch_only_exports_they_may_make(team: Team) -> None:
    workspace = await team_workspace(team)
    viewer, _ = await team.member("tru", "viewer", workspace)
    made = (await team.owner.post("/api/library/universes", json={"name": "Spare Shelf"})).json()
    entry = (await team.owner.delete(f"/api/library/universes/{made['id']}")).json()
    refused = await viewer.post(f"/api/library/trash/{entry['id']}/restore")
    assert refused.status_code == 403
    exported = (await team.owner.post(f"/api/library/universes/{team.universe_id}/export")).json()
    await settled(team.owner, f"/api/library/exports/{exported['id']}")
    assert (await viewer.get(f"/api/library/exports/{exported['id']}/file")).status_code == 403
    assert (await viewer.delete(f"/api/library/exports/{exported['id']}")).status_code == 403
    assert (await team.owner.post(f"/api/library/trash/{entry['id']}/restore")).status_code == 200
