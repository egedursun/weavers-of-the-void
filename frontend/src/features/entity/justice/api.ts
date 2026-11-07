import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { loreKeys } from '../api/keys'

export type Justice = components['schemas']['JusticeView']
export type Proposal = components['schemas']['LawProposalView']
export type Stance = components['schemas']['StanceView']
export type CrimeCase = components['schemas']['CrimeCaseView']
export type Witness = components['schemas']['WitnessView']
export type ProposalState = components['schemas']['ProposalState']
export type ProposalStance = components['schemas']['ProposalStance']
export type CaseStage = components['schemas']['CaseStage']
export type TrialKind = components['schemas']['TrialKind']
export type Deposition = components['schemas']['Deposition']
export type CrimeKind = components['schemas']['CrimeKind']
export type LawKind = components['schemas']['LawKind']
export type LegitimacyBasis = components['schemas']['LegitimacyBasis']

export function justiceKey(nodeId: number) {
  return [...loreKeys.entity(nodeId), 'justice'] as const
}

export function useJustice(nodeId: number) {
  return useQuery({
    queryKey: justiceKey(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/justice/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
    retry: false,
  })
}
