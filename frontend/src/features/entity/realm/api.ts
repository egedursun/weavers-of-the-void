import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { loreKeys } from '../api/keys'

export const realmKeys = {
  link: (id: number) => [...loreKeys.entity(id), 'realm-link'] as const,
  realm: (id: number) => [...loreKeys.entity(id), 'realm'] as const,
  house: (id: number) => [...loreKeys.entity(id), 'house'] as const,
  treaty: (id: number) => [...loreKeys.entity(id), 'treaty'] as const,
  oaths: (id: number) => [...loreKeys.entity(id), 'oaths'] as const,
}

export function useRealmLink(id: number, enabled = true) {
  return useQuery({
    queryKey: realmKeys.link(id),
    enabled,
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/realm', {
          params: { path: { entity_id: id } },
        })
      ),
  })
}

export function useRealm(id: number | null) {
  return useQuery({
    queryKey: realmKeys.realm(id ?? 0),
    enabled: id !== null,
    queryFn: () =>
      unwrap(
        api.GET('/api/polities/{polity_id}', {
          params: { path: { polity_id: id ?? 0 } },
        })
      ),
  })
}

export function useHouse(id: number) {
  return useQuery({
    queryKey: realmKeys.house(id),
    queryFn: () =>
      unwrap(
        api.GET('/api/houses/{house_id}', {
          params: { path: { house_id: id } },
        })
      ),
  })
}

export function useTreaty(id: number) {
  return useQuery({
    queryKey: realmKeys.treaty(id),
    queryFn: () =>
      unwrap(
        api.GET('/api/treaties/{treaty_id}', {
          params: { path: { treaty_id: id } },
        })
      ),
  })
}

export function useOaths(id: number) {
  return useQuery({
    queryKey: realmKeys.oaths(id),
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/oaths', {
          params: { path: { entity_id: id } },
        })
      ),
  })
}
