import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { loreKeys } from '../api/keys'

export type EventView = components['schemas']['EventView']
export type HappeningsHere = components['schemas']['HappeningsHereView']
export type LandShape = components['schemas']['LandShapeView']

export const happeningKeys = {
  event: (id: number) => [...loreKeys.entity(id), 'event'] as const,
  here: (id: number) => [...loreKeys.entity(id), 'happenings'] as const,
  land: (id: number) => [...loreKeys.entity(id), 'land-shape'] as const,
}

export function useEventView(id: number) {
  return useQuery({
    queryKey: happeningKeys.event(id),
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/event', {
          params: { path: { entity_id: id } },
        })
      ),
  })
}

export function useHappeningsHere(id: number) {
  return useQuery({
    queryKey: happeningKeys.here(id),
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/happenings', {
          params: { path: { entity_id: id } },
        })
      ),
  })
}

export function useLandShape(id: number) {
  return useQuery({
    queryKey: happeningKeys.land(id),
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/land-shape', {
          params: { path: { entity_id: id } },
        })
      ),
  })
}
