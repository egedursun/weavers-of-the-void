from enum import StrEnum


class SoundChangeKind(StrEnum):
    SHIFT = "shift"
    LENITION = "lenition"
    VOWEL_SHIFT = "vowel_shift"
    MERGER = "merger"
    LOSS = "loss"
    METATHESIS = "metathesis"
    EPENTHESIS = "epenthesis"
    ASSIMILATION = "assimilation"
    PALATALISATION = "palatalisation"
    TONOGENESIS = "tonogenesis"


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


class NumeralBase(StrEnum):
    DECIMAL = "decimal"
    VIGESIMAL = "vigesimal"
    DUODECIMAL = "duodecimal"
    SEXAGESIMAL = "sexagesimal"
    OCTAL = "octal"
    BODY_TALLY = "body_tally"


class SenseShift(StrEnum):
    BROADENED = "broadened"
    NARROWED = "narrowed"
    PEJORATIVE = "pejorative"
    AMELIORATIVE = "ameliorative"
    EUPHEMISM = "euphemism"
    RESTORED = "restored"
    EXTENDED = "extended"
    ASSOCIATED = "associated"


class WordRegister(StrEnum):
    COMMON = "common"
    SACRED = "sacred"
    POETIC = "poetic"
    ARCHAIC = "archaic"
    TABOO = "taboo"
    TECHNICAL = "technical"
    HONORIFIC = "honorific"


class ScriptChangeCause(StrEnum):
    INVENTION = "invention"
    REFORM = "reform"
    SIMPLIFICATION = "simplification"
    BORROWING = "borrowing"
    IMPOSITION = "imposition"
    REVELATION = "revelation"


class LanguageModality(StrEnum):
    VOCAL = "vocal"
    SIGN = "sign"
    SCENT = "scent"
    COLOUR = "colour"
    TELEPATHIC = "telepathic"
    DATA = "data"
    CHEMICAL = "chemical"
    TACTILE = "tactile"
    VIBRATION = "vibration"
    ELECTRIC = "electric"


class LanguageStage(StrEnum):
    NATURAL = "natural"
    PIDGIN = "pidgin"
    CREOLE = "creole"
    DIVINE = "divine"
    CONSTRUCTED = "constructed"
    REVIVED = "revived"


class LanguagePolicy(StrEnum):
    OFFICIAL = "official"
    LITURGICAL = "liturgical"
    SUPPRESSED = "suppressed"
    REVIVAL = "revival"
    PROTECTED = "protected"
    STANDARDISED = "standardised"


class ScriptFate(StrEnum):
    READABLE = "readable"
    UNWRITTEN = "unwritten"
