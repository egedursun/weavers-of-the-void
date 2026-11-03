from collections import defaultdict
from functools import cache

from aerona.domain.enums.modifier import ModifierSource
from aerona.engine.interconnect.annotations import declared_reads, declared_writes
from aerona.engine.interconnect.catalog import REGISTERED
from aerona.engine.interconnect.registry import Edge, EdgeKind, Mechanic, Subsystem
from aerona.engine.interconnect.sources import CONDITION_EFFECTS, SOURCE_SUBSYSTEMS
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
        "table.epoch_year_cursors",
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


def mechanic_reads(mechanic: Mechanic) -> frozenset[str]:
    table = phase_table()
    return frozenset(key for name in mechanic.phases if name in table for key in declared_reads(table[name].run) if key not in INFRASTRUCTURE)


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


def flow_edges() -> list[Edge]:
    readers: dict[str, list[Mechanic]] = defaultdict(list)
    for mechanic in REGISTERED.values():
        for key in mechanic_reads(mechanic):
            readers[key].append(mechanic)
    edges: list[Edge] = []
    for writer in REGISTERED.values():
        for key in sorted(mechanic_writes(writer)):
            for reader in readers.get(key, []):
                if reader.key != writer.key:
                    edges.append(Edge(writer.subsystem, reader.subsystem, key, None, EdgeKind.FLOW, writer.key, reader.key))
    return edges


def modifier_edges() -> list[Edge]:
    targets: dict[ModifierSource, set[str]] = {ModifierSource.WONDER: set(WONDER_KEYS)}
    targets[ModifierSource.CONDITION] = {effect.key for effects in CONDITION_EFFECTS.values() for effect in effects}
    edges: list[Edge] = []
    for source, keys in targets.items():
        for mechanic in REGISTERED.values():
            read = {bare(key) for key in mechanic_reads(mechanic)}
            for key in sorted(keys & read):
                edges.append(
                    Edge(SOURCE_SUBSYSTEMS[source], mechanic.subsystem, key, f"modifiers.{source.value}", EdgeKind.MODIFIER, "modifier_upkeep", mechanic.key)
                )
    return edges


def rule_switch_edges() -> list[Edge]:
    return [
        Edge(Subsystem.CORE, mechanic.subsystem, phase, f"engine_phases.{phase}", EdgeKind.RULE_SWITCH, "rules", mechanic.key)
        for mechanic in REGISTERED.values()
        for phase in mechanic.phases
        if phase in phase_table()
    ]


@cache
def cached_edges() -> tuple[Edge, ...]:
    return (*declared_edges(), *flow_edges(), *modifier_edges(), *rule_switch_edges())


def all_edges() -> list[Edge]:
    return list(cached_edges())


def edges_of(mechanic_key: str) -> list[Edge]:
    return [edge for edge in all_edges() if mechanic_key in (edge.writer, edge.reader)]


def matrix() -> dict[tuple[Subsystem, Subsystem], set[str]]:
    cells: dict[tuple[Subsystem, Subsystem], set[str]] = defaultdict(set)
    for edge in all_edges():
        if edge.kind is not EdgeKind.RULE_SWITCH and edge.source is not edge.target:
            cells[(edge.source, edge.target)].add(edge.carrier)
    return cells
