import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { loreKeys } from '../api/keys'

export const structureKeys = {
  host: (id: number) => [...loreKeys.entity(id), 'structures'] as const,
  one: (id: number) => [...loreKeys.entity(id), 'structure'] as const,
  designs: (worldId: number | null) =>
    ['structure-designs', worldId ?? 0] as const,
}

export function useHostStructures(id: number, enabled = true) {
  return useQuery({
    queryKey: structureKeys.host(id),
    enabled,
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/structures', {
          params: { path: { entity_id: id } },
        })
      ),
  })
}

export function useStructure(id: number, enabled = true) {
  return useQuery({
    queryKey: structureKeys.one(id),
    enabled,
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/structure', {
          params: { path: { entity_id: id } },
        })
      ),
  })
}

export function useStructureDesigns(worldId: number | null) {
  return useQuery({
    queryKey: structureKeys.designs(worldId),
    queryFn: () =>
      unwrap(
        api.GET('/api/structure-designs', {
          params: { query: { world_id: worldId ?? undefined } },
        })
      ),
  })
}
