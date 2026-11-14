import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type ErasNodeView = Schema['ErasNodeView']

export const erasKeys = {
  of: (nodeId: number) => [...queryKeys.world.all, 'eras-of', nodeId] as const,
}

export function useNodeEras(nodeId: number) {
  return useQuery({
    queryKey: erasKeys.of(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/eras/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export type EraAction =
  | 'tech_programme:create'
  | 'tech_programme:edit'
  | 'tech_programme:delete'
  | 'research:technique'
  | 'eras:run'

export function useEraAction<Name extends EraAction, T>(
  name: Name,
  toBody: (vars: T) => ActionBody<Name>,
  success?: string
) {
  return useGodAction<T>({
    run: (vars) => postAction(name, toBody(vars)),
    success,
  })
}
