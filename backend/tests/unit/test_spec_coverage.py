import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_depth_expansion_coverage_matrix_is_complete_and_consistent() -> None:
    script = REPOSITORY_ROOT / "scripts" / "spec_coverage.py"
    completed = subprocess.run([sys.executable, str(script), "check"], capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stdout
