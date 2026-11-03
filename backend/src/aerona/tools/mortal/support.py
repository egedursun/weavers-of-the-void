from collections.abc import Callable, Collection, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import NoReturn

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.body import Capacity
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, CivilizationTier, EngineKind, EntityOrigin, EntityStatus, EntityType, LegendCategory
from aerona.domain.enums.society import KnowledgeBranch, NaturalLaw
from aerona.domain.enums.son import SonStatus
from aerona.engine.body.book import factor
from aerona.engine.gods.queries import community_of
from aerona.engine.primitives.distance import seafaring_reach
from aerona.engine.primitives.knowledge import LawBook, branch_level, knows, level_multiplier
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import stat
from aerona.engine.primitives.subtypes import normalized_subtype
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.errors import RejectionError
from aerona.tools.framework.stats import fill_stats, mortal_age, stats_model
from aerona.tools.framework.validation import fail, state_reason

CRAFT_CHAIN = ("craft", "wealth", "intellect", "intelligence", "prosperity", "influence", "sway")
MONEY_KEYS = ("wealth", "prosperity")
HEADCOUNT_KEYS = ("population", "followers")
STRENGTH_CHAIN = ("strength", "martiality", "defense")
WITS_CHAIN = ("intellect", "influence", "sway")


def first_stat(entity: EntityRow, keys: Sequence[str], default: int) -> int:
    for key in keys:
        value = stat(entity, key)
        if value is not None:
            return value
    return default


async def craft_of(call: MortalCall, entity: EntityRow | None = None) -> int:
    holder = entity or call.me
    return round(first_stat(holder, CRAFT_CHAIN, call.rules.mortal_tools.default_stat) * await factor(call.session, holder.id, Capacity.CRAFT))


async def wits_of(call: MortalCall, entity: EntityRow | None = None) -> int:
    holder = entity or call.me
    return round(first_stat(holder, WITS_CHAIN, call.rules.mortal_tools.default_stat) * await factor(call.session, holder.id, Capacity.SCHOLARSHIP))


def money_key(entity: EntityRow) -> str | None:
    return next((key for key in MONEY_KEYS if stat(entity, key) is not None), None)


def headcount_key(entity: EntityRow) -> str | None:
    return next((key for key in HEADCOUNT_KEYS if stat(entity, key) is not None), None)


def is_community(entity: EntityRow) -> bool:
    return entity.entity_type in COMMUNITY_TYPES


def creation_power(call: MortalCall) -> int:
    tools = call.rules.mortal_tools
    return max(1, min(tools.creation_power_cap, round(call.me.power_level * tools.creation_power_pct / 100)))


async def home_of(call: MortalCall) -> EntityRow | None:
    if call.me.entity_type is EntityType.SETTLEMENT:
        return call.me
    return await call.session.get(EntityRow, call.me.location_id) if call.me.location_id is not None else None


async def i_know(call: MortalCall, branch: KnowledgeBranch, entity: EntityRow | None = None) -> bool:
    return await knows(call.session, (entity or call.me).id, branch)


async def my_branch_effect(call: MortalCall, branch: KnowledgeBranch, entity: EntityRow | None = None) -> float:
    return level_multiplier(call.rules.knowledge, await branch_level(call.session, (entity or call.me).id, branch))


async def near(call: MortalCall, other: EntityRow) -> bool:
    if other.id == call.me.id:
        return True
    if other.world_id != call.me.world_id:
        return False
    atlas = await call.atlas()
    seafaring = await i_know(call, KnowledgeBranch.SEAFARING) or await i_know(call, KnowledgeBranch.SEAFARING, other)
    sea_ban = (await LawBook.load(call.session)).has(NaturalLaw.SEA_BAN, call.me.world_id)
    return atlas.near(call.me.id, other.id, seafaring_reach(call.rules, seafaring, sea_ban))


async def same_region(call: MortalCall, other: EntityRow) -> bool:
    return other.world_id == call.me.world_id and (await call.atlas()).same_region(call.me.id, other.id)


async def require_target(call: MortalCall, entity_id: int | None) -> EntityRow:
    entity = await call.session.get(EntityRow, entity_id) if entity_id is not None else None
    reason = state_reason(entity, entity_id)
    if reason is not None or entity is None:
        raise RejectionError(reason or "")
    return entity


async def name_free(call: MortalCall, name: str) -> None:
    if await NameRepository(call.session).is_taken(name):
        fail(MortalResult.NAME_TAKEN)


@dataclass(frozen=True)
class MortalCreation:
    name: str
    entity_type: EntityType
    description: str
    subtype: str | None = None
    stats: dict[str, int] | None = None
    location_id: int | None = None
    power: int | None = None
    image_prompt: str | None = None
    knowledge_branch: KnowledgeBranch | None = None
    engine_kind: EngineKind | None = None
    tags: tuple[str, ...] = ()
    legend_category: LegendCategory | None = None


async def create_record(call: MortalCall, creation: MortalCreation) -> EntityRow:
    spec = ENTITY_TYPES[creation.entity_type]
    power = creation.power if creation.power is not None else creation_power(call)
    stats = fill_stats(call.rules, spec, dict(creation.stats or {}), power, banded=False)
    if creation.entity_type is EntityType.MORTAL:
        stats = mortal_age(call.rules, stats, call.rng("mortal_age"))
    subtype = await normalized_subtype(call.session, creation.entity_type, creation.subtype or spec.label.lower())
    location = await call.session.get(EntityRow, creation.location_id) if creation.location_id is not None else None
    valid_location = location if location is not None and location.entity_type in spec.containers else None
    draft = EntityDraft(
        name=creation.name,
        entity_type=creation.entity_type,
        description=creation.description.strip(),
        stats=stats_model(spec, stats),
        power_level=power,
        origin=EntityOrigin.MORTAL,
        birth_epoch=call.epoch,
        world_id=valid_location.world_id if valid_location is not None else call.me.world_id,
        location_id=valid_location.id if valid_location is not None else None,
        maker_entity_id=call.me.id,
        subtype=subtype or None,
        knowledge_branch=creation.knowledge_branch,
        legend_category=creation.legend_category if creation.entity_type is EntityType.LEGEND else None,
        engine_kind=creation.engine_kind,
        image_prompt=creation.image_prompt,
        tags=creation.tags,
        split_title=False,
    )
    created = await EntityRepository(call.session).create(draft)
    call.remember_creation(created.id)
    call.target(created.id)
    return created


async def enemies(call: MortalCall, first: int, second: int) -> bool:
    return bool(await BondRepository(call.session).active_between(first, second, [BondKind.ENEMY]))


def is_canon(entity: EntityRow | None) -> bool:
    return entity is not None and entity.status is EntityStatus.CANON


async def civilization_tier(session: AsyncSession, actor: EntityRow) -> int:
    if actor.civ_tier is not None:
        return actor.civ_tier
    community = await community_of(session, actor) if actor.entity_type is EntityType.MORTAL else None
    if community is not None and community.civ_tier is not None:
        return community.civ_tier
    return int(CivilizationTier.TRIBE)


async def worships_dead_son(session: AsyncSession, actor: EntityRow) -> bool:
    for bond in await BondRepository(session).outgoing(actor.id, BondKind.WORSHIPS):
        son = await session.get(SonRow, bond.target_node_id)
        if son is not None and son.status is SonStatus.DEAD:
            return True
    return False


async def candidates_text(call: MortalCall, types: Collection[EntityType], *, local: bool = False, fits: Callable[[EntityRow], bool] | None = None) -> str:
    limit = call.rules.mortal_tools.target_candidates
    found: list[EntityRow] = []
    for other in await canon(call.session, types, call.me.world_id):
        if len(found) >= limit:
            break
        if other.id == call.me.id or (fits is not None and not fits(other)):
            continue
        if not (await same_region(call, other) if local else await near(call, other)):
            continue
        found.append(other)
    if not found:
        return result(MortalResult.NO_CANDIDATES)
    listed = ", ".join(f"#{item.id} {item.name} ({ENTITY_TYPES[item.entity_type].label.lower()})" for item in found)
    return result(MortalResult.CANDIDATES, items=listed)


async def fail_with_candidates(
    call: MortalCall,
    template: StrEnum,
    types: Collection[EntityType],
    *,
    local: bool = False,
    fits: Callable[[EntityRow], bool] | None = None,
    **values: object,
) -> NoReturn:
    raise RejectionError(f"{result(template, **values)} {await candidates_text(call, types, local=local, fits=fits)}")
