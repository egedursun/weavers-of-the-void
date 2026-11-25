export const queryKeys = {
  health: ['health'] as const,
  jobs: {
    all: ['jobs'] as const,
    list: (limit: number) => ['jobs', 'list', limit] as const,
    detail: (jobId: string) => ['jobs', 'detail', jobId] as const,
  },
  rules: {
    all: ['rules'] as const,
  },
  world: {
    all: ['world'] as const,
  },
  notifications: {
    all: ['notifications'] as const,
  },
  images: {
    all: ['images'] as const,
  },
  backups: {
    all: ['backups'] as const,
  },
  metrics: {
    all: ['metrics'] as const,
  },
  usage: {
    all: ['usage'] as const,
  },
  epochs: {
    all: ['epochs'] as const,
  },
  ledger: {
    all: ['ledger'] as const,
  },
  catalogue: {
    all: ['catalogue'] as const,
  },
  divineWill: {
    all: ['divine-will'] as const,
    session: ['divine-will', 'session'] as const,
    artifacts: ['divine-will', 'artifacts'] as const,
    index: ['divine-will', 'index'] as const,
    cycle: (id: number) => ['divine-will', 'cycle', id] as const,
    plan: (id: number) => ['divine-will', 'plan', id] as const,
    forecast: (id: number) => ['divine-will', 'forecast', id] as const,
  },
}
