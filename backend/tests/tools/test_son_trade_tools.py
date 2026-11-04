from sqlalchemy import select

from aerona.db.session import Database
from aerona.db.tables.celestial import WorldMapRow
from aerona.db.tables.economy import TradeRouteProfileRow
from aerona.domain.enums.economy import TradeMode, TradeRouteStatus
from tests.engine.core.factories import region_record
from tests.tools.factories import seed_realm, son_toolkit


async def test_a_son_lays_closes_and_reopens_a_trade_route(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        geometry = {"regions": [region_record(realm.cosmos.region_id, []).model_dump(mode="json")]}
        session.add(WorldMapRow(world_id=realm.cosmos.world_id, generator_version=1, epoch=1, geometry=geometry))
    toolkit = await son_toolkit(database, realm.son_id, action_points=5)
    same = await toolkit.runtime.call("open_trade_route", {"first_id": realm.people_id, "second_id": realm.people_id, "reason": "salt must reach the folk"})
    assert same.is_error
    opened = await toolkit.runtime.call(
        "open_trade_route", {"first_id": realm.people_id, "second_id": realm.settlement_id, "mode": "river", "reason": "salt must reach the folk"}
    )
    assert not opened.is_error, opened.text
    async with database.read() as session:
        profile = await session.scalar(select(TradeRouteProfileRow))
        assert profile is not None and profile.mode is TradeMode.RIVER and profile.status is TradeRouteStatus.OPEN
        route_id = profile.route_entity_id
    twice = await toolkit.runtime.call(
        "open_trade_route", {"first_id": realm.people_id, "second_id": realm.settlement_id, "reason": "salt must reach the folk"}
    )
    assert twice.is_error
    closed = await toolkit.runtime.call("close_trade_route", {"route_id": route_id, "reason": "the salt-folk mocked me"})
    assert not closed.is_error, closed.text
    async with database.read() as session:
        profile = await session.get(TradeRouteProfileRow, route_id)
        assert profile is not None and profile.status is TradeRouteStatus.CLOSED and profile.closed_by_son_id == realm.son_id
    reopened = await toolkit.runtime.call("open_trade_route", {"first_id": realm.settlement_id, "second_id": realm.people_id, "reason": "I forgive them"})
    assert not reopened.is_error, reopened.text
    async with database.read() as session:
        profile = await session.get(TradeRouteProfileRow, route_id)
        assert profile is not None and profile.status is TradeRouteStatus.OPEN and profile.closed_by_son_id is None
    wrong = await toolkit.runtime.call("close_trade_route", {"route_id": realm.people_id, "reason": "the salt-folk mocked me"})
    assert wrong.is_error
