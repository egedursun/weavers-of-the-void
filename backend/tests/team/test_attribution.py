from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from aerona.core.account_scope import AccountRef, acting_account
from aerona.db.tables.agency import ActionRecordRow
from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.divine_will import DivineWillCycleRow, DivineWillSessionRow
from aerona.db.tables.ledger import LedgerEntryRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.divine_will import ArtifactFormat, ArtifactKind, ChunkSource, CycleStatus, DivineWillMode
from aerona.domain.enums.node import ActorKind
from aerona.services.divine_will.library import library_for
from aerona.services.divine_will.runtime import DivineWillRuntime
from aerona.settings import Settings
from aerona.tools.divine_will.library_ports import ArtifactDraft
from tests.accounts.team import Team, team_of
from tests.team.support import a_mortal, edit, guild, services_of

SECRET = "zephyrine quartzwork vellichor"


@pytest.fixture
async def team(settings: Settings) -> AsyncIterator[Team]:
    async with team_of(settings) as made:
        yield made


async def owner_ref(team: Team) -> AccountRef:
    me = (await team.owner.get("/api/team")).json()["me"]
    return AccountRef(me["account_id"], me["name"])


async def member_ref(client: AsyncClient) -> AccountRef:
    me = (await client.get("/api/team")).json()["me"]
    return AccountRef(me["account_id"], me["name"])


async def activity(client: AsyncClient) -> list[dict[str, Any]]:
    response = await client.get("/api/activity-log", params={"after": 0})
    assert response.status_code == 200, response.text
    return list(response.json())


async def test_every_act_names_its_author_and_reason_and_undo_names_who_undid(team: Team) -> None:
    workspace = await guild(team)
    mortal = await a_mortal(team)
    editor, _ = await team.member("nel", "editor", workspace)
    done = await edit(editor, mortal.id, {"title": "Warden"}, reason="the council asked")
    assert done.status_code == 200, done.text
    entry_id = done.json()["ledger_entry_id"]
    services = await services_of(team)
    async with services.database.read() as session:
        entry = await session.get(LedgerEntryRow, entry_id)
        assert entry is not None and (entry.author_name, entry.reason) == ("Nel", "the council asked")
        record = await session.scalar(select(ActionRecordRow).where(ActionRecordRow.ledger_entry_id == entry_id))
        assert record is not None and (record.author_name, record.reason) == ("Nel", "the council asked")
        changes = list(await session.scalars(select(StateChangeRow).where(StateChangeRow.node_id == mortal.id, StateChangeRow.field == "title")))
        assert changes and changes[-1].author_name == "Nel" and changes[-1].changed_at is not None
    history = (await team.owner.get(f"/api/nodes/{mortal.id}/history")).json()
    titled = [item for item in history["changes"] if item["field"] == "title"]
    assert titled and titled[0]["author_name"] == "Nel"
    undone = await team.owner.post(f"/api/ledger/{entry_id}/undo", params={"reason": "not yet"})
    assert undone.status_code == 200, undone.text
    entries = {item["entry"]["id"]: item["entry"] for item in (await editor.get("/api/ledger")).json()["entries"]}
    assert entries[entry_id]["undone_by"]["name"] == "The Owner"
    filtered = (await editor.get("/api/ledger", params={"author_account_id": (await member_ref(editor)).id})).json()["entries"]
    assert [item["entry"]["id"] for item in filtered] == [entry_id]


async def test_acts_from_before_the_team_are_shown_as_the_owners(team: Team) -> None:
    services = await services_of(team)
    async with services.database.write() as session:
        old = LedgerEntryRow(
            epoch=1, actor_kind=ActorKind.CREATOR, actor_node_id=None, actor_name="Creator", tool="record:edit", action_kind=ActionKind.EDIT_RECORD
        )
        session.add(old)
        await session.flush()
        old_id = old.id
    entries = {item["entry"]["id"]: item["entry"] for item in (await team.owner.get("/api/ledger")).json()["entries"]}
    assert entries[old_id]["author"]["name"] == "The Owner"


async def test_the_book_and_the_codex_show_the_hands_of_the_creator(team: Team) -> None:
    workspace = await guild(team)
    mortal = await a_mortal(team)
    editor, _ = await team.member("ash", "editor", workspace)
    assert (await edit(editor, mortal.id, {"title": "Lamplighter of names"}, reason="for the saga")).status_code == 200
    codex = await team.owner.get("/api/codex.md")
    assert codex.status_code == 200, codex.text
    text = codex.text
    assert "### The Hands of the Creator" in text and "#### Ash" in text and "Why: for the saga" in text
    assert "*(by Ash)*" in text
    book = await team.owner.get("/api/book")
    assert "The Hands of the Creator" in book.text and "Why: for the saga" in book.text


async def test_a_deleted_account_stays_in_the_codex_as_a_former_member(team: Team) -> None:
    workspace = await guild(team)
    mortal = await a_mortal(team)
    editor, joined = await team.member("brin", "editor", workspace)
    assert (await edit(editor, mortal.id, {"title": "Keeper of the ford"}, reason="before leaving")).status_code == 200
    gone = await team.owner.delete(f"/api/accounts/{joined['account']['id']}")
    assert gone.status_code == 200, gone.text
    text = (await team.owner.get("/api/codex.md")).text
    assert "#### Brin (former member)" in text
    assert "Why: before leaving" in text


async def test_notes_carry_their_author(team: Team) -> None:
    workspace = await guild(team)
    mortal = await a_mortal(team)
    editor, _ = await team.member("ida", "editor", workspace)
    noted = await editor.put(f"/api/entities/{mortal.id}/note", json={"text": "Watch this one"})
    assert noted.status_code == 200, noted.text
    pinned = await editor.post("/api/map-notes", json={"world_id": mortal.world_id, "x": 1, "y": 2, "text": "A ford"})
    assert pinned.status_code == 200, pinned.text
    notes = (await team.owner.get("/api/notes")).json()
    assert [(item["text"], item["author_name"]) for item in notes["entity_notes"]] == [("Watch this one", "Ida")]
    assert ("A ford", "Ida") in [(item["text"], item["author_name"]) for item in notes["map_notes"]]


async def test_private_writings_stay_private_until_shared(team: Team) -> None:
    workspace = await guild(team)
    reader, _ = await team.member("bor", "editor", workspace)
    services = await services_of(team)
    owner = await owner_ref(team)
    with acting_account(owner):
        made = await library_for(services).artifacts.create(
            ArtifactDraft(f"Notes of {SECRET}", ArtifactKind.STORY, ArtifactFormat.MARKDOWN, f"The {SECRET} of the hills.", "en", DivineWillMode.CREATIVE_WORK)
        )
    artifact_id = made.artifact.id
    assert artifact_id not in [item["id"] for item in (await reader.get("/api/divine-will/artifacts")).json()["items"]]
    assert (await reader.get(f"/api/divine-will/artifacts/{artifact_id}")).status_code == 404
    await services.application.lore_index.refresh()
    with acting_account(await member_ref(reader)):
        hidden = await services.application.lore_index.search(SECRET, sources=frozenset({ChunkSource.ARTIFACT}))
    assert not hidden.hits
    with acting_account(owner):
        seen = await services.application.lore_index.search(SECRET, sources=frozenset({ChunkSource.ARTIFACT}))
    assert seen.hits
    shared = await team.owner.patch(f"/api/divine-will/artifacts/{artifact_id}", json={"shared": True})
    assert shared.status_code == 200 and shared.json()["artifact"]["owner"]["shared"] is True
    assert artifact_id in [item["id"] for item in (await reader.get("/api/divine-will/artifacts")).json()["items"]]
    refused = await reader.patch(f"/api/divine-will/artifacts/{artifact_id}", json={"title": "Mine now"})
    assert refused.status_code == 403 and refused.json()["error"]
    with acting_account(await member_ref(reader)):
        found = await services.application.lore_index.search(SECRET, sources=frozenset({ChunkSource.ARTIFACT}))
    assert found.hits


async def test_a_private_divine_will_session_never_reaches_anyone_else(team: Team) -> None:
    workspace = await guild(team)
    other, _ = await team.member("cyn", "editor", workspace)
    services = await services_of(team)
    owner = await owner_ref(team)
    with acting_account(owner):
        async with services.database.write() as session:
            holder = DivineWillSessionRow(opened_epoch=1)
            session.add(holder)
            await session.flush()
            first = DivineWillCycleRow(session_id=holder.id, ordinal=1, mode=DivineWillMode.ASK_LORE, epoch=1, player_text="hello", status=CycleStatus.RUNNING)
            session.add(first)
            await session.flush()
            holder_id, first_id = holder.id, first.id
    await DivineWillRuntime(services).cancel(first_id)
    finished = [item for item in await activity(other) if item["kind"] == "divine_will.cycle_finished"]
    assert not finished
    assert [item for item in await activity(team.owner) if item["kind"] == "divine_will.cycle_finished"]
    assert (await other.get(f"/api/divine-will/sessions/{holder_id}")).status_code == 404
    assert (await other.get("/api/divine-will/session")).json()["session"] is None
    assert (await other.patch(f"/api/divine-will/sessions/{holder_id}", json={"shared": True})).status_code == 404
    assert (await team.owner.patch(f"/api/divine-will/sessions/{holder_id}", json={"shared": True})).json()["shared"] is True
    async with services.database.write() as session:
        second = DivineWillCycleRow(session_id=holder_id, ordinal=2, mode=DivineWillMode.ASK_LORE, epoch=1, player_text="again", status=CycleStatus.RUNNING)
        session.add(second)
        await session.flush()
        second_id = second.id
    await DivineWillRuntime(services).cancel(second_id)
    reached = [item for item in await activity(other) if item["kind"] == "divine_will.cycle_finished"]
    assert [item["payload"]["cycle_id"] for item in reached] == [second_id]
    assert (await other.get(f"/api/divine-will/sessions/{holder_id}")).json()["session"]["mine"] is False
    assert (await other.post(f"/api/divine-will/cycles/{second_id}/cancel")).status_code == 403


async def test_two_people_summon_the_same_speaker_in_private_audiences(team: Team) -> None:
    workspace = await guild(team)
    mortal = await a_mortal(team)
    other, _ = await team.member("eli", "editor", workspace)
    body = {"node_id": mortal.id, "guise": "ordinary", "record": "off_record"}
    mine = await team.owner.post("/api/presence/sessions", json=body)
    theirs = await other.post("/api/presence/sessions", json=body)
    assert (mine.status_code, theirs.status_code) == (201, 201), (mine.text, theirs.text)
    mine_id, theirs_id = mine.json()["session"]["id"], theirs.json()["session"]["id"]
    assert mine_id != theirs_id
    assert (await other.get(f"/api/presence/sessions/{mine_id}")).status_code == 404
    assert (await other.post(f"/api/presence/sessions/{mine_id}/close")).status_code == 404
    seen = [item for item in await activity(other) if item["kind"] == "presence.session_changed"]
    assert [item["payload"]["session_id"] for item in seen] == [theirs_id]
    assert (await team.owner.get(f"/api/presence/sessions/{mine_id}")).status_code == 200


async def test_each_person_chooses_their_own_notifications_and_read_state(team: Team) -> None:
    workspace = await guild(team)
    other, _ = await team.member("fay", "editor", workspace)
    note = await team.owner.post("/api/notifications", json={"title": "A shared note", "body": "for everyone"})
    assert note.status_code == 200, note.text
    note_id = note.json()["id"]
    assert (await team.owner.post("/api/notifications/read", json={"ids": [note_id]})).status_code == 200
    mine = {item["id"]: item for item in (await team.owner.get("/api/notifications")).json()["items"]}
    theirs = {item["id"]: item for item in (await other.get("/api/notifications")).json()["items"]}
    assert mine[note_id]["is_read"] is True and theirs[note_id]["is_read"] is False
    turned = await other.put("/api/notifications/settings", json={"note": False})
    assert turned.status_code == 200 and turned.json()["note"] is False
    assert note_id not in [item["id"] for item in (await other.get("/api/notifications")).json()["items"]]
    assert note_id in [item["id"] for item in (await team.owner.get("/api/notifications")).json()["items"]]
    assert (await team.owner.get("/api/notifications")).json()["settings"]["note"] is True
