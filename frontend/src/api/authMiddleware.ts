import { type Middleware } from 'openapi-fetch'
import { toast } from 'sonner'
import { type AuthSignal, raiseAuthSignal } from './authSignals'
import { WORKSPACE_HEADER, currentWorkspace } from './workspaceStore'

const SIGNED_OUT = 401
const FORBIDDEN = 403
const CONFLICT = 409
const FORBIDDEN_TOAST = 'forbidden'
const SIGNALS: Record<string, AuthSignal> = {
  signed_out: 'signed_out',
  password_change_required: 'password_change_required',
  setup_required: 'setup_required',
}

type Refusal = {
  code: string | null
  message: string | null
  permission: string | null
  role: string | null
}

function text(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null
}

export function refusalOf(body: unknown): Refusal {
  const record =
    body && typeof body === 'object' ? (body as Record<string, unknown>) : {}
  const detail = record['detail']
  const nested =
    detail && typeof detail === 'object'
      ? (detail as Record<string, unknown>)
      : {}
  const pick = (key: string) => text(nested[key]) ?? text(record[key])
  return {
    code: pick('code'),
    message: pick('error') ?? pick('message') ?? text(detail),
    permission: pick('permission'),
    role: pick('role'),
  }
}

export function forbiddenMessage(refusal: Refusal): string {
  if (refusal.message) return refusal.message
  if (refusal.role && refusal.permission)
    return `Your role (${refusal.role}) does not allow this.`
  return 'Your role does not allow this.'
}

export const authMiddleware: Middleware = {
  onRequest({ request }) {
    const workspace = currentWorkspace()
    if (workspace === null || request.headers.has(WORKSPACE_HEADER))
      return undefined
    request.headers.set(WORKSPACE_HEADER, workspace)
    return request
  },
  async onResponse({ response }) {
    if (
      response.status !== SIGNED_OUT &&
      response.status !== FORBIDDEN &&
      response.status !== CONFLICT
    )
      return undefined
    const body: unknown = await response
      .clone()
      .json()
      .catch(() => null)
    const refusal = refusalOf(body)
    const signal = refusal.code === null ? undefined : SIGNALS[refusal.code]
    if (signal !== undefined) raiseAuthSignal(signal)
    else if (response.status === SIGNED_OUT) raiseAuthSignal('signed_out')
    else if (refusal.code === FORBIDDEN_TOAST)
      toast.error(forbiddenMessage(refusal), { id: FORBIDDEN_TOAST })
    return undefined
  },
}
