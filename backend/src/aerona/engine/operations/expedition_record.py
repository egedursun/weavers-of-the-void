from aerona.catalog.life.operations import EXPEDITION_STATES, EXPEDITION_STEPS
from aerona.db.tables.operations import ExpeditionLogRow, ExpeditionRow
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.operations import ExpeditionEvent
from aerona.domain.enums.records import FactUnit, ProcessClock, StepLocus, StepOutcome
from aerona.engine.context import TickContext
from aerona.engine.primitives.process_steps import append_steps, open_process
from aerona.engine.recording.record import StepDraft

EXPEDITION_KEY = "expedition.delve"


def expedition_roles(row: ExpeditionRow) -> list[tuple[int, IncidentRole]]:
    found: list[tuple[int, IncidentRole]] = []
    if row.leader_entity_id is not None:
        found.append((row.leader_entity_id, IncidentRole.LEADER))
    if row.target_entity_id is not None:
        found.append((row.target_entity_id, IncidentRole.DESTINATION))
    if row.sponsor_node_id is not None:
        found.append((row.sponsor_node_id, IncidentRole.PATRON))
    return found


async def expedition_incident(ctx: TickContext, row: ExpeditionRow) -> int:
    if row.incident_id is None:
        row.incident_id = await open_process(ctx, EXPEDITION_KEY, ProcessClock.MARCH, expedition_roles(row), place=row.target_entity_id)
    return row.incident_id


def amount_of(entry: ExpeditionLogRow) -> tuple[float | None, FactUnit | None]:
    if entry.provisions_used:
        return float(entry.provisions_used), FactUnit.COUNT
    if entry.stress:
        return float(entry.stress), FactUnit.SEVERITY
    return None, None


async def log_entry(ctx: TickContext, row: ExpeditionRow, entry: ExpeditionLogRow) -> None:
    ctx.session.add(entry)
    await ctx.session.flush()
    incident = await expedition_incident(ctx, row)
    amount, unit = amount_of(entry)
    state = EXPEDITION_STATES.get(entry.event)
    draft = StepDraft(
        EXPEDITION_STEPS[entry.event],
        actor=entry.member_entity_id or row.leader_entity_id,
        target=row.target_entity_id,
        round=entry.leg,
        locus_kind=StepLocus.ROOM if entry.event is ExpeditionEvent.ROOM else StepLocus.NONE,
        locus_key=entry.quirk.value if entry.quirk is not None else entry.resolve.value if entry.resolve is not None else None,
        amount=amount,
        unit=unit,
        outcome=StepOutcome.KILLED if entry.event is ExpeditionEvent.FALLEN else None,
        record_table=ExpeditionLogRow.__tablename__,
        record_key=str(entry.id),
        states=((entry.member_entity_id, state),) if state is not None and entry.member_entity_id is not None else (),
    )
    steps = await append_steps(ctx, incident, EXPEDITION_KEY, ProcessClock.MARCH, [draft])
    entry.incident_id = incident
    entry.step_id = steps[0].id
