from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.engine.primitives.stats import set_stats, stat

MIRRORED = ("legitimacy", "stability")


async def polity_stats_astray(session: AsyncSession) -> list[int]:
    rows = await session.execute(
        select(EntityRow, PolityProfileRow).join(PolityProfileRow, PolityProfileRow.polity_entity_id == EntityRow.id).order_by(EntityRow.id)
    )
    return [polity.id for polity, profile in rows if any(stat(polity, key) != getattr(profile, key) for key in MIRRORED)]


async def mirror_polity_stats(session: AsyncSession, key: int) -> None:
    polity = await session.get(EntityRow, key)
    profile = await session.get(PolityProfileRow, key)
    if polity is not None and profile is not None:
        set_stats(polity, **{name: getattr(profile, name) for name in MIRRORED})
