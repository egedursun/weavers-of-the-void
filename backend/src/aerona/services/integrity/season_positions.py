from sqlalchemy import CursorResult, func, null, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.season_positions import SEASON_POSITIONS
from aerona.db.base import Base
from aerona.db.tables.environment import WorldSeasonRow
from aerona.engine.environment.season_remap import of_world


async def mend_season_positions(session: AsyncSession) -> int:
    rows = await session.execute(select(WorldSeasonRow.world_id, func.count()).group_by(WorldSeasonRow.world_id))
    counts = {int(world_id): int(count) for world_id, count in rows}
    changed = 0
    for world_id, count in sorted(counts.items()):
        for entry in SEASON_POSITIONS:
            table = Base.metadata.tables[entry.table]
            column = table.c[entry.column]
            settled = null() if entry.nullable else count - 1
            result = await session.execute(update(table).where(of_world(table, entry, world_id), column >= count).values({entry.column: settled}))
            changed += result.rowcount if isinstance(result, CursorResult) else 0
    return changed
