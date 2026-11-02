import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { queryKeys } from '@/api/queryKeys'

export const PEOPLE_LIST_LIMIT = 2000

export function usePeoples(enabled: boolean) {
  return useQuery({
    queryKey: [...queryKeys.world.all, 'peoples'],
    queryFn: () =>
      unwrap(
        api.GET('/api/entities', {
          params: { query: { type: 'people', limit: PEOPLE_LIST_LIMIT } },
        })
      ),
    enabled,
  })
}
