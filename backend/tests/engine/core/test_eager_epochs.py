from aerona.db.session import Database
from aerona.engine.pipeline import simulate
from aerona.rules.registry import Rules
from tests.engine.core.stirring import eager, stir
from tests.engine.integration.factories import seed_rich_cosmos

EPOCHS = 5


async def test_a_stirred_cosmos_lives_five_epochs_with_every_chance_certain(database: Database) -> None:
    async with database.write() as session:
        await stir(session, await seed_rich_cosmos(session))
    runs = await simulate(database, EPOCHS, rules=eager(Rules()))
    assert [run.epoch for run in runs] == sorted(run.epoch for run in runs) and len(runs) == EPOCHS
