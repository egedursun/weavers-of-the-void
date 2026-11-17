from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.incident_kinds import g10_movement, g11_social
from aerona.db.tables.households import HouseholdRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.records import IncidentFactRow, IncidentStepRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.genetics import HouseholdDecision
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, StepAction
from aerona.domain.enums.travel import JourneyEventKind, JourneyIntent, TravelMethod
from aerona.domain.models.entity_stats import MortalStats, PeopleStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.journey_record import JOURNEY_KEY
from aerona.engine.cosmos.routes import JourneySpec, add_event, start_journey
from aerona.engine.households.life import HouseholdTally, decided
from tests.engine.cosmos.factories import Cosmos, make_entity, make_route, make_world


async def roles_of(session: AsyncSession, incident_id: int) -> dict[IncidentRole, set[int]]:
    found: dict[IncidentRole, set[int]] = {}
    for row in await session.scalars(select(IncidentParticipantRow).where(IncidentParticipantRow.incident_id == incident_id)):
        found.setdefault(row.role, set()).add(row.node_id)
    return found


async def facts_of(session: AsyncSession, incident_id: int) -> dict[str, IncidentFactRow]:
    return {row.key: row for row in await session.scalars(select(IncidentFactRow).where(IncidentFactRow.incident_id == incident_id))}


def test_every_kind_of_movement_and_social_life_is_a_real_kind_with_typed_facts() -> None:
    kinds = [*g10_movement.KINDS, *g11_social.KINDS]
    assert kinds and not [spec.key for spec in kinds if spec.draft]
    assert not [(spec.key, fact.key) for spec in kinds for fact in spec.facts if fact.value.value == "number" and fact.unit is None]
    assert not [spec.key for spec in kinds if spec.told and not spec.template]
    assert not [spec.key for spec in kinds if spec.told and not spec.roles]


async def test_a_journey_is_one_incident_whose_events_are_its_steps(ctx: TickContext, cosmos: Cosmos) -> None:
    other = await make_world(ctx.session, "Velmor")
    people = await make_entity(ctx.session, "Tarn", EntityType.PEOPLE, PeopleStats(population=5000), world_id=cosmos.home.id)
    gate = await make_route(ctx.session, cosmos.home.id, other.id, TravelMethod.ANCIENT_GATE, duration=1)
    journey = await start_journey(ctx, JourneySpec(people, gate, JourneyIntent.COLONY, 1000))
    assert journey.incident_id is not None
    incident = await ctx.session.get(IncidentRow, journey.incident_id)
    assert incident is not None and incident.kind == JOURNEY_KEY
    await add_event(ctx, journey, JourneyEventKind.LOST_WAY, "lost", loss=12)
    steps = list(
        await ctx.session.scalars(select(IncidentStepRow).where(IncidentStepRow.incident_id == journey.incident_id).order_by(IncidentStepRow.position))
    )
    assert steps[0].action is StepAction.DEPART
    assert steps[-1].action is StepAction.LOSE_WAY and steps[-1].amount == 12
    assert [step.position for step in steps] == sorted({step.position for step in steps})
    assert len(steps) == 1 + len(journey.events)


async def test_a_household_decision_names_the_head_and_keeps_the_typed_choice(ctx: TickContext, cosmos: Cosmos) -> None:
    head = await make_entity(ctx.session, "Orra", EntityType.MORTAL, MortalStats(age=40), world_id=cosmos.home.id)
    household = HouseholdRow(name="Household of Orra", head_node_id=head.id, wealth=30, servants=1, formed_epoch=ctx.epoch, locked=[])
    ctx.session.add(household)
    await ctx.session.flush()
    assert await decided(ctx, household, HouseholdDecision.HIRE_SERVANT, amount=household.servants, tally=HouseholdTally())
    incident = await ctx.session.scalar(select(IncidentRow).where(IncidentRow.kind == "households.hire_servant").order_by(IncidentRow.id.desc()).limit(1))
    assert incident is not None
    assert (await roles_of(ctx.session, incident.id))[IncidentRole.ACTOR] == {head.id}
    facts = await facts_of(ctx.session, incident.id)
    assert facts["decision"].enum_value == HouseholdDecision.HIRE_SERVANT.value
    assert facts["wealth"].number == 30 and facts["wealth"].unit is FactUnit.WEALTH_POINTS
    assert facts["household"].name == "Household of Orra"
