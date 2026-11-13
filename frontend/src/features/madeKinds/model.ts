import { type ActionBody, type ActionName } from '@/api/actions'
import { why } from '@/features/dominion/model'
import { useLever } from './api'

type Values = Record<string, number | string | boolean | null>
export type Edit = { values: Values; release: string[] }

export const OWNER_TYPES = [
  'people',
  'polity',
  'settlement',
  'faction',
  'house',
  'cult',
] as const
export const HOLDER_TYPES = [
  ...OWNER_TYPES,
  'army',
  'mortal',
  'vessel',
  'structure',
] as const
export const COMMUNITY_TYPES = ['settlement', 'people'] as const

export function numberProblem(
  text: string,
  min: number,
  max: number
): string | null {
  const value = Number(text)
  return text.trim() !== '' &&
    Number.isInteger(value) &&
    value >= min &&
    value <= max
    ? null
    : `Enter a whole number from ${min} to ${max}`
}

export function settled(text: string, current: number): string | null {
  return Number(text) === current ? 'Change the number first' : null
}

export function useKindRow<
  E extends ActionName,
  D extends ActionName,
  K extends object,
>(edit: E, remove: D, keys: K, blocked: string | null) {
  const editing = useLever(
    edit,
    (vars: Edit) => ({ ...keys, ...vars }) as unknown as ActionBody<E>,
    'Set so'
  )
  const removing = useLever(
    remove,
    (_: void) => keys as unknown as ActionBody<D>,
    'Done'
  )
  return {
    busy: why(blocked, editing.isPending, removing.isPending),
    onEdit: (vars: Edit) => editing.mutate(vars),
    onRemove: () => removing.mutate(),
  }
}

export function useKindStep<A extends ActionName, K extends object>(
  action: A,
  keys: K,
  blocked: string | null,
  success: string
) {
  const running = useLever(
    action,
    (_: void) => keys as unknown as ActionBody<A>,
    success
  )
  return { busy: why(blocked, running.isPending), run: () => running.mutate() }
}

export function worst(
  count: number,
  damaged: number,
  disabled: number,
  destroyed: number
): 'sound' | 'damaged' | 'disabled' | 'destroyed' {
  if (count > 0 && destroyed >= count) return 'destroyed'
  if (disabled + destroyed > 0) return 'disabled'
  if (damaged > 0) return 'damaged'
  return 'sound'
}
