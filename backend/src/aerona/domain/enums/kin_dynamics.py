from enum import StrEnum


class RivalryCause(StrEnum):
    INHERITANCE = "inheritance"
    FAVOUR = "favour"
    OFFICE = "office"
    LOVE = "love"
    STANDING = "standing"


class DisownReason(StrEnum):
    DISOBEDIENCE = "disobedience"
    MARRIAGE = "marriage"
    FAITH = "faith"
    CRIME = "crime"
    RIVALRY = "rivalry"


class KinStir(StrEnum):
    FAVOUR = "favour"
    RIVALRY = "rivalry"
    RECONCILE = "reconcile"
    ELDER = "elder"
