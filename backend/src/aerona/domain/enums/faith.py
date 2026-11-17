from enum import StrEnum


class TenetKind(StrEnum):
    PACIFISM = "pacifism"
    HOLY_WAR = "holy_war"
    ASCETICISM = "asceticism"
    SACRED_SUFFERING = "sacred_suffering"
    PURITY_OF_BODY = "purity_of_body"
    ANCESTOR_VENERATION = "ancestor_veneration"
    HUMAN_SACRIFICE = "human_sacrifice"
    ANIMAL_SACRIFICE = "animal_sacrifice"
    CELIBATE_CLERGY = "celibate_clergy"
    PROSELYTISM = "proselytism"
    EXCLUSIVITY = "exclusivity"
    SYNCRETIC_OPENNESS = "syncretic_openness"
    MONASTIC_LEARNING = "monastic_learning"
    ANTI_MAGIC = "anti_magic"
    SANCTIFIED_MAGIC = "sanctified_magic"
    JUDGEMENT_BY_DEEDS = "judgement_by_deeds"
    JUDGEMENT_BY_FAITH = "judgement_by_faith"
    REINCARNATION = "reincarnation"
    MARTYRDOM_GLORY = "martyrdom_glory"
    DIVINE_RULE = "divine_rule"
    DIETARY_LAW = "dietary_law"
    SACRED_SPECIES = "sacred_species"
    PILGRIMAGE_DUTY = "pilgrimage_duty"
    SOULS_REST = "souls_rest"
    VOID_COMMUNION = "void_communion"
    FEEDING_THE_HUNGER = "feeding_the_hunger"
    WHISPERED_SECRETS = "whispered_secrets"
    HIDDEN_GOD = "hidden_god"


class JudgementDoctrine(StrEnum):
    DEEDS = "deeds"
    FAITH = "faith"
    RITE = "rite"
    FAVOUR = "favour"
    NONE = "none"


class ClergyFunction(StrEnum):
    LEADER = "leader"
    CELEBRANT = "celebrant"
    ASCETIC = "ascetic"
    GUARDIAN_OF_DOCTRINE = "guardian_of_doctrine"
    TEACHER = "teacher"
    HEALER = "healer"
    SEER = "seer"
    KEEPER_OF_SITES = "keeper_of_sites"
    MISSIONARY = "missionary"
    JUDGE = "judge"
    SCRIBE = "scribe"


class HoldingKind(StrEnum):
    TEMPLE = "temple"
    LAND = "land"
    RELIC = "relic"
    HOLY_PLACE = "holy_place"
    MONASTERY = "monastery"
    NETWORK = "network"
    SHARES = "shares"
    LINES = "lines"


class FanaticismKind(StrEnum):
    INQUISITION = "inquisition"
    ICONOCLASM = "iconoclasm"
    CRUSADE = "crusade"
    PURGE = "purge"
    FORCED_CONVERSION = "forced_conversion"
    MARTYRDOM = "martyrdom"
    MORTIFICATION = "mortification"
    BOOK_BURNING = "book_burning"
    PERSECUTION = "persecution"
    MILLENARIAN_FLIGHT = "millenarian_flight"


class StratumKind(StrEnum):
    REWARD = "reward"
    COMMON = "common"
    PUNISHMENT = "punishment"
    DISSOLUTION = "dissolution"
    BY_MANNER_OF_DEATH = "by_manner_of_death"
    BY_LINE = "by_line"


class StratumValence(StrEnum):
    REWARD = "reward"
    NEUTRAL = "neutral"
    PUNISHMENT = "punishment"
    MIXED = "mixed"


class StratumPermanence(StrEnum):
    ETERNAL = "eternal"
    UNTIL_REBIRTH = "until_rebirth"
    UNTIL_JUDGEMENT = "until_judgement"
    FADING = "fading"


class StratumAdmission(StrEnum):
    BY_DEEDS = "by_deeds"
    BY_FAITH = "by_faith"
    BY_MANNER_OF_DEATH = "by_manner_of_death"
    BY_LINE = "by_line"
    BY_RITES = "by_rites"
    BY_CHOICE = "by_choice"
    ALL = "all"


class StratumActivity(StrEnum):
    REST = "rest"
    SERVICE = "service"
    STRUGGLE = "struggle"
    REUNION = "reunion"
    LEARNING = "learning"
    DISSOLUTION = "dissolution"


class StratumContact(StrEnum):
    OPEN = "open"
    BY_RITE = "by_rite"
    CLOSED = "closed"


class AfterlifeState(StrEnum):
    WANDERING = "wandering"
    JUDGED = "judged"
    IN_REALM = "in_realm"
    REBORN = "reborn"
    CONSUMED = "consumed"
    RELEASED = "released"


class SpiritAlignment(StrEnum):
    GUARDIAN = "guardian"
    NEUTRAL = "neutral"
    VENGEFUL = "vengeful"


class BindingKind(StrEnum):
    NONE = "none"
    PLACE = "place"
    ITEM = "item"
    STRUCTURE = "structure"
    BEAST = "beast"
    PERSON = "person"
    REALM = "realm"
    NETWORK = "network"
    LINE = "line"


class ReincarnationGate(StrEnum):
    TENET = "tenet"
    NATURAL_LAW = "natural_law"
    RITE = "rite"
    GOD = "god"


class RebirthPath(StrEnum):
    PEOPLE = "people"
    HOUSE = "house"
    MERIT = "merit"
