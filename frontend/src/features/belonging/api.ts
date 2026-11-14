import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type BelongingNodeView = Schema['BelongingNodeView']

export const belongingKeys = {
  of: (nodeId: number) =>
    [...queryKeys.world.all, 'belonging-of', nodeId] as const,
}

export function useNodeBelonging(nodeId: number) {
  return useQuery({
    queryKey: belongingKeys.of(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/belonging/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export type BelongingAction =
  | 'held_identity:set'
  | 'held_identity:edit'
  | 'held_identity:delete'
  | 'peer_group:create'
  | 'peer_group:edit'
  | 'peer_group:delete'
  | 'peer_member:set'
  | 'peer_member:edit'
  | 'peer_member:delete'
  | 'sanctuary:create'
  | 'sanctuary:edit'
  | 'sanctuary:delete'
  | 'sanctuary_law:set'
  | 'sanctuary_law:edit'
  | 'sanctuary_law:delete'
  | 'satire:create'
  | 'satire:edit'
  | 'satire:delete'
  | 'belonging:run'
  | 'sanctuary:run'
  | 'satire:run'

export function useBelongingAction<Name extends BelongingAction, T>(
  name: Name,
  toBody: (vars: T) => ActionBody<Name>,
  success?: string
) {
  return useGodAction<T>({
    run: (vars) => postAction(name, toBody(vars)),
    success,
  })
}
