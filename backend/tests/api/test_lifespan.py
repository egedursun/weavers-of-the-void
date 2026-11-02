import os
from pathlib import Path

import pytest

from aerona.api.lifespan import InstanceLock
from aerona.constants.api import LOCK_FILENAME
from aerona.core.errors import ConflictError

DEAD_PID = 999_999_999


def test_lock_refuses_a_living_owner_and_takes_over_a_stale_one(tmp_path: Path) -> None:
    (tmp_path / LOCK_FILENAME).write_text(str(os.getppid()), encoding="utf-8")
    with pytest.raises(ConflictError):
        InstanceLock(tmp_path).acquire()
    (tmp_path / LOCK_FILENAME).write_text(str(DEAD_PID), encoding="utf-8")
    lock = InstanceLock(tmp_path)
    lock.acquire()
    assert (tmp_path / LOCK_FILENAME).read_text(encoding="utf-8") == str(os.getpid())
    lock.release()
    assert not (tmp_path / LOCK_FILENAME).exists()
