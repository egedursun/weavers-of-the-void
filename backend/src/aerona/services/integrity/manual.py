import asyncio
from dataclasses import dataclass
from enum import StrEnum

from aerona.core.grammar import several
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.session import Database
from aerona.engine.primitives.records import sweep_dead_bonds
from aerona.services.application import database_path
from aerona.services.integrity.data_repairs import checkpoint
from aerona.services.integrity.invariants import sweep


class IntegrityTask(StrEnum):
    DEAD_BONDS = "dead_bonds"
    SCHEMA_CHECKS = "schema_checks"
    CHECKPOINT = "checkpoint"


@dataclass(frozen=True)
class TaskInfo:
    task: IntegrityTask
    title: str
    description: str
    changes_world: bool


TASKS: tuple[TaskInfo, ...] = (
    TaskInfo(IntegrityTask.DEAD_BONDS, "Dead-bond sweep", "Close the living bonds of the dead and destroyed, passing inheritable ones to heirs.", True),
    TaskInfo(
        IntegrityTask.SCHEMA_CHECKS,
        "Check every table",
        "Clamp numbers into range, set past epochs back to the present, drop ids of lost nodes and mend rules across rows; what needs your word is listed.",
        True,
    ),
    TaskInfo(IntegrityTask.CHECKPOINT, "Checkpoint the log", "Fold the write-ahead log into the main database file.", False),
)


@dataclass(frozen=True)
class IntegrityOutcome:
    task: IntegrityTask
    counters: dict[str, int]
    message: str


async def run_task(database: Database, task: IntegrityTask) -> IntegrityOutcome:
    if task is IntegrityTask.CHECKPOINT:
        await asyncio.to_thread(checkpoint, database_path(database))
        return IntegrityOutcome(task, {}, "The write-ahead log was folded into the database file.")
    if task is IntegrityTask.SCHEMA_CHECKS:
        async with database.write() as session:
            checked = await sweep(session)
        mended = sum(checked.repaired.values())
        told = f"Mended {several(mended, 'value', 'values')}; {several(len(checked.findings), 'finding waits', 'findings wait')} for your word."
        return IntegrityOutcome(task, {**checked.repaired, "findings": len(checked.findings)}, told)
    async with database.write() as session:
        cosmos = await CosmosRepository(session).require_cosmos()
        swept = await sweep_dead_bonds(session, cosmos.epoch)
    counters = {"closed": swept.closed, "transferred": swept.transferred}
    return IntegrityOutcome(task, counters, f"Closed {several(swept.closed, 'bond', 'bonds')} of the dead and passed {swept.transferred} to heirs.")
