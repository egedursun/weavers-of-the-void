import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

type Schema = components['schemas']
export type LivingNodeView = Schema['LivingNodeView']
export type LivingLineView = Schema['LivingLineView']
export type SymbiontView = Schema['SymbiontView']
export type GeneBankView = Schema['GeneBankView']

export function useNodeLiving(nodeId: number) {
  return useQuery({
    queryKey: [...queryKeys.world.all, 'living-of', nodeId] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/living/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}
