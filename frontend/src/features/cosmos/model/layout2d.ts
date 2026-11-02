import { type CosmosData } from '../api'
import { unitHash } from './hash'

const STAR_SPREAD = 520
const STAR_RING_RADIUS = 300
const PLANET_BASE_RADIUS = 70
const PLANET_STEP_RADIUS = 46
const ORPHAN_RING_RADIUS = 240
const MOON_BASE_RADIUS = 20
const MOON_STEP_RADIUS = 9
const MOON_PASSES = 3
const PAD_X = 110
const PAD_Y = 90
const FULL_TURN = Math.PI * 2

export type Point = { x: number; y: number }

export type OrbitRing = { key: string; cx: number; cy: number; r: number }

export type Layout2D = {
  stars: Map<number, Point>
  worlds: Map<number, Point>
  orbits: OrbitRing[]
  viewBox: { x: number; y: number; width: number; height: number }
}

function starPositions(data: CosmosData): Map<number, Point> {
  const positions = new Map<number, Point>()
  const stars = data.stars
  if (stars.length === 1) {
    positions.set(stars[0].id, { x: 0, y: 0 })
    return positions
  }
  const xs = stars.map((star) => star.x)
  const ys = stars.map((star) => star.y)
  const minX = Math.min(...xs)
  const minY = Math.min(...ys)
  const span = Math.max(Math.max(...xs) - minX, Math.max(...ys) - minY)
  const scale = STAR_SPREAD * Math.sqrt(stars.length / 2)
  stars.forEach((star, index) => {
    if (span > 0) {
      positions.set(star.id, {
        x: ((star.x - minX) / span) * scale,
        y: ((star.y - minY) / span) * scale,
      })
    } else {
      const angle = (index / stars.length) * FULL_TURN
      positions.set(star.id, {
        x: Math.cos(angle) * STAR_RING_RADIUS,
        y: Math.sin(angle) * STAR_RING_RADIUS,
      })
    }
  })
  return positions
}

function around(center: Point, radius: number, angle: number): Point {
  return {
    x: center.x + Math.cos(angle) * radius,
    y: center.y + Math.sin(angle) * radius,
  }
}

export function layoutCosmos2D(data: CosmosData): Layout2D {
  const stars = starPositions(data)
  const worlds = new Map<number, Point>()
  const orbits: OrbitRing[] = []
  const topLevel = data.worlds.filter(
    (item) => item.world.parent_world_id === null
  )
  for (const star of data.stars) {
    const center = stars.get(star.id)
    if (!center) continue
    const planets = topLevel
      .filter((item) => item.world.star_id === star.id)
      .sort((a, b) => a.world.orbit - b.world.orbit || a.world.id - b.world.id)
    planets.forEach((item, order) => {
      const radius = PLANET_BASE_RADIUS + PLANET_STEP_RADIUS * order
      worlds.set(
        item.world.id,
        around(center, radius, unitHash(`d${item.world.id}`) * FULL_TURN)
      )
      orbits.push({
        key: `p${item.world.id}`,
        cx: center.x,
        cy: center.y,
        r: radius,
      })
    })
  }
  const orphans = topLevel.filter((item) => !worlds.has(item.world.id))
  orphans.forEach((item, index) => {
    const angle = (index / Math.max(orphans.length, 1)) * FULL_TURN
    worlds.set(item.world.id, around({ x: 0, y: 0 }, ORPHAN_RING_RADIUS, angle))
  })
  for (let pass = 0; pass < MOON_PASSES; pass += 1) {
    const placedPerParent = new Map<number, number>()
    for (const item of data.worlds) {
      const parentId = item.world.parent_world_id
      if (parentId === null || worlds.has(item.world.id)) continue
      const parent = worlds.get(parentId)
      if (!parent) continue
      const siblings =
        placedPerParent.get(parentId) ??
        data.worlds.filter(
          (other) =>
            other.world.parent_world_id === parentId &&
            worlds.has(other.world.id)
        ).length
      const radius = MOON_BASE_RADIUS + MOON_STEP_RADIUS * siblings
      worlds.set(
        item.world.id,
        around(parent, radius, unitHash(`a${item.world.id}`) * FULL_TURN)
      )
      orbits.push({
        key: `m${item.world.id}`,
        cx: parent.x,
        cy: parent.y,
        r: radius,
      })
      placedPerParent.set(parentId, siblings + 1)
    }
  }
  for (const item of data.worlds) {
    if (!worlds.has(item.world.id))
      worlds.set(item.world.id, around({ x: 0, y: 0 }, ORPHAN_RING_RADIUS, 0))
  }
  const points = [...stars.values(), ...worlds.values()]
  const xs = points.map((point) => point.x)
  const ys = points.map((point) => point.y)
  const minX = points.length ? Math.min(...xs) : 0
  const maxX = points.length ? Math.max(...xs) : 0
  const minY = points.length ? Math.min(...ys) : 0
  const maxY = points.length ? Math.max(...ys) : 0
  return {
    stars,
    worlds,
    orbits,
    viewBox: {
      x: minX - PAD_X,
      y: minY - PAD_Y,
      width: maxX - minX + PAD_X * 2,
      height: maxY - minY + PAD_Y * 2,
    },
  }
}

export function curvedPath(from: Point, to: Point, curve: number): string {
  const midX = (from.x + to.x) / 2
  const midY = (from.y + to.y) / 2
  const dx = to.x - from.x
  const dy = to.y - from.y
  const controlX = midX - dy * curve
  const controlY = midY + dx * curve
  return `M ${from.x} ${from.y} Q ${controlX} ${controlY} ${to.x} ${to.y}`
}
