from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.schemas.records import ChronicleLineRecord
from aerona.api.views.common import chronicle_lines
from aerona.core.errors import NotFoundError
from aerona.db.repositories.chronicle import shown_lines
from aerona.db.tables.celestial import StarRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.chronicle import ChronicleKind, ChronicleScope

TRACE_KINDS = (ChronicleKind.CREATOR_HAND, ChronicleKind.WORLD_BIRTH, ChronicleKind.COUNCIL, ChronicleKind.DIVINE_SIGN, ChronicleKind.ORDER)


async def scope_statement(session: AsyncSession, scope: ChronicleScope, scope_id: int | None) -> Select[Any]:
    statement = select(ChronicleRow).where(shown_lines())
    if scope is ChronicleScope.CREATOR:
        return statement.where(ChronicleRow.kind.in_(TRACE_KINDS))
    if scope_id is None:
        raise NotFoundError("Name the record whose chronicle to read.")
    if scope is ChronicleScope.WORLD:
        return statement.where(ChronicleRow.world_id == scope_id)
    if scope is ChronicleScope.SON:
        return statement.where(ChronicleRow.son_id == scope_id)
    if scope is ChronicleScope.STAR:
        star = await session.get(StarRow, scope_id)
        if star is None:
            raise NotFoundError("No such star.")
        return statement.where(ChronicleRow.kind == ChronicleKind.STAR, ChronicleRow.text.contains(star.name))
    if scope is ChronicleScope.FOREIGN_GOD:
        god = await session.get(ForeignGodRow, scope_id)
        if god is None:
            raise NotFoundError("No such god.")
        return statement.where(ChronicleRow.kind == ChronicleKind.FOREIGN_GOD, ChronicleRow.world_id == god.world_id)
    name = await session.scalar(select(NodeRow.name).where(NodeRow.id == scope_id))
    if not name:
        raise NotFoundError("No such record.")
    return statement.where(ChronicleRow.text.contains(name))


async def scoped_lines(session: AsyncSession, scope: ChronicleScope, scope_id: int | None, *, offset: int, limit: int) -> tuple[list[ChronicleLineRecord], int]:
    statement = await scope_statement(session, scope, scope_id)
    total = int(await session.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = list(await session.scalars(statement.order_by(ChronicleRow.id.desc()).offset(offset).limit(limit)))
    return await chronicle_lines(session, list(reversed(rows))), total
