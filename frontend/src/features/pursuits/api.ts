import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type PursuitsNodeView = Schema['PursuitsNodeView']

export const pursuitsKeys = {
  of: (nodeId: number) =>
    [...queryKeys.world.all, 'pursuits-of', nodeId] as const,
}

export function useNodePursuits(nodeId: number) {
  return useQuery({
    queryKey: pursuitsKeys.of(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/pursuits/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export type PursuitsAction =
  | 'art_price:set'
  | 'art_price:edit'
  | 'art_price:delete'
  | 'art_sale:create'
  | 'art_sale:edit'
  | 'art_sale:delete'
  | 'collector:create'
  | 'collector:edit'
  | 'collector:delete'
  | 'forgery:create'
  | 'forgery:expose'
  | 'forgery:edit'
  | 'forgery:delete'
  | 'canon_work:create'
  | 'canon_work:edit'
  | 'canon_work:delete'
  | 'art_movement:create'
  | 'art_movement:edit'
  | 'art_movement:manifesto'
  | 'art_movement:delete'
  | 'club:create'
  | 'club:edit'
  | 'club:delete'
  | 'league:create'
  | 'league:edit'
  | 'league:delete'
  | 'match:create'
  | 'match:edit'
  | 'match:delete'
  | 'bet:create'
  | 'bet:edit'
  | 'bet:delete'
  | 'construct:create'
  | 'construct:ensoul'
  | 'construct:unmake'
  | 'construct:edit'
  | 'construct:delete'
  | 'instruction_set:create'
  | 'instruction_set:resolve'
  | 'instruction_set:edit'
  | 'instruction_set:delete'
  | 'instruction_order:create'
  | 'instruction_order:edit'
  | 'instruction_order:delete'
  | 'remade:create'
  | 'remade:edit'
  | 'remade:delete'
  | 'monster_contract:create'
  | 'monster_contract:assign'
  | 'monster_contract:edit'
  | 'monster_contract:delete'
  | 'birth_sign:create'
  | 'birth_sign:edit'
  | 'birth_sign:delete'

export function usePursuitsAction<Name extends PursuitsAction, T>(
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
