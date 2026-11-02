import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

export type WorldSettings = components['schemas']['WorldSettingsView']
export type SettingsPatch = components['schemas']['PatchSettingsBody']
export type HealthReport = components['schemas']['HealthReport']

export const settingsKeys = {
  settings: [...queryKeys.world.all, 'settings'] as const,
  report: [...queryKeys.health, 'report'] as const,
}

export function useWorldSettings(enabled: boolean) {
  return useQuery({
    queryKey: settingsKeys.settings,
    queryFn: () => unwrap(api.GET('/api/settings')),
    enabled,
  })
}

function useInvalidateWorld() {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.world.all })
    void queryClient.invalidateQueries({ queryKey: queryKeys.ledger.all })
  }
}

export function usePatchSettings() {
  const invalidate = useInvalidateWorld()
  return useMutation({
    mutationFn: (body: SettingsPatch) =>
      unwrap(api.PATCH('/api/settings', { body })),
    onSuccess: invalidate,
  })
}

export function useCheatEssence() {
  const invalidate = useInvalidateWorld()
  return useMutation({
    mutationFn: (amount: number) =>
      unwrap(api.POST('/api/cheats/essence', { body: { amount } })),
    onSuccess: invalidate,
  })
}

export function useWriteMissingPrompts() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => unwrap(api.POST('/api/entities/prompts/write-missing')),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: queryKeys.jobs.all }),
  })
}

export function useHealthReport() {
  return useQuery({
    queryKey: settingsKeys.report,
    queryFn: () => unwrap(api.GET('/api/health/report')),
    retry: false,
  })
}

export function useResetWorld() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (confirm: string) =>
      unwrap(api.POST('/api/world/reset', { body: { confirm } })),
    onSuccess: () => void queryClient.invalidateQueries(),
  })
}
