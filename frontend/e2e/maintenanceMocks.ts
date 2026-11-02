const NOW = '2026-01-01T12:00:00+00:00'

const task = (
  name: string,
  title: string,
  description: string,
  automatic: string,
  options: { ledgered?: boolean; needs_llm?: boolean; running?: boolean } = {}
) => ({
  task: name,
  title,
  description,
  automatic,
  rows: [],
  ledgered: options.ledgered ?? true,
  needs_llm: options.needs_llm ?? false,
  running: options.running ?? false,
})

const TASKS = [
  task('completion', 'Complete missing content', 'Fill the Creator portrait, son powers, the first sky body and peoples, image prompts, undeepened foreign gods, pending names and past epoch narratives.', 'Before every epoch and shortly after startup when something is missing', { ledgered: false, needs_llm: true }),
  task('network_rules', 'Network rule repair', 'Bond every located canon record to its location where the inside bond is missing.', 'Every epoch end'),
  task('loose_ends', 'Loose-end repair', 'Repair dangling ends of the link graph: events, narratives, prophecies, remnants and lost records.', 'Every epoch end when automatic graph repair is on, and at startup', { running: true }),
  task('importance', 'Recompute importance', 'Recompute and persist the importance score of every visible record.', 'Startup when any is missing, and every epoch end'),
  task('planner_statistics', 'Refresh planner statistics', 'Refresh the database planner statistics.', 'At startup and every epoch end', { ledgered: false }),
  task('prune', 'Prune old data', 'Prune read notifications, old ledger pages, old model metrics, the change log and unreferenced media objects, then checkpoint the log.', 'Every epoch end', { ledgered: false }),
]

const MISSING = {
  portrait: true,
  son_powers: [7],
  sky_body: false,
  first_people: false,
  image_prompts: 14,
  undeepened_gods: [3],
  pending_names: 2,
  past_narratives: [3, 5],
  anything_missing: true,
}

export const MAINTENANCE_JOB_ID = 'job-maintenance'

const MAINTENANCE_JOB = {
  id: MAINTENANCE_JOB_ID,
  kind: 'maintenance',
  status: 'succeeded',
  progress: 1,
  stage: 'Prune old data',
  params: { task: 'prune' },
  result: { task: 'prune', counters: { notifications: 12, ledger: 3, metrics: 240, change_log: 0, media: 2 }, ledger_entry_id: null },
  error: null,
  created_at: NOW,
  started_at: NOW,
  finished_at: NOW,
}

export function maintenanceResponse(method: string, url: URL): unknown {
  const route = url.pathname
  if (route === `/api/jobs/${MAINTENANCE_JOB_ID}`) return MAINTENANCE_JOB
  if (!route.startsWith('/api/maintenance/')) return undefined
  if (method === 'GET' && route === '/api/maintenance/tasks') return TASKS
  if (method === 'GET' && route === '/api/maintenance/missing') return MISSING
  if (method !== 'POST') return undefined
  const verify = /^\/api\/maintenance\/backups\/([^/]+)\/verify$/.exec(route)
  if (verify) return { file: decodeURIComponent(verify[1]), ok: true }
  return { job_id: MAINTENANCE_JOB_ID }
}
