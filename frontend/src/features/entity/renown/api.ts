import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { loreKeys } from '../api/keys'

export type Renown = components['schemas']['RenownView']
export type LocalReputation = components['schemas']['LocalReputationView']
export type Standing = components['schemas']['StandingView']
export type DeedRecord = components['schemas']['DeedRecordView']
export type DeedClaim = components['schemas']['DeedClaimView']
export type LoreTrade = components['schemas']['LoreTradeView']
export type ReputationAxis = components['schemas']['ReputationAxis']

export function renownKey(nodeId: number) {
  return [...loreKeys.entity(nodeId), 'renown'] as const
}

export function useRenown(nodeId: number) {
  return useQuery({
    queryKey: renownKey(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/renown/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
    retry: false,
  })
}
