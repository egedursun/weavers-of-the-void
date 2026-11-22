import atexit
import multiprocessing
import os
import threading
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ProcessPoolExecutor

from aerona.rules.registry import Rules

POOLS: dict[int, ProcessPoolExecutor] = {}
PARENT_POLL_SECONDS = 2.0


def exit_with_parent(parent: int) -> None:
    def watch() -> None:
        while os.getppid() == parent:
            time.sleep(PARENT_POLL_SECONDS)
        os._exit(0)

    threading.Thread(target=watch, daemon=True).start()


def workers_for(rules: Rules) -> int:
    wanted = rules.engine_budget.workers
    return wanted if wanted > 0 else max(1, (os.cpu_count() or 2) - 1)


def pool_of(workers: int) -> ProcessPoolExecutor:
    found = POOLS.get(workers)
    if found is None:
        found = POOLS[workers] = ProcessPoolExecutor(
            max_workers=workers, mp_context=multiprocessing.get_context("spawn"), initializer=exit_with_parent, initargs=(os.getpid(),)
        )
    return found


def close_pools() -> None:
    for pool in POOLS.values():
        pool.shutdown(wait=True, cancel_futures=True)
    POOLS.clear()


atexit.register(close_pools)


def compute_shards[Item, Result](kernel: Callable[[Item], Result], shards: Sequence[Item], workers: int) -> list[Result]:
    if workers <= 1 or len(shards) <= 1:
        return [kernel(shard) for shard in shards]
    return list(pool_of(workers).map(kernel, shards))
