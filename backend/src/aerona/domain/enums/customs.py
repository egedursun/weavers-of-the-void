from enum import StrEnum


class RevivalWay(StrEnum):
    RESTORE = "restore"
    SYNTHESIS = "synthesis"
    ADOPT = "adopt"
    AWAIT = "await"
    WITHDRAW = "withdraw"
    MIGRATE = "migrate"


class RevivalStage(StrEnum):
    STEADY = "steady"
    STRESS = "stress"
    DISTORTION = "distortion"
    REVITALISATION = "revitalisation"
    NEW_STEADY = "new_steady"
    SUPPRESSED = "suppressed"


class RevivalGoal(StrEnum):
    REVIVE_LANGUAGE = "revive_language"
    RESTORE_GOD = "restore_god"
    EXPEL_FOREIGNERS = "expel_foreigners"
    RESTORE_LAND = "restore_land"
    RESTORE_RULE = "restore_rule"
    RESTORE_LAW = "restore_law"


class Intoxicant(StrEnum):
    BREW = "brew"
    WINE = "wine"
    SPIRITS = "spirits"
    SMOKE = "smoke"
    LEAF = "leaf"
    FUNGUS = "fungus"
    ESSENCE = "essence"
    SYNTHETIC = "synthetic"
    ANIMAL_DERIVED = "animal_derived"
    STIMULANT = "stimulant"
    RESIN = "resin"


class IntoxicantUse(StrEnum):
    DAILY = "daily"
    FEAST = "feast"
    RITE = "rite"
    MOURNING = "mourning"
    FORBIDDEN = "forbidden"
    MEDICINE = "medicine"
    HOSPITALITY = "hospitality"
    WORK = "work"
    COURAGE = "courage"


class MarkKind(StrEnum):
    TATTOO = "tattoo"
    SCAR = "scar"
    PIERCING = "piercing"
    SHAPING = "shaping"
    FILED_TEETH = "filed_teeth"
    COSMETIC = "cosmetic"
    JEWELLERY = "jewellery"
    BRAND = "brand"
    HAIR = "hair"
    IMPLANT = "implant"
    PAINT = "paint"
    STAIN = "stain"


class MarkMeaning(StrEnum):
    STATUS = "status"
    CLAN = "clan"
    DEED = "deed"
    AGE_SET = "age_set"
    MARRIAGE = "marriage"
    MOURNING = "mourning"
    PROTECTION = "protection"
    CRIME = "crime"
    FAITH = "faith"
    PROFESSION = "profession"
    BEAUTY = "beauty"
    HEALING = "healing"
    BOUND_LABOUR = "bound_labour"


class NamingPattern(StrEnum):
    GIVEN = "given"
    PARENT = "parent"
    CLAN = "clan"
    TEKNONYM = "teknonym"
    PLACE = "place"
    TRADE = "trade"
    ANCESTRAL = "ancestral"
    EVENT = "event"


class NameForm(StrEnum):
    BIRTH = "birth"
    SECRET = "secret"
    DEED = "deed"
    INITIATION = "initiation"
    MARRIAGE = "marriage"
    VOW = "vow"
    ASCENSION = "ascension"
    POSTHUMOUS = "posthumous"
    EPITHET = "epithet"
    ADOPTION = "adoption"


class AgeGrade(StrEnum):
    CHILDREN = "children"
    YOUTHS = "youths"
    YOUNG_ADULTS = "young_adults"
    JUNIOR_ELDERS = "junior_elders"
    SENIOR_ELDERS = "senior_elders"
    ANCIENTS = "ancients"


class GradeDuty(StrEnum):
    WAR = "war"
    HERDING = "herding"
    LABOUR = "labour"
    COUNCIL = "council"


class EvidenceKind(StrEnum):
    WITNESS = "witness"
    TRACE = "trace"
    DOCUMENT = "document"
    CONFESSION = "confession"
    DIVINATION = "divination"
    MAGIC = "magic"
    EXPERT = "expert"
    HEARSAY = "hearsay"
    RECORD = "record"
    BODY = "body"


class Membership(StrEnum):
    CITIZEN = "citizen"
    SUBJECT = "subject"
    RESIDENT_FOREIGNER = "resident_foreigner"
    PROTECTED_MINORITY = "protected_minority"
    BOUND = "bound"
    STATELESS = "stateless"


class MemberRight(StrEnum):
    OFFICE = "office"
    MARRIAGE = "marriage"
    ARMS = "arms"
    COURTS = "courts"
    PROPERTY = "property"
    MOVEMENT = "movement"
    VOTE = "vote"
    WORSHIP = "worship"
    ASSEMBLY = "assembly"
    EDUCATION = "education"


class Naturalisation(StrEnum):
    DESCENT = "descent"
    BIRTHPLACE = "birthplace"
    RESIDENCE = "residence"
    CONVERSION = "conversion"
    SERVICE = "service"
    PURCHASE = "purchase"
    GRANT = "grant"
    UNION = "union"
    ADOPTION = "adoption"


class ReliefKind(StrEnum):
    GRANARY = "granary"
    ALMS = "alms"
    WORKHOUSE = "workhouse"
    PARISH = "parish"
    FOSTER_CARE = "foster_care"
    SICK_HOUSE = "sick_house"
    PENSION = "pension"
    PUBLIC_KITCHEN = "public_kitchen"
    SHELTER = "shelter"


class CoopPurpose(StrEnum):
    MILL = "mill"
    BOATS = "boats"
    IRRIGATION = "irrigation"
    INSURANCE = "insurance"
    BURIAL = "burial"
    CREDIT = "credit"
    GRANARY = "granary"
    HERDING = "herding"
    SCHOOL = "school"
    HOUSING = "housing"
