import warnings

from sqlalchemy import event, exists, select, update
from sqlalchemy.orm import ORMExecuteState

from aerona.db.read_memo import DirtyStates, memo_of, pending_tables, table_names
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.economy import GoodsFlowRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import TraitRow
from aerona.db.tables.node import NameRegistryRow, NodeRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import TraitKind, TraitSource
from aerona.engine.economy.stocks import goods_of, holding
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.naming import Namer
from aerona.engine.primitives.queries import canon
from aerona.engine.services.community_relations import relation
from aerona.rules.registry import Rules
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


async def test_a_record_first_read_as_a_node_reads_whole_as_an_entity(realm: Realm) -> None:
    town = await settlement(realm, "Elmreach")
    town_id = town.id
    realm.session.expunge(town)
    node = await realm.session.get(NodeRow, town_id)
    assert node is not None
    found = await realm.session.get(EntityRow, town_id)
    assert found is not None and found.entity_type is EntityType.SETTLEMENT


async def test_a_read_flushes_only_when_it_reads_a_table_with_pending_changes(realm: Realm) -> None:
    town = await settlement(realm, "Fernhollow")
    town.name = "Fernhollow Vale"
    await realm.session.scalar(select(CosmosRow.epoch))
    assert town in realm.session.dirty
    named = await realm.session.scalar(select(NodeRow.name).where(NodeRow.id == town.id))
    assert named == "Fernhollow Vale" and town not in realm.session.dirty


async def test_dirty_tables_are_counted_as_rows_change_and_cleared_by_a_flush(realm: Realm) -> None:
    sync = realm.session.sync_session
    assert isinstance(sync.identity_map._modified, DirtyStates)
    first, second = await settlement(realm, "Ashford"), await settlement(realm, "Brackwater")
    await realm.session.flush()
    assert pending_tables(sync) == set()
    first.name = "Ashford Vale"
    second.name = "Brackwater Vale"
    assert "nodes" in pending_tables(sync)
    assert memo_of(realm.session, "probe", table_names([NodeRow])) is None
    assert memo_of(realm.session, "probe", table_names([CosmosRow])) is not None
    await realm.session.flush()
    assert pending_tables(sync) == set() and not sync.identity_map._modified.mappers
    sync.expunge_all()
    assert isinstance(sync.identity_map._modified, DirtyStates)


async def test_a_get_with_no_key_finds_nothing_without_asking_the_database(realm: Realm) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert await realm.session.get(EntityRow, None) is None
        assert await realm.session.get(GoodsFlowRow, (None, None, None, None)) is None


async def test_a_live_memo_lasts_through_changed_values_until_rows_come_or_go(realm: Realm) -> None:
    town = await settlement(realm, "Ashford")
    await realm.session.flush()
    names = table_names([NodeRow])
    memo = memo_of(realm.session, "live", names, live=True)
    assert memo is not None
    memo["kept"] = 1
    town.name = "Ashford Vale"
    assert memo_of(realm.session, "live", names) is None
    assert memo_of(realm.session, "live", names, live=True) == {"kept": 1}
    await realm.session.flush()
    assert memo_of(realm.session, "live", names, live=True) == {"kept": 1}
    await settlement(realm, "Brackwater")
    assert memo_of(realm.session, "live", names, live=True) == {}


async def test_the_goods_ledger_moves_stock_and_logs_flows_without_a_flush_per_call(realm: Realm) -> None:
    town = await settlement(realm, "Ashford")
    ledger = goods_of(realm.session, 3)
    await ledger.add(town.id, CommodityKind.GRAIN, 50, GoodsFlow.HARVEST)
    await ledger.take(town.id, CommodityKind.GRAIN, 5, GoodsFlow.CONSUMPTION)
    await realm.session.flush()
    flushes: list[object] = []
    event.listen(realm.session.sync_session, "before_flush", lambda *_: flushes.append(1))
    for _ in range(10):
        await ledger.add(town.id, CommodityKind.GRAIN, 7, GoodsFlow.HARVEST)
        await ledger.take(town.id, CommodityKind.GRAIN, 3, GoodsFlow.CONSUMPTION)
    assert flushes == []
    assert await holding(realm.session, town.id, CommodityKind.GRAIN) == 85
    flows = {row.flow: row.quantity for row in await realm.session.scalars(select(GoodsFlowRow).where(GoodsFlowRow.community_entity_id == town.id))}
    assert flushes == [1]
    assert flows == {GoodsFlow.HARVEST: 120, GoodsFlow.CONSUMPTION: -35}


async def test_a_narrow_canon_read_is_cut_from_a_wider_kept_one_and_matches_the_database(realm: Realm) -> None:
    await settlement(realm, "Alder")
    await settlement(realm, "Birch")
    await realm.session.flush()
    everything = await canon(realm.session)
    statements: list[str] = []
    sync = realm.session.sync_session

    def listener(state: ORMExecuteState) -> None:
        statements.append(str(state.statement))

    event.listen(sync, "do_orm_execute", listener)
    try:
        towns = await canon(realm.session, [EntityType.SETTLEMENT], realm.world.id)
    finally:
        event.remove(sync, "do_orm_execute", listener)
    assert not statements and towns and set(towns) <= set(everything)
    fresh = list(
        await realm.session.scalars(
            select(EntityRow)
            .where(EntityRow.status == EntityStatus.CANON, EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.world_id == realm.world.id)
            .order_by(EntityRow.id)
        )
    )
    assert towns == fresh


async def test_a_two_part_key_is_found_among_its_siblings_and_a_missing_one_stays_missing_until_it_is_added(realm: Realm) -> None:
    town = await settlement(realm, "Gorse")
    kinds = list(TraitKind)[:3]
    for kind in kinds[:2]:
        realm.session.add(TraitRow(node_id=town.id, trait=kind, source=TraitSource.BIRTH, epoch=1))
    await realm.session.flush()
    realm.session.expunge_all()
    first = await realm.session.get(TraitRow, (town.id, kinds[0]))
    second = await realm.session.get(TraitRow, (town.id, kinds[1]))
    assert first is not None and first.trait is kinds[0] and second is not None and second.trait is kinds[1]
    assert await realm.session.get(TraitRow, (town.id, kinds[2])) is None
    realm.session.add(TraitRow(node_id=town.id, trait=kinds[2], source=TraitSource.BIRTH, epoch=1))
    await realm.session.flush()
    third = await realm.session.get(TraitRow, (town.id, kinds[2]))
    assert third is not None and third.trait is kinds[2]


async def test_a_read_that_names_a_pending_table_only_in_a_subquery_still_flushes_first(realm: Realm) -> None:
    town = await settlement(realm, "Heath")
    other = await settlement(realm, "Ivybridge")
    await realm.session.flush()
    for target in (town, other):
        shaped = select(EntityRow.id).where(EntityRow.id == target.id, exists().where(BondRow.source_node_id == EntityRow.id, BondRow.kind == BondKind.ALLY))
        assert await realm.session.scalar(shaped) is None
    realm.session.add(BondRow(source_node_id=other.id, target_node_id=town.id, kind=BondKind.ALLY, state=BondState.ACTIVE, epoch=1))
    shaped = select(EntityRow.id).where(EntityRow.id == other.id, exists().where(BondRow.source_node_id == EntityRow.id, BondRow.kind == BondKind.ALLY))
    assert await realm.session.scalar(shaped) == other.id


async def test_each_namer_starts_from_the_registered_names_and_keeps_its_own_inventions_to_itself(realm: Realm) -> None:
    rules = Rules()
    first = await Namer(realm.session, rules).pool()
    first.add("Zzorquin")
    assert first.is_taken("Zzorquin")
    second = await Namer(realm.session, rules).pool()
    assert not second.is_taken("Zzorquin") and second is not first
    await settlement(realm, "Qorvathe")
    await realm.session.flush()
    assert await realm.session.scalar(select(NameRegistryRow.display).where(NameRegistryRow.display == "Qorvathe")) == "Qorvathe"
    third = await Namer(realm.session, rules).pool()
    assert third.is_taken("Qorvathe") and not second.is_taken("Qorvathe")
