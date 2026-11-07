import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'

export type LawKindSpec = components['schemas']['LawKindSpec']

export function useLawKinds() {
  return useQuery({
    queryKey: ['laws', 'kinds'],
    staleTime: Number.POSITIVE_INFINITY,
    queryFn: () => unwrap(api.GET('/api/laws/kinds')),
  })
}
