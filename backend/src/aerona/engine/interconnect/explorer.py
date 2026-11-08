from collections import defaultdict
from dataclasses import dataclass
from functools import cache

from aerona.engine.interconnect.catalog import REGISTERED
from aerona.engine.interconnect.edges import GENERIC_CARRIERS, declared_edges, mechanic_reads, mechanic_writes, modifier_edges, rule_switch_edges
from aerona.engine.interconnect.registry import Edge, EdgeKind, Mechanic, Subsystem


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


@dataclass(frozen=True)
class FlowIndex:
    writers: dict[str, tuple[Mechanic, ...]]
    readers: dict[str, tuple[Mechanic, ...]]


@cache
def flow_index() -> FlowIndex:
    writers: dict[str, list[Mechanic]] = defaultdict(list)
    readers: dict[str, list[Mechanic]] = defaultdict(list)
    for mechanic in REGISTERED.values():
        for key in mechanic_writes(mechanic):
            writers[key].append(mechanic)
        for key in mechanic_reads(mechanic):
            readers[key].append(mechanic)
    return FlowIndex({key: tuple(items) for key, items in writers.items()}, {key: tuple(items) for key, items in readers.items()})


@cache
def other_edges() -> tuple[Edge, ...]:
    return (*declared_edges(), *modifier_edges(), *rule_switch_edges())


def by_subsystem(mechanics: tuple[Mechanic, ...]) -> dict[Subsystem, set[str]]:
    found: dict[Subsystem, set[str]] = defaultdict(set)
    for mechanic in mechanics:
        found[mechanic.subsystem].add(mechanic.key)
    return found


@cache
def subsystem_links() -> tuple[Link, ...]:
    cells: dict[tuple[Subsystem, Subsystem], _Cell] = defaultdict(lambda: _Cell(set(), set(), set(), set()))
    for edge in other_edges():
        if edge.kind is EdgeKind.RULE_SWITCH:
            continue
        cell = cells[(edge.source, edge.target)]
        cell.kinds.add(edge.kind)
        cell.carriers.add(edge.carrier)
        cell.writers.add(edge.writer)
        if edge.reader is not None:
            cell.readers.add(edge.reader)
        cell.edges += 1
    index = flow_index()
    for key, writers in index.writers.items():
        readers = index.readers.get(key, ())
        if not readers:
            continue
        reading = by_subsystem(readers)
        for source, written in by_subsystem(writers).items():
            for target, read in reading.items():
                pairs = len(written) * len(read) - len(written & read)
                if pairs <= 0:
                    continue
                cell = cells[(source, target)]
                cell.kinds.add(EdgeKind.FLOW)
                cell.carriers.add(key)
                cell.writers.update(writer for writer in written if read - {writer})
                cell.readers.update(reader for reader in read if written - {reader})
                cell.edges += pairs
    return tuple(
        Link(source, target, tuple(sorted(cell.kinds)), cell.edges, tuple(sorted(cell.carriers)), tuple(sorted(cell.writers)), tuple(sorted(cell.readers)))
        for (source, target), cell in sorted(cells.items())
    )


@cache
def links_of(key: str) -> tuple[MechanicLink, ...]:
    grouped: dict[tuple[str, str, Subsystem | None, EdgeKind], set[str]] = defaultdict(set)
    for edge in other_edges():
        if edge.kind is EdgeKind.RULE_SWITCH or edge.carrier in GENERIC_CARRIERS:
            continue
        if edge.writer == key:
            grouped[("out", edge.reader or "", edge.target, edge.kind)].add(edge.carrier)
        if edge.reader == key:
            grouped[("in", edge.writer, edge.source, edge.kind)].add(edge.carrier)
    mechanic = REGISTERED.get(key)
    if mechanic is not None:
        index = flow_index()
        for carrier in mechanic_writes(mechanic) - GENERIC_CARRIERS:
            for reader in index.readers.get(carrier, ()):
                if reader.key != key:
                    grouped[("out", reader.key, reader.subsystem, EdgeKind.FLOW)].add(carrier)
        for carrier in mechanic_reads(mechanic) - GENERIC_CARRIERS:
            for writer in index.writers.get(carrier, ()):
                if writer.key != key:
                    grouped[("in", writer.key, writer.subsystem, EdgeKind.FLOW)].add(carrier)
    return tuple(
        MechanicLink(key, direction, other, subsystem, kind, tuple(sorted(carriers)))
        for (direction, other, subsystem, kind), carriers in sorted(grouped.items(), key=lambda item: (item[0][0], item[0][1], item[0][3]))
    )


@cache
def affects_by_writer() -> dict[str, frozenset[Subsystem]]:
    found: dict[str, set[Subsystem]] = defaultdict(set)
    for edge in other_edges():
        if edge.carrier not in GENERIC_CARRIERS:
            found[edge.writer].add(edge.target)
    index = flow_index()
    reach: dict[str, dict[Subsystem, set[str]]] = {key: by_subsystem(readers) for key, readers in index.readers.items()}
    for mechanic in REGISTERED.values():
        for carrier in mechanic_writes(mechanic) - GENERIC_CARRIERS:
            for target, readers in reach.get(carrier, {}).items():
                if readers - {mechanic.key}:
                    found[mechanic.key].add(target)
    return {key: frozenset(value) for key, value in found.items()}
