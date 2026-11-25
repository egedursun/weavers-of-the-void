import { useSyncExternalStore } from 'react'

export const UNIVERSE_HEADER = 'X-Aerona-Universe'
export const UNIVERSE_PARAM = 'universe'

const UNIVERSE_ID = /^[a-z0-9]{12}$/
const TAB_KEY = 'aerona.universe'
const LAST_KEY = 'aerona.universe.last'

type Shelf = 'session' | 'local'

function storageOf(shelf: Shelf): Storage | null {
  try {
    return shelf === 'session' ? window.sessionStorage : window.localStorage
  } catch {
    return null
  }
}

function readId(shelf: Shelf, key: string): string | null {
  try {
    const value = storageOf(shelf)?.getItem(key) ?? null
    return isUniverseId(value) ? value : null
  } catch {
    return null
  }
}

function writeId(shelf: Shelf, key: string, value: string | null): void {
  try {
    const storage = storageOf(shelf)
    if (value === null) storage?.removeItem(key)
    else storage?.setItem(key, value)
  } catch {
    return
  }
}

export function isUniverseId(value: unknown): value is string {
  return typeof value === 'string' && UNIVERSE_ID.test(value)
}

export function universeFromSearch(search: string): string | null {
  const value = new URLSearchParams(search).get(UNIVERSE_PARAM)
  return isUniverseId(value) ? value : null
}

function firstUniverse(): string | null {
  if (typeof window === 'undefined') return null
  return (
    universeFromSearch(window.location.search) ??
    readId('session', TAB_KEY) ??
    readId('local', LAST_KEY)
  )
}

let current: string | null = firstUniverse()
let documentUniverse: string | null = null
const listeners = new Set<() => void>()
const refusals = new Set<(message: string) => void>()
const refused = new Set<string>()

export function currentUniverse(): string | null {
  return current
}

export function lastUniverse(): string | null {
  return readId('local', LAST_KEY)
}

export function chooseUniverse(id: string | null): void {
  if (id !== null) refused.delete(id)
  writeId('session', TAB_KEY, id)
  if (id !== null) writeId('local', LAST_KEY, id)
  if (id === current) return
  current = id
  for (const listener of listeners) listener()
}

export function forgetUniverse(id: string): void {
  if (lastUniverse() === id) writeId('local', LAST_KEY, null)
  if (current === id) chooseUniverse(null)
}

export function subscribeUniverse(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function useUniverseId(): string | null {
  return useSyncExternalStore(
    subscribeUniverse,
    currentUniverse,
    currentUniverse
  )
}

export function documentHolder(): string | null {
  return documentUniverse
}

export function holdsDocument(id: string): boolean {
  if (documentUniverse === null) documentUniverse = id
  return documentUniverse === id
}

export function releaseDocument(): void {
  documentUniverse = null
}

export function onUniverseRefused(
  listener: (message: string) => void
): () => void {
  refusals.add(listener)
  return () => refusals.delete(listener)
}

export function wasRefused(id: string): boolean {
  return refused.has(id)
}

export function refuseUniverse(message: string): void {
  const gone = current
  if (gone !== null) {
    refused.add(gone)
    forgetUniverse(gone)
  }
  for (const listener of refusals) listener(message)
}
