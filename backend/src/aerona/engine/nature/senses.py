from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.ecology import SpeciesProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.nature import SenseProfileRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.demography import NaturalTrait
from aerona.domain.enums.ecology import Diet
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.nature import SenseKind, Thermoregulation
from aerona.domain.enums.society import CreatureTrait
from aerona.engine.belonging.values import own_people
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.cosmos.fauna import traits_of
from aerona.engine.demography.biology import natures

S = SenseKind
AGENTS = "agents"
NIGHT = "night"
AMBUSH = "ambush"
TRACKING = "tracking"
NAVIGATION = "navigation"
SPIRITS = "spirits"
PURPOSES: Mapping[str, Mapping[SenseKind, float]] = MappingProxyType(
    {
        AGENTS: {S.SMELL: 0.6, S.HEARING: 0.2, S.SPIRIT_SIGHT: 0.2},
        NIGHT: {S.NIGHT_VISION: 0.6, S.ECHOLOCATION: 0.2, S.HEAT: 0.2},
        AMBUSH: {S.HEARING: 0.5, S.SMELL: 0.3, S.VIBRATION: 0.2},
        TRACKING: {S.SMELL: 0.5, S.SIGHT: 0.2, S.HEAT: 0.15, S.VIBRATION: 0.15},
        NAVIGATION: {S.MAGNETIC: 0.7, S.SIGHT: 0.3},
        SPIRITS: {S.SPIRIT_SIGHT: 1.0},
    }
)
HUNTERS = frozenset({Diet.CARNIVORE, Diet.OMNIVORE, Diet.SCAVENGER})


@dataclass
class SenseTally:
    seeded: int = 0


@memoized(SenseProfileRow)
async def senses_of(session: AsyncSession, holder_id: int) -> dict[SenseKind, int]:
    return {row.sense: row.acuity for row in await session.scalars(select(SenseProfileRow).where(SenseProfileRow.holder_entity_id == holder_id))}


async def sense_holder(session: AsyncSession, node_id: int | None) -> int | None:
    entity = await session.get(EntityRow, node_id) if node_id is not None else None
    if entity is None:
        return None
    if entity.entity_type is EntityType.PEOPLE or await session.get(SpeciesProfileRow, entity.id) is not None:
        return entity.id
    if entity.entity_type is EntityType.MORTAL:
        return await own_people(session, entity)
    if entity.entity_type is EntityType.POLITY:
        realm = await session.get(PolityProfileRow, entity.id)
        capital = await session.get(EntityRow, realm.capital_entity_id) if realm is not None and realm.capital_entity_id is not None else None
        entity = capital if capital is not None else entity
    folk = await people_of(session, entity)
    return folk.id if folk is not None else None


async def sense_score(session: AsyncSession, node_id: int | None, purpose: str) -> float:
    holder = await sense_holder(session, node_id)
    if holder is None:
        return 0.0
    known = await senses_of(session, holder)
    return sum(weight * known.get(sense, 0) for sense, weight in PURPOSES[purpose].items()) / PERCENT


def born_species(base: int, gift: int, profile: SpeciesProfileRow, traits: set[CreatureTrait]) -> dict[SenseKind, int]:
    found = {S.SIGHT: base}
    gifts = {
        S.NIGHT_VISION: profile.nocturnal,
        S.SMELL: profile.diet in HUNTERS,
        S.HEARING: profile.diet is Diet.HERBIVORE,
        S.ECHOLOCATION: CreatureTrait.ECHOLOCATION in traits,
        S.VIBRATION: CreatureTrait.BURROWING in traits,
        S.MAGNETIC: profile.migratory,
        S.SPIRIT_SIGHT: CreatureTrait.SPIRIT_SIGHT in traits,
        S.HEAT: profile.thermoregulation is Thermoregulation.ECTOTHERM and profile.diet in HUNTERS,
    }
    found.update({sense: gift for sense, born in gifts.items() if born})
    return found


def born_people(base: int, gift: int, biology: PeopleBiologyRow | None) -> dict[SenseKind, int]:
    traits = natures(biology)
    found = {S.SIGHT: base, S.HEARING: base}
    gifts = {
        S.NIGHT_VISION: NaturalTrait.DARK_SIGHT in traits,
        S.SMELL: NaturalTrait.KEEN_SENSES in traits,
        S.VIBRATION: NaturalTrait.BURROWING in traits,
    }
    found.update({sense: gift for sense, born in gifts.items() if born})
    if NaturalTrait.KEEN_SENSES in traits:
        found[S.HEARING] = gift
    return found


async def seed_senses(ctx: TickContext, tally: SenseTally) -> None:
    table = ctx.rules.senses
    known = set(await ctx.session.scalars(select(SenseProfileRow.holder_entity_id).distinct()))
    holders = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type.in_([EntityType.SPECIES, EntityType.BEAST, EntityType.PEOPLE]), EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    for holder in list(holders):
        if holder.id in known or held(holder.id):
            continue
        if holder.entity_type is EntityType.PEOPLE:
            born = born_people(table.base_sight, table.gift, await ctx.session.get(PeopleBiologyRow, holder.id))
        else:
            profile = await ctx.session.get(SpeciesProfileRow, holder.id)
            if profile is None:
                continue
            born = born_species(table.base_sight, table.gift, profile, await traits_of(ctx.session, holder.id))
        for sense, acuity in born.items():
            ctx.session.add(SenseProfileRow(holder_entity_id=holder.id, sense=sense, acuity=acuity, locked=[]))
        tally.seeded += 1
    await ctx.session.flush()
