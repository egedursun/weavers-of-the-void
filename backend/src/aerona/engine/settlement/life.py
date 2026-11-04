from sqlalchemy import func, select

from aerona.catalog.laws import PENALTY_HARM
from aerona.constants.units import PERCENT
from aerona.db.tables.demography import CohortRow, LabourRow, PeopleCultureRow
from aerona.db.tables.disease import QuarantineRow
from aerona.db.tables.economy import TradeFlowRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.mind import CultureValueRow
from aerona.db.tables.settlement import DistrictRow, SettlementHistoryRow, SettlementTreasuryRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import ArmyRow, SiegeRow
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.demography import AgeBand, Job
from aerona.domain.enums.disease import SpreadPath
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.settlement import TIER_ORDER, WATER_ORDER, BuildMaterial, DistrictKind, SizeTier, TreasuryEntry, WaterSupply
from aerona.domain.enums.society import Commodity, KnowledgeBranch, SocialClass
from aerona.domain.enums.war import SiegeStatus
from aerona.engine.body.customs import culture_of, people_of
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.demography.cohorts import cohorts_of
from aerona.engine.demography.mobility import bound_revolt, inequality_pressure
from aerona.engine.economy.route_dangers import BANDIT_KINDS
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.lore.research import lacks
from aerona.engine.military.occupation import occupation_over, occupation_tax, pay_occupier
from aerona.engine.mind.drives import unrest as needs_unrest
from aerona.engine.mind.space import value_distance
from aerona.engine.notes import note
from aerona.engine.phases.disasters import strike_plague
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds, add_flag, living_entity
from aerona.engine.primitives.society import supply_index
from aerona.engine.primitives.stats import headcount_bounds, set_stats, shift_stat, stat
from aerona.engine.settlement.book import Town, ledger, tier_for
from aerona.rules.registry import Rules

FOOD_INDEX = 100
DAYS = 365
SIEGE_DISEASE = 50
DRY_OFF_PCT = 30
HALF = 2
WORK_LOCKS = {"cistern": "water", "aqueduct": "water", "walls": "walls_level"}


def granary_of(rules: Rules, town: Town) -> int:
    return (town.levels(DistrictKind.FARMLAND) + town.levels(DistrictKind.MARKET)) * rules.urban.granary_per_level


def housing_of(rules: Rules, town: Town) -> int:
    table = rules.urban
    return (town.tier_index() + 1) * table.housing_base + sum(district.level for district in town.districts) * table.housing_per_level


def slots_of(rules: Rules, town: Town) -> int:
    return 1 + town.tier_index() * rules.urban.district_slots_per_tier


async def labour(ctx: TickContext, town: Town, *jobs: Job) -> int:
    rows = await ctx.session.scalars(select(LabourRow).where(LabourRow.community_entity_id == town.entity.id, LabourRow.job.in_(list(jobs))))
    return sum(round_half_up(row.workers * row.output_pct / PERCENT) for row in rows)


async def capacities(ctx: TickContext, town: Town, knowledge: KnowledgeMap) -> None:
    table = ctx.rules.urban
    builders = await labour(ctx, town, Job.BUILDING)
    haulers = await labour(ctx, town, Job.TRADE, Job.BUILDING)
    architecture = knowledge.level(town.entity.id, KnowledgeBranch.ARCHITECTURE)
    town.profile.construction_capacity = round_half_up(builders * table.builder_capacity * (1 + architecture * table.engineering_capacity_pct / PERCENT))
    town.profile.hauling_capacity = round_half_up(haulers * table.hauler_capacity * (1 + town.infrastructure.roads * table.road_hauling_pct / PERCENT))


def logistics_waste(rules: Rules, town: Town) -> float:
    people = stat(town.entity, "population") or 0
    if people <= 0:
        return 0.0
    reach = min(1.0, town.profile.hauling_capacity * PERCENT / max(1, people))
    return rules.urban.waste_pct / PERCENT * (1 - reach) * town.tier_index() / (len(TIER_ORDER) - 1)


async def invest(ctx: TickContext, town: Town) -> int:
    sold = await ctx.session.scalar(
        select(func.coalesce(func.sum(TradeFlowRow.value), 0)).where(TradeFlowRow.from_entity_id == town.entity.id, TradeFlowRow.epoch == ctx.epoch)
    )
    profit = round_half_up(int(sold or 0) * ctx.rules.urban.investment_pct / PERCENT)
    town.profile.investment_pool += profit
    return profit


async def collect_taxes(ctx: TickContext, town: Town, literacy: int) -> int:
    table = ctx.rules.taxation
    people = stat(town.entity, "population") or 0
    wealth = stat(town.entity, "wealth") or stat(town.entity, "prosperity") or 0
    taxable = people / PERCENT * table.per_capita_output * max(0.1, wealth / PERCENT) * (1 - logistics_waste(ctx.rules, town))
    admin = (table.admin_base_pct + literacy * table.admin_per_literacy_pct / PERCENT) / PERCENT
    rate = town.profile.tax_rate / PERCENT * (ctx.rules.urban.free_city_tax_pct / PERCENT if town.profile.free_city else 1.0)
    income = round_half_up(taxable * rate * town.profile.public_order / PERCENT * admin)
    occupation = await occupation_over(ctx, town.entity.id)
    taken = occupation_tax(ctx, income, occupation)
    if taken and occupation is not None:
        await pay_occupier(ctx, occupation.occupier_entity_id, taken)
    return ledger(ctx, town, TreasuryEntry.TAX, income - taken, "taxes")


async def pay_soldiers(ctx: TickContext, town: Town) -> bool:
    table = ctx.rules.urban
    society = await ctx.session.get(CommunitySocietyRow, town.entity.id)
    warriors = society.share(SocialClass.WARRIOR) if society is not None else 0
    town.profile.militia = round_half_up((stat(town.entity, "population") or 0) * warriors / PERCENT * table.militia_pct / PERCENT)
    garrison = await ctx.session.scalar(
        select(ArmyRow.entity_id)
        .join(EntityFlagRow, EntityFlagRow.entity_id == ArmyRow.entity_id)
        .where(ArmyRow.owner_entity_id == town.entity.id, ArmyRow.disbanded_epoch.is_(None), EntityFlagRow.flag == EntityFlag.ON_WATCH)
        .limit(1)
    )
    town.profile.garrison_entity_id = garrison
    standing = await living_entity(ctx.session, garrison) if garrison is not None else None
    soldiers = town.profile.militia + ((stat(standing, "size") or 0) if standing is not None else 0)
    cost = round_half_up(soldiers / PERCENT * table.garrison_cost_per_100)
    paid = -ledger(ctx, town, TreasuryEntry.GARRISON, -cost, "garrison and militia")
    return paid >= cost


async def keep_walls(ctx: TickContext, town: Town) -> None:
    table = ctx.rules.urban
    walls = town.infrastructure
    if walls.walls_level <= 0:
        return
    walls.walls_condition = max(0, walls.walls_condition - table.walls_decay)
    if walls.walls_condition < PERCENT and -ledger(ctx, town, TreasuryEntry.WALLS, -table.walls_repair_cost, "wall repairs") >= table.walls_repair_cost:
        walls.walls_condition = PERCENT
    floor = round_half_up(walls.walls_level * table.walls_per_level * walls.walls_condition / PERCENT)
    if (stat(town.entity, "defense") or 0) < floor:
        set_stats(town.entity, defense=clamp_int(floor, 0, PERCENT))


async def permitted(ctx: TickContext, town: Town, wants: list[str]) -> list[str]:
    entity = town.entity.id
    walls_cap = 2 if await lacks(ctx.session, entity, Technique.FORTIFICATION) else 3 if await lacks(ctx.session, entity, Technique.FORTRESS) else 5
    barred = {
        want
        for want, technique in (("aqueduct", Technique.AQUEDUCT), ("sewers", Technique.ARCH), ("district:temple_quarter", Technique.DOME))
        if await lacks(ctx.session, entity, technique)
    }
    return [want for want in wants if want not in barred and not (want == "walls" and town.infrastructure.walls_level >= walls_cap)]


def wanted_works(ctx: TickContext, town: Town, knowledge: KnowledgeMap, *, at_war: bool, foreign: int) -> list[str]:
    table = ctx.rules.urban
    people = stat(town.entity, "population") or 0
    architecture = knowledge.level(town.entity.id, KnowledgeBranch.ARCHITECTURE)
    infrastructure = town.infrastructure
    wants: list[str] = [f"repair:{district.id}" for district in town.districts if district.condition < PERCENT // HALF]
    if people >= table.town_population and infrastructure.roads < 1:
        wants.append("roads")
    if (
        people >= table.city_population // HALF
        and WATER_ORDER.index(infrastructure.water) < WATER_ORDER.index(WaterSupply.CISTERN)
        and architecture >= table.cistern_level
    ):
        wants.append("cistern")
    if people >= table.metropolis_population // HALF and infrastructure.water is not WaterSupply.AQUEDUCT and architecture >= table.aqueduct_level:
        wants.append("aqueduct")
    if people >= table.city_population and not infrastructure.sewers and architecture >= table.sewer_level:
        wants.append("sewers")
    if at_war and infrastructure.walls_level < min(5, town.tier_index() + 1):
        wants.append("walls")
    kinds = {district.kind for district in town.districts}
    needs: list[DistrictKind] = []
    if granary_of(ctx.rules, town) <= 0 or (people >= table.city_population and DistrictKind.MARKET not in kinds):
        needs.append(DistrictKind.MARKET if DistrictKind.FARMLAND in kinds else DistrictKind.FARMLAND)
    if foreign >= table.foreign_quarter_pct and DistrictKind.FOREIGN_QUARTER not in kinds:
        needs.append(DistrictKind.FOREIGN_QUARTER)
    if at_war and DistrictKind.CITADEL not in kinds:
        needs.append(DistrictKind.CITADEL)
    if (stat(town.entity, "piety") or 0) >= PERCENT // HALF and DistrictKind.TEMPLE_QUARTER not in kinds:
        needs.append(DistrictKind.TEMPLE_QUARTER)
    if DistrictKind.CRAFT_QUARTER not in kinds and town.tier_index() >= 1:
        needs.append(DistrictKind.CRAFT_QUARTER)
    if town.tier_index() >= TIER_ORDER.index(SizeTier.CITY) and DistrictKind.NECROPOLIS not in kinds:
        needs.append(DistrictKind.NECROPOLIS)
    wants.extend(f"district:{kind.value}" for kind in needs)
    if people > housing_of(ctx.rules, town):
        wants.append("district:market" if DistrictKind.MARKET in kinds else "district:craft_quarter")
    return wants


def spend(ctx: TickContext, town: Town, cost: int, work: int, label: str) -> bool:
    profile = town.profile
    if profile.construction_capacity < work or profile.investment_pool + profile.treasury < cost:
        return False
    from_pool = min(profile.investment_pool, cost)
    profile.investment_pool -= from_pool
    if cost - from_pool:
        ledger(ctx, town, TreasuryEntry.BUILDING, -(cost - from_pool), label)
    if from_pool:
        ctx.session.add(
            SettlementTreasuryRow(
                settlement_entity_id=town.entity.id,
                epoch=ctx.epoch,
                entry=TreasuryEntry.INVESTMENT,
                amount=-from_pool,
                balance=profile.treasury,
                note=label[:120],
            )
        )
    profile.construction_capacity -= work
    gain = round_half_up(cost / max(1, ctx.rules.taxation.wealth_per_treasury))
    shift_stat(town.entity, "wealth", gain, ctx.rules.society.default_stat)
    return True


async def add_district(
    ctx: TickContext, town: Town, kind: DistrictKind, *, material: BuildMaterial, son_id: int | None = None, builder_id: int | None = None
) -> DistrictRow:
    same = next((district for district in town.districts if district.kind is kind and district.level < 5), None)
    if same is not None and (kind is not DistrictKind.SLUMS or same.level < 5):
        same.level += 1
        same.condition = PERCENT
        return same
    district = DistrictRow(
        settlement_entity_id=town.entity.id,
        kind=kind,
        level=1,
        condition=PERCENT,
        material=material,
        built_epoch=ctx.epoch,
        built_by_entity_id=builder_id,
        built_by_son_id=son_id,
    )
    ctx.session.add(district)
    town.districts.append(district)
    return district


def improve(rules: Rules, town: Town, kind: str, material: BuildMaterial) -> None:
    infrastructure = town.infrastructure
    if WORK_LOCKS.get(kind, kind) in infrastructure.locked:
        return
    if kind == "roads":
        infrastructure.roads = min(5, infrastructure.roads + 1)
    elif kind == "cistern":
        infrastructure.water = WaterSupply.CISTERN
    elif kind == "aqueduct":
        infrastructure.water = WaterSupply.AQUEDUCT
    elif kind == "sewers":
        infrastructure.sewers = True
    elif kind == "walls":
        infrastructure.walls_level = min(5, infrastructure.walls_level + 1)
        infrastructure.walls_material = material
        infrastructure.walls_condition = PERCENT
        infrastructure.gates = max(1, infrastructure.gates)
        infrastructure.towers = min(20, infrastructure.towers + 2)
        shift_stat(town.entity, "defense", rules.urban.walls_per_level, 0)


async def build(ctx: TickContext, town: Town, knowledge: KnowledgeMap, *, at_war: bool, foreign: int) -> int:
    table = ctx.rules.urban
    architecture = knowledge.level(town.entity.id, KnowledgeBranch.ARCHITECTURE)
    material = BuildMaterial.STONE if architecture >= ctx.rules.fire.stone_level else BuildMaterial.TIMBER
    built = 0
    for want in await permitted(ctx, town, wanted_works(ctx, town, knowledge, at_war=at_war, foreign=foreign)):
        kind, _, detail = want.partition(":")
        if kind == "repair":
            district = next((item for item in town.districts if str(item.id) == detail), None)
            if district is not None and spend(ctx, town, table.repair_cost, table.district_labour // 4, "repairs"):
                district.condition = PERCENT
                built += 1
            continue
        if kind == "district":
            used = len(town.districts)
            district_kind = DistrictKind(detail)
            if used >= slots_of(ctx.rules, town) and not any(item.kind is district_kind and item.level < 5 for item in town.districts):
                continue
            if spend(ctx, town, table.district_cost, table.district_labour, f"{district_kind.value} district"):
                await add_district(ctx, town, district_kind, material=material, builder_id=town.entity.id)
                built += 1
            continue
        if spend(ctx, town, table.district_cost, table.district_labour, kind):
            improve(ctx.rules, town, kind, material)
            built += 1
    people = stat(town.entity, "population") or 0
    if people > housing_of(ctx.rules, town):
        await add_district(ctx, town, DistrictKind.SLUMS, material=BuildMaterial.TIMBER)
    town.infrastructure.granary_capacity = granary_of(ctx.rules, town)
    town.infrastructure.harbour_capacity = town.levels(DistrictKind.HARBOUR) * table.harbour_per_level
    town.infrastructure.warehouse_capacity = (town.levels(DistrictKind.MARKET) + town.levels(DistrictKind.CRAFT_QUARTER)) * table.harbour_per_level
    return built


async def wear(ctx: TickContext, town: Town) -> None:
    for district in town.districts:
        district.condition = max(0, district.condition - ctx.rules.urban.district_wear)


def outcast_share(society: CommunitySocietyRow | None) -> float:
    return society.share(SocialClass.OUTCAST) / PERCENT if society is not None else 0.0


async def bandits_near(ctx: TickContext, atlas: RegionAtlas, town: Town) -> list[EntityRow]:
    home = atlas.top_region(town.entity.id)
    if home is None:
        return []
    near = {home, *atlas.neighbour_regions(home)}
    found = await ctx.session.scalars(
        select(EntityRow).where(
            EntityRow.entity_type == EntityType.FACTION, EntityRow.status == EntityStatus.CANON, EntityRow.engine_kind.in_(list(BANDIT_KINDS))
        )
    )
    return [band for band in found if atlas.top_region(band.id) in near]


async def keep_order(ctx: TickContext, town: Town, *, justice: float, bands: list[EntityRow], hierarchy: int) -> None:
    table = ctx.rules.crime
    profile = town.profile
    society = await ctx.session.get(CommunitySocietyRow, town.entity.id)
    garrison = await living_entity(ctx.session, profile.garrison_entity_id) if profile.garrison_entity_id is not None else None
    soldiers = profile.militia + ((stat(garrison, "size") or 0) if garrison is not None else 0)
    policing = soldiers / PERCENT * table.policing_per_100 + town.levels(DistrictKind.CITADEL) * table.citadel_policing
    wealth = stat(town.entity, "wealth") or stat(town.entity, "prosperity") or 0
    if "public_order" not in profile.locked:
        charter = ctx.rules.urban.charter_order if profile.charter_entity_id is not None else 0
        profile.public_order = clamp_int(table.order_base + soldiers / PERCENT * table.order_per_100 + charter - profile.crime / HALF, 0, PERCENT)
    if "crime" not in profile.locked:
        crime = (
            (PERCENT - wealth) * table.poverty_pct / PERCENT
            + outcast_share(society) * PERCENT * table.outcast_pct / PERCENT
            + inequality_pressure(ctx.rules, society, hierarchy)
            + (PERCENT - profile.public_order) * table.disorder_pct / PERCENT
            + len(bands) * table.bandit_crime
            - policing
            - justice * table.justice_pct
        )
        profile.crime = clamp_int(crime, 0, PERCENT)
    shift_stat(town.entity, "prosperity", -profile.crime * table.prosperity_loss / PERCENT, ctx.rules.society.default_stat)
    for band in bands:
        shift_stat(band, "strength", profile.crime * table.bandit_feed_pct / PERCENT / max(1, len(bands)), ctx.rules.society.default_stat)


async def punish(ctx: TickContext, town: Town) -> bool:
    table = ctx.rules.crime
    if not ctx.rng(f"punish.{town.entity.id}").chance(table.punishment_chance * town.profile.crime / PERCENT):
        return False
    culprits = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.location_id == town.entity.id)
        .order_by(EntityRow.id)
    )
    candidates = [
        mortal for mortal in culprits if mortal.social_class is SocialClass.OUTCAST or (mortal.subtype or "").lower() in {"bandit", "thief", "outlaw"}
    ]
    if not candidates:
        return False
    culprit = ctx.rng(f"culprit.{town.entity.id}").pick(candidates)
    penalty = await law_param(ctx.session, town.entity.id, LawKind.PENAL_CODE, "theft")
    if penalty == "exile":
        culprit.location_id = None
        await add_flag(ctx.session, culprit.id, EntityFlag.EXILE, ctx.epoch)
        return True
    hp = PENALTY_HARM.get(str(penalty), table.punishment_hp) if penalty is not None else table.punishment_hp
    if hp <= 0:
        return True
    await apply_hits(ctx, culprit, Harm(hp, HarmCause.PUNISHMENT, f"punished by the watch of {town.entity.name}"))
    return True


async def quarantined(ctx: TickContext, region: int | None) -> bool:
    row = await ctx.session.get(QuarantineRow, region) if region is not None else None
    return row is not None and row.until_epoch >= ctx.epoch


async def stir_unrest(ctx: TickContext, town: Town, *, tension: int, festival: bool, region: int | None) -> None:
    table = ctx.rules.crime
    taxation = ctx.rules.taxation
    profile = town.profile
    if "unrest" in profile.locked:
        return
    food = await supply_index(ctx.session, town.entity.id, Commodity.FOOD)
    hunger = max(0.0, 1 - food / FOOD_INDEX) if food is not None else 0.0
    rows = await cohorts_of(ctx.session, town.entity.id)
    pressure = await needs_unrest(ctx.session, ctx.rules, town.entity.id)
    unrest = (
        profile.unrest * (1 - table.unrest_decay / PERCENT)
        + profile.tax_rate * taxation.unrest_per_tax / PERCENT
        + profile.crime * table.crime_unrest_pct / PERCENT
        + hunger * table.hunger_unrest
        + pressure / 4
        + bound_revolt(ctx.rules, rows)
        + tension
        + (ctx.rules.urban.ration_unrest if profile.rationing else 0)
        + (ctx.rules.epidemiology.quarantine_unrest if await quarantined(ctx, region) else 0)
        - (taxation.festival_relief if festival else 0)
    )
    profile.unrest = clamp_int(unrest, 0, PERCENT)


def festivals_and_alms(ctx: TickContext, town: Town, society: CommunitySocietyRow | None) -> bool:
    taxation = ctx.rules.taxation
    festival = False
    if (
        town.profile.unrest >= taxation.festival_unrest
        and -ledger(ctx, town, TreasuryEntry.FESTIVAL, -taxation.festival_cost, "festival") >= taxation.festival_cost
    ):
        festival = True
    if (
        outcast_share(society) * PERCENT >= taxation.alms_outcast_pct
        and -ledger(ctx, town, TreasuryEntry.ALMS, -taxation.alms_cost, "alms") >= taxation.alms_cost
    ):
        town.profile.crime = max(0, town.profile.crime - taxation.alms_crime)
    return festival


async def fires(ctx: TickContext, town: Town, ground: RegionEnvironmentRow | None, knowledge: KnowledgeMap) -> int:
    table = ctx.rules.fire
    people = stat(town.entity, "population") or 0
    crowd = min(1.0, people / max(1, housing_of(ctx.rules, town)))
    town.profile.fire_risk = clamp_int(town.timber_share() * table.timber_risk + crowd * table.crowding_risk, 0, PERCENT)
    dry = 1.0 if ground is None or ground.rainfall < table.dry_rainfall else DRY_OFF_PCT / PERCENT
    rng = ctx.rng(f"fire.{town.entity.id}")
    burned = 0
    for _ in range(ctx.rules.demography.sampled_years):
        if not rng.chance(table.chance_pct * town.profile.fire_risk / PERCENT * dry):
            continue
        timber = [district for district in town.districts if district.material is BuildMaterial.TIMBER] or town.districts
        if not timber:
            continue
        district = max(timber, key=lambda item: (item.level, -item.id))
        district.condition = max(0, district.condition - table.district_loss)
        if district.condition == 0:
            district.level -= 1
            district.condition = PERCENT // HALF
            if knowledge.level(town.entity.id, KnowledgeBranch.ARCHITECTURE) >= table.stone_level:
                district.material = BuildMaterial.STONE
            if district.level <= 0:
                await ctx.session.delete(district)
                town.districts.remove(district)
        floor, _ = headcount_bounds(ctx.rules, town.entity)
        before = stat(town.entity, "population") or 0
        dead = min(max(0, before - floor), round_half_up(before * table.death_pct / PERCENT))
        with flowing(FlowCategory.DISASTER):
            set_stats(town.entity, population=before - dead)
        ledger(ctx, town, TreasuryEntry.FIRE, -table.treasury_loss, "great fire")
        burned += 1
        await note(
            ctx,
            f"A great fire swept through the {district.kind.value.replace('_', ' ')} of {town.entity.name}; {dead} died in the flames.",
            key="settlement.fire",
            ids=[town.entity.id],
            feed=FeedCategory.DISASTER,
            kind=ChronicleKind.WORLD,
        )
    return burned


def sanitation(ctx: TickContext, town: Town, knowledge: KnowledgeMap) -> None:
    table = ctx.rules.sanitation
    if "sanitation" in town.profile.locked:
        return
    infrastructure = town.infrastructure
    water = {WaterSupply.NONE: -table.base, WaterSupply.WELL: 0, WaterSupply.CISTERN: table.cistern, WaterSupply.AQUEDUCT: table.cistern + table.aqueduct}[
        infrastructure.water
    ]
    people = stat(town.entity, "population") or 0
    crowd = max(0.0, people / max(1, housing_of(ctx.rules, town)) - 1)
    value = (
        table.base
        + water
        + (table.sewers if infrastructure.sewers else 0)
        + knowledge.level(town.entity.id, KnowledgeBranch.MEDICINE) * table.medicine_step
        - town.levels(DistrictKind.SLUMS) * table.slum_loss
        - min(1.0, crowd) * table.crowding_loss
    )
    town.profile.sanitation = clamp_int(value, 0, PERCENT)


async def endure_siege(ctx: TickContext, town: Town, values: dict[ValueAxis, int]) -> None:
    table = ctx.rules.sanitation
    urban = ctx.rules.urban
    profile = town.profile
    siege = await ctx.session.scalar(
        select(SiegeRow).where(SiegeRow.besieged_entity_id == town.entity.id, SiegeRow.status == SiegeStatus.ONGOING).order_by(SiegeRow.id).limit(1)
    )
    food = await supply_index(ctx.session, town.entity.id, Commodity.FOOD) or 0
    stored = min(1.0, food / FOOD_INDEX) * (1.0 if town.infrastructure.granary_capacity > 0 else 0.5)
    profile.siege_supplies = round_half_up(stored * table.siege_food_days)
    water = {
        WaterSupply.NONE: 0,
        WaterSupply.WELL: table.siege_water_days // 3,
        WaterSupply.CISTERN: table.siege_water_days,
        WaterSupply.AQUEDUCT: table.siege_water_days,
    }
    profile.siege_water = water[town.infrastructure.water]
    if siege is None:
        profile.siege_disease = 0
        profile.rationing = profile.siege_supplies < urban.ration_supplies_days and food < FOOD_INDEX // HALF
    else:
        profile.siege_disease = clamp_int(profile.siege_disease + table.siege_disease_step * (1 - profile.sanitation / PERCENT), 0, PERCENT)
        profile.rationing = profile.siege_supplies < urban.ration_supplies_days or profile.siege_water < urban.ration_supplies_days // HALF
        if profile.siege_disease >= SIEGE_DISEASE and ctx.rng(f"siege_disease.{town.entity.id}").chance(profile.siege_disease):
            await strike_plague(ctx, town.entity, profile.siege_disease, path=SpreadPath.SIEGE)
            profile.siege_disease //= HALF
    if profile.rationing and values.get(ValueAxis.MERCY, 0) <= urban.abandon_mercy:
        await abandon_elders(ctx, town)


async def abandon_elders(ctx: TickContext, town: Town) -> None:
    rows = await ctx.session.scalars(select(CohortRow).where(CohortRow.community_entity_id == town.entity.id, CohortRow.age_band == AgeBand.ELDER))
    lost = 0
    for row in rows:
        part = round_half_up(row.count * ctx.rules.urban.abandon_pct / PERCENT)
        lost += part
    if lost <= 0:
        return
    floor, _ = headcount_bounds(ctx.rules, town.entity)
    before = stat(town.entity, "population") or 0
    lost = min(lost, max(0, before - floor))
    with flowing(FlowCategory.FAMINE):
        set_stats(town.entity, population=before - lost)
    await note(
        ctx,
        f"With the stores empty, {town.entity.name} left {lost} of its old and sick outside the walls; the choice will be remembered.",
        key="settlement.abandoned",
        ids=[town.entity.id],
        kind=ChronicleKind.WORLD,
    )


async def foreigners(ctx: TickContext, town: Town) -> int:
    home = await people_of(ctx.session, town.entity)
    shares: dict[str, int] = {}
    total = 0
    for bond in await active_bonds(ctx.session, [BondKind.LIVES_IN], targets=[town.entity.id]):
        people = await living_entity(ctx.session, bond.source_node_id)
        if people is None or people.entity_type is not EntityType.PEOPLE or (home is not None and people.id == home.id) or bond.role is BondRole.HOMELAND:
            continue
        weight = max(1, (stat(people, "population") or 0) // 20)
        shares[str(people.id)] = weight
        total += weight
    population = stat(town.entity, "population") or 1
    town.profile.foreigners = {key: clamp_int(value * PERCENT / max(population, total * 5), 0, PERCENT) for key, value in shares.items()}
    return sum(town.profile.foreigners.values())


async def prestige(ctx: TickContext, town: Town) -> None:
    table = ctx.rules.urban
    if "prestige" in town.profile.locked:
        return
    local = await ctx.session.scalars(select(EntityRow).where(EntityRow.location_id == town.entity.id, EntityRow.status == EntityStatus.CANON))
    splendour = artworks = renowned = 0
    for item in local:
        if item.entity_type is EntityType.STRUCTURE:
            splendour += stat(item, "splendor") or 0
        elif item.entity_type is EntityType.ARTWORK:
            artworks += 1
        elif item.entity_type is EntityType.MORTAL and (item.importance or 0) >= table.renown_bar:
            renowned += 1
    value = splendour / PERCENT * table.prestige_per_splendor + artworks * table.prestige_per_artwork + renowned * table.prestige_per_renown
    town.profile.prestige = clamp_int(value, 0, PERCENT)


async def urban_drift(ctx: TickContext, town: Town) -> int:
    table = ctx.rules.urban
    if town.tier_index() + 1 < table.drift_tier:
        return 0
    people = await people_of(ctx.session, town.entity)
    parent = await culture_of(ctx.session, people.id) if people is not None else {}
    rows = {row.axis: row for row in await ctx.session.scalars(select(CultureValueRow).where(CultureValueRow.entity_id == town.entity.id))}
    if not rows:
        for axis, value in parent.items():
            seeded = CultureValueRow(entity_id=town.entity.id, axis=axis, value=value)
            ctx.session.add(seeded)
            rows[axis] = seeded
    for axis, step in ((ValueAxis.XENOPHILIA, table.drift_step), (ValueAxis.TRADITION, -table.drift_step)):
        row = rows.get(axis)
        if row is None:
            row = CultureValueRow(entity_id=town.entity.id, axis=axis, value=parent.get(axis, 0))
            ctx.session.add(row)
            rows[axis] = row
        row.value = clamp_int(row.value + step, -PERCENT, PERCENT)
    own = {axis: row.value for axis, row in rows.items()}
    return clamp_int(value_distance(own, parent) * table.tension_pct / PERCENT, 0, PERCENT) if parent else 0


def retier(ctx: TickContext, town: Town) -> SizeTier | None:
    if "size_tier" in town.profile.locked:
        return None
    people = stat(town.entity, "population") or 0
    tier = tier_for(ctx.rules, people, town.infrastructure, town.infrastructure.granary_capacity)
    if tier is town.profile.size_tier:
        return None
    town.profile.size_tier = tier
    return tier


def remember(ctx: TickContext, town: Town) -> None:
    profile = town.profile
    ctx.session.add(
        SettlementHistoryRow(
            settlement_entity_id=town.entity.id,
            epoch=ctx.epoch,
            size_tier=profile.size_tier,
            public_order=profile.public_order,
            crime=profile.crime,
            unrest=profile.unrest,
            sanitation=profile.sanitation,
            wealth=stat(town.entity, "wealth") or 0,
            treasury=profile.treasury,
            population=stat(town.entity, "population") or 0,
        )
    )


async def literacy_of(ctx: TickContext, town: Town) -> int:
    people = await people_of(ctx.session, town.entity)
    culture = await ctx.session.get(PeopleCultureRow, people.id) if people is not None else None
    return culture.literacy if culture is not None else 0
