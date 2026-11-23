from enum import StrEnum


class PackageKind(StrEnum):
    SNAKE_VENOM = "snake_venom"
    DRINK_DEPENDENCE = "drink_dependence"
    DRUG_DEPENDENCE = "drug_dependence"
    LYCANTHROPY = "lycanthropy"
    VAMPIRISM = "vampirism"
    DIVINE_BLESSING = "divine_blessing"
    VOID_TAINT = "void_taint"
    POSSESSION = "possession"
    TRAUMA = "trauma"
    HUNGER_CURSE = "hunger_curse"
    WARPING = "warping"
    VIS_DEPENDENCE = "vis_dependence"
    GEAS_DOOM = "geas_doom"
    SOUL_TRAPPED = "soul_trapped"
    FORTUNE = "fortune"
    TRANSFORMATION = "transformation"
    CHARM = "charm"


class Transmission(StrEnum):
    CONTACT = "contact"
    BITE = "bite"
    INGESTION = "ingestion"
    INHALATION = "inhalation"
    BLOOD = "blood"
    CURSE = "curse"
    BIRTH = "birth"
    RITE = "rite"
    GAZE = "gaze"
    EXPERIENCE = "experience"
    WATER = "water"
    SPIRIT = "spirit"
    VOID = "void"
    INTIMATE = "intimate"
    OBJECTS = "objects"


class Visibility(StrEnum):
    OBVIOUS = "obvious"
    NOTICEABLE = "noticeable"
    HIDDEN = "hidden"


class CureKind(StrEnum):
    RITE = "rite"
    TECHNIQUE = "technique"
    MEDICINE = "medicine"
    TIME = "time"
    QUEST = "quest"
    DIVINE = "divine"
    POWER = "power"
    SYMBIONT = "symbiont"
    TRANSFER = "transfer"
    AUGMENT = "augment"


class ChangeSign(StrEnum):
    SEASON = "season"
    SKY_EVENT = "sky_event"
    EMOTION = "emotion"
    WORD = "word"
    NONE = "none"


class CharmKind(StrEnum):
    LOVE = "love"
    OBEDIENCE = "obedience"
    DEVOTION = "devotion"
