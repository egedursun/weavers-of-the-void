import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

type Schema = components['schemas']
export type FortuneNodeView = Schema['FortuneNodeView']
export type FortuneSourceView = Schema['FortuneSourceView']

export function useNodeFortune(nodeId: number) {
  return useQuery({
    queryKey: [...queryKeys.world.all, 'fortune-of', nodeId] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/fortune/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}
