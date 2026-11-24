from aerona.catalog.conditions import AGE_CONDITIONS, BEDRIDDEN_LOSSES, MADNESS_CONDITIONS, OPEN_INJURY_STATES, STATES
from aerona.catalog.harm_kinds import DAMAGE, INJURIES, STEPS, damage_where, injuries_where
from aerona.domain.enums.body import Capacity, ConditionKind, DamageType, InjuryKind, InjuryState, TreatmentStep
from aerona.domain.enums.records import StepAction


def test_damage_traits_keep_their_memberships() -> None:
    assert damage_where(lambda spec: spec.edged) == {DamageType.CUT, DamageType.PIERCE, DamageType.BALLISTIC}
    assert damage_where(lambda spec: spec.searing) == {DamageType.FIRE, DamageType.COLD, DamageType.ENERGY, DamageType.ELECTRIC, DamageType.CHEMICAL}
    assert damage_where(lambda spec: spec.deep) == {
        DamageType.PIERCE,
        DamageType.BLUNT,
        DamageType.VENOM,
        DamageType.BALLISTIC,
        DamageType.EXPLOSIVE,
        DamageType.PRESSURE,
    }
    assert DAMAGE[DamageType.PIERCE].blow is StepAction.THRUST and DAMAGE[DamageType.FIRE].spared is InjuryKind.BURN


def test_injury_traits_keep_their_memberships() -> None:
    assert injuries_where(lambda spec: spec.total_loss) == {InjuryKind.SEVERED, InjuryKind.GOUGED, InjuryKind.DESTROYED}
    assert injuries_where(lambda spec: spec.mark) == {InjuryKind.VOID_TOUCH, InjuryKind.DIVINE_BRAND}
    assert injuries_where(lambda spec: spec.cut_away) == {InjuryKind.SEVERED, InjuryKind.GOUGED}
    assert INJURIES[InjuryKind.FRACTURE].care == (TreatmentStep.SET_BONE, TreatmentStep.SPLINT)
    assert STEPS[TreatmentStep.SUTURE].stanches and not STEPS[TreatmentStep.DRESS].stanches


def test_conditions_capacities_and_states_keep_their_memberships() -> None:
    assert MADNESS_CONDITIONS == (ConditionKind.PARANOIA, ConditionKind.VISIONS, ConditionKind.RAGE, ConditionKind.MELANCHOLY)
    assert set(AGE_CONDITIONS) == {ConditionKind.AGE_BLINDNESS, ConditionKind.AGE_DEAFNESS, ConditionKind.CHRONIC_ILLNESS, ConditionKind.INFERTILITY}
    assert set(BEDRIDDEN_LOSSES) == {
        Capacity.MELEE,
        Capacity.MISSILE,
        Capacity.COMMAND,
        Capacity.MOBILITY,
        Capacity.CRAFT,
        Capacity.ENDURANCE,
        Capacity.STEALTH,
        Capacity.LABOUR,
    }
    assert {InjuryState.FRESH, InjuryState.INFECTED, InjuryState.HEALING, InjuryState.REOPENED, InjuryState.GANGRENOUS} == OPEN_INJURY_STATES
    assert sorted(STATES, key=lambda state: STATES[state].rank)[-1] is InjuryState.LETHAL
