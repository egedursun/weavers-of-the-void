import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { loreKeys } from '../api/keys'

export type Works = components['schemas']['WorksView']
export type WorksMethod = components['schemas']['WorksMethodView']
export type WorksOption = components['schemas']['WorksOptionView']
export type WorksEnergy = components['schemas']['WorksEnergyView']
export type WorksStock = components['schemas']['WorksStockView']
export type WorksPollution = components['schemas']['WorksPollutionView']
export type WorksStores = components['schemas']['WorksStoresView']
export type MethodKind = components['schemas']['MethodKind']
export type WorksSite = components['schemas']['WorksSiteView']
export type WorksLedger = components['schemas']['WorksLedgerView']
export type WorkshopKind = components['schemas']['WorkshopKind']

export function worksKey(nodeId: number) {
  return [...loreKeys.entity(nodeId), 'works'] as const
}

export function useWorks(nodeId: number) {
  return useQuery({
    queryKey: worksKey(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/works/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
    retry: false,
  })
}
