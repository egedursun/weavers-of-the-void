import importlib.util
from pathlib import Path
from types import ModuleType

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
    mortal = next(row for row in rows if row.name == "mortal")
    assert mortal.targets == (75, 140, 80)
    assert "| mortal |" in metric.render(rows)


def test_the_published_depth_metric_is_current() -> None:
    metric = load()
    assert metric.OUTPUT.read_text(encoding="utf-8") == metric.render(metric.measure()), "run scripts/depth_metric.py write"
