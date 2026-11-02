import { REALTIME_RETRY_BASE_MS, REALTIME_RETRY_MAX_MS } from '@/constants/ui'
import { EVENT_KINDS, type ServerEvent, parseServerEvent } from './events'

export type StreamStatus = 'connecting' | 'open' | 'reconnecting' | 'closed'

export type EventSourceLike = {
  readonly readyState: number
  onopen: ((event: Event) => void) | null
  onerror: ((event: Event) => void) | null
  onmessage: ((event: MessageEvent<string>) => void) | null
  addEventListener: (
    type: string,
    listener: (event: MessageEvent<string>) => void
  ) => void
  close: () => void
}

export type EventStreamOptions = {
  url: string
  onEvent: (event: ServerEvent) => void
  onStatus?: (status: StreamStatus) => void
  onResync?: () => void
  createSource?: (url: string) => EventSourceLike
  retryBaseMs?: number
  retryMaxMs?: number
  schedule?: (callback: () => void, delayMs: number) => () => void
}

const CLOSED = 2

function defaultSchedule(callback: () => void, delayMs: number) {
  const handle = setTimeout(callback, delayMs)
  return () => clearTimeout(handle)
}

export function retryDelay(attempt: number, baseMs: number, maxMs: number) {
  return Math.min(maxMs, baseMs * 2 ** attempt)
}

export class EventStream {
  private source: EventSourceLike | null = null
  private attempt = 0
  private cancelRetry: (() => void) | null = null
  private stopped = true
  private hardReconnect = false
  private lastId = 0
  private readonly options: Required<
    Omit<EventStreamOptions, 'onStatus' | 'onResync'>
  > &
    Pick<EventStreamOptions, 'onStatus' | 'onResync'>

  constructor(options: EventStreamOptions) {
    this.options = {
      ...options,
      createSource:
        options.createSource ??
        ((url) => new EventSource(url) as EventSourceLike),
      retryBaseMs: options.retryBaseMs ?? REALTIME_RETRY_BASE_MS,
      retryMaxMs: options.retryMaxMs ?? REALTIME_RETRY_MAX_MS,
      schedule: options.schedule ?? defaultSchedule,
    }
  }

  get lastEventId(): number {
    return this.lastId
  }

  start(): void {
    if (!this.stopped) return
    this.stopped = false
    this.connect()
  }

  stop(): void {
    this.stopped = true
    this.cancelRetry?.()
    this.cancelRetry = null
    this.source?.close()
    this.source = null
    this.options.onStatus?.('closed')
  }

  private connect(): void {
    this.options.onStatus?.(this.hardReconnect ? 'reconnecting' : 'connecting')
    const source = this.options.createSource(this.options.url)
    this.source = source
    const receive = (message: MessageEvent<string>) => this.receive(message)
    source.onmessage = receive
    for (const kind of EVENT_KINDS) source.addEventListener(kind, receive)
    source.onopen = () => {
      this.attempt = 0
      this.options.onStatus?.('open')
      if (this.hardReconnect) {
        this.hardReconnect = false
        this.options.onResync?.()
      }
    }
    source.onerror = () => this.handleError(source)
  }

  private receive(message: MessageEvent<string>): void {
    const event = parseServerEvent(message.data)
    if (!event || event.id <= this.lastId) return
    this.lastId = event.id
    this.options.onEvent(event)
  }

  private handleError(source: EventSourceLike): void {
    if (this.stopped || source !== this.source) return
    if (source.readyState !== CLOSED) {
      this.options.onStatus?.('reconnecting')
      return
    }
    source.close()
    this.source = null
    this.hardReconnect = true
    this.options.onStatus?.('reconnecting')
    const delay = retryDelay(
      this.attempt,
      this.options.retryBaseMs,
      this.options.retryMaxMs
    )
    this.attempt += 1
    this.cancelRetry = this.options.schedule(() => {
      this.cancelRetry = null
      if (!this.stopped) this.connect()
    }, delay)
  }
}
