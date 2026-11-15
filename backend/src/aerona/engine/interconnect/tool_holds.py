from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import cache

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.interconnect import ModifierRow
from aerona.db.write_guard import HELD_SCOPE, RESTORED, WRITE_GUARD, HeldScope
from aerona.domain.enums.modifier import ModifierSource
from aerona.engine.interconnect.catalog import REGISTERED
from aerona.engine.interconnect.registry import suppression_key


@cache
def tool_mechanics(tool: str) -> frozenset[str]:
    return frozenset(mechanic.key for mechanic in REGISTERED.values() if tool in mechanic.tools)


async def tool_scope(session: AsyncSession, epoch: int, tool: str) -> HeldScope:
    keys = sorted(suppression_key(key) for key in tool_mechanics(tool))
    if not keys:
        return HeldScope(None, frozenset())
    nodes = await session.scalars(
        select(ModifierRow.target_node_id).where(
            ModifierRow.source_kind == ModifierSource.SUPPRESSION,
            ModifierRow.target_key.in_(keys),
            ModifierRow.start_epoch <= epoch,
            or_(ModifierRow.end_epoch.is_(None), ModifierRow.end_epoch >= epoch),
        )
    )
    return HeldScope(None, frozenset(nodes))


@asynccontextmanager
async def tool_holds(session: AsyncSession, epoch: int, tool: str) -> AsyncIterator[list[str]]:
    scope = await tool_scope(session, epoch, tool)
    restored: list[str] = []
    token = HELD_SCOPE.set(scope)
    write_token = WRITE_GUARD.set(lambda node_id, _key: node_id in scope.nodes)
    restored_token = RESTORED.set(restored)
    try:
        yield restored
    finally:
        RESTORED.reset(restored_token)
        WRITE_GUARD.reset(write_token)
        HELD_SCOPE.reset(token)
