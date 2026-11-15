from collections.abc import Mapping
from typing import Any

from sqlalchemy import delete

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.prehistory import (
    DEEP_TIME_FIELDS,
    PREHISTORY_EVENT_FIELDS,
    PREHISTORY_FIELDS,
    DeepTimeEventRow,
    DeepTimeRunRow,
    PrehistoryEventRow,
    PrehistoryRow,
)
from aerona.domain.enums.prehistory import DeepTimeState, PrehistoryState
from aerona.engine.context import TickContext
from aerona.engine.divine.control import apply, require_world
from aerona.engine.gatherings.control import allowed
from aerona.engine.prehistory.digest import lore_free, prehistory_of

OPEN_STATES = frozenset({PrehistoryState.PLANNED, PrehistoryState.ABORTED})


async def require_prehistory(ctx: TickContext, world_id: int) -> PrehistoryRow:
    row = await ctx.session.get(PrehistoryRow, world_id)
    if row is None:
        raise NotFoundError("That world has no prehistory.")
    return row


async def configure(ctx: TickContext, world_id: int, epochs: int, resolution: int) -> PrehistoryRow:
    world = await require_world(ctx, world_id)
    row = await prehistory_of(ctx, world, epochs, resolution)
    if row.state not in OPEN_STATES:
        raise ValidationFailedError("A prehistory that is running or done keeps its length; strike its record out to plan another.")
    row.epochs, row.resolution = epochs, resolution
    await ctx.session.flush()
    return row


async def seed(ctx: TickContext, world_id: int, epochs: int, resolution: int) -> PrehistoryRow:
    world = await require_world(ctx, world_id)
    if not await lore_free(ctx, world.id):
        raise ValidationFailedError("Only a world still empty of lore can be given a prehistory; this world's story has begun.")
    return await configure(ctx, world.id, epochs, resolution)


async def ready(ctx: TickContext, world_id: int) -> PrehistoryRow:
    row = await require_prehistory(ctx, world_id)
    if row.state not in OPEN_STATES:
        raise ValidationFailedError("Only a planned or stopped prehistory can be run.")
    return row


async def abort(ctx: TickContext, world_id: int) -> PrehistoryRow:
    row = await require_prehistory(ctx, world_id)
    if row.state is not PrehistoryState.RUNNING:
        raise ValidationFailedError("Only a running prehistory can be stopped.")
    row.state = PrehistoryState.ABORTED
    await ctx.session.flush()
    return row


async def edit(ctx: TickContext, world_id: int, values: Mapping[str, Any], release: list[str]) -> PrehistoryRow:
    row = await require_prehistory(ctx, world_id)
    allowed(values, PREHISTORY_FIELDS, "prehistory")
    apply(row, values, release)
    await ctx.session.flush()
    return row


async def remove(ctx: TickContext, world_id: int) -> int:
    row = await require_prehistory(ctx, world_id)
    if row.state is PrehistoryState.RUNNING:
        raise ValidationFailedError("Stop the prehistory before striking out its record.")
    result = await ctx.session.execute(delete(PrehistoryEventRow).where(PrehistoryEventRow.world_id == world_id))
    await ctx.session.delete(row)
    await ctx.session.flush()
    return int(getattr(result, "rowcount", 0) or 0)


async def edit_event(ctx: TickContext, event_id: int, values: Mapping[str, Any], release: list[str]) -> PrehistoryEventRow:
    row = await ctx.session.get(PrehistoryEventRow, event_id)
    if row is None:
        raise NotFoundError("No such happening of a prehistory.")
    allowed(values, PREHISTORY_EVENT_FIELDS, "happening of a prehistory")
    apply(row, values, release)
    await ctx.session.flush()
    return row


async def remove_event(ctx: TickContext, event_id: int) -> None:
    row = await ctx.session.get(PrehistoryEventRow, event_id)
    if row is None:
        raise NotFoundError("No such happening of a prehistory.")
    await ctx.session.delete(row)
    await ctx.session.flush()


async def open_run(ctx: TickContext, epochs: int) -> DeepTimeRunRow:
    if epochs > ctx.rules.prehistory.deep_time_max_epochs:
        raise ValidationFailedError(f"One fast-forward runs at most {ctx.rules.prehistory.deep_time_max_epochs} epochs.")
    run = DeepTimeRunRow(epochs=epochs, from_epoch=ctx.epoch, to_epoch=ctx.epoch, state=DeepTimeState.RUNNING, locked=[])
    ctx.session.add(run)
    await ctx.session.flush()
    return run


async def require_run(ctx: TickContext, run_id: int) -> DeepTimeRunRow:
    run = await ctx.session.get(DeepTimeRunRow, run_id)
    if run is None:
        raise NotFoundError("No such fast-forward of deep time.")
    return run


async def stop_run(ctx: TickContext, run_id: int) -> DeepTimeRunRow:
    run = await require_run(ctx, run_id)
    if run.state is not DeepTimeState.RUNNING:
        raise ValidationFailedError("Only a running fast-forward can be stopped.")
    run.state = DeepTimeState.STOPPED
    await ctx.session.flush()
    return run


async def edit_run(ctx: TickContext, run_id: int, values: Mapping[str, Any], release: list[str]) -> DeepTimeRunRow:
    run = await require_run(ctx, run_id)
    allowed(values, DEEP_TIME_FIELDS, "fast-forward of deep time")
    apply(run, values, release)
    await ctx.session.flush()
    return run


async def remove_run(ctx: TickContext, run_id: int) -> None:
    run = await require_run(ctx, run_id)
    if run.state is DeepTimeState.RUNNING:
        raise ValidationFailedError("Stop the fast-forward before striking out its record.")
    await ctx.session.delete(run)
    await ctx.session.flush()


async def edit_run_event(ctx: TickContext, event_id: int, values: Mapping[str, Any], release: list[str]) -> DeepTimeEventRow:
    row = await ctx.session.get(DeepTimeEventRow, event_id)
    if row is None:
        raise NotFoundError("No such happening of a fast-forward.")
    allowed(values, ("magnitude",), "happening of a fast-forward")
    apply(row, values, release)
    await ctx.session.flush()
    return row


async def remove_run_event(ctx: TickContext, event_id: int) -> None:
    row = await ctx.session.get(DeepTimeEventRow, event_id)
    if row is None:
        raise NotFoundError("No such happening of a fast-forward.")
    await ctx.session.delete(row)
    await ctx.session.flush()
