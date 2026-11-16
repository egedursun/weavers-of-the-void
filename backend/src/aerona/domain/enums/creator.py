from enum import StrEnum


class CreatorPassion(StrEnum):
    ORDER = "order"
    CHAOS = "chaos"
    BEAUTY = "beauty"
    KNOWLEDGE = "knowledge"
    WAR = "war"
    MERCY = "mercy"
    CREATION = "creation"
    SILENCE = "silence"


class CreatorMoodAxis(StrEnum):
    CONTENTMENT = "contentment"
    ANGER = "anger"
    INTEREST = "interest"
    LONELINESS = "loneliness"


class CreatorMoodLabel(StrEnum):
    ANGRY = "angry"
    DISTANT = "distant"
    LONELY = "lonely"
    CONTENT = "content"
    UNEASY = "uneasy"
    SERENE = "serene"


class CreatorSignKind(StrEnum):
    WRATH = "wrath"
    GRACE = "grace"
    SILENCE = "silence"
    DREAM = "dream"
    OMEN = "omen"
    WARNING = "warning"
    REVELATION = "revelation"
    VISITATION = "visitation"
    MARK = "mark"
    WONDER = "wonder"
    WITHDRAWAL = "withdrawal"
    TEST = "test"
    REWARD = "reward"
    COVENANT_OFFER = "covenant_offer"


class CreatorStance(StrEnum):
    WORSHIP = "worship"
    REVERENCE = "reverence"
    INDIFFERENCE = "indifference"
    FEAR = "fear"
    REJECTION = "rejection"
    DENIAL = "denial"


class CreatorHeresy(StrEnum):
    NONE = "none"
    ANTI_GOD = "anti_god"
    RIVAL_CREATOR = "rival_creator"
    DENIAL = "denial"
    MANY_CREATORS = "many_creators"
    ABSENT_CREATOR = "absent_creator"


class CovenantDuty(StrEnum):
    WORSHIP = "worship"
    PEACE = "peace"
    OFFERINGS = "offerings"
    KEEP_LAW = "keep_law"
    PROTECT_THE_WEAK = "protect_the_weak"
    SEEK_KNOWLEDGE = "seek_knowledge"


class CreatorPromise(StrEnum):
    PROTECTION = "protection"
    PLENTY = "plenty"
    GUIDANCE = "guidance"
    PRESENCE = "presence"
    LONG_LIFE = "long_life"


class CovenantState(StrEnum):
    OFFERED = "offered"
    SEALED = "sealed"
    KEPT = "kept"
    BROKEN = "broken"
    ENDED = "ended"


class ChosenFavour(StrEnum):
    RENOWN = "renown"
    PROTECTION = "protection"
    LONG_LIFE = "long_life"
    GIFT = "gift"
    FORESIGHT = "foresight"


class CreatorNature(StrEnum):
    MAKER = "maker"
    JUDGE = "judge"
    ABSENT_ONE = "absent_one"
    SOURCE = "source"
    MANY_FACED = "many_faced"
    UNKNOWABLE = "unknowable"
