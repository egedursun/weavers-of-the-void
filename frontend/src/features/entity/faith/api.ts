import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { loreKeys } from '../api/keys'

export type Doctrine = components['schemas']['DoctrineView']
export type TenetKindSpec = components['schemas']['TenetKindSpec']
export type TenetKind = components['schemas']['TenetKind']
export type SoulCard = components['schemas']['SoulCard']
export type RealmOfDead = components['schemas']['RealmOfDeadView']
export type Stratum = components['schemas']['StratumView']
export type Possession = components['schemas']['PossessionView']

export const faithKeys = {
  doctrine: (id: number) => [...loreKeys.entity(id), 'doctrine'] as const,
  soul: (id: number) => [...loreKeys.entity(id), 'soul'] as const,
  afterlife: (id: number) => [...loreKeys.entity(id), 'afterlife'] as const,
  possession: (id: number) => [...loreKeys.entity(id), 'possession'] as const,
  tenets: ['tenets', 'kinds'] as const,
}

export function useDoctrine(id: number) {
  return useQuery({
    queryKey: faithKeys.doctrine(id),
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/doctrine', {
          params: { path: { entity_id: id } },
        })
      ),
  })
}

export function usePossession(id: number) {
  return useQuery({
    queryKey: faithKeys.possession(id),
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/possession', {
          params: { path: { entity_id: id } },
        })
      ),
  })
}

export function useSoul(id: number) {
  return useQuery({
    queryKey: faithKeys.soul(id),
    retry: false,
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/soul', {
          params: { path: { entity_id: id } },
        })
      ),
  })
}

export function useAfterlife(id: number) {
  return useQuery({
    queryKey: faithKeys.afterlife(id),
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/afterlife', {
          params: { path: { entity_id: id } },
        })
      ),
  })
}

export function useTenetKinds() {
  return useQuery({
    queryKey: faithKeys.tenets,
    staleTime: Number.POSITIVE_INFINITY,
    queryFn: () => unwrap(api.GET('/api/tenets/kinds')),
  })
}
