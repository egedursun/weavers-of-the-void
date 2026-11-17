import {
  llmCallKindValues,
  llmCallStatusValues,
  usageBucketValues,
  usageSortValues,
} from '@/api/generated/schema'
import {
  type LlmCallKind,
  type LlmCallStatus,
  type UsageBucket,
  type UsageFilter,
  type UsageOrder,
  type UsageSort,
} from './api'
import { RANGES, type RangeKey } from './usageVisuals'

export const BREAKDOWNS = ['steps', 'models', 'roles'] as const
export type Breakdown = (typeof BREAKDOWNS)[number]

const HOUR_MS = 3_600_000
const MINUTE_MS = 60_000

export type UsageSearch = {
  q?: string
  model?: string[]
  step?: string[]
  role?: string[]
  kind?: LlmCallKind[]
  status?: LlmCallStatus[]
  from?: number
  to?: number
  range?: RangeKey
  bucket?: UsageBucket
  sort?: UsageSort
  asc?: boolean
  offset?: number
  view?: Breakdown
}

function texts(value: unknown): string[] {
  const list = Array.isArray(value) ? value : [value]
  return list.filter(
    (item): item is string => typeof item === 'string' && item !== ''
  )
}

function whole(value: unknown): number | undefined {
  const number = Number(value)
  return value !== undefined &&
    value !== '' &&
    Number.isInteger(number) &&
    number >= 0
    ? number
    : undefined
}

function oneOf<T extends string>(
  values: readonly T[],
  value: unknown
): T | undefined {
  return values.find((item) => item === value)
}

function someOf<T extends string>(values: readonly T[], value: unknown): T[] {
  return texts(value).flatMap((item) => {
    const found = oneOf(values, item)
    return found ? [found] : []
  })
}

function present<T>(list: T[]): T[] | undefined {
  return list.length > 0 ? list : undefined
}

export function validateUsageSearch(
  search: Record<string, unknown>
): UsageSearch {
  const query = texts(search.q)[0]
  return {
    q: query,
    model: present(texts(search.model)),
    step: present(texts(search.step)),
    role: present(texts(search.role)),
    kind: present(someOf(llmCallKindValues, search.kind)),
    status: present(someOf(llmCallStatusValues, search.status)),
    from: whole(search.from),
    to: whole(search.to),
    range: oneOf(
      RANGES.map((item) => item.key),
      search.range
    ),
    bucket: oneOf(usageBucketValues, search.bucket),
    sort: oneOf(usageSortValues, search.sort),
    asc: search.asc === true || search.asc === 'true' ? true : undefined,
    offset: whole(search.offset) || undefined,
    view: oneOf(BREAKDOWNS, search.view),
  }
}

export function sinceOf(range: RangeKey, now: number): string | null {
  const hours = RANGES.find((item) => item.key === range)?.hours ?? null
  if (hours === null) return null
  return new Date(
    Math.floor(now / MINUTE_MS) * MINUTE_MS - hours * HOUR_MS
  ).toISOString()
}

export function filterOf(search: UsageSearch, now: number): UsageFilter {
  return {
    search: search.q ?? '',
    models: search.model ?? [],
    roles: search.role ?? [],
    steps: search.step ?? [],
    kinds: search.kind ?? [],
    statuses: search.status ?? [],
    epochFrom: search.from ?? null,
    epochTo: search.to ?? null,
    since: sinceOf(search.range ?? 'all', now),
  }
}

export function orderOf(search: UsageSearch): UsageOrder {
  return {
    sort: search.sort ?? 'time',
    descending: search.asc !== true,
    offset: search.offset ?? 0,
  }
}

export function searchOfFilter(
  filter: UsageFilter
): Pick<
  UsageSearch,
  'q' | 'model' | 'step' | 'role' | 'kind' | 'status' | 'from' | 'to'
> {
  return {
    q: filter.search.trim() === '' ? undefined : filter.search,
    model: present(filter.models),
    step: present(filter.steps),
    role: present(filter.roles),
    kind: present(filter.kinds),
    status: present(filter.statuses),
    from: filter.epochFrom ?? undefined,
    to: filter.epochTo ?? undefined,
  }
}
