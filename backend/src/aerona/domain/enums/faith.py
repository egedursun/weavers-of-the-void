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
    DIVINE_KINGSHIP = "divine_kingship"
    DIETARY_LAW = "dietary_law"
    SACRED_SPECIES = "sacred_species"
    PILGRIMAGE_DUTY = "pilgrimage_duty"
    SOULS_REST = "souls_rest"
    VOID_COMMUNION = "void_communion"
    FEEDING_THE_HUNGER = "feeding_the_hunger"
    WHISPERED_SECRETS = "whispered_secrets"


class JudgementDoctrine(StrEnum):
    DEEDS = "deeds"
    FAITH = "faith"
    RITE = "rite"
    FAVOUR = "favour"
    NONE = "none"


class ClergyOffice(StrEnum):
    HIGH_PRIEST = "high_priest"
    PRIEST = "priest"
    MONK = "monk"
    INQUISITOR = "inquisitor"


class HoldingKind(StrEnum):
    TEMPLE = "temple"
    LAND = "land"
    RELIC = "relic"
    HOLY_PLACE = "holy_place"
    MONASTERY = "monastery"


class FanaticismKind(StrEnum):
    INQUISITION = "inquisition"
    ICONOCLASM = "iconoclasm"
    CRUSADE = "crusade"


class StratumKind(StrEnum):
    PARADISE = "paradise"
    PLAIN = "plain"
    TORMENT = "torment"
    OBLIVION = "oblivion"
    WARRIOR_HALL = "warrior_hall"
    ANCESTOR_HALL = "ancestor_hall"


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


class ReincarnationGate(StrEnum):
    TENET = "tenet"
    NATURAL_LAW = "natural_law"
    RITE = "rite"
    GOD = "god"


class FuneralRite(StrEnum):
    BURIAL = "burial"
    BURNING = "burning"
    EXPOSURE = "exposure"
    NAMELESS = "nameless"
    NONE = "none"


class RebirthPath(StrEnum):
    PEOPLE = "people"
    HOUSE = "house"
    MERIT = "merit"
