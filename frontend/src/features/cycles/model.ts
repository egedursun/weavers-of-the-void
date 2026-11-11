import { why } from '@/features/dominion/model'
import { useNames } from '@/features/entity/api/queries'
import { type CycleAction, useCycleAction } from './api'

type Values = Record<string, number | string | boolean | null>
export type Edit = { values: Values; release: string[] }

export const SPAN = 100
export const MANY = 1_000_000_000

export const GOD_KINDS = ['son', 'foreign_god'] as const
export const COMMUNITY_TYPES = [
  'settlement',
  'people',
  'faction',
  'cult',
] as const
export const LINE_TYPES = ['house', 'mortal'] as const
export const GIVING_TYPES = [
  'mortal',
  'house',
  'polity',
  'settlement',
  'people',
  'faction',
  'cult',
] as const
export const STOP_TYPES = ['settlement', 'people', 'polity'] as const

export function clamp(text: string, max = SPAN, min = 0) {
  const value = Number(text)
  return Number.isNaN(value)
    ? min
    : Math.max(min, Math.min(max, Math.round(value)))
}

export function useNodeKind(nodeId: number): string | null {
  const names = useNames()
  const entry = names.data?.find((item) => item.id === nodeId)
  if (!entry) return null
  return entry.kind === 'entity' ? entry.type : entry.kind
}

export function useRow<
  E extends CycleAction,
  D extends CycleAction,
  K extends object,
>(edit: E, remove: D, keys: K, blocked: string | null) {
  const editing = useCycleAction(
    edit,
    (vars: Edit) => ({ ...keys, ...vars }) as never,
    'Set so'
  )
  const removing = useCycleAction(remove, (_: void) => keys as never, 'Done')
  return {
    busy: why(blocked, editing.isPending, removing.isPending),
    onEdit: (vars: Edit) => editing.mutate(vars),
    onRemove: () => removing.mutate(),
  }
}

export function useStep<A extends CycleAction, K extends object>(
  action: A,
  keys: K,
  blocked: string | null,
  success: string
) {
  const running = useCycleAction(action, (_: void) => keys as never, success)
  return { busy: why(blocked, running.isPending), run: () => running.mutate() }
}

export function signed(value: number) {
  return `${value > 0 ? '+' : ''}${value}`
}
