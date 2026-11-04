import {
  Eye,
  Footprints,
  Map as MapIcon,
  Mountain,
  Ship,
  Sparkles,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type KpiTone } from '@/components/domain'
import { type LoreNamed, PERCENT } from '../model'

export type RumourBoard = components['schemas']['RumourBoard']
export type Rumour = components['schemas']['RumourView']
type Channel = components['schemas']['RumourChannel']

export const CHANNELS: Record<Channel, LoreNamed> = {
  witness: { label: 'Seen with their own eyes', icon: Eye, tone: 'success' },
  route: { label: 'Down the trade road', icon: Ship, tone: 'info' },
  pilgrimage: { label: 'From pilgrims', icon: Mountain, tone: 'gold' },
  journey: {
    label: 'Brought by travellers',
    icon: Footprints,
    tone: 'verdigris',
  },
  spy: { label: 'Reported by spies', icon: MapIcon, tone: 'warning' },
  planted: { label: 'Whispered by your hand', icon: Sparkles, tone: 'gold' },
}

const TRUE = 75
const GARBLED = 40

export function truthTone(fidelity: number): KpiTone {
  if (fidelity >= TRUE) return 'success'
  if (fidelity >= GARBLED) return 'warning'
  return 'danger'
}

export function truthBar(
  fidelity: number
): 'success' | 'warning' | 'destructive' {
  if (fidelity >= TRUE) return 'success'
  if (fidelity >= GARBLED) return 'warning'
  return 'destructive'
}

export function truthWord(fidelity: number): string {
  if (fidelity >= TRUE) return 'close to the truth'
  if (fidelity >= GARBLED) return 'half true'
  return 'garbled'
}

export function averageTruth(rumours: readonly Rumour[]): number {
  if (rumours.length === 0) return 0
  return Math.round(
    rumours.reduce((sum, item) => sum + item.fidelity, 0) / rumours.length
  )
}

export function clampTruth(value: number): number {
  return Math.max(0, Math.min(PERCENT, Math.round(value)))
}
