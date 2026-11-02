import { type EventSourceLike } from '@/realtime/eventStream'

type Listener = (event: MessageEvent<string>) => void

export class FakeEventSource implements EventSourceLike {
  static instances: FakeEventSource[] = []
  readyState = 0
  onopen: ((event: Event) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  onmessage: ((event: MessageEvent<string>) => void) | null = null
  readonly url: string
  readonly listeners = new Map<string, Listener[]>()
  closed = false

  constructor(url: string) {
    this.url = url
    FakeEventSource.instances.push(this)
  }

  addEventListener(type: string, listener: Listener) {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), listener])
  }

  close() {
    this.closed = true
    this.readyState = 2
  }

  open() {
    this.readyState = 1
    this.onopen?.(new Event('open'))
  }

  emit(kind: string, data: unknown) {
    const message = new MessageEvent<string>(kind, {
      data: JSON.stringify(data),
    })
    for (const listener of this.listeners.get(kind) ?? []) listener(message)
  }

  fail(readyState: number) {
    this.readyState = readyState
    this.onerror?.(new Event('error'))
  }

  static reset() {
    FakeEventSource.instances = []
  }

  static latest(): FakeEventSource {
    const latest = FakeEventSource.instances.at(-1)
    if (!latest) throw new Error('No event source was created')
    return latest
  }
}

export function serverEvent(id: number, kind: string, payload: unknown) {
  return { id, kind, payload, at: '2026-01-01T00:00:00+00:00' }
}
