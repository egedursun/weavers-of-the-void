import { type EntrySearch } from '@/components/layout/entry/entryStack'

export type GraphSearch = EntrySearch & {
  focus?: number
  from?: number
  to?: number
  world?: number
}

function positive(value: unknown): number | undefined {
  const number = typeof value === 'string' ? Number(value) : value
  return typeof number === 'number' && Number.isInteger(number) && number > 0
    ? number
    : undefined
}

export function validateGraphSearch(
  search: Record<string, unknown>
): GraphSearch {
  const result: GraphSearch = {}
  for (const key of ['focus', 'from', 'to', 'world'] as const) {
    const value = positive(search[key])
    if (value !== undefined) result[key] = value
  }
  return result
}
