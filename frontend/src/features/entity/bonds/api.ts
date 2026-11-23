import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { loreKeys } from '../api/keys'

export type Bonds = components['schemas']['BondsView']
export type Bond = components['schemas']['TieView']
export type Passion = components['schemas']['PassionView']
export type Circle = components['schemas']['CircleView']
export type Rank = components['schemas']['RankView']
export type Contest = components['schemas']['ContestView']
export type RelationType = components['schemas']['RelationType']
export type PassionKind = components['schemas']['PassionKind']
export type PassionSource = components['schemas']['PassionSource']
export type CircleKind = components['schemas']['CircleKind']
export type ContestKind = components['schemas']['ContestKind']
export type ContestStake = components['schemas']['ContestStake']
export type AppealKind = components['schemas']['AppealKind']
export type PersuasionAim = components['schemas']['PersuasionAim']
export type GroupKind = components['schemas']['GroupKind']
export type ValueAxis = components['schemas']['ValueAxis']

export function bondsKey(nodeId: number) {
  return [...loreKeys.entity(nodeId), 'bonds'] as const
}

export function useBonds(nodeId: number) {
  return useQuery({
    queryKey: bondsKey(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/bonds/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
    retry: false,
  })
}
