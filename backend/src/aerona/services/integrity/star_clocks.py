from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.celestial import StarRow
from aerona.db.tables.physics import StarPhysicsRow
from aerona.db.write_guard import held
from aerona.engine.cosmos.starlife import stage_left


async def clocks_past_their_age(session: AsyncSession) -> list[int]:
    rules = await CosmosRepository(session).rules()
    found: list[int] = []
    for star in await session.scalars(select(StarRow).where(StarRow.lifecycle_clock.is_not(None)).order_by(StarRow.id)):
        physics = await session.get(StarPhysicsRow, star.id)
        if held(star.id) or "lifecycle_clock" in (star.locked or []) or physics is None:
            continue
        left = stage_left(rules, star, star.age_stage, physics)
        if left is not None and star.lifecycle_clock is not None and star.lifecycle_clock > left:
            found.append(star.id)
    return found


async def wind_clock_to_age(session: AsyncSession, star_id: int) -> None:
    star = await session.get(StarRow, star_id)
    physics = await session.get(StarPhysicsRow, star_id)
    if star is None or physics is None:
        return
    left = stage_left(await CosmosRepository(session).rules(), star, star.age_stage, physics)
    if left is not None and star.lifecycle_clock is not None:
        star.lifecycle_clock = min(star.lifecycle_clock, left)
