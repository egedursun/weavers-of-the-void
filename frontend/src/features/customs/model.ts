import { why } from '@/features/dominion/model'
import { type CustomsAction, useCustomsAction } from './api'

type Values = Record<string, number | string | boolean | null>
type Edit = { values: Values; release: string[] }

export const SPAN = 100
export const MANY = 1_000_000
export const MORTAL_TYPES = ['mortal'] as const
export const PEOPLE_TYPES = ['people'] as const
export const REALM_TYPES = ['polity'] as const

export function useCustomsRow<
  E extends CustomsAction,
  D extends CustomsAction,
  K extends object,
>(edit: E, remove: D, keys: K, blocked: string | null) {
  const editing = useCustomsAction(
    edit,
    (vars: Edit) => ({ ...keys, ...vars }) as never,
    'Set so'
  )
  const removing = useCustomsAction(remove, (_: void) => keys as never, 'Done')
  return {
    busy: why(blocked, editing.isPending, removing.isPending),
    onEdit: (vars: Edit) => editing.mutate(vars),
    onRemove: () => removing.mutate(),
  }
}

export function useCustomsStep<A extends CustomsAction, K extends object>(
  action: A,
  keys: K,
  blocked: string | null,
  success: string
) {
  const running = useCustomsAction(action, (_: void) => keys as never, success)
  return { busy: why(blocked, running.isPending), run: () => running.mutate() }
}
