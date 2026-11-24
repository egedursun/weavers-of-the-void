import {
  Activity,
  AlertTriangle,
  Archive,
  ArrowDownUp,
  Baby,
  Ban,
  Bird,
  Blend,
  BookHeart,
  Bug,
  Building,
  CloudLightning,
  Coins,
  Crown,
  DoorOpen,
  Eye,
  Flame,
  Flower2,
  Footprints,
  Gift,
  GitBranch,
  GitFork,
  GitMerge,
  Hand,
  Hammer,
  HandHeart,
  Handshake,
  HardHat,
  Heart,
  HeartHandshake,
  Home,
  Hourglass,
  KeyRound,
  Landmark,
  Languages,
  Lightbulb,
  Link,
  Mountain,
  Network,
  Orbit,
  PackageOpen,
  Palette,
  Recycle,
  Repeat,
  Route,
  Scale,
  ScrollText,
  Shield,
  ShieldAlert,
  Shuffle,
  Snowflake,
  Sparkles,
  Split,
  Sprout,
  Swords,
  Tent,
  TrendingDown,
  TrendingUp,
  type LucideIcon,
  Undo2,
  Users,
  Wallet,
  Wheat,
  Wind,
  Wrench,
  Gavel,
  MountainSnow,
  UserRound,
  UsersRound,
  Minus,
  Pyramid,
  Group,
  LineStyle,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'

type Schema = components['schemas']

export const CYCLES_ICON: LucideIcon = Orbit

export const PHASES: Record<Schema['CyclePhase'], Named> = {
  growth: { label: 'Growth', icon: Sprout, tone: 'success' },
  stagflation: { label: 'Stagflation', icon: Hourglass, tone: 'warning' },
  crisis: { label: 'Crisis', icon: Flame, tone: 'danger' },
  depression: { label: 'Depression', icon: TrendingDown, tone: 'muted' },
}

export const COMPONENTS: Record<Schema['StressComponent'], Named> = {
  population_pressure: {
    label: 'Population pressure',
    icon: Users,
    tone: 'info',
  },
  immiseration: {
    label: 'Immiseration of the poor',
    icon: Wheat,
    tone: 'warning',
  },
  elite_overproduction: {
    label: 'Elite overproduction',
    icon: Crown,
    tone: 'gold',
  },
  fiscal_distress: { label: 'Fiscal distress', icon: Wallet, tone: 'danger' },
}

export const CHALLENGES: Record<Schema['ChallengeKind'], Named> = {
  disaster: { label: 'Disaster', icon: CloudLightning, tone: 'danger' },
  climate: { label: 'A turn of the climate', icon: Wind, tone: 'info' },
  invasion: { label: 'Invasion', icon: Swords, tone: 'danger' },
  plague: { label: 'Plague', icon: Bug, tone: 'warning' },
  famine: { label: 'Famine', icon: Wheat, tone: 'warning' },
  collapse: { label: 'Collapse', icon: TrendingDown, tone: 'danger' },
  secession: { label: 'Secession', icon: Split, tone: 'danger' },
  technological_shock: {
    label: 'Technological shock',
    icon: CloudLightning,
    tone: 'danger',
  },
  source_depletion: {
    label: 'Source depletion',
    icon: CloudLightning,
    tone: 'danger',
  },
  runaway: { label: 'Runaway', icon: AlertTriangle, tone: 'danger' },
  revelation: { label: 'Revelation', icon: Eye, tone: 'danger' },
  migration_wave: {
    label: 'Migration wave',
    icon: CloudLightning,
    tone: 'danger',
  },
  long_season: { label: 'Long season', icon: Snowflake, tone: 'danger' },
  succession_crisis: {
    label: 'Succession crisis',
    icon: Crown,
    tone: 'danger',
  },
}

export const RESPONSES: Record<Schema['ChallengeResponse'], Named> = {
  stagnation: { label: 'Stagnation', icon: Hourglass, tone: 'muted' },
  response: { label: 'A creative answer', icon: Sparkles, tone: 'success' },
  collapse: { label: 'Collapse', icon: TrendingDown, tone: 'danger' },
  transformation: { label: 'Transformation', icon: Shuffle, tone: 'muted' },
}

export const PLAN_KINDS: Record<Schema['LongPlanKind'], Named> = {
  ecological_transformation: {
    label: 'Remaking a land',
    icon: Mountain,
    tone: 'verdigris',
  },
  bloodline: { label: 'Breeding a line', icon: GitBranch, tone: 'gold' },
  conversion: {
    label: 'Turning a world to a faith',
    icon: BookHeart,
    tone: 'info',
  },
  wonder: { label: 'Raising a wonder', icon: Landmark, tone: 'gold' },
  forecast: { label: 'Steering a forecast', icon: Activity, tone: 'verdigris' },
  network: {
    label: 'Network',
    icon: MountainSnow,
    tone: 'verdigris',
  },
  megastructure: {
    label: 'Megastructure',
    icon: Pyramid,
    tone: 'verdigris',
  },
  programme: {
    label: 'Programme',
    icon: Mountain,
    tone: 'verdigris',
  },
  realm: {
    label: 'Realm',
    icon: Mountain,
    tone: 'verdigris',
  },
  line: {
    label: 'Line',
    icon: LineStyle,
    tone: 'verdigris',
  },
  reform: {
    label: 'Reform',
    icon: Mountain,
    tone: 'verdigris',
  },
  exploration: {
    label: 'Exploration',
    icon: Mountain,
    tone: 'verdigris',
  },
  restoration: {
    label: 'Restoration',
    icon: Hammer,
    tone: 'verdigris',
  },
}

export const PLAN_STATUSES: Record<Schema['LongPlanStatus'], Named> = {
  active: { label: 'Under way', icon: Activity, tone: 'info' },
  completed: { label: 'Fulfilled', icon: Sparkles, tone: 'success' },
  abandoned: { label: 'Abandoned', icon: Ban, tone: 'muted' },
}

export const OCCASIONS: Record<Schema['GiftOccasion'], Named> = {
  courtesy: { label: 'Courtesy', icon: Gift, tone: 'info' },
  feast: { label: 'A rank-claiming feast', icon: Flame, tone: 'gold' },
  circuit: { label: 'A ceremonial circuit', icon: Repeat, tone: 'verdigris' },
  offering: { label: 'An offering', icon: HandHeart, tone: 'gold' },
  marriage: { label: 'A marriage gift', icon: Heart, tone: 'success' },
  return: { label: 'A return gift', icon: Undo2, tone: 'success' },
  alliance: { label: 'Between allies', icon: Handshake, tone: 'info' },
  relief: {
    label: 'Aid in a stricken hour',
    icon: HeartHandshake,
    tone: 'success',
  },
  birth: { label: 'At a birth', icon: Baby, tone: 'success' },
  funeral: { label: 'To the bereaved', icon: Flower2, tone: 'muted' },
  amends: { label: 'Amends for a wrong', icon: Scale, tone: 'warning' },
  patronage: { label: 'From a patron', icon: Crown, tone: 'gold' },
  hospitality: {
    label: 'Between host and guest',
    icon: DoorOpen,
    tone: 'info',
  },
  farewell: { label: 'At a parting', icon: Hand, tone: 'info' },
  homecoming: { label: 'At a homecoming', icon: Home, tone: 'success' },
  initiation: { label: 'Initiation', icon: KeyRound, tone: 'gold' },
}

export const GIFT_STATES: Record<Schema['GiftState'], Named> = {
  open: { label: 'Awaiting return', icon: PackageOpen, tone: 'warning' },
  returned: { label: 'Returned', icon: Undo2, tone: 'success' },
  refused: { label: 'Refused, an insult', icon: Ban, tone: 'danger' },
  destroyed: {
    label: 'Wealth destroyed, to be matched',
    icon: Flame,
    tone: 'gold',
  },
  lapsed: { label: 'Unanswered, face lost', icon: TrendingDown, tone: 'muted' },
  exceeded: {
    label: 'Answered with more, the giver now owes',
    icon: TrendingUp,
    tone: 'gold',
  },
  passed_on: {
    label: 'Passed on along a circuit',
    icon: Repeat,
    tone: 'verdigris',
  },
  released: {
    label: 'Debt released by grace',
    icon: HandHeart,
    tone: 'success',
  },
  hoarded: { label: 'Hoarded', icon: Archive, tone: 'warning' },
}

export const DESCENTS: Record<Schema['KinshipDescent'], Named> = {
  through_first_line: {
    label: 'Through the first line',
    icon: GitBranch,
    tone: 'info',
  },
  through_second_line: {
    label: 'Through the second line',
    icon: GitBranch,
    tone: 'verdigris',
  },
  bilateral: { label: 'Through both alike', icon: GitMerge, tone: 'success' },
  double: {
    label: 'Through both, for different things',
    icon: GitFork,
    tone: 'gold',
  },
  ambilineal: {
    label: 'Through the line each child picks',
    icon: ArrowDownUp,
    tone: 'muted',
  },
}

export const RESIDENCES: Record<Schema['ResidenceRule'], Named> = {
  with_first_family: {
    label: "With the first spouse's family",
    icon: Building,
    tone: 'info',
  },
  with_second_family: {
    label: "With the second spouse's family",
    icon: Building,
    tone: 'verdigris',
  },
  new_household: {
    label: 'In a home of their own',
    icon: Tent,
    tone: 'success',
  },
  with_kin_of_the_first_line: {
    label: 'With kin of the first line',
    icon: Users,
    tone: 'gold',
  },
}

export const GROUPS: Record<Schema['DescentGroup'], Named> = {
  lineage: { label: 'Lineages', icon: GitBranch, tone: 'info' },
  clan: { label: 'Clans', icon: Network, tone: 'gold' },
  moiety: { label: 'Two halves', icon: Blend, tone: 'verdigris' },
  house: { label: 'Houses', icon: Landmark, tone: 'success' },
}

export const KIN_TERMS: Record<Schema['KinTermSystem'], Named> = {
  generational: {
    label: 'One term for each generation',
    icon: Users,
    tone: 'gold',
  },
  lineal: {
    label: 'Direct kin apart from side kin',
    icon: Link,
    tone: 'muted',
  },
  bifurcate_merging: {
    label: "A parent's like sibling is called parent",
    icon: Link,
    tone: 'info',
  },
  bifurcate_collateral: {
    label: 'Each side has its own terms',
    icon: Split,
    tone: 'verdigris',
  },
  cross_parallel: {
    label: 'Parallel cousins are siblings, cross cousins apart',
    icon: Link,
    tone: 'info',
  },
  descriptive: {
    label: 'Each kinsperson has a term of their own',
    icon: Users,
    tone: 'muted',
  },
}

export const ADOPTIONS: Record<Schema['AdoptionKind'], Named> = {
  heir: { label: 'Adopted as heirs', icon: Crown, tone: 'gold' },
  ward: { label: 'Taken as wards', icon: Shield, tone: 'info' },
  foster: { label: 'Fostered', icon: Heart, tone: 'success' },
  sponsor: { label: 'Sponsored', icon: Scale, tone: 'muted' },
  blood_bond: {
    label: 'Joined by a bond of blood',
    icon: HandHeart,
    tone: 'danger',
  },
  chosen_kin: {
    label: 'Taken as chosen kin',
    icon: Sparkles,
    tone: 'verdigris',
  },
}

export const FIRST_SIDES: Record<Schema['SexKind'], Named> = {
  bearer: {
    label: 'The bearing side is first',
    icon: Users,
    tone: 'verdigris',
  },
  begetter: {
    label: 'The begetting side is first',
    icon: UsersRound,
    tone: 'info',
  },
  both: { label: 'Not a side', icon: UserRound, tone: 'muted' },
  neither: { label: 'Not a side', icon: Minus, tone: 'muted' },
  none: { label: 'Not a side', icon: Group, tone: 'muted' },
}

export const SYSTEMS: Record<Schema['ReproductiveSystem'], Named> = {
  two_sex: { label: 'Two sexes', icon: Heart, tone: 'info' },
  sequential: {
    label: 'Sex changes with age',
    icon: Recycle,
    tone: 'verdigris',
  },
  ambisexual: {
    label: 'Either sex, taken when fertile',
    icon: Blend,
    tone: 'gold',
  },
  caste: {
    label: 'Castes of workers, soldiers and breeders',
    icon: Network,
    tone: 'warning',
  },
  asexual: { label: 'Budding or dividing', icon: Flower2, tone: 'success' },
}

export const CASTES: Record<Schema['ReproductiveCaste'], Named> = {
  worker: { label: 'Worker', icon: HardHat, tone: 'info' },
  soldier: { label: 'Soldier', icon: Shield, tone: 'danger' },
  breeder: { label: 'Breeder', icon: Baby, tone: 'gold' },
}

export const MOBILITY: Record<Schema['MobilityMode'], Named> = {
  sedentary: { label: 'Settled', icon: Building, tone: 'muted' },
  transhumant: {
    label: 'Between two pastures',
    icon: ArrowDownUp,
    tone: 'verdigris',
  },
  nomadic: { label: 'Roaming a circuit', icon: Footprints, tone: 'gold' },
}

export const LEGACIES: Record<Schema['LegacyKind'], Named> = {
  martial_style: { label: 'Way of war', icon: Swords, tone: 'danger' },
  aesthetic: { label: 'Style', icon: Sparkles, tone: 'gold' },
  funeral_rite: { label: 'Funeral rite', icon: Bird, tone: 'muted' },
  belief: { label: 'Belief', icon: BookHeart, tone: 'info' },
  value: { label: 'Value', icon: Scale, tone: 'verdigris' },
  innovation: { label: 'Innovation', icon: Lightbulb, tone: 'info' },
  art_form: { label: 'Art form', icon: Palette, tone: 'gold' },
  technique: { label: 'Technique', icon: Wrench, tone: 'danger' },
  law: { label: 'Law', icon: Gavel, tone: 'danger' },
  institution: { label: 'Institution', icon: Landmark, tone: 'danger' },
  language: { label: 'Language', icon: Languages, tone: 'danger' },
}

export const REGIMES: Record<Schema['LabourRegime'], Named> = {
  indenture: {
    label: 'Indenture for a term',
    icon: ScrollText,
    tone: 'warning',
  },
  peonage: { label: 'Debt peonage', icon: Wallet, tone: 'danger' },
}

export const PATHS: Record<Schema['ManumissionPath'], Named> = {
  purchase: { label: 'Bought their freedom', icon: Coins, tone: 'gold' },
  will: { label: "By a master's will", icon: ScrollText, tone: 'info' },
  service: { label: 'Freed for service', icon: Shield, tone: 'success' },
  law: { label: 'By law', icon: Scale, tone: 'verdigris' },
  revolt: { label: 'By revolt', icon: ShieldAlert, tone: 'danger' },
}

export const TAB_ICONS = {
  stress: Activity,
  solidarity: TrendingUp,
  plans: Route,
  gifts: Gift,
  kin: HeartHandshake,
  nomads: Tent,
  labour: HardHat,
} as const

export const YES_NO = { true: 'Yes', false: 'No' }
