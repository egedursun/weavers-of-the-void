import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

export type PantheonOfView = components['schemas']['PantheonOfView']
export type PantheonTieView = components['schemas']['PantheonTieView']
export type SyncretismView = components['schemas']['SyncretismView']

export function usePantheonOf(nodeId: number) {
  return useQuery({
    queryKey: [...queryKeys.world.all, 'pantheon-of', nodeId] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/pantheon/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}
