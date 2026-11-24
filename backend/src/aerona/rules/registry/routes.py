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
    weather_lightning_pct: int = rule(15, 0, 300, G, "Weight of lightning in a route's weather danger (%)")
    weather_flood_pct: int = rule(40, 0, 300, G, "Weight of rising water in a route's weather danger (%)")
    weather_breath_pct: int = rule(20, 0, 300, G, "Weight of air unfit to breathe in a route's weather danger (%)")
    road_weather_pct: int = rule(100, 0, 300, G, "How hard foul weather bears on a road (%)")
    carrier_full_capacity: int = rule(10, 1, 200, G, "Carrying power of a carrier that lets a road move its whole capacity; a weaker carrier moves its share")
    contested_loss_pct: int = rule(30, 0, 100, G, "Extra share of cargo a route fought over loses while its sides fight (%)")
    bandits_pct: int = rule(100, 0, 300, G, "Bandit danger on a route against its reckoning from the lands, beasts and weather it crosses (%)")
    sea_pct: int = rule(100, 0, 300, G, "Danger of the sea on a route against its reckoning from the lands, beasts and weather it crosses (%)")
    beasts_pct: int = rule(100, 0, 300, G, "Beast danger on a route against its reckoning from the lands, beasts and weather it crosses (%)")
    weather_pct: int = rule(100, 0, 300, G, "Weather danger on a route against its reckoning from the lands, beasts and weather it crosses (%)")
    officials_pct: int = rule(
        20, 0, 300, G, "Share of a route's goods taken by tolls, bribes and extortion at the full corruption of the realms it crosses (%)"
    )
    spoilage_pct: int = rule(10, 0, 100, G, "Share of a long route's goods that spoils on the way where nothing keeps them (%)")
    pilferage_pct: int = rule(8, 0, 100, G, "Share of a route's goods its guards and crews take where no patrol watches (%)")
    caravan_weather_pct: int = rule(120, 0, 300, G, "How hard foul weather bears on a road through arid land served by pack carriers (%)")
    space_weather_pct: int = rule(0, 0, 300, G, "How hard foul weather bears on a star lane (%)")
    rift_weather_pct: int = rule(0, 0, 300, G, "How hard foul weather bears on a rift way (%)")
    network_weather_pct: int = rule(0, 0, 300, G, "How hard foul weather bears on a network link (%)")
    river_weather_pct: int = rule(100, 0, 300, G, "How hard foul weather bears on a river way (%)")
    sky_weather_pct: int = rule(150, 0, 300, G, "How hard foul weather bears on a sky lane (%)")
    sea_weather_pct: int = rule(100, 0, 300, G, "How hard storms at sea bear on a sea lane (%)")
    sea_danger_base: int = rule(10, 0, 100, G, "Danger of open water on any sea lane")
    beast_migrating_pct: int = rule(80, 0, 300, G, "Weight of a beast passing along a route on its seasonal path among the dangers of the route (%)")
    underground_weather_pct: int = rule(10, 0, 300, G, "Weight of weather on a tunnel way, which lies under the ground (%)")
    pirates_pct: int = rule(100, 0, 300, G, "Pirate danger on a water route against its reckoning from the raiders and havens on the way (%)")
    pirate_haven_danger: int = rule(15, 0, 100, G, "Pirate danger each lawless coast on a water route adds")
    breakage_pct: int = rule(100, 0, 300, G, "Weight of breakage of fragile cargo on a route (%)")
    breakage_base: int = rule(3, 0, 100, G, "Share of fragile cargo broken on a route before its containers and ground are weighed (%)")


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
