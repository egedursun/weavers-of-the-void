import { useMemo } from 'react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { useNames } from '@/features/entity/api/queries'
import { useGodAction } from '@/features/pantheon/godAction'
import { depthKeys } from './depth'

export type Values = Record<string, unknown>

export function useRecordActions(
  kind: string,
  recordId: number,
  scope: number | null,
  extra: unknown[][] = []
) {
  const invalidate = [
    depthKeys.records(kind, scope) as unknown as unknown[],
    ['military'],
    ['wars'],
    ['feuds'],
    ['vessels'],
    ...extra,
  ]
  const save = useGodAction<{ values: Values; hold: boolean }>({
    run: ({ values, hold }) =>
      unwrap(
        api.POST('/api/actions/military:edit', {
          body: { kind, record_id: recordId, values, hold },
        })
      ),
    invalidate,
  })
  const release = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/military:release', {
          body: { kind, record_id: recordId, columns: [] },
        })
      ),
    invalidate,
  })
  const remove = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/military:delete', {
          body: { kind, record_id: recordId },
        })
      ),
    invalidate,
  })
  return { save, release, remove }
}

export function useRecordCreate(
  kind: string,
  scope: number | null,
  extra: unknown[][] = []
) {
  return useGodAction<Values>({
    run: (values) =>
      unwrap(
        api.POST('/api/actions/military:create', { body: { kind, values } })
      ),
    invalidate: [
      depthKeys.records(kind, scope) as unknown as unknown[],
      ['military'],
      ['wars'],
      ['feuds'],
      ['vessels'],
      ...extra,
    ],
  })
}

export function useNameMap(): Record<number, string> {
  const names = useNames()
  return useMemo(
    () =>
      Object.fromEntries(
        (names.data ?? [])
          .filter((entry) => entry.kind === 'entity')
          .map((entry) => [entry.id, entry.name])
      ),
    [names.data]
  )
}

export function numbersOf(draft: Values, keys: readonly string[]): Values {
  return Object.fromEntries(
    Object.entries(draft).map(([key, value]) => [
      key,
      keys.includes(key) ? Math.round(Number(value) || 0) : value,
    ])
  )
}
