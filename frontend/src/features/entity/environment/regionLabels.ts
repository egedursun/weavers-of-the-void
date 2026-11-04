import {
  Biohazard,
  Bug,
  Castle,
  CloudRain,
  Crown,
  Flame,
  Ghost,
  HandHeart,
  Mountain,
  MountainSnow,
  PawPrint,
  ScrollText,
  Skull,
  Snowflake,
  Sparkles,
  Swords,
  Waves,
  Wheat,
  Zap,
  type LucideIcon,
} from 'lucide-react'
import type { KpiTone } from '@/components/domain'
import type { Named } from './labels'

export const DANGER_SOURCE: Record<string, Named & { hint: string }> = {
  beasts: {
    label: 'Beasts',
    icon: PawPrint,
    tone: 'warning',
    hint: 'Fierce wild kinds and named beasts with their lairs here',
  },
  bandits: {
    label: 'Bandits',
    icon: Swords,
    tone: 'danger',
    hint: 'Outlaws, deserters and lawless land no realm controls',
  },
  monsters: {
    label: 'Monsters',
    icon: Skull,
    tone: 'danger',
    hint: 'The most dangerous kinds of the world stalk this land',
  },
  phenomena: {
    label: 'Phenomena',
    icon: Ghost,
    tone: 'verdigris',
    hint: 'Hauntings, leak wounds, blight, wild magic and dark memories',
  },
  disease: {
    label: 'Disease',
    icon: Biohazard,
    tone: 'warning',
    hint: 'Fevers from a sick land and old plague ground',
  },
  avalanche: {
    label: 'Avalanches',
    icon: MountainSnow,
    tone: 'info',
    hint: 'Snow slopes in cold, rough country',
  },
  quicksand: {
    label: 'Quicksand',
    icon: Waves,
    tone: 'muted',
    hint: 'Sucking ground in marsh, wetland and desert sand',
  },
  volcanic: {
    label: 'Volcanic ground',
    icon: Flame,
    tone: 'danger',
    hint: 'Fumes, fire and craters of volcanic land',
  },
}

export const HARM: Record<string, Named> = {
  settlers: { label: 'Settlers', icon: Castle, tone: 'danger' },
  livestock: { label: 'Livestock', icon: Wheat, tone: 'warning' },
  travellers: { label: 'Travellers', icon: Mountain, tone: 'info' },
  armies: { label: 'Armies', icon: Swords, tone: 'danger' },
  ambush: { label: 'Ambush', icon: Zap, tone: 'warning' },
  merchants: { label: 'Merchants', icon: Crown, tone: 'gold' },
}

export const ORIGIN: Record<string, { label: string; tone: BadgeTone }> = {
  derived: { label: 'Bred by the land', tone: 'secondary' },
  player: { label: 'Set by your hand', tone: 'info' },
  divine: { label: 'A god’s curse', tone: 'warning' },
}

export type BadgeTone =
  'secondary' | 'info' | 'success' | 'warning' | 'destructive' | 'default'

export const MEMORY: Record<string, Named> = {
  battle: { label: 'Battle', icon: Swords, tone: 'warning' },
  massacre: { label: 'Massacre', icon: Skull, tone: 'danger' },
  sack: { label: 'Sack', icon: Flame, tone: 'danger' },
  disaster: { label: 'Disaster', icon: CloudRain, tone: 'warning' },
  plague: { label: 'Plague', icon: Bug, tone: 'danger' },
  famine: { label: 'Famine', icon: Wheat, tone: 'warning' },
  god_death: { label: 'A god fell here', icon: Crown, tone: 'gold' },
  saint_burial: { label: 'Saint’s grave', icon: HandHeart, tone: 'success' },
  miracle: { label: 'Miracle', icon: Sparkles, tone: 'gold' },
}

export const HAZARD: Record<string, Named & { season: string }> = {
  avalanche: {
    label: 'Avalanche',
    icon: MountainSnow,
    tone: 'info',
    season: 'in the coldest season',
  },
  spring_flood: {
    label: 'Spring flood',
    icon: Waves,
    tone: 'info',
    season: 'in the wettest season',
  },
  wildfire: {
    label: 'Wildfire',
    icon: Flame,
    tone: 'danger',
    season: 'in the hottest season',
  },
  whiteout: {
    label: 'Whiteout',
    icon: Snowflake,
    tone: 'info',
    season: 'in the coldest season',
  },
}

export const KNOWLEDGE_ICON: LucideIcon = ScrollText

const DANGER_HIGH = 60
const DANGER_MID = 30

export function dangerTone(value: number): KpiTone {
  if (value >= DANGER_HIGH) return 'danger'
  if (value >= DANGER_MID) return 'warning'
  return value > 0 ? 'gold' : 'success'
}

export function sacredTone(value: number, threshold: number): KpiTone {
  if (value >= threshold) return 'gold'
  return value > 0 ? 'verdigris' : 'muted'
}
