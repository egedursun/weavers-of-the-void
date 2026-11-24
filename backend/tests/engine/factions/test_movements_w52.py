from aerona.catalog.movement_causes import ENACTED, LAW_TARGETS, MOVEMENT_CAUSES
from aerona.domain.enums.faction import MovementCause
from aerona.domain.enums.polity import LawKind
from aerona.engine.factions.movements import PRESSURES


def test_twelve_movement_causes_each_with_a_pressure_and_a_goal() -> None:
    assert len(MOVEMENT_CAUSES) == len(MovementCause) == 14
    assert set(PRESSURES) == set(MovementCause)
    assert ENACTED[MovementCause.LABOUR] is LawKind.LABOUR_LAW
    assert ENACTED[MovementCause.MIND_RIGHTS] is LawKind.MIND_STATUS
    assert LAW_TARGETS[MovementCause.ABOLITION] is LawKind.SLAVERY
    assert MOVEMENT_CAUSES[MovementCause.LABOUR].founds_union and MOVEMENT_CAUSES[MovementCause.TEMPERANCE].curbs_intoxicants
