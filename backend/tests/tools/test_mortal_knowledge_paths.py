from aerona.db.session import Database
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from tests.engine.core.factories import tuned_rules
from tests.tools.factories import connect, mortal_toolkit, seed_realm
from tests.tools.test_mortal_tools import bonds_between, ok, rejected

LONG = "A careful account of what was learned, written out at length so the record says what it is and how it came to be known."


async def branch_of(database: Database, knowledge_id: int) -> str:
    async with database.read() as session:
        knowledge = await session.get(EntityRow, knowledge_id)
        assert knowledge is not None and knowledge.knowledge_branch is not None
        return knowledge.knowledge_branch.value


async def test_developing_a_branch_already_known_deepens_it(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        await connect(session, realm.people_id, realm.knowledge_id, BondKind.KNOWS)
    toolkit = await mortal_toolkit(database, realm.people_id)
    branch = await branch_of(database, realm.knowledge_id)
    text = await ok(toolkit, "develop_knowledge", {"branch": branch, "name": "Deeper Craft", "description": LONG})
    assert f"#{realm.knowledge_id}" in text and "level" in text.lower()


async def test_developing_a_full_branch_finds_the_knowledge_others_hold(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await mortal_toolkit(database, realm.people_id, rules=tuned_rules(knowledge={"branch_record_cap": 1}))
    branch = await branch_of(database, realm.knowledge_id)
    text = await ok(toolkit, "develop_knowledge", {"branch": branch, "name": "Found Craft", "description": LONG})
    assert f"#{realm.knowledge_id}" in text
    assert await bonds_between(database, realm.people_id, realm.knowledge_id, BondKind.KNOWS) == 1


async def test_learning_from_one_who_does_not_know_names_who_does(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        await connect(session, realm.settlement_id, realm.knowledge_id, BondKind.KNOWS)
    toolkit = await mortal_toolkit(database, realm.people_id)
    text = await rejected(toolkit, "learn_knowledge", {"knowledge_id": realm.knowledge_id, "from_id": realm.faction_id})
    assert "#" in text or "nobody you trade with" in text
