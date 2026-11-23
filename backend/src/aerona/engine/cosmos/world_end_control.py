from collections.abc import Mapping
from typing import Any

from aerona.catalog.life.cosmos import SOURCED_CAUSES
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.world_ends import WORLD_END_FIELDS, WorldEndRow
from aerona.domain.enums.world import WorldType
from aerona.domain.enums.world_end import WorldEnd, WorldEndCause
from aerona.engine.context import TickContext
from aerona.engine.cosmos.world_ends import end_world
from aerona.engine.divine.control import apply, require_world
from aerona.engine.gatherings.control import allowed


async def declare_end(
    ctx: TickContext, world_id: int, state: WorldEnd, cause: WorldEndCause, new_type: WorldType | None, *, source_node_id: int | None = None
) -> WorldEndRow:
    world = await require_world(ctx, world_id)
    cosmos = await CosmosRepository(ctx.session).require_cosmos()
    if state is WorldEnd.FORGOTTEN and world.id == cosmos.primary_world_id:
        raise ValidationFailedError("You cannot forget your first world.")
    if state is WorldEnd.TRANSFIGURED and (new_type is None or new_type is world.world_type):
        raise ValidationFailedError("A world is transfigured into another kind of world; name the kind it becomes.")
    if source_node_id is not None and cause not in SOURCED_CAUSES:
        raise ValidationFailedError("Only a war or an outer hunger names what ended a world.")
    return await end_world(ctx, world, state, cause, new_type, source_node_id=source_node_id)


async def edit_end(ctx: TickContext, world_id: int, values: Mapping[str, Any], release: list[str]) -> WorldEndRow:
    row = await ctx.session.get(WorldEndRow, world_id)
    if row is None:
        raise NotFoundError("That world has not come to an end.")
    allowed(values, WORLD_END_FIELDS, "end of a world")
    cause = WorldEndCause(str(values.get("cause", row.cause)))
    if values.get("source_node_id") is not None and cause not in SOURCED_CAUSES:
        raise ValidationFailedError("Only a war or an outer hunger names what ended a world.")
    apply(row, values, release)
    if cause not in SOURCED_CAUSES:
        row.source_node_id = None
    await ctx.session.flush()
    return row


async def remove_end(ctx: TickContext, world_id: int) -> None:
    row = await ctx.session.get(WorldEndRow, world_id)
    if row is None:
        raise NotFoundError("That world has not come to an end.")
    await ctx.session.delete(row)
    await ctx.session.flush()
