import asyncio
import json
import sys
import time
from pathlib import Path

from aerona.db.session import Database
from aerona.engine.pipeline import simulate

READY = "ready"


async def live(path: Path, epochs: int) -> None:
    database = Database(f"sqlite+aiosqlite:///{path}")
    try:
        for number in range(1, epochs + 1):
            started = time.perf_counter()
            await simulate(database, 1)
            sys.stdout.write(json.dumps({"epoch": number, "seconds": round(time.perf_counter() - started, 3)}) + "\n")
            sys.stdout.flush()
    finally:
        await database.dispose()


def main() -> int:
    sys.stdout.write(json.dumps({READY: True}) + "\n")
    sys.stdout.flush()
    order = sys.stdin.readline().strip()
    if not order:
        return 0
    wanted = json.loads(order)
    asyncio.run(live(Path(wanted["path"]), int(wanted["epochs"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
