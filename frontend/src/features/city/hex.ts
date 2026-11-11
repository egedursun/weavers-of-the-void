export const HEX_STEP_X = 2
export const HEX_STEP_Z = Math.sqrt(3)

export type Cell = readonly [number, number]

export function hexToWorld(q: number, r: number): [number, number] {
  return [HEX_STEP_X * (q + r / 2), HEX_STEP_Z * r]
}

export function hexDistance(first: Cell, second: Cell): number {
  const dq = first[0] - second[0]
  const dr = first[1] - second[1]
  return (Math.abs(dq) + Math.abs(dr) + Math.abs(dq + dr)) / 2
}

const DIRECTIONS: readonly Cell[] = [
  [1, 0],
  [1, -1],
  [0, -1],
  [-1, 0],
  [-1, 1],
  [0, 1],
]

export function hexRing(radius: number): Cell[] {
  if (radius === 0) return [[0, 0]]
  const found: Cell[] = []
  let q = DIRECTIONS[4][0] * radius
  let r = DIRECTIONS[4][1] * radius
  for (let side = 0; side < 6; side += 1)
    for (let step = 0; step < radius; step += 1) {
      found.push([q, r])
      q += DIRECTIONS[side][0]
      r += DIRECTIONS[side][1]
    }
  return found
}

export function waterDirection(side: number): Cell {
  return DIRECTIONS[side % DIRECTIONS.length]
}

const SLOT_RADIUS = 0.62

export function slotOffset(slot: number): [number, number] {
  if (slot <= 0) return [0, 0]
  const angle = ((slot - 1) / 6) * Math.PI * 2 + Math.PI / 6
  return [Math.cos(angle) * SLOT_RADIUS, Math.sin(angle) * SLOT_RADIUS]
}

export function cellKey(cell: Cell): string {
  return `${cell[0]},${cell[1]}`
}
