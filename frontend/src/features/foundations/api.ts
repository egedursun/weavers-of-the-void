import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

export type GoldenAge = components['schemas']['GoldenAgeView']
export type Anchorage = components['schemas']['AnchorageView']
export type Dedication = components['schemas']['DedicationView']
export type HoldKind = components['schemas']['HoldKind']

export const foundationKeys = {
  goldenAge: (worldId: number) =>
    [...queryKeys.world.all, 'golden-age', worldId] as const,
  anchorage: (sonId: number) =>
    [...queryKeys.world.all, 'anchorage', sonId] as const,
  dedication: (entityId: number) =>
    [...queryKeys.world.all, 'dedication', entityId] as const,
}

export function useGoldenAge(worldId: number) {
  return useQuery({
    queryKey: foundationKeys.goldenAge(worldId),
    queryFn: () =>
      unwrap(
        api.GET('/api/worlds/{world_id}/golden-age', {
          params: { path: { world_id: worldId } },
        })
      ),
  })
}

export function useAnchorage(sonId: number) {
  return useQuery({
    queryKey: foundationKeys.anchorage(sonId),
    queryFn: () =>
      unwrap(
        api.GET('/api/sons/{son_id}/anchorage', {
          params: { path: { son_id: sonId } },
        })
      ),
  })
}

export function useDedication(entityId: number) {
  return useQuery({
    queryKey: foundationKeys.dedication(entityId),
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/dedication', {
          params: { path: { entity_id: entityId } },
        })
      ),
  })
}

export function holdFoundation(kind: HoldKind, nodeId: number, held: boolean) {
  return unwrap(
    api.POST('/api/actions/foundation:hold', {
      body: { kind, node_id: nodeId, held },
    })
  )
}
