from aerona.catalog.conditions import FESTERING, FRESH_STATES, OPEN_INJURY_STATES, STATES
from aerona.db.tables.body import InjuryRow
from aerona.domain.enums.body import InjuryState, TreatmentStep
from aerona.engine.body.healing import bled, remedied
from aerona.rules.registry import Rules
from tests.engine.society.factories import tuned

RULES = Rules()


def test_eight_states_with_gangrene_between_festering_and_death() -> None:
    assert len(InjuryState) == len(STATES) == 9
    assert {InjuryState.INFECTED, InjuryState.GANGRENOUS} == FESTERING
    assert {InjuryState.FRESH, InjuryState.REOPENED} == FRESH_STATES
    assert {InjuryState.GANGRENOUS, InjuryState.REOPENED} <= OPEN_INJURY_STATES
    assert STATES[InjuryState.INFECTED].rank < STATES[InjuryState.GANGRENOUS].rank < STATES[InjuryState.LETHAL].rank


def test_bloodletting_harms_unless_the_world_says_otherwise_and_a_remedy_helps() -> None:
    bloodied = InjuryRow(treatments=[TreatmentStep.BLEED.value])
    plain = InjuryRow(treatments=[])
    assert bled(RULES, bloodied) > 1.0 > remedied(RULES, bloodied)
    assert bled(RULES, plain) == 1.0 == remedied(RULES, plain)
    kind = tuned(treatment={"bleed_harm_pct": -20})
    assert bled(kind, bloodied) < 1.0 < remedied(kind, bloodied)
    assert remedied(RULES, InjuryRow(treatments=[TreatmentStep.MEDICATE.value])) > 1.0
