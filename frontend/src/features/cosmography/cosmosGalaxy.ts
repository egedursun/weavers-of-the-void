import { type CosmosData } from '@/features/cosmos/api'
import { type Cosmography, type GalaxyRecord } from './api'

export const BETWEEN_GALAXIES = 0

export function galaxyOfWorlds(heavens: Cosmography): Map<number, number> {
  return new Map(
    heavens.placements.map((row) => [
      row.world_id,
      row.galaxy_id ?? BETWEEN_GALAXIES,
    ])
  )
}

export function chooseGalaxy(
  heavens: Cosmography | undefined,
  wanted: number | undefined,
  worldId: number | undefined,
  homeId: number | undefined
): number | undefined {
  if (!heavens || heavens.galaxies.length === 0) return undefined
  const known = new Set([
    ...heavens.galaxies.map((row) => row.id),
    BETWEEN_GALAXIES,
  ])
  if (wanted !== undefined && known.has(wanted)) return wanted
  const ofWorld = galaxyOfWorlds(heavens)
  for (const id of [worldId, homeId]) {
    const found = id !== undefined ? ofWorld.get(id) : undefined
    if (found !== undefined) return found
  }
  return heavens.galaxies[0]?.id
}

export function cosmosInGalaxy(
  data: CosmosData,
  heavens: Cosmography | undefined,
  galaxyId: number | undefined
): CosmosData {
  if (!heavens || galaxyId === undefined) return data
  const ofWorld = galaxyOfWorlds(heavens)
  const worlds = data.worlds.filter(
    (item) => (ofWorld.get(item.world.id) ?? BETWEEN_GALAXIES) === galaxyId
  )
  const kept = new Set(worlds.map((item) => item.world.id))
  const stars = data.stars.filter(
    (star) => (star.galaxy_id ?? BETWEEN_GALAXIES) === galaxyId
  )
  const starIds = new Set(stars.map((star) => star.id))
  const routes = data.routes.filter(
    (route) => kept.has(route.world_a_id) && kept.has(route.world_b_id)
  )
  const routeIds = new Set(routes.map((route) => route.id))
  return {
    ...data,
    stars,
    worlds,
    routes,
    journeys: data.journeys.filter((journey) => routeIds.has(journey.route_id)),
    foreign_gods: data.foreign_gods.filter((god) => kept.has(god.world_id)),
    sky_events: data.sky_events.filter(
      (event) =>
        (event.world_id !== null && kept.has(event.world_id)) ||
        (event.star_id !== null && starIds.has(event.star_id)) ||
        (event.world_id === null && event.star_id === null)
    ),
    places: data.places.filter((place) => kept.has(place.world_id)),
    communities: data.communities.filter((community) =>
      kept.has(community.world_id)
    ),
  }
}

export function leavingRoutes(
  data: CosmosData,
  heavens: Cosmography | undefined,
  galaxyId: number | undefined
): number {
  if (!heavens || galaxyId === undefined) return 0
  const ofWorld = galaxyOfWorlds(heavens)
  return data.routes.filter((route) => {
    const a = ofWorld.get(route.world_a_id) ?? BETWEEN_GALAXIES
    const b = ofWorld.get(route.world_b_id) ?? BETWEEN_GALAXIES
    return (a === galaxyId) !== (b === galaxyId)
  }).length
}

export function galaxyName(
  galaxies: readonly GalaxyRecord[],
  id: number | undefined
): string {
  if (id === BETWEEN_GALAXIES) return 'Between the galaxies'
  return galaxies.find((row) => row.id === id)?.name ?? 'The heavens'
}
