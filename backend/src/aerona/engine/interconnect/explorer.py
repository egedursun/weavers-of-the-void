from collections import defaultdict
from dataclasses import dataclass
from functools import cache

from aerona.engine.interconnect.edges import GENERIC_CARRIERS, cached_edges
from aerona.engine.interconnect.registry import EdgeKind, Subsystem


@dataclass(frozen=True)
class Link:
    source: Subsystem
    target: Subsystem
    kinds: tuple[EdgeKind, ...]
    edges: int
    carriers: tuple[str, ...]
    writers: tuple[str, ...]
    readers: tuple[str, ...]


@dataclass(frozen=True)
class MechanicLink:
    mechanic: str
    direction: str
    other: str
    other_subsystem: Subsystem | None
    kind: EdgeKind
    carriers: tuple[str, ...]


@dataclass
class _Cell:
    kinds: set[EdgeKind]
    carriers: set[str]
    writers: set[str]
    readers: set[str]
    edges: int = 0


@cache
def subsystem_links() -> tuple[Link, ...]:
    cells: dict[tuple[Subsystem, Subsystem], _Cell] = defaultdict(lambda: _Cell(set(), set(), set(), set()))
    for edge in cached_edges():
        if edge.kind is EdgeKind.RULE_SWITCH:
            continue
        cell = cells[(edge.source, edge.target)]
        cell.kinds.add(edge.kind)
        cell.carriers.add(edge.carrier)
        cell.writers.add(edge.writer)
        if edge.reader is not None:
            cell.readers.add(edge.reader)
        cell.edges += 1
    return tuple(
        Link(source, target, tuple(sorted(cell.kinds)), cell.edges, tuple(sorted(cell.carriers)), tuple(sorted(cell.writers)), tuple(sorted(cell.readers)))
        for (source, target), cell in sorted(cells.items())
    )


@cache
def mechanic_links() -> dict[str, tuple[MechanicLink, ...]]:
    grouped: dict[tuple[str, str, str, Subsystem | None, EdgeKind], set[str]] = defaultdict(set)
    for edge in cached_edges():
        if edge.kind is EdgeKind.RULE_SWITCH:
            continue
        grouped[(edge.writer, "out", edge.reader or "", edge.target, edge.kind)].add(edge.carrier)
        if edge.reader is not None:
            grouped[(edge.reader, "in", edge.writer, edge.source, edge.kind)].add(edge.carrier)
    found: dict[str, list[MechanicLink]] = defaultdict(list)
    for (mechanic, direction, other, subsystem, kind), carriers in sorted(grouped.items(), key=lambda item: (item[0][0], item[0][1], item[0][2], item[0][4])):
        found[mechanic].append(MechanicLink(mechanic, direction, other, subsystem, kind, tuple(sorted(carriers))))
    return {key: tuple(items) for key, items in found.items()}


@cache
def affects_by_writer() -> dict[str, frozenset[Subsystem]]:
    found: dict[str, set[Subsystem]] = defaultdict(set)
    for edge in cached_edges():
        if edge.carrier not in GENERIC_CARRIERS:
            found[edge.writer].add(edge.target)
    return {key: frozenset(value) for key, value in found.items()}
