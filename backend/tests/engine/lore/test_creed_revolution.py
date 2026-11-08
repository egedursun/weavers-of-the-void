from aerona.db.tables.culture import IdeologyAdherentRow, IdeologyProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import HELD_SCOPE, HeldScope
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import IdeologyTenet
from aerona.domain.enums.entity import EntityType
from aerona.engine.lore.control import create_lore
from aerona.engine.lore.ideology import revolution, spread
from tests.engine.society.factories import Realm, bonded, context, link, settlement, tuned
from tests.engine.statecraft.crowns import crown
from tests.engine.warfare.factories import society

RIPE = tuned(ideologies={"revolution_chance": 100})


async def ripe_realm(realm: Realm) -> tuple[int, int, int]:
    ctx = context(realm.session, RIPE)
    polity, core = await crown(realm, "Velmar")
    town = await settlement(realm, "Lowtown")
    realm.session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
    await society(realm.session, town.id)
    await realm.session.flush()
    held_society = await realm.session.get(CommunitySocietyRow, town.id)
    assert held_society is not None
    held_society.satisfaction_farmer = 5
    profile = await realm.session.get(PolityProfileRow, polity.id)
    assert profile is not None
    profile.stability = 5
    creed = await create_lore(
        ctx,
        EntityType.IDEOLOGY,
        name="The Levelling",
        description="",
        world_id=realm.world.id,
        location_id=None,
        power=3,
        values={"tenets": [IdeologyTenet.EGALITARIANISM.value]},
    )
    realm.session.add(IdeologyAdherentRow(ideology_entity_id=creed.id, adherent_entity_id=town.id, strength=90))
    await realm.session.flush()
    return creed.id, town.id, core.id


async def test_a_suffering_town_moved_by_an_equal_creed_rises_against_its_realm(realm: Realm) -> None:
    creed_id, town_id, core_id = await ripe_realm(realm)
    creed = await realm.session.get(EntityRow, creed_id)
    assert creed is not None
    told = await revolution(context(realm.session, RIPE), creed)
    assert told is not None and "rose against their rulers" in told
    assert await bonded(realm.session, town_id, core_id, BondKind.ENEMY)


async def test_a_held_town_does_not_rise(realm: Realm) -> None:
    creed_id, town_id, core_id = await ripe_realm(realm)
    creed = await realm.session.get(EntityRow, creed_id)
    assert creed is not None
    token = HELD_SCOPE.set(HeldScope(None, frozenset({town_id})))
    try:
        assert await revolution(context(realm.session, RIPE), creed) is None
    finally:
        HELD_SCOPE.reset(token)
    assert not await bonded(realm.session, town_id, core_id, BondKind.ENEMY)


async def test_a_creed_never_spreads_into_a_held_town(realm: Realm) -> None:
    creed_id, town_id, _ = await ripe_realm(realm)
    creed = await realm.session.get(EntityRow, creed_id)
    profile = await realm.session.get(IdeologyProfileRow, creed_id)
    assert creed is not None and profile is not None
    neighbour = await settlement(realm, "Nearby")
    await link(realm.session, town_id, neighbour.id, BondKind.TRADES_WITH)
    sure = tuned(ideologies={"spread_chance": 100})
    token = HELD_SCOPE.set(HeldScope(None, frozenset({neighbour.id})))
    try:
        assert await spread(context(realm.session, sure), creed, profile) == 0
    finally:
        HELD_SCOPE.reset(token)
    assert await realm.session.get(IdeologyAdherentRow, (creed_id, neighbour.id)) is None
    assert await spread(context(realm.session, sure), creed, profile) == 1
