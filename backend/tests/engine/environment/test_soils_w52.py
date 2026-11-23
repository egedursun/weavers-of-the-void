from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.cartography.biomes import Biome
from aerona.catalog.soils import SOILS
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.agrarian import NutrientKind
from aerona.domain.enums.environment import RiverClass, ScarKind, SoilKind
from aerona.domain.enums.world import WorldType
from aerona.engine.agrarian.soil import FieldWork, nutrient_change
from aerona.engine.environment.profile import Geography, soil_of
from aerona.engine.environment.soil_life import live_soils
from aerona.engine.phases.environment import land_use
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import seed_core_world, surveyed, tuned_rules

RULES = Rules()
S = SoilKind


def geography(biome: Biome = Biome.MID_LOWLAND, *, moisture: int = 50, latitude: int = 30, forest: int = 0, river: RiverClass = RiverClass.NONE) -> Geography:
    mix = [0] * len(Biome)
    mix[biome] = 100
    return Geography(mix, 30, 20, latitude, moisture, forest, 0, river)


def test_every_soil_reads_its_values_from_the_catalogue() -> None:
    assert set(SOILS) == set(SoilKind)
    assert SOILS[S.HUMIC].fertility(RULES) > SOILS[S.LEACHED].fertility(RULES)
    assert SOILS[S.SILT].workability(RULES) == RULES.soils.silt_workability


def test_the_new_soils_form_where_their_rule_holds() -> None:
    assert soil_of(RULES, geography(Biome.DRY_LOWLAND, moisture=40), WorldType.ORDINARY, 0) is S.HUMIC
    assert soil_of(RULES, geography(forest=80, latitude=70), WorldType.ORDINARY, 0) is S.LEACHED
    assert soil_of(RULES, geography(river=RiverClass.GREAT_RIVER), WorldType.ORDINARY, 0) is S.SILT
    assert soil_of(RULES, geography(), WorldType.ORDINARY, 0) is S.LOAM


async def test_leached_soil_gains_most_from_manure(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    ctx = await manual_context(session, "test", RULES)
    work = FieldWork(set(), set(), {}, set(), {}, {})

    def change(soil: SoilKind) -> float:
        land = RegionEnvironmentRow(entity_id=1, soil=soil, soil_base=50, farmed=0, grazed=50, cleared=50, erosion=0, forest_cover=0)
        return nutrient_change(ctx, land, NutrientKind.ORGANIC, 50, work)

    assert world.world.id
    assert change(S.LEACHED) - change(S.LOAM) == 50 * RULES.soils.leached_amend_gain / 100


async def test_cleared_silt_blows_and_washes_away(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    await surveyed(session, world)
    ctx = await manual_context(session, "test", tuned_rules(soils={"silt_erosion_pct": 100}))
    land = await session.get(RegionEnvironmentRow, world.regions[0].id)
    assert land is not None
    land.soil, land.cleared, land.scars, land.locked = S.SILT, 100, {}, []
    await live_soils(ctx, land, None)
    assert land.scars.get(ScarKind.ERODED.value, 0) >= 50
    assert "soil.eroded" in set(await session.scalars(select(IncidentRow.kind)))


async def test_ploughed_humic_soil_loses_fertility_fastest(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    await surveyed(session, world)
    ctx = await manual_context(session, "test", tuned_rules(soils={"humic_exhaustion_pct": 50}))
    lands = [await session.get(RegionEnvironmentRow, region.id) for region in world.regions[:2]]
    for land, soil in zip(lands, (S.HUMIC, S.LOAM), strict=True):
        assert land is not None
        land.soil, land.farmed, land.erosion, land.soil_fertility = soil, 100, 0, 80
        land.locked = ["farmed", "grazed", "cleared", "erosion"]
    await session.flush()
    await land_use(ctx)
    humic, loam = (80 - land.soil_fertility for land in lands if land is not None)
    assert humic > loam > 0
