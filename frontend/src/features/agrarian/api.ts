import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type AgrarianNodeView = Schema['AgrarianNodeView']
export type CosmosAgrarianView = Schema['CosmosAgrarianView']

export const agrarianKeys = {
  of: (nodeId: number) =>
    [...queryKeys.world.all, 'agrarian-of', nodeId] as const,
  cosmos: () => [...queryKeys.world.all, 'agrarian-cosmos'] as const,
}

export function useNodeAgrarian(nodeId: number) {
  return useQuery({
    queryKey: agrarianKeys.of(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/agrarian/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export function useCosmosAgrarian() {
  return useQuery({
    queryKey: agrarianKeys.cosmos(),
    queryFn: () => unwrap(api.GET('/api/agrarian/cosmos')),
  })
}

export type AgrarianAction =
  | 'land_ring:set'
  | 'land_ring:edit'
  | 'land_ring:delete'
  | 'central_place:set'
  | 'central_place:edit'
  | 'central_place:delete'
  | 'soil_nutrient:set'
  | 'soil_nutrient:edit'
  | 'soil_nutrient:delete'
  | 'intensification:set'
  | 'intensification:edit'
  | 'intensification:delete'
  | 'perennial:plant'
  | 'perennial:edit'
  | 'perennial:fell'
  | 'perennial:delete'
  | 'commons:create'
  | 'commons:edit'
  | 'commons:enclose'
  | 'commons:delete'
  | 'game_reserve:declare'
  | 'game_reserve:edit'
  | 'game_reserve:delete'
  | 'famine_lore:set'
  | 'famine_lore:edit'
  | 'famine_lore:delete'
  | 'preparedness:build'
  | 'preparedness:edit'
  | 'preparedness:delete'
  | 'relief:send'
  | 'relief:edit'
  | 'relief:delete'
  | 'reconstruction:begin'
  | 'reconstruction:edit'
  | 'reconstruction:finish'
  | 'reconstruction:delete'
  | 'keystone:designate'
  | 'keystone:edit'
  | 'keystone:delete'
  | 'brand:found'
  | 'brand:edit'
  | 'brand:delete'

export function useAgrarianAction<Name extends AgrarianAction, T>(
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
