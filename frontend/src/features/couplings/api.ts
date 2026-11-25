import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type CouplingNodeView = Schema['CouplingNodeView']

const keys = {
  node: (nodeId: number) =>
    [...queryKeys.world.all, 'couplings-of', nodeId] as const,
}

export function useNodeCouplings(nodeId: number) {
  return useQuery({
    queryKey: keys.node(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/couplings/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export type CouplingAction =
  | 'rite_component:set'
  | 'restraint:set'
  | 'sociolect:create'
  | 'sociolect:merge'
  | 'sociolect:edit'
  | 'sociolect:delete'
  | 'sign_language:create'
  | 'sign_origin:edit'
  | 'sign_origin:delete'
  | 'carrion:keep'
  | 'carrion:clear'
  | 'carrion:edit'
  | 'teaching:grant'
  | 'teaching:block'
  | 'teaching:edit'
  | 'teaching:delete'
  | 'beast_lore:grant'
  | 'beast_lore:reveal'
  | 'field_agreement:force'
  | 'field_agreement:void'
  | 'field_agreement:edit'
  | 'field_agreement:delete'
  | 'deep_seal:seal'
  | 'deep_seal:unseal'
  | 'deep_seal:edit'
  | 'deep_seal:delete'
  | 'novelty:set'
  | 'novelty:delete'

export function useCouplingAction<Name extends CouplingAction, T>(
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
