from sqlalchemy import select

from aerona.catalog.evolution import WET_LAND
from aerona.catalog.soils import SOILS
from aerona.catalog.terrain import TERRAIN
from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.economy import ResourceProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.industry import RegionPollutionRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.tables.water import CoastRow
from aerona.db.write_guard import held
from aerona.domain.enums.environment import ScarKind
from aerona.domain.enums.evolution import SuccessionStage
from aerona.engine.context import TickContext
from aerona.engine.environment.book import add_scar
from aerona.engine.environment.geomorph import natural_soil_kind, set_soil
from aerona.engine.phases.geography import LANDFORMS, seed_place
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.water.ice import COAST_OF_KIND, coast_form

COAST_FIXUP = "coasts.w52_forms"
SCAR_FIXUP = "scars.w52_causes"
STAGE_FIXUP = "succession.w52_paths"
PLACE_FIXUP = "places.w52_derive"
SOIL_FIXUP = "soils.w52_rederive"
OPEN_WATER_WETLAND = 80


async def once(ctx: TickContext, key: str) -> bool:
    if await ctx.session.get(AppliedFixupRow, key) is not None:
        return False
    ctx.session.add(AppliedFixupRow(key=key, result={}))
    return True


async def backfill_scars(ctx: TickContext) -> int:
    if not await once(ctx, SCAR_FIXUP):
        return 0
    marked = 0
    threshold = ctx.rules.scars.pollution_poison_threshold
    for pollution in await ctx.session.scalars(select(RegionPollutionRow).order_by(RegionPollutionRow.region_node_id)):
        worst = max(pollution.air, pollution.water, pollution.soil)
        ground = await ctx.session.get(RegionEnvironmentRow, pollution.region_node_id)
        if ground is not None and worst >= threshold and not held(ground.entity_id):
            add_scar(ground, ScarKind.POISONED, worst - threshold + 1)
            marked += 1
    atlas = await RegionAtlas.load(ctx.session)
    spent = select(ResourceProfileRow.resource_entity_id).where(ResourceProfileRow.reserve <= 0, ResourceProfileRow.regeneration <= 0)
    for resource_id in await ctx.session.scalars(spent.order_by(ResourceProfileRow.resource_entity_id)):
        region_id = atlas.top_region(resource_id)
        ground = await ctx.session.get(RegionEnvironmentRow, region_id) if region_id is not None else None
        if ground is not None and not held(ground.entity_id):
            add_scar(ground, ScarKind.MINED_OUT, PERCENT // 2)
            marked += 1
    return marked


async def backfill_stages(ctx: TickContext) -> int:
    if not await once(ctx, STAGE_FIXUP):
        return 0
    living = set(await ctx.session.scalars(select(SpeciesRangeRow.region_entity_id).where(SpeciesRangeRow.abundance > 0)))
    moved = 0
    for ground in await ctx.session.scalars(select(RegionEnvironmentRow).order_by(RegionEnvironmentRow.entity_id)):
        if held(ground.entity_id) or "succession" in ground.locked:
            continue
        if ground.wetland >= OPEN_WATER_WETLAND and ground.base_wetland >= WET_LAND and ground.succession in (SuccessionStage.BARE, SuccessionStage.GRASSLAND):
            ground.succession = SuccessionStage.OPEN_WATER
            moved += 1
        elif ground.succession is SuccessionStage.BARE and ground.entity_id in living:
            ground.succession = SuccessionStage.PIONEER
            moved += 1
    return moved


async def backfill_soils(ctx: TickContext) -> int:
    if not await once(ctx, SOIL_FIXUP):
        return 0
    worlds = {row.id: row.world_type for row in await ctx.session.scalars(select(WorldRow).order_by(WorldRow.id))}
    water = set(await ctx.session.scalars(select(EntityRow.id).where(EntityRow.is_water.is_(True))))
    drawn = 0
    for ground in list(await ctx.session.scalars(select(RegionEnvironmentRow).order_by(RegionEnvironmentRow.entity_id))):
        world_type = worlds.get(ground.world_id)
        if world_type is None or ground.entity_id in water or held(ground.entity_id) or not SOILS[ground.soil].drawn:
            continue
        natural = natural_soil_kind(ctx.rules, ground, world_type)
        if SOILS[natural].drawn and set_soil(ctx.rules, ground, natural):
            drawn += 1
    return drawn


async def backfill_coasts(ctx: TickContext) -> int:
    if not await once(ctx, COAST_FIXUP):
        return 0
    reformed = 0
    for row in list(await ctx.session.scalars(select(CoastRow).order_by(CoastRow.region_entity_id))):
        land = await ctx.session.get(RegionEnvironmentRow, row.region_entity_id)
        if land is None or held(land.entity_id) or "form" in row.locked or land.coast_kind not in COAST_OF_KIND:
            continue
        form = coast_form(land)
        if form is not row.form:
            row.form = form
            reformed += 1
    return reformed


async def backfill_landforms(ctx: TickContext) -> int:
    if not await once(ctx, PLACE_FIXUP):
        return 0
    atlas = await RegionAtlas.load(ctx.session)
    kinds_here: dict[int, set[str]] = {}
    for place_id, kind in await ctx.session.execute(select(PlaceProfileRow.entity_id, PlaceProfileRow.kind).order_by(PlaceProfileRow.entity_id)):
        region_id = atlas.top_region(place_id)
        if region_id is not None:
            kinds_here.setdefault(region_id, set()).add(kind.value)
    seeded = 0
    for ground in list(await ctx.session.scalars(select(RegionEnvironmentRow).order_by(RegionEnvironmentRow.entity_id))):
        region = await ctx.session.get(EntityRow, ground.entity_id)
        if region is None or held(region.id):
            continue
        fitting = [
            nature
            for nature in LANDFORMS
            if nature.subtype in TERRAIN[ground.dominant_terrain].natures and nature.kind.value not in kinds_here.get(region.id, set())
        ]
        if fitting and ctx.rng(f"landform.{region.id}").chance(ctx.rules.places.landform_backfill_pct):
            await seed_place(ctx, region, move=False, nature=fitting[0])
            seeded += 1
    return seeded
