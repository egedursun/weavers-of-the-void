import { describe, expect, it } from 'vitest'
import { type FullGraph } from './api'
import { familyOf } from './families'
import {
  IN_WORLD,
  ROUTE,
  buildGraph,
  defaultFocus,
  entryKindOf,
  filterGraph,
  findNode,
  linkGroupIndex,
  linkLabel,
} from './graphModel'
import { validateGraphSearch } from './graphRouteSearch'

const node = (
  id: number,
  type: string,
  extra: Partial<FullGraph['nodes'][number]> = {}
) => ({
  id,
  kind: 'entity' as const,
  name: `Node ${id}`,
  type,
  size: 3,
  epoch: 1,
  status: 'canon',
  world_id: 100,
  location_id: null,
  creator_son_id: null,
  ...extra,
})

const link = (source: number, target: number, kind: string, epoch = 1) => ({
  source,
  target,
  kind: kind as FullGraph['links'][number]['kind'],
  epoch,
  past: false,
})

const FULL: FullGraph = {
  nodes: [
    node(1, 'son', { kind: 'son' }),
    node(2, 'region'),
    node(3, 'people', { location_id: 2, creator_son_id: 1 }),
    node(4, 'settlement', { location_id: 2, epoch: 5 }),
    node(5, 'mortal', { world_id: 200 }),
  ],
  links: [
    link(3, 2, 'inside'),
    link(4, 2, 'inside', 5),
    link(3, 4, 'enemy', 3),
    link(5, 3, 'knows'),
  ],
  nodeTotal: 5,
  linkTotal: 4,
}

const WORLDS = [
  { id: 100, name: 'First', createdEpoch: 1 },
  { id: 200, name: 'Second', createdEpoch: 2 },
]

const ROUTES = [
  { id: 1, first: 100, second: 200, active: true, epoch: 2, description: null },
]

const GROUP_INDEX = linkGroupIndex([
  {
    key: 'all',
    label: 'All links',
    kinds: ['inside', 'enemy', 'knows', 'route', 'in_world', 'created'],
  },
  { key: 'conflict', label: 'Conflict', kinds: ['enemy'] },
  { key: 'knowledge', label: 'Knowledge', kinds: ['knows'] },
])

const BASE = {
  group: 'all' as const,
  epoch: null,
  hiddenTypes: new Set<string>(),
  worldId: null,
  focusId: null,
  whole: true,
  autoLinks: 50,
  radius: 2,
  cap: 1000,
}

describe('graph building', () => {
  it('adds worlds, routes, root links and creator links across worlds', () => {
    const graph = buildGraph(FULL, WORLDS, ROUTES, GROUP_INDEX)
    expect(graph.nodes.filter((item) => item.kind === 'world')).toHaveLength(2)
    expect(graph.links.some((item) => item.kind === ROUTE)).toBe(true)
    expect(
      graph.links.some((item) => item.kind === IN_WORLD && item.source === 2)
    ).toBe(true)
    expect(
      graph.links.some((item) => item.kind === 'created' && item.target === 3)
    ).toBe(true)
  })

  it('stays single-world without synthetic nodes', () => {
    const graph = buildGraph(FULL, WORLDS.slice(0, 1), [], GROUP_INDEX)
    expect(graph.nodes.some((item) => item.kind === 'world')).toBe(false)
  })
})

describe('graph filtering', () => {
  const graph = buildGraph(FULL, WORLDS, ROUTES, GROUP_INDEX)

  it('filters by link group, epoch and hidden type', () => {
    const conflict = filterGraph(graph, { ...BASE, group: 'conflict' })
    expect(conflict.links.map((item) => item.kind)).toEqual(['enemy'])
    expect(conflict.nodes.map((item) => item.id).sort()).toEqual([3, 4])
    const early = filterGraph(graph, { ...BASE, epoch: 2 })
    expect(early.nodes.some((item) => item.id === 4)).toBe(false)
    const hidden = filterGraph(graph, {
      ...BASE,
      hiddenTypes: new Set(['people']),
    })
    expect(
      hidden.links.some((item) => item.source === 3 || item.target === 3)
    ).toBe(false)
  })

  it('keeps the focus neighbourhood and reduces the radius over the cap', () => {
    const near = filterGraph(graph, { ...BASE, focusId: 4, radius: 1 })
    expect(near.nodes.map((item) => item.id).sort()).toEqual([2, 3, 4])
    const capped = filterGraph(graph, {
      ...BASE,
      focusId: 4,
      radius: 3,
      cap: 3,
    })
    expect(capped.reduced).toBe(true)
    expect(capped.radius).toBe(1)
    expect(capped.nodes).toHaveLength(3)
  })

  it('fills the view up to the cap with the best-connected records of the next step', () => {
    const wide: FullGraph = {
      nodes: [1, 2, 3, 4, 5, 6, 7].map((id) => node(id, 'mortal')),
      links: [
        link(1, 2, 'knows'),
        link(1, 3, 'knows'),
        link(2, 4, 'knows'),
        link(3, 5, 'knows'),
        link(3, 6, 'knows'),
        link(6, 7, 'knows'),
        link(5, 7, 'knows'),
      ],
      nodeTotal: 7,
      linkTotal: 7,
    }
    const graph = buildGraph(wide, WORLDS.slice(0, 1), [], GROUP_INDEX)
    const filled = filterGraph(graph, {
      ...BASE,
      focusId: 1,
      radius: 2,
      cap: 5,
    })
    expect(filled.nodes.map((item) => item.id).sort()).toEqual([1, 2, 3, 5, 6])
    expect(filled.radius).toBe(1)
    expect(filled.partial).toBe(2)
    expect(filled.reduced).toBe(true)
    const crowded = filterGraph(graph, {
      ...BASE,
      focusId: 3,
      radius: 1,
      cap: 2,
    })
    expect(crowded.nodes).toHaveLength(2)
    expect(crowded.radius).toBe(0)
  })

  it('scopes to a world and its route neighbours', () => {
    const scoped = filterGraph(graph, { ...BASE, worldId: 200 })
    expect(scoped.nodes.map((item) => item.id).sort((a, b) => a - b)).toEqual([
      5, 100, 200,
    ])
  })

  it('keeps the cap when the focus is outside the chosen world', () => {
    const scoped = filterGraph(graph, { ...BASE, worldId: 200, cap: 1 })
    expect(scoped.nodes).toHaveLength(3)
    const capped = filterGraph(graph, {
      ...BASE,
      worldId: 200,
      whole: false,
      cap: 1,
    })
    expect(capped.nodes).toHaveLength(1)
    expect(capped.focusId).not.toBeNull()
    expect([5, 100, 200]).toContain(capped.focusId)
    const stray = filterGraph(graph, {
      ...BASE,
      worldId: 200,
      whole: false,
      focusId: 3,
      cap: 1,
    })
    expect(stray.strayFocus).toBe(true)
    expect(stray.focusId).not.toBe(3)
    expect(stray.nodes).toHaveLength(1)
    const kept = filterGraph(graph, { ...BASE, focusId: 4, cap: 2 })
    expect(kept.strayFocus).toBe(false)
    expect(kept.focusId).toBe(4)
    expect(kept.nodes.length).toBeLessThanOrEqual(2)
  })

  it('never shows more records than the cap unless the whole network is asked for', () => {
    const ids = graph.nodes.map((item) => item.id)
    const types = [...new Set(graph.nodes.map((item) => item.type))]
    for (const worldId of [null, 100, 200])
      for (const epoch of [null, 1, 2, 5])
        for (const hidden of [[], ...types.map((type) => [type])])
          for (const focusId of [null, ...ids, 9999])
            for (const cap of [1, 2, 3])
              for (const radius of [1, 2, 3]) {
                const view = filterGraph(graph, {
                  ...BASE,
                  worldId,
                  epoch,
                  hiddenTypes: new Set(hidden),
                  focusId,
                  whole: false,
                  cap,
                  radius,
                })
                expect(view.nodes.length).toBeLessThanOrEqual(cap)
                if (view.focusId !== null)
                  expect(view.nodes.map((item) => item.id)).toContain(
                    view.focusId
                  )
              }
  })

  it('picks the best connected node as default focus', () => {
    expect(defaultFocus(graph, new Set(), 50)).toBe(3)
    expect(defaultFocus(graph, new Set(['people']), 50)).not.toBe(3)
  })

  it('never focuses a record with no bonds in the view while a bonded one exists', () => {
    const lonely: FullGraph = {
      nodes: [
        node(1, 'creator', { kind: 'creator', size: 14, world_id: null }),
        node(2, 'people'),
        node(3, 'people'),
      ],
      links: [link(2, 3, 'knows')],
      nodeTotal: 3,
      linkTotal: 1,
    }
    const graph = buildGraph(lonely, WORLDS.slice(0, 1), [], GROUP_INDEX)
    expect(defaultFocus(graph, new Set(), 50)).not.toBe(1)
    const view = filterGraph(graph, { ...BASE, whole: false, cap: 100 })
    expect(view.nodes.length).toBe(2)
  })
})

describe('graph helpers', () => {
  it('labels links, families, drawers and finds nodes by name', () => {
    expect(
      linkLabel({ kind: 'enemy', past: true }, new Map([['enemy', 'enemy of']]))
    ).toBe('formerly enemy of')
    expect(linkLabel({ kind: 'in world', past: false }, new Map())).toBe(
      'in this world'
    )
    expect(familyOf('settlement').key).toBe('places')
    expect(familyOf('unknown').key).toBe('other')
    expect(entryKindOf('foreign_god')).toBe('foreign-god')
    expect(entryKindOf('world')).toBe('world')
    expect(findNode([{ id: 1, name: 'Ithren' }], ' ithren ')?.id).toBe(1)
    expect(validateGraphSearch({ from: '4', to: '9', focus: '0' })).toEqual({
      from: 4,
      to: 9,
    })
  })
})
