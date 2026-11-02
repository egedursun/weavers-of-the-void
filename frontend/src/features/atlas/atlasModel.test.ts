import { describe, expect, it } from 'vitest'
import {
  type CosmosView,
  type EntitySummary,
  type WorldState,
} from '@/features/entity/api/types'
import {
  allKeys,
  buildAtlasTree,
  flattenVisible,
  isFiltering,
  matchesEntity,
  pruneTree,
  sortList,
} from './atlasModel'
import { parseSelection, validateAtlasSearch } from './atlasSearch'

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
    expect(parseSelection('son:11')).toEqual({ kind: 'son', id: 11 })
    expect(parseSelection(null)).toBeNull()
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
