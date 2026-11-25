import { why } from '@/features/dominion/model'
import { type MeansAction, useMeansAction } from './api'

type Values = Record<string, number | string | boolean | null>
type Edit = { values: Values; release: string[] }

export const SPAN = 100
export const MANY = 1_000_000

export function useMeansRow<
  E extends MeansAction,
  D extends MeansAction,
  K extends object,
>(edit: E, remove: D, keys: K, blocked: string | null) {
  const editing = useMeansAction(
    edit,
    (vars: Edit) => ({ ...keys, ...vars }) as never,
    'Set so'
  )
  const removing = useMeansAction(remove, (_: void) => keys as never, 'Done')
  return {
    busy:
      editing.blockedReason ??
      removing.blockedReason ??
      why(blocked, editing.isPending, removing.isPending),
    onEdit: (vars: Edit) => editing.mutate(vars),
    onRemove: () => removing.mutate(),
  }
}
