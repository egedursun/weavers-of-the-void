import { why } from '@/features/dominion/model'
import { type HonoursAction, useHonoursAction } from './api'

type Values = Record<string, number | string | boolean | null>
type Edit = { values: Values; release: string[] }

export const SPAN = 100
export const MANY = 1_000_000

export function useHonoursRow<E extends HonoursAction, D extends HonoursAction>(
  edit: E,
  remove: D,
  recordId: number,
  blocked: string | null
) {
  const editing = useHonoursAction(
    edit,
    (vars: Edit) => ({ record_id: recordId, ...vars }) as never,
    'Set so'
  )
  const removing = useHonoursAction(
    remove,
    (_: void) => ({ record_id: recordId }) as never,
    'Done'
  )
  return {
    busy: why(blocked, editing.isPending, removing.isPending),
    onEdit: (vars: Edit) => editing.mutate(vars),
    onRemove: () => removing.mutate(),
  }
}
