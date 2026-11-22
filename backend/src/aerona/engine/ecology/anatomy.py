from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.creature_anatomy import EXOTIC_TISSUES, HOARDED, LIFE_SKIN, PLAN_LIMBS, PLAN_SKIN, TISSUES, TRAIT_ATTACKS, TRAIT_SKIN, AttackSpec
from aerona.catalog.life.domain import GROWN
from aerona.catalog.life.ecology import ATTACK_SPECS_ATTACK_RANGES, BONE_OF, CLOSE_DELIVERIES, GENERATE_PACKAGE_KINDS, TOWN_DELIVERIES
from aerona.constants.units import PERCENT
from aerona.core.grammar import several
from aerona.core.random import RandomKey, SeededRandom
from aerona.db.tables.anatomy import CreatureAnatomyRow, CreatureAttackRow
from aerona.db.tables.body import BodyRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.ecology import BeastProfileRow, SpeciesProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.affliction import PackageKind
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.ecology import (
    AttackDelivery,
    AttackEffect,
    AttackRange,
    Aversion,
    AwakeningTrigger,
    Biochemistry,
    Habitat,
    Temperament,
    TissueMaterial,
)
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import CoastKind, RiverClass
from aerona.domain.enums.society import CreatureTrait
from aerona.domain.enums.structure import StructureKind
from aerona.engine.body.book import beast_plan, wild_plan
from aerona.engine.context import TickContext
from aerona.engine.cosmos.fauna import traits_of
from aerona.engine.economy.stocks import holding
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

T = CreatureTrait
BEAST_BODIES_FIXUP = "creature_anatomy.beast_bodies"
MIND_EFFECTS = (AttackEffect.FEAR, AttackEffect.STILLNESS, AttackEffect.SLEEP, AttackEffect.CONFUSION, AttackEffect.CHARM)
FLYERS = frozenset({BodyPlan.AVIAN})
HOLY_KINDS = frozenset({StructureKind.TEMPLE, StructureKind.SHRINE, StructureKind.MONASTERY})
TEMPERAMENTS = (Temperament.PLACID, Temperament.SKITTISH, Temperament.CURIOUS, Temperament.FIERCE, Temperament.CUNNING)


def words(value: str) -> str:
    return value.replace("_", " ")


def habitat_of(plan: BodyPlan, traits: set[CreatureTrait], biochemistry: Biochemistry, *, deep: bool) -> Habitat:
    if biochemistry is Biochemistry.VOID:
        return Habitat.VOID
    if deep or T.BURROWING in traits:
        return Habitat.DEEP
    if T.AQUATIC in traits or plan is BodyPlan.AQUATIC:
        return Habitat.WATER
    if T.FLYING in traits or plan in FLYERS:
        return Habitat.SKY
    return Habitat.LAND


def temperament_of(rng: SeededRandom, aggression: int, fear: int) -> Temperament:
    if aggression >= PERCENT * 2 // 3:
        return Temperament.FIERCE
    if fear >= PERCENT * 2 // 3:
        return Temperament.SKITTISH
    return rng.pick(list(TEMPERAMENTS))


def generate(
    rules: Rules,
    node_id: int,
    plan: BodyPlan,
    traits: set[CreatureTrait],
    biochemistry: Biochemistry,
    *,
    aggression: int,
    fear: int,
    monster: bool,
    deep: bool = False,
    epoch: int = 0,
) -> CreatureAnatomyRow:
    table = rules.creature_anatomy
    rng = SeededRandom(RandomKey(node_id, epoch, "anatomy"))
    limbs = PLAN_LIMBS[plan] + (2 if rng.chance(table.monster_limb_pct if monster else table.extra_limb_pct) else 0)
    heads = 1 + (rng.integer(1, 2) if monster and rng.chance(table.monster_head_pct) else 1 if rng.chance(table.extra_head_pct) else 0)
    flies = T.FLYING in traits or plan in FLYERS
    wings = 2 if flies or rng.chance(table.monster_wings_pct if monster else table.wings_pct) else 0
    skin = next((TRAIT_SKIN[trait] for trait in TRAIT_SKIN if trait in traits), None) or LIFE_SKIN.get(biochemistry) or PLAN_SKIN[plan]
    if monster and rng.chance(table.exotic_tissue_pct):
        skin = rng.pick(list(EXOTIC_TISSUES))
    bite = PackageKind.SNAKE_VENOM if T.VENOMOUS in traits else None
    if bite is None and rng.chance(table.monster_bite_pct if monster else table.bite_pct):
        bite = rng.pick(GENERATE_PACKAGE_KINDS)
    temperament = temperament_of(rng, aggression, fear)
    if monster and rng.chance(table.abductor_pct):
        temperament = Temperament.SEIZES_PREY
    return CreatureAnatomyRow(
        node_id=node_id,
        limbs=limbs,
        heads=heads,
        wings=wings,
        tails=1 if rng.chance(table.tail_pct) else 0,
        skin=skin,
        bone=BONE_OF.get(skin, TissueMaterial.RIGID),
        bite=bite,
        temperament=temperament,
        hoards=rng.pick(list(HOARDED)) if monster and rng.chance(table.hoard_pct) else None,
        hates=rng.pick(list(Aversion)) if rng.chance(table.hate_pct) else None,
        awakening=rng.pick(list(AwakeningTrigger)) if monster and rng.chance(table.awakening_pct) else None,
        habitat=habitat_of(plan, traits, biochemistry, deep=deep),
        generated_epoch=epoch,
        locked=[],
    )


async def anatomy_of(session: AsyncSession, node_id: int | None) -> CreatureAnatomyRow | None:
    return await session.get(CreatureAnatomyRow, node_id) if node_id is not None else None


async def unique_kind(session: AsyncSession, beast: BeastProfileRow) -> bool:
    if beast.species_entity_id is None:
        return True
    kin = await session.scalar(select(func.count()).select_from(BeastProfileRow).where(BeastProfileRow.species_entity_id == beast.species_entity_id))
    species = await session.get(EntityRow, beast.species_entity_id)
    abundance = (stat(species, "abundance") or 0) if species is not None else 0
    return int(kin or 0) <= 1 and abundance <= 0


def attack_specs(rules: Rules, node_id: int, traits: set[CreatureTrait], *, monster: bool, epoch: int = 0) -> list[AttackSpec]:
    table = rules.creature_anatomy
    rng = SeededRandom(RandomKey(node_id, epoch, "attacks"))
    specs = [TRAIT_ATTACKS[trait] for trait in TRAIT_ATTACKS if trait in traits]
    if not specs and rng.chance(table.monster_attack_pct if monster else table.attack_pct):
        effect = rng.pick([effect for effect in AttackEffect if effect not in MIND_EFFECTS])
        specs.append(AttackSpec(rng.pick(list(TOWN_DELIVERIES)), effect, rng.pick(ATTACK_SPECS_ATTACK_RANGES)))
    if monster and rng.chance(table.sight_attack_pct):
        effect = rng.pick(list(MIND_EFFECTS))
        specs.append(AttackSpec(AttackDelivery.GAZE, effect, AttackRange.SIGHT, permanent=effect is AttackEffect.STILLNESS))
    if monster and rng.chance(table.monster_bite_pct):
        specs.append(AttackSpec(rng.pick(list(CLOSE_DELIVERIES)), rng.pick([AttackEffect.VENOM, AttackEffect.DRAIN, AttackEffect.FORCE]), AttackRange.TOUCH))
    return specs


def attack_row(node_id: int, spec: AttackSpec) -> CreatureAttackRow:
    row = CreatureAttackRow(node_id=node_id, delivery=spec.delivery, effect=spec.effect, range=spec.range, recharge=0, permanent=spec.permanent)
    row.locked = []
    return row


async def give_attacks(ctx: TickContext, node_id: int, specs: list[AttackSpec]) -> None:
    for spec in specs:
        ctx.session.add(attack_row(node_id, spec))


async def species_anatomy(ctx: TickContext, species: EntityRow, profile: SpeciesProfileRow) -> CreatureAnatomyRow:
    traits = await traits_of(ctx.session, species.id)
    row = generate(
        ctx.rules,
        species.id,
        profile.body_plan,
        traits,
        profile.biochemistry,
        aggression=profile.aggression,
        fear=profile.fear_of_people,
        monster=False,
        epoch=ctx.epoch,
    )
    ctx.session.add(row)
    await give_attacks(ctx, species.id, attack_specs(ctx.rules, species.id, traits, monster=False, epoch=ctx.epoch))
    return row


async def known_plan(session: AsyncSession, node_id: int) -> BodyPlan:
    body = await session.get(BodyRow, node_id)
    if body is not None:
        return body.plan
    profile = await session.get(SpeciesProfileRow, node_id)
    if profile is not None:
        return profile.body_plan
    beast = await session.get(BeastProfileRow, node_id)
    if beast is None or beast.species_entity_id is None:
        return wild_plan(node_id)
    return await known_plan(session, beast.species_entity_id)


async def plan_limbs(session: AsyncSession, node_id: int) -> int:
    return PLAN_LIMBS[await known_plan(session, node_id)]


async def fit_beast_bodies(session: AsyncSession) -> int:
    if await session.get(AppliedFixupRow, BEAST_BODIES_FIXUP) is not None:
        return 0
    bodies = await session.execute(
        select(EntityRow, BodyRow).join(BodyRow, BodyRow.node_id == EntityRow.id).where(EntityRow.entity_type == EntityType.BEAST).order_by(EntityRow.id)
    )
    fitted = waiting = 0
    for beast, body in list(bodies):
        if body.plan is not BodyPlan.HUMANOID:
            continue
        if held(beast.id):
            waiting += 1
            continue
        plan, traits = await beast_plan(session, beast)
        if plan is not body.plan:
            body.plan, body.traits = plan, traits
            fitted += 1
    if not waiting:
        session.add(AppliedFixupRow(key=BEAST_BODIES_FIXUP, result={"fitted": fitted}))
    await session.flush()
    return fitted


async def beast_anatomy(ctx: TickContext, beast: EntityRow, row: BeastProfileRow, *, deep: bool = False) -> CreatureAnatomyRow:
    kind = await ctx.session.get(SpeciesProfileRow, row.species_entity_id) if row.species_entity_id is not None else None
    traits = await traits_of(ctx.session, row.species_entity_id) if row.species_entity_id is not None else set()
    plan = await known_plan(ctx.session, beast.id)
    biochemistry = kind.biochemistry if kind is not None else Biochemistry.CARBON_WATER
    anatomy = generate(
        ctx.rules,
        beast.id,
        plan,
        traits,
        biochemistry,
        aggression=stat(beast, "danger") or 0,
        fear=0,
        monster=deep or await unique_kind(ctx.session, row),
        deep=deep,
        epoch=ctx.epoch,
    )
    monster = deep or await unique_kind(ctx.session, row)
    specs = attack_specs(ctx.rules, beast.id, traits, monster=monster, epoch=ctx.epoch)
    inherited = await ctx.session.get(CreatureAnatomyRow, row.species_entity_id) if row.species_entity_id is not None else None
    if inherited is not None and not deep:
        anatomy.skin, anatomy.bone, anatomy.habitat = inherited.skin, inherited.bone, inherited.habitat
        anatomy.bite = anatomy.bite or inherited.bite
        if not specs and row.species_entity_id is not None:
            kin = await ctx.session.scalars(select(CreatureAttackRow).where(CreatureAttackRow.node_id == row.species_entity_id).order_by(CreatureAttackRow.id))
            specs = [AttackSpec(item.delivery, item.effect, item.range, item.permanent) for item in kin]
    ctx.session.add(anatomy)
    await give_attacks(ctx, beast.id, specs)
    return anatomy


async def ensure_anatomy(ctx: TickContext) -> int:
    await fit_beast_bodies(ctx.session)
    known = set(await ctx.session.scalars(select(CreatureAnatomyRow.node_id)))
    made = 0
    for profile in list(await ctx.session.scalars(select(SpeciesProfileRow).where(SpeciesProfileRow.species_class.not_in(list(GROWN))))):
        species = await ctx.session.get(EntityRow, profile.species_entity_id)
        if profile.species_entity_id in known or held(profile.species_entity_id) or species is None or species.status is not EntityStatus.CANON:
            continue
        await species_anatomy(ctx, species, profile)
        made += 1
    await ctx.session.flush()
    for row in list(await ctx.session.scalars(select(BeastProfileRow).order_by(BeastProfileRow.beast_entity_id))):
        beast = await ctx.session.get(EntityRow, row.beast_entity_id)
        if row.beast_entity_id in known or held(row.beast_entity_id) or beast is None or beast.status is not EntityStatus.CANON:
            continue
        await beast_anatomy(ctx, beast, row)
        made += 1
    await ctx.session.flush()
    return made


def harm_factor(rules: Rules, anatomy: CreatureAnatomyRow | None, plan_limbs: int, attacks: int = 0) -> float:
    if anatomy is None:
        return 1.0
    table = rules.creature_anatomy
    extra = (
        attacks * table.attack_harm_pct
        + max(0, anatomy.heads - 1) * table.head_harm_pct
        + max(0, anatomy.limbs - plan_limbs) * table.limb_harm_pct
        + TISSUES[anatomy.skin].harm_pct
    )
    return 1 + extra / PERCENT


def armour_of(anatomy: CreatureAnatomyRow | None) -> int:
    return TISSUES[anatomy.skin].armour_pct if anatomy is not None else 0


async def body_might(session: AsyncSession, rules: Rules, node_id: int) -> float:
    anatomy = await anatomy_of(session, node_id)
    if anatomy is None:
        return 1.0
    guard = 1 + armour_of(anatomy) * rules.creature_anatomy.armour_power_pct / PERCENT / PERCENT
    attacks = len(list(await session.scalars(select(CreatureAttackRow.id).where(CreatureAttackRow.node_id == node_id))))
    return harm_factor(rules, anatomy, await plan_limbs(session, node_id), attacks) * guard


async def repelled(ctx: TickContext, atlas: RegionAtlas, town: EntityRow, aversion: Aversion | None) -> bool:
    if aversion is None:
        return False
    if aversion is Aversion.FIRE:
        return await holding(ctx.session, town.id, CommodityKind.FUEL) > 0
    if aversion is Aversion.IRON:
        return await holding(ctx.session, town.id, CommodityKind.WEAPONS) > 0
    if aversion is Aversion.NOISE:
        return (stat(town, "population") or 0) >= ctx.rules.creature_anatomy.noise_population
    if aversion is Aversion.WATER:
        region = atlas.top_region(town.id)
        land = await ctx.session.get(RegionEnvironmentRow, region) if region is not None else None
        return land is not None and (land.coast_kind is not CoastKind.NONE or land.river_class is not RiverClass.NONE)
    holy = select(StructureProfileRow.structure_entity_id).join(EntityRow, EntityRow.id == StructureProfileRow.structure_entity_id)
    found = await ctx.session.scalar(
        holy.where(EntityRow.location_id == town.id, EntityRow.status == EntityStatus.CANON, StructureProfileRow.kind.in_(list(HOLY_KINDS))).limit(1)
    )
    return found is not None


async def anatomy_lines(session: AsyncSession, node_id: int) -> list[str]:
    row = await session.get(CreatureAnatomyRow, node_id)
    if row is None:
        return []
    parts = [f"{several(row.limbs, 'limb', 'limbs')}", f"{row.heads} {'head' if row.heads == 1 else 'heads'}"]
    if row.wings:
        parts.append(f"{several(row.wings, 'wing', 'wings')}")
    if row.tails:
        parts.append("a tail")
    lines = [f"body: {', '.join(parts)}; skin of {words(row.skin.value)}, bones of {words(row.bone.value)}; lives in the {words(row.habitat.value)}"]
    attacks = await session.scalars(select(CreatureAttackRow).where(CreatureAttackRow.node_id == node_id).order_by(CreatureAttackRow.id))
    weapons = [
        *(f"{words(item.delivery.value)} of {words(item.effect.value)}, reaching {words(item.range.value)}" for item in attacks),
        f"its bite carries {words(row.bite.value)}" if row.bite else "",
    ]
    if any(weapons):
        lines.append(f"attacks: {'; '.join(item for item in weapons if item)}")
    nature = [f"temperament {words(row.temperament.value)}"]
    if row.hoards:
        nature.append(f"hoards {words(row.hoards.value)}")
    if row.hates:
        nature.append(f"shuns {words(row.hates.value)}")
    if row.awakening:
        nature.append(f"wakes to {words(row.awakening.value)}")
    lines.append("nature: " + ", ".join(nature))
    return lines
