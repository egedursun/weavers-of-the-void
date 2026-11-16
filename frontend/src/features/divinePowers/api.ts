import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

export type DivinePowerView = components['schemas']['DivinePowerView']

export function useNodePowers(nodeId: number) {
  return useQuery({
    queryKey: [...queryKeys.world.all, 'divine-powers-of', nodeId] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/divine/powers/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}
