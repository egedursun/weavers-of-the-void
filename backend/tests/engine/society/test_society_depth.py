from collections import Counter
from dataclasses import replace

import pytest
from sqlalchemy import select

from aerona.catalog.commodities import COMMODITIES, FOOD_KINDS
from aerona.catalog.needs import JOB_GOODS, SERVE_ORDER, SHORTFALL_EFFECTS, WORKSHOP_JOBS
from aerona.db.repositories.cosmos import rules_from_snapshot, snapshot_differences
from aerona.db.tables.culture import IdeologyAdherentRow, IdeologyProfileRow
from aerona.db.tables.demography import LabourRow, PeopleCultureRow
from aerona.db.tables.economy import WorkshopRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.military import CaptiveCohortRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.polity import HouseMemberRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.society_depth import ClassStandingRow, CommunityNeedRow, DriftCauseRow, LabourReasonRow, MobilityEventRow
from aerona.domain.enums.demography import Aesthetic, InheritanceCustom, Job, MarriageCustom, MartialStyle
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, WorkshopKind
from aerona.domain.enums.entity import EngineKind, EntityType, MortalRole
from aerona.domain.enums.environment import TemperatureBand
from aerona.domain.enums.mind import PressureKind, ValueAxis
from aerona.domain.enums.polity import DecisionRule, GovernmentKind
from aerona.domain.enums.society import Commodity, SocialClass
from aerona.domain.enums.society_depth import DriftCause, LabourReason, LoyaltyPart, MobilityEvent, ShortfallEffect
from aerona.domain.models.entity_stats import FactionStats, IdeologyStats, PolityStats
from aerona.engine.demography.backfill import society_depth_backfill
from aerona.engine.demography.basket import (
    Basket,
    ClassNeed,
    apply_shortfalls,
    build_basket,
    class_need_penalty,
    effect_shortfalls,
    serve,
    serve_order,
    split,
    staples_of,
)
from aerona.engine.demography.cohorts import seed
from aerona.engine.demography.events import ennobled, enslaved, freed, ruined
from aerona.engine.demography.labour import Grounds, Plan, allocate, corvee, draw, gate, hold, job_pull, price_pull
from aerona.engine.demography.recruitment import recruit, recruitment_factor, recruits
from aerona.engine.demography.society_control import edit_standing, hold_need, impose_drift, set_corvee, set_labour
from aerona.engine.demography.wealth import gini, wealth_targets
from aerona.engine.economy.household import Meal, Wear, diet_demand, eat, eating_order
from aerona.engine.economy.stocks import goods_of, holding, nourishment_need
from aerona.engine.mind.book import write_pressures
from aerona.engine.mind.drift_causes import famine_shift, ideology_shift, impositions_of, lost_war_sign, record_causes, spend_impositions
from aerona.engine.phases.society_economy import EconomyInputs, satisfaction_targets, society_economy
from aerona.engine.polity.book import Realm as Holding
from aerona.engine.polity.loyalty import autonomy_pull, loyalty_of, mean_satisfaction, member_loyalty, satisfaction_term
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, chronicle_keys, context, make, mortal, people, settlement

RULES = Rules()
EVEN = {social_class: 10.0 for social_class in SocialClass}
INPUTS = EconomyInputs(
    harvest_pct=100,
    at_war=False,
    routes=1,
    pays_tribute=False,
    has_god=True,
    godless=False,
    cursed=False,
    bounty_law=False,
    justice=None,
    fertility=50,
    branches=frozenset(),
    piety=50,
    prosperity=50,
    skilled_crafts=False,
)
STOCKS = {Commodity.FOOD: 120, Commodity.ORE: 120, Commodity.GOODS: 120}


def test_every_commodity_has_a_typed_shortfall_and_a_trade() -> None:
    assert set(SHORTFALL_EFFECTS) == set(CommodityKind)
    assert set(SHORTFALL_EFFECTS.values()) == set(ShortfallEffect)
    made = {kind for goods in JOB_GOODS.values() for kind in goods}
    assert made == set(CommodityKind)
    assert set(WORKSHOP_JOBS) == set(WorkshopKind)
    assert set(SERVE_ORDER) == set(SocialClass)


def test_cuisine_staples_set_dietary_demand_and_eating_order() -> None:
    plain = diet_demand(RULES, 1000, (), nourishment_need(RULES, 1000))
    fish = diet_demand(RULES, 1000, (CommodityKind.FISH,), nourishment_need(RULES, 1000))
    assert fish[CommodityKind.FISH] > plain[CommodityKind.FISH]
    assert fish[CommodityKind.GRAIN] < plain[CommodityKind.GRAIN]
    nourish = {kind: COMMODITIES[kind].nourishment for kind in FOOD_KINDS}
    assert abs(sum(fish[kind] * nourish[kind] for kind in fish) - sum(plain[kind] * nourish[kind] for kind in plain)) <= sum(nourish.values())
    assert eating_order((CommodityKind.FISH,))[0] is CommodityKind.FISH
    assert set(eating_order((CommodityKind.FISH,))) == set(eating_order(()))


def test_split_and_serve_feed_the_first_in_line() -> None:
    parts = split(10, {SocialClass.NOBLE: 1.0, SocialClass.FARMER: 3.0})
    assert sum(parts.values()) == 10 and parts[SocialClass.FARMER] > parts[SocialClass.NOBLE]
    served = serve(5, {SocialClass.NOBLE: 3, SocialClass.FARMER: 7}, SERVE_ORDER)
    assert served[SocialClass.NOBLE] == 3 and served[SocialClass.FARMER] == 2


def basket_for(luxuries: int, medicine: int, *, staples: tuple[CommodityKind, ...] = (), fish: int = 100) -> Basket:
    meal = Meal(100, {CommodityKind.GRAIN: 500, CommodityKind.FISH: fish}, {}, {CommodityKind.GRAIN: 500, CommodityKind.FISH: 100})
    worn = Wear({CommodityKind.LUXURIES: 100, CommodityKind.MEDICINE: 100}, {CommodityKind.LUXURIES: luxuries, CommodityKind.MEDICINE: medicine})
    return build_basket(EVEN, meal, worn, staples=staples, order=SERVE_ORDER, held={}, luxuries_left=0)


def test_needs_basket_by_class_and_typed_effects() -> None:
    full = basket_for(100, 100)
    short = basket_for(20, 0)
    assert full.effects[ShortfallEffect.SICKNESS] == 0 and short.effects[ShortfallEffect.SICKNESS] == 100
    assert short.effects[ShortfallEffect.STATUS] == 80
    assert short.classes[SocialClass.NOBLE].effects[ShortfallEffect.STATUS] < short.classes[SocialClass.MERCHANT].effects[ShortfallEffect.STATUS]
    assert short.classes[SocialClass.FARMER].needs_met_pct < full.classes[SocialClass.FARMER].needs_met_pct
    held = build_basket(
        EVEN,
        Meal(100, {}, {}, {}),
        Wear({CommodityKind.MEDICINE: 100}, {CommodityKind.MEDICINE: 0}),
        staples=(),
        order=SERVE_ORDER,
        held={(SocialClass.FARMER, CommodityKind.MEDICINE): 100},
        luxuries_left=0,
    )
    want, got = held.rows[(SocialClass.FARMER, CommodityKind.MEDICINE)]
    assert got == want > 0


def test_staple_shortfall_and_luxury_plenty_move_satisfaction() -> None:
    missing = basket_for(100, 100, staples=(CommodityKind.FISH,), fish=0)
    assert missing.classes[SocialClass.FARMER].staple_short_pct > 0
    plenty = ClassNeed(luxury_pct=RULES.consumption.luxury_plenty_pct)
    assert class_need_penalty(RULES, SocialClass.MERCHANT, plenty) < 0
    assert class_need_penalty(RULES, SocialClass.FARMER, plenty) == 0
    hungry = {SocialClass.MERCHANT: ClassNeed(fed_pct=20, needs_met_pct=30)}
    content = {SocialClass.MERCHANT: plenty}
    assert (
        satisfaction_targets(RULES, INPUTS, STOCKS, content)[SocialClass.MERCHANT] > satisfaction_targets(RULES, INPUTS, STOCKS, hungry)[SocialClass.MERCHANT]
    )
    assert satisfaction_targets(RULES, INPUTS, STOCKS, corvee_pct=100)[SocialClass.FARMER] < satisfaction_targets(RULES, INPUTS, STOCKS)[SocialClass.FARMER]
    scorned = satisfaction_targets(RULES, INPUTS, STOCKS, freed_pct=100)
    assert scorned[SocialClass.ARTISAN] < satisfaction_targets(RULES, INPUTS, STOCKS)[SocialClass.ARTISAN]


def test_gini_over_class_wealth() -> None:
    shares = {SocialClass.FARMER: 50.0, SocialClass.NOBLE: 50.0}
    assert gini({SocialClass.FARMER: 100, SocialClass.NOBLE: 100}, shares) == 0
    assert gini({SocialClass.FARMER: 0, SocialClass.NOBLE: 100}, shares) == 50
    targets = wealth_targets(1000, shares)
    assert targets[SocialClass.NOBLE] > targets[SocialClass.FARMER]
    assert gini(targets, shares) > 0


def test_labour_follows_prices_structures_and_resources() -> None:
    plan = Plan(workers=Counter({Job.FARMING: 1000, Job.MINING: 100, Job.FISHING: 50}))
    gate(plan, Grounds({}, [], coastal=False))
    assert plan.workers[Job.MINING] == 0 and plan.workers[Job.FISHING] == 0
    assert plan.reasons[(Job.MINING, LabourReason.NO_STRUCTURE)].workers == -100
    kept = Plan(workers=Counter({Job.FARMING: 1000, Job.MINING: 100}))
    gate(kept, Grounds({WorkshopKind.MINE: 1}, [], coastal=False))
    assert kept.workers[Job.MINING] == 100
    drawn = Plan(workers=Counter({Job.FARMING: 1000}))
    draw(RULES, drawn, Grounds({WorkshopKind.FORGE: 2}, [(Job.MINING, CommodityKind.ORE)], coastal=False))
    assert drawn.workers[Job.CRAFTING] == 2 * RULES.labour.workshop_workers_per_level
    assert drawn.workers[Job.MINING] == RULES.labour.resource_workers
    assert drawn.reasons[(Job.CRAFTING, LabourReason.STRUCTURE)].workshop is WorkshopKind.FORGE
    prices = {kind: 100 for kind in CommodityKind} | {CommodityKind.TOOLS: 400, CommodityKind.GRAIN: 50, CommodityKind.BREAD: 50}
    assert job_pull(prices, Job.CRAFTING) > 0 > job_pull(prices, Job.FARMING)
    pulled = Plan(workers=Counter({Job.FARMING: 1000, Job.CRAFTING: 10}))
    price_pull(RULES, pulled, prices)
    assert pulled.workers[Job.CRAFTING] > 10
    assert pulled.reasons[(Job.CRAFTING, LabourReason.PRICE)].commodity is CommodityKind.TOOLS
    corvee_plan = Plan(workers=Counter({Job.FARMING: 1000}))
    corvee(corvee_plan, 50)
    assert corvee_plan.workers[Job.BUILDING] == 500


def test_held_labour_is_kept() -> None:
    plan = Plan(workers=Counter({Job.FARMING: 1000, Job.TRADE: 10}))
    hold(plan, {Job.TRADE: LabourRow(community_entity_id=1, job=Job.TRADE, workers=300, output_pct=100, epoch=1, held=True)})
    assert plan.workers[Job.TRADE] == 300 and plan.workers[Job.FARMING] == 710


def test_lost_wars_turn_on_cohesion_and_loyalty_formula() -> None:
    assert lost_war_sign(RULES, RULES.culture_drift.lost_war_cohesion) == 1
    assert lost_war_sign(RULES, RULES.culture_drift.lost_war_cohesion - 1) == -1
    near = loyalty_of(RULES, 0, 0, 10, 0)
    far = loyalty_of(RULES, 80, 20, 0, -10)
    assert near > far
    assert autonomy_pull(RULES, 10) > 0 > autonomy_pull(RULES, 90)
    assert satisfaction_term(RULES, 80) > 0 > satisfaction_term(RULES, 20)
    assert mean_satisfaction(None) == 50


def test_discontent_raises_faction_recruitment() -> None:
    society = CommunitySocietyRow(entity_id=1, satisfaction_merchant=10)
    assert recruitment_factor(RULES, society, SocialClass.MERCHANT) > 1
    assert recruits(RULES, society, SocialClass.MERCHANT) > 0
    society.satisfaction_merchant = 90
    assert recruitment_factor(RULES, society, SocialClass.MERCHANT) < 1
    assert recruits(RULES, society, SocialClass.MERCHANT) < 0


def test_old_rule_keys_map_into_the_new_namespaces() -> None:
    rules = rules_from_snapshot({"economy": {"consumption_grain_per_1000": 777.0}, "peoples": {"levy_martial_pct": 222.0}})
    assert rules.consumption.grain_per_1000 == 777
    assert rules.levies.martial_pct == 222
    assert rules_from_snapshot({"mobilisation": {"harvest_pct": 33.0}}).levies.harvest_pct == 33
    newer = rules_from_snapshot({"economy": {"consumption_fish_per_1000": 1.0}, "consumption": {"fish_per_1000": 9.0}})
    assert newer.consumption.fish_per_1000 == 9
    assert ("consumption", "grain_per_1000") in snapshot_differences({"economy": {"consumption_grain_per_1000": 777.0}}, Rules())


async def stocked_town(realm: Realm, name: str = "Ashford", population: int = 4000) -> object:
    town = await settlement(realm, name, population=population)
    realm.session.add(
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
    await realm.session.flush()
    return town


async def test_society_economy_writes_baskets_wealth_and_gini(realm: Realm) -> None:
    town = await stocked_town(realm)
    ctx = context(realm.session)
    ledger = goods_of(realm.session, ctx.epoch)
    for kind in (CommodityKind.GRAIN, CommodityKind.FISH, CommodityKind.LUXURIES, CommodityKind.CLOTH, CommodityKind.FUEL):
        await ledger.add(town.id, kind, 2000, GoodsFlow.SEED)
    await society_economy(ctx)
    needs = list(await realm.session.scalars(select(CommunityNeedRow).where(CommunityNeedRow.community_entity_id == town.id)))
    standing = list(await realm.session.scalars(select(ClassStandingRow).where(ClassStandingRow.community_entity_id == town.id)))
    assert needs and {row.social_class for row in standing} == set(SocialClass)
    society = await realm.session.get(CommunitySocietyRow, town.id)
    assert society is not None and society.gini > 0
    effects = await effect_shortfalls(realm.session, town.id)
    assert effects[ShortfallEffect.SICKNESS] > 0 and effects[ShortfallEffect.COLD] < effects[ShortfallEffect.SICKNESS]


async def test_each_shortfall_has_its_mechanical_effect(realm: Realm) -> None:
    town = await stocked_town(realm, population=20000)
    ctx = context(realm.session, replace(RULES, consumption=replace(RULES.consumption, notable_cold_deaths=1, notable_sick=1)))
    await seed(realm.session, ctx.rules, town, ctx.epoch)
    await goods_of(realm.session, ctx.epoch).add(town.id, CommodityKind.LIVESTOCK, 1000, GoodsFlow.SEED)
    before = {key: stat(town, key) or 0 for key in ("population", "piety", "prosperity", "defense")}
    shortfalls = {effect: 100 for effect in ShortfallEffect}
    done = await apply_shortfalls(ctx, town, Basket({}, {}, shortfalls), TemperatureBand.COLD)
    assert set(done) == set(ShortfallEffect)
    assert (stat(town, "population") or 0) < before["population"]
    assert (stat(town, "piety") or 0) < before["piety"]
    assert (stat(town, "prosperity") or 0) < before["prosperity"]
    assert (stat(town, "defense") or 0) < before["defense"]
    assert await holding(realm.session, town.id, CommodityKind.LIVESTOCK) < 1000
    assert done[ShortfallEffect.SICKNESS] > 0
    keys = await chronicle_keys(realm.session)
    assert {"consumption.cold_deaths", "consumption.sickness", "consumption.herd_loss"} <= set(keys)


async def test_cuisine_staples_feed_eating(realm: Realm) -> None:
    folk = await people(realm, "Fishers")
    ctx = context(realm.session)
    ledger = goods_of(realm.session, ctx.epoch)
    await ledger.add(folk.id, CommodityKind.FISH, 5000, GoodsFlow.SEED)
    await ledger.add(folk.id, CommodityKind.GRAIN, 5000, GoodsFlow.SEED)
    meal = await eat(ctx, folk, (CommodityKind.FISH,))
    assert meal.fed_pct == 100
    assert (
        meal.eaten[CommodityKind.FISH]
        >= meal.wanted[CommodityKind.FISH]
        > diet_demand(ctx.rules, 5000, (), nourishment_need(ctx.rules, 5000))[CommodityKind.FISH]
    )


async def test_labour_allocation_records_reasons_and_honours_holds_and_corvee(realm: Realm) -> None:
    town = await stocked_town(realm)
    ctx = context(realm.session)
    realm.session.add(WorkshopRow(community_entity_id=town.id, kind=WorkshopKind.FORGE, level=1, built_epoch=1))
    await realm.session.flush()
    await set_labour(ctx, town.id, Job.TRADE, 77)
    await set_corvee(ctx, town.id, 40, None)
    found = await allocate(ctx, town, None, wet_cold=False)
    assert found[Job.TRADE].workers == 77 and found[Job.TRADE].held
    reasons = {(row.job, row.reason) for row in await realm.session.scalars(select(LabourReasonRow).where(LabourReasonRow.community_entity_id == town.id))}
    assert (Job.CRAFTING, LabourReason.STRUCTURE) in reasons
    assert (Job.BUILDING, LabourReason.CORVEE) in reasons
    assert (Job.MINING, LabourReason.NO_STRUCTURE) in reasons
    assert "labour.corvee" in await chronicle_keys(realm.session)
    await set_labour(ctx, town.id, Job.TRADE, None)
    assert not (await allocate(ctx, town, None, wet_cold=False))[Job.TRADE].held


async def test_famine_and_scholars_drive_culture(realm: Realm) -> None:
    folk = await people(realm, "Hillfolk")
    ctx = context(realm.session)
    await write_pressures(realm.session, folk.id, dict.fromkeys(PressureKind, 0) | {PressureKind.HUNGER: 90})
    assert await famine_shift(realm.session, ctx.rules, folk.id) == ctx.rules.culture_drift.famine_kinship
    sage = await mortal(realm, "Orsa", role=MortalRole.SAGE)
    sage.affiliated_entity_id = folk.id
    school = await make(realm.session, "The Even Way", EntityType.IDEOLOGY, IdeologyStats(adherents=1, appeal=40), world_id=realm.world.id)
    realm.session.add(IdeologyProfileRow(ideology_entity_id=school.id, value_delta={"mercy": 40}, tenets=[], appeal={}, texts=[], locked=[]))
    realm.session.add(IdeologyAdherentRow(ideology_entity_id=school.id, adherent_entity_id=sage.id, strength=100))
    await realm.session.flush()
    pull = await ideology_shift(realm.session, ctx.rules, folk.id)
    assert pull[ValueAxis.MERCY] > 0
    await record_causes(ctx, folk.id, {DriftCause.FAMINE: {ValueAxis.KINSHIP: 50.0}}, 12)
    row = await realm.session.get(DriftCauseRow, (folk.id, DriftCause.FAMINE, ValueAxis.KINSHIP))
    assert row is not None and row.amount == 6 and row.total == 6


async def test_mobility_events_are_incidents_memories_and_houses(realm: Realm) -> None:
    town = await stocked_town(realm)
    origin = await people(realm, "Captured")
    hero = await mortal(realm, "Brann", location_id=town.id)
    merchant = await mortal(realm, "Cass", location_id=town.id)
    ctx = context(realm.session)
    realm.session.add(CaptiveCohortRow(captor_entity_id=town.id, origin_entity_id=origin.id, count=30, since_epoch=1))
    await realm.session.flush()
    await enslaved(ctx, town, 30)
    await freed(ctx, town, 5)
    house = await ennobled(ctx, hero, town)
    await ruined(ctx, merchant, None)
    events = [row.event for row in await realm.session.scalars(select(MobilityEventRow).order_by(MobilityEventRow.id))]
    assert events == [MobilityEvent.ENSLAVED, MobilityEvent.FREED, MobilityEvent.ENNOBLED, MobilityEvent.RUINED]
    assert house is not None
    assert await realm.session.scalar(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == hero.id)) == house.id
    memories = {row.kind.value for row in await realm.session.scalars(select(MemoryRow))}
    assert {"held_captive", "freed_us", "gifted_me"} <= memories
    kinds = set(await realm.session.scalars(select(IncidentRow.kind)))
    assert {"society.enslaved", "society.freed", "society.ennobled", "society.ruined"} <= kinds


async def test_holds_on_class_standing_and_needs(realm: Realm) -> None:
    town = await stocked_town(realm)
    ctx = context(realm.session)
    row = await edit_standing(ctx, town.id, SocialClass.OUTCAST, {"wealth": 99999}, release=[])
    assert "wealth" in row.locked
    standing = {SocialClass.OUTCAST: row}
    assert serve_order(standing, EVEN)[0] is SocialClass.OUTCAST
    need = await hold_need(ctx, town.id, SocialClass.FARMER, CommodityKind.MEDICINE, 100)
    assert need.held_pct == 100
    await society_economy(ctx)
    await realm.session.refresh(row)
    assert row.wealth == 99999
    farmer = await realm.session.get(CommunityNeedRow, (town.id, SocialClass.FARMER, CommodityKind.MEDICINE))
    assert farmer is not None and farmer.held_pct == 100
    released = await edit_standing(ctx, town.id, SocialClass.OUTCAST, {}, release=["wealth"])
    assert released.locked == []
    with pytest.raises(Exception, match="runs from"):
        await hold_need(ctx, town.id, SocialClass.FARMER, CommodityKind.MEDICINE, 150)


async def test_class_factions_recruit_from_discontent(realm: Realm) -> None:
    town = await stocked_town(realm)
    society = await realm.session.get(CommunitySocietyRow, town.id)
    assert society is not None
    society.satisfaction_merchant = 5
    guild = await make(
        realm.session,
        "Ashford Guild",
        EntityType.FACTION,
        FactionStats(strength=30, wealth=30, sway=30),
        world_id=realm.world.id,
        engine_kind=EngineKind.MERCHANT_GUILD,
        affiliated_entity_id=town.id,
    )
    assert await recruit(context(realm.session)) >= 1
    assert (stat(guild, "strength") or 0) > 30


async def test_backfill_fills_wealth_and_needs_once(realm: Realm) -> None:
    town = await stocked_town(realm)
    ctx = context(realm.session)
    await goods_of(realm.session, ctx.epoch).add(town.id, CommodityKind.LUXURIES, 500, GoodsFlow.SEED)
    result = await society_depth_backfill(ctx, [town])
    assert result["communities"] == 1
    rows = list(await realm.session.scalars(select(ClassStandingRow).where(ClassStandingRow.community_entity_id == town.id)))
    assert any(row.wealth > 0 for row in rows)
    assert await society_depth_backfill(ctx, [town]) == {}


async def test_impositions_feed_the_drift_and_staples_come_from_culture(realm: Realm) -> None:
    folk = await people(realm, "Plainsfolk")
    ctx = context(realm.session)
    row = await impose_drift(ctx, folk.id, DriftCause.WAR_LOST, ValueAxis.MARTIAL, amount=10, epochs=2)
    found = await impositions_of(realm.session, folk.id)
    assert [item.id for item in found] == [row.id]
    await spend_impositions(realm.session, found)
    assert row.epochs_left == 1
    await spend_impositions(realm.session, found)
    await realm.session.flush()
    assert await impositions_of(realm.session, folk.id) == []
    realm.session.add(
        PeopleCultureRow(
            people_entity_id=folk.id,
            cohesion=80,
            literacy=0,
            urbanisation=0,
            staples=["fish"],
            aesthetic=Aesthetic.AUSTERE,
            martial_style=MartialStyle.SHIELDWALL,
            marriage=MarriageCustom.MONOGAMY,
            inheritance=InheritanceCustom.GAVELKIND,
            locked=[],
        )
    )
    await realm.session.flush()
    assert await staples_of(realm.session, folk) == (CommodityKind.FISH,)


async def test_member_loyalty_counts_grievances_benefits_and_satisfaction(realm: Realm) -> None:
    town = await stocked_town(realm)
    crown = await make(realm.session, "Crown", EntityType.POLITY, PolityStats(legitimacy=50, stability=50), world_id=realm.world.id)
    profile = PolityProfileRow(polity_entity_id=crown.id, government=next(iter(GovernmentKind)), decision_rule=next(iter(DecisionRule)), war_weariness=40)
    member = PolityMemberRow(polity_entity_id=crown.id, member_entity_id=town.id, autonomy=0)
    realm.session.add(member)
    await realm.session.flush()
    ctx = context(realm.session)
    held = Holding(crown, profile, {town.id: member})
    row = await member_loyalty(ctx, held, town, 2)
    assert row.parts[LoyaltyPart.WEARINESS.value] > 0 and row.parts[LoyaltyPart.VICTORIES.value] == 2 * ctx.rules.realm_loyalty.victory_benefit
    assert row.grievances > 0 and row.benefits > 0
    calm = row.loyalty
    society = await realm.session.get(CommunitySocietyRow, town.id)
    assert society is not None
    for social_class in SocialClass:
        setattr(society, f"satisfaction_{social_class.value}", 5)
    assert (await member_loyalty(ctx, held, town, 2)).loyalty < calm
    row.locked = ["loyalty"]
    row.loyalty = 90
    assert (await member_loyalty(ctx, held, town, 0)).loyalty == 90
