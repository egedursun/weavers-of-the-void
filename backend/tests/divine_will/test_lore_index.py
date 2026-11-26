import asyncio
import itertools
import json
import threading
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import numpy as np
import pytest
from sqlalchemy import func, select

from aerona.db.session import Database
from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.divine_will import DivineWillAttachmentRow, DivineWillChunkRow, DivineWillCycleRow, DivineWillSessionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.records import IncidentStepRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.divine_will import AttachmentKind, AttachmentStatus, ChunkSource, CycleStatus, DivineWillMode, IndexStatus
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.job import JobKind
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.node import ActorKind
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
from aerona.tools.divine_will.catalogue import tool_by_name
from aerona.tools.divine_will.framework import PlayerPort, WillCall, WillResult, invoke
from tests.conftest import OpenDatabase
from tests.divine_will.embedder_fixtures import CountingEmbedder, model_folder
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


def test_reciprocal_rank_fusion_rewards_agreement() -> None:
    a, b, c = (0, 1), (0, 2), (1, 3)
    fused = fuse([[a, b, c], [c, a]])
    assert [key for key, _ in fused] == [a, c, b]
    assert fused[0][1] == 1 / (RRF_K + 1) + 1 / (RRF_K + 2)


def test_fusion_breaks_ties_by_best_rank_then_key() -> None:
    first, second, third = (0, 5), (0, 2), (1, 1)
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


async def test_only_changed_passages_are_embedded_again(tmp_path: Path, open_database: OpenDatabase) -> None:
    database, realm = await open_world(open_database, tmp_path)
    embedder = CountingEmbedder()
    index = LoreIndex(database, Rules, embedder=embedder)
    first = await index.refresh()
    embedded = len(embedder.passages)
    assert first["passages"] == first["embedded"] > 0
    assert embedded == len(set(embedder.passages))
    async with database.read() as session:
        assert await session.scalar(select(func.count()).select_from(DivineWillChunkRow)) == first["passages"]
    await index.refresh()
    assert len(embedder.passages) == embedded
    async with database.write() as session:
        town = await session.get(EntityRow, realm.settlement_id)
        assert town is not None
        town.description = "Brinewatch keeps a lighthouse on the northern cliff and a ferry across the bay."
    await index.refresh()
    again = embedder.passages[embedded:]
    assert again
    assert any("lighthouse" in text for text in again)
    assert len(again) < first["passages"] / 4
    async with database.read() as session:
        owners = set(await session.scalars(select(DivineWillChunkRow.node_id).where(DivineWillChunkRow.text.in_(again))))
    assert owners <= {realm.settlement_id, None}
    fresh = CountingEmbedder()
    reopened = LoreIndex(database, Rules, embedder=fresh)
    await reopened.load()
    await reopened.refresh()
    assert fresh.passages == []
    await database.dispose()


async def test_a_built_index_refreshes_quietly_and_skips_an_unchanged_world(
    tmp_path: Path, open_database: OpenDatabase, monkeypatch: pytest.MonkeyPatch
) -> None:
    database, realm = await open_world(open_database, tmp_path)
    index = LoreIndex(database, Rules, embedder=CountingEmbedder())
    await index.refresh()
    assert index.state().status is IndexStatus.READY
    shown: list[IndexStatus] = []
    original = index._set

    def watched(status: IndexStatus, note: str, *, force: bool = False) -> None:
        shown.append(status)
        original(status, note, force=force)

    monkeypatch.setattr(index, "_set", watched)
    reads: list[str] = []
    gather = index_module.gathered

    def counted(url: str, rules: Rules) -> Any:
        reads.append(url)
        return gather(url, rules)

    monkeypatch.setattr(index_module, "gathered", counted)
    await index.refresh()
    assert reads == []
    async with database.write() as session:
        town = await session.get(EntityRow, realm.settlement_id)
        assert town is not None
        town.description = "A new harbour wall stands where the old one fell."
    await index.refresh()
    assert len(reads) == 1
    assert IndexStatus.BUILDING not in shown
    assert index.state().status is IndexStatus.READY
    await database.dispose()


async def test_an_index_that_waited_for_an_epoch_shows_it_reads_again_at_once(
    tmp_path: Path, open_database: OpenDatabase, monkeypatch: pytest.MonkeyPatch
) -> None:
    database, realm = await open_world(open_database, tmp_path)
    index = LoreIndex(database, Rules, embedder=CountingEmbedder())
    await index.refresh()
    index._set(IndexStatus.WAITING, index_module.EPOCH_RUNNING)
    shown: list[IndexStatus] = []
    original = index._set

    def watched(status: IndexStatus, note: str, *, force: bool = False) -> None:
        shown.append(status)
        original(status, note, force=force)

    monkeypatch.setattr(index, "_set", watched)
    async with database.write() as session:
        town = await session.get(EntityRow, realm.settlement_id)
        assert town is not None
        town.description = "The ferry runs again."
    await index.refresh()
    assert shown[0] is IndexStatus.BUILDING
    assert index.state().status is IndexStatus.READY
    await database.dispose()


async def test_a_restarted_index_leaves_an_unchanged_world_unread(tmp_path: Path, open_database: OpenDatabase, monkeypatch: pytest.MonkeyPatch) -> None:
    database, realm = await open_world(open_database, tmp_path)
    await LoreIndex(database, Rules, embedder=CountingEmbedder()).refresh()
    reads: list[str] = []
    gather = index_module.gathered

    def counted(url: str, rules: Rules) -> Any:
        reads.append(url)
        return gather(url, rules)

    monkeypatch.setattr(index_module, "gathered", counted)
    restarted = LoreIndex(database, Rules, embedder=CountingEmbedder())
    await restarted.load()
    await restarted.refresh()
    assert reads == []
    assert restarted.state().status is IndexStatus.READY
    async with database.write() as session:
        town = await session.get(EntityRow, realm.settlement_id)
        assert town is not None
        town.description = "A bridge now spans the river."
    again = LoreIndex(database, Rules, embedder=CountingEmbedder())
    await again.load()
    await again.refresh()
    assert len(reads) == 1
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
    await database.dispose()


async def test_search_falls_back_to_words_when_the_model_is_missing(tmp_path: Path, open_database: OpenDatabase) -> None:
    database, _realm = await open_world(open_database, tmp_path)
    index = LoreIndex(database, Rules, directory=tmp_path / "no-model")
    assert index.state().status is IndexStatus.UNAVAILABLE
    found = await index.search("Brinewatch")
    assert found.hits and not found.semantic
    assert all(hit.similarity is None and hit.lexical_rank is not None for hit in found.hits)
    assert "words only" in found.note
    assert index.state().status is IndexStatus.UNAVAILABLE
    async with database.read() as session:
        assert await session.scalar(select(func.count()).select_from(DivineWillChunkRow)) == 0
    await database.dispose()


async def test_hybrid_search_fuses_words_and_meaning(tmp_path: Path, open_database: OpenDatabase) -> None:
    database, realm = await open_world(open_database, tmp_path)
    index = LoreIndex(database, Rules, directory=model_folder(), threads=2)
    found = await index.search("Brinewatch")
    assert found.semantic and found.note == ""
    assert found.embedded == found.passages
    best = found.hits[0]
    assert best.node_id == realm.settlement_id and best.lexical_rank is not None and best.similarity is not None
    meaning_only = await index.search("a settlement by the sea", sources=frozenset({ChunkSource.ENTITY}))
    assert meaning_only.hits and all(hit.source is ChunkSource.ENTITY for hit in meaning_only.hits)
    assert index.state().status is IndexStatus.READY
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
    async with database.read() as session:
        rows = await session.scalar(select(func.count()).select_from(DivineWillChunkRow).where(DivineWillChunkRow.source == ChunkSource.ATTACHMENT))
        status = await session.scalar(select(DivineWillAttachmentRow.status).where(DivineWillAttachmentRow.id == attachment_id))
    assert rows and status is AttachmentStatus.INDEXED
    gone = await run(lost, W.ATTACHMENT_SEARCH, {"query": "ferry crossing"})
    assert head_of(gone)["total"] == 0
    hidden = await run(lost, W.SEARCH_LORE, {"query": "ferry"})
    assert '"source": "attachment"' not in hidden.text
    unread = await run(lost, W.ATTACHMENT_READ, {"attachment_id": attachment_id})
    assert unread.is_error
    listed = await run(lost, W.ATTACHMENT_LIST, {})
    assert "field-notes.md" not in listed.text
    await database.dispose()


async def test_the_indexer_follows_world_changes_and_waits_for_epochs(tmp_path: Path, open_database: OpenDatabase, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(index_module, "QUIET_SECONDS", 0.01)
    monkeypatch.setattr(index_module, "POLL_SECONDS", 0.01)
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
    built = len(embedder.passages)
    assert built > 0 and IndexStatus.READY.value in progress
    epoch_done = asyncio.Event()

    async def epoch(_context: JobContext) -> dict[str, int]:
        await epoch_done.wait()
        return {}

    await jobs.submit(JobKind.EPOCH, epoch, exclusive_group=WORLD_GROUP)
    async with database.write() as session:
        town = await session.get(EntityRow, realm.settlement_id)
        assert town is not None
        town.description = "Brinewatch keeps a lighthouse on the northern cliff."
    bus.publish(EventKind.WORLD_CHANGED, {"action": "entity:edit"})
    assert await until(lambda: index.state().status is IndexStatus.WAITING, seconds=30)
    await asyncio.sleep(0.2)
    assert len(embedder.passages) == built
    epoch_done.set()
    assert await until(lambda: any("lighthouse" in text for text in embedder.passages), seconds=60)
    assert await until(lambda: index.state().status is IndexStatus.READY, seconds=60)
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
        session.add(
            StateChangeRow(
                epoch=2,
                year=61,
                table_name="entities",
                row_key=f'{{"id": {realm.people_id}}}',
                node_id=realm.people_id,
                operation=LedgerOperation.UPDATE,
                field="power_level",
                before_number=4.0,
                after_number=5.0,
                actor_kind=ActorKind.ENGINE,
                incident_id=fair.id,
            )
        )
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
    async with database.read() as session:
        chunks = list(await session.scalars(select(DivineWillChunkRow).order_by(DivineWillChunkRow.id)))
    viewed = [chunk.source_id for chunk in chunks if chunk.source is ChunkSource.TYPED_SECTION and chunk.source_id.rsplit(":", 1)[-1] in LEDGER_TITLES]
    told = " ".join(chunk.text for chunk in chunks if chunk.source is ChunkSource.INCIDENT and chunk.source_id == str(fair))
    assert viewed == []
    assert after["passages"] - before["passages"] <= 2
    assert "The Kessar Folk shared their grain." in told and "Cause: A drought emptied the granaries." in told and "Steps: 1." in told
    async with database.read() as session:
        named = [entity.name for entity in await session.scalars(select(EntityRow).where(EntityRow.id.in_(onlookers)).order_by(EntityRow.id))]
    assert all(name in told for name in named)
    await database.dispose()


class GatedEmbedder(CountingEmbedder):
    def __init__(self) -> None:
        super().__init__()
        self.closed = threading.Event()
        self.held = threading.Event()
        self.opened = threading.Event()
        self.finished = threading.Event()
        self.opened.set()

    def embed(self, texts: Sequence[str], role: TextRole) -> Vector:
        if not (self.closed.is_set() and role is TextRole.PASSAGE):
            return super().embed(texts, role)
        self.held.set()
        self.opened.wait()
        found = super().embed(texts, role)
        self.finished.set()
        return found


@dataclass
class WatchedContext(JobContext):
    shares: list[float] = field(default_factory=list)

    def report(self, progress: float, stage: str | None = None) -> None:
        if stage and "/" in stage:
            self.shares.append(progress)
        super().report(progress, stage)


async def test_the_index_job_reports_its_share_by_tokens_read(tmp_path: Path, open_database: OpenDatabase) -> None:
    database, _realm = await open_world(open_database, tmp_path)
    rules = replace(Rules(), divine_will=replace(Rules().divine_will, index_batch=1))
    index = LoreIndex(database, lambda: rules, embedder=CountingEmbedder())
    context = WatchedContext(job_id="index", kind=JobKind.DIVINE_WILL_INDEX, params={}, bus=EventBus())
    await index.refresh(context)
    assert index._world is not None
    tokens = sorted(chunk.tokens for chunk in index._world.chunks)
    expected = list(itertools.accumulate(tokens))
    assert context.shares == pytest.approx([read / expected[-1] for read in expected])
    assert len(set(tokens)) > 1
    await database.dispose()


async def test_a_cancelled_index_job_stays_stopped_until_the_world_changes(
    tmp_path: Path, open_database: OpenDatabase, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(index_module, "QUIET_SECONDS", 0.01)
    monkeypatch.setattr(index_module, "POLL_SECONDS", 0.01)
    database, realm = await open_world(open_database, tmp_path)
    bus = EventBus()
    jobs = JobManager(database, bus)
    embedder = GatedEmbedder()
    index = LoreIndex(database, Rules, embedder=embedder)
    index.attach(bus)
    index.start(jobs)
    assert await until(lambda: index.state().status is IndexStatus.READY and jobs.busy_group(index_module.INDEX_GROUP) is None, seconds=60)
    embedder.closed.set()
    embedder.opened.clear()
    async with database.write() as session:
        town = await session.get(EntityRow, realm.settlement_id)
        assert town is not None
        town.description = "Brinewatch keeps a lighthouse on the northern cliff."
    bus.publish(EventKind.WORLD_CHANGED, {"action": "entity:edit"})
    assert await until(embedder.held.is_set, seconds=60)
    running = jobs.busy_group(index_module.INDEX_GROUP)
    assert running is not None
    await jobs.cancel(running)
    assert await until(lambda: jobs.busy_group(index_module.INDEX_GROUP) is None, seconds=30)
    embedder.closed.clear()
    embedder.opened.set()
    assert await until(embedder.finished.is_set, seconds=30)
    read = len(embedder.passages)
    bus.publish(EventKind.CHANGES_AVAILABLE, {"version": 1})
    await asyncio.sleep(0.3)
    assert jobs.busy_group(index_module.INDEX_GROUP) is None and len(embedder.passages) == read
    assert index.state().status is IndexStatus.WAITING and index.state().note == index_module.STOPPED
    async with database.write() as session:
        town = await session.get(EntityRow, realm.settlement_id)
        assert town is not None
        town.description = "Brinewatch keeps a ferry across the bay."
    bus.publish(EventKind.WORLD_CHANGED, {"action": "entity:edit"})
    assert await until(lambda: any("ferry across the bay" in text for text in embedder.passages), seconds=60)
    assert await until(lambda: index.state().status is IndexStatus.READY, seconds=60)
    await index.stop()
    await jobs.shutdown()
    await database.dispose()
