import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type CollectiveView = Schema['CollectiveView']
export type AccountView = Schema['AccountView']
export type StoryletView = Schema['StoryletView']
export type DesignView = Schema['MachineDesignView']
export type ArmsView = Schema['ArmsView']
export type StoryletSpecView = Schema['StoryletSpecView']

export const collectiveKeys = {
  of: (nodeId: number) =>
    [...queryKeys.world.all, 'collective-of', nodeId] as const,
  storylets: () => [...queryKeys.world.all, 'storylet-catalog'] as const,
}

export function useNodeCollective(nodeId: number) {
  return useQuery({
    queryKey: collectiveKeys.of(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/collective/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export function useStoryletCatalog() {
  return useQuery({
    queryKey: collectiveKeys.storylets(),
    queryFn: () => unwrap(api.GET('/api/collective/storylets')),
    staleTime: Infinity,
  })
}

export type CollectiveAction =
  | 'crowd_mood:set'
  | 'crowd_mood:edit'
  | 'crowd_mood:delete'
  | 'cascade:spark'
  | 'cascade:delete'
  | 'mob:raise'
  | 'mob:edit'
  | 'mob:disperse'
  | 'mob:delete'
  | 'popular_movement:found'
  | 'popular_movement:edit'
  | 'popular_movement:delete'
  | 'account:write'
  | 'account:edit'
  | 'account:revise'
  | 'account:expose'
  | 'account:delete'
  | 'account_stance:set'
  | 'account_stance:delete'
  | 'memory_strike:set'
  | 'memory_strike:edit'
  | 'memory_strike:delete'
  | 'founding_myth:set'
  | 'founding_myth:edit'
  | 'founding_myth:debunk'
  | 'founding_myth:delete'
  | 'commemoration:set'
  | 'commemoration:edit'
  | 'commemoration:relive'
  | 'commemoration:delete'
  | 'lost_land:set'
  | 'lost_land:edit'
  | 'lost_land:delete'
  | 'storylet:open'
  | 'storylet:edit'
  | 'storylet:choose'
  | 'storylet:delete'
  | 'social_norm:set'
  | 'social_norm:edit'
  | 'social_norm:delete'
  | 'norm_change:delete'
  | 'learning_bias:set'
  | 'learning_bias:edit'
  | 'learning_bias:delete'
  | 'learning_event:delete'
  | 'generation:set'
  | 'generation:shape'
  | 'generation:edit'
  | 'generation:delete'
  | 'diaspora:set'
  | 'diaspora:edit'
  | 'diaspora:delete'
  | 'transition:set'
  | 'transition:edit'
  | 'transition:delete'
  | 'sex_ratio:set'
  | 'sex_ratio:edit'
  | 'sex_ratio:delete'
  | 'role_norm:set'
  | 'role_norm:edit'
  | 'role_norm:delete'
  | 'dating_system:set'
  | 'dating_system:edit'
  | 'dating_system:delete'
  | 'arms:set'
  | 'arms:edit'
  | 'arms:quarter'
  | 'arms:difference'
  | 'arms:delete'
  | 'design:draw'
  | 'design:edit'
  | 'design:refit'
  | 'design:delete'
  | 'design_component:set'
  | 'design_component:delete'
  | 'design:fit'
  | 'component_wear:set'
  | 'component_wear:edit'
  | 'component_wear:delete'

export function useCollectiveAction<Name extends CollectiveAction, T>(
  name: Name,
  toBody: (vars: T) => ActionBody<Name>,
  success?: string
) {
  return useGodAction<T>({
    run: (vars) => postAction(name, toBody(vars)),
    success,
  })
}
