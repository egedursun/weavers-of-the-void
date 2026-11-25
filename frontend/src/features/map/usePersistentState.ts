import { useCallback, useState } from 'react'
import {
  storedItem,
  storeItem,
  type UniversePrefixedKey,
  universeKey,
} from '@/lib/universeStorage'

function readStored<T>(
  key: UniversePrefixedKey,
  fallback: T,
  valid: (value: unknown) => boolean
): T {
  try {
    const raw = storedItem(universeKey(key))
    if (raw === null) return fallback
    const parsed: unknown = JSON.parse(raw)
    return valid(parsed) ? (parsed as T) : fallback
  } catch {
    return fallback
  }
}

function writeStored(key: UniversePrefixedKey, value: unknown): void {
  try {
    storeItem(universeKey(key), JSON.stringify(value))
  } catch {
    return
  }
}

export function usePersistentState<T>(
  key: UniversePrefixedKey,
  fallback: T | (() => T),
  valid: (value: unknown) => boolean
): [T, (next: T | ((current: T) => T)) => void] {
  const [value, setValue] = useState<T>(() =>
    readStored(
      key,
      typeof fallback === 'function' ? (fallback as () => T)() : fallback,
      valid
    )
  )
  const update = useCallback(
    (next: T | ((current: T) => T)) =>
      setValue((current) => {
        const resolved =
          typeof next === 'function'
            ? (next as (current: T) => T)(current)
            : next
        writeStored(key, resolved)
        return resolved
      }),
    [key]
  )
  return [value, update]
}

export const isBoolean = (value: unknown) => typeof value === 'boolean'
export const isNumber = (value: unknown) => typeof value === 'number'
export const oneOf =
  (options: readonly string[]) =>
  (value: unknown): boolean =>
    typeof value === 'string' && options.includes(value)
export const isStringList = (value: unknown) =>
  Array.isArray(value) && value.every((item) => typeof item === 'string')

export const isDepthRecord = (value: unknown) =>
  typeof value === 'object' &&
  value !== null &&
  !Array.isArray(value) &&
  Object.values(value).every((item) => typeof item === 'string')
