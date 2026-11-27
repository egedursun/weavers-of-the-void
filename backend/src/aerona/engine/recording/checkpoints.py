import hashlib
import json
from collections.abc import Iterable, Mapping
from typing import Any

from sqlalchemy import Table, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.base import Base
from aerona.db.fixups import fixup_due
from aerona.db.ledger_capture import UNCAPTURED_TABLES, jsonable, key_text, table_plan
from aerona.db.tables.changes import StateChangeRow, StateCheckpointRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.types import UtcDateTime
from aerona.engine.recording.past import state_at

FIRST_CHECKPOINT_FIXUP = "records_first_checkpoint"


def captured_tables() -> list[Table]:
    return [table for table in Base.metadata.sorted_tables if table.name not in UNCAPTURED_TABLES]


def kept_columns(table: Table) -> tuple[str, ...]:
    plan = table_plan(table)
    names = [*(column.name for column in plan.primary), *plan.content]
    return tuple(dict.fromkeys(name for name in names if not isinstance(table.c[name].type, UtcDateTime)))


def digest_of(rows: Iterable[Mapping[str, Any]], columns: tuple[str, ...]) -> tuple[int, str]:
    lines = sorted(key_text({name: jsonable(row.get(name)) for name in columns}) for row in rows)
    hashed = hashlib.sha256()
    for line in lines:
        hashed.update(line.encode())
    return len(lines), hashed.hexdigest()


async def present_rows(session: AsyncSession, table: Table) -> list[dict[str, Any]]:
    return [dict(row) for row in (await session.execute(select(table))).mappings()]


async def last_change_id(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.coalesce(func.max(StateChangeRow.id), 0))) or 0)


async def take_checkpoint(session: AsyncSession, epoch: int) -> int:
    mark = await last_change_id(session)
    taken = 0
    for table in captured_tables():
        count, digest = digest_of(await present_rows(session, table), kept_columns(table))
        session.add(StateCheckpointRow(epoch=epoch, table_name=table.name, row_count=count, digest=digest, last_change_id=mark))
        taken += 1
    await session.flush()
    return taken


async def first_checkpoint(session: AsyncSession, epoch: int) -> int:
    if not await fixup_due(session, FIRST_CHECKPOINT_FIXUP):
        return 0
    taken = await take_checkpoint(session, epoch)
    session.add(AppliedFixupRow(key=FIRST_CHECKPOINT_FIXUP, result={"tables": taken, "epoch": epoch}))
    await session.flush()
    return taken


async def due(session: AsyncSession, epoch: int, every: int) -> bool:
    latest = await session.scalar(select(func.max(StateCheckpointRow.epoch)))
    return latest is None or epoch - int(latest) >= every


async def rows_at(session: AsyncSession, table: Table, epoch: int, until_change_id: int | None = None) -> list[dict[str, Any]]:
    plan = table_plan(table)
    keys = {key_text({column.name: row[column.name] for column in plan.primary}): row for row in await present_rows(session, table)}
    changed = await session.scalars(select(StateChangeRow.row_key).where(StateChangeRow.table_name == table.name).group_by(StateChangeRow.row_key))
    wanted = set(keys) | set(changed)
    found: list[dict[str, Any]] = []
    for row_key in sorted(wanted):
        row = await state_at(session, table.name, json.loads(row_key), epoch=epoch, until_change_id=until_change_id)
        if row is not None:
            found.append(row)
    return found


async def checkpoint_holds(session: AsyncSession, checkpoint: StateCheckpointRow) -> bool:
    table = Base.metadata.tables[checkpoint.table_name]
    count, digest = digest_of(await rows_at(session, table, checkpoint.epoch, checkpoint.last_change_id), kept_columns(table))
    return count == checkpoint.row_count and digest == checkpoint.digest
