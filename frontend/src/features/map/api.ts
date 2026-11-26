import {
  keepPreviousData,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components, type paths } from '@/api/generated/schema'
import { useMutation } from '@/api/mutation'
import { queryKeys } from '@/api/queryKeys'
import { type WriteTarget } from '@/features/team/writeGate'

export type MapView =
  paths['/api/worlds/{world_id}/map']['get']['responses'][200]['content']['application/json']
export type WorldMap = MapView['geometry']
export type MapNote = MapView['notes'][number]
export type CosmosView = components['schemas']['CosmosView']
export type CosmosWorld = components['schemas']['CosmosWorld']
export type Catalogue = components['schemas']['Catalogue']
export type SonPublic = components['schemas']['SonPublic']
export type LanguageView = components['schemas']['LanguageView']
export type ActionResponse = components['schemas']['ActionResponse']

const STATIC_STALE_MS = Number.POSITIVE_INFINITY

export const mapKeys = {
  all: [...queryKeys.world.all, 'map'] as const,
  view: (worldId: number, epoch: number | null) =>
    [...queryKeys.world.all, 'map', worldId, epoch ?? 'today'] as const,
  deep: (worldId: number, stratum: string, epoch: number | null) =>
    [
      ...queryKeys.world.all,
      'map',
      worldId,
      'deep',
      stratum,
      epoch ?? 'today',
    ] as const,
  cosmos: [...queryKeys.world.all, 'cosmos'] as const,
  sons: [...queryKeys.world.all, 'sons'] as const,
  languages: [...queryKeys.world.all, 'languages'] as const,
  catalogue: ['catalogue'] as const,
}

export function useCosmos() {
  return useQuery({
    queryKey: mapKeys.cosmos,
    queryFn: () => unwrap(api.GET('/api/cosmos')),
  })
}

export function useWorldMap(worldId: number | null, epoch: number | null) {
  return useQuery({
    queryKey: mapKeys.view(worldId ?? 0, epoch),
    queryFn: async (): Promise<MapView> =>
      (await unwrap(
        api.GET('/api/worlds/{world_id}/map', {
          params: {
            path: { world_id: worldId ?? 0 },
            query: epoch === null ? {} : { epoch },
          },
        })
      )) as MapView,
    enabled: worldId !== null,
    placeholderData: keepPreviousData,
  })
}

export type MapStratum = components['schemas']['UndergroundStratum']

export function useDeepMap(
  worldId: number | null,
  stratum: MapStratum | null,
  epoch: number | null
) {
  return useQuery({
    queryKey: mapKeys.deep(worldId ?? 0, stratum ?? 'surface', epoch),
    queryFn: async (): Promise<MapView> =>
      (await unwrap(
        api.GET('/api/worlds/{world_id}/map/deep/{stratum}', {
          params: {
            path: {
              world_id: worldId ?? 0,
              stratum: stratum ?? 'cavern_upper',
            },
            query: epoch === null ? {} : { epoch },
          },
        })
      )) as MapView,
    enabled: worldId !== null && stratum !== null,
    placeholderData: keepPreviousData,
  })
}

export function useCatalogue() {
  return useQuery({
    queryKey: mapKeys.catalogue,
    queryFn: () => unwrap(api.GET('/api/catalogue')),
    staleTime: STATIC_STALE_MS,
  })
}

export function useSons() {
  return useQuery({
    queryKey: mapKeys.sons,
    queryFn: () => unwrap(api.GET('/api/sons')),
  })
}

export function useLanguages() {
  return useQuery({
    queryKey: mapKeys.languages,
    queryFn: () => unwrap(api.GET('/api/languages')),
  })
}

function useMapMutation<TInput, TOutput>(
  writes: readonly WriteTarget[],
  run: (input: TInput) => Promise<TOutput>
) {
  const client = useQueryClient()
  return useMutation({
    writes,
    mutationFn: run,
    onSettled: () => client.invalidateQueries({ queryKey: mapKeys.all }),
  })
}

export type NewMapNote = components['schemas']['PostMapNotesBody']

export function useAddMapNote() {
  return useMapMutation(
    [{ method: 'POST', path: '/api/map-notes' }],
    (note: NewMapNote) => unwrap(api.POST('/api/map-notes', { body: note }))
  )
}

export function useRemoveMapNote() {
  return useMapMutation(
    [{ method: 'DELETE', path: '/api/map-notes/{note_id}' }],
    (noteId: number) =>
      unwrap(
        api.DELETE('/api/map-notes/{note_id}', {
          params: { path: { note_id: noteId } },
        })
      )
  )
}

export function useMoveMarker() {
  return useMapMutation(
    [{ method: 'PUT', path: '/api/entities/{entity_id}/map-position' }],
    (move: { entityId: number; x: number; y: number }) =>
      unwrap(
        api.PUT('/api/entities/{entity_id}/map-position', {
          params: { path: { entity_id: move.entityId } },
          body: { x: move.x, y: move.y },
        })
      )
  )
}

export function useRegenerateMap() {
  return useMapMutation([{ lever: 'world:map' }], (worldId: number) =>
    unwrap(api.POST('/api/actions/world:map', { body: { world_id: worldId } }))
  )
}
