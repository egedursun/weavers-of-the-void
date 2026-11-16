from collections import defaultdict
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.eras import ERA_EFFECTS, ERA_MARKERS, POWDER
from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.eras import TechProgrammeRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.eras import EraChannel, ProgrammeStage, TechFamily
from aerona.domain.enums.society import NaturalLaw
from aerona.domain.enums.world import TechnologyEra
from aerona.engine.belonging.values import own_people
from aerona.engine.primitives.knowledge import LawBook
from aerona.rules.registry import Rules


@memoized(HolderTechniqueRow)
async def held_by(session: AsyncSession, holder_id: int) -> frozenset[Technique]:
    return frozenset(await session.scalars(select(HolderTechniqueRow.technique).where(HolderTechniqueRow.holder_entity_id == holder_id)))


COMMUNITIES = frozenset({EntityType.SETTLEMENT, EntityType.PEOPLE})
CHAIN_DEPTH = 8


async def home_community(session: AsyncSession, entity: EntityRow) -> EntityRow | None:
    current: EntityRow | None = entity
    for _ in range(CHAIN_DEPTH):
        if current is None:
            break
        if current.entity_type in COMMUNITIES:
            return current
        current = await session.get(EntityRow, current.location_id) if current.location_id is not None else None
    folk = await own_people(session, entity) if entity.entity_type is EntityType.MORTAL else None
    return await session.get(EntityRow, folk) if folk is not None else None


async def capital_of_member(session: AsyncSession, member_id: int) -> int | None:
    polity = await session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == member_id).limit(1))
    profile = await session.get(PolityProfileRow, polity) if polity is not None else None
    return profile.capital_entity_id if profile is not None else None


@memoized(EntityRow, "entities.other", BondRow, PolityMemberRow, PolityProfileRow)
async def era_holders(session: AsyncSession, node_id: int | None) -> tuple[int, ...]:
    if node_id is None:
        return ()
    entity = await session.get(EntityRow, node_id)
    if entity is None:
        return ()
    home = await home_community(session, entity)
    found = [entity.id, *(item for item in (home.id if home is not None else None, entity.location_id, entity.affiliated_entity_id) if item is not None)]
    realm = await session.get(PolityProfileRow, entity.id)
    if realm is not None:
        found += [item for item in (realm.capital_entity_id, realm.core_entity_id) if item is not None]
    for member in dict.fromkeys(item for item in (entity.id, home.id if home is not None else None) if item is not None):
        capital = await capital_of_member(session, member)
        if capital is not None:
            found.append(capital)
    return tuple(dict.fromkeys(found))


async def era_techniques(session: AsyncSession, node_id: int | None) -> frozenset[Technique]:
    known: set[Technique] = set()
    for holder in await era_holders(session, node_id):
        known |= await held_by(session, holder)
    if known & POWDER and node_id is not None:
        entity = await session.get(EntityRow, node_id)
        if entity is not None and (await LawBook.load(session)).has(NaturalLaw.NO_GUNPOWDER, entity.world_id):
            known -= POWDER
    return frozenset(known)


def channel_value(rules: Rules, known: Iterable[Technique], channel: EraChannel) -> int:
    total = 0
    for technique in sorted(set(known)):
        for item, field in ERA_EFFECTS.get(technique, ()):
            if item is channel:
                total += int(getattr(rules.eras, field))
    return total


async def tech_bonus(session: AsyncSession, rules: Rules, node_id: int | None, channel: EraChannel) -> int:
    return channel_value(rules, await era_techniques(session, node_id), channel)


async def tech_factor(session: AsyncSession, rules: Rules, node_id: int | None, channel: EraChannel) -> float:
    return 1 + await tech_bonus(session, rules, node_id, channel) / PERCENT


async def tech_relief(session: AsyncSession, rules: Rules, node_id: int | None, channel: EraChannel, cap: int = PERCENT) -> float:
    return 1 - min(cap, await tech_bonus(session, rules, node_id, channel)) / PERCENT


async def channel_by_holder(session: AsyncSession, rules: Rules, channel: EraChannel) -> dict[int, int]:
    wanted = [technique for technique, effects in ERA_EFFECTS.items() if any(item is channel for item, _ in effects)]
    held: dict[int, set[Technique]] = defaultdict(set)
    for holder, technique in await session.execute(
        select(HolderTechniqueRow.holder_entity_id, HolderTechniqueRow.technique).where(HolderTechniqueRow.technique.in_(wanted))
    ):
        held[holder].add(technique)
    return {holder: channel_value(rules, known, channel) for holder, known in held.items()}


async def world_start(session: AsyncSession) -> TechnologyEra:
    cosmos = await CosmosRepository(session).get()
    settings = cosmos.genesis_settings if cosmos is not None else None
    return settings.technology if settings is not None else TechnologyEra.IRON


async def chosen_levels(session: AsyncSession) -> dict[TechFamily, int]:
    cosmos = await CosmosRepository(session).get()
    settings = cosmos.genesis_settings if cosmos is not None else None
    return dict(settings.technology_levels) if settings is not None else {}


def era_of(known: Iterable[Technique], floor: TechnologyEra = TechnologyEra.STONE) -> TechnologyEra:
    held = set(known)
    reached = floor
    order = list(TechnologyEra)
    for era, marker in ERA_MARKERS:
        if marker in held and order.index(era) > order.index(reached):
            reached = era
    return reached


async def programme_pressure(session: AsyncSession, rules: Rules) -> dict[int, int]:
    pressure: dict[int, int] = defaultdict(int)
    rows = await session.execute(
        select(PolityProfileRow.capital_entity_id)
        .join(TechProgrammeRow, TechProgrammeRow.polity_entity_id == PolityProfileRow.polity_entity_id)
        .where(TechProgrammeRow.stage == ProgrammeStage.TESTING)
    )
    for (capital,) in rows:
        town = await session.get(EntityRow, capital) if capital is not None else None
        if town is not None and town.location_id is not None:
            pressure[town.location_id] += rules.programmes.leak
    return pressure
