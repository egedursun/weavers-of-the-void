from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.made import SOURCED_RIFTS
from aerona.db.tables.cosmography import CosmicBeingProfileRow, RiftRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.cosmography import BeingScale, RiftCause
from aerona.domain.enums.entity import EntityStatus, EntityType


async def regional(session: AsyncSession, being: EntityRow | None) -> bool:
    if being is None or being.location_id is None:
        return False
    place = await session.get(EntityRow, being.location_id)
    return place is not None and place.entity_type is EntityType.REGION and place.world_id == being.world_id


async def unplaced_regional_beings(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for profile in await session.scalars(
        select(CosmicBeingProfileRow).where(CosmicBeingProfileRow.scale == BeingScale.REGION).order_by(CosmicBeingProfileRow.entity_id)
    ):
        if not await regional(session, await session.get(EntityRow, profile.entity_id)):
            found.append(profile.entity_id)
    return found


async def place_regional_being(session: AsyncSession, key: int) -> None:
    being = await session.get(EntityRow, key)
    profile = await session.get(CosmicBeingProfileRow, key)
    if being is None or profile is None:
        return
    region = await session.scalar(
        select(EntityRow.id)
        .where(EntityRow.world_id == being.world_id, EntityRow.entity_type == EntityType.REGION, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
        .limit(1)
    )
    if region is not None and being.world_id is not None:
        being.location_id = region
    else:
        profile.scale = BeingScale.WORLD


async def sourceless_rifts(session: AsyncSession) -> list[int]:
    statement = select(RiftRow.id).where(RiftRow.cause.in_(sorted(SOURCED_RIFTS)), RiftRow.opened_by_node_id.is_(None))
    return list(await session.scalars(statement.order_by(RiftRow.id)))


async def unsource_rift(session: AsyncSession, key: int) -> None:
    rift = await session.get(RiftRow, key)
    if rift is not None and rift.opened_by_node_id is None:
        rift.cause = RiftCause.CONVERGENCE
