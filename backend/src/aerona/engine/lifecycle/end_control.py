from collections.abc import Mapping
from typing import Any

from sqlalchemy import delete

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.divine import BreachPointRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lifecycle_ends import LIFECYCLE_FIELDS, LifecycleStateRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.lifecycle_end import LifecycleCause, LifecycleKind, LifecycleState
from aerona.engine.context import TickContext
from aerona.engine.divine.control import apply
from aerona.engine.gatherings.control import allowed
from aerona.engine.lifecycle.ends import KIND_OF_TYPE, EndTally, keep_ends, move, seed_state, tend_one, wake
from aerona.engine.polity.control import lock


async def require_holder(ctx: TickContext, holder_id: int) -> tuple[EntityRow, LifecycleStateRow]:
    holder = await ctx.session.get(EntityRow, holder_id)
    if holder is None or holder.entity_type not in KIND_OF_TYPE:
        raise NotFoundError("No such ideology, theory, rite, disease or outer being.")
    row = await seed_state(ctx.session, holder, ctx.epoch)
    if row is None:
        raise NotFoundError("No such ideology, theory, rite, disease or outer being.")
    return holder, row


async def edit_state(ctx: TickContext, holder_id: int, values: Mapping[str, Any], release: list[str]) -> LifecycleStateRow:
    _, row = await require_holder(ctx, holder_id)
    allowed(values, LIFECYCLE_FIELDS, "life of a thing")
    apply(row, values, release)
    row.updated_epoch = ctx.epoch
    await ctx.session.flush()
    return row


async def reset_state(ctx: TickContext, holder_id: int) -> LifecycleStateRow:
    holder, row = await require_holder(ctx, holder_id)
    row.state, row.cause, row.idle_epochs, row.locked = LifecycleState.ACTIVE, LifecycleCause.LIVING, 0, []
    await tend_one(ctx, holder, row, EndTally())
    await ctx.session.flush()
    return row


async def destroy(ctx: TickContext, holder_id: int) -> LifecycleStateRow:
    holder, row = await require_holder(ctx, holder_id)
    if holder.entity_type is not EntityType.OUTER_BEING:
        raise ValidationFailedError("Only an outer being is destroyed for good; set the state of anything else.")
    await ctx.session.execute(delete(BreachPointRow).where(BreachPointRow.outer_entity_id == holder.id))
    await move(ctx, holder, row, LifecycleState.DESTROYED, LifecycleCause.GOD_ACT)
    row.locked = lock(row.locked, "state")
    await ctx.session.flush()
    return row


async def wake_now(ctx: TickContext, holder_id: int) -> LifecycleStateRow:
    holder, row = await require_holder(ctx, holder_id)
    if row.kind is LifecycleKind.DISEASE or row.kind is LifecycleKind.OUTER_BEING:
        raise ValidationFailedError("Only an ideology, theory or rite is woken from its texts.")
    if "state" in row.locked:
        raise ValidationFailedError("Its life is held fast.")
    if not await wake(ctx, holder, row, EndTally()):
        raise ValidationFailedError("Nothing of it survives that anyone could take up now.")
    await ctx.session.flush()
    return row


async def run_ends(ctx: TickContext) -> EndTally:
    tally = EndTally()
    await keep_ends(ctx, tally)
    return tally
