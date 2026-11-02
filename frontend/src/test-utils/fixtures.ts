export function serverEvent(
  kind: string,
  payload: Record<string, unknown>,
  at = '2026-01-01T12:00:00Z',
  id = 1
) {
  return { id, kind, payload, at } as never
}

export const WORLD = {
  id: 1,
  name: 'Aerona',
  type: 'planet',
  description: 'A green world.',
  epoch: 3,
  year: 300,
  mortal_agents_per_epoch: 4,
}

export function worldState(overrides: Record<string, unknown> = {}) {
  return {
    world: WORLD,
    creator: null,
    creator_cover: null,
    world_cover: null,
    sons: [],
    counts: {},
    prayers_pending: 0,
    relations: [],
    worlds: [],
    foreign_god_count: 0,
    pending_son_ids: [],
    covenants: [],
    threads: [],
    last_epoch: null,
    image_count: 0,
    promptless_count: 0,
    pulse: null,
    read_only: false,
    discovery: null,
    version: '0.1.0',
    notifications_unread: 0,
    running_jobs: 0,
    epoch_running: false,
    half_epoch: null,
    mood: null,
    image_gen: { running: false },
    batch_deepen: {},
    llm_enabled: true,
    ...overrides,
  }
}

export function ruleList(values: Record<string, number>) {
  return Object.entries(values).map(([path, value]) => {
    const [namespace, key] = path.split('.')
    return {
      namespace,
      key,
      value,
      default: value,
      minimum: 0,
      maximum: 1_000_000,
      group: namespace,
      label: key.replaceAll('_', ' '),
      integer: true,
    }
  })
}

export function jobRecord(overrides: Record<string, unknown> = {}) {
  return {
    id: 'job-1',
    kind: 'epoch',
    status: 'running',
    progress: 0.5,
    stage: null,
    params: {},
    result: null,
    error: null,
    created_at: '2026-01-01T12:00:00Z',
    started_at: '2026-01-01T12:00:00Z',
    finished_at: null,
    ...overrides,
  }
}
