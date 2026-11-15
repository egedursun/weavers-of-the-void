from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.catalog.materials import BUILD_MATERIALS, MATERIALS
from aerona.catalog.urban import QUARTER_WORKS
from aerona.catalog.zones import CIVIC_SERVICE_OF
from aerona.constants.units import PERCENT
from aerona.db.tables.communication import PublicOpinionRow
from aerona.db.tables.demography import CohortRow, LabourRow, PeopleCultureRow
from aerona.db.tables.disease import QuarantineRow
from aerona.db.tables.economy import TradeFlowRow, WorkshopRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow, WorldSeasonRow
from aerona.db.tables.mind import CultureValueRow
from aerona.db.tables.settlement import (
    ADMIN_MAX,
    DistrictRow,
    SettlementHistoryRow,
    SettlementInfrastructureRow,
    SettlementProfileRow,
    SettlementTreasuryRow,
)
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.tables.warfare import ArmyRow, SiegeRow
from aerona.domain.enums.agrarian import RebuildCause
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.demography import AgeBand, Job
from aerona.domain.enums.disease import SpreadPath
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.dominion import DivineScale
from aerona.domain.enums.economy import WorkshopKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.environment import RiverClass, WeatherEffect
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.settlement import TIER_ORDER, WATER_ORDER, BuildMaterial, DistrictKind, SizeTier, TreasuryEntry, WaterSupply
from aerona.domain.enums.society import Commodity, KnowledgeBranch, SocialClass
from aerona.domain.enums.structure import ConstructionState, StructureKind
from aerona.domain.enums.urban import HousingLevel, Morphology, UrbanService
from aerona.domain.enums.war import SiegeStatus
from aerona.engine.agrarian.book import centrality_of, counted_people, shield_of
from aerona.engine.agrarian.ruin import mark_ruin
from aerona.engine.body.customs import culture_of, people_of
from aerona.engine.context import TickContext
from aerona.engine.cosmos.world_views import view_of
from aerona.engine.demography.cohorts import cohorts_of
from aerona.engine.demography.mobility import bound_revolt, inequality_pressure
from aerona.engine.divine.hooks import foe_pct
from aerona.engine.dominion.effects import scale_here
from aerona.engine.economy.stocks import aggregate_need
from aerona.engine.environment.book import EnvironmentBook
from aerona.engine.environment.years import world_years
from aerona.engine.factions.book import robber_ids
from aerona.engine.factions.estates import armed_share, exempt_share
from aerona.engine.happenings.emergence import record_fire
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.lore.research import lacks
from aerona.engine.means.building import burn_structures
from aerona.engine.means.media import burn_works
from aerona.engine.military.occupation import occupation_over, occupation_tax, pay_occupier
from aerona.engine.mind.drives import unrest as needs_unrest
from aerona.engine.mind.space import value_distance
from aerona.engine.notes import note
from aerona.engine.phases.disasters import strike_plague
from aerona.engine.polity.laws import LawBook, law_param
from aerona.engine.polity.trials import judge_for, open_case
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds, living_entity
from aerona.engine.primitives.society import supply_index
from aerona.engine.primitives.stats import headcount_bounds, set_stats, shift_stat, stat
from aerona.engine.renown.currencies import realm_of_community, ruler_of_realm
from aerona.engine.settlement.book import Town, ledger, tier_for
from aerona.engine.settlement.districts import AdminParts, admin_parts, designs_for, unify_market, wound_district
from aerona.engine.settlement.storage import design_for, settlement_store, storage_index, store_kind
from aerona.engine.urban.morphology import hauling_of, replan, spread_of
from aerona.engine.urban.planning import seat
from aerona.rules.registry import Rules

FOOD_INDEX = 100
SIEGE_DISEASE = 50
DRY_OFF_PCT = 30
HALF = 2
WORK_LOCKS = {"cistern": "water", "aqueduct": "water", "walls": "walls_level"}


def granary_of(rules: Rules, town: Town) -> int:
    return town.effects(rules).food_store


def housing_of(rules: Rules, town: Town) -> int:
    table = rules.urban
    return (town.tier_index() + 1) * table.housing_base + town.effects(rules).housing + town.habitat


def slots_of(rules: Rules, town: Town) -> int:
    return 1 + town.tier_index() * rules.urban.district_slots_per_tier


async def weapons_crime(ctx: TickContext, town_id: int) -> int:
    level = await law_param(ctx.session, town_id, LawKind.WEAPONS_LAW, "level")
    if level == "banned":
        return -ctx.rules.crime.weapons_ban
    return ctx.rules.crime.weapons_open if level == "open" else 0


async def labour(ctx: TickContext, town: Town, *jobs: Job) -> int:
    rows = await ctx.session.scalars(select(LabourRow).where(LabourRow.community_entity_id == town.entity.id, LabourRow.job.in_(list(jobs))))
    return sum(round_half_up(row.workers * row.output_pct / PERCENT) for row in rows)


def keep(holder: SettlementProfileRow | SettlementInfrastructureRow, key: str, value: object) -> bool:
    if key in holder.locked:
        return False
    setattr(holder, key, value)
    return True


async def capacities(ctx: TickContext, town: Town, knowledge: KnowledgeMap) -> None:
    table = ctx.rules.urban
    builders = await labour(ctx, town, Job.BUILDING)
    haulers = await labour(ctx, town, Job.TRADE, Job.BUILDING)
    architecture = knowledge.level(town.entity.id, KnowledgeBranch.ARCHITECTURE)
    keep(
        town.profile, "construction_capacity", round_half_up(builders * table.builder_capacity * (1 + architecture * table.engineering_capacity_pct / PERCENT))
    )
    streets = hauling_of(ctx.rules, town.profile.morphology)
    keep(
        town.profile,
        "hauling_capacity",
        round_half_up(haulers * table.hauler_capacity * (1 + town.infrastructure.roads * table.road_hauling_pct / PERCENT) * streets),
    )
    town.work_used = 0


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
    extra = ctx.rules.districts
    foreign = town.effects(ctx.rules).investment_pct
    draw = 1 + (foreign + town.profile.prestige * extra.prestige_investment_pct / PERCENT) / PERCENT
    profit = round_half_up(int(sold or 0) * ctx.rules.urban.investment_pct / PERCENT * draw)
    if "investment_pool" not in town.profile.locked:
        town.profile.investment_pool += profit
    return profit


async def administer(ctx: TickContext, town: Town, knowledge: KnowledgeMap, literacy: int) -> AdminParts:
    society = await ctx.session.get(CommunitySocietyRow, town.entity.id)
    parts = admin_parts(
        ctx.rules,
        literacy=literacy,
        scribe_share=society.share(SocialClass.SCRIBE) if society is not None else 0.0,
        writing=knowledge.level(town.entity.id, KnowledgeBranch.WRITING),
        palace_pct=town.effects(ctx.rules).admin_pct,
    )
    if "admin_capacity" not in town.profile.locked:
        town.profile.admin_capacity = clamp_int(parts.total, 0, ADMIN_MAX)
    return parts


async def collect_taxes(ctx: TickContext, town: Town) -> int:
    table = ctx.rules.taxation
    people = stat(town.entity, "population") or 0
    wealth = stat(town.entity, "prosperity") or 0
    taxable = people / PERCENT * table.per_capita_output * max(0.1, wealth / PERCENT) * (1 - logistics_waste(ctx.rules, town))
    taxable *= 1 - await exempt_share(ctx, town.entity.id)
    admin = town.profile.admin_capacity / PERCENT
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
    armed = warriors + await armed_share(ctx, town.entity.id) * ctx.rules.estates.militia_pct / PERCENT
    keep(town.profile, "militia", round_half_up((stat(town.entity, "population") or 0) * armed / PERCENT * table.militia_pct / PERCENT))
    garrison = await ctx.session.scalar(
        select(ArmyRow.entity_id)
        .join(EntityFlagRow, EntityFlagRow.entity_id == ArmyRow.entity_id)
        .where(ArmyRow.owner_entity_id == town.entity.id, ArmyRow.disbanded_epoch.is_(None), EntityFlagRow.flag == EntityFlag.ON_WATCH)
        .limit(1)
    )
    keep(town.profile, "garrison_entity_id", garrison)
    garrison = town.profile.garrison_entity_id
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
    if "walls_condition" not in walls.locked:
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


@dataclass(frozen=True)
class Waterside:
    river: RiverClass = RiverClass.NONE
    irrigators: bool = False


def water_works(ctx: TickContext, town: Town, architecture: int, waterside: Waterside) -> list[str]:
    table = ctx.rules.urban
    people = stat(town.entity, "population") or 0
    infrastructure = town.infrastructure
    wants: list[str] = []
    if waterside.river is RiverClass.NONE:
        return wants
    if people >= table.bridge_population and architecture >= table.bridge_level and infrastructure.bridges < table.works_cap:
        wants.append("bridges")
    farming = any(district.kind is DistrictKind.FARMLAND for district in town.districts)
    if waterside.irrigators and farming and people >= table.irrigation_population and infrastructure.irrigation < table.works_cap:
        wants.append("irrigation")
    return wants


def wanted_works(ctx: TickContext, town: Town, knowledge: KnowledgeMap, *, at_war: bool, foreign: int, waterside: Waterside | None = None) -> list[str]:
    table = ctx.rules.urban
    people = stat(town.entity, "population") or 0
    architecture = knowledge.level(town.entity.id, KnowledgeBranch.ARCHITECTURE)
    infrastructure = town.infrastructure
    wants: list[str] = [f"repair:{district.id}" for district in town.districts if district.condition < PERCENT // HALF]
    if people >= table.town_population and infrastructure.roads < 1:
        wants.append("roads")
    wants.extend(water_works(ctx, town, architecture, waterside or Waterside()))
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
        wants.append("district:residential")
    return wants


async def quarter_wants(ctx: TickContext, town: Town) -> list[str]:
    table = ctx.rules.city_plan
    kinds = {district.kind for district in town.districts}
    built = list(
        await ctx.session.scalars(
            select(StructureProfileRow.kind).where(
                StructureProfileRow.host_entity_id == town.entity.id, StructureProfileRow.construction_state == ConstructionState.COMPLETE
            )
        )
    )
    wants: list[str] = []
    if DistrictKind.CIVIC_QUARTER not in kinds and sum(1 for kind in built if kind in CIVIC_SERVICE_OF) >= table.civic_quarter_at:
        wants.append("district:civic_quarter")
    greens = {StructureKind.PARK, StructureKind.FOUNTAIN}
    if DistrictKind.GARDENS not in kinds and greens & set(built) and (stat(town.entity, "prosperity") or 0) >= table.gardens_prosperity:
        wants.append("district:gardens")
    for quarter, works in QUARTER_WORKS.items():
        if quarter not in kinds and sum(1 for kind in built if kind in works) >= table.modern_quarter_at:
            wants.append(f"district:{quarter.value}")
    society = await ctx.session.get(CommunitySocietyRow, town.entity.id)
    if society is not None and DistrictKind.INDUSTRIAL not in kinds and society.share(SocialClass.WORKER) >= table.industrial_worker_pct:
        wants.append("district:industrial")
    city = town.tier_index() >= TIER_ORDER.index(SizeTier.CITY)
    traders = society.share(SocialClass.PROFESSIONAL) + society.share(SocialClass.MERCHANT) if society is not None else 0.0
    if DistrictKind.BUSINESS not in kinds and city and traders >= table.business_share_pct:
        wants.append("district:business")
    if town.profile.morphology is Morphology.SPRAWL and DistrictKind.SUBURB not in kinds:
        wants.append("district:suburb")
    if DistrictKind.ARCOLOGY not in kinds and any(district.housing is HousingLevel.ARCOLOGY_UNIT for district in town.districts):
        wants.append("district:arcology")
    return list(dict.fromkeys(wants))


def spend(ctx: TickContext, town: Town, cost: int, work: int, label: str) -> bool:
    profile = town.profile
    pool = 0 if "investment_pool" in profile.locked else profile.investment_pool
    if profile.construction_capacity - town.work_used < work or pool + profile.treasury < cost:
        return False
    from_pool = min(pool, cost)
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
                note=label,
            )
        )
    town.work_used += work
    gain = round_half_up(cost / max(1, ctx.rules.taxation.wealth_per_treasury))
    shift_stat(town.entity, "wealth", gain, ctx.rules.society.default_stat)
    return True


async def add_district(
    ctx: TickContext,
    town: Town,
    kind: DistrictKind,
    *,
    material: BuildMaterial,
    son_id: int | None = None,
    builder_id: int | None = None,
    design_id: int | None = None,
) -> DistrictRow:
    same = next(
        (item for item in town.districts if item.kind is kind and item.design_id == design_id and item.level < 5 and "level" not in item.locked),
        None,
    )
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
        design_id=design_id,
        locked=[],
    )
    seat(ctx, district, [*town.districts, district], town.profile.morphology, town.infrastructure.walls_level)
    ctx.session.add(district)
    town.districts.append(district)
    if design_id is not None and design_id not in town.designs:
        town.designs.update(await designs_for(ctx.session, [district]))
    return district


def improve(rules: Rules, town: Town, kind: str, material: BuildMaterial) -> None:
    infrastructure = town.infrastructure
    if WORK_LOCKS.get(kind, kind) in infrastructure.locked:
        return
    if kind == "roads":
        infrastructure.roads = min(5, infrastructure.roads + 1)
    elif kind == "bridges":
        infrastructure.bridges = min(5, infrastructure.bridges + 1)
    elif kind == "irrigation":
        infrastructure.irrigation = min(5, infrastructure.irrigation + 1)
    elif kind == "cistern":
        infrastructure.water = WaterSupply.CISTERN
    elif kind == "aqueduct":
        infrastructure.water = WaterSupply.AQUEDUCT
    elif kind == "sewers":
        infrastructure.sewers = True
    elif kind == "walls":
        infrastructure.walls_level = min(5, infrastructure.walls_level + 1)
        keep(infrastructure, "walls_material", material)
        keep(infrastructure, "walls_condition", PERCENT)
        keep(infrastructure, "gates", max(1, infrastructure.gates))
        keep(infrastructure, "towers", min(20, infrastructure.towers + 2))
        shift_stat(town.entity, "defense", rules.urban.walls_per_level, 0)


async def waterside_of(ctx: TickContext, town: Town, knowledge: KnowledgeMap, ground: RegionEnvironmentRow | None) -> Waterside:
    if ground is None:
        return Waterside()
    skilled = knowledge.level(town.entity.id, KnowledgeBranch.AGRICULTURE) >= ctx.rules.environment.irrigation_agriculture_level
    irrigators = skilled or not await lacks(ctx.session, town.entity.id, Technique.IRRIGATION)
    return Waterside(river=ground.river_class, irrigators=irrigators)


async def build(ctx: TickContext, town: Town, knowledge: KnowledgeMap, *, at_war: bool, foreign: int, ground: RegionEnvironmentRow | None = None) -> int:
    table = ctx.rules.urban
    architecture = knowledge.level(town.entity.id, KnowledgeBranch.ARCHITECTURE)
    material = BuildMaterial.STONE if architecture >= ctx.rules.fire.stone_level else BuildMaterial.TIMBER
    built = 0
    waterside = await waterside_of(ctx, town, knowledge, ground)
    works = wanted_works(ctx, town, knowledge, at_war=at_war, foreign=foreign, waterside=waterside) + await quarter_wants(ctx, town)
    for want in await permitted(ctx, town, works):
        kind, _, detail = want.partition(":")
        if kind == "repair":
            district = next((item for item in town.districts if str(item.id) == detail), None)
            if district is not None and "condition" not in district.locked and spend(ctx, town, table.repair_cost, table.district_labour // 4, "repairs"):
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
    await unify_market(ctx, town.entity, town.districts, material)
    await store_up(ctx, town)
    return built


async def store_up(ctx: TickContext, town: Town) -> None:
    infrastructure = town.infrastructure
    effects = town.effects(ctx.rules)
    stores = {
        row.kind: row
        for row in await ctx.session.scalars(
            select(WorkshopRow).where(WorkshopRow.community_entity_id == town.entity.id, WorkshopRow.kind.in_([WorkshopKind.GRANARY, WorkshopKind.WAREHOUSE]))
        )
    }
    if "granary_capacity" not in infrastructure.locked:
        food = stores.get(store_kind(Commodity.FOOD))
        infrastructure.granary_capacity = settlement_store(
            ctx.rules, effects.food_store, food, Commodity.FOOD, design=await design_for(ctx.session, food)
        ).total
    if "warehouse_capacity" not in infrastructure.locked:
        goods = stores.get(store_kind(Commodity.GOODS))
        infrastructure.warehouse_capacity = settlement_store(
            ctx.rules, effects.goods_store, goods, Commodity.GOODS, design=await design_for(ctx.session, goods)
        ).total
    if "harbour_capacity" not in infrastructure.locked:
        infrastructure.harbour_capacity = effects.harbour


async def wear(ctx: TickContext, town: Town) -> None:
    for district in town.districts:
        if "condition" not in (district.locked or []):
            district.condition = max(0, district.condition - ctx.rules.urban.district_wear)


def outcast_share(society: CommunitySocietyRow | None) -> float:
    return society.share(SocialClass.OUTCAST) / PERCENT if society is not None else 0.0


async def bandits_near(ctx: TickContext, atlas: RegionAtlas, town: Town) -> list[EntityRow]:
    home = atlas.top_region(town.entity.id)
    if home is None:
        return []
    near = {home, *atlas.neighbour_regions(home)}
    robbers = await robber_ids(ctx.session)
    found = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.FACTION, EntityRow.status == EntityStatus.CANON, EntityRow.id.in_(list(robbers) or [-1]))
    )
    return [band for band in found if atlas.top_region(band.id) in near]


def band_pressure(rules: Rules, atlas: RegionAtlas, town: Town, bands: list[EntityRow]) -> float:
    home = atlas.top_region(town.entity.id)
    return sum(1.0 if atlas.top_region(band.id) == home else rules.crime.neighbour_band_pct / PERCENT for band in bands)


async def keep_order(ctx: TickContext, town: Town, *, justice: float, bands: list[EntityRow], hierarchy: int, pressure: float) -> None:
    table = ctx.rules.crime
    profile = town.profile
    society = await ctx.session.get(CommunitySocietyRow, town.entity.id)
    garrison = await living_entity(ctx.session, profile.garrison_entity_id) if profile.garrison_entity_id is not None else None
    soldiers = profile.militia + ((stat(garrison, "size") or 0) if garrison is not None else 0)
    effects = town.effects(ctx.rules)
    urban = town.urban
    policing = soldiers / PERCENT * table.policing_per_100 + effects.policing + urban.covered(UrbanService.WATCH) * ctx.rules.prevention.watch_policing
    wealth = stat(town.entity, "prosperity") or 0
    rule = await scale_here(ctx, town.entity.id, DivineScale.ORDER)
    if "public_order" not in profile.locked:
        charter = ctx.rules.urban.charter_order if profile.charter_entity_id is not None else 0
        seat = effects.order + rule * ctx.rules.dominion.order_per_step
        profile.public_order = clamp_int(table.order_base + soldiers / PERCENT * table.order_per_100 + charter + seat - profile.crime / HALF, 0, PERCENT)
    if "crime" not in profile.locked:
        crime = (
            (PERCENT - wealth) * table.poverty_pct / PERCENT
            + outcast_share(society) * PERCENT * table.outcast_pct / PERCENT
            + inequality_pressure(ctx.rules, society, hierarchy)
            + (PERCENT - profile.public_order) * table.disorder_pct / PERCENT
            + pressure * table.bandit_crime
            - policing
            - justice * table.justice_pct
            - rule * ctx.rules.dominion.crime_per_step
            + (1 - urban.covered(UrbanService.WATCH)) * ctx.rules.coverage.crime
            + urban.homeless_share * ctx.rules.homelessness.crime
            + await weapons_crime(ctx, town.entity.id)
            + urban.turf * ctx.rules.turf.crime_per_turf
        )
        profile.crime = clamp_int(crime, 0, PERCENT)
    shift_stat(town.entity, "prosperity", -profile.crime * table.prosperity_loss / PERCENT, ctx.rules.society.default_stat)
    for band in bands:
        shift_stat(band, "strength", profile.crime * table.bandit_feed_pct / PERCENT / max(1, len(bands)), ctx.rules.society.default_stat)


def hallow(ctx: TickContext, town: Town) -> None:
    table = ctx.rules.coverage
    shift_stat(town.entity, "piety", -(1 - town.urban.covered(UrbanService.FAITH)) * table.impiety, ctx.rules.society.default_stat)
    shift_stat(town.entity, "prosperity", -(1 - town.urban.covered(UrbanService.MARKET)) * table.prices, ctx.rules.society.default_stat)
    floor = clamp_int(town.effects(ctx.rules).piety_floor, 0, PERCENT)
    piety = stat(town.entity, "piety")
    if floor > 0 and piety is not None and piety < floor:
        set_stats(town.entity, piety=floor)


async def punish(ctx: TickContext, town: Town, laws: LawBook) -> bool:
    table = ctx.rules.crime
    if not ctx.rng(f"punish.{town.entity.id}").chance(table.punishment_chance * town.profile.crime / PERCENT):
        return False
    judge = await judge_for(ctx, laws.member_of.get(town.entity.id), town.entity.id)
    return await open_case(ctx, town, laws, judge=judge) is not None


async def quarantined(ctx: TickContext, region: int | None) -> bool:
    row = await ctx.session.get(QuarantineRow, region) if region is not None else None
    return row is not None and row.until_epoch >= ctx.epoch


async def ruler_discontent(ctx: TickContext, town_id: int) -> float:
    realm = await realm_of_community(ctx.session, town_id)
    ruler = await ruler_of_realm(ctx.session, realm) if realm is not None else None
    opinion = await ctx.session.get(PublicOpinionRow, (town_id, ruler)) if ruler is not None else None
    if opinion is None or opinion.approval >= 0:
        return 0.0
    return -opinion.approval * ctx.rules.communication.disapproval_unrest_pct / PERCENT


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
    discontent = await ruler_discontent(ctx, town.entity.id)
    turmoil = max(0, -await scale_here(ctx, town.entity.id, DivineScale.ORDER)) * ctx.rules.dominion.unrest_per_step
    unrest = (
        profile.unrest * (1 - table.unrest_decay / PERCENT)
        + profile.tax_rate * taxation.unrest_per_tax / PERCENT
        + profile.crime * table.crime_unrest_pct / PERCENT
        + hunger * table.hunger_unrest
        + pressure / 4
        + bound_revolt(ctx.rules, rows)
        + tension
        + discontent
        + turmoil
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


@dataclass(frozen=True)
class FireYear:
    wet: int = 0
    wind: int = 0


def fire_season(book: EnvironmentBook, world_id: int) -> WorldSeasonRow | None:
    seasons = book.seasons_of(world_id)
    return min(seasons, key=lambda season: (season.rain_shift, season.position)) if seasons else None


def fire_years(ctx: TickContext, town: Town, ground: RegionEnvironmentRow | None, book: EnvironmentBook | None) -> list[FireYear]:
    years = world_years(ctx.environment, town.entity.world_id or 0, "fires")
    if ground is None or book is None:
        return [FireYear() for _ in years]
    season = fire_season(book, ground.world_id)
    found: list[FireYear] = []
    for year in years:
        weather = book.weather(ctx.environment.world_seed, ctx.epoch, ground, season, f"fire.{town.entity.id}.{year.year}")
        found.append(FireYear(wet=weather.effect(WeatherEffect.WET), wind=weather.effect(WeatherEffect.WIND)))
    return found


def flammability(material: BuildMaterial) -> float:
    return max(0, PERCENT - MATERIALS[BUILD_MATERIALS[material]].ignition_point) / PERCENT


def flammable_share(town: Town) -> float:
    total = sum(district.level for district in town.districts)
    timber = flammability(BuildMaterial.TIMBER) or 1.0
    if total <= 0:
        return 1.0
    return sum(district.level * flammability(district.material) for district in town.districts) / total / timber


def ambient_heat(rules: Rules, ground: RegionEnvironmentRow | None) -> int:
    if ground is None:
        return 0
    return round_half_up(max(0, ground.temperature - rules.fire.ambient_floor) * rules.fire.ambient_heat_pct / PERCENT)


def self_igniting(rules: Rules, town: Town, ground: RegionEnvironmentRow | None) -> bool:
    heat = ambient_heat(rules, ground)
    return heat > 0 and any(heat >= MATERIALS[BUILD_MATERIALS[district.material]].ignition_point for district in town.districts)


async def fires(ctx: TickContext, town: Town, ground: RegionEnvironmentRow | None, knowledge: KnowledgeMap, book: EnvironmentBook | None = None) -> int:
    table = ctx.rules.fire
    if not (await view_of(ctx.session, ctx.rules, town.entity.world_id)).fire:
        if "fire_risk" not in town.profile.locked:
            town.profile.fire_risk = 0
        return 0
    people = stat(town.entity, "population") or 0
    crowd = min(1.0, people / max(1, housing_of(ctx.rules, town)))
    brigade = 1 - town.urban.covered(UrbanService.FIRE) * ctx.rules.prevention.brigade_pct / PERCENT
    town.profile.fire_risk = clamp_int((flammable_share(town) * table.timber_risk + crowd * table.crowding_risk) * brigade, 0, PERCENT)
    igniting = self_igniting(ctx.rules, town, ground)
    dry = 1.0 if igniting or ground is None or ground.rainfall < table.dry_rainfall else DRY_OFF_PCT / PERCENT
    dry *= 1 + table.ambient_ignition_pct / PERCENT if igniting else 1.0
    dry *= 1 + await foe_pct(ctx, town.entity.id, DomainHook.FIRE_CURSE) / PERCENT
    rng = ctx.rng(f"fire.{town.entity.id}")
    burned = 0
    for year in fire_years(ctx, town, ground, book):
        damp = 1 - year.wet / PERCENT * table.wet_damp_pct / PERCENT
        if not rng.chance(table.chance_pct * town.profile.fire_risk / PERCENT * dry * max(0.0, damp)):
            continue
        timber = [district for district in town.districts if district.material is BuildMaterial.TIMBER] or town.districts
        if not timber:
            continue
        gale = (
            (1 + year.wind / PERCENT * table.wind_spread_pct / PERCENT)
            * spread_of(ctx.rules, town.profile.morphology)
            * (1 - await shield_of(ctx, town.entity, None))
        )
        district = max(timber, key=lambda item: (item.level, -item.id))
        level = district.level
        gone = wound_district(district, round_half_up(table.district_loss * gale))
        if district.level < level and knowledge.level(town.entity.id, KnowledgeBranch.ARCHITECTURE) >= table.stone_level and "material" not in district.locked:
            district.material = BuildMaterial.STONE
        if gone:
            await ctx.session.delete(district)
            town.districts.remove(district)
        replan(town.profile)
        floor, _ = headcount_bounds(ctx.rules, town.entity)
        before = stat(town.entity, "population") or 0
        dead = min(max(0, before - floor), round_half_up(before * table.death_pct * gale / PERCENT))
        with flowing(FlowCategory.DISASTER):
            set_stats(town.entity, population=before - dead)
        ledger(ctx, town, TreasuryEntry.FIRE, -table.treasury_loss, "great fire")
        burned += 1
        driven = " Driven by the wind, it leapt from roof to roof." if year.wind >= PERCENT // HALF else ""
        await note(
            ctx,
            f"A great fire swept through the {district.kind.value.replace('_', ' ')} of {town.entity.name}; {dead} died in the flames.{driven}",
            key="settlement.fire_wind" if driven else "settlement.fire",
            ids=[town.entity.id],
            feed=FeedCategory.DISASTER,
            kind=ChronicleKind.WORLD,
        )
        await record_fire(ctx, town.entity, dead)
        await burn_works(ctx, town.entity)
        await burn_structures(ctx, town.entity, gale)
        await mark_ruin(ctx, town.entity, RebuildCause.FIRE)
    return burned


def sanitation(ctx: TickContext, town: Town, knowledge: KnowledgeMap, *, lifted: int = 0) -> None:
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
        + town.effects(ctx.rules).sanitation
        + lifted
        - min(1.0, crowd) * table.crowding_loss
        - (1 - town.urban.covered(UrbanService.WATER)) * ctx.rules.coverage.thirst
        - (1 - max(town.urban.covered(UrbanService.HEALING), town.urban.covered(UrbanService.BATH))) * ctx.rules.coverage.disease
        - town.urban.homeless_share * ctx.rules.homelessness.disease
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
    people = stat(town.entity, "population") or 0
    need = aggregate_need(ctx.rules, people, Commodity.FOOD)
    in_granary = min(food, storage_index(ctx.rules, town.infrastructure.granary_capacity, need) - ctx.rules.economy.storage_base_index)
    at_home = min(food - in_granary, ctx.rules.economy.storage_base_index)
    stored = (in_granary + at_home / HALF) / FOOD_INDEX
    keep(profile, "siege_supplies", round_half_up(stored * table.siege_food_days))
    water = {
        WaterSupply.NONE: 0,
        WaterSupply.WELL: table.siege_water_days // 3,
        WaterSupply.CISTERN: table.siege_water_days,
        WaterSupply.AQUEDUCT: table.siege_water_days,
    }
    keep(profile, "siege_water", water[town.infrastructure.water])
    if siege is None:
        keep(profile, "siege_disease", 0)
        keep(profile, "rationing", profile.siege_supplies < urban.ration_supplies_days and food < FOOD_INDEX // HALF)
    else:
        keep(profile, "siege_disease", clamp_int(profile.siege_disease + table.siege_disease_step * (1 - profile.sanitation / PERCENT), 0, PERCENT))
        keep(profile, "rationing", profile.siege_supplies < urban.ration_supplies_days or profile.siege_water < urban.ration_supplies_days // HALF)
        if profile.siege_disease >= SIEGE_DISEASE and ctx.rng(f"siege_disease.{town.entity.id}").chance(profile.siege_disease):
            await strike_plague(ctx, town.entity, profile.siege_disease, path=SpreadPath.SIEGE)
            keep(profile, "siege_disease", profile.siege_disease // HALF)
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
    population = max(1, stat(town.entity, "population") or 0)
    keep(town.profile, "foreigners", {key: clamp_int(value * PERCENT / max(population, total * 5), 0, PERCENT) for key, value in shares.items()})
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
    relief = max(0.0, 1 - town.effects(ctx.rules).tension_relief_pct / PERCENT)
    return clamp_int(value_distance(own, parent) * table.tension_pct / PERCENT * relief, 0, PERCENT) if parent else 0


async def retier(ctx: TickContext, town: Town) -> SizeTier | None:
    if "size_tier" in town.profile.locked:
        return None
    people = counted_people(ctx.rules, stat(town.entity, "population") or 0, await centrality_of(ctx.session, town.entity.id))
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
    literacy = culture.literacy if culture is not None else 0
    unschooled = (1 - town.urban.covered(UrbanService.SCHOOL)) * ctx.rules.coverage.illiteracy
    return clamp_int(round_half_up(literacy - unschooled), 0, PERCENT)
