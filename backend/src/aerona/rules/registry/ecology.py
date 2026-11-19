from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.CREATURES


@dataclass(frozen=True)
class EcologyRules:
    initial_base: int = rule(40, 0, 100, G, "Initial abundance of a species: base")
    initial_fertility_pct: int = rule(40, 0, 100, G, "Share of the land's fertility added to a species' initial abundance (%)")
    initial_megafauna: int = rule(15, 0, 100, G, "Initial abundance of megafauna")
    capacity_base: int = rule(35, 0, 100, G, "Carrying capacity of the land for a species: base")
    capacity_fertility_pct: int = rule(60, 0, 100, G, "Share of the land's fertility added to a species' carrying capacity (%)")
    megafauna_capacity: int = rule(20, 0, 100, G, "Carrying capacity for megafauna")
    reversion_pct: int = rule(10, 0, 100, G, "Per-epoch drift of abundance toward carrying capacity (% of the gap)")
    predation: int = rule(3, 0, 100, G, "Per-epoch abundance pressure of each predator on its prey")
    predation_divisor: int = rule(25, 1, 1000, G, "A predator's abundance divided by this adds to its pressure on its prey")
    hunger_threshold: int = rule(20, 0, 100, G, "A predator whose prey average below this abundance goes hungry")
    hunger: int = rule(4, 0, 100, G, "Per-epoch abundance lost by a hungry predator")
    hunting_population: int = rule(
        30000, 1, 100000000, G, "People in a region whose hunting puts one pressure on its common species; each doubling of them adds about one more"
    )
    hunting_cap: int = rule(20, 0, 1000, G, "Most hunting pressure of communities on one species")
    hunting_danger: int = rule(60, 0, 100, G, "Communities cannot hunt species of this danger or more")
    invasive_pressure: int = rule(4, 0, 100, G, "Abundance pressure of each invasive species on the native species of its region")
    noise: int = rule(5, 1, 100, G, "Random per-epoch abundance swing of a species (plus or minus half of this)")
    critical: int = rule(10, 0, 100, G, "A species below this abundance is endangered")
    last_herd: int = rule(1, 0, 100, G, "Abundance a protected species clings to instead of dying out")
    rewind_abundance: int = rule(20, 0, 100, G, "Abundance a time-rewinding species returns with in the epoch it would die out")
    warning_cap: int = rule(3, 0, 100, G, "Most endangered-species warnings written to the chronicle per epoch")
    wildness_pivot: int = rule(40, 0, 100, RuleGroup.CREATURES, "Wild land (forest and wetland less clearing) at which wild species hold their usual numbers")
    capacity_wildness_pct: int = rule(30, 0, 200, RuleGroup.CREATURES, "Carrying capacity gained per point of wild land above the pivot (%)")
