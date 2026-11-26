import json
import os
import struct
import tempfile
import weakref
from array import array
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from itertools import batched
from typing import overload

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.core.grammar import an, fact_word, several, spoken
from aerona.db.tables.ages import AgeRow
from aerona.db.tables.changes import StateChangeRow, StateChangeTermRow, StateCheckpointRow
from aerona.db.tables.culture import RumourRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.records import IncidentFactRow, IncidentStepRow, IncidentStepStateRow, IncidentTermRow
from aerona.db.tables.tellings import IncidentNameRow, RumourDistortionRow
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.modifier import IncidentRole, ModifierOp
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.records import FactUnit, InstrumentKind, ProcessGroup, StepLocus
from aerona.engine.recording.record import KNOWERS
from aerona.services.books.typed import RecordTable, TypedIndex, TypedSection, title_of, words

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


@dataclass(frozen=True, slots=True)
class TermLine:
    op: ModifierOp
    term: str
    amount: float
    source_node_id: int | None
    source_incident_id: int | None


class RowStore:
    def __init__(self) -> None:
        handle, path = tempfile.mkstemp(prefix="aerona-book-")
        os.unlink(path)
        self.handle = handle
        self.end = 0
        weakref.finalize(self, os.close, handle)

    def append(self, text: str) -> int:
        data = text.encode()
        offset = self.end
        os.pwrite(self.handle, LENGTH.pack(len(data)) + data, offset)
        self.end = offset + LENGTH.size + len(data)
        return offset

    def read(self, offset: int) -> str:
        (size,) = LENGTH.unpack(os.pread(self.handle, LENGTH.size, offset))
        return os.pread(self.handle, size, offset + LENGTH.size).decode()


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
LOOKUP_BATCH = 500
LENGTH = struct.Struct("<I")


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
    changes: dict[int | None, array[int]] = field(default_factory=lambda: defaultdict(lambda: array("Q")))
    by_incident: dict[int, list[str]] = field(default_factory=lambda: defaultdict(list))
    phase_counts: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    first_seen: dict[int, dict[tuple[str, str], ChangeLine]] = field(default_factory=lambda: defaultdict(dict))
    last_seen: dict[int, dict[tuple[str, str], ChangeLine]] = field(default_factory=lambda: defaultdict(dict))
    named: dict[int, IncidentNameRow] = field(default_factory=dict)
    rumours: dict[int, list[RumourRow]] = field(default_factory=lambda: defaultdict(list))
    distortions: dict[int, list[RumourDistortionRow]] = field(default_factory=lambda: defaultdict(list))

    @classmethod
    async def load(cls, session: AsyncSession, names: dict[int, str]) -> "Ledger":
        ledger = cls(names)
        for row in await session.scalars(select(IncidentRow).order_by(IncidentRow.epoch, IncidentRow.id)):
            ledger.incidents[row.id] = row
        for chronicle_id, text in await session.execute(select(ChronicleRow.id, ChronicleRow.text).order_by(ChronicleRow.id)):
            ledger.lines[chronicle_id] = text
        for participant in await session.scalars(select(IncidentParticipantRow).order_by(IncidentParticipantRow.incident_id, IncidentParticipantRow.position)):
            ledger.participants[participant.incident_id].append(participant)
        for fact in await session.scalars(select(IncidentFactRow).order_by(IncidentFactRow.incident_id, IncidentFactRow.key, IncidentFactRow.position)):
            ledger.facts[fact.incident_id].append(fact)
        for step in await session.scalars(select(IncidentStepRow).order_by(IncidentStepRow.incident_id, IncidentStepRow.position, IncidentStepRow.id)):
            ledger.steps[step.incident_id].append(step)
        for state in await session.scalars(select(IncidentStepStateRow).order_by(IncidentStepStateRow.step_id, IncidentStepStateRow.node_id)):
            ledger.states[state.step_id].append(state)
        for term in await session.scalars(select(IncidentTermRow).order_by(IncidentTermRow.incident_id, IncidentTermRow.position)):
            ledger.terms[term.incident_id].append(term)
        await ledger.load_tellings(session)
        await ledger.load_changes(session)
        return ledger

    async def load_changes(self, session: AsyncSession) -> None:
        last = int(await session.scalar(select(func.coalesce(func.max(StateChangeRow.id), 0))) or 0)
        for start in range(0, last, CHANGE_CHUNK):
            end = start + CHANGE_CHUNK
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

    def take_change(self, change: ChangeLine, terms: list[TermLine]) -> None:
        text = self.change_text(change, terms)
        self.changes[change.node_id].append(self.store.append(text))
        happening = self.incidents.get(change.incident_id) if change.incident_id is not None else None
        if happening is not None and happening.kind.startswith(PHASE_PREFIX):
            self.phase_counts[happening.id] += 1
        elif change.incident_id is not None:
            self.by_incident[change.incident_id].append(text)
        if change.node_id is not None and change.operation is LedgerOperation.UPDATE and change.field is not None:
            key = (change.table_name, change.field)
            self.first_seen[change.node_id].setdefault(key, change)
            self.last_seen[change.node_id][key] = change

    async def load_tellings(self, session: AsyncSession) -> None:
        for name in await session.scalars(select(IncidentNameRow).order_by(IncidentNameRow.incident_id)):
            self.named[name.incident_id] = name
        for rumour in await session.scalars(select(RumourRow).order_by(RumourRow.incident_id, RumourRow.epoch, RumourRow.id)):
            self.rumours[rumour.incident_id].append(rumour)
        for distortion in await session.scalars(select(RumourDistortionRow).order_by(RumourDistortionRow.rumour_id, RumourDistortionRow.position)):
            self.distortions[distortion.rumour_id].append(distortion)

    def name(self, node_id: int | None) -> str:
        if node_id is None:
            return ""
        return self.names.get(node_id) or "an unnamed record"

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
        return found or (incident.note or words(incident.kind))

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
        source = self.name(source_node_id) if source_node_id is not None else ""
        happening = self.incidents.get(source_incident_id) if source_incident_id is not None else None
        origin = f" from {source}" if source else ""
        if happening is not None:
            origin += f" ({self.line_of(happening)})"
        return f"{words(term).lower()} {signed(op, amount)}{origin}"

    def step_text(self, step: IncidentStepRow) -> str:
        parts = [f"{step.position + 1}."]
        if step.round is not None:
            parts.append(f"round {step.round + 1}:")
        if step.actor_node_id is not None:
            parts.append(self.name(step.actor_node_id))
        parts.append(spoken(step.action))
        if step.target_node_id is not None:
            parts.append(self.name(step.target_node_id))
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
        return text if text is not None else "none"

    def shift_text(self, before: ChangeLine, after: ChangeLine) -> str:
        rewritten = rewritten_parts(before.before_text, after.after_text)
        if rewritten is not None:
            return f"rewrote {rewritten}"
        return f"{self.value_text(before, True)} → {self.value_text(after, False)}"

    def change_text(self, change: ChangeLine, terms: list[TermLine]) -> str:
        record = title_of(change.table_name).lower()
        owner = f" of {self.name(change.node_id)}" if change.node_id is not None else ""
        if change.operation is LedgerOperation.UPDATE:
            body = f"{words(change.field or '').lower()} of {record}{owner}: {self.shift_text(change, change)}"
        else:
            body = f"{'created' if change.operation is LedgerOperation.INSERT else 'removed'} {an(record)} record{owner}"
        actor = f" by {self.name(change.actor_node_id)}" if change.actor_node_id is not None else f" by the {spoken(change.actor_kind)}"
        phase = f" in {spoken(change.phase)}" if change.phase else ""
        reasons = [self.term_text(term.op, term.term, term.amount, term.source_node_id, term.source_incident_id) for term in terms]
        why = f" because {'; '.join(reasons)}" if reasons else ""
        happening = self.incidents.get(change.incident_id) if change.incident_id is not None else None
        cause = f" (during: {self.line_of(happening)})" if happening is not None and not happening.kind.startswith(PHASE_PREFIX) else ""
        when = moment_text(change.epoch, change.year, change.season, change.day, change.hour)
        return f"{when}: {body}{actor}{phase}{why}{cause}"

    def account_text(self, incident: IncidentRow, node_id: int | None) -> str:
        roles = self.participants.get(incident.id, [])
        own = [row.role for row in roles if row.node_id == node_id]
        parts = [self.account_head(incident)]
        if own:
            parts.append(f"as {', '.join(spoken(role) for role in own)}")
        parts.extend(self.account_place(incident))
        if own and all(role in KNOWERS for role in own):
            return " · ".join(parts)
        others = [f"{spoken(row.role)} {self.name(row.node_id)}" for row in roles if row.node_id != node_id and row.role not in UNLISTED_ROLES]
        knowing = Counter(row.role for row in roles if row.node_id != node_id and row.role in KNOWERS)
        others.extend(several(knowing[role], *words) for role, words in sorted(KNOWER_WORDS.items()) if knowing[role])
        if others:
            parts.append("with " + ", ".join(others))
        parts.extend(self.account_tail(incident))
        return " · ".join(parts)

    def account_head(self, incident: IncidentRow) -> str:
        found = self.heads.get(incident.id)
        if found is None:
            found = f"{self.when(incident)}: {self.line_of(incident)}"
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
        steps = [self.step_text(step) for step in self.steps.get(incident.id, [])]
        if steps:
            parts.append("steps: " + " ".join(steps))
        rumours = [self.rumour_text(rumour) for rumour in self.rumours.get(incident.id, [])]
        if rumours:
            parts.append("rumours: " + "; ".join(rumours))
        cause = self.incidents.get(incident.cause_incident_id) if incident.cause_incident_id is not None else None
        if cause is not None:
            parts.append(f"cause: {self.line_of(cause)}")
        self.tails[incident.id] = parts
        return parts

    def changes_cell(self, incident: IncidentRow) -> str:
        if incident.kind.startswith(PHASE_PREFIX):
            count = self.phase_counts.get(incident.id, 0)
            return f"{several(count, 'change', 'changes')}, each told under the record it changed" if count else ""
        return "; ".join(self.by_incident.get(incident.id, []))

    def then_and_now(self, node_id: int) -> list[tuple[str, str]]:
        first = self.first_seen.get(node_id, {})
        last = self.last_seen.get(node_id, {})
        found: list[tuple[str, str]] = []
        for key, earliest in first.items():
            latest = last[key]
            then, now = self.value_text(earliest, True), self.value_text(latest, False)
            if then != now:
                label = f"{words(key[1])} ({title_of(key[0]).lower()})"
                rewritten = rewritten_parts(earliest.before_text, latest.after_text)
                found.append(
                    (label, f"since epoch {earliest.epoch}: rewrote {rewritten}" if rewritten is not None else f"epoch {earliest.epoch}: {then} → now: {now}")
                )
        return found


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


def node_ids_of(ledger: Ledger) -> set[int]:
    nodes = {participant.node_id for rows in ledger.participants.values() for participant in rows}
    nodes.update(node for node in ledger.changes if node is not None)
    return nodes


async def add_history_sections(session: AsyncSession, index: TypedIndex) -> Ledger:
    ledger = await Ledger.load(session, index.names)
    taking_part: dict[int, list[int]] = defaultdict(list)
    for incident_id, rows in ledger.participants.items():
        for node_id in sorted({row.node_id for row in rows}):
            taking_part[node_id].append(incident_id)
    for node_id in sorted(node_ids_of(ledger)):
        incidents = sorted((ledger.incidents[item] for item in taking_part.get(node_id, []) if item in ledger.incidents), key=lambda row: (row.epoch, row.id))
        if incidents:
            told = array("Q", (ledger.store.append(ledger.account_text(row, node_id)) for row in incidents))
            index.sections[node_id].append(TypedSection(HISTORY_TITLE, spilled=SpilledRows(ledger.store, told)))
        changes = ledger.changes.get(node_id)
        if changes:
            index.sections[node_id].append(TypedSection(CHANGES_TITLE, spilled=SpilledRows(ledger.store, changes)))
        then = ledger.then_and_now(node_id)
        if then:
            section = TypedSection(THEN_TITLE)
            section.rows = [f"{label}: {text}" for label, text in then]
            index.sections[node_id].append(section)
    return ledger


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
        f"{title}: {ledger.line_of(incident)}",
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


async def record_tables(session: AsyncSession, ledger: Ledger) -> list[RecordTable]:
    tables: list[RecordTable] = []
    ages = list(await session.scalars(select(AgeRow).order_by(AgeRow.began_epoch, AgeRow.number)))
    spans = age_spans(ages)
    for position, (title, began, ended) in enumerate(spans):
        until = ended if ended is not None else (spans[position + 1][1] - 1 if position + 1 < len(spans) else None)
        table = RecordTable(title, ["Moment", "Kind", "Line", "Name", "Place", "Taking part", "Account", "Steps", "Changes", "Rumours", "Cause"])
        for incident in ledger.incidents.values():
            if incident.epoch < began or (until is not None and incident.epoch > until):
                continue
            cause = ledger.incidents.get(incident.cause_incident_id) if incident.cause_incident_id is not None else None
            table.rows.append(
                [
                    ledger.when(incident),
                    words(incident.kind),
                    ledger.line_of(incident),
                    ledger.name_of(incident),
                    ledger.name(incident.place_entity_id),
                    ", ".join(f"{spoken(row.role)} {ledger.name(row.node_id)}" for row in ledger.participants.get(incident.id, [])),
                    "; ".join(ledger.fact_text(fact) for fact in ledger.facts.get(incident.id, [])),
                    " ".join(ledger.step_text(step) for step in ledger.steps.get(incident.id, [])),
                    ledger.changes_cell(incident),
                    "; ".join(ledger.rumour_text(rumour) for rumour in ledger.rumours.get(incident.id, [])),
                    ledger.line_of(cause) if cause is not None else "",
                ]
            )
        if table.rows:
            tables.append(table)
    for incident in ledger.incidents.values():
        spec = INCIDENT_KINDS.get(incident.kind)
        report = REPORT_GROUPS.get(spec.group) if spec is not None else None
        if report is not None and ledger.steps.get(incident.id):
            tables.append(report_table(ledger, incident, report))
    loose = RecordTable("Changes to records of no single node", ["Change"])
    loose.rows = [[text] for text in SpilledRows(ledger.store, ledger.changes.get(None, array("Q")))]
    if loose.rows:
        tables.append(loose)
    checkpoints = RecordTable("Checkpoints of the past", ["Epoch", "Table", "Rows", "Digest", "Last change"])
    for row in await session.scalars(select(StateCheckpointRow).order_by(StateCheckpointRow.epoch, StateCheckpointRow.table_name)):
        checkpoints.rows.append([str(row.epoch), title_of(row.table_name), str(row.row_count), row.digest, str(row.last_change_id)])
    if checkpoints.rows:
        tables.append(checkpoints)
    return tables
