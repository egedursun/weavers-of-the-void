import { plural } from '@/lib/units'
import {
  type ThemeColorName,
  type ThemeColors,
} from '@/components/domain/useThemeColors'
import { type MapView } from './api'
import { type Transform, tracePolyline } from './mapModel'

export const LINE_KINDS = [
  'road',
  'trade_road',
  'trade',
  'hostility',
  'rule',
  'hunt',
  'route',
  'route_busy',
  'route_blocked',
  'outbreak',
  'front',
  'supply',
] as const
export type LineKind = (typeof LINE_KINDS)[number]

export const ROAD_KINDS: ReadonlySet<LineKind> = new Set(['road', 'trade_road'])
export const OUTBREAK_KINDS: ReadonlySet<LineKind> = new Set(['outbreak'])
export const MILITARY_KINDS: ReadonlySet<LineKind> = new Set([
  'front',
  'supply',
])
export const ROUTE_KINDS: ReadonlySet<LineKind> = new Set([
  'route',
  'route_busy',
  'route_blocked',
])
const BUSY_SHARE = 0.5

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
  route: {
    casing: { color: halo, width: 4, alpha: 0.4 },
    main: { color: gold, width: 1.8, alpha: 0.85 },
    flow: { color: light, width: 1, alpha: 0.7, dash: [2, 10], speed: 0.015 },
  },
  route_busy: {
    casing: { color: halo, width: 7, alpha: 0.45 },
    main: { color: gold, width: 3.6, alpha: 0.95 },
    flow: { color: light, width: 1.6, alpha: 0.85, dash: [3, 9], speed: 0.03 },
  },
  route_blocked: {
    casing: { color: halo, width: 4, alpha: 0.4 },
    main: { color: red, width: 1.8, alpha: 0.9, dash: [5, 5] },
  },
  outbreak: {
    casing: { color: halo, width: 4, alpha: 0.4 },
    main: { color: red, width: 2, alpha: 0.9, dash: [3, 3], speed: 0.02 },
    arrow: true,
  },
  front: {
    casing: { color: halo, width: 6, alpha: 0.45 },
    main: { color: red, width: 3, alpha: 0.95, dash: [2, 2] },
  },
  supply: {
    casing: { color: halo, width: 3, alpha: 0.35 },
    main: { color: gold, width: 1.4, alpha: 0.85, dash: [6, 3], speed: 0.01 },
    arrow: true,
  },
}
const ARMY_RADIUS = 3
const ARMY_SCALE = 0.9
const OCCUPIED_RADIUS = 9
const OCCUPIED_ALPHA = 0.22
const SICK_RADIUS = 4
const SICK_SCALE = 0.08
const SICK_ALPHA = 0.35
const ENDEMIC_ALPHA = 0.18

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
  for (const route of view.trade ?? [])
    shapes.push({
      info: {
        kind:
          route.status === 'blockaded'
            ? 'route_blocked'
            : route.capacity > 0 && route.volume >= route.capacity * BUSY_SHARE
              ? 'route_busy'
              : 'route',
        source: route.first,
        target: route.second,
        description: `${route.name}: ${route.volume} of ${route.capacity} carried`,
        length: null,
      },
      points: route.path,
      arrow: null,
    })
  for (const sickness of view.outbreaks ?? []) {
    if (sickness.endemic || sickness.path.length !== 4) continue
    const bent = curve(
      sickness.path,
      sickness.region_id > (sickness.source_region_id ?? 0)
    )
    shapes.push({
      info: {
        kind: 'outbreak',
        source: sickness.source_region_id ?? sickness.region_id,
        target: sickness.region_id,
        description: `${sickness.disease}: ${sickness.dead} dead`,
        length: null,
      },
      points: bent.points,
      arrow: bent.arrow,
    })
  }
  for (const front of view.fronts ?? []) {
    if (front.path.length !== 4) continue
    shapes.push({
      info: {
        kind: 'front',
        source: front.first_region_id,
        target: front.second_region_id,
        description: 'The front of a war',
        length: null,
      },
      points: front.path,
      arrow: null,
    })
  }
  for (const army of view.armies ?? []) {
    if (army.path.length < 4) continue
    shapes.push({
      info: {
        kind: 'supply',
        source: army.army_id,
        target: army.region_id ?? army.army_id,
        description: `${army.name}: ${plural(army.size, 'soldier', 'soldiers')}, ${army.stance.replaceAll('_', ' ')}${army.blockade_id !== null ? ', holding a blockade' : ''}`,
        length: null,
      },
      points: army.path,
      arrow: null,
    })
  }
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

function visibleShapes(
  view: MapView,
  roads: boolean,
  ties: boolean,
  trade = false,
  outbreaks = false,
  military = false
): Shape[] {
  return shapesOf(view).filter((shape) =>
    MILITARY_KINDS.has(shape.info.kind)
      ? military
      : OUTBREAK_KINDS.has(shape.info.kind)
        ? outbreaks
        : ROUTE_KINDS.has(shape.info.kind)
          ? trade
          : ROAD_KINDS.has(shape.info.kind)
            ? roads
            : ties
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
    trade?: boolean
    outbreaks?: boolean
    military?: boolean
    faith?: boolean
    lore?: boolean
    beasts?: boolean
    time: number
    animate: boolean
    fade: number
  }
): void {
  if (options.outbreaks)
    drawSickLands(context, view, tokens, transform.k, options.fade)
  if (options.military)
    drawArmies(context, view, tokens, transform.k, options.fade)
  if (options.faith) drawHoly(context, view, tokens, transform.k, options.fade)
  if (options.lore) drawLore(context, view, tokens, transform.k, options.fade)
  if (options.beasts)
    drawLairs(context, view, tokens, transform.k, options.fade)
  if (options.trade)
    drawConvoys(context, view, tokens, transform.k, options.fade)
  const shapes = visibleShapes(
    view,
    options.roads,
    options.ties,
    options.trade,
    options.outbreaks,
    options.military
  )
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

const CONVOY_RADIUS = 3
const CONVOY_GUARD_SCALE = 0.25
const CONVOY_ALONG: Record<string, number> = {
  loading: 0.1,
  travelling: 0.5,
  delayed: 0.35,
}

function drawConvoys(
  context: CanvasRenderingContext2D,
  view: MapView,
  tokens: ThemeColors,
  k: number,
  fade: number
): void {
  for (const convoy of view.convoys ?? []) {
    if (convoy.path.length < 4) continue
    const share = CONVOY_ALONG[convoy.status] ?? 0.5
    const x = convoy.path[0] + (convoy.path[2] - convoy.path[0]) * share
    const y = convoy.path[1] + (convoy.path[3] - convoy.path[1]) * share
    context.globalAlpha = fade
    context.fillStyle =
      convoy.status === 'delayed' ? tokens.warning : tokens['brand-gold']
    context.beginPath()
    context.arc(
      x,
      y,
      (CONVOY_RADIUS + Math.sqrt(convoy.guards) * CONVOY_GUARD_SCALE) / k,
      0,
      Math.PI * 2
    )
    context.fill()
  }
  context.globalAlpha = fade
}

function drawSickLands(
  context: CanvasRenderingContext2D,
  view: MapView,
  tokens: ThemeColors,
  k: number,
  fade: number
): void {
  context.fillStyle = tokens.destructive
  for (const sickness of view.outbreaks ?? []) {
    if (sickness.path.length < 2) continue
    const x = sickness.path[sickness.path.length - 2]
    const y = sickness.path[sickness.path.length - 1]
    context.globalAlpha = (sickness.endemic ? ENDEMIC_ALPHA : SICK_ALPHA) * fade
    context.beginPath()
    context.arc(
      x,
      y,
      (SICK_RADIUS + sickness.severity * SICK_SCALE) / k,
      0,
      Math.PI * 2
    )
    context.fill()
  }
  context.globalAlpha = fade
}

function drawArmies(
  context: CanvasRenderingContext2D,
  view: MapView,
  tokens: ThemeColors,
  k: number,
  fade: number
): void {
  const places = new Map<number, readonly [number, number]>()
  for (const point of view.points)
    if (point.x !== null && point.y !== null)
      places.set(point.entity.id, [point.x, point.y])
  context.fillStyle = tokens.destructive
  for (const [region] of Object.entries(view.occupations ?? {})) {
    const at = places.get(Number(region))
    if (!at) continue
    context.globalAlpha = OCCUPIED_ALPHA * fade
    context.beginPath()
    context.arc(at[0], at[1], OCCUPIED_RADIUS / k, 0, Math.PI * 2)
    context.fill()
  }
  context.fillStyle = tokens['brand-gold']
  for (const army of view.armies ?? []) {
    if (army.path.length < 2) continue
    const x = army.path[army.path.length - 2]
    const y = army.path[army.path.length - 1]
    context.globalAlpha = fade
    context.beginPath()
    context.arc(
      x,
      y,
      (ARMY_RADIUS + Math.log10(Math.max(1, army.size)) * ARMY_SCALE) / k,
      0,
      Math.PI * 2
    )
    context.fill()
  }
  context.globalAlpha = fade
}

const HOLY_RADIUS = 3.5
const HOLY_ALPHA = 0.9

function drawHoly(
  context: CanvasRenderingContext2D,
  view: MapView,
  tokens: ThemeColors,
  k: number,
  fade: number
): void {
  context.fillStyle = tokens['rarity-epic']
  context.globalAlpha = HOLY_ALPHA * fade
  for (const place of view.holy ?? []) {
    const size = HOLY_RADIUS / k
    context.beginPath()
    context.moveTo(place.x, place.y - size)
    context.lineTo(place.x + size, place.y)
    context.lineTo(place.x, place.y + size)
    context.lineTo(place.x - size, place.y)
    context.closePath()
    context.fill()
  }
  context.globalAlpha = fade
}

const LORE_RADIUS = 3
const LORE_ALPHA = 0.85
const LORE_COLOR: Record<string, ThemeColorName> = {
  haunted: 'muted-foreground',
  casting: 'rarity-legendary',
  creed: 'brand-verdigris',
  artwork: 'rarity-rare',
  learning: 'chart-2',
}

function drawLore(
  context: CanvasRenderingContext2D,
  view: MapView,
  tokens: ThemeColors,
  k: number,
  fade: number
): void {
  context.globalAlpha = LORE_ALPHA * fade
  for (const mark of view.lore ?? []) {
    const size = LORE_RADIUS / k
    context.fillStyle = tokens[LORE_COLOR[mark.kind] ?? 'accent']
    context.beginPath()
    if (mark.kind === 'creed')
      context.rect(mark.x - size, mark.y - size, size * 2, size * 2)
    else if (mark.kind === 'casting') {
      for (let point = 0; point < 10; point += 1) {
        const radius = point % 2 === 0 ? size * 1.4 : size * 0.6
        const angle = (Math.PI * point) / 5 - Math.PI / 2
        context.lineTo(
          mark.x + radius * Math.cos(angle),
          mark.y + radius * Math.sin(angle)
        )
      }
      context.closePath()
    } else context.arc(mark.x, mark.y, size, 0, Math.PI * 2)
    context.fill()
  }
  context.globalAlpha = fade
}

const LAIR_RADIUS = 4
const TERROR_REACH = 18
const TERROR_ALPHA = 0.18

function drawLairs(
  context: CanvasRenderingContext2D,
  view: MapView,
  tokens: ThemeColors,
  k: number,
  fade: number
): void {
  for (const lair of view.lairs ?? []) {
    const reach =
      (TERROR_REACH * Math.max(1, lair.reach) * (lair.terror / 100)) / k
    context.globalAlpha = TERROR_ALPHA * fade
    context.fillStyle = tokens.destructive
    context.beginPath()
    context.arc(lair.x, lair.y, reach, 0, Math.PI * 2)
    context.fill()
    context.globalAlpha = fade
    context.fillStyle =
      lair.temper === 'sleeping'
        ? tokens['muted-foreground']
        : tokens.destructive
    context.beginPath()
    context.arc(lair.x, lair.y, LAIR_RADIUS / k, 0, Math.PI * 2)
    context.fill()
  }
  context.globalAlpha = fade
}

export type LineHit = { info: LineInfo; points: number[] }

export function lineHits(
  view: MapView,
  transform: Transform,
  roads: boolean,
  ties: boolean,
  trade = false,
  outbreaks = false,
  military = false
): LineHit[] {
  return visibleShapes(view, roads, ties, trade, outbreaks, military).map(
    (shape) => {
      const points: number[] = []
      for (let index = 0; index + 1 < shape.points.length; index += 2)
        points.push(
          shape.points[index] * transform.k + transform.x,
          shape.points[index + 1] * transform.k + transform.y
        )
      return { info: shape.info, points }
    }
  )
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
