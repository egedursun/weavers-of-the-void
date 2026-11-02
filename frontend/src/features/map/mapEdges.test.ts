import { describe, expect, it } from 'vitest'
import { type WorldMap } from './api'
import { cellEdges, domainAnchors, domainEdges } from './mapEdges'

const SQUARE = (x: number) => [x, 0, x + 10, 0, x + 10, 10, x, 10]

const MAP = {
  cells: {
    x: [5, 15, 25],
    y: [5, 5, 5],
    water: [false, false, false],
    known: [1, 1, 0],
    region: [1, 2, 2],
    top_region: [1, 2, 2],
    polygon_offsets: [0, 8, 16, 24],
    polygon_coordinates: [...SQUARE(0), ...SQUARE(10), ...SQUARE(20)],
  },
} as unknown as WorldMap

describe('cell edges', () => {
  it('shares one edge between touching cells', () => {
    const edges = cellEdges(MAP)
    const shared = [...edges.second].filter((cell) => cell !== -1)
    expect(shared).toHaveLength(2)
    expect(edges.first).toHaveLength(10)
  })

  it('draws a border only between known land of different keys', () => {
    const keys = ['a', 'b', 'b']
    const { band } = domainEdges(MAP, (cell) => keys[cell])
    expect([...band].sort()).toEqual([0, 1])
  })

  it('anchors each domain on one of its own known cells', () => {
    const anchors = domainAnchors(MAP, (cell) => (cell === 0 ? 'a' : 'b'))
    expect(anchors.map((anchor) => [anchor.key, anchor.x])).toEqual([
      ['a', 5],
      ['b', 15],
    ])
  })
})
