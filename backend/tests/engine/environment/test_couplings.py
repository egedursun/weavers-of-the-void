from dataclasses import replace

from sqlalchemy import select

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.culture import RiteProfileRow, TraditionProfileRow
from aerona.db.tables.environment import CalendarRow, NotableYearRow, RegionEnvironmentRow, StructureLeyRow, WorldSeasonRow
from aerona.db.tables.settlement import SettlementInfrastructureRow, SettlementProfileRow
from aerona.db.tables.warfare import BattleRow, WarRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import MagicSchool, TraditionKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import NotableYearKind, RiverClass, WeatherKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.war import BattleOutcome, WarCause, WarStatus
from aerona.domain.enums.world import WorldType
from aerona.domain.models.entity_stats import StructureStats, TraditionStats
from aerona.engine.disease.seasons import region_factor
from aerona.engine.economy.markets import swing_of
from aerona.engine.environment.battles import backfill_battle_ground
from aerona.engine.environment.book import EnvironmentBook
from aerona.engine.environment.control import force_weather
from aerona.engine.environment.profile import Geography, Surroundings, Works, irrigation_pct, rainfall_of
from aerona.engine.environment.works import backfill_typed_works, works_by_region
from aerona.engine.environment.years import SUB_STEPS_USED, world_years
from aerona.engine.lore.calendar_rites import RiteCalendar, found_sleep_customs, hallow_holy_days, preferred_season
from aerona.engine.lore.rites import dampening
from aerona.engine.lore.traditions import Keeping, celebrate, profile_of
from aerona.engine.phases.environment import ley_lines
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.settlement.book import town_of
from aerona.engine.settlement.life import FireYear, Waterside, fire_years, water_works
from aerona.rules.registry import Rules
from tests.engine.environment.test_environment import ley_realm, surveyed
from tests.engine.society.factories import Realm, context, knowledge, link, make, people, settlement, tuned

RULES = Rules()


async def test_every_yearly_system_shares_one_budgeted_draw(realm: Realm) -> None:
    ctx = context(realm.session, tuned(engine_budget={"max_sub_steps_per_epoch": 7}))
    births = world_years(ctx.environment, realm.world.id, "births")
    again = world_years(ctx.environment, realm.world.id, "births")
    fires = world_years(ctx.environment, realm.world.id, "fires")
    assert births == again and len(births) == RULES.time.sampled_years
    assert len(fires) == 2 and fires == births[:2]
    assert ctx.environment.stats.counters[SUB_STEPS_USED] == 7
    starved = world_years(ctx.environment, realm.world.id, "disease")
    assert len(starved) == 1


async def test_wind_and_wet_reach_the_fires_of_a_town(realm: Realm) -> None:
    await surveyed(realm)
    town_entity = await settlement(realm, "Kindling")
    ctx = context(realm.session)
    town = await town_of(ctx, town_entity, await KnowledgeMap.load(realm.session))
    await force_weather(realm.session, realm.region, WeatherKind.STORM, from_epoch=1, epochs=10, season_position=None)
    book = await EnvironmentBook.load(realm.session, RULES, ctx.epoch)
    ground = book.regions[realm.region.id]
    years = fire_years(ctx, town, ground, book)
    assert years and all(year == FireYear(wet=RULES.weather.storm_wet, wind=RULES.weather.storm_wind) for year in years)
    assert fire_years(ctx, town, None, None)[0] == FireYear()


async def test_a_wet_hot_sickly_season_speeds_disease(realm: Realm) -> None:
    await surveyed(realm)
    ctx = context(realm.session)
    await force_weather(realm.session, realm.region, WeatherKind.DOWNPOUR, from_epoch=1, epochs=10, season_position=None)
    wet = region_factor(
        ctx,
        await EnvironmentBook.load(realm.session, RULES, ctx.epoch),
        (await realm.session.get(RegionEnvironmentRow, realm.region.id)) or RegionEnvironmentRow(),
    )
    await force_weather(realm.session, realm.region, WeatherKind.CLEAR, from_epoch=1, epochs=10, season_position=None)
    clear_book = await EnvironmentBook.load(realm.session, RULES, ctx.epoch)
    clear_book.forced[realm.region.id] = [row for row in clear_book.forced[realm.region.id] if row.kind is WeatherKind.CLEAR]
    clear = region_factor(ctx, clear_book, clear_book.regions[realm.region.id])
    assert wet > clear >= RULES.seasonal.disease_season_floor_pct / 100


async def test_a_lean_year_lifts_food_and_shakes_other_prices(realm: Realm) -> None:
    ctx = context(realm.session)
    market = await settlement(realm, "Market Town")
    food = swing_of(ctx, market, CommodityKind.GRAIN, [-50, 0])
    assert food.factor > 1 and food.spread > 0
    assert swing_of(ctx, market, CommodityKind.GRAIN, []).factor == 1.0
    tools = swing_of(ctx, market, CommodityKind.TOOLS, [0, 0, 0])
    assert RULES.seasonal.swing_floor_pct / 100 <= tools.factor <= RULES.seasonal.swing_cap_pct / 100


async def _tradition(realm: Realm, name: str, kind: TraditionKind) -> tuple:
    entity = await make(realm.session, name, EntityType.TRADITION, TraditionStats(spread=20, rigidity=20), world_id=realm.world.id)
    row = await profile_of(context(realm.session), entity)
    row.kind = kind
    return entity, row


async def test_festivals_bind_to_their_season_and_a_calendar_fixes_the_date(realm: Realm) -> None:
    await surveyed(realm)
    seasons = list(await realm.session.scalars(select(WorldSeasonRow).where(WorldSeasonRow.world_id == realm.world.id).order_by(WorldSeasonRow.position)))
    folk = await people(realm, "Harvesters")
    feast, row = await _tradition(realm, "Feast of Sheaves", TraditionKind.HARVEST_RITE)
    lore = await knowledge(realm, "Sky Count", KnowledgeBranch.ASTRONOMY)
    rites = await RiteCalendar.load(realm.session)
    rites.bind(row, feast, folk)
    assert row.season_position == preferred_season(TraditionKind.HARVEST_RITE, seasons)
    assert row.calendar_entity_id is None
    drifting = rites.keeping(context(realm.session, tuned(seasonal={"drift_chance": 100})), row, feast, folk)
    assert drifting.in_season is False and drifting.weight == RULES.seasonal.off_season_pct / 100
    realm.session.add(CalendarRow(knowledge_entity_id=lore.id, world_id=realm.world.id, adopted_epoch=1, anchor_year=0, month_names=[], holy_days=[]))
    await link(realm.session, folk.id, lore.id, BondKind.KNOWS)
    rites = await RiteCalendar.load(realm.session)
    rites.bind(row, feast, folk)
    assert row.calendar_entity_id == lore.id
    fixed = rites.keeping(context(realm.session, tuned(seasonal={"drift_chance": 100})), row, feast, folk)
    assert fixed.in_season is True and fixed.weight == RULES.seasonal.in_season_pct / 100 and fixed.relief > 0
    row.locked = ["season_position"]
    row.season_position = 0
    rites.bind(row, feast, folk)
    assert row.season_position == 0


async def test_a_hungry_holy_day_founds_a_fast_kept_by_the_calendar_folk(realm: Realm) -> None:
    await surveyed(realm)
    folk = await people(realm, "Fasters")
    lore = await knowledge(realm, "Moon Count", KnowledgeBranch.ASTRONOMY)
    await link(realm.session, folk.id, lore.id, BondKind.KNOWS)
    notable = NotableYearRow(
        world_id=realm.world.id, region_entity_id=realm.region.id, epoch=2, year=80, kind=NotableYearKind.HUNGER, name="the Bitter Year", magnitude=70
    )
    realm.session.add(notable)
    await realm.session.flush()
    calendar = CalendarRow(
        knowledge_entity_id=lore.id,
        world_id=realm.world.id,
        adopted_epoch=1,
        anchor_year=0,
        month_names=[],
        holy_days=[{"name": "Fast of the Bitter Year", "notable_year_id": notable.id, "year": 80}],
    )
    realm.session.add(calendar)
    await realm.session.flush()
    assert await hallow_holy_days(context(realm.session), calendar) == 1
    tradition_id = calendar.holy_days[0]["tradition_entity_id"]
    row = await realm.session.get(TraditionProfileRow, tradition_id)
    assert row is not None and row.kind is TraditionKind.FAST and row.notable_year_id == notable.id and row.calendar_entity_id == lore.id
    kept = await realm.session.scalar(
        select(BondRow).where(BondRow.source_node_id == folk.id, BondRow.target_node_id == tradition_id, BondRow.kind == BondKind.CELEBRATES)
    )
    assert kept is not None
    assert await hallow_holy_days(context(realm.session), calendar) == 0


async def test_long_days_bring_a_sleep_custom_that_works(realm: Realm) -> None:
    await surveyed(realm)
    world = await realm.session.get(WorldRow, realm.world.id)
    assert world is not None
    world.day_length_hours = 40
    town = await settlement(realm, "Lamp Town")
    profile = await realm.session.get(SettlementProfileRow, town.id)
    rules = tuned(seasonal={"sleep_custom_chance": 100})
    ctx = context(realm.session, rules)
    founded = await found_sleep_customs(ctx, await RegionAtlas.load(realm.session))
    assert founded >= 1
    statement = select(TraditionProfileRow).where(TraditionProfileRow.kind.in_([TraditionKind.SIESTA, TraditionKind.NIGHT_VIGIL]))
    customs = list(await realm.session.scalars(statement))
    assert customs
    assert await found_sleep_customs(ctx, await RegionAtlas.load(realm.session)) == 0
    if profile is not None:
        vigil, _ = await _tradition(realm, "Watch Night", TraditionKind.NIGHT_VIGIL)
        profile.crime = 50
        await celebrate(ctx, vigil, town, await RegionAtlas.load(realm.session), Keeping())
        assert profile.crime < 50


async def test_wet_weather_smothers_a_fire_rite(realm: Realm) -> None:
    await surveyed(realm)
    caster = await people(realm, "Fire Callers")
    await force_weather(realm.session, realm.region, WeatherKind.DOWNPOUR, from_epoch=1, epochs=10, season_position=None)
    fire = RiteProfileRow(school=MagicSchool.ELEMENTAL_FIRE)
    water = RiteProfileRow(school=MagicSchool.ELEMENTAL_WATER)
    ctx = context(realm.session)
    assert await dampening(ctx, caster, fire) < 1
    assert await dampening(ctx, caster, water) == 1


def test_works_water_the_fields_and_cleared_forest_dries_the_rains() -> None:
    assert irrigation_pct(RULES, RiverClass.RIVER, Works(irrigation=3)) > irrigation_pct(RULES, RiverClass.RIVER, Works())
    assert irrigation_pct(RULES, RiverClass.NONE, Works(irrigation=3)) == irrigation_pct(RULES, RiverClass.NONE, Works())
    geography = Geography([0] * 10, 20, 30, 30, 60, 80, 10, RiverClass.RIVER)
    around = Surroundings(world_type=WorldType.ORDINARY, era=None, coastal=False, highland=False)
    assert rainfall_of(RULES, geography, replace(around, cleared=100)) < rainfall_of(RULES, geography, around)


async def test_riverside_towns_want_bridges_and_irrigation(realm: Realm) -> None:
    town_entity = await settlement(realm, "Ford", population=6000)
    ctx = context(realm.session, tuned(urban={"bridge_level": 0}))
    town = await town_of(ctx, town_entity, await KnowledgeMap.load(realm.session))
    assert water_works(ctx, town, 0, Waterside()) == []
    wants = water_works(ctx, town, 0, Waterside(river=RiverClass.RIVER, irrigators=True))
    assert "bridges" in wants


async def test_bridge_structures_become_typed_works(realm: Realm) -> None:
    town = await settlement(realm, "Bridgend")
    await make(
        realm.session,
        "Old Span",
        EntityType.STRUCTURE,
        StructureStats(splendor=5, durability=50, function=40),
        world_id=realm.world.id,
        location_id=realm.region.id,
        subtype="stone bridge",
    )
    await surveyed(realm)
    ctx = context(realm.session)
    works = await realm.session.get(SettlementInfrastructureRow, town.id)
    assert works is not None and works.bridges == 1
    book = await EnvironmentBook.load(realm.session, RULES, ctx.epoch)
    assert (await works_by_region(ctx, book))[realm.region.id].bridges == 1
    assert await backfill_typed_works(ctx) == 0


async def test_old_battles_get_their_ground_and_year(realm: Realm) -> None:
    first = await people(realm, "Reds")
    second = await people(realm, "Blues")
    war = WarRow(event_entity_id=first.id, world_id=realm.world.id, status=WarStatus.ONGOING, cause=WarCause.HOSTILITY, started_epoch=1, battles=1)
    realm.session.add(war)
    await realm.session.flush()
    battle = BattleRow(
        war_id=war.id,
        epoch=2,
        sequence=1,
        place_entity_id=realm.region.id,
        winner_entity_id=first.id,
        loser_entity_id=second.id,
        outcome=BattleOutcome.FIELD_VICTORY,
        gap=1.0,
    )
    realm.session.add(battle)
    await realm.session.flush()
    await surveyed(realm)
    assert await backfill_battle_ground(context(realm.session)) == 0
    assert battle.terrain is not None and battle.weather is not None and battle.season_name is not None
    assert battle.year is not None and RULES.time.years_per_epoch <= battle.year < 2 * RULES.time.years_per_epoch


async def test_an_attuned_work_on_a_line_is_recorded(realm: Realm) -> None:
    await ley_realm(realm)
    work = await make(
        realm.session,
        "Star Dome",
        EntityType.STRUCTURE,
        StructureStats(splendor=5, durability=50, function=40),
        world_id=realm.world.id,
        location_id=realm.region.id,
    )
    await ley_lines(context(realm.session))
    row = await realm.session.get(StructureLeyRow, work.id)
    assert row is not None and row.on_ley_line and not row.attuned
    row.attuned = True
    await ley_lines(context(realm.session, epoch=4))
    assert row.updated_epoch == 4
