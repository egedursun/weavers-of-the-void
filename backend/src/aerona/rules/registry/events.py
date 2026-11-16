from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.FATE_AND_CHRONICLE


@dataclass(frozen=True)
class EventsRules:
    event_power: int = rule(3, 1, 10, G, "Power of an event that rises from the life of the world (festival, wedding, riot…)")
    emergent_cap: int = rule(12, 0, 200, G, "Most events of one kind that rise from the world's life in one epoch")
    season_match_weight: int = rule(3, 1, 20, G, "How much likelier an event falls in a season that suits it (wet floods, dry fires) (times)")
    severity_neutral: int = rule(50, 1, 100, G, "Event severity at which per-phase harm is applied as written")
    peak_max_epochs: int = rule(3, 1, 50, G, "Most epochs a famine, plague or siege can stay at its height before it turns")
    aftermath_epochs: int = rule(1, 0, 20, G, "Epochs an event spends in its aftermath before it is over")
    memory_pct: int = rule(50, 0, 100, G, "Share of an event's severity that each community it struck keeps as a memory of it once it passes into memory (%)")
    famine_peak_below_harvest: int = rule(70, 0, 200, G, "A famine deepens to its height while the land's harvest stays below this (% of normal)")
    famine_recover_harvest: int = rule(90, 0, 200, G, "A famine passes its height once the harvest is back to this (% of normal)")
    famine_onset_prosperity: int = rule(5, 0, 100, G, "Prosperity lost by the hungry communities when a famine begins")
    famine_peak_death_pct: int = rule(2, 0, 100, G, "Share of the hungry who die in each epoch a famine stays at its height (%)")
    famine_aftermath_disease: int = rule(8, 0, 100, G, "Disease load left in the land by the weakened survivors of a famine")
    plague_peak_death_pct: int = rule(2, 0, 100, G, "Share of the struck communities who die in each epoch a plague stays at its height (%)")
    plague_aftermath_prosperity_pct: int = rule(
        40, 0, 1000, G, "Prosperity gained after a plague per point of the adult workforce it killed (%), as the survivors' labour grows dear"
    )
    plague_aftermath_prosperity_cap: int = rule(12, 0, 100, G, "Most prosperity a community gains in a plague's aftermath")
    siege_peak_rounds: int = rule(2, 1, 50, G, "Siege rounds after which a siege reaches its height")
    siege_peak_starvation_pct: int = rule(3, 0, 100, G, "Share of the besieged who starve in each epoch a starving siege stays at its height (%)")
    siege_aftermath_prosperity: int = rule(6, 0, 100, G, "Prosperity the town loses in a siege's aftermath")
    siege_aftermath_disease: int = rule(6, 0, 100, G, "Disease load a siege leaves in the land around the town")
    festival_population: int = rule(3000, 0, 100000000, G, "Population a town needs before its festival becomes a festival of note")
    festival_unrest_relief: int = rule(6, 0, 100, G, "Unrest a festival of note calms in its town")
    festival_prosperity: int = rule(2, 0, 100, G, "Prosperity a festival of note brings its town")
    coronation_realm_power: int = rule(3, 1, 10, G, "Power of a realm whose new ruler is crowned in a coronation")
    coronation_prosperity: int = rule(2, 0, 100, G, "Prosperity a coronation brings the crowned realm")
    wedding_feast_relation: int = rule(4, 0, 100, G, "Goodwill a royal wedding feast adds between the two houses' communities")
    massacre_haunt_depth: int = rule(20, 0, 100, G, "Haunted ground a massacre leaves on its land")
    sack_burn_depth: int = rule(15, 0, 100, G, "Burned ground a sack leaves on its land")
    fire_burn_depth: int = rule(5, 0, 100, G, "Burned ground a great fire leaves on its land")
    riot_unrest: int = rule(75, 0, 100, G, "Unrest at which a town breaks into riot")
    riot_cooldown_epochs: int = rule(3, 0, 50, G, "Epochs before the same town can riot again")
    riot_death_pct: int = rule(1, 0, 100, G, "Share of a rioting town who die in the riot (%)")
    riot_prosperity: int = rule(4, 0, 100, G, "Prosperity a riot burns away")
    riot_unrest_vent: int = rule(20, 0, 100, G, "Unrest a riot vents")
    schism_council_zeal: int = rule(5, 0, 100, G, "Zeal the breakaway sect gains from the council that split it")
    schism_council_influence: int = rule(3, 0, 100, G, "Influence the old faith loses to the council that split it")
    eclipse_piety: int = rule(2, 0, 100, G, "Piety the communities of a world gain while they watch an eclipse")
