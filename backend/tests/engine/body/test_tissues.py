from typing import Any, cast

from aerona.catalog.anatomy import ANATOMIES
from aerona.catalog.tissues import covering_of, stack_of
from aerona.db.tables.body import InjuryRow
from aerona.domain.enums.body import (
    BodyFunction,
    BodyPlan,
    BodyRegion,
    Consciousness,
    DamageType,
    InjuryKind,
    InjuryState,
    NerveDamage,
    TissueKind,
    TreatmentStep,
)
from aerona.engine.body.book import aid_of, consciousness_of
from aerona.engine.body.capacities import BearerStats, BodyState, capacities
from aerona.engine.body.functions import Wound
from aerona.engine.body.tissues import bleed_rate, tissue_hit, tissue_loss
from aerona.engine.body.treatment import diagnosis_chance, wanted_steps
from aerona.rules.registry import Rules

RULES = Rules()
HUMAN = ANATOMIES[BodyPlan.HUMANOID]


def part(key: str) -> Any:
    found = HUMAN.part(key)
    assert found is not None
    return found


def injury(kind: InjuryKind, part_key: str, *, bleeding: int = 0, treatments: list[str] | None = None) -> InjuryRow:
    return InjuryRow(part=part_key, kind=kind, severity=3, state=InjuryState.FRESH, bleeding=bleeding, treatments=treatments or [], function_loss=0)


def test_every_plan_has_a_covering_and_humans_have_teeth_and_toes() -> None:
    assert covering_of(BodyPlan.INSECTOID) is TissueKind.CHITIN
    assert covering_of(BodyPlan.HUMANOID) is TissueKind.SKIN
    assert stack_of(BodyPlan.HUMANOID, "left_leg", BodyRegion.LEGS)[0] is TissueKind.SKIN
    assert part("teeth").counted == HUMAN.full_count("teeth") == 32 and part("toes").counted == HUMAN.full_count("toes") == 10


def test_a_deep_cut_reaches_artery_nerve_and_tendon_while_a_scratch_stays_in_the_skin() -> None:
    deep = tissue_hit(RULES, BodyPlan.HUMANOID, part("left_leg"), DamageType.CUT, 5, attack=120)
    assert deep.bleeding == bleed_rate(RULES, part("left_leg"), 5) > 0
    assert deep.nerve is NerveDamage.MOTOR and deep.tendon
    assert tissue_loss(RULES, deep) >= RULES.tissues.motor_loss
    scratch = tissue_hit(RULES, BodyPlan.HUMANOID, part("left_leg"), DamageType.CUT, 1, attack=5)
    assert scratch.bleeding == 0 and scratch.nerve is NerveDamage.NONE
    blow = tissue_hit(RULES, BodyPlan.HUMANOID, part("left_arm"), DamageType.BLUNT, 5, attack=200)
    assert blow.bone and not blow.tendon
    burn = tissue_hit(RULES, BodyPlan.INSECTOID, part("left_arm"), DamageType.FIRE, 3)
    assert burn.deepest is TissueKind.CHITIN


def test_pain_and_blood_loss_take_consciousness_and_will_masks_pain() -> None:
    assert consciousness_of(RULES, cast(Any, None), 10, 100) is Consciousness.AWAKE
    assert consciousness_of(RULES, cast(Any, None), 60, 100) is Consciousness.NAUSEOUS
    assert consciousness_of(RULES, cast(Any, None), 100, 100) is Consciousness.DIZZY
    assert consciousness_of(RULES, cast(Any, None), 10, RULES.tissues.blood_faint_at) is Consciousness.UNCONSCIOUS


def test_treatments_follow_the_wound_and_a_crutch_lets_the_lame_walk() -> None:
    cut = injury(InjuryKind.DEEP_CUT, "left_leg", bleeding=30)
    assert wanted_steps(cut, walking=True)[:3] == [TreatmentStep.SUTURE, TreatmentStep.CLEAN, TreatmentStep.DRESS]
    broken = injury(InjuryKind.FRACTURE, "left_arm")
    assert TreatmentStep.SET_BONE in wanted_steps(broken, walking=False) and TreatmentStep.CRUTCH not in wanted_steps(broken, walking=False)
    assert diagnosis_chance(RULES, 100) > diagnosis_chance(RULES, 0) == RULES.tissues.diagnose_floor_pct
    braced = injury(InjuryKind.FRACTURE, "left_leg", treatments=[TreatmentStep.CRUTCH.value])
    assert aid_of(RULES, HUMAN, [braced]) == RULES.tissues.crutch_restore_pct / 100


def test_numbness_dulls_fine_work_and_senselessness_stops_a_fighter() -> None:
    stats = BearerStats(50, 50, 50, 50, 50)
    whole = capacities(RULES, stats, BodyState(HUMAN, (), HUMAN.full_counts, 0))
    numb = capacities(RULES, stats, BodyState(HUMAN, (Wound("left_hand", InjuryKind.CUT, 2, 0, NerveDamage.SENSORY),), HUMAN.full_counts, 0))
    out = capacities(RULES, stats, BodyState(HUMAN, (), HUMAN.full_counts, 0, consciousness=Consciousness.UNCONSCIOUS))
    assert numb["craft"] <= whole["craft"]
    assert out["melee"] == 0 and out["command"] == 0
    assert BodyFunction.FINE_MANIPULATION in HUMAN.functions
