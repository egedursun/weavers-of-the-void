from aerona.db.session import Database
from aerona.db.tables.sacred import DoctrineAfterlifeRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.sacred import AfterlifeModel
from tests.tools.factories import seed_realm, son_toolkit
from tests.tools.test_son_tools import ok, rejected

REASON = "so that the faithful find what they were promised"


async def test_a_tool_cannot_change_a_value_the_god_holds_and_nothing_it_did_is_kept(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        session.add(DoctrineAfterlifeRow(cult_entity_id=realm.cult_id, model=next(iter(AfterlifeModel)), aligned=False, locked=["aligned"]))
    toolkit = await son_toolkit(database, realm.son_id, action_points=6)
    text = await rejected(toolkit, "align_afterlife", {"cult_id": realm.cult_id, "reason": REASON})
    assert "These fields are held and cannot change: the aligned of doctrine afterlives" in text
    async with database.read() as session:
        row = await session.get(DoctrineAfterlifeRow, realm.cult_id)
        son = await session.get(SonRow, realm.son_id)
        assert row is not None and row.aligned is False and son is not None and son.essence == 400
    async with database.write() as session:
        row = await session.get(DoctrineAfterlifeRow, realm.cult_id)
        assert row is not None
        row.locked = []
    await ok(toolkit, "align_afterlife", {"cult_id": realm.cult_id, "reason": REASON})
