import re
from collections.abc import Iterable
from dataclasses import dataclass, replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.anatomy import FINGER_COUNT, Anatomy, anatomy_of
from aerona.catalog.body_plans import BEING_PLANS, BUILD_RANK, HEIGHT_RANK, HUNGER_PLANS, PLANS, WHOLE_PLANS
from aerona.catalog.creature_anatomy import MONSTER_PLANS
from aerona.catalog.mind import SKILLS, TRAITS
from aerona.catalog.tissues import FULL_COUNTS
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.body import BodyRow, ConditionRow, InjuryRow, ProsthesisRow
from aerona.db.tables.cosmography import CosmicBeingProfileRow
from aerona.db.tables.divine import OuterBeingProfileRow
from aerona.db.tables.ecology import BeastProfileRow, SpeciesProfileRow
from aerona.db.tables.entities import EntityRow, EntityTagRow, EntityTraitRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.mind import SkillRow, TraitRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.body import (
    OPEN_INJURY_STATES,
    BodyBuild,
    BodyFunction,
    BodyPlan,
    Capacity,
    ConditionKind,
    Consciousness,
    HeightClass,
    InjuryState,
    StrikeStyle,
    TreatmentStep,
)
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.made import EffectTarget
from aerona.domain.enums.mind import TraitKind
from aerona.domain.enums.modifier import ModifierSource
from aerona.domain.enums.society import CreatureTrait, KnowledgeBranch
from aerona.engine.body.capacities import FUNCTION_LEVELS, BearerStats, BodyState, capacities, function_percents, perception_factor
from aerona.engine.body.digits import effective_counts, handedness_for
from aerona.engine.body.functions import Wound
from aerona.engine.body.hits import Armour
from aerona.engine.lore.arms import guard_of, held_profiles
from aerona.engine.mortal.equipment import worn_coverage
from aerona.engine.mortal.variants import strength, variants_by_id
from aerona.engine.primitives.augment_bonus import bonus
from aerona.engine.primitives.knowledge import known_levels
from aerona.engine.primitives.modifiers import combine, live_contributions
from aerona.engine.primitives.queries import active_bonds, living_entity
from aerona.engine.primitives.stats import base_stat, clamp_to_field, set_stats, stat, stat_or
from aerona.rules.registry import Rules

Bearer = EntityRow | SonRow | ForeignGodRow

ARMOUR_TAG = "armour"
SHIELD_TAG = "shield"
PROTECTION = "protection"
DEFAULT_STAT = 50
BODY_PLAN_VALUES = frozenset(plan.value for plan in BodyPlan)

TRAIT_FUNCTIONS: dict[CreatureTrait, BodyFunction] = {
    CreatureTrait.FLYING: BodyFunction.FLIGHT,
    CreatureTrait.VENOMOUS: BodyFunction.VENOM,
    CreatureTrait.HORNED: BodyFunction.HORN,
    CreatureTrait.TAILED: BodyFunction.TAIL,
}
TRAIT_PLANS: tuple[tuple[CreatureTrait, BodyPlan], ...] = (
    (CreatureTrait.HIVE_MIND, BodyPlan.INSECTOID),
    (CreatureTrait.SHAPESHIFTER, BodyPlan.AMORPHOUS),
    (CreatureTrait.FLYING, BodyPlan.AVIAN),
)


def bearer_stats(bearer: Bearer) -> BearerStats:
    if isinstance(bearer, EntityRow):
        agility = stat_or(bearer, "agility", DEFAULT_STAT)
        return BearerStats(
            strength=stat_or(bearer, "strength", DEFAULT_STAT),
            agility=agility,
            intellect=stat_or(bearer, "intellect", DEFAULT_STAT),
            charisma=stat_or(bearer, "charisma", DEFAULT_STAT),
            endurance=stat_or(bearer, "endurance", agility),
            age=stat(bearer, "age"),
            lifespan=stat(bearer, "lifespan"),
        )
    return BearerStats(bearer.strength, bearer.agility, bearer.wisdom, bearer.charisma, bearer.endurance)


def anatomy_for(body: BodyRow) -> Anatomy:
    return anatomy_of(body.plan, frozenset(BodyFunction(trait) for trait in body.traits))


async def species_traits(session: AsyncSession, species_id: int) -> set[CreatureTrait]:
    rows = await session.scalars(select(EntityTraitRow.trait).where(EntityTraitRow.entity_id == species_id))
    return set(rows)


def legacy_plan_from_words(text: str) -> BodyPlan | None:
    found = set(re.findall(r"[a-z]+", text.lower()))
    for spec in PLANS.values():
        if any(word in found or f"{word}s" in found for word in spec.words):
            return spec.plan
    return None


async def typed_plan(session: AsyncSession, species: EntityRow, traits: set[CreatureTrait]) -> BodyPlan:
    by_trait = next((plan for trait, plan in TRAIT_PLANS if trait in traits), None)
    if by_trait is not None:
        return by_trait
    if EntityFlag.MEGAFAUNA in await EntityRepository(session).flags(species.id):
        return BodyPlan.COLOSSAL
    profile = await session.get(SpeciesProfileRow, species.id)
    if profile is not None and profile.body_plan in BODY_PLAN_VALUES:
        return BodyPlan(profile.body_plan)
    home = await living_entity(session, species.location_id)
    return BodyPlan.AQUATIC if home is not None and home.is_water else BodyPlan.QUADRUPED


async def recorded_plan(session: AsyncSession, species: EntityRow, traits: set[CreatureTrait]) -> BodyPlan:
    typed = await typed_plan(session, species, traits)
    if typed is not BodyPlan.QUADRUPED:
        return typed
    worded = legacy_plan_from_words(" ".join(part for part in (species.name, species.subtype or "", species.description or "") if part))
    return worded or typed


def size_of(body: BodyRow) -> int:
    return HEIGHT_RANK[body.height_class] + BUILD_RANK[body.build]


def mortal_frame(rules: Rules, bearer: EntityRow, plan: BodyPlan) -> tuple[HeightClass, BodyBuild]:
    spec = PLANS[plan]
    rng = SeededRandom.for_epoch(bearer.id, bearer.birth_epoch, "frame")
    heights = list(HeightClass)
    height = spec.height
    if rng.chance(rules.anatomy.height_shift_chance):
        index = heights.index(height) + (1 if rng.chance(rules.anatomy.height_shift_up_pct) else -1)
        height = heights[max(0, min(len(heights) - 2, index))] if height is not HeightClass.GIANT else height
    strength = stat_or(bearer, "strength", DEFAULT_STAT)
    build = spec.build
    if spec.build is not BodyBuild.GIANT:
        build = (
            BodyBuild.HEAVY if strength >= rules.anatomy.heavy_build_strength else BodyBuild.SLIGHT if strength < rules.anatomy.slight_build_strength else build
        )
    return height, build


async def species_of(session: AsyncSession, mortal: EntityRow) -> EntityRow | None:
    for bond in await active_bonds(session, [BondKind.DESCENDS_FROM], sources=[mortal.id]):
        parent = await living_entity(session, bond.target_node_id)
        if parent is None:
            continue
        if parent.entity_type is EntityType.SPECIES:
            return parent
        if parent.entity_type in {EntityType.PEOPLE, EntityType.SETTLEMENT}:
            for lineage in await active_bonds(session, [BondKind.DESCENDS_FROM], sources=[parent.id]):
                ancestor = await living_entity(session, lineage.target_node_id)
                if ancestor is not None and ancestor.entity_type is EntityType.SPECIES:
                    return ancestor
    return None


def wild_plan(beast_id: int) -> BodyPlan:
    return SeededRandom.for_epoch(beast_id, 0, "monster_plan").pick(list(MONSTER_PLANS))


async def beast_plan(session: AsyncSession, beast: EntityRow) -> tuple[BodyPlan, list[str]]:
    profile = await session.get(BeastProfileRow, beast.id)
    species = await session.get(EntityRow, profile.species_entity_id) if profile is not None and profile.species_entity_id is not None else None
    if species is None:
        return wild_plan(beast.id), []
    known = await ensure_species_body(session, species)
    return known.plan, list(known.traits)


async def plan_for(session: AsyncSession, bearer: Bearer) -> tuple[BodyPlan, list[str]]:
    if not isinstance(bearer, EntityRow):
        return BodyPlan.DIVINE_MANIFEST, []
    if bearer.entity_type is EntityType.BEAST:
        return await beast_plan(session, bearer)
    if bearer.entity_type is EntityType.COSMIC_BEING:
        being = await session.get(CosmicBeingProfileRow, bearer.id)
        return (BEING_PLANS[being.being_kind] if being is not None else BodyPlan.COLOSSAL), []
    if bearer.entity_type is EntityType.OUTER_BEING:
        outer = await session.get(OuterBeingProfileRow, bearer.id)
        return (HUNGER_PLANS[outer.hunger] if outer is not None else BodyPlan.AMORPHOUS), []
    species = await species_of(session, bearer)
    if species is None:
        return BodyPlan.HUMANOID, []
    known = await ensure_species_body(session, species)
    return known.plan, list(known.traits)


VAST = frozenset({EntityType.COSMIC_BEING, EntityType.OUTER_BEING})
BODIED = frozenset({EntityType.MORTAL, EntityType.BEAST, EntityType.SPECIES, *VAST})


async def vast_hp(session: AsyncSession, rules: Rules, bearer: EntityRow) -> int:
    being = await session.get(CosmicBeingProfileRow, bearer.id)
    might: int = being.might if being is not None else stat_or(bearer, "influence", 50)
    return might * rules.cosmic_wounds.hp_per_might


async def ensure_body(session: AsyncSession, rules: Rules, bearer: Bearer, epoch: int) -> BodyRow:
    body = await session.get(BodyRow, bearer.id)
    if body is not None:
        return body
    if isinstance(bearer, EntityRow) and bearer.entity_type is EntityType.SPECIES:
        return await ensure_species_body(session, bearer)
    plan, traits = await plan_for(session, bearer)
    hp = bearer.hp if isinstance(bearer, SonRow) else (stat(bearer, "hp") if isinstance(bearer, EntityRow) else None)
    if isinstance(bearer, EntityRow) and bearer.entity_type in VAST:
        hp = await vast_hp(session, rules, bearer)
    floor = rules.world_effects.heir_hp
    height, build = mortal_frame(rules, bearer, plan) if isinstance(bearer, EntityRow) else (PLANS[plan].height, PLANS[plan].build)
    body = BodyRow(
        node_id=bearer.id,
        plan=plan,
        traits=traits,
        fingers=FINGER_COUNT,
        handedness=handedness_for(rules, bearer.id),
        hp_max=max(hp or 0, floor),
        updated_epoch=epoch,
        locked=[],
        height_class=height,
        build=build,
    )
    session.add(body)
    if isinstance(bearer, EntityRow) and bearer.entity_type in VAST and stat(bearer, "hp") is None:
        set_stats(bearer, hp=body.hp_max)
    await session.flush()
    return body


async def ensure_species_body(session: AsyncSession, species: EntityRow, plan: BodyPlan | None = None) -> BodyRow:
    body = await session.get(BodyRow, species.id)
    if body is not None:
        return body
    traits = await species_traits(session, species.id)
    functions = sorted(TRAIT_FUNCTIONS[trait].value for trait in traits if trait in TRAIT_FUNCTIONS)
    chosen = plan or await typed_plan(session, species, traits)
    body = BodyRow(
        node_id=species.id,
        plan=chosen,
        traits=functions,
        fingers=FINGER_COUNT,
        hp_max=0,
        locked=[],
        height_class=PLANS[chosen].height,
        build=PLANS[chosen].build,
    )
    session.add(body)
    await session.flush()
    return body


async def injuries_of(session: AsyncSession, node_id: int) -> list[InjuryRow]:
    rows = await session.scalars(select(InjuryRow).where(InjuryRow.bearer_node_id == node_id).order_by(InjuryRow.epoch, InjuryRow.id))
    return list(rows)


async def active_conditions(session: AsyncSession, node_id: int) -> list[ConditionRow]:
    rows = await session.scalars(
        select(ConditionRow).where(ConditionRow.bearer_node_id == node_id, ConditionRow.ended_epoch.is_(None)).order_by(ConditionRow.id)
    )
    return list(rows)


async def prostheses_of(session: AsyncSession, node_id: int) -> list[ProsthesisRow]:
    rows = await session.scalars(select(ProsthesisRow).where(ProsthesisRow.bearer_node_id == node_id).order_by(ProsthesisRow.id))
    return list(rows)


def wounds_from(injuries: list[InjuryRow], prostheses: list[ProsthesisRow]) -> tuple[Wound, ...]:
    restored = {row.injury_id: row.restored_pct for row in prostheses}
    counted = [row for row in injuries if row.state is not InjuryState.LETHAL]
    return tuple(Wound.of(row, restored.get(row.id, 0)) for row in counted if row.function_loss > 0)


def open_severity(injuries: list[InjuryRow]) -> int:
    return sum(row.severity for row in injuries if row.state in OPEN_INJURY_STATES)


@dataclass(frozen=True)
class Reading:
    presence_pct: int = PERCENT
    reader: bool = False
    hearing_aid: float = 0.0
    cane: float = 0.0
    magnifier: float = 0.0


async def metallurgy_of(session: AsyncSession, bearer_id: int, community_id: int | None) -> int:
    level = 0
    holders = [bearer_id, *([community_id] if community_id is not None else [])]
    for levels in (await known_levels(session, holders)).values():
        level = max(level, levels.get(KnowledgeBranch.METALLURGY, 0))
    return level


def aid_of(rules: Rules, anatomy: Anatomy, injuries: list[InjuryRow]) -> float:
    walking = {part.key for part in anatomy.with_function(BodyFunction.LOCOMOTION)}
    best = 0
    for row in injuries:
        if row.state not in OPEN_INJURY_STATES or row.part not in walking:
            continue
        if TreatmentStep.CRUTCH.value in row.treatments:
            best = max(best, rules.tissues.crutch_restore_pct)
        if TreatmentStep.TRACTION.value in row.treatments:
            best = max(best, rules.tissues.traction_restore_pct)
    return best / PERCENT


def consciousness_of(rules: Rules, bearer: Bearer, pain: int, blood: int) -> Consciousness:
    table = rules.tissues
    if blood <= table.blood_faint_at:
        return Consciousness.UNCONSCIOUS
    will = (stat(bearer, "willpower") if isinstance(bearer, EntityRow) else None) or PERCENT // 2
    felt = pain * (1 - will / PERCENT * table.pain_will_pct / PERCENT)
    if felt >= table.unconscious_at:
        return Consciousness.UNCONSCIOUS
    if felt >= table.dizzy_at:
        return Consciousness.DIZZY
    if felt >= table.nausea_at:
        return Consciousness.NAUSEOUS
    return Consciousness.AWAKE


def counts_of(body: BodyRow) -> dict[str, int]:
    return effective_counts(body)


async def armour_of(session: AsyncSession, rules: Rules, bearer: Bearer, community_id: int | None) -> Armour:
    table = rules.armour
    if not isinstance(bearer, EntityRow):
        return Armour(table.divine_head, table.divine_torso, table.divine_limbs)
    level = await metallurgy_of(session, bearer.id, community_id)
    head = min(table.coverage_cap, level * table.metallurgy_head_per_level)
    torso = min(table.coverage_cap, level * table.metallurgy_torso_per_level)
    limbs = min(table.coverage_cap, level * table.metallurgy_limbs_per_level)
    for bond in await active_bonds(session, [BondKind.OWNS], sources=[bearer.id]):
        item = await living_entity(session, bond.target_node_id)
        if item is None or item.entity_type is not EntityType.ITEM:
            continue
        tags = set(await session.scalars(select(EntityTagRow.tag).where(EntityTagRow.entity_id == item.id)))
        protection = stat(item, PROTECTION) or 0
        if ARMOUR_TAG in tags:
            torso = max(torso, min(table.coverage_cap, protection * table.armour_torso_pct // PERCENT))
            limbs = max(limbs, min(table.coverage_cap, protection * table.armour_limbs_pct // PERCENT))
            head = max(head, min(table.coverage_cap, protection * table.armour_head_pct // PERCENT))
        if SHIELD_TAG in tags:
            limbs = max(limbs, min(table.coverage_cap, protection * table.shield_limbs_pct // PERCENT))
            torso = max(torso, min(table.coverage_cap, protection * table.shield_torso_pct // PERCENT))
    guard = guard_of(await held_profiles(session, bearer.id), rules.item_wear.broken) * table.armour_torso_pct // PERCENT
    worn = await worn_coverage(session, bearer.id)
    if worn is not None:
        head = max(head, min(table.coverage_cap, worn[0] * table.armour_head_pct // PERCENT))
        torso = max(torso, min(table.coverage_cap, worn[1] * table.armour_torso_pct // PERCENT))
    return Armour(head, min(table.coverage_cap, max(torso, guard)), limbs)


def afflicted_parts(rules: Rules, conditions: list[ConditionRow]) -> tuple[tuple[str, int], ...]:
    loss = rules.epidemiology.chronic_function_loss_pct
    return tuple(
        (row.part, min(PERCENT, row.severity * loss))
        for row in conditions
        if row.kind is ConditionKind.CHRONIC_ILLNESS and row.part and row.ended_epoch is None
    )


def factors_of(
    rules: Rules,
    bearer: Bearer,
    body: BodyRow,
    *,
    injuries: list[InjuryRow],
    prostheses: list[ProsthesisRow],
    conditions: list[ConditionRow],
    reading: Reading,
    variant_scale: dict[int, float] | None = None,
) -> dict[Capacity, int]:
    stats = bearer_stats(bearer)
    anatomy = anatomy_for(body)
    scales = variant_scale or {}
    variant_scales = {row.id: scales[row.variant_id] for row in conditions if row.variant_id is not None and row.variant_id in scales}
    state = BodyState(
        anatomy,
        wounds_from(injuries, prostheses),
        counts_of(body),
        open_severity(injuries),
        tuple((row.kind, row.severity * variant_scales.get(row.id, 1.0)) for row in conditions),
        reading.presence_pct,
        reading.reader,
        afflicted_parts(rules, conditions),
        body.consciousness,
        body.exertion,
        max(aid_of(rules, anatomy, injuries), reading.cane),
        tuple(body.lost_digits),
        body.handedness,
        reading.hearing_aid,
        reading.magnifier,
    )
    actual = capacities(rules, stats, state)
    whole = capacities(rules, replace(stats, age=None), BodyState(anatomy, (), FULL_COUNTS, 0))
    factors = {capacity: round(actual[capacity] * PERCENT / whole[capacity]) if whole[capacity] else PERCENT for capacity in Capacity}
    if bedridden(rules, bearer):
        factors.update(dict.fromkeys(BEDRIDDEN_LOSSES, 0))
    return factors


BEDRIDDEN_LOSSES = (Capacity.MELEE, Capacity.MISSILE, Capacity.COMMAND, Capacity.MOBILITY, Capacity.CRAFT)


async def function_level(session: AsyncSession, rules: Rules, node_id: int | None, function: BodyFunction) -> int:
    if node_id is None:
        return 0
    body = await session.get(BodyRow, node_id)
    if body is None:
        return 0
    anatomy = anatomy_for(body)
    if not anatomy.with_function(function):
        return 0
    injuries = await injuries_of(session, node_id)
    state = BodyState(anatomy, wounds_from(injuries, await prostheses_of(session, node_id)), counts_of(body), open_severity(injuries))
    return function_percents(rules, state)[function] if function in FUNCTION_LEVELS else PERCENT


async def function_unhindered(session: AsyncSession, rules: Rules, node_id: int, function: BodyFunction) -> int:
    lift = await bonus(session, node_id, EffectTarget.CAPACITY, function.value)
    if await session.get(BodyRow, node_id) is None:
        return PERCENT + max(0, lift)
    return max(0, await function_level(session, rules, node_id, function) + lift)


async def perception_of(session: AsyncSession, rules: Rules, mortal: EntityRow) -> float:
    base = stat_or(mortal, "perception", DEFAULT_STAT)
    body = await session.get(BodyRow, mortal.id)
    if body is None:
        return float(base)
    return base * perception_factor(rules.capacities, body.hearing, body.sight)


def bedridden(rules: Rules, bearer: object) -> bool:
    if not isinstance(bearer, EntityRow) or bearer.entity_type is not EntityType.MORTAL:
        return False
    hp = stat(bearer, "hp")
    return hp is not None and 0 < hp < rules.capacities.bedridden_hp


async def factor(session: AsyncSession, node_id: int, capacity: Capacity) -> float:
    body = await session.get(BodyRow, node_id)
    if body is None:
        return 1.0
    value: int = getattr(body, capacity.value)
    return value / PERCENT


async def strike_style(session: AsyncSession, rules: Rules, attacker: EntityRow | None, defender: Bearer | None = None) -> StrikeStyle:
    if attacker is None:
        return StrikeStyle.NORMAL
    traits = await species_traits(session, attacker.id)
    found = next((style for trait, style in TRAIT_STYLES if trait in traits), None)
    if found is not None:
        return found
    body = await session.get(BodyRow, attacker.id)
    if body is None and attacker.entity_type is EntityType.MORTAL:
        body = await ensure_body(session, rules, attacker, attacker.birth_epoch)
    if body is not None and body.plan is BodyPlan.AMORPHOUS:
        return StrikeStyle.ENGULFING
    if body is not None and body.plan in WHOLE_PLANS:
        return StrikeStyle.WHOLE
    target = await session.get(BodyRow, defender.id) if defender is not None else None
    sized = frame_style(rules, size_of(body), target) if body is not None and target is not None else StrikeStyle.NORMAL
    if sized is not StrikeStyle.NORMAL:
        return sized
    huge = (body is not None and body.plan is BodyPlan.COLOSSAL) or (stat(attacker, "danger") or 0) >= rules.anatomy.trample_danger
    return StrikeStyle.TRAMPLE if huge else StrikeStyle.NORMAL


TRAIT_STYLES = (
    (CreatureTrait.FLYING, StrikeStyle.AERIAL),
    (CreatureTrait.BURROWING, StrikeStyle.BURROWING),
    (CreatureTrait.AMBUSH_PREDATOR, StrikeStyle.FROM_HIDING),
    (CreatureTrait.CAMOUFLAGE, StrikeStyle.FROM_HIDING),
    (CreatureTrait.FIRE_BREATHING, StrikeStyle.RANGED),
    (CreatureTrait.COLD_BREATHING, StrikeStyle.RANGED),
)
AVERAGE_SIZE = HEIGHT_RANK[HeightClass.AVERAGE] + BUILD_RANK[BodyBuild.AVERAGE]


async def blow_style(session: AsyncSession, rules: Rules, attacker: EntityRow | None, defender: Bearer) -> StrikeStyle:
    if attacker is not None:
        return await strike_style(session, rules, attacker, defender)
    target = await ensure_body(session, rules, defender, 0)
    return frame_style(rules, AVERAGE_SIZE, target)


def frame_style(rules: Rules, attacker_size: int, target: BodyRow) -> StrikeStyle:
    gap = attacker_size - size_of(target)
    if gap >= rules.anatomy.size_gap_style:
        return StrikeStyle.TRAMPLE
    if gap <= -rules.anatomy.size_gap_style:
        return StrikeStyle.LOW
    return StrikeStyle.NORMAL


BODY_SOURCES = frozenset({ModifierSource.INJURY, ModifierSource.TRAIT})
STAT_CAPACITY: dict[str, Capacity] = {
    "strength": Capacity.MELEE,
    "agility": Capacity.MOBILITY,
    "intellect": Capacity.SCHOLARSHIP,
    "charisma": Capacity.PRESENCE,
}


def temperament_factor(rules: Rules, held: Iterable[tuple[TraitKind, float]], capacity: Capacity) -> float:
    lift = sum(TRAITS[trait].capacities.get(capacity, 0) * scale for trait, scale in held) * rules.traits.capacity_scale_pct / PERCENT
    return max(0.0, (PERCENT + lift) / PERCENT)


async def held_temperament(session: AsyncSession, node_ids: Iterable[int]) -> dict[int, list[tuple[TraitKind, float]]]:
    rows = list(await session.scalars(select(TraitRow).where(TraitRow.node_id.in_(list(node_ids))).order_by(TraitRow.node_id, TraitRow.trait)))
    variants = await variants_by_id(session, (row.variant_id for row in rows))
    held: dict[int, list[tuple[TraitKind, float]]] = {}
    for row in rows:
        held.setdefault(row.node_id, []).append((row.trait, strength(variants, row.variant_id)))
    return held


async def temperament(session: AsyncSession, rules: Rules, node_id: int, capacity: Capacity) -> float:
    return temperament_factor(rules, (await held_temperament(session, (node_id,))).get(node_id, []), capacity)


async def training(session: AsyncSession, rules: Rules, node_id: int, capacity: Capacity) -> float:
    wanted = [skill for skill, spec in SKILLS.items() if spec.capacity is capacity]
    rows = list(
        await session.scalars(select(SkillRow).where(SkillRow.holder_node_id == node_id, SkillRow.skill.in_(wanted), SkillRow.subject_node_id.is_(None)))
    )
    variants = await variants_by_id(session, (row.variant_id for row in rows))
    best = max((row.level * strength(variants, row.variant_id) for row in rows), default=0)
    return 1 + best * rules.skills.capacity_skill_pct / PERCENT / PERCENT


async def effective(
    session: AsyncSession, mortal: EntityRow, key: str, default: int = 0, capacity: Capacity | None = None, *, rules: Rules | None = None
) -> float:
    contributions = live_contributions(mortal.id, key)
    held = {item.source_kind for item in contributions if item.held and item.source_kind in BODY_SOURCES}
    kept = [item for item in contributions if item.source_kind not in BODY_SOURCES or item.held]
    raw = base_stat(mortal, key)
    value = raw if raw is None or not contributions else clamp_to_field(mortal, key, combine(raw, kept).value)
    base = default if value is None else value
    use = capacity or STAT_CAPACITY[key]
    result = base if ModifierSource.INJURY in held else base * await factor(session, mortal.id, use)
    if rules is not None:
        mood = 1.0 if ModifierSource.TRAIT in held else await temperament(session, rules, mortal.id, use)
        result *= mood * await training(session, rules, mortal.id, use)
    return result
