import { useQueryClient } from '@tanstack/react-query'
import { useAnyEvent, useEvent, willCycleOf } from '@/realtime'
import { toast } from 'sonner'
import { useWillDock } from '@/components/layout/divine-will/dockStore'
import { willKeys } from './api'
import { type WillForecast } from './types'
import { useWill } from './willStore'

type Payload = Record<string, unknown>

function numberOf(payload: Payload, field: string): number | null {
  const value = payload[field]
  return typeof value === 'number' ? value : null
}

function textOf(payload: Payload, field: string): string {
  const value = payload[field]
  return typeof value === 'string' ? value : ''
}

function inputOf(payload: Payload): Record<string, unknown> | null {
  const value = payload['input']
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null
}

export function useWillStream() {
  const client = useQueryClient()
  const refreshCycle = (cycleId: number) =>
    void client.invalidateQueries({ queryKey: willKeys.cycle(cycleId) })

  useAnyEvent((event) => {
    const kind: string = event.kind
    if (!kind.startsWith('agent.')) return
    const payload = event.payload as Payload
    const cycleId = willCycleOf(payload)
    if (cycleId === null) return
    const live = useWill.getState()
    const callId = textOf(payload, 'call_id')
    const tool = textOf(payload, 'tool')
    switch (kind) {
      case 'agent.stream':
        live.appendText(cycleId, textOf(payload, 'text'))
        return
      case 'agent.thought':
        live.settleText(cycleId)
        refreshCycle(cycleId)
        return
      case 'agent.tool_preparing':
        live.trackTool(cycleId, { callId, tool, phase: 'preparing' })
        return
      case 'agent.tool_writing':
        live.trackTool(cycleId, {
          callId,
          tool,
          phase: 'writing',
          chars: numberOf(payload, 'chars') ?? 0,
        })
        return
      case 'agent.tool_called':
        live.trackTool(cycleId, {
          callId,
          tool,
          phase: 'called',
          input: inputOf(payload),
        })
        return
      case 'agent.tool_result':
        live.trackTool(cycleId, {
          callId,
          phase: 'result',
          error: payload['error'] === true,
        })
        refreshCycle(cycleId)
        return
      default:
        return
    }
  })

  useEvent('divine_will.cycle_finished', (event) => {
    const live = useWill.getState()
    live.endLive(event.payload.cycle_id)
    if (!useWillDock.getState().open) live.addUnread()
  })

  useEvent('divine_will.forecast_progress', (event) => {
    const { forecast_id, done_epochs, eta_seconds, progress, status } =
      event.payload
    useWill.getState().setForesight(forecast_id, progress ?? 0)
    client.setQueryData(
      willKeys.forecast(forecast_id),
      (current: WillForecast | undefined) =>
        current && {
          ...current,
          status,
          epochs_done: done_epochs ?? current.epochs_done,
          eta_seconds: eta_seconds || current.eta_seconds,
        }
    )
  })

  useEvent('divine_will.confirmation_requested', () => {
    if (useWillDock.getState().open) return
    useWill.getState().addUnread()
    toast.warning('The Divine Will waits for your approval', {
      description: 'An act needs your word before it runs.',
      action: {
        label: 'Open',
        onClick: () => useWillDock.getState().setOpen(true),
      },
    })
  })
}
