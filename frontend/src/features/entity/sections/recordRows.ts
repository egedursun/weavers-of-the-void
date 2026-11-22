import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { loreKeys } from '@/features/entity/api/keys'

export function useRecordRows(nodeId: number) {
  return useQuery({
    queryKey: [...loreKeys.entity(nodeId), 'record-rows'],
    queryFn: () =>
      unwrap(
        api.GET('/api/records/{node_id}/rows', {
          params: { path: { node_id: nodeId } },
        })
      ),
    retry: false,
  })
}
