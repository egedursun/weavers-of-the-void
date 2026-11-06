from dataclasses import dataclass, field

from aerona.rules.registry.agents import AgentsRules
from aerona.rules.registry.apocalypse import ApocalypseRules
from aerona.rules.registry.archive import ArchiveRules
from aerona.rules.registry.ascension import AscensionRules
from aerona.rules.registry.awakening import AwakeningRules
from aerona.rules.registry.backup import BackupRules
from aerona.rules.registry.balance import BalanceRules
from aerona.rules.registry.batch import BatchRules
from aerona.rules.registry.battle_tables import BattleTerrainRules, BattleWeatherRules, TacticMatchupRules
from aerona.rules.registry.beyond import BeyondRules
from aerona.rules.registry.body import (
    AnatomyRules,
    ArmourRules,
    BodyCustomsRules,
    CapacityRules,
    ConditionRules,
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
from aerona.rules.registry.civilization import CivilizationRules
from aerona.rules.registry.climate_effects import ClimateEffectsRules
from aerona.rules.registry.climate_world_type import ClimateWorldTypeRules
from aerona.rules.registry.content import ContentRules
from aerona.rules.registry.context import ContextRules
from aerona.rules.registry.core_rules import CoreRulesRules
from aerona.rules.registry.cosmic_costs import CosmicCostsRules
from aerona.rules.registry.cosmic_horror import CosmicHorrorRules
from aerona.rules.registry.costs import CostsRules
from aerona.rules.registry.council import CouncilRules
from aerona.rules.registry.creation_base_cost import CreationBaseCostRules
from aerona.rules.registry.creator import CreatorRules
from aerona.rules.registry.creature_traits import CreatureTraitsRules
from aerona.rules.registry.creatures import CreaturesRules
from aerona.rules.registry.culture import CultureRules
from aerona.rules.registry.death import DeathRules
from aerona.rules.registry.deep_life import DeepLifeRules
from aerona.rules.registry.deep_world import DeepWorldRules
from aerona.rules.registry.demography import CohortsRules, DemographyRules, LabourRules, MobilityRules, PeopleRules
from aerona.rules.registry.diplomacy import DiplomacyRules
from aerona.rules.registry.disasters import DisastersRules
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
from aerona.rules.registry.ecology import EcologyRules
from aerona.rules.registry.economy import EconomyRules
from aerona.rules.registry.effect_packages import EffectPackageRules
from aerona.rules.registry.empty_world import EmptyWorldRules
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
from aerona.rules.registry.espionage import EspionageRules
from aerona.rules.registry.essence import EssenceRules
from aerona.rules.registry.events import EventsRules
from aerona.rules.registry.exploration import ExplorationRules
from aerona.rules.registry.factions import BanditryRules, FactionsRules, IntrigueRules, MercenariesRules
from aerona.rules.registry.faith import FaithRules
from aerona.rules.registry.fate import FateRules
from aerona.rules.registry.folk import BiologyRules, CustomsRules
from aerona.rules.registry.folk_belief import FolkBeliefRules
from aerona.rules.registry.foreign_gods import ForeignGodsRules
from aerona.rules.registry.genesis import GenesisRules
from aerona.rules.registry.geography import GeographyRules
from aerona.rules.registry.geomorphology import GeomorphologyRules
from aerona.rules.registry.goals import GoalsRules
from aerona.rules.registry.god_actions import GodActionsRules
from aerona.rules.registry.god_hand import GodHandRules
from aerona.rules.registry.god_power import GodPowerRules
from aerona.rules.registry.guide import GuideRules
from aerona.rules.registry.harshness import HarshnessRules
from aerona.rules.registry.heroes import HeroesRules
from aerona.rules.registry.image_gen import ImageGenRules
from aerona.rules.registry.incitement import IncitementRules
from aerona.rules.registry.intervention_costs import InterventionCostsRules
from aerona.rules.registry.intervention_effects import InterventionEffectsRules
from aerona.rules.registry.items import EnchantmentsRules, ItemPowersRules
from aerona.rules.registry.knowledge import KnowledgeRules
from aerona.rules.registry.language import LanguageRules
from aerona.rules.registry.language_contact import LanguageContactRules
from aerona.rules.registry.ledger import LedgerRules
from aerona.rules.registry.life_cycles import LifeCyclesRules
from aerona.rules.registry.limits import LimitsRules
from aerona.rules.registry.link_graph import LinkGraphRules
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
from aerona.rules.registry.market import MarketRules
from aerona.rules.registry.markets import BankingRules, MarketsRules, MoneyRules, TollsRules, TradeRoutesRules
from aerona.rules.registry.materials import MaterialsRules
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
from aerona.rules.registry.model import ModelRules
from aerona.rules.registry.modifiers import IncidentRules, ModifiersRules
from aerona.rules.registry.mortal_acts import ActsRules, EthnicRules, LoyaltyRules
from aerona.rules.registry.mortal_agents import MortalAgentsRules
from aerona.rules.registry.mortal_life import AgingRules, EducationRules, FertilityRules, KinshipRules
from aerona.rules.registry.mortal_standing import EquipmentRules, PunishmentRules, StandingRules
from aerona.rules.registry.mortal_tools import MortalToolsRules
from aerona.rules.registry.naming import NamingRules
from aerona.rules.registry.narrative import NarrativeRules
from aerona.rules.registry.native_faith import NativeFaithRules
from aerona.rules.registry.notifications import NotificationsRules
from aerona.rules.registry.opportunities import OpportunitiesRules
from aerona.rules.registry.pantheon import PantheonRules
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
from aerona.rules.registry.production import ExtractionRules, MiningHazardsRules, RefiningRules
from aerona.rules.registry.rarities import RaritiesRules
from aerona.rules.registry.rarity_gates import RarityGatesRules
from aerona.rules.registry.record_schema import RecordSchemaRules
from aerona.rules.registry.region import HazardsRules, RegionalDangerRules, TerrainRules
from aerona.rules.registry.religion import ReligionRules
from aerona.rules.registry.remembrance import RemembranceRules
from aerona.rules.registry.reputation import ReputationRules
from aerona.rules.registry.routes import ChokepointsRules, RouteDangersRules, RouteSeasonsRules, SentientPactsRules, SonRoutesRules
from aerona.rules.registry.rumours import RumoursRules
from aerona.rules.registry.seasonal import SeasonalRules
from aerona.rules.registry.server import ServerRules
from aerona.rules.registry.settlement import CrimeRules, DistrictRules, FireRules, SanitationRules, TaxationRules, UrbanRules
from aerona.rules.registry.setup_wizard import SetupWizardRules
from aerona.rules.registry.sky import SkyRules
from aerona.rules.registry.society import SocietyRules
from aerona.rules.registry.society_depth import ConsumptionRules, RealmLoyaltyRules
from aerona.rules.registry.son_relations import SonRelationsRules
from aerona.rules.registry.son_tools import SonToolsRules
from aerona.rules.registry.star_types import StarTypeRules
from aerona.rules.registry.stress import StressRules
from aerona.rules.registry.strike import StrikeRules
from aerona.rules.registry.structures import ConstructionRules, StructureFunctionsRules, UpkeepRules
from aerona.rules.registry.summoning import SummoningRules
from aerona.rules.registry.time import TimeRules
from aerona.rules.registry.tissues import TissueRules
from aerona.rules.registry.trade import TradeRules
from aerona.rules.registry.travel import TravelRules
from aerona.rules.registry.travel_methods import TravelMethodsRules
from aerona.rules.registry.ui import UiRules
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
from aerona.rules.registry.world_engine import WorldEngineRules
from aerona.rules.registry.world_epoch_transition import WorldEpochTransitionRules
from aerona.rules.registry.world_hunt import WorldHuntRules
from aerona.rules.registry.world_physics import WorldPhysicsRules
from aerona.rules.registry.world_terrain import WorldTerrainRules
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
    thoughts: ThoughtsRules = field(default_factory=ThoughtsRules)
    grief: GriefRules = field(default_factory=GriefRules)
    dreams: DreamRules = field(default_factory=DreamRules)
    preferences: PreferencesRules = field(default_factory=PreferencesRules)
    ethics: EthicsRules = field(default_factory=EthicsRules)
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
    upkeep: UpkeepRules = field(default_factory=UpkeepRules)
