from aerona.catalog.law_areas import LAW_AREAS
from aerona.catalog.laws import LAW_EFFECTS, LAW_PARAMS, defaults_for, law_effect
from aerona.catalog.life.polity import DEFAULT_POWERS, POWER_SKILLS
from aerona.domain.enums.polity import LawKind, OfficeKind, OfficePower


def test_every_law_kind_has_an_area_terms_and_an_effect() -> None:
    assert [kind for kind in LawKind if kind not in LAW_AREAS] == []
    assert [kind for kind in LawKind if kind not in LAW_PARAMS] == []
    assert [kind for kind in LawKind if kind not in LAW_EFFECTS] == []
    for kind in LawKind:
        assert "{" not in law_effect(kind, defaults_for(kind))


def test_every_office_wields_a_power_and_every_power_names_its_office() -> None:
    assert [kind for kind in OfficeKind if kind not in DEFAULT_POWERS] == []
    assert [power for power in OfficePower if power not in POWER_SKILLS] == []
