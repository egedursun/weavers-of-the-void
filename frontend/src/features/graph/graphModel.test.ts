import { describe, expect, it } from 'vitest'
import { type FullGraph } from './api'
import { familyOf } from './families'
import {
  IN_WORLD,
  ROUTE,
  buildGraph,
  defaultFocus,
  drawerKindOf,
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
  })

  it('scopes to a world and its route neighbours', () => {
    const scoped = filterGraph(graph, { ...BASE, worldId: 200 })
    expect(scoped.nodes.map((item) => item.id).sort((a, b) => a - b)).toEqual([
      5, 100, 200,
    ])
  })

  it('picks the best connected node as default focus', () => {
    expect(defaultFocus(graph, new Set(), 50)).toBe(3)
    expect(defaultFocus(graph, new Set(['people']), 50)).not.toBe(3)
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
    expect(drawerKindOf('foreign_god')).toBe('foreign-god')
    expect(drawerKindOf('world')).toBe('world')
    expect(findNode([{ id: 1, name: 'Ithren' }], ' ithren ')?.id).toBe(1)
    expect(validateGraphSearch({ from: '4', to: '9', focus: '0' })).toEqual({
      from: 4,
      to: 9,
    })
  })
})
