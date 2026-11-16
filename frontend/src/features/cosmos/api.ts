import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { fetchJob } from '@/api/system'
import { RULES_STALE_TIME_MS } from '@/constants/ui'

type Schemas = components['schemas']

export type CosmosData = Schemas['CosmosView']
export type CosmosWorld = Schemas['CosmosWorld']
export type WorldRecord = Schemas['WorldRecord']
export type StarRecord = Schemas['StarRecord']
export type RouteRecord = Schemas['RouteRecord']
export type JourneyRecord = Schemas['JourneyRecord']
export type ForeignGodRecord = Schemas['ForeignGodRecord']
export type SkyEventRecord = Schemas['SkyEventRecord']
export type WorldTypeLook = Schemas['WorldTypeLook']
export type EntitySummary = Schemas['EntitySummary']
export type NodeRef = Schemas['NodeRef']
export type DiscoverySummary = Schemas['DiscoverySummary']
export type SensedWorld = Schemas['SensedWorld']
export type WorldState = Schemas['StateResponse']
export type SonPublic = Schemas['SonPublic']
export type RuleValue = Schemas['RuleResponse']
export type ActionResponse = Schemas['ActionResponse']
export type ActionCatalogueItem = Schemas['ActionCatalogueItem']
export type TravelResource = Schemas['TravelResource']
export type NameEntry = Schemas['NameEntry']
export type ThreadRecord = Schemas['ThreadRecord']

export type WorldType = Schemas['WorldType']
export type StarType = Schemas['StarType']
export type TravelMethod = Schemas['TravelMethod']
export type SkyEventKind = Schemas['SkyEventKind']
export type Discovery = Schemas['Discovery']
export type Gravity = Schemas['Gravity']
export type Atmosphere = Schemas['Atmosphere']
export type ClimateEra = Schemas['ClimateEra']
export type JourneyIntent = Schemas['JourneyIntent']
export type JourneyStatus = Schemas['JourneyStatus']
export type RouteClosure = Schemas['RouteClosure']
export type QuestAim = Schemas['QuestAim']
export type QuestTargetKind = Schemas['QuestTargetKind']
export type Disaster = Schemas['Disaster']
export type ForeignGodStatus = Schemas['ForeignGodStatus']
export type HorizonStatus = Schemas['HorizonStatus']
export type WorldLaw = Schemas['WorldLaw']
export type AddictionView = Schemas['AddictionView']
export type ImmunityView = Schemas['CravingImmunityView']
export type NaturalLaw = Schemas['NaturalLaw']

export const cosmosKeys = {
  cosmos: [...queryKeys.world.all, 'cosmos'] as const,
  discovery: [...queryKeys.world.all, 'cosmos', 'discovery'] as const,
  sensed: [...queryKeys.world.all, 'cosmos', 'sensed'] as const,
  guide: (worldId: number) =>
    [...queryKeys.world.all, 'cosmos', 'guide', worldId] as const,
  state: [...queryKeys.world.all, 'state'] as const,
  actions: [...queryKeys.rules.all, 'actions'] as const,
  names: [...queryKeys.world.all, 'names'] as const,
  laws: (worldId: number) =>
    [...queryKeys.world.all, 'cosmos', 'laws', worldId] as const,
  addictions: (communityId: number | null) =>
    [...queryKeys.world.all, 'addictions', communityId] as const,
  immunities: (communityId: number | null) =>
    [...queryKeys.world.all, 'addiction-immunities', communityId] as const,
  geography: (worldId: number) =>
    [...queryKeys.world.all, 'cosmos', 'geography', worldId] as const,
}

export function useCosmos() {
  return useQuery({
    queryKey: cosmosKeys.cosmos,
    queryFn: () => unwrap(api.GET('/api/cosmos')),
  })
}

export function useDiscoverySummary() {
  return useQuery({
    queryKey: cosmosKeys.discovery,
    queryFn: () => unwrap(api.GET('/api/discovery-summary')),
  })
}

export function useSensedWorlds() {
  return useQuery({
    queryKey: cosmosKeys.sensed,
    queryFn: () => unwrap(api.GET('/api/sensed-worlds')),
  })
}

export function useWorldGuide(worldId: number | null) {
  return useQuery({
    queryKey: cosmosKeys.guide(worldId ?? 0),
    queryFn: () =>
      unwrap(
        api.GET('/api/worlds/{world_id}/guide', {
          params: { path: { world_id: worldId ?? 0 } },
        })
      ),
    enabled: worldId !== null && worldId > 0,
  })
}

export function useCosmosState() {
  return useQuery({
    queryKey: cosmosKeys.state,
    queryFn: () => unwrap(api.GET('/api/state')),
  })
}

export function useCosmosRules() {
  return useQuery({
    queryKey: queryKeys.rules.all,
    queryFn: () => unwrap(api.GET('/api/rules')),
    staleTime: RULES_STALE_TIME_MS,
  })
}

export function useCosmicCatalogue() {
  return useQuery({
    queryKey: cosmosKeys.actions,
    queryFn: () => unwrap(api.GET('/api/actions')),
    staleTime: Infinity,
  })
}

export function useJob(jobId: string | null) {
  return useQuery({
    queryKey: queryKeys.jobs.detail(jobId ?? ''),
    queryFn: () => fetchJob(jobId ?? ''),
    enabled: jobId !== null,
  })
}

export function useNames() {
  return useQuery({
    queryKey: cosmosKeys.names,
    queryFn: () => unwrap(api.GET('/api/names')),
  })
}

export function useWorldLaws(worldId: number) {
  return useQuery({
    queryKey: cosmosKeys.laws(worldId),
    queryFn: () =>
      unwrap(
        api.GET('/api/worlds/{world_id}/laws', {
          params: { path: { world_id: worldId } },
        })
      ),
  })
}

export function useWorldGeography(worldId: number, enabled: boolean) {
  return useQuery({
    queryKey: cosmosKeys.geography(worldId),
    queryFn: () =>
      unwrap(
        api.GET('/api/worlds/{world_id}/geography', {
          params: { path: { world_id: worldId } },
        })
      ),
    enabled,
  })
}

export function useImmunities(communityId: number | null = null) {
  return useQuery({
    queryKey: cosmosKeys.immunities(communityId),
    queryFn: () =>
      unwrap(
        api.GET('/api/addiction-immunities', {
          params: { query: { community_id: communityId ?? undefined } },
        })
      ),
  })
}

export function useAddictions(communityId: number | null = null) {
  return useQuery({
    queryKey: cosmosKeys.addictions(communityId),
    queryFn: () =>
      unwrap(
        api.GET('/api/addictions', {
          params: { query: { community_id: communityId ?? undefined } },
        })
      ),
  })
}

export function useWorldPulse(worldId: number) {
  return useQuery({
    queryKey: [...cosmosKeys.laws(worldId), 'pulse'] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/worlds/{world_id}/pulse', {
          params: { path: { world_id: worldId } },
        })
      ),
  })
}
