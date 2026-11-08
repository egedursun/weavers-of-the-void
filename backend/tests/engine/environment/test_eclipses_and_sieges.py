import pytest

from aerona.db.tables.warfare import SiegeRow
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.military import StarvationStage
from aerona.domain.models.entity_stats import EventStats
from aerona.engine.happenings.effects import onset, siege_peaked, world_piety
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.stats import stat
from tests.engine.society.factories import Realm, context, make, people, settlement


async def test_an_eclipse_stirs_the_piety_of_every_society_of_its_world(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Lumen")
    folk = await people(realm, "Sky Folk", piety=30)
    event = await make(realm.session, "The Dark Noon", EntityType.EVENT, EventStats(), world_id=realm.world.id, engine_kind=EngineKind.ECLIPSE_WATCH)
    before = stat(town, "piety") or 0
    await onset(ctx, event, town, await RegionAtlas.load(realm.session))
    gain = ctx.rules.events.eclipse_piety
    assert stat(town, "piety") == min(100, before + gain) and stat(folk, "piety") == min(100, 30 + gain)


async def test_piety_without_a_world_touches_nothing(realm: Realm) -> None:
    assert await world_piety(context(realm.session), None, 10) == 0


@pytest.mark.parametrize(
    ("long", "starvation", "peaked"),
    [
        (False, StarvationStage.NONE, False),
        (False, StarvationStage.RATIONING, False),
        (True, StarvationStage.NONE, True),
        (False, StarvationStage.FAMINE, True),
        (False, StarvationStage.TABOO_BROKEN, True),
    ],
)
async def test_a_siege_peaks_by_its_length_or_its_hunger(realm: Realm, long: bool, starvation: StarvationStage, peaked: bool) -> None:
    ctx = context(realm.session)
    rounds = ctx.rules.events.siege_peak_rounds if long else 0
    siege = SiegeRow(war_id=1, besieged_entity_id=1, besieger_entity_id=2, started_epoch=1, rounds=rounds, starvation=starvation)
    assert siege_peaked(ctx, siege) is peaked
    assert not siege_peaked(ctx, None)
