import { useSyncExternalStore } from 'react'

export const WORKSPACE_HEADER = 'X-Aerona-Workspace'
export const WORKSPACE_PARAM = 'workspace'

const WORKSPACE_ID = /^[A-Za-z0-9_-]{1,64}$/
const TAB_KEY = 'aerona.workspace'
const LAST_KEY = 'aerona.workspace.last'

type Shelf = 'session' | 'local'

function storageOf(shelf: Shelf): Storage | null {
  try {
    return shelf === 'session' ? window.sessionStorage : window.localStorage
  } catch {
    return null
  }
}

export function isWorkspaceId(value: unknown): value is string {
  return typeof value === 'string' && WORKSPACE_ID.test(value)
}

function readId(shelf: Shelf, key: string): string | null {
  try {
    const value = storageOf(shelf)?.getItem(key) ?? null
    return isWorkspaceId(value) ? value : null
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

export function workspaceFromSearch(search: string): string | null {
  const value = new URLSearchParams(search).get(WORKSPACE_PARAM)
  return isWorkspaceId(value) ? value : null
}

function firstWorkspace(): string | null {
  if (typeof window === 'undefined') return null
  return (
    workspaceFromSearch(window.location.search) ??
    readId('session', TAB_KEY) ??
    readId('local', LAST_KEY)
  )
}

let current: string | null = firstWorkspace()
const listeners = new Set<() => void>()

export function currentWorkspace(): string | null {
  return current
}

export function chooseWorkspace(id: string | null): void {
  writeId('session', TAB_KEY, id)
  if (id !== null) writeId('local', LAST_KEY, id)
  if (id === current) return
  current = id
  for (const listener of listeners) listener()
}

export function subscribeWorkspace(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function useWorkspaceId(): string | null {
  return useSyncExternalStore(
    subscribeWorkspace,
    currentWorkspace,
    currentWorkspace
  )
}

export function forgetLastWorkspace(): void {
  writeId('local', LAST_KEY, null)
}
