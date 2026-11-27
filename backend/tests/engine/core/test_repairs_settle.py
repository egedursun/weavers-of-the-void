from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.session import Database
from aerona.engine.pipeline import simulate
from aerona.rules.registry import Rules
from aerona.services.bonds import BondService
from aerona.services.chronicle import ChronicleWriter
from aerona.services.integrity import network
from aerona.services.integrity.data_repairs import DataRepairs
from aerona.services.notifications import Notifier
from tests.engine.core.stirring import eager, stir
from tests.engine.integration.factories import seed_rich_cosmos


async def test_every_repair_settles_after_one_pass_over_a_lived_world(database: Database) -> None:
    async with database.write() as session:
        await stir(session, await seed_rich_cosmos(session))
    rules = eager(Rules())
    await simulate(database, 1, rules=rules)
    repairs = DataRepairs(BondService(ChronicleWriter(Notifier())), network.RepairLog())
    async with database.write() as session:
        epoch = (await CosmosRepository(session).require_cosmos()).epoch
        await repairs.run_all(session, rules, epoch)
        await repairs.schema(session, rules, epoch)
    async with database.write() as session:
        again = await repairs.run(session, rules)
        schema = await repairs.schema(session, rules, epoch)
    assert {name: count for name, count in again.items() if count} == {}
    assert schema == 0
