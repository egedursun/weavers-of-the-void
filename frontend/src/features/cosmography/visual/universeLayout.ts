import { unitHash } from '@/lib/hash'
import { type ClusterRecord, type GalaxyRecord, type RouteRecord } from '../api'
import { type Ladder } from '../ladder'

export type Vec3 = [number, number, number]

export type PlacedDimension = {
  id: number
  y: number
  radius: number
  index: number
}

export type PlacedCluster = { id: number; position: Vec3; size: number }

export type PlacedGalaxy = {
  id: number
  position: Vec3
  size: number
  tilt: number
  turn: number
}

export type GalaxyLink = {
  key: string
  from: number
  to: number
  method: RouteRecord['method']
  count: number
}

export type UniverseLayout = {
  dimensions: Map<number, PlacedDimension>
  clusters: Map<number, PlacedCluster>
  galaxies: Map<number, PlacedGalaxy>
  links: GalaxyLink[]
  extent: number
}

const PLANE_GAP = 1500
const TARGET = 1300
const MIN_PLANE = 760
const MIN_GALAXY = 70
const MIN_CLUSTER = 160
const CLUSTER_MARGIN = 1.35
const PLANE_MARGIN = 1.18
const MIN_TILT = 0.15
const TILT_RANGE = 0.75

function rawExtent(
  clusters: readonly ClusterRecord[],
  galaxies: readonly GalaxyRecord[]
): number {
  let extent = 1
  for (const row of clusters)
    extent = Math.max(extent, Math.hypot(row.x, row.y) + row.radius)
  for (const row of galaxies)
    extent = Math.max(extent, Math.hypot(row.x, row.y) + row.radius)
  return extent
}

function typicalRadius(
  ladder: Ladder,
  tops: readonly ClusterRecord[],
  loose: readonly GalaxyRecord[]
): number {
  const radii = loose.map((row) => row.radius)
  const walk = (cluster: ClusterRecord, seen: Set<number>) => {
    if (seen.has(cluster.id)) return
    seen.add(cluster.id)
    for (const galaxy of ladder.galaxiesIn(cluster.id))
      radii.push(galaxy.radius)
    for (const child of ladder.childClusters(cluster.id)) walk(child, seen)
  }
  const seen = new Set<number>()
  for (const cluster of tops) walk(cluster, seen)
  if (radii.length === 0) return Infinity
  const sorted = radii.sort((a, b) => a - b)
  return Math.max(sorted[Math.floor(sorted.length / 2)] ?? 1, 1)
}

function dimensionOrder(ladder: Ladder): number[] {
  const rows = ladder.data.dimensions
  const depth = (id: number): number => {
    let level = 0
    let current = rows.find((row) => row.id === id)
    const seen = new Set<number>()
    while (current?.parent_dimension_id != null && !seen.has(current.id)) {
      seen.add(current.id)
      level += 1
      const parent = current.parent_dimension_id
      current = rows.find((row) => row.id === parent)
    }
    return level
  }
  return [...rows]
    .sort((left, right) => {
      const prime =
        Number(right.dimension_kind === 'prime') -
        Number(left.dimension_kind === 'prime')
      return prime || depth(left.id) - depth(right.id) || left.id - right.id
    })
    .map((row) => row.id)
}

export function universeLayout(
  ladder: Ladder,
  routes: readonly RouteRecord[]
): UniverseLayout {
  const dimensions = new Map<number, PlacedDimension>()
  const clusters = new Map<number, PlacedCluster>()
  const galaxies = new Map<number, PlacedGalaxy>()
  const order = dimensionOrder(ladder)
  let extent = MIN_PLANE
  order.forEach((dimensionId, index) => {
    const tops = ladder.clustersIn(dimensionId)
    const loose = ladder.looseGalaxies(dimensionId)
    const scale = Math.max(
      TARGET / rawExtent(tops, loose),
      MIN_GALAXY / typicalRadius(ladder, tops, loose)
    )
    const y = -index * PLANE_GAP
    const placeCluster = (
      cluster: ClusterRecord,
      origin: Vec3,
      depth: number
    ): PlacedCluster => {
      const position: Vec3 = [
        origin[0] + cluster.x * scale,
        y + depth * 30,
        origin[2] + cluster.y * scale,
      ]
      const held = [
        ...ladder
          .galaxiesIn(cluster.id)
          .map((galaxy) => placeGalaxy(galaxy, position)),
        ...ladder
          .childClusters(cluster.id)
          .map((child) => placeCluster(child, position, depth + 1)),
      ]
      const reach = held.reduce(
        (best, inner) =>
          Math.max(
            best,
            Math.hypot(
              inner.position[0] - position[0],
              inner.position[2] - position[2]
            ) + inner.size
          ),
        0
      )
      const placed = {
        id: cluster.id,
        position,
        size: Math.max(reach * CLUSTER_MARGIN, MIN_CLUSTER),
      }
      clusters.set(cluster.id, placed)
      return placed
    }
    const placeGalaxy = (galaxy: GalaxyRecord, origin: Vec3): PlacedGalaxy => {
      const placed: PlacedGalaxy = {
        id: galaxy.id,
        position: [
          origin[0] + galaxy.x * scale,
          origin[1] + 40,
          origin[2] + galaxy.y * scale,
        ],
        size: Math.max(galaxy.radius * scale, MIN_GALAXY),
        tilt: MIN_TILT + unitHash(`galaxy-tilt-${galaxy.id}`) * TILT_RANGE,
        turn: unitHash(`galaxy-turn-${galaxy.id}`) * Math.PI * 2,
      }
      galaxies.set(galaxy.id, placed)
      return placed
    }
    for (const cluster of tops) placeCluster(cluster, [0, y, 0], 0)
    for (const galaxy of loose) placeGalaxy(galaxy, [0, y, 0])
    const reach = [
      ...tops.map((cluster) => clusters.get(cluster.id)),
      ...loose.map((galaxy) => galaxies.get(galaxy.id)),
    ].reduce(
      (best, placed) =>
        placed
          ? Math.max(
              best,
              Math.hypot(placed.position[0], placed.position[2]) + placed.size
            )
          : best,
      0
    )
    const radius = Math.max(reach * PLANE_MARGIN, MIN_PLANE)
    extent = Math.max(extent, radius)
    dimensions.set(dimensionId, { id: dimensionId, y, radius, index })
  })
  const galaxyOfWorld = new Map(
    ladder.data.placements.map((row) => [row.world_id, row.galaxy_id])
  )
  const grouped = new Map<string, GalaxyLink>()
  for (const route of routes) {
    const from = galaxyOfWorld.get(route.world_a_id)
    const to = galaxyOfWorld.get(route.world_b_id)
    if (from == null || to == null || from === to) continue
    const key =
      from < to
        ? `${from}-${to}-${route.method}`
        : `${to}-${from}-${route.method}`
    const found = grouped.get(key)
    if (found) found.count += 1
    else
      grouped.set(key, {
        key,
        from: Math.min(from, to),
        to: Math.max(from, to),
        method: route.method,
        count: 1,
      })
  }
  return {
    dimensions,
    clusters,
    galaxies,
    links: [...grouped.values()],
    extent: extent + (order.length - 1) * PLANE_GAP * 0.5,
  }
}
