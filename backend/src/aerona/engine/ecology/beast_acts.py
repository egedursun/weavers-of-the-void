from collections.abc import Awaitable, Callable, Mapping

from sqlalchemy import select

from aerona.catalog.conditions import MADNESS_CONDITIONS
from aerona.catalog.life.ecology import CARRIED_BY
from aerona.catalog.life_traits import ATTACK_RANGE_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.core.total import total
from aerona.db.stored import stored_id
from aerona.db.tables.anatomy import CreatureAnatomyRow, CreatureAttackRow
from aerona.db.tables.celestial import SkyEventRow
from aerona.db.tables.culture import RiteProfileRow
from aerona.db.tables.ecology import BeastProfileRow, SpeciesRangeRow
from aerona.db.tables.economy import ResourceProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.db.write_guard import held
from aerona.domain.enums.affliction import PackageKind, Transmission
from aerona.domain.enums.body import ConditionKind, DamageType, HarmCause
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.ecology import AttackEffect, AttackRange, AwakeningTrigger, BeastTemper, Habitat, Temperament
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.life_traits import AttackRangeTrait
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import ActKind, MemoryKind, ThoughtKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction, StepLocus, StepOutcome, StepState
from aerona.domain.enums.war import CaptiveStatus
from aerona.engine.body.afflictions import afflict
from aerona.engine.body.conditions import gain_condition
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import GoodsLedger
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mind.hooks import committed
from aerona.engine.mind.memories import remember
from aerona.engine.mind.thoughts import think
from aerona.engine.mortal.standing import add_stress
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_in
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import set_stats, shift_stat, stat
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.services.war import held_captive, release_captive, take_captive

HOARD_ROBBED = "beast.hoard_robbed"
FIGHTS = frozenset({EngineKind.BATTLE, EngineKind.SIEGE})


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


async def by_mining(ctx: TickContext, atlas: RegionAtlas, anatomy: CreatureAnatomyRow, region_id: int | None) -> bool:
    return await mine_depth(ctx, atlas, region_id) >= ctx.rules.monsters.awaken_depth_pct


async def by_desecration(ctx: TickContext, atlas: RegionAtlas, anatomy: CreatureAnatomyRow, region_id: int | None) -> bool:
    return await desecrated_near(ctx, atlas, region_id)


async def by_disturbance(ctx: TickContext, atlas: RegionAtlas, anatomy: CreatureAnatomyRow, region_id: int | None) -> bool:
    if region_id is None:
        return False
    table = ctx.rules.beast_waking
    fights = await ctx.session.scalars(
        select(EntityRow.id).where(EntityRow.engine_kind.in_(sorted(FIGHTS)), EntityRow.birth_epoch == ctx.epoch).order_by(EntityRow.id)
    )
    near = any(atlas.distance(region_id, fight) <= table.disturbance_range for fight in fights)
    return near and ctx.rng(f"wake.disturbance.{anatomy.node_id}.{ctx.epoch}").chance(table.disturbance_pct)


async def by_theft(ctx: TickContext, atlas: RegionAtlas, anatomy: CreatureAnatomyRow, region_id: int | None) -> bool:
    robbed = await ctx.session.scalar(
        select(IncidentRow.id)
        .join(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
        .where(IncidentRow.kind == HOARD_ROBBED, IncidentRow.epoch == ctx.epoch, IncidentParticipantRow.node_id == anatomy.node_id)
        .limit(1)
    )
    return robbed is not None and ctx.rng(f"wake.theft.{anatomy.node_id}.{ctx.epoch}").chance(ctx.rules.beast_waking.theft_pct)


async def by_sky_sign(ctx: TickContext, atlas: RegionAtlas, anatomy: CreatureAnatomyRow, region_id: int | None) -> bool:
    world_id = atlas.world_of(region_id) if region_id is not None else None
    sign = await ctx.session.scalar(select(SkyEventRow.id).where(SkyEventRow.epoch == ctx.epoch, SkyEventRow.world_id == world_id).limit(1))
    return sign is not None and ctx.rng(f"wake.sky.{anatomy.node_id}.{ctx.epoch}").chance(ctx.rules.beast_waking.sky_sign_pct)


async def summoner_of(ctx: TickContext, atlas: RegionAtlas, region_id: int | None) -> EntityRow | None:
    if region_id is None:
        return None
    rites = await ctx.session.scalars(
        select(EntityRow)
        .join(RiteProfileRow, RiteProfileRow.rite_entity_id == EntityRow.id)
        .where(RiteProfileRow.school == MagicSchool.SUMMONING, EntityRow.status == EntityStatus.CANON, EntityRow.location_id.is_not(None))
        .order_by(EntityRow.id)
    )
    for rite in rites:
        if rite.location_id is not None and atlas.top_region(rite.location_id) == region_id:
            return await ctx.session.get(EntityRow, rite.location_id)
    return None


async def by_summons(ctx: TickContext, atlas: RegionAtlas, anatomy: CreatureAnatomyRow, region_id: int | None) -> bool:
    caller = await summoner_of(ctx, atlas, region_id)
    if caller is None:
        return False
    row = await ctx.session.get(BeastProfileRow, anatomy.node_id)
    if (
        row is not None
        and "temper" not in row.locked
        and ctx.rng(f"wake.summons.{anatomy.node_id}.{ctx.epoch}").chance(ctx.rules.beast_waking.summons_bind_pct)
    ):
        row.temper, row.bound_to_node_id = BeastTemper.BOUND, caller.id
    return True


async def by_kin_harmed(ctx: TickContext, atlas: RegionAtlas, anatomy: CreatureAnatomyRow, region_id: int | None) -> bool:
    row = await ctx.session.get(BeastProfileRow, anatomy.node_id)
    if row is None or row.species_entity_id is None or region_id is None:
        return False
    kin = await ctx.session.get(SpeciesRangeRow, (row.species_entity_id, region_id))
    return kin is not None and kin.hunted > 0 and ctx.rng(f"wake.kin.{anatomy.node_id}.{ctx.epoch}").chance(ctx.rules.beast_waking.kin_harmed_pct)


async def by_season(ctx: TickContext, atlas: RegionAtlas, anatomy: CreatureAnatomyRow, region_id: int | None) -> bool:
    return ctx.rng(f"wake.season.{anatomy.node_id}.{ctx.epoch}").chance(ctx.rules.beast_waking.season_pct)


Trigger = Callable[[TickContext, RegionAtlas, CreatureAnatomyRow, int | None], Awaitable[bool]]
TRIGGERS: Mapping[AwakeningTrigger, Trigger] = total(
    AwakeningTrigger,
    {
        AwakeningTrigger.DEEP_MINING: by_mining,
        AwakeningTrigger.DESECRATION: by_desecration,
        AwakeningTrigger.DISTURBANCE: by_disturbance,
        AwakeningTrigger.THEFT: by_theft,
        AwakeningTrigger.SKY_SIGN: by_sky_sign,
        AwakeningTrigger.SUMMONS: by_summons,
        AwakeningTrigger.KIN_HARMED: by_kin_harmed,
        AwakeningTrigger.SEASON: by_season,
    },
)


async def triggered(ctx: TickContext, atlas: RegionAtlas, anatomy: CreatureAnatomyRow | None, region_id: int | None) -> bool:
    if anatomy is None or anatomy.awakening is None:
        return False
    woke = await TRIGGERS[anatomy.awakening](ctx, atlas, anatomy, region_id)
    if woke:
        await record(ctx, "beast.stirred", roles={IncidentRole.SUBJECT: anatomy.node_id}, facts={"trigger": anatomy.awakening})
    return woke


async def rob_hoards(ctx: TickContext, atlas: RegionAtlas) -> int:
    table = ctx.rules.beast_waking
    robbed = 0
    sleepers = await ctx.session.scalars(
        select(BeastProfileRow).where(BeastProfileRow.temper == BeastTemper.SLEEPING).order_by(BeastProfileRow.beast_entity_id)
    )
    for row in list(sleepers):
        if held(row.beast_entity_id) or "hoard" in row.locked or not row.hoard or row.lair_place_id is None:
            continue
        if not ctx.rng(f"hoard.theft.{row.beast_entity_id}.{ctx.epoch}").chance(table.hoard_theft_pct):
            continue
        lair = atlas.top_region(row.lair_place_id)
        towns = [
            town
            for town in await ctx.session.scalars(
                select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
            )
            if lair is not None and atlas.top_region(town.id) == lair and not held(town.id)
        ]
        if not towns:
            continue
        thief = towns[0]
        key = max(sorted(row.hoard), key=lambda item: row.hoard[item])
        taken = max(1, row.hoard[key] // 4)
        row.hoard = {**row.hoard, key: row.hoard[key] - taken}
        await remember(ctx.session, ctx.rules, holder_id=row.beast_entity_id, subject_id=thief.id, kind=MemoryKind.HARMED_ME, magnitude=-taken, epoch=ctx.epoch)
        await record(ctx, HOARD_ROBBED, roles={IncidentRole.SUBJECT: row.beast_entity_id, IncidentRole.ACTOR: thief.id}, facts={"taken": taken}, place=thief.id)
        await committed(ctx, thief.id, ActKind.TOMB_ROBBING, row.beast_entity_id)
        robbed += 1
    return robbed


async def carry_off(ctx: TickContext, beast: EntityRow, row: BeastProfileRow, near: list[EntityRow]) -> int | None:
    if not near or not ctx.rng(f"abduct.{beast.id}.{ctx.epoch}").chance(ctx.rules.monsters.abduct_pct):
        return None
    for town in near:
        victim = await seize(ctx, beast, row, town, "carried off in the night")
        if victim is not None:
            await record(
                ctx,
                "beasts.carried_off",
                roles={IncidentRole.ACTOR: beast.id, IncidentRole.VICTIM: victim.id, IncidentRole.ORIGIN: town.id},
                steps=(
                    StepDraft(
                        StepAction.CARRY_OFF,
                        actor=beast.id,
                        target=victim.id,
                        locus_kind=StepLocus.SETTLEMENT,
                        locus_node=town.id,
                        outcome=StepOutcome.CAPTURED,
                        states=((victim.id, StepState.CAPTURED),),
                    ),
                ),
                place=town.id,
            )
            return victim.id
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
WHOLE_TOWN = having(ATTACK_RANGE_TRAITS, AttackRangeTrait.WHOLE_TOWN)


def ready(attack: CreatureAttackRow, epoch: int) -> bool:
    return attack.last_used_epoch is None or epoch - attack.last_used_epoch >= attack.recharge


async def wound(ctx: TickContext, beast: EntityRow, victim: EntityRow, attack: CreatureAttackRow, damage_type: DamageType) -> None:
    told = f"struck by the {spoken(attack.delivery)} of {beast.name}"
    harm = Harm(ctx.rules.creature_anatomy.attack_damage, HarmCause.MONSTER, told, damage_type=damage_type, source_node_id=beast.id, killer_id=beast.id)
    await apply_hits(ctx, victim, harm)
    if attack.effect is AttackEffect.DRAIN and not held(beast.id):
        shift_stat(beast, "hp", ctx.rules.creature_anatomy.drain_heal, 0)


async def bind_mind(ctx: TickContext, beast: EntityRow, victims: list[EntityRow], attack: CreatureAttackRow) -> None:
    table = ctx.rules.creature_anatomy
    rng = ctx.rng(f"attack.mind.{beast.id}.{await stored_id(ctx.session, attack)}.{ctx.epoch}")
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
        return await seize(ctx, beast, row, town, f"taken by the {spoken(attack.delivery)} of {beast.name}")
    living = await townsfolk(ctx, town)
    if not living:
        return None
    victim = ctx.rng(f"attack.{beast.id}.{await stored_id(ctx.session, attack)}.{town.id}.{ctx.epoch}").pick(living)
    victims = living[: ctx.rules.beast_acts.area_targets] if attack.range is AttackRange.AREA else living if attack.range in WHOLE_TOWN else [victim]
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
