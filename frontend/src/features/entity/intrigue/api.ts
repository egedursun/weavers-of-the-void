import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { loreKeys } from '../api/keys'

export type Intrigue = components['schemas']['IntrigueView']
export type Secret = components['schemas']['SecretView']
export type Hook = components['schemas']['HookView']
export type Favour = components['schemas']['FavourView']
export type Scheme = components['schemas']['SchemeView']
export type Belief = components['schemas']['BeliefView']
export type IntrigueSecret = components['schemas']['IntrigueSecret']
export type PlotKind = components['schemas']['PlotKind']
export type SchemePhase = components['schemas']['SchemePhase']
export type HookStrength = components['schemas']['HookStrength']
export type HookSource = components['schemas']['HookSource']
export type HookDemand = components['schemas']['HookDemand']
export type FavourOrigin = components['schemas']['FavourOrigin']
export type IdentityReason = components['schemas']['IdentityReason']
export type BeliefSource = components['schemas']['BeliefSource']

export function intrigueKey(nodeId: number) {
  return [...loreKeys.entity(nodeId), 'intrigue'] as const
}

export function useIntrigue(nodeId: number) {
  return useQuery({
    queryKey: intrigueKey(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/intrigue/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
    retry: false,
  })
}
