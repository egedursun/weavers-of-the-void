export type ChartPoint = { x: number; y: number }

export type ChartSeries = {
  key: string
  label: string
  color: string
  points: ChartPoint[]
}

export type ChartFrame = {
  width: number
  height: number
  left: number
  right: number
  top: number
  bottom: number
}

export const CHART_MARGIN = {
  left: 44,
  top: 12,
  bottom: 22,
  single: 14,
  labelled: 78,
}
export const CHART_HEIGHT = { compact: 140, wide: 170, wideFrom: 400 }
export const MAX_X_LABELS = 8
export const LABEL_GAP = 44
export const DIRECT_LABEL_MIN = 2
export const DIRECT_LABEL_MAX = 4
export const DIRECT_LABEL_CHARS = 11
export const DIRECT_LABEL_SPACING = 12
const DECIMAL_BASE = 10

export function niceCeiling(value: number): number {
  if (!Number.isFinite(value) || value <= 0) return 1
  const power = DECIMAL_BASE ** Math.floor(Math.log10(value))
  return Math.ceil(value / power) * power
}

export function chartFrame(
  width: number,
  seriesCount: number,
  height?: number
): ChartFrame {
  const labelled =
    seriesCount >= DIRECT_LABEL_MIN && seriesCount <= DIRECT_LABEL_MAX
  return {
    width,
    height:
      height ??
      (width > CHART_HEIGHT.wideFrom
        ? CHART_HEIGHT.wide
        : CHART_HEIGHT.compact),
    left: CHART_MARGIN.left,
    right: labelled ? CHART_MARGIN.labelled : CHART_MARGIN.single,
    top: CHART_MARGIN.top,
    bottom: CHART_MARGIN.bottom,
  }
}

export function xDomain(series: ChartSeries[]): number[] {
  const values = new Set<number>()
  for (const item of series)
    for (const point of item.points) values.add(point.x)
  return [...values].sort((left, right) => left - right)
}

export function yCeiling(series: ChartSeries[], fixed?: number): number {
  if (fixed !== undefined) return fixed
  const highest = Math.max(
    0,
    ...series.flatMap((item) => item.points.map((point) => point.y))
  )
  return niceCeiling(highest)
}

export function xScale(frame: ChartFrame, xs: number[]): (x: number) => number {
  const inner = Math.max(1, frame.width - frame.left - frame.right)
  if (xs.length < 2) return () => frame.left + inner / 2
  const first = xs[0]
  const span = xs[xs.length - 1] - first || 1
  return (x) => frame.left + ((x - first) / span) * inner
}

export function yScale(
  frame: ChartFrame,
  ceiling: number
): (y: number) => number {
  const inner = Math.max(1, frame.height - frame.top - frame.bottom)
  return (y) =>
    frame.top + inner - (Math.min(Math.max(y, 0), ceiling) / ceiling) * inner
}

export function xLabelIndices(
  xs: number[],
  position: (x: number) => number
): number[] {
  if (xs.length === 0) return []
  const last = xs.length - 1
  const span = Math.abs(position(xs[last]) - position(xs[0]))
  const fit = Math.max(2, Math.floor(span / LABEL_GAP) + 1)
  const step = Math.ceil(xs.length / Math.min(MAX_X_LABELS, fit))
  const picked = xs
    .map((_, index) => index)
    .filter((index) => index % step === 0 || index === last)
  return picked.filter(
    (index) =>
      index === last || position(xs[last]) - position(xs[index]) >= LABEL_GAP
  )
}

export function directLabelOffsets(ends: number[]): number[] {
  const order = ends
    .map((y, index) => ({ y, index }))
    .sort((left, right) => left.y - right.y)
  const placed: number[] = new Array<number>(ends.length)
  let previous = Number.NEGATIVE_INFINITY
  for (const item of order) {
    const y = Math.max(item.y, previous + DIRECT_LABEL_SPACING)
    placed[item.index] = y
    previous = y
  }
  return placed
}

export function nearestIndex(
  xs: number[],
  position: (x: number) => number,
  pointer: number
): number {
  let best = 0
  let distance = Number.POSITIVE_INFINITY
  xs.forEach((x, index) => {
    const gap = Math.abs(position(x) - pointer)
    if (gap < distance) {
      distance = gap
      best = index
    }
  })
  return best
}

export function shortLabel(label: string): string {
  return label.length > DIRECT_LABEL_CHARS
    ? label.slice(0, DIRECT_LABEL_CHARS)
    : label
}
