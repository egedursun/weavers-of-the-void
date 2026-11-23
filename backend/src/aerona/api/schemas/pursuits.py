from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.arts import ArtMarketRole, CanonPath, ClubKind, FandomLine, ForgeryKind, ForgeryStatus
from aerona.domain.enums.body import BodyFunction
from aerona.domain.enums.constructs import CommandToken, ContractStatus, InstructionBinding, MindWill, OrderCondition, OrderKind
from aerona.domain.enums.culture import MagicSource
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.sacred import SignInfluence


class ArtPriceView(ApiModel):
    artwork: NodeRef
    price: int
    provenance: int
    acclaim: int
    interest: int
    last_buyer: NodeRef | None
    last_sale_epoch: int | None
    updated_epoch: int
    locked: list[str]


class ArtSaleView(ApiModel):
    id: int
    artwork: NodeRef
    seller: NodeRef | None
    buyer: NodeRef | None
    price: int
    fair_place: NodeRef | None
    epoch: int
    locked: list[str]


class CollectorView(ApiModel):
    holder: NodeRef
    role: ArtMarketRole
    taste: NodeRef | None
    connoisseurship: int
    since_epoch: int
    locked: list[str]


class ForgeryView(ApiModel):
    id: int
    item: NodeRef
    kind: ForgeryKind
    forger: NodeRef | None
    original: NodeRef | None
    brand_id: int | None
    claim_id: int | None
    skill: int
    status: ForgeryStatus
    exposed_by: NodeRef | None
    exposed_epoch: int | None
    made_epoch: int
    locked: list[str]


class CanonWorkView(ApiModel):
    people: NodeRef
    artwork: NodeRef
    path: CanonPath
    weight: int
    contested: bool
    since_epoch: int
    locked: list[str]


class ArtMovementView(ApiModel):
    faction: NodeRef
    manifesto: dict[str, int]
    art_form: NodeRef | None
    orthodoxy: bool
    scandals: int
    patrons: int
    founded_epoch: int
    locked: list[str]


class ClubView(ApiModel):
    faction: NodeRef
    kind: ClubKind
    league: NodeRef | None
    arena: NodeRef | None
    wins: int
    losses: int
    rating: int
    fandom: int
    line: FandomLine
    line_node: NodeRef | None
    leverage: int
    bought_by: NodeRef | None
    fixed_by: NodeRef | None
    fixed_winner: NodeRef | None
    founded_epoch: int
    locked: list[str]


class LeagueView(ApiModel):
    faction: NodeRef
    polity: NodeRef | None
    champion: NodeRef | None
    season_epoch: int
    locked: list[str]


class MatchView(ApiModel):
    id: int
    league: NodeRef | None
    home: NodeRef
    away: NodeRef
    winner: NodeRef | None
    stake: int
    riot: bool
    fixed_by: NodeRef | None
    fixing_exposed: bool
    epoch: int
    locked: list[str]


class BetView(ApiModel):
    id: int
    match_id: int
    settlement: NodeRef
    club: NodeRef
    stake: int
    won: bool | None
    locked: list[str]


class InstructionOrderView(ApiModel):
    id: int
    kind: OrderKind
    target: NodeRef | None
    priority: int
    condition: OrderCondition
    until_epoch: int | None
    lapsed: bool
    locked: list[str]


class InstructionSetView(ApiModel):
    id: int
    owner: NodeRef
    binding: InstructionBinding
    command_token: CommandToken
    token: NodeRef | None
    holder: NodeRef | None
    kill_switch: bool
    kill_token: NodeRef | None
    literalness: int
    orders: list[InstructionOrderView]
    locked: list[str]


class ConstructView(ApiModel):
    body: NodeRef
    material: MaterialKind
    power_source: MagicSource
    power: int
    upkeep: int
    maker: NodeRef | None
    decay: int
    will: MindWill
    soul: NodeRef | None
    made_epoch: int
    locked: list[str]


class RemadeView(ApiModel):
    mortal: NodeRef
    lost_function: BodyFunction | None
    forced_function: BodyFunction | None
    sentenced_by: NodeRef | None
    case_id: int | None
    bound_to: NodeRef | None
    grievance: int
    epoch: int
    locked: list[str]


class MonsterContractView(ApiModel):
    id: int
    community: NodeRef
    beast: NodeRef
    bounty: int
    hunter: NodeRef | None
    status: ContractStatus
    study: int
    posted_epoch: int
    closed_epoch: int | None
    locked: list[str]


class BirthSignView(ApiModel):
    mortal: NodeRef
    season: int
    ruling_celestial: NodeRef | None
    dreaded: bool
    influence: SignInfluence
    fortune: int
    exposed: bool
    born_epoch: int
    locked: list[str]


class PursuitsNodeView(ApiModel):
    node: NodeRef
    prices: list[ArtPriceView]
    sales: list[ArtSaleView]
    collector: CollectorView | None
    forgeries: list[ForgeryView]
    canon: list[CanonWorkView]
    movement: ArtMovementView | None
    clubs: list[ClubView]
    league: LeagueView | None
    matches: list[MatchView]
    bets: list[BetView]
    as_construct: ConstructView | None
    made: list[ConstructView]
    instructions: list[InstructionSetView]
    remade: RemadeView | None
    contracts: list[MonsterContractView]
    sign: BirthSignView | None
