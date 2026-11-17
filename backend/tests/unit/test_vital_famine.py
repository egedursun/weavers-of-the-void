from aerona.catalog.reproduction import SEX_SYSTEMS
from aerona.db.tables.demography import CohortRow
from aerona.domain.enums.cycles import ReproductiveSystem
from aerona.domain.enums.demography import AgeBand, CohortCondition, Sex
from aerona.domain.enums.society import SocialClass
from aerona.engine.demography.vital import Pressures, one_year
from aerona.rules.registry import Rules


def cohorts() -> dict:
    rows = {}
    for band, count in ((AgeBand.CHILD, 30000), (AgeBand.ADULT, 50000), (AgeBand.ELDER, 20000)):
        for sex in (Sex.MALE, Sex.FEMALE):
            key = (band, sex, SocialClass.FARMER, CohortCondition.NONE)
            rows[key] = CohortRow(community_entity_id=1, age_band=band, sex=sex, social_class=SocialClass.FARMER, condition=CohortCondition.NONE, count=count)
    return rows


def deaths_at(hunger: float, disease: float = 0.0) -> int:
    year = one_year(
        Rules(),
        cohorts(),
        None,
        Pressures(fertility=1.0, hunger=hunger, crowding=0.0, disease=disease, stress=0.0, mortality=1.0),
        SEX_SYSTEMS[ReproductiveSystem.TWO_SEX],
    )
    return sum(year.deaths.values())


def test_a_lean_year_kills_few_while_a_true_famine_still_kills_many() -> None:
    rules = Rules()
    fed = deaths_at(0.0)
    lean = deaths_at(0.25)
    starved = deaths_at(1.0)
    assert lean < fed * (1 + 0.25 * rules.demography.hunger_death_pct / 100 / 2)
    assert starved >= fed * (1 + rules.demography.hunger_death_pct / 100) * 0.95
