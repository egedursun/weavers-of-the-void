import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { loreKeys } from '../api/keys'

export type Correspondence = components['schemas']['CorrespondenceView']
export type Dispatch = components['schemas']['DispatchView']
export type Opinion = components['schemas']['PublicOpinionView']
export type Cipher = components['schemas']['CipherView']
export type Signal = components['schemas']['SignalView']
export type Medium = components['schemas']['Medium']
export type DispatchContent = components['schemas']['DispatchContent']
export type DispatchState = components['schemas']['DispatchState']
export type OpinionSubject = components['schemas']['OpinionSubject']
export type SignalKind = components['schemas']['SignalKind']
export type SignalState = components['schemas']['SignalState']

export function correspondenceKey(nodeId: number) {
  return [...loreKeys.entity(nodeId), 'correspondence'] as const
}

export function useCorrespondence(nodeId: number) {
  return useQuery({
    queryKey: correspondenceKey(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/correspondence/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
    retry: false,
  })
}
