import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { loreKeys } from '../api/keys'

export type Affairs = components['schemas']['AffairsView']
export type CouncilTaskView = components['schemas']['CouncilTaskView']
export type Election = components['schemas']['ElectionView']
export type Seat = components['schemas']['SeatView']
export type Tax = components['schemas']['TaxView']
export type Mandate = components['schemas']['MandateView']
export type Demand = components['schemas']['DemandView']
export type Approval = components['schemas']['ApprovalView']
export type CouncilTask = components['schemas']['CouncilTask']
export type TaxKind = components['schemas']['TaxKind']
export type MandateKind = components['schemas']['MandateKind']
export type MandateState = components['schemas']['MandateState']
export type NobleWant = components['schemas']['NobleWant']
export type CommodityKind = components['schemas']['CommodityKind']
export type DistrictKind = components['schemas']['DistrictKind']
export type Resolution = components['schemas']['ResolutionView']
export type ResolutionVote = components['schemas']['VoteView']
export type ResolutionKind = components['schemas']['ResolutionKind']
export type ResolutionState = components['schemas']['ResolutionState']
export type CourtPosition = components['schemas']['CourtPosition']
export type PositionView = components['schemas']['PositionView']

export function affairsKey(nodeId: number) {
  return [...loreKeys.entity(nodeId), 'affairs'] as const
}

export function useAffairs(nodeId: number) {
  return useQuery({
    queryKey: affairsKey(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/affairs/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
    retry: false,
  })
}
