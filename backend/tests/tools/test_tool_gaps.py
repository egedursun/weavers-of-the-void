from aerona.db.session import Database
from aerona.db.tables import EntityRow
from aerona.domain.enums.bond import BondKind
from tests.engine.core.factories import tuned_rules
from tests.tools.factories import mortal_toolkit, seed_realm, son_toolkit
from tests.tools.test_mortal_tools import bonds_between
from tests.tools.test_son_tools import ok, rejected


async def test_a_son_speaks_with_a_foreign_god_once_per_age(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=6)
    await ok(toolkit, "talk_to_foreign_god", {"god_id": realm.god_id, "intent": "bargain", "words": "let us share the storm"})
    text = await rejected(toolkit, "talk_to_foreign_god", {"god_id": realm.god_id, "intent": "bargain", "words": "hear me once more"})
    assert "already spoke" in text


async def test_a_watchful_target_catches_the_spies(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        target = await session.get(EntityRow, realm.settlement_id)
        assert target is not None
        target.stats = target.stats.model_copy(update={"defense": 100})
    rules = tuned_rules(mortal_tools={"spy_war_threshold": 0, "spy_die": 1, "spy_caught_margin": 0})
    toolkit = await mortal_toolkit(database, realm.people_id, action_points=3, rules=rules)
    text = await ok(toolkit, "build_spy_network", {"target_id": realm.settlement_id, "cover": "pilgrims bearing salt"})
    assert "caught" in text and "enemy" in text
    assert await bonds_between(database, realm.people_id, realm.settlement_id, BondKind.SPY_NETWORK) == 0
    assert await bonds_between(database, realm.settlement_id, realm.people_id, BondKind.ENEMY) == 1
