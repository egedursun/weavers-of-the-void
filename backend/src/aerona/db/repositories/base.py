from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError
from aerona.db.base import Base


class Repository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def require[R: Base](self, model: type[R], key: Any, label: str) -> R:
        row = await self.session.get(model, key)
        if row is None:
            raise NotFoundError(f"No such {label}.")
        return row

    async def insert[R: Base](self, row: R) -> R:
        self.session.add(row)
        await self.session.flush()
        return row

    async def flush(self) -> None:
        await self.session.flush()
