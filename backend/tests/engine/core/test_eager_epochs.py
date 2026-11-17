from sqlalchemy import func, select

from aerona.db.kind_concepts.registry import CONCEPTS
from aerona.db.session import Database
from aerona.db.tables.creator_bonds import CovenantRow, CreatorChosenRow
from aerona.db.tables.divine_powers import DivinePowerRow
from aerona.db.tables.kinds import KindHoldingRow
from aerona.db.tables.pantheon import PantheonStructureRow, PantheonTieRow, SyncretismRow
from aerona.engine.pipeline import simulate
from aerona.rules.registry import Rules
from tests.engine.core.stirring import eager, stir
from tests.engine.integration.factories import seed_rich_cosmos

EPOCHS = 5
LIVED_DIVINE = (DivinePowerRow, PantheonStructureRow, PantheonTieRow, SyncretismRow, CovenantRow, CreatorChosenRow)
LIVED_STEPS = ("ways_of_life", "foodways", "crafts_of_life", "traits_and_works", "culture_kinds", "society_kinds")


async def test_a_stirred_cosmos_lives_five_epochs_with_every_chance_certain(database: Database) -> None:
    async with database.write() as session:
        await stir(session, await seed_rich_cosmos(session))
    async with database.read() as session:
        holdings_before = await session.scalar(select(func.count()).select_from(KindHoldingRow))
    runs = await simulate(database, EPOCHS, rules=eager(Rules()))
    assert [run.epoch for run in runs] == sorted(run.epoch for run in runs) and len(runs) == EPOCHS
    async with database.read() as session:
        empty = [table.__tablename__ for table in LIVED_DIVINE if not await session.scalar(select(func.count()).select_from(table))]
        unmade = [spec.table.__tablename__ for spec in CONCEPTS.values() if not await session.scalar(select(func.count()).select_from(spec.table))]
        holdings_after = await session.scalar(select(func.count()).select_from(KindHoldingRow))
    work = {step: sum(value for run in runs for key, value in run.tick.stats.counters.items() if key.startswith(f"{step}.")) for step in LIVED_STEPS}
    idle = [step for step, done in work.items() if done <= 0]
    grown = (holdings_after or 0) > (holdings_before or 0)
    assert {"empty": empty, "unmade": unmade, "idle": idle, "holdings grew": grown} == {"empty": [], "unmade": [], "idle": [], "holdings grew": True}
