from sqlalchemy import select

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.enums.bond import BondKind
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.route_control import route_of
from aerona.engine.economy.routes import RouteTally, _chokepoint_war, _pass_into_legend, _shipwreck
from aerona.engine.primitives.stats import stat
from tests.engine.society.factories import Realm, context, people, settlement, trade_route, tuned
from tests.engine.warfare.factories import society


async def test_a_storm_drowns_sailors_and_a_famous_road_passes_into_legend(realm: Realm) -> None:
    ctx = context(realm.session)
    port = await settlement(realm, "Saltmere", population=1000)
    far = await settlement(realm, "Farwatch")
    road = await trade_route(realm, port, far)
    route = await route_of(ctx, road.id)
    tally = RouteTally()
    await _shipwreck(ctx, route, port, tally)
    assert tally.shipwrecks == 1 and (stat(port, "population") or 0) == 1000 - ctx.rules.trade_routes.shipwreck_crew
    await _pass_into_legend(ctx, route)
    legend = await realm.session.scalar(select(BondRow).where(BondRow.kind == BondKind.TELLS_OF, BondRow.target_node_id == road.id))
    assert legend is not None
    lines = set(await realm.session.scalars(select(ChronicleRow.template_key)))
    assert {"trade_route.shipwreck", "trade_route.legend"} <= lines


async def test_merchants_go_to_war_over_a_chokepoint_its_master_holds(realm: Realm) -> None:
    ctx = context(realm.session, tuned(chokepoints={"war_chance": 100}))
    first = await people(realm, "Reed Folk")
    second = await people(realm, "Iron Folk")
    master = await people(realm, "Toll Folk")
    road = await trade_route(realm, first, second)
    await society(realm.session, first.id, merchant=60.0)
    route = await route_of(ctx, road.id)
    route.profile.controller_entity_id = master.id
    tally = RouteTally()
    await _chokepoint_war(ctx, await EconomyBook.load(ctx), route, tally)
    assert tally.wars == 1
    enemy = await realm.session.scalar(select(BondRow).where(BondRow.kind == BondKind.ENEMY, BondRow.target_node_id == master.id))
    assert enemy is not None and enemy.source_node_id == first.id
