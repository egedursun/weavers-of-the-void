import asyncio
import inspect
from collections.abc import Awaitable, Callable

WAIT_SECONDS = 120.0
STEP_SECONDS = 0.02


async def until(check: Callable[[], bool | Awaitable[bool]], seconds: float = WAIT_SECONDS, step: float = STEP_SECONDS) -> bool:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + seconds
    while True:
        outcome = check()
        if inspect.isawaitable(outcome):
            outcome = await outcome
        if outcome:
            return True
        if loop.time() >= deadline:
            return False
        await asyncio.sleep(step)
