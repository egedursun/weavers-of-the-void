import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_every_subcategory_discipline_and_motif_range_is_closed_by_a_done_section() -> None:
    script = REPOSITORY_ROOT / "scripts" / "check_ocm_coverage.py"
    completed = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stdout
