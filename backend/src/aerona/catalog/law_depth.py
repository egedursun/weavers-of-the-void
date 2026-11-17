from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.law_depth import CourtLevel, JurisdictionClaim, KillMethod, LegalSystem, RecruitMotive, RegistryKind
from aerona.domain.enums.mortal import DeathCause
from aerona.domain.enums.polity import OfficeKind

SYSTEM_TEXT = total(
    LegalSystem,
    {
        LegalSystem.CUSTOMARY: "customary law kept by memory and sworn oaths",
        LegalSystem.CODIFIED: "a written code applied by judges",
        LegalSystem.RELIGIOUS: "sacred law judged by the clergy",
        LegalSystem.PRECEDENT: "case law built from earlier rulings",
        LegalSystem.ORACLE: "the answer of a god through a seer",
        LegalSystem.MIXED: "sacred law for faith and a written code for the rest",
    },
)
COURT_TEXT = total(
    CourtLevel,
    {
        CourtLevel.LOCAL: "the local court",
        CourtLevel.PROVINCIAL: "the provincial court",
        CourtLevel.HIGH: "the high court",
        CourtLevel.RELIGIOUS: "the court of the faith",
    },
)
COURT_OFFICES: MappingProxyType[CourtLevel, OfficeKind] = MappingProxyType({CourtLevel.PROVINCIAL: OfficeKind.GOVERNOR, CourtLevel.HIGH: OfficeKind.HIGH_JUDGE})
SECULAR_COURTS = (CourtLevel.LOCAL, CourtLevel.PROVINCIAL, CourtLevel.HIGH)
CLAIM_TEXT = total(
    JurisdictionClaim,
    {
        JurisdictionClaim.CLERGY: "the clergy's own courts over clergy and faith",
        JurisdictionClaim.GUILD: "the guild's own courts over guild matters",
        JurisdictionClaim.FOREIGN: "the right of its folk to be judged by their own realm",
    },
)
REGISTRY_TEXT = total(
    RegistryKind,
    {
        RegistryKind.LAND_TITLE: "title to land",
        RegistryKind.DEBT: "debt",
        RegistryKind.SALE: "sale",
        RegistryKind.UNION_PORTION: "portion given at a union",
        RegistryKind.INDENTURE: "indenture",
        RegistryKind.PATENT: "patent",
        RegistryKind.PATTERN: "registered pattern",
        RegistryKind.MIND_STATE: "registered state of a mind",
        RegistryKind.LINE: "registered living line",
        RegistryKind.COMPANY: "company charter",
        RegistryKind.BIRTH: "birth",
        RegistryKind.DEATH: "death",
        RegistryKind.CITIZENSHIP: "citizenship",
    },
)
PAID_IN_WORK = frozenset({RegistryKind.INDENTURE})
OWED = frozenset({RegistryKind.DEBT, RegistryKind.SALE, RegistryKind.UNION_PORTION, RegistryKind.INDENTURE})
MOTIVE_LOYALTY = total(
    RecruitMotive,
    {
        RecruitMotive.MONEY: "money_loyalty",
        RecruitMotive.IDEOLOGY: "ideology_loyalty",
        RecruitMotive.COMPROMISE: "compromise_loyalty",
        RecruitMotive.EGO: "ego_loyalty",
    },
)
MOTIVE_TEXT = total(
    RecruitMotive,
    {
        RecruitMotive.MONEY: "for money",
        RecruitMotive.IDEOLOGY: "for belief",
        RecruitMotive.COMPROMISE: "under a hook",
        RecruitMotive.EGO: "for pride or grievance",
    },
)
METHOD_STEALTH = total(
    KillMethod,
    {
        KillMethod.BLADE: "blade_stealth",
        KillMethod.POISON: "poison_stealth",
        KillMethod.ACCIDENT: "accident_stealth",
        KillMethod.DISEASE: "disease_stealth",
        KillMethod.CURSE: "curse_stealth",
    },
)
METHOD_HARM = total(
    KillMethod,
    {
        KillMethod.BLADE: HarmCause.BATTLE,
        KillMethod.POISON: HarmCause.POISON,
        KillMethod.ACCIDENT: HarmCause.ACCIDENT,
        KillMethod.DISEASE: HarmCause.EXPOSURE,
        KillMethod.CURSE: HarmCause.CURSE,
    },
)
METHOD_SEEMING = total(
    KillMethod,
    {
        KillMethod.BLADE: DeathCause.MURDER,
        KillMethod.POISON: DeathCause.UNKNOWN,
        KillMethod.ACCIDENT: DeathCause.ACCIDENT,
        KillMethod.DISEASE: DeathCause.DISEASE,
        KillMethod.CURSE: DeathCause.UNKNOWN,
    },
)
METHOD_TEXT = total(
    KillMethod,
    {
        KillMethod.BLADE: "by the blade",
        KillMethod.POISON: "by poison",
        KillMethod.ACCIDENT: "by a staged accident",
        KillMethod.DISEASE: "by a deliberate infection",
        KillMethod.CURSE: "by a curse",
    },
)
MEDICINE_TECHNIQUES = (Technique.HERBALISM, Technique.SURGERY)
CODE_TECHNIQUES = (Technique.CODIFIED_LAW, Technique.WRITTEN_LAW)
