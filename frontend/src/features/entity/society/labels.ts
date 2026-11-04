import {
  Anchor,
  Axe,
  Baby,
  Ban,
  BookOpen,
  Brain,
  BrickWall,
  Bug,
  Building,
  Castle,
  Church,
  CircleCheck,
  CloudRain,
  Coins,
  Container,
  Crosshair,
  Crown,
  Disc3,
  Dna,
  Droplet,
  Droplets,
  Eye,
  Feather,
  Fingerprint,
  Fish,
  Flame,
  Flower2,
  Footprints,
  Gem,
  Ghost,
  Gift,
  Globe,
  Hammer,
  Hand,
  HandCoins,
  HandHeart,
  Heart,
  HeartHandshake,
  HeartPulse,
  Hexagon,
  House,
  Landmark,
  Leaf,
  Link,
  Lock,
  Mars,
  Medal,
  Milestone,
  Minus,
  Moon,
  Mountain,
  Orbit,
  PartyPopper,
  PawPrint,
  Pickaxe,
  Route,
  Sailboat,
  ScrollText,
  Shield,
  ShieldHalf,
  Skull,
  Snowflake,
  Sparkles,
  Split,
  Sprout,
  Store,
  Sun,
  Sunset,
  Swords,
  Tent,
  Thermometer,
  TreePine,
  TrendingDown,
  TrendingUp,
  Trophy,
  User,
  UserRound,
  Users,
  UsersRound,
  Venus,
  Vote,
  WandSparkles,
  Wheat,
  Wind,
  Zap,
  type LucideIcon,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type KpiTone } from '@/components/domain'

type Schemas = components['schemas']
export type SocialClass = Schemas['SocialClass']
export type Job = Schemas['Job']
export type AgeBand = Schemas['AgeBand']
export type Sex = Schemas['Sex']
export type CohortCondition = Schemas['CohortCondition']
export type DistrictKind = Schemas['DistrictKind']
export type DiseaseVector = Schemas['DiseaseVector']
export type DiseaseTarget = Schemas['DiseaseTarget']
export type ClimateAffinity = Schemas['ClimateAffinity']
export type SpreadPath = Schemas['SpreadPath']
export type OutbreakStatus = Schemas['OutbreakStatus']
export type CureSource = Schemas['CureSource']
export type SizeTier = Schemas['SizeTier']
export type WaterSupply = Schemas['WaterSupply']
export type BuildMaterial = Schemas['BuildMaterial']
export type TreasuryEntry = Schemas['TreasuryEntry']
export type Aesthetic = Schemas['Aesthetic']
export type MartialStyle = Schemas['MartialStyle']
export type MarriageCustom = Schemas['MarriageCustom']
export type InheritanceCustom = Schemas['InheritanceCustom']

export type Spec = {
  label: string
  icon: LucideIcon
  tone?: KpiTone
  hint?: string
}

export const CLASS_SPEC: Record<SocialClass, Spec> = {
  farmer: { label: 'Farmers', icon: Wheat, tone: 'success' },
  artisan: { label: 'Artisans', icon: Hammer, tone: 'gold' },
  merchant: { label: 'Merchants', icon: Coins, tone: 'gold' },
  priest: { label: 'Priests', icon: Church, tone: 'verdigris' },
  warrior: { label: 'Warriors', icon: Swords, tone: 'danger' },
  scribe: { label: 'Scribes', icon: BookOpen, tone: 'info' },
  noble: { label: 'Nobles', icon: Crown, tone: 'gold' },
  serf_or_slave: { label: 'Serfs and slaves', icon: Link, tone: 'warning' },
  outcast: { label: 'Outcasts', icon: Tent, tone: 'muted' },
  monastic: { label: 'Monastics', icon: ScrollText, tone: 'verdigris' },
}
export const CLASS_ORDER = Object.keys(CLASS_SPEC) as SocialClass[]

export const JOB_SPEC: Record<Job, Spec> = {
  farming: { label: 'Farming', icon: Wheat },
  herding: { label: 'Herding', icon: Sprout },
  fishing: { label: 'Fishing', icon: Fish },
  mining: { label: 'Mining', icon: Pickaxe },
  crafting: { label: 'Crafting', icon: Hammer },
  trade: { label: 'Trade', icon: Store },
  soldiering: { label: 'Soldiering', icon: Shield },
  clergy: { label: 'Clergy', icon: Church },
  scholarship: { label: 'Scholarship', icon: BookOpen },
  building: { label: 'Building', icon: TreePine },
  idle: { label: 'No work', icon: User },
}
export const JOB_ORDER = Object.keys(JOB_SPEC) as Job[]

export const AGE_SPEC: Record<AgeBand, Spec> = {
  child: { label: 'Children', icon: Baby, tone: 'success' },
  adult: { label: 'Adults', icon: UserRound, tone: 'gold' },
  elder: { label: 'Elders', icon: Users, tone: 'verdigris' },
}
export const AGE_ORDER: AgeBand[] = ['elder', 'adult', 'child']

export const SEX_SPEC: Record<Sex, Spec> = {
  male: { label: 'Men', icon: Mars, tone: 'info' },
  female: { label: 'Women', icon: Venus, tone: 'verdigris' },
}

export const CONDITION_SPEC: Record<CohortCondition, Spec> = {
  none: { label: 'Free and well', icon: User, tone: 'muted' },
  veteran: {
    label: 'Veterans',
    icon: Medal,
    tone: 'gold',
    hint: 'Survivors of war; they steady a levy',
  },
  sick: {
    label: 'Sick',
    icon: Thermometer,
    tone: 'danger',
    hint: 'Laid low by disease; they work and fight less',
  },
  enslaved: {
    label: 'Enslaved',
    icon: Link,
    tone: 'warning',
    hint: 'Held in bondage; they work without will',
  },
  captive: {
    label: 'Captives',
    icon: Lock,
    tone: 'warning',
    hint: 'Taken in war and not yet ransomed or freed',
  },
}

export const PRESSURE_HINT: Record<string, string> = {
  hunger: 'Granaries and harvests fall short of mouths',
  insecurity: 'Raids, wars and lawlessness press on them',
  overcrowding: 'More people than the land and houses hold',
  poverty: 'Coin and goods are scarce for the many',
  impiety: 'Their gods and rites go unhonoured',
  humiliation: 'Defeat, subjugation or shame weighs on them',
  stagnation: 'Nothing grows, nothing changes',
}

export const DISTRICT_SPEC: Record<DistrictKind, Spec> = {
  farmland: { label: 'Farmland', icon: Wheat, tone: 'success' },
  market: { label: 'Market', icon: Store, tone: 'gold' },
  craft_quarter: { label: 'Craft quarter', icon: Hammer, tone: 'gold' },
  temple_quarter: { label: 'Temple quarter', icon: Church, tone: 'verdigris' },
  harbour: { label: 'Harbour', icon: Anchor, tone: 'info' },
  citadel: { label: 'Citadel', icon: Castle, tone: 'danger' },
  slums: { label: 'Slums', icon: Tent, tone: 'warning' },
  palace: { label: 'Palace', icon: Crown, tone: 'gold' },
  foreign_quarter: { label: 'Foreign quarter', icon: Globe, tone: 'info' },
  necropolis: { label: 'Necropolis', icon: Skull, tone: 'muted' },
}
export const DISTRICT_ORDER = Object.keys(DISTRICT_SPEC) as DistrictKind[]
export const DISTRICT_MAX_LEVEL = 5

export const SIZE_SPEC: Record<SizeTier, Spec & { rank: number }> = {
  hamlet: { label: 'Hamlet', icon: Tent, tone: 'muted', rank: 1 },
  village: { label: 'Village', icon: House, tone: 'success', rank: 2 },
  town: { label: 'Town', icon: Building, tone: 'info', rank: 3 },
  city: { label: 'City', icon: Castle, tone: 'gold', rank: 4 },
  metropolis: { label: 'Metropolis', icon: Landmark, tone: 'gold', rank: 5 },
}
export const SIZE_ORDER = Object.keys(SIZE_SPEC) as SizeTier[]

export const WATER_SPEC: Record<WaterSupply, Spec> = {
  none: { label: 'No waterworks', icon: Ban, tone: 'muted' },
  well: { label: 'Wells', icon: Droplet, tone: 'info' },
  cistern: { label: 'Cisterns', icon: Container, tone: 'info' },
  aqueduct: { label: 'Aqueduct', icon: Droplets, tone: 'verdigris' },
}

export const MATERIAL_SPEC: Record<BuildMaterial, Spec> = {
  timber: { label: 'Timber', icon: TreePine, tone: 'warning' },
  stone: { label: 'Stone', icon: BrickWall, tone: 'info' },
}

export const TREASURY_SPEC: Record<TreasuryEntry, Spec> = {
  tax: { label: 'Taxes', icon: Coins, tone: 'success' },
  tolls: { label: 'Tolls', icon: Milestone, tone: 'success' },
  investment: { label: 'Investment', icon: TrendingUp, tone: 'info' },
  garrison: { label: 'Garrison and militia', icon: Shield, tone: 'danger' },
  walls: { label: 'Walls', icon: BrickWall, tone: 'warning' },
  building: { label: 'Building', icon: Hammer, tone: 'gold' },
  festival: { label: 'Festival', icon: PartyPopper, tone: 'verdigris' },
  alms: { label: 'Alms', icon: HandHeart, tone: 'verdigris' },
  fire: { label: 'Fire', icon: Flame, tone: 'danger' },
  plunder: { label: 'Plunder', icon: Swords, tone: 'danger' },
  grant: { label: 'Grant', icon: Gift, tone: 'gold' },
  upkeep: { label: 'Upkeep of works', icon: Building, tone: 'warning' },
}

export const AESTHETIC_SPEC: Record<Aesthetic, Spec> = {
  austere: { label: 'Austere', icon: Minus, tone: 'muted' },
  ornate: { label: 'Ornate', icon: Gem, tone: 'gold' },
  geometric: { label: 'Geometric', icon: Hexagon, tone: 'info' },
  natural: { label: 'Natural', icon: Leaf, tone: 'success' },
  macabre: { label: 'Macabre', icon: Skull, tone: 'danger' },
  celestial: { label: 'Celestial', icon: Moon, tone: 'verdigris' },
}

export const MARTIAL_SPEC: Record<MartialStyle, Spec> = {
  shieldwall: { label: 'Shield wall', icon: Shield, tone: 'info' },
  horse_archer: { label: 'Horse archers', icon: Crosshair, tone: 'gold' },
  skirmisher: { label: 'Skirmishers', icon: Feather, tone: 'success' },
  chariot: { label: 'Chariots', icon: Disc3, tone: 'gold' },
  phalanx: { label: 'Phalanx', icon: ShieldHalf, tone: 'info' },
  berserker: { label: 'Berserkers', icon: Axe, tone: 'danger' },
  naval_raider: { label: 'Sea raiders', icon: Sailboat, tone: 'info' },
  siege_engineer: { label: 'Siege engineers', icon: Castle, tone: 'warning' },
  war_magic: { label: 'War magic', icon: WandSparkles, tone: 'verdigris' },
  beast_war: { label: 'War beasts', icon: PawPrint, tone: 'warning' },
}

export const MARRIAGE_SPEC: Record<MarriageCustom, Spec> = {
  monogamy: { label: 'One spouse', icon: Heart, tone: 'danger' },
  polygyny: { label: 'Many wives', icon: Users, tone: 'gold' },
  polyandry: { label: 'Many husbands', icon: UsersRound, tone: 'gold' },
  group: { label: 'Group marriage', icon: HeartHandshake, tone: 'verdigris' },
}

export const INHERITANCE_SPEC: Record<InheritanceCustom, Spec> = {
  primogeniture: { label: 'Eldest child', icon: Crown, tone: 'gold' },
  ultimogeniture: { label: 'Youngest child', icon: Baby, tone: 'success' },
  gavelkind: { label: 'Split among heirs', icon: Split, tone: 'info' },
  matrilineal: {
    label: 'Through the mother',
    icon: Flower2,
    tone: 'verdigris',
  },
  elective: { label: 'Chosen by vote', icon: Vote, tone: 'info' },
  by_merit: { label: 'The worthiest', icon: Trophy, tone: 'gold' },
}

export const VECTOR_SPEC: Record<DiseaseVector, Spec> = {
  air: { label: 'Breath and air', icon: Wind, tone: 'info' },
  water: { label: 'Water', icon: Droplets, tone: 'info' },
  touch: { label: 'Touch', icon: Hand, tone: 'warning' },
  bite: { label: 'Bites of beasts', icon: Bug, tone: 'warning' },
  spirit: { label: 'Spirits', icon: Ghost, tone: 'verdigris' },
  void: { label: 'The void', icon: Orbit, tone: 'danger' },
  curse: { label: 'A curse', icon: Sparkles, tone: 'danger' },
}

export const AFFINITY_SPEC: Record<ClimateAffinity, Spec> = {
  warm: { label: 'Warm lands', icon: Sun, tone: 'gold' },
  wet: { label: 'Wet lands', icon: CloudRain, tone: 'info' },
  cold: { label: 'Cold lands', icon: Snowflake, tone: 'info' },
  dry: { label: 'Dry lands', icon: Sunset, tone: 'warning' },
  any: { label: 'Any land', icon: Globe, tone: 'muted' },
}

export const TARGET_SPEC: Record<DiseaseTarget, Spec> = {
  breath: { label: 'Breath', icon: Wind, tone: 'info' },
  vital: { label: 'Vital organs', icon: HeartPulse, tone: 'danger' },
  cognition: { label: 'Mind', icon: Brain, tone: 'verdigris' },
  sight: { label: 'Sight', icon: Eye, tone: 'warning' },
  skin: { label: 'Skin', icon: Fingerprint, tone: 'warning' },
}

export const PATH_SPEC: Record<SpreadPath, Spec> = {
  origin: { label: 'Rose here', icon: Sprout, tone: 'danger' },
  route: { label: 'Came by trade road', icon: Route, tone: 'warning' },
  army: { label: 'Marched in with an army', icon: Swords, tone: 'danger' },
  journey: {
    label: 'Carried by travellers',
    icon: Footprints,
    tone: 'warning',
  },
  siege: { label: 'Bred in a siege', icon: Castle, tone: 'danger' },
  loosed: { label: 'Loosed by a god', icon: Zap, tone: 'gold' },
  mutation: { label: 'A new strain', icon: Dna, tone: 'verdigris' },
}

export const STATUS_SPEC: Record<OutbreakStatus, Spec> = {
  active: { label: 'Raging', icon: Flame, tone: 'danger' },
  waning: { label: 'Waning', icon: TrendingDown, tone: 'warning' },
  ended: { label: 'Over', icon: CircleCheck, tone: 'success' },
}

export const CURE_SPEC: Record<CureSource, Spec> = {
  knowledge: { label: 'Learned by healers', icon: BookOpen, tone: 'success' },
  granted: { label: 'Granted by a god', icon: Sparkles, tone: 'gold' },
}

export const FIELD_LABEL: Record<string, string> = {
  maturity_years: 'Coming of age',
  adult_years: 'Years of adulthood',
  elder_years: 'Years of old age',
  fertility_pct: 'Fertility',
  cohesion: 'Cohesion',
  literacy: 'Literacy',
  urbanisation: 'Urbanisation',
  aesthetic: 'Art',
  martial_style: 'Way of war',
  marriage: 'Marriage',
  inheritance: 'Inheritance',
  endogamous: 'Marrying within',
  slavery_lawful: 'Slavery',
  public_order: 'Order',
  crime: 'Crime',
  unrest: 'Unrest',
  sanitation: 'Sanitation',
  fire_risk: 'Fire risk',
  prestige: 'Prestige',
  treasury: 'Treasury',
  tax_rate: 'Tax',
  militia: 'Militia',
  investment_pool: 'Investment pool',
  siege_supplies: 'Siege food',
  siege_water: 'Siege water',
  siege_disease: 'Camp sickness',
  walls_level: 'Wall height',
  walls_condition: 'Wall repair',
  walls_material: 'Wall stone',
  gates: 'Gates',
  towers: 'Towers',
  roads: 'Roads',
  granary_capacity: 'Granaries',
  warehouse_capacity: 'Warehouses',
  harbour_capacity: 'Harbour',
  size_tier: 'Size',
  water: 'Water',
  sewers: 'Sewers',
  rationing: 'Rationing',
  free_city: 'Free city',
  virulence: 'Virulence',
  lethality: 'Lethality',
  chronic_rate: 'Lasting illness',
  incubation: 'Incubation',
  immunity_epochs: 'Immunity',
  mutation_rate: 'Mutation',
  stigma: 'Stigma',
  cure_level: 'Medicine to cure',
  vector: 'Spread',
  climate_affinity: 'Climate',
}

export const TREASURY_ICON: LucideIcon = HandCoins
export const SETTLEMENT_ICON: LucideIcon = Landmark
export const FIRE_ICON: LucideIcon = Flame
export const GEM_ICON: LucideIcon = Gem
export const MOUNTAIN_ICON: LucideIcon = Mountain

export function fieldLabel(key: string): string {
  return (
    FIELD_LABEL[key] ?? words(key).replace(/^./, (first) => first.toUpperCase())
  )
}

export function words(value: string): string {
  return value.replaceAll('_', ' ')
}

export function choices(values: readonly string[]): Record<string, string> {
  return Object.fromEntries(values.map((value) => [value, words(value)]))
}
