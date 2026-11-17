from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.grammar import several, spoken
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
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import CoastKind, RiverClass
from aerona.domain.enums.living import LineTrait
from aerona.domain.enums.mind import ActKind, MemoryKind
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.statecraft import MandateKind, MandateState
from aerona.engine.agrarian.rings import put
from aerona.engine.collective.book import shift
from aerona.engine.context import TickContext
from aerona.engine.cycles.standing import regard
from aerona.engine.economy.purse import give_coin
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.living.traits import eased, traits_of
from aerona.engine.lore.civics import holders_know
from aerona.engine.mind.hooks import judged
from aerona.engine.notes import note
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.laws import law_param
from aerona.engine.polity.mandates import issue
from aerona.engine.polity.trials import report_crime
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_in
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat, stat_or

LONG_LIVED = frozenset({GrowthCycle.PERENNIAL, GrowthCycle.TREE})
CITY_TIERS = frozenset({SizeTier.TOWN, SizeTier.CITY, SizeTier.METROPOLIS, SizeTier.MEGALOPOLIS, SizeTier.WORLD_CITY})
CASH_CROPS = frozenset({CommodityKind.FIBRE, CommodityKind.DYE, CommodityKind.LUXURIES, CommodityKind.INCENSE, CommodityKind.HERBS})
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
        },
    )[kind]


def kind_of(yields: set[CommodityKind], land: RegionEnvironmentRow | None, forest: int) -> PerennialKind:
    if yields & CASH_CROPS:
        return PerennialKind.PLANTATION
    if land is not None and land.forest_cover >= forest and CommodityKind.FRUIT in yields:
        return PerennialKind.FOREST_GARDEN
    return next((kind for commodity, kind in YIELD_KINDS if commodity in yields), PerennialKind.GROVE)


KIND_TOLL: Mapping[PerennialKind, tuple[int, str, int]] = total(
    PerennialKind,
    {
        PerennialKind.ORCHARD: (100, "soil_fertility", 0),
        PerennialKind.VINEYARD: (110, "soil_fertility", 0),
        PerennialKind.GROVE: (90, "soil_fertility", 0),
        PerennialKind.TIMBER: (100, "forest_cover", 1),
        PerennialKind.PLANTATION: (150, "soil_fertility", -1),
        PerennialKind.FOREST_GARDEN: (70, "forest_cover", 1),
    },
)


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
        plant_entity = await ctx.session.get(EntityRow, plant_id)
        region = await ctx.session.get(EntityRow, region_id)
        if plant_entity is not None and region is not None:
            await note(
                ctx,
                f"{owner.name} planted {plant_entity.name} in {region.name}; the {spoken(kind)} will bear in {several(epochs, 'epoch', 'epochs')}.",
                key="perennials.planted",
                ids=[owner.id, region.id],
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
            coin_pct, field, toll = KIND_TOLL[row.kind]
            earned = row.area * table.coin_per_area * row.condition / PERCENT * max(0, bred) / PERCENT * coin_pct / PERCENT
            await give_coin(ctx.session, ctx.rules, owner, round_half_up(earned))
            land = lands.lands.get(row.region_entity_id)
            if toll and land is not None and field not in land.locked:
                setattr(land, field, clamp_int(getattr(land, field) + toll, 0, PERCENT))
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
    region = await ctx.session.get(EntityRow, row.region_entity_id)
    epochs_counted = several(row.mature_epochs, "epoch", "epochs")
    await note(
        ctx,
        f"The old {spoken(row.kind)} of {region.name if region else 'the land'} was worn out and planted anew; it will bear again in {epochs_counted}.",
        key="perennials.replanted",
        ids=[row.region_entity_id],
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
    holders = [town.id for town in towns]
    if await holders_know(ctx.session, holders, Technique.RADIO):
        kinds.append(CommonsKind.SPECTRUM)
    if await holders_know(ctx.session, holders, Technique.ROCKETRY):
        kinds.append(CommonsKind.ORBITS)
    return kinds


COMMONS_BOON: Mapping[CommonsKind, tuple[str, int]] = total(
    CommonsKind,
    {
        CommonsKind.PASTURE: ("prosperity", 1),
        CommonsKind.WOODS: ("construction_capacity", 2),
        CommonsKind.FISHERY: ("prosperity", 1),
        CommonsKind.WATER: ("sanitation", 1),
        CommonsKind.HUNTING_GROUND: ("prosperity", 1),
        CommonsKind.QUARRY: ("construction_capacity", 3),
        CommonsKind.SPECTRUM: ("prestige", 1),
        CommonsKind.ORBITS: ("prestige", 2),
        CommonsKind.SOURCE_GROUND: ("public_order", 1),
    },
)


def bestow(row: CommonsRow, town: EntityRow, profile: SettlementProfileRow | None) -> None:
    field, amount = COMMONS_BOON[row.kind]
    gain = amount * row.condition // PERCENT
    if field == "prosperity":
        shift_stat(town, field, gain)
    elif profile is not None and field not in profile.locked:
        setattr(profile, field, clamp_int(getattr(profile, field) + gain, 0, PERCENT * 100 if field == "construction_capacity" else PERCENT))


def wear_share(ctx: TickContext, rule: CommonsRule) -> int:
    table = ctx.rules.commons
    return {CommonsRule.COUNCIL: table.council_pct, CommonsRule.ENCLOSED: table.enclosed_pct}.get(rule, PERCENT)


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
    region = await ctx.session.get(EntityRow, row.region_entity_id)
    went = f" and went to {city.name} for work" if city is not None else " and were left without homes"
    cottagers_counted = several(driven, "cottager", "cottagers")
    await note(
        ctx,
        f"{encloser.name} enclosed the common {spoken(row.kind)} of {region.name if region else 'the land'}; {cottagers_counted} lost their living{went}.",
        key="commons.enclosed",
        ids=[encloser.id, *([city.id] if city is not None else []), *[town.id for town in towns]],
    )
    return driven


def realm_dispossessed(rows: list[CommonsRow], book: RealmBook, realm_id: int) -> int:
    return sum(row.dispossessed for row in rows if row.steward_entity_id is not None and book.member_of.get(row.steward_entity_id) == realm_id)


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
        if row.use > table.sustainable:
            shift(row, "condition", -(row.use - table.sustainable) * table.degrade_pct / PERCENT * wear_share(ctx, row.rule) / PERCENT)
        else:
            shift(row, "condition", table.regrow)
        if row.rule is not CommonsRule.ENCLOSED:
            for town in lands.towns.get(row.region_entity_id, []):
                if not held(town.id):
                    shift_stat(town, "prosperity", (row.condition - HALF) / HALF * table.prosperity_weight)
                    bestow(row, town, lands.profiles.get(town.id))
        steward = lands.profiles.get(row.steward_entity_id) if row.steward_entity_id is not None else None
        if (
            row.rule in (CommonsRule.OPEN, CommonsRule.CUSTOMARY)
            and row.condition < table.council_at
            and steward is not None
            and steward.public_order >= table.council_order
            and ctx.rng(f"commons.council.{row.id}.{ctx.epoch}").chance(table.council_chance)
        ):
            put(row, "rule", CommonsRule.COUNCIL)
            tally.councils += 1
            steward_town = await ctx.session.get(EntityRow, row.steward_entity_id)
            if steward_town is not None:
                await note(
                    ctx,
                    f"The folk of {steward_town.name} formed a council to rule the use of their common {spoken(row.kind)}.",
                    key="commons.council",
                    ids=[steward_town.id],
                )
        await maybe_enclose(ctx, row, rows=rows, book=book, orders=orders)
        await obey_orders(ctx, lands, row, orders, book=book, tally=tally)
        if row.rule is CommonsRule.ENCLOSED and row.encloser_node_id is not None:
            owner = await ctx.session.get(EntityRow, row.encloser_node_id)
            if owner is not None and not held(owner.id):
                await give_coin(ctx.session, ctx.rules, owner, round_half_up(table.enclosed_coin * row.condition / PERCENT))


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
    profit = 1 + realm_dispossessed(rows, book, realm.entity.id) / table.labour_span
    tenure = await law_param(ctx.session, row.steward_entity_id, LawKind.LAND_TENURE, "tenure")
    law = {FREEHOLD: table.freehold_pct, COMMUNAL: table.communal_pct}.get(str(tenure), PERCENT) / PERCENT
    if ctx.rng(f"commons.enclose.{row.id}.{ctx.epoch}").chance(table.enclose_pct * eager * profit * law):
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
        region = await ctx.session.get(EntityRow, region_id)
        await note(
            ctx,
            f"{house.name} reserved the game of {region.name if region else 'its land'} for its own hunts; the folk may no longer hunt there.",
            key="game.reserved",
            ids=[house.id, region_id],
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
            region = await ctx.session.get(EntityRow, row.region_entity_id)
            await note(
                ctx,
                f"Poachers were caught in the reserve of {region.name if region else 'the land'} and punished; the folk of the land resent the game laws.",
                key="game.poachers_punished",
                ids=[town.id for town in towns],
            )


async def keep_lands(ctx: TickContext, tally: LandsTally) -> None:
    lands = await holdings(ctx)
    await plant(ctx, lands, tally)
    await grow(ctx, lands, tally)
    await keep_commons(ctx, lands, tally)
    await keep_reserves(ctx, lands, tally)
    await ctx.session.flush()
