from aerona.db.tables.operations import AdmiraltyRow
from aerona.db.tables.polity import TreatyClauseRow
from aerona.engine.context import TickContext


def cap_of(ctx: TickContext, clause: TreatyClauseRow) -> int:
    value = clause.params.get("tonnage", clause.params.get("amount", ctx.rules.admiralty.fleet_limit))
    return value if isinstance(value, int) and not isinstance(value, bool) else ctx.rules.admiralty.fleet_limit


async def over_limit(ctx: TickContext, clause: TreatyClauseRow) -> bool:
    if clause.obligor_node_id is None:
        return False
    row = await ctx.session.get(AdmiraltyRow, clause.obligor_node_id)
    return row is not None and row.tonnage - row.concealed > cap_of(ctx, clause)
