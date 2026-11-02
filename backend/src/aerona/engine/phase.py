from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from aerona.engine.context import TickContext

PhaseFunction = Callable[[TickContext], Awaitable[None]]


@dataclass(frozen=True)
class Phase:
    name: str
    run: PhaseFunction
