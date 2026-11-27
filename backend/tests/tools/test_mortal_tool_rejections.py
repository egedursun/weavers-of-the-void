from aerona.db.session import Database
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from tests.engine.core.factories import tuned_rules
from tests.tools.every_setup_orders import seated_member
from tests.tools.factories import connect, mortal_toolkit, seed_realm
from tests.tools.test_mortal_tools import bonds_between, ok, rejected

SURE = tuned_rules(mortal_tools={"sabotage_die": 1, "sabotage_caught_margin": 100})


async def open_town(database: Database, settlement_id: int) -> None:
    async with database.write() as session:
        town = await session.get(EntityRow, settlement_id)
        assert town is not None
        town.stats = town.stats.model_copy(update={"defense": 0, "prosperity": 0})


async def test_sown_discord_breaks_the_targets_alliance(database: Database) -> None:
    realm = await seed_realm(database)
    await open_town(database, realm.settlement_id)
    async with database.write() as session:
        await connect(session, realm.settlement_id, realm.people_id, BondKind.ALLY)
    toolkit = await mortal_toolkit(database, realm.faction_id, rules=SURE)
    text = await ok(toolkit, "sabotage", {"target_id": realm.settlement_id, "kind": "discord", "how": "rumours between the councils"})
    assert "dissolved" in text
    assert await bonds_between(database, realm.settlement_id, realm.people_id, BondKind.ALLY) == 0


async def test_discord_without_an_alliance_breaks_nothing(database: Database) -> None:
    realm = await seed_realm(database)
    await open_town(database, realm.settlement_id)
    toolkit = await mortal_toolkit(database, realm.faction_id, rules=SURE)
    text = await ok(toolkit, "sabotage", {"target_id": realm.settlement_id, "kind": "discord", "how": "rumours between the councils"})
    assert "there was no alliance to break" in text.lower()


async def test_a_refused_trade_lists_the_partners_near_enough(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await mortal_toolkit(database, realm.people_id)
    text = await rejected(toolkit, "establish_trade", {"target_id": realm.mortal_id, "goods": "grain"})
    assert "Invalid partner." in text
    assert "Fitting ones near you:" in text or "Nothing fitting is near you." in text


async def test_bartering_away_what_one_does_not_own_lists_what_one_does(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await mortal_toolkit(database, realm.people_id)
    text = await rejected(toolkit, "barter", {"target_id": realm.settlement_id, "give_ids": [realm.resource_id], "terms": "goods for goods"})
    assert "What you own and can give:" in text
    async with database.write() as session:
        await connect(session, realm.people_id, realm.resource_id, BondKind.OWNS)
    owned = await rejected(toolkit, "barter", {"target_id": realm.settlement_id, "give_ids": [realm.species_id], "terms": "goods for goods"})
    assert f"#{realm.resource_id}" in owned


async def test_one_whom_custom_retired_for_their_age_cannot_seek_a_headship(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        org = (await seated_member(session, realm))["org"]
        seeker = await session.get(EntityRow, realm.mortal_id)
        assert seeker is not None
        seeker.stats = seeker.stats.model_copy(update={"age": 99, "lifespan": 100})
    toolkit = await mortal_toolkit(database, realm.mortal_id)
    text = await rejected(toolkit, "seek_headship", {"org_id": org})
    assert "custom retires those of your age" in text
