import os
import subprocess
import sys
import time
from pathlib import Path

from aerona.engine.parallel.pool import PARENT_POLL_SECONDS

PARENT = """
import os
import sys
from aerona.engine.parallel.pool import pool_of


def pid(_index: int) -> int:
    return os.getpid()


if __name__ == "__main__":
    print(*sorted(set(pool_of(2).map(pid, range(8)))), flush=True)
    os._exit(0)
"""


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def test_a_pool_worker_leaves_when_the_process_that_made_it_dies(tmp_path: Path) -> None:
    script = tmp_path / "parent.py"
    script.write_text(PARENT, encoding="utf-8")
    done = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=120, check=True, env=os.environ)
    workers = [int(item) for item in done.stdout.split()]
    assert workers
    deadline = time.monotonic() + PARENT_POLL_SECONDS * 10
    while any(alive(pid) for pid in workers) and time.monotonic() < deadline:
        time.sleep(0.2)
    assert not [pid for pid in workers if alive(pid)]
