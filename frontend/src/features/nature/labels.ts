import {
  Bean,
  Bug,
  CircleSlash,
  Compass,
  Droplets,
  Ear,
  Eye,
  Flame,
  FlaskConical,
  Ghost,
  Handshake,
  Leaf,
  type LucideIcon,
  Moon,
  MoonStar,
  Radar,
  Shield,
  Skull,
  Snowflake,
  Sprout,
  Sun,
  Thermometer,
  Vibrate,
  Wheat,
  Wind,
  Zap,
  Drama,
  Egg,
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
}

export const WARMTH: Record<Schema['Thermoregulation'], Named> = {
  endotherm: { label: 'Warm-blooded', icon: Flame, tone: 'gold' },
  ectotherm: { label: 'Cold-blooded', icon: Snowflake, tone: 'info' },
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
}

export const BONDS: Record<Schema['SymbiosisKind'], Named> = {
  mutualism: { label: 'Mutualism', icon: Handshake, tone: 'success' },
  commensalism: { label: 'Commensalism', icon: Leaf, tone: 'verdigris' },
  parasitism: { label: 'Parasitism', icon: Bug, tone: 'danger' },
  mimicry: { label: 'Mimicry', icon: Drama, tone: 'gold' },
}

export const BOND_HINTS: Record<Schema['SymbiosisKind'], string> = {
  mutualism: 'Each gives the other room where they share a land',
  commensalism: 'The first gains room and the second is left be',
  parasitism: 'The first feeds on the second, and on its herds',
  mimicry: 'The first passes for the second, so hunters spare it',
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
}

export const FERMENTS: Record<Schema['FermentKind'], Named> = {
  yeast: { label: 'Yeast', icon: Bean, tone: 'gold' },
  starter: { label: 'Starter', icon: Egg, tone: 'success' },
  mould: { label: 'Mould', icon: Moon, tone: 'muted' },
  lactic: { label: 'Lactic culture', icon: Droplets, tone: 'info' },
  vinegar: { label: 'Vinegar mother', icon: Zap, tone: 'warning' },
}
