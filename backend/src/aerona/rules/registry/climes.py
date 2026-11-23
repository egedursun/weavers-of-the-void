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
    trade_rain_pct: int = rule(0, -100, 100, W, "Trade winds: rain they bring or take (%)")
    trade_sailing_pct: int = rule(10, -100, 100, W, "Trade winds: how much they speed or slow ships (%)")
    westerly_rain_pct: int = rule(10, -100, 100, W, "Westerlies: rain they bring or take (%)")
    westerly_sailing_pct: int = rule(5, -100, 100, W, "Westerlies: how much they speed or slow ships (%)")
    polar_rain_pct: int = rule(0, -100, 100, W, "Polar easterlies: rain they bring or take (%)")
    polar_sailing_pct: int = rule(-10, -100, 100, W, "Polar easterlies: how much they speed or slow ships (%)")
    single_cell_rain_pct: int = rule(0, -100, 100, W, "One band: rain they bring or take (%)")
    single_cell_sailing_pct: int = rule(0, -100, 100, W, "One band: how much they speed or slow ships (%)")
    terminator_rain_pct: int = rule(-10, -100, 100, W, "Terminator winds: rain they bring or take (%)")
    terminator_sailing_pct: int = rule(0, -100, 100, W, "Terminator winds: how much they speed or slow ships (%)")
    still_strength: int = rule(0, 0, 100, W, "Strength of the still air")
    still_rain_pct: int = rule(0, -100, 100, W, "Still air: rain they bring or take (%)")
    still_sailing_pct: int = rule(-50, -100, 100, W, "Still air: how much they speed or slow ships (%)")
    doldrums_strength: int = rule(10, 0, 100, W, "Strength of the doldrums")
    doldrums_rain_pct: int = rule(60, -100, 100, W, "Doldrums: rain they bring or take (%)")
    doldrums_sailing_pct: int = rule(-60, -100, 100, W, "Doldrums: how much they speed or slow ships (%)")
    subtropical_calm_strength: int = rule(15, 0, 100, W, "Strength of the subtropical calm")
    subtropical_calm_rain_pct: int = rule(-60, -100, 100, W, "Subtropical calm: rain they bring or take (%)")
    subtropical_calm_sailing_pct: int = rule(-30, -100, 100, W, "Subtropical calm: how much they speed or slow ships (%)")
    banded_strength: int = rule(85, 0, 100, W, "Strength of the banded winds")
    banded_rain_pct: int = rule(10, -100, 100, W, "Banded winds: rain they bring or take (%)")
    banded_sailing_pct: int = rule(-20, -100, 100, W, "Banded winds: how much they speed or slow ships (%)")
    super_rotation_strength: int = rule(70, 0, 100, W, "Strength of the super rotation")
    super_rotation_rain_pct: int = rule(0, -100, 100, W, "Super rotation: rain they bring or take (%)")
    super_rotation_sailing_pct: int = rule(10, -100, 100, W, "Super rotation: how much they speed or slow ships (%)")
    doldrums_width: int = rule(5, 0, 30, W, "Latitude on either side of the equator the doldrums span")
    subtropical_latitude: int = rule(30, 10, 50, W, "Latitude of the calm dry belt between trade winds and westerlies")
    banded_rotation_hours: int = rule(15, 1, 100, W, "Length of day below which a thick atmosphere breaks into many bands")
    super_rotation_day_hours: int = rule(500, 24, 10000, W, "Length of day above which a thick atmosphere circles its world faster than the ground")
    thick_pressure_tenths: int = rule(20, 1, 1000, W, "Air pressure, in tenths of an ordinary world, from which an atmosphere counts as thick")
    seasonal_shift: int = rule(5, 0, 30, W, "Latitude the belts move toward the warm half of a world in its summer")
    band_rain_points: int = rule(20, 0, 100, W, "Rain a belt at its full rain share moves")
    becalmed_pct: int = rule(20, 0, 100, W, "Chance a ship crossing still or calm air lies becalmed (%)")


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
    none_temperature: int = rule(0, -100, 100, W, "Warmth a none current gives its coast")
    none_sailing_pct: int = rule(0, -100, 100, W, "How much a none current speeds or slows ships (%)")
    none_danger: int = rule(0, -100, 100, W, "Danger a none current adds to the waters it runs through")
    warm_temperature: int = rule(4, -100, 100, W, "Warmth a warm current gives its coast")
    warm_sailing_pct: int = rule(15, -100, 100, W, "How much a warm current speeds or slows ships (%)")
    warm_danger: int = rule(0, -100, 100, W, "Danger a warm current adds to the waters it runs through")
    cold_temperature: int = rule(-4, -100, 100, W, "Warmth a cold current gives its coast")
    cold_sailing_pct: int = rule(0, -100, 100, W, "How much a cold current speeds or slows ships (%)")
    cold_danger: int = rule(5, -100, 100, W, "Danger a cold current adds to the waters it runs through")
    upwelling_temperature: int = rule(-6, -100, 100, W, "Warmth a upwelling current gives its coast")
    upwelling_sailing_pct: int = rule(-5, -100, 100, W, "How much a upwelling current speeds or slows ships (%)")
    upwelling_danger: int = rule(5, -100, 100, W, "Danger a upwelling current adds to the waters it runs through")
    tidal_temperature: int = rule(0, -100, 100, W, "Warmth a tidal current gives its coast")
    tidal_sailing_pct: int = rule(-20, -100, 100, W, "How much a tidal current speeds or slows ships (%)")
    tidal_danger: int = rule(25, -100, 100, W, "Danger a tidal current adds to the waters it runs through")
    upwelling_fish_pct: int = rule(80, 0, 300, W, "Fish an upwelling coast gains (%)")
    upwelling_rain_cut_pct: int = rule(30, 0, 100, W, "Rain an upwelling coast loses to the cold sea (%)")
    tidal_strength_min: int = rule(40, 0, 100, W, "Tidal strength from which narrow seas run with tidal streams")
    warm_phase_upwelling_cut_pct: int = rule(50, 0, 100, W, "Share of an upwelling's catch a warm phase of the oscillation takes (%)")


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
