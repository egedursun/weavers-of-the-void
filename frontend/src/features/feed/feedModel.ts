import { type ServerEvent } from '@/realtime'
import { type components } from '@/api/generated/schema'
import { formatDuration } from '@/lib/units'
import { JOB_KIND_LABEL, isJobKind } from '@/constants/jobs'
import { type TimelineTone } from '@/components/domain'
import { type DrawerEntry } from '@/components/layout/drawer/drawerEntries'
import {
  type FeedMeta,
  type FeedStream,
  NO_META,
  retryMeta,
  turnMeta,
  STREAM_KINDS,
  closesKey,
  isOpenStream,
  mergeStream,
  streamDraft,
} from './feedStream'
import { toolLabel } from './feedToolIcons'

export const FEED_LINE_CAP = 500
export const GROUP_VISIBLE = 2
const TURN_SUCCESS = 'success'

export const FEED_ACTORS = ['all', 'gods', 'mortals', 'world', 'fate'] as const
export type FeedActorFilter = (typeof FEED_ACTORS)[number]
export type FeedActor = Exclude<FeedActorFilter, 'all'> | 'system'

export type FeedCategory = components['schemas']['FeedCategory']

export const FEED_CATEGORIES: readonly FeedCategory[] = [
  'voyage',
  'gate',
  'leak',
  'war',
  'disaster',
  'sky',
  'life',
  'civilization',
  'world',
]

export const FEED_CATEGORY_LABEL: Record<FeedCategory, string> = {
  voyage: 'Ships and voyages',
  gate: 'Gates and routes',
  leak: 'Leakage and horror',
  war: 'Wars',
  disaster: 'Disasters',
  sky: 'Sky events',
  life: 'Birth and death',
  civilization: 'Civilization',
  world: 'The world',
}

export const FEED_ACTOR_LABEL: Record<FeedActorFilter, string> = {
  all: 'All',
  gods: 'Gods',
  mortals: 'Mortals',
  world: 'World',
  fate: 'Fate',
}

export type FeedSymbol =
  | 'job'
  | 'job-done'
  | 'job-failed'
  | 'epoch'
  | 'phase'
  | 'son'
  | 'mortal'
  | 'engine'
  | 'fate'
  | 'council'
  | 'record'
  | 'world'
  | 'notice'
  | 'error'
  | 'retry'
  | 'image'
  | 'backup'
  | 'rules'
  | 'undo'
  | 'network'
  | 'thought'
  | 'tool'
  | 'writing'

export type FeedLink = DrawerEntry & { label: string }

export type FeedLine = {
  id: number
  kind: ServerEvent['kind']
  at: string
  epoch: number | null
  actor: FeedActor
  actorKey: string | null
  category: FeedCategory | null
  symbol: FeedSymbol
  tone: TimelineTone
  title: string
  detail: string | null
  link: FeedLink | null
  stream: FeedStream | null
  meta: FeedMeta
}

type Draft = Omit<FeedLine, 'id' | 'kind' | 'at' | 'epoch'>

const QUIET_KINDS: ReadonlySet<ServerEvent['kind']> = new Set([
  'job.progress',
  'image.progress',
  'world.changes',
  'world.changed',
  'son.turn_queued',
])

function draft(
  actor: FeedActor,
  symbol: FeedSymbol,
  title: string,
  extra: Partial<Draft> = {}
): Draft {
  return {
    actor,
    actorKey: null,
    category: null,
    symbol,
    tone: 'default',
    title,
    detail: null,
    link: null,
    stream: null,
    meta: NO_META,
    ...extra,
  }
}

function jobLabel(kind: string): string {
  return isJobKind(kind) ? JOB_KIND_LABEL[kind] : kind
}

function sonLink(id: number, name: string): FeedLink {
  return { kind: 'son', id: String(id), label: name }
}

function entityLink(id: number, name: string): FeedLink {
  return { kind: 'entity', id: String(id), label: name }
}

function describe(event: ServerEvent): Draft | null {
  switch (event.kind) {
    case 'job.queued':
      return draft('system', 'job', `${jobLabel(event.payload.kind)} queued`)
    case 'job.started':
      return draft('system', 'job', `${jobLabel(event.payload.kind)} started`, {
        tone: 'primary',
      })
    case 'job.finished':
      return draft(
        'system',
        'job-done',
        `${jobLabel(event.payload.kind)} finished`,
        { tone: 'success' }
      )
    case 'job.failed':
      return draft(
        'system',
        'job-failed',
        `${jobLabel(event.payload.kind)} failed`,
        { tone: 'destructive', detail: event.payload.error }
      )
    case 'job.cancelled':
      return draft(
        'system',
        'job-failed',
        `${jobLabel(event.payload.kind)} cancelled`,
        { tone: 'warning' }
      )
    case 'rules.changed':
      return draft('system', 'rules', 'World rules changed', {
        detail:
          event.payload.namespace && event.payload.key
            ? `${event.payload.namespace}.${event.payload.key}`
            : null,
      })
    case 'engine.note':
      return draft('world', 'engine', event.payload.text, {
        category: event.payload.feed ?? 'world',
      })
    case 'engine.phase':
      return event.payload.error
        ? draft('world', 'error', `Engine step ${event.payload.phase} failed`, {
            tone: 'destructive',
            detail: event.payload.error,
          })
        : null
    case 'engine.started':
      return draft('world', 'engine', 'The world engine turns')
    case 'engine.finished':
      return draft(
        'world',
        'engine',
        event.payload.notes > 0
          ? `The world engine wrote ${event.payload.notes} notes`
          : 'A quiet epoch: the world engine wrote nothing',
        { tone: 'success' }
      )
    case 'system.note':
      return draft('system', 'notice', event.payload.text)
    case 'system.error':
      return draft('system', 'error', event.payload.text, {
        tone: 'destructive',
        detail: event.payload.will_retry ? 'It will be retried.' : null,
        link:
          event.payload.son_id !== null && event.payload.son_id !== undefined
            ? sonLink(event.payload.son_id, 'Open the son')
            : null,
      })
    case 'agent.retry':
      return draft(
        'system',
        'retry',
        `${event.payload.actor}: retrying (${event.payload.attempt}/${event.payload.total})`,
        {
          tone: 'warning',
          detail: event.payload.reason ?? null,
          meta: retryMeta(event.payload),
        }
      )
    case 'epoch.started':
      return draft(
        'system',
        'epoch',
        event.payload.resuming ? 'The epoch resumes' : 'A new epoch begins',
        {
          tone: 'primary',
          detail:
            event.payload.order && event.payload.order.length > 0
              ? `Order: ${event.payload.order.map((item) => `${item.name} (initiative ${item.ini})`).join(', ')}`
              : null,
        }
      )
    case 'epoch.resumed':
      return draft(
        'system',
        'epoch',
        `Resuming from phase ${event.payload.phase}`,
        { tone: 'primary' }
      )
    case 'epoch.progress':
      return draft(
        'system',
        'phase',
        `Phase ${event.payload.no}/${event.payload.total}: ${event.payload.name}`
      )
    case 'epoch.stop_requested':
      return draft(
        'system',
        'epoch',
        'Stop requested: the epoch stops at a safe point',
        { tone: 'warning' }
      )
    case 'epoch.stopped':
      return draft(
        'system',
        'epoch',
        `The epoch stopped at phase ${event.payload.phase}`,
        { tone: 'warning', detail: 'Complete the epoch to resume it.' }
      )
    case 'epoch.finished':
      return draft(
        'system',
        'epoch',
        `The epoch closed; epoch ${event.payload.new_epoch} begins`,
        {
          tone: 'success',
          detail: `It took ${formatDuration(event.payload.duration_s)}.`,
        }
      )
    case 'epoch.backup':
      return draft('system', 'backup', 'Backup taken before the epoch', {
        detail: event.payload.file,
      })
    case 'backup.taken':
      return draft('system', 'backup', 'Backup taken', {
        detail: event.payload.file,
      })
    case 'son.distributed':
      return draft('gods', 'son', event.payload.text ?? 'Sons were distributed')
    case 'son.turn_started':
      return draft(
        'gods',
        'son',
        event.payload.resumed
          ? `${event.payload.son_name} resumes their turn`
          : `${event.payload.son_name} takes their turn`,
        {
          actorKey: `son:${event.payload.son_id}`,
          tone: 'primary',
          link: sonLink(event.payload.son_id, event.payload.son_name),
          meta: turnMeta(event.payload),
        }
      )
    case 'son.turn_finished':
      return draft('gods', 'son', `${event.payload.son_name} ends their turn`, {
        actorKey: `son:${event.payload.son_id}`,
        tone: event.payload.status === TURN_SUCCESS ? 'success' : 'warning',
        detail: event.payload.word ?? null,
        link: sonLink(event.payload.son_id, event.payload.son_name),
        meta: turnMeta(event.payload),
      })
    case 'mortals.started':
      return draft(
        'mortals',
        'mortal',
        event.payload.agents && event.payload.agents.length > 0
          ? `${event.payload.agents.length} mortal agents wake`
          : 'The mortals wake',
        {
          detail:
            event.payload.agents && event.payload.agents.length > 0
              ? event.payload.agents.map((agent) => agent.name).join(', ')
              : null,
        }
      )
    case 'mortal.turn_started':
      return draft('mortals', 'mortal', `${event.payload.name} takes a turn`, {
        actorKey: `mortal:${event.payload.entity_id}`,
        link: entityLink(event.payload.entity_id, event.payload.name),
        meta: turnMeta(event.payload),
      })
    case 'mortal.turn_finished':
      return draft('mortals', 'mortal', `${event.payload.name} ends a turn`, {
        actorKey: `mortal:${event.payload.entity_id}`,
        tone: event.payload.status === TURN_SUCCESS ? 'success' : 'warning',
        detail: event.payload.word ?? null,
        link: entityLink(event.payload.entity_id, event.payload.name),
      })
    case 'fate.started':
      return draft('fate', 'fate', 'Fate weighs the creations')
    case 'fate.step':
      return draft('fate', 'fate', event.payload.text)
    case 'fate.finished': {
      const rejected = event.payload.rejected?.length ?? 0
      const corrected = event.payload.corrected?.length ?? 0
      return draft('fate', 'fate', 'Fate has spoken', {
        tone: event.payload.fate_debt ? 'warning' : 'success',
        detail: event.payload.fate_debt
          ? 'Fate could not weigh this epoch; it is in debt.'
          : `${rejected} rejected, ${corrected} corrected.`,
      })
    }
    case 'council.held':
      return draft('gods', 'council', `Council: ${event.payload.topic}`, {
        tone: event.payload.passed ? 'success' : 'warning',
        detail: event.payload.passed
          ? 'The motion passed.'
          : 'The motion failed.',
      })
    case 'son.chat_replied':
      return draft('gods', 'son', 'A son answered you', {
        detail: `Attitude: ${event.payload.attitude}`,
        link: sonLink(event.payload.son_id, 'Open the son'),
      })
    case 'son.new':
      return draft(
        'gods',
        'son',
        `${event.payload.name ?? 'A new son'} arrives`,
        {
          tone: 'primary',
          link: sonLink(
            event.payload.son_id,
            event.payload.name ?? 'Open the son'
          ),
        }
      )
    case 'son.ascended':
      return draft('gods', 'son', 'A son ascends', {
        tone: 'primary',
        detail: `Now ${event.payload.rarity}.`,
        link: sonLink(event.payload.son_id, 'Open the son'),
      })
    case 'creator.revelation':
      return draft(
        'gods',
        'record',
        `${event.payload.name ?? 'A revelation'} appeared`,
        {
          tone: 'primary',
          link:
            event.payload.entity_id !== null &&
            event.payload.entity_id !== undefined
              ? entityLink(
                  event.payload.entity_id,
                  event.payload.name ?? 'Open'
                )
              : null,
        }
      )
    case 'world.born':
      return draft(
        'world',
        'world',
        `${event.payload.name ?? 'A world'} is born`,
        {
          tone: 'primary',
          link: {
            kind: 'world-guide',
            id: String(event.payload.world_id),
            label: event.payload.name ?? 'Open the guide',
          },
        }
      )
    case 'genesis.finished':
      return draft('system', 'world', 'Genesis is complete', {
        tone: 'success',
      })
    case 'entity.deepened':
      return draft('world', 'record', `${event.payload.name} was deepened`, {
        link: entityLink(event.payload.entity_id, event.payload.name),
      })
    case 'foreign_god.deepened':
      return draft('world', 'record', `${event.payload.name} was deepened`, {
        link: {
          kind: 'foreign-god',
          id: String(event.payload.id),
          label: event.payload.name,
        },
      })
    case 'epic.written':
      return draft(
        'gods',
        'record',
        `An epic was written: ${event.payload.title}`
      )
    case 'network.repaired':
      return draft('system', 'network', event.payload.text)
    case 'language.translated':
      return draft(
        'world',
        'record',
        `A language grew by ${event.payload.new_words} words`
      )
    case 'notification.created':
      return draft('system', 'notice', event.payload.title, {
        tone: event.payload.category === 'achievement' ? 'success' : 'default',
        detail: event.payload.body ?? null,
      })
    case 'world.replaced':
      return draft('system', 'world', event.payload.message, {
        tone: 'warning',
      })
    case 'ledger.undone':
      return draft(
        'system',
        'undo',
        `Ledger page #${event.payload.entry_id} undone`,
        {
          detail:
            event.payload.conflicts > 0
              ? `${event.payload.applied} changes reverted, ${event.payload.conflicts} conflicts skipped.`
              : `${event.payload.applied} changes reverted.`,
        }
      )
    case 'image.queued':
      return draft('system', 'image', 'Image queued', {
        detail: `Position ${event.payload.position}`,
      })
    case 'image.done':
      return draft('system', 'image', 'Image generated', { tone: 'success' })
    case 'image.failed':
      return draft('system', 'image', 'Image generation failed', {
        tone: 'destructive',
        detail: event.payload.error,
      })
    case 'image.bulk_log':
    case 'batch_deepen.log': {
      const text = event.payload.line ?? event.payload.text
      if (!text) return null
      const level = event.payload.level
      return draft(
        'system',
        event.kind === 'image.bulk_log' ? 'image' : 'record',
        text,
        {
          tone:
            level === 'error'
              ? 'destructive'
              : level === 'warning'
                ? 'warning'
                : 'default',
        }
      )
    }
    default:
      return describeStream(event)
  }
}

function describeStream(event: ServerEvent): Draft | null {
  if (!STREAM_KINDS.has(event.kind)) return null
  const built = streamDraft(event.kind, event.payload)
  if (!built) return null
  const { stream, actorKind, actorId } = built
  const actor: FeedActor =
    actorKind === 'son' ||
    actorKind === 'creator' ||
    actorKind === 'foreign_god'
      ? 'gods'
      : actorKind === 'mortal'
        ? 'mortals'
        : actorKind === 'fate'
          ? 'fate'
          : actorKind === 'engine'
            ? 'world'
            : 'system'
  const link =
    actorId === null
      ? null
      : actorKind === 'son'
        ? sonLink(actorId, stream.actorName)
        : actorKind === 'mortal'
          ? entityLink(actorId, stream.actorName)
          : null
  const isTool = stream.key.startsWith('tool:')
  const isWrite = stream.key.startsWith('write:')
  return draft(
    actor,
    isTool ? 'tool' : isWrite ? 'writing' : 'thought',
    isTool
      ? `${stream.actorName} · ${toolLabel(stream.tool)}`
      : isWrite
        ? `${stream.actorName} is writing`
        : `${stream.actorName} thinks`,
    {
      actorKey: actorId === null ? null : `${actorKind}:${actorId}`,
      tone:
        stream.phase === 'failed'
          ? 'destructive'
          : stream.phase === 'result' || stream.phase === 'finished'
            ? 'success'
            : 'default',
      link,
      stream,
    }
  )
}

export function toFeedLine(event: ServerEvent): FeedLine | null {
  if (QUIET_KINDS.has(event.kind)) return null
  const described = describe(event)
  if (!described) return null
  return {
    ...described,
    id: event.id,
    kind: event.kind,
    at: event.at,
    epoch: event.payload.epoch ?? null,
  }
}

function mergeLine(existing: FeedLine, incoming: FeedLine): FeedLine {
  if (!existing.stream || !incoming.stream) return existing
  return {
    ...existing,
    at: incoming.at,
    tone: incoming.tone,
    title: incoming.stream.tool ? incoming.title : existing.title,
    stream: mergeStream(existing.stream, incoming.stream),
  }
}

function openIndex(lines: FeedLine[], line: FeedLine): number {
  const key = line.stream?.key
  if (!key) return -1
  for (let index = lines.length - 1; index >= 0; index -= 1) {
    const stream = lines[index].stream
    if (stream && stream.key === key && !closesKey(stream)) return index
  }
  return -1
}

export function appendLines(
  current: FeedLine[],
  incoming: FeedLine[]
): FeedLine[] {
  if (incoming.length === 0) return current
  const known = new Set(current.map((line) => line.id))
  const next = [...current]
  let changed = false
  for (const line of incoming) {
    if (known.has(line.id)) continue
    known.add(line.id)
    changed = true
    const index = openIndex(next, line)
    if (index >= 0) next[index] = mergeLine(next[index], line)
    else next.push(line)
  }
  if (!changed) return current
  return next.sort((left, right) => left.id - right.id).slice(-FEED_LINE_CAP)
}

export const INTERRUPTED_TEXT = 'Interrupted'

export function closeOpenStreams(lines: FeedLine[]): FeedLine[] {
  if (!lines.some((line) => line.stream && isOpenStream(line.stream)))
    return lines
  return lines.map((line) =>
    line.stream && isOpenStream(line.stream)
      ? {
          ...line,
          tone: 'warning',
          stream: {
            ...line.stream,
            phase: 'failed',
            text: line.stream.text || INTERRUPTED_TEXT,
          },
        }
      : line
  )
}

export type FeedFilter = {
  actor: FeedActorFilter
  categories: ReadonlySet<FeedCategory>
}

export function matchesFilter(line: FeedLine, filter: FeedFilter): boolean {
  if (filter.actor !== 'all' && line.actor !== filter.actor) return false
  if (line.category && filter.categories.size > 0)
    return filter.categories.has(line.category)
  return true
}

export function presentCategories(lines: FeedLine[]): FeedCategory[] {
  const present = new Set(
    lines.map((line) => line.category).filter((value) => value !== null)
  )
  return FEED_CATEGORIES.filter((category) => present.has(category))
}

export type FeedRow =
  | { type: 'line'; line: FeedLine; repeatedEpoch: boolean; open: boolean }
  | { type: 'continues'; key: string; line: FeedLine }
  | { type: 'reading'; key: string; lines: FeedLine[]; open: boolean }
  | {
      type: 'group'
      key: string
      category: FeedCategory
      hidden: FeedLine[]
    }

export function buildRows(
  lines: FeedLine[],
  expanded: ReadonlySet<string>
): FeedRow[] {
  const rows: FeedRow[] = []
  let previousEpoch: number | null = null
  let lastActorKey: string | null = null
  let index = 0
  while (index < lines.length) {
    const line = lines[index]
    if (line.category) {
      let end = index
      while (
        end + 1 < lines.length &&
        lines[end + 1].category === line.category
      )
        end += 1
      const run = lines.slice(index, end + 1)
      const key = `group-${run[0].id}`
      const visible =
        expanded.has(key) || run.length <= GROUP_VISIBLE + 1
          ? run
          : run.slice(0, GROUP_VISIBLE)
      for (const item of visible) {
        rows.push({
          type: 'line',
          line: item,
          repeatedEpoch: item.epoch !== null && item.epoch === previousEpoch,
          open: expanded.has(`line-${item.id}`),
        })
        previousEpoch = item.epoch
      }
      if (run.length > GROUP_VISIBLE + 1)
        rows.push({
          type: 'group',
          key,
          category: line.category,
          hidden: expanded.has(key) ? [] : run.slice(GROUP_VISIBLE),
        })
      index = end + 1
      continue
    }
    if (
      line.actorKey &&
      lastActorKey &&
      line.actorKey !== lastActorKey &&
      line.kind !== 'son.turn_started' &&
      line.kind !== 'mortal.turn_started'
    )
      rows.push({ type: 'continues', key: `continues-${line.id}`, line })
    if (line.actorKey) lastActorKey = line.actorKey
    if (line.stream?.readOnly) {
      let end = index
      while (
        end + 1 < lines.length &&
        lines[end + 1].stream?.readOnly &&
        lines[end + 1].actorKey === line.actorKey
      )
        end += 1
      if (end > index) {
        const key = `reading-${line.id}`
        rows.push({
          type: 'reading',
          key,
          lines: lines.slice(index, end + 1),
          open: expanded.has(key),
        })
        index = end + 1
        continue
      }
    }
    rows.push({
      type: 'line',
      line,
      repeatedEpoch: line.epoch !== null && line.epoch === previousEpoch,
      open: expanded.has(`line-${line.id}`),
    })
    previousEpoch = line.epoch
    index += 1
  }
  return rows
}
