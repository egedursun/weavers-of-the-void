from enum import StrEnum


class WorkerBodyForm(StrEnum):
    CRAFT_UNION = "craft_union"
    INDUSTRIAL_UNION = "industrial_union"
    GENERAL_UNION = "general_union"
    COMPANION_SOCIETY = "companion_society"
    MUTUAL_AID = "mutual_aid"
    WORKER_COOPERATIVE = "worker_cooperative"
    MADE_MIND_COLLECTIVE = "made_mind_collective"


class LegalStanding(StrEnum):
    BANNED = "banned"
    TOLERATED = "tolerated"
    RECOGNISED = "recognised"
    COMPULSORY = "compulsory"


class ContractStatus(StrEnum):
    PROPOSED = "proposed"
    BARGAINING = "bargaining"
    AGREED = "agreed"
    BROKEN = "broken"
    EXPIRED = "expired"


class DisputeAct(StrEnum):
    STRIKE = "strike"
    GO_SLOW = "go_slow"
    LOCKOUT = "lockout"
    BOYCOTT = "boycott"
    OCCUPATION_OF_WORKS = "occupation_of_works"
    SABOTAGE = "sabotage"


class LabourDemand(StrEnum):
    WAGE = "wage"
    HOURS = "hours"
    SAFETY = "safety"
    REST = "rest"
    KEEP = "keep"
    RECOGNITION = "recognition"


class DisputeOutcome(StrEnum):
    ONGOING = "ongoing"
    WON = "won"
    LOST = "lost"
    SETTLED = "settled"


OPEN_CONTRACTS = frozenset({ContractStatus.PROPOSED, ContractStatus.BARGAINING, ContractStatus.AGREED})


class WorkerAct(StrEnum):
    STRIKE = DisputeAct.STRIKE.value
    GO_SLOW = DisputeAct.GO_SLOW.value
    BOYCOTT = DisputeAct.BOYCOTT.value
    OCCUPATION_OF_WORKS = DisputeAct.OCCUPATION_OF_WORKS.value
    SABOTAGE = DisputeAct.SABOTAGE.value
