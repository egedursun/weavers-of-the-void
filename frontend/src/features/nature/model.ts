import { why } from '@/features/dominion/model'
import { type NatureAction, useNatureAction } from './api'

type Values = Record<string, number | string | boolean | null>
type Edit = { values: Values; release: string[] }

export const SPAN = 100
export const MANY = 1_000_000
export const KIND_TYPES = ['species', 'beast'] as const
export const HOLDER_TYPES = [
  'settlement',
  'faction',
  'structure',
  'house',
] as const

export function useNatureRow<
  E extends NatureAction,
  D extends NatureAction,
  K extends object,
>(edit: E, remove: D, keys: K, blocked: string | null) {
  const editing = useNatureAction(
    edit,
    (vars: Edit) => ({ ...keys, ...vars }) as never,
    'Set so'
  )
  const removing = useNatureAction(remove, (_: void) => keys as never, 'Done')
  return {
    busy:
      editing.blockedReason ??
      removing.blockedReason ??
      why(blocked, editing.isPending, removing.isPending),
    onEdit: (vars: Edit) => editing.mutate(vars),
    onRemove: () => removing.mutate(),
  }
}

export function useProfileEdit<E extends NatureAction, K extends object>(
  edit: E,
  keys: K,
  blocked: string | null
) {
  const editing = useNatureAction(
    edit,
    (vars: Edit) => ({ ...keys, ...vars }) as never,
    'Set so'
  )
  return {
    busy: editing.blockedReason ?? why(blocked, editing.isPending),
    onEdit: (vars: Edit) => editing.mutate(vars),
  }
}
