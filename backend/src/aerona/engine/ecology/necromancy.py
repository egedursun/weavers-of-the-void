from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import RiteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.tables.warfare import ArmyRow, SiegeRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.military import UnitKind
from aerona.domain.enums.structure import StructureKind
from aerona.domain.enums.war import SiegeStatus, WarCause
from aerona.domain.models.entity_stats import ArmyStats, StructureStats
from aerona.engine.context import TickContext
from aerona.engine.military.control import add_stack
from aerona.engine.military.siege import open_siege
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import connect, living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.services.war import open_war
from aerona.engine.structures.profiles import ensure_profile


@dataclass
class NecromancyTally:
    towers: int = 0
    hosts: int = 0
    sieges: int = 0


async def death_power(ctx: TickContext, mortal_id: int) -> int:
    rites = select(BondRow.target_node_id).where(BondRow.source_node_id == mortal_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    found = await ctx.session.scalar(
        select(func.max(RiteProfileRow.power)).where(RiteProfileRow.rite_entity_id.in_(rites), RiteProfileRow.school == MagicSchool.DEATH)
    )
    return int(found or 0)


async def necromancers(ctx: TickContext) -> list[tuple[EntityRow, int]]:
    deathly = select(RiteProfileRow.rite_entity_id).where(RiteProfileRow.school == MagicSchool.DEATH)
    owners = await ctx.session.scalars(
        select(BondRow.source_node_id)
        .where(BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE, BondRow.target_node_id.in_(deathly))
        .distinct()
        .order_by(BondRow.source_node_id)
    )
    found: list[tuple[EntityRow, int]] = []
    for owner_id in list(owners):
        mortal = await living_entity(ctx.session, owner_id)
        if mortal is not None and mortal.entity_type is EntityType.MORTAL and not held(mortal.id):
            found.append((mortal, await death_power(ctx, mortal.id)))
    return found


async def tower_of(ctx: TickContext, necromancer_id: int) -> EntityRow | None:
    tower_id = await ctx.session.scalar(
        select(StructureProfileRow.structure_entity_id)
        .join(EntityRow, EntityRow.id == StructureProfileRow.structure_entity_id)
        .where(StructureProfileRow.kind == StructureKind.TOWER, StructureProfileRow.builder_entity_id == necromancer_id, EntityRow.status == EntityStatus.CANON)
        .limit(1)
    )
    return await ctx.session.get(EntityRow, tower_id) if tower_id is not None else None


async def host_of(ctx: TickContext, necromancer_id: int) -> EntityRow | None:
    army_id = await ctx.session.scalar(
        select(ArmyRow.entity_id)
        .join(EntityRow, EntityRow.id == ArmyRow.entity_id)
        .where(ArmyRow.owner_entity_id == necromancer_id, ArmyRow.disbanded_epoch.is_(None), EntityRow.status == EntityStatus.CANON)
        .limit(1)
    )
    return await ctx.session.get(EntityRow, army_id) if army_id is not None else None


async def raise_tower(ctx: TickContext, necromancer: EntityRow) -> EntityRow:
    tower = await create_record(
        ctx,
        RecordSpec(
            name=f"The Tower of {necromancer.name}",
            entity_type=EntityType.STRUCTURE,
            stats=StructureStats(splendor=PERCENT // 4, durability=PERCENT * 3 // 4, function=PERCENT // 2),
            body=f"A tower {necromancer.name} raised to work the rites of death.",
            power=3,
            world_id=necromancer.world_id,
            location_id=necromancer.location_id,
            subtype="tower",
        ),
    )
    await ensure_profile(ctx.session, ctx.rules, ctx.epoch, tower, StructureKind.TOWER, builder=necromancer)
    await connect(ctx.session, necromancer.id, tower.id, BondKind.OWNS, ctx.epoch, description="raised it")
    return tower


async def raise_host(ctx: TickContext, necromancer: EntityRow, power: int) -> EntityRow:
    count = max(1, power * ctx.rules.monsters.necro_undead_per_power)
    army = await create_record(
        ctx,
        RecordSpec(
            name=f"The Dead of {necromancer.name}",
            entity_type=EntityType.ARMY,
            stats=ArmyStats(size=count, morale=PERCENT, equipment=PERCENT // 4, experience=PERCENT // 4),
            body=f"The dead {necromancer.name} raised from their graves to march.",
            power=max(1, min(10, power)),
            world_id=necromancer.world_id,
            location_id=necromancer.location_id,
            subtype="host of the dead",
            flags=(EntityFlag.CROSSED_TO_THE_DEAD,),
        ),
    )
    ctx.session.add(ArmyRow(entity_id=army.id, war_id=None, owner_entity_id=necromancer.id, commander_entity_id=necromancer.id, raised_epoch=ctx.epoch))
    await ctx.session.flush()
    await add_stack(ctx, army.id, UnitKind.GHOST_HOST, count)
    await connect(ctx.session, necromancer.id, army.id, BondKind.COMMANDS, ctx.epoch, description="raised from the dead")
    return army


async def nearest_town(ctx: TickContext, atlas: RegionAtlas, necromancer: EntityRow) -> EntityRow | None:
    towns = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, EntityRow.world_id == necromancer.world_id)
        .order_by(EntityRow.id)
    )
    home = necromancer.location_id
    options = [town for town in towns if town.id != home and not held(town.id)]
    if not options:
        return None
    return min(options, key=lambda town: (atlas.distance(necromancer.id, town.id), town.id))


async def besiege(ctx: TickContext, atlas: RegionAtlas, necromancer: EntityRow, host: EntityRow) -> SiegeRow | None:
    row = await ctx.session.get(ArmyRow, host.id)
    if row is None or row.war_id is not None:
        return None
    town = await nearest_town(ctx, atlas, necromancer)
    if town is None:
        return None
    war = await open_war(ctx, necromancer, town, cause=WarCause.HOSTILITY, cause_text=f"{necromancer.name} sent the raised dead against {town.name}")
    row.war_id = war.id
    host.location_id = town.location_id
    siege = await open_siege(ctx, war, town, host)
    return siege if siege.status is SiegeStatus.ONGOING else None


async def necromancy(ctx: TickContext) -> NecromancyTally:
    table = ctx.rules.monsters
    tally = NecromancyTally()
    atlas = await RegionAtlas.load(ctx.session)
    acted = 0
    for necromancer, power in await necromancers(ctx):
        if acted >= table.necro_cap or power <= 0:
            continue
        rng = ctx.rng(f"necromancy.{necromancer.id}.{ctx.epoch}")
        tower = await tower_of(ctx, necromancer.id)
        if tower is None:
            if rng.chance(table.necro_tower_pct):
                tower = await raise_tower(ctx, necromancer)
                tally.towers += 1
                acted += 1
                await note(ctx, f"{necromancer.name} raised a tower to work the rites of death.", key="necromancy.tower", ids=[necromancer.id, tower.id])
            continue
        host = await host_of(ctx, necromancer.id)
        if host is None:
            if rng.chance(table.necro_raise_pct):
                host = await raise_host(ctx, necromancer, power)
                tally.hosts += 1
                acted += 1
                await note(ctx, f"{necromancer.name} raised {host.name} from their graves.", key="necromancy.host", ids=[necromancer.id, host.id])
            continue
        if rng.chance(table.necro_siege_pct):
            siege = await besiege(ctx, atlas, necromancer, host)
            if siege is not None:
                tally.sieges += 1
                acted += 1
                town = await ctx.session.get(EntityRow, siege.besieged_entity_id)
                await note(ctx, f"{host.name} laid siege to {town.name if town else 'a town'}.", key="necromancy.siege", ids=[necromancer.id, host.id])
    return tally
