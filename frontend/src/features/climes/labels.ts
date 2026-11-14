import {
  CircleDot,
  CloudRain,
  Compass,
  Flame,
  Minus,
  Mountain,
  Orbit,
  Snowflake,
  Sun,
  Wind,
  type LucideIcon,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'
import { COMPASS } from '@/features/operations/labels'

type Schema = components['schemas']

export const CLIMES_ICON: LucideIcon = Wind

export const TAB_ICONS = {
  winds: Wind,
  seasons: CloudRain,
  crossings: Orbit,
} as const

export const BANDS: Record<Schema['CirculationBand'], Named> = {
  trade: { label: 'Trade wind', icon: Wind, tone: 'info' },
  westerly: { label: 'Westerly', icon: Wind, tone: 'verdigris' },
  polar: { label: 'Polar wind', icon: Snowflake, tone: 'muted' },
  single_cell: {
    label: 'One band of a slow world',
    icon: CircleDot,
    tone: 'warning',
  },
  terminator: {
    label: 'Wind from the day side',
    icon: Sun,
    tone: 'gold',
  },
  still: { label: 'Still air', icon: Minus, tone: 'muted' },
}

export const PHASES: Record<Schema['OscillationPhase'], Named> = {
  neutral: { label: 'Neutral', icon: Minus, tone: 'muted' },
  warm: { label: 'Warm swing', icon: Flame, tone: 'warning' },
  cold: { label: 'Cold swing', icon: Snowflake, tone: 'info' },
}

export const DIRECTIONS = COMPASS.map(
  (point) => point.charAt(0).toUpperCase() + point.slice(1)
)

export const DIRECTION_TABLE: Record<string, string> = Object.fromEntries(
  DIRECTIONS.map((label, index) => [String(index), label])
)

export const ROTATIONS = [
  'rotate-0',
  'rotate-45',
  'rotate-90',
  'rotate-135',
  'rotate-180',
  '-rotate-135',
  '-rotate-90',
  '-rotate-45',
] as const

export const COMPASS_ICON: LucideIcon = Compass
export const SHADOW_ICON: LucideIcon = Mountain
