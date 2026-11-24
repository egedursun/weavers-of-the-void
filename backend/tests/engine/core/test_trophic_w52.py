from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.evolution import trophic_level
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.domain.enums.ecology import Diet, SizeClass
from aerona.domain.enums.environment import TemperatureBand
from aerona.domain.enums.evolution import TrophicLevel
from aerona.engine.ecology.anatomy import by_cold
from aerona.engine.ecology.trophic import TrophicTally, decompose_dead
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, settlement, tuned_rules
from tests.engine.core.living_kinds import land, told


def levels(region_id: int, living: int, workers: int) -> dict[TrophicLevel, list[SpeciesRangeRow]]:
    return {
        TrophicLevel.HERBIVORE: [SpeciesRangeRow(species_entity_id=1, region_entity_id=region_id, abundance=living)],
        TrophicLevel.DECOMPOSER: [SpeciesRangeRow(species_entity_id=2, region_entity_id=region_id, abundance=workers)] if workers else [],
    }


def test_five_trophic_levels_and_decomposers_take_their_own() -> None:
    assert len(TrophicLevel) == 6
    assert trophic_level(Diet.DECOMPOSER, SizeClass.SMALL) is TrophicLevel.DECOMPOSER


async def test_decomposers_return_the_dead_to_the_soil_and_their_absence_stalls_decay(session: AsyncSession, world: CoreWorld) -> None:
    rich, barren = world.regions[0], world.regions[1]
    fed = await land(session, world, rich, soil_fertility=40, temperature_band=TemperatureBand.TEMPERATE)
    starved = await land(session, world, barren, soil_fertility=5, forest_cover=0, wetland=0, temperature_band=TemperatureBand.TEMPERATE)
    ctx = await manual_context(session, "trophic", tuned_rules(trophic={"decomposer_share_pct": 50, "decomposer_return_pct": 100}))
    await decompose_dead(ctx, rich.id, levels(rich.id, 100, 100), fed, TrophicTally())
    await decompose_dead(ctx, barren.id, levels(barren.id, 100, 0), starved, TrophicTally())
    assert fed.soil_fertility > 40 and starved.soil_fertility <= 5
    assert await told(session, "life.decay_stalled")


async def test_the_life_of_a_fertile_soil_breaks_down_the_dead_where_no_decomposer_is_known(session: AsyncSession, world: CoreWorld) -> None:
    ground = await land(session, world, world.regions[0], soil_fertility=60, temperature_band=TemperatureBand.TEMPERATE)
    ctx = await manual_context(session, "trophic", tuned_rules(trophic={"decomposer_share_pct": 10}))
    await decompose_dead(ctx, world.regions[0].id, levels(world.regions[0].id, 100, 0), ground, TrophicTally())
    assert ground.soil_fertility >= 60
    assert not await told(session, "life.decay_stalled")


async def test_cold_slows_the_work_of_decomposers(session: AsyncSession, world: CoreWorld) -> None:
    warm, frozen = world.regions[0], world.regions[1]
    mild = await land(session, world, warm, soil_fertility=40, temperature_band=TemperatureBand.TEMPERATE)
    icy = await land(session, world, frozen, soil_fertility=40, temperature_band=TemperatureBand.FROZEN)
    ctx = await manual_context(
        session, "trophic", tuned_rules(trophic={"decomposer_share_pct": 50, "decomposer_return_pct": 100, "decomposer_cold_cut_pct": 90})
    )
    await decompose_dead(ctx, warm.id, levels(warm.id, 100, 100), mild, TrophicTally())
    await decompose_dead(ctx, frozen.id, levels(frozen.id, 100, 100), icy, TrophicTally())
    assert mild.soil_fertility > icy.soil_fertility


async def test_a_frozen_land_wards_off_beasts_that_shun_the_cold(session: AsyncSession, world: CoreWorld) -> None:
    frozen, mild = world.regions[0], world.regions[1]
    await land(session, world, frozen, temperature_band=TemperatureBand.FROZEN)
    await land(session, world, mild, temperature_band=TemperatureBand.TEMPERATE)
    cold_town = await settlement(session, "Rime Town", world, frozen)
    warm_town = await settlement(session, "Sun Town", world, mild)
    ctx = await manual_context(session, "beasts", tuned_rules(aversions={"cold_ward_pct": 100}))
    atlas = await RegionAtlas.load(session)
    assert await by_cold(ctx, atlas, cold_town)
    assert not await by_cold(ctx, atlas, warm_town)
