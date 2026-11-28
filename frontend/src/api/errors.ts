import { APP_NAME } from '@/config/brand'

export class ApiError extends Error {
  readonly status: number | null

  constructor(message: string, status: number | null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

const UNREACHABLE_MESSAGE = `The ${APP_NAME} server cannot be reached right now. It may be starting or restarting; try again in a moment.`

const SERVER_FAILED = 'The server failed to complete the request.'
const REFUSED = 'The server refused the request.'

const STATUS_MESSAGES: Record<number, string> = {
  400: 'The request was not valid.',
  404: 'The requested record does not exist.',
  409: 'The world changed in the meantime. Try again.',
  413: 'What was sent is too large for the server to take.',
  422: 'Some fields are not valid.',
  500: SERVER_FAILED,
  502: UNREACHABLE_MESSAGE,
  503: 'The server is not available right now. Try again in a moment.',
  504: 'The server took too long to answer. Try again in a moment.',
}

const SERVER_DOWN = new Set([502, 503, 504])

function detailOf(body: unknown): string | null {
  if (!body || typeof body !== 'object' || Array.isArray(body)) return null
  for (const key of ['error', 'detail'] as const) {
    const value = (body as Record<string, unknown>)[key]
    if (typeof value === 'string' && value.trim()) return value
  }
  return null
}

export function errorFromResponse(
  response: Response | undefined,
  body: unknown
): ApiError {
  if (!response) return new ApiError(UNREACHABLE_MESSAGE, null)
  const message =
    detailOf(body) ??
    STATUS_MESSAGES[response.status] ??
    (response.status >= 500 ? SERVER_FAILED : REFUSED)
  return new ApiError(message, response.status)
}

export function serverDown(error: unknown): boolean {
  if (!(error instanceof ApiError)) return false
  return error.status === null || SERVER_DOWN.has(error.status)
}

export async function unwrap<T>(
  request: Promise<{ data?: T; error?: unknown; response: Response }>
): Promise<T> {
  let result: { data?: T; error?: unknown; response: Response }
  try {
    result = await request
  } catch {
    throw errorFromResponse(undefined, null)
  }
  if (result.error !== undefined || !result.response.ok) {
    throw errorFromResponse(result.response, result.error)
  }
  return result.data as T
}
