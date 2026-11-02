import { type EventKind, type ServerEvent } from './events'

type Handler<K extends EventKind> = (event: ServerEvent<K>) => void
type AnyHandler = (event: ServerEvent) => void

export type EventBus = {
  emit: (event: ServerEvent) => void
  on: <K extends EventKind>(kind: K, handler: Handler<K>) => () => void
  onAny: (handler: AnyHandler) => () => void
}

export function createEventBus(): EventBus {
  const byKind = new Map<EventKind, Set<AnyHandler>>()
  const any = new Set<AnyHandler>()

  return {
    emit(event) {
      byKind.get(event.kind)?.forEach((handler) => handler(event))
      any.forEach((handler) => handler(event))
    },
    on(kind, handler) {
      const handlers = byKind.get(kind) ?? new Set<AnyHandler>()
      const wrapped = handler as AnyHandler
      handlers.add(wrapped)
      byKind.set(kind, handlers)
      return () => {
        handlers.delete(wrapped)
      }
    },
    onAny(handler) {
      any.add(handler)
      return () => {
        any.delete(handler)
      }
    },
  }
}
