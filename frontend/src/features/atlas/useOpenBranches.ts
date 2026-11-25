import { useCallback, useState } from 'react'
import { storedItem, storeItem, universeKey } from '@/lib/universeStorage'
import { DEFAULT_OPEN } from './atlasModel'

const STORAGE_KEY = 'aerona.atlas.open'

function load(): Set<string> {
  try {
    const raw = storedItem(universeKey(STORAGE_KEY))
    const parsed: unknown = raw ? JSON.parse(raw) : null
    if (Array.isArray(parsed))
      return new Set(
        parsed.filter((item): item is string => typeof item === 'string')
      )
  } catch {
    return new Set(DEFAULT_OPEN)
  }
  return new Set(DEFAULT_OPEN)
}

function save(keys: Set<string>) {
  try {
    storeItem(universeKey(STORAGE_KEY), JSON.stringify([...keys]))
  } catch {
    return
  }
}

export function useOpenBranches() {
  const [open, setOpen] = useState<Set<string>>(load)
  const update = useCallback((next: (current: Set<string>) => Set<string>) => {
    setOpen((current) => {
      const value = next(current)
      save(value)
      return value
    })
  }, [])
  const toggle = useCallback(
    (key: string, isOpen: boolean) =>
      update((current) => {
        const value = new Set(current)
        if (isOpen) value.add(key)
        else value.delete(key)
        return value
      }),
    [update]
  )
  const openAll = useCallback(
    (keys: string[]) => update(() => new Set(keys)),
    [update]
  )
  const closeAll = useCallback(() => update(() => new Set()), [update])
  return { open, toggle, openAll, closeAll }
}
