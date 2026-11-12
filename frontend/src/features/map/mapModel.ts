import { type MapView, type WorldMap } from './api'

export type Transform = { k: number; x: number; y: number }

export type Size = { width: number; height: number }

export const FIT_MARGIN = 1.12
export const MIN_ZOOM = 0.3
export const MAX_ZOOM = 12
export const FOCUS_ZOOM = 3
export const UNITS_PER_LEAGUE = 10
export const SCALE_BAR_PX = 120

export const LAYER_MODES = [
  'terrain',
  'political',
  'realms',
  'de_jure',
  'regions',
  'creators',
  'religions',
  'dominion',
  'languages',
  'ground',
  'soil',
  'climate',
  'land_use',
  'rainfall',
  'danger',
  'scars',
  'sacred',
  'ley',
  'population',
  'followers',
  'soldiers',
  'wildlife',
  'species_range',
  'desirability',
  'coverage',
  'niches',
  'solidarity',
  'rings',
  'centrality',
  'nutrients',
] as const
export type LayerMode = (typeof LAYER_MODES)[number]

export const LAYER_LABEL: Record<LayerMode, string> = {
  terrain: 'Terrain',
  political: 'Political',
  realms: 'Realms',
  de_jure: 'De jure titles',
  regions: 'Regions',
  creators: 'Creators',
  religions: 'Religions',
  dominion: 'Divine dominion',
  languages: 'Languages',
  ground: 'Ground',
  soil: 'Soil',
  climate: 'Climate',
  land_use: 'Land use',
  rainfall: 'Rainfall',
  danger: 'Danger sources',
  scars: 'Scars',
  sacred: 'Holy ground',
  ley: 'Ley lines',
  population: 'Population',
  followers: 'Followers',
  soldiers: 'Soldiers',
  wildlife: 'Wildlife',
  species_range: 'Species range',
  desirability: 'Desirable districts',
  coverage: 'Service coverage',
  niches: 'Ways of life',
  solidarity: 'Solidarity and frontiers',
  rings: 'Rings of land use',
  centrality: 'Central places',
  nutrients: 'Soil nutrients',
}

export const LAYER_SURFACE: Partial<Record<LayerMode, string>> = {
  realms: 'map-layer-realms',
  de_jure: 'map-layer-de-jure',
  ground: 'map-layer-terrain',
  soil: 'map-layer-soil',
  climate: 'map-layer-climate',
  land_use: 'map-layer-land-use',
  rainfall: 'map-layer-rainfall',
  danger: 'map-layer-danger',
  scars: 'map-layer-scars',
  sacred: 'map-layer-sacred',
  ley: 'map-layer-ley',
  dominion: 'map-layer-dominion',
  population: 'map-layer-population',
  followers: 'map-layer-followers',
  soldiers: 'map-layer-soldiers',
  wildlife: 'map-layer-wildlife',
  species_range: 'map-layer-species-range',
  desirability: 'map-layer-desirability',
  coverage: 'map-layer-coverage',
  niches: 'map-layer-niches',
  solidarity: 'cycles-frontier-map',
  rings: 'map-layer-rings',
  centrality: 'map-layer-centrality',
  nutrients: 'map-layer-nutrients',
}

export const OVERLAY_SURFACE: Partial<Record<Overlay, string>> = {
  trade: 'map-layer-trade',
  outbreaks: 'map-layer-outbreaks',
  military: 'map-layer-military',
  faith: 'map-layer-faith',
  lore: 'map-layer-lore',
  beasts: 'map-layer-beasts',
}

export const OVERLAYS = [
  'roads',
  'trade',
  'outbreaks',
  'military',
  'faith',
  'lore',
  'beasts',
  'ties',
  'wars',
  'events',
  'labels',
  'fog',
] as const
export type Overlay = (typeof OVERLAYS)[number]

export const OVERLAY_LABEL: Record<Overlay, string> = {
  roads: 'Roads',
  trade: 'Trade',
  outbreaks: 'Sickness',
  military: 'Armies',
  faith: 'Holy places',
  lore: 'Legends and rites',
  beasts: 'Beast lairs',
  ties: 'Ties',
  wars: 'Wars',
  events: 'Events',
  labels: 'Labels',
  fog: 'Fog',
}

export const SETTLEMENT_TIERS = [
  'village',
  'town',
  'city',
  'great_city',
  'capital',
] as const
export type SettlementTier = (typeof SETTLEMENT_TIERS)[number]

export const TIER_LABEL: Record<SettlementTier, string> = {
  village: 'Village',
  town: 'Town',
  city: 'City',
  great_city: 'Great city',
  capital: 'Capital',
}

export const TIER_RADIUS: Record<SettlementTier, number> = {
  village: 7,
  town: 8.5,
  city: 10,
  great_city: 12,
  capital: 13,
}

export const COMMUNITY_TYPES = new Set(['people', 'faction', 'cult'])
export const LABELLED_TYPES = new Set([
  'settlement',
  'place',
  'resource',
  'people',
  'faction',
])
export const POWERFUL_LEVEL = 5

export function fitTransform(map: WorldMap, size: Size): Transform {
  const extent = map.extent
  const k = Math.min(
    size.width / (extent.width * FIT_MARGIN),
    size.height / (extent.height * FIT_MARGIN)
  )
  const centreX = extent.x + extent.width / 2
  const centreY = extent.y + extent.height / 2
  return {
    k,
    x: size.width / 2 - centreX * k,
    y: size.height / 2 - centreY * k,
  }
}

export function clampZoom(transform: Transform, fit: Transform): Transform {
  const min = fit.k * MIN_ZOOM
  const max = fit.k * MAX_ZOOM
  return { ...transform, k: Math.min(max, Math.max(min, transform.k)) }
}

export function zoomAt(
  transform: Transform,
  fit: Transform,
  factor: number,
  screenX: number,
  screenY: number
): Transform {
  const next = clampZoom({ ...transform, k: transform.k * factor }, fit)
  const ratio = next.k / transform.k
  return {
    k: next.k,
    x: screenX - (screenX - transform.x) * ratio,
    y: screenY - (screenY - transform.y) * ratio,
  }
}

export function centreOn(
  x: number,
  y: number,
  k: number,
  size: Size
): Transform {
  return { k, x: size.width / 2 - x * k, y: size.height / 2 - y * k }
}

export function toMap(transform: Transform, sx: number, sy: number) {
  return {
    x: (sx - transform.x) / transform.k,
    y: (sy - transform.y) / transform.k,
  }
}

export function toScreen(transform: Transform, mx: number, my: number) {
  return {
    x: mx * transform.k + transform.x,
    y: my * transform.k + transform.y,
  }
}

export function relativeZoom(transform: Transform, fit: Transform): number {
  return fit.k > 0 ? transform.k / fit.k : 1
}

export function leagues(units: number): string {
  const value = units / UNITS_PER_LEAGUE
  return value < 10 ? value.toFixed(1) : String(Math.round(value))
}

export class CellIndex {
  private readonly buckets = new Map<string, number[]>()
  private readonly size: number

  constructor(private readonly map: WorldMap) {
    const cells = map.cells
    const area = map.window.width * map.window.height
    this.size = Math.max(1, Math.sqrt(area / Math.max(1, cells.x.length)) * 2)
    cells.x.forEach((x, index) => {
      const key = this.key(x, cells.y[index])
      const list = this.buckets.get(key)
      if (list) list.push(index)
      else this.buckets.set(key, [index])
    })
  }

  private key(x: number, y: number): string {
    return `${Math.floor(x / this.size)}:${Math.floor(y / this.size)}`
  }

  nearest(x: number, y: number): number | null {
    const cells = this.map.cells
    const column = Math.floor(x / this.size)
    const row = Math.floor(y / this.size)
    let best: number | null = null
    let bestDistance = Number.POSITIVE_INFINITY
    for (let ring = 0; ring <= 2; ring += 1) {
      for (let dx = -ring; dx <= ring; dx += 1)
        for (let dy = -ring; dy <= ring; dy += 1) {
          for (const index of this.buckets.get(`${column + dx}:${row + dy}`) ??
            []) {
            const distance =
              (cells.x[index] - x) ** 2 + (cells.y[index] - y) ** 2
            if (distance < bestDistance) {
              bestDistance = distance
              best = index
            }
          }
        }
      if (best !== null) return best
    }
    return best
  }
}

export function cellPolygon(map: WorldMap, index: number): number[] {
  const offsets = map.cells.polygon_offsets
  return map.cells.polygon_coordinates.slice(offsets[index], offsets[index + 1])
}

export function tracePolygon(
  context: CanvasRenderingContext2D | Path2D,
  coordinates: readonly number[]
): void {
  if (coordinates.length < 6) return
  context.moveTo(coordinates[0], coordinates[1])
  for (let index = 2; index < coordinates.length; index += 2)
    context.lineTo(coordinates[index], coordinates[index + 1])
  context.closePath()
}

export function tracePolyline(
  context: CanvasRenderingContext2D | Path2D,
  coordinates: readonly number[]
): void {
  if (coordinates.length < 4) return
  context.moveTo(coordinates[0], coordinates[1])
  for (let index = 2; index < coordinates.length; index += 2)
    context.lineTo(coordinates[index], coordinates[index + 1])
}

export type Trend = 'up' | 'down' | null

export function populationTrend(
  population: number,
  previous: number | null | undefined,
  minPct: number
): Trend {
  if (!previous || previous <= 0) return null
  const change = ((population - previous) / previous) * 100
  if (Math.abs(change) < minPct) return null
  return change > 0 ? 'up' : 'down'
}

export function percentChange(population: number, previous: number): number {
  return previous > 0
    ? Math.round(((population - previous) / previous) * 100)
    : 0
}

export function tierOf(
  view: MapView,
  entityId: number,
  thresholds: { town: number; city: number; greatCity: number }
): SettlementTier {
  const info = view.settlements[String(entityId)]
  if (info && (SETTLEMENT_TIERS as readonly string[]).includes(info.tier))
    return info.tier as SettlementTier
  const population = view.population[String(entityId)] ?? 0
  if (population >= thresholds.greatCity) return 'great_city'
  if (population >= thresholds.city) return 'city'
  if (population >= thresholds.town) return 'town'
  return 'village'
}

export function markerRadius(type: string, power: number): number {
  return COMMUNITY_TYPES.has(type) ? 9.5 : 8 + 0.25 * power
}

export function regionLabelSize(size: number): number {
  return Math.min(22, Math.max(12, 9 + Math.sqrt(size) * 0.5))
}

export type PositionedPoint = {
  id: number
  name: string
  type: string
  subtype: string | null
  status: string
  power: number
  x: number
  y: number
  locationId: number | null
  cover: string | null
}

export function positionedPoints(view: MapView): PositionedPoint[] {
  const placed = new Map(
    view.geometry.markers.map((marker) => [marker.id, marker])
  )
  const regions = new Map(
    view.geometry.regions.map((region) => [region.id, region])
  )
  const points: PositionedPoint[] = []
  for (const point of view.points) {
    const entity = point.entity
    const marker = placed.get(entity.id)
    const region = regions.get(entity.id)
    const anchor = region?.anchor ?? region?.centroid ?? null
    const x = point.x ?? marker?.x ?? anchor?.[0] ?? null
    const y = point.y ?? marker?.y ?? anchor?.[1] ?? null
    if (x === null || y === null) continue
    points.push({
      id: entity.id,
      name: entity.name,
      type: entity.entity_type,
      subtype: entity.subtype ?? null,
      status: entity.status,
      power: entity.power_level,
      x,
      y,
      locationId: entity.location_id ?? null,
      cover: point.cover ?? null,
    })
  }
  return points
}

export function isDead(status: string): boolean {
  return status === 'dead' || status === 'destroyed'
}
