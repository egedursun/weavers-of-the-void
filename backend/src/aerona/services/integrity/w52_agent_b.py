from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.customs import ANIMAL_INTOXICANT_SOURCES, MADE_INTOXICANT_TECHNIQUES, SOURCED_INTOXICANTS
from aerona.db.tables.biology import BiologyRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.customs import IntoxicantCustomRow
from aerona.db.tables.ecology import SpeciesProductRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.relations import ContestRow
from aerona.domain.enums.biology import BiologyVariant
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.customs import Intoxicant
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.relations import ContestStake
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import towns_of_people

LAND_TYPES = frozenset({EntityType.REGION, EntityType.SETTLEMENT})
BROKEN_PROMISE = "a party to the promise is gone"


async def gone(session: AsyncSession, node_id: int) -> bool:
    entity = await session.get(EntityRow, node_id)
    return entity is None or entity.status is not EntityStatus.CANON


async def dead_promises(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for bond in await session.scalars(select(BondRow).where(BondRow.kind == BondKind.BETROTHED_TO, BondRow.state == BondState.ACTIVE).order_by(BondRow.id)):
        if await gone(session, bond.source_node_id) or await gone(session, bond.target_node_id):
            found.append(bond.id)
    return found


async def end_promise(session: AsyncSession, key: int) -> None:
    bond = await session.get(BondRow, key)
    if bond is not None and bond.state is BondState.ACTIVE:
        bond.state = BondState.PAST
        bond.closed_reason = BROKEN_PROMISE


async def unnamed_stakes(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await session.scalars(
        select(ContestRow).where(ContestRow.stake == ContestStake.LAND, ContestRow.stake_node_id.is_not(None)).order_by(ContestRow.id)
    ):
        entity = await session.get(EntityRow, row.stake_node_id)
        if entity is None or entity.entity_type not in LAND_TYPES:
            found.append(row.id)
    return found


async def clear_stake(session: AsyncSession, key: int) -> None:
    row = await session.get(ContestRow, key)
    if row is not None:
        row.stake_node_id = None


async def stray_customs(session: AsyncSession, people_id: int | None = None) -> list[IntoxicantCustomRow]:
    statement = select(IntoxicantCustomRow).where(IntoxicantCustomRow.intoxicant.in_(SOURCED_INTOXICANTS))
    if people_id is not None:
        statement = statement.where(IntoxicantCustomRow.people_entity_id == people_id)
    found: list[IntoxicantCustomRow] = []
    for row in await session.scalars(statement.order_by(IntoxicantCustomRow.people_entity_id, IntoxicantCustomRow.intoxicant)):
        if "intoxicant" in (row.locked or []):
            continue
        sourced = (
            await knows_making(session, row.people_entity_id) if row.intoxicant is Intoxicant.SYNTHETIC else await has_beasts(session, row.people_entity_id)
        )
        if not sourced:
            found.append(row)
    return found


async def unsourced_intoxicants(session: AsyncSession) -> list[int]:
    return sorted({row.people_entity_id for row in await stray_customs(session)})


async def knows_making(session: AsyncSession, people_id: int) -> bool:
    found = await session.scalar(
        select(HolderTechniqueRow.technique)
        .where(HolderTechniqueRow.holder_entity_id == people_id, HolderTechniqueRow.technique.in_(sorted(MADE_INTOXICANT_TECHNIQUES)))
        .limit(1)
    )
    return found is not None


async def has_beasts(session: AsyncSession, people_id: int) -> bool:
    towns = await towns_of_people(session, people_id)
    if not towns:
        return False
    lands = select(EntityRow.location_id).where(EntityRow.id.in_(towns), EntityRow.location_id.is_not(None))
    sources = select(SpeciesProductRow.species_entity_id).where(SpeciesProductRow.product.in_(sorted(product.value for product in ANIMAL_INTOXICANT_SOURCES)))
    found = await session.scalar(
        select(SpeciesRangeRow.species_entity_id).where(SpeciesRangeRow.region_entity_id.in_(lands), SpeciesRangeRow.species_entity_id.in_(sources)).limit(1)
    )
    return found is not None


async def drop_intoxicant(session: AsyncSession, key: int) -> None:
    for row in await stray_customs(session, key):
        await session.delete(row)


async def partnerless(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(BiologyRow).where(BiologyRow.partner_species_id.is_(None)).order_by(BiologyRow.holder_entity_id))
    return [row.holder_entity_id for row in rows if BiologyVariant.SYMBIOTIC.value in row.variants and "partner_species_id" not in row.locked]


async def name_partner(session: AsyncSession, key: int) -> None:
    row = await session.get(BiologyRow, key)
    if row is None:
        return
    atlas = await RegionAtlas.load(session)
    lands = sorted({region for town in await towns_of_people(session, key) if (region := atlas.top_region(town)) is not None})
    found = await session.scalar(
        select(SpeciesRangeRow.species_entity_id)
        .where(SpeciesRangeRow.region_entity_id.in_(lands), SpeciesRangeRow.abundance > 0, SpeciesRangeRow.species_entity_id != key)
        .group_by(SpeciesRangeRow.species_entity_id)
        .order_by(func.sum(SpeciesRangeRow.abundance).desc(), SpeciesRangeRow.species_entity_id)
        .limit(1)
    )
    if found is not None:
        row.partner_species_id = int(found)
    else:
        row.variants = [value for value in row.variants if value != BiologyVariant.SYMBIOTIC.value]
