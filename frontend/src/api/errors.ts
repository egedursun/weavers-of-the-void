export class ApiError extends Error {
  readonly status: number | null

  constructor(message: string, status: number | null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

const STATUS_MESSAGES: Record<number, string> = {
  400: 'The request was not valid.',
  404: 'The requested record does not exist.',
  409: 'The world changed in the meantime. Try again.',
  422: 'Some fields are not valid.',
  500: 'The server failed to complete the request.',
  503: 'The server is not available right now.',
}

const UNREACHABLE_MESSAGE = 'The Weavers of the Void server cannot be reached.'

function detailOf(body: unknown): string | null {
  if (typeof body === 'string' && body.trim()) return body
  if (body && typeof body === 'object') {
    for (const key of ['error', 'detail'] as const) {
      const value = (body as Record<string, unknown>)[key]
      if (typeof value === 'string' && value.trim()) return value
    }
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
    `Request failed with status ${response.status}.`
  return new ApiError(message, response.status)
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
