from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from aerona.domain.enums.providers import ModelRole
from aerona.llm.backends.base import ModelBackend


@dataclass(frozen=True)
class ModelRoute:
    provider: str
    model: str
    sees_images: bool | None
    open: Callable[[], Awaitable[ModelBackend]]

    @property
    def name(self) -> str:
        return f"{self.model} · {self.provider}" if self.model else self.provider


class RouteBook(Protocol):
    def routes(self, role: ModelRole) -> Sequence[ModelRoute]: ...


class NoRoutes:
    def routes(self, role: ModelRole) -> Sequence[ModelRoute]:
        del role
        return ()
