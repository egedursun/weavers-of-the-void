import { describe, expect, it } from 'vitest'
import { type MapView } from './api'
import { type PositionedPoint } from './mapModel'
import { type HitTarget } from './mapScene'
import { hoverText } from './mapText'

const THRESHOLDS = {
  town: 500,
  city: 2000,
  greatCity: 8000,
  megacity: 100000,
  conurbation: 1000000,
}
const LABELS = new Map([['ruin', 'Ruin']])

const POINTS = new Map<number, PositionedPoint>([
  [
    1,
    {
      id: 1,
      name: 'Velmora',
      type: 'settlement',
      subtype: 'harbour',
    } as PositionedPoint,
  ],
  [
    2,
    {
      id: 2,
      name: 'Ashreach',
      type: 'region',
      subtype: 'steppe',
    } as PositionedPoint,
  ],
  [
    3,
    {
      id: 3,
      name: 'Salt Wells',
      type: 'region',
      subtype: null,
    } as PositionedPoint,
  ],
  [
    4,
    {
      id: 4,
      name: 'Old Ruin',
      type: 'structure',
      subtype: null,
    } as PositionedPoint,
  ],
])

const VIEW = {
  population: { '1': 3000 },
  settlements: { '1': { tier: 'unknown', previous_population: 2000 } },
  political: {
    '2': {
      ruler_name: 'Kethrani',
      ruler_type: 'polity',
      share: 61.6,
      contested: true,
    },
  },
  occupations: {
    '2': { occupier_id: 1, name: 'Velmora', control: 60, resistance: 30 },
  },
  holy: [
    { cult_id: 5, cult: 'The Quiet Order', holding_id: 4, kind: 'shrine' },
  ],
  geometry: {
    regions: [
      {
        id: 2,
        elevation_class: 'plain',
        coastal: true,
        mean_elevation: 41.6,
        geography: { land_share: 80, river_flow: 12.4 },
        climate: [
          { name: 'arid', share_pct: 70 },
          { name: 'cold', share_pct: 20 },
        ],
        neighbours: [3, 99],
      },
    ],
  },
  wars: [{ id: 9, name: 'War of Wells', started_epoch: 5, ongoing: true }],
  markers: [
    { id: 8, name: 'Black Wall', kind: 'remnant', subtype: 'wall', epoch: 3 },
  ],
  notes: [{ id: 7, text: 'Remember the salt.' }],
} as unknown as MapView

type Hit = { kind: 'entity' | 'region' | 'war' | 'event' | 'note'; id: number }

function text(hit: Hit) {
  return hoverText(
    hit as unknown as HitTarget,
    VIEW,
    POINTS,
    LABELS,
    THRESHOLDS
  )
}

describe('map hover text', () => {
  it('shows a settlement tier, souls and the change since the previous epoch', () => {
    expect(text({ kind: 'entity', id: 1 })).toEqual({
      title: 'Velmora',
      lines: ['City · harbour', '3,000 souls (previous epoch 2,000, +50%)'],
    })
  })

  it('names other entity types through the catalogue labels', () => {
    expect(text({ kind: 'entity', id: 4 })?.lines).toEqual([
      'Structure',
      'Holy to The Quiet Order: shrine',
    ])
  })

  it('describes a region with terrain, climate, neighbours and its ruler', () => {
    expect(text({ kind: 'region', id: 2 })?.lines).toEqual([
      'steppe · plains, coastal',
      'arid 70%, cold 20%',
      'Mean height 42 · 80% land · river flow 12',
      'Neighbours: Salt Wells',
      'Ruler: Kethrani (polity) 62% · contested',
      'Occupied by Velmora · control 60%, resistance 30%',
    ])
  })

  it('describes wars, event markers and notes', () => {
    expect(text({ kind: 'war', id: 9 })).toEqual({
      title: 'War of Wells',
      lines: ['Epoch 5 · ongoing'],
    })
    expect(text({ kind: 'event', id: 8 })).toEqual({
      title: 'Black Wall',
      lines: ['Relic · wall · Epoch 3'],
    })
    expect(text({ kind: 'note', id: 7 })).toEqual({
      title: 'Your note',
      lines: ['Remember the salt.'],
    })
  })

  it('returns nothing for a target that no longer exists', () => {
    expect(text({ kind: 'entity', id: 404 })).toBeNull()
    expect(text({ kind: 'war', id: 404 })).toBeNull()
    expect(text({ kind: 'note', id: 404 })).toBeNull()
  })
})
