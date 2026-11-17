from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession


class Keyed(Protocol):
    @property
    def id(self) -> int | None: ...


async def stored_id(session: AsyncSession, row: Keyed) -> int:
    if row.id is None:
        await session.flush()
    found = row.id
    if found is None:
        raise ValueError("The row has no id after a flush.")
    return found
