from sqlalchemy import update

from aerona.db.read_memo import memo_of
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.entities import EntityRow
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.services.community_relations import relation
from tests.engine.society.factories import Realm, context, settlement


async def test_memoised_reads_last_until_the_next_write(realm: Realm) -> None:
    memo = memo_of(realm.session, "probe")
    assert memo is not None
    memo["kept"] = 1
    assert memo_of(realm.session, "probe") == {"kept": 1}
    town = await settlement(realm, "Quarry")
    assert memo_of(realm.session, "probe") == {}
    town.name = "Quarrytown"
    assert memo_of(realm.session, "probe") is None
    await realm.session.flush()
    again = memo_of(realm.session, "probe")
    assert again == {}
    again["kept"] = 2
    await realm.session.execute(update(CosmosRow).values(epoch=CosmosRow.epoch))
    assert memo_of(realm.session, "probe") == {}


async def test_relations_and_the_atlas_are_reused_until_something_changes(realm: Realm) -> None:
    ctx = context(realm.session)
    first = await settlement(realm, "Alder")
    second = await settlement(realm, "Birch")
    value = await relation(realm.session, ctx.rules, first.id, second.id)
    assert await relation(realm.session, ctx.rules, first.id, second.id) == value
    atlas = await RegionAtlas.load(realm.session)
    assert await RegionAtlas.load(realm.session) is atlas
    second.location_id = realm.far_region.id
    await realm.session.flush()
    moved = await RegionAtlas.load(realm.session)
    assert moved is not atlas and moved.top_region(second.id) == realm.far_region.id


async def test_a_fast_get_finds_known_rows_and_remembers_missing_ones_until_they_exist(realm: Realm) -> None:
    town = await settlement(realm, "Cedar")
    town_id = town.id
    assert await realm.session.get(EntityRow, town_id) is town
    assert await realm.session.get(EntityRow, 10_000_000) is None
    assert await realm.session.get(EntityRow, 10_000_000) is None
    realm.session.expire(town)
    assert await realm.session.get(EntityRow, town_id) is town
    late = await settlement(realm, "Dogwood")
    assert await realm.session.get(EntityRow, late.id) is late
