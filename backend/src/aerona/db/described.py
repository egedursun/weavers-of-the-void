from sqlalchemy import ColumnElement, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.node import ActorKind

DESCRIPTION = "description"


def rewritten() -> ColumnElement[bool]:
    return and_(
        StateChangeRow.table_name == EntityRow.__tablename__,
        StateChangeRow.field == DESCRIPTION,
        StateChangeRow.actor_kind != ActorKind.ENGINE,
    )


async def described_in(session: AsyncSession, entity: EntityRow) -> int:
    last = await session.scalar(select(func.max(StateChangeRow.epoch)).where(StateChangeRow.node_id == entity.id, rewritten()))
    return max(entity.birth_epoch, int(last)) if last is not None else entity.birth_epoch
