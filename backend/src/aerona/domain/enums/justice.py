from enum import StrEnum


class ProposalState(StrEnum):
    DEBATING = "debating"
    PASSED = "passed"
    FAILED = "failed"
    WITHDRAWN = "withdrawn"


class ProposalEvent(StrEnum):
    DEBATE = "debate"
    RIOT = "riot"
    COMPROMISE = "compromise"
    OBSTRUCTION = "obstruction"


class ProposalStance(StrEnum):
    SUPPORT = "support"
    OPPOSE = "oppose"
    OBSTRUCT = "obstruct"


class CaseStage(StrEnum):
    INVESTIGATION = "investigation"
    TRIAL = "trial"
    CLOSED = "closed"


class TrialKind(StrEnum):
    JUDGE = "judge"
    JURY = "jury"
    COMBAT = "combat"
    ORDEAL = "ordeal"


class Verdict(StrEnum):
    GUILTY = "guilty"
    ACQUITTED = "acquitted"
    FLED = "fled"
    DROPPED = "dropped"


class Deposition(StrEnum):
    ACCUSES = "accuses"
    SHIELDS = "shields"
    SILENT = "silent"
