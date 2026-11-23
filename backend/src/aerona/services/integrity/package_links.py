from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.affliction import PackageKind
from aerona.domain.enums.entity import EntityStatus, EntityType


async def open_packages(session: AsyncSession, package: PackageKind) -> list[AfflictionRow]:
    return list(
        await session.scalars(select(AfflictionRow).where(AfflictionRow.package == package, AfflictionRow.cured_epoch.is_(None)).order_by(AfflictionRow.id))
    )


async def aimless_charms(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await open_packages(session, PackageKind.CHARM):
        target = await session.get(EntityRow, row.charm_target_node_id) if row.charm_target_node_id is not None else None
        if row.charm_target_node_id is None or (target is not None and target.status is not EntityStatus.CANON):
            found.append(row.id)
    return found


async def end_aimless_charm(session: AsyncSession, key: int) -> None:
    row = await session.get(AfflictionRow, key)
    if row is not None and "charm_target_node_id" not in row.locked:
        row.charm_strength = 0
        row.cured_epoch = row.since_epoch


async def formless_changes(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await open_packages(session, PackageKind.TRANSFORMATION):
        species = await session.get(EntityRow, row.transform_species_id) if row.transform_species_id is not None else None
        bad_species = row.transform_species_id is not None and (species is None or species.entity_type is not EntityType.SPECIES)
        if row.transform_plan is None or bad_species:
            found.append(row.id)
    return found


async def mend_formless_change(session: AsyncSession, key: int) -> None:
    row = await session.get(AfflictionRow, key)
    if row is None or "transform_plan" in row.locked:
        return
    species = await session.get(EntityRow, row.transform_species_id) if row.transform_species_id is not None else None
    if species is None or species.entity_type is not EntityType.SPECIES:
        row.transform_species_id = None
    if row.transform_plan is None:
        row.cured_epoch = row.since_epoch


async def unsigned_fortunes(session: AsyncSession) -> list[int]:
    return [row.id for row in await open_packages(session, PackageKind.FORTUNE) if row.fortune_sign not in (-1, 1) or row.fortune_strength is None]


async def sign_fortune(session: AsyncSession, key: int) -> None:
    row = await session.get(AfflictionRow, key)
    if row is not None and "fortune" not in row.locked:
        row.fortune_sign = row.fortune_sign if row.fortune_sign in (-1, 1) else 1
        row.fortune_strength = row.fortune_strength if row.fortune_strength is not None else 0
