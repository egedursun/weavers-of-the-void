import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type BiologyNodeView = Schema['BiologyNodeView']
export type BiologyEffectsView = Schema['BiologyEffectsView']
export type BiologyBodyView = Schema['BiologyBodyView']
export type BiologyVariant = Schema['BiologyVariant']

export const biologyKeys = {
  of: (nodeId: number) =>
    [...queryKeys.world.all, 'biology-of', nodeId] as const,
}

export function useNodeBiology(nodeId: number) {
  return useQuery({
    queryKey: biologyKeys.of(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/biology/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export type BiologyAction =
  | 'biology:edit'
  | 'biology_variant:add'
  | 'biology_variant:remove'
  | 'biology:reset'
  | 'biology_variants:run'

export function useBiologyAction<Name extends BiologyAction, T>(
  name: Name,
  toBody: (vars: T) => ActionBody<Name>,
  success?: string
) {
  return useGodAction<T>({
    writes: [{ lever: name }],
    run: (vars) => postAction(name, toBody(vars)),
    success,
  })
}
