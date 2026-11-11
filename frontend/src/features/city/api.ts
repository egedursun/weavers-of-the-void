import { useQueries, useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

type Schema = components['schemas']
export type CityScene = Schema['CitySceneView']
export type CityDistrict = Schema['CityDistrictView']
export type CityBuilding = Schema['CityBuildingView']
export type LandScene = Schema['LandSceneView']
export type StructureTypes = Schema['StructureTypesView']
export type StructureType = Schema['StructureTypeView']

export const cityKeys = {
  city: (id: number) => [...queryKeys.world.all, 'city-scene', id] as const,
  land: (id: number) => [...queryKeys.world.all, 'land-scene', id] as const,
  types: (id: number) =>
    [...queryKeys.world.all, 'structure-types', id] as const,
}

export function useCityScene(settlementId: number) {
  return useQuery({
    queryKey: cityKeys.city(settlementId),
    queryFn: () =>
      unwrap(
        api.GET('/api/city/{settlement_id}', {
          params: { path: { settlement_id: settlementId } },
        })
      ),
  })
}

export function useLandScene(regionId: number) {
  return useQuery({
    queryKey: cityKeys.land(regionId),
    queryFn: () =>
      unwrap(
        api.GET('/api/land/{region_id}', {
          params: { path: { region_id: regionId } },
        })
      ),
  })
}

function typesQuery(worldId: number) {
  return {
    queryKey: cityKeys.types(worldId),
    queryFn: () =>
      unwrap(
        api.GET('/api/structure-types/{world_id}', {
          params: { path: { world_id: worldId } },
        })
      ),
  }
}

export function useStructureTypes(worldId: number) {
  return useQuery(typesQuery(worldId))
}

function byWorld(
  results: { data?: StructureTypes }[]
): ReadonlyMap<number, StructureTypes> {
  return new Map(
    results.flatMap((result) =>
      result.data ? [[result.data.world_id, result.data] as const] : []
    )
  )
}

export function useWorldsStructureTypes(
  worldIds: number[]
): ReadonlyMap<number, StructureTypes> {
  return useQueries({ queries: worldIds.map(typesQuery), combine: byWorld })
}
