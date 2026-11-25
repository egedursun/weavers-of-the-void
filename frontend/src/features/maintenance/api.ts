import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { useMutation } from '@/api/mutation'
import { queryKeys } from '@/api/queryKeys'

export type MaintenanceTaskInfo = components['schemas']['TaskInfo']
export type MaintenanceTaskId = components['schemas']['MaintenanceTask']
export type MissingContent = components['schemas']['MissingContent']
export type JobAccepted = components['schemas']['JobAccepted']

export const maintenanceKeys = {
  tasks: [...queryKeys.jobs.all, 'maintenance', 'tasks'] as const,
  missing: [...queryKeys.world.all, 'maintenance', 'missing'] as const,
}

export function useMaintenanceTasks() {
  return useQuery({
    queryKey: maintenanceKeys.tasks,
    queryFn: () => unwrap(api.GET('/api/maintenance/tasks')),
  })
}

export function useMissingContent() {
  return useQuery({
    queryKey: maintenanceKeys.missing,
    queryFn: () => unwrap(api.GET('/api/maintenance/missing')),
  })
}

function useRefreshAfterJob() {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.jobs.all })
    void queryClient.invalidateQueries({ queryKey: maintenanceKeys.missing })
  }
}

export function useRunMaintenanceTask() {
  const refresh = useRefreshAfterJob()
  return useMutation({
    writes: [{ method: 'POST', path: '/api/maintenance/tasks/{task}/run' }],
    mutationFn: (task: MaintenanceTaskId) =>
      unwrap(
        api.POST('/api/maintenance/tasks/{task}/run', {
          params: { path: { task } },
        })
      ),
    onSettled: refresh,
  })
}

export function useWriteSonPowers() {
  const refresh = useRefreshAfterJob()
  return useMutation({
    writes: [{ method: 'POST', path: '/api/maintenance/sons/{son_id}/powers' }],
    mutationFn: (sonId: number) =>
      unwrap(
        api.POST('/api/maintenance/sons/{son_id}/powers', {
          params: { path: { son_id: sonId } },
        })
      ),
    onSettled: refresh,
  })
}

export function useWriteCosmosPrompts() {
  const refresh = useRefreshAfterJob()
  return useMutation({
    writes: [{ method: 'POST', path: '/api/maintenance/cosmos-prompts' }],
    mutationFn: () => unwrap(api.POST('/api/maintenance/cosmos-prompts')),
    onSettled: refresh,
  })
}

export function useWriteMissingChronicles() {
  const refresh = useRefreshAfterJob()
  return useMutation({
    writes: [{ method: 'POST', path: '/api/maintenance/chronicles' }],
    mutationFn: () => unwrap(api.POST('/api/maintenance/chronicles')),
    onSettled: refresh,
  })
}

export function useVerifyBackup() {
  return useMutation({
    writes: [
      { method: 'POST', path: '/api/maintenance/backups/{file_name}/verify' },
    ],
    mutationFn: (fileName: string) =>
      unwrap(
        api.POST('/api/maintenance/backups/{file_name}/verify', {
          params: { path: { file_name: fileName } },
        })
      ),
  })
}
