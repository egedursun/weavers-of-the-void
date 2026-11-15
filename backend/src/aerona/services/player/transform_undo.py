from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.base import Base
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.transform import TransformationRow
from aerona.db.types import PydanticJSON
from aerona.domain.enums.transform import TransformState
from aerona.engine.context import TickContext
from aerona.engine.primitives.stats import set_stats
from aerona.engine.transform.ledger import ADDED, MADE, STAT


def mapped_by_table() -> dict[str, type[Any]]:
    return {str(getattr(mapper.local_table, "name", "")): mapper.class_ for mapper in Base.registry.mappers}


def restored(row: Any, column: str, raw: Any) -> Any:
    kind = type(row).__table__.c[column].type
    if raw is None:
        return None
    if isinstance(kind, PydanticJSON):
        return kind.adapter.validate_python(raw)
    enum_class = getattr(kind, "enum_class", None)
    return enum_class(raw) if enum_class is not None else raw


async def undo(session: AsyncSession, steps: list[dict[str, Any]]) -> int:
    tables = mapped_by_table()
    undone = 0
    for step in reversed(steps):
        if step["op"] == MADE:
            node = await session.get(NodeRow, step["node"])
            if node is not None:
                await session.delete(node)
                undone += 1
            continue
        if step["op"] == STAT:
            entity = await session.get(EntityRow, step["node"])
            if entity is not None:
                set_stats(entity, **{step["key"]: step["before"]})
                undone += 1
            continue
        model = tables.get(step["table"])
        if model is None:
            continue
        row = await session.get(model, tuple(step["key"]))
        if row is None:
            continue
        if step["op"] == ADDED:
            await session.delete(row)
        else:
            setattr(row, step["column"], restored(row, step["column"], step["before"]))
        undone += 1
    await session.flush()
    return undone


async def revert(ctx: TickContext, transformation_id: int) -> TransformationRow:
    row = await ctx.session.get(TransformationRow, transformation_id)
    if row is None:
        raise NotFoundError("No such transformation.")
    if row.state is TransformState.REVERTED:
        raise ValidationFailedError("This transformation has already been reverted.")
    if row.epoch != ctx.epoch:
        raise ValidationFailedError("Only a transformation of this epoch can be reverted.")
    if not row.undo:
        raise ValidationFailedError("This transformation kept no ledger to undo.")
    await undo(ctx.session, row.undo)
    row.state = TransformState.REVERTED
    await ctx.session.flush()
    return row
