import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

type Schemas = components['schemas']

export type EventAccount = Schemas['EventAccountView']
export type EventStep = Schemas['EventStepRecord']
export type EventChange = Schemas['EventChangeRecord']
export type EventFact = Schemas['EventFactRecord']
export type EventParticipant = Schemas['EventParticipantRecord']
export type EventRumour = Schemas['EventRumourRecord']
export type EventDistortion = Schemas['EventRumourDistortionRecord']
export type EventTerm = Schemas['EventTermRecord']
export type EventLink = Schemas['EventLinkRecord']
export type EventMoment = Schemas['EventMomentRecord']
export type NodeHistoryEntry = Schemas['NodeHistoryEntry']
export type StateAtRow = Schemas['StateAtRowRecord']
export type IncidentRole = Schemas['IncidentRole']
export type StepAction = Schemas['StepAction']
export type StepOutcome = Schemas['StepOutcome']
export type InstrumentKind = Schemas['InstrumentKind']
export type StepLocus = Schemas['StepLocus']
export type FactUnit = Schemas['FactUnit']
export type WitnessMode = Schemas['WitnessMode']

export const recordKeys = {
  all: [...queryKeys.world.all, 'records'] as const,
  account: (incidentId: number) =>
    [...recordKeys.all, 'account', incidentId] as const,
  history: (nodeId: number, query: HistoryQuery) =>
    [...recordKeys.all, 'history', nodeId, query] as const,
  stateAt: (query: StateAtQuery) =>
    [...recordKeys.all, 'state-at', query] as const,
}

export function useEventAccount(incidentId: number | null) {
  return useQuery({
    queryKey: recordKeys.account(incidentId ?? 0),
    enabled: incidentId !== null,
    queryFn: () =>
      unwrap(
        api.GET('/api/incidents/{incident_id}', {
          params: { path: { incident_id: incidentId ?? 0 } },
        })
      ),
  })
}

export type HistoryQuery = {
  role: IncidentRole | null
  kind: string | null
  limit: number
}

export function useNodeHistory(nodeId: number | null, query: HistoryQuery) {
  return useQuery({
    queryKey: recordKeys.history(nodeId ?? 0, query),
    enabled: nodeId !== null,
    placeholderData: keepPreviousData,
    queryFn: () =>
      unwrap(
        api.GET('/api/nodes/{node_id}/history', {
          params: {
            path: { node_id: nodeId ?? 0 },
            query: {
              role: query.role ?? undefined,
              kind: query.kind ?? undefined,
              offset: 0,
              limit: query.limit,
            },
          },
        })
      ),
  })
}

export type StateAtQuery = {
  epoch: number
  nodeId: number | null
  table: string | null
  limit: number
}

export function useStateAt(query: StateAtQuery | null) {
  return useQuery({
    queryKey: recordKeys.stateAt(
      query ?? { epoch: 0, nodeId: null, table: null, limit: 0 }
    ),
    enabled: query !== null && (query.nodeId !== null || query.table !== null),
    placeholderData: keepPreviousData,
    queryFn: () =>
      unwrap(
        api.GET('/api/state-at', {
          params: {
            query: {
              epoch: query?.epoch ?? 0,
              node_id: query?.nodeId ?? undefined,
              table: query?.table ?? undefined,
              offset: 0,
              limit: query?.limit,
            },
          },
        })
      ),
  })
}
