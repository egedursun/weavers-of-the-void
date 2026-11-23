from collections.abc import Mapping

from aerona.catalog.biology import SKYLESS_VARIANTS
from aerona.core.total import total
from aerona.domain.enums.affliction import PackageKind
from aerona.domain.enums.agrarian import PreparednessKind, RebuildCause
from aerona.domain.enums.arcana import SpellForm, SpellTechnique
from aerona.domain.enums.belonging import IdentityLayer
from aerona.domain.enums.biology import BiologyVariant
from aerona.domain.enums.body_systems import BodySystem
from aerona.domain.enums.communication import Medium
from aerona.domain.enums.concealment import BreachCause, HiddenTruthKind
from aerona.domain.enums.constructs import CommandToken, OrderKind
from aerona.domain.enums.crafts import AssistiveAid, RightKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.customs import AgeGrade, CoopPurpose, Intoxicant
from aerona.domain.enums.cycles import GiftState
from aerona.domain.enums.daily_life import HouseDuty, LeisureKind
from aerona.domain.enums.death_work import DeathRole
from aerona.domain.enums.demography import InheritanceCustom, Job
from aerona.domain.enums.divine import CouncilMotion
from aerona.domain.enums.ecology import AttackRange, SizeClass, SpeciesClass
from aerona.domain.enums.economy import ExtractionKind, HazardKind, TradeMode, TradeRouteStatus
from aerona.domain.enums.environment import WeatherEffect
from aerona.domain.enums.faction import FactionActionKind, FactionKind
from aerona.domain.enums.finance import TradePolicyKind
from aerona.domain.enums.folkways import CharmPower, MishapKind
from aerona.domain.enums.forecasting import ObservationMethod
from aerona.domain.enums.gathering import GatheringKind
from aerona.domain.enums.happening import LandAct
from aerona.domain.enums.honours import UnitHonourKind
from aerona.domain.enums.kind_crafts import FurnishingCategory
from aerona.domain.enums.life_traits import (
    ActKindTrait,
    AgeGradeTrait,
    AllocationModeTrait,
    AssistiveAidTrait,
    AttackRangeTrait,
    BiologyVariantTrait,
    BodySystemTrait,
    BreachCauseTrait,
    BuildingFormTrait,
    CaptiveFateTrait,
    CaptiveStatusTrait,
    CharmPowerTrait,
    ClauseKindTrait,
    CommanderTraitTrait,
    CommandTokenTrait,
    ConstructionStateTrait,
    ContestStakeTrait,
    CoopPurposeTrait,
    CouncilMotionTrait,
    CultivationMethodTrait,
    DeathRoleTrait,
    DuelContextTrait,
    EmotionTrait,
    ExpeditionGroundTrait,
    ExtractionKindTrait,
    FactionActionKindTrait,
    FactionKindTrait,
    FurnishingCategoryTrait,
    GatheringKindTrait,
    GiftStateTrait,
    GroupKindTrait,
    HazardKindTrait,
    HiddenTruthKindTrait,
    HouseDutyTrait,
    IdentityLayerTrait,
    InheritanceCustomTrait,
    InteractionKindTrait,
    IntoxicantTrait,
    JobTrait,
    JourneyIntentTrait,
    KnowledgeBranchTrait,
    LandActTrait,
    LeisureKindTrait,
    LifeStageTrait,
    LineTraitTrait,
    MadeMindStanceTrait,
    MediumTrait,
    MemoryKindTrait,
    MetabolismTrait,
    MindUpkeepTrait,
    MishapKindTrait,
    OathKindTrait,
    ObservationMethodTrait,
    OfficeDutyTrait,
    OfficeKindTrait,
    OrderKindTrait,
    PackageKindTrait,
    PassionKindTrait,
    PopulationInstrumentTrait,
    PowerOriginTrait,
    PowerStateTrait,
    PreparednessKindTrait,
    PunishmentKindTrait,
    RebuildCauseTrait,
    RecordFormTrait,
    RegionalStandingTrait,
    RelationTypeTrait,
    RightKindTrait,
    RumourDistortionTrait,
    SettleModeTrait,
    SizeClassTrait,
    SkillKindTrait,
    SourceLocusTrait,
    SpeciesClassTrait,
    SpeechVenueTrait,
    SpellFormTrait,
    SpellTechniqueTrait,
    StanceTrait,
    StarvationStageTrait,
    StructureSectionTrait,
    TacticTrait,
    TaxKindTrait,
    TechniqueTrait,
    ThoughtKindTrait,
    TradeModeTrait,
    TradePolicyKindTrait,
    TradeRouteStatusTrait,
    TreatyKindTrait,
    UnitHonourKindTrait,
    VehicleFamilyTrait,
    WarCauseTrait,
    WarEndingTrait,
    WarTerrainTrait,
    WeatherEffectTrait,
    WitnessModeTrait,
    WorksKindTrait,
    WorldEndTrait,
    WorldTypeTrait,
    YouthPurposeTrait,
)
from aerona.domain.enums.living import CultivationMethod, LineTrait, Metabolism
from aerona.domain.enums.made import MadeMindStance
from aerona.domain.enums.media import RecordForm
from aerona.domain.enums.military import CaptiveFate, CommanderTrait, DuelContext, Stance, StarvationStage, Tactic
from aerona.domain.enums.mind import ActKind, Emotion, MemoryKind, SkillKind, ThoughtKind
from aerona.domain.enums.minds import MindUpkeep
from aerona.domain.enums.mortal import LifeStage, PunishmentKind
from aerona.domain.enums.nature_kinds import OfficeDuty
from aerona.domain.enums.operations import ExpeditionGround
from aerona.domain.enums.orders import AllocationMode
from aerona.domain.enums.polity import ClauseKind, OathKind, OfficeKind, RegionalStanding, TreatyKind
from aerona.domain.enums.population import PopulationInstrument
from aerona.domain.enums.powers import PowerOrigin, PowerState, SourceLocus
from aerona.domain.enums.records import RumourDistortion, WitnessMode
from aerona.domain.enums.relations import ContestStake, GroupKind, InteractionKind, PassionKind, RelationType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.speech import SpeechVenue
from aerona.domain.enums.statecraft import TaxKind
from aerona.domain.enums.structure import BuildingForm, ConstructionState, StructureSection
from aerona.domain.enums.travel import JourneyIntent
from aerona.domain.enums.vehicles import VehicleFamily
from aerona.domain.enums.war import CaptiveStatus, WarCause, WarEnding
from aerona.domain.enums.works import WorksKind
from aerona.domain.enums.world import WorldType
from aerona.domain.enums.world_end import WorldEnd
from aerona.domain.enums.world_view import SettleMode, WarTerrain
from aerona.domain.enums.youth import YouthPurpose


def having[K, T](table: Mapping[K, frozenset[T]], trait: T) -> frozenset[K]:
    return frozenset(key for key, traits in table.items() if trait in traits)


ACT_KIND_TRAITS: Mapping[ActKind, frozenset[ActKindTrait]] = total(
    ActKind,
    {
        ActKind.EXECUTION: frozenset({ActKindTrait.FEARSOME}),
        ActKind.MUTILATION: frozenset({ActKindTrait.FEARSOME}),
        ActKind.BETRAYAL: frozenset(),
        ActKind.MERCY_TO_ENEMY: frozenset(),
        ActKind.SACRIFICE_OF_PEOPLE: frozenset(),
        ActKind.TRADE_WITH_OUTSIDERS: frozenset(),
        ActKind.BUILDING_TEMPLES: frozenset(),
        ActKind.BURNING_BOOKS: frozenset(),
        ActKind.CONQUEST: frozenset({ActKindTrait.WAR_ACTS}),
        ActKind.RAIDING: frozenset({ActKindTrait.WAR_ACTS}),
        ActKind.DUELLING: frozenset(),
        ActKind.RANSOM: frozenset(),
        ActKind.TAKING_CAPTIVES: frozenset({ActKindTrait.WAR_ACTS}),
        ActKind.OATHBREAKING: frozenset(),
        ActKind.LEARNING: frozenset(),
        ActKind.HOSPITALITY: frozenset(),
        ActKind.WINTER_FIGHTING: frozenset(),
        ActKind.GUEST_KILLING: frozenset(),
        ActKind.RITUAL_SCARRING: frozenset(),
        ActKind.KILLING_KIN: frozenset(),
        ActKind.KILLING_OUTSIDER: frozenset({ActKindTrait.WAR_ACTS}),
        ActKind.KILLING_IN_WAR: frozenset({ActKindTrait.WAR_ACTS}),
        ActKind.KILLING_CAPTIVE: frozenset(),
        ActKind.REGICIDE: frozenset(),
        ActKind.DUEL_TO_DEATH: frozenset(),
        ActKind.REVENGE_KILLING: frozenset(),
        ActKind.THEFT: frozenset({ActKindTrait.FAMINE_ACTS}),
        ActKind.TREASON: frozenset(),
        ActKind.COWARDICE: frozenset(),
        ActKind.DESECRATION: frozenset(),
        ActKind.BRIBERY: frozenset(),
        ActKind.SUICIDE: frozenset(),
        ActKind.TORTURE: frozenset({ActKindTrait.FEARSOME}),
        ActKind.EATING_SAPIENTS: frozenset(),
        ActKind.ICONOCLASM: frozenset(),
        ActKind.CONVERSION_BY_FORCE: frozenset(),
        ActKind.POLYGAMY: frozenset(),
        ActKind.INCEST: frozenset(),
        ActKind.MAGIC_USE: frozenset(),
        ActKind.BLOOD_MAGIC: frozenset(),
        ActKind.VOID_MAGIC: frozenset(),
        ActKind.NECROMANCY: frozenset(),
        ActKind.HOARDING_IN_FAMINE: frozenset({ActKindTrait.FAMINE_ACTS}),
        ActKind.SLAVERY: frozenset(),
        ActKind.ADULTERY: frozenset(),
        ActKind.USURY: frozenset(),
        ActKind.INFANTICIDE: frozenset(),
        ActKind.ABANDONING_ELDERS: frozenset(),
        ActKind.FORCED_LABOUR: frozenset(),
        ActKind.SELLING_OFFICES: frozenset(),
        ActKind.POACHING: frozenset(),
        ActKind.ENCLOSING: frozenset(),
        ActKind.LYING: frozenset(),
        ActKind.DRUNKENNESS: frozenset(),
        ActKind.TOMB_ROBBING: frozenset(),
        ActKind.USING_CHARMS: frozenset(),
        ActKind.FEEDING_ON_HOSTS: frozenset({ActKindTrait.FAMINE_ACTS}),
        ActKind.KILLING_SACRED_ANIMAL: frozenset(),
        ActKind.FIXING_CONTESTS: frozenset(),
    },
)


AGE_GRADE_TRAITS: Mapping[AgeGrade, frozenset[AgeGradeTrait]] = total(
    AgeGrade,
    {
        AgeGrade.CHILDREN: frozenset({AgeGradeTrait.UNWED_GRADES}),
        AgeGrade.YOUTHS: frozenset({AgeGradeTrait.UNWED_GRADES}),
        AgeGrade.YOUNG_ADULTS: frozenset(),
        AgeGrade.JUNIOR_ELDERS: frozenset(),
        AgeGrade.SENIOR_ELDERS: frozenset(),
    },
)


ALLOCATION_MODE_TRAITS: Mapping[AllocationMode, frozenset[AllocationModeTrait]] = total(
    AllocationMode,
    {
        AllocationMode.MARKET: frozenset(),
        AllocationMode.REDISTRIBUTION: frozenset({AllocationModeTrait.CENTRES, AllocationModeTrait.STATE_BUYERS}),
        AllocationMode.COMMAND: frozenset({AllocationModeTrait.STATE_BUYERS}),
        AllocationMode.OBLIGATION: frozenset({AllocationModeTrait.CENTRES}),
        AllocationMode.GIFT: frozenset(),
        AllocationMode.NEED: frozenset({AllocationModeTrait.SHARING}),
        AllocationMode.ABUNDANCE: frozenset({AllocationModeTrait.SHARING}),
    },
)


ASSISTIVE_AID_TRAITS: Mapping[AssistiveAid, frozenset[AssistiveAidTrait]] = total(
    AssistiveAid,
    {
        AssistiveAid.SPECTACLES: frozenset({AssistiveAidTrait.GROUND_LENS}),
        AssistiveAid.MAGNIFIER: frozenset({AssistiveAidTrait.GROUND_LENS}),
        AssistiveAid.TELESCOPE: frozenset({AssistiveAidTrait.GROUND_LENS}),
        AssistiveAid.HEARING_HORN: frozenset(),
        AssistiveAid.CANE: frozenset(),
        AssistiveAid.MICROSCOPE: frozenset({AssistiveAidTrait.GROUND_LENS}),
    },
)


ATTACK_RANGE_TRAITS: Mapping[AttackRange, frozenset[AttackRangeTrait]] = total(
    AttackRange,
    {
        AttackRange.TOUCH: frozenset(),
        AttackRange.NEAR: frozenset(),
        AttackRange.FAR: frozenset({AttackRangeTrait.WHOLE_TOWN}),
        AttackRange.SIGHT: frozenset({AttackRangeTrait.WHOLE_TOWN}),
    },
)


BIOLOGY_VARIANT_TRAITS: Mapping[BiologyVariant, frozenset[BiologyVariantTrait]] = total(
    BiologyVariant,
    {variant: frozenset({BiologyVariantTrait.SKYLESS}) if variant in SKYLESS_VARIANTS else frozenset() for variant in BiologyVariant},
)


BODY_SYSTEM_TRAITS: Mapping[BodySystem, frozenset[BodySystemTrait]] = total(
    BodySystem,
    {
        BodySystem.BREATH: frozenset({BodySystemTrait.BLOODLESS}),
        BodySystem.CIRCULATION: frozenset({BodySystemTrait.BLOODLESS}),
        BodySystem.DIGESTION: frozenset({BodySystemTrait.BLOODLESS}),
        BodySystem.REGULATION: frozenset(),
        BodySystem.NERVES: frozenset(),
        BodySystem.IMMUNITY: frozenset(),
        BodySystem.REPRODUCTION: frozenset(),
        BodySystem.STRUCTURE: frozenset(),
        BodySystem.NONE: frozenset(),
    },
)


BREACH_CAUSE_TRAITS: Mapping[BreachCause, frozenset[BreachCauseTrait]] = total(
    BreachCause,
    {
        BreachCause.OVERT_USE: frozenset({BreachCauseTrait.ACCORD_BREAKING}),
        BreachCause.WITNESS: frozenset(),
        BreachCause.DEFECTOR: frozenset({BreachCauseTrait.ACCORD_BREAKING}),
        BreachCause.INVESTIGATOR: frozenset(),
        BreachCause.ACCIDENT: frozenset(),
        BreachCause.WAR: frozenset({BreachCauseTrait.ACCORD_BREAKING}),
        BreachCause.RECORD_LEAK: frozenset(),
        BreachCause.INTRUSION: frozenset(),
        BreachCause.REVELATION_BY_GOD: frozenset(),
    },
)


BUILDING_FORM_TRAITS: Mapping[BuildingForm, frozenset[BuildingFormTrait]] = total(
    BuildingForm,
    {
        BuildingForm.HALL: frozenset(),
        BuildingForm.LONGHOUSE: frozenset(),
        BuildingForm.TOWER: frozenset(),
        BuildingForm.KEEP: frozenset(),
        BuildingForm.DOME: frozenset(),
        BuildingForm.SPIRE: frozenset(),
        BuildingForm.STEPPED: frozenset(),
        BuildingForm.PYRAMID: frozenset(),
        BuildingForm.COURTYARD: frozenset(),
        BuildingForm.RING: frozenset({BuildingFormTrait.FIXED_FORMS}),
        BuildingForm.TENT: frozenset(),
        BuildingForm.MOUND: frozenset(),
        BuildingForm.ARCADE: frozenset(),
        BuildingForm.TERRACE: frozenset(),
        BuildingForm.PLATFORM: frozenset(),
        BuildingForm.BRIDGE_FORM: frozenset({BuildingFormTrait.FIXED_FORMS}),
        BuildingForm.WALL_LINE: frozenset({BuildingFormTrait.FIXED_FORMS}),
        BuildingForm.TUNNEL_FORM: frozenset({BuildingFormTrait.FIXED_FORMS}),
        BuildingForm.ORBITAL: frozenset({BuildingFormTrait.FIXED_FORMS}),
        BuildingForm.HIGH_RISE: frozenset(),
        BuildingForm.ARCOLOGY: frozenset(),
        BuildingForm.BUNKER: frozenset(),
        BuildingForm.FLOATING: frozenset(),
        BuildingForm.GEODESIC: frozenset(),
        BuildingForm.MODULAR: frozenset(),
        BuildingForm.GROWN: frozenset(),
        BuildingForm.CARVED: frozenset(),
    },
)


CAPTIVE_FATE_TRAITS: Mapping[CaptiveFate, frozenset[CaptiveFateTrait]] = total(
    CaptiveFate,
    {
        CaptiveFate.HELD: frozenset({CaptiveFateTrait.BOUND}),
        CaptiveFate.RANSOMED: frozenset(),
        CaptiveFate.ENSLAVED: frozenset({CaptiveFateTrait.BOUND}),
        CaptiveFate.SACRIFICED: frozenset(),
        CaptiveFate.LABOUR: frozenset({CaptiveFateTrait.BOUND}),
        CaptiveFate.EXCHANGED: frozenset(),
        CaptiveFate.RELEASED: frozenset(),
        CaptiveFate.EXECUTED: frozenset(),
        CaptiveFate.RECRUITED: frozenset({CaptiveFateTrait.BOUND}),
    },
)


CAPTIVE_STATUS_TRAITS: Mapping[CaptiveStatus, frozenset[CaptiveStatusTrait]] = total(
    CaptiveStatus,
    {
        CaptiveStatus.HELD: frozenset(),
        CaptiveStatus.RANSOMED: frozenset({CaptiveStatusTrait.FREEING_STATUSES, CaptiveStatusTrait.RESCUE_STATUSES}),
        CaptiveStatus.ESCAPED: frozenset({CaptiveStatusTrait.FREEING_STATUSES}),
        CaptiveStatus.EXECUTED: frozenset(),
        CaptiveStatus.TURNCOAT: frozenset(),
        CaptiveStatus.RESCUED: frozenset({CaptiveStatusTrait.FREEING_STATUSES, CaptiveStatusTrait.RESCUE_STATUSES}),
        CaptiveStatus.RELEASED: frozenset({CaptiveStatusTrait.FREEING_STATUSES}),
        CaptiveStatus.WARD: frozenset(),
        CaptiveStatus.PAROLED: frozenset({CaptiveStatusTrait.FREEING_STATUSES, CaptiveStatusTrait.RESCUE_STATUSES, CaptiveStatusTrait.AFTER_CAPTIVITY}),
        CaptiveStatus.MARRIED_IN: frozenset({CaptiveStatusTrait.AFTER_CAPTIVITY}),
    },
)


CHARM_POWER_TRAITS: Mapping[CharmPower, frozenset[CharmPowerTrait]] = total(
    CharmPower,
    {
        CharmPower.PROTECTION: frozenset({CharmPowerTrait.WARDS}),
        CharmPower.FERTILITY: frozenset(),
        CharmPower.LUCK: frozenset({CharmPowerTrait.WARDS}),
        CharmPower.HEALING: frozenset(),
    },
)


CLAUSE_KIND_TRAITS: Mapping[ClauseKind, frozenset[ClauseKindTrait]] = total(
    ClauseKind,
    {
        ClauseKind.CALL_TO_ARMS: frozenset({ClauseKindTrait.PEACEFUL}),
        ClauseKind.TRIBUTE: frozenset(),
        ClauseKind.CESSION: frozenset(),
        ClauseKind.HOSTAGE: frozenset(),
        ClauseKind.MARRIAGE: frozenset(),
        ClauseKind.TRADE_RIGHTS: frozenset(),
        ClauseKind.TOLLS_WAIVED: frozenset(),
        ClauseKind.RELIGIOUS_FREEDOM: frozenset(),
        ClauseKind.DEMILITARISED: frozenset(),
        ClauseKind.CHAMPION: frozenset(),
        ClauseKind.EXTRADITION: frozenset(),
        ClauseKind.WERGILD: frozenset(),
        ClauseKind.NON_AGGRESSION: frozenset({ClauseKindTrait.PEACEFUL}),
        ClauseKind.ROUTE_CONTROL: frozenset(),
        ClauseKind.RESOURCE_DEMAND: frozenset(),
        ClauseKind.RESEARCH_AGREEMENT: frozenset(),
        ClauseKind.FLEET_LIMIT: frozenset(),
        ClauseKind.AUTONOMOUS_WEAPONS_BAN: frozenset({ClauseKindTrait.METHOD_CLAUSES}),
        ClauseKind.MIND_SEIZURE_BAN: frozenset({ClauseKindTrait.METHOD_CLAUSES}),
        ClauseKind.SOLDIER_COPY_BAN: frozenset({ClauseKindTrait.METHOD_CLAUSES}),
        ClauseKind.REPLICATOR_WEAPON_BAN: frozenset({ClauseKindTrait.METHOD_CLAUSES}),
        ClauseKind.CIVIL_NETWORK_SHIELD: frozenset({ClauseKindTrait.METHOD_CLAUSES}),
        ClauseKind.CIVIL_HOST_SHIELD: frozenset({ClauseKindTrait.METHOD_CLAUSES}),
        ClauseKind.NO_MIND_COMPULSION: frozenset({ClauseKindTrait.METHOD_CLAUSES}),
        ClauseKind.NO_PLAGUE_POWERS: frozenset({ClauseKindTrait.METHOD_CLAUSES}),
        ClauseKind.NO_DESIGNED_DISEASE: frozenset({ClauseKindTrait.METHOD_CLAUSES}),
        ClauseKind.MASS_WEAPON_LIMIT: frozenset({ClauseKindTrait.METHOD_CLAUSES}),
    },
)


COMMAND_TOKEN_TRAITS: Mapping[CommandToken, frozenset[CommandTokenTrait]] = total(
    CommandToken,
    {
        CommandToken.NONE: frozenset(),
        CommandToken.ITEM: frozenset({CommandTokenTrait.OWNED_TOKENS}),
        CommandToken.WORD: frozenset(),
        CommandToken.BLOODLINE: frozenset(),
        CommandToken.OFFICE: frozenset(),
        CommandToken.NETWORK_KEY: frozenset({CommandTokenTrait.OWNED_TOKENS}),
    },
)


COMMANDER_TRAIT_TRAITS: Mapping[CommanderTrait, frozenset[CommanderTraitTrait]] = total(
    CommanderTrait,
    {
        CommanderTrait.AGGRESSIVE_ASSAULTER: frozenset(
            {CommanderTraitTrait.AGGRESSIVE, CommanderTraitTrait.CLASH_AGGRESSIVE, CommanderTraitTrait.DECAPITATORS}
        ),
        CommanderTrait.DEFENSIVE_GENIUS: frozenset({CommanderTraitTrait.CAREFUL}),
        CommanderTrait.CAVALRY_MASTER: frozenset(),
        CommanderTrait.WINTER_CAMPAIGNER: frozenset(),
        CommanderTrait.HILL_FIGHTER: frozenset(),
        CommanderTrait.SIEGE_EXPERT: frozenset({CommanderTraitTrait.AGGRESSIVE}),
        CommanderTrait.RECKLESS: frozenset({CommanderTraitTrait.AGGRESSIVE, CommanderTraitTrait.CLASH_AGGRESSIVE}),
        CommanderTrait.CAUTIOUS: frozenset({CommanderTraitTrait.CAREFUL}),
        CommanderTrait.INSPIRING: frozenset(),
        CommanderTrait.BRUTAL: frozenset({CommanderTraitTrait.AGGRESSIVE, CommanderTraitTrait.DECAPITATORS}),
        CommanderTrait.FOREST_FIGHTER: frozenset(),
        CommanderTrait.DESERT_FIGHTER: frozenset(),
        CommanderTrait.MARSH_FIGHTER: frozenset(),
        CommanderTrait.SKY_COMMANDER: frozenset(),
        CommanderTrait.SPACE_COMMANDER: frozenset(),
        CommanderTrait.ARTILLERIST: frozenset(),
        CommanderTrait.AMBUSHER: frozenset(),
        CommanderTrait.LOGISTICIAN: frozenset(),
        CommanderTrait.UNDERGROUND_FIGHTER: frozenset(),
        CommanderTrait.AMPHIBIOUS_COMMANDER: frozenset(),
        CommanderTrait.SIEGE_DEFENDER: frozenset(),
        CommanderTrait.SKIRMISHER: frozenset(),
        CommanderTrait.ARMOURED_COMMANDER: frozenset(),
        CommanderTrait.DISCIPLINARIAN: frozenset(),
        CommanderTrait.SIGNALS_COMMANDER: frozenset(),
        CommanderTrait.NIGHT_FIGHTER: frozenset(),
    },
)


CONSTRUCTION_STATE_TRAITS: Mapping[ConstructionState, frozenset[ConstructionStateTrait]] = total(
    ConstructionState,
    {
        ConstructionState.PLANNED: frozenset({ConstructionStateTrait.COUNTED_STATES}),
        ConstructionState.BUILDING: frozenset({ConstructionStateTrait.COUNTED_STATES}),
        ConstructionState.COMPLETE: frozenset({ConstructionStateTrait.COUNTED_STATES}),
        ConstructionState.DAMAGED: frozenset({ConstructionStateTrait.COUNTED_STATES}),
        ConstructionState.RUINED: frozenset(),
        ConstructionState.ABANDONED: frozenset(),
        ConstructionState.DISMANTLED: frozenset(),
    },
)


CONTEST_STAKE_TRAITS: Mapping[ContestStake, frozenset[ContestStakeTrait]] = total(
    ContestStake,
    {
        ContestStake.HONOUR: frozenset(),
        ContestStake.UNION: frozenset({ContestStakeTrait.NOTED}),
        ContestStake.WAGER: frozenset(),
        ContestStake.OFFICE: frozenset({ContestStakeTrait.NOTED}),
        ContestStake.CAPTIVE: frozenset({ContestStakeTrait.NOTED}),
        ContestStake.DIVINE_FAVOUR: frozenset({ContestStakeTrait.NOTED}),
        ContestStake.LAND: frozenset({ContestStakeTrait.NOTED}),
        ContestStake.FREEDOM: frozenset({ContestStakeTrait.NOTED}),
        ContestStake.KNOWLEDGE: frozenset({ContestStakeTrait.NOTED}),
    },
)


COOP_PURPOSE_TRAITS: Mapping[CoopPurpose, frozenset[CoopPurposeTrait]] = total(
    CoopPurpose,
    {
        CoopPurpose.MILL: frozenset({CoopPurposeTrait.WORKING}),
        CoopPurpose.BOATS: frozenset({CoopPurposeTrait.WORKING}),
        CoopPurpose.IRRIGATION: frozenset({CoopPurposeTrait.WORKING}),
        CoopPurpose.INSURANCE: frozenset({CoopPurposeTrait.POOLING, CoopPurposeTrait.RELIEVING}),
        CoopPurpose.BURIAL: frozenset({CoopPurposeTrait.POOLING, CoopPurposeTrait.RELIEVING}),
        CoopPurpose.CREDIT: frozenset({CoopPurposeTrait.RELIEVING}),
        CoopPurpose.GRANARY: frozenset({CoopPurposeTrait.POOLING}),
        CoopPurpose.HERDING: frozenset({CoopPurposeTrait.WORKING}),
    },
)


COUNCIL_MOTION_TRAITS: Mapping[CouncilMotion, frozenset[CouncilMotionTrait]] = total(
    CouncilMotion,
    {
        CouncilMotion.NONE: frozenset(),
        CouncilMotion.AGAINST_DOOMSDAY: frozenset(),
        CouncilMotion.JOINT_BLESSING: frozenset(),
        CouncilMotion.CONDEMN_REBEL: frozenset(),
        CouncilMotion.CALL_FOR_PEACE: frozenset(),
        CouncilMotion.WAR_ON_FOREIGN_GOD: frozenset(),
        CouncilMotion.DIVIDE_WORLDS: frozenset(),
        CouncilMotion.OUTLAW_RITE: frozenset(),
        CouncilMotion.PUNISH_SON: frozenset(),
        CouncilMotion.BLESS_HERO: frozenset(),
        CouncilMotion.HOLY_WORLD: frozenset(),
        CouncilMotion.COSMIC_TRUCE: frozenset(),
        CouncilMotion.PETITION_CREATOR: frozenset(),
        CouncilMotion.APPOINT_OFFICE: frozenset(),
        CouncilMotion.REASSIGN_WORLD: frozenset(),
        CouncilMotion.OUTLAW_POWER: frozenset({CouncilMotionTrait.ORDER_LASTING}),
        CouncilMotion.OUTLAW_SOURCE: frozenset({CouncilMotionTrait.ORDER_LASTING}),
        CouncilMotion.ADMIT_MEMBER: frozenset(),
        CouncilMotion.EXPEL_MEMBER: frozenset(),
        CouncilMotion.RECOGNISE_GOD: frozenset(),
        CouncilMotion.ESSENCE_TITHE: frozenset(),
        CouncilMotion.SET_COUNCIL_RULES: frozenset(),
        CouncilMotion.REGULATE_MADE_MINDS: frozenset({CouncilMotionTrait.ORDER_LASTING}),
        CouncilMotion.REGULATE_POWERS: frozenset({CouncilMotionTrait.ORDER_LASTING}),
        CouncilMotion.REGULATE_LIVING_CRAFT: frozenset({CouncilMotionTrait.ORDER_LASTING}),
    },
)


CULTIVATION_METHOD_TRAITS: Mapping[CultivationMethod, frozenset[CultivationMethodTrait]] = total(
    CultivationMethod,
    {
        CultivationMethod.SELECTIVE_BREEDING: frozenset(),
        CultivationMethod.CULTIVATION: frozenset(),
        CultivationMethod.SHAPING: frozenset({CultivationMethodTrait.RITE_PATHS}),
        CultivationMethod.ENGINEERING: frozenset(),
        CultivationMethod.SYNTHESIS: frozenset(),
        CultivationMethod.BINDING: frozenset({CultivationMethodTrait.RITE_PATHS}),
        CultivationMethod.CLONING: frozenset({CultivationMethodTrait.RITE_PATHS}),
        CultivationMethod.MERGING: frozenset({CultivationMethodTrait.RITE_PATHS}),
        CultivationMethod.INDUCTION: frozenset(),
    },
)


DEATH_ROLE_TRAITS: Mapping[DeathRole, frozenset[DeathRoleTrait]] = total(
    DeathRole,
    {
        DeathRole.WASHER: frozenset({DeathRoleTrait.HANDLING}),
        DeathRole.PREPARER: frozenset({DeathRoleTrait.HANDLING, DeathRoleTrait.TENDING}),
        DeathRole.KEEPER_OF_REMAINS: frozenset({DeathRoleTrait.SACRED}),
        DeathRole.OFFICIANT: frozenset({DeathRoleTrait.SACRED}),
        DeathRole.MOURNER: frozenset(),
        DeathRole.RECORD_KEEPER: frozenset(),
        DeathRole.CARRIER: frozenset({DeathRoleTrait.HANDLING, DeathRoleTrait.TENDING}),
    },
)


DUEL_CONTEXT_TRAITS: Mapping[DuelContext, frozenset[DuelContextTrait]] = total(
    DuelContext,
    {
        DuelContext.WAR: frozenset({DuelContextTrait.DUEL_CONTEXTS, DuelContextTrait.AT_WAR}),
        DuelContext.HONOUR: frozenset({DuelContextTrait.DUEL_CONTEXTS, DuelContextTrait.CUSTOMARY}),
        DuelContext.TRIAL: frozenset({DuelContextTrait.DUEL_CONTEXTS}),
        DuelContext.CHAMPION: frozenset({DuelContextTrait.DUEL_CONTEXTS, DuelContextTrait.AT_WAR}),
        DuelContext.GOD: frozenset({DuelContextTrait.DUEL_CONTEXTS, DuelContextTrait.AT_WAR}),
        DuelContext.RITUAL: frozenset({DuelContextTrait.DUEL_CONTEXTS, DuelContextTrait.CUSTOMARY}),
    },
)


EMOTION_TRAITS: Mapping[Emotion, frozenset[EmotionTrait]] = total(
    Emotion,
    {
        Emotion.JOY: frozenset({EmotionTrait.STIRRED}),
        Emotion.CONTENTMENT: frozenset(),
        Emotion.PRIDE: frozenset({EmotionTrait.STIRRED}),
        Emotion.LOVE: frozenset(),
        Emotion.GRATITUDE: frozenset(),
        Emotion.RELIEF: frozenset(),
        Emotion.HOPE: frozenset({EmotionTrait.HOPEFUL}),
        Emotion.AWE: frozenset({EmotionTrait.STIRRED}),
        Emotion.AMUSEMENT: frozenset(),
        Emotion.FEAR: frozenset({EmotionTrait.AFRAID}),
        Emotion.ANXIETY: frozenset({EmotionTrait.AFRAID}),
        Emotion.ANGER: frozenset({EmotionTrait.ANGRY}),
        Emotion.RAGE: frozenset({EmotionTrait.ANGRY}),
        Emotion.GRIEF: frozenset({EmotionTrait.GRIEVING}),
        Emotion.SADNESS: frozenset({EmotionTrait.GRIEVING}),
        Emotion.SHAME: frozenset(),
        Emotion.GUILT: frozenset(),
        Emotion.ENVY: frozenset(),
        Emotion.JEALOUSY: frozenset(),
        Emotion.DISGUST: frozenset(),
        Emotion.LONELINESS: frozenset(),
        Emotion.BOREDOM: frozenset(),
        Emotion.DESPAIR: frozenset({EmotionTrait.GRIEVING}),
        Emotion.LONGING: frozenset(),
        Emotion.SURPRISE: frozenset({EmotionTrait.STIRRED}),
        Emotion.CURIOSITY: frozenset({EmotionTrait.STIRRED}),
        Emotion.COMPASSION: frozenset(),
        Emotion.CONTEMPT: frozenset({EmotionTrait.ANGRY}),
    },
)


EXPEDITION_GROUND_TRAITS: Mapping[ExpeditionGround, frozenset[ExpeditionGroundTrait]] = total(
    ExpeditionGround,
    {
        ExpeditionGround.SITE: frozenset({ExpeditionGroundTrait.DARK_GROUNDS}),
        ExpeditionGround.WILDS: frozenset(),
        ExpeditionGround.UNDERWORLD: frozenset({ExpeditionGroundTrait.DARK_GROUNDS}),
        ExpeditionGround.REALM: frozenset({ExpeditionGroundTrait.DARK_GROUNDS}),
    },
)


EXTRACTION_KIND_TRAITS: Mapping[ExtractionKind, frozenset[ExtractionKindTrait]] = total(
    ExtractionKind,
    {
        ExtractionKind.MINING: frozenset({ExtractionKindTrait.ARTISAN_KINDS}),
        ExtractionKind.QUARRYING: frozenset({ExtractionKindTrait.ARTISAN_KINDS}),
        ExtractionKind.LOGGING: frozenset(),
        ExtractionKind.FISHING: frozenset(),
        ExtractionKind.HERDING: frozenset(),
        ExtractionKind.FARMING: frozenset(),
        ExtractionKind.GATHERING: frozenset(),
        ExtractionKind.DRILLING: frozenset(),
        ExtractionKind.PUMPING: frozenset(),
        ExtractionKind.DREDGING: frozenset(),
        ExtractionKind.DEEP_SEA: frozenset(),
        ExtractionKind.ATMOSPHERIC: frozenset(),
        ExtractionKind.ASTEROID: frozenset(),
        ExtractionKind.STELLAR: frozenset(),
        ExtractionKind.SOURCE_HARVEST: frozenset(),
        ExtractionKind.SALVAGE: frozenset(),
        ExtractionKind.LIVING_HARVEST: frozenset(),
        ExtractionKind.DISTILLATION: frozenset(),
    },
)


FACTION_ACTION_KIND_TRAITS: Mapping[FactionActionKind, frozenset[FactionActionKindTrait]] = total(
    FactionActionKind,
    {
        FactionActionKind.LOBBY: frozenset(),
        FactionActionKind.BRIBE: frozenset(),
        FactionActionKind.PETITION: frozenset(),
        FactionActionKind.STRIKE: frozenset({FactionActionKindTrait.DEFIANT}),
        FactionActionKind.RIOT: frozenset({FactionActionKindTrait.DEFIANT}),
        FactionActionKind.COUP: frozenset({FactionActionKindTrait.DEFIANT}),
        FactionActionKind.ASSASSINATE: frozenset({FactionActionKindTrait.DEFIANT}),
        FactionActionKind.SMUGGLE: frozenset(),
        FactionActionKind.RAID: frozenset(),
        FactionActionKind.FUND_WAR: frozenset(),
        FactionActionKind.RECRUIT: frozenset(),
        FactionActionKind.SCHISM: frozenset(),
        FactionActionKind.SUPPRESSED: frozenset(),
        FactionActionKind.HIRED: frozenset(),
        FactionActionKind.DEFECTED: frozenset(),
        FactionActionKind.PROPAGANDA: frozenset(),
        FactionActionKind.BOYCOTT: frozenset({FactionActionKindTrait.DEFIANT}),
    },
)


FACTION_KIND_TRAITS: Mapping[FactionKind, frozenset[FactionKindTrait]] = total(
    FactionKind,
    {
        FactionKind.MERCHANT_GUILD: frozenset(
            {
                FactionKindTrait.GUILDS,
                FactionKindTrait.HERALDRY_GUILDS,
            }
        ),
        FactionKind.CRAFT_GUILD: frozenset({FactionKindTrait.GUILDS, FactionKindTrait.HERALDRY_GUILDS}),
        FactionKind.PRIESTHOOD: frozenset({FactionKindTrait.GUILDS}),
        FactionKind.WARRIOR_ORDER: frozenset({FactionKindTrait.GUILDS, FactionKindTrait.HERALDRY_GUILDS, FactionKindTrait.ORDERS, FactionKindTrait.WARLIKE}),
        FactionKind.NOBLE_COUNCIL: frozenset(),
        FactionKind.PEASANT_LEAGUE: frozenset(),
        FactionKind.REBELS: frozenset({FactionKindTrait.MOVEMENTS, FactionKindTrait.TREASON_KINDS}),
        FactionKind.BANDITS: frozenset({FactionKindTrait.GANGS, FactionKindTrait.WARLIKE}),
        FactionKind.PIRATES: frozenset({FactionKindTrait.WARLIKE}),
        FactionKind.ASSASSINS: frozenset({}),
        FactionKind.SCHOLARS_ACADEMY: frozenset({FactionKindTrait.GUILDS}),
        FactionKind.SECRET_SOCIETY: frozenset({FactionKindTrait.TREASON_KINDS}),
        FactionKind.MERCENARY_COMPANY: frozenset({FactionKindTrait.WARLIKE}),
        FactionKind.INTERWORLD_FEDERATION: frozenset(),
        FactionKind.WANDERING_MARKET: frozenset({}),
        FactionKind.ROUTE_RAIDERS: frozenset({FactionKindTrait.WARLIKE}),
        FactionKind.SOCIAL_CIRCLE: frozenset(),
        FactionKind.MAGE_ORDER: frozenset({FactionKindTrait.ORDERS}),
        FactionKind.ESTATE: frozenset(),
        FactionKind.PARTY: frozenset({FactionKindTrait.MOVEMENTS}),
        FactionKind.MOVEMENT: frozenset({FactionKindTrait.MOVEMENTS}),
        FactionKind.CHARTERED_COMPANY: frozenset(),
        FactionKind.HOLY_ORDER: frozenset({FactionKindTrait.HERALDRY_GUILDS, FactionKindTrait.ORDERS}),
        FactionKind.CRIME_FAMILY: frozenset({FactionKindTrait.GANGS}),
        FactionKind.THIEVES_GUILD: frozenset(
            {
                FactionKindTrait.GANGS,
                FactionKindTrait.HERALDRY_GUILDS,
            }
        ),
        FactionKind.SMUGGLING_RING: frozenset({FactionKindTrait.GANGS}),
        FactionKind.PIRATE_CONFEDERACY: frozenset({FactionKindTrait.WARLIKE}),
        FactionKind.ART_MOVEMENT: frozenset(),
        FactionKind.CLUB: frozenset(),
        FactionKind.LEAGUE: frozenset(),
        FactionKind.WORKERS_UNION: frozenset({FactionKindTrait.BODY_KINDS}),
        FactionKind.ENGINEERS_SOCIETY: frozenset(),
        FactionKind.FINANCIERS: frozenset({}),
        FactionKind.VETERANS: frozenset(),
        FactionKind.WORKER_BODY: frozenset({FactionKindTrait.BODY_KINDS}),
        FactionKind.STREET_GANG: frozenset({FactionKindTrait.GANGS}),
        FactionKind.TRAFFICKING_RING: frozenset({FactionKindTrait.GANGS}),
    },
)


FURNISHING_CATEGORY_TRAITS: Mapping[FurnishingCategory, frozenset[FurnishingCategoryTrait]] = total(
    FurnishingCategory,
    {
        FurnishingCategory.SLEEPING: frozenset(),
        FurnishingCategory.SEATING: frozenset(),
        FurnishingCategory.STORAGE: frozenset(),
        FurnishingCategory.TABLE: frozenset(),
        FurnishingCategory.LIGHTING: frozenset({FurnishingCategoryTrait.FURNISHING_FIRE}),
        FurnishingCategory.HEATING: frozenset({FurnishingCategoryTrait.FURNISHING_FIRE}),
        FurnishingCategory.COOKING_VESSEL: frozenset(),
        FurnishingCategory.TABLEWARE: frozenset(),
        FurnishingCategory.HOUSEHOLD_TEXTILE: frozenset(),
        FurnishingCategory.DECORATION: frozenset(),
        FurnishingCategory.SANITATION: frozenset(),
        FurnishingCategory.SHRINE: frozenset(),
    },
)


GATHERING_KIND_TRAITS: Mapping[GatheringKind, frozenset[GatheringKindTrait]] = total(
    GatheringKind,
    {
        GatheringKind.FEAST: frozenset({GatheringKindTrait.POTLATCH_FEASTS, GatheringKindTrait.SON_KINDS}),
        GatheringKind.WEDDING: frozenset({GatheringKindTrait.POTLATCH_FEASTS}),
        GatheringKind.FUNERAL: frozenset({GatheringKindTrait.POTLATCH_FEASTS}),
        GatheringKind.CORONATION: frozenset({GatheringKindTrait.ENGINE_KINDS}),
        GatheringKind.TOURNAMENT: frozenset({GatheringKindTrait.RULER_KINDS}),
        GatheringKind.HUNT: frozenset(),
        GatheringKind.PILGRIMAGE: frozenset({GatheringKindTrait.SON_KINDS}),
        GatheringKind.COUNCIL: frozenset({GatheringKindTrait.RULER_KINDS}),
        GatheringKind.SUMMIT: frozenset({GatheringKindTrait.RULER_KINDS}),
        GatheringKind.FESTIVAL: frozenset({GatheringKindTrait.POTLATCH_FEASTS, GatheringKindTrait.SON_KINDS}),
        GatheringKind.FAIR: frozenset(),
        GatheringKind.GAMES: frozenset({GatheringKindTrait.SON_KINDS}),
        GatheringKind.PERFORMANCE: frozenset({GatheringKindTrait.SON_KINDS}),
        GatheringKind.TRIAL: frozenset({GatheringKindTrait.ENGINE_KINDS}),
        GatheringKind.EXECUTION: frozenset({GatheringKindTrait.ENGINE_KINDS}),
        GatheringKind.PROCESSION: frozenset({GatheringKindTrait.SON_KINDS}),
        GatheringKind.MILESTONE: frozenset(),
        GatheringKind.WAKE: frozenset(),
        GatheringKind.EXAMINATION: frozenset({GatheringKindTrait.ENGINE_KINDS}),
        GatheringKind.ELECTION: frozenset({GatheringKindTrait.ENGINE_KINDS}),
        GatheringKind.RALLY: frozenset(),
        GatheringKind.STRIKE: frozenset(),
        GatheringKind.CONVENTION: frozenset(),
        GatheringKind.LAUNCH: frozenset({GatheringKindTrait.ENGINE_KINDS}),
        GatheringKind.BROADCAST: frozenset(),
        GatheringKind.TESTING: frozenset(),
        GatheringKind.EXHIBITION: frozenset(),
        GatheringKind.TRADE_FAIR: frozenset(),
        GatheringKind.SUMMIT_OF_GODS: frozenset(),
        GatheringKind.NETWORK_GATHERING: frozenset(),
        GatheringKind.REALM_GATHERING: frozenset(),
        GatheringKind.MOURNING: frozenset(),
        GatheringKind.INITIATION: frozenset(),
        GatheringKind.SPORT_MATCH: frozenset(),
        GatheringKind.COMMEMORATION: frozenset({GatheringKindTrait.ENGINE_KINDS}),
        GatheringKind.MUSTER: frozenset({GatheringKindTrait.ENGINE_KINDS}),
    },
)


GIFT_STATE_TRAITS: Mapping[GiftState, frozenset[GiftStateTrait]] = total(
    GiftState,
    {
        GiftState.OPEN: frozenset({GiftStateTrait.OBLIGING}),
        GiftState.RETURNED: frozenset(),
        GiftState.REFUSED: frozenset(),
        GiftState.DESTROYED: frozenset({GiftStateTrait.OBLIGING}),
        GiftState.LAPSED: frozenset(),
        GiftState.EXCEEDED: frozenset(),
        GiftState.PASSED_ON: frozenset(),
        GiftState.RELEASED: frozenset(),
    },
)


GROUP_KIND_TRAITS: Mapping[GroupKind, frozenset[GroupKindTrait]] = total(
    GroupKind,
    {
        GroupKind.HOUSEHOLD: frozenset(),
        GroupKind.COURT: frozenset(),
        GroupKind.CIRCLE: frozenset({GroupKindTrait.LEADING}),
        GroupKind.WARBAND: frozenset({GroupKindTrait.LEADING}),
        GroupKind.CREW: frozenset(),
        GroupKind.CELL: frozenset({GroupKindTrait.LEADING}),
        GroupKind.BAND: frozenset({GroupKindTrait.LEADING}),
        GroupKind.TEAM: frozenset(),
    },
)


HAZARD_KIND_TRAITS: Mapping[HazardKind, frozenset[HazardKindTrait]] = total(
    HazardKind,
    {
        HazardKind.CAVE_IN: frozenset({HazardKindTrait.WORKS_HAZARDS}),
        HazardKind.FLOODED_SHAFT: frozenset({HazardKindTrait.WORKS_HAZARDS}),
        HazardKind.FELLING_ACCIDENT: frozenset(),
        HazardKind.DROWNING: frozenset(),
        HazardKind.GORING: frozenset(),
        HazardKind.BLOWOUT: frozenset({HazardKindTrait.WORKS_HAZARDS}),
        HazardKind.EXPLOSION: frozenset({HazardKindTrait.WORKS_HAZARDS}),
        HazardKind.TOXIC_RELEASE: frozenset(),
        HazardKind.DECOMPRESSION: frozenset(),
        HazardKind.RADIATION_EXPOSURE: frozenset(),
        HazardKind.SUBSIDENCE: frozenset({HazardKindTrait.WORKS_HAZARDS}),
        HazardKind.BEAST_ATTACK: frozenset(),
        HazardKind.SOURCE_BACKLASH: frozenset(),
        HazardKind.MACHINE_ACCIDENT: frozenset(),
    },
)


HIDDEN_TRUTH_KIND_TRAITS: Mapping[HiddenTruthKind, frozenset[HiddenTruthKindTrait]] = total(
    HiddenTruthKind,
    {
        HiddenTruthKind.EXISTENCE: frozenset(),
        HiddenTruthKind.NATURE: frozenset({HiddenTruthKindTrait.GIFTED_TRUTHS}),
        HiddenTruthKind.PRESENCE: frozenset({HiddenTruthKindTrait.GIFTED_TRUTHS}),
        HiddenTruthKind.POWER: frozenset({HiddenTruthKindTrait.GIFTED_TRUTHS}),
        HiddenTruthKind.EVENT: frozenset(),
        HiddenTruthKind.ORIGIN: frozenset(),
        HiddenTruthKind.AWAKENING: frozenset(),
        HiddenTruthKind.PROGRAMME: frozenset(),
        HiddenTruthKind.COSMIC: frozenset(),
    },
)


HOUSE_DUTY_TRAITS: Mapping[HouseDuty, frozenset[HouseDutyTrait]] = total(
    HouseDuty,
    {
        HouseDuty.FOOD: frozenset(),
        HouseDuty.WATER: frozenset({HouseDutyTrait.SERVED_DUTIES}),
        HouseDuty.FUEL: frozenset({HouseDutyTrait.SERVED_DUTIES}),
        HouseDuty.CLEANING: frozenset({HouseDutyTrait.SERVED_DUTIES}),
        HouseDuty.TEXTILES: frozenset(),
        HouseDuty.CHILDCARE: frozenset({HouseDutyTrait.CARE_DUTIES}),
        HouseDuty.ELDERCARE: frozenset({HouseDutyTrait.CARE_DUTIES}),
        HouseDuty.ANIMALS: frozenset(),
        HouseDuty.REPAIRS: frozenset(),
        HouseDuty.SICKCARE: frozenset({HouseDutyTrait.CARE_DUTIES}),
        HouseDuty.HOUSEHOLD_RITES: frozenset(),
    },
)


IDENTITY_LAYER_TRAITS: Mapping[IdentityLayer, frozenset[IdentityLayerTrait]] = total(
    IdentityLayer,
    {
        IdentityLayer.PEOPLE: frozenset(),
        IdentityLayer.FAITH: frozenset(),
        IdentityLayer.CLASS: frozenset(),
        IdentityLayer.LOCALITY: frozenset({IdentityLayerTrait.GROUP_LAYERS}),
        IdentityLayer.HOUSE: frozenset({IdentityLayerTrait.GROUP_LAYERS}),
        IdentityLayer.PROFESSION: frozenset({IdentityLayerTrait.GROUP_LAYERS}),
        IdentityLayer.GENERATION: frozenset(),
        IdentityLayer.POLITY: frozenset(),
        IdentityLayer.CIRCLE: frozenset({IdentityLayerTrait.GROUP_LAYERS}),
        IdentityLayer.LANGUAGE: frozenset(),
        IdentityLayer.KIND: frozenset(),
        IdentityLayer.CAUSE: frozenset({IdentityLayerTrait.GROUP_LAYERS}),
    },
)


INHERITANCE_CUSTOM_TRAITS: Mapping[InheritanceCustom, frozenset[InheritanceCustomTrait]] = total(
    InheritanceCustom,
    {
        InheritanceCustom.EQUAL_SHARES: frozenset({InheritanceCustomTrait.DISCRETION}),
        InheritanceCustom.PRIMOGENITURE: frozenset(),
        InheritanceCustom.ULTIMOGENITURE: frozenset(),
        InheritanceCustom.THROUGH_SECOND_LINE: frozenset(),
        InheritanceCustom.ELECTIVE: frozenset({InheritanceCustomTrait.DISCRETION}),
        InheritanceCustom.BY_MERIT: frozenset({InheritanceCustomTrait.DISCRETION}),
        InheritanceCustom.SENIORITY: frozenset(),
        InheritanceCustom.DESIGNATED: frozenset({InheritanceCustomTrait.DISCRETION}),
    },
)


INTERACTION_KIND_TRAITS: Mapping[InteractionKind, frozenset[InteractionKindTrait]] = total(
    InteractionKind,
    {
        InteractionKind.CONVERSE: frozenset({InteractionKindTrait.FRIENDLY_TALK}),
        InteractionKind.BEFRIEND: frozenset({InteractionKindTrait.FRIENDLY_TALK}),
        InteractionKind.GOSSIP: frozenset(),
        InteractionKind.JOKE: frozenset({InteractionKindTrait.FRIENDLY_TALK}),
        InteractionKind.COMFORT: frozenset(),
        InteractionKind.FLATTER: frozenset(),
        InteractionKind.BOAST: frozenset(),
        InteractionKind.INSULT: frozenset(),
        InteractionKind.ARGUE: frozenset(),
        InteractionKind.FLIRT: frozenset(),
        InteractionKind.COURT: frozenset(),
        InteractionKind.PROPOSE: frozenset(),
        InteractionKind.SEDUCE: frozenset(),
        InteractionKind.QUARREL: frozenset(),
        InteractionKind.RECONCILE: frozenset(),
        InteractionKind.TEACH: frozenset(),
        InteractionKind.GIFT: frozenset({InteractionKindTrait.TALK_FREE}),
        InteractionKind.ASK_FAVOUR: frozenset(),
        InteractionKind.CONFIDE_SECRET: frozenset({InteractionKindTrait.FRIENDLY_TALK}),
        InteractionKind.THREATEN: frozenset(),
        InteractionKind.BRAWL: frozenset({InteractionKindTrait.TALK_FREE}),
        InteractionKind.APOLOGISE: frozenset({InteractionKindTrait.FRIENDLY_TALK}),
        InteractionKind.SHARE_MEAL: frozenset({InteractionKindTrait.FRIENDLY_TALK, InteractionKindTrait.TALK_FREE}),
        InteractionKind.ASK_COUNSEL: frozenset({InteractionKindTrait.FRIENDLY_TALK}),
    },
)


INTOXICANT_TRAITS: Mapping[Intoxicant, frozenset[IntoxicantTrait]] = total(
    Intoxicant,
    {
        Intoxicant.BREW: frozenset({IntoxicantTrait.DRINKS}),
        Intoxicant.WINE: frozenset({IntoxicantTrait.DRINKS}),
        Intoxicant.SPIRITS: frozenset({IntoxicantTrait.DRINKS}),
        Intoxicant.SMOKE: frozenset(),
        Intoxicant.LEAF: frozenset({IntoxicantTrait.STIMULATES}),
        Intoxicant.FUNGUS: frozenset(),
        Intoxicant.ESSENCE: frozenset(),
        Intoxicant.SYNTHETIC: frozenset({IntoxicantTrait.STIMULATES}),
        Intoxicant.ANIMAL_DERIVED: frozenset(),
    },
)


JOB_TRAITS: Mapping[Job, frozenset[JobTrait]] = total(
    Job,
    {
        Job.FARMING: frozenset({JobTrait.BOUND_JOBS}),
        Job.HERDING: frozenset({JobTrait.BOUND_JOBS}),
        Job.FISHING: frozenset(),
        Job.MINING: frozenset({JobTrait.BOUND_JOBS}),
        Job.CRAFTING: frozenset({JobTrait.MADE_MIND_TRADES}),
        Job.TRADE: frozenset(),
        Job.SOLDIERING: frozenset(),
        Job.CLERGY: frozenset(),
        Job.SCHOLARSHIP: frozenset({JobTrait.MADE_MIND_TRADES}),
        Job.BUILDING: frozenset({JobTrait.BOUND_JOBS}),
        Job.SERVICE: frozenset({JobTrait.MADE_MIND_TRADES}),
        Job.IDLE: frozenset(),
        Job.TRANSPORT: frozenset(),
        Job.ADMINISTRATION: frozenset({JobTrait.MADE_MIND_TRADES}),
        Job.GATHERING: frozenset(),
        Job.INDUSTRY: frozenset({JobTrait.BOUND_JOBS, JobTrait.MADE_MIND_TRADES}),
        Job.ARTS: frozenset(),
    },
)


JOURNEY_INTENT_TRAITS: Mapping[JourneyIntent, frozenset[JourneyIntentTrait]] = total(
    JourneyIntent,
    {
        JourneyIntent.COLONY: frozenset({JourneyIntentTrait.CROWD_INTENTS, JourneyIntentTrait.PASSENGER_INTENTS, JourneyIntentTrait.SURVEYING}),
        JourneyIntent.TRADE: frozenset({JourneyIntentTrait.SURVEYING}),
        JourneyIntent.EXPLORATION: frozenset({JourneyIntentTrait.SURVEYING}),
        JourneyIntent.CONQUEST: frozenset({JourneyIntentTrait.CROWD_INTENTS, JourneyIntentTrait.PASSENGER_INTENTS, JourneyIntentTrait.SURVEYING}),
        JourneyIntent.PILGRIMAGE: frozenset({JourneyIntentTrait.PASSENGER_INTENTS, JourneyIntentTrait.SURVEYING}),
    },
)


KNOWLEDGE_BRANCH_TRAITS: Mapping[KnowledgeBranch, frozenset[KnowledgeBranchTrait]] = total(
    KnowledgeBranch,
    {
        KnowledgeBranch.AGRICULTURE: frozenset({KnowledgeBranchTrait.CRAFT_BRANCHES, KnowledgeBranchTrait.NATURAL_BRANCHES}),
        KnowledgeBranch.METALLURGY: frozenset({KnowledgeBranchTrait.CRAFT_BRANCHES, KnowledgeBranchTrait.NATURAL_BRANCHES}),
        KnowledgeBranch.SEAFARING: frozenset(
            {
                KnowledgeBranchTrait.EXPLORATION_BRANCHES,
                KnowledgeBranchTrait.KNOWLEDGE_FOR_EXPLORING,
                KnowledgeBranchTrait.NATURAL_BRANCHES,
                KnowledgeBranchTrait.RECKONED,
            }
        ),
        KnowledgeBranch.WRITING: frozenset(),
        KnowledgeBranch.ARCHITECTURE: frozenset({KnowledgeBranchTrait.CRAFT_BRANCHES, KnowledgeBranchTrait.RECKONED}),
        KnowledgeBranch.MEDICINE: frozenset({KnowledgeBranchTrait.NATURAL_BRANCHES}),
        KnowledgeBranch.MAGIC: frozenset({KnowledgeBranchTrait.ROAD_BRANCHES}),
        KnowledgeBranch.WARFARE: frozenset(),
        KnowledgeBranch.ASTRONOMY: frozenset(
            {
                KnowledgeBranchTrait.EXPLORATION_BRANCHES,
                KnowledgeBranchTrait.KNOWLEDGE_FOR_EXPLORING,
                KnowledgeBranchTrait.NATURAL_BRANCHES,
                KnowledgeBranchTrait.RECKONED,
            }
        ),
        KnowledgeBranch.TRADE: frozenset({KnowledgeBranchTrait.CRAFT_BRANCHES, KnowledgeBranchTrait.RECKONED}),
        KnowledgeBranch.SKY_NAVIGATION: frozenset({KnowledgeBranchTrait.KNOWLEDGE_FOR_EXPLORING, KnowledgeBranchTrait.ROAD_BRANCHES}),
        KnowledgeBranch.SHIPBUILDING: frozenset(),
        KnowledgeBranch.GATE_LORE: frozenset({KnowledgeBranchTrait.ROAD_BRANCHES}),
        KnowledgeBranch.PATHFINDING: frozenset(
            {KnowledgeBranchTrait.EXPLORATION_BRANCHES, KnowledgeBranchTrait.KNOWLEDGE_FOR_EXPLORING, KnowledgeBranchTrait.ROAD_BRANCHES}
        ),
        KnowledgeBranch.VOID_LIVING: frozenset(),
        KnowledgeBranch.IMMORTALITY: frozenset(),
        KnowledgeBranch.BIOMANCY: frozenset(),
        KnowledgeBranch.FORBIDDEN: frozenset(),
        KnowledgeBranch.CIVICS: frozenset(),
    },
)


LAND_ACT_TRAITS: Mapping[LandAct, frozenset[LandActTrait]] = total(
    LandAct,
    {
        LandAct.SHIFT_RIVER: frozenset({LandActTrait.SOIL_ACTS}),
        LandAct.PARCH: frozenset({LandActTrait.FEARED, LandActTrait.SOIL_ACTS}),
        LandAct.GREEN: frozenset({LandActTrait.SOIL_ACTS, LandActTrait.WELCOMED}),
        LandAct.MAKE_SALINE: frozenset({LandActTrait.FEARED, LandActTrait.SOIL_ACTS}),
        LandAct.ENRICH_SOIL: frozenset({LandActTrait.SOIL_ACTS, LandActTrait.WELCOMED}),
        LandAct.RAISE_LAND: frozenset({LandActTrait.LIFTS, LandActTrait.WELCOMED}),
        LandAct.LOWER_LAND: frozenset({LandActTrait.LIFTS}),
        LandAct.CARVE_VALLEY: frozenset({LandActTrait.LIFTS}),
        LandAct.FILL_VALLEY: frozenset({LandActTrait.LIFTS}),
        LandAct.OPEN_SPRING: frozenset({LandActTrait.WELCOMED}),
        LandAct.CALL_LAVA: frozenset({LandActTrait.FEARED}),
        LandAct.SINK_COAST: frozenset({LandActTrait.FEARED}),
    },
)


LEISURE_KIND_TRAITS: Mapping[LeisureKind, frozenset[LeisureKindTrait]] = total(
    LeisureKind,
    {
        LeisureKind.CONVERSATION: frozenset(),
        LeisureKind.GAMES: frozenset(),
        LeisureKind.SPORT: frozenset(),
        LeisureKind.MUSIC: frozenset(),
        LeisureKind.CRAFTS: frozenset(),
        LeisureKind.COLLECTING: frozenset(),
        LeisureKind.READING: frozenset(),
        LeisureKind.EXCURSION: frozenset({LeisureKindTrait.TRAVEL_PURSUITS}),
        LeisureKind.TOURISM: frozenset({LeisureKindTrait.TRAVEL_PURSUITS}),
        LeisureKind.DRINKING: frozenset(),
        LeisureKind.WORSHIP_EXTRA: frozenset(),
        LeisureKind.REST: frozenset(),
        LeisureKind.MEDIA: frozenset(),
        LeisureKind.DANCE: frozenset(),
        LeisureKind.STORYTELLING: frozenset(),
        LeisureKind.HUNTING: frozenset({LeisureKindTrait.TRAVEL_PURSUITS}),
    },
)


LIFE_STAGE_TRAITS: Mapping[LifeStage, frozenset[LifeStageTrait]] = total(
    LifeStage,
    {
        LifeStage.INFANT: frozenset({LifeStageTrait.CARED_FOR, LifeStageTrait.DUTIES_YOUNG, LifeStageTrait.GROWING}),
        LifeStage.CHILD: frozenset({LifeStageTrait.CARED_FOR, LifeStageTrait.DUTIES_YOUNG, LifeStageTrait.GROWING, LifeStageTrait.YOUNG}),
        LifeStage.YOUTH: frozenset({LifeStageTrait.GROWING, LifeStageTrait.YOUNG}),
        LifeStage.ADULT: frozenset({LifeStageTrait.GROWN}),
        LifeStage.ELDER: frozenset({LifeStageTrait.CARED_FOR, LifeStageTrait.GROWN, LifeStageTrait.OLD}),
        LifeStage.ANCIENT: frozenset({LifeStageTrait.CARED_FOR, LifeStageTrait.GROWN, LifeStageTrait.OLD}),
    },
)


LINE_TRAIT_TRAITS: Mapping[LineTrait, frozenset[LineTraitTrait]] = total(
    LineTrait,
    {
        LineTrait.YIELD: frozenset({LineTraitTrait.SHAPING_TRAITS}),
        LineTrait.HARDINESS: frozenset({LineTraitTrait.SHAPING_TRAITS}),
        LineTrait.CLIMATE_TOLERANCE: frozenset({LineTraitTrait.SHAPING_TRAITS}),
        LineTrait.DISEASE_RESISTANCE: frozenset(),
        LineTrait.STRENGTH: frozenset(),
        LineTrait.SPEED: frozenset(),
        LineTrait.SIZE: frozenset(),
        LineTrait.REGENERATION: frozenset(),
        LineTrait.LIFESPAN: frozenset(),
        LineTrait.DOCILITY: frozenset(),
        LineTrait.POTENCY: frozenset(),
        LineTrait.FIBRE: frozenset(),
        LineTrait.VENOM: frozenset(),
        LineTrait.FLIGHT: frozenset({LineTraitTrait.SPREADING}),
        LineTrait.AQUATIC: frozenset({LineTraitTrait.SPREADING}),
        LineTrait.VOID_HARDY: frozenset({LineTraitTrait.SPREADING}),
        LineTrait.GIFT: frozenset(),
        LineTrait.NERVOUS_SYSTEM: frozenset(),
        LineTrait.SAPIENCE: frozenset(),
    },
)


MADE_MIND_STANCE_TRAITS: Mapping[MadeMindStance, frozenset[MadeMindStanceTrait]] = total(
    MadeMindStance,
    {
        MadeMindStance.ABOMINATION: frozenset(),
        MadeMindStance.TOOL: frozenset(),
        MadeMindStance.KIN: frozenset({MadeMindStanceTrait.KEEPING_STANCES}),
        MadeMindStance.SACRED: frozenset({MadeMindStanceTrait.KEEPING_STANCES}),
        MadeMindStance.SILENT: frozenset(),
    },
)


MEDIUM_TRAITS: Mapping[Medium, frozenset[MediumTrait]] = total(
    Medium,
    {
        Medium.ENVOY: frozenset({MediumTrait.OVERLAND}),
        Medium.LETTER: frozenset({MediumTrait.OVERLAND}),
        Medium.HERALD: frozenset({MediumTrait.OPEN_MEDIA, MediumTrait.OVERLAND}),
        Medium.SIGNAL_FIRE: frozenset(),
        Medium.DREAM: frozenset({MediumTrait.INSTANT}),
        Medium.BIRD: frozenset(),
        Medium.MAGIC_SENDING: frozenset({MediumTrait.INSTANT}),
        Medium.NETWORK: frozenset(),
        Medium.MIND_LINK: frozenset({MediumTrait.INSTANT}),
        Medium.BROADCAST: frozenset({MediumTrait.INSTANT, MediumTrait.OPEN_MEDIA}),
    },
)


MEMORY_KIND_TRAITS: Mapping[MemoryKind, frozenset[MemoryKindTrait]] = total(
    MemoryKind,
    {
        MemoryKind.HARMED_ME: frozenset({MemoryKindTrait.HARMS, MemoryKindTrait.TRAUMA_KINDS}),
        MemoryKind.KILLED_KIN: frozenset({MemoryKindTrait.GRIEVANCES, MemoryKindTrait.TRAUMA_KINDS}),
        MemoryKind.SAVED_ME: frozenset({MemoryKindTrait.CARES}),
        MemoryKind.BETRAYED_ME: frozenset({MemoryKindTrait.GRIEVANCES, MemoryKindTrait.HARMS, MemoryKindTrait.TRAUMA_KINDS}),
        MemoryKind.KEPT_OATH: frozenset(),
        MemoryKind.BROKE_OATH: frozenset(),
        MemoryKind.MAIMED_ME: frozenset({MemoryKindTrait.HARMS, MemoryKindTrait.TRAUMA_KINDS}),
        MemoryKind.HUMILIATED_ME: frozenset({MemoryKindTrait.HARMS, MemoryKindTrait.TRAUMA_KINDS}),
        MemoryKind.GIFTED_ME: frozenset({MemoryKindTrait.CARES}),
        MemoryKind.CONVERTED_ME: frozenset(),
        MemoryKind.CONQUERED_US: frozenset(),
        MemoryKind.FREED_US: frozenset({MemoryKindTrait.CARES}),
        MemoryKind.FAMINE_AID: frozenset(),
        MemoryKind.DESECRATED_HOLY: frozenset(),
        MemoryKind.MARRIED_INTO: frozenset(),
        MemoryKind.FOUGHT_US: frozenset(),
        MemoryKind.TRADED_WITH: frozenset(),
        MemoryKind.ALLIED_WITH: frozenset(),
        MemoryKind.MADE_PEACE: frozenset(),
        MemoryKind.DEMANDED_TRIBUTE: frozenset(),
        MemoryKind.CHEATED_US: frozenset(),
        MemoryKind.SPIED_ON_US: frozenset(),
        MemoryKind.ENVIED: frozenset(),
        MemoryKind.FAILED_TO_HEAL: frozenset(),
        MemoryKind.TAUGHT_ME: frozenset({MemoryKindTrait.CARES}),
        MemoryKind.HELD_CAPTIVE: frozenset({MemoryKindTrait.TRAUMA_KINDS}),
        MemoryKind.LAMENTED: frozenset(),
        MemoryKind.DIVINE_WILL: frozenset(),
        MemoryKind.GOODWILL: frozenset(),
        MemoryKind.ILL_WILL: frozenset({MemoryKindTrait.GRIEVANCES}),
        MemoryKind.LONG_HISTORY: frozenset(),
        MemoryKind.DREADS: frozenset(),
        MemoryKind.FORMATIVE: frozenset({MemoryKindTrait.TRAUMA_KINDS}),
        MemoryKind.STOLE_FAITHFUL: frozenset(),
        MemoryKind.AIDED_CHOSEN: frozenset(),
        MemoryKind.MEMORY_GAP: frozenset(),
        MemoryKind.COMPELLED_ME: frozenset(),
    },
)


METABOLISM_TRAITS: Mapping[Metabolism, frozenset[MetabolismTrait]] = total(
    Metabolism,
    {
        Metabolism.FEEDING: frozenset(),
        Metabolism.LIGHT: frozenset({MetabolismTrait.SELF_FED}),
        Metabolism.CHEMICAL: frozenset(),
        Metabolism.HOST: frozenset(),
        Metabolism.SOURCE: frozenset({MetabolismTrait.SELF_FED}),
        Metabolism.PARTNER: frozenset({MetabolismTrait.SELF_FED}),
        Metabolism.DORMANT: frozenset(),
    },
)


MIND_UPKEEP_TRAITS: Mapping[MindUpkeep, frozenset[MindUpkeepTrait]] = total(
    MindUpkeep,
    {
        MindUpkeep.FOOD: frozenset({MindUpkeepTrait.SELF_KEPT}),
        MindUpkeep.ENERGY: frozenset(),
        MindUpkeep.ESSENCE: frozenset(),
        MindUpkeep.VIS: frozenset(),
        MindUpkeep.BELIEF: frozenset(),
        MindUpkeep.MAINTENANCE: frozenset(),
        MindUpkeep.HOST: frozenset(),
        MindUpkeep.PLACE: frozenset({MindUpkeepTrait.REALMS_SELF_KEPT}),
        MindUpkeep.NONE: frozenset({MindUpkeepTrait.REALMS_SELF_KEPT, MindUpkeepTrait.SELF_KEPT}),
    },
)


MISHAP_KIND_TRAITS: Mapping[MishapKind, frozenset[MishapKindTrait]] = total(
    MishapKind,
    {
        MishapKind.ILLNESS: frozenset(),
        MishapKind.CROP_FAILURE: frozenset(),
        MishapKind.CHILD_DEATH: frozenset(),
        MishapKind.LIVESTOCK_DEATH: frozenset(),
        MishapKind.ACCIDENT: frozenset(),
        MishapKind.BAD_LUCK: frozenset(),
        MishapKind.FALL: frozenset(),
        MishapKind.CRUSH: frozenset(),
        MishapKind.CUT: frozenset(),
        MishapKind.BURN: frozenset(),
        MishapKind.SCALD: frozenset(),
        MishapKind.DROWNING: frozenset(),
        MishapKind.BEAST: frozenset(),
        MishapKind.TOOL: frozenset(),
        MishapKind.MACHINE: frozenset(),
        MishapKind.VEHICLE: frozenset(),
        MishapKind.COLLAPSE: frozenset(),
        MishapKind.HOUSE_FIRE: frozenset(),
        MishapKind.POISONING: frozenset(),
        MishapKind.CHOKING: frozenset(),
        MishapKind.EXPOSURE: frozenset(),
        MishapKind.LIGHTNING: frozenset(),
        MishapKind.SPORT: frozenset(),
        MishapKind.BRAWL: frozenset(),
        MishapKind.LOST_WAY: frozenset({MishapKindTrait.FRIGHTS}),
        MishapKind.STORES_SPOILED: frozenset({MishapKindTrait.LOSSES}),
        MishapKind.GOODS_LOST: frozenset({MishapKindTrait.LOSSES}),
        MishapKind.PURSE_LOST: frozenset({MishapKindTrait.LOSSES}),
        MishapKind.THEFT_SUFFERED: frozenset({MishapKindTrait.LOSSES}),
        MishapKind.TOOL_BROKEN: frozenset({MishapKindTrait.LOSSES}),
        MishapKind.NEAR_MISS: frozenset({MishapKindTrait.FRIGHTS}),
    },
)


OATH_KIND_TRAITS: Mapping[OathKind, frozenset[OathKindTrait]] = total(
    OathKind,
    {
        OathKind.FEALTY: frozenset({OathKindTrait.LOYAL_OATHS}),
        OathKind.VENGEANCE: frozenset({OathKindTrait.TIMED}),
        OathKind.CELIBACY: frozenset(),
        OathKind.PILGRIMAGE: frozenset({OathKindTrait.TIMED}),
        OathKind.PROTECTION: frozenset({OathKindTrait.LOYAL_OATHS}),
        OathKind.SILENCE: frozenset(),
        OathKind.SWORN_KINSHIP: frozenset({OathKindTrait.LOYAL_OATHS}),
        OathKind.SERVICE: frozenset(),
        OathKind.POVERTY: frozenset(),
        OathKind.NONVIOLENCE: frozenset(),
        OathKind.FIDELITY: frozenset(),
        OathKind.SECRECY: frozenset(),
        OathKind.TESTIMONY: frozenset(),
    },
)


OBSERVATION_METHOD_TRAITS: Mapping[ObservationMethod, frozenset[ObservationMethodTrait]] = total(
    ObservationMethod,
    {
        ObservationMethod.SIGHT: frozenset({ObservationMethodTrait.TRUSTED_BY_FAITH}),
        ObservationMethod.LORE: frozenset({ObservationMethodTrait.TRUSTED_BY_FAITH}),
        ObservationMethod.ALMANAC: frozenset({ObservationMethodTrait.TRUSTED_BY_FAITH}),
        ObservationMethod.INSTRUMENT: frozenset(),
        ObservationMethod.NETWORK_OF_OBSERVERS: frozenset(),
        ObservationMethod.MODEL: frozenset(),
        ObservationMethod.NETWORK: frozenset(),
        ObservationMethod.POWER: frozenset({ObservationMethodTrait.TRUSTED_BY_FAITH}),
        ObservationMethod.DIVINATION: frozenset({ObservationMethodTrait.TRUSTED_BY_FAITH}),
    },
)


OFFICE_DUTY_TRAITS: Mapping[OfficeDuty, frozenset[OfficeDutyTrait]] = total(
    OfficeDuty,
    {
        OfficeDuty.THE_DEAD: frozenset(),
        OfficeDuty.THRESHOLDS: frozenset(),
        OfficeDuty.THE_SKY: frozenset({OfficeDutyTrait.DUTY_TOWNS, OfficeDutyTrait.PIETY_DUTIES}),
        OfficeDuty.OATHS: frozenset({OfficeDutyTrait.DUTY_TOWNS, OfficeDutyTrait.UNREST_DUTIES}),
        OfficeDuty.MESSAGES: frozenset({OfficeDutyTrait.DUTY_TOWNS, OfficeDutyTrait.PIETY_DUTIES}),
        OfficeDuty.THE_HUNT: frozenset(),
        OfficeDuty.JUDGEMENT: frozenset({OfficeDutyTrait.DUTY_TOWNS, OfficeDutyTrait.UNREST_DUTIES}),
        OfficeDuty.MEMORY: frozenset({OfficeDutyTrait.DUTY_TOWNS, OfficeDutyTrait.PIETY_DUTIES}),
        OfficeDuty.MAKING: frozenset({OfficeDutyTrait.DUTY_TOWNS}),
        OfficeDuty.HEALING: frozenset({OfficeDutyTrait.DUTY_TOWNS}),
    },
)


OFFICE_KIND_TRAITS: Mapping[OfficeKind, frozenset[OfficeKindTrait]] = total(
    OfficeKind,
    {
        OfficeKind.RULER: frozenset({OfficeKindTrait.KEPT_OFFICES, OfficeKindTrait.SEATS_KEPT}),
        OfficeKind.HEIR_DESIGNATE: frozenset({OfficeKindTrait.SEATS_KEPT}),
        OfficeKind.REGENT: frozenset({OfficeKindTrait.COUNCIL, OfficeKindTrait.SEATS_KEPT}),
        OfficeKind.CHANCELLOR: frozenset({OfficeKindTrait.COUNCIL}),
        OfficeKind.MARSHAL: frozenset({OfficeKindTrait.COUNCIL}),
        OfficeKind.TREASURER: frozenset({OfficeKindTrait.COUNCIL}),
        OfficeKind.HIGH_JUDGE: frozenset({OfficeKindTrait.COUNCIL}),
        OfficeKind.SPYMASTER: frozenset({OfficeKindTrait.COUNCIL, OfficeKindTrait.KEPT_OFFICES}),
        OfficeKind.GOVERNOR: frozenset(),
        OfficeKind.AMBASSADOR: frozenset(),
        OfficeKind.HERALD: frozenset(),
        OfficeKind.CHAPLAIN: frozenset({OfficeKindTrait.COUNCIL}),
        OfficeKind.COURT_SCHOLAR: frozenset(),
        OfficeKind.HEAD_OF_STATE: frozenset(),
        OfficeKind.HEAD_OF_GOVERNMENT: frozenset({OfficeKindTrait.COUNCIL}),
        OfficeKind.MINISTER: frozenset({OfficeKindTrait.COUNCIL, OfficeKindTrait.MANY_SEATS}),
        OfficeKind.GENERAL: frozenset({OfficeKindTrait.COUNCIL, OfficeKindTrait.MANY_SEATS}),
        OfficeKind.ADMIRAL: frozenset({OfficeKindTrait.MANY_SEATS}),
        OfficeKind.SPEAKER: frozenset({OfficeKindTrait.COUNCIL}),
        OfficeKind.CHIEF_SCIENTIST: frozenset(),
        OfficeKind.JESTER: frozenset(),
        OfficeKind.WARDEN: frozenset(),
    },
)


ORDER_KIND_TRAITS: Mapping[OrderKind, frozenset[OrderKindTrait]] = total(
    OrderKind,
    {
        OrderKind.GUARD: frozenset({OrderKindTrait.TARGETED_ORDERS, OrderKindTrait.WEAPON_ORDERS}),
        OrderKind.SERVE: frozenset(),
        OrderKind.OBEY_HOLDER: frozenset(),
        OrderKind.BUILD: frozenset(),
        OrderKind.GATHER: frozenset(),
        OrderKind.PROTECT: frozenset({OrderKindTrait.TARGETED_ORDERS}),
        OrderKind.DESTROY: frozenset({OrderKindTrait.TARGETED_ORDERS, OrderKindTrait.WEAPON_ORDERS}),
        OrderKind.REPORT: frozenset(),
        OrderKind.MAINTAIN: frozenset(),
        OrderKind.REPLICATE: frozenset(),
        OrderKind.HOLD_STILL: frozenset(),
        OrderKind.FOLLOW: frozenset({OrderKindTrait.TARGETED_ORDERS}),
        OrderKind.FORBID: frozenset(),
    },
)


PACKAGE_KIND_TRAITS: Mapping[PackageKind, frozenset[PackageKindTrait]] = total(
    PackageKind,
    {
        PackageKind.SNAKE_VENOM: frozenset(),
        PackageKind.DRINK_DEPENDENCE: frozenset(),
        PackageKind.DRUG_DEPENDENCE: frozenset(),
        PackageKind.LYCANTHROPY: frozenset({PackageKindTrait.BEAST_CURSES}),
        PackageKind.VAMPIRISM: frozenset(),
        PackageKind.DIVINE_BLESSING: frozenset(),
        PackageKind.VOID_TAINT: frozenset(),
        PackageKind.POSSESSION: frozenset(),
        PackageKind.TRAUMA: frozenset(),
        PackageKind.HUNGER_CURSE: frozenset({PackageKindTrait.BEAST_CURSES}),
        PackageKind.WARPING: frozenset({PackageKindTrait.BEAST_CURSES}),
        PackageKind.VIS_DEPENDENCE: frozenset(),
        PackageKind.GEAS_DOOM: frozenset(),
        PackageKind.SOUL_TRAPPED: frozenset(),
        PackageKind.FORTUNE: frozenset(),
        PackageKind.TRANSFORMATION: frozenset(),
        PackageKind.CHARM: frozenset(),
    },
)


PASSION_KIND_TRAITS: Mapping[PassionKind, frozenset[PassionKindTrait]] = total(
    PassionKind,
    {
        PassionKind.LOVE: frozenset({PassionKindTrait.TENDER}),
        PassionKind.LOYALTY: frozenset({PassionKindTrait.TENDER}),
        PassionKind.HATRED: frozenset(),
        PassionKind.DEVOTION: frozenset({PassionKindTrait.TENDER}),
        PassionKind.AMBITION: frozenset(),
        PassionKind.ENVY: frozenset(),
        PassionKind.GRIEF: frozenset(),
        PassionKind.CURIOSITY: frozenset(),
        PassionKind.FEAR: frozenset(),
        PassionKind.SHAME: frozenset(),
        PassionKind.PRIDE: frozenset(),
        PassionKind.JEALOUSY: frozenset(),
        PassionKind.ADMIRATION: frozenset(),
        PassionKind.OBSESSION: frozenset(),
    },
)


POPULATION_INSTRUMENT_TRAITS: Mapping[PopulationInstrument, frozenset[PopulationInstrumentTrait]] = total(
    PopulationInstrument,
    {
        PopulationInstrument.BIRTH_REWARD: frozenset(),
        PopulationInstrument.BIRTH_TAX: frozenset(),
        PopulationInstrument.UNION_LAW: frozenset(),
        PopulationInstrument.CHILD_LIMIT: frozenset({PopulationInstrumentTrait.HARSH}),
        PopulationInstrument.CHILD_SUPPORT: frozenset(),
        PopulationInstrument.INHERITANCE_RULE: frozenset(),
        PopulationInstrument.SETTLEMENT_GRANT: frozenset({PopulationInstrumentTrait.PULLS}),
        PopulationInstrument.MIGRATION_PERMIT: frozenset({PopulationInstrumentTrait.PULLS}),
        PopulationInstrument.MIGRATION_BAN: frozenset(),
        PopulationInstrument.EXPULSION: frozenset({PopulationInstrumentTrait.HARSH}),
        PopulationInstrument.RESETTLEMENT: frozenset(),
        PopulationInstrument.RECRUITMENT_ABROAD: frozenset({PopulationInstrumentTrait.PULLS}),
        PopulationInstrument.HEALTH_CAMPAIGN: frozenset(),
        PopulationInstrument.FAITH_TEACHING: frozenset(),
        PopulationInstrument.MADE_BIRTH: frozenset(),
    },
)


POWER_ORIGIN_TRAITS: Mapping[PowerOrigin, frozenset[PowerOriginTrait]] = total(
    PowerOrigin,
    {
        PowerOrigin.BORN: frozenset({PowerOriginTrait.BORN_ORIGINS, PowerOriginTrait.GIFTED_ORIGINS}),
        PowerOrigin.AWAKENED: frozenset({PowerOriginTrait.GIFTED_ORIGINS}),
        PowerOrigin.EXPOSURE: frozenset({PowerOriginTrait.GIFTED_ORIGINS}),
        PowerOrigin.GRANTED: frozenset(),
        PowerOrigin.BONDED: frozenset(),
        PowerOrigin.DISCIPLINE: frozenset(),
        PowerOrigin.MADE: frozenset(),
        PowerOrigin.GROWN: frozenset(),
        PowerOrigin.BLOODLINE: frozenset({PowerOriginTrait.BORN_ORIGINS, PowerOriginTrait.GIFTED_ORIGINS}),
        PowerOrigin.HELD: frozenset(),
    },
)


POWER_STATE_TRAITS: Mapping[PowerState, frozenset[PowerStateTrait]] = total(
    PowerState,
    {
        PowerState.LATENT: frozenset({PowerStateTrait.QUIET}),
        PowerState.EMERGING: frozenset({PowerStateTrait.USABLE}),
        PowerState.ACTIVE: frozenset({PowerStateTrait.USABLE}),
        PowerState.STRAINED: frozenset({PowerStateTrait.USABLE}),
        PowerState.EXHAUSTED: frozenset({PowerStateTrait.QUIET}),
        PowerState.SUPPRESSED: frozenset({PowerStateTrait.QUIET}),
        PowerState.LOST: frozenset({PowerStateTrait.QUIET}),
    },
)


PREPAREDNESS_KIND_TRAITS: Mapping[PreparednessKind, frozenset[PreparednessKindTrait]] = total(
    PreparednessKind,
    {
        PreparednessKind.LEVEE: frozenset(),
        PreparednessKind.FIREBREAK: frozenset({PreparednessKindTrait.FIRE_SHIELDS}),
        PreparednessKind.STOCKPILE: frozenset(),
        PreparednessKind.DRILL: frozenset(),
        PreparednessKind.WATCHTOWER: frozenset(),
        PreparednessKind.SEAWALL: frozenset(),
        PreparednessKind.QUARANTINE_PLAN: frozenset(),
        PreparednessKind.SHELTERS: frozenset(),
        PreparednessKind.WARNING_NETWORK: frozenset(),
        PreparednessKind.EVACUATION_ROUTES: frozenset({PreparednessKindTrait.FIRE_SHIELDS}),
        PreparednessKind.WARD: frozenset({PreparednessKindTrait.FIRE_SHIELDS}),
        PreparednessKind.RESERVES_OF_ENERGY: frozenset(),
    },
)


PUNISHMENT_KIND_TRAITS: Mapping[PunishmentKind, frozenset[PunishmentKindTrait]] = total(
    PunishmentKind,
    {
        PunishmentKind.FINE: frozenset(),
        PunishmentKind.FLOGGING: frozenset(),
        PunishmentKind.EXILE: frozenset(),
        PunishmentKind.BRANDING: frozenset(),
        PunishmentKind.HAND: frozenset(),
        PunishmentKind.TONGUE: frozenset(),
        PunishmentKind.EYES: frozenset(),
        PunishmentKind.DEATH: frozenset(),
        PunishmentKind.PUBLIC_SHAMING: frozenset(),
        PunishmentKind.IMPRISONMENT: frozenset(),
        PunishmentKind.REMAKING: frozenset(),
        PunishmentKind.FORCED_DORMANCY: frozenset({PunishmentKindTrait.MIND_PUNISHMENTS}),
        PunishmentKind.FORCED_EDIT: frozenset({PunishmentKindTrait.MIND_PUNISHMENTS}),
        PunishmentKind.SEAT_CONFINEMENT: frozenset({PunishmentKindTrait.MIND_PUNISHMENTS}),
        PunishmentKind.STATE_SEIZURE: frozenset({PunishmentKindTrait.MIND_PUNISHMENTS}),
        PunishmentKind.ERASURE: frozenset({PunishmentKindTrait.MIND_PUNISHMENTS}),
        PunishmentKind.RESTITUTION: frozenset(),
        PunishmentKind.COMPENSATION: frozenset(),
        PunishmentKind.PENAL_LABOUR: frozenset(),
        PunishmentKind.SERVITUDE: frozenset(),
        PunishmentKind.OUTLAWRY: frozenset(),
        PunishmentKind.CONFISCATION: frozenset(),
        PunishmentKind.LOSS_OF_RANK: frozenset(),
        PunishmentKind.EXCOMMUNICATION: frozenset(),
        PunishmentKind.PENANCE: frozenset(),
        PunishmentKind.BANISHMENT_FROM_PLACE: frozenset(),
        PunishmentKind.HOUSE_ARREST: frozenset(),
        PunishmentKind.PROBATION: frozenset(),
        PunishmentKind.REEDUCATION: frozenset(),
        PunishmentKind.TRANSPORTATION: frozenset(),
        PunishmentKind.COMMUNITY_WORK: frozenset(),
        PunishmentKind.DAMPENING: frozenset(),
    },
)


REBUILD_CAUSE_TRAITS: Mapping[RebuildCause, frozenset[RebuildCauseTrait]] = total(
    RebuildCause,
    {
        RebuildCause.FIRE: frozenset({RebuildCauseTrait.SEIZING}),
        RebuildCause.FLOOD: frozenset(),
        RebuildCause.QUAKE: frozenset(),
        RebuildCause.STORM: frozenset(),
        RebuildCause.SACK: frozenset({RebuildCauseTrait.SEIZING}),
        RebuildCause.ERUPTION: frozenset(),
        RebuildCause.SEA_WAVE: frozenset(),
        RebuildCause.LANDSLIDE: frozenset(),
    },
)


RECORD_FORM_TRAITS: Mapping[RecordForm, frozenset[RecordFormTrait]] = total(
    RecordForm,
    {
        RecordForm.WRITTEN: frozenset(),
        RecordForm.PRINTED: frozenset(),
        RecordForm.IMAGE: frozenset({RecordFormTrait.RECORDED_FORMS}),
        RecordForm.SOUND: frozenset({RecordFormTrait.RECORDED_FORMS}),
        RecordForm.MOVING_IMAGE: frozenset({RecordFormTrait.RECORDED_FORMS}),
        RecordForm.SIGNAL: frozenset({RecordFormTrait.RECORDED_FORMS}),
        RecordForm.NETWORK: frozenset({RecordFormTrait.RECORDED_FORMS}),
        RecordForm.LIVING: frozenset({RecordFormTrait.RECORDED_FORMS}),
        RecordForm.CRAFTED: frozenset(),
        RecordForm.MENTAL: frozenset(),
    },
)


REGIONAL_STANDING_TRAITS: Mapping[RegionalStanding, frozenset[RegionalStandingTrait]] = total(
    RegionalStanding,
    {
        RegionalStanding.HEGEMON: frozenset({RegionalStandingTrait.GREAT}),
        RegionalStanding.GREAT_POWER: frozenset({RegionalStandingTrait.GREAT}),
        RegionalStanding.MINOR_POWER: frozenset(),
        RegionalStanding.CLIENT: frozenset(),
        RegionalStanding.NEUTRAL: frozenset(),
    },
)


RELATION_TYPE_TRAITS: Mapping[RelationType, frozenset[RelationTypeTrait]] = total(
    RelationType,
    {
        RelationType.ACQUAINTANCE: frozenset(),
        RelationType.FRIEND: frozenset({RelationTypeTrait.FRIENDLY}),
        RelationType.CLOSE_FRIEND: frozenset({RelationTypeTrait.FRIENDLY}),
        RelationType.BEST_FRIEND: frozenset({RelationTypeTrait.FRIENDLY}),
        RelationType.CONFIDANT: frozenset({RelationTypeTrait.FRIENDLY}),
        RelationType.CRUSH: frozenset(),
        RelationType.LOVER: frozenset(),
        RelationType.EX_LOVER: frozenset(),
        RelationType.SPOUSE: frozenset(),
        RelationType.RIVAL: frozenset(),
        RelationType.NEMESIS: frozenset(),
        RelationType.ENEMY: frozenset(),
        RelationType.MENTOR: frozenset(),
        RelationType.PROTEGE: frozenset(),
        RelationType.COMRADE_IN_ARMS: frozenset(),
        RelationType.DRINKING_COMPANION: frozenset(),
        RelationType.PATRON: frozenset(),
        RelationType.CLIENT: frozenset(),
        RelationType.BETROTHED: frozenset(),
        RelationType.SWORN_KIN: frozenset({RelationTypeTrait.FRIENDLY}),
        RelationType.FOSTER: frozenset({RelationTypeTrait.FRIENDLY}),
    },
)


RIGHT_KIND_TRAITS: Mapping[RightKind, frozenset[RightKindTrait]] = total(
    RightKind,
    {
        RightKind.SONG: frozenset({RightKindTrait.PORTION}),
        RightKind.DANCE: frozenset({RightKindTrait.PORTION}),
        RightKind.STORY: frozenset({RightKindTrait.PORTION}),
        RightKind.RITE: frozenset(),
        RightKind.DESIGN: frozenset({RightKindTrait.COPIED, RightKindTrait.PORTION}),
        RightKind.NAME: frozenset(),
        RightKind.TITLE: frozenset(),
        RightKind.TRADEMARK: frozenset({RightKindTrait.COPIED, RightKindTrait.PORTION}),
        RightKind.MARKET_PRIVILEGE: frozenset({RightKindTrait.COPIED}),
        RightKind.RECIPE: frozenset({RightKindTrait.COPIED, RightKindTrait.PORTION}),
        RightKind.TECHNIQUE: frozenset({RightKindTrait.COPIED, RightKindTrait.PORTION}),
    },
)


RUMOUR_DISTORTION_TRAITS: Mapping[RumourDistortion, frozenset[RumourDistortionTrait]] = total(
    RumourDistortion,
    {
        RumourDistortion.DOER_SWAPPED: frozenset({RumourDistortionTrait.SWAPS}),
        RumourDistortion.TARGET_SWAPPED: frozenset({RumourDistortionTrait.SWAPS}),
        RumourDistortion.AMOUNT_CHANGED: frozenset(),
        RumourDistortion.OUTCOME_CHANGED: frozenset(),
        RumourDistortion.CAUSE_CHANGED: frozenset(),
        RumourDistortion.PLACE_CHANGED: frozenset(),
        RumourDistortion.MOMENT_CHANGED: frozenset(),
        RumourDistortion.STEP_ADDED: frozenset({RumourDistortionTrait.STEP_KINDS}),
        RumourDistortion.STEP_DROPPED: frozenset({RumourDistortionTrait.STEP_KINDS}),
        RumourDistortion.ROLE_CHANGED: frozenset({RumourDistortionTrait.SWAPS}),
    },
)


SETTLE_MODE_TRAITS: Mapping[SettleMode, frozenset[SettleModeTrait]] = total(
    SettleMode,
    {
        SettleMode.GROUND: frozenset(),
        SettleMode.FLOATING: frozenset({SettleModeTrait.UPKEPT}),
        SettleMode.STILT: frozenset(),
        SettleMode.OASIS: frozenset(),
        SettleMode.VENT: frozenset(),
        SettleMode.HABITAT: frozenset({SettleModeTrait.UPKEPT}),
        SettleMode.BAND: frozenset(),
        SettleMode.DECK: frozenset(),
    },
)


SIZE_CLASS_TRAITS: Mapping[SizeClass, frozenset[SizeClassTrait]] = total(
    SizeClass,
    {
        SizeClass.TINY: frozenset({SizeClassTrait.SHELLED, SizeClassTrait.SLEEPERS}),
        SizeClass.SMALL: frozenset({SizeClassTrait.KEPT_SIZES, SizeClassTrait.SHELLED, SizeClassTrait.SLEEPERS}),
        SizeClass.MEDIUM: frozenset({SizeClassTrait.KEPT_SIZES, SizeClassTrait.SLEEPERS}),
        SizeClass.LARGE: frozenset({SizeClassTrait.DRAUGHT, SizeClassTrait.KEPT_SIZES, SizeClassTrait.RIDEABLE}),
        SizeClass.HUGE: frozenset({SizeClassTrait.DRAUGHT, SizeClassTrait.GREAT, SizeClassTrait.RIDEABLE}),
        SizeClass.COLOSSAL: frozenset({SizeClassTrait.GREAT, SizeClassTrait.RIDEABLE}),
    },
)


SKILL_KIND_TRAITS: Mapping[SkillKind, frozenset[SkillKindTrait]] = total(
    SkillKind,
    {
        SkillKind.BLADE: frozenset({SkillKindTrait.HUNT_SKILLS}),
        SkillKind.SPEAR: frozenset({SkillKindTrait.HUNT_SKILLS}),
        SkillKind.AXE: frozenset(),
        SkillKind.BLUNT: frozenset(),
        SkillKind.BOW: frozenset({SkillKindTrait.HUNT_SKILLS}),
        SkillKind.SLING: frozenset(),
        SkillKind.THROWING: frozenset(),
        SkillKind.SHIELD: frozenset(),
        SkillKind.UNARMED: frozenset(),
        SkillKind.RIDING: frozenset({SkillKindTrait.NEEDS_TRAVEL_SKILLS, SkillKindTrait.TRAVEL_SKILLS}),
        SkillKind.MOUNTED_COMBAT: frozenset(),
        SkillKind.SIEGECRAFT: frozenset(),
        SkillKind.NAVAL_COMBAT: frozenset(),
        SkillKind.BEAST_HANDLING: frozenset(),
        SkillKind.TACTICS: frozenset(),
        SkillKind.STRATEGY: frozenset(),
        SkillKind.LOGISTICS: frozenset(),
        SkillKind.LEADERSHIP: frozenset(),
        SkillKind.INTIMIDATION: frozenset(),
        SkillKind.ORATORY: frozenset(),
        SkillKind.NEGOTIATION: frozenset(),
        SkillKind.INTRIGUE: frozenset({SkillKindTrait.INTRIGUE_SKILLS}),
        SkillKind.ETIQUETTE: frozenset(),
        SkillKind.DECEPTION: frozenset({SkillKindTrait.INTRIGUE_SKILLS}),
        SkillKind.TEACHING: frozenset(),
        SkillKind.SMITHING: frozenset(),
        SkillKind.CARPENTRY: frozenset(),
        SkillKind.MASONRY: frozenset(),
        SkillKind.WEAVING: frozenset(),
        SkillKind.POTTERY: frozenset(),
        SkillKind.JEWELLING: frozenset(),
        SkillKind.SHIPWRIGHT: frozenset(),
        SkillKind.ENGINEERING: frozenset(),
        SkillKind.ALCHEMY: frozenset(),
        SkillKind.LORE: frozenset(),
        SkillKind.MEDICINE: frozenset(),
        SkillKind.SURGERY: frozenset(),
        SkillKind.ASTRONOMY: frozenset(),
        SkillKind.LAW: frozenset(),
        SkillKind.THEOLOGY: frozenset(),
        SkillKind.LANGUAGES: frozenset(),
        SkillKind.WRITING: frozenset(),
        SkillKind.CRYPTOGRAPHY: frozenset(),
        SkillKind.ACCOUNTING: frozenset(),
        SkillKind.HUNTING: frozenset({SkillKindTrait.HUNT_SKILLS}),
        SkillKind.TRACKING: frozenset({SkillKindTrait.NEEDS_TRAVEL_SKILLS}),
        SkillKind.FORAGING: frozenset(),
        SkillKind.SAILING: frozenset({SkillKindTrait.NEEDS_TRAVEL_SKILLS, SkillKindTrait.TRAVEL_SKILLS}),
        SkillKind.NAVIGATION: frozenset({SkillKindTrait.NEEDS_TRAVEL_SKILLS, SkillKindTrait.TRAVEL_SKILLS}),
        SkillKind.MOUNTAINEERING: frozenset({SkillKindTrait.NEEDS_TRAVEL_SKILLS, SkillKindTrait.TRAVEL_SKILLS}),
        SkillKind.SWIMMING: frozenset(),
        SkillKind.RITUAL: frozenset(),
        SkillKind.PROPHECY: frozenset(),
        SkillKind.SPELLCRAFT: frozenset(),
        SkillKind.SPIRIT_SPEAKING: frozenset(),
        SkillKind.FIREARMS: frozenset(),
        SkillKind.PILOTING: frozenset(),
        SkillKind.DRIVING: frozenset(),
        SkillKind.MECHANICS: frozenset(),
        SkillKind.ELECTRONICS: frozenset(),
        SkillKind.COMPUTING: frozenset(),
        SkillKind.SCIENCE: frozenset(),
        SkillKind.ADMINISTRATION: frozenset(),
    },
)


SOURCE_LOCUS_TRAITS: Mapping[SourceLocus, frozenset[SourceLocusTrait]] = total(
    SourceLocus,
    {
        SourceLocus.SELF: frozenset(),
        SourceLocus.OTHERS: frozenset(),
        SourceLocus.PLACE: frozenset({SourceLocusTrait.LAND_LOCI}),
        SourceLocus.SKY: frozenset({SourceLocusTrait.LAND_LOCI}),
        SourceLocus.SURROUNDINGS: frozenset({SourceLocusTrait.LAND_LOCI}),
        SourceLocus.MADE_THINGS: frozenset(),
        SourceLocus.PATRON: frozenset(),
        SourceLocus.BOND: frozenset(),
        SourceLocus.STORY: frozenset(),
        SourceLocus.VOID: frozenset(),
        SourceLocus.SUBSTANCE: frozenset(),
        SourceLocus.LIFE: frozenset({SourceLocusTrait.LAND_LOCI}),
        SourceLocus.DEATH: frozenset({SourceLocusTrait.LAND_LOCI}),
        SourceLocus.DREAM: frozenset(),
        SourceLocus.EMOTION: frozenset(),
    },
)


SPECIES_CLASS_TRAITS: Mapping[SpeciesClass, frozenset[SpeciesClassTrait]] = total(
    SpeciesClass,
    {
        SpeciesClass.ANIMAL: frozenset({SpeciesClassTrait.ROAMING}),
        SpeciesClass.PLANT: frozenset({SpeciesClassTrait.PLANT_CLASSES}),
        SpeciesClass.FUNGUS: frozenset({SpeciesClassTrait.PLANT_CLASSES}),
        SpeciesClass.VERMIN: frozenset({SpeciesClassTrait.ROAMING}),
        SpeciesClass.MICROBE: frozenset(),
        SpeciesClass.MINERAL: frozenset(),
        SpeciesClass.GASEOUS: frozenset(),
        SpeciesClass.ENERGY: frozenset(),
        SpeciesClass.MADE: frozenset(),
        SpeciesClass.COLONIAL: frozenset({SpeciesClassTrait.PLANT_CLASSES}),
        SpeciesClass.HYBRID: frozenset(),
    },
)


SPEECH_VENUE_TRAITS: Mapping[SpeechVenue, frozenset[SpeechVenueTrait]] = total(
    SpeechVenue,
    {
        SpeechVenue.ASSEMBLY: frozenset(),
        SpeechVenue.COURT: frozenset(),
        SpeechVenue.TEMPLE: frozenset(),
        SpeechVenue.SQUARE: frozenset({SpeechVenueTrait.CROWD_VENUES}),
        SpeechVenue.SCHOOL: frozenset(),
        SpeechVenue.CAMP: frozenset({SpeechVenueTrait.CROWD_VENUES}),
        SpeechVenue.OUTLET: frozenset({SpeechVenueTrait.CROWD_VENUES}),
    },
)


SPELL_FORM_TRAITS: Mapping[SpellForm, frozenset[SpellFormTrait]] = total(
    SpellForm,
    {
        SpellForm.FIRE: frozenset(),
        SpellForm.WATER: frozenset(),
        SpellForm.AIR: frozenset(),
        SpellForm.EARTH: frozenset({SpellFormTrait.BREACHING}),
        SpellForm.PLANT: frozenset(),
        SpellForm.ANIMAL: frozenset(),
        SpellForm.BODY: frozenset(),
        SpellForm.MIND: frozenset(),
        SpellForm.IMAGE: frozenset(),
        SpellForm.SPIRIT: frozenset(),
        SpellForm.TIME: frozenset(),
        SpellForm.VOID: frozenset(),
        SpellForm.DEATH: frozenset(),
        SpellForm.LIGHT: frozenset(),
        SpellForm.SPACE: frozenset({SpellFormTrait.BREACHING}),
        SpellForm.FORCE: frozenset({SpellFormTrait.BREACHING}),
        SpellForm.SOUND: frozenset(),
        SpellForm.EMOTION: frozenset(),
        SpellForm.FATE: frozenset(),
        SpellForm.MACHINE: frozenset(),
        SpellForm.INFORMATION: frozenset(),
    },
)


SPELL_TECHNIQUE_TRAITS: Mapping[SpellTechnique, frozenset[SpellTechniqueTrait]] = total(
    SpellTechnique,
    {
        SpellTechnique.CREATE: frozenset(),
        SpellTechnique.PERCEIVE: frozenset(),
        SpellTechnique.TRANSFORM: frozenset(),
        SpellTechnique.DESTROY: frozenset({SpellTechniqueTrait.HARMING}),
        SpellTechnique.CONTROL: frozenset(),
        SpellTechnique.BIND: frozenset(),
        SpellTechnique.SUMMON: frozenset(),
        SpellTechnique.WARD: frozenset(),
        SpellTechnique.DRAIN: frozenset({SpellTechniqueTrait.HARMING}),
        SpellTechnique.MIMIC: frozenset(),
    },
)


STANCE_TRAITS: Mapping[Stance, frozenset[StanceTrait]] = total(
    Stance,
    {
        Stance.MARCH: frozenset({StanceTrait.LAYING}),
        Stance.FORAGE: frozenset(),
        Stance.ENTRENCH: frozenset({StanceTrait.LAYING, StanceTrait.PATROLS}),
        Stance.BESIEGE: frozenset({StanceTrait.LAYING}),
        Stance.GARRISON: frozenset({StanceTrait.LAYING, StanceTrait.PATROLS}),
        Stance.RAID: frozenset(),
        Stance.RETREAT: frozenset(),
        Stance.WINTER_QUARTERS: frozenset({StanceTrait.LAYING, StanceTrait.PATROLS}),
        Stance.PURSUE: frozenset(),
        Stance.ESCORT: frozenset({StanceTrait.PATROLS}),
    },
)


STARVATION_STAGE_TRAITS: Mapping[StarvationStage, frozenset[StarvationStageTrait]] = total(
    StarvationStage,
    {
        StarvationStage.NONE: frozenset(),
        StarvationStage.RATIONING: frozenset(),
        StarvationStage.FAMINE: frozenset({StarvationStageTrait.HUNGRY}),
        StarvationStage.TABOO_BROKEN: frozenset({StarvationStageTrait.HUNGRY}),
    },
)


STRUCTURE_SECTION_TRAITS: Mapping[StructureSection, frozenset[StructureSectionTrait]] = total(
    StructureSection,
    {
        StructureSection.FOUNDATION: frozenset(),
        StructureSection.OUTER_WALL: frozenset({StructureSectionTrait.BREACHES}),
        StructureSection.GATE: frozenset({StructureSectionTrait.BREACHES}),
        StructureSection.GATEHOUSE: frozenset(),
        StructureSection.TOWERS: frozenset({StructureSectionTrait.TALL}),
        StructureSection.KEEP: frozenset({StructureSectionTrait.TALL}),
        StructureSection.BATTLEMENTS: frozenset(),
        StructureSection.EARTHWORK: frozenset(),
        StructureSection.ROOF: frozenset({StructureSectionTrait.TALL}),
        StructureSection.MAIN_HALL: frozenset(),
        StructureSection.UPPER_FLOORS: frozenset({StructureSectionTrait.TALL}),
        StructureSection.STORES: frozenset(),
        StructureSection.QUARTERS: frozenset(),
        StructureSection.WORKSHOP_FLOOR: frozenset(),
        StructureSection.KITCHEN: frozenset(),
        StructureSection.SANCTUM: frozenset(),
        StructureSection.VAULT: frozenset(),
        StructureSection.ARCHIVE: frozenset(),
        StructureSection.WARDS: frozenset(),
        StructureSection.DOME: frozenset({StructureSectionTrait.TALL}),
        StructureSection.SPIRE: frozenset({StructureSectionTrait.TALL}),
        StructureSection.SPAN: frozenset(),
        StructureSection.PIERS: frozenset(),
        StructureSection.SLUICE: frozenset(),
        StructureSection.CONDUITS: frozenset(),
        StructureSection.SEATING: frozenset(),
        StructureSection.STAGE: frozenset(),
        StructureSection.PENS: frozenset(),
        StructureSection.FURNACE: frozenset(),
        StructureSection.WHEEL: frozenset(),
        StructureSection.SHAFTS: frozenset(),
        StructureSection.DOCKS: frozenset(),
        StructureSection.SLIPWAY: frozenset(),
        StructureSection.BEACON: frozenset({StructureSectionTrait.TALL}),
        StructureSection.CORE: frozenset(),
        StructureSection.SPINE: frozenset({StructureSectionTrait.TALL}),
        StructureSection.RING_SEGMENTS: frozenset({StructureSectionTrait.BREACHED_DECKS}),
        StructureSection.COLLECTORS: frozenset(),
        StructureSection.THRUSTERS: frozenset(),
        StructureSection.DOCKING_RING: frozenset(),
        StructureSection.HABITAT_DECKS: frozenset({StructureSectionTrait.BREACHED_DECKS}),
        StructureSection.CONTROL_CORE: frozenset(),
        StructureSection.SHIELDING: frozenset(),
    },
)


TACTIC_TRAITS: Mapping[Tactic, frozenset[TacticTrait]] = total(
    Tactic,
    {
        Tactic.HOLD_LINE: frozenset({TacticTrait.LINE_TACTICS}),
        Tactic.FRONTAL_ASSAULT: frozenset(),
        Tactic.DOUBLE_ENVELOPMENT: frozenset(),
        Tactic.FEIGNED_RETREAT: frozenset(),
        Tactic.FLANK_CAVALRY: frozenset(),
        Tactic.MISSILE_ATTRITION: frozenset({TacticTrait.GUNS_TACTICS}),
        Tactic.SHIELD_WALL: frozenset({TacticTrait.LINE_TACTICS}),
        Tactic.WEDGE: frozenset(),
        Tactic.NIGHT_RAID: frozenset({TacticTrait.HIDDEN_TACTICS}),
        Tactic.AMBUSH: frozenset({TacticTrait.HIDDEN_TACTICS}),
        Tactic.SKIRMISH_HARASS: frozenset({TacticTrait.SKIRMISH_TACTICS}),
        Tactic.RIVER_DEFENCE: frozenset(),
        Tactic.SIEGE_ASSAULT: frozenset(),
        Tactic.FEINT: frozenset({TacticTrait.SKIRMISH_TACTICS}),
        Tactic.ARTILLERY_BARRAGE: frozenset({TacticTrait.GUNS_TACTICS}),
        Tactic.ARMOURED_THRUST: frozenset(),
        Tactic.AIR_SUPERIORITY: frozenset(),
        Tactic.BLOCKADE: frozenset(),
        Tactic.GUERRILLA: frozenset({TacticTrait.HIDDEN_TACTICS}),
        Tactic.ELECTRONIC_WARFARE: frozenset(),
        Tactic.ORBITAL_BOMBARDMENT: frozenset(),
        Tactic.DROP_ASSAULT: frozenset({TacticTrait.STRIKE_TACTICS}),
        Tactic.INFILTRATION: frozenset({TacticTrait.HIDDEN_TACTICS, TacticTrait.STRIKE_TACTICS}),
    },
)


TAX_KIND_TRAITS: Mapping[TaxKind, frozenset[TaxKindTrait]] = total(
    TaxKind,
    {
        TaxKind.LAND: frozenset(),
        TaxKind.POLL: frozenset({TaxKindTrait.HEAD_TAXES}),
        TaxKind.TRADE: frozenset(),
        TaxKind.CONSUMPTION: frozenset(),
        TaxKind.TITHE: frozenset(),
        TaxKind.INCOME: frozenset({TaxKindTrait.SHARE_TAXES}),
        TaxKind.PROPERTY: frozenset({TaxKindTrait.SHARE_TAXES}),
        TaxKind.INHERITANCE: frozenset({TaxKindTrait.HEAD_TAXES}),
        TaxKind.WEALTH: frozenset({TaxKindTrait.SHARE_TAXES}),
        TaxKind.COMPANY: frozenset(),
        TaxKind.LABOUR_LEVY: frozenset({TaxKindTrait.HEAD_TAXES}),
        TaxKind.IN_KIND: frozenset({TaxKindTrait.SHARE_TAXES}),
        TaxKind.LICENCE: frozenset(),
        TaxKind.SEIGNIORAGE: frozenset(),
        TaxKind.POLLUTION: frozenset({TaxKindTrait.SHARE_TAXES}),
        TaxKind.EXCISE: frozenset({TaxKindTrait.SHARE_TAXES}),
    },
)


TECHNIQUE_TRAITS: Mapping[Technique, frozenset[TechniqueTrait]] = total(
    Technique,
    {
        Technique.PHALANX_DRILL: frozenset(),
        Technique.HORSE_ARCHERY: frozenset(),
        Technique.SIEGECRAFT: frozenset(),
        Technique.FORTIFICATION: frozenset(),
        Technique.LOGISTICS: frozenset(),
        Technique.HERBALISM: frozenset(),
        Technique.SURGERY: frozenset(),
        Technique.AMPUTATION: frozenset(),
        Technique.PROSTHETICS: frozenset(),
        Technique.QUARANTINE: frozenset(),
        Technique.INOCULATION: frozenset(),
        Technique.IRRIGATION: frozenset(),
        Technique.CROP_ROTATION: frozenset(),
        Technique.TERRACING: frozenset(),
        Technique.PLOUGH: frozenset(),
        Technique.SELECTIVE_BREEDING: frozenset(),
        Technique.BRONZE: frozenset({TechniqueTrait.TOOL_METALS}),
        Technique.IRON: frozenset({TechniqueTrait.TOOL_METALS}),
        Technique.STEEL: frozenset({TechniqueTrait.TOOL_METALS}),
        Technique.SKYSTEEL: frozenset({TechniqueTrait.TOOL_METALS}),
        Technique.ARCH: frozenset(),
        Technique.DOME: frozenset(),
        Technique.AQUEDUCT: frozenset(),
        Technique.FORTRESS: frozenset(),
        Technique.ALPHABET: frozenset(),
        Technique.PAPER: frozenset(),
        Technique.PRINTING: frozenset(),
        Technique.CRYPTOGRAPHY: frozenset(),
        Technique.CALENDAR: frozenset(),
        Technique.NAVIGATION_STARS: frozenset(),
        Technique.ECLIPSE_PREDICTION: frozenset(),
        Technique.SAILING: frozenset(),
        Technique.SHIPWRIGHTING: frozenset(),
        Technique.COINAGE: frozenset(),
        Technique.BANKING: frozenset({TechniqueTrait.FINANCE}),
        Technique.WARDING: frozenset(),
        Technique.SUMMONING: frozenset(),
        Technique.SKY_SAILING: frozenset(),
        Technique.NECROMANCY: frozenset(),
        Technique.ALCHEMY: frozenset(),
        Technique.ASTRONOMY_INSTRUMENTS: frozenset(),
        Technique.CARTOGRAPHY: frozenset(),
        Technique.ORAL_LAW: frozenset(),
        Technique.WRITTEN_LAW: frozenset(),
        Technique.CODIFIED_LAW: frozenset(),
        Technique.BUREAUCRACY: frozenset(),
        Technique.CENSUS: frozenset(),
        Technique.POSTAL_SERVICE: frozenset(),
        Technique.DIPLOMATIC_CORPS: frozenset(),
        Technique.STANDING_ARMY_ADMIN: frozenset(),
        Technique.DOUBLE_ENTRY: frozenset({TechniqueTrait.PLACE_VALUE_RECKONING}),
        Technique.JOINT_STOCK: frozenset({TechniqueTrait.FINANCE}),
        Technique.INSURANCE: frozenset(),
        Technique.GUILDS: frozenset(),
        Technique.UNIVERSITIES: frozenset(),
        Technique.HOSPITALS: frozenset(),
        Technique.PRINTING_PRESS: frozenset(),
        Technique.ORGANISED_CLERGY: frozenset(),
        Technique.MONASTICISM: frozenset(),
        Technique.THEOLOGY_SCHOOLS: frozenset(),
        Technique.LOGIC: frozenset(),
        Technique.NATURAL_PHILOSOPHY: frozenset(),
        Technique.EMPIRICISM: frozenset(),
        Technique.HUMANIST_IDEALS: frozenset(),
        Technique.EXAMINATIONS: frozenset(),
        Technique.DRAINAGE: frozenset(),
        Technique.GUNPOWDER: frozenset(),
        Technique.FIREARMS: frozenset(),
        Technique.CANNON: frozenset(),
        Technique.STAR_FORTS: frozenset(),
        Technique.VOLLEY_DRILL: frozenset(),
        Technique.STEAM_POWER: frozenset({TechniqueTrait.ENGINEERING}),
        Technique.COKE_SMELTING: frozenset(),
        Technique.MACHINE_TOOLS: frozenset({TechniqueTrait.ENGINEERING}),
        Technique.RAILWAYS: frozenset({TechniqueTrait.ENGINEERING}),
        Technique.STEAMSHIPS: frozenset(),
        Technique.FACTORY_PRODUCTION: frozenset(),
        Technique.INDUSTRIAL_CHEMISTRY: frozenset(),
        Technique.CANNED_FOOD: frozenset(),
        Technique.VACCINES: frozenset(),
        Technique.ELECTRICITY: frozenset(),
        Technique.TELEGRAPH: frozenset(),
        Technique.TELEPHONE: frozenset(),
        Technique.ELECTRIC_LIGHT: frozenset(),
        Technique.REFRIGERATION: frozenset(),
        Technique.COMBUSTION_ENGINE: frozenset(),
        Technique.AVIATION: frozenset(),
        Technique.COMPUTATION: frozenset({TechniqueTrait.PLACE_VALUE_RECKONING}),
        Technique.RADIO: frozenset(),
        Technique.MASS_MEDIA: frozenset(),
        Technique.ANTIBIOTICS: frozenset(),
        Technique.GREEN_REVOLUTION: frozenset(),
        Technique.NUCLEAR_POWER: frozenset(),
        Technique.NUCLEAR_WEAPONS: frozenset(),
        Technique.ROCKETRY: frozenset(),
        Technique.GENETIC_ENGINEERING: frozenset(),
        Technique.ARTIFICIAL_MINDS: frozenset(),
    },
)


THOUGHT_KIND_TRAITS: Mapping[ThoughtKind, frozenset[ThoughtKindTrait]] = total(
    ThoughtKind,
    {
        ThoughtKind.MARRIED: frozenset(),
        ThoughtKind.CHILD_BORN: frozenset(),
        ThoughtKind.SAW_KIN_DIE: frozenset(),
        ThoughtKind.LOST_SPOUSE: frozenset(),
        ThoughtKind.LOST_CHILD: frozenset(),
        ThoughtKind.BETRAYED: frozenset(),
        ThoughtKind.WAS_INSULTED: frozenset({ThoughtKindTrait.SHAME_KINDS}),
        ThoughtKind.WAS_GIFTED: frozenset(),
        ThoughtKind.WAS_SAVED: frozenset(),
        ThoughtKind.WAS_CHEATED: frozenset(),
        ThoughtKind.WON_BATTLE: frozenset(),
        ThoughtKind.DEFEATED: frozenset({ThoughtKindTrait.SHAME_KINDS}),
        ThoughtKind.WON_DUEL: frozenset(),
        ThoughtKind.LOST_DUEL: frozenset({ThoughtKindTrait.SHAME_KINDS}),
        ThoughtKind.WAS_WOUNDED: frozenset(),
        ThoughtKind.WAS_MAIMED: frozenset(),
        ThoughtKind.LOST_LIMB_BUT_LIVED: frozenset(),
        ThoughtKind.WAS_HEALED: frozenset(),
        ThoughtKind.FELL_ILL: frozenset(),
        ThoughtKind.WITNESSED_ATROCITY: frozenset(),
        ThoughtKind.WAS_CAPTURED: frozenset(),
        ThoughtKind.WAS_FREED: frozenset(),
        ThoughtKind.KILLED_FOE: frozenset(),
        ThoughtKind.ROSE_IN_RANK: frozenset(),
        ThoughtKind.FELL_IN_RANK: frozenset(),
        ThoughtKind.GAINED_RENOWN: frozenset(),
        ThoughtKind.WAS_SHAMED: frozenset({ThoughtKindTrait.SHAME_KINDS}),
        ThoughtKind.WAS_PUNISHED: frozenset({ThoughtKindTrait.SHAME_KINDS}),
        ThoughtKind.WAS_CONQUERED: frozenset(),
        ThoughtKind.PRAYED_ANSWERED: frozenset(),
        ThoughtKind.PRAYER_IGNORED: frozenset(),
        ThoughtKind.SAW_MIRACLE: frozenset(),
        ThoughtKind.FELT_GOD_NEAR: frozenset(),
        ThoughtKind.ALIEN_DOMINION: frozenset(),
        ThoughtKind.LOST_FAITH: frozenset(),
        ThoughtKind.FOUND_FAITH: frozenset(),
        ThoughtKind.SAW_DESECRATION: frozenset(),
        ThoughtKind.TOUCHED_BY_A_GOD: frozenset(),
        ThoughtKind.ADMIRED_GREAT_WORK: frozenset(),
        ThoughtKind.HEARD_GREAT_MUSIC: frozenset(),
        ThoughtKind.ATTENDED_FEAST: frozenset(),
        ThoughtKind.MADE_MASTERWORK: frozenset(),
        ThoughtKind.LEARNED_SOMETHING: frozenset(),
        ThoughtKind.TAUGHT_APPRENTICE: frozenset(),
        ThoughtKind.TOOK_IDEA_TO_HEART: frozenset(),
        ThoughtKind.ATE_FINE_FOOD: frozenset(),
        ThoughtKind.WENT_HUNGRY: frozenset(),
        ThoughtKind.WENT_THIRSTY: frozenset(),
        ThoughtKind.DRANK_WELL: frozenset(),
        ThoughtKind.SLEPT_WELL: frozenset(),
        ThoughtKind.EXHAUSTED: frozenset(),
        ThoughtKind.LIVED_IN_COMFORT: frozenset(),
        ThoughtKind.LIVED_IN_SQUALOR: frozenset(),
        ThoughtKind.FELT_HALE: frozenset(),
        ThoughtKind.FELT_UNWELL: frozenset(),
        ThoughtKind.FELT_SAFE: frozenset(),
        ThoughtKind.FELT_UNSAFE: frozenset(),
        ThoughtKind.AMONG_KIN: frozenset(),
        ThoughtKind.MISSED_KIN: frozenset(),
        ThoughtKind.AMONG_FRIENDS: frozenset(),
        ThoughtKind.FELT_LONELY: frozenset(),
        ThoughtKind.LOST_PET: frozenset(),
        ThoughtKind.COMFORTED_BY_PET: frozenset(),
        ThoughtKind.LOVED: frozenset(),
        ThoughtKind.LONGED_FOR_LOVE: frozenset(),
        ThoughtKind.HAD_PEACE_AND_QUIET: frozenset(),
        ThoughtKind.CROWDED: frozenset(),
        ThoughtKind.RESPECTED: frozenset(),
        ThoughtKind.OVERLOOKED: frozenset(),
        ThoughtKind.BELONGED: frozenset(),
        ThoughtKind.ADRIFT: frozenset(),
        ThoughtKind.FELT_PURPOSE: frozenset(),
        ThoughtKind.LACKED_PURPOSE: frozenset(),
        ThoughtKind.PRAYED_IN_PEACE: frozenset(),
        ThoughtKind.FAITH_UNMET: frozenset(),
        ThoughtKind.LEARNED_NOTHING: frozenset(),
        ThoughtKind.FELT_FREE: frozenset(),
        ThoughtKind.FELT_CONSTRAINED: frozenset(),
        ThoughtKind.FOUND_ANSWERS: frozenset(),
        ThoughtKind.KEPT_IN_IGNORANCE: frozenset(),
        ThoughtKind.FELT_STIMULATED: frozenset(),
        ThoughtKind.FELT_DULLED: frozenset(),
        ThoughtKind.FELT_LASTING: frozenset(),
        ThoughtKind.FEARED_ENDING: frozenset(),
        ThoughtKind.WELL_KEPT: frozenset(),
        ThoughtKind.NEGLECTED: frozenset(),
        ThoughtKind.MADE_SOMETHING: frozenset(),
        ThoughtKind.NOTHING_MADE: frozenset(),
        ThoughtKind.SAW_BEAUTY: frozenset(),
        ThoughtKind.SURROUNDED_BY_UGLINESS: frozenset(),
        ThoughtKind.WALKED_IN_NATURE: frozenset(),
        ThoughtKind.CUT_OFF_FROM_NATURE: frozenset(),
        ThoughtKind.HAD_ADVENTURE: frozenset(),
        ThoughtKind.RESTLESS: frozenset(),
        ThoughtKind.TESTED_IN_COMBAT: frozenset(),
        ThoughtKind.BLADE_RUSTING: frozenset(),
        ThoughtKind.PROSPERED: frozenset(),
        ThoughtKind.WANTED_FOR_MONEY: frozenset(),
        ThoughtKind.ENJOYED_LEISURE: frozenset(),
        ThoughtKind.BORED: frozenset(),
        ThoughtKind.LIVED_IN_ORDER: frozenset(),
        ThoughtKind.LIVED_IN_DISORDER: frozenset(),
        ThoughtKind.RELIVED_MEMORY: frozenset(),
        ThoughtKind.MOURNED: frozenset(),
        ThoughtKind.MADE_PEACE_WITH_LOSS: frozenset(),
        ThoughtKind.HAD_NIGHTMARE: frozenset(),
        ThoughtKind.HAD_GOOD_DREAM: frozenset(),
        ThoughtKind.DREAMED_OF_LONGING: frozenset(),
        ThoughtKind.RECEIVED_VISITATION: frozenset(),
        ThoughtKind.SENT_BY_THE_CREATOR: frozenset(),
        ThoughtKind.LIKED_SURROUNDINGS: frozenset(),
        ThoughtKind.DISLIKED_SURROUNDINGS: frozenset(),
        ThoughtKind.PROUD_OF_HOME: frozenset(),
        ThoughtKind.ASHAMED_OF_HOME: frozenset(),
        ThoughtKind.ENJOYED_FAVOURITE: frozenset(),
        ThoughtKind.ENDURED_A_DISLIKE: frozenset(),
        ThoughtKind.ACTED_ON_CONSCIENCE: frozenset(),
        ThoughtKind.ACTED_AGAINST_CONSCIENCE: frozenset(),
        ThoughtKind.KIN_SHAMED: frozenset(),
        ThoughtKind.SHAME_RESTORED: frozenset(),
        ThoughtKind.DREAM_PROGRESS: frozenset(),
        ThoughtKind.DREAM_FULFILLED: frozenset(),
        ThoughtKind.DREAM_SHATTERED: frozenset(),
        ThoughtKind.WANT_FULFILLED: frozenset(),
        ThoughtKind.FEAR_NEAR: frozenset(),
        ThoughtKind.INSPIRED: frozenset(),
        ThoughtKind.INSPIRATION_LOST: frozenset(),
        ThoughtKind.DISILLUSIONED: frozenset(),
        ThoughtKind.MADE_A_FRIEND: frozenset(),
        ThoughtKind.LOST_A_FRIEND: frozenset(),
        ThoughtKind.LAUGHED_TOGETHER: frozenset(),
        ThoughtKind.WAS_COMFORTED: frozenset(),
        ThoughtKind.WAS_FLATTERED: frozenset(),
        ThoughtKind.QUARRELLED: frozenset(),
        ThoughtKind.RECONCILED: frozenset(),
        ThoughtKind.FELL_IN_LOVE: frozenset(),
        ThoughtKind.HEARTBROKEN: frozenset(),
        ThoughtKind.JEALOUS: frozenset(),
        ThoughtKind.BRAWLED: frozenset(),
        ThoughtKind.WAS_THREATENED: frozenset(),
        ThoughtKind.CONFIDED_IN: frozenset(),
        ThoughtKind.WON_CONTEST: frozenset(),
        ThoughtKind.LOST_CONTEST: frozenset(),
        ThoughtKind.WAS_PERSUADED: frozenset(),
        ThoughtKind.ROSE_IN_STANDING: frozenset(),
        ThoughtKind.LOST_STANDING: frozenset(),
        ThoughtKind.PASSION_STIRRED: frozenset(),
        ThoughtKind.PASSION_BROKE: frozenset(),
        ThoughtKind.CAUGHT_FEELING: frozenset(),
        ThoughtKind.WAS_SURPRISED: frozenset(),
        ThoughtKind.GREW_CURIOUS: frozenset(),
        ThoughtKind.FELT_COMPASSION: frozenset(),
        ThoughtKind.FELT_CONTEMPT: frozenset(),
    },
)


TRADE_MODE_TRAITS: Mapping[TradeMode, frozenset[TradeModeTrait]] = total(
    TradeMode,
    {
        TradeMode.ROAD: frozenset({TradeModeTrait.ICE_MODES, TradeModeTrait.LAND_MODES}),
        TradeMode.RIVER: frozenset({TradeModeTrait.ICE_MODES, TradeModeTrait.WATER_MODES}),
        TradeMode.SEA: frozenset({TradeModeTrait.WATER_MODES}),
        TradeMode.SKY: frozenset(),
        TradeMode.SPACE: frozenset(),
        TradeMode.RIFT: frozenset(),
        TradeMode.NETWORK: frozenset(),
    },
)


TRADE_POLICY_KIND_TRAITS: Mapping[TradePolicyKind, frozenset[TradePolicyKindTrait]] = total(
    TradePolicyKind,
    {
        TradePolicyKind.TARIFF: frozenset(),
        TradePolicyKind.SUBSIDY: frozenset(),
        TradePolicyKind.EMBARGO: frozenset({TradePolicyKindTrait.BARRING}),
        TradePolicyKind.QUOTA: frozenset(),
        TradePolicyKind.LICENCE: frozenset(),
        TradePolicyKind.PRICE_CONTROL: frozenset(),
        TradePolicyKind.FREE_TRADE: frozenset(),
        TradePolicyKind.EXPORT_BAN: frozenset(),
        TradePolicyKind.SANCTION: frozenset({TradePolicyKindTrait.BARRING}),
    },
)


TRADE_ROUTE_STATUS_TRAITS: Mapping[TradeRouteStatus, frozenset[TradeRouteStatusTrait]] = total(
    TradeRouteStatus,
    {
        TradeRouteStatus.FORMING: frozenset({TradeRouteStatusTrait.LIVE_STATUSES}),
        TradeRouteStatus.OPEN: frozenset({TradeRouteStatusTrait.LIVE_STATUSES, TradeRouteStatusTrait.CARRYING}),
        TradeRouteStatus.CONTESTED: frozenset({TradeRouteStatusTrait.LIVE_STATUSES, TradeRouteStatusTrait.CARRYING}),
        TradeRouteStatus.SEASONAL: frozenset({TradeRouteStatusTrait.LIVE_STATUSES, TradeRouteStatusTrait.CARRYING}),
        TradeRouteStatus.BLOCKADED: frozenset({TradeRouteStatusTrait.LIVE_STATUSES}),
        TradeRouteStatus.CLOSED: frozenset(),
        TradeRouteStatus.DECAYED: frozenset(),
    },
)


TREATY_KIND_TRAITS: Mapping[TreatyKind, frozenset[TreatyKindTrait]] = total(
    TreatyKind,
    {
        TreatyKind.PEACE: frozenset(),
        TreatyKind.TRUCE: frozenset(),
        TreatyKind.ALLIANCE_DEFENSIVE: frozenset({TreatyKindTrait.ALLIANCES, TreatyKindTrait.DEFENSIVE, TreatyKindTrait.KEPT_KINDS}),
        TreatyKind.ALLIANCE_OFFENSIVE: frozenset({TreatyKindTrait.ALLIANCES, TreatyKindTrait.KEPT_KINDS, TreatyKindTrait.OFFENSIVE}),
        TreatyKind.NON_AGGRESSION: frozenset(),
        TreatyKind.VASSALAGE: frozenset({TreatyKindTrait.DEFENSIVE, TreatyKindTrait.KEPT_KINDS}),
        TreatyKind.TRIBUTE: frozenset(),
        TreatyKind.MARRIAGE_PACT: frozenset({TreatyKindTrait.ALLIANCES, TreatyKindTrait.DEFENSIVE, TreatyKindTrait.KEPT_KINDS}),
        TreatyKind.TRADE_PACT: frozenset({TreatyKindTrait.KEPT_KINDS}),
        TreatyKind.CONDOTTA: frozenset({TreatyKindTrait.OFFENSIVE}),
        TreatyKind.GUARANTEE: frozenset({TreatyKindTrait.DEFENSIVE, TreatyKindTrait.KEPT_KINDS}),
        TreatyKind.INTERWORLD: frozenset({TreatyKindTrait.KEPT_KINDS}),
        TreatyKind.COALITION: frozenset({TreatyKindTrait.DEFENSIVE, TreatyKindTrait.KEPT_KINDS}),
        TreatyKind.DIVINE_PACT: frozenset(),
        TreatyKind.NAVAL_LIMIT: frozenset({TreatyKindTrait.MUTUAL}),
        TreatyKind.ARMS_LIMIT: frozenset({TreatyKindTrait.MUTUAL}),
    },
)


UNIT_HONOUR_KIND_TRAITS: Mapping[UnitHonourKind, frozenset[UnitHonourKindTrait]] = total(
    UnitHonourKind,
    {
        UnitHonourKind.VICTORY: frozenset({UnitHonourKindTrait.GLORIOUS}),
        UnitHonourKind.STAND: frozenset({UnitHonourKindTrait.GLORIOUS}),
        UnitHonourKind.SIEGE: frozenset({UnitHonourKindTrait.GLORIOUS}),
        UnitHonourKind.SURVIVAL: frozenset(),
        UnitHonourKind.MASSACRE: frozenset(),
        UnitHonourKind.RELIEF: frozenset({UnitHonourKindTrait.GLORIOUS}),
        UnitHonourKind.CROSSING: frozenset({UnitHonourKindTrait.GLORIOUS}),
    },
)


VEHICLE_FAMILY_TRAITS: Mapping[VehicleFamily, frozenset[VehicleFamilyTrait]] = total(
    VehicleFamily,
    {
        VehicleFamily.MOUNT: frozenset(),
        VehicleFamily.CART: frozenset(),
        VehicleFamily.WAGON: frozenset(),
        VehicleFamily.CHARIOT: frozenset(),
        VehicleFamily.MOTOR: frozenset(),
        VehicleFamily.TRACKED: frozenset(),
        VehicleFamily.WALKER: frozenset(),
        VehicleFamily.RAIL: frozenset(),
        VehicleFamily.RAM: frozenset({VehicleFamilyTrait.SIEGE}),
        VehicleFamily.TOWER: frozenset({VehicleFamilyTrait.SIEGE}),
        VehicleFamily.THROWER: frozenset({VehicleFamilyTrait.SIEGE}),
        VehicleFamily.GUN: frozenset(),
        VehicleFamily.BOAT: frozenset(),
        VehicleFamily.GALLEY: frozenset(),
        VehicleFamily.SAILING_SHIP: frozenset(),
        VehicleFamily.STEAM_SHIP: frozenset(),
        VehicleFamily.SUBMARINE: frozenset(),
        VehicleFamily.BALLOON: frozenset(),
        VehicleFamily.AIRSHIP: frozenset(),
        VehicleFamily.AIRCRAFT: frozenset(),
        VehicleFamily.ROTORCRAFT: frozenset(),
        VehicleFamily.SPACECRAFT: frozenset(),
        VehicleFamily.BURROWER: frozenset(),
        VehicleFamily.CONSTRUCT: frozenset(),
        VehicleFamily.LIVING: frozenset(),
    },
)


WAR_CAUSE_TRAITS: Mapping[WarCause, frozenset[WarCauseTrait]] = total(
    WarCause,
    {
        WarCause.HOSTILITY: frozenset(),
        WarCause.UPRISING: frozenset({WarCauseTrait.CASUS_BELLI_REVOLT_CAUSES}),
        WarCause.TRIBUTE_REVOLT: frozenset({WarCauseTrait.CASUS_BELLI_REVOLT_CAUSES}),
        WarCause.INCITED: frozenset(),
        WarCause.DECLARED: frozenset(),
        WarCause.BETRAYAL: frozenset(),
        WarCause.CONQUEST_JOURNEY: frozenset(),
        WarCause.FOREIGN_GOD: frozenset({WarCauseTrait.CASUS_BELLI_REVOLT_CAUSES}),
        WarCause.INDEPENDENCE: frozenset({WarCauseTrait.CASUS_BELLI_REVOLT_CAUSES}),
        WarCause.VENDETTA: frozenset(),
        WarCause.GRUDGE: frozenset(),
        WarCause.DIVINE_GRUDGE: frozenset(),
        WarCause.RIVALRY: frozenset(),
        WarCause.DEBT: frozenset(),
        WarCause.ESPIONAGE: frozenset(),
        WarCause.SABOTAGE: frozenset(),
        WarCause.ENVY: frozenset(),
        WarCause.SCHISM: frozenset({WarCauseTrait.HOLY_CAUSES}),
        WarCause.BEAST: frozenset({WarCauseTrait.CASUS_BELLI_REVOLT_CAUSES}),
        WarCause.RESOURCE: frozenset(),
        WarCause.IDEOLOGY: frozenset(),
        WarCause.TRADE_ROUTE: frozenset(),
        WarCause.CLAIM: frozenset(),
        WarCause.HOLY_WAR: frozenset({WarCauseTrait.HOLY_CAUSES}),
        WarCause.SUCCESSION: frozenset(),
        WarCause.RAID: frozenset(),
        WarCause.LIBERATION: frozenset({}),
        WarCause.PUNITIVE: frozenset(),
    },
)


WAR_ENDING_TRAITS: Mapping[WarEnding, frozenset[WarEndingTrait]] = total(
    WarEnding,
    {
        WarEnding.VICTORY: frozenset(),
        WarEnding.CONQUEST: frozenset(),
        WarEnding.TRIBUTE: frozenset(),
        WarEnding.EXHAUSTION: frozenset({WarEndingTrait.SIGNED_ENDINGS}),
        WarEnding.PEACE: frozenset({WarEndingTrait.SIGNED_ENDINGS}),
        WarEnding.WHITE_PEACE: frozenset({WarEndingTrait.SIGNED_ENDINGS}),
        WarEnding.BETRAYAL: frozenset(),
        WarEnding.SAME_FRONT: frozenset(),
        WarEnding.NO_SIDE_LEFT: frozenset(),
        WarEnding.MIRACLE: frozenset({WarEndingTrait.SIGNED_ENDINGS}),
    },
)


WAR_TERRAIN_TRAITS: Mapping[WarTerrain, frozenset[WarTerrainTrait]] = total(
    WarTerrain,
    {
        WarTerrain.LAND: frozenset(),
        WarTerrain.NAVAL: frozenset({WarTerrainTrait.LAND_UNFIT}),
        WarTerrain.SKY: frozenset({WarTerrainTrait.LAND_UNFIT}),
        WarTerrain.BOARDING: frozenset({WarTerrainTrait.LAND_UNFIT}),
        WarTerrain.STRATA: frozenset(),
    },
)


WEATHER_EFFECT_TRAITS: Mapping[WeatherEffect, frozenset[WeatherEffectTrait]] = total(
    WeatherEffect,
    {
        WeatherEffect.VISIBILITY: frozenset({WeatherEffectTrait.FALLING_EFFECTS}),
        WeatherEffect.FOOTING: frozenset({WeatherEffectTrait.FALLING_EFFECTS}),
        WeatherEffect.COLD: frozenset(),
        WeatherEffect.HEAT: frozenset(),
        WeatherEffect.WET: frozenset(),
        WeatherEffect.WIND: frozenset(),
        WeatherEffect.MORALE: frozenset(),
        WeatherEffect.GROWTH: frozenset(),
        WeatherEffect.LIGHTNING: frozenset(),
        WeatherEffect.FLOOD: frozenset(),
        WeatherEffect.BREATH: frozenset({WeatherEffectTrait.FALLING_EFFECTS}),
    },
)


WITNESS_MODE_TRAITS: Mapping[WitnessMode, frozenset[WitnessModeTrait]] = total(
    WitnessMode,
    {
        WitnessMode.SAW: frozenset({WitnessModeTrait.FIRST_HAND}),
        WitnessMode.HEARD: frozenset(),
        WitnessMode.TOOK_PART: frozenset({WitnessModeTrait.FIRST_HAND}),
        WitnessMode.WAS_TOLD: frozenset(),
    },
)


WORKS_KIND_TRAITS: Mapping[WorksKind, frozenset[WorksKindTrait]] = total(
    WorksKind,
    {
        WorksKind.ROAD: frozenset({WorksKindTrait.ROUTE_WORKS}),
        WorksKind.BRIDGE: frozenset({WorksKindTrait.ROUTE_WORKS}),
        WorksKind.CANAL: frozenset({WorksKindTrait.ROUTE_WORKS}),
        WorksKind.RAIL_LINE: frozenset({WorksKindTrait.ROUTE_WORKS}),
        WorksKind.AQUEDUCT: frozenset(),
        WorksKind.DAM: frozenset(),
        WorksKind.DRAINAGE: frozenset(),
        WorksKind.HARBOUR_WORKS: frozenset(),
        WorksKind.WALLS: frozenset(),
        WorksKind.GRANARY_SYSTEM: frozenset(),
        WorksKind.SEWER: frozenset(),
        WorksKind.POWER_LINE: frozenset(),
        WorksKind.NETWORK_LINE: frozenset(),
        WorksKind.TERRAFORMING_STAGE: frozenset(),
        WorksKind.MEGASTRUCTURE_STAGE: frozenset(),
        WorksKind.GROWN_WORKS: frozenset(),
    },
)


WORLD_END_TRAITS: Mapping[WorldEnd, frozenset[WorldEndTrait]] = total(
    WorldEnd,
    {
        WorldEnd.SHATTERED: frozenset({WorldEndTrait.LIFELESS}),
        WorldEnd.CONSUMED: frozenset({WorldEndTrait.GONE_FROM_SKY, WorldEndTrait.LIFELESS}),
        WorldEnd.FROZEN_DEAD: frozenset({WorldEndTrait.LIFELESS}),
        WorldEnd.SUNK_INTO_VOID: frozenset({WorldEndTrait.GONE_FROM_SKY, WorldEndTrait.LIFELESS}),
        WorldEnd.FORGOTTEN: frozenset({WorldEndTrait.GONE_FROM_SKY}),
        WorldEnd.TRANSFIGURED: frozenset(),
    },
)


WORLD_TYPE_TRAITS: Mapping[WorldType, frozenset[WorldTypeTrait]] = total(
    WorldType,
    {
        WorldType.ORDINARY: frozenset(),
        WorldType.OCEAN: frozenset(),
        WorldType.SAND: frozenset(),
        WorldType.ICE: frozenset({WorldTypeTrait.COLD_WORLDS, WorldTypeTrait.HARSH_WORLDS, WorldTypeTrait.TWO_SEASON_WORLDS}),
        WorldType.LAVA: frozenset({WorldTypeTrait.HARSH_WORLDS, WorldTypeTrait.VOLCANIC_WORLDS}),
        WorldType.CRYSTAL: frozenset(),
        WorldType.LIVING: frozenset(),
        WorldType.DEAD: frozenset({WorldTypeTrait.LIFELESS_WORLDS}),
        WorldType.DREAM: frozenset({WorldTypeTrait.DIVINE_WORLDS, WorldTypeTrait.SKYLESS_WORLDS}),
        WorldType.MIRROR: frozenset({WorldTypeTrait.SKYLESS_WORLDS}),
        WorldType.GAS: frozenset({WorldTypeTrait.GAS_WORLDS, WorldTypeTrait.GIANTS}),
        WorldType.RINGED: frozenset({WorldTypeTrait.BELTS, WorldTypeTrait.GAS_WORLDS}),
        WorldType.ASTEROID_BELT: frozenset({WorldTypeTrait.BELTS, WorldTypeTrait.BROKEN_WORLDS}),
        WorldType.TIDALLY_LOCKED: frozenset(),
        WorldType.VOID_POCKET: frozenset({WorldTypeTrait.DIVINE_WORLDS, WorldTypeTrait.SKYLESS_WORLDS}),
        WorldType.GODS_PALACE: frozenset({WorldTypeTrait.DIVINE_WORLDS, WorldTypeTrait.SKYLESS_WORLDS}),
        WorldType.GENERATION_SHIP: frozenset({WorldTypeTrait.DIVINE_WORLDS, WorldTypeTrait.SKYLESS_WORLDS}),
        WorldType.CORPSE_WORLD: frozenset({WorldTypeTrait.LIFELESS_WORLDS}),
        WorldType.SUPER_EARTH: frozenset(),
        WorldType.ICE_GIANT: frozenset({WorldTypeTrait.GAS_WORLDS, WorldTypeTrait.GIANTS}),
        WorldType.HOT_GIANT: frozenset({WorldTypeTrait.GAS_WORLDS}),
        WorldType.IRON: frozenset(),
        WorldType.CARBON: frozenset(),
        WorldType.GREENHOUSE: frozenset({WorldTypeTrait.HARSH_WORLDS, WorldTypeTrait.VOLCANIC_WORLDS}),
        WorldType.DWARF_PLANET: frozenset({WorldTypeTrait.HARSH_WORLDS, WorldTypeTrait.TWO_SEASON_WORLDS}),
        WorldType.CHTHONIAN: frozenset({WorldTypeTrait.BURIED_WORLDS, WorldTypeTrait.LIFELESS_WORLDS, WorldTypeTrait.VOLCANIC_WORLDS}),
        WorldType.HYCEAN: frozenset(),
        WorldType.JUNGLE: frozenset(),
        WorldType.FORGE: frozenset({WorldTypeTrait.HARSH_WORLDS}),
        WorldType.FUNGAL: frozenset({WorldTypeTrait.BURIED_WORLDS}),
        WorldType.SHATTERED: frozenset({WorldTypeTrait.BROKEN_WORLDS}),
        WorldType.HOLLOW: frozenset({WorldTypeTrait.BURIED_WORLDS, WorldTypeTrait.SKYLESS_WORLDS}),
        WorldType.ICE_SHELL: frozenset({WorldTypeTrait.BURIED_WORLDS, WorldTypeTrait.COLD_WORLDS, WorldTypeTrait.HARSH_WORLDS}),
        WorldType.METHANE: frozenset({WorldTypeTrait.HARSH_WORLDS}),
    },
)


YOUTH_PURPOSE_TRAITS: Mapping[YouthPurpose, frozenset[YouthPurposeTrait]] = total(
    YouthPurpose,
    {
        YouthPurpose.SPORT: frozenset(),
        YouthPurpose.SERVICE: frozenset(),
        YouthPurpose.COURTSHIP: frozenset(),
        YouthPurpose.DEFENCE: frozenset(),
        YouthPurpose.FAITH: frozenset(),
        YouthPurpose.MISCHIEF: frozenset({YouthPurposeTrait.DELINQUENT, YouthPurposeTrait.UNRULY}),
        YouthPurpose.CRIME: frozenset({YouthPurposeTrait.DELINQUENT, YouthPurposeTrait.UNRULY}),
        YouthPurpose.POLITICS: frozenset({YouthPurposeTrait.UNRULY}),
    },
)

CARRYING_ROUTES = tuple(status for status, traits in TRADE_ROUTE_STATUS_TRAITS.items() if TradeRouteStatusTrait.CARRYING in traits)
