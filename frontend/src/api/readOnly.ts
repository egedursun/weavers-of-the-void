import { type Middleware } from 'openapi-fetch'

const READ_METHODS = new Set(['GET', 'HEAD', 'OPTIONS'])
const ALLOWED_PATHS = new Set(['/api/discovery/end'])
const READ_ONLY_STATUS = 409

export const READ_ONLY_MESSAGE =
  'You are browsing a guest world read-only. Return to your own world to change anything.'

let readOnly = false

export function setReadOnly(value: boolean): void {
  readOnly = value
}

export function isReadOnly(): boolean {
  return readOnly
}

export const readOnlyGuard: Middleware = {
  onRequest({ request }) {
    if (!readOnly || READ_METHODS.has(request.method)) return undefined
    if (ALLOWED_PATHS.has(new URL(request.url, window.location.origin).pathname))
      return undefined
    return new Response(JSON.stringify({ detail: READ_ONLY_MESSAGE }), {
      status: READ_ONLY_STATUS,
      headers: { 'content-type': 'application/json' },
    })
  },
}
