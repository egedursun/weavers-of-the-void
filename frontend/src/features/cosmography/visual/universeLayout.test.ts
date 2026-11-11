import { describe, expect, it } from 'vitest'
import { VIEW } from '../cosmographyFixtures'
import { ladderOf } from '../ladder'
import {
  type UniverseLayout,
  type Vec3,
  universeLayout,
} from './universeLayout'

const LONE = {
  ...VIEW,
  clusters: VIEW.clusters.map((row) => ({ ...row, x: 0, y: 0, radius: 4000 })),
  galaxies: VIEW.galaxies.map((row) => ({ ...row, x: 0, y: 0, radius: 900 })),
}

const SPREAD = {
  ...VIEW,
  galaxies: [
    ...VIEW.galaxies,
    { ...VIEW.galaxies[0], id: 9301, x: 1800, y: -600, radius: 300 },
    { ...VIEW.galaxies[0], id: 9302, x: -900, y: 1400, radius: 1200 },
  ],
}

const CROWD = {
  ...VIEW,
  clusters: [
    ...VIEW.clusters,
    ...Array.from({ length: 12 }, (_, index) => ({
      ...VIEW.clusters[0],
      id: 9400 + index,
      name: `Far Group ${index}`,
      x: 40000 * Math.cos(index),
      y: 40000 * Math.sin(index),
      central_galaxy_id: null,
    })),
  ],
  galaxies: [
    ...VIEW.galaxies,
    ...Array.from({ length: 6 }, (_, index) => ({
      ...VIEW.galaxies[0],
      id: 9500 + index,
      name: `Neighbour ${index}`,
      x: (index + 1) * 1500,
      y: 0,
      radius: 600,
    })),
  ],
}

function apart(a: Vec3, b: Vec3): number {
  return Math.hypot(a[0] - b[0], a[2] - b[2])
}

function nested(layout: UniverseLayout, view: typeof VIEW): string[] {
  const ladder = ladderOf(view)
  const outside: string[] = []
  for (const galaxy of view.galaxies) {
    const placed = layout.galaxies.get(galaxy.id)
    const cluster =
      galaxy.cluster_id !== null ? layout.clusters.get(galaxy.cluster_id) : null
    if (!placed || !cluster) continue
    if (apart(placed.position, cluster.position) + placed.size > cluster.size)
      outside.push(`galaxy ${galaxy.id} outside cluster ${cluster.id}`)
  }
  for (const cluster of view.clusters) {
    const placed = layout.clusters.get(cluster.id)
    const plane =
      cluster.dimension_id !== null
        ? layout.dimensions.get(cluster.dimension_id)
        : undefined
    if (!placed || !plane) continue
    if (
      Math.hypot(placed.position[0], placed.position[2]) + placed.size >
      plane.radius
    )
      outside.push(`cluster ${cluster.id} outside its dimension`)
    if (
      ladder.galaxiesIn(cluster.id).length > 0 &&
      placed.size > plane.radius * 0.95
    )
      outside.push(`cluster ${cluster.id} fills its whole dimension`)
  }
  return outside
}

describe('the map of the heavens', () => {
  it('draws every galaxy inside its cluster and every cluster inside its dimension', () => {
    for (const view of [VIEW, LONE, SPREAD])
      expect(nested(universeLayout(ladderOf(view), []), view)).toEqual([])
  })

  it('draws a lone group around its galaxy, not across the whole dimension', () => {
    const layout = universeLayout(ladderOf(LONE), [])
    const cluster = layout.clusters.get(LONE.clusters[0].id)
    const galaxy = layout.galaxies.get(LONE.galaxies[0].id)
    expect(cluster && galaxy).toBeTruthy()
    if (!cluster || !galaxy) return
    expect(cluster.size).toBeLessThan(galaxy.size * 2)
  })

  it('keeps neighbouring galaxies apart in a crowded dimension', () => {
    const layout = universeLayout(ladderOf(CROWD), [])
    const placed = CROWD.galaxies
      .filter((row) => row.id >= 9500)
      .map((row) => layout.galaxies.get(row.id))
    for (let index = 1; index < placed.length; index += 1) {
      const left = placed[index - 1]
      const right = placed[index]
      expect(left && right).toBeTruthy()
      if (!left || !right) continue
      expect(apart(left.position, right.position)).toBeGreaterThan(
        left.size + right.size
      )
    }
  })
})
