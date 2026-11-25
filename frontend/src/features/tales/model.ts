import { why } from '@/features/dominion/model'
import { type TalesAction, useTalesAction } from './api'

type Values = Record<string, number | string | boolean | null>
type Edit = { values: Values; release: string[] }

export const SPAN = 100
export const MANY = 1_000_000
export const PEOPLE_TYPES = ['people'] as const
export const REGION_TYPES = ['region'] as const
export const STAR_KINDS = ['star'] as const
export const MORTAL_TYPES = ['mortal'] as const
export const SUBJECT_TYPES = ['mortal', 'house', 'polity', 'faction'] as const
export const FIGURE_TYPES = [
  'mortal',
  'house',
  'polity',
  'faction',
  'beast',
] as const
export const GOD_KINDS = ['son', 'foreign_god'] as const

export function useTalesRow<
  E extends TalesAction,
  D extends TalesAction,
  K extends object,
>(edit: E, remove: D, keys: K, blocked: string | null) {
  const editing = useTalesAction(
    edit,
    (vars: Edit) => ({ ...keys, ...vars }) as never,
    'Set so'
  )
  const removing = useTalesAction(remove, (_: void) => keys as never, 'Done')
  return {
    busy:
      editing.blockedReason ??
      removing.blockedReason ??
      why(blocked, editing.isPending, removing.isPending),
    onEdit: (vars: Edit) => editing.mutate(vars),
    onRemove: () => removing.mutate(),
  }
}

export function useTalesStep<A extends TalesAction, K extends object>(
  action: A,
  keys: K,
  blocked: string | null,
  success: string
) {
  const running = useTalesAction(action, (_: void) => keys as never, success)
  return {
    busy: running.blockedReason ?? why(blocked, running.isPending),
    run: () => running.mutate(),
  }
}

export function withNoRole(
  record: Record<string, string>
): Record<string, string> {
  return { none: 'No part', ...record }
}
