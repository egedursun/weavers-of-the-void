from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

W = RuleGroup.WEATHER
C = RuleGroup.COSMOS_AND_TRAVEL
L = RuleGroup.RELIGION_AND_LANGUAGE


@dataclass(frozen=True)
class WindRules:
    trade_below: int = rule(30, 0, 90, W, "Latitude below which the winds of a world blow as trade winds")
    polar_above: int = rule(60, 0, 90, W, "Latitude above which the winds of a world blow as polar easterlies")
    single_cell_hours: int = rule(200, 1, 10000, W, "Length of day in hours above which a world turns too slowly for more than one band of winds")
    trade_strength: int = rule(55, 0, 100, W, "Strength of trade winds")
    westerly_strength: int = rule(65, 0, 100, W, "Strength of westerlies")
    polar_strength: int = rule(45, 0, 100, W, "Strength of polar winds")
    single_cell_strength: int = rule(35, 0, 100, W, "Strength of the winds of a world with one band of winds")
    terminator_strength: int = rule(80, 0, 100, W, "Strength of the winds that blow from the day side of a world locked to its light")
    upwind_cosine_pct: int = rule(60, 0, 100, W, "How closely a neighbour must lie toward the wind to count as upwind (cosine, %)")
    shadow: int = rule(25, 0, 100, W, "Rain a land loses in the lee of the highlands upwind of it")
    windward_rain: int = rule(15, 0, 100, W, "Rain a highland gains when moist wind from the sea climbs it")
    pollution_drift_pct: int = rule(20, 0, 100, W, "Share of a land's foul air the wind carries to the land downwind each epoch (%)")
    sail_steady_pct: int = rule(70, 0, 100, W, "Chance a ship meets the prevailing wind of its waters rather than a shifting one (%)")
    fire_wind_pct: int = rule(50, 0, 400, W, "How much more often wildfire strikes a land under a wind of full strength (%)")


@dataclass(frozen=True)
class MonsoonRules:
    lowest_latitude: int = rule(5, 0, 90, W, "Latitude above which a coast can know a monsoon")
    highest_latitude: int = rule(35, 0, 90, W, "Latitude below which a coast can know a monsoon")
    strength: int = rule(30, 0, 100, W, "Strength of the monsoon of a coast where land and sea meet")
    swing: int = rule(60, 0, 200, W, "How far the strength of a year's monsoon swings around the usual (% of the usual)")
    fail_below: int = rule(50, 0, 200, W, "Strength of a year's monsoon below which it fails (% of the usual)")
    rain_pct: int = rule(100, 0, 400, W, "Share of a coast's monsoon strength its rainfall follows (%)")
    famine_prosperity: int = rule(8, 0, 100, W, "Prosperity a town of a monsoon coast loses each time the monsoon fails")
    sea_danger_pct: int = rule(20, 0, 100, W, "Sea danger a failed monsoon adds to the sea roads of its coasts, and a strong one takes off (%)")


@dataclass(frozen=True)
class OscillationRules:
    seed_chance: int = rule(60, 0, 100, W, "Chance a world with seas has a climate oscillation (%)")
    period_min: int = rule(4, 2, 100, W, "Fewest epochs of a full cycle of a climate oscillation")
    period_max: int = rule(9, 2, 100, W, "Most epochs of a full cycle of a climate oscillation")
    strength: int = rule(12, 0, 100, W, "Rain and heat an oscillation shifts at its height")
    latitude_reach: int = rule(35, 0, 90, W, "Latitude within which an oscillation shifts the climate")
    sight_bonus: int = rule(15, 0, 100, W, "Certainty a seer of a people that reads the sky gains in a world with an oscillation")


@dataclass(frozen=True)
class CurrentRules:
    upwelling_catch_pct: int = rule(30, 0, 200, W, "Catch a fishing ground in waters of upwelling gains (%)")
    current_speed_pct: int = rule(15, 0, 100, W, "Sea danger a warm current takes off the sea roads of its coast (%)")
    stowaway_chance: int = rule(5, 0, 100, W, "Chance each epoch that a current carries a living kind of one coast to the next coast it reaches (%)")
    stowaway_abundance: int = rule(10, 0, 100, W, "Abundance a kind carried by a current first holds on the coast it reaches")


@dataclass(frozen=True)
class LaunchWindowRules:
    synodic_min: int = rule(2, 1, 100, C, "Fewest epochs between two windows between worlds")
    synodic_max: int = rule(12, 1, 100, C, "Most epochs between two windows between worlds")
    closed_epochs: int = rule(2, 0, 50, C, "Epochs a journey of a physical way of travel takes beyond the usual when it leaves outside a window")


@dataclass(frozen=True)
class CosmopolitanRules:
    traffic_from: int = rule(20, 0, 100000, C, "Traffic of a road between worlds from which its travellers form a culture of their own")
    join_share: int = rule(20, 0, 100, C, "Share of a member community that belongs to the culture of the road when it joins")
    share_gain: int = rule(5, 0, 100, C, "Share a member community gains each epoch while the road stays busy")
    share_fade: int = rule(5, 0, 100, C, "Share a member community loses each epoch while the road is quiet")
    nativism_ease_pct: int = rule(
        50, 0, 100, C, "Share of the pressure that would stir a people to a movement that its towns' full belonging to a road culture eases (%)"
    )
    value_pull_pct: int = rule(10, 0, 100, L, "Share of the gap to the culture's values a member people closes each epoch at full share (%)")
    lingua_share: int = rule(50, 0, 100, L, "Share of a member community from which it speaks the lingua franca of the road")
