from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

LINKS = RuleGroup.INTERCONNECTION
MOST_DELAY = 10


@dataclass(frozen=True)
class LoopRules:
    delay_war_weariness: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before war weariness turns into pressure for peace")
    delay_overextension: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before a realm larger than its administration feels the strain of its provinces")
    delay_soil_exhaustion: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before exhausted soil drives its farmers away")
    delay_toll_diversion: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before traffic turns away from high tolls")
    delay_comfort_zeal: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before prosperity cools the zeal of the faithful")
    delay_endemic_immunity: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before an endemic sickness leaves its survivors immune")
    delay_god_neglect: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before a neglected god feels its worshippers fall away")
    delay_predator_prey: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before predators feel the prey they lost")
    delay_debasement: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before debased coin turns merchants against the treasury")
    delay_wonder_envy: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before neighbours envy a wonder")
    delay_regency: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before a regent's ambition grows into a threat to the heir")
    delay_mill_riots: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before unemployment from mills turns into riots")
    delay_tyranny_concessions: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before tyranny raises factions against it")
    delay_glacial_thaw: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before glaciers answer the warming of the air")
    delay_courier_networks: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before slow messages push a realm to faster couriers")
    delay_storyteller_pacing: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before the storyteller answers low tension with disruption")
    delay_squalor_disease: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before squalor in dwellings turns into disease")
    delay_great_person_envy: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before neighbours envy a realm that gathers great people")
    delay_impact_preparation: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before a predicted impact moves people to prepare")
    delay_heroquest_schism: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before a quester's change to a myth splits its faithful")
    delay_gentrification: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before wages answer the poor pushed out of a district")
    delay_precedent_drift: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before harsh case law stirs unrest")
    delay_keystone_hunting: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before hunters feel the loss of a keystone species")
    delay_malthusian: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before wages answer the growth of a population")
    delay_salinisation: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before salted fields lose their yield")
    delay_theodicy: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before a crisis of faith moves its god to act")
    delay_monsoon_migration: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before a failed monsoon drives people away")
    delay_redistribution_collapse: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before the cost of a redistributing centre strains its treasury")
    delay_novelty_drain: int = rule(0, 0, MOST_DELAY, LINKS, "Epochs before a form everyone has loses its freshness")
