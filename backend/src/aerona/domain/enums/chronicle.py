from enum import StrEnum


class ChronicleKind(StrEnum):
    CREATION = "creation"
    SPEECH = "speech"
    CHALLENGE = "challenge"
    PRAYER = "prayer"
    ORDER = "order"
    FATE = "fate"
    DEATH = "death"
    BIRTH = "birth"
    SYSTEM = "system"
    MESSAGE = "message"
    CREATOR_HAND = "creator_hand"
    WORLD = "world"
    ENGINE_RAW = "engine_raw"
    KNOWLEDGE = "knowledge"
    RESOURCE = "resource"
    CULTURE = "culture"
    TRADE = "trade"
    EXPLORATION = "exploration"
    DIPLOMACY = "diplomacy"
    PRODUCTION = "production"
    LANGUAGE = "language"
    MIRACLE = "miracle"
    CIVILIZATION = "civilization"
    CREATOR_REPUTATION = "creator_reputation"
    CONSTRUCTION = "construction"
    EXISTENCE = "existence"
    DREAM = "dream"
    STAR = "star"
    DIVINE_SIGN = "divine_sign"
    CLIMATE = "climate"
    COSMIC = "cosmic"
    DEBT = "debt"
    FOREIGN_GOD = "foreign_god"
    WORLD_AGE = "world_age"
    COUNCIL = "council"
    PREVIOUS_CREATION = "previous_creation"
    SKY = "sky"
    GIFT = "gift"
    WORSHIP = "worship"
    WORLD_BIRTH = "world_birth"
    PROPHECY = "prophecy"
    COVENANT = "covenant"
    ARMY = "army"
    ASCENSION = "ascension"
    MIGRATION = "migration"
    LEGENDARY_QUEST = "legendary_quest"
    WAR = "war"
    WAR_OF_GODS = "war_of_gods"
    COSMIC_LAW = "cosmic_law"
    HORROR = "horror"
    OUTER_BEING = "outer_being"
    IMMORTALITY = "immortality"
    REBELLION = "rebellion"
    APOCALYPSE = "apocalypse"
    RESURRECTION = "resurrection"
    LINEAGE = "lineage"
    DISASTER = "disaster"
    ADVENTURE = "adventure"
    INTRIGUE = "intrigue"
    RESCUE = "rescue"
    CHIMERA = "chimera"
    ESCAPE = "escape"
    DOMESTICATION = "domestication"
    AGE_CHANGE = "age_change"
    EXPEDITION = "expedition"
    SPIRIT = "spirit"
    CURSE = "curse"
    DENIAL = "denial"
    RANSOM = "ransom"
    PROHIBITION = "prohibition"


class FeedCategory(StrEnum):
    VOYAGE = "voyage"
    GATE = "gate"
    LEAK = "leak"
    WAR = "war"
    DISASTER = "disaster"
    SKY = "sky"
    LIFE = "life"
    CIVILIZATION = "civilization"
    WORLD = "world"


class NotificationCategory(StrEnum):
    REBELLION = "rebellion"
    DEATH = "death"
    BIRTH = "birth"
    PROPHECY = "prophecy"
    APOCALYPSE = "apocalypse"
    HORROR = "horror"
    WAR = "war"
    PRAYER = "prayer"
    COSMOS = "cosmos"
    ASCENSION = "ascension"
    DISASTER = "disaster"
    EPOCH = "epoch"
    ACHIEVEMENT = "achievement"
    SOCIETY = "society"
    REPUTATION = "reputation"
    ERROR = "error"
    NOTE = "note"
    WORK = "work"


class ThreadStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class ThreadLinkRole(StrEnum):
    RELATED = "related"
    ADVANCED = "advanced"


class LegendaryQuestOutcome(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    INVALIDATED = "invalidated"


class PartOfSpeech(StrEnum):
    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    AFFIX = "affix"
    TITLE = "title"
    PLACE_NAME = "place_name"
    PROPER_NAME = "proper_name"
    NUMBER = "number"
    INTERJECTION = "interjection"


class WritingSystem(StrEnum):
    ALPHABET = "alphabet"
    SYLLABARY = "syllabary"
    PICTOGRAPHIC = "pictographic"
    KNOT = "knot"
    NOTCH = "notch"
    LOGOGRAPHIC = "logographic"
    MIXED = "mixed"
    ABJAD = "abjad"


class ChronicleAuditKind(StrEnum):
    REJECTED_MENTIONED = "rejected_mentioned"
    SON_SKIPPED = "son_skipped"
    EVENT_SKIPPED = "event_skipped"
    VERDICT_SKIPPED = "verdict_skipped"
    WINNER_AS_LOSER = "winner_as_loser"
    ACTIVE_AS_SILENT = "active_as_silent"
    DEED_MISCREDITED = "deed_miscredited"
    NUMBER_CONTRADICTION = "number_contradiction"


HEAVY_AUDIT_KINDS = frozenset(
    {
        ChronicleAuditKind.REJECTED_MENTIONED,
        ChronicleAuditKind.SON_SKIPPED,
        ChronicleAuditKind.WINNER_AS_LOSER,
        ChronicleAuditKind.ACTIVE_AS_SILENT,
        ChronicleAuditKind.DEED_MISCREDITED,
    }
)


class MajorEventCategory(StrEnum):
    CIVILIZATION = "civilization"
    LEGENDARY_QUEST = "legendary_quest"
    DISASTER = "disaster"
    SCHISM = "schism"
    INVASION = "invasion"
    RETURN_AND_BIRTH = "return_and_birth"
    LEGEND_AND_WONDER = "legend_and_wonder"
    WAR = "war"
    FAITH = "faith"
