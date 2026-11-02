from statistics import median_high

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.meta import MapSnapshotRow


async def population_at(session: AsyncSession, epoch: int) -> dict[int, int] | None:
    rows = list(await session.scalars(select(MapSnapshotRow).where(MapSnapshotRow.epoch == epoch)))
    if not rows:
        return None
    merged: dict[int, int] = {}
    for row in rows:
        merged.update(row.data.population)
    return merged


def loss_pct(now: int, before: int) -> float:
    return (before - now) * PERCENT / before if before > 0 else 0.0


def median_of(values: list[int]) -> int:
    return median_high(values) if values else 0
