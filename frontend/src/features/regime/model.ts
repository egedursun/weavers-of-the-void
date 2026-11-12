import { why } from '@/features/dominion/model'
import { type RegimeAction, useRegimeAction } from './api'

type Values = Record<string, number | string | boolean | null>
type Edit = { values: Values; release: string[] }

export const PATRON_TYPES = [
  'mortal',
  'house',
  'polity',
  'faction',
  'cult',
] as const
export const DOCTRINE_TYPES = ['theory', 'ideology'] as const

export function useRegimeRow<
  E extends RegimeAction,
  D extends RegimeAction,
  K extends object,
>(edit: E, remove: D, keys: K, blocked: string | null) {
  const editing = useRegimeAction(
    edit,
    (vars: Edit) => ({ ...keys, ...vars }) as never,
    'Set so'
  )
  const removing = useRegimeAction(remove, (_: void) => keys as never, 'Done')
  return {
    busy: why(blocked, editing.isPending, removing.isPending),
    onEdit: (vars: Edit) => editing.mutate(vars),
    onRemove: () => removing.mutate(),
  }
}

export function useRegimeStep<A extends RegimeAction, K extends object>(
  action: A,
  keys: K,
  blocked: string | null,
  success: string
) {
  const running = useRegimeAction(action, (_: void) => keys as never, success)
  return { busy: why(blocked, running.isPending), run: () => running.mutate() }
}
