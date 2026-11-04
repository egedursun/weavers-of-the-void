import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { loreKeys } from '../api/keys'

export const depthKeys = {
  depth: (id: number) => [...loreKeys.entity(id), 'society-depth'] as const,
}

export function useSocietyDepth(id: number, enabled = true) {
  return useQuery({
    queryKey: depthKeys.depth(id),
    enabled,
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/society-depth', {
          params: { path: { entity_id: id } },
        })
      ),
  })
}
