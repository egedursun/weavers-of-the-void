export type Box = {
  left: number
  top: number
  right: number
  bottom: number
}

export type LabelCandidate = {
  id: string
  x: number
  y: number
  width: number
  height: number
  priority: number
  always?: boolean
  shifts?: readonly number[]
}

export type PlacedLabel = {
  id: string
  x: number
  y: number
  box: Box
}

const CELL_SIZE = 48
const DEFAULT_SHIFTS: readonly number[] = [0]

export function boxAt(
  x: number,
  y: number,
  width: number,
  height: number,
  padding = 0
): Box {
  return {
    left: x - width / 2 - padding,
    top: y - height / 2 - padding,
    right: x + width / 2 + padding,
    bottom: y + height / 2 + padding,
  }
}

export function overlaps(a: Box, b: Box): boolean {
  return (
    a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom
  )
}

export class BoxGrid {
  private readonly cells = new Map<string, Box[]>()

  private keys(box: Box): string[] {
    const keys: string[] = []
    const startX = Math.floor(box.left / CELL_SIZE)
    const endX = Math.floor(box.right / CELL_SIZE)
    const startY = Math.floor(box.top / CELL_SIZE)
    const endY = Math.floor(box.bottom / CELL_SIZE)
    for (let column = startX; column <= endX; column += 1)
      for (let row = startY; row <= endY; row += 1)
        keys.push(`${column}:${row}`)
    return keys
  }

  collides(box: Box): boolean {
    return this.keys(box).some((key) =>
      (this.cells.get(key) ?? []).some((other) => overlaps(box, other))
    )
  }

  add(box: Box): void {
    for (const key of this.keys(box)) {
      const list = this.cells.get(key)
      if (list) list.push(box)
      else this.cells.set(key, [box])
    }
  }
}

function insideBounds(box: Box, bounds: Box | undefined): boolean {
  if (!bounds) return true
  return (
    box.left >= bounds.left &&
    box.top >= bounds.top &&
    box.right <= bounds.right &&
    box.bottom <= bounds.bottom
  )
}

export function placeLabels(
  candidates: readonly LabelCandidate[],
  options: { bounds?: Box; obstacles?: readonly Box[]; padding?: number } = {}
): PlacedLabel[] {
  const grid = new BoxGrid()
  for (const obstacle of options.obstacles ?? []) grid.add(obstacle)
  const padding = options.padding ?? 2
  const ordered = [...candidates].sort(
    (left, right) =>
      Number(Boolean(right.always)) - Number(Boolean(left.always)) ||
      right.priority - left.priority
  )
  const placed: PlacedLabel[] = []
  for (const candidate of ordered) {
    const shifts = candidate.shifts ?? DEFAULT_SHIFTS
    const boxFor = (shift: number) =>
      boxAt(
        candidate.x,
        candidate.y + shift,
        candidate.width,
        candidate.height,
        padding
      )
    const shift = shifts.find((option) => {
      const box = boxFor(option)
      return insideBounds(box, options.bounds) && !grid.collides(box)
    })
    const chosen = shift ?? (candidate.always ? 0 : undefined)
    if (chosen === undefined) continue
    const box = boxFor(chosen)
    grid.add(box)
    placed.push({
      id: candidate.id,
      x: candidate.x,
      y: candidate.y + chosen,
      box,
    })
  }
  return placed
}

export function verticalShifts(height: number, tries: number): number[] {
  const shifts = [0]
  for (let step = 1; step <= tries; step += 1) {
    shifts.push(-step * height * 0.9, step * height * 0.9)
  }
  return shifts
}

const ELLIPSIS = '…'

export function fitText(
  context: CanvasRenderingContext2D,
  text: string,
  maxWidth: number
): string {
  if (context.measureText(text).width <= maxWidth) return text
  let low = 0
  let high = text.length
  while (low < high) {
    const middle = Math.ceil((low + high) / 2)
    const candidate = `${text.slice(0, middle).trimEnd()}${ELLIPSIS}`
    if (context.measureText(candidate).width <= maxWidth) low = middle
    else high = middle - 1
  }
  return `${text.slice(0, low).trimEnd()}${ELLIPSIS}`
}
