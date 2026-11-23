from aerona.catalog.harm_kinds import STEPS
from aerona.db.tables.body import InjuryRow
from aerona.domain.enums.body import InjuryKind, InjuryState, TreatmentStep
from aerona.engine.body.treatment import wanted_steps


def test_thirteen_steps_and_the_three_new_ones_are_told() -> None:
    assert len(TreatmentStep) == len(STEPS) == 13
    assert all(STEPS[step].noted for step in (TreatmentStep.DRAIN, TreatmentStep.BLEED, TreatmentStep.MEDICATE))


def test_a_festering_wound_is_drained_and_given_a_remedy_and_bloodletters_bleed_it() -> None:
    festering = InjuryRow(kind=InjuryKind.CUT, state=InjuryState.GANGRENOUS, bleeding=0, treatments=[])
    wanted = wanted_steps(festering, walking=False)
    assert TreatmentStep.DRAIN in wanted and TreatmentStep.MEDICATE in wanted and TreatmentStep.BLEED not in wanted
    assert TreatmentStep.BLEED in wanted_steps(festering, walking=False, bleeds=True)
    fresh = InjuryRow(kind=InjuryKind.CUT, state=InjuryState.FRESH, bleeding=0, treatments=[])
    assert TreatmentStep.DRAIN not in wanted_steps(fresh, walking=False)
