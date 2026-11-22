import type { components } from '@/api/generated/schema'

export type ThingKind =
  | components['schemas']['EntityType']
  | 'creator'
  | 'son'
  | 'foreign_god'
  | 'world'
  | 'star'
  | 'galaxy'
  | 'cluster'
  | 'dimension'

type Homes = readonly ThingKind[] | 'every'

const GODS = ['creator', 'son', 'foreign_god'] as const
const MINDS = [
  'mortal',
  'spirit',
  'outer_being',
  'cosmic_being',
  ...GODS,
] as const
const BODIES = [
  'mortal',
  'beast',
  'species',
  'people',
  'son',
  'foreign_god',
] as const
const PEOPLES = ['people'] as const
const TOWNS = ['settlement'] as const
const REALMS = ['polity'] as const
const ORDERS = ['faction', 'cult', 'house', 'league', 'network'] as const
const COMMUNITIES = [...PEOPLES, ...TOWNS, ...REALMS, ...ORDERS] as const
const LANDS = ['region', 'place'] as const
const HEAVENS = [
  'world',
  'star',
  'celestial',
  'galaxy',
  'cluster',
  'dimension',
] as const
const LIFE = ['species', 'beast'] as const
const IDEAS = [
  'ideology',
  'theory',
  'rite',
  'knowledge',
  'art_form',
  'tradition',
  'legend',
  'law',
  'natural_law',
  'prophecy',
] as const
const MADE = [
  'item',
  'structure',
  'vessel',
  'artwork',
  'vehicle_type',
  'unit_type',
  'equipment_model',
  'dish',
  'building_type',
] as const
const MILITARY = ['army', 'polity', 'faction', 'league'] as const

export const SECTION_HOMES: Record<
  string,
  { homes: Homes; tables?: readonly string[] }
> = {
  EntityMechanics: { homes: 'every' },
  NameSection: { homes: 'every' },
  MindSplitSection: { homes: [...MINDS, ...PEOPLES] },
  MindSeatSection: { homes: MINDS },
  AugmentsSection: { homes: BODIES },
  NetworkSection: { homes: ['network', 'mortal', ...COMMUNITIES, ...GODS] },
  MadeWorldSection: { homes: ['mortal', ...COMMUNITIES, ...MADE, ...LANDS] },
  PowersSection: {
    homes: ['mortal', 'beast', 'spirit', ...PEOPLES, ...REALMS, ...GODS],
  },
  SourcesSection: { homes: [...LANDS, 'world', 'resource', ...GODS] },
  MagicSystemsSection: { homes: ['world', ...REALMS, ...PEOPLES, 'cult'] },
  HiddenTruthsSection: { homes: 'every' },
  LivingSection: { homes: [...LIFE, 'mortal', ...PEOPLES] },
  FortuneSection: { homes: ['mortal', ...COMMUNITIES, ...GODS] },
  TechnologySection: { homes: [...PEOPLES, ...TOWNS, ...REALMS, 'world'] },
  DivinePowersSection: { homes: GODS },
  CreatorBondsSection: {
    homes: [
      'mortal',
      ...PEOPLES,
      ...TOWNS,
      ...REALMS,
      'cult',
      'son',
      'foreign_god',
      'creator',
    ],
  },
  PantheonSection: { homes: ['world', ...GODS] },
  WaysOfLifeSection: { homes: [...PEOPLES, ...TOWNS, ...REALMS, 'mortal'] },
  TypedModelsSection: {
    homes: ['outer_being', 'mortal', 'dimension', ...TOWNS, ...LANDS, ...GODS],
  },
  SourceTrustSection: {
    homes: ['mortal', ...PEOPLES, ...TOWNS, ...REALMS, 'network'],
  },
  GodCouncilSection: { homes: GODS },
  FeelingsSection: { homes: ['mortal', ...GODS] },
  TastesSection: { homes: 'every' },
  EthicsSection: { homes: 'every' },
  AspirationsSection: { homes: ['mortal'] },
  BondsSection: { homes: 'every' },
  RenownSection: { homes: 'every' },
  WorksSection: { homes: [...TOWNS, ...PEOPLES, ...REALMS] },
  FinanceSection: { homes: ['mortal', ...COMMUNITIES] },
  LineageSection: { homes: ['mortal', 'house'] },
  HomeSection: { homes: ['mortal', 'house'] },
  IntrigueSection: { homes: ['mortal', ...REALMS, ...ORDERS, ...GODS] },
  CorrespondenceSection: { homes: ['mortal', ...REALMS, ...ORDERS, ...GODS] },
  TitlesSection: { homes: ['mortal', 'title', 'house', ...REALMS] },
  EstatesSection: { homes: ['mortal', 'house', ...REALMS, 'faction', 'cult'] },
  JusticeSection: { homes: ['mortal', ...REALMS, ...TOWNS, 'law'] },
  StatecraftSection: { homes: ['mortal', ...REALMS, ...TOWNS] },
  AffairsSection: { homes: ['mortal', ...REALMS] },
  GatheringsSection: { homes: ['mortal', ...COMMUNITIES, ...GODS] },
  HistoriesSection: { homes: 'every' },
  HistorySection: { homes: 'every' },
  DominionSection: {
    homes: [...LANDS, ...TOWNS, ...REALMS, ...PEOPLES, 'world', ...GODS],
  },
  ArcanaSection: {
    homes: ['mortal', 'cult', 'faction', 'item', 'rite', 'spirit', ...GODS],
  },
  MythicSection: { homes: ['mortal', 'legend', ...GODS] },
  TonguesSection: { homes: ['language', ...PEOPLES, ...REALMS, ...GODS] },
  EvolutionSection: {
    homes: [...LIFE, 'disease', ...LANDS, 'world', ...PEOPLES],
  },
  UrbanSection: { homes: [...TOWNS, 'faction', 'trade_route'] },
  LawDepthSection: { homes: [...REALMS, ...TOWNS, 'mortal', 'law'] },
  CollectiveSection: {
    homes: [...TOWNS, ...PEOPLES, ...REALMS, 'event', 'mortal'],
  },
  CyclesSection: {
    homes: [...REALMS, ...TOWNS, ...PEOPLES, 'mortal', ...GODS],
  },
  RegimeSection: { homes: [...REALMS, 'mortal', 'house'] },
  AgrarianSection: { homes: [...LANDS, ...TOWNS, ...PEOPLES] },
  OperationsSection: { homes: [...MILITARY, 'vessel'] },
  SacredSection: {
    homes: [
      'cult',
      'spirit',
      ...LANDS,
      ...TOWNS,
      ...PEOPLES,
      'mortal',
      ...GODS,
    ],
  },
  PursuitsSection: {
    homes: ['artwork', 'art_form', 'mortal', ...TOWNS, ...PEOPLES, 'faction'],
  },
  TalesSection: { homes: ['mortal', 'world', ...PEOPLES, 'legend'] },
  FolkwaysSection: { homes: [...TOWNS, ...PEOPLES, ...LIFE, 'mortal'] },
  CustomsSection: { homes: [...PEOPLES, ...TOWNS, 'mortal'] },
  DailyLifeSection: {
    homes: [...PEOPLES, 'mortal', 'house'],
    tables: [
      'care_customs',
      'housework',
      'domestic_service',
      'leisure_pursuits',
      'space_norms',
    ],
  },
  KinSection: {
    homes: [...PEOPLES, 'mortal'],
    tables: ['kin_role_duties', 'kin_groups', 'kin_group_members'],
  },
  ChildhoodSection: {
    homes: [...PEOPLES, 'mortal', 'tradition'],
    tables: ['infant_care', 'child_standing', 'socialization', 'pedagogy'],
  },
  UnionsSection: {
    homes: [...PEOPLES, 'mortal'],
    tables: [
      'intimacy_norms',
      'restraint_customs',
      'reproductive_courses',
      'legitimacy_rules',
      'child_recognitions',
    ],
  },
  YouthSection: {
    homes: [...PEOPLES, ...TOWNS, 'mortal'],
    tables: ['youth_standing', 'youth_groups', 'youth_group_members'],
  },
  NumbersSection: {
    homes: [...REALMS, ...PEOPLES, 'cult', 'faction', ...TOWNS],
    tables: ['population_policies', 'population_instruments'],
  },
  CommerceSection: {
    homes: [...TOWNS],
    tables: ['shops', 'shop_goods', 'supply_tiers', 'promotions', 'leases'],
  },
  PublicWorksSection: {
    homes: [...REALMS, ...TOWNS, 'trade_route', 'region'],
    tables: ['public_works', 'public_work_stages', 'state_enterprises'],
  },
  MediaSection: {
    homes: [...PEOPLES, ...REALMS, ...TOWNS],
    tables: ['record_media', 'media_outlets', 'media_items'],
  },
  GovernanceSection: {
    homes: ['faction', 'cult', 'house', 'league'],
    tables: [
      'org_governance',
      'org_seats',
      'org_cliques',
      'org_mergers',
      'org_research',
      'insolvency_cases',
    ],
  },
  MarketStructureSection: {
    homes: [...TOWNS],
    tables: ['market_structures', 'cartels', 'price_wars'],
  },
  LabourSection: {
    homes: [...TOWNS],
    tables: ['worker_bodies', 'labour_contracts', 'labour_disputes'],
  },
  MoneyPolicySection: { homes: [...REALMS], tables: ['monetary_authorities'] },
  SecuritiesSection: {
    homes: [...TOWNS, 'faction'],
    tables: [
      'stock_exchanges',
      'issued_securities',
      'security_holdings',
      'security_prices',
    ],
  },
  LeaguesSection: {
    homes: ['league'],
    tables: ['polity_leagues', 'league_members', 'league_decisions'],
  },
  DeparturesSection: { homes: [], tables: ['departures'] },
  ReferendumsSection: { homes: [], tables: ['referendums'] },
  ReckoningSection: {
    homes: [],
    tables: ['reckonings', 'reckoning_measures', 'reckoning_cases'],
  },
  LeaderCultsSection: { homes: [], tables: ['leader_cults'] },
  RestorationsSection: { homes: [], tables: ['restorations'] },
  OccupationSection: {
    homes: [],
    tables: ['occupation_regimes', 'collaborations', 'occupation_measures'],
  },
  ArsenalSection: {
    homes: [],
    tables: ['mass_weapons', 'deterrence_postures', 'war_remnants'],
  },
  InterworldSection: {
    homes: [],
    tables: [
      'interworld_campaigns',
      'orbital_control',
      'interworld_migrations',
    ],
  },
  CityRulesSection: {
    homes: [...TOWNS],
    tables: ['land_use_rules', 'municipal_services', 'conurbations'],
  },
  ProtectedNatureSection: {
    homes: [],
    tables: [
      'protected_areas',
      'species_protections',
      'conservation_movements',
    ],
  },
  FamilySection: {
    homes: ['house'],
    tables: [
      'kin_dynamics',
      'kin_favours',
      'kin_rivalries',
      'kin_disownings',
      'kin_blends',
      'elder_sway',
    ],
  },
  MoodSection: { homes: [...TOWNS], tables: ['feeling_spread'] },
  InterpretationSection: { homes: [], tables: ['interpretations'] },
  GraveGoodsSection: { homes: [], tables: ['grave_goods'] },
  ConditionKindsSection: { homes: ['world'], tables: ['agentless_conditions'] },
  FertilitySection: {
    homes: [...PEOPLES],
    tables: ['fertility_means', 'fertility_uses'],
  },
  PersonHonoursSection: {
    homes: [...REALMS, 'cult', 'faction', 'son', 'foreign_god'],
    tables: ['honour_kinds', 'honours_held'],
  },
  SeaWavesSection: {
    homes: ['world'],
    tables: ['sea_waves', 'sea_wave_coasts', 'wave_warnings'],
  },
  CreatureGroupsSection: { homes: [...LIFE], tables: ['creature_groups'] },
  DivineConceptionsSection: {
    homes: ['cult', ...GODS],
    tables: ['divine_conceptions', 'god_readings'],
  },
  SpeechSection: { homes: [...PEOPLES], tables: ['humour_styles', 'speeches'] },
  FolkKnowledgeSection: {
    homes: [...PEOPLES],
    tables: ['folk_knowledge', 'folk_classes'],
  },
  EndowmentsSection: { homes: [], tables: ['endowments'] },
  TheDeadSection: { homes: [...PEOPLES], tables: ['death_work'] },
  PracticesSection: {
    homes: [...PEOPLES, ...TOWNS],
    tables: ['facet_practices'],
  },
  ProfessionsSection: {
    homes: [...MINDS, ...PEOPLES, 'cult'],
    tables: ['professions_of_value'],
  },
  ForecastingSection: {
    homes: [...PEOPLES, ...LANDS],
    tables: ['observation_methods', 'weather_works'],
  },
  PlantBodiesSection: {
    homes: ['species'],
    tables: ['plant_anatomy', 'plant_parts'],
  },
  BodySystemsSection: {
    homes: [...PEOPLES, ...LIFE, 'mortal'],
    tables: ['body_systems', 'sensitivities'],
  },
  DiseaseAgentsSection: { homes: ['disease'], tables: ['disease_agents'] },
  WaterIceSection: {
    homes: [...LANDS, ...TOWNS],
    tables: ['region_cryosphere', 'sediment_flows', 'coasts', 'local_climates'],
  },
  SpaceWeatherSection: {
    homes: ['world', 'star'],
    tables: ['world_fields', 'star_activity', 'space_weather_events'],
  },
  CraftsSection: { homes: [...LANDS, ...TOWNS, ...PEOPLES, 'mortal', 'item'] },
  ClimesSection: { homes: [...LANDS, 'world', 'trade_route'] },
  BelongingSection: { homes: [...TOWNS, ...PEOPLES, 'mortal', ...REALMS] },
  TechErasSection: { homes: [...TOWNS, ...PEOPLES, ...REALMS] },
  NatureSection: { homes: [...LIFE, ...LANDS, ...PEOPLES] },
  MeansSection: { homes: [...TOWNS, ...PEOPLES, 'vessel', 'structure'] },
  OrdersSection: { homes: [...REALMS, ...TOWNS, ...PEOPLES] },
  HonoursSection: { homes: ['army', ...REALMS] },
  WorldViewSection: { homes: ['world', ...LANDS, ...TOWNS] },
  BiologySection: { homes: [...PEOPLES, ...LIFE, 'mortal'] },
  LifecycleSection: {
    homes: ['ideology', 'theory', 'rite', 'disease', 'outer_being'],
  },
  WorldEndSection: { homes: ['world'] },
  PrehistorySection: { homes: ['world'] },
  TransformSection: { homes: [...HEAVENS, ...GODS, ...LANDS] },
  CouplingsSection: { homes: [...IDEAS, 'mortal', ...COMMUNITIES, ...GODS] },
  FossilSection: { homes: [...LANDS, 'world'] },
  GroundsSection: { homes: [...TOWNS, ...REALMS, 'cult', 'house'] },
  MadeKindsSection: { homes: [...MADE, ...MILITARY, ...TOWNS, ...PEOPLES] },
  RecordRowsSection: { homes: 'every' },
}

export function shows(
  section: string,
  kind: ThingKind,
  held: ReadonlySet<string>
) {
  const spec = SECTION_HOMES[section]
  if (!spec) return true
  if (spec.homes === 'every' || spec.homes.includes(kind)) return true
  return (spec.tables ?? []).some((table) => held.has(table))
}
