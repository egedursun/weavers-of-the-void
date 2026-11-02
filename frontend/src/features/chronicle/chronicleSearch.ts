export type ChronicleSearch = {
  q?: string
  kinds?: string
  world?: number
  epoch?: number
  line?: number
  all?: boolean
}

function positive(value: unknown): number | undefined {
  const number = typeof value === 'string' ? Number(value) : value
  return typeof number === 'number' && Number.isInteger(number) && number > 0
    ? number
    : undefined
}

export function validateChronicleSearch(
  search: Record<string, unknown>
): ChronicleSearch {
  const result: ChronicleSearch = {}
  if (typeof search.q === 'string' && search.q.trim()) result.q = search.q
  if (typeof search.kinds === 'string' && /^[a-z_,]+$/.test(search.kinds))
    result.kinds = search.kinds
  const world = positive(search.world)
  if (world) result.world = world
  const epoch = positive(search.epoch)
  if (epoch) result.epoch = epoch
  const line = positive(search.line)
  if (line) result.line = line
  if (search.all === true || search.all === 'true') result.all = true
  return result
}

export function kindSet(kinds: string | undefined): Set<string> | null {
  if (!kinds) return null
  return new Set(kinds.split(',').filter(Boolean))
}
