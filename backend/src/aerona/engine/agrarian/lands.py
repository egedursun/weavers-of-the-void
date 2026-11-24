from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.catalog.goods_traits import commodities_with
from aerona.catalog.life.agrarian import COMMONS_BOON, KIND_TOLL, PALM_GOODS
from aerona.constants.units import PER_MILLE, PERCENT
from aerona.core.grammar import spoken
from aerona.core.total import total
from aerona.db.tables.affairs import MandateRow
from aerona.db.tables.agrarian import CommonsRow, GameReserveRow, IntensificationRow, PerennialRow
from aerona.db.tables.ecology import SpeciesProductRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.flora import PlantProfileRow, RegionCropRow
from aerona.db.tables.households import HouseholdRow
from aerona.db.tables.polity import HouseProfileRow
from aerona.db.tables.regime import RegimeRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.agrarian import CommonsKind, CommonsRule, PerennialKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.ecology import SOWN, GrowthCycle
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import CoastKind, RiverClass, SoilKind, TemperatureBand
from aerona.domain.enums.goods_traits import CommodityTrait
from aerona.domain.enums.living import LineTrait
from aerona.domain.enums.mind import ActKind, MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.records import StepAction
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.statecraft import MandateKind, MandateState
from aerona.engine.agrarian.rings import put
from aerona.engine.collective.book import shift
from aerona.engine.context import TickContext
from aerona.engine.cycles.standing import regard
from aerona.engine.economy.purse import give_coin
from aerona.engine.economy.stocks import goods_of
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.living.traits import eased, traits_of
from aerona.engine.lore.civics import holders_know
from aerona.engine.mind.hooks import judged
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.laws import law_param
from aerona.engine.polity.mandates import issue
from aerona.engine.polity.trials import report_crime
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_in
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat, stat_or
from aerona.engine.recording.record import FactInput, RoleValue, StepDraft, record

LONG_LIVED = frozenset({GrowthCycle.PERENNIAL, GrowthCycle.TREE})
CITY_TIERS = frozenset({SizeTier.TOWN, SizeTier.CITY, SizeTier.METROPOLIS, SizeTier.MEGALOPOLIS, SizeTier.WORLD_CITY})
CASH_CROPS = frozenset(commodities_with(CommodityTrait.CASH_CROP))
YIELD_KINDS: tuple[tuple[CommodityKind, PerennialKind], ...] = (
    (CommodityKind.TIMBER, PerennialKind.TIMBER),
    (CommodityKind.BREW_BASE, PerennialKind.VINEYARD),
    (CommodityKind.FRUIT, PerennialKind.ORCHARD),
)
HALF = 50
FREEHOLD = "freehold"
COMMUNAL = "communal"
COTTAGERS = frozenset({SocialClass.FARMER, SocialClass.SERF_OR_SLAVE})
STRICT = 50
WARM_BANDS = frozenset({TemperatureBand.WARM, TemperatureBand.HOT, TemperatureBand.SEARING})


@dataclass
class LandsTally:
    planted: int = 0
    bearing: int = 0
    commons: int = 0
    councils: int = 0
    enclosed: int = 0
    dispossessed: int = 0
    reserves: int = 0
    poaching: int = 0


@dataclass
class Holdings:
    atlas: RegionAtlas
    towns: dict[int, list[EntityRow]] = field(default_factory=lambda: defaultdict(list))
    profiles: dict[int, SettlementProfileRow] = field(default_factory=dict)
    lands: dict[int, RegionEnvironmentRow] = field(default_factory=dict)

    def largest(self, region_id: int) -> EntityRow | None:
        towns = self.towns.get(region_id, [])
        return max(towns, key=lambda town: (stat_or(town, "population", 0), -town.id)) if towns else None


async def holdings(ctx: TickContext) -> Holdings:
    found = Holdings(await RegionAtlas.load(ctx.session))
    rows = await ctx.session.execute(
        select(EntityRow, SettlementProfileRow)
        .join(SettlementProfileRow, SettlementProfileRow.settlement_entity_id == EntityRow.id)
        .where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    for town, profile in rows.all():
        region = found.atlas.top_region(town.id)
        if region is not None:
            found.towns[region].append(town)
            found.profiles[town.id] = profile
    found.lands = {row.entity_id: row for row in await ctx.session.scalars(select(RegionEnvironmentRow))}
    return found


def mature_epochs(ctx: TickContext, kind: PerennialKind) -> int:
    table = ctx.rules.perennials
    return total(
        PerennialKind,
        {
            PerennialKind.ORCHARD: table.orchard_epochs,
            PerennialKind.VINEYARD: table.vineyard_epochs,
            PerennialKind.GROVE: table.grove_epochs,
            PerennialKind.TIMBER: table.timber_epochs,
            PerennialKind.PLANTATION: table.plantation_epochs,
            PerennialKind.FOREST_GARDEN: table.forest_garden_epochs,
            PerennialKind.COPPICE: table.epochs(table.coppice_years),
            PerennialKind.HEDGEROW: table.epochs(table.hedgerow_years),
            PerennialKind.PALM_STAND: table.epochs(table.palm_stand_years),
        },
    )[kind]


def kind_of(yields: set[CommodityKind], land: RegionEnvironmentRow | None, forest: int) -> PerennialKind:
    if land is not None and land.temperature_band in WARM_BANDS and yields & PALM_GOODS:
        return PerennialKind.PALM_STAND
    if yields & CASH_CROPS:
        return PerennialKind.PLANTATION
    if land is not None and CommodityKind.TIMBER in yields and land.forest_cover < forest:
        return PerennialKind.COPPICE
    if land is not None and not yields - {CommodityKind.TIMBER} and land.farmed >= STRICT:
        return PerennialKind.HEDGEROW
    if land is not None and land.forest_cover >= forest and CommodityKind.FRUIT in yields:
        return PerennialKind.FOREST_GARDEN
    return next((kind for commodity, kind in YIELD_KINDS if commodity in yields), PerennialKind.GROVE)


async def plant(ctx: TickContext, lands: Holdings, tally: LandsTally) -> None:
    table = ctx.rules.perennials
    crops = await ctx.session.execute(
        select(RegionCropRow.region_entity_id, RegionCropRow.plant_entity_id)
        .join(PlantProfileRow, PlantProfileRow.species_entity_id == RegionCropRow.plant_entity_id)
        .where(PlantProfileRow.growth_cycle.in_(list(LONG_LIVED)), PlantProfileRow.cultivation.in_(list(SOWN)))
        .order_by(RegionCropRow.region_entity_id, RegionCropRow.plant_entity_id)
    )
    planted = {(row.region_entity_id, row.species_entity_id) for row in await ctx.session.scalars(select(PerennialRow))}
    yields: dict[int, set[CommodityKind]] = defaultdict(set)
    for species_id, commodity in await ctx.session.execute(select(SpeciesProductRow.species_entity_id, SpeciesProductRow.commodity)):
        if commodity is not None:
            yields[species_id].add(commodity)
    for region_id, plant_id in crops.all():
        owner = lands.largest(region_id)
        if owner is None or held(region_id) or (region_id, plant_id) in planted:
            continue
        if not ctx.rng(f"perennials.{region_id}.{plant_id}.{ctx.epoch}").chance(table.plant_pct):
            continue
        kind = kind_of(yields.get(plant_id, set()), lands.lands.get(region_id), ctx.rules.commons.woods_forest)
        epochs = mature_epochs(ctx, kind)
        ctx.session.add(
            PerennialRow(
                region_entity_id=region_id,
                kind=kind,
                species_entity_id=plant_id,
                owner_node_id=owner.id,
                area=table.area,
                mature_epochs=epochs,
                planted_epoch=ctx.epoch,
                locked=[],
            )
        )
        planted.add((region_id, plant_id))
        tally.planted += 1
        await record(
            ctx,
            "perennials.planted",
            roles={IncidentRole.ACTOR: owner.id, IncidentRole.PRODUCT: plant_id, IncidentRole.PLACE: region_id},
            facts={"perennial": kind, "area": table.area, "epochs": epochs},
            place=region_id,
        )


async def grow(ctx: TickContext, lands: Holdings, tally: LandsTally) -> None:
    table = ctx.rules.perennials
    bearing: dict[int, int] = defaultdict(int)
    for row in await ctx.session.scalars(select(PerennialRow).order_by(PerennialRow.id)):
        if held(row.region_entity_id):
            continue
        if row.condition > 0:
            shift(row, "maturity", PERCENT / max(1, row.mature_epochs))
        old = row.maturity >= PERCENT and ctx.epoch - row.planted_epoch > row.mature_epochs * (PERCENT + table.life_pct) / PERCENT
        traits = await traits_of(ctx.session, row.line_id)
        shift(row, "condition", -eased(table.ageing, traits.get(LineTrait.HARDINESS, 0)) if old else table.recover)
        if old and row.condition <= 0:
            await replant(ctx, row)
            continue
        if row.maturity < PERCENT:
            continue
        bearing[row.region_entity_id] += 1
        tally.bearing += 1
        owner = await ctx.session.get(EntityRow, row.owner_node_id) if row.owner_node_id is not None else None
        if owner is not None and not held(owner.id):
            bred = PERCENT + traits.get(LineTrait.YIELD, 0) * ctx.rules.living_production.yield_pct // PERCENT
            coin_pct, column, toll = KIND_TOLL[row.kind]
            earned = row.area * table.coin_per_area * row.condition / PERCENT * max(0, bred) / PERCENT * coin_pct / PERCENT
            await give_coin(ctx.session, ctx.rules, owner, round_half_up(earned))
            if row.kind is PerennialKind.COPPICE:
                await goods_of(ctx.session, ctx.epoch).add(
                    owner.id, CommodityKind.FUEL, round_half_up(row.area * table.coppice_fuel * row.condition / PERCENT), GoodsFlow.EXTRACTION
                )
            land = lands.lands.get(row.region_entity_id)
            if toll and land is not None and column not in land.locked:
                setattr(land, column, clamp_int(getattr(land, column) + toll, 0, PERCENT))
    for region_id, count in sorted(bearing.items()):
        for town in lands.towns.get(region_id, []):
            if not held(town.id):
                shift_stat(town, "prosperity", min(table.prosperity_cap, count))


async def replant(ctx: TickContext, row: PerennialRow) -> None:
    if "maturity" in row.locked:
        return
    row.maturity = 0
    row.planted_epoch = ctx.epoch
    if "condition" not in row.locked:
        row.condition = PERCENT
    await record(
        ctx,
        "perennials.replanted",
        roles={IncidentRole.PLACE: row.region_entity_id},
        facts={"perennial": row.kind, "epochs": row.mature_epochs},
        place=row.region_entity_id,
    )


async def commons_kinds(ctx: TickContext, land: RegionEnvironmentRow, towns: list[EntityRow]) -> list[CommonsKind]:
    table = ctx.rules.commons
    kinds: list[CommonsKind] = []
    if land.grazed >= table.pasture_grazed:
        kinds.append(CommonsKind.PASTURE)
    if land.forest_cover >= table.woods_forest:
        kinds.append(CommonsKind.WOODS)
    if land.coast_kind is not CoastKind.NONE or land.river_class is not RiverClass.NONE:
        kinds.append(CommonsKind.FISHERY)
    if land.river_class is not RiverClass.NONE or land.rainfall >= table.water_rain:
        kinds.append(CommonsKind.WATER)
    if land.forest_cover >= table.woods_forest and land.built < table.wild_built:
        kinds.append(CommonsKind.HUNTING_GROUND)
    if land.mined > 0 or land.mineral_layers:
        kinds.append(CommonsKind.QUARRY)
    if land.magic_density >= table.source_density:
        kinds.append(CommonsKind.SOURCE_GROUND)
    if land.soil is SoilKind.PEAT or land.wetland >= table.turbary_peat:
        kinds.append(CommonsKind.TURBARY)
    if land.forest_cover >= table.woods_forest // 2 and land.farmed < table.wild_built:
        kinds.append(CommonsKind.FORAGING_GROUND)
    if land.coast_kind is not CoastKind.NONE and land.base_wetland < table.turbary_peat:
        kinds.append(CommonsKind.SHORE)
    holders = [town.id for town in towns]
    if await holders_know(ctx.session, holders, Technique.RADIO):
        kinds.append(CommonsKind.SPECTRUM)
    if await holders_know(ctx.session, holders, Technique.ROCKETRY):
        kinds.append(CommonsKind.ORBITS)
    return kinds


def bestow(row: CommonsRow, town: EntityRow, profile: SettlementProfileRow | None) -> None:
    column, amount = COMMONS_BOON[row.kind]
    gain = amount * row.condition // PERCENT
    if column == "prosperity":
        shift_stat(town, column, gain)
    elif profile is not None and column not in profile.locked:
        setattr(profile, column, clamp_int(getattr(profile, column) + gain, 0, PERCENT * 100 if column == "construction_capacity" else PERCENT))


def wear_share(ctx: TickContext, rule: CommonsRule) -> int:
    table = ctx.rules.commons
    return {
        CommonsRule.COUNCIL: table.council_pct,
        CommonsRule.ENCLOSED: table.enclosed_pct,
        CommonsRule.STATE: table.state_pct,
        CommonsRule.LICENSED: table.licensed_pct,
        CommonsRule.ROTATIONAL: table.rotational_pct,
    }.get(rule, PERCENT)


async def seed_commons(ctx: TickContext, lands: Holdings, rows: list[CommonsRow]) -> None:
    known = {(row.region_entity_id, row.kind) for row in rows}
    for region_id in sorted(lands.towns):
        land = lands.lands.get(region_id)
        steward = lands.largest(region_id)
        if land is None or steward is None or held(region_id):
            continue
        for kind in await commons_kinds(ctx, land, lands.towns.get(region_id, [])):
            if (region_id, kind) not in known:
                row = CommonsRow(region_entity_id=region_id, kind=kind, steward_entity_id=steward.id, since_epoch=ctx.epoch, locked=[])
                ctx.session.add(row)
                rows.append(row)
    if any(row.id is None for row in rows):
        await ctx.session.flush()


async def city_for(ctx: TickContext, lands: Holdings, row: CommonsRow, book: RealmBook) -> EntityRow | None:
    realm_id = book.member_of.get(row.steward_entity_id) if row.steward_entity_id is not None else None
    realm = book.realms.get(realm_id) if realm_id is not None else None
    cities: list[EntityRow] = []
    for member in realm.members if realm is not None else {}:
        profile = lands.profiles.get(member)
        place = await ctx.session.get(EntityRow, member)
        if place is None or profile is None or profile.size_tier not in CITY_TIERS or held(member):
            continue
        if lands.atlas.top_region(member) != row.region_entity_id:
            cities.append(place)
    return max(cities, key=lambda town: (stat_or(town, "population", 0), -town.id)) if cities else None


async def drive_off(ctx: TickContext, lands: Holdings, town: EntityRow, city: EntityRow | None) -> int:
    lost = round_half_up(stat_or(town, "population", 0) * ctx.rules.commons.dispossess_pct / PERCENT)
    profile = lands.profiles.get(town.id)
    if city is None:
        if profile is not None:
            shift(profile, "homeless", lost, high=10**9)
        return lost
    before = stat_or(town, "population", 0)
    with flowing(FlowCategory.MIGRATION):
        shift_stat(town, "population", -lost)
        moved = before - stat_or(town, "population", 0)
        shift_stat(city, "population", moved)
    return moved


async def enclose(ctx: TickContext, lands: Holdings, row: CommonsRow, encloser: EntityRow, book: RealmBook) -> int:
    table = ctx.rules.commons
    put(row, "rule", CommonsRule.ENCLOSED)
    put(row, "encloser_node_id", encloser.id)
    row.enclosed_epoch = ctx.epoch
    towns = [town for town in lands.towns.get(row.region_entity_id, []) if not held(town.id)]
    city = await city_for(ctx, lands, row, book)
    driven = 0
    for town in towns:
        driven += await drive_off(ctx, lands, town, city)
        shift_stat(town, "prosperity", -table.sol_loss)
        profile = lands.profiles.get(town.id)
        if profile is not None:
            shift(profile, "unrest", table.unrest_gain)
        for household in await ctx.session.scalars(
            select(HouseholdRow).where(HouseholdRow.settlement_node_id == town.id, HouseholdRow.social_class.in_(list(COTTAGERS)))
        ):
            if "wealth" not in household.locked:
                household.wealth = max(0, household.wealth - household.wealth * table.household_loss // PERCENT)
        await judged(ctx, encloser.id, town.id, ActKind.ENCLOSING, note=f"enclosed the common {spoken(row.kind)} of {town.name}")
    put(row, "dispossessed", row.dispossessed + driven)
    roles: dict[IncidentRole, RoleValue] = {
        IncidentRole.ACTOR: encloser.id,
        IncidentRole.PLACE: row.region_entity_id,
        IncidentRole.VICTIM: [town.id for town in towns],
    }
    facts: dict[str, FactInput] = {"common": row.kind, "driven": driven}
    if city is not None:
        await record(ctx, "commons.enclosed", roles={**roles, IncidentRole.DESTINATION: city.id}, facts=facts, place=row.region_entity_id)
    else:
        await record(ctx, "commons.enclosed_homeless", roles=roles, facts=facts, place=row.region_entity_id)
    return driven


def realm_dispossessed(rows: list[CommonsRow], book: RealmBook, realm_id: int) -> int:
    return sum(row.dispossessed for row in rows if row.steward_entity_id is not None and book.member_of.get(row.steward_entity_id) == realm_id)


def share_common(ctx: TickContext, lands: Holdings, row: CommonsRow) -> None:
    table = ctx.rules.commons
    towns = lands.towns.get(row.region_entity_id, [])
    for town in towns:
        if not held(town.id):
            share = 1 - table.licence_concentration_pct / PERCENT if row.rule is CommonsRule.LICENSED and town.id != row.steward_entity_id else 1.0
            shift_stat(town, "prosperity", (row.condition - HALF) / HALF * table.prosperity_weight * share)
            bestow(row, town, lands.profiles.get(town.id))
            if row.rule is CommonsRule.STATE:
                aggrieve(table.state_grievance, lands.profiles.get(town.id))
            elif row.rule is CommonsRule.ROTATIONAL:
                aggrieve(-table.rotational_calm, lands.profiles.get(town.id))


async def keep_commons(ctx: TickContext, lands: Holdings, tally: LandsTally) -> None:
    table = ctx.rules.commons
    rows = list(await ctx.session.scalars(select(CommonsRow).order_by(CommonsRow.id)))
    await seed_commons(ctx, lands, rows)
    pressure = {row.region_entity_id: row.pressure for row in await ctx.session.scalars(select(IntensificationRow))}
    book = await RealmBook.load(ctx.session)
    orders = await enclosure_orders(ctx)
    for row in rows:
        if held(row.region_entity_id):
            continue
        tally.commons += 1
        put(row, "use", clamp_int(pressure.get(row.region_entity_id, HALF), 0, PERCENT * 2))
        if row.rule in QUOTA_RULES:
            put(row, "use", await held_to_quota(ctx, row))
        if row.use > table.sustainable:
            before = row.condition
            shift(row, "condition", -(row.use - table.sustainable) * table.degrade_pct / PERCENT * wear_share(ctx, row.rule) / PERCENT)
            if row.condition < table.council_at <= before:
                await record(
                    ctx,
                    "commons.overused",
                    roles={IncidentRole.SUBJECT: row.region_entity_id},
                    facts={"common": row.kind, "use": row.use, "condition": row.condition},
                    place=row.region_entity_id,
                )
        else:
            shift(row, "condition", table.regrow)
        if row.rule is not CommonsRule.ENCLOSED:
            share_common(ctx, lands, row)
            await pay_realm(ctx, row, book)
        steward = lands.profiles.get(row.steward_entity_id) if row.steward_entity_id is not None else None
        if (
            row.rule in (CommonsRule.OPEN, CommonsRule.CUSTOMARY)
            and row.condition < table.council_at
            and steward is not None
            and steward.public_order >= table.council_order
            and ctx.rng(f"commons.council.{row.id}.{ctx.epoch}").chance(table.council_chance)
        ):
            put(row, "rule", CommonsRule.ROTATIONAL if row.condition < table.rotational_at else CommonsRule.COUNCIL)
            tally.councils += 1
            await record(
                ctx,
                "commons.council",
                roles={IncidentRole.SUBJECT: row.steward_entity_id},
                facts={"common": row.kind, "condition": row.condition},
                place=row.steward_entity_id,
            )
        await maybe_enclose(ctx, row, rows=rows, book=book, orders=orders)
        await obey_orders(ctx, lands, row, orders, book=book, tally=tally)
        if row.rule is CommonsRule.ENCLOSED and row.encloser_node_id is not None:
            owner = await ctx.session.get(EntityRow, row.encloser_node_id)
            if owner is not None and not held(owner.id):
                await give_coin(ctx.session, ctx.rules, owner, round_half_up(table.enclosed_coin * row.condition / PERCENT))


QUOTA_RULES = frozenset({CommonsRule.STATE, CommonsRule.LICENSED})


async def held_to_quota(ctx: TickContext, row: CommonsRow) -> int:
    over = max(0, row.use - row.quota)
    if over <= 0:
        return row.use
    if row.rule is CommonsRule.LICENSED:
        return row.quota
    slipped = round_half_up(over * (PERCENT - row.officials) / PERCENT)
    if slipped > 0 and ctx.rng(f"commons.poach.{row.id}.{ctx.epoch}").chance(ctx.rules.commons.poaching_pct):
        await record(
            ctx,
            "commons.poaching",
            roles={IncidentRole.SUBJECT: row.steward_entity_id},
            facts={"common": row.kind, "poached": slipped},
            place=row.steward_entity_id,
        )
        return row.quota + slipped
    return row.quota


def aggrieve(grievance: int, profile: SettlementProfileRow | None) -> None:
    if profile is not None and "public_order" not in profile.locked:
        profile.public_order = clamp_int(profile.public_order - grievance, 0, PERCENT)


async def pay_realm(ctx: TickContext, row: CommonsRow, book: RealmBook) -> None:
    if row.rule not in QUOTA_RULES or row.steward_entity_id is None:
        return
    realm_id = book.member_of.get(row.steward_entity_id)
    realm = book.realms.get(realm_id) if realm_id is not None else None
    if realm is None or held(realm.entity.id):
        return
    table = ctx.rules.commons
    coin = table.state_coin * row.condition // PERCENT if row.rule is CommonsRule.STATE else row.quota * row.licence_price // PERCENT
    if coin > 0:
        await give_coin(ctx.session, ctx.rules, realm.entity, coin)
    if row.rule is CommonsRule.LICENSED and coin > 0:
        await record(
            ctx,
            "commons.licences_sold",
            roles={IncidentRole.SUBJECT: row.steward_entity_id},
            facts={"common": row.kind, "coin": coin},
            place=row.steward_entity_id,
        )


async def take_common(ctx: TickContext, row: CommonsRow, rule: CommonsRule) -> None:
    table = ctx.rules.commons
    before = row.rule
    put(row, "rule", rule)
    if rule is CommonsRule.STATE:
        put(row, "officials", table.state_enforcement)
    if rule is CommonsRule.LICENSED:
        put(row, "licence_price", table.licence_price)
    await record(
        ctx,
        "commons.rule_changed",
        roles={IncidentRole.SUBJECT: row.steward_entity_id},
        facts={"common": row.kind, "rule": rule, "before": before},
        place=row.steward_entity_id,
    )


async def maybe_enclose(ctx: TickContext, row: CommonsRow, *, rows: list[CommonsRow], book: RealmBook, orders: dict[int, int]) -> None:
    table = ctx.rules.commons
    if row.rule is CommonsRule.ENCLOSED or "rule" in row.locked or row.steward_entity_id is None:
        return
    realm_id = book.member_of.get(row.steward_entity_id)
    realm = book.realms.get(realm_id) if realm_id is not None else None
    if realm is None or realm.ruler_id is None or held(realm.ruler_id):
        return
    regime = await ctx.session.get(RegimeRow, realm.entity.id)
    eager = 2 if regime is not None and regime.horizon < table.horizon_mark else 1
    profit = 1 + realm_dispossessed(rows, book, realm.entity.id) / max(1.0, table.labour_span * stat_or(realm.entity, "subjects", 0) / PER_MILLE)
    tenure = await law_param(ctx.session, row.steward_entity_id, LawKind.LAND_TENURE, "tenure")
    law = {FREEHOLD: table.freehold_pct, COMMUNAL: table.communal_pct}.get(str(tenure), PERCENT) / PERCENT
    if ctx.rng(f"commons.enclose.{row.id}.{ctx.epoch}").chance(table.enclose_pct * eager * profit * law):
        roll = ctx.rng(f"commons.take.{row.id}.{ctx.epoch}").below(PERCENT)
        if roll < table.state_take_pct and row.rule not in QUOTA_RULES:
            await take_common(ctx, row, CommonsRule.STATE)
            return
        if roll < table.state_take_pct + table.licensed_take_pct and row.rule not in QUOTA_RULES:
            await take_common(ctx, row, CommonsRule.LICENSED)
            return
        order = await issue(ctx, realm, MandateKind.ENCLOSURE, settlement_id=row.steward_entity_id)
        if order is not None and order.issuer_node_id is not None:
            orders[row.steward_entity_id] = order.issuer_node_id


async def enclosure_orders(ctx: TickContext) -> dict[int, int]:
    rows = await ctx.session.execute(
        select(MandateRow.settlement_entity_id, MandateRow.issuer_node_id).where(
            MandateRow.kind == MandateKind.ENCLOSURE, MandateRow.state == MandateState.ACTIVE, MandateRow.settlement_entity_id.is_not(None)
        )
    )
    return {town: issuer for town, issuer in rows.all() if town is not None and issuer is not None}


async def obey_orders(ctx: TickContext, lands: Holdings, row: CommonsRow, orders: dict[int, int], *, book: RealmBook, tally: LandsTally) -> None:
    issuer_id = orders.get(row.steward_entity_id) if row.steward_entity_id is not None else None
    if issuer_id is None or row.rule is CommonsRule.ENCLOSED or "rule" in row.locked:
        return
    encloser = await ctx.session.get(EntityRow, issuer_id)
    if encloser is None or held(encloser.id):
        return
    tally.enclosed += 1
    tally.dispossessed += await enclose(ctx, lands, row, encloser, book)


async def reserve_land(ctx: TickContext, lands: Holdings, rows: list[GameReserveRow], tally: LandsTally) -> None:
    table = ctx.rules.game_laws
    reserved = {row.region_entity_id for row in rows}
    houses = await ctx.session.execute(
        select(EntityRow, HouseProfileRow)
        .join(HouseProfileRow, HouseProfileRow.house_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON, HouseProfileRow.wealth >= table.wealth_at)
        .order_by(EntityRow.id)
    )
    for house, profile in houses.all():
        seat = next(iter(profile.seats), None)
        region_id = lands.atlas.top_region(seat) if seat is not None else None
        land = lands.lands.get(region_id) if region_id is not None else None
        if region_id is None or land is None or region_id in reserved or held(region_id, house.id) or land.forest_cover < table.forest_at:
            continue
        if not ctx.rng(f"game.reserve.{house.id}.{ctx.epoch}").chance(table.reserve_pct):
            continue
        quarry = await ctx.session.scalar(
            select(SpeciesRangeRow.species_entity_id)
            .where(SpeciesRangeRow.region_entity_id == region_id, SpeciesRangeRow.abundance > 0)
            .order_by(SpeciesRangeRow.abundance.desc(), SpeciesRangeRow.species_entity_id)
            .limit(1)
        )
        row = GameReserveRow(region_entity_id=region_id, holder_node_id=house.id, species_entity_id=quarry, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
        rows.append(row)
        reserved.add(region_id)
        tally.reserves += 1
        await record(
            ctx,
            "game.reserved",
            roles={IncidentRole.OWNER: house.id, IncidentRole.PLACE: region_id, IncidentRole.SUBJECT: quarry},
            facts={"strictness": row.strictness},
            steps=(StepDraft(StepAction.DECREE, actor=house.id, target=region_id),),
            place=region_id,
        )


async def charge_poacher(ctx: TickContext, towns: list[EntityRow], row: GameReserveRow) -> None:
    for town in towns:
        poacher = await ctx.session.scalar(
            select(EntityRow)
            .where(
                EntityRow.entity_type == EntityType.MORTAL,
                EntityRow.status == EntityStatus.CANON,
                await present_in(ctx.session, town),
                EntityRow.id != (row.holder_node_id or 0),
            )
            .order_by(EntityRow.id)
            .limit(1)
        )
        if poacher is not None and not held(poacher.id):
            await report_crime(ctx, town.id, poacher.id, CrimeKind.THEFT)
            return


async def keep_reserves(ctx: TickContext, lands: Holdings, tally: LandsTally) -> None:
    table = ctx.rules.game_laws
    rows = list(await ctx.session.scalars(select(GameReserveRow).order_by(GameReserveRow.id)))
    await reserve_land(ctx, lands, rows, tally)
    for row in rows:
        if held(row.region_entity_id):
            continue
        land = lands.lands.get(row.region_entity_id)
        towns = [town for town in lands.towns.get(row.region_entity_id, []) if not held(town.id)]
        hunger = max(0, PERCENT - land.harvest_pct) if land is not None else 0
        wealth = sum(stat_or(town, "prosperity", HALF) for town in towns) / len(towns) if towns else HALF
        poverty = max(0.0, HALF - wealth)
        aim = (hunger * table.hunger_poach + poverty * table.poverty_poach) / PERCENT * (1 - row.strictness / PERCENT * table.deter_pct / PERCENT)
        shift(row, "poaching", (clamp_int(aim, 0, PERCENT) - row.poaching) * table.drift_pct / PERCENT)
        grudge = clamp_int(row.strictness * row.poaching / PERCENT * table.resentment_pct / PERCENT, 0, PERCENT)
        shift(row, "resentment", (grudge - row.resentment) * table.drift_pct / PERCENT)
        if row.poaching > 0:
            tally.poaching += 1
        for town in towns:
            profile = lands.profiles.get(town.id)
            if profile is not None:
                shift(profile, "crime", row.poaching / PERCENT * table.crime_pct)
            if row.holder_node_id is not None and row.resentment > 0:
                await regard(ctx, (town.id, row.holder_node_id), -table.regard_loss * row.resentment / PERCENT, MemoryKind.HARMED_ME, "kept the game from us")
        if row.poaching >= table.punish_at and row.strictness >= STRICT and towns:
            for town in towns:
                profile = lands.profiles.get(town.id)
                if profile is not None:
                    shift(profile, "unrest", table.unrest_gain)
            await charge_poacher(ctx, towns, row)
            await record(
                ctx,
                "game.poachers_punished",
                roles={IncidentRole.OWNER: row.holder_node_id, IncidentRole.PLACE: row.region_entity_id, IncidentRole.MEMBER: [town.id for town in towns]},
                facts={"poaching": row.poaching, "resentment": row.resentment, "unrest": table.unrest_gain},
                steps=(StepDraft(StepAction.PUNISH, actor=row.holder_node_id),),
                place=row.region_entity_id,
            )


async def keep_lands(ctx: TickContext, tally: LandsTally) -> None:
    lands = await holdings(ctx)
    await plant(ctx, lands, tally)
    await grow(ctx, lands, tally)
    await keep_commons(ctx, lands, tally)
    await keep_reserves(ctx, lands, tally)
    await ctx.session.flush()
