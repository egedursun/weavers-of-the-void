from collections.abc import Mapping

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.anatomy import CreatureAnatomyRow, CreatureAttackRow
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.economy import ResourceProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.db.write_guard import held
from aerona.domain.enums.affliction import PackageKind, Transmission
from aerona.domain.enums.body import MADNESS_CONDITIONS, ConditionKind, DamageType, HarmCause
from aerona.domain.enums.ecology import AttackDelivery, AttackEffect, AttackRange, AwakeningTrigger, Habitat, Temperament
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import MemoryKind, ThoughtKind
from aerona.domain.enums.war import CaptiveStatus
from aerona.engine.body.afflictions import afflict
from aerona.engine.body.conditions import gain_condition
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import GoodsLedger
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mind.thoughts import think
from aerona.engine.mortal.standing import add_stress
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_in
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import set_stats, shift_stat, stat
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
        victim = await seize(ctx, beast, row, town, "carried off in the night")
        if victim is not None:
            return f"{beast.name} carried {victim.name} off from {town.name}"
    return None


async def seize(ctx: TickContext, beast: EntityRow, row: BeastProfileRow, town: EntityRow, description: str) -> EntityRow | None:
    if held(town.id):
        return None
    victims = await ctx.session.scalars(
        select(EntityRow)
        .where(await present_in(ctx.session, town), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    for victim in list(victims):
        if held(victim.id) or await held_captive(ctx.session, victim.id) is not None:
            continue
        await take_captive(ctx, beast, victim, None, description=description, home_id=town.id)
        victim.location_id = row.lair_place_id or beast.location_id
        await think(ctx.session, ctx.rules, victim.id, ThoughtKind.WAS_CAPTURED, ctx.epoch, subject_id=beast.id)
        return victim
    return None


WOUNDS: Mapping[AttackEffect, DamageType | None] = total(
    AttackEffect,
    {
        AttackEffect.HEAT: DamageType.FIRE,
        AttackEffect.COLD: DamageType.COLD,
        AttackEffect.CORROSION: DamageType.CHEMICAL,
        AttackEffect.SHOCK: DamageType.ELECTRIC,
        AttackEffect.VENOM: None,
        AttackEffect.FORCE: DamageType.BLUNT,
        AttackEffect.ENTANGLE: None,
        AttackEffect.FEAR: None,
        AttackEffect.STILLNESS: None,
        AttackEffect.SLEEP: None,
        AttackEffect.CONFUSION: None,
        AttackEffect.CHARM: None,
        AttackEffect.DRAIN: DamageType.VOID,
    },
)
CARRIED_BY: Mapping[AttackDelivery, Transmission] = total(
    AttackDelivery,
    {
        AttackDelivery.BREATH: Transmission.INHALATION,
        AttackDelivery.SPIT: Transmission.CONTACT,
        AttackDelivery.SPRAY: Transmission.CONTACT,
        AttackDelivery.EMANATION: Transmission.INHALATION,
        AttackDelivery.GAZE: Transmission.GAZE,
        AttackDelivery.VOICE: Transmission.EXPERIENCE,
        AttackDelivery.TOUCH: Transmission.CONTACT,
        AttackDelivery.SPORES: Transmission.INHALATION,
        AttackDelivery.BITE: Transmission.BITE,
        AttackDelivery.STING: Transmission.BLOOD,
    },
)
WHOLE_TOWN = frozenset({AttackRange.FAR, AttackRange.SIGHT})


def ready(attack: CreatureAttackRow, epoch: int) -> bool:
    return attack.last_used_epoch is None or epoch - attack.last_used_epoch >= attack.recharge


async def wound(ctx: TickContext, beast: EntityRow, victim: EntityRow, attack: CreatureAttackRow, damage_type: DamageType) -> None:
    told = f"struck by the {attack.delivery.value} of {beast.name}"
    harm = Harm(ctx.rules.creature_anatomy.attack_damage, HarmCause.MONSTER, told, damage_type=damage_type, source_node_id=beast.id, killer_id=beast.id)
    await apply_hits(ctx, victim, harm)
    if attack.effect is AttackEffect.DRAIN and not held(beast.id):
        shift_stat(beast, "hp", ctx.rules.creature_anatomy.drain_heal, 0)


async def bind_mind(ctx: TickContext, beast: EntityRow, victims: list[EntityRow], attack: CreatureAttackRow) -> None:
    table = ctx.rules.creature_anatomy
    rng = ctx.rng(f"attack.mind.{beast.id}.{attack.id}.{ctx.epoch}")
    if attack.effect is AttackEffect.FEAR:
        for mortal in victims:
            await add_stress(ctx.session, mortal.id, table.fear_stress, ctx.epoch)
    elif attack.effect is AttackEffect.STILLNESS:
        severity = 5 if attack.permanent else table.stillness_severity
        await gain_condition(ctx, rng.pick(victims), ConditionKind.WITHERED_LIMB, HarmCause.MONSTER, severity=severity, source_node_id=beast.id)
    elif attack.effect is AttackEffect.CONFUSION:
        await gain_condition(ctx, rng.pick(victims), rng.pick(list(MADNESS_CONDITIONS)), HarmCause.MONSTER, source_node_id=beast.id)


async def strike(ctx: TickContext, beast: EntityRow, row: BeastProfileRow, town: EntityRow, attack: CreatureAttackRow) -> EntityRow | None:
    if not ready(attack, ctx.epoch) or attack.effect is AttackEffect.SLEEP:
        return None
    if "last_used_epoch" not in attack.locked:
        attack.last_used_epoch = ctx.epoch
    if attack.effect in (AttackEffect.ENTANGLE, AttackEffect.CHARM):
        return await seize(ctx, beast, row, town, f"taken by the {attack.delivery.value} of {beast.name}")
    living = await townsfolk(ctx, town)
    if not living:
        return None
    victim = ctx.rng(f"attack.{beast.id}.{attack.id}.{town.id}.{ctx.epoch}").pick(living)
    victims = living if attack.range in WHOLE_TOWN else [victim]
    damage_type = WOUNDS[attack.effect]
    if attack.effect is AttackEffect.VENOM:
        await afflict(ctx, victim, PackageKind.SNAKE_VENOM, CARRIED_BY[attack.delivery], source_node_id=beast.id)
    elif damage_type is not None:
        await wound(ctx, beast, victim, attack, damage_type)
    else:
        await bind_mind(ctx, beast, victims, attack)
    return victim


async def attacks_of(ctx: TickContext, node_id: int) -> list[CreatureAttackRow]:
    return list(await ctx.session.scalars(select(CreatureAttackRow).where(CreatureAttackRow.node_id == node_id).order_by(CreatureAttackRow.id)))


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
    return anatomy is not None and anatomy.temperament is Temperament.SEIZES_PREY


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


async def townsfolk(ctx: TickContext, town: EntityRow) -> list[EntityRow]:
    found = await ctx.session.scalars(
        select(EntityRow)
        .where(await present_in(ctx.session, town), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    return [mortal for mortal in found if not held(mortal.id)]


async def sight_scale(ctx: TickContext, beast: EntityRow, town: EntityRow, attacks: list[CreatureAttackRow]) -> float:
    seen = [attack for attack in attacks if attack.range is AttackRange.SIGHT and ready(attack, ctx.epoch)]
    if not seen:
        return 1.0
    table = ctx.rules.creature_anatomy
    set_stats(beast, terror=clamp_int((stat(beast, "terror") or 0) + table.sight_terror, 0, PERCENT))
    return 1 + table.sleep_raid_pct / PERCENT if any(attack.effect is AttackEffect.SLEEP for attack in seen) else 1.0


async def bite_someone(ctx: TickContext, beast: EntityRow, town: EntityRow, package: PackageKind) -> bool:
    living = await townsfolk(ctx, town)
    if not living:
        return False
    victim = ctx.rng(f"bite.{beast.id}.{town.id}.{ctx.epoch}").pick(living)
    return await afflict(ctx, victim, package, Transmission.BITE, source_node_id=beast.id) is not None
