import { type Cell, cellKey, hexDistance, hexRing, hexToWorld } from './hex'

export type WallModel =
  | 'straight'
  | 'gate'
  | 'corner_wide'
  | 'corner_sharp'
  | 'tower'
  | 'fence'
  | 'fence_gate'

export type WallPiece = {
  key: string
  cell: Cell
  model: WallModel
  turn: number
}

export type RoadSegment = {
  key: string
  cell: Cell
  from: readonly [number, number]
  to: readonly [number, number]
}

const STONE_FROM = 3
const TOWERS_FROM = 4
const FULL_TURN = 360
const HALF_TURN = 180
const WIDE = 120
const SHARP = 60
const SIDES = 6
const MAX_GATES = 6

function angleOf(from: Cell, to: Cell): number {
  const [fx, fz] = hexToWorld(from[0], from[1])
  const [tx, tz] = hexToWorld(to[0], to[1])
  return (Math.atan2(tz - fz, tx - fx) * HALF_TURN) / Math.PI
}

function wrap(degrees: number): number {
  return (
    (((degrees % FULL_TURN) + FULL_TURN + HALF_TURN) % FULL_TURN) - HALF_TURN
  )
}

function same(first: number, second: number): boolean {
  return Math.abs(wrap(first - second)) < 1
}

function radians(degrees: number): number {
  return (degrees * Math.PI) / HALF_TURN
}

function cornerTurn(back: number, ahead: number, second: number): number {
  const first = HALF_TURN - back
  if (same(second - first, ahead)) return radians(first)
  return radians(HALF_TURN - ahead)
}

export function gateCount(roads: number): number {
  return Math.max(1, Math.min(MAX_GATES, roads + 1))
}

export function gateIndices(radius: number, gates: number): Set<number> {
  const sides = Array.from(
    { length: gates },
    (_, index) => Math.floor((index * SIDES) / gates) % SIDES
  )
  return new Set(
    sides.map((side) => side * radius + Math.max(0, Math.floor(radius / 2)))
  )
}

export function wallPieces(
  radius: number,
  level: number,
  roads: number
): WallPiece[] {
  if (radius < 1 || level < 1) return []
  const ring = hexRing(radius)
  const gates = gateIndices(radius, gateCount(roads))
  if (level < STONE_FROM)
    return ring.flatMap((cell, index) =>
      hexRing(1)
        .map((step) => [cell[0] + step[0], cell[1] + step[1]] as Cell)
        .filter((near) => hexDistance(near, [0, 0]) === radius - 1)
        .map((near, edge) => ({
          key: `fence-${cellKey(cell)}-${edge}`,
          cell,
          model: gates.has(index) && edge === 0 ? 'fence_gate' : 'fence',
          turn: radians(HALF_TURN - angleOf(cell, near)),
        }))
    )
  return ring.map((cell, index) => {
    const back = angleOf(cell, ring[(index + ring.length - 1) % ring.length])
    const ahead = angleOf(cell, ring[(index + 1) % ring.length])
    const bend = Math.abs(wrap(back - ahead))
    const key = `wall-${cellKey(cell)}`
    if (bend > HALF_TURN - 1)
      return {
        key,
        cell,
        model: gates.has(index) ? 'gate' : 'straight',
        turn: radians(-ahead),
      }
    if (level >= TOWERS_FROM) return { key, cell, model: 'tower', turn: 0 }
    if (Math.abs(bend - WIDE) < 1)
      return {
        key,
        cell,
        model: 'corner_wide',
        turn: cornerTurn(back, ahead, -SHARP),
      }
    return {
      key,
      cell,
      model: 'corner_sharp',
      turn: cornerTurn(back, ahead, -WIDE),
    }
  })
}

function outward(cell: Cell, center: Cell): Cell {
  const [cx, cz] = hexToWorld(center[0], center[1])
  const [x, z] = hexToWorld(cell[0], cell[1])
  const heading = Math.atan2(z - cz, x - cx)
  return hexRing(1)
    .map((step) => [cell[0] + step[0], cell[1] + step[1]] as Cell)
    .filter((near) => hexDistance(near, center) > hexDistance(cell, center))
    .sort((first, second) => {
      const [ax, az] = hexToWorld(first[0], first[1])
      const [bx, bz] = hexToWorld(second[0], second[1])
      const turnA = Math.abs(
        wrap(((Math.atan2(az - z, ax - x) - heading) * HALF_TURN) / Math.PI)
      )
      const turnB = Math.abs(
        wrap(((Math.atan2(bz - z, bx - x) - heading) * HALF_TURN) / Math.PI)
      )
      return turnA - turnB
    })[0]
}

export function roadSegments(
  radius: number,
  roads: number,
  length: number
): RoadSegment[] {
  if (radius < 1 || roads < 1) return []
  const ring = hexRing(radius)
  return [...gateIndices(radius, gateCount(roads))].flatMap((index) => {
    const path: Cell[] = [ring[index]]
    for (let step = 0; step < length; step += 1)
      path.push(outward(path[path.length - 1], [0, 0]))
    return path.slice(1).map((cell, step) => ({
      key: `road-${index}-${step}`,
      cell,
      from: hexToWorld(path[step][0], path[step][1]),
      to: hexToWorld(cell[0], cell[1]),
    }))
  })
}
