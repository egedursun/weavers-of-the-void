import math
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.creatures import trait_war_bonus
from aerona.constants.units import PERCENT
from aerona.constants.warfare import LOG_FLOOR
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.sons import SonPowerRow, SonRow
from aerona.domain.enums.body import Capacity
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.domain.enums.son import PowerEffect
from aerona.engine.body.book import factor
from aerona.engine.primitives.faith import patron_son
from aerona.engine.primitives.knowledge import KnowledgeMap, known_levels, level_multiplier
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.physics import PhysicsTable
from aerona.engine.primitives.queries import active_bonds, living_entity
from aerona.engine.primitives.society import class_shares
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

PHYSICS_WAR_TYPES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.FACTION})
WARRIOR_CLASS_TYPES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT})
FALLBACK_STRENGTH_KEYS = ("strength", "martiality", "defense")


@dataclass(frozen=True)
class PatronBonus:
    son: SonRow | None
    bonus: int


async def has_power(session: AsyncSession, son_id: int, effect: PowerEffect) -> bool:
    statement = select(SonPowerRow.son_id).where(SonPowerRow.son_id == son_id, SonPowerRow.effect == effect).limit(1)
    return await session.scalar(statement) is not None


async def patron_bonus(session: AsyncSession, rules: Rules, entity: EntityRow) -> PatronBonus:
    patron = await patron_son(session, entity)
    if patron is None:
        return PatronBonus(None, 0)
    strength = rules.world_war_strength
    multiplier = strength.war_father_mult if await has_power(session, patron.id, PowerEffect.WAR_FATHER) else 1
    return PatronBonus(patron, round_half_up(patron.strength / strength.patron_strength_divisor * multiplier))


async def equipment(session: AsyncSession, entity_id: int) -> list[EntityRow]:
    items: list[EntityRow] = []
    for bond in await active_bonds(session, [BondKind.OWNS], sources=[entity_id]):
        item = await living_entity(session, bond.target_node_id)
        if item is not None and item.entity_type is EntityType.ITEM:
            items.append(item)
    return items


def item_power(rules: Rules, item: EntityRow) -> float:
    strength = rules.world_war_strength
    return (
        (stat(item, "damage") or 0) / strength.weapon_damage_divisor
        + (stat(item, "protection") or 0) / strength.armor_protection_divisor
        + (stat(item, "might") or 0) / strength.item_might_divisor
    )


async def weapon_power(session: AsyncSession, rules: Rules, entity_id: int, multiplier: float = 1.0) -> int:
    return round_half_up(sum(item_power(rules, item) for item in await equipment(session, entity_id)) * multiplier)


async def species_trait_bonus(session: AsyncSession, rules: Rules, entity_id: int) -> int:
    return sum(trait_war_bonus(rules, trait) for trait in await EntityRepository(session).traits(entity_id))


async def tamed_power(session: AsyncSession, rules: Rules, entity_id: int) -> int:
    creatures = rules.creatures
    total = 0.0
    for bond in await active_bonds(session, [BondKind.TAMED], sources=[entity_id]):
        creature = await living_entity(session, bond.target_node_id)
        if creature is None or creature.entity_type is not EntityType.SPECIES:
            continue
        creature_strength = stat(creature, "strength")
        base_strength = creature_strength if creature_strength is not None else creatures.tamed_default_strength
        traits = await species_trait_bonus(session, rules, creature.id)
        total += creatures.tamed_war_base + round_half_up(base_strength / creatures.tamed_strength_divisor) + traits * creatures.tamed_trait_share_pct / PERCENT
    return round_half_up(total)


def _value(entity: EntityRow, key: str, default: int) -> int:
    value = stat(entity, key)
    return default if value is None else value


def _cult_base(rules: Rules, entity: EntityRow) -> float:
    strength = rules.world_war_strength
    followers = stat(entity, "followers") or 0
    zeal = _value(entity, "zeal", strength.default_zealotry) * strength.cult_zealotry_coeff_pct / PERCENT
    return zeal + math.log10(max(LOG_FLOOR, followers)) * strength.cult_follower_log_coeff


def _faction_base(rules: Rules, entity: EntityRow) -> float:
    strength = rules.world_war_strength
    default = strength.default_stat
    return _value(entity, "strength", default) + _value(entity, "sway", default) * strength.faction_sway_coeff_pct / PERCENT


def _people_base(rules: Rules, entity: EntityRow) -> float:
    return _value(entity, "martiality", rules.world_war_strength.default_stat)


def _settlement_base(rules: Rules, entity: EntityRow) -> float:
    strength = rules.world_war_strength
    return _value(entity, "defense", strength.default_stat) * strength.settlement_defense_coeff_pct / PERCENT


def _mortal_base(rules: Rules, entity: EntityRow) -> float:
    strength = rules.world_war_strength
    return _value(entity, "strength", strength.default_stat) + _value(entity, "agility", strength.default_stat) / strength.mortal_agility_divisor


def _species_base(rules: Rules, entity: EntityRow) -> float:
    strength = rules.world_war_strength
    return _value(entity, "danger", strength.default_stat) + (stat(entity, "strength") or 0) / strength.species_strength_divisor


def _other_base(rules: Rules, entity: EntityRow) -> float:
    return next((value for key in FALLBACK_STRENGTH_KEYS if (value := stat(entity, key)) is not None), rules.world_war_strength.default_stat)


BASE_STRENGTH: dict[EntityType, Callable[[Rules, EntityRow], float]] = {
    EntityType.CULT: _cult_base,
    EntityType.FACTION: _faction_base,
    EntityType.PEOPLE: _people_base,
    EntityType.SETTLEMENT: _settlement_base,
    EntityType.MORTAL: _mortal_base,
    EntityType.SPECIES: _species_base,
}


async def _base_strength(session: AsyncSession, rules: Rules, entity: EntityRow) -> float:
    strength = rules.world_war_strength
    base = BASE_STRENGTH.get(entity.entity_type, _other_base)(rules, entity)
    if entity.entity_type is EntityType.MORTAL:
        base *= await factor(session, entity.id, Capacity.MELEE)
    if entity.entity_type in WARRIOR_CLASS_TYPES:
        shares = await class_shares(session, rules, entity.id)
        base += (shares[SocialClass.WARRIOR] - strength.warrior_threshold_pct) * strength.warrior_coeff_pct / PERCENT
    return base


async def military_strength(session: AsyncSession, rules: Rules, entity: EntityRow, physics: PhysicsTable | None = None) -> float:
    strength = rules.world_war_strength
    total = await _base_strength(session, rules, entity)
    total += await weapon_power(session, rules, entity.id)
    levels = (await known_levels(session, [entity.id])).get(entity.id, {})
    total += strength.warcraft_bonus * level_multiplier(rules.knowledge, levels.get(KnowledgeBranch.WARFARE, 0))
    if KnowledgeBranch.FORBIDDEN in levels:
        total += strength.forbidden_knowledge_bonus
    total += (entity.civ_tier or 0) * strength.civilization_stage_bonus
    total += await tamed_power(session, rules, entity.id)
    if entity.entity_type is EntityType.SPECIES:
        total += await species_trait_bonus(session, rules, entity.id)
    if entity.entity_type in PHYSICS_WAR_TYPES:
        table = physics or await PhysicsTable.load(session, rules)
        total += table.of(entity.world_id).war
    return total


async def ally_strength(session: AsyncSession, rules: Rules, entity: EntityRow) -> float:
    total = 0.0
    for bond in await active_bonds(session, [BondKind.ALLY], sources=[entity.id]) + await active_bonds(session, [BondKind.ALLY], targets=[entity.id]):
        ally = await living_entity(session, bond.other_end(entity.id))
        if ally is not None and ally.status is EntityStatus.CANON:
            total += await military_strength(session, rules, ally) * rules.world_war_strength.ally_share_pct / PERCENT
    return total


class MilitaryStrength:
    def __init__(self, session: AsyncSession, rules: Rules, knowledge: KnowledgeMap, physics: PhysicsTable, warrior_shares: dict[int, float]) -> None:
        self._session = session
        self._rules = rules
        self._knowledge = knowledge
        self._physics = physics
        self._warrior_shares = warrior_shares
        self._patrons: dict[int, PatronBonus] = {}
        self._weapons: dict[tuple[int, float], int] = {}

    @classmethod
    async def load(cls, session: AsyncSession, rules: Rules) -> "MilitaryStrength":
        shares = {row.entity_id: row.share_warrior for row in await session.scalars(select(CommunitySocietyRow))}
        return cls(session, rules, await KnowledgeMap.load(session), await PhysicsTable.load(session, rules), shares)

    def warrior_share(self, entity: EntityRow) -> float:
        return self._warrior_shares.get(entity.id, float(self._rules.society.class_warrior_pct))

    def knows(self, entity_id: int, branch: KnowledgeBranch) -> bool:
        return self._knowledge.knows(entity_id, branch)

    async def power(self, entity: EntityRow) -> float:
        return await military_strength(self._session, self._rules, entity, self._physics)

    async def ally_power(self, entity: EntityRow) -> float:
        return await ally_strength(self._session, self._rules, entity)

    async def weapon_power(self, entity: EntityRow, multiplier: float = 1) -> int:
        key = (entity.id, multiplier)
        if key not in self._weapons:
            self._weapons[key] = await weapon_power(self._session, self._rules, entity.id, multiplier)
        return self._weapons[key]

    async def patron_bonus(self, entity: EntityRow) -> PatronBonus:
        if entity.id not in self._patrons:
            self._patrons[entity.id] = await patron_bonus(self._session, self._rules, entity)
        return self._patrons[entity.id]
