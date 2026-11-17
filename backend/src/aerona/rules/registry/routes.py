from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.MARKETS_AND_MONEY


@dataclass(frozen=True)
class RouteDangersRules:
    bandit_region_pct: int = rule(100, 0, 300, G, "Weight of the lands' own danger, the brigands of the wild, in a route's bandit danger (%)")
    bandit_band_danger: int = rule(20, 0, 100, G, "Bandit danger a robber band camped on the way adds")
    beast_danger_pct: int = rule(40, 0, 300, G, "Share of a beast's own danger it adds to a route crossing its land (%)")
    beast_hungry_pct: int = rule(100, 0, 300, G, "Weight of a hungry beast in a route's beast danger (%)")
    beast_territorial_pct: int = rule(80, 0, 300, G, "Weight of a territorial beast in a route's beast danger (%)")
    beast_enraged_pct: int = rule(140, 0, 300, G, "Weight of an enraged beast in a route's beast danger (%)")
    beast_sleeping_pct: int = rule(20, 0, 300, G, "Weight of a sleeping beast in a route's beast danger (%)")
    beast_bound_pct: int = rule(0, 0, 300, G, "Weight of a beast bound to a master in a route's beast danger (%)")
    beast_tamed_pct: int = rule(0, 0, 300, G, "Weight of a tamed beast in a route's beast danger (%)")
    beast_hoard_pct: int = rule(50, 0, 100, G, "Share of the cargo a beast takes that ends in its hoard (%)")
    weather_footing_pct: int = rule(60, 0, 300, G, "Weight of bad footing (mud, snow, ice) in a route's weather danger (%)")
    weather_cold_pct: int = rule(30, 0, 300, G, "Weight of cold in a route's weather danger (%)")
    weather_heat_pct: int = rule(30, 0, 300, G, "Weight of heat in a route's weather danger (%)")
    weather_wet_pct: int = rule(25, 0, 300, G, "Weight of wetness, floods and swollen fords, in a route's weather danger (%)")
    weather_wind_pct: int = rule(40, 0, 300, G, "Weight of wind and storm in a route's weather danger (%)")
    weather_visibility_pct: int = rule(20, 0, 300, G, "Weight of fog and darkness in a route's weather danger (%)")
    road_weather_pct: int = rule(100, 0, 300, G, "How hard foul weather bears on a road (%)")
    caravan_weather_pct: int = rule(120, 0, 300, G, "How hard foul weather bears on a caravan way (%)")
    river_weather_pct: int = rule(100, 0, 300, G, "How hard foul weather bears on a river way (%)")
    sky_weather_pct: int = rule(150, 0, 300, G, "How hard foul weather bears on a sky lane (%)")
    sea_weather_pct: int = rule(100, 0, 300, G, "How hard storms at sea bear on a sea lane (%)")
    sea_danger_base: int = rule(10, 0, 100, G, "Danger of open water on any sea lane")


@dataclass(frozen=True)
class RouteSeasonsRules:
    land_season_pct: int = rule(20, 0, 100, G, "Cargo kept back on a road in its worst travelling season (%)")
    pass_snow_pct: int = rule(35, 0, 100, G, "Cargo kept back when snow closes a mountain pass in the cold season (%)")
    pass_elevation: int = rule(60, 0, 100, G, "Mean height at which a land on the way counts as a high pass")
    caravan_heat_pct: int = rule(25, 0, 100, G, "Cargo kept back on a caravan way in the burning season (%)")
    river_ice_pct: int = rule(40, 0, 100, G, "Cargo kept back when a river way freezes over (%)")
    river_flood_pct: int = rule(25, 0, 100, G, "Cargo kept back when a river way floods in the wet season (%)")
    flood_rain_shift: int = rule(15, 0, 100, G, "Rise of a season's rain over the year's at which rivers flood")
    sky_season_pct: int = rule(30, 0, 100, G, "Cargo kept back on a sky lane in its stormiest season (%)")
    freeze_temperature: int = rule(25, 0, 100, G, "Temperature of a season below which rivers freeze and passes fill with snow")
    burning_temperature: int = rule(75, 0, 100, G, "Temperature of a season above which traffic on a caravan way rests through the heat")


@dataclass(frozen=True)
class ChokepointsRules:
    strategic_share_pct: int = rule(
        20, 0, 100, G, "Share of a route's cargo in strategic goods (metal, arms, mounts, reagents) that makes a road with no other way a chokepoint (%)"
    )
    war_chance: int = rule(8, 0, 100, G, "A strong merchant power goes to war over an overtaxed chokepoint (% per epoch)")
    blockade_aim_score: int = rule(15, 0, 100, G, "Score a blockade earns toward the blockader's aim of seizing the route")


@dataclass(frozen=True)
class SentientPactsRules:
    pact_epochs: int = rule(6, 1, 100, G, "Epochs a pact with a sentient resource lasts")
    every_epochs: int = rule(2, 1, 100, G, "Epochs between the tributes a sentient resource is owed under a pact")
    discount_pct_per_level: int = rule(5, 0, 100, G, "Share a negotiator's skill level takes off a sentient resource's demand when a pact is struck (%)")
    honour_reserve_pct: int = rule(4, 0, 100, G, "Reserve a sentient resource yields up when its pact is honoured (% of its first reserve)")
    honour_prosperity: int = rule(3, 0, 100, G, "Prosperity an owner gains when it honours a pact with a sentient resource")
    wrath_prosperity: int = rule(12, 0, 100, G, "Prosperity an owner loses when it breaks a pact with a sentient resource")
    wrath_reserve_pct: int = rule(10, 0, 100, G, "Reserve a wrathful sentient resource withholds when its pact is broken (% of its first reserve)")


@dataclass(frozen=True)
class SonRoutesRules:
    open_cost: int = rule(25, 0, 1000, RuleGroup.SON_TOOLS, "open_trade_route cost (essence)")
    open_ap: int = rule(1, 1, 5, RuleGroup.SON_TOOLS, "open_trade_route action cost")
    close_cost: int = rule(20, 0, 1000, RuleGroup.SON_TOOLS, "close_trade_route cost (essence)")
    close_ap: int = rule(1, 1, 5, RuleGroup.SON_TOOLS, "close_trade_route action cost")
