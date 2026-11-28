from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.calendar_slots import SLOTS
from aerona.db.remembered import told_of
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import TraditionProfileRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import SlotOpening

ORIGIN = "origin_entity_id"
REMEMBERING = sorted(slot for slot, spec in SLOTS.items() if spec.opening is SlotOpening.REMEMBERED)


async def remembrances_forgetting(session: AsyncSession) -> list[int]:
    telling = select(BondRow.source_node_id).where(BondRow.kind == BondKind.TELLS_OF, BondRow.state == BondState.ACTIVE)
    rows = await session.scalars(
        select(TraditionProfileRow)
        .where(
            TraditionProfileRow.calendar_slot.in_(REMEMBERING),
            TraditionProfileRow.notable_year_id.is_(None),
            TraditionProfileRow.origin_entity_id.is_(None),
            TraditionProfileRow.tradition_entity_id.in_(telling),
        )
        .order_by(TraditionProfileRow.tradition_entity_id)
    )
    return [row.tradition_entity_id for row in rows if ORIGIN not in (row.locked or [])]


async def remember_what_it_tells(session: AsyncSession, tradition_id: int) -> None:
    row = await session.get(TraditionProfileRow, tradition_id)
    if row is None or row.origin_entity_id is not None or ORIGIN in (row.locked or []):
        return
    row.origin_entity_id = await told_of(session, tradition_id)
