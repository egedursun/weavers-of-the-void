from collections import Counter
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.engine.interconnect.guards import CONSERVED_KEYS

Flows = Counter[tuple[str, str, int]]


@dataclass(frozen=True)
class StockSnapshot:
    values: dict[tuple[int, str], int]


async def snapshot(session: AsyncSession) -> StockSnapshot:
    values: dict[tuple[int, str], int] = {}
    for row in await session.scalars(select(EntityRow)):
        for key in CONSERVED_KEYS:
            value = getattr(row.stats, key, None)
            if isinstance(value, int):
                values[(row.id, key)] = value
    return StockSnapshot(values)


def totals_by_phase(flows: Flows) -> dict[tuple[str, str], int]:
    totals: Counter[tuple[str, str]] = Counter()
    for (phase, key, _), delta in flows.items():
        totals[(phase, key)] += delta
    return dict(totals)


async def residuals(session: AsyncSession, before: StockSnapshot, flows: Flows) -> dict[tuple[int, str], int]:
    after = await snapshot(session)
    moved: Counter[tuple[int, str]] = Counter()
    for (_, key, node_id), delta in flows.items():
        moved[(node_id, key)] += delta
    found = {item: after.values.get(item, 0) - value - moved.get(item, 0) for item, value in before.values.items()}
    return {item: value for item, value in found.items() if value}
