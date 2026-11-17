from collections.abc import Mapping
from types import MappingProxyType

from aerona.db.tables.records import IncidentStepRow
from aerona.db.tables.routes import JourneyRow
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, InstrumentKind, ProcessClock, StepAction, StepOutcome
from aerona.domain.enums.travel import JourneyEventKind
from aerona.engine.context import TickContext
from aerona.engine.primitives.process_steps import append_steps, open_process
from aerona.engine.recording.record import StepDraft

JOURNEY_KEY = "travel.journey"
JOURNEY_STEPS: Mapping[JourneyEventKind, StepAction] = MappingProxyType(
    {
        JourneyEventKind.PIRATES: StepAction.MEET_DANGER,
        JourneyEventKind.VOID_STORM: StepAction.MEET_DANGER,
        JourneyEventKind.CREATURE: StepAction.MEET_DANGER,
        JourneyEventKind.LOST_WAY: StepAction.LOSE_WAY,
        JourneyEventKind.DISCOVERY: StepAction.DISCOVER,
        JourneyEventKind.SACRIFICE: StepAction.SACRIFICE,
        JourneyEventKind.MEMORY_LOSS: StepAction.MEET_DANGER,
        JourneyEventKind.DREAM_NOT_RETURNED: StepAction.MEET_DANGER,
        JourneyEventKind.SAIL_SNAPPED: StepAction.BREAK,
        JourneyEventKind.BRIDGE_COLLAPSED: StepAction.COLLAPSE,
        JourneyEventKind.NOT_RELEASED: StepAction.MEET_DANGER,
        JourneyEventKind.STOWAWAY: StepAction.DISCOVER,
        JourneyEventKind.OUTER_TOUCH: StepAction.MEET_DANGER,
        JourneyEventKind.DERELICT: StepAction.DISCOVER,
        JourneyEventKind.TOLL: StepAction.TOLL,
        JourneyEventKind.CROSSING: StepAction.CROSS,
        JourneyEventKind.PROVISIONS: StepAction.REST,
        JourneyEventKind.OTHER: StepAction.TRAVEL,
        JourneyEventKind.ENCOUNTER: StepAction.MEET,
        JourneyEventKind.BIRTH: StepAction.GIVE_BIRTH,
        JourneyEventKind.DEATH: StepAction.DIE,
    }
)


def journey_roles(journey: JourneyRow) -> list[tuple[int, IncidentRole]]:
    found = [
        (journey.traveller_entity_id, IncidentRole.ACTOR),
        (journey.origin_world_id, IncidentRole.ORIGIN),
        (journey.destination_world_id, IncidentRole.DESTINATION),
    ]
    if journey.vehicle_entity_id is not None:
        found.append((journey.vehicle_entity_id, IncidentRole.INSTRUMENT))
    return [(node, role) for node, role in found if node is not None]


async def journey_incident(ctx: TickContext, journey: JourneyRow) -> int:
    if journey.incident_id is None:
        await ctx.session.flush()
        journey.incident_id = await open_process(ctx, JOURNEY_KEY, ProcessClock.VOYAGE, journey_roles(journey))
    return journey.incident_id


async def journey_step(
    ctx: TickContext,
    journey: JourneyRow,
    action: StepAction,
    *,
    amount: int = 0,
    unit: FactUnit = FactUnit.PEOPLE,
    outcome: StepOutcome | None = None,
    target: int | None = None,
) -> IncidentStepRow:
    draft = StepDraft(
        action,
        actor=journey.traveller_entity_id,
        target=target,
        instrument_kind=InstrumentKind.VEHICLE if journey.vehicle_entity_id is not None else InstrumentKind.NONE,
        instrument_node=journey.vehicle_entity_id,
        amount=float(amount) if amount else None,
        unit=unit if amount else None,
        outcome=outcome,
        record_table=JourneyRow.__tablename__,
        record_key=str(journey.id),
    )
    rows = await append_steps(ctx, await journey_incident(ctx, journey), JOURNEY_KEY, ProcessClock.VOYAGE, [draft])
    return rows[0]
