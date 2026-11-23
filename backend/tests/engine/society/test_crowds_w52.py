import importlib.util
from pathlib import Path

from aerona.catalog.collective import ACTS, CROWD_FEELINGS, TRIGGERS
from aerona.db.tables.collective import CrowdMoodRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.collective import CollectiveActKind, CollectiveTrigger, CrowdFeeling
from aerona.domain.enums.settlement import SizeTier
from aerona.engine.collective.crowds import act_for, trigger_for
from aerona.engine.collective.feelings import fade_feelings, feelings_of, set_feeling, stir_feelings
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, settlement

RULES = Rules()


def calm(**levels: int) -> dict[CrowdFeeling, int]:
    return {feeling: levels.get(feeling.value, 0) for feeling in CrowdFeeling}


def test_twelve_acts_five_feelings_and_sixteen_triggers_are_typed() -> None:
    assert len(ACTS) == len(CollectiveActKind) == 12
    assert len(CROWD_FEELINGS) == len(CrowdFeeling) == 5
    assert len(TRIGGERS) == len(CollectiveTrigger) == 16
    assert TRIGGERS[CollectiveTrigger.VICTORY].act is CollectiveActKind.JUBILATION
    assert TRIGGERS[CollectiveTrigger.GREAT_FUNERAL].mood is CrowdFeeling.GRIEF
    assert trigger_for(CollectiveActKind.BOYCOTT) in TRIGGERS


async def test_hope_turns_a_riot_into_a_demonstration_and_the_watch_turns_it_into_a_boycott(realm: Realm) -> None:
    ctx = context(realm.session, RULES)
    open_mood = CrowdMoodRow(settlement_entity_id=1, deterrence=0, agitation=0, locked=[])
    assert act_for(ctx, CollectiveActKind.RIOT, calm(anger=40), open_mood) is CollectiveActKind.RIOT
    assert act_for(ctx, CollectiveActKind.RIOT, calm(anger=40, hope=80), open_mood) is CollectiveActKind.DEMONSTRATION
    guarded = CrowdMoodRow(settlement_entity_id=1, deterrence=90, agitation=0, locked=[])
    assert act_for(ctx, CollectiveActKind.RIOT, calm(anger=60), guarded) is CollectiveActKind.BOYCOTT
    assert act_for(ctx, CollectiveActKind.PANIC, calm(fear=40, grief=90), open_mood) is CollectiveActKind.EXODUS


async def test_one_store_holds_five_feelings_that_rise_fade_and_hold(realm: Realm) -> None:
    town = await settlement(realm, "Weir")
    realm.session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, locked=[]))
    ctx = context(realm.session)
    await stir_feelings(ctx, town.id, {CrowdFeeling.GRIEF: 60, CrowdFeeling.HOPE: 30})
    await realm.session.flush()
    levels = await feelings_of(realm.session, town.id)
    assert levels[CrowdFeeling.GRIEF] == 60 and levels[CrowdFeeling.HOPE] == 30 and len(levels) == 5
    await set_feeling(realm.session, town.id, CrowdFeeling.HOPE, 50, hold=True)
    await fade_feelings(ctx, town.id)
    await stir_feelings(ctx, town.id, {CrowdFeeling.HOPE: 20})
    await realm.session.flush()
    levels = await feelings_of(realm.session, town.id)
    assert levels[CrowdFeeling.HOPE] == 50
    assert levels[CrowdFeeling.GRIEF] == 60 - RULES.collective.grief_decay


def test_a_fixed_crowd_feeling_column_is_caught() -> None:
    spec = importlib.util.spec_from_file_location("check_cycle_fields", Path(__file__).resolve().parents[4] / "scripts" / "check_cycle_fields.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert len(module.fixed_in("engine/sample.py", "def heat(mood):\n    return mood.anger + mood.anxiety\n")) == 2
    assert module.fixed_in("engine/sample.py", "def heat(row):\n    return row.level\n") == []
