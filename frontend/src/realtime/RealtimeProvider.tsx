import { type ReactNode, useEffect, useMemo, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { apiUrl } from '@/api/url'
import { createEventBus } from './eventBus'
import {
  EventStream,
  type EventSourceLike,
  type StreamStatus,
} from './eventStream'
import { applyServerEvent } from './invalidation'
import { RealtimeContext } from './realtimeContext'

type RealtimeProviderProps = {
  children: ReactNode
  url?: string
  createSource?: (url: string) => EventSourceLike
}

export function RealtimeProvider({
  children,
  url: givenUrl,
  createSource,
}: RealtimeProviderProps) {
  const url = givenUrl ?? apiUrl('/api/events')
  const queryClient = useQueryClient()
  const bus = useMemo(() => createEventBus(), [])
  const [status, setStatus] = useState<StreamStatus>('connecting')

  useEffect(() => {
    const stream = new EventStream({
      url,
      createSource,
      onStatus: setStatus,
      onEvent: (event) => {
        applyServerEvent(queryClient, event)
        bus.emit(event)
      },
      onResync: () => {
        void queryClient.invalidateQueries()
      },
    })
    stream.start()
    return () => stream.stop()
  }, [bus, createSource, queryClient, url])

  const value = useMemo(() => ({ bus, status }), [bus, status])
  return <RealtimeContext value={value}>{children}</RealtimeContext>
}
