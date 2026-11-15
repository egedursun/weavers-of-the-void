import asyncio
import json
import sys
import tempfile
from pathlib import Path

from sqlalchemy import event

from aerona.db.migrations import upgrade_to_head_sync
from aerona.db.session import Database
from aerona.engine.pipeline import TICK_ORDER, current_environment, run_phases
from aerona.rules.registry import Rules
from tests.engine.integration.factories import seed_rich_cosmos

ROOT = Path(__file__).resolve().parent.parent
BUDGET = ROOT / "docs" / "work" / "engine-budget.json"


async def measured() -> tuple[int, float]:
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "budget.db"
        upgrade_to_head_sync(f"sqlite:///{path}")
        database = Database(f"sqlite+aiosqlite:///{path}")
        async with database.write() as session:
            await seed_rich_cosmos(session)
        statements = 0

        def counted(*_: object) -> None:
            nonlocal statements
            statements += 1

        event.listen(database.engine.sync_engine, "before_cursor_execute", counted)
        environment = await current_environment(database, rules=Rules())
        await run_phases(environment, database, TICK_ORDER)
        await database.dispose()
        return statements, round(sum(environment.stats.phase_cpu.values()), 2)


def main() -> int:
    statements, cpu = asyncio.run(measured())
    print(f"a tick of the reference world ran {statements} statements in {cpu} cpu seconds")
    if sys.argv[1:] == ["write"]:
        BUDGET.write_text(json.dumps({"tick_statements": statements, "tick_cpu_seconds": cpu}, indent=1) + "\n", encoding="utf-8")
        print(f"written to {BUDGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
