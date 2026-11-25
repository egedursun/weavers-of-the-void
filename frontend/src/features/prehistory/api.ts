import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type PrehistoryNodeView = Schema['PrehistoryNodeView']
export type PrehistoryHappeningView = Schema['PrehistoryHappeningView']
export type DeepTimeRunView = Schema['DeepTimeRunView']
export type DeepTimeHappeningView = Schema['DeepTimeHappeningView']

const keys = {
  prehistory: (nodeId: number) =>
    [...queryKeys.world.all, 'prehistory-of', nodeId] as const,
  deepTime: () => [...queryKeys.world.all, 'deep-time'] as const,
}

export function useNodePrehistory(nodeId: number) {
  return useQuery({
    queryKey: keys.prehistory(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/prehistory/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export function useDeepTime() {
  return useQuery({
    queryKey: keys.deepTime(),
    queryFn: () => unwrap(api.GET('/api/deep-time')),
  })
}

export type PrehistoryAction =
  | 'prehistory:configure'
  | 'prehistory:run'
  | 'prehistory:seed'
  | 'prehistory:abort'
  | 'prehistory:edit'
  | 'prehistory:remove'
  | 'prehistory_event:edit'
  | 'prehistory_event:remove'
  | 'deep_time:run'
  | 'deep_time:stop'
  | 'deep_time:edit'
  | 'deep_time:remove'
  | 'deep_time_event:edit'
  | 'deep_time_event:remove'

export function usePrehistoryAction<Name extends PrehistoryAction, T>(
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
