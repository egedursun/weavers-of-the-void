import { why } from '@/features/dominion/model'
import { type SacredAction, useSacredAction } from './api'

type Values = Record<string, number | string | boolean | null>
type Edit = { values: Values; release: string[] }

export const SPAN = 100
export const MANY = 1_000_000
export const MORTAL_TYPES = ['mortal'] as const
export const TOWN_TYPES = ['settlement'] as const
export const CHURCH_TYPES = ['cult'] as const
export const SPIRIT_TYPES = ['spirit'] as const
export const REALM_TYPES = ['polity'] as const
export const PEOPLE_TYPES = ['people'] as const
export const ORDER_TYPES = ['faction'] as const
export const PROPHECY_TYPES = ['prophecy'] as const
export const SPIRIT_HOMES = ['place', 'settlement', 'house'] as const
export const GOD_KINDS = ['son', 'foreign_god'] as const
export const GODS: readonly string[] = GOD_KINDS
export const SUBJECT_TYPES = ['mortal', 'polity', 'settlement'] as const

export function useSacredRow<
  E extends SacredAction,
  D extends SacredAction,
  K extends object,
>(edit: E, remove: D, keys: K, blocked: string | null) {
  const editing = useSacredAction(
    edit,
    (vars: Edit) => ({ ...keys, ...vars }) as never,
    'Set so'
  )
  const removing = useSacredAction(remove, (_: void) => keys as never, 'Done')
  return {
    busy:
      editing.blockedReason ??
      removing.blockedReason ??
      why(blocked, editing.isPending, removing.isPending),
    onEdit: (vars: Edit) => editing.mutate(vars),
    onRemove: () => removing.mutate(),
  }
}

export function useSacredStep<A extends SacredAction, K extends object>(
  action: A,
  keys: K,
  blocked: string | null,
  success: string
) {
  const running = useSacredAction(action, (_: void) => keys as never, success)
  return {
    busy: running.blockedReason ?? why(blocked, running.isPending),
    run: () => running.mutate(),
  }
}

export function share(part: number, whole: number): number {
  return whole > 0 ? Math.round((part * SPAN) / whole) : 0
}

export function withNone(
  record: Record<string, string>,
  none: string
): Record<string, string> {
  return { none, ...record }
}
