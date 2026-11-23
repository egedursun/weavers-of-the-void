from aerona.catalog.life.made import STANCE_USE
from aerona.domain.enums.made import RelicStance, RelicUse


def test_five_stances_and_study_turns_a_relic_to_new_use() -> None:
    assert len(RelicStance) == 5
    assert STANCE_USE[RelicStance.STUDIED] is RelicUse.REPURPOSED and RelicStance.TOOL not in STANCE_USE
