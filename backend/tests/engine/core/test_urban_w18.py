from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.urban import cargo_class
from aerona.db.tables.economy import TradeRouteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.tables.urban import (
    ConvoyRow,
    CrimeStanceRow,
    DistrictServiceRow,
    FleetRow,
    MarketPlayRow,
    OrderLawRow,
    RacketRow,
    TradingPostRow,
    TribunalRow,
    TurfRow,
)
from aerona.domain.enums.economy import CommodityKind, TradeMode, TradeRouteStatus
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind, FactionRank
from aerona.domain.enums.settlement import DistrictKind
from aerona.domain.enums.structure import StructureKind
from aerona.domain.enums.urban import (
    CargoClass,
    ConvoyStatus,
    CrimeStance,
    HousingLevel,
    MarketPlay,
    Morphology,
    OrderLaw,
    Preservation,
    TransportKind,
    TribunalVerdict,
    UrbanService,
)
from aerona.domain.models.entity_stats import FactionStats, StructureStats, TradeRouteStats
from aerona.engine.context import TickContext
from aerona.engine.economy.cargo import carriage_factor, spoilage
from aerona.engine.economy.convoys import ConvoyTally, dispatch, fate_of, fleet_capacity, wear_fleets
from aerona.engine.economy.manipulation import swing
from aerona.engine.factions.crime import CrimeTally, bear_stances, keep_rackets
from aerona.engine.factions.mage_orders import OrderTally, try_member
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.manual import manual_context
from aerona.engine.settlement.book import town_of
from aerona.engine.settlement.districts import home_factor
from aerona.engine.urban.control import set_turf
from aerona.engine.urban.coverage import CoverageTally, cover_town, reach_of
from aerona.engine.urban.desirability import DesirabilityTally, assess_town
from aerona.engine.urban.housing import HousingTally, clear_slums, house_town, step_home
from aerona.engine.urban.morphology import grow_rings, replan, siege_of, spread_of
from aerona.engine.urban.turf import TurfTally, hold_turf
from aerona.services.integrity.urban_links import mend_urban_links
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement, tuned_rules


async def context(session: AsyncSession, **namespaces: dict[str, int]) -> TickContext:
    return await manual_context(session, "urban", rules=tuned_rules(**namespaces))


async def town_with_districts(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> EntityRow:
    town = await settlement(session, "Ashby", world, world.regions[0], population=2400)
    await town_of(ctx, town, await KnowledgeMap.load(session))
    await session.flush()
    return town


async def faction(session: AsyncSession, world: CoreWorld, kind: FactionKind, home: EntityRow, name: str) -> EntityRow:
    row = await entity(session, name, EntityType.FACTION, FactionStats(strength=40), world_id=world.world.id, location_id=home.id)
    session.add(FactionProfileRow(faction_entity_id=row.id, kind=kind, home_entity_id=home.id, influence_over={}, locked=[]))
    await session.flush()
    return row


def test_services_reach_further_in_planned_towns_and_fire_spreads_faster_in_crooked_ones() -> None:
    rules = tuned_rules()
    assert reach_of(rules, Morphology.PLANNED) > reach_of(rules, Morphology.ORGANIC)
    assert spread_of(rules, Morphology.ORGANIC) > spread_of(rules, Morphology.PLANNED)
    assert siege_of(rules, Morphology.CONCENTRIC) > siege_of(rules, Morphology.ORGANIC) == 0
    assert carriage_factor(rules, CommodityKind.STONE, TradeMode.SEA) < carriage_factor(rules, CommodityKind.STONE, TradeMode.ROAD)
    assert spoilage(rules, CommodityKind.FISH, TradeMode.ROAD, Preservation.NONE) > spoilage(rules, CommodityKind.FISH, TradeMode.ROAD, Preservation.ICED)
    assert cargo_class(CommodityKind.LIVESTOCK) is CargoClass.LIVESTOCK
    assert swing(rules, MarketPlay.CORNER, 100) > 1 > swing(rules, MarketPlay.DUMP, 100)


async def test_a_town_is_covered_by_its_services_and_its_districts_are_valued(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town = await town_with_districts(session, world, ctx)
    temple = await entity(session, "High Fane", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town.id)
    session.add(StructureProfileRow(structure_entity_id=temple.id, kind=StructureKind.TEMPLE, level=3, staff_pct=100))
    await session.flush()
    await cover_town(ctx, town, CoverageTally())
    profile = await session.get(StructureProfileRow, temple.id)
    assert profile is not None and profile.district_id is not None
    faith = await session.get(DistrictServiceRow, (profile.district_id, UrbanService.FAITH))
    assert faith is not None and faith.coverage > 0
    await assess_town(ctx, town, DesirabilityTally())
    district = await session.get(DistrictRow, profile.district_id)
    assert district is not None and district.desirability > 50


async def test_homes_rise_when_served_and_the_homeless_breed_slums(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, homelessness={"slum_share": 1})
    town = await town_with_districts(session, world, ctx)
    district = (await session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id == town.id))).first()
    assert district is not None
    district.land_value = 100
    assert home_factor(ctx.rules, district) == 1.0
    assert step_home(district, up=True) and district.housing is HousingLevel.TOWNHOUSE
    assert home_factor(ctx.rules, district) < 1.0
    town.stats = town.stats.model_copy(update={"population": 90000})
    await session.flush()
    await house_town(ctx, town, await KnowledgeMap.load(session), HousingTally())
    profile = await session.get(SettlementProfileRow, town.id)
    assert profile is not None and profile.homeless > 0
    kinds = {row.kind for row in await session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id == town.id))}
    assert DistrictKind.SLUMS in kinds
    cleared = await clear_slums(ctx, await town_of(ctx, town, await KnowledgeMap.load(session)))
    assert cleared >= 0
    assert DistrictKind.SLUMS not in {row.kind for row in await session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id == town.id))}


async def test_walls_ring_a_town_and_a_great_fire_replans_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town = await town_with_districts(session, world, ctx)
    built = await town_of(ctx, town, await KnowledgeMap.load(session))
    built.infrastructure.walls_level = ctx.rules.morphology.rings_at
    assert grow_rings(ctx.rules, built.profile, built.infrastructure)
    assert built.profile.morphology is Morphology.CONCENTRIC
    assert replan(built.profile) and built.profile.morphology is Morphology.PLANNED


async def test_criminal_turf_grows_pays_and_is_fought_for(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, turf={"claim_pct": 100, "claim_crime": 0, "war_pct": 100}, crime_orgs={"racket_pct": 100})
    town = await town_with_districts(session, world, ctx)
    family = await faction(session, world, FactionKind.CRIME_FAMILY, town, "Lantern Family")
    ring = await faction(session, world, FactionKind.SMUGGLING_RING, town, "Low Ring")
    tally = TurfTally()
    await hold_turf(ctx, tally)
    assert tally.claimed == 2
    district = (await session.scalars(select(TurfRow).where(TurfRow.faction_entity_id == family.id))).first()
    assert district is not None
    await set_turf(ctx, district.district_id, ring.id, 20)
    await hold_turf(ctx, tally)
    assert tally.wars >= 1
    profile = await session.get(FactionProfileRow, family.id)
    assert profile is not None
    crime = CrimeTally()
    await keep_rackets(ctx, family, profile, crime)
    assert crime.rackets == 1 and await session.scalar(select(RacketRow).where(RacketRow.faction_entity_id == family.id)) is not None


async def test_a_suppressing_realm_takes_turf_from_an_organisation(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town = await town_with_districts(session, world, ctx)
    family = await faction(session, world, FactionKind.CRIME_FAMILY, town, "Lantern Family")
    district = (await session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id == town.id))).first()
    assert district is not None
    turf = await set_turf(ctx, district.id, family.id, 60)
    assert "strength" in turf.locked
    turf.locked = []
    realm = world.people
    session.add(CrimeStanceRow(polity_entity_id=realm.id, faction_entity_id=family.id, stance=CrimeStance.SUPPRESS, strength=100, locked=[]))
    await session.flush()
    await bear_stances(ctx)
    assert turf.strength < 60


async def test_a_tribunal_casts_out_a_member_who_breaks_a_strong_law(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town = await town_with_districts(session, world, ctx)
    order = await faction(session, world, FactionKind.MAGE_ORDER, town, "Quiet Order")
    member = await mortal(session, "Vesh", world, town.id)
    session.add(FactionMembershipRow(faction_entity_id=order.id, mortal_entity_id=member.id, rank=FactionRank.MEMBER, locked=[]))
    law = OrderLawRow(faction_entity_id=order.id, law=OrderLaw.NO_OUTER_DEALINGS, strength=90, locked=[])
    session.add(law)
    await session.flush()
    await try_member(ctx, order, law, member.id, OrderTally())
    trial = await session.scalar(select(TribunalRow).where(TribunalRow.faction_entity_id == order.id))
    assert trial is not None and trial.verdict is TribunalVerdict.EXPELLED
    assert await session.get(FactionMembershipRow, (order.id, member.id)) is None


async def test_convoys_carry_their_route_and_fleets_wear(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    first = await town_with_districts(session, world, ctx)
    second = await settlement(session, "Lowmere", world, world.regions[1])
    route = await entity(session, "Long Road", EntityType.TRADE_ROUTE, TradeRouteStats(capacity=40), world_id=world.world.id)
    profile = TradeRouteProfileRow(
        route_entity_id=route.id,
        first_market_id=first.id,
        second_market_id=second.id,
        mode=TradeMode.ROAD,
        status=TradeRouteStatus.OPEN,
        length=2,
        founded_epoch=0,
        danger_bandits=100,
        locked=[],
    )
    session.add(profile)
    await session.flush()
    tally = ConvoyTally()
    await dispatch(ctx, route, profile, tally)
    await session.flush()
    convoy = await session.scalar(select(ConvoyRow).where(ConvoyRow.route_entity_id == route.id))
    assert convoy is not None and convoy.status is ConvoyStatus.TRAVELLING and convoy.capacity > 0
    assert fate_of(ctx.rules, convoy, profile, 0.0) is ConvoyStatus.RAIDED
    convoy.guards = 1000
    assert fate_of(ctx.rules, convoy, profile, 0.0) is ConvoyStatus.ARRIVED
    fleet = await session.get(FleetRow, (first.id, TransportKind.WAGONS))
    assert fleet is not None
    before = fleet_capacity(ctx.rules, fleet)
    await wear_fleets(ctx, tally)
    assert fleet.condition < 100 and fleet_capacity(ctx.rules, fleet) <= before


async def test_repairs_drop_the_turf_of_vanished_organisations(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town = await town_with_districts(session, world, ctx)
    family = await faction(session, world, FactionKind.CRIME_FAMILY, town, "Lantern Family")
    district = (await session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id == town.id))).first()
    assert district is not None
    await set_turf(ctx, district.id, family.id, 30)
    session.add(TradingPostRow(structure_entity_id=family.id, owner_entity_id=None, host_settlement_id=town.id, locked=[]))
    session.add(MarketPlayRow(holder_entity_id=family.id, settlement_entity_id=town.id, commodity=CommodityKind.GRAIN, play=MarketPlay.CORNER, locked=[]))
    await session.flush()
    family.status = EntityStatus.DESTROYED
    family.end_epoch = 1
    await session.flush()
    assert await mend_urban_links(session) >= 2
    assert await session.get(TurfRow, (district.id, family.id)) is None
