import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

export type UsageReport = components['schemas']['UsageReport']
export type UsageShare = components['schemas']['UsageShare']
export type UsagePoint = components['schemas']['UsagePoint']
export type UsageTotals = components['schemas']['UsageTotals']
export type UsageCall = components['schemas']['UsageCall']
export type UsageCallPage = components['schemas']['UsageCallPage']
export type UsageSort = components['schemas']['UsageSort']
export type UsageBucket = components['schemas']['UsageBucket']
export type LlmCallKind = components['schemas']['LlmCallKind']
export type LlmCallStatus = components['schemas']['LlmCallStatus']

export type UsageFilter = {
  search: string
  models: string[]
  roles: string[]
  steps: string[]
  kinds: LlmCallKind[]
  statuses: LlmCallStatus[]
  epochFrom: number | null
  epochTo: number | null
  since: string | null
}

export type UsageOrder = {
  sort: UsageSort
  descending: boolean
  offset: number
}

export const EMPTY_FILTER: UsageFilter = {
  search: '',
  models: [],
  roles: [],
  steps: [],
  kinds: [],
  statuses: [],
  epochFrom: null,
  epochTo: null,
  since: null,
}

const usageRoot = [...queryKeys.metrics.all, 'usage'] as const

const usageKeys = {
  summary: (filter: UsageFilter, bucket: UsageBucket) =>
    [...usageRoot, 'summary', filter, bucket] as const,
  calls: (filter: UsageFilter, order: UsageOrder) =>
    [...usageRoot, 'calls', filter, order] as const,
}

function filterQuery(filter: UsageFilter) {
  const search = filter.search.trim()
  return {
    search: search === '' ? undefined : search,
    model: filter.models.length ? filter.models : undefined,
    role: filter.roles.length ? filter.roles : undefined,
    step: filter.steps.length ? filter.steps : undefined,
    kind: filter.kinds.length ? filter.kinds : undefined,
    status: filter.statuses.length ? filter.statuses : undefined,
    epoch_from: filter.epochFrom ?? undefined,
    epoch_to: filter.epochTo ?? undefined,
    since: filter.since ?? undefined,
  }
}

export function useUsageSummary(filter: UsageFilter, bucket: UsageBucket) {
  return useQuery({
    queryKey: usageKeys.summary(filter, bucket),
    placeholderData: keepPreviousData,
    queryFn: () =>
      unwrap(
        api.GET('/api/usage/summary', {
          params: { query: { ...filterQuery(filter), bucket } },
        })
      ),
  })
}

export function useUsageCalls(filter: UsageFilter, order: UsageOrder) {
  return useQuery({
    queryKey: usageKeys.calls(filter, order),
    placeholderData: keepPreviousData,
    queryFn: () =>
      unwrap(
        api.GET('/api/usage/calls', {
          params: {
            query: {
              ...filterQuery(filter),
              sort: order.sort,
              descending: order.descending,
              offset: order.offset,
            },
          },
        })
      ),
  })
}
