import { type StateStorage, createJSONStorage } from 'zustand/middleware'
import { currentAccountScope, subscribeAccountScope } from '@/api/accountScope'
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

export const VIEWER_STORAGE_KEYS = [
  'aerona.feed',
  'aerona.divine-will',
  'aerona.cards.view',
  'aerona.cards.guide',
  'aerona.cosmos.view',
  'aerona.cosmos.quality',
  'aerona.translation.average-ms',
] as const

type FixedKey = (typeof UNIVERSE_STORAGE_KEYS)[number]

export type ViewerStorageKey = (typeof VIEWER_STORAGE_KEYS)[number]

declare const SCOPED: unique symbol

export type ScopedKey = string & { readonly [SCOPED]: true }

export type UniversePrefixedKey =
  `${(typeof UNIVERSE_STORAGE_PREFIXES)[number]}${string}`

export type UniverseStorageKey = FixedKey | UniversePrefixedKey

const SCOPE_MARK = '@'
const ACCOUNT_MARK = '~'
const NO_UNIVERSE = 'none'
const NO_ACCOUNT = 'nobody'

let quiet = false

function owned(base: string, account: number | null): string {
  return `${base}${ACCOUNT_MARK}${account ?? NO_ACCOUNT}`
}

function scoped(base: string, universe: string | null): ScopedKey {
  return owned(
    `${base}${SCOPE_MARK}${universe ?? NO_UNIVERSE}`,
    currentAccountScope()
  ) as ScopedKey
}

export function universeKey(base: UniverseStorageKey): ScopedKey {
  return scoped(base, currentUniverse())
}

export function viewerKey(base: ViewerStorageKey): ScopedKey {
  return owned(base, currentAccountScope()) as ScopedKey
}

export function storedItem(key: ScopedKey): string | null {
  try {
    return local()?.getItem(key) ?? null
  } catch {
    return null
  }
}

export function storeItem(key: ScopedKey, value: string): void {
  try {
    local()?.setItem(key, value)
  } catch {
    return
  }
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

const viewerLocalStorage: StateStorage = {
  getItem: (name) => {
    try {
      return local()?.getItem(owned(name, currentAccountScope())) ?? null
    } catch {
      return null
    }
  },
  setItem: (name, value) => {
    if (quiet) return
    try {
      local()?.setItem(owned(name, currentAccountScope()), value)
    } catch {
      return
    }
  },
  removeItem: (name) => {
    if (quiet) return
    try {
      local()?.removeItem(owned(name, currentAccountScope()))
    } catch {
      return
    }
  },
}

export function viewerPersisted<S>(name: ViewerStorageKey) {
  return {
    name,
    storage: createJSONStorage<S>(() => viewerLocalStorage),
  }
}

type FollowingStore<S> = {
  getInitialState: () => S
  setState: (state: S, replace: true) => void
  persist: { rehydrate: () => Promise<void> | void }
}

function reload<S>(store: FollowingStore<S>): () => void {
  return () => {
    quiet = true
    try {
      store.setState(store.getInitialState(), true)
    } finally {
      quiet = false
    }
    void store.persist.rehydrate()
  }
}

export function followUniverse<S>(store: FollowingStore<S>): void {
  subscribeUniverse(reload(store))
  subscribeAccountScope(reload(store))
}

export function followViewer<S>(store: FollowingStore<S>): void {
  subscribeAccountScope(reload(store))
}

function universeScoped(key: string): boolean {
  if (key.includes(SCOPE_MARK) || key.includes(ACCOUNT_MARK)) return false
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

function unowned(key: string): boolean {
  if (key.includes(ACCOUNT_MARK)) return false
  const base = key.split(SCOPE_MARK)[0] ?? key
  return (
    VIEWER_STORAGE_KEYS.some((item) => item === key) ||
    UNIVERSE_STORAGE_KEYS.some((item) => item === base) ||
    UNIVERSE_STORAGE_PREFIXES.some((prefix) => base.startsWith(prefix))
  )
}

export function adoptViewerStorage(account: number): void {
  const storage = local()
  if (!storage) return
  try {
    const legacy = Array.from({ length: storage.length }, (_, index) =>
      storage.key(index)
    ).filter((key): key is string => key !== null && unowned(key))
    for (const key of legacy) {
      const target = owned(key, account)
      const value = storage.getItem(key)
      if (value !== null && storage.getItem(target) === null)
        storage.setItem(target, value)
      storage.removeItem(key)
    }
  } catch {
    return
  }
}
