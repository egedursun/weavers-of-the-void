from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.anatomy import CreatureAnatomyRow
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.ecology import Aversion, BeastTemper, Biochemistry, Habitat, Temperament
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import TemperatureBand, TerrainKind
from aerona.domain.models.entity_stats import BeastStats
from aerona.engine.ecology.anatomy import WARDS, habitat_of, repelled
from aerona.engine.ecology.beast_ways import habitat_ways
from aerona.engine.ecology.beasts import pick_prey
from aerona.engine.ecology.contracts import reachable
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement, surveyed, tuned_rules


async def beast_of(session: AsyncSession, world: CoreWorld, name: str, **anatomy: object) -> tuple[EntityRow, BeastProfileRow, CreatureAnatomyRow]:
    region = world.regions[0]
    beast = await entity(session, name, EntityType.BEAST, BeastStats(hp=200), world_id=world.world.id, location_id=region.id)
    row = BeastProfileRow(beast_entity_id=beast.id, endurance=50, lair_place_id=region.id, temper=BeastTemper.HUNGRY, locked=[])
    shape = CreatureAnatomyRow(node_id=beast.id, locked=[], **anatomy)
    session.add_all([row, shape])
    await session.flush()
    return beast, row, shape


async def ground_of(session: AsyncSession, world: CoreWorld) -> RegionEnvironmentRow:
    await surveyed(session, world)
    ground = await session.get(RegionEnvironmentRow, world.regions[0].id)
    assert ground is not None
    return ground


def test_spirit_bodies_live_in_the_spirit_realms_and_deep_stone_bodies_in_the_magma() -> None:
    assert habitat_of(BodyPlan.AMORPHOUS, set(), Biochemistry.SPIRIT, deep=False) is Habitat.ETHEREAL
    assert habitat_of(BodyPlan.COLOSSAL, set(), Biochemistry.SILICON, deep=True) is Habitat.MAGMA
    assert habitat_of(BodyPlan.COLOSSAL, set(), Biochemistry.SILICON, deep=False) is Habitat.LAND
    assert set(WARDS) == set(Aversion)


async def test_a_magma_beast_surfaces_from_burning_ground_and_a_spirit_beast_crosses_over(session: AsyncSession, world: CoreWorld) -> None:
    ground = await ground_of(session, world)
    ground.dominant_terrain = TerrainKind.VOLCANIC
    ctx = await manual_context(session, "test", tuned_rules(habitats={"magma_surface_pct": 100, "ethereal_cross_pct": 100}))
    magma, magma_row, magma_shape = await beast_of(session, world, "Cinder Wyrm", habitat=Habitat.MAGMA)
    assert await habitat_ways(ctx, magma, magma_row, magma_shape, world.regions[0].id)
    ghost, ghost_row, ghost_shape = await beast_of(session, world, "Pale Drift", habitat=Habitat.ETHEREAL)
    assert await habitat_ways(ctx, ghost, ghost_row, ghost_shape, world.regions[0].id)
    await session.flush()
    assert {"beast.surfaced", "beast.crossed_over"} <= set(await session.scalars(select(IncidentRow.kind)))


async def test_a_spirit_beast_is_harder_to_reach_than_a_land_beast(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test")
    hunter = await mortal(session, "Dagny", world, world.regions[0].id)
    ghost, _row, _shape = await beast_of(session, world, "Grey Drift", habitat=Habitat.ETHEREAL)
    walker, _row2, _shape2 = await beast_of(session, world, "Grey Stag", habitat=Habitat.LAND)
    assert await reachable(ctx, hunter, ghost) < await reachable(ctx, hunter, walker) == 1.0


async def test_a_frozen_town_keeps_off_a_beast_that_hates_the_cold_and_drives_it_off(session: AsyncSession, world: CoreWorld) -> None:
    ground = await ground_of(session, world)
    ground.temperature_band = TemperatureBand.FROZEN
    ctx = await manual_context(session, "test", tuned_rules(aversions={"cold_ward_pct": 100, "light_ward_pct": 100}))
    town = await settlement(session, "Rimehold", world, world.regions[0], population=8000)
    atlas = await RegionAtlas.load(session)
    assert await repelled(ctx, atlas, town, Aversion.COLD)
    assert await repelled(ctx, atlas, town, Aversion.LIGHT)
    assert not await repelled(ctx, atlas, town, None)
    beast, row, _shape = await beast_of(session, world, "Ash Hound", hates=Aversion.COLD, temperament=Temperament.FIERCE)
    assert await pick_prey(ctx, beast, [town], None) is None
    assert row.temper is BeastTemper.COWED
    await session.flush()
    assert "beast.driven_off" in set(await session.scalars(select(IncidentRow.kind)))
