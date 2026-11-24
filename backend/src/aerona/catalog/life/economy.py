from collections.abc import Callable, Mapping
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.body import DamageType, MaimedKind
from aerona.domain.enums.demography import Job
from aerona.domain.enums.economy import ExtractionKind, HazardKind, MoneyForm, TradeLoss, TradeRouteStatus
from aerona.domain.enums.environment import WeatherEffect
from aerona.domain.enums.evolution import PlagueResponse
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.urban import ConvoyStatus
from aerona.rules.registry import Rules

LIVE = (TradeRouteStatus.FORMING, TradeRouteStatus.OPEN, TradeRouteStatus.BLOCKADED, TradeRouteStatus.CONTESTED, TradeRouteStatus.SEASONAL)
CONTESTABLE = (TradeRouteStatus.OPEN, TradeRouteStatus.CONTESTED)


OPEN = (ConvoyStatus.LOADING, ConvoyStatus.TRAVELLING, ConvoyStatus.DELAYED, ConvoyStatus.STRANDED, ConvoyStatus.QUARANTINED)
CONVOY_WORDS = total(
    ConvoyStatus,
    {
        ConvoyStatus.LOADING: "loading",
        ConvoyStatus.TRAVELLING: "on the way",
        ConvoyStatus.DELAYED: "delayed",
        ConvoyStatus.ARRIVED: "arrived",
        ConvoyStatus.RAIDED: "raided",
        ConvoyStatus.LOST: "lost",
        ConvoyStatus.STRANDED: "stranded by the season",
        ConvoyStatus.QUARANTINED: "held in quarantine",
        ConvoyStatus.TURNED_BACK: "turned back",
    },
)
SHUTTING_RESPONSES = (PlagueResponse.CLOSE_BORDERS, PlagueResponse.QUARANTINE)


BRANCH_OF: dict[ExtractionKind, KnowledgeBranch] = {
    ExtractionKind.MINING: KnowledgeBranch.METALLURGY,
    ExtractionKind.QUARRYING: KnowledgeBranch.ARCHITECTURE,
    ExtractionKind.FISHING: KnowledgeBranch.SEAFARING,
    ExtractionKind.FARMING: KnowledgeBranch.AGRICULTURE,
    ExtractionKind.HERDING: KnowledgeBranch.AGRICULTURE,
}


HAZARD_HARM: Mapping[HazardKind, tuple[DamageType, str, int]] = total(
    HazardKind,
    {
        HazardKind.CAVE_IN: (DamageType.BLUNT, "crushed in a cave-in", 40),
        HazardKind.FLOODED_SHAFT: (DamageType.COLD, "drowned in a flooded shaft", 30),
        HazardKind.FELLING_ACCIDENT: (DamageType.BLUNT, "struck by a falling tree", 30),
        HazardKind.DROWNING: (DamageType.COLD, "dragged under by rough water", 35),
        HazardKind.GORING: (DamageType.PIERCE, "gored by the herd", 25),
        HazardKind.BLOWOUT: (DamageType.FIRE, "caught in a blowout at the well", 45),
        HazardKind.EXPLOSION: (DamageType.EXPLOSIVE, "caught in an explosion", 50),
        HazardKind.TOXIC_RELEASE: (DamageType.CHEMICAL, "poisoned by a release of fumes", 35),
        HazardKind.DECOMPRESSION: (DamageType.BLUNT, "torn by a loss of pressure", 45),
        HazardKind.RADIATION_EXPOSURE: (DamageType.RADIATION, "burned by radiation", 40),
        HazardKind.SUBSIDENCE: (DamageType.BLUNT, "buried as the ground sank", 35),
        HazardKind.BEAST_ATTACK: (DamageType.PIERCE, "attacked by the beasts it tended", 30),
        HazardKind.SOURCE_BACKLASH: (DamageType.MAGIC, "struck by the backlash of the source", 35),
        HazardKind.MACHINE_ACCIDENT: (DamageType.CUT, "caught in the machinery", 35),
        HazardKind.FALLS: (DamageType.BLUNT, "fell from a height at work", 35),
        HazardKind.BURNS: (DamageType.FIRE, "burned at the furnace", 30),
        HazardKind.DUST_LUNG: (DamageType.ASPHYXIA, "choked by years of dust", 25),
    },
)


HAZARD_MAIMS: Mapping[HazardKind, MaimedKind] = total(
    HazardKind,
    {
        HazardKind.CAVE_IN: MaimedKind.ONE_LEGGED,
        HazardKind.FLOODED_SHAFT: MaimedKind.BROKEN_MINDED,
        HazardKind.FELLING_ACCIDENT: MaimedKind.ONE_ARMED,
        HazardKind.DROWNING: MaimedKind.SCARRED,
        HazardKind.GORING: MaimedKind.LAME,
        HazardKind.BLOWOUT: MaimedKind.SCARRED,
        HazardKind.EXPLOSION: MaimedKind.DEAF,
        HazardKind.TOXIC_RELEASE: MaimedKind.BLIND,
        HazardKind.DECOMPRESSION: MaimedKind.DEAF,
        HazardKind.RADIATION_EXPOSURE: MaimedKind.SCARRED,
        HazardKind.SUBSIDENCE: MaimedKind.ONE_LEGGED,
        HazardKind.BEAST_ATTACK: MaimedKind.LAME,
        HazardKind.SOURCE_BACKLASH: MaimedKind.BROKEN_MINDED,
        HazardKind.MACHINE_ACCIDENT: MaimedKind.ONE_ARMED,
        HazardKind.FALLS: MaimedKind.LAME,
        HazardKind.BURNS: MaimedKind.SCARRED,
        HazardKind.DUST_LUNG: MaimedKind.BROKEN_MINDED,
    },
)


KIND_JOBS = total(
    ExtractionKind,
    {
        ExtractionKind.MINING: Job.MINING,
        ExtractionKind.QUARRYING: Job.MINING,
        ExtractionKind.FISHING: Job.FISHING,
        ExtractionKind.HERDING: Job.HERDING,
        ExtractionKind.FARMING: Job.FARMING,
        ExtractionKind.GATHERING: Job.GATHERING,
        ExtractionKind.LOGGING: Job.BUILDING,
        ExtractionKind.DRILLING: Job.MINING,
        ExtractionKind.PUMPING: Job.MINING,
        ExtractionKind.DREDGING: Job.MINING,
        ExtractionKind.DEEP_SEA: Job.MINING,
        ExtractionKind.ATMOSPHERIC: Job.MINING,
        ExtractionKind.ASTEROID: Job.MINING,
        ExtractionKind.STELLAR: Job.CRAFTING,
        ExtractionKind.SOURCE_HARVEST: Job.SCHOLARSHIP,
        ExtractionKind.SALVAGE: Job.CRAFTING,
        ExtractionKind.LIVING_HARVEST: Job.HERDING,
        ExtractionKind.DISTILLATION: Job.CRAFTING,
        ExtractionKind.EVAPORATING: Job.GATHERING,
    },
)


HAZARD_RULES: Mapping[HazardKind, str] = total(
    HazardKind,
    {
        HazardKind.CAVE_IN: "cave_in_pct",
        HazardKind.FLOODED_SHAFT: "cave_in_pct",
        HazardKind.FELLING_ACCIDENT: "felling_pct",
        HazardKind.DROWNING: "drowning_pct",
        HazardKind.GORING: "goring_pct",
        HazardKind.BLOWOUT: "blowout_pct",
        HazardKind.EXPLOSION: "explosion_pct",
        HazardKind.TOXIC_RELEASE: "toxic_release_pct",
        HazardKind.DECOMPRESSION: "decompression_pct",
        HazardKind.RADIATION_EXPOSURE: "radiation_pct",
        HazardKind.SUBSIDENCE: "subsidence_pct",
        HazardKind.BEAST_ATTACK: "beast_attack_pct",
        HazardKind.SOURCE_BACKLASH: "source_backlash_pct",
        HazardKind.MACHINE_ACCIDENT: "machine_accident_pct",
        HazardKind.FALLS: "falls_pct",
        HazardKind.BURNS: "burns_pct",
        HazardKind.DUST_LUNG: "dust_lung_pct",
    },
)


DANGER_KEYS: MappingProxyType[TradeLoss, str] = MappingProxyType(
    {
        TradeLoss.BANDITS: "danger_bandits",
        TradeLoss.BEASTS: "danger_beasts",
        TradeLoss.WEATHER: "danger_weather",
        TradeLoss.SEA: "danger_sea",
        TradeLoss.OFFICIALS: "danger_officials",
        TradeLoss.SPOILAGE: "danger_spoilage",
        TradeLoss.PILFERAGE: "danger_pilferage",
        TradeLoss.PIRATES: "danger_pirates",
        TradeLoss.BREAKAGE: "danger_breakage",
    }
)


EFFECT_WEIGHT: Mapping[WeatherEffect, Callable[[Rules], int]] = total(
    WeatherEffect,
    {
        WeatherEffect.GROWTH: lambda rules: 0,
        WeatherEffect.MORALE: lambda rules: 0,
        WeatherEffect.FOOTING: lambda rules: rules.route_dangers.weather_footing_pct,
        WeatherEffect.COLD: lambda rules: rules.route_dangers.weather_cold_pct,
        WeatherEffect.HEAT: lambda rules: rules.route_dangers.weather_heat_pct,
        WeatherEffect.WET: lambda rules: rules.route_dangers.weather_wet_pct,
        WeatherEffect.WIND: lambda rules: rules.route_dangers.weather_wind_pct,
        WeatherEffect.VISIBILITY: lambda rules: rules.route_dangers.weather_visibility_pct,
        WeatherEffect.LIGHTNING: lambda rules: rules.route_dangers.weather_lightning_pct,
        WeatherEffect.FLOOD: lambda rules: rules.route_dangers.weather_flood_pct,
        WeatherEffect.BREATH: lambda rules: rules.route_dangers.weather_breath_pct,
    },
)

CRAFT_FACTOR_EXTRACTION_KINDS = (ExtractionKind.FARMING, ExtractionKind.HERDING)
ROLL_HAZARDS_HAZARD_KINDS = (HazardKind.CAVE_IN, HazardKind.FLOODED_SHAFT)
REFORM_MONEY_FORMS = (MoneyForm.COIN, MoneyForm.COMMODITY)
