import { type TimelineTone } from '@/components/domain'
import { type ChronicleKind } from '@/features/entity/api/types'

const WEIGHT: Partial<Record<ChronicleKind, number>> = {
  death: 5,
  fate: 4,
  war: 4,
  challenge: 4,
  world: 3,
  curse: 3,
  disaster: 3,
  birth: 2,
  creation: 1,
}

const TONE: Partial<Record<ChronicleKind, TimelineTone>> = {
  death: 'destructive',
  curse: 'destructive',
  disaster: 'destructive',
  fate: 'primary',
  war: 'warning',
  challenge: 'warning',
  world: 'warning',
  birth: 'success',
}

export function kindWeight(kind: string): number {
  return WEIGHT[kind as ChronicleKind] ?? 0
}

export function kindTone(kind: string): TimelineTone {
  return TONE[kind as ChronicleKind] ?? 'default'
}

export function strongestKind(kinds: string[]): string {
  return kinds.reduce(
    (best, kind) => (kindWeight(kind) > kindWeight(best) ? kind : best),
    kinds[0] ?? 'creation'
  )
}

export const DEFAULT_HIDDEN_KINDS: ReadonlySet<string> = new Set([
  'engine_raw',
  'system',
])
