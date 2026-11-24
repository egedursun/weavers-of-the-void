from aerona.catalog.life.domain import GONE_STATES
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.structure import ConstructionState, StructureKind
from aerona.domain.models.entity_stats import StructureStats
from aerona.engine.structures.leftovers import abandon_work, dismantle, gather_legend
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, chronicle_keys, context, make, settlement

RULES = Rules()


def test_seven_construction_states_and_three_gone() -> None:
    assert len(ConstructionState) == 8
    assert {ConstructionState.RUINED, ConstructionState.ABANDONED, ConstructionState.DISMANTLED} == GONE_STATES


async def test_an_abandoned_work_gathers_a_legend_and_a_dismantled_one_feeds_new_building(realm: Realm) -> None:
    town = await settlement(realm, "Domefall")
    realm.session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, locked=[], foreigners={}))
    work = await make(realm.session, "The Half Dome", EntityType.STRUCTURE, StructureStats(), world_id=realm.world.id, location_id=town.id)
    profile = StructureProfileRow(structure_entity_id=work.id, kind=StructureKind.TEMPLE, host_entity_id=town.id, construction_state=ConstructionState.BUILDING)
    realm.session.add(profile)
    await realm.session.flush()
    ctx = context(realm.session, RULES)
    await abandon_work(ctx, work, profile, by=None)
    assert profile.construction_state is ConstructionState.ABANDONED
    assert await gather_legend(ctx, work, profile)
    assert not await gather_legend(ctx, work, profile)
    gained = await dismantle(ctx, work, profile, by=town.id)
    pool = await realm.session.get(SettlementProfileRow, town.id)
    assert gained > 0 and pool is not None and pool.investment_pool == gained
    assert profile.construction_state is ConstructionState.DISMANTLED and work.status is not EntityStatus.CANON
    keys = await chronicle_keys(realm.session)
    assert {"structure.left_unfinished", "structure.legend_gathered", "structure.dismantled"} <= set(keys)
