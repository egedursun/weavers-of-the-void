import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

export type SourceTrustOfView = components['schemas']['SourceTrustOfView']
export type SourceTrustView = components['schemas']['SourceTrustView']

export function useSourceTrust(nodeId: number) {
  return useQuery({
    queryKey: [...queryKeys.world.all, 'source-trust-of', nodeId] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/beliefs/trust/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}
