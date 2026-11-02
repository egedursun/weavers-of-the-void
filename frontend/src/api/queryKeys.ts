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
  epochs: {
    all: ['epochs'] as const,
  },
  ledger: {
    all: ['ledger'] as const,
  },
  catalogue: {
    all: ['catalogue'] as const,
  },
}
