import { type WorldMap } from './api'
import { domainEdges } from './mapEdges'
import { cellPolygon, tracePolygon } from './mapModel'
import { type LayerPalette } from './useLayerPalette'

const MAX_TEXTURE = 4096
const MAX_SCALE = 4
const SEAM_WIDTH = 0.6
const WAVE_WIDTHS = [26, 17, 10, 5] as const
const WAVE_ALPHAS = [0.05, 0.07, 0.1, 0.14] as const
const HACHURE_MIN = 0.55
const HACHURE_ALPHA = 0.55
const HACHURE_WIDTH = 0.8
const HACHURE_BASE = 3
const HACHURE_GAIN = 3
const KNOWN_FOG = 2
const UNKNOWN = 0
const LIGHT = 'white'
const DARK = 'black'
const FOG_SCALE = 0.07
const FOG_EDGE_ALPHA = 0.55
const FOG_BLUR_PX = 3
const MIST_BLOBS = 160
const MIST_MIN = 30
const MIST_SPAN = 140
const MIST_ALPHA = 0.07
const SHADOW_ALPHA = 0.25
const BAND_GAIN = 1.9
const BAND_MAX_ALPHA = 0.85

export type MapTexture = {
  canvas: HTMLCanvasElement
  scale: number
}

export function texture(map: WorldMap): {
  canvas: HTMLCanvasElement
  context: CanvasRenderingContext2D
  scale: number
} | null {
  const window = map.window
  const scale = Math.min(
    MAX_SCALE,
    MAX_TEXTURE / Math.max(window.width, window.height, 1)
  )
  const canvas = document.createElement('canvas')
  canvas.width = Math.max(1, Math.ceil(window.width * scale))
  canvas.height = Math.max(1, Math.ceil(window.height * scale))
  const context = canvas.getContext('2d')
  if (!context) return null
  context.setTransform(scale, 0, 0, scale, -window.x * scale, -window.y * scale)
  return { canvas, context, scale }
}

export function fillCell(
  context: CanvasRenderingContext2D,
  map: WorldMap,
  index: number,
  color: string,
  seam = true
): void {
  context.beginPath()
  tracePolygon(context, cellPolygon(map, index))
  context.fillStyle = color
  context.fill()
  if (seam) {
    context.strokeStyle = color
    context.lineWidth = SEAM_WIDTH
    context.stroke()
  }
}

function cellColor(map: WorldMap, index: number, fog: boolean): string {
  const cells = map.cells
  const palette = map.palette
  if (fog && cells.known[index] === UNKNOWN)
    return cells.water[index] ? palette.unknown_water : palette.unknown_land
  if (cells.water[index] && cells.coastal[index]) return palette.coastal_water
  return (
    palette.terrain_colours[cells.biome[index]] ??
    palette.terrain_colours.at(-1) ??
    palette.background
  )
}

export function coastPath(map: WorldMap): Path2D {
  const path = new Path2D()
  const coordinates = map.borders.coordinates
  map.borders.kinds.forEach((kind, index) => {
    if (kind !== 'coast') return
    const offset = index * 4
    path.moveTo(coordinates[offset], coordinates[offset + 1])
    path.lineTo(coordinates[offset + 2], coordinates[offset + 3])
  })
  return path
}

export function buildTerrain(map: WorldMap, fog = true): MapTexture | null {
  const made = texture(map)
  if (!made) return null
  const { canvas, context, scale } = made
  const cells = map.cells
  context.fillStyle = map.palette.background
  context.fillRect(
    map.window.x,
    map.window.y,
    map.window.width,
    map.window.height
  )
  const land: number[] = []
  for (let index = 0; index < cells.x.length; index += 1) {
    const seen = !fog || cells.known[index] !== UNKNOWN
    if (seen && !cells.water[index]) land.push(index)
    else fillCell(context, map, index, cellColor(map, index, fog))
  }
  const coast = coastPath(map)
  context.lineCap = 'round'
  WAVE_WIDTHS.forEach((width, step) => {
    context.globalAlpha = WAVE_ALPHAS[step]
    context.strokeStyle = map.palette.water_label
    context.lineWidth = width
    context.stroke(coast)
  })
  context.globalAlpha = 1
  for (const index of land) {
    fillCell(context, map, index, cellColor(map, index, fog))
    const shade = cells.shade[index] ?? 0
    if (shade !== 0) {
      context.globalAlpha = Math.abs(shade)
      fillCell(context, map, index, shade > 0 ? LIGHT : DARK, false)
      context.globalAlpha = 1
    }
  }
  context.globalAlpha = HACHURE_ALPHA
  context.strokeStyle = DARK
  context.lineWidth = HACHURE_WIDTH
  context.beginPath()
  for (const index of land) {
    const elevation = cells.elevation[index]
    if (elevation < HACHURE_MIN) continue
    const height = HACHURE_BASE + HACHURE_GAIN * elevation
    const x = cells.x[index]
    const y = cells.y[index]
    context.moveTo(x - height * 0.7, y + height * 0.4)
    context.lineTo(x, y - height * 0.6)
    context.lineTo(x + height * 0.7, y + height * 0.4)
  }
  context.stroke()
  context.globalAlpha = 1
  return { canvas, scale }
}

export function seeded(seed: string): () => number {
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

function lowTexture(map: WorldMap, scale: number) {
  const window = map.window
  const canvas = document.createElement('canvas')
  canvas.width = Math.max(1, Math.ceil(window.width * scale))
  canvas.height = Math.max(1, Math.ceil(window.height * scale))
  const context = canvas.getContext('2d')
  if (!context) return null
  context.setTransform(scale, 0, 0, scale, -window.x * scale, -window.y * scale)
  return { canvas, context }
}

export function buildFog(map: WorldMap): MapTexture | null {
  const mask = lowTexture(map, FOG_SCALE)
  if (!mask) return null
  const cells = map.cells
  const palette = map.palette
  for (let index = 0; index < cells.x.length; index += 1) {
    const known = cells.known[index]
    if (known !== UNKNOWN && known !== KNOWN_FOG) continue
    mask.context.globalAlpha = known === UNKNOWN ? 1 : FOG_EDGE_ALPHA
    fillCell(
      mask.context,
      map,
      index,
      cells.water[index] ? palette.unknown_water : palette.unknown_land
    )
  }
  mask.context.globalAlpha = 1
  mask.context.globalCompositeOperation = 'source-atop'
  const random = seeded(`${map.seed}:fog`)
  const window = map.window
  for (let blob = 0; blob < MIST_BLOBS; blob += 1) {
    const x = window.x + random() * window.width
    const y = window.y + random() * window.height
    const radius = MIST_MIN + random() * MIST_SPAN
    const light = random() > 0.35
    const gradient = mask.context.createRadialGradient(x, y, 0, x, y, radius)
    gradient.addColorStop(0, light ? palette.land_label : DARK)
    gradient.addColorStop(1, 'transparent')
    mask.context.globalAlpha = light ? MIST_ALPHA : SHADOW_ALPHA
    mask.context.fillStyle = gradient
    mask.context.fillRect(x - radius, y - radius, radius * 2, radius * 2)
  }
  mask.context.globalAlpha = 1
  mask.context.globalCompositeOperation = 'source-over'
  const soft = document.createElement('canvas')
  soft.width = mask.canvas.width
  soft.height = mask.canvas.height
  const softContext = soft.getContext('2d')
  if (!softContext) return { canvas: mask.canvas, scale: FOG_SCALE }
  if ('filter' in softContext) softContext.filter = `blur(${FOG_BLUR_PX}px)`
  softContext.drawImage(mask.canvas, 0, 0)
  return { canvas: soft, scale: FOG_SCALE }
}

export type TintLayer = {
  texture: MapTexture
  border: Path2D
  contested: Path2D | null
}

export function buildTint(
  map: WorldMap,
  palette: LayerPalette
): TintLayer | null {
  if (palette.tints.size === 0) return null
  const made = texture(map)
  if (!made) return null
  const { canvas, context, scale } = made
  const cells = map.cells
  const { border, band } = domainEdges(map, palette.cellKey)
  const banded = palette.mode !== 'regions'
  for (let index = 0; index < cells.x.length; index += 1) {
    const key = palette.cellKey(index)
    if (key === null) continue
    const region = cells.region[index]
    const tint = region === null ? undefined : palette.tints.get(region)
    if (!tint) continue
    context.globalAlpha =
      banded && band.has(index)
        ? Math.min(BAND_MAX_ALPHA, tint.alpha * BAND_GAIN)
        : tint.alpha
    fillCell(context, map, index, palette.colorOf(key))
  }
  const contested = palette.contested.size > 0 ? new Path2D() : null
  for (let index = 0; contested && index < cells.x.length; index += 1) {
    if (palette.cellKey(index) === null) continue
    const region = cells.region[index]
    const top = cells.top_region[index]
    if (
      (region !== null && palette.contested.has(region)) ||
      (top !== null && palette.contested.has(top))
    )
      tracePolygon(contested, cellPolygon(map, index))
  }
  context.globalAlpha = 1
  return { texture: { canvas, scale }, border, contested }
}

export function drawTexture(
  context: CanvasRenderingContext2D,
  map: WorldMap,
  layer: MapTexture
): void {
  context.drawImage(
    layer.canvas,
    map.window.x,
    map.window.y,
    layer.canvas.width / layer.scale,
    layer.canvas.height / layer.scale
  )
}
