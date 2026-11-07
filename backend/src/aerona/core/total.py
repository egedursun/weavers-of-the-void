from collections.abc import Collection, Mapping
from enum import Enum
from types import MappingProxyType

DECLARED_PARTIAL: set[int] = set()


class IncompleteTableError(LookupError):
    pass


def total[K: Enum, V](kind: type[K], table: Mapping[K, V]) -> MappingProxyType[K, V]:
    return partial(kind, table, without=())


def partial[K: Enum, V](kind: type[K], table: Mapping[K, V], *, without: Collection[K]) -> MappingProxyType[K, V]:
    expected = {member for member in kind if member not in without}
    if set(table) != expected:
        missing = sorted(member.value for member in expected - set(table))
        extra = sorted(member.value for member in set(table) - expected)
        raise IncompleteTableError(f"a table over {kind.__name__} misses {missing} and has unexpected {extra}")
    found = MappingProxyType(dict(table))
    if without:
        DECLARED_PARTIAL.add(id(found))
    return found
