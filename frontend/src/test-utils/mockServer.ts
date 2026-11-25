import { installFetch } from './networkGuard'

export type MockRequest = {
  method: string
  path: string
  query: URLSearchParams
  headers: Headers
  body: unknown
}

export type MockReply = unknown | MockFailure

export class MockFailure {
  constructor(
    readonly status: number,
    readonly detail: string
  ) {}
}

export type MockHandler = (request: MockRequest) => MockReply

export type MockRoutes = Record<string, MockHandler | unknown>

export type MockServer = {
  calls: MockRequest[]
  callsTo: (key: string) => MockRequest[]
  stop: () => void
}

export function failure(status: number, detail: string): MockFailure {
  return new MockFailure(status, detail)
}

function compile(key: string): { method: string; pattern: RegExp } {
  const space = key.indexOf(' ')
  const method = key.slice(0, space)
  const path = key.slice(space + 1)
  const source = path
    .split(/(\{[^}]+\})/)
    .map((part) =>
      part.startsWith('{')
        ? '[^/]+'
        : part.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    )
    .join('')
  return { method, pattern: new RegExp(`^${source}$`) }
}

function jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

async function readBody(request: Request): Promise<unknown> {
  if (request.method === 'GET' || request.method === 'HEAD') return undefined
  const text = await request.text()
  if (!text) return undefined
  if (request.headers.get('content-type')?.includes('json'))
    return JSON.parse(text) as unknown
  return text
}

export function startMockServer(routes: MockRoutes): MockServer {
  const compiled = Object.entries(routes).map(([key, handler]) => ({
    key,
    ...compile(key),
    handler,
  }))
  const calls: MockRequest[] = []
  installFetch(async (input, init) => {
    const request = new Request(input as RequestInfo, init)
    const url = new URL(request.url)
    const mockRequest: MockRequest = {
      method: request.method,
      path: url.pathname,
      query: url.searchParams,
      headers: request.headers,
      body: await readBody(request),
    }
    calls.push(mockRequest)
    const route = compiled.find(
      (item) =>
        item.method === request.method && item.pattern.test(url.pathname)
    )
    if (!route) return jsonResponse({ detail: 'Not found' }, 404)
    const reply =
      typeof route.handler === 'function'
        ? (route.handler as MockHandler)(mockRequest)
        : route.handler
    if (reply instanceof MockFailure)
      return jsonResponse({ detail: reply.detail }, reply.status)
    return jsonResponse(reply ?? {}, 200)
  })
  return {
    calls,
    callsTo: (key) => {
      const { method, pattern } = compile(key)
      return calls.filter(
        (call) => call.method === method && pattern.test(call.path)
      )
    },
    stop: () => installFetch(null),
  }
}
