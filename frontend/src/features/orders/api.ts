import { useQuery } from '@tanstack/react-query'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { useGodAction } from '@/features/pantheon/godAction'

type Schema = components['schemas']
export type OrdersNodeView = Schema['OrdersNodeView']

export const ordersKeys = {
  of: (nodeId: number) =>
    [...queryKeys.world.all, 'orders-of', nodeId] as const,
}

export function useNodeOrders(nodeId: number) {
  return useQuery({
    queryKey: ordersKeys.of(nodeId),
    queryFn: () =>
      unwrap(
        api.GET('/api/orders/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export type OrdersAction =
  | 'saving:set'
  | 'saving:edit'
  | 'saving:delete'
  | 'hoard:create'
  | 'hoard:edit'
  | 'hoard:delete'
  | 'exchange_rate:create'
  | 'exchange_rate:edit'
  | 'exchange_rate:delete'
  | 'bill_of_exchange:create'
  | 'bill_of_exchange:edit'
  | 'bill_of_exchange:delete'
  | 'economic_order:create'
  | 'economic_order:edit'
  | 'economic_order:delete'
  | 'economic_order_kind:create'
  | 'economic_order_kind:edit'
  | 'economic_order_kind:delete'
  | 'order_transition:create'
  | 'order_transition:edit'
  | 'order_transition:delete'
  | 'order_transition:advance'
  | 'putting_out:create'
  | 'putting_out:edit'
  | 'putting_out:delete'
  | 'chain_holding:set'
  | 'chain_holding:edit'
  | 'chain_holding:delete'
  | 'tourist_flow:create'
  | 'tourist_flow:edit'
  | 'tourist_flow:delete'
  | 'orders:run'

export function useOrdersAction<Name extends OrdersAction, T>(
  name: Name,
  toBody: (vars: T) => ActionBody<Name>,
  success?: string
) {
  return useGodAction<T>({
    writes: [{ lever: name }],
    run: (vars) => postAction(name, toBody(vars)),
    success,
  })
}
