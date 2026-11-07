import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { loreKeys } from '../api/keys'

export type Statecraft = components['schemas']['StatecraftView']
export type Regard = components['schemas']['RegardView']
export type Crisis = components['schemas']['CrisisView']
export type Backer = components['schemas']['BackerView']
export type Sphere = components['schemas']['SphereView']
export type Subject = components['schemas']['SubjectView']
export type CrisisDemand = components['schemas']['CrisisDemand']
export type CrisisSide = components['schemas']['CrisisSide']
export type CrisisState = components['schemas']['CrisisState']
export type SubjectKind = components['schemas']['SubjectKind']

export function statecraftKey(nodeId: number) {
  return [...loreKeys.entity(nodeId), 'statecraft'] as const
}

export function useStatecraft(nodeId: number) {
  return useQuery({
    queryKey: statecraftKey(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/statecraft/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
    retry: false,
  })
}
