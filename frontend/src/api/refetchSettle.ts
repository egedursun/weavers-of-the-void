import { type Query, type QueryClient } from '@tanstack/react-query'
import { MUTATION_SETTLE_MAX_MS } from '@/constants/ui'

type InFlight = ReadonlyMap<Query, Promise<unknown> | undefined>

function inFlight(queryClient: QueryClient): InFlight {
  return new Map(
    queryClient
      .getQueryCache()
      .getAll()
      .map((query) => [query, query.promise])
  )
}

function startedSince(queryClient: QueryClient, before: InFlight): Query[] {
  return queryClient
    .getQueryCache()
    .getAll()
    .filter(
      (query) =>
        query.promise !== undefined && query.promise !== before.get(query)
    )
}

function idle(queries: readonly Query[]): boolean {
  return queries.every((query) => query.state.fetchStatus !== 'fetching')
}

function untilIdle(
  queryClient: QueryClient,
  queries: readonly Query[]
): Promise<void> {
  if (idle(queries)) return Promise.resolve()
  return new Promise((resolve) => {
    const cache = queryClient.getQueryCache()
    const finish = () => {
      clearTimeout(timer)
      unsubscribe()
      resolve()
    }
    const unsubscribe = cache.subscribe(() => {
      if (idle(queries)) finish()
    })
    const timer = setTimeout(finish, MUTATION_SETTLE_MAX_MS)
  })
}

export async function settleRefetches(
  queryClient: QueryClient,
  run: () => unknown
): Promise<void> {
  const before = inFlight(queryClient)
  await run()
  await untilIdle(queryClient, startedSince(queryClient, before))
}
