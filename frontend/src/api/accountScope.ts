const listeners = new Set<() => void>()

let current: number | null = null

export function currentAccountScope(): number | null {
  return current
}

export function setAccountScope(id: number | null): void {
  if (id === current) return
  current = id
  for (const listener of listeners) listener()
}

export function subscribeAccountScope(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}
