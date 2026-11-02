import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { cancelJob, fetchJobs } from '@/api/system'

export type EpochEstimate = components['schemas']['EpochEstimate']
export type JobAccepted = components['schemas']['JobAccepted']

export const epochKeys = {
  estimate: [...queryKeys.epochs.all, 'estimate'] as const,
}

export function useEpochEstimate() {
  return useQuery({
    queryKey: epochKeys.estimate,
    queryFn: () => unwrap(api.GET('/api/epochs/current/estimate')),
  })
}

function useInvalidateRun() {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.jobs.all })
    void queryClient.invalidateQueries({ queryKey: queryKeys.world.all })
    void queryClient.invalidateQueries({ queryKey: queryKeys.epochs.all })
  }
}

export function useCompleteEpoch() {
  const invalidate = useInvalidateRun()
  return useMutation({
    mutationFn: () => unwrap(api.POST('/api/epochs/current/complete')),
    onSuccess: invalidate,
  })
}

export function useStopEpoch() {
  const invalidate = useInvalidateRun()
  return useMutation({
    mutationFn: () => unwrap(api.POST('/api/epochs/current/stop')),
    onSuccess: invalidate,
  })
}

export function useSonTurn() {
  const invalidate = useInvalidateRun()
  return useMutation({
    mutationFn: (sonId: number) =>
      unwrap(
        api.POST('/api/sons/{son_id}/act', {
          params: { path: { son_id: sonId } },
        })
      ),
    onSuccess: invalidate,
  })
}

export const RECENT_JOB_LIMIT = 20

export type Job = components['schemas']['JobResponse']

export function useRecentJobs() {
  return useQuery({
    queryKey: queryKeys.jobs.list(RECENT_JOB_LIMIT),
    queryFn: () => fetchJobs(RECENT_JOB_LIMIT),
  })
}

export function useRunningJobs(): Job[] {
  const jobs = useRecentJobs()
  return (jobs.data ?? []).filter(
    (job) => job.status === 'running' || job.status === 'queued'
  )
}

export function useCancelJob() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: cancelJob,
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: queryKeys.jobs.all }),
  })
}
