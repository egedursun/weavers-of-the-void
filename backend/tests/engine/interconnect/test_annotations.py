from pathlib import Path

from aerona.db.base import Base
from aerona.db.session import Database
from aerona.engine.interconnect.annotations import declared_reads, declared_writes
from aerona.engine.interconnect.guards import READ_MODE, recording
from aerona.engine.interconnect.table_io import install_table_recorder
from aerona.engine.pipeline import all_phases, simulate
from tests.engine.integration.factories import seed_rich_cosmos


async def test_every_step_declares_what_it_reads_and_writes(tmp_path: Path) -> None:
    install_table_recorder()
    database = Database(f"sqlite+aiosqlite:///{tmp_path}/io.db")
    recorder: dict[str, set[tuple[str, str]]] = {}
    try:
        async with database.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with database.write() as session:
            await seed_rich_cosmos(session)
        with recording(recorder):
            await simulate(database, 1)
    finally:
        await database.dispose()
    phases = {phase.name: phase for phase in all_phases()}
    undeclared = sorted(
        f"{name}: {mode} {key}"
        for name, items in recorder.items()
        for mode, key in items
        if key not in (declared_reads(phases[name].run) if mode == READ_MODE else declared_writes(phases[name].run))
    )
    assert undeclared == [], "run scripts/phase_io.py to refresh the annotations"
    assert [name for name, phase in phases.items() if not declared_reads(phase.run) and not declared_writes(phase.run)] == []
