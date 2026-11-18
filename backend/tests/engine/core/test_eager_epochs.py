from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.kind_concepts.registry import CONCEPTS
from aerona.db.kind_concepts.spec import ConceptSpec
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.session import Database
from aerona.db.tables.changes import StateCheckpointRow
from aerona.db.tables.creator_bonds import CovenantRow, CreatorChosenRow
from aerona.db.tables.divine_powers import DivinePowerRow
from aerona.db.tables.kinds import KindHoldingRow
from aerona.db.tables.pantheon import PantheonStructureRow, PantheonTieRow, SyncretismRow
from aerona.engine.pipeline import simulate
from aerona.engine.recording.checkpoints import take_checkpoint
from aerona.rules.registry import Rules
from aerona.services.integrity.record_links import checkpoint_still_holds
from tests.engine.core.stirring import eager, stir
from tests.engine.integration.factories import seed_rich_cosmos

EPOCHS = 5
LIVED_DIVINE = (DivinePowerRow, PantheonStructureRow, PantheonTieRow, SyncretismRow, CovenantRow, CreatorChosenRow)
LIVED_STEPS = ("ways_of_life", "foodways", "crafts_of_life", "traits_and_works", "culture_kinds", "society_kinds")


async def twin_derivatives(session: AsyncSession, spec: ConceptSpec) -> bool:
    query = (
        select(KindHoldingRow.holder_node_id, spec.table.derived_from_id)
        .join(spec.table, spec.table.id == KindHoldingRow.kind_id)
        .where(KindHoldingRow.concept == spec.concept, spec.table.derived_from_id.is_not(None))
        .group_by(KindHoldingRow.holder_node_id, spec.table.derived_from_id)
        .having(func.count() > 1)
    )
    return await session.scalar(select(func.count()).select_from(query.subquery())) != 0


async def test_a_stirred_cosmos_lives_five_epochs_with_every_chance_certain(database: Database) -> None:
    async with database.write() as session:
        await stir(session, await seed_rich_cosmos(session))
    async with database.write() as session:
        holdings_before = await session.scalar(select(func.count()).select_from(KindHoldingRow))
        cosmos = await CosmosRepository(session).get()
        assert cosmos is not None
        start = cosmos.epoch
        await take_checkpoint(session, start)
    runs = await simulate(database, EPOCHS, rules=eager(Rules()))
    assert [run.epoch for run in runs] == sorted(run.epoch for run in runs) and len(runs) == EPOCHS
    async with database.read() as session:
        empty = [table.__tablename__ for table in LIVED_DIVINE if not await session.scalar(select(func.count()).select_from(table))]
        unmade = [spec.table.__tablename__ for spec in CONCEPTS.values() if not await session.scalar(select(func.count()).select_from(spec.table))]
        holdings_after = await session.scalar(select(func.count()).select_from(KindHoldingRow))
        twins = [spec.table.__tablename__ for spec in CONCEPTS.values() if await twin_derivatives(session, spec)]
        taken = await session.scalars(select(StateCheckpointRow).where(StateCheckpointRow.epoch == start).order_by(StateCheckpointRow.table_name))
        unrebuilt = [checkpoint.table_name for checkpoint in taken if not await checkpoint_still_holds(session, checkpoint)]
    work = {step: sum(value for run in runs for key, value in run.tick.stats.counters.items() if key.startswith(f"{step}.")) for step in LIVED_STEPS}
    idle = [step for step, done in work.items() if done <= 0]
    grown = (holdings_after or 0) > (holdings_before or 0)
    found = {"empty": empty, "unmade": unmade, "idle": idle, "holdings grew": grown, "twin derivatives": twins, "past not rebuilt": unrebuilt}
    assert found == {"empty": [], "unmade": [], "idle": [], "holdings grew": True, "twin derivatives": [], "past not rebuilt": []}
