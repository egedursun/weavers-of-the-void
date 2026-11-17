from enum import StrEnum


class UnionForm(StrEnum):
    PAIR = "pair"
    PLURAL = "plural"
    GROUP = "group"
    SERIAL = "serial"
    CONTRACT = "contract"
    POSTHUMOUS = "posthumous"
    NONE = "none"


class UnionPurpose(StrEnum):
    KINSHIP = "kinship"
    ALLIANCE = "alliance"
    INHERITANCE = "inheritance"
    LOVE = "love"
    FAITH = "faith"
    LABOUR = "labour"
    STATUS = "status"


class UnionResidence(StrEnum):
    WITH_FIRST_FAMILY = "with_first_family"
    WITH_SECOND_FAMILY = "with_second_family"
    NEW_HOUSEHOLD = "new_household"
    SEPARATE = "separate"


class UnionDescent(StrEnum):
    THROUGH_FIRST = "through_first"
    THROUGH_SECOND = "through_second"
    THROUGH_BOTH = "through_both"
    CHOSEN = "chosen"
    BY_HOUSE_RULE = "by_house_rule"


class UnionExchange(StrEnum):
    TO_ONE_FAMILY = "to_one_family"
    FROM_ONE_FAMILY = "from_one_family"
    MUTUAL = "mutual"
    SERVICE = "service"
    NONE = "none"


class UnionArrangement(StrEnum):
    ARRANGED = "arranged"
    CHOSEN = "chosen"
    BOTH_CONSENT = "both_consent"


class UnionDissolution(StrEnum):
    NONE = "none"
    BY_EITHER = "by_either"
    BY_COURT = "by_court"
    BY_CUSTOM = "by_custom"


class PartnerScope(StrEnum):
    NONE = "none"
    PEOPLE = "people"
    CLASS = "class"
    CASTE = "caste"
    FAITH = "faith"
    HOUSE = "house"
    LINE = "line"
    MOIETY = "moiety"


class PluralSide(StrEnum):
    FIRST = "first"
    SECOND = "second"
    EITHER = "either"


class KinMatch(StrEnum):
    NONE = "none"
    CROSS_COUSIN = "cross_cousin"
    PARALLEL_COUSIN = "parallel_cousin"
