import { useSyncExternalStore } from 'react'
import { type Middleware } from 'openapi-fetch'
import { takeReason } from './actReason'
import { pinnedRevision, settleEdit } from './editSession'
import { type components } from './generated/schema'

export type ConflictChange = components['schemas']['EditConflictChange']

export type Choice = 'theirs' | 'mine'

export type PendingConflict = {
  message: string
  changes: ConflictChange[]
  mine: Record<string, unknown>
  decide: (choice: Choice) => void
}

const WRITES = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])
const OUTSIDE = /^\/api\/(library|auth|accounts|workspaces|team|presence)(\/|$)/
const CONFLICT = 409
const CONFLICT_CODE = 'edit_conflict'
const KEPT_CODE = 'edit_kept'
const KEPT_MESSAGE = 'You kept their change; yours was not applied.'
const REASON_PARAM = 'reason'
const REVISION_PARAM = 'expected_revision'

let pending: PendingConflict | null = null
const listeners = new Set<() => void>()
const originals = new WeakMap<Request, Request>()

function changed(): void {
  for (const listener of listeners) listener()
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function usePendingConflict(): PendingConflict | null {
  return useSyncExternalStore(
    subscribe,
    () => pending,
    () => null
  )
}

function ask(next: Omit<PendingConflict, 'decide'>): Promise<Choice> {
  return new Promise((resolve) => {
    pending = {
      ...next,
      decide: (choice) => {
        pending = null
        changed()
        resolve(choice)
      },
    }
    changed()
  })
}

function bodyOf(text: string): Record<string, unknown> {
  try {
    const value: unknown = JSON.parse(text)
    return value !== null && typeof value === 'object' && !Array.isArray(value)
      ? (value as Record<string, unknown>)
      : {}
  } catch {
    return {}
  }
}

function conflictOf(
  body: unknown
): { message: string; changes: ConflictChange[] } | null {
  if (body === null || typeof body !== 'object') return null
  const record = body as Record<string, unknown>
  if (record['code'] !== CONFLICT_CODE || !Array.isArray(record['changes']))
    return null
  return {
    message: typeof record['error'] === 'string' ? record['error'] : '',
    changes: record['changes'] as ConflictChange[],
  }
}

function kept(): Response {
  return new Response(
    JSON.stringify({ error: KEPT_MESSAGE, code: KEPT_CODE }),
    { status: CONFLICT, headers: { 'content-type': 'application/json' } }
  )
}

export const actNoteMiddleware: Middleware = {
  onRequest({ request }) {
    if (!WRITES.has(request.method)) return undefined
    const url = new URL(request.url, window.location.origin)
    if (OUTSIDE.test(url.pathname)) return undefined
    const reason = takeReason()
    const revision = pinnedRevision()
    if (reason === null && revision === null) return undefined
    if (reason !== null) url.searchParams.set(REASON_PARAM, reason)
    if (revision !== null)
      url.searchParams.set(REVISION_PARAM, String(revision))
    const next = new Request(url, request)
    originals.set(next, next.clone())
    return next
  },
  async onResponse({ request, response }) {
    const original = originals.get(request)
    if (!original) return undefined
    originals.delete(request)
    if (response.ok) {
      settleEdit()
      return undefined
    }
    if (response.status !== CONFLICT) return undefined
    const conflict = conflictOf(
      await response
        .clone()
        .json()
        .catch(() => null)
    )
    if (conflict === null) return undefined
    const sent = await original.clone().text()
    const choice = await ask({ ...conflict, mine: bodyOf(sent) })
    if (choice === 'theirs') {
      settleEdit()
      return kept()
    }
    const url = new URL(original.url)
    url.searchParams.delete(REVISION_PARAM)
    const retried = await globalThis.fetch(new Request(url, original))
    if (retried.ok) settleEdit()
    return retried
  },
}
