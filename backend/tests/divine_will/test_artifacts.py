from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from aerona.core.errors import ConflictError, NotFoundError, ValidationFailedError
from aerona.db.session import Database
from aerona.domain.enums.divine_will import ArtifactFormat, ArtifactKind, ArtifactStatus, DivineWillMode
from aerona.events.kinds import EventKind
from aerona.jobs.manager import JobManager
from aerona.services.divine_will.artifacts import ArtifactLibrary
from aerona.services.divine_will.plans import PlanDesk
from aerona.tools.divine_will.library_ports import ArtifactEdit, ArtifactPatch, InsertSpec, LibraryQuery, LibrarySort, ReplaceSpec, StepDraft
from tests.conftest import OpenDatabase
from tests.divine_will.library_fixtures import Heard, ScriptedPlayer, draft, listening_bus, open_cycle, rule_steps
from tests.tools.factories import Realm, seed_realm


@pytest.fixture
async def database(tmp_path: Path, open_database: OpenDatabase) -> AsyncIterator[Database]:
    found = open_database(tmp_path / "library.db")
    yield found
    await found.dispose()


@pytest.fixture
async def realm(database: Database) -> Realm:
    return await seed_realm(database)


@pytest.fixture
def heard_library(database: Database) -> tuple[ArtifactLibrary, Heard]:
    bus, heard = listening_bus()
    return ArtifactLibrary(database, bus), heard


def replace(old: str, new: str) -> ArtifactEdit:
    return ArtifactEdit(replace=ReplaceSpec(old=old, new=new))


async def test_a_created_artifact_keeps_its_first_version_subjects_and_event(heard_library: tuple[ArtifactLibrary, Heard], realm: Realm) -> None:
    library, heard = heard_library
    view = await library.create(draft(tags=("one", " One ", "two", ""), node_ids=(realm.people_id, realm.son_id)))
    assert view.version == 1
    assert view.artifact.current_version == 1
    assert view.artifact.tags == ["one", "two"]
    assert sorted(subject.node_id for subject in view.artifact.subjects) == sorted([realm.people_id, realm.son_id])
    assert view.artifact.characters == len("First paragraph.\n\nSecond paragraph.")
    assert [event.payload["artifact_id"] for event in heard.of(EventKind.DIVINE_WILL_ARTIFACT_CHANGED)] == [view.artifact.id]


async def test_an_artifact_needs_a_title_a_text_and_real_subjects(heard_library: tuple[ArtifactLibrary, Heard]) -> None:
    library, _ = heard_library
    with pytest.raises(ValidationFailedError):
        await library.create(draft(title="   "))
    with pytest.raises(ValidationFailedError):
        await library.create(draft(body="  \n "))
    with pytest.raises(ValidationFailedError, match="No such subject"):
        await library.create(draft(node_ids=(987654,)))


async def test_every_kind_of_edit_makes_a_new_version_and_keeps_the_old(heard_library: tuple[ArtifactLibrary, Heard], database: Database) -> None:
    library, _ = heard_library
    cycle = await open_cycle(database)
    first = await library.create(draft(body="Alpha one.\n\nBeta two."))
    artifact_id = first.artifact.id
    replaced = await library.edit(artifact_id, [replace("Alpha one.", "Alpha first.")], cycle_id=cycle)
    inserted = await library.edit(artifact_id, [ArtifactEdit(insert_after=InsertSpec(anchor="Alpha first.", text="\n\nMiddle."))], cycle_id=cycle)
    appended = await library.edit(artifact_id, [ArtifactEdit(append="Gamma three.")], cycle_id=cycle)
    rewritten = await library.edit(artifact_id, [ArtifactEdit(rewrite="All new.")], cycle_id=cycle, summary="Started over.")
    assert replaced.body == "Alpha first.\n\nBeta two."
    assert inserted.body == "Alpha first.\n\nMiddle.\n\nBeta two."
    assert appended.body == "Alpha first.\n\nMiddle.\n\nBeta two.\n\nGamma three."
    assert rewritten.body == "All new."
    assert [item.version for item in rewritten.versions] == [1, 2, 3, 4, 5]
    assert rewritten.versions[-1].summary == "Started over."
    assert all(item.cycle_id == cycle for item in rewritten.versions[1:])
    old = await library.read(artifact_id, 2)
    assert old.body == "Alpha first.\n\nBeta two."
    assert old.artifact.current_version == 5
    assert (await library.version(artifact_id, 1)).body == "Alpha one.\n\nBeta two."


async def test_several_edits_in_one_call_make_one_version_each(heard_library: tuple[ArtifactLibrary, Heard]) -> None:
    library, _ = heard_library
    first = await library.create(draft(body="a b c"))
    view = await library.edit(first.artifact.id, [replace("a", "x"), replace("b", "y"), ArtifactEdit(append="z")], cycle_id=None)
    assert view.version == 4
    assert view.body == "x y c\n\nz"


async def test_a_missing_anchor_changes_nothing_and_says_which_edit(heard_library: tuple[ArtifactLibrary, Heard]) -> None:
    library, _ = heard_library
    first = await library.create(draft(body="one two"))
    with pytest.raises(ValidationFailedError, match=r"Edit 2 of 2 .*not found in version 2"):
        await library.edit(first.artifact.id, [replace("one", "uno"), replace("three", "tres")], cycle_id=None)
    after = await library.read(first.artifact.id)
    assert after.version == 1
    assert after.body == "one two"


async def test_an_ambiguous_anchor_is_refused_with_its_count(heard_library: tuple[ArtifactLibrary, Heard]) -> None:
    library, _ = heard_library
    first = await library.create(draft(body="echo and echo"))
    with pytest.raises(ValidationFailedError, match="occurs 2 times"):
        await library.edit(first.artifact.id, [replace("echo", "once")], cycle_id=None)
    with pytest.raises(ValidationFailedError, match="occurs 2 times"):
        await library.edit(first.artifact.id, [ArtifactEdit(insert_after=InsertSpec(anchor="echo", text="!"))], cycle_id=None)
    with pytest.raises(ValidationFailedError, match="as it was"):
        await library.edit(first.artifact.id, [replace("and", "and")], cycle_id=None)
    assert (await library.read(first.artifact.id)).version == 1


async def test_an_edit_holds_exactly_one_change() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        ArtifactEdit(append="x", rewrite="y")
    with pytest.raises(ValueError, match="exactly one"):
        ArtifactEdit()


async def test_the_library_filters_sorts_and_pages(heard_library: tuple[ArtifactLibrary, Heard], realm: Realm) -> None:
    library, _ = heard_library
    poem = await library.create(draft("Zeta", "A short café poem.", kind=ArtifactKind.POEM, language="fr", tags=("verse",), node_ids=(realm.people_id,)))
    story = await library.create(draft("Alpha", "A much longer story about nothing in particular at all.", tags=("prose",)))
    script = await library.create(
        draft("Mid", "INT. ROOM - DAY", kind=ArtifactKind.SCREENPLAY, form=ArtifactFormat.FOUNTAIN, status=ArtifactStatus.FINAL, mode=DivineWillMode.COMMAND)
    )
    everything = await library.library(LibraryQuery())
    assert everything.total == 3
    assert [item.id for item in everything.items] == [script.artifact.id, story.artifact.id, poem.artifact.id]
    assert everything.languages == ["en", "fr"]
    assert everything.tags == ["prose", "verse"]
    assert [item.id for item in (await library.library(LibraryQuery(kind=ArtifactKind.POEM))).items] == [poem.artifact.id]
    assert [item.id for item in (await library.library(LibraryQuery(status=ArtifactStatus.FINAL))).items] == [script.artifact.id]
    assert [item.id for item in (await library.library(LibraryQuery(format=ArtifactFormat.FOUNTAIN))).items] == [script.artifact.id]
    assert [item.id for item in (await library.library(LibraryQuery(language="FR"))).items] == [poem.artifact.id]
    assert [item.id for item in (await library.library(LibraryQuery(mode=DivineWillMode.COMMAND))).items] == [script.artifact.id]
    assert [item.id for item in (await library.library(LibraryQuery(tag="Verse"))).items] == [poem.artifact.id]
    assert [item.id for item in (await library.library(LibraryQuery(node_id=realm.people_id))).items] == [poem.artifact.id]
    assert [item.title for item in (await library.library(LibraryQuery(sort=LibrarySort.TITLE))).items] == ["Alpha", "Mid", "Zeta"]
    assert [item.title for item in (await library.library(LibraryQuery(sort=LibrarySort.LENGTH))).items] == ["Alpha", "Zeta", "Mid"]
    assert [item.title for item in (await library.library(LibraryQuery(sort=LibrarySort.CREATED))).items] == ["Mid", "Alpha", "Zeta"]
    paged = await library.library(LibraryQuery(sort=LibrarySort.TITLE, offset=1, limit=1))
    assert (paged.total, paged.offset, paged.limit, [item.title for item in paged.items]) == (3, 1, 1, ["Mid"])
    assert [item.title for item in (await library.library(LibraryQuery(q="CAFÉ"))).items] == ["Zeta"]
    assert [item.title for item in (await library.library(LibraryQuery(q="alpha"))).items] == ["Alpha"]
    assert (await library.library(LibraryQuery(q="story nothing"))).total == 1
    assert (await library.library(LibraryQuery(q="story absent"))).total == 0


async def test_meaning_orders_word_matches_and_never_adds_others(database: Database) -> None:
    bus, _ = listening_bus()
    plain = ArtifactLibrary(database, bus)
    first = await plain.create(draft("One", "words about harvest"))
    second = await plain.create(draft("Two", "nothing alike"))
    third = await plain.create(draft("Three", "harvest and harvest again"))

    async def by_meaning(query: str) -> list[int]:
        assert query == "harvest"
        return [second.artifact.id, first.artifact.id, third.artifact.id]

    fused = ArtifactLibrary(database, bus, by_meaning)
    found = [item.id for item in (await fused.library(LibraryQuery(q="harvest"))).items]
    assert sorted(found) == sorted([first.artifact.id, third.artifact.id])
    assert second.artifact.id not in found
    assert [item.id for item in (await plain.library(LibraryQuery(q="harvest"))).items] == [third.artifact.id, first.artifact.id]


async def test_a_diff_shows_what_changed_between_versions(heard_library: tuple[ArtifactLibrary, Heard]) -> None:
    library, _ = heard_library
    first = await library.create(draft(body="line one\nline two\nline three\n"))
    await library.edit(first.artifact.id, [replace("line two", "line 2")], cycle_id=None)
    diff = await library.versions_diff(first.artifact.id, 1, 2)
    assert "-line two\n" in diff.text
    assert "+line 2\n" in diff.text
    assert "--- version 1" in diff.text
    assert (diff.added, diff.removed) == (1, 1)
    with pytest.raises(NotFoundError):
        await library.versions_diff(first.artifact.id, 1, 9)


async def test_patching_changes_metadata_but_not_the_text(heard_library: tuple[ArtifactLibrary, Heard], realm: Realm) -> None:
    library, heard = heard_library
    first = await library.create(draft())
    patched = await library.patch(
        first.artifact.id,
        ArtifactPatch(title="Renamed", status=ArtifactStatus.FINAL, tags=["x"], kind=ArtifactKind.NOTES, node_ids=[realm.settlement_id]),
    )
    assert (patched.artifact.title, patched.artifact.status, patched.artifact.tags, patched.artifact.kind) == (
        "Renamed",
        ArtifactStatus.FINAL,
        ["x"],
        ArtifactKind.NOTES,
    )
    assert [subject.node_id for subject in patched.artifact.subjects] == [realm.settlement_id]
    assert patched.version == 1
    assert patched.body == first.body
    with pytest.raises(ConflictError):
        await library.patch(first.artifact.id, ArtifactPatch(kind=ArtifactKind.PLAN))
    with pytest.raises(ValidationFailedError):
        await library.patch(first.artifact.id, ArtifactPatch(node_ids=[987654]))
    assert len(heard.of(EventKind.DIVINE_WILL_ARTIFACT_CHANGED)) == 2


async def test_deleting_removes_the_artifact_and_every_version(heard_library: tuple[ArtifactLibrary, Heard]) -> None:
    library, heard = heard_library
    first = await library.create(draft())
    await library.edit(first.artifact.id, [ArtifactEdit(append="more")], cycle_id=None)
    await library.delete(first.artifact.id)
    with pytest.raises(NotFoundError):
        await library.read(first.artifact.id)
    with pytest.raises(NotFoundError):
        await library.version(first.artifact.id, 1)
    assert heard.of(EventKind.DIVINE_WILL_ARTIFACT_CHANGED)[-1].payload["deleted"] is True


async def test_a_plans_artifact_follows_its_plan_and_is_kept_while_the_plan_is_open(database: Database) -> None:
    bus, _ = listening_bus()
    library = ArtifactLibrary(database, bus)
    desk = PlanDesk(database, bus, JobManager(database, bus), lambda _job: ScriptedPlayer(), rule_steps(database, bus))
    plan = await desk.create("Calm", [StepDraft(title="Settle the mood", action_id="creator:mood", input={"contentment": 60})], cycle_id=None)
    assert plan.artifact_id is not None
    mirror = await library.read(plan.artifact_id)
    assert mirror.artifact.kind is ArtifactKind.PLAN
    assert mirror.artifact.plan_id == plan.id
    assert "Settle the mood" in mirror.body
    with pytest.raises(ConflictError):
        await library.edit(plan.artifact_id, [ArtifactEdit(append="x")], cycle_id=None)
    with pytest.raises(ConflictError):
        await library.patch(plan.artifact_id, ArtifactPatch(kind=ArtifactKind.NOTES))
    with pytest.raises(ConflictError, match="finish or abandon"):
        await library.delete(plan.artifact_id)
    await desk.abandon(plan.id)
    await library.delete(plan.artifact_id)
    assert (await desk.read(plan.id)).artifact_id is None
