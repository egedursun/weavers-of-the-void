import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type SacredNodeView = Schema['SacredNodeView']

export const sacredKeys = {
  of: (nodeId: number) =>
    [...queryKeys.world.all, 'sacred-of', nodeId] as const,
}

export function useNodeSacred(nodeId: number) {
  return useQuery({
    queryKey: sacredKeys.of(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/sacred/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export type SacredAction =
  | 'genius_locus:create'
  | 'genius_locus:edit'
  | 'genius_locus:delete'
  | 'spirit_office:set'
  | 'spirit_office:edit'
  | 'spirit_office:delete'
  | 'petition:create'
  | 'petition:judge'
  | 'petition:edit'
  | 'petition:delete'
  | 'mystic:create'
  | 'mystic:edit'
  | 'mystic:delete'
  | 'vision:create'
  | 'vision:edit'
  | 'vision:delete'
  | 'millenarian:create'
  | 'millenarian:edit'
  | 'millenarian:delete'
  | 'theodicy:create'
  | 'theodicy:answer'
  | 'theodicy:edit'
  | 'theodicy:delete'
  | 'doctrine_sacrament:set'
  | 'doctrine_sacrament:edit'
  | 'doctrine_sacrament:delete'
  | 'sacrament:create'
  | 'sacrament:edit'
  | 'sacrament:delete'
  | 'doctrine_afterlife:set'
  | 'doctrine_afterlife:align'
  | 'doctrine_afterlife:edit'
  | 'doctrine_afterlife:delete'
  | 'faith_climate:set'
  | 'faith_climate:edit'
  | 'faith_climate:delete'
  | 'divination_system:create'
  | 'divination_system:read'
  | 'divination_system:edit'
  | 'divination_system:delete'
  | 'divination:create'
  | 'divination:edit'
  | 'divination:delete'
  | 'foresight:create'
  | 'foresight:edit'
  | 'foresight:delete'
  | 'forecast_model:create'
  | 'forecast_model:edit'
  | 'forecast_model:delete'
  | 'god_feeding:set'
  | 'god_feeding:edit'
  | 'god_feeding:delete'

export function useSacredAction<Name extends SacredAction, T>(
  name: Name,
  toBody: (vars: T) => ActionBody<Name>,
  success?: string
) {
  return useGodAction<T>({
    writes: [{ lever: name }],
    run: (vars) => postAction(name, toBody(vars)),
    success,
  })
}
