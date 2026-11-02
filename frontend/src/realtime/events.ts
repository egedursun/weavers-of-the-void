import { z } from 'zod'
import { type paths, eventKindValues } from '@/api/generated/schema'

type ActivityLog =
  paths['/api/activity-log']['get']['responses'][200]['content']['application/json']

type AnyServerEvent = ActivityLog[number]

export type EventKind = AnyServerEvent['kind']

export type ServerEvent<K extends EventKind = EventKind> = Extract<
  AnyServerEvent,
  { kind: K }
>

export type EventPayload<K extends EventKind> = ServerEvent<K>['payload']

export const EVENT_KINDS: readonly EventKind[] = eventKindValues

const jobReference = z.object({
  job_id: z.string(),
  kind: z.string(),
})

const payloadChecks: Partial<Record<EventKind, z.ZodType>> = {
  'job.queued': jobReference,
  'job.started': jobReference,
  'job.progress': jobReference.extend({
    progress: z.number(),
    stage: z.string().nullable().optional(),
  }),
  'job.finished': jobReference.extend({
    result: z.record(z.string(), z.unknown()).nullable().optional(),
  }),
  'job.failed': jobReference.extend({ error: z.string() }),
  'job.cancelled': jobReference,
}

const envelope = z.object({
  id: z.number().int().nonnegative(),
  kind: z.string(),
  payload: z.record(z.string(), z.unknown()),
  at: z.string(),
})

export function isEventKind(value: string): value is EventKind {
  return (EVENT_KINDS as readonly string[]).includes(value)
}

export function parseServerEvent(data: string): ServerEvent | null {
  let raw: unknown
  try {
    raw = JSON.parse(data)
  } catch {
    return null
  }
  const parsed = envelope.safeParse(raw)
  if (!parsed.success || !isEventKind(parsed.data.kind)) return null
  const check = payloadChecks[parsed.data.kind]
  if (check && !check.safeParse(parsed.data.payload).success) return null
  return parsed.data as ServerEvent
}
