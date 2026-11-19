from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.catalog.incident_kinds.spec import IncidentKindSpec
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import fact_word
from aerona.db.tables.changes import StateChangeRow, StateChangeTermRow
from aerona.db.tables.culture import RumourRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.records import IncidentFactRow, IncidentStepRow, IncidentStepStateRow, IncidentTermRow
from aerona.db.tables.tellings import IncidentNameRow, RumourDistortionRow
from aerona.domain.enums.body import DamageType
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.modifier import IncidentRole, ModifierOp
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.records import (
    FactUnit,
    IncidentTier,
    InstrumentKind,
    ProcessGroup,
    RumourDistortion,
    StepAction,
    StepLocus,
    StepOutcome,
    StepState,
    WitnessMode,
)
from aerona.engine.recording.render import render_incident

CHAIN_DEPTH = 50
NAME_CHUNK = 500


@dataclass(frozen=True)
class AccountMoment:
    epoch: int
    year: int | None
    season: int | None
    day: int | None
    hour: int | None


@dataclass(frozen=True)
class AccountParticipant:
    node_id: int
    name: str | None
    role: IncidentRole
    position: int
    witness_mode: WitnessMode | None
    fidelity: int | None


@dataclass(frozen=True)
class AccountFact:
    id: int
    key: str
    position: int
    node_id: int | None
    node_name: str | None
    number: float | None
    unit: FactUnit | None
    enum_name: str | None
    enum_value: str | None
    name: str | None


@dataclass(frozen=True)
class AccountTerm:
    position: int
    term: str
    op: ModifierOp
    amount: float
    source_node_id: int | None
    source_name: str | None
    source_incident_id: int | None
    fact_key: str | None


@dataclass(frozen=True)
class AccountStepState:
    node_id: int
    node_name: str | None
    state: StepState


@dataclass(frozen=True)
class AccountStep:
    id: int
    incident_id: int
    position: int
    round: int | None
    parent_step_id: int | None
    moment: AccountMoment
    actor_node_id: int | None
    actor_name: str | None
    target_node_id: int | None
    target_name: str | None
    action: StepAction
    instrument_kind: InstrumentKind
    instrument_node_id: int | None
    instrument_name: str | None
    instrument_key: str | None
    locus_kind: StepLocus
    locus_key: str | None
    locus_node_id: int | None
    locus_name: str | None
    damage_type: DamageType | None
    amount: float | None
    unit: FactUnit | None
    outcome: StepOutcome | None
    record_table: str | None
    record_key: str | None
    states: tuple[AccountStepState, ...]


@dataclass(frozen=True)
class AccountChange:
    id: int
    moment: AccountMoment
    table_name: str
    row_key: str
    node_id: int | None
    node_name: str | None
    operation: LedgerOperation
    field: str | None
    before_number: float | None
    after_number: float | None
    before_text: str | None
    after_text: str | None
    before_node_id: int | None
    before_node_name: str | None
    after_node_id: int | None
    after_node_name: str | None
    actor_kind: ActorKind
    actor_node_id: int | None
    actor_name: str | None
    phase: str | None
    incident_id: int | None
    step_id: int | None
    terms: tuple[AccountTerm, ...]


@dataclass(frozen=True)
class AccountDistortion:
    id: int
    position: int
    distortion: RumourDistortion
    role: IncidentRole | None
    fact_key: str | None
    step_id: int | None
    told_node_id: int | None
    told_name: str | None
    told_number: float | None
    told_enum_value: str | None
    told_year: int | None
    told_incident_id: int | None
    told_action: StepAction | None
    told_outcome: StepOutcome | None
    epoch: int
    locked: tuple[str, ...]


@dataclass(frozen=True)
class AccountRumour:
    id: int
    carrier_id: int
    carrier_name: str | None
    source_id: int | None
    source_name: str | None
    fidelity: int
    hops: int
    epoch: int
    distortions: tuple[AccountDistortion, ...]


@dataclass(frozen=True)
class AccountLink:
    id: int
    kind: str
    epoch: int
    year: int | None
    text: str | None


@dataclass(frozen=True)
class Account:
    id: int
    kind: str
    family: str
    group: ProcessGroup | None
    known: bool
    name: str | None
    name_language_id: int | None
    name_language_name: str | None
    moment: AccountMoment
    world_id: int | None
    place_id: int | None
    place_name: str | None
    origin_id: int | None
    origin_name: str | None
    destination_id: int | None
    destination_name: str | None
    tier: IncidentTier
    locked: tuple[str, ...]
    magnitude: int
    chronicle_id: int | None
    line: str | None
    retold: str | None
    note: str | None
    thread_id: int | None
    participants: tuple[AccountParticipant, ...]
    facts: tuple[AccountFact, ...]
    steps: tuple[AccountStep, ...]
    terms: tuple[AccountTerm, ...]
    changes: tuple[AccountChange, ...]
    rumours: tuple[AccountRumour, ...]
    causes: tuple[AccountLink, ...]
    effects: tuple[AccountLink, ...]

    @property
    def witnesses(self) -> tuple[AccountParticipant, ...]:
        return tuple(item for item in self.participants if item.role is IncidentRole.WITNESS)


@dataclass(frozen=True)
class HistoryEntry:
    incident_id: int
    kind: str
    group: ProcessGroup | None
    moment: AccountMoment
    roles: tuple[IncidentRole, ...]
    line: str | None
    place_id: int | None
    place_name: str | None
    tier: IncidentTier
    facts: int
    steps: int
    changes: int


@dataclass(frozen=True)
class HistoryPage:
    node_id: int
    total_incidents: int
    incidents: tuple[HistoryEntry, ...]
    total_steps: int
    steps: tuple[AccountStep, ...]
    total_changes: int
    changes: tuple[AccountChange, ...]
    kinds: tuple[str, ...]
    roles: tuple[IncidentRole, ...]


@dataclass
class Names:
    session: AsyncSession
    known: dict[int, str | None] = field(default_factory=dict)

    async def load(self, ids: Iterable[int | None]) -> None:
        wanted = sorted({value for value in ids if value is not None and value not in self.known})
        for start in range(0, len(wanted), NAME_CHUNK):
            chunk = wanted[start : start + NAME_CHUNK]
            found = {row.id: row.name for row in await self.session.execute(select(NodeRow.id, NodeRow.name).where(NodeRow.id.in_(chunk)))}
            for value in chunk:
                self.known[value] = found.get(value)

    def of(self, node_id: int | None) -> str | None:
        return self.known.get(node_id) if node_id is not None else None


def moment_of(row: IncidentRow | IncidentStepRow | StateChangeRow, epoch: int) -> AccountMoment:
    return AccountMoment(epoch=epoch, year=row.year, season=row.season, day=row.day, hour=row.hour)


def kind_spec(key: str) -> IncidentKindSpec | None:
    return INCIDENT_KINDS.get(key)


def fact_value(fact: AccountFact) -> object:
    if fact.node_id is not None:
        return fact.node_name or "someone"
    if fact.number is not None:
        return fact.number
    if fact.enum_value is not None:
        return fact_word(fact.enum_name, fact.enum_value)
    return fact.name


def retold(spec: IncidentKindSpec | None, participants: Sequence[AccountParticipant], facts: Sequence[AccountFact]) -> str | None:
    if spec is None or not spec.told or not spec.template:
        return None
    names: dict[IncidentRole, list[str]] = defaultdict(list)
    for item in sorted(participants, key=lambda row: row.position):
        names[item.role].append(item.name or "someone")
    values: dict[str, list[object]] = defaultdict(list)
    for fact in sorted(facts, key=lambda row: (row.key, row.position)):
        values[fact.key].append(fact_value(fact))
    declared = {fact.key: fact for fact in spec.facts}
    facts_told: dict[str, object] = {key: items if declared.get(key) is not None and declared[key].many else items[0] for key, items in values.items()}
    try:
        return render_incident(spec, names, facts_told)
    except ValidationFailedError:
        return None


async def step_records(session: AsyncSession, names: Names, rows: Sequence[IncidentStepRow], epochs: dict[int, int]) -> list[AccountStep]:
    ids = [row.id for row in rows]
    states: dict[int, list[IncidentStepStateRow]] = defaultdict(list)
    for start in range(0, len(ids), NAME_CHUNK):
        statement = (
            select(IncidentStepStateRow)
            .where(IncidentStepStateRow.step_id.in_(ids[start : start + NAME_CHUNK]))
            .order_by(IncidentStepStateRow.step_id, IncidentStepStateRow.node_id, IncidentStepStateRow.state)
        )
        for state in await session.scalars(statement):
            states[state.step_id].append(state)
    await names.load(
        [value for row in rows for value in (row.actor_node_id, row.target_node_id, row.instrument_node_id, row.locus_node_id)]
        + [state.node_id for found in states.values() for state in found]
    )
    return [
        AccountStep(
            id=row.id,
            incident_id=row.incident_id,
            position=row.position,
            round=row.round,
            parent_step_id=row.parent_step_id,
            moment=moment_of(row, epochs.get(row.incident_id, 0)),
            actor_node_id=row.actor_node_id,
            actor_name=names.of(row.actor_node_id),
            target_node_id=row.target_node_id,
            target_name=names.of(row.target_node_id),
            action=row.action,
            instrument_kind=row.instrument_kind,
            instrument_node_id=row.instrument_node_id,
            instrument_name=names.of(row.instrument_node_id),
            instrument_key=row.instrument_key,
            locus_kind=row.locus_kind,
            locus_key=row.locus_key,
            locus_node_id=row.locus_node_id,
            locus_name=names.of(row.locus_node_id),
            damage_type=row.damage_type,
            amount=row.amount,
            unit=row.unit,
            outcome=row.outcome,
            record_table=row.record_table,
            record_key=row.record_key,
            states=tuple(AccountStepState(node_id=state.node_id, node_name=names.of(state.node_id), state=state.state) for state in states.get(row.id, [])),
        )
        for row in rows
    ]


async def change_records(session: AsyncSession, names: Names, rows: Sequence[StateChangeRow]) -> list[AccountChange]:
    ids = [row.id for row in rows]
    terms: dict[int, list[StateChangeTermRow]] = defaultdict(list)
    for start in range(0, len(ids), NAME_CHUNK):
        statement = (
            select(StateChangeTermRow)
            .where(StateChangeTermRow.change_id.in_(ids[start : start + NAME_CHUNK]))
            .order_by(StateChangeTermRow.change_id, StateChangeTermRow.position)
        )
        for term in await session.scalars(statement):
            terms[term.change_id].append(term)
    await names.load(
        [value for row in rows for value in (row.node_id, row.before_node_id, row.after_node_id, row.actor_node_id)]
        + [term.source_node_id for found in terms.values() for term in found]
    )
    return [
        AccountChange(
            id=row.id,
            moment=moment_of(row, row.epoch),
            table_name=row.table_name,
            row_key=row.row_key,
            node_id=row.node_id,
            node_name=names.of(row.node_id),
            operation=row.operation,
            field=row.field,
            before_number=row.before_number,
            after_number=row.after_number,
            before_text=row.before_text,
            after_text=row.after_text,
            before_node_id=row.before_node_id,
            before_node_name=names.of(row.before_node_id),
            after_node_id=row.after_node_id,
            after_node_name=names.of(row.after_node_id),
            actor_kind=row.actor_kind,
            actor_node_id=row.actor_node_id,
            actor_name=names.of(row.actor_node_id),
            phase=row.phase,
            incident_id=row.incident_id,
            step_id=row.step_id,
            terms=tuple(
                AccountTerm(
                    position=term.position,
                    term=term.term,
                    op=term.op,
                    amount=term.amount,
                    source_node_id=term.source_node_id,
                    source_name=names.of(term.source_node_id),
                    source_incident_id=term.source_incident_id,
                    fact_key=row.field,
                )
                for term in terms.get(row.id, [])
            ),
        )
        for row in rows
    ]


async def link_records(session: AsyncSession, rows: Sequence[IncidentRow]) -> list[AccountLink]:
    texts = await lines_of(session, [row.chronicle_id for row in rows])
    return [AccountLink(id=row.id, kind=row.kind, epoch=row.epoch, year=row.year, text=texts.get(row.chronicle_id)) for row in rows]


async def lines_of(session: AsyncSession, chronicle_ids: Iterable[int | None]) -> dict[int | None, str]:
    wanted = sorted({value for value in chronicle_ids if value is not None})
    found: dict[int | None, str] = {}
    for start in range(0, len(wanted), NAME_CHUNK):
        statement = select(ChronicleRow.id, ChronicleRow.text).where(ChronicleRow.id.in_(wanted[start : start + NAME_CHUNK]))
        found.update({row.id: row.text for row in await session.execute(statement)})
    return found


def distortion_record(names: Names, row: RumourDistortionRow) -> AccountDistortion:
    return AccountDistortion(
        id=row.id,
        position=row.position,
        distortion=row.distortion,
        role=row.role,
        fact_key=row.fact_key,
        step_id=row.step_id,
        told_node_id=row.told_node_id,
        told_name=names.of(row.told_node_id),
        told_number=row.told_number,
        told_enum_value=row.told_enum_value,
        told_year=row.told_year,
        told_incident_id=row.told_incident_id,
        told_action=row.told_action,
        told_outcome=row.told_outcome,
        epoch=row.epoch,
        locked=tuple(row.locked or ()),
    )


async def causes_of(session: AsyncSession, incident: IncidentRow) -> list[IncidentRow]:
    path: list[IncidentRow] = []
    seen = {incident.id}
    current = incident.cause_incident_id
    while current is not None and current not in seen and len(path) < CHAIN_DEPTH:
        row = await session.get(IncidentRow, current)
        if row is None:
            break
        path.append(row)
        seen.add(row.id)
        current = row.cause_incident_id
    return list(reversed(path))


async def effects_of(session: AsyncSession, incident_id: int) -> list[IncidentRow]:
    statement = select(IncidentRow).where(IncidentRow.cause_incident_id == incident_id).order_by(IncidentRow.epoch, IncidentRow.id)
    return list(await session.scalars(statement))


async def account_of(session: AsyncSession, incident_id: int) -> Account:
    incident = await session.get(IncidentRow, incident_id)
    if incident is None:
        raise NotFoundError("No such happening.")
    names = Names(session)
    participant_rows = list(
        await session.scalars(
            select(IncidentParticipantRow)
            .where(IncidentParticipantRow.incident_id == incident.id)
            .order_by(IncidentParticipantRow.position, IncidentParticipantRow.role, IncidentParticipantRow.node_id)
        )
    )
    fact_rows = list(
        await session.scalars(select(IncidentFactRow).where(IncidentFactRow.incident_id == incident.id).order_by(IncidentFactRow.key, IncidentFactRow.position))
    )
    step_rows = list(
        await session.scalars(select(IncidentStepRow).where(IncidentStepRow.incident_id == incident.id).order_by(IncidentStepRow.position, IncidentStepRow.id))
    )
    term_rows = list(
        await session.scalars(select(IncidentTermRow).where(IncidentTermRow.incident_id == incident.id).order_by(IncidentTermRow.position, IncidentTermRow.id))
    )
    change_rows = list(await session.scalars(select(StateChangeRow).where(StateChangeRow.incident_id == incident.id).order_by(StateChangeRow.id)))
    rumour_rows = list(await session.scalars(select(RumourRow).where(RumourRow.incident_id == incident.id).order_by(RumourRow.epoch, RumourRow.id)))
    distortions: dict[int, list[RumourDistortionRow]] = defaultdict(list)
    if rumour_rows:
        statement = (
            select(RumourDistortionRow)
            .where(RumourDistortionRow.rumour_id.in_([row.id for row in rumour_rows]))
            .order_by(RumourDistortionRow.rumour_id, RumourDistortionRow.position, RumourDistortionRow.id)
        )
        for row in await session.scalars(statement):
            distortions[row.rumour_id].append(row)
    named = await session.get(IncidentNameRow, incident.id)
    await names.load(
        [incident.place_entity_id, incident.origin_entity_id, incident.destination_entity_id]
        + [row.node_id for row in participant_rows]
        + [row.node_id for row in fact_rows]
        + [row.source_node_id for row in term_rows]
        + [value for row in rumour_rows for value in (row.carrier_entity_id, row.source_entity_id)]
        + [row.told_node_id for found in distortions.values() for row in found]
        + [named.language_entity_id if named is not None else None]
    )
    participants = tuple(
        AccountParticipant(
            node_id=row.node_id, name=names.of(row.node_id), role=row.role, position=row.position, witness_mode=row.witness_mode, fidelity=row.fidelity
        )
        for row in participant_rows
    )
    facts = tuple(
        AccountFact(
            id=row.id,
            key=row.key,
            position=row.position,
            node_id=row.node_id,
            node_name=names.of(row.node_id),
            number=row.number,
            unit=row.unit,
            enum_name=row.enum_name,
            enum_value=row.enum_value,
            name=row.name,
        )
        for row in fact_rows
    )
    spec = kind_spec(incident.kind)
    line = (await lines_of(session, [incident.chronicle_id])).get(incident.chronicle_id)
    return Account(
        id=incident.id,
        kind=incident.kind,
        family=incident.kind.split(".", 1)[0],
        group=spec.group if spec is not None else None,
        known=spec is not None,
        name=named.name if named is not None else None,
        name_language_id=named.language_entity_id if named is not None else None,
        name_language_name=names.of(named.language_entity_id) if named is not None else None,
        moment=moment_of(incident, incident.epoch),
        world_id=incident.world_id,
        place_id=incident.place_entity_id,
        place_name=names.of(incident.place_entity_id),
        origin_id=incident.origin_entity_id,
        origin_name=names.of(incident.origin_entity_id),
        destination_id=incident.destination_entity_id,
        destination_name=names.of(incident.destination_entity_id),
        tier=incident.tier,
        locked=tuple(incident.locked or ()),
        magnitude=incident.magnitude,
        chronicle_id=incident.chronicle_id,
        line=line,
        retold=retold(spec, participants, facts),
        note=incident.note,
        thread_id=incident.thread_id,
        participants=participants,
        facts=facts,
        steps=tuple(await step_records(session, names, step_rows, {incident.id: incident.epoch})),
        terms=tuple(
            AccountTerm(
                position=row.position,
                term=row.term,
                op=row.op,
                amount=row.amount,
                source_node_id=row.source_node_id,
                source_name=names.of(row.source_node_id),
                source_incident_id=row.source_incident_id,
                fact_key=row.fact_key,
            )
            for row in term_rows
        ),
        changes=tuple(await change_records(session, names, change_rows)),
        rumours=tuple(
            AccountRumour(
                id=row.id,
                carrier_id=row.carrier_entity_id,
                carrier_name=names.of(row.carrier_entity_id),
                source_id=row.source_entity_id,
                source_name=names.of(row.source_entity_id),
                fidelity=row.fidelity,
                hops=row.hops,
                epoch=row.epoch,
                distortions=tuple(distortion_record(names, item) for item in distortions.get(row.id, [])),
            )
            for row in rumour_rows
        ),
        causes=tuple(await link_records(session, await causes_of(session, incident))),
        effects=tuple(await link_records(session, await effects_of(session, incident.id))),
    )


async def history_of(
    session: AsyncSession,
    node_id: int,
    *,
    role: IncidentRole | None = None,
    kind: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> HistoryPage:
    if await session.scalar(select(NodeRow.id).where(NodeRow.id == node_id)) is None:
        raise NotFoundError("No such record.")
    names = Names(session)
    involved = select(IncidentParticipantRow.incident_id).where(IncidentParticipantRow.node_id == node_id)
    if role is not None:
        involved = involved.where(IncidentParticipantRow.role == role)
    chosen = select(IncidentRow).where(IncidentRow.id.in_(involved))
    if kind is not None:
        chosen = chosen.where((IncidentRow.kind == kind) | IncidentRow.kind.startswith(f"{kind}."))
    total_incidents = int(await session.scalar(select(func.count()).select_from(chosen.subquery())) or 0)
    incident_rows = list(await session.scalars(chosen.order_by(IncidentRow.epoch.desc(), IncidentRow.id.desc()).offset(offset).limit(limit)))
    ids = [row.id for row in incident_rows]
    roles: dict[int, list[IncidentRole]] = defaultdict(list)
    facts: dict[int, int] = {}
    steps: dict[int, int] = {}
    changes: dict[int, int] = {}
    if ids:
        for incident_id, given in await session.execute(
            select(IncidentParticipantRow.incident_id, IncidentParticipantRow.role)
            .where(IncidentParticipantRow.incident_id.in_(ids), IncidentParticipantRow.node_id == node_id)
            .order_by(IncidentParticipantRow.incident_id, IncidentParticipantRow.role)
        ):
            roles[incident_id].append(given)
        for table, column, target in (
            (IncidentFactRow, IncidentFactRow.incident_id, facts),
            (IncidentStepRow, IncidentStepRow.incident_id, steps),
            (StateChangeRow, StateChangeRow.incident_id, changes),
        ):
            counted = select(column, func.count()).select_from(table).where(column.in_(ids)).group_by(column)
            target.update({int(key): int(value) for key, value in await session.execute(counted) if key is not None})
    lines = await lines_of(session, [row.chronicle_id for row in incident_rows])
    await names.load([row.place_entity_id for row in incident_rows])
    entries = tuple(
        HistoryEntry(
            incident_id=row.id,
            kind=row.kind,
            group=spec.group if (spec := kind_spec(row.kind)) is not None else None,
            moment=moment_of(row, row.epoch),
            roles=tuple(roles.get(row.id, [])),
            line=lines.get(row.chronicle_id),
            place_id=row.place_entity_id,
            place_name=names.of(row.place_entity_id),
            tier=row.tier,
            facts=facts.get(row.id, 0),
            steps=steps.get(row.id, 0),
            changes=changes.get(row.id, 0),
        )
        for row in incident_rows
    )
    acting = select(IncidentStepRow).where((IncidentStepRow.actor_node_id == node_id) | (IncidentStepRow.target_node_id == node_id))
    total_steps = int(await session.scalar(select(func.count()).select_from(acting.subquery())) or 0)
    step_rows = list(await session.scalars(acting.order_by(IncidentStepRow.incident_id.desc(), IncidentStepRow.position).offset(offset).limit(limit)))
    epochs = {
        row.id: row.epoch
        for row in await session.execute(select(IncidentRow.id, IncidentRow.epoch).where(IncidentRow.id.in_(sorted({row.incident_id for row in step_rows}))))
    }
    changed = select(StateChangeRow).where(StateChangeRow.node_id == node_id)
    total_changes = int(await session.scalar(select(func.count()).select_from(changed.subquery())) or 0)
    change_rows = list(await session.scalars(changed.order_by(StateChangeRow.id.desc()).offset(offset).limit(limit)))
    kinds = sorted(
        set(
            (
                await session.scalars(
                    select(IncidentRow.kind)
                    .where(IncidentRow.id.in_(select(IncidentParticipantRow.incident_id).where(IncidentParticipantRow.node_id == node_id)))
                    .distinct()
                )
            ).all()
        )
    )
    held_roles = sorted(
        set((await session.scalars(select(IncidentParticipantRow.role).where(IncidentParticipantRow.node_id == node_id).distinct())).all()),
        key=lambda item: item.value,
    )
    return HistoryPage(
        node_id=node_id,
        total_incidents=total_incidents,
        incidents=entries,
        total_steps=total_steps,
        steps=tuple(await step_records(session, names, step_rows, epochs)),
        total_changes=total_changes,
        changes=tuple(await change_records(session, names, change_rows)),
        kinds=tuple(kinds),
        roles=tuple(held_roles),
    )
