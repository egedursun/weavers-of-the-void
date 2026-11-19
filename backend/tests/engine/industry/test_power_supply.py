from collections import Counter
from dataclasses import replace

from aerona.catalog.methods import FUEL_FAMILY
from aerona.catalog.needs import SHORTFALL_EFFECTS
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.economy import CommunityStockRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import CoastKind, RiverClass, TemperatureBand, TerrainKind
from aerona.domain.enums.industry import EnergyKind
from aerona.domain.enums.society_depth import ShortfallEffect
from aerona.domain.enums.structure import STRUCTURE_LEVEL_MAX, StructureKind
from aerona.domain.models.entity_stats import StructureStats
from aerona.engine.demography.basket import freeze, short_pct
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.household import Wear, warmed, wear
from aerona.engine.industry.energy import draw, gauge, industry_row, power_for_heat, survival_heat, unmet_pct
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.stats import stat_or
from aerona.engine.structures.needs import SiteFacts, commission_level, power_folk_at, power_levels_at
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, make, people, settlement

RULES = Rules()
THOUSAND = 1000
COLD_GOODS = [kind for kind, effect in SHORTFALL_EFFECTS.items() if effect is ShortfallEffect.COLD]


async def loaded(realm: Realm, band: TemperatureBand = TemperatureBand.TEMPERATE) -> EconomyBook:
    book = await EconomyBook.load(context(realm.session))
    book.ground.regions[realm.region.id] = RegionEnvironmentRow(
        entity_id=realm.region.id,
        world_id=realm.world.id,
        river_class=RiverClass.NONE,
        coast_kind=CoastKind.NONE,
        roughness=20,
        forest_cover=0,
        wetland=0,
        temperature_band=band,
        rainfall=50,
        magic_density=0,
        seasonality=40,
        soil_fertility=60,
        moisture=50,
        base_forest=0,
        base_wetland=0,
        temperature=50,
        latitude=30,
        dominant_terrain=TerrainKind.PLAIN,
        scars={},
        disease_load=0,
        locked=[],
    )
    return book


def site_facts(town: EntityRow) -> SiteFacts:
    return SiteFacts(
        site=town,
        town=None,
        shares={},
        knowledge=KnowledgeMap({}),
        at_war=False,
        patron=False,
        coastal=False,
        river=False,
        literacy=100,
        capital=False,
        outbreak=False,
        present=Counter(),
        workshops=set(),
        barred=set(),
    )


def cold_short(worn: Wear) -> int:
    wanted = sum(worn.wanted.get(kind, 0) for kind in COLD_GOODS)
    return short_pct(wanted, sum(min(worn.wanted.get(kind, 0), worn.got.get(kind, 0)) for kind in COLD_GOODS))


async def test_a_modern_city_with_plants_sized_to_it_meets_its_electric_need(realm: Realm) -> None:
    ctx = context(realm.session)
    population = 200000
    town = await settlement(realm, "Lumenford", population=population)
    await realm.session.flush()
    facts = site_facts(town)
    assert facts.power_lacking(RULES) > STRUCTURE_LEVEL_MAX
    plants = 0
    while facts.power_lacking(RULES) > 0:
        level = commission_level(RULES, facts, StructureKind.POWER_PLANT)
        plant = await make(realm.session, f"Lumenford Plant {plants}", EntityType.STRUCTURE, StructureStats(), world_id=realm.world.id, location_id=town.id)
        realm.session.add(StructureProfileRow(structure_entity_id=plant.id, kind=StructureKind.POWER_PLANT, host_entity_id=town.id, level=level))
        await realm.session.flush()
        plants += 1
        facts = replace(facts, present=Counter({StructureKind.POWER_PLANT: plants}), power_levels=await power_levels_at(ctx, town.id))
    assert plants > 1
    book = await loaded(realm)
    row = await gauge(ctx, book, town, leys=Counter())
    need = population * RULES.energy.electric_per_1000 // THOUSAND
    assert draw(book, town.id, EnergyKind.ELECTRIC, need) == need
    assert unmet_pct(row, EnergyKind.ELECTRIC) == 0
    assert replace(facts, power_drawn=need * 2).power_lacking(RULES) > 0
    assert commission_level(RULES, facts, StructureKind.MARKET) == 1


async def test_a_place_with_power_and_no_fuel_keeps_warm_and_none_die_of_cold(realm: Realm) -> None:
    ctx = context(realm.session)
    lit = await settlement(realm, "Coldharbour", population=10000)
    dark = await settlement(realm, "Frostmere", population=10000)
    for town in (lit, dark):
        realm.session.add(CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.CLOTH, quantity=100000, quality=50))
        realm.session.add(CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.WOOL, quantity=100000, quality=50))
        realm.session.add(CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.FIBRE, quantity=100000, quality=50))
    plant = await make(realm.session, "Coldharbour Plant", EntityType.STRUCTURE, StructureStats(), world_id=realm.world.id, location_id=lit.id)
    realm.session.add(StructureProfileRow(structure_entity_id=plant.id, kind=StructureKind.POWER_PLANT, host_entity_id=lit.id, level=1))
    await realm.session.flush()
    book = await loaded(realm, TemperatureBand.COLD)
    row = await gauge(ctx, book, lit, leys=Counter())
    unwarmed = survival_heat(RULES, 10000, TemperatureBand.COLD)
    assert unwarmed > 0 and row.electric == RULES.energy.electric_per_level - power_for_heat(RULES, unwarmed)
    industry_row(ctx, book, dark.id)
    warm = warmed(ctx.rules, book, lit.id, await wear(ctx, lit))
    assert all(warm.got[kind] >= warm.wanted[kind] for kind in FUEL_FAMILY if kind in warm.wanted)
    assert row.spent.get(EnergyKind.ELECTRIC.value, 0) > 0
    assert cold_short(warm) == 0
    assert await freeze(ctx, lit, cold_short(warm), TemperatureBand.COLD) == 0
    assert stat_or(lit, "population", 0) == 10000
    cold = warmed(ctx.rules, book, dark.id, await wear(ctx, dark))
    assert cold_short(cold) > 0
    assert await freeze(ctx, dark, cold_short(cold), TemperatureBand.COLD) > 0


async def test_a_dam_gives_electric_power_only_to_a_place_that_knows_electricity(realm: Realm) -> None:
    ctx = context(realm.session)
    old = await settlement(realm, "Weirholm", population=4000)
    wired = await settlement(realm, "Voltmere", population=4000)
    realm.session.add(HolderTechniqueRow(holder_entity_id=old.id, technique=Technique.STEEL))
    realm.session.add(HolderTechniqueRow(holder_entity_id=wired.id, technique=Technique.ELECTRICITY))
    for town in (old, wired):
        dam = await make(realm.session, f"{town.name} Dam", EntityType.STRUCTURE, StructureStats(), world_id=realm.world.id, location_id=town.id)
        realm.session.add(StructureProfileRow(structure_entity_id=dam.id, kind=StructureKind.DAM, host_entity_id=town.id, level=1))
    await realm.session.flush()
    book = await loaded(realm)
    assert (await gauge(ctx, book, old, leys=Counter())).electric == 0
    assert (await gauge(ctx, book, wired, leys=Counter())).electric == RULES.energy.electric_per_level


async def test_a_town_sizes_its_plants_to_every_people_that_draws_on_them_and_shares_their_power(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Tarimside", population=10000)
    throng = await people(realm, "Hemsar Throng", population=180000)
    await BondRepository(realm.session).connect(BondDraft(town.id, throng.id, BondKind.DESCENDS_FROM, 1))
    await realm.session.flush()
    folk = await power_folk_at(ctx, town.id)
    assert folk == 180000
    facts = replace(site_facts(town), power_folk=folk)
    plants = 0
    while facts.power_lacking(RULES) > 0:
        plant = await make(realm.session, f"Tarimside Plant {plants}", EntityType.STRUCTURE, StructureStats(), world_id=realm.world.id, location_id=town.id)
        level = commission_level(RULES, facts, StructureKind.POWER_PLANT)
        realm.session.add(StructureProfileRow(structure_entity_id=plant.id, kind=StructureKind.POWER_PLANT, host_entity_id=town.id, level=level))
        await realm.session.flush()
        plants += 1
        facts = replace(facts, present=Counter({StructureKind.POWER_PLANT: plants}), power_levels=await power_levels_at(ctx, town.id))
    book = await loaded(realm)
    town_row = await gauge(ctx, book, town, leys=Counter())
    throng_row = await gauge(ctx, book, throng, leys=Counter())
    made = facts.power_levels * RULES.energy.electric_per_level
    assert town_row.electric + throng_row.electric <= made + 1
    for community, row in ((town, town_row), (throng, throng_row)):
        need = stat_or(community, "population", 0) * RULES.energy.electric_per_1000 // THOUSAND
        assert draw(book, community.id, EnergyKind.ELECTRIC, need) == need
        assert unmet_pct(row, EnergyKind.ELECTRIC) == 0
