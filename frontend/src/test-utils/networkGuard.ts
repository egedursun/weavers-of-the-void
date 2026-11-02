type FetchLike = typeof fetch

type GuardState = {
  handler: FetchLike | null
  violations: string[]
  realFetch: FetchLike
  realXhr: typeof XMLHttpRequest
  realWebSocket: typeof WebSocket
}

const STATE_KEY = Symbol.for('aerona.test.networkGuard')
const BLOCKED_STATUS = 599
const API_PREFIX = '/api'

type GuardedGlobal = typeof globalThis & { [STATE_KEY]?: GuardState }

function guardState(): GuardState {
  const scope = globalThis as GuardedGlobal
  const existing = scope[STATE_KEY]
  if (existing) return existing
  const created: GuardState = {
    handler: null,
    violations: [],
    realFetch: globalThis.fetch.bind(globalThis),
    realXhr: globalThis.XMLHttpRequest,
    realWebSocket: globalThis.WebSocket,
  }
  scope[STATE_KEY] = created
  return created
}

function urlOf(input: RequestInfo | URL): URL {
  if (input instanceof Request) return new URL(input.url, window.location.origin)
  return new URL(String(input), window.location.origin)
}

export function isGuardedUrl(url: URL): boolean {
  return (
    url.host !== window.location.host || url.pathname.startsWith(API_PREFIX)
  )
}

function guardedTarget(target: string | URL): URL | null {
  const url = new URL(String(target), window.location.origin)
  return isGuardedUrl(url) ? url : null
}

function record(kind: string, url: string): void {
  guardState().violations.push(`${kind} ${url}`)
}

function blockedResponse(url: string): Response {
  return new Response(
    JSON.stringify({ detail: `Network access is blocked in tests: ${url}` }),
    { status: BLOCKED_STATUS, headers: { 'content-type': 'application/json' } }
  )
}

class BlockedEventSource extends EventTarget {
  static readonly CONNECTING = 0
  static readonly OPEN = 1
  static readonly CLOSED = 2
  readonly CONNECTING = 0
  readonly OPEN = 1
  readonly CLOSED = 2
  readonly url: string
  readonly withCredentials = false
  readyState = 2
  onopen: ((event: Event) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null

  constructor(url: string | URL) {
    super()
    this.url = String(url)
    record('EventSource', this.url)
  }

  close(): void {
    this.readyState = 2
  }
}

function guardedXhr(RealXhr: typeof XMLHttpRequest): typeof XMLHttpRequest {
  return class GuardedXMLHttpRequest extends RealXhr {
    private blocked = false

    override open(
      method: string,
      url: string | URL,
      async: boolean = true,
      username?: string | null,
      password?: string | null
    ): void {
      const target = guardedTarget(url)
      if (target) {
        this.blocked = true
        record('xhr', target.href)
      }
      super.open(method, target ? 'about:blank' : url, async, username, password)
    }

    override send(body?: Document | XMLHttpRequestBodyInit | null): void {
      if (this.blocked) return
      super.send(body)
    }
  }
}

function guardedWebSocket(RealSocket: typeof WebSocket): typeof WebSocket {
  return class GuardedWebSocket extends RealSocket {
    constructor(url: string | URL, protocols?: string | string[]) {
      const target = guardedTarget(url)
      if (target) {
        record('websocket', target.href)
        throw new DOMException(
          `Network access is blocked in tests: ${target.href}`,
          'SecurityError'
        )
      }
      super(url, protocols)
    }
  }
}

const guardedFetch: FetchLike = (input, init) => {
  const state = guardState()
  if (state.handler) return state.handler(input, init)
  const url = urlOf(input)
  if (!isGuardedUrl(url)) return state.realFetch(input, init)
  record('fetch', url.href)
  return Promise.resolve(blockedResponse(url.href))
}

export function installNetworkGuard(): void {
  const state = guardState()
  globalThis.fetch = guardedFetch
  globalThis.EventSource = BlockedEventSource as unknown as typeof EventSource
  globalThis.XMLHttpRequest = guardedXhr(state.realXhr)
  globalThis.WebSocket = guardedWebSocket(state.realWebSocket)
  if (typeof navigator.sendBeacon === 'function')
    navigator.sendBeacon = (url) => {
      record('beacon', String(url))
      return false
    }
}

export function installFetch(handler: FetchLike | null): void {
  guardState().handler = handler
}

export function takeNetworkViolations(): string[] {
  const state = guardState()
  const taken = [...state.violations]
  state.violations.length = 0
  return taken
}
