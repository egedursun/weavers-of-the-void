import { type LucideIcon } from 'lucide-react'
import { type ThemeColors } from '@/components/domain/useThemeColors'
import { familyOf } from '@/features/graph/families'
import { type MapNote, type MapView } from './api'
import {
  type Box,
  type LabelCandidate,
  boxAt,
  fitText,
  placeLabels,
  verticalShifts,
} from './labelLayout'
import { type DomainAnchor } from './mapEdges'
import {
  EVENT_RADIUS,
  NOTE_PIN,
  PORTRAIT_GAIN,
  RING_GAP,
  RING_WIDTH,
  type Slice,
  eventIcon,
  font,
  warIcon,
} from './mapGlyphs'
import { type LineInfo, lineHits } from './mapLines'
import {
  type LayerMode,
  type Overlay,
  type PositionedPoint,
  type SettlementTier,
  type Size,
  type Transform,
  LABELLED_TYPES,
  POWERFUL_LEVEL,
  SETTLEMENT_TIERS,
  TIER_RADIUS,
  isDead,
  markerRadius,
  regionLabelSize,
  relativeZoom,
  tierOf,
  toScreen,
} from './mapModel'
import { type LayerPalette } from './useLayerPalette'

export type HitKind = 'entity' | 'region' | 'war' | 'event' | 'note' | 'line'

export type HitTarget = {
  key: string
  kind: HitKind
  id: number
  x: number
  y: number
  radius: number
  box?: Box
  path?: readonly number[]
  members?: readonly number[]
  line?: LineInfo
  area?: boolean
  draggable: boolean
}

export type Thresholds = { town: number; city: number; greatCity: number }

export type MarkerFilter = {
  hiddenTypes: ReadonlySet<string>
  fallen: boolean
}

export type MarkerDraw = {
  key: string
  point: PositionedPoint
  x: number
  y: number
  radius: number
  tier: SettlementTier | null
  members: number[]
  slices: Slice[]
  crown: string | null
  portrait: boolean
}

export type StackDraw = {
  key: string
  kind: 'war' | 'event'
  x: number
  y: number
  ids: number[]
  count: number
  ongoing: boolean
  color: string
  icon: LucideIcon
  slices: Slice[]
}

export type GlowDraw = { x: number; y: number; radius: number; hot: boolean }

export type LabelDraw = {
  text: string
  x: number
  y: number
  font: string
  spacing: string
  fill: string
  halo: number
  alpha: number
}

export type NoteDraw = { note: MapNote; x: number; y: number }

export type Layout = {
  markers: MarkerDraw[]
  stacks: StackDraw[]
  glows: GlowDraw[]
  notes: NoteDraw[]
  labels: LabelDraw[]
  hits: HitTarget[]
}

export type LayoutInput = {
  view: MapView
  points: readonly PositionedPoint[]
  pointById: ReadonlyMap<number, PositionedPoint>
  size: Size
  transform: Transform
  fit: Transform
  tokens: ThemeColors
  palette: LayerPalette | null
  anchors: readonly DomainAnchor[]
  mode: LayerMode
  overlays: Record<Overlay, boolean>
  filter: MarkerFilter
  past: boolean
  noteMode: boolean
  thresholds: Thresholds
  hoverKey: string | null
  focusId: number | null
  drag: { key: string; x: number; y: number } | null
}

const CLUSTER_PX = 22
const CULL_PX = 40
const STACK_OFFSET = 13
const SETTLEMENT_ZOOM = 1.3
const ANY_LABEL_ZOOM = 1.6
const PORTRAIT_ZOOM = 2.6
const LABEL_GAP = 4
const MARKER_LABEL_SIZE = 10
const MARKER_LABEL_MAX = 200
const REGION_LABEL_MAX = 320
const REGION_LABEL_TRIES = 4
const DOMAIN_LABEL_TRIES = 6
const DOMAIN_MIN = 13
const DOMAIN_MAX = 26
const DOMAIN_BASE = 9
const DOMAIN_GAIN = 0.32
const DOMAIN_ZOOM_POWER = 0.3
const DOMAIN_ZOOM_MIN = 0.85
const DOMAIN_ZOOM_MAX = 1.6
const DOMAIN_HALO = 4.5
const GLOW_BASE = 16
const GLOW_GAIN = 6
const BATTLE_HEAT = 0.3
const TIER_LABEL_SIZE: Record<SettlementTier, number> = {
  village: 10,
  town: 11,
  city: 12.5,
  great_city: 14,
  capital: 14.5,
}
const TYPE_RANK: Record<string, number> = {
  settlement: 9,
  people: 8,
  faction: 7,
  place: 6,
  cult: 5,
  resource: 4,
  species: 3,
  item: 2,
  mortal: 1,
}
const ALIVE_RANK = 100000
const TYPE_WEIGHT = 1000
const TIER_WEIGHT = 100

export const EVENT_TOKEN: Record<string, keyof ThemeColors | null> = {
  battle: 'destructive',
  disaster: 'warning',
  ruin: null,
  remnant: 'chart-2',
  event: null,
}

export function eventColor(
  kind: string,
  tokens: ThemeColors,
  light: string
): string {
  const token = EVENT_TOKEN[kind]
  return token ? (tokens[token] as string) : light
}

export function locate(
  input: Pick<LayoutInput, 'pointById' | 'view'>,
  id: number | null | undefined
): { x: number; y: number } | null {
  if (id === null || id === undefined) return null
  const point = input.pointById.get(id)
  if (point) return point
  const region = input.view.geometry.regions.find((item) => item.id === id)
  const anchor = region?.anchor ?? region?.centroid
  return anchor ? { x: anchor[0], y: anchor[1] } : null
}

function priorityOf(
  point: PositionedPoint,
  tier: SettlementTier | null
): number {
  return (
    (isDead(point.status) ? 0 : ALIVE_RANK) +
    (TYPE_RANK[point.type] ?? 0) * TYPE_WEIGHT +
    (tier ? SETTLEMENT_TIERS.indexOf(tier) + 1 : 0) * TIER_WEIGHT +
    point.power
  )
}

function familyColor(type: string, tokens: ThemeColors): string {
  if (type === 'settlement') return tokens['brand-gold']
  return tokens[familyOf(type).token] as string
}

function slicesOf(counts: ReadonlyMap<string, number>): Slice[] {
  return [...counts.entries()]
    .sort((left, right) => right[1] - left[1])
    .map(([color, value]) => ({ color, value }))
}

function onScreen(x: number, y: number, size: Size): boolean {
  return (
    x >= -CULL_PX &&
    y >= -CULL_PX &&
    x <= size.width + CULL_PX &&
    y <= size.height + CULL_PX
  )
}

function stackedIds(view: MapView): Set<number> {
  return new Set([
    ...view.markers.map((marker) => marker.id),
    ...view.wars.map((war) => war.id),
  ])
}

function clusterMarkers(
  input: LayoutInput,
  dragOf: (key: string, x: number, y: number) => { x: number; y: number }
): MarkerDraw[] {
  const { view, transform, size, tokens, filter, palette } = input
  const relative = relativeZoom(transform, input.fit)
  const regionIds = new Set(view.geometry.regions.map((region) => region.id))
  const stacked = stackedIds(view)
  const candidates = input.points
    .filter(
      (point) =>
        !regionIds.has(point.id) &&
        !stacked.has(point.id) &&
        !filter.hiddenTypes.has(point.type) &&
        (filter.fallen || !isDead(point.status))
    )
    .map((point) => {
      const tier =
        point.type === 'settlement'
          ? tierOf(view, point.id, input.thresholds)
          : null
      const key = `entity:${point.id}`
      const at = dragOf(key, point.x, point.y)
      const screen = toScreen(transform, at.x, at.y)
      return { point, tier, key, screen, priority: priorityOf(point, tier) }
    })
    .filter((item) => onScreen(item.screen.x, item.screen.y, size))
    .sort(
      (left, right) =>
        Number(right.key === input.drag?.key) -
          Number(left.key === input.drag?.key) ||
        right.priority - left.priority ||
        left.point.id - right.point.id
    )
  const grid = new Map<string, MarkerDraw[]>()
  const families = new Map<MarkerDraw, Map<string, number>>()
  const draws: MarkerDraw[] = []
  for (const item of candidates) {
    const column = Math.floor(item.screen.x / CLUSTER_PX)
    const row = Math.floor(item.screen.y / CLUSTER_PX)
    let host: MarkerDraw | null = null
    let best = CLUSTER_PX
    if (item.key !== input.drag?.key)
      for (let dx = -1; dx <= 1; dx += 1)
        for (let dy = -1; dy <= 1; dy += 1)
          for (const draw of grid.get(`${column + dx}:${row + dy}`) ?? []) {
            if (draw.key === input.drag?.key) continue
            const distance = Math.hypot(
              draw.x - item.screen.x,
              draw.y - item.screen.y
            )
            if (distance <= best) {
              best = distance
              host = draw
            }
          }
    const color = familyColor(item.point.type, tokens)
    if (host) {
      host.members.push(item.point.id)
      const counts = families.get(host)
      counts?.set(color, (counts.get(color) ?? 0) + 1)
      if (!host.crown && palette?.rulers.has(item.point.id))
        host.crown = palette.colorOf(`ruler:${item.point.id}`)
      continue
    }
    const portrait = relative >= PORTRAIT_ZOOM && item.point.cover !== null
    const base = item.tier
      ? TIER_RADIUS[item.tier]
      : markerRadius(item.point.type, item.point.power)
    const draw: MarkerDraw = {
      key: item.key,
      point: item.point,
      x: item.screen.x,
      y: item.screen.y,
      radius: portrait ? base * PORTRAIT_GAIN : base,
      tier: item.tier,
      members: [item.point.id],
      slices: [],
      crown:
        input.mode === 'political' && palette?.rulers.has(item.point.id)
          ? palette.colorOf(`ruler:${item.point.id}`)
          : null,
      portrait,
    }
    families.set(draw, new Map([[color, 1]]))
    draws.push(draw)
    const cell = `${column}:${row}`
    const list = grid.get(cell)
    if (list) list.push(draw)
    else grid.set(cell, [draw])
  }
  for (const draw of draws) {
    if (draw.members.length > 1)
      draw.slices = slicesOf(families.get(draw) ?? new Map())
    if (input.mode !== 'political') draw.crown = null
  }
  return draws
}

function stacksOf(input: LayoutInput): {
  stacks: StackDraw[]
  glows: GlowDraw[]
} {
  const { view, transform, size, tokens, overlays } = input
  const light = view.geometry.palette.land_label
  const stacks: StackDraw[] = []
  const glows: GlowDraw[] = []
  const bySite = <T extends { location_id?: number | null }>(
    items: readonly T[]
  ) => {
    const groups = new Map<number, T[]>()
    for (const item of items) {
      if (item.location_id === null || item.location_id === undefined) continue
      const list = groups.get(item.location_id)
      if (list) list.push(item)
      else groups.set(item.location_id, [item])
    }
    return groups
  }
  const battles = overlays.wars
    ? bySite(view.markers.filter((marker) => marker.kind === 'battle'))
    : new Map()
  if (overlays.wars)
    for (const [site, wars] of bySite(view.wars)) {
      const place = locate(input, site)
      if (!place) continue
      const screen = toScreen(transform, place.x, place.y)
      if (!onScreen(screen.x, screen.y, size)) continue
      const fought = battles.get(site) ?? []
      const ongoing = wars.some((war) => war.ongoing)
      glows.push({
        x: screen.x,
        y: screen.y,
        radius:
          GLOW_BASE +
          GLOW_GAIN * Math.sqrt(wars.length + fought.length * BATTLE_HEAT),
        hot: ongoing,
      })
      stacks.push({
        key: `war:${site}`,
        kind: 'war',
        x: screen.x + STACK_OFFSET,
        y: screen.y - STACK_OFFSET,
        ids: [
          ...wars.map((war) => war.id),
          ...fought.map((marker: { id: number }) => marker.id),
        ],
        count: wars.length,
        ongoing,
        color: tokens.destructive,
        icon: warIcon(),
        slices: [],
      })
    }
  if (overlays.events) {
    const shown = view.markers.filter(
      (marker) => !(overlays.wars && marker.kind === 'battle')
    )
    for (const [site, markers] of bySite(shown)) {
      const place = locate(input, site)
      if (!place) continue
      const screen = toScreen(transform, place.x, place.y)
      if (!onScreen(screen.x, screen.y, size)) continue
      const kinds = new Map<string, number>()
      for (const marker of markers)
        kinds.set(marker.kind, (kinds.get(marker.kind) ?? 0) + 1)
      const ordered = [...kinds.entries()].sort(
        (left, right) => right[1] - left[1]
      )
      const dominant = ordered[0][0]
      stacks.push({
        key: `event:${site}`,
        kind: 'event',
        x: screen.x - STACK_OFFSET,
        y: screen.y - STACK_OFFSET,
        ids: markers.map((marker) => marker.id),
        count: markers.length,
        ongoing: false,
        color: eventColor(dominant, tokens, light),
        icon: eventIcon(dominant),
        slices:
          ordered.length > 1
            ? ordered.map(([kind, value]) => ({
                color: eventColor(kind, tokens, light),
                value,
              }))
            : [],
      })
    }
  }
  return { stacks, glows }
}

function domainLabels(input: LayoutInput, context: CanvasRenderingContext2D) {
  const { palette, anchors, transform, size, tokens } = input
  if (!palette || input.mode === 'regions' || input.mode === 'terrain')
    return []
  const relative = relativeZoom(transform, input.fit)
  const zoom = Math.min(
    DOMAIN_ZOOM_MAX,
    Math.max(DOMAIN_ZOOM_MIN, relative ** DOMAIN_ZOOM_POWER)
  )
  const categories = new Map(palette.categories.map((item) => [item.key, item]))
  const labels: { candidate: LabelCandidate; draw: LabelDraw }[] = []
  for (const anchor of anchors) {
    const category = categories.get(anchor.key)
    if (!category) continue
    const screen = toScreen(transform, anchor.x, anchor.y)
    if (!onScreen(screen.x, screen.y, size)) continue
    const textSize =
      Math.min(
        DOMAIN_MAX,
        Math.max(
          DOMAIN_MIN,
          DOMAIN_BASE + Math.sqrt(anchor.cells) * DOMAIN_GAIN
        )
      ) * zoom
    const styled = font(textSize, tokens.fontDisplay, 700)
    context.font = styled
    context.letterSpacing = '0.3em'
    const text = fitText(
      context,
      category.mapLabel.toLocaleUpperCase('en-US'),
      size.width * 0.5
    )
    const width = context.measureText(text).width
    context.letterSpacing = '0px'
    labels.push({
      candidate: {
        id: `domain:${anchor.key}`,
        x: screen.x,
        y: screen.y,
        width,
        height: textSize + 4,
        priority: anchor.cells,
        always: true,
        shifts: verticalShifts(textSize, DOMAIN_LABEL_TRIES),
      },
      draw: {
        text,
        x: screen.x,
        y: screen.y,
        font: styled,
        spacing: '0.3em',
        fill: category.color,
        halo: DOMAIN_HALO,
        alpha: 0.92,
      },
    })
  }
  return labels
}

export function computeLayout(
  input: LayoutInput,
  context: CanvasRenderingContext2D
): Layout {
  const { view, transform, size, tokens, overlays } = input
  const palette = view.geometry.palette
  const light = palette.land_label
  const draggable = !input.past && !input.noteMode
  const relative = relativeZoom(transform, input.fit)
  const dragOf = (key: string, x: number, y: number) =>
    input.drag && input.drag.key === key
      ? { x: input.drag.x, y: input.drag.y }
      : { x, y }
  const hits: HitTarget[] = []

  if (overlays.roads || overlays.ties || overlays.trade || overlays.outbreaks)
    for (const line of lineHits(
      view,
      transform,
      overlays.roads,
      overlays.ties,
      overlays.trade,
      overlays.outbreaks
    ))
      hits.push({
        key: `line:${line.info.kind}:${line.info.source}:${line.info.target}`,
        kind: 'line',
        id: line.info.source,
        x: 0,
        y: 0,
        radius: 0,
        path: line.points,
        line: line.info,
        draggable: false,
      })

  const markers = clusterMarkers(input, dragOf)
  const { stacks, glows } = stacksOf(input)
  const obstacles: Box[] = []
  for (const marker of markers) {
    const reach =
      marker.radius + (marker.members.length > 1 ? RING_GAP + RING_WIDTH : 0)
    obstacles.push(boxAt(marker.x, marker.y, reach * 2, reach * 2))
    hits.push({
      key: marker.key,
      kind: 'entity',
      id: marker.point.id,
      x: marker.x,
      y: marker.y,
      radius: reach + 3,
      members: marker.members,
      draggable,
    })
  }
  for (const stack of stacks) {
    obstacles.push(boxAt(stack.x, stack.y, EVENT_RADIUS * 2, EVENT_RADIUS * 2))
    hits.push({
      key: stack.key,
      kind: stack.kind,
      id: stack.ids[0],
      x: stack.x,
      y: stack.y,
      radius: EVENT_RADIUS + 3,
      members: stack.ids,
      draggable: false,
    })
  }
  const notes = view.notes.map((note) => {
    const screen = toScreen(transform, note.x, note.y)
    hits.push({
      key: `note:${note.id}`,
      kind: 'note',
      id: note.id,
      x: screen.x,
      y: screen.y - NOTE_PIN * 1.2,
      radius: NOTE_PIN + 2,
      draggable: false,
    })
    return { note, x: screen.x, y: screen.y }
  })

  const labels: LabelDraw[] = []
  if (!overlays.labels) return { markers, stacks, glows, notes, labels, hits }

  const domains = domainLabels(input, context)
  const placedDomains = placeLabels(
    domains.map((item) => item.candidate),
    {
      obstacles,
      bounds: { left: 0, top: 0, right: size.width, bottom: size.height },
    }
  )
  const domainById = new Map(domains.map((item) => [item.candidate.id, item]))
  for (const placed of placedDomains) {
    const item = domainById.get(placed.id)
    if (item) labels.push({ ...item.draw, x: placed.x, y: placed.y })
  }

  const markerCandidates: { candidate: LabelCandidate; draw: LabelDraw }[] = []
  for (const marker of markers) {
    const point = marker.point
    if (!LABELLED_TYPES.has(point.type) && point.power < POWERFUL_LEVEL)
      continue
    const tier = marker.tier
    const major =
      tier !== null &&
      SETTLEMENT_TIERS.indexOf(tier) >= SETTLEMENT_TIERS.indexOf('city')
    const pinned = input.hoverKey === marker.key || input.focusId === point.id
    const visible =
      major ||
      (tier !== null && relative > SETTLEMENT_ZOOM) ||
      relative > ANY_LABEL_ZOOM ||
      pinned
    if (!visible) continue
    const textSize = tier ? TIER_LABEL_SIZE[tier] : MARKER_LABEL_SIZE
    const styled = font(
      textSize,
      tokens.fontBody,
      tier && tier !== 'village' ? 600 : 400
    )
    context.font = styled
    const text = fitText(context, point.name, MARKER_LABEL_MAX)
    const y = marker.y + marker.radius + LABEL_GAP + textSize / 2
    markerCandidates.push({
      candidate: {
        id: marker.key,
        x: marker.x,
        y,
        width: context.measureText(text).width,
        height: textSize + 2,
        priority:
          (tier ? SETTLEMENT_TIERS.indexOf(tier) + 10 : 0) + point.power,
        always: pinned,
        shifts: [0],
      },
      draw: {
        text,
        x: marker.x,
        y,
        font: styled,
        spacing: '0px',
        fill: light,
        halo: 3.2,
        alpha: isDead(point.status) ? 0.7 : 1,
      },
    })
  }
  const placedMarkers = placeLabels(
    markerCandidates.map((item) => item.candidate),
    { obstacles: [...obstacles, ...placedDomains.map((label) => label.box)] }
  )
  const markerById = new Map(
    markerCandidates.map((item) => [item.candidate.id, item])
  )
  for (const placed of placedMarkers) {
    const item = markerById.get(placed.id)
    if (item) labels.push({ ...item.draw, x: placed.x, y: placed.y })
  }

  const regionCandidates: {
    candidate: LabelCandidate
    draw: LabelDraw
    id: number
  }[] = []
  for (const region of view.geometry.regions) {
    const point = input.pointById.get(region.id)
    if (!point) continue
    const key = `region:${region.id}`
    const at = dragOf(key, point.x, point.y)
    const screen = toScreen(transform, at.x, at.y)
    if (!onScreen(screen.x, screen.y, size)) continue
    const textSize = regionLabelSize(region.size)
    const styled = font(textSize, tokens.fontDisplay, 700, region.is_water)
    context.font = styled
    context.letterSpacing = '0.18em'
    const text = fitText(
      context,
      point.name.toLocaleUpperCase('en-US'),
      Math.min(REGION_LABEL_MAX, size.width * 0.6)
    )
    const width = context.measureText(text).width
    context.letterSpacing = '0px'
    const pinned = input.hoverKey === key || input.drag?.key === key
    regionCandidates.push({
      id: region.id,
      candidate: {
        id: key,
        x: screen.x,
        y: screen.y,
        width,
        height: textSize + 2,
        priority: region.size,
        always: pinned,
        shifts: verticalShifts(textSize, REGION_LABEL_TRIES),
      },
      draw: {
        text,
        x: screen.x,
        y: screen.y,
        font: styled,
        spacing: '0.18em',
        fill: region.is_water ? palette.water_label : light,
        halo: 3.2,
        alpha: input.mode === 'terrain' || pinned ? 1 : 0.82,
      },
    })
  }
  const regionHits: HitTarget[] = []
  const placedRegions = placeLabels(
    regionCandidates.map((item) => item.candidate),
    {
      obstacles: [
        ...obstacles,
        ...placedDomains.map((label) => label.box),
        ...placedMarkers.map((label) => label.box),
      ],
      bounds: { left: 0, top: 0, right: size.width, bottom: size.height },
    }
  )
  const regionById = new Map(
    regionCandidates.map((item) => [item.candidate.id, item])
  )
  for (const placed of placedRegions) {
    const item = regionById.get(placed.id)
    if (!item) continue
    labels.push({ ...item.draw, x: placed.x, y: placed.y })
    regionHits.push({
      key: placed.id,
      kind: 'region',
      id: item.id,
      x: placed.x,
      y: placed.y,
      radius: 0,
      box: placed.box,
      draggable,
    })
  }
  const firstPoint = hits.findIndex((hit) => hit.kind !== 'line')
  const ordered =
    firstPoint === -1
      ? [...hits, ...regionHits]
      : [...hits.slice(0, firstPoint), ...regionHits, ...hits.slice(firstPoint)]
  return { markers, stacks, glows, notes, labels, hits: ordered }
}
