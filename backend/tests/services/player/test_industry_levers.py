import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.economy import WorkshopRow
from aerona.db.tables.industry import CommunityIndustryRow, CommunityMethodRow, RegionPollutionRow
from aerona.db.tables.ownership import SiteProfitRow
from aerona.domain.enums.economy import WorkshopKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.industry import MethodKind, ProcessKind
from aerona.services.player import industry
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity


async def test_the_god_sets_holds_and_releases_a_way_of_working(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    city = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    made = await industry.set_method(scope, industry.SetMethod(community_id=city.id, method=MethodKind.WATERMILL))
    row = await session.get(CommunityMethodRow, made.values["method_id"])
    assert row is not None and row.process is ProcessKind.MILLING and row.locked == ["method"]
    await industry.set_method(scope, industry.SetMethod(community_id=city.id, method=MethodKind.WINDMILL, hold=False))
    assert row.method is MethodKind.WINDMILL and row.locked == []
    await industry.remove_method(scope, industry.MethodTarget(community_id=city.id, process=ProcessKind.MILLING))
    assert await session.scalar(select(CommunityMethodRow).where(CommunityMethodRow.community_node_id == city.id)) is None
    with pytest.raises(NotFoundError):
        await industry.remove_method(scope, industry.MethodTarget(community_id=city.id, process=ProcessKind.MILLING))
    with pytest.raises(ValidationFailedError):
        await industry.set_method(scope, industry.SetMethod(community_id=world.region.id, method=MethodKind.WATERMILL))


async def test_the_god_sets_power_and_stores_and_wipes_them(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    city = await make_entity(session, "Brindle", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    await industry.set_industry(scope, industry.SetIndustry(community_id=city.id, water=40, magic=12, meal_quality=70, tools_worn=3, light=55))
    row = await session.get(CommunityIndustryRow, city.id)
    assert row is not None and row.water == 40 and row.magic == 12 and row.meal_quality == 70
    assert set(row.locked) == {"water", "magic", "meal_quality", "tools_worn", "light"} and row.light == 55
    with pytest.raises(ValidationFailedError):
        await industry.set_industry(scope, industry.SetIndustry(community_id=city.id))
    await industry.remove_industry(scope, industry.IndustryTarget(community_id=city.id))
    assert await session.get(CommunityIndustryRow, city.id) is None


async def test_the_god_fouls_cleanses_and_wipes_a_land(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    await industry.set_pollution(scope, industry.SetPollution(region_id=world.region.id, air=40, soil=70))
    row = await session.get(RegionPollutionRow, world.region.id)
    assert row is not None and row.air == 40 and row.soil == 70 and set(row.locked) == {"air", "soil"}
    await industry.purify(scope, industry.PurifyLand(region_id=world.region.id, amount=30))
    assert row.air == 10 and row.soil == 40 and row.water == 0
    await industry.remove_pollution(scope, industry.PollutionTarget(region_id=world.region.id))
    assert await session.get(RegionPollutionRow, world.region.id) is None
    city = await make_entity(session, "Cray", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    with pytest.raises(ValidationFailedError):
        await industry.set_pollution(scope, industry.SetPollution(region_id=city.id, air=10))


async def test_the_god_gives_a_workshop_and_rewrites_and_strikes_its_ledger(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    city = await make_entity(session, "Dunmere", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    lord = await make_entity(session, "Orrin", EntityType.MORTAL, world_id=world.world.id, location_id=city.id)
    forge = WorkshopRow(community_entity_id=city.id, kind=WorkshopKind.FORGE, level=2, built_epoch=1)
    session.add(forge)
    await session.flush()
    await industry.set_workshop_owner(scope, industry.SetWorkshopOwner(community_id=city.id, kind=WorkshopKind.FORGE, owner_id=lord.id))
    assert forge.owner_node_id == lord.id and forge.held
    await industry.set_workshop_owner(scope, industry.SetWorkshopOwner(community_id=city.id, kind=WorkshopKind.FORGE, owner_id=None, hold=False))
    assert forge.owner_node_id is None and not forge.held
    with pytest.raises(NotFoundError):
        await industry.set_workshop_owner(scope, industry.SetWorkshopOwner(community_id=city.id, kind=WorkshopKind.MILL, owner_id=lord.id))
    entry = SiteProfitRow(epoch=1, owner_node_id=lord.id, community_node_id=city.id, workshop_id=forge.id, site="forge", revenue=90, profit=40, locked=[])
    session.add(entry)
    await session.flush()
    await industry.edit_site_profit(scope, industry.EditSiteProfit(profit_id=entry.id, profit=-15, taxes=12))
    assert entry.profit == -15 and entry.taxes == 12 and set(entry.locked) == {"profit", "taxes"}
    await industry.remove_site_profit(scope, industry.SiteProfitTarget(profit_id=entry.id))
    assert await session.get(SiteProfitRow, entry.id) is None
