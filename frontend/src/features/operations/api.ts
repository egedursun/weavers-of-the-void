import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type OperationsNodeView = Schema['OperationsNodeView']

export const operationsKeys = {
  of: (nodeId: number) =>
    [...queryKeys.world.all, 'operations-of', nodeId] as const,
}

export function useNodeOperations(nodeId: number) {
  return useQuery({
    queryKey: operationsKeys.of(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/operations/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export type OperationsAction =
  | 'echelon:create'
  | 'echelon:edit'
  | 'echelon:assign'
  | 'echelon:delete'
  | 'depot:create'
  | 'depot:edit'
  | 'depot:delete'
  | 'transport:create'
  | 'transport:edit'
  | 'transport:delete'
  | 'supply_flow:edit'
  | 'supply_flow:delete'
  | 'army_operation:set'
  | 'army_operation:edit'
  | 'army_operation:delete'
  | 'theatre:set'
  | 'theatre:edit'
  | 'theatre:delete'
  | 'ship_state:set'
  | 'ship_state:edit'
  | 'ship_state:delete'
  | 'ship_crew:set'
  | 'ship_crew:edit'
  | 'ship_crew:delete'
  | 'admiralty:set'
  | 'admiralty:edit'
  | 'admiralty:delete'
  | 'expedition:create'
  | 'expedition:edit'
  | 'expedition:advance'
  | 'expedition:recall'
  | 'expedition:delete'
  | 'expedition_member:create'
  | 'expedition_member:edit'
  | 'expedition_member:delete'
  | 'expedition_log:edit'
  | 'expedition_log:delete'
  | 'quirk:create'
  | 'quirk:edit'
  | 'quirk:delete'

export function useOperationsAction<Name extends OperationsAction, T>(
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
