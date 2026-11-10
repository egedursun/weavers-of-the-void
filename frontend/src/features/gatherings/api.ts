import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type GatheringView = Schema['GatheringView']
export type GuestView = Schema['GuestView']
export type CollectionView = Schema['CollectionView']
export type HistoryDetail = Schema['HistoryDetail']
export type HistoryPage = Schema['HistoryPage']
export type MemberView = Schema['HistoryMemberView']
export type StorytellerView = Schema['StorytellerView']
export type TensionPoint = Schema['TensionPoint']
export type SiteView = Schema['SiteView']
export type RoomView = Schema['RoomView']
export type ContentView = Schema['ContentView']
export type DigView = Schema['DigView']
export type StageView = Schema['DigStageView']
export type FeatureView = Schema['FeatureView']
export type HolderView = Schema['HolderView']
export type CollectionKind = Schema['CollectionKind']
export type CollectionRole = Schema['CollectionRole']

export type HistoryFilter = {
  kind?: CollectionKind
  world_id?: number
  node_id?: number
  place_id?: number
  offset?: number
  limit?: number
}

export const gatheringKeys = {
  of: (nodeId: number) =>
    [...queryKeys.world.all, 'gatherings-of', nodeId] as const,
  histories: (filter: HistoryFilter) =>
    [...queryKeys.world.all, 'histories', filter] as const,
  lifeLog: (nodeId: number) =>
    [...queryKeys.world.all, 'histories-of', nodeId] as const,
  history: (collectionId: number) =>
    [...queryKeys.world.all, 'history', collectionId] as const,
  storyteller: (worldId: number) =>
    [...queryKeys.world.all, 'storyteller', worldId] as const,
  site: (entityId: number) =>
    [...queryKeys.world.all, 'site', entityId] as const,
}

export function useNodeGatherings(nodeId: number) {
  return useQuery({
    queryKey: gatheringKeys.of(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/gatherings/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export function useHistories(filter: HistoryFilter, enabled = true) {
  return useQuery({
    queryKey: gatheringKeys.histories(filter),
    enabled,
    queryFn: () =>
      unwrap(api.GET('/api/histories', { params: { query: filter } })),
  })
}

export function useLifeLog(nodeId: number) {
  return useQuery({
    queryKey: gatheringKeys.lifeLog(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/histories/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export function useHistory(collectionId: number | null) {
  return useQuery({
    queryKey: gatheringKeys.history(collectionId ?? 0),
    enabled: collectionId !== null,
    queryFn: () =>
      unwrap(
        api.GET('/api/histories/{collection_id}', {
          params: { path: { collection_id: collectionId ?? 0 } },
        })
      ),
  })
}

export function useStoryteller(worldId: number) {
  return useQuery({
    queryKey: gatheringKeys.storyteller(worldId),
    queryFn: () =>
      unwrap(
        api.GET('/api/storyteller/{world_id}', {
          params: { path: { world_id: worldId } },
        })
      ),
  })
}

export function useSite(entityId: number) {
  return useQuery({
    queryKey: gatheringKeys.site(entityId),
    queryFn: () =>
      unwrap(
        api.GET('/api/sites/{entity_id}', {
          params: { path: { entity_id: entityId } },
        })
      ),
  })
}

export type GatheringAction =
  | 'gathering:convene'
  | 'gathering:hold'
  | 'gathering:edit'
  | 'gathering:delete'
  | 'gathering_guest:set'
  | 'gathering_guest:remove'
  | 'collection:create'
  | 'collection:edit'
  | 'collection:delete'
  | 'collection:place'
  | 'collection_member:set'
  | 'collection_member:remove'
  | 'storyteller:set'
  | 'site_room:create'
  | 'site_room:edit'
  | 'site_room:delete'
  | 'room_content:add'
  | 'room_content:remove'
  | 'site:delve'
  | 'site_holder:set'
  | 'site_holder:delete'
  | 'excavation:begin'
  | 'excavation:edit'
  | 'excavation:advance'
  | 'excavation:delete'
  | 'excavation_stage:edit'
  | 'battlefield_feature:create'
  | 'battlefield_feature:edit'
  | 'battlefield_feature:delete'

export function useGatheringAction<Name extends GatheringAction, T>(
  name: Name,
  toBody: (vars: T) => ActionBody<Name>,
  success?: string
) {
  return useGodAction<T>({
    run: (vars) => postAction(name, toBody(vars)),
    success,
  })
}
