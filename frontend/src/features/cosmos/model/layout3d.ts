import { type CosmosData, type CosmosWorld } from '../api'
import { signedHash, unitHash } from './hash'
import { STAR_LOOK } from './looks'

const ORB_MAX = 58
const ORB_MIN = 24
const ORB_SPACING = 0.94
const ORB_GAP = 0.7
const STAR_HEIGHT_JITTER = 25
const STAR_RADIUS_FACTOR = 0.15
const BODY_BASE = 0.075
const BODY_POPULATION = 0.05
const BODY_POPULATION_LOG = 5.5
const BODY_REGION = 0.006
const BODY_REGION_CAP = 8
const GAS_SCALE = 1.75
const MOON_SCALE = 0.55
const PLANET_PERIOD = 220
const PLANET_PERIOD_POWER = 1.5
const MOON_PERIOD_BASE = 40
const MOON_PERIOD_STEP = 90
const MOON_GAS_SPACING = 2.55
const MOON_SPACING = 1.75
const MOON_BODY_GAP = 1.2
const MOON_ORBIT_SHARE = 0.75
const PLANET_TILT = 0.045
const MOON_TILT = 0.35
const AXIAL_TILT = 0.35
const SPIN_MIN = 0.04
const SPIN_RANGE = 0.08
const RETROGRADE_SHARE = 0.15
const FREE_RING_ORBITS = 6
const STAR_EXTENT_RADII = 5
const WORLD_EXTENT_RADII = 3
const FULL_TURN = Math.PI * 2
const MIN_ORBIT = 0.4

export type Vec3 = [number, number, number]

export type StarBody = {
  id: number
  position: Vec3
  radius: number
  extent: number
}

export type WorldBody = {
  id: number
  kind: 'planet' | 'moon' | 'free'
  starId: number | null
  parentId: number | null
  radius: number
  orbitRadius: number
  speed: number
  phase: number
  inclination: number
  node: number
  tilt: number
  spinRate: number
  anchor: Vec3
}

export type Layout3D = {
  orb: number
  stars: Map<number, StarBody>
  worlds: Map<number, WorldBody>
  order: number[]
  center: Vec3
  extent: number
  signature: string
}

function outermostOrbit(data: CosmosData, starId: number): number {
  let outer = 0
  for (const item of data.worlds) {
    if (item.world.star_id === starId && item.world.parent_world_id === null)
      outer = Math.max(outer, item.world.orbit)
  }
  return outer
}

export function orbitUnit(data: CosmosData): number {
  let orb = ORB_MAX
  const outer = new Map(
    data.stars.map((star) => [star.id, outermostOrbit(data, star.id)])
  )
  for (let i = 0; i < data.stars.length; i += 1) {
    for (let j = i + 1; j < data.stars.length; j += 1) {
      const a = data.stars[i]
      const b = data.stars[j]
      const distance = Math.hypot(a.x - b.x, a.y - b.y)
      const room = (outer.get(a.id) ?? 0) + (outer.get(b.id) ?? 0) + ORB_GAP
      orb = Math.min(orb, (ORB_SPACING * distance) / room)
    }
  }
  return Math.max(ORB_MIN, Math.min(ORB_MAX, orb))
}

export function bodyRadius(item: CosmosWorld, orb: number): number {
  const population = Math.min(
    Math.log10(item.counts.population + 1) / BODY_POPULATION_LOG,
    1
  )
  const regions = Math.min(item.counts.regions, BODY_REGION_CAP)
  let radius =
    orb * (BODY_BASE + BODY_POPULATION * population + BODY_REGION * regions)
  if (item.world.world_type === 'gas') radius *= GAS_SCALE
  if (item.world.parent_world_id !== null) radius *= MOON_SCALE
  return radius
}

function depthOf(data: CosmosData, item: CosmosWorld): number {
  let depth = 0
  let parent = item.world.parent_world_id
  const byId = new Map(data.worlds.map((other) => [other.world.id, other]))
  while (parent !== null && depth < data.worlds.length) {
    depth += 1
    parent = byId.get(parent)?.world.parent_world_id ?? null
  }
  return depth
}

export function layoutCosmos3D(data: CosmosData): Layout3D {
  const orb = orbitUnit(data)
  const stars = new Map<number, StarBody>()
  for (const star of data.stars) {
    const radius = orb * STAR_RADIUS_FACTOR * STAR_LOOK[star.star_type].size
    const outer = outermostOrbit(data, star.id) * orb
    stars.set(star.id, {
      id: star.id,
      position: [
        star.x,
        signedHash(`sy${star.id}`) * STAR_HEIGHT_JITTER,
        star.y,
      ],
      radius,
      extent: Math.max(
        outer + radius * WORLD_EXTENT_RADII,
        radius * STAR_EXTENT_RADII
      ),
    })
  }
  const worlds = new Map<number, WorldBody>()
  const order = [...data.worlds]
    .sort(
      (a, b) => depthOf(data, a) - depthOf(data, b) || a.world.id - b.world.id
    )
    .map((item) => item.world.id)
  const byId = new Map(data.worlds.map((item) => [item.world.id, item]))
  const starCenter = centerOf([...stars.values()].map((star) => star.position))
  const freeWorlds = data.worlds.filter(
    (item) =>
      item.world.parent_world_id === null &&
      (item.world.star_id === null || !stars.has(item.world.star_id))
  )
  for (const id of order) {
    const item = byId.get(id)
    if (!item) continue
    const world = item.world
    const radius = bodyRadius(item, orb)
    const orbit = Math.max(world.orbit, MIN_ORBIT)
    const tilt = signedHash(`t${id}`) * AXIAL_TILT
    const retro = unitHash(`r${id}`) < RETROGRADE_SHARE ? -1 : 1
    const spinRate = retro * (SPIN_MIN + unitHash(`s${id}`) * SPIN_RANGE)
    const phase = unitHash(`p${id}`) * FULL_TURN
    const node = unitHash(`n${id}`) * FULL_TURN
    const parent =
      world.parent_world_id === null
        ? undefined
        : worlds.get(world.parent_world_id)
    if (parent) {
      const parentGas = byId.get(parent.id)?.world.world_type === 'gas'
      worlds.set(id, {
        id,
        kind: 'moon',
        starId: parent.starId,
        parentId: parent.id,
        radius,
        orbitRadius:
          parent.radius * (parentGas ? MOON_GAS_SPACING : MOON_SPACING) +
          radius * MOON_BODY_GAP +
          orbit * orb * MOON_ORBIT_SHARE,
        speed: FULL_TURN / (MOON_PERIOD_BASE + MOON_PERIOD_STEP * orbit),
        phase,
        inclination: signedHash(`i${id}`) * MOON_TILT,
        node,
        tilt,
        spinRate,
        anchor: [0, 0, 0],
      })
      continue
    }
    const host = world.star_id === null ? undefined : stars.get(world.star_id)
    if (host) {
      worlds.set(id, {
        id,
        kind: 'planet',
        starId: host.id,
        parentId: null,
        radius,
        orbitRadius: orbit * orb,
        speed: FULL_TURN / (PLANET_PERIOD * orbit ** PLANET_PERIOD_POWER),
        phase,
        inclination: signedHash(`i${id}`) * PLANET_TILT,
        node,
        tilt,
        spinRate,
        anchor: host.position,
      })
      continue
    }
    const index = freeWorlds.findIndex((other) => other.world.id === id)
    const angle =
      (Math.max(index, 0) / Math.max(freeWorlds.length, 1)) * FULL_TURN +
      phase * 0.1
    const ring = orb * FREE_RING_ORBITS
    worlds.set(id, {
      id,
      kind: 'free',
      starId: null,
      parentId: null,
      radius,
      orbitRadius: 0,
      speed: 0,
      phase,
      inclination: 0,
      node,
      tilt,
      spinRate,
      anchor: [
        starCenter[0] + Math.cos(angle) * ring,
        0,
        starCenter[2] + Math.sin(angle) * ring,
      ],
    })
  }
  const points: { position: Vec3; reach: number }[] = [
    ...[...stars.values()].map((star) => ({
      position: star.position,
      reach: star.extent,
    })),
    ...[...worlds.values()]
      .filter((body) => body.kind === 'free')
      .map((body) => ({
        position: body.anchor,
        reach: body.radius * WORLD_EXTENT_RADII,
      })),
  ]
  const center = centerOf(points.map((point) => point.position))
  const extent = points.reduce(
    (best, point) =>
      Math.max(
        best,
        Math.hypot(
          point.position[0] - center[0],
          point.position[1] - center[1],
          point.position[2] - center[2]
        ) + point.reach
      ),
    orb
  )
  return {
    orb,
    stars,
    worlds,
    order,
    center,
    extent,
    signature: `${Math.round(extent / 50)}:${center.map((value) => Math.round(value / 50)).join(',')}`,
  }
}

function centerOf(points: Vec3[]): Vec3 {
  if (points.length === 0) return [0, 0, 0]
  const sum = points.reduce<Vec3>(
    (total, point) => [
      total[0] + point[0],
      total[1] + point[1],
      total[2] + point[2],
    ],
    [0, 0, 0]
  )
  return [
    sum[0] / points.length,
    sum[1] / points.length,
    sum[2] / points.length,
  ]
}

export function orbitOffset(body: WorldBody, time: number, out: Vec3): Vec3 {
  const angle = body.phase + body.speed * time
  const x = Math.cos(angle) * body.orbitRadius
  const z = Math.sin(angle) * body.orbitRadius
  const height = -z * Math.sin(body.inclination)
  const depth = z * Math.cos(body.inclination)
  const cosNode = Math.cos(body.node)
  const sinNode = Math.sin(body.node)
  out[0] = x * cosNode + depth * sinNode
  out[1] = height
  out[2] = -x * sinNode + depth * cosNode
  return out
}

export function worldPositions(
  layout: Layout3D,
  time: number
): Map<number, Vec3> {
  const positions = new Map<number, Vec3>()
  const offset: Vec3 = [0, 0, 0]
  for (const id of layout.order) {
    const body = layout.worlds.get(id)
    if (!body) continue
    const anchor =
      body.kind === 'moon'
        ? (positions.get(body.parentId ?? 0) ?? body.anchor)
        : body.anchor
    if (body.kind === 'free') {
      positions.set(id, [anchor[0], anchor[1], anchor[2]])
      continue
    }
    orbitOffset(body, time, offset)
    positions.set(id, [
      anchor[0] + offset[0],
      anchor[1] + offset[1],
      anchor[2] + offset[2],
    ])
  }
  return positions
}
