import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type WorldViewNodeView = Schema['WorldViewNodeView']
export type WorldNatureView = Schema['WorldNatureView']

export const worldViewKeys = {
  of: (nodeId: number) =>
    [...queryKeys.world.all, 'world-view-of', nodeId] as const,
}

export function useNodeWorldView(nodeId: number) {
  return useQuery({
    queryKey: worldViewKeys.of(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/world-views/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export type WorldViewAction =
  'world_view:edit' | 'world_view:reset' | 'world_views:run'

export function useWorldViewAction<Name extends WorldViewAction, T>(
  name: Name,
  toBody: (vars: T) => ActionBody<Name>,
  success?: string
) {
  return useGodAction<T>({
    run: (vars) => postAction(name, toBody(vars)),
    success,
  })
}
