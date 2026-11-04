from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.warfare import WarRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType


async def dedicated_structures(session: AsyncSession, son_id: int) -> list[EntityRow]:
    statement = (
        select(EntityRow)
        .join(BondRow, BondRow.source_node_id == EntityRow.id)
        .where(
            BondRow.target_node_id == son_id,
            BondRow.kind == BondKind.WORSHIPS,
            BondRow.state == BondState.ACTIVE,
            EntityRow.entity_type == EntityType.STRUCTURE,
            EntityRow.status == EntityStatus.CANON,
        )
        .order_by(EntityRow.id)
    )
    return list((await session.scalars(statement)).unique())


async def dedication_of(session: AsyncSession, structure_id: int) -> SonRow | None:
    son_id = await session.scalar(
        select(BondRow.target_node_id)
        .join(SonRow, SonRow.id == BondRow.target_node_id)
        .where(BondRow.source_node_id == structure_id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
        .order_by(BondRow.id.desc())
        .limit(1)
    )
    return await session.get(SonRow, son_id) if son_id is not None else None


async def may_anchor(session: AsyncSession, son: SonRow, entity: EntityRow) -> bool:
    if entity.creator_son_id == son.id:
        return True
    if entity.entity_type is not EntityType.STRUCTURE:
        return False
    return any(work.id == entity.id for work in await dedicated_structures(session, son.id))


async def incited_wars(session: AsyncSession, son_id: int) -> list[WarRow]:
    return list(await session.scalars(select(WarRow).where(WarRow.incited_by_son_id == son_id).order_by(WarRow.started_epoch, WarRow.id)))
