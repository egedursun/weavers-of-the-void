from enum import StrEnum


class MythicRealm(StrEnum):
    PALACE = "palace"
    DEAD = "dead"
    DREAM = "dream"
    SACRED_SITE = "sacred_site"


class QuestTrial(StrEnum):
    SKILL = "skill"
    PASSION = "passion"
    CONVICTION = "conviction"
    FAITH = "faith"


class HeroquestState(StrEnum):
    QUESTING = "questing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TRAPPED = "trapped"
    BROKEN = "broken"


class HeroquestBoon(StrEnum):
    BLESSING = "blessing"
    ITEM = "item"
    RITE = "rite"
    LIFTED_CURSE = "lifted_curse"
    RENEWED_LAND = "renewed_land"
    FAVOUR = "favour"
    TRUE_NAME = "true_name"
    TITLE = "title"


class MantlingState(StrEnum):
    WALKING = "walking"
    ASCENDED = "ascended"
    REPLACED = "replaced"
    BLOCKED = "blocked"
    FAILED = "failed"


class ServitorOrigin(StrEnum):
    MADE = "made"
    RAISED = "raised"
    SUMMONED = "summoned"


class ServitorRole(StrEnum):
    MESSENGER = "messenger"
    GUARD = "guard"
    JUDGE = "judge"
    HOST = "host"
    SPY = "spy"
    AGENT = "agent"
    AVENGER = "avenger"
    GUIDE_OF_SOULS = "guide_of_souls"
    WORSHIPPER = "worshipper"
    WARDEN = "warden"
    SCRIBE = "scribe"


class GeasMode(StrEnum):
    TABOO = "taboo"
    DUTY = "duty"


class GeasState(StrEnum):
    KEPT = "kept"
    BROKEN = "broken"


class GeasLayer(StrEnum):
    SEER = "seer"
    GOD = "god"
    RITE = "rite"


class CosmicOffice(StrEnum):
    DEAD = "dead"
    GATES = "gates"
    STARS = "stars"
    OATHS = "oaths"
    HERALD = "herald"
    HUNT = "hunt"


class OfficeChoice(StrEnum):
    COUNCIL = "council"
    CREATOR = "creator"
    CONQUEST = "conquest"
    MANTLING = "mantling"
