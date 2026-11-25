import { useSyncExternalStore } from 'react'

const IDLE_MS = 20_000
const FIELD =
  'input, textarea, select, [role="combobox"], [contenteditable="true"]'

let revision: number | null = null
let pinned: number | null = null
let editing = false
let idleTimer: ReturnType<typeof setTimeout> | null = null
const listeners = new Set<() => void>()

function changed(): void {
  for (const listener of listeners) listener()
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

const AWAITING = -1

export function noteRevision(next: number): void {
  revision = next
  if (pinned === AWAITING) pinned = next
}

export function pinnedRevision(): number | null {
  return pinned === AWAITING ? null : pinned
}

export function settleEdit(): void {
  pinned = editing ? AWAITING : null
}

function stop(): void {
  if (idleTimer !== null) clearTimeout(idleTimer)
  idleTimer = null
  pinned = null
  if (editing) {
    editing = false
    changed()
  }
}

function focusIn(event: FocusEvent): void {
  const target = event.target
  if (!(target instanceof Element) || !target.closest(FIELD)) return
  if (target.closest('[data-presence="free"]')) return
  if (idleTimer !== null) clearTimeout(idleTimer)
  idleTimer = null
  pinned ??= revision
  if (!editing) {
    editing = true
    changed()
  }
}

function focusOut(): void {
  if (idleTimer !== null) clearTimeout(idleTimer)
  idleTimer = setTimeout(() => {
    const active = document.activeElement
    if (active instanceof Element && active.closest(FIELD)) return
    stop()
  }, IDLE_MS)
}

export function watchEditing(): () => void {
  document.addEventListener('focusin', focusIn)
  document.addEventListener('focusout', focusOut)
  return () => {
    document.removeEventListener('focusin', focusIn)
    document.removeEventListener('focusout', focusOut)
    stop()
  }
}

export function useEditing(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => editing,
    () => false
  )
}
