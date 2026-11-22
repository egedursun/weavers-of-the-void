from aerona.domain.enums.childhood import SocializationTechnique
from aerona.domain.enums.civilization import TierCapability
from aerona.domain.enums.customs import RevivalAim, RevivalGoal
from aerona.domain.enums.happening import LandAct
from aerona.domain.enums.mind import SkillKind, ValueAxis
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.powers import PowerState
from aerona.domain.enums.records import RumourDistortion
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.speech import SpeechVenue
from aerona.domain.enums.statecraft import CrisisDemand
from aerona.domain.enums.travel import JourneyIntent, TravelMethod, VehicleKind

TECHNIQUE_AXES: dict[SocializationTechnique, ValueAxis] = {
    SocializationTechnique.EXAMPLE: ValueAxis.FAMILY,
    SocializationTechnique.INSTRUCTION: ValueAxis.TRADITION,
    SocializationTechnique.PRAISE: ValueAxis.MERCY,
    SocializationTechnique.SHAME: ValueAxis.HONOUR,
    SocializationTechnique.PUNISHMENT: ValueAxis.HIERARCHY,
    SocializationTechnique.RITUAL_ORDEAL: ValueAxis.MARTIAL,
    SocializationTechnique.STORYTELLING: ValueAxis.ARTWORK,
    SocializationTechnique.PLAY: ValueAxis.LEISURE,
    SocializationTechnique.APPRENTICESHIP: ValueAxis.CRAFTSMANSHIP,
    SocializationTechnique.SCHOOLING: ValueAxis.KNOWLEDGE,
    SocializationTechnique.PEER_GROUP: ValueAxis.FRIENDSHIP,
    SocializationTechnique.AGE_SET: ValueAxis.LOYALTY,
}


WAY_KNOWLEDGE = (KnowledgeBranch.SEAFARING, KnowledgeBranch.PATHFINDING, KnowledgeBranch.ASTRONOMY)


INTENT_TIERS = {JourneyIntent.COLONY: TierCapability.COLONY, JourneyIntent.CONQUEST: TierCapability.CONQUEST}


SAMPLE_SKILLS = (SkillKind.SCIENCE, SkillKind.MEDICINE, SkillKind.FORAGING, SkillKind.BEAST_HANDLING)


COMMAND_SKILLS = (SkillKind.TACTICS, SkillKind.STRATEGY)


FORGE_SKILLS = (SkillKind.SMITHING, SkillKind.ENGINEERING)


MAKERS = (SkillKind.COMPUTING, SkillKind.ENGINEERING, SkillKind.SPELLCRAFT, SkillKind.RITUAL, SkillKind.MECHANICS, SkillKind.SCIENCE)


THRONES = (OfficeKind.RULER, OfficeKind.REGENT)


RULER_THRONES = (OfficeKind.RULER, OfficeKind.REGENT)


VENUE_REACH = {
    SpeechVenue.ASSEMBLY: 60,
    SpeechVenue.COURT: 30,
    SpeechVenue.TEMPLE: 50,
    SpeechVenue.SQUARE: 50,
    SpeechVenue.SCHOOL: 30,
    SpeechVenue.CAMP: 40,
    SpeechVenue.OUTLET: 0,
}


VESSEL_ROUTES = {
    VehicleKind.GATE: TravelMethod.ANCIENT_GATE,
    VehicleKind.SHIP: TravelMethod.LIGHT_SAIL,
    VehicleKind.MOUNT: TravelMethod.CARRIER_MOUNT,
    VehicleKind.BRIDGE: TravelMethod.DIVINE_BRIDGE,
}


AIMS = {
    RevivalGoal.REVIVE_LANGUAGE: RevivalAim.RESTORE,
    RevivalGoal.RESTORE_GOD: RevivalAim.RESTORE,
    RevivalGoal.EXPEL_FOREIGNERS: RevivalAim.RESTORE,
    RevivalGoal.ADOPT_WAYS: RevivalAim.ADOPT,
}


ACT_WORDS = {
    LandAct.SHIFT_RIVER: "moved its river",
    LandAct.PARCH: "parched it into desert",
    LandAct.GREEN: "brought the grass back",
    LandAct.MAKE_SALINE: "made its soil saline",
    LandAct.ENRICH_SOIL: "made its soil rich",
    LandAct.RAISE_LAND: "raised the land",
    LandAct.LOWER_LAND: "lowered the land",
    LandAct.CARVE_VALLEY: "carved a valley",
    LandAct.FILL_VALLEY: "filled its valleys",
    LandAct.OPEN_SPRING: "opened a spring",
    LandAct.CALL_LAVA: "called up lava",
    LandAct.SINK_COAST: "sank its coast",
}

RAISE_CHILD_SOCIALIZATION_TECHNIQUES = (SocializationTechnique.SHAME, SocializationTechnique.PUNISHMENT, SocializationTechnique.RITUAL_ORDEAL)
SEARCH_RUINS_SKILL_KINDS = (SkillKind.LORE, SkillKind.TRACKING)
DIPLOMACY_SKILL_KINDS = (SkillKind.NEGOTIATION, SkillKind.ETIQUETTE)
RAISE_SAPIENCE_TOOL_SKILL_KINDS = (SkillKind.SCIENCE, SkillKind.SPELLCRAFT, SkillKind.MEDICINE)
DEFEND_SYSTEM_SKILL_KINDS = (SkillKind.COMPUTING, SkillKind.CRYPTOGRAPHY, SkillKind.RITUAL)
TRAIN_POWER_POWER_STATES = frozenset({PowerState.LOST, PowerState.EXHAUSTED})
BUILD_STRUCTURE_SKILL_KINDS = (SkillKind.MASONRY, SkillKind.CARPENTRY, SkillKind.ENGINEERING)
ISSUE_DEMAND_CRISIS_DEMANDS = frozenset({CrisisDemand.CEDE_REGION, CrisisDemand.CONVERT})
RULES_A_REALM_OFFICE_KINDS = (OfficeKind.RULER, OfficeKind.REGENT)
VOICE_OF_OFFICE_KINDS = (OfficeKind.RULER, OfficeKind.REGENT)
SABOTAGE_SKILL_KINDS = (SkillKind.INTRIGUE, SkillKind.DECEPTION)
DISTORTION_ROW_RUMOUR_DISTORTIONS = (RumourDistortion.AMOUNT_CHANGED, RumourDistortion.OUTCOME_CHANGED)
