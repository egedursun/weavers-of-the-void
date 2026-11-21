from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.honours import HonourHeldRow, HonourKindRow
from aerona.domain.enums.honours import HonourPrivilege

PRIVILEGES = frozenset(privilege.value for privilege in HonourPrivilege)


async def overfull_honours(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for kind in await session.scalars(select(HonourKindRow).where(HonourKindRow.holder_limit > 0).order_by(HonourKindRow.id)):
        live = list(
            await session.scalars(
                select(HonourHeldRow.id).where(HonourHeldRow.kind_id == kind.id, HonourHeldRow.revoked_epoch.is_(None)).order_by(HonourHeldRow.id)
            )
        )
        found.extend(live[kind.holder_limit :])
    return found


async def lapse_honour(session: AsyncSession, key: int) -> None:
    row = await session.get(HonourHeldRow, key)
    if row is not None:
        await session.delete(row)


async def odd_privileges(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(HonourKindRow).order_by(HonourKindRow.id))
    return [row.id for row in rows if not set(row.privileges or []) <= PRIVILEGES]


async def mend_privileges(session: AsyncSession, key: int) -> None:
    row = await session.get(HonourKindRow, key)
    if row is not None:
        row.privileges = sorted(set(row.privileges or []) & PRIVILEGES)
