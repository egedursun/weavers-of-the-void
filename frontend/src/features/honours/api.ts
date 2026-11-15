import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type HonoursNodeView = Schema['HonoursNodeView']

export const honoursKeys = {
  of: (nodeId: number) =>
    [...queryKeys.world.all, 'honours-of', nodeId] as const,
}

export function useNodeHonours(nodeId: number) {
  return useQuery({
    queryKey: honoursKeys.of(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/honours/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export type HonoursAction =
  | 'named_unit:create'
  | 'named_unit:edit'
  | 'named_unit:delete'
  | 'unit_honour:create'
  | 'unit_honour:edit'
  | 'unit_honour:delete'
  | 'veteran_grant:create'
  | 'veteran_grant:edit'
  | 'veteran_grant:delete'
  | 'honours:run'

export function useHonoursAction<Name extends HonoursAction, T>(
  name: Name,
  toBody: (vars: T) => ActionBody<Name>,
  success?: string
) {
  return useGodAction<T>({
    run: (vars) => postAction(name, toBody(vars)),
    success,
  })
}
