import { useSyncExternalStore } from 'react'
import { type components } from './generated/schema'

export type Permission = components['schemas']['Permission']

export type TeamGate = {
  universe: string
  refusals: Partial<Record<Permission, string>>
  adminRefusal: string | null
}

let gate: TeamGate | null = null
let holds: ReadonlyMap<string, readonly string[]> = new Map()
const listeners = new Set<() => void>()

function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function setTeamGate(next: TeamGate | null): void {
  gate = next
  for (const listener of listeners) listener()
}

export function useTeamGate(): TeamGate | null {
  return useSyncExternalStore(
    subscribe,
    () => gate,
    () => null
  )
}

export function refusalIn(
  current: TeamGate | null,
  permission: Permission | null
): string | null {
  if (permission === null || current === null) return null
  return current.refusals[permission] ?? null
}

export function gateReason(permission: Permission | null): string | null {
  return refusalIn(gate, permission)
}

export function setHoldFields(
  next: ReadonlyMap<string, readonly string[]>
): void {
  holds = next
}

export function matches(template: string, path: string): boolean {
  if (!template.includes('{')) return template === path
  const parts = template.split('/')
  const given = path.split('/')
  return (
    parts.length === given.length &&
    parts.every((part, index) => part.startsWith('{') || part === given[index])
  )
}

export function holdFieldsAt(path: string): readonly string[] {
  const exact = holds.get(path)
  if (exact) return exact
  for (const [template, fields] of holds)
    if (matches(template, path)) return fields
  return []
}
