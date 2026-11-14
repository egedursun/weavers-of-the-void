from collections import Counter, defaultdict

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmography import PhenomenonFootprintRow, PhenomenonProfileRow, RiftRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.routes import RouteRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.cosmography import OPEN_RIFT_STATES, PhenomenonKind, WorldAge
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityType
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.enums.world import Atmosphere, WorldType
from aerona.engine.context import TickContext
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.eras.effects import programme_pressure
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phases.disasters import apply_disaster
from aerona.engine.primitives.numbers import clamp_int, clamp_percent
from aerona.engine.primitives.queries import canon, flags_by_entity
from aerona.engine.primitives.stats import stat_or
from aerona.rules.registry import Rules

GATE_METHODS = frozenset(
    {TravelMethod.ANCIENT_GATE, TravelMethod.DIVINE_BRIDGE, TravelMethod.GALACTIC_GATE, TravelMethod.DIMENSIONAL_RIFT, TravelMethod.PLANAR_DOOR}
)
MOOD_LIMIT = PERCENT


def excess_radiation(rules: Rules, world: WorldRow | None) -> int:
    if world is None:
        return 0
    return max(0, world.radiation - rules.world_life.radiation_baseline)


def cosmic_disease(rules: Rules, world: WorldRow | None) -> int:
    if world is None:
        return 0
    table = rules.world_life
    load = excess_radiation(rules, world) * table.radiation_disease_pct // PERCENT
    if world.atmosphere is Atmosphere.TOXIC:
        load += table.toxic_disease
    if world.biosphere_health < table.biosphere_collapse:
        load += table.collapse_disease
    return load


def radiation_mutation(rules: Rules, world: WorldRow | None) -> float:
    return excess_radiation(rules, world) * rules.world_life.radiation_mutation_pct / PERCENT / PERCENT


def age_of(rules: Rules, world: WorldRow, epoch: int) -> WorldAge:
    table = rules.world_life
    age = epoch - (world.created_epoch or 1)
    if age < table.young_epochs:
        return WorldAge.YOUNG
    if age < table.young_epochs + table.mature_epochs:
        return WorldAge.MATURE
    if age < table.young_epochs + table.mature_epochs + table.old_epochs:
        return WorldAge.OLD
    return WorldAge.DYING


def grown_age(rules: Rules, world: WorldRow, epoch: int) -> WorldAge:
    ages = list(WorldAge)
    return max(age_of(rules, world, epoch), world.age_stage, key=ages.index)


async def extinct_kinds(ctx: TickContext) -> Counter[int]:
    statement = select(EntityRow.world_id).join(EntityFlagRow, EntityFlagRow.entity_id == EntityRow.id).where(EntityFlagRow.flag == EntityFlag.EXTINCT)
    return Counter(await ctx.session.scalars(statement))


async def invasive_kinds(ctx: TickContext) -> Counter[int]:
    statement = select(EntityRow.world_id).join(EntityFlagRow, EntityFlagRow.entity_id == EntityRow.id).where(EntityFlagRow.flag == EntityFlag.INVASIVE)
    return Counter(await ctx.session.scalars(statement))


def biosphere_target(rules: Rules, grounds: list[RegionEnvironmentRow], extinct: int, invasive: int) -> int:
    table = rules.world_life
    use = sum((ground.cleared + ground.farmed) / 2 for ground in grounds) / len(grounds) if grounds else 0
    return clamp_percent(PERCENT - use * table.biosphere_land_use_pct / PERCENT - extinct * table.biosphere_extinction - invasive * table.biosphere_invasive)


async def tend_mood(ctx: TickContext, world: WorldRow, grounds: list[RegionEnvironmentRow], revering: int) -> None:
    table = ctx.rules.world_life
    if world.world_type is not WorldType.LIVING or "mood" in world.locked:
        return
    worked = sum(ground.mined + ground.cleared for ground in grounds) / len(grounds) if grounds else 0
    if world.consciousness_closed:
        if worked <= table.mood_reopen_worked and "consciousness_closed" not in world.locked:
            world.consciousness_closed = False
            await note(ctx, f"{world.name} woke again to those who live on it.", key="world.consciousness_opened", world_id=world.id)
        return
    world.mood = clamp_int(world.mood - round(worked / 10 * table.mood_mining) + revering * table.mood_reverence, -MOOD_LIMIT, MOOD_LIMIT)
    if world.mood <= table.mood_close and "consciousness_closed" not in world.locked:
        world.consciousness_closed = True
        await note(ctx, f"{world.name} withdrew into itself and no longer answers those who live on it.", key="world.consciousness_closed", world_id=world.id)
        return
    if world.mood <= table.mood_quake and grounds:
        target = ctx.rng(f"world_mood.{world.id}").pick(sorted(ground.entity_id for ground in grounds))
        region = await ctx.session.get(EntityRow, target)
        if region is not None and not held(region.id):
            await apply_disaster(ctx, region, Disaster.EARTHQUAKE, table.mood_quake_severity / PERCENT)
            await note(ctx, f"{world.name} shook {region.name} in anger at what was taken from it.", key="world.mood_quake", ids=[region.id], world_id=world.id)
    if world.mood >= table.mood_bounty:
        for ground in grounds:
            if not held(ground.entity_id) and "soil_fertility" not in ground.locked:
                ground.soil_fertility = clamp_percent(ground.soil_fertility + table.mood_fertility)


@reads(
    "region.danger",
    "table.cosmos",
    "table.dimensional_events",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.galactic_structures",
    "table.region_environment",
)
@writes("table.chronicle", "table.epoch_year_cursors", "table.incidents", "table.worlds")
async def world_lives(ctx: TickContext) -> None:
    cosmography = await Cosmography.load(ctx.session)
    grounds: dict[int, list[RegionEnvironmentRow]] = defaultdict(list)
    for ground in await ctx.session.scalars(select(RegionEnvironmentRow).order_by(RegionEnvironmentRow.entity_id)):
        grounds[ground.world_id].append(ground)
    extinct, invasive = await extinct_kinds(ctx), await invasive_kinds(ctx)
    planet_devoted = await flags_by_entity(ctx.session, EntityFlag.WORSHIPS_PLANET)
    revering: Counter[int] = Counter(community.world_id for community in await canon(ctx.session, COMMUNITY_TYPES) if community.id in planet_devoted)
    regions: dict[int, list[EntityRow]] = defaultdict(list)
    for region in await canon(ctx.session, [EntityType.REGION]):
        regions[region.world_id].append(region)
    for world in sorted(cosmography.worlds.values(), key=lambda row: row.id):
        if held(world.id):
            continue
        star = cosmography.place_world(world).star
        if "radiation" not in world.locked:
            world.radiation = clamp_percent(round((star.radiation if star is not None else 0) * (PERCENT - world.magnetism) / PERCENT))
        await tend_biosphere(ctx, world, biosphere_target(ctx.rules, grounds[world.id], extinct[world.id], invasive[world.id]))
        await tend_age(ctx, world, grounds[world.id])
        await tend_mood(ctx, world, grounds[world.id], revering[world.id])
        if "danger" not in world.locked and regions[world.id]:
            world.danger = clamp_percent(round(sum(stat_or(region, "danger", 0) for region in regions[world.id]) / len(regions[world.id])))
    await ctx.session.flush()


async def tend_biosphere(ctx: TickContext, world: WorldRow, target: int) -> None:
    table = ctx.rules.world_life
    if "biosphere_health" in world.locked:
        return
    before = world.biosphere_health
    step = max(-table.biosphere_regen * 5, min(table.biosphere_regen, target - world.biosphere_health))
    world.biosphere_health = clamp_percent(world.biosphere_health + step)
    if before >= table.biosphere_collapse > world.biosphere_health:
        await note(ctx, f"The life of {world.name} collapsed.", key="world.biosphere_collapse", world_id=world.id, kind=ChronicleKind.WORLD)


async def tend_age(ctx: TickContext, world: WorldRow, grounds: list[RegionEnvironmentRow]) -> None:
    if "age_stage" not in world.locked:
        aged = grown_age(ctx.rules, world, ctx.epoch)
        if aged is not world.age_stage:
            world.age_stage = aged
            await note(ctx, f"{world.name} grew {aged.value}.", key=f"world.aged.{aged.value}", world_id=world.id, kind=ChronicleKind.WORLD_AGE)
    if world.age_stage not in (WorldAge.OLD, WorldAge.DYING):
        return
    for ground in grounds:
        if not held(ground.entity_id) and "soil_fertility" not in ground.locked:
            ground.soil_fertility = clamp_percent(ground.soil_fertility - ctx.rules.world_life.old_soil_loss)


async def regional_leak(ctx: TickContext) -> int:
    table = ctx.rules.world_life
    worlds = {row.id: row for row in await ctx.session.scalars(select(WorldRow))}
    outer_ids = await flags_by_entity(ctx.session, EntityFlag.OUTER_CULT)
    pressure: Counter[int] = Counter()
    for being in await canon(ctx.session, [EntityType.OUTER_BEING, EntityType.CULT]):
        if (being.entity_type is EntityType.OUTER_BEING or being.id in outer_ids) and being.location_id is not None:
            pressure[being.location_id] += table.leak_outer
    for rift in await ctx.session.scalars(select(RiftRow).where(RiftRow.state.in_(list(OPEN_RIFT_STATES)))):
        if rift.region_entity_id is not None:
            pressure[rift.region_entity_id] += rift.size * ctx.rules.rifts.leak_pct // PERCENT
    wounds = select(PhenomenonFootprintRow.region_entity_id, PhenomenonFootprintRow.intensity).join(
        PhenomenonProfileRow, PhenomenonProfileRow.entity_id == PhenomenonFootprintRow.phenomenon_entity_id
    )
    for region_id, intensity in await ctx.session.execute(wounds.where(PhenomenonProfileRow.kind == PhenomenonKind.LEAK_WOUND)):
        pressure[region_id] += intensity * ctx.rules.rifts.leak_pct // PERCENT
    for region_id, amount in (await programme_pressure(ctx.session, ctx.rules)).items():
        pressure[region_id] += amount
    gated = set()
    for route in await ctx.session.scalars(select(RouteRow).where(RouteRow.active.is_(True), RouteRow.method.in_(list(GATE_METHODS)))):
        gated |= {route.world_a_id, route.world_b_id}
    hot = 0
    for ground in await ctx.session.scalars(select(RegionEnvironmentRow).order_by(RegionEnvironmentRow.entity_id)):
        if held(ground.entity_id) or "leak" in ground.locked:
            continue
        world = worlds.get(ground.world_id)
        target = (world.leakage * table.leak_world_pct // PERCENT if world is not None else 0) + pressure[ground.entity_id]
        if ground.world_id in gated:
            target += table.leak_gate
        target = clamp_percent(target)
        if ground.leak > target:
            ground.leak = max(target, ground.leak - table.leak_decay)
        else:
            ground.leak = target
        hot += int(ground.leak >= table.leak_hot)
    await ctx.session.flush()
    return hot


async def hot_regions(ctx: TickContext, world_id: int) -> list[int]:
    statement = select(RegionEnvironmentRow.entity_id).where(
        RegionEnvironmentRow.world_id == world_id, RegionEnvironmentRow.leak >= ctx.rules.world_life.leak_hot
    )
    return list(await ctx.session.scalars(statement.order_by(RegionEnvironmentRow.leak.desc(), RegionEnvironmentRow.entity_id)))
