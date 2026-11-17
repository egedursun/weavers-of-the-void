from aerona.catalog.lore import STAGES, TRADITIONS, tradition_spec
from aerona.domain.enums.culture import RiteStage, TraditionFunction
from aerona.domain.enums.mind import ValueAxis


def test_every_tradition_function_and_rite_stage_has_its_own_spec() -> None:
    assert set(TRADITIONS) == set(TraditionFunction)
    assert set(STAGES) == set(RiteStage)


def test_a_rite_of_passage_reads_the_spec_of_its_stage() -> None:
    death = tradition_spec(TraditionFunction.RITE_OF_PASSAGE, RiteStage.DEATH)
    union = tradition_spec(TraditionFunction.RITE_OF_PASSAGE, RiteStage.UNION)
    assert death.effects == {"rite": 1} and death.values == {ValueAxis.DEATH: 1}
    assert union.effects == {"fertility": 5}
    assert tradition_spec(TraditionFunction.RITE_OF_PASSAGE, None) is TRADITIONS[TraditionFunction.RITE_OF_PASSAGE]
    assert tradition_spec(TraditionFunction.FESTIVAL, RiteStage.DEATH) is TRADITIONS[TraditionFunction.FESTIVAL]
