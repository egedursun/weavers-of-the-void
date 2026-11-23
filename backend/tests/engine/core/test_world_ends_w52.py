import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.cosmos import CAUSE_END, END_REMNANT, SOURCED_CAUSES
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.divine import BreachPointRow
from aerona.db.tables.evolution import WorldCycleRow
from aerona.db.tables.mass_weapons import MassWeaponRow
from aerona.db.tables.world_ends import WorldEndRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.evolution import PlanetaryCycle
from aerona.domain.enums.mass_weapons import MassReach
from aerona.domain.enums.outer import OuterFate
from aerona.domain.enums.world_end import WorldEnd, WorldEndCause
from aerona.domain.models.entity_stats import OuterBeingStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.world_end_control import declare_end
from aerona.engine.cosmos.world_ends import EndingTally, keep_world_ends
from aerona.engine.divine.outer import outer_profile
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, entity

CYCLE = next(iter(PlanetaryCycle))


async def at(session: AsyncSession, epoch: int) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "w52_world_ends")


async def ended(session: AsyncSession, world: CoreWorld) -> WorldEndRow:
    row = await session.get(WorldEndRow, world.world.id)
    assert row is not None
    return row


def test_every_new_end_leaves_its_remnant_and_only_war_and_hunger_name_a_source() -> None:
    assert set(END_REMNANT) == set(WorldEnd)
    assert CAUSE_END[WorldEndCause.OUTER_HUNGER] is WorldEnd.DEVOURED
    assert {WorldEndCause.WAR, WorldEndCause.OUTER_HUNGER} == SOURCED_CAUSES


@pytest.mark.parametrize(("sea", "state"), [(0.2, WorldEnd.BURNED), (1.0, WorldEnd.DROWNED)])
async def test_a_runaway_climate_burns_a_dry_world_and_drowns_a_wet_one(session: AsyncSession, world: CoreWorld, sea: float, state: WorldEnd) -> None:
    ctx = await at(session, 3)
    world.world.terrain_sea = sea
    session.add(WorldCycleRow(world_id=world.world.id, cycle=CYCLE, stock=ctx.rules.world_ends.runaway_stock, locked=[]))
    await session.flush()
    await keep_world_ends(ctx, EndingTally())
    row = await ended(session, world)
    assert row.state is state and row.cause is WorldEndCause.RUNAWAY_CLIMATE and row.source_node_id is None


async def test_a_war_of_world_weapons_unmakes_the_world_and_names_its_maker(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    for _ in range(ctx.rules.world_ends.war_weapons):
        session.add(MassWeaponRow(holder_entity_id=world.people.id, reach=MassReach.WORLD, used_epoch=3, count=1, seen_by=[], locked=[]))
    await session.flush()
    await keep_world_ends(ctx, EndingTally())
    row = await ended(session, world)
    assert row.state is WorldEnd.BURNED and row.cause is WorldEndCause.WAR and row.source_node_id == world.people.id


async def test_a_starving_outer_being_devours_the_world_it_breached(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    being = await entity(session, "The Long Want", EntityType.OUTER_BEING, OuterBeingStats(size=60, interest=50, influence=30), world_id=world.world.id)
    profile = await outer_profile(ctx, being)
    profile.fate, profile.reach, profile.unfed_epochs = OuterFate.ACTIVE, ctx.rules.world_ends.hunger_reach, ctx.rules.world_ends.hunger_unfed_epochs
    session.add(BreachPointRow(outer_entity_id=being.id, world_id=world.world.id, strength=40, opened_epoch=1, locked=[]))
    await session.flush()
    await keep_world_ends(ctx, EndingTally())
    row = await ended(session, world)
    assert row.state is WorldEnd.DEVOURED and row.cause is WorldEndCause.OUTER_HUNGER and row.source_node_id == being.id


async def test_a_declared_end_names_a_source_only_for_war_or_hunger(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    with pytest.raises(ValidationFailedError):
        await declare_end(ctx, world.world.id, WorldEnd.FROZEN_DEAD, WorldEndCause.STAR_DEATH, None, source_node_id=world.people.id)
    row = await declare_end(ctx, world.world.id, WorldEnd.BURNED, WorldEndCause.WAR, None, source_node_id=world.people.id)
    assert row.source_node_id == world.people.id
