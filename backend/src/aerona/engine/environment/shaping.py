from enum import StrEnum

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.physics import WorldPhysicsRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import SOCIETY_TYPES
from aerona.domain.enums.environment import CoastKind, RiverClass, SoilKind
from aerona.domain.enums.happening import LandAct, RiverShiftCause
from aerona.domain.enums.intervention import Disaster
from aerona.engine.context import TickContext
from aerona.engine.divine.standing import standing_row
from aerona.engine.environment.geomorph import downhill, erupted, ranked_up, set_soil, shape_of, shift_river
from aerona.engine.environment.succession import burn_back
from aerona.engine.phases.disasters import apply_disaster
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import canon
from aerona.rules.registry import Rules

A = LandAct
FEARED = frozenset({A.CALL_LAVA, A.SINK_COAST, A.PARCH, A.SALT_SOIL})
WELCOMED = frozenset({A.RAISE_LAND, A.OPEN_SPRING, A.GREEN, A.ENRICH_SOIL})


class LandOutcome(StrEnum):
    DONE = "done"
    NO_RIVER = "no_river"
    UNCHANGED = "unchanged"
    NO_COAST = "no_coast"


def hold_value(ground: RegionEnvironmentRow, key: str, value: int | RiverClass | CoastKind) -> bool:
    if getattr(ground, key) == value:
        return False
    setattr(ground, key, value)
    if key not in ground.locked:
        ground.locked = [*ground.locked, key]
    return True


async def awe_of_folk(ctx: TickContext, region_id: int, god_id: int, act: LandAct) -> int:
    table = ctx.rules.land_shaping
    shift = -table.awe_loss if act in FEARED else table.awe_gain if act in WELCOMED else 0
    if not shift:
        return 0
    atlas = await RegionAtlas.load(ctx.session)
    moved = 0
    for community in await canon(ctx.session, SOCIETY_TYPES):
        if atlas.top_region(community.id) != region_id or held(community.id, god_id):
            continue
        row = await standing_row(ctx, community.id, god_id)
        if "awe" not in row.locked:
            row.awe = clamp_int(row.awe + shift, 0, PERCENT)
        if act in FEARED and "fear" not in row.locked:
            row.fear = clamp_int(row.fear + table.awe_loss, 0, PERCENT)
        row.epoch = ctx.epoch
        moved += 1
    return moved


def lift(ground: RegionEnvironmentRow, act: LandAct, step: int) -> bool:
    if act is A.RAISE_LAND:
        return hold_value(ground, "elevation_mean", clamp_int(ground.elevation_mean + step, 0, PERCENT))
    if act is A.LOWER_LAND:
        return hold_value(ground, "elevation_mean", clamp_int(ground.elevation_mean - step, 0, PERCENT))
    if act is A.CARVE_VALLEY:
        deeper = hold_value(ground, "roughness", clamp_int(ground.roughness + step, 0, PERCENT))
        return hold_value(ground, "river_class", ranked_up(ground.river_class, 1)) or deeper
    return hold_value(ground, "roughness", clamp_int(ground.roughness - step, 0, PERCENT))


SOIL_ACTS = frozenset({A.SHIFT_RIVER, A.PARCH, A.GREEN, A.SALT_SOIL, A.ENRICH_SOIL})
LIFTS = frozenset({A.RAISE_LAND, A.LOWER_LAND, A.CARVE_VALLEY, A.FILL_VALLEY})


async def work_soil(
    ctx: TickContext, region: EntityRow, ground: RegionEnvironmentRow, act: LandAct, *, fiery: bool, target_region_id: int | None
) -> LandOutcome:
    geomorph = ctx.rules.geomorphology
    if act is A.SHIFT_RIVER:
        moved = await shift_river(ctx, region.id, target_region_id, RiverShiftCause.DIVINE)
        return LandOutcome.DONE if moved is not None else LandOutcome.NO_RIVER
    if act in (A.PARCH, A.GREEN):
        shape = await shape_of(ctx.session, region.id, region.world_id)
        shape.desertification = geomorph.desertified_at if act is A.PARCH else 0
        shape.desertified = act is A.PARCH
        shape.desert_since_epoch = ctx.epoch if shape.desertified else None
        if act is A.PARCH:
            set_soil(ctx.rules, ground, SoilKind.SAND, base_drop=geomorph.desert_soil_base_drop)
        return LandOutcome.DONE
    soil = SoilKind.SALT if act is A.SALT_SOIL else SoilKind.VOLCANIC if fiery else SoilKind.LOAM
    return LandOutcome.DONE if set_soil(ctx.rules, ground, soil) else LandOutcome.UNCHANGED


async def stir_ground(ctx: TickContext, region: EntityRow, ground: RegionEnvironmentRow, act: LandAct) -> LandOutcome:
    table = ctx.rules.land_shaping
    if act is A.OPEN_SPRING:
        wetter = hold_value(ground, "moisture", clamp_int(ground.moisture + table.spring_moisture, 0, PERCENT))
        flowing = ground.river_class is RiverClass.NONE and hold_value(ground, "river_class", RiverClass.STREAM)
        return LandOutcome.DONE if wetter or flowing else LandOutcome.UNCHANGED
    if act is A.CALL_LAVA:
        await erupted(ctx, region, PERCENT)
        burn_back(ground, ctx.epoch)
        physics = await ctx.session.get(WorldPhysicsRow, region.world_id) if region.world_id is not None else None
        if physics is not None and "volcanism" not in physics.locked:
            physics.volcanism = clamp_int(physics.volcanism + table.lava_volcanism, 0, PERCENT)
        return LandOutcome.DONE
    if ground.coast_kind is CoastKind.NONE:
        return LandOutcome.NO_COAST
    hold_value(ground, "elevation_mean", clamp_int(ground.elevation_mean - table.step, 0, PERCENT))
    await apply_disaster(ctx, region, Disaster.FLOOD, 1.0)
    return LandOutcome.DONE


WATERING = {A.CARVE_VALLEY: 1, A.OPEN_SPRING: 1, A.FILL_VALLEY: -1}


async def downstream(ctx: TickContext, region: EntityRow, act: LandAct) -> int | None:
    sign = WATERING.get(act)
    if sign is None:
        return None
    atlas = await RegionAtlas.load(ctx.session)
    grounds = {
        row.entity_id: row
        for row in await ctx.session.scalars(select(RegionEnvironmentRow).where(RegionEnvironmentRow.entity_id.in_(atlas.neighbour_regions(region.id))))
    }
    lower = [region_id for region_id in downhill(atlas, grounds, region.id) if not held(region_id)]
    if not lower:
        return None
    ground = grounds[lower[0]]
    hold_value(ground, "moisture", clamp_int(ground.moisture + sign * ctx.rules.land_shaping.downstream_moisture, 0, PERCENT))
    return ground.entity_id


def above_the_sea(rules: Rules, ground: RegionEnvironmentRow, act: LandAct) -> bool:
    if act is not A.RAISE_LAND or ground.coast_kind is CoastKind.NONE or ground.elevation_mean < rules.land_shaping.coast_lift:
        return False
    return hold_value(ground, "coast_kind", CoastKind.NONE)


async def reshape_ground(
    ctx: TickContext, region: EntityRow, ground: RegionEnvironmentRow, act: LandAct, *, god_id: int, fiery: bool, target_region_id: int | None = None
) -> LandOutcome:
    if act in SOIL_ACTS:
        outcome = await work_soil(ctx, region, ground, act, fiery=fiery, target_region_id=target_region_id)
    elif act in LIFTS:
        outcome = LandOutcome.DONE if lift(ground, act, ctx.rules.land_shaping.step) else LandOutcome.UNCHANGED
    else:
        outcome = await stir_ground(ctx, region, ground, act)
    if outcome is LandOutcome.DONE:
        above_the_sea(ctx.rules, ground, act)
        await downstream(ctx, region, act)
        await awe_of_folk(ctx, region.id, god_id, act)
        await ctx.session.flush()
    return outcome
