import subprocess
import sys
from pathlib import Path

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
