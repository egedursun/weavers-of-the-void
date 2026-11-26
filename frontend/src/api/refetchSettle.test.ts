import { QueryClient, QueryObserver } from '@tanstack/react-query'
import { describe, expect, it } from 'vitest'
import { settleRefetches } from './refetchSettle'

type Gate = { promise: Promise<string>; open: (value: string) => void }

function gate(): Gate {
  let open: (value: string) => void = () => undefined
  const promise = new Promise<string>((resolve) => {
    open = resolve
  })
  return { promise, open }
}

function watched(client: QueryClient, key: string, fetches: Gate[]) {
  const observer = new QueryObserver(client, {
    queryKey: [key],
    queryFn: () => {
      const next = gate()
      fetches.push(next)
      return next.promise
    },
    staleTime: Infinity,
  })
  return observer.subscribe(() => undefined)
}

async function flushed(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 0))
}

describe('settling the refetches a success starts', () => {
  it('waits until the queries the success invalidated have their new data', async () => {
    const client = new QueryClient()
    const fetches: Gate[] = []
    const stop = watched(client, 'shown', fetches)
    fetches[0].open('before')
    await flushed()
    let settled = false
    const done = settleRefetches(client, () => {
      void client.invalidateQueries({ queryKey: ['shown'] })
    }).then(() => {
      settled = true
    })
    await flushed()
    expect(fetches).toHaveLength(2)
    expect(settled).toBe(false)
    fetches[1].open('after')
    await done
    expect(settled).toBe(true)
    expect(client.getQueryData(['shown'])).toBe('after')
    stop()
  })

  it('does not wait for a fetch that was already running before the success', async () => {
    const client = new QueryClient()
    const fetches: Gate[] = []
    const stop = watched(client, 'slow', fetches)
    await settleRefetches(client, () => undefined)
    expect(client.getQueryState(['slow'])?.fetchStatus).toBe('fetching')
    fetches[0].open('late')
    stop()
  })

  it('waits for an async success before looking for its refetches', async () => {
    const client = new QueryClient()
    const fetches: Gate[] = []
    const stop = watched(client, 'shown', fetches)
    fetches[0].open('before')
    await flushed()
    let settled = false
    const done = settleRefetches(client, async () => {
      await flushed()
      void client.invalidateQueries({ queryKey: ['shown'] })
    }).then(() => {
      settled = true
    })
    await flushed()
    await flushed()
    expect(settled).toBe(false)
    fetches[1].open('after')
    await done
    expect(settled).toBe(true)
    stop()
  })
})
