import { QueryClient } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { applyChanges, type Changes } from './changePatch'
import { resetIdleGate } from './idleGate'

const QUIET: Changes = {
  full: false,
  version: 'v2',
  entities: [],
  removed_entity_ids: [],
  sons: [],
  removed_son_ids: [],
  new_chronicle_lines: 0,
  bonds_changed: false,
  cosmos_changed: false,
  worlds_changed: false,
  relations_changed: false,
  foreign_god_ids: [],
}

describe('change patching', () => {
  beforeEach(() => resetIdleGate())
  afterEach(() => vi.restoreAllMocks())

  it('reloads the world when the server says the change is full', () => {
    const client = new QueryClient()
    const invalidate = vi.spyOn(client, 'invalidateQueries')
    applyChanges(client, { ...QUIET, full: true })
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['world'] })
  })

  it('patches a changed row in an entity list and the detail without a full reload', () => {
    const client = new QueryClient()
    client.setQueryData(['world', 'entities', 'list', {}], {
      items: [
        { id: 5, name: 'Old name', status: 'active' },
        { id: 6, name: 'Other', status: 'active' },
      ],
    })
    client.setQueryData(['world', 'entity', 5], {
      entity: { id: 5, name: 'Old name' },
      cover: null,
    })
    const invalidate = vi.spyOn(client, 'invalidateQueries')
    applyChanges(client, {
      ...QUIET,
      entities: [{ id: 5, name: 'New name', status: 'dead' } as never],
    })
    const list = client.getQueryData<{
      items: { id: number; name: string; status: string }[]
    }>(['world', 'entities', 'list', {}])
    expect(list?.items[0]).toMatchObject({ name: 'New name', status: 'dead' })
    expect(list?.items[1].name).toBe('Other')
    expect(
      client.getQueryData<{ entity: { name: string } }>(['world', 'entity', 5])
        ?.entity.name
    ).toBe('New name')
    expect(invalidate).not.toHaveBeenCalledWith({ queryKey: ['world'] })
  })

  it('removes a gone son from the state', () => {
    const client = new QueryClient()
    client.setQueryData(['world', 'state'], {
      sons: [{ son: { id: 1 } }, { son: { id: 2 } }],
    })
    applyChanges(client, { ...QUIET, removed_son_ids: [1] })
    expect(
      client.getQueryData<{ sons: unknown[] }>(['world', 'state'])?.sons
    ).toHaveLength(1)
  })
})
