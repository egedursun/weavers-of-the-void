import asyncio
import threading
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from aerona.db.session import Database

ENGINE_THREADS = ThreadPoolExecutor(max_workers=1, thread_name_prefix="engine")
BOOK_THREADS = ThreadPoolExecutor(max_workers=1, thread_name_prefix="books")


def threadsafe[**P](loop: asyncio.AbstractEventLoop, call: Callable[P, Any]) -> Callable[P, None]:
    def forwarded(*args: P.args, **kwargs: P.kwargs) -> None:
        if loop.is_closed():
            return
        loop.call_soon_threadsafe(lambda: call(*args, **kwargs))

    return forwarded


async def off_loop[T](database: Database, work: Callable[[Database, threading.Event], Awaitable[T]], threads: ThreadPoolExecutor) -> T:
    stop = threading.Event()

    def run() -> T:
        async def inner() -> T:
            sibling = database.sibling()
            try:
                return await work(sibling, stop)
            finally:
                await sibling.close()

        return asyncio.run(inner())

    future = asyncio.get_running_loop().run_in_executor(threads, run)
    try:
        return await asyncio.shield(future)
    except asyncio.CancelledError:
        stop.set()
        await asyncio.wait({future})
        raise
