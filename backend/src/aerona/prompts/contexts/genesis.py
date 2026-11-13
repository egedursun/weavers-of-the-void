from pydantic import Field

from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.world import CosmosSize, LanguageTexture, TechnologyEra
from aerona.prompts.contexts.base import ContextItem, LoreContext, LoreRulesContext, RulesContext
from aerona.prompts.contexts.common import SonBrief, WorldItem


class GenesisContext(LoreRulesContext):
    god_name: str
    seed: str
    tone: str | None = None
    wizard_text: str | None = None
    first_son_rarities: list[str] = Field(default_factory=list)
    layered: bool = False


class GenesisWizardContext(RulesContext):
    for_genesis: bool = True
    template_name: str | None = None
    magic: int
    danger: int
    technology: TechnologyEra
    language: LanguageTexture
    cosmos: CosmosSize
    shape_line: str | None = None
    layer_label: str | None = None
    world_type_label: str | None = None
    world_type_key: str | None = None
    sea: int | None = None
    mountains: int | None = None
    moisture: int | None = None
    climate_label: str | None = None
    age_label: str | None = None


class SonPowersContext(LoreContext):
    world_name: str
    world_header: str
    name: str
    title: str
    rarity_label: str
    domain_1: str
    domain_2: str
    appearance: str
    temperament: str
    obsession: str
    secret: str


class CreatorPortraitContext(LoreContext):
    world_name: str
    world_header: str
    god_name: str
    sons: list[SonBrief] = Field(default_factory=list)


class SummonSonContext(LoreContext):
    world_name: str
    world_header: str
    target_world_line: str | None = None
    god_name: str
    pantheon: list[SonBrief] = Field(default_factory=list)
    threads: str = ""
    recent_events: str = ""
    parent: SonBrief | None = None
    co_parent: SonBrief | None = None
    inspiration: str | None = None
    rarity: Rarity
    rarity_label: str


class AwakenPeoplesContext(LoreRulesContext):
    world_name: str
    world_summary: str
    map: str
    count: int
    earlier: list[str] = Field(default_factory=list)
    creation_text: str | None = None


class RevelationType(ContextItem):
    type_label: str
    stats: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)


class RevelationContext(LoreContext):
    god_name: str
    world_name: str
    target_world: WorldItem | None = None
    target_world_line: str | None = None
    world_summary: str
    entity_types: list[RevelationType]
    first_star: bool = False
    revelation_text: str = ""
