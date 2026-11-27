from collections.abc import Awaitable, Callable, Hashable
from typing import Any
from weakref import WeakKeyDictionary

from aerona.db.session import Database

STATE_MEMO_KEYS = 16
MEMOS: WeakKeyDictionary[Database, dict[Hashable, tuple[int, Any]]] = WeakKeyDictionary()


async def per_state[T](database: Database, key: Hashable, build: Callable[[], Awaitable[T]]) -> T:
    memo = MEMOS.setdefault(database, {})
    generation = database.generation
    found = memo.get(key)
    if found is not None and found[0] == generation:
        value: T = found[1]
        return value
    built = await build()
    memo.pop(key, None)
    memo[key] = (generation, built)
    while len(memo) > STATE_MEMO_KEYS:
        memo.pop(next(iter(memo)))
    return built
