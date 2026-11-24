from aerona.catalog.effect_packages import PACKAGES
from aerona.catalog.grief import GRIEF_STAGES
from aerona.catalog.kinds.life_stages import LIFE_STAGES
from aerona.catalog.methods import METHODS
from aerona.domain.enums.affliction import PackageKind, Visibility
from aerona.domain.enums.industry import MethodKind, ProcessKind
from aerona.domain.enums.mind import GriefStage, MoodArousal, ValueAxis
from aerona.domain.enums.mortal import DeathCause, DeathReading, LifeStage
from aerona.engine.mind.thoughts import arousal_state, settled_arousal
from aerona.engine.mortal.life import StageBounds, stage_for
from aerona.engine.mortal.readings import derive_reading
from aerona.rules.registry import Rules

RULES = Rules()


def test_a_mature_stage_sits_between_adulthood_and_old_age() -> None:
    bounds = StageBounds(1, 5, 15, 60, 80, 40)
    assert [stage_for(bounds, age) for age in (20, 50, 70)] == [LifeStage.ADULT, LifeStage.MATURE, LifeStage.ELDER]
    assert LIFE_STAGES[LifeStage.MATURE].counts_as_adult


def test_arousal_settles_toward_what_is_felt_and_names_its_state() -> None:
    assert settled_arousal(RULES, 50, 100) > 50
    assert arousal_state(RULES, 10) is MoodArousal.CALM
    assert arousal_state(RULES, 90) is MoodArousal.AGITATED
    assert arousal_state(RULES, 50) is MoodArousal.ALERT


def test_bargaining_comes_between_anger_and_mourning() -> None:
    order = sorted(GRIEF_STAGES, key=lambda stage: GRIEF_STAGES[stage].order)
    assert order.index(GriefStage.ANGER) < order.index(GriefStage.BARGAINING) < order.index(GriefStage.MOURNING)
    assert GRIEF_STAGES[GriefStage.BARGAINING].bargains


def test_a_merciful_people_pities_a_death_no_one_chose() -> None:
    merciful = {ValueAxis.MERCY: 90}
    assert derive_reading(RULES, merciful, DeathCause.DISEASE) is DeathReading.PITIED
    assert derive_reading(RULES, {}, DeathCause.DISEASE) is not DeathReading.PITIED


def test_new_packages_bend_a_life_and_one_is_marked() -> None:
    assert any(stage.hastens for stage in PACKAGES[PackageKind.AGEING].stages)
    assert any(stage.forgets for stage in PACKAGES[PackageKind.FORGETTING].stages)
    assert any(stage.sleeps for stage in PACKAGES[PackageKind.SLEEP].stages)
    assert PACKAGES[PackageKind.AGEING].visibility is Visibility.MARKED


def test_printing_paper_and_rope_have_their_own_methods_and_fuel_works_warm_the_waters() -> None:
    assert METHODS[MethodKind.ROTARY_PRESS].process is ProcessKind.PRINTING
    assert METHODS[MethodKind.PAPER_MACHINE].process is ProcessKind.PAPERMAKING
    assert METHODS[MethodKind.ROPE_MACHINE].process is ProcessKind.ROPEMAKING
    assert METHODS[MethodKind.PAPER_MACHINE].heat > 0
    assert METHODS[MethodKind.HAND_MOULD].heat == 0
