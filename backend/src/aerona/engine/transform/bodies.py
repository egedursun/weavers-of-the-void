from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.son import SonStatus
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_percent


async def living_body(session: AsyncSession, son: SonRow) -> EntityRow | None:
    body_id = son.body_entity_id if son.body_entity_id is not None else son.anchor_entity_id
    body = await session.get(EntityRow, body_id) if body_id is not None else None
    return body if body is not None and body.entity_type is EntityType.MORTAL and body.status is EntityStatus.CANON else None


async def fallen_in(ctx: TickContext, body_id: int) -> SonRow | None:
    return await ctx.session.scalar(select(SonRow).where(SonRow.body_entity_id == body_id, SonRow.status == SonStatus.FALLEN))


async def lift_fallen(ctx: TickContext, body_id: int, amount: int) -> SonRow | None:
    son = await fallen_in(ctx, body_id)
    if son is None or held(son.id):
        return None
    son.existence = clamp_percent(son.existence + amount)
    return son
