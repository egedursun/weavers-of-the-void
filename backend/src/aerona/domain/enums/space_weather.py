from enum import StrEnum


class SpaceWeatherKind(StrEnum):
    FLARE = "flare"
    PARTICLE_STORM = "particle_storm"
    FIELD_STORM = "field_storm"
    FIELD_REVERSAL = "field_reversal"
    COSMIC_RAY_BURST = "cosmic_ray_burst"
    WIND_SURGE = "wind_surge"
    METEOR_SHOWER = "meteor_shower"
    STELLAR_DIMMING = "stellar_dimming"
