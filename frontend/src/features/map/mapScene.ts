import { type ThemeColors } from '@/components/domain/useThemeColors'
import { familyOf } from '@/features/graph/families'
import { type MapNote, type MapView } from './api'
import { type DomainAnchor, regionOutline } from './mapEdges'
import {
  EVENT_RADIUS,
  countBadge,
  crownGlyph,
  donutRing,
  entityGlyph,
  font,
  haloText,
  pinGlyph,
  portraitGlyph,
  settlementGlyph,
  stackGlyph,
  trendGlyph,
} from './mapGlyphs'
import {
  type HitTarget,
  type Layout,
  type LayoutInput,
  type MarkerDraw,
  computeLayout,
  locate,
} from './mapLayout'
import { drawLines, nearLine } from './mapLines'
import {
  type LayerMode,
  type Overlay,
  type PositionedPoint,
  isDead,
  populationTrend,
  toScreen,
} from './mapModel'
import { markerImage } from './markerImages'
import { type MapTexture, type TintLayer, drawTexture } from './terrainLayer'
import { type LayerPalette } from './useLayerPalette'

export {
  type HitKind,
  type HitTarget,
  type MarkerFilter,
  type Thresholds,
  locate,
} from './mapLayout'

export type NoteColor = 'gold' | 'red' | 'blue' | 'green' | 'violet'

export const NOTE_COLORS: readonly NoteColor[] = [
  'gold',
  'red',
  'blue',
  'green',
  'violet',
]

export const NOTE_TOKEN: Record<NoteColor, keyof ThemeColors> = {
  gold: 'brand-gold',
  red: 'destructive',
  blue: 'chart-2',
  green: 'rarity-uncommon',
  violet: 'rarity-epic',
}

export function noteColor(note: MapNote): NoteColor {
  return (NOTE_COLORS as readonly string[]).includes(note.color ?? '')
    ? (note.color as NoteColor)
    : 'gold'
}

export type SceneInput = LayoutInput & {
  terrain: MapTexture | null
  tint: TintLayer | null
  fog: MapTexture | null
  trendPct: number
  focusStartedAt: number
  time: number
  animate: boolean
  entrance: number
  leakLevel: 0 | 1 | 2
  onImage: () => void
}

const FOCUS_PULSE_MS = 800
const FOCUS_PULSES = 3
const WAR_PULSE_MS = 1400
const GRAIN_SIZE = 128
const GRAIN_ALPHA = 0.07
const VIGNETTE_ALPHA = 0.5
const HATCH_SIZE = 9
const HATCH_ALPHA = 0.42
const OUTLINE_WIDTH = 2.4
const OUTLINE_GLOW = 10
const DOMAIN_CASING = 3.8
const DOMAIN_LINE = 1.7
const TAU = Math.PI * 2

export type DrawScene = (
  context: CanvasRenderingContext2D,
  input: SceneInput
) => HitTarget[]

function drawBorders(
  context: CanvasRenderingContext2D,
  view: MapView,
  k: number,
  mode: LayerMode,
  fade: number
) {
  const palette = view.geometry.palette
  const coordinates = view.geometry.borders.coordinates
  const thematic = mode !== 'terrain' && mode !== 'regions'
  const styles = {
    coast: { color: palette.coastline, width: 1.1, alpha: 0.75, dash: [] },
    region: thematic
      ? { color: palette.land_label, width: 0.9, alpha: 0.4, dash: [4, 3] }
      : { color: palette.land_label, width: 1.2, alpha: 0.6, dash: [5, 3] },
    sub_region: thematic
      ? { color: palette.land_label, width: 0.6, alpha: 0.3, dash: [2, 3] }
      : { color: palette.land_label, width: 0.7, alpha: 0.45, dash: [2, 3] },
  }
  for (const kind of ['sub_region', 'region', 'coast'] as const) {
    const style = styles[kind]
    context.beginPath()
    view.geometry.borders.kinds.forEach((found, index) => {
      if (found !== kind) return
      const offset = index * 4
      context.moveTo(coordinates[offset], coordinates[offset + 1])
      context.lineTo(coordinates[offset + 2], coordinates[offset + 3])
    })
    context.strokeStyle = style.color
    context.globalAlpha = style.alpha * fade
    context.lineWidth = style.width / k
    context.setLineDash(style.dash.map((value) => value / k))
    context.stroke()
  }
  context.setLineDash([])
  context.globalAlpha = fade
}

function drawDomainBorder(
  context: CanvasRenderingContext2D,
  view: MapView,
  tint: TintLayer,
  k: number,
  fade: number
) {
  const palette = view.geometry.palette
  context.lineJoin = 'round'
  context.lineCap = 'round'
  context.globalAlpha = 0.6 * fade
  context.strokeStyle = palette.background
  context.lineWidth = DOMAIN_CASING / k
  context.stroke(tint.border)
  context.globalAlpha = 0.9 * fade
  context.strokeStyle = palette.land_label
  context.lineWidth = DOMAIN_LINE / k
  context.stroke(tint.border)
  context.globalAlpha = fade
}

const hatchCache = new Map<string, CanvasPattern | null>()

function hatchPattern(
  context: CanvasRenderingContext2D,
  color: string,
  ratio: number
): CanvasPattern | null {
  const key = `${color}|${ratio}`
  if (hatchCache.has(key)) return hatchCache.get(key) ?? null
  const side = Math.round(HATCH_SIZE * ratio)
  const tile = document.createElement('canvas')
  tile.width = side
  tile.height = side
  const tileContext = tile.getContext('2d')
  let pattern: CanvasPattern | null = null
  if (tileContext) {
    tileContext.strokeStyle = color
    tileContext.lineWidth = 1.3 * ratio
    tileContext.beginPath()
    for (const offset of [-side, 0, side]) {
      tileContext.moveTo(offset, side)
      tileContext.lineTo(offset + side, 0)
    }
    tileContext.stroke()
    pattern = context.createPattern(tile, 'repeat')
  }
  hatchCache.set(key, pattern)
  return pattern
}

function drawContested(
  context: CanvasRenderingContext2D,
  view: MapView,
  path: Path2D,
  ratio: number,
  size: { width: number; height: number },
  fade: number
) {
  const pattern = hatchPattern(context, view.geometry.palette.land_label, ratio)
  if (!pattern) return
  context.save()
  context.clip(path)
  context.setTransform(1, 0, 0, 1, 0, 0)
  context.globalAlpha = HATCH_ALPHA * fade
  context.fillStyle = pattern
  context.fillRect(0, 0, size.width * ratio, size.height * ratio)
  context.restore()
}

function drawOutline(
  context: CanvasRenderingContext2D,
  path: Path2D,
  color: string,
  k: number,
  fade: number
) {
  context.save()
  context.shadowColor = color
  context.shadowBlur = OUTLINE_GLOW
  context.globalAlpha = 0.95 * fade
  context.strokeStyle = color
  context.lineWidth = OUTLINE_WIDTH / k
  context.lineJoin = 'round'
  context.stroke(path)
  context.restore()
}

function drawUnexplored(context: CanvasRenderingContext2D, input: SceneInput) {
  const extent = input.view.geometry.extent
  const palette = input.view.geometry.palette
  const middle = extent.y + extent.height / 2
  const left = toScreen(input.transform, extent.x, middle)
  const right = toScreen(input.transform, extent.x + extent.width, middle)
  context.font = font(12, input.tokens.fontDisplay, 400, true)
  context.letterSpacing = '0.4em'
  context.fillStyle = palette.land_label
  context.globalAlpha = 0.35 * input.entrance
  context.textAlign = 'center'
  context.textBaseline = 'middle'
  for (const [point, angle] of [
    [left, -Math.PI / 2],
    [right, Math.PI / 2],
  ] as const) {
    context.save()
    context.translate(point.x + (angle < 0 ? -22 : 22), point.y)
    context.rotate(angle)
    context.fillText('TERRA INCOGNITA', 0, 0)
    context.restore()
  }
  context.letterSpacing = '0px'
  context.globalAlpha = 1
}

let grainTile: HTMLCanvasElement | null = null
const grainPatterns = new WeakMap<CanvasRenderingContext2D, CanvasPattern>()

function grainOf(context: CanvasRenderingContext2D): CanvasPattern | null {
  const known = grainPatterns.get(context)
  if (known) return known
  if (!grainTile) {
    const tile = document.createElement('canvas')
    tile.width = GRAIN_SIZE
    tile.height = GRAIN_SIZE
    const tileContext = tile.getContext('2d')
    if (!tileContext) return null
    const image = tileContext.createImageData(GRAIN_SIZE, GRAIN_SIZE)
    for (let index = 0; index < image.data.length; index += 4) {
      const value = Math.floor(Math.random() * 256)
      image.data[index] = value
      image.data[index + 1] = value
      image.data[index + 2] = value
      image.data[index + 3] = 255
    }
    tileContext.putImageData(image, 0, 0)
    grainTile = tile
  }
  const pattern = context.createPattern(grainTile, 'repeat')
  if (pattern) grainPatterns.set(context, pattern)
  return pattern
}

function drawGrain(context: CanvasRenderingContext2D, input: SceneInput) {
  const pattern = grainOf(context)
  if (!pattern) return
  context.save()
  context.globalCompositeOperation = 'overlay'
  context.globalAlpha = GRAIN_ALPHA * input.entrance
  context.fillStyle = pattern
  context.fillRect(0, 0, input.size.width, input.size.height)
  context.restore()
}

function drawVignette(context: CanvasRenderingContext2D, input: SceneInput) {
  const { width, height } = input.size
  const gradient = context.createRadialGradient(
    width / 2,
    height / 2,
    Math.min(width, height) * 0.45,
    width / 2,
    height / 2,
    Math.hypot(width, height) * 0.6
  )
  gradient.addColorStop(0, 'transparent')
  gradient.addColorStop(1, input.view.geometry.palette.background)
  context.globalAlpha = VIGNETTE_ALPHA
  context.fillStyle = gradient
  context.fillRect(0, 0, width, height)
  context.globalAlpha = 1
}

function drawLeak(context: CanvasRenderingContext2D, input: SceneInput) {
  if (input.leakLevel === 0) return
  const { width, height } = input.size
  const breathing = input.animate
    ? 0.5 + 0.5 * Math.sin(input.time / 1200)
    : 0.5
  const strength = input.leakLevel === 2 ? 0.55 : 0.32
  const gradient = context.createRadialGradient(
    width / 2,
    height / 2,
    Math.min(width, height) * 0.25,
    width / 2,
    height / 2,
    Math.max(width, height) * 0.75
  )
  gradient.addColorStop(0, 'transparent')
  gradient.addColorStop(1, input.tokens['rarity-epic'])
  context.globalAlpha = strength * (0.7 + 0.3 * breathing)
  if (
    input.leakLevel === 2 &&
    input.animate &&
    Math.sin(input.time / 97) > 0.97
  )
    context.globalAlpha = Math.min(1, context.globalAlpha + 0.25)
  context.fillStyle = gradient
  context.fillRect(0, 0, width, height)
  context.globalAlpha = 1
}

const glintCache = new WeakMap<MapView, number[]>()

function glintCells(view: MapView): number[] {
  const found = glintCache.get(view)
  if (found) return found
  const cells = view.geometry.cells
  const chosen: number[] = []
  for (
    let index = 0;
    index < cells.x.length && chosen.length < 90;
    index += 7
  ) {
    if (cells.water[index] && cells.coastal[index] && cells.known[index] !== 0)
      chosen.push(index)
  }
  glintCache.set(view, chosen)
  return chosen
}

function seeded(seed: string): () => number {
  let state = 2166136261
  for (const char of seed)
    state = Math.imul(state ^ char.charCodeAt(0), 16777619)
  return () => {
    state = Math.imul(state ^ (state >>> 15), 2246822507)
    state = Math.imul(state ^ (state >>> 13), 3266489909)
    state ^= state >>> 16
    return (state >>> 0) / 4294967296
  }
}

function drawAmbient(context: CanvasRenderingContext2D, input: SceneInput) {
  if (!input.animate) return
  const { view, transform, time } = input
  const palette = view.geometry.palette
  const cells = view.geometry.cells
  context.fillStyle = palette.water_label
  glintCells(view).forEach((index, order) => {
    const alpha = Math.max(0, Math.sin(time / 700 + order * 1.7)) * 0.55
    if (alpha <= 0.02) return
    const point = toScreen(transform, cells.x[index], cells.y[index])
    context.globalAlpha = alpha * input.entrance
    context.beginPath()
    context.arc(point.x, point.y, 1.6, 0, TAU)
    context.fill()
  })
  const random = seeded(view.geometry.seed)
  const window = view.geometry.window
  for (let cloud = 0; cloud < 14; cloud += 1) {
    const radius = 180 + random() * 340
    const speed = 0.006 + random() * 0.012
    const alpha = 0.035 + random() * 0.05
    const baseX = window.x + random() * window.width
    const baseY = window.y + random() * window.height
    const span = window.width + radius * 2
    const x =
      window.x -
      radius +
      ((((baseX - window.x + time * speed) % span) + span) % span)
    const y = baseY + Math.sin(time / 4000 + cloud) * 12
    const centre = toScreen(transform, x, y)
    const reach = radius * transform.k
    const gradient = context.createRadialGradient(
      centre.x,
      centre.y,
      0,
      centre.x,
      centre.y,
      reach
    )
    gradient.addColorStop(0, palette.land_label)
    gradient.addColorStop(1, 'transparent')
    context.globalAlpha = alpha * input.entrance
    context.fillStyle = gradient
    context.fillRect(centre.x - reach, centre.y - reach, reach * 2, reach * 2)
  }
  context.globalAlpha = 1
}

function drawMarker(
  context: CanvasRenderingContext2D,
  input: SceneInput,
  marker: MarkerDraw
) {
  const { tokens, view } = input
  const halo = view.geometry.palette.background
  const point = marker.point
  const dead = isDead(point.status)
  const color =
    point.type === 'settlement'
      ? tokens['brand-gold']
      : (tokens[familyOf(point.type).token] as string)
  context.save()
  context.translate(marker.x, marker.y)
  if (marker.slices.length > 0)
    donutRing(context, marker.radius, marker.slices, halo)
  const image =
    marker.portrait && point.cover
      ? markerImage(point.cover, input.onImage)
      : null
  if (image) portraitGlyph(context, image, marker.radius, color, dead, halo)
  else if (marker.tier)
    settlementGlyph(context, marker.tier, dead, tokens, halo)
  else
    entityGlyph(context, point.type, marker.radius, color, dead, tokens, halo)
  if (marker.tier) {
    const info = view.settlements[String(point.id)]
    const trend = info
      ? populationTrend(
          info.population,
          info.previous_population,
          input.trendPct
        )
      : null
    if (trend) trendGlyph(context, trend, marker.radius, tokens, halo)
  }
  if (marker.crown) crownGlyph(context, marker.radius, marker.crown, halo)
  if (marker.members.length > 1)
    countBadge(
      context,
      marker.members.length,
      marker.radius,
      halo,
      view.geometry.palette.land_label,
      tokens.fontBody
    )
  if (input.hoverKey === marker.key) {
    context.beginPath()
    context.arc(0, 0, marker.radius + 6, 0, TAU)
    context.strokeStyle = view.geometry.palette.land_label
    context.lineWidth = 1.5
    context.stroke()
  }
  context.restore()
}

function drawStacks(
  context: CanvasRenderingContext2D,
  input: SceneInput,
  layout: Layout
) {
  const { view, tokens } = input
  const palette = view.geometry.palette
  const halo = palette.background
  for (const glow of layout.glows) {
    const gradient = context.createRadialGradient(
      glow.x,
      glow.y,
      0,
      glow.x,
      glow.y,
      glow.radius
    )
    gradient.addColorStop(0, tokens.destructive)
    gradient.addColorStop(1, 'transparent')
    context.globalAlpha = (glow.hot ? 0.42 : 0.2) * input.entrance
    context.fillStyle = gradient
    context.fillRect(
      glow.x - glow.radius,
      glow.y - glow.radius,
      glow.radius * 2,
      glow.radius * 2
    )
  }
  context.globalAlpha = input.entrance
  for (const stack of layout.stacks) {
    context.save()
    context.translate(stack.x, stack.y)
    if (stack.kind === 'war' && stack.ongoing) {
      const phase = input.animate
        ? (input.time % WAR_PULSE_MS) / WAR_PULSE_MS
        : 0.5
      context.globalAlpha = (1 - phase) * 0.8 * input.entrance
      context.beginPath()
      context.arc(0, 0, EVENT_RADIUS + phase * 9, 0, TAU)
      context.strokeStyle = tokens.destructive
      context.lineWidth = 1.6
      context.stroke()
      context.globalAlpha = input.entrance
    }
    if (stack.slices.length > 0)
      donutRing(context, EVENT_RADIUS, stack.slices, halo)
    if (stack.kind === 'war' && !stack.ongoing)
      context.globalAlpha = 0.7 * input.entrance
    stackGlyph(context, stack.color, stack.icon, halo)
    context.globalAlpha = input.entrance
    if (stack.count > 1)
      countBadge(
        context,
        stack.count,
        EVENT_RADIUS,
        halo,
        palette.land_label,
        tokens.fontBody
      )
    if (input.hoverKey === stack.key) {
      context.beginPath()
      context.arc(0, 0, EVENT_RADIUS + 5, 0, TAU)
      context.strokeStyle = palette.land_label
      context.lineWidth = 1.5
      context.stroke()
    }
    context.restore()
  }
}

function drawLabels(
  context: CanvasRenderingContext2D,
  input: SceneInput,
  layout: Layout
) {
  const halo = input.view.geometry.palette.background
  context.textAlign = 'center'
  context.textBaseline = 'middle'
  for (const label of layout.labels) {
    context.font = label.font
    context.letterSpacing = label.spacing
    context.globalAlpha = label.alpha * input.entrance
    haloText(
      context,
      label.text,
      label.x,
      label.y,
      label.fill,
      halo,
      label.halo
    )
  }
  context.letterSpacing = '0px'
  context.globalAlpha = 1
}

type LayoutCache = {
  signature: string
  view: MapView
  points: readonly PositionedPoint[]
  palette: LayerPalette | null
  anchors: readonly DomainAnchor[]
  tokens: ThemeColors
  layout: Layout
}

let layoutCache: LayoutCache | null = null

function signatureOf(input: SceneInput): string {
  const { transform, size, overlays, filter, drag } = input
  return [
    transform.k,
    transform.x,
    transform.y,
    size.width,
    size.height,
    input.mode,
    (Object.keys(overlays) as Overlay[])
      .map((key) => (overlays[key] ? key : ''))
      .join(','),
    [...filter.hiddenTypes].sort().join(','),
    filter.fallen,
    input.hoverKey,
    input.focusId,
    drag ? `${drag.key}:${drag.x}:${drag.y}` : '',
    input.past,
    input.noteMode,
  ].join('|')
}

function layoutOf(
  context: CanvasRenderingContext2D,
  input: SceneInput
): Layout {
  const signature = signatureOf(input)
  const cache = layoutCache
  if (
    cache &&
    cache.signature === signature &&
    cache.view === input.view &&
    cache.points === input.points &&
    cache.palette === input.palette &&
    cache.anchors === input.anchors &&
    cache.tokens === input.tokens
  )
    return cache.layout
  const layout = computeLayout(input, context)
  layoutCache = {
    signature,
    view: input.view,
    points: input.points,
    palette: input.palette,
    anchors: input.anchors,
    tokens: input.tokens,
    layout,
  }
  return layout
}

function hoveredRegion(input: SceneInput): number | null {
  const key = input.hoverKey
  if (!key) return null
  const [kind, id] = key.split(':')
  return kind === 'region' || kind === 'area' ? Number(id) : null
}

export const drawScene: DrawScene = (context, input) => {
  const { view, transform, size, tokens, overlays } = input
  const palette = view.geometry.palette
  const fade = input.entrance
  const pixelRatio = context.getTransform().a
  const layout = layoutOf(context, input)
  context.save()
  context.fillStyle = palette.background
  context.fillRect(0, 0, size.width, size.height)
  context.setTransform(
    transform.k * pixelRatio,
    0,
    0,
    transform.k * pixelRatio,
    transform.x * pixelRatio,
    transform.y * pixelRatio
  )
  context.imageSmoothingEnabled = true
  context.imageSmoothingQuality = 'high'
  context.globalAlpha = fade
  if (input.terrain) drawTexture(context, view.geometry, input.terrain)
  if (input.tint) {
    drawTexture(context, view.geometry, input.tint.texture)
    if (input.tint.contested)
      drawContested(context, view, input.tint.contested, pixelRatio, size, fade)
  }
  drawBorders(context, view, transform.k, input.mode, fade)
  if (input.tint && input.mode !== 'regions')
    drawDomainBorder(context, view, input.tint, transform.k, fade)
  drawLines(context, view, tokens, transform, {
    roads: overlays.roads,
    ties: overlays.ties,
    time: input.time,
    animate: input.animate,
    fade,
  })
  if (overlays.fog && input.fog) {
    context.globalAlpha = fade
    drawTexture(context, view.geometry, input.fog)
  }
  const hovered = hoveredRegion(input)
  if (hovered !== null)
    drawOutline(
      context,
      regionOutline(view.geometry, hovered),
      palette.land_label,
      transform.k,
      fade
    )
  const focusRegion =
    input.focusId !== null &&
    view.geometry.regions.some((region) => region.id === input.focusId)
      ? input.focusId
      : null
  if (focusRegion !== null && focusRegion !== hovered)
    drawOutline(
      context,
      regionOutline(view.geometry, focusRegion),
      tokens['brand-verdigris'],
      transform.k,
      fade
    )
  context.restore()

  drawGrain(context, input)
  drawAmbient(context, input)
  if (overlays.fog) drawUnexplored(context, input)

  context.globalAlpha = fade
  drawStacks(context, input, layout)
  for (const marker of layout.markers) {
    context.globalAlpha = fade
    drawMarker(context, input, marker)
  }
  context.globalAlpha = fade
  for (const note of layout.notes) {
    context.save()
    context.translate(note.x, note.y)
    pinGlyph(
      context,
      tokens[NOTE_TOKEN[noteColor(note.note)]] as string,
      palette.background
    )
    context.restore()
  }
  drawLabels(context, input, layout)

  if (input.focusId !== null && focusRegion === null) {
    const site = locate(input, input.focusId)
    if (site) {
      const screen = toScreen(transform, site.x, site.y)
      const elapsed = input.time - input.focusStartedAt
      const pulses = input.animate && elapsed < FOCUS_PULSE_MS * FOCUS_PULSES
      const phase = pulses ? (elapsed % FOCUS_PULSE_MS) / FOCUS_PULSE_MS : 0.4
      context.globalAlpha = pulses ? 1 - phase : 0.9
      context.beginPath()
      context.arc(screen.x, screen.y, 14 + phase * 18, 0, TAU)
      context.strokeStyle = tokens['brand-verdigris']
      context.lineWidth = 2.5
      context.stroke()
      context.globalAlpha = 1
    }
  }

  drawVignette(context, input)
  drawLeak(context, input)
  context.globalAlpha = 1
  return layout.hits
}

export function hitAt(
  hits: readonly HitTarget[],
  x: number,
  y: number
): HitTarget | null {
  for (let index = hits.length - 1; index >= 0; index -= 1) {
    const hit = hits[index]
    if (hit.path) {
      if (nearLine(hit.path, x, y)) return hit
      continue
    }
    if (hit.box) {
      if (
        x >= hit.box.left &&
        x <= hit.box.right &&
        y >= hit.box.top &&
        y <= hit.box.bottom
      )
        return hit
      continue
    }
    if ((hit.x - x) ** 2 + (hit.y - y) ** 2 <= hit.radius ** 2) return hit
  }
  return null
}
