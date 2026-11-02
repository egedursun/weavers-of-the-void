import {
  type CosmosData,
  type CosmosWorld,
  type EntitySummary,
  type ForeignGodRecord,
  type JourneyRecord,
  type RouteRecord,
  type StarRecord,
  type WorldType,
  type WorldTypeLook,
} from '../api'
import { JOURNEY_STATUS_ORDER } from './labels'

export type RouteStateKey =
  | 'open'
  | 'temporary'
  | 'unaligned'
  | 'sealed'
  | 'severed'
  | 'forgotten'
  | 'collapsed'
  | 'snapped'

export type RouteState = {
  key: RouteStateKey
  open: boolean
  untilEpoch: number | null
  opensAtEpoch: number | null
}

export const ROUTE_STATE_LABEL: Record<RouteStateKey, string> = {
  open: 'Open',
  temporary: 'Temporarily open',
  unaligned: 'Not aligned',
  sealed: 'Sealed',
  severed: 'Severed',
  forgotten: 'In oblivion',
  collapsed: 'Collapsed',
  snapped: 'Snapped',
}

export const RESTORABLE_ROUTE_STATES: ReadonlySet<RouteStateKey> = new Set([
  'sealed',
  'severed',
  'collapsed',
  'snapped',
])

export function routeState(route: RouteRecord): RouteState {
  if (route.active) {
    return {
      key: route.temp_open_until_epoch !== null ? 'temporary' : 'open',
      open: true,
      untilEpoch: route.temp_open_until_epoch,
      opensAtEpoch: null,
    }
  }
  const closure = route.closure
  const key: RouteStateKey =
    closure === null
      ? route.method === 'slingshot_orbit'
        ? 'unaligned'
        : 'sealed'
      : closure
  return {
    key,
    open: false,
    untilEpoch: null,
    opensAtEpoch: route.temp_closed_until_epoch,
  }
}

export function routeStateText(route: RouteRecord): string {
  const state = routeState(route)
  const label = ROUTE_STATE_LABEL[state.key]
  if (state.untilEpoch !== null)
    return `${label} until the start of epoch ${state.untilEpoch}`
  if (state.opensAtEpoch !== null)
    return `${label}, opens at the start of epoch ${state.opensAtEpoch}`
  return label
}

export function isRouteOpen(route: RouteRecord): boolean {
  return route.active
}

export function otherEnd(route: RouteRecord, worldId: number): number {
  return route.world_a_id === worldId ? route.world_b_id : route.world_a_id
}

export function journeyProgress(
  journey: JourneyRecord,
  route: RouteRecord | undefined
): number {
  if (journey.status === 'arrived') return 1
  const duration = Math.max(route?.duration_epochs ?? 1, 1)
  const done = duration - Math.min(journey.epochs_left, duration)
  return Math.max(0, Math.min(1, done / duration))
}

export function isUnderway(journey: JourneyRecord): boolean {
  return journey.status === 'underway' || journey.status === 'waiting'
}

export function sortJourneys(journeys: JourneyRecord[]): JourneyRecord[] {
  return [...journeys].sort(
    (left, right) =>
      JOURNEY_STATUS_ORDER[left.status] - JOURNEY_STATUS_ORDER[right.status] ||
      right.start_epoch - left.start_epoch ||
      right.id - left.id
  )
}

export type CosmosIndex = {
  data: CosmosData
  worlds: CosmosWorld[]
  world: (id: number | null | undefined) => CosmosWorld | undefined
  star: (id: number | null | undefined) => StarRecord | undefined
  route: (id: number | null | undefined) => RouteRecord | undefined
  look: (type: WorldType) => WorldTypeLook | undefined
  palette: (type: WorldType) => string[]
  moonsOf: (worldId: number) => CosmosWorld[]
  planetsOf: (starId: number) => CosmosWorld[]
  routesOf: (worldId: number) => RouteRecord[]
  godsOf: (worldId: number) => ForeignGodRecord[]
  arrivingAt: (worldId: number) => JourneyRecord[]
  placesOf: (worldId: number) => EntitySummary[]
  communitiesOf: (worldId: number) => EntitySummary[]
  entityName: (id: number | null | undefined) => string | undefined
  worldName: (id: number | null | undefined) => string
  hasSlingshot: boolean
}

function groupBy<T>(items: T[], key: (item: T) => number): Map<number, T[]> {
  const groups = new Map<number, T[]>()
  for (const item of items) {
    const id = key(item)
    const group = groups.get(id)
    if (group) group.push(item)
    else groups.set(id, [item])
  }
  return groups
}

const NONE: never[] = []

export function indexCosmos(data: CosmosData): CosmosIndex {
  const worlds = new Map(data.worlds.map((item) => [item.world.id, item]))
  const stars = new Map(data.stars.map((star) => [star.id, star]))
  const routes = new Map(data.routes.map((route) => [route.id, route]))
  const looks = new Map(data.world_types.map((look) => [look.world_type, look]))
  const moons = groupBy(
    data.worlds.filter((item) => item.world.parent_world_id !== null),
    (item) => item.world.parent_world_id ?? 0
  )
  const planets = groupBy(
    data.worlds.filter(
      (item) =>
        item.world.parent_world_id === null && item.world.star_id !== null
    ),
    (item) => item.world.star_id ?? 0
  )
  for (const group of planets.values())
    group.sort(
      (left, right) =>
        left.world.orbit - right.world.orbit || left.world.id - right.world.id
    )
  const routesByWorld = new Map<number, RouteRecord[]>()
  for (const route of data.routes) {
    for (const end of [route.world_a_id, route.world_b_id]) {
      const list = routesByWorld.get(end)
      if (list) list.push(route)
      else routesByWorld.set(end, [route])
    }
  }
  const gods = groupBy(data.foreign_gods, (god) => god.world_id)
  const arriving = groupBy(
    data.journeys.filter(isUnderway),
    (journey) => journey.destination_world_id
  )
  const places = groupBy(data.places, (place) => place.world_id)
  const communities = groupBy(data.communities, (item) => item.world_id)
  const names = new Map<number, string>()
  for (const entity of [...data.places, ...data.communities])
    names.set(entity.id, entity.name)
  for (const item of data.worlds) names.set(item.world.id, item.world.name)
  for (const star of data.stars) names.set(star.id, star.name)
  for (const god of data.foreign_gods) names.set(god.id, god.name)
  return {
    data,
    worlds: data.worlds,
    world: (id) => (id == null ? undefined : worlds.get(id)),
    star: (id) => (id == null ? undefined : stars.get(id)),
    route: (id) => (id == null ? undefined : routes.get(id)),
    look: (type) => looks.get(type),
    palette: (type) => looks.get(type)?.palette.biome_colours ?? NONE,
    moonsOf: (worldId) => moons.get(worldId) ?? NONE,
    planetsOf: (starId) => planets.get(starId) ?? NONE,
    routesOf: (worldId) => routesByWorld.get(worldId) ?? NONE,
    godsOf: (worldId) => gods.get(worldId) ?? NONE,
    arrivingAt: (worldId) => arriving.get(worldId) ?? NONE,
    placesOf: (worldId) => places.get(worldId) ?? NONE,
    communitiesOf: (worldId) => communities.get(worldId) ?? NONE,
    entityName: (id) => (id == null ? undefined : names.get(id)),
    worldName: (id) =>
      (id == null ? undefined : worlds.get(id)?.world.name) ??
      'an unknown world',
    hasSlingshot: data.routes.some(
      (route) => route.method === 'slingshot_orbit'
    ),
  }
}

export function isMisty(item: CosmosWorld): boolean {
  return (
    item.world.discovery === 'unknown' || item.world.discovery === 'forgotten'
  )
}

export function homeWorldId(
  index: CosmosIndex,
  primaryWorldId: number | null | undefined
): number | undefined {
  return primaryWorldId ?? index.worlds[0]?.world.id
}

export function crowdedRegions(
  places: EntitySummary[],
  communities: EntitySummary[],
  limit: number
): { region: EntitySummary; count: number }[] {
  const counts = new Map<number, number>()
  for (const community of communities) {
    if (community.location_id === null) continue
    counts.set(
      community.location_id,
      (counts.get(community.location_id) ?? 0) + 1
    )
  }
  return places
    .filter((place) => place.entity_type === 'region')
    .map((region) => ({ region, count: counts.get(region.id) ?? 0 }))
    .filter((entry) => entry.count > 0)
    .sort(
      (left, right) =>
        right.count - left.count || left.region.id - right.region.id
    )
    .slice(0, limit)
}
