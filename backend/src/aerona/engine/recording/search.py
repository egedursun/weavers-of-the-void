from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.records import IncidentFactRow, IncidentStepRow
from aerona.domain.enums.records import FactUnit, InstrumentKind, StepAction
from aerona.engine.recording.accounts import Names, lines_of


@dataclass(frozen=True)
class RecordQuery:
    fact_key: str | None = None
    enum_name: str | None = None
    enum_value: str | None = None
    node_id: int | None = None
    kind: str | None = None
    action: StepAction | None = None
    instrument_kind: InstrumentKind | None = None

    @property
    def by_step(self) -> bool:
        return self.action is not None or self.instrument_kind is not None


@dataclass(frozen=True)
class RecordHit:
    incident_id: int
    kind: str
    epoch: int
    year: int | None
    line: str | None
    fact_key: str | None
    node_id: int | None
    node_name: str | None
    number: float | None
    unit: FactUnit | None
    enum_name: str | None
    enum_value: str | None
    name: str | None
    step_action: StepAction | None
    instrument_kind: InstrumentKind | None


async def search_records(session: AsyncSession, query: RecordQuery, *, offset: int = 0, limit: int = 50) -> tuple[int, list[RecordHit]]:
    names = Names(session)
    if query.by_step:
        steps = select(IncidentStepRow, IncidentRow).join(IncidentRow, IncidentRow.id == IncidentStepRow.incident_id)
        if query.action is not None:
            steps = steps.where(IncidentStepRow.action == query.action)
        if query.instrument_kind is not None:
            steps = steps.where(IncidentStepRow.instrument_kind == query.instrument_kind)
        if query.node_id is not None:
            steps = steps.where((IncidentStepRow.actor_node_id == query.node_id) | (IncidentStepRow.target_node_id == query.node_id))
        if query.kind is not None:
            steps = steps.where((IncidentRow.kind == query.kind) | IncidentRow.kind.startswith(f"{query.kind}."))
        total = int(await session.scalar(select(func.count()).select_from(steps.subquery())) or 0)
        found = list(
            await session.execute(steps.order_by(IncidentRow.epoch.desc(), IncidentRow.id.desc(), IncidentStepRow.position).offset(offset).limit(limit))
        )
        lines = await lines_of(session, [incident.chronicle_id for _, incident in found])
        await names.load([step.instrument_node_id for step, _ in found])
        return total, [
            RecordHit(
                incident_id=incident.id,
                kind=incident.kind,
                epoch=incident.epoch,
                year=incident.year,
                line=lines.get(incident.chronicle_id),
                fact_key=None,
                node_id=step.instrument_node_id,
                node_name=names.of(step.instrument_node_id),
                number=step.amount,
                unit=step.unit,
                enum_name=None,
                enum_value=step.instrument_key,
                name=None,
                step_action=step.action,
                instrument_kind=step.instrument_kind,
            )
            for step, incident in found
        ]
    facts = select(IncidentFactRow, IncidentRow).join(IncidentRow, IncidentRow.id == IncidentFactRow.incident_id)
    if query.fact_key is not None:
        facts = facts.where(IncidentFactRow.key == query.fact_key)
    if query.enum_name is not None:
        facts = facts.where(IncidentFactRow.enum_name == query.enum_name)
    if query.enum_value is not None:
        facts = facts.where(IncidentFactRow.enum_value == query.enum_value)
    if query.node_id is not None:
        facts = facts.where(IncidentFactRow.node_id == query.node_id)
    if query.kind is not None:
        facts = facts.where((IncidentRow.kind == query.kind) | IncidentRow.kind.startswith(f"{query.kind}."))
    total = int(await session.scalar(select(func.count()).select_from(facts.subquery())) or 0)
    rows = list(
        await session.execute(
            facts.order_by(IncidentRow.epoch.desc(), IncidentRow.id.desc(), IncidentFactRow.key, IncidentFactRow.position).offset(offset).limit(limit)
        )
    )
    lines = await lines_of(session, [incident.chronicle_id for _, incident in rows])
    await names.load([fact.node_id for fact, _ in rows])
    return total, [
        RecordHit(
            incident_id=incident.id,
            kind=incident.kind,
            epoch=incident.epoch,
            year=incident.year,
            line=lines.get(incident.chronicle_id),
            fact_key=fact.key,
            node_id=fact.node_id,
            node_name=names.of(fact.node_id),
            number=fact.number,
            unit=fact.unit,
            enum_name=fact.enum_name,
            enum_value=fact.enum_value,
            name=fact.name,
            step_action=None,
            instrument_kind=None,
        )
        for fact, incident in rows
    ]
