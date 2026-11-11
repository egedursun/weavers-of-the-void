import { why } from '@/features/dominion/model'
import { type CollectiveAction, useCollectiveAction } from './api'

type Values = Record<string, number | string | boolean | null>
export type Edit = { values: Values; release: string[] }

export const SPAN = 100

export function clamp(text: string, max = SPAN, min = 0) {
  const value = Number(text)
  return Number.isNaN(value)
    ? min
    : Math.max(min, Math.min(max, Math.round(value)))
}

export function useRow<
  E extends CollectiveAction,
  D extends CollectiveAction,
  K extends object,
>(edit: E, remove: D, keys: K, blocked: string | null) {
  const editing = useCollectiveAction(
    edit,
    (vars: Edit) => ({ ...keys, ...vars }) as never,
    'Set so'
  )
  const removing = useCollectiveAction(
    remove,
    (_: void) => keys as never,
    'Done'
  )
  return {
    busy: why(blocked, editing.isPending, removing.isPending),
    onEdit: (vars: Edit) => editing.mutate(vars),
    onRemove: () => removing.mutate(),
  }
}

export function useRemove<D extends CollectiveAction, K extends object>(
  remove: D,
  keys: K,
  blocked: string | null
) {
  const removing = useCollectiveAction(
    remove,
    (_: void) => keys as never,
    'Done'
  )
  return {
    busy: why(blocked, removing.isPending),
    onRemove: () => removing.mutate(),
  }
}
