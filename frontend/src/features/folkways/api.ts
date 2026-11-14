import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type FolkwaysNodeView = Schema['FolkwaysNodeView']

export const folkwaysKeys = {
  of: (nodeId: number) =>
    [...queryKeys.world.all, 'folkways-of', nodeId] as const,
}

export function useNodeFolkways(nodeId: number) {
  return useQuery({
    queryKey: folkwaysKeys.of(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/folkways/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export type FolkwaysAction =
  | 'diet:set'
  | 'diet:edit'
  | 'diet:delete'
  | 'nutrient_need:set'
  | 'nutrient_need:edit'
  | 'nutrient_need:delete'
  | 'nutrition_score:set'
  | 'nutrition_score:edit'
  | 'nutrition_score:delete'
  | 'nutrition:feed'
  | 'bias_weight:set'
  | 'bias_weight:edit'
  | 'bias_weight:delete'
  | 'bias:read'
  | 'purity:set'
  | 'purity:edit'
  | 'purity:delete'
  | 'purity:cleanse'
  | 'impurity_source:set'
  | 'impurity_source:edit'
  | 'impurity_source:delete'
  | 'purification:set'
  | 'purification:edit'
  | 'purification:delete'
  | 'purity_rank:create'
  | 'purity_rank:edit'
  | 'purity_rank:delete'
  | 'purity_rank:profession'
  | 'mishap:create'
  | 'mishap:edit'
  | 'mishap:delete'
  | 'luck_belief:create'
  | 'luck_belief:edit'
  | 'luck_belief:delete'
  | 'charm:set'
  | 'charm:edit'
  | 'charm:delete'
  | 'accusation:create'
  | 'accusation:edit'
  | 'accusation:delete'
  | 'witch_hunt:create'
  | 'witch_hunt:edit'
  | 'witch_hunt:delete'

export function useFolkwaysAction<Name extends FolkwaysAction, T>(
  name: Name,
  toBody: (vars: T) => ActionBody<Name>,
  success?: string
) {
  return useGodAction<T>({
    run: (vars) => postAction(name, toBody(vars)),
    success,
  })
}
