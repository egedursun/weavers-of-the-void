from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.agency import ActionRecordRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.node import ActorKind
from aerona.engine.context import TickContext


async def require_creator(session: AsyncSession) -> CreatorRow:
    return await CosmosRepository(session).require_creator()


async def record_action(
    ctx: TickContext, kind: ActionKind, target_node_id: int | None = None, essence_spent: int = 0, summary: str | None = None
) -> ActionRecordRow:
    creator = await require_creator(ctx.session)
    row = ActionRecordRow(
        epoch=ctx.epoch,
        actor_kind=ActorKind.CREATOR,
        actor_node_id=creator.id,
        kind=kind,
        target_node_id=target_node_id,
        essence_spent=essence_spent,
        summary=summary,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


def require[T](row: T | None, label: str) -> T:
    if row is None:
        raise NotFoundError(f"No such {label}.")
    return row
