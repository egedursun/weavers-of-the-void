from aerona.catalog.lore import LEGEND_MORALS, TRADITIONS
from aerona.catalog.mythic import ARCHETYPE_REALMS, ARCHETYPE_SKILLS, ARCHETYPE_TRIALS
from aerona.catalog.rumours import LEGEND_PREFIXES, legend_archetype
from aerona.domain.enums.culture import LegendArchetype, TraditionFunction
from aerona.domain.enums.faith import ClergyFunction
from aerona.engine.faith.doctrine import CLERGY_DUTIES
from aerona.engine.lore.calendar_rites import SEASON_OF


def test_every_legend_shape_has_its_realm_trials_skills_and_morals_and_a_happening_that_tells_it() -> None:
    told = set(LEGEND_PREFIXES.values())
    for archetype in LegendArchetype:
        assert archetype in ARCHETYPE_REALMS and archetype in ARCHETYPE_TRIALS and archetype in ARCHETYPE_SKILLS
        assert archetype in LEGEND_MORALS, archetype
    for archetype in (LegendArchetype.FOUNDING, LegendArchetype.UNION, LegendArchetype.FALL, LegendArchetype.DECEPTION, LegendArchetype.DISCOVERY):
        assert archetype in told, archetype
    assert legend_archetype("kin.marriage") is LegendArchetype.UNION
    assert legend_archetype("intrigue.scheme_exposed") is LegendArchetype.DECEPTION


def test_every_tradition_function_has_its_effects_and_a_season() -> None:
    for kind in TraditionFunction:
        assert kind in TRADITIONS, kind
    for kind in (TraditionFunction.GIFT_CUSTOM, TraditionFunction.PURIFICATION, TraditionFunction.COMMEMORATION, TraditionFunction.COMPETITION):
        assert kind in SEASON_OF and TRADITIONS[kind].effects


def test_every_clergy_function_has_a_duty_and_the_new_ones_follow_a_tenet() -> None:
    assert set(CLERGY_DUTIES) == set(ClergyFunction)
    for kind in (ClergyFunction.TEACHER, ClergyFunction.HEALER, ClergyFunction.MISSIONARY, ClergyFunction.JUDGE, ClergyFunction.SCRIBE):
        assert CLERGY_DUTIES[kind].tenets
