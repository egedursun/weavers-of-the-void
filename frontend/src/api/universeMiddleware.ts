import { type Middleware } from 'openapi-fetch'
import {
  UNIVERSE_HEADER,
  currentUniverse,
  refuseUniverse,
} from './universeStore'
import { isLibraryApi } from './url'

const CONFLICT = 409
const REFUSAL_PREFIX = 'universe_'
const FALLBACK_REFUSAL = 'Choose a universe from the Library to continue.'

function messageOf(body: Record<string, unknown>): string | null {
  for (const key of ['error', 'message', 'detail'] as const) {
    const value = body[key]
    if (typeof value === 'string' && value.trim()) return value
  }
  return null
}

export function universeRefusal(body: unknown): string | null {
  if (!body || typeof body !== 'object') return null
  const record = body as Record<string, unknown>
  const detail = record['detail']
  const nested =
    detail && typeof detail === 'object'
      ? (detail as Record<string, unknown>)
      : null
  const code = record['code'] ?? nested?.['code']
  if (typeof code !== 'string' || !code.startsWith(REFUSAL_PREFIX)) return null
  return (
    (nested ? messageOf(nested) : null) ?? messageOf(record) ?? FALLBACK_REFUSAL
  )
}

export const universeMiddleware: Middleware = {
  onRequest({ request }) {
    const universe = currentUniverse()
    if (universe === null || request.headers.has(UNIVERSE_HEADER))
      return undefined
    if (isLibraryApi(new URL(request.url, window.location.origin).pathname))
      return undefined
    request.headers.set(UNIVERSE_HEADER, universe)
    return request
  },
  async onResponse({ response }) {
    if (response.status !== CONFLICT) return undefined
    const body: unknown = await response
      .clone()
      .json()
      .catch(() => null)
    const refusal = universeRefusal(body)
    if (refusal !== null) refuseUniverse(refusal)
    return undefined
  },
}
