from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import HELD_SCOPE, HeldScope
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.settlement import SizeTier
from aerona.engine.phases.mortal_life import ethnic_relations
from aerona.engine.primitives.stats import stat
from aerona.engine.services.community_relations import change_relation, relation
from tests.engine.society.factories import Realm, context, link, people, settlement, tuned
from tests.engine.statecraft.crowns import crown

STRIFE = tuned(ethnic={"strife_chance": 100})


async def two_peoples(realm: Realm, regard: int) -> tuple[PolityProfileRow, list[EntityRow], list[EntityRow]]:
    polity, _ = await crown(realm, "Velmar")
    folks = [await people(realm, "Hill Folk", population=9000), await people(realm, "Reed Folk", population=3000)]
    towns = []
    for index, folk in enumerate(folks):
        town = await settlement(realm, f"Town {index}")
        realm.session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, treasury=0, unrest=10, locked=[], foreigners={}))
        realm.session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
        await link(realm.session, town.id, folk.id, BondKind.DESCENDS_FROM)
        towns.append(town)
    await realm.session.flush()
    await change_relation(context(realm.session), folks[0].id, folks[1].id, regard, MemoryKind.GOODWILL if regard > 0 else MemoryKind.ILL_WILL)
    profile = await realm.session.get(PolityProfileRow, polity.id)
    assert profile is not None
    profile.stability = 60
    return profile, folks, towns


async def test_hostile_peoples_of_one_realm_clash_and_the_weaker_bleeds(realm: Realm) -> None:
    profile, folks, towns = await two_peoples(realm, regard=-90)
    ctx = context(realm.session, STRIFE)
    await ethnic_relations(ctx)
    table = ctx.rules.ethnic
    assert stat(folks[1], "population") == 3000 - round(3000 * table.strife_population_pct / 100)
    assert stat(folks[0], "population") == 9000
    assert profile.stability == 60 - table.strife_stability
    for town in towns:
        row = await realm.session.get(SettlementProfileRow, town.id)
        assert row is not None and row.unrest == 10 + table.strife_unrest


async def test_friendly_peoples_of_one_realm_draw_closer(realm: Realm) -> None:
    _, folks, _ = await two_peoples(realm, regard=90)
    ctx = context(realm.session, STRIFE)
    before = await relation(realm.session, ctx.rules, folks[0].id, folks[1].id)
    await ethnic_relations(ctx)
    assert await relation(realm.session, ctx.rules, folks[0].id, folks[1].id) >= before
    assert stat(folks[1], "population") == 3000


async def test_peoples_of_a_held_realm_keep_the_peace(realm: Realm) -> None:
    profile, folks, _ = await two_peoples(realm, regard=-90)
    token = HELD_SCOPE.set(HeldScope(None, frozenset({profile.polity_entity_id})))
    try:
        await ethnic_relations(context(realm.session, STRIFE))
    finally:
        HELD_SCOPE.reset(token)
    assert stat(folks[1], "population") == 3000 and profile.stability == 60
