import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { useMutation } from '@/api/mutation'
import { queryKeys } from '@/api/queryKeys'

export type BulkStatus = components['schemas']['BulkStatus']
export type LogLine = components['schemas']['LogLine']

export const bulkKeys = {
  status: [...queryKeys.world.all, 'batch-deepen'] as const,
}

export function useBulkStatus() {
  return useQuery({
    queryKey: bulkKeys.status,
    queryFn: () => unwrap(api.GET('/api/batch-deepen')),
  })
}

function useRefresh() {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: bulkKeys.status })
    void queryClient.invalidateQueries({ queryKey: queryKeys.jobs.all })
  }
}

export function useStartBulk() {
  const refresh = useRefresh()
  return useMutation({
    writes: [{ method: 'POST', path: '/api/batch-deepen/start' }],
    mutationFn: () => unwrap(api.POST('/api/batch-deepen/start')),
    onSuccess: refresh,
  })
}

export function useStopBulk() {
  const refresh = useRefresh()
  return useMutation({
    writes: [{ method: 'POST', path: '/api/batch-deepen/stop' }],
    mutationFn: () => unwrap(api.POST('/api/batch-deepen/stop')),
    onSuccess: refresh,
  })
}

export function useAssignNames() {
  const refresh = useRefresh()
  return useMutation({
    writes: [{ method: 'POST', path: '/api/names/assign-missing' }],
    mutationFn: () => unwrap(api.POST('/api/names/assign-missing')),
    onSuccess: refresh,
  })
}
