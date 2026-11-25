import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { useMutation } from '@/api/mutation'
import { queryKeys } from '@/api/queryKeys'

export type ActionItem = components['schemas']['ActionCatalogueItem']
export type ActionResponse = components['schemas']['ActionResponse']
export type SearchHit = components['schemas']['SearchHit']

const SEARCH_DEBOUNCE_MS = 140
export const SEARCH_MIN_LENGTH = 2

export const paletteKeys = {
  actions: [...queryKeys.rules.all, 'actions'] as const,
  search: (query: string) => [...queryKeys.world.all, 'search', query] as const,
}

export function useActionCatalogue(enabled: boolean) {
  return useQuery({
    queryKey: paletteKeys.actions,
    queryFn: () => unwrap(api.GET('/api/actions')),
    enabled,
  })
}

function useDebounced(value: string): string {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const handle = window.setTimeout(
      () => setDebounced(value),
      SEARCH_DEBOUNCE_MS
    )
    return () => window.clearTimeout(handle)
  }, [value])
  return debounced
}

export function useWorldSearch(query: string) {
  const term = useDebounced(query.trim())
  const search = useQuery({
    queryKey: paletteKeys.search(term),
    queryFn: () =>
      unwrap(api.GET('/api/search', { params: { query: { q: term } } })),
    enabled: term.length >= SEARCH_MIN_LENGTH,
    placeholderData: (previous) => previous,
  })
  return { term, search }
}

type RawMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

function callAction(
  method: string,
  url: string,
  body: Record<string, unknown>
) {
  const request = api.request as unknown as (
    method: string,
    url: string,
    init: { body?: Record<string, unknown> }
  ) => Promise<{ data?: ActionResponse; error?: unknown; response: Response }>
  const verb = method.toUpperCase() as RawMethod
  return unwrap(
    request(verb.toLowerCase(), url, verb === 'GET' ? {} : { body })
  )
}

export function useRunAction(lever: string) {
  const queryClient = useQueryClient()
  return useMutation({
    writes: [{ lever }],
    mutationFn: ({
      method,
      url,
      body,
    }: {
      method: string
      url: string
      body: Record<string, unknown>
    }) => callAction(method, url, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.world.all })
      void queryClient.invalidateQueries({ queryKey: queryKeys.ledger.all })
      void queryClient.invalidateQueries({ queryKey: queryKeys.jobs.all })
    },
  })
}
