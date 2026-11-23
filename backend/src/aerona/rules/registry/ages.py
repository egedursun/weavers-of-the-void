from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

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
class LongSeasonRules(Spanned):
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
    impact_size_min: int = rule(30, 0, 100, E, "Size of a struck impact from which it brings a long winter instead of a cold snap")
    impact_severity_per_size_pct: int = rule(80, 0, 200, E, "Severity of an impact winter per point of the impact's size (%)")
    eruption_strength_min: int = rule(70, 0, 100, E, "Strength of an eruption from which it brings a long winter instead of a cold snap")
    eruption_world_strength: int = rule(90, 0, 100, E, "Strength of an eruption from which its winter reaches the whole world rather than its half")
    eruption_years_min: int = span(1, 1, 50, E, "Fewest years an eruption winter lasts")
    eruption_years_max: int = span(3, 1, 100, E, "Most years an eruption winter lasts")
    eruption_severity_pct: int = rule(60, 0, 200, E, "Severity of an eruption winter per point of the eruption's strength (%)")
    far_share_pct: int = rule(25, 0, 100, E, "Share of an eruption winter that regions outside its reach still feel (%)")
    stellar_dim_pct: int = rule(10, 1, 100, E, "Fall of a star's brightness in an epoch that brings a long winter to the worlds it lights (%)")
    stellar_bright_pct: int = rule(10, 1, 100, E, "Rise of a star's brightness in an epoch that brings a long summer to the worlds it lights (%)")
    stacking_share_pct: int = rule(30, 0, 100, E, "Share of each weaker spell of the same kind added to the strongest on one world (%)")
    summer_harvest_pct: int = rule(30, 0, 100, E, "Share of the harvest a long summer of full severity takes from hot or dry regions (%)")
    summer_cold_gain_pct: int = rule(15, 0, 100, E, "Harvest a long summer of full severity adds to cold regions (%)")
    summer_heat_shift: int = rule(10, 0, 50, E, "Warmth a long summer of full severity adds to the regions it reaches")
    summer_rain_shift: int = rule(10, 0, 50, E, "Rain a long summer of full severity takes from the regions it reaches")
    summer_sickness_pct: int = rule(10, 0, 100, E, "Rise of the sickness of the season under a long summer of full severity (%)")
    winter_cold_shift: int = rule(15, 0, 50, E, "Warmth a long winter of full severity takes from the regions it reaches")
    weather_shift_pct: int = rule(50, 0, 200, E, "Extra weight of cold weather in a long winter, or hot and dry weather in a long summer, at full severity (%)")
    travel_winter_pct: int = rule(30, 0, 100, E, "Ease of travel a long winter of full severity takes from every season (%)")
    campaign_winter_pct: int = rule(40, 0, 100, E, "Fitness for war a long winter of full severity takes from every season (%)")
    forecast_known_source_pct: int = rule(50, 0, 100, E, "Error a forecast loses when its people watched the source of a single spell (%)")
    ocean_shift_pct: int = rule(2, 0, 100, E, "Chance a turned ocean current brings a long season to its world (%)")
    made_threshold: int = rule(70, 0, 100, E, "Stock of a world's carbon cycle from which the works of its peoples bring a long summer")

    @property
    def eruption_length_min(self) -> int:
        return self.epochs(self.eruption_years_min)

    @property
    def eruption_length_max(self) -> int:
        return self.epochs(self.eruption_years_max)


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
    rise_and_fall_weight: int = rule(50, 0, 100, F, "How readily a life is read as a tale of rise and fall (50 is neutral)")
    rags_to_riches_weight: int = rule(50, 0, 100, F, "How readily a life is read as a tale of rags to riches (50 is neutral)")
    revenge_weight: int = rule(50, 0, 100, F, "How readily a life is read as a tale of revenge (50 is neutral)")
    redemption_weight: int = rule(50, 0, 100, F, "How readily a life is read as a tale of redemption (50 is neutral)")
    quest_weight: int = rule(50, 0, 100, F, "How readily a life is read as a tale of quest (50 is neutral)")
    tragedy_weight: int = rule(50, 0, 100, F, "How readily a life is read as a tale of tragedy (50 is neutral)")
    forbidden_love_weight: int = rule(50, 0, 100, F, "How readily a life is read as a tale of forbidden love (50 is neutral)")
    rivalry_weight: int = rule(50, 0, 100, F, "How readily a life is read as a tale of rivalry (50 is neutral)")
    mentor_and_heir_weight: int = rule(50, 0, 100, F, "How readily a life is read as a tale of mentor and heir (50 is neutral)")
    exile_and_return_weight: int = rule(50, 0, 100, F, "How readily a life is read as a tale of exile and return (50 is neutral)")
    corruption_weight: int = rule(50, 0, 100, F, "How readily a life is read as a tale of corruption (50 is neutral)")
    coming_of_age_weight: int = rule(50, 0, 100, F, "How readily a life is read as a tale of coming of age (50 is neutral)")
    fall_of_a_house_weight: int = rule(50, 0, 100, F, "How readily a life is read as a tale of fall of a house (50 is neutral)")
    founding_weight: int = rule(50, 0, 100, F, "How readily a life is read as a tale of founding (50 is neutral)")
    apotheosis_weight: int = rule(50, 0, 100, F, "How readily a life is read as a tale of apotheosis (50 is neutral)")
    overcoming_weight: int = rule(50, 0, 100, F, "How readily a life is read as a tale of overcoming (50 is neutral)")
    reconciliation_weight: int = rule(50, 0, 100, F, "How readily a life is read as a tale of reconciliation (50 is neutral)")
    sacrifice_weight: int = rule(50, 0, 100, F, "How readily a life is read as a tale of sacrifice (50 is neutral)")
    discovery_weight: int = rule(50, 0, 100, F, "How readily a life is read as a tale of discovery (50 is neutral)")
    open_arcs: int = rule(3, 1, 20, F, "Open arcs one subject may carry at once")
    beats_per_epoch: int = rule(3, 1, 20, F, "Beats an arc may take in one epoch, one for each happening its subject and figures share since its last beat")
    stall_epochs: int = rule(3, 1, 100, F, "Epochs without a beat after which an arc stalls and the drama manager presses it")
    drama_step: int = rule(20, 0, 100, F, "Drama a stalled arc gains each epoch")
    drama_boost: int = rule(50, 0, 500, F, "Share by which full drama raises the chance of the scheme or tale that would bring the next beat (%)")
    counterpoint: int = rule(15, 0, 100, F, "Drama a counterpart's arc gains when its counterpart's arc takes a beat")
    lapse_epochs: int = rule(10, 1, 100, F, "Epochs after which an unpaid setup lapses")
    setup_pull: int = rule(10, 0, 100, F, "Drama an open arc gains each epoch while a setup about its subject waits to be paid off")
