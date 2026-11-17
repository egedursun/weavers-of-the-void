from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import PlaceEnvironmentRow, RegionEnvironmentRow
from aerona.db.tables.happenings import EventFootprintRow, RegionGeomorphRow, RiverShiftRow
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.environment import RiverClass, ScarKind, SoilKind, TerrainKind, WaterSource
from aerona.domain.enums.happening import RiverShiftCause
from aerona.domain.enums.world import WorldType
from aerona.engine.context import TickContext
from aerona.engine.environment.profile import RIVER_RANK, Geography, natural_soil, soil_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.rules.registry import Rules

VOLCANIC_WORLDS = frozenset({WorldType.LAVA, WorldType.CHTHONIAN, WorldType.GREENHOUSE})
SALT_WORLDS = frozenset({WorldType.HYCEAN})
RANKED = sorted(RIVER_RANK, key=lambda river: RIVER_RANK[river])
DRY_LANDS = frozenset({TerrainKind.ICE_SHEET, TerrainKind.FLESH, TerrainKind.VOID_SHORE, TerrainKind.CRYSTAL_FIELD, TerrainKind.UNDERGROUND})
SHAPE_FIELDS = frozenset({"desertification", "desertified", "volcanic", "volcanic_pressure"})


def geography_of(env: RegionEnvironmentRow) -> Geography:
    return Geography(
        biome_mix=list(env.biome_mix),
        elevation_mean=env.elevation_mean,
        roughness=env.roughness,
        latitude=env.latitude,
        moisture=env.moisture,
        base_forest=env.base_forest,
        base_wetland=env.base_wetland,
        river_class=env.river_class,
    )


def is_volcanic(env: RegionEnvironmentRow, world_type: WorldType | None) -> bool:
    return env.dominant_terrain is TerrainKind.VOLCANIC or env.soil is SoilKind.VOLCANIC or world_type in VOLCANIC_WORLDS


def course_of(shapes: dict[int, RegionGeomorphRow], region_id: int) -> RiverClass | None:
    found = shapes.get(region_id)
    return found.river_course if found is not None else None


async def shapes_by_region(session: AsyncSession) -> dict[int, RegionGeomorphRow]:
    return {row.region_entity_id: row for row in await session.scalars(select(RegionGeomorphRow))}


async def shape_of(session: AsyncSession, region_id: int, world_id: int | None) -> RegionGeomorphRow:
    found = await session.get(RegionGeomorphRow, region_id)
    if found is not None:
        return found
    row = RegionGeomorphRow(
        region_entity_id=region_id,
        world_id=world_id,
        desertification=0,
        desertified=False,
        desert_since_epoch=None,
        river_course=None,
        course_changed_epoch=None,
        volcanic=False,
        volcanic_pressure=0,
        last_eruption_epoch=None,
        ash_since_epoch=None,
        locked=[],
    )
    session.add(row)
    await session.flush()
    return row


def desert_rainfall(rules: Rules, env: RegionEnvironmentRow, shape: RegionGeomorphRow | None) -> None:
    if shape is not None and shape.desertified and "rainfall" not in env.locked:
        env.rainfall = clamp_int(env.rainfall - rules.geomorphology.desert_rainfall_drop, 0, PERCENT)


def desert_terrain(env: RegionEnvironmentRow, shape: RegionGeomorphRow | None) -> None:
    if shape is not None and shape.desertified and "dominant_terrain" not in env.locked and env.dominant_terrain not in DRY_LANDS:
        env.dominant_terrain = TerrainKind.DESERT


def set_soil(rules: Rules, env: RegionEnvironmentRow, soil: SoilKind, *, base_drop: int = 0) -> bool:
    if "soil" in env.locked or env.soil is soil:
        return False
    env.soil = soil
    if "soil_base" not in env.locked:
        env.soil_base = clamp_int(natural_soil(rules, soil, env.moisture) - base_drop, 0, PERCENT)
    return True


def natural_soil_kind(rules: Rules, env: RegionEnvironmentRow, world_type: WorldType) -> SoilKind:
    return SoilKind.SALINE if world_type in SALT_WORLDS else soil_of(rules, geography_of(env), world_type, env.wetland)


async def land_line(ctx: TickContext, region: EntityRow | None, key: str, text: str, ids: list[int] | None = None) -> int | None:
    if region is None:
        return None
    written = await ctx.chronicle(
        ChronicleKind.CLIMATE,
        text,
        template_key=key,
        entity_ids=ids or [region.id],
        world_id=region.world_id,
        place_entity_id=region.id,
        feed_category=FeedCategory.WORLD,
    )
    return written.incident_id


async def droughts_now(ctx: TickContext) -> set[int]:
    statement = (
        select(EventFootprintRow.region_entity_id)
        .join(EntityRow, EntityRow.id == EventFootprintRow.event_entity_id)
        .where(EntityRow.entity_type == EntityType.EVENT, EntityRow.engine_kind == EngineKind.DROUGHT, EntityRow.birth_epoch == ctx.epoch)
    )
    return set(await ctx.session.scalars(statement))


async def desertify(ctx: TickContext, env: RegionEnvironmentRow, shape: RegionGeomorphRow, droughts: set[int]) -> str | None:
    table = ctx.rules.geomorphology
    if "desertification" not in shape.locked:
        dry = env.rainfall < table.desert_rainfall_below
        overgrazed = env.grazed > table.overgrazed_above
        if dry and overgrazed:
            gain = table.desertify_rate + (table.drought_desertify if env.entity_id in droughts else 0)
            shape.desertification = clamp_int(shape.desertification + gain, 0, PERCENT)
        elif not dry or not overgrazed:
            shape.desertification = clamp_int(shape.desertification - table.desert_recover_rate, 0, PERCENT)
    if "desertified" in shape.locked:
        return None
    if not shape.desertified and shape.desertification >= table.desertified_at:
        shape.desertified = True
        shape.desert_since_epoch = ctx.epoch
        set_soil(ctx.rules, env, SoilKind.SAND, base_drop=table.desert_soil_base_drop)
        return "land.desertified"
    if shape.desertified and shape.desertification < table.desert_recovered_below:
        shape.desertified = False
        shape.desert_since_epoch = None
        return "land.desert_retreat"
    return None


def salt_source(rules: Rules, env: RegionEnvironmentRow, shape: RegionGeomorphRow, world_type: WorldType | None) -> bool:
    table = rules.geomorphology
    salted = env.scars.get(ScarKind.MADE_BARREN.value, 0) >= table.salted_earth_salt_depth
    flat = shape.desertified and env.river_class is RiverClass.NONE and env.rainfall < table.salt_flat_rainfall_below
    return salted or flat or world_type in SALT_WORLDS


LINES = {
    "land.desertified": "The grass of {region} is gone; sand blows where the herds once grazed.",
    "land.desert_retreat": "Rest and rain have brought the grass back to {region}; the desert has drawn back.",
    "land.salted": "Salt has crept into the soil of {region}; little will grow there now.",
    "land.ash_weathered": "The ash that buried {region} has weathered into dark, rich soil.",
}


async def reshape(ctx: TickContext) -> Counter[str]:
    counts: Counter[str] = Counter()
    rules = ctx.rules
    table = rules.geomorphology
    worlds = {world_id: world_type for world_id, world_type in await ctx.session.execute(select(WorldRow.id, WorldRow.world_type))}
    shapes = await shapes_by_region(ctx.session)
    droughts = await droughts_now(ctx)
    for env in list(await ctx.session.scalars(select(RegionEnvironmentRow).order_by(RegionEnvironmentRow.entity_id))):
        region = await ctx.session.get(EntityRow, env.entity_id)
        if region is None or region.is_water:
            continue
        world_type = worlds.get(env.world_id)
        shape = shapes.get(env.entity_id) or await shape_of(ctx.session, env.entity_id, env.world_id)
        if "volcanic" not in shape.locked:
            shape.volcanic = is_volcanic(env, world_type)
        if "volcanic_pressure" not in shape.locked:
            shape.volcanic_pressure = clamp_int(shape.volcanic_pressure + table.volcanic_pressure_gain, 0, PERCENT) if shape.volcanic else 0
        turned = await desertify(ctx, env, shape, droughts)
        if turned == "land.desert_retreat" and env.soil is SoilKind.SAND and world_type is not None:
            set_soil(rules, env, natural_soil_kind(rules, env, world_type))
        salty = salt_source(rules, env, shape, world_type)
        if salty and set_soil(rules, env, SoilKind.SALINE):
            turned = turned or "land.salted"
        elif not salty and env.soil is SoilKind.SALINE and world_type is not None and natural_soil_kind(rules, env, world_type) is not SoilKind.SALINE:
            set_soil(rules, env, natural_soil_kind(rules, env, world_type))
        if env.soil is SoilKind.TEPHRA and shape.ash_since_epoch is None:
            shape.ash_since_epoch = ctx.epoch
        elif env.soil is SoilKind.TEPHRA and shape.ash_since_epoch is not None and ctx.epoch - shape.ash_since_epoch >= table.ash_weathering_epochs:
            if set_soil(rules, env, SoilKind.VOLCANIC):
                shape.ash_since_epoch = None
                await land_line(ctx, region, "land.ash_weathered", LINES["land.ash_weathered"].format(region=region.name))
                counts["ash_weathered"] += 1
        elif env.soil is not SoilKind.TEPHRA:
            shape.ash_since_epoch = None
        if turned is not None:
            await land_line(ctx, region, turned, LINES[turned].format(region=region.name))
            counts[turned.removeprefix("land.")] += 1
    await ctx.session.flush()
    return counts


def downhill(atlas: RegionAtlas, grounds: dict[int, RegionEnvironmentRow], source_id: int) -> list[int]:
    candidates = [region_id for region_id in atlas.neighbour_regions(source_id) if not atlas.is_water(region_id) and region_id in grounds]
    return sorted(candidates, key=lambda region_id: (grounds[region_id].elevation_mean, region_id))


def ranked_up(river: RiverClass, steps: int) -> RiverClass:
    return RANKED[clamp_int(RIVER_RANK[river] + steps, 0, len(RANKED) - 1)]


async def move_water(session: AsyncSession, source_id: int, target_id: int) -> int:
    moved = 0
    for place in list(await session.scalars(select(PlaceEnvironmentRow).where(PlaceEnvironmentRow.region_entity_id.in_([source_id, target_id])))):
        if "water_source" in place.locked:
            continue
        if place.region_entity_id == source_id and place.water_source is WaterSource.RIVER:
            place.water_source = WaterSource.WELL
            moved += 1
        elif place.region_entity_id == target_id and place.water_source in (WaterSource.NONE, WaterSource.WELL):
            place.water_source = WaterSource.RIVER
            moved += 1
    return moved


async def shift_river(
    ctx: TickContext,
    source_id: int,
    target_id: int | None,
    cause: RiverShiftCause,
    *,
    event_id: int | None = None,
    year: int | None = None,
) -> RiverShiftRow | None:
    source = await ctx.session.get(RegionEnvironmentRow, source_id)
    if source is None or RIVER_RANK[source.river_class] < RIVER_RANK[RiverClass.STREAM] or "river_class" in source.locked:
        return None
    atlas = await RegionAtlas.load(ctx.session)
    grounds = {row.entity_id: row for row in await ctx.session.scalars(select(RegionEnvironmentRow).where(RegionEnvironmentRow.world_id == source.world_id))}
    choices = downhill(atlas, grounds, source_id)
    chosen = target_id if target_id is not None else next((region_id for region_id in choices if "river_class" not in grounds[region_id].locked), None)
    target = grounds.get(chosen) if chosen is not None else None
    if target is None or target.entity_id == source_id or "river_class" in target.locked:
        return None
    river = source.river_class
    target.river_class = river if RIVER_RANK[river] > RIVER_RANK[target.river_class] else ranked_up(target.river_class, 1)
    source.river_class = RiverClass.STREAM if RIVER_RANK[river] > RIVER_RANK[RiverClass.STREAM] else RiverClass.NONE
    for ground, course in ((source, source.river_class), (target, target.river_class)):
        shape = await shape_of(ctx.session, ground.entity_id, ground.world_id)
        shape.river_course = course
        shape.course_changed_epoch = ctx.epoch
    await move_water(ctx.session, source_id, target.entity_id)
    origin = await ctx.session.get(EntityRow, source_id)
    destination = await ctx.session.get(EntityRow, target.entity_id)
    label = river.value.replace("_", " ")
    text = (
        f"The {label} of {origin.name if origin else 'the land'} broke its banks for good and found a new bed through "
        f"{destination.name if destination else 'the lowlands'}; old wells ran dry and new fields drank."
    )
    incident = await land_line(ctx, origin, "land.river_shift", text, [source_id, target.entity_id, *([event_id] if event_id is not None else [])])
    shift = RiverShiftRow(
        world_id=source.world_id,
        from_region_id=source_id,
        to_region_id=target.entity_id,
        epoch=ctx.epoch,
        year=year,
        river_class=river,
        cause=cause,
        event_entity_id=event_id,
        incident_id=incident,
    )
    ctx.session.add(shift)
    await ctx.session.flush()
    return shift


async def river_after_flood(ctx: TickContext, target: EntityRow, severity: int, event: EntityRow) -> RiverShiftRow | None:
    return await river_moved(ctx, target, severity, event, RiverShiftCause.FLOOD)


async def river_after_quake(ctx: TickContext, target: EntityRow, severity: int, event: EntityRow) -> RiverShiftRow | None:
    return await river_moved(ctx, target, severity, event, RiverShiftCause.QUAKE)


async def river_moved(ctx: TickContext, target: EntityRow, severity: int, event: EntityRow, cause: RiverShiftCause) -> RiverShiftRow | None:
    table = ctx.rules.geomorphology
    if severity < table.river_shift_severity:
        return None
    region_id = target.id if target.entity_type is EntityType.REGION else (await RegionAtlas.load(ctx.session)).top_region(target.id)
    ground = await ctx.session.get(RegionEnvironmentRow, region_id) if region_id is not None else None
    if ground is None or RIVER_RANK[ground.river_class] < RIVER_RANK[RiverClass.RIVER]:
        return None
    if not ctx.rng(f"river_shift.{event.id}").chance(table.river_shift_chance):
        return None
    return await shift_river(ctx, ground.entity_id, None, cause, event_id=event.id)


async def erupted(ctx: TickContext, target: EntityRow, severity: int) -> RegionGeomorphRow | None:
    region_id = target.id if target.entity_type is EntityType.REGION else (await RegionAtlas.load(ctx.session)).top_region(target.id)
    ground = await ctx.session.get(RegionEnvironmentRow, region_id) if region_id is not None else None
    if ground is None:
        return None
    shape = await shape_of(ctx.session, ground.entity_id, ground.world_id)
    if "volcanic_pressure" not in shape.locked:
        shape.volcanic_pressure = 0
    shape.last_eruption_epoch = ctx.epoch
    if set_soil(ctx.rules, ground, SoilKind.TEPHRA):
        shape.ash_since_epoch = ctx.epoch
    scars = dict(ground.scars)
    scars[ScarKind.BURNED.value] = clamp_int(
        scars.get(ScarKind.BURNED.value, 0) + severity * ctx.rules.geomorphology.eruption_burn_depth_pct // PERCENT, 0, PERCENT
    )
    ground.scars = scars
    return shape


async def quaked(ctx: TickContext, target: EntityRow) -> bool:
    region_id = target.id if target.entity_type is EntityType.REGION else (await RegionAtlas.load(ctx.session)).top_region(target.id)
    ground = await ctx.session.get(RegionEnvironmentRow, region_id) if region_id is not None else None
    if ground is None:
        return False
    shape = await shape_of(ctx.session, ground.entity_id, ground.world_id)
    if "volcanic_pressure" not in shape.locked:
        shape.volcanic_pressure = max(0, shape.volcanic_pressure - ctx.rules.geomorphology.volcanic_quake_relief)
    return ctx.rng(f"quake_wakes.{ground.entity_id}.{ctx.epoch}").chance(ctx.rules.geomorphology.volcanic_quake_eruption_chance)


def eruption_chance(rules: Rules, shape: RegionGeomorphRow | None) -> float:
    if shape is None or not shape.volcanic:
        return 0.0
    table = rules.geomorphology
    return float(table.eruption_base_chance + shape.volcanic_pressure * table.eruption_pressure_pct / PERCENT)
