import { useMemo } from 'react'
import {
  keepPreviousData,
  useInfiniteQuery,
  useQuery,
} from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useCatalogue } from '@/features/entity/api/queries'

export type EpochListItem = components['schemas']['EpochListItem']
export type ChronicleEpoch = components['schemas']['ChronicleEpoch']
export type ChroniclePage = components['schemas']['ChroniclePage']
export type PerspectiveLine = components['schemas']['PerspectiveLine']
export type CosmicEpoch = components['schemas']['CosmicEpoch']
export type EpochStatistics = components['schemas']['EpochStatistics']
export type SearchHit = components['schemas']['SearchHit']
export type ThreadRecord = components['schemas']['ThreadRecord']
export type ChronicleScope = components['schemas']['ChronicleScope']
export type FactSearchView = components['schemas']['FactSearchView']
export type FactSearchHit = components['schemas']['FactSearchHit']
export type StepAction = components['schemas']['StepAction']
export type InstrumentKind = components['schemas']['InstrumentKind']

const world = queryKeys.world.all

export const chronicleKeys = {
  epochs: [...world, 'epochs'] as const,
  counts: [...world, 'chronicle', 'epochs'] as const,
  linesAll: [...world, 'chronicle', 'lines'] as const,
  lines: (epoch: number) => [...world, 'chronicle', 'lines', epoch] as const,
  perspectives: [...world, 'chronicle', 'perspectives'] as const,
  cosmic: (last: number) => [...world, 'chronicle', 'cosmic', last] as const,
  stats: [...world, 'stats', 'epochs'] as const,
  search: (query: string) => [...world, 'search', query] as const,
  facts: (query: RecordQuery) =>
    [...world, 'records', 'search', query] as const,
  scoped: (scope: ChronicleScope, scopeId: number | null, loaded: number) =>
    [...world, 'chronicle', 'scope', scope, scopeId, loaded] as const,
}

export const CODEX_URL = '/api/codex.zip'
export const BOOK_URL = '/api/book'
export const SEARCH_MIN_LENGTH = 2

export function useEpochs() {
  return useQuery({
    queryKey: chronicleKeys.epochs,
    queryFn: () => unwrap(api.GET('/api/epochs')),
  })
}

export function useChronicleCounts() {
  return useQuery({
    queryKey: chronicleKeys.counts,
    queryFn: () => unwrap(api.GET('/api/chronicle/epochs')),
  })
}

function fetchEpochLines(epoch: number) {
  return unwrap(api.GET('/api/chronicle', { params: { query: { epoch } } }))
}

export function useEpochLines(epoch: number, enabled: boolean) {
  return useQuery({
    queryKey: chronicleKeys.lines(epoch),
    queryFn: () => fetchEpochLines(epoch),
    enabled,
  })
}

export function usePerspectives() {
  return useQuery({
    queryKey: chronicleKeys.perspectives,
    queryFn: () => unwrap(api.GET('/api/chronicle/perspectives')),
  })
}

export function useCosmicChronicle(last: number, enabled: boolean) {
  return useQuery({
    queryKey: chronicleKeys.cosmic(last),
    placeholderData: keepPreviousData,
    queryFn: () =>
      unwrap(api.GET('/api/chronicle/cosmic', { params: { query: { last } } })),
    enabled,
  })
}

export function useEpochStatistics() {
  return useQuery({
    queryKey: chronicleKeys.stats,
    queryFn: () => unwrap(api.GET('/api/stats/epochs')),
  })
}

export function useWorldSearch(query: string) {
  const trimmed = query.trim()
  return useQuery({
    queryKey: chronicleKeys.search(trimmed),
    queryFn: () =>
      unwrap(api.GET('/api/search', { params: { query: { q: trimmed } } })),
    enabled: trimmed.length >= SEARCH_MIN_LENGTH,
    placeholderData: keepPreviousData,
  })
}

export function closeThread(threadId: number, how: string) {
  return unwrap(
    api.POST('/api/threads/{thread_id}/close', {
      params: { path: { thread_id: threadId } },
      body: { how },
    })
  )
}

export function openThread(text: string, relatedIds: number[]) {
  return unwrap(
    api.POST('/api/threads', { body: { text, related_ids: relatedIds } })
  )
}

export function useChronicleKindLabels(): Map<string, string> {
  const catalogue = useCatalogue()
  return useMemo(
    () =>
      new Map(
        (catalogue.data?.chronicle_kinds ?? []).map((item) => [
          item.key,
          item.label,
        ])
      ),
    [catalogue.data]
  )
}

export const SCOPED_STEP = 40

export function useOlderLines(
  scope: ChronicleScope,
  scopeId: number | null,
  loaded: number,
  total: number
) {
  const pages = useInfiniteQuery({
    queryKey: chronicleKeys.scoped(scope, scopeId, loaded),
    queryFn: ({ pageParam }) =>
      unwrap(
        api.GET('/api/chronicle/scope', {
          params: {
            query: {
              scope,
              scope_id: scopeId ?? undefined,
              offset: pageParam,
              limit: SCOPED_STEP,
            },
          },
        })
      ),
    initialPageParam: loaded,
    getNextPageParam: (last, all) => {
      const reached =
        loaded + all.reduce((sum, page) => sum + page.items.length, 0)
      return reached < last.total ? reached : undefined
    },
    enabled: false,
  })
  const lines = (pages.data?.pages ?? []).flatMap((page) => page.items)
  const reached = loaded + lines.length
  const loadOlder = () => {
    if (pages.isFetching) return
    if (pages.data) void pages.fetchNextPage({ cancelRefetch: false })
    else void pages.refetch()
  }
  return {
    lines,
    total,
    remaining: Math.max(0, total - reached),
    loading: pages.isFetching,
    failed: pages.isError,
    loadOlder,
  }
}

export type OlderLines = ReturnType<typeof useOlderLines>

export type RecordQuery = {
  fact: string | null
  enumValue: string | null
  kind: string | null
  action: StepAction | null
  instrumentKind: InstrumentKind | null
}

export const RECORD_PAGE = 25

export function recordQueryEmpty(query: RecordQuery): boolean {
  return (
    !query.fact &&
    !query.enumValue &&
    !query.kind &&
    query.action === null &&
    query.instrumentKind === null
  )
}

export function useRecordSearch(query: RecordQuery) {
  return useInfiniteQuery({
    queryKey: chronicleKeys.facts(query),
    queryFn: ({ pageParam }) =>
      unwrap(
        api.GET('/api/records/search', {
          params: {
            query: {
              fact: query.fact ?? undefined,
              enum_value: query.enumValue ?? undefined,
              kind: query.kind ?? undefined,
              action: query.action ?? undefined,
              instrument_kind: query.instrumentKind ?? undefined,
              offset: pageParam,
              limit: RECORD_PAGE,
            },
          },
        })
      ),
    initialPageParam: 0,
    getNextPageParam: (last) => {
      const reached = last.offset + last.hits.length
      return reached < last.total ? reached : undefined
    },
    enabled: !recordQueryEmpty(query),
  })
}
