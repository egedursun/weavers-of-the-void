import { createContext, useContext } from 'react'
import { type EventBus } from './eventBus'
import { type StreamStatus } from './eventStream'

export type RealtimeContextValue = {
  bus: EventBus
  status: StreamStatus
}

export const RealtimeContext = createContext<RealtimeContextValue | null>(null)

export function useRealtime(): RealtimeContextValue {
  const context = useContext(RealtimeContext)
  if (!context)
    throw new Error('useRealtime must be used within RealtimeProvider')
  return context
}

export function useRealtimeStatus(): StreamStatus {
  return useRealtime().status
}
