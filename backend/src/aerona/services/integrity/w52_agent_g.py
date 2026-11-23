from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.sacred import PLACE_SPIRITS
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.faith import ReincarnationRow
from aerona.db.tables.folkways import LuckBeliefRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.tables.sacred import GeniusLocusRow, PetitionRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import TerrainKind
from aerona.domain.enums.faith import RebirthPath
from aerona.domain.enums.folkways import LuckSign
from aerona.domain.enums.sacred import GeniusLocusKind, PetitionKind, PetitionStatus

OPEN_PETITIONS = (PetitionStatus.FILED, PetitionStatus.DELAYED, PetitionStatus.APPEALED)


async def fitting_kind(session: AsyncSession, place: EntityRow) -> GeniusLocusKind | None:
    if place.entity_type is EntityType.SETTLEMENT:
        return GeniusLocusKind.CITY
    if place.entity_type is EntityType.HOUSE:
        return GeniusLocusKind.HEARTH
    if place.entity_type is EntityType.REGION:
        land = await session.get(RegionEnvironmentRow, place.id)
        return GeniusLocusKind.SEA if land is not None and land.dominant_terrain is TerrainKind.SEA else None
    profile = await session.get(PlaceProfileRow, place.id)
    return PLACE_SPIRITS.get(profile.kind) if profile is not None else None


async def misplaced_spirits(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await session.scalars(select(GeniusLocusRow).where(GeniusLocusRow.place_entity_id.is_not(None)).order_by(GeniusLocusRow.spirit_entity_id)):
        place = await session.get(EntityRow, row.place_entity_id)
        fit = await fitting_kind(session, place) if place is not None else None
        if fit is not None and fit is not row.kind and "kind" not in row.locked:
            found.append(row.spirit_entity_id)
    return found


async def refit_spirit(session: AsyncSession, key: int) -> None:
    row = await session.get(GeniusLocusRow, key)
    place = await session.get(EntityRow, row.place_entity_id) if row is not None and row.place_entity_id is not None else None
    fit = await fitting_kind(session, place) if place is not None else None
    if row is not None and fit is not None:
        row.kind = fit


async def targetless_vengeance(session: AsyncSession) -> list[int]:
    rows = await session.scalars(
        select(PetitionRow.id)
        .where(PetitionRow.kind == PetitionKind.VENGEANCE, PetitionRow.target_node_id.is_(None), PetitionRow.status.in_(OPEN_PETITIONS))
        .order_by(PetitionRow.id)
    )
    return list(rows)


async def dismiss_petition(session: AsyncSession, key: int) -> None:
    row = await session.get(PetitionRow, key)
    if row is not None:
        row.status = PetitionStatus.DISMISSED


async def unmarked_signs(session: AsyncSession) -> list[int]:
    rows = await session.scalars(
        select(LuckBeliefRow.id)
        .where(
            ((LuckBeliefRow.sign == LuckSign.ANIMAL) & LuckBeliefRow.species_entity_id.is_(None))
            | ((LuckBeliefRow.sign == LuckSign.COLOUR) & LuckBeliefRow.colour.is_(None))
        )
        .order_by(LuckBeliefRow.id)
    )
    return list(rows)


async def drop_sign(session: AsyncSession, key: int) -> None:
    row = await session.get(LuckBeliefRow, key)
    if row is not None:
        await session.delete(row)


async def kindless_rebirths(session: AsyncSession) -> list[int]:
    rows = await session.scalars(
        select(ReincarnationRow.id).where(ReincarnationRow.path == RebirthPath.KIND, ReincarnationRow.species_entity_id.is_(None)).order_by(ReincarnationRow.id)
    )
    return list(rows)


async def rebirth_by_people(session: AsyncSession, key: int) -> None:
    row = await session.get(ReincarnationRow, key)
    if row is not None:
        row.path = RebirthPath.PEOPLE
