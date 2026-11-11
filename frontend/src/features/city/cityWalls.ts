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

export type RoadModel = 'straight' | 'bend' | 'sharp' | 'end'

export type RoadTile = {
  key: string
  cell: Cell
  model: RoadModel
  turn: number
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

function inward(cell: Cell): Cell {
  const [x, z] = hexToWorld(cell[0], cell[1])
  const heading = Math.atan2(-z, -x)
  return hexRing(1)
    .map((step) => [cell[0] + step[0], cell[1] + step[1]] as Cell)
    .filter((near) => hexDistance(near, [0, 0]) < hexDistance(cell, [0, 0]))
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

function roadTile(
  key: string,
  cell: Cell,
  back: Cell,
  ahead: Cell | null
): RoadTile {
  const behind = angleOf(cell, back)
  if (ahead === null)
    return { key, cell, model: 'end', turn: radians(HALF_TURN - behind) }
  const forth = angleOf(cell, ahead)
  const bend = Math.abs(wrap(behind - forth))
  if (bend > HALF_TURN - 1)
    return { key, cell, model: 'straight', turn: radians(-forth) }
  if (Math.abs(bend - WIDE) < 1)
    return { key, cell, model: 'bend', turn: cornerTurn(behind, forth, -SHARP) }
  return { key, cell, model: 'sharp', turn: cornerTurn(behind, forth, -WIDE) }
}

export type RoadDress = {
  key: string
  kind: 'stone' | 'lantern' | 'cart'
  x: number
  z: number
  turn: number
}

const STONES_PER_STEP = 3
const LANTERN_EVERY = 2
const CART_EVERY = 3
const SIDE = 0.62
const COBBLED_FROM = 2
const LIT_FROM = 3

export function roadPaths(
  radius: number,
  roads: number,
  length: number,
  blocked: (cell: Cell) => boolean = () => false
): Cell[][] {
  if (radius < 1 || roads < 1) return []
  const ring = hexRing(radius)
  return [...gateIndices(radius, gateCount(roads))].map((index) => {
    const inner: Cell[] = []
    let cell = ring[index]
    while (hexDistance(cell, [0, 0]) > 0) {
      const next = inward(cell)
      if (blocked(next)) break
      inner.push(next)
      cell = next
    }
    const path: Cell[] = [...inner.reverse(), ring[index]]
    for (let step = 0; step < length; step += 1)
      path.push(outward(path[path.length - 1], [0, 0]))
    return path
  })
}

export function roadTiles(
  radius: number,
  roads: number,
  length: number,
  blocked: (cell: Cell) => boolean = () => false
): RoadTile[] {
  return roadPaths(radius, roads, length, blocked).flatMap((path, road) =>
    path.map((cell, step) => {
      const key = `road-${road}-${step}`
      if (step === 0)
        return path.length > 1
          ? roadTile(key, cell, path[1], null)
          : { key, cell, model: 'end' as const, turn: 0 }
      return roadTile(key, cell, path[step - 1], path[step + 1] ?? null)
    })
  )
}

export function roadDress(
  paths: Cell[][],
  roads: number,
  radius: number
): RoadDress[] {
  return paths.flatMap((path, road) =>
    path.slice(0, -1).flatMap((cell, step) => {
      const [fx, fz] = hexToWorld(cell[0], cell[1])
      const [tx, tz] = hexToWorld(path[step + 1][0], path[step + 1][1])
      const along = Math.atan2(tz - fz, tx - fx)
      const [nx, nz] = [-Math.sin(along), Math.cos(along)]
      const found: RoadDress[] = []
      if (roads >= COBBLED_FROM)
        for (let part = 0; part < STONES_PER_STEP; part += 1) {
          const t = part / STONES_PER_STEP
          found.push({
            key: `stone-${road}-${step}-${part}`,
            kind: 'stone',
            x: fx + (tx - fx) * t,
            z: fz + (tz - fz) * t,
            turn: -along + (part % 2) * (Math.PI / 2),
          })
        }
      const side = step % 2 === 0 ? 1 : -1
      if (roads >= LIT_FROM && step % LANTERN_EVERY === 0)
        found.push({
          key: `lantern-${road}-${step}`,
          kind: 'lantern',
          x: (fx + tx) / 2 + nx * SIDE * side,
          z: (fz + tz) / 2 + nz * SIDE * side,
          turn: -along,
        })
      if (step % CART_EVERY === 1 && hexDistance(cell, [0, 0]) > radius)
        found.push({
          key: `cart-${road}-${step}`,
          kind: 'cart',
          x: (fx + tx) / 2 - nx * SIDE * side,
          z: (fz + tz) / 2 - nz * SIDE * side,
          turn: -along,
        })
      return found
    })
  )
}
