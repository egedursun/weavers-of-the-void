from enum import StrEnum


class RelationContext(StrEnum):
    BEFORE_UNION = "before_union"
    WITHIN_UNION = "within_union"
    OUTSIDE_UNION = "outside_union"
    BETWEEN_ANY_SEXES = "between_any_sexes"
    WITH_KIN = "with_kin"
    WITH_MADE_MINDS = "with_made_minds"
    WITH_OTHER_KINDS = "with_other_kinds"
    WITH_SPIRITS_OR_GODS = "with_spirits_or_gods"


class NormStance(StrEnum):
    FORBIDDEN = "forbidden"
    DISCOURAGED = "discouraged"
    TOLERATED = "tolerated"
    ACCEPTED = "accepted"
    HONOURED = "honoured"
    EXPECTED = "expected"


class NormEnforcer(StrEnum):
    KIN = "kin"
    FAITH = "faith"
    LAW = "law"
    NONE = "none"


class NormSanction(StrEnum):
    SHAMING = "shaming"
    FINE = "fine"
    SHUNNING = "shunning"
    EXILE = "exile"
    NONE = "none"


class KinScope(StrEnum):
    CLOSE = "close"
    EXTENDED = "extended"
    GROUP = "group"


class RestraintRole(StrEnum):
    CLERGY = "clergy"
    ASCETIC = "ascetic"
    WARRIOR = "warrior"
    RULER = "ruler"
    EVERYONE = "everyone"


class RestraintOccasion(StrEnum):
    ALWAYS = "always"
    BEFORE_BATTLE = "before_battle"
    SEASON = "season"
    RITE = "rite"


class RestraintVow(StrEnum):
    CELIBACY = "celibacy"
    FIDELITY = "fidelity"


class CycleCustom(StrEnum):
    SECLUSION = "seclusion"
    PURITY_RULES = "purity_rules"
    NONE = "none"


class BirthComplication(StrEnum):
    POSITION = "position"
    BLEEDING = "bleeding"
    FEVER = "fever"
    EARLY = "early"
    LATE = "late"
    MULTIPLE = "multiple"
    NONE = "none"
    STILLBIRTH = "stillbirth"
    BIRTH_INJURY = "birth_injury"


class PostnatalCustom(StrEnum):
    REST_PERIOD = "rest_period"
    SECLUSION = "seclusion"
    KIN_CARE = "kin_care"
    SPECIALIST_CARE = "specialist_care"
    RITE = "rite"
    NONE = "none"
    PARTNER_REST = "partner_rest"


class BirthAttendant(StrEnum):
    KIN = "kin"
    SPECIALIST = "specialist"
    HEALER = "healer"
    MADE_MIND = "made_mind"
    NONE = "none"


class BirthPlace(StrEnum):
    HOME = "home"
    BIRTH_HOUSE = "birth_house"
    SACRED_SITE = "sacred_site"
    APART = "apart"
    ANYWHERE = "anywhere"


class ParentUnion(StrEnum):
    WED = "wed"
    UNWED = "unwed"
    OUTSIDE_UNION = "outside_union"
    UNKNOWN = "unknown"


class ChildLegitimacy(StrEnum):
    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"


class LegitimacyPath(StrEnum):
    RECOGNITION = "recognition"
    ADOPTION = "adoption"
    PAYMENT = "payment"
    RITE = "rite"
    NONE = "none"
