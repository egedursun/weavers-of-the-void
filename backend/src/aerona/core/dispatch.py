from collections.abc import Callable, Collection
from enum import Enum

from aerona.core.total import IncompleteTableError


class Handlers[K: Enum, V](dict[K, V]):
    def __init__(self, kind: type[K]) -> None:
        super().__init__()
        self.kind = kind

    def on(self, *keys: K) -> Callable[[V], V]:
        def register(handler: V) -> V:
            for key in keys:
                if key in self:
                    raise IncompleteTableError(f"{key} of {self.kind.__name__} has two handlers")
                self[key] = handler
            return handler

        return register

    def seal(self, *, without: Collection[K] = ()) -> "Handlers[K, V]":
        expected = {member for member in self.kind if member not in without}
        if set(self) != expected:
            missing = sorted(str(member.value) for member in expected - set(self))
            extra = sorted(str(member.value) for member in set(self) - expected)
            raise IncompleteTableError(f"the handlers of {self.kind.__name__} miss {missing} and have unexpected {extra}")
        return self
