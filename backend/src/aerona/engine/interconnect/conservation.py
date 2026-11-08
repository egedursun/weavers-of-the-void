from collections import Counter
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.routes import JourneyRow
from aerona.domain.enums.travel import JourneyStatus
from aerona.engine.interconnect.flows import SINKS, SOURCES, TRANSFERS, FlowCategory
from aerona.engine.interconnect.guards import CONSERVED_KEYS

BODY_COUNT = "bodies"
UNDERWAY = (JourneyStatus.UNDERWAY, JourneyStatus.WAITING, JourneyStatus.STRANDED)

Flows = Counter[tuple[str, str, int, str]]


@dataclass(frozen=True)
class StockSnapshot:
    values: dict[tuple[int, str], int]
    travelling: int = 0
    lost_on_the_road: int = 0


async def snapshot(session: AsyncSession) -> StockSnapshot:
    values: dict[tuple[int, str], int] = {}
    for row in await session.scalars(select(EntityRow)):
        for key in CONSERVED_KEYS:
            value = getattr(row.stats, key, None)
            if isinstance(value, int):
                values[(row.id, key)] = value
    travelling = await session.scalar(select(func.coalesce(func.sum(JourneyRow.population), 0)).where(JourneyRow.status.in_(UNDERWAY)))
    lost = await session.scalar(select(func.coalesce(func.sum(JourneyRow.population), 0)).where(JourneyRow.status == JourneyStatus.LOST))
    return StockSnapshot(values, int(travelling or 0), int(lost or 0))


def journey_imbalance(before: StockSnapshot, after: StockSnapshot, flows: Flows) -> int:
    moved = sum(delta for (_, key, _, category), delta in flows.items() if category == FlowCategory.JOURNEY.value and key in CONSERVED_KEYS)
    return moved + (after.travelling - before.travelling) + (after.lost_on_the_road - before.lost_on_the_road)


def totals_by_phase(flows: Flows) -> dict[tuple[str, str], int]:
    totals: Counter[tuple[str, str]] = Counter()
    for (phase, key, _, _), delta in flows.items():
        totals[(phase, key)] += delta
    return dict(totals)


def transfer_imbalance(flows: Flows) -> dict[tuple[str, str, str], int]:
    totals: Counter[tuple[str, str, str]] = Counter()
    for (phase, key, _, category), delta in flows.items():
        if FlowCategory(category) in TRANSFERS and category != FlowCategory.JOURNEY.value:
            totals[(phase, category, BODY_COUNT if key in CONSERVED_KEYS else key)] += delta
    return {item: value for item, value in totals.items() if value}


def wrong_signs(flows: Flows) -> dict[tuple[str, str, str], int]:
    totals: Counter[tuple[str, str, str]] = Counter()
    for (phase, key, _, category), delta in flows.items():
        totals[(phase, category, key)] += delta
    return {
        item: value
        for item, value in totals.items()
        if (FlowCategory(item[1]) in SINKS and value > 0) or (FlowCategory(item[1]) in SOURCES - {FlowCategory.CONVERSION, FlowCategory.GROWTH} and value < 0)
    }


def unexplained(flows: Flows) -> dict[tuple[str, str], int]:
    totals: Counter[tuple[str, str]] = Counter()
    for (phase, key, _, category), delta in flows.items():
        if category == FlowCategory.UNSPECIFIED.value:
            totals[(phase, key)] += delta
    return {item: value for item, value in totals.items() if value}


async def residuals(session: AsyncSession, before: StockSnapshot, flows: Flows) -> dict[tuple[int, str], int]:
    after = await snapshot(session)
    moved: Counter[tuple[int, str]] = Counter()
    for (_, key, node_id, _), delta in flows.items():
        moved[(node_id, key)] += delta
    items = sorted(set(before.values) | set(after.values))
    found = {item: after.values.get(item, 0) - before.values.get(item, 0) - moved.get(item, 0) for item in items}
    return {item: value for item, value in found.items() if value}
