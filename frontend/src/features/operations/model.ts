import { why } from '@/features/dominion/model'
import { type OperationsAction, useOperationsAction } from './api'

type Values = Record<string, number | string | boolean | null>
type Edit = { values: Values; release: string[] }

export const OWNER_TYPES = [
  'polity',
  'settlement',
  'people',
  'faction',
  'house',
] as const
export const MORTAL_TYPES = ['mortal'] as const
export const REGION_TYPES = ['region'] as const
export const STRUCTURE_TYPES = ['structure'] as const
export const SPAN = 100
export const STRESS_SPAN = 200
export const MANY = 1_000_000_000

export function useOpsRow<
  E extends OperationsAction,
  D extends OperationsAction,
  K extends object,
>(edit: E, remove: D, keys: K, blocked: string | null) {
  const editing = useOperationsAction(
    edit,
    (vars: Edit) => ({ ...keys, ...vars }) as never,
    'Set so'
  )
  const removing = useOperationsAction(
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

export function useOpsStep<A extends OperationsAction, K extends object>(
  action: A,
  keys: K,
  blocked: string | null,
  success: string
) {
  const running = useOperationsAction(
    action,
    (_: void) => keys as never,
    success
  )
  return { busy: why(blocked, running.isPending), run: () => running.mutate() }
}

export function share(part: number, whole: number): number {
  return whole > 0 ? Math.round((part * SPAN) / whole) : 0
}

export function heading(value: number, compass: readonly string[]): string {
  return compass[((value % compass.length) + compass.length) % compass.length]
}
