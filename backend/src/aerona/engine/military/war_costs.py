from collections.abc import Mapping

from aerona.catalog.war_terms import PEACE_COSTS
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.domain.enums.military import PeaceTermKind
from aerona.domain.enums.war import WarSide
from aerona.engine.context import TickContext
from aerona.engine.primitives.stats import stat

Params = Mapping[str, int | str | bool]


async def peace_budget(ctx: TickContext, war: WarRow, victor_id: int) -> int:
    table = ctx.rules.war_conduct
    side = await ctx.session.get(WarSideRow, (war.id, victor_id))
    won = -war.score if side is not None and side.side is WarSide.DEFENDER else war.score
    return table.base_budget + max(0, won) * table.score_unit


async def term_cost(ctx: TickContext, kind: PeaceTermKind, params: Params, target_id: int | None) -> int:
    table = ctx.rules.war_conduct
    cost = PEACE_COSTS[kind]
    if kind is PeaceTermKind.CESSION and target_id is not None:
        land = await ctx.session.get(EntityRow, target_id)
        cost += (stat(land, "population") or 0) // max(1, table.cession_pop_per_cost) if land is not None else 0
    if kind is PeaceTermKind.TRIBUTE:
        epochs = params.get("epochs", ctx.rules.peace.treaty_epochs)
        cost += (epochs if isinstance(epochs, int) and not isinstance(epochs, bool) else 0) * table.tribute_cost_per_epoch
        amount = params.get("amount", 0)
        cost += (amount if isinstance(amount, int) and not isinstance(amount, bool) else 0) // max(1, table.tribute_amount_per_cost)
    return cost
