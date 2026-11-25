import { type StateStorage, createJSONStorage } from 'zustand/middleware'
import { currentUniverse, subscribeUniverse } from '@/api/universeStore'

export const UNIVERSE_STORAGE_KEYS = [
  'aerona.world-filter',
  'aerona.divine-will.composer',
  'aerona.onboarding',
  'aerona.cards.seals',
  'aerona.bookmarks',
  'aerona.records-tab',
  'aerona.atlas.open',
  'aerona.compare',
  'aerona.epoch-box-hidden',
] as const

export const UNIVERSE_STORAGE_PREFIXES = [
  'aerona.map.',
  'aerona.graph.',
  'aerona.cosmos.dialect.',
] as const

type FixedKey = (typeof UNIVERSE_STORAGE_KEYS)[number]

export type UniversePrefixedKey =
  `${(typeof UNIVERSE_STORAGE_PREFIXES)[number]}${string}`

export type UniverseStorageKey = FixedKey | UniversePrefixedKey

const SCOPE_MARK = '@'
const NO_UNIVERSE = 'none'

let quiet = false

function scoped(base: string, universe: string | null): string {
  return `${base}${SCOPE_MARK}${universe ?? NO_UNIVERSE}`
}

export function universeKey(base: UniverseStorageKey): string {
  return scoped(base, currentUniverse())
}

function local(): Storage | null {
  try {
    return window.localStorage
  } catch {
    return null
  }
}

const universeLocalStorage: StateStorage = {
  getItem: (name) => {
    try {
      return local()?.getItem(scoped(name, currentUniverse())) ?? null
    } catch {
      return null
    }
  },
  setItem: (name, value) => {
    if (quiet) return
    try {
      local()?.setItem(scoped(name, currentUniverse()), value)
    } catch {
      return
    }
  },
  removeItem: (name) => {
    if (quiet) return
    try {
      local()?.removeItem(scoped(name, currentUniverse()))
    } catch {
      return
    }
  },
}

export function universePersisted<S>(name: FixedKey) {
  return {
    name,
    storage: createJSONStorage<S>(() => universeLocalStorage),
  }
}

type FollowingStore<S> = {
  getInitialState: () => S
  setState: (state: S, replace: true) => void
  persist: { rehydrate: () => Promise<void> | void }
}

export function followUniverse<S>(store: FollowingStore<S>): void {
  subscribeUniverse(() => {
    quiet = true
    try {
      store.setState(store.getInitialState(), true)
    } finally {
      quiet = false
    }
    void store.persist.rehydrate()
  })
}

function universeScoped(key: string): boolean {
  if (key.includes(SCOPE_MARK)) return false
  return (
    UNIVERSE_STORAGE_KEYS.some((item) => item === key) ||
    UNIVERSE_STORAGE_PREFIXES.some((prefix) => key.startsWith(prefix))
  )
}

export function adoptLegacyStorage(universeId: string): void {
  const storage = local()
  if (!storage) return
  try {
    const legacy = Array.from({ length: storage.length }, (_, index) =>
      storage.key(index)
    ).filter((key): key is string => key !== null && universeScoped(key))
    for (const key of legacy) {
      const target = scoped(key, universeId)
      const value = storage.getItem(key)
      if (value !== null && storage.getItem(target) === null)
        storage.setItem(target, value)
      storage.removeItem(key)
    }
  } catch {
    return
  }
}
