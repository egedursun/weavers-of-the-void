from enum import StrEnum


class GoverningBody(StrEnum):
    FOUNDER = "founder"
    HEAD = "head"
    BOARD = "board"
    CHAPTER = "chapter"
    ASSEMBLY_OF_MEMBERS = "assembly_of_members"
    COUNCIL_OF_ELDERS = "council_of_elders"
    SHAREHOLDERS_MEETING = "shareholders_meeting"
    MADE_MIND = "made_mind"
    NONE = "none"


class HeadSelection(StrEnum):
    APPOINTED_BY_OWNER = "appointed_by_owner"
    ELECTED_BY_BODY = "elected_by_body"
    ELECTED_BY_MEMBERS = "elected_by_members"
    INHERITED = "inherited"
    SENIORITY = "seniority"
    LOT = "lot"
    DIVINATION = "divination"
    PURCHASE = "purchase"


class VoteBasis(StrEnum):
    ONE_MEMBER_ONE_VOTE = "one_member_one_vote"
    BY_SHARE = "by_share"
    BY_RANK = "by_rank"
    BY_SENIORITY = "by_seniority"


class OrgStrategy(StrEnum):
    GROW = "grow"
    HOLD = "hold"
    SPECIALISE = "specialise"
    DIVERSIFY = "diversify"
    EXPAND_ABROAD = "expand_abroad"
    INTEGRATE_UP = "integrate_up"
    INTEGRATE_DOWN = "integrate_down"
    LOBBY = "lobby"
    RESEARCH = "research"
    WITHDRAW = "withdraw"


class CliqueAim(StrEnum):
    STRATEGY = "strategy"
    HEAD = "head"
    SPLIT = "split"
    MERGER = "merger"


class MergerKind(StrEnum):
    MERGER = "merger"
    FRIENDLY_ACQUISITION = "friendly_acquisition"
    HOSTILE_TAKEOVER = "hostile_takeover"
    BUYOUT = "buyout"
    ABSORPTION_BY_POLITY = "absorption_by_polity"


class MergerStage(StrEnum):
    BID = "bid"
    RESISTED = "resisted"
    AGREED = "agreed"
    CLOSED = "closed"
    BLOCKED = "blocked"
    WITHDRAWN = "withdrawn"


class InsolvencyPath(StrEnum):
    LIQUIDATION = "liquidation"
    RESTRUCTURING = "restructuring"
    RESCUE_BY_OWNER = "rescue_by_owner"
    RESCUE_BY_POLITY = "rescue_by_polity"
    SEIZURE_BY_CREDITOR = "seizure_by_creditor"


class InsolvencyStage(StrEnum):
    FILED = "filed"
    CLAIMS = "claims"
    SETTLED = "settled"
    CLOSED = "closed"


class VoteChoice(StrEnum):
    FOR = "for"
    AGAINST = "against"


OPEN_MERGER_STAGES = frozenset({MergerStage.BID, MergerStage.RESISTED, MergerStage.AGREED})
OPEN_INSOLVENCY_STAGES = frozenset({InsolvencyStage.FILED, InsolvencyStage.CLAIMS, InsolvencyStage.SETTLED})
