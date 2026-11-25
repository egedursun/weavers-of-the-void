import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { useMutation } from '@/api/mutation'
import { queryKeys } from '@/api/queryKeys'
import { apiUrl } from '@/api/url'

export type BackupInfo = components['schemas']['BackupInfo']
export type ImportMode = components['schemas']['ImportMode']
export type ImportResult = components['schemas']['ImportResult']
export type MergeSummary = components['schemas']['MergeSummary']

export const RESTORE_WORD = 'RESTORE'
export const REPLACE_WORD = 'REPLACE'
export const MERGE_WORD = 'MERGE'
export const RESET_WORD = 'RESET'

export type SecondaryTarget = components['schemas']['SecondaryTarget']

export const backupKeys = {
  list: [...queryKeys.backups.all, 'list'] as const,
  secondary: [...queryKeys.backups.all, 'secondary'] as const,
  discovery: [...queryKeys.world.all, 'discovery'] as const,
}

export function databaseUrl(file: string): string {
  return apiUrl(`/api/backups/${encodeURIComponent(file)}/database`)
}

export function packageUrl(file: string): string {
  return apiUrl(`/api/backups/${encodeURIComponent(file)}/package`)
}

export function exportUrl(images: boolean): string {
  return apiUrl('/api/world/export', { images })
}

export function useBackups() {
  return useQuery({
    queryKey: backupKeys.list,
    queryFn: () => unwrap(api.GET('/api/backups')),
  })
}

export function useSecondaryTarget() {
  return useQuery({
    queryKey: backupKeys.secondary,
    queryFn: () => unwrap(api.GET('/api/backups/secondary')),
  })
}

export function useSetSecondaryTarget() {
  const queryClient = useQueryClient()
  return useMutation({
    writes: [{ method: 'PUT', path: '/api/backups/secondary' }],
    mutationFn: (directory: string | null) =>
      unwrap(api.PUT('/api/backups/secondary', { body: { directory } })),
    onSuccess: (target) =>
      queryClient.setQueryData(backupKeys.secondary, target),
  })
}

export function useTakeBackup() {
  const queryClient = useQueryClient()
  return useMutation({
    writes: [{ method: 'POST', path: '/api/backups' }],
    mutationFn: () => unwrap(api.POST('/api/backups')),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: queryKeys.backups.all }),
  })
}

export function useRestoreBackup() {
  const queryClient = useQueryClient()
  return useMutation({
    writes: [{ method: 'POST', path: '/api/backups/restore' }],
    mutationFn: ({ file, confirm }: { file: string; confirm: string }) =>
      unwrap(api.POST('/api/backups/restore', { body: { file, confirm } })),
    onSuccess: () => void queryClient.invalidateQueries(),
  })
}

export function useImportWorld() {
  const queryClient = useQueryClient()
  return useMutation({
    writes: [{ method: 'POST', path: '/api/world/import' }],
    mutationFn: ({
      file,
      mode,
      confirm,
    }: {
      file: File
      mode: ImportMode
      confirm: string | null
    }) =>
      unwrap(
        api.POST('/api/world/import', {
          params: { query: { mode, confirm: confirm ?? undefined } },
          body: file as unknown as string,
          bodySerializer: (body) => body,
          headers: { 'content-type': 'application/octet-stream' },
        })
      ),
    onSuccess: () => void queryClient.invalidateQueries(),
  })
}

export function useDiscovery() {
  return useQuery({
    queryKey: backupKeys.discovery,
    queryFn: () => unwrap(api.GET('/api/discovery')),
  })
}

export function useEndDiscovery() {
  const queryClient = useQueryClient()
  return useMutation({
    writes: [{ method: 'POST', path: '/api/discovery/end' }],
    mutationFn: () => unwrap(api.POST('/api/discovery/end')),
    onSuccess: () => void queryClient.invalidateQueries(),
  })
}
