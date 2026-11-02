from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.repositories.nodes import NodeRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.engine.gods.queries import active_bond_exists, worshippers_of
from aerona.engine.gods.stats import Trait, trait, trait_or
from aerona.engine.primitives.faith import saturated_followers
from aerona.engine.primitives.numbers import round_half_up
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class CultEffect:
    faith: int
    essence: int
    doom_pushback: int


async def creator_node_id(session: AsyncSession) -> int | None:
    return await NodeRepository(session).creator_id()


async def worships_creator(session: AsyncSession, entity_id: int) -> bool:
    creator = await creator_node_id(session)
    return creator is not None and await active_bond_exists(session, entity_id, creator, BondKind.WORSHIPS)


async def creator_worshippers(session: AsyncSession) -> list[EntityRow]:
    creator = await creator_node_id(session)
    if creator is None:
        return []
    return await worshippers_of(session, creator)


def cult_member_faith(rules: Rules, entity: EntityRow) -> float:
    creator = rules.creator
    population = trait_or(entity, Trait.POPULATION, 0)
    piety = trait(entity, Trait.PIETY)
    piety_share = (creator.cult_default_piety if piety is None else piety) / PERCENT
    followers = trait_or(entity, Trait.FOLLOWERS, 0)
    mortal = creator.cult_faith_per_mortal if entity.entity_type is EntityType.MORTAL else 0
    return population / creator.cult_population_per_faith * piety_share + saturated_followers(rules, followers, creator.cult_followers_per_faith) + mortal


async def creator_faith(session: AsyncSession, rules: Rules) -> int:
    return round_half_up(sum(cult_member_faith(rules, entity) for entity in await creator_worshippers(session)))


def cult_effect_from_faith(rules: Rules, faith: int) -> CultEffect:
    creator = rules.creator
    return CultEffect(
        faith=faith,
        essence=faith // creator.cult_faith_per_essence,
        doom_pushback=min(creator.cult_apocalypse_push_cap, faith // creator.cult_faith_per_apocalypse_push),
    )


async def cult_effect(session: AsyncSession, rules: Rules) -> CultEffect:
    return cult_effect_from_faith(rules, await creator_faith(session, rules))
