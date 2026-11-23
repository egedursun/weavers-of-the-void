from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.cartography.biomes import Biome
from aerona.catalog.terrain import TERRAIN
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.records import IncidentFactRow
from aerona.domain.enums.environment import MovementMode, RiverClass, SoilKind, TerrainKind, TerrainTrait
from aerona.domain.enums.world import WorldType
from aerona.engine.environment.profile import Geography, Surroundings, TerrainReading, terrain_of
from aerona.engine.phases.environment import environment_derive
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import seed_core_world, surveyed

RULES = Rules()
T = TerrainKind


def reading(
    biome: Biome = Biome.MID_LOWLAND,
    *,
    temperature: int = 50,
    rainfall: int = 50,
    wetland: int = 0,
    forest: int = 0,
    soil: SoilKind | None = None,
    coastal: bool = False,
    airless: bool = False,
    gaseous: bool = False,
) -> TerrainReading:
    mix = [0] * len(Biome)
    mix[biome] = 100
    geography = Geography(mix, 30, 20, 40, rainfall, forest, wetland, RiverClass.NONE)
    world = Surroundings(world_type=WorldType.ORDINARY, era=None, coastal=coastal, highland=False, airless=airless, gaseous=gaseous)
    return TerrainReading(geography, world, temperature, rainfall, wetland, 0, soil)


def test_every_terrain_has_traits_and_a_passage_for_every_mode() -> None:
    assert set(TERRAIN) == set(TerrainKind)
    for spec in TERRAIN.values():
        assert spec.traits and set(spec.passage(RULES)) == set(MovementMode)


def test_the_new_terrains_carry_the_traits_their_readers_test() -> None:
    assert {TerrainTrait.WOODED, TerrainTrait.COLD} <= TERRAIN[T.TAIGA].traits
    assert {TerrainTrait.WOODED, TerrainTrait.COASTAL, TerrainTrait.WET} <= TERRAIN[T.MANGROVE].traits
    assert TerrainTrait.UNDERGROUND in TERRAIN[T.KARST].traits and TerrainTrait.AIRLESS in TERRAIN[T.REGOLITH_PLAIN].traits
    assert TerrainTrait.GASEOUS in TERRAIN[T.CLOUD_DECK].traits and TerrainTrait.ARID in TERRAIN[T.EVAPORITE_FLAT].traits


def test_each_new_terrain_is_derived_where_its_rule_holds() -> None:
    cold = RULES.weather.cold_threshold
    assert terrain_of(RULES, reading(temperature=cold - 5, forest=80)) is T.TAIGA
    assert terrain_of(RULES, reading(temperature=cold + 20, forest=80)) is T.FOREST
    assert terrain_of(RULES, reading(Biome.DRY_LOWLAND, temperature=70, rainfall=30)) is T.SAVANNA
    assert terrain_of(RULES, reading(temperature=70, wetland=60, coastal=True)) is T.MANGROVE
    assert terrain_of(RULES, reading(temperature=70, wetland=60)) is T.MARSH
    assert terrain_of(RULES, reading(temperature=60, rainfall=10, soil=SoilKind.SALINE)) is T.EVAPORITE_FLAT
    assert terrain_of(RULES, reading(temperature=60, rainfall=10)) is T.DESERT
    assert terrain_of(RULES, reading(Biome.DRY_HILLS, rainfall=60, soil=SoilKind.CALCAREOUS)) is T.KARST
    assert terrain_of(RULES, reading(Biome.DRY_HILLS, rainfall=60)) is T.HILLS
    assert terrain_of(RULES, reading(airless=True)) is T.REGOLITH_PLAIN
    assert terrain_of(RULES, reading(gaseous=True)) is T.CLOUD_DECK


async def test_a_region_whose_terrain_is_derived_anew_records_the_change(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    await surveyed(session, world)
    land = await session.get(RegionEnvironmentRow, world.regions[0].id)
    assert land is not None
    land.dominant_terrain = T.REGOLITH_PLAIN
    await session.flush()
    await environment_derive(await manual_context(session, "test", RULES))
    assert land.dominant_terrain is not T.REGOLITH_PLAIN
    told = await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "terrain.changed").order_by(IncidentRow.id))
    assert told is not None
    facts = {row.key: row.enum_value for row in await session.scalars(select(IncidentFactRow).where(IncidentFactRow.incident_id == told))}
    assert facts == {"before": T.REGOLITH_PLAIN.value, "after": land.dominant_terrain.value}
