import { type ThemeColors } from '@/components/domain/useThemeColors'
import { type MapView } from './api'
import { type Transform, tracePolyline } from './mapModel'

export const LINE_KINDS = [
  'road',
  'trade_road',
  'trade',
  'hostility',
  'rule',
  'hunt',
] as const
export type LineKind = (typeof LINE_KINDS)[number]

export const ROAD_KINDS: ReadonlySet<LineKind> = new Set(['road', 'trade_road'])

export type LineInfo = {
  kind: LineKind
  source: number
  target: number
  description: string | null
  length: number | null
}

type Shape = {
  info: LineInfo
  points: number[]
  arrow: { x: number; y: number; angle: number } | null
}

type Stroke = {
  color: (tokens: ThemeColors, view: MapView) => string
  width: number
  alpha: number
  dash?: readonly number[]
  speed?: number
}

type LineStyle = {
  casing?: Stroke
  main: Stroke
  flow?: Stroke
  arrow?: boolean
}

const halo = (_: ThemeColors, view: MapView) => view.geometry.palette.background
const gold = (tokens: ThemeColors) => tokens['brand-gold']
const red = (tokens: ThemeColors) => tokens.destructive
const violet = (tokens: ThemeColors) => tokens['rarity-epic']
const coast = (_: ThemeColors, view: MapView) => view.geometry.palette.coastline
const light = (_: ThemeColors, view: MapView) =>
  view.geometry.palette.land_label

export const LINE_STYLE: Record<LineKind, LineStyle> = {
  road: {
    casing: { color: halo, width: 3.4, alpha: 0.45 },
    main: { color: coast, width: 1.3, alpha: 0.85, dash: [4, 3] },
  },
  trade_road: {
    casing: { color: halo, width: 5, alpha: 0.55 },
    main: { color: gold, width: 2.6, alpha: 0.95 },
    flow: { color: light, width: 1.1, alpha: 0.75, dash: [2, 12], speed: 0.02 },
  },
  trade: {
    main: { color: gold, width: 1.5, alpha: 0.8, dash: [1, 4], speed: 0.012 },
  },
  hostility: {
    casing: { color: halo, width: 3.2, alpha: 0.35 },
    main: { color: red, width: 1.6, alpha: 0.9, dash: [7, 4], speed: 0.006 },
  },
  rule: {
    casing: { color: halo, width: 3, alpha: 0.35 },
    main: { color: violet, width: 1.4, alpha: 0.85 },
    arrow: true,
  },
  hunt: {
    main: { color: red, width: 1.1, alpha: 0.9, dash: [1, 3] },
    arrow: true,
  },
}

const CURVE_BEND = 0.16
const CURVE_SAMPLES = 20
const ARROW_AT = 0.56
const ARROW_PX = 6
const HIT_TOLERANCE = 5

const shapeCache = new WeakMap<MapView, Shape[]>()

function curve(
  path: readonly number[],
  flip: boolean
): { points: number[]; arrow: Shape['arrow'] } {
  const [x1, y1, x2, y2] = path
  const dx = x2 - x1
  const dy = y2 - y1
  const bend = (flip ? -1 : 1) * CURVE_BEND
  const cx = (x1 + x2) / 2 - dy * bend
  const cy = (y1 + y2) / 2 + dx * bend
  const points: number[] = []
  for (let step = 0; step <= CURVE_SAMPLES; step += 1) {
    const t = step / CURVE_SAMPLES
    const u = 1 - t
    points.push(
      u * u * x1 + 2 * u * t * cx + t * t * x2,
      u * u * y1 + 2 * u * t * cy + t * t * y2
    )
  }
  const t = ARROW_AT
  const u = 1 - t
  const x = u * u * x1 + 2 * u * t * cx + t * t * x2
  const y = u * u * y1 + 2 * u * t * cy + t * t * y2
  const tx = 2 * u * (cx - x1) + 2 * t * (x2 - cx)
  const ty = 2 * u * (cy - y1) + 2 * t * (y2 - cy)
  return { points, arrow: { x, y, angle: Math.atan2(ty, tx) } }
}

function shapesOf(view: MapView): Shape[] {
  const cached = shapeCache.get(view)
  if (cached) return cached
  const shapes: Shape[] = []
  for (const road of view.roads)
    shapes.push({
      info: {
        kind: road.kind === 'trade' ? 'trade_road' : 'road',
        source: road.first,
        target: road.second,
        description: null,
        length: road.length,
      },
      points: road.path,
      arrow: null,
    })
  for (const line of view.relations) {
    const kind = line.kind as LineKind
    const info = {
      kind,
      source: line.source,
      target: line.target,
      description: line.description ?? null,
      length: null,
    }
    if (line.path.length === 4 && kind !== 'trade') {
      const bent = curve(line.path, line.source > line.target)
      shapes.push({
        info,
        points: bent.points,
        arrow: LINE_STYLE[kind].arrow ? bent.arrow : null,
      })
    } else shapes.push({ info, points: line.path, arrow: null })
  }
  shapeCache.set(view, shapes)
  return shapes
}

function visibleShapes(view: MapView, roads: boolean, ties: boolean): Shape[] {
  return shapesOf(view).filter((shape) =>
    ROAD_KINDS.has(shape.info.kind) ? roads : ties
  )
}

function applyStroke(
  context: CanvasRenderingContext2D,
  stroke: Stroke,
  tokens: ThemeColors,
  view: MapView,
  k: number,
  time: number,
  animate: boolean,
  fade: number
): void {
  context.strokeStyle = stroke.color(tokens, view)
  context.globalAlpha = stroke.alpha * fade
  context.lineWidth = stroke.width / k
  context.setLineDash((stroke.dash ?? []).map((value) => value / k))
  context.lineDashOffset =
    animate && stroke.speed ? (-time * stroke.speed) / k : 0
}

export function drawLines(
  context: CanvasRenderingContext2D,
  view: MapView,
  tokens: ThemeColors,
  transform: Transform,
  options: {
    roads: boolean
    ties: boolean
    time: number
    animate: boolean
    fade: number
  }
): void {
  const shapes = visibleShapes(view, options.roads, options.ties)
  if (shapes.length === 0) return
  const k = transform.k
  context.lineJoin = 'round'
  context.lineCap = 'round'
  for (const kind of LINE_KINDS) {
    const style = LINE_STYLE[kind]
    const ofKind = shapes.filter((shape) => shape.info.kind === kind)
    if (ofKind.length === 0) continue
    const path = new Path2D()
    for (const shape of ofKind) tracePolyline(path, shape.points)
    for (const stroke of [style.casing, style.main, style.flow]) {
      if (!stroke) continue
      applyStroke(
        context,
        stroke,
        tokens,
        view,
        k,
        options.time,
        options.animate,
        options.fade
      )
      context.stroke(path)
    }
    if (!style.arrow) continue
    context.setLineDash([])
    context.globalAlpha = style.main.alpha * options.fade
    context.fillStyle = style.main.color(tokens, view)
    const size = ARROW_PX / k
    for (const shape of ofKind) {
      if (!shape.arrow) continue
      context.save()
      context.translate(shape.arrow.x, shape.arrow.y)
      context.rotate(shape.arrow.angle)
      context.beginPath()
      context.moveTo(size, 0)
      context.lineTo(-size * 0.8, size * 0.7)
      context.lineTo(-size * 0.4, 0)
      context.lineTo(-size * 0.8, -size * 0.7)
      context.closePath()
      context.fill()
      context.restore()
    }
  }
  context.setLineDash([])
  context.lineDashOffset = 0
  context.globalAlpha = options.fade
}

export type LineHit = { info: LineInfo; points: number[] }

export function lineHits(
  view: MapView,
  transform: Transform,
  roads: boolean,
  ties: boolean
): LineHit[] {
  return visibleShapes(view, roads, ties).map((shape) => {
    const points: number[] = []
    for (let index = 0; index + 1 < shape.points.length; index += 2)
      points.push(
        shape.points[index] * transform.k + transform.x,
        shape.points[index + 1] * transform.k + transform.y
      )
    return { info: shape.info, points }
  })
}

function segmentDistance(
  px: number,
  py: number,
  ax: number,
  ay: number,
  bx: number,
  by: number
): number {
  const dx = bx - ax
  const dy = by - ay
  const span = dx * dx + dy * dy
  const t =
    span === 0
      ? 0
      : Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / span))
  return Math.hypot(px - (ax + t * dx), py - (ay + t * dy))
}

export function nearLine(points: readonly number[], x: number, y: number) {
  for (let index = 0; index + 3 < points.length; index += 2)
    if (
      segmentDistance(
        x,
        y,
        points[index],
        points[index + 1],
        points[index + 2],
        points[index + 3]
      ) <= HIT_TOLERANCE
    )
      return true
  return false
}
