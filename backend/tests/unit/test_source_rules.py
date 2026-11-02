import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_repository_follows_source_rules() -> None:
    script = REPOSITORY_ROOT / "scripts" / "check_source_rules.py"
    completed = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stdout
