import importlib.util
from pathlib import Path
from types import ModuleType

from aerona.domain.enums.modifier import ModifierSource
from aerona.engine.interconnect import edges
from aerona.engine.interconnect.catalog import REGISTERED
from aerona.engine.interconnect.edges import edge_counts, flow_carriers, flow_count, linked, mechanic_reads, mechanic_writes, structural_edges
from aerona.engine.interconnect.registry import EdgeKind
from aerona.engine.interconnect.sources import REASONS, SOURCE_SUBSYSTEMS

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "interconnection_docs.py"


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("interconnection_docs", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_edge_has_a_writer_and_a_reader() -> None:
    readers_by_subsystem = {mechanic.subsystem for mechanic in REGISTERED.values() if mechanic_reads(mechanic)}
    problems: list[str] = []
    for edge in structural_edges():
        if edge.writer not in REGISTERED and edge.writer not in ("modifier_upkeep", "rules"):
            problems.append(f"{edge}: unknown writer")
        if edge.reader is None and edge.target not in readers_by_subsystem:
            problems.append(f"{edge}: nothing in {edge.target} reads anything")
    for carrier, (writers, readers) in flow_carriers().items():
        problems.extend(f"{carrier}: {writer.key} carries it but does not write it" for writer in writers if carrier not in mechanic_writes(writer))
        problems.extend(f"{carrier}: {reader.key} takes it but does not read it" for reader in readers if carrier not in mechanic_reads(reader))
    assert problems == []


def test_every_mechanic_carries_at_least_one_edge() -> None:
    assert [key for key in REGISTERED if not linked(key)] == []


def test_every_modifier_source_has_an_edge_and_every_reason_reads_well() -> None:
    assert set(SOURCE_SUBSYSTEMS) == set(ModifierSource)
    assert all(text and not text.endswith(".") for text in REASONS.values())


def test_the_published_interconnection_registry_is_current() -> None:
    docs = load()
    assert docs.OUTPUT.read_text(encoding="utf-8") == docs.render(), "run scripts/interconnection_docs.py write"


def test_the_registry_counts_flows_without_building_every_flow_edge() -> None:
    source = Path(edges.__file__).read_text(encoding="utf-8")
    assert "EdgeKind.FLOW" not in source.split("def flow_count")[0]
    declared = sum(1 for edge in structural_edges() if edge.kind is EdgeKind.FLOW)
    assert edge_counts()[EdgeKind.FLOW] == declared + flow_count()
