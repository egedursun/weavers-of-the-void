from enum import StrEnum


class SoundChangeKind(StrEnum):
    SHIFT = "shift"
    LENITION = "lenition"
    VOWEL_SHIFT = "vowel_shift"
    MERGER = "merger"
    LOSS = "loss"


class SoundEnvironment(StrEnum):
    ANYWHERE = "anywhere"
    INITIAL = "initial"
    FINAL = "final"
    BETWEEN_VOWELS = "between_vowels"


class SoundChangeCause(StrEnum):
    CONTACT = "contact"
    PRESTIGE = "prestige"
    MIGRATION = "migration"
    DRIFT = "drift"
    INHERITED = "inherited"
    DECREE = "decree"


class WordOrder(StrEnum):
    SOV = "sov"
    SVO = "svo"
    VSO = "vso"
    VOS = "vos"
    OVS = "ovs"
    OSV = "osv"
    FREE = "free"


class MorphologyType(StrEnum):
    ISOLATING = "isolating"
    AGGLUTINATIVE = "agglutinative"
    FUSIONAL = "fusional"
    POLYSYNTHETIC = "polysynthetic"


class NumberSystem(StrEnum):
    NONE = "none"
    SINGULAR_PLURAL = "singular_plural"
    DUAL = "dual"
    TRIAL = "trial"
    PAUCAL = "paucal"


class SenseShift(StrEnum):
    BROADENED = "broadened"
    NARROWED = "narrowed"
    PEJORATIVE = "pejorative"
    AMELIORATIVE = "ameliorative"
    EUPHEMISM = "euphemism"
    RESTORED = "restored"


class WordRegister(StrEnum):
    COMMON = "common"
    SACRED = "sacred"
    POETIC = "poetic"
    ARCHAIC = "archaic"


class ScriptChangeCause(StrEnum):
    INVENTION = "invention"
    REFORM = "reform"
    SIMPLIFICATION = "simplification"
    BORROWING = "borrowing"


class LanguageModality(StrEnum):
    VOCAL = "vocal"
    SIGN = "sign"
    SCENT = "scent"
    COLOUR = "colour"
    TELEPATHIC = "telepathic"
    DATA = "data"


class LanguageStage(StrEnum):
    NATURAL = "natural"
    PIDGIN = "pidgin"
    CREOLE = "creole"
    DIVINE = "divine"


class LanguagePolicy(StrEnum):
    OFFICIAL = "official"
    LITURGICAL = "liturgical"
    SUPPRESSED = "suppressed"
    REVIVAL = "revival"
