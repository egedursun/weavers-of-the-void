import { useCallback, useMemo } from 'react'
import { useNames } from '@/features/entity/api/queries'

export function useNameOf(): (id: number) => string | undefined {
  const names = useNames()
  const byId = useMemo(
    () => new Map((names.data ?? []).map((entry) => [entry.id, entry.name])),
    [names.data]
  )
  return useCallback((id: number) => byId.get(id), [byId])
}
