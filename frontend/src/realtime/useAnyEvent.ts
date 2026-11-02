import { useEffect, useRef } from 'react'
import { type ServerEvent } from './events'
import { useRealtime } from './realtimeContext'

export function useAnyEvent(handler: (event: ServerEvent) => void): void {
  const { bus } = useRealtime()
  const latest = useRef(handler)
  useEffect(() => {
    latest.current = handler
  })
  useEffect(() => bus.onAny((event) => latest.current(event)), [bus])
}
