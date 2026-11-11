import { useNames } from '@/features/entity/api/queries'

export function useEntityType(nodeId: number): string | null {
  const names = useNames()
  return (
    names.data?.find((entry) => entry.kind === 'entity' && entry.id === nodeId)
      ?.type ?? null
  )
}
