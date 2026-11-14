from typing import Any

from pydantic import Field, model_validator

from aerona.domain.enums.ages import AgeCycle
from aerona.domain.enums.cosmography import DimensionKind, WorldAge
from aerona.domain.enums.storyteller import StorytellerProfile
from aerona.domain.enums.world import ClimateEra, CosmosShape, CosmosSize, GenesisTemplate, LanguageTexture, TechnologyEra, WorldType
from aerona.domain.models.base import ValueObject

PERCENT_CEILING = 100
MOISTURE_FLOOR = -100
LEGACY_DANGER_KEY = "darkness"
DANGER_KEY = "danger"


class GenesisSettings(ValueObject):
    template: GenesisTemplate | None = None
    magic: int = Field(ge=0, le=PERCENT_CEILING)
    danger: int = Field(ge=0, le=PERCENT_CEILING)
    technology: TechnologyEra = TechnologyEra.IRON
    language_texture: LanguageTexture = LanguageTexture.FREE
    peoples: int = Field(ge=1)
    cosmos_size: CosmosSize = CosmosSize.SINGLE
    cosmos_shape: CosmosShape = CosmosShape.ONE_SUN
    layer_kind: DimensionKind | None = None
    storyteller: StorytellerProfile = StorytellerProfile.CYCLIC
    age_cycle: AgeCycle = AgeCycle.LINEAR
    world_type: WorldType | None = None
    sea_pct: int | None = Field(default=None, ge=0, le=PERCENT_CEILING)
    mountains_pct: int | None = Field(default=None, ge=0, le=PERCENT_CEILING)
    moisture_pct: int | None = Field(default=None, ge=MOISTURE_FLOOR, le=PERCENT_CEILING)
    climate_era: ClimateEra | None = None
    world_age: WorldAge | None = None
    tone: str | None = None
    seed_idea: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _stored_danger(cls, data: Any) -> Any:
        if not isinstance(data, dict) or LEGACY_DANGER_KEY not in data:
            return data
        kept = {key: value for key, value in data.items() if key != LEGACY_DANGER_KEY}
        return kept if DANGER_KEY in kept else {**kept, DANGER_KEY: data[LEGACY_DANGER_KEY]}


class GenesisOutcome(ValueObject):
    world_id: int
    layer_galaxy_id: int | None = None
