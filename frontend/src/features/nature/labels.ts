import {
  Bean,
  Bug,
  CircleSlash,
  Compass,
  Copy,
  Drama,
  Droplets,
  Ear,
  Egg,
  Eye,
  Flame,
  FlaskConical,
  Gauge,
  Ghost,
  Handshake,
  Hourglass,
  Leaf,
  MinusCircle,
  Moon,
  MoonStar,
  PauseCircle,
  Radar,
  RefreshCw,
  Shield,
  ShieldCheck,
  Skull,
  Snowflake,
  Sprout,
  Sun,
  SunDim,
  Thermometer,
  Utensils,
  Vibrate,
  Wheat,
  Wind,
  Zap,
  type LucideIcon,
  ThermometerSun,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'

type Schema = components['schemas']

export const NATURE_ICON: LucideIcon = Sprout

export const TAB_ICONS = {
  body: Thermometer,
  senses: Eye,
  bonds: Handshake,
  soil: Leaf,
} as const

export const SLEEP: Record<Schema['Dormancy'], Named> = {
  none: { label: 'Never sleeps a season', icon: Sun, tone: 'muted' },
  hibernation: {
    label: 'Sleeps through the cold',
    icon: Snowflake,
    tone: 'info',
  },
  aestivation: {
    label: 'Sleeps through the heat',
    icon: Flame,
    tone: 'warning',
  },
  torpor: { label: 'Slows in daily torpor', icon: Moon, tone: 'verdigris' },
  cryptobiosis: {
    label: 'Lies near lifeless for years',
    icon: Hourglass,
    tone: 'muted',
  },
  diapause: {
    label: 'Pauses its young until the season returns',
    icon: PauseCircle,
    tone: 'info',
  },
}

export const WARMTH: Record<Schema['Thermoregulation'], Named> = {
  endotherm: { label: 'Warm-blooded', icon: Flame, tone: 'gold' },
  ectotherm: { label: 'Cold-blooded', icon: Snowflake, tone: 'info' },
  heterotherm: {
    label: 'Warm and cold by turns',
    icon: Thermometer,
    tone: 'verdigris',
  },
  athermic: {
    label: 'Untouched by heat or cold',
    icon: CircleSlash,
    tone: 'muted',
  },
  mesotherm: {
    label: 'Warm core, cooler limbs',
    icon: ThermometerSun,
    tone: 'verdigris',
  },
}

export const SENSES: Record<Schema['SenseKind'], Named> = {
  sight: { label: 'Sight', icon: Eye, tone: 'gold' },
  night_vision: { label: 'Night vision', icon: MoonStar, tone: 'info' },
  smell: { label: 'Smell', icon: Wind, tone: 'success' },
  hearing: { label: 'Hearing', icon: Ear, tone: 'verdigris' },
  echolocation: { label: 'Echolocation', icon: Radar, tone: 'info' },
  vibration: { label: 'Feeling vibration', icon: Vibrate, tone: 'muted' },
  magnetic: { label: 'Sense of direction', icon: Compass, tone: 'verdigris' },
  spirit_sight: { label: 'Spirit sight', icon: Ghost, tone: 'gold' },
  heat: { label: 'Sensing heat', icon: Thermometer, tone: 'warning' },
  electric: { label: 'Electric sense', icon: Zap, tone: 'info' },
  ultraviolet: { label: 'Ultraviolet sight', icon: SunDim, tone: 'gold' },
  taste: { label: 'Taste', icon: Utensils, tone: 'gold' },
  pressure: { label: 'Sense of pressure', icon: Gauge, tone: 'info' },
}

export const BONDS: Record<Schema['SymbiosisKind'], Named> = {
  mutualism: { label: 'Mutualism', icon: Handshake, tone: 'success' },
  commensalism: { label: 'Commensalism', icon: Leaf, tone: 'verdigris' },
  parasitism: { label: 'Parasitism', icon: Bug, tone: 'danger' },
  mimicry: { label: 'Mimicry', icon: Drama, tone: 'gold' },
  amensalism: {
    label: 'Harms without gain',
    icon: MinusCircle,
    tone: 'warning',
  },
  farming: { label: 'Tends and harvests', icon: Sprout, tone: 'success' },
}

export const BOND_HINTS: Record<Schema['SymbiosisKind'], string> = {
  mutualism: 'Each gives the other room where they share a land',
  commensalism: 'The first gains room and the second is left be',
  parasitism: 'The first feeds on the second, and on its herds',
  mimicry: 'The first passes for the second, so hunters spare it',
  amensalism:
    'One kind harms the other by its shade or the ground it fouls, and gains nothing',
  farming: 'One kind tends, guards and harvests the other, and both grow',
}

export const DEFENCES: Record<Schema['PlantDefence'], Named> = {
  none: { label: 'Undefended', icon: CircleSlash, tone: 'muted' },
  thorns: { label: 'Thorns', icon: Shield, tone: 'warning' },
  toxins: { label: 'Toxins', icon: FlaskConical, tone: 'danger' },
  allelopathy: {
    label: 'Poisons its neighbours',
    icon: Wheat,
    tone: 'warning',
  },
  carnivorous: { label: 'Eats flesh', icon: Skull, tone: 'danger' },
  stinging: { label: 'Stinging hairs', icon: Bug, tone: 'warning' },
  guardians: {
    label: 'Guarded by allies',
    icon: ShieldCheck,
    tone: 'verdigris',
  },
  mimicry: { label: 'Looks like a guarded plant', icon: Copy, tone: 'info' },
  regrowth: { label: 'Grows back fast', icon: RefreshCw, tone: 'success' },
}

export const FERMENTS: Record<Schema['FermentKind'], Named> = {
  yeast: { label: 'Yeast', icon: Bean, tone: 'gold' },
  starter: { label: 'Starter', icon: Egg, tone: 'success' },
  mould: { label: 'Mould', icon: Moon, tone: 'muted' },
  lactic: { label: 'Lactic culture', icon: Droplets, tone: 'info' },
  vinegar: { label: 'Vinegar mother', icon: Zap, tone: 'warning' },
  alkaline: { label: 'Alkaline culture', icon: FlaskConical, tone: 'gold' },
  wild: { label: 'Wild culture of a place', icon: Wind, tone: 'verdigris' },
}
