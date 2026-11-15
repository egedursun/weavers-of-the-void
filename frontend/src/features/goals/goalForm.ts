import { formatInteger } from '@/lib/format'
import { useRuleLookup } from '@/features/pantheon/gate'

export const DEFAULT_DEADLINE = 10
const FALLBACK_DEADLINE_MAX = 500

export function parseCount(text: string): number | null {
  if (text.trim() === '') return null
  const value = Number(text)
  return Number.isInteger(value) ? value : null
}

export function outOfRange(
  value: number | null,
  low: number,
  high: number,
  what: string
): string | null {
  if (value === null) return `Enter a whole number for the ${what}.`
  if (value < low || value > high)
    return `The ${what} must be between ${formatInteger(low)} and ${formatInteger(high)}.`
  return null
}

export function useDeadlineMax(): number {
  const rule = useRuleLookup()
  return rule('goals.deadline_max_epochs') ?? FALLBACK_DEADLINE_MAX
}
