import { type components, permissionValues } from '@/api/generated/schema'
import { type LibraryJob, type UniverseSummary } from './types'

export const FIRST_ID = 'aaaaaaaaaaaa'
export const SECOND_ID = 'bbbbbbbbbbbb'

export function universeSummary(
  overrides: Partial<UniverseSummary> = {}
): UniverseSummary {
  return {
    id: FIRST_ID,
    name: 'Eldmark',
    summary: 'A cosmos grown from its seed.',
    notes: '',
    tags: [],
    status: 'active',
    pinned: false,
    origin: 'created',
    origin_note: '',
    created_at: '2026-11-01T10:00:00Z',
    opened_at: '2026-11-20T10:00:00Z',
    updated_at: '2026-11-20T10:00:00Z',
    epoch: 4,
    year: 200,
    population: 12000,
    sons: 3,
    size_bytes: 5_000_000,
    schema_revision: 'w52',
    app_version: '0.1.0',
    cover_path: null,
    media_prefix: 'universes/aaaaaaaaaaaa/',
    is_open: false,
    running_jobs: [],
    workspace_id: 7,
    canon_approval: false,
    legacy_author_name: '',
    role: 'admin',
    permissions: [...permissionValues],
    ...overrides,
  }
}

export function universePage(
  items: UniverseSummary[]
): components['schemas']['UniverseList'] {
  return {
    items,
    total: items.length,
    offset: 0,
    limit: 24,
    facets: {
      tags: [{ value: 'favourite', count: 1 }],
      origins: [{ value: 'created', count: items.length }],
      statuses: [{ value: 'active', count: items.length }],
    },
  }
}

export function trashPage(
  items: components['schemas']['TrashEntryView'][] = []
): components['schemas']['TrashPageView'] {
  return {
    items,
    total: items.length,
    offset: 0,
    limit: 24,
    held_bytes: items.reduce((sum, item) => sum + item.size_bytes, 0),
    keep_days: 30,
  }
}

export function libraryJob(overrides: Partial<LibraryJob> = {}): LibraryJob {
  return {
    id: 'job1',
    kind: 'export',
    stage: 'pack',
    status: 'running',
    universe_id: FIRST_ID,
    universe_name: 'Eldmark',
    done: 4,
    total: 10,
    progress: 0.4,
    error: '',
    notes: [],
    file_name: '',
    size_bytes: 0,
    preview: null,
    ...overrides,
  }
}
