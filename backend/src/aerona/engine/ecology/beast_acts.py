from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.anatomy import CreatureAnatomyRow
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.economy import ResourceProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.db.write_guard import held
from aerona.domain.enums.affliction import PackageKind, Transmission
from aerona.domain.enums.ecology import AwakeningTrigger, Habitat, Temperament
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import MemoryKind, ThoughtKind
from aerona.domain.enums.war import CaptiveStatus
from aerona.engine.body.afflictions import afflict
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import GoodsLedger
from aerona.engine.mind.thoughts import think
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.services.war import held_captive, release_captive, take_captive


async def mine_depth(ctx: TickContext, atlas: RegionAtlas, region_id: int | None) -> int:
    if region_id is None:
        return 0
    deepest = 0
    for resource_id, reserve, initial in await ctx.session.execute(
        select(ResourceProfileRow.resource_entity_id, ResourceProfileRow.reserve, ResourceProfileRow.initial_reserve).where(
            ResourceProfileRow.initial_reserve > 0
        )
    ):
        if atlas.top_region(resource_id) == region_id:
            deepest = max(deepest, round((initial - reserve) * PERCENT / initial))
    return deepest


async def desecrated_near(ctx: TickContext, atlas: RegionAtlas, region_id: int | None) -> bool:
    if region_id is None:
        return False
    since = ctx.epoch - ctx.rules.monsters.desecration_epochs
    holders = await ctx.session.scalars(select(MemoryRow.holder_node_id).where(MemoryRow.kind == MemoryKind.DESECRATED_HOLY, MemoryRow.epoch >= since))
    return any(atlas.top_region(holder) == region_id for holder in holders)


async def triggered(ctx: TickContext, atlas: RegionAtlas, anatomy: CreatureAnatomyRow | None, region_id: int | None) -> bool:
    if anatomy is None or anatomy.awakening is None:
        return False
    if anatomy.awakening is AwakeningTrigger.DEEP_MINING:
        return await mine_depth(ctx, atlas, region_id) >= ctx.rules.monsters.awaken_depth_pct
    return await desecrated_near(ctx, atlas, region_id)


async def carry_off(ctx: TickContext, beast: EntityRow, row: BeastProfileRow, near: list[EntityRow]) -> str | None:
    if not near or not ctx.rng(f"abduct.{beast.id}.{ctx.epoch}").chance(ctx.rules.monsters.abduct_pct):
        return None
    for town in near:
        if held(town.id):
            continue
        victims = await ctx.session.scalars(
            select(EntityRow)
            .where(EntityRow.location_id == town.id, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
            .order_by(EntityRow.id)
        )
        for victim in list(victims):
            if held(victim.id) or await held_captive(ctx.session, victim.id) is not None:
                continue
            await take_captive(ctx, beast, victim, None, description="carried off in the night", home_id=town.id)
            victim.location_id = row.lair_place_id or beast.location_id
            await think(ctx.session, ctx.rules, victim.id, ThoughtKind.WAS_CAPTURED, ctx.epoch, subject_id=beast.id)
            return f"{beast.name} carried {victim.name} off from {town.name}"
    return None


async def free_captives(ctx: TickContext, beast: EntityRow) -> int:
    freed = 0
    kept = select(CaptiveRow).where(CaptiveRow.captor_entity_id == beast.id, CaptiveRow.status == CaptiveStatus.HELD)
    for captive in list(await ctx.session.scalars(kept)):
        await release_captive(ctx, captive, CaptiveStatus.RESCUED)
        prisoner = await ctx.session.get(EntityRow, captive.captive_entity_id)
        if prisoner is not None and captive.home_entity_id is not None:
            prisoner.location_id = captive.home_entity_id
            await think(ctx.session, ctx.rules, prisoner.id, ThoughtKind.WAS_FREED, ctx.epoch, subject_id=beast.id)
        freed += 1
    return freed


def is_abductor(anatomy: CreatureAnatomyRow | None) -> bool:
    return anatomy is not None and anatomy.temperament is Temperament.ABDUCTOR


async def void_trophy(ctx: TickContext, beast: EntityRow, slayer: EntityRow) -> int:
    anatomy = await ctx.session.get(CreatureAnatomyRow, beast.id)
    if anatomy is None or anatomy.habitat is not Habitat.VOID:
        return 0
    home = await ctx.session.get(EntityRow, slayer.location_id) if slayer.entity_type is EntityType.MORTAL and slayer.location_id else slayer
    if home is None:
        return 0
    return await GoodsLedger(ctx.session, ctx.epoch).add(
        home.id, CommodityKind.LUXURIES, ctx.rules.monsters.void_glass_trophy, GoodsFlow.LOOT, material=MaterialKind.VOID_GLASS
    )


async def terror_gaze(ctx: TickContext, beast: EntityRow) -> None:
    anatomy = await ctx.session.get(CreatureAnatomyRow, beast.id)
    if anatomy is not None and anatomy.gaze is not None:
        terror = stat(beast, "terror") or 0
        set_stats(beast, terror=clamp_int(terror + ctx.rules.creature_anatomy.gaze_terror, 0, PERCENT))


async def bite_someone(ctx: TickContext, beast: EntityRow, town: EntityRow, package: PackageKind) -> bool:
    victims = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.location_id == town.id, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    living = [victim for victim in victims if not held(victim.id)]
    if not living:
        return False
    victim = ctx.rng(f"bite.{beast.id}.{town.id}.{ctx.epoch}").pick(living)
    return await afflict(ctx, victim, package, Transmission.BITE, source_node_id=beast.id) is not None
