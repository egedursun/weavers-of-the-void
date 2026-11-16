import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

export type TechLevelView = components['schemas']['TechLevelView']

export function useNodeTechnology(nodeId: number) {
  return useQuery({
    queryKey: [...queryKeys.world.all, 'technology-of', nodeId] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/technology/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}
