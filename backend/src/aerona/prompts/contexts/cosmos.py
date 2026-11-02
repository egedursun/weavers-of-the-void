from enum import StrEnum

from pydantic import Field

from aerona.prompts.contexts.base import ContextItem, LoreRulesContext, PromptContext, RulesContext
from aerona.prompts.contexts.common import SonBrief, WorldItem


class StarLine(ContextItem):
    id: int
    name: str
    type_label: str
    description: str | None = None
    planets: list[WorldItem] = Field(default_factory=list)


class ForeignGodBrief(ContextItem):
    name: str
    title: str | None = None
    world_id: int
    domains: str | None = None


class PlacementKind(StrEnum):
    EXISTING_STAR = "existing_star"
    MOON = "moon"
    NEW_STAR = "new_star"
    FREE = "free"


class NewWorldContext(LoreRulesContext):
    cosmos_name: str
    world_header: str
    cosmos_lines: str = ""
    main_world: WorldItem
    stars: list[StarLine] = Field(default_factory=list)
    foreign_gods: list[ForeignGodBrief] = Field(default_factory=list)
    placement: PlacementKind = PlacementKind.FREE
    star_id: int | None = None
    parent_world_id: int | None = None
    creator_son: SonBrief | None = None
    god_name: str
    world_type_label: str | None = None
    world_type_key: str | None = None
    inspiration: str | None = None
    banned_names: list[str] = Field(default_factory=list)
    cosmic_resource: str | None = None


class InspirationKind(StrEnum):
    MORTAL_INTUITION = "mortal_intuition"
    GENESIS_EXTRA_WORLD = "genesis_extra_world"


class WorldInspirationContext(PromptContext):
    kind: InspirationKind
    mortal_name: str = ""
    method: str = ""
    world_number: int = 0


class GraphNodeKind(StrEnum):
    SON = "son"
    ENTITY = "entity"


GRAPH_KEY_PREFIX: dict[GraphNodeKind, str] = {GraphNodeKind.SON: "s", GraphNodeKind.ENTITY: "e"}


class GraphNode(ContextItem):
    kind: GraphNodeKind
    id: int
    name: str
    title: str | None = None
    type_label: str | None = None
    subtype: str | None = None
    status_label: str | None = None
    description: str = ""

    @property
    def key(self) -> str:
        return f"{GRAPH_KEY_PREFIX[self.kind]}{self.id}"


class BondNodeLineContext(RulesContext):
    node: GraphNode


class CandidateReason(StrEnum):
    MENTIONED_TOGETHER = "mentioned_together"
    LOCATION = "location"
    MAKER = "maker"
    CREATOR = "creator"
    SAME_PLACE = "same_place"
    NOTABLE_OF_WORLD = "notable_of_world"


class BondCandidate(ContextItem):
    node: GraphNode
    reason: CandidateReason
    mentions: int = 0


class SuggestRecord(ContextItem):
    node: GraphNode
    candidates: list[BondCandidate]


class BondSuggestContext(LoreRulesContext):
    world_name: str
    bond_types: list[str]
    records: list[SuggestRecord]


class RelatedBond(ContextItem):
    source: GraphNode
    target: GraphNode
    reason: str | None = None


class BondNameRelatedContext(LoreRulesContext):
    world_name: str
    bond_types: list[str]
    bonds: list[RelatedBond]
