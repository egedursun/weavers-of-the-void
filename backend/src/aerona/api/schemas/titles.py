from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.mind import LabelView
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.titles import TitleRank, TitleTenure


class TitleHolderView(ApiModel):
    holder: NodeRef | None
    tenure: TitleTenure
    tenure_label: str
    since_epoch: int
    until_epoch: int | None


class TitleDriftView(ApiModel):
    land: NodeRef | None
    epochs: int


class TitleSummary(ApiModel):
    title: NodeRef
    rank: TitleRank
    rank_label: str
    holder: NodeRef | None
    lands: int
    dormant: bool


class TitleDetail(ApiModel):
    rank: TitleRank
    rank_label: str
    liege: NodeRef | None
    holder: NodeRef | None
    polity: NodeRef | None
    capital: NodeRef | None
    succession_law: NodeRef | None
    emblem: str | None
    prestige: int
    regalia: list[NodeRef]
    drift: list[TitleDriftView]
    created_epoch: int
    destroyed_epoch: int | None
    lands: list[NodeRef]
    vassal_titles: list[TitleSummary]
    holders: list[TitleHolderView]
    held: list[str]


class TitleClaimView(ApiModel):
    title: NodeRef
    strength: int
    since_epoch: int


class TitlesView(ApiModel):
    node_id: int
    detail: TitleDetail | None
    titles_held: list[TitleSummary]
    claims: list[TitleClaimView]
    realm_titles: list[TitleSummary]
    seat_titles: list[TitleSummary]
    de_jure_chain: list[TitleSummary]
    ranks: list[LabelView]
