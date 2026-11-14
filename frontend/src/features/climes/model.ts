import { why } from '@/features/dominion/model'
import { type ClimesAction, useClimesAction } from './api'

type Values = Record<string, number | string | boolean | null>
type Edit = { values: Values; release: string[] }

export const SPAN = 100
export const DOUBLE_SPAN = 200
export const OCTANT_MAX = 7
export const SYNODIC_MAX = 100
export const COMMUNITY_TYPES = [
  'settlement',
  'people',
  'faction',
  'cult',
] as const
export const LANGUAGE_TYPES = ['language'] as const
export const REGION_TYPES = ['region'] as const
export const WORLD_KINDS = ['world'] as const

export function useClimesRow<
  E extends ClimesAction,
  D extends ClimesAction,
  K extends object,
>(edit: E, remove: D, keys: K, blocked: string | null) {
  const editing = useClimesAction(
    edit,
    (vars: Edit) => ({ ...keys, ...vars }) as never,
    'Set so'
  )
  const removing = useClimesAction(remove, (_: void) => keys as never, 'Done')
  return {
    busy: why(blocked, editing.isPending, removing.isPending),
    onEdit: (vars: Edit) => editing.mutate(vars),
    onRemove: () => removing.mutate(),
  }
}

export function useClimesStep<A extends ClimesAction>(
  action: A,
  blocked: string | null,
  success: string
) {
  const running = useClimesAction(action, (_: void) => ({}) as never, success)
  return { busy: why(blocked, running.isPending), run: () => running.mutate() }
}

export function epochsToWindow(
  synodic: number,
  offset: number,
  epoch: number
): number {
  const span = Math.max(1, synodic)
  return (span - ((epoch + offset) % span)) % span
}
