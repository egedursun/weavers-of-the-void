from enum import StrEnum


class AgentKind(StrEnum):
    SON = "son"
    MORTAL = "mortal"


class MessageIntent(StrEnum):
    FRIENDSHIP = "friendship"
    ALLIANCE = "alliance"
    LOVE = "love"
    THREAT = "threat"
    MOCKERY = "mockery"
    WARNING = "warning"
    BARGAIN = "bargain"
    PRAYER = "prayer"
    ANSWER = "answer"
    CHAT = "chat"
    DREAM = "dream"
    COMMAND = "command"


class PrayerRequest(StrEnum):
    ESSENCE = "essence"
    BLESSING = "blessing"
    PERMISSION = "permission"
    VENGEANCE = "vengeance"
    FORGIVENESS = "forgiveness"
    NONE = "none"
    WISH = "wish"


class Verdict(StrEnum):
    UNJUDGED = "unjudged"
    ACCEPTED = "accepted"
    FIXED = "fixed"
    REJECTED = "rejected"
    LIMBO = "limbo"


class TurnCounter(StrEnum):
    SIBLING_MESSAGES = "sibling_messages"
    NARRATIVE_BONDS = "narrative_bonds"
    PRAYERS = "prayers"
    FREE_LIVING_CREATION = "free_living_creation"
    FREE_LAND_CREATION = "free_land_creation"
    ANCHOR_CHOSEN = "anchor_chosen"
    WORDS_COINED = "words_coined"
    GIFTS = "gifts"
    HOLY_WORLD = "holy_world"
    LEAK_STITCHED = "leak_stitched"
    TAKE_LIFE = "take_life"
    INTRIGUE = "intrigue"
    OUTER_BARGAIN = "outer_bargain"
    HARVESTS = "harvests"
    DISCOVERIES = "discoveries"
    CLAIMS = "claims"
    WORSHIP_CHANGES = "worship_changes"
    LEARNING = "learning"
    PROPHECIES = "prophecies"
    COMMANDER_APPOINTMENTS = "commander_appointments"
    ADOPTIONS = "adoptions"
    EXPLORATIONS = "explorations"
    REPEATED_CREATIONS = "repeated_creations"
    RESURRECTION_RITES = "resurrection_rites"
    LANGUAGES_FOUNDED = "languages_founded"
    CULTURES_CREATED = "cultures_created"
    LAND_REWARDS = "land_rewards"


class PendingJobKind(StrEnum):
    WORLD_BIRTH = "world_birth"
    CHILD_BIRTH = "child_birth"


class CouncilVote(StrEnum):
    YES = "yes"
    NO = "no"
    ABSTAIN = "abstain"


class CouncilCaller(StrEnum):
    CREATOR = "creator"
    FATE = "fate"


class ToolBlock(StrEnum):
    RARITY = "rarity"
    ACTOR_TYPE = "actor_type"
    CIVILIZATION_TIER = "civilization_tier"
    WORLD_STATE = "world_state"
    UNWIRED = "unwired"
