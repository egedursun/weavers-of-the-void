import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { fetchJobs } from '@/api/system'
import { RULES_STALE_TIME_MS } from '@/constants/ui'

export type WorldState = components['schemas']['StateResponse']
export type SonPublic = components['schemas']['SonPublic']
export type SonRecord = components['schemas']['SonRecord']
export type SonRelation = components['schemas']['SonRelationItem']
export type ThreadRecord = components['schemas']['ThreadRecord']
export type PlayerHints = components['schemas']['PlayerHints']
export type RuleValue = components['schemas']['RuleResponse']
export type ActionCatalogueItem = components['schemas']['ActionCatalogueItem']
export type ActionResponse = components['schemas']['ActionResponse']
export type Catalogue = components['schemas']['Catalogue']
export type ForeignGodRecord = components['schemas']['ForeignGodRecord']
export type WorldBrief = components['schemas']['WorldBriefItem']
export type Rarity = components['schemas']['Rarity']
export type Domain = components['schemas']['Domain']
export type StatKey = components['schemas']['Stat']
export type EntitySummary = components['schemas']['EntitySummary']
export type NodeRef = components['schemas']['NodeRef']
export type ChronicleLine = components['schemas']['ChronicleLineRecord']
export type ImageRecord = components['schemas']['ImageRecord']
export type FolkView = components['schemas']['FolkView']
export type WorldSettings = components['schemas']['WorldSettingsView']

export const ACTIVE_JOB_LIMIT = 50

export const godKeys = {
  state: [...queryKeys.world.all, 'state'] as const,
  sons: [...queryKeys.world.all, 'sons'] as const,
  relations: [...queryKeys.world.all, 'sons', 'relations'] as const,
  threads: [...queryKeys.world.all, 'threads'] as const,
  opportunities: [...queryKeys.world.all, 'opportunities'] as const,
  foreignGods: [...queryKeys.world.all, 'foreign-gods'] as const,
  settings: [...queryKeys.world.all, 'settings'] as const,
  distribution: [...queryKeys.world.all, 'sons', 'distribution'] as const,
  actions: [...queryKeys.rules.all, 'actions'] as const,
  catalogue: ['catalogue'] as const,
}

export function useWorldState() {
  return useQuery({
    queryKey: godKeys.state,
    queryFn: () => unwrap(api.GET('/api/state')),
  })
}

export type DistributionPreview =
  components['schemas']['DistributionPreviewView']

export function useDistributionPreview() {
  return useQuery({
    queryKey: godKeys.distribution,
    queryFn: () => unwrap(api.GET('/api/sons/distribution-preview')),
  })
}

export function useSons() {
  return useQuery({
    queryKey: godKeys.sons,
    queryFn: () => unwrap(api.GET('/api/sons')),
  })
}

export function useSonRelations() {
  return useQuery({
    queryKey: godKeys.relations,
    queryFn: () => unwrap(api.GET('/api/sons/relations')),
  })
}

export function useThreads() {
  return useQuery({
    queryKey: godKeys.threads,
    queryFn: () => unwrap(api.GET('/api/threads')),
  })
}

export function useOpportunities() {
  return useQuery({
    queryKey: godKeys.opportunities,
    queryFn: () => unwrap(api.GET('/api/opportunities')),
  })
}

export function useForeignGods() {
  return useQuery({
    queryKey: godKeys.foreignGods,
    queryFn: () => unwrap(api.GET('/api/foreign-gods')),
  })
}

export function useWorldSettings() {
  return useQuery({
    queryKey: godKeys.settings,
    queryFn: () => unwrap(api.GET('/api/settings')),
  })
}

export function useRules() {
  return useQuery({
    queryKey: queryKeys.rules.all,
    queryFn: () => unwrap(api.GET('/api/rules')),
    staleTime: RULES_STALE_TIME_MS,
  })
}

export function useActionCatalogue() {
  return useQuery({
    queryKey: godKeys.actions,
    queryFn: () => unwrap(api.GET('/api/actions')),
    staleTime: Infinity,
  })
}

export function useCatalogue() {
  return useQuery({
    queryKey: godKeys.catalogue,
    queryFn: () => unwrap(api.GET('/api/catalogue')),
    staleTime: Infinity,
  })
}

export function useActiveJobs() {
  return useQuery({
    queryKey: queryKeys.jobs.list(ACTIVE_JOB_LIMIT),
    queryFn: () => fetchJobs(ACTIVE_JOB_LIMIT),
  })
}

export type NameEntry = components['schemas']['NameEntry']

export function useNames(enabled = true) {
  return useQuery({
    queryKey: [...queryKeys.world.all, 'names'],
    queryFn: () => unwrap(api.GET('/api/names')),
    enabled,
  })
}

export function useCreatorHintLines() {
  return useQuery({
    queryKey: [...queryKeys.world.all, 'opportunities', 'creator'] as const,
    queryFn: () => unwrap(api.GET('/api/opportunities/creator')),
  })
}
