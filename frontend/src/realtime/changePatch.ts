import { type QueryClient } from '@tanstack/react-query'
import { type components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { whenIdle } from './idleGate'

export type Changes = components['schemas']['ChangesResponse']
type EntityRecord = components['schemas']['EntityRecord']
type SonPublic = components['schemas']['SonPublic']

const WORLD = queryKeys.world.all[0]

function keyHas(key: readonly unknown[], word: string): boolean {
  return key[0] === WORLD && key.includes(word)
}

function mergeShared<T extends object>(row: T, source: object): T {
  const next = { ...row } as Record<string, unknown>
  for (const field of Object.keys(row))
    if (field in source)
      next[field] = (source as Record<string, unknown>)[field]
  return next as T
}

function patchEntities(
  client: QueryClient,
  changed: EntityRecord[],
  removed: number[]
): void {
  const byId = new Map(changed.map((entity) => [entity.id, entity]))
  const gone = new Set(removed)
  for (const entity of changed)
    client.setQueryData<{ entity: EntityRecord }>(
      [WORLD, 'entity', entity.id],
      (current) => (current ? { ...current, entity } : current)
    )
  client.setQueriesData<unknown>(
    { predicate: (query) => keyHas(query.queryKey, 'entities') },
    (current: unknown) => {
      const patchRow = (row: { id: number }) => {
        const source = byId.get(row.id)
        return source ? mergeShared(row, source) : row
      }
      if (Array.isArray(current)) return current.map(patchRow)
      if (!current || typeof current !== 'object') return current
      const page = current as { items?: { id: number }[] }
      if (!Array.isArray(page.items)) return current
      return { ...page, items: page.items.map(patchRow) }
    }
  )
  if (removed.length > 0)
    for (const id of gone)
      void client.invalidateQueries({ queryKey: [WORLD, 'entity', id] })
}

function patchSons(
  client: QueryClient,
  changed: SonPublic[],
  removed: number[]
): void {
  const byId = new Map(changed.map((view) => [view.son.id, view]))
  const gone = new Set(removed)
  client.setQueryData<{ sons: SonPublic[] }>([WORLD, 'state'], (current) =>
    current && Array.isArray(current.sons)
      ? {
          ...current,
          sons: current.sons
            .filter((view) => !gone.has(view.son.id))
            .map((view) => byId.get(view.son.id) ?? view),
        }
      : current
  )
  client.setQueryData<SonPublic[]>([WORLD, 'sons'], (current) =>
    Array.isArray(current)
      ? current
          .filter((view) => !gone.has(view.son.id))
          .map((view) => byId.get(view.son.id) ?? view)
      : current
  )
  for (const view of changed)
    client.setQueryData<{ son: SonPublic['son'] }>(
      [WORLD, 'son', view.son.id],
      (current) => (current ? { ...current, son: view.son } : current)
    )
}

function later(
  client: QueryClient,
  key: string,
  predicate: (k: readonly unknown[]) => boolean
): void {
  whenIdle(`changes:${key}`, () => {
    void client.invalidateQueries({
      predicate: (query) => predicate(query.queryKey),
    })
  })
}

export function applyChanges(client: QueryClient, changes: Changes): void {
  if (changes.full) {
    whenIdle('changes:full', () => {
      void client.invalidateQueries({ queryKey: queryKeys.world.all })
    })
    return
  }
  if (changes.entities.length > 0 || changes.removed_entity_ids.length > 0)
    patchEntities(client, changes.entities, changes.removed_entity_ids)
  if (changes.sons.length > 0 || changes.removed_son_ids.length > 0)
    patchSons(client, changes.sons, changes.removed_son_ids)
  if (changes.new_chronicle_lines > 0)
    later(client, 'chronicle', (key) => keyHas(key, 'chronicle'))
  if (changes.bonds_changed)
    later(
      client,
      'bonds',
      (key) => keyHas(key, 'bonds') || keyHas(key, 'graph')
    )
  if (changes.cosmos_changed || changes.worlds_changed)
    later(
      client,
      'cosmos',
      (key) => keyHas(key, 'cosmos') || keyHas(key, 'state')
    )
  if (changes.relations_changed)
    later(client, 'relations', (key) => keyHas(key, 'relations'))
  if (changes.foreign_god_ids.length > 0)
    later(client, 'foreign', (key) => keyHas(key, 'foreign-gods'))
  if (changes.entities.length > 0 || changes.removed_entity_ids.length > 0)
    later(client, 'entity-lists', (key) => keyHas(key, 'entities'))
}
