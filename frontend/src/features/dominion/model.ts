const WORKING = 'Working on it.'
export const GOD_KINDS = ['son', 'foreign_god', 'creator'] as const
export const PLACE_TYPES = ['place', 'settlement', 'structure', 'region']
export const HOME_TYPES = ['place', 'region']

export function why(blocked: string | null, ...pending: boolean[]) {
  return blocked ?? (pending.some(Boolean) ? WORKING : null)
}
