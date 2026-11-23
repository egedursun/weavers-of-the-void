from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.affliction import PackageKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.customs import AgeGrade, CoopPurpose, EvidenceKind, Intoxicant, IntoxicantUse, MemberRight, Membership, Naturalisation
from aerona.domain.enums.daily_life import HouseDuty
from aerona.domain.enums.ecology import YieldProduct
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.mortal import LifeStage

GRADES = (AgeGrade.CHILDREN, AgeGrade.YOUTHS, AgeGrade.YOUNG_ADULTS, AgeGrade.JUNIOR_ELDERS, AgeGrade.SENIOR_ELDERS)


RIGHTS: Mapping[Membership, tuple[MemberRight, ...]] = {
    Membership.CITIZEN: tuple(MemberRight),
    Membership.SUBJECT: (MemberRight.MARRIAGE, MemberRight.COURTS, MemberRight.ARMS, MemberRight.PROPERTY, MemberRight.MOVEMENT, MemberRight.WORSHIP),
    Membership.RESIDENT_FOREIGNER: (MemberRight.MARRIAGE, MemberRight.COURTS, MemberRight.PROPERTY, MemberRight.MOVEMENT),
    Membership.PROTECTED_MINORITY: (MemberRight.MARRIAGE, MemberRight.COURTS, MemberRight.PROPERTY, MemberRight.WORSHIP),
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
        Naturalisation.UNION: 25,
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


RIGHT_GRIEVANCE: Mapping[MemberRight, str] = total(
    MemberRight,
    {
        MemberRight.OFFICE: "office_grievance",
        MemberRight.MARRIAGE: "marriage_grievance",
        MemberRight.ARMS: "arms_grievance",
        MemberRight.COURTS: "courts_grievance",
        MemberRight.PROPERTY: "property_grievance",
        MemberRight.MOVEMENT: "movement_grievance",
        MemberRight.VOTE: "vote_grievance",
        MemberRight.WORSHIP: "worship_grievance",
    },
)


@dataclass(frozen=True)
class EvidenceSpec:
    weight: str
    decay: str
    hearsay: bool = False


EVIDENCE: Mapping[EvidenceKind, EvidenceSpec] = total(
    EvidenceKind,
    {
        EvidenceKind.WITNESS: EvidenceSpec("witness_weight", "witness_decay"),
        EvidenceKind.TRACE: EvidenceSpec("trace_weight", "trace_decay"),
        EvidenceKind.DOCUMENT: EvidenceSpec("document_weight", "document_decay"),
        EvidenceKind.CONFESSION: EvidenceSpec("confession_weight", "confession_decay"),
        EvidenceKind.DIVINATION: EvidenceSpec("divination_weight", "divination_decay"),
        EvidenceKind.MAGIC: EvidenceSpec("magic_weight", "magic_decay"),
        EvidenceKind.EXPERT: EvidenceSpec("expert_weight", "expert_decay"),
        EvidenceKind.HEARSAY: EvidenceSpec("hearsay_weight", "hearsay_decay", hearsay=True),
    },
)


COOP_GAINS: Mapping[CoopPurpose, str] = total(
    CoopPurpose,
    {
        CoopPurpose.MILL: "mill_gain",
        CoopPurpose.BOATS: "boats_gain",
        CoopPurpose.IRRIGATION: "irrigation_gain",
        CoopPurpose.INSURANCE: "insurance_gain",
        CoopPurpose.BURIAL: "burial_gain",
        CoopPurpose.CREDIT: "credit_gain",
        CoopPurpose.GRANARY: "granary_gain",
        CoopPurpose.HERDING: "herding_gain",
    },
)

EXPERT_SKILLS = (SkillKind.MEDICINE, SkillKind.LAW, SkillKind.ALCHEMY)
