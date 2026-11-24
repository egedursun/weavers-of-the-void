import { type ThemeColors, toHex } from '@/components/domain/useThemeColors'
import { type MapView, type WorldMap } from './api'
import {
  type DeepPattern,
  PASSAGE_GLYPH,
  PASSAGE_LOOK,
  type PassageState,
  ROCK_GRAIN_TOKEN,
  ROCK_SEAM_TOKEN,
  ROCK_TOKEN,
  SEABED_TOKEN,
  STRATUM_LOOK,
  type ShaftGlyph,
  type StratumLook,
} from './deepLooks'
import { cellEdges } from './mapEdges'
import { cellPolygon, tracePolygon } from './mapModel'
import {
  type MapTexture,
  coastPath,
  fillCell,
  seeded,
  texture,
} from './terrainLayer'

type DeepCell = NonNullable<MapView['level']>['cells'][number]

export type Hollow = {
  cell: DeepCell
  members: number[]
  x: number
  y: number
  radius: number
}

const NO_CELL = -1
const LIGHT = 'white'
const DARK = 'black'
const FULL = 100
const EXTENT_RAGGED = 0.22
const ROCK_JITTER = 0.08
const INNER_SHADOW_STEPS = 5
const INNER_SHADOW_ALPHA = 0.11
const SEABED_ALPHA = 0.16
const GRAIN_PER_CELL = 3
const GRAIN_ALPHA = 0.2
const SEAM_STEP = 1.6
const SEAM_ALPHA = 0.12
const SEAM_WAVE = 0.35
const GLOW_BASE = 0.12
const GLOW_GAIN = 0.55
const RIM_SHADOW = 0.6
const RIM_LINE = 0.13
const RIM_SHADOW_ALPHA = 0.6
const GHOST_ALPHA = 0.3
const GHOST_WIDTH = 0.07
const TAU = Math.PI * 2

export function unitOf(map: WorldMap): number {
  const window = map.window
  return Math.sqrt(
    (window.width * window.height) / Math.max(1, map.cells.x.length)
  )
}

function ownerCell(
  map: WorldMap,
  index: number,
  byRegion: ReadonlyMap<number, DeepCell>
): DeepCell | undefined {
  const region = map.cells.region[index]
  const top = map.cells.top_region[index]
  return (
    (region !== null ? byRegion.get(region) : undefined) ??
    (top !== null ? byRegion.get(top) : undefined)
  )
}

export function hollowsOf(view: MapView): Hollow[] {
  const level = view.level
  if (!level) return []
  const map = view.geometry
  const byRegion = new Map(level.cells.map((cell) => [cell.region_id, cell]))
  const members = new Map<number, number[]>()
  for (let index = 0; index < map.cells.x.length; index += 1) {
    const cell = ownerCell(map, index, byRegion)
    if (!cell) continue
    const list = members.get(cell.cell_id) ?? []
    list.push(index)
    members.set(cell.cell_id, list)
  }
  const unit = unitOf(map)
  return level.cells.flatMap((cell): Hollow[] => {
    const all = members.get(cell.cell_id) ?? []
    if (all.length === 0) return []
    const x =
      all.reduce((sum, index) => sum + map.cells.x[index], 0) / all.length
    const y =
      all.reduce((sum, index) => sum + map.cells.y[index], 0) / all.length
    const random = seeded(`${map.seed}:extent:${cell.cell_id}`)
    const phases = [random() * TAU, random() * TAU]
    const reach = new Map(
      all.map((index) => {
        const dx = map.cells.x[index] - x
        const dy = map.cells.y[index] - y
        const angle = Math.atan2(dy, dx)
        const wobble =
          EXTENT_RAGGED * Math.sin(3 * angle + phases[0]) +
          EXTENT_RAGGED * 0.5 * Math.sin(5 * angle + phases[1])
        return [index, Math.hypot(dx, dy) * (1 + wobble)]
      })
    )
    const near = [...all].sort(
      (left, right) => (reach.get(left) ?? 0) - (reach.get(right) ?? 0)
    )
    const kept = near.slice(
      0,
      Math.max(1, Math.round((near.length * cell.extent) / FULL))
    )
    return [
      {
        cell,
        members: kept,
        x,
        y,
        radius: Math.sqrt(kept.length) * unit * 0.75,
      },
    ]
  })
}

function hollowPath(map: WorldMap, hollow: Hollow): Path2D {
  const path = new Path2D()
  for (const index of hollow.members)
    tracePolygon(path, cellPolygon(map, index))
  return path
}

function rimPath(map: WorldMap, hollowCells: ReadonlySet<number>): Path2D {
  const edges = cellEdges(map)
  const path = new Path2D()
  for (let edge = 0; edge < edges.first.length; edge += 1) {
    const first = edges.first[edge]
    const second = edges.second[edge]
    const inside = hollowCells.has(first)
    const outside = second === NO_CELL ? false : hollowCells.has(second)
    if (inside === outside) continue
    const offset = edge * 4
    path.moveTo(edges.coordinates[offset], edges.coordinates[offset + 1])
    path.lineTo(edges.coordinates[offset + 2], edges.coordinates[offset + 3])
  }
  return path
}

function drawRock(
  context: CanvasRenderingContext2D,
  map: WorldMap,
  tokens: ThemeColors,
  unit: number
): void {
  const random = seeded(`${map.seed}:rock`)
  for (let index = 0; index < map.cells.x.length; index += 1) {
    fillCell(context, map, index, tokens[ROCK_TOKEN])
    const jitter = (random() - 0.5) * 2 * ROCK_JITTER
    context.globalAlpha = Math.abs(jitter)
    fillCell(context, map, index, jitter > 0 ? LIGHT : DARK, false)
    context.globalAlpha = 1
    if (map.cells.water[index]) {
      context.globalAlpha = SEABED_ALPHA
      fillCell(context, map, index, tokens[SEABED_TOKEN], false)
      context.globalAlpha = 1
    }
  }
  const window = map.window
  context.fillStyle = tokens[ROCK_GRAIN_TOKEN]
  context.globalAlpha = GRAIN_ALPHA
  for (let grain = 0; grain < map.cells.x.length * GRAIN_PER_CELL; grain += 1) {
    const x = window.x + random() * window.width
    const y = window.y + random() * window.height
    context.beginPath()
    context.arc(x, y, unit * (0.03 + random() * 0.08), 0, TAU)
    context.fill()
  }
  context.strokeStyle = tokens[ROCK_SEAM_TOKEN]
  context.globalAlpha = SEAM_ALPHA
  context.lineWidth = unit * 0.05
  for (
    let row = window.y + unit;
    row < window.y + window.height;
    row += unit * SEAM_STEP
  ) {
    const phase = random() * TAU
    context.beginPath()
    for (let x = window.x; x <= window.x + window.width; x += unit * 0.5) {
      const y = row + Math.sin(x / (unit * 3) + phase) * unit * SEAM_WAVE
      if (x === window.x) context.moveTo(x, y)
      else context.lineTo(x, y)
    }
    context.stroke()
  }
  context.globalAlpha = 1
}

type PatternInput = {
  context: CanvasRenderingContext2D
  hollow: Hollow
  look: StratumLook
  tokens: ThemeColors
  unit: number
  random: () => number
}

function spot(input: PatternInput): { x: number; y: number } {
  const angle = input.random() * TAU
  const distance = Math.sqrt(input.random()) * input.hollow.radius
  return {
    x: input.hollow.x + Math.cos(angle) * distance,
    y: input.hollow.y + Math.sin(angle) * distance,
  }
}

function count(input: PatternInput, per: number): number {
  return Math.max(3, Math.round(input.hollow.members.length * per))
}

const PATTERNS: Record<DeepPattern, (input: PatternInput) => void> = {
  frost: (input) => {
    const { context, unit } = input
    context.globalAlpha = 0.35
    context.fillStyle = input.tokens[input.look.glow]
    context.fillRect(
      input.hollow.x - input.hollow.radius * 2,
      input.hollow.y - input.hollow.radius * 2,
      input.hollow.radius * 4,
      input.hollow.radius * 4
    )
    context.strokeStyle = LIGHT
    context.globalAlpha = 0.7
    context.lineWidth = unit * 0.06
    for (let crystal = 0; crystal < count(input, 0.45); crystal += 1) {
      const centre = spot(input)
      const size = unit * (0.35 + input.random() * 0.45)
      for (let arm = 0; arm < 3; arm += 1) {
        const angle = (arm * Math.PI) / 3
        context.beginPath()
        context.moveTo(
          centre.x - Math.cos(angle) * size,
          centre.y - Math.sin(angle) * size
        )
        context.lineTo(
          centre.x + Math.cos(angle) * size,
          centre.y + Math.sin(angle) * size
        )
        context.stroke()
      }
    }
  },
  ripples: (input) => {
    const { context, hollow, unit, tokens, look } = input
    const wells = Math.max(
      2,
      Math.min(5, Math.round(hollow.members.length / 12))
    )
    for (let well = 0; well < wells; well += 1) {
      const centre = spot(input)
      const reach = hollow.radius * (0.35 + input.random() * 0.25)
      for (let ring = 1; ring <= 4; ring += 1) {
        const radius = (reach * ring) / 4
        context.globalAlpha = 0.9 - ring * 0.17
        context.strokeStyle = ring % 2 === 0 ? LIGHT : tokens[look.glow]
        context.lineWidth = Math.max(unit * 0.12, radius * 0.06)
        context.beginPath()
        context.arc(centre.x, centre.y, radius, 0, TAU)
        context.stroke()
      }
    }
  },
  abyss: (input) => {
    const { context, hollow, unit, tokens, look } = input
    const gradient = context.createRadialGradient(
      hollow.x,
      hollow.y,
      0,
      hollow.x,
      hollow.y,
      hollow.radius
    )
    gradient.addColorStop(0, DARK)
    gradient.addColorStop(1, 'transparent')
    context.globalAlpha = 0.3
    context.fillStyle = gradient
    context.fillRect(
      hollow.x - hollow.radius,
      hollow.y - hollow.radius,
      hollow.radius * 2,
      hollow.radius * 2
    )
    context.fillStyle = tokens[look.glow]
    const bubble = Math.max(unit * 0.08, hollow.radius * 0.025)
    context.strokeStyle = tokens[look.glow]
    context.lineWidth = Math.max(unit * 0.07, hollow.radius * 0.02)
    for (let wave = 0; wave < 5; wave += 1) {
      const row = hollow.y + (wave - 2) * hollow.radius * 0.32
      context.globalAlpha = 0.5
      context.beginPath()
      for (let step = -10; step <= 10; step += 1) {
        const x = hollow.x + (step / 10) * hollow.radius
        const y = row + Math.sin(step * 0.9 + wave) * hollow.radius * 0.05
        if (step === -10) context.moveTo(x, y)
        else context.lineTo(x, y)
      }
      context.stroke()
    }
    for (let index = 0; index < count(input, 0.3); index += 1) {
      const centre = spot(input)
      context.globalAlpha = 0.45 + input.random() * 0.35
      context.beginPath()
      context.arc(centre.x, centre.y, bubble * (0.6 + input.random()), 0, TAU)
      context.fill()
    }
  },
  sheen: (input) => {
    const { context, hollow, unit, tokens, look } = input
    const span = hollow.radius
    const pool = context.createLinearGradient(
      hollow.x,
      hollow.y - span,
      hollow.x,
      hollow.y + span
    )
    pool.addColorStop(0, 'transparent')
    pool.addColorStop(0.45, 'transparent')
    pool.addColorStop(1, DARK)
    context.globalAlpha = 0.55
    context.fillStyle = pool
    context.fillRect(hollow.x - span, hollow.y - span, span * 2, span * 2)
    context.globalAlpha = 0.85
    context.strokeStyle = DARK
    context.lineWidth = Math.max(unit * 0.22, span * 0.09)
    context.beginPath()
    context.ellipse(
      hollow.x,
      hollow.y + span * 0.2,
      span * 0.8,
      span * 0.55,
      0,
      Math.PI * 1.08,
      Math.PI * 1.92
    )
    context.stroke()
    context.globalAlpha = 0.7
    context.strokeStyle = tokens[look.glow]
    context.lineWidth = Math.max(unit * 0.06, span * 0.018)
    context.stroke()
    context.fillStyle = tokens[look.glow]
    const bead = Math.max(unit * 0.07, span * 0.02)
    for (let index = 0; index < count(input, 0.8); index += 1) {
      const centre = spot(input)
      if (centre.y < hollow.y - span * 0.15) continue
      context.globalAlpha = 0.35 + input.random() * 0.35
      context.beginPath()
      context.arc(centre.x, centre.y, bead * (0.5 + input.random()), 0, TAU)
      context.fill()
    }
  },
  drips: (input) => {
    const { context, unit, tokens, look } = input
    for (let drip = 0; drip < count(input, 0.6); drip += 1) {
      const centre = spot(input)
      context.globalAlpha = 0.55
      context.fillStyle = DARK
      context.beginPath()
      context.ellipse(centre.x, centre.y, unit * 0.16, unit * 0.42, 0, 0, TAU)
      context.fill()
      context.globalAlpha = 0.65
      context.fillStyle = tokens[look.glow]
      context.beginPath()
      context.arc(centre.x, centre.y + unit * 0.46, unit * 0.09, 0, TAU)
      context.fill()
    }
  },
  columns: (input) => {
    const { context, unit, tokens, look } = input
    for (let pillar = 0; pillar < count(input, 0.45); pillar += 1) {
      const centre = spot(input)
      const size = unit * (0.18 + input.random() * 0.16)
      context.globalAlpha = 0.6
      context.fillStyle = DARK
      context.beginPath()
      context.arc(centre.x + size * 0.3, centre.y + size * 0.3, size, 0, TAU)
      context.fill()
      context.globalAlpha = 0.85
      context.fillStyle = tokens[look.glow]
      context.beginPath()
      context.arc(centre.x, centre.y, size, 0, TAU)
      context.fill()
    }
  },
  roots: (input) => {
    const { context, hollow, unit, tokens, look } = input
    const step = Math.max(unit * 0.3, hollow.radius * 0.12)
    for (let root = 0; root < 7; root += 1) {
      let point = spot(input)
      let angle = input.random() * TAU
      context.globalAlpha = 1
      context.strokeStyle = tokens[look.glow]
      context.lineWidth = Math.max(unit * 0.12, hollow.radius * 0.035)
      context.beginPath()
      context.moveTo(point.x, point.y)
      for (let segment = 0; segment < 6; segment += 1) {
        angle += (input.random() - 0.5) * 1.2
        point = {
          x: point.x + Math.cos(angle) * step,
          y: point.y + Math.sin(angle) * step,
        }
        context.lineTo(point.x, point.y)
      }
      context.stroke()
    }
  },
  cracks: (input) => {
    const { context, hollow, unit, tokens, look } = input
    const step = Math.max(unit * 0.32, hollow.radius * 0.14)
    for (let crack = 0; crack < 5; crack += 1) {
      const start = spot(input)
      const angle = input.random() * TAU
      const points: { x: number; y: number }[] = [start]
      for (let segment = 1; segment <= 6; segment += 1) {
        const side = segment % 2 === 0 ? 1 : -1
        points.push({
          x:
            start.x +
            Math.cos(angle) * step * segment +
            Math.cos(angle + Math.PI / 2) * step * 0.35 * side,
          y:
            start.y +
            Math.sin(angle) * step * segment +
            Math.sin(angle + Math.PI / 2) * step * 0.35 * side,
        })
      }
      for (const [width, alpha] of [
        [0.5, 0.3],
        [0.14, 1],
      ] as const) {
        context.strokeStyle = tokens[look.glow]
        context.lineWidth = step * width
        context.globalAlpha = alpha
        context.beginPath()
        points.forEach((point, index) =>
          index === 0
            ? context.moveTo(point.x, point.y)
            : context.lineTo(point.x, point.y)
        )
        context.stroke()
      }
    }
  },
  radiance: (input) => {
    const { context, hollow, unit, tokens, look } = input
    const gradient = context.createRadialGradient(
      hollow.x,
      hollow.y,
      0,
      hollow.x,
      hollow.y,
      hollow.radius * 1.2
    )
    gradient.addColorStop(0, tokens[look.glow])
    gradient.addColorStop(0.6, 'transparent')
    context.globalAlpha = 0.45
    context.fillStyle = gradient
    context.fillRect(
      hollow.x - hollow.radius * 1.2,
      hollow.y - hollow.radius * 1.2,
      hollow.radius * 2.4,
      hollow.radius * 2.4
    )
    context.strokeStyle = LIGHT
    context.lineWidth = unit * 0.04
    context.globalAlpha = 0.35
    for (let ray = 0; ray < 12; ray += 1) {
      const angle = (ray / 12) * TAU
      context.beginPath()
      context.moveTo(
        hollow.x + Math.cos(angle) * unit * 0.3,
        hollow.y + Math.sin(angle) * unit * 0.3
      )
      context.lineTo(
        hollow.x + Math.cos(angle) * hollow.radius,
        hollow.y + Math.sin(angle) * hollow.radius
      )
      context.stroke()
    }
  },
  embers: (input) => {
    const { context, unit, tokens, look } = input
    for (let ember = 0; ember < count(input, 0.6); ember += 1) {
      const centre = spot(input)
      const size = unit * (0.3 + input.random() * 0.45)
      const gradient = context.createRadialGradient(
        centre.x,
        centre.y,
        0,
        centre.x,
        centre.y,
        size
      )
      gradient.addColorStop(0, LIGHT)
      gradient.addColorStop(0.35, tokens[look.glow])
      gradient.addColorStop(1, 'transparent')
      context.globalAlpha = 0.75
      context.fillStyle = gradient
      context.fillRect(centre.x - size, centre.y - size, size * 2, size * 2)
    }
  },
  mist: (input) => {
    const { context, hollow, unit, tokens, look } = input
    const size = Math.max(unit * 0.2, hollow.radius * 0.12)
    context.strokeStyle = tokens[look.glow]
    for (let swirl = 0; swirl < 6; swirl += 1) {
      const centre = spot(input)
      const start = input.random() * TAU
      context.globalAlpha = 0.55 + input.random() * 0.3
      context.lineWidth = size * 0.18
      for (let turn = 1; turn <= 3; turn += 1) {
        context.beginPath()
        context.arc(
          centre.x,
          centre.y,
          size * turn * 0.6,
          start + turn,
          start + turn + Math.PI * 1.2
        )
        context.stroke()
      }
    }
  },
}

type Rgb = [number, number, number]

const BLACK: Rgb = [0, 0, 0]
const WHITE: Rgb = [255, 255, 255]
const GREY: Rgb = [128, 128, 128]
const MUTE = 0.42
const DIM = 0.82

function rgbOf(color: string): Rgb {
  const hex = toHex(color).replace('#', '')
  if (hex.length >= 6)
    return [0, 2, 4].map((at) => parseInt(hex.slice(at, at + 2), 16)) as Rgb
  return GREY
}

function blend(from: Rgb, to: Rgb, share: number): Rgb {
  const clamped = Math.max(0, Math.min(1, share))
  return from.map((value, index) =>
    Math.round(value + (to[index] - value) * clamped)
  ) as Rgb
}

function muted(color: Rgb): Rgb {
  const grey = (color[0] + color[1] + color[2]) / 3
  return color.map((value) =>
    Math.round((value + (grey - value) * MUTE) * DIM)
  ) as Rgb
}

function mix(from: Rgb, to: Rgb, share: number): string {
  const [red, green, blue] = muted(blend(from, to, share))
  return `#${[red, green, blue].map((value) => value.toString(16).padStart(2, '0')).join('')}`
}

const neighbourCache = new WeakMap<WorldMap, number[][]>()

function neighboursOf(map: WorldMap): number[][] {
  const cached = neighbourCache.get(map)
  if (cached) return cached
  const edges = cellEdges(map)
  const found: number[][] = map.cells.x.map(() => [])
  for (let edge = 0; edge < edges.first.length; edge += 1) {
    const first = edges.first[edge]
    const second = edges.second[edge]
    if (second === NO_CELL) continue
    found[first].push(second)
    found[second].push(first)
  }
  neighbourCache.set(map, found)
  return found
}

function depthFromRim(
  map: WorldMap,
  members: readonly number[]
): Map<number, number> {
  const inside = new Set(members)
  const near = neighboursOf(map)
  const depth = new Map<number, number>()
  let frontier = members.filter((index) =>
    near[index].some((other) => !inside.has(other))
  )
  if (frontier.length === 0) frontier = [...members]
  frontier.forEach((index) => depth.set(index, 0))
  let level = 0
  while (frontier.length > 0) {
    level += 1
    const next: number[] = []
    for (const index of frontier)
      for (const other of near[index])
        if (inside.has(other) && !depth.has(other)) {
          depth.set(other, level)
          next.push(other)
        }
    frontier = next
  }
  const deepest = Math.max(1, ...depth.values())
  return new Map([...depth].map(([index, value]) => [index, value / deepest]))
}

function smoothNoise(
  map: WorldMap,
  members: readonly number[],
  seed: string
): Map<number, number> {
  const random = seeded(seed)
  const inside = new Set(members)
  const near = neighboursOf(map)
  let noise = new Map(members.map((index) => [index, random() * 2 - 1]))
  for (let pass = 0; pass < 2; pass += 1) {
    noise = new Map(
      members.map((index) => {
        const around = near[index].filter((other) => inside.has(other))
        const total = around.reduce(
          (sum, other) => sum + (noise.get(other) ?? 0),
          noise.get(index) ?? 0
        )
        return [index, total / (around.length + 1)]
      })
    )
  }
  const spread = Math.max(0.0001, ...[...noise.values()].map(Math.abs))
  return new Map([...noise].map(([index, value]) => [index, value / spread]))
}

function paintHollow(
  context: CanvasRenderingContext2D,
  map: WorldMap,
  hollow: Hollow,
  look: StratumLook,
  tokens: ThemeColors
): void {
  const depth = depthFromRim(map, hollow.members)
  const noise = smoothNoise(
    map,
    hollow.members,
    `${map.seed}:floor:${hollow.cell.cell_id}`
  )
  const fill = rgbOf(tokens[look.fill])
  const glow = rgbOf(tokens[look.glow])
  const black = BLACK
  const white = WHITE
  const darkRgb = blend(black, fill, 0.35)
  const lit = hollow.cell.light / FULL
  for (const index of hollow.members) {
    const inward = depth.get(index) ?? 0
    const grain = noise.get(index) ?? 0
    const relief = map.cells.shade[index] ?? 0
    let color: string
    if (look.surface === 'molten') {
      const heat = grain * 0.6 + inward * 0.7 - 0.15
      color =
        heat > 0 ? mix(glow, white, heat * 0.6) : mix(black, fill, 0.45 + heat)
    } else if (look.surface === 'water') {
      color = mix(
        glow,
        black,
        0.15 + inward * 0.55 - grain * 0.08 - relief * 0.4
      )
    } else {
      const value =
        0.42 + grain * 0.22 + relief * 1.4 + inward * 0.12 + lit * 0.25
      color =
        value > 0.5
          ? mix(fill, glow, (value - 0.5) * 1.6)
          : mix(darkRgb, fill, value * 2)
    }
    fillCell(context, map, index, color)
  }
  context.globalAlpha = 1
}

export function buildDeep(
  view: MapView,
  tokens: ThemeColors
): MapTexture | null {
  const level = view.level
  if (!level) return null
  const map = view.geometry
  const made = texture(map)
  if (!made) return null
  const { canvas, context, scale } = made
  const unit = unitOf(map)
  const look = STRATUM_LOOK[level.stratum]
  context.fillStyle = tokens[ROCK_TOKEN]
  context.fillRect(
    map.window.x,
    map.window.y,
    map.window.width,
    map.window.height
  )
  drawRock(context, map, tokens, unit)
  const hollows = hollowsOf(view)
  const hollowCells = new Set(hollows.flatMap((hollow) => hollow.members))
  for (const hollow of hollows) {
    const path = hollowPath(map, hollow)
    context.save()
    context.clip(path)
    paintHollow(context, map, hollow, look, tokens)
    if (look.pattern === 'cracks')
      PATTERNS.cracks({
        context,
        hollow,
        look,
        tokens,
        unit,
        random: seeded(`${map.seed}:${hollow.cell.cell_id}`),
      })
    const glow = context.createRadialGradient(
      hollow.x,
      hollow.y,
      0,
      hollow.x,
      hollow.y,
      hollow.radius * 1.3
    )
    glow.addColorStop(0, tokens[look.glow])
    glow.addColorStop(1, 'transparent')
    context.globalAlpha = GLOW_BASE + (hollow.cell.light / FULL) * GLOW_GAIN
    context.fillStyle = glow
    context.fill(path)
    const edge = rimPath(map, new Set(hollow.members))
    context.strokeStyle = DARK
    context.lineJoin = 'round'
    for (let step = INNER_SHADOW_STEPS; step >= 1; step -= 1) {
      context.globalAlpha = INNER_SHADOW_ALPHA
      context.lineWidth = unit * 0.45 * step
      context.stroke(edge)
    }
    context.restore()
  }
  const rim = rimPath(map, hollowCells)
  context.lineJoin = 'round'
  context.lineCap = 'round'
  context.globalAlpha = RIM_SHADOW_ALPHA
  context.strokeStyle = DARK
  context.lineWidth = unit * RIM_SHADOW
  context.stroke(rim)
  context.globalAlpha = 1
  context.strokeStyle = tokens[look.glow]
  context.lineWidth = unit * RIM_LINE
  context.stroke(rim)
  context.globalAlpha = GHOST_ALPHA
  context.strokeStyle = map.palette.land_label
  context.lineWidth = unit * GHOST_WIDTH
  context.setLineDash([unit * 0.4, unit * 0.3])
  context.stroke(coastPath(map))
  context.setLineDash([])
  context.globalAlpha = 1
  return { canvas, scale }
}

const SHAFT_PX = 9
const SHAFT_RING = 2.2
const SHAFT_STEP = 2.4

const centreCache = new WeakMap<
  WorldMap,
  Map<number, { x: number; y: number }>
>()

export function regionCentres(
  map: WorldMap
): Map<number, { x: number; y: number }> {
  const cached = centreCache.get(map)
  if (cached) return cached
  const sums = new Map<number, [number, number, number]>()
  for (let index = 0; index < map.cells.x.length; index += 1) {
    const region = map.cells.top_region[index]
    if (region === null) continue
    const total = sums.get(region) ?? [0, 0, 0]
    total[0] += map.cells.x[index]
    total[1] += map.cells.y[index]
    total[2] += 1
    sums.set(region, total)
  }
  const centres = new Map(
    [...sums.entries()].map(([region, [x, y, n]]) => [
      region,
      { x: x / n, y: y / n },
    ])
  )
  centreCache.set(map, centres)
  return centres
}

export type Shaft = {
  region: number
  glyph: ShaftGlyph
  state: PassageState
  up: boolean
}

export function shaftsOf(view: MapView): Shaft[] {
  if (view.level) {
    return view.level.passages
      .filter((passage) => PASSAGE_GLYPH[passage.kind] !== 'trail')
      .map((passage) => ({
        region: passage.first_region_id,
        glyph: PASSAGE_GLYPH[passage.kind],
        state: passage.state,
        up: passage.kind === 'opening',
      }))
  }
  return (view.deep?.openings ?? []).map((opening) => ({
    region: opening.region_id,
    glyph: 'mouth' as const,
    state: opening.state,
    up: false,
  }))
}

function chevron(
  context: CanvasRenderingContext2D,
  x: number,
  y: number,
  size: number,
  up: boolean
): void {
  const tip = up ? -size : size
  context.beginPath()
  context.moveTo(x - size, y - tip * 0.4)
  context.lineTo(x, y + tip * 0.5)
  context.lineTo(x + size, y - tip * 0.4)
  context.stroke()
}

export function drawShafts(
  context: CanvasRenderingContext2D,
  view: MapView,
  tokens: ThemeColors,
  k: number,
  fade: number
): void {
  const shafts = shaftsOf(view)
  if (shafts.length === 0) return
  const centres = regionCentres(view.geometry)
  const placed = new Map<number, number>()
  const size = SHAFT_PX / k
  context.save()
  context.lineJoin = 'round'
  context.lineCap = 'round'
  for (const shaft of shafts) {
    const centre = centres.get(shaft.region)
    if (!centre) continue
    const slot = placed.get(shaft.region) ?? 0
    placed.set(shaft.region, slot + 1)
    const x = centre.x + slot * size * SHAFT_STEP
    const y = centre.y - size * 1.6
    const color = tokens[PASSAGE_LOOK[shaft.state].token]
    context.globalAlpha = fade
    context.fillStyle = DARK
    context.strokeStyle = color
    context.lineWidth = SHAFT_RING / k
    context.beginPath()
    if (shaft.glyph === 'mouth') context.arc(x, y, size, 0, TAU)
    else context.roundRect(x - size, y - size, size * 2, size * 2, size * 0.35)
    context.fill()
    context.stroke()
    context.setLineDash(
      PASSAGE_LOOK[shaft.state].dash.map((value) => value / k)
    )
    context.lineWidth = (SHAFT_RING * 0.8) / k
    if (shaft.glyph === 'shaft') {
      context.setLineDash([])
      chevron(context, x, y - size * 0.35, size * 0.45, true)
      chevron(context, x, y + size * 0.35, size * 0.45, false)
    } else {
      context.setLineDash([])
      chevron(context, x, y, size * 0.5, shaft.up)
    }
  }
  context.restore()
}
