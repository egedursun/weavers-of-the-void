from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

G = RuleGroup.COSMOS


@dataclass(frozen=True)
class SpaceWeatherRules(Spanned):
    flare_base_pct: int = rule(5, 0, 100, G, "Chance each epoch that an active star sends a flare to a world it lights (%)")
    storm_base_pct: int = rule(3, 0, 100, G, "Chance each epoch that an active star sends a particle storm, a field storm or a wind surge to a world (%)")
    burst_base_pct: int = rule(1, 0, 100, G, "Chance each epoch that a burst of rays from far away reaches a world (%)")
    shield_per_field_point: int = rule(1, 0, 5, G, "Shielding each point of a world's magnetic field gives against space weather")
    shield_per_air_point: int = rule(1, 0, 5, G, "Shielding each point of a world's upper air gives against space weather")
    outage_threshold: int = rule(40, 0, 100, G, "Dose at a world's surface at which its signals and networks fail")
    compass_error_threshold: int = rule(30, 0, 100, G, "Dose or field weakness at which compasses err and navigation is lost")
    dose_harm_per_point: int = rule(1, 0, 20, G, "Health lost by a mortal of the world for each ten points of dose past the outage threshold")
    mutation_per_dose_pct: int = rule(1, 0, 100, G, "Mutation chance a kind of life of the world gains for each ten points of dose (%)")
    crop_dose: int = rule(80, 0, 100, G, "Dose at which crops and herds of the world suffer")
    crop_loss: int = rule(2, 0, 50, G, "Prosperity a town of the world loses when crops and herds suffer")
    reversal_chance_per_epoch_pct: int = rule(1, 0, 100, G, "Chance each epoch that a world's magnetic field reverses (%)")
    reversal_years: int = span(50, 1, 5000, G, "Years a field reversal weakens a world's shield")
    reversal_shield_loss: int = rule(30, 0, 100, G, "Shielding a world loses while its field reverses")
    cycle_years: int = span(11, 1, 1000, G, "Years of a star's cycle of activity for a star whose cycle no one set")
    aurora_per_strength: int = rule(1, 0, 5, G, "How far toward the equator auroras reach for each point of an event's strength past the shield")
    omen_piety: int = rule(2, 0, 20, G, "Piety a community of a world gains when it reads a field reversal or a great aurora as an omen")
    shield_change_max: int = rule(100, 0, 100, G, "Most a god can strengthen or strip a world's field in one deed")
