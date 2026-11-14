import { why } from '@/features/dominion/model'
import { type FolkwaysAction, useFolkwaysAction } from './api'

type Values = Record<string, number | string | boolean | null>
type Edit = { values: Values; release: string[] }

export const SPAN = 100
export const MANY = 1_000_000
export const MIDDLE = 50
export const PEOPLE_TYPES = ['people'] as const
export const MORTAL_TYPES = ['mortal'] as const
export const TOWN_TYPES = ['settlement'] as const
export const ITEM_TYPES = ['item'] as const

export function useFolkwaysRow<
  E extends FolkwaysAction,
  D extends FolkwaysAction,
  K extends object,
>(edit: E, remove: D, keys: K, blocked: string | null) {
  const editing = useFolkwaysAction(
    edit,
    (vars: Edit) => ({ ...keys, ...vars }) as never,
    'Set so'
  )
  const removing = useFolkwaysAction(remove, (_: void) => keys as never, 'Done')
  return {
    busy: why(blocked, editing.isPending, removing.isPending),
    onEdit: (vars: Edit) => editing.mutate(vars),
    onRemove: () => removing.mutate(),
  }
}

export function useFolkwaysStep<A extends FolkwaysAction, K extends object>(
  action: A,
  keys: K,
  blocked: string | null,
  success: string
) {
  const running = useFolkwaysAction(action, (_: void) => keys as never, success)
  return { busy: why(blocked, running.isPending), run: () => running.mutate() }
}

export function withNone(record: Record<string, string>, none: string) {
  return { none, ...record }
}
