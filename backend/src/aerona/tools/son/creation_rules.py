import re
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.constants.agents import FILLER_WORDS
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonPowerRow, SonRow
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.son import PowerEffect
from aerona.engine.primitives.faith import has_unlocked_power
from aerona.rules.registry import Rules

PERCENT = 100


def base_cost(rules: Rules, entity_type: EntityType) -> int:
    value: int = getattr(rules.creation_base_cost, entity_type.value)
    return value


def creation_cost(rules: Rules, base: int, power: int, *, in_domain: bool, creativity: int, cheap: bool) -> int:
    core = rules.core_rules
    domain = (core.cost_in_domain_pct if in_domain else core.cost_out_of_domain_pct) / PERCENT
    creative = 1 - (creativity / PERCENT) * (core.creativity_discount_pct / PERCENT)
    discount = core.cheap_power_cost_pct / PERCENT if cheap else 1
    return max(1, round((base + core.cost_per_power_level * power) * domain * creative * discount))


async def cheap_creation(session: AsyncSession, rules: Rules, son: SonRow, entity_type: EntityType) -> bool:
    if entity_type is EntityType.PROPHECY and await has_unlocked_power(session, rules, son, PowerEffect.SEER):
        return True
    if not await has_unlocked_power(session, rules, son, PowerEffect.CHEAP_CREATION):
        return False
    statement = select(SonPowerRow.param_entity_type).where(SonPowerRow.son_id == son.id, SonPowerRow.effect == PowerEffect.CHEAP_CREATION)
    return entity_type in set(await session.scalars(statement))


async def star_domain(session: AsyncSession, world_id: int | None) -> Domain | None:
    world = await session.get(WorldRow, world_id) if world_id is not None else None
    star = await session.get(EntityRow, world.epoch_star_entity_id) if world is not None and world.epoch_star_entity_id is not None else None
    return star.domain if star is not None else None


def repeat_multiplier(rules: Rules, repeats: int) -> float:
    tools = rules.son_tools
    return min(tools.repeat_cost_cap_pct / PERCENT, 1 + tools.repeat_cost_increase_pct / PERCENT * repeats)


@dataclass(frozen=True)
class CostBreakdown:
    total: int
    in_domain: bool
    cheap: bool
    starred: bool
    repeat_multiplier: float


def final_cost(rules: Rules, base: int, starred: bool, repeats: float) -> int:
    star = rules.son_tools.star_domain_cost_pct / PERCENT if starred else 1
    return max(1, round(base * star * repeats))


WORD = re.compile(r"[^\W\d_]+")


def roots(text: str | None, letters: int, exclude: frozenset[str] = frozenset()) -> set[str]:
    words = (word.casefold() for word in WORD.findall(text or ""))
    return {word[:letters] for word in words if len(word) >= letters and word not in FILLER_WORDS and word[:letters] not in exclude}


def similarity(first: set[str], second: set[str]) -> int:
    if not first or not second:
        return 0
    shared = len(first & second)
    return round(PERCENT * shared / (len(first) + len(second) - shared))


@dataclass(frozen=True)
class RepeatQuery:
    son_id: int
    entity_type: EntityType
    subtype: str
    description: str
    name: str
    epoch: int


async def similar_creations(session: AsyncSession, rules: Rules, query: RepeatQuery) -> list[EntityRow]:
    tools = rules.son_tools
    letters = tools.repeat_root_letters
    type_words = frozenset(
        word[:letters] for word in (query.entity_type.value.replace("_", " ") + " " + ENTITY_TYPES[query.entity_type].label).casefold().split()
    )
    subtype_roots = roots(query.subtype, letters, type_words)
    theme = roots(query.description, letters, type_words | frozenset(roots(query.name, letters)))
    statement = select(EntityRow).where(
        EntityRow.creator_son_id == query.son_id,
        EntityRow.origin == EntityOrigin.SON,
        EntityRow.entity_type == query.entity_type,
        EntityRow.birth_epoch >= query.epoch - tools.repeat_window_epochs,
        EntityRow.status != EntityStatus.REJECTED,
    )
    found: list[EntityRow] = []
    for other in await session.scalars(statement.order_by(EntityRow.id)):
        same = query.subtype and (other.subtype or "").casefold() == query.subtype.casefold()
        shared_root = bool(subtype_roots & roots(other.subtype, letters, type_words))
        themed = similarity(theme, roots(other.description, letters, type_words | frozenset(roots(other.name, letters)))) >= tools.repeat_similarity_pct
        if same or shared_root or themed:
            found.append(other)
    return found


async def same_type_this_epoch(session: AsyncSession, son_id: int, entity_type: EntityType, epoch: int, exclude_id: int) -> int:
    statement = select(func.count(EntityRow.id)).where(
        EntityRow.creator_son_id == son_id,
        EntityRow.origin == EntityOrigin.SON,
        EntityRow.entity_type == entity_type,
        EntityRow.birth_epoch == epoch,
        EntityRow.status != EntityStatus.REJECTED,
        EntityRow.id != exclude_id,
    )
    return int(await session.scalar(statement) or 0)
