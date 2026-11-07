import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { loreKeys } from '../api/keys'

export type Lineage = components['schemas']['LineageView']
export type Genome = components['schemas']['GenomeView']
export type Gene = components['schemas']['GeneView']
export type Pool = components['schemas']['PoolView']
export type Locus = components['schemas']['LocusView']
export type Resemblance = components['schemas']['ResemblanceView']
export type LocusKey = components['schemas']['Locus']
export type GiftStance = components['schemas']['GiftStance']
export type Home = components['schemas']['HomeView']
export type Household = components['schemas']['HouseholdView']
export type Member = components['schemas']['HouseholdMemberView']
export type Dwelling = components['schemas']['DwellingView']
export type Aggregate = components['schemas']['AggregateView']
export type HouseholdRole = components['schemas']['HouseholdRole']
export type DwellingKind = components['schemas']['DwellingKind']
export type SocialClass = components['schemas']['SocialClass']

export function lineageKey(nodeId: number) {
  return [...loreKeys.entity(nodeId), 'lineage'] as const
}

export function homeKey(nodeId: number) {
  return [...loreKeys.entity(nodeId), 'home'] as const
}

export function useLineage(nodeId: number) {
  return useQuery({
    queryKey: lineageKey(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/lineage/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
    retry: false,
  })
}

export function useHome(nodeId: number) {
  return useQuery({
    queryKey: homeKey(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/home/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
    retry: false,
  })
}
