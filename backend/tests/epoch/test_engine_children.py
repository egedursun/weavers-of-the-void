import os
import time
from concurrent.futures import ProcessPoolExecutor
from functools import partial

from aerona.db.session import shared_gate
from aerona.engine.parallel.pool import PARENT_POLL_SECONDS, lives
from aerona.epoch.engine_process import child_start, engine_context, warm_engine_processes


def test_an_engine_child_forked_from_the_preloaded_server_outlives_its_watch() -> None:
    warm_engine_processes()
    context = engine_context()
    assert context.get_start_method() == "forkserver"
    with ProcessPoolExecutor(max_workers=1, mp_context=context, initializer=child_start, initargs=(os.getpid(), shared_gate(), context.Queue())) as pool:
        pool.submit(partial(time.sleep, PARENT_POLL_SECONDS * 2)).result()
        assert pool.submit(os.getpid).result() != os.getpid()


def test_a_process_lives_until_it_is_gone() -> None:
    assert lives(os.getpid())
    assert not lives(2**22 + 12345)
