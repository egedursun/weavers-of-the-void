from collections.abc import Callable
from typing import Any, TypeVar

READS_ATTRIBUTE = "__aerona_reads__"
WRITES_ATTRIBUTE = "__aerona_writes__"
F = TypeVar("F", bound=Callable[..., Any])


def _mark(attribute: str, keys: tuple[str, ...]) -> Callable[[F], F]:
    def apply(function: F) -> F:
        setattr(function, attribute, frozenset(getattr(function, attribute, frozenset())) | frozenset(keys))
        return function

    return apply


def reads(*keys: str) -> Callable[[F], F]:
    return _mark(READS_ATTRIBUTE, keys)


def writes(*keys: str) -> Callable[[F], F]:
    return _mark(WRITES_ATTRIBUTE, keys)


def declared_reads(function: object) -> frozenset[str]:
    found: frozenset[str] = getattr(function, READS_ATTRIBUTE, frozenset())
    return found


def declared_writes(function: object) -> frozenset[str]:
    found: frozenset[str] = getattr(function, WRITES_ATTRIBUTE, frozenset())
    return found
