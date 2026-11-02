import { useCallback, useState } from 'react'

function readStored<T>(
  key: string,
  fallback: T,
  valid: (value: unknown) => boolean
): T {
  try {
    const raw = window.localStorage.getItem(key)
    if (raw === null) return fallback
    const parsed: unknown = JSON.parse(raw)
    return valid(parsed) ? (parsed as T) : fallback
  } catch {
    return fallback
  }
}

function writeStored(key: string, value: unknown): void {
  try {
    window.localStorage.setItem(key, JSON.stringify(value))
  } catch {
    return
  }
}

export function usePersistentState<T>(
  key: string,
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
