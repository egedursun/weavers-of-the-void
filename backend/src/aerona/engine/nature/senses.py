from collections.abc import Callable, Mapping
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.diets import FLESH_SEEKERS
from aerona.catalog.senses import PURPOSES, SENSES
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.read_memo import memoized
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.ecology import SpeciesProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.nature import SenseProfileRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.ecology import Diet
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.made import EffectTarget
from aerona.domain.enums.nature import SenseCause, SenseKind, Thermoregulation
from aerona.domain.enums.society import CreatureTrait
from aerona.engine.belonging.values import own_people
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.cosmos.fauna import traits_of
from aerona.engine.demography.biology import natures
from aerona.engine.primitives.augment_bonus import lifts_of


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
    extra = await lifts_of(session, node_id, EffectTarget.SENSE) if node_id is not None and node_id != holder else {}
    lifted = {sense: known.get(sense, 0) + extra.get(sense.value, 0) for sense in PURPOSES[purpose]}
    return sum(weight * lifted[sense] for sense, weight in PURPOSES[purpose].items()) / PERCENT


BORN: Mapping[SenseCause, Callable[[SpeciesProfileRow, set[CreatureTrait]], bool]] = total(
    SenseCause,
    {
        SenseCause.BASE: lambda profile, traits: False,
        SenseCause.NOCTURNAL: lambda profile, traits: profile.nocturnal,
        SenseCause.FLESH_SEEKER: lambda profile, traits: profile.diet in FLESH_SEEKERS,
        SenseCause.PLANT_EATER: lambda profile, traits: profile.diet is Diet.HERBIVORE,
        SenseCause.ECHOLOCATION: lambda profile, traits: CreatureTrait.ECHOLOCATION in traits,
        SenseCause.BURROWING: lambda profile, traits: CreatureTrait.BURROWING in traits,
        SenseCause.MIGRATORY: lambda profile, traits: profile.migratory,
        SenseCause.SPIRIT_SIGHT: lambda profile, traits: CreatureTrait.SPIRIT_SIGHT in traits,
        SenseCause.COLD_HUNTER: lambda profile, traits: profile.thermoregulation is Thermoregulation.ECTOTHERM and profile.diet in FLESH_SEEKERS,
    },
)


def born_species(base: int, gift: int, profile: SpeciesProfileRow, traits: set[CreatureTrait]) -> dict[SenseKind, int]:
    found = {sense: base for sense, spec in SENSES.items() if spec.cause is SenseCause.BASE}
    found.update({sense: gift for sense, spec in SENSES.items() if BORN[spec.cause](profile, traits)})
    return found


def born_people(base: int, gift: int, biology: PeopleBiologyRow | None) -> dict[SenseKind, int]:
    traits = natures(biology)
    found = {sense: base for sense, spec in SENSES.items() if spec.people_base}
    found.update({sense: gift for sense, spec in SENSES.items() if spec.people_trait is not None and spec.people_trait in traits})
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
