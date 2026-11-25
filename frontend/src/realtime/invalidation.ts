import { type QueryClient, type QueryKey } from '@tanstack/react-query'
import { type components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { WORLD_REFRESH_MIN_MS } from '@/constants/ui'
import { type EventKind, type ServerEvent } from './events'
import { whenIdle } from './idleGate'

type Job = components['schemas']['JobResponse']

type InvalidationRule<K extends EventKind> = (
  event: ServerEvent<K>
) => QueryKey[]

const nothing = (): QueryKey[] => []
const world = (): QueryKey[] => [queryKeys.world.all]
const notifications = (): QueryKey[] => [
  queryKeys.notifications.all,
  queryKeys.world.all,
]
const images = (): QueryKey[] => [queryKeys.images.all]
const painted = (): QueryKey[] => [queryKeys.images.all, queryKeys.world.all]
const batchDeepen = (): QueryKey[] => [[...queryKeys.world.all, 'batch-deepen']]
const epochRun = (): QueryKey[] => [queryKeys.epochs.all]
const epochClosed = (): QueryKey[] => [
  queryKeys.world.all,
  queryKeys.jobs.all,
  queryKeys.epochs.all,
  queryKeys.metrics.all,
  queryKeys.usage.all,
  queryKeys.ledger.all,
]
const ledger = (): QueryKey[] => [queryKeys.world.all, queryKeys.ledger.all]

const turnFinished = (): QueryKey[] => [
  queryKeys.world.all,
  queryKeys.usage.all,
]

const jobChanged = (event: { payload: { job_id: string } }): QueryKey[] => [
  queryKeys.jobs.all,
  queryKeys.jobs.detail(event.payload.job_id),
  queryKeys.health,
]

const jobEnded = (event: { payload: { job_id: string } }): QueryKey[] => [
  ...jobChanged(event),
  queryKeys.usage.all,
]

export const INVALIDATIONS: { [K in EventKind]: InvalidationRule<K> } = {
  'job.queued': () => [queryKeys.jobs.all, queryKeys.health],
  'job.started': jobChanged,
  'job.progress': nothing,
  'job.finished': jobEnded,
  'job.failed': jobEnded,
  'job.cancelled': jobChanged,
  'world.changed': world,
  'rules.changed': () => [queryKeys.rules.all],
  'engine.note': nothing,
  'engine.phase': nothing,
  'system.note': nothing,
  'system.error': nothing,
  'agent.retry': nothing,
  'agent.stream': nothing,
  'agent.thought': nothing,
  'agent.tool_preparing': nothing,
  'agent.tool_writing': nothing,
  'agent.tool_called': nothing,
  'agent.tool_result': nothing,
  'agent.writing': nothing,
  'stream.hello': nothing,
  'epoch.started': () => [queryKeys.jobs.all, queryKeys.epochs.all],
  'epoch.resumed': epochRun,
  'epoch.progress': epochRun,
  'epoch.stop_requested': nothing,
  'epoch.stopped': epochClosed,
  'epoch.finished': epochClosed,
  'epoch.backup': () => [queryKeys.backups.all],
  'son.distributed': world,
  'son.turn_queued': nothing,
  'son.turn_started': nothing,
  'son.turn_finished': turnFinished,
  'mortals.started': nothing,
  'mortal.turn_started': nothing,
  'mortal.turn_finished': turnFinished,
  'engine.started': nothing,
  'engine.finished': world,
  'fate.started': nothing,
  'fate.step': nothing,
  'fate.finished': world,
  'council.held': world,
  'son.chat_replied': world,
  'son.new': world,
  'son.ascended': world,
  'creator.revelation': world,
  'world.born': world,
  'genesis.finished': world,
  'entity.deepened': world,
  'foreign_god.deepened': world,
  'epic.written': world,
  'network.repaired': world,
  'language.translated': world,
  'notification.created': notifications,
  'world.changes': () => [queryKeys.ledger.all],
  'world.replaced': () => [],
  'ledger.undone': ledger,
  'backup.taken': () => [queryKeys.backups.all],
  'image.queued': images,
  'image.progress': nothing,
  'image.done': painted,
  'image.failed': images,
  'image.status': images,
  'image.bulk_log': nothing,
  'batch_deepen.log': batchDeepen,
  'divine_will.cycle_started': () => [queryKeys.divineWill.session],
  'divine_will.cycle_finished': (event) => [
    queryKeys.divineWill.session,
    queryKeys.divineWill.cycle(event.payload.cycle_id),
    queryKeys.divineWill.artifacts,
    queryKeys.world.all,
    queryKeys.ledger.all,
    queryKeys.usage.all,
  ],
  'divine_will.confirmation_requested': (event) => [
    queryKeys.divineWill.session,
    queryKeys.divineWill.cycle(event.payload.cycle_id),
  ],
  'divine_will.artifact_changed': () => [queryKeys.divineWill.artifacts],
  'divine_will.plan_changed': (event) => [
    queryKeys.divineWill.plan(event.payload.plan_id),
    queryKeys.divineWill.session,
    queryKeys.world.all,
    queryKeys.ledger.all,
  ],
  'divine_will.forecast_progress': (event) => [
    queryKeys.divineWill.forecast(event.payload.forecast_id),
  ],
  'divine_will.index_progress': () => [queryKeys.divineWill.index],
}

const lastRun = new Map<string, number>()
const trailing = new Map<string, ReturnType<typeof setTimeout>>()

function coalesce(key: string, run: () => void): void {
  if (trailing.has(key)) return
  const wait = (lastRun.get(key) ?? 0) + WORLD_REFRESH_MIN_MS - Date.now()
  const fire = () => {
    trailing.delete(key)
    lastRun.set(key, Date.now())
    run()
  }
  if (wait <= 0) fire()
  else trailing.set(key, setTimeout(fire, wait))
}

export function invalidationsFor(event: ServerEvent): QueryKey[] {
  const rule = INVALIDATIONS[event.kind] as InvalidationRule<typeof event.kind>
  return rule(event)
}

function patchJobProgress(
  queryClient: QueryClient,
  event: ServerEvent<'job.progress'>
): void {
  const patch = (job: Job): Job =>
    job.id === event.payload.job_id
      ? {
          ...job,
          progress: event.payload.progress,
          stage: event.payload.stage ?? null,
        }
      : job
  queryClient.setQueryData<Job>(
    queryKeys.jobs.detail(event.payload.job_id),
    (current) => (current ? patch(current) : current)
  )
  queryClient.setQueriesData<Job[]>(
    { queryKey: queryKeys.jobs.all },
    (current) => (Array.isArray(current) ? current.map(patch) : current)
  )
}

export function applyServerEvent(
  queryClient: QueryClient,
  event: ServerEvent
): void {
  if (event.kind === 'world.replaced') {
    void queryClient.invalidateQueries()
    return
  }
  if (event.kind === 'job.progress') patchJobProgress(queryClient, event)
  for (const queryKey of invalidationsFor(event)) {
    const refresh = () => void queryClient.invalidateQueries({ queryKey })
    if (queryKey[0] === queryKeys.world.all[0])
      coalesce(JSON.stringify(queryKey), () =>
        whenIdle(JSON.stringify(queryKey), refresh)
      )
    else refresh()
  }
}
