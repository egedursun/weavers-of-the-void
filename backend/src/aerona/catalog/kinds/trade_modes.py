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
    navigated: bool = False


TRADE_MODES: Mapping[TradeMode, TradeModeSpec] = total(
    TradeMode,
    {
        TradeMode.ROAD: TradeModeSpec("Road", None, "road_weather_pct", (E.FOOTING, E.COLD, E.HEAT, E.WET)),
        TradeMode.RIVER: TradeModeSpec("River Way", "river_length_pct", "river_weather_pct", (E.WET, E.COLD, E.WIND), waterborne=True),
        TradeMode.SKY: TradeModeSpec("Sky Lane", None, "sky_weather_pct", (E.WIND, E.VISIBILITY, E.COLD), navigated=True),
        TradeMode.SEA: TradeModeSpec(
            "Sea Lane", "sea_length_pct", "sea_weather_pct", (E.WIND, E.VISIBILITY, E.WET), waterborne=True, seagoing=True, navigated=True
        ),
        TradeMode.SPACE: TradeModeSpec("Star Lane", None, "space_weather_pct", ()),
        TradeMode.RIFT: TradeModeSpec("Rift Way", None, "rift_weather_pct", ()),
        TradeMode.NETWORK: TradeModeSpec("Network Link", None, "network_weather_pct", ()),
    },
)

TRADE_LOSS_CULPRITS: Mapping[TradeLoss, str | None] = total(
    TradeLoss,
    {
        TradeLoss.BANDITS: "bandit_id",
        TradeLoss.BEASTS: "beast_id",
        TradeLoss.WEATHER: None,
        TradeLoss.SEA: None,
        TradeLoss.OFFICIALS: "official_id",
        TradeLoss.SPOILAGE: None,
        TradeLoss.PILFERAGE: None,
    },
)


@dataclass(frozen=True)
class LossSpec:
    label: str
    rule: str
    told_by_its_own: bool = False
    reckoned: bool = True


TRADE_LOSSES = total(
    TradeLoss,
    {
        TradeLoss.BANDITS: LossSpec("Bandits", "bandits_pct"),
        TradeLoss.SEA: LossSpec("The sea", "sea_pct", told_by_its_own=True),
        TradeLoss.BEASTS: LossSpec("Beasts", "beasts_pct", told_by_its_own=True),
        TradeLoss.WEATHER: LossSpec("Weather", "weather_pct", told_by_its_own=True),
        TradeLoss.OFFICIALS: LossSpec("Tolls and extortion", "officials_pct", reckoned=False),
        TradeLoss.SPOILAGE: LossSpec("Spoilage", "spoilage_pct", reckoned=False),
        TradeLoss.PILFERAGE: LossSpec("Pilferage", "pilferage_pct", reckoned=False),
    },
)

NAVIGATED_MODES = tuple(mode for mode, spec in TRADE_MODES.items() if spec.navigated)
