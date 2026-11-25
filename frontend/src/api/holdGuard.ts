import { type Middleware } from 'openapi-fetch'
import { gateReason, holdFieldsAt } from './teamGate'

const HOLD = 'lock_canon'
const WRITES = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

export const holdGuard: Middleware = {
  async onRequest({ request }) {
    if (!WRITES.has(request.method) || gateReason(HOLD) === null)
      return undefined
    const path = new URL(request.url, window.location.origin).pathname
    const fields = holdFieldsAt(path)
    if (fields.length === 0) return undefined
    const text = await request.clone().text()
    if (!text) return undefined
    const body: unknown = JSON.parse(text)
    if (body === null || typeof body !== 'object' || Array.isArray(body))
      return undefined
    const record = body as Record<string, unknown>
    const held = fields.filter((field) => record[field] === true)
    if (held.length === 0) return undefined
    const cleared = { ...record }
    for (const field of held) cleared[field] = false
    return new Request(request, { body: JSON.stringify(cleared) })
  },
}
