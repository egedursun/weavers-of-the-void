import importlib.util
from pathlib import Path
from types import ModuleType

from aerona.catalog.calendar_slots import SLOTS
from aerona.db.tables.celestial import SkyEventRow
from aerona.db.tables.culture import RiteProfileRow
from aerona.db.tables.environment import CalendarRow, WorldSeasonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import CalendarSlot, MagicSchool, MagicSource
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.world import SkyEventKind
from aerona.domain.models.entity_stats import RiteStats
from aerona.engine.lore.calendar_slots import slot_open
from aerona.engine.lore.rites import unmet
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
    realm.session.add_all([season(world, 0, cold=-20, growth=10, campaign=20), season(world, 1, growth=80, campaign=70)])
    await realm.session.flush()
    ctx = context(realm.session)
    states = {slot: await slot_open(ctx, world, slot, None) for slot in CalendarSlot}
    assert {slot for slot, state in states.items() if state.open} == {CalendarSlot.SOWING, CalendarSlot.HARVEST, CalendarSlot.MIDWINTER, CalendarSlot.CAMPAIGN}
    assert states[CalendarSlot.HOLY_DAY].reason is not None
    assert set(SLOTS) == set(CalendarSlot)


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
