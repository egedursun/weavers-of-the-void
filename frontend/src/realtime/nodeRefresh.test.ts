import { QueryClient } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { queryKeys } from '@/api/queryKeys'
import { EVENT_KINDS, type EventKind, type ServerEvent } from './events'
import { resetIdleGate } from './idleGate'
import { applyServerEvent, invalidationsFor } from './invalidation'
import { mentionsNode, showsNode } from './nodeRefresh'

const AT = '2026-01-01T00:00:00+00:00'
const WORLD = queryKeys.world.all[0]
const STREAMING_PREFIXES = ['image.', 'agent.']
const STREAMING_KINDS = new Set<EventKind>([
  'job.progress',
  'epoch.progress',
  'engine.note',
  'engine.phase',
  'fate.step',
  'son.turn_started',
  'mortal.turn_started',
  'batch_deepen.log',
])

function imageDone(nodeId: number): ServerEvent {
  return {
    id: nodeId,
    kind: 'image.done',
    payload: { node_id: nodeId, image_id: 1, file: 'a.png', cover: false },
    at: AT,
  } as ServerEvent
}

function seeded(): QueryClient {
  const client = new QueryClient()
  client.setQueryData([WORLD, 'state'], { creator_cover: null })
  client.setQueryData([WORLD, 'opportunities'], { sons_without_image: 1 })
  client.setQueryData(
    [WORLD, 'entities', 'all'],
    [
      { id: 7, cover: null },
      { id: 8, cover: 'b.png' },
    ]
  )
  client.setQueryData([WORLD, 'cosmos'], {
    worlds: [{ world: { id: 3 }, cover: null }],
  })
  client.setQueryData([WORLD, 'entity', 9], { entity: { id: 9 } })
  client.setQueryData([WORLD, 'chronicle'], [{ line_id: 1, text: 'x' }])
  return client
}

function refreshedKeys(client: QueryClient): string[] {
  return client
    .getQueryCache()
    .getAll()
    .filter((query) => query.state.isInvalidated)
    .map((query) => JSON.stringify(query.queryKey))
    .sort()
}

describe('refreshing the views of one node', () => {
  beforeEach(() => resetIdleGate())

  it('finds a node by any id field, nested or listed', () => {
    expect(mentionsNode({ entity: { id: 4 } }, 4)).toBe(true)
    expect(mentionsNode({ items: [{ son_id: 4 }] }, 4)).toBe(true)
    expect(mentionsNode({ member_ids: [1, 4] }, 4)).toBe(true)
    expect(mentionsNode({ count: 4, population: 4 }, 4)).toBe(false)
    expect(mentionsNode(undefined, 4)).toBe(false)
  })

  it('treats the world state and the hints as showing every node', () => {
    const client = seeded()
    const state = client.getQueryCache().find({ queryKey: [WORLD, 'state'] })
    const chronicle = client
      .getQueryCache()
      .find({ queryKey: [WORLD, 'chronicle'] })
    expect(state && showsNode(state, 99)).toBe(true)
    expect(chronicle && showsNode(chronicle, 99)).toBe(false)
  })

  it('refreshes only the queries that show the painted node on image.done', async () => {
    const client = seeded()
    const invalidate = vi.spyOn(client, 'invalidateQueries')
    applyServerEvent(client, imageDone(3))
    await vi.waitFor(() =>
      expect(refreshedKeys(client)).toEqual(
        [
          [WORLD, 'cosmos'],
          [WORLD, 'opportunities'],
          [WORLD, 'state'],
        ]
          .map((key) => JSON.stringify(key))
          .sort()
      )
    )
    expect(invalidate).not.toHaveBeenCalledWith({
      queryKey: queryKeys.world.all,
    })
  })

  it('refreshes the views of each painted node and leaves the rest', async () => {
    const client = seeded()
    applyServerEvent(client, imageDone(7))
    applyServerEvent(client, imageDone(9))
    await vi.waitFor(() =>
      expect(refreshedKeys(client)).toContain(
        JSON.stringify([WORLD, 'entity', 9])
      )
    )
    expect(refreshedKeys(client)).toContain(
      JSON.stringify([WORLD, 'entities', 'all'])
    )
    expect(refreshedKeys(client)).not.toContain(
      JSON.stringify([WORLD, 'chronicle'])
    )
  })

  it('never lets a streaming event refetch the whole world', () => {
    const streaming = EVENT_KINDS.filter(
      (kind) =>
        STREAMING_KINDS.has(kind) ||
        STREAMING_PREFIXES.some((prefix) => kind.startsWith(prefix))
    )
    expect(streaming.length).toBeGreaterThan(5)
    for (const kind of streaming) {
      const keys = invalidationsFor({
        id: 1,
        kind,
        payload: { job_id: 'a', node_id: 1 },
        at: AT,
      } as ServerEvent)
      expect(keys, kind).not.toContainEqual(queryKeys.world.all)
    }
  })
})
