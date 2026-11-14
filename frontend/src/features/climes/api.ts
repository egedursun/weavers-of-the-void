import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type ClimesNodeView = Schema['ClimesNodeView']

export const climesKeys = {
  of: (nodeId: number) =>
    [...queryKeys.world.all, 'climes-of', nodeId] as const,
}

export function useNodeClimes(nodeId: number) {
  return useQuery({
    queryKey: climesKeys.of(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/climes/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export type ClimesAction =
  | 'region_wind:set'
  | 'region_wind:edit'
  | 'region_wind:delete'
  | 'monsoon_season:set'
  | 'monsoon_season:edit'
  | 'monsoon_season:delete'
  | 'climate_oscillation:set'
  | 'climate_oscillation:edit'
  | 'climate_oscillation:delete'
  | 'launch_window:set'
  | 'launch_window:edit'
  | 'launch_window:delete'
  | 'cosmopolitan_culture:create'
  | 'cosmopolitan_culture:edit'
  | 'cosmopolitan_culture:delete'
  | 'cosmopolitan_culture:value'
  | 'cosmopolitan_member:set'
  | 'cosmopolitan_member:edit'
  | 'cosmopolitan_member:delete'
  | 'climes:run'
  | 'crossings:run'

export function useClimesAction<Name extends ClimesAction, T>(
  name: Name,
  toBody: (vars: T) => ActionBody<Name>,
  success?: string
) {
  return useGodAction<T>({
    run: (vars) => postAction(name, toBody(vars)),
    success,
  })
}
