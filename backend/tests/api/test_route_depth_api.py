from aerona.db.tables.economy import ProductionRunRow, TradeRouteLossRow, WorkshopRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.domain.enums.economy import CommodityKind, TradeLoss, WorkshopKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.polity import DecisionRule, GovernmentKind
from aerona.domain.models.entity_stats import PolityStats
from tests.api.conftest import ApiWorld, seeded
from tests.engine.core.factories import entity, settlement


async def test_a_polity_sees_its_members_production_chain(api: ApiWorld) -> None:
    world = seeded(api).core
    async with api.services.database.write() as session:
        polity = await entity(session, "Crown of Quern", EntityType.POLITY, PolityStats(legitimacy=50), world_id=world.world.id)
        session.add(PolityProfileRow(polity_entity_id=polity.id, government=GovernmentKind.MONARCHY, decision_rule=DecisionRule.AUTOCRATIC, locked=[]))
        smithy = await settlement(session, "Brazenhyde", world, world.regions[0])
        mill = await settlement(session, "Quernhallow", world, world.regions[1])
        for member in (smithy, mill):
            session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=member.id))
        session.add(WorkshopRow(community_entity_id=smithy.id, kind=WorkshopKind.FORGE, level=2, built_epoch=1))
        session.add(
            ProductionRunRow(
                epoch=1, community_entity_id=smithy.id, step="forge_tools", workshop=WorkshopKind.FORGE, output=CommodityKind.TOOLS, quantity=12, quality=60
            )
        )
        session.add(
            ProductionRunRow(
                epoch=1,
                community_entity_id=mill.id,
                step="forge_tools",
                workshop=WorkshopKind.FORGE,
                output=CommodityKind.TOOLS,
                quantity=0,
                quality=0,
                bottleneck=CommodityKind.FUEL,
            )
        )
        polity_id, smithy_id, mill_id = polity.id, smithy.id, mill.id
    response = await api.http.get(f"/api/polities/{polity_id}/production")
    assert response.status_code == 200, response.text
    body = response.json()
    tools = next(step for step in body["chain"] if step["key"] == "forge_tools")
    assert tools["made"] == 12 and tools["bottleneck"] == "fuel"
    assert tools["running_ids"] == [smithy_id] and tools["starved_ids"] == [mill_id] and tools["able_ids"] == [smithy_id]
    assert {member["community_id"] for member in body["members"]} == {smithy_id, mill_id}
    assert body["workshops"] == {"forge": 2}
    assert (await api.http.get(f"/api/polities/{smithy_id}/production")).status_code == 404


async def test_route_actions_found_edit_toll_and_strike_a_route(api: ApiWorld) -> None:
    world = seeded(api).core
    async with api.services.database.write() as session:
        first = await settlement(session, "Qorvellan", world, world.regions[0])
        second = await settlement(session, "Ystrandel", world, world.regions[2])
        keeper = await settlement(session, "Mirefolden", world, world.regions[1])
        ids = (first.id, second.id, keeper.id)
    founded = await api.http.post(
        "/api/actions/trade_route:found", json={"first_id": ids[0], "second_id": ids[1], "mode": "road", "controller_id": ids[2], "toll_pct": 9}
    )
    assert founded.status_code == 200, founded.text
    routes = (await api.http.get("/api/trade-routes")).json()
    route = next(row for row in routes if {row["first_id"], row["second_id"]} == {ids[0], ids[1]})
    assert route["mode"] == "road" and route["controller_id"] == ids[2] and "mode" in route["locked"]
    assert route["tolls"] and route["tolls"][0]["rate_pct"] == 9 and route["tolls"][0]["controller_held"]
    assert set(route["dangers"]) == {"bandits", "beasts", "weather", "sea", "officials", "spoilage", "pilferage"} and 0 <= route["season_pct"] <= 100
    edited = await api.http.post("/api/actions/trade_route:edit", json={"route_id": route["route_id"], "values": {"danger_weather": 41, "chokepoint": True}})
    assert edited.status_code == 200, edited.text
    removed = await api.http.post("/api/actions/trade_route:toll_remove", json={"route_id": route["route_id"], "region_id": route["tolls"][0]["region_id"]})
    assert removed.status_code == 200, removed.text
    async with api.services.database.write() as session:
        session.add(TradeRouteLossRow(route_entity_id=route["route_id"], epoch=1, commodity=CommodityKind.GRAIN, cause=TradeLoss.BEASTS, units=7))
    detail = (await api.http.get(f"/api/trade-routes/{route['route_id']}")).json()
    assert detail["dangers"]["weather"] == 41 and detail["chokepoint"] and detail["untolled"] == [route["tolls"][0]["region_id"]]
    assert detail["losses"] == [{"epoch": 1, "commodity": "grain", "cause": "beasts", "units": 7, "culprit_id": None, "culprit_name": ""}]
    released = await api.http.post("/api/actions/trade_route:edit", json={"route_id": route["route_id"], "release": ["danger_weather"]})
    assert released.status_code == 200
    assert "danger_weather" not in (await api.http.get(f"/api/trade-routes/{route['route_id']}")).json()["locked"]
    struck = await api.http.post("/api/actions/trade_route:delete", json={"route_id": route["route_id"]})
    assert struck.status_code == 200, struck.text
    assert (await api.http.get(f"/api/trade-routes/{route['route_id']}")).json()["status"] == "decayed"
