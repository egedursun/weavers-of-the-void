import subprocess
import sys

PROBE = """
from sqlalchemy.orm import Session
from aerona.db.session import Database
Database("sqlite+aiosqlite://")
session = Session()
before = [getattr(hook, "__name__", "") for hook in session.dispatch.before_flush]
after = [getattr(hook, "__name__", "") for hook in session.dispatch.after_flush]
assert "hold_profile_columns" in before, "the profile guard is not installed"
assert "align_updates" in before, "flush batching is not installed"
assert before.index("hold_profile_columns") < before.index("align_updates"), "held columns must be restored before updates are aligned"
assert "capture_activity" in after, "activity capture is not installed"
"""


def test_a_database_alone_installs_every_flush_hook_in_order() -> None:
    done = subprocess.run([sys.executable, "-c", PROBE], capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr[-600:]
