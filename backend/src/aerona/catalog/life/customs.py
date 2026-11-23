from collections.abc import Mapping

from aerona.core.total import total
from aerona.domain.enums.affliction import PackageKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.customs import AgeGrade, CoopPurpose, Intoxicant, IntoxicantUse, MemberRight, Membership, Naturalisation
from aerona.domain.enums.daily_life import HouseDuty
from aerona.domain.enums.ecology import YieldProduct
from aerona.domain.enums.mortal import LifeStage

GRADES = (AgeGrade.CHILDREN, AgeGrade.YOUTHS, AgeGrade.YOUNG_ADULTS, AgeGrade.JUNIOR_ELDERS, AgeGrade.SENIOR_ELDERS)


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


PACKAGES: Mapping[Intoxicant, PackageKind] = total(
    Intoxicant,
    {
        Intoxicant.BREW: PackageKind.DRINK_DEPENDENCE,
        Intoxicant.WINE: PackageKind.DRINK_DEPENDENCE,
        Intoxicant.SPIRITS: PackageKind.DRINK_DEPENDENCE,
        Intoxicant.SMOKE: PackageKind.DRUG_DEPENDENCE,
        Intoxicant.LEAF: PackageKind.DRUG_DEPENDENCE,
        Intoxicant.FUNGUS: PackageKind.DRUG_DEPENDENCE,
        Intoxicant.ESSENCE: PackageKind.VIS_DEPENDENCE,
        Intoxicant.SYNTHETIC: PackageKind.DRUG_DEPENDENCE,
        Intoxicant.ANIMAL_DERIVED: PackageKind.DRUG_DEPENDENCE,
    },
)


SEEDED_STAGES = (LifeStage.CHILD, LifeStage.YOUTH, LifeStage.ADULT, LifeStage.ELDER)


STAGE_SHIFTS: dict[LifeStage, dict[str, int]] = {
    LifeStage.CHILD: {"learning": 20, "leisure": 15, "care": -3, "service": -2},
    LifeStage.YOUTH: {"learning": 10, "leisure": 5},
    LifeStage.ADULT: {},
    LifeStage.ELDER: {"rest": 15, "care": 5, "travel": -2},
}

KEEP_INTOXICATION_INTOXICANT_USES = frozenset({IntoxicantUse.DAILY, IntoxicantUse.FEAST})
KEEP_INTOXICATION_INTOXICANT_USES_2 = (IntoxicantUse.DAILY, IntoxicantUse.FORBIDDEN, IntoxicantUse.MEDICINE)
ANIMAL_INTOXICANT_SOURCES = frozenset({YieldProduct.VENOM, YieldProduct.SCENT, YieldProduct.ORGANS, YieldProduct.BLOOD})
MADE_INTOXICANT_TECHNIQUES = frozenset({Technique.INDUSTRIAL_CHEMISTRY, Technique.ALCHEMY})
SOURCED_INTOXICANTS = (Intoxicant.SYNTHETIC, Intoxicant.ANIMAL_DERIVED)
KEPT_HOUSE_DUTIES = (HouseDuty.SICKCARE, HouseDuty.HOUSEHOLD_RITES)
PURPOSE_FOR_COOP_PURPOSES = (CoopPurpose.INSURANCE, CoopPurpose.BURIAL, CoopPurpose.CREDIT, CoopPurpose.IRRIGATION)
