from collections.abc import Mapping

from aerona.core.total import total
from aerona.domain.enums.affliction import PackageKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.customs import AgeGrade, CoopPurpose, Intoxicant, IntoxicantUse, MarkMeaning, MemberRight, Membership, Naturalisation, RevivalGoal
from aerona.domain.enums.mortal import LifeStage

GRADES = (AgeGrade.CHILDREN, AgeGrade.YOUTHS, AgeGrade.WARRIORS, AgeGrade.JUNIOR_ELDERS, AgeGrade.SENIOR_ELDERS)


RIGHTS: Mapping[Membership, tuple[MemberRight, ...]] = {
    Membership.CITIZEN: tuple(MemberRight),
    Membership.SUBJECT: (MemberRight.MARRIAGE, MemberRight.COURTS, MemberRight.ARMS),
    Membership.RESIDENT_FOREIGNER: (MemberRight.MARRIAGE, MemberRight.COURTS),
    Membership.PROTECTED_MINORITY: (MemberRight.MARRIAGE, MemberRight.COURTS),
    Membership.BOUND: (),
}


PATH_WAIT: Mapping[Naturalisation, int] = total(
    Naturalisation,
    {
        Naturalisation.DESCENT: 0,
        Naturalisation.BIRTHPLACE: 0,
        Naturalisation.RESIDENCE: 100,
        Naturalisation.CONVERSION: 50,
        Naturalisation.SERVICE: 50,
        Naturalisation.PURCHASE: 0,
        Naturalisation.GRANT: 0,
    },
)


PACKAGES: Mapping[Intoxicant, PackageKind] = {
    Intoxicant.BREW: PackageKind.DRINK_DEPENDENCE,
    Intoxicant.WINE: PackageKind.DRINK_DEPENDENCE,
    Intoxicant.SPIRITS: PackageKind.DRINK_DEPENDENCE,
    Intoxicant.SMOKE: PackageKind.DRUG_DEPENDENCE,
    Intoxicant.LEAF: PackageKind.DRUG_DEPENDENCE,
    Intoxicant.FUNGUS: PackageKind.DRUG_DEPENDENCE,
    Intoxicant.ESSENCE: PackageKind.VIS_DEPENDENCE,
}


EVENT_BONDS: Mapping[MarkMeaning, BondKind] = {
    MarkMeaning.DEED: BondKind.KILLED,
    MarkMeaning.MARRIAGE: BondKind.SPOUSE_OF,
    MarkMeaning.STATUS: BondKind.RULES,
}


RESTORING = (RevivalGoal.REVIVE_LANGUAGE, RevivalGoal.RESTORE_GOD, RevivalGoal.EXPEL_FOREIGNERS)


SEEDED_STAGES = (LifeStage.CHILD, LifeStage.YOUTH, LifeStage.ADULT, LifeStage.ELDER)


STAGE_SHIFTS: dict[LifeStage, dict[str, int]] = {
    LifeStage.CHILD: {"learning": 20, "leisure": 15, "care": -3, "service": -2},
    LifeStage.YOUTH: {"learning": 10, "leisure": 5},
    LifeStage.ADULT: {},
    LifeStage.ELDER: {"rest": 15, "care": 5, "travel": -2},
}

KEEP_INTOXICATION_INTOXICANT_USES = frozenset({IntoxicantUse.DAILY, IntoxicantUse.FEAST})
KEEP_INTOXICATION_INTOXICANT_USES_2 = (IntoxicantUse.DAILY, IntoxicantUse.FORBIDDEN)
READ_MARK_MARK_MEANINGS = (MarkMeaning.DEED, MarkMeaning.STATUS)
READ_MARK_MARK_MEANINGS_2 = (MarkMeaning.CLAN, MarkMeaning.MARRIAGE, MarkMeaning.AGE_SET)
CALM_MARKED_MARK_MEANINGS = (MarkMeaning.PROTECTION, MarkMeaning.MOURNING)
PURPOSE_FOR_COOP_PURPOSES = (CoopPurpose.INSURANCE, CoopPurpose.BURIAL, CoopPurpose.CREDIT, CoopPurpose.IRRIGATION)
