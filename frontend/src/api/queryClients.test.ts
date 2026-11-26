import { describe, expect, it } from 'vitest'
import {
  dropQueryClient,
  queryClientFor,
  refreshEveryUniverse,
} from './queryClients'

describe('query clients of the open universes', () => {
  it('marks a query stale in every open universe at once', () => {
    const key = ['world', 'state'] as const
    const first = queryClientFor('first-universe')
    const second = queryClientFor('second-universe')
    first.setQueryData(key, { role_models: [] })
    second.setQueryData(key, { role_models: [] })
    refreshEveryUniverse(key)
    expect(first.getQueryState(key)?.isInvalidated).toBe(true)
    expect(second.getQueryState(key)?.isInvalidated).toBe(true)
    dropQueryClient('first-universe')
    dropQueryClient('second-universe')
  })
})
