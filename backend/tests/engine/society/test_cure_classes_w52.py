from aerona.catalog.disease_agents import AGENTS, CURES, MEDICINE_ORDER, OVERUSED
from aerona.db.tables.disease_agents import DiseaseAgentRow
from aerona.domain.enums.disease_agents import CureClass, DiseaseAgent
from aerona.engine.disease.agents import cure_tried, unclean, within_reach
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, settlement, tuned

RULES = Rules()


def test_twelve_cure_classes_each_with_its_place_and_the_two_new_ones_working_on_their_agents() -> None:
    assert len(CURES) == len(CureClass) == 14
    assert CureClass.ANTIVIRAL in AGENTS[DiseaseAgent.VIRUS].cures
    assert CureClass.SURGERY in AGENTS[DiseaseAgent.PARASITE].cures
    assert CureClass.ANTIMICROBIAL not in AGENTS[DiseaseAgent.VIRUS].cures
    assert {CureClass.ANTIVIRAL, CureClass.SURGERY} <= set(MEDICINE_ORDER)
    assert CureClass.ANTIVIRAL in OVERUSED and CureClass.SURGERY not in OVERUSED


def test_an_antiviral_breeds_resistance_faster_and_needs_an_advanced_technique() -> None:
    assert CURES[CureClass.ANTIVIRAL].resistance(RULES) > CURES[CureClass.ANTIMICROBIAL].resistance(RULES)
    assert not within_reach(RULES, CureClass.ANTIVIRAL, RULES.cures.antiviral_level - 1)
    assert within_reach(RULES, CureClass.ANTIVIRAL, RULES.cures.antiviral_level)


def test_cutting_is_riskier_where_healers_know_little() -> None:
    assert unclean(RULES, 0) > unclean(RULES, 8) > unclean(RULES, 10) == 0
    assert unclean(tuned(cures={"surgery_death_pct": 0}), 0) == 0


async def test_healers_reach_for_an_antiviral_only_once_they_can_make_it(realm: Realm) -> None:
    town = await settlement(realm, "Spire", population=4000)
    virus = DiseaseAgentRow(disease_entity_id=1, agent=DiseaseAgent.VIRUS, identified=True, locked=[])
    assert cure_tried(RULES, town, 10, virus) is CureClass.ANTIVIRAL
    assert cure_tried(RULES, town, RULES.disease.identify_level, virus) is not CureClass.ANTIVIRAL
