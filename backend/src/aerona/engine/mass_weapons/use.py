from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mass_weapons import MassWeaponRow
from aerona.db.write_guard import held
from aerona.domain.enums.cosmography import RiftCause
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mass_weapons import MassHarm, MassReach
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.cosmos.rifts import tear_toward
from aerona.engine.environment.long_seasons import made_spell
from aerona.engine.mass_weapons.book import BURNING, KILL_WEIGHT, REACH_RANK, REMNANT_OF, ArsenalTally
from aerona.engine.mass_weapons.remnants import leave_remnant
from aerona.engine.means.building import burn_structures
from aerona.engine.mind.memories import remember
from aerona.engine.phases.disasters import strike_plague
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.doom import advance_doom
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.recording.record import record

GALE = 1.0
GRIEF_SCALE = 100

MADE_WINTER_PER_RANK = 10


async def victims(ctx: TickContext, atlas: RegionAtlas, weapon: MassWeaponRow, target: EntityRow) -> list[EntityRow]:
    if weapon.reach is MassReach.SETTLEMENT:
        return [target] if target.entity_type is EntityType.SETTLEMENT else []
    if weapon.reach is MassReach.REGION:
        region = target.id if target.entity_type is EntityType.REGION else atlas.top_region(target.id)
        if region is None:
            return []
        query = select(EntityRow).where(EntityRow.id.in_(atlas.communities_in(region)), EntityRow.entity_type == EntityType.SETTLEMENT)
    else:
        query = select(EntityRow).where(EntityRow.world_id == target.world_id, EntityRow.entity_type == EntityType.SETTLEMENT)
    return list(await ctx.session.scalars(query.where(EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)))


async def strike_town(ctx: TickContext, weapon: MassWeaponRow, town: EntityRow, by: int) -> int:
    dead = round_half_up((stat(town, "population") or 0) * ctx.rules.mass_weapons.use_kill_pct * KILL_WEIGHT[weapon.harm] / (PERCENT * PERCENT))
    shift_stat(town, "population", -dead)
    if weapon.harm in BURNING:
        await burn_structures(ctx, town, GALE)
    if weapon.harm is MassHarm.DISEASE:
        await strike_plague(ctx, town, ctx.rules.mass_weapons.use_kill_pct)
    await remember(
        ctx.session,
        ctx.rules,
        holder_id=town.id,
        subject_id=weapon.holder_entity_id,
        kind=MemoryKind.KILLED_KIN,
        magnitude=-min(PERCENT, dead // GRIEF_SCALE + 1),
        epoch=ctx.epoch,
    )
    await record(
        ctx,
        "war.mass_weapon_used",
        roles={IncidentRole.ACTOR: by, IncidentRole.VICTIM: town.id},
        facts={"harm": weapon.harm, "dead": dead},
    )
    return dead


async def tear_by_weapon(ctx: TickContext, weapon: MassWeaponRow, regions: list[int]) -> None:
    for region_id in regions:
        region = await ctx.session.get(EntityRow, region_id)
        world = await ctx.session.get(WorldRow, region.world_id) if region is not None and region.world_id is not None else None
        if world is None or not ctx.rng(f"mass_weapon.rift.{weapon.id}.{region_id}.{ctx.epoch}").chance(ctx.rules.rifts.mass_weapon_pct):
            continue
        await tear_toward(ctx, world, region, RiftCause.MASS_WEAPON, by_node_id=weapon.holder_entity_id)


async def use_weapon(ctx: TickContext, weapon: MassWeaponRow, target: EntityRow, tally: ArsenalTally, *, by: int | None = None) -> int:
    atlas = await RegionAtlas.load(ctx.session)
    towns = [town for town in await victims(ctx, atlas, weapon, target) if not held(town.id)]
    if "count" not in (weapon.locked or []):
        weapon.count = max(0, weapon.count - 1)
    weapon.used_epoch = ctx.epoch
    killed = 0
    for town in towns:
        killed += await strike_town(ctx, weapon, town, by or weapon.holder_entity_id)
    kind = REMNANT_OF[weapon.harm]
    regions = sorted({region for region in (atlas.top_region(town.id) for town in towns) if region is not None})
    if kind is not None:
        for region in regions:
            await leave_remnant(ctx, kind, ctx.rules.mass_weapons.remnant_density, tally, region=region, weapon=weapon.id)
    if REACH_RANK[weapon.reach] >= REACH_RANK[MassReach.REGION]:
        await tear_by_weapon(ctx, weapon, regions)
    await advance_doom(ctx.session, ctx.rules, ctx.rules.mass_weapons.doom_per_reach * REACH_RANK[weapon.reach])
    world = await ctx.session.get(WorldRow, target.world_id) if target.world_id is not None else None
    if world is not None and REACH_RANK[weapon.reach] >= REACH_RANK[MassReach.REGION]:
        await made_spell(ctx, world, winter=True, severity=min(PERCENT, REACH_RANK[weapon.reach] * MADE_WINTER_PER_RANK), incident_id=None)
    tally.used += 1
    tally.killed += killed
    return killed
