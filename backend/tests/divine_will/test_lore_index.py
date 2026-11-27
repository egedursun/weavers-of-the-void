import asyncio
import json
import threading
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import numpy as np
import pytest
from sqlalchemy import delete, select
from sqlalchemy import inspect as table_inspect

from aerona.db.session import Database
from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.culture import RumourRow
from aerona.db.tables.divine_will import DivineWillAttachmentRow, DivineWillCycleRow, DivineWillSessionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.military import SpyAgentRow, SpyNetworkRow
from aerona.db.tables.records import IncidentStepRow
from aerona.db.tables.routes import RouteRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.divine_will import AttachmentKind, AttachmentStatus, ChunkSource, CycleStatus, DivineWillMode, IndexStatus
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.job import JobKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction
from aerona.epoch.concurrency import WORLD_GROUP
from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind
from aerona.jobs.context import JobContext
from aerona.jobs.manager import JobManager
from aerona.media.file_store import FileMediaStore
from aerona.prompts.tools.divine_will_ids import DivineWillToolId
from aerona.rules.registry import Rules
from aerona.services.books.records import LEDGER_TITLES
from aerona.services.divine_will import index as index_module
from aerona.services.divine_will.embedding import TextRole, Vector
from aerona.services.divine_will.index import RRF_K, SMALL_SAMPLE, LoreIndex, fuse, relevant
from aerona.services.divine_will.store import WORDS_FOLDER
from aerona.tools.divine_will.catalogue import tool_by_name
from aerona.tools.divine_will.framework import PlayerPort, WillCall, WillResult, invoke
from tests.conftest import OpenDatabase
from tests.divine_will.embedder_fixtures import CountingEmbedder, model_folder
from tests.divine_will.index_documents import documents
from tests.polling import until
from tests.tools.factories import EPOCH, Realm, make_entity, seed_realm

W = DivineWillToolId
CROWD = 40
NOTE_TEXT = "# Field notes\n\nThe ferry of Brinewatch crosses the bay twice a day.\n\nIts keeper writes each crossing in a book."


def head_of(result: WillResult) -> dict[str, Any]:
    head: dict[str, Any] = json.loads(result.text.split("\n", 1)[0])
    return head


def ranks_of(result: WillResult) -> list[int]:
    return [json.loads(line)["rank"] for line in result.text.splitlines() if line.startswith('{"rank"')]


async def open_world(open_database: OpenDatabase, folder: Path) -> tuple[Database, Realm]:
    database = open_database(folder / "lore.db")
    return database, await seed_realm(database)


async def open_cycles(database: Database, statuses: list[CycleStatus]) -> tuple[int, list[int]]:
    async with database.write() as session:
        opened = DivineWillSessionRow(opened_epoch=EPOCH, title="")
        session.add(opened)
        await session.flush()
        rows = [
            DivineWillCycleRow(session_id=opened.id, ordinal=ordinal, mode=DivineWillMode.ASK_LORE, epoch=EPOCH, status=status, player_text="")
            for ordinal, status in enumerate(statuses, start=1)
        ]
        session.add_all(rows)
        await session.flush()
        return opened.id, [row.id for row in rows]


def will_call(database: Database, index: LoreIndex, media: FileMediaStore, cycle: tuple[int, int], rules: Rules) -> WillCall:
    session_id, cycle_id = cycle
    host = SimpleNamespace(lore_index=index, attachment_store=media)
    return WillCall(
        database,
        rules,
        cycle_id=cycle_id,
        session_id=session_id,
        epoch=EPOCH,
        mode=DivineWillMode.ASK_LORE,
        lore_language="english",
        player=cast(PlayerPort, None),
        services=host,
    )


async def run(call: WillCall, tool: DivineWillToolId, arguments: dict[str, Any]) -> WillResult:
    found = tool_by_name(tool.value)
    assert found is not None
    return await invoke(call, found, arguments)


async def describe(database: Database, entity_id: int, text: str) -> None:
    async with database.write() as session:
        entity = await session.get(EntityRow, entity_id)
        assert entity is not None
        entity.description = text


def test_reciprocal_rank_fusion_rewards_agreement() -> None:
    a, b, c = ("entity", "1", 0), ("entity", "2", 0), ("son", "3", 0)
    fused = fuse([[a, b, c], [c, a]])
    assert [key for key, _ in fused] == [a, c, b]
    assert fused[0][1] == 1 / (RRF_K + 1) + 1 / (RRF_K + 2)


def test_fusion_breaks_ties_by_best_rank_then_key() -> None:
    first, second, third = ("entity", "5", 0), ("entity", "2", 0), ("son", "1", 0)
    assert [key for key, _ in fuse([[first, third], [second]])] == [second, first, third]
    assert [key for key, _ in fuse([[second], [first]])] == [second, first]


def test_the_relevance_floor_keeps_small_samples_whole() -> None:
    small = np.linspace(0.1, 0.9, SMALL_SAMPLE - 1, dtype=np.float32)
    assert relevant(small, small).all()
    large = np.concatenate([np.full(500, 0.5, dtype=np.float32), np.asarray([0.9, 0.95], dtype=np.float32)])
    assert relevant(large, large).sum() == 2


def test_a_few_allowed_passages_are_judged_against_the_whole_corpus() -> None:
    corpus = np.concatenate([np.full(500, 0.5, dtype=np.float32), np.asarray([0.9, 0.95], dtype=np.float32)])
    allowed = np.asarray([0.5, 0.51, 0.93], dtype=np.float32)
    assert relevant(allowed, corpus).tolist() == [False, False, True]


async def test_a_change_is_read_alone_and_a_restart_reads_nothing(tmp_path: Path, open_database: OpenDatabase) -> None:
    database, realm = await open_world(open_database, tmp_path)
    embedder = CountingEmbedder()
    index = LoreIndex(database, Rules, embedder=embedder)
    first = await index.refresh()
    embedded = len(embedder.passages)
    assert first["passages"] > first["embedded"] > 0
    assert embedded == len(set(embedder.passages))
    again = await index.refresh()
    assert again["written"] == 0 and len(embedder.passages) == embedded
    await describe(database, realm.settlement_id, "Brinewatch keeps a lighthouse on the northern cliff and a ferry across the bay.")
    changed = await index.refresh()
    fresh = embedder.passages[embedded:]
    assert fresh and all("lighthouse" in text for text in fresh)
    assert 0 < changed["written"] < first["passages"] / 4
    found = await index.search("lighthouse cliff")
    assert found.hits[0].node_id == realm.settlement_id
    await index.stop()
    reopened_embedder = CountingEmbedder()
    reopened = LoreIndex(database, Rules, embedder=reopened_embedder)
    restarted = await reopened.refresh()
    assert restarted["written"] == 0 and reopened_embedder.passages == []
    assert restarted["passages"] == changed["passages"]
    await reopened.stop()
    await database.dispose()


async def plant_spies(database: Database, realm: Realm) -> None:
    async with database.write() as session:
        network = SpyNetworkRow(owner_entity_id=realm.faction_id, target_entity_id=realm.settlement_id, since_epoch=EPOCH)
        session.add(network)
        await session.flush()
        session.add(SpyAgentRow(network_id=network.id))


async def stir(database: Database, realm: Realm) -> None:
    async with database.write() as session:
        await session.execute(delete(SpyNetworkRow).where(SpyNetworkRow.target_entity_id == realm.settlement_id))
        people = await session.get(EntityRow, realm.people_id)
        assert people is not None
        people.name = "Kessar Clans"
        mortal = await session.get(EntityRow, realm.mortal_id)
        assert mortal is not None
        mortal.status = EntityStatus.REJECTED
        route = await session.get(RouteRow, realm.route_id)
        assert route is not None
        await session.delete(route)
        line = ChronicleRow(epoch=EPOCH, year=70, kind=ChronicleKind.WORLD, world_id=realm.cosmos.world_id, text="The Kessar Clans raised a harbour wall.")
        session.add(line)
        await session.flush()
        happening = IncidentRow(
            kind="player.history",
            epoch=EPOCH,
            year=70,
            world_id=realm.cosmos.world_id,
            place_entity_id=realm.settlement_id,
            chronicle_id=line.id,
            magnitude=4,
            locked=[],
        )
        session.add(happening)
        await session.flush()
        session.add(IncidentParticipantRow(incident_id=happening.id, node_id=realm.people_id, role=IncidentRole.ACTOR, position=0))
        session.add(
            IncidentStepRow(incident_id=happening.id, position=0, actor_node_id=realm.people_id, action=StepAction.GIVE, target_node_id=realm.settlement_id)
        )
        session.add(RumourRow(incident_id=happening.id, carrier_entity_id=realm.faction_id, epoch=EPOCH, hops=0, fidelity=80))
        await make_entity(session, "Gull Rock", EntityType.REGION, world_id=realm.cosmos.world_id)
    async with database.write() as session:
        rumour = await session.scalar(select(RumourRow).order_by(RumourRow.id.desc()))
        assert rumour is not None
        rumour.fidelity = 61


async def test_following_the_changes_matches_a_fresh_build(tmp_path: Path, open_database: OpenDatabase) -> None:
    database, realm = await open_world(open_database, tmp_path)
    await plant_spies(database, realm)
    followed = LoreIndex(database, Rules, embedder=CountingEmbedder(), folder=tmp_path / "followed")
    await followed.refresh()
    before = documents(followed)
    assert any(key[0] == ChunkSource.TYPED_SECTION.value and key[1].startswith(f"{SpyAgentRow.__tablename__}:") for key in before)
    await stir(database, realm)
    await followed.refresh()
    after = documents(followed)
    fresh = LoreIndex(database, Rules, embedder=CountingEmbedder(), folder=tmp_path / "fresh")
    await fresh.refresh()
    built = documents(fresh)
    assert after == built
    renamed = [key for key in after if key not in before or before[key] != after[key]]
    assert any(key[0] == ChunkSource.TYPED_SECTION.value for key in renamed)
    assert any(key[0] == ChunkSource.INCIDENT.value for key in renamed)
    assert not any(key[0] == ChunkSource.ENTITY.value and key[1] == str(realm.mortal_id) for key in after)
    assert not any(key[0] == ChunkSource.TYPED_SECTION.value and key[1].startswith(f"{RouteRow.__tablename__}:") for key in after)
    assert not any(key[0] == ChunkSource.TYPED_SECTION.value and key[1].startswith(f"{SpyAgentRow.__tablename__}:") for key in after)
    assert any(key[0] == ChunkSource.TYPED_SECTION.value and key[1].startswith(f"{RouteRow.__tablename__}:") for key in before)
    told = await followed.search("Kessar Clans harbour wall")
    assert told.hits and "Kessar Clans" in told.hits[0].text
    named = await followed.search("Kessar", sources=frozenset({ChunkSource.ENTITY}))
    assert any(hit.record == str(realm.people_id) and hit.text.startswith("Kessar Clans") for hit in named.hits)
    await followed.stop()
    await fresh.stop()
    await database.dispose()


async def test_a_natural_question_finds_its_record_by_words(tmp_path: Path, open_database: OpenDatabase) -> None:
    database, realm = await open_world(open_database, tmp_path)
    fair, _onlookers = await crowded_fair(database, realm)
    index = LoreIndex(database, Rules, directory=tmp_path / "no-model")
    found = await index.search("When did the Kessar Folk share their grain with the town?")
    assert not found.semantic
    assert any(hit.source is ChunkSource.INCIDENT and hit.record == str(fair) for hit in found.hits[:3])
    await index.stop()
    await database.dispose()


async def test_paging_reaches_every_hit(tmp_path: Path, open_database: OpenDatabase) -> None:
    database, _realm = await open_world(open_database, tmp_path)
    index = LoreIndex(database, Rules, embedder=CountingEmbedder())
    session_id, (cycle_id,) = await open_cycles(database, [CycleStatus.RUNNING])
    rules = replace(Rules(), divine_will=replace(Rules().divine_will, search_page=3))
    call = will_call(database, index, FileMediaStore(tmp_path / "media"), (session_id, cycle_id), rules)
    first = await run(call, W.SEARCH_LORE, {"query": "Kessar Folk"})
    head = head_of(first)
    assert head["total"] > 3 and head["next"]
    ranks = ranks_of(first)
    page = 1
    while head["next"]:
        page += 1
        following = await run(call, W.SEARCH_LORE, {"handle": head["handle"], "page": page})
        assert not following.is_error, following.text
        head = head_of(following)
        ranks += ranks_of(following)
    assert ranks == list(range(1, head["total"] + 1))
    past = await run(call, W.SEARCH_LORE, {"handle": head["handle"], "page": page + 5})
    assert head_of(past)["shown"] == 0
    await index.stop()
    await database.dispose()


async def test_search_falls_back_to_words_when_the_model_is_missing(tmp_path: Path, open_database: OpenDatabase) -> None:
    database, _realm = await open_world(open_database, tmp_path)
    index = LoreIndex(database, Rules, directory=tmp_path / "no-model")
    assert index.state().status is IndexStatus.UNAVAILABLE
    found = await index.search("Brinewatch")
    assert found.hits and not found.semantic
    assert all(hit.similarity is None and hit.lexical_rank is not None for hit in found.hits)
    assert "words only" in found.note
    state = index.state()
    assert state.status is IndexStatus.UNAVAILABLE and state.embedded == 0 and state.passages > 0
    await index.stop()
    await database.dispose()


async def test_hybrid_search_fuses_words_and_meaning(tmp_path: Path, open_database: OpenDatabase) -> None:
    database, realm = await open_world(open_database, tmp_path)
    index = LoreIndex(database, Rules, directory=model_folder(), threads=2)
    found = await index.search("Brinewatch")
    assert found.semantic and found.note == ""
    best = found.hits[0]
    assert best.node_id == realm.settlement_id and best.lexical_rank is not None and best.similarity is not None
    meaning_only = await index.search("a settlement by the sea", sources=frozenset({ChunkSource.ENTITY}))
    assert meaning_only.hits and all(hit.source is ChunkSource.ENTITY for hit in meaning_only.hits)
    assert all(hit.similarity is not None for hit in meaning_only.hits[:3])
    assert index.state().status is IndexStatus.READY
    await index.stop()
    await database.dispose()


async def attach(database: Database, media: FileMediaStore, cycle_id: int) -> int:
    key = "divine-will/notes/document.md"
    await media.put(key, NOTE_TEXT.encode())
    async with database.write() as session:
        row = DivineWillAttachmentRow(
            cycle_id=cycle_id,
            kind=AttachmentKind.DOCUMENT,
            filename="field-notes.md",
            mime="text/markdown",
            size=len(NOTE_TEXT),
            media_key=key,
            markdown_key=key,
            status=AttachmentStatus.CONVERTED,
            note="",
        )
        session.add(row)
        await session.flush()
        return row.id


async def test_attachment_passages_leave_retrieval_with_their_cycle(tmp_path: Path, open_database: OpenDatabase) -> None:
    database, _realm = await open_world(open_database, tmp_path)
    media = FileMediaStore(tmp_path / "media")
    embedder = CountingEmbedder()
    index = LoreIndex(database, Rules, embedder=embedder, media=media)
    session_id, (old, _middle, current) = await open_cycles(database, [CycleStatus.DONE, CycleStatus.DONE, CycleStatus.RUNNING])
    attachment_id = await attach(database, media, old)
    remembering = Rules()
    forgetting = replace(remembering, divine_will=replace(remembering.divine_will, remembered_cycles=1))
    kept = will_call(database, index, media, (session_id, current), remembering)
    lost = will_call(database, index, media, (session_id, current), forgetting)
    found = await run(kept, W.ATTACHMENT_SEARCH, {"query": "ferry crossing"})
    assert '"source": "attachment"' in found.text and "ferry of Brinewatch" in found.text
    lore = await run(kept, W.SEARCH_LORE, {"query": "ferry", "sources": ["attachment"]})
    assert f'"record": "{attachment_id}"' in lore.text
    assert any(key[0] == ChunkSource.ATTACHMENT.value for key in documents(index))
    async with database.read() as session:
        status = await session.scalar(select(DivineWillAttachmentRow.status).where(DivineWillAttachmentRow.id == attachment_id))
    assert status is AttachmentStatus.INDEXED
    gone = await run(lost, W.ATTACHMENT_SEARCH, {"query": "ferry crossing"})
    assert head_of(gone)["total"] == 0
    hidden = await run(lost, W.SEARCH_LORE, {"query": "ferry"})
    assert '"source": "attachment"' not in hidden.text
    unread = await run(lost, W.ATTACHMENT_READ, {"attachment_id": attachment_id})
    assert unread.is_error
    listed = await run(lost, W.ATTACHMENT_LIST, {})
    assert "field-notes.md" not in listed.text
    await index.stop()
    await database.dispose()


async def test_the_index_follows_the_world_while_an_epoch_runs(tmp_path: Path, open_database: OpenDatabase, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(index_module, "QUIET_SECONDS", 0.01)
    monkeypatch.setattr(index_module, "FOLLOW_SECONDS", 0.05)
    database, realm = await open_world(open_database, tmp_path)
    bus = EventBus()
    jobs = JobManager(database, bus)
    embedder = CountingEmbedder()
    index = LoreIndex(database, Rules, embedder=embedder)
    index.attach(bus)
    progress: list[str] = []
    bus.add_listener(lambda event: progress.append(event.payload["status"]) if event.kind is EventKind.DIVINE_WILL_INDEX_PROGRESS else None)
    index.start(jobs)
    assert await until(lambda: index.state().status is IndexStatus.READY and jobs.busy_group(index_module.INDEX_GROUP) is None, seconds=60)
    assert IndexStatus.BUILDING.value in progress and IndexStatus.READY.value in progress
    epoch_done = asyncio.Event()

    async def epoch(_context: JobContext) -> dict[str, int]:
        await epoch_done.wait()
        return {}

    await jobs.submit(JobKind.EPOCH, epoch, exclusive_group=WORLD_GROUP)
    await describe(database, realm.settlement_id, "Brinewatch keeps a lighthouse on the northern cliff.")
    bus.publish(EventKind.ENGINE_PHASE, {"phase": "settlements"})
    assert await until(lambda: any("lighthouse" in text for text in embedder.passages), seconds=60)
    assert jobs.busy_group(WORLD_GROUP) is not None
    found = await index.search("lighthouse")
    assert found.hits and found.hits[0].node_id == realm.settlement_id
    epoch_done.set()
    await index.stop()
    await jobs.shutdown()
    await database.dispose()


async def crowded_fair(database: Database, realm: Realm) -> tuple[int, list[int]]:
    async with database.write() as session:
        cause_line = ChronicleRow(epoch=2, year=60, kind=ChronicleKind.WORLD, world_id=realm.cosmos.world_id, text="A drought emptied the granaries.")
        line = ChronicleRow(epoch=2, year=61, kind=ChronicleKind.WORLD, world_id=realm.cosmos.world_id, text="The Kessar Folk shared their grain.")
        session.add_all([cause_line, line])
        await session.flush()
        cause = IncidentRow(kind="player.history", epoch=2, year=60, world_id=realm.cosmos.world_id, chronicle_id=cause_line.id, magnitude=5, locked=[])
        session.add(cause)
        await session.flush()
        fair = IncidentRow(
            kind="player.history",
            epoch=2,
            year=61,
            world_id=realm.cosmos.world_id,
            place_entity_id=realm.settlement_id,
            chronicle_id=line.id,
            cause_incident_id=cause.id,
            magnitude=5,
            locked=[],
        )
        session.add(fair)
        await session.flush()
        session.add(IncidentParticipantRow(incident_id=fair.id, node_id=realm.people_id, role=IncidentRole.ACTOR, position=0))
        session.add(IncidentStepRow(incident_id=fair.id, position=0, actor_node_id=realm.people_id, action=StepAction.GIVE, target_node_id=realm.settlement_id))
        onlookers = [
            (await make_entity(session, f"Onlooker {number:02d}", EntityType.MORTAL, world_id=realm.cosmos.world_id, location_id=realm.settlement_id)).id
            for number in range(CROWD)
        ]
        return fair.id, onlookers


async def test_the_index_reads_each_happening_once_and_no_view_of_the_ledger(tmp_path: Path, open_database: OpenDatabase) -> None:
    database, realm = await open_world(open_database, tmp_path)
    fair, onlookers = await crowded_fair(database, realm)
    index = LoreIndex(database, Rules, embedder=CountingEmbedder())
    before = await index.refresh()
    async with database.write() as session:
        session.add_all(
            IncidentParticipantRow(incident_id=fair, node_id=onlooker, role=IncidentRole.WITNESS, position=number + 1)
            for number, onlooker in enumerate(onlookers)
        )
    after = await index.refresh()
    held = documents(index)
    assert not any(key[0] == ChunkSource.TYPED_SECTION.value and key[1].split(":", 1)[0] in LEDGER_TITLES for key in held)
    assert not any(key[0] == ChunkSource.TYPED_SECTION.value and key[1].startswith(StateChangeRow.__tablename__) for key in held)
    assert after["passages"] - before["passages"] <= 2
    told = " ".join(hit.text for hit in (await index.search("Kessar Folk shared grain")).hits if hit.source is ChunkSource.INCIDENT and hit.record == str(fair))
    assert "The Kessar Folk shared their grain." in told and "Cause: A drought emptied the granaries." in told and "Steps: 1." in told
    async with database.read() as session:
        named = [entity.name for entity in await session.scalars(select(EntityRow).where(EntityRow.id.in_(onlookers)).order_by(EntityRow.id))]
    assert any(key[0] == ChunkSource.INCIDENT.value and key[1] == str(fair) for key in held)
    shown = " ".join(hit.text for hit in (await index.search(" ".join(named))).hits if hit.record == str(fair))
    assert all(name in shown for name in named)
    await index.stop()
    await database.dispose()


@dataclass
class WatchedContext(JobContext):
    shares: list[float] = field(default_factory=list)

    def report(self, progress: float, stage: str | None = None) -> None:
        if stage and "/" in stage:
            self.shares.append(progress)
        super().report(progress, stage)


async def test_the_build_reports_its_share_of_the_world_read(tmp_path: Path, open_database: OpenDatabase) -> None:
    database, _realm = await open_world(open_database, tmp_path)
    index = LoreIndex(database, Rules, embedder=CountingEmbedder())
    context = WatchedContext(job_id="index", kind=JobKind.DIVINE_WILL_INDEX, params={}, bus=EventBus())
    await index.refresh(context)
    assert context.shares and context.shares == sorted(context.shares) and context.shares[-1] == pytest.approx(1.0)
    await index.stop()
    await database.dispose()


class GatedEmbedder(CountingEmbedder):
    def __init__(self) -> None:
        super().__init__()
        self.held = threading.Event()
        self.opened = threading.Event()
        self.finished = threading.Event()
        self.opened.set()

    def embed(self, texts: Sequence[str], role: TextRole) -> Vector:
        if role is not TextRole.PASSAGE or self.opened.is_set():
            return super().embed(texts, role)
        self.held.set()
        self.opened.wait()
        found = super().embed(texts, role)
        self.finished.set()
        return found


async def test_a_cancelled_build_stays_stopped_until_the_world_changes(tmp_path: Path, open_database: OpenDatabase, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(index_module, "QUIET_SECONDS", 0.01)
    monkeypatch.setattr(index_module, "FOLLOW_SECONDS", 0.05)
    database, realm = await open_world(open_database, tmp_path)
    bus = EventBus()
    jobs = JobManager(database, bus)
    embedder = GatedEmbedder()
    embedder.opened.clear()
    index = LoreIndex(database, Rules, embedder=embedder)
    index.attach(bus)
    index.start(jobs)
    assert await until(embedder.held.is_set, seconds=60)
    running = jobs.busy_group(index_module.INDEX_GROUP)
    assert running is not None
    await jobs.cancel(running)
    assert await until(lambda: jobs.busy_group(index_module.INDEX_GROUP) is None, seconds=30)
    embedder.opened.set()
    bus.publish(EventKind.CHANGES_AVAILABLE, {"version": 1})
    await asyncio.sleep(0.3)
    assert jobs.busy_group(index_module.INDEX_GROUP) is None
    assert index.state().status is IndexStatus.WAITING and index.state().note == index_module.STOPPED
    await describe(database, realm.settlement_id, "Brinewatch keeps a ferry across the bay.")
    bus.publish(EventKind.WORLD_CHANGED, {"action": "entity:edit"})
    assert await until(lambda: any("ferry across the bay" in text for text in embedder.passages), seconds=60)
    assert await until(lambda: index.state().status is IndexStatus.READY, seconds=60)
    await index.stop()
    await jobs.shutdown()
    await database.dispose()


async def test_the_store_lives_beside_the_world_and_writes_nothing_into_it(tmp_path: Path, open_database: OpenDatabase) -> None:
    database, _realm = await open_world(open_database, tmp_path)
    async with database.read() as session:
        changes = await session.scalar(select(StateChangeRow.id).order_by(StateChangeRow.id.desc()).limit(1))
        tables = await session.run_sync(lambda sync: set(table_inspect(sync.connection()).get_table_names()))
    assert "divine_will_chunks" not in tables
    index = LoreIndex(database, Rules, embedder=CountingEmbedder())
    await index.refresh()
    assert index.folder == (tmp_path / index_module.STORE_FOLDER).resolve()
    assert (index.folder / WORDS_FOLDER).is_dir()
    async with database.read() as session:
        assert await session.scalar(select(StateChangeRow.id).order_by(StateChangeRow.id.desc()).limit(1)) == changes
    await index.stop()
    await database.dispose()
