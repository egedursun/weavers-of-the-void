import { isMode } from './modes'
import {
  type CycleNotice,
  type DivineWillMode,
  type WillConfirmation,
  type WillCycle,
  type WillCycleEvent,
} from './types'
import { type LiveCycle, type LiveTool } from './willStore'

type Payload = Record<string, unknown>

export type ToolTrace = {
  key: string
  tool: string
  input: Payload
  details: Payload
  actionId: string
  outcome: string
  detail: string
  essence: number
  ledgerEntryId: number | null
  failed: boolean
  handle: string
  done: boolean
}

export type ConfirmationReply = {
  decision: string
  ok: boolean
  text: string
  essence: number
  jobId: string
}

export type TraceItem =
  | { type: 'thoughts'; key: string; texts: string[] }
  | { type: 'text'; key: string; text: string }
  | { type: 'tool'; key: string; trace: ToolTrace }
  | {
      type: 'confirmation'
      key: string
      confirmation: WillConfirmation
      reply: ConfirmationReply | null
    }
  | { type: 'plan'; key: string; planId: number }
  | { type: 'forecast'; key: string; forecastId: number }
  | { type: 'artifact'; key: string; artifactId: number; version: number }
  | {
      type: 'suggest'
      key: string
      mode: DivineWillMode
      reason: string
    }
  | { type: 'notice'; key: string; text: string; vision: boolean }
  | {
      type: 'retry'
      key: string
      attempt: number
      total: number
      reason: string
      waitSeconds: number
    }
  | { type: 'error'; key: string; text: string }
  | { type: 'live-tool'; key: string; tool: LiveTool }
  | { type: 'streaming'; key: string; text: string }

const SUGGEST_NOTICE: CycleNotice = 'suggest_mode'
const VISION_NOTICE: CycleNotice = 'vision_unavailable'

export function textField(payload: Payload, field: string): string {
  const value = payload[field]
  return typeof value === 'string' ? value : ''
}

export function numberField(payload: Payload, field: string): number | null {
  const value = payload[field]
  return typeof value === 'number' ? value : null
}

export function objectField(payload: Payload, field: string): Payload {
  const value = payload[field]
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Payload)
    : {}
}

function callOf(event: WillCycleEvent): string {
  return textField(event.payload, 'call_id')
}

function newTrace(event: WillCycleEvent): ToolTrace {
  const input = objectField(event.payload, 'arguments')
  return {
    key: `tool-${String(event.id)}`,
    tool: event.tool,
    input,
    details: {},
    actionId: textField(input, 'action_id'),
    outcome: '',
    detail: '',
    essence: 0,
    ledgerEntryId: null,
    failed: false,
    handle: '',
    done: false,
  }
}

function settle(trace: ToolTrace, event: WillCycleEvent): ToolTrace {
  const payload = event.payload
  const details = objectField(payload, 'details')
  return {
    ...trace,
    tool: trace.tool || event.tool,
    details,
    actionId: trace.actionId || textField(details, 'action_id'),
    outcome: textField(payload, 'outcome'),
    detail: textField(payload, 'text'),
    essence: numberField(details, 'essence') ?? 0,
    ledgerEntryId: numberField(details, 'ledger_entry_id'),
    failed: payload['is_error'] === true,
    handle: event.handle,
    done: true,
  }
}

function lastToolEvent(cycle: WillCycle): number {
  let found = -1
  cycle.events.forEach((event, index) => {
    if (event.kind === 'tool_call' || event.kind === 'tool_result')
      found = index
  })
  return found
}

function replies(cycle: WillCycle): Map<number, ConfirmationReply> {
  const found = new Map<number, ConfirmationReply>()
  for (const event of cycle.events) {
    if (event.kind !== 'confirmation_reply') continue
    const id = numberField(event.payload, 'confirmation_id')
    if (id === null) continue
    found.set(id, {
      decision: textField(event.payload, 'decision'),
      ok: event.payload['ok'] !== false,
      text: textField(event.payload, 'text'),
      essence: numberField(event.payload, 'essence') ?? 0,
      jobId: textField(event.payload, 'job_id'),
    })
  }
  return found
}

function results(trace: ToolTrace): TraceItem[] {
  const planId = numberField(trace.details, 'plan_id')
  const forecastId = numberField(trace.details, 'forecast_id')
  const artifactId = numberField(trace.details, 'artifact_id')
  const found: TraceItem[] = []
  if (planId !== null)
    found.push({ type: 'plan', key: `plan-${String(planId)}`, planId })
  else if (artifactId !== null)
    found.push({
      type: 'artifact',
      key: `artifact-${trace.key}`,
      artifactId,
      version: numberField(trace.details, 'version') ?? 0,
    })
  if (forecastId !== null)
    found.push({
      type: 'forecast',
      key: `forecast-${String(forecastId)}`,
      forecastId,
    })
  return found
}

export function traceOf(cycle: WillCycle, live: LiveCycle | null): TraceItem[] {
  const items: TraceItem[] = []
  const open = new Map<string, number>()
  const shown = new Set<number>()
  const seenCards = new Set<string>()
  const persistedCalls = new Set<string>()
  const answered = replies(cycle)
  const finalFrom = cycle.final_text.trim()
    ? lastToolEvent(cycle)
    : cycle.events.length
  const confirmationItem = (
    confirmation: WillConfirmation,
    key: string
  ): TraceItem => ({
    type: 'confirmation',
    key,
    confirmation,
    reply: answered.get(confirmation.id) ?? null,
  })
  cycle.events.forEach((event, index) => {
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
        persistedCalls.add(callOf(event))
        open.set(callOf(event) || trace.key, items.length)
        items.push({ type: 'tool', key: trace.key, trace })
        return
      }
      case 'tool_result': {
        const position = open.get(callOf(event))
        const item = position === undefined ? undefined : items[position]
        const trace =
          item?.type === 'tool'
            ? settle(item.trace, event)
            : settle(newTrace(event), event)
        if (item?.type === 'tool' && position !== undefined) {
          items[position] = { ...item, trace }
          open.delete(callOf(event))
        } else items.push({ type: 'tool', key: trace.key, trace })
        for (const card of results(trace))
          if (!seenCards.has(card.key)) {
            seenCards.add(card.key)
            items.push(card)
          }
        return
      }
      case 'confirmation_request': {
        const id = numberField(payload, 'confirmation_id')
        const confirmation = cycle.confirmations.find((row) => row.id === id)
        if (confirmation && !shown.has(confirmation.id)) {
          shown.add(confirmation.id)
          items.push(confirmationItem(confirmation, key))
        }
        return
      }
      case 'notice': {
        const mode = payload['mode']
        const notice = event.notice
        if (notice === SUGGEST_NOTICE && isMode(mode))
          items.push({
            type: 'suggest',
            key,
            mode,
            reason: textField(payload, 'reason'),
          })
        else {
          const text =
            textField(payload, 'text') || textField(payload, 'reason')
          if (text)
            items.push({
              type: 'notice',
              key,
              text,
              vision: notice === VISION_NOTICE,
            })
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
      default:
        return
    }
  })
  for (const confirmation of cycle.confirmations)
    if (!shown.has(confirmation.id))
      items.push(
        confirmationItem(
          confirmation,
          `confirmation-${String(confirmation.id)}`
        )
      )
  if (live) {
    for (const tool of live.tools)
      if (tool.phase !== 'result' && !persistedCalls.has(tool.callId))
        items.push({ type: 'live-tool', key: `live-${tool.callId}`, tool })
    if (live.text)
      items.push({ type: 'streaming', key: 'streaming', text: live.text })
  }
  return items
}

export function isActive(cycle: WillCycle): boolean {
  return cycle.status === 'running' || cycle.status === 'awaiting_confirmation'
}
