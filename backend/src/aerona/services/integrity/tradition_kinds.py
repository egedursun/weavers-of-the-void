from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.lore import FUNCTIONS, SUBTYPE_KINDS, TRADITIONS, slot_fit
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.culture import TraditionEffectRow, TraditionProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityOrigin


async def traditions_unlike_their_kind(session: AsyncSession) -> list[int]:
    rows = await session.execute(
        select(TraditionProfileRow, EntityRow.subtype)
        .join(EntityRow, EntityRow.id == TraditionProfileRow.tradition_entity_id)
        .where(EntityRow.origin == EntityOrigin.ENGINE, EntityRow.subtype.in_(sorted(SUBTYPE_KINDS)), TraditionProfileRow.custom_kind_id.is_(None))
        .order_by(TraditionProfileRow.tradition_entity_id)
    )
    return [
        row.tradition_entity_id
        for row, subtype in rows
        if row.kind is not SUBTYPE_KINDS[subtype or ""] and "kind" not in row.locked and not held(row.tradition_entity_id)
    ]


async def give_tradition_its_kind(session: AsyncSession, tradition_id: int) -> None:
    row = await session.get(TraditionProfileRow, tradition_id)
    tradition = await session.get(EntityRow, tradition_id)
    if row is None or tradition is None or tradition.subtype not in SUBTYPE_KINDS or "kind" in row.locked:
        return
    kind = SUBTYPE_KINDS[tradition.subtype or ""]
    rules = await CosmosRepository(session).rules()
    row.kind = kind
    if "calendar_slot" not in row.locked:
        row.calendar_slot = slot_fit(kind, row.stage)
    if "effects" not in row.locked:
        row.effects = dict(TRADITIONS[kind].effects)
        await session.execute(delete(TraditionEffectRow).where(TraditionEffectRow.tradition_entity_id == tradition_id))
    if "cost" not in row.locked:
        amount = FUNCTIONS[kind].cost(rules)
        row.cost = {resource: amount for resource in TRADITIONS[kind].cost} if amount else {}
