import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

export type OuterAgencyView = components['schemas']['OuterAgencyView']
export type OuterPlanView = components['schemas']['OuterPlanView']
export type OuterHeraldView = components['schemas']['OuterHeraldView']
export type OuterIncursionView = components['schemas']['OuterIncursionView']
export type OuterPactView = components['schemas']['OuterPactView']
export type OuterRelationView = components['schemas']['OuterRelationView']
export type OuterSealView = components['schemas']['OuterSealView']

export function useOuterAgency(beingId: number) {
  return useQuery({
    queryKey: [...queryKeys.world.all, 'outer-agency', beingId] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/outer-beings/{being_id}/agency', {
          params: { path: { being_id: beingId } },
        })
      ),
  })
}
