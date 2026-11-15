import {
  type components,
  jobKindValues,
  jobStatusValues,
} from '@/api/generated/schema'

export type JobStatus = components['schemas']['JobStatus']

export type JobKind = components['schemas']['JobKind']

export const JOB_STATUSES: readonly JobStatus[] = jobStatusValues

export const JOB_KINDS: readonly JobKind[] = jobKindValues

export const TERMINAL_JOB_STATUSES: ReadonlySet<JobStatus> = new Set<JobStatus>(
  ['succeeded', 'failed', 'cancelled', 'interrupted']
)

export const JOB_KIND_LABEL: Record<JobKind, string> = {
  epoch: 'Epoch',
  genesis: 'Genesis',
  deepen: 'Deepening',
  summon: 'Summoning',
  image: 'Image generation',
  backup: 'Backup',
  book: 'Printing the book',
  import: 'Import',
  simulation: 'Simulation',
  son_turn: 'Son turn',
  naming: 'Naming',
  completion: 'Completion',
  revelation: 'Revelation',
  world_creation: 'World creation',
  prehistory: 'Prehistory',
  deep_time: 'Fast-forward of deep time',
  awakening: 'Awakening',
  content: 'Writing',
  retry: 'Retry',
  maintenance: 'Maintenance',
}

export const JOB_STATUS_LABEL: Record<JobStatus, string> = {
  queued: 'Queued',
  running: 'Running',
  succeeded: 'Done',
  failed: 'Failed',
  cancelled: 'Cancelled',
  interrupted: 'Interrupted',
}

export function isJobStatus(value: unknown): value is JobStatus {
  return (
    typeof value === 'string' &&
    (JOB_STATUSES as readonly string[]).includes(value)
  )
}

export function isJobKind(value: unknown): value is JobKind {
  return (
    typeof value === 'string' &&
    (JOB_KINDS as readonly string[]).includes(value)
  )
}
