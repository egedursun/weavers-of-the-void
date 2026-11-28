import json
import mmap
import os
import re
import struct
import tempfile
import weakref
from array import array
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from functools import cache
from itertools import batched
from pathlib import Path
from typing import Any, overload

from sqlalchemy import Column, Table, select
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.core.grammar import an, fact_word, several, spoken
from aerona.core.total import total
from aerona.db.base import Base
from aerona.db.ledger_capture import PRESENT_EPOCH
from aerona.db.tables.ages import AgeRow
from aerona.db.tables.changes import StateChangeRow, StateChangeTermRow
from aerona.db.tables.culture import RumourRow
from aerona.db.tables.customs import NameFormRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.records import IncidentFactRow, IncidentStepRow, IncidentStepStateRow, IncidentTermRow
from aerona.db.tables.tellings import IncidentNameRow, RumourDistortionRow
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.modifier import IncidentRole, ModifierOp
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.records import FactUnit, InstrumentKind, ProcessGroup, StepLocus, WitnessMode
from aerona.engine.recording.record import KNOWERS
from aerona.services.books.typed import RecordTable, title_of, words

PHASE_PREFIX = "phase."
HISTORY_TITLE = "History"
CHANGES_TITLE = "Changes"
THEN_TITLE = "Then and now"
LEDGER_TITLES = frozenset({HISTORY_TITLE, CHANGES_TITLE})
UNLISTED_ROLES = KNOWERS | {IncidentRole.PLACE}
KNOWER_WORDS = {IncidentRole.WITNESS: ("witness", "witnesses"), IncidentRole.TELLER: ("teller", "tellers")}
REPORT_GROUPS = {ProcessGroup.BATTLES: "Battle report", ProcessGroup.VESSELS: "Engagement report"}
NO_UNIT = frozenset({FactUnit.NONE, FactUnit.COUNT})


def number_text(value: float | None) -> str:
    if value is None:
        return ""
    return str(int(value)) if float(value).is_integer() else f"{value:.2f}".rstrip("0").rstrip(".")


def signed(op: ModifierOp, amount: float) -> str:
    if op is ModifierOp.MULTIPLY:
        return f"times {number_text(amount)}"
    return f"{'+' if amount >= 0 else '-'}{number_text(abs(amount))}"


def moment_text(epoch: int, year: int | None, season: int | None, day: int | None, hour: int | None) -> str:
    parts = [f"epoch {epoch}"]
    if year is not None:
        parts.append(f"year {year}")
    if season is not None:
        parts.append(f"season {season + 1}")
    if day is not None:
        parts.append(f"day {day + 1}")
    if hour is not None:
        parts.append(f"hour {hour}")
    return ", ".join(parts)


WITNESS_WORDS = total(
    WitnessMode,
    {
        WitnessMode.SAW: "as witness",
        WitnessMode.HEARD: "heard of it",
        WitnessMode.TOOK_PART: "took part in it",
        WitnessMode.WAS_TOLD: "was told of it",
        WitnessMode.SENSED: "sensed it from afar",
    },
)


def part_taken(row: IncidentParticipantRow) -> str:
    if row.role is IncidentRole.WITNESS and row.witness_mode is not None:
        return WITNESS_WORDS[row.witness_mode]
    return f"as {spoken(row.role)}"


@cache
def enum_of(table: str, column_name: str | None) -> str | None:
    found = Base.metadata.tables.get(table)
    column = found.columns.get(column_name) if found is not None and column_name else None
    kind = getattr(column.type, "enum_class", None) if column is not None and isinstance(column.type, SqlEnum) else None
    return kind.__name__ if kind is not None else None


@dataclass(frozen=True, slots=True)
class ChangeLine:
    id: int
    epoch: int
    year: int | None
    season: int | None
    day: int | None
    hour: int | None
    table_name: str
    field: str | None
    node_id: int | None
    incident_id: int | None
    operation: LedgerOperation
    before_number: float | None
    before_text: str | None
    before_node_id: int | None
    after_number: float | None
    after_text: str | None
    after_node_id: int | None
    actor_kind: ActorKind
    actor_node_id: int | None
    phase: str | None
    row_key: str


@dataclass(frozen=True, slots=True)
class ToldChange:
    when: str
    head: str
    tail: str
    shift: tuple[str, str] | None = None
    rewrote: str = ""
    row: str = ""

    def text(self) -> str:
        return f"{self.when}: {self.head}{self.body()}{self.tail}"

    def body(self) -> str:
        if self.rewrote:
            return f": {self.rewrote}"
        if self.shift is not None:
            return f": {self.shift[0]} → {self.shift[1]}"
        return ""

    def packed(self) -> str:
        kind = REWROTE if self.rewrote else SHIFTED if self.shift is not None else MADE
        before, after = self.shift if self.shift is not None else ("", self.rewrote)
        return PACK.join(part.replace(PACK, " ") for part in (kind, self.when, self.head, self.tail, before, after, self.row))

    def bound(self, bind: Callable[[str], str]) -> "ToldChange":
        shift = (bind(self.shift[0]), bind(self.shift[1])) if self.shift is not None else None
        return ToldChange(self.when, bind(self.head), bind(self.tail), shift, self.rewrote)

    @classmethod
    def unpacked(cls, text: str) -> "ToldChange":
        kind, when, head, tail, before, after, row = text.split(PACK)
        if kind == SHIFTED:
            return cls(when, head, tail, (before, after), row=row)
        return cls(when, head, tail, rewrote=after if kind == REWROTE else "", row=row)


def row_parts(row_key: str, node_id: int | None) -> dict[str, object] | None:
    try:
        found = json.loads(row_key)
    except ValueError:
        return None
    if not isinstance(found, dict):
        return None
    return {key: value for key, value in found.items() if value != node_id}


def row_words(row_key: str, node_id: int | None) -> str:
    parts = row_parts(row_key, node_id)
    if not parts or set(parts) == {SURROGATE_KEY}:
        return ""
    return ", ".join(f"{words(key.removesuffix('_id')).lower()} {value}" for key, value in sorted(parts.items()))


def own_row(row_key: str, node_id: int | None) -> bool:
    return row_parts(row_key, node_id) == {}


def kind_phrase(kind: str) -> str:
    spec = INCIDENT_KINDS.get(kind)
    head = words(kind.rsplit(".", 1)[-1])
    return f"{head} ({spoken(spec.group)})" if spec is not None else head


def counted_moment(when: str, times: int) -> str:
    return when if times == 1 else f"{when} ({several(times, 'time', 'times')})"


def told_together(group: list[ToldChange]) -> str:
    first = group[0]
    if len(group) == 1:
        return first.text()
    runs: list[tuple[ToldChange, int]] = []
    for told in group:
        if runs and runs[-1][0] == told:
            runs[-1] = (told, runs[-1][1] + 1)
        else:
            runs.append((told, 1))
    if first.shift is None and not first.rewrote:
        return f"{first.head}{first.tail}: {'; '.join(counted_moment(told.when, times) for told, times in runs)}"
    pieces: list[str] = []
    previous: ToldChange | None = None
    for told, times in runs:
        moment = counted_moment(told.when, times)
        if told.shift is None:
            pieces.append(f"; {told.rewrote} ({moment})")
        elif previous is not None and previous.shift is not None and previous.shift[1] == told.shift[0]:
            pieces.append(f" → {told.shift[1]} ({moment})")
        else:
            pieces.append(f"; {told.shift[0]} → {told.shift[1]} ({moment})")
        previous = told
    return f"{first.head}{first.tail}: {''.join(pieces)[2:]}"


def grouped_changes(changes: Iterable[ToldChange]) -> list[str]:
    groups: dict[tuple[bool, str, str, str], list[ToldChange]] = {}
    for told in changes:
        groups.setdefault((told.shift is not None or bool(told.rewrote), told.head, told.tail, told.row), []).append(told)
    return [told_together(group) for group in groups.values()]


@dataclass(frozen=True, slots=True)
class TermLine:
    op: ModifierOp
    term: str
    amount: float
    source_node_id: int | None
    source_incident_id: int | None


class RowStore:
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            handle, name = tempfile.mkstemp(prefix="aerona-book-")
            os.unlink(name)
        else:
            handle = os.open(path, os.O_RDWR | os.O_CREAT, KEPT_MODE)
        self.handle = handle
        self.written = os.fstat(handle).st_size
        self.end = self.written
        self.buffer = bytearray()
        self.view: mmap.mmap | bytes = b""
        weakref.finalize(self, os.close, handle)

    def append(self, text: str) -> int:
        data = text.encode()
        offset = self.end
        self.buffer += LENGTH.pack(len(data))
        self.buffer += data
        self.end = offset + LENGTH.size + len(data)
        if len(self.buffer) >= STORE_BUFFER:
            self.flush()
        return offset

    def flush(self) -> None:
        if self.buffer:
            os.pwrite(self.handle, self.buffer, self.written)
            self.written += len(self.buffer)
            self.buffer = bytearray()

    def read(self, offset: int) -> str:
        start = offset + LENGTH.size
        if start > len(self.view):
            self.remap()
        (size,) = LENGTH.unpack_from(self.view, offset)
        if start + size > len(self.view):
            self.remap()
        return self.view[start : start + size].decode()

    def remap(self) -> None:
        self.flush()
        self.view = mmap.mmap(self.handle, self.written, access=mmap.ACCESS_READ) if self.written else b""


class SpilledRows(Sequence[str]):
    def __init__(self, store: RowStore, offsets: array[int]) -> None:
        self.store = store
        self.offsets = offsets

    def __len__(self) -> int:
        return len(self.offsets)

    @overload
    def __getitem__(self, index: int) -> str: ...

    @overload
    def __getitem__(self, index: slice) -> list[str]: ...

    def __getitem__(self, index: int | slice) -> str | list[str]:
        if isinstance(index, slice):
            return [self.store.read(offset) for offset in self.offsets[index]]
        return self.store.read(self.offsets[index])

    def __iter__(self) -> Iterator[str]:
        for offset in self.offsets:
            yield self.store.read(offset)


CHANGE_COLUMNS = tuple(StateChangeRow.__table__.c[name] for name in ChangeLine.__dataclass_fields__)
CHANGE_CHUNK = 50_000
NAME_FIELD = "name"
NAMED_TABLES = frozenset({"nodes", "entities"})
SURROGATE_KEY = "id"
LOOKUP_BATCH = 500
LENGTH = struct.Struct("<I")
KEPT_MODE = 0o644
STORE_BUFFER = 4_194_304
PACK = "\x1f"
MADE = "m"
SHIFTED = "s"
REWROTE = "r"
UNNAMED = "an unnamed record"
MARK = "\ue000"
MARK_END = "\ue001"
TOKEN = re.compile(r"\ue000([a-z])(\d+)(?::(\d+))?\ue001")
NAME_TOKEN = "n"
NAME_AT_TOKEN = "m"
LINE_TOKEN = "l"
SOURCE_TOKEN = "e"
DURING_TOKEN = "d"
CAUSE_PART_TOKEN = "c"
CAUSE_CELL_TOKEN = "k"
RUMOURS_PART_TOKEN = "r"
RUMOURS_CELL_TOKEN = "s"
RECORD_TOKEN = "g"
NODE_KEY_SUFFIXES = ("_entity_id", "_node_id", "_id")


def node_table(table: Table) -> bool:
    return table.name == NodeRow.__tablename__ or any(
        foreign.column.table.name == NodeRow.__tablename__ for column in table.primary_key.columns for foreign in column.foreign_keys
    )


def keyed_tables() -> tuple[str, ...]:
    found = {
        foreign.column.table.name
        for table in Base.metadata.tables.values()
        if len(table.primary_key.columns) > 1
        for column in table.primary_key.columns
        for foreign in column.foreign_keys
        if not node_table(foreign.column.table)
    }
    return tuple(sorted(found))


RECORD_TABLES = keyed_tables()


def token(kind: str, first: int, second: int | None = None) -> str:
    return f"{MARK}{kind}{first}{'' if second is None else f':{second}'}{MARK_END}"


def name_within(current: str, former: Sequence[str], text: str) -> str:
    if current in text:
        return current
    then = next((name for name in sorted(former, key=len, reverse=True) if name in text), None)
    return f"{current} (then {then})" if then is not None else current


def during_text(line: str | None, phase: bool) -> str:
    return f" (during: {line})" if line is not None and not phase else ""


def source_text(line: str | None) -> str:
    return f" ({line})" if line is not None else ""


def cause_part_text(line: str | None) -> str:
    return f" · cause: {line}" if line is not None else ""


def rumours_part_text(told: Sequence[str]) -> str:
    return f" · rumours: {'; '.join(told)}" if told else ""


@dataclass(frozen=True)
class Bindings:
    names: dict[int, str]
    lines: dict[int, str]
    phases: frozenset[int]
    former: dict[int, list[str]]
    rumours: dict[int, list[str]]
    records: dict[tuple[int, int], str] = field(default_factory=dict)

    def name(self, node_id: int) -> str:
        return self.names.get(node_id) or UNNAMED

    def record(self, table: int, row_id: int) -> str:
        return self.records.get((table, row_id)) or f"{an(words(RECORD_TABLES[table]).lower().removesuffix('s'))} no longer kept"

    def bind(self, text: str) -> str:
        return TOKEN.sub(self.resolve, text) if MARK in text else text

    def resolve(self, found: re.Match[str]) -> str:
        first, second = int(found.group(2)), found.group(3)
        if second is not None and found.group(1) == RECORD_TOKEN:
            return self.record(first, int(second))
        if second is not None:
            return self.name_at(first, int(second))
        return RESOLVERS[found.group(1)](self, first)

    def name_at(self, node_id: int, incident_id: int) -> str:
        within = self.lines.get(incident_id)
        return name_within(self.name(node_id), self.former.get(node_id, []), within) if within is not None else self.name(node_id)

    def line(self, incident_id: int) -> str:
        return self.lines.get(incident_id) or ""

    def source(self, incident_id: int) -> str:
        return source_text(self.lines.get(incident_id))

    def during(self, incident_id: int) -> str:
        return during_text(self.lines.get(incident_id), incident_id in self.phases)

    def cause_part(self, incident_id: int) -> str:
        return cause_part_text(self.lines.get(incident_id))

    def rumours_part(self, incident_id: int) -> str:
        return rumours_part_text(self.rumours.get(incident_id, []))

    def rumours_cell(self, incident_id: int) -> str:
        return "; ".join(self.rumours.get(incident_id, []))


RESOLVERS: dict[str, Callable[[Bindings, int], str]] = {
    NAME_TOKEN: Bindings.name,
    LINE_TOKEN: Bindings.line,
    SOURCE_TOKEN: Bindings.source,
    DURING_TOKEN: Bindings.during,
    CAUSE_PART_TOKEN: Bindings.cause_part,
    CAUSE_CELL_TOKEN: Bindings.line,
    RUMOURS_PART_TOKEN: Bindings.rumours_part,
    RUMOURS_CELL_TOKEN: Bindings.rumours_cell,
}


@dataclass
class Ledger:
    names: dict[int, str]
    incidents: dict[int, IncidentRow] = field(default_factory=dict)
    lines: dict[int, str] = field(default_factory=dict)
    heads: dict[int, str] = field(default_factory=dict)
    tails: dict[int, list[str]] = field(default_factory=dict)
    participants: dict[int, list[IncidentParticipantRow]] = field(default_factory=lambda: defaultdict(list))
    facts: dict[int, list[IncidentFactRow]] = field(default_factory=lambda: defaultdict(list))
    steps: dict[int, list[IncidentStepRow]] = field(default_factory=lambda: defaultdict(list))
    states: dict[int, list[IncidentStepStateRow]] = field(default_factory=lambda: defaultdict(list))
    terms: dict[int, list[IncidentTermRow]] = field(default_factory=lambda: defaultdict(list))
    store: RowStore = field(default_factory=RowStore)
    first_seen: dict[int, dict[tuple[str, str, str], ChangeLine]] = field(default_factory=lambda: defaultdict(dict))
    last_seen: dict[int, dict[tuple[str, str, str], ChangeLine]] = field(default_factory=lambda: defaultdict(dict))
    row_of_table: dict[tuple[int, str], str] = field(default_factory=dict)
    mixed: set[tuple[int, str]] = field(default_factory=set)
    named: dict[int, IncidentNameRow] = field(default_factory=dict)
    rumours: dict[int, list[RumourRow]] = field(default_factory=lambda: defaultdict(list))
    distortions: dict[int, list[RumourDistortionRow]] = field(default_factory=lambda: defaultdict(list))
    former: dict[int, list[str]] = field(default_factory=lambda: defaultdict(list))

    async def load_incidents(self, session: AsyncSession) -> None:
        for row in await session.scalars(select(IncidentRow).order_by(IncidentRow.epoch, IncidentRow.id)):
            self.incidents[row.id] = row
        for chronicle_id, text in await session.execute(select(ChronicleRow.id, ChronicleRow.text).order_by(ChronicleRow.id)):
            self.lines[chronicle_id] = text

    async def load_incidents_between(self, session: AsyncSession, first: int, last: int) -> None:
        for row in await session.scalars(
            select(IncidentRow).where(IncidentRow.id >= first, IncidentRow.id <= last).order_by(IncidentRow.epoch, IncidentRow.id)
        ):
            self.incidents[row.id] = row

    async def load_happening_records(self, session: AsyncSession, first: int, last: int) -> None:
        span = (IncidentParticipantRow.incident_id >= first, IncidentParticipantRow.incident_id <= last)
        for participant in await session.scalars(
            select(IncidentParticipantRow).where(*span).order_by(IncidentParticipantRow.incident_id, IncidentParticipantRow.position)
        ):
            self.participants[participant.incident_id].append(participant)
        facts = select(IncidentFactRow).where(IncidentFactRow.incident_id >= first, IncidentFactRow.incident_id <= last)
        for fact in await session.scalars(facts.order_by(IncidentFactRow.incident_id, IncidentFactRow.key, IncidentFactRow.position)):
            self.facts[fact.incident_id].append(fact)
        steps = select(IncidentStepRow).where(IncidentStepRow.incident_id >= first, IncidentStepRow.incident_id <= last)
        for step in await session.scalars(steps.order_by(IncidentStepRow.incident_id, IncidentStepRow.position, IncidentStepRow.id)):
            self.steps[step.incident_id].append(step)
        stepped = select(IncidentStepRow.id).where(IncidentStepRow.incident_id >= first, IncidentStepRow.incident_id <= last)
        states = select(IncidentStepStateRow).where(IncidentStepStateRow.step_id.in_(stepped))
        for state in await session.scalars(states.order_by(IncidentStepStateRow.step_id, IncidentStepStateRow.node_id)):
            self.states[state.step_id].append(state)
        terms = select(IncidentTermRow).where(IncidentTermRow.incident_id >= first, IncidentTermRow.incident_id <= last)
        for term in await session.scalars(terms.order_by(IncidentTermRow.incident_id, IncidentTermRow.position)):
            self.terms[term.incident_id].append(term)
        await self.load_tellings(session, first, last)

    async def load_former_names(self, session: AsyncSession) -> None:
        for holder, name in await session.execute(select(NameFormRow.holder_node_id, NameFormRow.name).order_by(NameFormRow.holder_node_id, NameFormRow.form)):
            self.remember_name(holder, name)
        renamed = (
            select(StateChangeRow.node_id, StateChangeRow.before_text)
            .where(StateChangeRow.field == NAME_FIELD, StateChangeRow.table_name.in_(NAMED_TABLES), StateChangeRow.node_id.is_not(None))
            .order_by(StateChangeRow.id)
        )
        for node_id, before in await session.execute(renamed):
            if node_id is not None:
                self.remember_name(node_id, before)

    def remember_name(self, node_id: int, name: str | None) -> None:
        if name and name != self.names.get(node_id) and name not in self.former[node_id]:
            self.former[node_id].append(name)

    def name_in(self, node_id: int | None, text: str) -> str:
        return name_within(self.name(node_id), self.former.get(node_id, []), text) if node_id is not None else ""

    def name_at(self, node_id: int | None, incident: IncidentRow) -> str:
        return self.name_in(node_id, self.line_of(incident))

    def happening_line(self, incident: IncidentRow) -> str:
        return self.line_of(incident)

    def known_line(self, incident_id: int | None) -> str | None:
        happening = self.incidents.get(incident_id) if incident_id is not None else None
        return self.line_of(happening) if happening is not None else None

    def source_part(self, incident_id: int | None) -> str:
        return source_text(self.known_line(incident_id))

    def during_part(self, incident_id: int | None) -> str:
        happening = self.incidents.get(incident_id) if incident_id is not None else None
        return during_text(self.line_of(happening), happening.kind.startswith(PHASE_PREFIX)) if happening is not None else ""

    def rumours_told(self, incident_id: int) -> list[str]:
        return [self.rumour_text(rumour) for rumour in self.rumours.get(incident_id, [])]

    def rumours_part(self, incident_id: int) -> str:
        return rumours_part_text(self.rumours_told(incident_id))

    def rumours_cell(self, incident_id: int) -> str:
        return "; ".join(self.rumours_told(incident_id))

    def cause_part(self, incident_id: int | None) -> str:
        return cause_part_text(self.known_line(incident_id))

    def cause_cell(self, incident_id: int | None) -> str:
        return self.known_line(incident_id) or ""

    async def load_tellings(self, session: AsyncSession, first: int, last: int) -> None:
        named = select(IncidentNameRow).where(IncidentNameRow.incident_id >= first, IncidentNameRow.incident_id <= last)
        for name in await session.scalars(named.order_by(IncidentNameRow.incident_id)):
            self.named[name.incident_id] = name
        rumours = select(RumourRow).where(RumourRow.incident_id >= first, RumourRow.incident_id <= last)
        for rumour in await session.scalars(rumours.order_by(RumourRow.incident_id, RumourRow.epoch, RumourRow.id)):
            self.rumours[rumour.incident_id].append(rumour)
        told = select(RumourRow.id).where(RumourRow.incident_id >= first, RumourRow.incident_id <= last)
        distortions = select(RumourDistortionRow).where(RumourDistortionRow.rumour_id.in_(told))
        for distortion in await session.scalars(distortions.order_by(RumourDistortionRow.rumour_id, RumourDistortionRow.position)):
            self.distortions[distortion.rumour_id].append(distortion)

    def name(self, node_id: int | None) -> str:
        if node_id is None:
            return ""
        return self.names.get(node_id) or UNNAMED

    def row_text(self, table: str, row_key: str, node_id: int | None) -> str:
        parts = row_parts(row_key, node_id)
        if not parts or set(parts) == {SURROGATE_KEY}:
            return ""
        columns = Base.metadata.tables[table].columns if table in Base.metadata.tables else None
        return ", ".join(self.part_text(columns[key] if columns is not None and key in columns else None, key, value) for key, value in sorted(parts.items()))

    def part_text(self, column: Column[Any] | None, key: str, value: object) -> str:
        targets = [foreign.column.table for foreign in column.foreign_keys] if column is not None else []
        label = words(next((key.removesuffix(suffix) for suffix in NODE_KEY_SUFFIXES if key.endswith(suffix)), key)).lower()
        if isinstance(value, int) and not isinstance(value, bool):
            if any(node_table(target) for target in targets):
                return f"{label} {self.name(value)}"
            found = next((RECORD_TABLES.index(target.name) for target in targets if target.name in RECORD_TABLES), None)
            if found is not None:
                return token(RECORD_TOKEN, found, value)
        if isinstance(value, str):
            return f"{label} {spoken(value)}"
        return f"{label} {value}"

    def name_of(self, incident: IncidentRow) -> str:
        named = self.named.get(incident.id)
        if named is None:
            return ""
        language = f" (in {self.name(named.language_entity_id)})" if named.language_entity_id is not None else ""
        return f"{named.name}{language}"

    def distortion_text(self, row: RumourDistortionRow) -> str:
        target = spoken(row.role) if row.role is not None else words(row.fact_key).lower() if row.fact_key else f"step {row.step_id}" if row.step_id else ""
        told: list[str] = []
        if row.told_node_id is not None:
            told.append(self.name(row.told_node_id))
        if row.told_number is not None:
            told.append(number_text(row.told_number))
        if row.told_enum_value is not None:
            told.append(spoken(row.told_enum_value))
        if row.told_year is not None:
            told.append(f"year {row.told_year}")
        if row.told_incident_id is not None and row.told_incident_id in self.incidents:
            told.append(self.line_of(self.incidents[row.told_incident_id]))
        if row.told_action is not None:
            told.append(spoken(row.told_action))
        if row.told_outcome is not None:
            told.append(spoken(row.told_outcome))
        shown = f" told as {', '.join(told)}" if told else ""
        return f"{spoken(row.distortion)}{f' ({target})' if target else ''}{shown}"

    def rumour_text(self, rumour: RumourRow) -> str:
        source = f" from {self.name(rumour.source_entity_id)}" if rumour.source_entity_id is not None else ""
        distortions = [self.distortion_text(row) for row in self.distortions.get(rumour.id, [])]
        changed = f", changed: {'; '.join(distortions)}" if distortions else ", told true"
        hops = several(rumour.hops, "hop", "hops")
        return f"{self.name(rumour.carrier_entity_id)} heard it{source} in epoch {rumour.epoch} after {hops}, fidelity {rumour.fidelity}%{changed}"

    def line_of(self, incident: IncidentRow) -> str:
        found = self.lines.get(incident.chronicle_id) if incident.chronicle_id is not None else None
        return found or incident.note or kind_phrase(incident.kind)

    def when(self, incident: IncidentRow) -> str:
        return moment_text(incident.epoch, incident.year, incident.season, incident.day, incident.hour)

    def fact_text(self, fact: IncidentFactRow) -> str:
        if fact.node_id is not None:
            value = self.name(fact.node_id)
        elif fact.number is not None:
            unit = "" if fact.unit is None or fact.unit in NO_UNIT else f" {spoken(fact.unit)}"
            value = f"{number_text(fact.number)}{unit}"
        elif fact.enum_value is not None:
            value = fact_word(fact.enum_name, fact.enum_value)
        else:
            value = fact.name or ""
        return f"{words(fact.key).lower()} {value}".strip()

    def term_text(self, op: ModifierOp, term: str, amount: float, source_node_id: int | None, source_incident_id: int | None) -> str:
        if term == PRESENT_EPOCH:
            return f"the age is now epoch {number_text(amount)}"
        source = self.name(source_node_id) if source_node_id is not None else ""
        origin = f" from {source}" if source else ""
        return f"{words(term).lower()} {signed(op, amount)}{origin}{self.source_part(source_incident_id)}"

    def step_text(self, step: IncidentStepRow, incident: IncidentRow) -> str:
        parts = [f"{step.position + 1}."]
        if step.round is not None:
            parts.append(f"round {step.round + 1}:")
        if step.actor_node_id is not None:
            parts.append(self.name_at(step.actor_node_id, incident))
        parts.append(spoken(step.action))
        if step.target_node_id is not None:
            parts.append(self.name_at(step.target_node_id, incident))
        if step.instrument_kind is not InstrumentKind.NONE or step.instrument_node_id is not None or step.instrument_key:
            instrument = self.name(step.instrument_node_id) if step.instrument_node_id is not None else spoken(step.instrument_key or step.instrument_kind)
            parts.append(f"with {instrument}")
        if step.locus_kind is not StepLocus.NONE:
            locus = self.name(step.locus_node_id) if step.locus_node_id is not None else spoken(step.locus_key or step.locus_kind)
            parts.append(f"at the {locus}" if step.locus_node_id is None else f"at {locus}")
        if step.damage_type is not None:
            parts.append(f"({spoken(step.damage_type)})")
        if step.amount is not None:
            unit = "" if step.unit is None or step.unit in NO_UNIT else f" {spoken(step.unit)}"
            parts.append(f"for {number_text(step.amount)}{unit}")
        if step.outcome is not None:
            parts.append(f"→ {spoken(step.outcome)}")
        states = [f"{self.name(state.node_id)} {spoken(state.state)}" for state in self.states.get(step.id, [])]
        if states:
            parts.append(f"[{', '.join(states)}]")
        return " ".join(parts)

    def value_text(self, change: ChangeLine, before: bool) -> str:
        node = change.before_node_id if before else change.after_node_id
        if node is not None:
            return self.name(node)
        number = change.before_number if before else change.after_number
        if number is not None:
            return number_text(number)
        text = change.before_text if before else change.after_text
        if text is None:
            return "none"
        kind = enum_of(change.table_name, change.field)
        return fact_word(kind, text) if kind is not None else text

    def told_change(self, change: ChangeLine, terms: list[TermLine]) -> ToldChange:
        record = title_of(change.table_name).lower()
        owner = f" of {self.name(change.node_id)}" if change.node_id is not None else ""
        when = moment_text(change.epoch, change.year, change.season, change.day, change.hour)
        tail = self.change_tail(change, terms)
        if change.operation is not LedgerOperation.UPDATE:
            return ToldChange(when, f"{'created' if change.operation is LedgerOperation.INSERT else 'removed'} {an(record)} record{owner}", tail)
        told_row = self.row_text(change.table_name, change.row_key, change.node_id)
        head = f"{words(change.field or '').lower()} of {record}{f' ({told_row})' if told_row else ''}{owner}"
        row = "" if told_row or own_row(change.row_key, change.node_id) else change.row_key
        rewritten = rewritten_parts(change.before_text, change.after_text)
        if rewritten is not None:
            return ToldChange(when, head, tail, rewrote=f"rewrote {rewritten}", row=row)
        return ToldChange(when, head, tail, (self.value_text(change, True), self.value_text(change, False)), row=row)

    def change_text(self, change: ChangeLine, terms: list[TermLine]) -> str:
        return self.told_change(change, terms).text()

    def change_tail(self, change: ChangeLine, terms: list[TermLine]) -> str:
        actor = f" by {self.name(change.actor_node_id)}" if change.actor_node_id is not None else f" by the {spoken(change.actor_kind)}"
        phase = f" in {spoken(change.phase)}" if change.phase else ""
        reasons = [self.term_text(term.op, term.term, term.amount, term.source_node_id, term.source_incident_id) for term in terms]
        why = f" because {'; '.join(reasons)}" if reasons else ""
        return f"{actor}{phase}{why}{self.during_part(change.incident_id)}"

    def account_text(self, incident: IncidentRow, node_id: int | None) -> str:
        roles = self.participants.get(incident.id, [])
        mine = [row for row in roles if row.node_id == node_id]
        own = [row.role for row in mine]
        parts = [self.account_head(incident)]
        if own:
            parts.append(", ".join(part_taken(row) for row in mine))
        parts.extend(self.account_place(incident))
        if own and all(role in KNOWERS for role in own):
            return " · ".join(parts)
        others = [f"{spoken(row.role)} {self.name_at(row.node_id, incident)}" for row in roles if row.node_id != node_id and row.role not in UNLISTED_ROLES]
        knowing = Counter(row.role for row in roles if row.node_id != node_id and row.role in KNOWERS)
        others.extend(several(knowing[role], *words) for role, words in sorted(KNOWER_WORDS.items()) if knowing[role])
        if others:
            parts.append("with " + ", ".join(others))
        parts.extend(self.account_tail(incident))
        return " · ".join(parts) + self.rumours_part(incident.id) + self.cause_part(incident.cause_incident_id)

    def account_head(self, incident: IncidentRow) -> str:
        found = self.heads.get(incident.id)
        if found is None:
            found = f"{self.when(incident)}: {self.happening_line(incident)}"
            if incident.id in self.named:
                found = f"{found} · named {self.name_of(incident)}"
            self.heads[incident.id] = found
        return found

    def account_place(self, incident: IncidentRow) -> list[str]:
        parts = []
        if incident.place_entity_id is not None:
            parts.append(f"at {self.name(incident.place_entity_id)}")
        if incident.origin_entity_id is not None or incident.destination_entity_id is not None:
            parts.append(f"from {self.name(incident.origin_entity_id) or 'somewhere'} to {self.name(incident.destination_entity_id) or 'somewhere'}")
        return parts

    def account_tail(self, incident: IncidentRow) -> list[str]:
        found = self.tails.get(incident.id)
        if found is not None:
            return found
        parts = []
        facts = [self.fact_text(fact) for fact in self.facts.get(incident.id, [])]
        if facts:
            parts.append("account: " + "; ".join(facts))
        terms = [self.term_text(term.op, term.term, term.amount, term.source_node_id, term.source_incident_id) for term in self.terms.get(incident.id, [])]
        if terms:
            parts.append("terms: " + "; ".join(terms))
        steps = [self.step_text(step, incident) for step in self.steps.get(incident.id, [])]
        if steps:
            parts.append("steps: " + " ".join(steps))
        self.tails[incident.id] = parts
        return parts

    def note_seen(self, change: ChangeLine) -> None:
        if change.node_id is None or change.field is None:
            return
        told_row = row_words(change.row_key, change.node_id)
        if not told_row and not own_row(change.row_key, change.node_id):
            first_row = self.row_of_table.setdefault((change.node_id, change.table_name), change.row_key)
            if first_row != change.row_key:
                self.mixed.add((change.node_id, change.table_name))
        key = (change.table_name, change.field, told_row)
        self.first_seen[change.node_id].setdefault(key, change)
        self.last_seen[change.node_id][key] = change

    def then_and_now(self, node_id: int) -> list[tuple[str, str]]:
        first = self.first_seen.get(node_id, {})
        last = self.last_seen.get(node_id, {})
        found: list[tuple[str, str]] = []
        for key, earliest in first.items():
            if (node_id, key[0]) in self.mixed:
                continue
            latest = last[key]
            then, now = self.value_text(earliest, True), self.value_text(latest, False)
            if then != now:
                told_row = self.row_text(key[0], earliest.row_key, node_id) if key[2] else ""
                label = f"{words(key[1])} ({title_of(key[0]).lower()}{f', {told_row}' if told_row else ''})"
                rewritten = rewritten_parts(earliest.before_text, latest.after_text)
                found.append(
                    (label, f"since epoch {earliest.epoch}: rewrote {rewritten}" if rewritten is not None else f"epoch {earliest.epoch}: {then} → now: {now}")
                )
        return found


@dataclass
class LateLedger(Ledger):
    changes: dict[int | None, array[int]] = field(default_factory=lambda: defaultdict(lambda: array("Q")))
    incident_changes: dict[int, array[int]] = field(default_factory=lambda: defaultdict(lambda: array("Q")))

    async def load_changes(self, session: AsyncSession, after: int, last: int) -> None:
        for start in range(after, last, CHANGE_CHUNK):
            end = min(start + CHANGE_CHUNK, last)
            terms: dict[int, list[TermLine]] = defaultdict(list)
            term_rows = await session.execute(
                select(
                    StateChangeTermRow.change_id,
                    StateChangeTermRow.op,
                    StateChangeTermRow.term,
                    StateChangeTermRow.amount,
                    StateChangeTermRow.source_node_id,
                    StateChangeTermRow.source_incident_id,
                )
                .where(StateChangeTermRow.change_id > start, StateChangeTermRow.change_id <= end)
                .order_by(StateChangeTermRow.change_id, StateChangeTermRow.position)
            )
            for change_id, op, term, amount, source_node_id, source_incident_id in term_rows:
                terms[change_id].append(TermLine(op, term, amount, source_node_id, source_incident_id))
            rows = await session.execute(select(*CHANGE_COLUMNS).where(StateChangeRow.id > start, StateChangeRow.id <= end).order_by(StateChangeRow.id))
            for row in rows:
                self.take_change(ChangeLine(*row), terms.get(row[0], []))

    def name(self, node_id: int | None) -> str:
        return token(NAME_TOKEN, node_id) if node_id is not None else ""

    def name_at(self, node_id: int | None, incident: IncidentRow) -> str:
        return token(NAME_AT_TOKEN, node_id, incident.id) if node_id is not None else ""

    def happening_line(self, incident: IncidentRow) -> str:
        return token(LINE_TOKEN, incident.id)

    def source_part(self, incident_id: int | None) -> str:
        return token(SOURCE_TOKEN, incident_id) if incident_id is not None else ""

    def during_part(self, incident_id: int | None) -> str:
        return token(DURING_TOKEN, incident_id) if incident_id is not None else ""

    def rumours_part(self, incident_id: int) -> str:
        return token(RUMOURS_PART_TOKEN, incident_id)

    def rumours_cell(self, incident_id: int) -> str:
        return token(RUMOURS_CELL_TOKEN, incident_id)

    def cause_part(self, incident_id: int | None) -> str:
        return token(CAUSE_PART_TOKEN, incident_id) if incident_id is not None else ""

    def cause_cell(self, incident_id: int | None) -> str:
        return token(CAUSE_CELL_TOKEN, incident_id) if incident_id is not None else ""

    def take_change(self, change: ChangeLine, terms: list[TermLine]) -> None:
        offset = self.store.append(self.told_change(change, terms).packed())
        self.changes[change.node_id].append(offset)
        if change.incident_id is not None:
            self.incident_changes[change.incident_id].append(offset)
        if change.node_id is not None and change.operation is LedgerOperation.UPDATE and change.field is not None:
            self.note_seen(change)


def composite(text: str | None) -> dict[str, object] | list[object] | None:
    if text is None or not text.startswith(("{", "[")):
        return None
    try:
        found = json.loads(text)
    except ValueError:
        return None
    return found if isinstance(found, (dict, list)) else None


def rewritten_parts(before: str | None, after: str | None) -> str | None:
    old, new = composite(before), composite(after)
    if old is None and new is None:
        return None
    if isinstance(old, dict) or isinstance(new, dict):
        first = old if isinstance(old, dict) else {}
        second = new if isinstance(new, dict) else {}
        keys = sorted(key for key in {*first, *second} if first.get(key) != second.get(key))
        return ", ".join(words(key).lower() for key in keys) or "nothing"
    return "its list"


async def node_change_lines(session: AsyncSession, names: dict[int, str], node_id: int) -> list[str]:
    ledger = Ledger(names)
    rows = [ChangeLine(*row) for row in await session.execute(select(*CHANGE_COLUMNS).where(StateChangeRow.node_id == node_id).order_by(StateChangeRow.id))]
    terms: dict[int, list[TermLine]] = defaultdict(list)
    for batch in batched([row.id for row in rows], LOOKUP_BATCH, strict=False):
        term_rows = await session.execute(
            select(
                StateChangeTermRow.change_id,
                StateChangeTermRow.op,
                StateChangeTermRow.term,
                StateChangeTermRow.amount,
                StateChangeTermRow.source_node_id,
                StateChangeTermRow.source_incident_id,
            )
            .where(StateChangeTermRow.change_id.in_(batch))
            .order_by(StateChangeTermRow.change_id, StateChangeTermRow.position)
        )
        for change_id, op, term, amount, source_node_id, source_incident_id in term_rows:
            terms[change_id].append(TermLine(op, term, amount, source_node_id, source_incident_id))
    named = {row.incident_id for row in rows if row.incident_id is not None}
    named.update(term.source_incident_id for found in terms.values() for term in found if term.source_incident_id is not None)
    for batch in batched(sorted(named), LOOKUP_BATCH, strict=False):
        for incident in await session.scalars(select(IncidentRow).where(IncidentRow.id.in_(batch)).order_by(IncidentRow.id)):
            ledger.incidents[incident.id] = incident
    told = sorted({incident.chronicle_id for incident in ledger.incidents.values() if incident.chronicle_id is not None})
    for batch in batched(told, LOOKUP_BATCH, strict=False):
        for chronicle_id, text in await session.execute(select(ChronicleRow.id, ChronicleRow.text).where(ChronicleRow.id.in_(batch)).order_by(ChronicleRow.id)):
            ledger.lines[chronicle_id] = text
    return [ledger.change_text(row, terms.get(row.id, [])) for row in rows]


def age_spans(ages: Iterable[AgeRow]) -> list[tuple[str, int, int | None]]:
    found = [(f"Happenings of age {row.number}", row.began_epoch, row.ended_epoch) for row in sorted(ages, key=lambda row: (row.began_epoch, row.number))]
    return found or [("Happenings", 0, None)]


def report_table(ledger: Ledger, incident: IncidentRow, title: str) -> RecordTable:
    table = RecordTable(
        f"{title}: {ledger.happening_line(incident)}",
        ["Step", "Round", "Moment", "Actor", "Action", "Target", "Instrument", "Section or part", "Amount", "Outcome", "States"],
    )
    for step in ledger.steps.get(incident.id, []):
        instrument = ledger.name(step.instrument_node_id) if step.instrument_node_id is not None else spoken(step.instrument_key or step.instrument_kind)
        locus = ledger.name(step.locus_node_id) if step.locus_node_id is not None else spoken(step.locus_key or step.locus_kind)
        unit = "" if step.unit is None or step.unit in NO_UNIT else f" {spoken(step.unit)}"
        table.rows.append(
            [
                str(step.position + 1),
                str(step.round + 1) if step.round is not None else "",
                moment_text(incident.epoch, step.year, step.season, step.day, step.hour),
                ledger.name(step.actor_node_id),
                spoken(step.action),
                ledger.name(step.target_node_id),
                instrument if step.instrument_kind is not InstrumentKind.NONE or step.instrument_node_id is not None else "",
                locus if step.locus_kind is not StepLocus.NONE else "",
                f"{number_text(step.amount)}{unit}" if step.amount is not None else "",
                spoken(step.outcome) if step.outcome is not None else "",
                ", ".join(f"{ledger.name(state.node_id)} {spoken(state.state)}" for state in ledger.states.get(step.id, [])),
            ]
        )
    return table
