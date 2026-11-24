from collections.abc import Mapping
from types import MappingProxyType

from aerona.core.total import partial, total
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.intrigue import IntrigueSecret
from aerona.domain.enums.mind import HonourModel, SkillKind, ValueAxis
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.polity import (
    ClaimBasis,
    ClauseKind,
    LawArea,
    LawKind,
    OathKind,
    OathPenalty,
    OfficeKind,
    OfficePower,
    SuccessionRule,
    TreatyKind,
    TreatyStatus,
)
from aerona.domain.enums.regime import ClientRole
from aerona.domain.enums.statecraft import CouncilTask, CourtPosition, CrisisDemand, TaxKind
from aerona.domain.enums.titles import TitleTier
from aerona.domain.enums.war import WarCause

TREATY_WORDS = MappingProxyType(
    {
        TreatyKind.PEACE: "the Peace",
        TreatyKind.TRUCE: "the Truce",
        TreatyKind.ALLIANCE_DEFENSIVE: "the Alliance",
        TreatyKind.ALLIANCE_OFFENSIVE: "the War Pact",
        TreatyKind.NON_AGGRESSION: "the Pact of Restraint",
        TreatyKind.VASSALAGE: "the Oath of Vassalage",
        TreatyKind.TRIBUTE: "the Tribute",
        TreatyKind.MARRIAGE_PACT: "the Marriage Pact",
        TreatyKind.TRADE_PACT: "the Trade Pact",
        TreatyKind.CONDOTTA: "the Condotta",
        TreatyKind.GUARANTEE: "the Guarantee",
        TreatyKind.INTERWORLD: "the Treaty of the Worlds",
        TreatyKind.COALITION: "the Coalition",
        TreatyKind.DIVINE_PACT: "the Divine Pact",
        TreatyKind.NAVAL_LIMIT: "the Naval Treaty",
        TreatyKind.ARMS_LIMIT: "the Arms Treaty",
        TreatyKind.MUTUAL_AID: "the Pact of Mutual Aid",
        TreatyKind.BORDER_ACCORD: "the Border Accord",
    }
)


DEFAULT_CLAUSES = MappingProxyType(
    {
        TreatyKind.ALLIANCE_DEFENSIVE: (ClauseKind.CALL_TO_ARMS,),
        TreatyKind.ALLIANCE_OFFENSIVE: (ClauseKind.CALL_TO_ARMS,),
        TreatyKind.NON_AGGRESSION: (ClauseKind.NON_AGGRESSION,),
        TreatyKind.PEACE: (ClauseKind.NON_AGGRESSION,),
        TreatyKind.TRUCE: (ClauseKind.NON_AGGRESSION,),
        TreatyKind.VASSALAGE: (ClauseKind.TRIBUTE, ClauseKind.CALL_TO_ARMS),
        TreatyKind.TRIBUTE: (ClauseKind.TRIBUTE,),
        TreatyKind.TRADE_PACT: (ClauseKind.TRADE_RIGHTS, ClauseKind.TOLLS_WAIVED),
        TreatyKind.MARRIAGE_PACT: (ClauseKind.MARRIAGE,),
        TreatyKind.INTERWORLD: (ClauseKind.TRADE_RIGHTS, ClauseKind.NON_AGGRESSION),
        TreatyKind.GUARANTEE: (ClauseKind.NON_AGGRESSION,),
        TreatyKind.CONDOTTA: (ClauseKind.CALL_TO_ARMS,),
        TreatyKind.COALITION: (ClauseKind.CALL_TO_ARMS,),
        TreatyKind.DIVINE_PACT: (ClauseKind.NON_AGGRESSION,),
        TreatyKind.NAVAL_LIMIT: (ClauseKind.FLEET_LIMIT,),
        TreatyKind.ARMS_LIMIT: (ClauseKind.MASS_WEAPON_LIMIT,),
        TreatyKind.MUTUAL_AID: (ClauseKind.SHARED_WATER,),
        TreatyKind.BORDER_ACCORD: (ClauseKind.RETURN_OF_REFUGEES, ClauseKind.CAPTIVE_EXCHANGE),
    }
)


DERIVED = MappingProxyType(
    {
        TreatyKind.ALLIANCE_DEFENSIVE: BondKind.ALLY,
        TreatyKind.ALLIANCE_OFFENSIVE: BondKind.ALLY,
        TreatyKind.MARRIAGE_PACT: BondKind.ALLY,
        TreatyKind.TRUCE: BondKind.TRUCE,
        TreatyKind.PEACE: BondKind.TRUCE,
        TreatyKind.VASSALAGE: BondKind.PAYS_TRIBUTE,
        TreatyKind.TRIBUTE: BondKind.PAYS_TRIBUTE,
        TreatyKind.TRADE_PACT: BondKind.TRADES_WITH,
        TreatyKind.INTERWORLD: BondKind.TRADES_WITH,
        TreatyKind.COALITION: BondKind.ALLY,
    }
)


TASKS: dict[OfficeKind, CouncilTask] = {
    OfficeKind.CHANCELLOR: CouncilTask.IMPROVE_RELATIONS,
    OfficeKind.MARSHAL: CouncilTask.TRAIN_TROOPS,
    OfficeKind.TREASURER: CouncilTask.COLLECT_TAXES,
    OfficeKind.SPYMASTER: CouncilTask.DISRUPT_SCHEMES,
    OfficeKind.CHAPLAIN: CouncilTask.CONVERT_PROVINCE,
    OfficeKind.HIGH_JUDGE: CouncilTask.PURGE_CORRUPTION,
    OfficeKind.HEAD_OF_GOVERNMENT: CouncilTask.IMPROVE_RELATIONS,
    OfficeKind.MINISTER: CouncilTask.COLLECT_TAXES,
    OfficeKind.GENERAL: CouncilTask.TRAIN_TROOPS,
    OfficeKind.ADMIRAL: CouncilTask.TRAIN_TROOPS,
    OfficeKind.SPEAKER: CouncilTask.PURGE_CORRUPTION,
    OfficeKind.GOVERNOR: CouncilTask.OVERSEE_WORKS,
    OfficeKind.AMBASSADOR: CouncilTask.PROMOTE_TRADE,
    OfficeKind.COURT_SCHOLAR: CouncilTask.ADVANCE_LEARNING,
    OfficeKind.CHIEF_SCIENTIST: CouncilTask.ADVANCE_LEARNING,
    OfficeKind.CENSOR: CouncilTask.COLLECT_TAXES,
    OfficeKind.WARDEN: CouncilTask.SECURE_BORDERS,
}


POSITION_STATS: dict[CourtPosition, str] = {
    CourtPosition.STEWARD: "intellect",
    CourtPosition.CHAMPION: "strength",
    CourtPosition.PHYSICIAN: "wisdom",
    CourtPosition.TUTOR: "intellect",
    CourtPosition.CHRONICLER: "creativity",
    CourtPosition.MASTER_OF_REVELS: "charisma",
    CourtPosition.JESTER: "creativity",
    CourtPosition.SEER: "wisdom",
    CourtPosition.TASTER: "wisdom",
    CourtPosition.INTERPRETER: "intellect",
}


CRISIS_CAUSES: dict[WarCause, CrisisDemand] = {
    WarCause.CLAIM: CrisisDemand.CEDE_REGION,
    WarCause.HOLY_WAR: CrisisDemand.CONVERT,
    WarCause.DEBT: CrisisDemand.PAY,
    WarCause.TRADE_ROUTE: CrisisDemand.OPEN_TRADE,
    WarCause.ESPIONAGE: CrisisDemand.HAND_OVER,
    WarCause.VENDETTA: CrisisDemand.HAND_OVER,
    WarCause.RIVALRY: CrisisDemand.DISARM,
    WarCause.GRUDGE: CrisisDemand.APOLOGY,
    WarCause.RAID: CrisisDemand.RELEASE_CAPTIVES,
}


AREA_LOBBIES: Mapping[LawArea, frozenset[FactionKind]] = total(
    LawArea,
    {
        LawArea.SUCCESSION: frozenset({FactionKind.NOBLE_COUNCIL, FactionKind.ESTATE, FactionKind.PARTY}),
        LawArea.PROPERTY: frozenset({FactionKind.NOBLE_COUNCIL, FactionKind.PEASANT_LEAGUE, FactionKind.MERCHANT_GUILD, FactionKind.CHARTERED_COMPANY}),
        LawArea.FISCAL: frozenset(
            {FactionKind.MERCHANT_GUILD, FactionKind.FINANCIERS, FactionKind.CRAFT_GUILD, FactionKind.PEASANT_LEAGUE, FactionKind.SMUGGLING_RING}
        ),
        LawArea.PENAL: frozenset({FactionKind.CRIME_FAMILY, FactionKind.THIEVES_GUILD, FactionKind.ASSASSINS, FactionKind.BANDITS}),
        LawArea.MILITARY: frozenset({FactionKind.WARRIOR_ORDER, FactionKind.MERCENARY_COMPANY, FactionKind.VETERANS}),
        LawArea.SOCIAL: frozenset({FactionKind.PRIESTHOOD, FactionKind.HOLY_ORDER, FactionKind.MOVEMENT, FactionKind.WORKERS_UNION, FactionKind.SOCIAL_CIRCLE}),
        LawArea.PUBLIC_HEALTH: frozenset({FactionKind.SCHOLARS_ACADEMY, FactionKind.ENGINEERS_SOCIETY, FactionKind.WORKERS_UNION}),
        LawArea.MAGIC: frozenset({FactionKind.MAGE_ORDER, FactionKind.SECRET_SOCIETY, FactionKind.PRIESTHOOD}),
        LawArea.CONSTITUTIONAL: frozenset({FactionKind.PARTY, FactionKind.MOVEMENT, FactionKind.REBELS, FactionKind.NOBLE_COUNCIL}),
        LawArea.COMMERCE: frozenset({FactionKind.MERCHANT_GUILD, FactionKind.CRAFT_GUILD, FactionKind.FINANCIERS, FactionKind.CHARTERED_COMPANY}),
        LawArea.FAITH: frozenset({FactionKind.PRIESTHOOD, FactionKind.HOLY_ORDER, FactionKind.MOVEMENT}),
        LawArea.LABOUR: frozenset({FactionKind.WORKERS_UNION, FactionKind.PEASANT_LEAGUE, FactionKind.CRAFT_GUILD}),
        LawArea.FAMILY: frozenset({FactionKind.ESTATE, FactionKind.PRIESTHOOD, FactionKind.MOVEMENT}),
        LawArea.ENVIRONMENT: frozenset({FactionKind.PEASANT_LEAGUE, FactionKind.MOVEMENT, FactionKind.CHARTERED_COMPANY}),
    },
)


AREA_ORDER: Mapping[LawArea, int] = total(
    LawArea,
    {
        LawArea.SUCCESSION: 80,
        LawArea.PROPERTY: 100,
        LawArea.FISCAL: 110,
        LawArea.PENAL: 130,
        LawArea.MILITARY: 120,
        LawArea.SOCIAL: 80,
        LawArea.PUBLIC_HEALTH: 90,
        LawArea.MAGIC: 100,
        LawArea.CONSTITUTIONAL: 70,
        LawArea.COMMERCE: 100,
        LawArea.FAITH: 90,
        LawArea.LABOUR: 100,
        LawArea.FAMILY: 90,
        LawArea.ENVIRONMENT: 100,
    },
)


KIND_VALUES: Mapping[LawKind, Mapping[ValueAxis, int]] = {
    LawKind.SLAVERY: {ValueAxis.MERCY: -1, ValueAxis.HIERARCHY: 1},
    LawKind.PENAL_CODE: {ValueAxis.MERCY: -1, ValueAxis.TRADITION: 1},
    LawKind.CONSCRIPTION: {ValueAxis.MARTIAL: 1},
    LawKind.CENSORSHIP: {ValueAxis.HIERARCHY: 1, ValueAxis.TRUTH: -1, ValueAxis.KNOWLEDGE: -1},
    LawKind.RELIGIOUS_TOLERANCE: {ValueAxis.XENOPHILIA: 1, ValueAxis.PIETY: -1},
    LawKind.FOREIGNER_RIGHTS: {ValueAxis.XENOPHILIA: 1},
    LawKind.SUMPTUARY: {ValueAxis.HIERARCHY: 1, ValueAxis.WEALTH: -1},
    LawKind.MAGIC_BAN: {ValueAxis.SUPERSTITION: 1, ValueAxis.KNOWLEDGE: -1},
    LawKind.TAX_RATE: {ValueAxis.WEALTH: -1},
    LawKind.BLOOD_FEUD: {ValueAxis.HONOUR: 1, ValueAxis.KINSHIP: 1},
    LawKind.FRANCHISE: {ValueAxis.HIERARCHY: -1},
    LawKind.LABOUR_LAW: {ValueAxis.MERCY: 1, ValueAxis.WEALTH: -1},
    LawKind.ENVIRONMENT_LAW: {ValueAxis.NATURE: 1, ValueAxis.WEALTH: -1},
    LawKind.DATA_PRIVACY: {ValueAxis.HIERARCHY: -1},
    LawKind.WEAPONS_LAW: {ValueAxis.MARTIAL: -1, ValueAxis.LAW: 1},
    LawKind.INTELLECTUAL_PROPERTY: {ValueAxis.WEALTH: 1, ValueAxis.KNOWLEDGE: -1},
    LawKind.MACHINE_LAW: {ValueAxis.TRADITION: 1, ValueAxis.KNOWLEDGE: -1},
    LawKind.SPACE_LAW: {ValueAxis.XENOPHILIA: 1},
    LawKind.MIND_STATUS: {ValueAxis.MERCY: 1, ValueAxis.TRADITION: -1},
    LawKind.COPY_LAW: {ValueAxis.TRADITION: 1, ValueAxis.FAMILY: 1},
    LawKind.COPY_SUCCESSION: {ValueAxis.LAW: 1},
    LawKind.ERASURE_LAW: {ValueAxis.MERCY: 1},
    LawKind.AUGMENT_LAW: {ValueAxis.TRADITION: 1, ValueAxis.PURITY: 1},
    LawKind.NETWORK_LAW: {ValueAxis.HIERARCHY: 1},
    LawKind.SURVEILLANCE_LAW: {ValueAxis.LAW: 1, ValueAxis.HIERARCHY: 1},
    LawKind.COMPETITION_LAW: {ValueAxis.LAW: 1, ValueAxis.WEALTH: -1},
    LawKind.PROVISION_LAW: {ValueAxis.MERCY: 1, ValueAxis.WEALTH: -1},
    LawKind.POWER_LAW: {ValueAxis.LAW: 1, ValueAxis.HIERARCHY: 1},
    LawKind.SOURCE_LAW: {ValueAxis.TRADITION: 1, ValueAxis.PIETY: 1},
    LawKind.LIVING_CRAFT_LAW: {ValueAxis.PURITY: 1, ValueAxis.TRADITION: 1},
    LawKind.CLONE_LAW: {ValueAxis.TRADITION: 1, ValueAxis.FAMILY: 1},
    LawKind.CLONE_STATUS: {ValueAxis.MERCY: 1, ValueAxis.TRADITION: -1},
    LawKind.GERMLINE_LAW: {ValueAxis.PURITY: 1, ValueAxis.FAMILY: 1},
    LawKind.DESIGNED_STATUS: {ValueAxis.MERCY: 1, ValueAxis.HIERARCHY: -1},
}


MODEL_PENALTIES: Mapping[HonourModel, OathPenalty | None] = total(
    HonourModel,
    {
        HonourModel.DIGNITY: OathPenalty.FINE,
        HonourModel.HONOUR: OathPenalty.SHAME,
        HonourModel.FACE: OathPenalty.SHAME,
        HonourModel.NONE: None,
        HonourModel.PURITY: OathPenalty.SHAME,
    },
)


OFFICE_SKILLS = partial(
    OfficeKind,
    {
        OfficeKind.CHANCELLOR: ((SkillKind.NEGOTIATION, SkillKind.ETIQUETTE, SkillKind.ORATORY), "charisma"),
        OfficeKind.MARSHAL: ((SkillKind.TACTICS, SkillKind.STRATEGY, SkillKind.LEADERSHIP), "strength"),
        OfficeKind.TREASURER: ((SkillKind.ACCOUNTING, SkillKind.WRITING), "intellect"),
        OfficeKind.HIGH_JUDGE: ((SkillKind.LAW, SkillKind.LORE), "intellect"),
        OfficeKind.SPYMASTER: ((SkillKind.INTRIGUE, SkillKind.DECEPTION), "agility"),
        OfficeKind.GOVERNOR: ((SkillKind.LEADERSHIP, SkillKind.LAW, SkillKind.LOGISTICS), "charisma"),
        OfficeKind.AMBASSADOR: ((SkillKind.NEGOTIATION, SkillKind.LANGUAGES, SkillKind.ETIQUETTE), "charisma"),
        OfficeKind.HERALD: ((SkillKind.ORATORY, SkillKind.ETIQUETTE), "charisma"),
        OfficeKind.CHAPLAIN: ((SkillKind.THEOLOGY, SkillKind.ORATORY), "wisdom"),
        OfficeKind.REGENT: ((SkillKind.LEADERSHIP, SkillKind.LAW), "charisma"),
        OfficeKind.COURT_SCHOLAR: ((SkillKind.LORE, SkillKind.WRITING, SkillKind.ASTRONOMY), "intellect"),
        OfficeKind.HEAD_OF_STATE: ((SkillKind.LEADERSHIP, SkillKind.ORATORY, SkillKind.ETIQUETTE), "charisma"),
        OfficeKind.HEAD_OF_GOVERNMENT: ((SkillKind.ADMINISTRATION, SkillKind.LEADERSHIP, SkillKind.NEGOTIATION), "intellect"),
        OfficeKind.MINISTER: ((SkillKind.ADMINISTRATION, SkillKind.LAW, SkillKind.ACCOUNTING), "intellect"),
        OfficeKind.GENERAL: ((SkillKind.STRATEGY, SkillKind.TACTICS, SkillKind.LOGISTICS), "strength"),
        OfficeKind.ADMIRAL: ((SkillKind.NAVAL_COMBAT, SkillKind.NAVIGATION, SkillKind.STRATEGY), "wisdom"),
        OfficeKind.SPEAKER: ((SkillKind.ORATORY, SkillKind.LAW, SkillKind.NEGOTIATION), "charisma"),
        OfficeKind.CHIEF_SCIENTIST: ((SkillKind.SCIENCE, SkillKind.COMPUTING, SkillKind.ENGINEERING), "intellect"),
        OfficeKind.JESTER: ((SkillKind.ORATORY, SkillKind.DECEPTION, SkillKind.ETIQUETTE), "charisma"),
        OfficeKind.WARDEN: ((SkillKind.HUNTING, SkillKind.TRACKING, SkillKind.LAW), "wisdom"),
        OfficeKind.CENSOR: ((SkillKind.LAW, SkillKind.ETIQUETTE, SkillKind.ORATORY), "intellect"),
    },
    without={OfficeKind.HEIR_DESIGNATE, OfficeKind.RULER},
)


COUNCIL = (
    OfficeKind.CHANCELLOR,
    OfficeKind.MARSHAL,
    OfficeKind.TREASURER,
    OfficeKind.HIGH_JUDGE,
    OfficeKind.SPYMASTER,
    OfficeKind.HERALD,
    OfficeKind.CHAPLAIN,
    OfficeKind.COURT_SCHOLAR,
    OfficeKind.HEAD_OF_STATE,
    OfficeKind.HEAD_OF_GOVERNMENT,
    OfficeKind.MINISTER,
    OfficeKind.GENERAL,
    OfficeKind.ADMIRAL,
    OfficeKind.SPEAKER,
    OfficeKind.CHIEF_SCIENTIST,
    OfficeKind.CENSOR,
)


DEFAULT_POWERS: Mapping[OfficeKind, tuple[OfficePower, ...]] = MappingProxyType(
    {
        OfficeKind.RULER: (OfficePower.RULE,),
        OfficeKind.HEIR_DESIGNATE: (OfficePower.SUCCEED,),
        OfficeKind.REGENT: (OfficePower.RULE,),
        OfficeKind.CHANCELLOR: (OfficePower.NEGOTIATE,),
        OfficeKind.MARSHAL: (OfficePower.COMMAND,),
        OfficeKind.TREASURER: (OfficePower.TREASURY,),
        OfficeKind.HIGH_JUDGE: (OfficePower.JUDGE,),
        OfficeKind.SPYMASTER: (OfficePower.SPY,),
        OfficeKind.GOVERNOR: (OfficePower.GOVERN,),
        OfficeKind.AMBASSADOR: (OfficePower.EMBASSY,),
        OfficeKind.HERALD: (OfficePower.PROCLAIM,),
        OfficeKind.CHAPLAIN: (OfficePower.PREACH,),
        OfficeKind.COURT_SCHOLAR: (OfficePower.RESEARCH,),
        OfficeKind.HEAD_OF_STATE: (OfficePower.PROCLAIM,),
        OfficeKind.HEAD_OF_GOVERNMENT: (OfficePower.GOVERN, OfficePower.NEGOTIATE),
        OfficeKind.MINISTER: (OfficePower.TREASURY,),
        OfficeKind.GENERAL: (OfficePower.COMMAND,),
        OfficeKind.ADMIRAL: (OfficePower.COMMAND,),
        OfficeKind.SPEAKER: (OfficePower.PROCLAIM,),
        OfficeKind.CHIEF_SCIENTIST: (OfficePower.RESEARCH,),
        OfficeKind.JESTER: (OfficePower.JEST,),
        OfficeKind.WARDEN: (OfficePower.JUDGE,),
        OfficeKind.CENSOR: (OfficePower.CENSUS,),
    }
)


POWER_SKILLS: Mapping[OfficePower, OfficeKind] = MappingProxyType(
    {
        OfficePower.RULE: OfficeKind.REGENT,
        OfficePower.SUCCEED: OfficeKind.REGENT,
        OfficePower.NEGOTIATE: OfficeKind.CHANCELLOR,
        OfficePower.COMMAND: OfficeKind.MARSHAL,
        OfficePower.TREASURY: OfficeKind.TREASURER,
        OfficePower.JUDGE: OfficeKind.HIGH_JUDGE,
        OfficePower.SPY: OfficeKind.SPYMASTER,
        OfficePower.GOVERN: OfficeKind.GOVERNOR,
        OfficePower.EMBASSY: OfficeKind.AMBASSADOR,
        OfficePower.PROCLAIM: OfficeKind.HERALD,
        OfficePower.PREACH: OfficeKind.CHAPLAIN,
        OfficePower.RESEARCH: OfficeKind.COURT_SCHOLAR,
        OfficePower.JEST: OfficeKind.JESTER,
        OfficePower.CENSUS: OfficeKind.CENSOR,
    }
)


ENVOYS = (OfficeKind.CHANCELLOR, OfficeKind.AMBASSADOR)


RANK_ORDER = (TitleTier.LOCAL, TitleTier.DISTRICT, TitleTier.REGIONAL, TitleTier.REALM, TitleTier.IMPERIAL)


AREA_SECRETS: Mapping[LawArea, frozenset[IntrigueSecret]] = total(
    LawArea,
    {
        LawArea.SUCCESSION: frozenset({IntrigueSecret.TRUE_PARENTAGE, IntrigueSecret.CRIME}),
        LawArea.PROPERTY: frozenset({IntrigueSecret.CRIME, IntrigueSecret.DEBT}),
        LawArea.FISCAL: frozenset({IntrigueSecret.CRIME, IntrigueSecret.DEBT}),
        LawArea.PENAL: frozenset({IntrigueSecret.CRIME}),
        LawArea.MILITARY: frozenset({IntrigueSecret.COWARDICE_IN_BATTLE, IntrigueSecret.BROKEN_OATH}),
        LawArea.SOCIAL: frozenset({IntrigueSecret.CRIME, IntrigueSecret.AFFAIR}),
        LawArea.PUBLIC_HEALTH: frozenset({IntrigueSecret.HIDDEN_CONDITION, IntrigueSecret.CRIME}),
        LawArea.MAGIC: frozenset({IntrigueSecret.DEAL_WITH_OUTER_BEING, IntrigueSecret.SECRET_CULT_MEMBERSHIP}),
        LawArea.CONSTITUTIONAL: frozenset({IntrigueSecret.CRIME, IntrigueSecret.BROKEN_OATH}),
        LawArea.COMMERCE: frozenset({IntrigueSecret.CRIME, IntrigueSecret.DEBT}),
        LawArea.FAITH: frozenset({IntrigueSecret.SECRET_CULT_MEMBERSHIP, IntrigueSecret.CRIME}),
        LawArea.LABOUR: frozenset({IntrigueSecret.CRIME, IntrigueSecret.DEBT}),
        LawArea.FAMILY: frozenset({IntrigueSecret.AFFAIR, IntrigueSecret.ILLEGITIMATE_CHILD, IntrigueSecret.TRUE_PARENTAGE}),
        LawArea.ENVIRONMENT: frozenset({IntrigueSecret.ECOSABOTAGE, IntrigueSecret.CRIME}),
    },
)


NAMED_CRIME_SECRETS: dict[CrimeKind, frozenset[IntrigueSecret]] = {
    CrimeKind.THEFT: frozenset({IntrigueSecret.CRIME}),
    CrimeKind.MURDER: frozenset({IntrigueSecret.MURDER, IntrigueSecret.CRIME}),
    CrimeKind.BLASPHEMY: frozenset({IntrigueSecret.HERESY, IntrigueSecret.SECRET_CULT_MEMBERSHIP}),
    CrimeKind.TREASON: frozenset({IntrigueSecret.CRIME, IntrigueSecret.BROKEN_OATH}),
    CrimeKind.DESERTION: frozenset({IntrigueSecret.COWARDICE_IN_BATTLE}),
    CrimeKind.WITCHCRAFT: frozenset({IntrigueSecret.DEAL_WITH_OUTER_BEING, IntrigueSecret.SECRET_CULT_MEMBERSHIP}),
    CrimeKind.MIND_THEFT: frozenset({IntrigueSecret.CRIME}),
    CrimeKind.UNLICENSED_COPYING: frozenset({IntrigueSecret.CRIME}),
    CrimeKind.FORCED_EDIT: frozenset({IntrigueSecret.CRIME}),
    CrimeKind.ERASURE: frozenset({IntrigueSecret.MURDER, IntrigueSecret.CRIME}),
    CrimeKind.MACHINE_SEIZURE: frozenset({IntrigueSecret.CRIME}),
    CrimeKind.IMPERSONATION: frozenset({IntrigueSecret.CRIME}),
    CrimeKind.MIND_COMPULSION: frozenset({IntrigueSecret.CRIME}),
}

END_TREATY_TREATY_STATUSS = frozenset({TreatyStatus.FULFILLED, TreatyStatus.EXPIRED})
INHERIT_CLAIMS_CLAIM_BASISS = frozenset({ClaimBasis.CONQUEST, ClaimBasis.DIVINE})
LAPSE_OATH_KINDS = frozenset({OathKind.FEALTY, OathKind.PROTECTION, OathKind.SWORN_KINSHIP, OathKind.CELIBACY, OathKind.SILENCE})
SUCCESSION_LINE_SUCCESSION_RULES = frozenset({SuccessionRule.PRIMOGENITURE, SuccessionRule.ULTIMOGENITURE})
BASE_OF_TAX_KINDS = frozenset({TaxKind.TRADE, TaxKind.SEIGNIORAGE})
HOSTILITIES_TREATY_KINDS = frozenset({TreatyKind.PEACE, TreatyKind.TRUCE, TreatyKind.NON_AGGRESSION})
KEEP_CLAUSES_TREATY_KINDS = frozenset({TreatyKind.TRUCE, TreatyKind.TRIBUTE})
KEEP_CLAUSES_TREATY_KINDS_2 = frozenset({TreatyKind.TRIBUTE, TreatyKind.TRUCE})
TO_SECRECY_FACTION_KINDS = (FactionKind.SECRET_SOCIETY, FactionKind.ASSASSINS)


CLAIM_STRENGTHS: Mapping[ClaimBasis, str] = total(
    ClaimBasis,
    {
        ClaimBasis.INHERITANCE: "inheritance_strength",
        ClaimBasis.MARRIAGE: "marriage_strength",
        ClaimBasis.CONQUEST: "conquest_strength",
        ClaimBasis.DIVINE: "divine_strength",
        ClaimBasis.FABRICATED: "fabricated_strength",
        ClaimBasis.DE_JURE: "de_jure_strength",
        ClaimBasis.ELECTION: "election_strength",
        ClaimBasis.ADOPTION: "adoption_strength",
        ClaimBasis.PROPHECY: "prophecy_strength",
    },
)


AREA_CLASH: Mapping[LawArea, str] = total(
    LawArea,
    {
        LawArea.SUCCESSION: "succession_clash_weight",
        LawArea.PROPERTY: "property_clash_weight",
        LawArea.FISCAL: "fiscal_clash_weight",
        LawArea.PENAL: "penal_clash_weight",
        LawArea.MILITARY: "military_clash_weight",
        LawArea.SOCIAL: "social_clash_weight",
        LawArea.PUBLIC_HEALTH: "public_health_clash_weight",
        LawArea.MAGIC: "magic_clash_weight",
        LawArea.CONSTITUTIONAL: "constitutional_clash_weight",
        LawArea.COMMERCE: "commerce_clash_weight",
        LawArea.FAITH: "faith_clash_weight",
        LawArea.LABOUR: "labour_clash_weight",
        LawArea.FAMILY: "family_clash_weight",
        LawArea.ENVIRONMENT: "environment_clash_weight",
    },
)

SERVING_CLIENTS = (ClientRole.BROKER, ClientRole.ARTIST, ClientRole.SCHOLAR, ClientRole.INFORMANT)
