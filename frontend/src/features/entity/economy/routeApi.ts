import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { loreKeys } from '../api/keys'

export const routeKeys = {
  production: (id: number) =>
    [...loreKeys.entity(id), 'polity-production'] as const,
  pacts: (id: number) => [...loreKeys.entity(id), 'pacts'] as const,
}

export function usePolityProduction(id: number, enabled = true) {
  return useQuery({
    queryKey: routeKeys.production(id),
    enabled,
    queryFn: () =>
      unwrap(
        api.GET('/api/polities/{polity_id}/production', {
          params: { path: { polity_id: id } },
        })
      ),
  })
}

export function useResourcePacts(id: number, enabled = true) {
  return useQuery({
    queryKey: routeKeys.pacts(id),
    enabled,
    queryFn: () =>
      unwrap(
        api.GET('/api/resources/{resource_id}/pacts', {
          params: { path: { resource_id: id } },
        })
      ),
  })
}
