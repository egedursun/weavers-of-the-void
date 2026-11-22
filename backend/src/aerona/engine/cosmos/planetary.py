from collections import defaultdict

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.physics import WorldPhysicsRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import CoastKind
from aerona.domain.enums.evolution import CycleEffect
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.loops import BalanceLoop
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.cosmos.cycles import WorldCycles, cycles_by_world, flux_of
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.loops.delay import lagged
from aerona.engine.phases.disasters import apply_disaster
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, clamp_percent, round_half_up
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import POPULATION_KEY, scale_stat, shift_bounded
from aerona.engine.recording.record import record
from aerona.rules.registry import Rules

FERTILITY_KEY = "fertility"


def ice_target(rules: Rules, physics: WorldPhysicsRow) -> int:
    table = rules.planetary_climate
    return clamp_percent(round_half_up((table.thaw_kelvin - physics.surface_temperature) * table.ice_per_kelvin))


def sea_level_of(rules: Rules, physics: WorldPhysicsRow) -> int:
    return round_half_up(physics.hydrosphere - physics.cryosphere * rules.planetary_climate.sea_per_ice_pct / PERCENT)


def move_ice(rules: Rules, physics: WorldPhysicsRow, target: int) -> int:
    if "cryosphere" in physics.locked:
        return 0
    table = rules.planetary_climate
    step = max(-table.ice_step, min(table.ice_step, target - physics.cryosphere))
    if not step:
        return 0
    physics.cryosphere = clamp_percent(physics.cryosphere + step)
    if "albedo" not in physics.locked:
        physics.albedo = clamp_int(physics.albedo + round_half_up(step * table.albedo_per_ice_pct / PERCENT), 0, 95)
    return step


def move_carbon(ctx: TickContext, physics: WorldPhysicsRow, cleared: float, cycles: WorldCycles | None = None) -> int:
    if "carbon_dioxide" in physics.locked or physics.pressure <= 0:
        return 0
    table = ctx.rules.planetary_climate
    rng = ctx.rng(f"carbon.{physics.world_id}")
    change = 0
    flux = flux_of(cycles, CycleEffect.GREENHOUSE)
    if flux is not None:
        change = flux if flux > 0 or physics.carbon_dioxide > table.weathering_floor else 0
    else:
        if rng.chance(physics.volcanism * table.volcanic_co2_pct / PERCENT):
            change += 1
        if rng.chance(cleared * table.burning_co2_pct / PERCENT):
            change += 1
        if physics.carbon_dioxide > table.weathering_floor and rng.chance(table.weathering_pct):
            change -= 1
    if change:
        physics.carbon_dioxide = clamp_percent(physics.carbon_dioxide + change)
        if change > 0 and "nitrogen" not in physics.locked and physics.nitrogen > 0:
            physics.nitrogen = clamp_percent(physics.nitrogen - change)
    return change


async def move_coasts(ctx: TickContext, world: WorldRow, physics: WorldPhysicsRow, grounds: list[RegionEnvironmentRow], atlas: RegionAtlas) -> int:
    table = ctx.rules.planetary_climate
    level = sea_level_of(ctx.rules, physics)
    shift = level - physics.sea_level
    if abs(shift) < table.flood_step:
        return 0
    if "sea_level" not in physics.locked:
        physics.sea_level = level
    coastal = {ground.entity_id for ground in grounds if ground.coast_kind is not CoastKind.NONE and not held(ground.entity_id)}
    if not coastal:
        return 0
    regions = {region.id: region for region in await canon(ctx.session, [EntityType.REGION], world.id) if region.id in coastal}
    if shift > 0:
        for region in sorted(regions.values(), key=lambda row: row.id):
            await apply_disaster(ctx, region, Disaster.FLOOD, table.flood_loss_pct / PERCENT)
        moved = await move_inland(ctx, world, coastal, atlas)
        await record(
            ctx,
            "climate.seas_rose",
            roles={IncidentRole.SUBJECT: world.id, IncidentRole.VICTIM: sorted(regions)},
            facts={"shift": shift, "loss": table.flood_loss_pct, "moved": moved},
            world_id=world.id,
        )
        return moved + len(regions)
    for region in regions.values():
        shift_bounded(ctx.rules, region, FERTILITY_KEY, table.flood_step)
    await record(
        ctx,
        "climate.seas_fell",
        roles={IncidentRole.SUBJECT: world.id, IncidentRole.BENEFICIARY: sorted(regions)},
        facts={"shift": shift, "fertility": table.flood_step},
        world_id=world.id,
    )
    return len(regions)


async def move_inland(ctx: TickContext, world: WorldRow, coastal: set[int], atlas: RegionAtlas) -> int:
    table = ctx.rules.planetary_climate
    moved = 0
    statement = select(EntityRow).where(
        EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.world_id == world.id, EntityRow.location_id.in_(list(coastal))
    )
    for town in list(await ctx.session.scalars(statement.order_by(EntityRow.id))):
        if held(town.id) or town.location_id is None:
            continue
        with flowing(FlowCategory.DISASTER):
            scale_stat(ctx.rules, town, POPULATION_KEY, (PERCENT - table.flood_loss_pct) / PERCENT)
        inland = sorted(region for region in atlas.neighbour_regions(town.location_id) if region not in coastal)
        if not inland:
            continue
        coast = town.location_id
        town.location_id = inland[0]
        await BondRepository(ctx.session).refresh_location(town.id, town.location_id, ctx.epoch)
        await record(
            ctx,
            "climate.town_moved",
            roles={IncidentRole.SUBJECT: town.id, IncidentRole.ORIGIN: coast, IncidentRole.DESTINATION: inland[0]},
            facts={"loss": table.flood_loss_pct},
            origin=coast,
            destination=inland[0],
            world_id=world.id,
        )
        moved += 1
    return moved


async def planetary_climate(ctx: TickContext, worlds: dict[int, WorldRow], physics: dict[int, WorldPhysicsRow]) -> int:
    grounds: dict[int, list[RegionEnvironmentRow]] = defaultdict(list)
    for ground in await ctx.session.scalars(select(RegionEnvironmentRow).order_by(RegionEnvironmentRow.entity_id)):
        grounds[ground.world_id].append(ground)
    atlas = await RegionAtlas.load(ctx.session)
    cycles = await cycles_by_world(ctx.session)
    changed = 0
    for world_id, row in sorted(physics.items()):
        world = worlds.get(world_id)
        if world is None or held(world_id):
            continue
        land = grounds.get(world_id, [])
        cleared = sum(ground.cleared for ground in land) / len(land) if land else 0.0
        changed += abs(move_ice(ctx.rules, row, await lagged(ctx, BalanceLoop.GLACIAL_THAW, row.world_id, ice_target(ctx.rules, row))))
        changed += abs(move_carbon(ctx, row, cleared, cycles.get(world_id)))
        changed += await move_coasts(ctx, world, row, land, atlas)
    return changed
