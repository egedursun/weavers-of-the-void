from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.faction import FactionKind as F
from aerona.domain.enums.faction import FactionRank
from aerona.domain.enums.governance import GoverningBody as B
from aerona.domain.enums.governance import HeadSelection as H
from aerona.domain.enums.governance import OrgStrategy
from aerona.domain.enums.governance import VoteBasis as V


@dataclass(frozen=True)
class OrgForm:
    body: B
    selection: H
    basis: V


ORG_FORMS: MappingProxyType[F, OrgForm] = total(
    F,
    {
        F.MERCHANT_GUILD: OrgForm(B.ASSEMBLY_OF_MEMBERS, H.ELECTED_BY_MEMBERS, V.BY_RANK),
        F.CRAFT_GUILD: OrgForm(B.ASSEMBLY_OF_MEMBERS, H.ELECTED_BY_MEMBERS, V.BY_RANK),
        F.PRIESTHOOD: OrgForm(B.CHAPTER, H.ELECTED_BY_BODY, V.BY_RANK),
        F.WARRIOR_ORDER: OrgForm(B.CHAPTER, H.ELECTED_BY_BODY, V.BY_RANK),
        F.NOBLE_COUNCIL: OrgForm(B.COUNCIL_OF_ELDERS, H.SENIORITY, V.BY_SENIORITY),
        F.PEASANT_LEAGUE: OrgForm(B.ASSEMBLY_OF_MEMBERS, H.ELECTED_BY_MEMBERS, V.ONE_MEMBER_ONE_VOTE),
        F.REBELS: OrgForm(B.HEAD, H.ELECTED_BY_MEMBERS, V.ONE_MEMBER_ONE_VOTE),
        F.BANDITS: OrgForm(B.HEAD, H.SENIORITY, V.BY_RANK),
        F.PIRATES: OrgForm(B.ASSEMBLY_OF_MEMBERS, H.ELECTED_BY_MEMBERS, V.ONE_MEMBER_ONE_VOTE),
        F.ASSASSINS: OrgForm(B.HEAD, H.APPOINTED_BY_OWNER, V.BY_RANK),
        F.SCHOLARS_ACADEMY: OrgForm(B.ASSEMBLY_OF_MEMBERS, H.ELECTED_BY_MEMBERS, V.BY_SENIORITY),
        F.SECRET_SOCIETY: OrgForm(B.COUNCIL_OF_ELDERS, H.ELECTED_BY_BODY, V.BY_RANK),
        F.MERCENARY_COMPANY: OrgForm(B.HEAD, H.SENIORITY, V.BY_RANK),
        F.INTERWORLD_FEDERATION: OrgForm(B.ASSEMBLY_OF_MEMBERS, H.ELECTED_BY_BODY, V.ONE_MEMBER_ONE_VOTE),
        F.WANDERING_MARKET: OrgForm(B.ASSEMBLY_OF_MEMBERS, H.ELECTED_BY_MEMBERS, V.ONE_MEMBER_ONE_VOTE),
        F.ROUTE_RAIDERS: OrgForm(B.HEAD, H.SENIORITY, V.BY_RANK),
        F.SOCIAL_CIRCLE: OrgForm(B.ASSEMBLY_OF_MEMBERS, H.ELECTED_BY_MEMBERS, V.ONE_MEMBER_ONE_VOTE),
        F.MAGE_ORDER: OrgForm(B.CHAPTER, H.ELECTED_BY_BODY, V.BY_RANK),
        F.ESTATE: OrgForm(B.COUNCIL_OF_ELDERS, H.SENIORITY, V.BY_RANK),
        F.PARTY: OrgForm(B.ASSEMBLY_OF_MEMBERS, H.ELECTED_BY_MEMBERS, V.ONE_MEMBER_ONE_VOTE),
        F.MOVEMENT: OrgForm(B.ASSEMBLY_OF_MEMBERS, H.ELECTED_BY_MEMBERS, V.ONE_MEMBER_ONE_VOTE),
        F.CHARTERED_COMPANY: OrgForm(B.SHAREHOLDERS_MEETING, H.ELECTED_BY_BODY, V.BY_SHARE),
        F.HOLY_ORDER: OrgForm(B.CHAPTER, H.ELECTED_BY_BODY, V.BY_RANK),
        F.CRIME_FAMILY: OrgForm(B.HEAD, H.INHERITED, V.BY_RANK),
        F.THIEVES_GUILD: OrgForm(B.COUNCIL_OF_ELDERS, H.ELECTED_BY_BODY, V.BY_RANK),
        F.SMUGGLING_RING: OrgForm(B.HEAD, H.SENIORITY, V.BY_RANK),
        F.PIRATE_CONFEDERACY: OrgForm(B.ASSEMBLY_OF_MEMBERS, H.ELECTED_BY_BODY, V.BY_RANK),
        F.ART_MOVEMENT: OrgForm(B.ASSEMBLY_OF_MEMBERS, H.ELECTED_BY_MEMBERS, V.ONE_MEMBER_ONE_VOTE),
        F.CLUB: OrgForm(B.ASSEMBLY_OF_MEMBERS, H.ELECTED_BY_MEMBERS, V.ONE_MEMBER_ONE_VOTE),
        F.LEAGUE: OrgForm(B.ASSEMBLY_OF_MEMBERS, H.ELECTED_BY_BODY, V.ONE_MEMBER_ONE_VOTE),
        F.WORKERS_UNION: OrgForm(B.ASSEMBLY_OF_MEMBERS, H.ELECTED_BY_MEMBERS, V.ONE_MEMBER_ONE_VOTE),
        F.WORKER_BODY: OrgForm(B.ASSEMBLY_OF_MEMBERS, H.ELECTED_BY_MEMBERS, V.ONE_MEMBER_ONE_VOTE),
        F.ENGINEERS_SOCIETY: OrgForm(B.BOARD, H.ELECTED_BY_MEMBERS, V.BY_SENIORITY),
        F.FINANCIERS: OrgForm(B.BOARD, H.ELECTED_BY_BODY, V.BY_SHARE),
        F.VETERANS: OrgForm(B.ASSEMBLY_OF_MEMBERS, H.ELECTED_BY_MEMBERS, V.ONE_MEMBER_ONE_VOTE),
    },
)
CULT_FORM = OrgForm(B.CHAPTER, H.ELECTED_BY_BODY, V.BY_RANK)

RANK_WEIGHT: MappingProxyType[FactionRank, int] = total(
    FactionRank,
    {FactionRank.LEADER: 4, FactionRank.OFFICER: 3, FactionRank.MEMBER: 2, FactionRank.NOVICE: 1},
)
BODY_RANKS: MappingProxyType[B, frozenset[FactionRank]] = total(
    B,
    {
        B.FOUNDER: frozenset({FactionRank.LEADER}),
        B.HEAD: frozenset({FactionRank.LEADER}),
        B.BOARD: frozenset({FactionRank.LEADER, FactionRank.OFFICER}),
        B.CHAPTER: frozenset({FactionRank.LEADER, FactionRank.OFFICER}),
        B.ASSEMBLY_OF_MEMBERS: frozenset({FactionRank.LEADER, FactionRank.OFFICER, FactionRank.MEMBER}),
        B.COUNCIL_OF_ELDERS: frozenset({FactionRank.LEADER, FactionRank.OFFICER}),
        B.SHAREHOLDERS_MEETING: frozenset(),
        B.MADE_MIND: frozenset({FactionRank.LEADER}),
        B.NONE: frozenset(),
    },
)
STRATEGY_TREASURY_PCT: MappingProxyType[OrgStrategy, int] = total(
    OrgStrategy,
    {
        OrgStrategy.GROW: 2,
        OrgStrategy.HOLD: 0,
        OrgStrategy.SPECIALISE: 1,
        OrgStrategy.DIVERSIFY: 1,
        OrgStrategy.EXPAND_ABROAD: 2,
        OrgStrategy.INTEGRATE_UP: 1,
        OrgStrategy.INTEGRATE_DOWN: 1,
        OrgStrategy.LOBBY: -1,
        OrgStrategy.RESEARCH: -1,
        OrgStrategy.WITHDRAW: -2,
    },
)
