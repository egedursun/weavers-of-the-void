from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.society_depth import DriftCause
from aerona.domain.models.entity_stats import SettlementStats
from aerona.engine.demography.society_control import impose_drift, set_corvee
from aerona.engine.economy.stocks import goods_of
from aerona.engine.phases.society_economy import society_economy
from tests.api.conftest import ApiWorld, seeded
from tests.engine.core.factories import entity
from tests.engine.society.factories import context


async def test_society_depth_shows_needs_wealth_labour_and_drift(api: ApiWorld) -> None:
    core = seeded(api).core
    async with api.services.database.write() as session:
        town = await entity(
            session,
            "Ashford",
            EntityType.SETTLEMENT,
            SettlementStats(population=3000, prosperity=50, defense=40, piety=50),
            world_id=core.world.id,
            location_id=core.regions[0].id,
        )
        session.add(
            CommunitySocietyRow(
                entity_id=town.id,
                **{f"share_{item.value}": 10.0 for item in SocialClass},
                **{f"satisfaction_{item.value}": 50 for item in SocialClass},
                stock_food=100,
                stock_ore=100,
                stock_goods=100,
                price_food=100,
                price_ore=100,
                price_goods=100,
            )
        )
        await session.flush()
        ctx = context(session)
        await goods_of(session, ctx.epoch).add(town.id, CommodityKind.GRAIN, 5000, GoodsFlow.SEED)
        await society_economy(ctx)
        await set_corvee(ctx, town.id, 25, None)
        await impose_drift(ctx, town.id, DriftCause.FAMINE, ValueAxis.KINSHIP, 5, 2)
        town_id = town.id
    body = (await api.http.get(f"/api/entities/{town_id}/society-depth")).json()
    assert body["entity_id"] == town_id
    assert {item["social_class"] for item in body["classes"]} == {item.value for item in SocialClass}
    assert body["needs"] and all(item["effect"] for item in body["needs"])
    assert body["corvee"]["share_pct"] == 25
    assert body["impositions"][0]["cause"] == "famine"
    assert {item["effect"] for item in body["effects"]} >= {"hunger", "sickness"}
    assert len(body["prices"]) == len(CommodityKind)
