from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.affairs import MandateRow
from aerona.db.tables.agrarian import CommonsRow, IntensificationRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.agrarian import CommonsKind, CommonsRule
from aerona.domain.enums.settlement import SizeTier
from aerona.engine.agrarian.lands import LandsTally, holdings, keep_commons
from aerona.engine.primitives.stats import stat_or
from tests.engine.core.factories import CoreWorld, mortal
from tests.engine.core.test_agrarian_w23 import BIG, realm, surveyed, town

QUIET = {"enclose_pct": 0, "council_chance": 0}


async def kinds(session: AsyncSession) -> set[str]:
    return set(await session.scalars(select(IncidentRow.kind)))


async def common_at(session: AsyncSession, world: CoreWorld, steward: EntityRow, rule: CommonsRule, **values: int) -> CommonsRow:
    session.add(IntensificationRow(region_entity_id=world.regions[1].id, pressure=150, locked=[]))
    row = CommonsRow(region_entity_id=world.regions[1].id, kind=CommonsKind.PASTURE, steward_entity_id=steward.id, rule=rule, condition=80, locked=[], **values)
    session.add(row)
    await session.flush()
    return row


async def crowned(session: AsyncSession, world: CoreWorld) -> tuple[EntityRow, EntityRow, EntityRow]:
    village = await town(session, world, "Brack", 1, BIG, tier=SizeTier.VILLAGE)
    city = await town(session, world, "Hollin", 3, BIG, tier=SizeTier.CITY)
    crown = await realm(session, world, [city, village], await mortal(session, "Ruler", world, city.id))
    return village, city, crown


async def test_a_realm_holds_a_common_to_its_quota_poachers_slip_past_weak_officials_and_folk_grieve(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session, commons=QUIET | {"poaching_pct": 100})
    village, _, crown = await crowned(session, world)
    common = await common_at(session, world, village, CommonsRule.STATE, quota=50, officials=0)
    before = await session.get(SettlementProfileRow, village.id)
    assert before is not None
    order_before = before.public_order
    purse = await session.get(PolityProfileRow, crown.id)
    assert purse is not None
    treasury = purse.treasury
    await keep_commons(ctx, await holdings(ctx), LandsTally())
    assert common.use > common.quota and "commons.poaching" in await kinds(session)
    profile = await session.get(SettlementProfileRow, village.id)
    assert profile is not None and profile.public_order == order_before - ctx.rules.commons.state_grievance
    assert purse.treasury > treasury
    common.officials, common.use = 100, 0
    await session.flush()
    await keep_commons(ctx, await holdings(ctx), LandsTally())
    assert common.use == common.quota


async def test_licences_cap_use_at_the_quota_sell_permits_and_favour_the_holder(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await surveyed(session, commons=QUIET)
    village, _, crown = await crowned(session, world)
    neighbour = await town(session, world, "Moss", 1, BIG, tier=SizeTier.VILLAGE)
    common = await common_at(session, world, village, CommonsRule.LICENSED, quota=40, licence_price=50)
    purse = await session.get(PolityProfileRow, crown.id)
    assert purse is not None
    treasury = purse.treasury
    held_before, other_before = stat_or(village, "prosperity", 0), stat_or(neighbour, "prosperity", 0)
    await keep_commons(ctx, await holdings(ctx), LandsTally())
    assert common.use == common.quota
    assert purse.treasury >= treasury + common.quota * common.licence_price // 100 and "commons.licences_sold" in await kinds(session)
    assert stat_or(village, "prosperity", 0) - held_before > stat_or(neighbour, "prosperity", 0) - other_before


async def test_a_ruler_s_move_on_a_common_can_set_officials_sell_permits_or_order_enclosure(session: AsyncSession, world: CoreWorld) -> None:
    village, _, _ = await crowned(session, world)
    common = await common_at(session, world, village, CommonsRule.CUSTOMARY)
    ctx = await surveyed(session, commons={"enclose_pct": 100, "council_chance": 0, "state_take_pct": 100, "licensed_take_pct": 0})
    await keep_commons(ctx, await holdings(ctx), LandsTally())
    assert common.rule is CommonsRule.STATE and common.officials == ctx.rules.commons.state_enforcement
    assert "commons.rule_changed" in await kinds(session)
    common.rule = CommonsRule.CUSTOMARY
    ctx = await surveyed(session, commons={"enclose_pct": 100, "council_chance": 0, "state_take_pct": 0, "licensed_take_pct": 100})
    await keep_commons(ctx, await holdings(ctx), LandsTally())
    assert common.rule is CommonsRule.LICENSED and common.licence_price == ctx.rules.commons.licence_price
    common.rule = CommonsRule.CUSTOMARY
    ctx = await surveyed(session, commons={"enclose_pct": 100, "council_chance": 0, "state_take_pct": 0, "licensed_take_pct": 0})
    await keep_commons(ctx, await holdings(ctx), LandsTally())
    assert await session.scalar(select(MandateRow.id).where(MandateRow.settlement_entity_id == village.id)) is not None
    assert common.rule is not CommonsRule.STATE and common.rule is not CommonsRule.LICENSED
