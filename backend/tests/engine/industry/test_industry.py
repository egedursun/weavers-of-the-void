from collections import Counter

from sqlalchemy import select

from aerona.catalog.methods import METHODS
from aerona.db.tables.culture import HolderTechniqueRow, IdeologyAdherentRow, IdeologyTenetRow
from aerona.db.tables.demography import LabourRow
from aerona.db.tables.economy import CommunityStockRow, ProductionRunRow, WorkshopRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.factions import FactionGoalRow, FactionProfileRow
from aerona.db.tables.industry import RegionPollutionRow
from aerona.domain.enums.culture import IdeologyTenet, Technique
from aerona.domain.enums.demography import Job
from aerona.domain.enums.economy import CommodityKind, WorkshopKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import CoastKind, RiverClass, TemperatureBand
from aerona.domain.enums.faction import FactionGoalKind, FactionKind
from aerona.domain.enums.industry import EnergyKind, MethodKind, Pollutant, ProcessKind, QualityTier
from aerona.domain.models.entity_stats import FactionStats, IdeologyStats
from aerona.engine.economy.book import EconomyBook
from aerona.engine.industry.energy import draw, gauge, industry_row, survival_heat, unmet_pct
from aerona.engine.industry.methods import MethodTally, adopt, choose_methods, profit, reveres_nature
from aerona.engine.industry.pollution import PollutionTally, disease_extra, fertility_factor, fish_factor, tend_pollution
from aerona.engine.industry.quality import premium, tier_of
from aerona.engine.industry.stores import StoreTally, preserve, spoil, wear_tools
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, make, settlement

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
    await realm.session.flush()
    book = await loaded(realm)
    row = await gauge(ctx, book, town, leys=Counter())
    assert row.heat > 0 and row.water > 0 and row.muscle > 0
    await adopt(ctx, book, town, METHODS[MethodKind.BLOOMERY], MethodTally())
    tally = MethodTally()
    await choose_methods(ctx, book, town, tally)
    chosen = book.methods[town.id][ProcessKind.SMELTING]
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
