import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type NodeUrbanView = Schema['NodeUrbanView']
export type DistrictUrbanView = Schema['DistrictUrbanView']
export type TurfView = Schema['TurfView']
export type RacketView = Schema['RacketView']
export type PayrollView = Schema['PayrollView']
export type CrimeStanceView = Schema['CrimeStanceView']
export type OrderLawView = Schema['OrderLawView']
export type TribunalView = Schema['TribunalView']
export type TradingPostView = Schema['TradingPostView']
export type ConvoyView = Schema['ConvoyView']
export type FleetView = Schema['FleetView']
export type MarketPlayView = Schema['MarketPlayView']

export const urbanKeys = {
  of: (nodeId: number) => [...queryKeys.world.all, 'urban-of', nodeId] as const,
}

export function useNodeUrban(nodeId: number) {
  return useQuery({
    queryKey: urbanKeys.of(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/urban/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export type UrbanAction =
  | 'district_urban:edit'
  | 'town_urban:edit'
  | 'structure:place'
  | 'slums:clear'
  | 'district_service:set'
  | 'district_service:edit'
  | 'district_service:delete'
  | 'turf:set'
  | 'turf:edit'
  | 'turf:delete'
  | 'racket:set'
  | 'racket:edit'
  | 'racket:delete'
  | 'payroll:add'
  | 'payroll:edit'
  | 'payroll:delete'
  | 'crime_stance:set'
  | 'crime_stance:edit'
  | 'crime_stance:delete'
  | 'order_law:set'
  | 'order_law:edit'
  | 'order_law:delete'
  | 'tribunal:convene'
  | 'tribunal:strike'
  | 'trading_post:open'
  | 'trading_post:edit'
  | 'trading_post:close'
  | 'convoy:send'
  | 'convoy:edit'
  | 'convoy:delete'
  | 'fleet:set'
  | 'fleet:edit'
  | 'fleet:delete'
  | 'market_play:set'
  | 'market_play:edit'
  | 'market_play:delete'

export function useUrbanAction<Name extends UrbanAction, T>(
  name: Name,
  toBody: (vars: T) => ActionBody<Name>,
  success?: string
) {
  return useGodAction<T>({
    run: (vars) => postAction(name, toBody(vars)),
    success,
  })
}
