import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { useGodAction } from '@/features/pantheon/godAction'

export const WORKING = 'Working…'
export const PERCENT = 100
export const LORE_KINDS = [
  'language',
  'legend',
  'tradition',
  'ideology',
  'rite',
  'prophecy',
  'item',
  'artwork',
] as const
export type LoreKind = (typeof LORE_KINDS)[number]

export function isLoreKind(kind: string): kind is LoreKind {
  return (LORE_KINDS as readonly string[]).includes(kind)
}

export function busyOf(
  blocked: string | null,
  ...pending: boolean[]
): string | null {
  return blocked ?? (pending.some(Boolean) ? WORKING : null)
}

export function useLoreEdit(entityId: number) {
  return useGodAction<{ values: Record<string, unknown>; release?: string[] }>({
    run: ({ values, release }) =>
      unwrap(
        api.POST('/api/actions/lore:edit', {
          body: {
            entity_id: entityId,
            values: values as Record<string, never>,
            release: release ?? [],
          },
        })
      ),
  })
}
