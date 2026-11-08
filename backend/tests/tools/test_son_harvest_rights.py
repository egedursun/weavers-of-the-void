from aerona.db.session import Database
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from tests.tools.factories import seed_realm, son_toolkit
from tests.tools.test_son_tools import rejected


async def test_a_son_without_a_right_to_a_resource_is_told_what_it_may_harvest(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        resource = await session.get(EntityRow, realm.resource_id)
        sibling = await session.get(SonRow, realm.sibling_id)
        assert resource is not None and sibling is not None
        resource.creator_son_id = realm.son_id
        resource.domain = next(domain for domain in type(sibling.domain_primary) if domain not in sibling.domains)
    toolkit = await son_toolkit(database, realm.sibling_id)
    text = await rejected(toolkit, "harvest_resource", {"resource_id": realm.resource_id})
    assert "You have no right over this resource" in text and "Resources you may harvest:" in text
