from collections.abc import Mapping

from aerona.core.total import partial, total
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.made import (
    CompanyCharter,
    CompanyHoldingKind,
    IntrusionAim,
    IntrusionApproach,
    IntrusionTarget,
    RealmEntry,
    RelicStance,
    RelicState,
    RelicUse,
    ReplicatorOutput,
)
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.networks import NetworkCarrier
from aerona.domain.enums.world import TechnologyEra

MAKERS = (ReplicatorOutput.GOODS, ReplicatorOutput.STRUCTURES, ReplicatorOutput.COPIES)


HOLDING_WEIGHT: Mapping[CompanyHoldingKind, int] = total(
    CompanyHoldingKind,
    {
        CompanyHoldingKind.STRUCTURE: 100,
        CompanyHoldingKind.NETWORK: 150,
        CompanyHoldingKind.DATA_STORE: 120,
        CompanyHoldingKind.MADE_MIND: 130,
        CompanyHoldingKind.FABRICATOR: 140,
        CompanyHoldingKind.LIVING_LINE: 110,
        CompanyHoldingKind.ROUTE: 160,
        CompanyHoldingKind.ENCLAVE: 200,
    },
)


CHARTER_REACH: Mapping[CompanyCharter, tuple[bool, bool]] = total(
    CompanyCharter,
    {
        CompanyCharter.CHARTERED: (True, True),
        CompanyCharter.FREE: (True, True),
        CompanyCharter.STATE_OWNED: (False, False),
        CompanyCharter.COOPERATIVE: (False, True),
    },
)


CARRIERS = {
    TechnologyEra.STEAM: NetworkCarrier.WIRED,
    TechnologyEra.ELECTRICAL: NetworkCarrier.WIRED,
    TechnologyEra.INFORMATION: NetworkCarrier.MESH,
    TechnologyEra.ADVANCED: NetworkCarrier.BROADCAST,
    TechnologyEra.INTERSTELLAR: NetworkCarrier.BROADCAST,
    TechnologyEra.BEYOND: NetworkCarrier.MIND_LINK,
}


APPROACH_SKILLS = {
    IntrusionApproach.TECHNICAL: (SkillKind.COMPUTING, SkillKind.CRYPTOGRAPHY, SkillKind.ELECTRONICS),
    IntrusionApproach.SOCIAL: (SkillKind.DECEPTION, SkillKind.INTRIGUE),
    IntrusionApproach.INSIDER: (SkillKind.INTRIGUE,),
    IntrusionApproach.RITE: (SkillKind.RITUAL, SkillKind.SPELLCRAFT),
    IntrusionApproach.POWER: (SkillKind.SPELLCRAFT, SkillKind.SPIRIT_SPEAKING),
}


AIM_HARM = {IntrusionAim.READ: 2, IntrusionAim.ALTER: 4, IntrusionAim.DENY: 5, IntrusionAim.SEIZE: 8, IntrusionAim.PLANT: 3, IntrusionAim.EXTORT: 6}


ENTRY_SKILL: Mapping[RealmEntry, SkillKind | None] = total(
    RealmEntry,
    {
        RealmEntry.INTERFACE: None,
        RealmEntry.TRANSFER: None,
        RealmEntry.RITE: SkillKind.SPELLCRAFT,
        RealmEntry.DEATH: None,
        RealmEntry.BIRTH: None,
    },
)


DECLINE = {RelicState.WORKING: RelicState.FAILING, RelicState.FAILING: RelicState.BROKEN}


STANCE_USE = partial(
    RelicStance,
    {RelicStance.SACRED: RelicUse.REVERED, RelicStance.FORBIDDEN: RelicUse.FEARED, RelicStance.HERITAGE: RelicUse.DISPLAYED},
    without={RelicStance.TOOL},
)


OUTPUT_GOODS = {ReplicatorOutput.GOODS: CommodityKind.TOOLS, ReplicatorOutput.MEDICINE: CommodityKind.MEDICINE}


KEEPERS = (SkillKind.WRITING, SkillKind.LAW, SkillKind.CRYPTOGRAPHY, SkillKind.COMPUTING)

SEIZE_INTRUSION_TARGETS = frozenset({IntrusionTarget.MADE_MIND, IntrusionTarget.CONSTRUCT})
LAND_INTRUSION_AIMS = frozenset({IntrusionAim.ALTER, IntrusionAim.PLANT})
ADMIT_BY_ENTRY_REALM_ENTRYS = frozenset({RealmEntry.DEATH, RealmEntry.BIRTH})
