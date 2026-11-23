from types import MappingProxyType

from aerona.catalog.war_w52 import MOTIVES
from aerona.core.total import total
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.law_depth import CourtLevel, JurisdictionClaim, KillMethod, LegalSystem, RegistryKind
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
        CourtLevel.GUILD: "a trade court",
        CourtLevel.MILITARY: "a court of the armed forces",
        CourtLevel.CONSULAR: "a court of a foreign realm",
    },
)
COURT_BIAS = total(
    CourtLevel,
    {
        CourtLevel.LOCAL: "local_bias",
        CourtLevel.PROVINCIAL: "provincial_bias",
        CourtLevel.HIGH: "high_bias",
        CourtLevel.RELIGIOUS: "religious_bias",
        CourtLevel.GUILD: "guild_bias",
        CourtLevel.MILITARY: "military_bias",
        CourtLevel.CONSULAR: "consular_bias",
    },
)
COURT_OFFICES: MappingProxyType[CourtLevel, OfficeKind] = MappingProxyType({CourtLevel.PROVINCIAL: OfficeKind.GOVERNOR, CourtLevel.HIGH: OfficeKind.HIGH_JUDGE})
SECULAR_COURTS = (CourtLevel.LOCAL, CourtLevel.PROVINCIAL, CourtLevel.HIGH)
CLAIM_TEXT = total(
    JurisdictionClaim,
    {
        JurisdictionClaim.CLERGY: "the clergy's own courts over clergy and faith",
        JurisdictionClaim.GUILD: "a craft or trade association's own courts over the matters of its trade",
        JurisdictionClaim.FOREIGN: "the right of its folk to be judged by their own realm",
    },
)
REGISTRY_TEXT = total(
    RegistryKind,
    {
        RegistryKind.LAND_TITLE: "title to land",
        RegistryKind.DEBT: "debt",
        RegistryKind.SALE: "sale",
        RegistryKind.UNION_PAYMENT: "payment made at a union, to one family, from one family or in service",
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
OWED = frozenset({RegistryKind.DEBT, RegistryKind.SALE, RegistryKind.UNION_PAYMENT, RegistryKind.INDENTURE})
MOTIVE_LOYALTY = {motive: spec.loyalty_rule for motive, spec in MOTIVES.items()}
MOTIVE_TEXT = {motive: spec.text for motive, spec in MOTIVES.items()}
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
