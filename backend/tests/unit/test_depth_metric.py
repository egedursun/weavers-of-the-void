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


def test_depth_metric_measures_every_entity_type() -> None:
    metric = load()
    rows = metric.measure()
    assert len(rows) == len(metric.EntityType)
    assert all(a >= 0 and b >= 0 and c >= 0 for _, a, b, c in rows)
    assert "| mortal |" in metric.render(rows)
