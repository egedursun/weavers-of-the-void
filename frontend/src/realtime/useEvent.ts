import { useEffect, useRef } from 'react'
import { type EventKind, type ServerEvent } from './events'
import { useRealtime } from './realtimeContext'

export function useEvent<K extends EventKind>(
  kind: K,
  handler: (event: ServerEvent<K>) => void
): void {
  const { bus } = useRealtime()
  const latest = useRef(handler)
  useEffect(() => {
    latest.current = handler
  })
  useEffect(() => bus.on(kind, (event) => latest.current(event)), [bus, kind])
}
