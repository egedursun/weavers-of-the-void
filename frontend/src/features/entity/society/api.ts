import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { loreKeys } from '../api/keys'

export const societyKeys = {
  demography: (id: number) => [...loreKeys.entity(id), 'demography'] as const,
  disease: (id: number) => [...loreKeys.entity(id), 'disease'] as const,
  plan: (id: number) => [...loreKeys.entity(id), 'settlement-plan'] as const,
}

export function useDemography(id: number, enabled = true) {
  return useQuery({
    queryKey: societyKeys.demography(id),
    enabled,
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/demography', {
          params: { path: { entity_id: id } },
        })
      ),
  })
}

export function useDisease(id: number, enabled = true) {
  return useQuery({
    queryKey: societyKeys.disease(id),
    enabled,
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/disease', {
          params: { path: { entity_id: id } },
        })
      ),
  })
}

export function useSettlementPlan(id: number, enabled = true) {
  return useQuery({
    queryKey: societyKeys.plan(id),
    enabled,
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/settlement-plan', {
          params: { path: { entity_id: id } },
        })
      ),
  })
}
