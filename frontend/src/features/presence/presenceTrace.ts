import { type LiveCall, type LiveExchange } from './presenceStore'
import { type PresenceEvent, type PresenceExchange } from './types'

type Payload = Record<string, unknown>

export type CallTrace = {
  key: string
  tool: string
  input: Payload
  result: string
  outcome: string
  failed: boolean
  done: boolean
}

export type PresenceTraceItem =
  | { type: 'thoughts'; key: string; texts: string[] }
  | { type: 'text'; key: string; text: string }
  | { type: 'call'; key: string; trace: CallTrace }
  | {
      type: 'retry'
      key: string
      attempt: number
      total: number
      reason: string
      waitSeconds: number
    }
  | { type: 'error'; key: string; text: string }
  | { type: 'live-call'; key: string; call: LiveCall }
  | { type: 'streaming'; key: string; text: string }

const TOOL_PREFIX = /^.*__/

export function shortTool(name: string): string {
  return name.replace(TOOL_PREFIX, '')
}

function textField(payload: Payload, field: string): string {
  const value = payload[field]
  return typeof value === 'string' ? value : ''
}

function numberField(payload: Payload, field: string): number | null {
  const value = payload[field]
  return typeof value === 'number' ? value : null
}

function objectField(payload: Payload, field: string): Payload {
  const value = payload[field]
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Payload)
    : {}
}

function callOf(event: PresenceEvent): string {
  return textField(event.payload, 'call_id')
}

function newTrace(event: PresenceEvent): CallTrace {
  const input = objectField(event.payload, 'arguments')
  return {
    key: `call-${String(event.id)}`,
    tool: event.tool,
    input,
    result: '',
    outcome: '',
    failed: false,
    done: false,
  }
}

function settle(trace: CallTrace, event: PresenceEvent): CallTrace {
  const payload = event.payload
  return {
    ...trace,
    tool: trace.tool || event.tool,
    result: textField(payload, 'text'),
    outcome: textField(payload, 'outcome'),
    failed: payload['is_error'] === true,
    done: true,
  }
}

function lastCallEvent(exchange: PresenceExchange): number {
  let found = -1
  exchange.events.forEach((event, index) => {
    if (event.kind === 'tool_call' || event.kind === 'tool_result')
      found = index
  })
  return found
}

export function traceOfExchange(
  exchange: PresenceExchange,
  live: LiveExchange | null
): PresenceTraceItem[] {
  const items: PresenceTraceItem[] = []
  const open = new Map<string, number>()
  const persisted = new Set<string>()
  const finalFrom = exchange.reply_text.trim()
    ? lastCallEvent(exchange)
    : exchange.events.length
  exchange.events.forEach((event, index) => {
    const payload = event.payload
    const key = `event-${String(event.id)}`
    switch (event.kind) {
      case 'thought': {
        const text = textField(payload, 'text')
        if (!text.trim()) return
        const last = items.at(-1)
        if (last?.type === 'thoughts') last.texts.push(text)
        else items.push({ type: 'thoughts', key, texts: [text] })
        return
      }
      case 'text': {
        const text = textField(payload, 'text')
        if (text.trim() && index < finalFrom)
          items.push({ type: 'text', key, text })
        return
      }
      case 'tool_call': {
        const trace = newTrace(event)
        persisted.add(callOf(event))
        open.set(callOf(event) || trace.key, items.length)
        items.push({ type: 'call', key: trace.key, trace })
        return
      }
      case 'tool_result': {
        const position = open.get(callOf(event))
        const item = position === undefined ? undefined : items[position]
        if (item?.type === 'call' && position !== undefined) {
          items[position] = { ...item, trace: settle(item.trace, event) }
          open.delete(callOf(event))
        } else {
          const trace = settle(newTrace(event), event)
          items.push({ type: 'call', key: trace.key, trace })
        }
        return
      }
      case 'retry':
        items.push({
          type: 'retry',
          key,
          attempt: numberField(payload, 'attempt') ?? 1,
          total: numberField(payload, 'total') ?? 1,
          reason: textField(payload, 'reason'),
          waitSeconds: numberField(payload, 'wait_s') ?? 0,
        })
        return
      case 'error':
        items.push({ type: 'error', key, text: textField(payload, 'text') })
        return
    }
  })
  if (live) {
    for (const call of live.calls)
      if (call.phase !== 'result' && !persisted.has(call.callId))
        items.push({ type: 'live-call', key: `live-${call.callId}`, call })
    if (live.text)
      items.push({ type: 'streaming', key: 'streaming', text: live.text })
  }
  return items
}
