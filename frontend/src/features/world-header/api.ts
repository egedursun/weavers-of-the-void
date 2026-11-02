import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { queryKeys } from '@/api/queryKeys'

export const EPOCH_STAR_LIMIT = 1

export function useEpochStar() {
  return useQuery({
    queryKey: [...queryKeys.world.all, 'epoch-star'] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/cosmos/epoch-star', {
          params: { query: { limit: EPOCH_STAR_LIMIT } },
        })
      ),
  })
}

export function useDoomForecast(enabled: boolean) {
  return useQuery({
    queryKey: [...queryKeys.world.all, 'doom'] as const,
    queryFn: () => unwrap(api.GET('/api/doom')),
    enabled,
  })
}
