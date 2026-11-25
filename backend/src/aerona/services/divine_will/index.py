import asyncio
import logging
import sqlite3
import time
from collections import Counter
from collections.abc import AsyncIterator, Callable, Iterable, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from itertools import batched, repeat
from multiprocessing import get_context
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.account_scope import current_account, detached
from aerona.core.grammar import several
from aerona.db.authorship import visible
from aerona.db.record_context import UNCAPTURED
from aerona.db.repositories.divine_will import active_session
from aerona.db.session import Database
from aerona.db.tables.divine_will import DivineWillArtifactRow, DivineWillAttachmentRow, DivineWillChunkRow, DivineWillCycleRow, DivineWillSessionRow
from aerona.db.tables.node import NodeRow
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
from aerona.services.divine_will.passages import SOURCE_ORDER, heading, world_passages
from aerona.services.search import TOKENIZER, fold, match_expression
from aerona.tools.divine_will.retrieval_ports import LoreHit, LoreSearch

logger = logging.getLogger(__name__)

INDEX_GROUP = "divine_will_index"
RRF_K = 60
RELEVANCE_SIGMAS = 2.0
SMALL_SAMPLE = 24
SCORE_BLOCK = 8192
PERSIST_BATCH = 500
LOOKUP_BATCH = 500
QUIET_SECONDS = 3.0
POLL_SECONDS = 2.0
RETRY_SECONDS = 900.0
PARALLEL_PASSAGES = 2000
COUNT_MEMORY = 1 << 18
PARALLEL_SHARES = 4
PROGRESS_SECONDS = 1.0
PERSIST_SECONDS = 60.0
REFRESH_KINDS = frozenset(
    {
        EventKind.EPOCH_FINISHED,
        EventKind.WORLD_CHANGED,
        EventKind.WORLD_REPLACED,
        EventKind.CHANGES_AVAILABLE,
        EventKind.DIVINE_WILL_ARTIFACT_CHANGED,
    }
)
INDEXABLE_ATTACHMENTS = frozenset({AttachmentStatus.CONVERTED, AttachmentStatus.INDEXED})
NO_DIRECTORY = "No folder is set for the embedding model."
EPOCH_RUNNING = "An epoch is running; the index waits for it to end."
GATHERING = "Gathering everything the world holds to read."
CUTTING = "Cutting what it gathered into passages."
ON_DEMAND = "The index is built when the Divine Will first searches."
OTHER_WORK = "Other work is waiting for its turn; the index goes on after it."
REFRESH_FAILED = "The last refresh of the index failed and the next change of the world tries again: {reason}"
MISSING_MODEL = "The embedding model files {names} are missing from {directory}."
WORDS_ONLY = "Passages are matched by their words only, because the meaning index is unavailable. {reason}"
PARTLY = "The meaning index holds {embedded} of {passages} so far; the rest are matched by their words only."
ATTACHMENT_LABEL = "attachment"
WORLD_LAYER = 0
NO_RECORD = -1
SOURCE_CODES = {source: code for code, source in enumerate(ChunkSource)}
ATTACHMENT_LAYER = 1

Matrix = NDArray[np.float16]
Mask = NDArray[np.bool_]
Key = tuple[int, int]
Cached = tuple[Passage, TokenCounter, list[Chunk]]


def never() -> bool:
    return False


def first_state(directory: Path | None, fetch: Fetcher | None, embedder: TextEmbedder | None) -> tuple[IndexStatus, str]:
    if embedder is not None:
        return IndexStatus.WAITING, ON_DEMAND
    if directory is None:
        return IndexStatus.UNAVAILABLE, NO_DIRECTORY
    missing = [file.path for file in MODEL_FILES if not (directory / file.path).is_file()]
    if missing and fetch is None:
        return IndexStatus.UNAVAILABLE, WORDS_ONLY.format(reason=MISSING_MODEL.format(names=", ".join(missing), directory=directory))
    return IndexStatus.WAITING, ON_DEMAND


class Lexical:
    def __init__(self, texts: Iterable[str]) -> None:
        self._connection = sqlite3.connect(":memory:", check_same_thread=False)
        self._connection.execute(f"CREATE VIRTUAL TABLE passages USING fts5(body, tokenize='{TOKENIZER}')")
        self._connection.executemany("INSERT INTO passages(rowid, body) VALUES (?, ?)", ((position, fold(text)) for position, text in enumerate(texts)))
        self._connection.commit()

    def ranked(self, query: str) -> list[int]:
        expression = match_expression(query)
        if not expression:
            return []
        try:
            rows = self._connection.execute("SELECT rowid FROM passages WHERE passages MATCH ? ORDER BY bm25(passages), rowid", (expression,)).fetchall()
        except sqlite3.OperationalError:
            return []
        return [int(row[0]) for row in rows]


@dataclass(frozen=True)
class Hidden:
    artifacts: frozenset[str]
    cycles: frozenset[int]


@dataclass(frozen=True)
class Layer:
    chunks: tuple[Chunk, ...]
    vectors: Matrix
    embedded: Mask
    lexical: Lexical
    parts: Mapping[tuple[ChunkSource, str], int]
    codes: NDArray[np.int64]
    records: NDArray[np.int64]

    @property
    def embedded_count(self) -> int:
        return int(self.embedded.sum())

    def tally(self) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
        size = len(SOURCE_CODES)
        passages = np.bincount(self.codes, minlength=size)
        embedded = np.bincount(self.codes, weights=self.embedded.astype(np.int64), minlength=size)
        return passages.astype(np.int64), embedded.astype(np.int64)


def build_layer(chunks: Sequence[Chunk], known: Mapping[str, Matrix]) -> Layer:
    vectors = np.zeros((len(chunks), DIMENSIONS), dtype=np.float16)
    embedded = np.zeros(len(chunks), dtype=np.bool_)
    for position, chunk in enumerate(chunks):
        found = known.get(chunk.digest)
        if found is not None:
            vectors[position] = found
            embedded[position] = True
    parts = Counter((chunk.source, chunk.source_id) for chunk in chunks)
    codes = np.asarray([SOURCE_CODES[chunk.source] for chunk in chunks], dtype=np.int64)
    records = np.asarray([int(chunk.source_id) if chunk.source_id.isdigit() else NO_RECORD for chunk in chunks], dtype=np.int64)
    return Layer(tuple(chunks), vectors, embedded, Lexical(chunk.text for chunk in chunks), dict(parts), codes, records)


def empty_layer() -> Layer:
    return build_layer([], {})


def known_vectors(layer: Layer | None) -> dict[str, Matrix]:
    if layer is None:
        return {}
    return {chunk.digest: layer.vectors[position] for position, chunk in enumerate(layer.chunks) if layer.embedded[position]}


def fuse(rankings: Sequence[Sequence[Key]], k: int = RRF_K) -> list[tuple[Key, float]]:
    scores: dict[Key, float] = {}
    best: dict[Key, int] = {}
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


def similarities(layer: Layer, query: NDArray[np.float32]) -> NDArray[np.float32]:
    found = np.zeros(len(layer.chunks), dtype=np.float32)
    for start in range(0, len(layer.chunks), SCORE_BLOCK):
        block = layer.vectors[start : start + SCORE_BLOCK].astype(np.float32)
        found[start : start + SCORE_BLOCK] = block @ query
    return found


WORKER_COUNTERS: dict[str, TokenCounter] = {}


def chunked_in_worker(passages: list[Passage], directory: str) -> list[list[Chunk]]:
    count = WORKER_COUNTERS.get(directory)
    if count is None:
        count = WORKER_COUNTERS[directory] = remembered(token_counter(Path(directory)))
    return [chunk_passage(passage, count, EMBEDDER_KEY) for passage in passages]


def remembered(count: TokenCounter) -> TokenCounter:
    return lru_cache(maxsize=COUNT_MEMORY)(count)


def chunk_order(chunk: Chunk) -> tuple[int, str, int]:
    return SOURCE_ORDER[chunk.source], chunk.source_id, chunk.ordinal


def gathered(url: str, rules: Rules) -> list[Passage]:
    async def run() -> list[Passage]:
        database = Database(url)
        try:
            async with database.read() as session:
                return await world_passages(session, rules)
        finally:
            await database.dispose()

    return asyncio.run(run())


def stored(url: str) -> list[tuple[Chunk, bytes]]:
    async def run() -> list[tuple[Chunk, bytes]]:
        database = Database(url)
        row = DivineWillChunkRow
        try:
            async with database.read() as session:
                rows = await session.execute(
                    select(row.source, row.source_id, row.ordinal, row.node_id, row.cycle_id, row.text, row.tokens, row.digest, row.vector).order_by(
                        row.source, row.source_id, row.ordinal
                    )
                )
                return [
                    (Chunk(source, source_id, ordinal, node_id, cycle_id, text, tokens, digest), vector)
                    for source, source_id, ordinal, node_id, cycle_id, text, tokens, digest, vector in rows
                ]
        finally:
            await database.dispose()

    return asyncio.run(run())


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
    sources: tuple[SourceCount, ...]
    built_at: datetime | None
    model: str


class LoreIndex:
    def __init__(
        self,
        database: Database,
        rules: Callable[[], Rules],
        *,
        directory: Path | None = None,
        threads: int = 1,
        fetch: Fetcher | None = None,
        embedder: TextEmbedder | None = None,
        media: MediaStore | None = None,
        bus: EventBus | None = None,
        read_only: Callable[[], bool] = never,
    ) -> None:
        self._database = database
        self._rules = rules
        self._directory = directory
        self._threads = threads
        self._fetch = fetch
        self._embedder = embedder
        self._media = media
        self._bus = bus
        self._read_only = read_only
        self._world: Layer | None = None
        self._attached: Layer | None = None
        self._world_cache: dict[tuple[ChunkSource, str], Cached] = {}
        self._attached_cache: dict[tuple[ChunkSource, str], Cached] = {}
        self._counter: TokenCounter | None = None
        self._world_lock = asyncio.Lock()
        self._attach_lock = asyncio.Lock()
        self._wanted = asyncio.Event()
        self._loaded = asyncio.Event()
        self._reset = False
        self._background = False
        self._built_generation: int | None = None
        self._own_writes = 0
        self._attached_generation: int | None = None
        self._failed_at: float | None = None
        self._status, self._note = first_state(directory, fetch, embedder)
        self._pending = 0
        self._built_at: datetime | None = None
        self._published_at = 0.0
        self._loop: asyncio.AbstractEventLoop | None = None
        self._task: asyncio.Task[None] | None = None
        self._jobs: JobManager | None = None
        self._tasks: set[asyncio.Task[None]] = set()

    def state(self) -> IndexState:
        layers = [layer for layer in (self._world, self._attached) if layer is not None]
        counted = np.zeros(len(SOURCE_CODES), dtype=np.int64)
        vectored = np.zeros(len(SOURCE_CODES), dtype=np.int64)
        for layer in layers:
            found, held = layer.tally()
            counted += found
            vectored += held
        passages = int(counted.sum())
        embedded = int(vectored.sum())
        return IndexState(
            status=self._status,
            note=self._note,
            semantic=self._embedder is not None and embedded > 0,
            passages=passages,
            embedded=embedded,
            pending=self._pending,
            sources=tuple(SourceCount(source, int(counted[code]), int(vectored[code])) for source, code in SOURCE_CODES.items()),
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
        if event.kind not in REFRESH_KINDS:
            return
        if event.kind is EventKind.WORLD_REPLACED:
            self._reset = True
        self._loop.call_soon_threadsafe(self._wanted.set)

    def schedule_attachments(self) -> None:
        task = detached(self._attachments_now())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _attachments_now(self) -> None:
        try:
            await self.refresh_attachments(embed=self._background)
        except Exception:
            logger.exception("the attached documents could not be indexed")

    def start(self, jobs: JobManager) -> None:
        self._jobs = jobs
        self._background = True
        self._loop = asyncio.get_running_loop()
        if self._status is IndexStatus.WAITING:
            self._set(IndexStatus.BUILDING, "")
        self._task = self._loop.create_task(self._run(jobs))

    async def stop(self) -> None:
        for pending in list(self._tasks):
            pending.cancel()
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None

    async def _run(self, jobs: JobManager) -> None:
        try:
            await self.load()
        finally:
            self._loaded.set()
        self._wanted.set()
        while True:
            await self._wanted.wait()
            while self._wanted.is_set():
                self._wanted.clear()
                await asyncio.sleep(QUIET_SECONDS)
            while jobs.busy_group(INDEX_GROUP) is not None or jobs.busy_group(WORLD_GROUP) is not None or self._read_only():
                if jobs.busy_group(WORLD_GROUP) is not None:
                    self._set(IndexStatus.WAITING, EPOCH_RUNNING)
                await asyncio.sleep(POLL_SECONDS)
            try:
                await jobs.submit(JobKind.DIVINE_WILL_INDEX, self._job, exclusive_group=INDEX_GROUP)
            except Exception:
                logger.exception("the divine will index could not be scheduled")

    async def _job(self, context: JobContext) -> dict[str, Any]:
        try:
            counts = await self.refresh(context)
            counts.update(await self.refresh_attachments())
        except Exception as error:
            self._set(IndexStatus.WAITING, REFRESH_FAILED.format(reason=str(error) or type(error).__name__), force=True)
            raise
        return counts

    async def load(self) -> None:
        rows = await asyncio.to_thread(stored, self._url())
        world: list[Chunk] = []
        attached: list[Chunk] = []
        known: dict[str, Matrix] = {}
        for chunk, blob in rows:
            vector = np.frombuffer(blob, dtype=np.float16)
            if vector.size != DIMENSIONS:
                continue
            known[chunk.digest] = vector
            (attached if chunk.source is ChunkSource.ATTACHMENT else world).append(chunk)
        world.sort(key=chunk_order)
        attached.sort(key=chunk_order)
        self._world = await asyncio.to_thread(build_layer, world, known) if world else None
        self._attached = await asyncio.to_thread(build_layer, attached, known) if attached else None
        self._world_cache.clear()
        self._attached_cache.clear()

    @asynccontextmanager
    async def _own_write(self) -> AsyncIterator[AsyncSession]:
        async with self._database.write() as session:
            yield session
        self._own_writes += 1

    def _quiet_since(self, generation: int, writes: int) -> int:
        current = self._database.generation
        return current if current - generation == self._own_writes - writes else generation

    def _url(self) -> str:
        return self._database.engine.url.render_as_string(hide_password=False)

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
            {"indexed": state.embedded, "total": state.passages, "finished": status is IndexStatus.READY, "status": status.value, "note": note},
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
            self._set(IndexStatus.UNAVAILABLE, WORDS_ONLY.format(reason=error))
            return None
        self._counter = None
        return self._embedder

    def _shared_directory(self) -> Path | None:
        directory = self._directory
        portable = isinstance(self._embedder, Embedder) or (self._embedder is None and self._counter is not count_tokens)
        return directory if directory is not None and portable and holds(directory, VOCABULARY_FILE) else None

    async def token_count(self) -> TokenCounter:
        if self._embedder is not None:
            return self._embedder.count
        if self._counter is None:
            directory = self._directory
            self._counter = await asyncio.to_thread(token_counter, directory) if directory is not None else count_tokens
        return self._counter

    def _yield_reason(self) -> str:
        jobs = self._jobs
        if jobs is None:
            return ""
        if jobs.busy_group(WORLD_GROUP) is not None:
            return EPOCH_RUNNING
        return OTHER_WORK if jobs.queued_count > 0 else ""

    async def refresh(self, context: JobContext | None = None) -> dict[str, int]:
        async with self._world_lock:
            if self._reset:
                self._reset = False
                await self.load()
            generation = self._database.generation
            writes = self._own_writes
            if self._world is not None and self._built_generation == generation:
                return {"passages": len(self._world.chunks), "embedded": self._world.embedded_count, "written": 0}
            quiet = self._status is IndexStatus.READY
            self._stage(context, quiet, GATHERING)
            passages = await asyncio.to_thread(gathered, self._url(), self._rules())
            embedder = await self.ready_embedder()
            count = await self.token_count()
            self._stage(context, quiet, CUTTING)
            chunks = await asyncio.to_thread(self._chunked, passages, count, self._world_cache, self._shared_directory(), self._threads)
            known = known_vectors(self._world)
            layer = await asyncio.to_thread(build_layer, chunks, known)
            self._stage(context, quiet, "")
            self._world = layer
            paused = ""
            written = 0
            if embedder is not None:
                paused = await self._embed(embedder, layer, known, context, yielding=True)
                written = await self._persist(layer.chunks, known, None)
            self._built_generation = self._quiet_since(generation, writes)
            self._built_at = datetime.now(UTC)
            self._finish(paused)
            return {"passages": len(layer.chunks), "embedded": layer.embedded_count, "written": written}

    def _stage(self, context: JobContext | None, quiet: bool, note: str) -> None:
        if context is not None:
            context.report(context.progress, note or None)
        if not quiet:
            self._set(IndexStatus.BUILDING, note, force=True)

    def _finish(self, paused: str) -> None:
        if self._embedder is None:
            self._set(IndexStatus.UNAVAILABLE, self._note or NO_DIRECTORY, force=True)
        elif not paused:
            self._set(IndexStatus.READY, "", force=True)
        else:
            self._set(IndexStatus.WAITING, paused, force=True)
            if self._loop is not None:
                self._loop.call_soon_threadsafe(self._wanted.set)

    @staticmethod
    def _chunked(
        passages: Sequence[Passage],
        count: TokenCounter,
        cache: dict[tuple[ChunkSource, str], Cached],
        directory: Path | None = None,
        workers: int = 1,
    ) -> list[Chunk]:
        fresh: dict[tuple[ChunkSource, str], Cached] = {}
        made: dict[tuple[ChunkSource, str], list[Chunk]] = {}
        missing: list[Passage] = []
        for passage in passages:
            key = (passage.source, passage.source_id)
            cached = cache.get(key)
            if cached is not None and cached[0] == passage and cached[1] == count:
                made[key] = cached[2]
            else:
                missing.append(passage)
        if directory is not None and workers > 1 and len(missing) >= PARALLEL_PASSAGES:
            groups = [list(group) for group in batched(missing, max(1, -(-len(missing) // (workers * PARALLEL_SHARES))), strict=False)]
            with ProcessPoolExecutor(max_workers=workers, mp_context=get_context("spawn")) as pool:
                for group, chunked in zip(groups, pool.map(chunked_in_worker, groups, repeat(str(directory))), strict=True):
                    for passage, chunks in zip(group, chunked, strict=True):
                        made[(passage.source, passage.source_id)] = chunks
        else:
            counting = remembered(count)
            for passage in missing:
                made[(passage.source, passage.source_id)] = chunk_passage(passage, counting, EMBEDDER_KEY)
        found: list[Chunk] = []
        for passage in passages:
            key = (passage.source, passage.source_id)
            fresh[key] = (passage, count, made[key])
            found.extend(made[key])
        cache.clear()
        cache.update(fresh)
        return found

    async def _embed(self, embedder: TextEmbedder, layer: Layer, known: dict[str, Matrix], context: JobContext | None, *, yielding: bool) -> str:
        places: dict[str, list[int]] = {}
        for position, chunk in enumerate(layer.chunks):
            if chunk.digest not in known:
                places.setdefault(chunk.digest, []).append(position)
        order = sorted(places, key=lambda digest: (layer.chunks[places[digest][0]].tokens, digest))
        total = len(order)
        self._pending = total
        done = 0
        quiet = self._status is IndexStatus.READY
        persisted_at = time.monotonic()
        for batch in batched(order, max(1, self._rules().divine_will.index_batch), strict=False):
            reason = self._yield_reason() if yielding else ""
            if reason:
                return reason
            texts = [layer.chunks[places[digest][0]].text for digest in batch]
            vectors = await asyncio.to_thread(embedder.embed, texts, TextRole.PASSAGE)
            for digest, vector in zip(batch, vectors, strict=True):
                stored_vector = vector.astype(np.float16)
                known[digest] = stored_vector
                for position in places[digest]:
                    layer.vectors[position] = stored_vector
                    layer.embedded[position] = True
            done += len(batch)
            self._pending = total - done
            if context is not None:
                context.report(done / total, f"{done}/{total}")
            if not quiet:
                self._set(IndexStatus.BUILDING, "")
            if yielding and time.monotonic() - persisted_at >= PERSIST_SECONDS:
                await self._persist(layer.chunks, known, None)
                persisted_at = time.monotonic()
        self._pending = 0
        return ""

    async def _present(self, column: Any, wanted: set[int]) -> set[int]:
        found: set[int] = set()
        async with self._database.read() as session:
            for batch in batched(sorted(wanted), LOOKUP_BATCH, strict=False):
                found.update(await session.scalars(select(column).where(column.in_(batch))))
        return found

    async def _persist(self, chunks: Sequence[Chunk], known: Mapping[str, Matrix], attachments: frozenset[str] | None) -> int:
        row = DivineWillChunkRow
        statement = select(row.id, row.source, row.source_id, row.ordinal, row.digest, row.node_id, row.cycle_id)
        statement = statement.where(row.source != ChunkSource.ATTACHMENT if attachments is None else row.source == ChunkSource.ATTACHMENT)
        async with self._database.read() as session:
            existing = {
                (source, source_id, ordinal): (identity, digest, node_id, cycle_id)
                for identity, source, source_id, ordinal, digest, node_id, cycle_id in await session.execute(statement)
                if attachments is None or source_id in attachments
            }
        nodes = await self._present(NodeRow.id, {chunk.node_id for chunk in chunks if chunk.node_id is not None})
        cycles = await self._present(DivineWillCycleRow.id, {chunk.cycle_id for chunk in chunks if chunk.cycle_id is not None})
        wanted: dict[tuple[ChunkSource, str, int], Chunk] = {}
        for chunk in chunks:
            if chunk.digest in known:
                wanted[chunk.key] = Chunk(
                    chunk.source,
                    chunk.source_id,
                    chunk.ordinal,
                    chunk.node_id if chunk.node_id in nodes else None,
                    chunk.cycle_id if chunk.cycle_id in cycles else None,
                    chunk.text,
                    chunk.tokens,
                    chunk.digest,
                )
        stale = [
            identity
            for key, (identity, digest, node_id, cycle_id) in existing.items()
            if key not in wanted or (wanted[key].digest, wanted[key].node_id, wanted[key].cycle_id) != (digest, node_id, cycle_id)
        ]
        dropped = set(stale)
        fresh = [chunk for key, chunk in wanted.items() if key not in existing or existing[key][0] in dropped]
        epoch = self._database_epoch()
        for batch in batched(stale, PERSIST_BATCH, strict=False):
            async with self._own_write() as session:
                session.info[UNCAPTURED] = True
                await session.execute(delete(row).where(row.id.in_(batch)))
        for part in batched(fresh, PERSIST_BATCH, strict=False):
            async with self._own_write() as session:
                session.info[UNCAPTURED] = True
                await session.execute(
                    insert(row),
                    [
                        {
                            "source": chunk.source,
                            "source_id": chunk.source_id,
                            "node_id": chunk.node_id,
                            "cycle_id": chunk.cycle_id,
                            "ordinal": chunk.ordinal,
                            "text": chunk.text,
                            "tokens": chunk.tokens,
                            "vector": known[chunk.digest].astype(np.float16).tobytes(),
                            "digest": chunk.digest,
                            "updated_epoch": epoch,
                        }
                        for chunk in part
                    ],
                )
        return len(fresh)

    def _database_epoch(self) -> int:
        epoch = self._bus.epoch if self._bus is not None else None
        return max(0, epoch or 0)

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

    async def refresh_attachments(self, *, embed: bool = True) -> dict[str, int]:
        async with self._attach_lock:
            generation = self._database.generation
            passages, chosen = await self._attachment_passages()
            embedder = await self.ready_embedder() if embed else None
            count = await self.token_count()
            chunks = await asyncio.to_thread(self._chunked, passages, count, self._attached_cache)
            known = known_vectors(self._attached)
            layer = await asyncio.to_thread(build_layer, chunks, known)
            self._attached = layer
            written = 0
            if embedder is not None:
                await self._embed(embedder, layer, known, None, yielding=False)
                written = await self._persist(layer.chunks, known, chosen)
                await self._mark_indexed(layer)
            self._attached_generation = generation
            return {"attachment_passages": len(layer.chunks), "attachment_written": written}

    async def _mark_indexed(self, layer: Layer) -> None:
        complete: dict[str, bool] = {}
        for position, chunk in enumerate(layer.chunks):
            complete[chunk.source_id] = complete.get(chunk.source_id, True) and bool(layer.embedded[position])
        ready = sorted(int(source_id) for source_id, whole in complete.items() if whole)
        if not ready:
            return
        async with self._own_write() as session:
            await session.execute(
                update(DivineWillAttachmentRow)
                .where(DivineWillAttachmentRow.id.in_(ready), DivineWillAttachmentRow.status == AttachmentStatus.CONVERTED)
                .values(status=AttachmentStatus.INDEXED)
            )

    async def _lexical_world(self) -> None:
        passages = await asyncio.to_thread(gathered, self._url(), self._rules())
        count = await self.token_count()
        chunks = await asyncio.to_thread(lambda: [chunk for passage in passages for chunk in chunk_passage(passage, count, EMBEDDER_KEY)])
        layer = await asyncio.to_thread(build_layer, chunks, known_vectors(self._world))
        if self._world is None:
            self._world = layer

    async def _ensure_layers(self) -> None:
        if self._background:
            await self._loaded.wait()
            if self._world is None:
                await self._lexical_world()
            if self._attached is None:
                await self.refresh_attachments(embed=False)
            return
        if self._world is None or self._built_generation != self._database.generation:
            await self.refresh()
        if self._attached is None or self._attached_generation != self._database.generation:
            await self.refresh_attachments()

    async def search(self, query: str, *, sources: frozenset[ChunkSource] | None = None, attachments: frozenset[int] = frozenset()) -> LoreSearch:
        await self._ensure_layers()
        embedder = self._embedder if self._background else await self.ready_embedder()
        layers = (self._world or empty_layer(), self._attached or empty_layer())
        hidden = await self._hidden()
        allowed = [
            self._allowed(layers[WORLD_LAYER], sources, None) & self._visible(layers[WORLD_LAYER], hidden),
            self._allowed(layers[ATTACHMENT_LAYER], sources, attachments) & self._visible(layers[ATTACHMENT_LAYER], hidden),
        ]
        text = query.strip()
        rankings: list[list[Key]] = [
            [(number, position) for position in layer.lexical.ranked(text) if allowed[number][position]] for number, layer in enumerate(layers)
        ]
        similarity: dict[Key, float] = {}
        semantic = False
        if embedder is not None and text and any((mask & layer.embedded).any() for mask, layer in zip(allowed, layers, strict=True)):
            semantic = True
            probe = np.asarray(embedder.embed([text], TextRole.QUERY)[0], dtype=np.float32)
            keys: list[Key] = []
            values: list[float] = []
            backdrop: list[NDArray[np.float32]] = []
            for number, layer in enumerate(layers):
                scores = similarities(layer, probe)
                backdrop.append(scores[layer.embedded])
                for position in np.flatnonzero(allowed[number] & layer.embedded):
                    keys.append((number, int(position)))
                    values.append(float(scores[position]))
            sample = np.asarray(values, dtype=np.float32)
            kept = relevant(sample, np.concatenate(backdrop))
            chosen = sorted((index for index in range(len(keys)) if kept[index]), key=lambda index: (-values[index], keys[index]))
            rankings.append([keys[index] for index in chosen])
            similarity = {keys[index]: values[index] for index in range(len(keys))}
        lexical_rank = {key: rank for ranking in rankings[:2] for rank, key in enumerate(ranking, start=1)}
        hits = tuple(self._hit(layers, key, lexical_rank.get(key), similarity.get(key)) for key, _ in fuse(rankings))
        passages = sum(len(layer.chunks) for layer in layers)
        embedded = sum(layer.embedded_count for layer in layers)
        return LoreSearch(hits=hits, semantic=semantic, passages=passages, embedded=embedded, note=self._search_note(semantic, passages, embedded))

    def _search_note(self, semantic: bool, passages: int, embedded: int) -> str:
        if not semantic:
            return WORDS_ONLY.format(reason=self._note or NO_DIRECTORY) if self._embedder is None else ""
        return PARTLY.format(embedded=embedded, passages=several(passages, "passage", "passages")) if embedded < passages else ""

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
    def _visible(layer: Layer, hidden: Hidden) -> Mask:
        if not hidden.artifacts and not hidden.cycles:
            return np.ones(len(layer.chunks), dtype=np.bool_)
        return np.asarray(
            [
                not (
                    (chunk.source is ChunkSource.ARTIFACT and chunk.source_id in hidden.artifacts)
                    or (chunk.cycle_id is not None and chunk.cycle_id in hidden.cycles)
                )
                for chunk in layer.chunks
            ],
            dtype=np.bool_,
        )

    @staticmethod
    def _allowed(layer: Layer, sources: frozenset[ChunkSource] | None, attachments: frozenset[int] | None) -> Mask:
        mask = np.ones(len(layer.chunks), dtype=np.bool_)
        if sources is not None:
            mask &= np.isin(layer.codes, [SOURCE_CODES[source] for source in sources])
        if attachments is not None:
            mask &= np.isin(layer.records, sorted(attachments))
        return mask

    @staticmethod
    def _hit(layers: Sequence[Layer], key: Key, lexical_rank: int | None, similarity: float | None) -> LoreHit:
        layer = layers[key[0]]
        chunk = layer.chunks[key[1]]
        return LoreHit(
            source=chunk.source,
            record=chunk.source_id,
            ordinal=chunk.ordinal,
            parts=layer.parts.get((chunk.source, chunk.source_id), 1),
            node_id=chunk.node_id,
            cycle_id=chunk.cycle_id,
            text=chunk.text,
            tokens=chunk.tokens,
            lexical_rank=lexical_rank,
            similarity=similarity,
        )
