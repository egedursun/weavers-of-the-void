import { describe, expect, it } from 'vitest'
import { webCloud, webStrands } from './cosmicWeb'
import { type UniverseLayout } from './universeLayout'

const PLANE = { id: 1, y: 0, radius: 3000, index: 0 }

function layoutOf(
  clusters: { id: number; x: number; z: number; size: number; y?: number }[]
): UniverseLayout {
  return {
    dimensions: new Map([
      [1, PLANE],
      [2, { id: 2, y: -1500, radius: 3000, index: 1 }],
    ]),
    clusters: new Map(
      clusters.map((row) => [
        row.id,
        { id: row.id, position: [row.x, row.y ?? 0, row.z], size: row.size },
      ])
    ),
    orbs: new Map(),
    rings: [],
    galaxies: new Map(),
    links: [],
    extent: 3000,
  }
}

const token = (id: number) => `--cluster-${id}`

describe('the cosmic web', () => {
  it('ties each cluster to its nearest neighbours once', () => {
    const strands = webStrands(
      layoutOf([
        { id: 1, x: 0, z: 0, size: 200 },
        { id: 2, x: 1000, z: 0, size: 200 },
        { id: 3, x: 0, z: 1000, size: 200 },
        { id: 4, x: 2600, z: 2600, size: 200 },
      ]),
      token
    )
    const keys = strands.map((strand) => strand.key)
    expect(new Set(keys).size).toBe(keys.length)
    expect(keys).toEqual(expect.arrayContaining(['1-2', '1-3']))
    expect(strands.find((strand) => strand.key === '1-2')?.toToken).toBe(
      '--cluster-2'
    )
  })

  it('leaves out clusters held inside another and clusters of other dimensions', () => {
    const strands = webStrands(
      layoutOf([
        { id: 1, x: 0, z: 0, size: 900 },
        { id: 2, x: 300, z: 0, size: 200 },
        { id: 3, x: 1500, z: 0, size: 200, y: -1500 },
      ]),
      token
    )
    expect(strands).toEqual([])
  })

  it('lays finite points along every strand', () => {
    const strands = webStrands(
      layoutOf([
        { id: 1, x: 0, z: 0, size: 200 },
        { id: 2, x: 1800, z: 400, size: 200 },
      ]),
      token
    )
    const cloud = webCloud(strands, () => [0.5, 0.6, 0.9])
    expect(cloud.count).toBeGreaterThan(0)
    expect(cloud.positions.every(Number.isFinite)).toBe(true)
    expect(cloud.colors.every((value) => value >= 0)).toBe(true)
  })
})
