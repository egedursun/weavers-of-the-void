from enum import StrEnum


class GeniusLocusKind(StrEnum):
    RIVER = "river"
    SPRING = "spring"
    LAKE = "lake"
    WELL = "well"
    SHORE = "shore"
    GROVE = "grove"
    FOREST = "forest"
    MOUNTAIN = "mountain"
    CAVE = "cave"
    CROSSROADS = "crossroads"
    WILDS = "wilds"
    FIELD = "field"
    CITY = "city"
    HEARTH = "hearth"
    SEA = "sea"
    RUIN = "ruin"
    BATTLEFIELD = "battlefield"
    MARSH = "marsh"
    DESERT = "desert"
    GLACIER = "glacier"


class SpiritOffence(StrEnum):
    POLLUTION = "pollution"
    CLEARING = "clearing"
    UNPAID = "unpaid"
    TABOO = "taboo"
    BLOODSHED = "bloodshed"
    OVERHARVEST = "overharvest"
    TRESPASS = "trespass"
    NOISE = "noise"


class BureauRank(StrEnum):
    HEARTH = "hearth"
    LOCAL = "local"
    CITY = "city"
    PROVINCE = "province"
    MINISTRY = "ministry"


class PetitionKind(StrEnum):
    HEALING = "healing"
    HARVEST = "harvest"
    FERTILITY = "fertility"
    SAFE_PASSAGE = "safe_passage"
    PROSPERITY = "prosperity"
    SUIT = "suit"
    RAIN = "rain"
    PROTECTION = "protection"
    VENGEANCE = "vengeance"
    FINDING = "finding"
    JUSTICE = "justice"


class PetitionStatus(StrEnum):
    FILED = "filed"
    DELAYED = "delayed"
    GRANTED = "granted"
    DENIED = "denied"
    APPEALED = "appealed"
    DISMISSED = "dismissed"


class MysticState(StrEnum):
    SEEKER = "seeker"
    VISIONARY = "visionary"
    REVERED = "revered"
    PERSECUTED = "persecuted"
    FOUNDER = "founder"
    LAPSED = "lapsed"
    HERMIT = "hermit"


class VisionKind(StrEnum):
    VISION = "vision"
    UNION = "union"
    VOICE = "voice"
    TRANCE = "trance"
    DREAM = "dream"
    ORACLE_SPEECH = "oracle_speech"
    SIGN = "sign"


class MillenarianStage(StrEnum):
    STIRRING = "stirring"
    GATHERING = "gathering"
    VIGIL = "vigil"
    MARCHING = "marching"
    REDATED = "redated"
    SECT = "sect"
    DISPERSED = "dispersed"


class TheodicyCause(StrEnum):
    PLAGUE = "plague"
    FAMINE = "famine"
    DEFEAT = "defeat"
    DISASTER = "disaster"
    PERSECUTION = "persecution"
    LONG_SEASON = "long_season"
    LEADER_LOST = "leader_lost"
    SCHISM = "schism"


class TheodicyResolution(StrEnum):
    PENDING = "pending"
    ANSWERED = "answered"
    ARGUED = "argued"
    NEW_DOCTRINE = "new_doctrine"
    CONVERSION = "conversion"
    SECULAR_DRIFT = "secular_drift"


class SacramentKind(StrEnum):
    BIRTH_BLESSING = "birth_blessing"
    INITIATION = "initiation"
    MARRIAGE = "marriage"
    LAST_RITES = "last_rites"
    PURIFICATION = "purification"
    ORDINATION = "ordination"
    PENANCE = "penance"
    COMMUNION = "communion"


class SacramentProtection(StrEnum):
    ROUTING = "routing"
    POSSESSION = "possession"
    UNREST = "unrest"
    CURSE = "curse"
    FORTUNE = "fortune"


class AfterlifeModel(StrEnum):
    JUDGED_REALMS = "judged_realms"
    COMMON_REALM = "common_realm"
    REALM_BY_DEATH = "realm_by_death"
    REALM_OF_LINE = "realm_of_line"
    REBIRTH = "rebirth"
    WANDERING = "wandering"
    UNION = "union"
    OBLIVION = "oblivion"
    AMONG_LIVING = "among_living"


class DivinationKind(StrEnum):
    AUGURY = "augury"
    HARUSPICY = "haruspicy"
    ASTROLOGY = "astrology"
    ORACLE = "oracle"
    LOTS = "lots"
    DREAM_READING = "dream_reading"
    SCRYING = "scrying"
    SPIRIT_CONSULTATION = "spirit_consultation"
    EARTH_SIGNS = "earth_signs"
    NUMEROLOGY = "numerology"
    BODY_READING = "body_reading"


class DivinationValidity(StrEnum):
    GOD_ANSWERS = "god_answers"
    SEER_GIFT = "seer_gift"
    NATURAL_LAW = "natural_law"
    NOISE = "noise"


class DivinationQuestion(StrEnum):
    BATTLE = "battle"
    WAR = "war"
    WEDDING = "wedding"
    CORONATION = "coronation"
    HARVEST = "harvest"
    VOYAGE = "voyage"
    FOUNDING = "founding"
    ILLNESS = "illness"
    SUCCESSION = "succession"
    LOST_THINGS = "lost_things"


class OmenVerdict(StrEnum):
    AUSPICIOUS = "auspicious"
    INAUSPICIOUS = "inauspicious"
    UNCLEAR = "unclear"


class ForesightSource(StrEnum):
    POWER = "power"
    DIVINATION = "divination"
    GOD = "god"
    MADE_ORACLE = "made_oracle"
    DREAM = "dream"


class ForesightStatus(StrEnum):
    PENDING = "pending"
    FULFILLED = "fulfilled"
    FAILED = "failed"
    CLOUDED = "clouded"


class SignInfluence(StrEnum):
    REAL = "real"
    BELIEVED = "believed"
