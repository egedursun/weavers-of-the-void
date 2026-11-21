from enum import StrEnum


class ReferendumSubject(StrEnum):
    LAW = "law"
    CONSTITUTION = "constitution"
    INDEPENDENCE = "independence"
    UNION = "union"
    TREATY = "treaty"
    WAR = "war"
    TRANSITION = "transition"
    RECALL = "recall"
    FAITH = "faith"


class Franchise(StrEnum):
    NOBLES = "nobles"
    LANDHOLDERS = "landholders"
    CITIZENS = "citizens"
    FREE = "free"
    ALL = "all"


class ReferendumResult(StrEnum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    VOID = "void"


class VoteSide(StrEnum):
    YES = "yes"
    NO = "no"


class CampaignMeans(StrEnum):
    MONEY = "money"
    MEDIA = "media"
    SPEECH = "speech"
    FRAUD = "fraud"


class ReferendumCaller(StrEnum):
    RULER = "ruler"
    ASSEMBLY = "assembly"
    PETITION = "petition"
    LEAGUE = "league"
    GOD = "god"
