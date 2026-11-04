from sqlalchemy import select

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.happenings import EventCasualtyRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.happening import EventPhase
from aerona.engine.context import TickContext
from aerona.engine.happenings.profile import flow_of, record_casualties

CASUALTIES_FIXUP = "events.casualties_backfill"
LIVES_LOST = "lives lost"


def lives_in(description: str | None) -> int:
    words = (description or "").split()
    if len(words) < 3 or " ".join(words[1:3]) != LIVES_LOST or not words[0].isdigit():
        return 0
    return int(words[0])


async def backfill_casualties(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, CASUALTIES_FIXUP) is not None:
        return 0
    counted = set(await ctx.session.scalars(select(EventCasualtyRow.event_entity_id).distinct()))
    bonds = await ctx.session.scalars(
        select(BondRow)
        .join(EntityRow, EntityRow.id == BondRow.source_node_id)
        .where(BondRow.kind == BondKind.CAUSED, EntityRow.entity_type == EntityType.EVENT, EntityRow.status != EntityStatus.REJECTED)
        .order_by(BondRow.id)
    )
    recorded = 0
    for bond in list(bonds):
        lost = lives_in(bond.description)
        if not lost or bond.source_node_id in counted:
            continue
        event = await ctx.session.get(EntityRow, bond.source_node_id)
        community = await ctx.session.get(EntityRow, bond.target_node_id)
        if event is None or community is None:
            continue
        recorded += await record_casualties(ctx, event.id, community, lost, category=flow_of(event.engine_kind), phase=EventPhase.ONSET)
    ctx.session.add(AppliedFixupRow(key=CASUALTIES_FIXUP, result={"dead": recorded}))
    await ctx.session.flush()
    return recorded
