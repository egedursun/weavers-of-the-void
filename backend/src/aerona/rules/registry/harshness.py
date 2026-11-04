from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.HARSHNESS


@dataclass(frozen=True)
class HarshnessRules:
    profile: int = rule(1, 0, 2, G, "How harsh the world is: 0 heroic, 1 realistic, 2 brutal")
    heroic_wound_lethality_pct: int = rule(50, 0, 1000, G, "Heroic: how deadly wounds are (%)")
    realistic_wound_lethality_pct: int = rule(100, 0, 1000, G, "Realistic: how deadly wounds are (%)")
    brutal_wound_lethality_pct: int = rule(160, 0, 1000, G, "Brutal: how deadly wounds are (%)")
    heroic_infection_pct: int = rule(50, 0, 1000, G, "Heroic: how often and how deadly wounds fester (%)")
    realistic_infection_pct: int = rule(100, 0, 1000, G, "Realistic: how often and how deadly wounds fester (%)")
    brutal_infection_pct: int = rule(150, 0, 1000, G, "Brutal: how often and how deadly wounds fester (%)")
    heroic_permanent_injury_pct: int = rule(50, 0, 1000, G, "Heroic: how often wounds leave lasting harm (%)")
    realistic_permanent_injury_pct: int = rule(100, 0, 1000, G, "Realistic: how often wounds leave lasting harm (%)")
    brutal_permanent_injury_pct: int = rule(150, 0, 1000, G, "Brutal: how often wounds leave lasting harm (%)")
    heroic_disease_death_pct: int = rule(60, 0, 1000, G, "Heroic: deaths from disease (%)")
    realistic_disease_death_pct: int = rule(100, 0, 1000, G, "Realistic: deaths from disease (%)")
    brutal_disease_death_pct: int = rule(140, 0, 1000, G, "Brutal: deaths from disease (%)")
    heroic_famine_death_pct: int = rule(60, 0, 1000, G, "Heroic: deaths from famine and siege starvation (%)")
    realistic_famine_death_pct: int = rule(100, 0, 1000, G, "Realistic: deaths from famine and siege starvation (%)")
    brutal_famine_death_pct: int = rule(140, 0, 1000, G, "Brutal: deaths from famine and siege starvation (%)")
    heroic_childbirth_death_pct: int = rule(40, 0, 1000, G, "Heroic: deaths in childbirth (%)")
    realistic_childbirth_death_pct: int = rule(100, 0, 1000, G, "Realistic: deaths in childbirth (%)")
    brutal_childbirth_death_pct: int = rule(150, 0, 1000, G, "Brutal: deaths in childbirth (%)")
    heroic_battle_loss_pct: int = rule(70, 0, 1000, G, "Heroic: losses in battle and pursuit (%)")
    realistic_battle_loss_pct: int = rule(100, 0, 1000, G, "Realistic: losses in battle and pursuit (%)")
    brutal_battle_loss_pct: int = rule(130, 0, 1000, G, "Brutal: losses in battle and pursuit (%)")
    heroic_notable_survival_pct: int = rule(200, 0, 1000, G, "Heroic: how much notable figures shrug off deadly harm (%)")
    realistic_notable_survival_pct: int = rule(100, 0, 1000, G, "Realistic: how much notable figures shrug off deadly harm (%)")
    brutal_notable_survival_pct: int = rule(50, 0, 1000, G, "Brutal: how much notable figures shrug off deadly harm (%)")
