from aerona.core.total import total
from aerona.domain.enums.environment import SeasonOnset, SeasonWarmth, SeasonWater

WARMTH_LABELS = total(
    SeasonWarmth,
    {
        SeasonWarmth.COLDEST: "Coldest",
        SeasonWarmth.COLD: "Cold",
        SeasonWarmth.COOLING: "Cooling",
        SeasonWarmth.EVEN: "Even",
        SeasonWarmth.WARMING: "Warming",
        SeasonWarmth.WARM: "Warm",
        SeasonWarmth.WARMEST: "Warmest",
    },
)
WATER_LABELS = total(
    SeasonWater,
    {
        SeasonWater.ARID: "Arid",
        SeasonWater.DRY: "Dry",
        SeasonWater.EVEN: "Even rain",
        SeasonWater.WET: "Wet",
        SeasonWater.DELUGE: "Deluge",
    },
)
ONSET_LABELS = total(
    SeasonOnset,
    {
        SeasonOnset.EARLY: "Came early",
        SeasonOnset.ON_TIME: "Came on time",
        SeasonOnset.LATE: "Came late",
        SeasonOnset.FAILED: "Failed",
    },
)
ONSET_SHIFT = total(SeasonOnset, {SeasonOnset.EARLY: 1, SeasonOnset.ON_TIME: 0, SeasonOnset.LATE: -1, SeasonOnset.FAILED: -2})
