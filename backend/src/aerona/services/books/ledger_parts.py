import asyncio
import shutil
import tempfile
import weakref
from array import array
from collections import defaultdict
from collections.abc import Awaitable, Callable
from concurrent.futures import Executor
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.core.grammar import several, spoken
from aerona.db.base import Base
from aerona.db.profile_guard import table_name
from aerona.db.session import Database
from aerona.db.tables.ages import AgeRow
from aerona.db.tables.changes import StateChangeRow, StateCheckpointRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.services.books.records import (
    CHANGES_TITLE,
    HISTORY_TITLE,
    PHASE_PREFIX,
    REPORT_GROUPS,
    THEN_TITLE,
    ChangeLine,
    Ledger,
    RowStore,
    SpilledRows,
    ToldChange,
    age_spans,
    grouped_changes,
    report_table,
)
from aerona.services.books.typed import RecordTable, TypedIndex, TypedSection, title_of, typed_mappers, words

HAPPENING_HEADERS = ["Moment", "Kind", "Line", "Name", "Place", "Taking part", "Account", "Steps", "Changes", "Rumours", "Cause"]
CHANGES_COLUMN = 8
LOOSE_TITLE = "Changes to records of no single node"
CHECKPOINT_HEADERS = ["Epoch", "Table", "Rows", "Digest", "Last change"]
CHECKPOINT_TITLE = "Checkpoints of the past"
SLICES_PER_WORKER = 2
FieldKey = tuple[str, str]


@dataclass(frozen=True)
class Slice:
    url: str
    names: dict[int, str]
    after: int
    last: int
    path: str


@dataclass
class ChangesTold:
    path: str
    nodes: dict[int | None, array[int]]
    first_seen: dict[int, dict[FieldKey, ChangeLine]]
    last_seen: dict[int, dict[FieldKey, ChangeLine]]
    by_incident: dict[int, list[str]]
    phase_counts: dict[int, int]


@dataclass
class HappeningsTold:
    path: str
    accounts: dict[int, list[tuple[int, int, int]]]
    rows: list[tuple[int, int, bool, list[str]]]
    reports: list[tuple[int, int, RecordTable]]


@dataclass(frozen=True)
class Grouping:
    nodes: list[int | None]
    change_paths: list[str]
    changes: dict[int | None, list[tuple[int, array[int]]]]
    account_paths: list[str]
    accounts: dict[int, list[tuple[int, int, int, int]]]
    path: str


@dataclass
class Grouped:
    path: str
    history: dict[int, array[int]]
    changes: dict[int | None, array[int]]


@dataclass(frozen=True)
class TableJob:
    url: str
    names: dict[int, str]
    tables: list[str]


TableTold = tuple[list[tuple[int, TypedSection]], list[RecordTable]]


@dataclass
class LedgerBook:
    happenings: list[tuple[int, int, bool, list[str]]] = field(default_factory=list)
    reports: list[tuple[int, int, RecordTable]] = field(default_factory=list)
    loose: list[str] = field(default_factory=list)
    by_incident: dict[int, list[str]] = field(default_factory=dict)
    phase_counts: dict[int, int] = field(default_factory=dict)

    def changes_cell(self, incident_id: int, phase: bool) -> str:
        if phase:
            count = self.phase_counts.get(incident_id, 0)
            return f"{several(count, 'change', 'changes')}, each told under the record it changed" if count else ""
        return "; ".join(self.by_incident.get(incident_id, []))


class SliceRunner:
    def __init__(self) -> None:
        self.executor: Executor | None = None
        self.count = 1

    def use(self, executor: Executor, count: int) -> None:
        self.executor = executor
        self.count = count


SLICES = SliceRunner()


def on_database[T](url: str, work: Callable[[AsyncSession], Awaitable[T]]) -> T:
    async def run() -> T:
        database = Database(url)
        try:
            async with database.read() as session:
                return await work(session)
        finally:
            await database.close()

    return asyncio.run(run())


async def tell_changes_in(session: AsyncSession, job: Slice) -> ChangesTold:
    ledger = Ledger(job.names, store=RowStore(Path(job.path)))
    await ledger.load_incidents(session)
    await ledger.load_changes(session, job.after, job.last)
    ledger.store.flush()
    return ChangesTold(
        job.path,
        dict(ledger.changes),
        {node: dict(seen) for node, seen in ledger.first_seen.items()},
        {node: dict(seen) for node, seen in ledger.last_seen.items()},
        dict(ledger.by_incident),
        dict(ledger.phase_counts),
    )


def happening_cells(ledger: Ledger, incident: IncidentRow) -> list[str]:
    cause = ledger.incidents.get(incident.cause_incident_id) if incident.cause_incident_id is not None else None
    line = ledger.line_of(incident)
    return [
        ledger.when(incident),
        words(incident.kind),
        line,
        ledger.name_of(incident),
        ledger.name(incident.place_entity_id),
        ", ".join(f"{spoken(row.role)} {ledger.name_in(row.node_id, line)}" for row in ledger.participants.get(incident.id, [])),
        "; ".join(ledger.fact_text(fact) for fact in ledger.facts.get(incident.id, [])),
        " ".join(ledger.step_text(step, line) for step in ledger.steps.get(incident.id, [])),
        "",
        "; ".join(ledger.rumour_text(rumour) for rumour in ledger.rumours.get(incident.id, [])),
        ledger.line_of(cause) if cause is not None else "",
    ]


async def tell_happenings_in(session: AsyncSession, job: Slice) -> HappeningsTold:
    first = job.after + 1
    ledger = Ledger(job.names, store=RowStore(Path(job.path)))
    await ledger.load_incidents(session)
    await ledger.load_happening_records(session, first, job.last)
    await ledger.load_former_names(session)
    accounts: dict[int, list[tuple[int, int, int]]] = defaultdict(list)
    rows: list[tuple[int, int, bool, list[str]]] = []
    reports: list[tuple[int, int, RecordTable]] = []
    for incident in ledger.incidents.values():
        if not first <= incident.id <= job.last:
            continue
        for node_id in sorted({row.node_id for row in ledger.participants.get(incident.id, [])}):
            accounts[node_id].append((incident.epoch, incident.id, ledger.store.append(ledger.account_text(incident, node_id))))
        rows.append((incident.epoch, incident.id, incident.kind.startswith(PHASE_PREFIX), happening_cells(ledger, incident)))
        spec = INCIDENT_KINDS.get(incident.kind)
        report = REPORT_GROUPS.get(spec.group) if spec is not None else None
        if report is not None and ledger.steps.get(incident.id):
            reports.append((incident.epoch, incident.id, report_table(ledger, incident, report)))
    ledger.store.flush()
    return HappeningsTold(job.path, dict(accounts), rows, reports)


def group_in(job: Grouping) -> Grouped:
    out = RowStore(Path(job.path))
    change_stores = [RowStore(Path(path)) for path in job.change_paths]
    account_stores = [RowStore(Path(path)) for path in job.account_paths]
    history: dict[int, array[int]] = {}
    changes: dict[int | None, array[int]] = {}
    for node in job.nodes:
        told = job.accounts.get(node) if node is not None else None
        if node is not None and told:
            history[node] = array("Q", (out.append(account_stores[store].read(offset)) for _epoch, _id, store, offset in sorted(told)))
        spans = job.changes.get(node)
        if spans:
            lines = (ToldChange.unpacked(change_stores[store].read(offset)) for store, offsets in spans for offset in offsets)
            changes[node] = array("Q", (out.append(text) for text in grouped_changes(lines)))
    out.flush()
    return Grouped(job.path, history, changes)


async def tell_tables_in(session: AsyncSession, job: TableJob) -> dict[str, TableTold]:
    index = TypedIndex(job.names)
    await index.load_references(session)
    await index.load_seasons(session)
    mappers = {table_name(mapper): mapper for mapper in Base.registry.mappers}
    told: dict[str, TableTold] = {}
    for table in job.tables:
        index.sections = defaultdict(list)
        index.records = []
        await index.load_table(session, mappers[table])
        told[table] = ([(node, section) for node, sections in index.sections.items() for section in sections], index.records)
    return told


def tell_tables(job: TableJob) -> dict[str, TableTold]:
    return on_database(job.url, lambda session: tell_tables_in(session, job))


def tell_changes(job: Slice) -> ChangesTold:
    return on_database(job.url, lambda session: tell_changes_in(session, job))


def tell_happenings(job: Slice) -> HappeningsTold:
    return on_database(job.url, lambda session: tell_happenings_in(session, job))


def spans(first: int, last: int, count: int) -> list[tuple[int, int]]:
    size = max(1, -(-(last - first + 1) // count))
    return [(start - 1, min(start + size - 1, last)) for start in range(first, last + 1, size)]


async def table_sizes(session: AsyncSession, tables: list[str]) -> dict[str, int]:
    mappers = {table_name(mapper): mapper for mapper in Base.registry.mappers}
    sizes: dict[str, int] = {}
    for table in tables:
        keys = mappers[table].primary_key
        counted = len(keys) == 1 and isinstance(keys[0].type, Integer)
        sizes[table] = int(await session.scalar(select(func.coalesce(func.max(keys[0]), 0))) or 0) if counted else 0
    return sizes


class Pending[T, J]:
    def __init__(self, jobs: list[J], inside: Callable[[AsyncSession, J], Awaitable[T]], outside: Callable[[J], T]) -> None:
        self.jobs = jobs
        self.inside = inside
        executor = SLICES.executor
        loop = asyncio.get_running_loop()
        self.running = [loop.run_in_executor(executor, outside, job) for job in jobs] if executor is not None else None

    async def done(self, session: AsyncSession) -> list[T]:
        if self.running is None:
            return [await self.inside(session, job) for job in self.jobs]
        return list(await asyncio.gather(*self.running))


@dataclass
class TypedWork:
    tables: list[str]
    pending: Pending[dict[str, TableTold], TableJob] | None


async def start_typed(session: AsyncSession, names: dict[int, str]) -> TypedWork:
    tables = [table_name(mapper) for mapper in typed_mappers()]
    if SLICES.count == 1:
        return TypedWork(tables, None)
    sizes = await table_sizes(session, tables)
    buckets: list[list[str]] = [[] for _ in range(SLICES.count)]
    loads = [0] * SLICES.count
    for table in sorted(tables, key=lambda name: -sizes[name]):
        lightest = loads.index(min(loads))
        buckets[lightest].append(table)
        loads[lightest] += sizes[table] + 1
    url = session.sync_session.get_bind().engine.url.render_as_string(hide_password=False)
    return TypedWork(tables, Pending([TableJob(url, names, bucket) for bucket in buckets if bucket], tell_tables_in, tell_tables))


async def typed_index(session: AsyncSession, names: dict[int, str], work: TypedWork | None = None) -> TypedIndex:
    started = work or await start_typed(session, names)
    if started.pending is None:
        return await TypedIndex.load(session, names)
    index = TypedIndex(names)
    await index.load_references(session)
    await index.load_seasons(session)
    told: dict[str, TableTold] = {}
    for part in await started.pending.done(session):
        told.update(part)
    for table in started.tables:
        sections, records = told[table]
        for node, section in sections:
            index.sections[node].append(section)
        index.records.extend(records)
    return index


async def grouped(jobs: list[Grouping]) -> list[Grouped]:
    executor = SLICES.executor
    if executor is None:
        return [group_in(job) for job in jobs]
    loop = asyncio.get_running_loop()
    return list(await asyncio.gather(*(loop.run_in_executor(executor, group_in, job) for job in jobs)))


def then_and_now(names: dict[int, str], told: list[ChangesTold], node_id: int) -> list[str]:
    ledger = Ledger(names)
    for part in told:
        for key, change in part.first_seen.get(node_id, {}).items():
            ledger.first_seen[node_id].setdefault(key, change)
        ledger.last_seen[node_id].update(part.last_seen.get(node_id, {}))
    return [f"{label}: {text}" for label, text in ledger.then_and_now(node_id)]


@dataclass
class LedgerWork:
    folder: Path
    changes: Pending[ChangesTold, Slice]
    happenings: Pending[HappeningsTold, Slice]


async def happening_spans(session: AsyncSession, count: int) -> list[tuple[int, int]]:
    weights = list(
        await session.execute(
            select(IncidentRow.id, func.count(IncidentParticipantRow.incident_id))
            .outerjoin(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
            .group_by(IncidentRow.id)
            .order_by(IncidentRow.id)
        )
    )
    if not weights:
        return []
    share = max(1, -(-sum(weight + 1 for _id, weight in weights) // count))
    found: list[tuple[int, int]] = []
    after = int(weights[0][0]) - 1
    load = 0
    for incident_id, weight in weights:
        load += weight + 1
        if load >= share:
            found.append((after, int(incident_id)))
            after, load = int(incident_id), 0
    if after < int(weights[-1][0]):
        found.append((after, int(weights[-1][0])))
    return found


async def start_ledger(session: AsyncSession, names: dict[int, str]) -> LedgerWork:
    folder = Path(tempfile.mkdtemp(prefix="aerona-ledger-"))
    url = session.sync_session.get_bind().engine.url.render_as_string(hide_password=False)
    count = SLICES.count * SLICES_PER_WORKER if SLICES.count > 1 else 1
    last_change = int(await session.scalar(select(func.coalesce(func.max(StateChangeRow.id), 0))) or 0)
    change_jobs = [
        Slice(url, names, after, last, str(folder / f"changes-{number}"))
        for number, (after, last) in enumerate(spans(1, last_change, max(1, count // SLICES_PER_WORKER)))
    ]
    happening_jobs = [
        Slice(url, names, after, last, str(folder / f"happenings-{number}")) for number, (after, last) in enumerate(await happening_spans(session, count))
    ]
    return LedgerWork(folder, Pending(change_jobs, tell_changes_in, tell_changes), Pending(happening_jobs, tell_happenings_in, tell_happenings))


async def add_history_sections(session: AsyncSession, index: TypedIndex, work: LedgerWork | None = None) -> LedgerBook:
    started = work or await start_ledger(session, index.names)
    folder = started.folder
    count = SLICES.count
    told = await started.changes.done(session)
    happened = await started.happenings.done(session)
    changes: dict[int | None, list[tuple[int, array[int]]]] = defaultdict(list)
    for number, part in enumerate(told):
        for node, offsets in part.nodes.items():
            changes[node].append((number, offsets))
    accounts: dict[int, list[tuple[int, int, int, int]]] = defaultdict(list)
    for number, happening in enumerate(happened):
        for node, entries in happening.accounts.items():
            accounts[node].extend((epoch, incident_id, number, offset) for epoch, incident_id, offset in entries)
    nodes = sorted({*accounts, *(node for node in changes if node is not None)})
    buckets: list[list[int | None]] = [[] for _ in range(count)]
    for position, node in enumerate(nodes):
        buckets[position % count].append(node)
    buckets[0].append(None)
    grouping = [
        Grouping(
            bucket,
            [part.path for part in told],
            {node: changes[node] for node in bucket if node in changes},
            [happening.path for happening in happened],
            {node: accounts[node] for node in bucket if node is not None and node in accounts},
            str(folder / f"grouped-{number}"),
        )
        for number, bucket in enumerate(buckets)
    ]
    finished = await grouped(grouping)
    stores = [RowStore(Path(done.path)) for done in finished]
    weakref.finalize(stores[0], shutil.rmtree, folder, True)
    history = {node: (stores[number], offsets) for number, done in enumerate(finished) for node, offsets in done.history.items()}
    merged = {node: (stores[number], offsets) for number, done in enumerate(finished) for node, offsets in done.changes.items()}
    for node in nodes:
        if node in history:
            index.sections[node].append(TypedSection(HISTORY_TITLE, spilled=SpilledRows(*history[node])))
        if node in merged:
            index.sections[node].append(TypedSection(CHANGES_TITLE, spilled=SpilledRows(*merged[node])))
        rows = then_and_now(index.names, told, node)
        if rows:
            index.sections[node].append(TypedSection(THEN_TITLE, rows=rows))
    by_incident: dict[int, list[str]] = defaultdict(list)
    phase_counts: dict[int, int] = defaultdict(int)
    for part in told:
        for incident_id, texts in part.by_incident.items():
            by_incident[incident_id].extend(texts)
        for incident_id, number in part.phase_counts.items():
            phase_counts[incident_id] += number
    loose = list(SpilledRows(*merged[None])) if None in merged else []
    return LedgerBook(
        sorted((row for happening in happened for row in happening.rows), key=lambda row: (row[0], row[1])),
        sorted((report for happening in happened for report in happening.reports), key=lambda report: (report[0], report[1])),
        loose,
        dict(by_incident),
        dict(phase_counts),
    )


async def record_tables(session: AsyncSession, book: LedgerBook) -> list[RecordTable]:
    tables: list[RecordTable] = []
    ages = list(await session.scalars(select(AgeRow).order_by(AgeRow.began_epoch, AgeRow.number)))
    spans_of_ages = age_spans(ages)
    for position, (title, began, ended) in enumerate(spans_of_ages):
        until = ended if ended is not None else (spans_of_ages[position + 1][1] - 1 if position + 1 < len(spans_of_ages) else None)
        table = RecordTable(title, list(HAPPENING_HEADERS))
        for epoch, incident_id, phase, cells in book.happenings:
            if epoch < began or (until is not None and epoch > until):
                continue
            table.rows.append([*cells[:CHANGES_COLUMN], book.changes_cell(incident_id, phase), *cells[CHANGES_COLUMN + 1 :]])
        if table.rows:
            tables.append(table)
    tables.extend(report for _epoch, _id, report in book.reports)
    if book.loose:
        tables.append(RecordTable(LOOSE_TITLE, ["Change"], [[text] for text in book.loose]))
    checkpoints = RecordTable(CHECKPOINT_TITLE, list(CHECKPOINT_HEADERS))
    for row in await session.scalars(select(StateCheckpointRow).order_by(StateCheckpointRow.epoch, StateCheckpointRow.table_name)):
        checkpoints.rows.append([str(row.epoch), title_of(row.table_name), str(row.row_count), row.digest, str(row.last_change_id)])
    if checkpoints.rows:
        tables.append(checkpoints)
    return tables
