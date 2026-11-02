import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

export type RelationEntry = components['schemas']['RelationEntry']
export type RelationPair = components['schemas']['RelationPair']

export const relationKeys = {
  list: (entityId: number) =>
    [...queryKeys.world.all, 'relations', entityId] as const,
  pair: (entityId: number, otherId: number) =>
    [...queryKeys.world.all, 'relations', entityId, otherId] as const,
}

export function useRelations(entityId: number) {
  return useQuery({
    queryKey: relationKeys.list(entityId),
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/relations', {
          params: { path: { entity_id: entityId } },
        })
      ),
  })
}

export function useRelationPair(entityId: number, otherId: number | null) {
  return useQuery({
    queryKey: relationKeys.pair(entityId, otherId ?? 0),
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/relations/{other_id}', {
          params: { path: { entity_id: entityId, other_id: otherId ?? 0 } },
        })
      ),
    enabled: otherId !== null && otherId !== entityId,
  })
}

function useRefresh() {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.world.all })
    void queryClient.invalidateQueries({ queryKey: queryKeys.ledger.all })
  }
}

export function useSetRelation(entityId: number) {
  const refresh = useRefresh()
  return useMutation({
    mutationFn: (change: { otherId: number; value: number }) =>
      unwrap(
        api.PUT('/api/entities/{entity_id}/relations/{other_id}', {
          params: { path: { entity_id: entityId, other_id: change.otherId } },
          body: { value: change.value },
        })
      ),
    onSettled: refresh,
  })
}

export function useStartFeud(entityId: number) {
  const refresh = useRefresh()
  return useMutation({
    mutationFn: (otherId: number) =>
      unwrap(
        api.POST('/api/entities/{entity_id}/relations/{other_id}/feud', {
          params: { path: { entity_id: entityId, other_id: otherId } },
        })
      ),
    onSettled: refresh,
  })
}

export function useEndFeud(entityId: number) {
  const refresh = useRefresh()
  return useMutation({
    mutationFn: (otherId: number) =>
      unwrap(
        api.DELETE('/api/entities/{entity_id}/relations/{other_id}/feud', {
          params: { path: { entity_id: entityId, other_id: otherId } },
        })
      ),
    onSettled: refresh,
  })
}
