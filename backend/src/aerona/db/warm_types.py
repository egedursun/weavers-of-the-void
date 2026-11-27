from sqlalchemy import select

from aerona.db.base import Base
from aerona.db.session import Database

WARMED: set[str] = set()


async def warm_column_types(database: Database) -> None:
    dialect = database.engine.dialect.name
    if dialect in WARMED:
        return
    async with database.read() as session:
        for mapper in sorted(Base.registry.mappers, key=lambda item: item.class_.__name__):
            await session.execute(select(mapper.class_).limit(0))
    WARMED.add(dialect)
