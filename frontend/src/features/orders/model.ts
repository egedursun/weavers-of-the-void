import { why } from '@/features/dominion/model'
import { type OrdersAction, useOrdersAction } from './api'

type Values = Record<string, number | string | boolean | null>
type Edit = { values: Values; release: string[] }

export const SPAN = 100
export const MANY = 1_000_000

export function useOrdersRow<
  E extends OrdersAction,
  D extends OrdersAction,
  K extends object,
>(edit: E, remove: D, keys: K, blocked: string | null) {
  const editing = useOrdersAction(
    edit,
    (vars: Edit) => ({ ...keys, ...vars }) as never,
    'Set so'
  )
  const removing = useOrdersAction(remove, (_: void) => keys as never, 'Done')
  return {
    busy: why(blocked, editing.isPending, removing.isPending),
    onEdit: (vars: Edit) => editing.mutate(vars),
    onRemove: () => removing.mutate(),
  }
}

export function clamp(text: string, high: number): number {
  return Math.max(0, Math.min(high, Number(text) || 0))
}
