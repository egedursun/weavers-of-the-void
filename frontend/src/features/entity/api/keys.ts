import { queryKeys } from '@/api/queryKeys'

const world = queryKeys.world.all

export type EntityListParams = {
  type?: string | null
  q?: string | null
  status?: string | null
  worldId?: number | null
  hideArchived?: boolean
  offset: number
  limit: number
}

export const loreKeys = {
  state: [...world, 'state'] as const,
  catalogue: ['catalogue'] as const,
  actions: [...queryKeys.rules.all, 'actions'] as const,
  names: [...world, 'names'] as const,
  cosmos: [...world, 'cosmos'] as const,
  knowledge: [...world, 'knowledge'] as const,
  foreignGods: [...world, 'foreign-gods'] as const,
  threads: [...world, 'threads'] as const,
  favorites: [...world, 'favorites'] as const,
  languages: [...world, 'languages'] as const,
  languageTree: [...world, 'languages', 'tree'] as const,
  entities: [...world, 'entities'] as const,
  entityList: (params: EntityListParams) =>
    [...world, 'entities', 'list', params] as const,
  entityAll: (status: string) => [...world, 'entities', 'all', status] as const,
  entity: (id: number) => [...world, 'entity', id] as const,
  note: (id: number) => [...world, 'entity', id, 'note'] as const,
  entityBonds: (id: number, offset: number, limit: number) =>
    [...world, 'entity', id, 'bonds', offset, limit] as const,
  entityChronicle: (id: number, offset: number, limit: number) =>
    [...world, 'entity', id, 'chronicle', offset, limit] as const,
  path: (from: number, to: number) => [...world, 'path', from, to] as const,
}
