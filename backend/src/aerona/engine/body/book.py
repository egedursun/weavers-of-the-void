import re
from dataclasses import dataclass, replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.anatomy import FINGER_COUNT, Anatomy, anatomy_of
from aerona.catalog.body_plans import BUILD_RANK, HEIGHT_RANK, PLANS, WHOLE_PLANS
from aerona.catalog.mind import SKILLS, TRAITS
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.body import BodyRow, ConditionRow, InjuryRow, ProsthesisRow
from aerona.db.tables.ecology import SpeciesProfileRow
from aerona.db.tables.entities import EntityRow, EntityTagRow, EntityTraitRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.mind import SkillRow, TraitRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.body import OPEN_INJURY_STATES, BodyBuild, BodyFunction, BodyPlan, Capacity, HeightClass, InjuryState, StrikeStyle
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.society import CreatureTrait, KnowledgeBranch
from aerona.engine.body.capacities import FUNCTION_LEVELS, BearerStats, BodyState, capacities, function_percents, perception_factor
from aerona.engine.body.functions import Wound
from aerona.engine.body.hits import Armour
from aerona.engine.lore.arms import guard_of, held_profiles
from aerona.engine.primitives.knowledge import known_levels
from aerona.engine.primitives.queries import active_bonds, living_entity
from aerona.engine.primitives.stats import stat
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


def is_bearer(node: object) -> bool:
    if isinstance(node, EntityRow):
        return node.entity_type is EntityType.MORTAL
    return isinstance(node, SonRow | ForeignGodRow)


def bearer_stats(bearer: Bearer) -> BearerStats:
    if isinstance(bearer, EntityRow):
        agility = stat(bearer, "agility") or DEFAULT_STAT
        return BearerStats(
            strength=stat(bearer, "strength") or DEFAULT_STAT,
            agility=agility,
            intellect=stat(bearer, "intellect") or DEFAULT_STAT,
            charisma=stat(bearer, "charisma") or DEFAULT_STAT,
            endurance=stat(bearer, "endurance") or agility,
            age=stat(bearer, "age"),
            lifespan=stat(bearer, "lifespan"),
        )
    return BearerStats(bearer.strength, bearer.agility, bearer.wisdom, bearer.charisma, bearer.endurance)


def anatomy_for(body: BodyRow) -> Anatomy:
    return anatomy_of(body.plan, frozenset(BodyFunction(trait) for trait in body.traits))


async def species_traits(session: AsyncSession, species_id: int) -> set[CreatureTrait]:
    rows = await session.scalars(select(EntityTraitRow.trait).where(EntityTraitRow.entity_id == species_id))
    return set(rows)


def plan_from_traits(traits: set[CreatureTrait]) -> BodyPlan:
    return next((plan for trait, plan in TRAIT_PLANS if trait in traits), BodyPlan.QUADRUPED)


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
    strength = stat(bearer, "strength") or DEFAULT_STAT
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


async def plan_for(session: AsyncSession, bearer: Bearer) -> tuple[BodyPlan, list[str]]:
    if not isinstance(bearer, EntityRow):
        return BodyPlan.DIVINE_MANIFEST, []
    species = await species_of(session, bearer)
    if species is None:
        return BodyPlan.HUMANOID, []
    known = await ensure_species_body(session, species)
    return known.plan, list(known.traits)


async def ensure_body(session: AsyncSession, rules: Rules, bearer: Bearer, epoch: int) -> BodyRow:
    body = await session.get(BodyRow, bearer.id)
    if body is not None:
        return body
    if isinstance(bearer, EntityRow) and bearer.entity_type is EntityType.SPECIES:
        return await ensure_species_body(session, bearer)
    plan, traits = await plan_for(session, bearer)
    hp = bearer.hp if isinstance(bearer, SonRow) else (stat(bearer, "hp") if isinstance(bearer, EntityRow) else None)
    floor = rules.world_effects.heir_hp
    height, build = mortal_frame(rules, bearer, plan) if isinstance(bearer, EntityRow) else (PLANS[plan].height, PLANS[plan].build)
    body = BodyRow(
        node_id=bearer.id,
        plan=plan,
        traits=traits,
        fingers=FINGER_COUNT,
        hp_max=max(hp or 0, floor),
        updated_epoch=epoch,
        locked=[],
        height_class=height,
        build=build,
    )
    session.add(body)
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


async def armour_of(session: AsyncSession, rules: Rules, bearer: Bearer, community_id: int | None) -> Armour:
    table = rules.armour
    if not isinstance(bearer, EntityRow):
        return Armour(table.divine_head, table.divine_torso, table.divine_limbs)
    level = 0
    holders = [bearer.id, *([community_id] if community_id is not None else [])]
    for levels in (await known_levels(session, holders)).values():
        level = max(level, levels.get(KnowledgeBranch.METALLURGY, 0))
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
    guard = guard_of(await held_profiles(session, bearer.id)) * table.armour_torso_pct // PERCENT
    return Armour(head, min(table.coverage_cap, max(torso, guard)), limbs)


def factors_of(
    rules: Rules, bearer: Bearer, body: BodyRow, *, injuries: list[InjuryRow], prostheses: list[ProsthesisRow], conditions: list[ConditionRow], reading: Reading
) -> dict[Capacity, int]:
    stats = bearer_stats(bearer)
    anatomy = anatomy_for(body)
    state = BodyState(
        anatomy,
        wounds_from(injuries, prostheses),
        body.fingers,
        open_severity(injuries),
        tuple((row.kind, row.severity) for row in conditions),
        reading.presence_pct,
        reading.reader,
    )
    actual = capacities(rules, stats, state)
    whole = capacities(rules, replace(stats, age=None), BodyState(anatomy, (), FINGER_COUNT, 0))
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
    state = BodyState(anatomy, wounds_from(injuries, await prostheses_of(session, node_id)), body.fingers, open_severity(injuries))
    return function_percents(rules, state)[function] if function in FUNCTION_LEVELS else PERCENT


async def perception_of(session: AsyncSession, rules: Rules, mortal: EntityRow) -> float:
    base = stat(mortal, "perception") or DEFAULT_STAT
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


async def scaled(session: AsyncSession, node_id: int, value: float, capacity: Capacity) -> float:
    return value * await factor(session, node_id, capacity)


async def strike_style(session: AsyncSession, rules: Rules, attacker: EntityRow | None, defender: Bearer | None = None) -> StrikeStyle:
    if attacker is None:
        return StrikeStyle.NORMAL
    if CreatureTrait.FLYING in await species_traits(session, attacker.id):
        return StrikeStyle.AERIAL
    body = await session.get(BodyRow, attacker.id)
    if body is None and attacker.entity_type is EntityType.MORTAL:
        body = await ensure_body(session, rules, attacker, attacker.birth_epoch)
    if body is not None and body.plan in WHOLE_PLANS:
        return StrikeStyle.WHOLE
    target = await session.get(BodyRow, defender.id) if defender is not None else None
    sized = frame_style(rules, size_of(body), target) if body is not None and target is not None else StrikeStyle.NORMAL
    if sized is not StrikeStyle.NORMAL:
        return sized
    huge = (body is not None and body.plan is BodyPlan.COLOSSAL) or (stat(attacker, "danger") or 0) >= rules.anatomy.trample_danger
    return StrikeStyle.TRAMPLE if huge else StrikeStyle.NORMAL


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


STAT_CAPACITY: dict[str, Capacity] = {
    "strength": Capacity.MELEE,
    "agility": Capacity.MOBILITY,
    "intellect": Capacity.SCHOLARSHIP,
    "charisma": Capacity.PRESENCE,
}


async def temperament(session: AsyncSession, rules: Rules, node_id: int, capacity: Capacity) -> float:
    held = await session.scalars(select(TraitRow.trait).where(TraitRow.node_id == node_id))
    lift = sum(TRAITS[trait].capacities.get(capacity, 0) for trait in held) * rules.traits.capacity_scale_pct / PERCENT
    return max(0.0, (PERCENT + lift) / PERCENT)


async def training(session: AsyncSession, rules: Rules, node_id: int, capacity: Capacity) -> float:
    wanted = [skill for skill, spec in SKILLS.items() if spec.capacity is capacity]
    levels = await session.scalars(
        select(SkillRow.level).where(SkillRow.holder_node_id == node_id, SkillRow.skill.in_(wanted), SkillRow.subject_node_id.is_(None))
    )
    return 1 + max(levels, default=0) * rules.skills.capacity_skill_pct / PERCENT / PERCENT


async def effective(
    session: AsyncSession, mortal: EntityRow, key: str, default: int = 0, capacity: Capacity | None = None, *, rules: Rules | None = None
) -> float:
    value = stat(mortal, key)
    base = default if value is None else value
    use = capacity or STAT_CAPACITY[key]
    result = base * await factor(session, mortal.id, use)
    if rules is not None:
        result *= await temperament(session, rules, mortal.id, use) * await training(session, rules, mortal.id, use)
    return result
