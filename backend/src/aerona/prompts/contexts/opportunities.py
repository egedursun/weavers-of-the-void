from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field

from aerona.prompts.contexts.base import ContextItem, RulesContext
from aerona.prompts.contexts.common import NamedRecord, SonBrief


class ValuedRecord(ContextItem):
    id: int
    name: str
    value: int


class PatronedRecord(ContextItem):
    id: int
    name: str
    patron: str


class RecordPair(ContextItem):
    a: NamedRecord
    b: NamedRecord


class BranchRecord(ContextItem):
    id: int
    name: str
    branch_label: str | None = None


class TargetMortal(ContextItem):
    id: int
    name: str
    patron: str
    cost: int
    chance: int


class ProphecyRecord(ContextItem):
    id: int
    name: str
    age: int
    own: bool = False


class StaleThread(ContextItem):
    id: int
    text: str


class OpportunityLine(ContextItem):
    @property
    def tension(self) -> bool:
        return False

    @property
    def first(self) -> bool:
        return False


class BreatheLife(OpportunityLine):
    kind: Literal["breathe_life"] = "breathe_life"
    lifeless: bool
    peoples: int
    settlements: int
    mortals: int
    species: int
    organizations: int
    empty_regions: list[NamedRecord] = Field(default_factory=list)
    few_mortals: bool = False


class NewEmptyWorld(OpportunityLine):
    kind: Literal["new_empty_world"] = "new_empty_world"
    world_id: int
    world_name: str
    world_type_label: str
    empty_ages: int | None = None
    regions: list[ValuedRecord] = Field(default_factory=list)


class NarrowLands(OpportunityLine):
    kind: Literal["narrow_lands"] = "narrow_lands"
    world_name: str | None = None
    regions: int
    communities: int
    per_region: float
    crowded: list[ValuedRecord] = Field(default_factory=list)


class IsolatedWorld(OpportunityLine):
    kind: Literal["isolated_world"] = "isolated_world"
    hidden_route: bool = False


class StagnantCosmos(OpportunityLine):
    kind: Literal["stagnant_cosmos"] = "stagnant_cosmos"
    last_birth_age: int


class DeadSibling(OpportunityLine):
    kind: Literal["dead_sibling"] = "dead_sibling"
    name: str
    death_age: int
    devotion: int
    remaining: int | None = None
    enemy: bool = False
    corpse_id: int | None = None
    cult: ValuedRecord | None = None

    @property
    def tension(self) -> bool:
        return self.enemy


class RivalSiblings(OpportunityLine):
    kind: Literal["rival_siblings"] = "rival_siblings"
    rivals: list[ValuedRecord]

    @property
    def tension(self) -> bool:
        return True


class RivalMortals(OpportunityLine):
    kind: Literal["rival_mortals"] = "rival_mortals"
    mortals: list[TargetMortal]

    @property
    def tension(self) -> bool:
        return True


class Unclaimed(OpportunityLine):
    kind: Literal["unclaimed"] = "unclaimed"
    communities: list[NamedRecord]


class RivalWorshippers(OpportunityLine):
    kind: Literal["rival_worshippers"] = "rival_worshippers"
    communities: list[PatronedRecord]

    @property
    def tension(self) -> bool:
        return True


class OwnWorshippers(OpportunityLine):
    kind: Literal["own_worshippers"] = "own_worshippers"
    communities: list[NamedRecord]


class Hostilities(OpportunityLine):
    kind: Literal["hostilities"] = "hostilities"
    pairs: list[RecordPair]

    @property
    def tension(self) -> bool:
        return True


class TeachableKnowledge(OpportunityLine):
    kind: Literal["teachable_knowledge"] = "teachable_knowledge"
    knowledge: list[BranchRecord] = Field(default_factory=list)


class SuggestionReason(StrEnum):
    RIVAL_CREATION = "rival_creation"
    RIVAL_SETTLEMENT = "rival_settlement"
    RIVAL_WORSHIPPER = "rival_worshipper"
    OWN_AND_NEIGHBOUR = "own_and_neighbour"
    POOR_WORSHIPPER = "poor_worshipper"
    REBELLED_AGAINST_YOU = "rebelled_against_you"
    HOSTILE_PAIR = "hostile_pair"
    RICH_ESSENCE = "rich_essence"
    FEW_CELESTIALS = "few_celestials"
    FEW_LAWS = "few_laws"
    NO_ROAD = "no_road"
    NO_FACTION = "no_faction"
    UNCLAIMED = "unclaimed"
    OWN_MORTAL = "own_mortal"
    HUNGRY = "hungry"
    GODLESS = "godless"
    BEST_STAT = "best_stat"
    SPEAK = "speak"
    TENSE_NEIGHBOUR = "tense_neighbour"
    POORER_NEIGHBOUR = "poorer_neighbour"
    SHIPLESS = "shipless"
    OPEN_ROUTE = "open_route"
    OTHER_FAITH = "other_faith"
    ENEMY = "enemy"


class ToolSuggestion(ContextItem):
    tool: str
    reason: SuggestionReason
    target: NamedRecord | None = None
    second: NamedRecord | None = None
    value: int | None = None
    label: str | None = None


class RivalOptions(OpportunityLine):
    kind: Literal["rival_options"] = "rival_options"
    rival: NamedRecord
    options: list[ToolSuggestion]

    @property
    def tension(self) -> bool:
        return True


class UntriedTools(OpportunityLine):
    kind: Literal["untried_tools"] = "untried_tools"
    suggestions: list[ToolSuggestion]


class OverusedTool(OpportunityLine):
    kind: Literal["overused_tool"] = "overused_tool"
    tool: str
    uses: int
    epochs: int


class Covenants(OpportunityLine):
    kind: Literal["covenants"] = "covenants"
    sons: list[NamedRecord]


class StalePlan(OpportunityLine):
    kind: Literal["stale_plan"] = "stale_plan"
    thread_ids: list[int]


class GodlessCreeds(OpportunityLine):
    kind: Literal["godless_creeds"] = "godless_creeds"
    creeds: list[NamedRecord]
    strongest: int


class KnowledgePairs(OpportunityLine):
    kind: Literal["knowledge_pairs"] = "knowledge_pairs"
    pairs: list[RecordPair]


class LeveledRecord(ContextItem):
    id: int
    name: str
    level: int


class UnknownBranches(OpportunityLine):
    kind: Literal["unknown_branches"] = "unknown_branches"
    branches: list[str]


class DeepenableKnowledge(OpportunityLine):
    kind: Literal["deepenable_knowledge"] = "deepenable_knowledge"
    knowledge: list[LeveledRecord]


class Languageless(OpportunityLine):
    kind: Literal["languageless"] = "languageless"
    communities: list[NamedRecord] = Field(default_factory=list)


class UnownedResources(OpportunityLine):
    kind: Literal["unowned_resources"] = "unowned_resources"
    resources: list[NamedRecord]


class RivalCreations(OpportunityLine):
    kind: Literal["rival_creations"] = "rival_creations"
    creations: list[NamedRecord]

    @property
    def tension(self) -> bool:
        return True


class RebelsAgainstYou(OpportunityLine):
    kind: Literal["rebels_against_you"] = "rebels_against_you"
    records: list[NamedRecord]

    @property
    def tension(self) -> bool:
        return True


class YourEnemies(OpportunityLine):
    kind: Literal["your_enemies"] = "your_enemies"
    records: list[NamedRecord]

    @property
    def tension(self) -> bool:
        return True


class Godless(OpportunityLine):
    kind: Literal["godless"] = "godless"
    communities: list[NamedRecord]


class RebelSiblings(OpportunityLine):
    kind: Literal["rebel_siblings"] = "rebel_siblings"
    siblings: list[NamedRecord]

    @property
    def tension(self) -> bool:
        return True


class LowLoyalty(OpportunityLine):
    kind: Literal["low_loyalty"] = "low_loyalty"

    @property
    def tension(self) -> bool:
        return True


class Existence(OpportunityLine):
    kind: Literal["existence"] = "existence"
    fading: bool
    value: int


class WorshipperWars(OpportunityLine):
    kind: Literal["worshipper_wars"] = "worshipper_wars"
    wars: list[NamedRecord]

    @property
    def tension(self) -> bool:
        return True


class HungryWorshippers(OpportunityLine):
    kind: Literal["hungry_worshippers"] = "hungry_worshippers"
    communities: list[NamedRecord]


class Wonders(OpportunityLine):
    kind: Literal["wonders"] = "wonders"
    wonders: list[NamedRecord]


class StaleThreads(OpportunityLine):
    kind: Literal["stale_threads"] = "stale_threads"
    threads: list[StaleThread]

    @property
    def first(self) -> bool:
        return True


class LongThreads(OpportunityLine):
    kind: Literal["long_threads"] = "long_threads"
    thread_ids: list[int]


class PendingProphecies(OpportunityLine):
    kind: Literal["pending_prophecies"] = "pending_prophecies"
    prophecies: list[ProphecyRecord]


class OpenThreads(OpportunityLine):
    kind: Literal["open_threads"] = "open_threads"
    thread_ids: list[int]


class Silence(OpportunityLine):
    kind: Literal["silence"] = "silence"
    never_spoken: bool
    ages: int = 0


SonOpportunity = Annotated[
    BreatheLife
    | NewEmptyWorld
    | NarrowLands
    | IsolatedWorld
    | StagnantCosmos
    | DeadSibling
    | RivalSiblings
    | RivalMortals
    | Unclaimed
    | RivalWorshippers
    | OwnWorshippers
    | Hostilities
    | TeachableKnowledge
    | UnknownBranches
    | DeepenableKnowledge
    | KnowledgePairs
    | GodlessCreeds
    | RivalOptions
    | UntriedTools
    | OverusedTool
    | Covenants
    | StalePlan
    | Languageless
    | UnownedResources
    | RivalCreations
    | RebelsAgainstYou
    | YourEnemies
    | Godless
    | RebelSiblings
    | LowLoyalty
    | Existence
    | WorshipperWars
    | HungryWorshippers
    | Wonders
    | StaleThreads
    | LongThreads
    | PendingProphecies
    | OpenThreads
    | Silence,
    Field(discriminator="kind"),
]


def ordered_lines[L: OpportunityLine](lines: list[L], tension_first: bool) -> list[L]:
    leading = [line for line in lines if line.first]
    rest = [line for line in lines if not line.first]
    ordered = leading + rest
    if not tension_first:
        return ordered
    return [line for line in ordered if line.tension] + [line for line in ordered if not line.tension]


class SonOpportunitiesContext(RulesContext):
    lines: list[SonOpportunity]
    available_tools: list[str] | None = None

    @property
    def ordered(self) -> list[OpportunityLine]:
        return ordered_lines(list(self.lines), self.rules.opportunities.tension_first > 0)

    def template_variables(self) -> dict[str, object]:
        return {**super().template_variables(), "ordered": self.ordered}


class TradePartners(OpportunityLine):
    kind: Literal["trade_partners"] = "trade_partners"
    communities: list[NamedRecord]


class Enemies(OpportunityLine):
    kind: Literal["enemies"] = "enemies"
    enemies: list[NamedRecord]
    can_declare_war: bool = True
    can_sabotage: bool = False

    @property
    def tension(self) -> bool:
        return True


class TenseNeighbours(OpportunityLine):
    kind: Literal["tense_neighbours"] = "tense_neighbours"
    neighbours: list[ValuedRecord]
    can_sabotage: bool = False

    @property
    def tension(self) -> bool:
        return True


class LearnableKnowledge(OpportunityLine):
    kind: Literal["learnable_knowledge"] = "learnable_knowledge"
    knowledge: list[PatronedRecord]


class LandResources(OpportunityLine):
    kind: Literal["land_resources"] = "land_resources"
    resources: list[NamedRecord]


class DangerousCreatures(OpportunityLine):
    kind: Literal["dangerous_creatures"] = "dangerous_creatures"
    species: list[NamedRecord]


class NoKnowledge(OpportunityLine):
    kind: Literal["no_knowledge"] = "no_knowledge"


class NoLanguage(OpportunityLine):
    kind: Literal["no_language"] = "no_language"


class BloodFeuds(OpportunityLine):
    kind: Literal["blood_feuds"] = "blood_feuds"
    communities: list[NamedRecord]

    @property
    def tension(self) -> bool:
        return True


class LovingNeighbours(OpportunityLine):
    kind: Literal["loving_neighbours"] = "loving_neighbours"
    neighbours: list[ValuedRecord]


class AtWar(OpportunityLine):
    kind: Literal["at_war"] = "at_war"
    wars: list[NamedRecord]

    @property
    def tension(self) -> bool:
        return True


class GranaryEmptying(OpportunityLine):
    kind: Literal["granary"] = "granary"
    food: int
    bread_price: int


class Discontent(OpportunityLine):
    kind: Literal["discontent"] = "discontent"
    class_label: str
    satisfaction: int


class Remains(OpportunityLine):
    kind: Literal["remains"] = "remains"
    remains: list[NamedRecord]


class DeadGod(OpportunityLine):
    kind: Literal["dead_god"] = "dead_god"
    name: str
    death_age: int
    devotion: int
    corpse: str | None = None


class ExplorationReasonKind(ContextItem):
    kind: Literal["narrow_lands", "hunger", "poverty", "explorer", "explorer_spirited", "road_knowledge"]
    explorer_name: str | None = None


class UnknownLands(OpportunityLine):
    kind: Literal["unknown_lands"] = "unknown_lands"
    reasons: list[ExplorationReasonKind] = Field(default_factory=list)
    can_settle: bool = False


class SkyOpen(OpportunityLine):
    kind: Literal["sky_open"] = "sky_open"
    roadless_worlds: list[str] = Field(default_factory=list)


class SkyUnknown(OpportunityLine):
    kind: Literal["sky_unknown"] = "sky_unknown"
    worlds: list[str]


class OpenRoute(OpportunityLine):
    kind: Literal["open_route"] = "open_route"


class DefyGod(OpportunityLine):
    kind: Literal["defy_god"] = "defy_god"
    sons: list[NamedRecord]

    @property
    def tension(self) -> bool:
        return True


class BurdensomeGod(OpportunityLine):
    kind: Literal["burdensome_god"] = "burdensome_god"
    name: str


class NoGod(OpportunityLine):
    kind: Literal["no_god"] = "no_god"
    candidates: list[SonBrief]


MortalOpportunity = Annotated[
    TradePartners
    | Enemies
    | TenseNeighbours
    | LearnableKnowledge
    | LandResources
    | DangerousCreatures
    | NoKnowledge
    | UnknownBranches
    | UntriedTools
    | OverusedTool
    | NoLanguage
    | BloodFeuds
    | LovingNeighbours
    | AtWar
    | GranaryEmptying
    | Discontent
    | Remains
    | DeadGod
    | UnknownLands
    | SkyOpen
    | SkyUnknown
    | OpenRoute
    | DefyGod
    | BurdensomeGod
    | NoGod,
    Field(discriminator="kind"),
]


class MortalOpportunitiesContext(RulesContext):
    lines: list[MortalOpportunity]
    available_tools: list[str] | None = None

    @property
    def ordered(self) -> list[OpportunityLine]:
        return ordered_lines(list(self.lines), self.rules.opportunities.tension_first > 0)

    def template_variables(self) -> dict[str, object]:
        return {**super().template_variables(), "ordered": self.ordered}


class FadingSon(ContextItem):
    name: str
    existence: int


class CreatorHintKind(StrEnum):
    UNANSWERED_PRAYERS = "unanswered_prayers"
    UNCLAIMED = "unclaimed"
    REBEL_SONS = "rebel_sons"
    FADING_SONS = "fading_sons"
    DOOM = "doom"
    GODLESS_WORLDS = "godless_worlds"
    STALE_THREADS = "stale_threads"
    RICH_ESSENCE = "rich_essence"


class CreatorOpportunitiesContext(RulesContext):
    only: CreatorHintKind | None = None
    unanswered_prayers: int = 0
    unclaimed_count: int = 0
    unclaimed_examples: list[str] = Field(default_factory=list)
    rebel_sons: list[str] = Field(default_factory=list)
    fading_sons: list[FadingSon] = Field(default_factory=list)
    doom: int = 0
    doom_threshold: int
    godless_worlds: list[str] = Field(default_factory=list)
    stale_threads: int = 0
    essence: int = 0
