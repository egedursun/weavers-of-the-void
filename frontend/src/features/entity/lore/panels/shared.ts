import { type KpiTone } from '@/components/domain'
import { type LoreCard as LoreCardData } from '../api'
import { PERCENT, TRADITION_TERMS } from '../model'

export type Card<K extends keyof LoreCardData> = NonNullable<LoreCardData[K]>
export const COMMUNITIES = [
  'settlement',
  'people',
  'cult',
  'faction',
  'polity',
] as const
export const COST_ONLY = Object.fromEntries(
  ['food', 'goods'].map((key) => [key, TRADITION_TERMS[key]])
)
export const ENTITY_ARGS = new Set([
  'entity',
  'settlement',
  'house',
  'first',
  'second',
  'polity',
  'chosen',
])
export const WORN = 20
export const WEARING = 50

export function percentHint(value: number, high: string, low: string) {
  return value >= PERCENT / 2 ? high : low
}

export function average(values: number[]): number {
  if (values.length === 0) return 0
  return Math.round(
    values.reduce((sum, value) => sum + value, 0) / values.length
  )
}

export function wear(condition: number): KpiTone {
  if (condition < WORN) return 'danger'
  if (condition < WEARING) return 'warning'
  return 'success'
}
