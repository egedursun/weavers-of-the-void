import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

export type WorldWiki = components['schemas']['WorldWiki']
export type StarWiki = components['schemas']['StarWiki']
export type CelestialDepth = components['schemas']['EntityDepth']

export const celestialKeys = {
  world: (worldId: number) =>
    [...queryKeys.world.all, 'wiki', 'world', worldId] as const,
  star: (starId: number) =>
    [...queryKeys.world.all, 'wiki', 'star', starId] as const,
}

export function useWorldWiki(worldId: number) {
  return useQuery({
    queryKey: celestialKeys.world(worldId),
    queryFn: () =>
      unwrap(
        api.GET('/api/worlds/{world_id}/wiki', {
          params: { path: { world_id: worldId } },
        })
      ),
    enabled: worldId > 0,
  })
}

export function useStarWiki(starId: number) {
  return useQuery({
    queryKey: celestialKeys.star(starId),
    queryFn: () =>
      unwrap(
        api.GET('/api/stars/{star_id}/wiki', {
          params: { path: { star_id: starId } },
        })
      ),
    enabled: starId > 0,
  })
}
