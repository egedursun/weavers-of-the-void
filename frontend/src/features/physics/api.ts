import { type QueryKey, useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { cosmographyKeys } from '@/features/cosmography/api'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type StarPhysicsView = Schema['StarPhysicsView']
export type WorldPhysicsView = Schema['WorldPhysicsView']
export type WorldPhysicsRecord = Schema['WorldPhysicsRecord']
export type HeavensPhysicsView = Schema['HeavensPhysicsView']
export type SystemView = Schema['SystemView']
export type FeatureRecord = Schema['FeatureRecord']
export type ImpactRecord = Schema['ImpactRecord']
export type TerraformRecord = Schema['TerraformRecord']
export type SurveyRecord = Schema['SurveyRecord']
export type OrbitRecord = Schema['OrbitRecord']

export const physicsKeys = {
  all: [...queryKeys.world.all, 'physics'] as const,
  star: (id: number) =>
    [...queryKeys.world.all, 'physics', 'star', id] as const,
  world: (id: number) =>
    [...queryKeys.world.all, 'physics', 'world', id] as const,
  heavens: [...queryKeys.world.all, 'physics', 'heavens'] as const,
  observer: (id: number) =>
    [...queryKeys.world.all, 'physics', 'observer', id] as const,
}

export function useStarPhysics(starId: number) {
  return useQuery({
    queryKey: physicsKeys.star(starId),
    queryFn: () =>
      unwrap(
        api.GET('/api/physics/stars/{star_id}', {
          params: { path: { star_id: starId } },
        })
      ),
  })
}

export function useWorldPhysics(worldId: number) {
  return useQuery({
    queryKey: physicsKeys.world(worldId),
    queryFn: () =>
      unwrap(
        api.GET('/api/physics/worlds/{world_id}', {
          params: { path: { world_id: worldId } },
        })
      ),
  })
}

export function useHeavensPhysics() {
  return useQuery({
    queryKey: physicsKeys.heavens,
    queryFn: () => unwrap(api.GET('/api/physics/heavens')),
  })
}

export function useObserverSurveys(entityId: number) {
  return useQuery({
    queryKey: physicsKeys.observer(entityId),
    queryFn: () =>
      unwrap(
        api.GET('/api/physics/observers/{entity_id}/surveys', {
          params: { path: { entity_id: entityId } },
        })
      ),
  })
}

export type PhysicsAction =
  | 'star_physics:edit'
  | 'star_system:create'
  | 'star_system:edit'
  | 'star_system:delete'
  | 'star_system:move'
  | 'world_physics:edit'
  | 'life_class:edit'
  | 'cosmic_feature:create'
  | 'cosmic_feature:edit'
  | 'cosmic_feature:delete'
  | 'impact:call'
  | 'impact:deflect'
  | 'impact:edit'
  | 'impact:delete'
  | 'terraform:start'
  | 'terraform:edit'
  | 'terraform:stop'
  | 'survey:set'
  | 'survey:forget'

export function usePhysicsAction<Name extends PhysicsAction, T>(
  name: Name,
  toBody: (vars: T) => ActionBody<Name>,
  success?: string,
  also: readonly QueryKey[] = []
) {
  return useGodAction<T>({
    writes: [{ lever: name }],
    run: (vars) => postAction(name, toBody(vars)),
    success,
    invalidate: [physicsKeys.all, cosmographyKeys.view, ...also],
  })
}
