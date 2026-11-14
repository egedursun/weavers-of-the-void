from enum import StrEnum

from sqlalchemy import select

from aerona.catalog.climate import climate_profile
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.cosmography import OceanCurrent, WorldAge
from aerona.domain.enums.environment import CoastKind
from aerona.domain.enums.world import ClimateEra
from aerona.engine.context import TickContext
from aerona.engine.cosmos.cycles import cycles_by_world, rain_swing
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.rules.registry import Rules

SHIFT_LIMIT = PERCENT
COLD_ERAS = frozenset({ClimateEra.ICE_AGE})


class ClimateTurn(StrEnum):
    WARMER = "warmer"
    COLDER = "colder"
    WETTER = "wetter"
    DRIER = "drier"


def current_heat(rules: Rules, current: OceanCurrent) -> int:
    heat = rules.world_life.current_heat
    return {OceanCurrent.NONE: 0, OceanCurrent.WARM: heat, OceanCurrent.COLD: -heat}[current]


def band_of(rules: Rules, star: StarRow | None) -> tuple[float, float] | None:
    if star is None:
        return None
    table = rules.star_life
    return star.brightness * table.band_inner_pct / PERCENT, star.brightness * table.band_outer_pct / PERCENT


def band_heat(rules: Rules, world: WorldRow, star: StarRow | None, orbit: float | None = None) -> int:
    band = band_of(rules, star)
    if band is None or (orbit is None and world.parent_world_id is not None):
        return 0
    inner, outer = band
    distance = world.orbit if orbit is None else orbit
    if distance < inner:
        return rules.star_life.band_heat
    if distance > outer:
        return -rules.star_life.band_heat
    return 0


def age_cooling(rules: Rules, world: WorldRow) -> int:
    table = rules.world_life
    steps = {WorldAge.YOUNG: 0, WorldAge.MATURE: 0, WorldAge.OLD: 1, WorldAge.DYING: 2}[world.age_stage]
    return -min(table.cooling_floor, steps * table.old_cooling)


def world_heat(rules: Rules, world: WorldRow, star: StarRow | None, sky_heat: int | None = None) -> int:
    return (band_heat(rules, world, star) if sky_heat is None else 0) + age_cooling(rules, world)


def era_target(rules: Rules, env: RegionEnvironmentRow, era: ClimateEra | None) -> int:
    if era is None:
        return 0
    shift = climate_profile(rules, era).temperature_shift
    table = rules.world_life
    target = 0
    if env.coast_kind is not CoastKind.NONE:
        target -= round(shift * table.coast_era_pct / PERCENT)
    if era in COLD_ERAS and env.elevation_mean >= table.highland_elevation:
        target += round(shift * table.highland_era_pct / PERCENT)
    return target


def toward(value: int, target: int, step: int) -> int:
    return value + max(-step, min(step, target - value))


async def regional_climate(ctx: TickContext) -> int:
    table = ctx.rules.world_life
    atlas = await RegionAtlas.load(ctx.session)
    grounds = {row.entity_id: row for row in await ctx.session.scalars(select(RegionEnvironmentRow).order_by(RegionEnvironmentRow.entity_id))}
    worlds = {row.id: row for row in await ctx.session.scalars(select(WorldRow))}
    cycles = await cycles_by_world(ctx.session)
    moved = 0
    for region_id, env in grounds.items():
        if held(region_id, env.world_id):
            continue
        world = worlds.get(env.world_id)
        era = world.climate_era if world is not None else None
        neighbours = [grounds[other] for other in atlas.neighbour_regions(region_id) if other in grounds]
        cleared = sum(other.cleared for other in neighbours) / len(neighbours) if neighbours else 0
        rain_target = -round(cleared / 20 * table.deforestation_rain) + rain_swing(ctx.rules, cycles.get(env.world_id))
        heat_target = era_target(ctx.rules, env, era)
        if "temperature_shift" not in env.locked:
            before = env.temperature_shift
            env.temperature_shift = clamp_int(toward(env.temperature_shift, heat_target, table.shift_step), -SHIFT_LIMIT, SHIFT_LIMIT)
            moved += int(before != env.temperature_shift)
        if "rainfall_shift" not in env.locked:
            before = env.rainfall_shift
            env.rainfall_shift = clamp_int(toward(env.rainfall_shift, rain_target, table.shift_step), -SHIFT_LIMIT, SHIFT_LIMIT)
            moved += int(before != env.rainfall_shift)
    await ctx.session.flush()
    return moved


async def cold_snap(ctx: TickContext, world_id: int, amount: int, cause: str) -> int:
    chilled = 0
    for env in await ctx.session.scalars(select(RegionEnvironmentRow).where(RegionEnvironmentRow.world_id == world_id)):
        if held(env.entity_id) or "temperature_shift" in env.locked:
            continue
        env.temperature_shift = clamp_int(env.temperature_shift - amount, -SHIFT_LIMIT, SHIFT_LIMIT)
        chilled += 1
    if chilled:
        world = await ctx.session.get(WorldRow, world_id)
        if world is not None:
            await note(ctx, f"{cause} cooled {world.name}.", key="climate.cold_snap", kind=ChronicleKind.CLIMATE, world_id=world_id)
    return chilled


async def turn_region(ctx: TickContext, region_id: int, turn: ClimateTurn, by: str) -> RegionEnvironmentRow:
    env = await ctx.session.get(RegionEnvironmentRow, region_id)
    region = await ctx.session.get(EntityRow, region_id)
    if env is None or region is None:
        raise NotFoundError("That region has no climate to turn.")
    amount = ctx.rules.world_life.imposed_shift
    if turn in (ClimateTurn.WARMER, ClimateTurn.COLDER):
        env.temperature_shift = clamp_int(env.temperature_shift + (amount if turn is ClimateTurn.WARMER else -amount), -SHIFT_LIMIT, SHIFT_LIMIT)
    else:
        env.rainfall_shift = clamp_int(env.rainfall_shift + (amount if turn is ClimateTurn.WETTER else -amount), -SHIFT_LIMIT, SHIFT_LIMIT)
    await note(
        ctx,
        f"{by} turned the climate of {region.name} {turn.value}.",
        key="climate.region_turned",
        ids=[region.id],
        kind=ChronicleKind.CLIMATE,
        world_id=region.world_id,
    )
    await ctx.session.flush()
    return env
