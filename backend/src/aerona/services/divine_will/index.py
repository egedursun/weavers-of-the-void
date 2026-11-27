import asyncio
import logging
import tempfile
import time
from collections.abc import Awaitable, Callable, Iterable, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from itertools import batched
from multiprocessing import get_context
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from sqlalchemy import select, text, update
from sqlalchemy.exc import OperationalError

from aerona.core.account_scope import current_account, detached
from aerona.db import record_edits
from aerona.db.authorship import visible
from aerona.db.repositories.divine_will import active_session
from aerona.db.session import Database
from aerona.db.tables.divine_will import DivineWillArtifactRow, DivineWillAttachmentRow, DivineWillCycleRow, DivineWillSessionRow
from aerona.domain.enums.divine_will import AttachmentStatus, ChunkSource, IndexStatus
from aerona.domain.enums.job import JobKind
from aerona.epoch.concurrency import WORLD_GROUP
from aerona.events.bus import Event, EventBus
from aerona.events.kinds import EventKind
from aerona.jobs.context import JobContext
from aerona.jobs.manager import JobManager
from aerona.llm.token_count import count_tokens
from aerona.media.store import MediaStore, read_all
from aerona.rules.registry import Rules
from aerona.services.divine_will import follow
from aerona.services.divine_will.chunking import Chunk, Passage, chunk_passage
from aerona.services.divine_will.embedding import (
    DIMENSIONS,
    EMBEDDER_KEY,
    MODEL_FILES,
    MODEL_NAME,
    VOCABULARY_FILE,
    Embedder,
    EmbedderUnavailableError,
    Fetcher,
    TextEmbedder,
    TextRole,
    ensure_files,
    holds,
    load_embedder,
    token_counter,
)
from aerona.services.divine_will.embedding import (
    Counter as TokenCounter,
)
from aerona.services.divine_will.passages import PassageKey, build_units, heading, keyed_passages, line_ref, unit_passages
from aerona.services.divine_will.store import ChunkKey, Exclusions, Found, Rendered, WordStore, chunk_key
from aerona.services.divine_will.vectors import Vector16, VectorStore
from aerona.tools.divine_will.retrieval_ports import LoreHit, LoreSearch

logger = logging.getLogger(__name__)

INDEX_GROUP = "divine_will_index"
STORE_FOLDER = "divine-will-index"
RRF_K = 60
RELEVANCE_SIGMAS = 2.0
SMALL_SAMPLE = 24
SCORE_BLOCK = 8192
LEXICAL_DEPTH = 1000
RERANK_CANDIDATES = 300
FOLLOW_BATCH = 20000
FOLLOW_SECONDS = 3.0
QUIET_SECONDS = 1.0
RETRY_SECONDS = 900.0
SWEPT_EPOCHS = 2
BUILD_SHARES = 4
MOST_PROCESSES = 4
COUNT_MEMORY = 1 << 18
PROGRESS_SECONDS = 1.0
MEANING_SOURCES = frozenset(
    {
        ChunkSource.ENTITY,
        ChunkSource.SON,
        ChunkSource.FOREIGN_GOD,
        ChunkSource.WORLD,
        ChunkSource.STAR,
        ChunkSource.CREATOR,
        ChunkSource.EPOCH,
        ChunkSource.WORD,
        ChunkSource.COUNCIL,
        ChunkSource.ARTIFACT,
        ChunkSource.NOTE,
        ChunkSource.ATTACHMENT,
    }
)
WAKE_KINDS = frozenset(
    {
        EventKind.EPOCH_FINISHED,
        EventKind.ENGINE_FINISHED,
        EventKind.ENGINE_PHASE,
        EventKind.WORLD_CHANGED,
        EventKind.WORLD_REPLACED,
        EventKind.CHANGES_AVAILABLE,
        EventKind.DIVINE_WILL_ARTIFACT_CHANGED,
    }
)
SWEEP_KINDS = frozenset({EventKind.ENGINE_FINISHED, EventKind.EPOCH_FINISHED, EventKind.WORLD_CHANGED})
INDEXABLE_ATTACHMENTS = frozenset({AttachmentStatus.CONVERTED, AttachmentStatus.INDEXED})
NO_DIRECTORY = "No folder is set for the embedding model."
BUILDING_NOTE = "Reading the whole world once; later changes are read as they happen."
ON_DEMAND = "The index is built when the Divine Will first searches."
STOPPED = "The reading was stopped; it goes on when the world next changes."
REFRESH_FAILED = "The last reading of the world's changes failed and the next change tries again: {reason}"
MISSING_MODEL = "The embedding model files {names} are missing from {directory}."
WORDS_ONLY = "Passages are matched by their words only, because the meaning model is unavailable. {reason}"
UNBUILT = "The index is still being built; what is not read yet is not found."
ATTACHMENT_LABEL = "attachment"
NO_RECORD = -1
SOURCE_CODES = {source: code for code, source in enumerate(ChunkSource)}

Matrix = NDArray[np.float16]
Mask = NDArray[np.bool_]


def never() -> bool:
    return False


def index_processes(threads: int) -> int:
    return max(1, min(threads, MOST_PROCESSES))


def first_state(directory: Path | None, fetch: Fetcher | None, embedder: TextEmbedder | None) -> tuple[IndexStatus, str]:
    if embedder is not None:
        return IndexStatus.WAITING, ON_DEMAND
    if directory is None:
        return IndexStatus.UNAVAILABLE, NO_DIRECTORY
    missing = [file.path for file in MODEL_FILES if not (directory / file.path).is_file()]
    if missing and fetch is None:
        return IndexStatus.UNAVAILABLE, WORDS_ONLY.format(reason=MISSING_MODEL.format(names=", ".join(missing), directory=directory))
    return IndexStatus.WAITING, ON_DEMAND


def fuse(rankings: Sequence[Sequence[ChunkKey]], k: int = RRF_K) -> list[tuple[ChunkKey, float]]:
    scores: dict[ChunkKey, float] = {}
    best: dict[ChunkKey, int] = {}
    for ranking in rankings:
        for rank, key in enumerate(ranking, start=1):
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            best[key] = min(best.get(key, rank), rank)
    ordered = sorted(scores, key=lambda key: (-scores[key], best[key], key))
    return [(key, scores[key]) for key in ordered]


def relevant(scores: NDArray[np.float32], background: NDArray[np.float32]) -> NDArray[np.bool_]:
    if background.size < SMALL_SAMPLE:
        return np.ones(scores.size, dtype=np.bool_)
    floor = float(background.mean()) + RELEVANCE_SIGMAS * float(background.std())
    return np.asarray(scores >= floor, dtype=np.bool_)


def store_folder(database: Database) -> Path:
    path = database.engine.url.database
    if path and path != ":memory:":
        return Path(path).resolve().parent / STORE_FOLDER
    return Path(tempfile.mkdtemp(prefix="divine-will-index-"))


WORKER_COUNTERS: dict[str, TokenCounter] = {}


def remembered(count: TokenCounter) -> TokenCounter:
    return lru_cache(maxsize=COUNT_MEMORY)(count)


def cut(passages: Iterable[Passage], count: TokenCounter) -> list[Rendered]:
    return [Rendered((passage.source, passage.source_id), passage.refs, tuple(chunk_passage(passage, count, EMBEDDER_KEY))) for passage in passages]


def worker_counter(directory: str | None) -> TokenCounter:
    key = directory or ""
    found = WORKER_COUNTERS.get(key)
    if found is None:
        found = WORKER_COUNTERS[key] = remembered(token_counter(Path(directory)) if directory else count_tokens)
    return found


def rendered_in_worker(url: str, keys: list[PassageKey] | None, units: list[str] | None, directory: str | None) -> list[Rendered]:
    async def run() -> list[Passage]:
        database = Database(url)
        try:
            async with database.read() as session:
                if units is not None:
                    return await unit_passages(session, units)
                return await keyed_passages(session, keys or [])
        finally:
            await database.dispose()

    return cut(asyncio.run(run()), worker_counter(directory))


@dataclass(frozen=True)
class MeaningChunk:
    key: ChunkKey
    passage: PassageKey
    digest: str
    code: int
    record: int
    cycle: int


@dataclass(frozen=True)
class Hidden:
    artifacts: frozenset[str]
    cycles: frozenset[int]


@dataclass(frozen=True)
class SourceCount:
    source: ChunkSource
    passages: int
    embedded: int


@dataclass(frozen=True)
class IndexState:
    status: IndexStatus
    note: str
    semantic: bool
    passages: int
    embedded: int
    pending: int
    share: float
    sources: tuple[SourceCount, ...]
    built_at: datetime | None
    model: str


@dataclass
class MeaningLayer:
    keys: list[ChunkKey]
    vectors: Matrix
    codes: NDArray[np.int64]
    records: NDArray[np.int64]
    cycles: NDArray[np.int64]


def meaning_chunk(chunk: Chunk) -> MeaningChunk:
    return MeaningChunk(
        key=chunk_key(chunk),
        passage=(chunk.source, chunk.source_id),
        digest=chunk.digest,
        code=SOURCE_CODES[chunk.source],
        record=int(chunk.source_id) if chunk.source_id.isdigit() else NO_RECORD,
        cycle=NO_RECORD if chunk.cycle_id is None else chunk.cycle_id,
    )


class LoreIndex:
    def __init__(
        self,
        database: Database,
        rules: Callable[[], Rules],
        *,
        directory: Path | None = None,
        threads: int = 1,
        processes: int = 0,
        fetch: Fetcher | None = None,
        embedder: TextEmbedder | None = None,
        media: MediaStore | None = None,
        bus: EventBus | None = None,
        read_only: Callable[[], bool] = never,
        folder: Path | None = None,
    ) -> None:
        self._database = database
        self._rules = rules
        self._directory = directory
        self._threads = threads
        self._processes = processes
        self._fetch = fetch
        self._embedder = embedder
        self._media = media
        self._bus = bus
        self._read_only = read_only
        self._folder = folder or store_folder(database)
        self._store = WordStore(self._folder)
        self._vectors = VectorStore(self._folder)
        self._known: dict[str, Vector16] = {}
        self._meaning: dict[PassageKey, list[MeaningChunk]] = {}
        self._layer: MeaningLayer | None = None
        self._counts: dict[ChunkSource, int] = {}
        self._opened = False
        self._built = False
        self._reset = False
        self._sweep = True
        self._background = False
        self._counter: TokenCounter | None = None
        self._pool: ProcessPoolExecutor | None = None
        self._lock = asyncio.Lock()
        self._wanted = asyncio.Event()
        self._loaded = asyncio.Event()
        self._stopped_at: int | None = None
        self._build_head = 0
        self._words_note = ""
        self._failed_at: float | None = None
        self._status, self._note = first_state(directory, fetch, embedder)
        self._pending = 0
        self._share = 0.0
        self._built_at: datetime | None = None
        self._published_at = 0.0
        self._loop: asyncio.AbstractEventLoop | None = None
        self._task: asyncio.Task[None] | None = None
        self._jobs: JobManager | None = None
        self._tasks: set[asyncio.Task[None]] = set()

    @property
    def folder(self) -> Path:
        return self._folder

    def state(self) -> IndexState:
        held: dict[ChunkSource, int] = dict.fromkeys(ChunkSource, 0)
        for chunks in self._meaning.values():
            for chunk in chunks:
                if chunk.digest in self._known:
                    held[ChunkSource(chunk.key[0])] += 1
        counts = self._counts or dict.fromkeys(ChunkSource, 0)
        embedded = sum(held.values())
        return IndexState(
            status=self._status,
            note=self._note,
            semantic=self._embedder is not None,
            passages=sum(counts.values()),
            embedded=embedded,
            pending=self._pending,
            share=self._share,
            sources=tuple(SourceCount(source, counts.get(source, 0), held[source]) for source in ChunkSource),
            built_at=self._built_at,
            model=MODEL_NAME,
        )

    def attach(self, bus: EventBus) -> None:
        self._bus = bus
        bus.add_listener(self.on_event)

    def on_event(self, event: Event) -> None:
        if self._loop is None:
            return
        if event.kind is EventKind.DIVINE_WILL_CYCLE_STARTED:
            self._loop.call_soon_threadsafe(self.schedule_attachments)
            return
        if event.kind not in WAKE_KINDS:
            return
        if event.kind is EventKind.WORLD_REPLACED:
            self._reset = True
        if event.kind in SWEEP_KINDS:
            self._sweep = True
        self._loop.call_soon_threadsafe(self._wanted.set)

    def schedule_attachments(self) -> None:
        task = detached(self._attachments_now())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _attachments_now(self) -> None:
        try:
            await self.refresh_attachments()
        except Exception:
            logger.exception("the attached documents could not be indexed")

    def start(self, jobs: JobManager) -> None:
        self._jobs = jobs
        self._background = True
        self._loop = asyncio.get_running_loop()
        self._task = self._loop.create_task(self._run(jobs))

    async def stop(self) -> None:
        for pending in list(self._tasks):
            pending.cancel()
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        if self._pool is not None:
            self._pool.shutdown(wait=False, cancel_futures=True)
            self._pool = None
        record_edits.unwatch(self._url())
        await asyncio.to_thread(self._store.close)
        await asyncio.to_thread(self._vectors.close)

    async def _run(self, jobs: JobManager) -> None:
        try:
            await self.load()
        finally:
            self._loaded.set()
        self._wanted.set()
        while True:
            await self._wait()
            if self._read_only():
                continue
            if await self._still_stopped():
                continue
            if self._reset or not self._built:
                if jobs.busy_group(INDEX_GROUP) is None:
                    try:
                        await jobs.submit(JobKind.DIVINE_WILL_INDEX, self._job, exclusive_group=INDEX_GROUP)
                    except Exception:
                        logger.exception("the divine will index could not be scheduled")
                continue
            try:
                await self.follow()
            except asyncio.CancelledError:
                raise
            except Exception as error:
                logger.exception("the divine will index could not read the world's changes")
                self._set(IndexStatus.WAITING, REFRESH_FAILED.format(reason=str(error) or type(error).__name__), force=True)

    async def _wait(self) -> None:
        epoch_running = self._jobs is not None and self._jobs.busy_group(WORLD_GROUP) is not None
        try:
            await asyncio.wait_for(self._wanted.wait(), timeout=FOLLOW_SECONDS if epoch_running or self._pending else None)
        except TimeoutError:
            return
        await asyncio.sleep(QUIET_SECONDS)
        self._wanted.clear()

    async def _job(self, context: JobContext) -> dict[str, Any]:
        try:
            counts = await self.refresh(context)
            counts.update(await self.refresh_attachments())
        except asyncio.CancelledError:
            self._stopped_at = self._build_head
            self._set(IndexStatus.WAITING, STOPPED, force=True)
            raise
        except Exception as error:
            self._set(IndexStatus.WAITING, REFRESH_FAILED.format(reason=str(error) or type(error).__name__), force=True)
            raise
        return counts

    async def _head(self) -> int:
        async with self._database.read() as session:
            return await follow.world_head(session)

    async def _still_stopped(self) -> bool:
        if self._stopped_at is None:
            return False
        if await self._head() == self._stopped_at:
            return True
        self._stopped_at = None
        return False

    async def _schema_mark(self) -> str:
        async with self._database.read() as session:
            try:
                return str(await session.scalar(text("SELECT version_num FROM alembic_version")) or "")
            except OperationalError:
                return ""

    async def load(self) -> None:
        record_edits.watch(self._url())
        schema = await self._schema_mark()
        self._built = await asyncio.to_thread(self._store.open, schema)
        self._known = await asyncio.to_thread(self._vectors.load)
        chunks = await asyncio.to_thread(self._store.chunks_of, MEANING_SOURCES)
        self._meaning = {}
        for chunk in chunks:
            self._meaning.setdefault((chunk.source, chunk.source_id), []).append(meaning_chunk(chunk))
        self._layer = None
        self._counts = await asyncio.to_thread(self._store.counts)
        self._built_at = datetime.fromisoformat(self._store.meta.built_at) if self._store.meta.built_at else None
        self._share = 1.0 if self._built else 0.0
        self._opened = True

    def _set(self, status: IndexStatus, note: str, *, force: bool = False) -> None:
        changed = status is not self._status or note != self._note
        self._status = status
        self._note = note
        now = time.monotonic()
        if self._bus is None or not (changed or force or now - self._published_at >= PROGRESS_SECONDS):
            return
        self._published_at = now
        state = self.state()
        self._bus.publish(
            EventKind.DIVINE_WILL_INDEX_PROGRESS,
            {"indexed": state.passages, "total": state.passages + state.pending, "finished": status is IndexStatus.READY, "status": status.value, "note": note},
        )

    async def ready_embedder(self) -> TextEmbedder | None:
        if self._embedder is not None:
            return self._embedder
        directory = self._directory
        if directory is None:
            self._set(IndexStatus.UNAVAILABLE, NO_DIRECTORY)
            return None
        if self._failed_at is not None and time.monotonic() - self._failed_at < RETRY_SECONDS:
            return None
        try:
            if self._fetch is not None and not await asyncio.to_thread(lambda: all(holds(directory, file) for file in MODEL_FILES)):
                self._set(IndexStatus.FETCHING, "")
            await asyncio.to_thread(ensure_files, directory, self._fetch)
            self._embedder = await asyncio.to_thread(load_embedder, directory, self._threads)
        except (EmbedderUnavailableError, OSError, RuntimeError, ValueError) as error:
            self._failed_at = time.monotonic()
            self._words_note = WORDS_ONLY.format(reason=error)
            self._set(IndexStatus.UNAVAILABLE, self._words_note)
            return None
        self._counter = None
        return self._embedder

    def _shared_directory(self) -> str | None:
        directory = self._directory
        portable = isinstance(self._embedder, Embedder) or (self._embedder is None and self._counter is not count_tokens)
        return str(directory) if directory is not None and portable and holds(directory, VOCABULARY_FILE) else None

    async def token_count(self) -> TokenCounter:
        if self._embedder is not None:
            return self._embedder.count
        if self._counter is None:
            directory = self._directory
            self._counter = await asyncio.to_thread(token_counter, directory) if directory is not None else count_tokens
        return self._counter

    def _worker_pool(self) -> ProcessPoolExecutor:
        if self._pool is None:
            self._pool = ProcessPoolExecutor(max_workers=self._processes, mp_context=get_context("spawn"))
        return self._pool

    def _url(self) -> str:
        return self._database.engine.url.render_as_string(hide_password=False)

    async def _render_keys(self, keys: set[PassageKey]) -> list[Rendered]:
        ordered = sorted(keys, key=lambda key: (key[0].value, key[1]))
        if self._processes > 0:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(self._worker_pool(), rendered_in_worker, self._url(), ordered, None, self._shared_directory())
        async with self._database.read() as session:
            passages = await keyed_passages(session, ordered)
        return cut(passages, remembered(await self.token_count()))

    async def _render_units(self, units: list[str]) -> list[Rendered]:
        if self._processes > 0:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(self._worker_pool(), rendered_in_worker, self._url(), None, units, self._shared_directory())
        async with self._database.read() as session:
            passages = await unit_passages(session, units)
        return cut(passages, remembered(await self.token_count()))

    async def _render_group(self, group: list[str]) -> tuple[int, list[Rendered]]:
        return len(group), await self._render_units(group)

    async def refresh(self, context: JobContext | None = None) -> dict[str, int]:
        async with self._lock:
            if not self._opened:
                await self.load()
            written = 0
            if self._reset or not self._built:
                written += await self._build(context)
            written += await self._follow_now()
            await self._finish()
            return {"passages": sum(self._counts.values()), "embedded": self.state().embedded, "written": written}

    async def follow(self) -> int:
        async with self._lock:
            if not self._opened:
                await self.load()
            if self._reset or not self._built:
                return 0
            written = await self._follow_now()
            await self._finish()
            return written

    async def _build(self, context: JobContext | None) -> int:
        self._reset = False
        self._set(IndexStatus.BUILDING, BUILDING_NOTE, force=True)
        schema = await self._schema_mark()
        await asyncio.to_thread(self._store.reset, schema)
        self._meaning = {}
        self._layer = None
        self._counts = {}
        async with self._database.read() as session:
            start = await follow.heads(session)
            self._build_head = await follow.world_head(session)
        units = build_units()
        shares = max(1, self._processes * BUILD_SHARES) if self._processes > 0 else 1
        groups = [list(group) for group in batched(units, max(1, -(-len(units) // shares)), strict=False)]
        self._pending = len(units)
        self._share = 0.0
        written = 0
        done = 0
        if self._processes > 0:
            finishing: Iterable[Awaitable[tuple[int, list[Rendered]]]] = asyncio.as_completed(
                [asyncio.ensure_future(self._render_group(group)) for group in groups]
            )
        else:
            finishing = (self._render_group(group) for group in groups)
        for finished in finishing:
            size, rendered = await finished
            written += await self._apply(rendered, ())
            done += size
            self._pending = len(units) - done
            self._share = done / len(units)
            if context is not None:
                context.report(done / len(units), f"{done}/{len(units)}")
            self._set(IndexStatus.BUILDING, BUILDING_NOTE)
        self._store.meta.cursors = start
        self._store.meta.built = True
        self._built_at = datetime.now(UTC)
        self._store.meta.built_at = self._built_at.isoformat()
        await asyncio.to_thread(self._store.save_meta)
        await asyncio.to_thread(self._vectors.keep, {chunk.digest for chunks in self._meaning.values() for chunk in chunks})
        self._built = True
        self._sweep = True
        self._share = 1.0
        return written

    async def _follow_now(self) -> int:
        written = 0
        while True:
            edits = record_edits.drain(self._url())
            async with self._database.read() as session:
                affected = await follow.affected_since(session, self._store.meta.cursors, FOLLOW_BATCH, edits)
                sweep = await follow.latest_lines(session, SWEPT_EPOCHS) if self._sweep else None
            keys = set(affected.keys)
            refs = set(affected.refs)
            if sweep is not None:
                self._sweep = False
                every, shown = sweep
                held_keys = [(ChunkSource.CHRONICLE.value, str(line), 0) for line in every]
                held = {int(key[1]) for key in await asyncio.to_thread(self._store.chunks, held_keys)}
                for line in follow.flipped(every, shown, held):
                    keys.add((ChunkSource.CHRONICLE, str(line)))
                    refs.add(line_ref(line))
            written += await self._settle(keys, refs)
            self._store.meta.cursors = affected.cursors
            await asyncio.to_thread(self._store.save_meta)
            if not affected.more:
                break
        async with self._database.read() as session:
            now = await follow.heads(session)
        self._pending = max(0, now[follow.STATE_CURSOR] - self._store.meta.cursors.get(follow.STATE_CURSOR, 0))
        return written

    async def _settle(self, keys: set[PassageKey], refs: set[str]) -> int:
        written = 0
        told: set[str] = set()
        while refs or keys:
            told |= refs
            if refs:
                keys |= await asyncio.to_thread(self._store.dependents, refs)
            if not keys:
                break
            rendered = await self._render_keys(keys)
            removed = keys - {item.key for item in rendered}
            written += await self._apply(rendered, removed)
            refs = follow.removed_refs(removed) - told
            keys = set()
        return written

    async def _apply(self, rendered: Sequence[Rendered], removed: Iterable[PassageKey]) -> int:
        gone = list(removed)
        await asyncio.to_thread(self._store.apply, rendered, gone)
        for key in gone:
            self._meaning.pop(key, None)
        for item in rendered:
            self._meaning.pop(item.key, None)
            if item.key[0] in MEANING_SOURCES and item.chunks:
                self._meaning[item.key] = [meaning_chunk(chunk) for chunk in item.chunks]
        self._layer = None
        self._counts = await asyncio.to_thread(self._store.counts)
        await self._embed_meaning(chunk for item in rendered if item.key[0] in MEANING_SOURCES for chunk in item.chunks)
        return sum(len(item.chunks) for item in rendered)

    async def _embed_meaning(self, chunks: Iterable[Chunk]) -> None:
        missing: dict[str, str] = {}
        for chunk in chunks:
            if chunk.digest not in self._known:
                missing.setdefault(chunk.digest, chunk.text)
        if not missing:
            return
        embedder = await self.ready_embedder()
        if embedder is None:
            return
        await self._embed_texts(embedder, missing)

    async def _embed_texts(self, embedder: TextEmbedder, texts: Mapping[str, str]) -> None:
        order = sorted(texts)
        fresh: dict[str, Vector16] = {}
        for batch in batched(order, max(1, self._rules().divine_will.index_batch), strict=False):
            vectors = await asyncio.to_thread(embedder.embed, [texts[digest] for digest in batch], TextRole.PASSAGE)
            for digest, vector in zip(batch, vectors, strict=True):
                fresh[digest] = vector.astype(np.float16)
        self._known.update(fresh)
        self._layer = None
        await asyncio.to_thread(self._vectors.add, fresh)

    async def _finish(self) -> None:
        if await self.ready_embedder() is None:
            self._set(IndexStatus.UNAVAILABLE, self._words_note or NO_DIRECTORY, force=True)
            return
        self._set(IndexStatus.READY, "", force=self._status is not IndexStatus.READY)

    async def _attachment_passages(self) -> tuple[list[Passage], frozenset[str]]:
        async with self._database.read() as session:
            current = await active_session(session)
            cycles = (
                set(await session.scalars(select(DivineWillCycleRow.id).where(DivineWillCycleRow.session_id == current.id))) if current is not None else set()
            )
            rows = list(
                await session.scalars(
                    select(DivineWillAttachmentRow)
                    .where(DivineWillAttachmentRow.status.in_(INDEXABLE_ATTACHMENTS), DivineWillAttachmentRow.markdown_key != "")
                    .order_by(DivineWillAttachmentRow.id)
                )
            )
        chosen = [row for row in rows if row.cycle_id is None or row.cycle_id in cycles]
        passages: list[Passage] = []
        for row in chosen:
            data = await read_all(self._media, row.markdown_key) if self._media is not None else None
            if data is None:
                continue
            title = heading(row.filename, ATTACHMENT_LABEL)
            passages.append(Passage(ChunkSource.ATTACHMENT, str(row.id), title, data.decode("utf-8", errors="replace"), cycle_id=row.cycle_id))
        return passages, frozenset(str(row.id) for row in chosen)

    async def refresh_attachments(self) -> dict[str, int]:
        async with self._lock:
            if not self._opened:
                await self.load()
            passages, chosen = await self._attachment_passages()
            count = remembered(await self.token_count())
            rendered = cut(passages, count)
            held = {key: chunks for key, chunks in self._meaning.items() if key[0] is ChunkSource.ATTACHMENT}
            fresh = [item for item in rendered if [chunk.digest for chunk in held.get(item.key, [])] != [chunk.digest for chunk in item.chunks]]
            removed = [key for key in held if key[1] not in chosen]
            written = await self._apply(fresh, removed) if fresh or removed else 0
            await self._embed_meaning(chunk for item in rendered for chunk in item.chunks)
            await self._mark_indexed(rendered)
            return {"attachment_passages": sum(len(item.chunks) for item in rendered), "attachment_written": written}

    async def _mark_indexed(self, rendered: Sequence[Rendered]) -> None:
        ready = sorted(int(item.key[1]) for item in rendered if item.chunks and all(chunk.digest in self._known for chunk in item.chunks))
        if not ready or self._read_only():
            return
        async with self._database.write() as session:
            await session.execute(
                update(DivineWillAttachmentRow)
                .where(DivineWillAttachmentRow.id.in_(ready), DivineWillAttachmentRow.status == AttachmentStatus.CONVERTED)
                .values(status=AttachmentStatus.INDEXED)
            )

    async def _ensure_ready(self) -> None:
        if self._background:
            await self._loaded.wait()
            return
        await self.refresh()
        await self.refresh_attachments()

    def _meaning_layer(self) -> MeaningLayer:
        if self._layer is not None:
            return self._layer
        chunks = [
            chunk
            for passage in sorted(self._meaning, key=lambda key: (key[0].value, key[1]))
            for chunk in self._meaning[passage]
            if chunk.digest in self._known
        ]
        vectors = np.zeros((len(chunks), DIMENSIONS), dtype=np.float16)
        for position, chunk in enumerate(chunks):
            vectors[position] = self._known[chunk.digest]
        self._layer = MeaningLayer(
            keys=[chunk.key for chunk in chunks],
            vectors=vectors,
            codes=np.asarray([chunk.code for chunk in chunks], dtype=np.int64),
            records=np.asarray([chunk.record for chunk in chunks], dtype=np.int64),
            cycles=np.asarray([chunk.cycle for chunk in chunks], dtype=np.int64),
        )
        return self._layer

    @staticmethod
    def _allowed(layer: MeaningLayer, exclusions: Exclusions) -> Mask:
        mask = np.ones(len(layer.keys), dtype=np.bool_)
        attachment = SOURCE_CODES[ChunkSource.ATTACHMENT]
        artifact = SOURCE_CODES[ChunkSource.ARTIFACT]
        if exclusions.sources is not None:
            mask &= np.isin(layer.codes, [SOURCE_CODES[source] for source in exclusions.sources])
        if exclusions.attachments is not None:
            kept = [int(record) for record in exclusions.attachments if record.isdigit()]
            mask &= (layer.codes != attachment) | np.isin(layer.records, kept)
        if exclusions.artifacts:
            hidden = [int(record) for record in exclusions.artifacts if record.isdigit()]
            mask &= ~((layer.codes == artifact) & np.isin(layer.records, hidden))
        if exclusions.cycles:
            mask &= ~np.isin(layer.cycles, sorted(exclusions.cycles))
        return mask

    def _dense(self, probe: NDArray[np.float32], exclusions: Exclusions) -> list[tuple[ChunkKey, float]]:
        layer = self._meaning_layer()
        if not layer.keys:
            return []
        scores = np.zeros(len(layer.keys), dtype=np.float32)
        for start in range(0, len(layer.keys), SCORE_BLOCK):
            scores[start : start + SCORE_BLOCK] = layer.vectors[start : start + SCORE_BLOCK].astype(np.float32) @ probe
        allowed = self._allowed(layer, exclusions)
        kept = relevant(scores[allowed], scores)
        positions = np.flatnonzero(allowed)[kept]
        ordered = sorted(positions.tolist(), key=lambda position: (-float(scores[position]), layer.keys[position]))
        return [(layer.keys[position], float(scores[position])) for position in ordered]

    async def _reranked(self, embedder: TextEmbedder, probe: NDArray[np.float32], found: Sequence[Found]) -> list[tuple[ChunkKey, float]]:
        candidates = found[:RERANK_CANDIDATES]
        missing = {item.chunk.digest: item.chunk.text for item in candidates if item.chunk.digest not in self._known}
        if missing:
            await self._embed_texts(embedder, missing)
        scored = [(chunk_key(item.chunk), float(self._known[item.chunk.digest].astype(np.float32) @ probe)) for item in candidates]
        return sorted(scored, key=lambda pair: (-pair[1], pair[0]))

    async def search(
        self, query: str, *, sources: frozenset[ChunkSource] | None = None, attachments: frozenset[int] = frozenset(), reach: int = 0
    ) -> LoreSearch:
        await self._ensure_ready()
        embedder = self._embedder if self._background else await self.ready_embedder()
        hidden = await self._hidden()
        exclusions = Exclusions(sources=sources, attachments=frozenset(str(item) for item in attachments), artifacts=hidden.artifacts, cycles=hidden.cycles)
        words = query.strip()
        found, total = await asyncio.to_thread(self._store.search, words, exclusions, max(LEXICAL_DEPTH, reach))
        held: dict[ChunkKey, tuple[Chunk, int]] = {chunk_key(item.chunk): (item.chunk, item.parts) for item in found}
        lexical = [chunk_key(item.chunk) for item in found]
        rankings: list[list[ChunkKey]] = [lexical]
        similarity: dict[ChunkKey, float] = {}
        semantic = False
        if embedder is not None and words:
            semantic = True
            probe = np.asarray((await asyncio.to_thread(embedder.embed, [words], TextRole.QUERY))[0], dtype=np.float32)
            dense = self._dense(probe, exclusions)
            reranked = await self._reranked(embedder, probe, found)
            rankings.extend([[key for key, _ in dense], [key for key, _ in reranked]])
            similarity = {**dict(dense), **dict(reranked)}
        fused = fuse(rankings)
        missing = [key for key, _ in fused if key not in held]
        if missing:
            held.update(await asyncio.to_thread(self._store.chunks, missing))
        lexical_rank = {key: rank for rank, key in enumerate(lexical, start=1)}
        hits = tuple(self._hit(held[key], lexical_rank.get(key), similarity.get(key)) for key, _ in fused if key in held)
        extra = sum(1 for key, _ in fused if key not in lexical_rank and key in held)
        state = self.state()
        return LoreSearch(
            hits=hits,
            semantic=semantic,
            passages=state.passages,
            embedded=state.embedded,
            note=self._search_note(semantic),
            total=max(len(hits), total + extra),
        )

    def _search_note(self, semantic: bool) -> str:
        if not semantic:
            return (self._words_note or WORDS_ONLY.format(reason=NO_DIRECTORY)) if self._embedder is None else ""
        return UNBUILT if not self._built else ""

    async def _hidden(self) -> Hidden:
        if current_account() is None:
            return Hidden(frozenset(), frozenset())
        async with self._database.read() as session:
            artifacts = await session.scalars(
                select(DivineWillArtifactRow.id).where(~visible(DivineWillArtifactRow.author_account_id, DivineWillArtifactRow.shared))
            )
            cycles = await session.scalars(
                select(DivineWillCycleRow.id)
                .join(DivineWillSessionRow, DivineWillSessionRow.id == DivineWillCycleRow.session_id)
                .where(~visible(DivineWillSessionRow.author_account_id, DivineWillSessionRow.shared))
            )
            return Hidden(frozenset(str(found) for found in artifacts), frozenset(int(found) for found in cycles))

    @staticmethod
    def _hit(held: tuple[Chunk, int], lexical_rank: int | None, similarity: float | None) -> LoreHit:
        chunk, parts = held
        return LoreHit(
            source=chunk.source,
            record=chunk.source_id,
            ordinal=chunk.ordinal,
            parts=parts,
            node_id=chunk.node_id,
            cycle_id=chunk.cycle_id,
            text=chunk.text,
            tokens=chunk.tokens,
            lexical_rank=lexical_rank,
            similarity=similarity,
        )
