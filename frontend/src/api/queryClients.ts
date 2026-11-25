import { QueryClient } from '@tanstack/react-query'
import { QUERY_STALE_TIME_MS } from '@/constants/ui'

const universeClients = new Map<string, QueryClient>()

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: 1,
        refetchOnWindowFocus: false,
        staleTime: QUERY_STALE_TIME_MS,
      },
    },
  })
}

export const libraryQueryClient = createQueryClient()

export function queryClientFor(universeId: string): QueryClient {
  const known = universeClients.get(universeId)
  if (known) return known
  const created = createQueryClient()
  universeClients.set(universeId, created)
  return created
}

export function dropQueryClient(universeId: string): void {
  universeClients.get(universeId)?.clear()
  universeClients.delete(universeId)
}
