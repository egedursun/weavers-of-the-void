export type PresenceSearch = {
  node?: number
}

export function validatePresenceSearch(
  search: Record<string, unknown>
): PresenceSearch {
  const value = search.node
  const node = typeof value === 'number' ? value : Number(value)
  return Number.isInteger(node) && node > 0 ? { node } : {}
}
