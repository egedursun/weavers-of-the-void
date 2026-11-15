from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.world_views import WorldViewRow
from aerona.engine.cosmos.world_views import default_values, seed_view
from aerona.rules.registry import Rules


async def seed_missing_views(session: AsyncSession, rules: Rules, epoch: int) -> int:
    rows = {row.world_id: row for row in await session.scalars(select(WorldViewRow))}
    mended = 0
    for world in list(await session.scalars(select(WorldRow).order_by(WorldRow.id))):
        row = rows.get(world.id)
        if row is None:
            await seed_view(session, rules, world, epoch)
            mended += 1
            continue
        for key, value in default_values(rules, world.world_type).items():
            if key not in row.locked and getattr(row, key) != value:
                setattr(row, key, value)
                mended += 1
    await session.flush()
    return mended
