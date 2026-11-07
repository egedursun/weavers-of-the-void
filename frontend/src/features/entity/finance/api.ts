import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { loreKeys } from '../api/keys'

export type Finance = components['schemas']['FinanceView']
export type FinancePolicy = components['schemas']['FinancePolicyView']
export type FinanceHoard = components['schemas']['FinanceHoardView']
export type FinanceIndicator = components['schemas']['FinanceIndicatorView']
export type CommodityKind = components['schemas']['CommodityKind']
export type TradePolicyKind = components['schemas']['TradePolicyKind']
export type CreditState = components['schemas']['CreditState']
export type SpeculationStatus = components['schemas']['SpeculationStatus']

export function financeKey(nodeId: number) {
  return [...loreKeys.entity(nodeId), 'finance'] as const
}

export function useFinance(nodeId: number) {
  return useQuery({
    queryKey: financeKey(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/finance/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
    retry: false,
  })
}
