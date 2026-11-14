from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.belonging import FugitiveKind, IdentityLayer, PlayKind, SalienceDriver, SanctuaryKind, SanctuaryState, SatireSource
from aerona.domain.enums.society import SocialClass


class HeldIdentityView(ApiModel):
    layer: IdentityLayer
    value: NodeRef | None
    value_label: str | None
    strength: int
    salience: int
    driver: SalienceDriver
    updated_epoch: int
    locked: list[str]


class PeerMemberView(ApiModel):
    mortal: NodeRef
    joined_epoch: int
    deprived_epochs: int
    locked: list[str]


class PeerGroupView(ApiModel):
    id: int
    settlement: NodeRef
    social_class: SocialClass
    play: PlayKind
    children: int
    cohesion: int
    deprived: bool
    formed_epoch: int
    dissolved_epoch: int | None
    members: list[PeerMemberView]
    locked: list[str]


class SanctuaryView(ApiModel):
    id: int
    fugitive: NodeRef
    host: NodeRef
    kind: SanctuaryKind
    fugitive_kind: FugitiveKind
    pursuer: NodeRef | None
    state: SanctuaryState
    fee: int
    granted_epoch: int
    siege_epochs: int
    locked: list[str]


class SanctuaryLawView(ApiModel):
    restricted: bool
    fee_pct: int
    locked: list[str]


class SatireView(ApiModel):
    id: int
    satirist: NodeRef | None
    target: NodeRef
    polity: NodeRef | None
    work: NodeRef | None
    source: SatireSource
    bite: int
    tolerated: bool
    punished: bool
    judged: bool
    epoch: int
    locked: list[str]


class BelongingNodeView(ApiModel):
    node: NodeRef
    epoch: int
    realm: NodeRef | None
    identities: list[HeldIdentityView]
    fault_layer: IdentityLayer | None
    peer_groups: list[PeerGroupView]
    sanctuaries: list[SanctuaryView]
    sanctuary_law: SanctuaryLawView | None
    satires: list[SatireView]
    jester: NodeRef | None
