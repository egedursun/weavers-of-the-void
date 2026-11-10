from pydantic import Field

from aerona.domain.enums.storyteller import StorytellerProfile
from aerona.domain.enums.world import CosmosSize, GenesisTemplate, LanguageTexture, TechnologyEra
from aerona.domain.models.base import ValueObject

PERCENT_CEILING = 100


class GenesisSettings(ValueObject):
    template: GenesisTemplate | None = None
    magic: int = Field(ge=0, le=PERCENT_CEILING)
    darkness: int = Field(ge=0, le=PERCENT_CEILING)
    technology: TechnologyEra = TechnologyEra.IRON
    language_texture: LanguageTexture = LanguageTexture.FREE
    peoples: int = Field(ge=1)
    cosmos_size: CosmosSize = CosmosSize.SINGLE
    storyteller: StorytellerProfile = StorytellerProfile.CYCLIC
    tone: str | None = None
    seed_idea: str | None = None
