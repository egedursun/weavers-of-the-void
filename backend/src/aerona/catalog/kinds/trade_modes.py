from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.economy import TradeLoss, TradeMode
from aerona.domain.enums.environment import WeatherEffect

E = WeatherEffect


@dataclass(frozen=True)
class TradeModeSpec:
    words: str
    length_rule: str | None
    weather_rule: str
    exposure: tuple[WeatherEffect, ...]
    waterborne: bool = False
    seagoing: bool = False


TRADE_MODES: Mapping[TradeMode, TradeModeSpec] = total(
    TradeMode,
    {
        TradeMode.ROAD: TradeModeSpec("Road", None, "road_weather_pct", (E.FOOTING, E.COLD, E.HEAT, E.WET)),
        TradeMode.CARAVAN: TradeModeSpec("Caravan Way", None, "caravan_weather_pct", (E.FOOTING, E.HEAT, E.WIND, E.VISIBILITY)),
        TradeMode.RIVER: TradeModeSpec("River Way", "river_length_pct", "river_weather_pct", (E.WET, E.COLD, E.WIND), waterborne=True),
        TradeMode.SKY: TradeModeSpec("Sky Lane", None, "sky_weather_pct", (E.WIND, E.VISIBILITY, E.COLD)),
        TradeMode.SEA: TradeModeSpec("Sea Lane", "sea_length_pct", "sea_weather_pct", (E.WIND, E.VISIBILITY, E.WET), waterborne=True, seagoing=True),
    },
)

TRADE_LOSS_CULPRITS: Mapping[TradeLoss, str | None] = total(
    TradeLoss,
    {TradeLoss.BANDITS: "bandit_id", TradeLoss.BEASTS: "beast_id", TradeLoss.WEATHER: None, TradeLoss.SEA: None},
)
