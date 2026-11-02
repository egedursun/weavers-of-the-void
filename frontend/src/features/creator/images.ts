import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { queryKeys } from '@/api/queryKeys'

export function useNodeImages(nodeId: number | null) {
  return useQuery({
    queryKey: [...queryKeys.images.all, 'node', nodeId],
    queryFn: async () => {
      const views = await unwrap(
        api.GET('/api/images', { params: { query: { node_id: nodeId } } })
      )
      return views.map((view) => view.image)
    },
    enabled: nodeId !== null,
  })
}
