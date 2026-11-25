import { why } from '@/features/dominion/model'
import { useEraAction } from './api'

type Values = Record<string, number | string | boolean | null>
type Edit = { values: Values; release: string[] }

export const SPAN = 100
export const MANY = 1_000_000
export const REALM_TYPES = ['polity'] as const

export function useProgrammeRow(recordId: number, blocked: string | null) {
  const editing = useEraAction(
    'tech_programme:edit',
    (vars: Edit) => ({ record_id: recordId, ...vars }),
    'The programme is set so'
  )
  const removing = useEraAction(
    'tech_programme:delete',
    (_: void) => ({ record_id: recordId }),
    'The programme is ended'
  )
  return {
    busy:
      editing.blockedReason ??
      removing.blockedReason ??
      why(blocked, editing.isPending, removing.isPending),
    onEdit: (vars: Edit) => editing.mutate(vars),
    onRemove: () => removing.mutate(),
  }
}

export function signed(value: number, unit: string) {
  return `${value > 0 ? '+' : ''}${value}${unit}`
}
