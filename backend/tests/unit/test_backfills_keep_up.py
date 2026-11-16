import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "check_backfills.py"


def test_every_backfill_step_also_runs_for_what_arrives_later() -> None:
    spec = importlib.util.spec_from_file_location("check_backfills", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.lagging_steps() == []
