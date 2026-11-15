import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type MeansNodeView = Schema['MeansNodeView']

export const meansKeys = {
  of: (nodeId: number) => [...queryKeys.world.all, 'means-of', nodeId] as const,
}

export function useNodeMeans(nodeId: number) {
  return useQuery({
    queryKey: meansKeys.of(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/means/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export type MeansAction =
  | 'writing_custom:set'
  | 'writing_custom:edit'
  | 'writing_custom:delete'
  | 'written_work:set'
  | 'written_work:edit'
  | 'written_work:delete'
  | 'security:set'
  | 'security:edit'
  | 'security:delete'
  | 'water_lift:set'
  | 'water_lift:edit'
  | 'water_lift:delete'
  | 'navigation_kit:set'
  | 'navigation_kit:edit'
  | 'navigation_kit:delete'
  | 'container_stock:set'
  | 'container_stock:edit'
  | 'container_stock:delete'
  | 'node_material:set'
  | 'means:run'

export function useMeansAction<Name extends MeansAction, T>(
  name: Name,
  toBody: (vars: T) => ActionBody<Name>,
  success?: string
) {
  return useGodAction<T>({
    run: (vars) => postAction(name, toBody(vars)),
    success,
  })
}
