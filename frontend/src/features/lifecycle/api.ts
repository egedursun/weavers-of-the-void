import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type LifecycleNodeView = Schema['LifecycleNodeView']
export type WorldEndNodeView = Schema['WorldEndNodeView']
export type FossilNodeView = Schema['FossilNodeView']
export type FossilBedView = Schema['FossilBedView']
export type GroundsNodeView = Schema['GroundsNodeView']
export type MuseumCollectionView = Schema['MuseumCollectionView']
export type GardenView = Schema['GardenView']

const keys = {
  life: (nodeId: number) =>
    [...queryKeys.world.all, 'lifecycle-of', nodeId] as const,
  end: (nodeId: number) =>
    [...queryKeys.world.all, 'world-end-of', nodeId] as const,
  fossils: (nodeId: number) =>
    [...queryKeys.world.all, 'fossils-of', nodeId] as const,
  grounds: (nodeId: number) =>
    [...queryKeys.world.all, 'grounds-of', nodeId] as const,
}

export function useNodeLifecycle(nodeId: number) {
  return useQuery({
    queryKey: keys.life(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/lifecycle/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export function useNodeWorldEnd(nodeId: number) {
  return useQuery({
    queryKey: keys.end(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/world-ends/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export function useNodeFossils(nodeId: number) {
  return useQuery({
    queryKey: keys.fossils(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/fossils/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export function useNodeGrounds(nodeId: number) {
  return useQuery({
    queryKey: keys.grounds(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/grounds/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export type EndsAction =
  | 'lifecycle:edit'
  | 'lifecycle:reset'
  | 'lifecycle:destroy'
  | 'lifecycles:run'
  | 'world_end:declare'
  | 'world_end:edit'
  | 'world_end:remove'
  | 'fossil_bed:create'
  | 'fossil_bed:edit'
  | 'fossil_bed:delete'
  | 'fossil_bed:reveal'
  | 'fossils:run'
  | 'museum:found'
  | 'museum:edit'
  | 'museum:delete'
  | 'museum_piece:add'
  | 'museum_piece:edit'
  | 'museum_piece:remove'
  | 'museum_piece:restitute'
  | 'museums:run'
  | 'garden:found'
  | 'garden:edit'
  | 'garden:delete'
  | 'garden:plant'
  | 'garden:uproot'
  | 'gardens:run'

export function useEndsAction<Name extends EndsAction, T>(
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
