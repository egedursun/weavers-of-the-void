import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_every_countable_thing_has_a_row_and_every_named_guard_exists() -> None:
    script = REPOSITORY_ROOT / "scripts" / "check_inventory.py"
    completed = subprocess.run([sys.executable, str(script), "check"], capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stdout
