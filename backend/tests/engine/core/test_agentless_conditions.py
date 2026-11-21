from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.agentless_conditions import AgentlessConditionRow
from aerona.db.tables.body import ConditionRow
from aerona.db.tables.body_systems import BodySystemRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.agentless_conditions import ConditionCause, ConditionCourse
from aerona.domain.enums.body import ConditionKind, HarmCause
from aerona.domain.enums.body_systems import BodySystem
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.engine.agentless_conditions.arise import ConditionTally, arise, roll_conditions
from aerona.engine.agentless_conditions.catalogue import SYSTEMS, seed_catalogue
from aerona.engine.agentless_conditions.course import tend_courses
from aerona.engine.economy.purse import points_of, shift_points
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import stat_or
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, bond, mortal, settlement, tuned_rules

QUIET = {
    "age_rate_pct": 0,
    "diet_rate_pct": 0,
    "exposure_rate_pct": 0,
    "heredity_weight_pct": 0,
    "strain_rate_pct": 0,
    "aftermath_rate_pct": 0,
    "unknown_rate_pct": 0,
}


def rules_with(**changes: int) -> Rules:
    return tuned_rules(agentless_conditions={**QUIET, "ease_pct": 0, "medicine_ease_pct": 0, "worsen_pct": 0, **changes})


async def homeland(session: AsyncSession, world: CoreWorld, name: str, prosperity: int = 50) -> EntityRow:
    town = await settlement(session, name, world, world.regions[0], prosperity=prosperity)
    await BondRepository(session).connect(BondDraft(world.people.id, town.id, BondKind.LIVES_IN, 0, role=BondRole.HOMELAND))
    return town


async def borne(session: AsyncSession, being: EntityRow) -> list[ConditionRow]:
    return list(await session.scalars(select(ConditionRow).where(ConditionRow.bearer_node_id == being.id, ConditionRow.ended_epoch.is_(None))))


async def test_every_world_gains_its_kinds_once_and_old_illness_with_no_sickness_gains_an_unknown_cause(session: AsyncSession, world: CoreWorld) -> None:
    town = await homeland(session, world, "Oldwell")
    elder = await mortal(session, "Grey Ash", world, town.id)
    session.add(ConditionRow(bearer_node_id=elder.id, kind=ConditionKind.CHRONIC_ILLNESS, severity=2, source=HarmCause.AGE, since_epoch=0))
    await session.flush()
    ctx = await manual_context(session, "seed", rules_with())
    assert await seed_catalogue(ctx) == len(ConditionCause) * len(SYSTEMS)
    assert await seed_catalogue(ctx) == 0
    kinds = await session.scalar(select(func.count(AgentlessConditionRow.id)).where(AgentlessConditionRow.world_id == world.world.id))
    assert kinds == len(ConditionCause) * len(SYSTEMS)
    assert [row.cause for row in await borne(session, elder)] == [ConditionCause.UNKNOWN]


async def test_age_and_want_bring_conditions_of_their_own_cause(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "worn", rules_with(age_rate_pct=100))
    await seed_catalogue(ctx)
    town = await homeland(session, world, "Agewick")
    elder = await mortal(session, "Old Moss", world, town.id, age=70, lifespan=70)
    tally = ConditionTally()
    await roll_conditions(ctx, tally)
    rows = await borne(session, elder)
    assert tally.arose >= 1 and rows and rows[0].cause is ConditionCause.AGE and rows[0].kind_id is not None
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "body.condition_arose")) is not None
    hungry = await manual_context(session, "want", rules_with(diet_rate_pct=100))
    poor = await homeland(session, world, "Wantby", prosperity=0)
    child = await mortal(session, "Thin Reed", world, poor.id, age=10)
    await roll_conditions(hungry, ConditionTally())
    assert [row.cause for row in await borne(session, child)] == [ConditionCause.DIET]


async def test_a_condition_of_a_parent_passes_to_a_child(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "line", rules_with(heredity_weight_pct=100))
    await seed_catalogue(ctx)
    town = await homeland(session, world, "Lineby")
    parent, child = await mortal(session, "Ama Line", world, town.id, age=40), await mortal(session, "Bo Line", world, town.id, age=10)
    await bond(session, parent.id, child.id, BondKind.PARENT_OF)
    line = await session.scalar(select(AgentlessConditionRow).where(AgentlessConditionRow.cause == ConditionCause.HEREDITY).limit(1))
    assert line is not None
    await arise(ctx, parent, line, ConditionTally())
    await roll_conditions(ctx, ConditionTally())
    assert [row.kind_id for row in await borne(session, child)] == [line.id]


async def test_a_worsening_condition_grows_heavier_costs_life_and_care_then_eases_away(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "course", rules_with(worsen_pct=100, lifespan_cost=2, care_cost=3))
    await seed_catalogue(ctx)
    town = await homeland(session, world, "Coursey")
    bearer = await mortal(session, "Hale Worn", world, town.id, age=30, lifespan=80)
    await shift_points(session, bearer, 50)
    kind = await session.scalar(select(AgentlessConditionRow).where(AgentlessConditionRow.course == ConditionCourse.WORSENING).limit(1))
    assert kind is not None
    row = await arise(ctx, bearer, kind, ConditionTally())
    tally = ConditionTally()
    await tend_courses(ctx, tally)
    assert tally.worsened == 1 and row.severity == 2 and stat_or(bearer, "lifespan", 0) == 76 and await points_of(session, bearer) == 44
    easing = await manual_context(session, "ease", rules_with(ease_pct=100))
    await tend_courses(easing, ConditionTally())
    await tend_courses(easing, ConditionTally())
    assert row.ended_epoch is not None
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "body.condition_healed")) is not None


async def test_a_people_without_a_body_bears_no_such_conditions(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "bodiless", rules_with(unknown_rate_pct=100))
    await seed_catalogue(ctx)
    for system in SYSTEMS:
        session.add(BodySystemRow(holder_entity_id=world.people.id, system=system, present=False, locked=[]))
    town = await homeland(session, world, "Nowhere")
    shade = await mortal(session, "Pale One", world, town.id)
    await roll_conditions(ctx, ConditionTally())
    assert await borne(session, shade) == []
    assert BodySystem.NONE not in SYSTEMS
