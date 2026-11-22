from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.enums.youth import YouthPurpose

TOWN_EFFECTS: dict[YouthPurpose, tuple[str, int]] = {
    YouthPurpose.DEFENCE: ("crime", -1),
    YouthPurpose.SERVICE: ("public_order", 1),
    YouthPurpose.POLITICS: ("unrest", 1),
    YouthPurpose.MISCHIEF: ("crime", 1),
    YouthPurpose.CRIME: ("crime", 1),
}


MEMBER_AXES: dict[YouthPurpose, ValueAxis] = {
    YouthPurpose.SPORT: ValueAxis.COMPETITION,
    YouthPurpose.COURTSHIP: ValueAxis.FRIENDSHIP,
    YouthPurpose.FAITH: ValueAxis.PIETY,
    YouthPurpose.DEFENCE: ValueAxis.MARTIAL,
    YouthPurpose.SERVICE: ValueAxis.LOYALTY,
}


PURPOSE_AXES: dict[ValueAxis, YouthPurpose] = {
    ValueAxis.MARTIAL: YouthPurpose.DEFENCE,
    ValueAxis.PIETY: YouthPurpose.FAITH,
    ValueAxis.COMPETITION: YouthPurpose.SPORT,
    ValueAxis.FRIENDSHIP: YouthPurpose.COURTSHIP,
    ValueAxis.LOYALTY: YouthPurpose.SERVICE,
}

YOUTHS_WITHOUT_GROUP_LIFE_STAGES = (LifeStage.CHILD, LifeStage.YOUTH, LifeStage.ADULT)
