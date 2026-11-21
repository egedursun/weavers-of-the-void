from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import MovementProfileRow
from aerona.db.tables.protected_nature import ConservationMovementRow, ProtectedAreaRow, SpeciesProtectionRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import MovementCause


async def landless_areas(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await session.scalars(select(ProtectedAreaRow).where(ProtectedAreaRow.lifted_epoch.is_(None)).order_by(ProtectedAreaRow.id)):
        region = await session.get(EntityRow, row.region_entity_id)
        if region is None or region.entity_type is not EntityType.REGION:
            found.append(row.id)
    return found


async def lift_landless(session: AsyncSession, key: int) -> None:
    row = await session.get(ProtectedAreaRow, key)
    if row is not None:
        row.lifted_epoch = row.since_epoch


async def kindless_protections(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await session.scalars(select(SpeciesProtectionRow).order_by(SpeciesProtectionRow.id)):
        species = await session.get(EntityRow, row.species_entity_id)
        if species is None or species.entity_type is not EntityType.SPECIES:
            found.append(row.id)
    return found


async def drop_protection(session: AsyncSession, key: int) -> None:
    row = await session.get(SpeciesProtectionRow, key)
    if row is not None:
        await session.delete(row)


async def stray_aims(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await session.scalars(select(ConservationMovementRow).order_by(ConservationMovementRow.movement_entity_id)):
        movement = await session.get(MovementProfileRow, row.movement_entity_id)
        if movement is None or movement.cause is not MovementCause.CONSERVATION:
            found.append(row.movement_entity_id)
    return found


async def drop_aims(session: AsyncSession, key: int) -> None:
    row = await session.get(ConservationMovementRow, key)
    if row is not None:
        await session.delete(row)
