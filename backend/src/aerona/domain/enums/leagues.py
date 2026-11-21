from enum import StrEnum


class LeagueAim(StrEnum):
    DEFENCE = "defence"
    TRADE = "trade"
    CUSTOMS_UNION = "customs_union"
    CURRENCY_UNION = "currency_union"
    LAW = "law"
    FAITH = "faith"
    PEACE = "peace"
    RESEARCH = "research"
    MIGRATION = "migration"


class LeagueVoteBasis(StrEnum):
    ONE_MEMBER_ONE_VOTE = "one_member_one_vote"
    BY_POPULATION = "by_population"
    BY_DUES = "by_dues"
    BY_VETO_HOLDERS = "by_veto_holders"


class LeagueOrgan(StrEnum):
    ASSEMBLY = "assembly"
    COUNCIL = "council"
    COURT = "court"
    SECRETARIAT = "secretariat"
    FORCE = "force"


class LeagueStanding(StrEnum):
    FOUNDER = "founder"
    MEMBER = "member"
    OBSERVER = "observer"
    SUSPENDED = "suspended"
    EXPELLED = "expelled"


class LeagueDecisionKind(StrEnum):
    ADMIT = "admit"
    EXPEL = "expel"
    SANCTION = "sanction"
    COMMON_TARIFF = "common_tariff"
    COMMON_FORCE = "common_force"
    RULING = "ruling"
    BUDGET = "budget"
    MEDIATION = "mediation"


class LeagueDecisionOutcome(StrEnum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    VETOED = "vetoed"


VOTING_STANDINGS = frozenset({LeagueStanding.FOUNDER, LeagueStanding.MEMBER})
BOUND_STANDINGS = frozenset({LeagueStanding.FOUNDER, LeagueStanding.MEMBER, LeagueStanding.SUSPENDED})
