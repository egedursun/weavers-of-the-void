from dataclasses import dataclass, replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.anatomy import FINGER_COUNT, Anatomy, anatomy_of
from aerona.constants.units import PERCENT
from aerona.db.tables.body import BodyRow, ConditionRow, InjuryRow, ProsthesisRow
from aerona.db.tables.entities import EntityRow, EntityTagRow, EntityTraitRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.body import OPEN_INJURY_STATES, BodyFunction, BodyPlan, Capacity, InjuryState, StrikeStyle
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.society import CreatureTrait, KnowledgeBranch
from aerona.engine.body.capacities import BearerStats, BodyState, capacities
from aerona.engine.body.functions import Wound
from aerona.engine.body.hits import Armour
from aerona.engine.primitives.knowledge import known_levels
from aerona.engine.primitives.queries import active_bonds, living_entity
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

Bearer = EntityRow | SonRow | ForeignGodRow

ARMOUR_TAG = "armour"
SHIELD_TAG = "shield"
PROTECTION = "protection"
DEFAULT_STAT = 50

TRAIT_FUNCTIONS: dict[CreatureTrait, BodyFunction] = {CreatureTrait.FLYING: BodyFunction.FLIGHT, CreatureTrait.VENOMOUS: BodyFunction.VENOM}
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
            endurance=agility,
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
    body = BodyRow(node_id=bearer.id, plan=plan, traits=traits, fingers=FINGER_COUNT, hp_max=max(hp or 0, floor), updated_epoch=epoch, locked=[])
    session.add(body)
    await session.flush()
    return body


async def ensure_species_body(session: AsyncSession, species: EntityRow) -> BodyRow:
    body = await session.get(BodyRow, species.id)
    if body is not None:
        return body
    traits = await species_traits(session, species.id)
    functions = sorted(TRAIT_FUNCTIONS[trait].value for trait in traits if trait in TRAIT_FUNCTIONS)
    body = BodyRow(node_id=species.id, plan=plan_from_traits(traits), traits=functions, fingers=FINGER_COUNT, hp_max=0, locked=[])
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
    return Armour(head, torso, limbs)


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
    return {capacity: round(actual[capacity] * PERCENT / whole[capacity]) if whole[capacity] else PERCENT for capacity in Capacity}


async def factor(session: AsyncSession, node_id: int, capacity: Capacity) -> float:
    body = await session.get(BodyRow, node_id)
    if body is None:
        return 1.0
    value: int = getattr(body, capacity.value)
    return value / PERCENT


async def scaled(session: AsyncSession, node_id: int, value: float, capacity: Capacity) -> float:
    return value * await factor(session, node_id, capacity)


async def strike_style(session: AsyncSession, rules: Rules, attacker: EntityRow | None) -> StrikeStyle:
    if attacker is None:
        return StrikeStyle.NORMAL
    traits = await species_traits(session, attacker.id)
    if CreatureTrait.FLYING in traits:
        return StrikeStyle.AERIAL
    body = await session.get(BodyRow, attacker.id)
    if body is not None and body.plan is BodyPlan.COLOSSAL:
        return StrikeStyle.TRAMPLE
    danger = stat(attacker, "danger") or 0
    return StrikeStyle.TRAMPLE if danger >= rules.anatomy.trample_danger else StrikeStyle.NORMAL


STAT_CAPACITY: dict[str, Capacity] = {
    "strength": Capacity.MELEE,
    "agility": Capacity.MOBILITY,
    "intellect": Capacity.SCHOLARSHIP,
    "charisma": Capacity.PRESENCE,
}


async def effective(session: AsyncSession, mortal: EntityRow, key: str, default: int = 0, capacity: Capacity | None = None) -> float:
    value = stat(mortal, key)
    base = default if value is None else value
    return base * await factor(session, mortal.id, capacity or STAT_CAPACITY[key])
