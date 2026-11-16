import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

export type CreatorBondsView = components['schemas']['CreatorBondsView']
export type CovenantView = components['schemas']['CovenantView']

export function useCreatorBonds(nodeId: number) {
  return useQuery({
    queryKey: [...queryKeys.world.all, 'creator-bonds-of', nodeId] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/creator/bonds/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}
