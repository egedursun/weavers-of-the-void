from collections.abc import Mapping
from typing import Any

from aerona.db.tables.world_views import WORLD_VIEW_FIELDS, WorldViewRow
from aerona.engine.context import TickContext
from aerona.engine.cosmos.world_views import ViewTally, keep_views, reset_view, seed_view
from aerona.engine.divine.control import apply, require_world
from aerona.engine.gatherings.control import allowed


async def edit_view(ctx: TickContext, world_id: int, values: Mapping[str, Any], release: list[str]) -> WorldViewRow:
    world = await require_world(ctx, world_id)
    allowed(values, WORLD_VIEW_FIELDS, "world view")
    row = await seed_view(ctx.session, ctx.rules, world, ctx.epoch)
    apply(row, values, release)
    row.updated_epoch = ctx.epoch
    await ctx.session.flush()
    return row


async def restore_view(ctx: TickContext, world_id: int) -> WorldViewRow:
    world = await require_world(ctx, world_id)
    row = await reset_view(ctx.session, ctx.rules, world, ctx.epoch)
    row.locked = []
    await ctx.session.flush()
    return row


async def run_views(ctx: TickContext) -> ViewTally:
    tally = ViewTally()
    await keep_views(ctx, tally)
    return tally
