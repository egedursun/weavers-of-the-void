import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_depth_expansion_coverage_matrix_is_complete_and_consistent() -> None:
    script = REPOSITORY_ROOT / "scripts" / "spec_coverage.py"
    completed = subprocess.run([sys.executable, str(script), "check"], capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stdout


def test_the_minds_spec_has_a_row_for_every_kind_of_item() -> None:
    script = REPOSITORY_ROOT / "scripts" / "spec_coverage.py"
    spec = (REPOSITORY_ROOT / "docs" / "spec" / "16-minds-powers-living-craft.md").read_text(encoding="utf-8")
    matrix = (REPOSITORY_ROOT / "docs" / "spec" / "16-coverage.md").read_text(encoding="utf-8")
    assert script.exists() and "F50" in spec
    for key in ("F50", "F50.1", "S44.1", "S44.10a", "C10", "L79", "AS31", "R43", "K.21"):
        assert f"| {key} |" in matrix, key


def coverage_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("spec_coverage", REPOSITORY_ROOT / "scripts" / "spec_coverage.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["spec_coverage"] = module
    spec.loader.exec_module(module)
    return module


def test_a_done_row_that_names_a_lever_missing_from_the_action_catalogue_is_a_problem() -> None:
    spec_coverage = coverage_script()
    levers = spec_coverage.lever_ids()
    assert {"record_row:edit", "authored_kind:edit", "war:declare"} <= levers
    row = spec_coverage.Row({"Lever": "war:declare, duel:edit (the duel editor)", "Test": "", "Module": ""})
    assert spec_coverage.reference_problems("S0", row, set(), levers) == ["row S0 names a lever that is not in the action catalogue: duel:edit"]
