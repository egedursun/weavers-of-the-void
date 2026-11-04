from enum import StrEnum
from typing import Annotated

from pydantic import Field

from aerona.constants.tool_inputs import (
    COUNT_MIN,
    DESCRIPTION_MAX,
    DESCRIPTION_MIN,
    IMAGE_PROMPT_MAX,
    MESSAGE_MAX,
    MESSAGE_MIN,
    NAME_MAX,
    NAME_MIN,
    REASON_MAX,
    REASON_MIN,
    SAYING_MAX,
    SAYING_MIN,
    SUBTYPE_MAX,
)
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import LegendCategory
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import KnowledgeBranch, ResourceMechanic
from aerona.domain.enums.travel import JourneyIntent
from aerona.tools.framework.inputs import ToolInput

Name = Annotated[str, Field(min_length=NAME_MIN, max_length=NAME_MAX)]
Subtype = Annotated[str, Field(max_length=SUBTYPE_MAX)]
Description = Annotated[str, Field(min_length=DESCRIPTION_MIN, max_length=DESCRIPTION_MAX)]
Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
Short = Annotated[str, Field(min_length=MESSAGE_MIN, max_length=REASON_MAX)]
ImagePrompt = Annotated[str, Field(max_length=IMAGE_PROMPT_MAX)]


class ItemCategory(StrEnum):
    WEAPON = "weapon"
    ARMOUR = "armour"
    SHIELD = "shield"
    TOOL = "tool"
    JEWELLERY = "jewellery"
    SACRED_RELIC = "sacred_relic"
    INSTRUMENT = "instrument"
    BOOK = "book"


class CultureKind(StrEnum):
    TRADITION = "tradition"
    LEGEND = "legend"
    ARTWORK = "artwork"
    LAW = "law"


class DiplomacyKind(StrEnum):
    ALLIANCE = "alliance"
    PEACE = "peace"
    TRIBUTE = "tribute"
    MARRIAGE = "marriage"


class LandKind(StrEnum):
    REGION = "region"
    PLACE = "place"


class RiteKind(StrEnum):
    PRAYER = "prayer"
    WEALTH = "wealth"
    BLOOD = "blood"
    LIFE = "life"


class SabotageKind(StrEnum):
    POISON = "poison"
    ARSON = "arson"
    DISCORD = "discord"


class ProduceInput(ToolInput):
    name: Name
    category: ItemCategory
    subtype: Subtype | None = None
    description: Description
    resource_ids: Annotated[list[int], Field(min_length=1)]
    material: MaterialKind | None = None
    owner_id: int | None = None
    image_prompt: ImagePrompt | None = None


class BuildInput(ToolInput):
    name: Name
    subtype: Subtype | None = None
    description: Description
    location_id: int | None = None
    dedicated_son_id: int | None = None
    material: MaterialKind | None = None
    channels_ley: bool = False
    image_prompt: ImagePrompt | None = None


class CultureInput(ToolInput):
    kind: CultureKind
    name: Name
    subtype: Subtype | None = None
    description: Description
    related_ids: list[int] | None = None
    image_prompt: ImagePrompt | None = None
    legend_category: LegendCategory | None = None


class DiscoverInput(ToolInput):
    name: Name
    subtype: Subtype | None = None
    description: Description
    location_id: int
    domain: str | None = None
    image_prompt: ImagePrompt | None = None
    commodity: CommodityKind | None = None
    material: MaterialKind | None = None
    mechanics: list[ResourceMechanic] | None = None


class ClaimInput(ToolInput):
    resource_id: int


class SettleInput(ToolInput):
    name: Name
    subtype: Subtype | None = None
    description: Description
    location_id: int
    image_prompt: ImagePrompt | None = None


class TradeInput(ToolInput):
    target_id: int
    goods: Short


class DeclareWarInput(ToolInput):
    target_id: int
    reason: Reason


class WorshipInput(ToolInput):
    son_id: int
    offering: Reason


class PrayerInput(ToolInput):
    prayer: Annotated[str, Field(min_length=REASON_MIN, max_length=MESSAGE_MAX)]
    request: Annotated[str, Field(max_length=REASON_MAX)] | None = None


class DevelopKnowledgeInput(ToolInput):
    name: Name
    branch: KnowledgeBranch
    description: Description
    base_ids: list[int] | None = None
    resource_id: int | None = None
    image_prompt: ImagePrompt | None = None


class LearnInput(ToolInput):
    knowledge_id: int
    from_id: int


class DiplomacyInput(ToolInput):
    target_id: int
    kind: DiplomacyKind
    terms: Reason


class AdventureInput(ToolInput):
    target_id: int
    goal: Reason


class FindRouteInput(ToolInput):
    how: Reason


class ExploreInput(ToolInput):
    kind: LandKind
    name: Name
    subtype: Subtype | None = None
    description: Description
    location_id: int | None = None
    settle: bool = False
    image_prompt: ImagePrompt | None = None


class RiteInput(ToolInput):
    son_id: int
    kind: RiteKind
    victim_id: int | None = None


class ShipInput(ToolInput):
    name: Name
    subtype: Subtype | None = None
    description: Description
    image_prompt: ImagePrompt | None = None


class ExpeditionInput(ToolInput):
    route_id: int
    intent: JourneyIntent
    percent: Annotated[int, Field(ge=COUNT_MIN)] | None = None
    vessel_id: int | None = None


class TameInput(ToolInput):
    species_id: int
    how: Reason


class ChimeraInput(ToolInput):
    a_id: int
    b_id: int
    name: Name
    goal: Reason


class BindSpiritInput(ToolInput):
    spirit_id: int
    target_id: int


class RuinsInput(ToolInput):
    target_id: int
    how: Reason


class SabotageInput(ToolInput):
    target_id: int
    kind: SabotageKind
    how: Reason


class PreachInput(ToolInput):
    target_id: int
    sermon: Annotated[str, Field(min_length=SAYING_MIN, max_length=REASON_MAX)]


class DefyInput(ToolInput):
    son_id: int
    reason: Reason


class DenyInput(ToolInput):
    reason: Reason


class ProphesyInput(ToolInput):
    name: Name
    saying: Annotated[str, Field(min_length=SAYING_MIN, max_length=SAYING_MAX)]
    related_ids: list[int] | None = None


class EscapeInput(ToolInput):
    how: Reason


class RansomInput(ToolInput):
    captive_id: int


class RescueInput(ToolInput):
    captive_id: int
    plan: Reason


class ArmyInput(ToolInput):
    name: Name
    percent: Annotated[int, Field(ge=COUNT_MIN)] | None = None


class CommanderInput(ToolInput):
    mortal_id: int


class SpyInput(ToolInput):
    target_id: int
    cover: Reason


class BarterInput(ToolInput):
    target_id: int
    give_ids: Annotated[list[int], Field(min_length=1)]
    take_ids: list[int] | None = None
    terms: Short


class LendInput(ToolInput):
    debtor_id: int
    amount: Annotated[int, Field(ge=COUNT_MIN)]
    what: Annotated[str, Field(min_length=NAME_MIN, max_length=NAME_MAX)]
    term_ages: Annotated[int, Field(ge=COUNT_MIN)] | None = None


class RepayInput(ToolInput):
    creditor_id: int


class AdoptInput(ToolInput):
    child_id: int
    reason: Reason
