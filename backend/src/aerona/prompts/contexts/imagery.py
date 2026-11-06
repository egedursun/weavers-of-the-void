from pydantic import Field

from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.travel import VehicleKind
from aerona.prompts.contexts.base import ContextItem, RulesContext
from aerona.prompts.data.images import AMBIENCE_BIOME_COUNT, COSMOS_DIRECTION, CosmosSubjectKind, ImageSubjectTraits, image_direction


class WorldAmbience(ContextItem):
    type_label: str
    biomes: list[str] = Field(default_factory=list)

    @property
    def leading_biomes(self) -> list[str]:
        return self.biomes[:AMBIENCE_BIOME_COUNT]


class ImageSubject(ContextItem):
    id: int
    entity_type: EntityType
    type_label: str
    subtype: str | None = None
    name: str
    description: str
    megafauna: bool = False
    vehicle: VehicleKind | None = None
    ambience: WorldAmbience | None = None

    @property
    def direction(self) -> str:
        return image_direction(ImageSubjectTraits(self.entity_type, self.megafauna, self.vehicle))


class EntityImagePromptsContext(RulesContext):
    world_name: str
    cosmology: str
    tone: str
    subjects: list[ImageSubject]


class CosmosSubject(ContextItem):
    number: int
    kind: CosmosSubjectKind
    type_label: str | None = None
    name: str
    title: str | None = None
    description: str
    ambience: WorldAmbience | None = None

    @property
    def direction(self) -> str:
        return COSMOS_DIRECTION[self.kind]


class CosmosImagePromptsContext(RulesContext):
    world_name: str
    cosmology: str
    tone: str
    subjects: list[CosmosSubject]
