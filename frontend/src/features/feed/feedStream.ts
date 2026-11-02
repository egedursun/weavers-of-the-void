export type StreamPhase =
  | 'streaming'
  | 'thought'
  | 'preparing'
  | 'writing'
  | 'called'
  | 'result'
  | 'failed'
  | 'finished'

export type FeedStream = {
  key: string
  phase: StreamPhase
  actorName: string
  tool: string | null
  chars: number
  text: string
  readOnly: boolean
}

export type StreamActorKind =
  'creator' | 'son' | 'mortal' | 'foreign_god' | 'fate' | 'engine' | 'system'

export type StreamDraft = {
  actorKind: StreamActorKind
  actorId: number | null
  stream: FeedStream
}

export const STREAM_KINDS: ReadonlySet<string> = new Set([
  'agent.stream',
  'agent.thought',
  'agent.tool_preparing',
  'agent.tool_writing',
  'agent.tool_called',
  'agent.tool_result',
  'agent.writing',
])

export const THROTTLED_STREAM_KINDS: ReadonlySet<string> = new Set([
  'agent.stream',
  'agent.tool_writing',
  'agent.writing',
])

const ACTOR_KINDS: readonly StreamActorKind[] = [
  'creator',
  'son',
  'mortal',
  'foreign_god',
  'fate',
  'engine',
  'system',
]

type Payload = Record<string, unknown>

function text(payload: Payload, field: string): string {
  const value = payload[field]
  return typeof value === 'string' ? value : ''
}

function count(payload: Payload, field: string): number {
  const value = payload[field]
  return typeof value === 'number' ? value : 0
}

function flag(payload: Payload, field: string): boolean {
  return payload[field] === true
}

function actorKindOf(payload: Payload): StreamActorKind {
  const value = text(payload, 'actor_kind')
  return ACTOR_KINDS.find((kind) => kind === value) ?? 'system'
}

function actorIdOf(payload: Payload): number | null {
  const value = payload['actor_id']
  return typeof value === 'number' ? value : null
}

export function streamDraft(
  kind: string,
  payload: Payload
): StreamDraft | null {
  const actorKind = actorKindOf(payload)
  const actorId = actorIdOf(payload)
  const actorName =
    text(payload, 'actor_name') || text(payload, 'who') || 'Someone'
  const owner = `${actorKind}:${actorId ?? actorName}`
  const base = { actorName, tool: null, chars: 0, text: '', readOnly: false }
  switch (kind) {
    case 'agent.stream':
      return {
        actorKind,
        actorId,
        stream: {
          ...base,
          key: `text:${owner}`,
          phase: 'streaming',
          chars: count(payload, 'chars'),
          text: text(payload, 'text'),
        },
      }
    case 'agent.thought':
      return {
        actorKind,
        actorId,
        stream: {
          ...base,
          key: `text:${owner}`,
          phase: 'thought',
          text: text(payload, 'text'),
        },
      }
    case 'agent.tool_preparing':
      return {
        actorKind,
        actorId,
        stream: {
          ...base,
          key: `tool:${text(payload, 'call_id')}`,
          phase: 'preparing',
          tool: text(payload, 'tool'),
        },
      }
    case 'agent.tool_writing':
      return {
        actorKind,
        actorId,
        stream: {
          ...base,
          key: `tool:${text(payload, 'call_id')}`,
          phase: 'writing',
          tool: text(payload, 'tool'),
          chars: count(payload, 'chars'),
        },
      }
    case 'agent.tool_called':
      return {
        actorKind,
        actorId,
        stream: {
          ...base,
          key: `tool:${text(payload, 'call_id')}`,
          phase: 'called',
          tool: text(payload, 'tool'),
          readOnly: flag(payload, 'read_only'),
        },
      }
    case 'agent.tool_result':
      return {
        actorKind,
        actorId,
        stream: {
          ...base,
          key: `tool:${text(payload, 'call_id')}`,
          phase: flag(payload, 'error') ? 'failed' : 'result',
          tool: text(payload, 'tool'),
          text: text(payload, 'text'),
          readOnly: flag(payload, 'quiet'),
        },
      }
    case 'agent.writing':
      return {
        actorKind: 'system',
        actorId: null,
        stream: {
          ...base,
          key: `write:${text(payload, 'stream_id')}`,
          phase: flag(payload, 'finished')
            ? payload['error']
              ? 'failed'
              : 'finished'
            : 'writing',
          chars: count(payload, 'chars'),
          text: text(payload, 'error'),
        },
      }
    default:
      return null
  }
}

export function isOpenStream(stream: FeedStream): boolean {
  return (
    stream.phase === 'streaming' ||
    stream.phase === 'preparing' ||
    stream.phase === 'writing' ||
    stream.phase === 'called'
  )
}

export function mergeStream(
  previous: FeedStream,
  next: FeedStream
): FeedStream {
  if (next.phase === 'streaming')
    return {
      ...previous,
      phase: 'streaming',
      chars: next.chars,
      text:
        previous.phase === 'streaming' ? previous.text + next.text : next.text,
    }
  if (next.phase === 'thought') return { ...previous, ...next }
  return {
    ...previous,
    ...next,
    tool: next.tool ?? previous.tool,
    readOnly: next.readOnly || previous.readOnly,
    chars: Math.max(previous.chars, next.chars),
    text: next.text || previous.text,
  }
}

export function closesKey(stream: FeedStream): boolean {
  return (
    stream.phase === 'thought' ||
    stream.phase === 'result' ||
    stream.phase === 'failed' ||
    stream.phase === 'finished'
  )
}

export type FeedMeta = {
  rarity: string | null
  chips: string[]
}

export const NO_META: FeedMeta = { rarity: null, chips: [] }

function optionalText(payload: Payload, field: string): string | null {
  const value = payload[field]
  return typeof value === 'string' && value !== '' ? value : null
}

function optionalCount(payload: Payload, field: string): number | null {
  const value = payload[field]
  return typeof value === 'number' ? value : null
}

export function turnMeta(payload: Payload): FeedMeta {
  const chips: string[] = []
  const order = optionalCount(payload, 'order')
  const total = optionalCount(payload, 'total')
  if (order !== null && total !== null) chips.push(`${order}/${total}`)
  const model = optionalText(payload, 'model')
  if (model) chips.push(model)
  return { rarity: optionalText(payload, 'rarity'), chips }
}

const RETRY_LABEL: Record<string, string> = {
  restart: 'Restarted from the beginning',
  continuation: 'Resumed where it stopped',
  dropped_turn: 'Turn dropped and retried',
  model_call: 'Model call retried',
}

export function retryMeta(payload: Payload): FeedMeta {
  const chips: string[] = []
  const kind = optionalText(payload, 'kind')
  if (kind) chips.push(RETRY_LABEL[kind] ?? kind)
  const kept = optionalCount(payload, 'kept_steps')
  if (kept !== null && kept > 0)
    chips.push(`${kept} successful ${kept === 1 ? 'step' : 'steps'} kept`)
  const wait = optionalCount(payload, 'wait_s')
  if (wait !== null && wait > 0) chips.push(`waits ${wait}s`)
  return { rarity: null, chips }
}
