from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.city_rules import ConurbationRow, LandUseRuleRow, MunicipalServiceRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.polity import LawJurisdictionRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.settlement import DistrictRow, SettlementInfrastructureRow, SettlementProfileRow
from aerona.domain.enums.city_rules import ConurbationGovernance, LandUseRule, MunicipalService
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, LawKind
from aerona.domain.enums.settlement import DistrictKind, SizeTier, WaterSupply
from aerona.domain.enums.urban import HousingLevel, Morphology, UrbanService
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.city_rules.book import CityTally
from aerona.engine.city_rules.conurbations import grow_together, join, tend_conurbations
from aerona.engine.city_rules.effects import above_cap, cost_factor, fire_cut, housing_cap, municipal_cover, use_barred
from aerona.engine.city_rules.land import plan_rules, rebuild, set_rule, tend_rules
from aerona.engine.city_rules.services import found_service, run_service, town_services
from aerona.engine.context import TickContext
from aerona.engine.polity.laws import enact
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, entity, settlement, tuned_rules


async def town_with(
    session: AsyncSession, world: CoreWorld, name: str, region: int = 0, *, treasury: int = 1000
) -> tuple[EntityRow, SettlementProfileRow, DistrictRow]:
    town = await settlement(session, name, world, world.regions[0], population=6000)
    profile = SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, treasury=treasury, crime=40, sanitation=20, locked=[])
    session.add(profile)
    district = DistrictRow(settlement_entity_id=town.id, kind=DistrictKind.RESIDENTIAL, level=2, built_epoch=0, land_value=100, locked=[])
    session.add(district)
    await session.flush()
    return town, profile, district


async def test_rules_bar_uses_cap_homes_cut_fire_and_raise_costs(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    town, _profile, district = await town_with(session, world, "Ruledholm")
    tally = CityTally()
    banned = await set_rule(ctx, town, LandUseRule.BANNED_USES, {"kinds": ["industrial"]}, tally)
    banned.strength = banned.enforcement = 100
    height = await set_rule(ctx, town, LandUseRule.HEIGHT_LIMIT, {"level": 1}, tally)
    height.strength = height.enforcement = 100
    spacing = await set_rule(ctx, town, LandUseRule.FIRE_SPACING, {}, tally)
    spacing.strength = spacing.enforcement = 100
    assert await use_barred(session, town.id, DistrictKind.INDUSTRIAL) and not await use_barred(session, town.id, DistrictKind.MARKET)
    district.housing = HousingLevel.HOUSE
    assert above_cap(district.housing, await housing_cap(session, district))
    assert await fire_cut(session, ctx.rules, town.id) == ctx.rules.city_rules.fire_spread_cut_pct / 100
    assert await cost_factor(session, ctx.rules, town.id) > 1 and tally.rules_set == 3


async def test_a_weakly_enforced_rule_on_dear_land_is_evaded_and_a_wrecked_town_rebuilds_to_plan(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "evaded", tuned_rules(city_rules={"evasion_per_land_value_pct": 100, "enforcement_follow_pct": 0}))
    town, profile, district = await town_with(session, world, "Evadeburg")
    rule = await set_rule(ctx, town, LandUseRule.FRONTAGE_RULE, {}, CityTally())
    rule.enforcement = 0
    tally = CityTally()
    await tend_rules(ctx, tally)
    assert rule.evasion >= 50 and tally.evaded == 1
    district.condition = 10
    await rebuild(ctx, town, profile, tally)
    assert district.condition == 100 and profile.morphology is Morphology.PLANNED and tally.rebuilt == 1


async def test_services_reach_districts_as_far_as_paid_and_fail_when_unpaid(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    town, profile, district = await town_with(session, world, "Servedton")
    tally = CityTally()
    refuse = await found_service(ctx, town, MunicipalService.REFUSE, tally, budget=1000)
    await run_service(ctx, refuse, town, tally)
    assert refuse.coverage[str(district.id)] == 100 and profile.sanitation > 20
    water = await found_service(ctx, town, MunicipalService.WATER_DISTRIBUTION, tally, budget=1000)
    await run_service(ctx, water, town, tally)
    assert (await municipal_cover(session, [district.id], town.id))[(district.id, UrbanService.WATER)] > 0
    lighting = await found_service(ctx, town, MunicipalService.LIGHTING, tally, budget=1000)
    await run_service(ctx, lighting, town, tally)
    assert profile.crime < 40
    profile.treasury = 0
    await run_service(ctx, refuse, town, tally)
    assert refuse.failed_epoch == ctx.epoch and tally.failed == 1
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "city.service_failed")) is not None


async def test_towns_of_one_realm_and_people_grow_together_spread_laws_and_split_under_strain(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "joined", tuned_rules(city_rules={"join_tie_threshold": 40}))
    core, core_profile, _district = await town_with(session, world, "Greatholm")
    member, member_profile, _other = await town_with(session, world, "Lesserholm")
    realm = await entity(session, "The Joined Crown", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    rule = next(iter(DecisionRule))
    session.add(PolityProfileRow(polity_entity_id=realm.id, government=next(iter(GovernmentKind)), decision_rule=rule, core_entity_id=core.id))
    session.add_all([PolityMemberRow(polity_entity_id=realm.id, member_entity_id=town.id) for town in (core, member)])
    await session.flush()
    tally = CityTally()
    await grow_together(ctx, tally)
    city = await session.scalar(select(ConurbationRow))
    assert city is not None and tally.joined == 1 and member.id in city.members
    law = await enact(ctx, core, LawKind.SERFDOM, {})
    city.governance = ConurbationGovernance.ONE_COUNCIL
    await tend_conurbations(ctx, tally)
    assert await session.get(LawJurisdictionRow, (law.id, member.id)) is not None
    member_profile.unrest, core_profile.unrest = 90, 10
    await tend_conurbations(ctx, tally)
    assert city.split_epoch == ctx.epoch and await session.get(LawJurisdictionRow, (law.id, member.id)) is None


async def test_a_joined_city_shares_unrest_under_one_council(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    core, core_profile, _district = await town_with(session, world, "Unity")
    member, member_profile, _other = await town_with(session, world, "Concord")
    core_profile.unrest, member_profile.unrest = 10, 30
    await join(ctx, core, [member], ConurbationGovernance.ONE_COUNCIL, CityTally())
    await tend_conurbations(ctx, CityTally())
    assert core_profile.unrest == member_profile.unrest == 20
    assert await session.scalar(select(MunicipalServiceRow.id)) is None


async def test_a_town_planned_or_given_water_in_a_later_epoch_gains_its_rules_and_service_once(
    ctx: TickContext, session: AsyncSession, world: CoreWorld
) -> None:
    tally = CityTally()
    await plan_rules(ctx, tally)
    await town_services(ctx, tally)
    town, profile, _district = await town_with(session, world, "Lateplan")
    profile.morphology = Morphology.PLANNED
    session.add(SettlementInfrastructureRow(settlement_entity_id=town.id, water=WaterSupply.WELL))
    await session.flush()
    await plan_rules(ctx, tally)
    await town_services(ctx, tally)
    rules = set(await session.scalars(select(LandUseRuleRow.rule).where(LandUseRuleRow.settlement_entity_id == town.id)))
    assert rules == {LandUseRule.FIRE_SPACING, LandUseRule.FRONTAGE_RULE}
    water = await session.scalar(select(MunicipalServiceRow).where(MunicipalServiceRow.settlement_entity_id == town.id))
    assert water is not None and water.service is MunicipalService.WATER_DISTRIBUTION
    water.failed_epoch, water.budget = ctx.epoch, 0
    for row in list(await session.scalars(select(LandUseRuleRow).where(LandUseRuleRow.settlement_entity_id == town.id))):
        await session.delete(row)
    await session.flush()
    await plan_rules(ctx, tally)
    await town_services(ctx, tally)
    assert await session.scalar(select(LandUseRuleRow.id).where(LandUseRuleRow.settlement_entity_id == town.id)) is None
    assert water.failed_epoch == ctx.epoch and water.budget == 0


async def test_a_service_paid_in_full_grows_better_its_budget_follows_need_and_an_unpaid_one_decays(
    ctx: TickContext, session: AsyncSession, world: CoreWorld
) -> None:
    town, profile, _district = await town_with(session, world, "Tendton", treasury=10_000)
    tally = CityTally()
    refuse = await found_service(ctx, town, MunicipalService.REFUSE, tally, budget=1)
    quality = refuse.quality
    await run_service(ctx, refuse, town, tally)
    assert refuse.budget > 1 and refuse.quality < quality
    refuse.budget = 10_000
    lowered = refuse.quality
    await run_service(ctx, refuse, town, tally)
    assert refuse.quality == lowered + ctx.rules.city_rules.quality_step and refuse.budget < 10_000
    assert profile.treasury < 10_000


async def test_a_rule_is_enforced_as_well_as_its_town_keeps_order_and_a_watch_helps(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "order", tuned_rules(city_rules={"enforcement_follow_pct": 100}))
    town, profile, district = await town_with(session, world, "Orderby")
    rule = await set_rule(ctx, town, LandUseRule.FIRE_SPACING, {}, CityTally())
    profile.crime = 40
    await tend_rules(ctx, CityTally())
    assert rule.enforcement == 60
    session.add(MunicipalServiceRow(settlement_entity_id=town.id, service=MunicipalService.NIGHT_WATCH, coverage={str(district.id): 100}, locked=[]))
    await session.flush()
    await tend_rules(ctx, CityTally())
    assert rule.enforcement == 100
