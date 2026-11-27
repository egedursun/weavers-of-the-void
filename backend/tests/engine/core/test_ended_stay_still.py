import json

from sqlalchemy import select

from aerona.db.profile_guard import profile_key, shape_of_table
from aerona.db.session import Database
from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.node import ActorKind
from aerona.engine.interconnect.ended import ENDING_STEPS, LASTING, RESTORED_COUNTER
from aerona.engine.pipeline import simulate
from aerona.rules.registry import Rules
from tests.engine.core.stirring import eager, stir
from tests.engine.integration.factories import seed_rich_cosmos

EPOCHS = 2


async def test_nothing_ended_in_an_earlier_age_is_changed_by_the_engine(database: Database) -> None:
    async with database.write() as session:
        await stir(session, await seed_rich_cosmos(session))
    runs = await simulate(database, EPOCHS, rules=eager(Rules()))
    kept = sorted({key for run in runs for stats in (run.tick.stats, run.transition) for key in stats.counters if f".{RESTORED_COUNTER}." in key})
    async with database.read() as session:
        rows = (
            await session.execute(
                select(StateChangeRow.table_name, StateChangeRow.phase, StateChangeRow.field, StateChangeRow.row_key, StateChangeRow.node_id)
                .join(EntityRow, EntityRow.id == StateChangeRow.node_id)
                .where(
                    StateChangeRow.actor_kind == ActorKind.ENGINE,
                    StateChangeRow.operation == LedgerOperation.UPDATE,
                    EntityRow.end_epoch.is_not(None),
                    EntityRow.end_epoch < StateChangeRow.epoch,
                )
            )
        ).all()
    moved: set[str] = set()
    for table, phase, field, key, node in rows:
        shape = shape_of_table(table)
        if shape is None or phase in ENDING_STEPS or profile_key(table, field or "") in LASTING or json.loads(key).get(shape.node_column) != node:
            continue
        moved.add(f"{table}.{field} by {phase}")
    assert sorted(moved) == []
    assert kept == [], f"engine steps that tried to change what ended in an earlier age: {kept}"
