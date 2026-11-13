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

export type PlacedOrb = {
  id: number
  position: Vec3
  size: number
  parentId: number | null
}

export type OrbRing = { radius: number; y: number }

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
  orbs: Map<number, PlacedOrb>
  rings: OrbRing[]
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
const ORB_SIZE = 165
const SMALL_ORB = 0.75
const SMALL_KINDS = new Set(['pocket', 'bubble_universe', 'compactified'])
const ORB_RING = 1.18
const ORB_SPACING = 3.8
const ORB_RING_STEP = 4.2
const ORB_LIFT = 140
const ORB_WAVE = 0.9
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

function holdsSpace(ladder: Ladder, dimensionId: number): boolean {
  return (
    ladder.prime?.id === dimensionId ||
    ladder.clustersIn(dimensionId).length > 0 ||
    ladder.looseGalaxies(dimensionId).length > 0
  )
}

function familyOrder(ladder: Ladder, ids: readonly number[]): number[] {
  const kept = new Set(ids)
  const parentOf = (id: number) =>
    ladder.data.dimensions.find((row) => row.id === id)?.parent_dimension_id ??
    null
  const ordered: number[] = []
  const visit = (id: number) => {
    if (ordered.includes(id)) return
    ordered.push(id)
    for (const child of ids.filter((other) => parentOf(other) === id))
      visit(child)
  }
  for (const id of ids) {
    const parent = parentOf(id)
    if (parent === null || !kept.has(parent)) visit(id)
  }
  for (const id of ids) visit(id)
  return ordered
}

function placeOrbs(
  ladder: Ladder,
  ids: readonly number[],
  around: PlacedDimension | undefined
): { orbs: Map<number, PlacedOrb>; rings: OrbRing[] } {
  const orbs = new Map<number, PlacedOrb>()
  const rings: OrbRing[] = []
  const y = (around?.y ?? 0) + ORB_LIFT
  let radius = (around?.radius ?? MIN_PLANE) * ORB_RING + ORB_SIZE
  let left = familyOrder(ladder, ids)
  while (left.length > 0) {
    const room = Math.max(
      Math.floor((Math.PI * 2 * radius) / (ORB_SIZE * ORB_SPACING)),
      1
    )
    const ring = left.slice(0, room)
    left = left.slice(room)
    rings.push({ radius, y })
    const offset = rings.length * 0.37
    ring.forEach((id, slot) => {
      const row = ladder.data.dimensions.find(
        (dimension) => dimension.id === id
      )
      const angle = offset + (slot / ring.length) * Math.PI * 2
      const size =
        ORB_SIZE * (row && SMALL_KINDS.has(row.dimension_kind) ? SMALL_ORB : 1)
      orbs.set(id, {
        id,
        position: [
          Math.cos(angle) * radius,
          y + Math.sin(angle * 3) * ORB_SIZE * ORB_WAVE,
          Math.sin(angle) * radius,
        ],
        size,
        parentId: row?.parent_dimension_id ?? null,
      })
    })
    radius += ORB_SIZE * ORB_RING_STEP
  }
  return { orbs, rings }
}

export function dimensionAnchor(
  layout: UniverseLayout,
  id: number
): Vec3 | null {
  const orb = layout.orbs.get(id)
  if (orb) return orb.position
  const plane = layout.dimensions.get(id)
  return plane ? [0, plane.y, 0] : null
}

export function universeLayout(
  ladder: Ladder,
  routes: readonly RouteRecord[]
): UniverseLayout {
  const dimensions = new Map<number, PlacedDimension>()
  const clusters = new Map<number, PlacedCluster>()
  const galaxies = new Map<number, PlacedGalaxy>()
  const everyDimension = dimensionOrder(ladder)
  const spaced = everyDimension.filter((id) => holdsSpace(ladder, id))
  const order = spaced.length > 0 ? spaced : everyDimension.slice(0, 1)
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
  const { orbs, rings } = placeOrbs(
    ladder,
    everyDimension.filter((id) => !dimensions.has(id)),
    order[0] !== undefined ? dimensions.get(order[0]) : undefined
  )
  const outer = rings.at(-1)
  if (outer) extent = Math.max(extent, outer.radius + ORB_SIZE)
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
    orbs,
    rings,
    clusters,
    galaxies,
    links: [...grouped.values()],
    extent: extent + Math.max(order.length - 1, 0) * PLANE_GAP * 0.5,
  }
}
