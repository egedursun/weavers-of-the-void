from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.evolution import WET_LAND
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.industry import RegionPollutionRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.tables.water import CoastRow
from aerona.domain.enums.environment import CoastKind, RiverClass, ScarKind, SoilKind, TerrainKind
from aerona.domain.enums.evolution import SuccessionStage
from aerona.domain.enums.place import PlaceKind
from aerona.domain.enums.water import CoastForm
from aerona.engine.environment.w52_land import (
    COAST_FIXUP,
    PLACE_FIXUP,
    SCAR_FIXUP,
    SOIL_FIXUP,
    STAGE_FIXUP,
    backfill_coasts,
    backfill_landforms,
    backfill_scars,
    backfill_soils,
    backfill_stages,
)
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, seed_core_world, surveyed, tuned_rules

RULES = Rules()


async def lands(session: AsyncSession) -> tuple[CoreWorld, list[RegionEnvironmentRow]]:
    world = await seed_core_world(session)
    await surveyed(session, world)
    await session.execute(delete(AppliedFixupRow).where(AppliedFixupRow.key.in_([COAST_FIXUP, PLACE_FIXUP, SCAR_FIXUP, SOIL_FIXUP, STAGE_FIXUP])))
    found = [await session.get(RegionEnvironmentRow, region.id) for region in world.regions]
    return world, [land for land in found if land is not None]


async def test_heavy_pollution_leaves_poisoned_ground_once(session: AsyncSession) -> None:
    world, grounds = await lands(session)
    ctx = await manual_context(session, "test", RULES)
    grounds[0].scars = {}
    session.add(RegionPollutionRow(region_node_id=grounds[0].entity_id, air=0, water=RULES.scars.pollution_poison_threshold + 9, soil=0, epoch=0))
    await session.flush()
    assert await backfill_scars(ctx) == 1 and grounds[0].scars[ScarKind.POISONED.value] == 10
    assert await backfill_scars(ctx) == 0 and world.world.id


async def test_old_wet_and_bare_lands_take_their_new_stages(session: AsyncSession) -> None:
    world, grounds = await lands(session)
    ctx = await manual_context(session, "test", RULES)
    wet, bare = grounds[0], grounds[1]
    wet.succession, wet.wetland, wet.base_wetland, wet.locked = SuccessionStage.GRASSLAND, 90, WET_LAND, []
    bare.succession, bare.wetland, bare.base_wetland, bare.locked = SuccessionStage.BARE, 0, 0, []
    session.add(SpeciesRangeRow(species_entity_id=world.species.id, region_entity_id=bare.entity_id, abundance=40, locked=[]))
    await session.flush()
    assert await backfill_stages(ctx) >= 2
    assert wet.succession is SuccessionStage.OPEN_WATER and bare.succession is SuccessionStage.PIONEER
    assert await backfill_stages(ctx) == 0


async def test_old_coasts_take_their_derived_form_unless_held(session: AsyncSession) -> None:
    _, grounds = await lands(session)
    ctx = await manual_context(session, "test", RULES)
    free, kept = grounds[0], grounds[1]
    for land in (free, kept):
        land.coast_kind, land.river_class, land.dominant_terrain = CoastKind.BEACH, RiverClass.GREAT_RIVER, TerrainKind.COAST
    free_row = CoastRow(region_entity_id=free.entity_id, form=CoastForm.CLIFF, locked=[])
    kept_row = CoastRow(region_entity_id=kept.entity_id, form=CoastForm.CLIFF, locked=["form"])
    session.add_all([free_row, kept_row])
    await session.flush()
    assert await backfill_coasts(ctx) == 1
    assert free_row.form is CoastForm.ESTUARY and kept_row.form is CoastForm.CLIFF


async def test_old_lands_gain_the_landforms_their_terrain_allows(session: AsyncSession) -> None:
    _, grounds = await lands(session)
    for land in grounds:
        land.dominant_terrain = TerrainKind.PLAIN
    grounds[0].dominant_terrain = TerrainKind.KARST
    await session.flush()
    ctx = await manual_context(session, "test", tuned_rules(places={"landform_backfill_pct": 100}))
    assert await backfill_landforms(ctx) >= 1
    kinds = set(await session.scalars(select(PlaceProfileRow.kind)))
    assert PlaceKind.SINKHOLE in kinds
    assert await backfill_landforms(ctx) == 0


async def test_old_soils_drawn_from_the_land_take_the_new_kinds_once_and_laid_soils_stay(session: AsyncSession) -> None:
    _, grounds = await lands(session)
    ctx = await manual_context(session, "test", RULES)
    damp, laid, kept = grounds[0], grounds[1], grounds[2]
    between = RULES.environment.peat_wetland_pct * 3 // 4
    for ground, soil in ((damp, SoilKind.LOAM), (laid, SoilKind.VOLCANIC), (kept, SoilKind.LOAM)):
        ground.soil, ground.wetland, ground.locked = soil, between, []
    kept.locked = ["soil"]
    await session.flush()
    assert await backfill_soils(ctx) >= 1
    assert damp.soil is SoilKind.GLEY and laid.soil is SoilKind.VOLCANIC and kept.soil is SoilKind.LOAM
    assert await backfill_soils(ctx) == 0
