import asyncio
import sqlite3
from collections.abc import AsyncIterator, Callable, Iterable, Sequence
from functools import partial
from typing import Any

from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

YIELD_EVERY = 64


class Pacer:
    def __init__(self) -> None:
        self.count = 0

    async def tick(self) -> None:
        self.count += 1
        if self.count % YIELD_EVERY == 0:
            await asyncio.sleep(0)


class InlineCursor:
    def __init__(self, cursor: sqlite3.Cursor, pacer: Pacer) -> None:
        self.cursor = cursor
        self.pacer = pacer

    async def __aenter__(self) -> "InlineCursor":
        return self

    async def __aexit__(self, *_: object) -> None:
        self.cursor.close()

    @property
    def description(self) -> Any:
        return self.cursor.description

    @property
    def rowcount(self) -> int:
        return self.cursor.rowcount

    @property
    def lastrowid(self) -> int | None:
        return self.cursor.lastrowid

    @property
    def arraysize(self) -> int:
        return self.cursor.arraysize

    @arraysize.setter
    def arraysize(self, value: int) -> None:
        self.cursor.arraysize = value

    async def execute(self, sql: str, parameters: Sequence[Any] | dict[str, Any] | None = None) -> "InlineCursor":
        await self.pacer.tick()
        if parameters is None:
            self.cursor.execute(sql)
        else:
            self.cursor.execute(sql, parameters)
        return self

    async def executemany(self, sql: str, parameters: Iterable[Sequence[Any] | dict[str, Any]]) -> "InlineCursor":
        await self.pacer.tick()
        self.cursor.executemany(sql, parameters)
        return self

    async def fetchone(self) -> Any:
        return self.cursor.fetchone()

    async def fetchmany(self, size: int | None = None) -> list[Any]:
        return self.cursor.fetchmany(self.cursor.arraysize if size is None else size)

    async def fetchall(self) -> list[Any]:
        return self.cursor.fetchall()

    async def close(self) -> None:
        self.cursor.close()

    async def __aiter__(self) -> AsyncIterator[Any]:
        for row in self.cursor:
            yield row


class Immediate:
    def put_nowait(self, item: tuple[asyncio.Future[Any], Callable[[], Any]]) -> None:
        future, function = item
        try:
            future.set_result(function())
        except Exception as error:
            future.set_exception(error)


class InlineConnection:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn: sqlite3.Connection | None = connection
        self._connection: sqlite3.Connection | None = connection
        self._tx = Immediate()
        self.pacer = Pacer()

    @property
    def live(self) -> sqlite3.Connection:
        if self._conn is None:
            raise ValueError("Connection closed")
        return self._conn

    @property
    def isolation_level(self) -> str | None:
        return self.live.isolation_level

    def cursor(self) -> InlineCursor:
        return InlineCursor(self.live.cursor(), self.pacer)

    async def execute(self, sql: str, parameters: Sequence[Any] | dict[str, Any] | None = None) -> InlineCursor:
        return await self.cursor().execute(sql, parameters)

    async def commit(self) -> None:
        self.live.commit()

    async def rollback(self) -> None:
        self.live.rollback()

    async def create_function(self, name: str, arity: int, function: Callable[..., Any], *, deterministic: bool = False) -> None:
        self.live.create_function(name, arity, function, deterministic=deterministic)

    async def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
        self._conn = self._connection = None

    def stop(self) -> None:
        if self._conn is not None:
            self._conn.close()
        self._conn = self._connection = None


async def connect_inline(database: str, **options: Any) -> InlineConnection:
    return InlineConnection(sqlite3.connect(database, check_same_thread=False, **{key: value for key, value in options.items() if key != "check_same_thread"}))


def inline_engine(url: str) -> AsyncEngine:
    database = make_url(url).database
    if not database or database == ":memory:" or database.startswith("file:"):
        return create_async_engine(url, future=True)
    return create_async_engine(url, future=True, async_creator=partial(connect_inline, database))
