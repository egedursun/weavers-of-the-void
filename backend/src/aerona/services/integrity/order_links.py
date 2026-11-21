from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.orders import EconomicOrderRow, OrderTransitionRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.orders import AllocationMode, DistributionRule, OrderLabour, OwnershipRegime, TransitionStage

AXIS_VALUES: dict[str, frozenset[str]] = {
    "ownership": frozenset(item.value for item in OwnershipRegime),
    "allocation": frozenset(item.value for item in AllocationMode),
    "labour": frozenset(item.value for item in OrderLabour),
    "distribution": frozenset(item.value for item in DistributionRule),
}
OPEN_STAGES = (TransitionStage.PROCLAIMED, TransitionStage.TRANSFERRING)


async def doubled_orders(session: AsyncSession) -> list[int]:
    seen: set[tuple[int, str | None]] = set()
    found: list[int] = []
    for order in await session.scalars(select(EconomicOrderRow).order_by(EconomicOrderRow.id)):
        key = (order.polity_entity_id, order.sector.value if order.sector is not None else None)
        if key in seen:
            found.append(order.id)
        seen.add(key)
    return found


async def drop_order(session: AsyncSession, key: int) -> None:
    order = await session.get(EconomicOrderRow, key)
    if order is not None:
        await session.delete(order)


def stray_axes(axes: dict[str, str]) -> bool:
    return any(axis not in AXIS_VALUES or value not in AXIS_VALUES[axis] for axis, value in axes.items())


async def bad_axes(session: AsyncSession) -> list[int]:
    return [
        row.id
        for row in await session.scalars(select(OrderTransitionRow).order_by(OrderTransitionRow.id))
        if stray_axes(row.from_axes or {}) or stray_axes(row.to_axes or {})
    ]


async def clean_axes(session: AsyncSession, key: int) -> None:
    row = await session.get(OrderTransitionRow, key)
    if row is None:
        return
    row.from_axes = {axis: value for axis, value in (row.from_axes or {}).items() if axis in AXIS_VALUES and value in AXIS_VALUES[axis]}
    row.to_axes = {axis: value for axis, value in (row.to_axes or {}).items() if axis in AXIS_VALUES and value in AXIS_VALUES[axis]}


async def orphan_transitions(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await session.scalars(select(OrderTransitionRow).where(OrderTransitionRow.stage.in_(OPEN_STAGES)).order_by(OrderTransitionRow.id)):
        realm = await session.get(EntityRow, row.polity_entity_id)
        if realm is None or realm.status is not EntityStatus.CANON:
            found.append(row.id)
    return found


async def fail_transition(session: AsyncSession, key: int) -> None:
    row = await session.get(OrderTransitionRow, key)
    if row is not None:
        realm = await session.get(EntityRow, row.polity_entity_id)
        row.stage = TransitionStage.FAILED
        row.ended_epoch = realm.end_epoch if realm is not None and realm.end_epoch is not None else row.started_epoch
