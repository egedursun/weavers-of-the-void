from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from aerona.db.read_memo import memo_of, table_names
from aerona.db.tables.entities import EntityRow


async def kept_rows[R](session: AsyncSession, model: type[R], column: InstrumentedAttribute[Any], key: int) -> list[R]:
    name = f"kept_rows:{getattr(model, '__tablename__', model.__name__)}:{column.key}"
    tables = table_names((model, EntityRow))
    memo = memo_of(session, name, tables, live=True)
    found: list[R] | None = memo.get(key) if memo is not None else None
    if found is None:
        found = list(await session.scalars(select(model).where(column == key)))
        after = memo_of(session, name, tables, live=True)
        if after is not None:
            after[key] = found
    return list(found)
