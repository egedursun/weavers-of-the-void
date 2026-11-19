from sqlalchemy import select

from aerona.db.tables.customs import WelfareRow
from aerona.db.tables.endowments import EndowmentRow
from aerona.db.write_guard import held
from aerona.domain.enums.endowments import EndowmentCapital, EndowmentPurpose
from aerona.engine.context import TickContext

UPKEEP_YEARS = 20
LEAST_CAPITAL = 50


async def seed_endowments(ctx: TickContext) -> int:
    endowed = set(await ctx.session.scalars(select(EndowmentRow.beneficiary_node_id)))
    made = 0
    for house in list(await ctx.session.scalars(select(WelfareRow).where(WelfareRow.patron_node_id.is_not(None)).order_by(WelfareRow.structure_entity_id))):
        patron = house.patron_node_id
        if patron is None or house.structure_entity_id in endowed or held(house.structure_entity_id) or held(patron):
            continue
        ctx.session.add(
            EndowmentRow(
                founder_node_id=patron,
                beneficiary_node_id=house.structure_entity_id,
                trustee_node_id=patron,
                purpose=EndowmentPurpose.RELIEF,
                capital_kind=EndowmentCapital.RENTS,
                capital=max(LEAST_CAPITAL, house.upkeep * UPKEEP_YEARS),
                founded_epoch=ctx.epoch,
                locked=[],
            )
        )
        made += 1
    await ctx.session.flush()
    return made
