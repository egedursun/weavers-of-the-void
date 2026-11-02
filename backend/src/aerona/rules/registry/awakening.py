from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class AwakeningRules:
    batch_cap: int = rule(
        3, 1, 20, RuleGroup.AWAKENING_OF_THE_PEOPLES, "Maximum peoples in one awakening batch (one model call); more requested are split into batches"
    )
    timeout: int = rule(300, 30, 3600, RuleGroup.AGENTS_AND_MODEL, "Awakening of the peoples timeout (s)")
    words_min: int = rule(6, 0, 100, RuleGroup.AWAKENING_OF_THE_PEOPLES, "Minimum words of a new language")
    words_max: int = rule(10, 1, 200, RuleGroup.AWAKENING_OF_THE_PEOPLES, "Maximum words of a new language")
    people_power: int = rule(4, 1, 11, RuleGroup.AWAKENING_OF_THE_PEOPLES, "Power level of an awakened people")
    first_peoples: int = rule(2, 1, 1000, RuleGroup.AWAKENING_OF_THE_PEOPLES, "Peoples awakening automatically at startup on a world without peoples")
    people_population: int = rule(20000, 1, 1000000000, RuleGroup.AWAKENING_OF_THE_PEOPLES, "People's population (if the model gives none)")
    people_population_min: int = rule(500, 1, 1000000000, RuleGroup.AWAKENING_OF_THE_PEOPLES, "Minimum population of an awakened people")
    people_population_max: int = rule(5000000, 1, 2000000000, RuleGroup.AWAKENING_OF_THE_PEOPLES, "Maximum population of an awakened people")
    people_martiality: int = rule(40, 0, 100, RuleGroup.AWAKENING_OF_THE_PEOPLES, "People's martiality (if the model gives none)")
    people_magic: int = rule(30, 0, 100, RuleGroup.AWAKENING_OF_THE_PEOPLES, "People's magic (if the model gives none)")
    people_craft: int = rule(45, 0, 100, RuleGroup.AWAKENING_OF_THE_PEOPLES, "People's craft (if the model gives none)")
    people_piety: int = rule(60, 0, 100, RuleGroup.AWAKENING_OF_THE_PEOPLES, "People's piety")
    language_spread: int = rule(30, 0, 100, RuleGroup.AWAKENING_OF_THE_PEOPLES, "New language spread")
    language_complexity: int = rule(45, 0, 100, RuleGroup.AWAKENING_OF_THE_PEOPLES, "New language complexity")
    language_sacredness: int = rule(25, 0, 100, RuleGroup.AWAKENING_OF_THE_PEOPLES, "New language sacredness")
    language_power: int = rule(3, 1, 11, RuleGroup.AWAKENING_OF_THE_PEOPLES, "New language power level")
    settlement_population: int = rule(3000, 1, 1000000000, RuleGroup.AWAKENING_OF_THE_PEOPLES, "First settlement population (if the model gives none)")
    settlement_population_min: int = rule(100, 1, 1000000000, RuleGroup.AWAKENING_OF_THE_PEOPLES, "Minimum population of the first settlement")
    settlement_population_max: int = rule(500000, 1, 2000000000, RuleGroup.AWAKENING_OF_THE_PEOPLES, "Maximum population of the first settlement")
    settlement_prosperity: int = rule(45, 0, 100, RuleGroup.AWAKENING_OF_THE_PEOPLES, "Prosperity of the first settlement")
    settlement_defense: int = rule(30, 0, 100, RuleGroup.AWAKENING_OF_THE_PEOPLES, "Defense of the first settlement")
    settlement_piety: int = rule(60, 0, 100, RuleGroup.AWAKENING_OF_THE_PEOPLES, "Piety of the first settlement")
    settlement_power: int = rule(3, 1, 11, RuleGroup.AWAKENING_OF_THE_PEOPLES, "Power level of the first settlement")
    resource_abundance: int = rule(70, 0, 100, RuleGroup.AWAKENING_OF_THE_PEOPLES, "Abundance of the people's resource")
    resource_value: int = rule(50, 0, 100, RuleGroup.AWAKENING_OF_THE_PEOPLES, "Value of the people's resource")
    resource_might: int = rule(35, 0, 100, RuleGroup.AWAKENING_OF_THE_PEOPLES, "Might of the people's resource")
    resource_power: int = rule(3, 1, 11, RuleGroup.AWAKENING_OF_THE_PEOPLES, "Power level of the people's resource")
    knowledge_level: int = rule(1, 1, 100, RuleGroup.AWAKENING_OF_THE_PEOPLES, "Level of the people's first knowledge")
    knowledge_spread: int = rule(20, 0, 100, RuleGroup.AWAKENING_OF_THE_PEOPLES, "Spread of the people's first knowledge")
    knowledge_power: int = rule(2, 1, 11, RuleGroup.AWAKENING_OF_THE_PEOPLES, "Power level of the people's first knowledge")
    tradition_spread: int = rule(60, 0, 100, RuleGroup.AWAKENING_OF_THE_PEOPLES, "Spread of the people's tradition")
    tradition_rigidity: int = rule(50, 0, 100, RuleGroup.AWAKENING_OF_THE_PEOPLES, "Rigidity of the people's tradition")
    tradition_power: int = rule(2, 1, 11, RuleGroup.AWAKENING_OF_THE_PEOPLES, "Power level of the people's tradition")
