from dataclasses import dataclass, field

from aerona.rules.registry.achievements import AchievementRules
from aerona.rules.registry.affairs import AffairsRules
from aerona.rules.registry.agents import AgentsRules
from aerona.rules.registry.ages import AgeRules, ArcRules, EcoTransformationRules, FormationRules, LongSeasonRules
from aerona.rules.registry.agrarian import (
    BoserupRules,
    BrandRules,
    CentralPlaceRules,
    CommonsRules,
    FamineFoodRules,
    GameLawRules,
    KeystoneResourceRules,
    NutrientRules,
    PerennialRules,
    ReconstructionRules,
    ReliefRules,
    ResilienceRules,
    ThunenRules,
)
from aerona.rules.registry.apocalypse import ApocalypseRules
from aerona.rules.registry.arcana import (
    EnchantedItemRules,
    GlobalEnchantmentRules,
    LongevityRules,
    MythCouplingRules,
    ParadigmRules,
    SpellEnvironmentRules,
    SpellGrammarRules,
    SpellResistanceRules,
    VisRules,
    WarpingRules,
)
from aerona.rules.registry.archive import ArchiveRules
from aerona.rules.registry.army_depth import ArmyDepthRules
from aerona.rules.registry.arts import (
    ArtMarketRules,
    ArtMovementRules,
    AstrologyRules,
    CanonRules,
    CircusFactionRules,
    ConstructRules,
    ForgeryRules,
    MonsterContractRules,
    PunitiveRemakingRules,
    SportRules,
)
from aerona.rules.registry.ascension import AscensionRules
from aerona.rules.registry.augments import AugmentRules
from aerona.rules.registry.awakening import AwakeningRules
from aerona.rules.registry.backup import BackupRules
from aerona.rules.registry.balance import BalanceRules
from aerona.rules.registry.batch import BatchRules
from aerona.rules.registry.battle_depth import BattleDepthRules
from aerona.rules.registry.battle_tables import BattleTerrainRules, BattleWeatherRules, TacticMatchupRules
from aerona.rules.registry.belonging import IdentityRules, PeerRules, SanctuaryRules, SatireRules
from aerona.rules.registry.beyond import BeyondRules
from aerona.rules.registry.biology_variants import BiologyVariantRules
from aerona.rules.registry.body import (
    AnatomyRules,
    ArmourRules,
    BodyCustomsRules,
    CapacityRules,
    ConditionRules,
    HarmBandRules,
    HealingRules,
    InjuryRules,
    MaimedRules,
    ProstheticsRules,
)
from aerona.rules.registry.campaigns import CampaignsRules
from aerona.rules.registry.cartography import CartographyRules
from aerona.rules.registry.casualties import CasualtiesRules
from aerona.rules.registry.chronicle_audit import ChronicleAuditRules
from aerona.rules.registry.chronicle_repeat import ChronicleRepeatRules
from aerona.rules.registry.city_plan import CityPlanRules
from aerona.rules.registry.civilization import CivilizationRules
from aerona.rules.registry.climate_effects import ClimateEffectsRules
from aerona.rules.registry.climate_world_type import ClimateWorldTypeRules
from aerona.rules.registry.climes import (
    CosmopolitanRules,
    CurrentRules,
    LaunchWindowRules,
    MonsoonRules,
    OscillationRules,
    WindRules,
)
from aerona.rules.registry.collective import (
    CollectiveBehaviourRules,
    DatingRules,
    DemographicTransitionRules,
    DesignRules,
    DiasporaRules,
    GenerationRules,
    HeraldryRules,
    HistoriographyRules,
    NormRules,
    RoleNormRules,
    SexRatioRules,
    SocialLearningRules,
    StoryletRules,
    VolitionRules,
)
from aerona.rules.registry.communication import CommunicationRules
from aerona.rules.registry.content import ContentRules
from aerona.rules.registry.context import ContextRules
from aerona.rules.registry.core_rules import CoreRulesRules
from aerona.rules.registry.cosmic_costs import CosmicCostsRules
from aerona.rules.registry.cosmic_horror import CosmicHorrorRules
from aerona.rules.registry.cosmography import (
    CelestialBodyRules,
    ClusterRules,
    CosmicBeingRules,
    CosmographyRules,
    DimensionRules,
    GalaxyRules,
    JourneyRules,
    PhenomenaRules,
    RiftRules,
    StarLifeRules,
    WorldLifeRules,
)
from aerona.rules.registry.cosmography_kinds import (
    BeingKindRules,
    ClusterKindRules,
    DimensionKindRules,
    GalacticStructureRules,
    GalacticZoneRules,
    GalaxyTypeRules,
    PhenomenonKindRules,
)
from aerona.rules.registry.costs import CostsRules
from aerona.rules.registry.council import CouncilRules
from aerona.rules.registry.couplings import (
    CarrionRules,
    ClosureRules,
    CouplingRules,
    DeepSealRules,
    FashionRules,
    FieldDiplomacyRules,
    OfficeMakingRules,
    TeachingRules,
)
from aerona.rules.registry.crafts import (
    AffinityRules,
    AidRules,
    ChemistryRules,
    ClockRules,
    EmotionSpiritRules,
    GameRules,
    GroundRules,
    InsuranceRules,
    NumeracyRules,
    RightsRules,
    SympathyRules,
)
from aerona.rules.registry.creation_base_cost import CreationBaseCostRules
from aerona.rules.registry.creator import CreatorRules
from aerona.rules.registry.creature_traits import CreatureTraitsRules
from aerona.rules.registry.creatures import CreaturesRules
from aerona.rules.registry.culture import CultureRules
from aerona.rules.registry.customs import (
    AgeSetRules,
    BorderRules,
    CitizenshipRules,
    CommuteRules,
    CooperativeRules,
    EvidenceRules,
    IntoxicationRules,
    MarkRules,
    MeasureRules,
    NamingCustomRules,
    PoorReliefRules,
    RevivalRules,
    TavernRules,
    TimeBudgetRules,
    WelfareRules,
)
from aerona.rules.registry.cycles import (
    AsabiyyaRules,
    ChallengeResponseRules,
    CircuitRules,
    CorveeRules,
    IndentureRules,
    KinshipSystemRules,
    LabourRegimeRules,
    LegacyTraitRules,
    LongPlanRules,
    ManumissionRules,
    MarriageAllianceRules,
    NomadismRules,
    PotlatchRules,
    ReciprocityRules,
    ReproductionSystemRules,
    SacrificeRules,
    SlaveMarketRules,
    StructuralDemographyRules,
)
from aerona.rules.registry.death import DeathRules
from aerona.rules.registry.deep_life import DeepLifeRules
from aerona.rules.registry.deep_world import DeepWorldRules
from aerona.rules.registry.demography import CohortsRules, DemographyRules, LabourRules, MobilityRules, PeopleRules
from aerona.rules.registry.diplomacy import DiplomacyRules
from aerona.rules.registry.disasters import DisastersRules
from aerona.rules.registry.discovery import DiscoveryRules
from aerona.rules.registry.divine import (
    AvatarRules,
    CreatorBondRules,
    DivineGrammarRules,
    DivineStandingRules,
    DivineWoundRules,
    DomainRules,
    GodRelationRules,
    NaturalLawRules,
    OuterBeingRules,
    PantheonLifeRules,
    SonGoalRules,
)
from aerona.rules.registry.doctrine import (
    AfterlifeRules,
    DoctrineRules,
    InquisitionRules,
    MissionsRules,
    NecromancyRules,
    SpiritsRules,
    TithesRules,
    ZealRules,
)
from aerona.rules.registry.dominion import (
    DivineCreatureRules,
    DominionRules,
    GodDesignRules,
    GodImageRules,
    MagicSiteRules,
    MiracleImpressionRules,
    ThroneRules,
    WorshipViewRules,
)
from aerona.rules.registry.ecology import EcologyRules
from aerona.rules.registry.economy import EconomyRules
from aerona.rules.registry.effect_packages import EffectPackageRules
from aerona.rules.registry.empty_world import EmptyWorldRules
from aerona.rules.registry.engagement import EngagementRules
from aerona.rules.registry.engine_phases import EnginePhasesRules
from aerona.rules.registry.environment import (
    CalendarsRules,
    EngineBudgetRules,
    EnvironmentRules,
    HarvestRules,
    LandUseRules,
    PassabilityRules,
    ScarsRules,
    SeasonsRules,
)
from aerona.rules.registry.epidemiology import EpidemiologyRules
from aerona.rules.registry.epoch_flow import EpochFlowRules
from aerona.rules.registry.eras import EraRules, ProgrammeRules
from aerona.rules.registry.espionage import EspionageRules
from aerona.rules.registry.essence import EssenceRules
from aerona.rules.registry.estates import CompanyRules, EstateRules, GuildRules, MovementRules, OrderRules
from aerona.rules.registry.events import EventsRules
from aerona.rules.registry.evolution import (
    BiomeSuccessionRules,
    CarrierRules,
    CureResearchRules,
    CycleRules,
    FeralRules,
    KeystoneRules,
    LandShapingRules,
    LineageRules,
    NicheRules,
    PathogenRules,
    PlagueResponseRules,
    SpilloverRules,
    TraitEvolutionRules,
    TrophicRules,
    VaccinationRules,
    VectorRules,
)
from aerona.rules.registry.exploration import ExplorationRules
from aerona.rules.registry.factions import BanditryRules, FactionsRules, IntrigueRules, MercenariesRules
from aerona.rules.registry.faith import FaithRules
from aerona.rules.registry.fate import FateRules
from aerona.rules.registry.finance import AccessRules, ArbitrageRules, CreditRules, ElasticityRules, SpeculationRules, TradePolicyRules
from aerona.rules.registry.flora import FloraRules
from aerona.rules.registry.folk import BiologyRules, CustomsRules
from aerona.rules.registry.folk_belief import FolkBeliefRules
from aerona.rules.registry.folkways import BiasRules, EverydayMishapRules, MishapRules, NutritionRules, PurityRules, WitchcraftRules
from aerona.rules.registry.foreign_gods import ForeignGodsRules
from aerona.rules.registry.fossils import FossilRules
from aerona.rules.registry.gardens import GardenRules
from aerona.rules.registry.gatherings import CollectionRules, GatheringRules
from aerona.rules.registry.genesis import GenesisRules
from aerona.rules.registry.genetics import GeneticsRules, GiftRules, HouseholdRules
from aerona.rules.registry.geography import GeographyRules
from aerona.rules.registry.geomorphology import GeomorphologyRules
from aerona.rules.registry.goals import GoalsRules
from aerona.rules.registry.god_actions import GodActionsRules
from aerona.rules.registry.god_hand import GodHandRules
from aerona.rules.registry.god_power import GodPowerRules
from aerona.rules.registry.goods_kinds import GoodsRules
from aerona.rules.registry.guide import GuideRules
from aerona.rules.registry.harshness import HarshnessRules
from aerona.rules.registry.heroes import HeroesRules
from aerona.rules.registry.honours import UnitHonourRules, VeteranRules
from aerona.rules.registry.husbandry import HusbandryRules
from aerona.rules.registry.image_gen import ImageGenRules
from aerona.rules.registry.incitement import IncitementRules
from aerona.rules.registry.industry import (
    ContrabandRules,
    DrinkRules,
    EnergyRules,
    FoodChainRules,
    MethodRules,
    MineRules,
    OwnershipRules,
    PollutionRules,
    QualityRules,
    StoreRules,
    SubstitutionRules,
)
from aerona.rules.registry.intervention_costs import InterventionCostsRules
from aerona.rules.registry.intervention_effects import InterventionEffectsRules
from aerona.rules.registry.intrigue import BeliefStateRules
from aerona.rules.registry.items import EnchantmentsRules, ItemPowersRules
from aerona.rules.registry.justice import EnactmentRules, TrialRules
from aerona.rules.registry.kind_crafts import ColourRules, DressRules, HouseholdGoodsRules, MusicRules, ScentRules, SubstanceRules
from aerona.rules.registry.kinds import KindsRules
from aerona.rules.registry.knowledge import KnowledgeRules
from aerona.rules.registry.language import LanguageRules
from aerona.rules.registry.language_contact import LanguageContactRules
from aerona.rules.registry.law_depth import (
    AppealRules,
    DefectionRules,
    DivineSpyRules,
    ForensicsRules,
    JurisdictionRules,
    LegalSystemRules,
    MoleHuntRules,
    OutlawRules,
    PardonRules,
    PrecedentRules,
    PrisonRules,
    RegistryRules,
    SpyDepthRules,
)
from aerona.rules.registry.ledger import LedgerRules
from aerona.rules.registry.life_cycles import LifeCyclesRules
from aerona.rules.registry.lifecycle_ends import LifecycleEndRules
from aerona.rules.registry.limits import LimitsRules
from aerona.rules.registry.link_graph import LinkGraphRules
from aerona.rules.registry.living import (
    CloneRules,
    DesignedDiseaseRules,
    FortuneRules,
    GenomeDesignRules,
    LivingMethodRules,
    LivingProductionRules,
    LivingRules,
    SymbiontRules,
)
from aerona.rules.registry.loops import LoopRules
from aerona.rules.registry.lore import (
    ArtRules,
    BacklashRules,
    BeliefRules,
    CraftingRules,
    IdeologiesRules,
    InterpretersRules,
    ItemCursesRules,
    ItemRenownRules,
    ItemWearRules,
    MapsRules,
    PrestigeRules,
    PropagandaRules,
    ProphecyRules,
    RegaliaRules,
    RelicsRules,
    ResearchRules,
    RitesRules,
    ScriptRules,
    TechGraphRules,
    TechniqueEffectsRules,
    TraditionsRules,
)
from aerona.rules.registry.made_kinds import (
    ArmamentRules,
    AttractionRules,
    CosmicWoundRules,
    CuisineRules,
    DeclineRules,
    IntegrityRules,
    MegastructureRules,
    UnitTypeRules,
    VehicleRules,
)
from aerona.rules.registry.made_world import (
    AbundanceRules,
    CompanyPowerRules,
    InformationRules,
    IntrusionRules,
    MadePeopleRules,
    MadeRealmRules,
    MadeRelicRules,
    MindLawRules,
    ReplicatorRules,
    SurveillanceRules,
)
from aerona.rules.registry.market import MarketRules
from aerona.rules.registry.markets import BankingRules, MarketsRules, MoneyRules, TollsRules, TradeRoutesRules
from aerona.rules.registry.materials import MaterialsRules
from aerona.rules.registry.means import (
    BuildingMaterialRules,
    ContainerRules,
    NavigationRules,
    SecurityRules,
    WaterLiftingRules,
    WritingMediaRules,
)
from aerona.rules.registry.mechanics import MechanicsRules
from aerona.rules.registry.metrics import MetricsRules
from aerona.rules.registry.military import (
    AttritionRules,
    CaptivityRules,
    DuelsRules,
    LogisticsRules,
    MilitaryUnitsRules,
    MoraleRules,
    NavalRules,
    OccupationRules,
    PeaceRules,
    SiegecraftRules,
    TacticsRules,
    TerrainEffectsRules,
    VendettaRules,
    WarAimsRules,
    WarWearinessRules,
    WeatherBattleEffectsRules,
)
from aerona.rules.registry.mind import (
    AspirationsRules,
    CareersRules,
    CultureDriftRules,
    DreamRules,
    EthicsRules,
    GriefRules,
    IdeasRules,
    MemoryRules,
    MindSplitRules,
    NeedsDepthRules,
    NeedsRules,
    OpinionRules,
    PreferencesRules,
    SkillsRules,
    ThoughtsRules,
    TraitsRules,
)
from aerona.rules.registry.minds import ContinuityRules, InterfaceRules, MindAwakeningRules, MindMakingRules, MindRules, MindWillRules
from aerona.rules.registry.model import ModelRules
from aerona.rules.registry.modifiers import IncidentRules, ModifiersRules
from aerona.rules.registry.monsters import CreatureAnatomyRules, MonstersRules
from aerona.rules.registry.mortal_acts import ActsRules, EthnicRules, LoyaltyRules
from aerona.rules.registry.mortal_agents import MortalAgentsRules
from aerona.rules.registry.mortal_life import AgingRules, EducationRules, FertilityRules, KinshipRules
from aerona.rules.registry.mortal_standing import EquipmentRules, PunishmentRules, SentenceRules, StandingRules
from aerona.rules.registry.mortal_tools import MortalToolsRules
from aerona.rules.registry.museums import MuseumRules
from aerona.rules.registry.mythic import (
    CosmicOfficeRules,
    GeasRules,
    HeroquestRules,
    MantlingRules,
    ServitorRules,
)
from aerona.rules.registry.naming import NamingRules
from aerona.rules.registry.narrative import NarrativeRules
from aerona.rules.registry.native_faith import NativeFaithRules
from aerona.rules.registry.nature import (
    DormancyRules,
    FermentationRules,
    IslandRules,
    MicrobeRules,
    PlantDefenceRules,
    SenseRules,
    SymbiosisRules,
    ThermoregulationRules,
)
from aerona.rules.registry.nature_kinds import BuildingRules, OfficeDutyRules, TraitRules
from aerona.rules.registry.networks import NetworkRules
from aerona.rules.registry.notifications import NotificationsRules
from aerona.rules.registry.operations import (
    AdmiraltyRules,
    AgeOfSailRules,
    CulminationRules,
    ExpeditionRules,
    LanchesterRules,
    OrderOfBattleRules,
    SupplyNetworkRules,
    TheatreRules,
)
from aerona.rules.registry.opportunities import OpportunitiesRules
from aerona.rules.registry.orders import EconomicOrderRules, ExchangeRules, PuttingOutRules, SavingRules, TourismRules
from aerona.rules.registry.pantheon import PantheonRules
from aerona.rules.registry.physics import (
    CosmicFeatureRules,
    ImpactRules,
    LifeClassRules,
    OrbitRules,
    PlanetaryClimateRules,
    StellarEvolutionRules,
    SurveyRules,
    TerraformingRules,
)
from aerona.rules.registry.places import PlacesRules
from aerona.rules.registry.politics import PoliticsRules
from aerona.rules.registry.polity import (
    AdministrationRules,
    GovernmentRules,
    HousesRules,
    LegislationRules,
    LegitimacyRules,
    OathsRules,
    OverextensionRules,
    RealmTierRules,
    RevoltsRules,
    SuccessionRules,
    TreatiesRules,
)
from aerona.rules.registry.power_unlock_levels import PowerUnlockLevelsRules
from aerona.rules.registry.powers import ConcealmentRules, MagicSystemRules, PoweredSocietyRules, PowerRules, PowerSourceRules
from aerona.rules.registry.prehistory import PrehistoryRules
from aerona.rules.registry.production import ExtractionRules, MiningHazardsRules, RefiningRules
from aerona.rules.registry.rarities import RaritiesRules
from aerona.rules.registry.rarity_gates import RarityGatesRules
from aerona.rules.registry.record_schema import RecordSchemaRules
from aerona.rules.registry.records import RecordsRules
from aerona.rules.registry.regime import (
    AcademicFreedomRules,
    BreedingPlanRules,
    ClientelismRules,
    CoupProofingRules,
    CredentialRules,
    ExaminationRules,
    LeadershipModeRules,
    LegitimacyTypeRules,
    PowerBaseRules,
    RoutinisationRules,
    SchoolLineageRules,
    SegmentaryRules,
    SelectorateRules,
    TimeHorizonRules,
    VenalityRules,
)
from aerona.rules.registry.region import HazardsRules, RegionalDangerRules, TerrainRules
from aerona.rules.registry.relations import CircleRules, ContestRules, PassionRules, PeckingRules, PersuasionRules, SocialRules
from aerona.rules.registry.religion import ReligionRules
from aerona.rules.registry.remembrance import RemembranceRules
from aerona.rules.registry.renown import ClaimRules, CurrencyRules, LocalRenownRules, LoreTradeRules
from aerona.rules.registry.reputation import ReputationRules
from aerona.rules.registry.research_depth import ResearchDepthRules
from aerona.rules.registry.routes import ChokepointsRules, RouteDangersRules, RouteSeasonsRules, SentientPactsRules, SonRoutesRules
from aerona.rules.registry.rumours import RumoursRules
from aerona.rules.registry.sacred import (
    AfterlifeBeliefRules,
    CelestialBureaucracyRules,
    DivinationRules,
    EmotionFeedingRules,
    GeniusLociRules,
    MillenarianRules,
    MysticismRules,
    PrescienceRules,
    PsychohistoryRules,
    SacramentRules,
    SecularisationRules,
    TheodicyRules,
)
from aerona.rules.registry.seasonal import SeasonalRules
from aerona.rules.registry.server import ServerRules
from aerona.rules.registry.settlement import CrimeRules, DistrictRules, FireRules, SanitationRules, TaxationRules, UrbanRules
from aerona.rules.registry.setup_wizard import SetupWizardRules
from aerona.rules.registry.sites import ExcavationRules, SiteRules
from aerona.rules.registry.sky import SkyRules
from aerona.rules.registry.society import SocietyRules
from aerona.rules.registry.society_depth import ConsumptionRules, RealmLoyaltyRules
from aerona.rules.registry.society_kinds import SocietyKindsRules
from aerona.rules.registry.son_relations import SonRelationsRules
from aerona.rules.registry.son_tools import SonToolsRules
from aerona.rules.registry.star_types import StarTypeRules
from aerona.rules.registry.statecraft import StatecraftRules
from aerona.rules.registry.storyteller import StorytellerRules
from aerona.rules.registry.stress import StressRules
from aerona.rules.registry.strike import StrikeRules
from aerona.rules.registry.structures import ConstructionRules, StructureEffectRules, StructureFunctionsRules, UpkeepRules
from aerona.rules.registry.summoning import SummoningRules
from aerona.rules.registry.theories import ArtFormsRules, NameMeaningsRules, TheoriesRules
from aerona.rules.registry.thin_b import (
    BeliefDepthRules,
    NeedsWiderRules,
    NormDepthRules,
    PreferenceDepthRules,
    RiftControlRules,
    StorytellerDepthRules,
    WitchcraftDepthRules,
)
from aerona.rules.registry.thin_sections import CommunityRelationRules
from aerona.rules.registry.time import TimeRules
from aerona.rules.registry.tissues import TissueRules
from aerona.rules.registry.titles import TitleRules
from aerona.rules.registry.tongues import (
    DecipherRules,
    DivineTongueRules,
    GrammarRules,
    LanguagePolicyRules,
    ModalityRules,
    PidginRules,
    ScriptEvolutionRules,
    SemanticDriftRules,
    SoundChangeRules,
)
from aerona.rules.registry.trade import TradeRules
from aerona.rules.registry.transform import TransformRules
from aerona.rules.registry.travel import TravelRules
from aerona.rules.registry.travel_methods import TravelMethodsRules
from aerona.rules.registry.ui import UiRules
from aerona.rules.registry.urban_depth import (
    CargoRules,
    ConvoyRules,
    CoverageRules,
    CrimeOrgRules,
    DesirabilityRules,
    FleetRules,
    HomelessRules,
    HousingEvolutionRules,
    MagicalOrderRules,
    ManipulationRules,
    MorphologyRules,
    PortRules,
    PreservationRules,
    PreventionRules,
    TradingPostRules,
    TurfRules,
)
from aerona.rules.registry.war_conduct import WarConductRules
from aerona.rules.registry.war_depth import (
    BattleMagicRules,
    CampaignDepthRules,
    CaptiveDepthRules,
    LevyRules,
    SeafaringRules,
    SiegeDepthRules,
    SonMilitaryRules,
    WarFinanceRules,
)
from aerona.rules.registry.weather import WeatherRules
from aerona.rules.registry.wilds import (
    BeastsRules,
    DomesticationRules,
    ExtinctionRules,
    FoodWebRules,
    HabitatRules,
    PestsRules,
    SpeciesNatureRules,
    TotemsRules,
)
from aerona.rules.registry.wonders import WondersRules
from aerona.rules.registry.world_balance import WorldBalanceRules
from aerona.rules.registry.world_birth import WorldBirthRules
from aerona.rules.registry.world_effects import WorldEffectsRules
from aerona.rules.registry.world_ends import WorldEndRules
from aerona.rules.registry.world_engine import WorldEngineRules
from aerona.rules.registry.world_epoch_transition import WorldEpochTransitionRules
from aerona.rules.registry.world_hunt import WorldHuntRules
from aerona.rules.registry.world_physics import WorldPhysicsRules
from aerona.rules.registry.world_terrain import WorldTerrainRules
from aerona.rules.registry.world_views import WorldViewRules
from aerona.rules.registry.world_war_strength import WorldWarStrengthRules


@dataclass(frozen=True)
class Rules:
    agents: AgentsRules = field(default_factory=AgentsRules)
    modifiers: ModifiersRules = field(default_factory=ModifiersRules)
    incidents: IncidentRules = field(default_factory=IncidentRules)
    environment: EnvironmentRules = field(default_factory=EnvironmentRules)
    scars: ScarsRules = field(default_factory=ScarsRules)
    regional_danger: RegionalDangerRules = field(default_factory=RegionalDangerRules)
    hazards: HazardsRules = field(default_factory=HazardsRules)
    terrain: TerrainRules = field(default_factory=TerrainRules)
    passability: PassabilityRules = field(default_factory=PassabilityRules)
    seasons: SeasonsRules = field(default_factory=SeasonsRules)
    land_use: LandUseRules = field(default_factory=LandUseRules)
    harvest: HarvestRules = field(default_factory=HarvestRules)
    calendars: CalendarsRules = field(default_factory=CalendarsRules)
    engine_budget: EngineBudgetRules = field(default_factory=EngineBudgetRules)
    weather: WeatherRules = field(default_factory=WeatherRules)
    seasonal: SeasonalRules = field(default_factory=SeasonalRules)
    anatomy: AnatomyRules = field(default_factory=AnatomyRules)
    injury: InjuryRules = field(default_factory=InjuryRules)
    capacities: CapacityRules = field(default_factory=CapacityRules)
    healing: HealingRules = field(default_factory=HealingRules)
    armour: ArmourRules = field(default_factory=ArmourRules)
    strike: StrikeRules = field(default_factory=StrikeRules)
    tissues: TissueRules = field(default_factory=TissueRules)
    effect_packages: EffectPackageRules = field(default_factory=EffectPackageRules)
    nutrition: NutritionRules = field(default_factory=NutritionRules)
    biases: BiasRules = field(default_factory=BiasRules)
    purity: PurityRules = field(default_factory=PurityRules)
    mishaps: MishapRules = field(default_factory=MishapRules)
    witchcraft: WitchcraftRules = field(default_factory=WitchcraftRules)
    revivals: RevivalRules = field(default_factory=RevivalRules)
    intoxication: IntoxicationRules = field(default_factory=IntoxicationRules)
    marks: MarkRules = field(default_factory=MarkRules)
    time_budgets: TimeBudgetRules = field(default_factory=TimeBudgetRules)
    naming_customs: NamingCustomRules = field(default_factory=NamingCustomRules)
    age_sets: AgeSetRules = field(default_factory=AgeSetRules)
    taverns: TavernRules = field(default_factory=TavernRules)
    welfare: WelfareRules = field(default_factory=WelfareRules)
    commuting: CommuteRules = field(default_factory=CommuteRules)
    cooperatives: CooperativeRules = field(default_factory=CooperativeRules)
    evidence: EvidenceRules = field(default_factory=EvidenceRules)
    citizenship: CitizenshipRules = field(default_factory=CitizenshipRules)
    borders: BorderRules = field(default_factory=BorderRules)
    poor_relief: PoorReliefRules = field(default_factory=PoorReliefRules)
    measures: MeasureRules = field(default_factory=MeasureRules)
    grounds: GroundRules = field(default_factory=GroundRules)
    chemistry: ChemistryRules = field(default_factory=ChemistryRules)
    insurance: InsuranceRules = field(default_factory=InsuranceRules)
    incorporeal: RightsRules = field(default_factory=RightsRules)
    aids: AidRules = field(default_factory=AidRules)
    clocks: ClockRules = field(default_factory=ClockRules)
    games: GameRules = field(default_factory=GameRules)
    numeracy: NumeracyRules = field(default_factory=NumeracyRules)
    affinities: AffinityRules = field(default_factory=AffinityRules)
    sympathy: SympathyRules = field(default_factory=SympathyRules)
    emotion_spirits: EmotionSpiritRules = field(default_factory=EmotionSpiritRules)
    winds: WindRules = field(default_factory=WindRules)
    monsoons: MonsoonRules = field(default_factory=MonsoonRules)
    oscillations: OscillationRules = field(default_factory=OscillationRules)
    currents: CurrentRules = field(default_factory=CurrentRules)
    launch_windows: LaunchWindowRules = field(default_factory=LaunchWindowRules)
    cosmopolitan: CosmopolitanRules = field(default_factory=CosmopolitanRules)
    identities: IdentityRules = field(default_factory=IdentityRules)
    peer_groups: PeerRules = field(default_factory=PeerRules)
    sanctuary: SanctuaryRules = field(default_factory=SanctuaryRules)
    satire: SatireRules = field(default_factory=SatireRules)
    eras: EraRules = field(default_factory=EraRules)
    programmes: ProgrammeRules = field(default_factory=ProgrammeRules)
    microbes: MicrobeRules = field(default_factory=MicrobeRules)
    fermentation: FermentationRules = field(default_factory=FermentationRules)
    symbiosis: SymbiosisRules = field(default_factory=SymbiosisRules)
    dormancy: DormancyRules = field(default_factory=DormancyRules)
    thermoregulation: ThermoregulationRules = field(default_factory=ThermoregulationRules)
    senses: SenseRules = field(default_factory=SenseRules)
    plant_defences: PlantDefenceRules = field(default_factory=PlantDefenceRules)
    island_rule: IslandRules = field(default_factory=IslandRules)
    body_customs: BodyCustomsRules = field(default_factory=BodyCustomsRules)
    conditions: ConditionRules = field(default_factory=ConditionRules)
    prosthetics: ProstheticsRules = field(default_factory=ProstheticsRules)
    maimed: MaimedRules = field(default_factory=MaimedRules)
    culture_drift: CultureDriftRules = field(default_factory=CultureDriftRules)
    traits: TraitsRules = field(default_factory=TraitsRules)
    skills: SkillsRules = field(default_factory=SkillsRules)
    mind_split: MindSplitRules = field(default_factory=MindSplitRules)
    ideas: IdeasRules = field(default_factory=IdeasRules)
    needs_depth: NeedsDepthRules = field(default_factory=NeedsDepthRules)
    needs_wider: NeedsWiderRules = field(default_factory=NeedsWiderRules)
    preference_depth: PreferenceDepthRules = field(default_factory=PreferenceDepthRules)
    belief_depth: BeliefDepthRules = field(default_factory=BeliefDepthRules)
    storyteller_depth: StorytellerDepthRules = field(default_factory=StorytellerDepthRules)
    rift_control: RiftControlRules = field(default_factory=RiftControlRules)
    norm_depth: NormDepthRules = field(default_factory=NormDepthRules)
    witchcraft_depth: WitchcraftDepthRules = field(default_factory=WitchcraftDepthRules)
    thoughts: ThoughtsRules = field(default_factory=ThoughtsRules)
    grief: GriefRules = field(default_factory=GriefRules)
    dreams: DreamRules = field(default_factory=DreamRules)
    preferences: PreferencesRules = field(default_factory=PreferencesRules)
    ethics: EthicsRules = field(default_factory=EthicsRules)
    aspirations: AspirationsRules = field(default_factory=AspirationsRules)
    social: SocialRules = field(default_factory=SocialRules)
    circles: CircleRules = field(default_factory=CircleRules)
    passions: PassionRules = field(default_factory=PassionRules)
    persuasion: PersuasionRules = field(default_factory=PersuasionRules)
    pecking: PeckingRules = field(default_factory=PeckingRules)
    contests: ContestRules = field(default_factory=ContestRules)
    methods: MethodRules = field(default_factory=MethodRules)
    energy: EnergyRules = field(default_factory=EnergyRules)
    pollution: PollutionRules = field(default_factory=PollutionRules)
    stores: StoreRules = field(default_factory=StoreRules)
    quality: QualityRules = field(default_factory=QualityRules)
    substitution: SubstitutionRules = field(default_factory=SubstitutionRules)
    ownership: OwnershipRules = field(default_factory=OwnershipRules)
    drink: DrinkRules = field(default_factory=DrinkRules)
    mines: MineRules = field(default_factory=MineRules)
    food_chain: FoodChainRules = field(default_factory=FoodChainRules)
    contraband: ContrabandRules = field(default_factory=ContrabandRules)
    market_access: AccessRules = field(default_factory=AccessRules)
    trade_policy: TradePolicyRules = field(default_factory=TradePolicyRules)
    credit: CreditRules = field(default_factory=CreditRules)
    speculation: SpeculationRules = field(default_factory=SpeculationRules)
    genetics: GeneticsRules = field(default_factory=GeneticsRules)
    gift: GiftRules = field(default_factory=GiftRules)
    households: HouseholdRules = field(default_factory=HouseholdRules)
    belief_state: BeliefStateRules = field(default_factory=BeliefStateRules)
    communication: CommunicationRules = field(default_factory=CommunicationRules)
    titles: TitleRules = field(default_factory=TitleRules)
    estates: EstateRules = field(default_factory=EstateRules)
    movements: MovementRules = field(default_factory=MovementRules)
    companies: CompanyRules = field(default_factory=CompanyRules)
    battle_depth: BattleDepthRules = field(default_factory=BattleDepthRules)
    army_depth: ArmyDepthRules = field(default_factory=ArmyDepthRules)
    gatherings: GatheringRules = field(default_factory=GatheringRules)
    dominion: DominionRules = field(default_factory=DominionRules)
    miracle_impression: MiracleImpressionRules = field(default_factory=MiracleImpressionRules)
    worship_views: WorshipViewRules = field(default_factory=WorshipViewRules)
    god_images: GodImageRules = field(default_factory=GodImageRules)
    thrones: ThroneRules = field(default_factory=ThroneRules)
    magic_sites: MagicSiteRules = field(default_factory=MagicSiteRules)
    divine_creatures: DivineCreatureRules = field(default_factory=DivineCreatureRules)
    god_design: GodDesignRules = field(default_factory=GodDesignRules)
    spell_grammar: SpellGrammarRules = field(default_factory=SpellGrammarRules)
    vis: VisRules = field(default_factory=VisRules)
    spell_resistance: SpellResistanceRules = field(default_factory=SpellResistanceRules)
    paradigms: ParadigmRules = field(default_factory=ParadigmRules)
    myth_coupling: MythCouplingRules = field(default_factory=MythCouplingRules)
    spell_environment: SpellEnvironmentRules = field(default_factory=SpellEnvironmentRules)
    warping: WarpingRules = field(default_factory=WarpingRules)
    enchanted_items: EnchantedItemRules = field(default_factory=EnchantedItemRules)
    longevity: LongevityRules = field(default_factory=LongevityRules)
    global_enchantments: GlobalEnchantmentRules = field(default_factory=GlobalEnchantmentRules)
    heroquests: HeroquestRules = field(default_factory=HeroquestRules)
    mantling: MantlingRules = field(default_factory=MantlingRules)
    servitors: ServitorRules = field(default_factory=ServitorRules)
    geasa: GeasRules = field(default_factory=GeasRules)
    cosmic_offices: CosmicOfficeRules = field(default_factory=CosmicOfficeRules)
    sound_changes: SoundChangeRules = field(default_factory=SoundChangeRules)
    grammar: GrammarRules = field(default_factory=GrammarRules)
    semantic_drift: SemanticDriftRules = field(default_factory=SemanticDriftRules)
    script_evolution: ScriptEvolutionRules = field(default_factory=ScriptEvolutionRules)
    decipherment: DecipherRules = field(default_factory=DecipherRules)
    pidgins: PidginRules = field(default_factory=PidginRules)
    language_policy: LanguagePolicyRules = field(default_factory=LanguagePolicyRules)
    modality: ModalityRules = field(default_factory=ModalityRules)
    divine_tongues: DivineTongueRules = field(default_factory=DivineTongueRules)
    trait_evolution: TraitEvolutionRules = field(default_factory=TraitEvolutionRules)
    niches: NicheRules = field(default_factory=NicheRules)
    trophic: TrophicRules = field(default_factory=TrophicRules)
    keystones: KeystoneRules = field(default_factory=KeystoneRules)
    feral: FeralRules = field(default_factory=FeralRules)
    lineages: LineageRules = field(default_factory=LineageRules)
    pathogen_evolution: PathogenRules = field(default_factory=PathogenRules)
    vectors: VectorRules = field(default_factory=VectorRules)
    carriers: CarrierRules = field(default_factory=CarrierRules)
    spillover: SpilloverRules = field(default_factory=SpilloverRules)
    plague_responses: PlagueResponseRules = field(default_factory=PlagueResponseRules)
    vaccination: VaccinationRules = field(default_factory=VaccinationRules)
    cure_research: CureResearchRules = field(default_factory=CureResearchRules)
    biome_succession: BiomeSuccessionRules = field(default_factory=BiomeSuccessionRules)
    world_cycles: CycleRules = field(default_factory=CycleRules)
    land_shaping: LandShapingRules = field(default_factory=LandShapingRules)
    desirability: DesirabilityRules = field(default_factory=DesirabilityRules)
    city_plan: CityPlanRules = field(default_factory=CityPlanRules)
    coverage: CoverageRules = field(default_factory=CoverageRules)
    housing_evolution: HousingEvolutionRules = field(default_factory=HousingEvolutionRules)
    homelessness: HomelessRules = field(default_factory=HomelessRules)
    prevention: PreventionRules = field(default_factory=PreventionRules)
    morphology: MorphologyRules = field(default_factory=MorphologyRules)
    turf: TurfRules = field(default_factory=TurfRules)
    crime_orgs: CrimeOrgRules = field(default_factory=CrimeOrgRules)
    trading_posts: TradingPostRules = field(default_factory=TradingPostRules)
    magical_orders: MagicalOrderRules = field(default_factory=MagicalOrderRules)
    convoys: ConvoyRules = field(default_factory=ConvoyRules)
    fleets: FleetRules = field(default_factory=FleetRules)
    cargo: CargoRules = field(default_factory=CargoRules)
    preservation: PreservationRules = field(default_factory=PreservationRules)
    ports: PortRules = field(default_factory=PortRules)
    manipulation: ManipulationRules = field(default_factory=ManipulationRules)
    legal_systems: LegalSystemRules = field(default_factory=LegalSystemRules)
    precedents: PrecedentRules = field(default_factory=PrecedentRules)
    appeals: AppealRules = field(default_factory=AppealRules)
    registries: RegistryRules = field(default_factory=RegistryRules)
    jurisdictions: JurisdictionRules = field(default_factory=JurisdictionRules)
    pardons: PardonRules = field(default_factory=PardonRules)
    outlaws: OutlawRules = field(default_factory=OutlawRules)
    prisons: PrisonRules = field(default_factory=PrisonRules)
    collective_behaviour: CollectiveBehaviourRules = field(default_factory=CollectiveBehaviourRules)
    historiography: HistoriographyRules = field(default_factory=HistoriographyRules)
    storylets: StoryletRules = field(default_factory=StoryletRules)
    norms: NormRules = field(default_factory=NormRules)
    volition: VolitionRules = field(default_factory=VolitionRules)
    social_learning: SocialLearningRules = field(default_factory=SocialLearningRules)
    generations: GenerationRules = field(default_factory=GenerationRules)
    diaspora: DiasporaRules = field(default_factory=DiasporaRules)
    demographic_transition: DemographicTransitionRules = field(default_factory=DemographicTransitionRules)
    sex_ratio: SexRatioRules = field(default_factory=SexRatioRules)
    role_norms: RoleNormRules = field(default_factory=RoleNormRules)
    dating: DatingRules = field(default_factory=DatingRules)
    heraldry: HeraldryRules = field(default_factory=HeraldryRules)
    designs: DesignRules = field(default_factory=DesignRules)
    spy_depth: SpyDepthRules = field(default_factory=SpyDepthRules)
    mole_hunts: MoleHuntRules = field(default_factory=MoleHuntRules)
    defections: DefectionRules = field(default_factory=DefectionRules)
    forensics: ForensicsRules = field(default_factory=ForensicsRules)
    divine_spies: DivineSpyRules = field(default_factory=DivineSpyRules)
    collections: CollectionRules = field(default_factory=CollectionRules)
    storyteller: StorytellerRules = field(default_factory=StorytellerRules)
    sites: SiteRules = field(default_factory=SiteRules)
    excavations: ExcavationRules = field(default_factory=ExcavationRules)
    war_conduct: WarConductRules = field(default_factory=WarConductRules)
    structural_demography: StructuralDemographyRules = field(default_factory=StructuralDemographyRules)
    asabiyya: AsabiyyaRules = field(default_factory=AsabiyyaRules)
    challenge_response: ChallengeResponseRules = field(default_factory=ChallengeResponseRules)
    long_plans: LongPlanRules = field(default_factory=LongPlanRules)
    reciprocity: ReciprocityRules = field(default_factory=ReciprocityRules)
    potlatch: PotlatchRules = field(default_factory=PotlatchRules)
    ceremonial_circuits: CircuitRules = field(default_factory=CircuitRules)
    sacrifice_exchange: SacrificeRules = field(default_factory=SacrificeRules)
    kinship_systems: KinshipSystemRules = field(default_factory=KinshipSystemRules)
    marriage_alliance: MarriageAllianceRules = field(default_factory=MarriageAllianceRules)
    reproduction_systems: ReproductionSystemRules = field(default_factory=ReproductionSystemRules)
    nomadism: NomadismRules = field(default_factory=NomadismRules)
    legacy_traits: LegacyTraitRules = field(default_factory=LegacyTraitRules)
    labour_regimes: LabourRegimeRules = field(default_factory=LabourRegimeRules)
    corvee: CorveeRules = field(default_factory=CorveeRules)
    indenture: IndentureRules = field(default_factory=IndentureRules)
    slave_markets: SlaveMarketRules = field(default_factory=SlaveMarketRules)
    manumission: ManumissionRules = field(default_factory=ManumissionRules)
    selectorate: SelectorateRules = field(default_factory=SelectorateRules)
    legitimacy_types: LegitimacyTypeRules = field(default_factory=LegitimacyTypeRules)
    charisma_routinisation: RoutinisationRules = field(default_factory=RoutinisationRules)
    time_horizon: TimeHorizonRules = field(default_factory=TimeHorizonRules)
    clientelism: ClientelismRules = field(default_factory=ClientelismRules)
    venality: VenalityRules = field(default_factory=VenalityRules)
    power_bases: PowerBaseRules = field(default_factory=PowerBaseRules)
    coup_proofing: CoupProofingRules = field(default_factory=CoupProofingRules)
    leadership_modes: LeadershipModeRules = field(default_factory=LeadershipModeRules)
    segmentary_lineages: SegmentaryRules = field(default_factory=SegmentaryRules)
    breeding_plans: BreedingPlanRules = field(default_factory=BreedingPlanRules)
    examinations: ExaminationRules = field(default_factory=ExaminationRules)
    credentials: CredentialRules = field(default_factory=CredentialRules)
    academic_freedom: AcademicFreedomRules = field(default_factory=AcademicFreedomRules)
    school_lineages: SchoolLineageRules = field(default_factory=SchoolLineageRules)
    thunen: ThunenRules = field(default_factory=ThunenRules)
    central_places: CentralPlaceRules = field(default_factory=CentralPlaceRules)
    boserup: BoserupRules = field(default_factory=BoserupRules)
    nutrients: NutrientRules = field(default_factory=NutrientRules)
    perennials: PerennialRules = field(default_factory=PerennialRules)
    commons: CommonsRules = field(default_factory=CommonsRules)
    game_laws: GameLawRules = field(default_factory=GameLawRules)
    famine_foods: FamineFoodRules = field(default_factory=FamineFoodRules)
    resilience: ResilienceRules = field(default_factory=ResilienceRules)
    relief: ReliefRules = field(default_factory=ReliefRules)
    reconstruction: ReconstructionRules = field(default_factory=ReconstructionRules)
    keystone_resource: KeystoneResourceRules = field(default_factory=KeystoneResourceRules)
    armament: ArmamentRules = field(default_factory=ArmamentRules)
    vehicles: VehicleRules = field(default_factory=VehicleRules)
    integrity: IntegrityRules = field(default_factory=IntegrityRules)
    megastructures: MegastructureRules = field(default_factory=MegastructureRules)
    unit_types: UnitTypeRules = field(default_factory=UnitTypeRules)
    cuisine: CuisineRules = field(default_factory=CuisineRules)
    decline: DeclineRules = field(default_factory=DeclineRules)
    attraction: AttractionRules = field(default_factory=AttractionRules)
    cosmic_wounds: CosmicWoundRules = field(default_factory=CosmicWoundRules)
    brands: BrandRules = field(default_factory=BrandRules)
    order_of_battle: OrderOfBattleRules = field(default_factory=OrderOfBattleRules)
    supply_network: SupplyNetworkRules = field(default_factory=SupplyNetworkRules)
    culmination: CulminationRules = field(default_factory=CulminationRules)
    theatres: TheatreRules = field(default_factory=TheatreRules)
    lanchester: LanchesterRules = field(default_factory=LanchesterRules)
    age_of_sail: AgeOfSailRules = field(default_factory=AgeOfSailRules)
    engagement: EngagementRules = field(default_factory=EngagementRules)
    admiralty: AdmiraltyRules = field(default_factory=AdmiraltyRules)
    expeditions: ExpeditionRules = field(default_factory=ExpeditionRules)
    genius_loci: GeniusLociRules = field(default_factory=GeniusLociRules)
    celestial_bureaucracy: CelestialBureaucracyRules = field(default_factory=CelestialBureaucracyRules)
    mysticism: MysticismRules = field(default_factory=MysticismRules)
    millenarianism: MillenarianRules = field(default_factory=MillenarianRules)
    theodicy: TheodicyRules = field(default_factory=TheodicyRules)
    sacraments: SacramentRules = field(default_factory=SacramentRules)
    afterlife_belief: AfterlifeBeliefRules = field(default_factory=AfterlifeBeliefRules)
    secularisation: SecularisationRules = field(default_factory=SecularisationRules)
    divination: DivinationRules = field(default_factory=DivinationRules)
    prescience: PrescienceRules = field(default_factory=PrescienceRules)
    psychohistory: PsychohistoryRules = field(default_factory=PsychohistoryRules)
    emotion_feeding: EmotionFeedingRules = field(default_factory=EmotionFeedingRules)
    art_markets: ArtMarketRules = field(default_factory=ArtMarketRules)
    forgery: ForgeryRules = field(default_factory=ForgeryRules)
    canon: CanonRules = field(default_factory=CanonRules)
    art_movements: ArtMovementRules = field(default_factory=ArtMovementRules)
    sports: SportRules = field(default_factory=SportRules)
    circus_factions: CircusFactionRules = field(default_factory=CircusFactionRules)
    constructs: ConstructRules = field(default_factory=ConstructRules)
    monster_contracts: MonsterContractRules = field(default_factory=MonsterContractRules)
    astrology: AstrologyRules = field(default_factory=AstrologyRules)
    punitive_remaking: PunitiveRemakingRules = field(default_factory=PunitiveRemakingRules)
    formation: FormationRules = field(default_factory=FormationRules)
    long_seasons: LongSeasonRules = field(default_factory=LongSeasonRules)
    eco_transformations: EcoTransformationRules = field(default_factory=EcoTransformationRules)
    ages: AgeRules = field(default_factory=AgeRules)
    arcs: ArcRules = field(default_factory=ArcRules)
    research_depth: ResearchDepthRules = field(default_factory=ResearchDepthRules)
    discovery: DiscoveryRules = field(default_factory=DiscoveryRules)
    theories: TheoriesRules = field(default_factory=TheoriesRules)
    flora: FloraRules = field(default_factory=FloraRules)
    husbandry: HusbandryRules = field(default_factory=HusbandryRules)
    domains: DomainRules = field(default_factory=DomainRules)
    son_goals: SonGoalRules = field(default_factory=SonGoalRules)
    divine_standing: DivineStandingRules = field(default_factory=DivineStandingRules)
    divine_wounds: DivineWoundRules = field(default_factory=DivineWoundRules)
    divine_grammar: DivineGrammarRules = field(default_factory=DivineGrammarRules)
    creator_bonds: CreatorBondRules = field(default_factory=CreatorBondRules)
    pantheon_life: PantheonLifeRules = field(default_factory=PantheonLifeRules)
    kinds: KindsRules = field(default_factory=KindsRules)
    typed_traits: TraitRules = field(default_factory=TraitRules)
    office_duties: OfficeDutyRules = field(default_factory=OfficeDutyRules)
    building: BuildingRules = field(default_factory=BuildingRules)
    society_kinds: SocietyKindsRules = field(default_factory=SocietyKindsRules)
    goods: GoodsRules = field(default_factory=GoodsRules)
    dress: DressRules = field(default_factory=DressRules)
    colours: ColourRules = field(default_factory=ColourRules)
    scents: ScentRules = field(default_factory=ScentRules)
    household_goods: HouseholdGoodsRules = field(default_factory=HouseholdGoodsRules)
    music: MusicRules = field(default_factory=MusicRules)
    substances: SubstanceRules = field(default_factory=SubstanceRules)
    avatars: AvatarRules = field(default_factory=AvatarRules)
    god_relations: GodRelationRules = field(default_factory=GodRelationRules)
    natural_laws: NaturalLawRules = field(default_factory=NaturalLawRules)
    outer_beings: OuterBeingRules = field(default_factory=OuterBeingRules)
    creature_anatomy: CreatureAnatomyRules = field(default_factory=CreatureAnatomyRules)
    monsters: MonstersRules = field(default_factory=MonstersRules)
    art_forms: ArtFormsRules = field(default_factory=ArtFormsRules)
    name_meanings: NameMeaningsRules = field(default_factory=NameMeaningsRules)
    holy_orders: OrderRules = field(default_factory=OrderRules)
    guild_ranks: GuildRules = field(default_factory=GuildRules)
    elasticity: ElasticityRules = field(default_factory=ElasticityRules)
    arbitrage: ArbitrageRules = field(default_factory=ArbitrageRules)
    local_renown: LocalRenownRules = field(default_factory=LocalRenownRules)
    currencies: CurrencyRules = field(default_factory=CurrencyRules)
    lore_trade: LoreTradeRules = field(default_factory=LoreTradeRules)
    claims: ClaimRules = field(default_factory=ClaimRules)
    careers: CareersRules = field(default_factory=CareersRules)
    memory: MemoryRules = field(default_factory=MemoryRules)
    opinion: OpinionRules = field(default_factory=OpinionRules)
    needs: NeedsRules = field(default_factory=NeedsRules)
    harshness: HarshnessRules = field(default_factory=HarshnessRules)
    aging: AgingRules = field(default_factory=AgingRules)
    fertility: FertilityRules = field(default_factory=FertilityRules)
    education: EducationRules = field(default_factory=EducationRules)
    kinship: KinshipRules = field(default_factory=KinshipRules)
    stress: StressRules = field(default_factory=StressRules)
    standing: StandingRules = field(default_factory=StandingRules)
    punishment: PunishmentRules = field(default_factory=PunishmentRules)
    sentences: SentenceRules = field(default_factory=SentenceRules)
    enactment: EnactmentRules = field(default_factory=EnactmentRules)
    trials: TrialRules = field(default_factory=TrialRules)
    statecraft: StatecraftRules = field(default_factory=StatecraftRules)
    affairs: AffairsRules = field(default_factory=AffairsRules)
    equipment: EquipmentRules = field(default_factory=EquipmentRules)
    loyalty: LoyaltyRules = field(default_factory=LoyaltyRules)
    acts: ActsRules = field(default_factory=ActsRules)
    ethnic: EthnicRules = field(default_factory=EthnicRules)
    casualties: CasualtiesRules = field(default_factory=CasualtiesRules)
    ecology: EcologyRules = field(default_factory=EcologyRules)
    habitat: HabitatRules = field(default_factory=HabitatRules)
    food_web: FoodWebRules = field(default_factory=FoodWebRules)
    pests: PestsRules = field(default_factory=PestsRules)
    domestication: DomesticationRules = field(default_factory=DomesticationRules)
    extinction: ExtinctionRules = field(default_factory=ExtinctionRules)
    totems: TotemsRules = field(default_factory=TotemsRules)
    beasts: BeastsRules = field(default_factory=BeastsRules)
    species_nature: SpeciesNatureRules = field(default_factory=SpeciesNatureRules)
    writing_media: WritingMediaRules = field(default_factory=WritingMediaRules)
    security: SecurityRules = field(default_factory=SecurityRules)
    water_lifting: WaterLiftingRules = field(default_factory=WaterLiftingRules)
    navigation_instruments: NavigationRules = field(default_factory=NavigationRules)
    building_materials: BuildingMaterialRules = field(default_factory=BuildingMaterialRules)
    containers: ContainerRules = field(default_factory=ContainerRules)
    saving: SavingRules = field(default_factory=SavingRules)
    exchange_rates: ExchangeRules = field(default_factory=ExchangeRules)
    economic_orders: EconomicOrderRules = field(default_factory=EconomicOrderRules)
    putting_out: PuttingOutRules = field(default_factory=PuttingOutRules)
    tourism: TourismRules = field(default_factory=TourismRules)
    unit_honours: UnitHonourRules = field(default_factory=UnitHonourRules)
    veterans: VeteranRules = field(default_factory=VeteranRules)
    world_views: WorldViewRules = field(default_factory=WorldViewRules)
    biology_variants: BiologyVariantRules = field(default_factory=BiologyVariantRules)
    lifecycle_ends: LifecycleEndRules = field(default_factory=LifecycleEndRules)
    world_ends: WorldEndRules = field(default_factory=WorldEndRules)
    prehistory: PrehistoryRules = field(default_factory=PrehistoryRules)
    transform: TransformRules = field(default_factory=TransformRules)
    couplings: CouplingRules = field(default_factory=CouplingRules)
    carrion: CarrionRules = field(default_factory=CarrionRules)
    teachings: TeachingRules = field(default_factory=TeachingRules)
    offices_made: OfficeMakingRules = field(default_factory=OfficeMakingRules)
    field_diplomacy: FieldDiplomacyRules = field(default_factory=FieldDiplomacyRules)
    deep_seals: DeepSealRules = field(default_factory=DeepSealRules)
    closures: ClosureRules = field(default_factory=ClosureRules)
    fashion: FashionRules = field(default_factory=FashionRules)
    loops: LoopRules = field(default_factory=LoopRules)
    minds: MindRules = field(default_factory=MindRules)
    mind_making: MindMakingRules = field(default_factory=MindMakingRules)
    mind_awakening: MindAwakeningRules = field(default_factory=MindAwakeningRules)
    mind_will: MindWillRules = field(default_factory=MindWillRules)
    continuity: ContinuityRules = field(default_factory=ContinuityRules)
    interfaces: InterfaceRules = field(default_factory=InterfaceRules)
    networks: NetworkRules = field(default_factory=NetworkRules)
    augments: AugmentRules = field(default_factory=AugmentRules)
    made_realms: MadeRealmRules = field(default_factory=MadeRealmRules)
    intrusion: IntrusionRules = field(default_factory=IntrusionRules)
    surveillance: SurveillanceRules = field(default_factory=SurveillanceRules)
    information: InformationRules = field(default_factory=InformationRules)
    company_power: CompanyPowerRules = field(default_factory=CompanyPowerRules)
    replicators: ReplicatorRules = field(default_factory=ReplicatorRules)
    abundance: AbundanceRules = field(default_factory=AbundanceRules)
    made_relics: MadeRelicRules = field(default_factory=MadeRelicRules)
    made_peoples: MadePeopleRules = field(default_factory=MadePeopleRules)
    mind_law: MindLawRules = field(default_factory=MindLawRules)
    power_sources: PowerSourceRules = field(default_factory=PowerSourceRules)
    magic_systems: MagicSystemRules = field(default_factory=MagicSystemRules)
    powers: PowerRules = field(default_factory=PowerRules)
    powered_society: PoweredSocietyRules = field(default_factory=PoweredSocietyRules)
    concealment: ConcealmentRules = field(default_factory=ConcealmentRules)
    living: LivingRules = field(default_factory=LivingRules)
    living_methods: LivingMethodRules = field(default_factory=LivingMethodRules)
    genome_design: GenomeDesignRules = field(default_factory=GenomeDesignRules)
    symbionts: SymbiontRules = field(default_factory=SymbiontRules)
    clones: CloneRules = field(default_factory=CloneRules)
    designed_disease: DesignedDiseaseRules = field(default_factory=DesignedDiseaseRules)
    living_production: LivingProductionRules = field(default_factory=LivingProductionRules)
    fortune: FortuneRules = field(default_factory=FortuneRules)
    harm_bands: HarmBandRules = field(default_factory=HarmBandRules)
    everyday_mishaps: EverydayMishapRules = field(default_factory=EverydayMishapRules)
    fossils: FossilRules = field(default_factory=FossilRules)
    museums: MuseumRules = field(default_factory=MuseumRules)
    gardens: GardenRules = field(default_factory=GardenRules)
    geography: GeographyRules = field(default_factory=GeographyRules)
    life_cycles: LifeCyclesRules = field(default_factory=LifeCyclesRules)
    remembrance: RemembranceRules = field(default_factory=RemembranceRules)
    world_balance: WorldBalanceRules = field(default_factory=WorldBalanceRules)
    apocalypse: ApocalypseRules = field(default_factory=ApocalypseRules)
    archive: ArchiveRules = field(default_factory=ArchiveRules)
    ascension: AscensionRules = field(default_factory=AscensionRules)
    awakening: AwakeningRules = field(default_factory=AwakeningRules)
    backup: BackupRules = field(default_factory=BackupRules)
    balance: BalanceRules = field(default_factory=BalanceRules)
    batch: BatchRules = field(default_factory=BatchRules)
    beyond: BeyondRules = field(default_factory=BeyondRules)
    campaigns: CampaignsRules = field(default_factory=CampaignsRules)
    cartography: CartographyRules = field(default_factory=CartographyRules)
    chronicle_audit: ChronicleAuditRules = field(default_factory=ChronicleAuditRules)
    chronicle_repeat: ChronicleRepeatRules = field(default_factory=ChronicleRepeatRules)
    civilization: CivilizationRules = field(default_factory=CivilizationRules)
    climate_effects: ClimateEffectsRules = field(default_factory=ClimateEffectsRules)
    climate_world_type: ClimateWorldTypeRules = field(default_factory=ClimateWorldTypeRules)
    content: ContentRules = field(default_factory=ContentRules)
    context: ContextRules = field(default_factory=ContextRules)
    core_rules: CoreRulesRules = field(default_factory=CoreRulesRules)
    cosmic_costs: CosmicCostsRules = field(default_factory=CosmicCostsRules)
    cosmic_horror: CosmicHorrorRules = field(default_factory=CosmicHorrorRules)
    costs: CostsRules = field(default_factory=CostsRules)
    council: CouncilRules = field(default_factory=CouncilRules)
    creation_base_cost: CreationBaseCostRules = field(default_factory=CreationBaseCostRules)
    creator: CreatorRules = field(default_factory=CreatorRules)
    creatures: CreaturesRules = field(default_factory=CreaturesRules)
    creature_traits: CreatureTraitsRules = field(default_factory=CreatureTraitsRules)
    culture: CultureRules = field(default_factory=CultureRules)
    death: DeathRules = field(default_factory=DeathRules)
    deep_life: DeepLifeRules = field(default_factory=DeepLifeRules)
    deep_world: DeepWorldRules = field(default_factory=DeepWorldRules)
    diplomacy: DiplomacyRules = field(default_factory=DiplomacyRules)
    disasters: DisastersRules = field(default_factory=DisastersRules)
    events: EventsRules = field(default_factory=EventsRules)
    geomorphology: GeomorphologyRules = field(default_factory=GeomorphologyRules)
    economy: EconomyRules = field(default_factory=EconomyRules)
    materials: MaterialsRules = field(default_factory=MaterialsRules)
    extraction: ExtractionRules = field(default_factory=ExtractionRules)
    refining: RefiningRules = field(default_factory=RefiningRules)
    mining_hazards: MiningHazardsRules = field(default_factory=MiningHazardsRules)
    markets: MarketsRules = field(default_factory=MarketsRules)
    money: MoneyRules = field(default_factory=MoneyRules)
    trade_routes: TradeRoutesRules = field(default_factory=TradeRoutesRules)
    banking: BankingRules = field(default_factory=BankingRules)
    tolls: TollsRules = field(default_factory=TollsRules)
    route_dangers: RouteDangersRules = field(default_factory=RouteDangersRules)
    route_seasons: RouteSeasonsRules = field(default_factory=RouteSeasonsRules)
    chokepoints: ChokepointsRules = field(default_factory=ChokepointsRules)
    sentient_pacts: SentientPactsRules = field(default_factory=SentientPactsRules)
    son_routes: SonRoutesRules = field(default_factory=SonRoutesRules)
    cohorts: CohortsRules = field(default_factory=CohortsRules)
    demography: DemographyRules = field(default_factory=DemographyRules)
    epidemiology: EpidemiologyRules = field(default_factory=EpidemiologyRules)
    urban: UrbanRules = field(default_factory=UrbanRules)
    taxation: TaxationRules = field(default_factory=TaxationRules)
    crime: CrimeRules = field(default_factory=CrimeRules)
    fire: FireRules = field(default_factory=FireRules)
    sanitation: SanitationRules = field(default_factory=SanitationRules)
    districts: DistrictRules = field(default_factory=DistrictRules)
    government: GovernmentRules = field(default_factory=GovernmentRules)
    succession: SuccessionRules = field(default_factory=SuccessionRules)
    legitimacy: LegitimacyRules = field(default_factory=LegitimacyRules)
    administration: AdministrationRules = field(default_factory=AdministrationRules)
    overextension: OverextensionRules = field(default_factory=OverextensionRules)
    revolts: RevoltsRules = field(default_factory=RevoltsRules)
    legislation: LegislationRules = field(default_factory=LegislationRules)
    houses: HousesRules = field(default_factory=HousesRules)
    oaths: OathsRules = field(default_factory=OathsRules)
    treaties: TreatiesRules = field(default_factory=TreatiesRules)
    realm_tiers: RealmTierRules = field(default_factory=RealmTierRules)
    military_units: MilitaryUnitsRules = field(default_factory=MilitaryUnitsRules)
    logistics: LogisticsRules = field(default_factory=LogisticsRules)
    attrition: AttritionRules = field(default_factory=AttritionRules)
    morale: MoraleRules = field(default_factory=MoraleRules)
    terrain_effects: TerrainEffectsRules = field(default_factory=TerrainEffectsRules)
    weather_battle_effects: WeatherBattleEffectsRules = field(default_factory=WeatherBattleEffectsRules)
    tactics: TacticsRules = field(default_factory=TacticsRules)
    battle_terrain: BattleTerrainRules = field(default_factory=BattleTerrainRules)
    battle_weather: BattleWeatherRules = field(default_factory=BattleWeatherRules)
    tactic_matchups: TacticMatchupRules = field(default_factory=TacticMatchupRules)
    battle_magic: BattleMagicRules = field(default_factory=BattleMagicRules)
    levies: LevyRules = field(default_factory=LevyRules)
    campaign_depth: CampaignDepthRules = field(default_factory=CampaignDepthRules)
    war_finance: WarFinanceRules = field(default_factory=WarFinanceRules)
    siege_depth: SiegeDepthRules = field(default_factory=SiegeDepthRules)
    captive_depth: CaptiveDepthRules = field(default_factory=CaptiveDepthRules)
    seafaring: SeafaringRules = field(default_factory=SeafaringRules)
    son_military: SonMilitaryRules = field(default_factory=SonMilitaryRules)
    interpreters: InterpretersRules = field(default_factory=InterpretersRules)
    prestige: PrestigeRules = field(default_factory=PrestigeRules)
    script: ScriptRules = field(default_factory=ScriptRules)
    belief: BeliefRules = field(default_factory=BeliefRules)
    traditions: TraditionsRules = field(default_factory=TraditionsRules)
    research: ResearchRules = field(default_factory=ResearchRules)
    tech_graph: TechGraphRules = field(default_factory=TechGraphRules)
    ideologies: IdeologiesRules = field(default_factory=IdeologiesRules)
    rites: RitesRules = field(default_factory=RitesRules)
    backlash: BacklashRules = field(default_factory=BacklashRules)
    prophecy: ProphecyRules = field(default_factory=ProphecyRules)
    crafting: CraftingRules = field(default_factory=CraftingRules)
    item_wear: ItemWearRules = field(default_factory=ItemWearRules)
    item_curses: ItemCursesRules = field(default_factory=ItemCursesRules)
    maps: MapsRules = field(default_factory=MapsRules)
    technique_effects: TechniqueEffectsRules = field(default_factory=TechniqueEffectsRules)
    item_renown: ItemRenownRules = field(default_factory=ItemRenownRules)
    regalia: RegaliaRules = field(default_factory=RegaliaRules)
    records: RecordsRules = field(default_factory=RecordsRules)
    relics: RelicsRules = field(default_factory=RelicsRules)
    rumours: RumoursRules = field(default_factory=RumoursRules)
    item_powers: ItemPowersRules = field(default_factory=ItemPowersRules)
    enchantments: EnchantmentsRules = field(default_factory=EnchantmentsRules)
    art: ArtRules = field(default_factory=ArtRules)
    propaganda: PropagandaRules = field(default_factory=PropagandaRules)
    doctrine: DoctrineRules = field(default_factory=DoctrineRules)
    zeal: ZealRules = field(default_factory=ZealRules)
    tithes: TithesRules = field(default_factory=TithesRules)
    missions: MissionsRules = field(default_factory=MissionsRules)
    inquisition: InquisitionRules = field(default_factory=InquisitionRules)
    afterlife: AfterlifeRules = field(default_factory=AfterlifeRules)
    spirits: SpiritsRules = field(default_factory=SpiritsRules)
    necromancy: NecromancyRules = field(default_factory=NecromancyRules)
    siegecraft: SiegecraftRules = field(default_factory=SiegecraftRules)
    naval: NavalRules = field(default_factory=NavalRules)
    duels: DuelsRules = field(default_factory=DuelsRules)
    captivity: CaptivityRules = field(default_factory=CaptivityRules)
    war_aims: WarAimsRules = field(default_factory=WarAimsRules)
    occupation: OccupationRules = field(default_factory=OccupationRules)
    war_weariness: WarWearinessRules = field(default_factory=WarWearinessRules)
    peace: PeaceRules = field(default_factory=PeaceRules)
    vendetta: VendettaRules = field(default_factory=VendettaRules)
    labour: LabourRules = field(default_factory=LabourRules)
    peoples: PeopleRules = field(default_factory=PeopleRules)
    biology: BiologyRules = field(default_factory=BiologyRules)
    customs: CustomsRules = field(default_factory=CustomsRules)
    mobility: MobilityRules = field(default_factory=MobilityRules)
    espionage: EspionageRules = field(default_factory=EspionageRules)
    incitement: IncitementRules = field(default_factory=IncitementRules)
    empty_world: EmptyWorldRules = field(default_factory=EmptyWorldRules)
    engine_phases: EnginePhasesRules = field(default_factory=EnginePhasesRules)
    epoch_flow: EpochFlowRules = field(default_factory=EpochFlowRules)
    essence: EssenceRules = field(default_factory=EssenceRules)
    exploration: ExplorationRules = field(default_factory=ExplorationRules)
    faith: FaithRules = field(default_factory=FaithRules)
    fate: FateRules = field(default_factory=FateRules)
    folk_belief: FolkBeliefRules = field(default_factory=FolkBeliefRules)
    factions: FactionsRules = field(default_factory=FactionsRules)
    intrigue: IntrigueRules = field(default_factory=IntrigueRules)
    mercenaries: MercenariesRules = field(default_factory=MercenariesRules)
    banditry: BanditryRules = field(default_factory=BanditryRules)
    foreign_gods: ForeignGodsRules = field(default_factory=ForeignGodsRules)
    genesis: GenesisRules = field(default_factory=GenesisRules)
    goals: GoalsRules = field(default_factory=GoalsRules)
    achievements: AchievementRules = field(default_factory=AchievementRules)
    god_actions: GodActionsRules = field(default_factory=GodActionsRules)
    god_hand: GodHandRules = field(default_factory=GodHandRules)
    god_power: GodPowerRules = field(default_factory=GodPowerRules)
    guide: GuideRules = field(default_factory=GuideRules)
    heroes: HeroesRules = field(default_factory=HeroesRules)
    image_gen: ImageGenRules = field(default_factory=ImageGenRules)
    intervention_costs: InterventionCostsRules = field(default_factory=InterventionCostsRules)
    intervention_effects: InterventionEffectsRules = field(default_factory=InterventionEffectsRules)
    knowledge: KnowledgeRules = field(default_factory=KnowledgeRules)
    market: MarketRules = field(default_factory=MarketRules)
    mechanics: MechanicsRules = field(default_factory=MechanicsRules)
    language: LanguageRules = field(default_factory=LanguageRules)
    language_contact: LanguageContactRules = field(default_factory=LanguageContactRules)
    ledger: LedgerRules = field(default_factory=LedgerRules)
    limits: LimitsRules = field(default_factory=LimitsRules)
    link_graph: LinkGraphRules = field(default_factory=LinkGraphRules)
    metrics: MetricsRules = field(default_factory=MetricsRules)
    model: ModelRules = field(default_factory=ModelRules)
    mortal_agents: MortalAgentsRules = field(default_factory=MortalAgentsRules)
    mortal_tools: MortalToolsRules = field(default_factory=MortalToolsRules)
    naming: NamingRules = field(default_factory=NamingRules)
    native_faith: NativeFaithRules = field(default_factory=NativeFaithRules)
    narrative: NarrativeRules = field(default_factory=NarrativeRules)
    notifications: NotificationsRules = field(default_factory=NotificationsRules)
    opportunities: OpportunitiesRules = field(default_factory=OpportunitiesRules)
    pantheon: PantheonRules = field(default_factory=PantheonRules)
    places: PlacesRules = field(default_factory=PlacesRules)
    politics: PoliticsRules = field(default_factory=PoliticsRules)
    power_unlock_levels: PowerUnlockLevelsRules = field(default_factory=PowerUnlockLevelsRules)
    rarities: RaritiesRules = field(default_factory=RaritiesRules)
    rarity_gates: RarityGatesRules = field(default_factory=RarityGatesRules)
    record_schema: RecordSchemaRules = field(default_factory=RecordSchemaRules)
    religion: ReligionRules = field(default_factory=ReligionRules)
    reputation: ReputationRules = field(default_factory=ReputationRules)
    server: ServerRules = field(default_factory=ServerRules)
    setup_wizard: SetupWizardRules = field(default_factory=SetupWizardRules)
    sky: SkyRules = field(default_factory=SkyRules)
    star_types: StarTypeRules = field(default_factory=StarTypeRules)
    galaxies: GalaxyRules = field(default_factory=GalaxyRules)
    clusters: ClusterRules = field(default_factory=ClusterRules)
    dimensions: DimensionRules = field(default_factory=DimensionRules)
    rifts: RiftRules = field(default_factory=RiftRules)
    cosmic_beings: CosmicBeingRules = field(default_factory=CosmicBeingRules)
    stellar_evolution: StellarEvolutionRules = field(default_factory=StellarEvolutionRules)
    orbits: OrbitRules = field(default_factory=OrbitRules)
    planetary_climate: PlanetaryClimateRules = field(default_factory=PlanetaryClimateRules)
    impacts: ImpactRules = field(default_factory=ImpactRules)
    terraforming: TerraformingRules = field(default_factory=TerraformingRules)
    cosmic_features: CosmicFeatureRules = field(default_factory=CosmicFeatureRules)
    survey: SurveyRules = field(default_factory=SurveyRules)
    life_classes: LifeClassRules = field(default_factory=LifeClassRules)
    phenomena: PhenomenaRules = field(default_factory=PhenomenaRules)
    cosmography: CosmographyRules = field(default_factory=CosmographyRules)
    star_life: StarLifeRules = field(default_factory=StarLifeRules)
    world_life: WorldLifeRules = field(default_factory=WorldLifeRules)
    celestial_bodies: CelestialBodyRules = field(default_factory=CelestialBodyRules)
    journeys: JourneyRules = field(default_factory=JourneyRules)
    community_relations: CommunityRelationRules = field(default_factory=CommunityRelationRules)
    galaxy_types: GalaxyTypeRules = field(default_factory=GalaxyTypeRules)
    cluster_kinds: ClusterKindRules = field(default_factory=ClusterKindRules)
    dimension_kinds: DimensionKindRules = field(default_factory=DimensionKindRules)
    galactic_structures: GalacticStructureRules = field(default_factory=GalacticStructureRules)
    galactic_zones: GalacticZoneRules = field(default_factory=GalacticZoneRules)
    phenomenon_kinds: PhenomenonKindRules = field(default_factory=PhenomenonKindRules)
    being_kinds: BeingKindRules = field(default_factory=BeingKindRules)
    society: SocietyRules = field(default_factory=SocietyRules)
    son_relations: SonRelationsRules = field(default_factory=SonRelationsRules)
    son_tools: SonToolsRules = field(default_factory=SonToolsRules)
    summoning: SummoningRules = field(default_factory=SummoningRules)
    time: TimeRules = field(default_factory=TimeRules)
    trade: TradeRules = field(default_factory=TradeRules)
    travel: TravelRules = field(default_factory=TravelRules)
    travel_methods: TravelMethodsRules = field(default_factory=TravelMethodsRules)
    ui: UiRules = field(default_factory=UiRules)
    wonders: WondersRules = field(default_factory=WondersRules)
    world_birth: WorldBirthRules = field(default_factory=WorldBirthRules)
    world_effects: WorldEffectsRules = field(default_factory=WorldEffectsRules)
    world_engine: WorldEngineRules = field(default_factory=WorldEngineRules)
    world_epoch_transition: WorldEpochTransitionRules = field(default_factory=WorldEpochTransitionRules)
    world_hunt: WorldHuntRules = field(default_factory=WorldHuntRules)
    world_physics: WorldPhysicsRules = field(default_factory=WorldPhysicsRules)
    world_terrain: WorldTerrainRules = field(default_factory=WorldTerrainRules)
    world_war_strength: WorldWarStrengthRules = field(default_factory=WorldWarStrengthRules)
    consumption: ConsumptionRules = field(default_factory=ConsumptionRules)
    realm_loyalty: RealmLoyaltyRules = field(default_factory=RealmLoyaltyRules)
    construction: ConstructionRules = field(default_factory=ConstructionRules)
    structure_functions: StructureFunctionsRules = field(default_factory=StructureFunctionsRules)
    structure_effects: StructureEffectRules = field(default_factory=StructureEffectRules)
    upkeep: UpkeepRules = field(default_factory=UpkeepRules)
