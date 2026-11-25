import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type TransformNodeView = Schema['TransformNodeView']
export type KindChangeView = Schema['KindChangeView']
export type TransformProspectView = Schema['TransformProspectView']
export type StarModifierView = Schema['StarModifierView']
export type TransformKind = Schema['TransformKind']

const keys = {
  node: (nodeId: number) =>
    [...queryKeys.world.all, 'transformations-of', nodeId] as const,
  timeline: () => [...queryKeys.world.all, 'transformations'] as const,
}

export function useNodeTransformations(nodeId: number) {
  return useQuery({
    queryKey: keys.node(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/transformations/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export function useTransformTimeline() {
  return useQuery({
    queryKey: keys.timeline(),
    queryFn: () => unwrap(api.GET('/api/transformations')),
  })
}

export type TransformAction =
  | 'transform:force'
  | 'transform:block'
  | 'transform:release'
  | 'transform:revert'
  | 'transformation:edit'
  | 'transformation:delete'
  | 'transform_prospect:edit'
  | 'transform_prospect:delete'
  | 'star_modifier:create'
  | 'star_modifier:edit'
  | 'star_modifier:delete'
  | 'son:sanity'
  | 'son:outer_bargain'
  | 'ruling:decree'
  | 'heroquest:begin'

export function useTransformAction<Name extends TransformAction, T>(
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
