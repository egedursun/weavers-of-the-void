from aerona.catalog.peoples import FUNERALS
from aerona.domain.enums.demography import FuneralCustom
from aerona.domain.enums.faith import JudgementDoctrine
from aerona.engine.disease.responses import bodies_left
from aerona.engine.faith.judgement import score_of
from aerona.rules.registry import Rules


def test_every_funeral_custom_is_one_rite_with_typed_properties() -> None:
    assert set(FUNERALS) == set(FuneralCustom)
    assert FUNERALS[FuneralCustom.NAMELESS].seals
    assert not any(FUNERALS[custom].seals for custom in FuneralCustom if custom is not FuneralCustom.NAMELESS)
    assert not FUNERALS[FuneralCustom.NONE].counts_as_rite
    assert FUNERALS[FuneralCustom.SEA_BURIAL].counts_as_rite


def test_only_customs_that_leave_remains_spread_sickness_from_the_dead() -> None:
    assert bodies_left(FuneralCustom.BURIAL)
    assert bodies_left(FuneralCustom.SEA_BURIAL)
    assert not bodies_left(FuneralCustom.CREMATION)
    assert not bodies_left(FuneralCustom.SOUL_BINDING)
    assert bodies_left(FuneralCustom.NONE)
    assert not bodies_left(None)


def test_a_rite_doctrine_rewards_any_kept_custom_and_not_an_unkept_one() -> None:
    table = Rules().afterlife
    kept = score_of(table, {}, JudgementDoctrine.RITE, rite=FuneralCustom.ENTOMBMENT, favoured=False, tenets=set())
    unkept = score_of(table, {}, JudgementDoctrine.RITE, rite=FuneralCustom.NONE, favoured=False, tenets=set())
    assert kept == table.rite_score
    assert unkept == table.no_rite_score
