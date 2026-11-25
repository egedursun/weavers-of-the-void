import { useQueryClient } from '@tanstack/react-query'
import { presenceExchangeOf, useAnyEvent, useEvent } from '@/realtime'
import { queryKeys } from '@/api/queryKeys'
import { usePresence } from './presenceStore'

type Payload = Record<string, unknown>

function textOf(payload: Payload, field: string): string {
  const value = payload[field]
  return typeof value === 'string' ? value : ''
}

export function usePresenceStream() {
  const client = useQueryClient()
  const refresh = () =>
    void client.invalidateQueries({
      queryKey: [...queryKeys.presence.all, 'session'],
    })

  useAnyEvent((event) => {
    const kind: string = event.kind
    const payload = event.payload as Payload
    const exchangeId = presenceExchangeOf(payload)
    if (exchangeId === null) return
    const live = usePresence.getState()
    const callId = textOf(payload, 'call_id')
    const tool = textOf(payload, 'tool')
    switch (kind) {
      case 'agent.stream':
        live.appendText(exchangeId, textOf(payload, 'text'))
        return
      case 'agent.thought':
        live.settleText(exchangeId)
        refresh()
        return
      case 'agent.tool_preparing':
        live.trackCall(exchangeId, { callId, tool, phase: 'preparing' })
        return
      case 'agent.tool_writing':
        live.trackCall(exchangeId, { callId, tool, phase: 'writing' })
        return
      case 'agent.tool_called':
        live.trackCall(exchangeId, { callId, tool, phase: 'called' })
        return
      case 'agent.tool_result':
        live.trackCall(exchangeId, {
          callId,
          phase: 'result',
          error: payload['error'] === true,
        })
        refresh()
        return
      case 'agent.retry':
        refresh()
        return
      default:
        return
    }
  })

  useEvent('presence.exchange_finished', (event) =>
    usePresence.getState().endLive(event.payload.exchange_id)
  )
}
