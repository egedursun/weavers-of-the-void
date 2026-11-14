import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type TalesNodeView = Schema['TalesNodeView']

export const talesKeys = {
  of: (nodeId: number) => [...queryKeys.world.all, 'tales-of', nodeId] as const,
}

export function useNodeTales(nodeId: number) {
  return useQuery({
    queryKey: talesKeys.of(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/tales/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export type TalesAction =
  | 'formation:read'
  | 'formation:reshape'
  | 'formation:edit'
  | 'formation:delete'
  | 'irregular_season:create'
  | 'irregular_season:forecast'
  | 'irregular_season:edit'
  | 'irregular_season:delete'
  | 'winter_forecast:set'
  | 'winter_forecast:edit'
  | 'winter_forecast:delete'
  | 'eco_transformation:set'
  | 'eco_transformation:edit'
  | 'eco_transformation:delete'
  | 'age:cycle'
  | 'age:turn'
  | 'age:edit'
  | 'age:delete'
  | 'age_echo:create'
  | 'age_echo:edit'
  | 'age_echo:delete'
  | 'arc:create'
  | 'arc:press'
  | 'arc:edit'
  | 'arc:delete'
  | 'arc_figure:create'
  | 'arc_figure:edit'
  | 'arc_figure:delete'
  | 'arc_beat:create'
  | 'arc_beat:edit'
  | 'arc_beat:delete'
  | 'setup:create'
  | 'setup:edit'
  | 'setup:delete'

export function useTalesAction<Name extends TalesAction, T>(
  name: Name,
  toBody: (vars: T) => ActionBody<Name>,
  success?: string
) {
  return useGodAction<T>({
    run: (vars) => postAction(name, toBody(vars)),
    success,
  })
}
