from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.mind import LabelView
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.faction import EstatePrivilege, FactionRank, MovementCause
from aerona.domain.enums.society import SocialClass


class EstateView(ApiModel):
    estate: NodeRef
    realm: NodeRef | None
    social_class: SocialClass
    class_label: str
    loyalty: int
    influence: int
    privileges: list[EstatePrivilege]
    privilege_since: dict[str, int]
    held: list[str]


class PoliticalSupportView(ApiModel):
    community: NodeRef
    share: int
    held: bool


class PoliticalMovementView(ApiModel):
    movement: NodeRef
    realm: NodeRef | None
    cause: MovementCause
    cause_label: str
    support: int
    is_party: bool
    founded_epoch: int
    communities: list[PoliticalSupportView]
    held: list[str]


class ShareView(ApiModel):
    holder: NodeRef
    share: int
    held: bool


class CompanyView(ApiModel):
    company: NodeRef
    realm: NodeRef | None
    route: NodeRef | None
    region: NodeRef | None
    commodity: CommodityKind | None
    dividend_pct: int
    value: int
    chartered_epoch: int
    shares: list[ShareView]
    held: list[str]


class HolyOrderView(ApiModel):
    order: NodeRef
    cult: NodeRef | None
    fortress: NodeRef | None
    tithe_share: int
    held: list[str]


class GuildMemberView(ApiModel):
    member: NodeRef
    rank: FactionRank
    rank_label: str


class GuildView(ApiModel):
    guild: NodeRef
    members: list[GuildMemberView]
    secrets: list[Technique]
    known: list[Technique]


class EstatesView(ApiModel):
    node_id: int
    estates: list[EstateView]
    movements: list[PoliticalMovementView]
    companies: list[CompanyView]
    orders: list[HolyOrderView]
    guilds: list[GuildView]
    holdings: list[ShareView]
    guild_rank: str | None
    classes: list[LabelView]
    privileges: list[LabelView]
    causes: list[LabelView]
    can_found: bool
    reason: str | None
