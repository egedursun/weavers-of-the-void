from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.diets import DIETS
from aerona.domain.enums.ecology import Diet
from aerona.domain.enums.environment import ScarKind, TerrainKind
from aerona.engine.ecology.living_ways import keep_living_ways
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, tuned_rules
from tests.engine.core.living_kinds import kind, land, range_of, told


def test_fifteen_diets_and_the_four_new_ones_read_their_own_food() -> None:
    assert len(DIETS) == len(Diet) == 15
    assert DIETS[Diet.DECOMPOSER].eats_refuse and not DIETS[Diet.DECOMPOSER].yields_meat
    assert not DIETS[Diet.ENERGY].edible and not DIETS[Diet.CHEMOSYNTHETIC].hunts


async def test_parasites_drain_hosts_and_the_drain_is_told(session: AsyncSession, world: CoreWorld) -> None:
    region = world.regions[0]
    host = await kind(session, world, "Fed Grazer", region, 80, diet=Diet.HERBIVORE)
    await kind(session, world, "Blood Leech", region, 100, diet=Diet.PARASITE)
    tally = await keep_living_ways(await manual_context(session, "ecology"), set())
    assert (await range_of(session, host, region)).abundance < 80 and tally.drained == 1
    assert await told(session, "life.host_drained")


async def test_decomposers_turn_dead_ground_back_into_soil(session: AsyncSession, world: CoreWorld) -> None:
    region = world.regions[0]
    ground = await land(session, world, region, scars={ScarKind.BATTLEFIELD.value: 90}, soil_fertility=30)
    await kind(session, world, "Grave Mould", region, 100, diet=Diet.DECOMPOSER)
    tally = await keep_living_ways(await manual_context(session, "ecology", tuned_rules(diets={"decomposer_return_pct": 100})), set())
    assert ground.soil_fertility > 30 and tally.returned == 1


async def test_chemical_life_thins_away_from_vents_and_holds_on_volcanic_ground(session: AsyncSession, world: CoreWorld) -> None:
    dry, vented = world.regions[1], world.regions[2]
    await land(session, world, dry, dominant_terrain=TerrainKind.PLAIN)
    await land(session, world, vented, dominant_terrain=TerrainKind.VOLCANIC)
    lost = await kind(session, world, "Vent Mat", dry, 50, diet=Diet.CHEMOSYNTHETIC)
    kept = await kind(session, world, "Vent Tubes", vented, 50, diet=Diet.CHEMOSYNTHETIC)
    await keep_living_ways(await manual_context(session, "ecology", tuned_rules(diets={"chemosynthetic_vent_need": 50})), set())
    assert (await range_of(session, lost, dry)).abundance == 45
    assert (await range_of(session, kept, vented)).abundance == 50


async def test_feeders_on_power_draw_down_the_magic_of_their_land(session: AsyncSession, world: CoreWorld) -> None:
    region = world.regions[3]
    ground = await land(session, world, region, magic_density=60)
    await kind(session, world, "Spark Drinker", region, 100, diet=Diet.ENERGY)
    await keep_living_ways(await manual_context(session, "ecology", tuned_rules(diets={"energy_draw": 20})), set())
    assert ground.magic_density == 40
