from pydantic import BaseModel, ConfigDict

from aerona.cartography.world_types import world_type_profile
from aerona.constants.cartography import (
    BACKGROUND_COLOUR_DARKEN,
    COASTAL_WATER_COLOUR_DARKEN,
    COASTLINE_COLOUR,
    COLOUR_CHANNEL_MAX,
    FOG_COLOUR,
    HEX_BASE,
    HEX_COLOUR_DIGITS,
    LAND_COLOUR_DARKEN,
    LAND_LABEL_COLOUR,
    UNKNOWN_LAND_COLOUR,
    UNKNOWN_WATER_COLOUR,
    WATER_COLOUR_DARKEN,
    WATER_LABEL_COLOUR,
)
from aerona.domain.enums.world import WorldType

WATER_BIOME_COUNT = 2


class WorldPalette(BaseModel):
    model_config = ConfigDict(frozen=True)

    world_type: WorldType
    biome_names: list[str]
    biome_colours: list[str]
    terrain_colours: list[str]
    coastal_water: str
    background: str
    unknown_land: str
    unknown_water: str
    fog: str
    coastline: str
    land_label: str
    water_label: str


def _channels(colour: str) -> tuple[int, int, int]:
    digits = colour.lstrip("#")[:HEX_COLOUR_DIGITS]
    return int(digits[0:2], HEX_BASE), int(digits[2:4], HEX_BASE), int(digits[4:6], HEX_BASE)


def darken(colour: str, amount: float) -> str:
    keep = max(0.0, min(1.0, 1.0 - amount))
    red, green, blue = (max(0, min(COLOUR_CHANNEL_MAX, round(channel * keep))) for channel in _channels(colour))
    return f"#{red:02x}{green:02x}{blue:02x}"


def palette_for(world_type: WorldType) -> WorldPalette:
    profile = world_type_profile(world_type)
    colours = list(profile.palette)
    terrain = [darken(colour, WATER_COLOUR_DARKEN if index < WATER_BIOME_COUNT else LAND_COLOUR_DARKEN) for index, colour in enumerate(colours)]
    return WorldPalette(
        world_type=world_type,
        biome_names=list(profile.biomes),
        biome_colours=colours,
        terrain_colours=terrain,
        coastal_water=darken(colours[0], COASTAL_WATER_COLOUR_DARKEN),
        background=darken(colours[1], BACKGROUND_COLOUR_DARKEN),
        unknown_land=UNKNOWN_LAND_COLOUR,
        unknown_water=UNKNOWN_WATER_COLOUR,
        fog=FOG_COLOUR,
        coastline=COASTLINE_COLOUR,
        land_label=LAND_LABEL_COLOUR,
        water_label=WATER_LABEL_COLOUR,
    )
