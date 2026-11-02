from sqlalchemy import delete, select

from aerona.constants.units import PERCENT
from aerona.db.tables.interconnect import ModifierRow
from aerona.domain.enums.modifier import ModifierOp
from aerona.engine.context import TickContext
from aerona.engine.phase import Phase
from aerona.engine.primitives.modifiers import NEUTRAL_MULTIPLIER, decayed


async def modifier_upkeep(ctx: TickContext) -> None:
    rules = ctx.rules.modifiers
    expired = await ctx.session.execute(delete(ModifierRow).where(ModifierRow.end_epoch.is_not(None), ModifierRow.end_epoch < ctx.epoch))
    ctx.count("modifiers_expired", int(getattr(expired, "rowcount", 0) or 0))
    faded = 0
    for row in list(await ctx.session.scalars(select(ModifierRow).where(ModifierRow.decay_pct.is_not(None), ModifierRow.decay_pct > 0))):
        if row.start_epoch >= ctx.epoch:
            continue
        row.magnitude = decayed(row)
        spent = (
            abs(row.magnitude) < rules.decayed_add_drop_below
            if row.op is ModifierOp.ADD
            else abs(row.magnitude - NEUTRAL_MULTIPLIER) * PERCENT < rules.decayed_multiplier_drop_within_pct
        )
        if spent:
            await ctx.session.delete(row)
            faded += 1
    ctx.count("modifiers_faded", faded)


PHASES = (Phase("modifier_upkeep", modifier_upkeep),)
