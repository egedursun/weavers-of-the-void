export const PERCENT = 100
const WORKING = 'Working…'

export const STRESS_WORDS: [string, string, string, string] = [
  'Uneasy',
  'Troubled',
  'Tormented',
  'Breaking',
]

export function busyOf(
  blocked: string | null,
  ...pending: boolean[]
): string | null {
  return blocked ?? (pending.some(Boolean) ? WORKING : null)
}

export function clampPercent(value: number): number {
  return Math.max(0, Math.min(PERCENT, Math.round(value)))
}
