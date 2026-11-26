import { QueryClient } from '@tanstack/react-query'
import { QUERY_STALE_TIME_MS } from '@/constants/ui'
import { subscribeWorkspace } from './workspaceStore'

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

subscribeWorkspace(() => {
  void libraryQueryClient.resetQueries()
})

export function queryClientFor(universeId: string): QueryClient {
  const known = universeClients.get(universeId)
  if (known) return known
  const created = createQueryClient()
  universeClients.set(universeId, created)
  return created
}

export function refreshEveryUniverse(queryKey: readonly unknown[]): void {
  for (const client of universeClients.values())
    void client.invalidateQueries({ queryKey })
}

export function dropQueryClient(universeId: string): void {
  universeClients.get(universeId)?.clear()
  universeClients.delete(universeId)
}

export function dropEveryQueryClient(): void {
  libraryQueryClient.removeQueries({
    predicate: (query) => query.getObserversCount() === 0,
  })
  void libraryQueryClient.resetQueries()
  for (const id of [...universeClients.keys()]) dropQueryClient(id)
}
