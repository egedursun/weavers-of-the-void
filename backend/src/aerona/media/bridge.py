import asyncio
import io
from collections.abc import AsyncGenerator, Awaitable, Callable, Coroutine
from typing import Any

from aerona.media.store import MediaObject, MediaStore


def run_in_loop[T](loop: asyncio.AbstractEventLoop, coroutine: Coroutine[Any, Any, T]) -> T:
    return asyncio.run_coroutine_threadsafe(coroutine, loop).result()


async def _pull(chunks: AsyncGenerator[bytes]) -> bytes | None:
    try:
        return await anext(chunks)
    except StopAsyncIteration:
        return None


class BlockingObjectReader(io.RawIOBase):
    def __init__(self, opened: MediaObject, loop: asyncio.AbstractEventLoop) -> None:
        super().__init__()
        self._opened = opened
        self._loop = loop
        self._buffer = bytearray()
        self._finished = False

    def readable(self) -> bool:
        return True

    def readinto(self, target: Any) -> int:
        view = memoryview(target).cast("B")
        while not self._buffer and not self._finished:
            chunk = run_in_loop(self._loop, _pull(self._opened.chunks))
            if chunk is None:
                self._finished = True
            else:
                self._buffer.extend(chunk)
        count = min(len(view), len(self._buffer))
        view[:count] = self._buffer[:count]
        del self._buffer[:count]
        return count

    def close(self) -> None:
        if not self.closed:
            run_in_loop(self._loop, self._opened.aclose())
        super().close()


def blocking_opener(store: MediaStore, loop: asyncio.AbstractEventLoop) -> Callable[[str], BlockingObjectReader | None]:
    def open_object(key: str) -> BlockingObjectReader | None:
        opened = run_in_loop(loop, store.get(key))
        return None if opened is None else BlockingObjectReader(opened, loop)

    return open_object


def blocking_call[T](loop: asyncio.AbstractEventLoop, function: Callable[..., Awaitable[T]]) -> Callable[..., T]:
    def call(*arguments: Any) -> T:
        async def invoke() -> T:
            return await function(*arguments)

        return run_in_loop(loop, invoke())

    return call
