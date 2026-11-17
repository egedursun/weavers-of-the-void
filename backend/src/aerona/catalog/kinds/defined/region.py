from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.region import DangerHarm, HazardSeason

DANGER_HARM = total(
    DangerHarm,
    {
        DangerHarm.SETTLERS: Defined(
            "Settlers", checked_by=("engine.environment.dangers.HARM_WEIGHTS",), used_by=("engine.environment.perils.strike_community",)
        ),
        DangerHarm.LIVESTOCK: Defined(
            "Livestock", checked_by=("engine.environment.dangers.HARM_WEIGHTS",), used_by=("engine.environment.perils.strike_community",)
        ),
        DangerHarm.TRAVELLERS: Defined("Travellers", checked_by=("engine.environment.dangers.HARM_WEIGHTS",), used_by=("engine.phases.travel.road_event",)),
        DangerHarm.ARMIES: Defined("Armies", checked_by=("engine.environment.dangers.HARM_WEIGHTS",), used_by=("engine.environment.perils.danger_toll",)),
        DangerHarm.AMBUSH: Defined("Ambush", checked_by=("engine.environment.dangers.HARM_WEIGHTS",), used_by=("engine.environment.perils.danger_toll",)),
        DangerHarm.MERCHANTS: Defined("Merchants", checked_by=("engine.environment.dangers.HARM_WEIGHTS",), used_by=("engine.phases.commerce.trade_flow",)),
    },
)

HAZARD_SEASON = total(
    HazardSeason,
    {
        HazardSeason.COLDEST: Defined("Coldest", checked_by=("engine.environment.hazards.season_for",), used_by=("catalog.dangers.HAZARDS",)),
        HazardSeason.WETTEST: Defined("Wettest", checked_by=("engine.environment.hazards.season_for",), used_by=("catalog.dangers.HAZARDS",)),
        HazardSeason.HOTTEST: Defined("Hottest", checked_by=(), used_by=("catalog.dangers.HAZARDS",)),
    },
)
