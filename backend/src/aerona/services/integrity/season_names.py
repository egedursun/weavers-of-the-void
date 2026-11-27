from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.environment import WorldSeasonRow
from aerona.engine.environment.season_names import name_for_season
from aerona.services.integrity.w52_agent_e import world_rules


async def twin_season_names(session: AsyncSession) -> list[int]:
    seen: dict[tuple[int, str], int] = {}
    found: list[int] = []
    for row in await session.scalars(select(WorldSeasonRow).order_by(WorldSeasonRow.world_id, WorldSeasonRow.position)):
        key = (row.world_id, row.name)
        if key in seen and not row.edited:
            found.append(row.id)
        seen.setdefault(key, row.id)
    return found


async def rename_twin_season(session: AsyncSession, season_id: int) -> None:
    row = await session.get(WorldSeasonRow, season_id)
    world = await session.get(WorldRow, row.world_id) if row is not None else None
    if row is None or world is None:
        return
    others = set(await session.scalars(select(WorldSeasonRow.name).where(WorldSeasonRow.world_id == row.world_id, WorldSeasonRow.id != row.id)))
    row.name = await name_for_season(session, await world_rules(session), world, row.position, others)
