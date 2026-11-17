from enum import StrEnum

from pydantic import BaseModel, Field

from aerona.api.schemas.common import ApiModel
from aerona.constants.api import CARD_PAGE_DEFAULT, CARD_PAGE_MAX
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.rarity import Rarity


class CardOrder(StrEnum):
    POWER = "power"
    NAME = "name"
    NEWEST = "newest"


class CharacterCardStat(ApiModel):
    key: str
    label: str
    value: int
    maximum: int | None


class CharacterCardAbility(ApiModel):
    name: str
    text: str


class CharacterCardNote(ApiModel):
    label: str
    text: str


class CharacterCard(ApiModel):
    node_id: int
    node_kind: NodeKind
    entity_type: EntityType | None
    name: str
    title: str | None
    subtype: str | None
    rarity: Rarity | None
    stars: int | None
    power_level: int | None
    level: int | None
    xp: int | None
    domains: list[Domain]
    world_id: int | None
    cover: str | None
    flavor: str
    headline: list[CharacterCardStat]
    stats: list[CharacterCardStat]
    abilities: list[CharacterCardAbility]
    notes: list[CharacterCardNote]
    fallen: bool
    born_epoch: int | None
    ended_epoch: int | None


class CharacterDeckCount(ApiModel):
    node_kind: NodeKind
    entity_type: EntityType | None
    total: int


class CharacterRarityCount(ApiModel):
    rarity: Rarity
    total: int


class CharacterCardPage(ApiModel):
    items: list[CharacterCard]
    total: int
    offset: int
    limit: int
    decks: list[CharacterDeckCount]
    rarities: list[CharacterRarityCount]


class CardQuery(BaseModel):
    q: str | None = Field(default=None, max_length=200)
    node_kind: NodeKind | None = None
    entity_type: EntityType | None = None
    rarity: Rarity | None = None
    world_id: int | None = Field(default=None, ge=1)
    fallen: bool | None = None
    order: CardOrder = CardOrder.POWER
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=CARD_PAGE_DEFAULT, ge=1, le=CARD_PAGE_MAX)
