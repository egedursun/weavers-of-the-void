import {
  Bird,
  Bone,
  Box,
  CloudFog,
  Dna,
  Flame,
  Gem,
  Ghost,
  HeartPulse,
  Hexagon,
  Hourglass,
  type LucideIcon,
  Mountain,
  Repeat,
  Shield,
  Skull,
  Sprout,
  Utensils,
  Waves,
  Wind,
  Baby,
  Droplets,
  Bug,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'

type Schema = components['schemas']

export const BIOLOGY_ICON: LucideIcon = Dna

export const VARIANTS: Record<Schema['BiologyVariant'], Named> = {
  incorporeal: { label: 'Incorporeal', icon: Ghost, tone: 'info' },
  aquatic: { label: 'Aquatic', icon: Waves, tone: 'info' },
  aerial: { label: 'Aerial', icon: Bird, tone: 'info' },
  subterranean: { label: 'Subterranean', icon: Mountain, tone: 'muted' },
  hive: { label: 'Hive', icon: Hexagon, tone: 'gold' },
  plant_like: { label: 'Plant-like', icon: Sprout, tone: 'success' },
  construct: { label: 'Construct', icon: Box, tone: 'muted' },
  ageless: { label: 'Ageless', icon: Hourglass, tone: 'gold' },
  shapeshifting: { label: 'Shapeshifting', icon: Repeat, tone: 'verdigris' },
  gaseous: { label: 'Gaseous', icon: CloudFog, tone: 'info' },
  crystalline: { label: 'Crystalline', icon: Gem, tone: 'verdigris' },
  undead: { label: 'Undead', icon: Skull, tone: 'danger' },
}

export const SHARES = [
  { key: 'food_need_pct', label: 'Food needed', icon: Utensils },
  { key: 'fertility_pct', label: 'Births', icon: Baby },
  { key: 'death_pct', label: 'Deaths', icon: Bone },
  { key: 'disease_pct', label: 'Sickness', icon: Bug },
  { key: 'morale_loss_pct', label: 'Fear in battle', icon: Shield },
  { key: 'fire_harm_pct', label: 'Harm from fire', icon: Flame },
  { key: 'storm_harm_pct', label: 'Harm from storms', icon: Wind },
] as const

export const FLAGS = [
  { key: 'breathes', label: 'Breathes', icon: Wind },
  { key: 'drinks', label: 'Drinks', icon: Droplets },
  { key: 'ages', label: 'Ages', icon: HeartPulse },
] as const
