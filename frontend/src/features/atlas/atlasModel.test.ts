import { describe, expect, it } from 'vitest'
import { parseTypeKey } from '@/features/city/typeKeys'
import {
  type CosmosView,
  type EntitySummary,
  type WorldState,
} from '@/features/entity/api/types'
import {
  allKeys,
  buildAtlasTree,
  drawerFor,
  flattenVisible,
  isFiltering,
  matchesEntity,
  pruneTree,
  sortList,
} from './atlasModel'
import { validateAtlasSearch } from './atlasSearch'

function entity(
  id: number,
  name: string,
  type: string,
  location: number | null = null,
  extra: Partial<EntitySummary> = {}
): EntitySummary {
  return {
    id,
    name,
    title: null,
    entity_type: type,
    subtype: null,
    status: 'canon',
    world_id: 1,
    location_id: location,
    power_level: id,
    birth_epoch: id,
    end_epoch: null,
    importance: null,
    favorite: false,
    pending_name: false,
    ...extra,
  } as EntitySummary
}

const ENTITIES = [
  entity(1, 'Ashreach', 'region'),
  entity(2, 'Velmora', 'settlement', 1),
  entity(3, 'The Salt Song', 'legend'),
  entity(4, 'Orun the Pale', 'mortal', 2, { favorite: true }),
]

const COSMOS = {
  stars: [{ id: 5, name: 'Iridel' }],
  worlds: [
    {
      world: { id: 1, name: 'Aerona', star_id: 5, parent_world_id: null },
      type_label: 'Living world',
    },
  ],
  foreign_gods: [{ id: 8, name: 'Old Moth', title: null, world_id: 1 }],
} as unknown as CosmosView

const STATE = {
  creator: { id: 100, name: 'The Maker', title: null },
  sons: [
    {
      son: {
        id: 11,
        name: 'Ithren',
        title: 'the Unbowed',
        parent_son_id: null,
      },
    },
    { son: { id: 12, name: 'Sael', title: 'the Second', parent_son_id: 11 } },
  ],
  worlds: [{ id: 1, name: 'Aerona' }],
} as unknown as WorldState

describe('atlas building types', () => {
  it('files buildings under their type and homes under their kind, never one entry per building', () => {
    const buildings = new Map([
      [
        1,
        {
          world_id: 1,
          structures: [
            {
              kind: 'school',
              label: 'School',
              instances: [{ node: { id: 30 } }, { node: { id: 31 } }],
            },
            { kind: 'temple', label: 'Temple', instances: [] },
          ],
          dwellings: [
            { housing: 'cottage', districts: 2, dwellings: 40, towns: [] },
            { housing: 'manor', districts: 0, dwellings: 0, towns: [] },
          ],
        },
      ],
    ]) as unknown as Parameters<typeof buildAtlasTree>[0]['buildings']
    const tree = buildAtlasTree({
      entities: [
        ...ENTITIES,
        entity(30, 'North School', 'structure', 2),
        entity(31, 'South School', 'structure', 2),
      ],
      state: STATE,
      cosmos: COSMOS,
      types: [],
      buildings,
    })
    const keys = flattenVisible(tree, new Set(allKeys(tree))).map(
      (row) => row.node.key
    )
    expect(keys).toContain('building-type:1:school')
    expect(keys).toContain('dwelling-type:1:cottage')
    expect(keys).not.toContain('building-type:1:temple')
    expect(keys).not.toContain('dwelling-type:1:manor')
    expect(keys).not.toContain('entity:30')
    expect(keys).not.toContain('entity:31')
    expect(parseTypeKey('building-type:1:school')).toEqual({
      kind: 'building',
      worldId: 1,
      type: 'school',
    })
    expect(parseTypeKey('dwelling-type:1:cottage')).toEqual({
      kind: 'dwelling',
      worldId: 1,
      type: 'cottage',
    })
    expect(parseTypeKey('entity:3')).toBeNull()
  })
})

describe('atlas tree', () => {
  const tree = buildAtlasTree({
    entities: ENTITIES,
    state: STATE,
    cosmos: COSMOS,
    types: [],
  })

  it('nests the pantheon, the cosmos, places and loose records', () => {
    const keys = allKeys(tree)
    expect(keys).toEqual(
      expect.arrayContaining([
        'group:pantheon',
        'creator:100',
        'son:11',
        'group:cosmos',
        'star:5',
        'world:1',
        'entity:1',
        'entity:2',
      ])
    )
    const rows = flattenVisible(tree, new Set(keys)).map((row) => row.node.key)
    expect(rows.indexOf('entity:2')).toBeGreaterThan(rows.indexOf('entity:1'))
    expect(rows).toContain('entity:4')
    expect(rows).toContain('group:1:legend')
    expect(rows).toContain('foreign-god:8')
  })

  it('sets galaxies, clusters and dimensions above their stars', () => {
    const heavens = {
      dimensions: [
        {
          id: 40,
          name: 'Prime',
          dimension_kind: 'prime',
          parent_dimension_id: null,
        },
      ],
      clusters: [
        {
          id: 41,
          name: 'Home Group',
          cluster_kind: 'local_group',
          parent_cluster_id: null,
          dimension_id: 40,
        },
      ],
      galaxies: [
        {
          id: 42,
          name: 'Home Wheel',
          galaxy_type: 'spiral',
          cluster_id: 41,
          dimension_id: null,
        },
      ],
      stars: [{ id: 5, galaxy_id: 42 }],
      placements: [{ world_id: 1, galaxy_id: 42, dimension_id: 40 }],
    } as unknown as Parameters<typeof buildAtlasTree>[0]['heavens']
    const placed = buildAtlasTree({
      entities: ENTITIES,
      state: STATE,
      cosmos: COSMOS,
      heavens,
      types: [],
    })
    const rows = flattenVisible(placed, new Set(allKeys(placed))).map(
      (row) => row.node.key
    )
    expect(rows.indexOf('dimension:40')).toBeLessThan(
      rows.indexOf('cluster:41')
    )
    expect(rows.indexOf('cluster:41')).toBeLessThan(rows.indexOf('galaxy:42'))
    expect(rows.indexOf('galaxy:42')).toBeLessThan(rows.indexOf('star:5'))
    expect(rows.indexOf('star:5')).toBeLessThan(rows.indexOf('world:1'))
  })

  it('keeps only branches with a match while filtering', () => {
    const filters = {
      q: 'orun',
      type: null,
      status: 'visible',
      favorites: false,
    }
    const pruned = pruneTree(
      tree,
      (node) =>
        node.kind === 'entity' &&
        node.entity !== undefined &&
        matchesEntity(node.entity, filters)
    )
    const rows = flattenVisible(pruned, new Set(allKeys(pruned))).map(
      (row) => row.node.key
    )
    expect(rows).toEqual([
      'group:cosmos',
      'star:5',
      'world:1',
      'entity:1',
      'entity:2',
      'entity:4',
    ])
  })

  it('filters favourites and sorts the list', () => {
    expect(
      ENTITIES.filter((item) =>
        matchesEntity(item, {
          q: '',
          type: null,
          status: 'visible',
          favorites: true,
        })
      ).map((item) => item.id)
    ).toEqual([4])
    expect(sortList(ENTITIES, 'epoch', true).map((item) => item.id)).toEqual([
      4, 3, 2, 1,
    ])
    expect(sortList(ENTITIES, 'name', false)[0].name).toBe('Ashreach')
  })

  it('validates the atlas address', () => {
    expect(
      validateAtlasSearch({
        q: 'salt',
        view: 'list',
        sort: 'bogus',
        page: '2',
        select: 'entity:4',
      })
    ).toEqual({ q: 'salt', view: 'list', page: 2, select: 'entity:4' })
  })

  it('keeps only the chosen world under the global world filter', () => {
    const filters = { q: '', type: null, status: 'visible', favorites: false }
    const worlds = new Set(ENTITIES.map((item) => item.world_id))
    const first = ENTITIES[0].world_id
    const kept = ENTITIES.filter((item) =>
      matchesEntity(item, { ...filters, world: first })
    )
    expect(kept.every((item) => item.world_id === first)).toBe(true)
    expect(kept.length).toBeGreaterThan(0)
    expect(isFiltering({ ...filters, world: first })).toBe(true)
    expect(isFiltering(filters)).toBe(false)
    expect(worlds.size).toBeGreaterThan(0)
    expect(validateAtlasSearch({ world: '3' })).toEqual({ world: 3 })
    expect(validateAtlasSearch({ world: 'x' })).toEqual({})
  })
})

describe('drawerFor', () => {
  const node = (
    kind: Parameters<typeof drawerFor>[0]['kind'],
    id?: number
  ) => ({
    key: `${kind}:${id ?? ''}`,
    label: kind,
    kind,
    id,
    children: [],
  })

  it('opens every record and every node of the heavens in its own drawer', () => {
    expect(drawerFor(node('entity', 7))).toEqual({ kind: 'entity', id: '7' })
    expect(drawerFor(node('son', 2))).toEqual({ kind: 'son', id: '2' })
    expect(drawerFor(node('foreign-god', 3))).toEqual({
      kind: 'foreign-god',
      id: '3',
    })
    for (const kind of [
      'world',
      'star',
      'galaxy',
      'cluster',
      'dimension',
    ] as const)
      expect(drawerFor(node(kind, 5))).toEqual({ kind, id: '5' })
    expect(drawerFor(node('creator'))).toEqual({ kind: 'creator' })
  })

  it('keeps groups and type pages in the atlas pane', () => {
    expect(drawerFor(node('group'))).toBeNull()
    expect(drawerFor(node('building-type', 4))).toBeNull()
    expect(drawerFor(node('dwelling-type', 4))).toBeNull()
    expect(drawerFor(node('entity'))).toBeNull()
  })
})
