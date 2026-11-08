from sqlalchemy import select

from aerona.db.tables.culture import TraditionParticipationRow, TraditionProfileRow
from aerona.db.tables.mind import MemoryRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import TraditionKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import ActKind
from aerona.domain.models.entity_stats import TraditionStats
from aerona.engine.lore.taboos import winter_rest
from tests.engine.society.factories import Realm, context, link, make, settlement


async def winter_taboo(realm: Realm, keeper_id: int, participation: int) -> int:
    taboo = await make(realm.session, f"Winter Peace {keeper_id}", EntityType.TRADITION, TraditionStats(), world_id=realm.world.id)
    realm.session.add(
        TraditionProfileRow(tradition_entity_id=taboo.id, kind=TraditionKind.TABOO, taboo_act=ActKind.WINTER_FIGHTING, cost={}, effects={}, locked=[])
    )
    realm.session.add(TraditionParticipationRow(tradition_entity_id=taboo.id, community_entity_id=keeper_id, participation=participation, locked=[]))
    await link(realm.session, keeper_id, taboo.id, BondKind.CELEBRATES)
    await realm.session.flush()
    return taboo.id


async def test_a_people_that_keeps_the_winter_peace_will_not_march_in_winter(realm: Realm) -> None:
    attacker, defender = await settlement(realm, "Northhold"), await settlement(realm, "Southmere")
    await winter_taboo(realm, attacker.id, participation=100)
    assert await winter_rest(context(realm.session), attacker.id, defender.id, shamed=False) == (True, False)


async def test_marching_on_a_people_that_keeps_the_winter_peace_shames_the_attacker_once(realm: Realm) -> None:
    attacker, defender = await settlement(realm, "Northhold"), await settlement(realm, "Southmere")
    await winter_taboo(realm, defender.id, participation=100)
    ctx = context(realm.session)
    assert await winter_rest(ctx, attacker.id, defender.id, shamed=False) == (False, True)
    grudge = await realm.session.scalar(select(MemoryRow).where(MemoryRow.holder_node_id == defender.id, MemoryRow.subject_node_id == attacker.id))
    assert grudge is not None and grudge.magnitude < 0
    assert await winter_rest(ctx, attacker.id, defender.id, shamed=True) == (False, True)


async def test_without_a_winter_taboo_war_goes_on(realm: Realm) -> None:
    attacker, defender = await settlement(realm, "Northhold"), await settlement(realm, "Southmere")
    assert await winter_rest(context(realm.session), attacker.id, defender.id, shamed=False) == (False, False)
