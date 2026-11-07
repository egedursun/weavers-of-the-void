from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.polity import RegionalStanding
from aerona.domain.enums.statecraft import CrisisDemand, CrisisSide, CrisisState, SubjectKind


class RegardView(ApiModel):
    holder: NodeRef
    subject: NodeRef
    threat: int
    trust: int
    locked: list[str]


class DiplomacyView(ApiModel):
    capacity: int
    relations: int
    strain: int
    locked: list[str]


class BackerView(ApiModel):
    backer: NodeRef
    side: CrisisSide
    promised: int
    swing: bool
    locked: bool


class CrisisView(ApiModel):
    id: int
    demander: NodeRef | None
    target: NodeRef | None
    demand: CrisisDemand
    subject: NodeRef | None
    amount: int
    escalation: int
    steps: int
    state: CrisisState
    opened_epoch: int
    resolved_epoch: int | None
    locked: list[str]
    backers: list[BackerView]


class SphereView(ApiModel):
    power: NodeRef
    client: NodeRef
    strength: int
    since_epoch: int
    locked: bool


class SubjectView(ApiModel):
    vassal: NodeRef
    overlord: NodeRef
    kind: SubjectKind
    tribute_pct: int
    levy_pct: int
    loyalty: int
    liberty: int
    private_war: bool
    coinage: bool
    confirm_succession: bool
    pays_tribute: bool
    sends_levies: bool
    since_epoch: int
    locked: list[str]


class StatecraftView(ApiModel):
    node_id: int
    realm: NodeRef | None
    standing: RegionalStanding | None
    coalition_threshold: int
    liberty_revolt: int
    diplomacy: DiplomacyView | None
    felt: list[RegardView]
    feared: list[RegardView]
    crises: list[CrisisView]
    spheres: list[SphereView]
    subjects: list[SubjectView]
