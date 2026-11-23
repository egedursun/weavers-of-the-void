from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.nature_kinds50 import SEDIMENTS
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.geology import RegionGeologyRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.water import CoastRow, SedimentFlowRow
from aerona.domain.enums.environment import CoastKind, RiverClass, SoilKind, TerrainKind
from aerona.domain.enums.geology import RockKind
from aerona.domain.enums.water import CoastForm, SedimentCarrier, SedimentKind
from aerona.engine.environment.geology import lay_columns
from aerona.engine.primitives.manual import manual_context
from aerona.engine.water.ice import WaterTally, keep_water, lay_soils, sediment_kind
from aerona.rules.registry import Rules
from tests.engine.core.factories import seed_core_world, surveyed, tuned_rules

RULES = Rules()
K = SedimentKind


def land(terrain: TerrainKind = TerrainKind.PLAIN, *, coast: CoastKind = CoastKind.NONE, temperature: int = 50, wetland: int = 0) -> RegionEnvironmentRow:
    return RegionEnvironmentRow(dominant_terrain=terrain, coast_kind=coast, temperature=temperature, wetland=wetland, locked=[])


def test_each_new_sediment_lays_where_its_waters_lie() -> None:
    assert sediment_kind(land(TerrainKind.DESERT), land(), SedimentCarrier.RIVER) is K.EVAPORITE
    assert sediment_kind(land(), land(coast=CoastKind.REEF), SedimentCarrier.WAVE) is K.CARBONATE
    assert sediment_kind(land(), land(temperature=90), SedimentCarrier.WAVE) is K.CARBONATE
    assert sediment_kind(land(), land(wetland=80), SedimentCarrier.RIVER) is K.CLAY
    assert sediment_kind(land(), land(), SedimentCarrier.RIVER) is not K.CLAY
    assert (SEDIMENTS[K.CLAY].soil, SEDIMENTS[K.CARBONATE].soil, SEDIMENTS[K.EVAPORITE].soil) == (SoilKind.CLAY, SoilKind.CALCAREOUS, SoilKind.SALINE)
    assert (SEDIMENTS[K.CLAY].rock, SEDIMENTS[K.CARBONATE].rock, SEDIMENTS[K.EVAPORITE].rock) == (RockKind.SHALE, RockKind.LIMESTONE, RockKind.HALITE)


async def test_a_heavy_load_lays_its_soil_and_dry_irrigated_fields_turn_salt(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    await surveyed(session, world)
    ctx = await manual_context(session, "test", tuned_rules(sediment={"soil_lay_pct": 100, "salt_irrigation_pct": 100}))
    lands = {row.entity_id: row for row in await session.scalars(select(RegionEnvironmentRow).where(RegionEnvironmentRow.world_id == world.world.id))}
    sink, dry = world.regions[0].id, world.regions[1].id
    lands[sink].soil = SoilKind.LOAM
    lands[dry].dominant_terrain, lands[dry].farmed, lands[dry].river_class, lands[dry].soil = TerrainKind.DESERT, 40, RiverClass.RIVER, SoilKind.SAND
    flows = [
        SedimentFlowRow(source_region_id=dry, sink_region_id=sink, carrier=SedimentCarrier.RIVER, kind=K.CLAY, load=RULES.sediment.soil_lay_load, locked=[])
    ]
    laid = await lay_soils(ctx, lands, flows)
    assert laid >= 2 and lands[sink].soil is SoilKind.CLAY and lands[dry].soil is SoilKind.SALINE
    assert "land.sediment_laid" in set(await session.scalars(select(IncidentRow.kind)))


async def test_a_fine_sediment_fills_a_harbour_faster_and_old_sediment_becomes_rock(session: AsyncSession) -> None:
    assert SEDIMENTS[K.CLAY].fill(RULES) > SEDIMENTS[K.GRAVEL].fill(RULES)
    world = await seed_core_world(session)
    await surveyed(session, world)
    ctx = await manual_context(session, "test", RULES)
    sink, source = world.regions[0].id, world.regions[1].id
    session.add(CoastRow(region_entity_id=sink, form=CoastForm.LAGOON, harbour_silting=0, locked=["rate", "progress"]))
    session.add(SedimentFlowRow(source_region_id=source, sink_region_id=sink, carrier=SedimentCarrier.RIVER, kind=K.CLAY, load=60, locked=[]))
    await session.flush()
    await keep_water(ctx, WaterTally())
    coast = await session.get(CoastRow, sink)
    assert coast is not None and coast.harbour_silting > 0
    await lay_columns(ctx)
    rocks = list(await session.scalars(select(RegionGeologyRow.rock).where(RegionGeologyRow.region_entity_id == sink).order_by(RegionGeologyRow.depth_order)))
    assert rocks[0] is RockKind.SOIL and RockKind.SHALE in rocks[1:3]
