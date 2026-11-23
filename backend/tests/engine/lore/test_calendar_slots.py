import importlib.util
from pathlib import Path
from types import ModuleType

from aerona.catalog.calendar_slots import SLOTS
from aerona.db.tables.celestial import SkyEventRow
from aerona.db.tables.culture import RiteProfileRow, TraditionProfileRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.environment import CalendarRow, WorldSeasonRow
from aerona.db.tables.gatherings import GatheringRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import CalendarSlot, MagicSchool, MagicSource
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.gathering import GatheringKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.world import SkyEventKind
from aerona.domain.models.entity_stats import RiteStats, SpeciesStats
from aerona.engine.lore.calendar_slots import slot_open
from aerona.engine.lore.rites import unmet
from aerona.rules.registry import Rules
from aerona.services.integrity.rite_needs import keep_war_needs
from tests.db.factories import seed_world
from tests.engine.society.factories import Realm, context, knowledge, link, make, mortal

SCRIPT = Path(__file__).resolve().parents[4] / "scripts" / "check_calendar_slots.py"


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_calendar_slots", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def season(world_id: int, position: int, *, cold: int = 0, growth: int = 50, campaign: int = 50) -> WorldSeasonRow:
    return WorldSeasonRow(
        world_id=world_id, position=position, name=f"Season {position}", temperature_shift=cold, rain_shift=0, growth=growth, travel=50, campaign=campaign
    )


async def test_every_slot_opens_by_its_own_season(realm: Realm) -> None:
    world = realm.world.id
    realm.session.add_all(
        [
            season(world, 0, cold=-20, growth=10, campaign=20),
            season(world, 1, cold=0, growth=70, campaign=40),
            season(world, 2, cold=20, growth=80, campaign=70),
            season(world, 3, cold=0, growth=70, campaign=40),
        ]
    )
    await realm.session.flush()
    ctx = context(realm.session)
    states = {slot: await slot_open(ctx, world, slot, None) for slot in CalendarSlot}
    assert {slot for slot, state in states.items() if state.open} == {
        CalendarSlot.SOWING,
        CalendarSlot.HARVEST,
        CalendarSlot.MIDWINTER,
        CalendarSlot.MIDSUMMER,
        CalendarSlot.CAMPAIGN,
        CalendarSlot.NEW_YEAR,
    }
    assert all(state.reason is not None for state in states.values() if not state.open)
    assert set(SLOTS) == set(CalendarSlot)


async def test_a_world_without_seasons_begins_no_year(realm: Realm) -> None:
    state = await slot_open(context(realm.session), realm.world.id, CalendarSlot.NEW_YEAR, None)
    assert not state.open and state.reason is not None


async def test_a_remembrance_opens_only_for_a_custom_that_names_what_it_remembers(realm: Realm) -> None:
    ctx = context(realm.session)
    named = TraditionProfileRow(notable_year_id=1)
    plain = TraditionProfileRow()
    assert (await slot_open(ctx, realm.world.id, CalendarSlot.REMEMBRANCE, None, named)).open
    assert not (await slot_open(ctx, realm.world.id, CalendarSlot.REMEMBRANCE, None, plain)).open


async def test_a_market_opens_where_a_fair_is_held_and_roads_allow_it(realm: Realm) -> None:
    world = realm.world.id
    trader = await mortal(realm, "Ama", location_id=realm.region.id)
    realm.session.add(season(world, 0))
    await realm.session.flush()
    ctx = context(realm.session)
    assert not (await slot_open(ctx, world, CalendarSlot.MARKET, trader.id)).open
    realm.session.add(GatheringRow(host_node_id=trader.id, kind=GatheringKind.FAIR, world_id=world, epoch=3, season=0))
    await realm.session.flush()
    assert (await slot_open(ctx, world, CalendarSlot.MARKET, trader.id)).open


async def test_a_wild_harvest_opens_where_the_wild_stands_thick(realm: Realm) -> None:
    world = realm.world.id
    gatherer = await mortal(realm, "Tove", location_id=realm.region.id)
    beast = await make(realm.session, "Reed Deer", EntityType.SPECIES, SpeciesStats(), world_id=world, location_id=realm.region.id)
    stock = SpeciesRangeRow(species_entity_id=beast.id, region_entity_id=realm.region.id, abundance=Rules().traditions.wild_stock_min - 1, locked=[])
    realm.session.add(stock)
    await realm.session.flush()
    ctx = context(realm.session)
    assert not (await slot_open(ctx, world, CalendarSlot.WILD_HARVEST, gatherer.id)).open
    stock.abundance = Rules().traditions.wild_stock_min
    await realm.session.flush()
    assert (await slot_open(ctx, world, CalendarSlot.WILD_HARVEST, gatherer.id)).open


async def test_a_mild_world_keeps_no_midwinter_and_a_calm_one_no_campaign(realm: Realm) -> None:
    world = realm.world.id
    realm.session.add_all([season(world, 0, cold=0, growth=10, campaign=10), season(world, 1, growth=30, campaign=20)])
    await realm.session.flush()
    ctx = context(realm.session)
    assert not (await slot_open(ctx, world, CalendarSlot.MIDWINTER, None)).open
    assert not (await slot_open(ctx, world, CalendarSlot.CAMPAIGN, None)).open
    assert not (await slot_open(ctx, world, CalendarSlot.HARVEST, None)).open


async def test_a_holy_day_on_another_world_does_not_open_a_rite_slot(realm: Realm) -> None:
    other = await seed_world(realm.session, "Elsewhere", "Far Sun")
    realm.session.add(SkyEventRow(kind=SkyEventKind.ECLIPSE, epoch=3, world_id=other.id))
    caster = await mortal(realm, "Ilse")
    rite = await make(realm.session, "Rite of Dawn", EntityType.RITE, RiteStats(), world_id=realm.world.id)
    realm.session.add(
        RiteProfileRow(rite_entity_id=rite.id, school=MagicSchool.DIVINATION, source=MagicSource.DIVINE, requirements={"slot": "holy_day"}, cost={}, locked=[])
    )
    await realm.session.flush()
    ctx = context(realm.session)
    profile = await realm.session.get(RiteProfileRow, rite.id)
    assert profile is not None
    assert await unmet(ctx, caster, profile) == SLOTS_CLOSED_HOLY
    realm.session.add(SkyEventRow(kind=SkyEventKind.COMET, epoch=3, world_id=realm.world.id))
    await realm.session.flush()
    assert (await slot_open(ctx, realm.world.id, CalendarSlot.HOLY_DAY, caster.id)).open


async def test_a_kept_calendar_with_holy_days_opens_the_holy_day(realm: Realm) -> None:
    caster = await mortal(realm, "Oren")
    lore = await knowledge(realm, "The Count of Days", KnowledgeBranch.WRITING)
    realm.session.add(CalendarRow(knowledge_entity_id=lore.id, world_id=realm.world.id, adopted_epoch=1, anchor_year=0, holy_days=[{"name": "First Light"}]))
    await link(realm.session, caster.id, lore.id, BondKind.KNOWS)
    await realm.session.flush()
    assert (await slot_open(context(realm.session), realm.world.id, CalendarSlot.HOLY_DAY, caster.id)).open


async def test_an_old_campaign_rite_keeps_its_need_of_war(realm: Realm) -> None:
    rite = await make(realm.session, "Rite of Spears", EntityType.RITE, RiteStats(), world_id=realm.world.id)
    realm.session.add(
        RiteProfileRow(rite_entity_id=rite.id, school=MagicSchool.STORM, source=MagicSource.LEY, requirements={"slot": "campaign"}, cost={}, locked=[])
    )
    await realm.session.flush()
    assert await keep_war_needs(realm.session) == 1
    profile = await realm.session.get(RiteProfileRow, rite.id)
    assert profile is not None and profile.requirements["war"]
    assert await keep_war_needs(realm.session) == 0


def test_a_slot_compared_outside_its_catalogue_is_caught() -> None:
    text = "from aerona.domain.enums.culture import CalendarSlot\nwarm = slot is CalendarSlot.HARVEST\n"
    assert [item.line for item in checker().specials_in("engine/sample.py", text)] == [2]


def test_the_source_asks_slot_open_for_every_slot() -> None:
    assert checker().main() == 0


SLOTS_CLOSED_HOLY = "no sign shows over that world this epoch and no calendar kept there marks holy days"
