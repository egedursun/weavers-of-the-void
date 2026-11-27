import asyncio
import hashlib
import os
import pickle
import shutil
import tempfile
import weakref
from array import array
from collections import defaultdict
from collections.abc import Awaitable, Callable
from concurrent.futures import Executor
from dataclasses import dataclass, field, replace
from functools import cache
from pathlib import Path

from sqlalchemy import Integer, TextClause, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

import aerona
from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.core.grammar import several, spoken
from aerona.db.base import Base
from aerona.db.book_marks import PAST_STAMP, ledger_folder, past_stamp
from aerona.db.profile_guard import table_name
from aerona.db.session import Database
from aerona.db.tables.ages import AgeRow
from aerona.db.tables.changes import StateChangeRow, StateChangeTermRow, StateCheckpointRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.records import IncidentFactRow, IncidentStepRow, IncidentStepStateRow, IncidentTermRow
from aerona.db.tables.tellings import IncidentNameRow
from aerona.services.books.records import (
    CHANGES_TITLE,
    HISTORY_TITLE,
    PHASE_PREFIX,
    REPORT_GROUPS,
    THEN_TITLE,
    Bindings,
    ChangeLine,
    LateLedger,
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
CHANGE_GRID = 125_000
HAPPENING_GRID = 2_000
CHANGES_KIND = "changes"
HAPPENINGS_KIND = "happenings"
ROWS_SUFFIX = ".rows"
META_SUFFIX = ".meta"
WRITING_SUFFIX = ".writing"
KEY_PART = "\x1f"
RANGE = '"{column}" > :after AND "{column}" <= :last'
STEPS_IN_RANGE = '"step_id" IN (SELECT "id" FROM "incident_steps" WHERE "incident_id" > :after AND "incident_id" <= :last)'
FieldKey = tuple[str, str, str]


@dataclass(frozen=True)
class Slice:
    url: str
    after: int
    last: int
    folder: str
    version: str


@dataclass(frozen=True)
class BindingsJob:
    url: str
    names: dict[int, str]


@dataclass
class ChangesTold:
    path: str
    nodes: dict[int | None, array[int]]
    first_seen: dict[int, dict[FieldKey, ChangeLine]]
    last_seen: dict[int, dict[FieldKey, ChangeLine]]
    incidents: dict[int, array[int]]
    row_of_table: dict[tuple[int, str], str]
    mixed: set[tuple[int, str]]


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
    bindings: Bindings


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


@cache
def code_version() -> str:
    root = Path(aerona.__file__).parent
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def database_identity(url: str) -> int:
    database = make_url(url).database
    try:
        return os.stat(database).st_ino if database else 0
    except FileNotFoundError:
        return 0


def key_of(*parts: object) -> str:
    return hashlib.sha256(KEY_PART.join(str(part) for part in parts).encode()).hexdigest()


def rows_text(name: str, where: str) -> TextClause:
    table = Base.metadata.tables[name]
    fields = "||char(31)||".join(f'quote("{column.name}")' for column in table.columns)
    order = ", ".join(f'"{column.name}"' for column in table.primary_key.columns)
    return text(f'SELECT group_concat({fields}, char(30) ORDER BY {order}) FROM "{table.name}" WHERE {where}')


HAPPENING_ROWS = (
    rows_text(IncidentRow.__tablename__, RANGE.format(column="id")),
    *(
        rows_text(row.__tablename__, RANGE.format(column="incident_id"))
        for row in (IncidentParticipantRow, IncidentFactRow, IncidentStepRow, IncidentTermRow, IncidentNameRow)
    ),
    rows_text(IncidentStepStateRow.__tablename__, STEPS_IN_RANGE),
)
CHANGE_EDGES = rows_text(StateChangeRow.__tablename__, '"id" IN (:first, :top)')


async def change_key(session: AsyncSession, job: Slice) -> str:
    count, first, top = (
        await session.execute(
            select(func.count(), func.min(StateChangeRow.id), func.max(StateChangeRow.id)).where(StateChangeRow.id > job.after, StateChangeRow.id <= job.last)
        )
    ).one()
    terms = await session.scalar(
        select(func.count()).select_from(StateChangeTermRow).where(StateChangeTermRow.change_id > job.after, StateChangeTermRow.change_id <= job.last)
    )
    edges = await session.scalar(CHANGE_EDGES, {"first": first, "top": top}) if count else ""
    return key_of(job.version, count, top, terms, edges)


async def happening_key(session: AsyncSession, job: Slice) -> str:
    digest = hashlib.sha256(job.version.encode())
    for statement in HAPPENING_ROWS:
        found = await session.scalar(statement, {"after": job.after, "last": job.last})
        digest.update(KEY_PART.join(("", found or "")).encode())
    return digest.hexdigest()


def kept_told[T: (ChangesTold, HappeningsTold)](folder: Path, stem: str, kind: type[T]) -> T | None:
    rows, meta = folder / f"{stem}{ROWS_SUFFIX}", folder / f"{stem}{META_SUFFIX}"
    if not rows.exists() or not meta.exists():
        return None
    try:
        told = pickle.loads(meta.read_bytes())
    except (OSError, pickle.UnpicklingError, EOFError, AttributeError, ImportError, TypeError, ValueError):
        return None
    if not isinstance(told, kind):
        return None
    told.path = str(rows)
    return told


def writing_path(folder: Path, stem: str) -> Path:
    found = folder / f"{stem}.{os.getpid()}{ROWS_SUFFIX}{WRITING_SUFFIX}"
    found.unlink(missing_ok=True)
    return found


def keep_told[T: (ChangesTold, HappeningsTold)](folder: Path, stem: str, told: T) -> T:
    rows = folder / f"{stem}{ROWS_SUFFIX}"
    os.replace(told.path, rows)
    told.path = str(rows)
    writing = folder / f"{stem}.{os.getpid()}{META_SUFFIX}{WRITING_SUFFIX}"
    writing.write_bytes(pickle.dumps(told))
    os.replace(writing, folder / f"{stem}{META_SUFFIX}")
    return told


async def tell_changes_in(session: AsyncSession, job: Slice) -> ChangesTold:
    folder = Path(job.folder)
    stem = f"{CHANGES_KIND}-{job.after}-{job.last}-{await change_key(session, job)}"
    kept = kept_told(folder, stem, ChangesTold)
    if kept is not None:
        return kept
    path = writing_path(folder, stem)
    ledger = LateLedger({}, store=RowStore(path))
    await ledger.load_changes(session, job.after, job.last)
    ledger.store.flush()
    told = ChangesTold(
        str(path),
        dict(ledger.changes),
        {node: dict(seen) for node, seen in ledger.first_seen.items()},
        {node: dict(seen) for node, seen in ledger.last_seen.items()},
        dict(ledger.incident_changes),
        dict(ledger.row_of_table),
        set(ledger.mixed),
    )
    return keep_told(folder, stem, told)


def happening_cells(ledger: Ledger, incident: IncidentRow) -> list[str]:
    return [
        ledger.when(incident),
        words(incident.kind),
        ledger.happening_line(incident),
        ledger.name_of(incident),
        ledger.name(incident.place_entity_id),
        ", ".join(f"{spoken(row.role)} {ledger.name_at(row.node_id, incident)}" for row in ledger.participants.get(incident.id, [])),
        "; ".join(ledger.fact_text(fact) for fact in ledger.facts.get(incident.id, [])),
        " ".join(ledger.step_text(step, incident) for step in ledger.steps.get(incident.id, [])),
        "",
        ledger.rumours_cell(incident.id),
        ledger.cause_cell(incident.cause_incident_id),
    ]


async def tell_happenings_in(session: AsyncSession, job: Slice) -> HappeningsTold:
    folder = Path(job.folder)
    stem = f"{HAPPENINGS_KIND}-{job.after}-{job.last}-{await happening_key(session, job)}"
    kept = kept_told(folder, stem, HappeningsTold)
    if kept is not None:
        return kept
    first = job.after + 1
    path = writing_path(folder, stem)
    ledger = LateLedger({}, store=RowStore(path))
    await ledger.load_incidents_between(session, first, job.last)
    await ledger.load_happening_records(session, first, job.last)
    accounts: dict[int, list[tuple[int, int, int]]] = defaultdict(list)
    rows: list[tuple[int, int, bool, list[str]]] = []
    reports: list[tuple[int, int, RecordTable]] = []
    for incident in ledger.incidents.values():
        for node_id in sorted({row.node_id for row in ledger.participants.get(incident.id, [])}):
            accounts[node_id].append((incident.epoch, incident.id, ledger.store.append(ledger.account_text(incident, node_id))))
        rows.append((incident.epoch, incident.id, incident.kind.startswith(PHASE_PREFIX), happening_cells(ledger, incident)))
        spec = INCIDENT_KINDS.get(incident.kind)
        report = REPORT_GROUPS.get(spec.group) if spec is not None else None
        if report is not None and ledger.steps.get(incident.id):
            reports.append((incident.epoch, incident.id, report_table(ledger, incident, report)))
    ledger.store.flush()
    return keep_told(folder, stem, HappeningsTold(str(path), dict(accounts), rows, reports))


def group_in(job: Grouping) -> Grouped:
    out = RowStore(Path(job.path))
    change_stores = [RowStore(Path(path)) for path in job.change_paths]
    account_stores = [RowStore(Path(path)) for path in job.account_paths]
    history: dict[int, array[int]] = {}
    changes: dict[int | None, array[int]] = {}
    seen: dict[str, str] = {}

    def bind(told: str) -> str:
        found = seen.get(told)
        if found is None:
            found = seen[told] = job.bindings.bind(told)
        return found

    for node in job.nodes:
        told = job.accounts.get(node) if node is not None else None
        if node is not None and told:
            history[node] = array("Q", (out.append(job.bindings.bind(account_stores[store].read(offset))) for _epoch, _id, store, offset in sorted(told)))
        spans = job.changes.get(node)
        if spans:
            lines = (ToldChange.unpacked(change_stores[store].read(offset)).bound(bind) for store, offsets in spans for offset in offsets)
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


def grid(last: int, size: int) -> list[tuple[int, int]]:
    return [(start, min(start + size, last)) for start in range(0, last, size)]


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
        ledger.mixed.update(pair for pair in part.mixed if pair[0] == node_id)
        for (node, table), row in part.row_of_table.items():
            if node != node_id:
                continue
            first_row = ledger.row_of_table.setdefault((node, table), row)
            if first_row != row:
                ledger.mixed.add((node, table))
    return [f"{label}: {text}" for label, text in ledger.then_and_now(node_id)]


@dataclass
class LedgerWork:
    folder: Path
    kept: Path
    bindings: Pending[Bindings, BindingsJob]
    changes: Pending[ChangesTold, Slice]
    happenings: Pending[HappeningsTold, Slice]


async def bindings_in(session: AsyncSession, job: BindingsJob) -> Bindings:
    return await bindings_of(session, job.names)


def tell_bindings(job: BindingsJob) -> Bindings:
    return on_database(job.url, lambda session: bindings_of(session, job.names))


async def start_ledger(session: AsyncSession, names: dict[int, str]) -> LedgerWork:
    folder = Path(tempfile.mkdtemp(prefix="aerona-ledger-"))
    url = session.sync_session.get_bind().engine.url.render_as_string(hide_password=False)
    kept = ledger_folder(url)
    kept.mkdir(parents=True, exist_ok=True)
    code = code_version()
    changes_version = key_of(code, database_identity(url), past_stamp(url))
    last_change = int(await session.scalar(select(func.coalesce(func.max(StateChangeRow.id), 0))) or 0)
    last_incident = int(await session.scalar(select(func.coalesce(func.max(IncidentRow.id), 0))) or 0)
    change_jobs = [Slice(url, after, last, str(kept), changes_version) for after, last in grid(last_change, CHANGE_GRID)]
    happening_jobs = [Slice(url, after, last, str(kept), code) for after, last in grid(last_incident, HAPPENING_GRID)]
    bindings = Pending([BindingsJob(url, names)], bindings_in, tell_bindings)
    return LedgerWork(folder, kept, bindings, Pending(change_jobs, tell_changes_in, tell_changes), Pending(happening_jobs, tell_happenings_in, tell_happenings))


async def bindings_of(session: AsyncSession, names: dict[int, str]) -> Bindings:
    ledger = Ledger(names)
    await ledger.load_incidents(session)
    await ledger.load_tellings(session, 0, max(ledger.incidents, default=0))
    await ledger.load_former_names(session)
    return Bindings(
        names,
        {incident_id: ledger.line_of(incident) for incident_id, incident in ledger.incidents.items()},
        frozenset(incident_id for incident_id, incident in ledger.incidents.items() if incident.kind.startswith(PHASE_PREFIX)),
        {node: list(former) for node, former in ledger.former.items()},
        {incident_id: ledger.rumours_told(incident_id) for incident_id in ledger.rumours},
    )


def bound_report(report: RecordTable, bindings: Bindings) -> RecordTable:
    return replace(report, title=bindings.bind(report.title), rows=[[bindings.bind(cell) for cell in row] for row in report.rows])


def changes_by_incident(told: list[ChangesTold], bindings: Bindings) -> tuple[dict[int, list[str]], dict[int, int]]:
    by_incident: dict[int, list[str]] = defaultdict(list)
    phase_counts: dict[int, int] = defaultdict(int)
    for part in told:
        store = RowStore(Path(part.path))
        for incident_id, offsets in part.incidents.items():
            if incident_id in bindings.phases:
                phase_counts[incident_id] += len(offsets)
            else:
                by_incident[incident_id].extend(ToldChange.unpacked(store.read(offset)).bound(bindings.bind).text() for offset in offsets)
    return dict(by_incident), dict(phase_counts)


def tidy(folder: Path, used: set[str]) -> None:
    for path in folder.iterdir():
        if path.name.startswith(PAST_STAMP) or (path.suffix in (ROWS_SUFFIX, META_SUFFIX) and path.stem in used):
            continue
        path.unlink(missing_ok=True)


async def add_history_sections(session: AsyncSession, index: TypedIndex, work: LedgerWork | None = None) -> LedgerBook:
    started = work or await start_ledger(session, index.names)
    folder = started.folder
    count = SLICES.count
    (bindings,) = await started.bindings.done(session)
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
            bindings,
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
    by_incident, phase_counts = changes_by_incident(told, bindings)
    loose = list(SpilledRows(*merged[None])) if None in merged else []
    tidy(started.kept, {Path(part.path).stem for part in told} | {Path(part.path).stem for part in happened})
    return LedgerBook(
        sorted(
            (
                (epoch, incident_id, phase, [bindings.bind(cell) for cell in cells])
                for happening in happened
                for epoch, incident_id, phase, cells in happening.rows
            ),
            key=lambda row: (row[0], row[1]),
        ),
        sorted(
            ((epoch, incident_id, bound_report(report, bindings)) for happening in happened for epoch, incident_id, report in happening.reports),
            key=lambda report: (report[0], report[1]),
        ),
        loose,
        by_incident,
        phase_counts,
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
