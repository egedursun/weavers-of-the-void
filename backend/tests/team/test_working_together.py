from collections.abc import AsyncIterator

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.node import ActorKind
from aerona.engine.mortal.profile import ensure_profile
from aerona.services.player.catalog import action
from aerona.services.team.canon import reading_of
from aerona.settings import Settings
from tests.accounts.team import Team, team_of
from tests.polling import until
from tests.team.support import a_mortal, an_age, edit, guild, services_of, settled_act


@pytest.fixture
async def team(settings: Settings) -> AsyncIterator[Team]:
    async with team_of(settings) as made:
        yield made


async def revision_of(client: AsyncClient, node_id: int) -> int:
    response = await client.get(f"/api/team/revisions/{node_id}")
    return int(response.json()["revision"])


async def test_two_people_see_each_other_present_and_editing(team: Team) -> None:
    workspace = await guild(team)
    mortal = await a_mortal(team)
    editor, _ = await team.member("ivo", "editor", workspace)
    marked = await team.owner.post("/api/presence", json={"screen": "entry", "node_id": mortal.id, "editing": True})
    assert marked.status_code == 200, marked.text
    await editor.post("/api/presence", json={"screen": "atlas"})
    seen = (await editor.get("/api/team")).json()
    by_name = {item["name"]: item for item in seen["present"]}
    assert by_name["The Owner"]["node_id"] == mortal.id and by_name["The Owner"]["editing"] is True
    assert by_name["Ivo"]["screen"] == "atlas"
    assert seen["role"] == "editor" and "edit_world" in seen["permissions"]
    assert seen["heartbeat_seconds"] > 0
    await team.owner.delete("/api/presence")
    assert [item["name"] for item in (await editor.get("/api/team")).json()["present"]] == ["Ivo"]


async def test_a_change_by_someone_else_to_the_same_field_conflicts_and_both_choices_work(team: Team) -> None:
    workspace = await guild(team)
    mortal = await a_mortal(team)
    editor, _ = await team.member("una", "editor", workspace)
    opened = await revision_of(team.owner, mortal.id)
    assert (await edit(editor, mortal.id, {"name": "Una's choice"})).status_code == 200
    clean = await edit(team.owner, mortal.id, {"title": "Keeper of the lists"}, expected_revision=opened)
    assert clean.status_code == 200, clean.text
    clashed = await edit(team.owner, mortal.id, {"name": "Owner's choice"}, expected_revision=opened)
    assert clashed.status_code == 409
    body = clashed.json()
    assert body["code"] == "edit_conflict"
    change = next(item for item in body["changes"] if item["field"] == "name")
    assert (change["after"], change["by"]) == ("Una's choice", "Una")
    services = await services_of(team)
    async with services.database.read() as session:
        kept = await session.get(EntityRow, mortal.id)
        assert kept is not None and kept.name == "Una's choice"
    forced = await edit(team.owner, mortal.id, {"name": "Owner's choice"})
    assert forced.status_code == 200
    mine = await revision_of(team.owner, mortal.id)
    assert (await edit(team.owner, mortal.id, {"name": "Owner again"}, expected_revision=opened)).status_code == 409
    assert (await edit(team.owner, mortal.id, {"name": "Owner once more"}, expected_revision=mine)).status_code == 200


async def test_the_last_person_who_changed_a_thing_stays_named_after_the_engine_moves_it(team: Team) -> None:
    workspace = await guild(team)
    mortal = await a_mortal(team)
    editor, _ = await team.member("wen", "editor", workspace)
    assert (await edit(editor, mortal.id, {"title": "Keeper of the ford"})).status_code == 200
    by_person = (await team.owner.get(f"/api/team/revisions/{mortal.id}")).json()
    assert by_person["changed_by"] == "Wen"
    services = await services_of(team)
    async with services.database.write() as session:
        row = await session.get(EntityRow, mortal.id)
        assert row is not None
        row.description = "The world moved this on its own."
    after_engine = (await team.owner.get(f"/api/team/revisions/{mortal.id}")).json()
    assert after_engine["revision"] > by_person["revision"]
    assert after_engine["changed_by"] == "Wen"


async def test_acts_during_an_age_queue_and_apply_after_it_in_order_with_their_authors(team: Team) -> None:
    workspace = await guild(team)
    mortal = await a_mortal(team)
    editor, _ = await team.member("tam", "editor", workspace)
    services = await services_of(team)
    async with an_age(services):
        first = await edit(editor, mortal.id, {"name": "First"}, reason="a better name")
        second = await edit(team.owner, mortal.id, {"name": "Second"})
        cancelled = await edit(editor, mortal.id, {"name": "Never"})
        assert (first.status_code, second.status_code, cancelled.status_code) == (202, 202, 202)
        assert first.json()["queued"]["author"]["name"] == "Tam"
        stranger = await team.owner.get("/api/team")
        assert stranger.json()["queued"] == 3 and stranger.json()["world_busy"] is True
        assert (await editor.delete(f"/api/team/queue/{cancelled.json()['queued']['id']}")).status_code == 200
    applied_first = await settled_act(team.owner, first.json()["queued"]["id"])
    applied_second = await settled_act(team.owner, second.json()["queued"]["id"])
    assert (applied_first["status"], applied_second["status"]) == ("applied", "applied")
    assert applied_first["ledger_entry_id"] < applied_second["ledger_entry_id"]
    ledger = (await team.owner.get("/api/ledger")).json()["entries"]
    by_id = {item["entry"]["id"]: item["entry"] for item in ledger}
    assert by_id[applied_first["ledger_entry_id"]]["author"]["name"] == "Tam"
    assert by_id[applied_first["ledger_entry_id"]]["reason"] == "a better name"
    assert by_id[applied_second["ledger_entry_id"]]["author"]["name"] == "The Owner"
    async with services.database.read() as session:
        kept = await session.get(EntityRow, mortal.id)
        assert kept is not None and kept.name == "Second"


async def test_a_queued_edit_survives_the_age_but_not_another_persons_change(team: Team) -> None:
    workspace = await guild(team)
    mortal = await a_mortal(team)
    editor, _ = await team.member("ren", "editor", workspace)
    services = await services_of(team)
    opened = await revision_of(editor, mortal.id)
    async with an_age(services):
        survives = await edit(editor, mortal.id, {"description": "Written during the age"}, expected_revision=opened)
        assert survives.status_code == 202
    assert (await settled_act(editor, survives.json()["queued"]["id"]))["status"] == "applied"
    opened = await revision_of(editor, mortal.id)
    async with an_age(services):
        between = await edit(team.owner, mortal.id, {"name": "Owner's"})
        clashing = await edit(editor, mortal.id, {"name": "Ren's"}, expected_revision=opened)
        assert (clashing.status_code, between.status_code) == (202, 202)
    failed = await settled_act(editor, clashing.json()["queued"]["id"])
    assert failed["status"] == "failed"
    assert failed["conflict"] and failed["conflict"][0]["field"] == "name"
    notes = (await editor.get("/api/notifications")).json()["items"]
    assert any(item["title"] == "A queued act could not be applied" for item in notes)
    assert not any(item["title"] == "A queued act could not be applied" for item in (await team.owner.get("/api/notifications")).json()["items"])
    stranger, _ = await team.member("sol", "editor", workspace)
    refused = await stranger.post(f"/api/team/queue/{failed['id']}/retry")
    assert refused.status_code == 403
    assert refused.json()["error"].startswith("This act is Ren's")
    retried = await editor.post(f"/api/team/queue/{failed['id']}/retry")
    assert retried.status_code == 200 and retried.json()["status"] == "applied"


async def test_a_cancelled_act_never_runs_and_only_its_author_or_an_admin_cancels(team: Team) -> None:
    workspace = await guild(team)
    mortal = await a_mortal(team)
    editor, _ = await team.member("pia", "editor", workspace)
    other, _ = await team.member("oto", "editor", workspace)
    services = await services_of(team)
    async with an_age(services):
        queued = (await edit(editor, mortal.id, {"name": "Cancelled name"})).json()["queued"]
        refused = await other.delete(f"/api/team/queue/{queued['id']}")
        assert refused.status_code == 403
        assert "Pia" in refused.json()["error"]
        assert (await team.owner.delete(f"/api/team/queue/{queued['id']}")).status_code == 200
        assert (await editor.delete(f"/api/team/queue/{queued['id']}")).status_code == 409
    assert await until(lambda: services.jobs.busy_group("world") is None)
    gone = (await team.owner.get("/api/team/queue", params={"status": "cancelled"})).json()["items"]
    assert gone[0]["cancelled_by"]["name"] == "The Owner"
    async with services.database.read() as session:
        kept = await session.get(EntityRow, mortal.id)
        assert kept is not None and kept.name != "Cancelled name"


async def test_a_demoted_author_s_queued_act_fails_with_the_reason(team: Team) -> None:
    workspace = await guild(team)
    mortal = await a_mortal(team)
    editor, member = await team.member("dee", "editor", workspace)
    services = await services_of(team)
    async with an_age(services):
        queued = (await edit(editor, mortal.id, {"name": "Dee's"})).json()["queued"]
        demoted = await team.owner.patch(f"/api/workspaces/{workspace}/members/{member['account']['id']}", json={"role": "viewer"})
        assert demoted.status_code == 200, demoted.text
    failed = await settled_act(team.owner, queued["id"])
    assert failed["status"] == "failed"
    assert "cannot change the world" in failed["result"]


async def test_canon_approval_turns_an_editors_act_on_held_canon_into_a_proposal(team: Team) -> None:
    workspace = await guild(team)
    mortal = await a_mortal(team)
    editor, _ = await team.member("kai", "editor", workspace)
    held = await team.owner.post("/api/actions/lever:suppress", json={"node_id": mortal.id, "mechanic": "pets", "epochs": 3})
    assert held.status_code == 200, held.text
    switched = await team.owner.put(f"/api/workspaces/{workspace}/universes/{team.universe_id}/access/canon-approval", json={"on": True})
    assert switched.status_code == 200, switched.text
    other = await a_free_mortal(team, mortal.id)
    direct = await edit(editor, other, {"description": "An ordinary change"})
    assert direct.status_code == 200 and direct.json()["proposal"] is None
    proposed = await edit(editor, mortal.id, {"name": "Kai's name"}, reason="it reads better")
    assert proposed.status_code == 202
    proposal = proposed.json()["proposal"]
    assert "held_thing" in proposal["touches"] and proposal["reason"] == "it reads better"
    assert proposal["preview"]["changes"]
    assert (await editor.post(f"/api/team/proposals/{proposal['id']}/approve", json={})).status_code == 403
    services = await services_of(team)
    async with services.database.read() as session:
        untouched = await session.get(EntityRow, mortal.id)
        assert untouched is not None and untouched.name != "Kai's name"
    approved = await team.owner.post(f"/api/team/proposals/{proposal['id']}/approve", json={"note": "yes"})
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved" and approved.json()["decided_by"]["name"] == "The Owner"
    ledger = {item["entry"]["id"]: item["entry"] for item in (await team.owner.get("/api/ledger")).json()["entries"]}
    assert ledger[approved.json()["ledger_entry_id"]]["author"]["name"] == "Kai"
    owners_own = await edit(team.owner, mortal.id, {"name": "Owner never waits"})
    assert owners_own.status_code == 200
    rejected_one = (await edit(editor, mortal.id, {"name": "Rejected"})).json()["proposal"]
    rejected = await team.owner.post(f"/api/team/proposals/{rejected_one['id']}/reject", json={"note": "not now"})
    assert rejected.json()["status"] == "rejected" and rejected.json()["note"] == "not now"
    withdrawn_one = (await edit(editor, mortal.id, {"name": "Withdrawn"})).json()["proposal"]
    assert (await team.owner.post(f"/api/team/proposals/{withdrawn_one['id']}/withdraw")).status_code == 403
    assert (await editor.post(f"/api/team/proposals/{withdrawn_one['id']}/withdraw")).json()["status"] == "withdrawn"
    titles = [item["title"] for item in (await editor.get("/api/notifications")).json()["items"]]
    assert "Your proposal was approved" in titles and "Your proposal was rejected" in titles


async def test_a_lock_release_is_reviewed_but_an_in_world_release_is_not(team: Team) -> None:
    workspace = await guild(team)
    mortal = await a_mortal(team)
    editor, _ = await team.member("lia", "editor", workspace)
    services = await services_of(team)
    async with services.database.write() as session:
        await ensure_profile(session, mortal.id, 1)
    set_value = {"node_id": mortal.id, "table": "mortal_profiles", "column": "wealth", "value": 40, "hold": True}
    placed = await team.owner.post("/api/actions/profile:set", json=set_value)
    assert placed.status_code == 200, placed.text
    await team.owner.put(f"/api/workspaces/{workspace}/universes/{team.universe_id}/access/canon-approval", json={"on": True})
    released = await editor.post("/api/actions/profile:release", json={"node_id": mortal.id, "table": "mortal_profiles", "column": "wealth"})
    assert released.status_code == 202, released.text
    assert "lock_changed" in released.json()["proposal"]["touches"]
    async with services.database.read() as session:
        plain = StateChangeRow(
            epoch=1,
            table_name="entities",
            row_key=f'{{"id": {mortal.id}}}',
            node_id=await a_free_mortal(team, mortal.id),
            operation=LedgerOperation.UPDATE,
            field="description",
            actor_kind=ActorKind.CREATOR,
        )
        reading = await reading_of(session, action("herd:release"), [plain], 1)
    assert not reading.locked


async def a_free_mortal(team: Team, other_than: int) -> int:
    services = await services_of(team)
    async with services.database.read() as session:
        found = await session.scalar(
            select(EntityRow.id)
            .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.id != other_than)
            .order_by(EntityRow.id)
            .limit(1)
        )
    assert found is not None
    return int(found)
