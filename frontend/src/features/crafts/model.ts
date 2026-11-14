import { why } from '@/features/dominion/model'
import { type CraftsAction, useCraftsAction } from './api'

type Values = Record<string, number | string | boolean | null>
type Edit = { values: Values; release: string[] }

export const SPAN = 100
export const MANY = 1_000_000
export const MORTAL_TYPES = ['mortal'] as const
export const PEOPLE_TYPES = ['people'] as const
export const REALM_TYPES = ['polity'] as const

export function useCraftsRow<
  E extends CraftsAction,
  D extends CraftsAction,
  K extends object,
>(edit: E, remove: D, keys: K, blocked: string | null) {
  const editing = useCraftsAction(
    edit,
    (vars: Edit) => ({ ...keys, ...vars }) as never,
    'Set so'
  )
  const removing = useCraftsAction(remove, (_: void) => keys as never, 'Done')
  return {
    busy: why(blocked, editing.isPending, removing.isPending),
    onEdit: (vars: Edit) => editing.mutate(vars),
    onRemove: () => removing.mutate(),
  }
}

export function useCraftsStep<A extends CraftsAction, K extends object>(
  action: A,
  keys: K,
  blocked: string | null,
  success: string
) {
  const running = useCraftsAction(action, (_: void) => keys as never, success)
  return { busy: why(blocked, running.isPending), run: () => running.mutate() }
}
