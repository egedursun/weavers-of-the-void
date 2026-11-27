from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.calendar_slots import SLOTS
from aerona.db.fixups import fixup_due
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.culture import RiteProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.culture import CalendarSlot, SlotOpening

WAR_NEED_FIXUP = "rites.w52_war_need"
SLOT_VALUES = frozenset(slot.value for slot in CalendarSlot)


async def keep_war_needs(session: AsyncSession) -> int:
    if not await fixup_due(session, WAR_NEED_FIXUP):
        return 0
    changed = 0
    for row in await session.scalars(select(RiteProfileRow).order_by(RiteProfileRow.rite_entity_id)):
        needs = dict(row.requirements or {})
        slot = needs.get("slot")
        warlike = isinstance(slot, str) and slot in SLOT_VALUES and SLOTS[CalendarSlot(slot)].opening is SlotOpening.WAR_SEASON
        if warlike and "war" not in needs and "requirements" not in (row.locked or []) and not held(row.rite_entity_id):
            row.requirements = {**needs, "war": True}
            changed += 1
    session.add(AppliedFixupRow(key=WAR_NEED_FIXUP, result={"rites": changed}))
    await session.flush()
    return changed
