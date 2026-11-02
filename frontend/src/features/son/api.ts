import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

export type SonDetail = components['schemas']['SonDetail']
export type ChatMessage = components['schemas']['MessageRecord']
export type ChatReply = components['schemas']['ChatReply']
export type LedgerPage = components['schemas']['LedgerPage']
export type BondView = components['schemas']['BondView']

export const SON_LEDGER_LIMIT = 60

export const sonKeys = {
  detail: (sonId: number) => [...queryKeys.world.all, 'son', sonId] as const,
  resurrection: (sonId: number) =>
    [...queryKeys.world.all, 'son', sonId, 'resurrection'] as const,
  chat: (sonId: number) =>
    [...queryKeys.world.all, 'son', sonId, 'chat'] as const,
  ledger: (sonId: number) =>
    [...queryKeys.world.all, 'son', sonId, 'ledger'] as const,
}

export function useSonDetail(sonId: number) {
  return useQuery({
    queryKey: sonKeys.detail(sonId),
    queryFn: () =>
      unwrap(
        api.GET('/api/sons/{son_id}', { params: { path: { son_id: sonId } } })
      ),
    enabled: Number.isInteger(sonId) && sonId > 0,
  })
}

export function useSonChat(sonId: number) {
  return useQuery({
    queryKey: sonKeys.chat(sonId),
    queryFn: () =>
      unwrap(
        api.GET('/api/sons/{son_id}/chat', {
          params: { path: { son_id: sonId } },
        })
      ),
  })
}

export function useSonLedger(sonId: number) {
  return useQuery({
    queryKey: sonKeys.ledger(sonId),
    queryFn: () =>
      unwrap(
        api.GET('/api/ledger', {
          params: {
            query: {
              actor_kind: 'son',
              actor_id: sonId,
              limit: SON_LEDGER_LIMIT,
            },
          },
        })
      ),
  })
}

export function useResurrection(sonId: number) {
  return useQuery({
    queryKey: sonKeys.resurrection(sonId),
    queryFn: () =>
      unwrap(
        api.GET('/api/sons/{son_id}/resurrection', {
          params: { path: { son_id: sonId } },
        })
      ),
    enabled: Number.isInteger(sonId) && sonId > 0,
  })
}

export type OpportunityLines = components['schemas']['OpportunityLines']
export type SonToolsView = components['schemas']['SonToolsView']

export function useSonOpportunities(sonId: number, enabled = true) {
  return useQuery({
    queryKey: [...sonKeys.detail(sonId), 'opportunities'] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/sons/{son_id}/opportunities', {
          params: { path: { son_id: sonId } },
        })
      ),
    enabled: enabled && Number.isInteger(sonId) && sonId > 0,
  })
}

export function useSonTools(sonId: number, enabled = true) {
  return useQuery({
    queryKey: [...sonKeys.detail(sonId), 'tools'] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/sons/{son_id}/tools', {
          params: { path: { son_id: sonId } },
        })
      ),
    enabled: enabled && Number.isInteger(sonId) && sonId > 0,
  })
}
