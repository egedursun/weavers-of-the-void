import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { loreKeys } from '../api/keys'

export const economyKeys = {
  community: (id: number) => [...loreKeys.entity(id), 'economy'] as const,
  resource: (id: number) =>
    [...loreKeys.entity(id), 'resource-profile'] as const,
  route: (id: number) => [...loreKeys.entity(id), 'trade-route'] as const,
  prices: (id: number) => [...loreKeys.entity(id), 'prices'] as const,
  routes: (worldId: number | null) => ['economy', 'routes', worldId] as const,
  materials: (worldId: number) => ['economy', 'materials', worldId] as const,
  currencies: () => ['economy', 'currencies'] as const,
  ledger: () => ['economy', 'ledger'] as const,
  markets: (worldId: number | null) => ['economy', 'markets', worldId] as const,
}

export function useCommunityEconomy(id: number, enabled = true) {
  return useQuery({
    queryKey: economyKeys.community(id),
    enabled,
    queryFn: () =>
      unwrap(
        api.GET('/api/communities/{community_id}/economy', {
          params: { path: { community_id: id } },
        })
      ),
  })
}

export function useResourceProfile(id: number, enabled = true) {
  return useQuery({
    queryKey: economyKeys.resource(id),
    enabled,
    queryFn: () =>
      unwrap(
        api.GET('/api/resources/{resource_id}/profile', {
          params: { path: { resource_id: id } },
        })
      ),
  })
}

export function useTradeRoute(id: number, enabled = true) {
  return useQuery({
    queryKey: economyKeys.route(id),
    enabled,
    queryFn: () =>
      unwrap(
        api.GET('/api/trade-routes/{route_id}', {
          params: { path: { route_id: id } },
        })
      ),
  })
}

export function useMarketPrices(id: number, enabled = true) {
  return useQuery({
    queryKey: economyKeys.prices(id),
    enabled,
    queryFn: () =>
      unwrap(
        api.GET('/api/markets/{market_id}/prices', {
          params: { path: { market_id: id } },
        })
      ),
  })
}

export function useTradeRoutes(worldId: number | null, enabled = true) {
  return useQuery({
    queryKey: economyKeys.routes(worldId),
    enabled,
    queryFn: () =>
      unwrap(
        api.GET('/api/trade-routes', {
          params: { query: worldId ? { world_id: worldId } : {} },
        })
      ),
  })
}

export function useWorldMaterials(worldId: number | null) {
  return useQuery({
    queryKey: economyKeys.materials(worldId ?? 0),
    enabled: worldId !== null,
    queryFn: () =>
      unwrap(
        api.GET('/api/worlds/{world_id}/materials', {
          params: { path: { world_id: worldId ?? 0 } },
        })
      ),
  })
}

export function useCurrencies() {
  return useQuery({
    queryKey: economyKeys.currencies(),
    queryFn: () => unwrap(api.GET('/api/currencies')),
  })
}

export function useDebtsLedger() {
  return useQuery({
    queryKey: economyKeys.ledger(),
    queryFn: () => unwrap(api.GET('/api/ledger/debts')),
  })
}

export function useMarkets(worldId: number | null, enabled = true) {
  return useQuery({
    queryKey: economyKeys.markets(worldId),
    enabled,
    queryFn: () =>
      unwrap(
        api.GET('/api/markets', {
          params: { query: worldId ? { world_id: worldId } : {} },
        })
      ),
  })
}
