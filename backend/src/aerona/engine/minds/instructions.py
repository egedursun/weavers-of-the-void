from itertools import combinations

from sqlalchemy import select

from aerona.catalog.life.minds import CONTRARY
from aerona.constants.units import PERCENT
from aerona.db.tables.constructs import InstructionOrderRow, InstructionSetRow
from aerona.engine.context import TickContext

CONFLICT_STEP = 25


def clash(first: InstructionOrderRow, second: InstructionOrderRow) -> bool:
    if frozenset({first.kind, second.kind}) not in CONTRARY:
        return False
    return first.target_node_id is None or second.target_node_id is None or first.target_node_id == second.target_node_id


async def conflict_of(ctx: TickContext, node_id: int) -> int:
    sets = select(InstructionSetRow.id).where(InstructionSetRow.owner_entity_id == node_id)
    orders = list(await ctx.session.scalars(select(InstructionOrderRow).where(InstructionOrderRow.set_id.in_(sets), InstructionOrderRow.lapsed.is_(False))))
    return min(PERCENT, CONFLICT_STEP * sum(1 for first, second in combinations(orders, 2) if clash(first, second)))
