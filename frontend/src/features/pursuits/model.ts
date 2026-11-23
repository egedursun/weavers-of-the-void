import { why } from '@/features/dominion/model'
import { type PursuitsAction, usePursuitsAction } from './api'

type Values = Record<string, number | string | boolean | null>
type Edit = { values: Values; release: string[] }

export const SPAN = 100
export const MANY = 1_000_000
export const PRIORITIES = 100
export const MORTAL_TYPES = ['mortal'] as const
export const TOWN_TYPES = ['settlement'] as const
export const REALM_TYPES = ['polity'] as const
export const PEOPLE_TYPES = ['people'] as const
export const ART_TYPES = ['artwork'] as const
export const FORM_TYPES = ['art_form'] as const
export const FACTION_TYPES = ['faction'] as const
export const BEAST_TYPES = ['beast'] as const
export const SPIRIT_TYPES = ['spirit'] as const
export const STRUCTURE_TYPES = ['structure'] as const
export const SKY_TYPES = ['celestial'] as const
export const FAIR_TYPES = ['settlement', 'place', 'structure'] as const
export const HOLDER_TYPES = [
  'mortal',
  'polity',
  'cult',
  'faction',
  'settlement',
] as const
export const FORGED_TYPES = [
  'artwork',
  'item',
  'title',
  'law',
  'treaty',
  'settlement',
  'polity',
] as const
export const OWNER_TYPES = ['beast', 'army'] as const
export const FIXER_TYPES = [
  'mortal',
  'polity',
  'faction',
  'settlement',
] as const
export const TOKEN_TYPES = ['item', 'polity'] as const
export const GOD_KINDS = ['son', 'foreign_god'] as const
export const LINE_TYPES = ['settlement', 'cult'] as const
export const ENTITY_KINDS = ['entity'] as const

export function usePursuitsRow<
  E extends PursuitsAction,
  D extends PursuitsAction,
  K extends object,
>(edit: E, remove: D, keys: K, blocked: string | null) {
  const editing = usePursuitsAction(
    edit,
    (vars: Edit) => ({ ...keys, ...vars }) as never,
    'Set so'
  )
  const removing = usePursuitsAction(remove, (_: void) => keys as never, 'Done')
  return {
    busy: why(blocked, editing.isPending, removing.isPending),
    onEdit: (vars: Edit) => editing.mutate(vars),
    onRemove: () => removing.mutate(),
  }
}

export function usePursuitsStep<A extends PursuitsAction, K extends object>(
  action: A,
  keys: K,
  blocked: string | null,
  success: string
) {
  const running = usePursuitsAction(action, (_: void) => keys as never, success)
  return { busy: why(blocked, running.isPending), run: () => running.mutate() }
}

export function withNone(
  record: Record<string, string>,
  none: string
): Record<string, string> {
  return { none, ...record }
}

export const MAYBE: Record<string, string> = {
  none: 'Not settled yet',
  true: 'Won',
  false: 'Lost',
}
