from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

W = RuleGroup.COSMOS
E = RuleGroup.ENVIRONMENT
A = RuleGroup.APOCALYPSE
F = RuleGroup.FATE_AND_CHRONICLE


@dataclass(frozen=True)
class FormationRules:
    snow_line_tenths: int = rule(27, 1, 1000, W, "Distance of the snow line from a star as bright as the sun, in tenths of the world's orbit unit")
    inner_share: int = rule(80, 1, 100, W, "Share of the snow line inside which a world forms rocky and metal-rich (%)")
    outer_share: int = rule(125, 100, 1000, W, "Share of the snow line beyond which a world forms icy and gas-rich (%)")
    inward_chance: int = rule(25, 0, 100, W, "Chance that the giants of a young system migrated inward, scattering the inner worlds and bringing water (%)")
    outward_chance: int = rule(25, 0, 100, W, "Chance that the giants of a young system migrated outward, leaving the inner worlds dry (%)")
    migration_water: int = rule(35, 0, 100, W, "Water an inward migration brings to an inner world")
    bombardment_per_crater: int = rule(15, 1, 100, W, "Bombardment for each ancient crater a world keeps")
    recorded_craters: int = rule(3, 0, 50, W, "Ancient craters recorded for a world as impacts of its youth")
    mantle_heat_base: int = rule(30, 0, 100, W, "Mantle heat a world keeps from its forming before its core and bombardment")
    exotic_pct: int = rule(20, 0, 100, W, "Share of a world's bombardment that brings it exotic matter (%)")


@dataclass(frozen=True)
class LongSeasonRules:
    chaos_eccentricity: int = rule(25, 1, 100, E, "Eccentricity, in hundredths, from which a world's orbit makes its seasons irregular")
    shortest_spell: int = rule(1, 1, 50, E, "Fewest epochs a long summer or winter lasts")
    longest_spell: int = rule(6, 1, 100, E, "Most epochs a long summer or winter lasts")
    mildest: int = rule(30, 0, 100, E, "Least severity an irregular season can have")
    winter_loss_pct: int = rule(40, 0, 100, E, "Share of a town's food a long winter of full severity eats each epoch (%)")
    prepared_share: int = rule(40, 0, 100, E, "Share of that loss a town suffers when its people heeded a forecast (%)")
    storage_ease_pct: int = rule(50, 0, 100, E, "Share of a long winter's loss that a people's full food stores take off (%)")
    famine_foods_share: int = rule(70, 0, 100, E, "Share of a long winter's loss a town suffers when its people know what the land gives in a failed year (%)")
    scholar_skill: int = rule(3, 0, 10, E, "Astronomy a mortal needs to forecast the end of a long season")
    scholar_error: int = rule(8, 0, 50, E, "Epochs a forecast can miss by, before the scholar's skill")
    heed_base: int = rule(30, 0, 100, E, "Chance a people heeds its scholar's forecast before the scholar's skill (%)")
    heed_per_level: int = rule(8, 0, 100, E, "Chance of heeding a forecast added by each level of the scholar's skill")
    winter_harvest_pct: int = rule(60, 0, 100, E, "Share of a world's harvest a long winter of full severity takes (%)")


@dataclass(frozen=True)
class EcoTransformationRules:
    step: int = rule(5, 0, 100, E, "Points each region moves toward the plan's target each epoch")
    resistance_pct: int = rule(50, 0, 100, E, "Share of the step the world's climate takes back where it pulls against the target (%)")
    sabotage_chance: int = rule(20, 0, 100, E, "Chance each epoch that folk who live from the old land sabotage the work (%)")
    sabotage_loss: int = rule(1, 0, 100, E, "Steps of progress a sabotage undoes; the land it touches also goes back one step")


@dataclass(frozen=True)
class AgeRules:
    carry_pct: int = rule(30, 0, 100, A, "Share of the lore of an ended age that the next age half-remembers (%)")
    echo_weight: int = rule(60, 0, 100, A, "Weight with which the arcs of an ended age's great figures are seeded in the next age")
    echoes_per_age: int = rule(5, 0, 100, A, "Great figures of an ended age who echo into the next")
    rebirth_chance: int = rule(30, 0, 100, A, "Chance each epoch that an unborn echo is reborn into a newborn (%)")
    period_epochs: int = rule(0, 0, 10000, A, "Epochs after which an age turns by itself in a cosmos that turns in ages; 0 lets only the doom clock turn it")


@dataclass(frozen=True)
class ArcRules:
    detect_chance: int = rule(40, 0, 100, F, "Chance each epoch that a pattern in a life is read as the start of an arc (%)")
    arcs_per_epoch: int = rule(6, 0, 1000, F, "Arcs that may start across the cosmos in one epoch")
    open_arcs: int = rule(3, 1, 20, F, "Open arcs one subject may carry at once")
    beats_per_epoch: int = rule(3, 1, 20, F, "Beats an arc may take in one epoch, one for each happening its subject and figures share since its last beat")
    stall_epochs: int = rule(3, 1, 100, F, "Epochs without a beat after which an arc stalls and the drama manager presses it")
    drama_step: int = rule(20, 0, 100, F, "Drama a stalled arc gains each epoch")
    drama_boost: int = rule(50, 0, 500, F, "Share by which full drama raises the chance of the scheme or tale that would bring the next beat (%)")
    counterpoint: int = rule(15, 0, 100, F, "Drama a counterpart's arc gains when its counterpart's arc takes a beat")
    lapse_epochs: int = rule(10, 1, 100, F, "Epochs after which an unpaid setup lapses")
    setup_pull: int = rule(10, 0, 100, F, "Drama an open arc gains each epoch while a setup about its subject waits to be paid off")
