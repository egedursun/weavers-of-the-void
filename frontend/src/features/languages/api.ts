import { useMutation, useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { errorText, useLoreMutation } from '@/features/entity/api/mutations'

export type LanguageEdit = components['schemas']['LanguageEditInput']
export type LanguageSignature = components['schemas']['LanguageSignature']
export type WritingSystem = components['schemas']['WritingSystem']
export type SampleNames = components['schemas']['SampleNames']

export const WRITING_SYSTEMS: readonly WritingSystem[] = [
  'alphabet',
  'syllabary',
  'pictographic',
  'knot',
  'notch',
  'logographic',
  'mixed',
  'abjad',
]

export const SAMPLE_PREVIEW_COUNT = 9

export function useEditLanguage() {
  return useLoreMutation({
    run: (body: LanguageEdit) =>
      unwrap(api.POST('/api/actions/language:edit', { body })),
  })
}

export function useRedrawSignature() {
  return useLoreMutation({
    run: (languageId: number) =>
      unwrap(
        api.POST('/api/actions/language:signature', {
          body: { language_id: languageId },
        })
      ),
  })
}

export function useEpochWords() {
  return useLoreMutation({
    run: (epoch: number | null) =>
      unwrap(
        api.POST('/api/actions/language:epoch_words', { body: { epoch } })
      ),
  })
}

export function useSampleNames(languageId: number) {
  return useMutation({
    onError: (error) => toast.error(errorText(error)),
    mutationFn: (salt: string) =>
      unwrap(
        api.POST('/api/languages/{language_id}/sample-names', {
          params: { path: { language_id: languageId } },
          body: { count: SAMPLE_PREVIEW_COUNT, salt },
        })
      ),
  })
}

export type NameReport = components['schemas']['NameReport']

export function useNameReport() {
  return useQuery({
    queryKey: [...queryKeys.world.all, 'dialect-fit'] as const,
    queryFn: () => unwrap(api.GET('/api/languages/dialect-fit')),
  })
}
