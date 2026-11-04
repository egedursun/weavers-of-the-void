from aerona.api.schemas.common import ApiModel
from aerona.domain.enums.faction import FactionActionKind, FactionGoalKind, FactionKind, FactionRank, FactionScale


class FactionGoalView(ApiModel):
    id: int
    kind: FactionGoalKind
    target_id: int | None
    target: str | None
    target_key: str | None
    priority: int
    progress: int
    since_epoch: int
    set_by_player: bool
    locked: list[str]


class FactionMemberView(ApiModel):
    id: int
    name: str
    rank: FactionRank
    joined_epoch: int
    alive: bool


class FactionActionView(ApiModel):
    id: int
    epoch: int
    kind: FactionActionKind
    target_id: int | None
    target: str | None
    success: bool
    amount: int
    note: str | None


class FactionSlice(ApiModel):
    id: int
    name: str
    kind: str
    share: int


class FactionView(ApiModel):
    id: int
    name: str
    kind: FactionKind
    scale: FactionScale
    treasury: int
    cohesion: int
    secrecy: int
    armed: bool
    reputation: int
    strength: int
    wealth: int
    sway: int
    influence_over: dict[str, int]
    influence_names: dict[str, str]
    cohort_share: dict[str, float]
    home_id: int | None
    home: str | None
    leader_id: int | None
    leader: str | None
    outlawed: bool
    chartered_by_id: int | None
    chartered_by: str | None
    monopoly: str | None
    employer_id: int | None
    employer: str | None
    contract_id: int | None
    pay: int
    loyalty: int
    unpaid_epochs: int
    locked: list[str]
    goals: list[FactionGoalView]
    members: list[FactionMemberView]
    actions: list[FactionActionView]
    realm_id: int | None
    balance: list[FactionSlice]
