from collections import defaultdict
from functools import cache

from aerona.domain.enums.modifier import ModifierSource
from aerona.engine.interconnect.annotations import declared_reads, declared_writes
from aerona.engine.interconnect.catalog import REGISTERED
from aerona.engine.interconnect.registry import Edge, EdgeKind, Mechanic, Subsystem
from aerona.engine.interconnect.sources import CONDITION_EFFECTS, SOURCE_KEYS, SOURCE_SUBSYSTEMS, SOURCE_WRITERS
from aerona.engine.phase import Phase
from aerona.engine.pipeline import all_phases

WONDER_KEYS = ("prosperity", "piety")
GENERIC_CARRIERS = frozenset({"table.entities", "table.bonds", "table.entity_flags", "table.entity_traits"})
INFRASTRUCTURE = frozenset(
    {
        "table.chronicle",
        "table.chronicle_entities",
        "table.incidents",
        "table.incident_participants",
        "table.nodes",
        "table.name_registry",
        "table.applied_fixups",
        "table.notifications",
        "table.entity_tags",
        "table.epoch_stats",
        "table.modifiers",
    }
)


@cache
def phase_table() -> dict[str, Phase]:
    return {phase.name: phase for phase in all_phases()}


@cache
def mechanic_reads(mechanic: Mechanic) -> frozenset[str]:
    table = phase_table()
    return frozenset(key for name in mechanic.phases if name in table for key in declared_reads(table[name].run) if key not in INFRASTRUCTURE)


@cache
def mechanic_writes(mechanic: Mechanic) -> frozenset[str]:
    table = phase_table()
    return frozenset(key for name in mechanic.phases if name in table for key in declared_writes(table[name].run) if key not in INFRASTRUCTURE)


def bare(key: str) -> str:
    return key.split(".", 1)[-1]


def declared_edges() -> list[Edge]:
    return [
        Edge(mechanic.subsystem, coupling.target, coupling.carrier, coupling.rule_key, coupling.kind, mechanic.key)
        for mechanic in REGISTERED.values()
        for coupling in mechanic.couplings
    ]


@cache
def flow_carriers() -> dict[str, tuple[tuple[Mechanic, ...], tuple[Mechanic, ...]]]:
    writers: dict[str, list[Mechanic]] = defaultdict(list)
    readers: dict[str, list[Mechanic]] = defaultdict(list)
    for mechanic in REGISTERED.values():
        for key in mechanic_writes(mechanic):
            writers[key].append(mechanic)
        for key in mechanic_reads(mechanic):
            readers[key].append(mechanic)
    return {key: (tuple(writers[key]), tuple(readers[key])) for key in sorted(writers) if key in readers}


def flow_count() -> int:
    return sum(
        len(writers) * len(readers) - len({item.key for item in writers} & {item.key for item in readers}) for writers, readers in flow_carriers().values()
    )


@cache
def flow_pairs(carrier: str) -> frozenset[tuple[str, Subsystem, Subsystem]]:
    writers, readers = flow_carriers().get(carrier, ((), ()))
    return frozenset((writer.key, writer.subsystem, reader.subsystem) for writer in writers for reader in readers if reader.key != writer.key)


@cache
def carrier_sides(carrier: str) -> tuple[frozenset[str], frozenset[str], frozenset[Subsystem], frozenset[Subsystem]]:
    writers, readers = flow_carriers().get(carrier, ((), ()))
    return (
        frozenset(item.key for item in writers),
        frozenset(item.key for item in readers),
        frozenset(item.subsystem for item in writers),
        frozenset(item.subsystem for item in readers),
    )


def flow_reach(mechanic: Mechanic) -> set[Subsystem]:
    reach: set[Subsystem] = set()
    for key in mechanic_writes(mechanic):
        _writers, readers, _sources, targets = carrier_sides(key)
        if readers - {mechanic.key}:
            reach |= targets
    for key in mechanic_reads(mechanic):
        writers, _readers, sources, _targets = carrier_sides(key)
        if writers - {mechanic.key}:
            reach |= sources
    return reach


def flows_through(mechanic: Mechanic) -> bool:
    shared = [carrier_sides(key)[1] for key in mechanic_writes(mechanic)] + [carrier_sides(key)[0] for key in mechanic_reads(mechanic)]
    return any(others - {mechanic.key} for others in shared)


def modifier_targets() -> dict[ModifierSource, set[str]]:
    targets: dict[ModifierSource, set[str]] = {ModifierSource.WONDER: set(WONDER_KEYS)}
    targets[ModifierSource.CONDITION] = {effect.key for effects in CONDITION_EFFECTS.values() for effect in effects}
    for source, keys in SOURCE_KEYS.items():
        targets[source] = set(keys)
    return targets


def modifier_edges() -> list[Edge]:
    edges: list[Edge] = []
    for source, keys in modifier_targets().items():
        writer = SOURCE_WRITERS.get(source, "modifier_upkeep")
        for mechanic in REGISTERED.values():
            read = {bare(key) for key in mechanic_reads(mechanic)}
            for key in sorted(keys & read):
                edges.append(Edge(SOURCE_SUBSYSTEMS[source], mechanic.subsystem, key, f"modifiers.{source.value}", EdgeKind.MODIFIER, writer, mechanic.key))
    return edges


def rule_switch_edges() -> list[Edge]:
    return [
        Edge(Subsystem.CORE, mechanic.subsystem, phase, f"engine_phases.{phase}", EdgeKind.RULE_SWITCH, "rules", mechanic.key)
        for mechanic in REGISTERED.values()
        for phase in mechanic.phases
        if phase in phase_table()
    ]


@cache
def structural_edges() -> tuple[Edge, ...]:
    return (*declared_edges(), *modifier_edges(), *rule_switch_edges())


def edge_counts() -> dict[EdgeKind, int]:
    counts = {kind: sum(1 for edge in structural_edges() if edge.kind is kind) for kind in EdgeKind}
    counts[EdgeKind.FLOW] += flow_count()
    return counts


@cache
def edges_by_mechanic() -> dict[str, tuple[Edge, ...]]:
    found: dict[str, list[Edge]] = defaultdict(list)
    for edge in structural_edges():
        found[edge.writer].append(edge)
        if edge.reader is not None and edge.reader != edge.writer:
            found[edge.reader].append(edge)
    return {key: tuple(edges) for key, edges in found.items()}


def linked(mechanic_key: str) -> bool:
    return bool(edges_by_mechanic().get(mechanic_key)) or (mechanic_key in REGISTERED and flows_through(REGISTERED[mechanic_key]))


@cache
def matrix() -> dict[tuple[Subsystem, Subsystem], frozenset[str]]:
    cells: dict[tuple[Subsystem, Subsystem], set[str]] = defaultdict(set)
    for edge in structural_edges():
        if edge.kind is not EdgeKind.RULE_SWITCH and edge.source is not edge.target:
            cells[(edge.source, edge.target)].add(edge.carrier)
    for carrier in flow_carriers():
        for _writer, source, target in flow_pairs(carrier):
            if source is not target:
                cells[(source, target)].add(carrier)
    return {pair: frozenset(carriers) for pair, carriers in cells.items()}
