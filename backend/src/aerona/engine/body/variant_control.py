from collections.abc import Mapping
from typing import Any

from aerona.core.errors import NotFoundError
from aerona.db.tables.biology import BIOLOGY_EDITABLE, BiologyRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.biology import BiologyVariant
from aerona.engine.body.variants import HOLDER_TYPES, BiologyTally, keep_biology, rederive, reset_biology, seed_biology, variants_of
from aerona.engine.context import TickContext
from aerona.engine.divine.control import apply
from aerona.engine.gatherings.control import allowed
from aerona.engine.polity.control import lock


async def require_holder(ctx: TickContext, holder_id: int) -> EntityRow:
    holder = await ctx.session.get(EntityRow, holder_id)
    if holder is None or holder.entity_type not in HOLDER_TYPES:
        raise NotFoundError("No such people or species.")
    return holder


async def edit_biology(ctx: TickContext, holder_id: int, values: Mapping[str, Any], release: list[str]) -> BiologyRow:
    holder = await require_holder(ctx, holder_id)
    allowed(values, BIOLOGY_EDITABLE, "biology")
    row = await seed_biology(ctx.session, holder.id, ctx.epoch)
    apply(row, values, release)
    rederive(row)
    row.updated_epoch = ctx.epoch
    await ctx.session.flush()
    return row


async def set_variant(ctx: TickContext, holder_id: int, variant: BiologyVariant, present: bool, *, hold: bool = True) -> BiologyRow:
    holder = await require_holder(ctx, holder_id)
    row = await seed_biology(ctx.session, holder.id, ctx.epoch)
    kept = {value for value in row.variants if value != variant.value}
    row.variants = [item.value for item in variants_of(kept | {variant.value} if present else kept)]
    if hold:
        row.locked = lock(row.locked, "variants")
    rederive(row)
    row.updated_epoch = ctx.epoch
    await ctx.session.flush()
    return row


async def restore_biology(ctx: TickContext, holder_id: int) -> BiologyRow:
    holder = await require_holder(ctx, holder_id)
    return await reset_biology(ctx.session, holder.id, ctx.epoch)


async def run_biology(ctx: TickContext) -> BiologyTally:
    tally = BiologyTally()
    await keep_biology(ctx, tally)
    return tally
