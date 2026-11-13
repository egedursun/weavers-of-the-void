import { useQuery } from '@tanstack/react-query'
import { type ActionBody, type ActionName, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type ThingKinds = Schema['ThingKindsView']
export type VehicleType = Schema['VehicleTypeView']
export type UnitType = Schema['UnitTypeView']
export type EquipmentModel = Schema['EquipmentModelView']
export type Dish = Schema['DishView']
export type BuildingType = Schema['BuildingTypeView']
export type VehicleGroup = Schema['VehicleGroupView']

export const kindKeys = {
  world: (worldId: number) =>
    [...queryKeys.world.all, 'made-kinds', worldId] as const,
  thing: (nodeId: number) =>
    [...queryKeys.world.all, 'made-kinds-of', nodeId] as const,
  frames: () => ['vehicle-frames'] as const,
}

function worldQuery(worldId: number) {
  return {
    queryKey: kindKeys.world(worldId),
    queryFn: () =>
      unwrap(
        api.GET('/api/made-kinds/world/{world_id}', {
          params: { path: { world_id: worldId } },
        })
      ),
  }
}

export function useWorldKinds(worldId: number | null) {
  return useQuery({ ...worldQuery(worldId ?? 0), enabled: worldId !== null })
}

export function useThingKinds(nodeId: number) {
  return useQuery({
    queryKey: kindKeys.thing(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/made-kinds/thing/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export function useFrames() {
  return useQuery({
    queryKey: kindKeys.frames(),
    staleTime: Number.POSITIVE_INFINITY,
    queryFn: () => unwrap(api.GET('/api/vehicles/frames')),
  })
}

export function useLever<Name extends ActionName, Vars = void>(
  name: Name,
  body: (vars: Vars) => ActionBody<Name>,
  success: string
) {
  return useGodAction({
    run: (vars: Vars) => postAction(name, body(vars)),
    success,
  })
}
