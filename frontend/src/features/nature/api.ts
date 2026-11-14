import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type NatureNodeView = Schema['NatureNodeView']

export const natureKeys = {
  of: (nodeId: number) =>
    [...queryKeys.world.all, 'nature-of', nodeId] as const,
}

export function useNodeNature(nodeId: number) {
  return useQuery({
    queryKey: natureKeys.of(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/nature/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export type NatureAction =
  | 'soil_microbiota:set'
  | 'soil_microbiota:edit'
  | 'soil_microbiota:delete'
  | 'ferment_culture:create'
  | 'ferment_culture:edit'
  | 'ferment_culture:delete'
  | 'species_relation:create'
  | 'species_relation:edit'
  | 'species_relation:delete'
  | 'sense:set'
  | 'sense:edit'
  | 'sense:delete'
  | 'species:edit'
  | 'people:edit'
  | 'plant:edit'
  | 'nature:run'

export function useNatureAction<Name extends NatureAction, T>(
  name: Name,
  toBody: (vars: T) => ActionBody<Name>,
  success?: string
) {
  return useGodAction<T>({
    run: (vars) => postAction(name, toBody(vars)),
    success,
  })
}
