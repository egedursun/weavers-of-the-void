import {
  Activity,
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
  Flame,
  Flower2,
  Footprints,
  Gem,
  Gift,
  GitBranch,
  GitFork,
  GitMerge,
  Handshake,
  HandHeart,
  HardHat,
  Heart,
  HeartHandshake,
  Hourglass,
  Landmark,
  Lightbulb,
  Link,
  type LucideIcon,
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
  Sparkles,
  Sprout,
  Swords,
  Tent,
  TrendingDown,
  TrendingUp,
  Undo2,
  Unlink,
  Users,
  Wallet,
  Wheat,
  Wind,
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
}

export const RESPONSES: Record<Schema['ChallengeResponse'], Named> = {
  stagnation: { label: 'Stagnation', icon: Hourglass, tone: 'muted' },
  response: { label: 'A creative answer', icon: Sparkles, tone: 'success' },
  collapse: { label: 'Collapse', icon: TrendingDown, tone: 'danger' },
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
  relief: { label: 'Aid in a stricken hour', icon: HandHeart, tone: 'success' },
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
}

export const DESCENTS: Record<Schema['KinshipDescent'], Named> = {
  patrilineal: {
    label: 'Patrilineal, through the male line',
    icon: GitBranch,
    tone: 'info',
  },
  matrilineal: {
    label: 'Matrilineal, through the female line',
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
  patrilocal: {
    label: "Patrilocal, with the male spouse's kin",
    icon: Building,
    tone: 'info',
  },
  matrilocal: {
    label: "Matrilocal, with the female spouse's kin",
    icon: Building,
    tone: 'verdigris',
  },
  neolocal: { label: 'In a home of their own', icon: Tent, tone: 'success' },
  avunculocal: { label: 'With a maternal uncle', icon: Users, tone: 'gold' },
}

export const GROUPS: Record<Schema['DescentGroup'], Named> = {
  lineage: { label: 'Lineages', icon: GitBranch, tone: 'info' },
  clan: { label: 'Clans', icon: Network, tone: 'gold' },
  moiety: { label: 'Two halves', icon: Blend, tone: 'verdigris' },
  house: { label: 'Houses', icon: Landmark, tone: 'success' },
}

export const COUSINS: Record<Schema['CousinTerms'], Named> = {
  distinct: { label: 'Cousins are cousins', icon: Users, tone: 'muted' },
  parallel_as_siblings: {
    label: 'Parallel cousins are siblings',
    icon: Link,
    tone: 'info',
  },
  all_as_siblings: {
    label: 'Every cousin is a sibling',
    icon: Link,
    tone: 'gold',
  },
}

export const PREFERENCES: Record<Schema['MarriagePreference'], Named> = {
  none: { label: 'No preferred spouse', icon: Heart, tone: 'muted' },
  cross_cousin: { label: 'A cross-cousin', icon: HeartHandshake, tone: 'gold' },
  clan_exogamy: { label: 'Outside the clan', icon: Unlink, tone: 'info' },
  moiety_exogamy: {
    label: 'In the other half',
    icon: Blend,
    tone: 'verdigris',
  },
}

export const PAYMENTS: Record<Schema['MarriagePayment'], Named> = {
  none: { label: 'Nothing passes', icon: Heart, tone: 'muted' },
  bride_price: {
    label: "Bride price to the bride's kin",
    icon: Coins,
    tone: 'gold',
  },
  dowry: { label: 'A dowry with the bride', icon: Gem, tone: 'gold' },
  bride_service: {
    label: 'Bride service in labour',
    icon: HardHat,
    tone: 'info',
  },
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
  aesthetic: { label: 'Aesthetic', icon: Sparkles, tone: 'gold' },
  funeral_rite: { label: 'Funeral rite', icon: Bird, tone: 'muted' },
  belief: { label: 'Belief', icon: BookHeart, tone: 'info' },
  value: { label: 'Value', icon: Scale, tone: 'verdigris' },
  innovation: { label: 'Innovation', icon: Lightbulb, tone: 'info' },
  art_form: { label: 'Art form', icon: Palette, tone: 'gold' },
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
