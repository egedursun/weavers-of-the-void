import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type CraftsNodeView = Schema['CraftsNodeView']

export const craftsKeys = {
  of: (nodeId: number) =>
    [...queryKeys.world.all, 'crafts-of', nodeId] as const,
}

export function useNodeCrafts(nodeId: number) {
  return useQuery({
    queryKey: craftsKeys.of(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/crafts/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export type CraftsAction =
  | 'catch_ground:set'
  | 'catch_ground:edit'
  | 'catch_ground:delete'
  | 'chemical_works:set'
  | 'chemical_works:edit'
  | 'chemical_works:delete'
  | 'insurer:set'
  | 'insurer:edit'
  | 'insurer:delete'
  | 'insurance_policy:create'
  | 'insurance_policy:edit'
  | 'insurance_policy:delete'
  | 'incorporeal_right:create'
  | 'incorporeal_right:edit'
  | 'incorporeal_right:delete'
  | 'assistive_aid:set'
  | 'assistive_aid:edit'
  | 'assistive_aid:delete'
  | 'public_clock:set'
  | 'public_clock:edit'
  | 'public_clock:delete'
  | 'number_system:set'
  | 'number_system:edit'
  | 'number_system:delete'
  | 'number_system:read'
  | 'material_affinity:set'
  | 'material_affinity:edit'
  | 'material_affinity:delete'
  | 'sympathetic_link:create'
  | 'sympathetic_link:edit'
  | 'sympathetic_link:delete'
  | 'emotion_spirit:create'
  | 'emotion_spirit:edit'
  | 'emotion_spirit:delete'
  | 'trades:run'
  | 'learning_aids:run'
  | 'sympathies:run'

export function useCraftsAction<Name extends CraftsAction, T>(
  name: Name,
  toBody: (vars: T) => ActionBody<Name>,
  success?: string
) {
  return useGodAction<T>({
    run: (vars) => postAction(name, toBody(vars)),
    success,
  })
}
