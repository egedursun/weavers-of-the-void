from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.urban import MarketPlay

MARKET_PLAY = total(
    MarketPlay,
    {
        MarketPlay.CORNER: Defined(
            "Cornered",
            checked_by=("engine.economy.manipulation.swing",),
            used_by=("engine.economy.manipulation.play_markets", "engine.media.press.alarm", "tools.mortal.urban_depth.corner_market"),
        ),
        MarketPlay.DUMP: Defined("Flooded", checked_by=(), used_by=("engine.economy.manipulation.play_markets",)),
    },
)
