import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'

export type WizardOptions = components['schemas']['WizardOptions']
export type WizardTemplate = components['schemas']['WizardTemplate']
export type GenesisRequest = components['schemas']['GenesisRequest']
export type LoreLanguage = components['schemas']['LoreLanguage']
export type TechnologyEra = components['schemas']['TechnologyEra']
export type LanguageTexture = components['schemas']['LanguageTexture']
export type Rarity = components['schemas']['Rarity']
export type CosmosSize = components['schemas']['CosmosSize']
export type StorytellerProfile = components['schemas']['StorytellerProfile']

export type SavedGenesis = components['schemas']['SavedGenesis']

export const genesisKeys = {
  wizard: [...queryKeys.rules.all, 'genesis-wizard'] as const,
  saved: [...queryKeys.world.all, 'genesis-settings'] as const,
}

export function useSavedGenesis(enabled = true) {
  return useQuery({
    queryKey: genesisKeys.saved,
    queryFn: () => unwrap(api.GET('/api/genesis/settings')),
    enabled,
  })
}

export function useWizardOptions() {
  return useQuery({
    queryKey: genesisKeys.wizard,
    queryFn: () => unwrap(api.GET('/api/genesis/wizard')),
    staleTime: Infinity,
  })
}

export function useStartGenesis() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: GenesisRequest) =>
      unwrap(api.POST('/api/genesis', { body })),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.jobs.all })
      void queryClient.invalidateQueries({ queryKey: queryKeys.world.all })
    },
  })
}
