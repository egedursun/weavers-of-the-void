import { type WorldMap } from './api'

export type CellEdges = {
  first: Int32Array
  second: Int32Array
  coordinates: Float64Array
}

export type CellKey = (cell: number) => string | null

export type DomainAnchor = {
  key: string
  x: number
  y: number
  cells: number
}

const NO_CELL = -1
const UNKNOWN = 0

const edgeCache = new WeakMap<WorldMap, CellEdges>()
const outlineCache = new WeakMap<WorldMap, Map<number, Path2D>>()

function pointKey(x: number, y: number): string {
  return `${x},${y}`
}

export function cellEdges(map: WorldMap): CellEdges {
  const cached = edgeCache.get(map)
  if (cached) return cached
  const offsets = map.cells.polygon_offsets
  const coordinates = map.cells.polygon_coordinates
  const owner = new Map<string, number>()
  const first: number[] = []
  const second: number[] = []
  const segments: number[] = []
  for (let cell = 0; cell + 1 < offsets.length; cell += 1) {
    const start = offsets[cell]
    const count = (offsets[cell + 1] - start) / 2
    for (let vertex = 0; vertex < count; vertex += 1) {
      const next = (vertex + 1) % count
      const ax = coordinates[start + vertex * 2]
      const ay = coordinates[start + vertex * 2 + 1]
      const bx = coordinates[start + next * 2]
      const by = coordinates[start + next * 2 + 1]
      const forward = ax < bx || (ax === bx && ay < by)
      const key = forward
        ? `${pointKey(ax, ay)}|${pointKey(bx, by)}`
        : `${pointKey(bx, by)}|${pointKey(ax, ay)}`
      const known = owner.get(key)
      if (known !== undefined) {
        second[known] = cell
        continue
      }
      owner.set(key, first.length)
      first.push(cell)
      second.push(NO_CELL)
      segments.push(ax, ay, bx, by)
    }
  }
  const edges = {
    first: Int32Array.from(first),
    second: Int32Array.from(second),
    coordinates: Float64Array.from(segments),
  }
  edgeCache.set(map, edges)
  return edges
}

function isKnownLand(map: WorldMap, cell: number): boolean {
  if (cell === NO_CELL) return false
  return !map.cells.water[cell] && map.cells.known[cell] !== UNKNOWN
}

export type DomainEdges = { border: Path2D; band: Set<number> }

export function domainEdges(map: WorldMap, keyOf: CellKey): DomainEdges {
  const edges = cellEdges(map)
  const border = new Path2D()
  const band = new Set<number>()
  const coordinates = edges.coordinates
  for (let edge = 0; edge < edges.first.length; edge += 1) {
    const first = edges.first[edge]
    const second = edges.second[edge]
    if (!isKnownLand(map, first) || !isKnownLand(map, second)) continue
    const firstKey = keyOf(first)
    const secondKey = keyOf(second)
    if (firstKey === secondKey) continue
    const offset = edge * 4
    border.moveTo(coordinates[offset], coordinates[offset + 1])
    border.lineTo(coordinates[offset + 2], coordinates[offset + 3])
    if (firstKey !== null) band.add(first)
    if (secondKey !== null) band.add(second)
  }
  return { border, band }
}

function inRegion(map: WorldMap, cell: number, regionId: number): boolean {
  if (cell === NO_CELL) return false
  return (
    map.cells.region[cell] === regionId ||
    map.cells.top_region[cell] === regionId
  )
}

export function regionOutline(map: WorldMap, regionId: number): Path2D {
  let byRegion = outlineCache.get(map)
  if (!byRegion) {
    byRegion = new Map()
    outlineCache.set(map, byRegion)
  }
  const cached = byRegion.get(regionId)
  if (cached) return cached
  const edges = cellEdges(map)
  const path = new Path2D()
  const coordinates = edges.coordinates
  for (let edge = 0; edge < edges.first.length; edge += 1) {
    const inside = inRegion(map, edges.first[edge], regionId)
    if (inside === inRegion(map, edges.second[edge], regionId)) continue
    const offset = edge * 4
    path.moveTo(coordinates[offset], coordinates[offset + 1])
    path.lineTo(coordinates[offset + 2], coordinates[offset + 3])
  }
  byRegion.set(regionId, path)
  return path
}

export function domainAnchors(map: WorldMap, keyOf: CellKey): DomainAnchor[] {
  const cells = map.cells
  const sums = new Map<string, { x: number; y: number; count: number }>()
  for (let cell = 0; cell < cells.x.length; cell += 1) {
    if (cells.water[cell] || cells.known[cell] === UNKNOWN) continue
    const key = keyOf(cell)
    if (key === null) continue
    const sum = sums.get(key) ?? { x: 0, y: 0, count: 0 }
    sum.x += cells.x[cell]
    sum.y += cells.y[cell]
    sum.count += 1
    sums.set(key, sum)
  }
  const anchors: DomainAnchor[] = []
  for (const [key, sum] of sums) {
    const centreX = sum.x / sum.count
    const centreY = sum.y / sum.count
    let best = { x: centreX, y: centreY }
    let bestDistance = Number.POSITIVE_INFINITY
    for (let cell = 0; cell < cells.x.length; cell += 1) {
      if (cells.water[cell] || keyOf(cell) !== key) continue
      const distance =
        (cells.x[cell] - centreX) ** 2 + (cells.y[cell] - centreY) ** 2
      if (distance < bestDistance) {
        bestDistance = distance
        best = { x: cells.x[cell], y: cells.y[cell] }
      }
    }
    anchors.push({ key, x: best.x, y: best.y, cells: sum.count })
  }
  return anchors.sort((left, right) => right.cells - left.cells)
}
