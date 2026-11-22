from collections import Counter

from sqlalchemy import select

from aerona.catalog.methods import METHODS
from aerona.catalog.production import STEPS
from aerona.constants.units import PERCENT
from aerona.db.tables.culture import HolderTechniqueRow, IdeologyAdherentRow, IdeologyTenetRow
from aerona.db.tables.demography import LabourRow
from aerona.db.tables.economy import CommunityStockRow, ProductionRunRow, ResourceProfileRow, WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.factions import FactionGoalRow, FactionProfileRow
from aerona.db.tables.industry import CommunityMethodRow, RegionPollutionRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.orders import EconomicOrderRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.culture import IdeologyTenet, Technique
from aerona.domain.enums.demography import Job
from aerona.domain.enums.economy import CommodityKind, HazardKind, WorkshopKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import CoastKind, RiverClass, TemperatureBand, TerrainKind
from aerona.domain.enums.faction import FactionGoalKind, FactionKind
from aerona.domain.enums.industry import EnergyKind, MethodKind, Pollutant, ProcessKind, QualityTier
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.orders import OwnershipRegime
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.world import TechnologyEra
from aerona.domain.models.entity_stats import FactionStats, IdeologyStats, PolityStats
from aerona.engine.commerce.trade import without_shops
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.extraction import shaft_factor
from aerona.engine.economy.household import Wear, burn_substitutes, field_shares, warmed
from aerona.engine.economy.refining import RefiningTally, refine_community
from aerona.engine.economy.refining import lit as lit_factor
from aerona.engine.economy.stocks import holding
from aerona.engine.industry.energy import draw, gauge, industry_row, survival_heat, unmet_pct
from aerona.engine.industry.fuels import lay_coal_seams
from aerona.engine.industry.methods import (
    MethodTally,
    adopt,
    allowed,
    choose_methods,
    feed,
    newest_tier,
    outdated,
    owner_reveres,
    profit,
    reveres_nature,
    step_method,
)
from aerona.engine.industry.owners import ProfitTally, barred_works, buy, pass_commons, tend_profits
from aerona.engine.industry.pollution import PollutionTally, disease_extra, fertility_factor, fish_factor, tend_pollution, void_scar
from aerona.engine.industry.quality import premium, tier_of
from aerona.engine.industry.stores import StoreTally, kindle, preserve, spoil, wear_tools
from aerona.engine.pipeline import TICK_ORDER
from aerona.engine.primitives.stats import set_stats
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, make, mortal, settlement
from tests.engine.society.factories import tuned as tuned_rules

RULES = Rules()


def ground(realm: Realm, **values: object) -> RegionEnvironmentRow:
    base: dict[str, object] = {
        "entity_id": realm.region.id,
        "world_id": realm.world.id,
        "river_class": RiverClass.RIVER,
        "coast_kind": CoastKind.NONE,
        "roughness": 20,
        "forest_cover": 0,
        "wetland": 0,
        "temperature_band": TemperatureBand.TEMPERATE,
        "rainfall": 50,
        "magic_density": 0,
        "seasonality": 40,
        "soil_fertility": 60,
        "moisture": 50,
        "base_forest": 0,
        "base_wetland": 0,
        "temperature": 50,
        "latitude": 30,
        "dominant_terrain": TerrainKind.PLAIN,
        "scars": {},
        "disease_load": 0,
        "locked": [],
    }
    base.update(values)
    return RegionEnvironmentRow(**base)


async def loaded(realm: Realm, **land: object) -> EconomyBook:
    book = await EconomyBook.load(context(realm.session))
    book.ground.regions[realm.region.id] = ground(realm, **land)
    return book


def test_goods_fall_into_seven_tiers_with_prices_by_tier() -> None:
    assert tier_of(RULES, 5) is QualityTier.POOR
    assert tier_of(RULES, 30) is QualityTier.COMMON
    assert tier_of(RULES, 50) is QualityTier.FINE
    assert tier_of(RULES, 99) is QualityTier.ARTIFACT
    assert premium(RULES, 5) < premium(RULES, 30) == 1.0 < premium(RULES, 92)
    assert survival_heat(RULES, 1000, TemperatureBand.FROZEN) > survival_heat(RULES, 1000, TemperatureBand.COLD) > 0
    assert survival_heat(RULES, 1000, TemperatureBand.TEMPERATE) == 0


async def test_a_place_takes_up_a_better_method_displaces_artisans_and_stirs_its_guild(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Forgeholm")
    realm.session.add(WorkshopRow(community_entity_id=town.id, kind=WorkshopKind.FORGE, level=2, built_epoch=1))
    realm.session.add(HolderTechniqueRow(holder_entity_id=town.id, technique=Technique.STEEL))
    realm.session.add(LabourRow(community_entity_id=town.id, job=Job.CRAFTING, workers=200, output_pct=100, epoch=1))
    guild = await make(realm.session, "Smiths", EntityType.FACTION, FactionStats(strength=30), world_id=realm.world.id)
    realm.session.add(FactionProfileRow(faction_entity_id=guild.id, kind=FactionKind.CRAFT_GUILD, home_entity_id=town.id))
    realm.session.add(CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.FUEL, quantity=400, quality=50))
    realm.session.add(CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.COAL, quantity=400, quality=50))
    await realm.session.flush()
    book = await loaded(realm)
    row = await gauge(ctx, book, town, leys=Counter())
    assert row.heat > 0 and row.water > 0 and row.muscle > 0
    await adopt(ctx, book, town, METHODS[MethodKind.BLOOMERY], MethodTally())
    set_stats(town, wealth=0)
    await choose_methods(ctx, book, town, MethodTally())
    dated = book.methods[town.id][ProcessKind.SMELTING]
    assert dated.method is MethodKind.BLOOMERY and dated.obsolete_since == ctx.epoch
    assert outdated(book, ctx.rules, town.id, ProcessKind.SMELTING) == 1 - ctx.rules.discovery.obsolete_pct / 100
    set_stats(town, wealth=PERCENT)
    tally = MethodTally()
    await choose_methods(ctx, book, town, tally)
    chosen = book.methods[town.id][ProcessKind.SMELTING]
    assert chosen.obsolete_since is None
    assert chosen.method is MethodKind.BLAST_FURNACE and chosen.displaced > 0 and tally.changed >= 1
    assert book.labour[town.id][Job.IDLE].workers == chosen.displaced
    goal = await realm.session.scalar(select(FactionGoalRow).where(FactionGoalRow.faction_entity_id == guild.id))
    assert goal is not None and goal.kind is FactionGoalKind.PROTECT_CRAFT and goal.progress > 0
    held = book.methods[town.id][ProcessKind.FARMING]
    held.locked = ["method"]
    held.method = MethodKind.HAND_SICKLE
    await choose_methods(ctx, book, town, MethodTally())
    assert held.method is MethodKind.HAND_SICKLE


async def test_a_creed_of_harmony_with_nature_weighs_pollution_against_profit(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Greenwick")
    book = await loaded(realm)
    industry_row(ctx, book, town.id).heat = 100
    furnace = METHODS[MethodKind.BLAST_FURNACE]
    assert profit(ctx, book, town, furnace, nature=True) < profit(ctx, book, town, furnace, nature=False)
    creed = await make(realm.session, "Way of Roots", EntityType.IDEOLOGY, IdeologyStats(), world_id=realm.world.id)
    realm.session.add(IdeologyTenetRow(ideology_entity_id=creed.id, tenet=IdeologyTenet.NATURE_HARMONY))
    realm.session.add(IdeologyAdherentRow(ideology_entity_id=creed.id, adherent_entity_id=town.id, state=True))
    await realm.session.flush()
    assert await reveres_nature(ctx, town.id)


async def test_energy_is_drawn_until_it_runs_short(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Millbrook")
    book = await loaded(realm)
    row = industry_row(ctx, book, town.id)
    row.water = 5
    assert draw(book, town.id, EnergyKind.WATER, 8) == 5
    assert row.short == {"water": 3} and row.spent == {"water": 5}
    assert unmet_pct(row, EnergyKind.WATER) == 38


async def test_perishables_spoil_unless_preserved_and_work_wears_tools(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Saltmarsh")
    fish = CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.FISH, quantity=200, quality=50)
    realm.session.add(CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.ORE, material=MaterialKind.SALT, quantity=50, quality=50))
    tools = CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.TOOLS, quantity=50, quality=50)
    realm.session.add_all([fish, tools])
    realm.session.add(
        ProductionRunRow(
            epoch=ctx.epoch,
            community_entity_id=town.id,
            step="forge_tools",
            output=CommodityKind.TOOLS,
            quantity=10,
            quality=50,
            inputs={},
            workers=200,
            method=MethodKind.PICK_AND_SHOVEL,
        )
    )
    await realm.session.flush()
    book = await loaded(realm)
    row = industry_row(ctx, book, town.id)
    row.muscle = 100
    tally = StoreTally()
    kept = await preserve(ctx, book, town, row, tally)
    assert kept > 0 and fish.preserved == kept
    lost = await spoil(ctx, book, town, row, tally)
    assert 0 < lost < 200 - kept and fish.quantity == 200 - lost and row.spoiled == lost
    worn = await wear_tools(ctx, book, town, row, tally)
    assert worn > 0 and tools.quantity == 50 - worn


async def test_works_and_crowds_foul_the_land_which_sickens_and_yields_less(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Smokeby", population=40000)
    realm.session.add(
        ProductionRunRow(
            epoch=ctx.epoch,
            community_entity_id=town.id,
            step="forge_tools",
            output=CommodityKind.TOOLS,
            quantity=200,
            quality=50,
            inputs={},
            workers=20,
            method=MethodKind.BLAST_FURNACE,
        )
    )
    await realm.session.flush()
    book = await loaded(realm)
    tally = PollutionTally()
    await tend_pollution(ctx, book, tally)
    row = book.pollution[realm.region.id]
    assert row.air > 0 and row.soil > 0 and row.polluters == {str(town.id): 120}
    row.air, row.water, row.soil = 50, 80, 90
    assert fertility_factor(RULES, row) < 1 and fish_factor(RULES, row) < 1 and disease_extra(RULES, row) > 0
    await tend_pollution(ctx, book, PollutionTally())
    assert book.ground.regions[realm.region.id].scars.get("blighted", 0) > 0
    stored = await realm.session.get(RegionPollutionRow, realm.region.id)
    assert stored is not None and Pollutant.SOIL.value not in stored.locked


async def test_owners_take_profit_after_costs_and_taxes_and_lobby_when_taxed(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Tollcross")
    realm.session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, tax_rate=40, treasury=0, investment_pool=0))
    guild = await make(realm.session, "Hammerers", EntityType.FACTION, FactionStats(strength=30), world_id=realm.world.id)
    realm.session.add(FactionProfileRow(faction_entity_id=guild.id, kind=FactionKind.CRAFT_GUILD, home_entity_id=town.id, treasury=0))
    forge = WorkshopRow(community_entity_id=town.id, kind=WorkshopKind.FORGE, level=1, built_epoch=1)
    realm.session.add(forge)
    await realm.session.flush()
    realm.session.add(
        ProductionRunRow(
            epoch=ctx.epoch,
            community_entity_id=town.id,
            step="forge_tools",
            workshop=WorkshopKind.FORGE,
            output=CommodityKind.TOOLS,
            quantity=40000,
            quality=60,
            inputs={"ore": 5000},
            workers=20,
            method=MethodKind.BLOOMERY,
        )
    )
    await realm.session.flush()
    book = await loaded(realm)
    tally = ProfitTally()
    rows = await tend_profits(ctx, book, tally)
    assert forge.owner_node_id == guild.id and tally.owned == 1
    assert len(rows) == 1 and rows[0].owner_node_id == guild.id and rows[0].taxes > 0 and rows[0].revenue > rows[0].inputs
    profile = await realm.session.get(FactionProfileRow, guild.id)
    town_profile = await realm.session.get(SettlementProfileRow, town.id)
    assert profile is not None and town_profile is not None
    assert town_profile.treasury == rows[0].taxes and town_profile.investment_pool == rows[0].invested
    assert profile.treasury == max(0, rows[0].profit - rows[0].invested)
    goal = await realm.session.scalar(select(FactionGoalRow).where(FactionGoalRow.faction_entity_id == guild.id))
    assert goal is not None and goal.kind is FactionGoalKind.LOWER_TAXES and tally.lobbied == 1
    buyer = await settlement(realm, "Coinford")
    realm.session.add(SettlementProfileRow(settlement_entity_id=buyer.id, size_tier=SizeTier.TOWN, treasury=500))
    await realm.session.flush()
    assert await buy(ctx, forge, buyer.id) == RULES.ownership.price_per_level and forge.owner_node_id == buyer.id


async def test_magic_bans_bar_magic_methods_and_deep_soft_mines_cave_in_more(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Hexley")
    book = await loaded(realm)
    industry_row(ctx, book, town.id).magic = 50
    alembic = METHODS[MethodKind.ARCANE_ALEMBIC]
    assert "forbids magic" in (allowed(book, town, alembic, banned=True) or "")
    assert barred_works(book, {town.id}) == {town.id}
    fresh = ResourceProfileRow(commodity=CommodityKind.ORE, reserve=100, initial_reserve=100, richness=50, extraction_difficulty=50, quality=50)
    spent = ResourceProfileRow(commodity=CommodityKind.ORE, reserve=10, initial_reserve=100, richness=50, extraction_difficulty=50, quality=50)
    shallow = shaft_factor(ctx, book, realm.region, fresh, community=town, hazard=HazardKind.CAVE_IN)
    deep = shaft_factor(ctx, book, realm.region, spent, community=town, hazard=HazardKind.CAVE_IN)
    assert deep > shallow > 0
    await adopt(ctx, book, town, METHODS[MethodKind.PUMPED_SHAFTS], MethodTally())
    dry = shaft_factor(ctx, book, realm.region, spent, community=town, hazard=HazardKind.FLOODED_SHAFT)
    assert dry < shaft_factor(ctx, book, realm.region, spent, community=town, hazard=HazardKind.CAVE_IN)


async def test_methods_take_their_inputs_and_hands_light_lifts_work_and_magic_stands_in_for_fuel(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Lampwick")
    realm.session.add(CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.COAL, quantity=30, quality=50))
    realm.session.add(CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.LIVESTOCK, quantity=100, quality=50))
    realm.session.add(WorkshopRow(community_entity_id=town.id, kind=WorkshopKind.WAREHOUSE, level=2, built_epoch=1))
    await realm.session.flush()
    book = await loaded(realm)
    furnace = METHODS[MethodKind.BLAST_FURNACE]
    assert furnace.labour_pct < 100 and furnace.inputs
    assert await feed(ctx, town.id, furnace, 100) == 1.0
    coal = await realm.session.scalar(
        select(CommunityStockRow).where(CommunityStockRow.community_entity_id == town.id, CommunityStockRow.commodity == CommodityKind.COAL)
    )
    assert coal is not None and coal.quantity == 20
    assert await feed(ctx, town.id, furnace, 400) == 0.5
    row = industry_row(ctx, book, town.id)
    row.magic = 40
    assert draw(book, town.id, EnergyKind.HEAT, 10) == 10 and row.spent["magic"] > 0
    assert allowed(book, town, METHODS[MethodKind.ICING]) is None
    row.muscle = 50
    lit = await kindle(ctx, book, town, row)
    assert lit > 0 and row.light == lit
    assert lit_factor(ctx, book, town.id) > 1


async def test_owners_who_love_nature_shun_fouling_methods_and_void_rites_foul_the_land(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Fernhollow")
    await realm.session.flush()
    assert not await owner_reveres(ctx, town.id, {})
    fouled = await void_scar(ctx, town.id)
    stored = await realm.session.get(RegionPollutionRow, realm.region.id)
    assert fouled > 0 and stored is not None and stored.air == RULES.pollution.void_rite and stored.soil == RULES.pollution.void_rite


async def test_harvests_bring_tubers_fruit_milk_and_dung_and_households_burn_other_fuels(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Rootmoor")
    realm.session.add(CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.PEAT, quantity=200, quality=50))
    await realm.session.flush()
    book = await loaded(realm, temperature_band=TemperatureBand.COLD, soil_fertility=20, moisture=60)
    tubers, fruit = field_shares(ctx, book, town)
    assert tubers == RULES.food_chain.tuber_cold_pct / 100 and fruit == 0.0
    warm = await loaded(realm, temperature_band=TemperatureBand.WARM, soil_fertility=70, moisture=70)
    assert field_shares(ctx, warm, town)[1] > 0
    covered = await burn_substitutes(ctx, town, 30)
    peat = await realm.session.scalar(
        select(CommunityStockRow).where(CommunityStockRow.community_entity_id == town.id, CommunityStockRow.commodity == CommodityKind.PEAT)
    )
    assert covered == 30 and peat is not None and peat.quantity < 200


async def test_food_chain_steps_and_coal_seams_exist_and_meat_spoils_unless_preserved(realm: Realm) -> None:
    ctx = context(realm.session)
    assert {"butcher", "cheese", "press_fruit"} <= set(STEPS)
    assert STEPS["cheese"].output is CommodityKind.CHEESE and STEPS["butcher"].output is CommodityKind.MEAT
    assert METHODS[MethodKind.BLAST_FURNACE].inputs[0][0] is CommodityKind.COAL
    town = await settlement(realm, "Smokehollow")
    meat = CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.MEAT, quantity=100, quality=50)
    realm.session.add(meat)
    await realm.session.flush()
    book = await loaded(realm, base_forest=80, base_wetland=40)
    row = industry_row(ctx, book, town.id)
    assert await spoil(ctx, book, town, row, StoreTally()) > 0 and meat.quantity < 100
    laid = await lay_coal_seams(context(realm.session, tuned_rules(mines={"coal_seam_pct": 100})), book)
    seam = await realm.session.scalar(select(ResourceProfileRow).where(ResourceProfileRow.commodity == CommodityKind.COAL))
    assert laid >= 1 and seam is not None and not seam.revealed


async def test_a_place_never_chooses_a_method_it_cannot_run_for_want_of_power_or_inputs(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Shrinewell")
    realm.session.add(WorkshopRow(community_entity_id=town.id, kind=WorkshopKind.SHRINE_WORKSHOP, level=1, built_epoch=1))
    realm.session.add(LabourRow(community_entity_id=town.id, job=Job.FARMING, workers=2000, output_pct=100, epoch=1))
    await realm.session.flush()
    book = await loaded(realm)
    row = await gauge(ctx, book, town, leys=Counter())
    assert 0 < row.divine < METHODS[MethodKind.DIVINE_HARVEST].energy_need * 20
    assert allowed(book, town, METHODS[MethodKind.DIVINE_HARVEST]) is None
    await choose_methods(ctx, book, town, MethodTally())
    assert book.methods[town.id][ProcessKind.FARMING].method is not MethodKind.DIVINE_HARVEST
    realm.session.add(CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.INCENSE, quantity=5000, quality=50))
    row.divine = 5000
    set_stats(town, wealth=PERCENT)
    await realm.session.flush()
    await choose_methods(ctx, book, town, MethodTally())
    assert book.methods[town.id][ProcessKind.FARMING].method is MethodKind.DIVINE_HARVEST


async def modern_town(realm: Realm, name: str, techniques: tuple[Technique, ...]) -> EntityRow:
    town = await settlement(realm, name)
    for kind in (WorkshopKind.CHARCOAL_KILN, WorkshopKind.WEAVERY):
        realm.session.add(WorkshopRow(community_entity_id=town.id, kind=kind, level=2, built_epoch=1))
    for technique in techniques:
        realm.session.add(HolderTechniqueRow(holder_entity_id=town.id, technique=technique))
    realm.session.add(LabourRow(community_entity_id=town.id, job=Job.CRAFTING, workers=600, output_pct=100, epoch=1))
    realm.session.add(CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.COAL, quantity=400, quality=50))
    realm.session.add(
        CommunityMethodRow(community_node_id=town.id, process=ProcessKind.CHARCOAL, method=MethodKind.OIL_REFINING, adopted_epoch=1, displaced=0, locked=[])
    )
    await realm.session.flush()
    return town


async def test_a_modern_place_makes_fuel_without_timber_and_cloth_without_livestock(realm: Realm) -> None:
    ctx = context(realm.session)
    modern = await modern_town(realm, "Gridhaven", (Technique.COKE_SMELTING, Technique.INDUSTRIAL_CHEMISTRY, Technique.ELECTRICITY))
    old = await modern_town(realm, "Oldhaven", (Technique.IRON,))
    book = await loaded(realm)
    for town in (modern, old):
        row = industry_row(ctx, book, town.id)
        row.heat, row.electric = 500, 500
    assert step_method(book, old.id, "charcoal") is None
    oil = step_method(book, modern.id, "coal_fuel")
    assert oil is not None and oil.kind is MethodKind.OIL_REFINING
    tally = RefiningTally()
    await refine_community(ctx, book, modern, tally)
    await refine_community(ctx, book, old, tally)
    await realm.session.flush()
    runs = list(await realm.session.scalars(select(ProductionRunRow).order_by(ProductionRunRow.id)))
    made = {run.step for run in runs if run.community_entity_id == modern.id and run.quantity > 0}
    assert made & {"coke_fuel", "coal_fuel"} and "synthetic_cloth" in made
    fuel_runs = [run for run in runs if run.community_entity_id == modern.id and run.output is CommodityKind.FUEL and run.quantity > 0]
    assert fuel_runs and all(run.method is MethodKind.OIL_REFINING for run in fuel_runs)
    assert not [run for run in runs if run.step == "synthetic_cloth" and run.method is MethodKind.HAND_LOOM]
    assert not {"charcoal", "gather_fuel", "weave", "spin", "tan_hides"} & made
    assert not [run for run in runs if run.community_entity_id == modern.id and run.bottleneck is not None]
    assert await holding(realm.session, modern.id, CommodityKind.CLOTH) > 0
    assert book.industry[modern.id].spent.get("electric", 0) > 0
    assert all(shop.idle_epochs == 0 for shop in book.workshops[modern.id].values())
    old_short = {run.bottleneck for run in runs if run.community_entity_id == old.id and run.bottleneck is not None}
    assert CommodityKind.TIMBER in old_short
    assert not [run for run in runs if run.community_entity_id == old.id and run.quantity > 0 and run.step in {"coke_fuel", "coal_fuel", "synthetic_cloth"}]


def test_a_world_begun_in_an_age_chooses_only_among_the_methods_of_its_newest_tier() -> None:
    farming = [METHODS[kind] for kind in (MethodKind.HAND_SICKLE, MethodKind.CULTURED_CROPS, MethodKind.HYDROPONICS, MethodKind.MOTOR_TRACTORS)]
    assert {spec.kind for spec in newest_tier(farming, TechnologyEra.INFORMATION)} == {MethodKind.HYDROPONICS, MethodKind.MOTOR_TRACTORS}
    assert newest_tier(farming[:2], TechnologyEra.INFORMATION) == farming[:2]
    keeping = [METHODS[MethodKind.MAGIC_KEEPING], METHODS[MethodKind.REFRIGERATION_HALLS]]
    assert newest_tier(keeping, TechnologyEra.INFORMATION) == [METHODS[MethodKind.REFRIGERATION_HALLS]]
    assert newest_tier(keeping, TechnologyEra.IRON) == keeping


def test_works_of_the_starting_age_stand_before_the_first_economy() -> None:
    order = [phase.name for phase in TICK_ORDER]
    assert order.index("works_in_age") < order.index("industry_methods") < order.index("society_economy") < order.index("refining")


async def test_a_home_warmed_by_power_lacks_neither_heat_nor_cloth_even_without_shops(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Wirehollow")
    book = await loaded(realm)
    industry_row(ctx, book, town.id).electric = 100000
    bare = Wear({CommodityKind.FUEL: 100, CommodityKind.CLOTH: 80}, {CommodityKind.FUEL: 100, CommodityKind.CLOTH: 0})
    worn = warmed(ctx.rules, book, town.id, without_shops(bare, 15))
    assert worn.got[CommodityKind.FUEL] >= 100 and worn.got[CommodityKind.CLOTH] >= 80
    assert book.industry[town.id].spent.get("electric", 0) > 0
    unlit = await settlement(realm, "Darkhollow")
    assert warmed(ctx.rules, book, unlit.id, bare).got[CommodityKind.CLOTH] == 0


async def test_scarce_hands_meet_every_need_before_any_good_is_stockpiled(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Narrowhands")
    for kind in (WorkshopKind.CHARCOAL_KILN, WorkshopKind.WEAVERY):
        realm.session.add(WorkshopRow(community_entity_id=town.id, kind=kind, level=2, built_epoch=1))
    realm.session.add(LabourRow(community_entity_id=town.id, job=Job.CRAFTING, workers=60, output_pct=100, epoch=1))
    for commodity in (CommodityKind.TIMBER, CommodityKind.FIBRE):
        realm.session.add(CommunityStockRow(community_entity_id=town.id, commodity=commodity, quantity=5000, quality=50))
    await realm.session.flush()
    book = await loaded(realm)
    await refine_community(ctx, book, town, RefiningTally())
    await realm.session.flush()
    assert await holding(realm.session, town.id, CommodityKind.FUEL) > 0
    assert await holding(realm.session, town.id, CommodityKind.CLOTH) > 0


async def test_works_a_community_holds_in_common_pass_to_separate_households_under_a_private_order(realm: Realm) -> None:
    ctx = context(realm.session, tuned_rules(ownership={"order_shift_pct": 100}))
    town = await settlement(realm, "Kettleford")
    crown = await make(realm.session, "The Kettle Crown", EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    realm.session.add(PolityMemberRow(polity_entity_id=crown.id, member_entity_id=town.id))
    realm.session.add(EconomicOrderRow(polity_entity_id=crown.id, sector=None, ownership=OwnershipRegime.PRIVATE))
    keepers = [await mortal(realm, name, location_id=town.id) for name in ("Orla Venn", "Bram Hale")]
    realm.session.add_all([MortalProfileRow(entity_id=keeper.id, wealth=60 - index * 10, locked=[]) for index, keeper in enumerate(keepers)])
    works = [
        WorkshopRow(community_entity_id=town.id, kind=kind, level=1, built_epoch=1, owner_node_id=town.id)
        for kind in (WorkshopKind.FISHERY, WorkshopKind.FORGE)
    ]
    realm.session.add_all(works)
    await realm.session.flush()
    tally = ProfitTally()
    for work in works:
        await pass_commons(ctx, town, work, tally)
        await realm.session.flush()
    assert sorted(work.owner_node_id or 0 for work in works) == sorted(keeper.id for keeper in keepers) and tally.owned == 2
