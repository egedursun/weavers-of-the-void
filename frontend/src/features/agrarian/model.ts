import { type ProgressTone } from '@/components/ui/progress'
import { type KpiTone } from '@/components/domain/KpiTile'
import { why } from '@/features/dominion/model'
import { type AgrarianAction, useAgrarianAction } from './api'

type Values = Record<string, number | string | boolean | null>
type Edit = { values: Values; release: string[] }

export const LAND_TYPES = ['region'] as const
export const TOWN_TYPES = ['settlement'] as const
export const HOLDER_TYPES = [
  'mortal',
  'house',
  'polity',
  'faction',
  'settlement',
] as const
export const GIVER_TYPES = ['polity', 'cult'] as const

export function useAgrarianRow<
  E extends AgrarianAction,
  D extends AgrarianAction,
  K extends object,
>(edit: E, remove: D, keys: K, blocked: string | null) {
  const editing = useAgrarianAction(
    edit,
    (vars: Edit) => ({ ...keys, ...vars }) as never,
    'Set so'
  )
  const removing = useAgrarianAction(remove, (_: void) => keys as never, 'Done')
  return {
    busy: why(blocked, editing.isPending, removing.isPending),
    onEdit: (vars: Edit) => editing.mutate(vars),
    onRemove: () => removing.mutate(),
  }
}

export function useAgrarianStep<A extends AgrarianAction, K extends object>(
  action: A,
  keys: K,
  blocked: string | null,
  success: string
) {
  const running = useAgrarianAction(action, (_: void) => keys as never, success)
  return { busy: why(blocked, running.isPending), run: () => running.mutate() }
}

const BARS: Record<KpiTone, ProgressTone> = {
  gold: 'legendary',
  verdigris: 'verdigris',
  info: 'info',
  success: 'success',
  warning: 'warning',
  danger: 'destructive',
  muted: 'muted',
}

export function bar(tone: KpiTone): ProgressTone {
  return BARS[tone]
}
