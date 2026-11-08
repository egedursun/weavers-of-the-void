from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.economy import TradeRouteProfileRow
from aerona.db.tables.statecraft import PolityRegardRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.statecraft import ResolutionKind
from aerona.domain.models.entity_stats import OuterBeingStats
from aerona.engine.polity.assembly import breach, guard_routes, meddling_son, motion, outer_beings
from aerona.engine.polity.book import RealmBook
from tests.engine.society.factories import Realm, context, make, son, trade_route
from tests.engine.statecraft.test_statecraft import polity


async def test_an_incited_war_brings_a_sanction_and_an_outer_being_a_void_ban(realm: Realm) -> None:
    ctx = context(realm.session)
    _, first = await polity(realm, "Wolf Throne")
    _, second = await polity(realm, "Bear Throne")
    members = [first, second]
    assert await meddling_son(ctx, members) is None and not await outer_beings(ctx, members)
    assert await motion(ctx, members) is None
    god = await son(realm.session, "Vael", realm.world.id)
    await BondRepository(realm.session).connect(BondDraft(second.id, first.id, BondKind.ENEMY, 1, "incited", incited_by_son_id=god.id))
    assert await meddling_son(ctx, members) == god.id
    assert await motion(ctx, members) in {(ResolutionKind.SANCTION, god.id), (ResolutionKind.EMBARGO, second.id), (ResolutionKind.EMBARGO, first.id)}
    await make(realm.session, "The Hollow", EntityType.OUTER_BEING, OuterBeingStats(), world_id=realm.world.id)
    assert await outer_beings(ctx, members)


async def test_route_security_makes_the_members_roads_safer_and_a_breach_costs_trust(realm: Realm) -> None:
    ctx = context(realm.session)
    _, first = await polity(realm, "Wolf Throne")
    _, second = await polity(realm, "Bear Throne")
    road = await trade_route(realm, first, second)
    profile = await realm.session.get(TradeRouteProfileRow, road.id)
    assert profile is not None
    profile.danger_bandits = 50
    await guard_routes(ctx, [first, second])
    assert profile.danger_bandits == 50 - ctx.rules.affairs.route_safety
    book = await RealmBook.load(realm.session)
    await breach(ctx, book, first, [first, second])
    offender = book.realm_for(first.id)
    judge = book.realm_for(second.id)
    assert offender is not None and judge is not None
    regard = await realm.session.get(PolityRegardRow, (judge.entity.id, offender.entity.id))
    assert regard is not None and regard.trust < 50
