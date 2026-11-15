from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.world_views import WorldViewRow
from aerona.engine.cosmos.world_views import seed_view
from aerona.rules.registry import Rules


async def seed_missing_views(session: AsyncSession, rules: Rules, epoch: int) -> int:
    known = set(await session.scalars(select(WorldViewRow.world_id)))
    seeded = 0
    for world in list(await session.scalars(select(WorldRow).where(WorldRow.id.not_in(known or {-1})).order_by(WorldRow.id))):
        await seed_view(session, rules, world, epoch)
        seeded += 1
    return seeded
