import { why } from '@/features/dominion/model'
import { type BelongingAction, useBelongingAction } from './api'

type Values = Record<string, number | string | boolean | null>
type Edit = { values: Values; release: string[] }

export const SPAN = 100
export const MANY = 1_000_000
export const SETTLEMENT_TYPES = ['settlement'] as const
export const MORTAL_TYPES = ['mortal'] as const
export const REALM_TYPES = ['polity'] as const
export const HOST_TYPES = ['structure', 'settlement', 'polity'] as const
export const PURSUER_TYPES = ['polity', 'mortal', 'faction'] as const
export const WORK_TYPES = ['artwork'] as const
export const VALUE_TYPES = [
  'people',
  'settlement',
  'polity',
  'house',
  'faction',
  'cult',
  'region',
] as const
export const VALUE_KINDS = ['son', 'foreign_god'] as const

export function useBelongingRow<
  E extends BelongingAction,
  D extends BelongingAction,
  K extends object,
>(edit: E, remove: D, keys: K, blocked: string | null) {
  const editing = useBelongingAction(
    edit,
    (vars: Edit) => ({ ...keys, ...vars }) as never,
    'Set so'
  )
  const removing = useBelongingAction(
    remove,
    (_: void) => keys as never,
    'Done'
  )
  return {
    busy:
      editing.blockedReason ??
      removing.blockedReason ??
      why(blocked, editing.isPending, removing.isPending),
    onEdit: (vars: Edit) => editing.mutate(vars),
    onRemove: () => removing.mutate(),
  }
}

export function useBelongingStep<A extends BelongingAction>(
  action: A,
  blocked: string | null,
  success: string
) {
  const running = useBelongingAction(
    action,
    (_: void) => ({}) as never,
    success
  )
  return {
    busy: running.blockedReason ?? why(blocked, running.isPending),
    run: () => running.mutate(),
  }
}
