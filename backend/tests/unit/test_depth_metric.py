import importlib.util
from pathlib import Path
from types import ModuleType

from aerona.engine.interconnect.registry import Edge, EdgeKind, Subsystem

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "depth_metric.py"


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("depth_metric", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_depth_metric_measures_every_node_type_against_its_target() -> None:
    metric = load()
    rows = metric.measure()
    names = {row.name for row in rows}
    assert {entity_type.value for entity_type in metric.EntityType} <= names
    assert {"son", "creator", "foreign_god", "war", "world", "star", "route"} <= names
    assert all(row.a >= 0 and row.b >= 0 and row.c >= 0 for row in rows)
    assert "| mortal |" in metric.render(rows)


def test_targets_take_the_latest_revision_and_increments() -> None:
    targets = load().spec_targets()
    assert targets["mortal"] == (330 + 25, 340, 200)
    assert targets["region"] == (200 + 15, 160, 120)
    assert targets["world"] == (180 + 15, 135, 115)
    assert targets["route"] == (45, 30, 25)
    assert targets["foreign_god"] == (200, 140, 100)
    assert targets["event"] == (15, 20, 15)


def test_couplings_count_distinct_cross_subsystem_pairs() -> None:
    metric = load()
    edges = [
        Edge(Subsystem.ENVIRONMENT, Subsystem.WAR, "region.danger", None, EdgeKind.FLOW, "a", "b"),
        Edge(Subsystem.ENVIRONMENT, Subsystem.WAR, "region.terrain", None, EdgeKind.FLOW, "a", "c"),
        Edge(Subsystem.ENVIRONMENT, Subsystem.ENVIRONMENT, "region.soil", None, EdgeKind.FLOW, "a", "d"),
        Edge(Subsystem.ENVIRONMENT, Subsystem.ECONOMY, "region.soil", None, EdgeKind.FLOW, "a", "e"),
    ]
    assert metric.subsystem_pairs(edges) == {("environment", "war"), ("environment", "economy")}
    pairs = len(Subsystem) * (len(Subsystem) - 1)
    assert all(row.c <= pairs for row in metric.measure())


def test_node_table_attributes_count_only_columns_the_engine_reads() -> None:
    metric = load()
    for name in metric.NODE_TABLES:
        assert metric.read_columns(name) <= metric.typed_fields(name)
    son = metric.read_columns("son")
    assert "existence" in son
    assert len(son) < len(metric.typed_fields("son"))


def test_the_published_depth_metric_is_current() -> None:
    metric = load()
    assert metric.OUTPUT.read_text(encoding="utf-8") == metric.render(metric.measure()), "run scripts/depth_metric.py write"


def test_the_rows_a_type_owns_are_real_tables_and_count_only_columns_the_engine_reads() -> None:
    metric = load()
    known = set(metric.Base.metadata.tables)
    assert all(set(tables) <= known for tables in metric.TYPE_TABLES.values())
    assert {"sons", "son_powers"} <= metric.owned_tables("son")
    assert "worlds" in metric.owned_tables("world")
    for name in metric.TYPE_TABLES:
        assert all(column.split(".", 1)[0] in metric.owned_tables(name) for column in metric.owned_columns(name))
