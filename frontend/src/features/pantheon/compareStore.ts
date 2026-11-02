import { useCallback, useSyncExternalStore } from 'react'
import { COMPARE_MAX, COMPARE_STORAGE_KEY } from './constants'

const listeners = new Set<() => void>()
let cache: number[] | null = null

function read(): number[] {
  if (cache) return cache
  try {
    const parsed: unknown = JSON.parse(
      localStorage.getItem(COMPARE_STORAGE_KEY) ?? '[]'
    )
    cache = Array.isArray(parsed)
      ? parsed.filter((item): item is number => typeof item === 'number')
      : []
  } catch {
    cache = []
  }
  return cache
}

function write(next: number[]) {
  cache = next
  try {
    localStorage.setItem(COMPARE_STORAGE_KEY, JSON.stringify(next))
  } catch {
    cache = next
  }
  for (const listener of listeners) listener()
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function useCompareSelection() {
  const selected = useSyncExternalStore(subscribe, read, read)
  const toggle = useCallback((sonId: number) => {
    const current = read()
    if (current.includes(sonId)) write(current.filter((id) => id !== sonId))
    else if (current.length < COMPARE_MAX) write([...current, sonId])
  }, [])
  const prune = useCallback((valid: number[]) => {
    const current = read()
    const kept = current.filter((id) => valid.includes(id))
    if (kept.length !== current.length) write(kept)
  }, [])
  return { selected, toggle, prune, full: selected.length >= COMPARE_MAX }
}
